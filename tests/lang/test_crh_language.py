"""Port of org.languagetool.tokenizers.crh.CrimeanTatarWordTokenizerTest,
org.languagetool.tokenizers.crh.CrimeanTatarSRXSentenceTokenizerTest,
org.languagetool.tagging.crh.CrimeanTatarTaggerTest,
org.languagetool.synthesis.crh.CrimeanTatarSynthesizerTest and
org.languagetool.rules.crh.MorfologikCrimeanTatarSpellerRuleTest, plus checks
of the Crimean Tatar language definition against
org.languagetool.language.CrimeanTatar, CrimeanTatarTagger and
CrimeanTatarWordTokenizer."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.crh.tagging import CrimeanTatarTagger
from langtool.lang.crh.tokenizers import CrimeanTatarWordTokenizer
from langtool.messages import messages_for
from langtool.synthesis import BaseSynthesizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('crh')


@pytest.mark.skip(reason='spell checking is not ported: MorfologikCrimeanTatarSpellerRuleTest tests '
                         'MorfologikCrimeanTatarSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.rules.crh.MorfologikCrimeanTatarSpellerRuleTest"""


def test_definition():
    lang = get_language('crh')
    assert lang.code == 'crh-UA'
    assert get_language('crh-UA') is lang
    assert lang.name == 'Crimean Tatar'
    assert lang.countries == ['UA']
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    # CrimeanTatar.getSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, CrimeanTatarWordTokenizer)
    assert isinstance(lang.tagger, CrimeanTatarTagger)
    assert isinstance(lang.synthesizer, BaseSynthesizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['crh', 'grammar.xml']]
    assert not unsupported_components(lang)


def test_relevant_rules():
    lang = get_language('crh-UA')
    rules = lang.get_relevant_rules(messages_for('crh'))
    # getRelevantRules without MorfologikCrimeanTatarSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE',
        'SENTENCE_WHITESPACE', 'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN']
    # the Example.wrong/Example.fixed constructor arguments (Rule.addExamplePair)
    comma, upper = rules[0], rules[2]
    assert [(e.example, e.corrections) for e in comma.incorrect_examples] == [
        ('Özü bir çaqrım uzaqta<marker> ,</marker> demiryol keçidi yanında yaşay.', [','])]
    assert [e.example for e in comma.correct_examples] == [
        'Özü bir çaqrım uzaqta<marker>,</marker> demiryol keçidi yanında yaşay.']
    assert [(e.example, e.corrections) for e in upper.incorrect_examples] == [
        ('Meclis Haberleri 10.09.2003. <marker>qırımtatar</marker> Milliy Meclisiniñ 120-cı toplaşuvı olıp keçti',
         ['Qırımtatar'])]
    assert [e.example for e in upper.correct_examples] == [
        'Meclis Haberleri 10.09.2003. <marker>Qırımtatar</marker> Milliy Meclisiniñ 120-cı toplaşuvı olıp keçti']
    for r in rules[1:2] + rules[3:]:
        assert r.incorrect_examples == [] and r.correct_examples == []


def test_rule_examples_match():
    """the examples of the code rules are found (in Java they are only
    documentation)"""
    lt = JLanguageTool(get_language('crh'))
    matches = lt.check('Özü bir çaqrım uzaqta , demiryol keçidi yanında yaşay.')
    assert [(m.rule.get_id(), m.suggested_replacements) for m in matches] == [('COMMA_PARENTHESIS_WHITESPACE', [','])]
    matches = lt.check('Meclis Haberleri 10.09.2003. qırımtatar Milliy Meclisiniñ 120-cı toplaşuvı olıp keçti')
    assert [(m.rule.get_id(), m.suggested_replacements) for m in matches] == [
        ('UPPERCASE_SENTENCE_START', ['Qırımtatar'])]


# --- CrimeanTatarWordTokenizerTest ---

def test_word_tokenize():
    """CrimeanTatarWordTokenizerTest.testTokenize"""
    tokens = CrimeanTatarWordTokenizer().tokenize('Qırımtatar Milliy Meclisiniñ 120-cı toplaşuvı olıp keçti')
    assert '[%s]' % ', '.join(tokens) == \
        '[Qırımtatar,  , Milliy,  , Meclisiniñ,  , 120-cı,  , toplaşuvı,  , olıp,  , keçti]'


def test_word_tokenize_hyphen_and_dash():
    """CrimeanTatarWordTokenizer: a hyphen at the end of a word is split off,
    the n-dash is a tokenizing character"""
    tokenizer = CrimeanTatarWordTokenizer()
    assert tokenizer.tokenize('Otlar- ölenler') == ['Otlar', '-', ' ', 'ölenler']
    assert tokenizer.tokenize('Otlar-ölenler') == ['Otlar-ölenler']
    assert tokenizer.tokenize('a–b - c--') == ['a', '–', 'b', ' ', '-', ' ', 'c-', '-']
    # the URL is joined after the hyphen was split off (joinEMailsAndUrls)
    assert tokenizer.tokenize('bak: http://example.com/a- x') == [
        'bak', ':', ' ', 'http://example.com/a-', ' ', 'x']  # joinUrls takes the hyphen back
    assert tokenizer.tokenize('') == []


# --- CrimeanTatarSRXSentenceTokenizerTest ---

def test_tokenize():
    """CrimeanTatarSRXSentenceTokenizerTest.testTokenize"""
    # accept \n as paragraph:
    stokenizer = SRXSentenceTokenizer(get_language('crh'))
    stokenizer.set_single_line_breaks_marks_paragraph(True)

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('Yapraqlar töküldi. ')
    test_split('Yapraqlar töküldi. ', 'Otlar-ölenler sarardı, soldılar.')


# --- CrimeanTatarTaggerTest ---

def _null(s):
    return 'null' if s is None else s


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    # (getNoWhitespaceTokens: only the tokens with a letter or digit)
    tokens = [t for t in tokenizer.tokenize(text) if any(is_letter(c) or is_digit(c) for c in t)]
    out = []
    for r in tagger.tag(tokens):
        out.append('|'.join(sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in r.readings)))
    assert ' -- '.join(out) == expected


def test_dictionary():
    """CrimeanTatarTaggerTest.testDictionary (TestTools.testDictionary only
    prints warnings for entries without POS tags; check that there are none.
    The dictionary has more than 11 million entries, so they are counted on
    the automaton instead of iterating over them, which takes minutes)"""
    d = get_language('crh').tagger.dictionary
    entries, without_tag = d.count_entries()
    assert entries > 0
    assert without_tag == 0


def test_tagger():
    """CrimeanTatarTaggerTest.testTagger"""
    tagger = get_language('crh').tagger
    _my_assert('meraba', 'meraba/[meraba]INTJ', CrimeanTatarWordTokenizer(), tagger)


def test_tagger_settings():
    """CrimeanTatarTagger: tagLowercaseWithUppercase=false, manual additions
    from /crh/added.txt only"""
    tagger = get_language('crh').tagger
    assert not tagger.tag_lowercase_with_uppercase
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in tagger.tag(['xyzzy'])] == [[(None, None)]]


# --- CrimeanTatarSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string():
    """CrimeanTatarSynthesizerTest.testSynthesizeString"""
    synth = get_language('crh').synthesizer
    assert len(synth.synthesize(_dummy_token('oluñızoluñız'), 'oluñızoluñız')) == 0
    assert synth.synthesize(_dummy_token('sen'), 'NPRO:subst:2per:sing:datv') == ['saña']
    # with regular expressions
    assert sorted(synth.synthesize(_dummy_token('sen'), 'NPRO:subst:2per:sing:lo.*', True)) == ['sende']
