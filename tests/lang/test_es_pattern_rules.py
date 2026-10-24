"""Port of org.languagetool.rules.es.SpanishPatternRuleTest (the <example>
sentences of the Spanish XML rules of es and es-AR: rules/es/grammar.xml and
style.xml) and of the DisambiguationRuleTest for the Spanish XML
disambiguation rules (resource/es/disambiguation.xml, checked in Java for
all languages)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['es', 'es-AR'])
def test_rules(code):
    """SpanishPatternRuleTest.testRules"""
    require_dictionaries('es')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Spanish disambiguation rules
    (resource/es/disambiguation.xml)"""
    require_dictionaries('es')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('es')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
