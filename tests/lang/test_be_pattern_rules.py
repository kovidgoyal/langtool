"""Port of org.languagetool.rules.be.BelarusianPatternRuleTest: the <example>
sentences of the Belarusian XML rules (rules/be/grammar.xml). Belarusian has
no disambiguation.xml (it uses the DemoDisambiguator)."""

import pytest

from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['be', 'be-BY'])
def test_rules(code):
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
