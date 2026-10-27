"""Port of org.languagetool.rules.ca.CatalanPatternRuleTest (the <example>
sentences of the Catalan XML rules of ca and its variants:
rules/ca/grammar.xml and rules/ca/ca-ES-valencia/grammar.xml) and of the
DisambiguationRuleTest for the Catalan XML disambiguation rules
(resource/ca/disambiguation.xml, checked in Java for all languages)."""

import pytest

from conftest import require_dictionaries, sharded
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code, shard', sharded(['ca-ES', 'ca-ES-valencia', 'ca-ES-balear'], {'ca-ES': 6}))
def test_rules(code, shard):
    """CatalanPatternRuleTest.testRules"""
    require_dictionaries('ca')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run(shard=shard)
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Catalan disambiguation rules
    (resource/ca/disambiguation.xml)"""
    require_dictionaries('ca')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('ca')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
