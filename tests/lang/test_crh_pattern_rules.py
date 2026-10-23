"""Port of org.languagetool.rules.crh.CrimeanTatarPatternRuleTest: the
<example> sentences of the Crimean Tatar XML rules (rules/crh/grammar.xml).
Crimean Tatar has no disambiguation.xml (it uses the DemoDisambiguator)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['crh', 'crh-UA'])
def test_rules(code):
    require_dictionaries('crh')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
