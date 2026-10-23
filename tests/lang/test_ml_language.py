"""Port of org.languagetool.tokenizers.ml.MalayalamSRXSentenceTokenizerTest
and org.languagetool.rules.ml.MorfologikMalayalamSpellerRuleTest, plus checks
of the Malayalam language definition against
org.languagetool.language.Malayalam, MalayalamTagger and
MalayalamWordTokenizer."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ml.tokenizers import MalayalamWordTokenizer
from langtool.messages import messages_for
from langtool.tagging import BaseTagger
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ml')


@pytest.mark.skip(reason='spell checking is not ported: MorfologikMalayalamSpellerRuleTest tests '
                         'MorfologikMalayalamSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.rules.ml.MorfologikMalayalamSpellerRuleTest"""


def test_definition():
    lang = get_language('ml')
    assert lang.code == 'ml-IN'
    assert get_language('ml-IN') is lang
    assert lang.name == 'Malayalam'
    assert lang.countries == ['IN']
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, MalayalamWordTokenizer)


def test_word_tokenizer():
    """MalayalamWordTokenizer: a StringTokenizer that returns the delimiters"""
    tokenizer = MalayalamWordTokenizer()
    # the zero width joiner (U+200D) of the chillu letters is not a delimiter
    assert tokenizer.tokenize('ഞാന്‍ നൂറ് രൂപ.') == ['ഞാന്‍', ' ', 'നൂറ്', ' ', 'രൂപ', '.']
    assert tokenizer.tokenize('ഗ്നൂ/ലിനക്സിൽ (a,b)…"x’') == [
        'ഗ്നൂ', '/', 'ലിനക്സിൽ', ' ', '(', 'a', ',', 'b', ')', '…', '"', 'x', '’']
    # not delimiters (unlike the default WordTokenizer): '-', U+2009, '\r', '«'
    assert tokenizer.tokenize('a-b c\r«d e f\tg\nh') == [
        'a-b c\r«d', ' ', 'e', ' ', 'f', '\t', 'g', '\n', 'h']
    assert tokenizer.tokenize('') == []
    assert tokenizer.tokenize('  ') == [' ', ' ']


def test_tagger():
    """MalayalamTagger: BaseTagger for /ml/malayalam.dict"""
    tagger = get_language('ml-IN').tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    readings = tagger.tag(['ആണ്', 'xyzzy'])
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in readings] == [
        [('ആണ്', 'VBB')],
        [(None, None)]]


def test_relevant_rules():
    lang = get_language('ml-IN')
    rules = lang.get_relevant_rules(messages_for('ml'))
    # getRelevantRules without MorfologikMalayalamSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WORD_REPEAT_RULE', 'WHITESPACE_RULE']
    assert rules[2].start_symbols == ['[', '(', '{', '"', "'"]
    assert rules[2].end_symbols == [']', ')', '}', '"', "'"]
    assert not unsupported_components(lang)


def test_rule_with_empty_name():
    """grammar.xml has <rule id="ഭയങ്കര" name="">: the name of a <rule> is an
    optional xs:string in rules.xsd, so Java loads it with an empty
    description, and so do we."""
    lt = JLanguageTool(get_language('ml'))
    rule = [r for r in lt.get_all_rules() if r.get_id() == 'ഭയങ്കര'][0]
    assert rule.get_description() == ''
    matches = lt.check('അമ്മ്യക്ക് എന്നെ ഭയങ്കര ഇഷ്ടമാണ്. ')
    assert [(m.rule.get_id(), m.suggested_replacements) for m in matches] == [('ഭയങ്കര', ['വളരെ'])]


def test_tokenize():
    """MalayalamSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('ml'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('1983 ൽ റിച്ചാർഡ് സ്റ്റാൾമാൻ സ്ഥാപിച്ച ഗ്നു എന്ന സംഘടനയിൽ നിന്നും വളർന്നു വന്ന '
               'സോഫ്റ്റ്‌വെയറും ടൂളുകളുമാണ് ഇന്ന് ഗ്നൂ/ലിനക്സിൽ ലഭ്യമായിട്ടുള്ള സോഫ്റ്റ്‌വെയറിൽ സിംഹഭാഗവും. ',
               'ഗ്നു സംഘത്തിന്റെ മുഖ്യലക്ഷ്യം സ്വതന്ത്ര സോഫ്റ്റ്‌വെയറുകൾ മാത്രം ഉപയോഗിച്ചുകൊണ്ട് യുണിക്സ് '
               'പോലുള്ള ഒരു ഓപ്പറേറ്റിംഗ് സിസ്റ്റം നിർമ്മിക്കുന്നതായിരുന്നു.')
