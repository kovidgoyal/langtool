"""Port of org.languagetool.rules.da.DanishPatternRuleTest: the <example>
sentences of the Danish XML rules (rules/da/grammar.xml)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['da', 'da-DK'])
def test_rules(code):
    require_dictionaries('da')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Danish disambiguation rules
    (resource/da/disambiguation.xml), checked in Java by
    DisambiguationRuleTest for all languages."""
    require_dictionaries('da')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('da')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
