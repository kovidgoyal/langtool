"""Port of org.languagetool.rules.nl.DutchPatternRuleTest (the <example>
sentences of the Dutch XML rules of nl and nl-BE: rules/nl/grammar.xml,
style.xml, nl-NL/grammar.xml and nl-BE/grammar.xml, style.xml) and of the
DisambiguationRuleTest for the Dutch XML disambiguation rules
(resource/nl/disambiguation.xml, checked in Java for all languages)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['nl', 'nl-BE'])
def test_rules(code):
    """DutchPatternRuleTest.testRules"""
    require_dictionaries('nl')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Dutch disambiguation rules
    (resource/nl/disambiguation.xml)"""
    require_dictionaries('nl')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('nl')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
