"""Galician specific rules (port of org.languagetool.rules.gl).

The Java rules get a Locale("gl") from getLocale(), used for case
conversion; it has no special case mapping, so the default lower() is
used. The AbstractSimpleReplaceRule2 subclasses pass a new Galician() as
the language in Java, here the language is given to the constructor."""

from ...rules.abstract_rules import AbstractSimpleReplaceRule, AbstractSimpleReplaceRule2
from ...rules.core import Categories

GL_CAST_WORDS_RULE = 'GL_CAST_WORDS'
GL_SIMPLE_REPLACE_RULE = 'GL_SIMPLE_REPLACE'
GALICIAN_BARBARISM_RULE = 'GL_BARBARISM_REPLACE'
GL_REDUNDANCY_REPLACE = 'GL_REDUNDANCY_REPLACE'
WIKIPEDIA_COMMON_ERRORS = 'GL_WIKIPEDIA_COMMON_ERRORS'
GL_WORDINESS_REPLACE = 'GL_WORDINESS_REPLACE'


class CastWordsRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.gl.CastWordsRule: Spanish words
    (castelanismos) of /gl/spanish.txt, case insensitive."""

    def get_wrong_words(self):
        return self.load_from_path('/gl/spanish.txt')

    def get_id(self):
        return GL_CAST_WORDS_RULE

    def get_description(self):
        return 'Corrección de erros léxicos (castelanismos).'

    def get_short(self):
        return 'Castelanismos léxicos'

    def get_message(self, token_str, replacements):
        return "'" + token_str + "' é un castelanismo. Empregue no seu sitio: " + ', '.join(replacements) + '.'

    def is_case_sensitive(self):
        return False


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.gl.SimpleReplaceRule: lexical errors
    (barbarismos) of /gl/words.txt, case insensitive."""

    def get_wrong_words(self):
        return self.load_from_path('/gl/words.txt')

    def get_id(self):
        return GL_SIMPLE_REPLACE_RULE

    def get_description(self):
        return 'Corrección de erros léxicos (barbarismos).'

    def get_short(self):
        return 'Erros léxicos'

    def get_message(self, token_str, replacements):
        return "'" + token_str + "' non existe en galego. Talvez quería vostede dicir: " + \
            ', '.join(replacements) + '.'

    def is_case_sensitive(self):
        return False


class GalicianBarbarismsRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.gl.GalicianBarbarismsRule: words of
    foreign origin (xenismos) of /gl/barbarisms.txt."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('STYLE', messages)
        self.url = 'https://gl.wikipedia.org/wiki/Xenismo'
        self.add_example_pair('<marker>curriculum vitae</marker>', '<marker>currículo</marker>')

    def get_file_names(self):
        return ['/gl/barbarisms.txt']

    def get_id(self):
        return GALICIAN_BARBARISM_RULE

    def get_description(self):
        return 'Palabras de orixe estranxeira evitábeis'

    def get_short(self):
        return 'Xenismo'

    def get_message(self):
        return "'$match' é un xenismo. É preferíbel dicir $suggestions"

    def get_suggestions_separator(self):
        return ' ou '


class GalicianRedundancyRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.gl.GalicianRedundancyRule: redundant
    expressions (pleonasmos) of /gl/redundancies.txt."""

    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.url = 'https://gl.wikipedia.org/wiki/Pleonasmo'
        self.add_example_pair('<marker>duna de area</marker>', '<marker>duna</marker>')

    def get_file_names(self):
        return ['/gl/redundancies.txt']

    def get_id(self):
        return GL_REDUNDANCY_REPLACE

    def get_description(self):
        return '1. Pleonasmos e redundancias'

    def get_short(self):
        return 'Pleonasmo'

    def get_message(self):
        return "'$match' é un pleonasmo. É preferible dicir $suggestions"

    def get_suggestions_separator(self):
        return ' ou '


class GalicianWikipediaRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.gl.GalicianWikipediaRule: common
    errors of Wikipedia articles of /gl/wikipedia.txt."""

    issue_type = 'Grammar'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('WIKIPEDIA', messages)
        self.url = 'https://gl.wikipedia.org/wiki/Wikipedia:Erros_de_ortograf%C3%ADa_e_desviaci%C3%B3ns'
        self.add_example_pair('<marker>a efectos de</marker>', '<marker>para os efectos de</marker>')

    def get_file_names(self):
        return ['/gl/wikipedia.txt']

    def get_id(self):
        return WIKIPEDIA_COMMON_ERRORS

    def get_description(self):
        return 'Erros frecuentes nos artigos da Wikipedia'

    def get_short(self):
        return 'Erro gramatical ou de normativa'

    def get_message(self):
        return "'$match' é un erro. Considere utilizar $suggestions"

    def get_suggestions_separator(self):
        return ' ou '


class GalicianWordinessRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.gl.GalicianWordinessRule: wordy
    expressions (expresións prolixas) of /gl/wordiness.txt (no URL, it is
    commented out in Java)."""

    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.add_example_pair('<marker>Raramente é o caso en que acontece</marker> isto.',
                              '<marker>Raramente acontece</marker> isto.')

    def get_file_names(self):
        return ['/gl/wordiness.txt']

    def get_id(self):
        return GL_WORDINESS_REPLACE

    def get_description(self):
        return '2. Expresións prolixas'

    def get_short(self):
        return 'Expresión prolixa'

    def get_message(self):
        return "'$match' é unha expresión innecesariamente complexa. É preferíbel dicir $suggestions"

    def get_suggestions_separator(self):
        return ' ou '
