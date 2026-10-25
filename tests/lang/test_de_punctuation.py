"""Port of the tests of the German punctuation and typography rules:
org.languagetool.rules.de.GermanCommaWhitespaceRuleTest,
GenericUnpairedBracketsRuleTest, GermanUnpairedQuotesRuleTest,
SentenceWhitespaceRuleTest, DashRuleTest and UnitConversionRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.punctuation_rules import DashRule, GermanCommaWhitespaceRule, UnitConversionRule
from langtool.messages import messages_for
from langtool.rules.abstract_rules import GenericUnpairedQuotesRule
from langtool.rules.core import GenericUnpairedBracketsRule
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt_de_de():
    return JLanguageTool(get_language('de-DE'))


def _disable_all_rules_except(lt, *rule_ids):
    # TestTools.disableAllRulesExcept
    for rule in lt.get_all_rules():
        lt.disable_rule(rule.get_id())
    for rule_id in rule_ids:
        lt.enable_rule(rule_id)


def test_german_comma_whitespace_rule():
    """GermanCommaWhitespaceRuleTest.testRule"""
    rule = GermanCommaWhitespaceRule(messages_for('en'))
    rule.add_example_pair('Die Partei<marker> ,</marker> die die letzte Wahl gewann.',
                          'Die Partei<marker>,</marker> die die letzte Wahl gewann.')
    rule.url = 'http://fake'
    lt = JLanguageTool(get_language('de'))
    assert len(rule.match(lt.get_analyzed_sentence('Es gibt 5 Millionen .de-Domains.'))) == 0


def test_german_unpaired_brackets_rule(lt_de_de):
    """GenericUnpairedBracketsRuleTest.testGermanRule"""
    lt = lt_de_de
    # GenericUnpairedBracketsRuleTest.getBracketsRule(lt) of languagetool-core
    rule = next(r for r in lt.get_all_active_rules() if isinstance(r, GenericUnpairedBracketsRule))

    def assert_matches(text, expected_matches):
        assert len(rule.match([lt.get_analyzed_sentence(text)])) == expected_matches, text

    # correct sentences:
    assert_matches('(Das sind die Sätze, die sie testen sollen).', 0)
    assert_matches('(Das sind die {Sätze}, die sie testen sollen).', 0)
    assert_matches('(Das sind die [Sätze], die sie testen sollen).', 0)
    assert_matches('(Das sind die Sätze (noch mehr Klammern [schon wieder!]), die sie testen sollen).', 0)
    assert_matches('Das ist ein Satz mit Smiley :-)', 0)
    assert_matches('Das ist auch ein Satz mit Smiley ;-)', 0)
    assert_matches('Das ist ein Satz mit Smiley :)', 0)
    assert_matches('Das ist ein Satz mit Smiley :(', 0)
    assert_matches('Die URL lautet https://de.wikipedia.org/wiki/Schlammersdorf_(Adelsgeschlecht)', 0)
    assert_matches('Die URL lautet https://de.wikipedia.org/wiki/Schlammersdorf_(Adelsgeschlecht).', 0)
    assert_matches('(Die URL lautet https://de.wikipedia.org/wiki/Schlammersdorf_(Adelsgeschlecht))', 0)
    assert_matches('(Die URL lautet https://de.wikipedia.org/wiki/Schlammersdorf)', 0)
    assert_matches('(Die URL lautet https://de.wikipedia.org/wiki/Schlammersdorf oder so)', 0)
    assert_matches('(Die URL lautet: http://www.pariscinema.org/).', 0)
    # these used to have wrong positions, causing "Could not map ... to original position":
    lt.check('Im Kran­ken­haus. Auch)')
    lt.check('Ein Kran­ken­haus. Auch)')
    lt.check('Das Kran­ken­haus. Auch)')
    lt.check('Kran­ken­haus. Auch)')
    lt.check('Kran­ken­haus. (Auch')


def test_german_unpaired_quotes_rule(lt_de_de):
    """GermanUnpairedQuotesRuleTest.testGermanRule"""
    lt = lt_de_de
    # GenericUnpairedQuotesRuleTest.getQuotesRule(lt) of languagetool-core
    rule = next(r for r in lt.get_all_active_rules() if isinstance(r, GenericUnpairedQuotesRule))

    def assert_matches(text, expected_matches):
        assert len(rule.match([lt.get_analyzed_sentence(text)])) == expected_matches, text

    # correct sentences:
    assert_matches('»Das sind die Sätze, die sie testen sollen«.', 0)
    assert_matches('«Das sind die ‹Sätze›, die sie testen sollen».', 0)
    assert_matches('»Das sind die ›Sätze‹, die sie testen sollen«.', 0)
    assert_matches('»Das sind die Sätze ›noch mehr Anführungszeichen‹ ›schon wieder!‹, die sie testen sollen«.', 0)
    assert_matches('»Das sind die Sätze ›noch mehr Anführungszeichen ›hier ein Fehler!‹‹, die sie testen sollen«.', 2)
    assert_matches('„Das sind die Sätze ‚noch mehr Anführungszeichen‘ ‚schon wieder!‘, die sie testen sollen“.', 0)
    assert_matches('„Das sind die Sätze ‚noch mehr Anführungszeichen ‚hier ein Fehler!‘‘, die sie testen sollen“.', 2)
    assert_matches('„Das sind die Sätze, die sie testen sollen.“ „Hier steht ein zweiter Satz.“', 0)
    assert_matches('Drücken Sie auf den "Jetzt Starten"-Knopf.', 0)
    assert_matches('Welches ist dein Lieblings-"Star Wars"-Charakter?', 0)
    assert_matches("‚So 'n Blödsinn!‘", 0)
    assert_matches('‚’n Blödsinn!‘', 0)
    assert_matches("'So 'n Blödsinn!'", 0)
    assert_matches("''n Blödsinn!'", 0)
    assert_matches('‚Das ist Hans’.‘', 0)
    assert_matches("'Das ist Hans'.'", 0)
    assert_matches('Das Fahrrad hat 26" Räder.', 0)
    assert_matches('"Das Fahrrad hat 26" Räder."', 0)
    assert_matches('und steigern » Datenbankperformance steigern » Tipps zur Performance-Verbesserung', 0)
    # incorrect sentences:
    assert_matches('"Das Fahrrad hat 26" Räder." "Und hier fehlt das abschließende doppelte Anführungszeichen.', 1)
    assert_matches('Die „Sätze zum Testen.', 1)
    assert_matches('Die «Sätze zum Testen.', 1)
    assert_matches('Die »Sätze zum Testen.', 1)
    # these used to have wrong positions, causing "Could not map ... to original position":
    lt.check('Im Kran­ken­haus. Auch)')
    lt.check('Ein Kran­ken­haus. Auch)')
    lt.check('Das Kran­ken­haus. Auch)')
    lt.check('Kran­ken­haus. Auch)')
    lt.check('Kran­ken­haus. (Auch')


def test_sentence_whitespace_rule():
    """SentenceWhitespaceRuleTest.testMatch"""
    lt = JLanguageTool(get_language('de-DE'))
    _disable_all_rules_except(lt, 'DE_SENTENCE_WHITESPACE')

    def assert_good(text):
        assert len(lt.check(text)) == 0, text

    def assert_bad(text):
        assert len(lt.check(text)) == 1, text

    assert_good('Das ist ein Satz. Und hier der nächste.')
    assert_good('Das ist ein Satz! Und hier der nächste.')
    assert_good('Ist das ein Satz? Hier der nächste.')

    assert_bad('Das ist ein Satz.Und hier der nächste.')
    assert_bad('Das ist ein Satz!Und hier der nächste.')
    assert_bad('Ist das ein Satz?Hier der nächste.')

    assert_good('Am 28. September.')
    assert_bad('Am 28.September.')

    assert_good('Das 1. Internationale Filmfestival findet nächste Woche statt.')
    assert_bad('Das 1.Internationale Filmfestival findet nächste Woche statt.')

    assert 'nach Ordnungszahlen' in lt.check('Am 7.September 2014.')[0].message
    assert 'zwischen Sätzen' in lt.check('Im September.Dann der nächste Satz.')[0].message


def test_dash_rule(lt_de_de):
    """DashRuleTest.testRule"""
    rule = DashRule(messages_for('de'))
    lt = lt_de_de

    def assert_good(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 0, text

    def assert_bad(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 1, text

    # correct sentences:
    assert_good('Die große Diäten-Erhöhung kam dann doch.')
    assert_good('Die große Diätenerhöhung kam dann doch.')
    assert_good('Die große Diäten-Erhöhungs-Manie kam dann doch.')
    assert_good('Die große Diäten- und Gehaltserhöhung kam dann doch.')
    assert_good('Die große Diäten- sowie Gehaltserhöhung kam dann doch.')
    assert_good('Die große Diäten- oder Gehaltserhöhung kam dann doch.')
    assert_good('Erst so - Karl-Heinz dann blah.')
    assert_good('Erst so -- Karl-Heinz aber...')
    assert_good('Nord- und Südkorea')
    assert_good('NORD- UND SÜDKOREA')
    assert_good('NORD- BZW. SÜDKOREA')

    # incorrect sentences:
    assert_bad('Die große Diäten- Erhöhung kam dann doch.')
    assert_bad('Die große Diäten-  Erhöhung kam dann doch.')
    assert_bad('Die große Diäten-Erhöhungs- Manie kam dann doch.')
    assert_bad('Die große Diäten- Erhöhungs-Manie kam dann doch.')
    assert_bad('MAZEDONIEN- SKOPJE Str.')


def _assert_unit_matches(text, expected_matches, converted, rule, lt):
    # UnitConversionRuleTestHelper.assertMatches
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_matches, 'Got matches: %s' % matches
    if expected_matches > 0 and converted is not None:
        assert any(converted in s for s in matches[0].suggested_replacements), \
            'Suggestion is correct: %s / expected: %s' % (matches[0].suggested_replacements, converted)


def test_unit_conversion_rule():
    """UnitConversionRuleTest.match"""
    lt = JLanguageTool(get_language('de'))
    rule = UnitConversionRule(messages_for('de'))
    _assert_unit_matches('Ich bin 6 Fuß groß.', 1, '1,83 Meter', rule, lt)
    _assert_unit_matches('Ich bin 6 Fuß (2,02 m) groß.', 1, '1,83 Meter', rule, lt)
    _assert_unit_matches('Ich bin 6 Fuß (1,82 m) groß.', 0, None, rule, lt)
    _assert_unit_matches('Der Kostenvoranschlag hatte eine Höhe von 1.800 Pfund Sterling.', 0, None, rule, lt)
    _assert_unit_matches('Der Weg ist 100 Meilen lang.', 1, '160,93 Kilometer', rule, lt)
    _assert_unit_matches('Der Weg ist 10 km (20 Meilen) lang.', 1, '6,21', rule, lt)
    _assert_unit_matches('Der Weg ist 10 km (6,21 Meilen) lang.', 0, None, rule, lt)
    _assert_unit_matches('Der Weg ist 100 Meilen (160,93 Kilometer) lang.', 0, None, rule, lt)
    _assert_unit_matches('Die Ladung ist 10.000,75 Pfund schwer.', 1, '4,54 Tonnen', rule, lt)
    _assert_unit_matches('Sie ist 5\'6" groß.', 1, '1,68 m', rule, lt)
    _assert_unit_matches('Meine neue Wohnung ist 500 sq ft groß.', 1, '46,45 Quadratmeter', rule, lt)
    _assert_unit_matches("Zwischen 330'000 und 500'000/600", 0, None, rule, lt)
