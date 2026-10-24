"""Port of the tests of the French rules: org.languagetool.rules.fr.
CompoundRuleTest, QuestionWhitespaceRuleTest, QuestionWhitespaceStrictRuleTest,
SimpleReplaceRuleTest, FrenchRepeatedWordsRuleTest,
GenericUnpairedBracketsRuleTest, MorfologikFrenchSpellerRuleTest (skipped,
spell checking; its suggestions for single words are tested with the ported
suggestion part, MorfologikFrenchSpellerCheck.get_spelling_suggestions),
FrenchConfusionProbabilityRuleTest (skipped, language model),
FrenchRemoteRuleFilterTest and GrammalecteRuleTest (skipped, remote rules),
plus checks of the French filters."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.fr.agreement import PostponedAdjectiveConcordanceFilter
from langtool.lang.fr.filters import (DateCheckFilter, DMYDateCheckFilter, FindSuggestionsFilter,
                                      FrenchNumberInWordFilter, FrenchPartialPosTagFilter,
                                      FrenchSuppressMisspelledSuggestionsFilter, InterrogativeVerbFilter,
                                      MakeContractionsFilter, NewYearDateFilter, SuggestionsFilter,
                                      WordWithDeterminerFilter)
from langtool.lang.fr.rules import (CompoundRule, FrenchRepeatedWordsRule, QuestionWhitespaceRule,
                                    QuestionWhitespaceStrictRule, SimpleReplaceRule)
from langtool.lang.fr.spelling import prepare_line_for_speller
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.core import GenericUnpairedBracketsRule
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('fr')


@pytest.fixture(scope='module')
def french():
    return get_language('fr')


@pytest.fixture(scope='module')
def lt(french):
    return JLanguageTool(french)


class FakeRule(Rule):
    def __init__(self, language=None):
        super().__init__()
        self.language = language

    def get_id(self):
        return 'FAKE-RULE'

    def get_description(self):
        return 'Fake rule'


def _java_list(items):
    return '[' + ', '.join(items) + ']'


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule(french, lt):
    """CompoundRuleTest.testRule (setUp runs AbstractCompoundRuleTest.testAllCompounds,
    which only prints warnings for possibly misspelled suggestions)"""
    rule = CompoundRule(messages_for('fr'), french, None)
    data = rule.get_compound_rule_data()
    for compound in data.incorrect_compounds:
        if compound in data.dash_suggestion:
            rule.is_misspelled(compound.replace(' ', '-'))
        if compound in data.joined_suggestion:
            rule.is_misspelled(rule.merge_compound(compound, compound in data.joined_lower_case_suggestion))
    # correct sentences:
    for text in ('Jésus-Christ', 'Congo-Brazzaville', 'vidéo-clip', 'anglo-saxon'):
        _check(lt, rule, 0, text)
    # incorrect sentences:
    for text in ('Jésus Christ', 'Congo Brazzaville', 'Congo- Brazzaville', 'Congo -Brazzaville'):
        _check(lt, rule, 1, text)
    for text, suggestion in (('rez-de chaussée', 'rez-de-chaussée'), ('Congo -Brazzaville', 'Congo-Brazzaville'),
                             ('Congo- Brazzaville', 'Congo-Brazzaville'), ('Congo - Brazzaville', 'Congo-Brazzaville'),
                             ('le - quel', 'lequel'), ('le quel', 'lequel'), ('le- quel', 'lequel'),
                             ('anglo saxon', 'anglo-saxon'), ('anglo- saxon', 'anglo-saxon'),
                             ('anglo -saxon', 'anglo-saxon'), ('anglo - saxon', 'anglo-saxon')):
        _check(lt, rule, 1, text, suggestion)


def test_compound_rule_specific_ids(french, lt):
    rule = CompoundRule(messages_for('fr'), french, None)
    m, = rule.match(lt.get_analyzed_sentence('Le Haut Rhin.'))
    assert m.rule.get_id() == 'FR_COMPOUNDS_HAUT_RHIN'
    assert m.rule.get_description() == 'Mots avec trait d’union : Haut Rhin'
    assert m.suggested_replacements == ['Haut-Rhin']
    assert rule.is_misspelled('blablabla-blublu') and not rule.is_misspelled('maison')


# --- QuestionWhitespaceRuleTest ---

def test_question_whitespace_rule(french):
    """QuestionWhitespaceRuleTest.testRule"""
    rule = QuestionWhitespaceRule(messages_for('en'), french)
    lt = JLanguageTool(french)

    def match(text):
        return rule.match(lt.get_analyzed_sentence(text))

    # correct sentences:
    for text in ("C'est vrai\u00a0!", "Qu'est ce que c'est\u00a0?",
                 "L'enjeu de ce livre est donc triple\u00a0: philosophique", 'Bonjour :)', '5/08/2019 23:30',
                 "C'est vrai\u00a0!!", "C'est vrai\u00a0??", '☀️9:00', '00:80:41:ae:fd:7e'):
        assert len(match(text)) == 0, text
    # TestTools.disableAllRulesExcept(lt, "FRENCH_WHITESPACE")
    for r in lt.get_all_rules():
        if r.get_id() != 'FRENCH_WHITESPACE':
            lt.disable_rule(r.get_id())
    for text in ('« Je suis Chris… »', '« Je suis Chris ! »', 'Je suis.[!]', 'Je suis[?]', 'Je suis(?)', '1;2;3',
                 'asd@dsa.fr;test@foo.com;'):
        assert len(lt.check(text)) == 0, text
    # errors:
    assert len(match("C'est vrai!")) == 1
    assert len(match("Qu'est ce que c'est?")) == 1
    assert len(match("L'enjeu de ce livre est donc triple: philosophique;")) == 2
    matches1 = match("L'enjeu de ce livre est donc triple: philosophique ;")
    assert len(matches1) == 1
    assert matches1[0].from_pos == 29
    assert matches1[0].to_pos == 36
    assert _java_list(matches1[0].suggested_replacements) == '[triple\u00a0:]'
    # guillemets:
    matches2 = match('LanguageTool offre une «vérification» orthographique.')
    assert len(matches2) == 1
    assert matches2[0].from_pos == 23
    assert matches2[0].to_pos == 37
    assert _java_list(matches2[0].suggested_replacements) == '[«\u00a0vérification\u00a0»]'
    matches3 = match("Le guillemet ouvrant est suivi d'un espace insécable\u00a0: «mais le lieu [...] et le "
                     "guillemet fermant est précédé d'un espace insécable\u00a0: [...] littérature».")
    assert len(matches3) == 2
    assert _java_list(matches3[0].suggested_replacements) == '[«\u00a0mais]'
    assert matches3[0].from_pos == 55
    assert matches3[0].to_pos == 60
    assert _java_list(matches3[1].suggested_replacements) == '[littérature\u00a0»]'
    assert matches3[1].from_pos == 141
    assert matches3[1].to_pos == 153


def test_question_whitespace_strict_rule(french, lt):
    """QuestionWhitespaceStrictRuleTest.testRule"""
    rule = QuestionWhitespaceStrictRule(messages_for('en'), french)

    def match(text):
        return rule.match(lt.get_analyzed_sentence(text))

    # correct sentences:
    for text in ("C'est vrai\u00a0!", "Qu'est ce que c'est\u00a0?",
                 "L'enjeu de ce livre est donc triple\u00a0: philosophique", 'Bonjour :)'):
        assert len(match(text)) == 0, text
    # covered by rule FRENCH_WHITESPACE
    for text in ("C'est vrai!", "Qu'est ce que c'est?", "L'enjeu de ce livre est donc triple: philosophique;",
                 "Le guillemet ouvrant est suivi d'un espace insécable\u00a0: «mais le lieu [...] et le guillemet "
                 "fermant est précédé d'un espace insécable\u00a0: [...] littérature»."):
        assert len(match(text)) == 0, text
    # covered partially by rule FRENCH_WHITESPACE
    matches = match("L'enjeu de ce livre est donc triple: philosophique ;")
    assert len(matches) == 1
    assert matches[0].from_pos == 50
    assert matches[0].to_pos == 52
    assert _java_list(matches[0].suggested_replacements) == '[\u202f;]'
    # errors:
    assert len(match("C'est vrai !")) == 1
    assert len(match("Qu'est ce que c'est ?")) == 1
    assert len(match('Bonjour : )')) == 1
    # guillemets
    matches = match("Le guillemet ouvrant est suivi d'un espace insécable\u00a0: « mais le lieu [...] et le "
                    "guillemet fermant est précédé d'un espace insécable\u00a0: [...] littérature ».")
    assert len(matches) == 2


def test_question_whitespace_rule_details(french):
    rule = QuestionWhitespaceStrictRule(messages_for('fr'), french)
    assert rule.get_id() == 'FRENCH_WHITESPACE_STRICT'
    assert rule.tags == ['picky'] and rule.default_off and rule.default_temp_off
    assert QuestionWhitespaceRule(messages_for('fr'), french).get_description() == \
        'Insertion des espaces fines insécables'
    assert len(rule.get_anti_patterns()) == 7


# --- SimpleReplaceRuleTest ---

def test_simple_replace_rule(french, lt):
    """SimpleReplaceRuleTest.testRule"""
    rule = SimpleReplaceRule(messages_for('fr'), french)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence("J'ai pas de quoi"))) == 0
    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence('jai pas de quoi'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == "j'ai"
    matches = rule.match(lt.get_analyzed_sentence('Jai pas de quoi'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == "J'ai"
    assert matches[0].message == "Vouliez-vous dire « j'ai » ?"
    assert matches[0].rule.get_id() == 'FR_SIMPLE_REPLACE_SIMPLE_JAI'
    assert rule.category.id == 'TYPOS' and rule.loc_quality_issue_type == 'Misspelling'


# --- FrenchRepeatedWordsRuleTest ---

def test_repeated_words_rule(french, lt):
    """FrenchRepeatedWordsRuleTest.testRule"""
    rule = FrenchRepeatedWordsRule(messages_for('fr'))

    def matches(sentences):
        return rule.match(lt.analyze_text(sentences))

    assert len(matches('Elle est notamment phénoménale. Les choses sont notamment compliquées')) == 0
    m = matches('Elle est notamment phénoménale. Les choses sont notamment compliquées.')
    assert len(m) == 1
    assert _java_list(m[0].suggested_replacements) == \
        '[particulièrement, spécialement, singulièrement, surtout, spécifiquement]'
    m = matches('Elle est maintenant phénoménale. Les choses sont maintenant compliquées.')
    assert len(m) == 1
    assert _java_list(m[0].suggested_replacements) == '[présentement, ce jour-ci, désormais, à présent]'


def test_repeated_words_rule_details(french):
    rule = FrenchRepeatedWordsRule(messages_for('fr'))
    assert rule.get_id() == 'FR_REPEATEDWORDS'
    assert rule.adjust_postag('J e sp') == 'J . .*'
    assert rule.adjust_postag('N m s') == 'N [me] sp?'
    assert rule.adjust_postag('J f p') == 'J [fe] s?p'
    assert rule.adjust_postag('V inf') == 'V inf'


# --- GenericUnpairedBracketsRuleTest ---

def test_unpaired_brackets_rule(french):
    """GenericUnpairedBracketsRuleTest.testFrenchRule"""
    lt = JLanguageTool(french)
    rule = next(r for r in lt.get_all_rules() if isinstance(r, GenericUnpairedBracketsRule))

    def assert_matches(text, expected):
        assert len(rule.match([lt.get_analyzed_sentence(text)])) == expected, text

    # correct sentences:
    assert_matches("(Qu'est ce que c'est\u00a0?)", 0)
    # Saxon genitive
    assert_matches("Harper's Dictionary of Classical Antiquities", 0)
    assert_matches('Harper’s Dictionary of Classical Antiquities', 0)
    # incorrect sentences:
    assert_matches("(Qu'est ce que c'est\u00a0?", 1)


# --- MorfologikFrenchSpellerRuleTest ---

@pytest.mark.skip(reason='spell checking is not ported: MorfologikFrenchSpellerRuleTest tests the rule matches of '
                         'MorfologikFrenchSpellerRule (FR_SPELLING_RULE)')
def test_morfologik_french_speller_rule():
    """Port of org.languagetool.rules.fr.MorfologikFrenchSpellerRuleTest"""


# the suggestions of MorfologikFrenchSpellerRule.getSpellingSuggestions (the
# words of MorfologikFrenchSpellerRuleTest that are single tokens; checked
# with Java)
@pytest.mark.parametrize('word,expected', [
    ('darriver', ["d'arriver", 'arriver', 'dériver']),
    ('Wordpress', ['WordPress', 'Bordures', 'Pourpres', 'Pourprés', 'Mordorés']),
    ('wordpress', ['WordPress', 'bordures', 'pourpres', 'pourprés', 'mordorés']),
    ('Playstation', ['PlayStation', 'Play station', 'Plantation']),
    ('Décu', ['Déçu', "D'Esse", "D'Essé", 'Reçu', 'Dessus']),
    ('etant', ['étant', 'était', 'tant', 'état', 'jetant']),
    ('Cliqez', ['Cliquez', 'Clivez']),
    ('cliqez', ['cliquez', 'clivez']),
    ('problemes', ['problèmes', 'problème']),
    ('damazon', ["d'Amazon", "d'amazone", "d'Amazone", 'Amazon', 'Damazan']),
    ('coulurs', ['couleurs', 'coulure', 'coulures', 'Coulours']),
    ('Den', ['De', 'Des', 'En', 'Dès', 'Der']),
    ('camara', ['caméra', 'Samara', 'Tamara', 'camard', 'Cabara']),
    ('deja', ['déjà', "d'EA", "d'ESA", "d'ENA", "d'Éva"]),
    ('BretagneItinéraire', ['Bretagne Itinéraire']),
    ('Parcontre', ['Par contre']),
    ('parcontre', ['par contre']),
    ('étaistu', ['étais-tu', 'étais tu']),
    ('voulezvous', ['voulez-vous', 'voulez vous']),
    ('ecoutemoi', ['écoute-moi', 'coûte-moi', 'écouterai']),
    ('mappelle', ["m'appelle", 'mappe-le', 'appelle', 'rappelle', 'rappelé']),
    ('mapelle', ['ma pelle', "m'appelle", "m'Appelle", "m'appeler", 'mappe-le']),
    ('allonsy', ['allons-y', 'Alonso', 'allons', 'allons y']),
    ('buvezen', ['buvez-en', 'buvez en']),
    ('avaisje', ['avais-je', 'avais je']),
    ('depechetoi', ['dépêche-toi', 'dépêcherai']),
    ('sattendre', ["s'attendre", 'attendre']),
    ('Lhomme', ["L'homme", 'Homme', 'Lomme', 'Chômé', 'Chôme']),
    ('dhommes', ["d'hommes", 'hommes', 'chômés', 'chômes', 'dromes']),
    ('ladolescence', ["l'adolescence", 'adolescence']),
    ('dIsraël', ["d'Israël", 'Israël']),
    ('dOrient', ["d'Orient", 'Lorient', 'dorment', 'orient', 'dorien']),
    ('AAAAAAAAAAAH', []),
    ('123heures', ['123 heures']),
    ('©heures', ['© heures']),
    ('macrodiscipline', []),
    ('windows1', ['Windows']),
    ('windows95', ['Windows 95']),
    ('à1930', ['à 1930', 'COP30']),
    ('saperçoit', ['sa perçoit', "s'aperçoit", 'aperçoit']),
    ('saperçu', ['sa perçu', 'aperçu']),
    ('Mcdonald', ['McDonald', 'Macdonald', "McDonald's", 'Donald', 'McDonald’s']),
    ('simpple', ['simple', 'Simplé', 'simples', 'simplet', 'simplex']),
    ('thisisanerror', []),
    ('mm2', ['mm²', 'mm', 'ma', 'me', 'mi']),
    ('voulai', ['voulais', 'voulait', 'coulé', 'voûté', 'foulé']),
    ('ecrit-il', ['écrit-il', 'écrit', 'écrite', 'écrits', 'écrivain']),
    # not misspelled
    ('LanguageTool', []),
    ('maison', []),
])
def test_spelling_suggestions(french, word, expected):
    """MorfologikFrenchSpellerRule.getSpellingSuggestions (the first five)"""
    assert french.get_default_spelling_rule().get_spelling_suggestions(word)[:5] == expected


def test_spelling_suggestions_complete(french):
    check = french.get_default_spelling_rule()
    assert check.get_spelling_suggestions('decodés') == [
        'décodés', 'décodes', 'de codés', "d'écoles", "d'équidés", "d'érodés", "d'encodés", 'décodais', 'décorés',
        'décidés', 'décédés', 'décoder', 'décades', 'décodé', 'démodés', 'décode', 'décodée', 'décodées', 'décotes',
        'décodait', 'dessoles', 'dessolés', 'dessoudes', 'dessoudés', 'décauses', 'décausés', 'décides', 'décodai',
        'décodas', 'décodez', 'décordes', 'décordés', 'décores', 'décotés', 'décèdes', 'démodes', 'dérodes',
        'dérodés', 'recodes', 'recodés', 'déboudes', 'déboudés']
    assert check.get_spelling_suggestions('camara') == [
        'caméra', 'Samara', 'Tamara', 'camard', 'Cabara', 'cambra', 'camera', 'canara', 'ramarra', 'cama ra']


@pytest.mark.skip(reason='language model rules are not ported: FrenchConfusionProbabilityRuleTest constructs '
                         'FrenchConfusionProbabilityRule with a fake language model')
def test_confusion_probability_rule():
    """Port of org.languagetool.rules.fr.FrenchConfusionProbabilityRuleTest"""


@pytest.mark.skip(reason='remote rules are not ported: FrenchRemoteRuleFilterTest tests the filters of '
                         'remote-rule-filters.xml for remote (AI) rules')
def test_remote_rule_filters():
    """Port of org.languagetool.rules.fr.FrenchRemoteRuleFilterTest"""


@pytest.mark.skip(reason='remote rules are not ported: GrammalecteRuleTest tests GrammalecteRule, which queries '
                         'a Grammalecte server')
def test_grammalecte_rule():
    """Port of org.languagetool.rules.fr.GrammalecteRuleTest"""


# --- filters ---

def _fake_match(french, message='msg', suggestion=None, from_pos=0, to_pos=5, sentence=None):
    m = RuleMatch(FakeRule(french), sentence, from_pos, to_pos, message)
    if suggestion is not None:
        m.set_suggested_replacement(suggestion)
    return m


def test_date_filters(french):
    """DateCheckFilter, DMYDateCheckFilter and NewYearDateFilter
    (DateFilterHelper)"""
    f = DateCheckFilter()
    assert f.get_day_of_week('Dimanche') == 1
    assert f.get_day_of_week('sam') == 7
    assert f.get_day_of_week('mercredi') == 4
    assert f.get_month('mars') == 3 and f.get_month('fév.') == 2 and f.get_month('Fevrier') == 2
    assert f.get_month('juin') == 6 and f.get_month('juillet') == 7 and f.get_month('Août') == 8
    assert f.get_month('aout') == 8 and f.get_month('déc.') == 12 and f.get_month('dec') == 12
    with pytest.raises(RuntimeError):
        f.get_month('jui')
    with pytest.raises(RuntimeError):
        f.get_day_of_week('foo')
    assert NewYearDateFilter().get_month('Janvier') == 1
    with pytest.raises(RuntimeError):
        DMYDateCheckFilter().accept_rule_match(_fake_match(french), {'year': '1', 'date': '28-08-2014',
                                                                     'weekDay': '1'}, 0, [], [])
    with pytest.raises(RuntimeError):
        DMYDateCheckFilter().accept_rule_match(_fake_match(french), {'date': '28-08', 'weekDay': '1'}, 0, [], [])


def test_date_check_filter(french, lt):
    """DateCheckFilter: the weekday doesn't match the date"""
    sentence = lt.get_analyzed_sentence('Vendredi 28 août 2014.')
    tokens = sentence.non_blank_tokens[1:]
    m = RuleMatch(FakeRule(french), sentence, 0, 21, 'La date ne correspond pas à un {day} mais à un {realDay}.')
    m = DateCheckFilter().accept_rule_match(m, {'weekDay': '1', 'day': '2', 'month': '3', 'year': '4'}, 1, tokens,
                                            [1, 1, 1, 1])
    assert m.message == 'La date ne correspond pas à un vendredi mais à un jeudi.'
    assert m.suggested_replacements[:2] == ['Jeudi 28', 'Vendredi 29']


def test_find_suggestions_filter(french, lt):
    """FindSuggestionsFilter: the spelling suggestions (of a wrong word
    made from a known word) with the desired POS tag"""
    sentence = lt.get_analyzed_sentence('Ils ont des souri.')
    tokens = sentence.non_blank_tokens
    m = RuleMatch(FakeRule(french), sentence, 12, 17, 'msg')
    m.set_suggested_replacement('{suggestion}')
    m = FindSuggestionsFilter().accept_rule_match(m, {'wordFrom': '4', 'desiredPostag': 'N.*'}, 1, tokens[1:],
                                                  [])
    assert m.suggested_replacements == ['souci', 'souris', 'sourd', 'soufi', 'houri', 'soui']
    f = FindSuggestionsFilter()
    assert f.clean_suggestion("s'aperçoit") == 'aperçoit'
    assert f.clean_suggestion('nous allons bien') == 'allons'


def test_interrogative_verb_filter(french, lt):
    """InterrogativeVerbFilter: verb + pronoun suggestions"""
    sentence = lt.get_analyzed_sentence('Peut je venir ?')
    tokens = sentence.non_blank_tokens[1:]
    m = RuleMatch(FakeRule(french), sentence, 0, 7, 'msg', 'short')
    m = InterrogativeVerbFilter().accept_rule_match(m, {'PronounFrom': '2', 'VerbFrom': '1'}, 1, tokens, [])
    assert m.suggested_replacements == ['Puis-je']
    sentence = lt.get_analyzed_sentence('Prefere tu le thé ?')
    tokens = sentence.non_blank_tokens[1:]
    m = RuleMatch(FakeRule(french), sentence, 0, 10, 'msg')
    m = InterrogativeVerbFilter().accept_rule_match(m, {'PronounFrom': '2', 'VerbFrom': '1'}, 1, tokens, [])
    assert m.suggested_replacements == ['Préfères-tu']


def test_word_with_determiner_filter(french, lt):
    """WordWithDeterminerFilter: determiner + word in all genders and
    numbers, without combinations with elision errors"""
    sentence = lt.get_analyzed_sentence('Les maison.')
    tokens = sentence.non_blank_tokens[1:]
    m = RuleMatch(FakeRule(french), sentence, 0, 10, 'msg')
    m = WordWithDeterminerFilter().accept_rule_match(m, {'determinerFrom': '1', 'wordFrom': '2'}, 1, tokens, [])
    assert m.suggested_replacements == ['La maison', 'Les maisons']


def test_postponed_adjective_concordance_filter(french, lt):
    """PostponedAdjectiveConcordanceFilter: the adjective doesn't agree with
    the previous noun"""
    sentence = lt.get_analyzed_sentence('Les maisons blanc sont belles.')
    tokens = sentence.non_blank_tokens
    m = RuleMatch(FakeRule(french), sentence, 12, 17, 'msg')
    m = PostponedAdjectiveConcordanceFilter().accept_rule_match(m, {}, 3, tokens[3:], [])
    assert m is not None and m.suggested_replacements == ['blanches']
    sentence = lt.get_analyzed_sentence('Les maisons blanches sont belles.')
    m = RuleMatch(FakeRule(french), sentence, 12, 20, 'msg')
    assert PostponedAdjectiveConcordanceFilter().accept_rule_match(m, {}, 3, sentence.non_blank_tokens[3:],
                                                                   []) is None


def test_suggestion_filters(french):
    """MakeContractionsFilter, SuggestionsFilter and
    FrenchSuppressMisspelledSuggestionsFilter"""
    m = _fake_match(french)
    m.set_suggested_replacements(['de le chat', 'à les chats', 'de les', 'À le', 'dele'])
    m = MakeContractionsFilter().accept_rule_match(m, {}, 0, [], [])
    assert m.suggested_replacements == ['du chat', 'aux chats', 'des', 'au', 'dele']
    m.set_suggested_replacements(['chat', 'chats', 'Chien'])
    m = SuggestionsFilter().accept_rule_match(m, {'RemoveSuggestionsRegexp': 'CHATS?'}, 0, [], [])
    assert m.suggested_replacements == ['Chien']
    m.set_suggested_replacements(['maison', 'mmaison'])
    m = FrenchSuppressMisspelledSuggestionsFilter().accept_rule_match(m, {'suppressMatch': 'true'}, 0, [], [])
    assert m.suggested_replacements == ['maison']
    m.set_suggested_replacements(['mmaison'])
    assert FrenchSuppressMisspelledSuggestionsFilter().accept_rule_match(m, {'suppressMatch': 'true'}, 0, [],
                                                                         []) is None


def test_number_in_word_filter(french):
    """FrenchNumberInWordFilter (with the misspelling check and the
    spelling suggestions of the default spelling rule)"""
    f = FrenchNumberInWordFilter()
    m = f.accept_rule_match(_fake_match(french), {'word': 'mais0n'}, 0, [], [])
    assert m.suggested_replacements == ['maison']
    m = f.accept_rule_match(_fake_match(french), {'word': 'bonj0ur'}, 0, [], [])
    assert m.suggested_replacements == ['bonjour']


def test_partial_pos_tag_filter(french):
    """FrenchPartialPosTagFilter tags and disambiguates the token"""
    tags = FrenchPartialPosTagFilter().tag('maison')
    assert len(tags) == 1
    assert [r.pos_tag for r in tags[0].readings] == ['N f s']


def test_prepare_line_for_speller():
    """French.prepareLineForSpeller"""
    assert prepare_line_for_speller('maison') == ['maison']
    assert prepare_line_for_speller('Ho Chi Minh') == ['']
    assert prepare_line_for_speller('Ho Chi Minh\tZ e sp') == ['']
    assert prepare_line_for_speller('New York\tZ e sp') == ['New York']
    assert prepare_line_for_speller('pomme de terre\tN f s') == ['pomme de terre']
    assert prepare_line_for_speller("d'abord\tA") == ["d'abord"]
    assert prepare_line_for_speller('à cause de\tP') == ['']
    assert prepare_line_for_speller('#comment') == ['#comment']
    assert prepare_line_for_speller('x;N m s # comment') == ['x']
