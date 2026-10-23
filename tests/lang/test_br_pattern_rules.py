"""Port of org.languagetool.rules.br.BretonPatternRuleTest (the <example>
sentences of the Breton XML rules, rules/br/grammar.xml) and of the
DisambiguationRuleTest for the Breton XML disambiguation rules
(resource/br/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """BretonPatternRuleTest.testRules"""
    require_dictionaries('br')
    lang = get_language('br')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Breton disambiguation rules
    (resource/br/disambiguation.xml)"""
    require_dictionaries('br')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('br')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
