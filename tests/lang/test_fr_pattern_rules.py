"""Port of org.languagetool.rules.fr.FrenchPatternRuleTest (the <example>
sentences of the French XML rules of fr, fr-CA, fr-CH and fr-BE:
rules/fr/grammar.xml and style.xml) and of the DisambiguationRuleTest for
the French XML disambiguation rules (resource/fr/disambiguation.xml,
checked in Java for all languages)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['fr', 'fr-CA', 'fr-CH', 'fr-BE'])
def test_rules(code):
    """FrenchPatternRuleTest.testRules"""
    require_dictionaries('fr')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the French disambiguation rules
    (resource/fr/disambiguation.xml)"""
    require_dictionaries('fr')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('fr')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
