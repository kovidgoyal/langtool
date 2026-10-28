"""The static rule tables: the rules of the built-in languages, compiled at
build time into read-only table files installed with the package
(langtool/_rule_tables/<code>.ltrt, see tools/gen_rule_tables.py and
static_format.py), which the C extension memory-maps (lazily, per language;
the pages are shared by the processes).

The C engine selects and matches the rules on the tables in place; the
Python objects of the rules (PatternRule, DisambiguationPatternRule,
PatternToken, ...) are created from the tables only when they are needed (a
rule matched, or code asks for the rules), and are the same as the objects
the XML loader creates (same attributes, same sharing of objects between
the rules, the PosTokens of the cache of the language, the interned
StringMatchers, the compiled regular expressions of jregex).

The tables are used for a rule file of a built-in language when the C
extension is used, it was built with the tables of the language, their file
can be mapped and is the one of the build (format, size and build id are
checked) and they are up to date: the files they were generated from (the rule files, the
entity files, the message bundles and the modules of the XML loading) are
unchanged. For an installed package the hashes of the manifest written when
it was built are compared (no file is read), in a source tree the size and
modification time of the files (and their hash if those differ). Otherwise
the rules are loaded from the XML files (and the disk cache). The table
files and the files they were generated from are those of the resource root
(see langtool.resources). status()
tells which languages use the tables; a stale table is logged (warning) on
the 'langtool.static' logger. LANGTOOL_STATIC_RULES=0 disables the tables;
LANGTOOL_RULE_TABLES_DIR is another directory with the table files (of the
same build).
"""

import json
import logging
import os
import threading

from .. import resources
from . import static_format as F

log = logging.getLogger('langtool.static')

_lock = threading.RLock()
_tables = {}     # short code -> Tables or None
_status = {}     # short code -> status string


def enabled():
    """whether the static tables can be used (the C extension is used and
    LANGTOOL_STATIC_RULES is not 0)"""
    from .._base import speedups
    if speedups is None or not hasattr(speedups, 'rule_blob'):
        return False
    v = os.environ.get('LANGTOOL_STATIC_RULES', '').strip().lower()
    return v not in ('0', 'off', 'no', 'false')


def tables_dir():
    """the directory of the table files: LANGTOOL_RULE_TABLES_DIR, else the
    _rule_tables directory of the resource root (see langtool.resources)"""
    d = os.environ.get('LANGTOOL_RULE_TABLES_DIR')
    return os.path.abspath(d) if d else resources.path('_rule_tables')


def table_path(short_code):
    return os.path.join(tables_dir(), short_code + '.ltrt')


def available_languages():
    """the short codes of the languages with tables in this build"""
    from .._base import speedups
    if speedups is None or not hasattr(speedups, 'rule_blob_names'):
        return []
    return list(speedups.rule_blob_names())


def status():
    """{short code: status} of the languages with tables in this build:
    'ok' (used), 'stale: <reason>' (the rules are loaded from the XML files),
    'unavailable: <reason>' (the table file is missing, damaged or of another
    build; the rules are loaded from the XML files), 'disabled' or 'not
    checked' (not used yet in this process)"""
    out = {}
    on = enabled()
    for code in available_languages():
        if not on:
            out[code] = 'disabled'
        else:
            out[code] = _status.get(code, 'not checked')
    return out


def tables_for(short_code):
    """the (up to date) Tables of a language, None if there are none or they
    can't be used"""
    t = _tables.get(short_code, False)
    if t is not False:
        return t
    with _lock:
        t = _tables.get(short_code, False)
        if t is not False:
            return t
        t = None
        if enabled():
            from .._base import speedups
            try:
                blob = speedups.rule_blob(short_code, table_path(short_code))
            except Exception as e:  # (missing, damaged or of another build)
                blob = None
                _status[short_code] = 'unavailable: %s' % e
                log.warning('static rule tables of %s not used: %s; the rules are loaded from the XML files',
                            short_code, e)
            if blob is not None:
                t = Tables(blob)
                reason = t.check()
                if reason is not None:
                    _status[short_code] = 'stale: ' + reason
                    log.warning('static rule tables of %s not used (%s): the rules are loaded from the XML files; '
                                'rebuild the extension to update them', short_code, reason)
                    t = None
                else:
                    _status[short_code] = 'ok'
        _tables[short_code] = t
        return t


def reset():
    """forget the tables and their checks (tests)"""
    with _lock:
        _tables.clear()
        _status.clear()


def _file_ok(rel, info, manifest):
    """whether the package file rel is the one the tables were generated from"""
    size, mtime_ns, digest = info
    if manifest is not None:
        hashes = manifest.get('hashes')
        if hashes:
            return hashes.get(rel) == digest
    path = resources.package_file(rel)
    try:
        st = os.stat(path)
    except OSError:
        return False
    if st.st_size != size:
        return False
    if st.st_mtime_ns == mtime_ns:
        return True
    from ..diskcache import file_hash
    try:
        return file_hash(path) == digest
    except OSError:
        return False


class Tables:
    """the tables of a language (a speedups.RuleBlob and its META)"""

    def __init__(self, blob):
        self.blob = blob
        self.meta = json.loads(blob.meta().decode('utf-8'))
        self.units = self.meta['units']
        self.unit_index = {(u['kind'], u['name'], u['short_code']): k for k, u in enumerate(self.units)}
        self._types = None
        self._bindings = {}
        self._regex_ok = None

    def check(self):
        """None if the tables can be used, else the reason"""
        m = self.meta
        if m.get('format') != F.FORMAT_VERSION:
            return 'other format'
        from ..diskcache import installed_manifest
        manifest = installed_manifest()
        for rel, info in m['files'].items():
            if not _file_ok(rel, info, manifest):
                return '%s changed' % rel
        return None

    def unit(self, kind, path, short_code):
        """the index of the unit of a rule file (absolute path), None if the tables have none"""
        rel = resources.relative(path)
        return self.unit_index.get((kind, rel, short_code)) if rel is not None else None

    def regex_programs_usable(self):
        """whether the compiled programs of the regular expressions can be used (the same version of the regex
        module)"""
        if self._regex_ok is None:
            try:
                import regex
                r = self.meta.get('regex', {})
                self._regex_ok = (r.get('version') == regex.__version__ and
                                  r.get('magic') == getattr(regex._regex, 'MAGIC', None))
            except Exception:
                self._regex_ok = False
        return self._regex_ok

    def ensure_types(self):
        if self._types is not None:
            return
        with _lock:
            if self._types is not None:
                return
            import importlib
            from .rules import AbstractPatternRule
            out = []
            for kind, module, qualname, attrs in self.meta['types']:
                if kind == F.K_SLOTS:
                    obj = importlib.import_module(module)
                    for part in qualname.split('.'):
                        obj = getattr(obj, part)
                    post = isinstance(obj, type) and issubclass(obj, AbstractPatternRule)
                    out.append((0, obj, tuple(attrs), post))
                elif kind == F.K_CONTAINER:
                    out.append((2, None, (), False))
                else:
                    out.append((1, kind, (), False))
            self.blob.set_types(tuple(out), self._engine_object)
            self._types = out

    def _engine_object(self, kind, arg):
        """the objects that the engine needs (shared by the languages): the StringMatcher of a matcher entry (kind
        0, arg: its object index), the ChunkTag of a chunk entry (1), the compiled expression of a regex rule (2,
        arg: (pattern, flags))"""
        if kind == 2:
            from .. import jregex
            return jregex.compile(*arg)
        return self.binding(None).obj(arg)

    def regex_program(self, pattern, flags):
        """the arguments of _regex.compile() for jregex.compile(pattern, flags), None if the tables have none"""
        if not self.regex_programs_usable():
            return None
        off = self.blob.regex_program(pattern, flags)
        if off < 0:
            return None
        return self.blob.decode_value(off, {}, None, None, None, None)

    def binding(self, language):
        """the Binding of the tables to a Language (None: the language independent objects only)"""
        key = id(language) if language is not None else None
        b = self._bindings.get(key)
        if b is None or b.language is not language:
            with _lock:
                b = self._bindings.get(key)
                if b is None or b.language is not language:
                    self.ensure_types()
                    b = self._bindings[key] = Binding(self, language)
        return b


def _glob(module, qualname):
    import importlib
    obj = importlib.import_module(module)
    for part in qualname.split('.'):
        obj = getattr(obj, part)
    return obj


class Binding:
    """the tables of a language bound to a Language object: the Python
    objects created from them for the language (each object of the tables is
    created once per language, like the XML loader creates one per
    language)"""

    def __init__(self, tables, language):
        self.tables = tables
        self.blob = tables.blob
        self.language = language
        self.memo = {}
        self.ready = {}
        self.lock = threading.RLock()
        self._units_loaded = {}
        self._unit_ok = {}
        self._ff = None
        self.variant_defaults = None

    # --- the hooks of RuleBlob.materialize ---

    def _special(self, kind, state):
        if kind == F.K_MATCHER:
            from .string_matcher import _interned_matcher
            return _interned_matcher(state)
        if kind == F.K_REGEX:
            from .. import jregex
            return jregex.compile(*state)
        lang = self.language
        if lang is None:
            raise ValueError('a %s object needs a language' % kind)
        if kind == F.K_POS:
            key, pos_tag, negation, pos_pattern, pos_unknown = state
            cache = lang.pos_token_cache
            t = cache.get(key)
            if t is None:
                from .pattern_token import PosToken
                t = PosToken.__new__(PosToken)
                t.pos_tag, t.negation, t.pos_pattern, t.pos_unknown = pos_tag, negation, pos_pattern, pos_unknown
                t = cache.setdefault(key, t)
            return t
        if kind == F.K_FILTER:
            method, class_name = state
            if self._ff is None:
                from ..rules.filters import default_filter_factory
                self._ff = default_filter_factory()
            return getattr(self._ff, method)(class_name, lang)
        raise ValueError('unknown object kind %r' % kind)

    def _ext(self, code):
        lang = self.language
        if lang is None:
            raise ValueError('a reference to the language without a language')
        if code == F.EXT_LANGUAGE:
            return lang
        if code == F.EXT_UNIFIER_CONFIG:
            return lang.unifier_config
        if code == F.EXT_DISAMBIGUATION_UNIFIER_CONFIG:
            return lang.disambiguation_unifier_config
        raise ValueError('unknown external reference %r' % code)

    def _post(self, obj):
        make = getattr(obj, '_make_native_hints', None)
        if make is not None:
            obj._native_hints = make()
        sf = getattr(obj, 'source_file', None)
        if sf is not None and sf.startswith(F.SOURCE_FILE_PREFIX):
            obj.source_file = os.path.join(resources.root(), *sf[len(F.SOURCE_FILE_PREFIX):].split('/'))
        if self.variant_defaults is not None:
            _apply_variant_defaults(obj, *self.variant_defaults)

    def apply_variant_defaults(self, enabled, disabled):
        """JLanguageTool applies the default_enabled_rules and default_disabled_rules of a variant to its pattern
        rules (set_default_on/off): to those created already and, from now on, when they are created"""
        with self.lock:
            self.variant_defaults = (frozenset(enabled), frozenset(disabled))
            for o in list(self.memo.values()):
                _apply_variant_defaults(o, *self.variant_defaults)

    def unit_ok(self, unit):
        """None if the unit can be used for the language (the filters it uses are available, and those that
        were not when the tables were generated still are not), else the reason"""
        r = self._unit_ok.get(unit, False)
        if r is False:
            r = self._unit_ok[unit] = _check_filters(self.tables.units[unit], self.language)
        return r

    def obj(self, index):
        """the object of the object record index (created when first needed)"""
        o = self.ready.get(index)
        if o is not None:
            return o
        with self.lock:
            # (memo has the objects being created too, ready only those that are complete: read without the lock)
            o = self.blob.materialize(index, self.memo, self._special, self._ext, _glob, self._post)
            self.ready[index] = o
            return o

    # --- units ---

    def load_unit(self, unit):
        """the side effects of loading the rule file of the unit (the set_equivalence() calls of the unifier
        configurations, replayed once)"""
        if unit in self._units_loaded:
            return
        with self.lock:
            if unit in self._units_loaded:
                return
            for cfg, feature, type_, elem in self.tables.units[unit]['unifier_calls']:
                self._ext(cfg).set_equivalence(feature, type_, self.obj(elem))
            self._units_loaded[unit] = True

    def unit_rules(self, unit):
        """(rules, problems) of the unit, all the rule objects created"""
        self.load_unit(unit)
        first, n, objs = self.blob.unit_rules(unit)
        rules = [self.obj(i) for i in objs]
        problems = [tuple(p) for p in self.tables.units[unit]['problems']]
        return rules, problems


def _apply_variant_defaults(obj, enabled, disabled):
    from .rules import PatternRule, RegexPatternRule
    if type(obj) in (PatternRule, RegexPatternRule):
        rid = obj.get_id()
        if rid in enabled:
            obj.set_default_on()
        if rid in disabled:
            obj.set_default_off()


def _filter_available(method, class_name, language):
    from ..rules import filters
    ff = filters.default_filter_factory()
    kind = 'regex_filter' if method == 'get_regex_filter' else 'filter'
    d = ff.regex_filters if kind == 'regex_filter' else ff.filters
    if d.get(class_name) is not None:
        return True
    try:
        return filters._lookup(kind, class_name, language) is not None
    except Exception:
        return False


def _check_filters(unit, language):
    """see Binding.unit_ok()"""
    if language is None:
        return None
    for method, class_name in unit['filters']:
        if not _filter_available(method, class_name, language):
            return 'filter %s not available' % class_name
    prefix = 'unsupported filter: '
    for p in unit['problems']:
        msg = p[2] if len(p) > 2 else ''
        if isinstance(msg, str) and msg.startswith(prefix):
            name = msg[len(prefix):]
            if _filter_available('get_filter', name, language) or _filter_available('get_regex_filter', name,
                                                                                       language):
                return 'filter %s is available now' % name
    return None


class StaticRules:
    """the rules of a rule file (a unit of the tables) for a language: a
    sequence whose rule objects are created when they are accessed"""

    def __init__(self, binding, unit):
        self.binding = binding
        self.tables = binding.tables
        self.blob = binding.blob
        self.unit = unit
        u = self.tables.units[unit]
        self.kind = u['kind']
        self.name = u['name']
        self.first, self.n = u['rules']
        self.problems = [tuple(p) for p in u['problems']]
        self._objs = None
        self._all = None
        self._ids = None
        binding.load_unit(unit)

    def __len__(self):
        return self.n

    def __repr__(self):
        return '<StaticRules %s (%s, %d rules)>' % (self.name, self.binding.language, self.n)

    def obj_indices(self):
        o = self._objs
        if o is None:
            o = self._objs = self.blob.unit_rules(self.unit)[2]
        return o

    def rule(self, i):
        """the rule object i (created if needed)"""
        return self.binding.obj(self.obj_indices()[i])

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self.rule(k) for k in range(*i.indices(self.n))]
        if i < 0:
            i += self.n
        if not 0 <= i < self.n:
            raise IndexError('rule index out of range')
        return self.rule(i)

    def __iter__(self):
        return iter(self.all())

    def all(self):
        """all the rule objects (created if needed)"""
        a = self._all
        if a is None:
            import gc
            enabled = gc.isenabled()
            gc.disable()
            try:
                a = self._all = [self.rule(i) for i in range(self.n)]
            finally:
                if enabled:
                    gc.enable()
        return a

    def materialized(self):
        """[(i, rule object)] of the rules created already"""
        ready = self.binding.ready
        if not ready:
            return []
        out = []
        for i, oi in enumerate(self.obj_indices()):
            o = ready.get(oi)
            if o is not None:
                out.append((i, o))
        return out

    def index_of(self, rule):
        """the index of the rule object, None if it is not one of this unit (or not created)"""
        for i, o in self.materialized():
            if o is rule:
                return i
        return None

    def select(self, ids=None, category_ids=None, id_prefix=None, min_prev_matches=False):
        """the indices of the rules with the ids or category ids, whose id starts with id_prefix or whose
        min_prev_matches is > 0 (see RuleBlob.select_rules; the created rules may have been changed: see
        JLanguageTool.rules_with())"""
        return self.blob.select_rules(self.first, self.n, frozenset(ids) if ids else None,
                                      frozenset(category_ids) if category_ids else None, id_prefix,
                                      bool(min_prev_matches))

    def active_mask(self, disabled_rules, enabled_rules, disabled_categories, enabled_categories, level,
                    active=None):
        """bytearray: 1 for the rules that are active for the configuration (JLanguageTool.ignore_rule and, if
        level is 1 (the default level) or 2 (another level), is_rule_active_for_level on the tables; active(rule)
        decides for the rules created already, which may have been changed)"""
        vd = self.binding.variant_defaults or (frozenset(), frozenset())
        m = bytearray(self.blob.active_mask(self.first, self.n, frozenset(disabled_rules),
                                            frozenset(enabled_rules), frozenset(disabled_categories),
                                            frozenset(enabled_categories), vd[0], vd[1], level))
        if active is not None:
            for i, o in self.materialized():
                m[i] = 1 if active(o) else 0
        return m

    def rule_ids(self, mask):
        """the set of the ids of the rules with mask[i]"""
        return self.blob.rule_ids(self.first, self.n, bytes(mask))

    def ids(self):
        """the ids of the rules (as created; created rules may have been changed)"""
        a = self._ids
        if a is None:
            a = self._ids = [t[0] for t in self.blob.rule_info(self.first, self.n)]
        return [o.get_id() if o is not None else a[i] for i, o in enumerate(self._created_list())]

    def _created_list(self):
        ready = self.binding.ready
        return [ready.get(oi) for oi in self.obj_indices()]


def rule_parts(kind, language, files, load_file, filter_factory):
    """The rules of the rule files: a list with, per file, a StaticRules (the
    tables are used) or the list of the rules loaded from the XML file (from
    the disk cache if possible, see langtool.patterns.rulecache); and the
    problems (skipped rules)."""
    from . import rulecache
    from .. import diskcache
    tables = None
    if diskcache.language_key(language) is not None and enabled():
        tables = tables_for(language.short_code)
    parts = []
    problems = []
    for f in files:
        u = tables.unit(kind, f, language.short_code) if tables is not None else None
        if u is not None:
            b = tables.binding(language)
            reason = b.unit_ok(u)
            if reason is None:
                sr = StaticRules(b, u)
                parts.append(sr)
                problems.extend(sr.problems)
                continue
            log.warning('static rules of %s not used for %s: %s', language.code, f, reason)
        r, p = rulecache.load_rules_file(kind, language, f, load_file, filter_factory)
        parts.append(list(r))
        problems.extend(p)
    return parts, problems


def flatten(parts):
    """the rule objects of the parts (all of them created)"""
    out = []
    for p in parts:
        out.extend(p.all() if isinstance(p, StaticRules) else p)
    return out


def regex_program(pattern, flags):
    """the compiled program of jregex.compile(pattern, flags) from the tables of a language in use, None if
    there is none"""
    for t in list(_tables.values()):
        if t is not None:
            d = t.regex_program(pattern, flags)
            if d is not None:
                return d
    return None


def _install_regex_programs():
    from .. import jregex
    if enabled():
        jregex._static_programs = regex_program


_install_regex_programs()


# the rule objects matched on the tables: id -> (rule, blob, rule index, its anti_patterns list) (for
# apply_anti_patterns())
_rule_refs = {}


def register_rule(rule, blob, index):
    """records that the rule object is the rule index of the tables (it is matched on the tables)"""
    if id(rule) not in _rule_refs:
        _rule_refs[id(rule)] = (rule, blob, index, rule.anti_patterns)


def _copy_sentence(sentence):
    return sentence.copy()


def apply_anti_patterns(rule, sentence, matches, matcher):
    """PatternRule.apply_anti_patterns() on the tables (the anti-patterns
    are applied and the rule is matched again without the objects of the
    anti-patterns), NotImplemented if it can't be done there (the rule is not
    one of the tables, it was changed, or its anti-patterns are not all plain
    immunizations)"""
    ref = _rule_refs.get(id(rule))
    if ref is None or ref[0] is not rule:
        return NotImplemented
    _, blob, index, aps = ref
    from .rules import PatternRule
    if (rule.anti_patterns is not aps or type(rule) is not PatternRule or
            'get_sentence_with_immunization' in rule.__dict__ or getattr(matcher, 'rule', None) is not rule):
        return NotImplemented
    from ..analysis import AnalyzedSentence
    immunized = blob.immunize(index, sentence, _copy_sentence, AnalyzedSentence,
                              lambda k: aps[k].get_replacer()._c_unify)
    if immunized is NotImplemented:
        return NotImplemented
    if immunized is not sentence:
        for t in immunized.tokens:
            if t.immunized:
                res = blob.run_rule(index, immunized, matcher._c_on_match, matcher._c_unify)
                if len(res) > 1:
                    from ..rules.base import rule_with_max_filter
                    return rule_with_max_filter(res)
                return res
    return matches
