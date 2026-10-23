"""Port of org.languagetool.rules.sv.SwedishPatternRuleTest (the <example>
sentences of the Swedish XML rules, rules/sv/grammar.xml) and
org.languagetool.tagging.disambiguation.sv.SwedishDisambiguationRuleTest's
counterpart for the XML disambiguation rules (resource/sv/disambiguation.xml,
checked in Java by DisambiguationRuleTest for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """SwedishPatternRuleTest.testRules"""
    require_dictionaries('sv')
    lang = get_language('sv')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Swedish disambiguation rules
    (resource/sv/disambiguation.xml)"""
    require_dictionaries('sv')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('sv')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
