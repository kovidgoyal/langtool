"""Port of org.languagetool.tagging.pt.PortugueseTaggerTest,
org.languagetool.synthesis.pt.PortugueseSynthesizerTest and
org.languagetool.tagging.disambiguation.pt.PortugueseDisambiguationRuleTest,
plus checks of PortugueseTagger."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.pt.tagging import PortugueseTagger
from langtool.lang.pt.tokenizers import PortugueseWordTokenizer
from langtool.tokenizers import WordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pt')


@pytest.fixture(scope='module')
def lang():
    return get_language('pt')


@pytest.fixture(scope='module')
def tagger(lang):
    return lang.tagger


@pytest.fixture(scope='module')
def tokenizer(lang):
    return PortugueseWordTokenizer(lang.tagger)


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _as_strings(readings):
    # TestTools.getAsStrings
    return sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in readings)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


# --- PortugueseTaggerTest ---

def test_dictionary(tagger):
    """PortugueseTaggerTest.testDictionary (TestTools.testDictionary only
    prints warnings for entries without POS tags; check that the dictionary
    can be read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0
    assert isinstance(tagger, PortugueseTagger)


@pytest.mark.parametrize('text,expected', [
    # testTagger
    ('Estes são os meus amigos.',
     'Estes/[este]AQ0CP0|Estes/[este]DD0MP0|Estes/[este]NCMP000|Estes/[este]PD0MP000 -- '
     'são/[ser]VMIP3P0|são/[são]AQ0MS0|são/[são]NCMS000 -- '
     'os/[ele]PP3MPA00|os/[o]DA0MP0|os/[o]PD0MP000 -- '
     'meus/[meu]AP0MP1S|meus/[meu]DP1MPS -- '
     'amigos/[amigo]AQ0MP0|amigos/[amigo]NCMP000'),
    ('tentou resolver',
     'tentou/[tentar]VMIS3S0 -- resolver/[resolver]VMN0000|resolver/[resolver]VMN01S0|resolver/[resolver]VMN03S0|'
     'resolver/[resolver]VMSF1S0|resolver/[resolver]VMSF3S0'),
    # as of dict v0.13, verbs with enclitics are considered as a single word and tagged as such
    ('Deixe-me',
     'Deixe-me/[deixar]VMM03S0:PP1CSO00|Deixe-me/[deixar]VMSP1S0:PP1CSO00|Deixe-me/[deixar]VMSP3S0:PP1CSO00'),
    # testTaggerTagsOrdinalAbbreviations: with regular lowercase letters
    ('1.as', '1.as/[1.º]AO0FP0|1.as/[1.º]NCFP000'),
    ('2as', '2as/[2º]AO0FP0|2as/[2º]NCFP000'),
    ('300as', '300as/[300º]AO0FP0|300as/[300º]NCFP000'),
    # with ordinal indicator
    ('4.ªˢ', '4.ªˢ/[4.º]AO0FP0|4.ªˢ/[4.º]NCFP000'),
    ('5ªˢ', '5ªˢ/[5º]AO0FP0|5ªˢ/[5º]NCFP000'),
    ('600ªˢ', '600ªˢ/[600º]AO0FP0|600ªˢ/[600º]NCFP000'),
    # with superscript
    ('7.ᵃˢ', '7.ᵃˢ/[7.º]AO0FP0|7.ᵃˢ/[7.º]NCFP000'),
    ('8ᵃˢ', '8ᵃˢ/[8º]AO0FP0|8ᵃˢ/[8º]NCFP000'),
    ('900ᵃˢ', '900ᵃˢ/[900º]AO0FP0|900ᵃˢ/[900º]NCFP000'),
    # percent sign
    ('10%', '10%/[10%]NCMP000'),
    ('−11.000%', '−11.000%/[−11.000%]NCMP000'),
    # degree sign
    ('12°', '12°/[12°]NCMP000'),
    # testContractionTagging
    ('das', 'das/[de:o]SPS00:DA0FP0'),
    ('to', 'to/[tu:ele]PP2CSO00:PP3MSA00'),
    ('ao', 'ao/[a:o]SPS00:DA0MS0'),
    # testTaggerTagsCompoundsRegardlessOfLetterCase
    ('jiu-jitsu', 'jiu-jitsu/[jiu-jitsu]NCMS000'),
    ('Jiu-jitsu', 'Jiu-jitsu/[jiu-jitsu]NCMS000'),
    ('JIU-JITSU', 'JIU-JITSU/[jiu-jitsu]NCMS000'),
    ('Jiu-Jitsu', 'Jiu-Jitsu/[jiu-jitsu]NCMS000'),
    # testTagProductivePrefixesNotPresentInSpeller: not a real prefix, must be null
    ('xoxotrepei', 'xoxotrepei/[null]null'),
    # new prefixes, to work with dict v0.13: include prefixes that always require a hyphen, like 'soto-'
    ('soto-trepei', 'soto-trepei/[soto-trepar]VMIS1S0'),
    # testTaggerTagsVerbsWithEnclitics (requires dictionary v0.14)
    ('distribuí-lo-ei', 'distribuí-lo-ei/[distribuir]VMIF1S0:PP3MSA00'),
])
def test_tagger(tagger, tokenizer, text, expected):
    """PortugueseTaggerTest (testTagger, testTaggerTagsOrdinalAbbreviations,
    testContractionTagging, testTaggerTagsCompoundsRegardlessOfLetterCase,
    testTagProductivePrefixesNotPresentInSpeller,
    testTaggerTagsVerbsWithEnclitics)"""
    _my_assert(text, expected, tokenizer, tagger)


def test_tagger_apostrophes_and_flags(tagger):
    """Typographic apostrophes of tokens longer than one character are
    looked up as typewriter apostrophes (the token text changes), tokens
    with a typewriter apostrophe get the chunk tag
    containsTypewriterApostrophe; verbs tagged by their prefix are ignored
    by the speller; -mente adverbs are tagged RG"""
    atr, = tagger.tag(['d’água'])
    assert atr.token == "d'água"
    assert not atr.chunk_tags
    atr, = tagger.tag(["d'água"])
    assert [c.chunk_tag for c in atr.chunk_tags] == ['containsTypewriterApostrophe']
    apos, = tagger.tag(['’'])
    assert apos.token == '’'
    prefixed, plain = tagger.tag(['soto-trepei', 'trepei'])
    assert prefixed.ignored_by_speller and not plain.ignored_by_speller
    assert prefixed.start_pos == 0 and plain.start_pos == len('soto-trepei')
    adverb, = tagger.tag(['Rapidamente'])
    assert [(r.lemma, r.pos_tag) for r in adverb.readings if r.pos_tag == 'RG']


# --- PortugueseSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string(lang):
    """PortugueseSynthesizerTest.testSynthesizeString"""
    synth = lang.synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert sorted(synth.synthesize(_dummy_token('boi'), 'NCMP000', True)) == ['bois']
    assert sorted(synth.synthesize(_dummy_token('tentar'), 'VMN0000', True)) == ['tentar']
    assert sorted(synth.synthesize(_dummy_token('tentar'), 'VMIS3S0', True)) == ['tentou']
    assert sorted(synth.synthesize(_dummy_token('resolver'), 'VMN0000', True)) == ['resolver']
    assert sorted(synth.synthesize(_dummy_token('resolver'), 'VMIS3S0', True)) == ['resolveu']
    # as of dict v1.0.1: issues with 'mesmíssimo' assigned to 'mesmo' lemma
    assert sorted(synth.synthesize(_dummy_token('mesmo'), 'DD0FP0', True)) == ['mesmas']


def test_synthesizer_number_speller(lang):
    """PortugueseSynthesizer passes /pt/pt.sor to BaseSynthesizer (number
    spelling, _spell_number_ tags) and has the Roman numberer"""
    synth = lang.synthesizer
    assert synth.number_speller is not None
    assert synth.get_roman_number('2024') == 'MMXXIV'


# --- PortugueseDisambiguationRuleTest ---

def _my_assert_disambiguated(text, expected, tokenizer, sentence_tokenizer, tagger, disambiguator):
    # TestTools.myAssert(input, expected, tokenizer, sentenceTokenizer, tagger, disambiguator)
    out = []
    for sentence in sentence_tokenizer.tokenize(text):
        tokens = tokenizer.tokenize(sentence)
        a_tokens = tagger.tag([t for t in tokens if _is_word(t)])
        token_array = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)]
        start_pos = 0
        no_whitespace_count = 0
        for token in tokens:
            if _is_word(token):
                pos_tag = a_tokens[no_whitespace_count]
                pos_tag.start_pos = start_pos
                no_whitespace_count += 1
            else:
                pos_tag = tagger.create_null_token(token, start_pos)
            token_array.append(pos_tag)
            start_pos += len(token)
        final_sentence = disambiguator.disambiguate(AnalyzedSentence(token_array))
        out.append(' '.join('|'.join(_as_strings(r.readings)) for r in final_sentence.tokens))
    assert ''.join(out) == expected


@pytest.mark.parametrize('text,expected', [
    ('A cada semana.',
     '/[null]SENT_START A/[a cada semana]RG  /[null]null cada/[a cada semana]RG  /[null]null '
     'semana/[a cada semana]RG ./[.]_PUNCT|./[.]_PUNCT_PERIOD'),
    ('Estes são os meus amigos.',
     '/[null]SENT_START Estes/[este]DD0MP0|Estes/[este]PD0MP000  '
     '/[null]null são/[ser]VMIP3P0|são/[são]AQ0MS0|são/[são]NCMS000  '
     '/[null]null os/[o]DA0MP0  /[null]null meus/[meu]DP1MPS  '
     '/[null]null amigos/[amigo]NCMP000 ./[.]_PUNCT|./[.]_PUNCT_PERIOD'),
    # https://github.com/languagetool-org/languagetool/issues/9063
    ('Foi iniciado eficiente e rapidamente.',
     '/[null]SENT_START Foi/[ser]VMIS3S0  /[null]null iniciado/[iniciar]VMP00SM  '
     '/[null]null eficiente/[eficiente]RM  /[null]null e/[e]CC  /[null]null rapidamente/[rapidamente]RM '
     './[.]_PUNCT|./[.]_PUNCT_PERIOD'),
    ('Foi iniciado na China e rapidamente disseminado.',
     '/[null]SENT_START Foi/[ser]VMIS3S0  /[null]null iniciado/[iniciar]VMP00SM  '
     '/[null]null na/[em:o]SPS00:DA0FS0  /[null]null China/[China]NPFSG00|China/[china]NCCS000  '
     '/[null]null e/[e]CC  /[null]null rapidamente/[rapidamente]RM  /[null]null disseminado/[disseminar]VMP00SM '
     './[.]_PUNCT|./[.]_PUNCT_PERIOD'),
])
def test_chunker(lang, text, expected):
    """PortugueseDisambiguationRuleTest.testChunker (with the core
    WordTokenizer and PortugueseHybridDisambiguator)"""
    _my_assert_disambiguated(text, expected, WordTokenizer(), SRXSentenceTokenizer(lang), lang.tagger,
                             lang.disambiguator)
