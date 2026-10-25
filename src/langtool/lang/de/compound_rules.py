"""Ports of the German compound rules (org.languagetool.rules.de):
GermanCompoundRule, SwissCompoundRule (with SwissExpander),
CompoundCoherencyRule, CompoundInfinitivRule and ProhibitedCompoundRule
(with its Pair class).

ProhibitedCompoundRule needs a language model (Java: created by
German.getRelevantLanguageModelRules only with n-gram data): it takes an
object with a method get_count(word) -> int (BaseLanguageModel.getCount),
there is no n-gram language model in langtool. The speller used by
GermanCompoundRule and ProhibitedCompoundRule is the default spelling rule
of German (Germany) (its misspelling check), CompoundInfinitivRule uses a
morfologik speller of /de/hunspell/de_DE.dict like Java. LinguServices
(LibreOffice/OpenOffice only) are not supported."""

import threading

from ... import jregex
from ...patterns.pattern_token import PatternTokenBuilder, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.abstract_rules import (AbstractCompoundRule, SpecificIdRule, load_compound_rule_data, to_id,
                                     java_hash_set_order, _read_lines, _resource_file)
from ...rules.base import RuleMatch
from ...rules.core import CoreRule, CoreTextLevelRule
from ...tools import (char_to_upper, is_numeric, is_upper_case, java_equals_ignore_case, java_split, java_trim,
                      lowercase_first_char, starts_with_uppercase, uppercase_first_char)
from .old_spelling import AhoCorasickSearch


def _germany_german():
    from ...api import get_language
    return get_language('de-DE')


# --- GermanCompoundRule, SwissCompoundRule ---------------------------------

def _german_compound_anti_patterns():
    return [
        [  # "Die Bürger konnten an die 900 Meter Kabel in Eigenregie verlegen."
            token_regex('an|um'), token('die'), token_regex('\\d+')],
        [  # "Lohnt sich die Werbung vom ausgegebenen Euro aus gedacht?"
            PatternTokenBuilder().token_regex('von|vom').set_skip(5).build(), token('aus'), token('gedacht')],
        [  # "Die Bürger konnten an die 900 Meter Kabel in Eigenregie verlegen."
            token_regex('rund|etwa|zirka|cirka|ungefähr|annähernd|grob|wohl|gegen|schätzungsweise'),
            token_regex('\\d+')],
        [  # "Die Bürger konnten ca. 900 Meter Kabel in Eigenregie verlegen."
            token('ca'), token('.'), token_regex('\\d+')],
        [  # Eigenname
            token('Kung'), token('Fu'), token_regex('Panda|Fighting')],
        [  # Eigenname
            token('Harlem'), token('Gospel'), token('Singers')],
        [  # Englisch
            token('Always'), token('on'), token_regex('my|your|the|an?|their')],
        [  # sich selbst gerecht werden
            token_regex('sich|uns|ihm|ihr|mir|euch'), token('selbst'), token_regex('gerecht.*')],
    ]


_lock = threading.Lock()
_compound_anti_patterns = []


def _swiss_expander(line):
    """SwissCompoundRule.SwissExpander.expandLine"""
    if 'ß' in line:
        # accept both, assuming Swiss users sometimes deal with GermanyGerman text
        return [line, line.replace('ß', 'ss')]
    return [line]


class GermanCompoundRule(AbstractCompoundRule):
    """Port of GermanCompoundRule: compounds (from /de/compounds.txt and
    /de/compound-cities.txt) must not be written as separate words."""

    category_id = 'COMPOUNDING'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Dieses Wort wird mit Bindestrich geschrieben.',
                         'Dieses Wort wird zusammengeschrieben.',
                         'Diese Wörter werden zusammengeschrieben oder mit Bindestrich getrennt.',
                         'Zusammenschreibung von Wörtern')
        self.add_example_pair('Wenn es schlimmer wird, solltest Du zum <marker>HNO Arzt</marker> gehen.',
                              'Wenn es schlimmer wird, solltest Du zum <marker>HNO-Arzt</marker> gehen.')

    def get_id(self):
        return 'DE_COMPOUNDS'

    def get_description(self):
        return "Zusammenschreibung von Wörtern, z. B. 'CD-ROM' statt 'CD ROM'"

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/de/compounds.txt', '/de/compound-cities.txt')

    def is_misspelled(self, word):
        speller = _germany_german().get_default_spelling_rule()
        if speller is None:
            # (Java always has the speller; without it, as AbstractCompoundRule.isMisspelled: no word is misspelled)
            return False
        return speller.is_misspelled(word)

    def get_anti_patterns(self):
        if not _compound_anti_patterns:
            with _lock:
                if not _compound_anti_patterns:
                    _compound_anti_patterns.append(
                        make_anti_patterns(_german_compound_anti_patterns(), _germany_german()))
        return _compound_anti_patterns[0]


class SwissCompoundRule(GermanCompoundRule):
    """Port of SwissCompoundRule: GermanCompoundRule with the compounds with
    'ß' also accepted with 'ss'."""

    def get_id(self):
        return 'DE_CH_COMPOUNDS'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/de/compounds.txt', '/de/compound-cities.txt',
                                       expander=_swiss_expander)


# --- CompoundCoherencyRule -------------------------------------------------

def _contains_hyphen_inside(token):
    return '-' in token and not token.startswith('-') and not token.endswith('-')


def _get_lemma(atr):
    lemma_or_null = atr.readings[0].lemma if atr.has_same_lemmas and len(atr.readings) > 0 else None
    if lemma_or_null is not None:
        # our analysis gets lemma "Jugendfoto" for "Jugend-Fotos", we 'fix' that here
        token = atr.token
        if '-' not in lemma_or_null and '-' in token:
            sb = []
            lemma_pos = 0
            token_pos = 0
            while lemma_pos < len(lemma_or_null):
                if token_pos >= len(token):
                    break
                lemma_char = lemma_or_null[lemma_pos]
                token_char = token[token_pos]
                if lemma_char == token_char:
                    sb.append(lemma_char)
                elif token[token_pos] == '-':
                    token_pos += 1  # skip hyphen
                    sb.append('-')
                    if lemma_pos + 1 < len(token) and is_upper_case(token[token_pos]):
                        sb.append(char_to_upper(lemma_char))
                    else:
                        sb.append(lemma_char)
                lemma_pos += 1
                token_pos += 1
            return ''.join(sb)
        return lemma_or_null
    return None


class CompoundCoherencyRule(CoreTextLevelRule):
    """Port of CompoundCoherencyRule: a compound written once with and once
    without hyphen in the same text, e.g. "Zahnärzteverband" and
    "Zahnärzte-Verband"."""

    category_id = 'STYLE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Ein Helpdesk gliedert sich in verschiedene Level. Die Qualität des '
                              '<marker>Help-Desks</marker> ist wichtig.',
                              'Ein Helpdesk gliedert sich in verschiedene Level. Die Qualität des '
                              '<marker>Helpdesks</marker> ist wichtig.')

    def get_id(self):
        return 'DE_COMPOUND_COHERENCY'

    def get_description(self):
        return 'Einheitliche Schreibweise bei Komposita (mit oder ohne Bindestrich)'

    def match(self, sentences, annotated_text=None):
        rule_matches = []
        norm_to_text_occurrences = {}
        pos = 0
        for sentence in sentences:
            for atr in sentence.non_blank_tokens:
                lemma_or_null = _get_lemma(atr)
                token = atr.token
                if not token:
                    continue
                # The whole implementation could be simpler, but this way we also catch cases where
                # the word (and thus its lemma) isn't known.
                lemma = lemma_or_null if lemma_or_null is not None else token
                norm_token = lemma.replace('-', '').lower()
                if is_numeric(norm_token):
                    # avoid messages about "2-3" and "23" both being used
                    break
                text_occ = norm_to_text_occurrences.get(norm_token)
                if text_occ is not None:
                    if not any(java_equals_ignore_case(f, lemma) for f in text_occ):
                        other = text_occ[0]
                        if _contains_hyphen_inside(other) or _contains_hyphen_inside(token):
                            msg = ("Uneinheitliche Verwendung von Bindestrichen. Der Text enthält sowohl '" + token
                                   + "' als auch '" + other + "'.")
                            rule_match = RuleMatch(self, sentence, pos + atr.start_pos, pos + atr.end_pos, msg)
                            if java_equals_ignore_case(token.replace('-', ''), other.replace('-', '')):
                                # might be different inflected forms, so only suggest if really just the hyphen
                                # is different:
                                rule_match.set_suggested_replacement(other)
                            rule_matches.append(rule_match)
                else:
                    norm_to_text_occurrences[norm_token] = [lemma]
            pos += sentence.get_corrected_text_length()
        return rule_matches

    def min_to_check_paragraph(self):
        return -1


# --- CompoundInfinitivRule -------------------------------------------------

def _compound_infinitiv_anti_patterns():
    # NOTE: antipatterns only work when they cover "zu":
    return [
        [token('auf'), token('Nummer'), token('sicher'), token('zu')],
        [  # "Den richtigen Weg zu gehen bedeutet ab und an zu erkennen, dass man eventuell auf der falschen
            # Spur ist."
            token('ab'), token_regex('und|&'), token('an'), token('zu')],
        [  # "Der diensthabende Kollege hatte ganz schön zu tun."
            token('ganz'), token('schön'), token('zu')],
        [  # "Fang dort an zu lesen, wo du aufgehört hast."
            token_regex('fang|fängst|fängt|fangt|fangen|fing|fingen'), pos_regex('ADV.*'), token('an'), token('zu')],
        [token_regex('dazu|darüber'), token('zu'), token('machen')],
        [  # Da Frauen keine Gelegenheit übersehen, sich schön zu machen, pflückte sie eine Orchidee und steckte
            # sie in ihr Haar. (compounding optional)
            token('schön'), token('zu'), token('machen')],
        [token('kurz'), token('davor'), token('zu')],
        [token_regex('Jahr|Monat|Zeit'), token('über'), token('zu')],
        [token('endlich'), token('wieder'), token('zu')],
        [token('bis'), token('hin'), token('zu')],
        [token('von'), token_regex('.*[a-z].*'), token('her'), token('zu')],
        [token_regex('sehr|ganz|äu(ss|ß)erst|zu|nicht|absolut|total|wirklich|möglichst'), pos_regex('ADJ.*'),
         token('zu')],
        [token('Schritt'), token('weiter'), token('zu')],
        [token('und'), token('so'), token('weiter')],
        [token('darauf'), token('zu'), pos_regex('VER.*'), token('dass')],
        [token('darauf'), token('zu'), pos_regex('VER.*'), token(',')],
        [  # "um dort die Nacht über zu stehen."
            token_regex('Spiel|Tag|Nacht|Morgen|Nachmittag|Abend|Zeit|.+zeit|Jahr(zehnt)?|Monat|.+tag|Mittwoch|'
                        'Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember'),
            token('über'), token('zu')],
        [token('kurz'), token('zu'), token('machen')],
        [  # "ohne die Erlaubnis dazu zu haben"
            token('dazu'), token('zu'), token('haben')],
        [  # "Er hatte nichts weiter zu sagen"
            token_regex('deutlich|viel|Stück|nichts|nix|noch'), token('weiter'), token('zu')],
        [  # "Auf und ab zu schreiten"
            token('auf'), token_regex('und|&|oder|\\/'), PatternTokenBuilder().pos_regex('ADV.*').min(0).build(),
            token('ab'), token('zu')],
        [token('zu'), pos_regex('ADJ.*'), token('zu')],
        [  # "Hin und her zu laufen"
            token('hin'), token_regex('und|&|oder|\\/'), PatternTokenBuilder().pos_regex('ADV.*').min(0).build(),
            token('her'), token('zu')],
        [  # "Hoch und runter zu laufen"
            token_regex('rauf|hoch'), token_regex('und|&|oder|\\/'),
            PatternTokenBuilder().pos_regex('ADV.*').min(0).build(), token('runter'), token('zu')],
        [  # Sie scheint aus Spanien heraus zu kaufen
            PatternTokenBuilder().token('aus').set_skip(3).build(), token('heraus'), token('zu')],
    ]


_ADJ_EXCEPTION = ('schwer', 'klar', 'verloren', 'bekannt', 'rot', 'blau', 'gelb', 'grün', 'schwarz', 'weiß',
                  'fertig', 'neu')
_PUNCTUATION = frozenset(('.', '?', '!', '…', ':', ';', ',', '(', ')', '[', ']'))
_infinitiv_anti_patterns = {}
_speller = []


def _de_de_speller(language):
    """new Speller(MorfologikSpeller.getDictionaryWithCaching("/de/hunspell/de_DE.dict"))"""
    if not _speller:
        with _lock:
            if not _speller:
                from ...spelling import MorfologikSpeller, SpellerMetadata, _FSAWords
                d = language.dictionary('de/hunspell/de_DE.dict')
                _speller.append(MorfologikSpeller(_FSAWords(d.fsa), SpellerMetadata(d.metadata)))
    return _speller[0]


class CompoundInfinitivRule(CoreRule):
    """Port of CompoundInfinitivRule (by Fred Kruse): the compound spelling
    of the infinitive clause (Erweiterter Infinitiv mit zu), e.g. "sicher zu
    gehen" -> "sicherzugehen"."""

    category_id = 'COMPOUNDING'
    issue_type = 'Misspelling'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language)
        self.add_example_pair('Er überprüfte die Rechnungen noch einmal, um <marker>sicher zu gehen</marker>.',
                              'Er überprüfte die Rechnungen noch einmal, um <marker>sicherzugehen</marker>.')
        self.lang = language
        self.speller = None
        self.url = 'https://languagetool.org/insights/de/beitrag/zu-zusammen-oder-getrennt/'

    def get_id(self):
        return 'COMPOUND_INFINITIV_RULE'

    def get_description(self):
        return 'Erweiterter Infinitiv mit zu (Zusammenschreibung)'

    @staticmethod
    def _is_infinitiv(token):
        return token.has_pos_tag_starting_with('VER:INF')

    def _is_misspelled(self, word):
        word = lowercase_first_char(word)
        if self.speller is not None:
            return self.speller.is_misspelled(word)
        raise RuntimeError('LinguServices or Speller must be not null to check spelling in CompoundInfinitivRule')

    @staticmethod
    def _is_relevant(token):
        return token.has_pos_tag('ZUS') and not java_equals_ignore_case('um', token.token)

    @staticmethod
    def _get_lemma(token):
        if token is not None:
            for reading in token.readings:
                if reading.lemma is not None:
                    return reading.lemma
        return None

    def _is_exception(self, tokens, n):
        if tokens[n - 2].has_pos_tag_starting_with('VER'):
            return True
        if tokens[n - 1].token in _ADJ_EXCEPTION:
            return True
        prev = tokens[n - 1].token
        nxt = tokens[n + 1].token
        if nxt == 'sagen' and (prev == 'weiter' or prev == 'dazu'):
            return True
        if (nxt == 'tragen' or nxt == 'machen') and prev == 'davon':
            return True
        if nxt == 'geben' and prev == 'daran':
            return True
        if nxt == 'gehen' and prev == 'ab':
            return True
        if nxt == 'errichten' and prev == 'wieder':
            return True
        verb = None
        i = n - 2
        while i > 0 and not self._is_punctuation(tokens[i].token):
            if tokens[i].has_pos_tag_starting_with('VER:IMP'):
                lemma = self._get_lemma(tokens[i])
                verb = lemma.lower() if lemma is not None else None
            elif tokens[i].has_pos_tag_starting_with('VER'):
                verb = tokens[i].token.lower()
            elif tokens[i].token == 'Fang':
                verb = 'fangen'
            if verb is not None:
                if not self._is_misspelled(prev + verb):
                    return True
                else:
                    break
            i -= 1
        if prev == 'aus' or prev == 'an':
            i = n - 2
            while i > 0 and not self._is_punctuation(tokens[i].token):
                if tokens[i].token == 'von' or tokens[i].token == 'vom':
                    return True
                i -= 1
        if prev == 'her':
            i = n - 2
            while i > 0 and not self._is_punctuation(tokens[i].token):
                if tokens[i].token == 'vor':
                    return True
                i -= 1
        return False

    def get_anti_patterns(self):
        key = self.lang.code if self.lang is not None else None
        r = _infinitiv_anti_patterns.get(key)
        if r is None:
            with _lock:
                r = _infinitiv_anti_patterns.get(key)
                if r is None:
                    r = _infinitiv_anti_patterns[key] = make_anti_patterns(_compound_infinitiv_anti_patterns(),
                                                                           self.lang)
        return r

    def match(self, sentence):
        if self.speller is None:
            # speller can not initialized by constructor because of temporary initialization of LanguageTool in
            # other rules, which leads to problems in LO/OO extension
            self.speller = _de_de_speller(self.lang)
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        for i in range(2, len(tokens) - 1):
            if tokens[i].token == 'zu' \
                    and self._is_infinitiv(tokens[i + 1]) \
                    and self._is_relevant(tokens[i - 1]) \
                    and not tokens[i].immunized \
                    and not self._is_exception(tokens, i) \
                    and not self._is_misspelled(tokens[i - 1].token + tokens[i + 1].token):
                msg = ("Wenn der erweiterte Infinitiv von dem Verb '" + tokens[i - 1].token + tokens[i + 1].token
                       + "' abgeleitet ist, sollte er zusammengeschrieben werden.")
                rule_match = RuleMatch(self, sentence, tokens[i - 1].start_pos, tokens[i + 1].end_pos, msg)
                rule_match.set_suggested_replacements([tokens[i - 1].token + tokens[i].token + tokens[i + 1].token])
                rule_matches.append(rule_match)
        return rule_matches

    @staticmethod
    def _is_punctuation(word):
        return word is not None and len(word) == 1 and word in _PUNCTUATION


# --- ProhibitedCompoundRule ------------------------------------------------

class Pair:
    """ProhibitedCompoundRule.Pair"""

    __slots__ = ('part1', 'part1_desc', 'part2', 'part2_desc')

    def __init__(self, part1, part1_desc, part2, part2_desc):
        self.part1 = part1
        self.part1_desc = part1_desc
        self.part2 = part2
        self.part2_desc = part2_desc

    def __repr__(self):
        return self.part1 + '/' + self.part2


_LOWERCASE_PAIRS = (
    # NOTES:
    # * words here must be all-lowercase
    # * no need to add words from confusion_sets.txt, they will be used automatically (if starting with
    #   uppercase char)
    Pair('knoten', 'Verschlingung von Fäden', 'konten', "Plural von 'Konto'"),
    Pair('schaf', 'Tier', 'schaft', "'-schaft' (Element zur Wortbildung, z. B. 'Freundschaft')"),
    Pair('schafen', "Dativ Plural von 'Schaf'", 'schaften',
         "'-schaften' (Element zur Wortbildung, z. B. 'Freundschaften')"),
    Pair('alpen', 'Hochgebirge in Mittel- und Südeuropa', 'alben', "Plural von 'Album'"),
    Pair('pillen', 'Tabletten', 'pullen', "Plural von 'Pulle' (Flasche)"),
    Pair('tauben', 'Vogelart', 'trauben', 'Obstsorte'),
    Pair('panel', 'ausgewählte Personengruppe', 'paneel', 'Platte für Wand- und Deckenverkleidungen'),
    Pair('nabe', 'Mittelteil eines Rades', 'narbe', 'verheilende Wunde'),
    Pair('first', 'höchste Kante an einem geneigten Dach', 'frist', 'spätester Zeitpunkt'),
    Pair('koma', 'Zustand tiefer Bewusstlosigkeit', 'komma', 'Satzzeichen'),
    Pair('korn', 'Getreide sowie dessen Frucht', 'kron', "Vorsilbe z.B. in 'Kronkorken'"),
    Pair('bauten', "Form von 'Bau' (Bauwerk, Haus, ...)", 'beuten', "Form von 'Beute'"),
    Pair('file', "engl. 'Datei'", 'filet', 'ein Stück Fleisch oder Fisch'),
    Pair('zecke', 'blutsaugender Parasit', 'zwecke', "Dativ von 'Zweck' (Ziel)"),
    Pair('frucht', 'Teil einer Pflanze; Obst', 'furcht', 'Angst'),
    Pair('rate', 'Verhältnis zwischen zwei Größen', 'ratte', 'Nagetier'),
    Pair('posten', 'Arbeitsplatz, Wachposten', 'posen', 'Pose: betonte Körperhaltung'),
    Pair('himmel', 'Bereich über der Erde', 'hummel', 'Insekt'),
    Pair('server', 'Computer', 'servier', "zu 'servieren'"),
    Pair('ziege', 'Tier', 'ziegel', 'Ziegelstein'),
    Pair('robe', 'Kleidungsstück', 'probe', 'Test, Kontrolle'),
    Pair('mode', 'Kleidung', 'monde', 'Begleiter eines Planeten'),
    Pair('eigen', "'selbst', z.B. 'Eigenzitat'", 'eingen', 'Möglicher Tippfehler'),
    Pair('stümpfe', 'Rest eines Körpergliedes', 'strümpfe', 'Bekleidungsstück für den Fuß'),
    Pair('gelände', 'Gebiet', 'geländer', 'Konstruktion zum Festhalten entlang von Treppen'),
    Pair('tropen', 'feuchtwarme Gebiete am Äquator', 'tropfen', 'kleine Menge Flüssigkeit'),
    Pair('enge', 'Mangel an Platz', 'menge', 'Anzahl an Einheiten'),
    Pair('ritt', 'Reiten', 'tritt', 'Aufsetzen eines Fußes'),
    Pair('beine', 'Körperteil', 'biene', 'Insekt'),
    Pair('rebe', 'Weinrebe', 'reibe', 'Küchenreibe'),
    Pair('ass', 'Spielkarte', 'pass', 'Reisepass; Übergang durch ein Gebirge'),
    Pair('türmer', 'Turmwächter', 'türme', "Plural von 'Turm' (Bauwerk)"),
    Pair('soge', 'ziehende Strömungen', 'sorge', 'bedrückendes Gefühl'),
    Pair('panne', 'technischer Defekt', 'spanne', 'Zeitraum'),
    Pair('elfer', 'Elfmeter', 'helfer', 'Person, die hilft'),
    Pair('gase', "Plural von 'Gas' (Aggregatzustand)", 'gasse', 'kleine Straße'),
    Pair('ekel', 'Abscheu', 'enkel', 'Kind eines eigenen Kindes'),
    Pair('reis', 'Nahrungsmittel', 'reise', 'Ausflug/Fahrt'),
    Pair('hüte', 'Kopfbedeckungen', 'häute', "Plural von 'Haut'"),
    Pair('werbereich', None, 'erbereich', None),
    Pair('lage', 'Position', 'alge', 'im Wasser lebende Organismen'),
    Pair('sphäre', 'Kugel', 'spähreh', None),
    Pair('schenke', 'Gastwirtschaft (auch: Schänke)', 'schenkel', 'Ober- und Unterschenkel'),
    Pair('mai', 'Monat nach April', 'mail', 'E-Mail'),
    Pair('pump', "'auf Pump': umgangssprachlich für 'auf Kredit'", 'pumpe', 'Gerät zur Beförderung von Flüssigkeiten'),
    Pair('mitte', 'zentral', 'mittel', 'Methode, um etwas zu erreichen'),
    Pair('fein', 'feinkörnig, genau, gut', 'feind', 'Gegner'),
    Pair('traum', 'Erleben während des Schlafes', 'trauma', 'Verletzung'),
    Pair('name', "Bezeichnung (z.B. 'Vorname')", 'nahme', "zu 'nehmen' (z.B. 'Teilnahme')"),
    Pair('bart', 'Haarbewuchs im Gesicht', 'dart', 'Wurfpfeil'),
    Pair('hart', 'fest', 'dart', 'Wurfpfeil'),
    Pair('speiche', 'Verbindung zwischen Nabe und Felge beim Rad', 'speicher', 'Lagerraum'),
    Pair('kart', 'Gokart (Fahrzeug)', 'karte', 'Fahrkarte, Postkarte, Landkarte, ...'),
    Pair('karts', 'Kart = Gokart (Fahrzeug)', 'karte', 'Fahrkarte, Postkarte, Landkarte, ...'),
    Pair('kiefer', 'knöcherner Teil des Schädels', 'kiefern', 'Kieferngewächse (Baum)'),
    Pair('gel', 'dickflüssige Masse', 'geld', 'Zahlungsmittel'),
    Pair('kamp', 'Flurname für ein Stück Land', 'kampf', 'Auseinandersetzung'),
    Pair('läuse', 'Insekt', 'läufe', 'Bewegungsart'),
    Pair('läusen', 'Insekt', 'läufen', 'Bewegungsart'),
    Pair('ruck', 'plötzliche Bewegung', 'druck', 'Belastung'),
    Pair('brüste', 'Plural von Brust', 'bürste', 'Gerät mit Borsten, z.B. zum Reinigen'),
    Pair('attraktion', 'Sehenswürdigkeit', 'akttaktion', 'vermutlicher Tippfehler'),
    Pair('turn', "zu 'turnen'", 'turm', 'hohes Bauwerk'),
    Pair('mit', 'Präposition', 'miet', "zu 'Miete' (Überlassung gegen Bezahlung)"),
    Pair('bart', 'Behaarung im Gesicht', 'brat', "zu 'braten', z.B. 'Bratkartoffel'"),
    Pair('uhr', 'Instrument zur Zeitmessung', 'ur', 'ursprünglich'),
    Pair('abschluss', 'Ende', 'abschuss', 'Vorgang des Abschießens, z.B. mit einer Waffe'),
    Pair('brache', 'verlassenes Grundstück', 'branche', 'Wirtschaftszweig'),
    Pair('wieder', 'erneut, wiederholt, nochmal (Wiederholung, Wiedervorlage, ...)', 'wider',
         'gegen, entgegen (Widerwille, Widerstand, Widerspruch, ...)'),
    Pair('leer', 'ohne Inhalt', 'lehr', 'bezogen auf Ausbildung und Wissen'),
    Pair('gewerbe', 'wirtschaftliche Tätigkeit', 'gewebe', 'gewebter Stoff; Verbund ähnlicher Zellen'),
    Pair('klima', 'langfristige Wetterzustände', 'lima', 'Hauptstadt von Peru'),
    Pair('modell', 'vereinfachtes Abbild der Wirklichkeit', 'model', 'Fotomodell'),
    Pair('häufigkeit', 'Anzahl von Ereignissen', 'häutigkeit', 'z.B. in Dunkelhäutigkeit'),
    Pair('hin', 'in Richtung', 'hirn', 'Gehirn, Denkapparat'),
    Pair('verklärung', 'Beschönigung, Darstellung in einem besseren Licht', 'erklärung',
         'Darstellung, Erläuterung'),
    Pair('punk', 'Jugendkultur', 'punkt', 'Satzzeichen'),
    Pair('haft', 'Freiheitsentzug', 'schaft', '-schaft (Element zur Wortbildung)'),
    Pair('stande', "zu 'Stand'", 'stange', 'länglicher Gegenstand'),
)
_HERRN_FRAU = jregex.compile('Herrn?|Frau|Dr|Prof|Mag|Hr|Fr|Mr|Mrs|Ms|Fräulein')
_IGNORE_WORDS = ('Die', 'De')
_BLACKLIST_REGEX = tuple(jregex.compile('.*' + k + '.*') for k in (
    'Lande(basis|basen|region|gebiets?|gebieten?|regionen|betriebs?|betrieben?|offizieren?|bereichs?|bereichen?|'
    'einrichtung|einrichtungen|massen?|plans?|versuchs?|versuchen?)',  # vs. Landes
    'Model(vertrags?|verträgen?|erfahrung|erfahrungen|szene|welt)',
    '(Raum|Surf|Jazz|Herbst|Gymnastik|Normal)schuhen?',
    'preis',  # Getränkepreis etc.
    'reisähnlich(e|e[nmrs])?',
    'neugestartet(e|e[nmrs])?',
    'reisender',  # Ägyptenreisender etc.
    '[a-zöäüß]+sender',  # wg. sende/sender, z.B. bremsender, abzulassender
    'gra(ph|f)ische?',  # kosmografisch etc.
    'gra(ph|f)ische[rsnm]',  # kosmografischen etc.
    'gra(ph|f)s?$',  # Elektrokardiograph
    'gra(ph|f)en',  # Elektrokardiographen
    'gra(ph|f)in',  # Demographin/Demografin
    'gra(ph|f)ik',  # Kunstgrafik
    'gra(ph|f)ie',  # Geographie
    'Gra(ph|f)its?',  # Grafit/Graphit
    '.+gra(ph|f)its?',  # ...grafit/graphit
))
_CONFUSION_LINE = jregex.compile('\\s*(;|->)\\s*')
_COMMENT = jregex.compile('\\s*#.*')
_COMMENT2 = jregex.compile('#.*')
_prohibited_data = []
_word_list_cache = {}


def _add_all_case_variants(candidate_pairs, lc_pair):
    candidate_pairs.append(Pair(lc_pair.part1, lc_pair.part1_desc, lc_pair.part2, lc_pair.part2_desc))
    uc_part1 = uppercase_first_char(lc_pair.part1)
    uc_part2 = uppercase_first_char(lc_pair.part2)
    if lc_pair.part1 != uc_part1 or lc_pair.part2 != uc_part2:
        candidate_pairs.append(Pair(uc_part1, lc_pair.part1_desc, uc_part2, lc_pair.part2_desc))


def _add_upper_case_variants(pairs):
    for lc_pair in _LOWERCASE_PAIRS:
        if starts_with_uppercase(lc_pair.part1):
            raise ValueError('Use all-lowercase word in ProhibitedCompoundRule: ' + lc_pair.part1)
        if starts_with_uppercase(lc_pair.part2):
            raise ValueError('Use all-lowercase word in ProhibitedCompoundRule: ' + lc_pair.part2)
        _add_all_case_variants(pairs, lc_pair)


def load_confusion_pairs(path):
    """ConfusionSetLoader.loadConfusionPairs (without word definitions, there
    is no /de/word_definitions.txt): a dict word -> list of pairs, a pair is
    a tuple of two (word, description) terms; the dict is in the iteration
    order of the Java HashMap."""
    m = {}
    for line in _read_lines(path):
        if line.startswith('#') or not java_trim(line):
            continue
        parts = _split_regex(_CONFUSION_LINE, jregex.java_replace(_COMMENT, '', line, 1))
        if len(parts) != 3:
            raise RuntimeError("Unexpected format: '" + line + "' - expected three semicolon-separated values: word1; "
                               "word2; factor")
        bidirectional = ' -> ' not in jregex.java_replace(_COMMENT2, '', line, 1)
        confusion_strings = []
        loaded_for_set = set()
        prev_word = None
        for part in parts[:-1]:
            sub_parts = java_split(part, '|')
            word = sub_parts[0]
            if bidirectional and prev_word is not None and word < prev_word:
                raise RuntimeError('Order words alphabetically per line in the confusion set file: ' + line
                                   + ': found ' + word + ' after ' + prev_word)
            prev_word = word
            description = sub_parts[1] if len(sub_parts) == 2 else None
            if word in loaded_for_set:
                raise RuntimeError("Word appears twice in same confusion set: '" + word + "'")
            confusion_strings.append((word, description))
            loaded_for_set.add(word)
        factor = int(parts[-1])
        if factor < 1:
            raise ValueError('factor must be >= 1: %d' % factor)
        if bidirectional:
            pairs = [(confusion_strings[0], confusion_strings[1]), (confusion_strings[1], confusion_strings[0])]
        else:
            pairs = [(confusion_strings[0], confusion_strings[1])]
        for pair in pairs:
            for cs in confusion_strings:
                m.setdefault(cs[0], []).append(pair)
    return {k: m[k] for k in java_hash_set_order(list(m))}


def _split_regex(pattern, s):
    """String.split(regex): trailing empty strings removed"""
    parts = []
    last = 0
    for m in pattern.finditer(s):
        if m.end() == 0:
            continue  # a zero-width match at the beginning never produces an empty leading substring
        parts.append(s[last:m.start()])
        last = m.end()
    parts.append(s[last:])
    while parts and parts[-1] == '':
        parts.pop()
    return parts if parts else ([s] if s == '' else [])


def _add_items_from_confusion_sets(language, pairs, confusion_sets_file, is_upper_case):
    confusion_pairs = load_confusion_pairs(_resource_file(language, confusion_sets_file))
    for pair_list in confusion_pairs.values():
        for pair in pair_list:
            all_upper = all(starts_with_uppercase(k[0]) and k[0] not in _IGNORE_WORDS for k in pair)
            if all_upper or not is_upper_case:
                part1, part2 = pair
                pairs.append(Pair(part1[0], part1[1], part2[0], part2[1]))
                if is_upper_case:
                    pairs.append(Pair(lowercase_first_char(part1[0]), part1[1], lowercase_first_char(part2[0]),
                                      part2[1]))
                else:
                    pairs.append(Pair(uppercase_first_char(part1[0]), part1[1], uppercase_first_char(part2[0]),
                                      part2[1]))


def setup_aho_corasick_search(pairs, pair_map):
    """ProhibitedCompoundRule.setupAhoCorasickSearch: fills pair_map and
    returns the search (built from a TreeMap)"""
    keys = set()
    for pair in pairs:
        keys.add(pair.part1)
        keys.add(pair.part2)
        pair_map.setdefault(pair.part1, []).append(pair)
        pair_map.setdefault(pair.part2, []).append(pair)
    return AhoCorasickSearch((k, k) for k in sorted(keys, key=lambda k: k.encode('utf-16-be')))


def _prohibited_compound_data(language):
    if not _prohibited_data:
        with _lock:
            if not _prohibited_data:
                pairs = []
                pair_map = {}
                _add_upper_case_variants(pairs)
                _add_items_from_confusion_sets(language, pairs, '/de/confusion_sets.txt', True)
                searcher = setup_aho_corasick_search(pairs, pair_map)
                _prohibited_data.append((searcher, pair_map))
    return _prohibited_data[0]


def _load_word_set(language, path):
    """the cache of ProhibitedCompoundRule: the words of a resource file
    (comments removed, trimmed)"""
    r = _word_list_cache.get(path)
    if r is None:
        words = set()
        for line in _read_lines(_resource_file(language, path)):
            if not line.startswith('#'):
                words.add(java_trim(jregex.java_replace(_COMMENT2, '', line, 1)))
        r = _word_list_cache[path] = frozenset(words)
    return r


class ProhibitedCompoundRule(CoreRule):
    """Port of ProhibitedCompoundRule: probably wrong compounds like
    'Lehrzeile' if 'Leerzeile' is more frequent (according to the language
    model lm, an object with get_count(word))."""

    RULE_ID = 'DE_PROHIBITED_COMPOUNDS'
    category_id = 'TYPOS'

    def __init__(self, messages, lm, user_config, language):
        super().__init__(messages, language)
        if lm is None:
            raise ValueError('ProhibitedCompoundRule needs a language model')
        self.lm = lm
        self.aho_corasick_search, self.pair_map = _prohibited_compound_data(language)
        self.confusion_pair = None  # specify single pair for evaluation
        self.add_example_pair('Da steht eine <marker>Lehrzeile</marker> zu viel.',
                              'Da steht eine <marker>Leerzeile</marker> zu viel.')

    def get_id(self):
        return self.RULE_ID

    def get_description(self):
        return "Markiert wahrscheinlich falsche Komposita wie 'Lehrzeile', wenn 'Leerzeile' häufiger vorkommt."

    def match(self, sentence):
        rule_matches = []
        prev_readings = None
        for readings in sentence.non_blank_tokens:
            tmp_word = readings.token
            if prev_readings is not None and prev_readings.has_any_partial_pos_tag('EIG:') and \
                    starts_with_uppercase(tmp_word) and \
                    (readings.has_any_partial_pos_tag('EIG:') or readings.is_pos_tag_unknown):
                # assume name, e.g. "Bianca Baalhorn" (avoid: Baalhorn => Ballhorn)
                continue
            if prev_readings is not None and _HERRN_FRAU.fullmatch(prev_readings.token):
                # assume name, e.g. "Herr Eiswert" (avoid: Eiswert -> Eiswelt)
                continue
            words_parts = java_split(tmp_word, '-')
            parts_start_pos = 0
            for word_part in words_parts:
                parts_start_pos = self._get_matches(sentence, rule_matches, readings, parts_start_pos, word_part, 0)
            no_hyphens = self.remove_hyphens_and_adapt_case(tmp_word)
            if no_hyphens is not None:
                self._get_matches(sentence, rule_matches, readings, 0, no_hyphens, len(tmp_word) - len(no_hyphens))
            prev_readings = readings
        return rule_matches

    def _is_misspelled(self, word):
        speller = _germany_german().get_default_spelling_rule()
        if speller is None:
            raise ValueError('No default spelling rule for de-DE')
        return speller.is_misspelled(word)

    def _get_matches(self, sentence, rule_matches, readings, parts_start_pos, word_part, to_pos_correction):
        # optimizations:
        # only nouns can be compounds
        # all parts are at least 3 characters long -> words must have at least 6 characters
        if (readings.is_tagged() and not readings.has_partial_pos_tag('SUB')) and \
                not readings.has_pos_tag_starting_with('EIG:') or len(word_part) <= 6:
            # EIG: e.g. "Obstdeutschland" -> "Ostdeutschland"
            parts_start_pos += len(word_part) + 1
            return parts_start_pos
        candidate_pairs = []
        # ignore other pair when confusionPair is set (-> running for evaluation)
        if self.confusion_pair is None:
            # might get duplicates, but since we only ever allow one match per word it doesn't matter
            for _begin, _end, value in self.aho_corasick_search.parse_text(word_part):
                pair = self.pair_map.get(value)
                if pair is not None:
                    candidate_pairs.extend(pair)
        else:
            _add_all_case_variants(candidate_pairs, self.confusion_pair)
        weighted_matches = []
        for pair in candidate_pairs:
            variant = None
            if pair.part1 in word_part:
                variant = jregex.java_replace(jregex.compile(pair.part1), pair.part2, word_part, 1)
            elif pair.part2 in word_part:
                variant = jregex.java_replace(jregex.compile(pair.part2), pair.part1, word_part, 1)
            if variant is None:
                parts_start_pos += len(word_part) + 1
                continue
            word_count = self.lm.get_count(word_part)
            variant_count = self.lm.get_count(variant)
            blacklist = _load_word_set(self.language, '/de/compound_exceptions.txt')
            if variant_count > self.get_threshold() and word_count == 0 and word_part not in blacklist and \
                    not self._is_misspelled(variant) and \
                    not any(k.fullmatch(word_part) for k in _BLACKLIST_REGEX):
                if pair.part1_desc is not None and pair.part2_desc is not None:
                    msg = ('Möglicher Tippfehler. ' + uppercase_first_char(pair.part1) + ': ' + pair.part1_desc + ', '
                           + uppercase_first_char(pair.part2) + ': ' + pair.part2_desc)
                else:
                    msg = 'Möglicher Tippfehler: ' + pair.part1 + '/' + pair.part2
                from_pos = readings.start_pos + parts_start_pos
                to_pos = from_pos + len(word_part) + to_pos_correction
                id = to_id(self.get_id() + '_' + pair.part1 + '_' + pair.part2, self.language)
                desc = ("Markiert wahrscheinlich falsche Komposita mit Teilwort '" + uppercase_first_char(pair.part1)
                        + "' statt '" + uppercase_first_char(pair.part2) + "' und umgekehrt")
                id_rule = SpecificIdRule(id, desc, self.premium, self.category, self.loc_quality_issue_type,
                                         self.tags)
                match = RuleMatch(id_rule, sentence, from_pos, to_pos, msg)
                match.set_suggested_replacement(variant)
                weighted_matches.append((variant_count, match))
        if weighted_matches:
            weighted_matches.sort(key=lambda wm: -wm[0])  # sort by most popular alternative
            rule_matches.append(weighted_matches[0][1])
        parts_start_pos += len(word_part) + 1
        return parts_start_pos

    def get_threshold(self):
        return 0

    def set_confusion_pair(self, confusion_pair):
        """ignore automatically loaded pairs and only match using the given
        Pair (parts are assumed to be lowercase; None to reset), used for
        evaluation"""
        self.confusion_pair = confusion_pair

    @staticmethod
    def remove_hyphens_and_adapt_case(word):
        parts = java_split(word, '-')
        if len(parts) > 1:
            sb = []
            for i, part in enumerate(parts):
                if len(part) <= 1:
                    # don't: S-Bahn -> Sbahn
                    return None
                sb.append(part if i == 0 else lowercase_first_char(part))
            return ''.join(sb)
        return None
