"""Port of org.languagetool.tagging.disambiguation.rules.DisambiguationRuleTest
for the demo language (tests/data/resource/xx/disambiguation.xml).

Note: in Java the demo language uses the DemoDisambiguator, so the Java test
actually skips it; the Python demo language (see conftest.py) uses the XML
rule disambiguator with the copied test resource, which is checked here with
the same logic as the Java test."""

import os

import pytest
import regex

from langtool.analysis import AnalyzedSentence
from langtool.api import get_language
from langtool.patterns.loader import load_disambiguation_rules
from langtool.rules.filters import default_filter_factory

HERE = os.path.dirname(os.path.abspath(__file__))
DISAMB_FILE = os.path.join(HERE, 'data', 'resource', 'xx', 'disambiguation.xml')


def _load_rules():
    lang = get_language('xx-XX')
    rules, skipped = load_disambiguation_rules(DISAMB_FILE, lang, lang.resource_root, default_filter_factory())
    assert not skipped, skipped
    return rules


RULES = _load_rules()

_CLEAN_XML = regex.compile('<.*?>')
_WS = regex.compile('[\\n\\t]+')


def clean_xml(s):
    return _CLEAN_XML.sub('', s)


def sort_forms(word_forms):
    if word_forms == ',[,]':
        return word_forms
    if len(word_forms) == 0:
        return word_forms
    word = word_forms[:word_forms.index('[') + 1]
    forms = word_forms[word_forms.index('[') + 1:len(word_forms) - 1]
    to_sort = forms.split(',')
    # Java Arrays.sort on Strings: UTF-16 code unit order
    to_sort.sort(key=lambda s: s.encode('utf-16-be', 'surrogatepass'))
    return word + ','.join(to_sort) + ']'


def disambiguate_until(rules, rule_id, sentence):
    """useful for testing the rule cascade (the demo language has no
    preDisambiguate step)"""
    disambiguated = sentence
    for rule in rules:
        if rule_id == rule.get_id():
            break
        disambiguated = rule.replace(disambiguated)
    return disambiguated


def test_rules_loaded():
    assert len(RULES) > 10


@pytest.mark.parametrize('index', range(len(RULES)),
                         ids=['%s[%s]' % (r.get_id(), r.get_sub_id()) for r in RULES])
def test_disambiguation_rules_from_xml(demo_lt, index):
    lt = demo_lt
    rules = RULES
    rule = rules[index]
    rid = rule.get_id()
    if rule.untouched_examples is not None:
        for good in rule.untouched_examples:
            # enable indentation use
            good = _WS.sub('', good)
            good = clean_xml(good)
            assert len(good.strip()) > 0
            sent = disambiguate_until(rules, rid, lt.get_raw_analyzed_sentence(good))
            sent_to_replace = disambiguate_until(rules, rid, lt.get_raw_analyzed_sentence(good))
            assert str(sent) == str(rule.replace(sent_to_replace)), \
                'The untouched example (%s) for rule %s] was touched!' % (good, rule)
    if rule.examples is not None:
        for example, input_forms, output_forms in rule.examples:
            assert output_forms is not None, 'No output form found for: ' + rid
            assert len(output_forms.strip()) > 0, 'Output form must not be empty'
            expected_start = example.find('<marker>')
            expected_end = example.find('</marker>') - len('<marker>')
            if expected_start == -1 or expected_end == -1:
                pytest.fail("No position markup ('<marker>...</marker>') in disambiguated example in rule %s" % rule)
            assert input_forms is not None, 'No input form found for: ' + rid
            assert len(input_forms.strip()) > 0
            assert output_forms != input_forms, 'Input and output forms for rule %s are the same!' % rid
            clean_input = lt.get_raw_analyzed_sentence(clean_xml(example))
            sent = disambiguate_until(rules, rid, lt.get_raw_analyzed_sentence(clean_xml(example)))
            disambiguated_sent = rule.replace(disambiguate_until(rules, rid,
                                                                 lt.get_raw_analyzed_sentence(clean_xml(example))))
            assert clean_input != disambiguated_sent, \
                'Disambiguated sentence is equal to the non-disambiguated sentence for rule: %s. ' \
                'The sentence was: %s' % (rid, sent)
            assert sent != disambiguated_sent, \
                'Disambiguated sentence is equal to the input sentence for rule: %s. ' \
                'The sentence was: %s' % (rid, sent)
            reading = ''
            annotations = ''
            for readings in sent.tokens:
                if readings.is_sentence_start and '<S>' not in input_forms:
                    continue
                if readings.start_pos == expected_start:
                    reading = AnalyzedSentence([readings]).to_short_string(',')
                    annotations = readings.historical_annotations
                    assert readings.start_pos == expected_start and readings.end_pos == expected_end, \
                        'Wrong marker position in the example for the rule %s: got %d-%d, expected %d-%d. ' \
                        "Sentence: '%s'" % (rid, readings.start_pos, readings.end_pos, expected_start,
                                            expected_end, sent)
                    break
            assert input_forms == sort_forms(reading), \
                'The input form for the rule %s in the example: %s is different than expected (expected %s but ' \
                'got %s). The token has been changed by the disambiguator: %s' % (
                    rid, example, input_forms, sort_forms(reading), annotations)
            for readings in disambiguated_sent.tokens:
                if readings.is_sentence_start and '<S>' not in output_forms:
                    continue
                if readings.start_pos == expected_start:
                    reading = AnalyzedSentence([readings]).to_short_string(',')
                    assert readings.start_pos == expected_start and readings.end_pos == expected_end
                    break
            assert output_forms == sort_forms(reading), \
                'The output form for the rule %s in the example: %s is different than expected (expected %s but ' \
                'got %s). The token has been changed by the disambiguator: %s' % (
                    rid, example, output_forms, sort_forms(reading), annotations)


def test_disambiguation_rule_tester(demo_lt):
    """The examples are also checked by langtool.testing.DisambiguationRuleTester"""
    from langtool.testing import DisambiguationRuleTester
    failures = DisambiguationRuleTester(demo_lt).run()
    assert not failures, '\n'.join(map(str, failures))
