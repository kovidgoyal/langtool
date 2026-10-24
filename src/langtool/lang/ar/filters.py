"""Arabic rule filters (port of org.languagetool.rules.ar.filters)."""

from ...rules.abstract_rules import _rules_file, load_simple_replace_data
from ...rules.base import RuleMatch
from ...rules.core_filters import AbstractAdvancedSynthesizerFilter, AbstractDateCheckFilter, java_parse_int
from ...rules.filters import RuleFilter
from ...tools import java_hash_set_copy_order, java_split, java_trim, trim_special_characters
from . import numbers
from .synthesis import inflect_adjective_tanwin_nasb, inflect_mafoul_mutlq
from .tagging import TAG_MANAGER
from .tools import TEH_MARBUTA, get_attached_pronoun


def _arabic(language):
    if language is not None:
        return language
    from ...api import get_language
    return get_language('ar')


def _load_from_path(language, path):
    """loadFromPath: SimpleReplaceDataLoader.loadWords of a file of the
    rules directory"""
    return load_simple_replace_data(_rules_file(language, path))


def _new_match(match):
    return RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message, match.short_message)


class ArabicAdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicAdvancedSynthesizerFilter
    (AbstractAdvancedSynthesizerFilter without changes)"""


# --- ArabicDateFilterHelper ---

SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY = range(1, 8)  # java.util.Calendar

_DAYS = {'السبت': SATURDAY, 'الأحد': SUNDAY, 'الإثنين': MONDAY, 'الاثنين': MONDAY, 'الثلاثاء': TUESDAY,
         'الأربعاء': WEDNESDAY, 'الخميس': THURSDAY, 'الجمعة': FRIDAY}
_DAY_NAMES = {SATURDAY: 'السبت', SUNDAY: 'الأحد', MONDAY: 'الإثنين', TUESDAY: 'الثلاثاء', WEDNESDAY: 'الأربعاء',
              THURSDAY: 'الخميس', FRIDAY: 'الجمعة'}
# the day names of the Arabic locale (Java's DateFormatSymbols, CLDR data)
_LOCALE_DAY_NAMES = {SUNDAY: 'الأحد', MONDAY: 'الاثنين', TUESDAY: 'الثلاثاء', WEDNESDAY: 'الأربعاء',
                     THURSDAY: 'الخميس', FRIDAY: 'الجمعة', SATURDAY: 'السبت'}
_MONTHS = {
    # the Syriac month names
    'كانون الثاني': 1, 'كانون ثاني': 1, 'شباط': 2, 'آذار': 3, 'نيسان': 4, 'أيار': 5, 'حزيران': 6, 'تموز': 7,
    'آب': 8, 'أيلول': 9, 'تشرين الأول': 10, 'تشرين الثاني': 11, 'كانون الأول': 12, 'تشرين ثاني': 11,
    'كانون أول': 12,
    # the month names from English
    'يناير': 1, 'فبراير': 2, 'مارس': 3, 'أبريل': 4, 'مايو': 5, 'يونيو': 6, 'يوليو': 7, 'أغسطس': 8, 'سبتمبر': 9,
    'أكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12,
    # the month names from French
    'جانفي': 1, 'جانفييه': 1, 'فيفري': 2, 'أفريل': 4, 'ماي': 5, 'جوان': 6, 'جويلية': 7, 'أوت': 8,
}


def get_day_of_week(day_str):
    """ArabicDateFilterHelper.getDayOfWeek (Calendar.SUNDAY is 1)"""
    d = _DAYS.get(day_str)
    if d is None:
        raise RuntimeError('No day name found for ' + day_str + "'")
    return d


def get_month(month_str):
    """ArabicDateFilterHelper.getMonth (January is 1)"""
    m = _MONTHS.get(trim_special_characters(month_str))
    if m is None:
        raise RuntimeError("No month name for '" + month_str + "'")
    return m


def get_day_of_week_name(day):
    """ArabicDateFilterHelper.getDayOfWeekName"""
    return _DAY_NAMES.get(day, 'غير محدد')


class ArabicDateCheckFilter(AbstractDateCheckFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicDateCheckFilter: the
    Arabic localization of AbstractDateCheckFilter (with
    ArabicDateFilterHelper). The real day of the date is named like
    Java's Calendar.getDisplayName for the Arabic locale."""

    def get_day_of_week(self, day_str):
        return get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return _LOCALE_DAY_NAMES[date.day_of_week]

    def get_day_of_week_name_for_day(self, day):
        """Java: getDayOfWeek(int)"""
        return get_day_of_week_name(day)

    def get_month(self, month_str):
        return get_month(month_str)


class ArabicDMYDateCheckFilter(ArabicDateCheckFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicDMYDateCheckFilter: a
    date filter that expects a 'date' argument in the format 'dd-mm-yyyy'"""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for ArabicDMYDateCheckFilter")
        date_string = self.get_required('date', args)
        parts = java_split(date_string, '-')
        if len(parts) != 3:
            raise RuntimeError("Expected date in format 'dd-mm-yyyy': '" + date_string + "'")
        args = dict(args)
        args['day'] = parts[0]
        args['month'] = parts[1]
        args['year'] = parts[2]
        return super().accept_rule_match(match, args, pattern_token_pos, pattern_tokens, token_positions)


class ArabicAdjectiveToExclamationFilter(RuleFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicAdjectiveToExclamationFilter:
    suggests the exclamation forms (/ar/arabic_adjective_exclamation.txt)
    of an adjective: "كم الولد جميل" -> "ما أجمل الولد". Note that the
    entries of the data file start with a space, so that (as in Java) the
    adjectives are not found."""

    FILE_NAME = '/ar/arabic_adjective_exclamation.txt'

    def __init__(self, language=None):
        super().__init__(language)
        self.adj2comp_list = _load_from_path(_arabic(language), self.FILE_NAME)

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        # this rule returns only the comparative according to the given adjective
        noun = arguments.get('noun')  # the second argument
        try:
            adj_token_index = java_parse_int(arguments.get('adj_pos')) - 1
        except (ValueError, TypeError) as e:
            raise RuntimeError('Error parsing adj_pos from : ' + str(arguments.get('adj_pos'))) from e
        # some cases can have multiple lemmas, but only adjective lemmas are used
        adj_lemmas = _arabic(self.language).tagger.get_lemmas(pattern_tokens[adj_token_index], 'adj')
        # get the comparatives of the adjectives
        comp_list = []
        for adj_lemma in adj_lemmas:
            comparative_list = self.adj2comp_list.get(adj_lemma)
            if comparative_list is not None:
                comp_list.extend(comparative_list)
        # remove duplicates
        comp_list = java_hash_set_copy_order(comp_list)
        new_match = _new_match(match)
        for sug in self.prepare_suggestions(comp_list, noun):
            new_match.add_suggested_replacement(sug)
        return new_match

    @classmethod
    def prepare_suggestions(cls, comp_list, noun):
        """the suggestions for a list of comparatives (Java's
        prepareSuggestions(List, String))"""
        sug_list = []
        for comp in comp_list:
            sug_list.extend(cls.prepare_suggestions_for(comp, noun))
        return sug_list

    @classmethod
    def prepare_suggestions_for(cls, comp, noun):
        """Java's prepareSuggestions(String, String). The cases:
        a noun: كم الولد جميل ==> ما أجمل الولد, أجمل بالولد;
        a pronoun: كم هو جميل ==> ما أجمله, أجمل به;
        a non-trilateral adjective with a noun: كم الطالب شديد الاستيعاب ==>
        ما أشد استيعاب الطالب, أشدد باستيعابه;
        with a pronoun: كم هو شديد الاستيعاب ==> ما أشد استيعابه, أشد باستيعابه"""
        suggestion = comp
        if noun is None or noun == '':
            pass
        elif cls._is_pronoun(noun):
            # no space adding
            suggestion += get_attached_pronoun(noun)
        else:
            # if the comparative is of the second form don't add a space
            if not comp.endswith(' ب'):
                suggestion += ' '
            suggestion += noun
        return [suggestion]

    @staticmethod
    def _is_pronoun(word):
        """test if the word is an isolated pronoun"""
        return word in ('هو', 'هي', 'هم', 'هما', 'أنا')

    @classmethod
    def get_data_file_path(cls):
        return cls.FILE_NAME


class ArabicMasdarToVerbFilter(RuleFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicMasdarToVerbFilter:
    "قام بالأكل" -> "أكل": replaces the masdar after the auxiliary verb قام by
    its verb (/ar/arabic_masdar_verb.txt), inflected like the auxiliary
    verb."""

    FILE_NAME = '/ar/arabic_masdar_verb.txt'
    AUTHORIZE_LEMMA = ('قَامَ',)

    def __init__(self, language=None):
        super().__init__(language)
        self.masdar2verb_list = _load_from_path(_arabic(language), self.FILE_NAME)

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        # first token: the auxiliary verb Qam, second token: the masdar
        language = _arabic(self.language)
        tagger = language.tagger
        synthesizer = language.synthesizer
        # some cases can have multiple lemmas, but only auxiliary lemmas are used
        aux_verb_lemmas = self.filter_lemmas(tagger.get_lemmas(pattern_tokens[0], 'verb'))
        # all lemmas of the masdar
        masdar_lemmas = tagger.get_lemmas(pattern_tokens[1], 'masdar')
        verb_list = []
        for aux_verb_token in pattern_tokens[0].readings:
            # if the token has an authorized lemma
            if aux_verb_token.lemma in aux_verb_lemmas:
                for lemma in masdar_lemmas:
                    verb_lemma_list = self.masdar2verb_list.get(lemma)
                    if verb_lemma_list is not None:
                        # inflect the verb according to the auxiliary verb inflection
                        for vrb_lem in verb_lemma_list:
                            verb_list.extend(synthesizer.inflect_lemma_like(vrb_lem, aux_verb_token))
        # remove duplicates
        verb_list = java_hash_set_copy_order(verb_list)
        new_match = _new_match(match)
        for verb in verb_list:
            new_match.add_suggested_replacement(verb)
        return new_match

    def filter_lemmas(self, lemmas):
        return [lem for lem in self.AUTHORIZE_LEMMA if lem in lemmas]


class ArabicVerbToMafoulMutlaqFilter(RuleFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicVerbToMafoulMutlaqFilter:
    "يعمل بطريقة جيدة" -> "يعمل عملًا جيدًا": suggests the verb with its
    masdar (/ar/arabic_verb_masdar.txt) as Mafoul Mutlaq and the adjective,
    both with tanwin nasb."""

    FILE_NAME = '/ar/arabic_verb_masdar.txt'

    def __init__(self, language=None):
        super().__init__(language)
        self.verb2masdar_list = _load_from_path(_arabic(language), self.FILE_NAME)

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        verb = arguments.get('verb')
        verb_lemmas = _arabic(self.language).tagger.get_lemmas(pattern_tokens[0], 'verb')
        adj = arguments.get('adj')
        # generate multiple masdars from the verb lemmas
        inflected_masdar_list = []
        inflected_adj_list = []
        inflected_adj_masculine = inflect_adjective_tanwin_nasb(adj, False)
        inflected_adj_feminin = inflect_adjective_tanwin_nasb(adj, True)
        for lemma in verb_lemmas:
            # get the suggested masdar lemmas
            msdr_lemma_list = self.verb2masdar_list.get(lemma)
            if msdr_lemma_list is not None:
                for msdr in msdr_lemma_list:
                    if msdr is not None:
                        inflected_masdar_list.append(inflect_mafoul_mutlq(msdr))
                        inflected_adj_list.append(inflected_adj_feminin if msdr.endswith(TEH_MARBUTA)
                                                  else inflected_adj_masculine)
        new_match = _new_match(match)
        suggestion_phrases = []
        for msdr, inflected_adj in zip(inflected_masdar_list, inflected_adj_list):
            sug_phrase = str(verb) + ' ' + msdr + ' ' + str(inflected_adj)
            # avoid redundancy
            if sug_phrase not in suggestion_phrases:
                new_match.add_suggested_replacement(sug_phrase)
                suggestion_phrases.append(sug_phrase)
        return new_match


class ArabicNumberPhraseFilter(RuleFilter):
    """Port of org.languagetool.rules.ar.filters.ArabicNumberPhraseFilter:
    suggests the correct form of a numeric phrase (with its unit, if the
    argument 'next' is given) according to the inflection given by the
    argument 'inflect' or by the previous word (a preposition: jar)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        # the previous word
        previous_word = arguments.get('previous', '')
        # the previous word index in the token list
        previous_word_pos = self._get_previous_pos(arguments)
        # the inflection mark
        inflect_arg = arguments.get('inflect', '')
        # the next word as unit
        next_word = arguments.get('next', '')
        next_word_pos = self._get_next_pos(arguments, len(pattern_tokens))
        # get all numeric tokens
        start_pos = previous_word_pos + 1 if previous_word_pos > 0 else 0
        end_pos = min(next_word_pos, len(pattern_tokens)) if next_word_pos > 0 else len(pattern_tokens) + next_word_pos
        num_phrase = ' '.join(java_trim(pattern_tokens[i].token) for i in range(start_pos, end_pos))
        # extract the features from the previous word
        feminine = False
        attached = False
        inflection = self._get_inflected_case(pattern_tokens, previous_word_pos, inflect_arg)
        if not next_word:
            suggestion_list = self.prepare_suggestion(num_phrase, previous_word, None, feminine, attached, inflection)
        else:
            next_word_token = None
            if 0 < end_pos < len(pattern_tokens):
                next_word_token = pattern_tokens[end_pos]
            suggestion_list = self.prepare_suggestion_with_units(num_phrase, previous_word, next_word_token, feminine,
                                                                 attached, inflection)
        new_match = _new_match(match)
        for sug in suggestion_list:
            new_match.add_suggested_replacement(sug)
        return new_match

    @staticmethod
    def _get_inflected_case(pattern_tokens, previous_pos, inflect):
        """the inflection case"""
        if inflect != '':
            return inflect
        # if the previous word is a jar
        if 0 <= previous_pos < len(pattern_tokens):
            for tk in pattern_tokens[previous_pos].readings:
                if tk.pos_tag is not None and tk.pos_tag.startswith('PR'):
                    return 'jar'
        first_word = pattern_tokens[previous_pos + 1].token
        if first_word.startswith('ب') or first_word.startswith('ل') or first_word.startswith('ك'):
            return 'jar'
        return ''

    @staticmethod
    def _get_feminin_case(pattern_tokens, next_pos):
        """getFemininCase (unused in Java)"""
        return any(TAG_MANAGER.is_feminin(tk.pos_tag) for tk in pattern_tokens[next_pos].readings)

    @staticmethod
    def prepare_suggestion(num_phrase, previous_word, next_word, feminin, attached, inflection):
        """the suggestions for a numeric phrase"""
        suggestion_list = []
        for sug in numbers.get_suggestions_numeric_phrase(num_phrase, feminin, attached, inflection):
            if previous_word:
                suggestion_list.append(previous_word + ' ' + sug)
        return suggestion_list

    def prepare_suggestion_with_units(self, num_phrase, previous_word, next_word, feminin, attached, inflection):
        """the suggestions for a numeric phrase with a unit"""
        default_unit = 'دينار'
        suggestion_list = []
        for sug_map in numbers.get_suggestions_numeric_phrase_with_units(num_phrase, default_unit, feminin, attached,
                                                                         inflection):
            sug = sug_map.get('phrase')
            inflected_unit_list = self._inflect_unit(next_word, sug_map)
            if inflected_unit_list is None:
                # Java: a NullPointerException (no unit token)
                raise TypeError('no unit token')
            for unit in inflected_unit_list:
                tmp = ''
                if previous_word:
                    tmp += previous_word + ' '
                tmp += sug
                if unit:
                    tmp += ' ' + unit
                suggestion_list.append(tmp)
        return suggestion_list

    def _inflect_unit(self, unit, sug_map):
        """the suitable forms of the unit"""
        if unit is None:
            return None
        tm = TAG_MANAGER
        synthesizer = _arabic(self.language).synthesizer
        inflection = sug_map.get('unitInflection', '')
        number = sug_map.get('unitNumber', '')
        tmp_list = []
        inflected_list = []
        for tk in unit.readings:
            postag = tk.pos_tag
            if tm.is_noun(postag) and not tm.is_definite(postag) and not tm.has_pronoun(postag):
                # add the inflection flag
                if inflection == 'jar':
                    postag = tm.set_majrour(postag)
                elif inflection == 'nasb':
                    postag = tm.set_mansoub(postag)
                else:  # raf3 and the others
                    postag = tm.set_marfou3(postag)
                # add the number flag
                if number == 'two':
                    postag = tm.set_dual(postag)
                elif number == 'plural':
                    postag = tm.set_plural(postag)
                else:  # one and the others
                    postag = tm.set_single(postag)
                # add tanwin
                if number == 'one' and inflection == 'nasb':
                    postag = tm.set_tanwin(postag)
                # for each postag generate a new token
                if postag not in tmp_list:
                    tmp_list.append(postag)
                    inflected_list.extend(synthesizer.synthesize(tk, postag))
        return inflected_list

    @staticmethod
    def _get_previous_pos(args):
        previous_word_pos = 0
        if args.get('previousPos') is not None:
            try:
                previous_word_pos = java_parse_int(args.get('previousPos')) - 1
            except ValueError:
                previous_word_pos = -1
        return previous_word_pos

    @staticmethod
    def _get_next_pos(args, size):
        try:
            next_pos = java_parse_int(args.get('nextPos', '0'))
            # the next token is indexed with a negative offset
            if next_pos < 0:
                next_pos = size + next_pos
        except ValueError:
            next_pos = 0
        return next_pos
