"""Polish rule filters (port of org.languagetool.rules.pl.DateCheckFilter
and DecadeSpellingFilter)."""

from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractDateCheckFilter, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
                                   SATURDAY, java_parse_int)
from ...rules.filters import RuleFilter

# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.forLanguageTag("pl"))
_DAY_NAMES = {SUNDAY: 'niedziela', MONDAY: 'poniedziałek', TUESDAY: 'wtorek', WEDNESDAY: 'środa',
              THURSDAY: 'czwartek', FRIDAY: 'piątek', SATURDAY: 'sobota'}

_MONTHS = (('stycznia', 'I'), ('lutego', 'II'), ('marca', 'III'), ('kwietnia', 'IV'), ('maja', 'V'),
           ('czerwca', 'VI'), ('lipca', 'VII'), ('sierpnia', 'VIII'), ('września', 'IX'),
           ('października', 'X'), ('listopada', 'XI'), ('grudnia', 'XII'))


class DateCheckFilter(AbstractDateCheckFilter):
    """Port of org.languagetool.rules.pl.DateCheckFilter, the Polish
    localization of AbstractDateCheckFilter (Java's getCalendar() returns a
    Calendar for the locale "pl", which doesn't change the result)."""

    def get_day_of_week(self, day_str):
        day = day_str.lower()
        if day.startswith('pon'):
            return MONDAY
        if day.startswith('wt'):
            return TUESDAY
        if day.startswith('śr'):
            return WEDNESDAY
        if day.startswith('czw'):
            return THURSDAY
        if day == 'pt' or day.startswith('piątk') or day == 'piątek':
            return FRIDAY
        if day.startswith('sob'):
            return SATURDAY
        if day.startswith('niedz'):
            return SUNDAY
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    def get_day_of_week_name(self, date):
        return _DAY_NAMES.get(date.day_of_week, '')

    def get_month(self, month_str):
        mon = month_str.lower()
        for i, (name, roman) in enumerate(_MONTHS):
            if mon == name or month_str == roman:
                return i + 1
        raise RuntimeError("Could not find month '" + month_str + "'")


_NUMBERS = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
_LETTERS = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')


def _get_roman_number(num):
    """The Roman notation of a number."""
    roman = []
    n = num  # the part of num that still has to be converted
    for number, letters in zip(_NUMBERS, _LETTERS):
        while n >= number:
            roman.append(letters)
            n -= number
    return ''.join(roman)


class DecadeSpellingFilter(RuleFilter):
    """Port of org.languagetool.rules.pl.DecadeSpellingFilter: creates the
    message of the DATA_DEKADY rule from the argument 'lata' (a year like
    "1970"): {dekada} becomes the decade ("70") and {wiek} the century in
    Roman numerals ("XX")."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lata = arguments.get('lata')
        if lata is None or len(lata) < 2:
            # NullPointerException / StringIndexOutOfBoundsException in Java
            raise IndexError("Invalid argument 'lata': %r" % (lata,))
        decade = lata[2:]
        century = lata[:2]
        try:
            cent = java_parse_int(century)
        except ValueError:
            # (NumberFormatException) ignore it silently
            return None
        message = match.message.replace('{dekada}', decade).replace('{wiek}', _get_roman_number(cent + 1))
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message,
                               match.short_message, match.pattern_from_pos, match.pattern_to_pos,
                               match.from_pos == 0)
        rule_match.type = match.type
        return rule_match
