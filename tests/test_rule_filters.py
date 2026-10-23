"""Ports of RuleMatchTest, RuleWithMaxFilterTest, SameRuleGroupFilterTest and
CleanOverlappingFilterTest (languagetool-core/src/test/java/org/languagetool/rules/)."""

import pytest

from langtool.analysis import AnalyzedSentence
from langtool.api import get_language
from langtool.language import Language
from langtool.languages import LANGUAGES
from langtool.patterns.rules import PatternRule
from langtool.rules import base
from langtool.rules.base import (Rule, RuleMatch, clean_overlapping_filter, rule_with_max_filter,
                                 same_rule_group_filter)


class FakeRule(Rule):
    """Port of org.languagetool.rules.FakeRule"""

    def __init__(self, rule_id='FAKE-RULE', tag=None):
        super().__init__()
        self.rule_id = rule_id
        if tag is not None:
            self.tags = [tag]

    def get_id(self):
        return self.rule_id

    def get_description(self):
        return '<none>'

    def match(self, sentence):
        return []


# --- RuleMatchTest -----------------------------------------------------------

class _TestRule(FakeRule):
    def __init__(self):
        super().__init__('TEST_RULE')

    def get_description(self):
        return 'test rule'



def test_trim_match_ends_keeps_whitespace_only_match():
    rule_match = RuleMatch(_TestRule(), None, 10, 13, 'msg')
    rule_match.set_original_error_str('   ')
    rule_match.set_suggested_replacement(' ')
    trimmed = rule_match.trim_match_ends()
    assert trimmed is rule_match
    assert trimmed.from_pos == 10
    assert trimmed.to_pos == 13
    assert trimmed.original_error_str == '   '
    assert trimmed.suggested_replacements[0] == ' '


def test_trim_match_ends_still_trims_common_tokens():
    rule_match = RuleMatch(_TestRule(), None, 10, 21, 'msg')
    rule_match.set_original_error_str('foo bar baz')
    rule_match.set_suggested_replacement('foo qux baz')
    trimmed = rule_match.trim_match_ends()
    assert trimmed.from_pos == 14
    assert trimmed.to_pos == 17
    assert trimmed.original_error_str == 'bar'
    assert trimmed.suggested_replacements[0] == 'qux'


def test_trim_match_ends_does_not_create_invalid_range_with_extra_whitespace():
    rule_match = RuleMatch(_TestRule(), None, 0, 9, 'msg')
    rule_match.set_original_error_str('fins  tot')
    rule_match.set_suggested_replacement('fins i tot')
    trimmed = rule_match.trim_match_ends()
    assert trimmed.from_pos == 0
    assert trimmed.to_pos == 5
    assert trimmed.from_pos < trimmed.to_pos


def test_rule_match_invalid_range():
    # RuleMatch constructor: "fromPos must be less than toPos"
    with pytest.raises(ValueError):
        RuleMatch(_TestRule(), None, 5, 5, 'msg')


def test_rule_match_suggestions_from_message():
    rm = RuleMatch(_TestRule(), None, 0, 3, 'Did you mean <suggestion>foo</suggestion> or <suggestion>bar</suggestion>?')
    assert rm.suggested_replacements == ['foo', 'bar']


# --- RuleWithMaxFilterTest / SameRuleGroupFilterTest -------------------------

@pytest.fixture(scope='module')
def language():
    return get_language('xx-XX')


def _prule(language, id, n):
    return PatternRule(id, language, [], 'desc%d' % n, 'msg%d' % n, 'shortMsg%d' % n)


def make_rule_match(from_pos, to_pos):
    return RuleMatch(FakeRule(), None, from_pos, to_pos, 'FakeMatch1')


def test_rule_with_max_filter(language):
    rule1 = _prule(language, 'id1', 1)
    rule2 = _prule(language, 'id1', 2)
    match1 = RuleMatch(rule1, None, 10, 20, 'Match1')
    match2 = RuleMatch(rule2, None, 15, 25, 'Match2')
    assert len(rule_with_max_filter([match1, match2])) == 2
    match3 = RuleMatch(rule2, None, 11, 19, 'Match3')
    assert len(rule_with_max_filter([match1, match3])) == 1


def test_rule_with_max_filter_no_filtering_if_not_overlapping(language):
    rule1 = _prule(language, 'id1', 1)
    rule2 = _prule(language, 'id1', 2)
    match1 = RuleMatch(rule1, None, 10, 20, 'Match1')
    match2 = RuleMatch(rule2, None, 21, 25, 'Match2')
    assert len(rule_with_max_filter([match1, match2])) == 2


def test_rule_with_max_filter_no_filtering_if_different_rulegroups(language):
    rule1 = _prule(language, 'id1', 1)
    rule2 = _prule(language, 'id2', 2)
    match1 = RuleMatch(rule1, None, 10, 20, 'Match1')
    match2 = RuleMatch(rule2, None, 15, 25, 'Match2')
    assert len(rule_with_max_filter([match1, match2])) == 2
    match3 = RuleMatch(rule2, None, 11, 19, 'Match3')
    assert len(rule_with_max_filter([match1, match3])) == 2


def test_rule_with_max_filter_includes():
    includes = base._includes
    assert includes(make_rule_match(10, 20), make_rule_match(10, 20))
    assert not includes(make_rule_match(10, 20), make_rule_match(5, 11))
    assert not includes(make_rule_match(10, 20), make_rule_match(11, 21))
    assert includes(make_rule_match(10, 20), make_rule_match(11, 19))
    assert not includes(make_rule_match(10, 20), make_rule_match(1, 10))
    assert includes(make_rule_match(10, 20), make_rule_match(19, 20))
    assert not includes(make_rule_match(10, 20), make_rule_match(21, 30))
    assert not includes(make_rule_match(10, 20), make_rule_match(1, 9))


def test_same_rule_group_filter(language):
    rule1 = _prule(language, 'id1', 1)
    rule2 = _prule(language, 'id1', 2)
    match1 = RuleMatch(rule1, None, 10, 20, 'Match1')
    match2 = RuleMatch(rule2, None, 15, 25, 'Match2')
    filtered = same_rule_group_filter([match1, match2])
    assert len(filtered) == 1
    assert filtered[0].message == 'Match1'


def test_same_rule_group_filter_no_filtering_if_not_overlapping(language):
    rule1 = _prule(language, 'id1', 1)
    rule2 = _prule(language, 'id1', 2)
    match1 = RuleMatch(rule1, None, 10, 20, 'Match1')
    match2 = RuleMatch(rule2, None, 21, 25, 'Match2')
    assert len(same_rule_group_filter([match1, match2])) == 2


def test_same_rule_group_filter_no_filtering_if_different_rulegroups(language):
    rule1 = _prule(language, 'id1', 1)
    rule2 = _prule(language, 'id2', 2)
    match1 = RuleMatch(rule1, None, 10, 20, 'Match1')
    match2 = RuleMatch(rule2, None, 15, 25, 'Match2')
    assert len(same_rule_group_filter([match1, match2])) == 2


def test_same_rule_group_filter_overlaps():
    overlaps = base._overlaps
    assert overlaps(make_rule_match(10, 20), make_rule_match(10, 20))
    assert overlaps(make_rule_match(10, 20), make_rule_match(5, 11))
    assert overlaps(make_rule_match(10, 20), make_rule_match(19, 21))
    assert overlaps(make_rule_match(10, 20), make_rule_match(11, 19))
    assert overlaps(make_rule_match(10, 20), make_rule_match(1, 10))
    assert overlaps(make_rule_match(10, 20), make_rule_match(19, 20))
    assert not overlaps(make_rule_match(10, 20), make_rule_match(21, 30))
    assert not overlaps(make_rule_match(10, 20), make_rule_match(1, 9))


# --- CleanOverlappingFilterTest ----------------------------------------------

_PRIORITIES = {
    'P3_RULE': 3,
    'P2_RULE': 2, 'P2_PREMIUM_RULE': 2, 'COMMA_HIGH_PRIORITY': 2, 'MISSING_THE_HIGH_PRIORITY': 2,
    'P1_RULE': 1, 'P1_RULE_B': 1, 'P1_PREMIUM_RULE': 1, 'COMMA_LOW_PRIORITY': 1, 'COMMA_LOW_PRIORITY2': 1,
    'MISSING_THE_LOW_PRIORITY': 1,
    'MISC': 0,
}


class MyDemoLang(Language):
    """CleanOverlappingFilterTest.MyDemoLang: the demo language with fixed rule priorities"""

    def __init__(self):
        d = LANGUAGES['xx']
        super().__init__('xx', d, d['variants'][0], get_language)

    def get_priority_for_id(self, id):
        if id not in _PRIORITIES:
            raise RuntimeError('No priority defined for ' + id)
        return _PRIORITIES[id]


class PremiumAwareFakeRule(FakeRule):
    """MyCleanOverlappingFilter.isPremiumRule(): rules with 'PREMIUM' in their id are premium"""

    def __init__(self, rule_id='FAKE-RULE', tag=None):
        super().__init__(rule_id, tag)
        self.premium = 'PREMIUM' in rule_id


@pytest.fixture(scope='module')
def my_demo_lang():
    return MyDemoLang()


def _filter(matches, lang):
    return clean_overlapping_filter(list(matches), lang, hide_premium_matches=True)


def _rm(rule_id, from_pos, to_pos, msg='msg', tag=None, sentence=None):
    return RuleMatch(PremiumAwareFakeRule(rule_id, tag), sentence or AnalyzedSentence([]), from_pos, to_pos, msg)


def test_clean_overlapping_empty(my_demo_lang):
    assert len(_filter([], my_demo_lang)) == 0


def test_clean_overlapping_no_overlap():
    # FakeRule() has the id 'FAKE-RULE', no priority is defined for it, but it's
    # not needed because there's no overlap
    lang = MyDemoLang()
    sentence = AnalyzedSentence([])
    matches2 = [RuleMatch(FakeRule(), sentence, 0, 10, 'msg'), RuleMatch(FakeRule(), sentence, 11, 20, 'msg')]
    assert len(_filter(matches2, lang)) == 2  # no overlap -> not filtering
    matches3 = [RuleMatch(FakeRule(), sentence, 0, 10, 'msg'), RuleMatch(FakeRule(), sentence, 10, 20, 'msg')]
    assert len(_filter(matches3, lang)) == 2  # no overlap -> not filtering


@pytest.mark.parametrize('first,second,winner', [
    (('P1_RULE', None), ('P1_RULE_B', None), 'P1_RULE_B'),  # overlap -> filtering
    (('P1_RULE_B', None), ('P1_RULE', None), 'P1_RULE'),  # latest wins with equal priority
    (('P1_RULE', None), ('P2_RULE', None), 'P2_RULE'),  # P2 has higher priority
    (('P2_RULE', None), ('P1_RULE', None), 'P2_RULE'),  # P2 has higher priority
    (('P2_PREMIUM_RULE', None), ('P1_RULE', None), 'P1_RULE'),  # premium rules are hidden
    (('P1_RULE', None), ('P2_PREMIUM_RULE', None), 'P1_RULE'),  # premium rules are hidden
    (('P2_PREMIUM_RULE', 'picky'), ('P1_RULE', None), 'P1_RULE'),
    (('P1_RULE', None), ('P2_PREMIUM_RULE', 'picky'), 'P1_RULE'),
    (('P2_RULE', 'picky'), ('P1_RULE', None), 'P1_RULE'),  # P2 has higher priority but it's picky
    (('P1_RULE', None), ('P2_RULE', 'picky'), 'P1_RULE'),  # P2 has higher priority but it's picky
])
def test_clean_overlapping_priorities(my_demo_lang, first, second, winner):
    matches = [_rm(first[0], 0, 10, 'msg1', first[1]), _rm(second[0], 9, 20, 'msg2', second[1])]
    filtered = _filter(matches, my_demo_lang)
    assert len(filtered) == 1
    assert filtered[0].rule.get_id() == winner


@pytest.mark.parametrize('first,second,winner', [
    # juxtaposed matches, comma in the same place
    (('COMMA_LOW_PRIORITY', 5, 10, 'right,'), ('COMMA_HIGH_PRIORITY', 10, 15, ', left'), 'COMMA_HIGH_PRIORITY'),
    (('COMMA_HIGH_PRIORITY', 5, 10, 'right,'), ('COMMA_LOW_PRIORITY', 10, 15, ', left'), 'COMMA_HIGH_PRIORITY'),
    (('COMMA_LOW_PRIORITY2', 5, 10, 'right,'), ('COMMA_LOW_PRIORITY', 10, 15, ', left'), 'COMMA_LOW_PRIORITY'),
    # same suggestion for the same place
    (('MISSING_THE_HIGH_PRIORITY', 5, 10, 'of the'), ('MISSING_THE_LOW_PRIORITY', 11, 15, 'the provisions'),
     'MISSING_THE_HIGH_PRIORITY'),
])
def test_clean_overlapping_juxtaposed(my_demo_lang, first, second, winner):
    m1 = _rm(first[0], first[1], first[2], 'msg1')
    m1.add_suggested_replacement(first[3])
    m2 = _rm(second[0], second[1], second[2], 'msg2')
    m2.add_suggested_replacement(second[3])
    filtered = _filter([m1, m2], my_demo_lang)
    assert len(filtered) == 1  # filtering
    assert filtered[0].rule.get_id() == winner


def test_clean_overlapping_unordered(my_demo_lang):
    unordered = [_rm('P1_RULE', 11, 12, 'msg2'), _rm('P2_RULE', 9, 10, 'msg1', 'picky')]
    with pytest.raises(ValueError):  # Java: IllegalArgumentException
        _filter(unordered, my_demo_lang)
