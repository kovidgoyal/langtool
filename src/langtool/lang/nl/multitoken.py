"""Port of org.languagetool.rules.nl.DutchMultitokenSpeller."""

import threading

from ...rules.multitoken import MultitokenSpeller


class DutchMultitokenSpeller(MultitokenSpeller):
    """The MultitokenSpeller for /nl/multiwords.txt and
    /spelling_global.txt, which doesn't correct a word that only differs
    from the candidate by a final s, hyphen or 's."""

    def is_exception(self, original, candidate):
        if len(original) > 2:
            if original[:-1] == candidate:
                if original.endswith('s') or original.endswith('-'):
                    return True
            if original[:-2] == candidate:
                if original.endswith("'s") or original.endswith('’s'):
                    return True
        return False


_instance = []
_lock = threading.Lock()


def dutch_multitoken_speller(language):
    """DutchMultitokenSpeller.INSTANCE (for the language nl-NL in Java,
    i.e. Dutch)"""
    with _lock:
        if not _instance:
            _instance.append(DutchMultitokenSpeller(
                language, [language.resource_path('nl/multiwords.txt'), language.resource_path('spelling_global.txt')],
                language.get_default_spelling_rule()))
        return _instance[0]
