"""Port of the tests of the German rule filters:
org.languagetool.rules.de.AdaptSuggestionFilterTest, DateCheckFilterTest,
GermanNumberInWordFilterTest and InsertCommaFilterTest, plus checks of the
other filters of langtool.lang.de.filters."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.lang.de.filters import (AdaptSuggestionFilter, CompoundCheckFilter, DateCheckFilter,
                                      GermanNumberInWordFilter, InsertCommaFilter, RecentYearFilter,
                                      UppercaseNounReadingFilter, _java_regex_split, _WHITESPACE)
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.core_filters import CalendarDate
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt_de():
    return JLanguageTool(get_language('de'))


class FakeRule(Rule):
    def get_id(self):
        return 'FAKE-RULE'

    def get_description(self):
        return 'Fake rule'


# --- AdaptSuggestionFilterTest ---

def _run_accept_rule_match(lt, sentence_str, word, orig_replacement, new_replacements):
    filt = AdaptSuggestionFilter()
    sentence = lt.get_analyzed_sentence(sentence_str)
    from_pos = sentence_str.find(word)
    to_pos = from_pos + len(word)
    match = RuleMatch(FakeRule(), sentence, from_pos, to_pos, 'fake message')
    match.set_suggested_replacement(orig_replacement)
    tokens = sentence.get_tokens_without_whitespace()
    token_pos = -1
    i = 0
    for t in tokens:
        if t.token == word:
            token_pos = i
            break
        i += 1
    new_match = filt.accept_rule_match(match, {'sub': '\\1'}, i, tokens[token_pos:token_pos + 1], None)
    assert new_match is not None
    assert '[' + ', '.join(new_match.suggested_replacements) + ']' == new_replacements, sentence_str


def test_adapt_suggestion_filter_accept_rule_match_with_det(lt_de):
    """AdaptSuggestionFilterTest.testAcceptRuleMatchWithDet"""
    run = _run_accept_rule_match
    # MAS (Der Plan):
    run(lt_de, 'Die Roadmap ist gut.', 'Roadmap', 'Plan', '[Den Plan, Der Plan]')
    # MAS (der Plan):
    run(lt_de, 'Hier steht die Roadmap.', 'Roadmap', 'Plan', '[den Plan, der Plan]')
    run(lt_de, 'Hier steht eine Roadmap.', 'Roadmap', 'Plan', '[einen Plan, ein Plan]')
    run(lt_de, 'Hier steht meine Roadmap.', 'Roadmap', 'Plan', '[meinen Plan, mein Plan]')
    run(lt_de, 'Hier steht deine Roadmap.', 'Roadmap', 'Plan', '[deinen Plan, dein Plan]')
    run(lt_de, 'Hier steht seine Roadmap.', 'Roadmap', 'Plan', '[seinen Plan, sein Plan]')
    run(lt_de, 'Hier steht ihre Roadmap.', 'Roadmap', 'Plan', '[ihren Plan, ihr Plan]')
    run(lt_de, 'Hier steht unsere Roadmap.', 'Roadmap', 'Plan', '[unseren Plan, unser Plan]')
    run(lt_de, 'Hier steht eure Roadmap.', 'Roadmap', 'Plan', '[euren Plan, euer Plan]')
    # FEM (die Idee):
    run(lt_de, 'Hier steht die Roadmap.', 'Roadmap', 'Idee', '[die Idee]')
    run(lt_de, 'Hier steht eine Roadmap.', 'Roadmap', 'Idee', '[eine Idee]')
    run(lt_de, 'Hier steht meine Roadmap.', 'Roadmap', 'Idee', '[meine Idee]')
    run(lt_de, 'Hier steht deine Roadmap.', 'Roadmap', 'Idee', '[deine Idee]')
    run(lt_de, 'Hier steht seine Roadmap.', 'Roadmap', 'Idee', '[seine Idee]')
    run(lt_de, 'Hier steht ihre Roadmap.', 'Roadmap', 'Idee', '[ihre Idee]')
    run(lt_de, 'Hier steht unsere Roadmap.', 'Roadmap', 'Idee', '[unsere Idee]')
    run(lt_de, 'Hier steht eure Roadmap.', 'Roadmap', 'Idee', '[eure Idee]')
    # NEU (das Verfahren):
    run(lt_de, 'Hier steht die Roadmap.', 'Roadmap', 'Verfahren', '[das Verfahren]')
    run(lt_de, 'Hier steht eine Roadmap.', 'Roadmap', 'Verfahren', '[ein Verfahren]')
    run(lt_de, 'Hier steht meine Roadmap.', 'Roadmap', 'Verfahren', '[mein Verfahren]')
    run(lt_de, 'Hier steht deine Roadmap.', 'Roadmap', 'Verfahren', '[dein Verfahren]')
    run(lt_de, 'Hier steht seine Roadmap.', 'Roadmap', 'Verfahren', '[sein Verfahren]')
    run(lt_de, 'Hier steht ihre Roadmap.', 'Roadmap', 'Verfahren', '[ihr Verfahren]')
    run(lt_de, 'Hier steht unsere Roadmap.', 'Roadmap', 'Verfahren', '[unser Verfahren]')
    run(lt_de, 'Hier steht eure Roadmap.', 'Roadmap', 'Verfahren', '[euer Verfahren]')


def _assert_det(det_token, repl_word, expected_det):
    adapted_det = AdaptSuggestionFilter().get_adapted_det(AnalyzedTokenReadings(det_token, 0), repl_word)
    assert '[' + ', '.join(adapted_det) + ']' == expected_det


def test_adapt_suggestion_filter_adapted_det():
    """AdaptSuggestionFilterTest.testAdaptedDet"""
    _assert_det(AnalyzedToken('die', 'ART:DEF:NOM:SIN:FEM', 'der'), 'Mann', '[der]')
    _assert_det(AnalyzedToken('der', 'ART:DEF:NOM:SIN:MAS', 'der'), 'Frau', '[die]')
    _assert_det(AnalyzedToken('der', 'ART:DEF:NOM:SIN:NEU', 'der'), 'Kind', '[das]')

    _assert_det(AnalyzedToken('eine', 'ART:IND:NOM:SIN:FEM', 'ein'), 'Plan', '[ein]')  # eine Roadmap -> ein Plan
    _assert_det(AnalyzedToken('eine', 'ART:IND:AKK:SIN:FEM', 'ein'), 'Plan', '[einen]')  # ich habe eine Roadmap -> ich habe einen Plan
    _assert_det(AnalyzedToken('einer', 'ART:IND:GEN:SIN:FEM', 'ein'), 'Plan', '[eines]')  # die Ausführung einer Roadmap -> die Ausführung eines Plans
    _assert_det(AnalyzedToken('einer', 'ART:IND:DAT:SIN:FEM', 'ein'), 'Plan', '[einem]')  # einer Roadmap -> einem Plan


# (AdaptSuggestionFilterTest.testAcceptRuleMatchDevTest, testAcceptRuleMatchWithDetAdj and testdAdaptedDetAdj
# are @Ignore'd in Java)


# --- DateCheckFilterTest ---

def _make_map(year, month, day_of_month, week_day):
    return {'year': year, 'month': month, 'day': day_of_month, 'weekDay': week_day}


def test_date_check_filter_accept_incomplete_args():
    """DateCheckFilterTest.testAcceptIncompleteArgs"""
    match = RuleMatch(FakeRule(), None, 0, 10, 'message')
    args = _make_map('2014', '8', '23', 'Samstag')
    del args['weekDay']
    with pytest.raises(ValueError):  # Java: IllegalArgumentException
        DateCheckFilter().accept_rule_match(match, args, -1, None, None)


def test_date_check_filter_get_day_of_week1():
    """DateCheckFilterTest.testGetDayOfWeek1"""
    f = DateCheckFilter()
    assert f.get_day_of_week('So') == 1
    assert f.get_day_of_week('Mo') == 2
    assert f.get_day_of_week('mo') == 2
    assert f.get_day_of_week('Mon.') == 2
    assert f.get_day_of_week('Montag') == 2
    assert f.get_day_of_week('montag') == 2
    assert f.get_day_of_week('Di') == 3
    assert f.get_day_of_week('Fr') == 6
    assert f.get_day_of_week('Samstag') == 7
    assert f.get_day_of_week('Sonnabend') == 7


def test_date_check_filter_get_day_of_week2():
    """DateCheckFilterTest.testGetDayOfWeek2"""
    f = DateCheckFilter()
    assert f.get_day_of_week_name(CalendarDate.of(2014, 8 - 1, 29)) == 'Freitag'
    assert f.get_day_of_week_name(CalendarDate.of(2014, 8 - 1, 30)) == 'Samstag'


def test_date_check_filter_get_month():
    """DateCheckFilterTest.testGetMonth"""
    f = DateCheckFilter()
    assert f.get_month('Januar') == 1
    assert f.get_month('Jan') == 1
    assert f.get_month('Jan.') == 1
    assert f.get_month('Dezember') == 12
    assert f.get_month('Dez') == 12
    assert f.get_month('dez') == 12
    assert f.get_month('DEZEMBER') == 12
    assert f.get_month('dezember') == 12


def test_date_check_filter_adjust_suggestion():
    """DateCheckFilter.adjustSuggestion (not tested in Java)"""
    f = DateCheckFilter()
    assert f.adjust_suggestion('Sonntag., 1. Mai') == 'Sonntag, 1. Mai'
    assert f.adjust_suggestion('So, 1. Mai') == 'So., 1. Mai'
    assert f.adjust_suggestion('So., 1. Mai') == 'So., 1. Mai'


# --- GermanNumberInWordFilterTest ---

def _run_number_in_word_filter(lt, text, arg, new_repl, pattern_token_pos, from_pos, to_pos):
    filt = GermanNumberInWordFilter()
    sentence = lt.get_analyzed_sentence(text)
    match = RuleMatch(FakeRule(), sentence, from_pos, to_pos, 'fake msg')
    match_tmp = filt.accept_rule_match(match, {'word': arg}, pattern_token_pos,
                                       sentence.get_tokens_without_whitespace(), None)
    assert match_tmp is not None
    assert new_repl in match_tmp.suggested_replacements


def test_german_number_in_word_filter(lt_de):
    """GermanNumberInWordFilterTest.testFilter"""
    _run_number_in_word_filter(lt_de, 'Schöne Grüß0e aus Potsdam.', 'Grüß0e', 'Grüße', 2, 0, 5)
    _run_number_in_word_filter(lt_de, 'Schöne Grü0e aus Potsdam.', 'Grü0e', 'Grüße', 2, 0, 5)
    _run_number_in_word_filter(lt_de, 'Der Aut0r schreibt ein Buch.', 'Aut0r', 'Autor', 2, 0, 5)


# --- InsertCommaFilterTest ---

def _run_insert_comma_filter(lt, text, pattern_token_pos, atr_from_pos, atr_to_pos, from_pos, to_pos, orig_repl,
                             new_repl):
    filt = InsertCommaFilter()
    sentence = lt.get_analyzed_sentence(text)
    match = RuleMatch(FakeRule(), sentence, from_pos, to_pos, 'fake msg')
    match.set_suggested_replacement(orig_repl)
    tokens = sentence.get_tokens_without_whitespace()
    atr = [tokens[atr_from_pos], tokens[atr_to_pos]]
    match_tmp = filt.accept_rule_match(match, {}, pattern_token_pos, atr, None)
    assert '[' + ', '.join(match_tmp.suggested_replacements) + ']' == new_repl


def test_insert_comma_filter(lt_de):
    """InsertCommaFilterTest.testFilter"""
    _run_insert_comma_filter(lt_de, 'Das Auto, das am Straßenrand steht parkt im Halteverbot.', 7,
                             7, 8, 29, 40, 'steht parkt', '[steht, parkt]')
    _run_insert_comma_filter(lt_de, 'Hoffe bei euch ist alles gut.', 1,
                             1, 4, 0, 7, 'Hoffe bei euch ist', '[Hoffe, bei euch ist]')


# --- checks of the other filters (no Java tests) ---

def test_java_regex_split():
    """Pattern.split as used by InsertCommaFilter"""
    assert _java_regex_split(_WHITESPACE, 'a b  c ') == ['a', 'b', '', 'c']
    assert _java_regex_split(_WHITESPACE, ' a') == ['', 'a']
    assert _java_regex_split(_WHITESPACE, '') == ['']


def test_compound_check_filter():
    """CompoundCheckFilter: part1;part2 must be listed in addedCompound.txt"""
    match = RuleMatch(FakeRule(), None, 0, 1, 'msg')
    f = CompoundCheckFilter()
    assert f.accept_rule_match(match, {'part1': 'Blumen', 'part2': 'Läden'}, 0, None, None) is match
    assert f.accept_rule_match(match, {'part1': 'Blumen', 'part2': 'Tische'}, 0, None, None) is None


def test_recent_year_filter():
    """RecentYearFilter: years from (this year - maxYearsBack) to last year"""
    import datetime
    this_year = datetime.date.today().year
    match = RuleMatch(FakeRule(), None, 0, 1, 'msg')
    f = RecentYearFilter()

    def accept(year):
        return f.accept_rule_match(match, {'year': str(year), 'maxYearsBack': '2'}, 0, None, None) is not None

    assert not accept(this_year)
    assert accept(this_year - 1)
    assert accept(this_year - 2)
    assert not accept(this_year - 3)


def test_uppercase_noun_reading_filter():
    """UppercaseNounReadingFilter: "stand" -> "Stand" is a noun"""
    match = RuleMatch(FakeRule(), None, 0, 1, 'msg')
    f = UppercaseNounReadingFilter()
    assert f.accept_rule_match(match, {'token': 'stand'}, 0, None, None) is match
    assert f.accept_rule_match(match, {'token': 'schnell'}, 0, None, None) is None
