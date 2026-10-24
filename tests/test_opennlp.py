"""Tests of langtool.opennlp, the port of the OpenNLP inference code (model
reading, GIS model evaluation, beam search, TokenizerME, POSTaggerME and
ChunkerME). The expected values are the output of opennlp-tools 1.9.5 (its
command line tools TokenizerME, POSTagger and ChunkerME) for the English
OpenNLP 1.5 models used by LanguageTool's EnglishChunker."""

import struct

import pytest

from conftest import require_dictionaries
from langtool import opennlp
from langtool.opennlp import (BeamSearch, ChunkerME, GISModel, POSTaggerME, TokenizerME, _JavaPriorityQueue,
                              java_length, java_string, load_package, read_gis_model, sequence_outcomes,
                              token_context)


def _model(name):
    require_dictionaries('en')
    from langtool.api import get_language
    from langtool.dictionaries import locate
    lang = get_language('en')
    return load_package(locate('en/' + name, lang.dictionary_path, lang.download_dictionaries))


@pytest.fixture(scope='module')
def tokenizer():
    return TokenizerME(_model('en-token.bin'))


@pytest.fixture(scope='module')
def tagger():
    return POSTaggerME(_model('en-pos-maxent.bin'))


@pytest.fixture(scope='module')
def chunker():
    return ChunkerME(_model('en-chunker.bin'))


# (sentence, tokens, POS tags, chunk tags) as computed by opennlp-tools 1.9.5
_EXPECTED = [
    ("I'll test it, Mr. Smith's dogs aren't here.",
     "I 'll test it , Mr. Smith 's dogs are n't here .",
     'PRP MD VB PRP , NNP NNP POS NNS VBP RB RB .',
     'B-NP B-VP I-VP B-NP O B-NP I-NP B-NP I-NP B-VP O B-ADVP O'),
    ('The U.S.A. said "no" (twice) -- e.g. at 5:30 p.m.',
     'The U.S.A. said "no " ( twice ) -- e.g . at 5:30 p.m.',
     'DT NNP VBD RB `` -LRB- RB -RRB- : JJ . IN CD NN',
     'B-NP I-NP B-VP O O B-NP I-NP I-NP O B-ADJP O B-PP B-NP I-NP'),
    ('A short test of the bicycle is needed',
     'A short test of the bicycle is needed',
     'DT JJ NN IN DT NN VBZ VBN',
     'B-NP I-NP I-NP B-PP B-NP I-NP B-VP I-VP'),
]


@pytest.mark.parametrize('sentence,tokens,tags,chunks', _EXPECTED)
def test_pipeline(tokenizer, tagger, chunker, sentence, tokens, tags, chunks):
    toks = tokenizer.tokenize(sentence)
    assert ' '.join(toks) == tokens
    pos = tagger.tag(toks)
    assert ' '.join(pos) == tags
    assert ' '.join(chunker.chunk(toks, pos)) == chunks


def test_tokenize_pos(tokenizer):
    assert tokenizer.tokenize_pos("Don't  go.") == [(0, 2), (2, 5), (7, 9), (9, 10)]
    # alphanumeric tokens and single characters are not split
    assert tokenizer.tokenize('abc123 x') == ['abc123', 'x']
    assert tokenizer.tokenize('') == []
    # the non-breaking space is whitespace for OpenNLP (StringUtil.isWhitespace)
    assert tokenizer.tokenize('a\u00a0b') == ['a', 'b']


def test_java_strings(tokenizer):
    # strings are processed as UTF-16 code units, like in Java
    s = java_string('a😀b')
    assert len(s) == 4 and java_length('a😀b') == 4
    assert java_string('abc') == 'abc'
    assert tokenizer.tokenize(java_string('x 😀')) == ['x', '\ud83d', '\ude00']


def test_token_context():
    """DefaultTokenContextGenerator.getContext"""
    assert token_context('ab.', 2) == ['p=ab', 's=.', 'p1=b', 'p1_alpha', 'p2=a', 'p2_alpha', 'p21=ab', 'p1f1=b.',
                                       'f1=.', 'f1_eos', 'f2=bok']
    assert token_context('&x;', 1) == ['p=&', 's=x;', 'p1=&', 'p2=bok', 'p1f1=&x', 'f1=x', 'f1_alpha', 'f2=;',
                                       'f12=x;', 'cc']


def _write_utf(s):
    b = s.encode('utf-8', 'surrogatepass').replace(b'\x00', b'\xc0\x80')
    return struct.pack('>H', len(b)) + b


def test_read_gis_model():
    """GenericModelReader with a GIS model: outcomes, outcome patterns,
    predicates (in modified UTF-8) and parameters"""
    data = (_write_utf('GIS') + struct.pack('>i', 1) + struct.pack('>d', 0.0) + struct.pack('>i', 2)
            + _write_utf('T') + _write_utf('F') + struct.pack('>i', 2) + _write_utf('1 0') + _write_utf('1 0 1')
            + struct.pack('>i', 2) + _write_utf('p=\x00') + _write_utf('q=😀')
            + struct.pack('>d', 1.5) + struct.pack('>2d', -1.0, 2.0))
    model = read_gis_model(data)
    assert model.outcome_names == ['T', 'F']
    assert model.pmap == {'p=\x00': ((0,), (1.5,)), 'q=😀': ((0, 1), (-1.0, 2.0))}
    probs = model.eval(['p=\x00', 'unknown', 'q=😀'])
    # log(1/2) + 1.5 - 1.0 and log(1/2) + 2.0
    import math
    e0, e1 = math.exp(math.log(0.5) + 0.5), math.exp(math.log(0.5) + 2.0)
    assert probs == [e0 / (e0 + e1), e1 / (e0 + e1)]
    assert model.get_best_outcome(probs) == 'F'
    assert model.get_best_outcome([0.5, 0.5]) == 'T'  # the first maximum
    assert model.get_index('F') == 1 and model.get_index('X') == -1


def test_java_priority_queue():
    """java.util.PriorityQueue keeps Java's order of equal elements (heap
    sift up/down)"""
    q = _JavaPriorityQueue()
    for i, score in enumerate((-1.0, -2.0, -1.0, -0.5, -1.0, -2.0)):
        q.add((score, i, None, None))
    out = [q.remove()[1] for _ in range(len(q))]
    assert out == [3, 0, 4, 2, 1, 5]


def test_beam_search():
    """BeamSearch.bestSequences with a model that prefers 'b' after 'a'"""
    model = GISModel(['a', 'b'], {'start': ((0,), (1.0,)), 'after=a': ((1,), (2.0,))})
    beam = BeamSearch(2, model)

    def evaluate(i, seq):
        return model.eval(['start'] if seq[1] is None else ['after=' + seq[1]])
    best = beam.best_sequences(2, 3, evaluate, lambda i, seq: None)
    assert [sequence_outcomes(s) for s in best] == [['a', 'b', 'a'], ['a', 'b', 'b']]
    # only the valid outcomes (here: 'b')
    best = beam.best_sequence(2, evaluate, lambda i, seq: [1])
    assert sequence_outcomes(best) == ['b', 'b']
    # (no parameters for 'after=b': uniform probabilities)
    assert opennlp.sequence_probs(best) == [model.eval(['start'])[1], 0.5]


def test_beam_search_ties():
    """With equal scores the result depends on java.util.PriorityQueue:
    after a, b, c (equal) are added, a and then c are removed; of the 6
    equal extensions of a and c, aa and then cc are removed"""
    model = GISModel(['a', 'b', 'c'], {})
    beam = BeamSearch(2, model)
    best = beam.best_sequences(2, 2, lambda i, seq: model.eval([]), lambda i, seq: None)
    assert [sequence_outcomes(s) for s in best] == [['a', 'a'], ['c', 'c']]


def test_gis_eval_speedups():
    """The C implementation of the evaluation gives the same results as the
    Python one (also for the degenerate sums: exp overflow, all zero)"""
    from langtool._base import speedups
    if speedups is None:
        pytest.skip('the C extension is not available')
    pmap = {'x': ((0, 2), (0.25, -1.5)), 'y': ((1,), (3.0,)), 'big': ((0,), (1000.0,)), 'small': ((0, 1, 2),
                                                                                                (-800.0,) * 3)}
    model = GISModel(['a', 'b', 'c'], pmap)
    prior = [model.r] * 3
    for context in (['x'], ['y', 'x', 'unknown', 'x'], []):
        expected = model.normalize(prior[:] if not context else _py_sum(model, prior, context))
        assert speedups.gis_eval(prior, pmap, context) == expected
        assert speedups.gis_sum(prior, pmap, context) == _py_sum(model, prior, context)
    assert speedups.gis_eval(prior, pmap, ['big']) is None
    assert speedups.gis_eval(prior, pmap, ['small']) is None
    probs = model.eval(['big'])
    assert probs[0] != probs[0] and probs[1:] == [0.0, 0.0]  # Java: Infinity / Infinity, 1 / Infinity
    assert all(p != p for p in model.eval(['small']))  # Java: 0.0 / 0.0


def _py_sum(model, prior, context):
    p = list(prior)
    model.sum_features(p, context)
    return p
