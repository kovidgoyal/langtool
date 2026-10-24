"""Port of org.languagetool.synthesis.uk.UkrainianSynthesizerTest."""

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.lang.uk.synthesis import UkrainianSynthesizer


def _dummy_token(token_str):
    return AnalyzedToken(token_str, token_str, token_str)


def test_synthesize_string():
    """UkrainianSynthesizerTest.testSynthesizeString"""
    require_dictionaries('uk')
    synth = get_language('uk').synthesizer
    assert isinstance(synth, UkrainianSynthesizer)

    assert len(synth.synthesize(_dummy_token('щосьтамтаке'), 'щосьтамтаке')) == 0

    assert synth.synthesize(_dummy_token('місто'), 'noun:inanim:n:v_rod') == ['міста']

    # with regular expressions
    assert sorted(synth.synthesize(_dummy_token('червоний'), 'adj:f:v_rod.*', True)) == ['червоної']
    assert sorted(synth.synthesize(_dummy_token('червоний'), 'adj:f:v_rod:compb', True)) == ['червоної']
    assert sorted(synth.synthesize(_dummy_token('червоний'), 'adj:.:v_oru:compb', True)) == [
        'червоним', 'червоним', 'червоними', 'червоною']
