"""Port of org.languagetool.rules.is.IcelandicPatternRuleTest: the <example>
sentences of the Icelandic XML rules (rules/is/grammar.xml)."""

import pytest

from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['is', 'is-IS'])
def test_rules(code):
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
