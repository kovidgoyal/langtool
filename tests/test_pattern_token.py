"""Port of org.languagetool.rules.patterns.PatternTokenTest"""

import pytest

from langtool.analysis import (AnalyzedToken, SENTENCE_START_TAGNAME, SENTENCE_END_TAGNAME,
                               PARAGRAPH_END_TAGNAME)
from langtool.patterns.pattern_token import PatternToken, PosToken, UNKNOWN_TAG


def pos_token(tag, regexp, negation):
    """Java: new PatternToken.PosToken(posTag, regExp, negation)"""
    return PosToken(tag, negation, regexp=regexp)


class PatternTokenBuilder:
    """Minimal port of org.languagetool.rules.patterns.PatternTokenBuilder"""

    def __init__(self):
        self._token = None
        self._pos_tag = None
        self._marker = True
        self._inflected = False
        self._case_sensitive = False
        self._regexp = False
        self._negation = False
        self._min = 1
        self._max = 1
        self._skip = 0

    def token(self, t):
        self._token = t
        return self

    def cs_token(self, t):
        self._token = t
        self._case_sensitive = True
        return self

    def token_regex(self, t):
        self._token = t
        self._regexp = True
        return self

    def cs_token_regex(self, t):
        self._token = t
        self._regexp = True
        self._case_sensitive = True
        return self

    def pos(self, tag, regexp=False):
        self._pos_tag = tag
        self._regexp = regexp
        return self

    def min(self, v):
        self._min = v
        return self

    def max(self, v):
        self._max = v
        return self

    def negate(self):
        self._negation = True
        return self

    def build(self):
        pt = PatternToken(self._token, self._case_sensitive, self._regexp, self._inflected)
        if self._pos_tag is not None:
            pt.pos_token = PosToken(self._pos_tag, False, regexp=self._regexp)
        pt.set_min_occurrence(self._min)
        pt.set_max_occurrence(self._max)
        pt.negation = self._negation
        pt.set_skip_next(self._skip)
        pt.inside_marker = self._marker
        return pt


def test_sentence_start():
    pt = PatternToken('', False, False, False)
    pt.pos_token = pos_token(SENTENCE_START_TAGNAME, False, False)
    assert pt.is_sentence_start()
    pt.pos_token = pos_token(SENTENCE_START_TAGNAME, False, True)
    assert not pt.is_sentence_start()
    pt.pos_token = pos_token(SENTENCE_START_TAGNAME, True, False)
    assert pt.is_sentence_start()
    pt.pos_token = pos_token(SENTENCE_START_TAGNAME, True, True)
    assert not pt.is_sentence_start()

    pt2 = PatternToken('bla|blah', False, True, False)
    pt2.pos_token = pos_token('foo', True, True)
    assert not pt2.is_sentence_start()


def test_unknown_tag():
    pt1 = PatternToken('', False, False, False)
    pt1.pos_token = pos_token(UNKNOWN_TAG, False, False)
    pt2 = PatternToken('', False, False, False)
    pt2.pos_token = pos_token(UNKNOWN_TAG, False, True)
    pt3 = PatternToken('', False, False, False)
    pt3.pos_token = pos_token(UNKNOWN_TAG + '|VBG', True, False)
    pt4 = PatternToken('', False, False, False)
    pt4.pos_token = pos_token(UNKNOWN_TAG + '|VBG', True, True)
    pt5 = PatternToken('\\p{Ll}+', False, True, False)
    pt5.pos_token = pos_token(UNKNOWN_TAG, False, False)

    def check(an, expected):
        assert [p.is_matched(an) for p in (pt1, pt2, pt3, pt4, pt5)] == expected

    an = AnalyzedToken('schword', None, None)
    check(an, [True, False, True, False, True])
    # if the AnalyzedToken is in the set of readings that have non-null tags...
    an.has_no_pos_tag = False
    check(an, [False, True, False, True, False])

    an_sent_end = AnalyzedToken('schword', SENTENCE_END_TAGNAME, None)
    check(an_sent_end, [True, False, True, False, True])

    pt6 = PatternToken('\\p{Ll}+', False, True, False)
    pt6.pos_token = pos_token(SENTENCE_END_TAGNAME, False, False)
    assert pt6.is_matched(an_sent_end)

    pt7 = PatternToken('\\p{Ll}+', False, True, False)
    pt7.pos_token = pos_token(SENTENCE_END_TAGNAME + '|BLABLA', True, False)
    assert pt7.is_matched(an_sent_end)

    an_sent_end.has_no_pos_tag = False
    check(an_sent_end, [False, True, False, True, False])

    an_para_end = AnalyzedToken('schword', PARAGRAPH_END_TAGNAME, None)
    check(an_para_end, [True, False, True, False, True])
    an_para_end.has_no_pos_tag = False
    check(an_para_end, [False, True, False, True, False])

    an_with_pos = AnalyzedToken('schword', 'POS', None)
    check(an_with_pos, [False, True, False, True, False])


def test_negation():
    assert PatternTokenBuilder().token_regex('an?|the').negate().build().negation
    assert not PatternTokenBuilder().token_regex('an?|the').build().negation
    assert PatternTokenBuilder().pos('NNS').negate().build().negation
    assert not PatternTokenBuilder().pos('NNS').build().negation
    assert PatternTokenBuilder().token('text').negate().build().negation
    assert not PatternTokenBuilder().token('text').build().negation


def test_form_hints():
    token = PatternTokenBuilder().token_regex('an?|the|th[eo]se').build()
    assert token.calc_form_hints() == {'a', 'an', 'the', 'these', 'those'}

    token = PatternTokenBuilder().token('foo').build()
    assert token.calc_form_hints() == {'foo'}

    token = PatternTokenBuilder().token_regex('(foo)?.*').build()
    assert token.calc_form_hints() is None

    token = PatternTokenBuilder().cs_token_regex('a|b').build()
    assert token.calc_form_hints() == {'a', 'b'}

    token = PatternTokenBuilder().token('a').min(0).build()
    assert token.calc_form_hints() is None

    token = PatternTokenBuilder().token_regex('an|the').build()
    token.set_or_group_element(PatternTokenBuilder().token_regex('foo|bar').build())
    assert token.calc_form_hints() == {'an', 'the', 'foo', 'bar'}
    token.set_or_group_element(PatternTokenBuilder().token_regex('foo.*|bar').build())
    assert token.calc_form_hints() is None

    token = PatternTokenBuilder().token_regex('an|the').build()
    token.set_and_group_element(PatternTokenBuilder().token_regex('foo|an').build())
    assert token.calc_form_hints() == {'an'}


def test_pattern_token_builder():
    """PatternTokenBuilder (and PatternRuleBuilderHelper.pos/posRegex)"""
    from langtool.patterns.pattern_token import PatternTokenBuilder, pos, pos_regex
    t = PatternTokenBuilder().cs_token('need').match_inflected_forms().build()
    assert t.get_string() == 'need' and t.is_case_sensitive() and t.inflected and not t.is_regular_expression()
    t = PatternTokenBuilder().token_regex('solve(s|d)?').set_skip(3).build()
    assert t.is_regular_expression() and not t.is_case_sensitive() and t.skip == 3
    t = PatternTokenBuilder().pos('RB').min(0).build()
    assert t.get_pos_tag() == 'RB' and not t.is_pos_tag_regular_expression() and t.get_min_occurrence() == 0
    assert not t.test_string
    t = pos_regex('VB.*')
    assert t.get_pos_tag() == 'VB.*' and t.is_pos_tag_regular_expression()
    # as in Java, posRegex() also makes the (empty) token string a regular expression
    assert t.is_regular_expression()
    assert pos('PCT').get_pos_tag() == 'PCT'
    t = PatternTokenBuilder().token('x').negate().mark(False).set_is_white_space_before(True).build()
    assert t.negation and not t.inside_marker and t.whitespace_before and t.test_whitespace
    t = PatternTokenBuilder().pos_regex_with_string_exception('N.*', 'foo|bar').build()
    assert [e.get_string() for e in t.current_and_next_exceptions] == ['foo|bar']
    with pytest.raises(ValueError):
        PatternTokenBuilder().min(-1)
    with pytest.raises(ValueError):
        PatternTokenBuilder().token('x').min(2).build()
