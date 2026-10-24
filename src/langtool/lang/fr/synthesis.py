"""Port of org.languagetool.synthesis.FrenchSynthesizer."""

from ...synthesis import BaseSynthesizer

_EXCEPTIONS_EGRAVE = frozenset(('burkinabè', 'koinè', 'épistémè'))


class FrenchSynthesizer(BaseSynthesizer):
    """French word form synthesizer (/fr/french_synth.dict with
    /fr/french_tags.txt and the number speller of /fr/fr.sor). Forms
    starting with "qq" (qq, qqe...) and forms ending with "è" (informè, V
    ind pres 1 s) are removed, except burkinabè, koinè and épistémè."""

    def is_exception(self, w):
        # remove: qq, qqe...
        if w.startswith('qq'):
            return True
        # informè V ind pres 1 s
        if w.endswith('è') and w.lower() not in _EXCEPTIONS_EGRAVE:
            return True
        return False
