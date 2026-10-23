"""Port of org.languagetool.rules.patterns.RegexPatternRuleTest and
RuleFilterEvaluatorTest"""

import pytest

from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.patterns.matcher import resolve_filter_arguments
from langtool.patterns.rules import AbstractPatternRule


def get_pattern_rules_by_id_and_sub_id(lt, id, sub_id):
    """JLanguageTool.getPatternRulesByIdAndSubId()"""
    return [r for r in lt.get_all_rules()
            if isinstance(r, AbstractPatternRule) and r.get_id() == id and r.get_sub_id() == sub_id]


def test_match(demo_lt):
    lt = demo_lt
    rule = get_pattern_rules_by_id_and_sub_id(lt, 'REGEX_PATTERN_RULE_DEMO_MARK_0', '1')[0]

    matches1 = rule.match(lt.get_analyzed_sentence('This is a test'))
    assert len(matches1) == 0

    matches2 = rule.match(lt.get_analyzed_sentence('This is foo bar'))
    assert len(matches2) == 1
    assert matches2[0].from_pos == 8
    assert matches2[0].to_pos == 15

    matches3 = rule.match(lt.get_analyzed_sentence('This is foo bar and fou bar'))
    assert len(matches3) == 2

    assert matches3[0].from_pos == 8
    assert matches3[0].to_pos == 15
    assert matches3[0].message == 'msg: <suggestion>a suggestion foo</suggestion>'
    assert matches3[0].suggested_replacements == ['a suggestion foo', 'another suggestion bar']

    assert matches3[1].from_pos == 20
    assert matches3[1].to_pos == 27
    assert matches3[1].message == 'msg: <suggestion>a suggestion fou</suggestion>'
    assert matches3[1].suggested_replacements == ['a suggestion fou', 'another suggestion bar']


def test_match_with_mark(demo_lt):
    lt = demo_lt
    rule = get_pattern_rules_by_id_and_sub_id(lt, 'REGEX_PATTERN_RULE_DEMO_MARK_1', '1')[0]
    matches2 = rule.match(lt.get_analyzed_sentence('This is foo bar'))
    assert len(matches2) == 1
    assert matches2[0].from_pos == 8
    assert matches2[0].to_pos == 11


# --- RuleFilterEvaluatorTest (RuleFilterEvaluator.getResolvedArguments -> resolve_filter_arguments)

def _atr(token, pos):
    return AnalyzedTokenReadings(AnalyzedToken(token, pos, None), 0)


def test_get_resolved_arguments():
    readings = [_atr('fake1', 'pos'), _atr('fake2', 'pos')]
    m = resolve_filter_arguments('year:\\1 month:\\2', readings, -1, [1, 1])
    assert m['year'] == 'fake1'
    assert m['month'] == 'fake2'
    assert len(m) == 2


def test_get_resolved_arguments_with_colon():
    readings = [_atr('fake1', 'pos')]
    m = resolve_filter_arguments('regex:(?:foo[xyz])bar', readings, -1, [1, 1])
    assert m['regex'] == '(?:foo[xyz])bar'
    assert len(m) == 1


def test_duplicate_key():
    readings = [_atr('fake1', 'SENT_START'), _atr('fake1', 'pos'), _atr('fake2', 'pos')]
    with pytest.raises(Exception):
        resolve_filter_arguments('year:\\1 year:\\2', readings, -1, [1, 2])


def test_no_back_reference():
    args = resolve_filter_arguments('year:2 foo:bar', None, -1, [])
    assert args == {'year': '2', 'foo': 'bar'}


def test_too_large_back_ref():
    with pytest.raises(Exception):
        resolve_filter_arguments('year:\\1 month:\\2 day:\\3 weekDay:\\4', None, -1, [])
