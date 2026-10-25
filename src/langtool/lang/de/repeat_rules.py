"""German repetition rules (port of org.languagetool.rules.de):
GermanRepeatedWordsRule, GermanParagraphRepeatBeginningRule,
GermanWordRepeatBeginningRule and GermanWordRepeatRule."""

import threading

from ... import jregex
from ...patterns.pattern_token import PatternTokenBuilder, cs_token, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.abstract_rules import AbstractRepeatedWordsRule, WordRepeatBeginningRule, load_repeated_words, _rules_file
from ...rules.core import Categories, ParagraphRepeatBeginningRule, WordRepeatRule


def _germany_german():
    """GermanyGerman.getInstance()"""
    from ...api import get_language
    return get_language('de-DE')


# --- GermanRepeatedWordsRule -------------------------------------------------

class GermanRepeatedWordsRule(AbstractRepeatedWordsRule):
    """Port of GermanRepeatedWordsRule: words of /de/synonyms.txt repeated
    within a short distance, with synonyms as suggestions (for
    GermanyGerman, as in Java)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, _germany_german())

    def get_message(self):
        return ('Dieses Wort kommt in einem nahe gelegenen vorherigen Satz bereits vor. Verwenden Sie ein Synonym, '
                'um Ihren Text abwechslungsreicher zu gestalten, außer die Wiederholung ist beabsichtigt.')

    def get_description(self):
        return 'Synonyme für wiederholte Wörter.'

    def get_words_to_check(self):
        return load_repeated_words(_rules_file(self.language, '/de/synonyms.txt'))

    def get_short_message(self):
        return 'Stil: Wortwiederholung'

    def get_synthesizer(self):
        return _germany_german().synthesizer  # GermanSynthesizer.INSTANCE

    def is_exception(self, tokens, i, sent_start, is_capitalized, is_all_upper):
        if is_all_upper or (is_capitalized and not sent_start):
            return True
        return tokens[i].has_pos_tag_starting_with('EIG:')


# --- GermanParagraphRepeatBeginningRule --------------------------------------

class GermanParagraphRepeatBeginningRule(ParagraphRepeatBeginningRule):
    """Port of GermanParagraphRepeatBeginningRule (default off)"""

    rule_id = 'GERMAN_PARAGRAPH_REPEAT_BEGINNING_RULE'

    def is_article(self, token):
        return token.has_pos_tag_starting_with('ART')


# --- GermanWordRepeatBeginningRule -------------------------------------------

_ADVERBS = frozenset(('Auch', 'Anschließend', 'Außerdem', 'Danach', 'Ferner', 'Nebenher', 'Nebenbei', 'Überdies',
                      'Weiterführend', 'Zudem', 'Zusätzlich'))


class GermanWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of GermanWordRepeatBeginningRule"""

    rule_id = 'GERMAN_WORD_REPEAT_BEGINNING_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('Dann hatten wir Freizeit. Dann gab es Essen. <marker>Dann</marker> gingen wir '
                              'schlafen.',
                              'Dann hatten wir Freizeit. Danach gab es Essen. <marker>Schließlich</marker> gingen '
                              'wir schlafen.')

    def is_adverb(self, atr):
        return atr.token in _ADVERBS


# --- GermanWordRepeatRule ----------------------------------------------------

_SINGLE_CHAR = jregex.compile('(?i)^[a-z]$')


def _word_repeat_anti_patterns():
    b = PatternTokenBuilder
    return [
        [cs_token('please'), cs_token('please'), cs_token('please')],
        [cs_token('Late'), cs_token('Late'), cs_token('Show')],
        [cs_token('Wenn'), cs_token('hinter'), cs_token('Robben'), cs_token('Robben'), cs_token('robben'),
         cs_token(','), cs_token('robben'), cs_token('Robben'), cs_token('Robben'), cs_token('hinterher')],
        [token_regex('tägliche(n|m|s)?'), cs_token('klein'), cs_token('klein')],
        [cs_token('Bora'), cs_token('Bora')],
        [cs_token('Tuk'), cs_token('Tuk')],
        [cs_token('Miu'), cs_token('Miu')],
        [token('Moin'), token('Moin')],
        [token('Na'), token('na')],
        [token('la'), token('la')],  # La La Land / la la la ...
        [cs_token('Fragen'), cs_token('fragen')],  # "Bei Fragen fragen"
        [token('ha'), token('ha')],
        [token('teils'), token('teils')],
        [token('Marsch'), token('Marsch')],
        [token('hip'), token('hip'), token('hurra')],
        [token('möp'), token('möp')],
        [token('gout'), token('gout')],
        [token('piep'), token('piep')],
        [token('bla'), token('bla')],
        [token('blah'), token('blah')],
        [token('oh'), token('oh')],
        [token('klopf'), token('klopf')],
        [token('ne'), token('ne')],
        [token('Fakten'), token('Fakten'), token('Fakten')],
        [token('Top'), token('Top'), token('Top')],
        [token('Toi'), token('Toi'), token('Toi')],
        [token('und'), token('und'), token('und')],
        [token('man'), token('man'), token('man')],
        [token_regex('wenn|falls'), token('das'), token('das'), token('nächste'), token('mal')],
        [token('Arbeit'), token('Arbeit'), token('Arbeit')],
        [token_regex('\\*|:|\\/'), token('in'), token('in')],  # Art Direktor*in in der ...
        [token('Üben'), token('Üben'), token('Üben')],
        [token('cha'), token('cha')],
        [token('zack'), token('zack')],
        [token('sapiens'), token('sapiens')],
        [token('peng'), token('peng')],
        [token('bye'), token('bye')],
        [token('nicht'), token('nicht'), token('kommunizieren')],  # Man kann nicht nicht kommunizieren
        [token('Dee'), token_regex('Dees?')],  # Dee Dee Ramone
        [token('Phi'), token('Phi')],  # Phi Phi Islands
        [token_regex(',|wei(ß|ss)|nicht'), token('wer'), token('wer'), token_regex('war|ist|sein')],
        # Ich weiß, wer wer ist!
        [token_regex('ist|war|wäre?|für|dass'), token('das'), token('das'), pos_regex('.*SUB:.*NEU.*')],
        # Wahrscheinlich ist das das Problem.
        [token_regex('ist|war|wäre?|für|dass'), token('das'), token('das'), pos_regex('ADJ:.*'),
         pos_regex('.*SUB:.*NEU.*')],
        [token_regex('ist|war|wäre?|für|dass'), token('das'), token('das'), pos_regex('ADJ:.*NEU.*'),
         pos_regex('UNKNOWN')],
        [token_regex('als|wenn'), pos_regex('(PRO|EIG):.*'), token('das'), token('das'), pos_regex('ADJ:.*NEU.*'),
         pos_regex('.*SUB:.*NEU.*')],  # Als wir das das erste Mal
        [token_regex('werden|würden|sollt?en|müsst?en|könnt?en'), token('sie'), token('sie'),
         pos_regex('VER:1:PLU:.*')],  # Werden sie sie töten?
        [token_regex('wenn|falls|ob'), token('das'), token('das'), pos_regex('SUB:NOM:SIN:NEU.*'),
         b().token_regex('sein|haben').match_inflected_forms().build()],  # Falls das das Problem ist, …
        [token_regex('wenn|falls|ob'), token('das'), token('das'), pos_regex('(ADJ|PA[12]).*NEU.*'),
         pos_regex('SUB:NOM:SIN:NEU.*'), b().token_regex('sein|haben').match_inflected_forms().build()],
        # Falls das das neue Problem ist, …
        [cs_token(','), b().cs_token('der').match_inflected_forms().build(),
         b().cs_token('der').match_inflected_forms().build()],
        # "wie Honda und Samsung, die die Bezahlung ihrer Firmenchefs..."
        [token_regex('alle|nur|obwohl|lediglich|für|zwar|aber'), b().cs_token('die').build(),
         b().cs_token('die').build()],  # "Alle die die"
        [pos_regex('PKT|SENT_START|KON:NEB'), token_regex('haben|hatten'), b().cs_token('die').build(),
         b().cs_token('die').build(), pos_regex('.*SUB.*PLU.*|UNKNOWN')],  # "Haben die die Elemente ..."
        [pos_regex('PKT|SENT_START|KON:NEB'), token_regex('ob|falls'), b().cs_token('die').build(),
         b().cs_token('die').build(), pos_regex('.*SUB.*PLU.*|UNKNOWN')],  # "und ob die die Währungen ..."
        [cs_token(','), pos_regex('PRP:.+'), b().cs_token('der').match_inflected_forms().build(),
         b().cs_token('der').match_inflected_forms().build()],  # "Das Haus, in das das Kind läuft."
        [cs_token('Leben'), cs_token('leben')],  # "Er will sein Leben leben"
        [cs_token('Stellen'), cs_token('stellen')],  # "Die markierten Stellen stellen die Aufnahmepunkte dar."
        [token('die'), cs_token('ferne'), cs_token('Ferne')],  # "Wir reisen in die ferne Ferne."
        [cs_token('Essen'), cs_token('essen')],  # "Er muss sein Essen essen"
        [token_regex('^[_]+$'), token_regex('^[_]+$')],
        [pos_regex('VER:.*[123]:.+|PKT|ADV:INR'), cs_token('ihr'), cs_token('ihr'), pos_regex('SUB.+')],
        # "Er gab ihr ihr Buch zurück."
    ]


_anti_patterns_lock = threading.Lock()
_anti_patterns_cache = {}


class GermanWordRepeatRule(WordRepeatRule):
    """Port of GermanWordRepeatRule: word repetitions, with German
    exceptions ("Warum fragen Sie sie nicht selbst?", "Ist das das
    Problem?" ...)."""

    rule_id = 'GERMAN_WORD_REPEAT_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.add_example_pair('In diesem Satz <marker>ist ist</marker> ein Wort doppelt.',
                              'In diesem Satz <marker>ist</marker> ein Wort doppelt.')

    def ignore(self, tokens, position):
        prev = tokens[position - 1].token
        cur = tokens[position].token
        # "Warum fragen Sie sie nicht selbst?" (operator precedence as in Java)
        if (position != 2 and prev == 'Sie' and cur == 'sie') or (prev == 'sie' and cur == 'Sie'):
            return True
        # "Ihre verbotenen Waren waren bisher nicht aufgeflogen"
        if (position != 2 and prev == 'Waren' and cur == 'waren') or (prev == 'waren' and cur == 'Waren'):
            return True
        if position > 2 and prev == 'sie' and cur == 'sie':
            if tokens[position - 2].has_pos_tag('KON:UNT'):
                # "Sie tut das, damit sie sie nicht fortschickt"
                return True
            if len(tokens) - 1 > position and \
                    ((tokens[position - 2].has_pos_tag_starting_with('VER:3:') and
                      tokens[position + 1].has_pos_tag('ZUS'))  # "Dann warfen sie sie weg."
                     or (tokens[position - 2].has_pos_tag_starting_with('VER:MOD:3') and
                         tokens[position + 1].has_pos_tag('VER:INF:NON'))):  # "Dann konnte sie sie sehen."
                return True
        if _SINGLE_CHAR.fullmatch(cur) and position > 1 and _SINGLE_CHAR.fullmatch(tokens[position - 2].token) and \
                position + 1 < len(tokens) and _SINGLE_CHAR.fullmatch(tokens[position + 1].token):
            # spelling with spaces in between: "A B B A"
            return True
        return super().ignore(tokens, position)

    def get_anti_patterns(self):
        key = self.language.code  # (Rule.cacheAntiPatterns caches per language)
        with _anti_patterns_lock:
            r = _anti_patterns_cache.get(key)
            if r is None:
                r = _anti_patterns_cache[key] = make_anti_patterns(_word_repeat_anti_patterns(), self.language)
            return r
