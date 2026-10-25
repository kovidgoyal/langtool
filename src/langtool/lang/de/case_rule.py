"""Port of org.languagetool.rules.de.CaseRule (with
CaseRuleExceptions): adjectives and verbs must not be written with an
uppercase first letter (except at the start of a sentence), substantivized
verbs like in "Das laufen fällt mir leicht." must be uppercased."""

import threading

from ... import jregex
from ...analysis import SENTENCE_START_TAGNAME
from ...patterns import string_matcher
from ...patterns.rules import make_anti_patterns
from ...rules.base import RuleMatch
from ...rules.core import CoreRule
from ...tools import (is_all_uppercase, is_lower_case, is_numeric, is_upper_case, java_equals_ignore_case,
                      java_is_whitespace, lowercase_first_char, starts_with_uppercase, uppercase_first_char)
from . import language_names
from .case_rule_antipatterns import anti_patterns
from .german_helper import has_reading_of_type as _has_reading_of_type
from .german_token import POSType

# --- CaseRuleExceptions ------------------------------------------------------

_exceptions_lock = threading.Lock()
_exception_cache = []


def _load_exceptions(language, *paths):
    """CaseRuleExceptions.loadExceptions"""
    result = set()
    for path in paths:
        with open(language.resource_path(path.lstrip('/')), encoding='utf-8') as f:
            lines = [line.rstrip('\r\n') for line in f]
        for line in lines:
            if not line or line.startswith('#'):
                continue
            if java_is_whitespace(line[0]) or java_is_whitespace(line[-1]):
                raise ValueError("Invalid line in %s, starts or ends with whitespace: '%s'" % (path, line))
            result.add(line)
    return frozenset(result)


def get_exceptions(language):
    """CaseRuleExceptions.getExceptions: the phrases (regular expressions
    separated by spaces) of /de/eigennamen_gross.txt and
    /de/case_rule_exceptions.txt"""
    if not _exception_cache:
        with _exceptions_lock:
            if not _exception_cache:
                exceptions = _load_exceptions(language, '/de/eigennamen_gross.txt', '/de/case_rule_exceptions.txt')
                patterns = []
                for phrase in exceptions:
                    # StringUtils.split(phrase, ' '): empty parts are dropped
                    parts = [p for p in phrase.split(' ') if p]
                    patterns.append(tuple(string_matcher.regexp(p) for p in parts))
                _exception_cache.append((exceptions, tuple(patterns), _index_exception_patterns(patterns)))
    return _exception_cache[0][0]


def _index_exception_patterns(patterns):
    """For CaseRule.isExceptionPhrase (whose result does not depend on the
    order of the patterns): the (patterns, j) pairs whose j-th
    StringMatcher has a finite set of possible values, indexed by these
    values, and the list of the other (patterns, j) pairs"""
    index = {}
    others = []
    for pats in patterns:
        for j, m in enumerate(pats):
            pv = m.possible_values
            if pv is not None:
                for v in pv:
                    index.setdefault(v, []).append((pats, j))
            else:
                others.append((pats, j))
    return index, tuple(others)


def get_exception_patterns(language):
    """CaseRuleExceptions.getExceptionPatterns: one tuple of StringMatchers
    per exception phrase"""
    get_exceptions(language)
    return _exception_cache[0][1]


# --- CaseRule ----------------------------------------------------------------

_NUMERALS_EN = jregex.compile('[a-z]|[0-9]+|(m{0,4}(c[md]|d?c{0,3})(x[cl]|l?x{0,3})(i[xv]|v?i{0,3}))$')
_TWO_UPPERCASE_CHARS = jregex.compile('[A-ZÖÄÜ][A-ZÖÄÜ][a-zöäüß-]+')

# wenn hinter diesen Wörtern ein Verb steht, ist es wohl ein substantiviertes Verb,
# muss also groß geschrieben werden:
_NOUN_INDICATORS = frozenset((
    'das',
    'sein',
    # 'ihr',    # would cause false alarm e.g. "Auf ihr stehen die Ruinen...", "Ich dachte, dass ihr kommen würdet.",
    #           # "Ich verdanke ihr meinen Erfolg."
    'mein',
    'dein',
    'euer',
    'unser',
))

UPPERCASE_MESSAGE = 'Außer am Satzanfang werden nur Nomen und Eigennamen großgeschrieben.'
LOWERCASE_MESSAGE = 'Falls es sich um ein substantiviertes Verb handelt, wird es großgeschrieben.'
COLON_MESSAGE = ('Folgt dem Doppelpunkt weder ein Substantiv noch eine wörtliche Rede oder ein vollständiger '
                 'Hauptsatz, schreibt man klein weiter.')
_VERHALTEN = jregex.compile('.+verhalten')
_IRGEND_ETC = jregex.compile('irgendwelche|irgendwas|irgendein|weniger?|einiger?|mehr|aufs')
_VER_MOD_AUX = jregex.compile('VER:(MOD|AUX):[1-3]:.*')
_SUB_VER_123_PA2 = jregex.compile('(VER:[123]:|PA2).+')
_NEU_MAS_FEM_END = jregex.compile('.*(NEU|MAS|FEM)$')
_SUB_SIN_NEU = jregex.compile('SUB:...:SIN:NEU')
_PRECEDED_BY_VERB = jregex.compile('VER:(MOD:|AUX:)?[1-3]:.*')
_ADJ_PA2_GEN_PLU_MAS = jregex.compile('(ADJ|PA2):GEN:PLU:MAS:GRU:SOL.*')
_ALLE_NM = jregex.compile('Alle[nm]')
_IN_INNEN = jregex.compile('in|innen')

_SENTENCE_START_EXCEPTIONS = frozenset(('(', '"', "'", '‘', '„', '«', '»', '‚', '.', '!', '?'))

_UNDEFINED_QUANTIFIERS = frozenset(('viel', 'nichts', 'nix', 'wenig', 'allerlei'))

# Used for subordinate clause detection after verbs (e.g. "Überlegen, wie man...")

_INTERROGATIVE_PARTICLES = frozenset(('was', 'wodurch', 'wofür', 'womit', 'woran', 'worauf', 'woraus', 'wovon',
                                      'wie'))

_POSSESSIVE_INDICATORS = frozenset(('einer', 'eines', 'der', 'des', 'dieser', 'dieses'))

_DAS_VERB_EXCEPTIONS = frozenset(('nur', 'sogar', 'auch', 'die', 'alle', 'viele', 'zu'))

# Used for short question fragments after a colon (e.g. "Ich frage mich: Warum?")
# Intentionally different from INTERROGATIVE_PARTICLES, which targets subordinate clauses.

_COLON_QUESTION_WORDS = ('warum', 'wieso', 'weshalb', 'wer', 'was', 'wann', 'wo', 'wie', 'wozu')

_COLON_QUESTION_CONJUNCTIONS = ('und', 'oder', 'aber', 'denn')

# These are words that Morphy only knows as non-nouns (or not at all).
# The proper solution is to add all those to our Morphy data, but as a simple
# workaround to avoid false alarms, these words can be added here.
_EXCEPTIONS = frozenset((
    'Bedienstete',
    'Bediensteter',
    'Feierwütiger',
    'Feierwütige',
    'Feierwütigen',
    'Dritten',
    'Berufstätige',
    'Berufstätigen',
    'Erwerbstätige',
    'Erwerbstätigen',
    'Tatverdächtige',
    'Tatverdächtigen',
    'Konsumierende',
    'Konsumierenden',
    'Verliebter',
    'Verliebte',
    'Beängstigendes',
    'Oppositioneller',
    'Oppositionelle',
    'Verantwortlicher',
    'Verantwortliche',
    'Verantwortlichen',
    'Beschuldigte',
    'Beschuldigten',
    'Beklagte',
    'Beklagten',
    'Befragte',
    'Befragten',
    'Hingerichtete',
    'Lehrende',
    'Lehrender',
    'Vertrauter',
    'Out',  # eng
    'Packet',  # misspelling of "Paket" (caught by spell checker)
    'Adult',  # eng
    'Apart',  # eng
    'Universal',  # eng
    'Multinational',  # eng
    'Additional',  # eng
    'Smart',  # eng
    'Adverse',  # eng
    'Different',  # eng
    'Light',  # eng
    'Legal',  # eng
    'Computational',  # eng
    'Holder',  # eng
    'Just',  # eng
    'Lost',  # eng
    'Fundamental',  # eng
    'Quick',  # eng
    'Infernal',  # eng
    'Fit',  # eng
    'Fair',  # eng
    'Viral',  # eng
    'Tough',  # eng
    'Indoor',  # eng
    'Superb',  # eng und Automodell
    'Resilient',  # eng
    'Hexagonal',  # eng
    'Responsive',  # eng
    'Anno',  # Name
    'Mo',
    'Di',
    'Mi',
    'Do',  # "Di. und Do. um 18 Uhr"
    'Fr',  # "Fr. Dr. Müller"
    'Sa',  # Sa. 12 - 16 Uhr
    'Gr',  # "Gr. 12" (Größe)
    'Mag',  # "Mag. Helke Müller"
    'Nov',
    'Diss',
    'Invalide',
    'Invalider',
    'Invaliden',
    'Sehende',
    'Sehender',
    'Sehenden',
    'Schutzheilige',
    'Schutzheiliger',
    'Schutzheiligen',
    'Lila',
    'Langzeitarbeitslose',
    'Langzeitarbeitslosen',
    'Langzeitarbeitsloser',
    'Linksintellektuelle',
    'Linksintellektueller',
    'Linksintellektuellen',
    'Beschuldigte',
    'Beschuldigten',
    'Drogenabhängige',
    'Drogenabhängiger',
    'Drogenabhängiger',
    'Drogenabhängigen',
    'Asylsuchender',
    'Asylsuchende',
    'Asylsuchenden',
    'Landtagsabgeordnete',
    'Landtagsabgeordneter',
    'Landtagsabgeordneten',
    'Stadtverordnete',
    'Stadtverordneter',
    'Stadtverordneten',
    'Veränderliche',
    'Veränderlicher',
    'Veränderlichen',
    'Werbetreibende',
    'Werbetreibender',
    'Werbetreibenden',
    'Verletzter',
    'Verletzten',
    'Werktätige',
    'Werktätiger',
    'Werktätigen',
    'Getestete',  # temporary fix
    'Getesteten',  # temporary fix
    'Genesene',  # temporary fix
    'Genesenen',  # temporary fix
    'Geimpfte',  # temporary fix
    'Geboosterte',  # temporary fix
    'Ungeimpfte',  # temporary fix
    'Geimpften',  # temporary fix
    'Geboosterten',  # temporary fix
    'Ungeimpften',  # temporary fix
    'Geflüchtete',  # temporary fix
    'Geflüchteten',  # temporary fix
    'Projektbeteiligte',  # temporary fix
    'Projektbeteiligten',  # temporary fix
    'Heranwachsende',  # temporary fix
    'Heranwachsenden',  # temporary fix
    'Interessierte',  # temporary fix
    'Interessierten',  # temporary fix
    'Infizierte',  # temporary fix
    'Infizierten',  # temporary fix
    'Gehörlose',  # temporary fix
    'Gehörlosen',  # temporary fix
    'Drücke',
    'Klecks',
    'Quatsch',
    'Speis',
    'Flash',
    'Suhl',
    'Müh',
    'Bims',
    'Wisch',
    'Außenputz',
    'Rinderhack',
    'Hack',
    'Schlitz',
    'Frevler',
    'Zementputz',
    'Hurst',  # Name
    'Bombardier',  # Name
    'Kraus',  # Nachname
    'Strunz',  # Nachname
    'Bell',  # Nachname
    'Melk',  # Nachname
    'Klopp',  # Nachname
    'Walz',  # Nachname
    'Schiel',  # Nachname
    'Dusch',  # Nachname
    'Penn',  # Nachname
    'Dörr',  # Nachname
    'Kies',
    'Koks',
    'Dell',  # Name
    'Wall',
    'Beige',
    'Zoom',
    'Perl',
    'Parallele',
    'Parallelen',
    'Rutsch',
    'Spar',
    'Merz',
    'Gefahren',
    'Minderjährige',
    'Minderjähriger',
    'Minderjährigen',
    'Scheinselbstständige',
    'Bundestagsabgeordneter',
    'Bundestagsabgeordneten',
    'Bundestagsabgeordnete',
    'Reichstagsabgeordneter',
    'Reichstagsabgeordneten',
    'Reichstagsabgeordnete',
    'Medienschaffende',
    'Medienschaffenden',
    'Medienschaffender',
    'Lehrende',
    'Lehrenden',
    'Vertretene',
    'Vertretenen',
    'Vorstandsvorsitzender',
    'Vorstandsvorsitzenden',
    'Vorstandsvorsitzende',
    'Demonstrierende',
    'Demonstrierenden',
    'Marketingtreibende',
    'Marketingtreibender',
    'Marketingtreibenden',
    'Strafgefangenen',
    'Strafgefangener',
    'Strafgefangene',
    'Pädophile',
    'Pädophiler',
    'Pädophilen',
    'Lehrbeauftragte',
    'Lehrbeauftragter',
    'Lehrbeauftragten',
    'Erkrankte',
    'Erkrankter',
    'Erkrankten',
    'Eigner',
    'Polizeibeamten',
    'Polizeibeamter',
    'Polizeibeamte',
    'Kriegsversehrte',
    'Kriegsversehrter',
    'Kriegsversehrten',
    'Demenzkranke',
    'Demenzkranker',
    'Demenzkranken',
    'Parteivorsitzende',
    'Parteivorsitzender',
    'Parteivorsitzenden',
    'Kriegsgefangene',
    'Kriegsgefangener',
    'Kriegsgefangenen',
    'Ehrenvorsitzende',
    'Ehrenvorsitzender',
    'Ehrenvorsitzenden',
    'Oberkommandierende',
    'Oberkommandierender',
    'Oberkommandierenden',
    'Werbungtreibende',
    'Werbungtreibenden',
    'Mitangeklagte',
    'Schuhfilz',
    'Mix',
    'Rahm',
    'Flansch',
    'WhatsApp',
    'Verschleiß',
    'Schutzsuchende',  # gendered form
    'Schutzsuchenden',  # gendered form
    'Versicherte',
    'Versicherten',  # gendered form
    'Cyberkriminelle',
    'Cyberkriminellen',
    'Kriminelle',
    'Kriminellen',
    'Auszubildenden',
    'Auszubildende',
    'Auszubildender',
    'Lernende',  # gendered form
    'Lernender',  # gendered form
    'Lernenden',  # gendered form
    'Teilnehmende',  # gendered form
    'Teilnehmenden',  # gendered form
    'Radfahrende',  # gendered form
    'Radfahrenden',  # gendered form
    'Autofahrende',  # gendered form
    'Autofahrenden',  # gendered form
    'Auszubildene',  # gendered form
    'Auszubildenen',  # gendered form
    'Absolvierende',  # gendered form
    'Absolvierenden',  # gendered form
    'Einheimische',
    'Einheimischen',
    'Einheimischer',
    'Wehrbeauftragter',
    'Wehrbeauftragte',
    'Wehrbeauftragten',
    'Wehrbeauftragtem',
    'Prozessbevollmächtigter',
    'Prozessbevollmächtigte',
    'Prozessbevollmächtigten',
    'Prozessbevollmächtigtem',
    'Bundesbeamte',
    'Bundesbeamter',
    'Bundesbeamten',
    'Bundesbeamtem',
    'Datenschutzbeauftragter',
    'Datenschutzbeauftragte',
    'Datenschutzbeauftragten',
    'Datenschutzbeauftragtem',
    'Steuerbevollmächtigte',
    'Steuerbevollmächtigter',
    'Steuerbevollmächtigten',
    'Steuerbevollmächtigtem',
    'Suchtkranken',
    'Suchtkranke',
    'Suchtkranker',
    'Filmschaffende',
    'Filmschaffender',
    'Filmschaffenden',
    'Filmschaffendem',
    'Arbeitssuchende',
    'Arbeitssuchender',
    'Arbeitssuchenden',
    'Arbeitssuchendem',
    'Bausachverständige',
    'Bausachverständiger',
    'Bausachverständigen',
    'Bausachverständigem',
    'Heurige',
    'Ratsuchende',
    'Ratsuchender',
    'Ratsuchenden',
    'Verwundete',
    'Verwundeter',
    'Verwundeten',
    'Vollzugsbeamte',
    'Vollzugsbeamter',
    'Vollzugsbeamten',
    'Schutzbefohlene',
    'Schutzbefohlener',
    'Schutzbefohlenen',
    'Verfahrensbeteiligte',
    'Verfahrensbeteiligter',
    'Verfahrensbeteiligten',
    'Kolonialbeamte',
    'Kolonialbeamter',
    'Kolonialbeamten',
    'Verwaltungsbeamte',
    'Verwaltungsbeamter',
    'Verwaltungsbeamten',
    'Verdächtige',
    'Verdächtiger',
    'Verdächtigen',
    'Leichtverletzte',
    'Leichtverletzten',
    'Leichtverletzte',
    'Dozierende',
    'Dozierenden',
    'Studierende',
    'Studierender',
    'Studierenden',
    'Suchbegriffen',
    'Plattdeutsch',
    'Wallet',
    'Str',
    'Priest',
    'Simple',
    'Legend',
    'Golden',
    'Forward',
    'Unverzagt',  # österreichisches Adelsgeschlecht
    'Auszubildende',
    'Auszubildender',
    'Gelehrte',
    'Gelehrter',
    'Gelehrten',
    'Vorstehende',
    'Vorstehender',
    'Mitwirkende',
    'Mitwirkender',
    'Mitwirkenden',
    'Tabellenletzte',
    'Tabellenletzter',
    'Familienangehörige',
    'Familienangehöriger',
    'Zeitreisende',
    'Zeitreisender',
    'Zeitreisenden',
    'Erwerbstätige',
    'Erwerbstätigen',
    'Erwerbstätiger',
    'Selbstständige',
    'Selbstständigen',
    'Selbstständiger',
    'Selbständige',
    'Selbständigen',
    'Selbständiger',
    'Genaueres',
    'Äußersten',
    'Dienstreisender',
    'Verletzte',
    'Vermisste',
    'Äußeres',
    'Abseits',
    'Unschuldige',
    'Unschuldiger',
    'Unschuldigen',
    'Mitarbeitende',
    'Mitarbeitender',
    'Mitarbeitenden',
    'Beschäftigter',
    'Beschäftigte',
    'Beschäftigten',
    'Beschäftigtem',
    'Bekannter',
    'Bekannte',
    'Bevollmächtigte',
    'Bevollmächtigter',
    'Bevollmächtigten',
    'Brecht',
    'Tel',  # Tel. = Telefon
    'Unschuldiger',
    'Vorgesetzter',
    'Abs',  # Abs. = Abkürzung für Absatz, Absender, ...
    'Klappe',
    'Vorfahre',
    'Mittler',
    'Hr',  # Hr. = Abkürzung für Herr
    'Schwarz',
    'Genese',
    'Rosa',
    'Auftrieb',
    'Zuschnitt',
    'Geschossen',
    'Vortrieb',
    'Abtrieb',
    'Gesandter',
    'Durchfahrt',
    'Durchgriff',
    'Überfahrt',
    'Zeche',
    'Sparte',
    'Sparten',
    'Heiliger',
    'Reisender',
    'Pest',
    'Schwinge',
    'Verlies',
    'Nachfolge',
    'Stift',
    'Belange',
    'Geistlicher',
    'Google',
    'Hu',  # name
    'Jenseits',
    'Abends',
    'Stimmberechtigte',
    'Stimmberechtigten',
    'Stimmberechtigter',
    'Alleinerziehende',
    'Alleinerziehenden',
    'Alleinerziehender',
    'Abgeordneter',
    'Abgeordnete',
    'Abgeordneten',
    'Angestellter',
    'Angestellte',
    'Angestellten',
    'Armeeangehörige',
    'Armeeangehörigen',
    'Armeeangehöriger',
    'Liberaler',
    'Abriss',
    'Ahne',
    'Ähnlichem',
    'Ähnliches',  # je nach Kontext groß (TODO), z.B. "Er hat Ähnliches erlebt"
    'Allerlei',
    'Anklang',
    'Verlobter',
    'Anstrich',
    'Armes',
    'Ausdrücke',
    'Auswüchsen',
    'Bände',
    'Bänden',
    'Beauftragter',
    'Belange',
    'Biss',
    'De',  # "De Morgan" etc
    'Diesseits',  # "im Diesseits"
    'Dr',
    'Durcheinander',
    'Eindrücke',
    'Erwachsener',
    'Familienangehörige',  # "Brüder und solche Familienangehörige, die..."
    'Flöße',
    'Folgendes',  # je nach Kontext groß (TODO)...
    'Fort',
    'Fraß',
    'Fristende',
    'Frevel',
    'Genüge',
    'Gefallen',  # Gefallen finden
    'Gläubige',
    'Gläubiger',
    'Gläubigen',
    'Hechte',
    'Herzöge',
    'Herzögen',
    'Hinfahrt',
    'Hilfsstoff',
    'Hilfsstoffe',
    'Hundert',  # groß und klein möglich
    'Zehntausend',  # groß und klein möglich
    'Hunderttausend',  # groß und klein möglich
    'Hyperwallet',  # Anglizismus
    'Ihnen',
    'Ihrerseits',
    'Ihr',
    'Ihre',
    'Ihrem',
    'Ihren',
    'Ihrer',
    'Ihres',
    'Infrarot',
    'Jenseits',
    'Jugendliche',
    'Jugendlichen',
    'Jugendlicher',
    'Jünger',
    'Kant',  # Immanuel
    'Klaue',
    'Konditional',
    'Krähe',
    'Kurzem',
    'Landwirtschaft',
    'Langem',
    'Längerem',
    'Lausitz',
    'Le',  # "Le Monde" etc
    'Lehrlingsunterweisung',
    # "Leichter", // Leichter = ein Schiff in oben offener Bauweise ohne Eigenantrieb
    'Letzt',
    'Letzt',  # "zu guter Letzt"
    'Letztere',
    'Letzterer',
    'Letzteres',
    'Link',
    'Links',
    'Löhne',
    'Luden',
    'Milk',  # Englisches Wort und eine Form von "melken"
    'Mitfahrt',
    'Mr',
    'Mrd',
    'Mrs',
    'Nachfrage',
    'Nachts',  # "des Nachts", "eines Nachts"
    'Nachspann',
    'Nähte',
    'Nähten',
    'Narkoseverfahren',
    'Neuem',
    'Neugeborene',
    'Neugeborenen',
    'Neugeborenes',
    'Nr',
    'Nutze',  # zu Nutze
    'Obdachlose',
    'Obdachloser',
    'Obdachlosen',
    'Oder',  # der Fluss
    'Ohrfeige',
    'Patsche',
    'Pfiffe',
    'Pfiffen',
    'Press',  # University Press
    'Prof',
    'Puste',
    'Sachverständiger',
    'Sankt',
    'Schaulustige',
    'Schaulustigen',
    'Schaulustiger',
    'Scheine',
    'Scheiße',
    'Schuft',
    'Schufte',
    'Schuld',
    'Schwangere',
    'Schwangeren',
    'Schwärme',
    'Schwarzes',  # Schwarzes Brett
    'Sie',
    'Skype',
    'Spitz',
    'Spott',
    'St',  # Paris St. Germain
    'Stereotyp',
    'Störe',
    'Tausend',  # je nach Kontext groß (TODO)
    'Tischende',
    'Toter',
    'Übrigen',  # je nach Kontext groß (TODO), z.B. "im Übrigen"
    'Unentschieden',
    'Unvorhergesehenes',  # je nach Kontext groß (TODO), z.B. "etwas Unvorhergesehenes"
    'Verantwortlicher',
    'Verlass',
    'Verwandter',
    'Verstorbenen',
    'Verstorbene',
    'Vielfache',
    'Vielfaches',
    'Vorsitzender',
    'Fraktionsvorsitzender',
    'Verletzte',
    'Verletzten',
    'Walt',
    'Weitem',
    'Weiteres',
    'Wohlen',  # Stadt in der Schweiz
    'Wicht',
    'Wichtiges',
    'Wider',  # "das Für und Wider"
    'Wild',
    'Zeche',
    'Zusage',
    'Zwinge',
    'Zirkusrund',
    'Tertiär',  # geologischer Zeitabschnitt

    'Erster',  # "er wurde Erster im Langlauf"
    'Zweiter',
    'Dritter',
    'Vierter',
    'Fünfter',
    'Sechster',
    'Siebter',
    'Achter',
    'Neunter',
    'Erste',  # "sie wurde Erste im Langlauf"
    'Zweite',
    'Dritte',
    'Vierte',
    'Fünfte',
    'Sechste',
    'Siebte',
    'Achte',
    'Neunte',

    # Änderungen an der Rechtschreibreform 2006 erlauben hier Großschreibung:
    'Dein',
    'Deine',
    'Deinem',
    'Deinen',
    'Deiner',
    'Deines',
    'Deinerseits',
    'Dich',
    'Dir',
    'Du',
    'Euch',
    'Euer',
    'Eure',
    'Euern',
    'Eurem',
    'Euren',
    'Eures',
    'Eueren',
    'Euerem',
    'Eueres',
    'Euerer',
    'Eurerseits',
    'Euerseits',
))

_SUBST_VERBEN_EXCEPTIONS = frozenset((
    'hinziehen',
    'helfen',
    'lassen',
    'passieren',  # "das Schlimmste, das passieren könnte"
    'haben',  # "Das haben schon viele versucht."
    'passiert',  # "Das passiert..."
    'beschränkt',  # "Das beschränkt sich..."
    'wiederholt',
    'scheinen',
    'klar',
    'heißen',
    'einen',
    'gehören',
    'bedeutet',  # "und das bedeutet..."
    'ermöglicht',  # "und das ermöglicht..."
    'funktioniert',  # "Das funktioniert..."
    'sollen',
    'werden',
    'dürfen',
    'müssen',
    'so',
    'ist',
    'können',
    'mein',  # "etwas, das mein Interesse geweckt hat"
    'sein',
    'muss',
    'muß',
    'wollen',
    'habe',
    'ein',  # nicht "einen" (Verb)
    'tun',  # "...dann wird er das tun."
    'bestätigt',
    'bestätigte',
    'bestätigten',
    'bekommen',
    'sauer',
    'bedeuten',
))

_SALUTATIONS = frozenset(('Herr', 'Hr', 'Herrn', 'Frau', 'Fr', 'Fräulein'))
_COMPANIES = frozenset(('Firma', 'Familie', 'Unternehmen', 'Firmen', 'Bäckerei', 'Metzgerei', 'Fa'))
_CITY_PREFIXES = frozenset(('Klein', 'Groß', 'Neu'))

_LOOKUP_CACHE_SIZE = 20000

_anti_patterns_cache = {}
_anti_patterns_lock = threading.Lock()
_ANTI_PATTERN_SIZES = []


def _first_char(s):
    """s.charAt(0) for the Character.isUpperCase/isLowerCase tests: a
    supplementary character is a (non-letter) surrogate in Java"""
    c = s[0]
    return '\ud800' if ord(c) > 0xffff else c


def _java_length(s):
    return len(s) + sum(1 for c in s if ord(c) > 0xffff)


def _remove_end(s, remove):
    """StringUtils.removeEnd"""
    return s[:-len(remove)] if remove and s.endswith(remove) else s


def _count_pos_tag_starting_with(tokens, partial_pos_tag):
    """getTokensWithPosTagStartingWithCount"""
    return sum(1 for t in tokens if t.has_pos_tag_starting_with(partial_pos_tag))


def _has_partial_tag(token, *pos_tags):
    if token is not None:
        for pos_tag in pos_tags:
            if token.has_partial_pos_tag(pos_tag):
                return True
    return False


def compare_lists(tokens, start_index, end_index, *patterns):
    """CaseRule.compareLists"""
    if start_index < 0:
        return False
    i = 0
    for j in range(start_index, end_index + 1):
        if i >= len(patterns) or j >= len(tokens) or not patterns[i].matches(tokens[j].token):
            return False
        i += 1
    return True


class CaseRule(CoreRule):
    """Port of org.languagetool.rules.de.CaseRule (DE_CASE)."""

    rule_id = 'DE_CASE'
    category_id = 'CASING'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        # (setUrl() in the constructor is overridden by getUrl())
        self.url = 'https://dict.leo.org/grammatik/deutsch/Rechtschreibung/Regeln/Gross-klein/index.html'
        self.add_example_pair('<marker>Das laufen</marker> fällt mir schwer.',
                              '<marker>Das Laufen</marker> fällt mir schwer.')
        self._lookup_cache = {}
        get_exceptions(language)
        self._exception_index, self._exception_others = _exception_cache[0][2]

    def get_id(self):
        return 'DE_CASE'

    def estimate_context_for_sure_match(self):
        if not _ANTI_PATTERN_SIZES:
            _ANTI_PATTERN_SIZES.append(max((len(p) for p in anti_patterns()), default=0))
        return _ANTI_PATTERN_SIZES[0]

    def get_description(self):
        return 'Großschreibung von Nomen und substantivierten Verben'

    def get_anti_patterns(self):
        # (cacheAntiPatterns: per language)
        key = self.language.short_code_with_country_and_variant
        aps = _anti_patterns_cache.get(key)
        if aps is None:
            with _anti_patterns_lock:
                aps = _anti_patterns_cache.get(key)
                if aps is None:
                    aps = _anti_patterns_cache[key] = make_anti_patterns(anti_patterns(), self.language)
        return aps

    def _lookup(self, word):
        """GermanTagger.lookup (memoized: the rule looks up the same words
        several times per sentence)"""
        cache = self._lookup_cache
        try:
            return cache[word]
        except KeyError:
            pass
        r = self.language.tagger.lookup(word)
        if len(cache) >= _LOOKUP_CACHE_SIZE:
            cache.clear()
        cache[word] = r
        return r

    def _is_misspelled(self, word):
        speller = self.language.get_default_spelling_rule()
        return speller is not None and speller.is_misspelled(word)

    def match(self, sentence):
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        n = len(tokens)
        prev_token_is_das = False
        is_preceded_by_modal_or_auxiliary = False
        for i in range(n):
            # Note: defaulting to the first analysis is only save if we only query for sentence start
            pos_token = tokens[i].readings[0].pos_tag
            if pos_token == SENTENCE_START_TAGNAME:
                continue
            if i == 1:  # don't care about first word, UppercaseSentenceStartRule does this already
                prev_token_is_das = tokens[1].token.lower() in _NOUN_INDICATORS
                continue
            if i > 0 and (tokens[i - 1].token in _SALUTATIONS or tokens[i - 1].token in _COMPANIES):
                # e.g. "Frau Stieg" could be a name, ignore
                continue

            # 1.1 Technische Dokumentation
            if i > 2 and _NUMERALS_EN.fullmatch(tokens[i - 1].token) and tokens[i - 2].token == '.' and \
                    _NUMERALS_EN.fullmatch(tokens[i - 3].token):
                continue

            analyzed_token = tokens[i]
            token = analyzed_token.token

            is_baseform = len(analyzed_token.readings) >= 1 and analyzed_token.has_lemma(token)
            if (analyzed_token.readings[0].pos_tag is None or
                    _has_reading_of_type(analyzed_token, POSType.VERB)) and is_baseform:
                next_token_is_personal_or_reflexive_pronoun = False
                if i < n - 1:
                    next_token = tokens[i + 1]
                    # avoid false alarm for "Das haben wir getan." etc:
                    next_token_is_personal_or_reflexive_pronoun = next_token.has_partial_pos_tag('PRO:PER') or \
                        next_token.token in ('sich', 'Sie')
                    if next_token.has_pos_tag('PKT'):
                        # avoid false alarm for "So sollte das funktionieren." (might also remove true alarms...)
                        continue
                    if (prev_token_is_das and (next_token.token in _DAS_VERB_EXCEPTIONS or
                                               self._is_followed_by_relative_or_subordinate_clause(i, tokens))) or \
                            (i > 1 and _has_partial_tag(tokens[i - 2], 'VER:AUX', 'VER:MOD')):
                        # avoid false alarm for "Er kann ihr das bieten, was sie verdient."
                        # avoid false alarm for "Das wissen die meisten." / "Um das sagen zu können, ..."
                        # avoid false alarm for "Du musst/solltest/könntest das wissen, damit du die Prüfung
                        # bestehst / weil wir das gestern besprochen haben."
                        # avoid false alarm for "Wir werden das stoppen."
                        # avoid false alarm for "Wahre Liebe muss das aushalten."
                        continue
                if self._is_prev_probably_relative_pronoun(tokens, i) or \
                        (prev_token_is_das and _count_pos_tag_starting_with(tokens, 'VER') == 1):
                    # ignore sentences containing a single verb, e.g., "Das wissen viele nicht."
                    continue
                self._potentially_add_lowercase_match(rule_matches, tokens[i], prev_token_is_das, token,
                                                      next_token_is_personal_or_reflexive_pronoun, sentence)
            prev_token_is_das = tokens[i].token.lower() in _NOUN_INDICATORS
            if analyzed_token.matches_pos_tag_regex(_VER_MOD_AUX):
                is_preceded_by_modal_or_auxiliary = True
            lowercase_readings = self._lookup(token.lower())
            # it's the spell checker's task to check that nouns are uppercase
            if self._has_noun_reading(analyzed_token):
                if not self._is_potential_upper_case_error(i, tokens, lowercase_readings,
                                                           is_preceded_by_modal_or_auxiliary):
                    continue
            elif analyzed_token.has_pos_tag_starting_with('SUB:') and i < n - 1 and \
                    is_lower_case(_first_char(tokens[i + 1].token)) and \
                    tokens[i + 1].matches_pos_tag_regex(_SUB_VER_123_PA2):
                # "Viele Minderjährige sind" but not "Das wirklich Wichtige Verfahren ist"
                continue
            if analyzed_token.readings[0].pos_tag is None and lowercase_readings is None:
                continue
            if analyzed_token.readings[0].pos_tag is None and lowercase_readings is not None and \
                    (lowercase_readings.readings[0].pos_tag is None or analyzed_token.token.endswith('innen')):
                continue  # unknown word, probably a name etc.
            self._potentially_add_uppercase_match(rule_matches, tokens, i, analyzed_token, token,
                                                  lowercase_readings, sentence)
        return rule_matches

    def _is_potential_upper_case_error(self, pos, tokens, lowercase_readings, is_preceded_by_modal_or_auxiliary):
        if pos <= 1:
            return False
        n = len(tokens)
        # "Das ist zu Prüfen." but not "Das geht zu Herzen."
        if tokens[pos - 1].token == 'zu' and not tokens[pos].matches_pos_tag_regex(_NEU_MAS_FEM_END) and \
                lowercase_readings is not None and lowercase_readings.has_pos_tag_starting_with('VER:INF'):
            return True
        if _VERHALTEN.fullmatch(tokens[pos].token):
            return False
        # find error in: "Man müsse Überlegen, wie man das Problem löst."
        is_potential_error = pos < n - 3 \
            and tokens[pos + 1].token == ',' \
            and tokens[pos + 2].token in _INTERROGATIVE_PARTICLES \
            and tokens[pos - 1].has_pos_tag_starting_with('VER:MOD') \
            and not tokens[pos - 1].has_lemma('mögen') \
            and tokens[pos + 3].token != 'zum'
        if not is_potential_error and \
                lowercase_readings is not None \
                and tokens[pos].has_any_partial_pos_tag('SUB:NOM:SIN:NEU:INF', 'SUB:DAT:PLU:') \
                and (tokens[pos - 1].token == 'zu' or
                     _has_partial_tag(tokens[pos - 1], 'SUB', 'EIG', 'VER:AUX:3:', 'ADV:TMP', 'ABK')):
            # find error in: "Der Brief wird morgen Übergeben." / "Die Ausgaben haben eine Mrd. Euro Überschritten."
            is_potential_error |= lowercase_readings.has_pos_tag('PA2:PRD:GRU:VER') and \
                not tokens[pos - 1].has_pos_tag_starting_with('VER:AUX:3') and \
                not lowercase_readings.has_pos_tag('VER:3:PLU:PRT:NON')
            # find error in: "Er lässt das Arktisbohrverbot Überprüfen."
            # find error in: "Sie bat ihn, es zu Überprüfen."
            # find error in: "Das Geld wird Überwiesen."
            is_potential_error |= (pos >= n - 2 or tokens[pos + 1].token == ',') \
                and (tokens[pos - 1].token == 'zu' or is_preceded_by_modal_or_auxiliary) \
                and tokens[pos].token.startswith('Über') \
                and lowercase_readings.has_any_partial_pos_tag('VER:INF:', 'PA2:PRD:GRU:VER')
        return is_potential_error

    # e.g. "Ein Kaninchen, das zaubern kann" - avoid false alarm here
    #                          ^^^^^^^
    @staticmethod
    def _is_prev_probably_relative_pronoun(tokens, i):
        return i >= 3 and \
            tokens[i - 1].token == 'das' and \
            tokens[i - 2].token == ',' and \
            tokens[i - 3].matches_pos_tag_regex(_SUB_SIN_NEU)

    def _has_noun_reading(self, readings):
        if readings is not None:
            # Anmeldung bis Fr. 1.12. (Fr. as abbreviation of Freitag is has a noun reading!)
            if readings.has_pos_tag_starting_with('ABK') and readings.has_partial_pos_tag('SUB'):
                return True
            # "Die Schöne Tür": "Schöne" also has a noun reading but like "SUB:AKK:SIN:FEM:ADJ", ignore that:
            # unification in disambiguation.xml removes reading, so look up again, removing soft hyphens
            all_readings = self._lookup(readings.token.replace('­', ''))
            if all_readings is not None:
                for reading in all_readings:
                    pos_tag = reading.pos_tag
                    if pos_tag is not None and 'SUB:' in pos_tag and ':ADJ' not in pos_tag:
                        return True
        return False

    def _potentially_add_lowercase_match(self, rule_matches, token_readings, prev_token_is_das, token,
                                         next_token_is_personal_or_reflexive_pronoun, sentence):
        # e.g. essen -> Essen
        if prev_token_is_das and \
                not next_token_is_personal_or_reflexive_pronoun and \
                is_lower_case(_first_char(token)) and \
                token not in _SUBST_VERBEN_EXCEPTIONS and \
                token_readings.has_pos_tag_starting_with('VER:INF') and \
                not token_readings.ignored_by_speller and \
                not token_readings.immunized:
            self._add_rule_match(rule_matches, sentence, LOWERCASE_MESSAGE, token_readings,
                                 uppercase_first_char(token_readings.token))

    def _potentially_add_uppercase_match(self, rule_matches, tokens, i, analyzed_token, token, lowercase_readings,
                                         sentence):
        is_upper_first = is_upper_case(_first_char(token))
        lc_word = lowercase_first_char(tokens[i].token)
        if is_upper_first and \
                _java_length(token) > 1 and \
                not tokens[i].ignored_by_speller and \
                not tokens[i].immunized and \
                tokens[i - 1].token not in _SENTENCE_START_EXCEPTIONS and \
                token not in _EXCEPTIONS and \
                not is_all_uppercase(token) and \
                not self._is_language(i, tokens, token) and \
                not self._is_probably_city(i, tokens, token) and \
                not _has_reading_of_type(analyzed_token, POSType.PROPER_NOUN) and \
                not analyzed_token.is_sentence_end and \
                not self._is_ellipsis(i, tokens) and \
                not self._is_numbering(i, tokens) and \
                not self._is_nominalization(i, tokens, token, lowercase_readings) and \
                not self._is_adverb_and_nominalization(i, tokens) and \
                not self._is_special_case(i, tokens) and \
                not self._is_adjective_as_noun(i, tokens, lowercase_readings) and \
                not self._is_singular_imperative(lowercase_readings, tokens[i]) and \
                not self._is_exception_phrase(i, tokens) and \
                not (i == 2 and tokens[i - 1].token == '“') and \
                not self._is_case_typo(tokens[i].token) and \
                not self._followed_by_gender_gap(tokens, i) and \
                not self._is_noun_with_verb_reading(i, tokens) and \
                not self._is_invisible_separator(i - 1, tokens) and \
                not self._is_misspelled(lc_word):
            # (_is_singular_imperative: too many names like "Kusch", "Klemm" etc.;
            # the closing quote at sentence start: https://github.com/languagetool-org/languagetool/issues/2558)
            if tokens[i - 1].token == ':':
                # allow short question sentences like "Warum? Und warum?" after colon
                if self.is_question_equivalent_after_colon(i, tokens):
                    return
                subarray = tokens[:i]
                if self._is_verb_following(i, tokens, lowercase_readings) or \
                        _count_pos_tag_starting_with(subarray, 'VER') == 0:
                    pass
                else:
                    self._add_rule_match(rule_matches, sentence, COLON_MESSAGE, tokens[i], lc_word)
                return
            self._add_rule_match(rule_matches, sentence, UPPERCASE_MESSAGE, tokens[i], lc_word)

    @staticmethod
    def _followed_by_gender_gap(tokens, i):
        return i + 2 < len(tokens) and tokens[i + 1].token == ':' and \
            _IN_INNEN.fullmatch(tokens[i + 2].token) is not None

    @staticmethod
    def _is_case_typo(token):
        return _TWO_UPPERCASE_CHARS.fullmatch(token) is not None  # e.g. "WUrzeln"

    @staticmethod
    def _is_singular_imperative(lowercase_readings, token):
        return lowercase_readings is not None and lowercase_readings.has_pos_tag_starting_with('VER:IMP:SIN') and \
            token.token != 'Ein' and token.token != 'Eine'

    @staticmethod
    def _is_noun_with_verb_reading(i, tokens):
        return tokens[i].has_pos_tag_starting_with('SUB') and tokens[i].has_pos_tag_starting_with('VER:INF')

    @staticmethod
    def _is_invisible_separator(i, tokens):
        # u2063 is used internally by our browser add-on
        return 0 <= i < len(tokens) and len(tokens[i].token) > 0 and tokens[i].token[0] == '⁣'

    @staticmethod
    def _is_verb_following(i, tokens, lowercase_readings):
        subarray = list(tokens[i:])
        if lowercase_readings is not None:
            subarray[0] = lowercase_readings
        # capitalization after ":" requires an independent clause to follow
        # if there is not a single verb, the tokens cannot be part of an independent clause
        return _count_pos_tag_starting_with(subarray, 'VER:') != 0

    @staticmethod
    def _is_colon_question_word(word):
        return any(java_equals_ignore_case(word, w) for w in _COLON_QUESTION_WORDS)

    def _add_rule_match(self, rule_matches, sentence, msg, token_readings, fixed_word):
        rule_match = RuleMatch(self, sentence, token_readings.start_pos, token_readings.end_pos, msg)
        rule_match.set_suggested_replacement(fixed_word)
        rule_matches.append(rule_match)

    # e.g. "a) bla bla"
    @staticmethod
    def _is_numbering(i, tokens):
        # (no numbering: "Der Vater (51) fuhr nach Rom.")
        return i >= 2 \
            and tokens[i - 1].token in (')', ']') \
            and _NUMERALS_EN.fullmatch(tokens[i - 2].token) is not None \
            and not (i > 3 and tokens[i - 3].token == '('
                     and tokens[i - 4].has_pos_tag_starting_with('SUB:'))

    @staticmethod
    def _is_ellipsis(i, tokens):
        # sentence starts with […]
        return tokens[i - 1].token in (']', ')') and \
            ((i == 4 and tokens[i - 2].token == '…') or (i == 6 and tokens[i - 2].token == '.'))

    def _is_nominalization(self, i, tokens, token, lowercase_readings):
        next_readings = tokens[i + 1] if i < len(tokens) - 1 else None
        # TODO: "vor Schlimmerem", "Er hatte Schlimmes zu befürchten"
        # TODO: wir finden den Fehler in "Die moderne Wissenschaftlich" nicht, weil nicht alle
        # Substantivierungen in den Morphy-Daten stehen (z.B. "Größte" fehlt) und wir deshalb nur
        # eine Abfrage machen, ob der erste Buchstabe groß ist.
        if starts_with_uppercase(token) and not self._is_number(token) and \
                not (self._has_noun_reading(next_readings) or
                     (next_readings is not None and is_numeric(next_readings.token))) and \
                not _ALLE_NM.fullmatch(token):
            if lowercase_readings is not None and lowercase_readings.has_pos_tag('PRP:LOK+TMP+CAU:DAT+AKK'):
                return False
            # Ignore "das Dümmste, was je..." but not "das Dümmste Kind"
            prev_token = tokens[i - 1] if i > 0 else None
            prev_prev_token = tokens[i - 2] if i >= 2 else None
            prev_prev_prev_token = tokens[i - 3] if i >= 3 else None
            prev_token_str = prev_token.token if prev_token is not None else ''
            if (prev_token_str in ('und', 'oder', 'beziehungsweise') and prev_prev_token is not None and
                    (tokens[i].has_partial_pos_tag('SUB') and tokens[i].has_partial_pos_tag(':ADJ'))) or \
                    (prev_prev_token.has_partial_pos_tag('SUB') and not self._has_noun_reading(next_readings) and
                     lowercase_readings is not None and lowercase_readings.has_partial_pos_tag('ADJ') and
                     prev_token_str != ','):
                # "das dabei Erlernte und Erlebte ist ..." -> 'Erlebte' is correct here
                # "die Ausgaben für Umweltschutz und Soziales"
                return True
            if lowercase_readings is not None and lowercase_readings.has_pos_tag('PA1:PRD:GRU:VER'):
                # "aus sechs Überwiegend muslimischen Ländern"
                return False
            return ((prev_token is not None and _IRGEND_ETC.fullmatch(prev_token_str) is not None and
                     tokens[i].has_partial_pos_tag('SUB'))
                    or self._is_number(prev_token_str)) or \
                (_has_partial_tag(prev_token, 'ART', 'PRO:') and
                 not (((i < 4 and len(tokens) > 4) or len(prev_token.readings) == 1 or
                       prev_prev_token.has_lemma('sein')) and
                      prev_token.has_pos_tag_starting_with('PRO:PER:NOM:')) and
                 not prev_token.has_partial_pos_tag(':STD')) or \
                (_has_partial_tag(prev_prev_prev_token, 'ART') and _has_partial_tag(prev_prev_token, 'PRP') and
                 _has_partial_tag(prev_token, 'SUB')) or \
                (_has_partial_tag(prev_prev_token, 'PRO:', 'PRP') and
                 _has_partial_tag(prev_token, 'ADJ', 'ADV', 'PA2', 'PA1')) or \
                (_has_partial_tag(prev_prev_prev_token, 'PRO:', 'PRP') and
                 _has_partial_tag(prev_prev_token, 'ADJ', 'ADV') and
                 _has_partial_tag(prev_token, 'ADJ', 'ADV', 'PA2')) or \
                (tokens[i].has_pos_tag_starting_with('SUB:') and _has_partial_tag(prev_token, 'GEN') and
                 not _has_partial_tag(next_readings, 'PKT'))
            # ("die Verurteilten", "etwas Verrücktes", "ihr Bestes"; "die zum Tode Verurteilten";
            # "etwas schön Verrücktes", "mit aufgewühltem Innerem"; "etwas ganz schön Verrücktes";
            # "Parks Vertraute Choi Soon Sil ist zu drei Jahren Haft verurteilt worden.")
        return False

    def _is_number(self, token):
        if is_numeric(token):
            return True
        lookup = self._lookup(lowercase_first_char(token))
        return lookup is not None and lookup.has_pos_tag('ZAL')

    def _is_adverb_and_nominalization(self, i, tokens):
        prev_prev_token = tokens[i - 2].token if i > 1 else ''
        prev_token = tokens[i - 1] if i > 0 else None
        token = tokens[i].token
        next_readings = tokens[i + 1] if i < len(tokens) - 1 else None
        # ignore "das wirklich Wichtige":
        return java_equals_ignore_case('das', prev_prev_token) and _has_partial_tag(prev_token, 'ADV') \
            and starts_with_uppercase(token) and not self._has_noun_reading(next_readings)

    def _is_special_case(self, i, tokens):
        prev_token = tokens[i - 1].token if i > 1 else ''
        token = tokens[i].token
        next_readings = tokens[i + 1] if i < len(tokens) - 1 else None
        # ignore "im Allgemeinen gilt" but not "im Allgemeinen Fall":
        return java_equals_ignore_case('im', prev_token) and token == 'Allgemeinen' and \
            not self._has_noun_reading(next_readings)

    def _is_adjective_as_noun(self, i, tokens, lowercase_readings):
        prev_token = tokens[i - 1] if i > 0 else None
        next_readings = tokens[i + 1] if i < len(tokens) - 1 else None
        prev_lowercase_readings = None

        if i > 1 and tokens[i - 2].token in _SENTENCE_START_EXCEPTIONS:
            prev_lowercase_readings = self._lookup(prev_token.token.lower())

        # ignore "Der Versuch, Neues zu lernen / Gutes zu tun / Spannendes auszuprobieren"
        is_possibly_followed_by_infinitive = next_readings is not None and next_readings.token == 'zu'
        is_followed_by_infinitive = next_readings is not None and not is_possibly_followed_by_infinitive and \
            next_readings.has_partial_pos_tag('EIZ')
        is_followed_by_possessive_indicator = next_readings is not None and \
            next_readings.token in _POSSESSIVE_INDICATORS

        is_undef_quantifier = prev_token is not None and prev_token.token.lower() in _UNDEFINED_QUANTIFIERS
        is_prev_determiner = prev_token is not None \
            and (_has_partial_tag(prev_token, 'ART', 'PRP', 'ZAL') or
                 _has_partial_tag(prev_lowercase_readings, 'ART', 'PRP', 'ZAL')) \
            and not prev_token.has_partial_pos_tag(':STD')
        is_preceded_by_verb = prev_token is not None and prev_token.matches_pos_tag_regex(_PRECEDED_BY_VERB) and \
            not prev_token.has_lemma('sein')
        if not is_prev_determiner and not is_undef_quantifier and \
                not (is_possibly_followed_by_infinitive or is_followed_by_infinitive) \
                and not (is_preceded_by_verb and lowercase_readings is not None and
                         _has_partial_tag(lowercase_readings, 'ADJ:', 'PA') and next_readings is not None and
                         next_readings.token not in ('und', 'oder', ',')) \
                and not (is_followed_by_possessive_indicator and
                         _has_partial_tag(lowercase_readings, 'ADJ', 'VER')) \
                and not (prev_token is not None and prev_token.has_pos_tag('KON:UNT') and
                         not self._has_noun_reading(next_readings) and next_readings is not None and
                         not next_readings.has_pos_tag('KON:NEB')):
            # ("Wacht auf, Verdammte dieser Welt!")
            prev_prev_token = tokens[i - 2] if i > 1 and prev_token is not None and \
                prev_token.has_partial_pos_tag('ADJ') else None
            # Another check to avoid false alarms for "eine Gruppe Aufständischer starb"
            if not is_preceded_by_verb and lowercase_readings is not None and prev_token is not None:
                if prev_token.has_partial_pos_tag('SUB:') and \
                        lowercase_readings.matches_pos_tag_regex(_ADJ_PA2_GEN_PLU_MAS):
                    return next_readings is not None and not next_readings.has_partial_pos_tag('SUB:')
                elif next_readings is not None and len(next_readings.readings) == 1 and \
                        prev_token.has_pos_tag_starting_with('PRO:PER:NOM:') and \
                        next_readings.has_pos_tag('ADJ:PRD:GRU'):
                    # avoid false alarm "Weil er Unmündige sexuell missbraucht haben soll,..."
                    return True
            # Another check to avoid false alarms for "ein politischer Revolutionär"
            if not _has_partial_tag(prev_prev_token, 'ART', 'PRP', 'ZAL'):
                return False

        # ignore "die Ausgewählten" but not "die Ausgewählten Leute":
        for reading in tokens[i].readings:
            pos_tag = reading.pos_tag
            if (pos_tag is None or 'ADJ' in pos_tag) and not self._has_noun_reading(next_readings) and \
                    not is_numeric(next_readings.token if next_readings is not None else ''):
                if pos_tag is None and _has_partial_tag(lowercase_readings, 'PRP:LOK', 'PA2:PRD:GRU:VER',
                                                        'PA1:PRD:GRU:VER', 'ADJ:PRD:KOM', 'ADV:TMP'):
                    # skip to avoid a false true for, e.g. "Die Zahl ging auf Über 1.000 zurück."/ "Dies gilt
                    # schon lange als Überholt." / "Bis Bald!"
                    # but not for "Er versuchte, Neues zu wagen."
                    pass
                else:
                    return True
        return False

    def _is_language(self, i, tokens, token):
        languages = language_names.get()
        # z.B. "im Japanischen" / z.B. "ins Japanische übersetzt"
        maybe_language = (token.endswith('sch') and token in languages) or \
            _remove_end(_remove_end(token, 'n'), 'e') in languages
        prev_token = tokens[i - 1] if i > 0 else None
        next_readings = tokens[i + 1] if i < len(tokens) - 1 else None
        return maybe_language and (not self._has_noun_reading(next_readings) or
                                   (prev_token is not None and prev_token.token == 'auf'))

    @staticmethod
    def _is_probably_city(i, tokens, token):
        if token in _CITY_PREFIXES:
            next_readings = tokens[i + 1] if i < len(tokens) - 1 else None
            return next_readings is not None and (not next_readings.is_tagged() or
                                                  next_readings.has_pos_tag_starting_with('EIG'))
        return False

    @staticmethod
    def _is_followed_by_relative_or_subordinate_clause(i, tokens):
        if i < len(tokens) - 4:
            return tokens[i + 1].token == ',' and \
                (tokens[i + 2].token in _INTERROGATIVE_PARTICLES or tokens[i + 2].has_pos_tag('KON:UNT'))
        return False

    def _is_exception_phrase(self, i, tokens):
        # (for patterns in exceptionPatterns, for j: if patterns[j] matches the token,
        # compare the token list at i-j; with the patterns indexed by their possible values)
        word = tokens[i].token
        for patterns, j in self._exception_index.get(word, ()):
            if patterns[j].matches(word):
                start_index = i - j
                if compare_lists(tokens, start_index, start_index + len(patterns) - 1, *patterns):
                    return True
        for patterns, j in self._exception_others:
            if patterns[j].matches(word):
                start_index = i - j
                if compare_lists(tokens, start_index, start_index + len(patterns) - 1, *patterns):
                    return True
        return False

    def is_question_equivalent_after_colon(self, i, tokens):
        """Returns true if the token at position i starts a short question
        fragment that forms a valid Satzäquivalent after a colon, per Duden
        rules. Handles: single word: "Ich frage mich: Warum?", with
        conjunction: "Ich frage mich: Und warum?" """
        if i < len(tokens) - 1:
            word = tokens[i].token
            nxt = tokens[i + 1].token
            # "Warum?"
            if self._is_colon_question_word(word) and nxt == '?':
                return True
            # "Und warum?"
            if any(java_equals_ignore_case(word, w) for w in _COLON_QUESTION_CONJUNCTIONS) \
                    and i < len(tokens) - 2 \
                    and self._is_colon_question_word(tokens[i + 1].token) \
                    and tokens[i + 2].token == '?':
                return True
        return False
