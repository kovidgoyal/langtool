"""Port of org.languagetool.rules.de.MissingVerbRule: checks that a
sentence contains at least one verb (MISSING_VERB, default off)."""

from ...patterns.pattern_token import PatternToken
from ...patterns.rules import PatternRule
from ...rules.base import RuleMatch
from ...rules.core import CoreRule
from ...tools import is_capitalized_word, lowercase_first_char

_MIN_TOKENS_FOR_ERROR = 5


class MissingVerbRule(CoreRule):
    """Port of org.languagetool.rules.de.MissingVerbRule. Ignores very short
    sentences. Off by default, as there are quite some "sentences" without a
    verb, e.g. "Nix für ungut!", "Bis nächste Woche.", "Nicht schon
    wieder!", "Und deine Schwester?", "Wie dumm von mir!", and book
    references like "Andreas Fecker: Fluglotsen."."""

    rule_id = 'MISSING_VERB'
    category_id = 'GRAMMAR'

    def __init__(self, messages, language, user_config=None, **kwargs):
        super().__init__(messages, language)
        self._rule1 = PatternRule("internal", language, [
            PatternToken("Vielen", True, False, False),
            PatternToken("Dank", True, False, False)], "", "", "")
        self._rule2 = PatternRule("internal", language, [
            PatternToken("Herzlichen", True, False, False),
            PatternToken("Glückwunsch", True, False, False)], "", "", "")
        self.set_default_off()
        self.add_example_pair("<marker>In diesem Satz kein Wort.</marker>",
                              "In diesem Satz <marker>fehlt</marker> kein Wort.")

    def get_description(self):
        return "Satz ohne Verb"

    def match(self, sentence):
        if not self._is_real_sentence(sentence) or self._is_special_case(sentence):
            return []
        verb_found = False
        last_token = None
        tokens = sentence.non_blank_tokens
        for i, readings in enumerate(tokens):
            if readings.has_pos_tag_starting_with("VER") \
                    or (not readings.is_tagged() and not is_capitalized_word(readings.token)) \
                    or (i == 1 and self._verb_at_sentence_start(readings)):
                # (ignore unknown words to avoid false alarms)
                verb_found = True
                break
            last_token = readings
        if not verb_found and last_token is not None and len(tokens) >= _MIN_TOKENS_FOR_ERROR:
            match = RuleMatch(self, sentence, 0, last_token.start_pos + len(last_token.token),
                              "Dieser Satz scheint kein Verb zu enthalten")
            return [match]
        return []

    @staticmethod
    def _is_real_sentence(sentence):
        # we want to ignore headlines, and these usually don't end with [.?!]
        tokens = sentence.non_blank_tokens
        if tokens:
            last_token = tokens[-1]
            return last_token.has_pos_tag("PKT") and last_token.token in (".", "?", "!")
        return False

    def _is_special_case(self, sentence):
        return len(self._rule1.match(sentence)) > 0 or len(self._rule2.match(sentence)) > 0

    def _verb_at_sentence_start(self, readings):
        # start of sentence is mis-tagged because of the uppercase first character, work around that:
        lowercased = lowercase_first_char(readings.token)
        lc_readings = self.language.tagger.tag([lowercased])
        return len(lc_readings) > 0 and lc_readings[0].has_pos_tag_starting_with("VER")
