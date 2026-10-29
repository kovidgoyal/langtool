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

Spell checking with Hunspell dictionaries is optional::

    tool = langtool.LanguageTool('en-US', spell_check=True)

The rules and other data loaded for a language are cached on disk, which
makes loading a language several times faster after the first time (see
set_disk_cache(); LANGTOOL_DISK_CACHE=0 disables the cache).
"""

__version__ = '1.2.0'  # (defined before the imports: langtool.diskcache uses it)

from .api import (LanguageTool, Match, RuleInfo, check, clear_disk_cache, download_dictionaries, download_size,
                  downloads_needed, get_cache_dir, get_disk_cache_dir, get_language, hunspell_dictionary_info, is_ready,
                  language_names, languages, set_cache_dir, set_disk_cache, set_download_hook, set_url_opener,
                  spell_check_languages)
from .dictionaries import DictionaryNotFound, DownloadAborted, DownloadItem, DownloadProgress
from .hunspell_dictionaries import SpellCheckUnavailable
from .resources import ResourceDirError, set_resource_dir

__all__ = ['LanguageTool', 'Match', 'RuleInfo', 'check', 'download_dictionaries', 'get_language',
           'language_names', 'languages', 'DictionaryNotFound', 'SpellCheckUnavailable', 'have_speedups',
           'set_cache_dir', 'get_cache_dir', 'set_disk_cache', 'get_disk_cache_dir', 'clear_disk_cache',
           'spell_check_languages', 'hunspell_dictionary_info', 'static_rules_status', 'set_resource_dir',
           'get_resource_dir', 'ResourceDirError', 'downloads_needed', 'download_size', 'is_ready',
           'set_download_hook', 'set_url_opener', 'DownloadItem', 'DownloadProgress', 'DownloadAborted']


def get_resource_dir():
    """The directory of the data files of langtool (see set_resource_dir()
    and langtool.resources)."""
    from .resources import root
    return root()


def have_speedups():
    """Whether the C extension is used."""
    from ._base import speedups
    return speedups is not None


def static_rules_status():
    """{language code: status} of the static rule tables in the C extension
    (see the README): 'ok' (the rules of the language come from the tables),
    'stale: <reason>' (the rules are loaded from the XML files; rebuild the
    extension), 'disabled' (LANGTOOL_STATIC_RULES=0) or 'not checked' (the
    language was not used yet). Empty without the C extension or tables."""
    from .patterns.static import status
    return status()
