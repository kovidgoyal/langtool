"""Port of org.languagetool.tagging.en.EnglishTaggerTest,
org.languagetool.synthesis.en.EnglishSynthesizerTest,
org.languagetool.tagging.disambiguation.rules.en.EnglishDisambiguationRuleTest,
org.languagetool.chunking.EnglishChunkerTest and
org.languagetool.chunking.EnglishChunkFilterTest."""

import re

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.chunking import ChunkTag, ChunkTaggedToken
from langtool.disambiguation import DemoDisambiguator, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, disambiguation_rules
from langtool.lang.en.chunking import EnglishChunkFilter, EnglishChunker
from langtool.lang.en.tagging import EnglishTagger
from langtool.lang.en.tokenizers import EnglishWordTokenizer
from langtool.tokenizers import WordTokenizer, string_tokenize
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter, java_trim


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('en')


@pytest.fixture(scope='module')
def lang():
    return get_language('en')


@pytest.fixture(scope='module')
def tagger(lang):
    return lang.tagger


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


# --- EnglishTaggerTest ---

def test_dictionary(tagger):
    """EnglishTaggerTest.testDictionary (TestTools.testDictionary only
    prints warnings for entries without POS tags; check that the dictionary
    can be read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0
    assert isinstance(tagger, EnglishTagger)


@pytest.mark.parametrize('text,expected', [
    ('This is a big house.',
     'This/[this]DT|This/[this]PDT -- is/[be]VBZ -- a/[a]DT -- big/[big]JJ|big/[big]RB -- '
     'house/[house]NN|house/[house]VB|house/[house]VBP'),
    ('Marketing do a lot of trouble.',
     'Marketing/[market]VBG|Marketing/[marketing]NN:U -- do/[do]VB|do/[do]VBP -- a/[a]DT -- lot/[lot]NN -- '
     'of/[of]IN -- trouble/[trouble]NN:UN|trouble/[trouble]VB|trouble/[trouble]VBP'),
    ('Manager use his laptop every day.',
     'Manager/[manager]NN -- use/[use]NN:UN|use/[use]VB|use/[use]VBP -- '
     'his/[he]PRP$_A3SM|his/[he]PRP$_P3SM|his/[hi]NNS|his/[his]PRP$ -- laptop/[laptop]NN -- '
     'every/[every]DT -- day/[day]NN:UN'),
    ('This is a bigger house.',
     'This/[this]DT|This/[this]PDT -- is/[be]VBZ -- a/[a]DT -- bigger/[big]JJR -- '
     'house/[house]NN|house/[house]VB|house/[house]VBP'),
    ("He doesn't believe me.",
     "He/[he]PRP|He/[he]PRP_S3SM -- does/[do]VBZ|does/[doe]NNS -- n't/[not]RB -- "
     'believe/[believe]VB|believe/[believe]VBP -- me/[I]PRP|me/[I]PRP_O1S'),
    ('It has become difficult.',
     'It/[it]PRP|It/[it]PRP_O3SN|It/[it]PRP_S3SN -- has/[have]VBZ -- '
     'become/[become]VB|become/[become]VBN|become/[become]VBP -- difficult/[difficult]JJ'),
    ("You haven't.",
     'You/[you]PRP|You/[you]PRP_O2P|You/[you]PRP_O2S|You/[you]PRP_S2P|You/[you]PRP_S2S -- '
     "have/[have]NN|have/[have]VB|have/[have]VBP -- n't/[not]RB"),
    ('You haven’t.',
     'You/[you]PRP|You/[you]PRP_O2P|You/[you]PRP_O2S|You/[you]PRP_S2P|You/[you]PRP_S2S -- '
     "have/[have]NN|have/[have]VB|have/[have]VBP -- n't/[not]RB"),
])
def test_tagger(tagger, text, expected):
    """EnglishTaggerTest.testTagger"""
    _my_assert(text, expected, EnglishWordTokenizer(tagger), tagger)


def test_lemma(tagger):
    """EnglishTaggerTest.testLemma"""
    a_token = tagger.tag(['Trump', 'works'])
    assert len(a_token) == 2
    assert len(a_token[0].readings) == 4
    assert len(a_token[1].readings) == 2
    assert [r.lemma for r in a_token[0].readings] == ['Trump', 'trump', 'trump', 'trump']
    assert [r.lemma for r in a_token[1].readings] == ['work', 'work']


def test_typographic_apostrophe(tagger):
    """EnglishTagger.tag: typographic apostrophes of tokens longer than one
    character are replaced (the token is marked), unknown words ending in
    "in'" are tagged like the "-ing" form, unknown all-uppercase words with
    an uppercase first character"""
    atr, = tagger.tag(['n’t'])
    assert atr.token == "n't" and atr.typographic_apostrophe
    apos, = tagger.tag(['’'])
    assert apos.token == '’' and not apos.typographic_apostrophe
    doin, = tagger.tag(["doin'"])
    assert ('do', 'VBG') in [(r.lemma, r.pos_tag) for r in doin.readings]
    doin, = tagger.tag(["DOIN'"])
    assert ('do', 'VBG') in [(r.lemma, r.pos_tag) for r in doin.readings]
    france, = tagger.tag(['FRANCE'])
    assert 'NNP' in [r.pos_tag for r in france.readings]
    unknown, = tagger.tag(['xyzzyq'])
    assert [(r.lemma, r.pos_tag) for r in unknown.readings] == [(None, None)]
    first, second = tagger.tag(['a’b', 'c'])
    assert first.start_pos == 0 and second.start_pos == 3


# --- EnglishSynthesizerTest ---

def _dummy_token(token_str, token_lemma=None):
    return AnalyzedToken(token_str, token_str, token_str if token_lemma is None else token_lemma)


def _s(forms):
    # Arrays.toString
    return '[' + ', '.join(forms) + ']'


def test_synthesize_string_string(lang):
    """EnglishSynthesizerTest.testSynthesizeStringString"""
    synth = lang.synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert _s(synth.synthesize(_dummy_token('be'), 'VBD')) == '[was, were]'
    assert _s(synth.synthesize(_dummy_token('president'), 'NNS')) == '[presidents]'
    assert _s(synth.synthesize(_dummy_token('test'), 'VBD')) == '[tested]'
    assert _s(synth.synthesize(_dummy_token('test'), 'VBD', False)) == '[tested]'
    # with regular expressions
    assert _s(synth.synthesize(_dummy_token('test'), 'VBD', True)) == '[tested]'
    assert _s(synth.synthesize(_dummy_token('test'), 'VBD|VBG', True)) == '[tested, testing]'
    # with special indefinite article
    assert _s(synth.synthesize(_dummy_token('university'), '+DT', False)) == '[a university, the university]'
    assert _s(synth.synthesize(_dummy_token('hour'), '+DT', False)) == '[an hour, the hour]'
    assert _s(synth.synthesize(_dummy_token('hour'), '+INDT', False)) == '[an hour]'
    # indefinite article and other changes...
    assert _s(synth.synthesize(_dummy_token('hours', 'hour'), 'NN\\+INDT', True)) == '[an hour]'
    assert _s(synth.synthesize(_dummy_token('hexagon'), 'NN|NN:.*\\+INDT', True)) == '[a hexagon]'
    # indefinite article and other changes...
    assert _s(synth.synthesize(_dummy_token('hours', 'hour'), 'NN\\+DT', True)) == '[the hour]'
    # from added.txt:
    assert _s(synth.synthesize(_dummy_token('absolutize'), 'VBD', False)) == '[absolutized]'
    assert _s(synth.synthesize(_dummy_token('absolutize'), 'VB[XD]', True)) == '[absolutized]'
    # from removed.txt:
    assert _s(synth.synthesize(_dummy_token('Christmas'), 'VBZ', False)) == '[]'
    assert _s(synth.synthesize(_dummy_token('12'), '_spell_number_', False)) == '[twelve]'
    assert _s(synth.synthesize(_dummy_token('1243'), '_spell_number_', False)) == \
        '[one thousand two hundred forty-three]'
    assert _s(synth.synthesize(_dummy_token('12'), '_spell_number_', True)) == '[twelve]'
    assert _s(synth.synthesize(_dummy_token('myself', 'I'), 'PRP_S1S', True)) == '[I]'
    assert _s(synth.synthesize(_dummy_token('myself', 'I'), 'PRP\\$_A1S', True)) == '[my]'
    assert _s(synth.synthesize(_dummy_token('mix'), 'VBD')) == '[mixed]'
    assert _s(synth.synthesize(_dummy_token('mix'), 'VBN')) == '[mixed]'


# --- EnglishDisambiguationRuleTest ---

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


def test_disambiguation_chunker(lang, tagger):
    """EnglishDisambiguationRuleTest.testChunker (with the core
    WordTokenizer, the XmlRuleDisambiguator without the global rules, the
    DemoDisambiguator and EnglishHybridDisambiguator)"""
    tokenizer = WordTokenizer()
    sentence_tokenizer = SRXSentenceTokenizer(lang)
    disambiguator = XmlRuleDisambiguator(lang, disambiguation_rules(lang, False)[0])
    disamb2 = DemoDisambiguator()
    hybrid_disam = lang.disambiguator
    _my_assert_disambiguated(
        'I cannot have it.',
        '/[null]SENT_START I/[I]PRP|I/[I]PRP_S1S  /[null]null cannot/[can]MD  /[null]null have/[have]VB  '
        '/[null]null it/[it]PRP|it/[it]PRP_O3SN|it/[it]PRP_S3SN ./[.]PCT',
        tokenizer, sentence_tokenizer, tagger, disambiguator)
    _my_assert_disambiguated(
        'I cannot have it.',
        '/[null]SENT_START I/[I]PRP|I/[I]PRP_S1S  /[null]null cannot/[can]MD  '
        '/[null]null have/[have]NN|have/[have]VB|have/[have]VBP  '
        '/[null]null it/[it]PRP|it/[it]PRP_O3SN|it/[it]PRP_S3SN ./[null]null',
        tokenizer, sentence_tokenizer, tagger, disamb2)
    _my_assert_disambiguated(
        'He is to blame.',
        '/[null]SENT_START He/[he]PRP|He/[he]PRP_S3SM  /[null]null is/[be]VBZ  /[null]null to/[to]IN|to/[to]TO  '
        '/[null]null blame/[blame]VB ./[.]PCT',
        tokenizer, sentence_tokenizer, tagger, disambiguator)
    _my_assert_disambiguated(
        'He is to blame.',
        '/[null]SENT_START He/[he]PRP|He/[he]PRP_S3SM  /[null]null is/[be]VBZ  /[null]null to/[to]IN|to/[to]TO  '
        '/[null]null blame/[blame]JJ|blame/[blame]NN:UN|blame/[blame]VB|blame/[blame]VBP ./[null]null',
        tokenizer, sentence_tokenizer, tagger, disamb2)
    _my_assert_disambiguated(
        'He is well known.',
        '/[null]SENT_START He/[he]PRP|He/[he]PRP_S3SM  /[null]null is/[be]VBZ  '
        '/[null]null well/[well]JJ|well/[well]NN|well/[well]RB|well/[well]UH|well/[well]VB|well/[well]VBP  '
        '/[null]null known/[know]VBN|known/[known]NN ./[null]null',
        tokenizer, sentence_tokenizer, tagger, disamb2)
    _my_assert_disambiguated(
        'The quid pro quo.',
        '/[null]SENT_START The/[the]DT  /[null]null quid/[quid pro quo]NN  /[null]null pro/[quid pro quo]NN  '
        '/[null]null quo/[quid pro quo]NN ./[.]PCT',
        tokenizer, sentence_tokenizer, tagger, hybrid_disam)
    _my_assert_disambiguated(
        'The QUID PRO QUO.',
        '/[null]SENT_START The/[the]DT  /[null]null QUID/[quid pro quo]NN  /[null]null PRO/[quid pro quo]NN  '
        '/[null]null QUO/[quid pro quo]NN ./[.]PCT',
        tokenizer, sentence_tokenizer, tagger, hybrid_disam)


# --- EnglishChunkerTest ---

def _create_readings_list(sentence):
    result = []
    pos = 0
    for tok in string_tokenize(sentence, ' '):
        if not java_trim(tok):
            result.append(AnalyzedTokenReadings(AnalyzedToken(tok, None, None), pos))
        else:
            result.append(AnalyzedTokenReadings(AnalyzedToken(tok, 'fake', 'fake'), pos))
        pos += len(tok)
    return result


def _chunks(atr):
    # getChunkTags().toString()
    return '[' + ', '.join(str(c) for c in atr.chunk_tags) + ']'


def test_add_chunk_tags(lang):
    """EnglishChunkerTest.testAddChunkTags"""
    chunker = EnglishChunker(lang)
    readings_list = _create_readings_list('A short test of the bicycle is needed')
    chunker.add_chunk_tags(readings_list)
    assert len(readings_list) == 15
    # "A short test":
    assert _chunks(readings_list[0]) == '[B-NP-singular]'
    assert _chunks(readings_list[2]) == '[I-NP-singular]'
    assert _chunks(readings_list[4]) == '[E-NP-singular]'
    # "the bicycle":
    assert _chunks(readings_list[8]) == '[B-NP-singular]'
    assert _chunks(readings_list[10]) == '[E-NP-singular]'
    # "is needed"
    assert _chunks(readings_list[12]) == '[B-VP]'
    assert _chunks(readings_list[14]) == '[I-VP]'


def test_singular_noun_at_end_of_noun_phrase(lang):
    """EnglishChunkerTest.testSingularNounAtEndOfNounPhrase"""
    lt = JLanguageTool(lang)
    res1 = lt.analyze_text('The aircraft manager is here.')[0].tokens
    assert _chunks(res1[1]) == '[B-NP-singular]'
    assert _chunks(res1[3]) == '[I-NP-singular]'
    assert _chunks(res1[5]) == '[E-NP-singular]'
    res2 = lt.analyze_text('The aircraft maintenance manager is here.')[0].tokens
    assert _chunks(res2[1]) == '[B-NP-singular]'
    assert _chunks(res2[3]) == '[I-NP-singular]'
    assert _chunks(res2[5]) == '[I-NP-singular]'
    assert _chunks(res2[7]) == '[E-NP-singular]'
    res3 = lt.analyze_text('Does your box converter operate correctly?')[0].tokens
    assert _chunks(res3[3]) == '[B-NP-singular]'
    assert _chunks(res3[5]) == '[I-NP-singular]'
    assert _chunks(res3[7]) == '[E-NP-singular]'
    res5 = lt.analyze_text('I’d like a fish pie.')[0].tokens
    assert _chunks(res5[6]) == '[B-NP-singular]'
    assert _chunks(res5[8]) == '[I-NP-singular]'
    assert _chunks(res5[10]) == '[E-NP-singular]'


def test_add_chunk_tags_singular(lang):
    """EnglishChunkerTest.testAddChunkTagsSingular"""
    chunker = EnglishChunker(lang)
    lt = JLanguageTool(lang)
    readings_list = list(lt.analyze_text('The abacus shows how numbers can be stored')[0].tokens)
    chunker.add_chunk_tags(readings_list)
    # "The abacus":
    assert _chunks(readings_list[1]) == '[B-NP-singular]'
    assert _chunks(readings_list[3]) == '[E-NP-singular]'
    # "numbers":
    assert _chunks(readings_list[9]) == '[B-NP-plural, E-NP-plural]'


def test_contractions(lang):
    """EnglishChunkerTest.testContractions"""
    lt = JLanguageTool(lang)
    tokens = lt.get_analyzed_sentence("I'll be there").tokens
    assert tokens[1].chunk_tags[0] == ChunkTag('B-NP-singular')
    assert tokens[2].chunk_tags[0] == ChunkTag('B-VP')
    assert tokens[4].chunk_tags[0] == ChunkTag('I-VP')
    assert tokens[6].chunk_tags[0] == ChunkTag('I-VP')


def test_tokenize(lang):
    """EnglishChunkerTest.testTokenize"""
    chunker = EnglishChunker(lang)
    expected = "[I, 'm, going, to, London]"
    assert _s(chunker.tokenize("I'm going to London")) == expected
    assert _s(chunker.tokenize('I’m going to London')) == expected  # different apostrophe char


def _pos_tags_as_string(text, lt):
    out = []
    for atr in lt.get_analyzed_sentence(text).tokens:
        # AnalyzedToken.toString: lemmaOrToken/posTag
        out.append('[' + ', '.join('%s/%s' % (r.token if r.lemma is None else r.lemma, _null(r.pos_tag))
                                   for r in atr.readings) + ']')
    return out


def _chunks_as_string(text, chunker, lt):
    tokens = list(lt.get_analyzed_sentence(text).tokens)
    chunker.add_chunk_tags(tokens)
    return [_chunks(t) for t in tokens]


def test_non_breaking_space(lang):
    """EnglishChunkerTest.testNonBreakingSpace"""
    expected_tags = ('[[/SENT_START], [away/JJ, away/NN, away/RB, away/RP, away/UH], [from/IN, from/RP], '
                     '[home/NN:UN], [often/RB], [?/SENT_END, ?/PCT]]')
    expected_chunks = '[[], [B-ADVP], [], [B-PP], [], [B-NP-singular, E-NP-singular], [], [B-ADVP], [O]]'
    chunker = EnglishChunker(lang)
    lt = JLanguageTool(lang)
    for text in ('Away from home often?', 'Away from home\u00A0often?'):
        tags = '[' + ', '.join(_pos_tags_as_string(text, lt)) + ']'
        assert re.sub(r'\[./null\], ', '', tags) == expected_tags
        assert '[' + ', '.join(_chunks_as_string(text, chunker, lt)) + ']' == expected_chunks


@pytest.mark.skip(reason='ignored in Java ("active when #2119 is fixed"): EnglishChunkerTest.testZeroWidthNoBreakSpace')
def test_zero_width_no_break_space(lang):
    """EnglishChunkerTest.testZeroWidthNoBreakSpace"""
    expected = '[[], [B-NP-singular], [], [I-NP-singular], [], [E-NP-singular]]'
    chunker = EnglishChunker(lang)
    lt = JLanguageTool(lang)
    assert '[' + ', '.join(_chunks_as_string('The long-term stability', chunker, lt)) + ']' == expected
    res2 = _chunks_as_string('The\u200b \u200blong-term\u200b \u200bstability\u200b', chunker, lt)
    assert '[' + ', '.join(res2) + ']' == expected


def test_zero_width_no_break_space_tokens(lang):
    """EnglishChunker.cleanZeroWidthWhitespaces: tokens with U+FEFF are kept
    (an empty token for each empty part), a token of only U+FEFF is
    removed"""
    clean = EnglishChunker._clean_zero_width_whitespaces
    assert clean(['a\ufeffb', '\ufeff', 'c']) == ['a\ufeffb', 'a\ufeffb', 'c']
    assert clean(['\ufeffa']) == ['', '\ufeffa']


# --- EnglishChunkFilterTest ---

def _make_tokens(tokens_as_string):
    result = []
    for tok in tokens_as_string.split(' '):
        parts = tok.split('/')
        if len(parts) != 2:
            raise ValueError("Invalid token, form 'x/y' required: " + tok)
        result.append(ChunkTaggedToken(parts[0], [ChunkTag(parts[1])], None))
    return result


def _assert_chunks(tokens, expected):
    result = EnglishChunkFilter().filter(tokens)
    assert ' '.join(str(t) for t in result) == expected


def test_chunk_filter_singular():
    """EnglishChunkFilterTest.testSingular"""
    _assert_chunks(_make_tokens('He/B-NP owns/B-VP a/B-NP nice/I-NP house/I-NP in/X Berlin/B-NP ./.'),
                   'He/B-NP-singular,E-NP-singular owns/B-VP a/B-NP-singular nice/I-NP-singular '
                   'house/E-NP-singular in/X Berlin/B-NP-singular,E-NP-singular ./.')


@pytest.mark.skip(reason='ignored in Java ("fails..."): EnglishChunkFilterTest.testPluralByAnd')
def test_chunk_filter_plural_by_and():
    """EnglishChunkFilterTest.testPluralByAnd"""
    _assert_chunks(_make_tokens('He/B-NP owns/B-VP a/B-NP large/I-NP house/I-NP and/I-NP a/I-NP ship/I-NP in/X '
                                'Berlin/B-NP ./.'),
                   'He/B-NP-singular owns/B-VP a/B-NP-plural large/I-NP-plural house/I-NP-plural and/I-NP-plural '
                   'a/I-NP-plural ship/I-NP-plural in/X Berlin/B-NP-singular ./.')


def test_chunk_filter_plural_by_plural_noun():
    """EnglishChunkFilterTest.testPluralByPluralNoun"""
    tokens = _make_tokens('I/X have/N-VP ten/B-NP books/I-NP ./.')
    del tokens[3]  # 'books'
    readings = AnalyzedTokenReadings([AnalyzedToken('books', 'NNS', 'book'), AnalyzedToken('books', 'VBZ', 'book')],
                                     0)
    tokens.insert(3, ChunkTaggedToken('books', [ChunkTag('I-NP')], readings))
    _assert_chunks(tokens, 'I/X have/N-VP ten/B-NP-plural books/E-NP-plural ./.')
