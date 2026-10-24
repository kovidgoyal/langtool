"""Port of org.languagetool.rules.ga.DhaNoBeirtRuleTest and
MorfologikIrishSpellerRuleTest (skipped, spell checking), plus checks of the
other Irish rules (their example pairs, IrishSpecificCaseRule,
DativePluralsData) and the Irish filters."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.ga.filters import IrishPartialPosTagFilter, NoDisambiguationIrishPartialPosTagFilter
from langtool.lang.ga.rules import (CompoundRule, DativePluralsData, DativePluralStandardReplaceRule, DhaNoBeirtRule,
                                    EnglishHomophoneRule, IrishFGBEqReplaceRule, IrishReplaceRule,
                                    IrishSpecificCaseRule, LogainmRule, PeopleRule, PrestandardReplaceRule,
                                    SpacesRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ga')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('ga'))


def _strip(example):
    return example.replace('<marker>', '').replace('</marker>', '')


def _marker(example):
    start = example.index('<marker>')
    return start, example.index('</marker>') - len('<marker>')


# --- DhaNoBeirtRuleTest ---

def test_dha_no_beirt(lt):
    """DhaNoBeirtRuleTest.testRule"""
    rule = DhaNoBeirtRule(messages_for('ga'))

    def assert_correct(sentence):
        assert len(rule.match(lt.get_analyzed_sentence(sentence))) == 0

    def assert_incorrect(sentence, expected):
        assert len(rule.match(lt.get_analyzed_sentence(sentence))) == expected

    assert_correct('Seo abairt bheag.')
    assert_correct('Tá beirt dheartháireacha agam.')
    assert_incorrect('Tá dhá dheartháireacha agam.', 1)
    assert_incorrect('Seo dhá ab déag', 2)
    # this next sentence is incorrect, just want a list of words between dhá and déag
    assert_incorrect('Tá dhá dheartháireacha níos aosta déag agam.', 2)


def test_dha_no_beirt_matches(lt):
    """positions and messages of DhaNoBeirtRule, including the quirks of the
    Java code (only the first number is reported, the replacement is looked
    up case sensitively)"""
    rule = DhaNoBeirtRule(messages_for('ga'))

    def matches(sentence):
        return [(m.from_pos, m.to_pos, m.message, m.short_message)
                for m in rule.match(lt.get_analyzed_sentence(sentence))]

    assert matches('Seo dhá ab déag') == [
        (4, 7, 'Ba chóir duit <suggestion>dháréag</suggestion> a scríobh', 'Uimhir phearsanta'),
        (11, 15, 'Ba chóir duit "déag" a scriosadh.', 'Uimhir phearsanta')]
    assert matches('Tá trí dheartháireacha agam.') == [
        (3, 6, 'Ba chóir duit <suggestion>triúr dheartháireacha</suggestion> a scríobh', 'Uimhir phearsanta')]
    assert matches('Tá dhá dheartháireacha agus trí dheartháireacha agam.') == [
        (3, 6, 'Ba chóir duit <suggestion>beirt dheartháireacha</suggestion> a scríobh', 'Uimhir phearsanta')]
    assert matches('Tá Trí dheartháireacha agam.') == [
        (3, 6, 'Ba chóir duit <suggestion>null dheartháireacha</suggestion> a scríobh', 'Uimhir phearsanta')]
    # the person must not be the last token (before the sentence end)
    assert matches('Tá dhá dheartháireacha') == []


@pytest.mark.skip(reason='spell checking is not ported: MorfologikIrishSpellerRuleTest tests the rule '
                         'MorfologikIrishSpellerRule')
def test_morfologik_speller():
    """Port of MorfologikIrishSpellerRuleTest.testMorfologikSpeller"""


# --- the example pairs of the rules ---

@pytest.mark.parametrize('cls', [CompoundRule, DativePluralStandardReplaceRule, DhaNoBeirtRule, EnglishHomophoneRule,
                                 IrishFGBEqReplaceRule, IrishReplaceRule, IrishSpecificCaseRule, PeopleRule,
                                 PrestandardReplaceRule])
def test_examples(lt, cls):
    lang = get_language('ga')
    messages = messages_for('ga')
    rule = cls(messages, lang, None) if cls is CompoundRule else cls(messages, lang)
    (wrong,) = rule.incorrect_examples
    (fixed,) = rule.correct_examples
    matches = rule.match(lt.get_analyzed_sentence(_strip(wrong.example)))
    assert len(matches) == 1
    assert (matches[0].from_pos, matches[0].to_pos) == _marker(wrong.example)
    start, end = _marker(fixed.example)
    suggestion = matches[0].suggested_replacements[0]
    if cls is DhaNoBeirtRule:
        # DhaNoBeirtRule suggests the number with the following word
        suggestion = suggestion.split(' ')[0]
    assert suggestion == fixed.example[start + len('<marker>'):end + len('<marker>')]
    assert rule.match(lt.get_analyzed_sentence(_strip(fixed.example))) == []


def test_simple_replace_rules(lt):
    lang = get_language('ga')
    messages = messages_for('ga')

    def match(rule, sentence):
        return [(m.from_pos, m.to_pos, m.message, m.short_message, m.suggested_replacements)
                for m in rule.match(lt.get_analyzed_sentence(sentence))]

    rule = LogainmRule(messages, lang)
    assert rule.url == 'https://www.logainm.ie/ga/'
    assert rule.category.id == 'TYPOS' and rule.loc_quality_issue_type == 'Misspelling'
    assert not rule.incorrect_examples
    # tagged words are ignored
    assert match(rule, 'Chuaigh mé go Dublin inné.') == []
    assert match(rule, 'Chuaigh mé go Adare inné.') == [
        (14, 19, 'Is logainm Béarla é "Adare" ar "Áth Dara".', 'Logainm Béarla', ['Áth Dara'])]
    # the word itself or its lowercase form must be listed
    assert match(rule, 'ADARE') == []
    rule = IrishReplaceRule(messages, lang)
    assert match(rule, 'AGUISIN') == [(0, 7, 'Litriú mícheart: "AGUISÍN".', 'Litriú mícheart', ['AGUISÍN'])]
    rule = DativePluralStandardReplaceRule(messages, lang)
    assert rule.category.id == 'TYPOS' and rule.loc_quality_issue_type == 'Grammar'
    # case sensitive
    assert match(rule, 'Mnáibh') == []
    assert match(rule, 'ar na cosaibh') == [
        (6, 13, 'Is litriú réamhchaighdeánach (tabharthach iolra) é "cosaibh"; an "cosa" a bhí i gceist agat?',
         'Tabharthach iolra', ['cosa'])]
    rule = SpacesRule(messages, lang)
    assert rule.ignore_tagged_words and not rule.incorrect_examples
    # case insensitive: an uppercase first letter is kept, all uppercase words get uppercase suggestions
    assert match(rule, 'Abheith') == [(0, 7, 'Spás ar iarraidh: "a bheith".', 'Spás ar iarraidh', ['A bheith'])]
    assert match(rule, 'ABHEITH') == [(0, 7, 'Spás ar iarraidh: "A BHEITH".', 'Spás ar iarraidh', ['A BHEITH'])]


def test_dative_plurals_data():
    """DativePluralsData: the simple replacements with the mutated forms and
    the modernisations"""
    repl = DativePluralsData.get_simple_replacements()
    assert repl['mnáibh'] == 'mná'
    assert repl['mhnáibh'] == 'mhná'
    assert repl['mbeachaibh'] == 'mbeacha'
    assert repl['háiteachaibh'] == 'háiteanna'
    assert repl['h-áiteachaibh'] == 'háiteanna'
    assert repl['n-áiteachaibh'] == 'n-áiteanna'
    assert repl['freumhaibh'] == 'fréamhacha'
    assert repl['fréamhaibh'] == 'fréamhacha'
    assert repl['bhfreumhaibh'] == 'bhfréamhacha'
    assert len(repl) == 125
    modern = DativePluralsData.get_modernisations()
    assert modern['búaibh'] == 'buaibh'
    # the mutated forms map to the mutated nominative plural (as in Java)
    assert modern['bhúaibh'] == 'bha'
    assert modern['freumhaibh'] == 'fréamhaibh'
    assert modern['fhreumhaibh'] == 'fhréamha'
    assert modern['húaislibh'] == 'huaislibh'
    assert len(modern) == 42


def test_specific_case(lt):
    rule = IrishSpecificCaseRule(messages_for('ga'))

    def match(sentence):
        return [(m.from_pos, m.to_pos, m.message, m.suggested_replacements)
                for m in rule.match(lt.get_analyzed_sentence(sentence))]

    assert rule.category.id == 'CASING'
    assert match('Rugadh agus tógadh i mbéal Feirste é.') == [
        (21, 34, 'Más ainmfhocal dílis é, scríobh é i gceannlitreacha.', ['mBéal Feirste'])]
    assert match('béal feirste atá ann.') == [
        (0, 12, 'Más ainmfhocal dílis é, scríobh é i gceannlitreacha.', ['Béal Feirste'])]
    # all uppercase (with Irish mutations) is accepted
    assert match('I MBÉAL FEIRSTE.') == []
    assert match('i mBÉAL FEIRSTE.') == []
    assert match('Rugadh i mBéal Feirste é.') == []


# --- filters ---

def _readings(tokens):
    return [(t.token, sorted(((r.lemma, r.pos_tag) for r in t.readings), key=str)) for t in tokens]


def test_partial_pos_tag_filters():
    assert _readings(NoDisambiguationIrishPartialPosTagFilter().tag('t-seomra')) == [
        ('t-seomra', [('seomra', 'Noun:Masc:Com:Sg:DefArt:MorphError'), (None, None)])]
    assert _readings(IrishPartialPosTagFilter().tag('haon')) == [
        ('haon', [('aon', 'Det:Qty:Idf:hPref'), ('aon', 'Noun:Masc:Com:Sg:hPref'), ('aon', 'Num:Card'),
                  ('aon', 'Num:Card:hPref')])]
