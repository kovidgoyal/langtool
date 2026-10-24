"""Dutch rule filters (port of org.languagetool.rules.nl.CompoundFilter,
DateCheckFilter, DutchNumberInWordFilter and
DutchSuppressMisspelledSuggestionsFilter)."""

from ... import jregex
from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractDateCheckWithSuggestionsFilter, AbstractNumberInWordFilter,
                                   AbstractSuppressMisspelledSuggestionsFilter, SUNDAY, MONDAY, TUESDAY,
                                   WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RuleFilter
from .rules import glue_parts

_SUGGESTION_ELEM = jregex.compile('<suggestion>.*?</suggestion>')


class CompoundFilter(RuleFilter):
    """Port of org.languagetool.rules.nl.CompoundFilter: the suggestion is
    the compound of the arguments word1 ... word5 (glued with
    Tools.glueParts), it replaces the <suggestion> elements of the
    message."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        words = []
        for i in range(1, 6):
            arg = arguments.get('word%d' % i)
            if arg is None:
                break
            words.append(arg)
        repl = glue_parts(words)
        elem = '<suggestion>' + repl + '</suggestion>'
        # (Matcher.replaceAll, the replacement is not quoted in Java)
        message = jregex.java_replace(_SUGGESTION_ELEM, elem, match.message)
        short_message = match.short_message
        if short_message is not None:
            short_message = jregex.java_replace(_SUGGESTION_ELEM, elem, short_message)
        new_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message, short_message)
        new_match.set_suggested_replacement(repl)
        return new_match


# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.UK) mapped to Dutch
_DAY_NAMES = {SUNDAY: 'zondag', MONDAY: 'maandag', TUESDAY: 'dinsdag', WEDNESDAY: 'woensdag',
              THURSDAY: 'donderdag', FRIDAY: 'vrijdag', SATURDAY: 'zaterdag'}
_DAYS = {'zo': SUNDAY, 'zondag': SUNDAY, 'ma': MONDAY, 'maandag': MONDAY, 'di': TUESDAY, 'dinsdag': TUESDAY,
         'wo': WEDNESDAY, 'woensdag': WEDNESDAY, 'do': THURSDAY, 'donderdag': THURSDAY, 'vr': FRIDAY,
         'vrijdag': FRIDAY, 'za': SATURDAY, 'zaterdag': SATURDAY}
_MONTH_PREFIXES = (('jan', 1), ('feb', 2), ('maa', 3), ('mrt', 3), ('mar', 3), ('apr', 4), ('mei', 5), ('jun', 6),
                   ('jul', 7), ('aug', 8), ('sep', 9), ('okt', 10), ('oct', 10), ('nov', 11), ('dec', 12))


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.nl.DateCheckFilter, the Dutch
    localization of AbstractDateCheckWithSuggestionsFilter."""

    def get_day_of_week(self, day_str):
        d = _DAYS.get(day_str.lower())
        if d is None:
            raise RuntimeError("Could not find day of week for '" + day_str + "'")
        return d

    def get_day_of_week_name(self, date):
        return _DAY_NAMES.get(date.day_of_week, '')

    def get_month(self, month_str):
        mon = month_str.lower()
        for prefix, month in _MONTH_PREFIXES:
            if mon.startswith(prefix):
                return month
        raise RuntimeError("Could not find month '" + month_str + "'")

    def get_error_message_wrong_year(self):
        return 'Deze datum is onjuist. Bedoelt u misschien "{currentYear}"?'


class DutchSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.nl.DutchSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of Dutch, see langtool.lang.nl.spelling)."""


class DutchNumberInWordFilter(AbstractNumberInWordFilter):
    """Port of org.languagetool.rules.nl.DutchNumberInWordFilter. Java asks
    a MorfologikDutchSpellerRule (for a new Dutch()) whether a word is
    misspelled (its misspelling check is ported, see
    langtool.lang.nl.spelling) and for its spelling suggestions (not ported:
    spell checking, so there are none)."""

    def is_misspelled(self, word):
        from ...api import get_language
        return get_language('nl').get_default_spelling_rule().is_misspelled(word)

    def get_suggestions(self, word):
        return []
