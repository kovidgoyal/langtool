"""Romanian specific rules (port of org.languagetool.rules.ro)."""

from ...rules.abstract_rules import AbstractCompoundRule, AbstractSimpleReplaceRule2, WordRepeatBeginningRule, \
    load_compound_rule_data

ROMANIAN_SIMPLE_REPLACE_RULE = 'RO_SIMPLE_REPLACE'


class SimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.ro.SimpleReplaceRule: words or groups
    of words of /ro/replace.txt that are incorrect or obsolete. (Java passes
    a new Romanian() as the language and sets the MISC category, the default
    here; getLocale() returns Locale("ro"), which AbstractSimpleReplaceRule2
    does not use.)"""

    def get_file_names(self):
        return ['/ro/replace.txt']

    def get_id(self):
        return ROMANIAN_SIMPLE_REPLACE_RULE

    def get_description(self):
        return 'Cuvinte sau grupuri de cuvinte incorecte sau ieșite din uz'

    def get_short(self):
        return 'Cuvânt incorect sau ieșit din uz'

    def get_message(self):
        return "'$match' este incorect sau ieșit din uz, folosiți $suggestions"

    def get_suggestions_separator(self):
        return ' sau '


class RomanianWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.ro.RomanianWordRepeatBeginningRule:
    successive sentences beginning with the same word, with Romanian
    adverbs (POS tags starting with 'G', see resource/ro/coduri.html)."""

    def get_id(self):
        return 'ROMANIAN_WORD_REPEAT_BEGINNING_RULE'

    def allow_ambiguous_adverbs(self):
        """Whether ambiguous adverbs (words that have the adverb tag along
        with other tags, like "Și") are considered."""
        return False

    def is_adverb(self, atr):
        is_adverb = False
        for reading in atr.readings:
            tag = reading.pos_tag
            if tag is not None:
                if tag.startswith('G'):
                    is_adverb = True
                elif not self.allow_ambiguous_adverbs():
                    return False
        return is_adverb


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.ro.CompoundRule: words that are written
    with a hyphen or joined, listed in /ro/compounds.txt."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Cuvântul se scrie cu cratimă.',
                         'Cuvântul se scrie legat.',
                         'Cuvântul se scrie legat sau cu cratimă.',
                         'Problemă de scriere (cratimă, spațiu, etc.)')

    def get_id(self):
        return 'RO_COMPOUND'

    def get_description(self):
        return 'Greșeală de scriere (cuvinte scrise legat sau cu cratimă)'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/ro/compounds.txt')
