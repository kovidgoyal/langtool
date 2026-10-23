"""Esperanto rule filters (port of org.languagetool.rules.eo filters)."""

from ...rules.core_filters import (AbstractDateCheckFilter, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
                                   SATURDAY)

_DAY_NAMES = {SUNDAY: 'dimanĉo', MONDAY: 'lundo', TUESDAY: 'mardo', WEDNESDAY: 'merkredo',
              THURSDAY: 'jaŭdo', FRIDAY: 'vendredo', SATURDAY: 'sabato'}

_DAYS_OF_WEEK = (('dim', SUNDAY), ('lun', MONDAY), ('mar', TUESDAY), ('mer', WEDNESDAY), ('ĵaŭ', THURSDAY),
                 ('jau', THURSDAY), ('jhau', THURSDAY), ('jxau', THURSDAY), ('ven', FRIDAY), ('sab', SATURDAY))

_MONTH_PREFIXES = ('jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aŭg', 'sep', 'okt', 'nov', 'dec')

_ORDINALS = {'unua': 1, 'dua': 2, 'tria': 3, 'kvara': 4, 'kvina': 5, 'sesa': 6, 'sepa': 7, 'oka': 8,
             'naŭa': 9, 'nauxa': 9, 'naua': 9}


class DateCheckFilter(AbstractDateCheckFilter):
    """Port of org.languagetool.rules.eo.DateCheckFilter, the Esperanto
    localization of AbstractDateCheckFilter (Java's getCalendar() returns a
    Calendar for Locale.UK, which doesn't change the result)."""

    def get_day_of_month(self, day_str):
        day = day_str.lower()
        if day.endswith('n'):
            # Removing final n if any.
            day = day[:-1]
        n = 0
        if day.startswith('dek'):
            n = 10
            day = day[3:]
        elif day.startswith('dudek'):
            n = 20
            day = day[5:]
        elif day.startswith('tridek'):
            n = 30
            day = day[6:]
        if n > 0 and day.startswith('-'):
            # Remove hyphen as in "dudek-trian".
            day = day[1:]
        return n + _ORDINALS.get(day, 0)

    def get_day_of_week(self, day_str):
        day = day_str.lower()
        for prefix, day_of_week in _DAYS_OF_WEEK:
            if day.startswith(prefix):
                return day_of_week
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
