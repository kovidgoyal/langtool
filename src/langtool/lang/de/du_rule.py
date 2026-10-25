"""Port of org.languagetool.rules.de.DuUpperLowerCaseRule: coherent use of
Du/du, Dich/dich etc. Assume that the first use has 'correct'
capitalization and suggest the same capitalization for subsequent uses."""

from ...rules.base import RuleMatch
from ...rules.core import CoreTextLevelRule
from ...tools import is_upper_case, lowercase_first_char, starts_with_uppercase, uppercase_first_char

_LOWER_WORDS = frozenset((
    'du', 'dir', 'dich', 'dein', 'deine', 'deines', 'deins', 'deiner', 'deinen', 'deinem',
    'euch', 'euer', 'eure', 'euere', 'euren', 'eueren', 'euern', 'eurer', 'euerer',
    'eurem', 'euerem', 'eures', 'eueres'))

# (as in Java, the last three are literal strings of a backslash, "u" and
# four hex digits, not the characters)
_SKIP_AFTER = frozenset(('"', '„', '‚', ':', '»', '«', '“', '-', '–', '*', '•', '\\u2063', '\\u25E6', '\\u00B7'))


def _is_all_upper_case(s):
    """org.apache.commons.lang3.StringUtils.isAllUpperCase"""
    return bool(s) and all(is_upper_case(c) for c in s)


class DuUpperLowerCaseRule(CoreTextLevelRule):
    """Port of org.languagetool.rules.de.DuUpperLowerCaseRule
    (DE_DU_UPPER_LOWER)."""

    rule_id = 'DE_DU_UPPER_LOWER'
    category_id = 'CASING'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Wie geht es Dir? Bist <marker>du</marker> wieder gesund?',
                              'Wie geht es Dir? Bist <marker>Du</marker> wieder gesund?')
        self.url = 'https://languagetool.org/insights/de/beitrag/duzen-grossgeschrieben/'

    def get_id(self):
        return 'DE_DU_UPPER_LOWER'

    def get_description(self):
        return 'Einheitliche Verwendung von Du/du, Dir/dir etc.'

    def match(self, sentences, annotated_text=None):
        first_use = None
        rule_matches = []
        pos = 0
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            for i in range(len(tokens)):
                if i > 0 and (tokens[i - 1].is_sentence_start or tokens[i - 1].token in _SKIP_AFTER):
                    continue
                token = tokens[i]
                word = token.token
                lc_word = word.lower()
                if lc_word in _LOWER_WORDS:
                    if first_use is None:
                        first_use = word
                    else:
                        first_use_is_upper = starts_with_uppercase(first_use)
                        msg = None
                        replacement = None
                        if first_use_is_upper and not starts_with_uppercase(word):
                            replacement = uppercase_first_char(word)
                            msg = "Vorher wurde bereits '" + first_use + "' großgeschrieben. " + \
                                "Aus Gründen der Einheitlichkeit '" + replacement + "' hier auch großschreiben?"
                        elif not first_use_is_upper and starts_with_uppercase(word) and not _is_all_upper_case(word):
                            replacement = lowercase_first_char(word)
                            msg = "Vorher wurde bereits '" + first_use + "' kleingeschrieben. " + \
                                "Aus Gründen der Einheitlichkeit '" + replacement + "' hier auch kleinschreiben?"
                        if msg is not None:
                            rule_match = RuleMatch(self, sentence, pos + token.start_pos, pos + token.end_pos, msg)
                            rule_match.set_suggested_replacement(replacement)
                            rule_matches.append(rule_match)
            pos += sentence.get_corrected_text_length()
        return rule_matches

    def min_to_check_paragraph(self):
        return -1
