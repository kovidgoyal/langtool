"""Port of the tests of the German style and repetition rules
(language-de, org.languagetool.rules.de): GermanFillerWordsRuleTest,
GermanStyleRepeatedWordRuleTest, NonSignificantVerbsRuleTest,
UnnecessaryPhraseRuleTest, RedundantModalOrAuxiliaryVerbTest,
GermanRepeatedWordsRuleTest, LongSentenceRuleTest,
GermanParagraphRepeatBeginningRuleTest, GermanWordRepeatBeginningRuleTest,
GermanWordRepeatRuleTest and WordRepeatRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.repeat_rules import (GermanParagraphRepeatBeginningRule, GermanRepeatedWordsRule,
                                           GermanWordRepeatRule)
from langtool.lang.de.style_rules import (GermanFillerWordsRule, GermanStyleRepeatedWordRule, LongSentenceRule,
                                          NonSignificantVerbsRule, RedundantModalOrAuxiliaryVerb,
                                          UnnecessaryPhraseRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


def _set_up_rule(lt, rule):
    """setUpRule of the Java tests: disable all rules, add the rule and
    enable it"""
    for r in lt.get_all_rules():
        lt.disable_rule(r.get_id())
    lt.add_rule(rule)
    lt.enable_rule(rule.get_id())


# --- GermanFillerWordsRuleTest -----------------------------------------------

_FILLER_TEXT_3 = (
    'Der Text enthält zu wenige Füllwörter, daher werden sie nicht angezeigt. Was sich an diesem Satz mit diesem '
    'relativ einfachen Füllwort zeigt. Dazu müssen noch eine Reihe von Sätzen geschrieben werden, um die Anzahl der '
    'Wörter zu erhöhen. Langsam sollten die Anzahl der Worte für das Drücken unter die kritische Grenze reichen. '
    'Jetzt schreibe ich allerdings einen Satz, der drei Füllwörter enthält, was allemal ziemlich ausreichend ist.')
_FILLER_TEXT_2 = (
    'Der Text enthält zu wenige Füllwörter, daher werden sie nicht angezeigt. Was sich an diesem Satz mit diesem '
    'relativ einfachen Füllwort zeigt. Dazu müssen noch eine Reihe von Sätzen geschrieben werden, um die Anzahl der '
    'Wörter zu erhöhen. Langsam sollten die Anzahl der Worte für das Drücken unter die kritische Grenze reichen. '
    'Jetzt schreibe ich einen Satz, der zwei Füllwörter hintereinander enthält, was allemal ziemlich ausreichend '
    'ist.')
_FILLER_TEXT_4 = (
    'Der Text enthält zu wenige Füllwörter, daher werden sie nicht angezeigt. Was sich an diesem Satz mit diesem '
    'relativ einfachen Füllwort zeigt. Dazu müssen noch eine Reihe von Sätzen geschrieben werden, um die Anzahl der '
    'Wörter zu erhöhen. Langsam sollten die Anzahl der Worte für das Drücken unter die kritische Grenze reichen. '
    'Jetzt schreibe ich allerdings einen Satz, der vier Füllwörter enthält, was allemal ziemlich ausreichend ist.')


def test_filler_words_rule():
    """GermanFillerWordsRuleTest.testRule"""
    lang = get_language('de-DE')
    messages = messages_for('de')
    lt = JLanguageTool(lang)
    _set_up_rule(lt, GermanFillerWordsRule(messages, lang, None))
    # more than 8% filler words (default)
    assert len(lt.check('Der Satz enthält augenscheinlich ein Füllwort.')) == 1
    assert len(lt.check('Der Satz enthält augenscheinlich relativ viele Füllwörter.')) == 2
    # less than 8% filler words - don't show them
    assert len(lt.check('Der Satz enthält augenscheinlich ein Füllwort, aber es sind nicht genug um angezeigt zu '
                        'werden.')) == 0
    # direct speech or citation - don't show filler words
    assert len(lt.check('»Der Satz enthält augenscheinlich ein Füllwort«')) == 0
    # less than 8% filler words - but three in one sentence (show 3 instead of 4) <- don't show them per default
    assert len(lt.check(_FILLER_TEXT_3)) == 0
    # less than 8% filler words - but two consecutively (show 2 instead of 3) <- don't show them per default
    assert len(lt.check(_FILLER_TEXT_2)) == 0

    # percentage set to zero - show all filler words
    rule_values = {'FILLER_WORDS_DE': [0]}
    _set_up_rule(lt, GermanFillerWordsRule(messages, lang, dict(rule_values)))
    assert len(lt.check('»Der Satz enthält augenscheinlich ein Füllwort«')) == 1
    assert len(lt.check('Der Satz enthält augenscheinlich ein Füllwort, aber es sind nicht genug um angezeigt zu '
                        'werden.')) == 1

    rule_values['FILLER_WORDS_DE'] = [8, True, True, True]
    _set_up_rule(lt, GermanFillerWordsRule(messages, lang, dict(rule_values)))
    # direct speech or citation - show filler words because of option set
    assert len(lt.check('»Der Satz enthält augenscheinlich ein Füllwort«')) == 1
    # less than 8% filler words - but three in one sentence (show 3 instead of 4)
    assert len(lt.check(_FILLER_TEXT_4)) == 4
    # less than 8% filler words - but two consecutively (show 2 instead of 3)
    assert len(lt.check(_FILLER_TEXT_2)) == 3


# --- GermanStyleRepeatedWordRuleTest -----------------------------------------

def test_style_repeated_word_rule():
    """GermanStyleRepeatedWordRuleTest.testRule"""
    lang = get_language('de-DE')
    messages = messages_for('de')
    lt = JLanguageTool(lang)
    _set_up_rule(lt, GermanStyleRepeatedWordRule(messages, lang, {}))

    def n(text):
        return len(lt.check(text))
    assert n('Der alte Mann wohnte in einem großen Haus. Es stand in einem großen Garten.') == 2
    assert n('Der alte Mann wohnte in einem großen Haus. Es stand in einem weitläufigen Garten.') == 0
    assert n('Endlos lang zog sich der Ton dahin, aber schließlich verklang er doch.') == 0
    assert n('Die Au leuchtete im Blitz, die Glühwürmchen flimmerten vor Aufregung.') == 0
    assert n('Sie sind alle in der gleichen Art hergestellt. Nur bei einem Artefakt wurde eine andere '
             'Vorgehensweise angewandt.') == 0
    assert n('Ich erkannte keinen Lidschlag zu spät, dass es nicht in ihrer Absicht lag.') == 0
    assert n('Dieser Schritt brachte uns näher an die Lösung. Der nächste würde das Problem für immer aus der Welt '
             'schaffen.') == 0
    assert n('Er lehnte seinen Wanderstab gegen die Wand.') == 0
    assert n('Zweifel lagen in der Luft, ob es richtig war, diesen Weg einzuschlagen.') == 0
    assert n('Der Donnerhall verklang nur langsam in meinen Ohren. Das war mir in all den Jahren meines Lebens noch '
             'nicht passiert.') == 0
    assert n('Der Schiffsmotor, der im Heck des Schiffs eingebaut war, röhrte. Auf Hochtouren lief der Motor.') == 0
    assert n('Der Buntspecht stolzierte den Baum hoch. Schon klopfte der Specht.') == 0
    assert n('Rotbraun war die Farbe der Haselnuss. Der Horizont schimmerte rot.') == 0
    assert n("Rotbraun war die Farbe der Haselnuss. Was für eine 'Farbe'?") == 0
    assert n('Der Ausblick war überwätigend. "Was für ein Ausblick!", sagte sie auch prompt.') == 0
    assert n('Frau Heinrich stand unschlüssig in in ihrem Garten. Frau Müller schaute zu ihr herüber.') == 0

    # getRuleValues(1, false, true)
    _set_up_rule(lt, GermanStyleRepeatedWordRule(messages, lang,
                                                 {'STYLE_REPEATED_WORD_RULE_DE': [1, False, True]}))
    assert n('Der Schiffsmotor, der im Heck des Schiffs eingebaut war, röhrte. Auf Hochtouren lief der Motor.') == 3
    assert n('Der Buntspecht stolzierte den Baum hoch. Schon klopfte der Specht.') == 2
    assert n('Rotbraun war die Farbe der Haselnuss. Der Horizont schimmerte rot.') == 2
    assert n('Der Ausblick war überwätigend. "Was für ein Ausblick!", sagte sie auch prompt.') == 2


# --- NonSignificantVerbsRuleTest ---------------------------------------------

def test_non_significant_verbs_rule():
    """NonSignificantVerbsRuleTest.testRule"""
    lang = get_language('de-DE')
    lt = JLanguageTool(lang)
    _set_up_rule(lt, NonSignificantVerbsRule(messages_for('de'), lang, {}))
    assert len(lt.check('Wenn man das machen kann, sollte man das tun. Das ist so.')) == 3
    assert len(lt.check('Der Vorgang war abgeschlossen. Das hatte er nicht bedacht.')) == 0


# --- UnnecessaryPhraseRuleTest -----------------------------------------------

def test_unnecessary_phrase_rule():
    """UnnecessaryPhraseRuleTest.testRule"""
    lang = get_language('de-DE')
    lt = JLanguageTool(lang)
    _set_up_rule(lt, UnnecessaryPhraseRule(messages_for('de'), lang, {}))
    assert len(lt.check('In diesem Zusammenhang ist es im Allgemeinen voll und ganz zumindest mehr oder weniger '
                        'sinnvoll.')) == 4
    # exclude direct speach:
    assert len(lt.check('„In diesem Zusammenhang ist es im Allgemeinen voll und ganz zumindest mehr oder weniger '
                        'sinnvoll.“')) == 0
    assert len(lt.check('Es ist weniger sinnvoll.')) == 0


# --- RedundantModalOrAuxiliaryVerbTest ---------------------------------------

_REDUNDANT_MATCHES = (
    'Erst werde ich die Preise vergleichen und erst dann werde ich entscheiden, ob ich die Kamera kaufe.',
    'Sie hat das Foto von mir als kleinem Jungen angeschaut und hat gelacht.',
    'Ich bin gern in eurer Mitte und ich bin gern zu Gast bei euch.',
    'Da ich nun einmal bin, wer ich bin und was ich bin, kann ich es nicht übers Herz bringen.',
    'Wann ist jemand kühn und wann ist jemand tollkühn?',
    'Tom ist um halb drei angekommen und Mary ist kurze Zeit später angekommen.',
    'Das Essen ist gut und der Service hier ist gut.',
    'Wir müssen wissen, was wir tun sollen und wie wir es tun sollen.',
    'Ich muss unbedingt wissen, was zu tun ist, wie es zu tun ist und wann es zu tun ist.',
    'Er erzählte ihr, eine böse Hexe habe ihn in einen Frosch verwandelt und nur sie allein habe ihn retten können '
    'und morgen würden sie gemeinsam in sein Reich fahren.',
)
_REDUNDANT_NO_MATCHES = (
    '„nicht dürfen“ und „nicht müssen“ dürfen nicht miteinander verwechselt werden.',
    'Ich mag Physik und Mathematik mag ich noch mehr.',
    'Aus Angst vor den Zeitungen sind Politiker langweilig und am Ende sind sie selbst für die Zeitungen zu '
    'langweilig.',
    'Ändert der Akkusativ wirklich die Bedeutung eines Satzes: Sie hat Aids oder Aids hat sie?',
    'Tom hat eine Tüte Äpfel gekauft und er hat an einem Tag ein Drittel davon gegessen.',
    'Mein Vaterland ist mein Stadtviertel und nun ist es beinahe nicht wiedererkennbar.',
    'Johnny hat Alice vorgeschlagen und sie hat akzeptiert.',
    'Unsere Zeit hier ist begrenzt und sie ist wertvoll.',
    'Manchmal ist die Wahrheit nützlich und manchmal ist sie unnütz.',
    'Treue ist irgendwo absolut oder sie ist gar nichts.',
    'Sie mag niemanden und niemand mag sie.',
    'Eines Tages wird die USA eine Frau als Präsidenten wählen und das wird kein schönes Schauspiel sein.',
    'Mein Name ist Mary und das ist Tom.',
    'Er hat seine Augen langsam geöffnet und dann hat sie ihn geküsst.',
    'Die Flaneure haben es prinzipiell nicht eilig und sind immer für ein Schwätzchen zu haben.',
    'Es sind Tendenzen erkennbar und diese Tendenzen sind leider nicht ermutigend.',
    'Ja ist ja und nein ist nein, das nennt man Offenheit.',
    'Wie werden einmal unsere Namen hinter den Erfindern des Fliegens und dergleichen vergessen werden?',
    'In den Chroniken ist über die Flut von 1342 zu lesen, dass im Mainzer Dom einem Mann das Wasser bis zur Brust '
    'gestanden habe und dass man in Köln mit Booten über die Stadtmauern habe fahren können.',
    'Sie stellt sicher, dass die gerissenen Bänder nicht belastet werden können und dass das Gelenk dennoch bewegt '
    'werden kann.',
)


def test_redundant_modal_or_auxiliary_verb():
    """RedundantModalOrAuxiliaryVerbTest.testRule"""
    lang = get_language('de-DE')
    lt = JLanguageTool(lang)
    _set_up_rule(lt, RedundantModalOrAuxiliaryVerb(messages_for('de')))
    for text in _REDUNDANT_MATCHES:
        assert len(lt.check(text)) == 1, text
    for text in _REDUNDANT_NO_MATCHES:
        assert len(lt.check(text)) == 0, text


# --- GermanRepeatedWordsRuleTest ---------------------------------------------

def test_repeated_words_rule():
    """GermanRepeatedWordsRuleTest.testRule"""
    rule = GermanRepeatedWordsRule(messages_for('de'))
    lt = JLanguageTool(get_language('de'))

    def matches(text):
        return rule.match(lt.analyze_text(text))
    assert len(matches('Lauf so schnell wie möglich. Das ist MÖGLICH!')) == 0
    m = matches('Das ist hervorragende Arbeit. Die Ergebnisse sind hervorragend.')
    assert len(m) == 1
    assert m[0].suggested_replacements == ['brillant', 'exzellent', 'perfekt', 'fantastisch', 'traumhaft']


# --- LongSentenceRuleTest ----------------------------------------------------

def test_long_sentence_rule():
    """LongSentenceRuleTest.testMatch (de)"""
    lt = JLanguageTool(get_language('de-DE'))
    rule = LongSentenceRule(messages_for('de'), None, {}, 6)

    def assert_no_match(text):
        assert len(rule.match(lt.analyze_text(text))) == 0, text

    def assert_match(text, from_pos, to_pos):
        m = rule.match(lt.analyze_text(text))
        assert len(m) == 1, text
        assert (m[0].from_pos, m[0].to_pos) == (from_pos, to_pos)
    assert_no_match('Eins zwei drei vier fünf sechs.')
    # Words after colon are treated like a separate sentence
    assert_no_match('Ich zähle jetzt: "Eins zwei drei vier fünf sechs."')
    assert_no_match('Peter, bist du bereit?” Er nickte nur.\n')
    assert_no_match('Peter, du bist bereit.” Er nickte nur.\n')
    assert_no_match('Eins zwei drei vier fünf (sechs sieben) acht.')

    assert_match('Eins zwei drei vier fünf sechs sieben.', 0, 38)
    assert_match('Eins zwei drei vier fünf (sechs sieben) acht neun.', 0, 50)
    assert_match('Ich zähle jetzt: Eins zwei drei vier fünf sechs sieben.', 0, 55)
    assert_match('Ein Satz. Eins zwei drei vier fünf sechs sieben.', 10, 48)


# --- GermanParagraphRepeatBeginningRuleTest ----------------------------------

def test_paragraph_repeat_beginning_rule():
    """GermanParagraphRepeatBeginningRuleTest.testRule"""
    lang = get_language('de-DE')
    lt = JLanguageTool(lang)
    _set_up_rule(lt, GermanParagraphRepeatBeginningRule(messages_for('de'), lang))
    assert len(lt.check('Der Hund spazierte über die Straße.\n\nDer Hund ignorierte den Verkehr.')) == 2
    assert len(lt.check('Der Hund spazierte über die Straße.\n\nDas Tier ignorierte den Verkehr.')) == 0
    assert len(lt.check('Peter spazierte über die Straße.\n\nPeter ignorierte den Verkehr.')) == 2
    assert len(lt.check('Peter spazierte über die Straße.\n\nDer Junge ignorierte den Verkehr.')) == 0
    assert len(lt.check('»Peter spazierte über die Straße.«\n\n»Peter ignorierte den Verkehr.«')) == 2


# --- GermanWordRepeatBeginningRuleTest ---------------------------------------

def test_word_repeat_beginning_rule():
    """GermanWordRepeatBeginningRuleTest.testRule"""
    lt = JLanguageTool(get_language('de-DE'))
    lt.disable_rule('DE_REPEATEDWORDS')
    # correct sentences:
    assert len(lt.check('Er ist nett. Er heißt Max.')) == 0
    assert len(lt.check('Außerdem kommt er. Ferner kommt sie. Außerdem kommt es.')) == 0
    assert len(lt.check('2011: Dieses passiert. 2011: Jenes passiert. 2011: Nicht passiert')) == 0
    # errors:
    assert len(lt.check('Er ist nett. Er heißt Max. Er ist 11.')) == 1
    assert len(lt.check('Außerdem kommt er. Außerdem kommt sie.')) == 1
    # this used to cause false alarms because reset() was not implemented
    assert len(lt.check('Außerdem ist das ein neuer Text.')) == 0
    # only consider 'real' sentences that end in [.!?]:
    assert len(lt.check('Außerdem ist das ein neuer Text\n\nAußerdem noch mehr ohne Punkt\n\nAußerdem schon '
                        'wieder')) == 0


# --- GermanWordRepeatRuleTest, WordRepeatRuleTest ----------------------------

def test_german_word_repeat_rule():
    """GermanWordRepeatRuleTest.testRule"""
    german = get_language('de')
    rule = GermanWordRepeatRule(messages_for('en'), german)
    lt = JLanguageTool(german)

    def n(text):
        return len(rule.match(lt.get_analyzed_sentence(text)))
    assert n('Das ist gut so.') == 0
    assert n('Das ist ist gut so.') == 1
    assert n('Der der Mann') == 1
    assert n('Warum fragen Sie sie nicht selbst?') == 0
    assert n('Er will nur sein Leben leben.') == 0
    assert n('Wie bei Honda, die die Bezahlung erhöht haben.') == 0
    assert n('Dann warfen sie sie weg.') == 0
    assert n('Dann konnte sie sie sehen.') == 0
    assert n('Er muss sein Essen essen.') == 0
    assert n('Wahrscheinlich ist das das Problem.') == 0
    assert n('Dann wäre das das erste Wirtschaftsmagazin mit mehr als 10.000 Lesern.') == 0
    assert n('Für mich war das das Härteste.') == 0
    assert n('Ich weiß, wer wer ist!') == 0
    assert n('Ich kann das machen, falls das das Problem ist.') == 0
    assert n('Als ich das das erste Mal gehört habe …') == 0
    assert n('Hat sie sie') == 1  # used to crash, issue #1010
    assert n('Hat hat') == 1
    assert n('hat hat') == 1


def test_word_repeat_rule_german():
    """WordRepeatRuleTest.testRuleGerman (de)"""
    german = get_language('de-DE')
    rule = GermanWordRepeatRule(messages_for('en'), german)
    lt = JLanguageTool(german)

    def n(text):
        return len(rule.match(lt.get_analyzed_sentence(text)))
    assert n('Das sind die Sätze, die die testen sollen.') == 0
    assert n('Sätze, die die testen.') == 0
    assert n('Das Haus, auf das das Mädchen zeigt.') == 0
    assert n('Warum fragen Sie sie nicht selbst?') == 0
    assert n('Er tut das, damit sie sie nicht sieht.') == 0

    assert n('Die die Sätze zum testen.') == 1
    assert n('Und die die Sätze zum testen.') == 1
    assert n('Auf der der Fensterbank steht eine Blume.') == 1
    assert n('Das Buch, in in dem es steht.') == 1
    assert n('Das Haus, auf auf das Mädchen zurennen.') == 1
    assert n('Sie sie gehen nach Hause.') == 1
