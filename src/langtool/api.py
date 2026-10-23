"""Public API."""

import threading

from .languages import LANGUAGES, resolve_code, all_codes

_languages = {}
_lock = threading.RLock()


def get_language(code):
    """Get the Language object for a code like 'en-US', 'de', 'pl-PL'."""
    from .language import Language
    short, vcode = resolve_code(code)
    with _lock:
        lang = _languages.get(vcode)
        if lang is None:
            d = LANGUAGES[short]
            vdef = next(v for v in d['variants'] if v['code'] == vcode)
            lang = _languages[vcode] = Language(short, d, vdef, get_language)
        return lang


def languages():
    """Codes of all supported languages (including variants)."""
    return all_codes()
