"""Port of the rule tests of language-ru: org.languagetool.rules.ru.RussianCompoundRuleTest,
RussianDashRuleTest, RussianSimpleReplaceRuleTest, RussianSpecificCaseRuleTest,
RussianUnpairedBracketsRuleTest, RussianVerbConjugationRuleTest,
RussianWordCoherencyRuleTest and RussianWordRepeatRuleTest, plus checks of
the other Russian rules (RussianSimpleWordRepeatRule, RussianFillerWordsRule,
RussianWordRootRepeatRule)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.ru.rules import (RussianCompoundRule, RussianDashRule, RussianFillerWordsRule,
                                    RussianSimpleReplaceRule, RussianSimpleWordRepeatRule, RussianSpecificCaseRule,
                                    RussianUnpairedBracketsRule, RussianVerbConjugationRule,
                                    RussianWordCoherencyRule, RussianWordRepeatRule, RussianWordRootRepeatRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ru')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('ru'))


def _check(lt, rule, expected_errors, text, exp_suggestions=None):
    # AbstractCompoundRuleTest.check and RussianDashRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions is not None:
        assert matches[0].suggested_replacements == exp_suggestions


# --- RussianCompoundRuleTest ---

def test_compound_rule(lt):
    """RussianCompoundRuleTest.testRule"""
    rule = RussianCompoundRule(messages_for('en'), get_language('ru'), None)
    # correct sentences:
    _check(lt, rule, 0, 'Он вышел из-за дома.')
    _check(lt, rule, 0, 'Разработка ПО за идею.')
    # Both  suggestion for some words:
    _check(lt, rule, 0, 'естественно-научный')
    # incorrect sentences:
    _check(lt, rule, 1, 'из за', ['из-за'])
    _check(lt, rule, 1, 'по за', ['по-за'])
    _check(lt, rule, 1, 'нет нет из за да да')
    # FIXME: suggestions / longest match
    _check(lt, rule, 1, 'Ростов на Дону', ['Ростов-на-Дону'])
    _check(lt, rule, 1, 'Ростов на Дону — крупнейший город на юге Российской Федерации, административный центр '
                        'Южного федерального округа и Ростовской области.')
    # no hyphen suggestion for some words:
    _check(lt, rule, 1, 'кругло суточный', ['круглосуточный'])
    # also must not accept incorrect upper/lowercase spelling:
    _check(lt, rule, 0, 'Ростов на дону')
    _check(lt, rule, 0, 'Ведь сейчас в лос Анджелесе')
    # also detect an error if only some of the hyphens are missing:
    _check(lt, rule, 1, 'Ростов-на Дону', ['Ростов-на-Дону'])
    # first part is a single character:
    _check(lt, rule, 0, 'во-первых')
    _check(lt, rule, 1, 'во первых', ['во-первых'])
    _check(lt, rule, 1, 'Лос Анджелес', ['Лос-Анджелес'])
    _check(lt, rule, 1, 'Ведь сейчас в Лос Анджелесе')
    _check(lt, rule, 1, 'Ведь сейчас в Лос Анджелесе хорошая погода.')
    _check(lt, rule, 1, 'Во первых, мы были довольно высоко над уровнем моря.')
    _check(lt, rule, 1, 'Мы, во первых, были довольно высоко над уровнем моря.')


def test_compound_rule_properties():
    rule = RussianCompoundRule(messages_for('ru'), get_language('ru'))
    assert rule.get_id() == 'RU_COMPOUNDS'
    assert rule.get_description() == 'Правописание через дефис'
    assert rule.sentence_starts_with_upper_case
    assert rule.incorrect_examples[0].example == 'Собрание состоится в <marker>конференц зале</marker>.'


# --- RussianDashRuleTest ---

def test_dash_rule(lt):
    """RussianDashRuleTest.testRule"""
    rule = RussianDashRule(messages_for('ru'), get_language('ru'))
    # correct sentences:
    _check(lt, rule, 0, 'Он вышел из-за забора.')
    _check(lt, rule, 0, 'Ростов-на-Дону.')
    _check(lt, rule, 0, 'ведром — работай')
    # incorrect sentences:
    _check(lt, rule, 1, 'из—за', ['из-за'])
    _check(lt, rule, 1, 'Ростов — на — Дону', ['Ростов-на-Дону'])


def test_dash_rule_properties():
    rule = RussianDashRule(messages_for('ru'), get_language('ru'))
    assert rule.get_id() == 'RU_DASH_RULE'
    assert rule.get_message() == 'Использовано тире вместо дефиса.'
    assert rule.tags == []
    assert rule.is_boundary(' ') and rule.is_boundary('a') and not rule.is_boundary('я')


# --- RussianSimpleReplaceRuleTest ---

def test_simple_replace_rule(lt):
    """RussianSimpleReplaceRuleTest.testRule"""
    rule = RussianSimpleReplaceRule(messages_for('ru'), get_language('ru'))
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Рост кораллов тут самый быстрый,'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Книга была порвана.'))) == 0
    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence('Книга была порвата.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['порвана']
    assert rule.get_id() == 'RU_SIMPLE_REPLACE'
    assert rule.category.name == 'Общие правила'
    assert rule.loc_quality_issue_type == 'Misspelling'


# --- RussianSpecificCaseRuleTest ---

def test_specific_case_rule(lt):
    """RussianSpecificCaseRuleTest.testRule"""
    rule = RussianSpecificCaseRule(messages_for('en'))

    def assert_good(text):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == 0

    def assert_bad(text):
        matches = rule.match(lt.get_analyzed_sentence(text))
        assert len(matches) == 1
        return matches

    assert_good('Рытый Банк')
    assert_good('Центральный банк РФ')
    assert_bad('Рытый банк')
    assert_bad('центральный банк РФ')
    matches1 = assert_bad('I like air France.')
    assert matches1[0].from_pos == 7
    assert matches1[0].to_pos == 17
    assert matches1[0].suggested_replacements == ['Air France']
    assert matches1[0].message == 'Для специальных наименований используйте начальную заглавную букву.'


def test_specific_case_rule_messages(lt):
    rule = RussianSpecificCaseRule(messages_for('ru'), get_language('ru'))
    matches = rule.match(lt.get_analyzed_sentence('Это центральный банк РФ.'))
    assert matches[0].suggested_replacements == ['Центральный банк РФ']
    assert matches[0].message == \
        'Для специальных наименований используйте предложенное написание заглавных и строчных букв.'
    # all uppercase phrases are accepted
    assert rule.match(lt.get_analyzed_sentence('РЫТЫЙ БАНК')) == []


# --- RussianUnpairedBracketsRuleTest ---

def test_unpaired_brackets_rule(lt):
    """RussianUnpairedBracketsRuleTest.testRuleRussian"""
    rule = RussianUnpairedBracketsRule(messages_for('en'), get_language('ru'))

    def matches(text):
        return rule.match([lt.get_analyzed_sentence(text)])

    # correct sentences:
    assert len(matches('(О жене и детях не беспокойся, я беру их на свои руки).')) == 0
    # correct sentences:
    assert len(matches('Позже выходит другая «южная поэма» «Бахчисарайский фонтан» (1824).')) == 0
    assert len(matches('А "б" Д.')) == 0
    assert len(matches('а), б), Д)..., ДД), аа) и 1а)')) == 0
    # incorrect sentences:
    assert len(matches("В таком ключе был начат в мае 1823 в Кишинёве роман в стихах 'Евгений Онегин.")) == 1
    assert rule.get_id() == 'RU_UNPAIRED_BRACKETS'


# --- RussianVerbConjugationRuleTest ---

RIGHT_SENTENCES = ('Я иду', 'Она сидит', 'Оно думает', 'Они пишут', 'Мы думаем', 'Ты читаешь', 'Он творит', 'Вы идёте',
                   'Я ходил', 'Они ходили', 'Мы ходили', 'Она ходила', 'Оно ходило', 'Я ходила', 'Я пойду',
                   'Она пойдёт', 'Оно пойдёт', 'Мы пойдём', 'Ты пойдёшь', 'Я согласился на предложение.',
                   'Джек и я согласились', 'Ты может быть не помнишь.')

WRONG_SENTENCES = ('Я идёт', 'Она сидят', 'Оно думаешь', 'Они идёте', 'Мы думаю', 'Ты читает', 'Он творю',
                   'Я ходили', 'Они ходил', 'Мы ходила', 'Она ходил', 'Оно ходила', 'Я ходило', 'Я пойдёт',
                   'Она пойдут', 'Оно пойдёте', 'Мы пойдёшь', 'Ты пойду', 'Мы может поговорить здесь.')


def test_verb_conjugation_rule(lt):
    """RussianVerbConjugationRuleTest.testRussianVerbConjugationRule"""
    rule = RussianVerbConjugationRule(messages_for('en'))
    for sentence in WRONG_SENTENCES:
        assert len(rule.match(lt.get_analyzed_sentence(sentence))) == 1, 'Expected error in sentence: ' + sentence
    for sentence in RIGHT_SENTENCES:
        assert len(rule.match(lt.get_analyzed_sentence(sentence))) == 0, \
            'Did not expect error in sentence: ' + sentence


def test_verb_conjugation_rule_match(lt):
    rule = RussianVerbConjugationRule(messages_for('ru'))
    m = rule.match(lt.get_analyzed_sentence('Я идёт.'))[0]
    assert (m.from_pos, m.to_pos) == (0, 6)
    assert m.message == 'Неверное спряжение глагола или неверное местоимение'
    assert m.short_message == 'Неверное спряжение глагола'


# --- RussianWordCoherencyRuleTest ---

def _coherency_matches(lt, text):
    rule = RussianWordCoherencyRule(messages_for('en'))
    return rule.match([lt.get_analyzed_sentence(text)])


def test_word_coherency_rule(lt):
    """RussianWordCoherencyRuleTest.testRule"""
    assert len(_coherency_matches(lt, 'По шкале Цельсия абсолютному нулю соответствует температура −273,15 °C.')) == 0
    assert len(_coherency_matches(lt, 'По шкале Цельсия абсолютному нулю соответствует температура −273,15 °C.')) == 0
    assert len(_coherency_matches(lt, 'По шкале Цельсия абсолютному нулю соответствует температура −273,15 °C или '
                                      'ноль по шкале Кельвина.')) == 1


def test_word_coherency_call_independence(lt):
    """RussianWordCoherencyRuleTest.testCallIndependence"""
    assert len(_coherency_matches(lt, 'Абсолютный нуль.')) == 0
    # this won't be noticed, the calls are independent of each other
    assert len(_coherency_matches(lt, 'Ноль по шкале Кельвина.')) == 0


def test_word_coherency_complete_texts(lt):
    """RussianWordCoherencyRuleTest.testRuleCompleteTexts"""
    assert len(lt.check('По шкале Цельсия абсолютному нулю соответствует температура −273,15 °C или нуль по шкале '
                        'Кельвина.')) == 0
    assert len(lt.check('По шкале Цельсия абсолютному нулю соответствует температура −273,15 °C или ноль по шкале '
                        'Кельвина.')) == 1
    # cross-paragraph checks:
    assert len(lt.check('Абсолютный нуль.\n\nСовсем недостижим. И ноль по шкале Кельвина.')) == 1


# --- RussianWordRepeatRuleTest ---

def test_word_repeat_rule(lt):
    """RussianWordRepeatRuleTest.testRule"""
    rule = RussianWordRepeatRule(messages_for('en'))
    # correct
    assert len(rule.match(lt.get_analyzed_sentence('Повтор слов в предложении.'))) == 0
    # incorrect
    assert len(rule.match(lt.get_analyzed_sentence('Повтор слов в повтор предложении.'))) == 1
    assert rule.default_off
    assert rule.get_id() == 'RU_WORD_REPEAT'


# --- other rules ---

def test_simple_word_repeat_rule(lt):
    """RussianSimpleWordRepeatRule: no false alarms for "и и", "по по",
    "ПО по", "что что", "- -" and single letters"""
    rule = RussianSimpleWordRepeatRule(messages_for('ru'), get_language('ru'))

    def count(text):
        return len(rule.match(lt.get_analyzed_sentence(text)))

    assert count('Это дом дом.') == 1
    assert rule.get_id() == 'WORD_REPEAT_RULE'
    for text in ('Он и и она.', 'Ходить по по дорогам.', 'Установка ПО по сети.', 'Установка по ПО.',
                 'Это то, что что-то значит.', 'Буква Л Л.'):
        assert count(text) == 0, text
    # (case-sensitive like in Java)
    assert count('Что что это?') == 1
    assert count('Ж ж.') == 0


def test_filler_words_rule():
    rule = RussianFillerWordsRule(messages_for('ru'), get_language('ru'), None)
    assert rule.get_id() == 'FILLER_WORDS_RU'
    assert rule.default_off
    assert rule.is_filler_word('однако') and rule.is_filler_word('ух-ты') and not rule.is_filler_word('Однако')


def test_word_root_repeat_rule(lt):
    rule = RussianWordRootRepeatRule(messages_for('ru'))
    assert rule.get_id() == 'RU_WORD_ROOT_REPEAT'
    assert rule.default_off
    sentences = lt.analyze_text('Абрикос рос в саду. У меня на столе стоит абрикосный сок.')
    matches = rule.match(sentences)
    assert len(matches) == 1
    assert matches[0].message == '«абрикосный» и «абрикос» – однокоренные слова, их не стоит использовать ' \
                                 'одновременно'
