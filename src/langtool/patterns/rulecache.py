"""Persistent caching (langtool.diskcache) of the rules loaded from the XML
rule files (grammar.xml etc. and disambiguation.xml) of a language.

The rules of the built-in languages normally come from the static rule
tables of the C extension (langtool.patterns.static) and are not cached; this
is used when the tables are not (the pure Python mode, stale or missing
tables, LANGTOOL_STATIC_RULES=0).

There is an entry per rule file, shared by the variants of a language: the
loading of a file only depends on the file, the short code of the language
(its messages) and its resource directory. The rules are pickled as they
are right after loading (with the regular expressions compiled while
loading them: pickled compiled regular expressions load much faster than
they compile; those compiled later are in the store of compiled
expressions, see langtool.diskcache). References to objects that are not
created by the loading are stored by name and bound when loading: the
Language, its unifier configurations, the filters (created again with the
filter factory), the PosTokens of the cache of the language (those of the
language are used, as when loading from XML, which shares them between the
rule files) and module level constants. The calls to set_equivalence() of
the unifier configurations are recorded and replayed (so an entry does not
depend on the definitions the configuration has already). When loading,
StringMatchers are interned and the compiled regular expressions are shared
with jregex.compile() (as when the rules are loaded from XML: the variants
of a language share them).

Only objects of the types listed here are pickled by value; if a rule
references something else, the rules are not cached (they are then loaded
from the XML files every time, as without the cache)."""

import enum
import itertools
import sys

from .. import diskcache, jregex
from .._base import speedups
from . import string_matcher
from .string_matcher import StringMatcher

_by_value = None


def _by_value_types():
    """the classes whose instances are pickled by value"""
    global _by_value
    if _by_value is None:
        import regex
        from ..analysis import AnalyzedToken, AnalyzedTokenReadings
        from ..chunking import ChunkTag
        from ..rules.base import Category, Example
        from .match import Match
        from .pattern_token import PatternToken, PosToken
        from . import rules as R
        types = {StringMatcher, PatternToken, PosToken, Match, ChunkTag, Category, Example, AnalyzedToken,
                 AnalyzedTokenReadings, R.TokenHint, R.PatternRule, R.RegexPatternRule, R.DisambiguationPatternRule,
                 type(regex.compile(''))}
        if speedups is not None:
            types.add(speedups.RuleHints)
        _by_value = frozenset(types)
    return _by_value


def _check_slots(cls):
    """the C base types pickle their members and the instance dict only:
    a Python subclass must not add other slots"""
    if speedups is None:
        return
    bases = (speedups.AnalyzedTokenBase, speedups.AnalyzedTokenReadingsBase, speedups.StringMatcherBase,
             speedups.PosTokenBase, speedups.PatternTokenBase)
    if not issubclass(cls, bases):
        return
    for k in cls.__mro__:
        if k in bases:
            break
        slots = k.__dict__.get('__slots__', ())
        if isinstance(slots, str):
            slots = (slots,)
        if any(s not in ('__weakref__', '__dict__') for s in slots):
            raise diskcache.Uncacheable('%s adds slots to a C base type' % cls.__name__)


def _module_constants(types):
    """id -> (module name, attribute) of the module level instances of the
    by-value classes in the langtool modules (pickled by reference so that
    their identity is kept)"""
    out = {}
    for name, mod in list(sys.modules.items()):
        if mod is None or not name.startswith('langtool'):
            continue
        for attr, v in list(vars(mod).items()):
            if type(v) in types:
                out.setdefault(id(v), (name, attr, v))
    return out


def _jregex_key(compiled, persist_state):
    """the key of jregex.compile() for a compiled expression (None if it was
    not compiled by jregex.compile())"""
    rev = persist_state.get('jregex')
    if rev is None:
        rev = persist_state['jregex'] = [0, {}]
    cache = jregex._cache
    n = len(cache)
    if rev[0] != n:
        # (jregex._cache only grows: the new entries are the last ones)
        try:
            items = list(itertools.islice(reversed(cache.items()), n - rev[0]))
        except RuntimeError:  # (changed by another thread)
            items = list(cache.items())
        for k, v in items:
            rev[1].setdefault(id(v), k)
        rev[0] = n
    key = rev[1].get(id(compiled))
    return key if key is not None and cache.get(key) is compiled else None


class _RecordingFilterFactory:
    """a filter factory that records the filters it creates"""

    def __init__(self, ff):
        self.ff = ff
        self.created = {}  # id -> (filter, method, class name)

    def get_filter(self, class_name, language):
        f = self.ff.get_filter(class_name, language)
        self.created[id(f)] = (f, 'get_filter', class_name)
        return f

    def get_regex_filter(self, class_name, language):
        f = self.ff.get_regex_filter(class_name, language)
        self.created[id(f)] = (f, 'get_regex_filter', class_name)
        return f


def load_rules(kind, language, files, load_file, filter_factory):
    """The rules loaded by load_file(path, filter_factory) -> (rules,
    problems) from the given XML files (concatenated), each file from the
    disk cache if possible. An entry is shared by the variants of the
    language (which load the same files, e.g. grammar.xml)."""
    rules = []
    problems = []
    for path in files:
        r, p = load_rules_file(kind, language, path, load_file, filter_factory)
        rules.extend(r)
        problems.extend(p)
    return rules, problems


def load_rules_file(kind, language, path, load_file, filter_factory):
    """The rules loaded by load_file(path, filter_factory) from a rule file,
    from the disk cache if possible.

    The loading of a file only depends on the file (and the entity files it
    includes), the short code of the language (the messages) and its
    resource directory; the language, its unifier configurations, its
    PosTokens and the filters are bound when the entry is loaded, so one
    entry serves all the variants of a language. Its side effects on the
    unifier configurations (the set_equivalence() calls) are recorded and
    replayed."""
    from . import unifier
    if diskcache.language_key(language) is None or not diskcache.is_enabled():
        return load_file(path, filter_factory)
    key = (language.short_code, language.resource_root, path)
    state = {}

    def build():
        rec = _RecordingFilterFactory(filter_factory)
        outer = getattr(unifier._recording, 'calls', None)
        calls = unifier._recording.calls = []
        pos_before = set(language.pos_token_cache)
        try:
            rules, problems = load_file(path, rec)
        finally:
            unifier._recording.calls = outer
            if outer is not None:
                outer.extend(calls)
        state['filters'] = rec.created
        return {
            'rules': rules,
            'problems': problems,
            'path': path,
            'unifier_calls': calls,
            # (the PosTokens that the loading added to the cache of the language, in their order)
            'pos_tokens': [k for k in language.pos_token_cache if k not in pos_before],
        }

    types = _by_value_types()
    by_slots = frozenset(t for t in types if diskcache.uses_slots_reduced(t))
    import regex
    from .pattern_token import PosToken
    pattern_type = type(regex.compile(''))
    persist_state = {}

    def persist(obj):
        t = type(obj)
        if obj is language:
            return ('L',)
        configs = persist_state.get('configs')
        if configs is None:
            # (the loading has used both already)
            configs = persist_state['configs'] = (language.unifier_config, language.disambiguation_unifier_config)
        if obj is configs[0]:
            return ('U',)
        if obj is configs[1]:
            return ('D',)
        created = state['filters'].get(id(obj))
        if created is not None and created[0] is obj:
            return ('F', id(obj), created[1], created[2])
        if t in types:
            consts = persist_state.get('consts')
            if consts is None:
                consts = persist_state['consts'] = _module_constants(types)
                for c in types:
                    _check_slots(c)
            c = consts.get(id(obj))
            if c is not None and c[2] is obj:
                return ('G', c[0], c[1])
            if t is StringMatcher:
                # (interned when loading, as when loading the rules from XML)
                return diskcache.Reduced((string_matcher._interned_matcher, (string_matcher._state(obj),)))
            if t is PosToken:
                # (one of the cache of the language: the one of the loading language, as when loading from XML)
                pos_keys = persist_state.get('pos')
                if pos_keys is None:
                    pos_keys = persist_state['pos'] = {id(v): k for k, v in language.pos_token_cache.items()}
                k = pos_keys.get(id(obj))
                if k is not None and language.pos_token_cache.get(k) is obj:
                    return ('P', k, obj.pos_tag, obj.negation, obj.pos_pattern, obj.pos_unknown)
            if t is pattern_type:
                # (a compiled expression of jregex.compile(): the one compiled already when loading, if there is one)
                key = _jregex_key(obj, persist_state)
                data = getattr(obj, '_pickled_data', None)
                if key is not None and data is not None:
                    return diskcache.Reduced((jregex._shared_compiled, (key, data)))
                return None
            if t in by_slots:
                return diskcache.slots_reduced(obj)
            return None
        if isinstance(obj, type) or t.__name__ in ('function', 'builtin_function_or_method'):
            return None  # (pickled by name)
        if isinstance(obj, enum.Enum):
            return None  # (pickled by name)
        raise diskcache.Uncacheable('%s rules reference a %s' % (language.code, t.__qualname__))

    filters = {}
    pos_created = {}

    def resolve(pid):
        tag = pid[0]
        if tag == 'L':
            return language
        if tag == 'U':
            return language.unifier_config
        if tag == 'D':
            return language.disambiguation_unifier_config
        if tag == 'F':
            f = filters.get(pid[1])
            if f is None:
                f = filters[pid[1]] = getattr(filter_factory, pid[2])(pid[3], language)
            return f
        if tag == 'P':
            k = pid[1]
            t = language.pos_token_cache.get(k)
            if t is None:
                t = pos_created.get(k)
                if t is None:
                    t = pos_created[k] = PosToken.__new__(PosToken)
                    t.pos_tag, t.negation, t.pos_pattern, t.pos_unknown = pid[2:]
            return t
        if tag == 'G':
            import importlib
            return getattr(importlib.import_module(pid[1]), pid[2])
        raise ValueError('unknown persistent id %r' % (pid,))

    # (the regular expressions compiled when loading the rules are stored with them)
    with diskcache.regex_store_paused():
        payload = diskcache.load_or_build('rules-' + kind, key, build, persist=persist, resolve=resolve,
                                          deps=[path])
    if 'filters' in state:
        # built now: the side effects happened
        return payload['rules'], payload['problems']
    cache = language.pos_token_cache
    for k in payload['pos_tokens']:
        t = pos_created.get(k)
        if t is not None:
            cache.setdefault(k, t)
    for config, feature, type_, elem in payload['unifier_calls']:
        config.set_equivalence(feature, type_, elem)
    built_path = payload['path']
    if built_path != path:
        # (the entry was written with the resource root in another directory: the keys of the entries are relative
        # to it, see diskcache.package_fingerprint())
        for r in payload['rules']:
            if getattr(r, 'source_file', None) == built_path:
                r.source_file = path
    return payload['rules'], payload['problems']
