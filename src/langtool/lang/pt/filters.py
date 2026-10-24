"""Portuguese rule filters (port of the filters of org.languagetool.rules.pt:
AdvancedSynthesizerFilter, BrazilianToponymFilter with BrazilianToponymMap
and BrazilianToponymMapLoader, ConfusionCheckFilter with
ConfusionPairsDataLoader, DateCheckFilter, YMDDateCheckFilter,
FutureDateFilter, NewYearDateFilter, YMDNewYearDateFilter and
DateFilterHelper, NoDisambiguationPortuguesePartialPosTagFilter,
PortugueseEnclisisFilter, PortugueseProclisisFilter,
PortugueseSuppressMisspelledSuggestionsFilter,
RegularIrregularParticipleFilter and RomanNumeralFilter).

PortugueseSynthesizer.INSTANCE (the synthesizer of all Portuguese variants)
is the synthesizer of the language pt here."""

import threading

from ... import jregex
from ...rules.abstract_rules import _read_lines, _resource_file, _rules_file, java_hash_set_order
from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckWithSuggestionsFilter,
                                   AbstractFutureDateFilter, AbstractNewYearDateFilter,
                                   AbstractSuppressMisspelledSuggestionsFilter, PartialPosTagFilter, YMDDateHelper,
                                   java_parse_int,
                                   SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RegexRuleFilter, RuleFilter
from ...tools import (has_diacritics, is_all_uppercase, is_capitalized_word, java_split, java_trim,
                      trim_special_characters, uppercase_first_char)


def _portuguese():
    """Portuguese.getInstance()"""
    from ...api import get_language
    return get_language('pt')


def _synthesizer():
    """PortugueseSynthesizer.INSTANCE"""
    return _portuguese().synthesizer


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.pt.AdvancedSynthesizerFilter:
    synthesize suggestions using the lemma from one token (lemma_from) and
    the POS tag from another one (postag_from); first and second person
    plural present forms must end in "s", and postagReplace "keepPronoun"
    keeps the pronoun part of the original POS tag."""

    def is_suggestion_exception(self, token, desired_postag):
        return desired_postag in ('VMIP1P0', 'VMIP2P0') and not token.endswith('s')

    @staticmethod
    def move_pronoun_tag(source_tag, destination_tag):
        source_tag_parts = java_split(source_tag, ':')
        new_tag = destination_tag
        if len(source_tag_parts) == 2:
            destination_tag_parts = java_split(destination_tag, ':')
            new_tag = destination_tag_parts[0] + ':' + source_tag_parts[1]
        return new_tag

    def get_composite_postag(self, lemma_select, postag_select, original_postag, desired_postag, postag_replace):
        if postag_replace == 'keepPronoun':
            return self.move_pronoun_tag(original_postag, desired_postag)
        return super().get_composite_postag(lemma_select, postag_select, original_postag, desired_postag,
                                            postag_replace)


class PortugueseSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.pt.PortugueseSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of Portuguese, see
    langtool.lang.pt.spelling)."""


class RomanNumeralFilter(RuleFilter):
    """Port of org.languagetool.rules.pt.RomanNumeralFilter: the suggestion
    is the Roman number of the argument arabicSource."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        arabic_source = arguments.get('arabicSource')
        match.set_suggested_replacement(_synthesizer().get_roman_number(arabic_source))
        return match


class PortugueseProclisisFilter(RuleFilter):
    """Port of org.languagetool.rules.pt.PortugueseProclisisFilter: the
    suggestions put the pronoun of the enclitic verb (the last pattern
    token, e.g. "fá-lo") before the verb ("o faz")."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        enclitic_verb_token_readings = pattern_tokens[-1]
        suggestions = []
        for at in enclitic_verb_token_readings.readings:
            pos_tag = at.pos_tag
            if pos_tag is None or not pos_tag.startswith('V') or ':' not in pos_tag:
                continue
            old_token = at.token
            tag_parts = java_split(pos_tag, ':')
            verb_tag = tag_parts[0]
            new_verb = _synthesizer().synthesize(at, verb_tag)[0]
            old_token_parts = java_split(old_token, '-')
            # Includes only the relevant part of the verb; i.e. for mesoclitics, we ignore the ending
            old_verb = old_token_parts[0]
            old_pronoun = old_token_parts[1]
            if old_pronoun in ('lo', 'no'):
                new_pronoun_forms = ['o']
            elif old_pronoun in ('la', 'na'):
                new_pronoun_forms = ['a']
            elif old_pronoun == 'los':
                new_pronoun_forms = ['os']
            elif old_pronoun in ('las', 'nas'):
                new_pronoun_forms = ['as']
            elif old_pronoun == 'nos':
                new_pronoun_forms = ['nos']
                if old_verb.endswith('m') or old_verb.endswith('ão') or old_verb.endswith('õe'):
                    new_pronoun_forms.append('os')
            else:
                new_pronoun_forms = [old_pronoun]
            for new_pronoun in new_pronoun_forms:
                suggestion = new_pronoun + ' ' + new_verb
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
        # (a HashSet in Java)
        match.set_suggested_replacements(java_hash_set_order(suggestions))
        return match


class PortugueseEnclisisFilter(RuleFilter):
    """Port of org.languagetool.rules.pt.PortugueseEnclisisFilter: the
    suggestions are the forms of the verb (argument verbPos, a 0-based
    index of the pattern tokens) with the pronoun (argument pronounPos)
    attached, synthesized with the verb's POS tag plus ":" plus the
    pronoun's POS tag (with convertToAccusative, nominative pronoun tags
    become accusative ones)."""

    @staticmethod
    def _convert_pronoun_to_accusative(pronoun_tag):
        # Used when we we have a pronoun like "eles", that is frequently used as a direct object, but we need it
        # to be "os", which is tagged as the accusative form of "eles".
        if pronoun_tag.endswith('N00'):
            return pronoun_tag[:-3] + 'A00'
        return pronoun_tag

    def _get_pronoun_tags(self, pronoun_readings, verb_text, convert_to_accusative):
        # Extract pronoun tags from pronoun tokens
        # We cannot just get all tags uncritically because of the 'nos' issue.
        pronoun_tags = []
        for pronoun_token in pronoun_readings.readings:
            pronoun_text = pronoun_token.token
            if pronoun_text == 'nos':
                pronoun_tags.append('PP1CPO00')
                if verb_text.endswith('m') or verb_text.endswith('ão') or verb_text.endswith('õe'):
                    pronoun_tags.append('PP3MPA00')
                break
            pos_tag = pronoun_token.pos_tag
            if pos_tag is not None and pos_tag.startswith('PP'):
                if convert_to_accusative:
                    pos_tag = self._convert_pronoun_to_accusative(pos_tag)
                pronoun_tags.append(pos_tag)
        return pronoun_tags

    @staticmethod
    def _get_verb_forms(verb_stem_token_readings, pronoun_tags):
        suggestions = []
        is_title_case = is_capitalized_word(verb_stem_token_readings.token)
        is_all_caps = is_all_uppercase(verb_stem_token_readings.token)
        synth = _synthesizer()
        for at in verb_stem_token_readings.readings:
            pos_tag = at.pos_tag
            if pos_tag is not None and pos_tag.startswith('V'):
                for pronoun_tag in pronoun_tags:
                    enclisis_tag = pos_tag + ':' + pronoun_tag
                    for form in synth.synthesize(at, enclisis_tag):
                        if is_title_case:
                            form = uppercase_first_char(form)
                        elif is_all_caps:
                            form = form.upper()
                        if form not in suggestions:
                            suggestions.append(form)
                break
        # (a HashSet in Java)
        return java_hash_set_order(suggestions)

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        verb_pos = java_parse_int(arguments.get('verbPos'))
        pronoun_pos = java_parse_int(arguments.get('pronounPos'))
        convert_to_accusative = (arguments.get('convertToAccusative') or '').lower() == 'true'
        verb_stem_token_readings = pattern_tokens[verb_pos]
        pronoun_token_readings = pattern_tokens[pronoun_pos]
        pronoun_tags = self._get_pronoun_tags(pronoun_token_readings, verb_stem_token_readings.token,
                                              convert_to_accusative)
        if not pronoun_tags:
            return None
        match.set_suggested_replacements(self._get_verb_forms(verb_stem_token_readings, pronoun_tags))
        return match


def _is_regular(p):
    lp = p.lower()
    return lp.endswith('do') or lp.endswith('dos') or lp.endswith('da') or lp.endswith('das')


class RegularIrregularParticipleFilter(RuleFilter):
    """Port of org.languagetool.rules.pt.RegularIrregularParticipleFilter:
    for verbs with a regular (-do) and an irregular participle, suggests
    the other one (argument direction: RegularToIrregular or
    IrregularToRegular); the participle replaces {suggestion} in the first
    suggestion."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        # RegularToIrregular or IrregularToRegular
        direction = self.get_required('direction', arguments)
        atr = None
        for token in pattern_tokens:
            if token.start_pos == match.from_pos:
                atr = token
                break
        replacement = None
        if atr.has_pos_tag_starting_with('VMP'):
            selected_at = None
            desired_postag = None
            for at in atr.readings:
                if at.pos_tag is not None and at.pos_tag.startswith('VMP'):
                    selected_at = at
                    desired_postag = at.pos_tag
            # assente SC assentado SM
            if desired_postag.endswith('C'):
                desired_postag = desired_postag[:-1] + '[MC]'
            else:
                desired_postag = desired_postag[:-1] + '[' + desired_postag[-1:] + 'C]'
            participles = _portuguese().synthesizer.synthesize(selected_at, desired_postag, True)
            if participles is not None and len(participles) > 1:
                if direction.lower() == 'regulartoirregular' and _is_regular(atr.token):
                    if not _is_regular(participles[0]):
                        replacement = participles[0]
                    elif not _is_regular(participles[1]):
                        replacement = participles[1]
                elif direction.lower() == 'irregulartoregular' and not _is_regular(atr.token):
                    if _is_regular(participles[0]):
                        replacement = participles[0]
                    elif _is_regular(participles[1]):
                        replacement = participles[1]
                if replacement is not None:
                    rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                                           match.short_message)
                    rule_match.type = match.type
                    suggestion = match.suggested_replacements[0].replace('{suggestion}', replacement)
                    suggestion = suggestion.replace('{Suggestion}', uppercase_first_char(replacement))
                    suggestion = suggestion.replace('{SUGGESTION}', replacement.upper())
                    rule_match.set_suggested_replacement(suggestion)
                    return rule_match
        return None


class NoDisambiguationPortuguesePartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.pt.NoDisambiguationPortuguesePartialPosTagFilter:
    a PartialPosTagFilter for Portuguese that does not run the
    disambiguator (the token is only tagged)."""

    def tag(self, token):
        return _portuguese().tagger.tag([token])


# --- ConfusionCheckFilter ---

_confusion_pairs = {}
_confusion_pairs_lock = threading.Lock()


def load_confusion_pairs(paths):
    """ConfusionPairsDataLoader.loadWords: form -> list of (token, POS tag)
    readings (an AnalyzedTokenReadings in Java)"""
    m = {}
    for path in paths:
        for raw in _read_lines(path):
            line = java_trim(raw)
            if not line or line[0] == '#':  # ignore comments
                continue
            parts = java_split(line, ';')
            if len(parts) != 3:
                raise RuntimeError('Format error in file ' + path + ', line: ' + line + ', '
                                   + 'expected 3 semicolon-separated parts, got ' + str(len(parts)))
            m.setdefault(parts[0], []).append((parts[1], parts[2]))
    return m


def _relevant_words(language, variant_dir):
    with _confusion_pairs_lock:
        m = _confusion_pairs.get(variant_dir)
        if m is None:
            m = _confusion_pairs[variant_dir] = load_confusion_pairs(
                [_rules_file(language, '/pt/confusion_pairs.txt'),
                 _rules_file(language, '/pt/' + variant_dir + '/confusion_pairs.txt')])
        return m


def _matches_pos_tag_regex(readings, pattern):
    """AnalyzedTokenReadings.matchesPosTagRegex"""
    p = jregex.compile(pattern)
    return any(tag is not None and p.fullmatch(tag) for _token, tag in readings)


_MS = jregex.compile('NC[MC][SN]000|A..[MC][SN].|V.P..SM')
_FS = jregex.compile('NC[FC][SN]000|A..[FC][SN].|V.P..SF')
_MP = jregex.compile('NC[MC][PN]000|A..[MC][PN].|V.P..PM')
_FP = jregex.compile('NC[FC][PN]000|A..[FC][PN].|V.P..PF')
_CP = jregex.compile('NC[MFC][PN]000|A..[MFC][PN].|V.P..P.')
_CS = jregex.compile('NC[MFC][SN]000|A..[MFC][SN].|V.P..S.')
_GENDER_NUMBER = (('[NAPD].+MS.*|V.P..SM', _MS), ('[NAPD].+MP.*|V.P..PM', _MP), ('[NAPD].+FS.*|V.P..SF', _FS),
                  ('[NAPD].+FP.*|V.P..PF', _FP), ('[NAPD].+CP.*|V.P..P.', _CP), ('[NAPD].+CS.*|V.P..S.', _CS))


class ConfusionCheckFilter(RuleFilter):
    """Port of org.languagetool.rules.pt.ConfusionCheckFilter: accepts the
    match if the form (argument 'form', lowercased) is in
    /pt/confusion_pairs.txt or the file of the variant
    (/pt/pt-BR/confusion_pairs.txt for pt-BR, /pt/pt-PT/confusion_pairs.txt
    for all other variants) with a reading matching the argument 'postag'
    (and, with 'gendernumberFrom', if the first reading of the confusion
    agrees in gender and number with that token); the confused word
    replaces {suggestion} in the first suggestion."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        desired_gender_number_pattern = None
        replacement = None
        postag = self.get_required('postag', arguments)
        form = self.get_required('form', arguments).lower()
        gendernumber_from = self.get_optional('gendernumberFrom', arguments)
        if gendernumber_from is not None:
            i = java_parse_int(gendernumber_from)
            if i < 1 or i > len(pattern_tokens):
                raise ValueError('ConfusionCheckFilter: Index out of bounds in ' + match.rule.get_full_id()
                                 + ', value: ' + str(i))
            atr = pattern_tokens[i - 1]
            for regex, pattern in _GENDER_NUMBER:
                if atr.matches_pos_tag_regex(regex):
                    desired_gender_number_pattern = pattern
                    break
        variant = match.rule.language.short_code_with_country_and_variant
        if variant == 'pt-BR':
            relevant_words = _relevant_words(match.rule.language, 'pt-BR')
        else:
            # in Africa and elsewhere, PT spelling appears to be dominant, but leave this condition separate
            relevant_words = _relevant_words(match.rule.language, 'pt-PT')
        readings = relevant_words.get(form)
        if readings is not None:
            if _matches_pos_tag_regex(readings, postag):
                if desired_gender_number_pattern is not None:
                    if not desired_gender_number_pattern.fullmatch(readings[0][1]):
                        return None
                    replacement = readings[0][0]
                elif gendernumber_from is None:
                    # there is no desired gender number defined
                    replacement = readings[0][0]
        if replacement is not None:
            message = match.message
            # Change the message if the replacement has no diacritic
            if not (has_diacritics(replacement) and not has_diacritics(form)):
                message = message.replace('se escribe con tilde', 'se escribe de otra manera')
            rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, message,
                                   match.short_message)
            rule_match.type = match.type
            suggestion = match.suggested_replacements[0].replace('{suggestion}', replacement)
            suggestion = suggestion.replace('{Suggestion}', uppercase_first_char(replacement))
            suggestion = suggestion.replace('{SUGGESTION}', replacement.upper())
            rule_match.set_suggested_replacement(suggestion)
            return rule_match
        return None


# --- BrazilianToponymFilter ---

# BrazilianToponymMapLoader
_STATES = ('AC',  # Acre
           'AL',  # Alagoas
           'AP',  # Amapá
           'AM',  # Amazonas
           'BA',  # Bahia
           'CE',  # Ceará
           'DF',  # Distrito Federal
           'ES',  # Espírito Santo
           'GO',  # Goiás
           'MA',  # Maranhão
           'MT',  # Mato Grosso
           'MS',  # Mato Grosso do Sul
           'MG',  # Minas Gerais
           'PA',  # Pará
           'PB',  # Paraíba
           'PR',  # Paraná
           'PE',  # Pernambuco
           'PI',  # Piauí
           'RJ',  # Rio de Janeiro
           'RN',  # Rio Grande do Norte
           'RS',  # Rio Grande do Sul
           'RO',  # Rondônia
           'RR',  # Roraima
           'SC',  # Santa Catarina
           'SP',  # São Paulo
           'SE',  # Sergipe
           'TO')  # Tocantins


class BrazilianToponymMap:
    """Port of org.languagetool.rules.pt.BrazilianToponymMap (with
    BrazilianToponymMapLoader): the municipalities of the Brazilian states
    (pt/brazilian_municipalities/<state>.tsv, normalized: hyphens replaced
    by spaces, lowercase)."""

    def __init__(self, language):
        self.map = {}
        for state in _STATES:
            toponyms = _read_lines(_resource_file(language, 'pt/brazilian_municipalities/' + state + '.tsv'))
            self.map[state] = [t.replace('-', ' ').lower() for t in toponyms]
        self._all = frozenset(t for municipalities in self.map.values() for t in municipalities)

    @staticmethod
    def _toponym_iter(toponym, processor, default_value):
        # Since the actually toponym string is only a heuristic, it could be that we match more than we need,
        # e.g.: "Venho do Rio de Janeiro" will match, hungrily, the whole thing, rather than just "Rio de
        # Janeiro". To account for this, we loop, dropping the leftmost element of the toponym until we can't
        # check any more.
        normalised_toponym = toponym.replace('-', ' ').lower()
        toponym_parts = java_split(normalised_toponym, ' ')
        for i in range(len(toponym_parts)):
            result = processor(' '.join(toponym_parts[i:]))
            if result is not None:
                return result
        return default_value

    def is_valid_toponym(self, toponym):
        return self._toponym_iter(toponym, lambda t: True if t in self._all else None, False)

    def get_states_with_municipality(self, toponym):
        # (in the iteration order of the Java HashMap)
        return [state for state in java_hash_set_order(list(self.map)) if toponym in self.map[state]]

    def is_toponym_in_state(self, toponym, state):
        municipalities = self.map.get(state)
        return municipalities is not None and toponym in municipalities


_toponym_map = []
_toponym_map_lock = threading.Lock()


def _brazilian_toponym_map(language):
    with _toponym_map_lock:
        if not _toponym_map:
            _toponym_map.append(BrazilianToponymMap(language))
        return _toponym_map[0]


class BrazilianToponymFilter(RegexRuleFilter):
    """Port of org.languagetool.rules.pt.BrazilianToponymFilter (a regex
    rule filter): the state after a Brazilian municipality (group 1) is
    written with an en dash; only real municipalities are checked."""

    def accept_rule_match(self, match, arguments, sentence, pattern_match):
        toponym = pattern_match.group(1)
        underlined = pattern_match.group(2)
        state = pattern_match.group(3)
        # TODO: read this from user options or something...
        suggestion = '–' + state
        if suggestion == underlined:
            return None
        # If it isn't a city in *any* state, it's prob. not intended as a city, so we don't perform the check.
        if not _brazilian_toponym_map(match.rule.language).is_valid_toponym(toponym):
            return None
        match.set_suggested_replacement(suggestion)
        return match


# --- date filters ---

def _get_day_of_week(day_str):
    """DateFilterHelper.getDayOfWeek(String)"""
    # quickfix for special characters like soft hyphens
    day = trim_special_characters(day_str).lower()
    if day.startswith('dom'):
        return SUNDAY
    if day.startswith('seg'):
        return MONDAY
    if day.startswith('ter'):
        return TUESDAY
    if day.startswith('qua'):
        return WEDNESDAY
    if day.startswith('qui'):
        return THURSDAY
    if day.startswith('sex'):
        return FRIDAY
    if day.startswith('sáb'):
        return SATURDAY
    raise RuntimeError("Could not find day of week for '" + day_str + "'")


_DAY_NAMES = {SUNDAY: 'domingo', MONDAY: 'segunda-feira', TUESDAY: 'terça-feira', WEDNESDAY: 'quarta-feira',
              THURSDAY: 'quinta-feira', FRIDAY: 'sexta-feira', SATURDAY: 'sábado'}


def _get_day_of_week_name(date):
    """DateFilterHelper.getDayOfWeek(Calendar)"""
    return _DAY_NAMES.get(date.day_of_week, '')


_MONTHS = (('jan', 1), ('fev', 2), ('mar', 3), ('abr', 4), ('mai', 5), ('jun', 6), ('jul', 7), ('ago', 8),
           ('set', 9), ('out', 10), ('nov', 11), ('dez', 12))


def _get_month(month_str):
    """DateFilterHelper.getMonth"""
    # quickfix for special characters like soft hyphens
    mon = trim_special_characters(month_str).lower()
    for prefix, month in _MONTHS:
        if mon.startswith(prefix):
            return month
    raise RuntimeError("Could not find month '" + month_str + "'")


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.pt.DateCheckFilter, the Portuguese
    localization of AbstractDateCheckWithSuggestionsFilter (with
    DateFilterHelper)."""

    def get_day_of_week(self, day_str):
        return _get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return _get_day_of_week_name(date)

    def get_month(self, month_str):
        return _get_month(month_str)

    def get_error_message_wrong_year(self):
        return 'Esta data está incorreta. Você está se referindo ao ano "{currentYear}"?'


class YMDDateCheckFilter(DateCheckFilter):
    """Port of org.languagetool.rules.pt.YMDDateCheckFilter: a date filter
    that expects a 'date' argument in the format 'yyyy-mm-dd'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for YMDDateCheckFilter")
        return super().accept_rule_match(match, YMDDateHelper.parse_date(args), pattern_token_pos, pattern_tokens,
                                         token_positions)


class FutureDateFilter(AbstractFutureDateFilter):
    """Port of org.languagetool.rules.pt.FutureDateFilter (with
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return _get_month(localized_month)


class NewYearDateFilter(AbstractNewYearDateFilter):
    """Port of org.languagetool.rules.pt.NewYearDateFilter (with
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return _get_month(localized_month)


class YMDNewYearDateFilter(NewYearDateFilter):
    """Port of org.languagetool.rules.pt.YMDNewYearDateFilter: a new year
    date filter that expects a 'date' argument in the format
    'yyyy-mm-dd'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for YMDDateCheckFilter")
        args = YMDDateHelper.parse_date(args)
        return super().accept_rule_match(YMDDateHelper.correct_date(match, args), args, pattern_token_pos,
                                         pattern_tokens, token_positions)
