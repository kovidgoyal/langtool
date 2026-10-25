"""Port of org.languagetool.rules.de.GermanMultitokenSpeller (and of
German.prepareLineForSpeller, which it uses to read its word lists)."""

import threading

from ...rules.multitoken import MultitokenSpeller
from ...tools import java_split


def german_prepare_line_for_speller(line):
    """German.prepareLineForSpeller: the form of a word list line and its
    forms with the suffixes of the flags E, S and N ("Tisch/E" ->
    [Tisch, Tische])"""
    results = []
    parts = java_split(line, '#')
    if not parts:
        return [line]
    form_tag = java_split(parts[0], '/')
    if not form_tag:
        return ['']
    form = form_tag[0]
    results.append(form)
    tag = ''
    if len(form_tag) == 2:
        tag = form_tag[1]
    if 'E' in tag:
        results.append(form + 'e')
    if 'S' in tag:
        results.append(form + 's')
    if 'N' in tag:
        results.append(form + 'n')
    return results


class GermanMultitokenSpeller(MultitokenSpeller):
    """The MultitokenSpeller for /de/multitoken-suggest.txt,
    /spelling_global.txt and de/hunspell/spelling.txt (for the language
    de-DE), which doesn't correct a word that only differs from the
    candidate by a final s or hyphen."""

    def prepare_line_for_speller(self, s):
        return german_prepare_line_for_speller(s)

    def is_exception(self, original, candidate):
        if original[:-1] == candidate:
            if original.endswith('s') or original.endswith('-'):
                return True
        return False


_instance = []
_lock = threading.Lock()


def german_multitoken_speller(language):
    """GermanMultitokenSpeller.INSTANCE (for the language de-DE in Java)"""
    with _lock:
        if not _instance:
            from ...api import get_language
            from ...dictionaries import locate
            de_de = get_language('de-DE')
            paths = [locate('de/multitoken-suggest.txt', de_de.dictionary_path, de_de.download_dictionaries),
                     de_de.resource_path('spelling_global.txt'),
                     locate('de/hunspell/spelling.txt', de_de.dictionary_path, de_de.download_dictionaries)]
            _instance.append(GermanMultitokenSpeller(de_de, paths, de_de.get_default_spelling_rule()))
        return _instance[0]
