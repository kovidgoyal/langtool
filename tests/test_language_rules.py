"""The <example> sentences of the XML rules of all languages (the equivalent of
the PatternRuleTest/DisambiguationRuleTest classes of the language modules
of LanguageTool).

Not all rules pass yet, mostly because the language specific Java code
(taggers, tokenizers, filters, ...) is not ported. The rules failing now
are recorded in data/rule_test_baseline.json; the test fails if a rule that
is not in the baseline fails. Regenerate the baseline with
tools/run_all_rule_tests.py --write-baseline after fixing things.

These tests need the dictionaries and take several minutes, they are only
run with the environment variable LANGTOOL_LANGUAGE_TESTS=1.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, 'data', 'rule_test_baseline.json')
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tools'))

from run_all_rule_tests import codes_to_test, run_language  # noqa: E402

pytestmark = pytest.mark.skipif(not os.environ.get('LANGTOOL_LANGUAGE_TESTS'),
                                reason='set LANGTOOL_LANGUAGE_TESTS=1 to run the rule tests of all languages')


def _baseline():
    if not os.path.exists(BASELINE):
        return {}
    with open(BASELINE, encoding='utf-8') as f:
        return json.load(f)


@pytest.mark.parametrize('code', codes_to_test() if os.environ.get('LANGTOOL_LANGUAGE_TESTS') else [])
def test_rule_examples(code):
    from conftest import require_dictionaries
    require_dictionaries(code.split('-')[0])
    expected = _baseline().get(code)
    if expected is None:
        pytest.fail('no baseline for %s, run tools/run_all_rule_tests.py --write-baseline' % code)
    result = run_language(code)
    new_failures = sorted(set(result['failed_ids']) - set(expected['failed_ids']))
    assert not new_failures, 'rules failing that are not in the baseline: %s' % new_failures
    assert result['skipped'] <= expected['skipped'], 'more rules could not be loaded than before'
