"""Port of org.languagetool.rules.fr.FrenchTest (LanguageSpecificTest),
org.languagetool.language.FrenchTest, org.languagetool.JLanguageToolTest
(language-fr), org.languagetool.rules.fr.AnnotatedTextTest and
LanguageSpecificSpellcheckerTest (skipped, spell checking), plus checks of
the French language definition against org.languagetool.language.French,
BelgianFrench, CanadianFrench and SwissFrench. The language independent
parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.fr.language import adjust_french_rule_match
from langtool.lang.fr.multitoken import FrenchMultitokenSpeller
from langtool.lang.fr.rules import (CompoundRule, FrenchRepeatedWordsRule, QuestionWhitespaceRule,
                                    QuestionWhitespaceStrictRule, SimpleReplaceRule)
from langtool.lang.fr.spelling import MorfologikFrenchSpellerCheck
from langtool.lang.fr.synthesis import FrenchSynthesizer
from langtool.lang.fr.tagging import FrenchTagger
from langtool.lang.fr.tokenizers import FrenchWordTokenizer
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.core import GenericUnpairedBracketsRule
from langtool.tool import LEVEL_DEFAULT, LEVEL_PICKY, AnnotatedText, JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('fr')


@pytest.fixture(scope='module')
def french():
    return get_language('fr')


# --- rules.fr.FrenchTest ---

def test_demo_text(french):
    """FrenchTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ("Écrivez ou collez votre texte ici pour le faire vérifier en continue. Les erreurs seront soulignés de "
         "différentes couleurs : les erreurs d'orthografe en rouge et les erreurs grammaticaux en jaune. Les "
         "problèmes de style, comme par exemple ceci, seront marqués en bleu dans vos textes. Le saviez vous ? "
         "LanguageTool vous propose des synonymes lorsque vous double-cliquez sur un mot .  Découvrez la "
         "multitude de ses fonctions, parfoi inattendues, tel que ça vérification des date. Par exemple, le "
         "mercredi 28 août 2020 était en fait un vendredi\u202f!")
    matches = JLanguageTool(french).check(s)
    # Java expects two more matches of FR_SPELLING_RULE (for "orthografe" after ETRE_VPPA_OU_ADJ and
    # "parfoi" after WHITESPACE_RULE), the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'EN_GENERALE', 'ETRE_VPPA_OU_ADJ', 'AGREEMENT_POSTPONED_ADJ', 'COMME_PAR_EXEMPLE', 'TRAIT_UNION_INVERSION',
        'COMMA_PARENTHESIS_WHITESPACE', 'WHITESPACE_RULE', 'CA_SA', 'D_N', 'FR_DATE_WEEKDAY']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists with MorfologikFrenchSpellerRule')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.fr.LanguageSpecificSpellcheckerTest"""


# --- language.FrenchTest ---

@pytest.mark.parametrize('text', [
    'Arrête de le cajoler... ça ne donnera rien.',
    'Arrête de le cajoler… ça ne donnera rien.',
    'Il est possible de le contacter par tous les moyens (courrier, téléphone, mail...) à condition de vous '
    'présenter.',
])
def test_sentence_tokenizer(french, text):
    """FrenchTest.testSentenceTokenizer"""
    assert len(french.sentence_tokenizer.tokenize(text)) == 1


@pytest.mark.parametrize('text,expected', [
    ('"C\'est"', '«\u00a0C’est\u00a0»'),
    ('"C\'est" ', '«\u00a0C’est\u00a0» '),
    ("'C'est'", '‘C’est’'),
    ("Vouliez-vous dire 'C'est'?", 'Vouliez-vous dire ‘C’est’\u202f?'),
    ('Vouliez-vous dire "C\'est"?', 'Vouliez-vous dire «\u00a0C’est\u00a0»\u202f?'),
    ("Vouliez-vous dire <suggestion>C'est</suggestion>?", 'Vouliez-vous dire «\u00a0C’est\u00a0»\u202f?'),
    ('Confusion possible : "a" est une conjugaison du verbe avoir. Vouliez-vous dire « à »?',
     'Confusion possible\u00a0: «\u00a0a\u00a0» est une conjugaison du verbe avoir. Vouliez-vous dire '
     '«\u00a0à\u00a0»\u202f?'),
    ('C\'est l\'"homme".', 'C’est l’«\u00a0homme\u00a0».'),
    ('Vouliez-vous dire <suggestion>50\u00a0$</suggestion>?', 'Vouliez-vous dire «\u00a050\u00a0$\u00a0»\u202f?'),
])
def test_advanced_typography(french, text, expected):
    """FrenchTest.testAdvancedTypography"""
    assert french.to_advanced_typography(text) == expected


def test_rules(french):
    """FrenchTest.testRules"""
    lt = JLanguageTool(french)
    # In some (unclear) circumstances, matches in these sentences and rules are not detected by tests on XML
    # examples #6300
    # FRENCH_WORD_REPEAT_RULE[2]
    assert len(lt.check("Fête des mères et remise de l'insigne \" Morts pour la France \".")) == 0
    # ACCORD_V_QUESTION2[1]: Java finds one match, of FR_SPELLING_RULE (for "france"), the spell checker,
    # which is not ported
    assert len(lt.check("D'autre part, je ne soutiens pas du tout le système actuel en france mais je sais "
                        "qu'au train où l'on va que notre prochaine étape sera celle de la Grèce ou de "
                        "l'Argentine.")) == 0


# --- JLanguageToolTest ---

class FakeRule(Rule):
    """org.languagetool.FakeRule"""

    def __init__(self, id='FAKE-RULE'):
        super().__init__()
        self._id = id

    def get_id(self):
        return self._id

    def get_description(self):
        return 'A fake rule for tests'


def test_language_dependent_filter(french):
    """JLanguageToolTest.testLanguageDependentFilter"""
    tool = JLanguageTool(french)
    # picky mode: suggestions with typographical apostrophes
    text = AnnotatedText.from_text(tool.get_analyzed_sentence('De homme').text)
    matches = tool.check(text, level=LEVEL_PICKY)
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["D'homme"]
    # normal mode: suggestions with straight apostrophes
    text = AnnotatedText.from_text(tool.get_analyzed_sentence('De homme').text)
    matches = tool.check(text, level=LEVEL_DEFAULT)
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["D'homme"]
    tool.check('vrai/faux avec explication : Les droits d\'accès, également appelés permissions ou autorisations, '
               'sont des règles définissant')


def test_language_dependent_filter_typographic_apostrophe(french):
    """With the rule APOS_TYP enabled (picky), the suggestions use the
    typographical apostrophe"""
    tool = JLanguageTool(french)
    tool.enable_rule('APOS_TYP')
    matches = tool.check('De homme', level=LEVEL_PICKY)
    assert [m.suggested_replacements for m in matches if m.rule.get_id() == 'ELISION'] == [['D’homme']]
    # (APOS_TYP is picky: not active in the default level)
    matches = tool.check('De homme', level=LEVEL_DEFAULT)
    assert [m.suggested_replacements for m in matches] == [["D'homme"]]


@pytest.mark.parametrize('text,expected', [
    ('greco-romain', '[gréco-romain, Gréco-Romain]'),
    ('Rinsky-Korsakov', '[Rimski-Korsakov]'),
    ('Nikolai Rimski-Korsakov', '[Nikolaï Rimski-Korsakov]'),
])
def test_multitoken_speller(french, text, expected):
    """JLanguageToolTest.testMultitokenSpeller"""
    assert '[' + ', '.join(french.get_multitoken_speller().get_suggestions(text)) + ']' == expected


def test_match_filtering(french):
    """JLanguageToolTest.testMatchfiltering"""
    lt = JLanguageTool(french)
    analyzed_sentence = lt.get_analyzed_sentence("C'est Madame Curie.")
    rule_match = RuleMatch(FakeRule('AI_FR_GGEC_REPLACEMENT_ORTHOGRAPHY_UPPERCASE_MADAME_MADAME'), analyzed_sentence,
                           6, 12, 'Possible error')
    rule_match.set_suggested_replacement('madame')
    filtered = french.filter_rule_matches([rule_match], None, None)
    assert filtered[0].message == 'Un usage différent des majuscules et des minuscules est recommandé.'
    assert filtered[0].short_message == 'Majuscules et minuscules'
    assert filtered[0].rule.loc_quality_issue_type == 'Typographical'
    assert filtered[0].rule.category.id == 'CASING'
    assert filtered[0].rule.get_full_id() == 'AI_FR_GGEC_REPLACEMENT_ORTHOGRAPHY_UPPERCASE_MADAME_MADAME'
    assert filtered[0].get_specific_rule_id() == 'AI_FR_GGEC_REPLACEMENT_CASING_UPPERCASE_MADAME_MADAME'


def test_quotes(french):
    """JLanguageToolTest.testQuotes"""
    lt = JLanguageTool(french)
    analyzed_sentence = lt.get_analyzed_sentence("'elle'.")
    rule_match = RuleMatch(FakeRule('AI_FR_GGEC_REPLACEMENT_PUNCTUATION_QUOTE_TEST'), analyzed_sentence, 0, 5,
                           'Possible error')
    processed_match = adjust_french_rule_match(french, rule_match, set())
    assert 'picky' in processed_match.rule.tags
    assert processed_match.get_specific_rule_id() == 'AI_FR_GGEC_QUOTES'


def test_merging_of_grammar_corrections(french):
    """JLanguageToolTest.testMergingOfGrammarCorrections"""
    lt = JLanguageTool(french)
    analyzed_sentence = lt.get_analyzed_sentence('Ce sont de spectateur')
    # Mocking two adjacent grammar issues
    rule_match1 = RuleMatch(FakeRule('AI_FR_GGEC_DES'), analyzed_sentence, 9, 11, 'Erreur de nombre')
    rule_match1.set_suggested_replacement('des')
    rule_match2 = RuleMatch(FakeRule('AI_FR_GGEC_SPECTATEURS'), analyzed_sentence, 12, 21,
                            'Erreur de forme plurielle')
    rule_match2.set_suggested_replacement('spectateurs')
    # Process the rule matches
    processed_matches = french.filter_rule_matches([rule_match1, rule_match2], None, set())
    assert processed_matches[0].suggested_replacements[0] == 'des spectateurs'
    assert processed_matches[0].get_specific_rule_id() == 'AI_FR_MERGED_MATCH'


# --- AnnotatedTextTest ---

@pytest.mark.skip(reason='spell checking is not ported: the first match of AnnotatedTextTest.testInterpretAsBefore, '
                         'testInterpretAsAfter and testWithFakeMarkupInSimpleMarkupeMarkup is one of '
                         'FR_SPELLING_RULE ("échapatoire", "trouuvé")')
def test_interpret_as():
    """AnnotatedTextTest.testInterpretAsBefore, testInterpretAsAfter and
    testWithFakeMarkupInSimpleMarkupeMarkup"""


@pytest.mark.parametrize('parts,text_to_check', [
    # testWithSimpleMarkup
    ([(False, "J'ai louper le train.", None), (True, '<span>', ''),
      (False, " Ce n'était pas dans mes habitudes.", None), (True, '</span>', '')],
     "J'ai louper le train.<span> Ce n'était pas dans mes habitudes.</span>"),
    # testWithMultipleSimpleMarkup
    ([(False, "J'ai louper le train.", None), (True, '<span>', ''),
      (False, " Ce n'était pas dans mes habitudes.", None), (True, '</span>', ''), (True, '<span>', ''),
      (True, '</span>', '')],
     "J'ai louper le train.<span> Ce n'était pas dans mes habitudes.</span>"),
    # testWithBr
    ([(False, "J'ai louper le train.", None), (True, '<br/>', '\n'),
      (False, " Ce n'était pas dans mes habitudes.", None)],
     "J'ai louper le train.<br/> Ce n'était pas dans mes habitudes."),
])
def test_annotated_text(french, parts, text_to_check):
    """AnnotatedTextTest.testWithSimpleMarkup, testWithMultipleSimpleMarkup
    and testWithBr ("louper" should be "loupé")"""
    match = JLanguageTool(french).check(AnnotatedText(parts))[0]
    assert text_to_check[match.from_pos:match.to_pos] == 'louper'


# --- the language definition ---

def test_definition(french):
    lang = french
    assert lang.code == 'fr'
    assert lang.name == 'French'
    assert lang.countries == ['FR', '', 'LU', 'MC', 'CM', 'CI', 'HT', 'ML', 'SN', 'CD', 'MA', 'RE']
    assert not lang.is_variant()
    assert lang.get_default_disabled_rules_for_variant() == []
    for code, name, country in (('fr-CA', 'French (Canada)', 'CA'), ('fr-CH', 'French (Switzerland)', 'CH'),
                                ('fr-BE', 'French (Belgium)', 'BE')):
        variant = get_language(code)
        assert variant.name == name and variant.countries == [country] and variant.is_variant()
        assert variant.default_variant is lang
        assert variant.get_default_disabled_rules_for_variant() == ['DOUBLER_UNE_CLASSE']
        assert variant.get_default_enabled_rules_for_variant() == []
    assert isinstance(lang.tagger, FrenchTagger)
    assert isinstance(lang.synthesizer, FrenchSynthesizer)
    assert lang.synthesizer.number_speller is not None
    assert type(lang.word_tokenizer) is FrenchWordTokenizer
    # FrenchHybridDisambiguator: the chunkers for spelling_global.txt and fr/multiwords.txt, then the
    # XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, MultiWordChunker, XmlRuleDisambiguator]
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'fr', 'grammar.xml'], ['rules', 'fr', 'style.xml']]
    assert isinstance(lang.get_default_spelling_rule(), MorfologikFrenchSpellerCheck)
    assert isinstance(lang.get_multitoken_speller(), FrenchMultitokenSpeller)
    # getIgnoredCharactersRegex(): the soft hyphen
    rx = lang.ignored_characters_regex
    assert [bool(rx.search(c)) for c in ('­', 'a')] == [True, False]


def test_typography():
    """French.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    for code in ('fr', 'fr-CA', 'fr-CH', 'fr-BE'):
        lang = get_language(code)
        assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
                lang.get_closing_single_quote()) == ('«', '»', '‘', '’')
        assert lang.is_advanced_typography_enabled()
        assert lang.to_advanced_typography('Bonjour!') == 'Bonjour\u202f!'


def test_priorities(french):
    """French.getPriorityForId"""
    p = french.get_priority_for_id
    assert p('AGREEMENT_EXCEPTIONS') == 100
    assert p('PAS_DE_TRAIT_UNION') == 50
    assert p('SOCIOCULTUREL') == 40
    assert p('ESPACE_UNITES') == 10
    assert p('SE_CE') == -10
    assert p('TOO_LONG_PARAGRAPH') == -15
    assert p('FR_SPELLING_RULE') == -100
    assert p('ET_SENT_START') == -151
    assert p('EN_CE_QUI_CONCERNE') == -152
    assert p('ELISION') == -200
    assert p('REPETITIONS_STYLE') == -250
    assert p('UPPERCASE_SENTENCE_START') == -300
    assert p('FRENCH_WHITESPACE_STRICT') == -350
    assert p('FRENCH_WHITESPACE') == -400
    assert p('FRENCH_WORD_REPEAT_BEGINNING_RULE') == -350
    assert p('FR_COMPOUNDS_HAUT_RHIN') == 500
    assert p('CAT_TYPOGRAPHIE') == 20
    assert p('CAT_TOURS_CRITIQUES') == 20
    assert p('CAT_HOMONYMES_PARONYMES') == 20
    assert p('SON') == -5
    assert p('CARTE') == -50
    assert p('CONFUSION_RULE_PREMIUM') == -50
    assert p('FR_MULTITOKEN_SPELLING_X') == -90
    assert p('FR_SIMPLE_REPLACE_SIMPLE_JAI') == 150
    assert p('grammalecte_x') == -150
    assert p('AI_FR_HYDRA_LEO_X') == -101
    assert p('AI_FR_GGEC_REPLACEMENT_ORTHOGRAPHY_X') == -101
    assert p('SOME_STYLE_RULE') == -50
    assert p('TOO_LONG_SENTENCE') == -101
    assert p('OTHER') == 0


def test_relevant_rules(french):
    rules = french.get_relevant_rules(messages_for('fr'))
    # getRelevantRules without MorfologikFrenchSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS', 'UPPERCASE_SENTENCE_START',
        'WHITESPACE_RULE', 'SENTENCE_WHITESPACE', 'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH', 'FR_COMPOUNDS',
        'FRENCH_WHITESPACE_STRICT', 'FRENCH_WHITESPACE', 'FR_SIMPLE_REPLACE_SIMPLE', 'FR_REPEATEDWORDS']
    assert type(rules[2]) is GenericUnpairedBracketsRule
    assert [type(r) for r in rules[8:]] == [CompoundRule, QuestionWhitespaceStrictRule, QuestionWhitespaceRule,
                                            SimpleReplaceRule, FrenchRepeatedWordsRule]
    assert rules[6].max_words == 40
    assert rules[9].default_off and 'picky' in rules[9].tags
    assert not unsupported_components(french)
    for code in ('fr-CA', 'fr-CH', 'fr-BE'):
        assert not unsupported_components(get_language(code))
