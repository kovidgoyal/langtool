"""Port of org.languagetool.rules.ar.ArabicLanguageSpecificTest (skipped:
it checks the hunspell word lists) plus checks of the Arabic language
definition against org.languagetool.language.Arabic."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ar.rules import (ArabicCommaWhitespaceRule, ArabicInflectedOneWordReplaceRule,
                                    ArabicWordRepeatRule)
from langtool.lang.ar.synthesis import ArabicSynthesizer
from langtool.lang.ar.tagging import ArabicTagger
from langtool.lang.ar.tokenizers import ArabicWordTokenizer
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ar')


@pytest.mark.skip(reason='spell checking is not ported: ArabicLanguageSpecificTest (SpellcheckerTest.'
                         'runLanguageSpecificTest) checks the hunspell prohibit.txt/spelling.txt word lists')
def test_language_specific():
    """ArabicLanguageSpecificTest.testRules"""


def test_definition():
    lang = get_language('ar')
    assert lang.code == 'ar'
    assert lang.name == 'Arabic'
    assert lang.countries == ['', 'SA', 'DZ', 'BH', 'EG', 'IQ', 'JO', 'KW', 'LB', 'LY', 'MA', 'OM', 'QA', 'SD', 'SY',
                              'TN', 'AE', 'YE']
    assert not lang.is_variant()
    assert isinstance(lang.tagger, ArabicTagger)
    assert isinstance(lang.synthesizer, ArabicSynthesizer)
    assert type(lang.word_tokenizer) is ArabicWordTokenizer
    # ArabicHybridDisambiguator: the chunker for ar/multiwords.txt, then the XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, XmlRuleDisambiguator]
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'ar', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('ar')
    rules = lang.get_relevant_rules(messages_for('ar'))
    # getRelevantRules without ArabicHunspellSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'WHITESPACE_RULE', 'SENTENCE_WHITESPACE', 'UNPAIRED_BRACKETS', 'COMMA_PARENTHESIS_WHITESPACE',
        'TOO_LONG_SENTENCE', 'ARABIC_COMMA_PARENTHESIS_WHITESPACE', 'ARABIC_QM_WHITESPACE', 'ARABIC_SC_WHITESPACE',
        'ARABIC_DOUBLE_PUNCTUATION', 'ARABIC_WORD_REPEAT_RULE', 'AR_SIMPLE_REPLACE', 'AR_DIACRITICS_REPLACE',
        'AR_DARJA_REPLACE', 'AR_HOMOPHONES_REPLACE', 'AR_REDUNDANCY_REPLACE', 'AR_WORD_COHERENCY',
        'AR_WORDINESS_REPLACE', 'ARABIC_WRONG_WORD_IN_CONTEXT', 'AR_VERB_TRANSITIVE_IINDIRECT',
        'AR_INFLECTED_ONE_WORD']
    assert not any(r.default_off for r in rules)
    assert rules[2].start_symbols == ['[', '(', '{', '«', '﴾', '"', "'"]
    assert rules[2].end_symbols == [']', ')', '}', '»', '﴿', '"', "'"]
    assert rules[3].quotes_whitespace_check
    assert rules[4].max_words == 50
    assert type(rules[5]) is ArabicCommaWhitespaceRule
    assert type(rules[9]) is ArabicWordRepeatRule
    assert type(rules[-1]) is ArabicInflectedOneWordReplaceRule
    assert rules[5].incorrect_examples[0].example == 'نعم<marker> ،</marker> لقد نجحنا.'
    assert not unsupported_components(lang)


def test_check():
    """JLanguageTool with the Arabic rules"""
    matches = JLanguageTool(get_language('ar')).check('هذا فقط فقط مثال. الى البيت ، يا صديقي')
    assert [(m.get_specific_rule_id(), m.from_pos, m.to_pos, m.suggested_replacements) for m in matches] == [
        ('ARABIC_WORD_REPEAT_RULE', 4, 11, ['فقط']), ('AR_SIMPLE_REPLACE', 18, 21, ['إلى']),
        ('ARABIC_COMMA_PARENTHESIS_WHITESPACE', 27, 29, ['،'])]
