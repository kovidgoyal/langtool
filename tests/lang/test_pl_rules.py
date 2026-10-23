"""Port of the tests of the Polish rules: org.languagetool.rules.pl.
CompoundRuleTest, DashRuleTest, DateCheckFilterTest,
PolishUnpairedBracketsRuleTest, PolishWordRepeatRuleTest,
SimpleReplaceRuleTest, WordCoherencyRuleTest, MorfologikPolishSpellerRuleTest
(skipped, spell checking), plus checks of the rule properties and of
DecadeSpellingFilter."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.pl.filters import DateCheckFilter, DecadeSpellingFilter
from langtool.lang.pl.rules import (CompoundRule, DashRule, PolishUnpairedBracketsRule, PolishWordRepeatRule,
                                    SimpleReplaceRule, WordCoherencyRule)
from langtool.messages import messages_for
from langtool.rules.base import RuleMatch
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pl')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('pl'))


def _matches(rule, lt, text):
    return rule.match(lt.get_analyzed_sentence(text))


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule(lt):
    """CompoundRuleTest.testRule"""
    rule = CompoundRule(messages_for('en'), get_language('pl'), None)
    # correct sentences:
    _check(lt, rule, 0, 'Nie róbmy nic na łapu-capu.')
    _check(lt, rule, 0, 'Jedzmy kogel-mogel.')
    # incorrect sentences:
    _check(lt, rule, 1, 'bim bom', 'bim-bom')


@pytest.mark.skip(reason='spell checking is not ported: CompoundRuleTest.testCompoundFile checks the entries of '
                         'compounds.txt with MorfologikPolishSpellerRule')
def test_compound_file():
    """CompoundRuleTest.testCompoundFile"""


def test_compound_rule_properties(lt):
    rule = CompoundRule(messages_for('pl'), get_language('pl'))
    assert rule.get_id() == 'PL_COMPOUNDS'
    assert rule.get_description() == 'Sprawdza wyrazy z łącznikiem, np. „łapu capu” zamiast „łapu-capu”'
    m, = _matches(rule, lt, 'Witamy w Rabce Zdroju.')
    assert m.message == 'Ten wyraz pisze się z łącznikiem.'
    assert m.short_message == 'Brak łącznika lub zbędny łącznik'
    assert m.suggested_replacements == ['Rabce-Zdroju']
    assert [e.example for e in rule.incorrect_examples] == ['Witamy w <marker>Rabce Zdroju</marker>.']
    assert [e.example for e in rule.correct_examples] == ['Witamy w <marker>Rabce-Zdroju</marker>.']


# --- DashRuleTest ---

def _check_dash(lt, rule, expected_errors, text, exp_suggestions=None):
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions is not None:
        assert matches[0].suggested_replacements == exp_suggestions


def test_dash_rule(lt):
    """DashRuleTest.testRule"""
    rule = DashRule(messages_for('pl'), get_language('pl'))
    # correct sentences:
    _check_dash(lt, rule, 0, 'Nie róbmy nic na łapu-capu.')
    _check_dash(lt, rule, 0, 'Jedzmy kogel-mogel.')
    _check_dash(lt, rule, 0, 'To jest ładna nota — bene, bene — odpowiedział Józek.')  # not really a real mistake
    # incorrect sentences:
    _check_dash(lt, rule, 1, 'bim – bom', ['bim-bom'])
    _check_dash(lt, rule, 1, 'Papua–Nowa Gwinea', ['Papua-Nowa'])
    _check_dash(lt, rule, 1, 'Papua — Nowa Gwinea', ['Papua-Nowa'])
    _check_dash(lt, rule, 1, 'Aix — en — Provence', ['Aix-en-Provence'])


def test_dash_rule_properties(lt):
    rule = DashRule(messages_for('pl'), get_language('pl'))
    assert rule.get_id() == 'DASH_RULE'
    assert rule.get_message() == 'Błędne użycie myślnika zamiast łącznika.'
    assert rule.get_description().startswith('Sprawdza, czy wyrazy pisane z łącznikiem')
    assert rule.tags == ['picky']


# --- DateCheckFilterTest ---

def test_get_day_of_week():
    """DateCheckFilterTest.testGetDayOfWeek"""
    f = DateCheckFilter()
    assert f.get_day_of_week('niedz') == 1
    assert f.get_day_of_week('pon') == 2
    assert f.get_day_of_week('Pon') == 2
    assert f.get_day_of_week('pon.') == 2
    assert f.get_day_of_week('poniedziałek') == 2
    assert f.get_day_of_week('Poniedziałek') == 2
    assert f.get_day_of_week('wtorek') == 3
    assert f.get_day_of_week('pt') == 6
    assert f.get_day_of_week('piątek') == 6


def test_month():
    """DateCheckFilterTest.testMonth"""
    f = DateCheckFilter()
    assert f.get_month('I') == 1
    assert f.get_month('XII') == 12
    assert f.get_month('grudnia') == 12
    assert f.get_month('Grudnia') == 12
    assert f.get_month('GRUDNIA') == 12


def test_date_check_filter_more():
    f = DateCheckFilter()
    with pytest.raises(RuntimeError):
        f.get_day_of_week('xyz')
    with pytest.raises(RuntimeError):
        f.get_month('xii')  # Roman numerals are case sensitive

    class _Date:
        day_of_week = 4
    assert f.get_day_of_week_name(_Date()) == 'środa'


# --- DecadeSpellingFilter ---

def test_decade_spelling_filter(lt):
    sentence = lt.get_analyzed_sentence('Wspominam lata 1990.')
    rule = CompoundRule(messages_for('pl'), get_language('pl'))
    match = RuleMatch(rule, sentence, 15, 20, 'Poprawnie: <suggestion>{dekada}. {wiek} w.</suggestion>', 'krótko')
    f = DecadeSpellingFilter()
    m = f.accept_rule_match(match, {'lata': '1990'}, 0, [], [])
    assert m.message == 'Poprawnie: <suggestion>90. XX w.</suggestion>'
    assert m.suggested_replacements == ['90. XX w.']
    assert m.short_message == 'krótko'
    assert (m.from_pos, m.to_pos) == (15, 20)
    m = f.accept_rule_match(match, {'lata': '1899'}, 0, [], [])
    assert m.suggested_replacements == ['99. XIX w.']
    # not a number: the match is ignored
    assert f.accept_rule_match(match, {'lata': 'ab90'}, 0, [], []) is None


# --- PolishUnpairedBracketsRuleTest ---

def test_unpaired_brackets_rule(lt):
    """PolishUnpairedBracketsRuleTest.testRulePolish"""
    rule = PolishUnpairedBracketsRule(messages_for('en'), get_language('pl'))

    def get_matches(text):
        return len(rule.match([lt.get_analyzed_sentence(text)]))

    assert get_matches('(To jest zdanie do testowania).') == 0
    assert get_matches('Piosenka ta trafiła na wiele list "Best of...", włączając w to te, które zostały utworzone '
                       'przez magazyn Rolling Stone.') == 0
    assert get_matches('A "B" C.') == 0
    assert get_matches('"A" B "C".') == 0
    assert get_matches('W tym zdaniu jest niesparowany „cudzysłów.') == 1


def test_unpaired_brackets_rule_properties():
    rule = PolishUnpairedBracketsRule(messages_for('pl'), get_language('pl'))
    assert rule.get_id() == 'PL_UNPAIRED_BRACKETS'
    assert rule.start_symbols == ['[', '(', '{', '„', '»', '"']
    assert rule.end_symbols == [']', ')', '}', '”', '«', '"']


# --- PolishWordRepeatRuleTest ---

def test_polish_word_repeat_rule(lt):
    """PolishWordRepeatRuleTest.testRule"""
    rule = PolishWordRepeatRule(messages_for('en'))
    # correct
    assert len(_matches(rule, lt, 'To jest zdanie próbne.')) == 0
    assert len(_matches(rule, lt, 'On tak się bardzo nie martwił, bo przecież musiał się umyć.')) == 0
    # repeated prepositions, don't count'em
    assert len(_matches(rule, lt, 'Na dyskotece tańczył jeszcze, choć był na bani.')) == 0
    # sf bug report:
    assert len(_matches(rule, lt, 'Żadnych „ale”.')) == 0
    # incorrect
    assert len(_matches(rule, lt, 'Był on bowiem pięknym strzelcem bowiem.')) == 1
    assert len(_matches(rule, lt, 'Mówiła długo, żeby tylko mówić długo.')) == 2


def test_polish_word_repeat_rule_properties(lt):
    rule = PolishWordRepeatRule(messages_for('pl'))
    assert rule.get_id() == 'PL_WORD_REPEAT'
    assert rule.default_off
    assert rule.get_description() == 'Powtórzenia wyrazów w zdaniu (monotonia stylistyczna)'
    m = _matches(rule, lt, 'Był on bowiem pięknym strzelcem bowiem.')[0]
    assert m.message == 'Powtórzony wyraz w zdaniu'
    assert m.short_message == 'Powtórzenie wyrazu'
    # Roman numerals and numbers are excluded
    assert len(_matches(rule, lt, 'Było XIX, potem XIX i 1990, 1990.')) == 0


# --- SimpleReplaceRuleTest ---

def test_simple_replace_rule(lt):
    """SimpleReplaceRuleTest.testRule"""
    rule = SimpleReplaceRule(messages_for('pl'), get_language('pl'))
    # correct sentences:
    assert len(_matches(rule, lt, 'Wszystko w porządku.')) == 0
    # no checking lemmas:
    assert len(_matches(rule, lt, 'Pola lodowe')) == 0
    # with immunized tokens:
    assert len(_matches(rule, lt, 'Witamy prez. Komorowskiego!')) == 0

    def check_simple_replace_rule(sentence, word):
        matches = _matches(rule, lt, sentence)
        assert len(matches) == 1, 'Invalid matches.length while checking sentence: ' + sentence
        assert matches[0].suggested_replacements == [word]

    # incorrect sentences:
    check_simple_replace_rule('Piaty przypadek.', 'Piąty')
    check_simple_replace_rule('To piaty przypadek.', 'piąty')


def test_simple_replace_rule_properties(lt):
    rule = SimpleReplaceRule(messages_for('pl'), get_language('pl'))
    assert rule.get_id() == 'PL_SIMPLE_REPLACE'
    assert rule.category.id == 'PRAWDOPODOBNE_LITEROWKI'
    assert rule.category.name == 'Prawdopodobne literówki'
    assert rule.loc_quality_issue_type == 'Misspelling'
    assert not rule.check_lemmas
    m, = _matches(rule, lt, 'Uspokój sei.')
    assert m.message == 'Wyraz „sei” to najczęściej literówka; poprawnie pisze się: się.'
    assert m.short_message == 'Literówka'


# --- WordCoherencyRuleTest ---

@pytest.fixture
def coherency_lt():
    lt = JLanguageTool(get_language('pl-PL'))
    # TestTools.disableAllRulesExcept(lt, "PL_WORD_COHERENCY")
    for rule in lt.get_all_rules():
        if rule.get_id() != 'PL_WORD_COHERENCY':
            lt.disable_rule(rule.get_id())
    return lt


def _coherency_matches(lt, s):
    rule = WordCoherencyRule(messages_for('en'), get_language('pl'))
    return rule.match(lt.analyze_text(s))


def _assert_good(lt, s):
    assert len(_coherency_matches(lt, s)) == 0


def _assert_error(lt, s, expected_suggestion):
    matches = _coherency_matches(lt, s)
    assert len(matches) == 1
    assert matches[0].suggested_replacements == [expected_suggestion]


def test_word_coherency_rule(coherency_lt):
    """WordCoherencyRuleTest.testRule"""
    lt = coherency_lt
    # correct sentences:
    _assert_good(lt, 'To jest grejpfrut. Dobry grejpfrut.')
    _assert_good(lt, 'Lubię Twoje blefy. Blef to jest coś.')
    # errors:
    _assert_error(lt, 'To jest grapefruit. Dobry grejpfrut.', 'grapefruit')
    matches1 = lt.check('To jest jego bluff. A może blef?')
    assert len(matches1) == 1
    assert (matches1[0].from_pos, matches1[0].to_pos) == (27, 31)
    assert matches1[0].suggested_replacements == ['bluff']
    matches2 = lt.check('To jest jego bluff. Nie chwalił się tym blefem.')
    assert len(matches2) == 1
    assert (matches2[0].from_pos, matches2[0].to_pos) == (40, 46)
    assert matches2[0].suggested_replacements == ['bluffem']


def test_word_coherency_call_independence(coherency_lt):
    """WordCoherencyRuleTest.testCallIndependence"""
    _assert_good(coherency_lt, 'To jest blef.')
    _assert_good(coherency_lt, 'A to nie bluff.')  # this won't be noticed, the calls are independent of each other


def test_word_coherency_match_position(coherency_lt):
    """WordCoherencyRuleTest.testMatchPosition"""
    rule_matches = coherency_lt.check('To jest blef. Ale nie bluff.')
    assert len(rule_matches) == 1
    assert (rule_matches[0].from_pos, rule_matches[0].to_pos) == (22, 27)


def test_word_coherency_complete_texts(coherency_lt):
    """WordCoherencyRuleTest.testRuleCompleteTexts"""
    lt = coherency_lt
    assert len(lt.check('To jest blef. Nie wierzysz? To naprawdę blef!')) == 0
    assert len(lt.check('To jest blef. Nie wierzysz? To naprawdę bluff!')) == 1
    assert len(lt.check('To jest bluff. Nie wierzysz? To naprawdę blef!')) == 1
    # also find full forms:
    assert len(lt.check('To jest blef. Nie wierzysz? Nie widzisz blefu!')) == 0
    assert len(lt.check('To jest blef. Nie wierzysz? Nie widzisz bluffu!')) == 1
    # cross-paragraph checks
    assert len(lt.check('Chwalił się blefem.\n\nTak było nie zmyślam. Ale bluff mu nie wyszedł.')) == 1


def test_word_coherency_rule_properties(lt):
    rule = WordCoherencyRule(messages_for('pl'), get_language('pl'))
    assert rule.get_id() == 'PL_WORD_COHERENCY'
    assert rule.get_description() == 'Jednolita pisownia wyrazów o obocznej dopuszczalnej pisowni'
    m, = rule.match(lt.analyze_text('To jest blef. Ale nie bluff.'))
    assert m.message == 'Formy „bluff” i „blef” zwykle nie powinny być używane jednocześnie.'


# --- MorfologikPolishSpellerRuleTest ---

@pytest.mark.skip(reason='spell checking is not ported: MorfologikPolishSpellerRuleTest tests '
                         'MorfologikPolishSpellerRule')
def test_morfologik_speller():
    """MorfologikPolishSpellerRuleTest.testMorfologikSpeller"""
