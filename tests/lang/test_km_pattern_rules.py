"""Port of org.languagetool.rules.km.KhmerPatternRuleTest (the <example>
sentences of the Khmer XML rules, rules/km/grammar.xml) and the counterpart
of DisambiguationRuleTest for the Khmer XML disambiguation rules
(resource/km/disambiguation.xml)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['km', 'km-KH'])
def test_rules(code):
    """KhmerPatternRuleTest.testRules"""
    require_dictionaries('km')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Khmer disambiguation rules
    (resource/km/disambiguation.xml)"""
    require_dictionaries('km')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('km')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
