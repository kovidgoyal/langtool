"""Language specific code (ports of the Java code of the language modules of
LanguageTool), one package per language code (a trailing underscore is added
when the code is a Python keyword, like ``is_``, and a
code with dashes gets a valid package name: de_simple for
de-DE-x-simple-language). load_all() imports all of them,
which registers the implementations with langtool.extensions (which
imports only the package of a language when that is enough)."""

import importlib

PACKAGES = ('ar', 'ast', 'be', 'br', 'ca', 'crh', 'da', 'de', 'de_simple', 'el', 'en', 'eo', 'es', 'fa', 'fr', 'ga', 'gl', 'is_', 'it', 'ja', 'km', 'lt', 'ml', 'nl', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sv', 'ta', 'tl', 'uk', 'zh')


def load_all():
    """Imports all the language packages"""
    for p in PACKAGES:
        importlib.import_module(__name__ + '.' + p)
