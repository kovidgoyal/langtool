"""Port of org.languagetool.rules.de.MissingCommaRelativeClauseRuleTest"""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.comma_rules import MissingCommaRelativeClauseRule
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


def _assert_no_match(rule, lt, text):
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == 0, (text, [(m.from_pos, m.to_pos) for m in matches])


def _assert_match(rule, lt, text, from_pos, to_pos):
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == 1, (text, [(m.from_pos, m.to_pos) for m in matches])
    assert (matches[0].from_pos, matches[0].to_pos) == (from_pos, to_pos), text


def test_match():
    """MissingCommaRelativeClauseRuleTest.testMatch"""
    lt = JLanguageTool(get_language('de-DE'))
    rule = MissingCommaRelativeClauseRule(messages_for('de'))

    _assert_match(rule, lt, "Das Auto das am Straßenrand steht parkt im Halteverbot.", 4, 12)
    _assert_match(rule, lt, "Das Auto das am Straßenrand steht, parkt im Halteverbot.", 4, 12)
    _assert_match(rule, lt, "Das Auto in dem der Mann sitzt, parkt im Halteverbot.", 4, 15)
    _assert_match(rule, lt, "Das Auto in dem der Mann sitzt parkt im Halteverbot.", 4, 15)
    _assert_match(rule, lt, "Die Frau die vor dem Auto steht hat schwarze Haare.", 4, 12)
    _assert_match(rule, lt, "Die Frau die vor dem Auto steht, hat schwarze Haare.", 4, 12)
    _assert_match(rule, lt, "Alles was ich habe, ist ein Buch.", 0, 9)
    _assert_no_match(rule, lt, "Computer machen die Leute dumm.")
    _assert_no_match(rule, lt, "Die Unstimmigkeit zwischen den Geschichten der zwei Unfallbeteiligten war groß.")
    _assert_no_match(rule, lt, "Ebenso darf keine schwerere Strafe als die zum Zeitpunkt der Begehung der strafbaren "
                               "Handlung angedrohte Strafe verhängt werden.")
    _assert_no_match(rule, lt, "Als dritte Gruppe lassen sich Aminosäuren fassen, die der Organismus anstelle dieser "
                               "in Proteine einbaut.")
    _assert_no_match(rule, lt, "Selbst wenn das alles perfekt verlustfrei wäre, hätte ich nichts gewonnen.")
    _assert_no_match(rule, lt, "Die Studenten, deren Urteil am stärksten von dem der Profis abwich, waren sich "
                               "sicher, einen guten von einem schlechten unterscheiden zu können.")
    _assert_no_match(rule, lt, "Die Studenten, deren Urteil am stärksten durch das der Profis beeinflusst wurde, "
                               "waren sich sicher, einen guten von einem schlechten unterscheiden zu können.")

    rule = MissingCommaRelativeClauseRule(messages_for('de'), behind=True)

    _assert_match(rule, lt, "Das Auto, das am Straßenrand steht parkt im Halteverbot.", 29, 40)
    _assert_match(rule, lt, "Das Auto, in dem der Mann sitzt parkt im Halteverbot.", 26, 37)
    _assert_match(rule, lt, "Die Frau, die vor dem Auto steht hat schwarze Haare.", 27, 36)
    _assert_match(rule, lt, "Alles, was ich habe ist ein Buch.", 15, 23)
    _assert_match(rule, lt, "In diesem Prozess sind aber Entwicklungsschritte ja integriert, die wir Psychiater "
                            "glaube ich auch gut kennen.", 72, 93)
    _assert_match(rule, lt, "Alles, was du für die Spieße brauchst sind Tortellini, getrocknete Tomaten, "
                            "Cherrytomaten und Mozzarellakugeln.", 29, 42)
    _assert_no_match(rule, lt, ".... das war eher so das, was alle im Browser deaktiviert hatten, weil man dachte, "
                               "über Javascript wird irgendwie Schadsoftware eingeschleust.")
    _assert_no_match(rule, lt, "Ich habe einige Fehler begangen, die ich vermeiden hätte können sollen.")
    _assert_no_match(rule, lt, "Doch die Rolle, die Mohammed bin Salman in Riad spielt, ist zwiespältig.")
    _assert_no_match(rule, lt, "Laut Josef Peter Burg gehörte das Haus, aus dem er samt Familie geworfen wurde, "
                               "Werner und Sigrid Bahlke, während er darin wohnte und darauf aufpasste.")
    _assert_no_match(rule, lt, "Darüber hinaus stellt die klassische Metaphysik eine Grundfrage, die sich etwa wie "
                               "folgt formulieren lässt: Warum ist überhaupt Seiendes und nicht vielmehr Nichts?")
    _assert_no_match(rule, lt, "Wenn du alles, was du meinst nicht zu können, von anderen erledigen lässt, wirst du "
                               "es niemals selbst lernen.")
    _assert_no_match(rule, lt, "Er hat einen Zeitraum durchlebt, in dem seine Gedanken verträumt auf den weiten "
                               "Feldern der Mysterien umherirrten.")
    _assert_no_match(rule, lt, "Es ist die Wiederkehr der Panikmache, die der neue Nationalismus mit dem der "
                               "Sprachreiniger verbindet und die Geschichte der Sprachreinigung zu einem Lehrstück "
                               "macht.")
    _assert_no_match(rule, lt, "Gesuche können von Institutionen, Organisationen, Vereinen und Gruppierungen gestellt "
                               "werden, die im Kanton Luzern domiziliert sind.")
    _assert_no_match(rule, lt, "Die Klausel kann zudem nur Gleichrang mit Verbindlichkeiten des Schuldners "
                               "herstellen, die vom Gesetz in der Insolvenz nicht privilegiert sind, so dass die "
                               "Klausel nichts an der gesetzlich vorgesehenen Rangfolge im Insolvenzverfahren ändert.")
    _assert_no_match(rule, lt, "Plan von Maßnahmen, mit denen das Ansteckungsrisiko während des Aufenthalts an einem "
                               "Ort verringert werden soll")
    _assert_no_match(rule, lt, "Aus diesem Grund sind die Wörter nicht direkt übersetzt, stattdessen wird der Zustand "
                               "oder die Situation beschrieben in der die Wörter benutzt werden.")
    _assert_no_match(rule, lt, "Kryptographisch sichere Verfahren sind dann solche, für die es keine bessere Methode "
                               "zum Brechen der Sicherheit als das Faktorisieren einer großen Zahl gibt, insbesondere "
                               "kann der private nicht aus dem öffentlichen Schlüssel errechnet werden.")
    _assert_no_match(rule, lt, "Wayne Jancik begrenzt seine One-Hit-Wonders in den USA auf die "
                               "Billboard-Top-40-Pop-Hitparade mit einer „Ruhe-Periode“ von 5 Jahren, innerhalb derer "
                               "kein weiterer Hit desselben Interpreten in die Top 40 gelangen darf.")
    _assert_no_match(rule, lt, "Nach dem Abzug russischer Truppen aus der Region Kiew sind in den ehemals besetzten "
                               "und umkämpften ukrainischen Gebieten inzwischen Hunderte Leichen von Bewohnern "
                               "gefunden worden.")
    _assert_no_match(rule, lt, "Bei der Installation werden Ihnen Sticker und Aufkleber zur Verfügung gestellt, die "
                               "Sie anstelle der traditionellen Emojis verwenden können.")
    _assert_no_match(rule, lt, "»Alles, was wir dank dieses Projektes sehen werden, wird für uns neu sein«, so der "
                               "renommierte Bienenforscher.")
