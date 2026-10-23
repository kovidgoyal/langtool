"""Port of org.languagetool.rules.el.NumeralStressRuleTest,
ReplaceHomonymsRuleTest, GreekRedundancyRuleTest, GreekSpecificCaseRuleTest
and GreekWordRepeatBeginningRuleTest, plus checks of the other properties of
the Greek rules (org.languagetool.rules.el)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.el.rules import (GreekRedundancyRule, GreekSpecificCaseRule, GreekWordRepeatBeginningRule,
                                    NumeralStressRule, ReplaceHomonymsRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module')
def lt():
    require_dictionaries('el')
    return JLanguageTool(get_language('el'))


def _matches(rule, lt, sentence):
    return rule.match(lt.get_analyzed_sentence(sentence))


# --- NumeralStressRuleTest ---

@pytest.mark.parametrize('sentence', ['1ος', '2η', '3ο', '20ός', '30ή', '40ό', '1000ών', '1010ες'])
def test_numeral_stress_correct(lt, sentence):
    """NumeralStressRuleTest.testRule (assertCorrect)"""
    rule = NumeralStressRule(messages_for('el'))
    assert len(_matches(rule, lt, sentence)) == 0


@pytest.mark.parametrize('sentence, correction', [
    ('4ός', '4ος'), ('5ή', '5η'), ('6ό', '6ο'), ('100ος', '100ός'), ('200η', '200ή'), ('300ο', '300ό'),
    ('2000ων', '2000ών'), ('2010ές', '2010ες'), ('2020α', '2020ά'),
])
def test_numeral_stress_incorrect(lt, sentence, correction):
    """NumeralStressRuleTest.testRule (assertIncorrect)"""
    rule = NumeralStressRule(messages_for('el'))
    matches = _matches(rule, lt, sentence)
    assert len(matches) == 1
    assert len(matches[0].suggested_replacements) == 1
    assert matches[0].suggested_replacements[0] == correction


def test_numeral_stress_rule_properties(lt):
    rule = NumeralStressRule(messages_for('el'))
    assert rule.get_id() == 'GREEK_ORTHOGRAPHY_NUMERAL_STRESS'
    assert rule.get_description() == 'Έλεγχος τονισμού αριθμητικών'
    assert (rule.category.id, rule.category.name) == ('ORTHOGRAPHY', 'Orthography')
    assert rule.loc_quality_issue_type == 'Misspelling'
    example, = rule.incorrect_examples
    assert example.corrections == ['20ός']
    m, = _matches(rule, lt, 'Ο 20ος αιώνας και ο 21ο αιώνας, 015ος 3ους.')
    assert (m.from_pos, m.to_pos, m.message, m.short_message) == (
        2, 6, '<suggestion>20ός</suggestion>', 'Πρόβλημα ορθογραφίας')
    # the whole token must be a number with a suffix
    assert _matches(rule, lt, '20όςα 020ος x20ος') == []


# --- ReplaceHomonymsRuleTest ---

@pytest.fixture(scope='module')
def homonyms_rule():
    return ReplaceHomonymsRule(messages_for('el'), get_language('el'))


def test_replace_homonyms_rule(lt, homonyms_rule):
    """ReplaceHomonymsRuleTest.testRule"""
    assert len(_matches(homonyms_rule, lt, 'Στην Ελλάδα επικρατεί εύκρατο κλίμα.')) == 0
    assert len(_matches(homonyms_rule, lt, 'Καλή τύχη σου εύχομαι.')) == 0


def test_replace_homonyms_rule_inside_of_sentence(lt, homonyms_rule):
    """ReplaceHomonymsRuleTest.testRuleInsideOfSentence"""
    matches = _matches(homonyms_rule, lt, 'Του ευχήθηκα καλή τείχη για το διαγώνισμα.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'καλή τύχη'


def test_replace_homonyms_rule_beginning_of_sentence(lt, homonyms_rule):
    """ReplaceHomonymsRuleTest.testRuleBegginingOfSentence"""
    matches = _matches(homonyms_rule, lt, 'Τεχνητό κόμμα είναι μια ακραία μορφή αναισθησίας.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Τεχνητό κώμα'


def test_replace_homonyms_rule_with_capitalization(lt, homonyms_rule):
    """ReplaceHomonymsRuleTest.testRuleWithCapitalization"""
    matches = _matches(homonyms_rule, lt, 'γάλος πρόεδρος.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Γάλλος πρόεδρος'


def test_replace_homonyms_rule_properties(lt, homonyms_rule):
    assert homonyms_rule.get_id() == 'GREEK_HOMONYMS_REPLACE'
    assert homonyms_rule.get_short() == 'Λανθασμένη χρήση της λέξης'
    assert homonyms_rule.category.id == 'MISC'
    m, = _matches(homonyms_rule, lt, 'Του ευχήθηκα καλή τείχη.')
    assert (m.from_pos, m.to_pos) == (13, 23)
    assert m.message == 'Μήπως εννοούσατε <suggestion>καλή τύχη</suggestion>?'


# --- GreekRedundancyRuleTest ---

@pytest.fixture(scope='module')
def redundancy_rule():
    return GreekRedundancyRule(messages_for('el'), get_language('el'))


def test_redundancy_rule(lt, redundancy_rule):
    """GreekRedundancyRuleTest.testRule"""
    assert len(_matches(redundancy_rule, lt, 'Τώρα μπαίνω στο σπίτι.')) == 0
    assert len(_matches(redundancy_rule, lt, 'Απόψε θα βγω.')) == 0


def test_redundancy_rule_within_sentence(lt, redundancy_rule):
    """GreekRedundancyRuleTest.testRuleWithinSentence"""
    matches = _matches(redundancy_rule, lt, 'Τώρα μπαίνω μέσα στο σπίτι.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'μπαίνω'


def test_redundancy_rule_beginning_of_sentence(lt, redundancy_rule):
    """GreekRedundancyRuleTest.testRuleBegginingOfSentence"""
    matches = _matches(redundancy_rule, lt, 'Απόψε το βράδυ θα βγω.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Απόψε'


def test_redundancy_rule_multiple_suggestions(lt, redundancy_rule):
    """GreekRedundancyRuleTest.testRuleMultipleSuggestions"""
    matches = _matches(redundancy_rule, lt, 'Το μαγαζί ήταν ωραίο, αλλά όμως δεν πέρασα καλά.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'αλλά,όμως'


def test_redundancy_rule_properties(lt, redundancy_rule):
    assert redundancy_rule.get_id() == 'EL_REDUNDANCY_REPLACE'
    assert redundancy_rule.get_short() == 'Πλεονασμός'
    assert redundancy_rule.category.id == 'REDUNDANCY'
    assert redundancy_rule.loc_quality_issue_type == 'Style'
    m, = _matches(redundancy_rule, lt, 'Τώρα μπαίνω μέσα στο σπίτι.')
    assert (m.from_pos, m.to_pos) == (5, 16)
    assert m.message == "'μπαίνω μέσα' είναι πλεονασμός. Γενικά, είναι προτιμότερο το: <suggestion>μπαίνω</suggestion>"
    example, = redundancy_rule.incorrect_examples
    assert example.corrections == ['ανεβαίνω']
    m, = _matches(redundancy_rule, lt, 'Μου αρέσει να ανεβαίνω πάνω σε δέντρα.')
    assert m.suggested_replacements == ['ανεβαίνω']


# --- GreekSpecificCaseRuleTest ---

@pytest.fixture(scope='module')
def specific_case_rule():
    return GreekSpecificCaseRule(messages_for('en'))


def _assert_good(rule, lt, text):
    assert len(_matches(rule, lt, text)) == 0


def _assert_bad(rule, lt, text):
    matches = _matches(rule, lt, text)
    assert len(matches) == 1
    return matches


def test_specific_case_rule(lt, specific_case_rule):
    """GreekSpecificCaseRuleTest.testRule"""
    rule = specific_case_rule
    _assert_good(rule, lt, 'Ηνωμένες Πολιτείες')
    _assert_good(rule, lt, 'Κατοικώ στις Ηνωμένες Πολιτείες.')
    _assert_good(rule, lt, 'Κατοικώ στις ΗΝΩΜΕΝΕΣ ΠΟΛΙΤΕΙΕΣ.')
    _assert_bad(rule, lt, 'ηνωμένες πολιτείες')
    _assert_bad(rule, lt, 'ηνωμένες Πολιτείες')
    _assert_bad(rule, lt, 'Ηνωμένες πολιτείες')

    matches1 = _assert_bad(rule, lt, 'Κατοικώ στις Ηνωμένες πολιτείες.')
    assert matches1[0].from_pos == 13
    assert matches1[0].to_pos == 31
    assert matches1[0].suggested_replacements == ['Ηνωμένες Πολιτείες']
    assert matches1[0].message == ('Οι λέξεις της συγκεκριμένης έκφρασης χρείαζεται να ξεκινούν με κεφαλαία '
                                   'γράμματα.')

    matches3 = _assert_bad(rule, lt, 'Κατοικώ στις Ηνωμένες  πολιτείες.')  # note the two spaces
    assert matches3[0].from_pos == 13
    assert matches3[0].to_pos == 32


def test_specific_case_rule_properties(lt, specific_case_rule):
    rule = specific_case_rule
    assert rule.get_id() == 'EL_SPECIFIC_CASE'
    assert rule.get_description() == 'Ελέγχει αν κάποιες λέξεις χρειάζονται κεφαλαίο το πρώτο τους γράμμα'
    assert rule.get_short_message() == 'Ειδική κεφαλαιοποίηση'
    assert [e.example for e in rule.incorrect_examples] == ['Κατοικώ στις <marker>Ηνωμένες πολιτείες</marker>.']


# --- GreekWordRepeatBeginningRuleTest ---

def test_word_repeat_beginning_rule(lt):
    """GreekWordRepeatBeginningRuleTest.testRule"""
    # ================== correct sentences ===================
    # two successive sentences that start with the same non-adverb word.
    assert len(lt.check('Εγώ παίζω ποδόσφαιρο. Εγώ παίζω μπάσκετ')) == 0
    # three successive sentences that start with the same exception word ("Το").
    assert len(lt.check('Το αυτοκίνητο είναι καινούργιο. Το ποδήλατο είναι παλιό. Το καράβι είναι '
                        'καινούργιο.')) == 0
    # two successive sentences that start with the same exception word ("Μία").
    assert len(lt.check('Μία περίπτωση εξηγήθηκε ήδη. Μία άλλη θα αναλυθεί παρακάτω.')) == 0

    # =================== errors =============================
    # two successive sentences that start with one of the saved adverbs ("Επίσης").
    matches2 = lt.check('Επίσης, μιλάω Ελληνικά. Επίσης, μιλάω Αγγλικά.')
    assert len(matches2) == 1
    for sugg in ('Επιπλέον', 'Ακόμη', 'Επιπρόσθετα', 'Συμπληρωματικά'):
        assert sugg in matches2[0].suggested_replacements
    # three successive sentences that start with the same non-exception word (no suggestions to check).
    matches1 = lt.check('Εγώ παίζω μπάσκετ. Εγώ παίζω ποδόσφαιρο. Εγώ παίζω βόλεϊ.')
    assert len(matches1) == 1


def test_word_repeat_beginning_rule_suggestion_order(lt):
    """The suggestions are in the iteration order of the Java HashSets (as
    checked with Java)"""
    matches = lt.check('Επίσης, μιλάω Ελληνικά. Επίσης, μιλάω Αγγλικά. Ωστόσο, α β. Ωστόσο, γ δ. Δηλαδή, α β. '
                       'Δηλαδή, γ δ.')
    assert [(m.get_specific_rule_id(), m.from_pos, m.suggested_replacements) for m in matches] == [
        ('GREEK_WORD_REPEAT_BEGINNING_RULE', 24, ['Επιπρόσθετα', 'Επιπλέον', 'Συμπληρωματικά', 'Ακόμη']),
        ('GREEK_WORD_REPEAT_BEGINNING_RULE', 60, ['Αντίθετα', 'Εντούτοις', 'Εξάλλου']),
        ('GREEK_WORD_REPEAT_BEGINNING_RULE', 86, ['Ειδικά', 'Ειδικότερα', 'Συγκεκριμένα'])]
    rule = GreekWordRepeatBeginningRule(messages_for('el'), get_language('el'))
    assert rule.get_id() == 'GREEK_WORD_REPEAT_BEGINNING_RULE'
    assert rule.category.id == 'REPETITIONS_STYLE'
    assert rule.is_exception('Ένα') and rule.is_exception(':') and not rule.is_exception('Εγώ')
