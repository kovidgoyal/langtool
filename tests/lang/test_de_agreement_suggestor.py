"""Port of org.languagetool.rules.de.AgreementSuggestor2Test (the tests of
AgreementSuggestor2, langtool.lang.de.agreement_suggestor)."""

import pytest

from conftest import require_dictionaries

from langtool.api import get_language
from langtool.lang.de.agreement_suggestor import AgreementSuggestor2, REPLACEMENT_INS, REPLACEMENT_ZUR
from langtool.tool import JLanguageTool


@pytest.fixture(autouse=True, scope='module')
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


@pytest.fixture(scope='module')
def synthesizer():
    return get_language('de-DE').synthesizer


def _str(suggestions):
    """List.toString()"""
    return '[' + ', '.join(suggestions) + ']'


def assert_suggestion1(lt, synthesizer, input, expected_suggestions, filter=False):
    tags = lt.get_analyzed_sentence(input).get_tokens_without_whitespace()
    assert len(tags) == 3, 'Please use 2 tokens (det, noun) as input: ' + input  # 2 tokens + sentence start token
    suggestor = AgreementSuggestor2(synthesizer, tags[1], tags[2], None)
    assert _str(suggestor.get_suggestions(filter)) == expected_suggestions


def assert_suggestion2(lt, synthesizer, input, expected_suggestions):
    tags = lt.get_analyzed_sentence(input).get_tokens_without_whitespace()
    assert len(tags) == 4, 'Please use 3 tokens (det, adj, noun) as input: ' + input  # 3 tokens + sentence start
    suggestor = AgreementSuggestor2(synthesizer, tags[1], tags[2], tags[3], None)
    assert _str(suggestor.get_suggestions()) == expected_suggestions


def assert_suggestion3(lt, synthesizer, input, expected_suggestions, filter):
    tags = lt.get_analyzed_sentence(input).get_tokens_without_whitespace()
    assert len(tags) == 5, 'Please use 4 tokens (det, adj, adj, noun) as input: ' + input  # 4 tokens + sentence start
    suggestor = AgreementSuggestor2(synthesizer, tags[1], tags[2], tags[3], tags[4], None)
    assert _str(suggestor.get_suggestions(filter)) == expected_suggestions


def test_interactive(lt, synthesizer):
    """AgreementSuggestor2Test.testInteractive"""
    # assertSuggestion1("des Züchten", "[das Züchten, dem Züchten, des Züchtens]");
    pass


def test_adverb_suggestions(lt, synthesizer):
    """AgreementSuggestor2Test.testAdverbSuggestions"""
    assert_suggestion3(lt, synthesizer, "ein sehr schönes Tisch", "[ein sehr schöner Tisch]", True)
    assert_suggestion3(lt, synthesizer, "eines sehr schönen Tisch", "[einen sehr schönen Tisch, einem sehr schönen Tisch, eines sehr schönen Tischs, eines sehr schönen Tisches]", True)
    assert_suggestion3(lt, synthesizer, "der sehr schönen Tischen", "[dem sehr schönen Tischen, den sehr schönen Tischen, der sehr schönen Tische]", True)


def test_suggestions(lt, synthesizer):
    """AgreementSuggestor2Test.testSuggestions"""
    assert_suggestion1(lt, synthesizer, "deine Buch", "[dein Buch, deinem Buch, deine Bücher, deinem Buche, deines Buchs, deines Buches, deiner Bücher, deinen Büchern]")
    assert_suggestion1(lt, synthesizer, "dieser Buch", "[dieses Buch, diesem Buch, dies Buch, dieser Bücher, diesem Buche, dieses Buchs, dieses Buches, diese Bücher, diesen Büchern]")
    assert_suggestion1(lt, synthesizer, "die Kabels", "[die Kabel, des Kabels, der Kabel, den Kabel, dem Kabel, das Kabel, den Kabeln]")
    assert_suggestion1(lt, synthesizer, "die LAN-Kabels", "[die LAN-Kabel, des LAN-Kabels, der LAN-Kabel, den LAN-Kabel, dem LAN-Kabel, das LAN-Kabel, den LAN-Kabeln]")
    assert_suggestion1(lt, synthesizer, "mehrere Kabels", "[mehrere Kabel, mehreren Kabeln, mehrerer Kabel]")
    assert_suggestion1(lt, synthesizer, "mehrere LAN-Kabels", "[mehrere LAN-Kabel, mehreren LAN-Kabeln, mehrerer LAN-Kabel]")
    assert_suggestion1(lt, synthesizer, "mehrere WLAN-LAN-Kabels", "[mehrere WLAN-LAN-Kabel, mehreren WLAN-LAN-Kabeln, mehrerer WLAN-LAN-Kabel]")
    assert_suggestion1(lt, synthesizer, "Ihren Verständnis", "[Ihrem Verständnis, Ihr Verständnis, Ihres Verständnisses]")
    assert_suggestion1(lt, synthesizer, "des Züchten", "[das Züchten, dem Züchten, des Züchtens]")
    assert_suggestion1(lt, synthesizer, "die Kühlschranktest", "[die Kühlschrankteste, die Kühlschranktests, der Kühlschranktest, den Kühlschranktest, "
        "dem Kühlschranktest, des Kühlschranktests, den Kühlschranktests, der Kühlschrankteste, der Kühlschranktests, "
        "des Kühlschranktestes, den Kühlschranktesten]")
    assert_suggestion1(lt, synthesizer, "die Kühlschrankverarbeitungstest", "[die Kühlschrankverarbeitungsteste, die Kühlschrankverarbeitungstests, "
        "der Kühlschrankverarbeitungstest, den Kühlschrankverarbeitungstest, dem Kühlschrankverarbeitungstest, "
        "des Kühlschrankverarbeitungstests, den Kühlschrankverarbeitungstests, der Kühlschrankverarbeitungsteste, "
        "der Kühlschrankverarbeitungstests, des Kühlschrankverarbeitungstestes, den Kühlschrankverarbeitungstesten]")
    assert_suggestion2(lt, synthesizer, "den gleiche Gebiete", "[dem gleichen Gebiete, den gleichen Gebieten, der gleichen Gebiete, "
        "das gleiche Gebiet, die gleichen Gebiete, dem gleichen Gebiet, des gleichen Gebietes, des gleichen Gebiets]")
    assert_suggestion2(lt, synthesizer, "den vorangegangen Versuchen", "[den vorangegangenen Versuchen, das vorangegangene Versuchen, "
        "dem vorangegangenen Versuchen, den vorangegangenen Versuch, der vorangegangene Versuch, des vorangegangenen Versuches, "
        "das vorangegangene versuchen, dem vorangegangenen versuchen, des vorangegangenen Versuchens, der vorangegangenen Versuche, "
        "dem vorangegangenen Versuch, des vorangegangenen Versuchs, des vorangegangenen versuchens, die vorangegangenen Versuche]")
    assert_suggestion1(lt, synthesizer, "der Blutflusses", "[des Blutflusses, der Blutfluss, der Blutflüsse, den Blutfluss, dem Blutfluss, den Blutflüssen, die Blutflüsse]")
    assert_suggestion2(lt, synthesizer, "ein anstrengenden Tag",
        "[ein anstrengender Tag, ein anstrengendes Tag, einen anstrengenden Tag, einem anstrengenden Tag, eines anstrengenden Tags, eines anstrengenden Tages]")
    # assertSuggestion2("vor allem Teams", "[vor allen Teams]");  // TODO: 'allen' is PRO:IND, 'allem' is PRO:DEM, so we don't map yet between those
    assert_suggestion1(lt, synthesizer, "dasselbe Erinnerung", "[dieselbe Erinnerung, derselben Erinnerung]")
    assert_suggestion1(lt, synthesizer, "derselbe Erinnerung", "[derselben Erinnerung, dieselbe Erinnerung]")
    assert_suggestion1(lt, synthesizer, "derselbe Frau", "[derselben Frau, dieselbe Frau]")
    assert_suggestion1(lt, synthesizer, "dieselben Erinnerung", "[dieselbe Erinnerung, derselben Erinnerung]")
    assert_suggestion1(lt, synthesizer, "derselben Mann", "[derselbe Mann, denselben Mann, demselben Mann, desselben Manns, desselben Mannes]")
    assert_suggestion1(lt, synthesizer, "demselben Frau", "[derselben Frau, dieselbe Frau]")
    assert_suggestion1(lt, synthesizer, "desselben Mann", "[denselben Mann, demselben Mann, desselben Manns, derselbe Mann, desselben Mannes]")
    assert_suggestion1(lt, synthesizer, "Desselben Mann", "[Denselben Mann, Demselben Mann, Desselben Manns, Derselbe Mann, Desselben Mannes]")
    assert_suggestion1(lt, synthesizer, "meinem Eltern", "[meine Eltern, meinen Eltern, meiner Eltern]")
    assert_suggestion1(lt, synthesizer, "eure Auge", "[eurem Auge, eure Augen, euer Auge, euerem Auge, euerm Auge, eures Auges, euren Augen, eueres Auges, euerer Augen]")
    assert_suggestion1(lt, synthesizer, "welche Internetvideo", "[welches Internetvideo, welchem Internetvideo, welche Internetvideos, welches Internetvideos, welchen Internetvideos, welcher Internetvideos]")
    assert_suggestion1(lt, synthesizer, "welchen Internetvideo", "[welches Internetvideo, welchem Internetvideo, welchen Internetvideos, welches Internetvideos, welche Internetvideos, welcher Internetvideos]")
    assert_suggestion1(lt, synthesizer, "welches Mann", "[welcher Mann, welchen Mann, welchem Mann, welches Manns, welches Mannes, welche Männer, welcher Männer, welchen Männern]")
    assert_suggestion1(lt, synthesizer, "welchem Frau", "[welche Frau, welcher Frau, welche Frauen, welchen Frauen, welcher Frauen]")
    assert_suggestion1(lt, synthesizer, "welcher Kind", "[welches Kind, welchem Kind, welcher Kinder, welchem Kinde, welches Kinds, welches Kindes, welche Kinder, welchen Kindern]")
    assert_suggestion1(lt, synthesizer, "Welcher Kind", "[Welches Kind, Welchem Kind, Welcher Kinder, Welchem Kinde, Welches Kinds, Welches Kindes, Welche Kinder, Welchen Kindern]")


def test_suggestions_with_repl_type(lt, synthesizer):
    """AgreementSuggestor2Test.testSuggestionsWithReplType"""
    tags = lt.get_analyzed_sentence("gehe zur Mann").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], REPLACEMENT_ZUR)
    assert _str(suggestor.get_suggestions()) == ("[zum Mann, zu Männern]")

    tags = lt.get_analyzed_sentence("gehe zur kuschelige Ferienwohnung").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], tags[4], REPLACEMENT_ZUR)
    assert _str(suggestor.get_suggestions()) == ("[zur kuscheligen Ferienwohnung, zu kuscheligen Ferienwohnungen]")


def test_suggestions_with_repl_type_ins(lt, synthesizer):
    """AgreementSuggestor2Test.testSuggestionsWithReplTypeIns"""
    tags = lt.get_analyzed_sentence("gehe ins Hauses").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], REPLACEMENT_INS)
    assert _str(suggestor.get_suggestions()) == ("[ins Haus, im Hause, im Haus, in die Häuser, in den Häusern]")


def test_suggestions_with_repl_type_ins_adj(lt, synthesizer):
    """AgreementSuggestor2Test.testSuggestionsWithReplTypeInsAdj"""
    tags = lt.get_analyzed_sentence("gehe ins großen Haus").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], tags[4], REPLACEMENT_INS)
    assert _str(suggestor.get_suggestions()) == ("[im großen Haus, ins große Haus, im großen Hause, in die großen Häuser, in den großen Häusern]")


def test_suggestions_haus(lt, synthesizer):
    """AgreementSuggestor2Test.testSuggestionsHaus"""
    assert_suggestion1(lt, synthesizer, "Der Haus", "[Dem Haus, Das Haus, Der Häuser, Dem Hause, Des Hauses, Die Häuser, Den Häusern]")
    assert_suggestion1(lt, synthesizer, "der Haus", "[dem Haus, das Haus, der Häuser, dem Hause, des Hauses, die Häuser, den Häusern]")
    assert_suggestion1(lt, synthesizer, "das Haus", "[dem Haus, dem Hause, des Hauses, die Häuser, der Häuser, den Häusern]")
    assert_suggestion1(lt, synthesizer, "der Haus", "[dem Haus, das Haus, der Häuser, dem Hause, des Hauses, die Häuser, den Häusern]")
    assert_suggestion1(lt, synthesizer, "die Haus", "[das Haus, dem Haus, die Häuser, dem Hause, des Hauses, der Häuser, den Häusern]")
    assert_suggestion1(lt, synthesizer, "die Hauses", "[des Hauses, die Häuser, dem Hause, das Haus, dem Haus, der Häuser, den Häusern]")
    assert_suggestion1(lt, synthesizer, "die Häusern", "[die Häuser, den Häusern, der Häuser, dem Hause, des Hauses, das Haus, dem Haus]")
    # filtered:
    assert_suggestion1(lt, synthesizer, "Der Haus", "[Dem Haus, Das Haus, Der Häuser]", True)
    assert_suggestion1(lt, synthesizer, "der Haus", "[dem Haus, das Haus, der Häuser]", True)
    assert_suggestion1(lt, synthesizer, "das Haus", "[dem Haus]", True)
    assert_suggestion1(lt, synthesizer, "der Haus", "[dem Haus, das Haus, der Häuser]", True)
    assert_suggestion1(lt, synthesizer, "die Haus", "[das Haus, dem Haus, die Häuser]", True)
    assert_suggestion1(lt, synthesizer, "die Hauses", "[des Hauses, die Häuser]", True)
    assert_suggestion1(lt, synthesizer, "die Häusern", "[die Häuser, den Häusern]", True)
    assert_suggestion1(lt, synthesizer, "unsere Buch", "[unser Buch, unserem Buch, unsere Bücher]", True)


def test_det_adj_noun_suggestions(lt, synthesizer):
    """AgreementSuggestor2Test.testDetAdjNounSuggestions"""
    assert_suggestion2(lt, synthesizer, "die neuen Unterlage", "[die neue Unterlage, die neuen Unterlagen, der neuen Unterlage, den neuen Unterlagen, der neuen Unterlagen]")
    assert_suggestion2(lt, synthesizer, "der neue Unterlagen", "[der neuen Unterlagen, der neuen Unterlage, den neuen Unterlagen, die neue Unterlage, die neuen Unterlagen]")
    assert_suggestion2(lt, synthesizer, "eine schönes Auto", "[ein schönes Auto, einem schönen Auto, eines schönen Autos]")
    assert_suggestion2(lt, synthesizer, "eine schöne Auto", "[ein schönes Auto, einem schönen Auto, eines schönen Autos]")
    assert_suggestion2(lt, synthesizer, "ein schöne Auto", "[ein schönes Auto, einem schönen Auto, eines schönen Autos]")
    assert_suggestion2(lt, synthesizer, "einen großen Auto", "[einem großen Auto, eines großen Autos, ein großes Auto]")
    assert_suggestion2(lt, synthesizer, "der schöne Auto", "[das schöne Auto, dem schönen Auto, der schönen Autos, des schönen Autos, den schönen Autos, die schönen Autos]")
    assert_suggestion2(lt, synthesizer, "der kleine Auto", "[das kleine Auto, dem kleinen Auto, der kleinen Autos, des kleinen Autos, den kleinen Autos, die kleinen Autos]")
    assert_suggestion2(lt, synthesizer, "der kleiner Auto", "[dem kleinen Auto, der kleinen Autos, das kleine Auto, des kleinen Autos, den kleinen Autos, die kleinen Autos]")
    assert_suggestion2(lt, synthesizer, "das stärkste Körperteil", "[der stärkste Körperteil, den stärksten Körperteil, dem stärksten Körperteil, des stärksten Körperteils, dem stärksten Körperteile, des stärksten Körperteiles, die stärksten Körperteile, der stärksten Körperteile, den stärksten Körperteilen]")
    # "benötigten" ist PA2:
    assert_suggestion2(lt, synthesizer, "die benötigten Unterlage", "[die benötigte Unterlage, die benötigten Unterlagen, der benötigten Unterlage, den benötigten Unterlagen, der benötigten Unterlagen]")
    assert_suggestion2(lt, synthesizer, "eine benötigten Unterlage", "[eine benötigte Unterlage, einer benötigten Unterlage]")
    assert_suggestion2(lt, synthesizer, "die voller Verzierungen", "[die vollen Verzierungen, die volle Verzierung, den vollen Verzierungen, der vollen Verzierungen, der vollen Verzierung]")   # evtl. Fehlalarm...
    assert_suggestion2(lt, synthesizer, "zu zukünftigen Vorstands", "[]")    # ?
    assert_suggestion2(lt, synthesizer, "des südlichen Kontinent", "[den südlichen Kontinent, dem südlichen Kontinent, des südlichen Kontinents, des südlichen Kontinentes, der südliche Kontinent, der südlichen Kontinente, die südlichen Kontinente, den südlichen Kontinenten]")
    assert_suggestion2(lt, synthesizer, "die erwartet Entwicklung", "[die erwartete Entwicklung, der erwarteten Entwicklung, die erwarteten Entwicklungen, den erwarteten Entwicklungen, der erwarteten Entwicklungen]")
    assert_suggestion2(lt, synthesizer, "die verschieden Ämter", "[die verschiedenen Ämter, der verschiedenen Ämter, den verschiedenen Ämtern, das verschiedene Amt, dem verschiedenen Amte, des verschiedenen Amtes, dem verschiedenen Amt, des verschiedenen Amts]")
    assert_suggestion2(lt, synthesizer, "keine richtiger Fahrerin", "[keine richtige Fahrerin, keiner richtigen Fahrerin, keine richtigen Fahrerinnen, keinen richtigen Fahrerinnen, keiner richtigen Fahrerinnen]")
    # GRU, KOM, SUP:
    assert_suggestion2(lt, synthesizer, "das schönes Auto", "[das schöne Auto, dem schönen Auto, des schönen Autos, die schönen Autos, den schönen Autos, der schönen Autos]")
    assert_suggestion2(lt, synthesizer, "das schöneren Auto", "[das schönere Auto, dem schöneren Auto, des schöneren Autos, die schöneren Autos, den schöneren Autos, der schöneren Autos]")
    assert_suggestion2(lt, synthesizer, "das schönstem Auto", "[das schönste Auto, dem schönsten Auto, des schönsten Autos, die schönsten Autos, den schönsten Autos, der schönsten Autos]")
    assert_suggestion2(lt, synthesizer, "das schönsten Auto", "[das schönste Auto, dem schönsten Auto, das schöne Auto, des schönsten Autos, die schönsten Autos, "
        "den schönsten Autos, der schönsten Autos, dem schönen Auto, des schönen Autos, die schönen Autos, den schönen Autos, der schönen Autos]")
    assert_suggestion2(lt, synthesizer, "der ikonischen Gebäuden", "[den ikonischen Gebäuden, der ikonischen Gebäude, dem ikonischen Gebäude, des ikonischen Gebäudes, die ikonischen Gebäude, das ikonische Gebäude]")
    assert_suggestion2(lt, synthesizer, "der ikonischeren Gebäuden", "[den ikonischeren Gebäuden, der ikonischeren Gebäude, dem ikonischeren Gebäude, des ikonischeren Gebäudes, die ikonischeren Gebäude, das ikonischere Gebäude]")
    assert_suggestion2(lt, synthesizer, "der ikonischsten Gebäuden", "[den ikonischsten Gebäuden, der ikonischsten Gebäude, dem ikonischsten Gebäude, "
        "des ikonischsten Gebäudes, die ikonischsten Gebäude, den ikonischen Gebäuden, der ikonischen Gebäude, das ikonischste Gebäude, "
        "dem ikonischen Gebäude, des ikonischen Gebäudes, die ikonischen Gebäude, das ikonische Gebäude]")
    assert_suggestion2(lt, synthesizer, "den meisten Fälle", "[den meisten Fällen, der meisten Fälle, die meisten Fälle]")


def test_det_noun_suggestions_with_preposition(lt, synthesizer):
    """AgreementSuggestor2Test.testDetNounSuggestionsWithPreposition"""
    tags = lt.get_analyzed_sentence("für dein Schmuck").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], None)
    assert _str(suggestor.get_suggestions(False)) == ("[deinen Schmuck, deinem Schmuck, deines Schmucks, deines Schmuckes]")
    assert _str(suggestor.get_suggestions(True)) == ("[deinen Schmuck, deinem Schmuck]")
    suggestor.set_preposition(tags[1])  # "für"
    assert _str(suggestor.get_suggestions(False)) == ("[deinen Schmuck]")
    assert _str(suggestor.get_suggestions(True)) == ("[deinen Schmuck]")


def test_det_adj_noun_suggestions_with_preposition(lt, synthesizer):
    """AgreementSuggestor2Test.testDetAdjNounSuggestionsWithPreposition"""
    tags = lt.get_analyzed_sentence("über ein hilfreichen Tipp").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], tags[4], None)
    assert _str(suggestor.get_suggestions()) == ("[ein hilfreicher Tipp, einen hilfreichen Tipp, einem hilfreichen Tipp, eines hilfreichen Tipps]")
    suggestor.set_preposition(tags[1])  # "über"
    assert _str(suggestor.get_suggestions()) == ("[einen hilfreichen Tipp, einem hilfreichen Tipp]")

    tags = lt.get_analyzed_sentence("an den stacheligen Pflanzenteile").get_tokens_without_whitespace()
    suggestor = AgreementSuggestor2(synthesizer, tags[2], tags[3], tags[4], None)
    assert _str(suggestor.get_suggestions()) == ("[den stacheligen Pflanzenteil, dem stacheligen Pflanzenteile, "
        "den stacheligen Pflanzenteilen, der stacheligen Pflanzenteile, die stacheligen Pflanzenteile, dem stacheligen Pflanzenteil, "
        "des stacheligen Pflanzenteiles, des stacheligen Pflanzenteils, der stachelige Pflanzenteil, das stachelige Pflanzenteil]")
    suggestor.set_preposition(tags[1])  # "an"
    assert _str(suggestor.get_suggestions()) == ("[den stacheligen Pflanzenteil, dem stacheligen Pflanzenteile, "
        "den stacheligen Pflanzenteilen, die stacheligen Pflanzenteile, dem stacheligen Pflanzenteil, das stachelige Pflanzenteil]")


def test_det_adj_adj_noun_suggestions(lt, synthesizer):
    """AgreementSuggestor2Test.testDetAdjAdjNounSuggestions"""
    assert_suggestion3(lt, synthesizer, "eine solides strategisches Fundament", "[ein solides strategisches Fundament]", True)
    assert_suggestion3(lt, synthesizer, "ein solide strategisches Fundament", "[ein solides strategisches Fundament]", True)
    assert_suggestion3(lt, synthesizer, "ein solides strategische Fundament", "[ein solides strategisches Fundament]", True)
    assert_suggestion3(lt, synthesizer, "ein solides strategisches Fundamente", "[ein solides strategisches Fundament]", True)
    assert_suggestion3(lt, synthesizer, "ein solides strategisches Fundamenten", "[ein solides strategisches Fundament]", True)
    assert_suggestion3(lt, synthesizer, "die meisten kommerziellen System", "[die meisten kommerziellen Systeme]", True)
    assert_suggestion3(lt, synthesizer, "die meisten kommerzielle Systeme", "[die meisten kommerziellen Systeme]", True)
    assert_suggestion3(lt, synthesizer, "die meisten kommerziell Systeme", "[die meisten kommerziellen Systeme]", True)
    assert_suggestion3(lt, synthesizer, "die meisten kommerziell System", "[die meisten kommerziellen Systeme]", True)
    assert_suggestion3(lt, synthesizer, "Die meisten kommerziellen System", "[Die meisten kommerziellen Systeme]", True)
    assert_suggestion3(lt, synthesizer, "der meisten kommerziellen System", "[der meisten kommerziellen Systeme]", True)
    assert_suggestion3(lt, synthesizer, "der meisten kommerziellen Systems", "[der meisten kommerziellen Systeme]", True)
    # assertSuggestion3("jedes viertes fremdsprachliche Wurzeln", "[jedes vierte fremdsprachliche Wurzeln]", true);  // TODO
