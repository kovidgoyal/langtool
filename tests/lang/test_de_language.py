"""Port of org.languagetool.rules.de.GermanTest (LanguageSpecificTest),
org.languagetool.JLanguageToolTest (language-de),
GermanConfusionProbabilityRuleTest and UpperCaseNgramRuleTest (both
skipped: language model), plus checks of the German language definition
against org.languagetool.language.German, GermanyGerman, AustrianGerman,
SwissGerman and NonSwissGerman. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, unsupported_components
from langtool.lang.de.language import filter_rule_matches
from langtool.patterns.rules import AbstractPatternRule, RegexPatternRule
from langtool.rules.base import Rule, RuleMatch, SuggestedReplacement
from langtool.tool import JLanguageTool, LEVEL_PICKY

DEMO_TEXT = ('Schreiben Sie in diesem Textfeld oder fügen Sie einen Text ein. Ihr Text wird kontinuierlich über prüft '
             'und Fehler werden farbig unterstrichen. Rechtshcreibfehler werden rot markirt, Grammatikfehler werden '
             'gelb hervor gehoben und Stilfehler werden, anders wie die anderen Fehler, blau unterstrichen. wussten '
             'Sie dass Synonyme per Doppelklick auf ein Wort aufgerufen werden können? Nutzen sie LanguageTool in '
             'allen Lebenslagen, etwa wenn Sie am Donnerstag, dem 13. Mai 2022, einen Basketballkorb in 10 Fuß Höhe '
             'montieren möchten.')


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


class FakeRule(Rule):
    """org.languagetool.FakeRule"""

    def __init__(self, id='FAKE-RULE'):
        super().__init__()
        self._id = id

    def get_id(self):
        return self._id

    def get_description(self):
        return 'Fake rule'


# --- GermanTest ---

def test_demo_text():
    """GermanTest.testLanguage (testDemoText). Java expects two more matches of
    GERMAN_SPELLER_RULE (for "Rechtshcreibfehler" and "markirt", after
    ZUSAMMENSCHREIBUNG_UEBER), the spell checker, which is not ported"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    matches = JLanguageTool(get_language('de-DE')).check(DEMO_TEXT)
    assert [m.rule.get_id() for m in matches] == [
        'ZUSAMMENSCHREIBUNG_UEBER', 'ZUSAMMENSCHREIBUNG_HER', 'KOMP_WIE', 'UPPERCASE_SENTENCE_START',
        'KOMMA_ZWISCHEN_HAUPT_UND_NEBENSATZ_2', 'AUFFORDERUNG_SIE', 'DE_DATE_WEEKDAY', 'EINHEITEN_METRISCH']


def test_message_coherency():
    """GermanTest.testMessageCoherency (Java only prints warnings for
    words to avoid in the messages of the pattern rules): all messages can
    be read"""
    lt = JLanguageTool(get_language('de-DE'))
    messages = [r.message for r in lt.get_all_rules() if isinstance(r, AbstractPatternRule)]
    assert messages and all(isinstance(m, str) for m in messages)


def test_gender_chars_against_all_rules():
    """GermanTest.testGenderCharsAgainstAllRules. The last check of the Java
    test ("Das ist flasch_nittrichtig." has 2 matches) counts matches of the
    spell checker, which is not ported (there are no matches without it)"""
    lt = JLanguageTool(get_language('de-DE'))
    assert len(lt.check('Die Jurist_innenausbildung ist schwer.')) == 0
    assert len(lt.check('Die Jurist*innenausbildung ist schwer.')) == 0
    assert len(lt.check('Die Jurist:innenausbildung ist schwer.')) == 0
    assert len(lt.check('Die Datei heißt Juriest_innenausbieldung.mfgjg und ist leer.')) == 0
    assert len(lt.check('Alles richtig_stimmt.')) == 0
    assert len(lt.check('Das ist flasch_nittrichtig.')) == 0


def test_merging_of_grammar_corrections():
    """GermanTest.testMergingOfGrammarCorrections"""
    lang = get_language('de')
    lt = JLanguageTool(lang)
    analyzed_sentence = lt.get_analyzed_sentence('Diese Mail ist z Hd Frau Müllers.')
    # Mocking two adjacent grammar issues
    rule_match1 = RuleMatch(FakeRule('AI_DE_GGEC_TEST'), analyzed_sentence, 16, 24, 'Adjektivfehler')
    rule_match1.set_suggested_replacement('absolute')
    rule_match2 = RuleMatch(FakeRule('AI_DE_GGEC_TEST2'), analyzed_sentence, 25, 28, 'Adjektivfehler')
    rule_match2.set_suggested_replacement('sich')
    # Process the rule matches
    processed = lang.filter_rule_matches([rule_match1, rule_match2], None, None)
    assert processed[0].suggested_replacements[0] == 'absolute sich'
    assert processed[0].get_specific_rule_id() == 'AI_DE_MERGED_MATCH'


def _lacks_switzerland_spelling(pattern):
    return pattern is not None and 'ß' in pattern and '(ß|ss)' not in pattern and '(ss|ß)' not in pattern \
        and not _contains_switzerland_spelling(pattern) and not _all_in_brackets('ß', pattern)


def _contains_switzerland_spelling(pattern):
    import re
    for part in re.split('[|()]', pattern):
        if 'ß' in part:
            if _clean_syntax(part).replace('ß', 'ss') not in _clean_syntax(pattern):
                return False
    return True


def _clean_syntax(part):
    return part.replace('(', '').replace(')', '')


def _all_in_brackets(search_char, pattern):
    in_brackets = False
    for c in pattern:
        if c == '[':
            in_brackets = True
        elif c == ']':
            in_brackets = False
        elif c == search_char and not in_brackets:
            return False
    return True


def test_swiss_spelling_variants():
    """GermanTest.testSwissSpellingVariants (Java only prints warnings for
    tokens with 'ß' but not 'ss'): the patterns of all rules can be
    checked"""
    lang = get_language('de-DE')
    ignore_ids = ('SCHARFES_SZ', 'APOSTROPH_S', 'EMPFOHLENE_ZUSAMMENSCHREIBUNG')
    warnings = []
    for rule in lang.get_pattern_rules():
        if rule.get_id() in ignore_ids:
            continue
        for anti_pattern in rule.anti_patterns:
            for pt in anti_pattern.pattern_tokens:
                if _lacks_switzerland_spelling(pt.get_string()):
                    warnings.append(rule.get_full_id())
        if isinstance(rule, RegexPatternRule):
            if _lacks_switzerland_spelling(rule.pattern.pattern):
                warnings.append(rule.get_full_id())
        else:
            for pt in rule.pattern_tokens or ():
                if _lacks_switzerland_spelling(pt.get_string()):
                    warnings.append(rule.get_full_id())
    assert isinstance(warnings, list)


# --- JLanguageToolTest ---

def test_german():
    """JLanguageToolTest.testGerman"""
    lt = JLanguageTool(get_language('de'))
    assert len(lt.check('Ein Test, der keine Fehler geben sollte.')) == 0
    assert len(lt.check('Ein Test Test, der Fehler geben sollte.')) == 1
    lt.set_list_unknown_words(True)
    # no spelling mistakes as we have not created a variant:
    assert len(lt.check('I can give you more a detailed description')) == 0
    # test unknown words listing
    assert lt.get_unknown_words() == ['I', 'can', 'description', 'detailed', 'give', 'more', 'you']


def test_germany_german():
    """JLanguageToolTest.testGermanyGerman. Java expects 6 matches for the
    English sentence, all of the spell checker, which is not ported"""
    lt = JLanguageTool(get_language('de-DE'))
    assert len(lt.check('Ein Test, der keine Fehler geben sollte.')) == 0
    assert len(lt.check('Ein Test Test, der Fehler geben sollte.')) == 1
    lt.set_list_unknown_words(True)
    # German rule has no effect with English error (the 6 matches in Java are spelling mistakes):
    assert len(lt.check('I can give you more a detailed description')) == 0
    # test unknown words listing
    assert lt.get_unknown_words() == ['I', 'can', 'description', 'detailed', 'give', 'more', 'you']


def test_positions_with_german():
    """JLanguageToolTest.testPositionsWithGerman"""
    lt = JLanguageTool(get_language('de-DE'))
    matches = lt.check('Stundenkilometer')
    assert len(matches) == 1
    assert matches[0].line == 0
    assert matches[0].column == 1


def test_clean_overlapping_with_german():
    """JLanguageToolTest.testCleanOverlappingWithGerman. Java expects 3
    matches; one of them is of the spell checker ("TRGS"), which is not
    ported"""
    lt = JLanguageTool(get_language('de-DE'))
    # Juxtaposed errors in "TRGS - Technische" should not be removed.
    matches = lt.check('TRGS - Technische Regeln für Gefahrstoffe', level=LEVEL_PICKY)
    assert len(matches) == 2


def test_advanced_typography():
    """JLanguageToolTest.testAdvancedTypography"""
    lang = get_language('de-DE')
    assert lang.to_advanced_typography('Das ist...') == 'Das ist…'
    assert lang.to_advanced_typography('Meinten Sie "entschieden" oder "entscheidend"?') == \
        'Meinten Sie „entschieden“ oder „entscheidend“?'
    assert lang.to_advanced_typography("Meinten Sie 'entschieden' oder 'entscheidend'?") == \
        'Meinten Sie ‚entschieden‘ oder ‚entscheidend‘?'
    assert lang.to_advanced_typography('z. B.') == 'z. B.'
    assert lang.to_advanced_typography('z.B.') == 'z. B.'
    assert lang.to_advanced_typography('i.d.R.') == 'i. d. R.'
    assert lang.to_advanced_typography('i. d. R.') == 'i. d. R.'
    assert lang.to_advanced_typography("Zeichen ohne sein Gegenstück: '\"' scheint zu fehlen") == \
        'Zeichen ohne sein Gegenstück: ‚"‘ scheint zu fehlen'


def test_german_variants():
    """JLanguageToolTest.testGermanVariants"""
    sentence = 'Ein Test, der keine Fehler geben sollte.'
    sentence2 = 'Ein Test Test, der Fehler geben sollte.'
    for code in ('de-DE', 'de-CH', 'de-AT'):
        lt = JLanguageTool(get_language(code))
        assert len(lt.check(sentence)) == 0
        assert len(lt.check(sentence2)) == 1


def test_multitoken_speller():
    """JLanguageToolTest.testMultitokenSpeller"""
    speller = get_language('de-DE').get_multitoken_speller()

    def sugg(s):
        return speller.get_suggestions(s)
    assert sugg('KarlHeinz Rummenigge') == ['Karl-Heinz Rummenigge']
    assert sugg('Leonardo Di-Caprio') == ['Leonardo DiCaprio']
    assert sugg('Marshall Mc-Luhan') == ['Marshall McLuhan']
    assert sugg('Jochen Striebeck') == []
    assert sugg('Ricardo Simoneti') == ['Ricardo Simonetti']
    assert sugg('Clint Eastwoods') == []
    assert sugg('otto dvd') == []
    assert sugg('one place') == []
    assert sugg('Yuval Noha Harari') == ['Yuval Noah Harari']
    assert sugg('Homos Sapiens') == ['Homo sapiens']
    assert sugg('à la carte') == []
    assert sugg('a la carte') == ['à la carte']
    assert sugg('dierser Straße') == []
    assert sugg('Tum Universität') == []
    assert sugg('fuer Trump') == []


# --- language model rules ---

@pytest.mark.skip(reason='language model rules are not ported: GermanConfusionProbabilityRuleTest tests the '
                         'GermanConfusionProbabilityRule (ConfusionProbabilityRule)')
def test_german_confusion_probability_rule():
    """GermanConfusionProbabilityRuleTest.testConstructor"""


@pytest.mark.skip(reason='language model rules are not ported: UpperCaseNgramRuleTest tests the '
                         'UpperCaseNgramRule, which needs a LanguageModel')
def test_upper_case_ngram_rule():
    """UpperCaseNgramRuleTest.testRule"""


# --- the language definitions ---

def test_definitions():
    """German, GermanyGerman, AustrianGerman, SwissGerman: names, countries,
    quotes, typography, sentence tokenizer, rule files, variant rules"""
    de = get_language('de')
    assert de.name == 'German' and de.countries == ['LU', 'LI', 'BE']
    assert de.default_variant.code == 'de-DE'
    assert not de.is_variant()
    assert isinstance(de.sentence_tokenizer, SRXSentenceTokenizer)
    for code, name, countries in (('de-DE', 'German (Germany)', ['DE']), ('de-AT', 'German (Austria)', ['AT']),
                                  ('de-CH', 'German (Swiss)', ['CH'])):
        lang = get_language(code)
        assert lang.name == name and lang.countries == countries
        assert lang.is_variant()
        assert lang.is_advanced_typography_enabled()
        files = [f.replace('\\', '/').split('/rules/de/')[1] for f in lang.get_rule_file_names()]
        expected = ['grammar.xml', 'style.xml']
        if code == 'de-CH':
            expected.append('de-CH/grammar.xml')
        else:
            expected.append('de-DE-AT/grammar.xml')
        assert files == expected
        rule_ids = {r.get_id() for r in JLanguageTool(lang).get_all_rules()}
        if code == 'de-CH':
            assert 'DE_CH_COMPOUNDS' in rule_ids  # SwissCompoundRule
        assert 'DE_AGREEMENT' in rule_ids
    assert [get_language('de-DE')._quote(i) for i in range(4)] == ['„', '“', '‚', '‘']
    assert [get_language('de-CH')._quote(i) for i in range(4)] == ['«', '»', '‚', '‘']


def test_all_components_supported():
    """All the components referenced by the German definitions are ported"""
    for code in ('de', 'de-DE', 'de-AT', 'de-CH'):
        lang = get_language(code)
        lt = JLanguageTool(lang)
        lt.check('Ein Test, der keine Fehler geben sollte.')
        assert lang.tagger and lang.synthesizer and lang.disambiguator and lang.post_disambiguation_chunker
        assert not unsupported_components(lang)


def test_swiss_filter_rule_matches():
    """SwissGerman.filterRuleMatches: ß is replaced by ss in the
    suggestions"""
    lang = get_language('de-CH')
    sentence = JLanguageTool(lang).get_analyzed_sentence('Das ist gross.')
    rm = RuleMatch(FakeRule('SOME_RULE'), sentence, 8, 13, 'msg')
    rm.set_suggested_replacement_objects([SuggestedReplacement('groß')])
    assert filter_rule_matches(lang, [rm], None, None)[0].suggested_replacements == ['gross']
    # an AI_DE_GGEC rule that only suggests ß for ss is removed
    rm2 = RuleMatch(FakeRule('AI_DE_GGEC_REPLACEMENT_ORTHOGRAPHY_SPELL'), sentence, 8, 13, 'msg')
    rm2.set_suggested_replacement('groß')
    assert filter_rule_matches(lang, [rm2], None, None) == []
    # not for de-DE
    assert filter_rule_matches(get_language('de-DE'), [rm], None, None)[0].suggested_replacements == ['groß']
