"""Italian rule filters (port of org.languagetool.rules.it filters)."""

from ...rules.core_filters import (AbstractDateCheckFilter, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
                                   SATURDAY)

_DAY_NAMES = {SUNDAY: 'domenica', MONDAY: 'lunedì', TUESDAY: 'martedì', WEDNESDAY: 'mercoledì',
              THURSDAY: 'giovedì', FRIDAY: 'venerdì', SATURDAY: 'sabato'}

_MONTH_PREFIXES = ('gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic')


class DateCheckFilter(AbstractDateCheckFilter):
    """Port of org.languagetool.rules.it.DateCheckFilter, the Italian
    localization of AbstractDateCheckFilter (Java's getCalendar() returns a
    Calendar for Locale.UK, which doesn't change the result)."""

    def get_day_of_week(self, day_str):
        day = day_str.lower()
        if day.startswith('do') or day == 'domenica':
            return SUNDAY
        if day.startswith('lu') or day == 'lunedì':
            return MONDAY
        if day.startswith('ma') or day == 'martedì':
            return TUESDAY
        if day.startswith('me') or day == 'mercoledì':
            return WEDNESDAY
        if day.startswith('gi') or day == 'giovedì':
            return THURSDAY
        if day.startswith('ve') or day == 'venerdì':
            return FRIDAY
        if day.startswith('sa') or day == 'sabato':
            return SATURDAY
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    def get_day_of_week_name(self, date):
        # Java: maps the English (Locale.UK) display name of the day of week
        return _DAY_NAMES.get(date.day_of_week, '')

    def get_month(self, month_str):
        mon = month_str.lower()
        for i, prefix in enumerate(_MONTH_PREFIXES):
            if mon.startswith(prefix):
                return i + 1
        raise RuntimeError("Could not find month '" + month_str + "'")
