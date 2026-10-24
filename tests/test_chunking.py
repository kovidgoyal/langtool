"""Tests of langtool.chunking (ChunkTaggedToken, TokenPredicate,
TokenExpressionFactory; TokenPredicateTest is a port of
org.languagetool.chunking.TokenPredicateTest of language-de) and of the
post-disambiguation chunker (Language.getPostDisambiguationChunker(), run by
JLanguageTool.getAnalyzedSentence)."""

import pytest

from conftest import DATA
from langtool import extensions
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.chunking import ChunkTag, ChunkTaggedToken, TokenExpressionFactory, TokenPredicate
from langtool.languages import V, register_language
from langtool.openregex import RegularExpression


def _token():
    chunk_tags = [ChunkTag('CHUNK1'), ChunkTag('CHUNK2')]
    readings = AnalyzedTokenReadings(AnalyzedToken('mytoken', 'MYPOS', 'mylemma'), 0)
    return ChunkTaggedToken('mytoken', chunk_tags, readings)


def test_token_predicate():
    """TokenPredicateTest.test"""
    t = _token()

    def matches(expr):
        return TokenPredicate(expr, False).apply(t)

    assert matches('mytoken')
    assert not matches('mytoken2')
    assert matches('string=mytoken')
    assert not matches('string=mytoken2')
    assert matches('regex=my[abct]oken')
    assert not matches('regex=my[abc]oken')
    assert matches('chunk=CHUNK1')
    assert matches('chunk=CHUNK2')
    assert not matches('chunk=OTHERCHUNK')
    assert matches('pos=MYPOS')
    assert not matches('pos=OTHER')
    assert matches('posre=M.POS')
    assert not matches('posre=O.HER')
    with pytest.raises(ValueError):
        matches('invalid=token')


def test_token_predicate_case_and_quotes():
    t = _token()
    # word tokens and regular expressions are compared case-insensitively unless case_sensitive is set,
    # regexCS is always case-sensitive
    assert TokenPredicate('MyToken', False).apply(t)
    assert not TokenPredicate('MyToken', True).apply(t)
    assert TokenPredicate('regex=MY.*', False).apply(t)
    assert not TokenPredicate('regexCS=MY.*', False).apply(t)
    # values may be quoted with single quotes
    assert TokenPredicate("posre='M.P(O|X)S'", False).apply(t)
    assert TokenPredicate("posregex='MYPOS'", False).apply(t)
    # without readings, POS predicates don't match
    assert not TokenPredicate('pos=MYPOS', False).apply(ChunkTaggedToken('x', [], None))
    with pytest.raises(ValueError):
        TokenPredicate('a=b=c', False)
    assert str(_token()) == 'mytoken/CHUNK1,CHUNK2'


def _tokens(*specs):
    out = []
    for i, (word, pos) in enumerate(specs):
        out.append(ChunkTaggedToken(word, [ChunkTag('O')], AnalyzedTokenReadings(AnalyzedToken(word, pos, word), i)))
    return out


def test_token_expression_factory():
    """Logic expressions of token predicates in OpenRegex expressions"""
    factory = TokenExpressionFactory(False)
    tokens = _tokens(('Der', 'ART'), ('alte', 'ADJ:x'), ('Mann', 'SUB:NOM'), ('und', 'KON'), ('Hund', 'SUB:AKK'))
    r = RegularExpression.compile("<pos=ART> <posre='ADJ:.*' & !pos=SUB>* <posre='SUB:(NOM|AKK)'>", factory.create)
    assert [(m.start_index(), m.end_index()) for m in r.find_all(tokens)] == [(0, 3)]
    r = RegularExpression.compile("<posre='SUB:.*' & (string=hund | string=katze)>", factory.create)
    assert [(m.start_index(), m.end_index()) for m in r.find_all(tokens)] == [(4, 5)]
    r = RegularExpression.compile('<!pos=SUB & !pos=KON>+', factory.create)
    assert [(m.start_index(), m.end_index()) for m in r.find_all(tokens)] == [(0, 2)]
    r = RegularExpression.compile('<chunk=O> <und>', factory.create)
    assert [(m.start_index(), m.end_index()) for m in r.find_all(tokens)] == [(2, 4)]


class _RecordingChunker:
    """Adds the chunk tag "POST" to tokens whose (disambiguated) reading has
    the POS tag "SENT_END"."""

    def __init__(self):
        self.calls = []

    def add_chunk_tags(self, token_readings):
        self.calls.append([t.token for t in token_readings])
        for t in token_readings:
            if t.has_pos_tag('SENT_END'):
                t.set_chunk_tags([ChunkTag('POST')])


_CHUNKER = _RecordingChunker()


def test_post_disambiguation_chunker():
    from langtool.api import get_language
    from langtool.tool import JLanguageTool
    # (registered here, not at import time, so that the test language is not seen by
    # test_language_rules.py)
    extensions.register('chunker', 'RecordingChunker', lambda lang: _CHUNKER, language='xy')
    register_language('xy', dict(name='Testlanguage with a post-disambiguation chunker', countries=['XY'],
                                 variants=[V('xy-XY')], data_dir=DATA, tagger=None, rules=[],
                                 post_disambiguation_chunker='RecordingChunker'))
    lang = get_language('xy')
    assert lang.post_disambiguation_chunker is _CHUNKER
    assert lang.chunker is None
    lt = JLanguageTool(lang)
    sentence = lt.get_analyzed_sentence('A test.')
    # the chunker gets all tokens of the analyzed sentence (with the sentence end set)
    assert _CHUNKER.calls[-1] == ['', 'A', ' ', 'test', '.']
    assert [str(c) for c in sentence.tokens[-1].chunk_tags] == ['POST']
    # the raw analysis is not chunked
    n = len(_CHUNKER.calls)
    raw = lt.get_raw_analyzed_sentence('A test.')
    assert len(_CHUNKER.calls) == n
    assert not raw.tokens[-1].chunk_tags
    # languages without a post-disambiguation chunker
    assert get_language('xx').post_disambiguation_chunker is None
