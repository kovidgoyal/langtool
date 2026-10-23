"""Port of org.languagetool.rules.patterns.PatternRuleMatcherTest"""

import pytest

from langtool.patterns import match as M
from langtool.patterns.match import Match
from langtool.patterns.matcher import PatternRuleMatcher
from langtool.patterns.pattern_token import PatternToken
from langtool.patterns.rules import PatternRule
from langtool.rules.base import RuleMatch


@pytest.fixture(scope='module')
def env(demo_lt, demo_language):
    return demo_lt, demo_language


class Helper:
    def __init__(self, lt, lang):
        self.lt = lt
        self.lang = lang

    def get_matches(self, text, matcher):
        return matcher.match(self.lt.get_analyzed_sentence(text))

    def get_pattern_rule(self, tokens):
        if isinstance(tokens, str):
            tokens = [PatternToken(part, False, False, False) for part in tokens.split(' ')]
        return PatternRule('', self.lang, tokens, 'my description', 'my message', 'short message')

    def get_matcher(self, *tokens):
        return PatternRuleMatcher(self.get_pattern_rule(list(tokens)), False)

    def assert_no_match(self, text, matcher):
        assert len(self.get_matches(text, matcher)) == 0, text

    def assert_partial_match(self, text, matcher):
        matches = self.get_matches(text, matcher)
        assert len(matches) == 1, text
        assert matches[0].from_pos > 0 or matches[0].to_pos < len(text), \
            "Expected partial match, got '%s' for '%s'" % (matches[0], text)

    def assert_complete_match(self, text, matcher):
        matches = self.get_matches(text, matcher)
        assert len(matches) == 1, 'Got matches: %r for %r' % (matches, text)
        assert matches[0].from_pos == 0, 'Wrong start position'
        assert matches[0].to_pos == len(text), 'Wrong end position'


def assert_position(match, expected_from, expected_to):
    assert match.from_pos == expected_from, 'Wrong start position'
    assert match.to_pos == expected_to, 'Wrong end position'


def make_element(token):
    return PatternToken(token, False, False, False)


def new_match():
    return Match(None, None, False, None, None, M.NONE, False, False, M.INCLUDE_NONE)


@pytest.fixture
def h(demo_lt, demo_language):
    return Helper(demo_lt, demo_language)


def test_match(h):
    matcher = PatternRuleMatcher(h.get_pattern_rule('my test'), False)
    h.assert_partial_match('This is my test.', matcher)
    h.assert_no_match('This is no test.', matcher)


def test_zero_min_occurrences(h):
    b = make_element('b')
    b.set_min_occurrence(0)
    matcher = h.get_matcher(make_element('a'), b, make_element('c'))  # regex syntax: a b? c
    h.assert_no_match('b a', matcher)
    h.assert_no_match('c a b', matcher)
    h.assert_partial_match('b a c', matcher)
    h.assert_partial_match('a c b', matcher)
    h.assert_no_match('a b b c', matcher)
    h.assert_complete_match('a c', matcher)
    h.assert_complete_match('a b c', matcher)
    h.assert_no_match('a X c', matcher)
    matches = h.get_matches('a b c FOO a b c FOO a c a b c', matcher)
    assert len(matches) == 4
    assert_position(matches[0], 0, 5)
    assert_position(matches[1], 10, 15)
    assert_position(matches[2], 20, 23)
    assert_position(matches[3], 24, 29)


def test_two_zero_min_occurrences(h):
    b1 = make_element('ba')
    b1.set_min_occurrence(0)
    b2 = make_element('bb')
    b2.set_min_occurrence(0)
    matcher = h.get_matcher(make_element('a'), b1, b2, make_element('c'))  # regex syntax: a (ba)? (bb)? c
    h.assert_no_match('ba a', matcher)
    h.assert_no_match('c a bb', matcher)
    h.assert_partial_match('z a c', matcher)
    h.assert_partial_match('a c z', matcher)
    h.assert_no_match('a ba ba c', matcher)
    h.assert_complete_match('a ba bb c', matcher)
    h.assert_complete_match('a ba c', matcher)
    h.assert_complete_match('a bb c', matcher)
    h.assert_complete_match('a c', matcher)
    h.assert_no_match('a X c', matcher)
    matches = h.get_matches('a ba c FOO a bb c FOO a c a ba bb c', matcher)
    assert len(matches) == 4
    assert_position(matches[0], 0, 6)
    assert_position(matches[1], 11, 17)
    assert_position(matches[2], 22, 25)
    assert_position(matches[3], 26, 35)


def test_zero_min_occurrences2(h):
    b = make_element('b')
    b.set_min_occurrence(0)
    # regex syntax: a b? c d e
    matcher = h.get_matcher(make_element('a'), b, make_element('c'), make_element('d'), make_element('e'))
    h.assert_complete_match('a b c d e', matcher)
    h.assert_complete_match('a c d e', matcher)
    h.assert_no_match('a d', matcher)
    h.assert_no_match('a c b d', matcher)
    h.assert_no_match('a c b d e', matcher)


def test_zero_min_occurrences3(h):
    c = make_element('c')
    c.set_min_occurrence(0)
    # regex syntax: a b c? d e
    matcher = h.get_matcher(make_element('a'), make_element('b'), c, make_element('d'), make_element('e'))
    h.assert_complete_match('a b c d e', matcher)
    h.assert_complete_match('a b d e', matcher)
    h.assert_partial_match('a b c d e x', matcher)
    h.assert_partial_match('x a b c d e', matcher)
    h.assert_no_match('a b c e d', matcher)
    h.assert_no_match('a c b d e', matcher)


def test_zero_min_occurrences4(h):
    a = make_element('a')
    a.set_min_occurrence(0)
    c = make_element('c')
    c.set_min_occurrence(0)
    # regex syntax: a? b c? d e
    matcher = h.get_matcher(a, make_element('b'), c, make_element('d'), make_element('e'))
    matches = h.get_matches('a b c d e', matcher)
    assert len(matches) == 1  # just the longest match...
    assert_position(matches[0], 0, 9)


def test_zero_min_occurrences_with_empty_element(h):
    b = make_element(None)
    b.set_min_occurrence(0)
    matcher = h.get_matcher(make_element('a'), b, make_element('c'))  # regex syntax: a .? c
    h.assert_no_match('b a', matcher)
    h.assert_no_match('c a b', matcher)
    h.assert_partial_match('b a c', matcher)
    h.assert_partial_match('a c b', matcher)
    h.assert_no_match('a b b c', matcher)
    h.assert_complete_match('a c', matcher)
    h.assert_complete_match('a b c', matcher)
    h.assert_complete_match('a X c', matcher)
    matches = h.get_matches('a b c FOO a X c', matcher)
    assert len(matches) == 2
    assert_position(matches[0], 0, 5)
    assert_position(matches[1], 10, 15)


def test_zero_min_occurrences_with_suggestion(h):
    b = make_element('b')
    b.set_min_occurrence(0)
    tokens = [make_element('a'), b, make_element('c')]  # regex: a b? c
    rule = PatternRule('', h.lang, tokens, 'my description', '<suggestion>\\1 \\2 \\3</suggestion>', 'short message')
    matcher = PatternRuleMatcher(rule, False)
    # we need to add this line to trigger proper replacement but I am not sure why :(
    rule.add_suggestion_match(new_match())
    matches = h.get_matches('a b c', matcher)
    assert matches[0].suggested_replacements == ['a b c']
    matches2 = h.get_matches('a c', matcher)
    assert matches2[0].suggested_replacements == ['a c']


@pytest.mark.skip(reason='min can only be 0 or 1 so far (@Ignore in Java)')
def test_two_min_occurrences(h):
    b = make_element('b')
    b.set_min_occurrence(2)
    b.set_max_occurrence(3)
    matcher = h.get_matcher(make_element('a'), b, make_element('c'))  # regex: a b{2,3} c
    h.assert_complete_match('a b b c', matcher)
    h.assert_complete_match('a b b b c', matcher)
    h.assert_no_match('a c', matcher)
    h.assert_no_match('a b c', matcher)


def test_zero_min_two_max_occurrences(h):
    b = make_element('b')
    b.set_min_occurrence(0)
    b.set_max_occurrence(2)
    matcher = h.get_matcher(make_element('a'), b, make_element('c'))
    h.assert_complete_match('a c', matcher)
    h.assert_complete_match('a  b c', matcher)
    h.assert_complete_match('a  b b c', matcher)
    h.assert_no_match('a b b b c', matcher)


def test_two_max_occurrences_with_any_token(h):
    any_token = make_element(None)
    any_token.set_max_occurrence(2)
    matcher = h.get_matcher(make_element('a'), any_token, make_element('c'))
    h.assert_complete_match('a b c', matcher)
    h.assert_complete_match('a b b c', matcher)
    h.assert_no_match('a b b b c', matcher)


def test_three_max_occurrences_with_any_token(h):
    any_token = make_element(None)
    any_token.set_max_occurrence(3)
    matcher = h.get_matcher(make_element('a'), any_token, make_element('c'))
    h.assert_complete_match('a b c', matcher)
    h.assert_complete_match('a b b c', matcher)
    h.assert_complete_match('a b b b c', matcher)
    h.assert_no_match('a b b b b c', matcher)


def test_zero_min_two_max_occurrences_with_any_token(h):
    any_token = make_element(None)
    any_token.set_min_occurrence(0)
    any_token.set_max_occurrence(2)
    matcher = h.get_matcher(make_element('a'), any_token, make_element('c'))
    h.assert_no_match('a b', matcher)
    h.assert_no_match('b c', matcher)
    h.assert_no_match('c', matcher)
    h.assert_no_match('a', matcher)
    h.assert_complete_match('a c', matcher)
    h.assert_complete_match('a x c', matcher)
    h.assert_complete_match('a x x c', matcher)
    h.assert_no_match('a x x x c', matcher)


def test_two_max_occurrences(h):
    b = make_element('b')
    b.set_max_occurrence(2)
    matcher = h.get_matcher(make_element('a'), b)
    h.assert_no_match('a a', matcher)
    h.assert_complete_match('a b', matcher)
    h.assert_complete_match('a b b', matcher)
    h.assert_partial_match('a b c', matcher)
    h.assert_partial_match('a b b c', matcher)
    h.assert_partial_match('x a b b', matcher)

    matches1 = h.get_matches('a b b b', matcher)
    assert len(matches1) == 1
    assert_position(matches1[0], 0, 5)

    matches2 = h.get_matches('a b b b foo a b b', matcher)
    assert len(matches2) == 2
    assert_position(matches2[0], 0, 5)
    assert_position(matches2[1], 12, 17)


def test_three_max_occurrences(h):
    b = make_element('b')
    b.set_max_occurrence(3)
    matcher = h.get_matcher(make_element('a'), b)  # regex: a b{1,3}
    h.assert_no_match('a a', matcher)
    h.assert_complete_match('a b', matcher)
    h.assert_complete_match('a b b', matcher)
    h.assert_complete_match('a b b b', matcher)
    h.assert_partial_match('a b b b b', matcher)

    matches1 = h.get_matches('a b b b b', matcher)
    assert len(matches1) == 1
    assert_position(matches1[0], 0, 7)


def test_optional_without_explicit_marker(h):
    a = make_element('a')
    b = make_element('b')
    b.set_min_occurrence(0)
    c = make_element('c')
    matcher = h.get_matcher(a, b, c)  # regex syntax: a .? c

    matches1 = h.get_matches('A B C ZZZ', matcher)
    assert len(matches1) == 1
    assert_position(matches1[0], 0, 5)

    matches2 = h.get_matches('A C ZZZ', matcher)
    assert len(matches2) == 1
    assert_position(matches2[0], 0, 3)


def test_optional_with_explicit_marker(h):
    a = make_element('a')
    a.inside_marker = True
    b = make_element('b')
    b.set_min_occurrence(0)
    b.inside_marker = True
    c = make_element('c')
    c.inside_marker = False
    matcher = h.get_matcher(a, b, c)  # regex syntax: (a .?) c

    matches1 = h.get_matches('A B C ZZZ', matcher)
    assert len(matches1) == 1
    assert_position(matches1[0], 0, 3)

    matches2 = h.get_matches('A C ZZZ', matcher)
    assert len(matches2) == 1
    assert_position(matches2[0], 0, 1)


def test_optional_any_token_with_explicit_marker(h):
    a = make_element('a')
    a.inside_marker = True
    b = make_element(None)
    b.set_min_occurrence(0)
    b.inside_marker = True
    c = make_element('c')
    c.inside_marker = False
    matcher = h.get_matcher(a, b, c)  # regex syntax: (a .?) c

    matches1 = h.get_matches('A x C ZZZ', matcher)
    assert len(matches1) == 1
    assert_position(matches1[0], 0, 3)

    matches2 = h.get_matches('A C ZZZ', matcher)
    assert len(matches2) == 1
    assert_position(matches2[0], 0, 1)


def test_optional_any_token_with_explicit_marker2(h):
    a = make_element('the')
    a.inside_marker = True
    b = make_element(None)
    b.set_min_occurrence(0)
    b.inside_marker = True
    c = make_element('bike')
    c.inside_marker = False
    matcher = h.get_matcher(a, b, c)  # regex syntax: (a .?) c

    matches1 = h.get_matches('the nice bike ZZZ', matcher)
    assert len(matches1) == 1
    assert_position(matches1[0], 0, 8)

    matches2 = h.get_matches('the bike ZZZ', matcher)
    assert len(matches2) == 1
    assert_position(matches2[0], 0, 3)


def test_unlimited_max_occurrences(h):
    b = make_element('b')
    b.set_max_occurrence(-1)
    matcher = h.get_matcher(make_element('a'), b, make_element('c'))
    h.assert_no_match('a c', matcher)
    h.assert_no_match('a b', matcher)
    h.assert_no_match('b c', matcher)
    h.assert_complete_match('a b c', matcher)
    h.assert_complete_match('a b b c', matcher)
    h.assert_complete_match('a b b b b b b b b b b b b b b b b b b b b b b b b b c', matcher)


def test_max_two_and_three_occurrences(h):
    a = make_element('a')
    a.set_max_occurrence(2)
    b = make_element('b')
    b.set_max_occurrence(3)
    matcher = h.get_matcher(a, b)  # regex: a{1,2} b{1,3}
    h.assert_complete_match('a b', matcher)
    h.assert_complete_match('a b b', matcher)
    h.assert_complete_match('a b b b', matcher)
    h.assert_no_match('a a', matcher)
    h.assert_no_match('a x b b b', matcher)
    matches2 = h.get_matches('a a b', matcher)
    assert len(matches2) == 1  # just the longest match
    assert_position(matches2[0], 0, 5)

    matches3 = h.get_matches('a a b b', matcher)
    assert len(matches3) == 1
    assert_position(matches3[0], 0, 7)  # again, only the longest match

    matches4 = h.get_matches('a a b b b', matcher)
    assert len(matches4) == 1
    assert_position(matches4[0], 0, 9)


def test_infinite_skip(h):
    a = make_element('a')
    a.set_skip_next(-1)
    matcher = h.get_matcher(a, make_element('b'))
    h.assert_complete_match('a b', matcher)
    h.assert_complete_match('a x b', matcher)
    h.assert_complete_match('a x x b', matcher)
    h.assert_complete_match('a x x x b', matcher)


def test_infinite_skip_with_match_reference(h):
    ab = PatternToken('a|b', False, True, False)
    ab.set_skip_next(-1)
    c = make_element('\\0')
    match = new_match()
    match.token_ref = 0
    match.in_message_only = True
    c.token_reference = match
    matcher = h.get_matcher(ab, c)
    h.assert_complete_match('a a', matcher)
    h.assert_complete_match('b b', matcher)
    h.assert_complete_match('a x a', matcher)
    h.assert_complete_match('b x b', matcher)
    h.assert_complete_match('a x x a', matcher)
    h.assert_complete_match('b x x b', matcher)

    h.assert_no_match('a b', matcher)
    h.assert_no_match('b a', matcher)
    h.assert_no_match('b x a', matcher)
    h.assert_no_match('b x a', matcher)
    h.assert_no_match('a x x b', matcher)
    h.assert_no_match('b x x a', matcher)

    matches = h.get_matches('a foo a and b foo b', matcher)
    assert len(matches) == 2
    assert_position(matches[0], 0, 7)
    assert_position(matches[1], 12, 19)

    matches2 = h.get_matches('xx a b x x x b a', matcher)
    assert len(matches2) == 1
    assert_position(matches2[0], 3, 16)


def test_no_match_reference_recursion(h):
    # \n in rule messages refers to matches, but if match text contains \n this should not be resolved
    rule = PatternRule('MATCH_REFERENCERE_CURSION_DEMO', h.lang,
                       [PatternToken('\\p{Punct}', False, True, False), PatternToken('\\d+', False, True, False)],
                       '', 'Here come the match references: \\1\\2. This is the end', '')
    matcher = PatternRuleMatcher(rule, False)
    matches = h.get_matches(':42', matcher)
    assert len(matches) == 1
    assert matches[0].message == 'Here come the match references: :42. This is the end'
    matches2 = h.get_matches('\\42', matcher)
    assert len(matches2) == 1
    assert matches2[0].message == 'Here come the match references: \\42. This is the end'


def test_equals(demo_language):
    rule1 = PatternRule('id1', demo_language, [], 'desc1', 'msg1', 'short1')
    rm1 = RuleMatch(rule1, None, 0, 1, 'message')
    rm2 = RuleMatch(rule1, None, 0, 1, 'message')
    assert rm1 == rm2
    rm3 = RuleMatch(rule1, None, 0, 9, 'message')
    assert not rm1 == rm3
    assert not rm2 == rm3


# --- Port of org.languagetool.rules.patterns.AbstractPatternRulePerformerTest

def _token_readings(token, chunk_tag):
    from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
    from langtool.chunking import ChunkTag
    atr = AnalyzedTokenReadings(AnalyzedToken(token, 'pos', 'lemma'), 0)
    if chunk_tag is not None:
        atr.set_chunk_tags([ChunkTag(chunk_tag)])
    return [atr]


def _performer(rule):
    from langtool.patterns.matcher import AbstractPatternRulePerformer
    from langtool.patterns.unifier import UnifierConfiguration
    return AbstractPatternRulePerformer(rule, UnifierConfiguration())


def test_test_all_readings(demo_language):
    from langtool.patterns.matcher import PatternTokenMatcher
    pt1 = PatternToken('foo', False, False, False)
    rule = PatternRule('FAKE', demo_language, [pt1], 'descr', 'message', 'short')
    elem_matcher = PatternTokenMatcher(pt1)
    p = _performer(rule)
    assert p.test_all_readings(_token_readings('foo', None), elem_matcher, None, 0, 0, 0)
    assert not p.test_all_readings(_token_readings('bar', None), elem_matcher, None, 0, 0, 0)
    assert p.test_all_readings(_token_readings('foo', 'myChunk'), elem_matcher, None, 0, 0, 0)
    assert p.test_all_readings(_token_readings('foo', 'otherChunk'), elem_matcher, None, 0, 0, 0)


def test_test_all_readings_with_chunks(demo_language):
    from langtool.chunking import ChunkTag
    from langtool.patterns.matcher import PatternTokenMatcher
    chunk_pt = PatternToken(None, False, False, False)
    chunk_pt.chunk_tag = ChunkTag('myChunk')
    rule = PatternRule('FAKE', demo_language, [chunk_pt], 'descr', 'message', 'short')
    elem_matcher = PatternTokenMatcher(chunk_pt)
    p = _performer(rule)
    assert not p.test_all_readings(_token_readings('bar', None), elem_matcher, None, 0, 0, 0)
    assert p.test_all_readings(_token_readings('bar', 'myChunk'), elem_matcher, None, 0, 0, 0)
    assert not p.test_all_readings(_token_readings('bar', 'otherChunk'), elem_matcher, None, 0, 0, 0)
