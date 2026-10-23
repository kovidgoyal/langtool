"""Port of org.languagetool.rules.ro.RomanianPatternRuleTest (the <example>
sentences of the Romanian XML rules, rules/ro/grammar.xml) and of the
DisambiguationRuleTest for the Romanian XML disambiguation rules
(resource/ro/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """RomanianPatternRuleTest.testRules"""
    require_dictionaries('ro')
    lang = get_language('ro')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Romanian disambiguation rules
    (resource/ro/disambiguation.xml)"""
    require_dictionaries('ro')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('ro')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
