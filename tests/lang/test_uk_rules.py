"""Ports of the Java tests of the smaller Ukrainian rules:
org.languagetool.rules.uk.TypographyRuleTest, HiddenCharacterRuleTest,
MissingHyphenRuleTest, MixedAlphabetsRuleTest, PunctuationCheckRuleTest,
UppercaseSentenceStartRuleTest, UkrainianWordRepeatRuleTest and
DateCheckFilterTest."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.uk.filters import DateCheckFilter
from langtool.lang.uk.rules import (HiddenCharacterRule, MissingHyphenRule, MixedAlphabetsRule, PunctuationCheckRule,
                                    TypographyRule, UkrainianUppercaseSentenceStartRule, UkrainianWordRepeatRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool

MESSAGES = messages_for('uk')
EN_MESSAGES = messages_for('en')


def _lt():
    require_dictionaries('uk')
    return JLanguageTool(get_language('uk'))


def test_typography_rule():
    """TypographyRuleTest.testRule"""
    rule = TypographyRule(MESSAGES)
    lt = _lt()

    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence("як-небудь"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("А\u2013Т"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("ХХ\u2013ХХІ"))) == 0

    # incorrect sentences:
    # TODO: does not work when word is the last in the sentence: "яскраво\u2013рожевий"
    matches = rule.match(lt.get_analyzed_sentence("яскраво\u2013рожевий."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["яскраво-рожевий", "яскраво \u2014 рожевий"]

    # test unknown word
    matches = rule.match(lt.get_analyzed_sentence("яскраво\u2013шуруровий."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["яскраво-шуруровий", "яскраво \u2014 шуруровий"]

    assert len(rule.match(lt.get_analyzed_sentence("ХХ\u2014ХХІ"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("Вовка,— волкова"))) == 0

    matches = rule.match(lt.get_analyzed_sentence("Вовка\u2014Волкова."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Вовка-Волкова", "Вовка \u2014 Волкова"]

    matches = rule.match(lt.get_analyzed_sentence("цукерок —знову низька"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["цукерок-знову", "цукерок \u2014 знову"]

    matches = rule.match(lt.get_analyzed_sentence("—знову низька"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["\u2014 знову"]

    matches = rule.match(lt.get_analyzed_sentence("знову—"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["знову \u2014"]

    assert len(rule.match(lt.get_analyzed_sentence("\u2014 Київ, 1994"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("\u2013 Київ, 1994"))) == 0

    matches = rule.match(lt.get_analyzed_sentence("важливіше \u2013потенційні"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["важливіше-потенційні", "важливіше \u2014 потенційні"]

    assert len(rule.match(lt.get_analyzed_sentence("Рахунки 1 класу –"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("\u2013"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence(" \u2013"))) == 0

    matches = rule.match(lt.get_analyzed_sentence("любили ,—люби"))
    assert len(matches) == 1
    assert len(matches[0].suggested_replacements) == 1


def test_hidden_character_rule():
    """HiddenCharacterRuleTest.testRule"""
    rule = HiddenCharacterRule(MESSAGES)
    lt = _lt()

    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence("сміття"))) == 0

    # incorrect sentences:

    matches = rule.match(lt.get_analyzed_sentence("смі\u00ADття"))
    # check match positions:
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["сміття"]


def test_missing_hyphen_rule():
    """MissingHyphenRuleTest.testRule"""
    lt = _lt()
    rule = MissingHyphenRule(MESSAGES, lt.language.tagger.get_word_tagger())

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence("Поїхали у штаб квартиру."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["штаб-квартиру"]

    matches = rule.match(lt.get_analyzed_sentence("Роблю «тайм аут»"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["тайм-аут"]

    matches = rule.match(lt.get_analyzed_sentence("Такий компакт диск."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["компакт-диск"]

    # spelling 2019

    matches = rule.match(lt.get_analyzed_sentence("Такий міні автомобіль."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["мініавтомобіль"]

    matches = rule.match(lt.get_analyzed_sentence("Арт проект вийшов провальним."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Артпроект"]

    matches = rule.match(lt.get_analyzed_sentence("Шоу бізнес - не моє."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["Шоубізнес"]

    matches = rule.match(lt.get_analyzed_sentence("на шоу поп–діви"))
    assert len(matches) == 0

    # TODO: hard - two errors, should be "ексвіцепрезидент"
    matches = rule.match(lt.get_analyzed_sentence("екс віце-президент"))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ["ексвіце-президент"]

    matches = rule.match(lt.get_analyzed_sentence("всі медіа півострова."))
    assert len(matches) == 0

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Тут все гаразд."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("Такий блок схемі не потрібен."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("конгрес Трансваалю."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("конгрес профспілок."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("рентген п'яти."))
    assert len(matches) == 0


def test_mixed_alphabets_rule():
    """MixedAlphabetsRuleTest.testRule"""
    rule = MixedAlphabetsRule(MESSAGES)
    lt = _lt()

    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence("сміття"))) == 0
    assert len(rule.match(lt.get_analyzed_sentence("not mixed"))) == 0
    assert len(rule.match(lt.get_analyzed_sentence("123454"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("x = a якщо"))) == 0
    assert len(rule.match(lt.get_analyzed_sentence("x − a та y − b"))) == 0
    assert len(rule.match(lt.get_analyzed_sentence("записати x та y через параметр t"))) == 0

    assert len(rule.match(lt.get_analyzed_sentence("ЛЮДИНИ І НАЦІЇ"))) == 0

    # incorrect sentences:

    matches = rule.match(lt.get_analyzed_sentence("смiття"))  # latin i
    # check match positions:
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні й латинські літери в одному слові"
    assert matches[0].suggested_replacements == ["сміття"]

    matches = rule.match(lt.get_analyzed_sentence("mіхed"))  # cyrillic i and x
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні літери замість латинських"
    assert matches[0].suggested_replacements == ["mixed"]

    matches = rule.match(lt.get_analyzed_sentence("горíти"))  # umlaut instead of accented і
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні й латинські літери в одному слові"
    assert matches[0].suggested_replacements == ["горі\u0301ти"]

    matches = rule.match(lt.get_analyzed_sentence("двоáктний"))  # lating á
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні й латинські літери в одному слові"

    matches = rule.match(lt.get_analyzed_sentence("Чорного i Азовського"))  # latin i
    assert len(matches) == 1
    assert matches[0].message == "Вжито латинську «i» замість кириличної"
    assert matches[0].suggested_replacements == ["і"]

    matches = rule.match(lt.get_analyzed_sentence("A нема"))  # latin A
    assert len(matches) == 1
    assert matches[0].message == "Вжито латинську «A» замість кириличної"
    assert matches[0].suggested_replacements == ["А"]

    matches = rule.match(lt.get_analyzed_sentence("Петро І"))  # cyrillic І
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "I"

    matches = rule.match(lt.get_analyzed_sentence("сибірську колекцію Петра І.\n\n Всім"))  # cyrillic І
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "I."

    matches = rule.match(lt.get_analyzed_sentence("Миколая І."))  # cyrillic І
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "I."

    matches = rule.match(lt.get_analyzed_sentence("У І кварталі"))  # cyrillic І
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "I"

    matches = rule.match(lt.get_analyzed_sentence("ЗА І ПРОТИ"))  # cyrillic І
    assert len(matches) == 0

    # ambiguous without semantics:
    # російський хемік Александр І. Опарін (1894–1980)

    matches = rule.match(lt.get_analyzed_sentence("Ленін В. І."))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("Тому І.    Вишенський радить "))
    assert len(matches) == 0

    matches = rule.match(lt.get_analyzed_sentence("у І ст."))  # cyrillic І
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "I"

    matches = rule.match(lt.get_analyzed_sentence("XІ"))  # cyrillic І and latin X
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні літери замість латинських"
    assert matches[0].suggested_replacements == ["XI"]

    matches = rule.match(lt.get_analyzed_sentence("ХI"))  # cyrillic X and latin I
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні літери замість латинських"
    assert matches[0].suggested_replacements == ["XI"]

    matches = rule.match(lt.get_analyzed_sentence("VIIІ-го"))  # latin VII and cyrillic І
    assert len(matches) == 1
    assert matches[0].message == \
        "Вжито кириличні літери замість латинських. Також: до римських цифр букви не дописуються."
    assert matches[0].suggested_replacements == ["VIII"]

    matches = rule.match(lt.get_analyzed_sentence("ІІІ-го"))  # cyrillic І
    assert len(matches) == 1
    assert matches[0].message == ("Вжито кириличні літери замість латинських на позначення римської цифри. "
                                  "Також: до римських цифр букви не дописуються.")
    assert matches[0].suggested_replacements == ["III"]

    matches = rule.match(lt.get_analyzed_sentence("ХІ"))  # cyrillic both X and I used for latin number
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні літери замість латинських на позначення римської цифри"
    assert matches[0].suggested_replacements == ["XI"]

    # we split tokens for latin numbers with \u2013 inside now
    #    matches = rule.match(lt.get_analyzed_sentence("ХI\u2013XX")); // cyrillic X and latin I
    #    assertEquals(1, len(matches));
    #    assertEquals("Вжито кириличні літери замість латинських", matches[0].message);
    #    assertEquals(Arrays.asList("ХІ–ХХ", "XI–XX"), matches[0].suggested_replacements);

    matches = rule.match(lt.get_analyzed_sentence("СOVID-19"))  # cyrillic С
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні літери замість латинських"
    assert matches[0].suggested_replacements == ["COVID-19"]

    matches = rule.match(lt.get_analyzed_sentence("австрo-турецької"))  # cyrillic both X and I used for latin number
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличні й латинські літери в одному слові"
    assert matches[0].suggested_replacements == ["австро-турецької"]

    matches = rule.match(lt.get_analyzed_sentence("Щеплення від гепатиту В."))  # cyrillic B
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "B"

    matches = rule.match(lt.get_analyzed_sentence("група А"))  # cyrillic А
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "A"

    matches = rule.match(lt.get_analyzed_sentence("На 0,6°С."))  # cyrillic С
    assert len(matches) == 1
    assert matches[0].message == "Вжито кириличну літеру замість латинської"
    assert matches[0].suggested_replacements[0] == "C"


def test_mixed_alphabets_combining_chars():
    """MixedAlphabetsRuleTest.testCombiningChars"""
    rule = MixedAlphabetsRule(MESSAGES)
    lt = _lt()

    # й and ї are done via combining characters: и + U+0306, ї + U+308
    matches = rule.match(lt.get_analyzed_sentence("Білоруськии\u0306 - украі\u0308нці"))
    assert len(matches) == 2
    assert matches[0].suggested_replacements[0] == "Білоруський"
    assert matches[1].suggested_replacements[0] == "українці"


def test_punctuation_check_rule():
    """PunctuationCheckRuleTest.testRule"""
    rule = PunctuationCheckRule(EN_MESSAGES)

    lt = _lt()

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Дві, коми. Ось: дві!!!"))
    assert len(matches) == 0

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("- Це ваша пряма мова?!!"))
    assert len(matches) == 0

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Дві,- коми!.."))
    assert len(matches) == 0

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Таке питання?.."))
    assert len(matches) == 0

    # correct sentences:
    matches = rule.match(lt.get_analyzed_sentence("Два  пробіли."))  # поки що ігноруємо - не царська це справа :)
    assert len(matches) == 0

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence("Дві крапки.."))
    assert len(matches) == 1
    assert len(matches[0].suggested_replacements) == 1
    assert matches[0].suggested_replacements[0] == "."

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence("Дві,, коми."))
    assert len(matches) == 1

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence("Не там ,кома."))
    assert len(matches) == 1

    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence("Двокрапка:- з тире."))
    assert len(matches) == 1


def test_uppercase_sentence_start_rule():
    """UppercaseSentenceStartRuleTest.testUkrainian"""
    lt = _lt()
    ukrainian = lt.language
    rule = UkrainianUppercaseSentenceStartRule(MESSAGES, ukrainian)
    rule.add_example_pair("<marker>речення</marker> має починатися з великої.",
                          "<marker>Речення</marker> має починатися з великої")

    assert len(rule.match(lt.analyze_text("Автор написав це речення з великої літери."))) == 0

    assert len(rule.match(lt.analyze_text("Він приїхав в с. Вижівка."))) == 0

    assert len(rule.match(lt.analyze_text("         http://narodna.pravda.com.ua"))) == 0

    matches = rule.match(lt.analyze_text("автор написав це речення з маленької літери."))
    assert len(matches) == 1
    assert len(matches[0].suggested_replacements) == 1
    assert matches[0].suggested_replacements[0] == "Автор"

    assert lt.check("Цей список з декількох рядків:\n\nрядок 1,\n\nрядок 2,\n\nрядок 3.") == []
    assert lt.check("Цей список з декількох рядків:\n\nрядок 1;\n\nрядок 2;\n\nрядок 3.") == []
    assert lt.check("Цей список з декількох рядків:\n\n 1) рядок 1;\n\n2) рядок 2;\n\n3)рядок 3.") == []

    assert lt.check("а) водопі\u0301й") == []


def test_word_repeat_rule():
    """UkrainianWordRepeatRuleTest.testRule"""
    lt = _lt()
    rule = UkrainianWordRepeatRule(MESSAGES, lt.language)

    def assert_empty_match(text):
        assert rule.match(lt.get_analyzed_sentence(text)) == [], text

    assert_empty_match("без повного розрахунку")
    assert_empty_match("без бугіма бугіма")
    assert_empty_match("без 100 100")
    assert_empty_match("1.30 3.20 3.20")
    assert_empty_match("ще в В.Кандинського")
    assert_empty_match("Від добра добра не шукають.")
    assert_empty_match("Що, що, а кіно в Україні...")
    assert_empty_match("Відповідно до ст. ст. 3, 7, 18.")
    assert_empty_match("Не можу сказати ні так, ні ні.")

    assert len(rule.match(lt.get_analyzed_sentence("без без повного розрахунку"))) == 1
    match = rule.match(lt.get_analyzed_sentence("Верховної Ради І і ІІ скликань"))
    assert len(match) == 1
    assert len(match[0].suggested_replacements) == 2


def test_date_check_filter_get_day_of_week():
    """DateCheckFilterTest.testGetDayOfWeek"""
    filter = DateCheckFilter()
    assert filter.get_day_of_week("Нед") == 1
    assert filter.get_day_of_week("Пон") == 2
    assert filter.get_day_of_week("пон") == 2
    assert filter.get_day_of_week("Понед.") == 2
    assert filter.get_day_of_week("Понеділок") == 2
    assert filter.get_day_of_week("понеділок") == 2
    assert filter.get_day_of_week("Вт") == 3
    assert filter.get_day_of_week("Сер") == 4
    assert filter.get_day_of_week("П'ят") == 6
    assert filter.get_day_of_week("Суб") == 7


def test_date_check_filter_month():
    """DateCheckFilterTest.testMonth"""
    filter = DateCheckFilter()
    assert filter.get_month("січ") == 1
    assert filter.get_month("гру") == 12
    assert filter.get_month("грудень") == 12
    assert filter.get_month("Грудень") == 12
    assert filter.get_month("ГРУДЕНЬ") == 12
