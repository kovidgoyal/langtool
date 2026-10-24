"""Port of org.languagetool.rules.nl.DutchTest (LanguageSpecificTest),
org.languagetool.JLanguageToolTest (language-nl),
org.languagetool.rules.nl.UppercaseSentenceStartRuleTest,
GenericUnpairedBracketsRuleTest, LanguageSpecificSpellcheckerTest and
DutchRemoteRuleFilterTest (both skipped), plus checks of the Dutch language
definition against org.languagetool.language.Dutch and BelgianDutch. The
language independent parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.nl.rules import (CheckCaseRule, CompoundRule, DutchWrongWordInContextRule, PreferredWordRule,
                                    SimpleReplaceRule, SpaceInCompoundRule, WordCoherencyRule)
from langtool.lang.nl.tagging import DutchTagger
from langtool.lang.nl.tokenizers import DutchWordTokenizer
from langtool.messages import messages_for
from langtool.rules.core import GenericUnpairedBracketsRule
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('nl')


# --- DutchTest ---

def test_demo_text():
    """DutchTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Schrijf of plak hier je tekst om deze al typende te check. Vergissingen worden gemarkeerd met '
         'verschillende kleuren: spelvouten laten we rood ondersteept zien. Grammaticafouten daarentegen markeren we '
         'met geel. LanguageTool laat stijlwesties zo optimaal mogelijk zien in het blauw. wist u al dat u '
         'synoniemen kunt oproepen met een dubbelklik op een woord ? LanguageTool is een absolute musthave voor '
         'het schrijven van perfecte tekst. Bij voorbeeld om een collega te vertellen wat er vrijdag 3 Maart 2007 '
         'gebeurd is.')
    matches = JLanguageTool(get_language('nl')).check(s)
    # Java expects three more matches of MORFOLOGIK_RULE_NL_NL (for "spelvouten", "ondersteept",
    # "stijlwesties") after NL_SIMPLE_REPLACE_TE_CHECK, the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'NL_SIMPLE_REPLACE_TE_CHECK', 'ZO_OPTIMAAL_MOGELIJK', 'UPPERCASE_SENTENCE_START', 'SPATIE_LEESTEKEN',
        'NL_SIMPLE_REPLACE_MUSTHAVE', 'BIJ_VOORBEELD', 'NL_DATE_WEEKDAY', 'WEEKDAGEN_MAANDEN']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the '
                         'spelling.txt/ignore.txt word lists with MorfologikDutchSpellerRule')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.nl.LanguageSpecificSpellcheckerTest"""


@pytest.mark.skip(reason='remote rules are not ported: DutchRemoteRuleFilterTest tests the filters of '
                         'remote-rule-filters.xml for remote (AI) rules')
def test_remote_rule_filters():
    """Port of org.languagetool.rules.nl.DutchRemoteRuleFilterTest"""


def test_definition():
    lang = get_language('nl')
    assert lang.code == 'nl'
    assert lang.name == 'Dutch'
    assert lang.countries == ['NL', 'BE']
    assert not lang.is_variant()
    be = get_language('nl-BE')
    assert be.name == 'Dutch (Belgium)' and be.countries == ['BE'] and be.is_variant()
    assert be.default_variant is lang
    assert isinstance(lang.tagger, DutchTagger)
    assert type(lang.word_tokenizer) is DutchWordTokenizer
    # DutchHybridDisambiguator: the chunkers for spelling_global.txt and nl/multiwords.txt, then the
    # XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, MultiWordChunker, XmlRuleDisambiguator]
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'nl', 'grammar.xml'], ['rules', 'nl', 'style.xml'], ['nl', 'nl-NL', 'grammar.xml']]
    # BelgianDutch removes nl-NL/grammar.xml
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in be.get_rule_file_names()]
    assert files == [['rules', 'nl', 'grammar.xml'], ['rules', 'nl', 'style.xml'], ['nl', 'nl-BE', 'grammar.xml'],
                     ['nl', 'nl-BE', 'style.xml']]


def test_typography():
    """Dutch.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    for code in ('nl', 'nl-BE'):
        lang = get_language(code)
        assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
                lang.get_closing_single_quote()) == ('“', '”', '‘', '’')
        assert lang.is_advanced_typography_enabled()


def test_priorities():
    """Dutch.getPriorityForId"""
    lang = get_language('nl')
    p = lang.get_priority_for_id
    assert p('TOO_LONG_SENTENCE') == -1
    assert p('SINT_X') == 3
    assert p('ET_AL') == 1
    assert p('VERSCHILLENDE_AANHALINGSTEKENS') == 1
    assert p('KOMMA_KOMMA') == -1
    assert p('HET_FIETS') == -2
    assert p('JOU_JOUW') == -3
    assert p('DOUBLE_PUNCTUATION') == -3
    assert p('EINDE_ZIN_ONVERWACHT') == -5
    assert p('TOO_LONG_PARAGRAPH') == -15
    assert p('DE_ONVERWACHT') == -20
    assert p('NL_SIMPLE_REPLACE_KLAA') == 1
    assert p('NL_SPACE_IN_COMPOUND_X') == 1
    assert p('AI_NL_HYDRA_LEO_MISSING_COMMA') == -51
    assert p('AI_NL_HYDRA_LEO_X') == -5
    assert p('SOME_STYLE_RULE') == -50
    assert p('NL_COMPOUNDS') == 0


def test_relevant_rules():
    lang = get_language('nl')
    rules = lang.get_relevant_rules(messages_for('nl'))
    # getRelevantRules without MorfologikDutchSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS', 'UPPERCASE_SENTENCE_START',
        'WHITESPACE_RULE', 'NL_COMPOUNDS', 'DUTCH_WRONG_WORD_IN_CONTEXT', 'NL_WORD_COHERENCY', 'NL_SIMPLE_REPLACE',
        'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH', 'NL_PREFERRED_WORD_RULE', 'NL_SPACE_IN_COMPOUND',
        'SENTENCE_WHITESPACE', 'NL_CHECKCASE']
    assert [type(r) for r in rules[5:9]] == [CompoundRule, DutchWrongWordInContextRule, WordCoherencyRule,
                                             SimpleReplaceRule]
    assert [type(r) for r in rules[11:13]] == [PreferredWordRule, SpaceInCompoundRule]
    assert type(rules[14]) is CheckCaseRule
    assert rules[9].max_words == 40
    assert not unsupported_components(lang)
    assert not unsupported_components(get_language('nl-BE'))


# --- JLanguageToolTest ---

def test_dutch():
    """JLanguageToolTest.testDutch"""
    tool = JLanguageTool(get_language('nl'))
    # Dutch rule has no effect with English error but they are spelling mistakes (Java: 1 match of
    # MorfologikDutchSpellerRule for "spelvout", the spell checker is not ported)
    assert len(tool.check('Hier staat een spelvout voor testdoeleinden.')) == 0
    # do not use simple replace rule: ok=ook|OK|oké
    assert len(tool.check("'Ok Google, zet de nachtlamp naar warm wit' - Veranderd de nachtlamp kleur naar "
                          "warm wit.")) == 0


def test_advanced_typography():
    """JLanguageToolTest.testAdvancedTypography"""
    lang = get_language('nl')
    assert lang.to_advanced_typography("\"Fatima zei 'Hallo' tegen me.\"") == '“Fatima zei ‘Hallo’ tegen me.”'
    assert lang.to_advanced_typography('Bedoelt u wellicht "vivo\'s"?') == 'Bedoelt u wellicht “vivo’s”?'


# --- UppercaseSentenceStartRuleTest ---

def test_dutch_special_cases():
    """UppercaseSentenceStartRuleTest.testDutchSpecialCases (a Dutch without
    pattern rules). Java counts one more match of MorfologikDutchSpellerRule
    (for "sentence") in "A sentence.", "a sentence." and "s sentence."; the
    spell checker is not ported."""
    lang = get_language('nl')
    lt = JLanguageTool(lang, rules=lang.get_relevant_rules(messages_for('nl')))
    assert len(lt.check('A sentence.')) == 0
    assert len(lt.check("'s Morgens...")) == 0
    assert len(lt.check('a sentence.')) == 1
    assert len(lt.check("'s morgens...")) == 1
    assert len(lt.check('s sentence.')) == 1
    assert len(lt.check("'t")) == 1


# --- GenericUnpairedBracketsRuleTest ---

def test_dutch_unpaired_brackets_rule():
    """GenericUnpairedBracketsRuleTest.testDutchRule"""
    lang = get_language('nl')
    lt = JLanguageTool(lang)
    # GenericUnpairedBracketsRuleTest.getBracketsRule: the rule of the language
    rule, = [r for r in lt.get_all_rules() if isinstance(r, GenericUnpairedBracketsRule)]

    def matches(text):
        return len(rule.match([lt.get_analyzed_sentence(text)]))
    # correct sentences:
    assert matches('Het centrale probleem van het werk is de ‘dichterlijke kuischheid’.') == 0
    # this was a bug as there are several pairs that start with the same char:
    assert matches(' Eurlings: “De gegevens van de dienst zijn van cruciaal belang voor de veiligheid van de '
                   'luchtvaart en de scheepvaart”.') == 0
    assert matches(' Eurlings: „De gegevens van de dienst zijn van cruciaal belang voor de veiligheid van de '
                   'luchtvaart en de scheepvaart”.') == 0
    # incorrect sentences:
    assert matches('Het centrale probleem van het werk is de „dichterlijke kuischheid.') == 1
    assert matches(' Eurlings: “De gegevens van de dienst zijn van cruciaal belang voor de veiligheid van de '
                   'luchtvaart en de scheepvaart.') == 1
