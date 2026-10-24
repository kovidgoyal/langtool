"""Catalan rule filters (port of the filters of org.languagetool.rules.ca:
AdvancedSynthesizerFilter, CatalanNumberSpellerFilter, DateCheckFilter,
NewYearDateFilter and DateFilterHelper, CatalanNumberInWordFilter,
RemoveSuggestionsFilter, CatalanSuppressMisspelledSuggestionsFilter,
FindSuggestionsFilter, FindSuggestionsEsFilter, TextToNumberFilter and
DiacriticsCheckFilter with ConfusionPairsDataLoader). The other filters
are in langtool.lang.ca.verb_filters, phrase_filters, que_inici, agreement
and remote."""

import threading

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...chunking import ChunkTag
from ...rules.abstract_rules import _rules_file
from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckWithSuggestionsFilter,
                                   AbstractFindSuggestionsFilter, AbstractNewYearDateFilter,
                                   AbstractNumberInWordFilter, AbstractSuppressMisspelledSuggestionsFilter,
                                   AbstractTextToNumberFilter, java_float, _default_tool,
                                   SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RuleFilter
from ...tools import (has_diacritics, is_all_uppercase, is_capitalized_word, java_equals_ignore_case, java_split,
                      java_trim, uppercase_first_char)
from .helpers import get_verb_from_noun, needs_apostrophation_ms


def _catalan():
    """Catalan.getInstance()"""
    from ...api import get_language
    return get_language('ca-ES')


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.ca.AdvancedSynthesizerFilter:
    synthesize suggestions using the lemma from one token (lemma_from) and
    the POS tag from another one (postag_from); a new lemma starting with
    "_" is the verb of the noun of the lemma (NounToVerbHelper)."""

    def get_new_lemma(self, word, new_lemma):
        return get_verb_from_noun(word)


class CatalanNumberSpellerFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.CatalanNumberSpellerFilter: the
    suggestion is the number (argument number_to_spell, without dots)
    spelled with the number speller of the Catalan synthesizer (feminine
    with gender:feminine), uppercase at the sentence start; numbers that
    need four words or more are not suggested (the match is discarded)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        str_to_spell = self.get_required('number_to_spell', arguments).replace('.', '')
        if self.get_required('gender', arguments) == 'feminine':
            str_to_spell = 'feminine ' + str_to_spell
        spelled_number = _catalan().synthesizer.get_spelled_number(str_to_spell)
        tokens = match.sentence.get_tokens_without_whitespace()
        if pattern_token_pos <= 1 or tokens[pattern_token_pos - 1].has_partial_pos_tag('SENT_START'):
            spelled_number = uppercase_first_char(spelled_number)
        if spelled_number and len(java_split(spelled_number.replace('-i-', ' ').replace('-', ' '), ' ')) < 4:
            rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                                   match.short_message)
            rule_match.type = match.type
            rule_match.set_suggested_replacement(spelled_number)
            return rule_match
        return None


# --- DateFilterHelper ---

# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.UK) mapped to Catalan
_DAY_NAMES = {SUNDAY: 'diumenge', MONDAY: 'dilluns', TUESDAY: 'dimarts', WEDNESDAY: 'dimecres', THURSDAY: 'dijous',
              FRIDAY: 'divendres', SATURDAY: 'dissabte'}
_DAYS = {'dg': SUNDAY, 'diumenge': SUNDAY, 'dl': MONDAY, 'dilluns': MONDAY, 'dt': TUESDAY, 'dimarts': TUESDAY,
         'dc': WEDNESDAY, 'dimecres': WEDNESDAY, 'dj': THURSDAY, 'dijous': THURSDAY, 'dv': FRIDAY,
         'divendres': FRIDAY, 'ds': SATURDAY, 'dissabte': SATURDAY}
_MONTH_PREFIXES = (('gen', 1), ('febr', 2), ('març', 3), ('abr', 4), ('maig', 5), ('juny', 6), ('jul', 7), ('ag', 8),
                   ('set', 9), ('oct', 10), ('nov', 11), ('des', 12))


def _get_day_of_week(day_str):
    """DateFilterHelper.getDayOfWeek(String)"""
    d = _DAYS.get(day_str.lower())
    if d is None:
        raise RuntimeError("Could not find day of week for '" + day_str + "'")
    return d


def _get_day_of_week_name(date):
    """DateFilterHelper.getDayOfWeek(Calendar)"""
    return _DAY_NAMES.get(date.day_of_week, '')


def _get_month(month_str):
    """DateFilterHelper.getMonth"""
    mon = month_str.lower()
    for prefix, month in _MONTH_PREFIXES:
        if mon.startswith(prefix):
            return month
    raise RuntimeError("Could not find month '" + month_str + "'")


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.ca.DateCheckFilter, the Catalan
    localization of AbstractDateCheckWithSuggestionsFilter (with
    DateFilterHelper)."""

    def get_day_of_week(self, day_str):
        return _get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return _get_day_of_week_name(date)

    def get_month(self, month_str):
        return _get_month(month_str)

    def get_error_message_wrong_year(self):
        return 'Aquesta data no és correcta. ¿Us referiu a l\'any "{currentYear}"?'


class NewYearDateFilter(AbstractNewYearDateFilter):
    """Port of org.languagetool.rules.ca.NewYearDateFilter (with
    DateFilterHelper)."""

    def get_month(self, month_str):
        return _get_month(month_str)


class CatalanNumberInWordFilter(AbstractNumberInWordFilter):
    """Port of org.languagetool.rules.ca.CatalanNumberInWordFilter: asks the
    MorfologikCatalanSpellerRule of Catalan (its misspelling check and
    spelling suggestions are ported, see langtool.lang.ca.spelling) whether
    a word is misspelled and for its spelling suggestions."""

    def is_misspelled(self, word):
        return _catalan().get_default_spelling_rule().is_misspelled(word)

    def get_suggestions(self, word):
        return _catalan().get_default_spelling_rule().get_spelling_suggestions(word)


class RemoveSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.RemoveSuggestionsFilter: removes the
    suggestions matching the regular expression removeSuggestionsRegexp
    (case sensitive); without suggestions left the match is discarded."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        regexp_pattern = jregex.compile(self.get_required('removeSuggestionsRegexp', arguments))
        new_replacements = [r for r in match.suggested_replacements if not regexp_pattern.fullmatch(r)]
        if not new_replacements:
            return None
        match.set_suggested_replacements(new_replacements)
        return match


_INCORRECT_VERB_CHUNK = ChunkTag('_incorrect_verb_')


class CatalanSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.ca.CatalanSuppressMisspelledSuggestionsFilter:
    a suggestion is misspelled if the default spelling rule of the language
    (its ported misspelling check, see langtool.lang.ca.spelling) would
    find an error in it: first in the raw analyzed sentence (for
    suggestions without spaces), then in the fully analyzed text, where
    tokens with the chunk tag _incorrect_verb_ also count as errors.
    Without a spelling rule every suggestion is misspelled (as in Java)."""

    def is_misspelled(self, s, language):
        speller_rule = language.get_default_spelling_rule()
        if speller_rule is None:
            return True
        lt = _default_tool(language)
        # Fast path: run the speller rule without the (expensive) disambiguator. If it already
        # finds a problem, there is no need for a full analysis. Only suggestions that pass this
        # cheap check need the full analysis to look for the "_incorrect_verb_" chunk tag.
        # Restricted to single tokens: multi-token suggestions may be accepted thanks to chunk
        # tags added by the disambiguator, so they need the full analysis.
        if ' ' not in s:
            raw_sentence = lt.get_raw_analyzed_sentence(s)
            if speller_rule.sentence_has_match(raw_sentence):
                return True
        sentence = lt.analyze_text(s)[0]
        has_incorrect_verb = any(_INCORRECT_VERB_CHUNK in x.chunk_tags
                                 for x in sentence.get_tokens_without_whitespace())
        return has_incorrect_verb or speller_rule.sentence_has_match(sentence)


# lemma exceptions
_LEMMAS_TO_IGNORE = ('enterar', 'sentar', 'conseguir', 'alcançar', 'liar', 'vore')
_LEMMAS_TO_ALLOW = ('enter', 'sentir')
# (Java: Pattern.CASE_INSENSITIVE without UNICODE_CASE)
_ELA_GEMINADA = jregex.compile('(?i)(l)[\\.•⋅∙\\-](l)')


class FindSuggestionsFilter(AbstractFindSuggestionsFilter):
    """Port of org.languagetool.rules.ca.FindSuggestionsFilter: the
    suggestions are the similar words of the MorfologikSpeller for
    /ca/ca-ES_spelling.dict (with the maximum edit distance 1), tagged with
    CatalanTagger.INSTANCE_CAT; suggestions with some lemmas are ignored;
    the wrong word is used without spaces and with a corrected "ela
    geminada". There is no synthesizer (as in Java)."""

    DICT_FILENAME = '/ca/ca-ES_spelling.dict'

    def get_tagger(self):
        from . import catalan_tagger
        return catalan_tagger(_catalan())

    def get_spelling_suggestions(self, atr):
        from ...spelling import morfologik_suggestion_speller
        return morfologik_suggestion_speller(_catalan(), self.DICT_FILENAME).find_similar_words(atr.token)

    def is_suggestion_exception(self, analyzed_suggestion):
        return (analyzed_suggestion.has_any_lemma(*_LEMMAS_TO_IGNORE)
                and not analyzed_suggestion.has_any_lemma(*_LEMMAS_TO_ALLOW))

    def pre_process_wrong_word(self, word):
        word = word.replace(' ', '')
        return jregex.java_replace(_ELA_GEMINADA, '$1·$2', word)


# es + unknown -> és + noun/adj | es + verb 3rd person
_P_POSTAG_NOMINAL = jregex.compile('NP..[^0].*|NC.[SN].*|A...[SN].|V.P..S..|V.[NG].*|RG|PX..S...')
_P_POSTAG_VERB_3PERSON = jregex.compile('V...3.*')


class FindSuggestionsEsFilter(FindSuggestionsFilter):
    """Port of org.languagetool.rules.ca.FindSuggestionsEsFilter: for "es"
    + unknown word, the spelling suggestions of the unknown word that are
    nouns/adjectives (-> "és" + word) or verbs in the third person (-> "es"
    + word, if the word doesn't need an apostrophe)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        replacements = []
        pos_word = 0
        while pos_word < len(pattern_tokens) and (pattern_tokens[pos_word].start_pos < match.from_pos
                                                  or pattern_tokens[pos_word].is_sentence_start):
            pos_word += 1
        pos_word += 1
        atr_word = pattern_tokens[pos_word]
        suggestions = self.get_spelling_suggestions_cached(atr_word)
        used_es_accent = False
        used_es = False
        for suggestion in suggestions:
            # TODO: do not tag capitalized words with tags for lower case
            for analyzed_suggestion in self.get_tagger().tag([self.clean_suggestion(suggestion)]):
                if len(replacements) >= 2 * self.MAX_SUGGESTIONS:
                    break
                if analyzed_suggestion.matches_pos_tag_regex(_P_POSTAG_NOMINAL):
                    replacements.append('és ' + analyzed_suggestion.token)
                    used_es_accent = True
                if analyzed_suggestion.matches_pos_tag_regex(_P_POSTAG_VERB_3PERSON):
                    if not needs_apostrophation_ms(analyzed_suggestion.token):
                        replacements.append('es ' + analyzed_suggestion.token.lower())
                        used_es = True
        if not replacements:
            return None
        first_ch = pattern_tokens[pos_word - 1].token[:1]
        if first_ch.upper() == first_ch:
            definitive_replacements = [uppercase_first_char(r) for r in replacements]
        else:
            definitive_replacements = list(replacements)
        is_first_es_accent = java_equals_ignore_case(pattern_tokens[pos_word - 1].token, 'és')
        message = match.message
        if is_first_es_accent and used_es_accent and not used_es:
            # show just the spelling rule
            return None
        if used_es_accent:
            message = message + " \"És\" (del verb 'ser') s'escriu amb accent."
        if used_es:
            message = message + ' "Es" (pronom) acompanya un verb en tercera persona.'
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message, match.short_message)
        rule_match.type = match.type
        rule_match.set_suggested_replacements(definitive_replacements)
        return rule_match


class TextToNumberFilter(AbstractTextToNumberFilter):
    """Port of org.languagetool.rules.ca.TextToNumberFilter: the number
    written in words (Catalan numbers and multipliers, compounds split at
    hyphens) with a decimal comma."""

    numbers = {k: java_float(v) for k, v in {
        'zero': 0, 'mig': 0.5, 'un': 1, 'u': 1, 'una': 1, 'dos': 2, 'dues': 2, 'tres': 3, 'quatre': 4, 'cinc': 5,
        'sis': 6, 'set': 7, 'vuit': 8, 'huit': 8, 'nou': 9, 'deu': 10, 'onze': 11, 'dotze': 12, 'tretze': 13,
        'catorze': 14, 'quinze': 15, 'setze': 16, 'disset': 17, 'desset': 17, 'dèsset': 17, 'divuit': 18,
        'devuit': 18, 'díhuit': 18, 'dinou': 19, 'denou': 19, 'dènou': 19, 'dèneu': 19, 'vint': 20, 'trenta': 30,
        'quaranta': 40, 'cinquanta': 50, 'seixanta': 60, 'setanta': 70, 'vuitanta': 80, 'huitanta': 80,
        'noranta': 90}.items()}
    multipliers = {k: java_float(v) for k, v in {
        'cent': 100, 'cents': 100, 'mil': 1000, 'milió': 1000000, 'milions': 1000000, 'bilió': 10E12,
        'bilions': 10E12, 'trilió': 10E18, 'trilions': 10E18}.items()}

    def is_comma(self, s):
        return java_equals_ignore_case(s, 'comma') or java_equals_ignore_case(s, 'coma')

    def is_percentage(self, pattern_tokens, i):
        return pattern_tokens[i].token == 'cent' and pattern_tokens[i - 1].token.lower() == 'per'

    def tokenize(self, s):
        return java_split(s, '-')

    def format_result(self, s):
        return s.replace('.', ',')


# --- DiacriticsCheckFilter ---

_relevant_words = None
_relevant_words_lock = threading.Lock()


def load_confusion_pairs(path):
    """ConfusionPairsDataLoader.loadWords: form -> AnalyzedTokenReadings of
    the (token, POS tag) readings of the file"""
    m = {}
    with open(path, encoding='utf-8') as f:
        for raw in f.read().splitlines():
            line = java_trim(raw)
            if not line or line[0] == '#':  # ignore comments
                continue
            parts = java_split(line, ';')
            if len(parts) != 3:
                raise RuntimeError('Format error in file ' + path + ', line: ' + line + ', '
                                   + 'expected 3 semicolon-separated parts, got ' + str(len(parts)))
            analyzed_token = AnalyzedToken(parts[1], parts[2], None)
            atrs = m.get(parts[0])
            if atrs is None:
                m[parts[0]] = AnalyzedTokenReadings(analyzed_token, 0)
            else:
                atrs.add_reading(analyzed_token, '')
    return m


def _confusion_pairs(language):
    global _relevant_words
    if _relevant_words is None:
        with _relevant_words_lock:
            if _relevant_words is None:
                _relevant_words = load_confusion_pairs(_rules_file(language, '/ca/confusion_pairs.txt'))
    return _relevant_words


_MS = jregex.compile('NC[MC][SN]000|A..[MC][SN].|V.P..SM.')
_FS = jregex.compile('NC[FC][SN]000|A..[FC][SN].|V.P..SF.')
_MP = jregex.compile('NC[MC][PN]000|A..[MC][PN].|V.P..PM.')
_FP = jregex.compile('NC[FC][PN]000|A..[FC][PN].|V.P..PF.')
_CP = jregex.compile('NC[MFC][PN]000|A..[MFC][PN].|V.P..P..')
_CS = jregex.compile('NC[MFC][SN]000|A..[MFC][SN].|V.P..S..')
_GENDER_NUMBER = (('[NAPD].+MS.*|V.P..SM.', _MS), ('[NAPD].+MP.*|V.P..PM.', _MP), ('[NAPD].+FS.*|V.P..SF.', _FS),
                  ('[NAPD].+FP.*|V.P..PF.', _FP), ('[NAPD].+CP.*|V.P..P..', _CP), ('[NAPD].+CS.*|V.P..S..', _CS))


class DiacriticsCheckFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.DiacriticsCheckFilter: accepts the
    match if the form (argument 'form', lowercased) is in
    /ca/confusion_pairs.txt with a reading matching the argument 'postag'
    (and, with 'gendernumberFrom', if the first reading of the confusion
    agrees in gender and number with that token); the confused word
    replaces {suggestion} in the suggestions."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        relevant_words = _confusion_pairs(self.get_language_from_rule_match(match))
        desired_gender_number_pattern = None
        replacement = None
        postag = self.get_required('postag', arguments)
        original_form = self.get_required('form', arguments)
        is_all_upper = is_all_uppercase(original_form)
        is_capitalized = is_capitalized_word(original_form)
        form = original_form.lower()
        gendernumber_from = self.get_optional('gendernumberFrom', arguments)
        if gendernumber_from is not None:
            i = int(gendernumber_from)
            if i < 1 or i > len(pattern_tokens):
                raise ValueError('ConfusionCheckFilter: Index out of bounds in ' + match.rule.get_full_id()
                                 + ', value: ' + str(i))
            atr = pattern_tokens[i - 1]
            for regex, pattern in _GENDER_NUMBER:
                if atr.matches_pos_tag_regex(regex):
                    desired_gender_number_pattern = pattern
                    break
        atrs = relevant_words.get(form)
        if atrs is not None:
            if atrs.matches_pos_tag_regex(postag):
                if desired_gender_number_pattern is not None:
                    if not desired_gender_number_pattern.fullmatch(atrs.readings[0].pos_tag):
                        return None
                    replacement = atrs.token
                elif gendernumber_from is None:
                    # there is no desired gender number defined
                    replacement = atrs.token
        if replacement is not None:
            message = match.message
            # Change the message if the replacement has no diacritic
            if not (has_diacritics(replacement) and not has_diacritics(form)):
                message = message.replace("s'escriu amb accent", "s'escriu d'una altra manera")
            rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message,
                                   match.short_message)
            rule_match.type = match.type
            if is_all_upper:
                replacement = replacement.upper()
            if is_capitalized:
                replacement = uppercase_first_char(replacement)
            for sugg in match.suggested_replacements:
                suggestion = sugg.replace('{suggestion}', replacement)
                suggestion = suggestion.replace('{Suggestion}', uppercase_first_char(replacement))
                suggestion = suggestion.replace('{SUGGESTION}', replacement.upper())
                rule_match.add_suggested_replacement(suggestion)
            return rule_match
        return None


# the filter classes of this module (registered as org.languagetool.rules.ca.<class name>)
FILTERS = (AdvancedSynthesizerFilter, CatalanNumberSpellerFilter, DateCheckFilter, NewYearDateFilter,
           CatalanNumberInWordFilter, RemoveSuggestionsFilter, CatalanSuppressMisspelledSuggestionsFilter,
           FindSuggestionsFilter, FindSuggestionsEsFilter, TextToNumberFilter, DiacriticsCheckFilter)
# rule factories of this module: Java class name -> factory(messages, language, user_config, **kwargs)
RULES = {}
