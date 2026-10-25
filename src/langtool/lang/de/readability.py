"""Port of org.languagetool.rules.de.GermanReadabilityRule: readability
of German paragraphs (Flesch reading ease for German, Amstad)."""

from ...rules.abstract_rules import ReadabilityRule
from ...rules.base import Category

_LEVEL_NAMES = ('Sehr schwer', 'Schwer', 'Mittelschwer', 'Mittel', 'Mittelleicht', 'Leicht', 'Sehr leicht')

_is_vowel = None


def _vowel_check():
    """GermanTools.isVowel (imported lazily, german_tools belongs to the
    speller port)"""
    global _is_vowel
    if _is_vowel is None:
        from .german_tools import is_vowel
        _is_vowel = is_vowel
    return _is_vowel


class GermanReadabilityRule(ReadabilityRule):
    """Port of GermanReadabilityRule (default off unless default_on)."""

    def __init__(self, messages, language, user_config=None, too_easy_test=False, level=-1, default_on=False):
        super().__init__(messages, language, user_config, too_easy_test, level, default_on)
        self.category = Category('CREATIVE_WRITING', messages['category_creative_writing'], 'INTERNAL', False)

    def get_id(self, too_easy_test=None):
        if too_easy_test is None:
            too_easy_test = self.too_easy_test
        return 'READABILITY_RULE_SIMPLE_DE' if too_easy_test else 'READABILITY_RULE_DIFFICULT_DE'

    def get_description(self):
        return 'Lesbarkeit: Zu einfacher Text' if self.too_easy_test else 'Lesbarkeit: Zu schwieriger Text'

    def print_message_level(self, level):
        if 0 <= level < len(_LEVEL_NAMES):
            return ' {Grad ' + str(level) + ': ' + _LEVEL_NAMES[level] + '}'
        return ''

    def get_message(self, level, fre, asl, asw):
        if self.too_easy_test:
            simple, few = 'einfach', 'wenige'
        else:
            simple, few = 'schwierig', 'viele'
        return 'Lesbarkeit: Der Text dieses Absatzes ist zu ' + simple + self.print_message_level(level) + '. Zu ' + \
            few + ' Wörter pro Satz und zu ' + few + ' Silben pro Wort.'

    def get_configure_text(self):
        return 'Grad der Lesbarkeit 0 (sehr schwierig) bis 6 (sehr einfach):'

    def get_flesch_reading_ease(self, asl, asw):
        return 180 - asl - (58.5 * asw)  # German

    def simple_syllables_count(self, word):
        if not word:
            return 0
        is_vowel = _vowel_check()
        n = 0
        if is_vowel(word[0]):
            n += 1
        last_double = False
        for i in range(1, len(word)):
            c = word[i]
            if is_vowel(c):
                cl = word[i - 1]
                if last_double:
                    n += 1
                    last_double = False
                elif (c in 'iy' and cl in 'aeAE') or (c == 'u' and cl in 'aeoAEO') or \
                        (c == 'e' and cl in 'eiEI') or (c == 'a' and cl in 'aA'):
                    last_double = True
                else:
                    n += 1
                    last_double = False
            else:
                last_double = False
        return 1 if n == 0 else n
