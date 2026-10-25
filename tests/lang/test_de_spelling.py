"""Port of org.languagetool.rules.de.GermanSpellerRuleTest (GermanSpellerRule:
the misspelling check, the ignore logic, compounds, word lists, the rule
matches and the suggestions; GermanSpellerRule is the default spelling rule
of German here, not one of its rules, see langtool.lang.de.spelling).

The tests of Morfologik itself (testMorfologikSpeller,
testMorfologikSpeller2, testMorfologikSpellerWithSpellingTxt) and the
interactive regression tests (testIgnoreMisspelledWordForRegressions,
testForRegressions) are @Ignore'd in Java and not ported. Positions of
rule matches are offsets in Python strings (code points)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.hunspell_rule import load_words
from langtool.lang.de.line_expander import LineExpander
from langtool.lang.de.spelling import GermanSpellerRule, SwissGermanSpellerRule
from langtool.messages import messages_for
from langtool.rules.base import SuggestedReplacement
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def german_de():
    return get_language('de-DE')


@pytest.fixture(scope='module')
def german_ch():
    return get_language('de-CH')


@pytest.fixture(scope='module')
def lt(german_de):
    return JLanguageTool(german_de)


@pytest.fixture(scope='module')
def rule(german_de):
    return GermanSpellerRule(messages_for('de'), german_de)


@pytest.fixture(scope='module')
def rule_ch(german_ch):
    return SwissGermanSpellerRule(messages_for('de'), german_ch)


def _match(rule, lt, text):
    return rule.match(lt.get_analyzed_sentence(text))


def _count(rule, lt, text):
    return len(rule.match(lt.get_analyzed_sentence(text), False))


def _check_all(cases, fn):
    failures = []
    for inp, expected in cases:
        got = fn(inp)
        if got != expected:
            failures.append((inp, expected, got))
    assert not failures, failures


def _assert_first_suggestion(rule, lt, inp, expected):
    matches = _match(rule, lt, inp)
    if expected is None:
        assert len(matches[0].suggested_replacements) == 0, matches[0].suggested_replacements
    else:
        assert matches, 'Matches: 0, expected at least one for %r' % inp
        assert matches[0].suggested_replacements[:1] == [expected], (inp, matches[0].suggested_replacements)


def _assert_not_suggestion(rule, lt, inp, not_expected):
    for match in _match(rule, lt, inp):
        assert not_expected not in match.suggested_replacements, (inp, not_expected)


def test_get_message(rule):
    """testGetMessage"""
    assert rule.get_message('aussen', SuggestedReplacement('außen')) == \
        "Nach einer Silbe aus zwei Vokalen (hier: au) schreibt man 'ß' statt 'ss'."
    assert rule.get_message('Strasse', SuggestedReplacement('Straße')) == \
        "Nach einer lang gesprochenen Silbe (hier: a) schreibt man 'ß' statt 'ss'."
    assert rule.get_message('STRASSE', SuggestedReplacement('STRAßE')) == 'Möglicher Tippfehler gefunden.'
    assert rule.get_message('nomral', SuggestedReplacement('normal')) == 'Möglicher Tippfehler gefunden.'


def test_ignore_misspelled_word(rule):
    """testIgnoreMisspelledWord"""
    _check_all(IGNORE_MISSPELLED, rule.ignore_potentially_misspelled_word)


def test_artig(rule):
    """testArtig"""
    for word in ('zigarrenartig', 'zigarrenartige', 'zigarrenartiger', 'zigarrenartiges', 'zigarrenartigen',
                 'zigarrenartigem', 'handlungsartig'):
        assert rule.ignore_word_at([word], 0), word
    for word in ('zigarrenartigex', 'handlungartig', 'arbeitartig', 'kostefrei', 'reglemäßig', 'hatfrei',
                 'geruchhemmend', 'aberabhängig'):
        assert not rule.ignore_word_at([word], 0), word


def test_split_words(rule, lt):
    """testSplitWords"""
    matches = _match(rule, lt, 'Das ist ein sher schöner Satz.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'sehr'
    assert matches[0].from_pos == 12
    assert matches[0].to_pos == 16
    matches = _match(rule, lt, 'Das sin die Optionen.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'ein'
    assert matches[0].suggested_replacements[1] == 'sind'
    matches = _match(rule, lt, 'Gibt es einen grund, dass…')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Grund'
    assert len(_match(rule, lt, 'Kryptomarktplatzes')) == 0


def test_get_only_suggestions(rule, lt):
    """testGetOnlySuggestions"""
    for word, expected in (('autentisch', 'authentisch'), ('brillianter', 'brillanter'),
                           ('autentischeres', 'authentischeres'), ('Autentischere', 'Authentischere')):
        suggestions = rule.get_only_suggestions(word)
        assert len(suggestions) == 1
        assert suggestions[0].replacement == expected
    matches = _match(rule, lt, 'Eine autentische Sache.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['authentische']


def test_filter_for_language(rule, rule_ch):
    """testFilterForLanguage"""
    list1 = ['Mafiosi s', 'foo']
    rule.filter_for_language(list1)
    assert list1 == ['foo']
    list2 = ['-bar', 'foo']
    rule.filter_for_language(list2)
    assert list2 == ['foo']
    list3 = ['Muße', 'foo']
    rule_ch.filter_for_language(list3)
    assert list3 == ['Musse', 'foo']


def test_sort_suggestion(rule):
    """testSortSuggestion"""
    assert rule.sort_suggestion_by_quality('fehler', ['fehla', 'xxx', 'Fehler']) == ['Fehler', 'fehla', 'xxx']
    assert rule.sort_suggestion_by_quality(
        'mülleimer', ['Mülheimer', '-mülheimer', 'Melkeimer', 'Mühlheimer', 'Mülleimer']) == \
        ['Mülleimer', 'Mülheimer', '-mülheimer', 'Melkeimer', 'Mühlheimer']
    # filtering out undesired inflected forms
    assert rule.sort_suggestion_by_quality(
        'glückklich', ['glücklich', 'glückliche', 'glücklichen', 'glücklicher', 'glückliches']) == ['glücklich']
    assert rule.sort_suggestion_by_quality(
        'Fußbaall', ['Fußball', 'Fußballs', 'Ausball', 'Fußball', 'Fußbälle']) == ['Fußball', 'Ausball']
    assert rule.sort_suggestion_by_quality(
        'glücklichr', ['glücklich', 'glückliche', 'glücklicher', 'glücklichen', 'glückliches']) == \
        ['glücklich', 'glückliche', 'glücklicher', 'glücklichen', 'glückliches']


def test_filtering_out_suggestions(rule, lt):
    """testFilteringOutSuggestions"""
    assert _match(rule, lt, 'glückklich')[0].suggested_replacements == ['glücklich', 'glücklichst']
    assert _match(rule, lt, 'erleddigt')[0].suggested_replacements == ['erledigt', 'erledige', 'erledigst']
    assert _match(rule, lt, 'glücklichhe')[0].suggested_replacements == ['glückliche', 'glücklichst']
    assert _match(rule, lt, 'glückklicher')[0].suggested_replacements == ['glücklicher', 'glücklichst']
    assert _match(rule, lt, 'großdenken')[0].suggested_replacements == [
        'Großdenken', 'groß denken', 'großdenkend', 'Grasstängel', 'Grasstängeln', 'Tröstungen', 'großdenkende',
        'großtunden', 'großtäten', 'tröstenden']


def test_prohibited(german_de):
    """testProhibited"""
    rule = GermanSpellerRule(messages_for('de'), german_de)
    rule.get_suggestions('')  # needed to force a proper init
    _check_all(PROHIBITED, rule.is_prohibited)


def test_filter_bad_suggestions(rule, lt):
    """testFilterBadSuggestions"""
    _assert_not_suggestion(rule, lt, 'nicht in euerer', 'i neuerer')
    _assert_not_suggestion(rule, lt, 'Ich rauche ne Zigarette', 'rauchen e')


def test_get_additional_top_suggestions(rule, lt):
    """testGetAdditionalTopSuggestions"""
    assert str(_match(rule, lt, 'dan')[0].suggested_replacements).startswith("['dann', 'Dan', 'den', 'an'")
    assert _match(rule, lt, 'konservierungsstoffstatistik')[0].suggested_replacements == \
        ['Konservierungsstoffstatistik']
    assert len(_match(rule, lt, 'konservierungsstoffsasdsasda')[0].suggested_replacements) == 0
    assert len(_match(rule, lt, 'Ventrolateral')) == 0
    assert len(_match(rule, lt, 'haben -sehr')) == 0
    # ignored due to ignoreCompoundWithIgnoredWord(), but still in ignore.txt -> ignore.txt must override this
    assert len(_match(rule, lt, 'Kleindung')) == 1
    assert _match(rule, lt, 'Majonäse.')[0].suggested_replacements == ['Mayonnaise']
    failures = []
    for inp, expected in FIRST_SUGGESTIONS:
        matches = _match(rule, lt, inp)
        got = matches[0].suggested_replacements[:1] if matches else None
        if got != [expected]:
            failures.append((inp, expected, got))
    assert not failures, failures


def test_add_ignore_words(german_de, german_ch, lt):
    """testAddIgnoreWords"""
    rule = GermanSpellerRule(messages_for('de'), german_de)
    rule.ensure_initialized()

    def correct(r, word):
        assert len(_match(r, lt, word)) == 0, word

    def incorrect(r, word):
        assert len(_match(r, lt, word)) == 1, word

    rule.add_ignore_words('Fußelmappse')
    correct(rule, 'Fußelmappse')
    rule.add_ignore_words('Fußelmappse/N')
    correct(rule, 'Fußelmappse')
    correct(rule, 'Fußelmappsen')
    rule.add_ignore_words('Toggeltröt/NS')
    correct(rule, 'Toggeltröt')
    correct(rule, 'Toggeltröts')
    correct(rule, 'Toggeltrötn')
    rule_ch = GermanSpellerRule(messages_for('de'), german_ch)
    rule_ch.ensure_initialized()
    rule_ch.add_ignore_words('Fußelmappse/N')
    correct(rule_ch, 'Fusselmappse')
    correct(rule_ch, 'Fusselmappsen')
    correct(rule, 'Coronapatienten')
    correct(rule, 'Coronapatienten.')
    correct(rule, 'Universitätsmitarbeitende')
    correct(rule, 'Universitätsmitarbeitenden')
    incorrect(rule, 'Xyzmitarbeitende')
    incorrect(rule, 'Xyzmitarbeitenden')
    incorrect(rule, 'Universitetsmitarbeitende')
    incorrect(rule, 'Universitetsmitarbeitenden')


def _speller_only_lt(language, rule):
    """JLanguageTool with only the spelling rule enabled
    (TestTools.disableAllRulesExcept(lt, GermanSpellerRule.RULE_ID); the
    spelling rule is not one of the rules of the language here, so it is
    added)"""
    lt = JLanguageTool(language)
    for r in lt.get_all_rules():
        lt.disable_rule(r.get_id())
    lt.add_rule(rule)
    return lt


def test_dash_and_hyphen_etc(german_de, rule, rule_ch, lt):
    """testDashAndHyphenEtc"""
    lt2 = _speller_only_lt(german_de, GermanSpellerRule(messages_for('de'), german_de))
    assert len(lt2.check('﻿-Product Development Coordinator')) == 2
    assert len(lt2.check('-Product Development Coordinator')) == 2
    assert len(lt2.check('﻿-Einx Test')) == 1
    assert len(lt2.check('﻿-Ein Test')) == 0
    assert len(lt2.check('Gratis E﻿-Book')) == 0
    # "-" as bullet point with no space:
    assert len(lt2.check('-Tee\n\n-Kaffee')) == 0
    matches1 = lt2.check('-Teex\n\n-Kaffee')
    assert len(matches1) == 1
    assert matches1[0].from_pos == 1
    assert matches1[0].to_pos == 5
    matches2 = lt2.check('- Teex\n\n-Kaffee')
    assert len(matches2) == 1
    assert matches2[0].from_pos == 2
    assert matches2[0].to_pos == 6
    _check_all(DASH_MATCH_COUNTS, lambda s: _count(rule, lt, s))
    # (a GermanSpellerRule for de-CH, like in Java)
    _check_all(DASH_MATCH_COUNTS_CH, lambda s: _count(GermanSpellerRule(messages_for('de'), get_language('de-CH')),
                                                      lt, s))


def test_get_suggestions_from_spelling_txt(german_de, german_ch):
    """testGetSuggestionsFromSpellingTxt"""
    rule_germany = GermanSpellerRule(messages_for('de'), german_de)
    rule_germany.ensure_initialized()
    assert rule_germany.get_suggestions('Ligafußboll') == ['Ligafußball']  # from spelling.txt
    # to prevent OutOfMemoryErrors: do not create hyphenated compounds consisting of >3 parts
    assert rule_germany.get_suggestions('free-and-open-source') == []
    rule_swiss = GermanSpellerRule(messages_for('de'), german_ch)
    rule_swiss.ensure_initialized()
    assert rule_swiss.get_suggestions('Ligafußboll') == ['Ligafussball']
    assert rule_swiss.get_suggestions('konfliktbereid') == ['konfliktbereit', 'konfliktbereite']
    assert rule_swiss.get_suggestions('konfliktbereitel') == [
        'konfliktbereite', 'konfliktbereiten', 'konfliktbereitem', 'konfliktbereiter', 'konfliktbereites',
        'konfliktbereit']


def test_ignore_word(german_de, german_ch):
    """testIgnoreWord"""
    rule_germany = GermanSpellerRule(messages_for('de'), german_de)
    rule_germany.ensure_initialized()
    assert rule_germany.ignore_word_at(['einPseudoWortFürLanguageToolTests'], 0)  # from ignore.txt
    # compounds formed from two valid words, but still incorrect:
    assert not rule_germany.ignore_word_at(['Hundhütte'], 0)
    assert not rule_germany.ignore_word_at(['Frauversteher'], 0)
    assert not rule_germany.ignore_word_at(['Wodkasglas'], 0)
    assert not rule_germany.ignore_word_at(['Author'], 0)
    assert not rule_germany.ignore_word_at(['SecondhandWare'], 0)  # from spelling.txt formed compound
    assert not rule_germany.ignore_word_at(['MHDware'], 0)  # from spelling.txt formed compound
    rule_swiss = GermanSpellerRule(messages_for('de'), german_ch)
    rule_swiss.ensure_initialized()
    assert rule_swiss.ignore_word_at(['einPseudoWortFürLanguageToolTests'], 0)
    assert not rule_swiss.ignore_word_at(['Ligafußball'], 0)  # 'ß' never accepted for Swiss


def common_german_asserts(rule, lt):
    """commonGermanAsserts"""
    _check_all(COMMON_GERMAN, lambda s: _count(rule, lt, s))


def test_rule_with_germany_german(rule, lt):
    """testRuleWithGermanyGerman"""
    common_german_asserts(rule, lt)
    assert _count(rule, lt, 'Der äußere Übeltäter.') == 0  # umlauts
    assert _count(rule, lt, 'Der äussere Übeltäter.') == 1
    assert _count(rule, lt, "Die Mozart'sche Sonate.") == 0
    assert _count(rule, lt, 'Einbusse') == 1
    assert _count(rule, lt, 'Einbussen') == 1


def test_rule_with_austrian_german():
    """testRuleWithAustrianGerman"""
    from langtool.lang.de.spelling import AustrianGermanSpellerRule
    language = get_language('de-AT')
    rule = AustrianGermanSpellerRule(messages_for('de'), language)
    lt = JLanguageTool(language)
    common_german_asserts(rule, lt)
    assert _count(rule, lt, 'Der äußere Übeltäter.') == 0  # umlauts
    assert _count(rule, lt, 'Der äussere Übeltäter.') == 1


def test_rule_with_swiss_german(rule_ch, german_ch):
    """testRuleWithSwissGerman"""
    lt = JLanguageTool(german_ch)
    common_german_asserts(rule_ch, lt)
    assert _count(rule_ch, lt, 'Der äußere Übeltäter.') == 1  # ß not allowed in Swiss
    assert _count(rule_ch, lt, 'Der äussere Übeltäter.') == 0  # ss is used instead of ß
    assert _count(rule_ch, lt, 'Einbusse') == 0
    assert _count(rule_ch, lt, 'Einbussen') == 0


def test_get_suggestions(rule):
    """testGetSuggestions"""
    failures = []
    for inp, expected_terms in CORRECTIONS:
        suggestions = rule.get_suggestions(inp)
        missing = [t for t in expected_terms if t not in suggestions]
        if missing or (not expected_terms and suggestions):
            failures.append((inp, expected_terms, suggestions))
    assert not failures, failures


def test_suggestions(rule, lt):
    """testSuggestions"""
    _assert_first_suggestion(rule, lt, 'informationnen.', 'Informationen')
    _assert_first_suggestion(rule, lt, 'Kundigungsfrist.', 'Kündigungsfrist')
    _assert_first_suggestion(rule, lt, 'aufgeregegt.', 'aufgeregt')
    _assert_first_suggestion(rule, lt, 'informationnen...', 'Informationen..')  # not 100% perfect, but we can live with this...
    _assert_first_suggestion(rule, lt, 'arkbeiten-', 'arbeiten')
    # commas are actually not part of the word, so the suggestion doesn't include them:
    _assert_first_suggestion(rule, lt, 'informationnen,', 'Informationen')
    _assert_first_suggestion(rule, lt, 'ALT-TARIF,', None)
    _assert_not_suggestion(rule, lt, 'Pseudo-Rebellentum', 'Pseudo- Rebellentum')
    _assert_not_suggestion(rule, lt, 'Pseudo-Rebellentum', 'Pseudo--Rebellentum')
    _assert_not_suggestion(rule, lt, 'Virtualisierungs-Layer', 'Virtualisierungs--Layer')
    _assert_not_suggestion(rule, lt, 'Mediations-Background', 'Mediation s-Background')
    _assert_first_suggestion(rule, lt, 'ALT-ÜBERSICHT,', None)
    _assert_first_suggestion(rule, lt, 'Sakralkultur,', None)
    _assert_first_suggestion(rule, lt, 'Auschwitzmythxs,', None)  # correction prevented by lcDoNotSuggestWords
    # "algen" was accepted in de_DE.dic as compound part, we removed it:
    _assert_first_suggestion(rule, lt, 'Wursteinalgen', 'Wursteinlagen')
    _assert_first_suggestion(rule, lt, 'Wursteinalge', 'Wursteinlage')


def test_get_suggestion_order(rule):
    """testGetSuggestionOrder"""
    failures = []
    for inp, expected_terms in ORDER:
        suggestions = rule.get_suggestions(inp)
        if suggestions[:len(expected_terms)] != list(expected_terms):
            failures.append((inp, expected_terms, suggestions))
    assert not failures, failures


def test_is_misspelled(rule):
    """testIsMisspelled"""
    _check_all(MISSPELLED, rule.is_misspelled)


def test_gender_compound(rule, lt):
    """testGenderCompound"""
    _check_all(GENDER, lambda s: _count(rule, lt, s))


def test_position(rule, lt):
    """testPosition"""
    match1 = _match(rule, lt, "Er ist entsetzt, weil beim 'Wiederaufbau' das original-gotische Achsfenster mit "
                              "reichem Maßwerk ausgebaut und an die südliche TeStWoRt gesetzt wurde.")
    assert len(match1) == 1
    assert match1[0].from_pos == 126
    assert match1[0].to_pos == 134


def test_morfologik_suggestions_workaround(german_de, lt):
    """testMorfologikSuggestionsWorkaround: number of suggestions seems to
    depend on previously checked text, fixed by not reusing morfologik
    Speller object"""
    rule1 = GermanSpellerRule(messages_for('de'), german_de)
    rule2 = GermanSpellerRule(messages_for('de'), german_de)
    sentence1 = 'Das Absinken der Motordrehzahl bfi größeren Geschwindigkeiten war.'
    sentence2 = 'Welche die Eidgenossenschaft ls Staatenbund wiederhergestellt hat.'
    matches11 = _match(rule1, lt, sentence1)
    matches12 = _match(rule1, lt, sentence2)
    matches22 = _match(rule2, lt, sentence2)
    matches21 = _match(rule2, lt, sentence1)
    assert all(len(m) == 1 for m in (matches11, matches12, matches21, matches22))
    assert len(matches11[0].suggested_replacements) == len(matches21[0].suggested_replacements)
    assert len(matches12[0].suggested_replacements) == len(matches22[0].suggested_replacements)
    # a bug caused "bie" to be ignored:
    assert len(_match(rule1, lt, 'laut Beispielen bie')) == 1


def test_prohibit_vs_spelling_de_ch(german_de):
    """testProhibitVsSpellingDeCH"""
    from langtool.hunspell_rule import read_lines, resource_file
    expander = LineExpander()

    def expand_lines(lines):
        expanded = []
        for line in lines:
            expanded.extend(expander.expand_line(line))
        return expanded

    prohibit = set(expand_lines(load_words(german_de, '/de/hunspell/prohibit.txt')))
    de_ch = expand_lines(read_lines(resource_file(german_de, '/de/hunspell/spelling-de-CH.txt')))
    for de_ch_word in de_ch:
        assert de_ch_word not in prohibit, \
            "'%s' is both in prohibit.txt (used for all de-.. variants) and in spelling-de-CH.txt" % de_ch_word
        assert 'ß' not in de_ch_word, \
            "'%s' from spelling-de-CH.txt contains 'ß' - should be 'ss' instead" % de_ch_word


# --- test data (from GermanSpellerRuleTest) ---

IGNORE_MISSPELLED = [
    ('Wahlkamp', False),
    ('Ahmenforscherin', False),
    ('Bachwettbewerb', False),
    ('Berlinhauptbahnhof', False),
    ('Schwedenreise', True),
    ('Erwachsenenintensivkurse', True),
    ('Horizontalbohrtechnik', True),
    ('Bogenschiessen', False),
    ('Badefenster', False),
    ('Badspaß', False),
    ('Widersachen', False),
    ('Widerherstellung', False),
    ('Journalistendramas', True),
    ('Bürokratieaufbau', True),
    ('Bestangebotsklauseln', True),
    ('Wendeplatte', True),
    ('Tassentrio', True),
    ('Ausbiegemöglichkeit', True),
    ('Lipochrom', True),
    ('Ostteil', True),
    ('Ostenteil', False),
    ('Perspektivwechsel', True),
    ('Perspektivewechsel', False),
    ('Suchemaschine', False),
    ('Sprachvariante', True),
    ('Sprachevariante', False),
    ('Sprachenvariante', False),
    ('Kontrollgremiums', True),
    ('Kontrollegremiums', False),
    ('Kontrollengremiums', False),
    ('Leuchtfunktion', True),
    ('Leuchtefunktion', False),
    ('Schulstreit', True),
    ('Schulestreit', False),
    ('Stelleplätze', False),
    ('Herzensanliegen', True),
    ('Herzenanliegen', False),
    ('Vornamensliste', True),
    ('Wörterbuch', True),
    ('Wortgrenze', True),
    ('Weltklimaveränderung', True),
    ('Weltbummler', False),
    ('Demokratenversammlung', True),
    ('Zahnbürsten', True),
    ('Zähnebürsten', True),
    ('Zähnebürste', False),
    ('Apfelstehlen', True),
    ('Äpfelstehlen', True),
    ('Zwiebelschneiden', True),
    ('Zwiebelnschneiden', True),
    ('Fußballspielen', True),
    ('Fußbällespielen', False),
    ('Abbiegemöglichkeit', True),
    ('Cholesterinwiederaufnahmehemmer', True),
    ('Kennenlernmöglichkeit', True),
    ('Konstruktionsverfahren', True),
    ('Wölkchenbildung', True),
    ('Abschlussgruße', False),
    ('Offenlegungsfrist', True),
    ('Hospizgemeinschaft', True),
    ('Azubikommt', False),
    ('Lasstest', False),
    ('Ablassbild', True),
    ('Wachtums-Pistole', False),
    ('Discorum', False),
    ('Arbeitsgeber', False),
    ('Arbeitsgeberverhandlungen', False),
    ('Arbeitplatz', False),
    ('Rechtlage', False),
    ('Rechtextremismus', False),
    ('Rechtanwälten', False),
    ('Rechtfertigungsgrund', True),
    ('Rechtsfertigungsgrund', False),
    ('Ausleihstelle', True),
    ('Aus-leihstelle', False),
    ('AusLeihStelle', False),
    ('Trauringkollektionen', True),
    ('Vorraus', False),
    ('Weinkühlschrank', True),
    ('Weinkühl-schrank', False),
    ('Weinskühlschrank', False),
    ('Weinsskühlschrank', False),
    ('Schokobrunnen', True),
    ('Schokosbrunnen', False),
    ('Gensfleisch', False),
    ('Grossmächten', False),
    ('Aussichtplattform', False),
    ('Datumangabe', False),
    ('Hundefutterschachtel', True),
    ('Leistungsversuchstest', True),
    ('Nachuntersuchungstest', True),
    ('Robustheitsabstände', True),
    ('Robustheitsabstände.', True),
    ('Absenkungsvorgaben', True),
    ('Prioritätsdings', True),
    ('Prioritätsdings.', True),
    ('Haltungsschäden', True),
    ('Prioritäts-Dings', True),
    ('Prioritäts-Dings.', True),
    ('Haltungs-Schäden', True),
    ('Kritzelcafé', True),
    ('haltungschäden', False),
    ('haltungs-schäden', False),
    ('haltungs-Schäden', False),
    ('Haltungschäden', False),
    ('Haltung-Schäden', False),
    ('Hultungsschäden', False),
    ('Hultungs-Schäden', False),
    ('Haltungsscheden', False),
    ('Haltungs-Scheden', False),
    ('HaltungsSchäden', False),
    ('Haltungsei', False),
    ('Haltungs-Ei', False),
    ('Leistungsnach', False),
    ('Antwortzugeschnitten', False),
    ('Leistungsgegangen', False),
    ('Leistungsgegangen.', False),
    ('Leistungsversuchstestnachweis', False),
    ('Leistung', False),
    ('Leistungs', False),
    ('Anschauungswiese', False),
    ('Fakultätsaal', False),
    ('Implementierungs-pflicht', False),
    ('Sachsenmeisterschaf', False),
    ('Agensprinzip', True),
    ('SEO-ExpertIn', True),
    ('SEO-Expert*in', True),
    ('SEO-Expert:in', True),
    ('SEO-Expert_in', True),
    ('SEO-Expert/-in', True),
    ('SEO-ExpertInnen', True),
    ('SEO-Expert*innen', True),
    ('SEO-Expert:innen', True),
    ('SEO-Expert_innen', True),
    ('SEO-Expert/-innen', True),
    ('Bürge*in', False),
    ('ArbeitnehmerInnenschutzgesetz', True),
    ('Arbeitnehmer*innenschutzgesetz', True),
    ('Arbeitnehmer:innenschutzgesetz', True),
    ('Arbeitnehmer_innenschutzgesetz', True),
    ('Arbeitnehmer/-innenschutzgesetz', True),
    ('PDFversion', False),
    ('AktienIndex', False),
    ('EisenbahnerInnern', False),
    ('Eisenbahner*innern', False),
    ('Eisenbahner/-innern', False),
    ('Ireland', False),
    ('Karnevalmuseum', True),
    ('Alkoholgenuß', False),
    ('Actionsspaß', False),
    ('Aktionswoche', True),
    ('Aktionwoche', False),
    ('Aufschwungsphase', False),
    ('Absprungsrate', False),
    ('Ahornswald', False),
    ('Aluminiumssockel', False),
    ('Antwortszeiten', False),
    ('Austauschsprogramms', False),
    ('Bahnstrasse', False),
    ('Bausstellen', False),
    ('Bergstrasse', False),
    ('Berufungssausschuss', False),
    ('Betreffszeile', False),
    ('Bundeswasserstrassen', False),
    ('Bunsenbrennerflamme', True),
    ('Abstiegzone', False),
    ('Abstimmungbeschluss', False),
    ('Dorfstrasse', False),
    ('Kitasausbau', False),
    ('Linkelemente', True),
    ('Linksdrehung', True),
    ('Linkpartei', False),
    ('Linksportal', False),
    ('Muttertagskarte', True),
    ('Muttertagkarte', False),
    ('Verbandmaterial', True),
    ('Verbandsmaterial', True),
    ('Verbandgemeinde', False),
    ('Sonntagnachmittag', True),
    ('Sonntagsfahrer', True),
    ('Sonntagfahrer', False),
    ('Gerätebezeichnung', True),
    ('Gerätbezeichnung', False),
    ('Abflußleitung', False),
    ('Abflussleitung', True),
    ('Grünschloß', False),
    ('Grünschloss', True),
    ('Bewußtseinswandels', False),
    ('Bewusstseinswandels', True),
    ('Meerweine', False),
]

FIRST_SUGGESTIONS = [
    ('Schöler-', 'Schüler-'),
    ('wars.', 'war es'),
    ('konservierungsstoffe', 'Konservierungsstoffe'),
    ('denkte', 'dachte'),
    ('schwimmte', 'schwamm'),
    ('gehte', 'ging'),
    ('greifte', 'griff'),
    ('geschwimmt', 'geschwommen'),
    ('gegeht', 'gegangen'),
    ('getrinkt', 'getrunken'),
    ('gespringt', 'gesprungen'),
    ('geruft', 'gerufen'),
    ('Netflix-Flm', 'Netflix-Film'),
    ('Bund-Länder-Kommissio', 'Bund-Länder-Kommission'),
    ('Emailaccount', 'E-Mail-Account'),
    ('Emailacount', 'E-Mail-Account'),
    ('millionmal', 'Million Mal'),
    ('millionenmal', 'Millionen Mal'),
    ('geupdated', 'upgedatet'),
    ('rosanen', 'rosa'),
    ('missionariesierung', 'Missionierung'),
    ('angehangener', 'angehängter'),
    ('aufgehangene', 'aufgehängte'),
    ('Germanistiker', 'Germanist'),
    ('Germanistikern', 'Germanisten'),
    ('Germanistikerin', 'Germanistin'),
    ('erhöherung', 'Erhöhung'),
    ('aufjedenfall', 'auf jeden Fall'),
    ('Aufjedenfall', 'Auf jeden Fall'),
    ('funkzunierende', 'funktionierende'),
    ('funkzuniert', 'funktioniert'),
    ('Mayonese', 'Mayonnaise'),
    ('Majonäse', 'Mayonnaise'),
    ('Salatmajonäse', 'Salatmayonnaise'),
    ('Physiklaborants', 'Physiklaboranten'),
    ('interkurelle', 'interkulturelle'),
    ('Zuende', 'Zu Ende'),
    ('zuende', 'zu Ende'),
    ('wolt', 'wollt'),
    ('allmähliges', 'allmähliches'),
    ('Allmähllig', 'Allmählich'),
    ('Probiren', 'Probieren'),
    ('gesetztreu', 'gesetzestreu'),
    ('wikiche', 'wirkliche'),
    ('kongratulierst', 'gratulierst'),
    ('Makeup', 'Make-up'),
    ('profesionehlle', 'professionelle'),
    ('professionählles', 'professionelles'),
    ('gehnemigung', 'Genehmigung'),
    ('korregierungen', 'Korrekturen'),
    ('Korrigierungen', 'Korrekturen'),
    ('Ticketresawihrung', 'Ticketreservierung'),
    ('gin', 'ging'),
    ('Gleichrechtige', 'Gleichberechtigte'),
    ('unnützliche', 'unnütze'),
    ('hälst', 'hältst'),
    ('erhälst', 'erhältst'),
    ('Verstehendnis', 'Verständnis'),
    ('schmetrlinge', 'Schmetterlinge'),
    ('einlamienirte', 'laminierte'),
    ('Assecoires', 'Accessoires'),
    ('Vorraussetzungen', 'Voraussetzungen'),
    ('aufwechselungsreichem', 'abwechslungsreichem'),
    ('nachwievor', 'nach wie vor'),
    ('letztenendes', 'letzten Endes'),
    ('mitanader', 'miteinander'),
    ('nocheimal', 'noch einmal'),
    ('konflikationen', 'Komplikationen'),
    ('unswar', 'und zwar'),
    ('fomelare', 'Formulare'),
    ('immoment', 'im Moment'),
    ('inordnung', 'in Ordnung'),
    ('inbälde', 'in Bälde'),
    ('unaufbesichtigt', 'unbeaufsichtigt'),
    ('uberaschend', 'überraschend'),
    ('uberagendes', 'überragendes'),
    ('unabsichtiges', 'unabsichtliches'),
    ('organisatives', 'organisatorisches'),
    ('Medallion', 'Medaillon'),
    ('diagnosiere', 'diagnostiziere'),
    ('diagnoziert', 'diagnostiziert'),
    ('durschnittliche', 'durchschnittliche'),
    ('durschnitliche', 'durchschnittliche'),
    ('durchnitliche', 'durchschnittliche'),
    ('Durschnittswerte', 'Durchschnittswerte'),
    ('Durschnittsbürgers', 'Durchschnittsbürgers'),
    ('Heileit', 'Highlight'),
    ('todesbedrohende', 'lebensbedrohende'),
    ('todesbedrohliches', 'lebensbedrohliches'),
    ('einfühlsvoller', 'einfühlsamer'),
    ('folklorisch', 'folkloristisch'),
    ('Religiösischen', 'Religiösen'),
    ('reschaschiert', 'recherchiert'),
    ('bißjen', 'bisschen'),
    ('bisien', 'bisschen'),
    ('Gruessen', 'Grüßen'),
    ('Pearl-Harbour', 'Pearl Harbor'),
    ('Autonomität', 'Autonomie'),
    ('Kompatibelkeit', 'Kompatibilität'),
    ('Sensibelkeit', 'Sensibilität'),
    ('Flexibelkeit', 'Flexibilität'),
    ('WiFi-Direkt', 'Wi-Fi Direct'),
    ('Wi-Fi-Direct', 'Wi-Fi Direct'),
    ('hofen', 'hoffen'),
    ('frustuck', 'Frühstück'),
    ('recourcen', 'Ressourcen'),
    ('familiärische', 'familiäre'),
    ('familliarisches', 'familiäres'),
    ('sommerverie', 'Sommerferien'),
    ('thelepatie', 'Telepathie'),
    ('artz', 'Arzt'),
    ('berücksichtung', 'Berücksichtigung'),
    ('okey', 'okay'),
    ('Energiesparung', 'Energieeinsparung'),
    ('Deluxe-Version', 'De-luxe-Version'),
    ('De-luxe-Champagnr', 'De-luxe-Champagner'),
    ('problemhafte', 'problembehaftete'),
    ('solltes', 'solltest'),
    ('Kilimanjaro', 'Kilimandscharo'),
    ('unzerbrechbare', 'unzerbrechliche'),
    ('voraussichtige', 'voraussichtliche'),
    ('Aleine', 'Alleine'),
    ('abenzu', 'ab und zu'),
    ('ergeitz', 'Ehrgeiz'),
    ('chouch', 'Couch'),
    ('kontaktfreundliche', 'kontaktfreudige'),
    ('angestegt', 'angesteckt'),
    ('festellt', 'feststellt'),
    ('liqide', 'liquide'),
    ('gelessen', 'gelesen'),
    ('Getrixe', 'Getrickse'),
    ('Naricht', 'Nachricht'),
    ('konektschen', 'Connection'),
    ('Neukundenaquise', 'Neukundenakquise'),
    ('Gehorsamkeitsverweigerung', 'Gehorsamsverweigerung'),
    ('leinensamens', 'Leinsamens'),
    ('Oldheimer', 'Oldtimer'),
    ('verhing', 'verhängte'),
    ('vorallendingen', 'vor allen Dingen'),
    ('unternehmenslüstige', 'unternehmungslustige'),
    ('proffesionaler', 'professioneller'),
    ('gesundliches', 'gesundheitliches'),
    ('eckelt', 'ekelt'),
    ('geherte', 'geehrte'),
    ('Kattermesser', 'Cuttermesser'),
    ('antisemitistischer', 'antisemitischer'),
    ('unvorsehbares', 'unvorhersehbares'),
    ('Würtenberg', 'Württemberg'),
    ('Baden-Würtenbergs', 'Baden-Württembergs'),
    ('indifiziert', 'identifiziert'),
    ('verblüte', 'verblühte'),
    ('dreitem', 'drittem'),
    ('zukuenftliche', 'zukünftige'),
    ('schwarzwälderkirschtorte', 'Schwarzwälder Kirschtorte'),
    ('kolegen', 'Kollegen'),
    ('gerechtlichkeit', 'Gerechtigkeit'),
    ('Zuverlässlichkeit', 'Zuverlässigkeit'),
    ('jedwilliger', 'jedweder'),
    ('Betriebsratzimmern', 'Betriebsratszimmern'),
    ('ausiehst', 'aussiehst'),
    ('unterbemittelnde', 'minderbemittelte'),
    ('koregiert', 'korrigiert'),
    ('Gelangenheitsbestätigungen', 'Gelangensbestätigungen'),
    ('mitenand', 'miteinander'),
    ('hinunher', 'hin und her'),
    ('Xter', 'X-ter'),
    ('Kaufentfehlung', 'Kaufempfehlung'),
    ('unverzeilige', 'unverzeihliche'),
    ('Addons', 'Add-ons'),
    ('Mitgliederinnen', 'Mitglieder'),
    ('Feinleiner', 'Fineliner'),
    ('größester', 'größter'),
    ('verhäufte', 'gehäufte'),
    ('naheste', 'nächste'),
    ('fluoreszenzierend', 'fluoreszierend'),
    ('revalierender', 'rivalisierender'),
    ('häherne', 'härene'),
    ('Portfolien', 'Portfolios'),
    ('Nivo', 'Niveau'),
    ('dilletanten', 'Dilettanten'),
    ('intersannt', 'interessant'),
    ('allereinzigstem', 'einzigem'),
    ('Einzigste', 'Einzige'),
    ('namenhafte', 'namhafte'),
    ('homeophatisch', 'homöopathisch'),
    ('verswindet', 'verschwindet'),
    ('Durschnitt', 'Durchschnitt'),
    ('Durchnitts', 'Durchschnitts'),
    ('überdurschnittlichem', 'überdurchschnittlichem'),
    ('Unterdurschnittlicher', 'Unterdurchschnittlicher'),
    ('höchstwahrliche', 'höchstwahrscheinliche'),
    ('vidasehen', 'wiedersehen'),
    ('striktliches', 'striktes'),
    ('preventiert', 'verhindert'),
    ('zurverfügung', 'zur Verfügung'),
    ('trationelle', 'traditionelle'),
    ('achsiales', 'axiales'),
    ('famiele', 'Familie'),
    ('miters', 'Mieters'),
    ('besigen', 'besiegen'),
    ('verziehrte', 'verzierte'),
    ('pieken', 'piken'),
    ('Erstsemesterin', 'Erstsemester'),
    ('zauberlicher', 'zauberischer'),
    ('assessoars', 'Accessoires'),
    ('könntes', 'könntest'),
    ('Casemangement', 'Case Management'),
    ('Anolierung', 'Annullierung'),
    ('Liaisonen', 'Liaisons'),
    ('kinderlichem', 'kindlichem'),
    ('wiedersprichst', 'widersprichst'),
    ('unproffesionele', 'unprofessionelle'),
    ('gefrustuckt', 'gefrühstückt'),
    ('Durführung', 'Durchführung'),
    ('verheielte', 'verheilte'),
    ('ausgewönlich', 'außergewöhnlich'),
    ('unausweichbaren', 'unausweichlichen'),
    ('Dampfschiffahrtskapitän', 'Dampfschifffahrtskapitän'),
    ('Helfes-Helfern', 'Helfershelfern'),
    ('Intelligentsbestie', 'Intelligenzbestie'),
    ('avantgardische', 'avantgardistische'),
    ('gewohnheitsbedürftigen', 'gewöhnungsbedürftigen'),
    ('patroliert', 'patrouilliert'),
    ('beidiges', 'beides'),
    ('revolutioniesiert', 'revolutioniert'),
    ('Copyride', 'Copyright'),
    ('angesehende', 'angesehene'),
    ('angesehendsten', 'angesehensten'),
    ('frühstücksbüfé', 'Frühstücksbuffet'),
    ('deutsprachiger', 'deutschsprachiger'),
    ('gehäckelten', 'gehäkelten'),
    ('Alterego', 'Alter Ego'),
    ('Makeupstylistin', 'Make-up-Stylistin'),
    ('islamophobische', 'islamophobe'),
    ('Fedbäck', 'Feedback'),
    ('desöfterem', 'des Öfteren'),
    ('momentmal', 'Moment mal'),
    ('eingängliche', 'eingängige'),
    ('kusengs', 'Cousins'),
    ('Influenzer', 'Influencer'),
    ('kaperzität', 'Kapazität'),
    ('ausversehendlich', 'aus Versehen'),
    ('tränern', 'Trainern'),
    ('Teiming', 'Timing'),
    ('inzinierung', 'Inszenierung'),
    ('weireten', 'weiteren'),
    ('Nivoschalters', 'Niveauschalters'),
    ('exhibitionischer', 'exhibitionistischer'),
    ('geschalten', 'geschaltet'),
    ('unterschiebenes', 'unterschriebenes'),
    ('Umbekwehmer', 'Unbequemer'),
    ('Unbequemliche', 'Unbequeme'),
    ('unbequemlichstes', 'unbequemstes'),
    ('Desatören', 'Deserteuren'),
    ('Panelen', 'Paneelen'),
    ('Deja-Vue', 'Déjà-vu'),
    ('Dejavou', 'Déjà-vu'),
    ('Cremefraiche', 'Crème fraîche'),
    ('aragemont', 'Arrangement'),
    ('Diseing', 'Design'),
    ('Lieradresse', 'Lieferadresse'),
    ('Boykutierung', 'Boykottierung'),
    ('rethorisch', 'rhetorisch'),
    ('anschliessliche', 'anschließende'),
    ('Überstreitung', 'Überschreitung'),
    ('werkzeug.', 'Werkzeug'),
    ('Wärkzeug.', 'Werkzeug'),
    ('Ingineuer', 'Ingenieur'),
    ('Panacotta', 'Panna cotta'),
    ('Ärcker', 'Erker'),
    ('genrealistischer', 'generalistischer'),
    ('schweinerosane', 'schweinchenrosa'),
    ('anstecklichen', 'ansteckenden'),
    ('geflechtetes', 'geflochtenes'),
    ('ärtlichem', 'ärztlichem'),
    ('großzüges', 'großzügiges'),
    ('Einbahnfrei', 'Einwandfrei'),
    ('einbandfreier', 'einwandfreier'),
    ('Beanstandigung', 'Beanstandung'),
    ('Beanstandigungen', 'Beanstandungen'),
    ('zweiundhalb', 'zweieinhalb'),
    ('dreiundhalb', 'dreieinhalb'),
    ('Zuguterletzt', 'Zu guter Letzt'),
    ('guterletzt', 'guter Letzt'),
    ('unfährer', 'unfairer'),
    ('unfäre', 'unfaire'),
    ('medikatöses', 'medikamentöses'),
    ('versendliches', 'versehentliches'),
    ('Nootbooks', 'Notebooks'),
    ('Eigtl', 'Eigtl.'),
    ('pflanzige', 'pflanzliche'),
    ('geblogt', 'gebloggt'),
    ('ähliche', 'ähnliche'),
    ('entfängt', 'empfängt'),
    ('verewiglichte', 'verewigte'),
    ('zeritifierte', 'zertifizierte'),
    ('gerähte', 'Geräte'),
    ('pirsing', 'Piercing'),
    ('behilfreiches', 'behilfliches'),
    ('einsichtbar', 'einsehbar'),
    ('vollrichtest', 'verrichtest'),
    ('Vollrichtet', 'Verrichtet'),
    ('bedingslosem', 'bedingungslosem'),
    ('überstenden', 'berstenden'),
    ('abbonierst', 'abonnierst'),
    ('Apeliere', 'Appelliere'),
    ('voltieschiert', 'voltigiert'),
    ('meistverkaufteste', 'meistverkaufte'),
    ('unleshaftem', 'unleserlichem'),
    ('glaubenswürdig', 'glaubwürdig'),
    ('nivovolle', 'niveauvolle'),
    ('niwovoller', 'niveauvoller'),
    ('notgezwungender', 'notgedrungener'),
    ('misstraurig', 'misstrauisch'),
    ('Aux-Anschluss', 'AUX-Anschluss'),
    ('Wi', 'Wie'),
    ('Verspäterung', 'Verspätung'),
    ('groesste', 'größte'),
    ('tefonische', 'telefonische'),
    ('optimalisiert', 'optimiert'),
    ('introvertisches', 'introvertiertes'),
    ('Entercotte', 'Entrecôte'),
    ('hirachie', 'Hierarchie'),
    ('amierte', 'armierte'),
    ('Versiehrten', 'Versierten'),
    ('durchsichtbar', 'durchsichtig'),
    ('offensichtiges', 'offensichtliches'),
    ('zurverfühgung', 'zur Verfügung'),
    ('Bewusstliches', 'Bewusstes'),
    ('leidensvolle', 'leidvolle'),
    ('augensichtlich', 'augenscheinlich'),
    ('Krankenbrüdern', 'Krankenpflegern'),
    ('Lan-Kabel', 'LAN-Kabel'),
    ('perfekteste', 'perfekte'),
    ('gleichtig', 'gleichzeitig'),
    ('vorsichgeht', 'vor sich geht'),
    ('Simkarte', 'SIM-Karte'),
    ('Pineingabe', 'PIN-Eingabe'),
    ('carnivorischen', 'karnivoren'),
    ('Zaubererinnen', 'Zauberinnen'),
    ('erroriere', 'eruiere'),
    ('erroriert', 'eruiert'),
    ('Second-Hand-Shops', 'Secondhandshops'),
    ('mediterranischer', 'mediterraner'),
    ('unterschreibungsfähige', 'unterschriftsfähige'),
    ('interplementiert', 'implementiert'),
    ('hochalterlich', 'hochmittelalterlich'),
    ('posiniert', 'positioniert'),
    ('russophobische', 'russophobe'),
    ('unsachmässiger', 'unsachgemäßer'),
    ('modernisches', 'modernes'),
    ('intapretation', 'Interpretation'),
    ('Rethorikkurses', 'Rhetorikkurses'),
    ('Deprisonen', 'Depressionen'),
    ('battalione', 'Bataillone'),
    ('Besuchungsverbot', 'Besuchsverbot'),
    ('widersprüchiges', 'widersprüchliches'),
    ('camelionhafte', 'chamäleonhafte'),
    ('angehangenen', 'angehängten'),
    ('spätrige', 'spätere'),
    ('faustigen', 'faustdicken'),
    ('Belastungsekgs', 'Belastungs-EKGs'),
    ('-Teex', 'Tee'),
    ('- Teex', 'Tee'),
    ('- Kaffeex', 'Kaffee'),
    ('E -Commerce', 'E-Commerce'),
    ('Intranzparentheit', 'Intransparenz'),
    ('aufkeinenfal', 'auf keinen Fall'),
    ('unverantwortunglosen', 'verantwortungslosen'),
    ('unverantwortungslose', 'verantwortungslose'),
    ('neuliche', 'neuerliche'),
    ('kompensioniert', 'kompensiert'),
    ('desinfektionierender', 'desinfizierender'),
    ('Desinfektioniert', 'Desinfiziert'),
    ('desinfektionierst', 'desinfizierst'),
    ('Neuhichkeit', 'Neuigkeit'),
    ('neuhichkeiten', 'Neuigkeiten'),
    ('Maßname', 'Maßnahme'),
    ('Maßnamen', 'Maßnahmen'),
    ('Analysemaßname', 'Analysemaßnahme'),
    ('Analysemaßnamen', 'Analysemaßnahmen'),
    ('Analysemassnamen', 'Analysemaßnahmen'),
]

DASH_MATCH_COUNTS = [
    ('Ist doch - gut', 0),
    ('Ist doch -- gut', 0),
    ('Stil- und Grammatikprüfung gut', 0),
    ('Stil- bzw. Grammatikprüfung gut', 0),
    ('Oliven- und Mandelöl', 0),
    ('Stil-, Text- und Grammatikprüfung gut', 0),
    ('Er liebt die Stil-, Text- und Grammatikprüfung.', 0),
    ('Stil-, Text- und Grammatikprüfung', 0),
    ('Stil-, Text- oder Grammatikprüfung', 0),
    ('Hierzu zählen Einkommen-, Körperschaft- sowie Gewerbesteuer.', 0),
    ('Miet- und Zinseinkünfte', 0),
    ('SPD- und CDU-Abgeordnete', 0),
    ('Haupt- und Nebensatz', 0),
    ('Vertuschungs- und Bespitzelungsmaßnahmen', 0),
    ('Netflix-Film', 0),
    ('Bund-Länder-Kommission', 0),
    ('Des World Wide Webs', 0),
    ('Der westperuanische Ferienort.', 0),
    ('„Pumpe“-Nachfolge', 0),
    ('"Pumpe"-Nachfolge', 0),
    ('ÖVP- und FPÖ-Chefverhandler', 0),
    ('α-Strahlung', 0),
    ('Primär-α-Mischkristallen', 0),
    ('supergut', 0),
    ('90°-Winkel', 0),
    ('Kosten- und Kreditmanagement', 0),
    ('Miet und Zinseinkünfte', 1),
    ('Stil- und Grammatik gut', 1),
    ('Flasch- und Grammatikprüfung gut', 1),
    ('Dual-Use-Güter', 0),
    ('Dual-Use- und Wirtschaftsgüter', 0),
    ('Test-Dual-Use', 0),
    ('Dual-Use', 1),
    ('Einpseudowortmitßfürlanguagetooltests-Auto', 0),
    ('-ablenkungsfrei', 0),
    ('-ablenkungsfreies', 0),
    ('-Ablenkungsfrei', 0),
    ('-Ablenkungsfreies', 0),
    ('- Ablenkungsfrei', 0),
    ('- Ablenkungsfreies', 0),
    ('abmantelung', 1),
    ('- abmantelung', 1),
    ('machtS', 1),
    ('All-Inclusive-Preis', 1),
    ('dRanging', 1),
    ('Das Draufklicken', 0),
    ('Des Draufklickens', 0),
    ('Des draufklickens', 1),
    ('Wichtelmännchen', 0),
    ('Wichtelmännchens', 0),
    ('wichtelmännchen', 1),
    ('wichtelmännchens', 1),
    ('vorgehängt', 0),
    ('vorgehängten', 0),
    ('Vorgehängt', 0),
    ('Vorgehängten', 0),
    ('Wichtelmännchen-vorgehängt', 0),
    ('Wichtelmännchen-Au-pair', 0),
    ('Fermi-Dirac-Statistik', 0),
    ('To-go-Becher', 0),
    ('Latte-macchiato-Glas', 0),
    ('Werkverträgler-Glas', 0),
    ('Werkverträglerglas', 0),
    ('Werkverträglerdu', 1),
    ('Helizitätso', 1),
    ('Feynmand', 1),
    ('Einpseudowortmitssfürlanguagetooltests-Auto', 1),
    ('\ufeffAblenkungsfreie Schreibumgebung', 0),
    ('Die blablaxx.mp3 und das sdifguds.avi bzw. die XYZXYZ.AVI', 0),
    ('Ausgestrahlt von 3sat', 0),
    ('Ein 32stel eines Loses', 0),
    ('Der Verlust eines 32stels eines Loses', 0),
    ('Ein 5tel eines Loses', 0),
    ('Der Verlust eines 5tels eines Loses', 0),
    ('ein 100stel-Millimeter', 0),
    ('ein 5tel-Gramm', 0),
    ('ein 100stel-Milimeter', 1),
    ('ein 5tel-Grömm', 1),
    ('ein 5tl-Gramm', 1),
    ('ein 100stl-Millimeter', 1),
    ('ein tl-Gramm', 1),
    ('ein stl-Millimeter', 1),
    ('ein tel-Gramm', 1),
    ('ein stel-Millimeter', 1),
    ('Bitte stel dich dazu', 1),
]

DASH_MATCH_COUNTS_CH = [
    ('Einpseudowortmitßfürlanguagetooltests-Auto', 1),
    ('Einpseudowortmitssfürlanguagetooltests-Auto', 0),
]

COMMON_GERMAN = [
    ('Der Waschmaschinentestversuch', 0),
    ('Der Waschmaschinentest-Versuch', 0),
    ('Der Arbeitnehmer', 0),
    ('Die Verhaltensänderung', 0),
    ('Er bzw. sie.', 0),
    ('Die Standarte', 0),
    ('Die Standarten', 0),
    ('Die Standartenführer', 0),
    ('Der Standard', 0),
    ('Der Standardversuch', 0),
    ('Der Waschmaschinentest-Dftgedgs', 1),
    ('Der Dftgedgs-Waschmaschinentest', 1),
    ('Der Waschmaschinentestdftgedgs', 1),
    ('Der Waschmaschinentestversuch orkt', 1),
    ('Der Arbeitsnehmer', 1),
    ('Die Verhaltenänderung', 1),
    ('Er bw. sie.', 1),
    ('Der asdegfue orkt', 2),
    ('rumfangreichen', 1),
    ('Der Standart', 1),
    ('Der Standartversuch', 1),
    ('Halterun', 1),
    ('Wandhalterun', 1),
    ('Halterung', 0),
    ('Wandhalterung', 0),
    ('Willkommenbei', 1),
    ('Fantasieschafft', 1),
    ('Babyquietschte', 1),
    ('nordwestfranzösisch', 0),
    ('nordestnisch', 0),
    ('westmünsterländische', 0),
    ('süddeutschland', 1),
    ('Desktopbetrieb', 0),
    ('Desktophintergrund', 0),
    ('Unibetrieb', 0),
    ('Integrallogarithmus', 0),
    ('Fledermaussonar', 0),
]

GENDER = [
    ('Jurist:innenausbildunk', 1),
    ('Jurrist:innenausbildung', 2),
    ('Jurist:innenausbildung', 0),
    ('Ein Satz. Die Jurist:innenausbildung und die Jurist*innenausbildung.', 0),
    ('Jurist*innenausbildunk', 1),
    ('Jurrist*innenausbildung', 2),
    ('Jurist*innenausbildung', 0),
    ('Jurist_innenausbildunk', 1),
    ('Jurrist_innenausbildung', 2),
    ('Jurist_innenausbildung', 0),
    ('Die Häuser der Juriest_innen sind grün.', 1),
    ('Die Häuser der Juriest*innen sind grün.', 1),
    ('Die Häuser der Juriest:innen sind grün.', 1),
    ('Die Häuser der Jurist_innen sind grün.', 0),
    ('Die Häuser der Jurist*innen sind grün.', 0),
    ('Die Häuser der Jurist:innen sind grün.', 0),
    ('Die Jurist_innenausbildung ist schwer.', 0),
    ('Die Jurist*innenausbildung ist schwer.', 0),
    ('Die Jurist:innenausbildung ist schwer.', 0),
    ('Die Jurist_innenausbieldung ist schwer.', 1),
    ('Die Jurist*innenausbieldung ist schwer.', 1),
    ('Die Jurist:innenausbieldung ist schwer.', 1),
    ('Die Juriest_innenausbildung ist schwer.', 2),
    ('Die Juriest*innenausbildung ist schwer.', 2),
    ('Die Juriest:innenausbildung ist schwer.', 2),
    ('Die Juriest_innenausbieldung ist schwer.', 2),
    ('Die Juriest*innenausbieldung ist schwer.', 2),
    ('Die Juriest:innenausbieldung ist schwer.', 2),
    ('Die SEO-Expert*innen', 0),
    ('Die SEO-Expxrt*innen', 1),
    ('Die SEO-Expert*annen', 2),
    ('Die Datei heißt Jurist_innen.txt.', 0),
    ('Die Datei heißt Jurist_innen.txt und ist leer.', 0),
    ('Die Datei heißt Juriest_innen.txt.', 0),
    ('Die Datei heißt Juriest_innen.txt und ist leer.', 0),
    ('Die Datei heißt Juriest_innenausbieldung.txt.', 0),
    ('Die Datei heißt Juriest_innenausbieldung.txt und ist leer.', 0),
    ('Die Datei heißt Jurist_innen.mfgjg.', 0),
    ('Die Datei heißt Jurist_innen.mfgjg und ist leer.', 0),
    ('Die Datei heißt Juriest_innen.mfgjg.', 0),
    ('Die Datei heißt Juriest_innen.mfgjg und ist leer.', 0),
    ('Die Datei heißt Juriest_innenausbieldung.mfgjg.', 0),
    ('Die Datei heißt Juriest_innenausbieldung.mfgjg und ist leer.', 0),
    ('Die Datei heißt counterelements4_0.xsd', 0),
    ('Die Datei heißt counter-elements4_0.xsd', 0),
    ('Die Datei heißt counterelements4_0.mfgjg und ist leer.', 0),
    ('Der @bla_xyz hat das gesagt', 0),
    ('richtig_stimmt', 0),
    ('flasch_nittrichtig', 2),
]

CORRECTIONS = [
    ('Hauk', ('Haus', 'Haut')),
    ('Eisnbahn', ('Eisbahn', 'Eisenbahn')),
    ('Rechtschreipreform', ('Rechtschreibreform',)),
    ('Theatrekasse', ('Theaterkasse',)),
    ('Traprennen', ('Trabrennen',)),
    ('Autuverkehr', ('Autoverkehr',)),
    ('Rechtschreibprüfun', ('Rechtschreibprüfung',)),
    ('Rechtschreib-Prüfun', ('Rechtschreib-Prüfung',)),
    ('bw.', ('bzw.',)),
    ('kan', ('kann', 'an')),
    ('kan.', ('kann.', 'an.')),
    ('Einzahlungschein', ('Einzahlungsschein',)),
    ('Arbeitamt', ('Arbeitet', 'Arbeitsamt')),
    ('Ordnungshütter', ('Ordnungshüter',)),
    ('inneremedizin', ('innere Medizin',)),
    ('innereMedizin', ('innere Medizin',)),
    ('InnereMedizin', ('Innere Medizin',)),
    ('gleichgroß', ('gleich groß',)),
    ('Arbeitamt', ('Arbeitsamt',)),
    ('Autoverkehrr', ('Autoverkehr',)),
    ('hasslich', ('hässlich', 'fasslich')),
    ('Struße', ('Strauße', 'Straße', 'Sträuße')),
    ('gewohnlich', ('gewöhnlich',)),
    ('gawöhnlich', ('gewöhnlich',)),
    ('gwöhnlich', ('gewöhnlich',)),
    ('geewöhnlich', ('gewöhnlich',)),
    ('gewönlich', ('gewöhnlich',)),
    ('außergewöhnkich', ('außergewöhnlich',)),
    ('agressiv', ('aggressiv',)),
    ('agressivster', ('aggressivster',)),
    ('agressiver', ('aggressiver',)),
    ('agressive', ('aggressive',)),
    ('Algorythmus', ('Algorithmus',)),
    ('Algorhythmus', ('Algorithmus',)),
    ('Amalgan', ('Amalgam',)),
    ('Amaturenbrett', ('Armaturenbrett',)),
    ('Aquise', ('Akquise',)),
    ('Artzt', ('Arzt',)),
    ('aufgrunddessen', ('aufgrund dessen',)),
    ('barfuss', ('barfuß',)),
    ('Batallion', ('Bataillon',)),
    ('Medallion', ('Medaillon',)),
    ('Scheisse', ('Scheiße',)),
    ('Handselvertreter', ('Handelsvertreter',)),
    ('aul', ('auf',)),
    ('Icj', ('Ich',)),
    ('Handelsvertretertrffen', ('Handelsvertretertreffen',)),
    ('Handelsvartretertreffen', ('Handelsvertretertreffen',)),
    ('Handelsvertretertriffen', ('Handelsvertretertreffen',)),
    ('Handelsvertrtertreffen', ('Handelsvertretertreffen',)),
    ('Handselvertretertreffen', ('Handelsvertretertreffen',)),
    ('Arbeidszimmer', ('Arbeitszimmer',)),
    ('Postleidzahl', ('Postleitzahl',)),
    ('vorallem', ('vor allem',)),
    ('wieviel', ('wie viel',)),
    ('wieviele', ('wie viele',)),
    ('wievielen', ('wie vielen',)),
    ('undzwar', ('und zwar',)),
    ('Ambei', ('Anbei',)),
    ('Kostn-', ('Kosten-',)),
    ('Adam-Ries-Nachfahrenbuch', ()),
]

ORDER = [
    ('heisst', ('heißt',)),
    ('heissen', ('heißen',)),
    ('müßte', ('musste', 'müsste')),
    ('schmohren', ('schmoren',)),
    ('Fänomen', ('Phänomen',)),
    ('homofob', ('homophob',)),
    ('ueber', ('über',)),
    ('Aerger', ('Ärger',)),
    ('Walt', ('Wald',)),
    ('Rythmus', ('Rhythmus',)),
    ('Rytmus', ('Rhythmus',)),
    ('is', ('IS', 'die', 'in', 'im', 'ist')),
    ('Fux', ('Fuchs',)),
    ('schänken', ('Schänken',)),
]

PROHIBITED = [
    ('Standart-Test', True),
    ('Blindarmentzündung', True),
    ('Weihnachtfreier', True),
    ('Standard-Test', False),
    ('Abstellgreis', True),
    ('Abstellgreise', True),
    ('Abstellgreisen', True),
    ('Landstreckenflüge', True),
    ('Landstreckenflügen', True),
    ('Abdominalgangion', True),
    ('Abdominalgangionen', True),
    ('Badegas', True),
    ('Aktienkur', True),
    ('Stellungsnahmen', True),
    ('Varietee', True),
    ('Varietees', True),
    ('Feuerwerksartigel', True),
    ('Feuerwerksartigeln', True),
    ('Feuerwerksartigels', True),
    ('To-go', True),
]

MISSPELLED = [
    ('dshfsdhsdf', True),
    ('Haussarbeit', True),
    ('Überschus', True),
    ('Überschussen', True),
    ('Hausarbeit', False),
    ('Überschuss', False),
    ('Überschüsse', False),
    ('Spielzugcomputer', True),
    ('Spielzugcomputern', True),
    ('Spielzug', False),
    ('Spielzugs', False),
    ('Studentenschafte', True),
    ('Steuereigenschafte', True),
    ('Studentenschaften', False),
    ('Steuereigenschaften', False),
    ('Eigenschaften', False),
    ('wirtschafte', False),
    ('Gebietskörperschaf', True),
    ('Gebietskörperschafs', True),
    ('Gebietskörperschafen', True),
    ('Freundschaf', True),
    ('Wollschaf', False),
    ('Wollschafs', False),
    ('Wollschafen', False),
]
