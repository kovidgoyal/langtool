"""Port of org.languagetool.rules.patterns.StringMatcher.

A StringMatcher matches a whole string, either exactly (optionally case
insensitive) or using a (Java) regular expression. As in LanguageTool,
regular expressions whose set of possible values can be enumerated are
turned into simple set lookups.
"""

from .. import jregex
from .._base import StringMatcherBase
from ..tools import java_equals_ignore_case, is_letter_or_digit

MAX_MATCH_LENGTH = 250
MAX_CHAR_RANGE_WIDTH = 64

KIND_EQUALS = 0
KIND_SET = 1
KIND_REGEX = 2


class TooComplexRegexp(Exception):
    pass


class _RegexpParser:
    _unsupported = '?$^{}*+'
    _finishing = ')|'
    _starting = '([\\'
    _non_literal = _finishing + _unsupported + _starting + '.'

    def __init__(self, regexp):
        if regexp.startswith('\\b'):
            regexp = regexp[2:]
        if regexp.startswith('^'):
            regexp = regexp[1:]
        if regexp.endswith('\\b') and not regexp.endswith('\\\\b'):
            regexp = regexp[:-2]
        if regexp.endswith('$') and not regexp.endswith('\\$'):
            regexp = regexp[:-1]
        self.r = regexp
        self.pos = 0

    def char_at(self, i):
        try:
            return self.r[i]
        except IndexError:
            raise TooComplexRegexp()

    def disjunction(self):
        comps = [self.concatenation()]
        while True:
            if self.pos >= len(self.r) or self.r[self.pos] != '|':
                return comps[0] if len(comps) == 1 else self.handle_or(comps)
            self.pos += 1
            comps.append(self.concatenation())

    def concatenation(self):
        result = self.postfix()
        while self.pos < len(self.r):
            c = self.r[self.pos]
            if c in self._finishing:
                break
            if c in self._unsupported:
                raise TooComplexRegexp()
            result = self.handle_concatenation(result, self.postfix())
        return result

    def postfix(self):
        group = self.atom()
        if self.pos < len(self.r):
            nxt = self.r[self.pos]
            if nxt == '{':
                closing = self.r.find('}', self.pos + 1)
                if closing < 0:
                    raise TooComplexRegexp()
                self.pos = closing + 1
                group = self.unknown()
                if self.pos >= len(self.r):
                    return group
                nxt = self.r[self.pos]
            if nxt in '*+?':
                self.pos += 1
                return self.optional(group, nxt)
        return group

    def atom(self):
        r = self.r
        if self.pos >= len(r):
            return self.literal('')
        c = r[self.pos]
        if c == '(':
            self.pos += 1
            if self.char_at(self.pos) == '?':
                self.pos += 1
                if self.char_at(self.pos) != ':':
                    raise TooComplexRegexp()
                self.pos += 1
            group = self.disjunction()
            if self.char_at(self.pos) != ')':
                raise TooComplexRegexp()
            self.pos += 1
            return group
        if c == '[':
            return self.square_bracket_group()
        if c == '\\':
            self.pos += 1
            return self.char_literal(self.escape())
        if c == '.':
            self.pos += 1
            return self.unknown()
        start = self.pos
        while self.pos < len(r) and r[self.pos] not in self._non_literal:
            self.pos += 1
        if start + 1 < self.pos and self.pos < len(r) and r[self.pos] == '?':
            self.pos -= 1
        return self.literal(r[start:self.pos])

    def square_bracket_group(self):
        self.pos += 1
        start = self.pos
        options = []
        while True:
            c1 = self.char_at(self.pos)
            self.pos += 1
            if c1 == ']':
                break
            if c1 == '-' and self.pos != start + 1 and self.char_at(self.pos) != ']':
                last = options[-1] if options else None
                nxt = self.char_at(self.pos)
                self.pos += 1
                if options is None or last is None or nxt == '\\' or ord(nxt) - ord(last) > MAX_CHAR_RANGE_WIDTH:
                    options = None
                if options is not None:
                    for c in range(ord(last) + 1, ord(nxt) + 1):
                        options.append(chr(c))
            elif c1 == '^':
                options = None
            elif c1 == '[':
                raise TooComplexRegexp()
            else:
                simple = self.escape() if c1 == '\\' else c1
                if options is not None:
                    options.append(simple)
            if options is not None and len(options) > MAX_CHAR_RANGE_WIDTH:
                options = None
        if options is None:
            return self.unknown()
        comps = [self.char_literal(c) for c in options]
        if not comps:
            raise TooComplexRegexp()
        return comps[0] if len(comps) == 1 else self.handle_or(comps)

    def char_literal(self, c):
        return self.unknown() if c is None else self.literal(c)

    def escape(self):
        nxt = self.char_at(self.pos)
        self.pos += 1
        if nxt in '0xucpP':
            raise TooComplexRegexp()
        if is_letter_or_digit(nxt):
            return None
        return nxt


class _PossibleValuesParser(_RegexpParser):

    def handle_concatenation(self, left, right):
        return [a + b for a in left for b in right]

    def handle_or(self, comps):
        out = []
        for c in comps:
            out.extend(c)
        return out

    def optional(self, group, op):
        if op == '?':
            return [''] + group
        raise TooComplexRegexp()

    def unknown(self):
        raise TooComplexRegexp()

    def literal(self, lit):
        return [lit]


def get_possible_regexp_values(regexp):
    """All strings that the given regexp can ever match, or None if they
    can't be enumerated."""
    try:
        p = _PossibleValuesParser(regexp)
        vals = p.disjunction()
        if p.pos != len(p.r):
            return None
        return frozenset(vals)
    except (TooComplexRegexp, RecursionError):
        return None


class StringMatcher(StringMatcherBase):

    __slots__ = ()

    def __init__(self, pattern, is_regexp, case_sensitive):
        self.pattern = pattern
        self.case_sensitive = case_sensitive
        self.is_regexp = is_regexp
        self.compiled = None
        self.cache = None
        self.value = self.value_lower = None
        self.values = None
        self.possible_values = None
        if not is_regexp or pattern == '\\0':
            self._set_equals(pattern)
            return
        # Java compiles the pattern here to check that it is well formed, we only
        # translate it (compiling with the regex module is slow) and compile lazily
        jregex.translate(pattern)
        pv = get_possible_regexp_values(pattern)
        if pv is not None:
            if len(pv) == 1:
                self._set_equals(next(iter(pv)))
                return
            self.kind = KIND_SET
            self.possible_values = pv
            self.values = pv if case_sensitive else frozenset(v.lower() for v in pv)
            return
        self.kind = KIND_REGEX
        self.possible_values = None
        self.cache = {}

    def _set_equals(self, value):
        self.kind = KIND_EQUALS
        self.value = value
        self.value_lower = value.lower()
        self.possible_values = frozenset((value,))

    def matches(self, s):
        if len(s) > MAX_MATCH_LENGTH:
            return False
        k = self.kind
        if k == KIND_EQUALS:
            if self.case_sensitive:
                return s == self.value
            return s == self.value or s.lower() == self.value_lower
        if k == KIND_SET:
            if self.case_sensitive:
                return s in self.values
            return s.lower() in self.values
        r = self.cache.get(s)
        if r is None:
            r = self._regex_match(s)
        return r

    def _regex_match(self, s):
        comp = self.compiled
        if comp is None:
            comp = self.compiled = jregex.compile(self.pattern, 0 if self.case_sensitive else jregex.IGNORECASE)
        r = comp.fullmatch(s) is not None
        c = self.cache
        if len(c) > 50000:
            c.clear()
        c[s] = r
        return r

    def matches_lower(self, s, s_lower):
        """Like matches() but with the lowercase version of s precomputed."""
        if len(s) > MAX_MATCH_LENGTH:
            return False
        k = self.kind
        if k == KIND_EQUALS:
            if self.case_sensitive:
                return s == self.value
            return s_lower == self.value_lower
        if k == KIND_SET:
            if self.case_sensitive:
                return s in self.values
            return s_lower in self.values
        return self.matches(s)

    def get_possible_values(self):
        return self.possible_values

    def __repr__(self):
        return 'StringMatcher(%r, regexp=%s, cs=%s)' % (self.pattern, self.is_regexp, self.case_sensitive)


_interned = {}

_STATE = ('pattern', 'value', 'value_lower', 'values', 'compiled', 'cache', 'possible_values', 'kind', 'case_sensitive',
          'is_regexp')


def _state(m):
    """(pickling, see langtool.patterns.rulecache) the state of a matcher"""
    return tuple(getattr(m, n) for n in _STATE)


def _interned_matcher(state):
    """(unpickling) the interned matcher with the pattern, regexp flag and
    case sensitivity of state (the one of this process if there is one,
    as when loading rules from XML), else a matcher with the state"""
    key = (state[0], state[9], state[8])
    m = _interned.get(key)
    if m is None:
        m = StringMatcher.__new__(StringMatcher)
        for n, v in zip(_STATE, state):
            setattr(m, n, v)
        m = _interned.setdefault(key, m)
    return m


def create(pattern, is_regexp, case_sensitive):
    key = (pattern, is_regexp, case_sensitive)
    m = _interned.get(key)
    if m is None:
        m = _interned[key] = StringMatcher(pattern, is_regexp, case_sensitive)
    return m


def regexp(pattern):
    return create(pattern, True, True)
