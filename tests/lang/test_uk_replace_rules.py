"""Ports of org.languagetool.rules.uk.SimpleReplaceRuleTest,
SimpleReplaceSoftRuleTest and SimpleReplaceRenamedRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.uk.replace_rules import SimpleReplaceRenamedRule, SimpleReplaceRule, SimpleReplaceSoftRule
from langtool.messages import messages_for
from langtool.tool import JLanguageTool

MESSAGES = messages_for('uk')
EN_MESSAGES = messages_for('en')


@pytest.fixture(scope='module')
def lt():
    require_dictionaries('uk')
    return JLanguageTool(get_language('uk'))


@pytest.fixture
def rule(lt):
    """SimpleReplaceRuleTest.setup"""
    return SimpleReplaceRule(EN_MESSAGES, lt.language.get_default_spelling_rule(), lt.language)


def test_simple_replace_rule(lt, rule):
    """SimpleReplaceRuleTest.testRule"""

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Ці рядки повинні збігатися."))
    assert len(matches) == 0

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence("Ці рядки повинні співпадати"))
    assert len(matches) == 1
    assert len(matches[0].suggested_replacements) == 2
    assert matches[0].suggested_replacements == ["збігатися", "сходитися"]
    assert "просторічна форма" not in matches[0].message

    matches = rule.match(lt.get_analyzed_sentence("Нападаючий"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Нападник", "Нападальний", "Нападний"]

    matches = rule.match(lt.get_analyzed_sentence("Нападаючого"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Нападник", "Нападальний", "Нападний"]

    # test enforce list
    # главком - дуже рідко зустрічається, як загальна назва
    #    matches = rule.match(lt.get_analyzed_sentence("главком"));
    #    assertEquals(1, len(matches));
    #    assertEquals(Arrays.asList("головком"), matches[0].suggested_replacements);

    # test ignoreTagged
    matches = rule.match(lt.get_analyzed_sentence("щедрота"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["щедрість", "гойність", "щедриня"]

    matches = rule.match(lt.get_analyzed_sentence("щедроти"))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("200 чоловік."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("Конрадом II і Генріхом III"))
    assert len(matches) == 0

    # TODO: should not react at all
    matches = rule.match(lt.get_analyzed_sentence("мікро-району"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["мікрорайону"]

    # subst + subst
    matches = rule.match(lt.get_analyzed_sentence("гребнем."))
    assert len(matches) == 0


def test_simple_replace_derivat(lt, rule):
    """SimpleReplaceRuleTest.testDerivat"""
    # derivat
    matches = rule.match(lt.get_analyzed_sentence("перелиставши."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["перегорнувши", "прогортаючи"]


def test_simple_replace_rule_part_of_multiword(lt):
    """SimpleReplaceRuleTest.testRulePartOfMultiword"""
    rule = SimpleReplaceRule(EN_MESSAGES, lt.language.get_default_spelling_rule(), lt.language)

    matches = rule.match(lt.get_analyzed_sentence("на думку проводжаючих"))
    assert len(matches) == 1

    #  @Test
    #  public void testSubstandards() throws IOException {
    #    SimpleReplaceRule rule = SimpleReplaceRule(EN_MESSAGES, lt.language.get_default_spelling_rule(), lt.language);
    #
    #    RuleMatch[] matches = rule.match(lt.get_analyzed_sentence("А шо такого?"));
    #    assertEquals(1, len(matches));
    #    assertEquals(Arrays.asList("що"), matches[0].suggested_replacements);
    #    assertEquals("Це розмовна просторічна форма", matches[0].message);
    #  }


def test_simple_replace_misspellings(lt):
    """SimpleReplaceRuleTest.testMisspellings"""
    rule = SimpleReplaceRule(EN_MESSAGES, lt.language.get_default_spelling_rule(), lt.language)

    matches = rule.match(lt.get_analyzed_sentence("ганделик"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["генделик"]
    #    assertEquals(Categories.MISC.toString(), matches[0].getRule().getCategory().getId());
    #    assertEquals("Це розмовна просторічна форма", matches[0].message);


def test_simple_replace_rule_by_tag(lt):
    """SimpleReplaceRuleTest.testRuleByTag"""
    rule = SimpleReplaceRule(EN_MESSAGES, lt.language.get_default_spelling_rule(), lt.language)

    matches = rule.match(lt.get_analyzed_sentence("спороутворюючого"))
    assert len(matches) == 1

    matches = rule.match(lt.get_analyzed_sentence("примкнувшим"))
    assert len(matches) == 1


def test_simple_replace_soft_rule(lt):
    """SimpleReplaceSoftRuleTest.testRule"""
    rule = SimpleReplaceSoftRule(MESSAGES, lt.language)

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Ці рядки повинні збігатися."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("у Трускавці."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("завидна"))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("Цей брелок"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["дармовис"]

    matches = rule.match(lt.get_analyzed_sentence("Не знайде спасіння."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["рятування", "рятунок", "порятунок", "визволення"]
    assert ": релігія" in matches[0].message

    # test ignoreTagged
    #    matches = rule.match(lt.get_analyzed_sentence("щедрота"));
    #    assertEquals(1, len(matches));
    #    assertEquals(Arrays.asList("щедрість", "гойність", "щедриня"), matches[0].suggested_replacements);
    #
    #    matches = rule.match(lt.get_analyzed_sentence("щедроти"));
    #    assertEquals(0, len(matches));


def test_simple_replace_soft_rule_for_derivats(lt):
    """SimpleReplaceSoftRuleTest.testRuleForDerivats"""
    rule = SimpleReplaceSoftRule(MESSAGES, lt.language)

    matches = rule.match(lt.get_analyzed_sentence("Підключивши"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Увімкнувши", "Під'єднавши", "Приєднавши"]


def test_simple_replace_renamed_rule(lt):
    """SimpleReplaceRenamedRuleTest.testRule"""
    rule = SimpleReplaceRenamedRule(MESSAGES)

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Київ."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("Дніпродзержинська"))
    assert len(matches) == 1, matches
    assert matches[0].suggested_replacements == ["Кам'янське", "кам'янський"]
    assert "2016" in matches[0].message

    matches = rule.match(lt.get_analyzed_sentence("дніпродзержинського."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["кам'янський"]

    matches = rule.match(lt.get_analyzed_sentence("Червонознам'янка."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Знам'янка", "Знаменка"]

    matches = rule.match(lt.get_analyzed_sentence("Переяслав-Хмельницький."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Переяслав", "переяславський"]
