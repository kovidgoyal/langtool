"""Port of org.languagetool.rules.de.GermanPatternRuleTest (the <example>
sentences of the German XML rules of de and its variants de-DE, de-AT and
de-CH: rules/de/grammar.xml, style.xml, de-DE-AT/grammar.xml,
de-CH/grammar.xml), of the DisambiguationRuleTest for the German XML
disambiguation rules (resource/de/disambiguation.xml, checked in Java for
all languages) and of GermanRemoteRuleFilterTest (skipped: remote rules)."""

import pytest

from conftest import require_dictionaries, sharded
from langtool.api import get_language
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code, shard', sharded(['de', 'de-DE', 'de-AT', 'de-CH'], {'de': 4}))
def test_rules(code, shard):
    """GermanPatternRuleTest.testRules"""
    require_dictionaries('de')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run(shard=shard)
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


def test_disambiguation_rules():
    """The examples of the German disambiguation rules
    (resource/de/disambiguation.xml)"""
    require_dictionaries('de')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('de')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))


@pytest.mark.skip(reason='remote rules are not ported: GermanRemoteRuleFilterTest tests the filters of '
                         'remote-rule-filters.xml for remote (AI) rule matches')
def test_remote_rule_filters():
    """GermanRemoteRuleFilterTest.testRules"""
