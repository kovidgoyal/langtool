"""Port of org.languagetool.rules.ar.ArabicPatternRuleTest (the <example>
sentences of the Arabic XML rules: rules/ar/grammar.xml) and of the
DisambiguationRuleTest for the Arabic XML disambiguation rules
(resource/ar/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """ArabicPatternRuleTest.testRules"""
    require_dictionaries('ar')
    lang = get_language('ar')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Arabic disambiguation rules
    (resource/ar/disambiguation.xml)"""
    require_dictionaries('ar')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('ar')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
