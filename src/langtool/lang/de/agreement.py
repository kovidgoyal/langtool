"""Port of org.languagetool.rules.de.AgreementRule: simple agreement checker
for German noun phrases. Checks agreement in:

- DET/PRO NOUN: e.g. "mein Auto", "der Mann", "die Frau" (correct), "die
  Haus" (incorrect)
- DET/PRO ADJ NOUN: e.g. "der riesige Tisch" (correct), "die riesigen
  Tisch" (incorrect)
- DET/PRO ADJ ADJ NOUN: e.g. "der große riesige Tisch" (correct), "die
  große riesige Tisch" (incorrect)

Note that this rule only checks agreement inside the noun phrase, not
whether e.g. the correct case is used. For example, "Es ist das Haus dem
Mann" is not detected as incorrect.
"""

import threading

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings, SENTENCE_START_TAGNAME
from ...patterns.rules import make_anti_patterns
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import is_numeric, lowercase_first_char, starts_with_uppercase
from .agreement_suggestor import AgreementSuggestor2, REPLACEMENT_INS, REPLACEMENT_ZUR
from .agreement_tools import GrammarCategory, get_agreement_categories
from .german_token import POSType

_MIT_MIR_ETC = jregex.compile('mit (mir|dir|ihm|ihr|ihnen|uns|euch)')
_OHNE_MICH_ETC = jregex.compile('ohne (mich|dich|ihn|sie|uns|euch)')
_ZUGESCHRIEBENEN_GENANNTEN = jregex.compile('zugeschriebenen?|genannten?')
_VIEL_WEIT = jregex.compile('viel|weit')
_WENIGER_EHER = jregex.compile('weniger|eher')
_HERR_FRAU = jregex.compile('Herr|Frau')


class ReplacementType:
    """AgreementRule.ReplacementType"""
    Ins = REPLACEMENT_INS
    Zur = REPLACEMENT_ZUR


_INS_REPLACEMENT = (AnalyzedToken('das', 'ART:DEF:AKK:SIN:NEU', 'das'),)
_ZUR_REPLACEMENT = (AnalyzedToken('der', 'ART:DEF:DAT:SIN:FEM', 'der'),)
_INS_ETC = frozenset(('ins', 'ans', 'aufs', 'vors', 'durchs', 'hinters', 'unters', 'übers', 'fürs', 'ums'))

MSG = 'Möglicherweise passen das Nomen und die Wörter, die das Nomen beschreiben, grammatisch nicht zusammen.'
MSG2 = 'Möglicherweise passen das Nomen und die Wörter, die das Nomen beschreiben, grammatisch nicht zusammen.'
SHORT_MSG = 'Evtl. passen Wörter grammatisch nicht zusammen.'

MODIFIERS = frozenset((
    'zu',
    'überraschend',
    'ungeahnt',
    'absolut',
    'ausgesprochen',
    'außergewöhnlich',
    'außerordentlich',
    'äußerst',
    'besonders',
    'dringend',
    'echt',
    'einigermaßen',
    'enorm',
    'extrem',
    'fast',
    'ganz',
    'entschieden',
    'geradezu',
    'zeitweise',
    'halbwegs',
    'höchst',
    'komplett',
    'laufend',
    'recht',
    'relativ',
    'sehr',
    'total',
    'überaus',
    'ungewöhnlich',
    'unglaublich',
    # 'viel',    # "xxx, die viel Platz..."
    'völlig',
    'weit',
    'wirklich',
    'gerade',
    'vereint',
    'überwiegend',
    'gewollt',
    'angestrengt',
    'ziemlich',
))

VIELE_WENIGE_LOWERCASE = frozenset((
    'manche',
    'jegliche',
    'jeglicher',
    'andere',
    'anderer',
    'anderen',
    'sämtliche',
    'sämtlicher',
    'etliche',
    'etlicher',
    'viele',
    'vieler',
    'wenige',
    'weniger',
    'einige',
    'einiger',
    'mehrerer',
    'mehrere',
))

REL_PRONOUN_LEMMAS = ('der', 'welch')

PRONOUNS_TO_BE_IGNORED = frozenset((
    'nichts',
    'alles',   # "Ruhe vor dem alles verheerenden Sturm", "Alles Große und Edle ist einfacher Art."
    'dies',
    'ebendies',
    'ich',
    'dir',
    'dich',
    'du',
    'd',
    'er', 'sie', 'es',
    'wir',
    'mich',
    'mir',
    'uns',
    'ihnen',
    'euch',
    'ihm',
    'ihr',
    'ihn',
    'dessen',
    'deren',
    'denen',
    'sich',
    'aller',
    'allen',  # "das allen bekannte Wollnashorn"
    'man',
    'beide',
    'beiden',
    'beider',
    'wessen',
    'a',
    'alle',
    'etwas',
    'irgendetwas',
    'irgendwas',
    'irgendwer',
    'was',
    'wer',
    'wem',
    'jenen',      # "...und mit jenen anderer Arbeitsgruppen verwoben"
    'diejenigen',
    'irgendjemand', 'irgendjemandes',
    'jemand', 'jemandes',
    'niemand', 'niemandes',
))

NOUNS_TO_BE_IGNORED = frozenset((
    'A',
    'Prozent',   # Plural "Prozente", trotzdem ist "mehrere Prozent" korrekt
    'Wollen',  # das Wollen
    'Gramm',
    'Kilogramm',
    'Flippers',  # Band, die Flippers
    'Standart',  # Caught by speller
    'Stellungsname',  # Caught by speller
    'Kündigungsscheiben',  # Caught by speller
    'Piepen',  # Die Piepen
    'Badlands',
    'Visual',  # englisch
    'Special',  # englisch
    'Multiple',  # englisch
    'Chief',  # Chief Executive Officer
    'Carina',  # Name
    'Wüstenrot',  # Name
    'Rückgrad',  # found by speller
    'Rückgrads',  # found by speller
    'Anteilname',  # found by speller
    'Aalen',  # Plural form of "Aal" but also large city in Germany
    'Meter',  # Das Meter (Objekt zum Messen)
    'Boots',  # "Die neuen Boots" (englisch Stiefel)
    'Taxameter',  # Beides erlaubt "Das" und "Die"
    'Bild',  # die Bild (Zeitung)
    'Emirates',  # "Mit einem Flug der Emirates" (Fluggesellschaft)
    'Uhr',   # "um ein Uhr"
    'cm',  # "Die letzten cm" können
    'km',
    'Nr',
    'KSC',  # Abk
    'ANC',  # Abk
    'DJK',  # Der DJK Schweinfurt
    'RP',  # "Die RP (Rheinische Post)"
))

_all_anti_patterns = None
_all_anti_patterns_lock = threading.Lock()


def all_anti_patterns():
    """AgreementRule.allAntiPatterns: the pattern token lists of
    AgreementRuleAntiPatterns1-3 (built once)"""
    global _all_anti_patterns
    if _all_anti_patterns is None:
        with _all_anti_patterns_lock:
            if _all_anti_patterns is None:
                from . import agreement_antipatterns as ap
                _all_anti_patterns = ap.anti_patterns_1() + ap.anti_patterns_2() + ap.anti_patterns_3()
    return _all_anti_patterns


def _has_reading_of_type(token_readings, pos_type):
    # GermanHelper.hasReadingOfType (imported lazily: lang/de/german_helper.py)
    from .german_helper import has_reading_of_type
    return has_reading_of_type(token_readings, pos_type)


class AgreementRule(Rule):
    """Simple agreement checker for German noun phrases (see the module
    docstring)."""

    # Rule.cacheAntiPatterns: per language
    _anti_patterns = {}
    _lock = threading.Lock()

    def __init__(self, messages, language):
        super().__init__()
        self.language = language
        self.category = Categories.get('GRAMMAR', messages)
        self.url = 'https://languagetool.org/insights/de/beitrag/deklination/'
        self.add_example_pair('<marker>Der Haus</marker> wurde letztes Jahr gebaut.',
                              '<marker>Das Haus</marker> wurde letztes Jahr gebaut.')
        self._lt = None
        self._lt_lock = threading.Lock()

    def get_id(self):
        return 'DE_AGREEMENT'

    def estimate_context_for_sure_match(self):
        return max((len(p) for p in all_anti_patterns()), default=0)

    def get_description(self):
        return "Kongruenz von Nominalphrasen (unvollständig!), z.B. 'mein kleiner (kleines) Haus'"

    def get_anti_patterns(self):
        cache = AgreementRule._anti_patterns
        key = self.language.code
        r = cache.get(key)
        if r is None:
            with AgreementRule._lock:
                r = cache.get(key)
                if r is None:
                    r = cache[key] = make_anti_patterns(all_anti_patterns(), self.language)
        return r

    @staticmethod
    def _replace_prepositions_by_article(tokens):
        repl_map = {}
        for i, t in enumerate(tokens):
            if t.token in _INS_ETC:
                tokens[i] = AnalyzedTokenReadings(_INS_REPLACEMENT, t.start_pos)
                repl_map[i] = REPLACEMENT_INS
            elif t.token == 'zur':
                tokens[i] = AnalyzedTokenReadings(_ZUR_REPLACEMENT, t.start_pos)
                repl_map[i] = REPLACEMENT_ZUR
        return repl_map

    def match(self, sentence):
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).get_tokens_without_whitespace()
        orig_tokens = list(tokens)
        repl_map = self._replace_prepositions_by_article(tokens)
        n = len(tokens)
        for i in range(n):
            pos_token = tokens[i].readings[0].pos_tag  # TODO: check for all readings?
            if pos_token == SENTENCE_START_TAGNAME or tokens[i].immunized or orig_tokens[i].immunized:
                continue
            if self._could_be_relative_or_dependent_clause(tokens, i):
                continue
            if i > 0:
                prev_token = tokens[i - 1].token.lower()
                if prev_token in ('der', 'die', 'das', 'des', 'dieses') and tokens[i].token in ('eine', 'einen'):
                    # z.B. "Auf der einen Seite endlose Dünen"
                    # TODO: "der eine Polizist" -> nicht ignorieren, sondern "der polizist" checken;
                    #  "auf der einen Seite"
                    # TODO: "Leute, die eine gewissen Sicherheit brauchen." -> nicht ignorieren
                    continue
            # avoid false alarm on "nichts Gutes" and "alles Gute"
            token_readings = tokens[i]
            # avoid false alarm on "Art. 1" and "bisherigen Art. 1" (Art. = Artikel):
            det_abbrev = i < n - 2 and tokens[i + 1].token == 'Art' and tokens[i + 2].token == '.'
            det_adj_abbrev = i < n - 3 and tokens[i + 2].token == 'Art' and tokens[i + 3].token == '.'
            # "einen Hochwasser führenden Fluss", "die Gott zugeschriebenen Eigenschaften":
            following_participle = i < n - 3 and (tokens[i + 2].has_partial_pos_tag('PA1') or
                                                  _ZUGESCHRIEBENEN_GENANNTEN.fullmatch(tokens[i + 2].token))
            if det_abbrev or det_adj_abbrev or following_participle:
                continue
            if _has_reading_of_type(token_readings, POSType.DETERMINER) or self._is_relevant_pronoun(tokens, i):
                token_pos_after_modifier = self._get_pos_after_modifier(i + 1, tokens)
                skipped_str = None
                if token_pos_after_modifier > i + 1:
                    skipped_str = sentence.text[tokens[i + 1].start_pos:tokens[token_pos_after_modifier - 1].end_pos]
                token_pos = token_pos_after_modifier
                if token_pos >= n:
                    break
                next_token = tokens[token_pos]
                maybe_preposition = tokens[i - 1] if i - 1 >= 0 else None
                if i - 2 >= 0 and tokens[i - 2].token.lower() == 'was':
                    maybe_preposition = None  # avoid preposition filtering on "Was für eine schöner Sonnenuntergang!"
                if self._is_non_predicative_adjective(next_token) or self._is_participle(next_token):
                    token_pos = token_pos_after_modifier + 1
                    if token_pos >= n:
                        break
                    if _has_reading_of_type(tokens[token_pos], POSType.NOMEN):
                        # TODO: add a case (checkAdjNounAgreement) for special cases like "deren",
                        # e.g. "deren komisches Geschenke" isn't yet detected as incorrect
                        if i >= 2 and _has_reading_of_type(tokens[i - 2], POSType.ADJEKTIV) \
                                and tokens[i - 1].token == 'als' and tokens[i].token == 'das':
                            # avoid false alarm for e.g. "weniger farbenprächtig als das anderer Papageien"
                            continue
                        # prevent incomplete suggestion for e.g. "einen 142 Meter hoher Obelisken" (-> "einen hohen
                        # Obelisken")
                        allow_suggestion = token_pos == i + 2
                        rule_match = self._check_det_adj_noun_agreement(
                            maybe_preposition, tokens[i], next_token, tokens[token_pos], sentence, i,
                            repl_map if allow_suggestion else None, skipped_str)
                        if rule_match is not None:
                            rule_matches.append(rule_match)
                    elif token_pos + 1 < n and _has_reading_of_type(tokens[token_pos + 1], POSType.NOMEN) and \
                            _has_reading_of_type(tokens[token_pos], POSType.ADJEKTIV):
                        rule_match = self._check_det_adj_adj_noun_agreement(
                            maybe_preposition, tokens[i], next_token, tokens[token_pos], tokens[token_pos + 1],
                            sentence, i, repl_map, skipped_str)
                        if rule_match is not None:
                            rule_matches.append(rule_match)
                elif _has_reading_of_type(next_token, POSType.NOMEN) and next_token.token != 'Herr':
                    rule_match = self._check_det_noun_agreement(maybe_preposition, tokens[i], next_token, sentence, i,
                                                                repl_map, skipped_str)
                    if rule_match is not None:
                        rule_matches.append(rule_match)
        return self.to_rule_match_array(rule_matches)

    @staticmethod
    def _get_pos_after_modifier(start_at, tokens):
        """Search for modifiers (such as "sehr", "1,4 Meter") which can
        expand a determiner - adjective - noun group ("ein hohes Haus" ->
        "ein sehr hohes Haus", "ein 500 Meter hohes Haus") and return the
        index of the first non-modifier token ("Haus")"""
        n = len(tokens)
        if start_at < n and tokens[start_at].token == 'relativ' and start_at + 1 < n and \
                tokens[start_at + 1].token == 'gesehen':
            start_at += 2
        if start_at < n and _VIEL_WEIT.fullmatch(tokens[start_at].token) and start_at + 1 < n and \
                _WENIGER_EHER.fullmatch(tokens[start_at + 1].token):
            start_at += 2
        elif start_at + 1 < n and tokens[start_at].token in MODIFIERS:
            start_at += 1
        if start_at + 1 < n:
            phrase = (tokens[start_at].token + ' ' + tokens[start_at + 1].token).lower()
            if _MIT_MIR_ETC.fullmatch(phrase):
                start_at += 2
            elif _OHNE_MICH_ETC.fullmatch(phrase):
                start_at += 2
        if start_at + 1 < n and (is_numeric(tokens[start_at].token) or tokens[start_at].has_pos_tag('ZAL')):
            pos_after_modifier = start_at + 1
            if start_at + 3 < n and tokens[start_at + 1].token == ',' and is_numeric(tokens[start_at + 2].token):
                pos_after_modifier = start_at + 3
            if tokens[pos_after_modifier].token.endswith(('gramm', 'Gramm', 'Meter', 'meter')):
                return pos_after_modifier + 1
        return start_at

    @staticmethod
    def _is_non_predicative_adjective(token_readings):
        for reading in token_readings.readings:
            pos_tag = reading.pos_tag
            if pos_tag is not None and pos_tag.startswith('ADJ') and 'PRD' not in pos_tag:
                return True
        return False

    @staticmethod
    def _is_participle(token_readings):
        return token_readings.has_partial_pos_tag('PA1') or token_readings.has_partial_pos_tag('PA2')

    @staticmethod
    def _is_relevant_pronoun(tokens, pos):
        analyzed_token = tokens[pos]
        relevant_pronoun = _has_reading_of_type(analyzed_token, POSType.PRONOMEN)
        # avoid false alarms:
        token = tokens[pos].token
        if token.lower() in PRONOUNS_TO_BE_IGNORED or \
                (pos > 0 and tokens[pos - 1].token.lower() == 'vor' and token.lower() == 'allem'):
            relevant_pronoun = False
        return relevant_pronoun

    @staticmethod
    def _could_be_relative_or_dependent_clause(tokens, pos):
        # TODO: improve this so it only returns true for real relative clauses
        if pos >= 1:
            # avoid false alarm: "Das Wahlrecht, das Frauen zugesprochen bekamen." etc:
            comma = tokens[pos - 1].token == ','
            rel_pronoun = comma and tokens[pos].has_any_lemma(*REL_PRONOUN_LEMMAS)
            if rel_pronoun and pos + 3 < len(tokens):
                return True
        if pos >= 2:
            # avoid false alarm: "Der Mann, in dem quadratische Fische schwammen."
            # or: "Die Polizei erwischte die Diebin, weil diese Ausweis und Visitenkarte hinterließ."
            comma = tokens[pos - 2].token == ','
            if comma:
                prep = tokens[pos - 1].has_pos_tag_starting_with('PRP:')
                rel_pronoun = tokens[pos].has_any_lemma(*REL_PRONOUN_LEMMAS)
                return (prep and rel_pronoun) or (tokens[pos - 1].has_pos_tag('KON:UNT') and (
                    tokens[pos].has_lemma('jen') or tokens[pos].has_lemma('dies') or
                    tokens[pos].has_lemma('ebendies')))
        return False

    def _check_det_noun_agreement(self, maybe_preposition, token1, token2, sentence, token_pos, repl_map,
                                  skipped_str):
        # TODO: remove "-".equals(token2.getToken()) after the bug fix
        # see Daniel's comment from 20.12.2016 at https://github.com/languagetool-org/languagetool/issues/635
        if token2.immunized or token2.token in NOUNS_TO_BE_IGNORED or token2.token == '-':
            return None
        if len(token1.readings) == 1 and token1.readings[0].pos_tag is not None and \
                token1.readings[0].pos_tag.endswith(':STV'):
            # catch the error in "Meiner Chef raucht."
            set1 = set()
        else:
            set1 = self._get_agreement_categories(token1)
        set2 = self._get_agreement_categories(token2)
        set1 &= set2
        rule_match = None
        if not set1 and not self._is_exception(token1, token2):
            compound_match = self._get_compound_error2(token1, token2, token_pos, sentence)
            if compound_match is not None:
                return compound_match
            rule_match = RuleMatch(self, sentence, token1.start_pos, token2.end_pos, MSG, SHORT_MSG)
            # this will not give a match for compounds that are not in the dictionary...
            suggestor = AgreementSuggestor2(self.language.synthesizer, token1, token2, repl_map.get(token_pos))
            suggestor.set_preposition(maybe_preposition)
            suggestor.set_skipped(skipped_str)
            rule_match.set_suggested_replacements(suggestor.get_suggestions(True))
        return rule_match

    def _get_compound_error2(self, token1, token2, token_pos, sentence):
        # z.B. "die Original Mail" -> "die Originalmail"
        tokens = sentence.get_tokens_without_whitespace()
        if token_pos != -1 and token_pos + 2 < len(tokens):
            next_token = tokens[token_pos + 2]
            if starts_with_uppercase(next_token.token):
                if token2.start_pos == next_token.start_pos:
                    # avoids a strange bug that suggests e.g. "Pflegende-Pflegende" in sentence like this:
                    # "Das passiert nur, wenn der zu Pflegende bereit ist."
                    return None
                potential_compound = token2.token + lowercase_first_char(next_token.token)
                orig_token1 = tokens[token_pos].token  # before 'ins' etc. replacement
                test_phrase = orig_token1 + ' ' + potential_compound
                hyphen_potential_compound = token2.token + '-' + next_token.token
                hyphen_test_phrase = orig_token1 + ' ' + hyphen_potential_compound
                return self._get_rule_match(token1, next_token, sentence, test_phrase, hyphen_test_phrase)
        return None

    def _get_compound_error3(self, token1, token2, token3, token_pos, sentence):
        # z.B. "die neue Original Mail" -> "die neue Originalmail"
        tokens = sentence.get_tokens_without_whitespace()
        if token_pos != -1 and token_pos + 3 < len(tokens):
            next_token = tokens[token_pos + 3]
            if starts_with_uppercase(next_token.token):
                if token3.start_pos == next_token.start_pos:
                    # avoids a strange bug, see above
                    return None
                potential_compound = token3.token + lowercase_first_char(next_token.token)
                orig_token1 = tokens[token_pos].token  # before 'ins' etc. replacement
                test_phrase = orig_token1 + ' ' + token2.token + ' ' + potential_compound
                hyphen_potential_compound = token3.token + '-' + next_token.token
                hyphen_test_phrase = orig_token1 + ' ' + token2.token + ' ' + hyphen_potential_compound
                return self._get_rule_match(token1, next_token, sentence, test_phrase, hyphen_test_phrase)
        return None

    def _get_compound_error4(self, token1, token2, token3, token4, token_pos, sentence, skipped_str):
        # z.B. "die ganz neue Original Mail" -> "die ganz neue Originalmail",
        # "Es ist ein sehr interessantes kostenloses Slot Spiel" -> "ein sehr interessantes kostenloses Slot-Spiel"
        tokens = sentence.get_tokens_without_whitespace()
        idx = token_pos + 4 + (1 if skipped_str is not None else 0)
        if token_pos != -1 and idx < len(tokens):
            next_token = tokens[idx]
            potential_compound = token4.token + lowercase_first_char(next_token.token)
            if starts_with_uppercase(token4.token) and starts_with_uppercase(next_token.token):
                if token4.start_pos == next_token.start_pos:
                    # avoids a strange bug that suggests e.g. "Machtmach" in sentences like this:
                    # "Denn die einzelnen sehen sich einer sehr verschieden starken Macht des..."
                    return None
                orig_token1 = tokens[token_pos].token  # before 'ins' etc. replacement
                skipped = ' ' + skipped_str + ' ' if skipped_str is not None else ' '
                test_phrase = orig_token1 + skipped + token2.token + ' ' + token3.token + ' ' + potential_compound
                hyphen_potential_compound = token4.token + '-' + next_token.token
                hyphen_test_phrase = orig_token1 + skipped + token2.token + ' ' + token3.token + ' ' + \
                    hyphen_potential_compound
                return self._get_rule_match(token1, next_token, sentence, test_phrase, hyphen_test_phrase)
        return None

    def _get_rule_match(self, token, token2, sentence, test_phrase, hyphen_test_phrase):
        lt = self._init_lt()
        if all(k.pos_tag is not None and not k.pos_tag.startswith('SUB') for k in token2.readings):
            return None
        replacements = []
        if self._check_is_empty(lt, test_phrase) and token2.is_tagged():
            replacements.append(test_phrase)
        if self._check_is_empty(lt, hyphen_test_phrase) and token2.is_tagged():
            replacements.append(hyphen_test_phrase)
        if replacements:
            message = 'Wenn es sich um ein zusammengesetztes Nomen handelt, wird es zusammengeschrieben.'
            rule_match = RuleMatch(self, sentence, token.start_pos, token2.end_pos, message)
            rule_match.add_suggested_replacements(replacements)
            rule_match.url = ('https://dict.leo.org/grammatik/deutsch/Rechtschreibung/Regeln/Getrennt-zusammen/'
                              'Nomen.html#grammarAnchor-Nomen-49575')
            return rule_match
        return None

    def _check_is_empty(self, lt, phrase):
        """lt.check(phrase).isEmpty() of Java's JLanguageTool with only
        DE_AGREEMENT and GERMAN_SPELLER_RULE active: the spelling rules are
        not among the rules of the port's languages, so the
        GermanSpellerRule (the language's default spelling rule) is run on
        the analyzed sentences separately (without computing suggestions)."""
        if lt.check(phrase):
            return False
        speller = self.language.get_default_spelling_rule()
        if speller is not None:
            for analyzed in lt.analyze_text(phrase):
                if speller.match(analyzed, with_suggestions=False):
                    return False
        return True

    def _init_lt(self):
        if self._lt is None:
            with self._lt_lock:
                if self._lt is None:
                    from ...tool import JLanguageTool
                    lt = JLanguageTool(self.language)
                    for rule_id in lt.get_all_active_rule_ids():
                        if rule_id != 'DE_AGREEMENT' and rule_id != 'GERMAN_SPELLER_RULE':
                            lt.disable_rule(rule_id)
                    self._lt = lt
        return self._lt

    @staticmethod
    def _is_exception(token1, token2):
        return token1.token == 'allen' and token2.token == 'Grund'

    def get_categories_causing_error(self, token1, token2):
        categories = []
        for category in (GrammarCategory.KASUS, GrammarCategory.GENUS, GrammarCategory.NUMERUS):
            if self._agreement_with_category_relaxation(token1, token2, category):
                categories.append(category.display_name)
        return categories

    def _check_det_adj_noun_agreement(self, maybe_preposition, token1, token2, token3, sentence, token_pos, repl_map,
                                      skipped_str):
        # TODO: remove (token3 == null || token3.getToken().length() < 2)
        # see Daniel's comment from 20.12.2016 at https://github.com/languagetool-org/languagetool/issues/635
        if token3 is None or len(token3.token) < 2:
            return None
        common = self._retain_common_categories3(token1, token2, token3)
        rule_match = None
        if not common:
            tokens = sentence.get_tokens_without_whitespace()
            if _HERR_FRAU.fullmatch(token3.token) and token_pos + 3 < len(tokens):
                token4 = tokens[token_pos + 3]
                if not token4.is_tagged() or token4.has_pos_tag_starting_with('EIG:'):
                    # 'Aber das ignorierte Herr Grey bewusst.'
                    return None
            if token_pos + 4 < len(tokens):
                compound_match = self._get_compound_error4(tokens[token_pos], tokens[token_pos + 1],
                                                           tokens[token_pos + 2], tokens[token_pos + 3], token_pos,
                                                           sentence, None)
                if compound_match is not None:
                    return compound_match
            compound_match = self._get_compound_error3(token1, token2, token3, token_pos, sentence)
            if compound_match is not None:
                return compound_match
            if token3.has_pos_tag_starting_with('ABK'):
                return None
            rule_match = RuleMatch(self, sentence, token1.start_pos, token3.end_pos, MSG, SHORT_MSG)
            suggestor = AgreementSuggestor2(self.language.synthesizer, token1, token2, token3,
                                            repl_map.get(token_pos) if repl_map is not None else None)
            suggestor.set_preposition(maybe_preposition)
            suggestor.set_skipped(skipped_str)
            rule_match.set_suggested_replacements(suggestor.get_suggestions(True))
        return rule_match

    def _check_det_adj_adj_noun_agreement(self, maybe_preposition, token1, token2, token3, token4, sentence,
                                          token_pos, repl_map, skipped_str):
        common = self._retain_common_categories4(token1, token2, token3, token4)
        rule_match = None
        if not common:
            compound_match = self._get_compound_error4(token1, token2, token3, token4, token_pos, sentence,
                                                       skipped_str)
            if compound_match is not None:
                return compound_match
            if token4.has_pos_tag_starting_with('ABK'):
                return None
            rule_match = RuleMatch(self, sentence, token1.start_pos, token4.end_pos, MSG2, SHORT_MSG)
            if repl_map is not None:
                suggestor = AgreementSuggestor2(self.language.synthesizer, token1, token2, token3, token4,
                                                repl_map.get(token_pos))
                suggestor.set_preposition(maybe_preposition)
                suggestor.set_skipped(skipped_str)
                rule_match.set_suggested_replacements(suggestor.get_suggestions(True))
        return rule_match

    @staticmethod
    def _agreement_with_category_relaxation(token1, token2, category_to_relax):
        category_to_relax_set = {category_to_relax} if category_to_relax is not None else frozenset()
        set1 = get_agreement_categories(token1, category_to_relax_set, True)
        set2 = get_agreement_categories(token2, category_to_relax_set, True)
        return bool(set1 & set2)

    @staticmethod
    def _retain_common_categories3(token1, token2, token3):
        skip_sol = token1.token.lower() not in VIELE_WENIGE_LOWERCASE
        set1 = get_agreement_categories(token1, frozenset(), skip_sol)
        set2 = get_agreement_categories(token2, frozenset(), skip_sol)
        set3 = get_agreement_categories(token3, frozenset(), True)
        return set1 & set2 & set3

    @staticmethod
    def _retain_common_categories4(token1, token2, token3, token4):
        skip_sol = token1.token.lower() not in VIELE_WENIGE_LOWERCASE
        set1 = get_agreement_categories(token1, frozenset(), skip_sol)
        set2 = get_agreement_categories(token2, frozenset(), skip_sol)
        set3 = get_agreement_categories(token3, frozenset(), skip_sol)
        set4 = get_agreement_categories(token4, frozenset(), True)
        return set1 & set2 & set3 & set4

    @staticmethod
    def _get_agreement_categories(a_token):
        return get_agreement_categories(a_token, frozenset(), False)
