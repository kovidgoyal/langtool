"""Slovak specific rules (port of org.languagetool.rules.sk)."""

from ...rules.abstract_rules import AbstractCompoundRule, load_compound_rule_data


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.sk.CompoundRule: words that are written
    with a hyphen (or joined), listed in /sk/compounds.txt."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Toto slovo sa zvyčajne píše so spojovníkom.',
                         'Toto slovo sa obvykle píše bez spojovníka.',
                         'Tento výraz sa bežne píše s alebo bez spojovníka.',
                         'Problém spájania slov')

    def get_id(self):
        return 'SK_COMPOUNDS'

    def get_description(self):
        return 'Slová so spojovníkom napr. použite „česko-slovenský” namiesto „česko slovenský”'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/sk/compounds.txt')
