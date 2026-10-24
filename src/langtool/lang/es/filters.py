"""Spanish rule filters (port of the filters of org.languagetool.rules.es:
AdvancedSynthesizerFilter, ConfusionCheckFilter with ConfusionPairsDataLoader,
DateCheckFilter, NewYearDateFilter and DateFilterHelper, FindSuggestionsFilter,
SpanishNumberInWordFilter, SpanishSuppressMisspelledSuggestionsFilter and
TextToNumberFilter; PostponedAdjectiveConcordanceFilter is in
langtool.lang.es.agreement)."""

import threading

from ... import jregex
from ...rules.abstract_rules import _rules_file
from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckWithSuggestionsFilter,
                                   AbstractFindSuggestionsFilter, AbstractNewYearDateFilter,
                                   AbstractNumberInWordFilter, AbstractSuppressMisspelledSuggestionsFilter,
                                   AbstractTextToNumberFilter,
                                   SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RuleFilter
from ...tools import (has_diacritics, is_all_uppercase, is_capitalized_word, java_equals_ignore_case, java_split,
                      java_trim, uppercase_first_char)


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.es.AdvancedSynthesizerFilter: the
    AbstractAdvancedSynthesizerFilter without changes (synthesize
    suggestions using the lemma from one token and the POS tag from
    another one)."""


class SpanishSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.es.SpanishSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of Spanish, see langtool.lang.es.spelling)."""


class SpanishNumberInWordFilter(AbstractNumberInWordFilter):
    """Port of org.languagetool.rules.es.SpanishNumberInWordFilter. Java
    asks a MorfologikSpanishSpellerRule whether a word is misspelled (its
    misspelling check is ported, see langtool.lang.es.spelling) and for its
    spelling suggestions (not ported: spell checking, so there are
    none)."""

    def is_misspelled(self, word):
        from ...api import get_language
        return get_language('es').get_default_spelling_rule().is_misspelled(word)

    def get_suggestions(self, word):
        return []


# --- DateFilterHelper ---

# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.UK) mapped to Spanish
_DAY_NAMES = {SUNDAY: 'domingo', MONDAY: 'lunes', TUESDAY: 'martes', WEDNESDAY: 'miércoles', THURSDAY: 'jueves',
              FRIDAY: 'viernes', SATURDAY: 'sábado'}
_DAYS = {'do': SUNDAY, 'domingo': SUNDAY, 'lu': MONDAY, 'lunes': MONDAY, 'ma': TUESDAY, 'martes': TUESDAY,
         'mi': WEDNESDAY, 'miércoles': WEDNESDAY, 'ju': THURSDAY, 'jueves': THURSDAY, 'vi': FRIDAY,
         'viernes': FRIDAY, 'sa': SATURDAY, 'sábado': SATURDAY}


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
    if mon.startswith('en'):
        return 1
    if mon.startswith('fe'):
        return 2
    if mon.startswith('mar') or mon.startswith('mzo'):
        return 3
    if mon.startswith('ab'):
        return 4
    if mon.startswith('may') or mon.startswith('my'):
        return 5
    if mon.startswith('jun') or mon == 'jn':
        return 6
    if mon.startswith('jul') or mon == 'jl':
        return 7
    if mon.startswith('ag'):
        return 8
    if mon.startswith('se') or mon.startswith('sep'):
        return 9
    if mon.startswith('oc'):
        return 10
    if mon.startswith('no'):
        return 11
    if mon.startswith('di'):
        return 12
    raise RuntimeError("Could not find month '" + month_str + "'")


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.es.DateCheckFilter, the Spanish
    localization of AbstractDateCheckWithSuggestionsFilter (with
    DateFilterHelper)."""

    def get_day_of_week(self, day_str):
        return _get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return _get_day_of_week_name(date)

    def get_month(self, month_str):
        return _get_month(month_str)

    def get_error_message_wrong_year(self):
        return 'Este fecha no es correcta. ¿Se refería al año "{currentYear}"?'


class NewYearDateFilter(AbstractNewYearDateFilter):
    """Port of org.languagetool.rules.es.NewYearDateFilter (with
    DateFilterHelper)."""

    def get_month(self, month_str):
        return _get_month(month_str)


class FindSuggestionsFilter(AbstractFindSuggestionsFilter):
    """Port of org.languagetool.rules.es.FindSuggestionsFilter: the
    suggestions are the similar words of the MorfologikSpeller for the
    tagger dictionary /es/es-ES.dict (with the maximum edit distance 1),
    tagged with the Spanish tagger. There is no synthesizer (as in
    Java)."""

    def get_tagger(self):
        return self._spanish().tagger

    def get_spelling_suggestions(self, atr):
        from ...spelling import morfologik_suggestion_speller
        return morfologik_suggestion_speller(self._spanish(), '/es/es-ES.dict').find_similar_words(atr.token)

    @staticmethod
    def _spanish():
        from ...api import get_language
        return get_language('es')


class TextToNumberFilter(AbstractTextToNumberFilter):
    """Port of org.languagetool.rules.es.TextToNumberFilter: the number
    written in words (Spanish numbers and multipliers)."""

    numbers = {
        'cero': 0, 'medio': 0.5, 'un': 1, 'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
        'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10, 'once': 11, 'doce': 12, 'trece': 13,
        'catorce': 14, 'quince': 15, 'dieciséis': 16, 'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19,
        'veinte': 20, 'veintiuno': 21, 'veintidós': 22, 'veintitrés': 23, 'veinticuatro': 24, 'veinticinco': 25,
        'veintiséis': 26, 'veintisiete': 27, 'veintiocho': 28, 'veintinueve': 29, 'treinta': 30,
        'cuarenta': 40, 'cincuenta': 50, 'sesenta': 60, 'setenta': 70, 'ochenta': 80, 'noventa': 90,
        'cien': 100, 'ciento': 100, 'doscientos': 200, 'trescientos': 300, 'cuatrocientos': 400,
        'quinientos': 500, 'seiscientos': 600, 'setecientos': 700, 'ochocientos': 800, 'novecientos': 900,
        'doscientas': 200, 'trescientas': 300, 'cuatrocientas': 400, 'quinientas': 500, 'seiscientas': 600,
        'setecientas': 700, 'ochocientas': 800, 'novecientas': 900,
    }
    multipliers = {
        'mil': 1000, 'millón': 1000000, 'millones': 1000000, 'billón': 10E12, 'billones': 10E12,
        'trillón': 10E18, 'trillones': 10E18,
    }

    def is_comma(self, s):
        return java_equals_ignore_case(s, 'comma') or java_equals_ignore_case(s, 'coma')

    def is_percentage(self, pattern_tokens, i):
        return pattern_tokens[i].token == 'ciento' and pattern_tokens[i - 1].token.lower() == 'por'


# --- ConfusionCheckFilter ---

_relevant_words = None
_relevant_words_lock = threading.Lock()


def _load_confusion_pairs(path):
    """ConfusionPairsDataLoader.loadWords: form -> list of (token, POS tag)
    readings (an AnalyzedTokenReadings in Java)"""
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
            m.setdefault(parts[0], []).append((parts[1], parts[2]))
    return m


def _confusion_pairs(language):
    global _relevant_words
    if _relevant_words is None:
        with _relevant_words_lock:
            if _relevant_words is None:
                _relevant_words = _load_confusion_pairs(_rules_file(language, '/es/confusion_pairs.txt'))
    return _relevant_words


def _matches_pos_tag_regex(readings, pattern):
    """AnalyzedTokenReadings.matchesPosTagRegex"""
    p = jregex.compile(pattern)
    return any(tag is not None and p.fullmatch(tag) for _token, tag in readings)


_MS = jregex.compile('NC[MC][SN]000|A..[MC][SN].|V.P..SM')
_FS = jregex.compile('NC[FC][SN]000|A..[FC][SN].|V.P..SF')
_MP = jregex.compile('NC[MC][PN]000|A..[MC][PN].|V.P..PM')
_FP = jregex.compile('NC[FC][PN]000|A..[FC][PN].|V.P..PF')
_CP = jregex.compile('NC[MFC][PN]000|A..[MFC][PN].|V.P..P.')
_CS = jregex.compile('NC[MFC][SN]000|A..[MFC][SN].|V.P..S.')
_GENDER_NUMBER = (('[NAPD].+MS.*|V.P..SM', _MS), ('[NAPD].+MP.*|V.P..PM', _MP), ('[NAPD].+FS.*|V.P..SF', _FS),
                  ('[NAPD].+FP.*|V.P..PF', _FP), ('[NAPD].+CP.*|V.P..P.', _CP), ('[NAPD].+CS.*|V.P..S.', _CS))


class ConfusionCheckFilter(RuleFilter):
    """Port of org.languagetool.rules.es.ConfusionCheckFilter: accepts the
    match if the form (argument 'form', lowercased) is in
    /es/confusion_pairs.txt with a reading matching the argument 'postag'
    (and, with 'gendernumberFrom', if the first reading of the confusion
    agrees in gender and number with that token); the confused word
    replaces {suggestion} in the first suggestion."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        relevant_words = _confusion_pairs(match.rule.language)
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
        readings = relevant_words.get(form)
        if readings is not None:
            if _matches_pos_tag_regex(readings, postag):
                if desired_gender_number_pattern is not None:
                    if not desired_gender_number_pattern.fullmatch(readings[0][1]):
                        return None
                    replacement = readings[0][0]
                elif gendernumber_from is None:
                    # there is no desired gender number defined
                    replacement = readings[0][0]
        if replacement is not None:
            message = match.message
            # Change the message if the replacement has no diacritic
            if not (has_diacritics(replacement) and not has_diacritics(form)):
                message = message.replace('se escribe con tilde', 'se escribe de otra manera')
            rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message,
                                   match.short_message)
            rule_match.type = match.type
            if is_all_upper:
                replacement = replacement.upper()
            if is_capitalized:
                replacement = uppercase_first_char(replacement)
            suggestion = match.suggested_replacements[0].replace('{suggestion}', replacement)
            suggestion = suggestion.replace('{Suggestion}', uppercase_first_char(replacement))
            suggestion = suggestion.replace('{SUGGESTION}', replacement.upper())
            rule_match.set_suggested_replacement(suggestion)
            return rule_match
        return None
