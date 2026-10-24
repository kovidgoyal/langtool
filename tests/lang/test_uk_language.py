"""Port of org.languagetool.rules.uk.UkrainianTest (LanguageSpecificTest),
LanguageSpecificSpellcheckerTest and MorfologikUkrainianSpellerRuleTest
(both skipped, spell checking), plus checks of the Ukrainian language
definition against org.languagetool.language.Ukrainian and of the
misspelling check and the suggestions of MorfologikUkrainianSpellerRule.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.uk.agreement_numr_noun import TokenAgreementNumrNounRule
from langtool.lang.uk.replace_rules import SimpleReplaceRenamedRule, SimpleReplaceRule, SimpleReplaceSoftRule
from langtool.lang.uk.rules import (HiddenCharacterRule, MissingHyphenRule, MixedAlphabetsRule, TypographyRule,
                                    UkrainianCommaWhitespaceRule, UkrainianUppercaseSentenceStartRule,
                                    UkrainianWordRepeatRule)
from langtool.lang.uk.spelling import MorfologikUkrainianSpellerCheck
from langtool.lang.uk.synthesis import UkrainianSynthesizer
from langtool.lang.uk.tokenizers import UkrainianWordTokenizer
from langtool.messages import messages_for
from langtool.rules.core import MultipleWhitespaceRule
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('uk')


def test_demo_text():
    """UkrainianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('УВАГА! Внизу наведено приклад тексту з помилками, які допоможе виправити LanguageTool. '
         'Будь-ласка, вставте тутт ваш текст, або перевірте цей текст на предмет помилок. '
         'Знайти всі помилки для LanguageTool є не по силах з багатьох причин але дещо він вам все таки підкаже. '
         'Порівняно з засобами перевірки орфографії LanguageTool також змайде граматичні та стильові проблеми. '
         'LanguageTool — ваш самий кращий помічник.')
    matches = JLanguageTool(get_language('uk')).check(s)
    # Java expects two matches of MORFOLOGIK_RULE_UK_UA (for "тутт" and "змайде"), the spell checker, which
    # is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'UK_SIMPLE_REPLACE', 'PO_VS_OTHER', 'comma_before_but', 'WORDS_WITH_DASH', 'SAMYI_WITH_ADJ']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists with MorfologikUkrainianSpellerRule')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.uk.LanguageSpecificSpellcheckerTest"""


@pytest.mark.skip(reason='spell checking is not ported: MorfologikUkrainianSpellerRuleTest tests the rule matches '
                         'and suggestions of MorfologikUkrainianSpellerRule (its misspelling check is tested in '
                         'test_misspelling_check)')
def test_morfologik_speller():
    """Port of MorfologikUkrainianSpellerRuleTest (testMorfologikSpeller, testSuggestionOrder,
    testCompounds, testDashedSuggestions, testProhibitedSuggestions)"""


def test_misspelling_check():
    """MorfologikUkrainianSpellerRule.isMisspelled (the default spelling rule)"""
    check = get_language('uk').get_default_spelling_rule()
    assert isinstance(check, MorfologikUkrainianSpellerCheck)
    assert not check.is_misspelled('прийдешній')
    assert check.is_misspelled('прийдешнiй')  # latin 'i'
    assert not check.is_misspelled('заввідділу')
    # words ending with a hyphen are misspelled unless they also start with one
    assert check.is_misspelled('радіо-')
    assert not check.is_misspelled('-ськ-')
    # the suggestions of speller1 (used by SimpleReplaceRule)
    assert 'прийдешній' in check.speller1_suggestions_from_default_dicts('прийдешнiй')


def test_definition():
    lang = get_language('uk')
    assert lang.code == 'uk-UA'
    assert get_language('uk-UA') is lang
    assert lang.name == 'Ukrainian'
    assert lang.countries == ['UA']
    assert type(lang.tagger).__name__ == 'UkrainianTagger'
    synth = lang.synthesizer
    assert type(synth) is UkrainianSynthesizer
    assert synth.tags_path.replace('\\', '/').endswith('uk/ukrainian_tags.txt')
    assert type(lang.word_tokenizer) is UkrainianWordTokenizer
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    names = ('grammar.xml', 'grammar-spelling.xml', 'grammar-grammar.xml', 'grammar-barbarism.xml',
             'grammar-style.xml', 'grammar-punctuation.xml')
    assert files == [['rules', 'uk', f] for f in names]
    # getIgnoredCharactersRegex(): soft hyphen and the combining acute accent
    rx = lang.ignored_characters_regex
    assert [bool(rx.search(c)) for c in ('\u00AD', '\u0301', '\u0300', 'а')] == [True, True, False, False]


def test_typography():
    """Ukrainian.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    lang = get_language('uk')
    assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
            lang.get_closing_single_quote()) == ('«', '»', '‘', '’')
    assert not lang.is_advanced_typography_enabled()


def test_relevant_rules():
    lang = get_language('uk')
    rules = lang.get_relevant_rules(messages_for('uk'))
    # getRelevantRules without MorfologikUkrainianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE', 'UKRAINIAN_WORD_REPEAT_RULE',
        'DASH', 'UK_HIDDEN_CHARS', 'UK_MISSING_HYPHEN', 'UK_VERB_NOUN_INFLECTION_AGREEMENT',
        'UK_NOUN_VERB_INFLECTION_AGREEMENT', 'UK_ADJ_NOUN_INFLECTION_AGREEMENT', 'UK_PREP_NOUN_INFLECTION_AGREEMENT',
        'UK_NUMR_NOUN_INFLECTION_AGREEMENT', 'UK_MIXED_ALPHABETS', 'UK_SIMPLE_REPLACE_SOFT',
        'UK_SIMPLE_REPLACE_RENAMED', 'UK_SIMPLE_REPLACE']
    assert [type(r) for r in rules[:7]] == [
        UkrainianCommaWhitespaceRule, UkrainianUppercaseSentenceStartRule, MultipleWhitespaceRule,
        UkrainianWordRepeatRule, TypographyRule, HiddenCharacterRule, MissingHyphenRule]
    assert [type(r) for r in rules[11:]] == [
        TokenAgreementNumrNounRule, MixedAlphabetsRule, SimpleReplaceSoftRule, SimpleReplaceRenamedRule,
        SimpleReplaceRule]
    assert [r.get_id() for r in rules if r.default_off] == []
    # the example pairs of the UkrainianCommaWhitespaceRule and UkrainianUppercaseSentenceStartRule constructors
    assert rules[0].incorrect_examples[0].example == \
        'Ми обідали борщем<marker> ,</marker> пловом і салатом,— все смачне.'
    assert rules[1].correct_examples[0].example == '<marker>Речення</marker> має починатися з великої'
    assert not unsupported_components(lang)


def test_date_check_filter_message():
    """DateCheckFilter: the day name of the date (Calendar.getDisplayName for the locale "uk")"""
    matches = JLanguageTool(get_language('uk')).check('Конференція відбудеться в понеділок, 10 жовтня 2014 р.')
    assert [m.message for m in matches if m.get_specific_rule_id() == 'DATE_WEEKDAY1'] == [
        'Днем тижня 10 жовтня 2014 є не понеділок, а пʼятниця.']
