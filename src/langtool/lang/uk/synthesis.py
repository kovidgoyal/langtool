"""Port of org.languagetool.synthesis.uk.UkrainianSynthesizer."""

from ...extensions import synthesizer_resources
from ...synthesis import BaseSynthesizer


class UkrainianSynthesizer(BaseSynthesizer):
    """Ukrainian word form synthesizer: a BaseSynthesizer for
    /uk/ukrainian_synth.dict with the tags of /uk/ukrainian_tags.txt (and the
    manual additions/removals of the resource directory)."""

    def __init__(self, dictionary, tags_path, resource_dir=None, number_speller=None, roman_numberer=None):
        super().__init__(dictionary, tags_path, 'uk', resource_dir, number_speller, roman_numberer)


def create_ukrainian_synthesizer(language, spec):
    """The 'synthesizer' factory (UkrainianSynthesizer.INSTANCE)"""
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return UkrainianSynthesizer(dictionary, tags_path, language.resource_dir, number_speller, roman_numberer)
