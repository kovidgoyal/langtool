"""Swedish specific rules (port of org.languagetool.rules.sv)."""

from ...rules.abstract_rules import AbstractCompoundRule, AbstractWordCoherencyRule, load_compound_rule_data


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.sv.CompoundRule: checks that compounds
    (if in the list /sv/compounds.txt) are not written as separate words."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Dessa ord skrivs samman med bindestreck.',
                         'Dessa ord skrivs samman.',
                         'Dessa ord skrivs samman med eller utan bindestreck.')

    def get_id(self):
        return 'SV_COMPOUNDS'

    def get_description(self):
        return "Särskrivningar, t.ex. 'e mail' bör skrivas 'e-mail'"

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/sv/compounds.txt')


class WordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.sv.WordCoherencyRule: Swedish version
    of AbstractWordCoherencyRule (word pairs of /sv/coherency.txt)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair(
            'Det är en blandning av <marker>mejl</marker> och <marker>mail</marker> i det du skriver.',
            'Om du använder enbart <marker>mejl</marker> när du skriver <marker>mejl</marker> blir det mer '
            'konsekvent.')

    def get_word_map(self):
        return self.load_word_map('/sv/coherency.txt')

    def get_message(self, word1, word2):
        return ("Använd endast en av stavningsvarianterna '" + word1 + "' och '" + word2
                + "' i en och samma text.")

    def get_id(self):
        return 'SV_WORD_COHERENCY'

    def get_description(self):
        return 'Enhetlig och konsekvent stavning av ord när det finns stavningsvarianter att välja på.'
