"""Ports of the Ukrainian rules of org.languagetool.rules.uk:
UkrainianCommaWhitespaceRule, UkrainianUppercaseSentenceStartRule,
UkrainianWordRepeatRule, TypographyRule, HiddenCharacterRule,
MissingHyphenRule, MixedAlphabetsRule and PunctuationCheckRule (with the
core AbstractPunctuationCheckRule in langtool.rules.abstract_rules)."""

from ... import jregex
from ...analysis import SENTENCE_END_TAGNAME
from ...rules.abstract_rules import AbstractPunctuationCheckRule
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories, CommaWhitespaceRule, UppercaseSentenceStartRule, WordRepeatRule
from ...tools import is_upper_case, java_equals_ignore_case, lowercase_first_char
from . import helpers
from . import pos_tag_helper as pth


class UkrainianCommaWhitespaceRule(CommaWhitespaceRule):
    """Port of UkrainianCommaWhitespaceRule: em and en dashes are
    exceptions"""

    def is_exception(self, tokens, i):
        token = tokens[i].token
        if token == '—' or token == '–':
            return True
        return super().is_exception(tokens, i)


_LIST_LETTER = jregex.compile('[а-яіїєґ]')


class UkrainianUppercaseSentenceStartRule(UppercaseSentenceStartRule):
    """Port of UkrainianUppercaseSentenceStartRule: list items like а) б) в)
    are exceptions"""

    def is_exception(self, tokens, i):
        # list, e.g. а) б) в)
        if i == 1 and i < len(tokens) - 1 and _LIST_LETTER.fullmatch(tokens[i].get_clean_token()) \
                and tokens[i + 1].token == ')':
            return True
        return False


_DATE_TIME_NUM_PATTERN = jregex.compile('date|time|number.*')
_REPEAT_ALLOWED_SET = frozenset(('ст.',))
_REPEAT_ALLOWED_CAPS_SET = frozenset(('Джей', 'Бі', 'Сі', 'Ла'))


class UkrainianWordRepeatRule(WordRepeatRule):
    """Port of UkrainianWordRepeatRule"""

    rule_id = 'UKRAINIAN_WORD_REPEAT_RULE'

    def ignore(self, tokens, position):
        atr = tokens[position]
        token = atr.token
        # від добра добра не шукають
        if position > 2 and token == 'добра' and java_equals_ignore_case(tokens[position - 2].token, 'від'):
            return True
        # Тому що що?
        if position > 1 and token == 'що' and java_equals_ignore_case(tokens[position - 2].token, 'тому'):
            return True
        # ні так, ні ні
        if position > 3 and token == 'ні' and tokens[position - 2].token == ',' \
                and java_equals_ignore_case(tokens[position - 3].token, 'так'):
            return True
        if token.lower() in _REPEAT_ALLOWED_SET:
            return True
        if token in _REPEAT_ALLOWED_CAPS_SET:
            return True
        if pth.has_pos_tag(atr, _DATE_TIME_NUM_PATTERN):
            return True
        for r in atr.readings:
            pos_tag = r.pos_tag
            if pos_tag is not None:
                if not self._is_initial(r, tokens, position) and pos_tag != SENTENCE_END_TAGNAME:
                    return False
        return True

    @staticmethod
    def _is_initial(analyzed_token, tokens, position):
        return ('abbr' in analyzed_token.pos_tag
                or (len(analyzed_token.token) == 1 and is_upper_case(analyzed_token.token[0])
                    and position < len(tokens) - 1 and tokens[position + 1].token == '.'))

    def create_rule_match(self, prev, token, prev_pos, pos, msg, sentence):
        double_i = prev == 'І' and token == 'і'
        if double_i:
            msg += ' або, можливо, перша І має бути латинською.'
        rm = super().create_rule_match(prev, token, prev_pos, pos, msg, sentence)
        if double_i:
            replacements = list(rm.suggested_replacements)
            replacements.append('I і')
            rm.set_suggested_replacements(replacements)
        return rm


_HIDDEN_CHAR = '\u00AD'  # soft hyphen


class HiddenCharacterRule(Rule):
    """Port of HiddenCharacterRule: finds soft hyphens in words"""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.category = Categories.get('MISC', messages)

    def get_id(self):
        return 'UK_HIDDEN_CHARS'

    def get_description(self):
        return 'Приховані символи: знак м’якого перенесення'

    def get_short(self):
        return 'Приховані символи'

    def get_suggestion(self, word):
        highlighted = word.replace(_HIDDEN_CHAR, '-')
        return ' містить невидимий знак м’якого перенесення: «' + highlighted + '», виправлення: '

    def match(self, sentence):
        out = []
        for atr in sentence.get_tokens_without_whitespace():
            if _HIDDEN_CHAR in atr.token:
                out.append(self._create_rule_match(atr, sentence))
        return out

    def _create_rule_match(self, atr, sentence):
        token = atr.token
        replacement = token.replace(_HIDDEN_CHAR, '')
        msg = token + self.get_suggestion(token) + replacement
        rm = RuleMatch(self, sentence, atr.start_pos, atr.end_pos, msg, self.get_short())
        rm.set_suggested_replacements([replacement])
        return rm


_TYPO_PATTERN = jregex.compile('.*[а-яїієґА-ЯІЇЄҐ].*')
_SHORT_DASH_WORD = jregex.compile("[а-яіїєґ']{2,}([–—][а-яіїєґ']{2,})+", jregex.IGNORECASE)
_BAD_LATIN = jregex.compile('[ХІXIV]+[–—][ХІXIV]+')
_DASHES = jregex.compile('[–—]')
_TYPO_MSG = 'Риска всередині слова. Всередині слова вживайте дефіс, між словами виокремлюйте риску пробілами.'


class TypographyRule(Rule):
    """Port of TypographyRule: short dash inside words"""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.category = Categories.get('TYPOGRAPHY', messages)

    def get_id(self):
        return 'DASH'

    def get_description(self):
        return 'Коротка риска замість дефісу'

    def get_short(self):
        return 'Коротка риска'

    def match(self, sentence):
        out = []
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        for i in range(1, n):
            short_dash_token = self._short_dash_token(tokens[i])
            if short_dash_token is not None:
                replacements = [_DASHES.sub('-', short_dash_token), _DASHES.sub(' — ', short_dash_token)]
                # Правопис 2019 § 161. ТИРЕ (—), пп. 12-15
                rm = RuleMatch(self, sentence, tokens[i].start_pos, tokens[i].end_pos, _TYPO_MSG, self.get_short())
                rm.set_suggested_replacements(replacements)
                out.append(rm)
            elif tokens[i].token in ('—', '–'):
                no_space_left = i > 1 and not tokens[i].whitespace_before and tokens[i - 1].token != ',' \
                    and tokens[i - 1].token != '«'
                no_space_right = i < n - 1 and not tokens[i + 1].whitespace_before and tokens[i + 1].token != '>'
                if no_space_left or no_space_right:
                    if i > 1 and self._is_number(tokens[i - 1]) and i < n - 1 and self._is_number(tokens[i + 1]):
                        continue
                    replacements = []
                    if i > 1 and i < n - 1 and _TYPO_PATTERN.fullmatch(tokens[i - 1].token) \
                            and _TYPO_PATTERN.fullmatch(tokens[i + 1].token):
                        replacements.append(tokens[i - 1].token + '-' + tokens[i + 1].token)
                    repl = ''
                    if i > 1:
                        repl = tokens[i - 1].token + ' '
                        start_pos = tokens[i - 1].start_pos
                    else:
                        start_pos = tokens[i].start_pos
                    repl += '—'
                    if i < n - 1:
                        repl += ' ' + tokens[i + 1].token
                        end_pos = tokens[i + 1].start_pos
                    else:
                        end_pos = tokens[i].end_pos
                    replacements.append(repl)
                    # Правопис 2019 § 161. ТИРЕ (—), пп. 12-15
                    rm = RuleMatch(self, sentence, start_pos, end_pos, _TYPO_MSG, self.get_short())
                    rm.set_suggested_replacements(replacements)
                    out.append(rm)
        return out

    @staticmethod
    def _is_number(atr):
        return pth.has_pos_tag_start(atr, 'number')

    @staticmethod
    def _short_dash_token(atr):
        readings = atr.readings
        if not readings or atr.token is None:
            return None
        last = readings[-1].token
        if last is not None and (last.find('–') > 0 or last.find('—') > 0) \
                and _SHORT_DASH_WORD.fullmatch(last) and not _BAD_LATIN.fullmatch(last):
            return last
        return None


_UA_1992_TAG_PART = ':alt'
_ALL_LOWER = jregex.compile("[а-яіїєґ'-]+")
_MEDIA_NEXT = jregex.compile('країни|півострова')
_missing_hyphen_prefixes = None


def _dash_prefixes():
    global _missing_hyphen_prefixes
    if _missing_hyphen_prefixes is None:
        m = helpers.load_map('/uk/dash_prefixes.txt')
        # these two generate too many false positives
        m.pop('блок', None)
        m.pop('рейтинг', None)
        _missing_hyphen_prefixes = {k: v for k, v in m.items() if _ALL_LOWER.fullmatch(k) and ':bad' not in v}
    return _missing_hyphen_prefixes


class MissingHyphenRule(Rule):
    """Port of MissingHyphenRule: a missing hyphen after a prefix of
    dash_prefixes.txt (or a superfluous space after a prefix written
    together in the 2019 orthography)"""

    def __init__(self, messages, word_tagger):
        super().__init__()
        self.messages = messages
        self.category = Categories.get('MISC', messages)
        self.loc_quality_issue_type = 'Misspelling'
        self.word_tagger = word_tagger

    def get_id(self):
        return 'UK_MISSING_HYPHEN'

    def get_description(self):
        return 'Пропущений дефіс'

    def match(self, sentence):
        out = []
        tokens = sentence.get_tokens_without_whitespace()
        for i in range(1, len(tokens) - 1):
            atr = tokens[i]
            next_atr = tokens[i + 1]
            if pth.has_pos_tag_start(next_atr, 'noun') and not pth.has_pos_tag_part(next_atr, 'pron') \
                    and _ALL_LOWER.fullmatch(next_atr.get_clean_token()):
                is_capitalized = helpers.is_capitalized(atr.get_clean_token())
                extra_tag = self._get_prefix_extra_tag(atr, is_capitalized)
                if extra_tag is not None or (atr.get_clean_token().lower() == 'тайм'
                                             and helpers.has_lemma(next_atr, 'аут')):
                    # всі медіа країни
                    if java_equals_ignore_case('медіа', atr.get_clean_token()) \
                            and _MEDIA_NEXT.fullmatch(next_atr.get_clean_token()):
                        continue
                    # до шоу поп-діви
                    if java_equals_ignore_case('шоу', atr.get_clean_token()) and '-' in next_atr.get_clean_token():
                        continue
                    if extra_tag == _UA_1992_TAG_PART:
                        suggested = '%s%s' % (atr.token, next_atr.token)
                        message = 'Можливо, зайвий пробіл?'
                    else:
                        suggested = '%s-%s' % (atr.token, next_atr.token)
                        message = 'Можливо, пропущено дефіс?'
                    token_to_check = lowercase_first_char(suggested) if is_capitalized else suggested
                    if len(self.word_tagger.tag(token_to_check)) > 0 or (
                            extra_tag == _UA_1992_TAG_PART and pth.has_pos_tag_part(next_atr, _UA_1992_TAG_PART)):
                        rm = RuleMatch(self, sentence, atr.start_pos, next_atr.end_pos, message,
                                       self.get_description())
                        rm.set_suggested_replacement(suggested)
                        out.append(rm)
        return out

    @staticmethod
    def _get_prefix_extra_tag(atr, is_capitalized):
        token = atr.token
        if is_capitalized:
            token = lowercase_first_char(token)
        return _dash_prefixes().get(token)


_LIKELY_LATIN_NUMBER = jregex.compile('[XVIХІ]{2,8}(-[а-яіїє]{1,3})?')
_LATIN_NUMBER_WITH_CYRILLICS = jregex.compile('(Х{1,3}І{1,3}|І{1,3}Х{1,3}|Х{2,3}|І{2,3})(-[а-яіїє]{1,4})?')
_MIXED_ALPHABETS = jregex.compile(
    ".*([a-zA-ZïáÁéÉíÍḯḮóÓúýÝ]'?[а-яіїєґА-ЯІЇЄҐ]|[а-яіїєґА-ЯІЇЄҐ]'?[a-zA-ZïáÁéÉíÍḯḮóÓúýÝ]).*")
_CYRILLIC_ONLY = jregex.compile('.*[бвгґдєжзийїлнпфцчшщьюяБГҐДЄЖЗИЙЇЛПФЦЧШЩЬЮЯ].*')
_LATIN_ONLY = jregex.compile('.*[bdfghjlqrstvzDFGJLNQRSUVZ].*')
_COMMON_CYR_LETTERS = jregex.compile('[АВЕІКОРСТУХ]+')
_CYRILLIC_FIRST_LETTER = jregex.compile('[а-яіїєґА-ЯІЇЄҐ].*')
_IYA = jregex.compile('[iya]')
_XBB = jregex.compile('[xbB]')
_FNAME_NOT_ABBR = jregex.compile('(?!.*:abbr).*fname.*')
_PREV_LEMMA_LATIN = jregex.compile('гепатит|група|турнір')
_COMBINING = jregex.compile('.*(и\u0306|і\u0308).*')
_INVALID_SUFFIX = jregex.compile('-[а-яіїє]{1,4}')
_ROMAN_WITH_SUFFIX = jregex.compile('[IVXІХ]+-[а-яіїє]{1,4}')
_MSG_CYR_FOR_LAT = 'Вжито кириличну літеру замість латинської'

_CYR_CHARS = 'аеіїкморстухАВЕІКМНОРСТУХ'
_LAT_CHARS = 'aeiïkmopctyxABEIKMHOPCTYX'
_TO_LAT = dict(zip(_CYR_CHARS, _LAT_CHARS))
_TO_CYR = dict(zip(_LAT_CHARS, _CYR_CHARS))
_UMLAUTS = ('á', 'Á', 'é', 'É', 'í', 'Í', 'ḯ', 'Ḯ', 'ó', 'Ó', 'ú', 'ý', 'Ý')
_UMLAUTS_REPLACE = ('а\u0301', 'А\u0301', 'е\u0301', 'Е\u0301', 'і\u0301', 'І\u0301', 'ї\u0301', 'Ї\u0301',
                    'о\u0301', 'О\u0301',
                    'и\u0301', 'у\u0301', 'У\u0301')


def _to_cyrillic(word):
    word = ''.join(_TO_CYR.get(c, c) for c in word)
    for u, r in zip(_UMLAUTS, _UMLAUTS_REPLACE):
        word = word.replace(u, r)
    return word


def _to_latin(word):
    return ''.join(_TO_LAT.get(c, c) for c in word)


class MixedAlphabetsRule(Rule):
    """Port of MixedAlphabetsRule: words with Latin and Cyrillic characters"""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.category = Categories.get('MISC', messages)

    def get_id(self):
        return 'UK_MIXED_ALPHABETS'

    def get_description(self):
        return 'Змішування кирилиці й латиниці'

    def get_short(self):
        return 'Мішанина розкладок'

    def match(self, sentence):
        out = []
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        for i in range(1, n):
            atr = tokens[i]
            token_string = atr.get_clean_token()

            # optimization: 1-letter tokens first
            if i < n - 1 and (_IYA.fullmatch(token_string) or (token_string == 'A' and i == 1)) \
                    and _CYRILLIC_FIRST_LETTER.fullmatch(tokens[i + 1].token) \
                    and not any(_XBB.fullmatch(t.token) for t in tokens):  # filter out formulas
                msg = 'Вжито латинську «' + token_string + '» замість кириличної'
                out.append(self._create_rule_match(atr, [_to_cyrillic(token_string)], msg, sentence))
            elif token_string == 'І' and self._likely_bad_latin_i(tokens, i):
                out.append(self._create_rule_match(atr, [_to_latin(token_string)], _MSG_CYR_FOR_LAT, sentence))
            elif i <= n - 1 and token_string == 'І.' and (
                    i > 1 and tokens[i - 1].get_clean_token() != 'Тому'
                    and tokens[i - 1].get_clean_token() != 'Франко'
                    and pth.has_pos_tag(tokens[i - 1], _FNAME_NOT_ABBR)):
                out.append(self._create_rule_match(atr, [_to_latin(token_string)], _MSG_CYR_FOR_LAT, sentence))
            elif _COMMON_CYR_LETTERS.fullmatch(token_string):
                prev_lemma = tokens[i - 1].readings[0].lemma
                if prev_lemma is not None and _PREV_LEMMA_LATIN.fullmatch(prev_lemma):
                    out.append(self._create_rule_match(atr, [_to_latin(token_string)], _MSG_CYR_FOR_LAT,
                                                       sentence))

            if len(token_string) < 2:
                if token_string == '°' and i < n - 1 and tokens[i + 1].get_clean_token() == 'С':  # Cyrillic С
                    out.append(self._create_rule_match(tokens[i + 1], ['C'], _MSG_CYR_FOR_LAT, sentence))
                continue

            if _MIXED_ALPHABETS.fullmatch(token_string):
                msg = 'Вжито кириличні й латинські літери в одному слові'
                replacements = []
                if not _LATIN_ONLY.fullmatch(token_string) and not _LIKELY_LATIN_NUMBER.fullmatch(token_string):
                    replacements.append(_to_cyrillic(token_string))
                if (len(token_string) > 2 and not _CYRILLIC_ONLY.fullmatch(token_string)) \
                        or _LIKELY_LATIN_NUMBER.fullmatch(token_string):
                    converted = self._to_latin_left_only(token_string)
                    converted = self._adjust_for_invalid_suffix(converted)
                    replacements.append(converted)
                    msg = 'Вжито кириличні літери замість латинських'
                    msg = self._adjust_msg_for_invalid_suffix(token_string, msg)
                if replacements:
                    out.append(self._create_rule_match(atr, replacements, msg, sentence))
            elif _LATIN_NUMBER_WITH_CYRILLICS.fullmatch(token_string):
                converted = self._to_latin_left_only(token_string)
                converted = self._adjust_for_invalid_suffix(converted)
                msg = 'Вжито кириличні літери замість латинських на позначення римської цифри'
                msg = self._adjust_msg_for_invalid_suffix(token_string, msg)
                out.append(self._create_rule_match(atr, [converted], msg, sentence))

            if token_string.find('\u0306') > 0 or token_string.find('\u0308') > 0:
                if _COMBINING.fullmatch(token_string):
                    fix = token_string.replace('и\u0306', 'й').replace('і\u0308', 'ї')
                    msg = 'Вжито комбіновані символи замість українських літер'
                    out.append(self._create_rule_match(atr, [fix], msg, sentence))
        return out

    @staticmethod
    def _likely_bad_latin_i(tokens, i):
        n = len(tokens)
        return i > 1 and (
            (helpers.is_capitalized(tokens[i - 1].get_clean_token())
             or (pth.has_pos_tag_start(tokens[i - 1], 'prep')
                 and i < n - 1 and not helpers.is_all_uppercase_uk(tokens[i + 1].get_clean_token())))
            or (i < n - 1 and tokens[i + 1].get_clean_token() in ('ст.', 'тис.'))
            or (i < n - 1 and tokens[i + 1].get_clean_token() in ('квартал', 'півріччя', 'тисячоліття', 'половина')))

    @staticmethod
    def _adjust_for_invalid_suffix(token_string):
        if '-' in token_string:
            token_string = _INVALID_SUFFIX.sub('', token_string, count=1)
        return token_string

    @staticmethod
    def _adjust_msg_for_invalid_suffix(token_string, msg):
        if '-' in token_string and _ROMAN_WITH_SUFFIX.fullmatch(token_string):
            msg += '. Також: до римських цифр букви не дописуються.'
        return msg

    @staticmethod
    def _to_latin_left_only(token_string):
        parts = token_string.split('-', 1)
        right = '-' + parts[1] if len(parts) > 1 else ''
        return _to_latin(parts[0]) + right

    def _create_rule_match(self, atr, replacements, msg, sentence):
        rm = RuleMatch(self, sentence, atr.start_pos, atr.end_pos, msg, self.get_short())
        rm.set_suggested_replacements(replacements)
        return rm


_PUNCT_PATTERN_1 = jregex.compile('([,:] | *- |,- | ) *')
_PUNCT_PATTERN_2 = jregex.compile('([.!?]|!!!|\\?\\?\\?|\\?!!|!\\.\\.|\\?\\.\\.|\\.\\.\\.) *')
_PUNCT_PATTERN_3 = jregex.compile('^[.,!?: -]$')


class PunctuationCheckRule(AbstractPunctuationCheckRule):
    """Port of org.languagetool.rules.uk.PunctuationCheckRule: matches "..",
    "::", "-," but not "...", "!..", "?!!", ",-" etc (not used by
    Ukrainian.getRelevantRules())"""

    def is_puncts_join_ok(self, tokens):
        # we ignore duplicated spaces - too many errors
        return bool(_PUNCT_PATTERN_1.fullmatch(tokens) or _PUNCT_PATTERN_2.fullmatch(tokens))

    def is_punctuation(self, token):
        return _PUNCT_PATTERN_3.fullmatch(token) is not None
