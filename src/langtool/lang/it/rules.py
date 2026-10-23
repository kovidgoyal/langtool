"""Italian specific rules (port of org.languagetool.rules.it)."""

from ...rules.core import WordRepeatRule


class ItalianWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.it.ItalianWordRepeatRule: avoid false
    alarms in the word repetition rule."""

    rule_id = 'ITALIAN_WORD_REPEAT_RULE'

    def ignore(self, tokens, position):
        if self.word_repetition_of('così', tokens, position):
            return True  # "Mi è sembrato così così."
        if self.word_repetition_of('passo', tokens, position):
            return True  # "che passo passo vanno verso la rovina"
        if self.word_repetition_of('piano', tokens, position):
            return True  # "Piano, piano, signor podestà."
        if self.word_repetition_of('via', tokens, position):
            return True  # "Il lessico si andava via via modificando."
        return super().ignore(tokens, position)
