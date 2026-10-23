"""Checks the Lithuanian language definition against
org.languagetool.language.Lithuanian, plus the port of
org.languagetool.tokenizers.lt.LithuanianSRXSentenceTokenizerTest."""

from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.messages import messages_for
from langtool.tagging import DemoTagger
from langtool.tool import JLanguageTool


def test_definition():
    lang = get_language('lt')
    assert lang.code == 'lt-LT'
    assert get_language('lt-LT') is lang
    assert lang.name == 'Lithuanian'
    assert lang.countries == ['LT']
    assert isinstance(lang.tagger, DemoTagger)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)


def _test_split(*sentences):
    # TestTools.testSplit
    stokenizer = SRXSentenceTokenizer(get_language('lt'))
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


def test_tokenize():
    """LithuanianSRXSentenceTokenizerTest.testTokenize"""
    _test_split('Linux – laisvos operacinės sistemos branduolio (kernel) pavadinimas. ',
                'Dažnai taip sutrumpintai vadinama ir bendrai visa Unix-tipo operacinė sistema naudojanti Linux '
                'branduolį kartu su sisteminėmis programomis bei bibliotekomis iš GNU projekto.')


def test_relevant_rules():
    lang = get_language('lt-LT')
    rules = lang.get_relevant_rules(messages_for('lt'))
    # getRelevantRules without MorfologikLithuanianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE']
    assert not unsupported_components(lang)


def test_check():
    lt = JLanguageTool(get_language('lt-LT'))
    matches = lt.check('dažnai taip vadinama  sistema.')
    assert [m.rule.get_id() for m in matches] == ['UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE']
