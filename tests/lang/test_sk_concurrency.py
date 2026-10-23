"""Port of org.languagetool.SlovakConcurrencyTest
(AbstractLanguageConcurrencyTest.testSpellCheckerFailure): check a sample
text from many threads at the same time. Java ignores this test as too slow
(availableProcessors * 10 threads, 100 runs each); it runs here with fewer
threads and runs."""

import threading

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.tool import JLanguageTool

SAMPLE_TEXT = 'Wikipédia neobsahuje článok s takýmto názvom.'


def test_spell_checker_failure():
    require_dictionaries('sk')
    language = get_language('sk-SK')
    thread_count, test_runs = 8, 5
    start = threading.Event()
    errors = []

    def run():
        start.wait()
        for _ in range(test_runs):
            try:
                assert JLanguageTool(language).check(SAMPLE_TEXT) is not None
            except Exception as e:  # noqa: BLE001 -- counted like failedTests in Java
                errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(thread_count)]
    for t in threads:
        t.start()
    start.set()
    for t in threads:
        t.join()
    assert errors == []
