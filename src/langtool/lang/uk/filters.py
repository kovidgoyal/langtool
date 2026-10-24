"""Port of org.languagetool.rules.uk.DateCheckFilter."""

from ...rules.core_filters import (AbstractDateCheckFilter, SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
                                   SATURDAY)

# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.forLanguageTag("uk"))
# (CLDR, with the modifier letter apostrophe U+02BC)
_DAY_NAMES = {SUNDAY: 'неділя', MONDAY: 'понеділок', TUESDAY: 'вівторок', WEDNESDAY: 'середа',
              THURSDAY: 'четвер', FRIDAY: 'пʼятниця', SATURDAY: 'субота'}


class DateCheckFilter(AbstractDateCheckFilter):
    """Ukrainian localization of AbstractDateCheckFilter (Java's
    getCalendar() returns a Calendar for the locale "uk", which doesn't
    change the result)."""

    def get_day_of_week(self, day_str):
        day = day_str.lower()
        if day.startswith('по') or day == 'пн':
            return MONDAY
        if day.startswith('ві') or day == 'вт':
            return TUESDAY
        if day.startswith('се') or day == 'ср':
            return WEDNESDAY
        if day.startswith('че') or day == 'чт':
            return THURSDAY
        if day.startswith("п'") or day.startswith('п’') or day == 'пт':
            return FRIDAY
        if day.startswith('су') or day == 'сб':
            return SATURDAY
        if day.startswith('не') or day == 'нд':
            return SUNDAY
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    def get_day_of_week_name(self, date):
        return _DAY_NAMES.get(date.day_of_week, '')

    def get_month(self, month_str):
        mon = month_str.lower()
        if mon.startswith('сі'):
            return 1
        if mon.startswith('лю'):
            return 2
        if mon.startswith('бе'):
            return 3
        if mon.startswith('кв'):
            return 4
        if mon.startswith('тр'):
            return 5
        if mon.startswith('че'):
            return 6
        if mon.startswith('ли'):
            return 7
        if mon.startswith('се'):
            return 8
        if mon.startswith('ве'):
            return 9
        if mon.startswith('жо'):
            return 10
        if mon.startswith('ли'):  # (unreachable, as in Java: листопад gives 7)
            return 11
        if mon.startswith('гр'):
            return 12
        raise RuntimeError("Could not find month '" + month_str + "'")
