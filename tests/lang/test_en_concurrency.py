"""Port of org.languagetool.AmericanEnglishConcurrencyTest,
AustralianEnglishConcurrencyTest, BritishEnglishConcurrencyTest,
CanadianEnglishConcurrencyTest, NewZealandEnglishConcurrencyTest and
SouthAfricanEnglishConcurrencyTest
(AbstractLanguageConcurrencyTest.testSpellCheckerFailure): check a sample
text from many threads at the same time. Java ignores this test as too slow
(availableProcessors * 10 threads, 100 runs each); it runs here with fewer
threads and runs."""

import threading

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.tool import JLanguageTool

SAMPLE_TEXT = "A sentence with a error in the Hitchhiker's Guide tot he Galaxy"


@pytest.mark.parametrize('code', ['en-US', 'en-AU', 'en-GB', 'en-CA', 'en-NZ', 'en-ZA'])
def test_spell_checker_failure(code):
    require_dictionaries('en')
    language = get_language(code)
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
