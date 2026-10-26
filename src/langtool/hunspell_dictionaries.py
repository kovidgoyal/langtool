"""The Hunspell dictionaries (.aff + .dic) used for spell checking.

A dictionary for a language is taken from (in order):

1. The dictionaries given by the API consumer: a mapping from a language or
   variant code to the location of a Hunspell dictionary, e.g.
   ``{'en-US': '/usr/share/hunspell/en_US'}``. A location is either a path
   prefix (``.aff`` and ``.dic`` are appended; a path ending with ``.aff``
   or ``.dic`` is also accepted) or a pair ``(aff_path, dic_path)``. The
   code of the variant (``de-CH``) is looked up first, then the language
   (``de``); ``de_CH`` is the same as ``de-CH``.
2. The download cache (see langtool.dictionaries.cache_root(): the
   ``hunspell/<commit>`` sub directory).
3. A download from the LibreOffice dictionaries repository
   (https://github.com/LibreOffice/dictionaries) at the commit pinned in
   hunspell_dictionaries.json (created by tools/make_hunspell_manifest.py),
   with the sha256 checksums of the manifest verified.

The manifest maps every language code to a LibreOffice dictionary (or to
none, see unavailable_languages()).
"""

import os
import threading
from functools import lru_cache

from .dictionaries import DictionaryNotFound, cache_root, download_file

_lock = threading.RLock()


class SpellCheckUnavailable(DictionaryNotFound):
    """There is no Hunspell dictionary for the language: none was given
    and the LibreOffice dictionaries have none (or downloading is not
    allowed and the dictionary is not in the cache)."""


@lru_cache()
def manifest():
    import json
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hunspell_dictionaries.json'),
              encoding='utf-8') as f:
        return json.load(f)


def _norm_code(code):
    return str(code).replace('_', '-').lower()


def _codes_for(language):
    """The codes under which a dictionary for the language (a code or a
    Language) is looked up: the variant code, then the language code"""
    if isinstance(language, str):
        from .languages import resolve_code
        short, vcode = resolve_code(language)
    else:
        short, vcode = language.short_code, language.code
    return [vcode] if vcode == short else [vcode, short]


def dictionary_name(language):
    """The LibreOffice dictionary (path in the repository without .aff/.dic,
    e.g. 'en/en_US') for a language code or Language, None if there is
    none."""
    langs = manifest()['languages']
    for c in _codes_for(language):
        if c in langs:
            return langs[c]
    return None


def note(language):
    """A remark about the dictionary used for the language (fallbacks), or
    None."""
    notes = manifest().get('notes', {})
    for c in _codes_for(language):
        if c in notes:
            return notes[c]
    return None


def available_languages():
    """The language codes that have a LibreOffice dictionary."""
    return sorted(c for c, d in manifest()['languages'].items() if d)


def unavailable_languages():
    """The language codes without a LibreOffice dictionary (spell checking
    needs a dictionary given by the API consumer for them)."""
    return sorted(c for c, d in manifest()['languages'].items() if not d)


def hunspell_cache_dir():
    """Where the downloaded Hunspell dictionaries are cached."""
    return os.path.join(cache_root(), 'hunspell', manifest()['commit'][:12])


def normalize_location(location):
    """The (aff_path, dic_path) of a dictionary location: a path prefix
    (str or os.PathLike, with or without .aff/.dic) or a pair of paths.
    Raises FileNotFoundError if a file does not exist."""
    if isinstance(location, (str, os.PathLike)):
        p = os.fspath(location)
        if p.endswith(('.aff', '.dic')):
            p = p[:-4]
        aff, dic = p + '.aff', p + '.dic'
    else:
        try:
            a, b = location
        except (TypeError, ValueError):
            raise TypeError('a Hunspell dictionary is a path prefix or an (aff, dic) pair, not %r' % (location,))
        aff, dic = os.fspath(a), os.fspath(b)
        if aff.endswith('.dic') and dic.endswith('.aff'):
            aff, dic = dic, aff
    for p in (aff, dic):
        if not os.path.isfile(p):
            raise FileNotFoundError('Hunspell dictionary file not found: %s' % p)
    return aff, dic


def user_dictionary(dictionaries, language):
    """The (aff, dic) pair from the mapping dictionaries (code -> location)
    for the language, None if the mapping has none for it."""
    if not dictionaries:
        return None
    by_code = {_norm_code(k): v for k, v in dictionaries.items()}
    for c in _codes_for(language):
        loc = by_code.get(_norm_code(c))
        if loc is not None:
            return normalize_location(loc)
    return None


def _cached_paths(name):
    d = hunspell_cache_dir()
    return os.path.join(d, name + '.aff'), os.path.join(d, name + '.dic')


def is_cached(language):
    name = dictionary_name(language)
    return name is not None and all(os.path.exists(p) for p in _cached_paths(name))


def download(language, progress=None):
    """Download the LibreOffice dictionary of the language (a code or
    Language) into the cache, returns (aff, dic). Raises
    SpellCheckUnavailable if there is none."""
    name = dictionary_name(language)
    if name is None:
        raise SpellCheckUnavailable(_unavailable_message(language))
    entry = manifest()['dictionaries'][name]
    paths = _cached_paths(name)
    with _lock:
        for ext, path in zip(('aff', 'dic'), paths):
            if not os.path.exists(path):
                download_file(entry[ext]['url'], path, entry[ext]['sha256'], progress)
    return paths


def download_all(progress=None):
    for name in sorted({d for d in manifest()['languages'].values() if d}):
        code = next(c for c, d in manifest()['languages'].items() if d == name)
        download(code, progress)


def _code(language):
    return language if isinstance(language, str) else language.code


def _unavailable_message(language):
    return ('Spell checking is not available for %s: there is no LibreOffice Hunspell dictionary for it. '
            'Pass the path of a Hunspell dictionary (.aff/.dic) with the hunspell_dictionaries argument.'
            % _code(language))


def locate(language, dictionaries=None, download_allowed=True, progress=None):
    """The (aff, dic) paths of the Hunspell dictionary for the language (a
    code or Language): from the mapping dictionaries, the cache or (if
    download_allowed) downloaded. Raises SpellCheckUnavailable if there is
    no dictionary."""
    user = user_dictionary(dictionaries, language)
    if user is not None:
        return user
    name = dictionary_name(language)
    if name is None:
        raise SpellCheckUnavailable(_unavailable_message(language))
    paths = _cached_paths(name)
    if all(os.path.exists(p) for p in paths):
        return paths
    if not download_allowed:
        raise SpellCheckUnavailable(
            'The Hunspell dictionary for %s (%s) is not in the cache (%s) and downloading is not allowed.'
            % (_code(language), name, hunspell_cache_dir()))
    return download(language, progress)
