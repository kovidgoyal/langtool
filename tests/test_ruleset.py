"""Port of org.languagetool.rules.patterns.RuleSetTest

Java's RuleSet.textHinted(rules) / RuleSet.textLemmaHinted(rules) correspond
to RuleSet(rules, with_lemma_hints=False/True)."""

import pytest

from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.patterns.pattern_token import PatternToken, PosToken
from langtool.patterns.rules import PatternRule
from langtool.patterns.ruleset import RuleSet


def text_hinted(rules):
    return RuleSet(rules, with_lemma_hints=False)


def text_lemma_hinted(rules):
    return RuleSet(rules, with_lemma_hints=True)


def build(token=None, cs=False, regexp=False, inflected=False, pos=None):
    """PatternTokenBuilder / PatternRuleBuilderHelper"""
    pt = PatternToken(token, cs, regexp, inflected)
    if pos is not None:
        pt.pos_token = PosToken(pos, False, regexp=regexp)
    return pt


@pytest.fixture(scope='module')
def sample_sentence():
    return AnalyzedSentence([AnalyzedTokenReadings(AnalyzedToken('token', 'pos', 'lemma'))])


@pytest.fixture
def rule_of(demo_language):
    def f(token):
        return PatternRule('', demo_language, [token], '', '', '')
    return f


def assert_rules_for_sentence(sentence, rule_set, *expected):
    assert rule_set.rules_for_sentence(sentence) == list(expected)


def test_text_hints_are_honored(sample_sentence, rule_of):
    suitable = rule_of(build('token', cs=True))
    assert_rules_for_sentence(sample_sentence, text_hinted([suitable]), suitable)

    suitable = rule_of(build('Token'))
    assert_rules_for_sentence(sample_sentence, text_hinted([suitable]), suitable)

    suitable = rule_of(build('token|another', regexp=True))
    assert_rules_for_sentence(sample_sentence, text_hinted([suitable]), suitable)

    assert_rules_for_sentence(sample_sentence, text_hinted([rule_of(build('unsuitable', cs=True))]))


def test_lemma_hints_are_honored(sample_sentence, rule_of):
    suitable = rule_of(build('lemma', inflected=True))
    assert_rules_for_sentence(sample_sentence, text_lemma_hinted([suitable]), suitable)

    suitable = rule_of(build('Lemma', inflected=True))
    assert_rules_for_sentence(sample_sentence, text_lemma_hinted([suitable]), suitable)

    suitable = rule_of(build('lemm[ab]', cs=True, regexp=True, inflected=True))
    assert_rules_for_sentence(sample_sentence, text_lemma_hinted([suitable]), suitable)

    unsuitable = build('unsuitable', cs=True, inflected=True)
    assert_rules_for_sentence(sample_sentence, text_lemma_hinted([rule_of(unsuitable)]))

    unrelated = rule_of(build(pos='somePos'))
    assert_rules_for_sentence(sample_sentence, text_lemma_hinted([rule_of(unsuitable), unrelated]), unrelated)
