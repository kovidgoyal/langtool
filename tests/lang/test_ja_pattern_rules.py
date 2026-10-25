"""Port of org.languagetool.rules.ja.JapanesePatternRuleTest (the <example>
sentences of the Japanese XML rules, rules/ja/grammar.xml). Japanese has no
disambiguation rules (DemoDisambiguator)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code', ['ja', 'ja-JP'])
def test_rules(code):
    """JapanesePatternRuleTest.testRules"""
    require_dictionaries('ja')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
