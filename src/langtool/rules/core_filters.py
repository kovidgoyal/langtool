"""Language independent rule filters from languagetool-core (the
<filter class="org.languagetool.rules.XXX"> classes)."""

import datetime
import math
import struct
import threading

import regex

from .. import jregex
from ..tools import (is_punctuation_or_symbol, is_all_uppercase, is_capitalized_word, is_whitespace,
                     uppercase_first_char, is_not_all_lowercase, is_numeric, trim_special_characters, is_junit_test,
                     preserve_case, is_letter, is_punctuation_mark, is_not_word_string,
                     java_equals_ignore_case, remove_diacritics, java_split)
from .filters import RuleFilter

_WS = regex.compile(r'\s+')
_OPENING_QUOTES = regex.compile('[«“"‘\'„¿¡]', regex.DOTALL)


def java_parse_int(s):
    """java.lang.Integer.parseInt: optional sign followed by digits."""
    if s is None:
        raise ValueError('null')
    t = s
    if t[:1] in ('+', '-'):
        t = t[1:]
    if not t or not all(c.isdigit() for c in t):
        raise ValueError('For input string: "%s"' % s)
    v = int(s)
    if not -2 ** 31 <= v < 2 ** 31:
        raise ValueError('For input string: "%s"' % s)
    return v


class AdaptSuggestionsFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule = match.rule
        lang = getattr(rule, 'language', None)
        if lang is None:
            return match
        adjusted = []
        for repl in match.suggested_replacements:
            match.set_original_error_str()
            adjusted.append(adapt_suggestion(lang, repl, match.original_error_str))
        match.set_suggested_replacements(adjusted)
        return match


def adapt_suggestion(lang, s, original_error_str):
    from .. import extensions
    f = extensions.lookup('adapt_suggestion', lang.short_code, lang.short_code)
    if f is not None:
        return f(lang, s, original_error_str)
    return s


class AddCommasFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        ss = self.get_optional('suggestSemicolon', arguments)
        suggest_semicolon = ss is not None and ss.lower() == 'true'
        sentence = match.sentence
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        pf = 1
        while pf < n and tokens[pf].start_pos < match.from_pos:
            pf += 1
        pt = pf
        while pt < n and tokens[pt].end_pos < match.to_pos:
            pt += 1
        before_ok = pf == 1 or is_punctuation_or_symbol(tokens[pf - 1].token) or is_capitalized_word(tokens[pf].token)
        after_ok = not (pt + 1 > n - 1) and is_punctuation_or_symbol(tokens[pt + 1].token) and \
            not (tokens[pt + 1].whitespace_before and _OPENING_QUOTES.fullmatch(tokens[pt + 1].token))
        if before_ok and after_ok:
            return None
        from .base import RuleMatch
        text = sentence.text
        nm = None
        if suggest_semicolon and tokens[pf - 1].token == ',' and not after_ok:
            nm = RuleMatch(match.rule, sentence, tokens[pf - 1].start_pos, tokens[pt].end_pos, match.message,
                           match.short_message)
            nm.add_suggested_replacement('; ' + text[match.from_pos:match.to_pos] + ',')
            nm.add_suggested_replacement(', ' + text[match.from_pos:match.to_pos] + ',')
        elif before_ok and not after_ok:
            nm = RuleMatch(match.rule, sentence, tokens[pt].start_pos, match.to_pos, match.message,
                           match.short_message)
            nm.set_suggested_replacement(tokens[pt].token + ',')
        elif not before_ok and after_ok:
            sp = tokens[pf].start_pos
            if tokens[pf].whitespace_before:
                sp -= 1
            nm = RuleMatch(match.rule, sentence, sp, tokens[pf].end_pos, match.message, match.short_message)
            nm.set_suggested_replacement(', ' + tokens[pf].token)
        else:
            sp = tokens[pf].start_pos
            if tokens[pf].whitespace_before:
                sp -= 1
            nm = RuleMatch(match.rule, sentence, sp, tokens[pt].end_pos, match.message, match.short_message)
            nm.set_suggested_replacement(', ' + text[match.from_pos:match.to_pos] + ',')
        return nm


class UnderlineSpacesFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        mode = self.get_required('underlineSpaces', arguments)
        sentence = match.sentence.text
        if mode in ('before', 'both'):
            if match.from_pos - 1 >= 0 and is_whitespace(sentence[match.from_pos - 1:match.from_pos]):
                match.set_offset_position(match.from_pos - 1, match.to_pos)
        if mode in ('after', 'both'):
            if match.to_pos + 1 < len(sentence) and is_whitespace(sentence[match.to_pos:match.to_pos + 1]):
                match.set_offset_position(match.from_pos, match.to_pos + 1)
        return match


class ApostropheTypeFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        word_from = self.get_required('wordFrom', arguments)
        has = self.get_required('hasTypographicalApostrophe', arguments).lower() == 'true'
        if word_from == 'marker':
            pos = 0
            while pos < len(pattern_tokens) and pattern_tokens[pos].start_pos < match.from_pos:
                pos += 1
            pos += 1
        else:
            pos = java_parse_int(word_from)
        if pos < 1 or pos > len(pattern_tokens):
            raise ValueError('ApostropheTypeFilter: Index out of bounds in %s, wordFrom: %d' % (
                match.rule.get_full_id(), pos))
        if has == pattern_tokens[pos - 1].typographic_apostrophe:
            return match
        return None


class WhitespaceCheckFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        ws = self.get_required('whitespaceChar', arguments)
        pos = java_parse_int(self.get_required('position', arguments))
        if pos < 1 or pos > len(pattern_tokens):
            raise ValueError('Wrong position in WhitespaceCheckFilter: %d' % pos)
        if pattern_tokens[pos - 1].whitespace_before_char != ws:
            return match
        return None


class DateRangeChecker(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        try:
            x = java_parse_int(arguments.get('x'))
            y = java_parse_int(arguments.get('y'))
        except ValueError:
            return None
        return match if x >= y else None


class ShortenedYearRangeChecker(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        try:
            x = java_parse_int(arguments.get('x'))
            prefix = arguments.get('x')[:2]
            y = java_parse_int(prefix + arguments.get('y'))
        except (ValueError, TypeError):
            return None
        return match if x >= y else None


# java.util.Calendar.SUNDAY .. SATURDAY
SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY = range(1, 8)


def _julian_day_number(year, month, day, gregorian):
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4
    if gregorian:
        return jdn - y // 100 + y // 400 - 32045
    return jdn - 32083


_GREGORIAN_CUTOVER = _julian_day_number(1582, 10, 15, True)


def _lenient_julian_day_number(year, month, day_of_month):
    """The day (Julian day number) of Calendar.set(year, month, dayOfMonth)
    on a lenient GregorianCalendar (month 0-based): months and days out of
    range roll over to the next or previous months and years. The Julian
    calendar is used before 1582-10-15, as by GregorianCalendar."""
    year += month // 12
    month %= 12
    gregorian = _julian_day_number(year, month + 1, 1, True) + day_of_month - 1 >= _GREGORIAN_CUTOVER
    return _julian_day_number(year, month + 1, 1, gregorian) + day_of_month - 1


class CalendarDate:
    """The fields of a java.util.GregorianCalendar (default cutover:
    Julian calendar before 1582-10-15) used by the date filters. month is
    0-based (Calendar.MONTH), day_of_week is Calendar.SUNDAY (1) to
    Calendar.SATURDAY (7)."""

    __slots__ = ('year', 'month', 'day_of_month', 'day_of_week')

    def __init__(self, year=None, month=None, day_of_month=None, day_of_week=None):
        self.year = year
        self.month = month
        self.day_of_month = day_of_month
        self.day_of_week = day_of_week

    @classmethod
    def of(cls, year, month, day_of_month):
        """Calendar.set(year, month, dayOfMonth, 0, 0, 0) on a non-lenient
        calendar followed by get(DAY_OF_WEEK): raises ValueError (Java:
        IllegalArgumentException) for invalid dates such as 32.8.2014, the
        29th of February of a non leap year or the days skipped by the
        Gregorian reform (1582-10-05 to 1582-10-14)."""
        if year < 1 or not 0 <= month <= 11 or not 1 <= day_of_month <= 31:
            raise ValueError('invalid date')
        m = month + 1
        if (year, m, day_of_month) >= (1582, 10, 15):
            gregorian = True
            leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        elif (year, m, day_of_month) <= (1582, 10, 4):
            gregorian = False
            leap = year % 4 == 0
        else:
            raise ValueError('invalid date')
        days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month]
        if day_of_month > days:
            raise ValueError('invalid date')
        dow = (_julian_day_number(year, m, day_of_month, gregorian) + 1) % 7 + 1
        return cls(year, month, day_of_month, dow)


_DAY_OF_MONTH_PATTERN = jregex.compile(r'(\d+).*')


class AbstractDateCheckFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractDateCheckFilter: accepts rule
    matches if a date doesn't match the accompanying weekday, e.g. if
    "Monday, 8 November 2003" isn't actually a Monday. Replaces {realDay}
    with the real day of the date in the rule's message, {day} with the
    claimed day from the text and {currentYear} with the current year.

    Subclasses implement get_day_of_week(str) (Sunday returns 1, Monday 2,
    ...), get_day_of_week_name(date) (Java: getDayOfWeek(Calendar), the
    localized name of date.day_of_week), get_month(str) (January returns 1)
    and optionally get_day_of_month(str). Java's getCalendar() only provides
    the calendar of the language's locale, which makes no difference for
    the fields used here (year, month, day of month, day of week), so it is
    not needed. Exceptions: ValueError (Java: IllegalArgumentException) is
    propagated, other errors (Java: RuntimeException, e.g. an unknown day
    name) discard the match."""

    def get_day_of_week(self, localized_week_day_string):
        raise NotImplementedError()

    def get_day_of_week_name(self, date):
        raise NotImplementedError()

    def get_day_of_month(self, localized_day_of_month):
        return 0

    def get_month(self, localized_month):
        raise NotImplementedError()

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        from .base import RuleMatch
        try:
            week_day = self.get_required('weekDay', arguments).replace('\u00ad', '')  # replace soft hyphen
            day_of_week_from_string = self.get_day_of_week(week_day)
            try:
                date_from_date = self._get_date(arguments)
            except ValueError as e:
                if isinstance(e, _InvalidDate):
                    # happens with 'dates' like '32.8.2014' - those should be caught by a different rule
                    return None
                raise
            if day_of_week_from_string != date_from_date.day_of_week:
                cal_from_date_string = CalendarDate(day_of_week=day_of_week_from_string)
                message = match.message.replace('{realDay}', self.get_day_of_week_name(date_from_date)) \
                    .replace('{day}', self.get_day_of_week_name(cal_from_date_string)) \
                    .replace('{currentYear}', str(datetime.date.today().year))
                rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message,
                                       match.short_message)
                rule_match.type = match.type
                rule_match.url = 'https://www.timeanddate.com/calendar/?year=%d' % date_from_date.year
                return rule_match
            return None
        except ValueError:
            raise
        except Exception:  # noqa: BLE001 -- Java: catch (RuntimeException e), logged and skipped
            # this can happen with some special characters which the regex matches but which the code
            # cannot map to days, e.g. German "Dıenstag" vs "Dienstag"
            return None

    def _get_date(self, args):
        year_arg = args.get('year')
        if year_arg is None and is_junit_test():
            # Hack for tests of date - weekday match with missing year: in production, we assume
            # the current year, for xml tests, we use weekdays of the year 2014
            year = 2014
        elif year_arg is None:
            # assume current year for rule DATUM_WOCHENTAG_OHNE_JAHR etc.
            year = datetime.date.today().year
        else:
            year = java_parse_int(year_arg)
        month = self._get_month_from_arguments(args)
        day_of_month = self._get_day_of_month_from_arguments(args)
        try:
            return CalendarDate.of(year, month, day_of_month)
        except ValueError as e:
            raise _InvalidDate(str(e))

    def _get_day_of_month_from_arguments(self, args):
        day_of_month_string = self.get_required('day', args)
        m = _DAY_OF_MONTH_PATTERN.fullmatch(day_of_month_string)
        if m:
            # The day of the month is a number, possibly with a suffix such as "22nd"
            return java_parse_int(m.group(1))
        # In some languages, the day of the month can also be written with letters rather than with
        # digits, so parse localized numbers.
        return self.get_day_of_month(day_of_month_string)

    def _get_month_from_arguments(self, args):
        month_str = self.get_required('month', args)
        if is_numeric(month_str):
            month = java_parse_int(month_str)
        else:
            month = self.get_month(trim_special_characters(month_str))
        return month - 1


class _InvalidDate(ValueError):
    """Calendar.get(DAY_OF_WEEK) failing on an invalid date (Java's
    IllegalArgumentException that is caught)"""


class AbstractFutureDateFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractFutureDateFilter: accepts rule
    matches if a date (arguments year, month, day) is in the future, used
    for the mismatch detection between verb tense and a given date.

    Subclasses implement get_month(str) (January returns 1) and optionally
    get_day_of_month(str). Java's getCalendar() only provides the calendar
    of the language's locale (a GregorianCalendar for all languages), which
    makes no difference here, so it is not needed.

    Java compares the date at 00:00:00 (with the milliseconds of the current
    time, which set(year, month, day, 0, 0, 0) doesn't reset) with the
    current time, i.e. a date is in the future if it is after today. In
    unit tests the current time is 2014-01-01 00:00:00.000, so that
    2014-01-01 itself is in the future, except when the check happens at a
    full second (ignored here). The comparison (Calendar.after) computes
    the time of a lenient clone of the calendar, so that the non-lenient
    calendar never rejects a date: invalid dates are normalized like
    32.8.2014 -> 1.9.2014 or day 0 -> the last day of the previous month
    (the IllegalArgumentException that Java catches never happens).
    Unparsable years and unknown months raise errors like in Java."""

    def get_day_of_month(self, localized_day_of_month):
        return 0

    def get_month(self, localized_month):
        raise NotImplementedError()

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        year = java_parse_int(self.get_required('year', arguments))
        month = self._get_month_from_arguments(arguments)
        day_of_month = self._get_day_of_month_from_arguments(arguments)
        date = _lenient_julian_day_number(year, month, day_of_month)
        if is_junit_test():
            if date >= _lenient_julian_day_number(2014, 0, 1):
                return match
            return None
        today = datetime.date.today()
        if date > _lenient_julian_day_number(today.year, today.month - 1, today.day):
            return match
        return None

    def _get_day_of_month_from_arguments(self, args):
        day_of_month_string = self.get_required('day', args)
        m = _DAY_OF_MONTH_PATTERN.fullmatch(day_of_month_string)
        if m:
            # The day of the month is a number, possibly with a suffix such as "22nd"
            return java_parse_int(m.group(1))
        # In some languages, the day of the month can also be written with letters rather than with
        # digits, so parse localized numbers.
        return self.get_day_of_month(day_of_month_string)

    def _get_month_from_arguments(self, args):
        month_str = self.get_required('month', args)
        if is_numeric(month_str):
            month = java_parse_int(month_str)
        else:
            month = self.get_month(month_str)
        return month - 1


_IS_PUNCTUATION = regex.compile(r'\p{P}')


class ConvertToSentenceCaseFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        first_done = False
        repl = []
        orig = []
        n = len(pattern_tokens)
        for i in range(pattern_token_pos, n):
            t = pattern_tokens[i]
            if t.start_pos < match.from_pos or t.end_pos > match.to_pos:
                continue
            nc = self._normalized_case(t)
            if i + 1 < n and pattern_tokens[i + 1].token == '.':
                if len(nc) == 1:
                    nc = nc.upper()
                elif nc == 'corp':
                    nc = 'Corp'
            ts = t.token
            cap = uppercase_first_char(nc)
            if not first_done and not _IS_PUNCTUATION.fullmatch(ts) and ts:
                first_done = True
                repl.append(cap)
                orig.append(ts)
            else:
                if t.whitespace_before:
                    repl.append(' ')
                    orig.append(' ')
                repl.append(nc)
                orig.append(ts)
        if ''.join(repl) == ''.join(orig):
            return None
        match.set_suggested_replacement(''.join(repl))
        return match

    def token_is_exception(self, s):
        return False

    def _normalized_case(self, atr):
        lower = atr.token.lower()
        if atr.typographic_apostrophe:
            lower = lower.replace("'", '’')
        if self.token_is_exception(lower):
            return lower
        cap = uppercase_first_char(lower)
        lemma_cap = lemma_lower = False
        for at in atr.readings:
            if at.has_no_pos_tag or at.lemma is None:
                return cap
            lemma = at.lemma.split(' ')[0]
            lemma_cap = lemma_cap or is_capitalized_word(lemma)
            lemma_lower = lemma_lower or not is_not_all_lowercase(lemma)
        if lemma_lower:
            return lower
        if lemma_cap:
            return cap
        return atr.token


class CheckPostagsInSuggestionFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = match.rule.language
        tagger = lang.tagger
        new = []
        tags = self.get_required('PostagsList', arguments).split(',')
        for repl in match.suggested_replacements:
            toks = _WS.split(repl)
            if len(toks) != len(tags) or not tags:
                raise ValueError('Mismatch between number of tokens and number of tags in rule %s' %
                                 match.rule.get_full_id())
            atrs = tagger.tag(toks)
            ok = True
            for i, t in enumerate(tags):
                ok = ok and atrs[i].matches_pos_tag_regex(t)
                if not ok:
                    break
            if ok:
                new.append(repl)
        if not new:
            return None
        match.set_suggested_replacements(new)
        return match


class PartialPosTagFilter(RuleFilter):
    """Abstract: subclasses implement tag(token) -> list of
    AnalyzedTokenReadings."""

    def tag(self, token):
        raise NotImplementedError()

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if not ('no' in args and 'regexp' in args and 'postag_regexp' in args):
            raise ValueError("Set 'no', 'regexp' and 'postag_regexp' for filter PartialPosTagFilter")
        pos = java_parse_int(args['no'])
        pattern = jregex.compile(args['regexp'])
        required = args['postag_regexp']
        negate_pos = 'negate_pos' in args
        two = 'two_groups_regexp' in args
        token = args.get('prefix', '') + pattern_tokens[pos - 1].token + args.get('suffix', '')
        if pattern.groups != 1 and not two:
            raise ValueError('Got %d groups for regex %r, expected 1' % (pattern.groups, args['regexp']))
        if pattern.groups != 2 and two:
            raise ValueError('Got %d groups for regex %r, expected 2' % (pattern.groups, args['regexp']))
        m = pattern.fullmatch(token)
        if m:
            partial = m.group(1) or ''
            if pattern.groups == 2:
                partial += m.group(2) or ''
            tags = self.tag(partial)
            if tags is not None and self._partial_tag_has_required_tag(tags, required, negate_pos):
                return match
            return None
        return None

    @staticmethod
    def _partial_tag_has_required_tag(tags, required, negate_pos):
        p = jregex.compile(required)
        count = 0
        for atr in tags:
            for at in atr.readings:
                if at.pos_tag is not None:
                    if negate_pos:
                        count += 1
                        if p.fullmatch(at.pos_tag):
                            return False
                    elif p.fullmatch(at.pos_tag):
                        return True
        return False if count == 0 else negate_pos


class IsEnglishWordFilter(RuleFilter):

    def __init__(self, language=None):
        super().__init__(language)
        self._tagger = None

    def _english_unavailable(self):
        """In Java, English (en-US) is not available in the unit tests of
        the other language modules (they don't depend on language-en), so
        that the filter rejects all matches there (the rule examples rely on
        that). Emulated for the tests (TestHackHelper.isJUnitTest) of a
        language other than English."""
        lang = self.language
        return lang is not None and lang.short_code != 'en' and is_junit_test()

    def _get_tagger(self):
        if self._tagger is None:
            from ..api import get_language
            try:
                self._tagger = get_language('en-US').tagger
            except Exception:
                self._tagger = False
        return self._tagger or None

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if self._english_unavailable():
            return None
        tagger = self._get_tagger()
        if tagger is None:
            return None
        forms = [pattern_tokens[self.get_skip_corrected_reference(token_positions, java_parse_int(p))].token
                 for p in self.get_required('formPositions', args).split(',')]
        ok = True
        postags = self.get_optional('postags', args)
        if postags is not None:
            pts = postags.split(',')
            if len(pts) != len(forms):
                raise ValueError('The number of forms and postags has to be the same in rule with filter '
                                 'IsEnglishWordFilter.')
            for f, p in zip(forms, pts):
                ok = ok and tagger.tag([f])[0].matches_pos_tag_regex(p)
        else:
            for f in forms:
                ok = ok and tagger.tag([f])[0].is_tagged()
        return match if ok else None


class SuppressIfAnyRuleMatchesFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule_ids = self.get_required('ruleIDs', arguments).split(',')
        fast_only = self.get_optional('fastOnly', arguments, 'false') == 'true'
        lang = match.rule.language
        lt = _default_tool(lang)
        sentence = match.sentence.text
        for repl in match.suggested_replacements:
            partial = self._replace_token(match, repl, lang)
            if partial is not None:
                if self._any_rule_matches(lt, rule_ids, partial, match):
                    return None
                if fast_only:
                    continue
            new_sentence = sentence[:match.from_pos] + repl + sentence[match.to_pos:]
            analyzed = lt.analyze_text(new_sentence)[0]
            if self._any_rule_matches(lt, rule_ids, analyzed, match):
                return None
        return match

    @staticmethod
    def _any_rule_matches(lt, rule_ids, analyzed, match):
        # (= the rules of lt.get_all_active_rules() with the ids, in order; the cheap tests first)
        for r in lt.get_all_rules():
            if r.get_id() in rule_ids and not r.is_text_level_rule() and not lt.ignore_rule(r):
                for m in r.match(analyzed):
                    if (match.from_pos <= m.to_pos <= match.to_pos) or (m.from_pos <= match.to_pos <= m.to_pos):
                        return True
        return False

    @staticmethod
    def _replace_token(match, repl, lang):
        from ..analysis import AnalyzedTokenReadings, AnalyzedSentence
        f, t = match.from_pos, match.to_pos
        if len(repl) != t - f or ' ' in repl:
            return None
        s = match.sentence
        tokens = s.tokens
        idx = -1
        for i, tok in enumerate(tokens):
            if not tok.is_whitespace and tok.start_pos == f:
                idx = i
                break
        if idx < 0:
            return None
        tagged = lang.tagger.tag([repl])
        if len(tagged) != 1:
            return None
        new_tokens = list(tokens)
        new_tokens[idx] = AnalyzedTokenReadings.from_old(tokens[idx], tagged[0].readings,
                                                         'SuppressIfAnyRuleMatchesFilter')
        new_pre = list(s.pre_disambig_tokens)
        new_pre[idx] = new_tokens[idx]
        return AnalyzedSentence(new_tokens, new_pre)


class AbstractAdvancedSynthesizerFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractAdvancedSynthesizerFilter:
    synthesize suggestions using the lemma from one token (lemmaFrom) and
    the POS tag from another one (postagFrom). The lemmaSelect and
    postagSelect arguments are required to choose one among several
    possible readings. Subclasses may override is_suggestion_exception()
    and get_new_lemma()."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        postag_select = self.get_required('postagSelect', arguments)
        lemma_select = self.get_required('lemmaSelect', arguments)
        postag_from_str = self.get_required('postagFrom', arguments)
        lemma_from_str = self.get_required('lemmaFrom', arguments)
        new_lemma = self.get_optional('newLemma', arguments, '')

        postag_from = self._position(postag_from_str, pattern_tokens, match)
        lemma_from = self._position(lemma_from_str, pattern_tokens, match)

        postag_replace = self.get_optional('postagReplace', arguments)

        lemma_token = self._get_analyzed_token(pattern_tokens[lemma_from - 1], lemma_select)
        desired_lemma = lemma_token.lemma
        original_postag = lemma_token.pos_tag
        desired_postag = self._get_analyzed_token(pattern_tokens[postag_from - 1], postag_select).pos_tag
        if new_lemma:
            if new_lemma.startswith('_'):
                desired_lemma = self.get_new_lemma(desired_lemma, new_lemma)
            else:
                desired_lemma = new_lemma
        if desired_lemma is None:
            return None

        if desired_postag is None:
            raise ValueError("AdvancedSynthesizerFilter: undefined POS tag for rule %s with POS regex '%s' for "
                             "token: %s" % (match.rule.get_full_id(), postag_select, pattern_tokens[postag_from - 1]))

        if postag_replace is not None:
            desired_postag = self.get_composite_postag(lemma_select, postag_select, original_postag, desired_postag,
                                                       postag_replace)

        # take capitalization from the lemma (?)
        is_word_capitalized = is_capitalized_word(pattern_tokens[lemma_from - 1].token)
        is_word_allupper = is_all_uppercase(pattern_tokens[lemma_from - 1].token)
        from ..analysis import AnalyzedToken
        token = AnalyzedToken('', desired_postag, desired_lemma)
        language = self.language if self.language is not None else match.rule.language
        replacements = language.synthesizer.synthesize(token, desired_postag, True)
        if replacements:
            from .base import RuleMatch
            new_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                                  match.short_message)
            new_match.type = match.type
            replacements_list = []
            suggestion_used = False
            for r in match.suggested_replacements:
                for nr in replacements:
                    if self.is_suggestion_exception(nr, desired_postag):
                        continue
                    if '{suggestion}' in r or '{Suggestion}' in r or '{SUGGESTION}' in r:
                        suggestion_used = True
                    if is_word_capitalized:
                        nr = uppercase_first_char(nr)
                    if is_word_allupper:
                        nr = nr.upper()
                    complete = r.replace('{suggestion}', nr)
                    complete = complete.replace('{Suggestion}', uppercase_first_char(nr))
                    complete = complete.replace('{SUGGESTION}', nr.upper())
                    if complete not in replacements_list:
                        replacements_list.append(complete)
            if not suggestion_used:
                replacements_list.extend(replacements)
            new_match.set_suggested_replacements([adapt_suggestion(language, r, '') for r in replacements_list])
            return new_match
        return match

    @staticmethod
    def _position(from_str, pattern_tokens, match):
        if from_str.startswith('marker'):
            i = 0
            while i < len(pattern_tokens) and pattern_tokens[i].start_pos < match.from_pos:
                i += 1
            i += 1
            if len(from_str) > 6:
                i += java_parse_int(from_str.replace('marker', ''))
        else:
            i = java_parse_int(from_str)
        if i < 1 or i > len(pattern_tokens):
            raise ValueError('AdvancedSynthesizerFilter: Index out of bounds in %s, value: %s' % (
                match.rule.get_full_id(), from_str))
        return i

    def get_composite_postag(self, lemma_select, postag_select, original_postag, desired_postag, postag_replace):
        a_pattern = jregex.compile(lemma_select)
        b_pattern = jregex.compile(postag_select)
        a_matcher = a_pattern.fullmatch(original_postag)
        b_matcher = b_pattern.fullmatch(desired_postag)
        result = postag_replace
        if a_matcher and b_matcher:
            for i in range(1, a_pattern.groups + 1):
                group_str = a_matcher.group(i)
                if group_str is not None:
                    result = result.replace('\\a%d' % i, group_str)
            for i in range(1, b_pattern.groups + 1):
                group_str = b_matcher.group(i)
                if group_str is not None:
                    result = result.replace('\\b%d' % i, group_str)
        return result

    def is_suggestion_exception(self, token, desired_postag):
        return False

    @staticmethod
    def _get_analyzed_token(atr, regexp):
        pattern = jregex.compile(regexp)
        for analyzed_token in atr.readings:
            pos_tag = analyzed_token.pos_tag
            if pos_tag is None:
                pos_tag = 'UNKNOWN'
            if pattern.fullmatch(pos_tag):
                return analyzed_token
        # Return the first one. Something is wrong, anyway
        return atr.readings[0]

    def get_new_lemma(self, word, new_lemma):
        return None


class AbstractDateCheckWithSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractDateCheckWithSuggestionsFilter:
    accepts rule matches if a date doesn't match the accompanying weekday,
    e.g. if "Monday, 8 November 2003" isn't actually a Monday, and suggests
    the corrected day of the week, the corrected day of the month, or (if
    the date fits the weekday in the current year) the current year.
    Replaces {realDay} with the real day of the date in the rule's message,
    {day} with the claimed day from the text and {currentYear} with the
    current year. The arguments are token positions: weekDay, day, month,
    year (optional), or date (optional, a yyyy-mm-dd token).

    Subclasses implement get_day_of_week(str) (Sunday returns 1, Monday 2,
    ...), get_day_of_week_name(date) (Java: getDayOfWeek(Calendar)),
    get_month(str) (January returns 1), get_error_message_wrong_year() and
    optionally get_day_of_month(str), get_day_str_like_original() and
    adjust_suggestion(). Java's getCalendar() (a Gregorian calendar in all
    languages) is not needed. Exceptions: ValueError (Java:
    IllegalArgumentException, e.g. from Integer.parseInt) is propagated,
    other errors (Java: RuntimeException, e.g. an unknown day name) discard
    the match."""

    def get_day_of_week(self, localized_week_day_string):
        raise NotImplementedError()

    def get_day_of_week_name(self, date):
        raise NotImplementedError()

    def get_day_of_month(self, localized_day_of_month):
        return 0

    def get_month(self, localized_month):
        raise NotImplementedError()

    def get_error_message_wrong_year(self):
        raise NotImplementedError()

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        from .base import RuleMatch
        try:
            day_of_week_pos = self.get_skip_corrected_reference(
                token_positions, java_parse_int(self.get_required('weekDay', args)))
            day_of_week_str = pattern_tokens[day_of_week_pos].token.replace('­', '')  # replace soft hyphen
            is_full_date_token = False
            full_date_pos = self.get_skip_corrected_reference(
                token_positions, java_parse_int(self.get_optional('date', args, '-1')))  # format yyyy-mm-dd
            if full_date_pos > -1:
                parts = pattern_tokens[full_date_pos].token.split('-')
                is_full_date_token = True
                day_pos = month_pos = year_pos = full_date_pos
                day_str = parts[2]
                month_str = parts[1]
                year_str = parts[0]
            else:
                day_pos = self.get_skip_corrected_reference(token_positions,
                                                            java_parse_int(self.get_required('day', args)))
                month_pos = self.get_skip_corrected_reference(token_positions,
                                                              java_parse_int(self.get_required('month', args)))
                year_pos = self.get_skip_corrected_reference(token_positions,
                                                             java_parse_int(self.get_optional('year', args, '-1')))
                day_str = pattern_tokens[day_pos].token
                month_str = pattern_tokens[month_pos].token
                year_str = pattern_tokens[year_pos].token if year_pos > -1 else None
            day_of_week_from_string = self.get_day_of_week(day_of_week_str)
            day = self._get_day_of_month_from_str(day_str)
            month = self._get_month_from_str(month_str)
            year = self._get_year_from_str(year_str)
            day_of_week_from_date = _day_of_week_or_minus_one(year, month, day)
            if day_of_week_from_date == -1:
                return None
            if day_of_week_from_string == day_of_week_from_date:
                return None
            date_from_date = CalendarDate.of(year, month, day)
            cal_from_date_string = CalendarDate(day_of_week=day_of_week_from_string)
            # suggest changing the year (to current year)
            current_year = self._get_year_from_str(None)
            if day_of_week_from_string == _day_of_week_or_minus_one(current_year, month, day):
                message = self.get_error_message_wrong_year().replace('{currentYear}', str(current_year))
                rule_match = RuleMatch(match.rule, match.sentence, pattern_tokens[year_pos].start_pos,
                                       pattern_tokens[year_pos].end_pos, message, match.short_message)
                rule_match.type = match.type
                rule_match.url = 'https://www.timeanddate.com/calendar/?year=%d' % current_year
                if is_full_date_token:
                    rule_match.set_suggested_replacement('%d-%s-%s' % (current_year, month_str, day_str))
                else:
                    rule_match.set_suggested_replacement(str(current_year))
                return rule_match
            # suggest changing day of week or day of month
            message = match.message.replace('{realDay}', self.get_day_of_week_name(date_from_date)) \
                .replace('{day}', self.get_day_of_week_name(cal_from_date_string)) \
                .replace('{currentYear}', str(datetime.date.today().year))
            if day_of_week_pos < day_pos:
                start_index, end_index = day_of_week_pos, day_pos
            else:
                start_index, end_index = day_pos, day_of_week_pos
            rule_match = RuleMatch(match.rule, match.sentence, pattern_tokens[start_index].start_pos,
                                   pattern_tokens[end_index].end_pos, message, match.short_message)
            rule_match.type = match.type
            rule_match.url = 'https://www.timeanddate.com/calendar/?year=%d' % date_from_date.year
            # suggest changing day of week
            suggestion = []
            for j in range(start_index, end_index + 1):
                if j > start_index and pattern_tokens[j].whitespace_before:
                    suggestion.append(' ')
                if j == day_of_week_pos:
                    suggestion.append(preserve_case(self.get_day_of_week_name(date_from_date), day_of_week_str))
                else:
                    suggestion.append(pattern_tokens[j].token)
            if ''.join(suggestion):
                rule_match.set_suggested_replacement(self.adjust_suggestion(''.join(suggestion)))
            # suggest changing day of month
            corrected_day_of_month = self._find_new_day_of_month(day, month, year, day_of_week_from_string)
            if corrected_day_of_month:
                suggestion = []
                for j in range(start_index, end_index + 1):
                    if j > start_index and pattern_tokens[j].whitespace_before:
                        suggestion.append(' ')
                    if j == day_pos:
                        if is_full_date_token:
                            suggestion.append(year_str + '-' + month_str + '-' + corrected_day_of_month)
                        else:
                            suggestion.append(self.get_day_str_like_original(corrected_day_of_month, day_str))
                    else:
                        suggestion.append(pattern_tokens[j].token)
                if ''.join(suggestion):
                    rule_match.add_suggested_replacement(self.adjust_suggestion(''.join(suggestion)))
            return rule_match
        except ValueError:
            raise
        except Exception:  # noqa: BLE001 -- Java: catch (RuntimeException e), skipped
            # this can happen with some special characters which the regex matches but which the code
            # cannot map to days, e.g. German "Dıenstag" vs "Dienstag"
            return None

    def _find_new_day_of_month(self, day, month, year, day_of_week_from_string):
        difference = 1
        while difference < 7:
            if day - difference > 0:
                if day_of_week_from_string == _day_of_week_or_minus_one(year, month, day - difference):
                    return str(day - difference)
            if day + difference < 32:
                if day_of_week_from_string == _day_of_week_or_minus_one(year, month, day + difference):
                    return str(day + difference)
            difference += 1
        return ''

    @staticmethod
    def _get_year_from_str(year_arg):
        if year_arg is None and is_junit_test():
            # Hack for tests of date - weekday match with missing year: in production, we assume
            # the current year, for xml tests, we use weekdays of the year 2014
            return 2014
        if year_arg is None:
            # assume current year for rule DATUM_WOCHENTAG_OHNE_JAHR etc.
            return datetime.date.today().year
        return java_parse_int(year_arg)

    def _get_day_of_month_from_str(self, day_of_month_string):
        m = _DAY_OF_MONTH_PATTERN.fullmatch(day_of_month_string)
        if m:
            # The day of the month is a number, possibly with a suffix such as "22nd"
            return java_parse_int(m.group(1))
        # In some languages, the day of the month can also be written with letters rather than with
        # digits, so parse localized numbers.
        return self.get_day_of_month(day_of_month_string)

    def _get_month_from_str(self, month_str):
        if is_numeric(month_str):
            month = java_parse_int(month_str)
        else:
            month = self.get_month(trim_special_characters(month_str))
        return month - 1

    def get_day_str_like_original(self, day, original):
        return day

    def adjust_suggestion(self, sugg):
        """typographical adjustments needed in some languages"""
        return sugg


def _day_of_week_or_minus_one(year, month, day_of_month):
    """getDate(dayOfMonth, month, year).get(Calendar.DAY_OF_WEEK) on a
    non-lenient calendar, -1 for invalid dates like '32.8.2014' (Java's
    IllegalArgumentException, caught in getDayOfWeekFromDate)"""
    try:
        return CalendarDate.of(year, month, day_of_month).day_of_week
    except ValueError:
        return -1


def is_misspelled_with_default_speller(s, language):
    """isMisspelled(String, Language) of AbstractSuppressMisspelledSuggestionsFilter
    and MultitokenSpellerFilter: whether one of the tokens of s is
    misspelled according to the language's default spelling rule (never
    without a spelling rule)."""
    speller_rule = language.get_default_spelling_rule()
    if speller_rule is None:
        return False
    for token in language.word_tokenizer.tokenize(s):
        if speller_rule.is_misspelled(token):
            return True
    return False


class AbstractSuppressMisspelledSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractSuppressMisspelledSuggestionsFilter:
    removes the suggestions that are misspelled (according to the
    misspelling check of the language's default spelling rule, see
    langtool.spelling; without one, as in Java, no suggestion is
    misspelled), and
    the suggestions whose POS tags match SuppressPostag or don't match
    FilterPostag (optional arguments). Without suggestions left, the match
    is discarded unless suppressMatch is "false"."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule_match = match
        language = match.rule.language
        tagger = language.tagger
        replacements = match.suggested_replacements
        new_replacements = []
        suppress_match = self.get_required('suppressMatch', arguments)
        suppress_postag = self.get_optional('SuppressPostag', arguments)
        filter_postag = self.get_optional('FilterPostag', arguments)
        check_postag = tagger is not None and (suppress_postag is not None or filter_postag is not None)
        for replacement in replacements:
            if not self.is_misspelled(replacement, language):
                add_replacement = True
                # Tag only replacements that are not misspelled (the postag is only needed for them).
                if check_postag:
                    atr = tagger.tag([replacement])[0]
                    if suppress_postag is not None and atr.matches_pos_tag_regex(suppress_postag):
                        add_replacement = False
                    if filter_postag is not None and not atr.matches_pos_tag_regex(filter_postag):
                        add_replacement = False
                if add_replacement:
                    new_replacements.append(replacement)
        b_suppress_match = True
        if suppress_match is not None and suppress_match.lower() == 'false':
            b_suppress_match = False
        if not new_replacements and b_suppress_match:
            return None
        rule_match.set_suggested_replacements(new_replacements)
        return rule_match

    def is_misspelled(self, s, language):
        return is_misspelled_with_default_speller(s, language)


_TYPO_PATTERN = jregex.compile('[0-9]')


class AbstractNumberInWordFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractNumberInWordFilter: suggests
    the word (argument 'word') with 0 replaced by o, or without digits, if
    these are spelled correctly, otherwise the spelling suggestions for the
    word without digits. Subclasses implement is_misspelled(word) and
    get_suggestions(word)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        word = arguments.get('word')
        word_replacing_zero_o = word.replace('0', 'o')
        word_without_number_character = jregex.java_replace(_TYPO_PATTERN, '', word)
        replacements = []
        if not self.is_misspelled(word_replacing_zero_o) and word != word_replacing_zero_o:
            replacements.append(word_replacing_zero_o)
        if not self.is_misspelled(word_without_number_character):
            replacements.append(word_without_number_character)
        if not replacements:
            replacements.extend(self.get_suggestions(word_without_number_character))
        if replacements:
            rule_match = match.copy()  # new RuleMatch(match)
            rule_match.set_suggested_replacements(replacements)
            return rule_match
        return None

    def is_misspelled(self, word):
        raise NotImplementedError()

    def get_suggestions(self, word):
        raise NotImplementedError()


class EditDistance:
    """Port of org.languagetool.rules.spelling.symspell.implementation.EditDistance
    (only the Damerau algorithm exists): the optimal string alignment
    (restricted Damerau-Levenshtein) distance to a base string, with a
    maximum distance. The work arrays are reused between comparisons, as in
    Java."""

    def __init__(self, base_string):
        self.base_string = base_string
        if not base_string:
            self.base_string = None
            return
        self.v0 = [0] * len(base_string)
        self.v2 = [0] * len(base_string)  # stores one level further back (offset by +1 position)

    def compare(self, string2, max_distance):
        """The edit distance (or -1 if max_distance is exceeded)."""
        return self.damerau_levenshtein_distance(string2, max_distance)

    def damerau_levenshtein_distance(self, string2, max_distance):
        base = self.base_string
        if base is None:
            return 0 if string2 is None else len(string2)
        if not string2:
            return len(base)
        if max_distance == 0:
            return 0 if base == string2 else -1
        # if strings of different lengths, ensure shorter string is in string1
        if len(base) > len(string2):
            string1 = string2
            string2 = base
        else:
            string1 = base
        s_len = len(string1)  # this is also the minimum length of the two strings
        t_len = len(string2)
        # suffix common to both strings can be ignored
        while s_len > 0 and string1[s_len - 1] == string2[t_len - 1]:
            s_len -= 1
            t_len -= 1
        start = 0
        if string1[0] == string2[0] or s_len == 0:
            # prefix common to both strings can be ignored
            while start < s_len and string1[start] == string2[start]:
                start += 1
            s_len -= start  # length of the part excluding common prefix and suffix
            t_len -= start
            # if all of shorter string matches prefix and/or suffix of longer string, then
            # edit distance is just the delete of additional characters present in longer string
            if s_len == 0:
                return t_len
            string2 = string2[start:start + t_len]
        len_diff = t_len - s_len
        if max_distance < 0 or max_distance > t_len:
            max_distance = t_len
        elif len_diff > max_distance:
            return -1
        if t_len > len(self.v0):
            self.v0 = [0] * t_len
            self.v2 = [0] * t_len
        else:
            for i in range(t_len):
                self.v2[i] = 0
        v0 = self.v0
        v2 = self.v2
        for j in range(max_distance):
            v0[j] = j + 1
        for j in range(max_distance, t_len):
            v0[j] = max_distance + 1
        j_start_offset = max_distance - (t_len - s_len)
        have_max = max_distance < t_len
        j_start = 0
        j_end = max_distance
        s_char = string1[0]
        current = 0
        for i in range(s_len):
            prevs_char = s_char
            s_char = string1[start + i]
            t_char = string2[0]
            left = i
            current = left + 1
            next_trans_cost = 0
            # no need to look beyond window of lower right diagonal - maxDistance cells (lower right diag is
            # i - lenDiff) and the upper left diagonal + maxDistance cells (upper left is i)
            if i > j_start_offset:
                j_start += 1
            if j_end < t_len:
                j_end += 1
            for j in range(j_start, j_end):
                above = current
                this_trans_cost = next_trans_cost
                next_trans_cost = v2[j]
                v2[j] = current = left  # cost of diagonal (substitution)
                left = v0[j]  # left now equals current cost (which will be diagonal at next iteration)
                prevt_char = t_char
                t_char = string2[j]
                if s_char != t_char:
                    if left < current:
                        current = left  # insertion
                    if above < current:
                        current = above  # deletion
                    current += 1
                    if i != 0 and j != 0 and s_char == prevt_char and prevs_char == t_char:
                        this_trans_cost += 1
                        if this_trans_cost < current:
                            current = this_trans_cost  # transposition
                v0[j] = current
            if have_max and v0[i + len_diff] > max_distance:
                return -1
        return current if current <= max_distance else -1


class _StringComparator:
    """AbstractFindSuggestionsFilter.StringComparator: orders strings by
    their Damerau edit distance to a word (at most 4, larger distances
    count as 8)."""

    max_distance = 4

    def __init__(self, word):
        self.distance = EditDistance(word)

    def key(self, s):
        d = self.distance.compare(s, self.max_distance)
        return 2 * self.max_distance if d < 0 else d


class AbstractFindSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractFindSuggestionsFilter: finds
    suggestions for the token wordFrom (a position, or "inmarker" for the
    marked text) among its spelling suggestions that match desiredPostag
    (suggestions matching priorityPostag first, suggestions matching
    removeSuggestionsRegexp removed); without any, the suggestions are
    synthesized with desiredPostag from the lemmas of the spelling
    suggestions (if get_synthesizer() gives a synthesizer), ordered by edit
    distance. The suggestions replace {suggestion}/{Suggestion}/{SUGGESTION}
    in the rule's suggestions. Mode:diacritics only accepts suggestions that
    differ in diacritics, suppressMatch:true discards matches without
    suggestions.

    Subclasses implement get_tagger() and get_spelling_suggestions(atr), and
    may override get_synthesizer(), is_suggestion_exception(atr),
    clean_suggestion(s) and pre_process_wrong_word(word). Filters are
    singletons per class in Java (RuleFilterCreator), so the cache of
    spelling suggestions is shared per class here too."""

    MAX_SUGGESTIONS = 10
    _CACHE_SIZE = 10000

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._spelling_suggestions_cache = {}
        cls._spelling_suggestions_lock = threading.Lock()

    _spelling_suggestions_cache = {}
    _spelling_suggestions_lock = threading.Lock()

    def get_tagger(self):
        raise NotImplementedError()

    def get_spelling_suggestions(self, atr):
        raise NotImplementedError()

    def get_synthesizer(self):
        return None

    def is_suggestion_exception(self, analyzed_suggestion):
        return False

    def clean_suggestion(self, s):
        return s

    def pre_process_wrong_word(self, word):
        return word.replace(' ', '')

    def get_spelling_suggestions_cached(self, atr):
        """Spell suggestions only depend on the token and whether it is
        tagged, so they are cached by that key."""
        key = (atr.token, atr.is_tagged())
        cache = type(self)._spelling_suggestions_cache
        cached = cache.get(key)
        if cached is None:
            cached = list(self.get_spelling_suggestions(atr))
            with type(self)._spelling_suggestions_lock:
                if len(cache) >= self._CACHE_SIZE:
                    cache.clear()
                cache[key] = cached
        return cached

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        from ..analysis import AnalyzedToken, AnalyzedTokenReadings
        from .base import RuleMatch
        replacements = []
        replacements2 = []
        word_from = self.get_required('wordFrom', arguments)
        desired_postag = self.get_required('desiredPostag', arguments)
        priority_postag = self.get_optional('priorityPostag', arguments)
        remove_suggestions_regexp = self.get_optional('removeSuggestionsRegexp', arguments)
        # suppress match if there are no suggestions
        b_suppress_match = self.get_optional('suppressMatch', arguments, 'false').lower() == 'true'
        # diacriticsMode: return only changes in diacritics. If there is none, the match is removed.
        mode = self.get_optional('Mode', arguments)
        diacritics_mode = mode is not None and mode == 'diacritics'
        generate_suggestions = True
        regexp_pattern = None
        synth = self.get_synthesizer()
        used_lemmas = []
        string_comparator = _StringComparator('')
        desired = jregex.compile(desired_postag)
        priority = jregex.compile(priority_postag) if priority_postag is not None else None
        if word_from is not None and desired_postag is not None:
            if word_from == 'inmarker':
                match.set_original_error_str()
                atr_word = AnalyzedTokenReadings(AnalyzedToken(self.pre_process_wrong_word(match.original_error_str),
                                                               '', ''))
            else:
                atr_word = pattern_tokens[self.get_position(word_from, pattern_tokens, match)]
            string_comparator = _StringComparator(atr_word.token)
            is_word_capitalized = is_capitalized_word(atr_word.token)
            is_word_allupper = is_all_uppercase(atr_word.token)
            # Check if the original token (before disambiguation) meets the requirements
            for atr in self.get_tagger().tag([atr_word.token]):
                if atr.matches_pos_tag_regex(desired):
                    if diacritics_mode:
                        return None
            if generate_suggestions:
                if remove_suggestions_regexp is not None:
                    regexp_pattern = jregex.compile(remove_suggestions_regexp)
                suggestions = self.get_spelling_suggestions_cached(atr_word)
                used_priority_postag_pos = 0
                for suggestion in suggestions:
                    # TODO: do not tag capitalized words with tags for lower case
                    analyzed_suggestions = self.get_tagger().tag([self.clean_suggestion(suggestion)])
                    for analyzed_suggestion in analyzed_suggestions:
                        if self.is_suggestion_exception(analyzed_suggestion):
                            continue
                        if len(replacements) >= 2 * self.MAX_SUGGESTIONS:
                            break
                        used = False
                        if suggestion != atr_word.token and analyzed_suggestion.matches_pos_tag_regex(desired):
                            if (suggestion not in replacements and suggestion.lower() not in replacements
                                    and (not diacritics_mode
                                         or self._equal_without_diacritics(suggestion, atr_word.token))):
                                if regexp_pattern is None or not regexp_pattern.fullmatch(suggestion):
                                    replacement = suggestion
                                    if is_word_allupper:
                                        replacement = replacement.upper()
                                    if is_word_capitalized:
                                        replacement = uppercase_first_char(replacement)
                                    if priority is not None and analyzed_suggestion.matches_pos_tag_regex(priority):
                                        replacements.insert(used_priority_postag_pos, replacement)
                                        used_priority_postag_pos += 1
                                        used = True
                                    else:
                                        replacements.append(replacement)
                                        used = True
                        # try with the synthesizer
                        if not used and synth is not None:
                            synthesized_suggestions = []
                            for at in analyzed_suggestion:
                                if at.lemma in used_lemmas:
                                    continue
                                synthesized_array = synth.synthesize(at, desired_postag, True) or []
                                used_lemmas.append(at.lemma)
                                for synthesized_suggestion in synthesized_array:
                                    if synthesized_suggestion not in synthesized_suggestions:
                                        synthesized_suggestions.append(synthesized_suggestion)
                                for replacement in synthesized_suggestions:
                                    if is_word_allupper:
                                        replacement = replacement.upper()
                                    if is_word_capitalized:
                                        replacement = uppercase_first_char(replacement)
                                    replacements2.append(replacement)
        match_contains_some_finished_suggestion = any('{suggestion}' not in k.lower()
                                                      for k in match.suggested_replacements)
        if diacritics_mode and not replacements and not match_contains_some_finished_suggestion:
            return None
        if not replacements and not replacements2 and b_suppress_match \
                and not match_contains_some_finished_suggestion:
            return None
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                               match.short_message)
        rule_match.type = match.type
        definitive_replacements = []
        replacements_used = False
        if generate_suggestions:
            for s in match.suggested_replacements:
                if '{suggestion}' in s or '{Suggestion}' in s or '{SUGGESTION}' in s:
                    replacements_used = True
                    for s2 in replacements:
                        if len(definitive_replacements) >= self.MAX_SUGGESTIONS:
                            break
                        if '{suggestion}' in s:
                            if s2 not in definitive_replacements:
                                definitive_replacements.append(s.replace('{suggestion}', s2))
                        elif '{Suggestion}' in s:
                            if uppercase_first_char(s2) not in definitive_replacements:
                                definitive_replacements.append(s.replace('{Suggestion}', uppercase_first_char(s2)))
                        else:
                            if s2.upper() not in definitive_replacements:
                                definitive_replacements.append(s.replace('{SUGGESTION}', s2.upper()))
                else:
                    if s not in definitive_replacements:
                        definitive_replacements.append(s)
            if not replacements_used:
                if not replacements:
                    replacements2.sort(key=string_comparator.key)  # stable, like Collections.sort
                    for replacement in replacements2:
                        if replacement not in replacements and replacement not in definitive_replacements:
                            replacements.append(replacement)
                for replacement in replacements:
                    if len(definitive_replacements) >= self.MAX_SUGGESTIONS:
                        break
                    if replacement not in definitive_replacements:
                        definitive_replacements.append(replacement)
        if match.original_error_str in definitive_replacements:
            definitive_replacements.remove(match.original_error_str)
        if definitive_replacements:
            rule_match.set_suggested_replacements(list(dict.fromkeys(definitive_replacements)))
        return rule_match

    @staticmethod
    def _equal_without_diacritics(s, t):
        return java_equals_ignore_case(remove_diacritics(s), remove_diacritics(t))


class AbstractNewYearDateFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractNewYearDateFilter: accepts
    rule matches if we are in the first days of a new year (= it is
    January) and the user may have entered a date (arguments year, month,
    day) with the old year (but not a date in December). Replaces {year}
    and {realYear} in the message. In unit tests it is always January 2014
    (TestHackHelper.isJUnitTest()).

    Subclasses implement get_month(str) (January returns 1) and optionally
    get_day_of_month(str). Java's getCalendar() (the calendar of the
    language's locale) is only used for the current date and to validate
    the date, which a GregorianCalendar does the same way for all
    languages, so it is not needed. Invalid dates (Java: the
    IllegalArgumentException of the non-lenient calendar) discard the
    match; unparsable years and unknown months raise errors like in
    Java."""

    def is_january(self):
        if is_junit_test():
            return True
        return datetime.date.today().month == 1

    def get_current_year(self):
        if is_junit_test():
            return 2014
        return datetime.date.today().year

    def get_month(self, localized_month):
        raise NotImplementedError()

    def get_day_of_month(self, localized_day_of_month):
        return 0

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        from .base import RuleMatch
        year = java_parse_int(self.get_required('year', args))
        month = self._get_month_from_arguments(args)
        day_of_month = self._get_day_of_month_from_arguments(args)
        try:
            date_from_text = CalendarDate.of(year, month, day_of_month)
        except ValueError:
            return None  # date is not valid; another rule is responsible
        month_from_text = date_from_text.month
        year_from_text = date_from_text.year
        current_year = self.get_current_year()
        if self.is_january() and month_from_text != 11 and year_from_text + 1 == current_year:  # 11: December
            message = match.message.replace('{year}', str(year_from_text)).replace('{realYear}', str(current_year))
            rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message,
                                   match.short_message)
            rule_match.type = match.type
            return rule_match
        return None

    def _get_day_of_month_from_arguments(self, args):
        day_of_month_string = self.get_required('day', args).replace('\u00ad', '')  # replace soft hyphen
        m = _DAY_OF_MONTH_PATTERN.fullmatch(day_of_month_string)
        if m:
            # The day of the month is a number, possibly with a suffix such as "22nd"
            return java_parse_int(m.group(1))
        # In some languages, the day of the month can also be written with letters rather than with
        # digits, so parse localized numbers.
        return self.get_day_of_month(day_of_month_string)

    def _get_month_from_arguments(self, args):
        month_str = self.get_required('month', args).replace('\u00ad', '')  # replace soft hyphen
        if is_numeric(month_str):
            month = java_parse_int(month_str)
        else:
            month = self.get_month(month_str)
        return month - 1


class YMDDateHelper:
    """Port of org.languagetool.rules.YMDDateHelper, used by the
    YMDDateCheckFilter and YMDNewYearDateFilter of the languages: the
    'date' argument in the format yyyy-mm-dd."""

    @staticmethod
    def parse_date(args):
        """Adds the year, month and day of the 'date' argument to (a copy
        of) the arguments."""
        date_string = args.get('date')
        if date_string is None:
            raise ValueError("Missing key 'date'")
        parts = java_split(date_string, '-')
        if len(parts) != 3:
            raise RuntimeError("Expected date in format 'yyyy-mm-dd': '" + date_string + "'")
        args = dict(args)
        args['year'] = parts[0]
        args['month'] = parts[1]
        args['day'] = parts[2]
        return args

    @staticmethod
    def correct_date(match, args):
        """A copy of the match with {realDate} in the message replaced by
        the date in the next year."""
        from .base import RuleMatch
        correct_year = java_parse_int(args.get('year')) + 1
        correct_date = '%d-%s-%s' % (correct_year, args.get('month'), args.get('day'))
        message = match.message.replace('{realDate}', correct_date)
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message, match.short_message)
        rule_match.type = match.type
        return rule_match


def java_float(x):
    """Rounds a number to a Java float (IEEE 754 single precision)."""
    try:
        return struct.unpack('f', struct.pack('f', x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def java_float_to_string(f):
    """java.lang.Float.toString: the shortest decimal that uniquely
    distinguishes the float, as plain decimal for 1e-3 <= |f| < 1e7 (with
    at least one digit after the point), otherwise in computerized
    scientific notation (like 1.0E10)."""
    if math.isnan(f):
        return 'NaN'
    if math.isinf(f):
        return 'Infinity' if f > 0 else '-Infinity'
    if f == 0:
        return '-0.0' if math.copysign(1, f) < 0 else '0.0'
    sign = '-' if f < 0 else ''
    a = abs(f)
    for p in range(1, 10):
        s = '%.*e' % (p - 1, a)
        if java_float(float(s)) == a:
            break
    mantissa, exp = s.split('e')
    digits = mantissa.replace('.', '').rstrip('0') or '0'
    e = int(exp)
    if 1e-3 <= a < 1e7:
        point = e + 1  # position of the decimal point in digits
        if point <= 0:
            return sign + '0.' + '0' * (-point) + digits
        if point >= len(digits):
            return sign + digits + '0' * (point - len(digits)) + '.0'
        return sign + digits[:point] + '.' + digits[point:]
    return sign + digits[0] + '.' + (digits[1:] or '0') + 'E' + str(e)


class AbstractTextToNumberFilter(RuleFilter):
    """Port of org.languagetool.rules.AbstractTextToNumberFilter: adds the
    number written with words in the marked tokens as a suggestion (with
    Java float arithmetic), e.g. "tres mil" -> "3000", with a decimal
    comma (is_comma()) and percentages (is_percentage()).

    Subclasses define the class attributes numbers and multipliers (word ->
    value) and implement is_comma(s) and is_percentage(pattern_tokens, i),
    optionally format_result(s) and tokenize(s). In Java numbers and
    multipliers are static fields of the abstract class, filled by the
    static initializers of all loaded subclasses (so in a JVM with several
    languages they are shared); here each subclass has its own."""

    numbers = {}
    multipliers = {}

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        numbers = self.numbers
        multipliers = self.multipliers
        f = java_float
        pos_word = 0
        total = 0.0
        current = 0.0
        total_decimal = 0.0
        current_decimal = 0.0
        added_zeros = 0
        percentage = False
        decimal = False
        while pos_word < len(pattern_tokens) and pattern_tokens[pos_word].end_pos <= match.to_pos:
            # inside <marker>
            if pattern_tokens[pos_word].start_pos >= match.from_pos and \
                    pattern_tokens[pos_word].end_pos <= match.to_pos:
                form = pattern_tokens[pos_word].token.lower()
                if pos_word > 0 and self.is_percentage(pattern_tokens, pos_word):
                    percentage = True
                    break
                if self.is_comma(form):
                    decimal = True
                    pos_word += 1
                    continue
                for sub_form in self.tokenize(form):
                    if not decimal:
                        if sub_form in numbers:
                            current = f(current + numbers[sub_form])
                        elif sub_form in multipliers:
                            if current == 0:  # mil
                                current = 1.0
                            total = f(total + f(current * multipliers[sub_form]))
                            current = 0.0
                    else:
                        if sub_form in numbers:
                            zeros_to_add = len(self._format(numbers[sub_form], False))
                            # (float / double, then narrowed by the compound assignment)
                            current_decimal = f(current_decimal + numbers[sub_form] / math.pow(10, added_zeros +
                                                                                               zeros_to_add))
                            added_zeros += 1
                        # else: multipliers after the decimal comma are not expected
            pos_word += 1
        total = f(total + current)
        total_decimal = f(total_decimal + current_decimal)
        total = f(total + total_decimal)
        rule_match = match
        rule_match.add_suggested_replacement(self._format(total, percentage))
        return rule_match

    def _format(self, d, percentage):
        # if (d == (long) d): the cast saturates (NaN becomes 0), the long is compared as a float
        if math.isnan(d):
            as_long = 0
        elif d >= 2 ** 63:
            as_long = 2 ** 63 - 1
        elif d <= -2 ** 63:
            as_long = -2 ** 63
        else:
            as_long = int(d)
        if d == java_float(as_long):
            result = '%d' % as_long
        else:
            result = java_float_to_string(d)
        if percentage:
            result = result + '\u202f%'  # narrow non-breaking space + percentage
        return self.format_result(result)

    def is_comma(self, s):
        raise NotImplementedError()

    def is_percentage(self, pattern_tokens, i):
        raise NotImplementedError()

    def format_result(self, s):
        return s

    def tokenize(self, s):
        return [s]


_MAX_UNDERLINED_LENGTH = 50


class MultitokenSpellerFilter(RuleFilter):
    """Port of org.languagetool.rules.spelling.multitoken.MultitokenSpellerFilter:
    provides suggestions for misspelled multitoken expressions, usually
    proper nouns, with the language's multitoken speller
    (Language.get_multitoken_speller())."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        if all(x.ignored_by_speller for x in pattern_tokens):
            return None
        underlined_error = match.original_error_str
        if self._is_clearly_unsuitable(underlined_error):
            return None
        lang = match.rule.language
        # check the spelling for some languages in a different way
        are_tokens_accepted_by_speller = False
        if lang.short_code in ('en', 'de', 'pt', 'nl'):
            if len(lang.short_code_with_country_and_variant) == 2:
                # needed in testing
                lang = lang.default_variant
            are_tokens_accepted_by_speller = not self.is_misspelled(underlined_error, lang)
        replacements = lang.get_multitoken_speller().get_suggestions(underlined_error,
                                                                     are_tokens_accepted_by_speller)
        if not replacements:
            return None
        if len(underlined_error) > 4 and is_all_uppercase(underlined_error):
            # all upper-case suggestions
            all_uppercase_replacements = []
            for replacement in replacements:
                new_replacement = replacement.upper()
                if new_replacement not in all_uppercase_replacements and underlined_error != new_replacement:
                    all_uppercase_replacements.append(new_replacement)
            replacements = all_uppercase_replacements
        else:
            # capitalize suggestion at sentence start
            words_start_pos = 1
            # ignore punctuation marks at the sentence start to do the capitalization
            tokens = match.sentence.non_blank_tokens
            while words_start_pos < len(tokens) and (is_punctuation_mark(tokens[words_start_pos].token)
                                                     or is_not_word_string(tokens[words_start_pos].token)):
                words_start_pos += 1
            if pattern_token_pos == words_start_pos:
                capitalized_replacements = []
                for replacement in replacements:
                    new_replacement = replacement
                    if replacement == replacement.lower():
                        # do not capitalize iPad
                        new_replacement = uppercase_first_char(replacement)
                    if new_replacement not in capitalized_replacements and underlined_error != new_replacement:
                        capitalized_replacements.append(new_replacement)
                replacements = capitalized_replacements
        if not replacements:
            return None
        match.set_suggested_replacements(replacements)
        return match

    @staticmethod
    def _is_clearly_unsuitable(s):
        """Cheaply discard inputs for which the (expensive) multitoken speller
        search cannot yield a suggestion."""
        # (Java string length and Character.isLetter(char): supplementary characters are two
        # surrogates, which are no letters)
        if len(s) + sum(1 for c in s if ord(c) > 0xffff) > _MAX_UNDERLINED_LENGTH:
            return True
        # a multiword expression needs at least two letters (e.g. the two tokens of a proper noun)
        letters = sum(1 for c in s if ord(c) <= 0xffff and is_letter(c))
        return letters < 2

    def is_misspelled(self, s, language):
        return is_misspelled_with_default_speller(s, language)


def _multitoken_speller_filter(language):
    """MultitokenSpellerFilter for languages with a (ported) multitoken
    speller; for the others the filter (and so its rule) is not
    supported."""
    from ..patterns.loader import UnsupportedFilter
    if language is not None and language.get_multitoken_speller() is None:
        raise UnsupportedFilter('org.languagetool.rules.spelling.multitoken.MultitokenSpellerFilter (no multitoken '
                                'speller for %s)' % language.code)
    return MultitokenSpellerFilter(language)


_tools = {}


def _default_tool(lang):
    """Port of Language.createDefaultJLanguageTool()"""
    from ..tool import JLanguageTool
    t = _tools.get(lang.code)
    if t is None:
        t = _tools[lang.code] = JLanguageTool(lang)
    return t


def register(ff):
    p = 'org.languagetool.rules.'
    ff.register(p + 'AdaptSuggestionsFilter', AdaptSuggestionsFilter)
    ff.register(p + 'AddCommasFilter', AddCommasFilter)
    ff.register(p + 'UnderlineSpacesFilter', UnderlineSpacesFilter)
    ff.register(p + 'patterns.ApostropheTypeFilter', ApostropheTypeFilter)
    ff.register(p + 'WhitespaceCheckFilter', WhitespaceCheckFilter)
    ff.register(p + 'DateRangeChecker', DateRangeChecker)
    ff.register(p + 'ShortenedYearRangeChecker', ShortenedYearRangeChecker)
    ff.register(p + 'ConvertToSentenceCaseFilter', ConvertToSentenceCaseFilter)
    ff.register(p + 'CheckPostagsInSuggestionFilter', CheckPostagsInSuggestionFilter)
    ff.register(p + 'IsEnglishWordFilter', IsEnglishWordFilter)
    ff.register(p + 'SuppressIfAnyRuleMatchesFilter', SuppressIfAnyRuleMatchesFilter)
    ff.register(p + 'spelling.multitoken.MultitokenSpellerFilter', _multitoken_speller_filter)
