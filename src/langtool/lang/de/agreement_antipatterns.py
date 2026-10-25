"""Port of org.languagetool.rules.de.AgreementRuleAntiPatterns1,
AgreementRuleAntiPatterns2 and AgreementRuleAntiPatterns3: the anti-patterns
of the AgreementRule (converted mechanically from the Java
PatternTokenBuilder code)."""

from ...analysis import SENTENCE_END_TAGNAME, SENTENCE_START_TAGNAME
from ...patterns.pattern_token import PatternTokenBuilder, cs_regex, cs_token, pos, pos_regex, token, token_regex

# AgreementRuleAntiPatterns1.MONTH_NAMES_REGEX
MONTH_NAMES_REGEX = 'Jänner|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember'


# AgreementRuleAntiPatterns1.ANTI_PATTERNS
def anti_patterns_1():
    return [
        [
          token_regex("bring(s?t|en?)"),
          token("das"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*PLU.*"),
          token("mit"),
          token("sich")
        ],
        [
          token_regex("der|die|das"),
          pos_regex("_english_ignore_")
        ],
        [
          token_regex("der|des"),   # "Übernahme der früher selbständigen Gesellschaft"
          token("früher"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token("sein"),   # "ich kann nicht dabei sein nächste Woche"
          pos("ADV:TMP"),
          token_regex("Woche|Monat|Jahr")
        ],
        [
          pos_regex("(ART|PRO):.*"),   # "Wie viele Kolleg/-innen haben sie?"
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.*"),
          token("/"),
          token_regex("-in|-innen")
        ],
        [
          token("wegen"),   # "...und hatte wegen des vielen Trinkens Kopfschmerzen." (#4695)
          token("des"),
          token("vielen"),
          pos_regex("SUB:GEN:SIN:.*"),
          pos_regex("SUB:GEN:.*")
        ],
        [
          token_regex("des"),   # "Chef des renommierten Institute for Fiscal Studies (IFS)"
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          token("Institute"),
          token_regex("for|of")
        ],
        [
          token("zur"),   # "Bis zur Anfang Juni geplanten Eröffnung gebe es noch einiges zu tun."
          token_regex("Anfang|Ende|Mitte"),
          token_regex(MONTH_NAMES_REGEX),
          pos_regex("PA2:.*"),
          pos_regex("SUB:.*FEM.*")
        ],
        [  # "Jedes Grad zählt"
          token("jedes"),
          token("Grad")
        ],
        [
          token("euer"),
          token("Gnaden")
        ],
        [
          token("die"),  # "Die Adelmanns" (Nachname not tagged properly)
          PatternTokenBuilder().pos("SUB:GEN:SIN:MAS").token_regex(".*manns").build()
        ],
        [
          token("für"),
          token("viele"),
          token("Grund"),
          token("genug")
        ],
        [
          token("sowas"),   # "Wir können sowas Mittwoch machen."
          token_regex("Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag")
        ],
        [
          token("bei"),   # "Es kann gut sein, dass bei sowas Probleme erkannt werden."
          token("sowas"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.*PLU.*")
        ],
        [
          token("beides"),   # "Beides Grund genug, es mal zu probieren."
          token("Grund")
        ],
        [
          token("bisschen"),   # "Für schwangere Frauen gelten wohl ein bisschen strengere Einschränkungen."
          pos_regex("ADJ.*"),
          pos_regex("SUB.*PLU.*")
          ],
        [
          token_regex("der|die|den"),   # "Ein Haus für die weniger Glücklichen."
          token_regex("weniger|besser|mehr|schlechter"),
          pos_regex("SUB:.*PLU:.*:ADJ")
        ],
        [
          token_regex("wusste|weiß"),   # "Da wusste keiner Bescheid"
          token_regex("keiner?"),
          token("Bescheid")
        ],
        [
          token_regex("keiner?"),  # "es braucht keiner Bescheid wissen"
          token("Bescheid"),
          token("wissen")
        ],
        [
          token("von"),  # "eine von manchem geforderte Übergewinnsteuer"
          token_regex("manche[nmr]?"),
          pos_regex("PA2:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token("niemandem"),  # "hat niemandem wirkliches Leid zugefügt"
          pos_regex("ADJ:NOM:SIN:NEU:.*"),
          pos_regex("SUB:.*SIN.*")
        ],
        [   # "Eine mehrere hundert Meter lange Startbahn."
          token_regex("viele|mehrere"),
          pos("ZAL"),
          token_regex("Meter|.+meter"),
          token_regex("lange[ns]?|kurze[ns]?|große[ns]?|kleine[ns]?"),
          pos_regex("SUB:.*")
        ],
        [  # "eine alles in allem spannende Geschichte"
          token("alles"),
          token("in"),
          token("allem")
        ],
        [  # "Man darf gespannt sein, wen Müller für"
          token("wen"),
          pos_regex("EIG:.*")
        ],
        [  # "das Vereinslokal in welchem Zusammenkünfte"
          token_regex("in|zu"),
          token_regex("welche[nmrs]"),
          pos_regex("SUB.*PLU.*")
        ],
        [  # "er lässt niemanden zu Wort kommen"
          token("niemanden"),
          token("zu"),
          token("Wort")
        ],
        [
          token("zu"),
          token_regex("Kopfe?|Zwecken?|Ohren|Fü(ß|ss)en|Fu(ß|ss)|Händen|Beginn|Anfang|Geld|Gesicht|Recht|Unrecht|.*stein")
        ],
        [   # "Zum anderen verringert Zuversicht seelische Belastungen"
          token("zum"),
          token("anderen"),
          pos_regex("VER:3:SIN:(PRÄ|PRT):SFT"),
          pos_regex("SUB:NOM:SIN:.*")
        ],
        [
          token("an"),
          token("allem"),
          token("Schuld")
        ],
        [
          pos_regex("ART.*|PRO:POS.*"),
          token("zu"),
          token_regex("gleichen|gro(ß|ss)en|kleinen"),
          token("Teilen")
        ],
        [  # "Bald läppert sich das zu richtigem Geld zusammen."
          PatternTokenBuilder().token_regex("läppern|summieren").match_inflected_forms().build(),
          token("sich"),
          pos_regex("PRO:DEM.*"),
          token("zu"),
          pos_regex("ADJ:DAT.*"),
          pos_regex("SUB:DAT.*")
        ],
        [  # "Die Weimarer Parks laden ja förmlich ein zu Fotos im öffentlichen Raum."
          PatternTokenBuilder().token("laden").match_inflected_forms().set_skip(-1).build(),
          token("ein"),
          token("zu"),
          pos_regex("SUB:AKK.*")
        ],
        [  # "Es is schwierig für mich, diese zu Sätzen zu verbinden."
          pos_regex("PRO:DEM.*"),
          token("zu"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB.*"),
          PatternTokenBuilder().token("zu").min(0).build(),
          token_regex("verbinden|verhelfen|fähig")
        ],
        [  # "Kombinieren Sie diese zu ganzen Bewegungsprogrammen"
          token_regex("diese[sn]?"),
          token("zu"),
          pos_regex("ADJ.*PLU.*"),
          pos_regex("SUB.*PLU.*")
        ],
        [  # "Es kam zum einen zu technischen Problemen, zum anderen wurde es unübersichtlich."
          token("zum"),
          token("einen"),
          token("zu"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          PatternTokenBuilder().pos_regex("SUB.*").set_skip(-1).build(),
          token("zum"),
          token("anderen")
        ],
        [  # "Das Spiel wird durch den zu neuer Größe gewachsenen Torwart dominiert."
          pos_regex("ART.*|PRO:POS.*"),
          token("zu"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).max(2).build(),
          pos_regex("SUB.*"),
          pos_regex("PA2.*")
        ],
        [  # "Dort findet sich schlicht und einfach alles & das zu sagenhafter Hafenkulisse."
          token_regex("und|&"),
          pos_regex("ART:DEF.*"),
          token("zu"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [  # "die zu basisdemokratischen Prozessen benötigte Mitbestimmung"
          token("die"),
          token("zu"),
          pos_regex("ADJ.*"),
          pos_regex("SUB:.*"),
          token_regex("nötigen?|benötigten?|erforderlichen?")
        ],
        [
          pos_regex("PRO:.*|ART.*"),
          token("zu"),
          token_regex("wenige|viele|verschiedene|höheren|günstigeren"),
          pos_regex("SUB:.*PLU.*")
        ],
        [
          pos_regex("PRO:.*|ART.*"),
          token("zu"),
          token("Hause")
        ],
        [  # "Und das zu guter Qualität."
          pos_regex("PRO:.*|ART.*"),
          token("zu"),
          pos_regex("ADJ:DAT:SIN:FEM:GRU:SOL"),
          token("Qualität")
        ],
        [
          pos_regex("PRO.*"),  # "Es gibt viele Stock Screener."
          pos_regex("SUB:.*"),
          PatternTokenBuilder().pos("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          pos_regex("PRP.*(DAT|AKK)"),  # "zur Learning Academy"
          pos_regex("SUB:.*"),
          PatternTokenBuilder().pos("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          pos_regex("PRP.*DAT"),  # "zur neuen Learning Academy"
          pos_regex("ADJ.*DAT.*"),
          pos_regex("SUB:.*"),
          PatternTokenBuilder().pos("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          pos_regex("PRP.*AKK"),  # "zur neuen Learning Academy"
          pos_regex("ADJ.*AKK.*"),
          pos_regex("SUB:.*"),
          PatternTokenBuilder().pos("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          pos_regex("PRO.*"),  # "Es gibt viele verschiedene Stock Screener."
          pos_regex("(ADJ|PA2).*"),
          pos_regex("SUB:.*"),
          PatternTokenBuilder().pos("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          token_regex("[(\\[]"),   # "... (ich meine Pfeil, nicht Raute) ..."
          token("ich"),
          token("meine"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("ein|das"),   # "ein leichter handhabbares Logo"
          token("leichter"),
          pos_regex("ADJ:NOM:SIN:NEU:GRU:IND"),
          pos("SUB:NOM:SIN:NEU")
        ],
        [
          token_regex("eine|die"),   # "eine leichter handhabbare Situation"
          token("leichter"),
          pos_regex("ADJ:NOM:SIN:FEM:GRU:IND"),
          pos("SUB:NOM:SIN:FEM")
        ],
        [
          token_regex("der|die|das"),   # "Der solchen Einsätzen gegenüber kritische Müller ..."
          token_regex("solche[mn]|(eben)?diese[mn]"),
          pos_regex("SUB:.*"),
          token("gegenüber"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*|EIG.*")
        ],
        [
          token_regex("des|der"),   # "des wenige Jahrzehnte zuvor verstorbenen Klostergründers"
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.*|EIG.*"),
          token("zuvor"),
          pos_regex("PA2:.*")
        ],
        [
          token("Ehre"),  # "Ehre, wem Ehre gebührt"
          token(","),
          token("wem"),
          token("Ehre")
        ],
        [
          token("in"),
          token("mehrerer"),
          token("Hinsicht")
        ],
        [
          token_regex("der|die|das"),   # "die [daraus] jedem zukommende Freiheit", "im Lichte der diesem zukommenden Repräsentationsaufgabe"
          PatternTokenBuilder().pos_regex("ADV:.*").min(0).build(),
          token_regex("jedem|(eben)?diesem"),
          pos_regex("PA1:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("spendet|macht"),  # "Macht dir das Hoffnung?"
          token_regex("mir|euch|dir|uns|ihnen"),
          token("das"),
          pos_regex("SUB:.*SIN.*")
        ],
        [
          token_regex("der|dem"),  # "Das Staatsoberhaupt ist der Verfassung zufolge der König."
          pos_regex("SUB:.*SIN.*"),
          token("zufolge"),
          token_regex("der|die|das"),
          pos_regex("SUB:.*SIN.*")
        ],
        [
          token_regex("Erkenntnis|Erkenntnissen"),  # "Als Auslöser könnte den ersten Erkenntnissen zufolge ein Specht in Betracht kommen."
          token("zufolge"),
          pos_regex("ART:.*")
        ],
        [
          # "die Anfang des 20. Jahrhunderts"
          token_regex("Anfang|Mitte|Ende"),
          token_regex("des"),
          token_regex("\\d+"),
          token_regex(".")
        ],
        [
          # "Das verlangt reifliche Überlegung.", "Die abnehmend aufwendige Gestaltung der Portale...",
          # "Eine ausreichend genaue Bestimmung"
          token_regex("(eben)?diese|der|die|das|ein|eine|dem|den|eine[ernm]|anderen?"),
          pos_regex("PA[12]:.*VER|ADV:TMP"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          # "Und den dritten wenige Tage später."
          token_regex("den|die"),
          token_regex("ersten?|zweiten?|dritten?|vierten?|fünften?|sechsten?|siebten?|achten?|neuten?|zehnten?|elften?|zwölften?"),
          pos_regex("ADJ:.*")
        ],
        [
          # "Die ersten Drei bekommen einen Preis." / "Die geheimen Sechs"
          token_regex("den|die"),
          token_regex(".+n"),
          cs_regex("Zwei|Drei|Vier|Fünf|Sechs|Sieben|Acht|Neun|Zehn|Elf|Zwölf|Zwanzig|Drei(ß|ss)ig|Vierzig|Fünzig|Hundert|Tausend")
        ],
        [
          # "sie zog allem anderen kindliche Spiele vor"
          token("allem"),
          token("anderen")
        ],
        [
          # "Von denen die meisten erst Ende des 19. Jahrhunderts"
          token("denen"),
          token("die"),
          token("meisten")
        ],
        [
          # "Viele weniger bekannte Vorschläge", "Seine überwiegend raschen Walzer ...",
          # "Keiner erwähnte eigene Überprüfungen"
          PatternTokenBuilder().pos_regex_with_string_exception("PRO:(IND|POS).*", "eine[nm]").build(),
          pos_regex("PA[12]:.*|ADV:TMP"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("der|die|manche[mr]"),  # "zog sich der Düsseldorfer schwere Verletzungen zu. "
          cs_regex("[A-ZÖÄÜ].*"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("einer?"),  # "Der als einer der ersten gängige Swingklischees vermied"
          token("der"),
          pos_regex("ADJ:GEN:.*")
        ],
        [
          token_regex("der|ein|eine[rnms]?|des|die"),  # "Ein lose zusammengewürfelter Haufen"
          token("lose"),
          token_regex("zusammengewürfelte[rnms]?")
        ],
        [
          token("den"),  # Als Ersatz für den kleiner gewordenen Spielplatz.
          pos_regex("ADJ:PRD:KOM"),
          pos_regex("ADJ:AKK:SIN.*"),
          pos_regex("SUB:AKK:SIN.*")
        ],
        [
          token("die"),  # Als Ersatz für die kleiner gewordenen Spielplätze.
          pos_regex("ADJ:PRD:KOM"),
          pos_regex("ADJ:AKK:PLU.*"),
          pos_regex("SUB:AKK:PLU.*")
        ],
        [
          # "Andere weniger bekannte Vorschläge", "Ich habe mir das gerade letzte Woche zugelegt."
          pos_regex("ART:.*|PRO:(POS|DEM|PER|IND).*"),
          token_regex("anscheinend|zunehmend|vorzugsweise|gekonnt|ausgeprägt|einige|solcher|solchen|typischerweise|hinreichend|nachgerade|vereinzelt|verheerend|hinreichend|zahlreiche|genauer|weiter|weniger|einzige|teilweise|anderen|sämtlicher|geringer|anderer|ausreichend|gerade|anhaltend|meisten"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          pos_regex("PRO:DEM:.*"),  # "Diese definiert einzelne Genres ..."
          PatternTokenBuilder().pos_regex_with_string_exception("VER:[23]:.*", "eine").build(),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("aufs|beides|welcher"),  # "aufs äußerste grausamer Krieg"
          pos_regex("ADJ:.*"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("eine[mr]"),  # "Dieses Bild stammt von einem lange Zeit unbekannten Maler."
          pos("ADV:TMP"),
          pos("ADV:TMP"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*SIN.*")
        ],
        [
          token_regex("zu"),  # "Sie gehörte einst zu den besten Afrikas."
          token_regex("den"),
          pos_regex("ADJ:.*"),
          pos_regex("EIG:GEN:.*")
        ],
        [
          token("von"),  # "von denen viele Open-Source-Software sind"
          token("denen"),
          token_regex("viele|etliche|alle|einige|manche|mehrere|wenige"),
          PatternTokenBuilder().pos_regex("SUB:.*SIN:.*").set_skip(-1).build(),
          token_regex("sind|seien|sein|waren|wären")
        ],
        [
          token("von"),  # "von denen die meisten Open-Source-Software sind"
          token("denen"),
          token("die"),
          token_regex("meisten|wenigsten|besten"),
          PatternTokenBuilder().pos_regex("SUB:.*SIN:.*").set_skip(-1).build(),
          token_regex("sind|seien|sein|waren|wären")
        ],
        [
          token_regex("die|der|den"),  # "die späten 50er Jahre"
          token_regex("frühen|späten"),  # "die späten 50er Jahre"
          token_regex("\\d+er"),  # "die späten 50er Jahre"
          token_regex("Jahren?")
        ],
        [
          token_regex("die|der|den"),  # "die wilden 90er"
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          token_regex("\\d+er")
        ],
        [
          pos_regex("ART:.*"),  # "ein ausgesprochen unattraktiver Dienstort"
          token("ausgesprochen"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("ein|eine|einen"),  # "bietet einen weniger genauen Zugriff"
          token("weniger"),
          pos_regex("ADJ:AKK:SIN:.*:GRU:.*"),
          pos_regex("SUB:.*SIN.*")
        ],
        [
          PatternTokenBuilder().cs_token("sein").match_inflected_forms().build(),
          token("das"),
          token_regex("Grund|Anlass|Auslöser|Ursache")
        ],
        [
          # "Vielleicht schreckt das Frauen ab"
          token_regex("schreckte?"),
          token("das"),
          pos_regex("SUB:.*")
        ],
        [
          token("eine"),
          token("Zeitlang")
        ],
        [
          token("für"),  # "..., wann und für wen Impfungen vorgenommen werden könnten."
          token("wen"),
          pos_regex("SUB:.*PLU.*")
        ],
        [
          token("der"),  # "der fließend Englisch sprechende Mitarbeiter"
          token_regex("flie(ß|ss)end"),
          token_regex(".*"),
          token("sprechende")
        ],
        [
          token("ein"),  # "Das wolkige und ein bisschen kühle Wetter..."
          token("bisschen"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*SIN.*")
        ],
        [
          token("ein"),  # "...um mal ein bisschen Einsichten zu bekommen" (ugs., aber okay)
          token("bisschen"),
          pos_regex("SUB:.*PLU.*")
        ],
        [
          token("dem"),  # "dem Abhilfe zu schaffen"
          token("Abhilfe"),
          PatternTokenBuilder().token("zu").min(0).build(),
          token("schaffen")
        ],
        [
          token("die"),  # "Die Müllers aus Hamburg"
          PatternTokenBuilder().pos_regex("EIG.*").token_regex(".*s").build()
        ],
        [
          token("die"),  # "Die Xi Jinping Ära ist …" -- should be 'Xi-Jinping-Ära', but don't detect here because of confusing error message
          pos_regex("EIG:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token("die"),  # "Die Xi Ära ist …"  -- should be 'Xi-Ära', but don't detect here because of confusing error message
          pos_regex("EIG:.*"),
          pos_regex("EIG:.*"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("ist|war|sei|wäre"),  # "war das Absicht"
          token("das"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          token_regex("Absicht")
        ],
        [
          token("das"),  # "in das damalige Reichenbach in Schlesien"
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          token_regex("Reichenbach|Albstadt|Arnstadt|Darmstadt|Duderstadt|Eberstadt|Eibelstadt|Erftstadt|Freudenstadt|Bergneustadt|" +
            "Neustadt|Burgkunstadt|Diemelstadt|Ebermannstadt|Eisenhüttenstadt|Friedrichstadt|Filderstadt|Freystadt|Florstadt|Glückstadt|" +
            "Grünstadt|Hallstadt|Halberstadt|Ingolstadt|Johanngeorgenstadt|Karlstadt")  # TODO: extend, https://de.wikipedia.org/wiki/Liste_der_St%C3%A4dte_in_Deutschland
        ],
        [
          token("das"),  # "Einwohnerzahl stieg um das Zweieinhalbfache"
          token_regex("(zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf).*fache")
        ],
        [
          token("ein"),  # "um ein vielfaches höhere Preise" -> Vielfaches, found by other rule
          token_regex("(viel|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf).*faches"),
          pos_regex("ADJ.*KOM.*")
        ],
        [
          token_regex("(eben)?diese"),  # "...damit diese ausreichend Sauerstoff geben."
          token_regex("genug|genügend|viel|hinreichend|ausreichend"),
          pos_regex("SUB:NOM:SIN:.*"),
          pos_regex("VER:.*")
        ],
        [
          token_regex("(eben)?diese[nmr]|andere[nm]"),  # "...um einer anderen genügend Platz zu schaffen"
          token_regex("genug|genügend|viel|hinreichend|ausreichend"),
          pos_regex("SUB:NOM:SIN:.*"),
          token("zu"),
          pos_regex("VER:.*")
        ],
        [
          pos_regex("VER:MOD:.*"),  # "Sollten zu diesem weitere Informationen benötigt werden, ..."
          token("zu"),
          token_regex("(eben)?diese[mnr]"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:NOM:PLU:.*"),
          pos_regex("PA2:.*")
        ],
        [
          token_regex("ein|das"),  # "Ein Geschenk, das Maßstäbe setzt" (#4043)
          pos("SUB:NOM:SIN:NEU"),
          token(","),
          token("das"),
          pos_regex("SUB:NOM:PLU:.*"),
          pos_regex("VER:3:.*")
        ],
        [
          token("uns"),  # "und wünschen uns allen Gesundheit."
          token("allen"),
          pos_regex("SUB:.*:SIN:.*")
        ],
        [
          token("Domain"),
          token("Name"),
          token_regex("Systems?")
        ],
        [
          token_regex("der|das|die"),
          PatternTokenBuilder().min(0).build(),
          token("Bad"),
          token("Homburger")
        ],
        [
          token_regex("der|die|das"),   # "Lieber jemanden, der einem Tipps/Hoffnung gibt." / "die 69er Revolte"
          cs_regex("einem|[0-9]+er"),
          pos_regex("SUB:.*")
        ],
        [
          token_regex("de[rs]"),   # "Die dauerhafte Abgrenzung des später Niedersachsen genannten Gebietes"
          pos_regex("ADJ:.*"),
          pos_regex("EIG:.*"),
          pos_regex("PA2:.*")
        ],
        [
          pos_regex("ART:.*FEM.*"),  # "Eine Lücke in der erneuerbare Energien eine sinnvolle Rolle spielen könnten"
          pos_regex("SUB:.*FEM.*"),
          token("in"),
          token("der")
        ],
        [
          token("einem"),
          token("kalte"),
          token("Schauer")
        ],
        [
          token_regex("die|der"),  # "die Querwild GmbH"
          token_regex(".*"),
          token("GmbH")
        ],
        [
          token("Die"),
          token_regex("Waltons|Einen")
        ],
        [
          token_regex("Gro(ß|ss)e[sn]?"),
          token_regex("(Bundes)?Verdienstkreuz(es)?")
        ],
        [  # "Adiponitril und Acetoncyanhydrin, beides Zwischenprodukte der Kunststoffproduktion."
          token_regex("[,–-]"),
          token("beides"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.*")
        ],
        [  # "In den Zwei Abhandlungen" (lowercase "zwei" is correct, but does not need to be found here)
          token_regex("Eins|Zwei|Drei|Vier|Fünf|Sechs|Sieben|Acht|Neun|Zehn|Elf|Zwölf"),
          pos_regex("SUB:.*")
        ],
        [  # "Eine Massengrenze, bis zu der Lithium nachgewiesen werden kann."
          token("bis"),
          token("zu"),
          token("der"),
          pos_regex("SUB:.*"),
          pos_regex("PA2:.*")
        ],
        [
          token_regex("jeder?"),
          token("Abitur")
        ],
        [
          token("Halle"),
          token("an"),
          token("der"),
          token("Saale")
        ],
        [  # "mehrere Tausend Menschen"
          token_regex("Dutzend|Hundert|Tausend"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.*")
        ],
        [  # "Besonders reizen mich Fahrräder.", "weil mich psychische Erkrankungen aus der Bahn werfen"
          token_regex("dich|mich"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.*")
        ],
        [  # "jenes Weges, den die Tausenden Juden 1945 ..."
          token("die"),
          token("Tausenden"),
          pos_regex("SUB:.*PLU.*")
        ],
        [  # misspelling "Format"
          token_regex("das|ein"),
          token("Formart")
        ],
        [  # "... andere erfreut Tennis."
          token_regex("andere"),
          pos_regex("VER:PA2.*"),
          pos_regex("SUB:.*")
        ],
        [  # "Das eine bedeutet Gefahr und das andere Gelegenheit."
          token_regex("der|die|das"),
          PatternTokenBuilder().token("eine").set_skip(-1).build(),
          token_regex("der|die|das"),
          token("andere"),
          pos_regex("SUB:.*")
        ],
        [  # "... größeren Bekanntheitsgrad in der Bevölkerung als jeder andere Kandidat vor ihm"
          token_regex("jede[mnrs]?"),
          token_regex("anderen?"),
          pos_regex("SUB:.*")
        ],
        [  # "... kein anderer Unrecht hat."
          token_regex("(eben)?diese[rs]?|keine?"),
          token_regex("anderer?"),
          pos_regex("SUB:.*")
        ],
        [  # "Toleranz ist der Verdacht, dass der andere Recht hat."
          token_regex("der|die|das"),
          token_regex("anderen?"),
          token("Recht"),
          PatternTokenBuilder().cs_token("haben").match_inflected_forms().build()
        ],
        [  # "als einziger ein für die anderen unsichtbares Wunder zu sehen."
          token("für"),
          token_regex("den|die"),
          token("anderen")
        ],
        [  # "Wer auf eines anderen Schuhe wartet...", "...Auge darauf haben, dass keine der anderen Abbruch tue"
          token_regex("der|eine[sr]"),
          token("anderen"),
          pos_regex("SUB:.*")
        ],
        [  # "wenn andere anderer Meinung sind"
          token("andere"),
          token_regex("anderer?"),
          pos_regex("SUB:.*")
        ],
        [  # "Hat ein Schutzgut gegenüber den anderen Priorität?"
          token("gegenüber"),
          token("den"),
          token("anderen"),
          pos_regex("SUB:.*")
        ],
        [  # "... ist des anderen Freiheitskämpfer", "... die anderen Volleyball"
          token_regex("des|die"),
          token("anderen"),
          pos_regex("SUB:.*")
        ],
        [  # "Ein Esel schimpft den anderen Langohr."
          pos_regex("VER:3:.*"),
          token_regex("den|die|das"),
          token_regex("anderen?"),
          pos_regex("SUB:.*")
        ],
        [  # "... eine bessere Behandlung als andere Gefangene."
          token("als"),
          token("andere"),
          pos_regex("SUB:.*PLU.*")
        ],
        [  # "was sein Klient für ein Mensch sei",
          # "Mir wird nicht ganz klar, was das bei 1:58 für ein Akkord ist."
          PatternTokenBuilder().token("was").set_skip(5).build(),
          token("für"),
          token("ein"),
          PatternTokenBuilder().pos_regex("ADJ:.*(MAS|NEU).*").min(0).build(),
          pos_regex("SUB:.*:(MAS|NEU).*")
        ],
        [  # "was sein Klient für ein Mensch sei",
          # "Mir wird nicht ganz klar, was das bei 1:58 für ein Akkord ist."
          PatternTokenBuilder().token("was").set_skip(5).build(),
          token("für"),
          token("eine"),
          PatternTokenBuilder().pos_regex("ADJ:.*FEM.*").min(0).build(),
          pos_regex("SUB:.*:FEM.*")
        ],
        [
          # "Wir zeigen die Gründe auf, wieso noch nicht jeder solche Anschlüsse hat."
          token_regex("jede[rsm]?"),
          token_regex("(eben)?solche[rsm]?"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          token_regex("als|um"),
          token_regex("(eben)?solche")
        ],
        [
          # "Solch frivolen Gedanken wollen wir gar nicht erst nachgehen."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+en?"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          # "Solch frivolen ungewohnten Gedanken wollen wir gar nicht erst nachgehen."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+en?"),
          cs_regex("[a-zäöüß]+en?"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          # "Er erwartete solch aggressives Verhalten."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+e[nms]"),
          pos_regex("SUB.*SIN.*NEU.*")
        ],
        [
          # "Er erwartete solch aggressives ungewohntes Verhalten."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+e[nms]"),
          cs_regex("[a-zäöüß]+e[nms]"),
          pos_regex("SUB.*SIN.*NEU.*")
        ],
        [
          # "Ein solch schöner Tisch."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+e[nmr]"),
          pos_regex("SUB.*SIN.*MAS.*")
        ],
        [
          # "Ein solch schöner neuer Tisch."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+e[nmr]"),
          cs_regex("[a-zäöüß]+e[nmr]"),
          pos_regex("SUB.*SIN.*MAS.*")
        ],
        [
          # "Eine solch schöne Frau."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+e[rn]?"),
          pos_regex("SUB.*SIN.*FEM.*")
        ],
        [
          # "Eine solch schöne hübsche Frau."
          token_regex("(eben)?solch"),
          cs_regex("[a-zäöüß]+e[rn]?"),
          cs_regex("[a-zäöüß]+e[rn]?"),
          pos_regex("SUB.*SIN.*FEM.*")
        ],
        [
          # "Wenn ein Tiger einen Menschen tötet, ist das Grausamkeit."
          token(","),
          PatternTokenBuilder().token_regex("dann|so").min(0).build(),
          cs_regex("ist|wäre?"),
          cs_regex("das(jenige)?|(der|die)jenige"),
          pos_regex("SUB:NOM.*")
        ],
        [
          # "Sind im Molekül mehrere Aminogruppen vertreten, so bestimmt dasjenige Kohlenstoff"
          PatternTokenBuilder().token_regex("wenn|falls|sobald").match_inflected_forms().set_skip(-1).build(),
          token(","),
          PatternTokenBuilder().token_regex("dann|so").min(0).build(),
          token("bestimmt"),
          cs_regex("das(jenige)?"),
          pos_regex("SUB:NOM.*")
        ],
        [
          # "das Bände spricht"
          token("das"),
          token("Bände"),
          cs_regex("spricht|sprach|sprechen")
        ],
        [
          token_regex("des|der|den|dem|die"),
          cs_token("Kommando"),
          cs_regex("Spezialkräften?")
        ],
        [
          token("auf"),
          cs_regex("die|den|das"),
          cs_token("Verlass"),
          cs_regex("ist|war|wäre?")
        ],
        [
          token("auf"),
          cs_regex("die|den|das"),
          cs_token("Verlass"),
          cs_token("zu"),
          cs_token("sein")
        ],
        [
          # kannst du mal schauen, ob das zahlende Kunden sind?
          token("ob"),
          token("das"),
          cs_regex(".+e"),
          pos_regex("SUB:NOM:PLU.*"),
          cs_regex("sind|waren")
        ],
        [
          # Er fragte, ob das Frauen auch so toll finden.
          token("ob"),
          token("das"),
          token("Frauen")
        ],
        [
          # Ich lese das Korrektur.
          cs_regex("l[ea]sen?|liest|l[ea]st?"),
          token("das"),
          token("Korrektur")
        ],
        [
          # Ich habe das Korrektur gelesen.
          cs_regex("habe?n?|ha[sb]?t"),
          token("das"),
          token("Korrektur"),
          token("gelesen")
        ],
        [
          # In einer entzückend chaotischen Partie zwischen A und B kam es zum Unentschieden.
          pos_regex("ART.*"),
          pos_regex("VER:PA[12]"),
          pos_regex("ADJ.*"),
          pos_regex("SUB.*")
        ],
        [
          # Er lässt einen Visionen haben.
          cs_regex("lässt|lassen|ließ|ließen"),
          token("einen"),
          pos_regex("SUB:AKK.*"),
          pos_regex("VER:INF.*")
        ],
        [
          # Eine Initialzündung war der Bericht „Grenzen des Wachstums“ des Club of Rome, ...
          token("des"),
          token("Club"),
          token("of"),
          token("Rome")
        ],
        [
          # Entwickelt wurde das Session Initiation Protocol von der IETF.
          cs_regex("das|ein"),
          token("Session"),
          token("Initiation"),
          token("Protocol")
        ],
        [
          # Ähnliches gilt im Norden der Insel für die George-Washington-Bridge.
          token("die"),
          token("George-Washington-Bridge")
        ],
        [
          # Wie kann ich das zu Wege bringen?
          token("das"),
          token("zu"),
          token("Wege")
        ],
        [
          # Erst in der zweiten Hälfte des 4. Jahrhunderts ging die alte aristokratische Ordnung durch Machtkämpfe zwischen diesen zu Grunde.
          cs_regex("diese[mnrs]?"),
          token("zu"),
          token("Grunde")
        ],
        [
          # acht Passionsszenen Christi sowie das Jüngste Gericht
          cs_regex("das|dem|des"),
          cs_regex("Jüngsten?"),
          cs_regex("Gerichts?")
        ],
        [
          # Großes Konzert in der Kampnagel Kulturfabrik
          token("Kampnagel"),
          token("Kulturfabrik")
        ],
        [
          # Es war Teil von Madonnas Performance während des Super Bowls 2012.
          token("Super"),
          cs_regex("Bowls?")
        ],
        [
          # Ein Teil der Communauté Française schloss sich zur Westafrikanischen Zollunion (UDAO) zusammen.
          cs_regex("Westafrikanischen?"),
          token("Zollunion")
        ],
        [
          # Die Zeit begann mit der Gründung der englischen Football Association.
          cs_regex("[Ee]nglischen?"),
          token("Football"),
          token("Assosiation")
        ],
        [
          # die neu geschaffene Position des Head of Men’s Tennis
          token("des"),
          token("Head"),
          token("of")
        ]
      ]


# AgreementRuleAntiPatterns2.ANTI_PATTERNS
def anti_patterns_2():
    return [
        [
          token("Eurovision"),
          token("Song"),
          token("Contest")
        ],
        [
          token("Account"),
          token_regex("Managers?")
        ],
        [
          token("Wohnungsbau"),
          token("Aalen")
        ],
        [
          token("Display"),
          token_regex("Ads?|Advertising")
        ],
        [
          token("Private"),
          token_regex("Equitys?|Clouds?")
        ],
        [
          token("Personal"),
          token_regex("Agents?|Computers?|Data|Firewalls?")
        ],
        [
          token("Junge"),
          token_regex("Union|Freiheit|Welt|Europäische|Alternative|Volkspartei|Akademie")
        ],
        [  # "Das Holocaust Memorial Museum."
          pos_regex("ART:.+"),
          pos_regex("SUB:.+"),
          pos("UNKNOWN")
        ],
        [  # "Er fragte, ob das Spaß macht."
          cs_token(","),
          pos_regex("KON:UNT|ADV:INR"),
          cs_token("das"),
          pos_regex("SUB:.+"),
          pos_regex("VER:3:SIN.*")
        ],
        [  # "Es gibt viele solcher Bilder"
          token_regex("viele|etliche|wenige|einige|mehrere"),
          cs_token("solcher"),
          pos_regex("SUB:GEN:PLU:.*")
        ],
        [  # "der französischen First Lady"
          token_regex("[dD](ie|er)"),
          cs_token("First"),
          cs_token("Lady")
        ],
        [  # "der französischen First Lady"
          token_regex("[dD](ie|er)"),
          pos_regex("ADJ:.*"),
          cs_token("First"),
          cs_token("Lady")
        ],
        [  # "der Super Nintendo"
          token_regex("[dD](ie|er)"),
          cs_token("Super"),
          cs_token("Nintendo")
        ],
        [  # Firmenname
          cs_token("Pizza"),
          cs_token("Hut")
        ],
        [  # Texas und New Mexico, beides spanische Kolonien, sind
          cs_token(","),
          cs_token("beides"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:PLU.+").min(0).build(),
          pos_regex("SUB:NOM:PLU.+"),
          pos("PKT")
        ],
        [    # Beides Teenager mit verrückten Ideen
          pos("SENT_START"),
          cs_token("Beides"),
          pos_regex("SUB:NOM:PLU.+")
        ],
        [
          token_regex("[dD]e[rn]"),
          cs_token("Gold"),
          cs_token("Cup")
        ],
        [
          token("das"),
          token_regex("viele|wenige"),
          pos_regex("SUB:.*")
        ],
        [
          token("das"),
          pos_regex("SUB:.+"),
          PatternTokenBuilder().cs_token("dauern").match_inflected_forms().build()
        ],
        [  # "Er verspricht allen/niemandem/jedem hohe Gewinne."
          token_regex("allen|(nieman|je(man)?)dem"),
          pos_regex("ADJ:AKK:PLU:.*"),
          pos_regex("SUB:AKK:PLU:.*")
        ],
        [  # "Er verspricht allen/niemandem/jedem Gewinne von über 15 Prozent."
          token_regex("allen|(nieman|je(man)?)dem"),
          pos_regex("SUB:AKK:PLU:.*")
        ],
        [  # "Für ihn ist das Alltag." / "Für die Religiösen ist das Blasphemie und führt zu Aufständen."
          PatternTokenBuilder().pos_regex("PRP:.+|ADV:MOD").set_skip(2).build(),
          PatternTokenBuilder().token("sein").match_inflected_forms().build(),
          cs_token("das"),
          pos_regex("SUB:NOM:.*"),
          pos_regex("PKT|SENT_END|KON.*")
        ],
        [  # "Meistens sind das faktenfreie Behauptungen."
          token_regex("sind|waren|wären"),
          cs_token("das"),
          pos_regex("ADJ:NOM:PLU.*"),
          pos_regex("SUB:NOM:PLU.*"),
          pos_regex("PKT|KON.*")
        ],
        [  # "Meistens ist das reine Formsache."
          token_regex("ist|war|wär"),
          cs_token("das"),
          pos_regex("ADJ:NOM:SIN.*"),
          pos_regex("SUB:NOM:SIN.*"),
          pos_regex("PKT|KON.*")
        ],
        [  # "Aber ansonsten ist das erste Sahne"
          PatternTokenBuilder().token("sein").match_inflected_forms().build(),
          cs_token("das"),
          cs_token("erste"),
          cs_token("Sahne")
        ],
        [  # "Sie sagte, dass das Rache bedeuten würden", "Sie werden merken, dass das echte Nutzer sind."
          pos("KON:UNT"),
          cs_token("das"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:.+"),
          PatternTokenBuilder().token_regex("bedeuten|sein").match_inflected_forms().build()
        ],
        [  # "Sie fragte, ob das wirklich Rache bedeuten würde"
          pos("KON:UNT"),
          cs_token("das"),
          pos("ADV:MOD"),
          pos_regex("SUB:.+"),
          PatternTokenBuilder().token_regex("bedeuten|sein").match_inflected_forms().build()
        ],
        [  # "Karl sagte, dass sie niemandem Bescheid gegeben habe."
          PatternTokenBuilder().token("niemand").match_inflected_forms().build(),
          pos_regex("SUB:.+")
        ],
        [
          token("alles"),
          cs_token("Walzer")
        ],
        [  # "ei der Daus"
          cs_token("der"),
          cs_token("Daus")
        ],
        [  # "Das Orange ist meine Lieblingsfarbe"
          pos_regex("PRO:...:...:SIN:NEU.*"),
          cs_token("Orange")
        ],
        [  # "Dieses rötliche Orange gefällt mir am besten"
          pos_regex("PRO:...:...:SIN:NEU.*"),
          pos_regex("ADJ:.+"),
          cs_token("Orange")
        ],
        [
          cs_token("dem"),
          PatternTokenBuilder().cs_token("Achtung").set_skip(1).build(),
          PatternTokenBuilder().cs_token("schenken").match_inflected_forms().build()
        ],
        [
          PatternTokenBuilder().cs_token("schenken").match_inflected_forms().build(),
          cs_token("dem"),
          cs_token("Achtung")
        ],
        [
          cs_token("dem"),
          PatternTokenBuilder().cs_token("Rechnung").set_skip(1).build(),
          PatternTokenBuilder().cs_token("tragen").match_inflected_forms().build()
        ],
        [
          PatternTokenBuilder().cs_token("tragen").match_inflected_forms().build(),
          cs_token("dem"),
          cs_token("Rechnung")
        ],
        [
          cs_token("zum"),
          cs_token("einen"),
          pos_regex("(ADJ|PA[12]):.+")
        ],
        [
          token("auf"),
          cs_token("die"),
          cs_token("Lauer")
        ],
        [
          token_regex("(eben)?dieser"),
          cs_token("eine"),
          pos("SUB:NOM:SIN:MAS")
        ],
        [
          token("das"),
          pos_regex("SUB:DAT:.+"),
          token("vorbehalten")
        ],
        [  # Wenn hier einer Geld hat, dann ich.
          PatternTokenBuilder().token("wenn").set_skip(1).build(),
          cs_token("einer"),
          pos_regex("SUB:AKK:.+"),
          pos_regex("VER:(MOD:)?3:SIN:.+"),
          cs_token(",")
        ],
        [  # Es ist nicht eines jeden Bestimmung
          token_regex("eine[rs]"),
          token_regex("jed(wed)?en")
        ],
        [  # Ich vertraue auf die Meinen.
          token("die"),
          token_regex("[MDS]einen")
        ],
        [  # Sie ist über die Maßen schön.
          cs_token("über"),
          cs_token("die"),
          token_regex("Ma(ß|ss)en")
        ],
        [  # Was nützt einem Gesundheit, wenn man sonst ein Idiot ist?
          token("was"),
          PatternTokenBuilder().cs_token("nützen").match_inflected_forms().build(),
          cs_token("einem"),
          pos_regex("SUB:NOM:.+")
        ],
        [  # Auch das hat sein Gutes.
          PatternTokenBuilder().cs_token("haben").match_inflected_forms().build(),
          cs_token("sein"),
          cs_token("Gutes")
        ],
        [  # Auch wenn es sein Gutes hatte.
          cs_token("Gutes"),
          PatternTokenBuilder().token_regex("haben|tun").match_inflected_forms().build()
        ],
        [
          token_regex("(eben)?dieser"),
          cs_token("einen"),
          pos("SUB:DAT:SIN:FEM")
        ],
        [
          cs_token("Rede"),
          cs_token("und"),
          cs_token("Antwort")
        ],
        [
          pos_regex("ABK:.+:SUB")
        ],
        [
          token_regex("(all|je(d|glich))en"),
          cs_token("Reiz")
        ],
        [
          token_regex("wieso|ob|warum|w[ae]nn"),
          token("das"),
          token_regex("sinn|mehrwert"),
          token_regex("macht|ergibt|stiftet|bringt")
        ],
        [
          token_regex("hat|hätte|kann|wird|dürfte|muss|soll(te)?|könnte|müsste|würde"),
          token("das"),
          token("Konsequenzen")
        ],
        [
          PatternTokenBuilder().pos_regex("VER:.*[1-3]:.+").set_skip(1).build(),
          cs_token("vermehrt")
        ],
        [  # In den Ruhr Nachrichten
          cs_token("Ruhr"),
          cs_token("Nachrichten")
        ],
        [
          cs_token("Joint"),
          token_regex("Ventures?|Cares?")
        ],
        [
          cs_token("Premier"),
          cs_token("League")
        ],
        [
          # Common job title
          cs_token("Software"),
          token_regex("Engineers?|Developer[sn]?|(Back|Front)end")
        ],
        [
          cs_token("Mark"),
          pos_regex("EIG:.*")
        ],
        [
          cs_token("Sales"),
          token_regex("Agent")
        ],
        [
          cs_token("Total"),
          token_regex("Tankstellen?")
        ],
        [
          pos_regex("ART:.*"),
          cs_token("Bund"),
          cs_token("Naturschutz")
        ],
        [
          cs_token("Real"),
          token_regex("Madrid|Valladolid|Mallorca")
        ],
        [  # Eng.
          cs_token("Real"),
          pos("UNKNOWN")
        ],
        [
          cs_token("Hammer"),
          token_regex("Stra(ß|ss)e")
        ],
        [  # https://www.duden.de/rechtschreibung/Personal_Trainer
          cs_token("Personal"),
          token_regex("Trainers?")
        ],
        [  # Ich wollte erstmal allen Hallo sagen.
          token("Hallo"),
          PatternTokenBuilder().cs_token("sagen").match_inflected_forms().build()
        ],
        [  # "ob die Deutsch sprechen"
          token("die"),
          token_regex("Deutsch|Englisch|Spanisch|Französisch|Russisch|Polnisch|Holländisch|Niederländisch|Portugiesisch"),
          PatternTokenBuilder().cs_token("sprechen").match_inflected_forms().build()
        ],
        [  # "Ein Trainer, der zum einen Fußballspiele sehr gut lesen und analysieren kann"
          token("zum"),
          token("einen"),
          pos_regex("SUB:.*")
        ],
        [  # https://www.duden.de/suchen/dudenonline/Fake%20News
          cs_token("Fake"),
          pos_regex("News")
        ],
        [
          token_regex("Steinberg|Park"),
          cs_token("Apotheke")
        ],
        [
          cs_token("IT"),
          cs_token("Finanzmagazin")
        ],
        [
          cs_token("Golden"),
          cs_token("Gate")
        ],
        [  # Vielen Dank fürs Bescheid geben
          token("fürs"),
          token("Bescheid"),
          token_regex("geben|sagen")
        ],
        [  # "Los" ist ein deutsches Substantiv
          token("Los"),
          token_regex("Angeles|Zetas")
        ],
        [  # https://www.autozeitung.de/
          cs_token("Auto"),
          cs_token("Zeitung")
        ],
        [  # "Das letzte Mal war das Ende der..."
          cs_token("Mal"),
          PatternTokenBuilder().token("sein").match_inflected_forms().build(),
          cs_token("das"),
          pos_regex("SUB:NOM:.*")
        ],
        [
          cs_token("FC"),  # Die FC Bayern München Hymne (Vorschlag macht keinen Sinn "FC-Bayern")
          cs_token("Bayern")
        ],
        [
          cs_token("Super"),
          cs_token("Mario")
        ],
        [
          token_regex(".+"),
          token_regex(".+"),
          cs_token("Toyota"),
          cs_token("Motor"),
          token_regex("Corp(oration)?|Company")
        ],
        [
          token_regex(".+"),
          token_regex(".+"),
          cs_token("Metropolitan"),
          token_regex("Police|Community|City|Books")
        ],
        [
          token_regex("Office|Microsoft"),
          cs_token("365")
        ],
        [
          cs_token("Prinz"),
          token_regex("Charles|William")
        ],
        [
          token(":"),
          cs_token("D")
        ],
        [
          token_regex("ist|war(en)?|sind|wird|werden"),
          cs_token("das"),
          cs_token("reine"),
          pos_regex("SUB:NOM:.*")
        ],
        [  # Eine Android Watch
          cs_token("Android"),
          token_regex("Wear|Watch(es)?|Smartwatch(es)?|OS")
        ],
        [  # "Bitte öffnen Sie die CAD.pdf"
          token_regex("\\w+"),
          PatternTokenBuilder().token(".").set_is_white_space_before(False).build(),
          PatternTokenBuilder().token_regex("pdf|zip|jpe?g|gif|png|rar|mp[34]|mpe?g|avi|docx?|xlsx?|pptx?|html?").set_is_white_space_before(False).build()
        ],
        [  # "Ich mache eine Ausbildung zur Junior Digital Marketing Managerin"
          PatternTokenBuilder().token_regex("Junior|Senior|Account").set_skip(3).build(),
          token_regex("Manager[ns]?|Managerin(nen)?|Developer(in)?")
        ],
        [
          PatternTokenBuilder().token_regex("Junior|Senior").build(),
          token("Software"),
          token_regex("Engineers?|Architects?|Managers?|Directors?")
        ],
        [
          PatternTokenBuilder().token_regex("Junior|Senior").build(),
          token("Engineering"),
          token_regex("Manager[ns]?|Directors?")
        ],
        [  # "Angel" is tagged like the "Die Angel" for fishing
          cs_token("Business"),
          token_regex("Angel[ns]?|Cases?")
        ],
        [  # "des Manager Magazins"
          cs_token("Manager"),
          token_regex("Magazins?")
        ],
        [
          cs_token("Junior"),
          token_regex("Suite[sn]?")
        ],
        [  # Deine Abt.
          token_regex("die|eine|unsere|meine|ihre|eure|(eben)?diese|seine|deine"),
          cs_token("Abt"),
          token("."),
          token_regex(".+")
        ],
        [
          token_regex(".+"),
          token_regex(".+"),
          token_regex("Customer|User"),
          token_regex("Journeys?|Service")
        ],
        [
          token_regex(".+"),
          token_regex(".+"),
          token("Hall"),
          token("of"),
          token("Fame")
        ],
        [  # Wir trinken ein kühles Blondes
          token("kühles"),
          token("Blondes")
        ],
        [
          token_regex("Vitamin|Buchstabe"),
          token_regex("D|B[1-9]?|B12")
        ],
        [  # "Bei uns im Krankenhaus betrifft das Operationssäle."
          PatternTokenBuilder().token("betreffen").match_inflected_forms().build(),
          cs_token("das"),
          pos_regex("SUB:AKK:PLU:.*")
        ],
        [  # "Was für ein Narr"
          token("was"),
          cs_token("für"),
          cs_token("ein"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:(MAS|NEU).*").min(0).build(),
          pos_regex("SUB:NOM:SIN:(MAS|NEU)")
        ],
        [  # "Was für ein liebe Frau"
          token("was"),
          cs_token("für"),
          cs_token("eine"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:FEM.*").min(0).build(),
          pos("SUB:NOM:SIN:FEM")
        ],
        [  # "Was war ich für ein Narr"
          token("was"),
          PatternTokenBuilder().token("sein").match_inflected_forms().set_skip(2).build(),
          cs_token("für"),
          cs_token("ein"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:(MAS|NEU).*").min(0).build(),
          pos_regex("SUB:NOM:SIN:(MAS|NEU)")
        ],
        [  # "Was war sie nur für eine dumme Person"
          token("was"),
          PatternTokenBuilder().token("sein").match_inflected_forms().set_skip(2).build(),
          cs_token("für"),
          cs_token("eine"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:FEM.*").min(0).build(),
          pos("SUB:NOM:SIN:FEM")
        ],
        [  # "Wie viele Paar Schuhe braucht er?"
          cs_regex("vielen?|etliche|wenigen?|einigen?"),
          cs_token("Paar"),
          pos_regex("SUB:NOM:PLU:...")
        ],
        [  # Dann macht das Sinn.
          cs_regex("machte?|ergibt|ergab|stiftete?"),
          cs_token("das"),
          cs_token("Sinn")
        ],
        [  # Mir machte das Spaß
          cs_regex("machte?"),
          cs_token("das"),
          cs_regex("Spa(ß|ss)|Freude")
        ],
        [  # Das sind beides Lichtschalter; Wasser und Luft sind beides Fluide.
          cs_regex("sind|waren"),
          cs_token("beides"),
          PatternTokenBuilder().pos_regex("ADJ:.*").min(0).build(),
          pos_regex("SUB:NOM:PLU:.*")
        ],
        [  # Heinrich von der Haar (https://de.wikipedia.org/wiki/Heinrich_von_der_Haar)
          token("Heinrich"),
          token("von"),
          token("der"),
          cs_regex("Haars?")
        ],
        [
          token("Präsident"),
          token("Xi")
        ],
        [
          token("Porsche"),
          token("Museum")
        ],
        [
          token("Auto"),
          token("Club"),
          token("Europa")
        ],
        [
          token("Queen"),
          pos_regex("EIG:.*")
        ],
        [
          token("King"),
          pos_regex("EIG:.*")
        ],
        [  # des Sturm und Drangs
          token("des"),
          token("Sturm"),
          token("und"),
          cs_regex("Drangs?")
        ],
        [  # die Funke Mediengruppe
          token("die"),
          token("Funke"),
          token("Mediengruppe")
        ],
        [
          PatternTokenBuilder().cs_token("meinen").match_inflected_forms().set_skip(3).build(),
          cs_regex("das|(eben)?dies(es)?"),
          PatternTokenBuilder().token("wirklich").min(0).build(),
          token("Ernst")
        ],
        [
          PatternTokenBuilder().cs_token("nehmen").match_inflected_forms().set_skip(3).build(),
          cs_regex("das|(eben)?dies(es)?"),
          PatternTokenBuilder().token("wirklich").min(0).build(),
          token("Ernst")
        ],
        [
          # ... dann spart das Zeit und Geld.
          PatternTokenBuilder().cs_token("sparen").match_inflected_forms().set_skip(3).build(),
          cs_regex("das|(eben)?dies(es)?"),
          token("Zeit"),
          token("und"),
          cs_regex("Geld|Nerven")
        ],
        [
          cs_regex("das|es|(eben)?dies"),
          cs_regex("bedeutete?"),
          cs_regex("Krieg|Ärger")
        ],
        [
          # In der aktuellen Niedrigzinsphase bedeutet das sehr geringe Zinsen, die aber deutlich ansteigen können.
          token_regex("bedeutete?"),
          cs_regex("das|(eben)?dies")
        ],
        [
          # Bietet das Vorteile, außer dass es "intelligent" wirkt?
          token_regex("bietete?"),
          cs_regex("das|(eben)?dies"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          # Bietet das große Vorteile, außer dass es "intelligent" wirkt?
          cs_regex("bietete?"),
          cs_regex("das|(eben)?dies"),
          pos_regex("ADJ.*PLU.*"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          # Bietet das sehr große Vorteile, außer dass es "intelligent" wirkt?
          cs_regex("bietete?"),
          cs_regex("das|(eben)?dies"),
          pos_regex("ADV.*"),
          pos_regex("ADJ.*PLU.*"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          cs_regex("das|es|(eben)?dies"),
          cs_regex("weite"),
          token("Teile")
        ],
        [
          token("hat"),
          token("das"),
          cs_regex("Einfluss|Auswirkungen"),
          cs_regex("auf|darauf")
        ],
        [  # ein Auto, das schnell fährt und in **das Menschen** gerne einsteigen
          pos_regex("VER.*[123].*"),
          token_regex("und|oder|aber"),
          PatternTokenBuilder().pos_regex("PRP.*").min(0).build(),
          token_regex("der|die|das|dem|den")  # nicht 'des' weil sonst nicht gefunden: "Wir haben das Abo beendet und des Betrag erstattet."
        ],
        [  # weil man oft bei **anderen schreckliches Essen** vorgesetzt bekommt
          token_regex("bei|zum"),
          token("anderen"),
          pos_regex("ADJ.*"),
          pos_regex("SUB.*")
        ],
        [  # dass jeder LanguageTool benutzen sollte
          token("jeder"),
          pos_regex("SUB:(AKK|DAT).*"),
          pos_regex("VER.*")
        ],
        [  # der fließend Französisch sprechende Trudeau
          pos_regex("(ART|PRO:DEM).*"),
          pos_regex("ADV.*"),
          pos_regex("SUB.*"),
          pos_regex("PA[12].*")
        ],
        [  # Spricht dieser fließend Französisch
          pos_regex("VER.*[123].*"),
          pos_regex("(ART|PRO:DEM).*"),
          pos_regex("ADV.*"),
          pos_regex("SUB.*")
        ],
        [  # Der Deutsch Langhaar ist ein mittelgroßer Jagdhund
          token("Deutsch"),
          token("Langhaar")
        ],
        [  # Einige nennen das
          PatternTokenBuilder().cs_token("nennen").match_inflected_forms().build(),
          token("das"),
          pos_regex("SUB:NOM:SIN:(FEM|MAS)")
        ],
        [  # Das ist bestimmt kein Made in Germany
          cs_token("Made"),
          cs_token("in"),
          cs_token("Germany")
        ],
        [  # Des Plan de XXX
          cs_regex("[A-Z].+"),
          cs_regex("del?"),
          cs_regex("[A-Z].+")
        ],
        [  # Des Plan de XXX
          cs_regex("[A-Z].+"),
          cs_token("de"),
          token_regex("l[ao]s?"),
          cs_regex("[A-Z].+")
        ]
      ]


# AgreementRuleAntiPatterns3.ANTI_PATTERNS
def anti_patterns_3():
    return [
        [
          # "Mit dem Tod von Rabin und der kurze Zeit später erfolgenden Wahl..."
          token("der"),
          token("kurze"),
          token("Zeit"),
          token_regex("später|früher|darauf|danach|vorher")
        ],
        [
          # "Was in aller Welt soll das denn für ein Satz sein?"
          token("was"),
          token("in"),
          token("aller"),
          PatternTokenBuilder().token("Welt").set_skip(4).build(),
          token("für"),
          token("ein"),
          PatternTokenBuilder().pos_regex("ADJ:.*(MAS|NEU).*").min(0).build(),
          pos_regex("SUB:.*:(MAS|NEU).*")
        ],
        [
          # "Was in aller Welt soll das denn für ein Satz sein?"
          token("was"),
          token("in"),
          token("aller"),
          PatternTokenBuilder().token("Welt").set_skip(4).build(),
          token("für"),
          token("eine"),
          PatternTokenBuilder().pos_regex("ADJ:.*FEM.*").min(0).build(),
          pos_regex("SUB:.*:FEM.*")
        ],
        [  # "wird das schwere Konsequenzen haben"
          token("das"),
          token("schwere"),
          token("Konsequenzen")
        ],
        [  # "der Chaos Computer Club"
          token("der"),
          token("Chaos"),
          token("Computer"),
          token("Club")
        ],
        [  # "der Echo Show" (Amazon device)
          token("Echo"),
          token_regex("Show|Dot")
        ],
        [  # "In einem App Store"
          token_regex("App|Play"),
          token("Store")
        ],
        [
          token("Knecht"),
          token("Ruprecht")
        ],
        [  # "in dem einen Jahr"
          token("dem"),
          token("einen"),
          pos("SUB:NOM:SIN:NEU")
        ],
        [  # -> "Kaffee" - handled by spell checker
          token_regex("eine[sn]"),
          token_regex("Kaffes?")
        ],
        [  # "Dies erlaubt Forschern, ..." aber auch "Dieses versuchten Mathematiker ..."
          pos("SENT_START"),
          pos_regex("PRO:DEM:.+"),
          pos_regex("VER:3:.+"),
          pos_regex("SUB:(DAT|NOM):PLU.*")
        ],
        [  # "Das verkündete Premierminister Miller"
          pos("SENT_START"),
          token("das"),
          token("verkündete"),
          pos_regex("SUB:.*")
        ],
        [  # "Das verkündete Premierminister Miller"
          token("wegen"),
          token("der"),
          token("vielen"),
          token("Arbeit")
        ],
        [  # "in denen Energie steckt"
          PatternTokenBuilder().pos_regex("SENT_START|VER:AUX:[123].+").negate().build(),
          pos_regex("PRP:.+"),
          PatternTokenBuilder().pos_regex("PRO:DEM:(DAT|AKK).+").token_regex("der|dies").match_inflected_forms().build(),
          pos_regex("SUB:...:PLU.*")
        ],
        [  # "ein für mich sehr peinlicher Termin"
          token("für"),
          token("mich"),
          pos("ADV:MOD"),
          pos_regex("ADJ:.*"),
          pos_regex("SUB:.*")
        ],
        [  # "für den Mailänder Bischofssitz"
          pos_regex("PRP:.+"),
          PatternTokenBuilder().pos_regex("PRO:DEM:(DAT|AKK).+").token_regex("der|dies").match_inflected_forms().build(),
          cs_regex("[A-ZÄÖÜ].+er"),
          PatternTokenBuilder().pos_regex("SUB.+").build()
        ],
        [
          pos_regex("PRP:.+"),
          pos_regex("PRO:DEM:(DAT|AKK).+"),
          pos_regex("PA2:(DAT|AKK).+"),
          pos_regex("SUB:(DAT|AKK):.*")
        ],
        [  # Artikel 34 setzt dem bestimmte Formen gleich
          pos_regex("VER:.*[123].*"),
          pos_regex("PRO:DEM:DAT:SIN:NEU.*"),
          pos_regex("PA2:AKK:PLU.+"),
          pos_regex("SUB:AKK:PLU.+")
        ],
        [  # Er stellt dieses interessierten Domänen zur Verfügung
          pos_regex("VER:.*[123].*"),
          pos_regex("PRO:DEM:AKK:SIN:NEU.*"),
          pos_regex("PA2:DAT:PLU.+"),
          pos_regex("SUB:DAT:PLU.+")
        ],
        [
          pos("ADJ:PRD:KOM"),
          cs_token("als"),
          token_regex("d(er|ie|as)"),
          pos_regex(".+:GEN:.+")
        ],
        [  # "Wir bereinigen das nächsten Dienstag."
          pos_regex("VER:.*|UNKNOWN"),
          token("das"),
          cs_regex("(über)?nächste[ns]?|kommende[ns]?|(vor)?letzten"),
          cs_regex(MONTH_NAMES_REGEX + "|Montag|D(ien|onner)stag|Mittwoch|Freitag|S(ams|onn)tag|Sonnabend|Woche|Monat|Jahr|Morgens?|Abends|Übermorgen|Mittags?|Nachmittags?|Vormittags?|Spätabends?|Nachts?")
        ],
        [  # "Wir releasen das Montag.", "Wir präsentierten das Januar."
          pos_regex("VER:.*|UNKNOWN"),
          cs_token("das"),
          cs_regex(MONTH_NAMES_REGEX + "|Montags?|D(ien|onner)stags?|Mittwochs?|Freitags?|S(ams|onn)tags?|Sonnabends?|Morgens?|Abends|Übermorgen|Mittags?|Nachmittags?|Vormittags?|Spätabends?|Nachts?")
        ],
        [  # "Kannst du das Mittags machen?"
          token("das"),
          token_regex(MONTH_NAMES_REGEX + "|Montags?|D(ien|onner)stags?|Mittwochs?|Freitags?|S(ams|onn)tags?|Sonnabends?|Morgens?|Abends|Übermorgen|Mittags?|Nachmittags?|Vormittags?|Spätabends?|Nachts?"),
          pos_regex("VER:.*|UNKNOWN")
        ],
        [  # "Kannst du das nächsten Monat machen?"
          token("das"),
          token_regex("(über)?nächste[ns]?|kommende[ns]?|(vor)?letzten|vorigen"),
          cs_regex(MONTH_NAMES_REGEX + "|Montag|D(ien|onner)stag|Mittwoch|Freitag|S(ams|onn)tag|Sonnabend|Woche|Monat|Jahr|Morgens?|Abends|Übermorgen|Mittags?|Nachmittags?|Vormittags?|Spätabends?|Nachts?"),
          pos_regex("VER:.*|UNKNOWN")
        ],
        [
          token("das"),
          cs_regex("Zufall|Sinn|Spa(ß|ss)|Freude"),
          token("?")
        ],
        [
          cs_regex("w[äa]r|ist|sei"),
          token("das"),
          cs_regex("Zufall|Spa(ß|ss)"),
          cs_regex("\\.|\\?|!|,|…")
        ],
        [
          # Dann sei das Zufall gewesen
          cs_regex("w[äa]r|ist|sei"),
          token("das"),
          cs_regex("Zufall|Spa(ß|ss)"),
          cs_regex("gewesen")
        ],
        [
           # "War das Zufall, dass es ging?"
          token("das"),
          cs_regex("Zufall|Sinn|Spa(ß|ss)"),
          cs_token(",")
        ],
        [
          token("in"),
          token_regex("d(ies)?em"),
          token("Fall"),
          token_regex("(?i:hat(te)?)"),
          token("das")
        ],
        [  # "So hatte das Vorteile|Auswirkungen|Konsequenzen..."
          pos_regex("ADV:.+"),
          token_regex("(?i:hat(te)?)"),
          cs_token("das")
        ],
        [
          token_regex("von|bei"),
          cs_regex("vielen|allen|etlichen"),
          pos_regex("PA2:.*|ADJ:AKK:PLU:.*")  # "ein von vielen bewundertes Haus" / "Das weckte bei vielen ungute Erinnerungen."
        ],
        [
          # "Der letzte Woche vom Rat der Justizminister gefasste Beschluss..."
          token_regex("de[mnr]|die|das"),
          cs_regex("letzte[ns]?|vorige[ns]?"),
          cs_regex("Woche|Monat|Jahr(zehnt|hundert)?"),
          pos_regex("PRP:.*"),
          pos_regex("SUB:.*"),
          pos_regex("ART:.*"),
          pos_regex("SUB:.*"),
          pos_regex("PA2:.*")
        ],
        [
          token("für"),
          cs_regex("(viele|etliche|alle|[dm]ich|ihn|sie|uns|andere|jeden)"),
          pos_regex("ADJ:NOM:.*")  # "Ein für viele wichtiges Anliegen."
        ],
        [
          PatternTokenBuilder().token_regex("flö(ß|ss)en|machen|jagen").match_inflected_forms().build(),
          cs_regex("einem|jedem|keinem"),
          cs_token("Angst")  # "Dinge, die/ Etwas, das einem Angst macht"
        ],
        [
          # Kann ja jeder weiter Maske tragen, der will?
          cs_regex("jede[sr]?"),
          cs_token("weiter"),
          pos_regex("SUB.*")
        ],
        [
          token_regex("einem|jedem|keinem"),
          cs_token("Angst"),  # "Was einem Angst macht"
          PatternTokenBuilder().token_regex("machen|ein(flö(ß|ss)en|jagen)").match_inflected_forms().build()
        ],
        [
          token("einem"),
          cs_token("geschenkten"),
          cs_token("Gaul")
        ],
        [  # "Wir wollen sein ein einzig Volk von Brüdern" -- Schiller
          cs_token("ein"),
          cs_token("einzig"),
          cs_token("Volk"),
          cs_token("von")
        ],
        [  # "Lieber den Spatz in der Hand"
          cs_token("den"),
          cs_token("Spatz"),
          cs_token("in")
        ],
        [
          token("kein"),
          cs_token("schöner"),
          cs_token("Land")  # https://de.wikipedia.org/wiki/Kein_sch%C3%B6ner_Land
        ],
        [
          token_regex("die|der|das"),
          cs_regex("Anfang|Mitte|Ende"),
          cs_regex(MONTH_NAMES_REGEX + "|[12][0-9]{3}")
        ],
        [  # Waren das schwierige Entscheidungen?
          cs_regex("Ist|Sind|War|Waren|Macht|Wird|Werden"),
          cs_token("das"),
          PatternTokenBuilder().pos_regex("ADJ:NOM.*").min(0).build(),
          pos_regex("SUB:NOM.*"),
          pos_regex("PKT|KON:NEB|PRP.+")  # "Ist das Kunst?" / "Ist das Kunst oder Abfall?" / "Sind das Eier aus Bodenhaltung"
        ],
        [  # Soll das Demokratie sein?
          pos_regex("SENT_START|PKT|KON:NEB"),
          token_regex("soll|sollen|sollte|wird|werden|würde|kann|können|könnte|muss|müssen|müsste"),
          cs_token("das"),
          PatternTokenBuilder().pos_regex("ADJ:NOM.*").min(0).build(),
          pos_regex("SUB:NOM.*"),
          cs_regex("sein|werden")
        ],
        [  # Hat das Spaß gemacht?
          pos_regex("SENT_START|PKT|KON:NEB"),
          token_regex("hat|hatte"),
          cs_token("das"),
          PatternTokenBuilder().pos_regex("ADJ:NOM.*").min(0).build(),
          cs_regex("Spa(ß|ss)|Freude|Sinn|Mehrwert"),
          cs_regex("gemacht|ergeben|gestiftet")
        ],
        [  # Eine Lösung die Spaß macht
          token_regex("die|der|das"),
          PatternTokenBuilder().pos_regex("ADJ:NOM.*").min(0).build(),
          cs_regex("Spa(ß|ss)|Freude|Sinn|Mehrwert"),
          PatternTokenBuilder().token_regex("machen|schaffen|stiften|ergeben").match_inflected_forms().build()
        ],
        [  # Soll das Spaß machen?
          pos_regex("SENT_START|PKT|KON:NEB"),
          token_regex("soll|sollte|wird|würde|kann|könnte"),
          cs_token("das"),
          PatternTokenBuilder().pos_regex("ADJ:NOM.*").min(0).build(),
          cs_regex("Spa(ß|ss)|Freude|Sinn|Mehrwert"),
          cs_regex("machen|stiften|ergeben")
        ],
        [  # Die Präsent AG ("Theater AG" is found via DE_COMPOUNDS)
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("AG|GmbH|SE")
        ],
        [  # Die Otto Christ AG
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("AG|GmbH|SE|KG")
        ],
        [  # Die Otto Christ AG
          pos_regex("ART.*"),
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("AG|GmbH|SE|KG")
        ],
        [  # Die Ernst Klett Schulbuch AG
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("AG|GmbH|SE|KG")
        ],
        [  # Die damalige Klett AG
          token("die"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:FEM.*").cs_token_regex("[a-zäöü].+").min(0).build(),
          cs_regex("[A-ZÄÖÜ].+"),
          cs_regex("AG|GmbH|SE")
        ],
        [  # Die damalige Ernst Klett AG
          token("die"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:FEM.*").cs_token_regex("[a-zäöü].+").min(0).build(),
          cs_regex("[A-ZÄÖÜ].*"),
          cs_regex("[A-ZÄÖÜ].*"),
          cs_regex("AG|GmbH|SE")
        ],
        [  # Die damalige Ernst Klett Schulbuch AG
          token("die"),
          PatternTokenBuilder().pos_regex("ADJ:NOM:SIN:FEM.*").cs_token_regex("[a-zäöü].+").min(0).build(),
          cs_regex("[A-ZÄÖÜ].*"),
          cs_regex("[A-ZÄÖÜ].*"),
          cs_regex("[A-ZÄÖÜ].*"),
          cs_regex("AG|GmbH|SE")
        ],
        [
          # like above, but with ":", as we don't interpret this as a sentence start (but it often is)
          cs_regex("Meist(ens)?|Oft(mals)?|Häufig|Selten|Natürlich"),
          token_regex("sind|waren|ist"),
          token("das"),
          pos_regex("SUB:.*")  # Meistens sind das Frauen, die damit besser umgehen können.
        ],
        [  # Natürlich ist das Quatsch!
          token_regex("ist|war"),
          token("das"),
          token("Quatsch")
        ],
        [  # Eine Maßnahme die Vertrauen schafft
          token_regex("der|die"),
          token("Vertrauen"),
          PatternTokenBuilder().match_inflected_forms().token_regex("schaffen").build()
        ],
        [
          token("des"),
          token("Lied"),
          token("ich")  # Wes Brot ich ess, des Lied ich sing
        ],
        [  # Es ist einige Grad kälter (see example on https://www.duden.de/rechtschreibung/Grad)
          token("einige"),
          token("Grad")
        ],
        [  # Ein dickes Danke an alle die ...
          token("ein"),
          pos_regex("ADJ:.+"),
          token("Danke")
        ],
        [
          pos(SENTENCE_START_TAGNAME),
          token_regex("D(a|ie)s"),
          pos_regex("VER:[123]:.*"),
          pos_regex("SUB:NOM:.*")  # "Das erfordert Können und..." / "Dies bestätigte Polizeimeister Huber"
        ],
        [
          # like above, but with ":", as we don't interpret this as a sentence start (but it often is)
          token(":"),
          token_regex("D(a|ie)s"),
          pos_regex("VER:[123]:.*"),
          pos_regex("SUB:NOM:.*")  # "Das erfordert Können und..." / "Dies bestätigte Polizeimeister Huber"
        ],
        [
          pos_regex("ART:.+"),  # "Das wenige Kilometer breite Tal"
          pos_regex("ADJ:.+"),
          token_regex("(Kilo|Zenti|Milli)?meter|Jahre|Monate|Wochen|Tage|Stunden|Minuten|Sekunden")
        ],
        [
          token("van"),  # https://de.wikipedia.org/wiki/Alexander_Van_der_Bellen
          token("der")
        ],
        [
          token_regex("mehrere|etliche"),  # "mehrere Verwundete" http://forum.languagetool.org/t/de-false-positives-and-false-false/1516
          pos("SUB:NOM:SIN:FEM:ADJ")
        ],
        [
          token("allen"),
          token_regex("Besitz|Mut")
        ],
        [
          token_regex("d(ie|e[nr])|[md]eine[nr]?|(eure|unsere)[nr]?|diese[nr]?"),
          token("Top"),
          token_regex("\\d+")
        ],
        [
          token_regex("d(ie|e[nr])|[md]eine[nr]?|(eure|unsere)[nr]?|diese[nr]?"),
          pos_regex("(ADJ|PA[12]).+"),
          token("Top"),
          token_regex("\\d+")
        ],
        [  # "Unter diesen rief das großen Unmut hervor."
          pos_regex("VER:3:SIN:.*"),
          token("das"),
          pos_regex("ADJ:AKK:.*"),
          pos_regex("SUB:AKK:.*"),
          pos("ZUS"),
          pos(SENTENCE_END_TAGNAME)
        ],
        [  # "Bei mir löste das Panik aus."
          pos_regex("VER:3:SIN:.+"),
          token("das"),
          pos_regex("SUB:AKK:.+"),
          pos("ZUS"),
          pos(SENTENCE_END_TAGNAME)
        ],
        [
          token("der"),
          token("viele"),
          token_regex("Schnee|Regen")
        ],
        [
          token_regex("der|die"),
          token_regex("vielen?"),
          token("Aufmerksamkeit")
        ],
        [
          token_regex("Au(ß|ss)enring"),
          token("Autobahn")
        ],
        [
          token_regex("Senior|Junior"),
          token_regex("Leaders?"),
          token_regex("Days?")
        ],
        [
          # ich habe meine Projektidee (die riesiges finanzielles Potenzial hat) an einen Unternehmenspräsidenten geschickt
          pos_regex("SUB.*(FEM|PLU).*|EIG.*FEM.*|UNKNOWN"),
          token("("),
          token("die")
        ],
        [
          # Wir sind immer offen für Mitarbeiter die Teil eines der traditionellsten Malerbetriebe auf dem Platz Zürich werden möchten.
          pos_regex("PRP.*"),
          pos_regex("SUB.*PLU.*"),
          token("die"),
          pos_regex("SUB.*SIN.*")
        ],
        [
          pos_regex("SUB.*MAS.*|EIG.*MAS.*|UNKNOWN"),
          token("("),
          token("de[rm]")
        ],
        [
          pos_regex("SUB.*NEU.*|EIG.*NEU.*|UNKNOWN"),
          token("("),
          token("das")
        ],
        [
          pos("KON:UNT"),  # "dass das komplett verschiedene Dinge sind"
          token_regex("der|das|dies"),
          PatternTokenBuilder().pos("ADJ:PRD:GRU").min(0).build(),
          pos_regex("ADJ.*PLU.*SOL|PA2.*PLU.*SOL:VER"),
          pos_regex("SUB.*PLU.*")
        ],
        [
          pos("KON:UNT"),  # "ob die wirklich zusätzliche Gebühren abdrücken"
          token("die"),
          PatternTokenBuilder().pos("ADJ:PRD:GRU").min(0).build(),
          pos_regex("ADJ.*(NOM|AKK):PLU.*SOL|PA2.*(NOM|AKK):PLU.*SOL:VER"),
          pos_regex("SUB.*(NOM|AKK):PLU.*")
        ],
        [
          token_regex("Ende|Mitte|Anfang"),  # "Ende 1923"
          token_regex("1[0-9]{3}|20[0-9]{2}")
        ],
        [
          token_regex("dann|so"),
          token("bedarf"),
          token_regex("das|dies")
        ],
        [
          pos_regex("ART.*|PRO:POS.*"),
          pos_regex("ADJ.*|PA[12].*"),
          token_regex("Windows|iOS"),
          token_regex("\\d+")
        ],
        [
          # Die letzte unter Windows 98 lauffähige Version ist 5.1.
          pos_regex("ART.*|PRO:POS.*"),
          pos_regex("ADJ.*|PA[12].*"),
          pos_regex("ADJ.*|PA[12].*"),
          token_regex("Windows|iOS"),
          token_regex("\\d+")
        ],
        [
          pos_regex("ART.*|PRO:POS.*"),
          token_regex("Windows|iOS"),
          token_regex("\\d+")
        ],
        # wird empfohlen, dass Unternehmen die gefährliche Güter benötigen ...
        [
          token("dass"),
          PatternTokenBuilder().pos_regex("ADJ.*|PA[12].*").min(0).build(),
          pos_regex("SUB:.*PLU.*"),
          token("die"),
          pos_regex("ADJ.*|PA[12].*"),
          pos_regex("SUB:.*"),
          pos_regex("VER:.*")
        ],
        [  # des Handelsblatt Research Institutes
          cs_token("Handelsblatt"),
          cs_token("Research"),
          cs_regex("Institute?s?")
        ],
        [  # Ich arbeite bei der Shop Apotheke im Vertrieb
          cs_token("Shop"),
          cs_token("Apotheke")
        ],
        [  # In den Prime Standard
          cs_token("Prime"),
          cs_token("Standard")
        ],
        [  # Die Nord Stream 2 AG
          cs_token("Nord"),
          cs_token("Stream")
        ],
        [  # Ein Mobiles Einsatzkommando
          pos_regex("ART.*|PRO:POS.*"),
          cs_token("Mobiles"),
          cs_token("Einsatzkommando")
        ],
        [  # Die Gen Z
          pos_regex("ART.*|PRO:POS.*"),
          cs_token("Gen"),
          token_regex("[XYZ]")
        ],
        [  # Das veranlasste Bürgermeister Adam
          token_regex("das|dies"),
          cs_token("veranlasste"),
          pos_regex("SUB.*")
        ],
        [  # In einem Eins gegen Eins
          token_regex("ein|einem"),
          token("Eins"),
          cs_token("gegen"),
          token("Eins")
        ],
        [  # Dann musst du das Schritt für Schritt …
          token_regex("das|dies"),
          token("Schritt"),
          cs_token("für"),
          token("Schritt")
        ],
        [  # Das hat etliche Zeit in Anspruch genommen
          token("etliche"),
          token("Zeit")
        ],
        [  # Ich habe auf vieles Lust
          token("auf"),
          token("vieles"),
          token_regex("Lust|Bock")
        ],
        [  # die Französisch Polizei deportiert mich.
          token_regex("die(se)?|der|das|[msdk]?ein(en?)?|ihren?|euren?|euer|unser(er)?|viele|einige|sonstige"),
          cs_regex("Deutsch|Französisch|Arabisch|Katalanisch|Spanisch|Türkisch|Holländisch|Tschechisch|Griechisch|Kurdisch|Indisch|Schweizerisch|Österreichisch|Pakistanisch|Belgisch|Baye?risch|Serbisch|Kroatisch|Portugiesisch|Italienisch|Dänisch|Schwedisch|Irisch|Norwegisch|Russisch|Polnisch|Chinesisch"),
          pos_regex("SUB.*")
        ],
        [  # ob die Bock haben
          token("die"),
          token("Bock"),
          token_regex("haben|hatten")
        ],
        [  # dann haben die Bock
          token_regex("haben|hatten"),
          token("die"),
          token("Bock")
        ],
        [  # Ich habe für vieles Zeit
          token("für"),
          token("vieles"),
          token("Zeit")
        ],
        [
          # …, kann das Infektionen möglicherweise verhindern
          pos_regex("KON.*|PKT|SENT_START"),
          PatternTokenBuilder().pos_regex("ADV.*").min(0).build(),
          pos_regex("VER:MOD:3:SIN.*"),
          cs_token("das"),
          pos_regex("SUB.*"),
          PatternTokenBuilder().pos_regex("ADV.*").min(0).max(2).build(),
          pos_regex("VER:INF:.*")
        ],
        [
          # die gegnerischen Shooting Guards
          pos_regex("(ART|PRO:POS).*NOM:PLU"),
          pos_regex("(ADJ|PA[12]).*NOM:PLU.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # die gegnerischen Shooting Guards
          pos_regex("(ART|PRO:POS).*GEN:PLU"),
          pos_regex("(ADJ|PA[12]).*GEN:PLU.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # die gegnerischen Shooting Guards
          pos_regex("(ART|PRO:POS).*DAT:PLU"),
          pos_regex("(ADJ|PA[12]).*DAT:PLU.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # die gegnerischen Shooting Guards
          pos_regex("(ART|PRO:POS).*AKK:PLU"),
          pos_regex("(ADJ|PA[12]).*AKK:PLU.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # den leidenschaftlichen Lobpreis der texanischen Gateway Church aus
          pos_regex("(ART|PRO:POS).*DAT:SIN.*"),
          pos_regex("(ADJ|PA[12]).*DAT:SIN.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # den leidenschaftlichen Lobpreis des texanischen Gateway Church aus
          pos_regex("(ART|PRO:POS).*GEN:SIN.*"),
          pos_regex("(ADJ|PA[12]).*GEN:SIN.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # den leidenschaftlichen Lobpreis des texanischen Gateway Church aus
          pos_regex("(ART|PRO:POS).*NOM:SIN.*"),
          pos_regex("(ADJ|PA[12]).*NOM:SIN.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # den leidenschaftlichen Lobpreis des texanischen Gateway Church aus
          pos_regex("(ART|PRO:POS).*AKK:SIN.*"),
          pos_regex("(ADJ|PA[12]).*AKK:SIN.*"),
          pos_regex("SUB.*SIN.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-ZÖÄÜ][A-ZÖÄÜa-zöäüß\\-]+").build()
        ],
        [
          # Von der ersten Spielminute an machten die Münsteraner Druck und ...
          PatternTokenBuilder().match_inflected_forms().token_regex("machen").build(),
          token("die"),
          pos_regex("SUB.*PLU.*"),
          token_regex("Druck")
        ],
        [
          # Im Tun zu sein verhindert Prokrastination.
          token("zu"),
          token("sein"),
          pos_regex("VER:3:SIN.*")
        ],
        [
          token_regex("Ende|Mitte|Anfang"),  # "Der Ende der achtziger Jahre umgestaltete ..."
          PatternTokenBuilder().pos_regex("ART:DEF:GEN:.*").min(0).build(),
          PatternTokenBuilder().pos_regex("ADJ.*:(GEN|DAT):.*|ZAL").build(),
          token_regex("Woche|Monats|Jahr(es?|zehnts|hunderts|tausends)")
        ],
        [
          token_regex("Ende|Mitte|Anfang"),  # "Ende letzten Jahres" "Ende der 50er Jahre"
          PatternTokenBuilder().pos_regex("ART:DEF:GEN:.*").min(0).build(),
          PatternTokenBuilder().match_inflected_forms().token_regex("dieser|(vor)?letzter|[0-9]+er").build(),
          token_regex("Woche|Monats|Jahr(es?|zehnts|hunderts|tausends)")
        ],
        [
          token("das"),
          cs_token("Boostern")
        ],
        [
          # Das Zeit.de-CMS / Das Zeit.de CMS
          token("das"),
          PatternTokenBuilder().pos_regex("(ADJ|PA[12]).+").min(0).build(),
          cs_token("Zeit"),
          cs_token("."),
          token_regex("de.*")
        ],
        [
          token("das"),
          cs_token("verlangte"),
          token_regex("Ruhe|Zeit|Geduld")
        ],
        [
          cs_token("BMW"),
          token("ConnectedDrive")
        ],
        [
          # https://www.jungewirtschaft.at/
          token("die"),
          cs_token("Junge"),
          cs_token("Wirtschaft")
        ],
        [
          token("der"),
          cs_token("Jungen"),
          cs_token("Wirtschaft")
        ],
        [
          # Das passiert, weil die Schiss haben.
          token("die"),
          cs_regex("Schiss|Mut|Respekt"),
          token_regex("haben|h[äa]tten?|zeigt?en|zollt?en")
        ],
        [
          # "Inwiefern soll denn das romantische Hoffnungen begründen?"
          PatternTokenBuilder().pos("ADV:MOD+INR").set_skip(-1).build(),
          PatternTokenBuilder().pos_regex("VER.*:[123]:SIN:.*").set_skip(1).build(),
          pos_regex("PRO:DEM:.*SIN.*"),
          PatternTokenBuilder().pos_regex("ADJ:.*PLU.*").min(0).build(),
          pos_regex("SUB:.*PLU.*"),
          pos_regex("VER.*INF:.*")
        ],
        [
          # beides staatliche Organe
          token("beides"),
          PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").cs_token_regex("[a-z0-9äöüß\\-]+e").build(),
          pos_regex("SUB.*NOM.*PLU.*")
        ],
        [
          # 1944 eroberte diese weite Teile von Südosteuropa.
          pos_regex("VER.*"),
          token_regex("diese[sr]?"),
          token("weite"),
          token("Teile")
        ],
        [
          # Laut Charlie XCX selbst sind das Personen, die vielleicht eine ...
          token_regex("sind|w[äa]ren"),
          token("das"),
          pos_regex("SUB.*PLU.*"),
          token_regex("die|welche|ohne|mit")
        ],
        [
          # Laut Charlie XCX selbst sind das Personen, die vielleicht eine ...
          token_regex("sind|w[äa]ren"),
          token("das"),
          pos_regex("SUB.*PLU.*"),
          token(","),
          token_regex("die|welche|ohne|mit")
        ],
        [
          # an unseren amerikanischen Commercial Lawyer geschickt
          PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").cs_token_regex("[a-z0-9äöüß\\-]+e[snmr]?").build(),
          pos_regex("SUB.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-Z][a-zäöüß\\-]+").build()
        ],
        [
          # … an unseren Commercial Lawyer geschickt
          pos_regex("PRO.*|ART.*"),
          pos_regex("SUB.*"),
          PatternTokenBuilder().pos_regex("UNKNOWN").cs_token_regex("[A-Z][a-zäöüß\\-]+").build()
        ]
      ]
