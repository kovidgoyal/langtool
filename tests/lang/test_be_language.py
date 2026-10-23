"""Port of org.languagetool.rules.be.BelarusianTest (LanguageSpecificTest),
org.languagetool.rules.be.SimpleReplaceRuleTest,
org.languagetool.rules.be.BelarusianSpecificCaseRuleTest,
org.languagetool.tokenizers.be.BelarusianWordTokenizerTest,
org.languagetool.rules.be.BelarusianMorfologikRuleTest and
org.languagetool.rules.be.LanguageSpecificSpellcheckerTest, plus checks of
the Belarusian language definition against
org.languagetool.language.Belarusian. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py
(which includes be)."""

import pytest

from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.be.rules import BelarusianSpecificCaseRule, SimpleReplaceRule
from langtool.lang.be.tokenizers import BelarusianWordTokenizer
from langtool.messages import messages_for
from langtool.tagging import DemoTagger
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool


# --- BelarusianTest ---

def test_demo_text():
    """BelarusianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Паспрабуйце напісаць нейкі тэкст з памылкамі, а LanguageTool паспрабуе паказаць нейкия найбольш '
         'распаусюджаныя памылки.')
    matches = JLanguageTool(get_language('be')).check(s)
    assert [m.get_specific_rule_id() for m in matches] == ['I', 'U_KAROTKAJE', 'I']


@pytest.mark.skip(reason='spell checking is not ported: BelarusianMorfologikRuleTest tests '
                         'MorfologikBelarusianSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.rules.be.BelarusianMorfologikRuleTest"""


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.be.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('be')
    assert lang.code == 'be-BY'
    assert get_language('be-BY') is lang
    assert lang.name == 'Belarusian'
    assert lang.countries == ['BY']
    assert isinstance(lang.tagger, DemoTagger)
    assert lang.synthesizer is None
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, BelarusianWordTokenizer)
    assert lang.definition['ignored_characters_regex'] == '[­́̀]'
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['be', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('be')
    rules = lang.get_relevant_rules(messages_for('be'))
    # getRelevantRules without MorfologikBelarusianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE',
        'SENTENCE_WHITESPACE', 'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN', 'TOO_LONG_SENTENCE',
        'TOO_LONG_PARAGRAPH', 'PARAGRAPH_REPEAT_BEGINNING_RULE', 'PUNCTUATION_PARAGRAPH_END2', 'BE_SIMPLE_REPLACE',
        'BE_SPECIFIC_CASE']
    assert rules[7].max_words == 50
    assert isinstance(rules[-2], SimpleReplaceRule)
    assert isinstance(rules[-1], BelarusianSpecificCaseRule)
    assert not unsupported_components(lang)


def test_priorities():
    """Belarusian.getPriorityForId (the ids RUSSIAN_SIMPLE_REPLACE_RULE and
    BELARUSIAN_SPECIFIC_CASE do not match the ids of the Belarusian rules,
    as in Java)"""
    lang = get_language('be')
    assert lang.get_priority_for_id('RUSSIAN_SIMPLE_REPLACE_RULE') == 10
    assert lang.get_priority_for_id('BELARUSIAN_SPECIFIC_CASE') == 9
    assert lang.get_priority_for_id('Word_root_repeat') == -1
    assert lang.get_priority_for_id('PUNCT_DPT_2') == -2
    assert lang.get_priority_for_id('TOO_LONG_PARAGRAPH') == -15
    assert lang.get_priority_for_id('BE_SIMPLE_REPLACE') == 0
    assert lang.get_priority_for_id('BE_SPECIFIC_CASE') == 0


# --- SimpleReplaceRuleTest ---

def test_simple_replace_rule():
    """SimpleReplaceRuleTest.testRule"""
    lang = get_language('be')
    rule = SimpleReplaceRule(messages_for('be'), lang)
    lt = JLanguageTool(lang)

    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Напрамкі дзейнасці былі ўзгоднены з ,'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Яго камп’ютар выключыўся.'))) == 0

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence('Яго кампутар выключыўся.'))
    assert len(matches) == 1
    assert len(matches[0].suggested_replacements) == 1
    assert matches[0].suggested_replacements[0] == 'камп’ютар'


def test_simple_replace_rule_properties():
    lang = get_language('be')
    rule = SimpleReplaceRule(messages_for('be'), lang)
    assert rule.get_id() == 'BE_SIMPLE_REPLACE'
    assert rule.get_description() == 'Пошук прастамоўяў і памылковых фраз'
    assert (rule.category.id, rule.category.name) == ('MISC', 'Агульныя правілы')
    assert rule.loc_quality_issue_type == 'Misspelling'
    assert [(e.example, e.corrections) for e in rule.incorrect_examples] == [
        ('<marker>З большага</marker>, гэта быў добры дзень.', ['Збольшага'])]
    m, = rule.match(JLanguageTool(lang).get_analyzed_sentence('Яго кампутар выключыўся.'))
    assert m.message == ('«кампутар» — памылка, нелітаратурны выраз або прастамоўе, правільна: '
                         '<suggestion>камп’ютар</suggestion>')
    assert m.short_message == 'Памылка?'
    assert (m.from_pos, m.to_pos) == (4, 12)


# --- BelarusianSpecificCaseRuleTest ---

def test_specific_case_rule():
    """BelarusianSpecificCaseRuleTest.testRule"""
    lt = JLanguageTool(get_language('be'))
    rule = BelarusianSpecificCaseRule(messages_for('en'))

    def assert_good(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 0

    def assert_bad(text):
        matches = rule.match(lt.get_analyzed_sentence(text))
        assert len(matches) == 1
        return matches

    assert_good('Беларуская Народная Рэспубліка')
    assert_good('Папа Рымскі')
    assert_bad('дзяржаўны сцяг Рэспублікі Беларусь')
    assert_bad('вярхоўны суд рэспублікі беларусь')

    matches1 = assert_bad('Мне падабаецца air France.')
    assert matches1[0].from_pos == 15
    assert matches1[0].to_pos == 25
    assert matches1[0].suggested_replacements == ['Air France']
    assert matches1[0].message == 'Уласныя імёны і назвы пішуцца з вялікай літары.'


def test_specific_case_rule_properties():
    rule = BelarusianSpecificCaseRule(messages_for('be'))
    assert rule.get_id() == 'BE_SPECIFIC_CASE'
    assert rule.get_description() == 'Напісанне спецыяльных найменняў у верхнім або ніжнім рэгістры'
    assert rule.category.id == 'CASING'
    assert rule.loc_quality_issue_type == 'Misspelling'
    assert [(e.example, e.corrections) for e in rule.incorrect_examples] == [
        ('<marker>Вялікая айчынная Вайна</marker> — гэта спецыфічны тэрмін савецкай гістарыяграфіі.',
         ['Вялікая Айчынная вайна'])]
    m, = rule.match(JLanguageTool(get_language('be')).get_analyzed_sentence('дзяржаўны сцяг Рэспублікі Беларусь'))
    assert m.message == 'Калі гэта уласнае імя або назва, выкарыстоўвайце прапанаванае напісанне.'
    assert m.short_message == 'Proper noun'


# --- BelarusianWordTokenizerTest ---

def test_word_tokenizer():
    """BelarusianWordTokenizerTest.testTokenize"""
    word_tokenizer = BelarusianWordTokenizer()
    tokens = word_tokenizer.tokenize("камп'ютар")
    assert len(tokens) == 1
    assert tokens == ["камп'ютар"]
    tokens2 = word_tokenizer.tokenize('Яно\rразбіваецца')
    assert len(tokens2) == 3
    assert tokens2 == ['Яно', '\r', 'разбіваецца']
    tokens3 = word_tokenizer.tokenize('Мой адрас — address@email.com')
    assert len(tokens3) == 7
    assert tokens3 == ['Мой', ' ', 'адрас', ' ', '—', ' ', 'address@email.com']


def test_word_tokenizer_apostrophes():
    """BelarusianWordTokenizer: ', ’ and ʼ are not tokenizing characters, ’
    is replaced by ' in tokens longer than one character"""
    word_tokenizer = BelarusianWordTokenizer()
    expected = WordTokenizer().get_tokenizing_characters().replace("'", '').replace('’', '').replace('ʼ', '')
    assert word_tokenizer.get_tokenizing_characters() == expected
    assert word_tokenizer.tokenize('Яго камп’ютар і зʼезд.') == [
        'Яго', ' ', "камп'ютар", ' ', 'і', ' ', 'зʼезд', '.']
    assert word_tokenizer.tokenize('’ а’') == ['’', ' ', "а'"]
