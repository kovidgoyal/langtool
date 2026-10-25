"""German rule filters: port of the filters of org.languagetool.rules.de
(AdaptSuggestionFilter, AdvancedSynthesizerFilter, CompoundCheckFilter,
DateCheckFilter, DateFilterHelper, FutureDateFilter,
GermanNumberInWordFilter, GermanSuppressMisspelledSuggestionsFilter,
InsertCommaFilter, NewYearDateFilter, PotentialCompoundFilter,
RecentYearFilter, RemoveUnknownCompoundsFilter, UppercaseNounReadingFilter,
ValidWordFilter, YMDDateCheckFilter, YMDNewYearDateFilter), and of
org.languagetool.rules.SuggestionFilter (used by AdaptSuggestionFilter).

The filters that ask the speller use the default spelling rule of de-DE
(Java: GermanyGerman.getInstance().getDefaultSpellingRule(), see
langtool.lang.de.spelling); the filters that use GermanTagger.INSTANCE or
GermanSynthesizer.INSTANCE use the tagger and synthesizer of 'de'."""

import datetime
import os
import threading

from ... import jregex
from ...analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckWithSuggestionsFilter,
                                   AbstractFutureDateFilter, AbstractNewYearDateFilter, AbstractNumberInWordFilter,
                                   AbstractSuppressMisspelledSuggestionsFilter, YMDDateHelper, java_parse_int,
                                   SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RuleFilter
from ...tools import (is_all_uppercase, is_mixed_case, starts_with_uppercase, trim_special_characters,
                      uppercase_first_char)


def _german():
    """new German() / Languages.getLanguageForShortCode("de")"""
    from ...api import get_language
    return get_language('de')


def _germany_german():
    """GermanyGerman.getInstance()"""
    from ...api import get_language
    return get_language('de-DE')


def _german_tagger():
    """GermanTagger.INSTANCE"""
    return _german().tagger


def _german_synthesizer():
    """GermanSynthesizer.INSTANCE"""
    return _german().synthesizer


def _speller():
    """GermanyGerman.getInstance().getDefaultSpellingRule()"""
    return _germany_german().get_default_spelling_rule()


def _is_misspelled(word):
    speller = _speller()
    return speller is not None and speller.is_misspelled(word)


# Java \s (ASCII whitespace)
_WHITESPACE = jregex.compile('\\s')


def _java_regex_split(pattern, s):
    """Pattern.split(s): trailing empty strings are removed"""
    if s == '':
        return ['']
    parts = []
    last = 0
    for m in pattern.finditer(s):
        if m.end() == 0:
            continue  # a zero-width match at the beginning never produces an empty leading substring
        parts.append(s[last:m.start()])
        last = m.end()
    parts.append(s[last:])
    while parts and parts[-1] == '':
        parts.pop()
    return parts


class SuggestionFilter:
    """Port of org.languagetool.rules.SuggestionFilter: keeps the
    replacements for which the rule finds no error when they are inserted
    into a template sentence ("{}" is replaced by the replacement)."""

    def __init__(self, rule, lang):
        from ...rules.core_filters import _default_tool
        if rule is None:
            raise ValueError('rule must not be None')
        self.rule = rule
        self.lt = _default_tool(lang)  # lang.createDefaultJLanguageTool()

    def filter(self, replacements, template):
        new_replacements = []
        for repl in replacements:
            analyzed_sentences = self.lt.analyze_text(template.replace('{}', repl))
            matches = self.rule.match(analyzed_sentences[0])
            if len(matches) == 0:
                new_replacements.append(repl)
        return new_replacements


_ART_PRO_PATTERN = jregex.compile('(ART|PRO):.*')
_MAS_FEM_NEU_PATTERN = jregex.compile('MAS|FEM|NEU')
_PRO_POS_ETC_PATTERN = jregex.compile('PRO:POS:(NOM|AKK|GEN|DAT):(SIN|PLU):(MAS|FEM|NEU)')
_STV_BEG_PATTERN = jregex.compile(':(STV|BEG).*')

_suggestion_filter = None
_suggestion_filter_lock = threading.Lock()


def _get_suggestion_filter():
    """SuggestionFilter(new AgreementRule(messages, german), german) (Java
    creates it for each match)"""
    global _suggestion_filter
    with _suggestion_filter_lock:
        if _suggestion_filter is None:
            from ...messages import messages_for
            from .agreement import AgreementRule
            german = _german()
            _suggestion_filter = SuggestionFilter(AgreementRule(messages_for('de'), german), german)
        return _suggestion_filter


class AdaptSuggestionFilter(RuleFilter):
    """Port of org.languagetool.rules.de.AdaptSuggestionFilter: adapts the
    determiner before the matched noun to the gender of the suggested
    nouns ("die Roadmap" -> "der Plan") and keeps only the suggestions
    that the AgreementRule accepts."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        new_match = None
        new_sugg = []
        if pattern_token_pos > 0:
            tokens = match.sentence.get_tokens_without_whitespace()
            prev_token = tokens[pattern_token_pos - 1]
            det_noun = prev_token.has_pos_tag_starting_with('ART:') or prev_token.has_pos_tag_starting_with('PRO:')
            if det_noun:
                new_match = RuleMatch(match.rule, match.sentence, prev_token.start_pos, match.to_pos, match.message,
                                      match.short_message)
                for replacement in match.suggested_replacements:
                    adapted_dets = self.get_adapted_det(prev_token, replacement)
                    for adapted_det in adapted_dets:
                        new_repl = adapted_det + ' ' + replacement
                        if new_repl not in new_sugg:
                            new_sugg.append(new_repl)
                new_match.set_suggested_replacements(new_sugg)
            # (Java: an "else if (detAdjNoun && false)" branch using get_adapted_det_adj(), disabled: "needs more
            # testing before commenting in")
        if new_sugg:
            suggestion_filter = _get_suggestion_filter()
            if starts_with_uppercase(new_sugg[0]):
                new_sugg = suggestion_filter.filter(new_sugg, '{} ist das.')
            else:
                new_sugg = suggestion_filter.filter(new_sugg, 'Das ist {}.')
            new_match.set_suggested_replacements(new_sugg)
            return new_match
        return match

    def get_adapted_det(self, det_token, repl):
        old_det_baseform = self._get_baseform(det_token, _ART_PRO_PATTERN)
        result = []
        repl_gender = self._get_noun_gender(repl)
        if repl_gender is None or old_det_baseform is None:
            return result
        synthesizer = _german_synthesizer()
        for reading in det_token.readings:
            pos = reading.pos_tag
            if pos is None or not (pos.startswith('ART:') or pos.startswith('PRO:')):
                continue
            new_det_pos = jregex.java_replace(_MAS_FEM_NEU_PATTERN, repl_gender, pos) \
                .replace('BEG', '(BEG|B/S)').replace(':STV', '')
            repl_det = synthesizer.synthesize(AnalyzedToken(old_det_baseform, None, old_det_baseform), new_det_pos,
                                              True)
            for s in repl_det:
                if starts_with_uppercase(det_token.token):
                    if not s.lower().startswith(det_token.token[:1].lower()):
                        continue  # see below
                    result.append(uppercase_first_char(s))
                else:
                    if not s.startswith(det_token.token[:1]):
                        continue  # mein, dein, sein etc. all share the same lemma ("mein"), but don't suggest "dein" for "mein"
                    result.append(s)
        return result

    def get_adapted_det_adj(self, det_token, adj_token, repl):
        old_det_baseform = self._get_baseform(det_token, _ART_PRO_PATTERN)
        old_adj_baseform = self._get_baseform(adj_token, _ADJ_PATTERN)
        result = []
        repl_gender = self._get_noun_gender(repl)
        if repl_gender is None or old_det_baseform is None or old_adj_baseform is None:
            return result
        synthesizer = _german_synthesizer()
        for reading in det_token.readings:
            pos = reading.pos_tag
            if pos is None or not _ART_PRO_PATTERN.fullmatch(pos):
                continue
            new_det_pos = jregex.java_replace(_MAS_FEM_NEU_PATTERN, repl_gender, pos).replace('BEG', '(BEG|B/S)')
            if new_det_pos.startswith('ART:'):
                new_adj_pos = jregex.java_replace(_MAS_FEM_NEU_PATTERN, repl_gender, pos) \
                    .replace('BEG', '(BEG|B/S)').replace(':STV', '')
            elif new_det_pos.startswith('PRO:'):
                new_adj_pos = jregex.java_replace(
                    _STV_BEG_PATTERN, ':GRU:IND',
                    jregex.java_replace(_PRO_POS_ETC_PATTERN, 'ADJ:$1:$2:$3', new_det_pos), count=1)
            else:
                raise RuntimeError('Unexpected POS tag: ' + new_det_pos)
            repl_det = synthesizer.synthesize(AnalyzedToken(old_det_baseform, None, old_det_baseform), new_det_pos,
                                              True)
            repl_adj = synthesizer.synthesize(AnalyzedToken(old_adj_baseform, None, old_adj_baseform), new_adj_pos,
                                              True)
            for det in repl_det:
                if not det.startswith(det_token.token[:1]):
                    continue  # mein, dein, sein etc. all share the same lemma ("mein"), but don't suggest "dein" for "mein"
                for adj in repl_adj:
                    new_det_adj = det + ' ' + adj
                    if new_det_adj not in result:
                        result.append(new_det_adj)
        return result

    @staticmethod
    def _get_baseform(token, tag_pattern):
        baseform = None
        for reading in token.readings:
            if reading.pos_tag is not None and tag_pattern.fullmatch(reading.pos_tag):
                baseform = reading.lemma
            # TODO: what if more than one match?
        return baseform

    @staticmethod
    def _get_noun_gender(word):
        readings = _german_tagger().tag([word])
        for atr in readings:
            if len(atr.readings) > 0:
                pos = atr.readings[0].pos_tag
                if pos is not None and pos.startswith('SUB:'):
                    parts = pos.split(':')
                    while parts and parts[-1] == '':
                        parts.pop()
                    if len(parts) >= 4:
                        return parts[3]
        return None


_ADJ_PATTERN = jregex.compile('ADJ:.*')


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.de.AdvancedSynthesizerFilter:
    synthesize suggestions using the lemma from one token (lemma_from) and
    the POS tag from another one (postag_from). The lemma_select and
    postag_select attributes are required to choose one among several
    possible readings."""


_added_compounds = None
_added_compounds_lock = threading.Lock()


def _load_words(path):
    words = {}
    with open(path, encoding='utf-8') as f:
        for line in f.read().split('\n'):
            line = line.rstrip('\r')
            hash_pos = line.find('#')
            if hash_pos >= 0:
                line = line[:hash_pos]  # replace comments
            line = line.strip()
            if not line:
                continue
            parts = line.split(';')
            while parts and parts[-1] == '':
                parts.pop()
            if len(parts) != 2:
                raise RuntimeError('Format error in file %s, line: %s, expected 2 semicolon-separated parts, got %d'
                                   % (path, line, len(parts)))
            words.setdefault(parts[0].strip().lower(), []).append(parts[1].strip().lower())
    return words


def _get_added_compounds():
    global _added_compounds
    with _added_compounds_lock:
        if _added_compounds is None:
            from ...language import RULES_DIR
            _added_compounds = _load_words(os.path.join(RULES_DIR, 'de', 'addedCompound.txt'))
        return _added_compounds


class CompoundCheckFilter(RuleFilter):
    """Port of org.languagetool.rules.de.CompoundCheckFilter: accepts the
    match if part1;part2 is listed in de/addedCompound.txt (rules
    directory)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        part1 = arguments.get('part1').lower()
        part2 = arguments.get('part2').lower()
        lst = _get_added_compounds().get(part1)
        return match if lst is not None and part2 in lst else None


# DateFilterHelper.getDayOfWeek(Calendar): Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.GERMAN)
_DAY_NAMES = {SUNDAY: 'Sonntag', MONDAY: 'Montag', TUESDAY: 'Dienstag', WEDNESDAY: 'Mittwoch',
              THURSDAY: 'Donnerstag', FRIDAY: 'Freitag', SATURDAY: 'Samstag'}
_DAY_PREFIXES = (('sonnabend', SATURDAY), ('so', SUNDAY), ('mo', MONDAY), ('di', TUESDAY), ('mi', WEDNESDAY),
                 ('do', THURSDAY), ('fr', FRIDAY), ('sa', SATURDAY))
_MONTH_PREFIXES = (('jän', 1), ('jan', 1), ('feb', 2), ('mär', 3), ('apr', 4), ('mai', 5), ('jun', 6), ('jul', 7),
                   ('aug', 8), ('sep', 9), ('okt', 10), ('nov', 11), ('dez', 12))


class DateFilterHelper:
    """Port of org.languagetool.rules.de.DateFilterHelper (getCalendar(),
    Calendar.getInstance(Locale.GERMANY), is not needed, see
    langtool.rules.core_filters)."""

    @staticmethod
    def get_day_of_week(day_str):
        day = trim_special_characters(day_str).lower()  # quickfix for special characters like soft hyphens
        for prefix, day_of_week in _DAY_PREFIXES:
            if day.startswith(prefix):
                return day_of_week
        raise RuntimeError("Could not find day of week for '" + day_str + "'")

    @staticmethod
    def get_day_of_week_name(date):
        """getDayOfWeek(Calendar)"""
        return _DAY_NAMES.get(date.day_of_week, '')

    @staticmethod
    def get_month(month_str):
        mon = trim_special_characters(month_str).lower()
        for prefix, month in _MONTH_PREFIXES:
            if mon.startswith(prefix):
                return month
        raise RuntimeError("Could not find month '" + month_str + "'")


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.de.DateCheckFilter, the German
    localization of AbstractDateCheckWithSuggestionsFilter."""

    def get_day_of_week(self, day_str):
        return DateFilterHelper.get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return DateFilterHelper.get_day_of_week_name(date)

    def get_month(self, month_str):
        return DateFilterHelper.get_month(month_str)

    def get_error_message_wrong_year(self):
        return 'Dieses Datum stimmt nicht mit dem Tag überein. Meinten Sie "{currentYear}"?'

    def adjust_suggestion(self, sugg):
        # So. vs Sonntag
        dot_comma_pos = sugg.find('.,')
        if 5 < dot_comma_pos < 12:
            # remove unnecessary dot
            return sugg.replace('.,', ',')
        comma_pos = sugg.find(',')
        if dot_comma_pos < 0 and 0 < comma_pos < 5:
            # add dot
            return sugg.replace(',', '.,')
        return sugg


class YMDDateCheckFilter(DateCheckFilter):
    """Port of org.languagetool.rules.de.YMDDateCheckFilter: a date filter
    that expects a 'date' argument in the format 'yyyy-mm-dd'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for YMDDateCheckFilter")
        return super().accept_rule_match(match, YMDDateHelper.parse_date(args), pattern_token_pos, pattern_tokens,
                                         token_positions)


class FutureDateFilter(AbstractFutureDateFilter):
    """Port of org.languagetool.rules.de.FutureDateFilter (with
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return DateFilterHelper.get_month(localized_month)


class NewYearDateFilter(AbstractNewYearDateFilter):
    """Port of org.languagetool.rules.de.NewYearDateFilter (with
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return DateFilterHelper.get_month(localized_month)


class YMDNewYearDateFilter(NewYearDateFilter):
    """Port of org.languagetool.rules.de.YMDNewYearDateFilter: a new year
    date filter that expects a 'date' argument in the format
    'yyyy-mm-dd'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for YMDDateCheckFilter")
        args = YMDDateHelper.parse_date(args)
        return super().accept_rule_match(YMDDateHelper.correct_date(match, args), args, pattern_token_pos,
                                         pattern_tokens, token_positions)


class RecentYearFilter(RuleFilter):
    """Port of org.languagetool.rules.de.RecentYearFilter: keeps only those
    matches whose 'year' value is last year or in recent years (up to
    'maxYearsBack' years ago)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        this_year = datetime.date.today().year
        max_year = this_year - java_parse_int(arguments.get('maxYearsBack'))
        year = java_parse_int(arguments.get('year'))
        if max_year <= year < this_year:
            return match
        return None


class GermanNumberInWordFilter(AbstractNumberInWordFilter):
    """Port of org.languagetool.rules.de.GermanNumberInWordFilter: the
    misspelling check and the suggestions of the default spelling rule of
    de-DE."""

    def is_misspelled(self, word):
        return _is_misspelled(word)

    def get_suggestions(self, word):
        speller = _speller()
        return list(speller.get_suggestions(word)) if speller is not None else []


class GermanSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.de.GermanSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of the rule's language)."""


_SAGT = jregex.compile('[Ss]agt?')
_DER_ETC = jregex.compile('der|die|das|seine|ihre|deine|unsere|meine|folgender|dieser')
_DENKE_ETC = jregex.compile('denke|dachte|glaube|schätze|vermute|behaupte')
_BEI_FUER_MIT = jregex.compile('bei|für|mit')
_DIR_ETC = jregex.compile('[Di]ir|[Dd]ich|[Ee]uer|[Ee]uch')


def _get_tag(i, parts):
    return _german_tagger().tag([parts[i]])


def _has_tag(tags, tag_start):
    return any(k.has_pos_tag_starting_with(tag_start) for k in tags)


class InsertCommaFilter(RuleFilter):
    """Port of org.languagetool.rules.de.InsertCommaFilter: specific to
    KOMMA_ZWISCHEN_HAUPT_UND_NEBENSATZ, helps setting the comma
    suggestion, if easily possible."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                               match.short_message)
        suggestions = []
        for replacement in match.suggested_replacements:
            parts = _java_regex_split(_WHITESPACE, replacement)
            if len(parts) == 2:
                suggestions.append(parts[0] + ', ' + parts[1])
            elif len(parts) == 3:
                tags1 = _get_tag(0, parts)
                tags2 = _get_tag(1, parts)
                tags3 = _get_tag(2, parts)
                if _has_tag(tags1, 'VER:') and _has_tag(tags2, 'PRO:PER:'):
                    # "Ich hoffe(,) es geht Ihnen gut."
                    suggestions.append(parts[0] + ', ' + parts[1] + ' ' + parts[2])
                elif _SAGT.fullmatch(parts[0]) and parts[1] == 'mal' and _has_tag(tags3, 'VER:'):
                    # "Sag mal(,) hast du"
                    suggestions.append(parts[0] + ' ' + parts[1] + ', ' + parts[2])
                elif _has_tag(tags1, 'VER:') and _has_tag(tags2, 'ADV:') and _has_tag(tags3, 'VER:'):
                    # "Ich denke(,) hier kann aber auch ..."
                    suggestions.append(parts[0] + ', ' + parts[1] + ' ' + parts[2])
            elif 4 <= len(parts) <= 7:
                tags1 = _get_tag(0, parts)
                tags2 = _get_tag(1, parts)
                tags3 = _get_tag(2, parts)
                tags4 = _get_tag(3, parts)
                rest1 = ' '.join(parts[1:])
                sentence_tokens = match.sentence.tokens
                if pattern_token_pos <= 2 or (pattern_token_pos == 3 and len(sentence_tokens) >= 1
                                              and sentence_tokens[1].has_pos_tag_starting_with('ADV:')):
                    if len(parts) == 5 and _has_tag(tags1, 'VER:') and _has_tag(tags2, 'ART:') \
                            and _has_tag(tags3, 'SUB:') and _has_tag(_get_tag(3, parts), 'SUB:') \
                            and _has_tag(_get_tag(4, parts), 'VER:'):
                        # "Ist der Kunde Verbraucher(,) gilt ..."
                        suggestions.append(parts[0] + ' ' + parts[1] + ' ' + parts[2] + ' ' + parts[3] + ',')
                    elif len(parts) == 4 and pattern_tokens[0].has_pos_tag_starting_with('VER:') \
                            and _DER_ETC.fullmatch(pattern_tokens[1].token):
                        # "Aristoteles meint(,) das Genussleben führe nicht zum Glück."
                        suggestions.append(parts[0] + ', ' + rest1)
                    elif _has_tag(tags1, 'VER:') and _has_tag(tags2, 'PRO:POS:') and _has_tag(tags3, 'SUB:'):
                        # "Ich glaube(,) eure Premium-Accounts sind noch aktiv."
                        suggestions.append(parts[0] + ', ' + rest1)
                    elif _has_tag(tags1, 'VER:') and _has_tag(tags2, 'PRO:PER:') and _has_tag(tags3, 'ADV:INR'):
                        # "Weißt du(,) warum diese Regel aus ist?"
                        rest2 = ' '.join(parts[2:])
                        suggestions.append(parts[0] + ' ' + parts[1] + ', ' + rest2)
                    elif _has_tag(tags1, 'VER:') and _has_tag(tags2, 'PRO:POS:') and _has_tag(tags3, 'ADJ:'):
                        # "Ich glaube(,) eure individuellen Premium-Accounts sind noch aktiv."
                        suggestions.append(parts[0] + ', ' + rest1)
                    elif _DENKE_ETC.fullmatch(parts[0]) and _has_tag(tags2, 'PRO:DEM:') and _has_tag(tags3, 'SUB:'):
                        # "Ich schätze(,) diese Krawatte passt gut zum Anzug."
                        suggestions.append(parts[0] + ', ' + rest1)
                    elif pattern_token_pos == 1 and _BEI_FUER_MIT.fullmatch(parts[1]) \
                            and _DIR_ETC.fullmatch(parts[2]) and _has_tag(tags4, 'VER:'):
                        # "Hoffe(,) bei euch ist alles gut."
                        suggestions.append(parts[0] + ', ' + rest1)
        rule_match.set_suggested_replacements(suggestions)
        rule_match.type = match.type
        return rule_match


class PotentialCompoundFilter(RuleFilter):
    """Port of org.languagetool.rules.de.PotentialCompoundFilter: creates a
    compound word from two tokens (arguments part1 and part2). If the
    joined word is a valid word (no match of the spelling rule of de-DE),
    the rule suggests the joined word (and before it the hyphenated word if
    the joined word is longer than 20 characters), otherwise the
    hyphenated word."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        part1 = arguments.get('part1')
        part2 = arguments.get('part2')
        part1capitalized = part1
        part2capitalized = part2
        part2lowercase = part2
        if not is_mixed_case(part2) and not is_all_uppercase(part2):
            part2lowercase = part2.lower()
            part2capitalized = uppercase_first_char(part2.lower())
        if not is_mixed_case(part1) and not is_all_uppercase(part1):
            part1capitalized = uppercase_first_char(part1.lower())
        joined_word = part1capitalized + part2lowercase
        hyphenated_word = part1capitalized + '-' + part2capitalized
        replacements = []
        # create an AnalyzedSentence without instantiating a new JLanguageTool
        language = _germany_german()
        tokens_list = language.tagger.tag([joined_word])
        sentence_start = AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)
        analyzed_sentence = AnalyzedSentence([sentence_start, tokens_list[0]])
        # check with the spelling rule
        speller = language.get_default_spelling_rule()
        matches = speller.match(analyzed_sentence) if speller is not None else []
        if len(matches) == 0:
            if len(joined_word.encode('utf-16-le')) // 2 > 20:
                replacements.append(hyphenated_word)
            replacements.append(joined_word)
        else:
            replacements.append(hyphenated_word)
        if replacements:
            rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                                   match.short_message)
            rule_match.type = match.type
            rule_match.set_suggested_replacements(replacements)
            return rule_match
        return None


class RemoveUnknownCompoundsFilter(RuleFilter):
    """Port of org.languagetool.rules.de.RemoveUnknownCompoundsFilter:
    discards the match if the compound of part1 and part2 (lowercased) is
    misspelled."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        compound = arguments.get('part1') + arguments.get('part2').lower()
        if _is_misspelled(compound):
            return None
        # TODO: use ngrams. no occurrences for compound = don't show error
        return match


class UppercaseNounReadingFilter(RuleFilter):
    """Port of org.languagetool.rules.de.UppercaseNounReadingFilter: accepts
    rule matches when the uppercased word of the 'token' parameter has a
    noun reading, e.g. German "stand" (past of "stehen") would be turned
    into "Stand" and the rule match would be accepted, as it's a noun."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        token = arguments.get('token')
        if token is None:
            raise RuntimeError("Set 'token' for filter org.languagetool.rules.de.UppercaseNounReadingFilter in rule "
                               + match.rule.get_id())
        uppercase = uppercase_first_char(token)
        tags = _german_tagger().tag([uppercase])
        has_noun_reading = False
        for tag in tags:
            if tag.has_partial_pos_tag('SUB:') and not tag.has_partial_pos_tag('ADJ'):
                has_noun_reading = True
                break
        if has_noun_reading:
            return match
        return None


class ValidWordFilter(RuleFilter):
    """Port of org.languagetool.rules.de.ValidWordFilter, used in
    LEERZEICHEN_NACH_KLAMMER: discards the match if word1 + word2 (or
    word1 + lowercased word2) is a correctly spelled word."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        word1 = arguments.get('word1') + arguments.get('word2')
        word2 = arguments.get('word1') + arguments.get('word2').lower()
        if not _is_misspelled(word1) or not _is_misspelled(word2):
            # e.g. "(Promotions)Studierende" -> "Promotionsstudierende" is ok, so no match
            return None
        # all other cases, e.g.: "Das ist (vielleicht)der bessere Ansatz".
        return match


# the filter classes of this module (registered as org.languagetool.rules.de.<class name>)
FILTERS = (AdaptSuggestionFilter, AdvancedSynthesizerFilter, CompoundCheckFilter, DateCheckFilter, FutureDateFilter,
           GermanNumberInWordFilter, GermanSuppressMisspelledSuggestionsFilter, InsertCommaFilter, NewYearDateFilter,
           PotentialCompoundFilter, RecentYearFilter, RemoveUnknownCompoundsFilter, UppercaseNounReadingFilter,
           ValidWordFilter, YMDDateCheckFilter, YMDNewYearDateFilter)
