"""Port of org.languagetool.rules.el.GreekPatternRuleTest (the <example>
sentences of the Greek XML rules, rules/el/grammar.xml) and of the
DisambiguationRuleTest for the Greek XML disambiguation rules
(resource/el/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """GreekPatternRuleTest.testRules"""
    require_dictionaries('el')
    lang = get_language('el')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Greek disambiguation rules
    (resource/el/disambiguation.xml)"""
    require_dictionaries('el')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('el')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
