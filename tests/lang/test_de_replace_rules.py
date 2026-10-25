"""Port of the tests of the German replacement and confusion rules
(org.languagetool.rules.de): GermanWrongWordInContextRuleTest,
WordCoherencyRuleTest, WiederVsWiderRuleTest and SimilarNameRuleTest
(Java has no test for SimpleReplaceRule; a check of it is added)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.replace_rules import (GermanWrongWordInContextRule, SimilarNameRule, SimpleReplaceRule,
                                            WiederVsWiderRule, WordCoherencyRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


# --- GermanWrongWordInContextRuleTest ---

def test_wrong_word_in_context(lt):
    """GermanWrongWordInContextRuleTest.testRule"""
    rule = GermanWrongWordInContextRule(None, get_language('de-DE'))

    def assert_good(sentence):
        assert len(rule.match(lt.get_analyzed_sentence(sentence))) == 0, sentence

    def assert_bad(sentence):
        assert len(rule.match(lt.get_analyzed_sentence(sentence))) == 1, sentence

    # Laiche/Leiche
    assert_bad('Eine Laiche ist ein toter Körper.')
    assert_good('Eine Leiche ist ein toter Körper.')
    assert_good('Die Leichen der Verstorbenen wurden ins Wasser geworfen.')
    # Mine/Miene
    assert_good('Er verzieht keine Miene.')
    assert_good('Er verzieht keine Miene.')
    assert_good('Die Explosion der Mine.')
    assert_good('Die Mine ist explodiert.')
    assert_good('Er versucht, keine Miene zu verziehen.')
    assert_good('Sie sollen weiter Minen eingesetzt haben.')
    assert_good('Er verzieht sich nach Bekanntgabe der Mineralölsteuerverordnung.')
    assert_bad('Er verzieht keine Mine.')
    assert_bad('Mit unbewegter Mine.')
    assert_bad('Er setzt eine kalte Mine auf.')
    assert_bad('Er sagt, die unterirdische Miene sei zusammengestürzt.')
    assert_bad('Die Miene ist eingestürzt.')
    assert_bad('Die Sprengung mit Mienen ist toll.')
    assert_bad('Der Bleistift hat eine Miene.')
    assert_bad('Die Mienen sind gestern Abend explodiert.')
    assert_bad('Die Miene des Kugelschreibers ist leer.')
    assert rule.match(lt.get_analyzed_sentence('Er hat das mit den Mienen weggesprengt.'))[0] \
        .suggested_replacements[0] == 'Minen'
    assert rule.match(lt.get_analyzed_sentence('Er versucht, keine Mine zu verziehen.'))[0] \
        .suggested_replacements[0] == 'Miene'
    # Neutron/Neuron
    assert_good('Nervenzellen nennt man Neuronen')
    assert_good('Das Neutron ist elektisch neutral')
    assert_bad('Atomkerne bestehen aus Protonen und Neuronen')
    assert_bad('Über eine Synapse wird das Neutron mit einer bestimmten Zelle verknüpft und nimmt mit der lokal '
               'zugeordneten postsynaptischen Membranregion eines Dendriten Signale auf.')
    assert rule.match(lt.get_analyzed_sentence('Protonen und Neuronen sind Bausteine des Atomkerns'))[0] \
        .suggested_replacements[0] == 'Neutronen'
    assert rule.match(lt.get_analyzed_sentence('Das Axon des Neutrons ...'))[0].suggested_replacements[0] == 'Neurons'
    # Wunde/Winde
    assert_good('Das Seil läuft durch eine Winde.')
    assert_good('Eine blutende Wunde')
    assert_bad('Es kamen Keime in die Winde.')
    assert_bad('Möglicherweise wehen die Wunde gerade nicht günstig.')
    # betäuben/bestäuben
    assert_good('Er war durch die Narkose betäubt.')
    assert_good('Die Biene bestäubt die Blume.')
    assert_bad('Den Kuchen mit Puderzucker betäuben.')
    assert_bad('Von Drogen bestäubt spürte er keine Schmerzen.')
    # ver(r)eisen
    assert_good('Er verreist stets mit leichtem Gepäck.')
    assert_good('Die Warze wurde vereist.')
    assert_bad('Nach Diktat vereist.')
    assert_bad('Die Tragfläche war verreist.')


# --- WordCoherencyRuleTest ---

@pytest.fixture(scope='module')
def coherency_lt():
    lt = JLanguageTool(get_language('de-DE'))
    # TestTools.disableAllRulesExcept(lt, "DE_WORD_COHERENCY")
    for rule in lt.get_all_rules():
        lt.disable_rule(rule.get_id())
    lt.enable_rule('DE_WORD_COHERENCY')
    return lt


def _coherency_matches(lt, s):
    rule = WordCoherencyRule(messages_for('en'), get_language('de-DE'))
    return rule.match(lt.analyze_text(s))


def test_word_coherency(coherency_lt):
    """WordCoherencyRuleTest.testRule"""
    lt = coherency_lt

    def assert_good(s):
        assert len(_coherency_matches(lt, s)) == 0, s

    def assert_error(s, expected_suggestion=None):
        matches = _coherency_matches(lt, s)
        assert len(matches) == 1, s
        if expected_suggestion is not None:
            assert matches[0].suggested_replacements == [expected_suggestion]

    # correct sentences:
    assert_good('Das ist aufwendig, aber nicht zu aufwendig.')
    assert_good('Das ist aufwendig. Aber nicht zu aufwendig.')
    assert_good('Das ist aufwändig, aber nicht zu aufwändig.')
    assert_good('Das ist aufwändig. Aber nicht zu aufwändig.')
    # errors:
    assert_error('Das ist aufwendig. Aufwändig ist das.', 'Aufwendig')
    assert_error('Das ist aufwendig, aber nicht zu aufwändig.')
    assert_error('Das ist aufwendig. Aber nicht zu aufwändig.')
    assert_error('Das ist aufwendiger, aber nicht zu aufwändig.')
    assert_error('Das ist aufwendiger. Aber nicht zu aufwändig.')
    assert_error('Das ist aufwändig, aber nicht zu aufwendig.')
    assert_error('Das ist aufwändig. Aber nicht zu aufwendig.')
    assert_error('Das ist aufwändiger, aber nicht zu aufwendig.')
    assert_error('Das ist aufwändiger. Aber nicht zu aufwendig.')
    assert_error('Delfin und Delphin')
    assert_error('Delfins und Delphine')
    assert_error('essentiell und essenziell')
    assert_error('essentieller und essenzielles')
    assert_error('Differential und Differenzial')
    assert_error('Differentials und Differenzials')
    assert_error('Facette und Fassette')
    assert_error('Facetten und Fassetten')
    assert_error('Joghurt und Jogurt')
    assert_error('Joghurts und Jogurt')
    assert_error('Joghurt und Jogurts')
    assert_error('Joghurts und Jogurts')
    assert_error('Ketchup und Ketschup')
    assert_error('Ketchups und Ketschups')
    assert_error('Kommuniqué und Kommunikee')
    assert_error('Kommuniqués und Kommunikees')
    assert_error('Necessaire und Nessessär')
    assert_error('Necessaires und Nessessärs')
    assert_error('Orthographie und Orthografie')
    assert_error('Orthographien und Orthografien')
    assert_error('Potential und Potenzial')
    assert_error('Potentials und Potenziale')
    assert_error('Portemonnaie und Portmonee')
    assert_error('Portemonnaies und Portmonees')
    assert_error('potentiell und potenziell')
    assert_error('potentielles und potenzieller')
    assert_error('Schenke und Schänke')
    assert_error('substantiell und substanziell')
    assert_error('substantieller und substanzielles')
    assert_error('Thunfisch und Tunfisch')
    assert_error('Thunfische und Tunfische')
    assert_error('Xylophon und Xylofon')
    assert_error('Xylophone und Xylofone')
    assert_error('selbständig und selbstständig')
    assert_error('selbständiges und selbstständiger')
    assert_error('Bahnhofsplatz und Bahnhofplatz')

    matches1 = lt.check('Eine aufwendige Untersuchung. Oder ist sie aufwändig?')
    assert len(matches1) == 1
    assert matches1[0].from_pos == 43
    assert matches1[0].to_pos == 52
    assert matches1[0].suggested_replacements == ['aufwendig']

    matches2 = lt.check('Eine aufwendige Untersuchung. Oder ist sie noch aufwändiger?')
    assert len(matches2) == 1
    assert matches2[0].from_pos == 48
    assert matches2[0].to_pos == 59
    assert matches2[0].suggested_replacements == ['aufwendiger']


def test_word_coherency_call_independence(coherency_lt):
    """WordCoherencyRuleTest.testCallIndependence"""
    assert len(_coherency_matches(coherency_lt, 'Das ist aufwendig.')) == 0
    # this won't be noticed, the calls are independent of each other
    assert len(_coherency_matches(coherency_lt, 'Aber nicht zu aufwändig.')) == 0


def test_word_coherency_match_position(coherency_lt):
    """WordCoherencyRuleTest.testMatchPosition"""
    rule_matches = coherency_lt.check('Das ist aufwendig. Aber nicht zu aufwändig')
    assert len(rule_matches) == 1
    assert rule_matches[0].from_pos == 33
    assert rule_matches[0].to_pos == 42


def test_word_coherency_complete_texts(coherency_lt):
    """WordCoherencyRuleTest.testRuleCompleteTexts"""
    lt = coherency_lt
    assert len(lt.check('Das ist aufwändig. Aber hallo. Es ist wirklich aufwändig.')) == 0
    assert len(lt.check('Das ist aufwendig. Aber hallo. Es ist wirklich aufwändig.')) == 1
    assert len(lt.check('Das ist aufwändig. Aber hallo. Es ist wirklich aufwendig.')) == 1
    # also find full forms:
    assert len(lt.check('Das ist aufwendig. Aber hallo. Es ist wirklich aufwendiger als so.')) == 0
    assert len(lt.check('Das ist aufwendig. Aber hallo. Es ist wirklich aufwändiger als so.')) == 1
    assert len(lt.check('Das ist aufwändig. Aber hallo. Es ist wirklich aufwendiger als so.')) == 1
    assert len(lt.check('Das ist das aufwändigste. Aber hallo. Es ist wirklich aufwendiger als so.')) == 1
    assert len(lt.check('Das ist das aufwändigste. Aber hallo. Es ist wirklich aufwendig.')) == 1
    # cross-paragraph checks
    assert len(lt.check('Das ist das aufwändigste.\n\nAber hallo. Es ist wirklich aufwendig.')) == 1


# --- WiederVsWiderRuleTest ---

def test_wieder_vs_wider(lt):
    """WiederVsWiderRuleTest.testRule"""
    rule = WiederVsWiderRule(messages_for('de'))

    def assert_good(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 0, text

    def assert_bad(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 1, text

    assert_good('Das spiegelt wider, wie es wieder läuft.')
    assert_good('Das spiegelt die Situation gut wider.')
    assert_good('Das spiegelt die Situation.')
    assert_good('Immer wieder spiegelt das die Situation.')
    assert_good('Immer wieder spiegelt das die Situation wider.')
    assert_good('Das spiegelt wieder wider, wie es läuft.')

    assert_bad('Das spiegelt wieder, wie es wieder läuft.')
    assert_bad('Sie spiegeln das Wachstum der Stadt wieder.')
    assert_bad('Das spiegelt die Situation gut wieder.')
    assert_bad('Immer wieder spiegelt das die Situation wieder.')
    assert_bad('Immer wieder spiegelte das die Situation wieder.')


# --- SimilarNameRuleTest ---

def test_similar_name(lt):
    """SimilarNameRuleTest.testRule"""
    rule = SimilarNameRule(messages_for('en'))

    def assert_errors(text, expected_matches):
        matches = rule.match([lt.get_analyzed_sentence(text)])
        assert len(matches) == expected_matches, text
        if expected_matches == 1:
            assert matches[0].rule.get_id() == 'DE_SIMILAR_NAMES'

    assert_errors('Hier steht Angela Müller. Im nächsten Satz dann Miller.', 1)
    assert_errors('Hier steht Angela Müller. Im nächsten Satz dann Müllers Ehemann.', 0)
    assert_errors('Hier steht Angela Müller. Dann Mulla, nicht ähnlich genug.', 0)
    assert_errors('Ein Mikrocontroller, bei Mikrocontrollern', 0)
    assert_errors('Hier steht das Rad Deiner Freundin. Und Deinem Hund geht es gut?', 0)


# --- SimpleReplaceRule (no Java test) ---

def test_simple_replace(lt):
    """SimpleReplaceRule: an entry of /de/replace.txt (not in Java's tests)"""
    rule = SimpleReplaceRule(messages_for('de'), get_language('de-DE'))
    assert rule.get_id() == 'DE_SIMPLE_REPLACE'
    # expected values from LanguageTool 6.6
    matches = rule.match(lt.get_analyzed_sentence('Ich mag Oscar Wild sehr.'))
    assert len(matches) == 1
    assert (matches[0].from_pos, matches[0].to_pos) == (8, 18)
    assert matches[0].suggested_replacements == ['Oscar Wilde']
    assert matches[0].rule.get_id() == 'DE_SIMPLE_REPLACE_OSCAR_WILD'
    assert matches[0].message == 'Meinten Sie vielleicht <suggestion>Oscar Wilde</suggestion>?'
    assert len(rule.match(lt.get_analyzed_sentence('Ich mag Oscar Wilde sehr.'))) == 0
