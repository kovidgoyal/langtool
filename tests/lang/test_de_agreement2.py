"""Port of org.languagetool.rules.de.AgreementRule2Test (the tests of
AgreementRule2, langtool.lang.de.agreement2)."""

import pytest

from conftest import require_dictionaries

from langtool.api import get_language
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(autouse=True, scope='module')
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def rule():
    from langtool.lang.de.agreement2 import AgreementRule2
    return AgreementRule2(messages_for('en'), get_language('de-DE'))


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


def assert_good(rule, lt, s):
    matches = rule.match(lt.get_analyzed_sentence(s))
    assert len(matches) == 0, s


def assert_bad(rule, lt, s, suggestion=None):
    matches = rule.match(lt.get_analyzed_sentence(s))
    assert len(matches) == 1, s
    if suggestion is not None:
        assert suggestion in matches[0].suggested_replacements, \
            'Got suggestions: %s, expected: %s' % (matches[0].suggested_replacements, suggestion)


def test_rule(rule, lt):
    """AgreementRule2Test.testRule"""
    assert_bad(rule, lt, "Kleiner Haus am Waldesrand")
    assert_good(rule, lt, "Kleines Haus am Waldesrand")
    assert_bad(rule, lt, "\"Kleiner Haus am Waldesrand\"")
    assert_good(rule, lt, "\"Kleines Haus am Waldesrand\"")
    assert_bad(rule, lt, "Wirtschaftlich Wachstum kommt ins Stocken")
    assert_good(rule, lt, "Wirtschaftliches Wachstum kommt ins Stocken")
    assert_good(rule, lt, "Unter Berücksichtigung des Übergangs")

    assert_good(rule, lt, "Wirklich Frieden herrscht aber noch nicht")
    assert_bad(rule, lt, "Deutscher Taschenbuch")
    assert_good(rule, lt, "Deutscher Taschenbuch Verlag expandiert")

    assert_good(rule, lt, "Wohl Anfang 1725 begegnete Bach dem Dichter.")
    assert_good(rule, lt, "Weniger Personal wird im ganzen Land gebraucht.")
    assert_good(rule, lt, "National Board of Review")   # eng
    assert_good(rule, lt, "International Management")   # eng.
    assert_good(rule, lt, "Gemeinsam Sportler anfeuern.")
    assert_good(rule, lt, "Viel Spaß beim Arbeiten")
    assert_good(rule, lt, "Ganz Europa stand vor einer Neuordnung.")
    assert_good(rule, lt, "Gesetzlich Versicherte sind davon ausgenommen.")
    assert_good(rule, lt, "Ausreichend Bananen essen.")
    assert_good(rule, lt, "Nachhaltig Yoga praktizieren")
    assert_good(rule, lt, "Überraschend Besuch bekommt er dann von ihr.")
    assert_good(rule, lt, "Ruhig Schlafen & Zentral Wohnen")
    assert_good(rule, lt, "Voller Mitleid")
    assert_good(rule, lt, "Voll Mitleid")
    assert_good(rule, lt, "Einzig Fernschüsse brachten Erfolgsaussichten.")
    assert_good(rule, lt, "Gelangweilt Dinge sortieren hilft als Ablenkung.")
    assert_good(rule, lt, "Ganzjährig Garten pflegen")
    assert_good(rule, lt, "Herzlich Willkommen bei unseren günstigen Rezepten!")
    assert_good(rule, lt, "10-tägiges Rückgaberecht")
    assert_good(rule, lt, "Angeblich Schüsse vor Explosionen gefallen")
    assert_good(rule, lt, "Dickes Danke auch an Elena")
    assert_good(rule, lt, "Dickes Dankeschön auch an Elena")
    assert_good(rule, lt, "Echt Scheiße")
    assert_good(rule, lt, "Entsprechende Automaten werden heute nicht mehr gebaut")
    assert_good(rule, lt, "Existenziell Bedrohte kriegen einen Taschenrechner")
    assert_good(rule, lt, "Flächendeckend Tempo 30")
    assert_good(rule, lt, "Frei Klavier spielen lernen")
    assert_good(rule, lt, "Ganz Eilige können es schaffen")
    assert_good(rule, lt, "Gering Gebildete laufen Gefahr ...")
    assert_good(rule, lt, "Ganz Ohr ist man hier")
    assert_good(rule, lt, "Gleichzeitig Muskeln aufbauen und Fett verlieren")
    assert_good(rule, lt, "Klar Schiff, Erster Offizier!")
    assert_good(rule, lt, "Kostenlos Bewegung schnuppern")
    assert_good(rule, lt, "Prinzipiell Anrecht auf eine Vertretung")
    assert_good(rule, lt, "Regelrecht Modell gestanden haben Michel")
    assert_good(rule, lt, "Weitgehend Konsens, auch über ...")
    assert_good(rule, lt, "Alarmierte Polizeibeamte nahmen den Mann fest.")
    assert_good(rule, lt, "Anderen Brot und Arbeit ermöglichen - das ist ihr Ziel")
    assert_good(rule, lt, "Diverse Unwesen, mit denen sich Hellboy beschäftigen muss, ...")
    assert_good(rule, lt, "Gut Qualifizierte bekommen Angebote")
    assert_good(rule, lt, "Liebe Mai, wie geht es dir?")
    assert_good(rule, lt, "Willkommen Simpsons-Fan!")


def test_suggestion(rule, lt):
    """AgreementRule2Test.testSuggestion"""
    # assertBad("Kleine Haus am Waldesrand", "Kleines Haus");
    # assertBad("Kleinen Haus am Waldesrand", "Kleines Haus");
    assert_good(rule, lt, "Kleinem Haus am Waldesrand ...")
    assert_bad(rule, lt, "Kleiner Haus am Waldesrand", "Kleines Haus")
    assert_bad(rule, lt, "Kleines Häuser am Waldesrand", "Kleine Häuser")
    assert_bad(rule, lt, "Kleinem Häuser am Waldesrand", "Kleine Häuser")
    # assertBad("Kleinen Häuser am Waldesrand", "Kleine Häuser");
    assert_bad(rule, lt, "Kleines Tisch reicht auch", "Kleiner Tisch")
    assert_good(rule, lt, "Junger Frau geht das Geld aus")
    assert_good(rule, lt, "Junge Frau gewinnt im Lotto")
    assert_bad(rule, lt, "Junges Frau gewinnt im Lotto", "Junge Frau")
    # assertBad("Jungen Frau gewinnt im Lotto", "Junge Frau");
    assert_bad(rule, lt, "Jungem Frau gewinnt im Lotto", "Junge Frau")
    assert_bad(rule, lt, "Jung Frau gewinnt im Lotto", "Junge Frau")
    assert_bad(rule, lt, "Wirtschaftlich Wachstum kommt ins Stocken", "Wirtschaftliches Wachstum")
    assert_bad(rule, lt, "Wirtschaftlicher Wachstum kommt ins Stocken", "Wirtschaftliches Wachstum")
    # assertBad("Wirtschaftliche Wachstum kommt ins Stocken", "Wirtschaftliches Wachstum");
