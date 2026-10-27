"""Port of org.languagetool.rules.pt.PortuguesePatternRuleTest (the
<example> sentences of the Portuguese XML rules of pt and its variants:
rules/pt/grammar.xml and style.xml and the grammar.xml/style.xml of the
variants) and of the DisambiguationRuleTest for the Portuguese XML
disambiguation rules (resource/pt/disambiguation.xml, checked in Java for
all languages)."""

import pytest

from conftest import require_dictionaries, sharded
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code, shard', sharded(['pt', 'pt-PT', 'pt-BR', 'pt-AO', 'pt-MZ'], {'pt': 2}))
def test_rules(code, shard):
    """PortuguesePatternRuleTest.testRules"""
    require_dictionaries('pt')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run(shard=shard)
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the Portuguese disambiguation rules
    (resource/pt/disambiguation.xml)"""
    require_dictionaries('pt')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('pt')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
