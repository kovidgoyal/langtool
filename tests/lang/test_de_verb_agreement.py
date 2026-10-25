"""Port of the Java tests org.languagetool.rules.de.VerbAgreementRuleTest,
SubjectVerbAgreementRuleTest and MissingVerbRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.de.missing_verb import MissingVerbRule
from langtool.lang.de.subject_verb_agreement import SubjectVerbAgreementRule
from langtool.lang.de.verb_agreement import VerbAgreementRule
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


class TestVerbAgreementRule:
    """Port of VerbAgreementRuleTest."""

    @pytest.fixture(autouse=True)
    def set_up(self, lt):
        self.lt = lt
        self.rule = VerbAgreementRule(messages_for('de'), get_language('de-DE'))

    def match(self, text):
        return self.rule.match(self.lt.analyze_text(text))

    def assert_good(self, s):
        matches = self.match(s)
        assert len(matches) == 0, "Got > 0 matches for '%s': %r" % (s, matches)

    def assert_bad(self, s, *args):
        """The overloads assertBad(s), assertBad(s, n), assertBad(s,
        expectedErrorSubstring), assertBad(s, n, expectedSuggestions...) and
        assertBad(s, expectedSuggestions...)"""
        if args and isinstance(args[0], int):
            n, suggestions = args[0], args[1:]
        elif len(args) == 1:
            matches = self.match(s)
            assert len(matches) == 1, s
            assert args[0] in matches[0].message, \
                "Got error '%s', expected substring '%s'" % (matches[0].message, args[0])
            return
        else:
            n, suggestions = 1, args
        matches = self.match(s)
        assert len(matches) == n, "Did not find %d match(es) in sentence '%s'" % (n, s)
        if suggestions:
            match = matches[0]
            # When two errors are reported by the rule (so TODO above), it might happen that the first match does
            # not have the suggestions, but the second one
            if len(matches) > 1 and not match.suggested_replacements:
                match = matches[1]
            assert match.suggested_replacements == list(suggestions)

    def test_suggestion_sorting(self):
        """testSuggestionSorting"""
        match1 = self.match("Wir nenne ihn mal „wild“.")
        assert len(match1) == 1
        assert str(match1[0].suggested_replacements).replace("'", "") == \
            "[Wir nennen, Wir nennten, Er nenne, Sie nenne, Wir nannten, Ich nenne, Es nenne]"

    def test_positions(self):
        """testPositions"""
        match1 = self.match("Du erreichst ich unter 12345")
        assert len(match1) == 1
        assert match1[0].from_pos == 3
        assert match1[0].to_pos == 16
        match2 = self.match("Hallo Karl. Du erreichst ich unter 12345")
        assert len(match2) == 1
        assert match2[0].from_pos == 12 + 3
        assert match2[0].to_pos == 12 + 16
        match3 = self.match("Ihr könnt das Training abbrechen, weil es nichts bringen wird. Er geht los und sagt dabei: "
                            "Werde ich machen.")
        assert len(match3) == 1
        assert match3[0].from_pos == 97
        assert match3[0].to_pos == 107

        # Was a FP, now fixed
        match4 = self.match("Mir ist bewusst, dass viele Menschen wie du empfinden.")
        assert len(match4) == 0

    def test_wrong_verb(self):
        """testWrongVerb"""
        # correct sentences:
        self.assert_good("*runterguck* das ist aber tief")  # chat style / Inflektiv
        self.assert_good("Weder Peter noch ich wollen das.")
        self.assert_good("Du bist in dem Moment angekommen, als ich gegangen bin.")
        self.assert_good("Kümmere du dich mal nicht darum!")
        self.assert_good("Ich weiß, was ich tun werde, falls etwas geschehen sollte.")
        self.assert_good("...die dreißig Jahre jünger als ich ist.")
        self.assert_good("Ein Mann wie ich braucht einen Hut.")
        self.assert_good("Egal, was er sagen wird, ich habe meine Entscheidung getroffen.")
        self.assert_good("Du Beharrst darauf, dein Wörterbuch hätte recht, hast aber von den Feinheiten des Japanischen keine Ahnung!")
        self.assert_good("Bin gleich wieder da.")
        self.assert_good("Wobei ich äußerst vorsichtig bin.")
        self.assert_good("Es ist klar, dass ich äußerst vorsichtig mit den Informationen umgehe")
        self.assert_good("Es ist klar, dass ich äußerst vorsichtig bin.")
        self.assert_good("Wobei er äußerst selten darüber spricht.")
        self.assert_good("Wobei er äußerst selten über seine erste Frau spricht.")
        self.assert_good("Das Wort „schreibst“ ist schön.")
        self.assert_good("Die Jagd nach bin Laden.")
        self.assert_good("Die Unterlagen solltet ihr gründlich durcharbeiten.")
        self.assert_good("Er reagierte äußerst negativ.")
        self.assert_good("Max und ich sollten das machen.")
        self.assert_good("Osama bin Laden stammt aus Saudi-Arabien.")
        self.assert_good("Solltet ihr das machen?")
        self.assert_good("Dann beende du den Auftrag und bring sie ihrem Vater.")
        self.assert_good("- Wirst du ausflippen?")
        self.assert_good("Ein Geschenk, das er einst von Aphrodite erhalten hatte.")
        self.assert_good("Wenn ich sterben sollte, wer würde sich dann um die Katze kümmern?")
        self.assert_good("Wenn er sterben sollte, wer würde sich dann um die Katze kümmern?")
        self.assert_good("Wenn sie sterben sollte, wer würde sich dann um die Katze kümmern?")
        self.assert_good("Wenn es sterben sollte, wer würde sich dann um die Katze kümmern?")
        self.assert_good("Wenn ihr sterben solltet, wer würde sich dann um die Katze kümmern?")
        self.assert_good("Wenn wir sterben sollten, wer würde sich dann um die Katze kümmern?")
        self.assert_good("Dafür erhielten er sowie der Hofgoldschmied Theodor Heiden einen Preis.")
        self.assert_good("Probst wurde deshalb in den Medien gefeiert.")
        self.assert_good("/usr/bin/firefox")
        self.assert_good("Das sind Leute, die viel mehr als ich wissen.")
        self.assert_good("Das ist mir nicht klar, kannst ja mal beim Kunden nachfragen.")
        self.assert_good("So tes\u00ADtest Du das mit dem soft hyphen.")
        self.assert_good("Viele Brunnen in Italiens Hauptstadt sind bereits abgeschaltet.")
        self.assert_good("„Werde ich tun!“")
        self.assert_good("Könntest dir mal eine Scheibe davon abschneiden!")
        self.assert_good("Müsstest dir das mal genauer anschauen.")
        self.assert_good("Kannst ein neues Release machen.")
        self.assert_good("Sie fragte: „Muss ich aussagen?“")
        self.assert_good("„Können wir bitte das Thema wechseln, denn ich möchte ungern darüber reden?“")
        self.assert_good("Er sagt: „Willst du behaupten, dass mein Sohn euch liebt?“")
        self.assert_good("Kannst mich gerne anrufen.")
        self.assert_good("Kannst ihn gerne anrufen.")
        self.assert_good("Kannst sie gerne anrufen.")
        self.assert_good("Aber wie ich sehe, benötigt ihr Nachschub.")
        self.assert_good("Wie ich sehe, benötigt ihr Nachschub.")
        self.assert_good("Einer wie du kennt doch bestimmt viele Studenten.")
        self.assert_good("Für Sie mache ich eine Ausnahme.")
        self.assert_good("Ohne sie hätte ich das nicht geschafft.")
        self.assert_good("Ohne Sie hätte ich das nicht geschafft.")
        self.assert_good("Ich hoffe du auch.")
        self.assert_good("Ich hoffe ihr auch.")
        self.assert_good("Wird hoffen du auch.")
        self.assert_good("Hab einen schönen Tag!")
        self.assert_good("Tom traue ich mehr als Maria.")
        self.assert_good("Tom kenne ich nicht besonders gut, dafür aber seine Frau.")
        self.assert_good("Tom habe ich heute noch nicht gesehen.")
        self.assert_good("Tom bezahle ich gut.")
        self.assert_good("Tom werde ich nicht noch mal um Hilfe bitten.")
        self.assert_good("Tom konnte ich überzeugen, nicht aber Maria.")
        self.assert_good("Mach du mal!")
        self.assert_good("Das bekomme ich nicht hin.")
        self.assert_good("Dies betreffe insbesondere Nietzsches Aussagen zu Kant und der Evolutionslehre.")
        self.assert_good("❌Du fühlst Dich unsicher?")
        self.assert_good("Bringst nicht einmal so etwas Einfaches zustande!")
        self.assert_good("Bekommst sogar eine Sicherheitszulage")
        self.assert_good("Dallun sagte nur, dass er gleich kommen wird und legte wieder auf.")
        self.assert_good("Tinne, Elvis und auch ich werden gerne wiederkommen!")
        self.assert_good("Du bist Lehrer und weißt diese Dinge nicht?")
        self.assert_good("Die Frage lautet: Bist du bereit zu helfen?")
        self.assert_good("Ich will nicht so wie er enden.")
        self.assert_good("Das heißt, wir geben einander oft nach als gute Freunde, ob wir gleich nicht einer Meinung sind.")
        self.assert_good("Wir seh'n uns in Berlin.")
        self.assert_good("Bist du bereit, darüber zu sprechen?")
        self.assert_good("Bist du schnell eingeschlafen?")
        self.assert_good("Im Gegenzug bin ich bereit, beim Türkischlernen zu helfen.")
        self.assert_good("Das habe ich lange gesucht.")
        self.assert_good("Dann solltest du schnell eine Nummer der sexy Omas wählen.")
        self.assert_good("Vielleicht würdest du bereit sein, ehrenamtlich zu helfen.")
        self.assert_good("Werde nicht alt, egal wie lange du lebst.")
        self.assert_good("Du bist hingefallen und hast dir das Bein gebrochen.")
        self.assert_good("Mögest du lange leben!")
        self.assert_good("Planst du lange hier zu bleiben?")
        self.assert_good("Du bist zwischen 11 und 12 Jahren alt und spielst gern Fußball bzw. möchtest damit anfangen?")
        self.assert_good("Ein großer Hadithwissenschaftler, Scheich Şemseddin Mehmed bin Muhammed-ül Cezri, kam in der Zeit von Mirza Uluğ Bey nach Semerkant.")
        self.assert_good("Die Prüfbescheinigung bekommst du gleich nach der bestanden Prüfung vom Prüfer.")
        self.assert_good("Du bist sehr schön und brauchst überhaupt gar keine Schminke zu verwenden.")
        self.assert_good("Ist das so schnell, wie du gehen kannst?")
        self.assert_good("Egal wie lange du versuchst, die Leute davon zu überzeugen")
        self.assert_good("Du bist verheiratet und hast zwei Kinder.")
        self.assert_good("Du bist aus Berlin und wohnst in Bonn.")
        self.assert_good("Sie befestigen die Regalbretter vermittelst dreier Schrauben.")
        self.assert_good("Meine Familie & ich haben uns ein neues Auto gekauft.")
        self.assert_good("Der Bescheid lasse im übrigen die Abwägungen vermissen, wie die Betriebsprüfung zu den Sachverhaltsbeurteilungen gelange, die den von ihr bekämpften Bescheiden zugrundegelegt worden seien.")
        self.assert_good("Die Bildung des Samens erfolgte laut Alkmaion im Gehirn, von wo aus er durch die Adern in den Hoden gelange.")
        self.assert_good("Michael Redmond (geb. 1963, USA).")
        self.assert_good("Würd mich sehr freuen drüber.")
        self.assert_good("Es würd' ein jeder Doktor sein, wenn's Wissen einging wie der Wein.")
        self.assert_good("Bald merkte er, dass er dank seines Talents nichts mehr in der österreichischen Jazzszene lernen konnte.")
        self.assert_good("»Alles, was wir dank dieses Projektes sehen werden, wird für uns neu sein«, so der renommierte Bienenforscher.")
        self.assert_good("Und da wir äußerst Laissez-faire sind, kann man das auch machen.")
        self.assert_good("Duzen, jemanden mit Du anreden, eine Sitte, die bei allen alten Völkern üblich war.")
        self.assert_good("Schreibtischtäter wie Du sind doch eher selten.")
        self.assert_good("Nee, geh du!")
        # self.assert_good("Nee, mach du das mal.")
        # self.assert_good("Ein Mädchen, das genauso wie wir war!")  # known false alarm
        # self.assert_good("Und bin völlig ohne Idee losgelaufen.")  # known false alarm (could be a picky match maybe)
        # incorrect sentences:
        self.assert_bad("Als Borcarbid weißt es eine hohe Härte auf.")
        self.assert_bad("Das greift auf Vorläuferinstitutionen bist auf die Zeit von 1234 zurück.")
        self.assert_bad("Die Eisenbahn dienst überwiegend dem Güterverkehr.")
        self.assert_bad("Die Unterlagen solltest ihr gründlich durcharbeiten.")
        self.assert_bad("Peter bin nett.")
        # self.assert_bad("Solltest ihr das machen?", "Subjekt und Prädikat (Solltest)"); - could be okay in colloquial language (short for "Du solltest ihr das machen")
        self.assert_bad("Weiter befindest sich im Osten die Gemeinde Dorf.")
        self.assert_bad("Ich geht jetzt nach Hause, weil ich schon zu spät bin.")
        self.assert_bad("„Du muss gehen.“")
        self.assert_bad("Du weiß es doch.")
        self.assert_bad("Sie sagte zu mir: „Du muss gehen.“")
        self.assert_bad("„Ich müsst alles machen.“")
        self.assert_bad("„Ich könnt mich sowieso nicht verstehen.“")
        self.assert_bad("Er sagte düster: Ich brauchen mich nicht böse angucken.")
        self.assert_bad("David sagte düster: Ich brauchen mich nicht böse angucken.")
        self.assert_bad("Ich setzet mich auf den weichen Teppich und kreuzte die Unterschenkel wie ein Japaner.")
        self.assert_bad("Ich brauchen einen Karren mit zwei Ochsen.")
        self.assert_bad("Ich haben meinen Ohrring fallen lassen.")
        self.assert_bad("Ich stehen Ihnen gerne für Rückfragen zur Verfügung.")


    def test_wrong_verb_subject(self):
        """testWrongVerbSubject"""
        # correct sentences:
        self.assert_good("Auch morgen lebe ich.")
        self.assert_good("Auch morgen leben wir noch.")
        self.assert_good("Auch morgen lebst du.")
        self.assert_good("Auch morgen lebt er.")
        self.assert_good("Auch wenn du leben möchtest.")
        self.assert_good("auf der er sieben Jahre blieb.")
        self.assert_good("Das absolute Ich ist nicht mit dem individuellen Geist zu verwechseln.")
        self.assert_good("Das Ich ist keine Einbildung")
        self.assert_good("Das lyrische Ich ist verzweifelt.")
        self.assert_good("Den Park, von dem er äußerst genaue Karten zeichnete.")
        self.assert_good("Der auffälligste Ring ist der erster Ring, obwohl er verglichen mit den anderen Ringen sehr schwach erscheint.")
        self.assert_good("Der Fehler, falls er bestehen sollte, ist schwerwiegend.")
        self.assert_good("Der Vorfall, bei dem er einen Teil seines Vermögens verloren hat, ist lange vorbei.")
        self.assert_good("Diese Lösung wurde in der 64'er beschrieben, kam jedoch nie.")
        self.assert_good("Die Theorie, mit der ich arbeiten konnte.")
        # self.assert_good("Die Zeitschrift film-dienst.")
        self.assert_good("Du bist nett.")
        self.assert_good("Du kannst heute leider nicht kommen.")
        self.assert_good("Du lebst.")
        self.assert_good("Du wünschst dir so viel.")
        self.assert_good("Er geht zu ihr.")
        self.assert_good("Er ist nett.")
        self.assert_good("Er kann heute leider nicht kommen.")
        self.assert_good("Er lebt.")
        self.assert_good("Er wisse nicht, ob er lachen oder weinen solle.")
        self.assert_good("Er und du leben.")
        self.assert_good("Er und ich leben.")
        self.assert_good("Falls er bestehen sollte, gehen sie weg.")
        # self.assert_good("Fest wie unsere Eichen halten allezeit wir stand, wenn Stürme brausen übers Land.")  # TODO (remembers "brausen", forgets about "halten")
        self.assert_good("Heere, des Gottes der Schlachtreihen Israels, den du verhöhnt hast.")
        self.assert_good("Ich bin")
        self.assert_good("Ich bin Frankreich!")
        self.assert_good("Ich bin froh, dass ich arbeiten kann.")
        self.assert_good("Ich bin nett.")
        self.assert_good("‚ich bin tot‘")  # TODO 1st token is "‚ich" ?
        self.assert_good("Ich kann heute leider nicht kommen.")
        self.assert_good("Ich lebe.")
        self.assert_good("Lebst du?")
        self.assert_good("Morgen kommen du und ich.")
        self.assert_good("Morgen kommen er, den ich sehr mag, und ich.")
        self.assert_good("Morgen kommen er und ich.")
        self.assert_good("Morgen kommen ich und sie.")
        self.assert_good("Morgen kommen wir und sie.")
        self.assert_good("nachdem er erfahren hatte")
        self.assert_good("Nett bin ich.")
        self.assert_good("Nett bist du.")
        self.assert_good("Nett ist er.")
        self.assert_good("Nett sind wir.")
        self.assert_good("Niemand ahnte, dass er gewinnen könne.")
        self.assert_good("Sie lebt und wir leben.")
        self.assert_good("Sie und er leben.")
        self.assert_good("Sind ich und Peter nicht nette Kinder?")
        self.assert_good("Sodass ich sagen möchte, dass unsere schönen Erinnerungen gut sind.")
        self.assert_good("Wann ich meinen letzten Film drehen werde, ist unbekannt.")
        self.assert_good("Was ich tun muss.")
        self.assert_good("Welche Aufgaben er dabei tatsächlich übernehmen könnte")
        self.assert_good("wie er beschaffen war")
        self.assert_good("Wir gelangen zu dir.")
        self.assert_good("Wir können heute leider nicht kommen.")
        self.assert_good("Wir leben noch.")
        self.assert_good("Wir sind nett.")
        self.assert_good("Wobei wir benutzt haben, dass der Satz gilt.")
        self.assert_good("Wünschst du dir mehr Zeit?")
        self.assert_good("Wyrjtjbst du?")  # make sure that "UNKNOWN" is handled correctly
        self.assert_good("Wenn ich du wäre, würde ich das nicht machen.")
        self.assert_good("Er sagte: „Darf ich bitten, mir zu folgen?“")
        self.assert_good("Ja sind ab morgen dabei.")
        self.assert_good("Oh bin überfragt.")
        # TODO: self.assert_bad("Er fragte irritiert: „Darf ich fragen, die an dich gerichtet werden, beantworten?“")
        self.assert_good("Angenommen, du wärst ich.")
        self.assert_good("Ich denke, dass das Haus, in das er gehen will, heute Morgen gestrichen worden ist.")
        self.assert_good("Ich hab mein Leben, leb du deines!")
        self.assert_good("Da freut er sich, wenn er schlafen geht und was findet.")
        self.assert_good("John nimmt weiter an einem Abendkurs über Journalismus teil.")
        self.assert_good("Viele nahmen an der Aktion teil und am Ende des rAAd-Events war die Tafel zwar bunt, aber leider überwogen die roten Kärtchen sehr deutlich.")
        self.assert_good("Musst also nichts machen.")
        self.assert_good("Eine Situation, wo der Stadtrat gleich mal zum Du übergeht.")
        self.assert_good("Machen wir, sobald wir frische und neue Akkus haben.")
        self.assert_good("Darfst nicht so reden, Franz!")
        self.assert_good("Finde du den Jungen.")
        self.assert_good("Finde Du den Jungen.")
        self.assert_good("Kümmerst dich ja gar nicht um sie.")
        self.assert_good("Könntest was erfinden, wie dein Papa.")
        self.assert_good("Siehst aus wie ein Wachhund.")
        self.assert_good("Solltest es mal in seinem Büro versuchen.")
        self.assert_good("Stehst einfach nicht zu mir.")
        self.assert_good("Stellst für deinen Dad etwas zu Essen bereit.")
        self.assert_good("Springst weit, oder?")
        self.assert_good("Wirst groß, was?")
        # incorrect sentences:
        self.assert_bad("Auch morgen leben du.")
        self.assert_bad("Du weiß noch, dass du das gestern gesagt hast.")
        self.assert_bad("Auch morgen leben du")  # do not segfault because "du" is the last token
        self.assert_bad("Auch morgen leben er.")
        self.assert_bad("Auch morgen leben ich.")
        self.assert_bad("Auch morgen lebte wir noch.")
        self.assert_bad("Du bin nett.", 2)  # TODO 2 errors
        self.assert_bad("Du können heute leider nicht kommen.")
        self.assert_bad("Du können heute leider nicht kommen.", "Du könnest", "Du kannst", "Du könntest", "Wir können", "Sie können", "Du konntest")
        self.assert_bad("Du leben.")
        self.assert_bad("Du wünscht dir so viel.")
        self.assert_bad("Er bin nett.", 2)
        self.assert_bad("Er gelangst zu ihr.", 2)
        self.assert_bad("Er können heute leider nicht kommen.", "Subjekt (Er) und Prädikat (können)")
        self.assert_bad("Er lebst.", 2)
        self.assert_bad("Ich bist nett.", 2)
        # self.assert_bad("Ich geht jetzt nach Hause und dort gehe ich sofort unter die Dusche."); TODO
        self.assert_bad("Ich kannst heute leider nicht kommen.", 2)
        self.assert_bad("Ich leben.")
        self.assert_bad("Ich leben.", "Ich lebe", "Ich lebte", "Wir leben", "Sie leben")
        self.assert_bad("Lebe du?")
        self.assert_bad("Lebe du?", "Lebest du", "Lebst du", "Lebe er", "Lebe es", "Lebtest du", "Lebe ich", "Lebe sie")
        self.assert_bad("Leben du?")
        self.assert_bad("Nett bist ich nicht.", 2)
        self.assert_bad("Nett bist ich nicht.", 2, "bin ich", "bist du", "sei ich", "wäre ich", "war ich")
        self.assert_bad("Nett sind du.")
        self.assert_bad("Nett sind er.")
        self.assert_bad("Nett sind er.", "sind wir", "sei er", "ist er", "sind sie", "wäre er", "war er")
        self.assert_bad("Nett warst wir.", 2)
        self.assert_bad("Wir bin nett.", 2)
        self.assert_bad("Wir gelangst zu ihr.", 2)
        self.assert_bad("Wir könnt heute leider nicht kommen.")
        self.assert_bad("Wünscht du dir mehr Zeit?", "Subjekt (du) und Prädikat (Wünscht)")
        self.assert_bad("Wir lebst noch.", 2)
        self.assert_bad("Wir lebst noch.", 2, "Wir leben", "Wir lebten", "Du lebst")
        self.assert_bad("Er sagte düster: „Ich brauchen mich nicht schuldig fühlen.“", 1, "Ich brauche", "Ich brauchte", "Ich bräuchte", "Wir brauchen", "Sie brauchen")
        self.assert_bad("Er sagte: „Ich brauchen mich nicht schuldig fühlen.“", 1, "Ich brauche", "Ich brauchte", "Ich bräuchte", "Wir brauchen", "Sie brauchen")



INCORRECT_SINGULAR = [
    "Die Autos ist schnell.",
    "Der Hund und die Katze ist draußen.",
    "Ein Hund und eine Katze ist schön.",
    "Der Hund und die Katze ist schön.",
    "Der große Hund und die Katze ist schön.",
    "Der Hund und die graue Katze ist schön.",
    "Der große Hund und die graue Katze ist schön.",
    "Die Kenntnisse ist je nach Bildungsgrad verschieden.",
    "Die Kenntnisse der Sprachen ist je nach Bildungsgrad verschieden.",
    "Die Kenntnisse der Sprache ist je nach Bildungsgrad verschieden.",
    "Die Kenntnisse der europäischen Sprachen ist je nach Bildungsgrad verschieden.",
    "Die Kenntnisse der neuen europäischen Sprachen ist je nach Bildungsgrad verschieden.",
    "Die Kenntnisse der deutschen Sprache ist je nach Bildungsgrad verschieden.",
    "Die Kenntnisse der aktuellen deutschen Sprache ist je nach Bildungsgrad verschieden.",
    "Drei Katzen ist im Haus.",
    "Drei kleine Katzen ist im Haus.",
    "Viele Katzen ist schön.",
    "Drei Viertel der Erdoberfläche ist Wasser.",  # http://canoonet.eu/blog/2012/04/02/ein-drittel-der-schueler-istsind/
    "Die ältesten und bekanntesten Maßnahmen ist die Einrichtung von Schutzgebieten.",
    "Ein Gramm Pfeffer waren früher wertvoll.",
    "Isolation und ihre Überwindung ist ein häufiges Thema in der Literatur."
    # "Katzen ist schön."
]


CORRECT_SINGULAR = [
    "Abschluss und Höhepunkt ist der Festumzug.",
    "Abschluss und Höhepunkt ist der Festumzug, der im Oktober stattfindet.",
    "All diesen Stadtteilen ist die Nähe zum Hamburger Hafen und zu den Industrie- und Gewerbegebieten gemein.",
    "All diesen Bereichen ist gemeinsam, dass sie unterfinanziert sind.",
    "Nicht entmutigen lassen, nur weil Sie kein Genie sind.",
    "Denken Sie daran, dass Sie hier zu Gast sind und sich entsprechend verhalten sollten.",
    "Ist es wahr, dass Sie ein guter Mensch sind?",
    "Die Katze ist schön.",
    "Die eine Katze ist schön.",
    "Eine Katze ist schön.",
    "Für Tunesiens Tourismusindustrie mit seinen Stränden, Oasen und antiken Kulturschätzen ist das Attentat ein verheerender Rückschlag.",
    "Man darf jedoch auch nicht glauben, weil die Brustvergrößerungscremes ein Allheilmittel sind, jedoch sind Sie optimal um Ihr Selbstvertrauen zu erhöhen",
    "Die Rechte der Kinder sind universell.",
    "Beiden Filmen war kein Erfolg beschieden.",
    "In einigen Fällen ist der vermeintliche Beschützer schwach.",
    "Was Wasser für die Fische ist.",
    "In den letzten Jahrzehnten ist die Zusammenarbeit der Astronomie verbessert worden.",
    "Für Oberleitungen bei elektrischen Bahnen ist es dagegen anders.",
    "... deren Thema die Liebe zwischen männlichen Charakteren ist.",
    "Mehr als das in westlichen Produktionen der Fall ist.",
    "Da das ein fast aussichtsloses Unterfangen ist.",
    "Was sehr verbreitet bei der Synthese organischer Verbindungen ist.",
    "In chemischen Komplexverbindungen ist das Kation wichtig.",
    "In chemischen Komplexverbindungen ist das As5+-Kation wichtig.",
    "Die selbstständige Behandlung psychischer Störungen ist jedoch ineffektiv.",
    "Die selbstständige Behandlung eigener psychischer Störungen ist jedoch ineffektiv.",
    "Im Gegensatz zu anderen akademischen Berufen ist es in der Medizin durchaus üblich ...",
    "Im Unterschied zu anderen Branchen ist Ärzten anpreisende Werbung verboten.",
    "Aus den verfügbaren Quellen ist es ersichtlich.",
    "Das Mädchen mit den langen Haaren ist Judy.",
    "Der Durchschnitt offener Mengen ist nicht notwendig offen.",
    "Der Durchschnitt vieler offener Mengen ist nicht notwendig offen.",
    "Der Durchschnitt unendlich vieler offener Mengen ist nicht notwendig offen.",
    "Der Ausgangspunkt für die heute gebräuchlichen Alphabete ist ...",
    "Nach sieben männlichen Amtsvorgängern ist Merkel ...",
    "Für einen japanischen Hamburger ist er günstig.",
    "Derzeitiger Bürgermeister ist seit 2008 der ehemalige Minister Müller.",
    "Derzeitiger Bürgermeister der Stadt ist seit 2008 der ehemalige Minister Müller.",
    "Die Eingabe mehrerer assoziativer Verknüpfungen ist beliebig.",
    "Die inhalative Anwendung anderer Adrenalinpräparate zur Akutbehandlung asthmatischer Beschwerden ist somit außerhalb der arzneimittelrechtlichen Zulassung.",
    "Die Kategorisierung anhand morphologischer Merkmale ist nicht objektivierbar.",
    "Die Kategorisierung mit morphologischen Merkmalen ist nicht objektivierbar.",
    "Ute, deren Hauptproblem ihr Mangel an Problemen ist, geht baden.",
    "Ute, deren Hauptproblem ihr Mangel an realen Problemen ist, geht baden.",
    "In zwei Wochen ist Weihnachten.",
    "In nur zwei Wochen ist Weihnachten.",
    "Mit chemischen Methoden ist es möglich, das zu erreichen.",
    "Für die Stadtteile ist auf kommunalpolitischer Ebene jeweils ein Beirat zuständig.",
    "Für die Stadtteile und selbständigen Ortsteile ist auf kommunalpolitischer Ebene jeweils ein Beirat zuständig.",
    "Die Qualität der Straßen ist unterschiedlich.",
    "In deutschen Installationen ist seit Version 3.3 ein neues Feature vorhanden.",
    "In deren Installationen ist seit Version 3.3 ein neues Feature vorhanden.",
    "In deren deutschen Installationen ist seit Version 3.3 ein neues Feature vorhanden.",
    "Die Führung des Wortes in Unternehmensnamen ist nur mit Genehmigung zulässig.",
    "Die Führung des Wortes in Unternehmensnamen und Institutionen ist nur mit Genehmigung zulässig.",
    "Die Hintereinanderreihung mehrerer Einheitenvorsatznamen oder Einheitenvorsatzzeichen ist nicht zulässig.",
    "Eines ihrer drei Autos ist blau und die anderen sind weiß.",
    "Eines von ihren drei Autos ist blau und die anderen sind weiß.",
    "Bei fünf Filmen war Robert F. Boyle für das Production Design verantwortlich.",
    "Insbesondere das Wasserstoffatom als das einfachste aller Atome war dabei wichtig.",
    "In den darauf folgenden Wochen war die Partei führungslos",
    "Gegen die wegen ihrer Schönheit bewunderte Phryne ist ein Asebie-Prozess überliefert.",
    "Dieses für Ärzte und Ärztinnen festgestellte Risikoprofil ist berufsunabhängig.",
    "Das ist problematisch, da kDa eine Masseeinheit und keine Gewichtseinheit ist.",
    "Nach sachlichen oder militärischen Kriterien war das nicht nötig.",
    "Die Pyramide des Friedens und der Eintracht ist ein Bauwerk.",
    "Ohne Architektur der Griechen ist die westliche Kultur der Neuzeit nicht denkbar.",
    "Ohne Architektur der Griechen und Römer ist die westliche Kultur der Neuzeit nicht denkbar.",
    "Ohne Architektur und Kunst der Griechen und Römer ist die westliche Kultur der Neuzeit nicht denkbar.",
    "In denen jeweils für eine bestimmte Anzahl Elektronen Platz ist.",
    "Mit über 1000 Handschriften ist Aristoteles ein Vielschreiber.",
    "Mit über neun Handschriften ist Aristoteles ein Vielschreiber.",
    "Die Klammerung assoziativer Verknüpfungen ist beliebig.",
    "Die Klammerung mehrerer assoziativer Verknüpfungen ist beliebig.",
    "Einen Sonderfall bildete jedoch Ägypten, dessen neue Hauptstadt Alexandria eine Gründung Alexanders und der Ort seines Grabes war.",
    "Jeder Junge und jedes Mädchen war erfreut.",
    "Jedes Mädchen und jeder Junge war erfreut.",
    "Jede Frau und jeder Junge war erfreut.",
    "Als Wissenschaft vom Erleben des Menschen einschließlich der biologischen Grundlagen ist die Psychologie interdisziplinär.",
    "Als Wissenschaft vom Erleben des Menschen einschließlich der biologischen und sozialen Grundlagen ist die Psychologie interdisziplinär.",
    "Als Wissenschaft vom Erleben des Menschen einschließlich der biologischen und neurowissenschaftlichen Grundlagen ist die Psychologie interdisziplinär.",  # 'neurowissenschaftlichen' not known
    "Als Wissenschaft vom Erleben und Verhalten des Menschen einschließlich der biologischen bzw. sozialen Grundlagen ist die Psychologie interdisziplinär.",
    "Alle vier Jahre ist dem Volksfest das Landwirtschaftliche Hauptfest angeschlossen.",
    "Aller Anfang ist schwer.",
    "Alle Dichtung ist zudem Darstellung von Handlungen.",
    "Allen drei Varianten ist gemeinsam, dass meistens nicht unter bürgerlichem...",
    "Er sagte, dass es neun Uhr war.",
    "Auch den Mädchen war es untersagt, eine Schule zu besuchen.",
    "Das dazugehörende Modell der Zeichen-Wahrscheinlichkeiten ist unter Entropiekodierung beschrieben.",
    "Ein über längere Zeit entladener Akku ist zerstört.",
    "Der Fluss mit seinen Oberläufen Río Paraná und Río Uruguay ist der wichtigste Wasserweg.",
    "In den alten Mythen und Sagen war die Eiche ein heiliger Baum.",
    "In den alten Religionen, Mythen und Sagen war die Eiche ein heiliger Baum.",
    "Zehn Jahre ist es her, seit ich mit achtzehn nach Tokio kam.",
    "Bei den niedrigen Oberflächentemperaturen ist Wassereis hart wie Gestein.",
    "Bei den sehr niedrigen Oberflächentemperaturen ist Wassereis hart wie Gestein.",
    "Die älteste und bekannteste Maßnahme ist die Einrichtung von Schutzgebieten.",
    "Die größte Dortmunder Grünanlage ist der Friedhof.",
    "Die größte Berliner Grünanlage ist der Friedhof.",
    "Die größte Bielefelder Grünanlage ist der Friedhof.",
    "Die Pariser Linie ist hier mit 2,2558 mm gerechnet.",
    "Die Frankfurter Innenstadt ist 7 km entfernt.",
    "Die Dortmunder Konzernzentrale ist ein markantes Gebäude an der Bundesstraße 1.",
    "Die Düsseldorfer Brückenfamilie war ursprünglich ein Sammelbegriff.",
    "Die Düssel ist ein rund 40 Kilometer langer Fluss.",
    "Die Berliner Mauer war während der Teilung Deutschlands die Grenze.",
    "Für amtliche Dokumente und Formulare ist das anders.",
    "Wie viele Kilometer ist ihre Stadt von unserer entfernt?",
    "Über laufende Sanierungsmaßnahmen ist bislang nichts bekannt.",
    "In den letzten zwei Monate war ich fleißig wie eine Biene.",
    "Durch Einsatz größerer Maschinen und bessere Kapazitätsplanung ist die Zahl der Flüge gestiegen.",
    "Die hohe Zahl dieser relativ kleinen Verwaltungseinheiten ist immer wieder Gegenstand von Diskussionen.",
    "Teil der ausgestellten Bestände ist auch die Bierdeckel-Sammlung.",
    "Teil der umfangreichen dort ausgestellten Bestände ist auch die Bierdeckel-Sammlung.",
    "Teil der dort ausgestellten Bestände ist auch die Bierdeckel-Sammlung.",
    "Der zweite Teil dieses Buches ist in England angesiedelt.",
    "Eine der am meisten verbreiteten Krankheiten ist die Diagnose",
    "Eine der verbreitetsten Krankheiten ist hier.",
    "Die Krankheit unserer heutigen Städte und Siedlungen ist folgendes.",
    "Die darauffolgenden Jahre war er ...",
    "Die letzten zwei Monate war ich fleißig wie eine Biene.",
    "Bei sehr guten Beobachtungsbedingungen ist zu erkennen, dass ...",
    "Die beste Rache für Undank und schlechte Manieren ist Höflichkeit.",
    "Ein Gramm Pfeffer war früher wertvoll.",
    "Die größte Stuttgarter Grünanlage ist der Friedhof.",
    "Mancher will Meister sein und ist kein Lehrjunge gewesen.",
    "Ellen war vom Schock ganz bleich.",  # Ellen: auch Plural von Elle
    "Nun gut, die Nacht ist sehr lang, oder?",
    "Der Morgen ist angebrochen, die lange Nacht ist vorüber.",
    "Die stabilste und häufigste Oxidationsstufe ist dabei −1.",
    "Man kann nicht eindeutig zuordnen, wer Täter und wer Opfer war.",
    "Ich schätze, die Batterie ist leer.",
    "Der größte und schönste Tempel eines Menschen ist in ihm selbst.",
    "Begehe keine Dummheit zweimal, die Auswahl ist doch groß genug!",
    "Seine größte und erfolgreichste Erfindung war die Säule.",
    "Egal was du sagst, die Antwort ist Nein.",
    "... in der Geschichte des Museums, die Sammlung ist seit 2011 zugänglich.",
    "Deren Bestimmung und Funktion ist allerdings nicht so klar.",
    "Sie hat eine Tochter, die Pianistin ist.",
    "Ja, die Milch ist sehr gut.",
    "Der als Befestigung gedachte östliche Teil der Burg ist weitgehend verfallen.",
    "Das Kopieren und Einfügen ist sehr nützlich.",
    "Der letzte der vier großen Flüsse ist die Kolyma.",
    "In christlichen, islamischen und jüdischen Traditionen ist das höchste Ziel der meditativen Praxis.",
    "Der Autor der beiden Spielbücher war Markus Heitz selbst.",
    "Der Autor der ersten beiden Spielbücher war Markus Heitz selbst.",
    "Das Ziel der elf neuen Vorstandmitglieder ist klar definiert.",
    "Laut den meisten Quellen ist das Seitenverhältnis der Nationalflagge...",
    "Seine Novelle, die eigentlich eine Glosse ist, war toll.",
    "Für in Österreich lebende Afrikaner und Afrikanerinnen ist dies nicht üblich.",
    "Von ursprünglich drei Almhütten ist noch eine erhalten.",
    "Einer seiner bedeutendsten Kämpfe war gegen den späteren Weltmeister.",
    "Aufgrund stark schwankender Absatzmärkte war die GEFA-Flug Mitte der 90er Jahre gezwungen, ...",
    "Der Abzug der Besatzungssoldaten und deren mittlerweile ansässigen Angehörigen der Besatzungsmächte war vereinbart.",
    "Das Bündnis zwischen der Sowjetunion und Kuba war für beide vorteilhaft.",
    "Knapp acht Monate ist die Niederlage nun her.",
    "Vier Monate ist die Niederlage nun her.",
    "Sie liebt Kunst und Kunst war auch kein Problem, denn er würde das Geld zurückkriegen.",
    "Bei komplexen und andauernden Störungen ist der Stress-Stoffwechsel des Hundes entgleist.",
    "Eltern ist der bisherige Kita-Öffnungsplan zu unkonkret",
    "Einer der bedeutendsten Māori-Autoren der Gegenwart ist Witi Ihimaera.",
    "Start und Ziel ist Innsbruck",
    "Heute ist sie lieb.",
    "Anfänger wie auch Fortgeschrittene sind herzlich willkommen!",
    "Die Aussichten für Japans Zukunft sind düster.",
    "Das Angeln an Mallorcas Felsküsten ist überaus Erfolg versprechend.",
    "Das bedeutendste Bauwerk und Wahrzeichen der Stadt ist die ehemalige Klosterkirche des Klosters Hofen.",
    "Das saisonale Obst und Gemüse ist köstlich und oft deutlich günstiger als in der Stadt.",
    "Gründer und Leiter des Zentrums ist der Rabbiner Marvin Hier, sein Stellvertreter ist Rabbi Abraham Cooper.",
    "Dank unserer Kunden, Freunde, Partner und unserer Mitarbeiter ist Alpenwahnsinn zur Heimatadresse für schöne Trachtenmode geworden.",
    "Laut seiner Recherche und mehreren Berichten der Welt ist die Zahl zu niedrig gegriffen."
]


INCORRECT_PLURAL = [
    "Die Katze sind schön.",
    "Die Katze waren schön.",
    "Der Text sind gut.",
    "Das Auto sind schnell.",
    # "Herr Müller sind alt." -- Müller has a plural reading
    "Herr Schröder sind alt.",
    "Julia und Karsten ist alt.",
    "Julia, Heike und Karsten ist alt.",
    "Herr Karsten Schröder sind alt."
    # "Die heute bekannten Bonsai sind häufig im japanischen Stil gestaltet."  # plural: Bonsais (laut Duden) - sollte von AgreementRule gefunden werden
]


CORRECT_PLURAL = [
    "Wenn Sie kein Teil der Lösung sind, sind Sie ein Teil des Problems.",
    "Er bemerkte, dass Experimente nicht gerade sein Ding sind",
    "Die meisten der Spieler sind nicht vermögend",
    "Wie viel Prozent der Menschen sind total bescheuert?",
    "Glaubt wirklich jemand, dass gute Fotos keine Arbeit sind?",
    "Zwei Schülern war aufgefallen, dass man im Fernsehen dazu nichts mehr sieht.",
    "Auch die Reste eines sehr großen Insektenfressers sind unter den Fossilien.",
    "Eine Persönlichkeit sind Sie selbst.",
    "Die Katzen sind schön.",
    "Frau Meier und Herr Müller sind alt.",
    "Frau Julia Meier und Herr Karsten Müller sind alt.",
    "Julia und Karsten sind alt.",
    "Julia, Heike und Karsten sind alt.",
    "Frau und Herr Müller sind alt.",
    "Herr und Frau Schröder sind alt.",
    "Herr Meier und Frau Schröder sind alt.",
    "Die restlichen 86 Prozent sind in der Flasche.",
    "Die restlichen sechsundachtzig Prozent sind in der Flasche.",
    "Die restlichen 86 oder 87 Prozent sind in der Flasche.",
    "Die restlichen 86 % sind in der Flasche.",
    "Durch den schnellen Zerfall des Actiniums waren stets nur geringe Mengen verfügbar.",
    "Soda und Anilin waren die ersten Produkte des Unternehmens.",
    "Bob und Tom sind Brüder.",
    "Letztes Jahr sind wir nach London gegangen.",
    "Trotz des Regens sind die Kinder in die Schule gegangen.",
    "Die Zielgruppe sind Männer.",
    "Männer sind die Zielgruppe.",
    "Die Zielgruppe sind meist junge Erwachsene.",
    "Die USA sind ein repräsentativer demokratischer Staat.",
    "Wesentliche Eigenschaften der Hülle sind oben beschrieben.",
    "Wesentliche Eigenschaften der Hülle sind oben unter Quantenmechanische Atommodelle und Erklärung grundlegender Atomeigenschaften dargestellt.",
    "Er und seine Schwester sind eingeladen.",
    "Er und seine Schwester sind zur Party eingeladen.",
    "Sowohl er als auch seine Schwester sind zur Party eingeladen.",
    "Rekonstruktionen oder der Wiederaufbau sind wissenschaftlich sehr umstritten.",
    "Form und Materie eines Einzeldings sind aber nicht zwei verschiedene Objekte.",
    "Dieses Jahr sind die Birnen groß.",
    "Es so umzugestalten, dass sie wie ein Spiel sind.",
    "Die Zielgruppe sind meist junge Erwachsene.",
    "Die Ursache eines Hauses sind so Ziegel und Holz.",
    "Vertreter dieses Ansatzes sind unter anderem Roth und Meyer.",
    "Sowohl sein Vater als auch seine Mutter sind tot.",
    "Einige der Inhaltsstoffe sind schädlich.",
    "Diese Woche sind wir schon einen großen Schritt weiter.",
    "Diese Woche sind sie hier.",
    "Vorsitzende des Vereins waren:",
    "Weder Gerechtigkeit noch Freiheit sind möglich, wenn nur das Geld regiert.",
    "Ein typisches Beispiel sind Birkenpollenallergene.",
    "Eine weitere Variante sind die Miniatur-Wohnlandschaften.",
    "Eine Menge englischer Wörter sind aus dem Lateinischen abgeleitet.",
    "Völkerrechtlich umstrittenes Territorium sind die Falklandinseln.",
    "Einige dieser älteren Synthesen sind wegen geringer Ausbeuten ...",
    "Einzelne Atome sind klein.",
    "Die Haare dieses Jungens sind schwarz.",
    "Die wichtigsten Mechanismen des Aminosäurenabbaus sind:",
    "Wasserlösliche Bariumverbindungen sind giftig.",
    "Die Schweizer Trinkweise ist dabei die am wenigsten etablierte.",
    "Die Anordnung der vier Achsen ist damit identisch.",
    "Die Nauheimer Musiktage, die immer wieder ein kultureller Höhepunkt sind.",
    "Räumliche und zeitliche Abstände sowie die Trägheit sind vom Bewegungszustand abhängig.",
    "Solche Gewerbe sowie der Karosseriebau sind traditionell stark vertreten.",
    "Hundert Dollar sind doch gar nichts!",
    "Sowohl Tom als auch Maria waren überrascht.",
    "Robben, die die hauptsächliche Beute der Eisbären sind.",
    "Die Albatrosse sind eine Gruppe von Seevögeln",
    "Die Albatrosse sind eine Gruppe von großen Seevögeln",
    "Die Albatrosse sind eine Gruppe von großen bis sehr großen Seevögeln",
    "Vier Elemente, welche der Urstoff aller Körper sind.",
    "Die Beziehungen zwischen Kanada und dem Iran sind seitdem abgebrochen.",
    "Die diplomatischen Beziehungen zwischen Kanada und dem Iran sind seitdem abgebrochen.",
    "Die letzten zehn Jahre seines Lebens war er erblindet.",
    "Die letzten zehn Jahre war er erblindet.",
    "... so dass Knochenbrüche und Platzwunden die Regel sind.",
    "Die Eigentumsverhältnisse an der Gesellschaft sind unverändert geblieben.",
    "Gegenstand der Definition sind für ihn die Urbilder.",
    "Mindestens zwanzig Häuser sind abgebrannt.",
    "Sie hielten geheim, dass sie Geliebte waren.",
    "Einige waren verspätet.",
    "Kommentare, Korrekturen und Kritik sind verboten.",
    "Kommentare, Korrekturen, Kritik sind verboten.",
    "Letztere sind wichtig, um die Datensicherheit zu garantieren.",
    "Jüngere sind oft davon überzeugt, im Recht zu sein.",
    "Verwandte sind selten mehr als Bekannte.",
    "Ursache waren die hohe Arbeitslosigkeit und die Wohnungsnot.",
    "Ursache waren unter anderem die hohe Arbeitslosigkeit und die Wohnungsnot.",
    "Er ahnt nicht, dass sie und sein Sohn ein Paar sind.",
    "Die Ursachen der vorliegenden Durchblutungsstörung sind noch unbekannt.",
    "Der See und das Marschland sind ein Naturschutzgebiet",
    "Details, Dialoge, wie auch die Typologie der Charaktere sind frei erfunden.",
    "Die internen Ermittler und auch die Staatsanwaltschaft sind nun am Zug.",
    "Sie sind so erfolgreich, weil sie eine Einheit sind.",
    "Wie viele Erwerbstätige sind im Gesundheitswesen beschäftigt?",
    "Auch Polizisten zu Fuß sind unterwegs.",
    "Julia sagte, dass Vater und Mutter zu Hause sind.",
    "Damit müssen sie zurechtkommen, wenn Kinder zu Hause sind.",
    "Auch Studien zu Zink sind vielversprechend.",
    "Die Züge vor Ort sind nicht klimatisiert.",
    "Ich verspreche dir, dass wir ein tolles Team sind."
]


CORRECT_SINGULAR_AND_PLURAL = [
    "Solchen Personen ist der Zugriff auf diese Daten verboten.",
    "Personen ist der Zugriff auf diese Daten verboten.",
    "So mancher Mitarbeiter und manche Führungskraft ist im Urlaub.",
    "So mancher Mitarbeiter und manche Führungskraft sind im Urlaub.",
    "Jeder Schüler und jede Schülerin ist mal schlecht gelaunt.",
    "Jeder Schüler und jede Schülerin sind mal schlecht gelaunt.",
    "Kaum mehr als vier Prozent der Fläche ist für landwirtschaftliche Nutzung geeignet.",
    "Kaum mehr als vier Prozent der Fläche sind für landwirtschaftliche Nutzung geeignet.",
    "Kaum mehr als vier Millionen Euro des Haushalts ist verplant.",
    "Kaum mehr als vier Millionen Euro des Haushalts sind verplant.",
    "80 Cent ist nicht genug.",  # ugs.
    "80 Cent sind nicht genug.",
    "1,5 Pfund ist nicht genug.",  # ugs.
    "1,5 Pfund sind nicht genug.",
    "Hier ist sowohl Anhalten wie Parken verboten.",
    "Hier sind sowohl Anhalten wie Parken verboten.",
    "Der Eifer der Männer und Frauen ist enorm."
]



class TestSubjectVerbAgreementRule:
    """Port of SubjectVerbAgreementRuleTest."""

    @pytest.fixture(autouse=True)
    def set_up(self, lt):
        self.lt = lt
        self.rule = SubjectVerbAgreementRule(messages_for('de'), get_language('de-DE'))

    def get_matches(self, s):
        return self.rule.match(self.lt.get_analyzed_sentence(s))

    def get_tokens(self, s):
        return self.lt.get_analyzed_sentence(s).get_tokens_without_whitespace()

    def test_prev_chunk_is_nominative(self):
        """testPrevChunkIsNominative"""
        assert self.rule.prev_chunk_is_nominative(self.get_tokens("Die Katze ist süß"), 2)
        assert self.rule.prev_chunk_is_nominative(self.get_tokens("Das Fell der Katzen ist süß"), 4)

        assert not self.rule.prev_chunk_is_nominative(self.get_tokens("Dem Mann geht es gut."), 2)
        assert not self.rule.prev_chunk_is_nominative(self.get_tokens("Dem alten Mann geht es gut."), 2)
        assert not self.rule.prev_chunk_is_nominative(self.get_tokens("Beiden Filmen war kein Erfolg beschieden."), 2)
        assert not self.rule.prev_chunk_is_nominative(self.get_tokens("Aber beiden Filmen war kein Erfolg beschieden."),
                                                      3)
        # assert not self.rule.prev_chunk_is_nominative(self.get_tokens("Der Katzen Fell ist süß"), 3)

    def test_array_out_of_bounds_bug(self):
        """testArrayOutOfBoundsBug"""
        self.rule.match(self.lt.get_analyzed_sentence("Die nicht Teil des Näherungsmodells sind"))

    @pytest.mark.parametrize('sentence', INCORRECT_SINGULAR)
    def test_rule_with_incorrect_singular_verb(self, sentence):
        """testRuleWithIncorrectSingularVerb"""
        assert len(self.get_matches(sentence)) > 0, "Did not get the expected match for '%s'" % sentence

    @pytest.mark.parametrize('sentence', CORRECT_SINGULAR)
    def test_rule_with_correct_singular_verb(self, sentence):
        """testRuleWithCorrectSingularVerb"""
        matches = self.get_matches(sentence)
        assert not matches, "Got unexpected match(es) for '%s': %r" % (sentence, matches)

    @pytest.mark.parametrize('sentence', INCORRECT_PLURAL)
    def test_rule_with_incorrect_plural_verb(self, sentence):
        """testRuleWithIncorrectPluralVerb"""
        assert len(self.get_matches(sentence)) > 0, "Did not get the expected match for '%s'" % sentence

    @pytest.mark.parametrize('sentence', CORRECT_PLURAL)
    def test_rule_with_correct_plural_verb(self, sentence):
        """testRuleWithCorrectPluralVerb"""
        matches = self.get_matches(sentence)
        assert not matches, "Got unexpected match(es) for '%s': %r" % (sentence, matches)

    @pytest.mark.parametrize('sentence', CORRECT_SINGULAR_AND_PLURAL)
    def test_rule_with_correct_singular_and_plural_verb(self, sentence):
        """testRuleWithCorrectSingularAndPluralVerb"""
        # Manchmal sind beide Varianten korrekt:
        # siehe https://dict.leo.org/grammatik/deutsch/Wort/Verb/Kategorien/Numerus-Person/ProblemNum.html
        matches = self.get_matches(sentence)
        assert not matches, "Got unexpected match(es) for '%s': %r" % (sentence, matches)


class TestMissingVerbRule:
    """Port of MissingVerbRuleTest."""

    @pytest.fixture(autouse=True)
    def set_up(self, lt):
        self.lt = lt
        self.rule = MissingVerbRule(messages_for('en'), get_language('de-DE'))

    def assert_good(self, text):
        assert len(self.rule.match(self.lt.get_analyzed_sentence(text))) == 0, \
            "Found unexpected error in: '%s'" % text

    def assert_bad(self, text):
        assert len(self.rule.match(self.lt.get_analyzed_sentence(text))) == 1, \
            "Did not find expected error in: '%s'" % text

    def test(self):
        """test"""
        self.assert_good("Da ist ein Verb, mal so zum testen.")
        self.assert_good("Überschrift ohne Verb aber doch nicht zu kurz")
        self.assert_good("Sprechen Sie vielleicht zufällig Türkisch?")
        self.assert_good("Leg den Tresor in den Koffer im Kofferraum.")
        self.assert_good("Bring doch einfach deine Kinder mit.")
        self.assert_good("Gut so.")  # no verb, but very short
        self.assert_good("Ja!")  # no verb, but very short
        self.assert_good("Vielen Dank für alles, was Du für mich getan hast.")
        self.assert_good("Herzlichen Glückwunsch zu Deinem zwanzigsten Geburtstag.")

        self.assert_bad("Dieser Satz kein Verb.")
        self.assert_bad("Aus einer Idee sich erste Wortgruppen, aus Wortgruppen einzelne Sätze, aus Sätzen ganze "
                        "Texte.")
        self.assert_bad("Ich ein neues Rad.")
        # self.assert_bad("Ich einen neuen Fehler gefunden.")  # see issue #42
