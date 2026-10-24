"""Port of org.languagetool.rules.ru.RussianTest (LanguageSpecificTest),
org.languagetool.tokenizers.ru.RussianSRXSentenceTokenizerTest,
org.languagetool.rules.ru.DateCheckFilterTest,
LanguageSpecificSpellcheckerTest, MorfologikRussianSpellerRuleTest and
MorfologikRussianYOSpellerRuleTest (all three skipped, spell checking),
plus checks of the Russian language definition against
org.languagetool.language.Russian, of the misspelling check of
MorfologikRussianSpellerRule and of the Russian filters. The language
independent parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ru.chunking import RussianChunker
from langtool.lang.ru.filters import (DateCheckFilter, DateFilterHelper, FutureDateFilter, INNNumberFilter,
                                      NoDisambiguationRussianPartialPosTagFilter, RussianPartialPosTagFilter)
from langtool.lang.ru.rules import (RussianCompoundRule, RussianDashRule, RussianFillerWordsRule,
                                    RussianSimpleReplaceRule, RussianSimpleWordRepeatRule, RussianSpecificCaseRule,
                                    RussianUnpairedBracketsRule, RussianVerbConjugationRule,
                                    RussianWordCoherencyRule, RussianWordRepeatRule, RussianWordRootRepeatRule)
from langtool.lang.ru.spelling import MorfologikRussianSpellerCheck
from langtool.lang.ru.tagging import RussianTagger
from langtool.lang.ru.tokenizers import RussianWordTokenizer
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.core_filters import FRIDAY, MONDAY, SUNDAY, TUESDAY, CalendarDate
from langtool.synthesis import BaseSynthesizer
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ru')


# --- RussianTest ---

def test_demo_text():
    """RussianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Вставьте ваш текст сюда .. или проверьте этот текстт. Релиз LanguageTool 4.7 состоялся в четверг '
         '28 сентября 2019 года.')
    matches = JLanguageTool(get_language('ru')).check(s)
    # Java expects a match of MORFOLOGIK_RULE_RU_RU (for "текстт") after UPPERCASE_SENTENCE_START, the
    # spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'DOUBLE_PUNCTUATION', 'UPPERCASE_SENTENCE_START', 'DATE_WEEKDAY1']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists with MorfologikRussianSpellerRule')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.ru.LanguageSpecificSpellcheckerTest"""


@pytest.mark.skip(reason='spell checking is not ported: MorfologikRussianSpellerRuleTest tests the rule '
                         'MorfologikRussianSpellerRule (its misspelling check is tested in '
                         'test_misspelling_check)')
def test_morfologik_speller():
    """Port of MorfologikRussianSpellerRuleTest.testMorfologikSpeller"""


@pytest.mark.skip(reason='spell checking is not ported: MorfologikRussianYOSpellerRuleTest tests the rule '
                         'MorfologikRussianYOSpellerRule')
def test_morfologik_yo_speller():
    """Port of MorfologikRussianYOSpellerRuleTest.testMorfologikSpeller"""


def test_definition():
    lang = get_language('ru')
    assert lang.code == 'ru-RU'
    assert get_language('ru-RU') is lang
    assert lang.name == 'Russian'
    assert lang.countries == ['RU']
    assert isinstance(lang.tagger, RussianTagger)
    synth = lang.synthesizer
    assert type(synth) is BaseSynthesizer
    assert synth.tags_path.replace('\\', '/').endswith('ru/tags_russian.txt')
    assert type(lang.word_tokenizer) is RussianWordTokenizer
    # RussianHybridDisambiguator: the MultiWordChunker for ru/multiwords.txt, then the XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, XmlRuleDisambiguator]
    # createDefaultPostDisambiguationChunker(), no (pre-disambiguation) chunker
    assert isinstance(lang.post_disambiguation_chunker, RussianChunker)
    assert lang.chunker is None
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'ru', 'grammar.xml']]
    # getIgnoredCharactersRegex(): soft hyphen and the combining acute and grave accents
    rx = lang.ignored_characters_regex
    assert [bool(rx.search(c)) for c in ('­', '́', '̀', 'а')] == [True, True, True, False]


def test_typography():
    """Russian.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    lang = get_language('ru')
    assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
            lang.get_closing_single_quote()) == ('«', '»', '‘', '’')
    assert lang.is_advanced_typography_enabled()


def test_priorities():
    """Russian.getPriorityForId"""
    p = get_language('ru').get_priority_for_id
    assert p('RU_DASH_RULE') == 12
    assert p('RU_COMPOUNDS') == 11
    assert p('RUSSIAN_SIMPLE_REPLACE_RULE') == 10
    assert p('RUSSIAN_SPECIFIC_CASE') == 9
    assert p('MORFOLOGIC_RULE_RU_RU_YO') == 2
    assert p('MORFOLOGIC_RULE_RU_RU') == 1
    assert p('Word_root_repeat') == -1
    assert p('PUNCT_DPT_2') == -2
    assert p('TOO_LONG_PARAGRAPH') == -15
    assert p('TOO_LONG_SENTENCE') == -101
    assert p('SOME_STYLE_RULE') == -50
    assert p('RU_SIMPLE_REPLACE') == 0


def test_relevant_rules():
    lang = get_language('ru')
    rules = lang.get_relevant_rules(messages_for('ru'))
    # getRelevantRules without MorfologikRussianSpellerRule and MorfologikRussianYOSpellerRule (spell
    # checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE', 'SENTENCE_WHITESPACE',
        'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN', 'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH',
        'PARAGRAPH_REPEAT_BEGINNING_RULE', 'FILLER_WORDS_RU', 'PUNCTUATION_PARAGRAPH_END2', 'RU_UNPAIRED_BRACKETS',
        'RU_COMPOUNDS', 'RU_SIMPLE_REPLACE', 'WORD_REPEAT_RULE', 'RU_WORD_COHERENCY', 'RU_WORD_REPEAT',
        'RU_WORD_ROOT_REPEAT', 'RU_VERB_CONJUGATION', 'RU_DASH_RULE', 'RU_SPECIFIC_CASE']
    assert [type(r) for r in rules[9:10]] == [RussianFillerWordsRule]
    assert [type(r) for r in rules[11:]] == [
        RussianUnpairedBracketsRule, RussianCompoundRule, RussianSimpleReplaceRule, RussianSimpleWordRepeatRule,
        RussianWordCoherencyRule, RussianWordRepeatRule, RussianWordRootRepeatRule, RussianVerbConjugationRule,
        RussianDashRule, RussianSpecificCaseRule]
    assert rules[6].max_words == 50
    assert [r.get_id() for r in rules if r.default_off] == [
        'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN', 'TOO_LONG_PARAGRAPH', 'PARAGRAPH_REPEAT_BEGINNING_RULE',
        'FILLER_WORDS_RU', 'PUNCTUATION_PARAGRAPH_END2', 'RU_WORD_REPEAT', 'RU_WORD_ROOT_REPEAT']
    # the example pairs of the CommaWhitespaceRule and UppercaseSentenceStartRule constructors
    assert rules[0].incorrect_examples[0].example == 'Не род<marker> ,</marker> а ум поставлю в воеводы.'
    assert rules[1].correct_examples[0].example == \
        'Закончилось лето. <marker>Дети</marker> снова сели за школьные парты.'
    # RussianDashRule has no tags (setTags(Collections.emptyList()))
    assert rules[19].tags == []
    assert not unsupported_components(lang)


def test_concurrency_sample():
    """RussianConcurrencyTest.createSampleText can be checked"""
    assert JLanguageTool(get_language('ru')).check('Материал из Википедии — свободной энциклопедии') is not None


# --- RussianSRXSentenceTokenizerTest ---

def test_sentence_tokenize():
    """RussianSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('ru'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    # NOTE: sentences here need to end with a space character so they
    # have correct whitespace when appended:
    # From the Russian abbreviation list:
    test_split('Отток капитала из России составил 7 млрд. долларов, сообщил министр финансов Алексей Кудрин.')
    test_split('Журнал издаётся с 1967 г., пользуется большой популярностью в мире.')
    test_split('С 2007 г. периодичность выхода газеты – 120 раз в год.')
    test_split('Редакция журнала находится в здании по адресу: г. Москва, 110000, улица Мира, д. 1.')
    test_split('Все эти вопросы заставляют нас искать ответы в нашей истории 60-80-х гг. прошлого столетия.')
    test_split('Более 300 тыс. документов и справочников.')
    test_split('Скидки до 50000 руб. на автомобили.')
    test_split('Изготовление визиток любыми тиражами (от 20 шт. до 10 тысяч) в минимальные сроки (от 20 минут).')
    test_split('Временно не работает, т.к. не поддерживается.')


# --- the misspelling check of MorfologikRussianSpellerRule ---

def test_misspelling_check():
    """isMisspelled of MorfologikRussianSpellerRule (the default spelling
    rule of Russian), with the words of MorfologikRussianSpellerRuleTest"""
    check = get_language('ru').get_default_spelling_rule()
    assert isinstance(check, MorfologikRussianSpellerCheck)
    for word in ('русский', 'ёжик', 'ежик', 'северо-восточный', 'Ростов-на-Дону', 'каждая'):
        assert not check.is_misspelled(word), word
    for word in ('юго-зпдный', 'Ростов-на-дону', 'каждя'):
        assert check.is_misspelled(word), word


# --- DateCheckFilterTest ---

def test_date_check_filter_day_of_week():
    """DateCheckFilterTest.testGetDayOfWeek"""
    f = DateCheckFilter()
    assert f.get_day_of_week('пн') == 2
    assert f.get_day_of_week('пн.') == 2
    assert f.get_day_of_week('вт') == 3
    assert f.get_day_of_week('пт') == 6
    # (commented out in Java)
    assert f.get_day_of_week('вс') == 1
    assert f.get_day_of_week('понедельник') == 2
    assert f.get_day_of_week('Понедельник') == 2
    assert f.get_day_of_week('Пн') == 2
    assert f.get_day_of_week('пятница') == 6
    with pytest.raises(RuntimeError):
        f.get_day_of_week('xx')
    assert f.get_day_of_week_name(CalendarDate.of(2014, 0, 1)) == 'среда'


def test_date_check_filter_month():
    """DateCheckFilterTest.testMonth"""
    f = DateCheckFilter()
    assert f.get_month('I') == 1
    assert f.get_month('XII') == 12
    assert f.get_month('декабрь') == 12
    assert f.get_month('Декабрь') == 12
    assert f.get_month('ДЕКАБРЬ') == 12
    assert f.get_month('мая') == 5
    assert f.get_month('ин') == 6
    with pytest.raises(RuntimeError):
        f.get_month('i')


def test_date_filter_helper():
    """DateFilterHelper (prefixes, special characters are removed)"""
    assert DateFilterHelper.get_day_of_week('Суббота') == 7
    assert DateFilterHelper.get_day_of_week('вос­кресенье') == SUNDAY
    assert DateFilterHelper.get_day_of_week('понедельник') == MONDAY
    assert DateFilterHelper.get_day_of_week('вторник') == TUESDAY
    assert DateFilterHelper.get_day_of_week('пятница') == FRIDAY
    assert DateFilterHelper.get_month('мая') == 5
    assert DateFilterHelper.get_month('Сентябрь') == 9
    with pytest.raises(RuntimeError):
        DateFilterHelper.get_month('xyz')


class _FakeRule(Rule):
    def get_id(self):
        return 'FAKE'

    def get_description(self):
        return 'fake'


def _match():
    return RuleMatch(_FakeRule(), None, 0, 1, 'msg')


def test_future_date_filter():
    """FutureDateFilter (in unit tests the current date is 2014-01-01)"""
    f = FutureDateFilter()
    m = _match()
    assert f.accept_rule_match(m, {'year': '2015', 'month': 'мая', 'day': '3'}, 0, [], []) is m
    assert f.accept_rule_match(m, {'year': '2013', 'month': 'декабря', 'day': '31'}, 0, [], []) is None
    assert f.accept_rule_match(m, {'year': '2014', 'month': '2', 'day': '1'}, 0, [], []) is m
    # invalid dates are normalized like in Java (Calendar.after compares a lenient clone): 30.02.2015 is
    # 02.03.2015, in the future
    assert f.accept_rule_match(m, {'year': '2015', 'month': 'февраля', 'day': '30'}, 0, [], []) is m


def test_inn_number_filter():
    """INNNumberFilter: wrong check digits of 10 and 12 digit INNs"""
    f = INNNumberFilter()
    m = _match()
    assert f.accept_rule_match(m, {'inn': '7707083893'}, 0, [], []) is None
    assert f.accept_rule_match(m, {'inn': '7707083894'}, 0, [], []) is m
    assert f.accept_rule_match(m, {'inn': '500100732259'}, 0, [], []) is None
    assert f.accept_rule_match(m, {'inn': '500100732258'}, 0, [], []) is m
    # other lengths and non-digits are not checked
    assert f.accept_rule_match(m, {'inn': '12345'}, 0, [], []) is None
    assert f.accept_rule_match(m, {'inn': '7676gj8778'}, 0, [], []) is None


def test_partial_pos_tag_filters():
    """RussianPartialPosTagFilter (tags and disambiguates the token) and
    NoDisambiguationRussianPartialPosTagFilter (only tags it)"""
    ru = get_language('ru')
    for cls in (RussianPartialPosTagFilter, NoDisambiguationRussianPartialPosTagFilter):
        tags = cls(ru).tag('дом')
        assert len(tags) == 1 and isinstance(tags[0], AnalyzedTokenReadings)
        assert 'NN:Inanim:Masc:Sin:Nom' in [r.pos_tag for r in tags[0].readings]
    token = AnalyzedTokenReadings(AnalyzedToken('недом', None, None), 0)
    args = {'no': '1', 'regexp': 'не(.*)', 'postag_regexp': 'NN:.*'}
    m = _match()
    assert RussianPartialPosTagFilter(ru).accept_rule_match(m, args, 0, [token], [1]) is m
    args['postag_regexp'] = 'VB:.*'
    assert NoDisambiguationRussianPartialPosTagFilter(ru).accept_rule_match(m, args, 0, [token], [1]) is None
