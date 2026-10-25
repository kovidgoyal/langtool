"""Ports of the German word replacement and confusion rules
(org.languagetool.rules.de): SimpleReplaceRule, GermanWrongWordInContextRule,
WordCoherencyRule, WiederVsWiderRule and SimilarNameRule.

The Java rules use Locale("DE") for case conversion, which has no special
case mapping; the default lower() is used here."""

from ...messages import messages_for
from ...rules.abstract_rules import (AbstractSimpleReplaceRule2, AbstractWordCoherencyRule, WrongWordInContextRule,
                                     java_hash_set_order)
from ...rules.base import RuleMatch
from ...rules.core import CoreRule, CoreTextLevelRule
from ...rules.multitoken import levenshtein_distance
from ...tools import java_equals_ignore_case, starts_with_uppercase


class SimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.de.SimpleReplaceRule: words which
    should not be used (/de/replace.txt, /de/replace_custom.txt) with
    correct ones as suggestions."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.use_sub_rule_specific_ids()

    def get_file_names(self):
        return ['/de/replace.txt', '/de/replace_custom.txt']

    def get_id(self):
        return 'DE_SIMPLE_REPLACE'

    def get_description(self):
        return 'Prüft auf bestimmte falsche Wörter/Phrasen: $match'

    def get_short(self):
        return 'Falsches Wort'

    def get_message(self):
        return 'Meinten Sie vielleicht $suggestions?'


class GermanWrongWordInContextRule(WrongWordInContextRule):
    """Port of GermanWrongWordInContextRule: easily confused words
    (/de/wrongWordInContext.txt). As in Java, messages may be None (the
    category is built from get_category_string())."""

    def __init__(self, messages, language):
        super().__init__(messages if messages is not None else messages_for('de'), language)
        self.add_example_pair('Die <marker>Miene</marker> vom Kugelschreiber ist leer.',
                              'Die <marker>Mine</marker> vom Kugelschreiber ist leer.')

    def get_category_string(self):
        return 'Leicht zu verwechselnde Wörter'

    def get_id(self):
        return 'GERMAN_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'Mögliche Wortverwechslungen: $match'

    def get_filename(self):
        return '/de/wrongWordInContext.txt'

    def get_message_string(self):
        return "Mögliche Wortverwechslung: Meinten Sie <suggestion>$SUGGESTION</suggestion> anstatt '$WRONGWORD'?"

    def get_short_message_string(self):
        return 'Mögliche Wortverwechslung'

    def get_long_message_string(self):
        return ('Mögliche Wortverwechslung: Meinten Sie <suggestion>$SUGGESTION</suggestion> '
                "(= $EXPLANATION_SUGGESTION) anstatt '$WRONGWORD' (= $EXPLANATION_WRONGWORD)?")


class WordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.de.WordCoherencyRule: words with more
    than one correct spelling (/de/coherency.txt) should be written
    consistently."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair(
            'Die Delfine gehören zu den Zahnwalen. <marker>Delphine</marker> sind in allen Meeren verbreitet.',
            'Die Delfine gehören zu den Zahnwalen. <marker>Delfine</marker> sind in allen Meeren verbreitet.')

    def load_word_map(self, path):
        if self.language is None:
            from ...api import get_language
            self.language = get_language('de')
        return super().load_word_map(path)

    def get_word_map(self):
        return self.load_word_map('/de/coherency.txt')

    def get_message(self, word1, word2):
        return "'" + word1 + "' und '" + word2 + "' sollten nicht gleichzeitig benutzt werden."

    def get_id(self):
        return 'DE_WORD_COHERENCY'

    def get_description(self):
        return 'Einheitliche Schreibweise für Wörter mit mehr als einer korrekten Schreibweise'


class WiederVsWiderRule(CoreRule):
    """Port of WiederVsWiderRule: "spiegelt ... wieder" instead of "spiegelt
    ... wider", e.g. in "Das spiegelt die Situation wieder" (incorrect)."""

    category_id = 'TYPOS'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Das spiegelt die Situation in Deutschland <marker>wieder</marker>.',
                              'Das spiegelt die Situation in Deutschland <marker>wider</marker>.')

    def get_id(self):
        return 'DE_WIEDER_VS_WIDER'

    def get_description(self):
        return "Möglicher Tippfehler 'spiegeln ... wieder (wider)'"

    def estimate_context_for_sure_match(self):
        return 0

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.non_blank_tokens
        found_spiegelt = False
        found_wieder = False
        found_wider = False
        n = len(tokens)
        for i in range(n):
            token = tokens[i].token
            if tokens[i].has_lemma('spiegeln'):
                found_spiegelt = True
            elif java_equals_ignore_case(token, 'wieder') and found_spiegelt:
                found_wieder = True
            elif java_equals_ignore_case(token, 'wider') and found_spiegelt:
                found_wider = True
            if found_spiegelt and found_wieder and not found_wider and \
                    not (n > i + 2 and (tokens[i + 1].token == 'wider' or tokens[i + 2].token == 'wider')):
                msg = ("'wider' in 'widerspiegeln' wird mit 'i' statt mit 'ie' "
                       "geschrieben, z.B. 'Das spiegelt die Situation gut wider.'")
                short_msg = "'wider' in 'widerspiegeln' wird mit 'i' geschrieben"
                pos = tokens[i].start_pos
                rule_match = RuleMatch(self, sentence, pos, pos + len(token), msg, short_msg)
                rule_match.set_suggested_replacement('wider')
                rule_matches.append(rule_match)
                found_spiegelt = False
                found_wieder = False
                found_wider = False
        return rule_matches


_MIN_LENGTH = 4
_MAX_DIFF = 1
_NOT_NAMES = frozenset(('Dein', 'Deine', 'Deinen', 'Deiner', 'Deines', 'Deinem',
                        'Ihr', 'Ihre', 'Ihren', 'Ihrer', 'Ihres', 'Ihrem'))


class SimilarNameRule(CoreTextLevelRule):
    """Port of SimilarNameRule: names similar to ones used before in the
    same text, as these might be typos. Off by default (it only works on
    known names)."""

    category_id = 'TYPOS'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Angela Müller ist CEO. <marker>Miller</marker> wurde in Hamburg geboren.',
                              'Angela Müller ist CEO. <marker>Müller</marker> wurde in Hamburg geboren.')
        self.set_default_off()

    def get_id(self):
        return 'DE_SIMILAR_NAMES'

    def get_description(self):
        return 'Mögliche Tippfehler in Namen finden'

    def match(self, sentences, annotated_text=None):
        names_so_far = []  # a HashSet in Java (iterated in its order, see _similar_name)
        names_set = set()
        rule_matches = []
        pos = 0
        for sentence in sentences:
            for token in sentence.non_blank_tokens:
                word = token.token
                # not tagged = too many correct words are not known so we cannot use that
                is_maybe_name = (len(word) >= _MIN_LENGTH
                                 and ((token.has_partial_pos_tag('EIG:') and not token.has_partial_pos_tag(':COU'))
                                      or token.is_pos_tag_unknown)
                                 and word not in _NOT_NAMES)
                if is_maybe_name and starts_with_uppercase(word):
                    similar_name = self._similar_name(word, names_so_far)
                    if similar_name is not None:
                        msg = ("'" + word + "' ähnelt dem vorher benutzten '" + similar_name
                               + "', handelt es sich evtl. um einen Tippfehler?")
                        rule_match = RuleMatch(self, sentence, pos + token.start_pos, pos + token.end_pos, msg)
                        rule_match.set_suggested_replacement(similar_name)
                        rule_matches.append(rule_match)
                    if word not in names_set:
                        names_set.add(word)
                        names_so_far.append(word)
            pos += sentence.get_corrected_text_length()
        return rule_matches

    @staticmethod
    def _similar_name(name_here, names_so_far):
        for name in java_hash_set_order(names_so_far):
            if name == name_here:
                continue
            len_diff = abs(len(name) - len(name_here))
            name_ends_with_s = name.endswith('s') and not name_here.endswith('s')
            other_name_ends_with_s = not name.endswith('s') and name_here.endswith('s')
            name_ends_with_n = name.endswith('n') and not name_here.endswith('n')  # probably a dative
            other_name_ends_with_n = not name.endswith('n') and name_here.endswith('n')
            if name_ends_with_s or other_name_ends_with_s or name_ends_with_n or other_name_ends_with_n:
                # we assume this is a genitive, e.g. "Angela Merkels Ehemann"
                continue
            if len_diff <= _MAX_DIFF and levenshtein_distance(name, name_here) <= _MAX_DIFF:
                return name
        return None

    def min_to_check_paragraph(self):
        return -1
