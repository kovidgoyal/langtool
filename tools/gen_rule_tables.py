"""Generate the static rule tables of the built-in languages.

Usage: python tools/gen_rule_tables.py OUTDIR [--jobs N] [--languages en,de] [--src SRC]

For every built-in language (short code) the rules of all its rule files
(the grammar, style and variant files of all its variants, the rule files
for speakers of other mother tongues and the disambiguation files) are
loaded with the XML loader of the package (in the pure Python mode, without
the disk cache) and written to OUTDIR/<code>.ltrt (the format is described
in langtool.patterns.static_format). These files are installed with the
package (langtool/_rule_tables/) and memory-mapped by the C extension.
OUTDIR/rule_tables.c (compiled into the extension) lists the languages and
the build id of each file (the hash of the inputs it was generated from,
also in its header): a file of another build is not used. Loading from the
XML files keeps the tables identical to the rules loaded at runtime by
construction; the tables record the files they were generated from (sizes,
modification times and hashes) so that stale tables are detected at
runtime.

The languages are processed in parallel (--jobs, default: the number of
CPUs). A language is only generated again when its inputs (the package
files it depends on) changed (OUTDIR/<code>.stamp).
"""

import argparse
import hashlib
import io
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = os.path.join(os.path.dirname(HERE), 'src')

GENERATOR_VERSION = 4
EXT = '.ltrt'


def _setup(src):
    os.environ['LANGTOOL_PURE_PYTHON'] = '1'
    os.environ['LANGTOOL_DISK_CACHE'] = '0'
    if src not in sys.path:
        sys.path.insert(0, src)
    _stable_regex_hashes()


def _stable_key(k):
    if isinstance(k, type):
        return k.__module__, k.__qualname__
    if type(k) is tuple:
        return tuple(_stable_key(x) for x in k)
    return k


def _stable_regex_hashes():
    """reproducible tables: the nodes of the parsed patterns of the regex module are hashed on keys containing their
    class, and a class is hashed on its address, which differs between processes (PYTHONHASHSEED does not change
    that), so the sets of nodes (the first sets of alternations, ...) and so the compiled programs had their members
    in another order in every run. Hash the class name instead (only in the generator: the order does not change what
    a program matches)"""
    from regex import _regex_core
    base = _regex_core.RegexBase
    if getattr(base, '_langtool_stable_hash', False):
        return
    base.__hash__ = lambda self: hash(_stable_key(self._key))
    base._langtool_stable_hash = True


# ---------------------------------------------------------------------------
# loading

class _Unit:
    """the result of loading a rule file"""

    def __init__(self, kind, relpath, rules, problems, unifier_calls, deps):
        self.kind = kind
        self.relpath = relpath
        self.rules = rules
        self.problems = problems
        self.unifier_calls = unifier_calls
        self.deps = deps


def _load_unit(kind, path, language, pkg_dir):
    from langtool.patterns import loader, unifier
    from langtool.rules.filters import default_filter_factory
    from langtool.messages import messages_for
    deps = {path}
    orig_resolve = loader._EntityResolver.resolve

    def resolve(self, url, pubid, context):
        ep = self.entity_path(url)
        if ep is not None:
            deps.add(ep)
        return orig_resolve(self, url, pubid, context)

    rec = _RecordingFilterFactory(default_filter_factory())
    loader._EntityResolver.resolve = resolve
    unifier._recording.calls = calls = []
    try:
        if kind == 'grammar':
            rules, problems = loader.load_pattern_rules(path, language, language.resource_root, rec,
                                                        messages_for(language.short_code))
        else:
            rules, problems = loader.load_disambiguation_rules(path, language, language.resource_root, rec)
    finally:
        loader._EntityResolver.resolve = orig_resolve
        unifier._recording.calls = None
    msg_dir = os.path.join(pkg_dir, 'data', 'messages')
    for name in ('MessagesBundle_%s.properties' % language.short_code, 'MessagesBundle.properties',
                 'MessagesBundle_en.properties'):
        p = os.path.join(msg_dir, name)
        if os.path.exists(p):
            deps.add(p)
    unit = _Unit(kind, os.path.relpath(path, pkg_dir).replace(os.sep, '/'), rules, problems, calls,
                 sorted(os.path.relpath(p, pkg_dir).replace(os.sep, '/') for p in deps))
    unit.filters = rec.created
    unit.language = language
    return unit


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


def unit_files(short):
    """[(kind, path, variant code)] of the rule files of the language (in the order they are loaded)"""
    from langtool.api import get_language
    from langtool.languages import LANGUAGES
    d = LANGUAGES[short]
    out = []
    seen = set()

    def add(kind, path, code):
        k = (kind, os.path.abspath(path))
        if k not in seen and os.path.exists(path):
            seen.add(k)
            out.append((kind, os.path.abspath(path), code))

    for v in d['variants']:
        lang = get_language(v['code'])
        for f in lang.get_rule_file_names():
            add('grammar', f, lang.code)
        for name in (lang.get('mother_tongue_rule_files') or {}).values():
            add('grammar', os.path.join(lang.rules_dir, name), lang.code)
    for v in d['variants']:
        lang = get_language(v['code'])
        dv = lang.default_variant
        if dv.short_code != short:
            continue
        add('disambiguation', os.path.join(dv.resource_dir, 'disambiguation.xml'), dv.code)
        add('disambiguation', dv.resource_path('disambiguation-global.xml'), dv.code)
    return out


# ---------------------------------------------------------------------------
# encoding

def _varint(out, v):
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return


class _Pool:
    def __init__(self):
        self.index = {}
        self.entries = []  # (offset, nbytes, ncp, hash)
        self.data = bytearray()

    def add(self, s):
        i = self.index.get(s)
        if i is None:
            b = s.encode('utf-8')
            i = self.index[s] = len(self.entries)
            self.entries.append((len(self.data), len(s)))
            self.data += b
            self.data.append(0)
        return i


class GenerationError(Exception):
    pass


class _Encoder:
    """builds the object table and the engine tables of a language"""

    def __init__(self, short):
        from langtool.patterns import static_format as F
        self.F = F
        self.short = short
        self.pool = _Pool()
        self.types = []           # descriptors
        self.type_index = {}      # (kind, cls) -> index
        self.obj_index = {}       # id(obj) -> index
        self.objs = []            # the objects (kept alive)
        self.records = []         # bytes per object (filled later)
        self.obj_kind = []
        self.shared_containers = set()
        self.pending = []
        self.hset_index = {}      # frozenset of strings -> (offset, size) in hset
        self.idx = []             # the IDX u32 array
        self.hset = []            # (hash, str)
        self.sm = []
        self.sm_index = {}
        self.pos = []
        self.pos_index = {}
        self.chunk = []
        self.chunk_index = {}
        self.pt = []
        self.pt_index = {}
        self.hint = []
        self.cat = []
        self.cat_index = {}
        self.rule = []
        self.rule_index = {}
        self.ient = []
        self.units = []
        self.regex_keys = {}
        self._consts = None
        self._by_value = None

    # --- classification (like langtool.patterns.rulecache) ---

    def _by_value_types(self):
        if self._by_value is None:
            from langtool.patterns import rulecache
            self._by_value = rulecache._by_value_types()
        return self._by_value

    def _module_constants(self):
        if self._consts is None:
            from langtool.patterns import rulecache
            self._consts = rulecache._module_constants(self._by_value_types())
        return self._consts

    def type_id(self, kind, cls, attrs=None):
        key = (kind, cls)
        t = self.type_index.get(key)
        if t is None:
            t = self.type_index[key] = len(self.types)
            self.types.append([kind, cls.__module__, cls.__qualname__, list(attrs or ())])
        return t

    # --- the object graph ---

    def collect(self, unit):
        """assign indices to the objects reachable from the unit (first the rules, in order)"""
        self.unit = unit
        lang = unit.language
        self.ctx = {
            'language': lang,
            'configs': (lang.unifier_config, lang.disambiguation_unifier_config),
            'filters': unit.filters,
            'pos_keys': {id(v): k for k, v in lang.pos_token_cache.items()},
        }
        # count the references to the mutable containers (shared ones become objects)
        counts = {}
        seen = set()
        stack = list(unit.rules) + [c[3] for c in unit.unifier_calls]
        while stack:
            o = stack.pop()
            t = type(o)
            if t in (list, dict, set):
                counts[id(o)] = counts.get(id(o), 0) + 1
                if counts[id(o)] > 1:
                    self.shared_containers.add(id(o))
                    continue
            if t not in (tuple, frozenset):
                # (immutable containers are encoded where they are referenced: their contents are counted every time)
                if id(o) in seen:
                    continue
                seen.add(id(o))
            stack.extend(self._children(o))
        for r in unit.rules:
            self.obj(r)
        for c in unit.unifier_calls:
            self.obj(c[3])

    def _children(self, o):
        t = type(o)
        if t in (list, tuple, set, frozenset):
            return list(o)
        if t is dict:
            return list(o.keys()) + list(o.values())
        if o is None or t in (bool, int, float, str, bytes):
            return []
        kind = self._special(o)
        if kind is not None:
            return [x for x in kind[1] if not isinstance(x, (str, int, float, bool, type(None)))]
        if t in self._by_value_types():
            out = []
            for n in _slot_names(t):
                try:
                    out.append(getattr(o, n))
                except AttributeError:
                    pass
            d = getattr(o, '__dict__', None)
            if d:
                out.extend(d.values())
            return out
        return []

    def _special(self, o):
        """(kind, state) for objects with a special record, ('ext'/'global', ...) for references, None for
        generic objects"""
        F = self.F
        ctx = self.ctx
        t = type(o)
        if o is ctx['language']:
            return ('ext', (F.EXT_LANGUAGE,))
        if o is ctx['configs'][0]:
            return ('ext', (F.EXT_UNIFIER_CONFIG,))
        if o is ctx['configs'][1]:
            return ('ext', (F.EXT_DISAMBIGUATION_UNIFIER_CONFIG,))
        created = ctx['filters'].get(id(o))
        if created is not None and created[0] is o:
            return (F.K_FILTER, (created[1], created[2]))
        from langtool.patterns.string_matcher import StringMatcher, _state
        from langtool.patterns.pattern_token import PosToken
        types = self._by_value_types()
        if t in types:
            c = self._module_constants().get(id(o))
            if c is not None and c[2] is o:
                return ('global', (c[0], c[1]))
            if t is StringMatcher:
                return (F.K_MATCHER, (_state(o),))
            if t is PosToken:
                k = ctx['pos_keys'].get(id(o))
                if k is not None and ctx['language'].pos_token_cache.get(k) is o:
                    return (F.K_POS, (k, o.pos_tag, o.negation, o.pos_pattern, o.pos_unknown))
                return None
            import regex
            if t is type(regex.compile('')):
                from langtool import jregex
                for k, v in jregex._cache.items():
                    if v is o:
                        return (F.K_REGEX, k)
                raise GenerationError('a compiled regular expression not compiled by jregex.compile(): %r' % o)
            return None
        if isinstance(o, type) or t.__name__ in ('function', 'builtin_function_or_method'):
            return ('global', (o.__module__, o.__qualname__))
        import enum
        if isinstance(o, enum.Enum):
            return ('global', (t.__module__, '%s.%s' % (t.__qualname__, o.name)))
        raise GenerationError('%s rules reference a %s (%r)' % (self.short, t.__qualname__, o))

    def obj(self, o):
        """the object index of o (an object that is not a builtin value), assigned when first seen (its record is
        written by flush_records())"""
        i = self.obj_index.get(id(o))
        if i is not None:
            return i
        i = self.obj_index[id(o)] = len(self.objs)
        self.objs.append(o)
        self.records.append(None)
        self.pending.append(i)
        return i

    def flush_records(self):
        """writes the records of the objects (after the engine tables of the unit: the records refer to their hash
        sets)"""
        k = 0
        while k < len(self.pending):
            i = self.pending[k]
            self.records[i] = self._record(self.objs[i])
            k += 1
        self.pending = []

    def _record(self, o):
        F = self.F
        out = bytearray()
        t = type(o)
        if t in (list, dict, set):
            _varint(out, self.type_id(F.K_CONTAINER, t))
            self.value(out, o, container_ok=True)
            return bytes(out)
        sp = self._special(o)
        if sp is not None:
            kind, state = sp
            if kind in ('ext', 'global'):
                raise GenerationError('internal: reference recorded as object')
            _varint(out, self.type_id(kind, t))
            if kind == F.K_MATCHER:
                self.value(out, state[0])
            else:
                self.value(out, tuple(state))
            return bytes(out)
        names = _slot_names(t)
        _varint(out, self.type_id(F.K_SLOTS, t, names))
        for n in names:
            try:
                v = getattr(o, n)
            except AttributeError:
                out.append(F.V_UNSET)
                continue
            # (the order of the values of a TokenHint comes from iterating a frozenset: it is arbitrary)
            self.value(out, v, set_tuple=n == 'lower_case_values')
        d = getattr(o, '__dict__', None)
        self.value(out, dict(d) if d else None, container_ok=True)
        return bytes(out)

    def value(self, out, v, container_ok=False, set_tuple=False):
        F = self.F
        t = type(v)
        if (t is frozenset or (set_tuple and t is tuple)) and len(v) >= 3:
            key = frozenset(v)
            ref = self.hset_index.get(key) if len(key) == len(v) and all(type(x) is str for x in v) else None
            if ref is not None:
                out.append(F.V_HSET)
                _varint(out, ref[0])
                _varint(out, ref[1])
                out.append(0 if t is frozenset else 1)
                return
        if v is None:
            out.append(F.V_NONE)
        elif v is True:
            out.append(F.V_TRUE)
        elif v is False:
            out.append(F.V_FALSE)
        elif t is int:
            out.append(F.V_INT)
            _varint(out, (v << 1) if v >= 0 else ((-v << 1) - 1))
        elif t is float:
            out.append(F.V_FLOAT)
            out += struct.pack('<d', v)
        elif t is str:
            out.append(F.V_STR)
            _varint(out, self.pool.add(v))
        elif t is bytes:
            out.append(F.V_BYTES)
            _varint(out, len(v))
            out += v
        elif t in (list, dict, set) and id(v) in self.shared_containers and not container_ok:
            out.append(F.V_OBJ)
            _varint(out, self.obj(v))
        elif t in (list, tuple):
            out.append(F.V_LIST if t is list else F.V_TUPLE)
            _varint(out, len(v))
            # (the values of a TokenHint in a deterministic order: they come from iterating a frozenset)
            for x in (sorted(v) if set_tuple else v):
                self.value(out, x)
        elif t in (set, frozenset):
            out.append(F.V_SET if t is set else F.V_FROZENSET)
            items = sorted(v, key=_sort_key)
            _varint(out, len(items))
            for x in items:
                self.value(out, x)
        elif t is dict:
            out.append(F.V_DICT)
            _varint(out, len(v))
            for k, x in v.items():
                self.value(out, k)
                self.value(out, x)
        else:
            sp = self._special(v)
            if sp is not None and sp[0] == 'ext':
                out.append(F.V_EXT)
                _varint(out, sp[1][0])
            elif sp is not None and sp[0] == 'global':
                out.append(F.V_GLOBAL)
                _varint(out, self.pool.add(sp[1][0]))
                _varint(out, self.pool.add(sp[1][1]))
            else:
                out.append(F.V_OBJ)
                _varint(out, self.obj(v))

    # --- engine tables ---

    def idx_list(self, values):
        off = len(self.idx)
        self.idx.extend(values)
        return off

    def hash_set(self, strings):
        """(offset, size) of a sorted hash set of the strings"""
        F = self.F
        key = frozenset(strings)
        r = self.hset_index.get(key)
        if r is not None:
            return r
        ents = sorted(set((F.fnv1a(s), self.pool.add(s)) for s in sorted(key)))
        off = len(self.hset)
        self.hset.extend(ents)
        r = self.hset_index[key] = (off, len(ents))
        return r

    def e_sm(self, m):
        F = self.F
        i = self.sm_index.get(id(m))
        if i is not None:
            return i
        from langtool.patterns.string_matcher import KIND_EQUALS, KIND_SET, KIND_REGEX
        from langtool import jregex
        value = value_lower = F.NONE32
        set_off = set_n = 0
        flags = 0
        if m.kind == KIND_EQUALS:
            value = self.pool.add(m.value)
            value_lower = self.pool.add(m.value_lower)
        elif m.kind == KIND_SET:
            set_off, set_n = self.hash_set(m.values)
        elif m.kind == KIND_REGEX:
            flags = 0 if m.case_sensitive else jregex.IGNORECASE
            self.regex_keys[(m.pattern, flags)] = None
        else:
            raise GenerationError('unknown matcher kind %r' % m.kind)
        rec = (m.kind, bool(m.case_sensitive), bool(m.is_regexp), 0, value, value_lower, set_off, set_n, self.obj(m),
               self.pool.add(m.pattern), flags)
        i = self.sm_index[id(m)] = len(self.sm)
        self.sm.append(rec)
        return i

    def e_pos(self, p):
        F = self.F
        i = self.pos_index.get(id(p))
        if i is not None:
            return i
        rec = (self.pool.add(p.pos_tag) if p.pos_tag is not None else F.NONE32,
               self.e_sm(p.pos_pattern) if p.pos_pattern is not None else F.NONE32,
               bool(p.negation), bool(p.pos_unknown), 0)
        i = self.pos_index[id(p)] = len(self.pos)
        self.pos.append(rec)
        return i

    def e_chunk(self, c):
        i = self.chunk_index.get(id(c))
        if i is not None:
            return i
        if c.is_regexp:
            self.regex_keys[(c.chunk_tag, 0)] = None
        rec = (self.pool.add(c.chunk_tag), self.obj(c), bool(c.is_regexp), 0, 0)
        i = self.chunk_index[id(c)] = len(self.chunk)
        self.chunk.append(rec)
        return i

    def e_pt(self, pt):
        F = self.F
        i = self.pt_index.get(id(pt))
        if i is not None:
            return i
        i = self.pt_index[id(pt)] = len(self.pt)
        self.pt.append(None)
        flags = 0
        for attr, bit in (('inflected', F.PT_INFLECTED), ('negation', F.PT_NEGATION),
                          ('test_whitespace', F.PT_TEST_WHITESPACE), ('whitespace_before', F.PT_WHITESPACE_BEFORE),
                          ('inside_marker', F.PT_INSIDE_MARKER), ('exception_valid_next', F.PT_EXCEPTION_VALID_NEXT),
                          ('may_be_omitted', F.PT_MAY_BE_OMITTED), ('test_string', F.PT_TEST_STRING),
                          ('unification_neutral', F.PT_UNIFICATION_NEUTRAL), ('uni_negation', F.PT_UNI_NEGATION),
                          ('last_in_unification', F.PT_LAST_IN_UNIFICATION)):
            if getattr(pt, attr):
                flags |= bit
        if pt.unification_features is not None:
            flags |= F.PT_UNIFIED
        if pt.token_reference is not None:
            flags |= F.PT_REFERENCE
        if pt.and_group is not None:
            flags |= F.PT_AND_GROUP
            if type(pt.and_group) is not list:
                raise GenerationError('and_group must be a list')
        cn = tuple(pt.current_and_next_exceptions)
        prev = tuple(pt.previous_exceptions)
        if type(pt.current_and_next_exceptions) is not tuple or type(pt.previous_exceptions) is not tuple:
            raise GenerationError('the exceptions must be tuples')
        exc = [self.e_pt(e) for e in cn + prev]
        ands = [self.e_pt(a) for a in (pt.and_group or ())]
        if len(cn) > 0xFFFF or len(prev) > 0xFFFF or len(ands) > 0xFFFF:
            raise GenerationError('too many exceptions')
        rec = (self.obj(pt), flags, pt.skip, pt.max_occurrence, self.e_sm(pt.text_matcher),
               self.e_pos(pt.pos_token) if pt.pos_token is not None else F.NONE32,
               self.e_chunk(pt.chunk_tag) if pt.chunk_tag is not None else F.NONE32,
               self.idx_list(exc), len(cn), len(prev), self.idx_list(ands), len(ands), 0)
        self.pt[i] = rec
        return i

    def e_cat(self, c):
        F = self.F
        if c is None:
            return F.NONE32
        i = self.cat_index.get(id(c))
        if i is None:
            i = self.cat_index[id(c)] = len(self.cat)
            self.cat.append((self.pool.add(c.id) if c.id is not None else F.NONE32, 1 if c.default_on else 0))
        return i

    def reserve_rule(self, r):
        i = self.rule_index[id(r)] = len(self.rule)
        self.rule.append(None)
        return i

    def e_rule(self, r, anti_pattern=False):
        i = self.rule_index.get(id(r))
        if i is None:
            i = self.reserve_rule(r)
        elif self.rule[i] is not None:
            return i
        self.rule[i] = self._rule_record(r, anti_pattern)
        return i

    def _rule_record(self, r, anti_pattern):
        F = self.F
        from langtool.patterns import rules as R
        t = type(r)
        if t is R.PatternRule:
            kind = F.RULE_PATTERN
        elif t is R.RegexPatternRule:
            kind = F.RULE_REGEX
        elif t is R.DisambiguationPatternRule:
            kind = F.RULE_DISAMBIGUATION
        else:
            raise GenerationError('unexpected rule class %s' % t)
        flags = 0
        if anti_pattern:
            flags |= F.RF_ANTI_PATTERN
        if r.default_off:
            flags |= F.RF_DEFAULT_OFF
        if r.default_temp_off:
            flags |= F.RF_DEFAULT_TEMP_OFF
        if r.goal_specific:
            flags |= F.RF_GOAL_SPECIFIC
        if r.get_unified:
            flags |= F.RF_GET_UNIFIED
        if 'picky' in r.tags:
            flags |= F.RF_PICKY
        if (kind == F.RULE_DISAMBIGUATION and r.action == R.IMMUNIZE and r.filter is None and not r.anti_patterns
                and type(r).replace is R.DisambiguationPatternRule.replace):
            flags |= F.RF_PLAIN_IMMUNIZE
        pt_off = n_pt = elno_off = n_elno = 0
        hints_off = n_hints = n_pos = 0
        anchor_hint = -1
        anchor_index = 0
        mtc = 0
        moc = 0
        max_span = -1
        regex_pattern = F.NONE32
        regex_flags = 0
        if kind == F.RULE_REGEX:
            pattern, rflags = r._pattern_src if r._pattern_src is not None else (None, None)
            if pattern is None:
                raise GenerationError('a regex rule without the source of its pattern')
            regex_pattern = self.pool.add(pattern)
            regex_flags = rflags
            self.regex_keys[(pattern, rflags)] = None
        else:
            if r.sent_start:
                flags |= F.RF_SENT_START
            if r.groups_or_unification:
                flags |= F.RF_GROUPS_OR_UNIFICATION
            if r.test_unification:
                flags |= F.RF_TEST_UNIFICATION
            if kind == F.RULE_PATTERN:
                if r.interpret_pos_tags_pre_disambiguation:
                    flags |= F.RF_PRE_DISAMBIGUATION
                else:
                    flags |= F.RF_CHECK_POS
                if r.use_list:
                    flags |= F.RF_USE_LIST
                    elno_off = self.idx_list([x & 0xFFFFFFFF for x in r.element_no])
                    n_elno = len(r.element_no)
                    if any(x < 0 for x in r.element_no):
                        raise GenerationError('negative element_no')
            else:
                flags |= F.RF_CHECK_POS
                if r.action in (R.REMOVE, R.FILTER) and r.disambiguated_pos:
                    self.regex_keys[(r.disambiguated_pos, 0)] = None
            pts = list(r.pattern_tokens)
            for pt in pts:
                if pt.token_reference is not None or any(a.token_reference is not None for a in pt.and_group or ()):
                    flags |= F.RF_REFERENCES
            pt_ids = [self.e_pt(pt) for pt in pts]
            pt_off = self.idx_list(pt_ids)
            n_pt = len(pt_ids)
            moc = sum(1 for pt in pts if pt.get_min_occurrence() == 0)
            # hints
            hints = []
            th = r.token_hints or ()
            for h in th:
                hints.append((F.HINT_LEMMA if h.inflected else F.HINT_TOKEN,) + self.hash_set(h.lower_case_values))
                if len(set(h.lower_case_values)) != len(h.lower_case_values):
                    raise GenerationError('duplicate hint values')
            if r.anchor_hint is not None:
                for k, h in enumerate(th):
                    if h is r.anchor_hint:
                        anchor_hint = k
                        break
                else:
                    raise GenerationError('anchor hint not among the token hints')
                anchor_index = r.anchor_hint.token_index
            ph = r.pos_hints or ()
            for p in ph:
                hints.append((F.HINT_POS,) + self.hash_set(p))
            hints_off = len(self.hint)
            for kd, so, sn in hints:
                self.hint.append((kd, 0, 0, so, sn))
            n_hints = len(th)
            n_pos = len(ph)
            mtc = r.min_token_count
            max_span = r.max_span_tokens
            flags |= F.RF_HINTS
            for pt in pts:
                if pt.token_reference is not None:
                    self._match_regexes(pt.token_reference)
        for m in list(r.suggestion_matches) + list(r.suggestion_matches_out_msg):
            self._match_regexes(m)
        if kind == F.RULE_DISAMBIGUATION and r.match_element is not None:
            self._match_regexes(r.match_element)
        aps = [self.e_rule(ap, True) for ap in r.anti_patterns]
        ap_off = self.idx_list(aps)
        tags = [self.pool.add(s) for s in r.tags]
        tone = [self.pool.add(s) for s in r.tone_tags]
        tags_off = self.idx_list(tags + tone)
        if r.sub_id is not None and type(r.sub_id) is not str:
            raise GenerationError('sub_id must be a string')
        rec = (self.obj(r), self.pool.add(r.get_id()), self.pool.add(r.sub_id) if r.sub_id is not None else F.NONE32,
               self.e_cat(r.category) if r.category is not None else F.NONE32, flags, moc, pt_off, n_pt, n_elno,
               elno_off, hints_off, n_hints, n_pos, anchor_hint, mtc, anchor_index, max_span, ap_off, len(aps),
               len(tags), tags_off, len(tone), kind, r.min_prev_matches, r.xml_line_number,
               r.start_position_correction, r.end_position_correction, regex_pattern, regex_flags)
        return rec

    def _match_regexes(self, m):
        if m is None:
            return
        if m._regex_match_src is not None:
            self.regex_keys[(m._regex_match_src, 0)] = None
        if m._pos_regex_src is not None:
            self.regex_keys[(m._pos_regex_src, 0)] = None

    def index(self, rule_ids, with_lemma_hints):
        """(token entries, lemma entries, unclassified) of RuleSet(rules, with_lemma_hints)"""
        by_token = {}
        by_lemma = {}
        uncl = []
        for local, r in enumerate(rule_ids):
            hints = getattr(r, 'token_hints', None)
            first = None
            if hints:
                if with_lemma_hints:
                    first = hints[0]
                else:
                    for th in hints:
                        if not th.inflected:
                            first = th
                            break
            if first is not None:
                m = by_lemma if first.inflected else by_token
                for h in first.lower_case_values:
                    m.setdefault(h, []).append(local)
            else:
                uncl.append(local)
        return self._ients(by_token), self._ients(by_lemma), (self.idx_list(uncl), len(uncl))

    def _ients(self, d):
        F = self.F
        ents = sorted((F.fnv1a(k), self.pool.add(k), v) for k, v in sorted(d.items()))
        off = len(self.ient)
        for h, s, v in ents:
            self.ient.append((h, s, self.idx_list(v), len(v)))
        return off, len(ents)

    def add_unit(self, unit):
        F = self.F
        self.collect(unit)
        first = len(self.rule)
        # (the top level rules first, contiguous; then the anti-patterns of the unit)
        tops = []
        for r in unit.rules:
            if id(r) in self.rule_index:
                raise GenerationError('a rule appears twice in %s' % unit.relpath)
            tops.append(self.reserve_rule(r))
        for r in unit.rules:
            self.e_rule(r)
        if tops != list(range(first, first + len(tops))):
            raise GenerationError('a rule appears twice in %s' % unit.relpath)
        # (the anti-patterns were added after the top level rules)
        aps_from = first + len(tops)
        idx_l = self.index(unit.rules, True)
        idx_n = self.index(unit.rules, False)
        for c in unit.unifier_calls:
            self.obj(c[3])
        self.flush_records()
        rec = (self.pool.add(unit.relpath), F.UNIT_GRAMMAR if unit.kind == 'grammar' else F.UNIT_DISAMBIGUATION,
               first, len(tops)) + idx_l[0] + idx_l[1] + idx_l[2] + idx_n[0] + idx_n[1] + idx_n[2]
        calls = []
        for cfg, feature, type_, elem in unit.unifier_calls:
            if cfg is unit.language.unifier_config:
                c = F.EXT_UNIFIER_CONFIG
            elif cfg is unit.language.disambiguation_unifier_config:
                c = F.EXT_DISAMBIGUATION_UNIFIER_CONFIG
            else:
                raise GenerationError('set_equivalence() on another configuration')
            calls.append([c, feature, type_, self.obj(elem)])
        filters = sorted(set((v[1], v[2]) for v in unit.filters.values()))
        filters = [list(f) for f in filters]
        problems = [list(p) for p in unit.problems]
        self.units.append({
            'name': unit.relpath, 'kind': unit.kind, 'record': list(rec), 'rules': [first, len(tops)],
            'anti_patterns': [aps_from, len(self.rule) - aps_from], 'problems': problems,
            'unifier_calls': calls, 'deps': unit.deps, 'filters': filters, 'short_code': unit.language.short_code,
            'loaded_with': unit.language.code, 'objects': len(self.objs),
        })

    # --- regex programs ---

    def regex_programs(self):
        """[(hash, pattern string, flags, encoded value)]"""
        F = self.F
        from langtool import jregex
        out = []
        for (pattern, flags) in self.regex_keys:
            try:
                r = jregex.compile(pattern, flags)
            except Exception as e:
                raise GenerationError('cannot compile %r: %s' % (pattern, e))
            data = r._pickled_data
            buf = bytearray()
            self.value(buf, tuple(data))
            out.append((F.regex_hash(pattern, flags), self.pool.add(pattern), flags, bytes(buf)))
        out.sort(key=lambda e: (e[0], e[1], e[2]))
        return out


def _sort_key(x):
    return (type(x).__name__, repr(x))


_slot_cache = {}


def _slot_names(cls):
    r = _slot_cache.get(cls)
    if r is None:
        names = []
        for k in reversed(cls.__mro__):
            s = k.__dict__.get('__slots__', ())
            if isinstance(s, str):
                s = (s,)
            for n in s:
                if n in ('__dict__', '__weakref__') or n in names:
                    continue
                names.append(n)
        r = _slot_cache[cls] = tuple(names)
    return r


# ---------------------------------------------------------------------------
# writing

def _file_info(path):
    st = os.stat(path)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return [st.st_size, st.st_mtime_ns, h.hexdigest()[:32]]


def build_language(short, pkg_dir):
    """the blob (bytes) of a language"""
    from langtool.api import get_language
    from langtool.patterns import static_format as F
    import regex
    t0 = time.time()
    enc = _Encoder(short)
    files = unit_files(short)
    units = []
    for kind, path, code in files:
        lang = get_language(code)
        units.append(_load_unit(kind, path, lang, pkg_dir))
    t1 = time.time()
    for u in units:
        enc.add_unit(u)
    regexes = enc.regex_programs()
    t2 = time.time()
    deps = set(F.CODE_DEPS)
    for u in units:
        deps.update(u.deps)
    from langtool import fsa  # noqa: F401  (messages.read_properties)
    deps.add('fsa.py')
    finfo = {d: _file_info(os.path.join(pkg_dir, d)) for d in sorted(deps)}
    languages = {}
    from langtool.languages import LANGUAGES
    for v in LANGUAGES[short]['variants']:
        lang = get_language(v['code'])
        languages[lang.code] = {'grammar': [os.path.relpath(f, pkg_dir).replace(os.sep, '/')
                                            for f in lang.get_rule_file_names()]}
    meta = {
        'format': F.FORMAT_VERSION, 'generator': GENERATOR_VERSION, 'language': short,
        'types': enc.types, 'units': enc.units, 'files': finfo, 'code_deps': list(F.CODE_DEPS) + ['fsa.py'],
        'languages': languages,
        'regex': {'version': regex.__version__, 'magic': getattr(regex._regex, 'MAGIC', None)},
        'objects': len(enc.objs),
    }
    deps = sorted(deps)
    digest = _inputs_digest(pkg_dir, deps)
    blob = _assemble(enc, meta, regexes, build_id(digest))
    t3 = time.time()
    stats = {'load': round(t1 - t0, 2), 'encode': round(t2 - t1, 2), 'write': round(t3 - t2, 2),
             'size': len(blob), 'objects': len(enc.objs), 'rules': len(enc.rule), 'strings': len(enc.pool.entries),
             'regexes': len(regexes)}
    return blob, stats, deps, digest


def build_id(digest):
    """the build id of a table (16 bytes): the start of the digest of its inputs"""
    return bytes.fromhex(digest[:32])


def _assemble(enc, meta, regexes, bid):
    F = enc.F
    sections = []

    def pack_all(st, rows):
        b = bytearray(st.size * len(rows))
        o = 0
        for r in rows:
            st.pack_into(b, o, *r)
            o += st.size
        return bytes(b)

    # the object table (the records of the regex programs are appended to OBJDATA)
    objdata = bytearray()
    objidx = bytearray(4 * len(enc.records))
    for i, rec in enumerate(enc.records):
        struct.pack_into('<I', objidx, 4 * i, len(objdata))
        objdata += rec
    regex_rows = []
    for h, p, fl, val in regexes:
        regex_rows.append((h, p, fl, len(objdata)))
        objdata += val
    meta_b = json.dumps(meta, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')
    sections.append((F.SEC_META, meta_b, 1))
    sections.append((F.SEC_STRTAB, pack_all(F.STR, enc.pool.entries), len(enc.pool.entries)))
    sections.append((F.SEC_STRDATA, bytes(enc.pool.data), len(enc.pool.data)))
    sections.append((F.SEC_OBJIDX, bytes(objidx), len(enc.records)))
    sections.append((F.SEC_OBJDATA, bytes(objdata), len(objdata)))
    sections.append((F.SEC_SM, pack_all(F.SM, enc.sm), len(enc.sm)))
    sections.append((F.SEC_HSET, pack_all(F.HENT, enc.hset), len(enc.hset)))
    sections.append((F.SEC_POS, pack_all(F.POS, enc.pos), len(enc.pos)))
    sections.append((F.SEC_CHUNK, pack_all(F.CHUNK, enc.chunk), len(enc.chunk)))
    sections.append((F.SEC_PT, pack_all(F.PT, enc.pt), len(enc.pt)))
    sections.append((F.SEC_IDX, struct.pack('<%dI' % len(enc.idx), *enc.idx), len(enc.idx)))
    sections.append((F.SEC_RULE, pack_all(F.RULE, enc.rule), len(enc.rule)))
    sections.append((F.SEC_HINT, pack_all(F.HINT, enc.hint), len(enc.hint)))
    sections.append((F.SEC_CAT, pack_all(F.CAT, enc.cat), len(enc.cat)))
    sections.append((F.SEC_UNIT, pack_all(F.UNIT, [u['record'] for u in enc.units]), len(enc.units)))
    sections.append((F.SEC_IENT, pack_all(F.IENT, enc.ient), len(enc.ient)))
    sections.append((F.SEC_REGEX, pack_all(F.REGEX, regex_rows), len(regex_rows)))
    header_size = F.HEADER.size + F.SECTION.size * len(sections)
    off = (header_size + 7) & ~7
    out = bytearray(off)
    dir_rows = []
    for sid, data, count in sections:
        dir_rows.append((sid, off, len(data), count))
        out += data
        off += len(data)
        pad = (-off) & 7
        out += b'\0' * pad
        off += pad
    F.HEADER.pack_into(out, 0, F.MAGIC, F.FORMAT_VERSION, header_size, len(out), len(sections), bid)
    for k, row in enumerate(dir_rows):
        F.SECTION.pack_into(out, F.HEADER.size + k * F.SECTION.size, *row)
    return bytes(out)


def _worker(args):
    short, src, outdir = args
    _setup(src)
    pkg_dir = os.path.join(src, 'langtool')
    try:
        blob, stats, deps, stamp = build_language(short, pkg_dir)
    except Exception as e:
        import traceback
        return short, None, '%s: %s\n%s' % (type(e).__name__, e, traceback.format_exc())
    path = os.path.join(outdir, short + EXT)
    # (written to another file and renamed: processes may have the old one mapped)
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(blob)
    os.replace(tmp, path)
    with open(os.path.join(outdir, short + '.stamp'), 'w') as f:
        json.dump({'digest': stamp, 'deps': deps}, f)
    return short, stats, None


def _inputs_digest(pkg_dir, deps):
    # (not the Python version: the tables generated with the supported versions (3.11-3.14) are the same, except for
    # the order of the members of some sets in the compiled programs of the regex module (the iteration order of
    # sets of the Python version), which does not change what they match: the tables of one Python version can be
    # used with the others)
    h = hashlib.sha256()
    h.update(repr(GENERATOR_VERSION).encode())
    with open(os.path.abspath(__file__), 'rb') as f:
        h.update(f.read())
    for d in deps:
        p = os.path.join(pkg_dir, d)
        try:
            with open(p, 'rb') as f:
                h.update(d.encode() + b'\0' + f.read())
        except OSError:
            h.update(d.encode() + b'\0missing')
    return h.hexdigest()


def _up_to_date(short, src, outdir):
    pkg_dir = os.path.join(src, 'langtool')
    try:
        with open(os.path.join(outdir, short + '.stamp')) as f:
            st = json.load(f)
        if not os.path.exists(os.path.join(outdir, short + EXT)):
            return False
        return st['digest'] == _inputs_digest(pkg_dir, st['deps'])
    except (OSError, ValueError, KeyError):
        return False


def write_c_file(outdir, shorts):
    """rule_tables.c: the languages with tables and the build ids of their files"""
    lines = ['/* generated by tools/gen_rule_tables.py: the static rule tables of this build (do not edit) */',
             '#include <stddef.h>', '',
             'typedef struct { const char *name; const char *build_id; } langtool_rule_table;',
             'const langtool_rule_table langtool_rule_tables[] = {']
    for short in shorts:
        with open(os.path.join(outdir, short + '.stamp')) as f:
            digest = json.load(f)['digest']
        lines.append('    {"%s", "%s"},' % (short, build_id(digest).hex()))
    lines.append('    {NULL, NULL}')
    lines.append('};')
    lines.append('const int langtool_rule_table_count = %d;' % len(shorts))
    text = '\n'.join(lines) + '\n'
    path = os.path.join(outdir, 'rule_tables.c')
    try:
        with open(path) as f:
            if f.read() == text:
                return path
    except OSError:
        pass
    with open(path, 'w') as f:
        f.write(text)
    return path


def table_files(outdir):
    """the paths of the table files listed in outdir/rule_tables.c"""
    import re
    with open(os.path.join(outdir, 'rule_tables.c')) as f:
        names = re.findall(r'^    \{"([^"]+)", "[0-9a-f]{32}"\},$', f.read(), re.M)
    return [os.path.join(outdir, s + EXT) for s in names]


def write_empty_c_file(outdir):
    os.makedirs(outdir, exist_ok=True)
    return write_c_file(outdir, [])


def all_short_codes(src):
    _setup(src)
    from langtool.languages import LANGUAGES
    return list(LANGUAGES)


def generate(outdir, src=DEFAULT_SRC, jobs=None, languages=None, log=print):
    """generate the tables of the languages (all by default) in outdir,
    returns the path of rule_tables.c"""
    src = os.path.abspath(src)
    os.makedirs(outdir, exist_ok=True)
    shorts = languages or all_short_codes(src)
    todo = [s for s in shorts if not _up_to_date(s, src, outdir)]
    t0 = time.time()
    if todo:
        jobs = jobs or os.cpu_count() or 1
        args = [(s, src, outdir) for s in todo]
        # (the large languages first)
        order = {'en': 0, 'ca': 1, 'fr': 2, 'de': 3, 'pt': 4, 'es': 5, 'nl': 6, 'pl': 7, 'uk': 8}
        args.sort(key=lambda a: order.get(a[0], 99))
        errors = []
        if jobs > 1 and len(args) > 1:
            import multiprocessing
            ctx = multiprocessing.get_context('spawn')
            # (a process per language: the tables do not depend on the languages generated before in a process)
            with ctx.Pool(min(jobs, len(args)), maxtasksperchild=1) as pool:
                results = pool.imap_unordered(_worker, args)
                for short, stats, err in results:
                    if err:
                        errors.append((short, err))
                    else:
                        log('rule tables: %s %s' % (short, stats))
        elif len(args) == 1:
            short, stats, err = _worker(args[0])
            if err:
                errors.append((short, err))
            else:
                log('rule tables: %s %s' % (short, stats))
        else:
            for a in args:
                short, stats, err = _worker(a)
                if err:
                    errors.append((short, err))
                else:
                    log('rule tables: %s %s' % (short, stats))
        if errors:
            raise GenerationError('; '.join('%s: %s' % e for e in errors))
    log('rule tables: %d languages (%d generated) in %.1fs' % (len(shorts), len(todo), time.time() - t0))
    return write_c_file(outdir, shorts)


def main(argv=None):
    if argv is None and os.environ.get('PYTHONHASHSEED') != '0':
        # (reproducible tables: the compiled programs of some regular expressions depend on the order of iterating
        # sets of strings in the regex module)
        # (a child process, not os.execve: on Windows exec starts a new process and the calling one exits at once,
        # so callers waiting for this one, like setup.py, would not wait for the tables)
        import subprocess
        sys.exit(subprocess.call([sys.executable] + sys.argv, env=dict(os.environ, PYTHONHASHSEED='0')))
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('outdir')
    ap.add_argument('--jobs', type=int, default=None)
    ap.add_argument('--languages', default=None, help='comma separated short codes (default: all)')
    ap.add_argument('--src', default=DEFAULT_SRC)
    a = ap.parse_args(argv)
    langs = a.languages.split(',') if a.languages else None
    generate(a.outdir, a.src, a.jobs, langs)


if __name__ == '__main__':
    main()
