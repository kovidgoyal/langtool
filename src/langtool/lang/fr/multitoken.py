"""Port of org.languagetool.rules.fr.FrenchMultitokenSpeller."""

import threading

from ...rules.multitoken import MultitokenSpeller
from .spelling import prepare_line_for_speller


class FrenchMultitokenSpeller(MultitokenSpeller):
    """The MultitokenSpeller for /fr/multiwords.txt, /spelling_global.txt
    and /fr/hyphenated_words.txt (the lines are prepared with
    French.prepareLineForSpeller)."""

    def prepare_line_for_speller(self, s):
        return prepare_line_for_speller(s)


_instance = []
_lock = threading.Lock()


def french_multitoken_speller(language):
    """FrenchMultitokenSpeller.INSTANCE (for the language fr in Java, i.e.
    French)"""
    with _lock:
        if not _instance:
            _instance.append(FrenchMultitokenSpeller(
                language, [language.resource_path('fr/multiwords.txt'), language.resource_path('spelling_global.txt'),
                           language.resource_path('fr/hyphenated_words.txt')],
                language.get_default_spelling_rule()))
        return _instance[0]
