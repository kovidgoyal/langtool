"""Russian specific rules (port of org.languagetool.rules.ru).

The Java rules lowercase with the default locale or Locale("ru"), which
have no special case mapping for Russian (str.lower here)."""

import os
import threading

from ... import jregex
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractDashRule, AbstractFillerWordsRule,
                                     AbstractSimpleReplaceRule2, AbstractWordCoherencyRule, AdvancedWordRepeatRule,
                                     load_compound_rule_data)
from ...rules.base import Category, Rule, RuleMatch
from ...rules.core import Categories, GenericUnpairedBracketsRule, WordRepeatRule
from ...tools import is_all_uppercase, java_split, starts_with_uppercase


def _russian():
    """Russian.getInstance(), the language of the rules whose Java
    constructors only get the messages"""
    from ...api import get_language
    return get_language('ru')


class RussianCompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.ru.RussianCompoundRule: compounds
    (listed in /ru/compounds.txt) that are not written as separate words."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Эти слова должны быть написаны через дефис.',
                         'Эти слова должны быть написаны слитно.',
                         'Эти слова могут быть написаны через дефис или слитно.')
        self.add_example_pair('Собрание состоится в <marker>конференц зале</marker>.',
                              'Собрание состоится в <marker>конференц-зале</marker>.')
        self.sentence_starts_with_upper_case = True

    def get_id(self):
        return 'RU_COMPOUNDS'

    def get_description(self):
        return 'Правописание через дефис'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/ru/compounds.txt')


_CYRILLIC = jregex.compile('[Ѐ-ӿ]')


class RussianDashRule(AbstractDashRule):
    """Port of org.languagetool.rules.ru.RussianDashRule: compounds written
    with dashes instead of hyphens (/ru/compounds.txt)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _russian())
        self.tags = []

    def get_id(self):
        return 'RU_DASH_RULE'

    def get_description(self):
        return 'Тире вместо дефиса («из — за» вместо «из-за»).'

    def get_message(self):
        return 'Использовано тире вместо дефиса.'

    def is_boundary(self, s):
        return _CYRILLIC.fullmatch(s) is None

    def get_compounds_data(self):
        return self.load_compound_file('/ru/compounds.txt')


_FILLER_WORDS = frozenset(('ах', 'аа', 'ааа', 'аааа', 'ау', 'бу', 'вау', 'ох', 'однако', 'эээ', 'э', 'эй', 'эх',
                           'ух-ты', 'ух'))


class RussianFillerWordsRule(AbstractFillerWordsRule):
    """Port of org.languagetool.rules.ru.RussianFillerWordsRule: hints about
    the use of Russian filler words, given when the percentage of filler
    words per paragraph exceeds the limit (default off)."""

    def get_id(self):
        return AbstractFillerWordsRule.rule_id + '_RU'

    def is_filler_word(self, token):
        return token in _FILLER_WORDS

    def is_exception(self, tokens, num):
        return False


RUSSIAN_SIMPLE_REPLACE_RULE = 'RU_SIMPLE_REPLACE'


class RussianSimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.ru.RussianSimpleReplaceRule:
    colloquialisms and wrong phrases of /ru/replace.txt. (getLocale()
    returns Locale("ru"); AbstractSimpleReplaceRule2 does not use it.)"""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Category('MISC', 'Общие правила')
        self.add_example_pair(
            '<marker>Экспрессо</marker> – крепкий кофе, приготовленный из хорошо обжаренных и тонко помолотых '
            'кофейных зёрен.',
            '<marker>Эспрессо</marker> – крепкий кофе, приготовленный из хорошо обжаренных и тонко помолотых '
            'кофейных зёрен.')

    def get_file_names(self):
        return ['/ru/replace.txt']

    def get_id(self):
        return RUSSIAN_SIMPLE_REPLACE_RULE

    def get_description(self):
        return 'Поиск просторечий и ошибочных фраз'

    def get_short(self):
        return 'Ошибка?'

    def get_message(self):
        return '«$match» — просторечие, исправление: $suggestions'


_LETTER = jregex.compile('[a-zA-Zа-яёА-ЯЁ]')


class RussianSimpleWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.ru.RussianSimpleWordRepeatRule: the
    WordRepeatRule without false alarms for "-", "и", "по", "что", "ПО по"
    and single letters ("L L")."""

    def ignore(self, tokens, position):
        if self.word_repetition_of('-', tokens, position):
            return True
        if self.word_repetition_of('и', tokens, position):
            return True
        if self.word_repetition_of('по', tokens, position):
            return True
        if tokens[position - 1].token == 'ПО' and tokens[position].token == 'по':
            return True  # "ПО по"
        if tokens[position - 1].token == 'по' and tokens[position].token == 'ПО':
            return True  # "по ПО"
        if self.word_repetition_of('что', tokens, position):
            return True
        if (_LETTER.fullmatch(tokens[position].token) and position > 1
                and _LETTER.fullmatch(tokens[position - 1].token)):
            # spelling with spaces in between: "L L"
            return True
        return super().ignore(tokens, position)


_phrases = None
_phrases_lock = threading.Lock()


def _specific_case_data(language):
    """(maxLen, lcToProperSpelling) of RussianSpecificCaseRule, loaded from
    /ru/specific_case.txt"""
    global _phrases
    with _phrases_lock:
        if _phrases is None:
            max_len = 0
            phrases = []
            with open(os.path.join(language.resource_dir, 'specific_case.txt'), encoding='utf-8') as f:
                for line in f.read().splitlines():
                    if not line or line.startswith('#'):
                        continue
                    max_len = max(len(java_split(line, ' ')), max_len)
                    phrases.append(line.strip())
            lc_to_proper_spelling = {}
            for phrase in dict.fromkeys(phrases):
                lc_to_proper_spelling[phrase.lower()] = phrase
            _phrases = (max_len, lc_to_proper_spelling)
        return _phrases


class RussianSpecificCaseRule(Rule):
    """Port of org.languagetool.rules.ru.RussianSpecificCaseRule (based on
    the English SpecificCaseRule): phrases of /ru/specific_case.txt that
    need a specific upper/lowercase spelling."""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.language = language or _russian()
        self.category = Categories.get('CASING', messages)
        self.loc_quality_issue_type = 'Misspelling'
        self.add_example_pair('Река <marker>рытый банк</marker> находится в Прикаспийской низменности.',
                              'Река <marker>Рытый Банк</marker> находится в Прикаспийской низменности')

    def get_id(self):
        return 'RU_SPECIFIC_CASE'

    def get_description(self):
        return 'Написание специальных наименований в верхнем или нижнем регистре'

    def match(self, sentence):
        max_len, lc_to_proper_spelling = _specific_case_data(self.language)
        matches = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        for i in range(n):
            words = []
            j = 0
            while len(words) < max_len and i + j < n:
                words.append(tokens[i + j].token)
                j += 1
                phrase = ' '.join(words)
                proper_spelling = lc_to_proper_spelling.get(phrase.lower())
                if proper_spelling is not None and not is_all_uppercase(phrase) and phrase != proper_spelling:
                    if i > 0 and tokens[i - 1].is_sentence_start and not starts_with_uppercase(proper_spelling):
                        # avoid suggesting e.g. "vitamin C" at sentence start:
                        continue
                    if self._all_words_uppercase(proper_spelling):
                        msg = 'Для специальных наименований используйте начальную заглавную букву.'
                    else:
                        msg = 'Для специальных наименований используйте предложенное написание заглавных и строчных ' \
                              'букв.'
                    match = RuleMatch(self, sentence, tokens[i].start_pos, tokens[i + j - 1].end_pos, msg)
                    match.set_suggested_replacement(proper_spelling)
                    matches.append(match)
        return matches

    @staticmethod
    def _all_words_uppercase(s):
        return all(starts_with_uppercase(w) for w in java_split(s, ' '))


RU_START_SYMBOLS = ['(', '{', '„', '"', "'", '“']
RU_END_SYMBOLS = [')', '}', '“', '"', "'", '”']

NUMERALS_RU = ("(?i)\\d{1,2}?[а-я]*|[а-я]|[А-Я]|[а-я][а-я]|[А-Я][А-Я]|(?i)\\d{1,2}?[a-z']*|"
               "M*(D?C{0,3}|C[DM])(L?X{0,3}|X[LC])(V?I{0,3}|I[VX])$")


class RussianUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.ru.RussianUnpairedBracketsRule."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, RU_START_SYMBOLS, RU_END_SYMBOLS, numerals=NUMERALS_RU)
        self.add_example_pair(
            'Самоотверженный поступок Оленина <marker>(</marker>подарок Лукашке коня вызывает лишь удивление и '
            'усиливает недоверие к нему станичников.',
            'Самоотверженный поступок Оленина <marker>(</marker>подарок Лукашке коня) вызывает лишь удивление и '
            'усиливает недоверие к нему станичников.')

    def get_id(self):
        return 'RU_UNPAIRED_BRACKETS'


_PRONOUN = jregex.compile('PNN:(.*):Nom:(.*)')
_FUT_REAL_VERB = jregex.compile('VB:(Fut|Real):(.*):(.*):(.*):(.*)')
_PAST_VERB = jregex.compile('VB:Past:(.*):(.*):(.*)')


class RussianVerbConjugationRule(Rule):
    """Port of org.languagetool.rules.ru.RussianVerbConjugationRule: the
    agreement of personal pronouns with the following verb (person and
    number in the present and future tense, gender and number in the past
    tense), checked with the first reading of the tokens."""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.language = language or _russian()
        self.category = Categories.get('GRAMMAR', messages)
        self.add_example_pair('<marker>Я идёт</marker>.', '<marker>Я иду</marker>.')

    def get_id(self):
        return 'RU_VERB_CONJUGATION'

    def get_description(self):
        return 'Согласование личных местоимений с глаголами'

    def match(self, sentence):
        rule_matches = []
        token_readings = sentence.non_blank_tokens
        n = len(token_readings)
        for i in range(1, n - 1):
            previous_reading = token_readings[i - 1]
            current_reading = token_readings[i]
            next_reading = token_readings[i + 1]
            previous_token = previous_reading.readings[0].token
            current_lemma_tok = current_reading.readings[0]
            current_token = current_lemma_tok.token
            current_pos_tag = current_lemma_tok.pos_tag
            if current_token and current_pos_tag:
                pronoun_matcher = _PRONOUN.search(current_pos_tag)
                if pronoun_matcher and previous_token != 'и':
                    pronoun_pair = (pronoun_matcher.group(1), pronoun_matcher.group(2))
                    next_lemma_tok = next_reading.readings[0]
                    if i < n - 2:
                        next2_token = token_readings[i + 2].readings[0].token
                    else:
                        next2_token = ''
                    next_token = next_lemma_tok.token
                    next_pos_tag = next_lemma_tok.pos_tag
                    if (next_pos_tag and not (next2_token == 'быть' and next_token == 'может')
                            and next_token != 'целую'):  # "может быть"
                        verb_matcher = _FUT_REAL_VERB.search(next_pos_tag)
                        if verb_matcher:
                            verb_pair = (verb_matcher.group(4), verb_matcher.group(5))
                            if self._is_conjugation_in_present_or_future_wrong(pronoun_pair, verb_pair):
                                self._add_rule_match(rule_matches, current_reading, next_reading, sentence)
                        else:
                            verb_matcher = _PAST_VERB.search(next_pos_tag)
                            if verb_matcher:
                                if self._is_conjugation_in_past_wrong(pronoun_matcher.group(1),
                                                                      verb_matcher.group(3)):
                                    self._add_rule_match(rule_matches, current_reading, next_reading, sentence)
        return rule_matches

    @staticmethod
    def _is_conjugation_in_present_or_future_wrong(pronoun, verb):
        if pronoun[1] != verb[1]:
            return True
        if pronoun[0] in ('Masc', 'Fem', 'Neut'):
            return verb[0] == 'PL'
        return pronoun[0] != verb[0]

    @staticmethod
    def _is_conjugation_in_past_wrong(pronoun, verb):
        if pronoun == 'Sin':
            return verb in ('PL', 'Neut')
        return pronoun != verb

    def _add_rule_match(self, rule_matches, current_reading, next_reading, sentence):
        rule_matches.append(RuleMatch(self, sentence, current_reading.start_pos, next_reading.end_pos,
                                      'Неверное спряжение глагола или неверное местоимение', self.get_short()))

    def get_short(self):
        return 'Неверное спряжение глагола'


class RussianWordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.ru.RussianWordCoherencyRule: words
    with more than one permitted spelling (/ru/coherency.txt) should be
    written consistently."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _russian())
        self.add_example_pair(
            'Понятие «оффлайн» тоже имеет английские корни и связано со словом «offline», что означает «вне сети». '
            'Принтер перешёл в состояние <marker>офлайн</marker>.',
            'Понятие «оффлайн» тоже имеет английские корни и связано со словом «offline», что означает «вне сети». '
            'Принтер перешёл в состояние <marker>оффлайн</marker>.')

    def get_word_map(self):
        return self.load_word_map('/ru/coherency.txt')

    def get_message(self, word1, word2):
        return '«' + word1 + '» и «' + word2 + '» не следует использовать одновременно'

    def get_id(self):
        return 'RU_WORD_COHERENCY'

    def get_description(self):
        return 'Единообразное написание слов с более чем одним допустимым написанием'


# Excluded dictionary words.
_EXC_WORDS = frozenset(('не', 'ни', 'а', 'их', 'на', 'в', 'по', 'минута', 'друг', 'час', 'секунда', 'ПАО', 'ООО',
                        'табл', 'рис'))

# Excluded part of speech classes.
_EXC_POS = jregex.compile('INTERJECTION|PRDC|PREP|CONJ|PARTICLE|ABR|NumC:.*|Num:.*')

# Excluded non-words (special symbols, Roman numerals etc.)
_EXC_NONWORDS = jregex.compile('&quot|&gt|&lt|&amp|[0-9].*|'
                               'M*(D?C{0,3}|C[DM])(L?X{0,3}|X[LC])(V?I{0,3}|I[VX])$')


class RussianWordRepeatRule(AdvancedWordRepeatRule):
    """Port of org.languagetool.rules.ru.RussianWordRepeatRule: repeated
    lemmas in a sentence."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _russian())
        self.add_example_pair('Всё смешалось в <marker>доме доме</marker> Облонских.',
                              'Всё смешалось в <marker>доме</marker> Облонских.')

    def get_id(self):
        return 'RU_WORD_REPEAT'

    def get_description(self):
        return 'Повтор слов в предложении'

    def get_excluded_words_pattern(self):
        return _EXC_WORDS

    def get_excluded_non_words_pattern(self):
        return _EXC_NONWORDS

    def get_excluded_pos(self):
        return _EXC_POS

    def get_message(self):
        return 'Повтор слов в предложении'

    def get_short_message(self):
        return 'Повтор слов в предложении'


class RussianWordRootRepeatRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.ru.RussianWordRootRepeatRule: words of
    different parts of speech with the same root in a text
    (/ru/wordrootrep.txt), default off."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _russian())
        self.set_default_off()
        self.add_example_pair(
            'Абрикос рос в саду. У меня на столе стоит <marker>абрикосный</marker> сок.',
            'Абрикос рос в саду. У меня на столе стоит сок из <marker>абрикосов</marker>.')

    def get_word_map(self):
        return self.load_word_map('/ru/wordrootrep.txt')

    def get_message(self, word1, word2):
        return '«' + word1 + '» и «' + word2 + '» – однокоренные слова, их не стоит использовать одновременно'

    def get_id(self):
        return 'RU_WORD_ROOT_REPEAT'

    def get_description(self):
        return 'Повтор однокоренных слов'
