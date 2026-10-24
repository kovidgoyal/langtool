"""Catalan specific rules (port of org.languagetool.rules.ca):
CatalanUnpairedBracketsRule, CatalanWordRepeatRule, CatalanPhraseRepeatRule,
CatalanUnpairedQuestionMarksRule, CatalanUnpairedExclamationMarksRule,
PronomFebleDuplicateRule, CatalanWordRepeatBeginningRule, CompoundRule,
CatalanPunctuationMarkAtParagraphEnd, IgnoreProperNouns and
CatalanRepeatedWordsRule.

Locale("ca") has no special case mapping (str.lower here)."""

import threading

from ... import jregex
from ...chunking import ChunkTag
from ...patterns.pattern_token import cs_regex
from ...patterns.rules import make_anti_patterns
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractRepeatedWordsRule, PhraseRepeatRule,
                                     WordRepeatBeginningRule, java_hash_set_order, load_compound_rule_data,
                                     load_repeated_words, _rules_file)
from ...rules.base import Category, RuleMatch
from ...rules.core import (CoreRule, CoreTextLevelRule, GenericUnpairedBracketsRule,
                           PunctuationMarkAtParagraphEnd, WordRepeatRule)
from ...tools import (is_digit, is_punctuation_mark, is_punctuation_or_symbol, java_equals_ignore_case, java_trim,
                      preserve_case)
from .helpers import transform_darrere

# --- CatalanUnpairedBracketsRule -------------------------------------------

CA_START_SYMBOLS = ['[', '(', '{', '“', '«', '"', "'", '‘']
CA_END_SYMBOLS = [']', ')', '}', '”', '»', '"', "'", '’']
_VALID_BEFORE_CLOSING_PARENTHESIS = jregex.compile('\\d+|[a-zA-Z]')
_NUMBER = jregex.compile('\\d[\\d., ]+\\d|\\d{1,2}')


class CatalanUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.ca.CatalanUnpairedBracketsRule (id
    UNPAIRED_BRACKETS), with exceptions for proper nouns and the Saxon
    genitive (allow_saxon_genitive), apostrophes in nouns and adjectives,
    degrees/minutes/seconds, "»" at the sentence start and enumerations
    like "a)". The suggestions add the missing symbol next to the unpaired
    one, or remove it."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, CA_START_SYMBOLS, CA_END_SYMBOLS)

    def is_no_exception(self, token_str, tokens, i, j, prec_space, foll_space, stack):
        if i < 1:
            return True
        if tokens[i].has_pos_tag_starting_with('NP') or tokens[i].has_pos_tag_starting_with('allow_saxon_genitive'):
            return False
        if ((token_str == '’' or token_str == "'")
                and (tokens[i].has_pos_tag_starting_with('N') or tokens[i].has_pos_tag_starting_with('A'))):
            return False
        if not super().is_no_exception(token_str, tokens, i, j, prec_space, foll_space, stack):
            return False
        # degrees, minutes, seconds...
        if ((token_str == '"' or token_str == "'")
                and _NUMBER.fullmatch(tokens[i - 1].token)
                and not tokens[i].whitespace_before
                and ((i > 2 and ('º' in tokens[i - 2].token or '°' in tokens[i - 2].token))
                     or (i > 4 and ('º' in tokens[i - 4].token or '°' in tokens[i - 4].token)))):
            return False
        if i == 1 and token_str == '»':
            return False
        if i > 1 and token_str == ')':
            is_there_opening_parenthesis = False
            k = 1
            while i - k > 0:
                if tokens[i - k].token == ')':
                    break
                if tokens[i - k].token == '(':
                    is_there_opening_parenthesis = True
                    break
                k += 1
            if not is_there_opening_parenthesis:
                if _VALID_BEFORE_CLOSING_PARENTHESIS.fullmatch(tokens[i - 1].token):
                    return False
        return True

    def get_suggestions(self, full_text, start_pos, end_pos, symbol, other_symbol, symbol_type=None):
        # add the other symbol together with the original symbol, needs to be
        # moved by the user
        if symbol_type == 'Closing':
            replacements = [other_symbol + symbol]
        else:
            replacements = [symbol + other_symbol]
        # add the option to remove the original symbol
        replacements.append('')
        return replacements

    def get_message(self):
        return 'Símbol sense parella. Afegiu-lo i situeu-lo manualment en el lloc adequat, o bé esborreu-lo.'


# --- CatalanWordRepeatRule -------------------------------------------------

class CatalanWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.ca.CatalanWordRepeatRule: avoid false
    alarms in the word repetition rule (_allow_repeat, LOC_ADV and some
    proper nouns)."""

    rule_id = 'CATALAN_WORD_REPEAT_RULE'

    def ignore(self, tokens, position):
        if position > 0 and (tokens[position].has_pos_tag('_allow_repeat')
                             or tokens[position - 1].has_pos_tag('_allow_repeat')
                             or tokens[position].has_pos_tag('LOC_ADV')
                             or tokens[position].has_lemma('Joan-Lluís Lluís')
                             or tokens[position].has_lemma('Chitty Chitty Bang Bang')):
            return True
        return super().ignore(tokens, position)


# --- CatalanPhraseRepeatRule -----------------------------------------------

# from ca/resource/ca/entities.ent: <!ENTITY unitats_temps "segon|minut|..."/>
_UNITATS_TEMPS = frozenset((
    'segon', 'minut', 'hora', 'horeta', 'dia', 'jorn', 'jornada', 'setmana', 'quinzena', 'mes', 'trimestre',
    'quadrimestre', 'semestre', 'any', 'lustre', 'dècada', 'decenni', 'segle', 'mil·lenni', 'mil·lenari', 'minutet',
    'segonet', 'anyet'))
_POSTAG_EXCEPTIONS = ('_emoji_', '_PUNCT', '_PUNCT_CONT', 'allow_repetition', '_allow_repeat', 'LOC_ADJ', 'LOC_ADV',
                      'LOC_CONJ', 'LOC_PREP', 'SENT_START', 'UNKNOWN')
_CONJUNCIONS_I_O = ('i', 'o')
# fixed 2-, 3- and 4-token antipatterns from the XML rule (as literal surface sequences)
_LITERAL_ANTIPATTERNS = (
    ('casa', 'a', 'casa', 'a'),
    ('boca', 'a', 'boca', 'a'),
    ('braç', 'a', 'braç', 'a'),
    ('gen', 'a', 'gen', 'a'),
    ('de', 'tu', 'a', 'tu'),
    ('milions', 'de'),
    ('res', 'de', 'res', 'de'),
)


def _sequence_matches(tokens, start, words):
    for k, w in enumerate(words):
        if not java_equals_ignore_case(tokens[start + k].token, w):
            return False
    return True


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start <= b_end and b_start <= a_end


class CatalanPhraseRepeatRule(PhraseRepeatRule):
    """Port of org.languagetool.rules.ca.CatalanPhraseRepeatRule: avoid false
    alarms in the phrase repetition rule; it mirrors all the exceptions of
    the PHRASE_REPETITION rule in ca/grammar.xml (its antipatterns and the
    exceptions inside its pattern)."""

    rule_id = 'CATALAN_PHRASE_REPEAT_RULE'

    def ignore(self, tokens, position, phrase_length):
        if phrase_length == 2 and self._matches_antipattern(tokens, position, position + phrase_length):
            return True
        if self._violates_pattern_exceptions(tokens, position, phrase_length):
            return True
        return super().ignore(tokens, position, phrase_length)

    @staticmethod
    def _violates_pattern_exceptions(tokens, position, phrase_length):
        """The exceptions inside the rule's pattern: word1 must not be
        punctuation/"i" nor SENT_START/allow_repetition/UNKNOWN/_PUNCT/
        _PUNCT_CONT/_emoji_; word2 must additionally not be a locution;
        word3/word4 (the repeated pair) must not be a locution either."""
        for i in range(position, position + phrase_length):
            first_token = tokens[i]
            second_token = tokens[i + phrase_length]
            token_str = first_token.token.lower()
            if first_token.is_pos_tag_unknown:
                return True
            if token_str in _CONJUNCIONS_I_O or is_punctuation_or_symbol(token_str):
                return True
            for postag_exception in _POSTAG_EXCEPTIONS:
                if first_token.has_pos_tag(postag_exception) or second_token.has_pos_tag(postag_exception):
                    return True
        return False

    @staticmethod
    def _matches_antipattern(tokens, match_start, match_end):
        """The rule's antipatterns: fixed idioms ("boca a boca a", "milions
        de", ...), the "ni massa poc(s)" and "de tu a tu" contexts, the
        &unitats_temps; + "a" + repeat + "a" construction (e.g. "dia a dia
        a"), and quotation marks immediately wrapping a single token.
        Antipatterns block the rule wherever they overlap the current
        2-word-phrase match."""
        window_start = max(1, match_start - 3)
        window_end = min(len(tokens) - 1, match_end + 3)
        for antipattern in _LITERAL_ANTIPATTERNS:
            j = window_start
            while j + len(antipattern) - 1 <= window_end:
                if (_sequence_matches(tokens, j, antipattern)
                        and _overlaps(j, j + len(antipattern) - 1, match_start, match_end)):
                    return True
                j += 1
        j = window_start
        while j + 3 <= window_end:
            # <token regexp="yes">&unitats_temps;</token> <token>a</token> <match no="0"/> <token>a</token>
            if (tokens[j].token.lower() in _UNITATS_TEMPS
                    and java_equals_ignore_case('a', tokens[j + 1].token)
                    and java_equals_ignore_case(tokens[j].token, tokens[j + 2].token)
                    and java_equals_ignore_case('a', tokens[j + 3].token)
                    and _overlaps(j, j + 3, match_start, match_end)):
                return True
            j += 1
        j = window_start
        while j + 2 <= window_end:
            # <token>ni</token> <token>massa</token> <token inflected="yes">poc</token>
            if (java_equals_ignore_case('ni', tokens[j].token) and java_equals_ignore_case('massa', tokens[j + 1].token)
                    and tokens[j + 2].has_lemma('poc') and _overlaps(j, j + 2, match_start, match_end)):
                return True
            # <token postag="_QM_OPEN"/> <token spacebefore="no"/> <token postag="_QM_CLOSE" spacebefore="no"/>
            if (tokens[j].has_pos_tag('_QM_OPEN') and tokens[j + 2].has_pos_tag('_QM_CLOSE')
                    and _overlaps(j, j + 2, match_start, match_end)):
                return True
            j += 1
        return False


# --- CatalanUnpairedQuestionMarksRule / CatalanUnpairedExclamationMarksRule ---

class CatalanUnpairedQuestionMarksRule(CoreTextLevelRule):
    """Port of org.languagetool.rules.ca.CatalanUnpairedQuestionMarksRule
    (default off): requires an initial '¿' if the sentence ends with '?'."""

    rule_id = 'CA_UNPAIRED_QUESTION'
    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def get_start_symbol(self):
        return '¿'

    def get_end_symbol(self):
        return '?'

    def min_to_check_paragraph(self):
        return 1

    def get_description(self):
        return "Exigeix signe d'interrogació inicial"

    def match(self, sentences, annotated_text=None):
        matches = []
        pos = 0
        start_symbol = self.get_start_symbol()
        end_symbol = self.get_end_symbol()
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            n = len(tokens)
            needs_inv_question_mark_at = self._has_token_at_pos(end_symbol, tokens)
            if needs_inv_question_mark_at > 1:
                has_inv_question_mark = False
                first_token = None
                for i in range(n):
                    t = tokens[i]
                    if first_token is None and not t.is_sentence_start and not is_punctuation_mark(t.token):
                        first_token = t
                    if t.token == start_symbol and i < needs_inv_question_mark_at:
                        has_inv_question_mark = True
                    # possibly a sentence end
                    if not t.is_sentence_end and t.token == end_symbol and i < needs_inv_question_mark_at:
                        first_token = None
                    # put the question mark in: ¿de què... ¿de quina
                    if i > 2 and i + 2 < n:
                        prev_comma = tokens[i - 1].token == ','
                        if (prev_comma and t.has_pos_tag('CC') and tokens[i + 1].has_pos_tag('SPS00')
                                and (tokens[i + 2].has_pos_tag_starting_with('PT')
                                     or tokens[i + 2].has_pos_tag_starting_with('DT'))):
                            first_token = t
                        if (prev_comma and t.has_pos_tag('SPS00')
                                and (tokens[i + 1].has_pos_tag_starting_with('PT')
                                     or tokens[i + 1].has_pos_tag_starting_with('DT'))):
                            first_token = t
                        if (prev_comma and t.has_pos_tag('CC')
                                and (tokens[i + 1].has_pos_tag_starting_with('PT')
                                     or tokens[i + 1].has_pos_tag_starting_with('DT'))):
                            first_token = t
                        if prev_comma and (t.has_pos_tag_starting_with('PT') or t.has_pos_tag_starting_with('DT')):
                            first_token = t
                        if (prev_comma and t.has_pos_tag('CC')
                                and (tokens[i + 1].token == 'no' or tokens[i + 1].token == 'sí')):
                            first_token = t
                    if i > 2:
                        if tokens[i - 1].token == ',' and t.token in ('no', 'sí', 'oi', 'eh'):
                            first_token = t
                if first_token is not None:
                    s = None
                    if needs_inv_question_mark_at > 1 and not has_inv_question_mark:
                        s = start_symbol
                    if s is not None:
                        message = "Símbol sense parella: Sembla que falta un '" + s + "'"
                        match = RuleMatch(self, sentence, pos + first_token.start_pos, pos + first_token.end_pos,
                                          message)
                        match.set_suggested_replacement(s + first_token.token)
                        matches.append(match)
            pos += sentence.get_corrected_text_length()
        return matches

    @staticmethod
    def _has_token_at_pos(ch, tokens):
        i = len(tokens) - 1
        while i > 0:
            if tokens[i].token == ch:
                if (i < len(tokens) - 1 and not tokens[i + 1].whitespace_before
                        and not is_punctuation_mark(tokens[i + 1].token)
                        and not tokens[i + 1].is_whitespace):
                    # ignore question marks joined to the next word, as in URLs
                    pass
                else:
                    return i
            i -= 1
        return -1


class CatalanUnpairedExclamationMarksRule(CatalanUnpairedQuestionMarksRule):
    """Port of org.languagetool.rules.ca.CatalanUnpairedExclamationMarksRule
    (default off): requires an initial '¡' if the sentence ends with '!'."""

    rule_id = 'CA_UNPAIRED_EXCLAMATION'

    def get_description(self):
        return "Exigeix signe d'exclamació inicial"

    def get_start_symbol(self):
        return '¡'

    def get_end_symbol(self):
        return '!'


# --- PronomFebleDuplicateRule ----------------------------------------------

# tots els pronoms febles
_PRONOM_FEBLE = jregex.compile('P0.{6}|PP3CN000|PP3NN000|PP3..A00|PP[123]CP000|PP3CSD00')
_VERB_CONJUGAT = jregex.compile('V.[SI].*')
_SPS00 = jregex.compile('SPS00')
_PRONOMS_EN_HI = ('en', 'hi')
_GV = ChunkTag('GV')


def _get_suggestion_from_to(tokens, from_, to):
    sugg = []
    for j in range(from_, to):
        if tokens[j].whitespace_before and sugg:
            sugg.append(' ')
        sugg.append(tokens[j].token)
    return ''.join(sugg)


def _get_lemma_of_pronom_feble(atr):
    for reading in atr:
        pos_tag = reading.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if _PRONOM_FEBLE.fullmatch(pos_tag):
            return reading.lemma
    return ''


class PronomFebleDuplicateRule(CoreRule):
    """Port of org.languagetool.rules.ca.PronomFebleDuplicateRule: weak
    pronouns duplicated before and after the verb (S'ha de fer-se). The
    suggestions keep the pronouns after or before the verb."""

    rule_id = 'PRONOMS_FEBLES_DUPLICATS'
    issue_type = 'Grammar'
    _RULE_MESSAGE = 'Combinació incorrecta de pronoms febles. Deixeu els de davant o els de darrere del verb.'
    _SHORT_MESSAGE = 'Combinació incorrecta de pronoms febles.'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.category = Category('PRONOMS_FEBLES', 'Pronoms febles')
        self.add_example_pair("<marker>S'ha de fer-se</marker>.", "<marker>S'ha de fer</marker>.")

    def get_description(self):
        return 'Pronoms febles duplicats'

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        init_pos = -1
        last_verb_pos = -1
        lemes_pronoms_abans = []
        lemes_pronoms_despres = []
        lemes_preposicions = []
        count_verb = 0
        in_verb_group = False
        i = 1
        while i < n:  # ignoring token 0, i.e., SENT_START
            pf_lemma = _get_lemma_of_pronom_feble(tokens[i])
            if pf_lemma:
                if count_verb == 0 and (lemes_pronoms_abans or tokens[i].whitespace_before
                                        or tokens[i - 1].has_pos_tag('SENT_START')):
                    lemes_pronoms_abans.append(pf_lemma)
                    if len(lemes_pronoms_abans) == 1:
                        init_pos = i
                    in_verb_group = True
                elif not tokens[i].whitespace_before:
                    lemes_pronoms_despres.append(pf_lemma)
                else:
                    count_verb = 0
                    lemes_pronoms_abans.clear()
                    lemes_pronoms_despres.clear()
                    lemes_pronoms_abans.append(pf_lemma)
                    init_pos = i
                    in_verb_group = True
            elif (_GV in tokens[i].chunk_tags and lemes_pronoms_abans and not lemes_pronoms_despres
                  and not self._is_exception(tokens, i)):
                if tokens[i].reading_with_tag_regex(_VERB_CONJUGAT) is not None and count_verb > 0:
                    in_verb_group = False
                else:
                    count_verb += 1
                    in_verb_group = True
                    last_verb_pos = i
                    prep_token = tokens[i].reading_with_tag_regex(_SPS00)
                    if prep_token is not None:
                        lemes_preposicions.append(prep_token.lemma)
            else:
                in_verb_group = False
            if not in_verb_group or i == n - 1:
                error, corrected_pronouns = self._is_there_error_in_lemmas(
                    lemes_pronoms_abans, lemes_pronoms_despres, lemes_preposicions, tokens, last_verb_pos)
                if error:
                    if in_verb_group and i == n - 1:
                        i += 1
                    rule_match = RuleMatch(self, sentence, tokens[init_pos].start_pos, tokens[i - 1].end_pos,
                                           self._RULE_MESSAGE, self._SHORT_MESSAGE)
                    model = tokens[init_pos].token
                    n_abans = len(lemes_pronoms_abans)
                    if corrected_pronouns is None:
                        replacements = [
                            preserve_case(_get_suggestion_from_to(
                                tokens, init_pos + n_abans,
                                init_pos + n_abans + count_verb + len(lemes_pronoms_despres)), model),
                            preserve_case(_get_suggestion_from_to(tokens, init_pos, init_pos + n_abans + count_verb),
                                          model)]
                    else:
                        verbs = _get_suggestion_from_to(tokens, init_pos + n_abans, init_pos + n_abans + count_verb)
                        pronoms_darrere = transform_darrere(corrected_pronouns, verbs)
                        replacements = [preserve_case(corrected_pronouns + ' ' + verbs, model),
                                        preserve_case(verbs + pronoms_darrere, model)]
                    rule_match.add_suggested_replacements(replacements)
                    rule_matches.append(rule_match)
                count_verb = 0
                lemes_pronoms_abans.clear()
                lemes_pronoms_despres.clear()
                lemes_preposicions.clear()
            i += 1
        return rule_matches

    @staticmethod
    def _is_exception(tokens, i):
        if tokens[i].has_any_partial_pos_tag('VMN0000', 'VSN0000', 'VAN0000') and tokens[i - 1].has_lemma('fer'):
            # et fan adonar-te --> rule EL_FAN_AGENOLLAR
            return True
        if tokens[i].token == 'poder' and tokens[i - 1].has_pos_tag_starting_with('V'):
            return True
        if (i > 3 and i + 3 < len(tokens)
                # l'oportunitat que hi ha de donar-los
                and (tokens[i].token == 'ha' or tokens[i].token == 'havia')
                and tokens[i - 2].token == 'que' and tokens[i - 1].token == 'hi'
                and tokens[i + 1].has_lemma('de')
                and not (tokens[i + 2].has_lemma('haver') and tokens[i + 3].has_lemma('hi'))):
            return True
        return False

    @staticmethod
    def _is_there_error_in_lemmas(abans, despres, preposicions, tokens, last_verb_pos):
        """isThereErrorInLemmas: (error, correctedPronouns)"""
        if not abans or not despres:
            return False, None
        if len(abans) == 1 and len(despres) == 1 and abans[0] == despres[0]:
            return True, None
        if len(abans) > 1 and len(despres) > 1:
            return True, None
        if ((tokens[last_verb_pos].token == 'haver' or tokens[last_verb_pos].token == 'havent')
                and despres[0] in _PRONOMS_EN_HI and abans[0] in _PRONOMS_EN_HI):
            return True, "n'hi"
        if 'en' in abans and 'en' in despres:
            return True, None
        if 'ell' in abans and 'ell' in despres:
            return True, None
        if 'ho' in abans and ('hi' in despres or 'ell' in despres or 'en' in despres):
            return True, None
        if 'hi' in abans and 'a' not in preposicions and ('ho' in despres or 'ell' in despres or 'en' in despres):
            return True, None
        return False, None


# --- CatalanWordRepeatBeginningRule ----------------------------------------

# adverbs used to add to what the previous sentence mentioned
_ADD_ADVERBS = ('Igualment', 'També', 'Addicionalment')
# adverbs used to express contrast to what the previous sentence mentioned
_CONTRAST_CONJ = ('Però', 'Emperò', 'Mes')
_CAUSE_CONJ = ('Perquè', 'Car')
# adverbs used to express emphasis to what the previous sentence mentioned
_EMPHASIS_ADVERBS = ('Òbviament', 'Clarament', 'Absolutament', 'Definitivament')
# adverbs used to explain what the previous sentence mentioned
_EXPLAIN_ADVERBS = ('Específicament', 'Concretament', 'Particularment', 'Precisament')
# personal pronouns
_PERSONAL_PRONOUNS = frozenset(('jo', 'tu', 'ell', 'ella', 'nosaltres', 'vosaltres', 'ells', 'elles', 'vostè',
                                'vostès', 'vosté', 'vostés', 'vós'))
# linking expressions that can be used instead of the ADD_ADVERBS
_ADD_EXPRESSIONS = ('Així mateix', 'A més a més')
# linking expressions that can be used instead of the CONTRAST_ADVERBS
_CONTRAST_EXPRESSIONS = ('Així i tot', "D'altra banda", 'Per altra part')
_CAUSE_EXPRESSIONS = ('Ja que', 'Per tal com', 'Pel fet que', 'Puix que')
_EXCEPCIONS_START = frozenset(("l'", 'el', 'la', 'els', 'les', 'punt', 'article', 'mòdul', 'part', 'sessió', 'unitat',
                               'tema', 'a', 'per', 'en', 'com'))
# (the iteration order of the Java HashSets)
_ADD_ADVERBS_ORDER = java_hash_set_order(_ADD_ADVERBS)
_CAUSE_CONJ_ORDER = java_hash_set_order(_CAUSE_CONJ)
_EMPHASIS_ADVERBS_ORDER = java_hash_set_order(_EMPHASIS_ADVERBS)
_EXPLAIN_ADVERBS_ORDER = java_hash_set_order(_EXPLAIN_ADVERBS)


def _different_adverbs_of_same_category(adverb, adverbs_of_category):
    return [adv for adv in adverbs_of_category if adv != adverb]


class CatalanWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.ca.CatalanWordRepeatBeginningRule:
    WordRepeatBeginningRule with Catalan adverbs, exceptions and
    suggestions (picky)."""

    rule_id = 'CATALAN_WORD_REPEAT_BEGINNING_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.tags = ['picky']
        self.add_example_pair('Però el carrer és tot modernista. <marker>Però</marker> té nom de poeta.',
                              'Però el carrer és tot modernista. Així i tot, té nom de poeta.')

    def is_exception(self, token_str):
        return (super().is_exception(token_str) or is_digit(token_str[0])
                or token_str.lower() in _EXCEPCIONS_START)

    def is_adverb(self, atr):
        if atr.has_pos_tag('RG') or atr.has_pos_tag('LOC_ADV'):
            return True
        tok = atr.token
        return (tok in _ADD_ADVERBS or tok in _CONTRAST_CONJ or tok in _EMPHASIS_ADVERBS or tok in _EXPLAIN_ADVERBS
                or tok in _CAUSE_CONJ)

    def get_suggestions(self, atr):
        tok = atr.token
        lower_tok = tok.lower()
        # the repeated word is a personal pronoun
        if lower_tok in _PERSONAL_PRONOUNS:
            return ['A més a més, ' + lower_tok, 'Igualment, ' + lower_tok, 'No sols aixó, sinó que ' + lower_tok]
        if tok in _ADD_ADVERBS:
            return _different_adverbs_of_same_category(tok, _ADD_ADVERBS_ORDER) + list(_ADD_EXPRESSIONS)
        if tok in _CONTRAST_CONJ:
            return list(_CONTRAST_EXPRESSIONS)
        if tok in _EMPHASIS_ADVERBS:
            return _different_adverbs_of_same_category(tok, _EMPHASIS_ADVERBS_ORDER)
        if tok in _EXPLAIN_ADVERBS:
            return _different_adverbs_of_same_category(tok, _EXPLAIN_ADVERBS_ORDER)
        if tok in _CAUSE_CONJ:
            return _different_adverbs_of_same_category(tok, _CAUSE_CONJ_ORDER) + list(_CAUSE_EXPRESSIONS)
        return []


# --- CompoundRule ----------------------------------------------------------

class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.ca.CompoundRule: compounds (listed in
    /ca/compounds.txt) that are not written as separate words. A word is
    misspelled if the Valencian Catalan tagger (CatalanTagger.INSTANCE_VAL)
    doesn't know it."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         "S'escriu amb un guionet.",
                         "S'escriu junt sense espai ni guionet.",
                         "S'escriu junt o amb guionet.",
                         'Error de mot compost')
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>Ryan-Air</marker>.', '<marker>Ryanair</marker>.')

    def get_id(self):
        return 'CA_COMPOUNDS'

    def get_description(self):
        return 'Paraules compostes amb guionet: $match'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/ca/compounds.txt')

    def is_misspelled(self, word):
        from . import catalan_tagger
        return not catalan_tagger(self.language, True).tag([word])[0].is_tagged()


# --- CatalanPunctuationMarkAtParagraphEnd ----------------------------------

_IGNORED_PREFIXES = jregex.compile('^(Annex|Article principal)\\s*:', jregex.IGNORECASE)


class CatalanPunctuationMarkAtParagraphEnd(PunctuationMarkAtParagraphEnd):
    """Port of org.languagetool.rules.ca.CatalanPunctuationMarkAtParagraphEnd:
    PunctuationMarkAtParagraphEnd (default on) that ignores cross-reference
    lines that do not end with a punctuation mark, e.g. "Annex: Videojocs
    cancel·lats" or "Article principal: Videojocs cancel·lats"."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, True)

    def is_ignored_paragraph(self, first_sentence):
        return _IGNORED_PREFIXES.search(java_trim(first_sentence.text)) is not None


# --- IgnoreProperNouns -----------------------------------------------------

class IgnoreProperNouns(CoreTextLevelRule):
    """Port of org.languagetool.rules.ca.IgnoreProperNouns: matches untagged
    words that already appeared as proper nouns (NP*) in the text; the
    matches are used by Catalan.filterRuleMatches to cancel the spelling
    matches at the same position (and removed)."""

    rule_id = 'IGNORE_PROPER_NOUNS'

    def get_description(self):
        return 'Ignora noms propis que hagin aparegut en altres parts del text.'

    def min_to_check_paragraph(self):
        return 0

    def match(self, sentences, annotated_text=None):
        rule_matches = []
        pos = 0
        seen_proper_nouns = []
        for sentence in sentences:
            for token in sentence.tokens:
                if token.has_pos_tag_starting_with('NP'):
                    seen_proper_nouns.append(token.token)
                if not token.is_tagged() and token.token in seen_proper_nouns:
                    rule_matches.append(RuleMatch(self, sentence, pos + token.start_pos, pos + token.end_pos,
                                                  'Aquesta paraula ja aparegut abans i es pot donar per correcta.'))
            pos += sentence.get_corrected_text_length()
        return rule_matches


# --- CatalanRepeatedWordsRule ----------------------------------------------

_ANTI_PATTERNS = (
    (cs_regex('[Tt]ema|TEMA'), cs_regex('\\d+|[IXVC]+')),
)


def _replace_once(s, search, replacement):
    """String.replaceFirst with a literal search string and replacement"""
    return s.replace(search, replacement, 1)


class CatalanRepeatedWordsRule(AbstractRepeatedWordsRule):
    """Port of org.languagetool.rules.ca.CatalanRepeatedWordsRule: words of
    /ca/synonyms.txt repeated within a short distance (picky)."""

    _anti_patterns = {}
    _lock = threading.Lock()

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.tags = ['picky']

    def get_anti_patterns(self):
        # (cacheAntiPatterns: per language)
        key = self.language.code
        aps = self._anti_patterns.get(key)
        if aps is None:
            with self._lock:
                aps = self._anti_patterns.get(key)
                if aps is None:
                    aps = self._anti_patterns[key] = make_anti_patterns(_ANTI_PATTERNS, self.language)
        return aps

    def get_words_to_check(self):
        return load_repeated_words(_rules_file(self.language, '/ca/synonyms.txt'))

    def get_message(self):
        return ('Aquesta paraula apareix en una de les frases anteriors. Podeu substituir-la per un sinònim per a '
                'fer més variat el text, llevat que la repetició sigui intencionada.')

    def get_description(self):
        return 'Sinònims per a paraules repetides.'

    def get_short_message(self):
        return 'Estil: paraula repetida'

    def get_synthesizer(self):
        return self.language.synthesizer

    def adjust_postag(self, postag):
        if 'CN' in postag:
            return _replace_once(postag, 'CN', '..')
        if 'MS' in postag:
            return _replace_once(postag, 'MS', '[MC][SN]')
        if 'FS' in postag:
            return _replace_once(postag, 'FS', '[FC][SN]')
        if 'MP' in postag:
            return _replace_once(postag, 'MP', '[MC][PN]')
        if 'FP' in postag:
            return _replace_once(postag, 'FP', '[FC][PN]')
        if 'CS' in postag:
            return _replace_once(postag, 'CS', '[MFC][SN]')  # also F ?
        if 'CP' in postag:
            return _replace_once(postag, 'CP', '[MFC][PN]')  # also F ?
        if 'MN' in postag:
            return _replace_once(postag, 'MN', '[MC][SPN]')
        if 'FN' in postag:
            return _replace_once(postag, 'FN', '[FC][SPN]')
        return postag

    def is_exception(self, tokens, i, sent_start, is_capitalized, is_all_upper):
        if is_all_upper or (is_capitalized and not sent_start):
            return True
        return tokens[i].has_pos_tag_starting_with('NP') or tokens[i].has_pos_tag('_english_ignore_')


# the filter classes of this module (registered as org.languagetool.rules.ca.<class name>)
FILTERS = ()


def _messages_language(cls):
    """factory for the rules with the Java constructor (messages, language)"""
    return lambda messages, language, user_config, _cls=cls: _cls(messages, language)


# rule factories of this module: Java class name -> factory(messages, language, user_config, **kwargs)
RULES = {
    'CatalanUnpairedBracketsRule': _messages_language(CatalanUnpairedBracketsRule),
    'CatalanWordRepeatRule': _messages_language(CatalanWordRepeatRule),
    'CatalanPhraseRepeatRule': _messages_language(CatalanPhraseRepeatRule),
    'CatalanUnpairedQuestionMarksRule': _messages_language(CatalanUnpairedQuestionMarksRule),
    'CatalanUnpairedExclamationMarksRule': _messages_language(CatalanUnpairedExclamationMarksRule),
    'CatalanWordRepeatBeginningRule': _messages_language(CatalanWordRepeatBeginningRule),
    'CatalanPunctuationMarkAtParagraphEnd': _messages_language(CatalanPunctuationMarkAtParagraphEnd),
    'CatalanRepeatedWordsRule': _messages_language(CatalanRepeatedWordsRule),
    # (Java: new CompoundRule(messages, this, userConfig))
    'CompoundRule': lambda messages, language, user_config: CompoundRule(messages, language, user_config),
    # (Java: new PronomFebleDuplicateRule(messages), new IgnoreProperNouns(messages))
    'PronomFebleDuplicateRule': lambda messages, language, user_config: PronomFebleDuplicateRule(messages, language),
    'IgnoreProperNouns': lambda messages, language, user_config: IgnoreProperNouns(messages, language),
}
