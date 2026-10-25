"""Port of org.languagetool.rules.de.CaseRuleAntiPatterns: the
anti-patterns of CaseRule (also see /de/case_rule_exceptions.txt).

The pattern token lists were converted mechanically from the Java builder
code (PatternRuleBuilderHelper / PatternTokenBuilder calls), in the same
order and with the same comments."""

from ...analysis import SENTENCE_END_TAGNAME, SENTENCE_START_TAGNAME
from ...patterns.pattern_token import (PatternTokenBuilder, cs_regex, cs_token, pos, pos_regex, token,
                                       token_regex)
from .language_names import get_as_regex


def anti_patterns():
    """CaseRuleAntiPatterns.ANTI_PATTERNS: a tuple of pattern token lists
    (built anew on each call; CaseRule caches the anti-pattern rules)"""
    sent_start = PatternTokenBuilder().pos_regex(SENTENCE_START_TAGNAME).build()
    return (
        (
            cs_regex('von'),
            cs_regex('Gleich'),
            cs_regex('zu'),
            cs_regex('Gleich'),
        ),
        (
            cs_regex('[iI]n'),
            cs_regex('-'),
            cs_regex('und|oder'),
            cs_regex('[Aa]us.*'),
        ),
        (
            cs_regex('[1-9]{2,4}'),
            cs_regex(':'),
            cs_regex('[A-ZÜÄÖ][a-züäö].*'),
        ),
        (
            cs_regex('In'),
            cs_regex(':'),
            cs_regex('[A-ZÜÄÖ][a-züäö].*'),
        ),
        (
            cs_regex('China'),
            cs_regex('National'),
            cs_regex('Petroleum'),
        ),
        (
            cs_regex('Republik'),
            cs_regex('der'),
            cs_regex('Sieben'),
            cs_regex('Vereinigten'),
            cs_regex('Provinzen|Niederlande'),
        ),
        (
            cs_regex('Rat'),
            cs_regex('für'),
            cs_regex('das'),
            cs_regex('Europäische'),
            cs_regex('Hilfswerk'),
        ),
        (
            cs_regex('Museum'),
            cs_regex('der'),
            cs_regex('Bayerischen'),
            cs_regex('Geschichte'),
        ),
        (
            token('Planten'),
            token('un'),
            token_regex('Blomens?'),
        ),
        (
            PatternTokenBuilder().token('sprechen').match_inflected_forms().build(),
            cs_regex(get_as_regex()),
        ),
        (
            token_regex('(inter)?national|regional'),
            cs_regex('GmbH|gGmbH|AG|gAG|InvAG|OHG|KG|UG|eG|GbR'),
        ),
        (
            # "die Spiegelblank GmbH"
            token_regex('die|der'),
            cs_regex('[A-ZÄÜÖ].+'),
            cs_regex('GmbH|gGmbH|AG|gAG|InvAG|OHG|KG|UG|eG|GbR'),
        ),
        (
            # Autohaus Dornig GmbH
            PatternTokenBuilder().pos_regex('EIG:.+|SUB:.+').cs_token_regex('[A-Z].+').build(),
            cs_regex('[A-ZÄÜÖ].+'),
            cs_regex('GmbH|gGmbH|AG|gAG|InvAG|OHG|KG|UG|eG|GbR'),
        ),
        (
            pos_regex('ADJ:.*'),
            token_regex('&|and'),
            pos_regex('ADJ:.*'),
        ),
        (
            token_regex('Deutschen?|Österreichischen?|Schweizerischen?'),
            # TODO: extend
            token_regex('.*gesellschaft'),
        ),
        (
            cs_regex('im|ins|ans?'),
            cs_regex('Gestern|Vorgestern'),
        ),
        (
            cs_regex('im|ins|ans?|das'),
            cs_regex('Gestern|Vorgestern'),
            cs_regex('und|&'),
            cs_regex('Gestern|Vorgestern'),
        ),
        (
            cs_regex('[Ii]m|[Dd]as|[Dd]em|[Ii]ns|[Dd]es|[Aa]ufs'),
            cs_regex('Hier|Vorher'),
            cs_regex('und|&'),
            cs_regex('Jetzt|Nachher'),
        ),
        (
            cs_regex('[Ii]m|[Dd]as|[Dd]em|[Ii]ns|[Dd]es|[Aa]ufs'),
            cs_regex('Jetzt|Nachher'),
            cs_regex('und|&'),
            cs_regex('Hier|Vorher'),
        ),
        (
            cs_regex('im|ins'),
            cs_regex('Hier|Jetzt'),
        ),
        (
            cs_regex('[Dd]ieses|das|k?ein'),
            PatternTokenBuilder().pos_regex('ADJ.*NEU.*').min(0).build(),
            cs_regex('Rein'),
            cs_regex('und|&'),
            cs_regex('Raus'),
        ),
        (
            cs_regex('Private[snm]|Familiäre[snm]'),
            cs_regex('und|&'),
            cs_regex('Berufliche[snm]|Geschäftliche[snm]'),
        ),
        (
            cs_regex('Hin'),
            cs_regex('und|&'),
            cs_regex('Her'),
        ),
        (
            cs_regex('k?ein'),
            cs_regex('Richtig|Falsch'),
            cs_regex('und|oder|&'),
            cs_regex('Richtig|Falsch'),
        ),
        (
            cs_regex('Tax'),
            cs_regex('[au]nd|&'),
            cs_regex('Legal'),
        ),
        (
            # Er sagte, Geradliniges und Krummliniges sei unvergleichbar.
            cs_regex('[A-ZÄÖÜ].+es'),
            cs_regex('und|oder|&'),
            cs_regex('[A-ZÄÖÜ].+es'),
            cs_regex('[a-zäöüß\\-,\\.\\!\\?…;:–\\)\\(]+'),
        ),
        (
            # … in Ägyptisch, Berberisch und Semitisch erfolgte zuletzt.
            cs_regex('[A-ZÄÖÜ].+isch'),
            cs_regex('und|oder|&'),
            cs_regex('[A-ZÄÖÜ].+isch'),
            cs_regex('[a-zäöüß\\-,\\.\\!\\?…;:–\\)\\(]+'),
        ),
        (
            # … in Ägyptisch, Berberisch und Semitisch erfolgte zuletzt.
            cs_regex('[A-ZÄÖÜ].+em'),
            cs_regex('und|oder|&'),
            cs_regex('[A-ZÄÖÜ].+em'),
            cs_regex('[a-zäöüß\\-,\\.\\!\\?…;:–\\)\\(]+'),
        ),
        (
            # Er arbeitet im Bereich Präsidiales.
            cs_regex('Bereich|Departement|Stabsstellen?|Dienststellen?|AG|Arbeitsgruppe|Edition'),
            cs_regex('[A-ZÄÖÜ].+es'),
        ),
        (
            cs_regex('Berufliche[snm]'),
            cs_regex('und|&'),
            cs_regex('Private[snm]'),
        ),
        (
            token('des'),
            cs_token('Weiteren'),
        ),
        (
            # Mo.–So.
            cs_regex('\\.|Mo|Di|Mi|Do|Fr|Sa'),
            cs_regex('-|–'),
            cs_token('So'),
        ),
        (
            # "Tom ist ein engagierter, gutaussehender Vierzigjähriger, der..."
            pos_regex('(ADJ:|PA[12]).*'),
            token(','),
            pos_regex('(ADJ:|PA[12]).*'),
            token_regex('[A-ZÖÄÜ].+jährige[mnr]?'),
            pos_regex('(?!SUB).*'),
        ),
        (
            # Er war verantwortlich für Lieder wie Everything I Do und andere.
            pos_regex('_english_ignore_'),
            pos_regex('_english_ignore_'),
        ),
        (
            # "Um das herauszubekommen..."
            token('das'),
            token_regex('.+zu.+'),
        ),
        (
            token('Rock'),
            token_regex("['’]"),
            token('n'),
            token_regex("['’]"),
            token('Roll'),
        ),
        (
            token_regex('Vitamin-[A-Z][0-9]?-reich(e|e[nms])?'),
        ),
        (
            # Auflistung
            cs_regex('[A-ZÖÄÜ][a-zöäüß]+'),
            token(','),
            cs_regex('[A-ZÖÄÜ][a-zöäüß]+'),
            token_regex(',|etc'),
        ),
        (
            token_regex('erste[nr]?'),
            cs_token('Hilfe'),
        ),
        (
            # Names
            token_regex('Alfred|Emanuel|Günter|Immanuel|Johannes|Karl|Ludvig|Anton|Peter|Robert|Rolf'),
            cs_token('Nobel'),
        ),
        (
            # https://github.com/languagetool-org/languagetool/issues/1663
            token('Großes'),
            PatternTokenBuilder().token_regex('leisten|erreichen|schaffen').match_inflected_forms().build(),
        ),
        (
            # https://github.com/languagetool-org/languagetool/issues/1515
            sent_start,
            token_regex('[:;]'),
            token(')'),
            token_regex('.*'),
        ),
        (
            # https://github.com/languagetool-org/languagetool/issues/1515
            sent_start,
            token_regex('[;:]'),
            token('-'),
            token(')'),
            token_regex('.*'),
        ),
        (
            sent_start,
            token_regex('[A-Z]'),
            token(')'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # Commas used as lower quotes
            sent_start,
            token(','),
            token(','),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # ignore uppercase word at beginning after a character that is not a letter or number
            # (needed to ignore emojies or bullet points at the beginning of a sentence)
            sent_start,
            token_regex('^[^A-Za-z0-9ÄÖÜäöüàÀß]{1,2}$'),
            cs_regex('[A-ZÖÜÄ].*'),
        ),
        (
            sent_start,
            token('*'),
            token('*'),
            token_regex('.*'),
        ),
        (
            # two single quotes (’’) that create one double quote (needs different rule)
            sent_start,
            token('’'),
            token('’'),
            token_regex('.*'),
        ),
        (
            # wrong quote used as opening quote, leave to UNPAIRED_BRACKETS etc.
            token('“'),
            cs_regex('[A-ZÖÜÄ].*'),
        ),
        (
            # => Hallo test
            sent_start,
            token_regex('=|-'),
            token('>'),
            token_regex('.*'),
        ),
        (
            sent_start,
            token('#'),
            token_regex('\\d+'),
            token_regex('.*'),
        ),
        (
            # GitHub / Markdown check lists
            sent_start,
            token_regex('\\*|\\-'),
            token('['),
            token_regex(']'),
            token_regex('.*'),
        ),
        (
            # GitHub / Markdown check lists
            sent_start,
            token_regex('\\*|\\-'),
            token('['),
            token('x'),
            token_regex(']'),
            token_regex('.*'),
        ),
        (
            # non-alphanumeric character
            sent_start,
            token_regex('^[^a-zA-ZäöüÄÖÜ\\d\\s:]+$'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            token_regex('Roten?'),
            token_regex('Bete'),
        ),
        (
            # see https://www.duden.de/suchen/dudenonline/u-f%C3%B6rmig
            token_regex('[A-Z]-förmig(e[mnrs]?)?'),
        ),
        (
            token('Geboten'),
        ),
        (
            token_regex('vor|den'),
            token('Gefahren'),
        ),
        # names with english adjectives
        (
            token_regex('Digital|Global|Smart|International|Trade|Private|Live|Urban|Man|Total|Native|Imperial|'
                        'Modern|Responsive|Simple|Legend|Human|Light|Ministerial|National'),
            pos('UNKNOWN'),
        ),
        (
            token('International'),
            token_regex('Managements?'),
        ),
        (
            token('National'),
            token_regex('Boards?'),
        ),
        (
            token_regex('[kK]nock'),
            token_regex('[oO]ut'),
        ),
        (
            cs_token('das'),
            pos_regex('VER:INF:.+'),
            pos_regex('KON:NEB|PKT'),
        ),
        (
            # wenn sie das beantworten
            token_regex('wenn|falls|sobald'),
            pos_regex('PRO.*|EIG.*'),
            cs_token('das'),
            pos_regex('VER:INF:.+'),
            token_regex('dann|,|und|oder|\\.|\\!|\\:'),
        ),
        (
            # wenn sie mir das beantworten
            token_regex('wenn|falls|sobald'),
            pos_regex('PRO.*|EIG.*'),
            cs_regex('mir|uns|ih[rm]'),
            cs_token('das'),
            pos_regex('VER:INF:.+'),
            token_regex('dann|,|und|oder|\\.|\\!|\\:'),
        ),
        (
            # Ich hatte das vergessen oder nicht ganz verstanden.
            cs_token('das'),
            pos_regex('ADV.*'),
            pos_regex('VER:INF:.+'),
            pos_regex('KON:NEB|PKT'),
        ),
        # names with english adjectives
        (
            pos('UNKNOWN'),
            token_regex('Digital|Global|Smart|International|Trade|Private|Live|Urban|Man|Total|Native|Imperial|'
                        'Modern|Responsive|Simple|Legend|Human|Light|Ministerial'),
        ),
        # names with english adjectives
        (
            token('Smart'),
            pos_regex('SUB.*'),
        ),
        # names with english adjectives
        (
            token('National'),
            token_regex('Sales|University'),
        ),
        (
            # see http://www.lektorenverband.de/die-deutsche-rechtschreibung-was-ist-neu/
            # and http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            token_regex('Goldenen?'),
            token_regex('Hochzeit(en)?'),
        ),
        (
            # see http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            token_regex('Graue[nr]?'),
            token_regex('Stars?|Eminenz'),
        ),
        (
            # see http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            token_regex('Große[nr]?'),
            token_regex('Strafkammer|Latinums?|Rats?'),
        ),
        (
            # see http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            cs_token('Guten'),
            cs_token('Tag'),
        ),
        (
            # see http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            token_regex('Höheren?'),
            token_regex('Schule|Mathematik'),
        ),
        (
            # see http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            token_regex('Künstliche[nr]?'),
            token('Intelligenz'),
        ),
        (
            # see http://www.rechtschreibrat.com/DOX/rfdr_Woerterverzeichnis_2017.pdf
            token_regex('Neue[ns]?'),
            token_regex('Jahr(s|es)?|Linken?'),
        ),
        (
            token('Neues'),
            token('\\?'),
        ),
        (
            token('Zahl'),
            pos('UNKNOWN'),
        ),
        (
            # "... und Expert*innnen ..."
            token_regex('[A-Z].+'),
            token('*'),
            token('innen'),
        ),
        (
            # Names: "Jeremy Schulte", "Alexa Jung", "Fiete Lang", "Dorian Klug" ...
            PatternTokenBuilder().pos_regex('EIG:.+|UNKNOWN').cs_token_regex('[A-ZÄÖÜ].+').build(),
            cs_regex('Schulte|Junge?|Lange?|Braun|Groß|Gross|K(ü|ue)hne?|Schier|Becker|Schön|Sauer|Ernst|Fr(ö|'
                     'oe)hlich|Kurz|Klein|Schick|Frisch|Kluge|Weigert|D(ü|ue)rr|Nagele|Hoppe|D(ö|oe)rre|G(ö|'
                     'oe)ttlich|Stark|Fahle|Fromm(er)?|Reichert|Wiest|Klug|Greiser|Nasser'),
        ),
        (
            token(','),
            pos_regex('.*ADJ.*|UNKNOWN'),
            token_regex('[\\.?!)]'),
        ),
        (
            cs_token(','),
            token_regex('[md]eine?|du'),
            pos_regex('.*ADJ.*|UNKNOWN'),
            token_regex('[\\.?!]'),
        ),
        (
            pos_regex('.*ADJ.*|UNKNOWN'),
            token_regex('Konstanten?'),
        ),
        (
            token('das'),
            pos_regex('PA2:.+'),
            pos_regex('VER:AUX:.+'),
        ),
        (
            # Er fragte,ob das gelingen wird.
            cs_token('das'),
            pos_regex('VER:.+'),
            pos_regex('VER:AUX:.+'),
            pos_regex('PKT|KON:NEB'),
        ),
        (
            # Er fragte, ob das gelingen oder scheitern wird.
            cs_token('das'),
            pos_regex('VER:.+'),
            PatternTokenBuilder().pos('KON:NEB').set_skip(5).build(),
            pos_regex('VER:(AUX|MOD):.*'),
            pos_regex('PKT|KON:NEB'),
        ),
        (
            # um ihren eigenen Glauben an das Gute, Wahre und Schöne zu stärken.
            token('das'),
            pos_regex('SUB:.+'),
            token(','),
            token_regex('[A-ZÄÖÜ][a-zäöü]+'),
            token_regex('und|oder'),
        ),
        (
            # "... weshalb ihr das wissen wollt."
            pos('VER:INF:NON'),
            pos('VER:MOD:2:PLU:PRÄ'),
        ),
        (
            pos('UNKNOWN'),
            token('und'),
            pos_regex('SUB:.*'),
        ),
        (
            # Nicht geimpft werden dürfen Immunsupprimierte, Personen mit Fieber 38 °C oder Menschen,
            # die allergisch sind.
            pos('UNKNOWN'),
            token(','),
            pos_regex('SUB:.*'),
        ),
        (
            # "... wie ich das prüfen sollte."
            pos_regex('VER:INF.+'),
            pos_regex('VER:MOD:.+'),
        ),
        (
            # "... wie ich das prüfen würde."
            pos_regex('VER:INF.+'),
            pos_regex('VER:AUX:.:(SIN|PLU)(:KJ2)?'),
        ),
        (
            # "... etwas Interessantes und Spannendes suchte"
            token_regex('etwas|nichts|viel|wenig|allerlei|was'),
            token_regex('[A-ZÄÖÜ].*es'),
            token_regex('und|oder|,'),
            token_regex('[A-ZÄÖÜ].*es'),
        ),
        (
            # "... bringt Interessierte und Experten zusammen"
            pos_regex('VER:.*[1-3]:.*'),
            pos_regex('SUB:AKK:.+:ADJ'),
            token_regex('und|oder|,'),
            pos_regex('SUB:AKK:.+:(NEU|FEM|MAS)|ART:.*'),
        ),
        (
            # "Das südöstlich von Berlin gelegene"
            token_regex('(süd|nord|ost|west).*lich'),
            token('von'),
        ),
        (
            # "Entscheiden 42,5 Millionen Stimmberechtigte über..."
            token_regex('Million(en)?'),
            pos_regex('SUB:.*:ADJ'),
        ),
        (
            # "Vor Betreten des" / "Trotz Verboten seiner Eltern"
            pos_regex('PRP:.+|ADV:MOD'),
            pos('VER:PA2:NON'),
            pos_regex('(ART|PRO):(IND|DE[FM]|POS):GEN:.*'),
        ),
        (
            # "Er liebt UV-bestrahltes, Na-haltiges und Makeup-freies Obst."
            # "Er vertraut auf CO2-arme Wasserkraft"
            token_regex('[A-ZÄÖÜ0-9]+[a-zäöüß0-9]-[a-zäöüß]+'),
        ),
        (
            # "Das Aus für Italien kam unerwartet." / "Müller drängt auf Aus bei Pflichtmitgliedschaft"
            token_regex('auf|das|vor|a[mn]|vorzeitige[mns]?|frühe[mns]?|späte[mns]?'),
            cs_token('Aus'),
            pos_regex('^PRP:.+|VER:[1-3]:.+'),
        ),
        (
            # Das ist das Aus des Airbus A380.
            token_regex('das'),
            cs_token('Aus'),
            token_regex('des|eines'),
            pos_regex('EIG:.+|SUB:.*|UNKNOWN'),
        ),
        # Arrays.asList(
        #       // "...,die ins Nichts griff."
        #       new PatternTokenBuilder().csTokenRegex("ins|ans|vors|durchs|hinters").setSkip(1).build(),
        #       posRegex("^PRP:.+|VER:[1-3]:.+")
        #     ),
        (
            # "Bündnis 90/Die Grünen"
            cs_token('90'),
            cs_token('/'),
            cs_token('Die'),
        ),
        (
            # https://de.wikipedia.org/wiki/Neue_Mittelschule
            token_regex('Neue[nrs]?'),
            (PatternTokenBuilder()
             .token_regex('Mitte(lschule)?|Rathaus|Testament|Welt|Markt|Rundschau')
             .match_inflected_forms()
             .build()),
        ),
        (
            # "Das schließen Forscher aus ..."
            token('das'),
            pos_regex('VER:INF:(SFT|NON)'),
            pos_regex('SUB:NOM:PLU:.+|ADV:MOD'),
        ),
        (
            # Das schaffen moderne E-Autos locker
            token('das'),
            pos_regex('VER:INF:(SFT|NON)'),
            pos_regex('ADJ:.+'),
            pos_regex('SUB:NOM:PLU:.+|ADV:MOD'),
        ),
        (
            # Das schaffen moderne und effiziente E-Autos locker
            token('das'),
            pos_regex('VER:INF:(SFT|NON)'),
            pos_regex('ADJ:.+'),
            pos_regex('KON:.+'),
            pos_regex('ADJ:.+'),
            pos_regex('SUB:NOM:PLU:.+|ADV:MOD'),
        ),
        (
            # "Tausende Gläubige kamen, um ihn zu sehen."
            token_regex('[tT]ausende?'),
            pos_regex('SUB:NOM:.+'),
            pos_regex(SENTENCE_END_TAGNAME + '|VER:[1-3]:.+'),
        ),
        (
            # "Man kann das generalisieren"
            pos_regex('VER:MOD.*'),
            token('das'),
            pos_regex('VER:INF:(SFT|NON)'),
        ),
        (
            # "Vielleicht kann er das generalisieren"
            pos_regex('VER:MOD.*'),
            pos_regex('PRO:.+'),
            token('das'),
            pos_regex('VER:INF:(SFT|NON)'),
        ),
        (
            # "Er befürchtete Schlimmeres."
            token_regex('Schlimm(er)?es'),
            pos(SENTENCE_END_TAGNAME),
        ),
        (
            token_regex('Angehörige[nr]?'),
        ),
        (
            # aus Alt wird neu
            cs_token('Alt'),
            token_regex('mach|w[iu]rde?'),
            cs_token('Neu'),
        ),
        (
            # see GermanTagger.getSubstantivatedForms
            pos('SUB:NOM:SIN:MAS:ADJ'),
            pos_regex('PRP:.+'),
        ),
        (
            # Einen Tag nach Bekanntwerden des Skandals
            pos('ZUS'),
            cs_token('Bekanntwerden'),
        ),
        (
            # Das ist also ihr Zuhause.
            pos_regex('.+:(POS|GEN):.+'),
            cs_token('Zuhause'),
        ),
        (
            # Ein anderes Zuhause habe ich nicht.
            token_regex('altes|anderes|k?ein|neues'),
            cs_token('Zuhause'),
        ),
        (
            # Weil er das kommen sah, traf er Vorkehrungen.
            cs_token('das'),
            cs_token('kommen'),
            PatternTokenBuilder().cs_token('sehen').match_inflected_forms().build(),
        ),
        (
            token('auf'),
            cs_token('die'),
            cs_token('Schnelle'),
        ),
        (
            # denn es fehlt bis heute am Nötigsten
            PatternTokenBuilder().cs_token('fehlen').match_inflected_forms().set_skip(3).build(),
            cs_token('am'),
            cs_token('Nötigsten'),
        ),
        (
            cs_token('am'),
            cs_token('Nötigsten'),
            PatternTokenBuilder().cs_token('fehlen').match_inflected_forms().build(),
        ),
        (
            token_regex('im|ins'),
            cs_token('Aus'),
        ),
        (
            token('im'),
            cs_token('Ganzen'),
        ),
        (
            # Die Top Fünf (https://www.korrekturen.de/forum.pl/md/read/id/73791/sbj/top-top-fuenf-fuenf/)
            cs_token('Top'),
            pos('ZAL'),
        ),
        (
            # Die Top Ten (https://www.korrekturen.de/forum.pl/md/read/id/73791/sbj/top-top-fuenf-fuenf/)
            cs_token('Top'),
            cs_token('Ten'),
        ),
        (
            # Dutch name (e.g. "Bert van den Brink")
            cs_token('Van'),
            cs_token('Den'),
        ),
        (
            cs_token('Lasse'),
            pos_regex('EIG:.*|UNKNOWN'),
        ),
        (
            # Spanish name (e.g. "Las Condes")
            cs_token('Las'),
            PatternTokenBuilder().pos('UNKNOWN').cs_token_regex('[A-Z].+').build(),
        ),
        (
            cs_token('Just'),
            token('in'),
            cs_token('Time'),
        ),
        (
            # Hey Süßer,
            token_regex('Hey|Hi|Hallo|Na|Moin|Servus'),
            token_regex('Süßer?|Hübscher?|Liebster?|Liebes'),
            pos('PKT'),
        ),
        (
            # Guten Morgen Liebste,
            cs_regex('Guten?'),
            cs_regex('Morgen|Abend|Mittag|Nacht'),
            token_regex('Süßer?|Hübscher?|Liebster?|Liebes'),
            pos('PKT'),
        ),
        (
            # Hey Matt (name),
            token_regex('Hey|Hi|Hallo|Na|Moin|Servus'),
            token_regex('Matt|Will|Per'),
        ),
        (
            # Hey mein Süßer,
            token_regex('Hey|Hi|Hallo|Na|Moin|Servus'),
            token_regex('du|meine?'),
            token_regex('Süßer?|Hübscher?'),
            pos('PKT'),
        ),
        (
            # Grüße aus Höchst, Ich wohne in Wohlen
            token_regex('aus|in'),
            token_regex('Höchst|Wohlen'),
        ),
        (
            # Am So. (Sonntag)
            token_regex(',|;|/|-|am|bis|vor|\\('),
            cs_token('So'),
            token('.'),
        ),
        (
            # a.) Im Mittelpunkt ...
            sent_start,
            token_regex('[a-z]'),
            token('.'),
            token(')'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # ---> Der USB  ...
            sent_start,
            token_regex('[-]{1,}'),
            token('>'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # # Was macht eigentlich Karl
            sent_start,
            token_regex('[#]{1,}'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # ## Was macht eigentlich Karl
            sent_start,
            token('#'),
            token('#'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # ### Was macht eigentlich Karl
            sent_start,
            token('#'),
            token('#'),
            token('#'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # = Schrittweise Erklärung ()
            sent_start,
            token('='),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # == Schrittweise Erklärung
            sent_start,
            token('='),
            token('='),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # === Schrittweise Erklärung
            sent_start,
            token('='),
            token('='),
            token('='),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # ==== Schrittweise Erklärung
            sent_start,
            token('='),
            token('='),
            token('='),
            token('='),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # ===== Schrittweise Erklärung
            sent_start,
            token('='),
            token('='),
            token('='),
            token('='),
            token('='),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # § 1 Allgemeine Bedingungen
            sent_start,
            token('§'),
            token_regex('\\d+'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # §1 Allgemeine Bedingungen
            sent_start,
            token_regex('§\\d+'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # 3a) Deine Idee ...
            sent_start,
            token_regex('[a-z0-9]{1,3}'),
            token(')'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # @Peter Hast du morgen Zeit?
            sent_start,
            token_regex('@.+'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # @b_fischer Der Bonussemester-Antrag oder der Widerspruch?
            sent_start,
            token_regex('@.+'),
            token('_'),
            token_regex('[a-z].*'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # M3.2 Deine Idee ...
            sent_start,
            token_regex('[A-Z]\\d+'),
            token('.'),
            token_regex('\\d+'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            cs_token('Gefahren'),
            cs_token('lauern'),
        ),
        (
            cs_regex('[A-ZÄÜÖ].+'),
            PatternTokenBuilder().token_regex('\\*|:').set_is_white_space_before(False).build(),
            cs_regex('innen|en?'),
        ),
        (
            # Am So 14:00 (should be "So." but that's a different error)
            cs_regex('am|jeden'),
            cs_token('So'),
        ),
        (
            # "Sa. oder So."
            cs_regex('M[io]|D[io]||Fr|Sa'),
            token('.'),
            cs_regex('&|und|oder|-|,'),
            cs_token('So'),
            token('.'),
        ),
        (
            # "Sa. oder So."
            cs_regex('M[io]|D[io]||Fr|Sa'),
            token('.'),
            cs_token('So'),
            token('.'),
        ),
        (
            # "Sa, So"
            cs_token('Sa'),
            cs_regex('&|und|oder|-|,'),
            cs_token('So'),
        ),
        (
            # Es hatte 10,5 Ah
            cs_regex('\\d+'),
            cs_token('Ah'),
        ),
        (
            # Via Camparlungo (Straßennamen in der italienischen Schweiz)
            cs_token('Via'),
            PatternTokenBuilder().pos('UNKNOWN').cs_token_regex('[A-Z].+').build(),
        ),
        (
            # Geoghegan Hart
            PatternTokenBuilder().pos('UNKNOWN').cs_token_regex('[A-Z].+').build(),
            cs_token('Hart'),
        ),
        (
            # Namen mit "Matt" (e.g. Matt Gaetz, Will Smith)
            cs_regex('Matt|Will|Dick'),
            PatternTokenBuilder().pos_regex('EIG:.+|UNKNOWN').cs_token_regex('[A-Z].+').build(),
        ),
        (
            # Klicke auf Home > Mehr > Team
            cs_token('>'),
            cs_regex('[A-ZÄÜÖ].+'),
            cs_token('>'),
        ),
        (
            # :D Auf dieses Frl. der apfel fällt ja doch nicht weit vom stamm!
            sent_start,
            token_regex('[:;]'),
            token_regex('[DPO]'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # :-D Auf dieses Frl. der apfel fällt ja doch nicht weit vom stamm!
            sent_start,
            token_regex('[:;]'),
            token('-'),
            token_regex('[DPO]'),
            token_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # Straßenname: "Am Hohen Hain 6"
            cs_regex('[IA]m'),
            cs_regex('[A-ZÄÖÜ].+n'),
            pos_regex('(EIG|SUB|UNKNOWN).*'),
            cs_regex('\\d{1,3}[a-hA-H]?'),
        ),
        (
            # Straßenname: "Am hohen Hain 6"
            cs_token('Am'),
            PatternTokenBuilder().pos_regex('ADJ:.+').cs_token_regex('[a-zäöü].+n').build(),
            cs_regex('[A-ZÄÜÖ].*'),
            cs_regex('\\d{1,3}[a-hA-H]?'),
        ),
        (
            # Straßenname: "Im hohen Hain 6e"
            cs_token('Im'),
            PatternTokenBuilder().pos_regex('ADJ:.+').cs_token_regex('[a-zäöü].+n').build(),
            cs_regex('[A-ZÄÜÖ].*'),
            cs_regex('\\d{1,3}[a-hA-H]|\\d'),
        ),
        (
            # Straßenname: "Am Wasserturm 6"
            cs_token('Am'),
            pos_regex('(EIG|SUB|UNKNOWN).*'),
            cs_regex('\\d+[a-hA-H]?'),
        ),
        (
            # Straßenname: "Am Wasserturm 6"
            cs_regex('[IA]m'),
            cs_regex('[A-Z].*(pfad|weg|kamp|platz|tor|gasse|feld|berg|park)'),
            cs_regex('\\d+[a-hA-H]?'),
        ),
        (
            # Straßenname: "Neue Kantstraße 6"
            cs_regex('Neuen?|Gro(ß|ss)e[rn]?|Alte[rn]?|Obere[rn]?|Untere[rn]?|Kleine[rn]?|Breite[rn]?'),
            cs_regex('[A-Z].+stra(ss|ß)e|.*[kK]amps?|.*[Tt]ors?|.*[Hh]ofs?|.*[Gg]asse|.*[Gg]rabens?|.*[Ff]elds?|'
                     '.*[Pp]latz(es)?|.*[Bb]ergs?|.*[Pp]arks?|.*[Ww]egs?|.*[Aa]llee|.*[wW]eide?|.*[mM]auer|.*[rR]eihe'),
            cs_regex('\\d{1,3}[a-hA-H]?|in'),
        ),
        (
            # Straßenname: "Neue Kantstr. 6"
            cs_regex('Neuen?|Gro(ß|ss)en?|Alten?|Oberen?|Unteren?|Breiten?'),
            cs_regex('[A-Z].+str'),
            token('.'),
            cs_regex('\\d{1,3}[a-hA-H]?|in'),
        ),
        (
            sent_start,
            # Listenpunkt https://github.com/languagetool-org/languagetool/issues/1515
            token_regex('\\*|-|/|_|%|o'),
            token_regex('.*'),
        ),
        (
            # Trennzeichen https://github.com/languagetool-org/languagetool/issues/1515
            token_regex('▶︎|▶|▶️|►|⇒|→|•|★|⧪|⮞|✔︎|✓|✔️|✅|0️⃣|1️⃣|2️⃣|3️⃣|4️⃣|5️⃣|6️⃣|7️⃣|8️⃣|9️⃣|❤️|➡️|➔|⇨|☛|◼|▲|◆|▪|'
                        '■|☞|❤|♥︎|✒︎|☑️|✗|✘|✖|➢|↑|=|>|\\}|❏|›|❖|·|▲|◄|⬢|\\||!|‼️|⚠️|√'),
            token_regex('.*'),
        ),
        (
            # Pfeil "=>"
            token_regex('[=\\-–]'),
            token('>'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # Zwei Kommas, die wie Anführungszeichen verwendet werden: ",,"
            PatternTokenBuilder().token(',').build(),
            PatternTokenBuilder().token(',').set_is_white_space_before(False).build(),
            PatternTokenBuilder().cs_token_regex('[A-ZÄÜÖ].*').set_is_white_space_before(False).build(),
        ),
        (
            # Markup: "[H3] Die Headline"
            token_regex('[a-z0-9\\-äöüß]+'),
            token(']'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            cs_regex('Schritt|Punkt|Absatz'),
            token_regex('\\d+'),
            token(':'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # Markup: "H3 Die Headline"
            sent_start,
            token_regex('H[1-6]'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "B.4 Neue Herstellervorgaben"
            sent_start,
            token_regex('[a-z]'),
            token('.'),
            token_regex('\\d+'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "1-) Ich bin ein Listenpunkt"
            sent_start,
            token_regex('\\d+-'),
            token_regex('[\\)\\]\\}]'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "1, Ich bin ebenfalls ein Listenpunkt"
            sent_start,
            token_regex('[a-z0-9]'),
            token(','),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "T = Das Ziel"
            sent_start,
            token_regex('[A-Z0-9]+'),
            token('='),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "(2c) Der Betrieb ist untersagt"
            sent_start,
            token_regex('[\\[\\(\\{]'),
            token_regex('[a-z0-9]{1,5}'),
            token_regex('[\\]\\)\\}]'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "(2c) Der Betrieb ist untersagt"
            sent_start,
            token_regex('[\\[\\(\\{]'),
            token_regex('[a-z0-9]{1,5}'),
            token('.'),
            token_regex('[a-z0-9]{1,5}'),
            token_regex('[\\]\\)\\}]'),
        ),
        (
            # "Sie/Er hat recht."
            sent_start,
            cs_regex('[A-ZÄÜÖ].*'),
            token('/'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "Sie/Er/Es hat recht."
            sent_start,
            cs_regex('[A-ZÄÜÖ].*'),
            token('/'),
            cs_regex('[A-ZÄÜÖ].*'),
            token('/'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "Er trank ein paar Halbe."
            token_regex('paar|einige|zwei|drei|vier|\\d+'),
            token('Halbe'),
        ),
        (
            # "Wir machen das Sa So Mo" (fehlender Punkt)
            cs_token('Sa'),
            cs_token('So'),
        ),
        (
            # "Wir machen das Sa oder So" (fehlender Punkt)
            cs_token('Sa'),
            token_regex('&|und|oder|-'),
            cs_token('So'),
        ),
        (
            # Vielleicht reden wir später mit ein paar Einheimischen.
            token('ein'),
            token('paar'),
            PatternTokenBuilder().pos_regex('.*SUB.*').cs_token_regex('[A-ZÖÜÄ].+').build(),
            PatternTokenBuilder().cs_token_regex('[a-zäöüß.,!?:;\\-–].*').build(),
        ),
        (
            PatternTokenBuilder().cs_token('Neues').set_skip(1).build(),
            PatternTokenBuilder().token('wagen').match_inflected_forms().build(),
        ),
        (
            # Wir wagen Neues.
            PatternTokenBuilder().token('wagen').match_inflected_forms().build(),
            token('Neues'),
        ),
        (
            # Das birgt zugleich Gefahren
            PatternTokenBuilder().cs_token('birgen').match_inflected_forms().set_skip(5).build(),
            token('Gefahren'),
        ),
        (
            # Du Ärmster!
            token('du'),
            cs_regex('Ärmster?'),
            cs_regex('[^A-ZÖÄÜ].*'),
        ),
        (
            # "... und das Zwischenmenschliche Hand in Hand."
            pos_regex('ART:.*|PRO:POS:.*'),
            PatternTokenBuilder().pos_regex('SUB:.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            cs_token('Hand'),
            cs_token('in'),
            cs_token('Hand'),
        ),
        (
            # "Der Platz auf dem die Ahnungslosen Kopf and Kopf stehen.""
            pos_regex('ART:.*|PRO:POS:.*'),
            PatternTokenBuilder().pos_regex('SUB:.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            cs_token('Kopf'),
            cs_token('an'),
            cs_token('Kopf'),
        ),
        (
            # "Der Platz auf dem die Ahnungslosen Schulter and Schulter stehen.""
            pos_regex('ART:.*|PRO:POS:.*'),
            PatternTokenBuilder().pos_regex('SUB:.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            cs_token('Schulter'),
            cs_token('an'),
            cs_token('Schulter'),
        ),
        (
            # "Der Platz auf dem die Ahnungslosen Stück für Stück ...""
            pos_regex('ART:.*|PRO:POS:.*'),
            PatternTokenBuilder().pos_regex('SUB:.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            cs_token('Stück'),
            cs_token('für'),
            cs_token('Stück'),
        ),
        (
            # "Der Platz auf dem die Ahnungslosen Schritt für Schritt ...""
            pos_regex('ART:.*|PRO:POS:.*'),
            PatternTokenBuilder().pos_regex('SUB:.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            cs_token('Schritt'),
            cs_token('für'),
            cs_token('Schritt'),
        ),
        (
            # "Der Platz auf dem die Ahnungslosen Arm in Arm ...""
            pos_regex('ART:.*|PRO:POS:.*'),
            PatternTokenBuilder().pos_regex('SUB:.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            cs_token('Arm'),
            cs_token('in'),
            cs_token('Arm'),
        ),
        (
            # ``Ich bin ein Anführungszeich
            sent_start,
            token('`'),
            token('`'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "4b Ein Listenpunkt"
            sent_start,
            token_regex('\\d{1,2}[a-z]'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "3.) Ein Listenpunkt"
            sent_start,
            token_regex('\\d{1,3}[a-z]?'),
            cs_token('.'),
            token_regex('[\\]\\)\\}]'),
            cs_regex('[A-ZÄÜÖ].*'),
        ),
        (
            # "Es besteht aus Schülern, Arbeitstätigen und Studenten."
            pos_regex('SUB:.+'),
            cs_token(','),
            pos_regex('SUB:.+'),
            cs_regex('und|oder|&'),
            pos_regex('SUB:.+:(MAS|FEM|NEU)'),
        ),
        (
            # Das denken zwar viele, ist aber total falsch.
            sent_start,
            cs_token('Das'),
            cs_token('denken'),
            PatternTokenBuilder().pos_regex('ADV:.+').min(0).build(),
            cs_regex('viele|manche|die|[dms]eine|ihre|eure|diese|jene|wenige'),
        ),
        (
            # Ich habe eine Menge Schlechtes über dich gehört
            cs_token('Menge'),
            cs_regex('Gutes|Schlechtes|Tolles|Böses|Schlimmes'),
            cs_regex('[a-zäöüß].*|\\.|\\,|\\!|:|;'),
        ),
        (
            # Während 208 der Befragten Frau Baerbock bevorzugten, ...
            cs_regex('\\d+%?|%|Prozent|meisten|wenige|einige|viele|Gro(ß|ss)teil'),
            cs_token('der'),
            cs_regex('Befragten|Teilnehmenden'),
            PatternTokenBuilder().pos_regex('SUB:.*').cs_token_regex('[A-ZÖÜÄ].+').build(),
        ),
        (
            # Dabei trauten die Befragten Frau Baerbock mehr zu.
            cs_token('die'),
            PatternTokenBuilder().pos_regex('SUB:NOM:PLU.*:ADJ').cs_token_regex('[A-ZÖÜÄ].+').build(),
            PatternTokenBuilder().pos_regex('SUB:.*:SIN').cs_token_regex('[A-ZÖÜÄ].+').build(),
        ),
        (
            # Sie starrt ständig ins Nichts.
            cs_regex('vorm|ins|im'),
            cs_token('Nichts'),
        ),
        (
            # zahlreiche Kulturschaffende, jungen Wilden
            cs_regex('[a-zäöü].+en?'),
            PatternTokenBuilder().pos_regex('SUB:NOM:PLU.*').cs_token_regex('[A-ZÄÖÜ].+').build(),
            cs_regex(',|und|oder|aber|\\.|!|\\?|…'),
        ),
        (
            # ignore uppercase words after invisible commas at sent start
            sent_start,
            token_regex('\\u2063'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # ignore uppercase words after invisible commas at sent start
            sent_start,
            token_regex('\\u2063'),
            token_regex('\\u2063'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # ignore uppercase words after invisible commas at sent start
            sent_start,
            token_regex('\\u2063'),
            token_regex('\\u2063'),
            token_regex('\\u2063'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # ignore uppercase words after invisible commas at sent start
            sent_start,
            token_regex('\\u2063'),
            token_regex('\\u2063'),
            token_regex('\\u2063'),
            token_regex('\\u2063'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # emoji question/exclamation mark
            token_regex('.*(\\u2753|\\u2757)'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            sent_start,
            token_regex('[\\\\/`´*„"\']'),
            token_regex('[\\\\/`´*„"\']'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            token_regex('nur'),
            cs_regex('Positives|Schlechtes|Gutes|Böses|Negatives|Folgendes|Neues|Altes|Schlimmes|Letzteres|Ersteres|'
                     'Blödes|Schreckliches|Wesentliches|Falsches|Richtiges|Hässliches'),
            cs_regex('[a-zäöü…\\.!\\?…].*'),
        ),
        (
            token('im'),
            cs_regex('Wesentlichen|Vorab|Geringsten'),
        ),
        (
            token('ans'),
            cs_regex('Wesentliche'),
        ),
        (
            token('im'),
            cs_regex('Allgemeinen'),
            cs_regex('[a-zäöü…\\.!\\?…].*'),
        ),
        (
            token('im'),
            cs_regex('Allgemeinen'),
            pos_regex('SUB.*FEM.*'),
        ),
        (
            token('im'),
            cs_regex('Allgemeinen'),
            pos_regex('SUB.*PLU.*'),
        ),
        (
            token('im'),
            cs_regex('Stillen|Dunkeln|Dunklen|Trocke?nen|Hellen|Trüben|Kalten|Warmen|Geringsten|Entferntesten|'
                     'Verborgenen'),
            cs_regex('[a-zäöü…\\.!\\?…\\)\\(;].*'),
        ),
        (
            token_regex('[\\ud83c\\udc00-\\ud83c\\udfff]+|[\\ud83d\\udc00-\\ud83d\\udfff]+|[\\u2600-\\u27ff]+'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Es gibt S-Bahn-ähnliche(, günstige) Verkehrsmittel
            cs_regex('[A-ZÄÖÜ]-[A-ZÄÖÜ].*-.*'),
            PatternTokenBuilder().pos_regex('PKT|KON:NEB|ADJ.*').min(0).max(2).build(),
            pos_regex('SUB.*'),
        ),
        (
            # Das ist das Debakel und Aus für Podolski
            cs_token('Aus'),
            cs_token('für'),
        ),
        (
            # Frohes Neues!
            cs_regex('[Ff]rohes|[Gg]esundes'),
            cs_token('Neues'),
        ),
        (
            # Wir sollten das mal labeln
            cs_token('das'),
            cs_token('mal'),
            cs_regex('[a-zäöüß].+n'),
        ),
        (
            token_regex('[^a-zäöüß\\-0-9]+'),
            cs_token('['),
            cs_token('…'),
            cs_token(']'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            token_regex('[^a-zäöüß\\-0-9]+'),
            cs_token('['),
            cs_token('.'),
            cs_token('.'),
            cs_token('.'),
            cs_token(']'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Kund:in
            cs_token('Kund'),
            cs_regex('[:_*\\/]'),
            token_regex('(in|innen|en?).*'),
        ),
        (
            # Wie ein verstoßener Größenwahnsinniger.
            pos_regex('ART:.*|PRO:POS:.*'),
            pos_regex('PA[12].*'),
            pos_regex('SUB.*ADJ'),
            cs_regex('[a-zäöüß\\-,\\.\\!\\?…;:–\\)\\(]+'),
        ),
        (
            # Vorab das Wichtigste - ...
            pos_regex('das'),
            pos_regex('SUB.*NEU:ADJ'),
            cs_regex('[a-zäöüß\\-,\\.\\!\\?…;:–\\)\\(]+'),
        ),
        (
            # Wichtiges/Lehrreiches/Großes/...
            token('/'),
            cs_regex('[A-ZÄÖÜ].*'),
            token('/'),
        ),
        (
            # Alles_Zutreffendes.csv
            token('_'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # Etwas anderes Lebendiges
            cs_regex('anderes'),
            cs_regex('[A-ZÄÖÜ].+es'),
            cs_regex('[a-zäöü…\\.!:;,\\?…\\)].*'),
        ),
        (
            # Ich habe noch Dringendes mitzuteilen
            cs_regex('Dringende[ms]|Bare[ms]|Vertraute[ms]|Positive[sm]|Negative[sm]|Gelernte[ms]|Neue[ms]|Alte[ms]|'
                     'Bessere[ms]|Störende[ms]|Schlechteres|Schlechte[ms]|Schöne[ms]|Schönere[ms]|Schlimmere[ms]|'
                     'Zutreffendes|Unzutreffende[ms]|Gesehene[ms]|Ungesehene[ms]|Abgerissene[ms]|Versoffenes|'
                     'Empfehlenswerte[ms]|Entnommene[ms]|Sü(ß|ss)e[ms]|Saure[ms]|Wesentliche[ms]|Gegenteilige[ms]|'
                     'Wegweisende[ms]|Hochprozentige[ms]|Erlernte[ms]|Vergangene[ms]|Unglaubliche[ms]|Schlimme[ms]|'
                     'Eingemachte[ms]|Rare[ms]|Brauchbare[ms]|Unbrauchbare[ms]|Gesehene[ms]|Erlebte[ms]|Private[ms]|'
                     'Berufliche[ms]|Ungeheuerliche[ms]|Vegane[ms]|Vegetarische[ms]|Eingemachte[ms]|Erwünschte[ms]|'
                     'Äu(ß|ss)erste[ms]|Äu(ß|ss)ere[ms]|Inhaltliche[ms]|Vernichtende[ms]|Salzige[ms]|Sü(ß|ss)e[ms]|'
                     'Selbstgemachte[ms]|Inhaltliche[ms]|Au(ß|ss)erordentliche[ms]|Säuerliche[ms]|Göttliche[ms]||'
                     'Hochprozentige[sm]|Erbrochene[ms]|Innere[mns]|Vorhandene[ms]|Relevante[ms]|Geübte[ms]|'
                     'Unmögliche[ms]|Mögliche[ms]|Näheres|Wissenswerte[ms]|Fundamentale[ms]|Interessante[ms]|'
                     'Uninteressante[ms]|Entsetzliche[ms]|Hartnäckige[ms]|Ersparte[ms]|Halbgare[ms]|Universale[ms]|'
                     'Finanzielle[ms]|Überraschendes|Grundlegendes|Gesunde[ms]|Ungesunde[ms]|Tagesaktuelle[ms]|'
                     'Aktuelle[ms]|Geschehene[ms]|Ungeschehene[ms]|Böse[ms]|Gesagte[ms]|Aufregende[sm]|Ausgestelltes|'
                     'Verschiedenes|Verborgenes|Soziale[ms]|Erfundenes|Gro(ß|ss)es|Neueres|Au(ß|ss)ergewöhnliche[ms]|'
                     'Zukunftsfähige[sm]|Administrative[ms]|Beunruhigendes|Naturverträgliches|Nachhaltiges|'
                     'Verderbliche[ms]|Sinnstiftendes|Unüberlegtes|Alltägliche[sm]|Geartetes?|Allgemeines?|'
                     'Übernatürliches?|Juristisches?|Rechtliches?|Vielfältiges?|Kommunales|Wundervolles?|'
                     'Abgelaufenes|Erstere[ms]|Zweitere[ms]|Letztere[ms]|Unvermeidliches?|Fressbares?|Essbares?|'
                     'Erbrochene[sm]|Politische[sm]|Regionale[sm]|Recherchiertes|Höheres|Kleineres|Deftiges|Liebes|'
                     'Grünes|Diverses|Machbare[ms]|Nachweisbare[ms]|Zerstörtes|Öffentliches|Produktives|'
                     'Entbehrliches|Notwendiges|Sinnvolle[ms]|Bewährte[ms]|Nötiges|Erfreuliches|Frustrierendes|'
                     'Vorübergehendes|Untaugliches|Rohes|Nettes|Blödes|Unerwartetes|Lesenswerte[ms]|Geplantes|'
                     'Ungeplantes|Redaktionelles|Spezielle[ms]|Spezifische[ms]|Staatstragendes|Organisatorisches|'
                     'Übersehenes|Altbewährte[ms]|Erstaunliches|Verdächtiges|Au(ß|ss)ergewöhnliches|Ungewöhnliches|'
                     'Unerreichbare[ms]|Bezahltes|Unbezahltes|Beschämendes|Grundsätzliche[sm]|Freiheitliches|'
                     'Übrige[ms]|Ähnliche[ms]|Letztgenannte[ms]|Echtes|Unechtes|Gro(ß|ss)artige[ms]|Esoterisches|'
                     'Qualifizierte[ms]|Unqualifizierte[ms]|Grö(ß|ss)eres|Postmodernes|Unklares|Bezahlbares|'
                     'Unbezahlbares|Gemischte[ms]|Gebündelte[ms]|Lebendige[ms]|Angenommenes|Zeitgenössisches|'
                     'Geistliches|Elementare[ms]|Bitteres|Äu(ß|ss)erliches|Spannendes|Kurioses|Digitale[ms]|'
                     'Hervorgebrachte[ms]|Gewirktes|Altbekannte[ms]|Gehackte[sm]|Gewordenes|Erkennbares|'
                     'Verstörende[sm]|Versaute[ms]|Nachdenkliches|Bestehendes|Beobachtetes|Originelle[ms]|'
                     'Derartige[sm]|Schriftliches|Mündliches|Verblühte[ms]|Faszinierende[ms]|Christliches|Gute[ms]|'
                     'Böse[ms]||Folgende[ms]|Letztere[ms]|Erstere[ms]|Schreckliche[ms]|Falsche[sm]|Richtige[ms]|'
                     'Hässliche[sm]|Auswärtige[ms]|Nervige[ms]|Ätzende[ms]|Kleine[ms]|Gro(ß|ss)e[ms]|Riskante[ms]|'
                     'Li?ebenswerte[ms]|Materielle[ms]|Geglaubte[sm]|Ausgedachte[sm]|Unsagbare[sm]?|'
                     'Unverwechselbare[sm]?|[A-Z].{1,20}rechtliche[ms]?|Umfassendere[ms]|[A-ZÄÖÜ].{1,20}(liche|bare|'
                     'werte)[ms]|Signifikante[ms]|Bestialische[ms]|Delikate[sm]|Nennenswerte[ms]|Verunglimpfende[ms]|'
                     'Wichtigere[ms]|Liberale[ms]|Heilsame[ms]|Geschriebene[sm]|Besondere[sm]|Bemerkenswerte[ms]|'
                     'Ernsthafte[ms]|Unvollendete[ms]|Vollendete[ms]'),
            cs_regex('(?!(und|oder))[a-zäöü…\\.!,\\?…\\)“„"»«–\\-:;\\[\\]].*'),
        ),
        (
            # Er sucht Neues und macht …
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Dieses|Alles|Eines|Jenes|[DMSK]eines|Anderes|Eures|Unse?res|Sonstiges|Einiges|'
                             'Manches|Welches|Vieles|Solches|Studies|Eyes))[A-ZÄÖÜ].+es')
             .build()),
            cs_regex('und|oder'),
            cs_regex('(?!([a-zäöüA-ZÄÖÜ].+es)).+'),
        ),
        (
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Diesem|Allem|Einem|Jenem|[DMSK]einem|Anderem|Eurem|Unse?rem|Sonstigem|Einigem|'
                             'Manchem|Welchem|Vielem|Solchem))[A-ZÄÖÜ].+em')
             .build()),
            cs_regex('und|oder'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Diesem|Allem|Einem|Jenem|[DMSK]einem|Anderem|Eurem|Unse?rem|Sonstigem|Einigem|'
                             'Manchem|Welchem|Vielem|Solchem))[A-ZÄÖÜ].+em')
             .build()),
            cs_regex('[a-zäöü…\\.!,\\?…\\)“„"»«–\\-:;].*'),
        ),
        (
            # Already caught by SEIT_LAENGEREN
            token('seit'),
            token('Längeren'),
        ),
        (
            token('von'),
            cs_token('Nichts'),
            cs_token('zu'),
            cs_token('Nichts'),
        ),
        (
            token('aus'),
            cs_token('dem'),
            cs_token('Nichts'),
        ),
        (
            token('das'),
            cs_token('meinen'),
        ),
        (
            token('Vors'),
            token('.'),
        ),
        (
            # Immer mehr Ältere erkranken daran
            cs_regex('Ältere[rn]?|Jüngere[rn]?|Zuschauende[rn]?|Angeklagte[rn]?|Referierende[rn]?|Schlafenden?|'
                     'Moderierende[rn]?|Dunkelhäutige[rn]?|Verantwortliche[rn]?|Alleinlebende[rn]?|Verdammten?|'
                     'Alleinstehende[rn]?|Ungeübte[rn]?|Au(ß|ss)erirdische[rn]?|Berittene[rn]?|Heranwachsende[rn]?|'
                     'Ganze[sn]?|Gefangene[rn]?|Steuerpflichtige[rn]?|Geschädigte[rn]?|Heimatvertriebenen?|'
                     'Schwerverletzte[rn]?|Werbenden?|Au(ß|ss)enstehenden?|Forschenden?|Prominenten?|Pflegenden?|'
                     'Beklagten?|Geistlichen?|Pflegebedürftigen?|(Teil|Voll)zeitbeschäftigten?|Fortgeschrittenen?|'
                     'Promovierenden?|Schreibenden?|Ungeimpfte[nr]?|Geimpfte[nr]?|Tatverdächtige[nr]?|Pubertären?|'
                     'Flüchtende[nr]?|Vortragende[nr]?|Besuchenden?|Vortragenden?|Verantwortliche[rn]?|'
                     'Geflohene[rn]?|Sterbende[nr]?|Werbende[nr]?|Vortragende[nr]?|Alliierte[nr]?|Bedürftige[rn]?|'
                     'Praktizierenden?|Geisteskranke[nr]?|Religiöse[rn]?|Kleinsten?|Kleinen|Dauerarbeitslose[rn]|'
                     'Angesteckten?|Ortskundigen?|Steuerpflichtige[rn]?|Vorbehandelnden?|Gefährdeten?|Eingemachte|'
                     'Geübten?|Schwimmenden?|Tauchenden?|Anständigen?|Liebenden?|Volljährigen?|Minderjährigen?|'
                     'Zeichnungsberechtigte[rn]?|Zeichnungsbefugte[rn]?|Altbekannte[nmr]?|Hartnäckigen?|'
                     'Unerfahrenen?|Arbeitenden?|Vortragende[nr]?|Dummen?|Fragenden?|Antwortenden?|'
                     'Kriegs[gb]eschädigten?|Begünstigten?|Verfolgten?|Verwitweten?|Geschiedenen?|Asexuellen?|'
                     'Liebsten?|(Rechts|Links)extremen?|(Aus|Ein)geschlossenen?|Betuchten?|Anteilnehmende[rn]?|'
                     'Anbietenden?|Hochbetagten?|Seelenverwandte[nr]?|Gleichgestellten?|Gottlosen?|Inhaftierten?|'
                     'Protestierenden?|Wohnungssuchenden?|Lesenden?|Schreibenden?|Beitragenden?|Superreichen?|Au(ß|'
                     'ss)enstehenden?|Juryvorsitzende[rn]?|Introvertierten?|Extrovertierten?|.+begeisterten?|(Schwer|'
                     'Seh)behinderten?|Unbekannten?|Anwesenden?|Personalverantwortlichen?|[NF]rühgeborenen?|'
                     'Hörgeschädigten?|Gehorsamen?|Ungehorsamen?|Suchtkranken?|Bildbetrachtenden?|Uniformierten?|'
                     'Bediensteten?|Gesetzlosen?|Vermummten?|(Schwer|Leicht)verletzten?|Untoten?|Hübschen?|'
                     'Reisende[rn]?|Abtrünnigen?|Liebende[nr]?|Befehlenden?|Pubertierende[rn]?|Lebenden?|'
                     'Geistliche[rn]?|Klassenbeste[rn]?|Totgesagte[rn]?|Zivildienstleistende[rn]?|Nutzenden?|'
                     'Kunstinteressierte[rn]?|Nachtaktive[nr]?|Bewerbenden?|Geliebter?|Unsterblichen?|Sterblichen?|'
                     'Evangelikalen?|Gewaltbereiten?|Dozierenden?|Autofahenden?|Impfgeschädigten?|'
                     '[A-ZÄÖÜ].+stämmigen?|Auszubildende[rn]?|Unnahbaren?|Arbeitgebenden?|Nutzungsberechtigte[nr]?|'
                     'Interviewte[rn]?|Bewohnenden?|Zugewanderte[rn]?|Eingeweihte[rn]?|Heimatvertriebene[nr]?|'
                     'Asylberechtigte[rn]?|Erwachte[rn]?|Kulturschaffende[rn]?|Gebärenden?|Beschenkte[rn]?|'
                     'Ungelernten?|Verbrauchende[rn]?|Schwule[rn]?|Partywütige[rn]?|(Homo|Hetero|Metro|'
                     'Trans)sexuelle[rn]?|Geduldige[rn]?|Ungeduldige[rn]?|Schneebegeisterte[rn]?|Befindlichen?|'
                     'Gebietsansässigen?|Erneuerbaren?|Militärinternierte[rn]?|Steuerpflichtige[nr]?|Ungläubige[rn]?|'
                     'Geduldigen?|Ungeduldigen?|Unerreichbaren?|Schuldige[rn]?|Alleinschuldige[rn]?|Getreuen?|'
                     'Mitschuldige[rn]?|Auswärtige[rn]?|[A-ZÄÖÜ].+schaffende[rn]|Übergewichtige[rn]?|'
                     'Schichtarbeitende[rn]?|Unbefugte[rn]?|Nominierte[rn]?|Erholungsuchende[rn]?|Getriebene[rn]?|'
                     'Vertriebene[rn]?|Unverwechselbaren?|Anständigen?|Zeitreisende[rn]?|Gefallene[rn]?|'
                     'Angereiste[rn]?|Liberale[rn]?|Geflüchtete[rn]?|Beratende[rn]?|Geborene[rn]?|Gerettete[rn]?|'
                     'Wahlberechtigte[rn]?|Unbeteiligte[rn]?|Bevorteilte[rn]?|Begeisterte[rn]?|Benachteiligte[rn]?'),
            cs_regex('(?!(und|oder))[a-zäöü…\\.!:;,\\?…\\)\\*\\(“„"»«–\\-\\[\\]].*'),
        ),
        (
            # wie oben, nur können die Adjektive auch als Verben gebraucht werden
            cs_regex('[a-zäöü…\\.,:;0-9\\/$%].*'),
            cs_regex('Vertraute[nr]?|Verwirrte[rn]?|Befragte[rn]?|Beschuldigte[rn]?|Interviewten?|Engagierten?|'
                     'Beteiligte[nr]?|Verurteilte[rn]?'),
            cs_regex('(?!(und|oder))[a-zäöü…\\.!:;,\\?…\\)\\*\\(“„"»«–\\-].*'),
        ),
        (
            # Im Folgenden Kunde genannt
            token('im'),
            cs_regex('Folgenden|Nachfolgenden'),
        ),
        (
            # § 12 Die Pflichtversicherung
            cs_token('§'),
            cs_regex('\\d+[a-z]{0,2}'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # § 12.1 Die Pflichtversicherung
            cs_token('§'),
            token_regex('\\d+'),
            token('.'),
            token_regex('\\d+'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Etwas anderes Lebendiges
            cs_token('zu'),
            cs_regex('Angeboten|Gefahren|Kosten'),
        ),
        (
            # Die Gemeinde Nahe in Schleswig-Holstein
            cs_regex('Gemeinden?'),
            cs_token('Nahe'),
        ),
        (
            cs_token('Für'),
            cs_token('und'),
            cs_token('Wider'),
        ),
        (
            # Ein Haus // Eine Villa
            token('/'),
            token('/'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Ein Haus // Eine Villa
            token('<'),
            token('<'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            token('('),
            cs_regex('[!?]'),
            token(')'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Ein Haus // Eine Villa
            token('>'),
            token('>'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # [Weiterlesen]
            token('['),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Beim Hoch- und Runtertragen
            token_regex('beim|zum|im|am'),
            cs_regex('[A-ZÄÖÜ].+-'),
            cs_regex('und|oder|&|/'),
            cs_regex('[A-ZÄÖÜ].+n'),
        ),
        (
            # Ein Highlight für Klein und Groß!
            token_regex('für'),
            cs_token('Klein'),
            cs_regex('und|oder|&|/'),
            cs_token('Groß'),
        ),
        (
            cs_token('/'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Ein Highlight für Groß und Klein!
            token_regex('für'),
            cs_token('Groß'),
            cs_regex('und|oder|&|/'),
            cs_token('Klein'),
        ),
        (
            # Das sagen meine Kunden:
            pos_regex('SENT_START|PKT'),
            token('das'),
            cs_regex('sagen|beweisen|zeigen|schaffen|machen|halten|verstehen|versuchen'),
            PatternTokenBuilder().pos_regex('ADV.*').min(0).build(),
            cs_regex('[dms]eine?|eure|die|unse?re|mehrere|einige|viele|manche|sonstige|diese|solche|andere|alle|'
                     'wenige|jene|nicht|koennt?en|zwar|wird'),
        ),
        (
            # Das verstehen Deutsche eben nicht
            pos_regex('SENT_START|PKT'),
            token('das'),
            cs_regex('sagen|beweisen|zeigen|schaffen|machen|halten|verstehen|versuchen'),
            pos_regex('SUB.+ADJ'),
        ),
        (
            cs_token('das'),
            cs_regex('sieben'),
        ),
        (
            # Das belegen mehrere Studien
            token('das'),
            cs_regex('belegen'),
        ),
        (
            # (Gelächter) Das sind die …
            sent_start,
            cs_regex('\\(|\\{'),
            cs_regex('[A-ZÄÖÜ].*'),
            cs_regex('\\)|\\}'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # ,Es sind die kleinen Dinge´
            sent_start,
            token(','),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # ,Es sind die kleinen Dinge´
            token(':'),
            token(','),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # LaTeX
            sent_start,
            token('\\'),
            cs_regex('(no)?indent|item'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # [Gelächter] Das sind die …
            sent_start,
            cs_token('['),
            cs_regex('[A-ZÄÖÜ].*'),
            cs_token(']'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # 22:30 Das sind die …
            sent_start,
            cs_regex('\\d+'),
            cs_token(':'),
            cs_regex('\\d+'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # 12:00 - 12:30 Gemeinsames Mittagessen
            sent_start,
            cs_regex('\\d+'),
            cs_token(':'),
            cs_regex('\\d+'),
            cs_regex('[\\-–]'),
            cs_regex('\\d+'),
            cs_token(':'),
            cs_regex('\\d+'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # (22:30) Das sind die …
            sent_start,
            cs_regex('\\(|\\['),
            cs_regex('\\d+'),
            cs_token(':'),
            cs_regex('\\d+'),
            cs_regex('\\)|\\]'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # Teil 1: Die Götter
            sent_start,
            cs_token('Teil'),
            cs_regex('\\d+|I{1,3}|V|IV|VI{1,3}|IX|XI{1,3}'),
            cs_token(':'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # ... ist das neue Normal.
            cs_token('das'),
            cs_token('neue'),
            cs_token('Normal'),
        ),
        (
            # siehe hierzu: Argentinisches Antarktisterritorium
            cs_token('siehe'),
            cs_token('hierzu'),
            cs_token(':'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # ... des vierten Offiziellen …
            cs_regex('de[mrs]'),
            cs_regex('vierten?'),
            cs_regex('Offiziellen?'),
        ),
        (
            # Auf \foo{Weiter} klicken
            cs_regex('[\\{\\[#]'),
            cs_regex('[A-ZÄÖÜ].*'),
        ),
        (
            # Hallo, Kleines, wie geht es dir?
            token(','),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*NEU.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('[A-ZÄÖÜ].+es?')
             .build()),
            token(','),
        ),
        (
            # Es gibt mehr Neues
            cs_regex('mehr|weniger|viel|nur'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*NEU.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Eines|Keines|Sonstiges|Anderes|Einiges))[A-ZÄÖÜ].+es')
             .build()),
        ),
        (
            # Bei der Fülle an Vorgaben kann das schnell vergessen werden.
            cs_token('das'),
            cs_regex('halt|schnell|gar|sicher|bitte|gleich'),
            pos_regex('VER:INF.*'),
        ),
        (
            # Dass du dir das gönnen tust
            cs_token('das'),
            pos_regex('VER:INF.*'),
            PatternTokenBuilder().token('tun').match_inflected_forms().build(),
        ),
        (
            # Über das Gesagte Gedanken machen
            # Und das Vergangene Revue passieren lassen
            cs_regex('das|dieses|[dmsk]ein'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*NEU.*ADJ|(ADJ|PA[12]).*SIN.*NEU.*|UNKNOWN')
             .cs_token_regex('(?!(Die|Diese|Alle|Eine|Jene|[DMSK]eine|Andere|Eure|Unse?re|Sonstige|Einige|Manche|'
                             'Ohne|Welche|Viele|Solche))[A-ZÄÖÜ].+e')
             .build()),
            pos_regex('SUB.*PLU.*(FEM|NEU|MAS|NOG)|SUB.*NOM.*SIN.*FEM'),
        ),
        (
            # Während der Befragte Geschichten erzählte
            cs_regex('der|dieser|[msdk]ein|euer|unser|ihr'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Die|Diese|Alle|Eine|Jene|[DMSK]eine|Andere|Eure|Unse?re|Sonstige|Einige|Manche|'
                             'Ohne|Welche|Viele|Solche))[A-ZÄÖÜ].+e')
             .build()),
            pos_regex('SUB.*PLU.*(FEM|NEU|MAS|NOG)'),
        ),
        (
            # Während des Hochwassers den Eingeschlossenen Wasser und Nahrung bringen
            cs_regex('den|diesen|[msdk]einen|unse?ren|euren|ihren'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Den|Diesen|Allen|Einen|Jenen|[DMSK]einen|Anderen|Euren|Unse?ren|Sonstigen|Einigen|'
                             'Manchen|Welchen|Vielen|Solchen))[A-ZÄÖÜ].+en')
             .build()),
            pos_regex('SUB.*NOM.*SIN.*(FEM|NEU)'),
        ),
        (
            # sind dem Zahlungspflichtigen Kosten entstanden
            cs_regex('dem|diesem|[msdk]einem|unse?rem|eurem|ihrem'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Den|Diesen|Allen|Einen|Jenen|[DMSK]einen|Anderen|Euren|Unse?ren|Sonstigen|Einigen|'
                             'Manchen|Welchen|Vielen|Solchen))[A-ZÄÖÜ].+en')
             .build()),
            (PatternTokenBuilder()
             .pos_regex_with_string_exception('SUB.*PLU.*(FEM|NEU|MAS|NOG)', 'Band|Kapitel|Maß|.*[Vv]erbrechen|'
                                                                             'Orchester|Gestalten|Gebirge|'
                                                                             '.*[vV]orkommen|.*[Vv]erfahren|'
                                                                             '.*[gG]utachten|Schreiben|Bayern|'
                                                                             'Theater|Verlangen|.*[sS]chlüssel|'
                                                                             '.*[mM]eister|.*[vV]erhalten|'
                                                                             '.*[Aa]benteuer|.*[wW]asser|Leben|Bauen|'
                                                                             '.*[gG]ewerbe|.*[Zz]immer|.*[Ee]ssen|'
                                                                             '.*[rR]asen|.*[hH]ebel|.*[oO]pfer|'
                                                                             '.*[cC]hirurgen|.*[Pp]räsidenten|'
                                                                             '.*[kK]reuzer|.*[wW]appen|Morgen')
             .build()),
        ),
        (
            # Dann hätten die Aufständischen Oberhand gewonnen
            cs_regex('die|diese|alle|solche|einige|sonstige|viele|[msdk]eine|unse?re|eure|ihre'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Den|Diesen|Allen|Einen|Jenen|[DMSK]einen|Anderen|Euren|Unse?ren|Sonstigen|Einigen|'
                             'Manchen|Welchen|Vielen|Solchen))[A-ZÄÖÜ].+en')
             .build()),
            PatternTokenBuilder().pos_regex('SUB.*SIN.*FEM').build(),
        ),
        (
            # Während ein Befragter Geschichten erzählte
            # für welche ein Befragter Geld ausgegeben hat
            cs_regex('[msdk]?ein'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Der|Dieser|Aller|Einer|Jener|[DMSK]einer|Anderer|Eurer|Unse?rer|Sonstiger|Einiger|'
                             'Mancher|Welcher|Vieler|Solcher))[A-ZÄÖÜ].+er')
             .build()),
            (PatternTokenBuilder()
             .pos_regex_with_string_exception('SUB.*PLU.*(FEM|NEU|MAS|NOG)|SUB.*SIN.*(NEU|FEM)', 'Tag|Kalkül')
             .build()),
        ),
        (
            # Während die Besagte Geld verdiente
            # Während die Besagte Geschichten erzählte
            cs_regex('die|diese|[msdk]eine'),
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Die|Diese|Alle|Eine|Jene|[DMSK]eine|Andere|Eure|Unse?re|Sonstige|Einige|Manche|'
                             'Ohne|Welche|Viele|Solche))[A-ZÄÖÜ].+e')
             .build()),
            pos_regex('SUB.*NOM.*SIN.*(MAS|NEU)|SUB.*NOM.*PLU.*(FEM|NEU|MAS|NOG)'),
        ),
        (
            # Mit Gesagtem Geschichten schreiben
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Diesem|Allem|Einem|Jenem|[DMSK]einem|Anderem|Eurem|Unse?rem|Sonstigem|Einigem|'
                             'Manchem|Welchem|Vielem|Solchem))[A-ZÄÖÜ].+em')
             .build()),
            pos_regex('SUB.*SIN.*FEM|SUB.*PLU.*(FEM|NEU|MAS|NOG)'),
        ),
        (
            # Während Besagtes Probleme verursacht
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*ADJ|(ADJ|PA[12]).*SIN.*|UNKNOWN')
             .cs_token_regex('(?!(Dieses|Alles|Eines|Jenes|[DMSK]eines|Anderes|Eures|Unse?res|Sonstiges|Einiges|'
                             'Manches|Welches|Vieles|Solches))[A-ZÄÖÜ].+es')
             .build()),
            (PatternTokenBuilder()
             .pos_regex_with_string_exception('SUB.*SIN.*(FEM|MAS)|SUB.*PLU.*(FEM|NEU|MAS|NOG)', 'Band|Kapitel|Maß|'
                                                                                                 '.*[Vv]erbrechen|'
                                                                                                 'Orchester|'
                                                                                                 'Gestalten|Gebirge|'
                                                                                                 '.*[vV]orkommen|'
                                                                                                 '.*[Vv]erfahren|'
                                                                                                 '.*[gG]utachten|'
                                                                                                 'Schreiben|Bayern|'
                                                                                                 'Theater|Verlangen|'
                                                                                                 '.*[sS]chlüssel|'
                                                                                                 '.*[mM]eister|'
                                                                                                 '.*[vV]erhalten|'
                                                                                                 '.*[Aa]benteuer|'
                                                                                                 '.*[wW]asser|Leben|'
                                                                                                 'Bauen|.*[gG]ewerbe|'
                                                                                                 '.*[Zz]immer|'
                                                                                                 '.*[Ee]ssen|'
                                                                                                 '.*[rR]asen|'
                                                                                                 '.*[hH]ebel|'
                                                                                                 '.*[oO]pfer|'
                                                                                                 '.*[cC]hirurgen|'
                                                                                                 '.*[Pp]räsidenten|'
                                                                                                 '.*[kK]reuzer|'
                                                                                                 '.*[wW]appen|Morgen')
             .build()),
        ),
        (
            # Hashtags
            token('#'),
            PatternTokenBuilder().token_regex('[A-Z].*').set_is_white_space_before(False).build(),
        ),
        (
            # Jetzt, wo Protestierende und Politiker sich streiten
            (PatternTokenBuilder()
             .pos_regex('SUB.*SIN.*NEU.*ADJ|(ADJ|PA[12]).*SIN.*NEU.*|UNKNOWN')
             .cs_token_regex('(?!(Die|Diese|Alle|Eine|Jene|[DMSK]eine|Andere|Eure|Unse?re|Sonstige|Einige|Manche|'
                             'Ohne|Welche|Viele|Solche))[A-ZÄÖÜ].+e')
             .build()),
            cs_regex('und|oder|&'),
            pos_regex('SUB.*NOM.*PLU.*(MAS|FEM|NEU|NOG)'),
        ),
        (
            # Hier ist Text. (Und dann schreibe ich etwas in Klammern.) Nach der Klammer möchte LT klein
            # weiterschreiben.
            cs_token('.'),
            cs_token(')'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # Wenn Sie Strg+Umschalt+I drücken
            cs_regex('Strg|STRG|Alt|ALT'),
            cs_regex('und|&|oder|\\+'),
            cs_token('Umschalt'),
        ),
        (
            # Wenn Sie Strg+Umschalt+I drücken
            cs_token('Umschalt'),
            cs_regex('und|&|oder|\\+'),
        ),
        (
            cs_regex('[Ii]m'),
            cs_regex('Inneren|Äu(ss|ß)eren'),
        ),
        (
            # denke aber, dass die das machen werden.
            cs_regex('ob|dass|weswegen|damit|sofern|wie|wann|wo|wozu|warum'),
            cs_regex('wir|[Ss]ie|ich|er|die|der|es|du|ihr'),
            cs_token('das'),
            pos_regex('VER:INF.*'),
        ),
        (
            pos_regex('KON.*'),
            cs_regex('wir|[Ss]ie|ich|er|die|der|es|du|ihr'),
            cs_token('das'),
            pos_regex('VER:INF.*'),
        ),
        (
            cs_regex('ob|dass|weswegen|damit|sofern|wie|wann|wo|wozu|warum'),
            pos_regex('EIG.*|UNKNOWN'),
            cs_token('das'),
            pos_regex('VER:INF.*'),
        ),
        (
            pos_regex('KON.*'),
            pos_regex('EIG.*|UNKNOWN'),
            cs_token('das'),
            pos_regex('VER:INF.*'),
        ),
        (
            # Filme drehen muss mir Spaß machen, und das machen Organisation, Finanzierung, Logistik
            # nicht, deswegen sind meine Filme nicht aufwändig.
            cs_regex('und|oder|&'),
            cs_token('das'),
            pos_regex('VER:INF.*'),
            pos_regex('SUB.*'),
        ),
        (
            # Ich würde ihn dann im Februar mal nach Potsdam schicken, damit die beiden das planen/entwickeln können.
            cs_token('das'),
            pos_regex('VER:INF.*'),
            cs_regex('und|oder|&|beziehungsweise|/|\\+'),
            pos_regex('VER:INF.*|UNKNOWN'),
            pos_regex('VER:(MOD|AUX).*'),
        ),
        (
            # Majid ergänzte: ”Vorläufigen Analysen der Terrakottaröhren aus Ardais liegen ...
            cs_token(':'),
            cs_regex('["”„»«]'),
            cs_regex('[A-ZÄÖÜ].+'),
        ),
        (
            # "gibt ja auch viele Nutzer, die sich das wünschen"
            cs_regex('die|welche'),
            cs_token('sich'),
            cs_token('das'),
            pos_regex('VER:INF.*'),
        ),
        (
            cs_regex('Bolivarische[mnrs]?'),
            cs_regex('Republik(en)?|Verfassung(en)?|Revolution(en)?'),
        ),
        (
            cs_regex('Harmonisierte[mnr]?'),
            cs_regex('Verbraucherpreisindex(e[sn]?)?'),
        ),
        (
            cs_regex('Gro(ss|ß)e[n]?'),
            cs_regex('Koalition(en?)?'),
        ),
        (
            cs_token('Oval'),
            cs_regex('Offices?'),
        ),
        (
            # "Er studierte an der Hebräischen Universität Jerusalem."
            cs_regex('Hebräischen?'),
            cs_regex('Universität|Bibel'),
        ),
        (
            # "Es wurde 1784 in das Allgemeine Krankenspital umgewandelt."
            cs_regex('Allgemeine[ns]?'),
            cs_regex('Kranken(spitale?s?|haus(es)?)?'),
        ),
        (
            cs_regex('[A-ZÄÖÜ].+stereotypen?'),
        ),
        (
            # Allerdings gibt es im Französischen und im Spanischen Ausnahmen.
            cs_token('im'),
            cs_regex('(Afrikanisch|Alt(arabisch|chinesisch|griechisch|persisch)|Amerikanisch|Arabisch|Chinesisch|'
                     'Dänisch|Deutsch|Plattdeutsch|Englisch|Finnisch|Französisch|Frühneuhochdeutsch|Germanisch|'
                     'Griechisch|Hocharabisch|Hochchinesisch|Hochdeutsch|Holländisch|Italienisch|Japanisch|Jiddisch|'
                     'Jugoslawisch|Koreanisch|Kroatisch|Lateinisch|Luxemburgisch|Mittelhochdeutsch|Neuhochdeutsch|'
                     'Niederländisch|Norwegisch|Persisch|Polnisch|Portugiesisch|Russisch|Schwedisch|Schweizerisch|'
                     'Semitisch|Serbisch|Serbokroatisch|Slawisch|Spanisch|Tschechisch|Türkisch|Ukrainisch|Ungarisch|'
                     'Wei[sß]russisch|Hebräisch|Katalanisch)en'),
        ),
        (
            # Aljos Farjon unterscheidet folgende Arten: die Europäische Eibe, Pazifische Eibe,
            # Kanadische Eibe und Chinesische Eibe.
            cs_regex('Pazifischen?|Chinesischen?|Europäischen?|Kanadischen?'),
            cs_regex('Eiben?'),
        ),
        (
            # für sein Werk Die Nächte des großen Jägers
            cs_regex('sein(e[nrs]?)?|ihr(e[nrs]?)?|das|des|die|den|der'),
            cs_regex('.*werks?|.*werke[sn]?|.*films?|.*filme[sn]?'),
            cs_regex('Der|Die|Das'),
        ),
        (
            # Jedenfalls schien das einigen völlig neu.
            cs_token('das'),
            cs_token('einigen'),
        ),
        (
            # ... schon gar nicht für Investorenträume das finden gerade die jüngeren, ...
            cs_regex('das|Das'),
            cs_token('finden'),
        ),
        (
            # Ich habe Tom das machen sehen.
            cs_token('das'),
            cs_token('machen'),
            cs_regex('sehen|gesehen'),
        ),
        (
            # Das bestätigen andere Praktikanten, die ihre Erfahrungen im Internet weitergeben.
            cs_regex('Das|das'),
            pos_regex('VER:[13]:PLU.*'),
            pos_regex('(PRO|SUB).*'),
        ),
    )
