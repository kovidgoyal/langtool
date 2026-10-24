"""Port of org.languagetool.rules.ru.RussianPatternRuleTest (the <example>
sentences of the Russian XML rules, rules/ru/grammar.xml) and of the
DisambiguationRuleTest for the Russian XML disambiguation rules
(resource/ru/disambiguation.xml, checked in Java for all languages)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """RussianPatternRuleTest.testRules"""
    require_dictionaries('ru')
    lang = get_language('ru')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Russian disambiguation rules
    (resource/ru/disambiguation.xml)"""
    require_dictionaries('ru')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('ru')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
