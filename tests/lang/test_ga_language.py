"""Checks of the Irish language definition against
org.languagetool.language.Irish (the Java module has no IrishTest; the
language independent parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ga.rules import (CompoundRule, DativePluralStandardReplaceRule, DhaNoBeirtRule,
                                    EnglishHomophoneRule, IrishFGBEqReplaceRule, IrishReplaceRule,
                                    IrishSpecificCaseRule, LogainmRule, PeopleRule, PrestandardReplaceRule,
                                    SpacesRule)
from langtool.lang.ga.tagging import IrishTagger
from langtool.messages import messages_for
from langtool.synthesis import BaseSynthesizer
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ga')


def test_definition():
    lang = get_language('ga')
    assert lang.code == 'ga-IE'
    assert get_language('ga-IE') is lang
    assert lang.name == 'Irish'
    assert lang.countries == ['IE']
    assert isinstance(lang.tagger, IrishTagger)
    synth = lang.synthesizer
    # IrishSynthesizer: a BaseSynthesizer for /ga/irish_synth.dict and /ga/irish_tags.txt
    assert type(synth) is BaseSynthesizer
    assert synth.tags_path.replace('\\', '/').endswith('ga/irish_tags.txt')
    assert type(lang.word_tokenizer) is WordTokenizer
    # IrishHybridDisambiguator: the MultiWordChunker for ga/multiwords.txt, then the XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, XmlRuleDisambiguator]
    assert lang.chunker is None
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'ga', 'grammar.xml']]


def test_priorities():
    """Irish.getPriorityForId"""
    p = get_language('ga').get_priority_for_id
    assert p('TOO_LONG_PARAGRAPH') == -15
    assert p('GA_REPLACE') == 0


def test_relevant_rules():
    lang = get_language('ga')
    rules = lang.get_relevant_rules(messages_for('ga'))
    # getRelevantRules without MorfologikIrishSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'UNPAIRED_BRACKETS', 'DOUBLE_PUNCTUATION', 'UPPERCASE_SENTENCE_START',
        'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE',
        'SENTENCE_WHITESPACE', 'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN',
        'PARAGRAPH_REPEAT_BEGINNING_RULE', 'WORD_REPEAT_RULE', 'GA_LOGAINM', 'GA_PEOPLE', 'GA_SPASANNA',
        'GA_COMPOUNDS', 'GA_PRESTANDARD_REPLACE', 'GA_REPLACE', 'GA_FGB_EQ_REPLACE', 'GA_ENGLISH_HOMOPHONE',
        'GA_DHA_NO_BEIRT', 'GA_DATIVE_PLURALS_STD', 'GA_SPECIFIC_CASE']
    assert [type(r) for r in rules[13:]] == [
        LogainmRule, PeopleRule, SpacesRule, CompoundRule, PrestandardReplaceRule, IrishReplaceRule,
        IrishFGBEqReplaceRule, EnglishHomophoneRule, DhaNoBeirtRule, DativePluralStandardReplaceRule,
        IrishSpecificCaseRule]
    assert rules[4].max_words == 50
    assert rules[1].start_symbols == ['[', '(', '{', '"', '“']
    assert rules[1].end_symbols == [']', ')', '}', '"', '”']
    assert [r.get_id() for r in rules if r.default_off] == [
        'TOO_LONG_PARAGRAPH', 'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN', 'PARAGRAPH_REPEAT_BEGINNING_RULE']
    assert not unsupported_components(lang)


def test_check():
    """a text with errors of the Java and XML rules"""
    matches = JLanguageTool(get_language('ga')).check('Tá dhá dheartháireacha agam. Chuaigh mé go Adare inné.')
    assert [(m.get_specific_rule_id(), m.from_pos, m.to_pos) for m in matches] == [
        ('GA_DHA_NO_BEIRT', 3, 6), ('GA_LOGAINM', 43, 48)]
