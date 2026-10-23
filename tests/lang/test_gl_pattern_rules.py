"""Port of org.languagetool.rules.gl.GalicianPatternRuleTest (the <example>
sentences of the Galician XML rules, rules/gl/grammar.xml) and of the
DisambiguationRuleTest for the Galician XML disambiguation rules
(resource/gl/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """GalicianPatternRuleTest.testRules"""
    require_dictionaries('gl')
    lang = get_language('gl')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Galician disambiguation rules
    (resource/gl/disambiguation.xml)"""
    require_dictionaries('gl')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('gl')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
