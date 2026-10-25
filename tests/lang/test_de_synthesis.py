"""Port of org.languagetool.synthesis.GermanSynthesizerTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.lang.de.synthesis import GermanSynthesizer, get_german_synthesizer


@pytest.fixture(autouse=True, scope='module')
def _dicts():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def synthesizer():
    return get_german_synthesizer()


def _dummy_token(token_str):
    return AnalyzedToken(token_str, token_str, token_str)


def synth(synthesizer, word, pos_tag, reg_ex=False):
    # Arrays.toString(synthesizer.synthesize(dummyToken(word), posTag[, regEx]))
    return '[' + ', '.join(synthesizer.synthesize(_dummy_token(word), pos_tag, reg_ex)) + ']'


def test_synthesize(synthesizer):
    """GermanSynthesizerTest.testSynthesize"""
    assert synth(synthesizer, '123', '_spell_number_') == '[einhundertdreiundzwanzig]'
    assert synth(synthesizer, 'Zug', 'SUB:DAT:SIN:MAS') == '[Zug]'
    assert synth(synthesizer, 'Tisch', 'SUB:DAT:SIN:MAS') == '[Tisch]'
    assert synth(synthesizer, 'Buschfeuer', 'SUB:GEN:SIN:NEU') == '[Buschfeuers]'
    assert synth(synthesizer, 'Äußerung', 'SUB:NOM:PLU:FEM') == '[Äußerungen]'
    assert synth(synthesizer, 'Äußerung', 'SUB:NOM:PLU:MAS') == '[]'
    assert synth(synthesizer, 'Haus', 'SUB:AKK:PLU:NEU') == '[Häuser]'
    assert synth(synthesizer, 'Diabetes-Zentrum', 'SUB:GEN:SIN.*', True) == '[Diabetes-Zentrums]'
    assert synth(synthesizer, 'Diabetes-Zentrum', 'SUB:GEN:PLU.*', True) == '[Diabetes-Zentren]'
    assert synth(synthesizer, 'Xxxxxx-Zentrum', 'SUB:GEN:PLU.*', True) == '[Xxxxxx-Zentren]'
    assert synth(synthesizer, 'Xxxxxx-zentrum', 'SUB:GEN:PLU.*', True) == '[Xxxxxx-zentren]'
    assert synth(synthesizer, 'gelb-grün', 'ADJ.*', True) == '[]'  # should this also work?
    assert synth(synthesizer, 'WLAN-LAN-Kabel', 'SUB:GEN:SIN.*', True) == '[WLAN-LAN-Kabels]'
    assert synth(synthesizer, 'Haus', '.*', True) == '[Häuser, Haus, Häusern, Haus, Hause, Häuser, Hauses, Häuser, Haus]'
    # could happen with soft hyphen in the input
    assert len(synthesizer.synthesize(AnalyzedToken('fake', 'FAKE', None), 'FAKE', False)) == 0


def test_synthesize_compounds(synthesizer):
    """GermanSynthesizerTest.testSynthesizeCompounds"""
    assert synth(synthesizer, 'Regelsystem', 'SUB:NOM:PLU:NEU') == '[Regelsysteme]'
    assert synth(synthesizer, 'Regelsystem', 'SUB:DAT:PLU:NEU') == '[Regelsystemen]'
    assert synth(synthesizer, 'Regelsystem', '.*:PLU:.*', True) == '[Regelsysteme, Regelsystemen]'
    assert synth(synthesizer, 'Regel-System', '.*:PLU:.*', True) == '[Regelsysteme, Regelsystemen]'
    assert synth(synthesizer, 'Kühlschrankversuch', '.*:PLU:.*', True) == '[Kühlschrankversuche, Kühlschrankversuchen]'
    assert synth(synthesizer, 'Kühlschrank-Versuch', '.*:PLU:.*', True) == \
        '[Kühlschrankversuche, Kühlschrankversuchen]'


def test_morfologik_bug(synthesizer):
    """GermanSynthesizerTest.testMorfologikBug"""
    # see https://github.com/languagetool-org/languagetool/issues/586
    assert synth(synthesizer, 'anfragen', 'VER:1:PLU:KJ1:SFT:NEB') == '[anfragen]'


def test_case_and_removed_forms(synthesizer):
    """GermanSynthesizer.lookup: no lowercase forms for uppercase lemmas
    and vice versa (except "mein"/"ich"), REMOVE forms are filtered"""
    assert 'unsre' not in synthesizer.synthesize(AnalyzedToken('unser', None, 'unser'), 'PRO:POS:.*', True)
    forms = synthesizer.synthesize_for_pos_tags('wissen', lambda t: t.startswith('VER:'))
    assert forms == synthesizer.synthesize_for_tag_list(
        'wissen', [t for t in synthesizer.get_possible_tags() if t.startswith('VER:')])


def test_instance():
    """German.createDefaultSynthesizer() returns GermanSynthesizer.INSTANCE"""
    assert isinstance(get_language('de-DE').synthesizer, GermanSynthesizer)
    assert get_language('de-AT').synthesizer is get_german_synthesizer()
