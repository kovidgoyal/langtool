"""Tests for the morfologik dictionary reader langtool.fsa.Dictionary: the
small test dictionary of languagetool-core (tests/data/test.dict) and real
dictionaries of several languages (covering the FSA5, CFSA and CFSA2
automaton formats and the SUFFIX and PREFIX encoders). The pure Python
lookup (Dictionary._raw_lookup) and the C one (Dictionary._native.lookup)
must agree."""

import itertools
import os

import pytest

from conftest import DATA, require_dictionaries
from langtool.fsa import Dictionary, _CFSA, _CFSA2, _FSA5

TEST_DICT = os.path.join(DATA, 'test.dict')

# (language code, dictionary, automaton class, encoder)
REAL_DICTS = [
    ('pl', 'pl/polish.dict', _CFSA2, 'PREFIX'),
    ('pl', 'pl/polish_synth.dict', _CFSA2, 'PREFIX'),
    ('en', 'en/english.dict', _CFSA2, 'SUFFIX'),
    ('de', 'de/german.dict', _CFSA2, 'SUFFIX'),
    ('it', 'it/italian.dict', _FSA5, 'SUFFIX'),
    ('da', 'da/danish.dict', _FSA5, 'SUFFIX'),
    ('ast', 'ast/asturian.dict', _CFSA, 'SUFFIX'),
]

N_ENTRIES = 20000  # entries checked from the start of the dictionary
PER_FIRST_BYTE = 300  # entries checked below each arc of the root node


def _norm(raw):
    return [(bytes(s), None if t is None else bytes(t)) for s, t in raw]


def _load(lang, name):
    require_dictionaries(lang)
    from langtool.dictionaries import locate
    return Dictionary(locate(name))


def _native(d):
    if d._native is None:
        pytest.skip('C extension _speedups not available')
    return d._native


def _assert_same(d, word_bytes):
    py = _norm(d._raw_lookup(word_bytes))
    c = _norm(_native(d).lookup(word_bytes))
    assert py == c, 'lookup of %r differs: python=%r native=%r' % (word_bytes, py, c)
    return py


def _words_below_root(d, per_label):
    """Words of the entries reachable below each arc of the root node (to
    cover the whole dictionary, not just its first entries)."""
    fsa = d.fsa
    sep = d.metadata.separator
    arc = fsa.first_arc(fsa.root)
    while arc != 0:
        label = fsa.label(arc)
        dest = fsa.destination(arc)
        if dest != 0 and label != sep:
            for seq in itertools.islice(d._sequences(dest), per_label):
                full = bytes((label,)) + seq
                i = full.find(bytes((sep,)))
                if i > 0:
                    yield full[:i]
        arc = fsa.next_arc(arc)


# --- tests/data/test.dict ---

def test_test_dict_metadata():
    d = Dictionary(TEST_DICT)
    assert d.metadata.separator == ord('+')
    assert d.metadata.encoder == 'SUFFIX'
    assert d.metadata.encoding.lower() == 'utf-8'


def test_test_dict_lookup():
    d = Dictionary(TEST_DICT)
    assert list(d.lookup('lowercase')) == [('lclemma', 'POS1'), ('lclemma2', 'POS1a')]
    assert list(d.lookup('schön')) == [('testlemma', 'POSTEST')]
    assert list(d.lookup('Mixedcase')) == [('mixedlemma', 'POS2')]
    assert list(d.lookup('UPPERCASE')) == [('upperlema', 'POS3')]
    # lookup is case sensitive
    assert len(d.lookup('Lowercase')) == 0
    assert len(d.lookup('mixedcase')) == 0
    assert len(d.lookup('uppercase')) == 0
    for w in ('noSuchWord', '', 'lower', 'lowercasex', 'schon', 'sch', 'l', '+', 'lowercase+', 'low+case'):
        assert len(d.lookup(w)) == 0, w


def test_test_dict_iter_all():
    d = Dictionary(TEST_DICT)
    assert sorted(d.iter_all()) == sorted([
        ('Mixedcase', 'mixedlemma', 'POS2'),
        ('UPPERCASE', 'upperlema', 'POS3'),
        ('lowercase', 'lclemma', 'POS1'),
        ('lowercase', 'lclemma2', 'POS1a'),
        ('schön', 'testlemma', 'POSTEST'),
    ])


def test_test_dict_native_agrees():
    d = Dictionary(TEST_DICT)
    words = [w for w, _, _ in d.iter_all()]
    words += ['noSuchWord', 'lower', 'lowercasex', 'Lowercase', 'sch', 'schö', 'schönn', 'l', 'U', 'M']
    for w in words:
        _assert_same(d, w.encode('utf-8'))
    for w, lemma, tag in d.iter_all():
        assert (lemma, tag) in d.lookup(w)


# --- real dictionaries ---

@pytest.mark.parametrize('lang,name,fsa_class,encoder', REAL_DICTS, ids=[r[1] for r in REAL_DICTS])
def test_real_dict_format(lang, name, fsa_class, encoder):
    d = _load(lang, name)
    assert isinstance(d.fsa, fsa_class)
    assert d.metadata.encoder == encoder


@pytest.mark.parametrize('lang,name,fsa_class,encoder', REAL_DICTS, ids=[r[1] for r in REAL_DICTS])
def test_real_dict_native_agrees_with_python(lang, name, fsa_class, encoder):
    d = _load(lang, name)
    enc = d.metadata.encoding
    sep = chr(d.metadata.separator)
    entries = list(itertools.islice(d.iter_all(), N_ENTRIES))
    assert len(entries) > 1000
    by_word = {}
    for w, lemma, tag in entries:
        by_word.setdefault(w, []).append((lemma, tag))
    checked = 0
    for w, expected in by_word.items():
        if sep in w:
            continue
        wb = w.encode(enc)
        raw = _assert_same(d, wb)
        assert raw, 'no result for %r' % w
        # the entries found by iterating must be found by the lookup
        result = d.lookup(w)
        for e in expected:
            assert e in result, '%r: %r not in %r' % (w, e, result)
        # some non-words derived from the word
        for variant in (wb[:-1], wb + b'x', wb + bytes((d.metadata.separator,)), w.swapcase().encode(enc)):
            _assert_same(d, variant)
        checked += 1
    assert checked > 500
    # entries spread over the whole dictionary
    n = 0
    for wb in _words_below_root(d, PER_FIRST_BYTE):
        assert _assert_same(d, wb), 'no result for %r' % wb
        _assert_same(d, wb + b'q')
        n += 1
    assert n > 1000


def test_real_dict_lookups():
    d = _load('pl', 'pl/polish.dict')
    assert ('kot', 'subst:sg:nom:m1+subst:sg:nom:m2') in d.lookup('kot')
    assert ('dom', 'subst:sg:gen:m3+subst:sg:loc:m3+subst:sg:voc:m3') in d.lookup('domu')
    assert len(d.lookup('kotxyz')) == 0
    d = _load('en', 'en/english.dict')
    assert list(d.lookup('houses')) == [('house', 'NNS'), ('house', 'VBZ')]
    assert list(d.lookup('went')) == [('go', 'VBD')]
    assert len(d.lookup('Houses')) == 0
    d = _load('de', 'de/german.dict')
    assert ('Haus', 'SUB:NOM:PLU:NEU') in d.lookup('Häuser')
