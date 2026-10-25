"""Port of the tests of the German compound rules
(org.languagetool.rules.de): GermanCompoundRuleTest, SwissCompoundRuleTest
(with AbstractCompoundRuleTest.check), CompoundCoherencyRuleTest,
CompoundInfinitivRuleTest and ProhibitedCompoundRuleTest (with a fake
language model like Java's FakeLanguageModel; testListOfWords and
testMoreThanOneCandidate are @Ignore'd in Java)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.compound_rules import (CompoundCoherencyRule, CompoundInfinitivRule, GermanCompoundRule,
                                             ProhibitedCompoundRule, SwissCompoundRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


def _count(rule, lt, text):
    return len(rule.match(lt.get_analyzed_sentence(text)))


# --- GermanCompoundRuleTest, SwissCompoundRuleTest ---

def check(rule, lt, expected_errors, text, *exp_suggestions):
    """AbstractCompoundRuleTest.check"""
    rule_matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(rule_matches) == expected_errors, 'Expected %d error(s), but got: %s' % (expected_errors, rule_matches)
    if exp_suggestions:
        assert expected_errors == 1
        assert rule_matches[0].suggested_replacements == list(exp_suggestions)


def _run_tests(rule, lt):
    # correct sentences:
    check(rule, lt, 0, "Eine tolle CD-ROM")
    check(rule, lt, 0, "Eine tolle CD-ROM.")
    check(rule, lt, 0, "Ein toller CD-ROM-Test.")
    check(rule, lt, 0, "Systemadministrator")
    check(rule, lt, 0, "Eine Million Dollar")
    check(rule, lt, 0, "Das System des Administrators")
    check(rule, lt, 0, "Nur im Stand-by-Betrieb")
    check(rule, lt, 0, "Start, Ziel, Sieg")
    check(rule, lt, 0, "Roll-on-roll-off-Schiff")
    check(rule, lt, 0, "Halswirbelsäule")
    check(rule, lt, 0, "Castrop-Rauxel")
    check(rule, lt, 0, "2-Zimmer-Wohnung")
    check(rule, lt, 0, "3-Zimmer-Wohnung")
    check(rule, lt, 0, "Hals-Wirbel-Säule")
    check(rule, lt, 0, "Die Bürger konnten an die 900 Meter Kabel in Eigenregie verlegen.")
    check(rule, lt, 0, "Die Bürger konnten ca. 900 Meter Kabel in Eigenregie verlegen.")
    check(rule, lt, 0, "Aus dem Tank zapften die Diebe rund 250 Liter Diesel ab.")
    check(rule, lt, 0, "Aus dem Tank zapften die Diebe 250 Liter Diesel ab.")
    check(rule, lt, 0, "Lohnt sich die Werbung vom ausgegebenen Euro aus gedacht?")
    # incorrect sentences:
    check(rule, lt, 1, "System Administrator", "Systemadministrator")
    check(rule, lt, 1, "System-Administrator")
    check(rule, lt, 1, "bla bla bla bla bla System Administrator bla bla bla bla bla")
    check(rule, lt, 1, "System Administrator blubb")
    check(rule, lt, 1, "Der System Administrator")
    check(rule, lt, 1, "Der dumme System Administrator")
    check(rule, lt, 1, "CD ROM", "CD-ROM")
    check(rule, lt, 1, "Nur im Stand by Betrieb", "Stand-by-Betrieb")
    check(rule, lt, 1, "Ein echter Start Ziel Sieg", "Start-Ziel-Sieg")
    check(rule, lt, 1, "Ein echter Start Ziel Sieg.")
    check(rule, lt, 1, "Ein Start Ziel Sieg")
    check(rule, lt, 1, "Start Ziel Sieg")
    check(rule, lt, 1, "Start Ziel Sieg!")
    check(rule, lt, 1, "Doppler Effekt")
    check(rule, lt, 1, "3 Tage Woche")
    check(rule, lt, 1, "4 Tage Woche")
    check(rule, lt, 1, "5 Tage Woche")
    check(rule, lt, 1, "100 m Lauf")
    check(rule, lt, 1, "200 m Lauf")
    check(rule, lt, 1, "800 m Lauf")
    check(rule, lt, 1, "1000 m Lauf")
    check(rule, lt, 1, "2 Zimmer Wohnung")
    check(rule, lt, 1, "3 Zimmer-Wohnung")
    check(rule, lt, 1, "4-Zimmer Wohnung")
    check(rule, lt, 1, "5 Zimmer Wohnung")
    check(rule, lt, 1, "6 Zimmer Wohnung")
    check(rule, lt, 1, "1000 Jahr Feier")
    check(rule, lt, 1, "1000-Jahr Feier")
    check(rule, lt, 1, "1000 Jahr-Feier")
    check(rule, lt, 2, "Der dumme System Administrator legt die CD ROM")
    check(rule, lt, 2, "Der dumme System Administrator legt die CD ROM.")
    check(rule, lt, 2, "Der dumme System Administrator legt die CD ROM ein blah")
    check(rule, lt, 2, "System Administrator CD ROM")
    # check(2, "Hals Wirbel Säule");
    check(rule, lt, 1, "Und herum zu knobeln können.", "herumzuknobeln")
    check(rule, lt, 1, "Castrop Rauxel", "Castrop-Rauxel")
    # suggestion not on dictionary
    # check(1, "Roll on roll off Schiff", new String[]{"Roll-on-roll-off-Schiff"});
    check(rule, lt, 1, "Spin off")
    # no hyphen suggestion for some words:
    check(rule, lt, 1, "Das ist Haar sträubend", "Haarsträubend")
    # Only hyphen suggestion for some words:
    # suggestion not on dictionary
    # check(1, "Reality TV", "Reality-TV");
    check(rule, lt, 1, "Spin off", "Spin-off")
    # also accept incorrect upper/lowercase spelling:
    # check(1, "Spin Off", new String[]{"Spin-Off"});
    # check(1, "CW Wert", new String[]{"CW-Wert"});
    # also detect an error if only some of the hyphens are missing:
    # check(1, "Roll-on-roll-off Schiff", "Roll-on-roll-off-Schiff");
    check(rule, lt, 1, "Geräte Wahl", "Geräte-Wahl", "Gerätewahl")
    # first part is a single character:
    check(rule, lt, 0, "x-mal")
    check(rule, lt, 1, "x mal", "x-mal")
    check(rule, lt, 0, "y-Achse")
    check(rule, lt, 1, "y Achse", "y-Achse")
    # "Blu-ray-Brenner*"
    check(rule, lt, 0, "Blu-ray-Brenner")
    check(rule, lt, 1, "Blu ray Brenner", "Blu-ray-Brenner")
    # "nach-denken+"
    check(rule, lt, 0, "Ich muss nachdenken")
    check(rule, lt, 1, "Ich muss  nach denken", "nachdenken")
    # "Back-up$"
    check(rule, lt, 0, "Backup")
    check(rule, lt, 0, "Back-up")
    check(rule, lt, 1, "Back up", "Back-up", "Backup")
    # "Aggregat-Zustand?"
    check(rule, lt, 0, "Aggregatzustand")
    # check(0, "Aggregat-Zustand");
    check(rule, lt, 1, "Aggregat-Zustand", "Aggregatzustand")
    check(rule, lt, 1, "Aggregat Zustand", "Aggregatzustand")
    check(rule, lt, 1, "Billard Kugel", "Billardkugel")


def test_german_compound_rule(lt):
    """GermanCompoundRuleTest.testRule"""
    rule = GermanCompoundRule(messages_for('de'), get_language('de-DE'), None)
    _run_tests(rule, lt)
    rule = SwissCompoundRule(messages_for('de'), get_language('de-DE'), None)
    _run_tests(rule, lt)


def test_swiss_compound_rule(lt):
    """SwissCompoundRuleTest.testRule"""
    rule = SwissCompoundRule(messages_for('de'), get_language('de-DE'), None)
    # check(1, "Ente süss-sauer")
    check(rule, lt, 1, "Ente süß-sauer")
    # check(1, "Ente süss sauer")
    check(rule, lt, 1, "Ente süß sauer")


# --- CompoundCoherencyRuleTest ---

@pytest.fixture(scope='module')
def coherency():
    return CompoundCoherencyRule(messages_for('en')), JLanguageTool(get_language('de'))


def _coherency_matches(coherency, s1, s2):
    rule, lt = coherency
    return rule.match([lt.get_analyzed_sentence(s1), lt.get_analyzed_sentence(s2)])


def test_compound_coherency(coherency):
    """CompoundCoherencyRuleTest.testRule"""

    def assert_okay(s1, s2):
        matches = _coherency_matches(coherency, s1, s2)
        assert len(matches) == 0, 'Got %s' % matches

    def assert_error(s1, s2, from_pos, to_pos, suggestion):
        matches = _coherency_matches(coherency, s1, s2)
        assert len(matches) == 1, 'Got %s' % matches
        assert matches[0].from_pos == from_pos
        assert matches[0].to_pos == to_pos
        if suggestion is None:
            assert len(matches[0].suggested_replacements) == 0
        else:
            assert matches[0].suggested_replacements == [suggestion]

    assert_okay("Ein Jugendfoto.", "Und ein Jugendfoto.")
    assert_okay("Ein Jugendfoto.", "Der Rahmen eines Jugendfotos.")
    assert_okay("Der Rahmen eines Jugendfotos.", "Ein Jugendfoto.")
    assert_okay("Der Zahn-Ärzte-Verband.", "Der Zahn-Ärzte-Verband.")
    assert_okay("Der Zahn-Ärzte-Verband.", "Des Zahn-Ärzte-Verbands.")
    assert_okay("Der Zahn-Ärzte-Verband.", "Des Zahn-Ärzte-Verbandes.")
    assert_okay("Es gibt E-Mail.", "Und es gibt E-Mails.")
    assert_okay("Es gibt E-Mails.", "Und es gibt E-Mail.")
    assert_okay("Ein Jugend-Foto.", "Der Rahmen eines Jugend-Fotos.")

    assert_error("Ein Jugendfoto.", "Und ein Jugend-Foto.", 23, 34, "Jugendfoto")
    assert_error("Ein Jugend-Foto.", "Und ein Jugendfoto.", 24, 34, "Jugend-Foto")

    assert_error("Viele Zahn-Ärzte.", "Oder Zahnärzte.", 22, 31, None)
    assert_error("Viele Zahn-Ärzte.", "Oder Zahnärzte.", 22, 31, None)
    assert_error("Viele Zahn-Ärzte.", "Oder Zahnärzten.", 22, 32, None)

    assert_error("Der Zahn-Ärzte-Verband.", "Der Zahn-Ärzteverband.", 27, 44, "Zahn-Ärzte-Verband")
    assert_error("Der Zahn-Ärzte-Verband.", "Der Zahnärzte-Verband.", 27, 44, "Zahn-Ärzte-Verband")
    assert_error("Der Zahn-Ärzte-Verband.", "Der Zahnärzteverband.", 27, 43, "Zahn-Ärzte-Verband")
    assert_error("Der Zahn-Ärzteverband.", "Der Zahn-Ärzte-Verband.", 26, 44, "Zahn-Ärzteverband")
    assert_error("Der Zahnärzte-Verband.", "Der Zahn-Ärzte-Verband.", 26, 44, "Zahnärzte-Verband")
    assert_error("Der Zahnärzteverband.", "Der Zahn-Ärzte-Verband.", 25, 43, "Zahnärzteverband")

    assert_error("Der Zahn-Ärzte-Verband.", "Des Zahn-Ärzteverbandes.", 27, 46, None)
    assert_error("Der Zahn-Ärzte-Verband.", "Des Zahnärzte-Verbandes.", 27, 46, None)
    assert_error("Der Zahn-Ärzte-Verband.", "Des Zahnärzteverbandes.", 27, 45, None)


# --- CompoundInfinitivRuleTest ---

def test_compound_infinitiv():
    """CompoundInfinitivRuleTest.testRule"""
    german = get_language('de')
    rule = CompoundInfinitivRule(messages_for('de'), german, None)
    lt = JLanguageTool(german)

    assert _count(rule, lt, "Ich brachte ihn dazu, mein Zimmer sauber zu machen.") == 1
    assert _count(rule, lt, "Du brauchst nicht bei mir vorbei zu kommen.") == 1
    assert _count(rule, lt, "Ich ging zur Seite, um die alte Dame vorbei zu lassen.") == 1

    assert _count(rule, lt, "Seine Frau gab vor zu schlafen.") == 0
    assert _count(rule, lt, "Mein Herz hörte auf zu schlagen.") == 0
    assert _count(rule, lt, "Den Sonnenaufgang von einem Berggipfel aus zu sehen, ist eine Wonne.") == 0
    assert _count(rule, lt, "Hör auf zu schreien") == 0
    assert _count(rule, lt, "Sie riss sich zusammen und fing wieder an zu reden.") == 0
    assert _count(rule, lt, "Fang an zu zählen.") == 0
    assert _count(rule, lt, "Er hatte nichts weiter zu sagen") == 0
    assert _count(rule, lt, "Sie strengte sich an zu schwimmen.") == 0
    assert _count(rule, lt, "Er erhob sich von dem Stuhl, auf dem er gesessen hatte, und begann im Zimmer auf und ab "
                            "zu schreiten.") == 0
    assert _count(rule, lt, "Tom stand auf und fing an, auf und ab zu gehen.") == 0
    assert _count(rule, lt, "Aber um auf Nummer sicher zu gehen, schrieb er es auf.") == 0
    assert _count(rule, lt, "Sie scheint aus Spanien heraus zu kaufen.") == 0
    assert _count(rule, lt, "Hab keine Lust, mir Gedanken darüber zu machen.") == 0
    assert _count(rule, lt, "Fang an zu lesen, wo du aufgehört hast.") == 0
    assert _count(rule, lt, "Fang dort an zu lesen, wo du aufgehört hast.") == 0
    assert _count(rule, lt, "Der diensthabende Kollege hatte ganz schön zu tun.") == 0


# --- ProhibitedCompoundRuleTest ---

class FakeLanguageModel:
    """org.languagetool.languagemodel.FakeLanguageModel (getCount of single
    words from a map)"""

    def __init__(self, counts):
        self.counts = counts

    def get_count(self, token):
        return self.counts.get(token, 0)


_COUNTS = {
    'Mietauto': 100,
    'Leerzeile': 100,
    'Urberliner': 100,
    'Ureinwohner': 100,
    'Wohnungsleerstand': 50,
    'Xliseihflehrstand': 50,
    'Eisensande': 100,
    'Eisenstange': 101,
}


@pytest.fixture(scope='module')
def prohibited(lt):
    return ProhibitedCompoundRule(messages_for('en'), FakeLanguageModel(_COUNTS), None, lt.language)


def test_prohibited_compound(prohibited, lt):
    """ProhibitedCompoundRuleTest.testRule"""

    def assert_count(text, expected_matches):
        matches = prohibited.match(lt.get_analyzed_sentence(text))
        assert len(matches) == expected_matches, 'Got matches: %s' % matches

    def assert_matches(text, expected_marked_text, expected_suggestions):
        matches = prohibited.match(lt.get_analyzed_sentence(text))
        assert len(matches) == 1, 'Got matches: %s' % matches
        assert text[matches[0].from_pos:matches[0].to_pos] == expected_marked_text
        assert matches[0].suggested_replacements == [expected_suggestions]

    assert_matches("Er ist Uhrberliner.", "Uhrberliner", "Urberliner")
    assert_matches("Er ist Uhr-Berliner.", "Uhr-Berliner", "Urberliner")
    assert_matches("Das ist ein Mitauto.", "Mitauto", "Mietauto")
    assert_matches("Das ist ein Mit-Auto.", "Mit-Auto", "Mietauto")
    assert_count("Das ist Herr Mitauto.", 0)
    assert_matches("Hier leben die Uhreinwohner.", "Uhreinwohner", "Ureinwohner")
    assert_matches("Hier leben die Uhr-Einwohner.", "Uhr-Einwohner", "Ureinwohner")
    assert_count("Eine Leerzeile einfügen.", 0)
    assert_count("Eine Leer-Zeile einfügen.", 0)
    assert_matches("Eine Lehrzeile einfügen.", "Lehrzeile", "Leerzeile")
    assert_matches("Eine Lehr-Zeile einfügen.", "Lehr-Zeile", "Leerzeile")

    assert_count("Viel Wohnungsleerstand.", 0)
    assert_count("Viel Wohnungs-Leerstand.", 0)
    assert_matches("Viel Wohnungslehrstand.", "Wohnungslehrstand", "Wohnungsleerstand")
    assert_matches("Viel Wohnungs-Lehrstand.", "Wohnungs-Lehrstand", "Wohnungsleerstand")
    assert_count("Viel Xliseihfleerstand.", 0)
    assert_count("Viel Xliseihflehrstand.", 0)  # no correct spelling, so not suggested
    assert_count("Ein kosmografischer Test", 0)
    assert_count("Ein Elektrokardiograph", 0)
    assert_count("Die Elektrokardiographen", 0)

    assert_matches("Den Lehrzeile-Test einfügen.", "Lehrzeile", "Leerzeile")
    assert_matches("Die Test-Lehrzeile einfügen.", "Lehrzeile", "Leerzeile")
    assert_matches("Die Versuchs-Test-Lehrzeile einfügen.", "Lehrzeile", "Leerzeile")
    assert_matches("Den Versuchs-Lehrzeile-Test einfügen.", "Lehrzeile", "Leerzeile")


def test_remove_hyphens_and_adapt_case(prohibited):
    """ProhibitedCompoundRuleTest.testRemoveHyphensAndAdaptCase"""
    assert prohibited.remove_hyphens_and_adapt_case('Marathonläuse') is None
    assert prohibited.remove_hyphens_and_adapt_case('Marathon-Läuse') == 'Marathonläuse'
    assert prohibited.remove_hyphens_and_adapt_case('Marathon-Läuse-Test') == 'Marathonläusetest'
    assert prohibited.remove_hyphens_and_adapt_case('Marathon-läuse-test') == 'Marathonläusetest'
    assert prohibited.remove_hyphens_and_adapt_case('viele-Läuse-Test') == 'vieleläusetest'
    assert prohibited.remove_hyphens_and_adapt_case('S-Bahn') is None
