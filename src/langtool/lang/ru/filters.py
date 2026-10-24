"""Russian rule filters (port of org.languagetool.rules.ru.AdvancedSynthesizerFilter,
DateCheckFilter, DateFilterHelper, FutureDateFilter, INNNumberFilter,
NoDisambiguationRussianPartialPosTagFilter, RussianPartialPosTagFilter and
RussianSuppressMisspelledSuggestionsFilter).

Java lowercases with the default locale or Locale("ru"), which have no
special case mapping for Russian (str.lower here)."""

from ... import jregex
from ...analysis import AnalyzedSentence
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckFilter,
                                   AbstractFutureDateFilter, AbstractSuppressMisspelledSuggestionsFilter,
                                   PartialPosTagFilter, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
                                   SATURDAY)
from ...rules.filters import RuleFilter
from ...tools import trim_special_characters


def _russian():
    from ...api import get_language
    return get_language('ru')


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.ru.AdvancedSynthesizerFilter: the
    AbstractAdvancedSynthesizerFilter without changes (synthesize
    suggestions using the lemma from one token (lemma_from) and the POS tag
    from another one (postag_from))."""


# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.forLanguageTag("ru"))
_DAY_NAMES = {SUNDAY: 'воскресенье', MONDAY: 'понедельник', TUESDAY: 'вторник', WEDNESDAY: 'среда',
              THURSDAY: 'четверг', FRIDAY: 'пятница', SATURDAY: 'суббота'}

# DateCheckFilter.getMonth: (names and abbreviations, Roman numeral)
_MONTHS = (
    (('январь', 'января', 'янв'), 'I'),
    (('февраль', 'февраля', 'фев'), 'II'),
    (('март', 'марта', 'мар'), 'III'),
    (('апрель', 'апреля', 'апр'), 'IV'),
    (('май', 'мая'), 'V'),
    (('июнь', 'июня', 'ин'), 'VI'),
    (('июль', 'июля', 'ил'), 'VII'),
    (('август', 'августа', 'авг'), 'VIII'),
    (('сентябрь', 'сентября', 'сен'), 'IX'),
    (('октябрь', 'октября', 'окт'), 'X'),
    (('ноябрь', 'ноября', 'ноя'), 'XI'),
    (('декабрь', 'декабря', 'дек'), 'XII'),
)


class DateCheckFilter(AbstractDateCheckFilter):
    """Port of org.languagetool.rules.ru.DateCheckFilter, the Russian
    localization of AbstractDateCheckFilter (Java's getCalendar() returns a
    Calendar for the locale "ru", which doesn't change the result)."""

    def get_day_of_week(self, day_str):
        day = day_str.lower()
        if day.startswith('пн') or day == 'понедельник':
            return MONDAY
        if day.startswith('вт'):
            return TUESDAY
        if day.startswith('ср'):
            return WEDNESDAY
        if day.startswith('чт') or day == 'четверг':
            return THURSDAY
        if day == 'пт' or day.startswith('пятниц'):
            return FRIDAY
        if day.startswith('сб') or day.startswith('суббот'):
            return SATURDAY
        if day.startswith('вс') or day == 'воскресенье':
            return SUNDAY
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    def get_day_of_week_name(self, date):
        return _DAY_NAMES.get(date.day_of_week, '')

    def get_month(self, month_str):
        mon = month_str.lower()
        for i, (names, roman) in enumerate(_MONTHS):
            if mon == names[0] or month_str == roman or mon in names[1:]:
                return i + 1
        raise RuntimeError("Could not find month '" + month_str + "'")


# DateFilterHelper.getDayOfWeek(String) and getMonth(String): prefixes, in
# the order of the Java checks
_HELPER_DAY_PREFIXES = (('суб', SATURDAY), ('вс', SUNDAY), ('вос', SUNDAY), ('пн', MONDAY), ('пон', MONDAY),
                        ('вт', TUESDAY), ('ср', WEDNESDAY), ('чт', THURSDAY), ('чет', THURSDAY), ('пт', FRIDAY),
                        ('пят', FRIDAY), ('сб', SATURDAY))
_HELPER_MONTH_PREFIXES = (('янв', 1), ('фев', 2), ('мар', 3), ('апр', 4), ('май', 5), ('мая', 5), ('июн', 6),
                          ('июл', 7), ('авг', 8), ('сен', 9), ('окт', 10), ('ноя', 11), ('дек', 12))


class DateFilterHelper:
    """Port of org.languagetool.rules.ru.DateFilterHelper (getCalendar() is
    not needed, see AbstractFutureDateFilter)."""

    @staticmethod
    def get_day_of_week(day_str):
        # quickfix for special characters like soft hyphens
        day = trim_special_characters(day_str).lower()
        for prefix, day_of_week in _HELPER_DAY_PREFIXES:
            if day.startswith(prefix):
                return day_of_week
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    @staticmethod
    def get_day_of_week_name(date):
        return _DAY_NAMES.get(date.day_of_week, '')

    @staticmethod
    def get_month(month_str):
        mon = trim_special_characters(month_str).lower()
        for prefix, month in _HELPER_MONTH_PREFIXES:
            if mon.startswith(prefix):
                return month
        raise RuntimeError("Could not find month '" + month_str + "'")


class FutureDateFilter(AbstractFutureDateFilter):
    """Port of org.languagetool.rules.ru.FutureDateFilter (the months of
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return DateFilterHelper.get_month(localized_month)


_DIGIT_SYMBOL_PATTERN = jregex.compile('(\\d*)')


class INNNumberFilter(RuleFilter):
    """Port of org.languagetool.rules.ru.INNNumberFilter: accepts the match
    if the INN (taxpayer identification number, argument 'inn') of 10 or 12
    digits has wrong check digits."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        inn_number_string = self.get_required('inn', arguments)
        if not _DIGIT_SYMBOL_PATTERN.fullmatch(inn_number_string):
            return None
        # (only ASCII digits, so Character.getNumericValue is the digit value)
        d = [int(c) for c in inn_number_string]
        if len(d) == 10:
            kz1 = (d[0] * 2 + d[1] * 4 + d[2] * 10 + d[3] * 3 + d[4] * 5 + d[5] * 9 + d[6] * 4 + d[7] * 6
                   + d[8] * 8) % 11
            if kz1 > 9:
                kz1 = kz1 - 10
            return None if d[9] == kz1 else match
        if len(d) == 12:
            kz1 = (d[0] * 7 + d[1] * 2 + d[2] * 4 + d[3] * 10 + d[4] * 3 + d[5] * 5 + d[6] * 9 + d[7] * 4
                   + d[8] * 6 + d[9] * 8) % 11
            kz2 = (d[0] * 3 + d[1] * 7 + d[2] * 2 + d[3] * 4 + d[4] * 10 + d[5] * 3 + d[6] * 5 + d[7] * 9
                   + d[8] * 4 + d[9] * 6 + d[10] * 8) % 11
            if kz1 > 9:
                kz1 = kz1 - 10
            if kz2 > 9:
                kz2 = kz2 - 10
            return None if d[10] == kz1 and d[11] == kz2 else match
        return None


class NoDisambiguationRussianPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.ru.NoDisambiguationRussianPartialPosTagFilter:
    a PartialPosTagFilter for Russian that only tags the token (it does not
    run the disambiguator)."""

    def tag(self, token):
        return list(_russian().tagger.tag([token]))


class RussianPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.ru.RussianPartialPosTagFilter: a
    PartialPosTagFilter for Russian that also runs the disambiguator. Note
    that the disambiguator is called with a single token (without sentence
    start), so only rules will apply that have a single <match> element."""

    def tag(self, token):
        russian = _russian()
        tags = russian.tagger.tag([token])
        disambiguated = russian.disambiguator.disambiguate(AnalyzedSentence(list(tags)))
        return list(disambiguated.tokens)


class RussianSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.ru.RussianSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of Russian, see langtool.lang.ru.spelling)."""
