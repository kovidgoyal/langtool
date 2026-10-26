"""Persistent caching (langtool.diskcache) of the rules loaded from the XML
rule files (grammar.xml etc. and disambiguation.xml) of a language.

The rules are pickled as they are right after loading (with the regular
expressions compiled while loading them: pickled compiled regular
expressions load much faster than they compile; those compiled later are in
the store of compiled expressions, see langtool.diskcache). References to
objects that are not created by the loading are stored by name and
resolved when loading: the Language, its unifier configurations, the
filters (created again with the filter factory) and module level constants.
The side effects of the loading on the language (the unification
definitions added to its unifier configuration, its cache of PosTokens)
are recorded and replayed. When loading, StringMatchers are interned and
the compiled regular expressions are shared with jregex.compile() (as when
the rules are loaded from XML: the variants of a language share them).

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


def _unifier_keys(u):
    return list(u.equivalence_types)


def load_rules(kind, language, files, load, filter_factory, unifier_config):
    """The rules loaded by load(filter_factory) -> (rules, problems) from
    the given XML files, from the disk cache if possible. The loading may
    add unification definitions to unifier_config (the configuration of
    the language)."""
    lang_code = diskcache.language_key(language)
    if lang_code is None or not diskcache.is_enabled():
        return load(filter_factory)
    unifier_before = _unifier_keys(unifier_config)
    # (the loading depends on the unification definitions that the unifier configuration has already)
    key = (lang_code, language.resource_root, language.rules_root, tuple(files), tuple(unifier_before))
    state = {}

    def build():
        rec = _RecordingFilterFactory(filter_factory)
        pos_before = set(language.pos_token_cache)
        rules, problems = load(rec)
        state['filters'] = rec.created
        added = [(k, unifier_config.equivalence_types[k]) for k in unifier_config.equivalence_types
                 if k not in unifier_before_set]
        payload = {
            'rules': rules,
            'problems': problems,
            'unifier_before': unifier_before,
            'unifier_added': added,
            'pos_tokens': [(k, v) for k, v in language.pos_token_cache.items() if k not in pos_before],
        }
        return payload

    unifier_before_set = set(unifier_before)
    types = _by_value_types()
    by_slots = frozenset(t for t in types if diskcache.uses_slots_reduced(t))
    import regex
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
        raise diskcache.Uncacheable('%s rules reference a %s' % (lang_code, t.__qualname__))

    filters = {}

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
        if tag == 'G':
            import importlib
            return getattr(importlib.import_module(pid[1]), pid[2])
        raise ValueError('unknown persistent id %r' % (pid,))

    # (the regular expressions compiled when loading the rules are stored with them)
    with diskcache.regex_store_paused():
        payload = diskcache.load_or_build('rules-' + kind, key, build, persist=persist, resolve=resolve, deps=files)
    if 'filters' in state:
        # built now: the side effects happened
        return payload['rules'], payload['problems']
    if payload['unifier_before'] != _unifier_keys(unifier_config):
        # (the unifier configuration of the language is not in the state the cached rules were loaded with)
        return load(filter_factory)
    for k, elem in payload['unifier_added']:
        unifier_config.set_equivalence(k[0], k[1], elem)
    cache = language.pos_token_cache
    for k, v in payload['pos_tokens']:
        cache.setdefault(k, v)
    return payload['rules'], payload['problems']
