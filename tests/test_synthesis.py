"""Port of org.languagetool.synthesis.ManualSynthesizerTest."""

import pytest

from langtool.synthesis import ManualSynthesizer

DATA = (
    '# some test data\n'
    'InflectedForm11\tLemma1\tPOS1\n'
    'InflectedForm121\tLemma1\tPOS2\n'
    'InflectedForm122\tLemma1\tPOS2\n'
    'InflectedForm2\tLemma2\tPOS1\n'
)


@pytest.fixture
def synthesizer(tmp_path):
    p = tmp_path / 'manual.txt'
    p.write_text(DATA, encoding='utf-8')
    return ManualSynthesizer([str(p)])


def _str(l):
    # String.valueOf(List<String>)
    return 'null' if l is None else '[' + ', '.join(l) + ']'


def test_lookup_non_existing(synthesizer):
    assert synthesizer.lookup('', '') is None
    assert synthesizer.lookup('', None) is None
    assert synthesizer.lookup(None, '') is None
    assert synthesizer.lookup(None, None) is None
    assert synthesizer.lookup('NONE', 'UNKNOWN') is None


def test_invalid_lookup(synthesizer):
    assert synthesizer.lookup('NONE', 'POS1') is None
    assert synthesizer.lookup('Lemma1', 'UNKNOWN') is None
    assert synthesizer.lookup('Lemma1', 'POS.') is None  # no reg exp
    assert synthesizer.lookup('Lemma2', 'POS2') is None


def test_valid_lookup(synthesizer):
    assert _str(synthesizer.lookup('Lemma1', 'POS1')) == '[InflectedForm11]'
    assert _str(synthesizer.lookup('Lemma1', 'POS2')) == '[InflectedForm121, InflectedForm122]'
    assert _str(synthesizer.lookup('Lemma2', 'POS1')) == '[InflectedForm2]'


def test_case_sensitive(synthesizer):
    # lookup is case sensitive:
    assert synthesizer.lookup('LEmma1', 'POS1') is None


def test_possible_tags(synthesizer):
    # ManualSynthesizer.getPossibleTags()
    assert set(synthesizer.possible_tags) == {'POS1', 'POS2'}
