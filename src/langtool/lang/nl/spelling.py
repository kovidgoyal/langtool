"""The misspelling check of org.languagetool.rules.nl.MorfologikDutchSpellerRule.

Only the check whether a word is misspelled is ported (see
langtool.spelling), not the spell checking rule MORFOLOGIK_RULE_NL_NL (no
rule matches, no suggestions). It is the default spelling rule of Dutch
here, used by CompoundAcceptor, DutchNumberInWordFilter,
DutchSuppressMisspelledSuggestionsFilter and MultitokenSpellerFilter. The
speller dictionary nl/spelling/nl_NL.dict (dutch-pos-dict) and the word
lists spelling.txt, ignore.txt and prohibit.txt (language-nl) are obtained
with the dictionary download mechanism (langtool.dictionaries)."""

from ...spelling import MorfologikMisspellingCheck


class MorfologikDutchSpellerCheck(MorfologikMisspellingCheck):
    """The files of MorfologikDutchSpellerRule (the other ones are the
    defaults of SpellingCheckRule, e.g. spelling_global.txt)."""

    def get_file_name(self):
        return '/nl/spelling/nl_NL.dict'

    def get_ignore_file_name(self):
        return '/nl/spelling/ignore.txt'

    def get_spelling_file_name(self):
        return '/nl/spelling/spelling.txt'

    def get_prohibit_file_name(self):
        return '/nl/spelling/prohibit.txt'
