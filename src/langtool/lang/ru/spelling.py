"""The misspelling check of org.languagetool.rules.ru.MorfologikRussianSpellerRule.

Only the check whether a word is misspelled is ported (see
langtool.spelling), not the spell checking rules MORFOLOGIK_RULE_RU_RU and
MORFOLOGIK_RULE_RU_RU_YO (no rule matches, no suggestions). It is the
default spelling rule of Russian here (Russian.createDefaultSpellingRule()),
used by RussianSuppressMisspelledSuggestionsFilter and the core filters
that ask the default spelling rule. The speller dictionary
ru/hunspell/ru_RU.dict and the word lists spelling.txt, ignore.txt and
prohibit.txt (language-ru) are obtained with the dictionary download
mechanism (langtool.dictionaries)."""

from ...spelling import MorfologikMisspellingCheck


class MorfologikRussianSpellerCheck(MorfologikMisspellingCheck):
    """The files of MorfologikRussianSpellerRule (the word lists are the
    defaults of SpellingCheckRule: ru/hunspell/spelling.txt, ignore.txt,
    prohibit.txt, ...)."""

    def get_file_name(self):
        return '/ru/hunspell/ru_RU.dict'

    def is_latin_script(self):
        return False
