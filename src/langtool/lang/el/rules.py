"""Greek specific rules (port of org.languagetool.rules.el).

The AbstractSimpleReplaceRule2 subclasses get Locale("el") from
getLocale(), which AbstractSimpleReplaceRule2 does not use (Java's
lowercase conversion of Greek is the same for every locale)."""

from ... import jregex
from ...rules.abstract_rules import (AbstractSimpleReplaceRule2, AbstractSpecificCaseRule, WordRepeatBeginningRule,
                                     java_hash_set_order)
from ...rules.base import Category, Rule, RuleMatch
from ...rules.core import Categories

EL_REDUNDANCY_REPLACE = 'EL_REDUNDANCY_REPLACE'


class GreekRedundancyRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.el.GreekRedundancyRule: redundant
    phrases (pleonasms) of /el/redundancies.txt."""

    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.add_example_pair('Μου αρέσει να <marker>ανεβαίνω πάνω</marker> σε δέντρα.',
                              'Μου αρέσει να <marker>ανεβαίνω</marker> σε δέντρα.')

    def get_file_names(self):
        return ['/el/redundancies.txt']

    def get_id(self):
        return EL_REDUNDANCY_REPLACE

    def get_description(self):
        return 'Έλεγχος για χρήση πλεονασμού σε μια πρόταση.'

    def get_short(self):
        return 'Πλεονασμός'

    def get_message(self):
        return "'$match' είναι πλεονασμός. Γενικά, είναι προτιμότερο το: $suggestions"


class ReplaceHomonymsRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.el.ReplaceHomonymsRule: wrong usage of
    homonyms (phrases of /el/replace.txt)."""

    def get_file_names(self):
        return ['/el/replace.txt']

    def get_id(self):
        return 'GREEK_HOMONYMS_REPLACE'

    def get_description(self):
        return 'Έλεγχος για λανθασμένη χρήση ομόηχων λέξεων σε μια πρόταση'

    def get_short(self):
        return 'Λανθασμένη χρήση της λέξης'

    def get_message(self):
        return 'Μήπως εννοούσατε $suggestions?'


class GreekSpecificCaseRule(AbstractSpecificCaseRule):
    """Port of org.languagetool.rules.el.GreekSpecificCaseRule: phrases of
    /el/specific_case.txt with a special capitalization."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Κατοικώ στις <marker>Ηνωμένες πολιτείες</marker>.',
                              'Κατοικώ στις <marker>Ηνωμένες Πολιτείες</marker>.')

    def get_phrases_path(self):
        return '/el/specific_case.txt'

    def get_initial_capital_message(self):
        return 'Οι λέξεις της συγκεκριμένης έκφρασης χρείαζεται να ξεκινούν με κεφαλαία γράμματα.'

    def get_other_capitalization_message(self):
        return 'Η συγκεκριμένη έκφραση γράφεται σύμφωνα με την προτεινόμενη κεφαλαιοποίηση.'

    def get_short_message(self):
        return 'Ειδική κεφαλαιοποίηση'

    def get_id(self):
        return 'EL_SPECIFIC_CASE'

    def get_description(self):
        return 'Ελέγχει αν κάποιες λέξεις χρειάζονται κεφαλαίο το πρώτο τους γράμμα'


# adverbs used to add to what the previous sentence mentioned (English example: Also),
# to express contrast to it (English example: Contrarily) and to explain it
# (English example: Specifically); java.util.HashSets in Java, the
# suggestions are in their iteration order
_ADD_ADVERBS = java_hash_set_order(['Επίσης', 'Επιπρόσθετα', 'Ακόμη', 'Επιπλέον', 'Συμπληρωματικά'])
_CONTRAST_ADVERBS = java_hash_set_order(['Αντίθετα', 'Ωστόσο', 'Εντούτοις', 'Εξάλλου'])
_EXPLAIN_ADVERBS = java_hash_set_order(['Δηλαδή', 'Ειδικότερα', 'Ειδικά', 'Συγκεκριμένα'])
_ADVERBS = frozenset(_ADD_ADVERBS + _CONTRAST_ADVERBS + _EXPLAIN_ADVERBS)
_EXCEPTIONS = frozenset(('Ο', 'Η', 'Το', 'Οι', 'Τα', 'Ένας', 'Μία', 'Ένα'))


class GreekWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.el.GreekWordRepeatBeginningRule:
    successive sentences beginning with the same word; the articles are
    exceptions, for some adverbs alternatives are suggested."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Επίσης, παίζω ποδόσφαιρο. <marker>Επίσης</marker>, παίζω μπάσκετ.',
                              'Επίσης, παίζω ποδόσφαιρο. <marker>Επιπλέον</marker>, παίζω μπάσκετ.')

    def get_id(self):
        return 'GREEK_WORD_REPEAT_BEGINNING_RULE'

    def is_exception(self, token):
        return super().is_exception(token) or token in _EXCEPTIONS

    def is_adverb(self, atr):
        return atr.token in _ADVERBS

    def get_suggestions(self, atr):
        tok = atr.token
        for adverbs in (_ADD_ADVERBS, _CONTRAST_ADVERBS, _EXPLAIN_ADVERBS):
            if tok in adverbs:
                return [adv for adv in adverbs if adv != tok]
        return []


# map from stressed to unstressed form and unstressed to stressed form
_UNSTRESSED_SFX = ('ος', 'ου', 'ο', 'ον', 'οι', 'ων', 'ους', 'η', 'ης', 'ην', 'ες', 'α')
_STRESSED_SFX = ('ός', 'ού', 'ό', 'όν', 'οί', 'ών', 'ούς', 'ή', 'ής', 'ήν', 'ές', 'ά')
_SUFFIX_MAP = dict(zip(_STRESSED_SFX, _UNSTRESSED_SFX))
_SUFFIX_MAP.update(zip(_UNSTRESSED_SFX, _STRESSED_SFX))
_STRESSED_SUFFIX_RE = '|'.join(_STRESSED_SFX)
# an arabic number followed by a possible suffix
_NUMERAL = jregex.compile('([1-9][0-9]*)(' + _STRESSED_SUFFIX_RE + ''.join('|' + s for s in _UNSTRESSED_SFX) + ')')
# an arabic number that needs stress (we know the token can not start with 0)
_STRESSED_NUMBER = jregex.compile('[0-9]*[0|2-9]0')
# a stressed suffix
_STRESSED_SUFFIX = jregex.compile(_STRESSED_SUFFIX_RE)


class NumeralStressRule(Rule):
    """Port of org.languagetool.rules.el.NumeralStressRule: the stress of the
    suffix of ordinal numbers written with arabic digits (stressed after
    multiples of ten except those ending in 10, like 20ός, unstressed
    otherwise, like 1ος, 2010ες)."""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.language = language
        self.category = Category('ORTHOGRAPHY', 'Orthography')
        self.loc_quality_issue_type = 'Misspelling'
        self.add_example_pair(
            'Ο <marker>20ος</marker> αιώνας μαζί με τον 21ο αιώνα κατατάσσεται από τους ιστορικούς στη '
            'Σύγχρονη Ιστορία.',
            'Ο <marker>20ός</marker> αιώνας μαζί με τον 21ο αιώνα κατατάσσεται από τους ιστορικούς στη '
            'Σύγχρονη Ιστορία.')

    def get_id(self):
        return 'GREEK_ORTHOGRAPHY_NUMERAL_STRESS'

    def get_description(self):
        return 'Έλεγχος τονισμού αριθμητικών'

    def match(self, sentence):
        out = []
        for token in sentence.non_blank_tokens:
            m = _NUMERAL.fullmatch(token.token)
            if m is not None:
                number = m.group(1)
                suffix = m.group(2)
                needs_stress = _STRESSED_NUMBER.fullmatch(number) is not None
                has_stress = _STRESSED_SUFFIX.fullmatch(suffix) is not None
                if needs_stress != has_stress:
                    suggestion = number + _SUFFIX_MAP[suffix]
                    msg = '<suggestion>' + suggestion + '</suggestion>'
                    out.append(RuleMatch(self, sentence, token.start_pos, token.end_pos, msg,
                                         'Πρόβλημα ορθογραφίας'))
        return out
