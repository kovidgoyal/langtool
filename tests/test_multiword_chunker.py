"""Port of org.languagetool.tagging.disambiguation.MultiWordChunkerTest."""

import os

import pytest

from conftest import DATA
from langtool import extensions
from langtool.analysis import AnalyzedToken
from langtool.disambiguation import MultiWordChunker, MultiWordChunker2
from langtool.languages import V, register_language
from langtool.tagging import DemoTagger

MULTIWORDS = os.path.join(DATA, 'resource', 'yy', 'multiwords.txt')


class FakePosDemoTagger(DemoTagger):
    """The DemoTagger subclass of the Java test: adds a 'FakePosTag' reading
    to every non-whitespace token."""

    def tag(self, sentence_tokens):
        token_readings = super().tag(sentence_tokens)
        for readings in token_readings:
            if readings.is_whitespace:
                continue
            readings.add_reading(AnalyzedToken(readings.token, 'FakePosTag', readings.token), '')
        return token_readings


@pytest.fixture(scope='module')
def lt():
    # port of the anonymous FakeLanguage subclass (short code yy)
    extensions.register('tagger', 'MultiWordChunkerTestTagger', lambda lang, spec: FakePosDemoTagger())
    register_language('yy', dict(
        name='FakeLanguage', countries=['YY'], variants=[V('yy')], data_dir=DATA,
        tagger=dict(impl='MultiWordChunkerTestTagger'), disambiguator=[], rules=[],
    ))
    from langtool.api import get_language
    from langtool.tool import JLanguageTool
    return JLanguageTool(get_language('yy'))


def readings_str(atr):
    # AnalyzedTokenReadings.getReadings().toString()
    return '[' + ', '.join(str(r) for r in atr.readings) + ']'


def test_disambiguate1(lt):
    chunker = MultiWordChunker(MULTIWORDS, True, True, True)
    tokens = chunker.disambiguate(lt.get_analyzed_sentence('ah for shame')).tokens

    assert '<adv>' in readings_str(tokens[1])
    assert 'adv' not in readings_str(tokens[3])
    assert '</adv>' in readings_str(tokens[5])

    assert 'FakePosTag' in readings_str(tokens[1])
    assert 'FakePosTag' in readings_str(tokens[3])
    assert 'FakePosTag' in readings_str(tokens[5])


def test_disambiguate2(lt):
    chunker = MultiWordChunker2(MULTIWORDS, True)
    tokens = chunker.disambiguate(lt.get_analyzed_sentence('Ah for shame')).tokens

    assert '<adv>' in readings_str(tokens[1])
    assert '<adv>' in readings_str(tokens[3])
    assert '<adv>' in readings_str(tokens[5])

    assert 'FakePosTag' in readings_str(tokens[1])
    assert 'FakePosTag' in readings_str(tokens[3])
    assert 'FakePosTag' in readings_str(tokens[5])


def test_disambiguate2_no_match(lt):
    chunker = MultiWordChunker2(MULTIWORDS, True)
    tokens = chunker.disambiguate(lt.get_analyzed_sentence('ahh for shame')).tokens
    assert '<adv>' not in readings_str(tokens[1])


def test_disambiguate2_remove_other_readings(lt):
    # Java: setRemoveOtherReadings(true); setWrapTag(false)
    chunker = MultiWordChunker2(MULTIWORDS, True, remove_other_readings=True, wrap_tag=False)
    tokens = chunker.disambiguate(lt.get_analyzed_sentence('ah for shame')).tokens

    assert 'adv' in readings_str(tokens[1])
    assert 'adv' in readings_str(tokens[3])
    assert 'adv' in readings_str(tokens[5])

    assert 'FakePosTag' not in readings_str(tokens[1])
    assert 'FakePosTag' not in readings_str(tokens[3])
    assert 'FakePosTag' not in readings_str(tokens[5])


def test_lettercase_variants():
    chunker = MultiWordChunker(MULTIWORDS, True, True, True)
    token_map = {
        'rhythm and blues': AnalyzedToken('rhythm and blues', 'NCMS000_', 'rhythm and blues'),
        'Vênus de Milo': AnalyzedToken('Vênus de Milo', 'NCFSS00_', 'Vênus de Milo'),
    }
    # Java: getTokenLettercaseVariants
    variants_rnb = chunker._lettercase_variants('rhythm and blues', token_map)
    assert 'Rhythm and blues' in variants_rnb  # simple upcase of first word
    assert 'Rhythm And Blues' in variants_rnb  # naive titlecase
    assert 'Rhythm and Blues' in variants_rnb  # smarter titlecase
    assert 'RHYTHM AND BLUES' in variants_rnb  # all caps
    variants_venus = chunker._lettercase_variants('Vênus de Milo', token_map)
    assert 'Vênus De Milo' not in variants_venus  # naive titlecase
    assert 'vênus de milo' not in variants_venus  # downcased
    assert 'VÊNUS DE MILO' in variants_venus  # all caps
