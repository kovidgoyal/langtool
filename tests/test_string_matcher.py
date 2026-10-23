"""Port of org.languagetool.rules.patterns.StringMatcherTest

The Java test compares StringMatcher with java.util.regex at runtime. As
there's no JVM here, the java.util.regex results for all the strings the Java
test checks were computed once with a small Java program and stored in
tests/data/java_string_matcher.json.gz (keys: 'consistency' = list of
[regexp, input, String.matches(regexp), Pattern.compile(regexp,
CASE_INSENSITIVE|UNICODE_CASE).matcher(input).matches()], 'specialized' =
bitmaps of the results for specializedSequenceMatcherIsConsistent).
"""

import gzip
import json
import os

import pytest

from langtool import jregex
from langtool.patterns import string_matcher
from langtool.patterns.string_matcher import StringMatcher, get_possible_regexp_values

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'java_string_matcher.json.gz')


@pytest.fixture(scope='module')
def java():
    with gzip.open(DATA, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    cons = {(rx, s): (cs, ci) for rx, s, cs, ci in data['consistency']}
    return {'consistency': cons, 'specialized': data['specialized']}


def _mutations(s):
    """trySomeMutations of the Java test"""
    out = [s]
    for i in range(len(s)):
        out.append(s[:i] + s[i + 1:])
        out.append(s[:i] + 'x' + s[i + 1:])
    out.append('a' + s)
    out.append(s + 'a')
    return out


def _try_some_mutations(java, regexp, s):
    for m in _mutations(s):
        java_cs, java_ci = java['consistency'][(regexp, m)]
        assert StringMatcher(regexp, True, True).matches(m) == java_cs, (regexp, m)
        assert string_matcher.regexp(regexp).matches(m) == java_cs, (regexp, m)
        assert string_matcher.create(regexp, True, False).matches(m) == java_ci, (regexp, m)


def test_syntax_is_validated():
    # java.util.regex rejects 'tú|?' with a PatternSyntaxException
    with pytest.raises(jregex.JavaRegexError):
        string_matcher.regexp('tú|?')


AZ = [chr(c) for c in range(ord('a'), ord('z') + 1)]

POSSIBLE_VALUES = [
    ('x.*', None), ('x+', None), ('a.c', None), ('a{2}', None),
    ('[a-z]', AZ), ('[^a]', None), ('a[a-z]', ['a' + c for c in AZ]), ('(?=a)', None),
    # A 26-letter range like [a-z] is enumerated, see StringMatcher.MAX_CHAR_RANGE_WIDTH.
    ('[A-Z]', [c.upper() for c in AZ]),
    # A range wider than MAX_CHAR_RANGE_WIDTH (64) still isn't enumerated.
    ('[ -~]', None),
    # even a small, enumerable class stays unenumerable once it's repeated
    ('[a-z]+', None), ('[a-z]*', None),
    ('', ['']), ('^x$', ['x']), ('aa|bb', ['aa', 'bb']), ('aa', ['aa']), ('aa|', ['aa', '']),
    ('aa?', ['aa', 'a']), ('[abc]', ['a', 'b', 'c']), ('a(bc)?', ['a', 'abc']), ('a(b|c)', ['ab', 'ac']),
    ('(a|b)(c|d)', ['ac', 'ad', 'bc', 'bd']), ('\\.|\\-', ['.', '-']), ('[\\.\\-]', ['.', '-']),
    ('are|is|w(?:as|ere)', ['are', 'is', 'was', 'were']), ('[,;:-]', [',', ';', ':', '-']),
    ('(?:[-‑])', ['-', '‑']), ('[0-9]', [str(i) for i in range(10)]),
    ('[0-9X]', [str(i) for i in range(10)] + ['X']), ('tú|\\?', ['tú', '?']), ('NN|PRP\\$', ['NN', 'PRP$']),
    ('\\\\b', ['\\b']),
]


@pytest.mark.parametrize('regexp,expected', POSSIBLE_VALUES, ids=[r for r, _ in POSSIBLE_VALUES])
def test_get_possible_values(java, regexp, expected):
    assert get_possible_regexp_values(regexp) == (None if expected is None else set(expected))
    for s in expected or []:
        _try_some_mutations(java, regexp, s)
    _try_some_mutations(java, regexp, regexp)


REQUIRED_SUBSTRINGS = [
    ('', '[]'), ('foo', '[foo]'), ('foo|bar', None), ('\\w', None), ('PRP.+', '[PRP)'), ('.*PRP.+', '(PRP)'),
    ('.*PRP', '(PRP]'), ('.+PRP', '(PRP]'), ('a.+b', '[a, b]'), ('a.*b', '[a, b]'),
    ('\\bZünglein an der (Wage)\\b', '[Zünglein an der Wage]'),
    ('(ökumenische[rn]?) (.*Messen?)', '[ökumenische,  , Messe)'),
    ('(CO2|Kohlendioxid|Schadstoff)\\-?Emulsion(en)?', '(Emulsion)'),
    ('\\bder (\\w*(Verkehrs|Verbots|Namens|Hinweis|Warn)schild)', '[der , schild]'),
    ('\\bvon Seiten\\b', '[von Seiten]'),
    ('((\\-)?[0-9]+[0-9.,]{0,15})(?:[\\s  ]+)(°[^CFK])', '(°)'),
    ('\\b(teils\\s[^,]+\\steils)\\b', '[teils, teils]'),
    ('§ ?(\\d+[a-z]?)', '[§)'),
]


@pytest.mark.parametrize('regexp,expected', REQUIRED_SUBSTRINGS, ids=[r for r, _ in REQUIRED_SUBSTRINGS])
def test_required_substrings(java, regexp, expected):
    # The Python port has no StringMatcher.getRequiredSubstrings() (a pure
    # optimization of the Java implementation), so only the consistency of
    # the matcher with java.util.regex on the strings derived from the
    # expected substrings is checked.
    _try_some_mutations(java, regexp, regexp)
    if expected is not None:
        _try_some_mutations(java, regexp, expected)
        _try_some_mutations(java, regexp, expected[1:-1])
        substrings = expected[1:-1].split(', ')
        for sep in ('', 'a', '0', ' '):
            j = sep.join(substrings)
            _try_some_mutations(java, regexp, j)
            _try_some_mutations(java, regexp, sep + j)
            _try_some_mutations(java, regexp, j + sep)


def test_no_soe_on_long_disjunction():
    count = 100_000
    pattern = '|'.join('a%d' % i for i in range(count))
    matcher = string_matcher.create(pattern, True, True)
    for i in range(count):
        assert matcher.matches('a%d' % i)
        assert not matcher.matches('b%d' % i)


SPECIALIZED = [
    '[a-z]+|,', "['-].+", "[^'-].+", '\\p{L}', '\\p{Ll}.+', '\\p{Lu}.+', '[a-z]+', '\\d+',
    '[1234567890]{1,2}', '[1234567890][1234567890., ]+[1234567890]', '\\p{P}\\p{P}+', '[_~°]+',
    '0o[0-7]+', '0x[0-9A-Fa-f]+', '[A-Z]+\\d+', '#.+', '@.+', '.+e', '.+[aei]sses', 'a.*b', 'a.+b',
    'aa?', 'a{2,3}b', '[a-c]?[0-9]*x', '(?-i)Han', '\\.|\\-', '[\\d ,\\.]+', '−?[\\d .,]+%?',
    '[a-z]+|,|[0-9]', '\\p{Lu}.*', '\\w+', '\\d?', 'a|', '|a', '\\p{N}+', '[^a-z]+', '[abc]*d',
    'x*', 'x+', 'x?', '[^\\d]+',
]
ALPHABET = ['a', 'A', 'b', 'B', '1', '-', '.', ' ', 'à', 'À', 'ç', 'Ç', '·', 'é', 'É', '_', 'x', 'X']


def _samples():
    out = ['']
    for c1 in ALPHABET:
        out.append(c1)
        for c2 in ALPHABET:
            out.append(c1 + c2)
            for c3 in ALPHABET:
                out.append(c1 + c2 + c3)
    return out


@pytest.mark.parametrize('regexp', SPECIALIZED)
@pytest.mark.parametrize('case_sensitive', [True, False])
def test_specialized_sequence_matcher_is_consistent(java, regexp, case_sensitive):
    """The matcher must accept exactly the same strings as java.util.regex,
    for both case-sensitive and case-insensitive matching."""
    bits = java['specialized'][regexp + ('\x00cs' if case_sensitive else '\x00ci')]
    matcher = string_matcher.create(regexp, True, case_sensitive)
    wrong = []
    for sample, bit in zip(_samples(), bits):
        if matcher.matches(sample) != (bit == '1'):
            wrong.append((sample, bit == '1'))
    assert not wrong, "regexp '%s', caseSensitive=%s, (input, java result): %r" % (
        regexp, case_sensitive, wrong[:20])
