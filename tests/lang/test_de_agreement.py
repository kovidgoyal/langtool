"""Port of org.languagetool.rules.de.AgreementRuleTest (the tests of
AgreementRule, langtool.lang.de.agreement)."""

import pytest

from conftest import require_dictionaries

from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(autouse=True, scope='module')
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def rule():
    from langtool.lang.de.agreement import AgreementRule
    return AgreementRule(messages_for('de'), get_language('de-DE'))


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


def assert_good(rule, lt, s):
    matches = rule.match(lt.get_analyzed_sentence(s))
    assert len(matches) == 0, "Found unexpected match in sentence '%s': %s" % (s, matches)


def assert_bad(rule, lt, s, *expected_suggestions):
    matches = rule.match(lt.get_analyzed_sentence(s))
    assert len(matches) == 1, "Did not find one match in sentence '%s'" % s
    if expected_suggestions:
        assert matches[0].suggested_replacements == list(expected_suggestions)


def assert_bad1(rule, lt, s, expected_suggestion):
    matches = rule.match(lt.get_analyzed_sentence(s))
    assert len(matches) == 1, "Did not find one match in sentence '%s'" % s
    suggestions = matches[0].suggested_replacements
    assert expected_suggestion in suggestions[:4], \
        "Expected suggestion '%s' not found in first 5 suggestions for input '%s'. Suggestions found: %s" % (
            expected_suggestion, s, suggestions)


def test_get_categories_causing_error(rule):
    """AgreementRuleTest.testGetCategoriesCausingError"""
    token_det_mas_sin = AnalyzedTokenReadings(AnalyzedToken("der", "ART:DEF:NOM:SIN:MAS", "der"))
    token_det_fem_sin = AnalyzedTokenReadings(AnalyzedToken("die", "ART:DEF:NOM:SIN:FEM", "der"))
    token_det_fem_plu = AnalyzedTokenReadings(AnalyzedToken("die", "ART:DEF:NOM:PLU:FEM", "der"))
    token_sub_neu_sin = AnalyzedTokenReadings(AnalyzedToken("Haus", "SUB:NOM:SIN:NEU", "Haus"))
    token_sub_fem_plu = AnalyzedTokenReadings(AnalyzedToken("Frauen", "SUB:NOM:PLU:FEM", "Frau"))
    token_sub_gen_fem_plu = AnalyzedTokenReadings(AnalyzedToken("Frauen", "SUB:GEN:PLU:FEM", "Frau"))

    res1 = rule.get_categories_causing_error(token_det_fem_plu, token_sub_gen_fem_plu)
    assert len(res1) == 1
    assert "Kasus" in res1[0]

    res2 = rule.get_categories_causing_error(token_det_mas_sin, token_sub_neu_sin)
    assert len(res2) == 1
    assert "Genus" in res2[0]

    res3 = rule.get_categories_causing_error(token_det_fem_sin, token_sub_fem_plu)
    assert len(res3) == 1
    assert "Numerus" in res3[0]

    # List<String> res4 = rule.getCategoriesCausingError(tokenDetFemSin, tokenSubGenFemPlu);
    # assertThat(res4.size(), is(2));
    # assertTrue(res4.get(0).contains("Numerus"));
    # assertTrue(res4.get(1).contains("Kasus"));


def test_compound_match(rule, lt):
    """AgreementRuleTest.testCompoundMatch"""
    assert_bad(rule, lt, "Das ist die Original Mail", "die Originalmail", "die Original-Mail")
    assert_bad(rule, lt, "Das ist die neue Original Mail", "die neue Originalmail", "die neue Original-Mail")
    assert_bad(rule, lt, "Das ist die ganz neue Original Mail", "die ganz neue Originalmail", "die ganz neue Original-Mail")
    assert_bad(rule, lt, "Doch dieser kleine Magnesium Anteil ist entscheidend.", "dieser kleine Magnesiumanteil", "dieser kleine Magnesium-Anteil")
    assert_bad(rule, lt, "Doch dieser sehr kleine Magnesium Anteil ist entscheidend.", "dieser sehr kleine Magnesiumanteil", "dieser sehr kleine Magnesium-Anteil")
    assert_bad(rule, lt, "Die Standard Priorität ist 5.", "Die Standardpriorität", "Die Standard-Priorität")
    assert_bad(rule, lt, "Die derzeitige Standard Priorität ist 5.", "Die derzeitige Standardpriorität", "Die derzeitige Standard-Priorität")
    assert_bad(rule, lt, "Ein neuer LanguageTool Account", "Ein neuer LanguageTool-Account")
    assert_bad(rule, lt, "Danke für deine Account Daten", "deine Accountdaten", "deine Account-Daten")
    assert_bad(rule, lt, "Mit seinem Konkurrent Alistair Müller", "seinem Konkurrenten")
    assert_bad(rule, lt, "Wir gehen ins Fitness Studio", "ins Fitnessstudio", "ins Fitness-Studio")
    assert_bad(rule, lt, "Wir gehen durchs Fitness Studio", "durchs Fitnessstudio", "durchs Fitness-Studio")
    assert_bad(rule, lt, "Was für eine schöner Sonnenuntergang!", "ein schöner Sonnenuntergang")
    assert_good(rule, lt, "Es gibt ein Sprichwort, dem zufolge der tägliche Genuss einer Mandel dem Gedächtnis förderlich sei.")
    assert_good(rule, lt, "War das Eifersucht?")
    assert_good(rule, lt, "Sie gehörte einst zu den besten Afrikas.")
    assert_good(rule, lt, "Dieses Bild stammt von einem lange Zeit unbekannten Maler.")
    assert_good(rule, lt, "Das Staatsoberhaupt ist der Verfassung zufolge der König.")
    assert_good(rule, lt, "Der Ende der 1960er Jahre umgestaltete Garten ist schön.")
    assert_good(rule, lt, "Der Ende der achtziger Jahre umgestaltete Garten hat unter anderem ungefähr 70 verschiedene Sorten von Rosen und Volieren für exotische Vögel.")
    assert_good(rule, lt, "Als Vorboten des Discounthandels sind die Ende der 50er Jahre in der Bundesrepublik Deutschland wiederauflebenden Erscheinungsformen des Beziehungs-, Betriebs- und Belegschaftshandels anzusehen.")
    assert_good(rule, lt, "Die Anfang des letzten Monats umgestaltete Veranda ist schön.")
    assert_good(rule, lt, "Der Mitte 2001 umgestaltete Garten ist schön.")
    assert_bad(rule, lt, "Es ist ein sehr interessantes kostenloses Slot Spiel.", "ein sehr interessantes kostenloses Slotspiel", "ein sehr interessantes kostenloses Slot-Spiel")
    # assertBad("Die Bad Taste Party von Susi", "Die Bad-Taste-Party");   // not supported yet
    # assertBad("Die Update Liste.", "Die Updateliste");  // not accepted by speller
    matches = lt.check("Er folgt damit dem Tipp des Autoren Michael Müller.")
    assert len(matches) == 1
    assert "zusammengesetztes Nomen" not in matches[0].message


def test_det_noun_rule(rule, lt):
    """AgreementRuleTest.testDetNounRule"""
    # correct sentences:
    assert_good(rule, lt, "Bis zur Anfang Juni geplanten Eröffnung gebe es noch einiges zu tun.")
    assert_good(rule, lt, "Der fließend Französisch sprechende Präsident dankt stilvoll ab.")
    assert_good(rule, lt, "Inwiefern soll denn das romantische Hoffnungen begründen?")
    assert_good(rule, lt, "Spricht der fließend Französisch?")
    assert_good(rule, lt, "Spricht dieser fließend Französisch, muss er viel Geld verdienen.")
    assert_good(rule, lt, "Der letzte Woche beschlossene Etat ist unwirksam.")
    assert_good(rule, lt, "Die Einen sagen dies, die Anderen das.")
    assert_good(rule, lt, "So ist es in den USA.")
    assert_good(rule, lt, "Das ist der Tisch.")
    assert_good(rule, lt, "Das ist das Haus.")
    assert_good(rule, lt, "Das ist die Frau.")
    assert_good(rule, lt, "Das ist das Auto der Frau.")
    assert_good(rule, lt, "Das gehört dem Mann.")
    assert_good(rule, lt, "Das Auto des Mannes.")
    assert_good(rule, lt, "Das interessiert den Mann.")
    assert_good(rule, lt, "Das interessiert die Männer.")
    assert_good(rule, lt, "Das Auto von einem Mann.")
    assert_good(rule, lt, "Das Auto eines Mannes.")
    assert_good(rule, lt, "Des großen Mannes.")
    assert_good(rule, lt, "Und nach der Nummerierung kommt die Überschrift.")
    assert_good(rule, lt, "Sie wiesen dieselben Verzierungen auf.")
    assert_good(rule, lt, "Die erwähnte Konferenz ist am Samstag.")
    assert_good(rule, lt, "Sie erreichten 5 Prozent.")
    assert_good(rule, lt, "Sie erreichten mehrere Prozent Zustimmung.")
    assert_good(rule, lt, "Die Bestandteile, aus denen Schwefel besteht.")
    assert_good(rule, lt, "Ich tat für ihn, was kein anderer Autor für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was keine andere Autorin für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was kein anderes Kind für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was dieser andere Autor für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was diese andere Autorin für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was dieses andere Kind für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was jener andere Autor für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was jeder andere Autor für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was jede andere Autorin für ihn tat.")
    assert_good(rule, lt, "Ich tat für ihn, was jedes andere Kind für ihn tat.")
    assert_good(rule, lt, "Klebe ein Preisschild auf jedes einzelne Produkt.")
    assert_good(rule, lt, "Eine Stadt, in der zurzeit eine rege Bautätigkeit herrscht.")
    assert_good(rule, lt, "... wo es zu einer regen Bautätigkeit kam.")
    assert_good(rule, lt, "Mancher ausscheidende Politiker hinterlässt eine Lücke.")
    assert_good(rule, lt, "Kern einer jeden Tragödie ist es, ..")
    assert_good(rule, lt, "Das wenige Sekunden alte Baby schrie laut.")
    assert_good(rule, lt, "Meistens sind das Frauen, die damit besser umgehen können.")
    assert_good(rule, lt, "Er fragte, ob das Spaß macht.")
    assert_good(rule, lt, "Das viele Geld wird ihr helfen.")
    assert_good(rule, lt, "Er verspricht jedem hohe Gewinne.")
    assert_good(rule, lt, "Er versprach allen Renditen jenseits von 15 Prozent.")
    assert_good(rule, lt, "Sind das Eier aus Bodenhaltung?")
    assert_good(rule, lt, "Sie sind sehr gute Kameraden, auf die Verlass ist.")
    assert_good(rule, lt, "Dir macht doch irgendwas Sorgen.")
    assert_good(rule, lt, "Sie fragte, ob das wirklich Kunst sei.")
    assert_good(rule, lt, "Für ihn ist das Alltag.")
    assert_good(rule, lt, "Für die Religiösen ist das Blasphemie und führt zu Aufständen.")
    assert_good(rule, lt, "Das Orange ist schön.")
    assert_good(rule, lt, "Dieses rötliche Orange gefällt mir am besten.")
    assert_good(rule, lt, "Das ist ein super Tipp.")
    assert_good(rule, lt, "Er nahm allen Mut zusammen und ging los.")
    assert_good(rule, lt, "Sie kann einem Angst einjagen.")
    assert_good(rule, lt, "Damit sollten zum einen neue Energien gefördert werden, zum anderen der Sozialbereich.")
    assert_good(rule, lt, "Nichts ist mit dieser einen Nacht zu vergleichen.")
    assert_good(rule, lt, "dann muss Schule dem Rechnung tragen.")
    assert_good(rule, lt, "Das Dach von meinem Auto.")
    assert_good(rule, lt, "Das Dach von meinen Autos.")
    assert_good(rule, lt, "Da stellt sich die Frage: Ist das Science-Fiction oder moderne Mobilität?")
    assert_good(rule, lt, "Er hat einen Post veröffentlicht.")
    assert_good(rule, lt, "Eine lückenlose Aufklärung sämtlicher physiologischer Gehirnprozesse")
    assert_good(rule, lt, "Sie fragte verwirrt: „Ist das Zucker?“")
    assert_good(rule, lt, "Er versuchte sich vorzustellen, was sein Klient für ein Mensch sei.")
    assert_good(rule, lt, "Sie legen ein Teilstück jenes Weges zurück, den die Tausenden Juden 1945 auf sich nehmen mussten.")
    assert_good(rule, lt, "Aber das ignorierte Herr Grey bewusst.")
    assert_good(rule, lt, "Aber das ignorierte Herr Müller bewusst.")
    assert_good(rule, lt, "Ich werde mich zurücknehmen und mich frischen Ideen zuwenden.")
    assert_good(rule, lt, "Das, plus ein eigener Firmenwagen.")
    assert_good(rule, lt, "Dieses leise Summen stört nicht.")
    assert_good(rule, lt, "Die Tiroler Küche")
    assert_good(rule, lt, "Was ist denn das für ein ungewöhnlicher Name?")
    assert_good(rule, lt, "Besonders reizen mich Fahrräder.")
    assert_good(rule, lt, "Und nur, weil mich psychische Erkrankungen aus der Bahn werfen")
    assert_good(rule, lt, "Das kostet dich Zinsen.")
    assert_good(rule, lt, "Sie hatten keine Chance gegen das kleinere Preußen.")
    assert_good(rule, lt, "Den 2019er Wert hatten sie geschätzt.")
    assert_good(rule, lt, "Andere formale Systeme, deren Semantiken jeweils...")
    assert_good(rule, lt, "Gesetz zur Änderung des Kündigungsrechts und anderer arbeitsrechtlicher Vorschriften")
    assert_good(rule, lt, "Die dauerhafte Abgrenzung des später Niedersachsen genannten Gebietes von Westfalen begann im 12. Jahrhundert.")
    assert_good(rule, lt, "Lieber jemanden, der einem Tipps gibt.")
    assert_good(rule, lt, "Jainas ist sogar der Genuss jeglicher tierischer Nahrungsmittel strengstens untersagt.")
    assert_good(rule, lt, "Es sind jegliche tierische Nahrungsmittel untersagt.")
    assert_good(rule, lt, "Das reicht bis weit ins heutige Hessen.")
    assert_good(rule, lt, "Die Customer Journey.")
    assert_good(rule, lt, "Für dich gehört Radfahren zum perfekten Urlaub dazu?")
    assert_good(rule, lt, ":D:D Leute, bitte!")
    assert_good(rule, lt, "Es genügt, wenn ein Mann sein eigenes Geschäft versteht und sich nicht in das anderer Leute einmischt.")
    assert_good(rule, lt, "Ich habe das einige Male versucht.")
    assert_good(rule, lt, "Und keine Märchen erzählst, die dem anderen Hoffnungen machen können.")
    assert_good(rule, lt, "Um diese Körpergrößen zu erreichen, war das Wachstum der Vertreter der Gattung Dinornis offenbar gegenüber dem anderer Moa-Gattungen beschleunigt")
    assert_good(rule, lt, "Der Schädel entspricht in den Proportionen dem anderer Vulpes-Arten, besitzt aber sehr große Paukenhöhlen, ein typisches Merkmal von Wüstenbewohnern.")
    assert_good(rule, lt, "Deuterium lässt sich aufgrund des großen Massenunterschieds leichter anreichern als die Isotope der anderer Elemente wie z. B. Uran.")
    assert_good(rule, lt, "Unklar ist, ob er zwischen der Atemseele des Menschen und der anderer Lebewesen unterschied.")
    assert_good(rule, lt, "Die Liechtensteiner Grenze ist im Verhältnis zu der anderer Länder kurz, da Liechtenstein ein eher kleines Land ist.")
    assert_good(rule, lt, "Picassos Kunstwerke werden häufiger gestohlen als die anderer Künstler.")
    assert_good(rule, lt, "Schreibe einen Artikel über deine Erfahrungen im Ausland oder die anderer Leute in deinem Land.")
    assert_good(rule, lt, "Die Bevölkerungen Chinas und Indiens lassen die anderer Staaten als Zwerge erscheinen.")
    assert_good(rule, lt, "Der eine mag Obst, ein anderer Gemüse, wieder ein anderer mag Fisch; allen kann man es nicht recht machen.")
    assert_good(rule, lt, "Mittels eines Bootloaders und zugehöriger Software kann nach jedem Anstecken des Adapters eine andere Firmware-Varianten geladen werden")
    assert_good(rule, lt, "Wenn sie eine andere Größe benötigen, teilen uns ihre speziellen Wünsche mit und wir unterbreiten ihnen ein Angebot über Preis und Lieferung.")
    assert_good(rule, lt, "Dabei wird in einer Vakuumkammer eine einige Mikrometer dicke CVD-Diamantschicht auf den Substraten abgeschieden.")
    assert_good(rule, lt, "1916 versuchte Gilbert Newton Lewis, die chemische Bindung durch Wechselwirkung der Elektronen eines Atoms mit einem anderen Atomen zu erklären.")
    assert_good(rule, lt, "Vom einen Ende der Straße zum anderen.")
    assert_good(rule, lt, "Er war müde vom vielen Laufen.")
    assert_good(rule, lt, "Sind das echte Diamanten?")
    assert_good(rule, lt, "Es wurde eine Verordnung erlassen, der zufolge jeder Haushalt Energie einsparen muss.")
    assert_good(rule, lt, "Im Jahr 1922 verlieh ihm König George V. den erblichen Titel eines Baronet. ")
    assert_good(rule, lt, "... der zu dieser Zeit aber ohnehin schon allen Einfluss verloren hatte.")
    assert_good(rule, lt, "Ein Geschenk, das Maßstäbe setzt")
    assert_good(rule, lt, "Einwohnerzahl stieg um das Zweieinhalbfache")
    assert_good(rule, lt, "Die Müllers aus Hamburg.")
    assert_good(rule, lt, "Es ist noch unklar, wann und für wen Impfungen vorgenommen werden könnten.")
    assert_good(rule, lt, "Macht dir das Hoffnung?")
    assert_good(rule, lt, "Mich fasziniert Macht.")
    assert_good(rule, lt, "Der solchen Einsätzen gegenüber kritische Hitler wurde nicht im Voraus informiert.")
    assert_good(rule, lt, "Gregor wählte die Gestalt des wenige Jahrzehnte zuvor verstorbenen Klostergründers.")

    assert_good(rule, lt, "Wir machen das Januar.")
    assert_good(rule, lt, "Wir teilen das Morgen mit.")
    assert_good(rule, lt, "Wir präsentierten das vorletzten Sonnabend.")
    assert_good(rule, lt, "Ich release das Vormittags.")
    assert_good(rule, lt, "Sie aktualisieren das Montags.")
    assert_good(rule, lt, "Kannst du das Mittags machen?")
    assert_good(rule, lt, "Können Sie das nächsten Monat erledigen?")
    assert_good(rule, lt, "Können Sie das auch nächsten Monat erledigen?")
    assert_good(rule, lt, "War das Absicht?")
    assert_good(rule, lt, "Alles Große und Edle ist einfacher Art.")
    assert_good(rule, lt, "Dieser vereint Sprachprüfung, Thesaurus und Umformuliertool in einem.")

    assert_good(rule, lt, "Das Dach meines Autos.")
    assert_good(rule, lt, "Das Dach meiner Autos.")

    assert_good(rule, lt, "Das Dach meines großen Autos.")
    assert_good(rule, lt, "Das Dach meiner großen Autos.")

    assert_good(rule, lt, "Dann schlug er so kräftig wie er konnte mit den Schwingen.")
    assert_good(rule, lt, "Also wenn wir Glück haben, ...")
    assert_good(rule, lt, "Wenn wir Pech haben, ...")
    assert_good(rule, lt, "Ledorn öffnete eines der an ihr vorhandenen Fächer.")
    assert_good(rule, lt, "Auf der einen Seite endlose Dünen")
    assert_good(rule, lt, "In seinem Maul hielt er einen blutigen Fleischklumpen.")
    assert_good(rule, lt, "Gleichzeitig dachte er intensiv an Nebelschwaden, aus denen Wolken ja bestanden.")
    assert_good(rule, lt, "Warum stellte der bloß immer wieder dieselben Fragen?")
    assert_good(rule, lt, "Bei der Hinreise.")
    assert_good(rule, lt, "Schließlich tauchten in einem Waldstück unter ihnen Schienen auf.")

    assert_good(rule, lt, "Das Wahlrecht, das Frauen damals zugesprochen bekamen.")
    assert_good(rule, lt, "Es war Karl, dessen Leiche Donnerstag gefunden wurde.")

    assert_good(rule, lt, "Erst recht ich Arbeiter.")
    assert_good(rule, lt, "Erst recht wir Arbeiter.")
    assert_good(rule, lt, "Erst recht wir fleißigen Arbeiter.")

    assert_good(rule, lt, "Dann lud er Freunde ein.")
    assert_good(rule, lt, "Dann lud sie Freunde ein.")
    assert_good(rule, lt, "Aller Kommunikation liegt dies zugrunde.")
    assert_good(rule, lt, "Pragmatisch wählt man solche Formeln als Axiome.")
    assert_good(rule, lt, "Der eine Polizist rief dem anderen zu...")
    assert_good(rule, lt, "Der eine große Polizist rief dem anderen zu...")
    assert_good(rule, lt, "Das eine Kind rief dem anderen zu...")
    assert_good(rule, lt, "Er wollte seine Interessen wahrnehmen.")
    assert_bad(rule, lt, "Denn die einzelnen sehen sich einer sehr verschieden starken Macht des...")    # TODO
    assert_bad(rule, lt, "Es birgt für mich ein zu hohes juristische Risiko.")
    assert_good(rule, lt, "Es birgt für mich ein zu hohes juristisches Risiko.")

    assert_good(rule, lt, "... wo Krieg den Unschuldigen Leid und Tod bringt.")
    assert_good(rule, lt, "Der Abschuss eines Papageien.")

    assert_good(rule, lt, "Die Beibehaltung des Art. 1 ist geplant.")
    assert_good(rule, lt, "Die Verschiebung des bisherigen Art. 1 ist geplant.")

    assert_good(rule, lt, "In diesem Fall hatte das Vorteile.")
    assert_good(rule, lt, "So hat das Konsequenzen.")

    assert_good(rule, lt, "Ein für viele wichtiges Anliegen.")
    assert_good(rule, lt, "Das weckte bei vielen ungute Erinnerungen.")
    assert_good(rule, lt, "Etwas, das einem Angst macht.")
    assert_good(rule, lt, "Einem geschenkten Gaul schaut man nicht ins Maul.")

    assert_good(rule, lt, "Das erfordert Können.")
    assert_good(rule, lt, "Ist das Kunst?")
    assert_good(rule, lt, "Ist das Kunst oder Abfall?")
    assert_good(rule, lt, "Die Zeitdauer, während der Wissen nützlich bleibt, wird kürzer.")
    assert_good(rule, lt, "Es sollte nicht viele solcher Bilder geben")
    assert_good(rule, lt, "In den 80er Jahren.")
    assert_good(rule, lt, "Hast du etwas das Carina machen kann?")
    assert_good(rule, lt, "Ein Artikel in den Ruhr Nachrichten.")
    assert_good(rule, lt, "Ich wollte nur allen Hallo sagen.")
    assert_good(rule, lt, "Ich habe deshalb allen Freund*innen Bescheid gegeben.")     # Gendersternchen, https://github.com/languagetool-org/languagetool/issues/2417
    assert_good(rule, lt, "Ich habe deshalb allen Freund_innen Bescheid gegeben.")
    assert_good(rule, lt, "Ich habe deshalb allen Freund:innen Bescheid gegeben.")
    assert_good(rule, lt, "Das betrifft auch eure Werkstudent:innen-Zielgruppe.")
    assert_bad(rule, lt, "Das betrifft auch eure Werkstudent:innen-Xihfrisfgds.")
    assert_good(rule, lt, "Das betrifft auch eure Werkstudent:innenzielgruppe.")
    assert_good(rule, lt, "Das betrifft auch eure Jurist:innenausbildung.")
    assert_bad(rule, lt, "Das betrifft auch eure Jurist:innenxyzdfsdf.")
    assert_good(rule, lt, "Sein*e Mitarbeiter*in ist davon auch betroffen.")
    assert_good(rule, lt, "Jede*r Mitarbeiter*in ist davon betroffen.")
    assert_good(rule, lt, "Alle Professor*innen")
    assert_good(rule, lt, "Gleichzeitig wünscht sich Ihr frostresistenter Mitbewohner einige Grad weniger im eigenen Zimmer?")
    assert_good(rule, lt, "Ein Trainer, der zum einen Fußballspiele sehr gut lesen und analysieren kann")
    assert_good(rule, lt, "Eine Massengrenze, bis zu der Lithium nachgewiesen werden kann.")
    assert_good(rule, lt, "Bei uns im Krankenhaus betrifft das Operationssäle.")
    assert_good(rule, lt, "Macht dir das Freude?")
    assert_good(rule, lt, "Das macht jedem Angst.")
    assert_good(rule, lt, "Dann macht das Sinn.")
    assert_good(rule, lt, "Das sind beides Lichtschalter.")
    assert_good(rule, lt, "Spielst du vielleicht auf das Bordell neben unserm Hotel an?")
    assert_good(rule, lt, "Spielst du vielleicht auf das Bordell neben unsrem Hotel an?")
    assert_good(rule, lt, "Dieses ungeahnt prophetische Wort")
    assert_good(rule, lt, "Das bestätigte Regierungssprecher Steffen Hebestreit am Freitag")
    assert_good(rule, lt, "Es kann gut sein, dass bei sowas Probleme erkannt werden.")

    # relative clauses:
    assert_good(rule, lt, "Das Recht, das Frauen eingeräumt wird.")
    assert_good(rule, lt, "Der Mann, in dem quadratische Fische schwammen.")
    assert_good(rule, lt, "Der Mann, durch den quadratische Fische schwammen.")
    assert_good(rule, lt, "Gutenberg, der quadratische Mann.")
    assert_good(rule, lt, "Die größte Stuttgarter Grünanlage ist der Friedhof.")
    assert_good(rule, lt, "Die meisten Lebensmittel enthalten das.")    # Lebensmittel has NOG as gender in Morphy
    # TODO: Find agreement errors in relative clauses
    assert_bad(rule, lt, "Gutenberg, die Genie.")
    assert_bad(rule, lt, "Wahrlich ein äußerst kritische Jury.", "eine äußerst kritische Jury")
    assert_bad(rule, lt, "Das ist ein enorm großer Auto.", "ein enorm großes Auto")
    # assertBad("Gutenberg, die größte Genie.");
    # assertBad("Gutenberg, die größte Genie aller Zeiten.");
    assert_good(rule, lt, "Die wärmsten Monate sind August und September, die kältesten Januar und Februar.")
    # some of these used to cause false alarms:
    assert_good(rule, lt, "Das Münchener Fest.")
    assert_good(rule, lt, "Das Münchner Fest.")
    assert_good(rule, lt, "Die Planung des Münchener Festes.")
    assert_good(rule, lt, "Das Berliner Wetter.")
    assert_good(rule, lt, "Den Berliner Arbeitern ist das egal.")
    assert_good(rule, lt, "Das Haus des Berliner Arbeiters.")
    assert_good(rule, lt, "Es gehört dem Berliner Arbeiter.")
    assert_good(rule, lt, "Das Stuttgarter Auto.")
    assert_good(rule, lt, "Das Bielefelder Radio.")
    assert_good(rule, lt, "Das Gütersloher Radio.")
    assert_good(rule, lt, "Das wirklich Wichtige kommt jetzt erst.")
    assert_good(rule, lt, "Besonders wenn wir Wermut oder Absinth trinken.")
    assert_good(rule, lt, "Ich wünsche dir alles Gute.")
    assert_good(rule, lt, "Es ist nicht bekannt, mit welchem Alter Kinder diese Fähigkeit erlernen.")
    assert_good(rule, lt, "Dieser ist nun in den Ortungsbereich des einen Roboters gefahren.")
    assert_good(rule, lt, "Wenn dies großen Erfolg hat, werden wir es weiter fördern.")
    assert_good(rule, lt, "Alles Gute!")
    assert_good(rule, lt, "Das bedeutet nichts Gutes.")
    assert_good(rule, lt, "Die Ereignisse dieses einen Jahres waren sehr schlimm.")
    assert_good(rule, lt, "Er musste einen Hochwasser führenden Fluss nach dem anderen überqueren.")
    assert_good(rule, lt, "Darf ich Ihren Füller für ein paar Minuten ausleihen?")
    assert_good(rule, lt, "Bringen Sie diesen Gepäckaufkleber an Ihrem Gepäck an.")
    assert_good(rule, lt, "Extras, die den Wert Ihres Autos erhöhen.")
    assert_good(rule, lt, "Er hat einen 34-jährigen Sohn.")
    assert_good(rule, lt, "Die Polizei erwischte die Diebin, weil diese Ausweis und Visitenkarte hinterließ.")
    assert_good(rule, lt, "Dieses Versäumnis soll vertuscht worden sein - es wurde Anzeige erstattet.")
    assert_good(rule, lt, "Die Firmen - nicht nur die ausländischen, auch die katalanischen - treibt diese Frage um.")
    # TODO: assertGood("Der Obst und Getränke führende Fachmarkt.");
    assert_good(rule, lt, "Stell dich dem Leben lächelnd!")
    assert_good(rule, lt, "Die Messe wird auf das vor der Stadt liegende Ausstellungsgelände verlegt.")
    assert_good(rule, lt, "Sie sind ein den Frieden liebendes Volk.")
    assert_good(rule, lt, "Zum Teil sind das Krebsvorstufen.")
    assert_good(rule, lt, "Er sagt, dass das Rache bedeutet.")
    assert_good(rule, lt, "Wenn das Kühe sind, bin ich ein Elefant.")
    assert_good(rule, lt, "Karl sagte, dass sie niemandem Bescheid gegeben habe.")
    assert_good(rule, lt, "Es blieb nur dieser eine Satz.")
    assert_good(rule, lt, "Oder ist das Mathematikern vorbehalten?")
    assert_good(rule, lt, "Wenn hier einer Fragen stellt, dann ich.")
    assert_good(rule, lt, "Wenn einer Katzen mag, dann meine Schwester.")
    assert_good(rule, lt, "Ergibt das Sinn?")
    assert_good(rule, lt, "Sie ist über die Maßen schön.")
    assert_good(rule, lt, "Ich vertraue ganz auf die Meinen.")
    assert_good(rule, lt, "Was nützt einem Gesundheit, wenn man sonst ein Idiot ist?")
    assert_good(rule, lt, "Auch das hatte sein Gutes.")
    assert_good(rule, lt, "Auch wenn es sein Gutes hatte, war es doch traurig.")
    assert_good(rule, lt, "Er wollte doch nur jemandem Gutes tun.")
    assert_good(rule, lt, "und das erst Jahrhunderte spätere Auftauchen der Legende")
    assert_good(rule, lt, "Texas und New Mexico, beides spanische Kolonien, sind...")
    assert_good(rule, lt, "Texas und New Mexico - beides spanische Kolonien - sind...")
    assert_good(rule, lt, "Texas und New Mexico – beides spanische Kolonien – sind...")
    assert_good(rule, lt, "Weitere Brunnen sind insbesondere der Wittelsbacher und der Vater-Rhein-Brunnen auf der Museumsinsel, beides Werke von Adolf von Hildebrand.")
    assert_good(rule, lt, "Für manche ist das Anlass genug, darüber nicht weiter zu diskutieren.")
    assert_good(rule, lt, "Vielleicht schreckt das Frauen ab.")
    assert_good(rule, lt, "Unser Hund vergräbt seine Knochen im Garten.")
    assert_good(rule, lt, "Ob das Mehrwert bringt?")
    assert_good(rule, lt, "Warum das Sinn macht?")
    assert_good(rule, lt, "Das hängt davon ab, ob die Deutsch sprechen")
    assert_good(rule, lt, "Die meisten Coaches wissen nichts.")
    assert_good(rule, lt, "Die Präsent AG.")
    assert_good(rule, lt, "In New York war er der Titelheld in Richard III. und spielte den Mark Anton in Julius Cäsar.")
    assert_good(rule, lt, "Vielen Dank fürs Bescheid geben.")
    assert_good(rule, lt, "Welche Display Ads?")
    assert_good(rule, lt, "Das letzte Mal war das Anfang der 90er Jahre des vergangenen Jahrhunderts")
    assert_good(rule, lt, "Der vom Rat der Justizminister gefasste Beschluss zur Aufnahme von Vertriebenen...")
    assert_good(rule, lt, "Der letzte Woche vom Rat der Justizminister gefasste Beschluss zur Aufnahme von Vertriebenen...")
    assert_good(rule, lt, "Was war sie nur für eine dumme Person!")
    assert_good(rule, lt, "Was war ich für ein Idiot!")
    assert_good(rule, lt, "Was für ein Idiot!")
    assert_good(rule, lt, "Was für eine blöde Kuh!")
    assert_good(rule, lt, "Was ist sie nur für eine blöde Kuh!")
    assert_good(rule, lt, "Wie viele Paar Stiefel brauche ich eigentlich?")
    assert_good(rule, lt, "Dieses versuchten Mathematiker 400 Jahre lang vergeblich zu beweisen.")
    # assertGood("Bei dem Papierabzüge von Digitalbildern bestellt werden.");
    assert_good(rule, lt, "Gemälde informieren uns über das Leben von den vergangenen Jahrhunderten…")
    assert_good(rule, lt, "Die Partei, die bei den vorangegangenen Wahlen noch seine Politik unterstützt hatte.")
    assert_good(rule, lt, "Bei Zunahme der aufgelösten Mineralstoffe, bei denen...")
    assert_good(rule, lt, "Je mehr Muskelspindeln in einem Muskel vorhanden sind, desto feiner können die mit diesem verbundenen Bewegungen abgestimmt werden.")
    assert_good(rule, lt, "Diese datentechnischen Operationen werden durch Computerprogramme ausgelöst, d. h. über entsprechende, in diesen enthaltene Befehle (als Teil eines implementierten Algorithmus') vorgegeben.")
    assert_good(rule, lt, "Aus diesen resultierten Konflikte wie der Bauernkrieg und der Pfälzische Erbfolgekrieg.")
    assert_good(rule, lt, "Die Staatshandlungen einer Mikronation und von dieser herausgegebene Ausweise, Urkunden und Dokumente gelten im Rechtsverkehr als unwirksam")
    assert_good(rule, lt, "Auf der Hohen See und auf den mit dieser verbundenen Gewässern gelten die internationalen Kollisionsverhütungsregeln.")
    assert_good(rule, lt, "Art. 11 Abs. 2 GGV setzt dem bestimmte Arten der außergemeinschaftlichen Zugänglichmachung gleich")
    assert_good(rule, lt, "Grundsätzlich sind die Heilungschancen von Männern mit Brustkrebs nicht schlechter als die betroffener Frauen.")
    assert_good(rule, lt, "In diesem Viertel bin ich aufgewachsen.")
    assert_good(rule, lt, "Im November wurde auf dem Gelände der Wettbewerb ausgetragen.")
    assert_good(rule, lt, "Er ist Eigentümer des gleichnamigen Schemas und stellt dieses interessierten Domänen zur Verfügung.")
    assert_good(rule, lt, "Dort finden sie viele Informationen rund um die Themen Schwangerschaft, Geburt, Stillen, Babys und Kinder.")
    assert_good(rule, lt, "Die Galerie zu den Bildern findet sich hier.")
    assert_good(rule, lt, "Ganz im Gegensatz zu den Blättern des Brombeerstrauches.")
    assert_good(rule, lt, "Er erzählte von den Leuten und den Dingen, die er auf seiner Reise gesehen hatte.")
    assert_good(rule, lt, "Diese Partnerschaft wurde 1989 nach dem Massaker auf dem Platz des Himmlischen Friedens eingefroren.")
    assert_good(rule, lt, "Die Feuergefahr hingegen war für für die Londoner Teil des Alltags.")
    assert_good(rule, lt, "Was ist, wenn ein Projekt bei den Berliner Type Awards mit einem Diplom ausgezeichnet wird?")
    assert_good(rule, lt, "Was ist mit dem Liechtensteiner Kulturleben los?")
    assert_good(rule, lt, "Das ist der Mann den Präsident Xi Jinping verurteilte.")
    assert_good(rule, lt, "Wie viele Kolleg/-innen haben sie?")
    assert_good(rule, lt, "Die Ideen der neuen Kolleg/-innen sind gut!")
    # incorrect sentences:
    assert_bad(rule, lt, "Ein Buch mit einem ganz ähnlichem Titel.")
    assert_bad(rule, lt, "Meiner Chef raucht.")
    assert_bad(rule, lt, "Er hat eine 34-jährigen Sohn.")
    assert_bad(rule, lt, "Es sind die Tisch.", "die Tische", "der Tisch", "den Tisch", "dem Tisch")
    assert_bad(rule, lt, "Es sind das Tisch.", "der Tisch", "den Tisch", "dem Tisch")
    assert_bad(rule, lt, "Es sind die Haus.", "das Haus", "dem Haus", "die Häuser")
    assert_bad(rule, lt, "Es sind der Haus.", "dem Haus", "das Haus", "der Häuser")
    assert_bad(rule, lt, "Es sind das Frau.", "die Frau", "der Frau")
    assert_bad(rule, lt, "Das Auto des Mann.", "der Mann", "den Mann", "dem Mann", "des Manns", "des Mannes")
    assert_bad(rule, lt, "Das interessiert das Mann.", "der Mann", "den Mann", "dem Mann")
    assert_bad(rule, lt, "Das interessiert die Mann.", "der Mann", "den Mann", "dem Mann", "die Männer")
    assert_bad(rule, lt, "Das Auto ein Mannes.", "ein Mann", "eines Mannes")
    assert_bad(rule, lt, "Das Auto einem Mannes.", "eines Mannes", "einem Mann")
    assert_bad(rule, lt, "Das Auto einer Mannes.", "eines Mannes")
    assert_bad(rule, lt, "Das Auto einen Mannes.", "eines Mannes", "einen Mann")
    assert_bad(rule, lt, "Die Galerie zu den Bilder findet sich hier.")
    assert_bad(rule, lt, "Ganz im Gegensatz zu den Blätter des Brombeerstrauches.")
    assert_good(rule, lt, "Das erlaubt Forschern, neue Versuche durchzuführen.")
    assert_good(rule, lt, "Dies ermöglicht Forschern, neue Versuche durchzuführen.")
    assert_good(rule, lt, "Je länger zugewartet wird, desto schwieriger dürfte es werden, die Jungtiere von den Elterntieren zu unterscheiden.")
    assert_good(rule, lt, "Er schrieb ein von 1237 bis 1358 reichendes Geschichtswerk, dessen Schwerpunkt auf den Ereignissen in der Lombardei liegt.")
    assert_good(rule, lt, "Private Veranstaltungen waren, darauf hat die Strandhaus Norderstedt GmbH im Rahmen rechtlicher Klärungen selbst bestanden, nicht Bestandteil dieser Verträge.")
    assert_bad(rule, lt, "Die erwähnt Konferenz ist am Samstag.")
    assert_bad(rule, lt, "Die erwähntes Konferenz ist am Samstag.")
    assert_bad(rule, lt, "Die erwähnten Konferenz ist am Samstag.")
    assert_bad(rule, lt, "Die erwähnter Konferenz ist am Samstag.")
    assert_bad(rule, lt, "Die erwähntem Konferenz ist am Samstag.")
    assert_bad(rule, lt, "Die gemessen Werte werden in die länderspezifische Höhe über dem Meeresspiegel umgerechnet.")
    assert_bad(rule, lt, "Darüber hinaus haben wir das berechtigte Interessen, diese Daten zu verarbeiten.")
    assert_bad(rule, lt, "Eine Amnestie kann den Hingerichteten nicht das Leben und dem heimgesuchten Familien nicht das Glück zurückgeben.")
    # assertBad("Zu den gefährdete Vögeln Malis gehören der Strauß, Großtrappen und Perlhuhn.");
    # assertBad("Zu den gefährdete Vögel Malis gehören der Strauß, Großtrappen und Perlhuhn.");
    assert_bad(rule, lt, "Z. B. therapeutisches Klonen, um aus den gewonnen Zellen in vitro Ersatzorgane für den Patienten zu erzeugen")
    # assertBad("Gemälde informieren uns über das Leben von den vergangenen Jahrhunderte…");
    assert_bad(rule, lt, "Die Partei, die bei den vorangegangen Wahlen noch seine Politik unterstützt hatte.")
    assert_bad(rule, lt, "Bei Zunahme der aufgelösten Mineralstoffen, bei denen...")
    assert_bad(rule, lt, "Durch die große Vielfalt der verschiedene Linien ist für jeden Anspruch die richtige Brille im Portfolio.")
    assert_bad(rule, lt, "In diesen Viertel bin ich aufgewachsen.")
    assert_bad(rule, lt, "Im November wurde auf den Gelände der Wettbewerb ausgetragen.")
    assert_bad(rule, lt, "Dort finden sie Testberichte und viele Informationen rund um das Themen Schwangerschaft, Geburt, Stillen, Babys und Kinder.")
    assert_bad(rule, lt, "Je länger zugewartet wird, desto schwieriger dürfte es werden, die Jungtiere von den Elterntiere zu unterscheiden.")
    assert_bad(rule, lt, "Er schrieb ein von 1237 bis 1358 reichendes Geschichtswerk, dessen Schwerpunkt auf den Ereignisse in der Lombardei liegt.")
    assert_bad(rule, lt, "Des großer Mannes.")
    assert_bad(rule, lt, "Er erzählte von den Leute und den Dingen, die er gesehen hatte.")
    assert_bad(rule, lt, "Diese Partnerschaft wurde 1989 nach den Massaker auf dem Platz des Himmlischen Friedens eingefroren.")

    assert_bad(rule, lt, "Das Dach von meine Auto.", "meinem Auto")
    assert_bad(rule, lt, "Das Dach von meinen Auto.", "meinem Auto", "meinen Autos")

    assert_bad(rule, lt, "Das Dach mein Autos.", "mein Auto", "meine Autos", "meines Autos", "meinen Autos", "meiner Autos")
    assert_bad(rule, lt, "Das Dach meinem Autos.", "meinem Auto", "meines Autos", "meine Autos", "meinen Autos", "meiner Autos")

    assert_bad(rule, lt, "Das Dach meinem großen Autos.")
    assert_bad(rule, lt, "Das Dach mein großen Autos.")

    assert_bad(rule, lt, "Das Klientel der Partei.", "Die Klientel", "Der Klientel")    # gender used to be wrong in Morphy data
    assert_good(rule, lt, "Die Klientel der Partei.")

    assert_bad(rule, lt, "Der Haus ist groß", "Dem Haus", "Das Haus", "Der Häuser")
    assert_bad(rule, lt, "Aber der Haus ist groß", "dem Haus", "das Haus", "der Häuser")

    assert_bad(rule, lt, "Ich habe einen Feder gefunden.", "eine Feder", "einer Feder")

    assert_good(rule, lt, "Wenn die Gott zugeschriebenen Eigenschaften stimmen, dann...")
    assert_good(rule, lt, "Dieses Grünkern genannte Getreide ist aber nicht backbar.")
    assert_good(rule, lt, "Außerdem unterstützt mich Herr Müller beim abheften")
    assert_good(rule, lt, "Außerdem unterstützt mich Frau Müller beim abheften")
    assert_bad(rule, lt, "Der Zustand meiner Gehirns.")

    assert_bad(rule, lt, "Lebensmittel sind da, um den menschliche Körper zu ernähren.")
    assert_bad(rule, lt, "Geld ist da, um den menschliche Überleben sicherzustellen.")
    assert_bad(rule, lt, "Sie hatte das kleinen Kaninchen.")
    assert_bad(rule, lt, "Frau Müller hat das wichtigen Dokument gefunden.")
    assert_bad(rule, lt, "Ich gebe dir ein kleine Kaninchen.")
    assert_bad(rule, lt, "Ich gebe dir ein kleinen Kaninchen.")
    assert_bad(rule, lt, "Ich gebe dir ein kleinem Kaninchen.")
    assert_bad(rule, lt, "Ich gebe dir ein kleiner Kaninchen.")
    # assertBad("Ich gebe dir ein klein Kaninchen.");  // already detected by MEIN_KLEIN_HAUS
    assert_good(rule, lt, "Ich gebe dir ein kleines Kaninchen.")

    assert_bad(rule, lt, "Ich gebe dir das kleinen Kaninchen.")
    assert_bad(rule, lt, "Ich gebe dir das kleinem Kaninchen.")
    assert_bad(rule, lt, "Ich gebe dir das kleiner Kaninchen.")
    assert_bad(rule, lt, "Geprägt ist der Platz durch einen 142 Meter hoher Obelisken", "einen 142 Meter hohen Obelisken")
    assert_bad(rule, lt, "Es birgt für mich ein überraschend hohes juristische Risiko.", "ein überraschend hohes juristisches Risiko")
    assert_bad(rule, lt, "Es birgt für mich ein zu hohes juristische Risiko.", "ein zu hohes juristisches Risiko")
    # assertBad("Ich gebe dir das kleines Kaninchen.");  // already detected by ART_ADJ_SOL
    # assertBad("Ich gebe dir das klein Kaninchen.");  // already detected by MEIN_KLEIN_HAUS
    assert_good(rule, lt, "Ich gebe dir das kleine Kaninchen.")
    assert_good(rule, lt, "Die Top 3 der Umfrage")
    assert_good(rule, lt, "Dein Vorschlag befindet sich unter meinen Top 5.")
    assert_good(rule, lt, "Unter diesen rief das großen Unmut hervor.")
    assert_good(rule, lt, "Bei mir löste das Panik aus.")
    assert_good(rule, lt, "Sie können das machen in dem sie die CAD.pdf öffnen.")
    assert_good(rule, lt, "Ich mache eine Ausbildung zur Junior Digital Marketing Managerin.")

    assert_good(rule, lt, "Dann wird das Konsequenzen haben.")
    assert_good(rule, lt, "Dann hat das Konsequenzen.")
    assert_good(rule, lt, "Sollte das Konsequenzen nach sich ziehen?")
    assert_good(rule, lt, "Der Echo Show von Amazon")
    assert_good(rule, lt, "Die BVG kommen immer zu spät.")
    assert_good(rule, lt, "In der Frühe der Nacht.")
    assert_good(rule, lt, "Der TV Steinfurt.")
    assert_good(rule, lt, "Ein ID 3 von Volkswagen.")
    assert_good(rule, lt, "Der ID.3 von Volkswagen.")
    assert_good(rule, lt, "Der ID3 von Volkswagen.")
    assert_good(rule, lt, "Das bedeutet Krieg!")
    assert_good(rule, lt, "Im Tun zu sein verhindert Prokrastination.")

    assert_bad(rule, lt, "Hier steht Ihre Text.")
    assert_bad(rule, lt, "Hier steht ihre Text.")
    assert_bad(rule, lt, "Antje Last, Inhaberin des Berliner Kult Hotels Auberge, freute sich ebenfalls über die Gastronomenfamilie aus Bayern.")

    assert_bad(rule, lt, "Das ist doch lächerlich, was ist denn das für ein Klinik?")
    assert_good(rule, lt, "Das ist doch lächerlich, was ist denn das für eine Klinik?")
    assert_good(rule, lt, "Was ist denn das für ein Typ?")
    assert_good(rule, lt, "Hier geht's zur Customer Journey.")
    assert_good(rule, lt, "Das führt zur Verbesserung der gesamten Customer Journey.")
    assert_good(rule, lt, "Meint er das wirklich Ernst?")
    assert_good(rule, lt, "Meinen Sie das Ernst?")
    assert_good(rule, lt, "Die können sich in unserer Hall of Fame verewigen.")
    assert_good(rule, lt, "Die können sich in unserer neuen Hall of Fame verewigen.")
    assert_good(rule, lt, "Auch, wenn das weite Teile der Bevölkerung betrifft.")
    assert_good(rule, lt, "Hat das Einfluss auf Ihr Trinkverhalten?")
    assert_good(rule, lt, "Ihr wisst aber schon, dass das Blödsinn ist.")

    assert_bad(rule, lt, "Ich weiß nicht mehr, was unser langweiligen Thema war.")
    assert_good(rule, lt, "Aber mein Wissen über die Antike ist ausbaufähig.")
    assert_bad(rule, lt, "Er ging ins Küche.")
    assert_bad(rule, lt, "Er ging ans Luft.")
    assert_bad(rule, lt, "Eine Niereninsuffizienz führt zur Störungen des Wasserhaushalts.")
    assert_bad(rule, lt, "Er stieg durchs Fensters.")
    assert_bad(rule, lt, "Ich habe heute ein Krankenwagen gesehen.")
    assert_good(rule, lt, "Sie werden merken, dass das echte Nutzer sind.")
    assert_good(rule, lt, "Dieses neue Mac OS trug den Codenamen Rhapsody.")
    assert_good(rule, lt, "Das Mac OS is besser als Windows.")
    assert_good(rule, lt, "Damit steht das Porsche Museum wie kaum ein anderes Museum für Lebendigkeit und Abwechslung.")
    assert_good(rule, lt, "Weitere Krankenhäuser sind dass Eastern Shore Memorial Hospital, IWK Health Centre, Nova Scotia Hospital und das Queen Elizabeth II Health Sciences Centre.")
    assert_good(rule, lt, "Ich bin von Natur aus ein sehr neugieriger Mensch.")
    assert_good(rule, lt, "Ich bin auf der Suche nach einer Junior Developerin.")
    assert_good(rule, lt, "War das Eifersucht?")
    assert_good(rule, lt, "Waren das schwierige Entscheidungen?")
    assert_good(rule, lt, "Soll das Demokratie sein?")
    assert_good(rule, lt, "Hat das Spaß gemacht?")
    assert_bad(rule, lt, "Funktioniert das Software auch mit Windows?")
    assert_good(rule, lt, "Soll das Sinn stiften?")
    assert_good(rule, lt, "Soll das Freude machen?")
    assert_good(rule, lt, "Die Trial ist ausgelaufen.")
    assert_good(rule, lt, "Ein geworbener Neukunde interagiert zusätzlich mit dem Unternehmen.")
    assert_good(rule, lt, "Ich weiß, dass jeder LanguageTool benutzen sollte.")
    assert_good(rule, lt, "1992 übernahm die damalige Ernst Klett Schulbuchverlag GmbH, Stuttgart, den reprivatisierten Verlag Haack Gotha")
    assert_good(rule, lt, "Überlegst du dir einen ID.3 zu leasen?")
    assert_good(rule, lt, "Der Deutsch Langhaar ist ein mittelgroßer Jagdhund")
    assert_good(rule, lt, "Eine Lösung die Spaß macht")
    assert_good(rule, lt, "Mir machte das Spaß.")
    assert_good(rule, lt, "Wir möchten nicht, dass irgendjemand Fragen stellt.")
    assert_good(rule, lt, "Die Multiple Sklerose hat 1000 Gesichter.")
    assert_good(rule, lt, "Na ja, einige nennen das Freundschaft plus, aber das machen wir besser nicht.")
    assert_good(rule, lt, "Vogue, eigentlich als B-Seite der letzten Like A Prayer-Auskopplung Keep It Together gedacht, wurde kurzfristig als eigenständige Single herausgebracht")
    assert_good(rule, lt, "..., die laufend Gewaltsituationen ausgeliefert sind")
    assert_good(rule, lt, "Dann folgte die Festnahme der dringend Tatverdächtigen.")
    assert_good(rule, lt, "Von der ersten Spielminute an machten die Münsteraner Druck und ...")
    assert_good(rule, lt, "Wenn diese Prognose bestätigt wird, wird empfohlen, dass Unternehmen die gefährliche Güter benötigen, die Transporte am Montag und Dienstag machen.")

    assert_good(rule, lt, "Ich habe meine Projektidee (die riesiges finanzielles Potenzial hat) an einen Unternehmenspräsidenten geschickt.")
    assert_good(rule, lt, "Als weitere Rechtsquelle gelten gelegentlich noch immer der Londoner Court of Appeal und das britische House of Lords.")
    assert_good(rule, lt, "Die Evangelische Kirche befindet sich in der Bad Sodener Altstadt direkt neben dem Quellenpark.")
    assert_good(rule, lt, "Der volle Windows 10 Treibersupport")
    assert_good(rule, lt, "Zugleich stärkt es die renommierte Berliner Biodiversitätsforschung.")
    assert_good(rule, lt, "Der Windows 10 Treibersupport")
    assert_good(rule, lt, "Kennt irgendwer Tipps wie Kopfhörer länger halten?")
    assert_good(rule, lt, "George Lucas 1999 über seine sechsteilige Star Wars Saga.")
    assert_good(rule, lt, "… und von denen mehrere Gegenstand staatsanwaltlicher Ermittlungen waren.")
    assert_good(rule, lt, "Natürlich ist das Quatsch!")
    assert_good(rule, lt, "Die Xi Jinping Ära ist …")
    assert_good(rule, lt, "Die letzte unter Windows 98 lauffähige Version ist 5.1.")
    assert_good(rule, lt, "Das veranlasste Bürgermeister Adam, selbst tätig zu werden, denn er wollte es nicht zulassen, dass in seiner Stadt Notleidende ohne Hilfe dastehen.")
    assert_good(rule, lt, "Die südlichste Düsseldorfer Rheinbrücke ist die Fleher Brücke, eine Schrägseilbrücke mit dem höchsten Brückenpylon in Deutschland und einer Vielzahl von fächerförmig angeordneten Seilen.")
    assert_good(rule, lt, "Ein zeitweise wahres Stakkato an einschlägigen Patenten, das Benz & Cie.")
    assert_good(rule, lt, "Wem Rugby nicht sehr geläufig ist, dem wird auch das Six Nations nicht viel sagen.")
    assert_good(rule, lt, "Eine Boeing 767 der Air China stürzt beim Landeanflug in ein Waldgebiet.")
    assert_good(rule, lt, "Wir sind immer offen für Mitarbeiter die Teil eines der traditionellsten Malerbetriebe auf dem Platz Zürich werden möchten.")
    assert_good(rule, lt, "Gelingt das mit Erregern rechtzeitig, könnte das Infektionen sogar oft verhindern.")
    assert_good(rule, lt, "In der aktuellen Niedrigzinsphase bedeutet das sehr geringe Zinsen, die aber deutlich ansteigen können.")
    assert_good(rule, lt, "Es gibt viele Stock Screener.")
    assert_bad(rule, lt, "So soll er etwa Texte des linken Literaturwissenschaftler Helmut Lethen mit besonderem Interesse gelesen haben.")    # "weiterverxxx" = unbekanntes Wort
    assert_bad(rule, lt, "Auf dieser Website werden allerdings keine solche Daten weiterverxxx.")    # "weiterverxxx" = unbekanntes Wort
    assert_bad(rule, lt, "Bei größeren Gruppen und/oder mehrere Tagen gibts einen nennenswerten Nachlass.")
    assert_good(rule, lt, "Wir gehen zur Learning Academy.")
    assert_good(rule, lt, "Es ist ein stiller Bank Run.")
    assert_good(rule, lt, "Whirlpool Badewanne der europäische Marke SPAtec Modell Infinity.")
    assert_good(rule, lt, "1944 eroberte diese weite Teile von Südosteuropa.")
    assert_good(rule, lt, "Auch die Monopolstellung des staatlichen All India Radio, das in 24 Sprachen sendet")
    assert_good(rule, lt, "Das schwedischen Entwicklerstudio MachineGames hat uns vor drei Jahren mit Wolfenstein: The New Order positiv überrascht.")
    assert_good(rule, lt, "In einem normalen Joint habe es etwa ein halbes Gramm Hanf.")
    assert_good(rule, lt, "den leidenschaftlichen Lobpreis der texanischen Gateway Church aus")
    assert_good(rule, lt, "die gegnerischen Shooting Guards")
    assert_good(rule, lt, "Bald läppert sich das zu richtigem Geld zusammen.")
    assert_good(rule, lt, "Die Weimarer Parks laden ja förmlich ein zu Fotos im öffentlichen Raum.")
    assert_good(rule, lt, "Es is schwierig für mich, diese zu Sätzen zu verbinden.")
    assert_good(rule, lt, "Es kam zum einen zu technischen Problemen, zum anderen wurde es unübersichtlich.")
    assert_good(rule, lt, "Das Spiel wird durch den zu neuer Größe gewachsenen Torwart dominiert.")
    assert_good(rule, lt, "Dort findet sich schlicht und einfach alles & das zu sagenhafter Hafenkulisse.")
    assert_good(rule, lt, "Man darf gespannt sein, wen Müller für diese Aufgabe gewinnt.")
    assert_good(rule, lt, "Das Vereinslokal in welchem Zusammenkünfte stattfinden.")
    assert_good(rule, lt, "Er lässt niemanden zu Wort kommen.")
    assert_good(rule, lt, "Es war eine alles in allem spannende Geschichte.")
    assert_good(rule, lt, "Eine mehrere hundert Meter lange Startbahn.")
    assert_good(rule, lt, "Wir müssen jetzt um ein vielfaches höhere Preise zahlen.")
    assert_good(rule, lt, "Und eine von manchem geforderte Übergewinnsteuer.")
    assert_good(rule, lt, "Sie hat niemandem wirkliches Leid zugefügt.")
    assert_good(rule, lt, "Die Organe eines gerade Verstorbenen")
    assert_good(rule, lt, "Da wusste keiner Bescheid bezüglich dieser Sache.")
    assert_good(rule, lt, "Es braucht keiner Bescheid wissen.")
    assert_good(rule, lt, "Das sind auch beides staatliche Organe.")
    assert_good(rule, lt, "Ein Haus für die weniger Glücklichen.")
    assert_good(rule, lt, "Wir können sowas Mittwoch machen.")
    assert_good(rule, lt, "Den schlechter Verdienenden geht es schlecht.")
    assert_good(rule, lt, "Mit der weit weniger bekannten Horrorkomödie begann ihre Karriere.")
    assert_bad(rule, lt, "Mit der weit weniger bekannte Horrorkomödie begann ihre Karriere.", "der weit weniger bekannten Horrorkomödie")
    assert_good(rule, lt, "Die Adelmanns wohnen in Herford.")
    assert_bad(rule, lt, "Die Idee des Werbekaufmann kam gut an.")
    assert_good(rule, lt, "Die Idee des Werbekaufmanns kam gut an.")
    assert_good(rule, lt, "Solch harte Worte!")
    assert_good(rule, lt, "Ich habe es an unseren amerikanischen Commercial Lawyer geschickt.")
    assert_good(rule, lt, "Dieser eine Schritt hat gedauert.")
    assert_good(rule, lt, "Es besteht durchaus die Gefahr, dass die Telekom eine solch starke monopolistische Stellung auf dem Markt hat, dass sich kaum Wettbewerb entfalten kann.")
    assert_bad(rule, lt, "Ich habe keine Zeit für solche kleinlichen Belangen.")
    assert_good(rule, lt, "Wenn ein Tiger einen Menschen tötet, ist das Grausamkeit.")
    assert_good(rule, lt, "Kombinieren Sie diese zu ganzen Bewegungsprogrammen")
    assert_bad(rule, lt, "Einen Dämonen wird er nicht aufhalten.")
    assert_bad(rule, lt, "Das versetzte den Kronprinz in Schrecken.")
    assert_good(rule, lt, "Erst später wurde Kritik hauptsächlich an den Plänen zu einem Patriot Act II laut.")
    assert_good(rule, lt, "Laut Charlie XCX selbst sind das Personen, die vielleicht eine ...")
    # TODO:
    # assertBad("Solch hartes Worte!");
    # unsure:
    # assertGood("Wie konnte mir solch Feindseligkeit innerhalb meiner Familie entgehen?");
    # assertGood("Es ist schon faszinierend wie verzaubernd solch Klänge wirken und dann die facettenreiche Programmzusammenstellung bei Tango und Polka die Besucher im „Sturm“ mitreißen. ");
    assert_bad(rule, lt, "Solche kleinen Anbietern nutzen dann eines der drei großen Mobilfunknetze Deutschlands.")
    assert_good(rule, lt, "Solch frivolen Gedanken wollen wir gar nicht erst nachgehen.")
    assert_good(rule, lt, "Er erwartete solch aggressives Verhalten.")
    assert_good(rule, lt, "Eine solch schöne Frau.")
    assert_good(rule, lt, "Einer solch schönen Frau.")
    assert_good(rule, lt, "Ein solch schöner Tisch.")
    assert_good(rule, lt, "Ein solch schöner neuer Tisch.")
    assert_good(rule, lt, "Eine solch begnadete Fotografin mit dabei zu haben und Tipps für die Fotosession zu bekommen, wäre schon toll.")
    assert_good(rule, lt, "Wie können wir als globale Gemeinschaft solch brennende Themen wie Klimawandel und Rezession in entwickelten Märkten in Angriff nehmen?")
    assert_good(rule, lt, "Wir waren überrascht, von ihm solch beißende Bemerkungen über seinen besten Freund zu hören.")
    assert_good(rule, lt, "Worten, wohl gewählt, wohnt solch große Macht inne.")
    assert_good(rule, lt, "Warum gelingt es den Stuten die Hengste in solch großen Rennen zu schlagen.")
    assert_good(rule, lt, "Eine solch gute Beratung kann natürlich nicht kostenlos sein, daher lassen Sie mich bitte wissen welche Kosten für die PKV und BU-Beratung auf mich zukommen werden.")
    assert_good(rule, lt, "Ein solch großer Ausbruch außerhalb des Nahen Ostens ist eine neue Entwicklung, heißt es weiter.")
    assert_good(rule, lt, "Natürlich dürfen unsere Sporteinheiten nicht fehlen, vor allem nicht bei solch gutem Essen.")
    assert_good(rule, lt, "Wie konnten Sie solch harte Songs gegen Ihre Familie schreiben?")
    assert_good(rule, lt, "Zur Krönung auf dem schönsten Aussichtsberg in der Ferienregion Tirol West gelegen, bietet die Venet Gipfelhütte alle Annehmlichkeiten, die man sich auf solch hohem Niveau (2.212 m) wünschen kann.")
    assert_good(rule, lt, "Vor allem nicht einen, der sich ein solch hohen Ballbesitz organisierte und die Berliner nicht zur Entfaltung kommen ließ.")
    assert_good(rule, lt, "Du solltest im Winter keinen solch hohen Berg besteigen.")
    assert_good(rule, lt, "Man darf an dieser Stelle fragen, wie ein solch hoher Verlust zustande kommt, wo doch der Stuttgarter Weg aus Sparen bestand.")
    assert_good(rule, lt, "Kann der Patient eine solch lange Operation überstehen?")
    assert_good(rule, lt, "Er kennt sich aus mit solch monumentalen Projekten.")
    assert_good(rule, lt, "Eine solch schöne hübsche Frau.")
    assert_good(rule, lt, "Bisher hat Gül einen solch offenen Affront gegen die ErdoganRegierung vermieden.")
    assert_bad(rule, lt, "..., das heißt solche natürliche Personen, welche unsere Leistungen in Anspruch nehmen, ...")
    assert_bad(rule, lt, "Der Erwerb solcher kultureller Güter ist natürlich stark an das ökonomische Kapital gebunden.")
    assert_good(rule, lt, "Umso dankbarer bin ich für Brüder, die klare Kante in theologischer Hinsicht zeigen und nachvollziehbar die Bibel auch in solch schwierigen unpopulären Themen auslegen.")
    assert_bad(rule, lt, "Wir haben das Abo beendet und des Betrag erstattet.")
    # TODO: not yet detected:
    # assertBad("Erst recht wir fleißiges Arbeiter.");
    # assertBad("Erst recht ich fleißiges Arbeiter.");
    # assertBad("Das Dach meine großen Autos.");
    # assertBad("Das Dach meinen großen Autos.");
    # assertBad("Das Dach meine Autos.");
    # assertBad("Es ist das Haus dem Mann.");
    # assertBad("Das interessiert der Männer.");
    # assertBad("Das interessiert der Mann.");
    # assertBad("Das gehört den Mann."); // detected by DEN_DEM
    # assertBad("Es sind der Frau.");


def test_zur_replacement(rule, lt):
    """AgreementRuleTest.testZurReplacement"""
    assert_bad(rule, lt, "Hier geht's zur Schrank.", "zum Schrank")
    assert_bad(rule, lt, "Hier geht's zur Schränken.", "zum Schränken", "zu Schränken")
    assert_bad(rule, lt, "Hier geht's zur Männern.", "zu Männern")
    assert_bad(rule, lt, "Hier geht's zur Portal.", "zum Portal")
    assert_bad(rule, lt, "Hier geht's zur Portalen.", "zu Portalen")
    assert_bad(rule, lt, "Sie gehen zur Frauen.", "zu Frauen", "zur Frau")
    assert_bad(rule, lt, "Niereninsuffizienz führt zur Störungen des Wasserhaushalts.", "zu Störungen", "zur Störung")
    assert_bad(rule, lt, "Das Motiv wird in der Klassik auch zur Darstellungen übernommen.", "zu Darstellungen", "zur Darstellung")
    assert_good(rule, lt, "Hier geht's zur Sonne.")
    assert_good(rule, lt, "Hier geht's zum Schrank.")
    assert_good(rule, lt, "Niereninsuffizienz führt zu Störungen des Wasserhaushalts.")
    assert_good(rule, lt, "Das hat der fließend Englisch sprechende Mitarbeiter veranlasst.")


def test_viele_wenige(rule, lt):
    """AgreementRuleTest.testVieleWenige"""
    assert_good(rule, lt, "Zusammenschluss mehrerer dörflicher Siedlungen an einer Furt")
    assert_good(rule, lt, "Für einige markante Szenen")
    assert_good(rule, lt, "Für einige markante Szenen baute Hitchcock ein Schloss.")
    assert_good(rule, lt, "Haben Sie viele glückliche Erfahrungen in Ihrer Kindheit gemacht?")
    assert_good(rule, lt, "Es gibt viele gute Sachen auf der Welt.")
    assert_good(rule, lt, "Viele englische Wörter haben lateinischen Ursprung")
    assert_good(rule, lt, "Ein Bericht über Fruchtsaft, einige ähnliche Erzeugnisse und Fruchtnektar")
    assert_good(rule, lt, "Der Typ, der seit einiger Zeit immer wieder hierher kommt.")
    assert_good(rule, lt, "Jede Schnittmenge abzählbar vieler offener Mengen")
    assert_good(rule, lt, "Es kam zur Fusion der genannten und noch einiger weiterer Unternehmen.")
    assert_good(rule, lt, "Zu dieser Fragestellung gibt es viele unterschiedliche Meinungen.")
    assert_good(rule, lt, "Wir zeigen die Gründe auf, wieso noch nicht jeder solche Anschlüsse hat.")


def test_regression():
    """AgreementRuleTest.testRegression"""
    lt = JLanguageTool(get_language('de-DE'))
    # used to be not detected > 1.0.1:
    s = "Und so.\r\nDie Bier."
    matches = lt.check(s)
    assert len(matches) == 1


def test_det_adj_noun_rule(rule, lt):
    """AgreementRuleTest.testDetAdjNounRule"""
    # correct sentences:
    assert_good(rule, lt, "Die Übernahme der früher selbständigen Gesellschaft")
    assert_good(rule, lt, "Das ist, weil man oft bei anderen schreckliches Essen vorgesetzt bekommt.")
    assert_good(rule, lt, "Das ist der riesige Tisch.")
    assert_good(rule, lt, "Der riesige Tisch ist groß.")
    assert_good(rule, lt, "Die Kanten der der riesigen Tische.")
    assert_good(rule, lt, "Den riesigen Tisch mag er.")
    assert_good(rule, lt, "Es mag den riesigen Tisch.")
    assert_good(rule, lt, "Die Kante des riesigen Tisches.")
    assert_good(rule, lt, "Dem riesigen Tisch fehlt was.")
    assert_good(rule, lt, "Die riesigen Tische sind groß.")
    assert_good(rule, lt, "Der riesigen Tische wegen.")
    assert_good(rule, lt, "An der roten Ampel.")
    assert_good(rule, lt, "Dann hat das natürlich Nachteile.")
    assert_good(rule, lt, "Ihre erste Nr. 1")
    assert_good(rule, lt, "Wir bedanken uns bei allen Teams.")
    assert_good(rule, lt, "Als Heinrich versuchte, seinen Kandidaten für den Mailänder Bischofssitz durchzusetzen, reagierte der Papst sofort.")
    assert_good(rule, lt, "Den neuen Finanzierungsweg wollen sie daher Hand in Hand mit dem Leser gehen.")
    assert_good(rule, lt, "Lieber den Spatz in der Hand...")
    assert_good(rule, lt, "Wir wollen sein ein einzig Volk von Brüdern")
    assert_good(rule, lt, "Eine Zeitreise durch die 68er Revolte")
    assert_good(rule, lt, "Ich besitze ein Modell aus der 300er Reihe.")
    assert_good(rule, lt, "Aber ansonsten ist das erste Sahne")
    assert_good(rule, lt, "...damit diese ausreichend Sauerstoff geben.")
    assert_good(rule, lt, "...als auch die jedem zukommende Freiheit.")
    assert_good(rule, lt, "...als auch die daraus jedem zukommende Freiheit.")
    assert_good(rule, lt, "Damit zeigen wir, wie bedeutungsreich manche deutsche Begriffe sein können.")    # http://mediawiki.ids-mannheim.de/VarGra/index.php/Starke_/_schwache_Flexion_des_Adjektivs_und_Substantivs_nach_Artikelw%C3%B6rtern,_artikelartigen_W%C3%B6rtern_und_Pronomen
    assert_good(rule, lt, "Damit zeigen wir, wie bedeutungsreich manche deutschen Begriffe sein können.")
    assert_good(rule, lt, "2009 gab es im Rathaus daher Bestrebungen ein leichter handhabbares Logo einzuführen.")
    assert_good(rule, lt, "Das ist eine leichter handhabbare Situation.")
    assert_good(rule, lt, "Es gibt viele verschiedene Stock Screener.")
    assert_good(rule, lt, "Die Ware umräumen, um einer anderen genügend Platz zu schaffen.")

    # incorrect sentences:
    assert_bad(rule, lt, "Er hatte ein anstrengenden Tag",
        "ein anstrengender Tag", "ein anstrengendes Tag", "einen anstrengenden Tag", "einem anstrengenden Tag")
    assert_bad(rule, lt, "Es sind die riesigen Tisch.")
    # assertBad("Dort, die riesigen Tischs!");    // TODO: error not detected because of comma
    assert_bad(rule, lt, "Als die riesigen Tischs kamen.")
    assert_bad(rule, lt, "Als die riesigen Tisches kamen.")
    assert_bad(rule, lt, "Der riesigen Tisch und so.")
    assert_bad(rule, lt, "An der roter Ampel.")
    assert_bad(rule, lt, "An der rote Ampel.")
    assert_bad(rule, lt, "An der rotes Ampel.")
    assert_bad(rule, lt, "An der rotem Ampel.")
    assert_bad(rule, lt, "Er hatte ihn aus dem 1,4 Meter tiefem Wasser gezogen.", "dem 1,4 Meter tiefen Wasser")
    assert_bad(rule, lt, "Das ist ein sehr schönes Tisch.", "ein sehr schöner Tisch")
    assert_bad(rule, lt, "Er hatte eine sehr schweren Infektion.")
    assert_bad(rule, lt, "Ein fast 5 Meter hohem Haus.")
    assert_bad(rule, lt, "Ein fünf Meter hohem Haus.")
    assert_bad(rule, lt, "Es wurden Karavellen eingesetzt, da diese für die flachen Gewässern geeignet waren.")
    assert_bad(rule, lt, "Wir bedanken uns bei allem Teams.")
    assert_bad(rule, lt, "Dabei geht es um das altbekannte Frage der Dynamiken der Eigenbildung..")
    assert_bad(rule, lt, "Den neue Finanzierungsweg wollen sie daher Hand in Hand mit dem Leser gehen.")
    assert_bad(rule, lt, "Den neuen Finanzierungsweg wollen sie daher Hand in Hand mit dem Lesern gehen.")
    assert_bad(rule, lt, "Ich widerrufe den mit Ihnen geschlossene Vertrag.", "der mit Ihnen geschlossene Vertrag", "den mit Ihnen geschlossenen Vertrag")
    assert_good(rule, lt, "Ich widerrufe den mit Ihnen geschlossenen Vertrag.")
    assert_bad(rule, lt, "Er klagte auch gegen den ohne ihn verkündete Sachbeschluss.", "den ohne ihn verkündeten Sachbeschluss")
    assert_good(rule, lt, "Er klagte auch gegen den ohne ihn verkündeten Sachbeschluss.")
    assert_good(rule, lt, "Dieser relativ gesehen starke Mann.")
    assert_good(rule, lt, "Diese relativ gesehen starke Frau.")
    assert_good(rule, lt, "Dieses relativ gesehen starke Auto.")
    assert_good(rule, lt, "Es kann gut sein, dass bei sowas echte Probleme erkannt werden.")
    # assertBad("Leute, die eine gewissen Sicherheit brauchen.");
    # assertBad("An der rot Ampel.");


def test_det_adj_adj_noun_rule(rule, lt):
    """AgreementRuleTest.testDetAdjAdjNounRule"""
    # correct:
    assert_good(rule, lt, "Das verlangt reifliche Überlegung.")
    assert_good(rule, lt, "Das bedeutet private Versicherungssummen ab 100€.")
    assert_good(rule, lt, "Das erfordert einigen Mut.")
    assert_good(rule, lt, "Die abnehmend aufwendige Gestaltung der Portale...")
    assert_good(rule, lt, "Die strahlend roten Blumen.")
    assert_good(rule, lt, "Der weiter vorhandene Widerstand konnte sich nicht durchsetzen.")
    assert_good(rule, lt, "Das jetzige gemeinsame Ergebnis...")
    assert_good(rule, lt, "Das früher übliche Abdecken mit elementarem Schwefel...")
    assert_good(rule, lt, "Das einzig wirklich Schöne...")
    assert_good(rule, lt, "Andere weniger bekannte Vorschläge waren „Konsistenter Empirismus“ oder...")
    assert_good(rule, lt, "Werden mehrere solcher physikalischen Elemente zu einer Einheit zusammengesetzt...")
    assert_good(rule, lt, "Aufgrund ihrer weniger guten Bonitätslage.")
    assert_good(rule, lt, "Mit ihren teilweise eigenwilligen Außenformen...")
    assert_good(rule, lt, "Die deutsche Kommasetzung bedarf einiger technischer Ausarbeitung.")
    assert_good(rule, lt, "Die deutsche Kommasetzung bedarf einiger guter technischer Ausarbeitung.")
    # incorrect:
    assert_bad(rule, lt, "Das ist eine solides strategisches Fundament", "ein solides strategisches Fundament")
    assert_bad(rule, lt, "Das ist eine solide strategisches Fundament", "ein solides strategisches Fundament")
    assert_bad1(rule, lt, "Das ist eine solide strategische Fundament", "ein solides strategisches Fundament")
    assert_bad(rule, lt, "Das ist ein solide strategisches Fundament", "ein solides strategisches Fundament")
    assert_bad(rule, lt, "Das ist ein solides strategische Fundament", "ein solides strategisches Fundament")
    assert_bad(rule, lt, "Das ist ein solides strategisches Fundamente", "ein solides strategisches Fundament")
    assert_bad(rule, lt, "Das ist ein solides strategisches Fundaments", "ein solides strategisches Fundament")
    assert_bad(rule, lt, "Die deutsche Kommasetzung bedarf einiger technisches Ausarbeitung.")
    assert_bad(rule, lt, "Die deutsche Kommasetzung bedarf einiger guter technische Ausarbeitung.")


def test_kon_unt_art_def_sub(rule, lt):
    """AgreementRuleTest.testKonUntArtDefSub"""
    # correct:
    assert_good(rule, lt, "Wieso verstehst du nicht, dass das komplett verschiedene Dinge sind?")
    assert_good(rule, lt, "Ich frage mich sehr, ob die wirklich zusätzliche Gebühren abdrücken wollen")
    # incorrect:
    assert_bad(rule, lt, "Dies wurde durchgeführt um das moderne Charakter zu betonen.", "den modernen Charakter")
    assert_bad(rule, lt, "Nur bei Topfpflanzung ist eine regelmäßige Düngung wichtig, da die normalen Bodenbildungsprozessen nicht stattfinden.", "die normalen Bodenbildungsprozesse", "den normalen Bodenbildungsprozessen")
    assert_bad(rule, lt, "Die Höhe kommt oft darauf an, ob die richtigen Leuten gut mit einen können oder nicht.")


def test_bug_fixes(rule, lt):
    """AgreementRuleTest.testBugFixes"""
    assert_bad(rule, lt, "Denn die einzelnen sehen sich einer sehr verschieden starken Macht des...", "einer sehr verschiedenen starken Macht")    # TODO: not actually a bug
    assert_good(rule, lt, "Das passiert nur, wenn der zu Pflegende bereit ist.")
    assert_good(rule, lt, "Peter, iss nicht meine")    # used to cause ArrayIndexOutOfBoundsException
