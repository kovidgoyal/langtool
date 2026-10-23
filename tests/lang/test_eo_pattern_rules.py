"""Port of org.languagetool.rules.eo.EsperantoPatternRuleTest (the <example>
sentences of the Esperanto XML rules, rules/eo/grammar.xml) and of the
DisambiguationRuleTest for the Esperanto XML disambiguation rules
(resource/eo/disambiguation.xml, checked in Java for all languages)."""

from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """EsperantoPatternRuleTest.testRules"""
    lang = get_language('eo')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Esperanto disambiguation rules
    (resource/eo/disambiguation.xml)"""
    tester = DisambiguationRuleTester(JLanguageTool(get_language('eo')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
