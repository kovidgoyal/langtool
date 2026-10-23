"""Language independent rule filters from languagetool-core (the
<filter class="org.languagetool.rules.XXX"> classes)."""

import datetime

import regex

from .. import jregex
from ..tools import (is_punctuation_or_symbol, is_all_uppercase, is_capitalized_word, is_whitespace,
                     uppercase_first_char, is_not_all_lowercase, is_numeric, trim_special_characters, is_junit_test)
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
    f = extensions.lookup('adapt_suggestion', lang.short_code)
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

    def _get_tagger(self):
        if self._tagger is None:
            from ..api import get_language
            try:
                self._tagger = get_language('en-US').tagger
            except Exception:
                self._tagger = False
        return self._tagger or None

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
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
        for r in lt.get_all_active_rules():
            if r.get_id() in rule_ids and not r.is_text_level_rule():
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
