"""Persian specific rules (port of org.languagetool.rules.fa)."""

from ... import jregex
from ...rules.abstract_rules import (AbstractSimpleReplaceRule, AbstractSpaceBeforeRule, AbstractWordCoherencyRule,
                                     WordRepeatBeginningRule)
from ...rules.core import Categories, CommaWhitespaceRule, DoublePunctuationRule, WordRepeatRule

_PERSIAN_COMMA = '،'


class PersianCommaWhitespaceRule(CommaWhitespaceRule):
    """Port of org.languagetool.rules.fa.PersianCommaWhitespaceRule: periods,
    Persian commas and closing parentheses preceded by whitespace and opening
    parentheses followed by whitespace. Off by default."""

    rule_id = 'PERSIAN_COMMA_PARENTHESIS_WHITESPACE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def get_comma_character(self):
        return _PERSIAN_COMMA


class PersianDoublePunctuationRule(DoublePunctuationRule):
    """Port of org.languagetool.rules.fa.PersianDoublePunctuationRule: ".."
    (but not "..." etc.) and "،،"."""

    rule_id = 'PERSIAN_DOUBLE_PUNCTUATION'

    def get_comma_character(self):
        return _PERSIAN_COMMA


_CONJUNCTIONS = jregex.compile('و|به|با|تا|زیرا|چون|بنابراین|چونکه')


class PersianSpaceBeforeRule(AbstractSpaceBeforeRule):
    """Port of org.languagetool.rules.fa.PersianSpaceBeforeRule: a missing
    space before some conjunctions. Off by default."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def get_conjunctions(self):
        return _CONJUNCTIONS

    def get_id(self):
        return 'FA_SPACE_BEFORE_CONJUNCTION'

    def get_description(self):
        return 'بررسی‌کردن فاصله قبل از حرف ربط'

    def get_short(self):
        return 'فاصلهٔ حذف‌شده'

    def get_suggestion(self):
        return 'فاصلهٔ قبل از حرف ربط حذف شده‌است'


_ADVERBS = frozenset(('هم', 'همچنین', 'نیز', 'از یک سو', 'از یک طرف', 'از طرف ديگر', 'بنابراین', 'حتی', 'چنانچه'))


class PersianWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.fa.PersianWordRepeatBeginningRule:
    WordRepeatBeginningRule with a list of Persian adverbs."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair(
            'همچنین، خیابان تقریباً کاملاً مسکونی است. <marker>همچنین</marker>، به افتخار یک شاعر نامگذاری شده‌است.',
            'همچنین، خیابان تقریباً مسکونی است. <marker>این خیابان</marker> به افتخار یک شاعر نامگذاری شده‌است.')

    def get_id(self):
        return 'PERSIAN_WORD_REPEAT_BEGINNING_RULE'

    def is_adverb(self, atr):
        return atr.token in _ADVERBS


class PersianWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.fa.PersianWordRepeatRule: avoid false
    alarms in the generic word repetition rule."""

    rule_id = 'PERSIAN_WORD_REPEAT_RULE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('این کار <marker>برای برای</marker> تو بود.',
                              'این کار <marker>برای</marker> تو بود.')

    def ignore(self, tokens, position):
        if self.word_repetition_of('لی', tokens, position):
            return True  # "من لی لی را دیدم"
        if self.word_repetition_of('سی', tokens, position):
            return True  # "آب درون بطری ۱۰۰ سی سی بود"
        if self.word_repetition_of('لک', tokens, position):
            return True  # "لک لک یک پرنده است"
        if self.word_repetition_of('ریز', tokens, position):
            return True  # "غذایش را ریز ریز کرد"
        if self.word_repetition_of('جز', tokens, position):
            return True  # "جز جز این کتاب را بلدم"
        if self.word_repetition_of('کل', tokens, position):
            return True  # "با من کل کل نکن"
        return super().ignore(tokens, position)


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.fa.SimpleReplaceRule: possible spelling
    mistakes of /fa/replace.txt, case insensitive. (getLocale() returns
    Locale.getDefault(), which is the default lower() here.)"""

    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.category = Categories.get('CONFUSED_WORDS', messages)
        self.add_example_pair('وی <marker>حاظر</marker> به همکاری شد.',
                              'وی <marker>حاضر</marker> به همکاری شد.')

    def get_wrong_words(self):
        return self.load_from_path('/fa/replace.txt')

    def get_id(self):
        return 'FA_SIMPLE_REPLACE'

    def get_description(self):
        return 'اشتباه محتمل املائی'

    def get_short(self):
        return 'اشتباه محتمل املائی'

    def get_message(self, token_str, replacements):
        return 'اشتباه محتمل املائی پیداشده: ' + '، '.join(replacements) + '.'

    def is_case_sensitive(self):
        return False


class WordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.fa.WordCoherencyRule: Persian version
    of AbstractWordCoherencyRule (word pairs of /fa/coherency.txt). (Java has
    no example pair yet, it is commented out as a TODO.)"""

    def get_word_map(self):
        return self.load_word_map('/fa/coherency.txt')

    def get_message(self, word1, word2):
        return "'" + word1 + "' و '" + word2 + "' نباید در یک جا استفاده شوند"

    def get_id(self):
        return 'FA_WORD_COHERENCY'

    def get_description(self):
        return 'چند املا برای یک کلمه که یکی از آنها اولویت بیشتری دارد'
