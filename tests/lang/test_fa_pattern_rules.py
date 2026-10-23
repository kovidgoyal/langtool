"""Port of org.languagetool.rules.fa.PersianPatternRuleTest: the <example>
sentences of the Persian XML rules (rules/fa/grammar.xml). Persian has no
XML disambiguation rules."""

from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """PersianPatternRuleTest.testRules"""
    lang = get_language('fa')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
