"""Breton rule filters (port of org.languagetool.rules.br filters)."""

from ...rules.core_filters import (AbstractDateCheckFilter, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
                                   SATURDAY)

_DAY_NAMES = {SUNDAY: 'Sul', MONDAY: 'Lun', TUESDAY: 'Meurzh', WEDNESDAY: 'Merc’her', THURSDAY: 'Yaou',
              FRIDAY: 'Gwener', SATURDAY: 'Sadorn'}

_DAYS_OF_MONTH = {
    'c’hentañ': 1, 'unan': 1,
    'daou': 2, 'eil': 2,
    'dri': 3, 'drede': 3, 'deir': 3,
    'bevar': 4,
    # bemp or bemvet (vet has been removed).
    'bemp': 5, 'bem': 5,
    'c’hwerc’h': 6,
    'seizh': 7,
    'eizh': 8,
    # nav and navet (vet has been removed).
    'nav': 9, 'na': 9,
    'dek': 10,
    'unnek': 11,
    'daouzek': 12,
    'drizek': 13,
    'bevarzek': 14,
    'bemzek': 15,
    'c’hwezek': 16,
    'seitek': 17,
    'driwec’h': 18,
    'naontek': 19,
    'ugent': 20,
    'dregont': 30,
}

_MONTHS = {
    'genver': 1, 'c’hwevrer': 2, 'meurzh': 3, 'ebrel': 4, 'mae': 5, 'mezheven': 6, 'even': 6,
    'gouere': 7, 'gouhere': 7, 'eost': 8, 'gwengolo': 9, 'here': 10, 'du': 11, 'kerzu': 12,
}


class DateCheckFilter(AbstractDateCheckFilter):
    """Port of org.languagetool.rules.br.DateCheckFilter, the Breton
    localization of AbstractDateCheckFilter (Java's getCalendar() returns a
    Calendar for Locale.UK, which doesn't change the result)."""

    def get_day_of_month(self, day_str):
        day = day_str.lower()
        # (an empty string raises IndexError like Java's charAt(0), a
        # RuntimeException that discards the match)
        if day[0] == 't':
            day = 'd' + day[1:]
        if day[0] == 'p':
            day = 'b' + day[1:]
        if day.endswith('vet'):
            # Removing final vet if any.
            day = day[:-3]
        return _DAYS_OF_MONTH.get(day, 0)

    def get_day_of_week(self, day_str):
        day = day_str.lower()
        if day.endswith('sul'):
            return SUNDAY
        if day.endswith('lun'):
            return MONDAY
        if day.endswith('meurzh'):
            return TUESDAY
        if day.endswith('merc’her'):
            return WEDNESDAY
        if day == 'yaou':
            return THURSDAY
        if day == 'diriaou':
            return THURSDAY
        if day.endswith('gwener'):
            return FRIDAY
        if day.endswith('sadorn'):
            return SATURDAY
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    def get_day_of_week_name(self, date):
        # Java: maps the English (Locale.UK) display name of the day of week
        return _DAY_NAMES.get(date.day_of_week, '')

    def get_month(self, month_str):
        mon = month_str.lower()
        month = _MONTHS.get(mon)
        if month is None:
            raise RuntimeError("Could not find month '" + month_str + "'")
        return month
