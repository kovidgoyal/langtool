"""Tests of the port of the suggestion search of morfologik's Speller
(findReplacements/findSimilarWords, with HMatrix and the replacement pairs
of the dictionary metadata) and LanguageTool's MorfologikSpeller wrapper
(langtool.spelling). The expected suggestions for the Spanish dictionary
(es/es-ES.dict of spanish-pos-dict 2.5) were obtained with morfologik's
Speller in Java."""

import pytest

from conftest import require_dictionaries
from langtool.spelling import HMatrix, Speller, morfologik_suggestion_speller, parse_equivalent_chars, \
    parse_replacement_pairs


def test_hmatrix():
    """HMatrix: H(i, j) = |i - j| at the borders, distance + 1 outside the band"""
    h = HMatrix(1, 10)
    assert h.get(0, 0) == 0
    assert h.get(0, 1) == 1
    assert h.get(1, 0) == 1
    assert h.get(2, 0) == 2  # distance + 1
    assert h.get(0, 2) == 2
    h.set(3, 3, 1)
    assert h.get(3, 3) == 1
    h.reset()
    assert h.get(3, 3) == 0
    assert h.get(0, 1) == 1


def test_parse_metadata():
    """DictionaryAttribute.REPLACEMENT_PAIRS / EQUIVALENT_CHARS"""
    assert parse_replacement_pairs('ás az, az ás,o ue, o ua, a_b c') == {
        'ás': ['az'], 'az': ['ás'], 'o': ['ue', 'ua'], 'a b': ['c']}
    assert parse_equivalent_chars('b v,v b, b w') == {'b': ['v', 'w'], 'v': ['b']}
    with pytest.raises(ValueError):
        parse_replacement_pairs('abc')
    with pytest.raises(ValueError):
        parse_equivalent_chars('ab c')


@pytest.fixture(scope='module')
def es_speller():
    require_dictionaries('es')
    from langtool.api import get_language
    return morfologik_suggestion_speller(get_language('es'), '/es/es-ES.dict')


# (word, Java's Speller(dictionary, 1).findSimilarWords(word))
_SIMILAR = [
    ('faltes', ['faltas', 'maltés', 'falte', 'faltos', 'falten', 'falles', 'faltéis', 'falté', 'Falces', 'falces',
                'falses', 'faltás', 'fantes', 'fálteos', 'fáltese', 'saltes']),
    ('ahorar', ['ahora', 'ahorrar', 'adorar', 'ahorra', 'ahogar', 'ahorcar', 'añorar', 'aforar', 'ahuecar', 'atorar',
                'ahormar', 'acorar', 'agorar', 'ahuevar', 'ajorar', 'azorar']),
    ('quier', ['quien', 'quiere', 'quién', 'quiera', 'quiero', 'Quer', 'queer']),
    ('encuenta', ['encuentra', 'encuesta', 'encenta', 'encentá', 'encuestá']),
    # replacement pairs (ke -> que, güe -> hue, x -> cc, ll -> y ...)
    ('kiero', ['quiero', 'quiere', 'quiera', 'fiero', 'quieto', 'quiebro', 'hiero', 'yero', 'Siero', 'Quero', 'quero',
               'quijero', 'yuyero']),
    ('güevo', ['huevo', 'huevó', 'nuevo', 'juego', 'hubo', 'huevos', 'hueco', 'hueso', 'gueto', 'suevo', 'hueva',
               'muevo', 'huero', 'guabo', 'güero', 'jubo', 'jumbo', 'Hueva', 'ahuevo', 'ahuevó', 'huelo', 'hueve',
               'huevá', 'huevé', 'huevón']),
    ('acsion', ['acción', 'acciona', 'accione', 'accionó', 'alción', 'acciono', 'accioná', 'accioné', 'ación',
                'ansión', 'arción']),
    ('cceso', ['acceso', 'cesó', 'ceso', 'cheso', 'creso', 'xero']),
    # case conversions
    ('Kilómetro', ['kilómetro', 'kilometro', 'kilometró', 'kilómetros', 'kilometra', 'kilometre', 'kilometrá',
                   'kilometré', 'xilómetro']),
    ('LLAVE', ['llave', 'clave', 'llaves', 'lleve', 'llame', 'llamé', 'llevé', 'lave', 'clavé', 'lavé', 'Clavé',
               'Ilave']),
    # short words
    ('a', ['Å']),
    ('abc', ['ABC', 'ave', 'ABP', 'ABS', 'BBC', 'CBC', 'aC', 'abu']),
]


@pytest.mark.parametrize('word,expected', _SIMILAR)
def test_find_similar_words_es(es_speller, word, expected):
    assert es_speller.find_similar_words(word) == expected


def test_find_replacements_es(es_speller):
    # findReplacements doesn't look for words that are in the dictionary
    assert es_speller.find_replacements('casa') == []
    # findSimilarWords also for correct words (the word itself is excluded)
    assert es_speller.find_similar_words('casa')[:12] == ['casá', 'cada', 'casi', 'caso', 'casas', 'causa', 'pasa',
                                                          'basa', 'caja', 'capa', 'cara', 'casó']
    assert len(es_speller.find_similar_words('casa')) == 75
    assert es_speller.find_replacements('kiero') == es_speller.find_similar_words('kiero')
    assert es_speller.find_replacements('') == []


def test_speller_internals_es(es_speller):
    sp = es_speller.speller
    assert isinstance(sp, Speller)
    assert sp.is_in_dictionary('casa')
    assert not sp.is_in_dictionary('cása')
    assert 0 <= sp.get_frequency('casa') < Speller.FREQ_RANGES
    assert sp.get_frequency('xyzxyz') == 0
    # replacement pairs with targets of more than two characters
    assert sp.get_all_replacements('kiero', 0, 0) == ['kiero', 'quiero']
    assert sp.get_all_replacements('a', 0, 0) == ['a']


# --- the dictionary of the plain text word lists, run-on words, MorfologikSpeller.getSuggestions ---

def _plain_dictionary(lines, info=''):
    from langtool.fsa import DictionaryMetadata, read_properties
    from langtool.spelling import PlainTextDictionary
    md = DictionaryMetadata(read_properties('fsa.dict.separator=+\nfsa.dict.encoding=utf-8\n'
                                            'fsa.dict.encoder=SUFFIX\n' + info))
    return PlainTextDictionary([s.encode('utf-8') for s in lines], md)


def test_plain_text_dictionary():
    """The FSA of the plain text word lists: the words, arcs in label order"""
    d = _plain_dictionary(['cosa', 'casa', 'caso', 'casa', 'a'])
    assert list(d._sequences(d.fsa.root)) == [b'a', b'casa', b'caso', b'cosa']
    s = Speller(d, 1)
    assert s.is_in_dictionary('casa') and s.is_in_dictionary('a') and not s.is_in_dictionary('cas')
    # edit distance 1, in the order of the FSA (no frequencies)
    assert s.find_replacements('cesa') == ['casa', 'cosa']
    assert [c.distance for c in s.find_replacement_candidates('cesa')] == [51, 51]
    assert Speller(d, 2).find_replacements('cesa') == ['casa', 'cosa', 'caso']


def test_run_on_words():
    """Speller.replaceRunOnWordCandidates (runon-words is on by default)"""
    d = _plain_dictionary(['casa', 'grande', 'gran', 'de'])
    s = Speller(d, 1)
    assert [c.word for c in s.replace_run_on_word_candidates('casagrande')] == ['casa grande']
    assert [c.word for c in s.replace_run_on_word_candidates('grande')] == []
    # camel case and uppercase first words
    assert [c.word for c in s.replace_run_on_word_candidates('CasaGrande')] == ['Casa Grande']
    assert [c.word for c in s.replace_run_on_word_candidates('grande')] == []
    s = Speller(_plain_dictionary(['casa', 'grande'], 'fsa.dict.speller.runon-words=false\n'), 1)
    assert s.replace_run_on_word_candidates('casagrande') == []


def test_weighted_speller():
    """MorfologikSpeller.getSuggestions: replacement candidates and run-on
    words with their weights, the case of the word"""
    from langtool.spelling import SuggestionMultiSpeller, _WeightedSpeller
    d = _plain_dictionary(['casa', 'cosa', 'grande', 'Madrid'])
    s = _WeightedSpeller(d, 1)
    assert s.get_suggestions('cesa') == [('casa', 51), ('cosa', 51)]
    assert s.get_suggestions('Cesa') == [('Casa', 51), ('Cosa', 51)]
    assert s.get_suggestions('CESA') == [('CASA', 51), ('COSA', 51)]
    assert s.get_suggestions('casagrande') == [('casa grande', 51)]
    assert s.get_suggestions('Madri') == [('Madrid', 51)]
    # the multi speller: no duplicates, not the word itself, sorted by weight
    m = SuggestionMultiSpeller(d, [b'cesar', b'casa'], 1)
    assert m.get_suggestions('cesa') == ['casa', 'cosa', 'cesar']
    assert m.get_weighted_suggestions_from_default_dicts('cesa') == [('casa', 51), ('cosa', 51), ('cesar', 51)]
