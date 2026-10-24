"""Port of org.languagetool.rules.uk.UkrainianPatternRuleTest (the <example>
sentences of the Ukrainian XML rules, rules/uk/grammar*.xml) and of the
DisambiguationRuleTest for the Ukrainian XML disambiguation rules
(resource/uk/disambiguation.xml, checked in Java for all languages, with the
pre-disambiguation of UkrainianHybridDisambiguator)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """UkrainianPatternRuleTest.testRules"""
    require_dictionaries('uk')
    lang = get_language('uk')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Ukrainian disambiguation rules
    (resource/uk/disambiguation.xml)"""
    require_dictionaries('uk')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('uk')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
