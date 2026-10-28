"""Belarusian specific rules (port of org.languagetool.rules.be)."""

from ...rules.abstract_rules import AbstractSimpleReplaceRule2, AbstractSpecificCaseRule
from ...rules.base import Category

BELARUSIAN_SIMPLE_REPLACE_RULE = 'BE_SIMPLE_REPLACE'


class SimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.be.SimpleReplaceRule: colloquialisms
    and wrong phrases of /be/replace.txt. (getLocale() returns
    Locale("be"); AbstractSimpleReplaceRule2 does not use it.)"""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Category('MISC', 'Агульныя правілы')
        self.add_example_pair('<marker>З большага</marker>, гэта быў добры дзень.',
                              '<marker>Збольшага</marker>, гэта быў добры дзень.')

    def get_file_names(self):
        return ['/be/replace.txt']

    def get_id(self):
        return BELARUSIAN_SIMPLE_REPLACE_RULE

    def get_description(self):
        return 'Пошук прастамоўяў і памылковых фраз'

    def get_short(self):
        return 'Памылка?'

    def get_message(self):
        return '«$match» — памылка, нелітаратурны выраз або прастамоўе, правільна: $suggestions'

    def get_suggestions_separator(self):
        return ', '


class BelarusianSpecificCaseRule(AbstractSpecificCaseRule):
    """Port of org.languagetool.rules.be.BelarusianSpecificCaseRule: proper
    nouns and names of /be/specific_case.txt with a special
    capitalization."""

    def __init__(self, messages, language=None):
        # (the Java constructor only gets the messages: the resources are those of Belarusian)
        if language is None:
            from ...api import get_language
            language = get_language('be')
        super().__init__(messages, language)
        self.add_example_pair(
            '<marker>Вялікая айчынная Вайна</marker> — гэта спецыфічны тэрмін савецкай гістарыяграфіі.',
            '<marker>Вялікая Айчынная вайна</marker> — гэта спецыфічны тэрмін савецкай гістарыяграфіі.')

    def get_phrases_path(self):
        return '/be/specific_case.txt'

    def get_initial_capital_message(self):
        return 'Уласныя імёны і назвы пішуцца з вялікай літары.'

    def get_other_capitalization_message(self):
        return 'Калі гэта уласнае імя або назва, выкарыстоўвайце прапанаванае напісанне.'

    def get_short_message(self):
        return 'Proper noun'

    def get_id(self):
        return 'BE_SPECIFIC_CASE'

    def get_description(self):
        return 'Напісанне спецыяльных найменняў у верхнім або ніжнім рэгістры'
