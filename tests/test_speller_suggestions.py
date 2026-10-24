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
