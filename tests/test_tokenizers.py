"""Port of org.languagetool.tokenizers.WordTokenizerTest,
SimpleSentenceTokenizerTest and ManualTaggerAdapterTest."""

import os
import types

import pytest

from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.extensions import SRXSentenceTokenizer
from langtool.tagging import ManualTagger
from langtool.tokenizers import WordTokenizer, is_email, is_url

SRC_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'langtool', 'data')

word_tokenizer = WordTokenizer()


def tokenize(text):
    return '|'.join(word_tokenizer.tokenize(text))


# --- WordTokenizerTest ---

def test_tokenize():
    wt = WordTokenizer()
    tokens = wt.tokenize('This is a test')
    assert len(tokens) == 7
    assert tokens == ['This', ' ', 'is', ' ', 'a', ' ', 'test']
    tokens = wt.tokenize('This\rbreaks')
    assert len(tokens) == 3
    assert tokens == ['This', '\r', 'breaks']
    assert len(wt.tokenize('dev.all@languagetool.org')) == 1
    assert len(wt.tokenize('dev.all@languagetool.org.')) == 2
    assert len(wt.tokenize('dev.all@languagetool.org:')) == 2
    assert len(wt.tokenize('Schreiben Sie Hr. Meier (meier@mail.com).')) == 13
    tokens = wt.tokenize('Get more at languagetool.org/foo, and via twitter')
    assert len(tokens) == 14
    assert 'languagetool.org/foo' in tokens
    tokens = wt.tokenize('Get more at sub.languagetool.org/foo, and via twitter')
    assert len(tokens) == 14
    assert 'sub.languagetool.org/foo' in tokens


def test_is_url():
    assert is_url('www.languagetool.org')
    assert is_url('languagetool.org/')
    assert is_url('languagetool.org/foo')
    assert is_url('subdomain.languagetool.org/')
    assert is_url('http://www.languagetool.org')
    assert is_url('https://www.languagetool.org')
    assert not is_url('languagetool.org')  # not detected yet
    assert not is_url('sub.languagetool.org')  # not detected yet
    assert not is_url('something-else')


def test_is_email():
    assert is_email('martin.mustermann@test.de')
    assert is_email('martin.mustermann@test.languagetool.de')
    assert is_email('martin-mustermann@test.com')
    assert not is_email('@test.de')
    assert not is_email('f.test@test')
    assert not is_email('f@t.t')


def test_url_tokenize():
    assert tokenize('"This http://foo.org."') == '"|This| |http://foo.org|.|"'
    assert tokenize('«This http://foo.org.»') == '«|This| |http://foo.org|.|»'
    assert tokenize('This http://foo.org...') == 'This| |http://foo.org|.|.|.'
    assert tokenize('This http://foo.org.') == 'This| |http://foo.org|.'
    assert tokenize('This http://foo.org blah') == 'This| |http://foo.org| |blah'
    assert tokenize('This http://foo.org and ftp://bla.com blah') == \
        'This| |http://foo.org| |and| |ftp://bla.com| |blah'
    assert tokenize('foo http://localhost:32000/?ch=1 bar') == 'foo| |http://localhost:32000/?ch=1| |bar'
    assert tokenize('foo ftp://localhost:32000/ bar') == 'foo| |ftp://localhost:32000/| |bar'
    assert tokenize('foo http://google.de/?aaa bar') == 'foo| |http://google.de/?aaa| |bar'
    assert tokenize('foo http://www.flickr.com/123@N04/hallo#test bar') == \
        'foo| |http://www.flickr.com/123@N04/hallo#test| |bar'
    assert tokenize('foo http://www.youtube.com/watch?v=wDN_EYUvUq0 bar') == \
        'foo| |http://www.youtube.com/watch?v=wDN_EYUvUq0| |bar'
    assert tokenize('foo http://example.net/index.html?s=A54C6FE2%23info bar') == \
        'foo| |http://example.net/index.html?s=A54C6FE2%23info| |bar'
    assert tokenize('foo https://writerduet.com/script/#V6922~***~branch=-MClu-LnPrTNz8oz_rJb bar') == \
        'foo| |https://writerduet.com/script/#V6922~***~branch=-MClu-LnPrTNz8oz_rJb| |bar'
    assert tokenize('foo https://joe:passwd@example.net:8080/index.html?action=x&session=A54C6FE2#info bar') == \
        'foo| |https://joe:passwd@example.net:8080/index.html?action=x&session=A54C6FE2#info| |bar'


def test_url_tokenize_with_quote():
    assert tokenize("This 'http://foo.org' blah") == "This| |'|http://foo.org|'| |blah"
    assert tokenize('This "http://foo.org" blah') == 'This| |"|http://foo.org|"| |blah'
    assert tokenize('This ("http://foo.org") blah') == 'This| |(|"|http://foo.org|"|)| |blah'  # issue #1226


def test_url_tokenize_with_appended_character():
    assert tokenize('foo (http://ex.net/p?a=x#i) bar') == 'foo| |(|http://ex.net/p?a=x#i|)| |bar'
    assert tokenize('foo http://ex.net/p?a=x#i, bar') == 'foo| |http://ex.net/p?a=x#i|,| |bar'
    assert tokenize('foo http://ex.net/p?a=x#i. bar') == 'foo| |http://ex.net/p?a=x#i|.| |bar'
    assert tokenize('foo http://ex.net/p?a=x#i: bar') == 'foo| |http://ex.net/p?a=x#i|:| |bar'
    assert tokenize('foo http://ex.net/p?a=x#i? bar') == 'foo| |http://ex.net/p?a=x#i|?| |bar'
    assert tokenize('foo http://ex.net/p?a=x#i! bar') == 'foo| |http://ex.net/p?a=x#i|!| |bar'


def test_incomplete_url_tokenize():
    assert tokenize('http:/') == 'http|:|/'
    assert tokenize('http://') == 'http://'
    assert tokenize('http://a') == 'http://a'
    assert tokenize('foo http bar') == 'foo| |http| |bar'
    assert tokenize('foo http: bar') == 'foo| |http|:| |bar'
    assert tokenize('foo http:/ bar') == 'foo| |http|:|/| |bar'
    assert tokenize('foo http:// bar') == 'foo| |http://| |bar'
    assert tokenize('foo http://a bar') == 'foo| |http://a| |bar'
    assert tokenize('foo http://? bar') == 'foo| |http://|?| |bar'


def test_check_currency_expression():
    assert word_tokenizer.is_currency_expression('US$45')
    assert word_tokenizer.is_currency_expression('5,000€')
    assert word_tokenizer.is_currency_expression('£1.50')
    assert word_tokenizer.is_currency_expression('R$1.999.99')
    assert not word_tokenizer.is_currency_expression('US$')
    assert not word_tokenizer.is_currency_expression('X€')
    assert not word_tokenizer.is_currency_expression('.50£')
    assert not word_tokenizer.is_currency_expression('5R$5')


def test_split_currency_expression():
    assert word_tokenizer.split_currency_expression('US$45') == ['US$', '45']
    assert word_tokenizer.split_currency_expression('5,000€') == ['5,000', '€']
    assert word_tokenizer.split_currency_expression('£1.50') == ['£', '1.50']
    assert word_tokenizer.split_currency_expression('R$1.999.99') == ['R$', '1.999.99']
    # not currency expr
    assert word_tokenizer.split_currency_expression('US$X') == ['US$X']
    assert word_tokenizer.split_currency_expression('foobar') == ['foobar']


# --- SimpleSentenceTokenizerTest ---

def simple_sentence_tokenizer():
    """Equivalent of org.languagetool.tokenizers.SimpleSentenceTokenizer:
    an SRXSentenceTokenizer for a fake language 'xx' using segment-simple.srx."""
    any_language = types.SimpleNamespace(short_code='xx')
    return SRXSentenceTokenizer(any_language, os.path.join(SRC_DATA, 'resource', 'segment-simple.srx'))


def _test_split(*sentences):
    # TestTools.testSplit
    assert simple_sentence_tokenizer().tokenize(''.join(sentences)) == list(sentences)


def test_simple_sentence_tokenizer():
    _test_split('Hi! ', 'This is a test. ', "Here's more. ", 'And even more?? ', 'Yes.')


# --- ManualTaggerAdapterTest ---

MANUAL_TAGGER_TEST_DATA = (
    '# some test data\n'
    'inflectedform11\tlemma1\tPOS1\n'
    'inflectedform121\tlemma1\tPOS2\n'
    'inflectedform122\tlemma1\tPOS2\n'
    'inflectedform123\tlemma1\tPOS3\n'
    'inflectedform2\tlemma2\tPOS1a\n'
    'inflectedform2\tlemma2\tPOS1b\n'
    'inflectedform2\tlemma2\tPOS1c\n'
    'inflectedform3\tlemma3a\tPOS3a\n'
    'inflectedform3\tlemma3b\tPOS3b\n'
    'inflectedform3\tlemma3c\tPOS3c\n'
    'inflectedform3\tlemma3d\tPOS3d\n'
)


class ManualTaggerAdapter:
    """Port of the test helper org.languagetool.tokenizers.ManualTaggerAdapter"""

    def __init__(self, manual_tagger):
        self.manual_tagger = manual_tagger

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            l = [AnalyzedToken(word, t.pos_tag, t.lemma) for t in self.manual_tagger.tag(word.lower())]
            if not l:
                l.append(AnalyzedToken(word, None, None))
            token_readings.append(AnalyzedTokenReadings(l, pos))
            pos += len(word)
        return token_readings

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)

    def create_token(self, token, pos_tag):
        return AnalyzedToken(token, pos_tag, None)


@pytest.fixture
def adapter_tagger(tmp_path):
    p = tmp_path / 'manual.txt'
    p.write_text(MANUAL_TAGGER_TEST_DATA, encoding='utf-8')
    return ManualTaggerAdapter(ManualTagger([str(p)]))


def test_manual_tagger_adapter_multiple_lemma(adapter_tagger):
    atrs = adapter_tagger.tag(['inflectedform3'])
    assert atrs is not None
    assert len(atrs) == 1
    atr = atrs[0]
    assert atr.token == 'inflectedform3'
    assert atr.readings is not None
    assert len(atr.readings) == 4
    for i, suffix in enumerate('abcd'):
        at = atr.readings[i]
        assert at.token == 'inflectedform3'
        assert at.lemma == 'lemma3' + suffix
        assert at.pos_tag == 'POS3' + suffix


def test_manual_tagger_adapter_multiple_pos(adapter_tagger):
    atrs = adapter_tagger.tag(['inflectedform2'])
    assert atrs is not None
    assert len(atrs) == 1
    atr = atrs[0]
    assert atr.token == 'inflectedform2'
    assert atr.readings is not None
    assert len(atr.readings) == 3
    for i, suffix in enumerate('abc'):
        at = atr.readings[i]
        assert at.pos_tag == 'POS1' + suffix
        assert at.token == 'inflectedform2'
        assert at.lemma == 'lemma2'


def test_manual_tagger_adapter_multiple_words(adapter_tagger):
    atrs = adapter_tagger.tag(['inflectedform2', 'inflectedform3'])
    assert atrs is not None
    assert len(atrs) == 2
    assert atrs[0].token == 'inflectedform2'
    assert len(atrs[0].readings) == 3
    assert atrs[1].token == 'inflectedform3'
    assert len(atrs[1].readings) == 4


SRX_CARET = '''<?xml version="1.0" encoding="UTF-8"?>
<srx xmlns="http://www.lisa.org/srx20" version="2.0">
<header segmentsubflows="yes" cascade="yes"/>
<body>
<languagerules>
<languagerule languagerulename="Test">
<rule break="no"><beforebreak>^\\d+\\.\\s</beforebreak><afterbreak>\\p{L}</afterbreak></rule>
<rule break="no"><beforebreak>\\.\\s</beforebreak><afterbreak>^x</afterbreak></rule>
<rule break="yes"><beforebreak>\\.\\s</beforebreak><afterbreak></afterbreak></rule>
</languagerule>
</languagerules>
<maprules>
<languagemap languagepattern="xx.*" languagerulename="Test"/>
</maprules>
</body>
</srx>
'''


def test_srx_caret_in_exception_rules(tmp_path):
    """The exception (break="no") rules are matched in Java with transparent
    bounds from the break position: ^ in the before pattern (a lookbehind)
    matches at the start of the text, ^ in the after pattern at the break
    position"""
    path = tmp_path / 'test.srx'
    path.write_text(SRX_CARET, encoding='utf-8')
    tokenizer = SRXSentenceTokenizer(types.SimpleNamespace(short_code='xx'), str(path))
    assert tokenizer.tokenize('1. Uno. Dos.') == ['1. Uno. ', 'Dos.']
    assert tokenizer.tokenize('Ver 1. Uno.') == ['Ver 1. ', 'Uno.']
    assert tokenizer.tokenize('Uno. xyz. Dos.') == ['Uno. xyz. ', 'Dos.']
