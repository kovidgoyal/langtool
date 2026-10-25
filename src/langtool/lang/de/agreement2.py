"""Port of org.languagetool.rules.de.AgreementRule2: simple agreement checker
for German adjective + noun phrases at the beginning of a sentence (e.g.
"Kleiner Haus am Waldrand")."""

import threading

from ...patterns.pattern_token import PatternTokenBuilder, cs_regex, cs_token, pos, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import uppercase_first_char
from .agreement_tools import get_agreement_categories

_ADJ_GRU = ('Allgemein|Ausgiebig|Stilvoll|Link|Direkt|Gegenseitig|Offensichtlich|Weitgehend|Frei|Prinzipiell|'
            'Regelrecht|Kostenlos|Gleichzeitig|Ganzjährig|Überraschend|Entsprechend|Ordentlich|Gelangweilt')


def _anti_patterns():
    # AgreementRule2.ANTI_PATTERNS
    return [
        [cs_regex('Willkommen|Link|Aktuell|Diverse|Flächendeckend|Entsprechende|Angeblich|Gelegentlich|Antizyklisch|'
                  'Unbedingt|Zusätzlich|Natürlich|Äußerlich|Erfolgreich|'
                  'Spät|Länger|Vorrangig|Rechtzeitig|Typisch|Allwöchentlich|Wöchentlich|Inhaltlich|Tagtäglich|'
                  'Täglich|Komplett|'
                  'Genau|Gerade|Bewusst|Vereinzelt|Gänzlich|Ständig|Okay|Meist|Generell|Ausreichend|Genügend|'
                  'Reichlich|'
                  'Regelmäßig(e|es)?|Unregelmäßig|Hauptsächlich'),
         pos_regex('SUB:.*')],  # "Regelmäßig Kiwis und Ananas zu essen...", "Reichlich Inspiration bietet..."
        [cs_regex(_ADJ_GRU), pos_regex('SUB:.*'), pos_regex('VER:.*')],  # "Überraschend Besuch bekommt er dann von ..."
        [cs_regex(_ADJ_GRU), pos_regex('SUB:.*'), pos_regex('PRP.*')],  # "Prinzipiell Anrecht auf eine Vertretung..."
        [cs_regex(_ADJ_GRU), pos_regex('SUB:.*'), token(',')],  # "Weitgehend Konsens, auch über ..."
        [cs_regex('Gut|Schlecht|Existenziell|Ganz|Gering|Viel|Wenig'),
         pos_regex('SUB:.*ADJ')],  # "Existenziell Bedrohte kriegen..."
        [token_regex('Nachhaltig|Direkt'), pos_regex('SUB:NOM:.*'),
         pos_regex('VER:INF:(SFT|NON)')],  # 'nachhaltig Yoga praktizieren'
        [token_regex('\\d0er'), token_regex('Jahren?')],
        [token('Liebe'), token('Mai')],   # Mai = auch Eigenname
        [token('Ganz'), token('Ohr')],
        [token('Klar'), token('Schiff')],
        [token('Echt'), token_regex('Scheiße|Mist')],
        [token('Dickes'), token('Danke')],
        [token('Personal'), token('Shopper')],
        [token('Schwäbisch'), token('Hall')],
        [token('Herzlich'), token('Willkommen')],
        [token('Gut'), token_regex('Ding|Holz')],  # "Gut Ding will Weile haben"
        [token('Urban'), token('Mining')],
        [token('Responsive'), token('Design')],
        [token('Dual'), token('Studierende')],
        [token('Deutsche'), cs_regex('Grammophon|Wohnen')],
        [pos_regex('ADJ.*'), token_regex('.+beamte')],  # "Alarmierte Polizeibeamte"
        [PatternTokenBuilder().token('Anderen').set_skip(5).build(),
         pos_regex('VER:INF:(SFT|NON)')],  # "Anderen Brot und Arbeit ermöglichen - ..."
        [token_regex('echt|absolut|voll|total'), token_regex('Wahnsinn|Klasse')],
        [pos('SENT_START'), pos('ADJ:PRD:GRU'), pos_regex('SUB:NOM:SIN:NEU:INF')],  # "Ruhig Schlafen & Zentral Wohnen"
        [token_regex('voll|voller'), pos_regex('SUB:NOM:SIN:.*')],  # "Voller Mitleid", "Voller Mitleid"
        [token('einzig'), pos_regex('SUB:NOM:.*')],  # "Einzig Fernschüsse brachten Erfolgsaussichten"
        [token_regex('Intelligent|Urban'), token('Design')],
        [token('Alternativ'), token('Berufserfahrung')],  # "Alternativ Berufserfahrung im Bereich ..."
        [token('Maritim'), token('Hotel')],
        [cs_token('Russisch'), cs_token('Brot')],
        [token('ruhig'), cs_token('Blut')],
        [token('Blind'), token_regex('Dates?')],
        [token('Fair'), token('Trade')],
        [token('Frei'), token('Haus')],
        [token('Global'), token('Player')],
        [token('psychisch'), token_regex('Kranken?')],
        [token('sportlich'), token_regex('Aktiven?')],
        [token('politisch'), token_regex('Interessierten?')],
        [token('voraussichtlich'), token_regex('Ende|Anfang')],
        [token_regex('gesetzlich|privat|freiwillig'), token_regex('(Kranken)?Versicherten?')],
        [token('typisch'), pos_regex('SUB:.*'), token_regex('[!?.]')],  # "Typisch November!"
        [token('lecker'), token('Essen')],  # "Lecker Essen an Weihnachten."
        [token('erneut'), pos_regex('SUB:.*')],  # "Erneut Ausgangssperre beschlossen"
        [token('Gesetzlich'), token_regex('Krankenversicherten?')],
        [token('weitgehend'), token('Einigkeit')],      # feste Phrase
        [token('Ernst')],      # Vorname
        [token('Anders')],     # Vorname
        [token('wirklich')],   # "Wirklich Frieden herrscht aber noch nicht"
        [token('gemeinsam')],   # "Gemeinsam Sportler anfeuern"
        [token('wenig')],      # "Wenig Geld - ..."
        [token('weniger')],      # "Weniger Geld - ..."
        [token('unaufgefordert')],      # Unaufgefordert Dinge erledigen
        [token('richtig')],    # "Richtig Kaffee kochen ..."
        [token('weiß')],       # "Weiß Papa, dass ..."
        [token('speziell')],   # "Speziell Flugfähigkeit hat sich unabhängig voneinander ..."
        [token('proaktiv')],   # "Speziell Flugfähigkeit hat sich unabhängig voneinander ..."
        [token('halb')],       # "Halb Traum, halb Wirklichkeit"
        [token('hinter')],     # "Hinter Bäumen"
        [token('vermutlich')],  # "Vermutlich Ende 1813 erkrankte..."
        [token('eventuell')],  # "Eventuell Ende 1813 erkrankte..."
        [token('ausschließlich')],
        [token('ausschliesslich')],
        [token('bloß')],       # "Bloß Anhängerkupplung und solche Dinge..."
        [token('einfach')],    # "Einfach Bescheid sagen ..."
        [token('egal')],
        [token('endlich')],    # "Endlich Mittagspause!"
        [token('unbemerkt')],    # "Unbemerkt Süßigkeiten essen"
        [token('Typisch'), token_regex('Mann|Frau')],    # "Einfach Bescheid sagen ..."
        [token('Ausreichend'), token_regex('Bewegung')],    # "Ausreichend Bewegung ..."
        [token('Genau'), token('Null')],
        [token('wohl')],       # "Wohl Anfang 1725 begegnete Bach ..."
        [token('erst')],       # "Erst X, dann ..."
        [token('lieber')],     # "Lieber X als Y"
        [token('besser')],     # "Besser Brot ohne Butter..."
        [token('laut')],       # "Laut Fernsehen"
        [token('research')],   # engl.
        [token('researchs')],  # engl.
        [token('security')],   # engl.
        [token('business')],   # oft engl.
        [token('Universal')],   # oft engl.
        [token('voll'), token('Sorge')],
        [token('Total'), token_regex('Tankstellen?')],
        [token('Ganz'), token('Gentleman')],
        [token('Kurz'), token('Zeit'), token_regex('für|um')],  # Kurz Zeit für einen Call?
        [token('Golden'), token('Gate')],
        [token('Wirtschaftlich'), token_regex('Berechtigte[rn]?')],
        [token('Russisch'), token('Roulette')],
        [token('Clever'), token_regex('Shuttles?')],  # name
        [token('Personal'), token_regex('(Computer|Coach|Trainer|Brand).*')],
        [token_regex('Digital|Fair|Regional|Global|Bilingual|International|National|Visual|Final|Rapid|Dual|Golden|'
                     'Human'),
         token_regex('(Initiative|Office|Connection|Bootcamp|Leadership|Sales|Community|Service|Management|Board|'
                     'Identity|City|Paper|Transfer|Transformation|Power|Shopping|Brand|Master|Gate|Drive|Learning|'
                     'Publishing|Signage|Value|Entertainment|Museum|Register|Society|Union|Institute|Symposium|Style|'
                     'Design|Edition).*')],
        [token('Smart')],
        [token('International'), token_regex('Society|Olympic|Space')],
        [token('GmbH')],
    ]


_ANTI_PATTERNS = None
_ANTI_PATTERNS_LOCK = threading.Lock()


def anti_patterns():
    """AgreementRule2.ANTI_PATTERNS (built once)"""
    global _ANTI_PATTERNS
    if _ANTI_PATTERNS is None:
        with _ANTI_PATTERNS_LOCK:
            if _ANTI_PATTERNS is None:
                _ANTI_PATTERNS = _anti_patterns()
    return _ANTI_PATTERNS


_QUOTES = frozenset(('"', '„', '»', '«'))


class AgreementRule2(Rule):
    """Simple agreement checker for German adjective + noun phrases at the
    beginning of a sentence."""

    # Rule.cacheAntiPatterns: per language
    _anti_patterns = {}
    _lock = threading.Lock()

    def __init__(self, messages, language):
        super().__init__()
        self.language = language
        self.category = Categories.get('GRAMMAR', messages)
        self.add_example_pair('<marker>Kleiner Haus</marker> am Waldrand',
                              '<marker>Kleines Haus</marker> am Waldrand')

    def get_id(self):
        return 'DE_AGREEMENT2'

    def get_description(self):
        return "Kongruenz von Adjektiv und Nomen (unvollständig!), z.B. 'kleiner (kleines) Haus'"

    def estimate_context_for_sure_match(self):
        return max((len(p) for p in anti_patterns()), default=0)

    def get_anti_patterns(self):
        cache = AgreementRule2._anti_patterns
        key = self.language.code
        r = cache.get(key)
        if r is None:
            with AgreementRule2._lock:
                r = cache.get(key)
                if r is None:
                    r = cache[key] = make_anti_patterns(anti_patterns(), self.language)
        return r

    def match(self, sentence):
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).get_tokens_without_whitespace()
        n = len(tokens)
        for i in range(n):
            tok = tokens[i].token
            if not tokens[i].is_sentence_start and tok not in _QUOTES:
                # skip quotes, as these are not relevant
                if i + 1 < n and tokens[i].has_pos_tag_starting_with('ADJ') and \
                        tokens[i + 1].has_pos_tag_starting_with('SUB') and \
                        not tokens[i + 1].has_pos_tag_starting_with('EIG'):
                    if tokens[i].immunized or tokens[i + 1].immunized or tokens[i].token.lower() == 'unter':
                        continue
                    next_token = tokens[i + 2] if i + 2 < n else None
                    if next_token is not None and next_token.has_pos_tag_starting_with('SUB'):
                        # no alarm for e.g. "Deutscher Taschenbuch Verlag"
                        break
                    rule_match = self._check_adj_noun_agreement(tokens[i], tokens[i + 1], sentence)
                    if rule_match is not None:
                        rule_match.set_suggested_replacements(self._get_suggestions(tokens, i))
                        rule_matches.append(rule_match)
                        break
                else:
                    # rule only works at sentence start (minus quotes)
                    break
        return self.to_rule_match_array(rule_matches)

    def _get_suggestions(self, tokens, i):
        suggestions = []
        adj_token = tokens[i].readings[0]
        synthesizer = self.language.synthesizer
        for noun_token in tokens[i + 1].readings:
            if noun_token.pos_tag is None:
                continue
            gender = _get_gender(noun_token)
            if gender is None:
                continue
            number = _get_number(noun_token)
            if number is None:
                continue
            forms = synthesizer.synthesize(adj_token, 'ADJ:NOM:' + number + ':' + gender + ':GRU:SOL', True)
            for s in forms:
                full_sugg = uppercase_first_char(s) + ' ' + noun_token.token
                if full_sugg not in suggestions:
                    suggestions.append(full_sugg)
        return suggestions

    def _check_adj_noun_agreement(self, token1, token2, sentence):
        common = self._retain_common_categories(token1, token2)
        rule_match = None
        if not common:
            msg = ("Möglicherweise fehlende grammatikalische Übereinstimmung zwischen Adjektiv und "
                   "Nomen bezüglich Kasus, Numerus oder Genus. Beispiel: 'kleiner Haus' statt 'kleines Haus'")
            short_msg = 'Möglicherweise keine Übereinstimmung bezüglich Kasus, Numerus oder Genus'
            rule_match = RuleMatch(self, sentence, token1.start_pos, token2.end_pos, msg, short_msg)
        return rule_match

    @staticmethod
    def _retain_common_categories(token1, token2):
        # finds more error but also more false alarms? see commented out cases in testSuggestion():
        # set1 = get_agreement_sol_categories(token1, frozenset())
        set1 = get_agreement_categories(token1, frozenset(), False)
        set2 = get_agreement_categories(token2, frozenset(), False)
        return set1 & set2


def _get_gender(noun_token):
    pos_tag = noun_token.pos_tag
    if ':MAS' in pos_tag:
        return 'MAS'
    if ':FEM' in pos_tag:
        return 'FEM'
    if ':NEU' in pos_tag:
        return 'NEU'
    return None


def _get_number(noun_token):
    pos_tag = noun_token.pos_tag
    if ':SIN:' in pos_tag:
        return 'SIN'
    if ':PLU:' in pos_tag:
        return 'PLU'
    return None
