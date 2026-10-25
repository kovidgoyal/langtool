"""Ports of the German module's spelling tests other than
GermanSpellerRuleTest: org.languagetool.rules.spelling.hunspell.HunspellRuleTest
(HunspellRule with the German dictionaries, langtool.hunspell_rule),
SpellingCheckRuleTest, org.languagetool.rules.de.LineExpanderTest,
GermanToolsTest, AustrianGermanSpellerRuleTest, SwissGermanSpellerRuleTest,
MorfologikGermanyGermanSpellerRuleTest and LanguageSpecificSpellcheckerTest.

The spelling rule is not one of the rules of the language here (spell
checking rules are excluded from the port): tests that check texts with
JLanguageTool add the language's default spelling rule to it. Positions of
rule matches are offsets in Python strings (code points), not UTF-16
offsets as in Java (relevant for emojis). The @Ignore'd performance tests
of HunspellRuleTest, MorfologikGermanyGermanSpellerRuleTest.testFrequency/
testCommonMisspellings and the @Ignore'd SuggestionRegressionTest (a
regression check against src/test/resources/suggestions.txt that rewrites
the file) are not ported."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.hunspell_rule import HunspellRule, load_words
from langtool.lang.de.german_tools import is_vowel
from langtool.lang.de.line_expander import LineExpander
from langtool.lang.de.spelling import (AustrianGermanSpellerRule, SwissGermanSpellerRule,
                                       morfologik_germany_german_speller_rule)
from langtool.messages import messages_for
from langtool.rules.base import SuggestedReplacement
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


def _match(rule, lt, text):
    return rule.match(lt.get_analyzed_sentence(text))


def _count(rule, lt, text):
    return len(rule.match(lt.get_analyzed_sentence(text), False))


def _lt_with_speller(code):
    """JLanguageTool(language) with the language's spelling rule (which is
    one of the rules of the language in Java)"""
    language = get_language(code)
    lt = JLanguageTool(language)
    lt.add_rule(language.get_default_spelling_rule())
    return lt


# --- HunspellRuleTest ---

@pytest.fixture(scope='module')
def hunspell_rule_de():
    return HunspellRule(messages_for('de'), get_language('de-DE'), None)


@pytest.fixture(scope='module')
def lt_de():
    return JLanguageTool(get_language('de-DE'))


def test_high_confidence_suggestion(hunspell_rule_de):
    """HunspellRuleTest.testHighConfidenceSuggestion"""
    rule = hunspell_rule_de
    assert rule.is_first_item_high_confidence_suggestion('HAus', [SuggestedReplacement('HAus')])
    assert not rule.is_first_item_high_confidence_suggestion('EI', [SuggestedReplacement('Eis')])
    assert not rule.is_first_item_high_confidence_suggestion('CMs', [SuggestedReplacement('CMS')])
    assert not rule.is_first_item_high_confidence_suggestion('DMs', [SuggestedReplacement('DMS')])


def _common_german_asserts(rule, lt):
    """HunspellRuleTest.commonGermanAsserts"""
    assert _count(rule, lt, 'Der Waschmaschinentestversuch') == 0  # compound
    assert _count(rule, lt, 'Der Waschmaschinentest-Versuch') == 0  # compound
    assert _count(rule, lt, 'Der Arbeitnehmer') == 0
    assert _count(rule, lt, 'Die Verhaltensänderung') == 0
    assert _count(rule, lt, 'Der Waschmaschinentest-Dftgedgs') == 1
    assert _count(rule, lt, 'Der Dftgedgs-Waschmaschinentest') == 1
    assert _count(rule, lt, 'Der Waschmaschinentestdftgedgs') == 1
    assert _count(rule, lt, 'Der Waschmaschinentestversuch orkt') == 1
    assert _count(rule, lt, 'Der Arbeitsnehmer') == 1  # wrong interfix
    assert _count(rule, lt, 'Die Verhaltenänderung') == 1  # missing interfix
    assert _count(rule, lt, 'Der asdegfue orkt') == 2


def test_rule_with_german(hunspell_rule_de, lt_de):
    """HunspellRuleTest.testRuleWithGerman"""
    rule = hunspell_rule_de
    lt = lt_de
    _common_german_asserts(rule, lt)
    assert _count(rule, lt, 'Der äußere Übeltäter.') == 0  # umlauts
    assert _count(rule, lt, 'Der äussere Übeltäter.') == 1
    # ignore URLs:
    assert _count(rule, lt, 'Unter http://foo.org/bar steht was.') == 0
    assert _count(rule, lt, 'dasdassda http://foo.org/bar steht was.') == 1
    assert _count(rule, lt, 'Unter http://foo.org/bar steht dasdassda.') == 1
    # check the correct calculation of error position
    # (Java: emojis have string length 2 or 3; here they have length 1 or 2 (code points))
    m = _match(rule, lt, 'Hallo men Schatz!')[0]
    assert (m.from_pos, m.to_pos) == (6, 9)
    m = _match(rule, lt, 'Hallo 😂 men Schatz!')[0]
    assert (m.from_pos, m.to_pos) == (9 - 1, 12 - 1)
    m = _match(rule, lt, 'Hallo 😂😂 men Schatz!')[0]
    assert (m.from_pos, m.to_pos) == (11 - 2, 14 - 2)
    assert _count(rule, lt, 'Mir geht es 😂gut😂.') == 0
    assert _count(rule, lt, 'Mir geht es 😂gtu😂.') == 1
    m = _match(rule, lt, 'Hallo 🗺️ men Schatz!')[0]  # U+1F5FA U+FE0F
    assert (m.from_pos, m.to_pos) == (10 - 1, 13 - 1)
    assert _count(rule, lt, 'B(ℓ2)') == 0
    assert _count(rule, lt, '🏽') == 0
    assert _count(rule, lt, '🧡🚴🏽♂️ , 🎉💛✈️') == 0
    assert _count(rule, lt, 'компьютерная') == 0
    assert _count(rule, lt, '中文維基百科 中文维基百科') == 0
    assert _count(rule, lt, 'Blu-ray-Brenner') == 0
    assert _count(rule, lt, 'Stand-by-Betrieb') == 0

    matches = _match(rule, lt, '- Teex')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Tee'
    assert (matches[0].from_pos, matches[0].to_pos) == (2, 6)
    matches = _match(rule, lt, '-Teex')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['Tee', 'Telex', 'Tees', 'Teen', 'Teer', 'Tee-', 'Texte', 'TeX',
                                                 'Text']
    assert (matches[0].from_pos, matches[0].to_pos) == (1, 5)
    matches = _match(rule, lt, '- Kaffeex')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['Kaffee', 'Kaffees', 'Kaffee-']
    assert (matches[0].from_pos, matches[0].to_pos) == (2, 9)
    matches = _match(rule, lt, '-Kaffeex')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['Kaffee', 'Kaffees', 'Kaffee-']
    assert (matches[0].from_pos, matches[0].to_pos) == (1, 8)
    matches = _match(rule, lt, 'E -Commerce')
    assert len(matches) == 2
    assert matches[0].suggested_replacements == ['E-Commerce']
    assert (matches[0].from_pos, matches[0].to_pos) == (0, 11)
    assert matches[1].suggested_replacements == ['E-Commerce', 'Comer']
    assert (matches[1].from_pos, matches[1].to_pos) == (3, 11)


def test_multitokens_with_speller_rule():
    """HunspellRuleTest.testMultitokensWithSepllerRule"""
    lt = _lt_with_speller('de-DE')
    # a multiword as a suggestion for a single-token misspelled word
    matches = lt.check('BigBrother')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Big Brother'
    # multiwords at the sentence start (capitalized)
    assert len(lt.check('Mea culpa')) == 0


def _assert_result(rule, lt, inp, expected_result, from_pos, to_pos):
    matches = _match(rule, lt, inp)
    assert len(matches) == 2, (inp, matches)
    assert matches[0].suggested_replacements == [expected_result]
    assert matches[0].from_pos == from_pos
    assert matches[0].to_pos == to_pos


def test_rule_with_wrong_split(hunspell_rule_de, lt_de):
    """HunspellRuleTest.testRuleWithWrongSplit"""
    rule = hunspell_rule_de
    lt = lt_de
    _assert_result(rule, lt, 'Vielen Dan kfür die Blumen', 'Dank für', 7, 15)
    _assert_result(rule, lt, 'Vielen Dankf ür die Blumen', 'Dank für', 7, 15)
    _assert_result(rule, lt, 'Viele nDank für die Blumen', 'Vielen Dank', 0, 11)
    _assert_result(rule, lt, 'VielenD ank für die Blumen', 'Vielen Dank', 0, 11)
    _assert_result(rule, lt, 'Vielen Dank für di eBlumen', 'die Blumen', 16, 26)
    _assert_result(rule, lt, 'Vielen Dank für di eBlumen.', 'die Blumen', 16, 26)
    _assert_result(rule, lt, 'Vielen Dank für dieB lumen', 'die Blumen', 16, 26)
    _assert_result(rule, lt, 'Vielen Dank für dieB lumen.', 'die Blumen', 16, 26)
    _assert_result(rule, lt, 'Das ist g anz falsch', 'ganz', 8, 13)

    matches = _match(rule, lt, 'Vielen Dak für dieB lumen')
    assert len(matches) == 3
    assert matches[0].suggested_replacements[0] == 'DAK'  # not really a good first suggestion...
    assert matches[1].suggested_replacements == ['die Blumen']
    assert (matches[1].from_pos, matches[1].to_pos) == (15, 25)
    assert matches[2].suggested_replacements[0] == 'Lumen'

    matches2 = _match(rule, lt, 'Und gan viele nDank')
    assert len(matches2) == 3
    assert matches2[0].suggested_replacements[0] == 'gab'  # not really a good first suggestion...
    assert matches2[1].suggested_replacements == ['vielen Dank']
    assert (matches2[1].from_pos, matches2[1].to_pos) == (8, 19)
    assert matches2[2].suggested_replacements[0] == 'Dank'

    matches3 = _match(rule, lt, 'Vielen Dank für dieB lumen und auuch falsch')
    assert len(matches3) == 3
    assert matches3[0].suggested_replacements[0] == 'die Blumen'
    assert matches3[1].suggested_replacements[0] == 'Lumen'
    assert matches3[2].suggested_replacements[0] == 'auch'


def test_hunspell_rule_with_austrian_german(lt_de):
    """HunspellRuleTest.testRuleWithAustrianGerman"""
    rule = HunspellRule(messages_for('de'), get_language('de-AT'), None)
    _common_german_asserts(rule, lt_de)
    assert _count(rule, lt_de, 'Der äußere Übeltäter.') == 0  # umlauts
    assert _count(rule, lt_de, 'Der äussere Übeltäter.') == 1


def test_hunspell_rule_with_swiss_german():
    """HunspellRuleTest.testRuleWithSwissGerman"""
    rule = HunspellRule(messages_for('de'), get_language('de-CH'), None)
    lt = JLanguageTool(get_language('de-CH'))
    _common_german_asserts(rule, lt)
    assert _count(rule, lt, 'Der äußere Übeltäter.') == 1  # ß not allowed in Swiss
    assert _count(rule, lt, 'Der äussere Übeltäter.') == 0  # ss is used instead of ß
    # suggestions with ss, not ß, in Swiss German (lt.check with the language's spelling rule)
    lt2 = _lt_with_speller('de-CH')
    matches = lt2.check('Mit freundlichen Gruessen')
    assert matches[0].suggested_replacements[0] == 'Grüssen'
    matches = lt2.check('schließen')
    assert matches[0].suggested_replacements[0] == 'schliessen'


# --- SpellingCheckRuleTest ---

def test_ignore_suggestions_with_hunspell():
    """SpellingCheckRuleTest.testIgnoreSuggestionsWithHunspell"""
    lt = _lt_with_speller('de-DE')
    # no error, as this word is in ignore.txt
    assert len(lt.check('Das ist ein einPseudoWortFürLanguageToolTests')) == 0
    matches = lt.check('Das ist ein Tibbfehla')
    assert len(matches) == 1
    assert matches[0].rule.get_id() == 'GERMAN_SPELLER_RULE'


def test_ignore_phrases():
    """SpellingCheckRuleTest.testIgnorePhrases"""
    from langtool.lang.de.spelling import GermanSpellerRule
    language = get_language('de-DE')
    lt = JLanguageTool(language)
    speller = GermanSpellerRule(messages_for('de'), language)
    lt.add_rule(speller)
    assert len(lt.check('Ein Test mit Auriensis Fantasiewortus')) == 2
    for rule in lt.get_all_active_rules():
        if rule is speller:
            rule.accept_phrases(['Auriensis Fantasiewortus', 'fudeldu laberwort'])
        else:
            lt.disable_rule(rule.get_id())
    assert len(lt.check('Ein Test mit Auriensis Fantasiewortus')) == 0
    assert len(lt.check('Ein Test mit Auriensis und Fantasiewortus')) == 2  # the words on their own are not ignored
    assert len(lt.check('fudeldu laberwort')) == 0
    assert len(lt.check('Fudeldu laberwort')) == 0  # Uppercase at sentence start is okay
    assert len(lt.check('Fudeldu Laberwort')) == 1  # Different case somewhere other than at sentence start is not okay


def test_multitoken_spelling():
    """SpellingCheckRuleTest.testMultitokenSpelling"""
    lt = _lt_with_speller('de-DE')
    assert len(lt.check('Bresegard bei Eldena')) == 0
    assert len(lt.check('Feichten an der Alz')) == 0
    assert len(lt.check('Groß Oesingen')) == 0
    assert len(lt.check('Eching am Ammersee')) == 0
    assert len(lt.check('Gross Oesingen')) == 2
    assert len(lt.check('Groß Oessingen')) == 1
    assert len(lt.check('Eching am Ammerse')) == 2


def test_prohibited_word_followed_by_dot():
    """SpellingCheckRuleTest.testProhibitedWordFollowedByDot"""
    lt = _lt_with_speller('de-DE')
    assert len(lt.check('Bestanteil.')) == 1


# --- LineExpanderTest ---

def _java_list_str(lst):
    return '[' + ', '.join(lst) + ']'


def _parse_string_to_set(bracket_string):
    content = bracket_string[1:-1]
    if not content.strip():
        return set()
    return {e.strip() for e in content.split(',')}


def _assert_sets_equal(expected, actual):
    assert _parse_string_to_set(actual) == _parse_string_to_set(expected)


def test_line_expansion():
    """LineExpanderTest.testExpansion"""
    exp = LineExpander()

    def expand(line):
        return _java_list_str(exp.expand_line(line))

    _assert_sets_equal(expand(''), '[]')
    _assert_sets_equal(expand('Das'), '[Das]')
    _assert_sets_equal(expand('Tisch/E'), '[Tisch, Tische]')
    _assert_sets_equal(expand('Tische/N'), '[Tische, Tischen]')
    _assert_sets_equal(expand('Auto/S'), '[Auto, Autos]')
    _assert_sets_equal(expand('klein/A'), '[klein, kleine, kleiner, kleines, kleinen, kleinem]')
    _assert_sets_equal(expand('x/NSE'), '[x, xn, xs, xe]')
    _assert_sets_equal(expand('x/NA'), '[x, xn, xe, xer, xes, xen, xem]')
    _assert_sets_equal(expand('viertjüngste/A'),
                       '[viertjüngste, viertjüngster, viertjüngstes, viertjüngsten, viertjüngstem]')
    _assert_sets_equal(expand('Das  #foo'), '[Das]')
    _assert_sets_equal(expand('Tisch/E  #bla #foo'), '[Tisch, Tische]')
    _assert_sets_equal(expand('Goethestraße/T'), '[Goethestraße, Goethestr.]')
    _assert_sets_equal(expand('Goethestrasse/T'), '[Goethestrasse, Goethestr.]')
    _assert_sets_equal(expand('Zwingenberger Straße/T'), '[Zwingenberger Straße, Zwingenberger Str.]')
    _assert_sets_equal(expand('Zwingenberger Strasse/T'), '[Zwingenberger Strasse, Zwingenberger Str.]')
    _assert_sets_equal(expand('Escape\\/N'), '[Escape/N]')
    _assert_sets_equal(expand('rüber_machen  #bla #foo'),
                       '[rübermach, rübergemacht, rübermachest, rübermachst, rübermache, '
                       'rübermachen, rübermachet, rübermachte, rübermachend, rübermachten, rübermacht, rübermachtest, '
                       'rübermachtet, rüberzumachen, Rübermachens]')
    _assert_sets_equal(expand('rüber_verschicken'),
                       '[rüberverschickend, rüberverschickst, rüberverschick, rüberverschickest, '
                       'rüberverschicktest, rüberverschicke, rüberverschicket, rüberverschickte, rüberverschicktet, '
                       'rüberverschickten, rüberverschicken, rüberverschickt, rüberzuverschicken, Rüberverschickens]')
    _assert_sets_equal(expand('escape\\_machen'), '[escape_machen]')
    with pytest.raises(Exception):
        expand('rüber/invalidword')


# --- GermanToolsTest ---

def test_is_vowel():
    """GermanToolsTest.testIsVowel"""
    assert is_vowel('a')
    assert is_vowel('Y')
    assert is_vowel('A')
    assert is_vowel('ö')
    assert not is_vowel('b')


# --- AustrianGermanSpellerRuleTest, SwissGermanSpellerRuleTest ---

def test_austrian_get_suggestions_from_spelling_txt():
    """AustrianGermanSpellerRuleTest.testGetSuggestionsFromSpellingTxt"""
    language = get_language('de-AT')
    rule = AustrianGermanSpellerRule(messages_for('en'), language, None, None)
    lt = JLanguageTool(language)
    assert len(_match(rule, lt, 'Shopbewertung')) == 0  # from spelling.txt
    assert len(_match(rule, lt, 'Wahlzuckerl')) == 0
    assert len(_match(rule, lt, 'Wahlzuckerls')) == 0
    assert len(_match(rule, lt, 'aifhdlidflifs')) == 1


def test_swiss_get_suggestions_from_spelling_txt():
    """SwissGermanSpellerRuleTest.testGetSuggestionsFromSpellingTxt"""
    language = get_language('de-CH')
    rule = SwissGermanSpellerRule(messages_for('en'), language)
    lt = JLanguageTool(language)
    assert len(_match(rule, lt, 'Shopbewertung')) == 0  # from spelling.txt
    assert len(_match(rule, lt, 'Abwart')) == 0
    assert len(_match(rule, lt, 'Abwarts')) == 0
    assert len(_match(rule, lt, 'aifhdlidflifs')) == 1
    matches = _match(rule, lt, 'Trottinettens')  # from spelling-de-CH.txt
    assert matches[0].suggested_replacements[0] == 'Trottinetten'


# --- MorfologikGermanyGermanSpellerRuleTest ---

def test_morfologik_speller():
    """MorfologikGermanyGermanSpellerRuleTest.testMorfologikSpeller (the
    rule matches of the morfologik speller rule are not ported: whether a
    sentence has a spelling error and the suggestions for a word are
    checked)"""
    rule = morfologik_germany_german_speller_rule(get_language('de-DE'))
    lt = JLanguageTool(get_language('de'))

    def has_match(text):
        return rule.sentence_has_match(lt.get_analyzed_sentence(text))

    assert not has_match('Hier stimmt jedes Wort!')
    assert has_match('Hir nicht so ganz.')
    assert not has_match('Überall äußerst böse Umlaute!')
    assert has_match('Üperall äußerst böse Umlaute!')
    assert has_match('daß')
    suggestions = rule.get_spelling_suggestions('daß')
    assert suggestions[0] == 'das'  # "dass" would actually be better...
    assert suggestions[1] == 'dass'
    assert not has_match('B(ℓ2)')
    assert not has_match('🏽')
    assert not has_match('🧡🚴🏽♂️ , 🎉💛✈️')
    assert not has_match('компьютерная')
    assert not has_match('中文維基百科 中文维基百科')


# --- LanguageSpecificSpellcheckerTest (SpellcheckerTest.runLanguageSpecificTest) ---

def test_language_specific_spellchecker():
    """LanguageSpecificSpellcheckerTest.testRules: no word of prohibit.txt
    may be in spelling.txt (for the German languages)"""
    total_prohibited = 0
    for code in ('de', 'de-DE', 'de-AT', 'de-CH'):
        lang = get_language(code)
        prohibited_words = load_words(lang, lang.short_code + '/hunspell/prohibit.txt')
        total_prohibited += len(prohibited_words)
        spelling_words = set(load_words(lang, lang.short_code + '/hunspell/spelling.txt'))
        intersection = {w for w in prohibited_words if w in spelling_words}
        assert not intersection, \
            "Word(s) appear in both spelling.txt and prohibit.txt - this doesn't make sense: %s" % intersection
    assert total_prohibited > 0


# --- German.createDefaultSpellingRule / getMultitokenSpeller (registration) ---

def test_default_spelling_rules():
    """German.createDefaultSpellingRule and its overrides in GermanyGerman,
    AustrianGerman and SwissGerman; German.getMultitokenSpeller"""
    expected = {'de': 'GERMAN_SPELLER_RULE', 'de-DE': 'GERMAN_SPELLER_RULE',
                'de-AT': 'AUSTRIAN_GERMAN_SPELLER_RULE', 'de-CH': 'SWISS_GERMAN_SPELLER_RULE'}
    for code, rule_id in expected.items():
        rule = get_language(code).get_default_spelling_rule()
        assert rule.get_id() == rule_id
        assert rule is get_language(code).get_default_spelling_rule()
    # "de" (German without country) has no dictionary (de_LU), like in Java: only prohibited words are misspelled
    assert not get_language('de').get_default_spelling_rule().is_misspelled('Hausx')
    assert get_language('de-DE').get_default_spelling_rule().is_misspelled('Hausx')
    assert get_language('de-CH').get_default_spelling_rule().is_misspelled('Straße')
    assert not get_language('de-AT').get_default_spelling_rule().is_misspelled('Straße')
    from langtool.lang.de.multitoken import GermanMultitokenSpeller
    speller = get_language('de-AT').get_multitoken_speller()
    assert isinstance(speller, GermanMultitokenSpeller)
    assert speller is get_language('de-DE').get_multitoken_speller()
