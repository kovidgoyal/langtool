"""Port of org.languagetool.rules.es.SpanishMultitokenSpeller."""

import threading

from ...rules.multitoken import MultitokenSpeller
from .spelling import prepare_line_for_speller


class SpanishMultitokenSpeller(MultitokenSpeller):
    """The MultitokenSpeller for /es/multiwords.txt, /spelling_global.txt
    and /es/hyphenated_words.txt (the lines are prepared with
    Spanish.prepareLineForSpeller)."""

    def prepare_line_for_speller(self, s):
        return prepare_line_for_speller(s)


_instance = []
_lock = threading.Lock()


def spanish_multitoken_speller(language):
    """SpanishMultitokenSpeller.INSTANCE (for the language es in Java,
    i.e. Spanish)"""
    with _lock:
        if not _instance:
            _instance.append(SpanishMultitokenSpeller(
                language, [language.resource_path('es/multiwords.txt'), language.resource_path('spelling_global.txt'),
                           language.resource_path('es/hyphenated_words.txt')],
                language.get_default_spelling_rule()))
        return _instance[0]
