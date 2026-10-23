"""Port of org.languagetool.rules.pl.PolishPatternRuleTest (the <example>
sentences of the Polish XML rules, rules/pl/grammar.xml) and of the
DisambiguationRuleTest for the Polish XML disambiguation rules
(resource/pl/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """PolishPatternRuleTest.testRules"""
    require_dictionaries('pl')
    lang = get_language('pl')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Polish disambiguation rules
    (resource/pl/disambiguation.xml)"""
    require_dictionaries('pl')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('pl')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
