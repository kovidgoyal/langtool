"""Port of org.languagetool.rules.ta.TamilPatternRuleTest: the <example>
sentences of the Tamil XML rules (rules/ta/grammar.xml)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['ta', 'ta-IN'])
def test_rules(code):
    require_dictionaries('ta')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
