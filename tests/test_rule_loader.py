"""Port of org.languagetool.rules.patterns.PatternRuleLoaderTest and
PatternRuleHandlerTest"""

import os

import pytest

from langtool.chunking import ChunkTag
from langtool.patterns.loader import load_pattern_rules, replace_spaces_in_regex
from langtool.rules.filters import default_filter_factory

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, 'data', 'rules', 'xx')


def get_rules(language, name):
    rules, skipped = load_pattern_rules(os.path.join(RULES, name), language, language.resource_root,
                                        default_filter_factory())
    assert skipped == []
    return rules


def get_rule_by_id(id, rules):
    for r in rules:
        if r.get_id() == id:
            return r
    raise RuntimeError("No rule found for id '%s'" % id)


def get_rules_by_id(id, rules):
    return [r for r in rules if r.get_id() == id]


def test_get_rules(demo_language):
    rules = get_rules(demo_language, 'grammar.xml')
    assert len(rules) >= 30

    demo_rule1 = get_rule_by_id('DEMO_RULE', rules)
    assert demo_rule1.url == 'http://fake-server.org/foo-bar-error-explained'
    assert [e.example for e in demo_rule1.correct_examples] == ['This is <marker>fuu bah</marker>.']
    incorrect = demo_rule1.incorrect_examples
    assert len(incorrect) == 1
    assert incorrect[0].example == 'This is <marker>foo bar</marker>.'

    demo_rule2 = get_rule_by_id('API_OUTPUT_TEST_RULE', rules)
    assert demo_rule2.url is None

    assert demo_rule1.loc_quality_issue_type == 'Uncategorized'
    assert get_rule_by_id('TEST_GO', rules).loc_quality_issue_type == 'Addition', 'tag inheritance failed'
    assert get_rule_by_id('TEST_PHRASES1', rules).loc_quality_issue_type == 'Uncategorized', \
        'tag inheritance overwrite failed'
    assert get_rule_by_id('test_include', rules).loc_quality_issue_type == 'Characters', \
        'tag inheritance overwrite failed'

    group_rules1 = get_rules_by_id('test_spacebefore', rules)
    assert group_rules1[0].loc_quality_issue_type == 'Addition', 'tag inheritance form category failed'
    assert group_rules1[1].loc_quality_issue_type == 'Duplication', 'tag inheritance overwrite failed'
    group_rules2 = get_rules_by_id('test_unification_with_negation', rules)
    assert group_rules2[0].loc_quality_issue_type == 'Grammar', 'tag inheritance from rulegroup failed'

    categories = {r.category.name for r in rules}
    assert len(categories) == 5
    assert 'misc' in categories
    assert 'otherCategory' in categories
    assert 'Test tokens with min and max attributes' in categories
    assert "A category that's off by default" in categories

    demo_rule_with_chunk = get_rule_by_id('DEMO_CHUNK_RULE', rules)
    pattern_tokens = demo_rule_with_chunk.pattern_tokens
    assert len(pattern_tokens) == 2
    assert pattern_tokens[1].get_pos_tag() is None
    assert pattern_tokens[1].chunk_tag == ChunkTag('B-NP-singular')

    or_rules = get_rules_by_id('GROUP_WITH_URL', rules)
    assert len(or_rules) == 3
    assert or_rules[0].url == 'http://fake-server.org/rule-group-url'
    assert or_rules[1].url == 'http://fake-server.org/rule-group-url-overwrite'
    assert or_rules[2].url == 'http://fake-server.org/rule-group-url'

    assert or_rules[0].get_short_message() == 'short message on rule group'
    assert or_rules[1].get_short_message() == 'overwriting short message'
    assert or_rules[2].get_short_message() == 'short message on rule group'

    # make sure URLs don't leak to the next rule:
    for rule in get_rules_by_id('OR_GROUPS', rules):
        assert rule.url is None
    assert get_rule_by_id('DEMO_CHUNK_RULE', rules).url is None


@pytest.mark.parametrize('file,id,premium', [
    ('grammar-nonPremium.xml', 'F-NP_C-NP_RG-NP_R-NP', False),
    ('grammar-nonPremium.xml', 'F-NP_C-NP_RG-NP_R-P', True),
    ('grammar-nonPremium.xml', 'F-NP_C-NP_RG-P_R-NP', False),
    ('grammar-nonPremium.xml', 'F-NP_C-NP_RG-P_R-P', True),
    ('grammar-nonPremium.xml', 'F-NP_C-P_RG-NP_R-NP', False),
    ('grammar-nonPremium.xml', 'F-NP_C-P_RG-NP_R-P', False),
    ('grammar-nonPremium.xml', 'F-NP_C-P_RG-P_R-NP', False),
    ('grammar-nonPremium.xml', 'F-NP_C-P_RG-P_R-P', True),
    ('grammar-premium.xml', 'F-P_C-P_RG-P_R-P', True),
    ('grammar-premium.xml', 'F-P_C-P_RG-P_R-NP', False),
    ('grammar-premium.xml', 'F-P_C-P_RG-NP_R-P', True),
    ('grammar-premium.xml', 'F-P_C-P_RG-NP_R-NP', False),
    ('grammar-premium.xml', 'F-P_C-NP_RG-P_R-NP', False),
    ('grammar-premium.xml', 'F-P_C-NP_RG-P_R-P', True),
    ('grammar-premium.xml', 'F-P_C-NP_RG-NP_R-NP', False),
    ('grammar-premium.xml', 'F-P_C-NP_RG-NP_R-P', True),
])
def test_premium_xml_flag(demo_language, file, id, premium):
    rules = get_rules(demo_language, file)
    assert get_rule_by_id(id, rules).premium is premium


def test_tone_tags_attribute(demo_language):
    style_rules = get_rules(demo_language, 'style.xml')

    def tone(id, tags, goal_specific, picky=False):
        r = get_rule_by_id(id, style_rules)
        for t in tags:
            assert t in r.tone_tags, (id, t)
        assert len(r.tone_tags) == len(tags), id
        if picky:
            assert r.has_tag('picky'), id
        assert r.goal_specific is goal_specific, id

    tone('Formal_Clarity_TONE_RULE', ['formal', 'clarity'], False)
    tone('NO_TONE_RULE', [], False)
    tone('CONFIDENT_ACADEMIC_SCIENTIFIC_TONE_RULE', ['confident', 'academic', 'scientific'], False)
    tone('CONFIDENT_ACADEMIC_TONE_RULE', ['confident', 'academic'], False)
    tone('PICKY-CLARITY_CONFIDENT_ACADEMIC_TONE_RULE', ['clarity', 'confident', 'academic'], False, picky=True)
    tone('PICKY-CLARITY_CONFIDENT_ACADEMIC_SCIENTIFIC_TONE_RULE', ['clarity', 'confident', 'academic', 'scientific'],
         False, picky=True)
    tone('PERSUASIVE_OBJECTIVE_TONE_RULE', ['persuasive', 'objective'], False)
    tone('PERSUASIVE_OBJECTIVE_INFORMAL_TONE_RULE', ['persuasive', 'objective', 'informal'], False)

    r = get_rule_by_id('PERSUASIVE_GOAL_SPECIFIC_TONE_RULE', style_rules)
    assert 'persuasive' in r.tone_tags
    assert r.goal_specific
    r = get_rule_by_id('PERSUASIVE_NOT_GOAL_SPECIFIC_TONE_RULE', style_rules)
    assert 'persuasive' in r.tone_tags
    assert not r.goal_specific

    assert get_rule_by_id('IS_GOAL_SPECIFIC_RULE_GROUP_FALSE_OVERRIDE_TEST_1', style_rules).goal_specific
    assert not get_rule_by_id('IS_GOAL_SPECIFIC_RULE_GROUP_FALSE_OVERRIDE_TEST_2', style_rules).goal_specific
    assert not get_rule_by_id('IS_GOAL_SPECIFIC_RULE_GROUP_FALSE_OVERRIDE_TEST_3', style_rules).goal_specific
    assert get_rule_by_id('IS_GOAL_SPECIFIC_FROM_CATEGORY', style_rules).goal_specific


def test_prio_attribute(demo_language):
    rules = get_rules(demo_language, 'grammar-withPrio.xml')
    assert get_rule_by_id('CAT-PRIO-5-RG-PRIO-10-R-PRIO-15', rules).priority == 15
    assert get_rule_by_id('CAT-PRIO-5-RG-PRIO-10-R-PRIO-0', rules).priority == 10
    assert get_rule_by_id('CAT-PRIO-5-RG-PRIO-0-R-PRIO-0', rules).priority == 5
    assert get_rule_by_id('CAT-PRIO-0-RG-PRIO-0-R-PRIO-0', rules).priority == 0
    assert get_rule_by_id('CAT-PRIO-0-R-PRIO-0', rules).priority == 0


# --- PatternRuleHandlerTest

def test_replace_spaces_in_regex():
    s = '(?:[\\s  ]+)'
    assert replace_spaces_in_regex('foo bar') == 'foo' + s + 'bar'
    assert replace_spaces_in_regex('foo bar x') == 'foo' + s + 'bar' + s + 'x'
    assert replace_spaces_in_regex('foo  bar') == 'foo' + s + s + 'bar'  # well, does not really make sense
    assert replace_spaces_in_regex('fo[xy ] bar') == 'fo[xy ]' + s + 'bar'


# --- not ported from Java

ENTITY_RULES = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE rules [
    <!ENTITY date '
        <token regexp="yes">\\d\\d?</token>
        <token>.</token>
    '>
]>
<rules lang="xx">
    <category id="C" name="c">
        <rule id="FIRST" name="first">
            <pattern>&date;</pattern>
            <message>m</message>
        </rule>
        <rule id="AFTER_COMMENT" name="after a comment">
            <pattern>
                <!-- "7." -->
                &date;
            </pattern>
            <message>m</message>
        </rule>
        <rule id="IN_MARKER" name="in a marker">
            <pattern><token>x</token><marker> &date; </marker></pattern>
            <message>m</message>
        </rule>
    </category>
</rules>
'''


def test_repeated_entity_references(demo_language, tmp_path):
    """every reference of an entity whose value starts with text has its
    tokens (libxml2 before 2.13, used by lxml's Windows wheels, sends no
    parser target events for the later references)"""
    path = tmp_path / 'grammar.xml'
    path.write_text(ENTITY_RULES, encoding='utf-8')
    rules, skipped = load_pattern_rules(str(path), demo_language, demo_language.resource_root,
                                        default_filter_factory())
    assert skipped == []
    tokens = {r.get_id(): [t.get_string() for t in r.pattern_tokens] for r in rules}
    assert tokens == {'FIRST': ['\\d\\d?', '.'], 'AFTER_COMMENT': ['\\d\\d?', '.'], 'IN_MARKER': ['x', '\\d\\d?', '.']}
