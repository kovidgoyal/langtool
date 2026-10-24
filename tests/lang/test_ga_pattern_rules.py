"""Port of org.languagetool.rules.ga.IrishPatternRuleTest (the <example>
sentences of the Irish XML rules, rules/ga/grammar.xml) and of the
DisambiguationRuleTest for the Irish XML disambiguation rules
(resource/ga/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """IrishPatternRuleTest.testRules"""
    require_dictionaries('ga')
    lang = get_language('ga')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Irish disambiguation rules
    (resource/ga/disambiguation.xml)"""
    require_dictionaries('ga')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('ga')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
