"""Shared test fixtures. The "demo" language (code xx) is a port of the
org.languagetool.language.Demo test language of LanguageTool, using the test
resources of languagetool-core (copied to tests/data)."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'src'))
DATA = os.path.join(HERE, 'data')

from langtool import extensions  # noqa: E402
from langtool.languages import register_language, V, xml  # noqa: E402


class DemoChunker:
    """Port of org.languagetool.chunking.xx.DemoChunker"""

    def add_chunk_tags(self, token_readings):
        from langtool.chunking import ChunkTag
        for t in token_readings:
            if t.token == 'chunkbar':
                t.set_chunk_tags([ChunkTag('B-NP-singular')])


class DemoDisambiguationFilter:
    """Port of org.languagetool.tagging.disambiguation.rules.xx.DemoDisambiguationFilter"""

    def __init__(self, language=None):
        self.language = language

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        if pattern_tokens[0].token == 'X9':
            return match
        return None

    def matches(self, arguments, pattern_tokens, first_match_token, token_positions):
        from langtool.rules.filters import RuleFilter
        return RuleFilter.matches(self, arguments, pattern_tokens, first_match_token, token_positions)


from langtool.rules.core_filters import PartialPosTagFilter  # noqa: E402


class DemoPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.DemoPartialPosTagFilter"""

    def tag(self, token):
        from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
        if token == 'accurate':
            return [AnalyzedTokenReadings([AnalyzedToken(token, 'JJ', 'fake')], 0)]
        return None


extensions.register('filter', 'org.languagetool.rules.DemoPartialPosTagFilter', DemoPartialPosTagFilter)
extensions.register('chunker', 'DemoChunker', lambda lang: DemoChunker())
extensions.register('filter', 'org.languagetool.tagging.disambiguation.rules.xx.DemoDisambiguationFilter',
                    DemoDisambiguationFilter)

DEMO = dict(
    name='Testlanguage', countries=['XX'], variants=[V('xx-XX')], data_dir=DATA,
    tagger=None, chunker='DemoChunker', disambiguator=[xml()], rules=[],
)
register_language('xx', DEMO)


@pytest.fixture(scope='session')
def demo_language():
    from langtool.api import get_language
    return get_language('xx-XX')


@pytest.fixture(scope='session')
def demo_lt(demo_language):
    from langtool.tool import JLanguageTool
    return JLanguageTool(demo_language)


def dictionaries_available(lang_code):
    from langtool.dictionaries import is_available
    return is_available(lang_code)


def require_dictionaries(lang_code):
    """Skip a test if the dictionaries of a language can not be obtained."""
    from langtool.dictionaries import DictionaryNotFound, download_language, is_available
    if is_available(lang_code):
        return
    if os.environ.get('LANGTOOL_NO_DOWNLOAD'):
        pytest.skip('dictionaries for %s not available' % lang_code)
    try:
        download_language(lang_code)
    except Exception as e:  # network problems etc.
        pytest.skip('could not download dictionaries for %s: %s' % (lang_code, e))
