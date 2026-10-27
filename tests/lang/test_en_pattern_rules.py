"""Port of org.languagetool.rules.en.EnglishPatternRuleTest (the <example>
sentences of the English XML rules of en and its variants: rules/en/grammar.xml
and style.xml and the grammar.xml/style.xml of the variants, and the rules
for German and French speakers of grammar-l2-de.xml and grammar-l2-fr.xml)
and of the DisambiguationRuleTest for the English XML disambiguation rules
(resource/en/disambiguation.xml, checked in Java for all languages)."""

import os

import pytest

from conftest import require_dictionaries, sharded
from langtool.api import get_language
from langtool.messages import messages_for
from langtool.patterns.loader import load_pattern_rules
from langtool.rules.filters import default_filter_factory
from langtool.testing import DisambiguationRuleTester, PatternRuleTester
from langtool.tool import JLanguageTool


@pytest.mark.parametrize('code, shard', sharded(['en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-NZ', 'en-ZA'], {'en': 5}))
def test_rules(code, shard):
    """EnglishPatternRuleTest.testRules"""
    require_dictionaries('en')
    lang = get_language(code)
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    failures = tester.run(shard=shard)
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems


@pytest.mark.parametrize('name', ['grammar-l2-de.xml', 'grammar-l2-fr.xml'])
def test_l2_languages(name):
    """EnglishPatternRuleTest.testL2Languages: the rules for German and French
    speakers (only these rules, for AmericanEnglish)"""
    require_dictionaries('en')
    lang = get_language('en-US')
    path = os.path.join(lang.rules_dir, name)
    rules, problems = load_pattern_rules(path, lang, lang.resource_root, default_filter_factory(),
                                         messages_for('en'))
    assert rules and not problems
    lt = JLanguageTool(lang, rules=[])
    for rule in rules:
        lt.add_rule(rule)
    tester = PatternRuleTester(lt)
    tester.rules = rules
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))


@pytest.mark.parametrize('mother_tongue,name', [('de', 'grammar-l2-de.xml'), ('fr-FR', 'grammar-l2-fr.xml'),
                                                ('es', None), (None, None)])
def test_l2_rules_for_mother_tongue(mother_tongue, name):
    """English.getRelevantRules adds the rules of grammar-l2-de.xml or
    grammar-l2-fr.xml for German or French speakers (before the other
    rules)"""
    require_dictionaries('en')
    lang = get_language('en-GB')
    rules = JLanguageTool(lang, mother_tongue=mother_tongue).builtin_rules
    l2 = [r for r in rules if '-l2-' in (getattr(r, 'source_file', None) or '')]
    if name is None:
        assert not l2
    else:
        assert l2 and rules[:len(l2)] == l2
        assert all(r.source_file.endswith(name) for r in l2)


def test_bug():
    """EnglishPatternRuleTest.testBug: used to cause an
    ArrayIndexOutOfBoundsException in MatchState.setToken()"""
    require_dictionaries('en')
    JLanguageTool(get_language('en')).check('Alexander between 369 and 358 BC\n\nAlexander')


def test_disambiguation_rules():
    """The examples of the English disambiguation rules
    (resource/en/disambiguation.xml)"""
    require_dictionaries('en')
    tester = DisambiguationRuleTester(JLanguageTool(get_language('en')))
    failures = tester.run()
    assert tester.rules
    assert not failures, '\n'.join(map(str, failures))
