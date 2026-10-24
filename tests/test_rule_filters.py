"""Ports of RuleMatchTest, RuleWithMaxFilterTest, SameRuleGroupFilterTest and
CleanOverlappingFilterTest (languagetool-core/src/test/java/org/languagetool/rules/),
plus tests of core filters (AbstractDateCheckFilter, AbstractAdvancedSynthesizerFilter,
AbstractFindSuggestionsFilter with EditDistance, AbstractNewYearDateFilter, AbstractTextToNumberFilter...)."""

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


# --- AbstractDateCheckFilter -------------------------------------------------

from langtool.rules.core_filters import AbstractDateCheckFilter, CalendarDate  # noqa: E402


def test_calendar_date_day_of_week():
    # java.util.GregorianCalendar: Sunday is 1, Julian calendar before 1582-10-15
    assert CalendarDate.of(2014, 9, 7).day_of_week == 3  # Tuesday, 7 October 2014
    assert CalendarDate.of(2000, 0, 1).day_of_week == 7  # Saturday
    assert CalendarDate.of(2024, 1, 29).day_of_week == 5  # Thursday
    assert CalendarDate.of(1582, 9, 15).day_of_week == 6  # Friday, first Gregorian day
    assert CalendarDate.of(1582, 9, 4).day_of_week == 5  # Thursday, last Julian day
    assert CalendarDate.of(1500, 1, 29).day_of_week == 7  # Julian leap year


@pytest.mark.parametrize('ymd', [(2014, 7, 32), (2014, 1, 29), (1900, 1, 29), (2014, 12, 1), (2014, -1, 1),
                                 (2014, 0, 0), (0, 0, 1), (1582, 9, 10)])
def test_calendar_date_invalid(ymd):
    # non-lenient Calendar: IllegalArgumentException
    with pytest.raises(ValueError):
        CalendarDate.of(*ymd)


class _EnglishDateCheckFilter(AbstractDateCheckFilter):
    _DAYS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
    _MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')

    def get_day_of_week(self, s):
        for i, d in enumerate(self._DAYS):
            if s.lower().startswith(d):
                return i + 1
        raise RuntimeError('unknown day ' + s)

    def get_day_of_week_name(self, date):
        return ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')[date.day_of_week - 1]

    def get_month(self, s):
        for i, m in enumerate(self._MONTHS):
            if s.lower().startswith(m):
                return i + 1
        raise RuntimeError('unknown month ' + s)


def _date_match(message='{day} is really a {realDay} ({currentYear})'):
    m = RuleMatch(FakeRule(), None, 0, 5, message, 'short')
    m.type = 'Hint'
    return m


def test_date_check_filter():
    import datetime
    f = _EnglishDateCheckFilter()
    args = dict(weekDay='Mon', day='7th', month='Oct­', year='2014')
    m = f.accept_rule_match(_date_match(), args, 0, [], [])
    assert m.message == 'Monday is really a Tuesday (%d)' % datetime.date.today().year
    assert m.short_message == 'short'
    assert m.type == 'Hint'
    assert m.url == 'https://www.timeanddate.com/calendar/?year=2014'
    assert f.accept_rule_match(_date_match(), dict(args, weekDay='Tue'), 0, [], []) is None
    # numeric months
    assert f.accept_rule_match(_date_match(), dict(args, month='10'), 0, [], []) is not None
    assert f.accept_rule_match(_date_match(), dict(args, month='10', weekDay='Tue'), 0, [], []) is None
    # invalid dates and unknown names: no match
    assert f.accept_rule_match(_date_match(), dict(args, day='32'), 0, [], []) is None
    assert f.accept_rule_match(_date_match(), dict(args, month='13'), 0, [], []) is None
    assert f.accept_rule_match(_date_match(), dict(args, weekDay='Xyz'), 0, [], []) is None
    assert f.accept_rule_match(_date_match(), dict(args, month='Xyz'), 0, [], []) is None
    # no year: 2014 in tests (TestHackHelper.isJUnitTest), the current year otherwise
    no_year = dict(weekDay='Mon', day='7', month='Oct')
    assert f.accept_rule_match(_date_match(), no_year, 0, [], []) is not None
    assert f.accept_rule_match(_date_match(), dict(no_year, weekDay='Tue'), 0, [], []) is None
    # missing arguments: IllegalArgumentException
    with pytest.raises(ValueError):
        f.accept_rule_match(_date_match(), dict(day='7', month='Oct'), 0, [], [])
    with pytest.raises(ValueError):
        f.accept_rule_match(_date_match(), dict(weekDay='Mon', month='Oct'), 0, [], [])


# --- AbstractFutureDateFilter -------------------------------------------------

from langtool.rules.core_filters import AbstractFutureDateFilter  # noqa: E402


class _EnglishFutureDateFilter(AbstractFutureDateFilter):

    def get_month(self, s):
        return _EnglishDateCheckFilter().get_month(s)


def test_future_date_filter():
    """AbstractFutureDateFilter: in tests the current date is 2014-01-01
    (TestHackHelper.isJUnitTest)"""
    f = _EnglishFutureDateFilter()
    m = _date_match()
    assert f.accept_rule_match(m, dict(day='7th', month='Oct', year='2014'), 0, [], []) is m
    assert f.accept_rule_match(m, dict(day='1', month='1', year='2014'), 0, [], []) is m
    assert f.accept_rule_match(m, dict(day='31', month='Dec', year='2013'), 0, [], []) is None
    assert f.accept_rule_match(m, dict(day='3', month='Mar', year='1999'), 0, [], []) is None
    # invalid dates: no match (caught by a different rule)
    assert f.accept_rule_match(m, dict(day='32', month='Aug', year='2014'), 0, [], []) is None
    assert f.accept_rule_match(m, dict(day='29', month='Feb', year='2015'), 0, [], []) is None
    assert f.accept_rule_match(m, dict(day='1', month='13', year='2015'), 0, [], []) is None
    # unknown months, invalid years and missing arguments raise errors like in Java
    with pytest.raises(RuntimeError):
        f.accept_rule_match(m, dict(day='1', month='Xyz', year='2015'), 0, [], [])
    with pytest.raises(ValueError):
        f.accept_rule_match(m, dict(day='1', month='Jan', year='20x5'), 0, [], [])
    with pytest.raises(ValueError):
        f.accept_rule_match(m, dict(day='1', month='Jan'), 0, [], [])
    # the day of the month written with letters (getDayOfMonth, 0 by default: an invalid date)
    assert f.accept_rule_match(m, dict(day='first', month='Jan', year='2015'), 0, [], []) is None


def test_future_date_filter_outside_tests(monkeypatch):
    """Outside of tests, dates after today are in the future"""
    import datetime
    from langtool.rules import core_filters
    monkeypatch.setattr(core_filters, 'is_junit_test', lambda: False)
    f = _EnglishFutureDateFilter()
    m = _date_match()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    def args(d):
        return dict(day=str(d.day), month=str(d.month), year=str(d.year))

    assert f.accept_rule_match(m, args(tomorrow), 0, [], []) is m
    assert f.accept_rule_match(m, args(today), 0, [], []) is None


# --- AbstractAdvancedSynthesizerFilter ---------------------------------------

def test_advanced_synthesizer_filter_composite_postag():
    """AbstractAdvancedSynthesizerFilter.getCompositePostag: \\aN and \\bN are
    replaced by the groups of lemmaSelect (matched against the original POS
    tag) and postagSelect (matched against the desired POS tag)"""
    from langtool.rules.core_filters import AbstractAdvancedSynthesizerFilter
    f = AbstractAdvancedSynthesizerFilter()
    assert f.get_composite_postag('V(.*)', '(PP.*)', 'VMIS1S0', 'PP2CP000', 'V\\a1:\\b1') == 'VMIS1S0:PP2CP000'
    assert f.get_composite_postag('V(.)N.*', 'V...(..).*', 'VMN0000', 'VMIP3S0', 'V\\a1(IP|IF)\\b1.') == \
        'VM(IP|IF)3S.'
    # no match (or a group that didn't participate): postagReplace unchanged
    assert f.get_composite_postag('V(.*)', '(PP.*)', 'NCMS000', 'PP2CP000', 'V\\a1:\\b1') == 'V\\a1:\\b1'
    assert f.get_composite_postag('V(X)?.*', '(PP.*)', 'VMIS1S0', 'PP2CP000', 'V\\a1:\\b1') == 'V\\a1:PP2CP000'


# --- AbstractDateCheckWithSuggestionsFilter ----------------------------------

from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings  # noqa: E402
from langtool.rules.core_filters import (AbstractDateCheckWithSuggestionsFilter,  # noqa: E402
                                         AbstractNumberInWordFilter, AbstractSuppressMisspelledSuggestionsFilter,
                                         IsEnglishWordFilter)


class _EnglishDateCheckWithSuggestionsFilter(AbstractDateCheckWithSuggestionsFilter):
    get_day_of_week = _EnglishDateCheckFilter.get_day_of_week
    get_day_of_week_name = _EnglishDateCheckFilter.get_day_of_week_name
    get_month = _EnglishDateCheckFilter.get_month
    _DAYS = _EnglishDateCheckFilter._DAYS
    _MONTHS = _EnglishDateCheckFilter._MONTHS

    def get_error_message_wrong_year(self):
        return 'Wrong year, {currentYear}?'


def _tokens(text):
    out = []
    pos = 0
    ws = False
    for t in text.split(' '):
        atr = AnalyzedTokenReadings(AnalyzedToken(t, None, None), pos)
        atr.whitespace_before = ws
        out.append(atr)
        pos += len(t) + 1
        ws = True
    return out


def test_date_check_with_suggestions_filter():
    f = _EnglishDateCheckWithSuggestionsFilter()
    tokens = _tokens('Monday 7 October 2015')
    args = dict(weekDay='1', day='2', month='3', year='4')
    m = f.accept_rule_match(_date_match(), args, 0, tokens, [1, 1, 1, 1])
    # 7 October 2015 is a Wednesday; 7 October 2014 (the current year in tests) is a Tuesday
    assert m.message == 'Monday is really a Wednesday (%d)' % __import__('datetime').date.today().year
    assert (m.from_pos, m.to_pos) == (0, 8)
    assert m.suggested_replacements == ['Wednesday 7', 'Monday 5']
    assert m.url == 'https://www.timeanddate.com/calendar/?year=2015'
    assert f.accept_rule_match(_date_match(), args, 0, _tokens('Wednesday 7 October 2015'), [1, 1, 1, 1]) is None
    # the date fits the weekday in the current year (2014 in tests): suggest the year
    m = f.accept_rule_match(_date_match(), args, 0, _tokens('Tuesday 7 October 2015'), [1, 1, 1, 1])
    assert m.message == 'Wrong year, 2014?'
    assert (m.from_pos, m.to_pos) == (18, 22)
    assert m.suggested_replacements == ['2014']
    # invalid date, unknown day: no match; parse errors: IllegalArgumentException
    assert f.accept_rule_match(_date_match(), args, 0, _tokens('Monday 32 October 2015'), [1, 1, 1, 1]) is None
    assert f.accept_rule_match(_date_match(), args, 0, _tokens('Xyz 7 October 2015'), [1, 1, 1, 1]) is None
    with pytest.raises(ValueError):
        f.accept_rule_match(_date_match(), args, 0, _tokens('Monday 7 October 20x5'), [1, 1, 1, 1])
    # a yyyy-mm-dd token
    m = f.accept_rule_match(_date_match(), dict(weekDay='1', date='2'), 0, _tokens('Monday 2015-10-07'), [1, 1])
    assert m.suggested_replacements == ['Wednesday 2015-10-07', 'Monday 2015-10-5']


# --- AbstractSuppressMisspelledSuggestionsFilter, AbstractNumberInWordFilter --

def _pattern_rule_match(language, message):
    rule = PatternRule('ID', language, [], 'desc', message, 'short')
    return RuleMatch(rule, None, 0, 5, message)


def test_suppress_misspelled_suggestions_filter_without_speller():
    """Without a spelling rule (Language.getDefaultSpellingRule() returns
    null), no suggestion is misspelled"""
    lang = get_language('xx')
    assert lang.get_default_spelling_rule() is None
    f = AbstractSuppressMisspelledSuggestionsFilter()
    m = f.accept_rule_match(_pattern_rule_match(lang, '<suggestion>a b</suggestion> <suggestion>c</suggestion>'),
                            {'suppressMatch': 'true'}, 0, [], [])
    assert m.suggested_replacements == ['a b', 'c']
    assert f.accept_rule_match(_pattern_rule_match(lang, 'no suggestions'), {'suppressMatch': 'true'}, 0, [],
                               []) is None
    m = f.accept_rule_match(_pattern_rule_match(lang, 'no suggestions'), {'suppressMatch': 'false'}, 0, [], [])
    assert m.suggested_replacements == []
    with pytest.raises(ValueError):
        f.accept_rule_match(_pattern_rule_match(lang, 'x'), {}, 0, [], [])


class _NumberInWordFilter(AbstractNumberInWordFilter):
    words = {'good', 'goed'}

    def is_misspelled(self, word):
        return word not in self.words

    def get_suggestions(self, word):
        return ['sugg:' + word]


def test_number_in_word_filter():
    f = _NumberInWordFilter()
    m = RuleMatch(FakeRule(), None, 0, 5, 'msg')
    assert f.accept_rule_match(m, {'word': 'g00d'}, 0, [], []).suggested_replacements == ['good']
    assert f.accept_rule_match(m, {'word': 'go3ed'}, 0, [], []).suggested_replacements == ['goed']
    assert f.accept_rule_match(m, {'word': 'xy1z'}, 0, [], []).suggested_replacements == ['sugg:xyz']


def test_is_english_word_filter_in_tests():
    """In Java, English is not available in the unit tests of the other
    language modules: the filter rejects all matches there"""
    f = IsEnglishWordFilter(get_language('xx'))
    m = RuleMatch(FakeRule(), None, 0, 5, 'msg')
    assert f.accept_rule_match(m, {'formPositions': '1'}, 0, [], []) is None


# --- MultitokenSpeller -------------------------------------------------------

def test_multitoken_speller(tmp_path):
    from langtool.rules.multitoken import MultitokenSpeller, convert_to_title_case_iterating_chars
    p = tmp_path / 'words.txt'
    p.write_text('# comment\nBritney Spears\nGarcía Márquez\nsingle\nHomo sapiens  # comment\n', encoding='utf-8')
    speller = MultitokenSpeller(get_language('xx'), [str(p)])
    assert speller.get_suggestions('britaney speers') == ['Britney Spears']
    assert speller.get_suggestions('Garcìa Mrquez') == ['García Márquez']
    assert speller.get_suggestions('Homos Sapiens') == ['Homo sapiens']
    # accepted tokens: only distance <= 1
    assert speller.get_suggestions('britaney speers x', True) == []
    assert speller.get_suggestions('Britney Spears') == []
    assert speller.get_suggestions('single') == []
    assert convert_to_title_case_iterating_chars('homo sapiens-x') == 'Homo Sapiens-X'
    assert get_language('xx').get_multitoken_speller() is None


# --- AbstractFindSuggestionsFilter, EditDistance --------------------------------

from langtool.rules.core_filters import (AbstractFindSuggestionsFilter, AbstractNewYearDateFilter,  # noqa: E402
                                         AbstractTextToNumberFilter, EditDistance, java_float_to_string)


def test_edit_distance_damerau():
    """org.languagetool.rules.spelling.symspell.implementation.EditDistance"""
    d = EditDistance('casa')
    assert d.compare('casa', 4) == 0
    assert d.compare('cosa', 4) == 1
    assert d.compare('caas', 4) == 1  # transposition
    assert d.compare('cas', 4) == 1
    assert d.compare('casas', 4) == 1
    assert d.compare('xyzw', 4) == 4
    assert d.compare('xyzwvu', 4) == -1  # more than maxDistance
    assert d.compare('perro', 1) == -1
    assert d.compare('', 4) == 4
    assert d.compare('cosa', 0) == -1
    assert d.compare('casa', 0) == 0
    assert EditDistance('').compare('abc', 4) == 3
    assert EditDistance('abcdef').compare('abdcef', 4) == 1
    assert EditDistance('ca').compare('abc', 4) == 3  # restricted Damerau (optimal string alignment)


class _FakeTagger:
    def __init__(self, readings):
        self.readings = readings

    def tag(self, words):
        out = []
        for w in words:
            rs = self.readings.get(w, [(None, None)])
            out.append(AnalyzedTokenReadings([AnalyzedToken(w, t, lemma) for lemma, t in rs], 0))
        return out


class _FakeSynth:
    def __init__(self, forms):
        self.forms = forms

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        return self.forms.get((token.lemma, pos_tag), [])


class _FindSuggestionsFilter(AbstractFindSuggestionsFilter):
    tagger = _FakeTagger({
        'casa': [('casa', 'NCFS000'), ('casar', 'VMIP3S0')], 'cosa': [('cosa', 'NCFS000')],
        'caso': [('caso', 'NCMS000')], 'casó': [('casar', 'VMIS3S0')], 'Casa': [('Casa', 'NP00000')],
        'casas': [('casa', 'NCFP000')], 'cása': [('cása', 'NCFS000')]})
    suggestions = {'cas': ['casa', 'cosa', 'caso', 'casó', 'Casa'], 'Cas': ['casa', 'caso'],
                   'casa': ['cosa', 'cása'], 'caso': ['cosa', 'casó', 'cáso']}
    synth = None
    calls = 0

    def get_tagger(self):
        return self.tagger

    def get_spelling_suggestions(self, atr):
        type(self).calls += 1
        return self.suggestions.get(atr.token, [])

    def get_synthesizer(self):
        return self.synth


def _find_match(sugg='{suggestion}', message='msg'):
    m = RuleMatch(FakeRule(), None, 0, 3, message, 'short')
    m.set_suggested_replacements([sugg] if sugg is not None else [])
    return m


def test_find_suggestions_filter():
    f = _FindSuggestionsFilter()
    tokens = _tokens('el cas')
    m = f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'NC.*'}, 1, tokens, [1, 1])
    assert m.suggested_replacements == ['casa', 'cosa', 'caso']
    assert m.short_message == 'short'
    # priorityPostag first, removeSuggestionsRegexp
    args = {'wordFrom': '2', 'desiredPostag': 'NC.*', 'priorityPostag': 'NCM.*', 'removeSuggestionsRegexp': 'cos.'}
    m = f.accept_rule_match(_find_match('x {suggestion}'), args, 1, tokens, [1, 1])
    assert m.suggested_replacements == ['x caso', 'x casa']
    # capitalization of the original word, {Suggestion}, {SUGGESTION}
    m = f.accept_rule_match(_find_match('{SUGGESTION}'), {'wordFrom': '2', 'desiredPostag': 'NC.*'}, 1,
                            _tokens('el Cas'), [1, 1])
    assert m.suggested_replacements == ['CASA', 'CASO']
    # cached per token + isTagged
    calls = _FindSuggestionsFilter.calls
    f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'NC.*'}, 1, tokens, [1, 1])
    assert _FindSuggestionsFilter.calls == calls
    # no suggestion: the match is kept without suggestions, unless suppressMatch
    m = f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'Z.*'}, 1, tokens, [1, 1])
    assert m.suggested_replacements == []
    assert f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'Z.*', 'suppressMatch': 'true'},
                               1, tokens, [1, 1]) is None
    # a finished suggestion keeps the match
    m = f.accept_rule_match(_find_match('fixed'), {'wordFrom': '2', 'desiredPostag': 'Z.*',
                                                   'suppressMatch': 'true'}, 1, tokens, [1, 1])
    assert m.suggested_replacements == ['fixed']
    # diacritics mode: the original word matches the POS tag -> no match; only diacritic changes
    assert f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'NC.*', 'Mode': 'diacritics'},
                               1, _tokens('la casa'), [1, 1]) is None
    m = f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'VMIS.*', 'Mode': 'diacritics'},
                            1, _tokens('lo caso'), [1, 1])
    assert m.suggested_replacements == ['casó']
    assert f.accept_rule_match(_find_match(), {'wordFrom': '2', 'desiredPostag': 'NCF.*', 'Mode': 'diacritics'},
                               1, _tokens('lo caso'), [1, 1]) is None
    with pytest.raises(ValueError):
        f.accept_rule_match(_find_match(), {'wordFrom': '2'}, 1, tokens, [1, 1])


def test_find_suggestions_filter_synthesizer():
    f = _FindSuggestionsFilter()
    f.synth = _FakeSynth({('casa', 'NC.P000'): ['casas'], ('casar', 'NC.P000'): [],
                          ('cosa', 'NC.P000'): ['cosas'], ('caso', 'NC.P000'): ['casos'],
                          ('Casa', 'NC.P000'): []})
    tokens = _tokens('las cas')
    m = f.accept_rule_match(_find_match(None), {'wordFrom': '2', 'desiredPostag': 'NC.P000'}, 1, tokens, [1, 1])
    # synthesized forms ordered by the edit distance to "cas" (stable: all have distance 2)
    assert m.suggested_replacements == ['casas', 'cosas', 'casos']
    m = f.accept_rule_match(_find_match(None), {'wordFrom': '2', 'desiredPostag': 'NC.P000'}, 1,
                            _tokens('los caos'), [1, 1])
    assert m.suggested_replacements == []


class _InMarkerFilter(_FindSuggestionsFilter):
    pass


def test_find_suggestions_filter_inmarker():
    f = _InMarkerFilter()
    from langtool.tool import JLanguageTool
    sentence = JLanguageTool(get_language('xx')).get_analyzed_sentence('x c as')
    m = RuleMatch(FakeRule(), sentence, 2, 6, 'msg')
    m.set_suggested_replacements(['{suggestion}'])
    m = f.accept_rule_match(m, {'wordFrom': 'inmarker', 'desiredPostag': 'NC.*'}, 1, [], [])
    assert m.suggested_replacements == ['casa', 'cosa', 'caso']


# --- AbstractNewYearDateFilter ------------------------------------------------

class _EnglishNewYearDateFilter(AbstractNewYearDateFilter):
    get_month = _EnglishDateCheckFilter.get_month
    _MONTHS = _EnglishDateCheckFilter._MONTHS


def test_new_year_date_filter():
    f = _EnglishNewYearDateFilter()
    m = f.accept_rule_match(_date_match('{year} or {realYear}?'), dict(year='2013', month='Feb', day='3rd'), 0, [],
                            [])
    # in tests it is always January 2014
    assert m.message == '2013 or 2014?'
    assert m.short_message == 'short' and m.type == 'Hint'
    assert f.accept_rule_match(_date_match(), dict(year='2013', month='2', day='3'), 0, [], []) is not None
    # December, other years, invalid dates: no match
    assert f.accept_rule_match(_date_match(), dict(year='2013', month='Dec', day='3'), 0, [], []) is None
    assert f.accept_rule_match(_date_match(), dict(year='2014', month='Feb', day='3'), 0, [], []) is None
    assert f.accept_rule_match(_date_match(), dict(year='2012', month='Feb', day='3'), 0, [], []) is None
    assert f.accept_rule_match(_date_match(), dict(year='2013', month='Feb', day='30'), 0, [], []) is None
    with pytest.raises(ValueError):
        f.accept_rule_match(_date_match(), dict(year='20x3', month='Feb', day='3'), 0, [], [])


def test_new_year_date_filter_outside_tests(monkeypatch):
    import langtool.rules.core_filters as cf
    monkeypatch.setattr(cf, 'is_junit_test', lambda: False)
    import datetime
    f = _EnglishNewYearDateFilter()
    today = datetime.date.today()
    assert f.get_current_year() == today.year
    assert f.is_january() == (today.month == 1)


# --- AbstractTextToNumberFilter -----------------------------------------------

class _SpanishLikeTextToNumberFilter(AbstractTextToNumberFilter):
    numbers = {'cero': 0.0, 'medio': 0.5, 'un': 1.0, 'dos': 2.0, 'tres': 3.0, 'cinco': 5.0, 'veinte': 20.0,
               'cien': 100.0, 'ciento': 100.0}
    multipliers = {'mil': 1000.0, 'millones': 1000000.0, 'billones': 10E12}

    def is_comma(self, s):
        return s.lower() in ('coma', 'comma')

    def is_percentage(self, pattern_tokens, i):
        return pattern_tokens[i].token == 'ciento' and pattern_tokens[i - 1].token.lower() == 'por'


def _number(text, from_pos=0, to_pos=None):
    tokens = [t for t in _tokens(text)]
    m = RuleMatch(FakeRule(), None, from_pos, to_pos if to_pos is not None else len(text), 'msg')
    return _SpanishLikeTextToNumberFilter().accept_rule_match(m, {}, 0, tokens, []).suggested_replacements


def test_text_to_number_filter():
    assert _number('tres') == ['3']
    assert _number('dos mil tres') == ['2003']
    assert _number('mil') == ['1000']
    assert _number('veinte millones') == ['20000000']
    assert _number('dos coma cinco') == ['2.5']
    assert _number('tres coma dos cinco') == ['3.25']
    assert _number('cinco por ciento') == ['5 %']
    # Java float arithmetic: (float) 10E12 * 3 (as in Java, a "billón" is 10E12 = 1e13 there)
    assert _number('tres billones') == ['30000000532480']
    # only the tokens inside the marker
    assert _number('dos mil tres', 4) == ['1003']


def test_java_float_to_string():
    """Float.toString"""
    assert java_float_to_string(0.5) == '0.5'
    assert java_float_to_string(2.25) == '2.25'
    assert java_float_to_string(1e10) == '1.0E10'
    assert java_float_to_string(1.0e-4) == '1.0E-4'
    assert java_float_to_string(0.001) == '0.001'
    assert java_float_to_string(-12.5) == '-12.5'
    assert java_float_to_string(0.0) == '0.0'
