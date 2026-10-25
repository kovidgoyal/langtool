"""Port of the Java tests org.languagetool.rules.de.CaseRuleTest,
DuUpperLowerCaseRuleTest and UppercaseSentenceStartRuleTest (the core
UppercaseSentenceStartRule with German)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.case_rule import CaseRule, compare_lists
from langtool.lang.de.du_rule import DuUpperLowerCaseRule
from langtool.messages import messages_for
from langtool.patterns.string_matcher import regexp
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


@pytest.fixture(scope='module')
def rule():
    return CaseRule(messages_for('de'), get_language('de-DE'))


class _Checker:
    """assertGood/assertBad of CaseRuleTest; the failures are collected
    and reported together at the end of a test"""

    def __init__(self, rule, lt):
        self.rule = rule
        self.lt = lt
        self.failures = []

    def good(self, s):
        matches = self.rule.match(self.lt.get_analyzed_sentence(s))
        if len(matches) != 0:
            self.failures.append("Did not expect error in: '%s': %r" % (s, matches))

    def bad(self, s):
        matches = self.rule.match(self.lt.get_analyzed_sentence(s))
        if len(matches) != 1:
            self.failures.append("Did not find expected error in: '%s': %r" % (s, matches))

    def check_count(self, s, n):
        matches = self.lt.check(s)
        if len(matches) != n:
            self.failures.append('Expected %d matches in: %r, got %r' % (n, s, matches))

    def done(self):
        assert not self.failures, '\n'.join(self.failures)


def test_rule_activation():
    """CaseRuleTest.testRuleActivation"""
    assert 'CaseRule' in [type(r).__name__ for r in get_language('de-DE').get_relevant_rules(messages_for('de'))]


def test_rule(rule, lt):
    """CaseRuleTest.testRule"""
    c = _Checker(rule, lt)
    good, bad, check_count = c.good, c.bad, c.check_count

    # correct sentences:
    good('(Dauer, Raum, Anwesende)')
    good('Es gibt wenige Befragte.')
    good('Es gibt weniger Befragte, die das machen würden.')
    good('Es gibt mehr Befragte, die das machen würden.')
    good('Das ist eine Abkehr von Gottes Geboten.')
    good('Dem Hund Futter geben')
    good('Heute spricht Frau Stieg.')
    good('So könnte es auch den Handwerksbetrieben gehen, die ausbilden und deren Ausbildung dann Industriebetrieben zugutekäme.')
    good('Die Firma Drosch hat nicht pünktlich geliefert.')
    good('3.1 Technische Dokumentation')
    good('Ein einfacher Satz zum Testen.')
    good('Das Laufen fällt mir leicht.')
    good('Das Winseln stört.')
    good('Das schlägt nicht so zu Buche.')
    good('Dirk Hetzel ist ein Name.')
    good('Aber sie tat es, sodass unsere Klasse das sehen und fotografieren konnte.')
    good('Sein Verhalten war okay.')
    good('Hier ein Satz. "Ein Zitat."')
    good("Hier ein Satz. 'Ein Zitat.'")
    good('Hier ein Satz. «Ein Zitat.»')
    good('Hier ein Satz. »Ein Zitat.«')
    good('Hier ein Satz. (Noch einer.)')
    good('Hier geht es nach Tel Aviv.')
    good('Unser Jüngster ist da.')
    good('Alles Erfundene ist wahr.')
    good('Sie hat immer ihr Bestes getan.')
    good('Er wird etwas Verrücktes träumen.')
    good('Er wird etwas schön Verrücktes träumen.')
    good('Er wird etwas ganz schön Verrücktes träumen.')
    good('Mit aufgewühltem Innerem.')
    good('Mit völlig aufgewühltem Innerem.')
    good('Er wird etwas so Verrücktes träumen.')
    good('Tom ist etwas über dreißig.')
    good('Diese Angriffe bleiben im Verborgenen.')
    good('Ihr sollt mich das wissen lassen.')
    good('Wenn er mich das rechtzeitig wissen lässt, gerne.')
    good('Und sein völlig aufgewühltes Inneres erzählte von den Geschehnissen.')
    good('Aber sein aufgewühltes Inneres erzählte von den Geschehnissen.')
    good('Sein aufgewühltes Inneres erzählte von den Geschehnissen.')
    good('Aber sein Inneres erzählte von den Geschehnissen.')
    good('Ein Kaninchen, das zaubern kann.')
    good('Keine Ahnung, wie ich das prüfen sollte.')
    good('Und dann noch Strafrechtsdogmatikerinnen.')
    good('Er kann ihr das bieten, was sie verdient.')
    good('Das fragen sich mittlerweile viele.')
    good('Ich habe gehofft, dass du das sagen würdest.')
    good('Eigentlich hätte ich das wissen müssen.')
    good('Mir tut es wirklich leid, Ihnen das sagen zu müssen.')
    good('Der Wettkampf endete im Unentschieden.')
    good('Er versuchte, Neues zu tun.')
    good('Du musst das wissen, damit du die Prüfung bestehst')
    good('Er kann ihr das bieten, was sie verdient.')
    good('Er fragte, ob das gelingen wird.')
    good('Er mag Obst, wie zum Beispel Apfelsinen.')
    good('Er will die Ausgaben für Umweltschutz und Soziales kürzen.')
    good('Die Musicalverfilmung „Die Schöne und das Biest“ bricht mehrere Rekorde.')
    good('Joachim Sauer lobte Johannes Rau.')
    good('Im Falle des Menschen ist dessen wirkendes Wollen gegeben.')
    good('Szenario: 1) Zwei Galaxien verschmelzen.')  # should be accepted by isNumbering
    good('Existieren Außerirdische im Universum?')
    good('Tom vollbringt Außerordentliches.')
    good('Er führt Böses im Schilde.')
    good('Es gab Überlebende.')
    good("'Wir werden das stoppen.'")
    good('Wahre Liebe muss das aushalten.')
    good('Du kannst das machen.')
    good('Vor dem Aus stehen.')
    good('Ich Armer!')
    good('Hallo Malte,')
    good('Parks Vertraute Choi Soon Sil ist zu drei Jahren Haft verurteilt worden.')
    good('Bei einer Veranstaltung Rechtsextremer passierte es.')
    good('Eine Gruppe Betrunkener singt.')
    good('Bei Betreten des Hauses.')
    good('Das Aus für Italien ist bitter.')
    good('Das Aus kam unerwartet.')
    good('Anmeldung bis Fr. 1.12.')
    good('Gibt es die Schuhe auch in Gr. 43?')
    good('Weil er Unmündige sexuell missbraucht haben soll, wurde ein Lehrer verhaftet.')
    good('Tausende Gläubige kamen.')
    good('Es kamen Tausende Gläubige.')
    good('Das schließen Forscher aus den gefundenen Spuren.')
    good('Wieder Verletzter bei Unfall')
    good('Eine Gruppe Aufständischer verwüstete die Bar.')
    good('‚Dieser Satz.‘ Hier kommt der nächste Satz.')
    good('Dabei werden im Wesentlichen zwei Prinzipien verwendet:')
    good('Er fragte, ob das gelingen oder scheitern wird.')
    good('Einen Tag nach Bekanntwerden des Skandals')
    good('Das machen eher die Erwachsenen.')
    good('Das ist ihr Zuhause.')
    good('Das ist Sandras Zuhause.')
    good('Das machen eher wohlhabende Leute.')
    good('Als Erstes würde ich sofort die Struktur ändern.')
    good('Er sagte: Als Erstes würde ich sofort die Struktur ändern.')
    good('Das schaffen moderne E-Autos locker.')
    good('Das schaffen moderne E-Autos schneller')
    good('Das schaffen moderne und effizientere E-Autos schneller.')
    good('Das verwalten User.')
    good('Man kann das generalisieren')
    good('Aber wie wir das machen und sicher gestalten, darauf konzentriert sich unsere Arbeit.')
    good('Vielleicht kann man das erweitern')
    good('Vielleicht soll er das generalisieren')
    good('Wahrscheinlich müssten sie das überarbeiten')
    good('Assistenzsysteme warnen rechtzeitig vor Gefahren.')
    good('Jeremy Schulte rannte um sein Leben.')
    good('Er arbeitet im Bereich Präsidiales.')
    good('Er spricht Sunnitisch & Schiitisch.')
    good('Er sagte, Geradliniges und Krummliniges sei unvergleichbar.')
    good('Dort erfahren sie Kurioses und Erstaunliches zum Zusammenspiel von Mensch und Natur.')
    good('Dabei unterscheidet die Shareware zwischen Privatem und Dienstlichem bei Fahrten ebenso wie bei Autos.')
    good('Besucher erwartet Handegefertigtes, Leckeres und Informatives rund um den Hund.')
    good('Der Unterschied zwischen Vorstellbarem und Machbarem war niemals geringer.')
    good('Das war Fiete Lang.')
    good('Wenn du an das glaubst, was du tust, kannst du Großes erreichen.')
    good('Dann hat er Großes erreicht.')
    good('Dann hat er Großes geleistet.')
    good('Das Thema Datenaustauschverfahren ist mir wichtig.')
    good('Ist das eine Frage ? Müsste das nicht anders sein?')
    good('Das ist ein Satz !!! Das auch.')
    good('Der russische Erdölmagnat Emanuel Nobel, der Erbauer des ersten Dieselmotorschiffes.')
    good('Zur Versöhnung: Jüdische Gläubige sollen beten.')
    good('Fast im Stundentakt wurden neue Infizierte gemeldet.')
    good('Bert Van Den Brink')
    good('“In den meisten Bundesländern werden solche Studien per se nicht durchgeführt.”')
    good('Aber “in den meisten Bundesländern werden solche Studien per se nicht durchgeführt.”')
    good('A) Das Haus')
    good('Rabi und Polykarp Kusch an der Columbia-Universität')
    good('Man geht davon aus, dass es sich dabei nicht um Reinigungsverhalten handelt.')
    good('Wenn dort oft Gefahren lauern.')
    good('3b) Den Bereich absichern')
    good('@booba Da der Holger keine Zeit hat ...')
    good('Es gibt infizierte Ärzt*innen.')
    good('WUrzeln')  # to be found by spell checker
    good('🙂 Übrigens finde ich dein neues Ordnungssystem richtig genial!')
    good('Ein 10,4 Ah Lithium-Akku')
    good('14:15 Uhr SpVgg Westheim')
    good('Unser Wärmestrom-Tarif WärmeKompakt im Detail')  # ignore so we don't suggest "wärmeKompakt" (#3779)
    good('Autohaus Dornig GmbH')
    good('Hans Pries GmbH')
    good('Der Kund*innenservice war auch sehr kulant und persönlich.')
    good(':D Auf dieses Frl.')
    good('@b_fischer Der Bonussemester-Antrag oder der Widerspruch?')
    good('Das Gedicht “Der Panther”.')  # quotes are not correct, but leave that to the quotes rule
    good('Klar, dass wir das brauchen.')
    good("Das wird Scholz' engster Vertrauter Wolfgang Schmidt übernehmen.")
    good('Bei der Fülle an Vorgaben kann das schnell vergessen werden.')
    good('Majid ergänzte: ”Vorläufigen Analysen der Terrakottaröhren aus Ardais liegen ...')

    good('Ist das eine Frage ? Müsste das nicht anders sein?')
    good('Das ist ein Satz !!! Das auch.')
    good('Liebe Kund:in')
    good('Wir sollten das mal labeln.')
    good('Teil 1: Der unaufhaltsame Aufstieg Bonapartes')
    good('Der Absatz bestimmt, in welchem Maße diese Daten Dritten zugänglich gemacht werden.')
    good('Der TN spricht Russisch - Muttersprache')

    good('Ich musste das Video mehrmals stoppen, um mir über das Gesagte Gedanken zu machen.')
    good('Während Besagtes Probleme verursachte.')
    good('Während der Befragte Geschichten erzählte.')
    good('Während ein Befragter Geschichten erzählte.')
    good('... für welche ein Befragter Geld ausgegeben hat.')
    good('Während die Befragte Geld verdiente.')
    good('Während die Besagte Geschichten erzählte.')
    good('Sind dem Zahlungspflichtigen Kosten entstanden?')
    good('Jetzt, wo Protestierende und Politiker sich streiten')
    good('Während die Besagte Geld verdiente.')
    good('Die Nacht, die Liebe, dazu der Wein — zu nichts Gutem Ratgeber sein.')
    good('Warum tun die Menschen Böses?')
    good('Und das Vergangene Revue passieren lassen')
    good('Seither ist das Französische Amtssprache in Frankreich.')
    good('Für die Betreute Kontoauszüge holen.')
    good('Das verstehen Deutsche halt nicht.')
    good('12:00 - 13:00 Gemeinsames Mittagessen')
    good('12:00 Gemeinsames Mittagessen')
    good('Meld dich, wenn du Großes vorhast.')
    good('Muss nicht der Einzelne Einschränkungen der Freiheit hinnehmen, wenn die Sicherheit der Menschen und des Staates mehr gefährdet sind?')
    good('Wie reißt ein Einzelner Millionen aus ihren Sitzen?')
    good('Der Aphorismus will nicht Dumme gescheit, sondern Gescheite nachdenklich machen.')
    good('Während des Hochwassers den Eingeschlossenen Wasser und Nahrung bringen')
    good('Aus dem Stein der Weisen macht ein Dummer Schotter.')
    good('Auf dem Weg zu ihnen begegnet der Halbwüchsige Revolverhelden und Indianern.')
    bad('Während des Hochwassers den Eingeschlossenen Menschen Nahrung bringen')
    bad('Während Gefragte Menschen antworteten.')
    # assertBad("Ich werde die Blaue Akte brauchen.");
    bad('Ich brauche eine Gratis App die Ohne WLAN.')
    bad('Alle Kommunikationsmedien die Meinem Widersacher dienen werden.')
    bad('Ich wünsche dir Alles Liebe.')
    bad('Das Auto Meines Vaters wird in Italien produziert.')
    bad('Nach Böhm-Bawerk steht die Allgemeine Profitrate und die Theorie der Produktionspreise im Widerspruch zum Wertgesetz des ersten Bandes.')
    bad('Ich sehe da keine Absolute Schranke.')
    bad('Manns und Fontanes Gesammelten Werken.')
    bad('Und das Neue Haus.')
    bad('Das sind die Die Lehrer.')
    bad('An der flachen Decke zeigt ein Großes Bildnis die Geburt Christi und die ewige Anbetung der Hirten.')
    bad('Und das Gesagte Wort.')
    bad('Und die Gesagten Wörter.')
    bad('Und meine Erzählte Geschichte.')
    bad('Und diese Erzählten Geschichten.')
    bad('Und eine Neue Zeit.')

    # https://github.com/languagetool-org/languagetool/issues/1515:
    good('▶︎ Dies ist ein Test')
    good('▶ Dies ist ein Test')
    good('* Dies ist ein Test')
    good('- Dies ist ein Test')
    good('• Dies ist ein Test')
    good(':-) Dies ist ein Test')
    good(';-) Dies ist ein Test')
    good(':) Dies ist ein Test')
    good(';) Dies ist ein Test')
    good('..., die ins Nichts griff.')
    good('Er fragte, was sie über das denken und zwinkerte ihnen zu.')
    good('dem Ägyptischen, Berberischen, Semitischen, Kuschitischen, Omotischen und dem Tschadischen')
    good('mit S-Bahn-ähnlichen Verkehrsmitteln')
    good('mit U-Bahn-ähnlichen und günstigen Verkehrsmitteln')
    good('mit Ü-Ei-großen, schweren Hagelkörnern')
    good('mit E-Musik-artigen, komplizierten Harmonien')
    good('eBay International AG')
    good('Harald & Schön')  # Firmenname
    good('Nicholas and Stark')  # Eigenname
    good('Die Schweizerische Bewachungsgesellschaft')  # Eigenname

    # assertBad("Sie sind nicht Verständlich");
    bad('Das machen der Töne ist schwierig.')
    bad('Sie Vertraute niemandem.')
    bad('Beten Lernt man in Nöten.')
    bad('Ich habe Heute keine Zeit.')
    bad('Er sagte, Geradliniges und krummliniges sei unvergleichbar.')
    bad('Er sagte, ein Geradliniges und Krummliniges Konzept ist nicht tragbar.')
    bad('Ä Was?')
    bad('… die preiswerte Variante unserer Topseller im Bereich Alternativ Mehle.')
    bad('…  jahrzehntelangen Mitstreitern und vielen Freunden aus Nah und Fern.')
    bad('Hi und Herzlich willkommen auf meiner Seite.')
    # assertBad("Ich gehe gerne Joggen.");
    bad('Er ist Groß.')
    bad('Die Zahl ging auf Über 1.000 zurück.')
    bad('Er sammelt Große und kleine Tassen.')
    bad('Er sammelt Große, mittlere und kleine Tassen.')
    bad('Dann will sie mit London Über das Referendum verhandeln.')
    bad('Sie kann sich täglich Über vieles freuen.')
    bad('Der Vater (51) Fuhr nach Rom.')
    bad('Er müsse Überlegen, wie er das Problem löst.')
    bad('Er sagte, dass er Über einen Stein stolperte.')
    bad('Tom ist etwas über Dreißig.')
    bad('Unser warten wird sich lohnen.')
    bad('Tom kann mit fast Allem umgehen.')
    bad('Dabei Übersah er sie.')
    bad('Der Brief wird am Mittwoch in Brüssel Übergeben.')
    bad('Damit sollen sie die Versorgung in der Region Übernehmen.')
    bad('Die Unfallursache scheint geklärt, ein Lichtsignal wurde Überfahren.')
    bad('Der Lenker hatte die Höchstgeschwindigkeit um 76 km/h Überschritten.')
    bad('Das sind 10 Millionen Euro, Gleichzeitig und zusätzlich.')
    # assertBad("Das Extreme Sportfest");
    # assertBad("Das Extreme Sportfest findet morgen statt.");
    good('Stets suchte er das Extreme.')
    good('Ich möchte zwei Kilo Zwiebeln.')
    # "NIL" reading in Morphy that used to confuse CaseRule:
    good('Ein Menschenfreund.')
    # works only thanks to addex.txt:
    good('Der Nachfahre.')
    # both can be correct:
    good('Hier ein Satz, "Ein Zitat."')
    good('Hier ein Satz, "ein Zitat."')
    # Exception 'Le':
    good('Schon Le Monde schrieb das.')
    # unknown word:
    good('In Blubberdorf macht man das so.')
    # Exception defined in case_rule_exceptions.txt:
    good('Der Thriller spielt zur Zeit des Zweiten Weltkriegs')

    good('Anders als physikalische Konstanten werden mathematische Konstanten unabhängig von jedem physikalischen Maß definiert.')
    good('Eine besonders einfache Klasse bilden die polylogarithmischen Konstanten.')
    good('Das südlich von Berlin gelegene Dörfchen.')
    good('Weil er das kommen sah, traf er Vorkehrungen.')

    good('Sie werden im Allgemeinen gefasst.')
    good('Sie werden im allgemeinen Fall gefasst.')
    # assertBad("Sie werden im allgemeinen gefasst.");
    bad('Sie werden im Allgemeinen Fall gefasst.')

    # sentences that used to trigger an error because of incorrect compound tokenization:
    good('Das sind Euroscheine.')
    good('John Stallman isst.')
    good('Das ist die neue Gesellschafterin hier.')
    good('Das ist die neue Dienerin hier.')
    good('Das ist die neue Geigerin hier.')
    good('Die ersten Gespanne erreichen Köln.')
    good('Er beschrieb den Angeklagten wie einen Schuldigen')
    good('Er beschrieb den Angeklagten wie einen Schuldigen.')
    good('Es dauerte bis ins neunzehnte Jahrhundert')

    good('Das ist das Dümmste, was ich je gesagt habe.')
    bad('Das ist das Dümmste Kind.')

    good('Wacht auf, Verdammte dieser Welt!')
    good('Er sagt, dass Geistliche davon betroffen sind.')
    bad('Er sagt, dass Geistliche Würdenträger davon betroffen sind.')
    bad('Er sagt, dass Geistliche und weltliche Würdenträger davon betroffen sind.')
    bad('Er ist begeistert Von der Fülle.')
    bad('Er wohnt Über einer Garage.')
    # assertBad("„Weißer Rauch“ Über Athen");   // could be title/quote, so not detected
    bad('Die Anderen 90 Prozent waren krank.')

    good('Man sagt, Liebe mache blind.')
    good('Die Deutschen sind sehr listig.')
    good('Der Lesestoff bestimmt die Leseweise.')
    good('Ich habe nicht viel von einem Reisenden.')
    good('Die Vereinigten Staaten')
    good('Der Satz vom ausgeschlossenen Dritten.')
    # TODO:
    good('Die Ausgewählten werden gut betreut.')
    good('Die ausgewählten Leute werden gut betreut.')
    # assertBad("Die ausgewählten werden gut betreut.");
    bad('Die Ausgewählten Leute werden gut betreut.')

    bad('Er war dort Im März 2000.')
    bad('Er war dort Im Jahr 96.')

    # used to trigger error because of wrong POS tagging:
    good('Die Schlinge zieht sich zu.')
    good('Die Schlingen ziehen sich zu.')

    # used to trigger error because of "abbreviation"
    good('Sie fällt auf durch ihre hilfsbereite Art. Zudem zeigt sie soziale Kompetenz.')

    good('Die Lieferadresse ist Obere Brandstr. 4-7')
    good('Das ist es: kein Satz.')
    good('Werner Dahlheim: Die Antike.')
    good('1993: Der talentierte Mr. Ripley')
    good('Ian Kershaw: Der Hitler-Mythos: Führerkult und Volksmeinung.')
    bad('Das ist es: Kein Satz.')
    bad('Wen magst du lieber: Die Giants oder die Dragons?')

    good('Ich frage mich: Warum?')
    good('Ich frage mich: Wieso?')
    good('Ich frage mich: Weshalb?')
    good('Ich frage mich: Und warum?')
    good('Ich frage mich: Oder wieso?')
    good('Ich frage mich: Aber warum?')
    bad('Ich frage mich: Warum Das so ist.')

    good('Das wirklich Wichtige ist dies:')
    good('Das wirklich wichtige Verfahren ist dies:')
    # assertBad("Das wirklich wichtige ist dies:");
    bad('Das wirklich Wichtige Verfahren ist dies:')

    # incorrect sentences:
    bad('Die Schöne Tür')
    bad('Das Blaue Auto.')
    # assertBad("Der Grüne Baum.");
    bad('Ein Einfacher Satz zum Testen.')
    bad('Eine Einfache Frage zum Testen?')
    bad('Er kam Früher als sonst.')
    bad('Er rennt Schneller als ich.')
    bad('Das Winseln Stört.')
    bad('Sein verhalten war okay.')
    check_count('Karten werden vom Auswahlstapel gezogen. Auch […] Der Auswahlstapel gehört zum Inhalt.', 1)
    # assertEquals(2, lt.check("Karten werden vom Auswahlstapel gezogen. Auch [...] Der Auswahlstapel gehört zum Inhalt.").size());

    check_count('Karten werden vom Auswahlstapel gezogen. […] Der Auswahlstapel gehört zum Inhalt.', 0)
    # assertEquals(1, lt.check("Karten werden vom Auswahlstapel gezogen. [...] Der Auswahlstapel gehört zum Inhalt.").size());
    # TODO: error not found:
    # assertBad("So schwer, dass selbst Er ihn nicht hochheben kann.");

    good('Im Norwegischen klingt das schöner.')
    good('Übersetzt aus dem Norwegischen von Ingenieur Frederik Dingsbums.')
    good('Dem norwegischen Ingenieur gelingt das gut.')
    bad('Dem Norwegischen Ingenieur gelingt das gut.')
    good('Peter Peterson, dessen Namen auf Griechisch Stein bedeutet.')
    good('Peter Peterson, dessen Namen auf Griechisch gut klingt.')
    good('Das dabei Erlernte und Erlebte ist sehr nützlich.')
    bad('Das dabei erlernte und Erlebte Wissen ist sehr nützlich.')
    good('Ein Kapitän verlässt als Letzter das sinkende Schiff.')
    bad('Diese Regelung wurde als Überholt bezeichnet.')
    bad('Die Dolmetscherin und Der Vorleser gehen spazieren.')
    good('Es hilft, die Harmonie zwischen Führer und Geführten zu stützen.')
    good('Das Gebäude des Auswärtigen Amts.')
    good('Das Gebäude des Auswärtigen Amtes.')
    good('   Im Folgenden beschreibe ich das Haus.')  # triggers WHITESPACE_RULE, but should not trigger CASE_RULE (see github #258)
    good('"Im Folgenden beschreibe ich das Haus."')  # triggers TYPOGRAFISCHE_ANFUEHRUNGSZEICHEN, but should not trigger CASE_RULE
    good('Gestern habe ich 10 Spieße gegessen.')
    good('Die Verurteilten wurden mit dem Fallbeil enthauptet.')
    good('Den Begnadigten kam ihre Reue zugute.')
    good('Die Zahl Vier ist gerade.')
    good('Ich glaube, dass das geschehen wird.')
    good('Ich glaube, dass das geschehen könnte.')
    good('Ich glaube, dass mir das gefallen wird.')
    good('Ich glaube, dass mir das gefallen könnte.')
    good('Alldem wohnte etwas faszinierend Rätselhaftes inne.')
    good('Schau mich an, Kleine!')
    good('Schau mich an, Süßer!')
    good('Weißt du, in welchem Jahr das geschehen ist?')
    good('Das wissen viele nicht.')
    bad('Das sagen haben hier viele.')
    good('Die zum Tode Verurteilten wurden in den Hof geführt.')
    good('Wenn Sie das schaffen, retten Sie mein Leben!')
    good('Etwas Grünes, Schleimiges klebte an dem Stein.')
    good('Er befürchtet Schlimmeres.')
    bad('Bis Bald!')
    good('#4 Aktuelle Situation')
    good('Er trinkt ein kühles Blondes.')
    good('* [ ] Ein GitHub Markdown Listenpunkt')
    good('Tom ist ein engagierter, gutaussehender Vierzigjähriger, der...')
    good('a.) Im Zusammenhang mit ...')
    good('✔︎ Weckt Aufmerksamkeit.')
    good('Hallo Eckhart,')
    good('Er kann Polnisch und Urdu.')
    good('---> Der USB 3.0 Stecker')
    good('Black Lives Matter')
    good('== Schrittweise Erklärung')
    good('Audi A5 Sportback 2.0 TDI')
    good('§ 1 Allgemeine Bedingungen')
    good('§1 Allgemeine Bedingungen')
    good('[H3] Was ist Daytrading?')
    good(' Das ist das Aus des Airbus A380.')
    good('Wir sollten ihr irgendwas Erotisches schenken.')
    good('Er trank ein paar Halbe.')
    good('Sie/Er hat Schuld.')
    good('Das war irgendein Irrer.')
    good('Wir wagen Neues.')
    good('Grundsätzlich gilt aber: Essen Sie, was die Einheimischen Essen.')
    good('Vielleicht reden wir später mit ein paar Einheimischen.')
    bad('Das existiert im Jazz zunehmend nicht mehr Bei der weiteren Entwicklung des Jazz zeigt sich das.')
    good('Das denken zwar viele, ist aber total falsch.')
    good('Ich habe nix Besseres gefunden.')
    good('Ich habe nichts Besseres gefunden.')
    good('Ich habe noch Dringendes mitzuteilen.')

    # uppercased adjective compounds
    good('Er isst UV-bestrahltes Obst.')
    good('Er isst Na-haltiges Obst.')
    good('Er vertraut auf CO2-arme Wasserkraft')
    good('Das Entweder-oder ist kein Problem.')
    good('Er liebt ihre Makeup-freie Haut.')
    good('Das ist eine Schreibweise.')
    bad('Das ist Eine Schreibweise.')
    good('Das ist ein Mann.')
    bad('Das ist Ein Mann.')

    bad('Sie erhalten bald unsere Neuesten Insights.')
    bad('Auf eine Carvingschiene sollte die Kette schon im Kalten Zustand weit durchhängen.')

    good('Du Ärmste!')
    good('Ich habe nur Schlechtes über den Laden gehört.')
    good('Du Ärmster, leg dich besser ins Bett.')
    good('Er wohnt Am Hohen Hain 6a')
    good('Das Bauvorhaben Am Wiesenhang 9')
    good('... und das Zwischenmenschliche Hand in Hand.')
    good('Der Platz auf dem die Ahnungslosen Kopf an Kopf stehen.')
    good('4.)   Bei Beschäftigung von Hilfskräften: Schadenfälle durch Hilfskräfte')
    good('Es besteht aus Schülern, Arbeitstätigen und Studenten.')
    good('Sie starrt ständig ins Nichts.')
    good('Sowas aber auch.\u2063Das Haus ist schön.')
    good('\u2063Das Haus ist schön.')
    good('\u2063\u2063Das Haus ist schön.')
    good('Die Mannschaft ist eine gelungene Mischung aus alten Haudegen und jungen Wilden.')
    good('Alleine durch die bloße Einwohnerzahl des Landes leben im Land zahlreiche Kulturschaffende, nach einer Schätzung etwa 30.000 Künstler.')
    good('Ich hatte das offenbar vergessen oder nicht ganz verstanden.')
    good('Ich hatte das vergessen oder nicht ganz verstanden.')
    good('Das ist ein zwingendes Muss.')
    good('Er hält eine Handbreit Abstand.')
    good('Das ist das Debakel und Aus für Podolski.')
    good('Ein Highlight für Klein und Groß!')
    good("Der schwedische Psychologe Dan Katz, Autor von 'Angst kocht auch nur mit Wasser', sieht in der Corona-Krise dennoch nicht nur Negatives.")
    c.done()


def test_substantivierte_verben(rule, lt):
    """CaseRuleTest.testSubstantivierteVerben"""
    c = _Checker(rule, lt)
    good, bad = c.good, c.bad
    # correct sentences:
    good('Das fahrende Auto.')
    good('Das können wir so machen.')
    good('Denn das Fahren ist einfach.')
    good('Das Fahren ist einfach.')
    good('Das Gehen fällt mir leicht.')
    good('Das Ernten der Kartoffeln ist mühsam.')
    good('Entschuldige das späte Weiterleiten.')
    good('Ich liebe das Lesen.')
    good('Das Betreten des Rasens ist verboten.')
    good('Das haben wir aus eigenem Antrieb getan.')
    good('Das haben wir.')
    good('Das haben wir schon.')
    good('Das lesen sie doch sicher in einer Minute durch.')
    good('Das lesen Sie doch sicher in einer Minute durch!')
    good('Formationswasser, das oxidiert war.')
    good('Um das herauszubekommen diskutieren zwei Experten.')
    good('Ich würde ihn dann mal nach München schicken, damit die beiden das planen/entwickeln können.')

    # Source of the following examples: https://dict.leo.org/grammatik/deutsch/Rechtschreibung/Amtlich/GrossKlein/pgf57-58.html
    good('Das Lesen fällt mir schwer.')
    good('Sie hörten ein starkes Klopfen.')
    good('Wer erledigt das Fensterputzen?')
    good('Viele waren am Zustandekommen des Vertrages beteiligt.')
    good('Die Sache kam ins Stocken.')
    good('Das ist zum Lachen.')
    good('Euer Fernbleiben fiel uns auf.')
    good('Uns half nur noch lautes Rufen.')
    good('Die Mitbewohner begnügten sich mit Wegsehen und Schweigen.')
    good('Sie wollte auf Biegen und Brechen gewinnen.')
    good('Er klopfte mit Zittern und Zagen an.')
    good('Ich nehme die Tabletten auf Anraten meiner Ärztin.')
    good('Sie hat ihr Soll erfüllt.')
    good('Dies ist ein absolutes Muss.')
    good('Das Lesen fällt mir schwer.')

    # incorrect sentences:
    bad('Das fahren ist einfach.')
    bad('Denn das fahren ist einfach.')
    bad('Denn das laufen ist einfach.')
    bad('Denn das essen ist einfach.')
    bad('Denn das gehen ist einfach.')
    bad('Das Große Auto wurde gewaschen.')
    bad('Ich habe ein Neues Fahrrad.')
    # TODO: detect all the cases not preceded with 'das'
    c.done()


def test_phrase_exceptions(rule, lt):
    """CaseRuleTest.testPhraseExceptions"""
    c = _Checker(rule, lt)
    good = c.good
    # correct sentences:
    good('Das gilt ohne Wenn und Aber.')
    good('Ohne Wenn und Aber')
    good('Das gilt ohne Wenn und Aber bla blubb.')
    # as long as phrase exception isn't complete, there's no error:
    good('Das gilt ohne wenn')
    good('Das gilt ohne wenn und')
    good('wenn und aber')
    good('und aber')
    good('aber')
    # incorrect sentences:
    # error not found here as it's in the XML rules:
    # assertBad("Das gilt ohne wenn und aber.");
    c.done()


def test_compare_lists(lt):
    """CaseRuleTest.testCompareLists"""
    sentence1 = lt.get_analyzed_sentence('Hier ein Test')
    tokens1 = sentence1.non_blank_tokens
    assert compare_lists(tokens1, 0, 2, regexp(''), regexp('Hier'), regexp('ein'))
    assert compare_lists(tokens1, 1, 2, regexp('Hier'), regexp('ein'))
    assert compare_lists(tokens1, 0, 3, regexp(''), regexp('Hier'), regexp('ein'), regexp('Test'))
    assert not compare_lists(tokens1, 0, 4, regexp(''), regexp('Hier'), regexp('ein'), regexp('Test'))

    sentence2 = lt.get_analyzed_sentence('das Heilige Römische Reich')
    tokens2 = sentence2.non_blank_tokens
    assert compare_lists(tokens2, 0, 4, regexp(''), regexp('das'), regexp('Heilige'), regexp('Römische'),
                         regexp('Reich'))
    assert not compare_lists(tokens2, 8, 11, regexp(''), regexp('das'), regexp('Heilige'), regexp('Römische'),
                             regexp('Reich'))


# --- DuUpperLowerCaseRuleTest ------------------------------------------------

@pytest.mark.parametrize('text, expected', [
    ('Du bist noch jung.', 0),
    ('Du bist noch jung, du bist noch fit.', 0),
    ('Aber du bist noch jung, du bist noch fit.', 0),
    ('Aber du bist noch jung, dir ist das egal.', 0),
    ('Hast Du ihre Brieftasche gesehen?', 0),

    ('Aber Du bist noch jung, du bist noch fit.', 1),
    ('Aber Du bist noch jung, dir ist das egal.', 1),
    ('Aber Du bist noch jung. Und dir ist das egal.', 1),

    ('Aber du bist noch jung. Und Du bist noch fit.', 1),
    ('Aber du bist noch jung, Dir ist das egal.', 1),
    ('Aber du bist noch jung. Und Dir ist das egal.', 1),

    ('Aber du bist noch jung, sagt euer Vater oft.', 0),
    ('Aber Du bist noch jung, sagt Euer Vater oft.', 0),
    ('Aber Du bist noch jung, sagt euer Vater oft.', 1),
    ('Aber du bist noch jung, sagt Euer Vater oft.', 1),

    ('Könnt Ihr Euch das vorstellen???', 0),
    ('Könnt ihr euch das vorstellen???', 0),
    ('Aber Samstags geht ihr Sohn zum Sport. Stellt Euch das mal vor!', 0),
    # ('Könnt Ihr euch das vorstellen???', 1),
    ('Wie geht es euch? Herr Meier, wie war ihr Urlaub?', 0),
    ('Wie geht es Euch? Herr Meier, wie war Ihr Urlaub?', 0),
    # ('Wie geht es euch? Herr Meier, wie war Ihr Urlaub?', 1),
    # ('Wie geht es Euch? Herr Meier, wie war ihr Urlaub?', 1),

    ('"Du sagtest, du würdest es schaffen!"', 0),
    ('Egal, was du tust: Du musst dein Bestes geben.', 0),
    ('Was auch immer du tust: ICH UND DU KÖNNEN ES SCHAFFEN.', 0),
    ('Hast Du die Adresse von ihr?', 0),
])
def test_du_upper_lower_case_rule(lt, text, expected):
    """DuUpperLowerCaseRuleTest.testRule"""
    rule = DuUpperLowerCaseRule(messages_for('en'))
    sentence = lt.get_analyzed_sentence(text)
    matches = rule.match([sentence])
    assert len(matches) == expected, 'Expected %d, got %d: %s -> %r' % (expected, len(matches), sentence.text,
                                                                         matches)


# --- UppercaseSentenceStartRuleTest -----------------------------------------

def test_uppercase_sentence_start_rule():
    """UppercaseSentenceStartRuleTest.testRule"""
    lt = JLanguageTool(get_language('de-DE'))
    # TestTools.disableAllRulesExcept(lt, "UPPERCASE_SENTENCE_START")
    for r in lt.get_all_rules():
        if r.get_id() != 'UPPERCASE_SENTENCE_START':
            lt.disable_rule(r.get_id())

    assert len(lt.check('etwas beginnen. und der auch nicht')) == 2

    assert len(lt.check('schön')) == 0  # not a real sentence
    assert len(lt.check('Satz')) == 0
    assert len(lt.check('Dies ist ein Satz. Und hier kommt noch einer')) == 0
    assert len(lt.check('Dies ist ein Satz. Ätsch, noch einer mit Umlaut.')) == 0
    assert len(lt.check('Dieser Satz ist bspw. okay so.')) == 0
    assert len(lt.check('Dieser Satz ist z.B. okay so.')) == 0
    assert len(lt.check('Dies ist ein Satz. "Aber der hier auch!".')) == 0
    assert len(lt.check('"Dies ist ein Satz!"')) == 0
    assert len(lt.check("'Dies ist ein Satz!'")) == 0
    assert len(lt.check('mRNA-Impfstoffe sind wichtig.')) == 0

    assert len(lt.check('Sehr geehrte Frau Merkel,\nwie wir Ihnen schon früher mitgeteilt haben...')) == 0
    # assert len(lt.check('Dies ist ein Satz. aber das hier noch nicht')) == 0

    assert len(lt.check('schön!')) == 1
    assert len(lt.check('Dies ist ein Satz. ätsch, noch einer mit Umlaut.')) == 1
    assert len(lt.check('Dies ist ein Satz. "aber der hier auch!"')) == 1
    assert len(lt.check('Dies ist ein Satz. „aber der hier auch!“')) == 1
    assert len(lt.check('"dies ist ein Satz!"')) == 1
    assert len(lt.check("'dies ist ein Satz!'")) == 1

    # Test soft hyphen removal / position fixing:
    matches0 = lt.check('Ein Test. was?')  # no soft hyphen yet
    assert len(matches0) == 1
    assert matches0[0].from_pos == 10
    assert matches0[0].to_pos == 13

    matches1 = lt.check('Ein \u00adTest. was?')
    assert len(matches1) == 1
    assert matches1[0].from_pos == 11
    assert matches1[0].to_pos == 14

    matches2 = lt.check('Ein \u00adTe\u00adst. was?')
    assert len(matches2) == 1
    assert matches2[0].from_pos == 12
    assert matches2[0].to_pos == 15

    matches3 = lt.check('Ein \u00adTe\u00adst. Te\u00adst. was?')
    assert len(matches3) == 1
    assert matches3[0].from_pos == 19
    assert matches3[0].to_pos == 22

    assert len(lt.check('Willkommen… im Berlin.')) == 0
    assert len(lt.check('Die neue Kollektion von NAU! ist jetzt online.')) == 0
