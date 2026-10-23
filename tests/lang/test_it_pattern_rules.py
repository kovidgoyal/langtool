"""Port of org.languagetool.rules.it.ItalianPatternRuleTest (the <example>
sentences of the Italian XML rules, rules/it/grammar.xml) and of the
DisambiguationRuleTest for the Italian XML disambiguation rules
(resource/it/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """ItalianPatternRuleTest.testRules"""
    require_dictionaries('it')
    lang = get_language('it')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Italian disambiguation rules
    (resource/it/disambiguation.xml)"""
    require_dictionaries('it')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('it')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
