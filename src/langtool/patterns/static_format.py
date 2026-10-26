"""The binary format of the static rule tables (see langtool.patterns.static
and tools/gen_rule_tables.py, which writes them; the C extension reads them,
see _rule_tables.h). Shared by the generator and the runtime.

A blob holds the rules of all the built-in rule files of one language (all
variants): a header with a directory of sections, then the sections (8 byte
aligned, little-endian):

- META: JSON (the units, i.e. the rule files, their dependencies, problems,
  the replayed unifier calls, the type descriptors of the object records)
- STRTAB / STRDATA: the string pool, entries (offset, number of code
  points), the UTF-8 data of the strings consecutive and NUL terminated
  (the hash sets have the FNV-1a hashes of the code points)
- OBJIDX / OBJDATA: the object table, the offset of the record of every
  object of the rule graphs (the generic value encoding below), from which
  the Python objects are created lazily
- engine tables read in place by the C engine: SM (string matchers), HSET
  (sorted hash sets of strings), POS, CHUNK, PT (pattern tokens), IDX (index
  lists), RULE, HINT, CAT (categories), UNIT, IENT (the selector indexes:
  value -> rules), REGEX (the compiled programs of the regular expressions
  the rules use, keyed by the arguments of jregex.compile())
"""

import struct

FORMAT_VERSION = 3
MAGIC = b'LTRULES\x00'
NONE32 = 0xFFFFFFFF

HEADER = struct.Struct('<8sIIII')  # magic, version, header size, total size, number of sections
SECTION = struct.Struct('<IIII')  # id, offset, size, count

(SEC_META, SEC_STRTAB, SEC_STRDATA, SEC_OBJIDX, SEC_OBJDATA, SEC_SM, SEC_HSET, SEC_POS, SEC_CHUNK, SEC_PT, SEC_IDX,
 SEC_RULE, SEC_HINT, SEC_CAT, SEC_UNIT, SEC_IENT, SEC_REGEX) = range(1, 18)

STR = struct.Struct('<II')          # offset (the strings are consecutive, NUL terminated), code points
HENT = struct.Struct('<II')         # hash, string
# kind, case_sensitive, is_regexp, pad, value, value_lower, set offset, set size, object, pattern, regex flags
SM = struct.Struct('<BBBBIIIIIII')
POS = struct.Struct('<IIBBH')       # pos tag (string or NONE32), matcher (SM or NONE32), negation, unknown, pad
CHUNK = struct.Struct('<IIBBH')     # chunk tag string, object, is_regexp, pad
# object, flags, skip, max_occurrence, matcher, pos, chunk, exceptions offset (IDX), current/next exceptions,
# previous exceptions, AND group offset (IDX), AND group size, pad
PT = struct.Struct('<IIiiIIIIHHIHH')
HINT = struct.Struct('<BBHII')      # kind, pad, pad, set offset, set size
RULE = struct.Struct('<IIIIIiIHHIIHHhhiiIHHIHHiiiiII')
CAT = struct.Struct('<II')          # id string, default_on
UNIT = struct.Struct('<16I')
IENT = struct.Struct('<IIII')       # hash, string, list offset (IDX), list size
REGEX = struct.Struct('<IIII')      # hash, pattern string, flags, value offset (OBJDATA)

# RULE fields (in order)
RULE_FIELDS = ('obj', 'id', 'sub_id', 'cat', 'flags', 'moc', 'pt_off', 'n_pt', 'n_elno', 'elno_off', 'hints_off',
               'n_hints', 'n_pos_hints', 'anchor_hint', 'min_token_count', 'anchor_index', 'max_span', 'ap_off',
               'n_ap', 'n_tags', 'tags_off', 'n_tone_tags', 'kind', 'min_prev_matches', 'xml_line', 'spc', 'epc',
               'regex_pattern', 'regex_flags')
# UNIT fields: name, kind, rule offset, rule count, then for the selector with lemma hints and without them:
# token index offset, size, lemma index offset, size, unclassified offset (IDX), size
UNIT_FIELDS = ('name', 'kind', 'rule_off', 'rule_n', 'tok_off', 'tok_n', 'lem_off', 'lem_n', 'uncl_off', 'uncl_n',
               'tok_off_nl', 'tok_n_nl', 'lem_off_nl', 'lem_n_nl', 'uncl_off_nl', 'uncl_n_nl')

UNIT_GRAMMAR, UNIT_DISAMBIGUATION = 0, 1
RULE_PATTERN, RULE_REGEX, RULE_DISAMBIGUATION = 0, 1, 2
HINT_TOKEN, HINT_LEMMA, HINT_POS = 0, 1, 2

# PT flags
PT_INFLECTED = 1 << 0
PT_NEGATION = 1 << 1
PT_TEST_WHITESPACE = 1 << 2
PT_WHITESPACE_BEFORE = 1 << 3
PT_INSIDE_MARKER = 1 << 4
PT_EXCEPTION_VALID_NEXT = 1 << 5
PT_MAY_BE_OMITTED = 1 << 6
PT_TEST_STRING = 1 << 7
PT_UNIFICATION_NEUTRAL = 1 << 8
PT_UNI_NEGATION = 1 << 9
PT_LAST_IN_UNIFICATION = 1 << 10
PT_UNIFIED = 1 << 11           # unification_features is not None
PT_REFERENCE = 1 << 12         # token_reference is not None
PT_AND_GROUP = 1 << 13         # and_group is not None

# RULE flags
RF_SENT_START = 1 << 0
RF_GROUPS_OR_UNIFICATION = 1 << 1
RF_TEST_UNIFICATION = 1 << 2
RF_REFERENCES = 1 << 3         # a pattern token or AND group member has a token reference (matched with the objects)
RF_PRE_DISAMBIGUATION = 1 << 4  # PatternRule.interpret_pos_tags_pre_disambiguation
RF_USE_LIST = 1 << 5
RF_CHECK_POS = 1 << 6          # the POS hints are checked (not is_interpret_pos_tags_pre_disambiguation())
RF_DEFAULT_OFF = 1 << 7
RF_DEFAULT_TEMP_OFF = 1 << 8
RF_GOAL_SPECIFIC = 1 << 9
RF_GET_UNIFIED = 1 << 10
RF_HINTS = 1 << 11             # the rule has hints (a RuleHints with the speedups)
RF_ANTI_PATTERN = 1 << 12
RF_PICKY = 1 << 13             # 'picky' in tags
RF_PLAIN_IMMUNIZE = 1 << 14    # a DisambiguationPatternRule IMMUNIZE without filter and anti-patterns (an anti-pattern)

# value encoding tags
(V_NONE, V_FALSE, V_TRUE, V_INT, V_FLOAT, V_STR, V_LIST, V_TUPLE, V_DICT, V_SET, V_FROZENSET, V_OBJ, V_BYTES, V_UNSET,
 V_GLOBAL, V_EXT, V_HSET) = range(17)
# V_HSET: offset, size (varints) of a sorted hash set of the HSET section, then 0 (a frozenset of its strings) or 1 (a
# tuple of them, in the order of the set): the sets of strings that the engine has too

# external references (V_EXT)
EXT_LANGUAGE, EXT_UNIFIER_CONFIG, EXT_DISAMBIGUATION_UNIFIER_CONFIG = range(3)

# object record kinds (the type descriptors in META: [kind, module, qualname, attributes])
K_SLOTS = 'slots'      # attributes (in the order of the descriptor) then the instance dict (or None)
K_MATCHER = 'sm'       # the state of a StringMatcher (string_matcher._STATE), interned when created
K_POS = 'pos'          # (cache key or None, pos_tag, negation, pos_pattern, pos_unknown) of a PosToken
K_FILTER = 'filter'    # (factory method, class name)
K_REGEX = 'regex'      # (pattern, flags) of jregex.compile()
K_CONTAINER = 'container'  # a shared list, dict or set


def fnv1a(s):
    """the hash of the strings in the tables: 32 bit FNV-1a of the code
    points"""
    h = 2166136261
    for c in s:
        h = ((h ^ ord(c)) * 16777619) & 0xFFFFFFFF
    return h


def regex_hash(pattern, flags):
    return (fnv1a(pattern) ^ ((flags * 0x9E3779B1) & 0xFFFFFFFF)) & 0xFFFFFFFF


# the modules (relative to the package) that the loading of the rules depends on: the tables are stale when they
# change (in a source tree; an installed package is checked with its manifest)
CODE_DEPS = ('patterns/loader.py', 'patterns/rules.py', 'patterns/pattern_token.py', 'patterns/string_matcher.py',
             'patterns/match.py', 'patterns/unifier.py', 'patterns/static_format.py', 'jregex.py', 'analysis.py',
             'chunking.py', 'rules/base.py', 'tools.py', 'messages.py', 'language.py')
