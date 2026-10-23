"""Tests of langtool.soros (port of org.languagetool.synthesis.Soros, which
has no Java unit test). The expected values were produced with
LanguageTool 6.6 (synthesizing with the _spell_number_ POS tags)."""

import os

import pytest

from langtool.analysis import AnalyzedToken
from langtool.language import RESOURCE_DIR
from langtool.soros import Soros, load_soros
from langtool.synthesis import BaseSynthesizer


def _sor(code):
    return os.path.join(RESOURCE_DIR, code, code + '.sor')


@pytest.mark.parametrize('number, expected', [
    ('0', 'noll'), ('7', 'sju'), ('21', 'tjugoett'), ('100', 'hundranollte'), ('101', 'hundraett'),
    ('123', 'hundratjugotre'), ('1000', 'tusen nollte'), ('1999', 'nittonhundranittionio'),
    ('2024', 'tvåtusen tjugofyra'), ('12345', 'tolvtusen trehundrafyrtiofem'), ('1000000', 'ett miljon nollte'),
    ('1234567890123', 'ett biljon tvåhundratrettiofyra miljard femhundrasextiosju miljon '
                      'åttahundranittionolltetusen hundratjugotre'),
])
def test_swedish(number, expected):
    assert load_soros(_sor('sv'), 'sv').run(number) == expected


@pytest.mark.parametrize('code, number, expected', [
    ('en', '21', 'twenty-one'), ('en', '2024', 'two thousand and twenty-four'),
    ('en', '123456', 'one hundred twenty-three thousand, four hundred fifty-six'),
    ('de', '21', 'einundzwanzig'), ('de', '2024', 'zweitausendvierundzwanzig'),
    ('de', '123456', 'einhundertdreiundzwanzigtausendvierhundertsechsundfünfzig'),
])
def test_other_languages(code, number, expected):
    assert load_soros(_sor(code), code).run(number) == expected


@pytest.mark.parametrize('number, expected', [
    ('0', ''), ('7', 'VII'), ('21', 'XXI'), ('1999', 'MCMXCIX'), ('2024', 'MMXXIV'),
    ('12345', 'X̅I̅I̅CCCXLV'), ('1000000', 'M̅'), ('1234567890123', '1234567890123'),
])
def test_roman(number, expected):
    assert load_soros(os.path.join(RESOURCE_DIR, 'Roman.sor'), 'Roman').run(number) == expected


def test_simple_program():
    # no match: empty string; function calls $(...) and the left zero deletion
    s = Soros('1 one\n2 two\n(\\d)(\\d) $1-$2\n', 'xx')
    assert s.run('1') == 'one'
    assert s.run('12') == 'one-two'
    assert s.run('012') == 'one-two'
    assert s.run('3') == ''


def test_missing_file():
    # BaseSynthesizer.createNumberSpeller returns null on any exception
    assert load_soros(os.path.join(RESOURCE_DIR, 'xx', 'missing.sor'), 'xx') is None


def test_synthesizer_spell_number():
    s = load_soros(_sor('sv'), 'sv')
    synth = BaseSynthesizer(None, None, 'sv', number_speller=s)
    assert synth.synthesize(AnalyzedToken('21', None, None), '_spell_number_') == ['tjugoett']
    # without number speller the number is returned unchanged
    synth = BaseSynthesizer(None, None, 'sv')
    assert synth.synthesize(AnalyzedToken('21', None, None), '_spell_number_') == ['21']
