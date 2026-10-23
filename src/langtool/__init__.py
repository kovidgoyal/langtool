"""langtool: grammar, style and typography checking for many languages, based
on the rules of LanguageTool (https://languagetool.org).

Quick start::

    import langtool
    tool = langtool.LanguageTool('en-US')
    for match in tool.check('This are a sentence with a error.'):
        print(match.offset, match.length, match.rule_id, match.message, match.replacements)

The binary dictionaries needed for part of speech tagging are downloaded on
first use (or can be pointed to with the dictionary_path argument or the
LANGTOOL_DICT_PATH environment variable).
"""

from .api import (LanguageTool, Match, RuleInfo, check, download_dictionaries, get_language, language_names,
                  languages)
from .dictionaries import DictionaryNotFound

__version__ = '0.1.0'

__all__ = ['LanguageTool', 'Match', 'RuleInfo', 'check', 'download_dictionaries', 'get_language',
           'language_names', 'languages', 'DictionaryNotFound', 'have_speedups']


def have_speedups():
    """Whether the C extension is used."""
    from ._base import speedups
    return speedups is not None
