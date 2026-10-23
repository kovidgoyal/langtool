"""Port of org.languagetool.rules.sl.SlovenianTest (LanguageSpecificTest) and
org.languagetool.JLanguageToolTest (language-sl), plus checks of the
Slovenian language definition against org.languagetool.language.Slovenian.
The language independent parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py (which includes sl)."""

import pytest

from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.messages import messages_for
from langtool.tagging import DemoTagger
from langtool.tool import JLanguageTool


def test_demo_text():
    """SlovenianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Tukaj vnesite svoje besedilo... Pa poglejmo primer besedila s nekaj napakami ki jih lahko razpozna '
         'orodje LanguageTool; ko opazite napake, jih lahko enostavno popiravite. ( Obenem se izvrši tudi '
         'preverjanje črkovanja črkovanja.')
    matches = JLanguageTool(get_language('sl')).check(s)
    # Java expects "TROPIČJETRI", "PREDLOG_S", "KI_BREZ_VEJICE", "MORFOLOGIK_RULE_SL_SI",
    # "COMMA_PARENTHESIS_WHITESPACE", "WORD_REPEAT_RULE"; MORFOLOGIK_RULE_SL_SI (for "popiravite")
    # is the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'TROPIČJETRI', 'PREDLOG_S', 'KI_BREZ_VEJICE', 'COMMA_PARENTHESIS_WHITESPACE', 'WORD_REPEAT_RULE']


def test_slovenian_without_speller():
    """JLanguageToolTest.testSlovenian, the part that does not need the spell
    checker: none of the ported rules matches (see test_slovenian)."""
    assert JLanguageTool(get_language('sl')).check('Kupil je npr. jajca, moko in mleko.') == []


@pytest.mark.skip(reason='spell checking is not ported: the one match Java expects comes from '
                         'MorfologikSlovenianSpellerRule (MORFOLOGIK_RULE_SL_SI)')
def test_slovenian():
    """JLanguageToolTest.testSlovenian"""
    assert len(JLanguageTool(get_language('sl')).check('Kupil je npr. jajca, moko in mleko.')) == 1


def test_definition():
    lang = get_language('sl')
    assert lang.code == 'sl-SI'
    assert get_language('sl-SI') is lang
    assert lang.name == 'Slovenian'
    assert lang.countries == ['SI']
    assert isinstance(lang.tagger, DemoTagger)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert st.tokenize('Kupil je npr. jajca. Pa poglejmo primer.') == ['Kupil je npr. jajca. ', 'Pa poglejmo primer.']


def test_relevant_rules():
    lang = get_language('sl-SI')
    rules = lang.get_relevant_rules(messages_for('sl'))
    # getRelevantRules without MorfologikSlovenianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WORD_REPEAT_RULE', 'WHITESPACE_RULE']
    assert not unsupported_components(lang)


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/prohibit.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.sl.LanguageSpecificSpellcheckerTest"""
