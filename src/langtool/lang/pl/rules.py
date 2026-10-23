"""Polish specific rules (port of org.languagetool.rules.pl).

The Java rules that use a Locale("pl") for case conversion (it has no
special case mapping) use the default lower() here."""

from ... import jregex
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractDashRule, AbstractSimpleReplaceRule,
                                     AbstractWordCoherencyRule, AdvancedWordRepeatRule, load_compound_rule_data)
from ...rules.base import Category
from ...rules.core import GenericUnpairedBracketsRule

POLISH_SIMPLE_REPLACE_RULE = 'PL_SIMPLE_REPLACE'


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.pl.CompoundRule: compounds (listed in
    /pl/compounds.txt) that are not written as separate words."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Ten wyraz pisze się z łącznikiem.',
                         'Ten wyraz pisze się razem (bez spacji ani łącznika).',
                         'Ten wyraz pisze się z łącznikiem lub bez niego.',
                         'Brak łącznika lub zbędny łącznik')
        self.add_example_pair('Witamy w <marker>Rabce Zdroju</marker>.',
                              'Witamy w <marker>Rabce-Zdroju</marker>.')

    def get_id(self):
        return 'PL_COMPOUNDS'

    def get_description(self):
        return 'Sprawdza wyrazy z łącznikiem, np. „łapu capu” zamiast „łapu-capu”'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/pl/compounds.txt')


class DashRule(AbstractDashRule):
    """Port of org.languagetool.rules.pl.DashRule: compounds written with
    dashes instead of hyphens (for example, Rabka — Zdrój)."""

    def get_description(self):
        return 'Sprawdza, czy wyrazy pisane z łącznikiem zapisano z myślnikami (np. „Lądek — Zdrój” zamiast ' \
               '„Lądek-Zdrój”).'

    def get_message(self):
        return 'Błędne użycie myślnika zamiast łącznika.'

    def get_compounds_data(self):
        return self.load_compound_file('/pl/compounds.txt')


PL_START_SYMBOLS = ['[', '(', '{', '„', '»', '"']
PL_END_SYMBOLS = [']', ')', '}', '”', '«', '"']


class PolishUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.pl.PolishUnpairedBracketsRule."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, PL_START_SYMBOLS, PL_END_SYMBOLS)
        self.add_example_pair('To jest zdanie z <marker>„</marker>cudzysłowem.',
                              'To jest zdanie z <marker>„</marker>cudzysłowem”.')

    def get_id(self):
        return 'PL_UNPAIRED_BRACKETS'


# Excluded dictionary words.
_EXC_WORDS = frozenset((
    'nie', 'tuż', 'aż', 'to', 'siebie', 'być', 'ani', 'ni', 'albo', 'lub', 'czy', 'bądź', 'jako', 'zł', 'np',
    'coraz', 'bardzo', 'bardziej', 'proc', 'ten', 'jak', 'mln', 'tys', 'swój', 'mój', 'twój', 'nasz', 'wasz',
    'i', 'zbyt', 'się'))

# Excluded part of speech classes.
_EXC_POS = jregex.compile('prep:.*|ppron.*')

# Excluded non-words (special symbols, Roman numerals etc.)
_EXC_NONWORDS = jregex.compile('&quot|&gt|&lt|&amp|[0-9].*|'
                               'M*(D?C{0,3}|C[DM])(L?X{0,3}|X[LC])(V?I{0,3}|I[VX])$')


class PolishWordRepeatRule(AdvancedWordRepeatRule):
    """Port of org.languagetool.rules.pl.PolishWordRepeatRule: repeated
    lemmas in a sentence (stylistic monotony)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Mówiła długo, bo lubiła robić wszystko <marker>długo</marker>.',
                              'Mówiła długo, bo lubiła robić wszystko <marker>powoli</marker>.')

    def get_description(self):
        return 'Powtórzenia wyrazów w zdaniu (monotonia stylistyczna)'

    def get_excluded_non_words_pattern(self):
        return _EXC_NONWORDS

    def get_excluded_pos(self):
        return _EXC_POS

    def get_excluded_words_pattern(self):
        return _EXC_WORDS

    def get_id(self):
        return 'PL_WORD_REPEAT'

    def get_message(self):
        return 'Powtórzony wyraz w zdaniu'

    def get_short_message(self):
        return 'Powtórzenie wyrazu'


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.pl.SimpleReplaceRule: typical typos
    and incorrect words of /pl/replace.txt, case insensitive, without
    checking the lemmas."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Category('PRAWDOPODOBNE_LITEROWKI', 'Prawdopodobne literówki')
        self.check_lemmas = False
        self.add_example_pair('Uspokój <marker>sei</marker>.', 'Uspokój <marker>się</marker>.')

    def get_wrong_words(self):
        return self.load_from_path('/pl/replace.txt')

    def get_id(self):
        return POLISH_SIMPLE_REPLACE_RULE

    def get_description(self):
        return 'Typowe literówki i niepoprawne wyrazy (domowi, sie, niewiadomo, duh, cie…)'

    def get_short(self):
        return 'Literówka'

    def get_message(self, token_str, replacements):
        return 'Wyraz „' + token_str + '” to najczęściej literówka; poprawnie pisze się: ' + \
            ', '.join(replacements) + '.'

    def is_case_sensitive(self):
        return False


class WordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.pl.WordCoherencyRule: words with two
    permitted spellings (/pl/coherency.txt) should be written consistently."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Grapefruity są zdrowe. <marker>Grejpfrut</marker> smakuje najlepiej smażony.',
                              'Grapefruity są zdrowe. <marker>Grapefruit</marker> smakuje najlepiej smażony.')

    def get_word_map(self):
        return self.load_word_map('/pl/coherency.txt')

    def get_message(self, word1, word2):
        return 'Formy „' + word1 + '” i „' + word2 + '” zwykle nie powinny być używane jednocześnie.'

    def get_id(self):
        return 'PL_WORD_COHERENCY'

    def get_description(self):
        return 'Jednolita pisownia wyrazów o obocznej dopuszczalnej pisowni'
