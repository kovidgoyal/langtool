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


def sharded(codes, shards):
    """pytest parameters (code, shard) for a slow test over the rules of the
    languages: the codes in shards ({code: n}) are split into n parts
    (PatternRuleTester.run(shard=...)), so that the parts can run in parallel
    (pytest -n ...); shard is None for the other codes"""
    params = []
    for code in codes:
        n = shards.get(code)
        if n:
            params += [pytest.param(code, (k, n), id='%s-%dof%d' % (code, k + 1, n)) for k in range(n)]
        else:
            params.append(pytest.param(code, None, id=code))
    return params


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


# The tests run in the pure Python mode (LANGTOOL_PURE_PYTHON=1) as a smoke
# test: `LANGTOOL_PURE_PYTHON=1 pytest -m pure_smoke`. They cover the code
# that has a C implementation; test_c_vs_python.py compares the results of
# both implementations in detail (it runs both in subprocesses).
PURE_SMOKE_MODULES = {
    'test_analysis.py', 'test_api.py', 'test_core_rules.py', 'test_disambiguation_rules.py', 'test_fsa.py',
    'test_jlanguagetool.py', 'test_levenshtein.py', 'test_match.py', 'test_opennlp.py',
    'test_pattern_rule_matcher.py', 'test_pattern_token.py', 'test_spellcheck.py', 'test_string_matcher.py',
    'test_tokenizers.py', 'test_unifier.py', 'test_hunspell.py', 'test_speller_suggestions.py',
    'test_pl_pattern_rules.py',
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if os.path.basename(str(item.fspath)) in PURE_SMOKE_MODULES:
            item.add_marker(pytest.mark.pure_smoke)


# Diagnostics for the CI (LANGTOOL_TEST_DIAGNOSTICS=1): with -q the failures
# are only reported at the end of the run, which never comes when a test
# hangs. Every failure is reported when it happens (with the pytest-xdist
# worker), and the tests running for longer than LANGTOOL_TEST_SLOW_REPORT
# seconds (default 300) are listed every minute. (In the controller process
# only: pytest-xdist forwards the reports of the workers to it.)
class _Diagnostics:
    def __init__(self, config):
        import threading
        self.config = config
        self.slow = float(os.environ.get('LANGTOOL_TEST_SLOW_REPORT', '300'))
        self.running = {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def _write(self, text):
        tr = self.config.pluginmanager.get_plugin('terminalreporter')
        if tr is not None:
            tr.write_line(text)
        else:
            print(text, flush=True)

    def _watch(self):
        import time
        while not self.stop.wait(60):
            now = time.monotonic()
            with self.lock:
                slow = sorted((now - t, nodeid) for nodeid, t in self.running.items() if now - t > self.slow)
            if slow:
                self._write('\n[diagnostics] %d test(s) running for more than %d s:' % (len(slow), self.slow))
                for t, nodeid in reversed(slow):
                    self._write('[diagnostics]   %6d s  %s' % (t, nodeid))

    @pytest.hookimpl
    def pytest_sessionstart(self, session):
        self.thread.start()

    @pytest.hookimpl
    def pytest_sessionfinish(self, session):
        self.stop.set()

    @pytest.hookimpl
    def pytest_runtest_logstart(self, nodeid, location):
        import time
        with self.lock:
            self.running[nodeid] = time.monotonic()

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report):
        if report.when not in ('setup', 'call'):  # (teardown, or a crash of an xdist worker)
            with self.lock:
                self.running.pop(report.nodeid, None)
        if report.failed:
            worker = getattr(getattr(report, 'node', None), 'gateway', None)
            self._write('\n[diagnostics] FAILED (%s%s): %s' % (report.when, ', ' + worker.id if worker else '',
                                                                report.nodeid))
            self._write(report.longreprtext)


def pytest_configure(config):
    if os.environ.get('LANGTOOL_TEST_DIAGNOSTICS') and not hasattr(config, 'workerinput'):
        config.pluginmanager.register(_Diagnostics(config), 'langtool-diagnostics')
