"""Port of org.languagetool.rules.de.OldSpellingRuleTest (OldSpellingRule
with SpellingData), plus a check of the Aho-Corasick hit order."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.old_spelling import AhoCorasickSearch, OldSpellingRule
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


@pytest.fixture(scope='module')
def rule():
    return OldSpellingRule(messages_for('de'), get_language('de-DE'))


def _suggestions(rule, lt, text):
    return rule.match(lt.get_analyzed_sentence(text))[0].suggested_replacements


def test_old_spelling(rule, lt):
    """OldSpellingRuleTest.test"""
    sentence1 = lt.get_analyzed_sentence('Ein Kuß')
    assert len(rule.match(sentence1)) == 1
    assert rule.match(sentence1)[0].suggested_replacements == ['Kuss']

    sentence2 = lt.get_analyzed_sentence('Das Corpus delicti')
    assert len(rule.match(sentence2)) == 1
    assert rule.match(sentence2)[0].suggested_replacements == ['Corpus Delicti']

    # inflected forms should work, too (as long as the inflection database still contains the old variants):
    sentence3 = lt.get_analyzed_sentence('In Rußlands Weiten')
    assert len(rule.match(sentence3)) == 1
    assert rule.match(sentence3)[0].suggested_replacements == ['Russlands']

    sentence4 = lt.get_analyzed_sentence('Hot pants')
    assert len(rule.match(sentence4)) == 1
    assert rule.match(sentence4)[0].suggested_replacements == ['Hotpants']

    sentence5 = lt.get_analyzed_sentence('Ich muß los')
    assert len(rule.match(sentence5)) == 1
    assert rule.match(sentence5)[0].suggested_replacements == ['muss']

    sentence6 = lt.get_analyzed_sentence('schwarzweißmalen')
    assert len(rule.match(sentence6)) == 1
    assert rule.match(sentence6)[0].suggested_replacements == ['schwarzweiß malen', 'schwarz-weiß malen']

    assert _suggestions(rule, lt, 'geschneuzt') == ['geschnäuzt']
    assert _suggestions(rule, lt, 'naß machen') == ['nassmachen']
    assert _suggestions(rule, lt, 'Midlife-crisis') == ['Midlife-Crisis', 'Midlifecrisis']
    assert _suggestions(rule, lt, 'Schluß') == ['Schluss']
    assert len(rule.match(lt.get_analyzed_sentence('schluß'))) == 0
    assert _suggestions(rule, lt, 'Schloß') == ['Schloss']
    assert _suggestions(rule, lt, 'radfahren') == ['Rad fahren']
    assert _suggestions(rule, lt, 'Photo') == ['Foto']
    assert _suggestions(rule, lt, 'Geschoß') == ['Geschoss']
    assert _suggestions(rule, lt, 'Erdgeschoß') == ['Erdgeschoss']
    assert _suggestions(rule, lt, 'Erdgeschoßes') == ['Erdgeschosses']

    def assert_no_match(text):
        matches = rule.match(lt.get_analyzed_sentence(text))
        assert not matches, "Unexpected match for '%s': %s" % (text, matches[0])

    def assert_match(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 1, text

    assert_no_match('In Russland')
    assert_no_match('In Russlands Weiten')
    assert_no_match('Schlüsse')
    assert_no_match('Schloß Holte')
    assert_no_match('in Schloß Holte')
    assert_no_match('Schloß Holte ist')
    assert_no_match('Asse')
    assert_no_match('Photons')  # not "Photo" substring match
    assert_no_match('Photon')
    assert_no_match('Des Photons')
    assert_no_match('Photons ')
    assert_no_match('Hallo Herr Naß')
    assert_no_match('Hallo Hr. Naß')
    assert_no_match('Hallo Frau Naß')
    assert_no_match('Hallo Fr. Naß')
    assert_no_match('Fr. Naß')
    assert_no_match('Dr. Naß')
    assert_no_match('Prof. Naß')
    assert_no_match('Bell Telephone')
    assert_no_match('Telephone Company')
    assert_match('Naß ist das Wasser')
    assert_match('Läßt du das bitte')
    assert_no_match('Das mögliche Bestehenbleiben')
    assert_no_match('Das mögliche Bloßstrampeln verhindern.')
    assert_match('Bloßstrampeln konnte er sich nicht.')


def test_german_at():
    """OldSpellingRuleTest.testGermanAT"""
    german_at = get_language('de-AT')
    rule = OldSpellingRule(messages_for('de'), german_at)
    lt = JLanguageTool(german_at)
    # this is a special case for Austria because of the pronunciation:
    assert len(rule.match(lt.get_analyzed_sentence('Geschoß'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Erdgeschoß'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Erdgeschoßes'))) == 0


def test_aho_corasick_hit_order():
    """AhoCorasickDoubleArrayTrie.parseText: hits by end position, for the
    same end position by descending keyword index"""
    search = AhoCorasickSearch([('he', 1), ('she', 2), ('hers', 3), ('e', 4)])
    assert search.parse_text('shers') == [(2, 3, 4), (0, 3, 2), (1, 3, 1), (1, 5, 3)]  # as in Java
