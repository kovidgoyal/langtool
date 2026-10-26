"""Port of org.languagetool.rules.de.GermanSpellerRule,
AustrianGermanSpellerRule, SwissGermanSpellerRule and
MorfologikGermanyGermanSpellerRule.

Spell checking is not part of the rules of the German languages here (spell
checking rules are excluded from the port), but the GermanSpellerRule is the
default spelling rule of German (Language.get_default_spelling_rule(): the
GermanSpellerRule for de and de-DE, AustrianGermanSpellerRule for de-AT,
SwissGermanSpellerRule for de-CH), which many German rules and filters ask
whether a word is misspelled (is_misspelled(word)), for suggestions
(get_suggestions(word)) or for the spelling errors of a sentence
(match(sentence), e.g. PotentialCompoundFilter).

Words are checked with Hunspell (langtool.hunspell, the dictionaries
de/hunspell/de_DE|de_AT|de_CH.dic/.aff) and the word lists spelling.txt,
spelling_custom.txt, spelling-de-AT.txt/spelling-de-CH.txt, ignore.txt,
prohibit.txt and prohibit_custom.txt (all downloaded, see
dictionaries.json); suggestions come from the morfologik speller
dictionary de/hunspell/de_DE.dict plus the plain text word lists (as in
CompoundAwareHunspellRule). As in Java, the language "de" (German without
country) has no dictionary (de_LU.dic doesn't exist): its spelling rule
only finds prohibited words.
"""

import threading

from ... import jregex
from ...analysis import AnalyzedToken
from ...hunspell_rule import CompoundAwareHunspellRule, HIGH_CONFIDENCE, load_words, read_lines, resource_file
from ...rules.base import SuggestedReplacement
from ...tools import (char_to_lower, char_to_upper, is_all_uppercase, is_lower_case, is_upper_case,
                      java_equals_ignore_case, java_split, lowercase_first_char, starts_with_lowercase,
                      starts_with_uppercase, uppercase_first_char)
from .german_tools import is_vowel
from .line_expander import LineExpander
from . import spelling_data

RULE_ID = 'GERMAN_SPELLER_RULE'

# --- the patterns of GermanSpellerRule ---

MIN_WORD_LENGTH = 5
MAX_WORD_LENGTH = 40
MAX_EDIT_DISTANCE = 2
_adjSuffix = '(affin|basiert|konform|widrig|fähig|haltig|bedingt|gerecht|würdig|relevant|übergreifend|tauglich|untauglich|artig|bezogen|orientiert|fremd|liebend|hassend|bildend|hemmend|abhängig|zentriert|förmig|mäßig|pflichtig|ähnlich|spezifisch|verträglich|technisch|typisch|frei|arm|freundlich|feindlich|gemäß|neutral|seitig|begeistert|geeignet|ungeeignet|berechtigt|sicher|süchtig|resistent|verachtend|schädigend)'
_missingAdjPattern = jregex.compile('[a-zöäüß]{3,25}(affin|basiert|konform|widrig|fähig|haltig|bedingt|gerecht|würdig|relevant|übergreifend|tauglich|untauglich|artig|bezogen|orientiert|fremd|liebend|hassend|bildend|hemmend|abhängig|zentriert|förmig|mäßig|pflichtig|ähnlich|spezifisch|verträglich|technisch|typisch|frei|arm|freundlich|feindlich|gemäß|neutral|seitig|begeistert|geeignet|ungeeignet|berechtigt|sicher|süchtig|resistent|verachtend|schädigend)(er|es|en|em|e)?')
_compoundPatternWithHeit = jregex.compile('.*(heit|keit|ion|ität|schaft|ung|tät)s')
_compoundPatternWithAction = jregex.compile('Action|Session|Champion|Jung|Wahrung')
_compoundPatternWithFirst = jregex.compile('First|Firsten')
_compoundPatternSpecialEnding = jregex.compile('.*(mus|ss|z|ß|innen|chen)')
MAX_TOKEN_LENGTH = 200
_GENDER_STAR_PATTERN = jregex.compile('([A-ZÖÄÜ][a-zöäüß]{1,25}|[A-ZÖÄÜ]{1,10}-[A-ZÖÄÜ][a-zöäüß]{1,25})[*:_][a-zöäüß]{1,25}')
_FILE_UNDERLINE_PATTERN = jregex.compile('[a-zA-Z0-9-]{1,25}_[a-zA-Z0-9-]{1,25}\\.[a-zA-Z]{1,5}')
_MENTION_UNDERLINE_PATTERN = jregex.compile('@[a-zA-Z0-9-]{1,25}_[a-zA-Z0-9_-]{1,25}')
_FIRST_UPPER_CASE = jregex.compile('[A-ZÖÄÜ][a-zöäüß-]+')
_HYPHENED_UPPER_WORD = jregex.compile('[A-ZÖÄÜ][a-zöäüß]+-[\\\\-\\\\s]?[a-zöäüß]+')
_HYPHENED_WORD = jregex.compile('[a-zöäüß]+-[\\-\\s][A-ZÖÄÜa-zöäüß]+')
_START_WITH_SPIEL = jregex.compile('Spielzugs?|Spielzugangs?|Spielzuganges|Spielzugbuchs?|Spielzugbüchern?|Spielzuges|Spielzugverluste?|Spielzugverluste[ns]')
_END_WITH_SCHAFTE = jregex.compile('[A-ZÖÄÜ][a-zöäß-]+schafte')
_WORD_WITH_PUNCT = jregex.compile('\\w\\p{Punct}?')
_LOWER_CASE_WORD = jregex.compile('[a-zöäü]-.+')
_SPECIAL_CASE = jregex.compile('.{3,25}(tum|ing|ling|heit|keit|schaft|ung|ion|tät|at|um)')
_SPECIAL_CASE_WITH_S = jregex.compile('.{3,25}(tum|ing|ling|heit|keit|schaft|ung|ion|tät|at|um)s')
_AUTENTISCH_WITH_CASES = jregex.compile('[Aa]utentisch(e[nmsr]?|ste[nmsr]?|ere[nmsr]?)?')
_SYMPHATISCH = jregex.compile('symphatisch(e[nmsr]?|ste[nmsr]?|ere[nmsr]?)?')
_BRILLIANT_WITH_CASES = jregex.compile('brilliant(e[nmsr]?|ere[nmsr]?|este[nmsr]?)?')
_RECHTMASIG_WITH_CASES = jregex.compile('rechtmässig(e[nmsr]?|ere[nmsr]?|ste[nmsr]?)?')
_HOLZ_SPIEGEL_PANEL_COMPOUND = jregex.compile('(Holz|Spiegel)panel(s|en?)?')
_SBHAN_PREFIX = jregex.compile('SBahn(en|hofs?|zug(e?s)?|zügen?|höfen?|netz(e[ns]?)?|tunnel[sn]?|linien?)?')
_UBAHN_PREFIX = jregex.compile('UBahn(en|hofs?|zug(e?s)?|zügen?|höfen?|netz(e[ns]?)?|tunnel[sn]?|linien?)?')
_SCHAF_PATTERN = jregex.compile('.{3,}schaf(s|en)?')
_SCHAFE_PATTERN = jregex.compile('(Alpenschaf|Berberschaf|Bergschaf|Blauschaf|Brillenschaf|Dachsteinschaf|Deichschaf|Dickhornschaf|Feinwollschaf|Fettschwanzschaf|Fleischschaf|Fuchsschaf|Glücksschaf|Hausschaf|Jungschaf|Karakulschaf|Klonschaf|Merinoschaf|Milchschaf|Mondschaf|Nutzschaf|Rhönschaf|Riesenwildschaf|Schaukelschaf|Schneeschaf|Steinschaf|Steppenschaf|Superschaf|Waldschaf|Weideschaf|Wildschaf|Wollschaf|Zackelschaf|Zuchtschaf|Zwergblauschaf)(s|en)?')
_START_WITH_NEGER = jregex.compile('neger.*')
_CONTAINS_NEGER = jregex.compile('.+neger(s|n|in|innen)?.+')
_CONTAINS_NEGER_2 = jregex.compile('.+-neger(s|n|in|innen)?-.+')
_CONTAINS_UNCOMMON_LOWERCASED_NOUN_AT_BEGINNING = jregex.compile('^(hunger|zeit|käse|zwiebel|kommoden?|lager|angst|freund|feind)\\s.+')
_CONTAINS_UNCOMMON_LOWERCASED_NOUN_AT_END = jregex.compile('.+\\s(hunger|zeit|käse|zwiebel|kommoden?|lager|angst|freund|feind)$')
_ENDS_WITH_IBELKEIT_IBLICHKEIT = jregex.compile('.*ibel[hk]eit$')
_ALLMAHLLIG = jregex.compile('[aA]llmähll?i(g|ch)(e[mnrs]?)?')
_CONTAINS_MAYONNAISE = jregex.compile('.*[mM]a[jy]onn?[äe]se.*')
_CONTAINS_MASZNAME = jregex.compile('.*[mM]a(ss|ß)namen?.*')
_CONTAINS_RESERVIERUNG = jregex.compile('.*[rR]es(a|er)[vw]i[he]?rung(en)?')
_STARTS_WITH_RESCHASCHIER = jregex.compile('[rR]eschaschier.+')
_ENDS_WITH_LABORANTS = jregex.compile('.*[lL]aborants$')
_PROFESSIONELL = jregex.compile('[pP]roff?ess?ion([äe])h?ll?(e[mnrs]?)?')
_VERSTANDNIS = jregex.compile('[vV]erstehendniss?(es?)?')
_STARTS_WITH_DIAGNOSZIER = jregex.compile('diagno[sz]ier.*')
_STARTING_WITH_SINGLE_CHAR = jregex.compile('\\p{L} \\p{L}+')
_SPECIAL_CASE_THIRD = jregex.compile('[A-ZÖÄÜ][a-zöäüß]{2,}(ei|öl)$')
_ZB = jregex.compile('z[bB]')
_STARTS_WITH_ZB = jregex.compile('z[bB].')
_DIRECTION = jregex.compile('nord|ost|süd|west')
_WOCHENTAGE = jregex.compile('Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag')
_WOCHENTAGE_S = jregex.compile('(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)s')
_CAMEL_CASE = jregex.compile('.*(\\p{Ll}\\p{Lu}|\\p{Lu}{2,}\\p{Ll}).*')
_COMPOUND_TYPOS = jregex.compile('([Ee]mail|[Ii]reland|[Kk]reissaal|[Mm]akeup|[Ss]tandart).*')
_COMPOUND_END_TYPOS = jregex.compile('.*(gruße|schaf(s|en)?)$')
_INFIX_S_SUFFIXES = jregex.compile('.*(heit|(s|[^c]t|x)ion|ität|keit|ling|ung|schaft|tum)$')
_WECHSELINFIX = jregex.compile('(arbeit|dienstag|donnerstag|freitag|montag|mittwoch|link|recht|samstag|sonntag|verband)s?')
_CONFUSED_PREFIXES = jregex.compile('bach|bade?|wi(e)?der')
_NEEDS_TO_BE_PLURAL = jregex.compile('absolvent(in)?|adressat|aktie|antenne|apache|arbeitnehmer(in)?|ärztin|assistent(in)?|astronom(in)?|asylant(in)?|autor(in)?|azteke|bakterie|ballade|bauer|billion|bisexuelle|blume|bonze|börse|bot(e|in)|buche|bürg(e|in)|bürokrat(in)?|chrysantheme|dän(e|in)?|debatte|debitor(in)?|decke|diakon(in)?|diktator(in)?|direktor(in)?|doktorand(in)?|domäne|dozent(in)?|drohne|druid(e|in)?|düne|ehre|eibe|elefant|elektron|ellipse|emittent(in)?|elfe|elle|enge|erbse|eremit|erde|erste|esche|exot(e|in)?|expert(e|in)?|extremist(in)?|fabrikant(in)?|falke|fassade|farbe|fasan|favorit(in)?|felge|ferien|figur|fluor|frage|franz(ose|ösin)|frau|frisur|förde|galle|gatt(e|in)?|gerät|gepard|gezeit|gigant|gilde|göttin|griech(e|in)?|halt|heid(e|in)?|herde|historie|hölle|höhle|hose|hugenott(e|in)?|hund|hündin|immigrant(in)?|investor(in)?|irokes(e|in)|islamist(in)?|jesuit(in)?|jungfer|jungfrau|junggesell(e|in)|juror(in)?|kadett|kante|kaskade|kathode|katholik(in)?|katze|kette|kid|klasse|kirche|klaue|klient(in)?|klinge|knappe|koeffizient|kojote|komet|kommentator(in)?|komödie|kompliz(e|in)|konkurrent(in)?|konfirmand(in)?|konsonant|kontrahent(in)?|krake|kralle|kranke|krähe|kraut|krippe|kurd(e|in)|kuriosität|kurve|kusine|küste|laie|laterne|laute|legende|lehne|leise|lektor(in)?|leopard|lerche|leserin|lieferant(in)?|lippe|loge|lotse|länge|läuse|löwe|lücke|luke|made|mädel|maske|maßnahme|matriarchin|menge|mensch|metapher|methode|metropole|miene|miete|migrant(in)?|million|mitte|maus|moderator(in)?|monarch(in)?|mongol(e|in)|mormone|mücke|mühle|musikant(in)?|mysterium|nerv|niederlage|nixe|nonne|note|obdachlose|ode|organist|panne|papagei|parzelle|pastor(in)?|pate|patient|patriarch(in)?|petze|pfadfinderin|pfanne|pfaffe|pfau|pfeife|platte|polle|pomade|pomeranze|posse|praktikant(in)?|prinz(essin)?|prise|produzent(in)?|prominente|prophet(in)?|prototyp|prälat|psychopath(in)?|puppe|pädophile|pygmäe|rabe|radikale|rakete|rampe|ranke|rassist(in)?|rate|raupe|rendite|repressalie|rest|riese|rinde|rind|robbe|robe|romanist|rose|ross|route|nummer|runde|russ(e|in)?|röhre|rübe|salbe|schabe|schale|scheide|schelle|schenke|schere|sphäre|dicke|kröte|schauspielerin|schimpans(e|in)|schlampe|schlange|schluchte|schmiere|schnake|schnalle|schneide|schnelle|schokolade|schotte|schurke|schwabe|schwalbe|schwede|schwule|seele|seide|seite|senator(in)?|serb(e|in)?|serie|silbe|skulptur|sonne|sorge|sorte|spanne|sparte|spatz|sperre|spitze|sproße|spule|stalaktit|steppe|straße|streife|studie|stunde|stütze|tabelle|therapeut(in)?|tinte|tote|toilette|torte|traube|treffe|treppe|truhe|träne|tunte|tüte|tyrann|urne|utensil|vandal(e|in)|vasall(in)?|vene|versicherte|verwandte|veteran(in)?|virtuose|vorname|waffe|wanne|ware|watte|wehe|welle|welpe|wiese|wirtin|zar(in)?|zentrum|zutat')
_SUBNOMPLUFEM_EXCEPTIONS = jregex.compile('.+(atie|lyse|metrie|sophie|omie)|absage|accessoire|allergie|analogie|anästhesie|anatomie|anomalie|archäologie|aufnahme|balance|barriere|batterie|creme|deponie|dürre|einlage|energie|folklore|franchise|gemeinde|glu[ck]ose|gülle|hanse|hefe|hirse|infanterie|kolonie|kontrolle|lounge|massage|mathe|melodie|nässe|parfümerie|pharmazie|pflege|pipeline|poesie|psychotherapie|regie|renaissance|säure|single|sprache|spree|stärke|suche|teilnahme|theorie|therapie|vanille|wiederaufnahme|wende')
_CITIES_EXCEPTIONS = jregex.compile('bahnhof|flughafen|haupt')
_INVALID_COMP_PART_1 = jregex.compile('adresse|ahmen|kamp|kontrolle|leuchte|norden|osten|perspektive|schule|sprache|stelle|suche|süden|westen')
_INVALID_COMP_PART_2 = jregex.compile('kamp')
_SUBINF_SINGULAR_OBJECT = jregex.compile('putzen|rauchen|sein|spielen')
_ARBEIT_COMP = jregex.compile('(gebe|nehme)(r(s|n|innen|in)?|nde[mnr]?)')
_BACH_COMP = jregex.compile('aue|bett|biograph(ie|in)?|chor|forelle|gesellschaft|kantate|lauf|niederung|stelze|tal|verein')
_BAD_COMP = jregex.compile('accessoire|architektur|besitzer(in)?|design|eintritt|fenster|größe|grund|kollektion|konzept|lösung|maß|möbel|nutzer(in)?|regal|spezialist(in)?|spiegel|straße|tür|utensil')
_LINK_COMP = jregex.compile('element|inhalt|liste|portal|text|titel|tracking|verzeichnis')
_LINKS_COMP = jregex.compile('abbieger(in)?|abweichler(in)?|anwalt|anwältin|anwaltschaft|ausfall|auslage|ausleger(in)?|au(ss|ß)en|bündnis|drall|drehung|extremer?|extremis(t|tin|mus)|faschis(t|tin|mus)|fraktion|galopp|gewinde|händ(er|erin|igkeit)|hörnchen|innen|intellektueller?|katholizis(t|tin|mus)|koalition|konter|kurs|kurve|lastigkeit|lenker|nationalis(t|tin|mus)|opposition|orientierung|partei|populis(t|tin|mus)|radikal(e|er|ismus|ist|istin)|regierung|ruck|rutsch|schnitt|schuss|schwenk(ung)?|sektierer(in)?|steuerung|terror(t|tin|ismus)|verbinder(in)?|verkehr|wendung|wichser')
_PERSON_SUFFIXES = jregex.compile('.+([dlt]ant(in)?|arch(in)?|graf(in)?|gog(e|in)|([bdfghnoptuvxyz]|he|([inrt]a|o)(l)|(for|ga|i)m|[^f]r)(ist)(in)?|krat(in)?|man(e|in)|naut(in)?|olog(e|in)|(d|[pt]i|r)ent(in)?|seur(in)?|soph(in)?|tit(in)?|.+[^b]urg(in)?)$')
_RECHT_COMP = jregex.compile('bank|eck|fertigung|gläubigkeit|haber|haberei|leitung|losigkeit|mäßigkeit|winkligkeit|zeitigkeit')
_RECHTS_COMP = jregex.compile('abbieger(in)?|abteilung|akt|akte|angelegenheit|ansicht|anspruch|anwalt|anwalts|anwaltschaft|anwendung|anwältin|auffassung|aufsicht|auskunft|ausleger(in)?|ausschuss|au(ss|ß)en|begehren|begriff|behelf|beistand|berater|beratung|bereich|beschwerde|beugung|beziehung|brecher|bruch|dienst|drall|durchsetzung|empfinden|entwicklung|setzung|experte|experten|extremer?|extremis(t|tin|mus)|fall|fehler|folge|form|fortbildung|frage|fähigkeit|gebiet|gebieten|gelehrte|gelehrter|geschichte|geschäft|gewinde|gleichheit|grund|grundlage|grundsatz|gründen|gut|gutachten|gültigkeit|güter|handlung|hilfe|händ(er|erin|igkeit)|hängigkeit|inhaber|institut|katholizis(t|tin|mus)|klick|konformität|kraft|kreis|kurve|lage|lastigkeit|lehre|lenker|medizin|mediziner|meinung|missbrauch|mittel|mitteln|mängel|nachfolge|nachfolger|nachfolgerin|nationalis(t|tin|mus)|natur|norm|ordnung|persönlichkeit|pflege|pfleger|pflicht|philosophie|politik|populis(t|tin|mus)|position|praxis|problem|quelle|radikal(e|er|ismus|ist|istin)|rahmen|rat|ratgeber(in)?|ruck|rutsch|sache|sachen|satz|schutz|sicherheit|sinn|sprache|soziologie|sprechung|staat|staatlichkeit|stand|status|stellung|streit|streitigkeit|system|terroris(t|tin|ismus)|texte|texter|thema|theorie|tipp|titel|träger|unsicherheit|verfolgung|vergleichung|verhältnis|verkehr|verletzung|verletzungen|verordnung|verstoß|verständnis|verteidiger|verteidigung|vertreter|vertretung|vorschrift|wahl|weg|wesen|widrigkeit|wirksamkeit|wirkung|wissenschaft|wissenschaften|wissenschaftler|zug|änderung')
_VERBAND_COMP = jregex.compile('klammer|kasten|kiste|mull|material|päckchen|platz|raum|schere|zeug|zimmer')
_VERBANDS_COMP = jregex.compile('chef(in)?|flug|funktionär(in)?|kasse|klage|leben|leitung|leiter(in)?|ligist(in)|material|päckchen|präsident(in)?|presse|spiel|vertreter(in)|vorsitzender?|vorstand|wechsel|zeichen|zeit(schrift|ung)')
_WIDER_COMP = jregex.compile('glanz|hall|haken|klage|klang|lager|rechtliche|ruf|spiel|spruch|sehen|stand|streit|wille')
_WOCHENTAG_COMP = jregex.compile('abend|mittag|morgen|nachmittag|vormittag')
_POTENTIAL_BINNEN_I = jregex.compile('.*((?<=(\\w))In).*')
_GENDER_NEUTRAL_SPECIAL_CHRS_SIN = jregex.compile('.*[\\*:_/]in$')
_GENDER_NEUTRAL_SPECIAL_CHRS_PLU = jregex.compile('.*[\\*:_/]in.+')
_GENDER_NEUTRAL_SLASH_HYPHEN = jregex.compile('.*/-in.+')
_GENDER_STAR = jregex.compile('((?<=(\\w))In|[\\*:_]in|/-in)')
_GENDER2_STAR2 = jregex.compile('.*((?<=(\\w))In|[\\*:_]in|/-in).*')
_WECHSELNUMERUS = jregex.compile('wort|welt')
_WELTEN_COMP = jregex.compile('Brand|Bummler(in)?|Drama|Wende')
_WOERTER_COMP = jregex.compile('Buch|Liste|Verzeichnis')

_EXPAND_PATTERN = jregex.compile('.*/[ESNAPFT]')

# some of these are taken from hunspell's dictionary where non-suggested words use tag "/n":
_LC_DO_NOT_SUGGEST_WORDS = frozenset((
    "verjuden", "verjudet", "verjudeter", "verjudetes", "verjudeter", "verjudeten", "verjudetem",
    "entjuden", "entjudet", "entjudete", "entjudetes", "entjudeter", "entjudeten", "entjudetem",
    "auschwitzmythos",
    "judensippe", "judensippen",
    "judensippschaft", "judensippschaften",
    "nigger", "niggern", "niggers", "neger", "negers", "negern",
    "rassejude", "rassejuden", "rassejüdin", "rassejüdinnen",
    "möse", "mösen", "fotze", "fotzen",
    "judenfrei", "judenfreie", "judenfreier", "judenfreies", "judenfreien", "judenfreiem",
    "judenrein", "judenreine", "judenreiner", "judenreines", "judenreinen", "judenreinem",
    "judenmord", "judenmorden", "judenmörder"))

# CommonFileTypes.getSuffixPattern()
_COMMON_FILE_TYPES = (
    "jpeg", "jpg", "gif", "png", "bmp", "svg", "ai", "sketch", "ico", "ps", "psd", "tiff", "tif",
    "mp3", "wav", "midi", "mid", "aif", "mpa", "ogg", "wma", "wpl", "cda",
    "7z", "arj", "deb", "pkg", "plist", "rar", "rpm", "tar.gz", "tar", "zip",
    "bin", "dmg", "iso", "toast", "vcd", "csv", "dat", "db", "log", "mdb", "sav", "sql", "xml",
    "apk", "bat", "cgi", "com", "exe", "gadget", "jar", "py", "js", "jsx", "json", "wsf", "ts", "tsx",
    "fnt", "fon", "otf", "ttf", "woff", "woff2",
    "rb", "java", "php", "html", "asp", "aspx", "cer", "cfm", "cgi", "pl", "css", "scss", "htm", "jsp", "part", "rss",
    "xhtml",
    "key", "odp", "pps", "ppt", "pptx", "class", "cpp", "cs", "h", "sh", "swift", "vb",
    "ods", "odt", "xlr", "xls", "xlsx", "xlt", "xltx", "bak", "cab", "cfg", "cpl", "cur", "dll", "dmp", "msi", "ini",
    "tmp",
    "3g2", "3gp", "avi", "flv", "h264", "m4v", "mkv", "mov", "mp4", "mpg", "mpeg", "rm", "swf", "vob", "wmv",
    "doc", "docx", "dot", "dotx", "pdf", "rtf", "srx", "text", "tex", "wks", "wps", "wpd", "txt", "yaml", "yml", "csl",
    "md", "adm", "webm", "webp")
COMMON_FILE_TYPES_SUFFIX_PATTERN = jregex.compile(
    '[\\wáàâóòìíéèùúôîêûäöüß\\-.()]*?.+\\.(' + '|'.join(_COMMON_FILE_TYPES) + ')', jregex.IGNORECASE)

_ELATIVE_PREFIXES = ("bitter", "dunkel", "erz", "extra", "früh", "gemein", "hyper", "lau", "mega", "minder", "stock",
                     "super", "tod", "ultra", "ur")
_ELATIVE_PREFIX_PATTERN = jregex.compile(
    '^(bitter|dunkel|erz|extra|früh|gemein|grund|hyper|lau|mega|minder|stock|super|tod|ultra|ur|voll)')
_SCHAF_END = jregex.compile('schaf$')
_SCHAFS_END = jregex.compile('schafs$')
_SCHAFEN_END = jregex.compile('schafen$')
_GENDER_CHAR = jregex.compile('[*:_]')
_MITARBEITENDE = jregex.compile('mitarbeitenden?')
_BINNEN_I_IN = jregex.compile('((?<=(\\w))In)')
_GENDER_SPECIAL_IN = jregex.compile('[\\*:_/]in')
_SLASH_HYPHEN_IN = jregex.compile('/-in')
_ISCHE = jregex.compile('.+ische?[mnrs]?')
_TRAILING_DOT = jregex.compile('\\.$')
_ENDS_EL_HK_EIT = jregex.compile('el[hk]eit$')
_AQUISE_END = jregex.compile('aquise$')
_STANDART_END = jregex.compile('standart$')
_STANDARTS_END = jregex.compile('standarts$')
_TIPS_END = jregex.compile('tips$')
_OULLIE_END = jregex.compile('oullie$')
_BUNDSTIFT_START = jregex.compile('^Bundstift')
_ALLMAHLLIG_REPL = jregex.compile('llmähll?i(g|ch)')
_MAYONNAISE_REPL = jregex.compile('a[jy]onn?[äe]se')
_RESERVIERUNG_REPL = jregex.compile('es(a|er)[vw]i[he]?rung')
_TS_END = jregex.compile('ts$')
_PROFESSIONELL_REPL = jregex.compile('roff?ess?ion([äe])h?l{1,2}')
_VERSTEHENDNIS_REPL = jregex.compile('[vV]erstehendnis')
_GNOSZIER = jregex.compile('gno[sz]ier')
_DERBIES_END = jregex.compile('derbies$')
_STORIES_END = jregex.compile('stories$')
_PARTIES_END = jregex.compile('parties$')
_MASZNAME_REPL = jregex.compile('a(ss|ß)name')

_PREVENT_SUGGESTION_PATTERNS = (
    jregex.compile('.*(Majonäse|Bravur|Anschovis|Belkanto|Campagne|Frotté|Grisli|Jockei|Joga|Kalvinismus|Kanossa|Kargo|Ketschup|Kollier|Kommunikee|Masurka|Negligee|Nessessär|Poulard|Varietee|Wandalismus|kalvinist|[Ff]ick).*'),
    jregex.compile('.+[*_:]in'),
    jregex.compile('.+[*_:]innen'),
    jregex.compile('.+\\szigste[srnm]?'),
    jregex.compile('[\\wöäüÖÄÜß]+ [a-zöäüß]-[\\wöäüÖÄÜß]+'),
    jregex.compile('[\\wöäüÖÄÜß]+- [\\wöäüÖÄÜß]+'),
    jregex.compile('[A-ZÄÖÜ][a-zäöüß]+-[a-zäöüß]+-[a-zäöüß]+'),
    jregex.compile('[A-ZÄÖÜ][a-zäöüß]+- [a-zäöüßA-ZÄÖÜ\\-]+'),
    jregex.compile('[A-ZÄÖÜa-zäöüß\\-]+ [a-zäöüßA-ZÄÖÜ]-[a-zäöüßA-ZÄÖÜ\\-]+'),
    jregex.compile('[A-ZÄÖÜa-zäöüß\\-]+ [a-zäöüß\\-]+-[A-ZÄÖÜ][a-zäöüß\\-]+'),
    jregex.compile('[\\wöäüÖÄÜß]+ -[\\wöäüÖÄÜß]+'),
    jregex.compile('[A-ZÄÖÜa-zäöüß\\-]+\\.[A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß\\-]+'),
    jregex.compile('[A-ZÄÖÜa-zäöüß\\-]+\\.\\-[a-zäöüß\\-]+'),
    jregex.compile('[a-zöäüß]{3,20} [A-ZÄÖÜ][a-zäöüß]{2,20}liche[rnsm]'),
    jregex.compile('[A-ZÄÖÜ][a-zäöüß]{2,20}-[a-zäöüß]{2,20}-'),
    jregex.compile('[a-zäöüß]{3,20}-[A-ZÄÖÜ][a-zäöüß\\-]{2,20}'),
    jregex.compile('[a-zäöüß]{3,20}-[A-ZÄÖÜ\\-]{2,20}'),
    jregex.compile('([skdm]?ein|viel|sitz|sing|web|hör|woh[nl]|kehr|adel|elektiv|wert|wein|wund|wurm|wand|weg|wett|gen|hei[lm]|kenn|vo[rnm]|fein|zu[rm]?|fehl|bei|peil|eckt?|mit|die|das|ehe|für|nur|eure[rn]?|unse?re?|e[sr]|fahr|bar|fern|warn|filz|oft|fort|bot|vote|käse|we[rnm]|was|gie(ss|ß)|haut|band|heiz|merk|mehr|z[äa]hl|knie|zie[lr]|braut|brat|park|reiz|wa[rs]|wo|ma(ß|ss)|kleb|gabel|brat|rast|rang|lesen?|arm|de[rnms]|sämig|sucht?|sägen?|steh|bahn|off|uff|auf|aß|also|anno|dank|back(en?)?|bl[oi]ck|fang|klär|macht?|haken?|[lw]agen?|messe?|bad(en?)?|pack|km|ecken?|bis|tauche?|tr?age?|segeln?|stei[lg]|stahl|da(nn)?|häng(en?)?[bt]oten?|plus|tat|lade?|tasten?|druck|fach|fragen?|lern|mag|facto|magre|bald|bau(en?)?|ich|sei[dtln]|gang|angeln?|[wl]ach|bist|[ge]ilt|warten?|turn|härten?|hold|[hg]alt|holt|angle|angab|ankam|anale?)-[A-ZÄÖÜa-zäöüß\\-]+'),
    jregex.compile('.+-(gen|tu[etn]|l?ehrt?(en?)?|[fv]iele?n?|gärt?en?|igeln?|nein|ja|d?rum|erb(en?)?|vo[rnm]|vors|hat|gab(en)?|gabs?|gibt|km|geb(en?)?|nu[nr]|gay|kalt(e[snr]?)?|la[gd](en?)?|man|rängen?|nässen?|angle|angeln?|angst|stur(en?)?|oft|wo|wann|was|wer|mengen?|spie(ß|ss)en?|adeln?|näht?en?|ob|beide[rn]?|gärten|zweiten?|hütt?en?|kehrt?en?|h?orten?|messen?|tr[ea]u|trüb|trüben?|senden?|gr[uo]b|feinden?|wie|käsen?|ih[rmn](e[srnm]?)?|grau|trug(en?)?|weil|dass|sein?|zucken?|kanten?|s?ich|getan|hält|bald|ärgern?|fächern?|wart?(en?)?|leid|weit(e[snr]?)?|weiden?|ruf(en?)?|min|im|bin|zicken?|jo|siegeln?|[ao]ha|ganz|zäh|jäh|gehen?|ga[br]|kam|sah|[sr]itzen|kann|mit|ohne|ist|so|war|da[rh]in|über|unter|doof|bis|sie|er|aalen?|[lb]aden?|raten?|die|mit|bis|d[ea]s|eifern?|acker[tn]?|z[iu]cken?|j[oe]|jäh|haha|gerät|[wrbfk]etten?|tja|je|kau|nach|haben?|hab|gaga|kicken?|kick|heil|heilen?|altern?|wänden?|wert(e[rsnm]?)?|werben?|zoom|genug|gehen?|ums?|und|oder|[sn]ah|ha|de[mnsr]|sü(ß|ss)|ringen?|dingen?|seil|au[fs]|gurten?|munden?|eigen|wenden?|regen?|b?rechen?|legen?|fächern?|leger|g[ia]lt|heim|heimen?|[mksdw]?ein|[mksdw]?einen?|erden?|ändern?|ernten?|bänden?|ästen?|arten?|kanten?|eichen?|unken?|wunden?|kunden?|runden?|regeln?|kegeln?|krähen?|zechen?|mähen?|ehren?|ehen?|enden?|eng(e[srn]?)?|gut(e[srn]?)?|zielt?(en?)?|spielt?(en?)?|ätzt?(en?)?|riegeln?|segeln?|engt?|engen?|angeln?|kochen?|[lk]ehren?|festen?|essen?|steuern?|ekeln?|irren?|cum|de|da|du|raus|rein|dort|knien?|hin|zu[rm]?|ritten?|riss|rissen?|[tr]ast(en?)?|rasseln?|hieb|wässern?|putz|hängen?|zinken?|a[bnm]|bisher|schöne?|solo|haken?|dr[üu]ck(en?|tot)?|huren?|pries|hupen?|hüllen?|lang|joa|sei[dt]|weist|üben?|ufern?|iss|steck(en?)?|fort|mal|aal|darf|halt(en?)?|eifern?|van|guck(en?|t)?|ganze?|acht(en?)?|auch|solo|[zs]og|lagern?|baggern?|au|haut?|als|uns|bei[m]?|[dm]ir|dich|uni|ergo|eich(en?)?|spick(en?)?|e[rs]|spielt?|we[hg]|wart|wi[rl]d|neue[rns]?|mithin|tags?|eine[snmr]?|wiesen?|rei[sz]en?|wei[sh]en?|siegen?|sag(en?)?|sitzen?|tagen?|all(en?)?|zahlen?|rügen?|ruhen?|bar|hüben?|hick|arm|armen?|plan(en?)?|[fpl]assen?|per|reg|rinnen?|bringen?|öl(en?)?|alt(en?)?|elf(en?)?|kp|ward|apart|wer[dkt](en?)?|weis(en?)?|sind|mm|wand|wir|licht(en)?|lügen?|loch(en?)?|übel|peu|[wtm]isch(en?)?|fein(e[rns]?)?|a(ß|ss)|mol|neu(en?)?|[dm]ich|rang|obe[nr]|übe[nl]?|maxi?|hart(en?)?|hexen?|ab|zück(en?)?|zurück|köpf(en?)?|band(en?)?|schafft?en?|schalt?en?|giften?|sieben?|seil(en?)?|wehen?|sehen?|s[it]?eht?|stocken?|red|rät|ma(ß|ss)|schämen?|innen?|karren?|wer[tf]en?|werft|loch(en?)?|logen?|gossen?|steil(en?)?|fr?isch(en?)?|d[ea]nn|zelt(en?)?|luv|kauf(en?)?|lasch(en?)?|bei(ß|ss)(en?)?|leihen?|leid(en?)?|[drsl]icht(en?)?|opfern?|[wz]äh[mln]en?|wär(en?)?|À|à|fugen?|la[xs]|zahl(en?)?|[rf]all(en?)?|wichs(en?)?|sog(en?)?|alias|glich(en?)?|würd(en?)?|wärm(en?)?|[rhg]eiz(en?)?|stieren?|teils?|trotz|fahr(en?)?|b[oa]u?[dt](en?)?|kl[öo]n(en?)?|paar|park(en?)?|last|landen?|alle[rnms]?|ad|l[äa]u[ft](en?)?|[ws]äg(en?)?|pasch(en?)?|kehl(en?)?|wohl(en?)?|flucht?(en?)?|zeit|rasa|selben?|mehr(en?)?|gabeln?|ordern?|[cw]ach(en?)?|arg(en?)?|brauch(en?)?|hauch(en?)?|[ms]a(ß|ss)(en?)?|mm?h|zart(e[snmr]?)?|ehrt?(en?)?|de[rn]en|ähm?|hui|hmm?|al|für|[bl]au(en?)?|[lr]ahm(en?)?|[bs]uch(en?)?|[wv]ag(en?)?|[tl]os(en?)?|les(en?)?|str?ahl(en?)?|zäh[mn]t?(en?)?|fest(e[rsnm]?)?|folgt?(en?)?|f[aä]llt?(en?)?|[tr]oll(en?)?|[mf]üllt?(en?)?|[rl]eit(en?)?|ras(en?)?|hall(en?)?|well(en?)?|fra(ß|ss)(en)?|tat(en)?|pah|buh(en?)?|bäh|hör(en?)?|holz(en?)?|reif(e[rsmn]?)?|litt|fort(an)?|härten?|welche[rnsm]?|wegen|fach(en?)?|bog(en?)?|foul(en?)?|löst?(en?)?|lots(en?)?|falls|[bwh][ua]ldige[rsn]?|(st)?reift?(en?)?|t?rei[bh](en?)?|[rb]ück(en?)?|wett(en?)?|t[oü]t(en?)?|[ft]est(en?)?|h[aä]ut(en?)?|knall(en?)?|[dk]ämpft?(en?)?|hört?(en?)?|patt(en?)?|[tw]ollt?en?|[km]g|[bkps]ack(en?)?|[lf]an?d(en?)?|seifen?|tabu|heft(en?)?|forma?|knall(en?)?|[lm]?acht?(en)?|boot(en?)?|lach(en?)?|[hb]i?eb(en?)?|tut(en?)?|tr?öt(e[tn]?)?|[sp]ackt?(en?)?|[klnrd]?eckt?(en?)?|beut(en?)?|top|st?att(en?)?|dien(en?)?|[hl]ieb(en?)?|sät|satt(en?)?|droh(en?)?|[sr]äum(en?)?|zeugt?(en?)?|reu(en?)?|nies(en?)?|[gzf]eigt?(en?)?|gie(ß|ss)(en?)?|sichern?|zog(en?)?|schert?(en?)?|s[tp]r?ickt?(en?)?|seicht(e[srn]?)?|(be)?sorgt?(en?)?|ehelich(en?)?|link(en?)?|wein(en?)?|r?echt|orangen?|blick(en?)?|kling(en?)?|übrig(en?)?|klick(en?)?)'),
    jregex.compile('[A-ZÖÄÜa-zöäüß] .+'),
    jregex.compile('.+ [a-zöäüßA-ZÖÄÜ]'),
)

_GERMAN_INSTANCE_FILES = {}
_files_lock = threading.Lock()


def _load_file(language, file_in_classpath):
    """GermanSpellerRule.loadFile: the first ';'-separated column of the
    non-comment lines (the expansion syntaxes '/X' and '_in' are not
    supported)"""
    with _files_lock:
        r = _GERMAN_INSTANCE_FILES.get(file_in_classpath)
        if r is not None:
            return r
    s = set()
    for line in read_lines(resource_file(language, file_in_classpath)):
        if not line.startswith('#'):
            s.add(_first_col(line))
        if _EXPAND_PATTERN.fullmatch(line):
            raise RuntimeError("Syntax '/{X}' for expansion not supported in this file: '" + line + "' in "
                               + file_in_classpath)
        if line.endswith('_in'):
            raise RuntimeError("Syntax '_in' not supported in this file: '" + line + "' in " + file_in_classpath)
    r = frozenset(s)
    with _files_lock:
        _GERMAN_INSTANCE_FILES[file_in_classpath] = r
    return r


def _java_trim(s):
    from ...tools import java_trim
    return java_trim(s)


def _first_col(line):
    """line.trim().split(";")[0]"""
    parts = java_split(_java_trim(line), ';')
    return parts[0] if parts else ''


def _replace_first(pattern, s, repl):
    """String.replaceFirst"""
    return jregex.java_replace(pattern, repl, s, count=1)


def _replace_all(pattern, s, repl):
    """String.replaceAll"""
    return jregex.java_replace(pattern, repl, s)


def _replace_once(s, search, repl):
    """StringUtils.replaceOnce"""
    return s.replace(search, repl, 1)


def _remove_end(s, end):
    """StringUtils.removeEnd"""
    if s is None:
        return None
    return s[:-len(end)] if end and s.endswith(end) else s


def _capitalize(s):
    """StringUtils.capitalize (title case of the first character)"""
    if not s:
        return s
    t = s[0].title()
    return (t if len(t) == 1 else s[0]) + s[1:]


def _uncapitalize(s):
    """StringUtils.uncapitalize"""
    if not s:
        return s
    return char_to_lower(s[0]) + s[1:]


def _is_all_upper_case_commons(s):
    """StringUtils.isAllUpperCase"""
    return bool(s) and all(is_upper_case(c) for c in s)


def _is_all_lower_case_commons(s):
    """StringUtils.isAllLowerCase"""
    return bool(s) and all(is_lower_case(c) for c in s)


def _apply_suggestion_item(item, w):
    if isinstance(item, str):
        return item
    op = item[0]
    if op == 'rf':
        return _replace_first(jregex.compile(item[1]), w, item[2])
    if op == 'ro':
        return _replace_once(w, item[1], item[2])
    if op == 'ucf':
        return uppercase_first_char(_apply_suggestion_item(item[1], w))
    raise ValueError(item)


class _AdditionalSuggestions:
    """ADDITIONAL_SUGGESTIONS: the first entry whose pattern matches the
    whole word (StringMatcher.regexp) gives the suggestions. Patterns with
    a finite set of matching words are looked up in a dict."""

    def __init__(self):
        from ...patterns.string_matcher import StringMatcher, KIND_EQUALS, KIND_SET
        self.by_word = {}
        self.regex_entries = []
        self.entries = spelling_data.ADDITIONAL_SUGGESTIONS
        for i, (pattern, _items) in enumerate(self.entries):
            m = StringMatcher(pattern, True, True)
            if m.kind == KIND_EQUALS:
                self.by_word.setdefault(m.value, i)
            elif m.kind == KIND_SET:
                for v in m.possible_values:
                    self.by_word.setdefault(v, i)
            else:
                self.regex_entries.append((i, m))

    def get(self, word):
        if len(word) > 250:  # StringMatcher.MAX_MATCH_LENGTH
            return None
        best = self.by_word.get(word)
        for i, m in self.regex_entries:
            if best is not None and i > best:
                break
            if m.matches(word):
                best = i
                break
        if best is None:
            return None
        return [_apply_suggestion_item(item, word) for item in self.entries[best][1]]


_additional_suggestions = []


def _get_additional_suggestions_map():
    with _files_lock:
        if not _additional_suggestions:
            _additional_suggestions.append(_AdditionalSuggestions())
        return _additional_suggestions[0]


_splitter = []


def _get_splitter():
    """GermanSpellerRule.splitter: new GermanWordSplitter(false)"""
    with _files_lock:
        if not _splitter:
            from .compound_tokenizer import GermanWordSplitter
            _splitter.append(GermanWordSplitter(False))
        return _splitter[0]


# --- the morfologik speller (getSpeller) ---

_SPELLING_FILE_PATHS = ('/{0}/hunspell/spelling.txt', '/{0}/hunspell/spelling_custom.txt',
                        '/{0}/multitoken-suggest.txt', 'spelling_global.txt',
                        '/{0}/hunspell/spelling_recommendation.txt')
_morfo_spellers = {}
_line_expander = LineExpander()


def get_spelling_file_paths(lang_code):
    """GermanSpellerRule.getSpellingFilePaths (CompoundAwareHunspellRule's
    paths plus spelling_recommendation.txt)"""
    return [p.format(lang_code) for p in _SPELLING_FILE_PATHS]


def _expanded_plain_text_lines(text_lines):
    """MorfologikMultiSpeller.getLines for an ExpandingReader (no
    Language.prepareLineForSpeller)"""
    lines = []
    for original_line in text_lines:
        for line in _line_expander.expand_line(original_line):
            if line.startswith('#') or not line:
                continue
            parts = java_split(line, '#')
            line = _java_trim(parts[0]) if parts else ''
            if line:
                lines.append(line.encode('utf-8'))
    return lines


def get_speller(language, language_variant_plain_text_dict):
    """GermanSpellerRule.getSpeller: the morfologik speller
    (maximum edit distance 2) for de/hunspell/de_<country>.dict and the
    plain text word lists (expanded with the LineExpander), None if the
    dictionary doesn't exist"""
    from ... import dictionaries
    from ...spelling import SuggestionMultiSpeller
    lang_code = language.short_code
    morfo_file = lang_code + '/hunspell/' + lang_code + '_' + language.countries[0] + '.dict'
    if morfo_file not in dictionaries.required_files(lang_code):
        return None  # spell data does not exist
    paths = get_spelling_file_paths(lang_code)
    if language_variant_plain_text_dict is not None:
        paths.append(language_variant_plain_text_dict)
    key = (morfo_file, tuple(paths), language.dictionary_path)
    with _files_lock:
        r = _morfo_spellers.get(key)
    if r is not None:
        return r
    binary_dict = language.dictionary(morfo_file)
    files = [resource_file(language, path) for path in paths]
    variant_file = resource_file(language, language_variant_plain_text_dict) if language_variant_plain_text_dict \
        else None

    def build():
        text_lines = []
        for path, p in zip(paths, files):
            # (the streams are separated by a comment line and terminated by a line separator)
            text_lines.append('# Start of file ' + path.replace('\n', ''))
            if p is not None:
                text_lines.extend(read_lines(p))
        lines = _expanded_plain_text_lines(text_lines)
        if language_variant_plain_text_dict:
            lines.extend(_expanded_plain_text_lines(read_lines(variant_file) if variant_file is not None else []))
            lines.append(b'LanguageTool')  # adding here so it's also used for suggestions
        return lines
    # (cached on disk, see langtool.diskcache; the line expansion uses the synthesizer)
    from ... import diskcache
    from ...dictionaries import dependency_files
    lines = diskcache.cached('de-speller-lines', (tuple(paths), tuple(files), language_variant_plain_text_dict,
                                                  variant_file), build,
                             deps=[f for f in files + [variant_file] if f is not None] + dependency_files(language))
    r = SuggestionMultiSpeller(binary_dict, lines, MAX_EDIT_DISTANCE)
    with _files_lock:
        _morfo_spellers.setdefault(key, r)
        return _morfo_spellers[key]


_init_cache = {}


class GermanSpellerRule(CompoundAwareHunspellRule):
    """org.languagetool.rules.de.GermanSpellerRule"""

    RULE_ID = RULE_ID

    def __init__(self, messages, language, user_config=None, language_variant_plain_text_dict=None,
                 alt_languages=None, language_model=None):
        super().__init__(messages, language, user_config, alt_languages, language_model)
        self.language_variant_plain_text_dict = language_variant_plain_text_dict
        self.add_example_pair('LanguageTool kann mehr als eine <marker>nromale</marker> Rechtschreibprüfung.',
                              'LanguageTool kann mehr als eine <marker>normale</marker> Rechtschreibprüfung.')
        self.words_to_be_ignored_in_compounds = set()
        self.word_starts_to_be_prohibited = set()
        self.word_endings_to_be_prohibited = set()
        self.words_needing_infix_s = _load_file(language, '/de/words_infix_s.txt')
        self.verb_stems = _load_file(language, '/de/verb_stems.txt')
        self.verb_prefixes = _load_file(language, '/de/verb_prefixes.txt')
        self.other_prefixes = _load_file(language, '/de/other_prefixes.txt')
        self.old_spelling = _load_file(language, '/de/alt_neu.csv')
        self._morfo_speller = None
        self._morfo_speller_loaded = False
        self._compound_tokenizer = None
        self._non_strict_compound_tokenizer = None

    # --- components ---

    @property
    def compound_tokenizer(self):
        """language.getStrictCompoundTokenizer()"""
        if self._compound_tokenizer is None:
            from .compound_tokenizer import get_strict_instance
            self._compound_tokenizer = get_strict_instance(self.language.dictionary_path,
                                                           self.language.download_dictionaries)
        return self._compound_tokenizer

    @property
    def non_strict_compound_tokenizer(self):
        """GermanCompoundTokenizer.getNonStrictInstance()"""
        if self._non_strict_compound_tokenizer is None:
            from .compound_tokenizer import get_non_strict_instance
            self._non_strict_compound_tokenizer = get_non_strict_instance(self.language.dictionary_path,
                                                                          self.language.download_dictionaries)
        return self._non_strict_compound_tokenizer

    def get_compound_splitter(self):
        """language.getNonStrictCompoundSplitter()"""
        return self.non_strict_compound_tokenizer

    def get_morfo_speller(self):
        if not self._morfo_speller_loaded:
            self._morfo_speller = get_speller(self.language, self.language_variant_plain_text_dict)
            self._morfo_speller_loaded = True
        return self._morfo_speller

    @property
    def synthesizer(self):
        return self.language.synthesizer

    def _tag(self, word):
        """getTagger().tag(singletonList(word))"""
        return self.language.tagger.tag([word])

    # --- init ---

    def init(self):
        key = (type(self), self.language.code, self.language.dictionary_path)
        cached = _init_cache.get(key)
        if cached is not None:
            (ignored, prohibited, starts, endings, in_compounds, anti_rules, anti_firsts, hunspell,
             non_word_pattern) = cached
            self.words_to_be_ignored.update(ignored)
            self.words_to_be_prohibited.update(prohibited)
            self.word_starts_to_be_prohibited.update(starts)
            self.word_endings_to_be_prohibited.update(endings)
            self.words_to_be_ignored_in_compounds.update(in_compounds)
            self._anti_pattern_rules.extend(anti_rules)
            self._anti_pattern_first_tokens.extend(anti_firsts)
            self._anti_pattern_index = None
            self._update_ignored_word_dictionary()
            self.hunspell = hunspell
            self.ignore_words_with_length = 1
            self.set_non_word_pattern(non_word_pattern)
            return
        self._init_uncached()
        _init_cache[key] = (frozenset(self.words_to_be_ignored), frozenset(self.words_to_be_prohibited),
                            frozenset(self.word_starts_to_be_prohibited),
                            frozenset(self.word_endings_to_be_prohibited),
                            frozenset(self.words_to_be_ignored_in_compounds), tuple(self._anti_pattern_rules),
                            tuple(self._anti_pattern_first_tokens), self.hunspell, self.non_word_pattern_source)

    def _init_uncached(self):
        """GermanSpellerRule.init"""
        super().init()
        self.ignore_words_with_length = 1
        self.set_non_word_pattern('(' + self.non_word_pattern_source + '|(?<=[\\d°])-|-(?=\\d+))')

    def get_id(self):
        return RULE_ID

    # --- word lists ---

    def is_ignored_no_case(self, word):
        return (word in self.words_to_be_ignored
                # words from spelling.txt also accepted in uppercase (e.g. sentence start, bullet list items):
                or (_FIRST_UPPER_CASE.fullmatch(word) is not None and word.lower() in self.words_to_be_ignored)
                or (self.ignore_words_with_length > 0 and len(word) <= self.ignore_words_with_length))

    def is_prohibited(self, word):
        return (word in self.words_to_be_prohibited
                or any(word.startswith(w) for w in self.word_starts_to_be_prohibited)
                or any(word.endswith(w) for w in self.word_endings_to_be_prohibited))

    def add_ignore_words(self, orig_line):
        # hack: Swiss German doesn't use "ß" but always "ss" - replace this, otherwise
        # misspellings (from Swiss point-of-view) like "äußere" wouldn't be found:
        line = orig_line.replace('ß', 'ss') if self.language.code == 'de-CH' else orig_line
        if line.isalpha():
            # (the result of the expansion and tokenization of a line of letters)
            self.words_to_be_ignored.add(line)
            return
        if orig_line.endswith('-*'):
            # words whose line ends with "-*" are only allowed in hyphenated compounds
            self.words_to_be_ignored_in_compounds.add(line[:-2])
            return
        for word in self.expand_line(line):
            super().add_ignore_words(word)

    def expand_line(self, line):
        return _line_expander.expand_line(line)

    def add_prohibited_words(self, words):
        if len(words) == 1 and words[0].endswith('.*'):
            self.word_starts_to_be_prohibited.add(words[0][:-2])
        elif words[0].startswith('.*'):
            for word in words:
                self.word_endings_to_be_prohibited.add(word[2:])
        else:
            super().add_prohibited_words(words)

    # --- messages ---

    def get_message(self, orig_word, first_suggestion):
        """Note: will not work for words like "Abgasausstoss" where there's
        more than one string of "ss" and the first one is not the one we're
        looking for"""
        if _replace_once(orig_word, 'ss', 'ß') == first_suggestion.replacement:
            first_sz = orig_word.find('ss')
            if first_sz >= 2:
                prev_prev_char = orig_word[first_sz - 2]
                prev_char = orig_word[first_sz - 1]
                if is_vowel(prev_prev_char) and is_vowel(prev_char):
                    return ("Nach einer Silbe aus zwei Vokalen (hier: " + prev_prev_char + prev_char
                            + ") schreibt man 'ß' statt 'ss'.")
                return "Nach einer lang gesprochenen Silbe (hier: " + prev_char + ") schreibt man 'ß' statt 'ss'."
        return self.messages.get('spelling')

    def create_wrong_split_match(self, sentence, rule_matches_so_far, pos, covered_word, suggestion1, suggestion2,
                                 prev_pos):
        if _LOWER_CASE_WORD.fullmatch(suggestion2):
            # avoid confusing matches for e.g. "haben -sehr" (was: "habe n-sehr")
            return None
        return super().create_wrong_split_match(sentence, rule_matches_so_far, pos, covered_word, suggestion1,
                                                suggestion2, prev_pos)

    def is_quoted_compound(self, sentence, idx, token):
        if idx > 3 and token.startswith('-'):
            tokens = sentence.tokens
            return tokens[idx - 1].token in ('“', '"') and tokens[idx - 3].token in ('„', '"')
        return False

    # --- matches ---

    def match(self, sentence, with_suggestions=True):
        matches = super().match(sentence, with_suggestions)
        return self._remove_gender_compound_matches(sentence, matches)

    def _remove_gender_compound_matches(self, sentence, matches):
        """":" and "*" are not in the tokenised text for the speller, so it's
        easier to remove matches for e.g. "Jurist:innenausbildung" as a
        cleanup step after the speller has run"""
        filtered = list(matches)
        text = sentence.text
        pos = 0
        while True:
            m = _GENDER_STAR_PATTERN.search(text, pos)  # Jurist:innenausbildung -> 'Jurist', ':innenausbildung'
            if m is None:
                break
            if not self.is_misspelled(_replace_first(_GENDER_CHAR, m.group(), '')):
                start, end = m.start(), m.end()
                # e.g. "Jurist:innenausbildung" with the ":" removed should be accepted:
                filtered = [k for k in filtered if not (start < k.from_pos and end == k.to_pos)]
                # e.g. "Testexpert*innen" with the "*" removed should be accepted:
                filtered = [k for k in filtered if not (start == k.from_pos and end > k.to_pos)]
            pos = m.end()
        for pattern in (_FILE_UNDERLINE_PATTERN, _MENTION_UNDERLINE_PATTERN):
            pos = 0
            while True:
                m = pattern.search(text, pos)
                if m is None:
                    break
                start, end = m.start(), m.end()
                filtered = [k for k in filtered if not (start <= k.from_pos and end >= k.to_pos)]
                pos = m.end()
        return filtered

    # --- misspelling check ---

    def is_misspelled(self, word):
        if _SCHAF_PATTERN.fullmatch(word) and not _SCHAFE_PATTERN.fullmatch(word):
            variant = _replace_first(_SCHAFEN_END, _replace_first(_SCHAFS_END, _replace_first(
                _SCHAF_END, word, 'schaft'), 'schaft'), 'schaften')
            if not self.is_misspelled(variant):
                return True
        if word.startswith('Spielzug') and not _START_WITH_SPIEL.fullmatch(word):
            return True
        if (word.startswith('Standart') and word != 'Standarte' and word != 'Standarten'
                and not word.startswith('Standartenträger') and not word.startswith('Standartenführer')):
            return True
        if word.endswith('schafte') and _END_WITH_SCHAFTE.fullmatch(word):
            return True
        return super().is_misspelled(word)

    def _ignore_elative(self, word):
        if word.startswith(_ELATIVE_PREFIXES):
            last_part = _replace_all(_ELATIVE_PREFIX_PATTERN, word, '')
            return len(last_part) >= 3 and not self.is_misspelled(last_part)
        return False

    def ignore_word_at(self, words, idx):
        """GermanSpellerRule.ignoreWord(List<String> words, int idx) (the
        rule is initialized first; in Java a call before the initialization
        can fail)"""
        self.ensure_initialized()
        word = words[idx]
        if len(word) > _MAX_TOKEN_LENGTH:
            return True
        ignore = super().ignore_word_at(words, idx)
        ignore_uncapitalized_word = not ignore and idx == 0 and super().ignore_word(_uncapitalize(words[0]))
        ignore_by_hyphen = False
        ignore_bullet_point_case = False
        if not ignore_uncapitalized_word:
            # happens e.g. with list items in Google Docs, which introduce ﻿, which here appears as
            # an empty token:
            ignore_bullet_point_case = (not ignore and idx == 1 and words[0] == ''
                                        and starts_with_uppercase(word)
                                        and self.is_misspelled(word)
                                        and not self.is_misspelled(word.lower()))
        ignore_hyphenated_compound = False
        if not ignore and not ignore_uncapitalized_word:
            if '-' in word:
                if idx > 0 and words[idx - 1] == '' and word.startswith(('stel-', 'tel-')):
                    # accept compounds such as '100stel-Millimeter' or '5tel-Gramm'
                    return not self.is_misspelled(word[word.index('-') + 1:])
                else:
                    ignore_by_hyphen = word.endswith('-') and self._ignore_by_hanging_hyphen(words, idx)
            ignore_hyphenated_compound = not ignore_by_hyphen and self._ignore_compound_with_ignored_word(word)
        if COMMON_FILE_TYPES_SUFFIX_PATTERN.fullmatch(word):
            return True
        if _missingAdjPattern.fullmatch(word):
            first_part = uppercase_first_char(_replace_first(_ADJ_SUFFIX_REMOVE, word, ''))
            # We append "test" to see if the word plus "test" is accepted as a compound. This way, we get the
            # infix 's' handled properly (e.g. "arbeitsartig" is okay, "arbeitartig" is not). It does not accept
            # all compounds, though, as hunspell's compound detection is limited ("Zwiebacktest"):
            if self.is_misspelled(word):
                if (not self.is_misspelled(first_part)
                        and not _SPECIAL_CASE.fullmatch(first_part)
                        and self._is_only_noun(first_part)
                        and not self.is_misspelled(first_part + 'test')):
                    return True
                elif not self.is_misspelled(first_part) and not _SPECIAL_CASE.fullmatch(first_part):
                    pass
                elif (first_part.endswith('s') and not self.is_misspelled(first_part[:-1])
                      and _SPECIAL_CASE_WITH_S.fullmatch(first_part)
                      and self._is_only_noun(first_part[:-1])
                      and not self.is_misspelled(first_part + 'test')):
                    return True
        if word.endswith('mitarbeitende') or word.endswith('mitarbeitenden'):
            if self.hunspell.spell(_replace_first(_MITARBEITENDE, word, 'mitarbeiter')):
                return True
        if ((idx + 1 < len(words) and (word.endswith('.mp') or word.endswith('.woff')) and words[idx + 1] == '')
                or (idx > 0 and words[idx - 1] == '' and word in ('sat', 'stel', 'tel', 'stels', 'tels'))):
            # e.g. ".mp3", "3sat", "100stel", "5tel" - the check for the empty string is because digits were
            # removed during hunspell-style tokenization before
            return True
        return (ignore or ignore_uncapitalized_word or ignore_bullet_point_case or ignore_by_hyphen
                or ignore_hyphenated_compound or self._ignore_elative(word))

    def _ignore_by_hanging_hyphen(self, words, idx):
        word = words[idx]
        next_word = self._get_word_after_enumeration_or_none(words, idx + 1)
        next_word = _remove_end(next_word, '.')
        is_compound = next_word is not None and (
            len(self.compound_tokenizer.tokenize(next_word)) > 1
            or next_word.find('-') > 0
            or _SPECIAL_CASE_THIRD.fullmatch(next_word) is not None)
        # compound tokenizer will only split compounds where each part is >= 3 characters...
        if is_compound:
            word = _remove_end(word, '-')
            is_misspelled = not self.hunspell.spell(word)  # "Stil- und Grammatikprüfung" or "Stil-, Text- und ..."
            if is_misspelled and (super().ignore_word(word) or word in self.words_to_be_ignored_in_compounds):
                is_misspelled = False
            elif is_misspelled and word.endswith('s') and self._is_needing_fugen_s(_remove_end(word, 's')):
                # Vertuschungs- und Bespitzelungsmaßnahmen: remove trailing "s" before checking "Vertuschungs"
                is_misspelled = not self.hunspell.spell(_remove_end(word, 's'))
            return not is_misspelled
        return False

    @staticmethod
    def _is_needing_fugen_s(word):
        # according to http://www.spiegel.de/kultur/zwiebelfisch/zwiebelfisch-der-gebrauch-des-fugen-s-im-ueberblick-a-293195.html
        return word.endswith(('tum', 'ling', 'ion', 'tät', 'keit', 'schaft', 'sicht', 'ung', 'en'))

    @staticmethod
    def _get_word_after_enumeration_or_none(words, idx):
        """for "Stil- und Grammatikprüfung", get "Grammatikprüfung" when at
        position of "Stil-" """
        for i in range(idx, len(words)):
            word = words[i]
            if not (word.endswith('-') or word in (',', '/', '&', 'und', 'oder', 'bzw.', 'beziehungsweise', 'sowie',
                                                   'statt') or not _java_trim(word)):
                return word
        return None

    def _ignore_compound_with_ignored_word(self, word):
        """check whether a word is a valid compound (e.g., "Feynmandiagramm"
        or "Feynman-Diagramm") that contains an ignored word from
        spelling.txt (e.g., "Feynman")"""
        if not starts_with_uppercase(word) and not word.startswith(('nord', 'west', 'ost', 'süd')):
            # otherwise stuff like "rumfangreichen" gets accepted
            return False
        words = java_split(word, '-')
        if len(words) < 2:
            # non-hyphenated compound (e.g., "Feynmandiagramm"):
            # only search for compounds that start(!) with a word from spelling.txt
            end = self.starts_with_ignored_word(word, True)
            if end < 3:
                # support for geographical adjectives - although "süd/ost/west/nord" are not in spelling.txt
                if word.startswith('ost') or word.startswith('süd'):
                    end = 3
                elif word.startswith('west') or word.startswith('nord'):
                    end = 4
                else:
                    return False
            ignored_word = word[:end]
            partial_word = word[end:]
            partial_word = partial_word[:-1] if partial_word.endswith('.') else partial_word
            is_noun = self._is_noun(partial_word)
            is_uppercase_noun = False
            if not is_noun and not starts_with_uppercase(partial_word):
                is_uppercase_noun = self._is_noun(uppercase_first_char(partial_word))
            is_direction = _DIRECTION.fullmatch(ignored_word) is not None
            is_adjective = self._is_adjective(ignored_word)
            is_directional_adjective = is_direction and (is_adjective or _ISCHE.fullmatch(partial_word) is not None)
            is_candidate = ((is_directional_adjective or is_noun or is_uppercase_noun)
                            and not _is_all_upper_case_commons(ignored_word)
                            and (_is_all_lower_case_commons(partial_word) or ignored_word.endswith('-')))
            need_fugen_s = self._is_needing_fugen_s(ignored_word)
            if is_candidate and not need_fugen_s and len(partial_word) > 2:
                return self.hunspell.spell(partial_word) or self.hunspell.spell(_capitalize(partial_word))
            elif is_candidate and need_fugen_s and len(partial_word) > 2:
                partial_word = partial_word[1:] if partial_word.startswith('s') else partial_word
                return self.hunspell.spell(partial_word) or self.hunspell.spell(_capitalize(partial_word))
            return False
        # hyphenated compound (e.g., "Feynman-Diagramm"):
        has_ignored_word = False
        to_spell_check = []
        strip_first = word[len(words[0]) + 1:]  # everything after the first "-"
        strip_last = word[:len(word) - len(words[-1]) - 1]  # everything up to the last "-"
        sup = super()
        if sup.ignore_word(strip_first) or strip_first in self.words_to_be_ignored_in_compounds:
            # e.g., "Senioren-Au-pair"
            has_ignored_word = True
            if not sup.ignore_word(words[0]):
                to_spell_check.append(words[0])
        elif sup.ignore_word(strip_last) or strip_last in self.words_to_be_ignored_in_compounds:
            # e.g., "Au-pair-Agentur"
            has_ignored_word = True
            if not sup.ignore_word(words[-1]):
                to_spell_check.append(words[-1])
        else:
            for word1 in words:
                if sup.ignore_word(word1) or word1 in self.words_to_be_ignored_in_compounds:
                    has_ignored_word = True
                else:
                    to_spell_check.append(word1)
        if has_ignored_word:
            for w in to_spell_check:
                if not self.hunspell.spell(w):
                    return False
        return has_ignored_word

    # --- ignorePotentiallyMisspelledWord and the compound checks ---

    def ignore_potentially_misspelled_word(self, word):
        self.ensure_initialized()
        # Remove dot
        word_no_dot = word[:-1] if word.endswith('.') else word
        if (self._is_valid_word_length(word) or starts_with_lowercase(word) or self.is_prohibited(word)
                or self.is_prohibited(word_no_dot)):
            # Exclude cases like weird/irrelevant words and very long words that can cause crashes
            return False
        # Check for words that are likely to be typos
        if self._is_probably_typo(word):
            return False
        # Format gender neutral forms here to make splitting easier, but
        #   we need to double-check the word later to avoid words in camel case
        #   that look similar to gender-neutral language (e. g. AktienIndex).
        word_no_dot_org = word_no_dot
        # "Expert*innen" -> "Expertinnen", "ExpertInnen"  -> "Expertinnen"
        word_no_dot = _replace_first(_GENDER_STAR, word_no_dot, 'in')
        # Return false if a word is written in CamelCase
        if not self._is_valid_camel_case(word_no_dot):
            return False
        parts = list(self.compound_tokenizer.tokenize(word_no_dot))
        if len(parts) == 1:
            parts = list(self.non_strict_compound_tokenizer.tokenize(word_no_dot))
        # If at least one element in *parts* at position i equals "s", then append "s" to element at i-1
        parts = self._avoid_infix_s_as_single_token(parts)
        # Handle cases for hyphenated compounds that don't depend on tokenization
        # and preprocess further
        if '-' in word_no_dot:
            # Split original word by hyphen
            split_by_hyphen = java_split(word_no_dot, '-')
            last_part = split_by_hyphen[-1] if split_by_hyphen else ''
            if not self._is_noun(last_part) and self._is_noun(uppercase_first_char(last_part)):
                # Make sure that last part is uppercase, if it is probably a noun
                # e.g. "Implementierungs-pflicht"
                return False
            for w in split_by_hyphen:
                if self.is_misspelled(w) and self.is_misspelled(_remove_trailing_s_and_hyphen(w)):
                    return False
            # Split tokenized parts that contain hyphens
            # example: "Wacht" + "ums-pistole" -> "Wacht" + "ums" + "pistole"
            parts = self._split_parts_by_hyphen(parts)
            # Hyphens are often removed by the tokenizer. Restore them to determine later if a compound is correct
            parts = self._restore_removed_hyphens(parts, word_no_dot)
        # Make sure that the individual parts of the compound have appropriate length.
        # Short words can also be typos.
        if not self._is_valid_part_length(parts):
            return False
        # Make sure that compound is not written in old spelling
        if len(parts) >= 2:
            if self._is_old_spelling(parts):
                return False
        # Now that the compound has probably been split correctly,
        #   we can use this information to check,
        #   if a part matching '(?<=(\w))In|[\*:_]in|/-in'
        #   is actually gender-neutral language
        if _GENDER2_STAR2.fullmatch(word_no_dot_org):
            if not self._is_valid_gender_neutral_word(parts, word_no_dot_org):
                return False
        if len(parts) == 2:
            return self._process_two_part_compounds(parts[0], parts[1])
        elif len(parts) == 3:
            return self.process_three_part_compound(parts)
        # more than three parts can be supported later
        return False

    @staticmethod
    def _is_valid_word_length(word):
        return len(word) <= MIN_WORD_LENGTH or len(word) >= MAX_WORD_LENGTH

    @staticmethod
    def _is_valid_part_length(parts):
        # don't assume very short parts (like "Ei") are correct, these can easily be typos:
        if len(parts) == 2:
            return len(parts[0]) >= 3 and len(parts[1]) >= 4
        if len(parts) == 3:
            return len(parts[0]) >= 3 and len(parts[1]) >= 4 and len(parts[2]) >= 4
        return False

    def _is_old_spelling(self, parts):
        old = self.old_spelling
        for part in parts:
            cleaned_part = _remove_trailing_s_and_hyphen(part)
            if part.endswith('s'):
                if (uppercase_first_char(part) in old or uppercase_first_char(cleaned_part) in old
                        or lowercase_first_char(part) in old or lowercase_first_char(cleaned_part) in old):
                    return True
            else:
                if uppercase_first_char(cleaned_part) in old or lowercase_first_char(cleaned_part) in old:
                    return True
        return False

    def _is_valid_gender_neutral_word(self, parts, word):
        start = 0
        for part in parts:
            end = start + len(part)
            to_check = word[start:end]
            if to_check.startswith('I') and start > 0:
                # e. g. AktienIndex
                return False
            if _POTENTIAL_BINNEN_I.fullmatch(to_check):
                if (self.is_misspelled(_replace_first(_BINNEN_I_IN, to_check, 'in'))
                        or (not to_check.endswith('In') and not to_check.endswith('Innen'))):
                    return False
            if _GENDER_NEUTRAL_SPECIAL_CHRS_SIN.fullmatch(to_check):
                if self.is_misspelled(_replace_first(_GENDER_SPECIAL_IN, to_check, 'in')):
                    return False
                end += 1
            if _GENDER_NEUTRAL_SPECIAL_CHRS_PLU.fullmatch(to_check):
                if end < len(word):
                    end += 1
                    to_check = word[start:end]
                if (self.is_misspelled(_replace_first(_GENDER_SPECIAL_IN, to_check, 'in'))
                        or (not to_check.endswith('in') and not to_check.endswith('innen'))):
                    return False
            if _GENDER_NEUTRAL_SLASH_HYPHEN.fullmatch(to_check):
                if end + 1 < len(word):
                    end += 2
                    to_check = word[start:end]
                if (self.is_misspelled(_replace_first(_SLASH_HYPHEN_IN, to_check, 'in'))
                        or (not to_check.endswith('in') and not to_check.endswith('innen'))):
                    return False
            start = end
        return True

    def _is_adjective(self, word):
        return any(k.has_pos_tag_starting_with('ADJ:') for k in self._tag(word))

    def _is_noun(self, word):
        return any(k.has_pos_tag_starting_with('SUB:') for k in self._tag(word))

    def _process_two_part_compounds(self, part1, part2):
        """Expects two parts of a compound and checks if their POS tags are
        correct, if an infix s is missing or if an infix s is incorrect"""
        part1upcased = uppercase_first_char(part1)
        part2upcased = uppercase_first_char(part2)
        part1_without_hyphen = _remove_trailing_hyphen(part1)
        part2upcased_is_noun = self._is_noun(part2upcased)
        part2upcased_is_misspelled = self.is_misspelled(uppercase_first_char(part2upcased))
        if _INVALID_COMP_PART_1.fullmatch(lowercase_first_char(part1_without_hyphen)):
            return False
        if _INVALID_COMP_PART_2.fullmatch(lowercase_first_char(part2)):
            return False
        part1_without_infix_s = part1upcased
        # Sometimes part1 requires singular or plural
        part1_lemma = self._find_lemma_for_noun(_remove_trailing_hyphen(part1))
        if part1_lemma == '' and _remove_trailing_hyphen(part1).endswith('s'):
            part1_lemma = self._find_lemma_for_noun(_remove_trailing_s_and_hyphen(part1))
            part1_without_infix_s = _remove_trailing_s(part1upcased)
        # Allow part1 to be a plural noun if...
        # ... part2 is a nominalized verb or...
        if (self._is_noun_nom_plu(part1_without_infix_s) and not self._is_noun_nom_sin(part1_without_infix_s)
                and not self._is_country_or_region_nom_sin(part1_without_infix_s)
                and (not self._is_sub_ver_inf(part2upcased)
                     or (self._is_sub_ver_inf(part2upcased)
                         and _SUBINF_SINGULAR_OBJECT.fullmatch(lowercase_first_char(part2))))
                and not self._needs_to_be_plural(lowercase_first_char(part1_lemma))
                and not _WECHSELNUMERUS.fullmatch(lowercase_first_char(part1_lemma))
                and not _WECHSELINFIX.fullmatch(lowercase_first_char(_remove_trailing_s(part1_lemma)))):
            return False
        # ... part1 always needs to be plural or...
        if self._needs_to_be_plural(lowercase_first_char(part1_lemma)) and self._is_noun_nom_sin(
                part1_without_infix_s):
            return False
        # ... part1
        if _WECHSELNUMERUS.fullmatch(lowercase_first_char(part1_lemma)):
            if not self._check_plural_for_part1_part2_combination(part1, part2):
                return False
        # For some part1-and-part2 combinations an infix s is correct or incorrect
        if _WECHSELINFIX.fullmatch(lowercase_first_char(part1)):
            return self._check_infix_s_for_part1_part2_combination(part1, part2)
        # Check for easily confused prefixes (e. g. wieder vs wider)
        if (_CONFUSED_PREFIXES.fullmatch(lowercase_first_char(part1)) and not part2upcased_is_misspelled
                and part2upcased_is_noun):
            return self._check_confusion_for_part1_part2_combination(part1, part2)
        # TODO distinguish more cases with hyphens
        if (part2upcased_is_noun and not part2upcased_is_misspelled
                # 's' is the last character in *part1* and is probably not an infix
                and part1_without_hyphen.endswith('s')
                and (self._is_noun_nom(part1upcased) or self._is_verb_stem(part1))
                # check if infix 's' is required or not allowed
                and not self._needs_infix_s(_remove_trailing_s(part1upcased))):
            return True
        if (part2upcased_is_noun and not part2upcased_is_misspelled
                # 's' is the last character in *part1* and is probably an infix
                and part1_without_hyphen.endswith('s')
                and self._is_noun_nom(_remove_trailing_s_and_hyphen(part1upcased))
                # check if infix 's' is required or not allowed
                and self._needs_infix_s(_remove_trailing_s_and_hyphen(part1upcased))):
            return True
        if (part2upcased_is_noun and not part2upcased_is_misspelled
                # *part1* does not end with 's' and is noun or verb stem
                and not part1_without_hyphen.endswith('s')
                and (self._is_noun_nom(part1upcased) or self._is_verb_stem(part1))
                # check if infix 's' is required or not allowed
                and not self._needs_infix_s(part1upcased)):
            return True
        if (part2upcased_is_noun and not part2upcased_is_misspelled
                # *part1* is acronym or other prefix, e. g. "SEO-Expertinnen", "Sprachvariante"
                and ((is_all_uppercase(_remove_trailing_s_and_hyphen(part1))
                      and not self.is_misspelled(_remove_trailing_s_and_hyphen(part1)))
                     or self._is_other_prefix(part1))):
            return True
        if (part2upcased_is_noun and not part2upcased_is_misspelled
                # e. g. Schwedenreise
                and self._is_country_or_region_nom_sin(part1)
                and not _CITIES_EXCEPTIONS.fullmatch(lowercase_first_char(part2))):
            return True
        return False

    def process_three_part_compound(self, parts):
        part1, part2, part3 = parts[0], parts[1], parts[2]
        compound1 = part1 + part2
        compound2 = uppercase_first_char(part2) + parts[2]
        if self._is_noun(compound1) and self._is_noun(compound2):
            # If part1part2 and part2part3 are compounds, then so is part1part2part3
            return (self._process_two_part_compounds(part1, _remove_trailing_hyphen(part2))
                    and self._process_two_part_compounds(part2, part3))
        if compound1.endswith('s') or compound1.endswith('s-'):
            part2_no_infix_s_no_hyphen = _remove_trailing_s_and_hyphen(part2)
            # If part1part2NoInfixSNoHyphen and part2part3 are compounds, then so is part1part2part3
            return (self._process_two_part_compounds(part1, part2_no_infix_s_no_hyphen)
                    and self._process_two_part_compounds(part2, part3))
        if self._is_verb_prefix(part1) and self._is_verb_stem(part2) and self._is_noun(compound2):
            # e.g. "Aus" + "leih" + "stelle"
            return True
        if self._is_noun_nom_sin(part1) and self._is_verb_stem(part2) and self._is_noun(compound2):
            # e.g. "Wein" + "kühl" + "schrank"
            return True
        if self._is_noun_nom(part1) and self._is_other_prefix(part2) and self._is_noun(compound2):
            # e.g. "Erwachsenen" + "intensiv" + "kurse"
            return True
        if self._is_other_prefix(part1) and self._is_verb_stem(part2) and self._is_noun(compound2):
            # e.g. "Horizontal" + "bohr" + "technik"
            return True
        return False

    def _check_infix_s_for_part1_part2_combination(self, part1, part2):
        """For some part1-and-part2 combinations an infix s is correct or
        incorrect"""
        part2_lemma = self._find_lemma_for_noun(_remove_trailing_hyphen(part2))
        if part2_lemma == '' and _remove_trailing_hyphen(part2).endswith('s'):
            part2_lemma = self._find_lemma_for_noun(_remove_trailing_s_and_hyphen(part2))
        lc_lemma = lowercase_first_char(part2_lemma)
        if part1 == 'Arbeit' and _ARBEIT_COMP.fullmatch(part2):
            # e. g. "Arbeitplatz"
            return True
        if part1 == 'Arbeits' and not _ARBEIT_COMP.fullmatch(part2):
            # e. g. "Arbeitsgeber"
            return True
        if part1 == 'Link' and _LINK_COMP.fullmatch(lc_lemma):
            return True
        if part1 == 'Links' and _LINKS_COMP.fullmatch(lc_lemma):
            return True
        if part1 == 'Recht' and _RECHT_COMP.fullmatch(lc_lemma):
            # e. g. "Rechtanwälte"
            return True
        if part1 == 'Rechts' and _RECHTS_COMP.fullmatch(lc_lemma):
            # e. g. "Rechtsfertigung"
            return True
        if part1 == 'Verband' and _VERBAND_COMP.fullmatch(lc_lemma):
            # e. g. "Verbandgemeinde"
            return True
        if part1 == 'Verbands' and _VERBANDS_COMP.fullmatch(lc_lemma):
            # e. g. "Verbandszeug"
            return True
        if _WOCHENTAGE.fullmatch(part1) and _WOCHENTAG_COMP.fullmatch(lc_lemma):
            return True
        if _WOCHENTAGE_S.fullmatch(part1) and not _WOCHENTAG_COMP.fullmatch(lc_lemma):
            return True
        return False

    def _check_confusion_for_part1_part2_combination(self, part1, part2):
        part2_lemma = self._find_lemma_for_noun(_remove_trailing_hyphen(part2))
        lc_lemma = lowercase_first_char(part2_lemma)
        if part1 == 'Bad' and _BACH_COMP.fullmatch(lc_lemma):
            return True
        if part1 == 'Bad' and _BAD_COMP.fullmatch(lc_lemma):
            return True
        if part1 == 'Bade' and not _BAD_COMP.fullmatch(lc_lemma):
            return True
        if part1 == 'Wider' and _WIDER_COMP.fullmatch(lc_lemma):
            return True
        if part1 == 'Wieder' and not _WIDER_COMP.fullmatch(lc_lemma):
            return True
        return False

    def _check_plural_for_part1_part2_combination(self, part1, part2):
        """For some part1-and-part2 combinations part1 needs to be singular
        or plural"""
        part2_lemma = self._find_lemma_for_noun(_remove_trailing_hyphen(part2))
        if part2_lemma == '' and _remove_trailing_hyphen(part2).endswith('s'):
            part2_lemma = self._find_lemma_for_noun(_remove_trailing_s_and_hyphen(part2))
        if part1 == 'Welt' and not _WELTEN_COMP.fullmatch(part2_lemma):
            # e. g. "Weltklima"
            return True
        if part1 == 'Welten' and _WELTEN_COMP.fullmatch(part2_lemma):
            # e. g. "Weltenbummler"
            return True
        if part1 == 'Wort' and not _WOERTER_COMP.fullmatch(part2_lemma):
            # e. g. "Wortgrenze"
            return True
        if part1 == 'Wörter' and _WOERTER_COMP.fullmatch(part2_lemma):
            # e. g. "Wörterbuch"
            return True
        return False

    def _find_lemma_for_noun(self, word):
        lemma = ''
        for reading in self._tag(uppercase_first_char(word)):
            if reading.has_pos_tag_starting_with('SUB'):
                lemma = reading.readings[0].lemma
        return lemma

    @staticmethod
    def _is_probably_typo(word):
        return _COMPOUND_TYPOS.fullmatch(word) is not None or _COMPOUND_END_TYPOS.fullmatch(word) is not None

    @staticmethod
    def _is_valid_camel_case(s):
        # Check if the string contains any instance of camel casing
        return _CAMEL_CASE.fullmatch(s) is None

    @staticmethod
    def _restore_removed_hyphens(parts, word):
        """Restore hyphens that were removed by the tokenizer by appending
        them to individual tokens"""
        tokens_with_hyphens = []
        # Find and store the positions of hyphens in the original word
        hyphen_positions = [i for i, c in enumerate(word) if c == '-']
        current_pos = 0
        for token in parts:
            # Check if the next hyphen is within the current token
            for hyphen_pos in hyphen_positions:
                if hyphen_pos >= current_pos and hyphen_pos == current_pos + len(token):
                    # Insert hyphen at the end of this token
                    token += '-'
                    break  # Move to the next token after adding a hyphen
            tokens_with_hyphens.append(token)
            current_pos += len(token)
        return tokens_with_hyphens

    @staticmethod
    def _avoid_infix_s_as_single_token(parts):
        """If a part equals "s", append it to its predecessor, example:
        "Priorität", "s", "ding" -> "Prioritäts", "ding" """
        indexes_of_s = [i for i, p in enumerate(parts) if p == 's']
        # Sort indexes in descending order to avoid shifting issues while removing elements
        for index in sorted(indexes_of_s, reverse=True):
            if 0 < index < len(parts):  # Ensure index is within bounds and not the first element
                to_append = parts.pop(index)
                parts[index - 1] = parts[index - 1] + to_append
        return parts

    @staticmethod
    def _split_parts_by_hyphen(original_parts):
        parts = []
        for element in original_parts:
            if '-' in element:
                parts.extend(java_split(element, '-'))
            else:
                parts.append(element)
        return parts

    def _needs_infix_s(self, word):
        # check for cases like Rivalität, Freiheit, Expedition...
        if (_INFIX_S_SUFFIXES.fullmatch(word)
                # make sure the POS tag is correct to avoid cases like "Jungs"
                and any(k.has_pos_tag_starting_with('SUB:NOM:SIN:FEM') for k in self._tag(word))):
            return True
        return word in self.words_needing_infix_s

    def _needs_to_be_plural(self, lemma):
        if _NEEDS_TO_BE_PLURAL.fullmatch(lemma):
            return True
        if (any(k.has_pos_tag_starting_with('SUB:NOM:SIN:FE') for k in self._tag(uppercase_first_char(lemma)))
                and lemma.endswith('e') and not _SUBNOMPLUFEM_EXCEPTIONS.fullmatch(lemma)):
            return True
        if _PERSON_SUFFIXES.fullmatch(lemma):
            return True
        return False

    def _is_noun_nom(self, word):
        return any(k.has_pos_tag_starting_with('SUB:NOM') for k in self._tag(word))

    def _is_noun_nom_sin(self, word):
        return any(k.has_pos_tag_starting_with('SUB:NOM:SIN') for k in self._tag(word))

    def _is_noun_nom_plu(self, word):
        return any(k.has_pos_tag_starting_with('SUB:NOM:PLU') for k in self._tag(word))

    def _is_country_or_region_nom_sin(self, word):
        return any(k.matches_pos_tag_regex(_COUNTRY_OR_REGION) for k in self._tag(word))

    def _is_other_prefix(self, word):
        return lowercase_first_char(word) in self.other_prefixes

    def _is_verb_prefix(self, word):
        return lowercase_first_char(word) in self.verb_prefixes

    def _is_verb_stem(self, word):
        return lowercase_first_char(word) in self.verb_stems

    # --- tagger based helpers of the suggestions ---

    def _is_noun_or_unknown(self, word):
        return any(r.has_pos_tag_starting_with('SUB') or r.is_pos_tag_unknown for r in self._tag(word))

    def _is_only_noun(self, word):
        readings = self._tag(word)
        for reading in readings:
            accept = all(k.pos_tag is not None and k.pos_tag.startswith('SUB:') for k in reading.readings)
            if not accept:
                return False
        return all(reading.matches_pos_tag_regex(_SUB_ANY) for reading in readings)

    def _is_adj_or_noun_or_unknown(self, word):
        return any(r.has_pos_tag_starting_with('SUB') or r.has_pos_tag_starting_with('ADJ') or r.is_pos_tag_unknown
                   for r in self._tag(word))

    def _is_noun_or_proper_noun(self, word):
        return any(r.has_pos_tag_starting_with('SUB') or r.has_pos_tag_starting_with('EIG') for r in self._tag(word))

    def _is_sub_ver_inf(self, word):
        return any(r.matches_pos_tag_regex(_SUB_INF) for r in self._tag(word))

    def _is_adj_base_form(self, word):
        return any(r.has_pos_tag_starting_with('ADJ:PRD:GRU') for r in self._tag(word))

    # --- suggestions ---

    def get_candidates(self, word):
        """GermanSpellerRule.getCandidates(String word)"""
        from .compound_tokenizer import InputTooLongException
        try:
            part_list = _get_splitter().get_all_splits(word)
        except InputTooLongException:
            part_list = []
        candidates = []
        for parts in part_list:
            parts = list(parts)
            tmp = self.get_candidates_for_parts(parts)
            tmp = [k for k in tmp if not _HYPHENED_UPPER_WORD.fullmatch(k) and not _HYPHENED_WORD.fullmatch(k)]
            tmp = [k for k in tmp if '-s-' not in k]  # avoid e.g. "Geheimnis-s-voll"
            if not word.endswith('-'):
                tmp = [k for k in tmp if not k.endswith('-')]  # avoid "xyz-" unless the input word ends in "-"
            candidates.extend(tmp)
            if len(parts) == 2:
                # e.g. "inneremedizin" -> "innere Medizin", "gleichgroß" -> "gleich groß"
                candidates.append(parts[0] + ' ' + parts[1])
                if self._is_noun_or_proper_noun(uppercase_first_char(parts[1])):
                    candidates.append(parts[0] + ' ' + uppercase_first_char(parts[1]))
            if len(parts) == 2 and not parts[0].endswith('s'):
                # so we get e.g. Einzahlungschein -> Einzahlungsschein
                candidates.append(parts[0] + 's' + parts[1])
            if len(parts) == 2 and parts[1].startswith('s'):
                # so we get e.g. Ordnungshütter -> Ordnungshüter (Ordnungshütter is split as Ordnung + shütter)
                first_part = parts[0]
                second_part = parts[1]
                candidates.extend(self.get_candidates_for_parts([first_part + 's', second_part[1:]]))
        return candidates

    def get_suggestions(self, word):
        """GermanSpellerRule.getSuggestions"""
        self.ensure_initialized()
        if self.hunspell is None or self.get_morfo_speller() is None:
            return []  # (no dictionary: NullPointerException in Java)
        suggestions = super().get_suggestions(word)
        suggestions = [s for s in suggestions if self.accept_suggestion(s)]
        if word.endswith('.'):
            # To avoid losing the "." of "word" if it is at the end of a sentence.
            suggestions = [s if s.endswith('.') else s + '.' for s in suggestions]
        suggestions = [k for k in suggestions
                       if k != word
                       and (not k.endswith('-') or word.endswith('-'))  # no "-" at end (#2450)
                       and not _STARTING_WITH_SINGLE_CHAR.fullmatch(k)]  # single chars like in "ü berstenden" (#2610)
        return suggestions

    def accept_suggestion(self, s):
        return (not any(p.fullmatch(s) for p in _PREVENT_SUGGESTION_PATTERNS)
                and '--' not in s
                and not s.endswith('roulett')
                and not s.endswith('-s')  # https://github.com/languagetool-org/languagetool/issues/4042
                and not s.endswith(' de')
                and not s.endswith(' en')
                and not s.endswith(' Artigen')
                and not s.endswith(' Artige')
                and not s.endswith(' artigen')
                and not s.endswith(' artiges')
                and not s.endswith(' artiger')
                and not s.endswith(' artige')
                and not s.endswith(' artig')
                and not s.endswith(' gen')
                and not s.endswith(' ehe')
                and not s.endswith(' ende')
                and not s.endswith(' enden')
                and not s.endswith(' enge')
                and not s.endswith(' förmig')
                and not s.endswith(' förmige')
                and not s.endswith(' förmigen')
                and not s.endswith(' förmiger')
                and not s.endswith(' förmiges')
                and not s.startswith('Doppel ')
                and not s.startswith('Kombi '))

    def filter_for_language(self, suggestions):
        """(modifies the list)"""
        if self.language.code == 'de-CH':
            for i, s in enumerate(suggestions):
                suggestions[i] = s.replace('ß', 'ss')
        # Remove suggestions like "Mafiosi s" and "Mafiosi s.":
        # This is not quite correct as it might remove valid suggestions that start with "-",
        # but without this we get too many strange suggestions that start with "-" for no apparent reason
        # (e.g. for "Gratifikationskrisem" -> "-Gratifikationskrisen"):
        suggestions[:] = [s for s in suggestions
                          if not any(_WORD_WITH_PUNCT.fullmatch(k) for k in java_split(s, ' '))
                          and not (len(s) > 1 and s.startswith('-'))]

    def sort_suggestion_by_quality(self, misspelling, suggestions):
        # filter some undesired inflected forms
        filtered_suggestions = []
        readings_list = self.language.tagger.tag(list(suggestions)) if suggestions else []
        lemma_to_filter = ''
        form_to_accept = ''
        for readings in readings_list:
            if readings.has_any_partial_pos_tag('ADJ', 'SUB', 'PA1:', 'PA2:'):
                if readings.token.endswith(misspelling[-2:] if len(misspelling) >= 2 else misspelling):
                    form_to_accept = readings.token
                    lemma_to_filter = readings.readings[0].lemma
                    break
        if lemma_to_filter and form_to_accept and len(misspelling) > 1:
            for i, s in enumerate(suggestions):
                if s == form_to_accept or not readings_list[i].has_any_lemma(lemma_to_filter):
                    if s not in filtered_suggestions:
                        filtered_suggestions.append(s)
        else:
            filtered_suggestions.extend(suggestions)
        # end of filtering
        result = []
        top_suggestions = []  # candidates from suggestions that get boosted to the top
        for suggestion in filtered_suggestions:
            if java_equals_ignore_case(misspelling, suggestion):  # this should be preferred - only case differs
                top_suggestions.append(suggestion)
            elif ' ' in suggestion:  # this should be preferred - prefer e.g. "vor allem":
                # (no language model: the split suggestion is preferred)
                top_suggestions.append(suggestion)
            else:
                result.append(suggestion)
        return top_suggestions + result

    def get_filtered_suggestions(self, words_or_phrases):
        result = []
        for word_or_phrase in words_or_phrases:
            words = self.tokenize_text(word_or_phrase)
            if (len(words) >= 2 and self._is_adj_or_noun_or_unknown(words[0]) and self._is_noun_or_unknown(words[1])
                    and starts_with_uppercase(words[0]) and starts_with_uppercase(words[1])):
                # ignore, seems to be in the form "Release Prozess" which is *probably* wrong
                pass
            elif (len(words) == 2 and self._is_adj_base_form(words[0]) and not starts_with_uppercase(words[0])
                  and self._is_sub_ver_inf(words[1])):
                # filter "groß Denken" in "großdenken"
                pass
            else:
                result.append(word_or_phrase)
        return result

    def filter_no_suggest_words(self, suggestions):
        result = []
        for k in suggestions:
            r = k.replacement
            lc = r.lower()
            if (lc in _LC_DO_NOT_SUGGEST_WORDS or _START_WITH_NEGER.fullmatch(lc) or _CONTAINS_NEGER.fullmatch(lc)
                    or _CONTAINS_NEGER_2.fullmatch(lc) or _CONTAINS_UNCOMMON_LOWERCASED_NOUN_AT_END.fullmatch(r)
                    or _CONTAINS_UNCOMMON_LOWERCASED_NOUN_AT_BEGINNING.fullmatch(r)):
                continue
            result.append(k)
        return result

    def get_only_suggestions(self, word):
        if _SYMPHATISCH.fullmatch(word):
            return _top_match(_replace_once(word, 'symphatisch', 'sympathisch'))
        if _AUTENTISCH_WITH_CASES.fullmatch(word):
            return _top_match(_replace_once(word, 'utent', 'uthent'))
        if _BRILLIANT_WITH_CASES.fullmatch(word):
            return _top_match(_replace_once(word, 'brilliant', 'brillant'))
        if _RECHTMASIG_WITH_CASES.fullmatch(word):
            return _top_match(_replace_once(word, 'mässig', 'mäßig'))
        if _CONTAINS_MASZNAME.fullmatch(word):
            return _top_match(_replace_first(_MASZNAME_REPL, word, 'aßnahme'))
        if _HOLZ_SPIEGEL_PANEL_COMPOUND.fullmatch(word):
            return _top_match(_replace_once(word, 'panel', 'paneel'))
        if _SBHAN_PREFIX.fullmatch(word):
            return _top_match(_replace_once(word, 'SBahn', 'S-Bahn'))
        if _UBAHN_PREFIX.fullmatch(word):
            return _top_match(_replace_once(word, 'UBahn', 'U-Bahn'))
        if word in ('Büffet', 'Buffett', 'Bufett', 'Büffett', 'Bufet', 'Büfet'):
            if self.language.code in ('de-CH', 'de-AT'):
                return _top_match('Buffet', 'zum Verzehr bereitgestellte Speisen')
            return _top_match('Büfett', 'zum Verzehr bereitgestellte Speisen')
        r = spelling_data.ONLY_SUGGESTIONS.get(word)
        if r is not None:
            return _top_match(r[0], r[1])
        return []

    def get_additional_top_suggestions(self, suggestions, word):
        suggestions_list = [s.replacement for s in suggestions]
        return [SuggestedReplacement(s) for s in self._get_additional_top_suggestions_string(suggestions_list, word)]

    def _spell_or_none(self, suggestion):
        if self.hunspell.spell(suggestion):
            return [suggestion]
        return None

    def _get_additional_top_suggestions_string(self, suggestions, word):
        r = self._special_top_suggestion(word)
        if r is not None:
            return r
        if not starts_with_uppercase(word):
            uc_word = uppercase_first_char(word)
            if uc_word not in suggestions and self.hunspell.spell(uc_word) and not uc_word.endswith('.'):
                # Hunspell doesn't always automatically offer the most obvious suggestion for compounds:
                return [uc_word]
        verb_suggestion = self._get_past_tense_verb_suggestion(word)
        if verb_suggestion is not None:
            return [verb_suggestion]
        participle_suggestion = self._get_participle_suggestion(word)
        if participle_suggestion is not None:
            return [participle_suggestion]
        abbreviation_suggestion = self._get_abbreviation_suggestion(word)
        if abbreviation_suggestion is not None:
            return [abbreviation_suggestion]
        # hyphenated compounds words (e.g., "Netflix-Flm")
        if not suggestions and '-' in word:
            words = java_split(word, '-')
            if len(words) > 1:
                suggestion_lists = []
                start_at = 0
                stop_at = len(words)
                partial_word = words[0] + '-' + words[1]
                sup = super(GermanSpellerRule, self)
                if sup.ignore_word(partial_word) or partial_word in self.words_to_be_ignored_in_compounds:
                    # "Au-pair-Agentr"
                    start_at = 2
                    suggestion_lists.append([words[0] + '-' + words[1]])
                partial_word = words[-2] + '-' + words[-1]
                if sup.ignore_word(partial_word) or partial_word in self.words_to_be_ignored_in_compounds:
                    # "Seniren-Au-pair"
                    stop_at = len(words) - 2
                for idx in range(start_at, stop_at):
                    if not self.hunspell.spell(words[idx]):
                        lst = self.sort_suggestion_by_quality(words[idx],
                                                              CompoundAwareHunspellRule.get_suggestions(self,
                                                                                                         words[idx]))
                        suggestion_lists.append(lst)
                    else:
                        suggestion_lists.append([words[idx]])
                if stop_at < len(words) - 1:
                    suggestion_lists.append([partial_word])
                if len(suggestion_lists) <= 3:  # avoid OutOfMemory on words like "free-and-open-source-and-..."
                    additional_suggestions = suggestion_lists[0]
                    for idx in range(1, len(suggestion_lists)):
                        suggestion_list = suggestion_lists[idx]
                        new_list = []
                        for additional_suggestion in additional_suggestions:
                            for a in suggestion_list:
                                new_list.append(additional_suggestion + '-' + a)
                        additional_suggestions = new_list
                    # avoid overly long lists of suggestions (we just take the first results)
                    return additional_suggestions[:5]
        return []

    def _special_top_suggestion(self, word):
        """the if/else chain at the start of getAdditionalTopSuggestions: a
        list (the result) or None (continue)"""
        spell = self._spell_or_none
        if java_equals_ignore_case('WIFI', word):
            return ['Wi-Fi']
        elif java_equals_ignore_case('W-Lan', word):
            return ['WLAN']
        elif word == 'Endstadion':
            return ['Endstadium']
        elif word == 'Endstadions':
            return ['Endstadiums']
        elif word == 'genomen':
            return ['genommen']
        elif word == 'Preis-Leistungsverhältnis':
            return ['Preis-Leistungs-Verhältnis']
        elif word == 'getz':
            return ['jetzt', "geht's"]
        elif word == 'Trons':
            return ['Trance']
        elif word == 'ei':
            return ['ein']
        elif word in ('jo', 'jepp', 'jopp'):
            return ['ja']
        elif word in ('Jo', 'Jepp', 'Jopp'):
            return ['Ja']
        elif word == 'Ne':
            # "Ne einfach Frage!", "Ne, das musst du machen!"
            return ['Nein', 'Eine']
        elif word == 'is':
            return ['ist']
        elif word == 'Is':
            return ['Ist']
        elif word == 'un':
            return ['und']
        elif word == 'Un':
            return ['Und']
        elif word == 'Std':
            return ['Std.']
        elif _ENDS_WITH_IBELKEIT_IBLICHKEIT.fullmatch(word):
            return spell(_replace_first(_ENDS_EL_HK_EIT, word, 'ilität'))
        elif word.endswith('aquise'):
            return spell(_replace_first(_AQUISE_END, word, 'akquise'))
        elif word.endswith('standart'):
            return spell(_replace_first(_STANDART_END, word, 'standard'))
        elif word.endswith('standarts'):
            return spell(_replace_first(_STANDARTS_END, word, 'standards'))
        elif word.endswith('tips'):
            return spell(_replace_first(_TIPS_END, word, 'tipps'))
        elif word.endswith('tip'):
            return spell(word + 'p')
        elif word.endswith('entfehlung'):
            return spell(_replace_once(word, 'ent', 'emp'))
        elif word.endswith('oullie'):
            return spell(_replace_first(_OULLIE_END, word, 'ouille'))
        elif word.startswith('Bundstift'):
            return spell(_replace_first(_BUNDSTIFT_START, word, 'Buntstift'))
        elif _ALLMAHLLIG.fullmatch(word):
            return spell(_replace_first(_ALLMAHLLIG_REPL, word, 'llmählich'))
        elif _CONTAINS_MAYONNAISE.fullmatch(word):
            return spell(_replace_first(_MAYONNAISE_REPL, word, 'ayonnaise'))
        elif _CONTAINS_RESERVIERUNG.fullmatch(word):
            # suggest e.g. 'Ticketreservierung', but not 'Blödsinnsquatschreservierung'
            return spell(_replace_first(_RESERVIERUNG_REPL, word, 'eservierung'))
        elif _STARTS_WITH_RESCHASCHIER.fullmatch(word):
            return spell(_replace_once(word, 'schaschier', 'cherchier'))
        elif _ENDS_WITH_LABORANTS.fullmatch(word):
            return spell(_replace_first(_TS_END, word, 'ten'))
        elif _PROFESSIONELL.fullmatch(word):
            return spell(_replace_first(_PROFESSIONELL_REPL, word, 'rofessionell'))
        elif _VERSTANDNIS.fullmatch(word):
            return spell(_replace_first(_VERSTEHENDNIS_REPL, word, 'Verständnis'))
        elif word.startswith('koregier'):
            return spell(word.replace('reg', 'rrig'))
        elif _STARTS_WITH_DIAGNOSZIER.fullmatch(word):
            return spell(_replace_all(_GNOSZIER, word, 'gnostizier'))
        elif 'eiss' in word:
            return spell(word.replace('eiss', 'eiß'))
        elif 'Akkupressur' in word:
            return spell(word.replace('Akkupressur', 'Akupressur'))
        elif 'farbend' in word:  # steinfarbenden, schwarzfarbenden, kupferfarbenden etc.
            return spell(word.replace('farbend', 'farben'))
        elif 'uess' in word:
            return spell(word.replace('uess', 'üß'))
        elif word == 'gin':
            return ['ging']
        elif word in ('dh', 'dh.'):
            return ['d. h.']
        elif word in ('ua', 'ua.'):
            return ['u. a.']
        elif _ZB.fullmatch(word) or _STARTS_WITH_ZB.fullmatch(word):
            return ['z. B.']
        elif word in ('uvm', 'uvm.'):
            return ['u. v. m.']
        elif word in ('udgl', 'udgl.'):
            return ['u. dgl.']
        elif word == 'Ruhigkeit':
            return ['Ruhe']
        elif word == 'angepreist':
            return ['angepriesen']
        elif word == 'halo':
            return ['hallo']
        elif java_equals_ignore_case(word, 'zumindestens'):
            return [word.replace('ens', '')]
        elif word == 'ca':
            return ['ca.']
        elif word == 'Jezt':
            return ['Jetzt']
        elif word == 'Wollst':
            return ['Wolltest']
        elif word == 'wollst':
            return ['wolltest']
        elif word == 'Rolladen':
            return ['Rollladen']
        elif word == 'Maßname':
            return ['Maßnahme']
        elif word == 'Maßnamen':
            return ['Maßnahmen']
        elif word == 'nanten':
            return ['nannten']
        elif word == 'diees':
            return ['dieses', 'dies']
        elif word == 'Diees':
            return ['Dieses', 'Dies']
        elif word.endswith('ies'):
            if word == 'Lobbies':
                return ['Lobbys']
            elif word == 'Parties':
                return ['Partys']
            elif word == 'Babies':
                return ['Babys']
            elif word.endswith('derbies'):
                return spell(_replace_first(_DERBIES_END, word, 'derbys'))
            elif word.endswith('stories'):
                return spell(_replace_first(_STORIES_END, word, 'storys'))
            elif word.endswith('parties'):
                return spell(_replace_first(_PARTIES_END, word, 'partys'))
            return None
        elif word == 'Hallochen':
            return ['Hallöchen', 'hallöchen']
        elif word == 'hallochen':
            return ['hallöchen']
        elif word == 'ok':
            return ['okay', 'O. K.']  # Duden-like suggestion with no-break space
        elif word == 'gesuchen':
            return ['gesuchten', 'gesucht']
        elif word == 'Germanistiker':
            return ['Germanist', 'Germanisten']
        elif word == 'Abschlepper':
            return ['Abschleppdienst', 'Abschleppwagen']
        elif word == 'par':
            return ['paar']
        elif word == 'iwie':
            return ['irgendwie']
        elif word == 'schwarzfarbenden':
            return ['schwarzfarbenen']
        elif word == 'bzgl':
            return ['bzgl.']
        elif word == 'bau':
            return ['baue']
        elif word == 'sry':
            return ['sorry']
        elif word == 'Sry':
            return ['Sorry']
        elif word == 'thx':
            return ['danke']
        elif word == 'Thx':
            return ['Danke']
        elif word == 'Zynik':
            return ['Zynismus']
        elif word == 'pieksen':
            return ['piksen']
        elif word == 'piekst':
            return ['pikst']
        elif word == 'gepiekst':
            return ['gepikst']
        elif java_equals_ignore_case(word, 'email'):
            return ['E-Mail']
        elif len(word) > 9 and word.startswith('Email'):
            suffix = word[5:]
            if not self.hunspell.spell(suffix):
                suffix_suggestions = self.hunspell.suggest(uppercase_first_char(suffix))
                suffix = suffix_suggestions[0] if suffix_suggestions else suffix
            return ['E-Mail-' + char_to_upper(suffix[0]) + suffix[1:]]
        elif word == 'wiederspiegeln':
            return ['widerspiegeln']
        elif word == 'ch':
            return ['ich']
        else:
            r = _get_additional_suggestions_map().get(word)
            if r is not None:
                return r
        return None

    def _get_past_tense_verb_suggestion(self, word):
        """Get a correct suggestion for invalid words like greifte, denkte,
        gehte: useful for non-native speakers and cannot be found by just
        looking for similar words."""
        if word.endswith('e'):
            # strip trailing "e"
            word_stem = word[:-1]
            lemma = self._base_for_third_person_singular_verb(word_stem)
            if lemma is not None:
                token = AnalyzedToken(lemma, None, lemma)
                forms = self.synthesizer.synthesize(token, 'VER:3:SIN:PRT:.*', True)
                if forms:
                    return forms[0]
        return None

    def _base_for_third_person_singular_verb(self, word):
        for reading in self._tag(word):
            if reading.has_pos_tag_starting_with('VER:3:SIN'):
                return reading.readings[0].lemma
        return None

    def _get_participle_suggestion(self, word):
        """Get a correct suggestion for invalid words like geschwimmt,
        geruft: useful for non-native speakers and cannot be found by just
        looking for similar words."""
        if word.startswith('ge') and word.endswith('t'):
            # strip leading "ge" and replace trailing "t" with "en":
            baseform = word[2:-1] + 'en'
            participle = self._get_participle_for_baseform(baseform)
            if participle is not None:
                return participle
        return None

    def _get_participle_for_baseform(self, baseform):
        token = AnalyzedToken(baseform, None, baseform)
        forms = self.synthesizer.synthesize(token, 'VER:PA2:.*', True)
        if forms and self.hunspell.spell(forms[0]):
            return forms[0]
        return None

    def _get_abbreviation_suggestion(self, word):
        if len(word) < 5:
            for reading in self._tag(word):
                if reading.has_pos_tag_starting_with('ABK'):
                    return word + '.'
        return None


_COUNTRY_OR_REGION = jregex.compile('EIG:NOM:SIN.+(COU|GEB|STD|WAT)')
_SUB_ANY = jregex.compile('SUB:.*')
_SUB_INF = jregex.compile('SUB:.*:INF')
_ADJ_SUFFIX_REMOVE = jregex.compile(_adjSuffix + '(er|es|en|em|e)?')
_MAX_TOKEN_LENGTH = MAX_TOKEN_LENGTH


def _remove_trailing_s(part1):
    return _remove_end(part1, 's')


def _remove_trailing_hyphen(part1):
    return _remove_end(part1, '-')


def _remove_trailing_s_and_hyphen(part1):
    return _remove_trailing_s(_remove_trailing_hyphen(part1))


def _top_match(word, short_desc=None):
    """SuggestedReplacement.topMatch"""
    sugg = SuggestedReplacement(word, short_desc)
    sugg.confidence = HIGH_CONFIDENCE
    return [sugg]


class AustrianGermanSpellerRule(GermanSpellerRule):
    """org.languagetool.rules.de.AustrianGermanSpellerRule: also accepts
    the words of de/hunspell/spelling-de-AT.txt"""

    LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT = 'de/hunspell/spelling-de-AT.txt'

    def __init__(self, messages, language, user_config=None, language_model=None):
        super().__init__(messages, language, user_config, self.LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT, [], language_model)

    def get_id(self):
        return 'AUSTRIAN_GERMAN_SPELLER_RULE'

    def _init_uncached(self):
        super()._init_uncached()
        for ignore_word in load_words(self.language, '/de/hunspell/spelling-de-AT.txt'):
            self.add_ignore_words(ignore_word)

    def get_language_variant_spelling_file_name(self):
        return self.LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT


class SwissGermanSpellerRule(GermanSpellerRule):
    """org.languagetool.rules.de.SwissGermanSpellerRule: also accepts the
    words of de/hunspell/spelling-de-CH.txt"""

    LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT = 'de/hunspell/spelling-de-CH.txt'

    def __init__(self, messages, language, user_config=None, language_model=None):
        super().__init__(messages, language, user_config, self.LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT, [], language_model)

    def get_id(self):
        return 'SWISS_GERMAN_SPELLER_RULE'

    def _init_uncached(self):
        super()._init_uncached()
        for ignore_word in load_words(self.language, '/de/hunspell/spelling-de-CH.txt'):
            self.add_ignore_words(ignore_word)

    def get_language_variant_spelling_file_name(self):
        return self.LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT


def default_spelling_rule(language):
    """German.createDefaultSpellingRule and its overrides: the
    GermanSpellerRule for de and de-DE, AustrianGermanSpellerRule for de-AT,
    SwissGermanSpellerRule for de-CH (with the German messages)"""
    from ...messages import messages_for
    messages = messages_for('de')
    if language.code == 'de-AT':
        return AustrianGermanSpellerRule(messages, language)
    if language.code == 'de-CH':
        return SwissGermanSpellerRule(messages, language)
    return GermanSpellerRule(messages, language)


class MorfologikGermanyGermanSpellerRule:
    """org.languagetool.rules.de.MorfologikGermanyGermanSpellerRule
    (deprecated in Java, not used by the language): the morfologik spell
    checker for de/hunspell/de_DE.dict without compound support. Only the
    misspelling check, the check of a sentence and the suggestions of the
    morfologik speller rule are ported (langtool.spelling); created with
    morfologik_germany_german_speller_rule(language)."""

    RULE_ID = 'MORFOLOGIK_RULE_DE_DE'
    RESOURCE_FILENAME = '/de/hunspell/de_DE.dict'


def morfologik_germany_german_speller_rule(language):
    """A MorfologikGermanyGermanSpellerRule (misspelling check and
    suggestions) for the language"""
    from ...spelling import MorfologikMisspellingCheck, MorfologikSuggestions

    class _Check(MorfologikSuggestions, MorfologikMisspellingCheck):
        __doc__ = MorfologikGermanyGermanSpellerRule.__doc__

        def get_file_name(self):
            return MorfologikGermanyGermanSpellerRule.RESOURCE_FILENAME

        def get_id(self):
            return MorfologikGermanyGermanSpellerRule.RULE_ID

    return _Check(language)
