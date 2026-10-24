"""Port of org.languagetool.rules.uk.TokenAgreementNumrNounRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import SENTENCE_START_TAGNAME, AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.lang.uk.agreement_numr_noun import TokenAgreementNumrNounRule
from langtool.messages import messages_for
from uk_rule_test_base import RuleTestBase


class TestTokenAgreementNumrNounRule(RuleTestBase):

    @pytest.fixture(autouse=True)
    def _setup(self):
        require_dictionaries('uk')
        self.rule = TokenAgreementNumrNounRule(messages_for('uk'), self.lt.language)

    def test_rule_tn(self):
        """TokenAgreementNumrNounRuleTest.testRuleTn"""

        # correct sentences:
        self.assert_empty_match("два пацани")
        self.assert_empty_match("два паркани")
        self.assert_empty_match("двох пацанів")
        self.assert_empty_match("двох парканів")
        self.assert_empty_match("трьома пацанами")
        self.assert_empty_match("трьома парканами")
        self.assert_empty_match("шість пацанів")
        self.assert_empty_match("шість парканів")
        self.assert_empty_match("двадцять пацанів")
        self.assert_empty_match("восьми пацанів")
        self.assert_empty_match("восьми парканів")
        self.assert_empty_match("вісьма пацанами")
        self.assert_empty_match("вісьма парканами")
        self.assert_empty_match("декілька пацанів")
        self.assert_empty_match("декілька парканів")
        self.assert_empty_match("кілька ложок цукру")
        self.assert_empty_match("декільком пацанам")
        self.assert_empty_match("декільком парканам")
        self.assert_empty_match("вісім-дев'ять місяців")

        self.assert_empty_match("протягом шістьох місяців")
        self.assert_empty_match("за чотирма категоріями")
        self.assert_empty_match("за кількома торгівельними центрами")

        self.assert_empty_match("двоє дверей")
        self.assert_empty_match("трьох людей")

        self.assert_empty_match("22 червня")
        self.assert_empty_match("2 лютого їжака забрали")
        self.assert_empty_match("Ту-154 президента")

        # prep
        self.assert_empty_match("до 4 секунд")

        # двоїна
        self.assert_empty_match("2 сонця")
        # different apostrophes
        self.assert_empty_match("було дев’ять років")

        self.assert_empty_match("багато часу")
        self.assert_empty_match("Минуло багато-багато часу")
        self.assert_empty_match("багато заліза")
        self.assert_has_error("як багато білку", "багато білка", "багато білки", "багато білок", "багато білків")

        self.assert_empty_match("пів ковбаси")

        self.assert_empty_match("Вісімдесят Геннадію Терентійовичу")

        self.assert_empty_match("3 подолянина")
        self.assert_empty_match("два подолянина")
        self.assert_empty_match("три рабини")
        # обидва (є) волиняни
        self.assert_empty_match("Обидва волиняни")
        self.assert_empty_match("Обидва волинянина")

        # odd plurals
        self.assert_empty_match("дві Франції")
        self.assert_empty_match("дві СБУ")
        self.assert_empty_match("усі три Петра")
        self.assert_empty_match("у три погибелі")

        # TODO:
        # два майбуття
        #      self.assert_empty_match("Обидва тіста");
        #      self.assert_empty_match("в десяти мерами стали");

        # exceptions
        self.assert_empty_match("багато хто")
        self.assert_empty_match("багато які")
        self.assert_empty_match("мало наслідком")
        self.assert_empty_match("все одно йому")
        self.assert_empty_match("один одному руки")
        self.assert_empty_match("за день чи два мене")
        self.assert_empty_match("сьома ранку")
        self.assert_empty_match("години півтори")
        self.assert_empty_match("хвилини за півтори поїзд приїхав")
        self.assert_empty_match("1972 року")
        self.assert_empty_match("1970-1971 рр.")
        self.assert_empty_match("ст. 2 пункта 1")
        self.assert_empty_match("3 / 5 вугілля світу")
        self.assert_empty_match("3 / 4 понеділка")
        self.assert_empty_match("1992 рік")
        self.assert_empty_match("обоє винні")
        self.assert_empty_match("скільки-небудь осяжний")
        self.assert_empty_match("обоє режисери")
        self.assert_empty_match("сотні дві персон")
        # reverse order
        self.assert_empty_match("метрів п’ять килиму")
        self.assert_empty_match("років з п’ять в'язниці")
        self.assert_empty_match("рази може у два більший")
        self.assert_empty_match("десятка півтора списочників")
        # v_rod insert
        self.assert_empty_match("два провінційного вигляду персонажі")

        self.assert_empty_match("У свої вісімдесят пан Василь")

        self.assert_empty_match("№ 4 Тижня")

        self.assert_empty_match("57-ма вулиця")

        # TODO:
        #      self.assert_empty_match("в 10,5 розділах");
        #      self.assert_empty_match("З п’ятьма розмови не вийшло");
        #      // DO THIS
        #      self.assert_empty_match("сті-і-і-льки реформ");
        #      self.assert_empty_match("з 15 блоків дев'ять зав'язані на дуже");
        #      self.assert_empty_match("місяць або два декретної відпустки");
        #      // pron
        #      self.assert_empty_match("двісті наш бюджет");

        self.assert_empty_match("мати не стільки слух")
        self.assert_empty_match("$300 тис. кредиту")
        self.assert_empty_match("20 мм кредиту")
        # близько 2,5 млн збіжжя
        # 18,1 тис. медперсоналу
        self.assert_empty_match("три нікому не відомих")
        # too many FP
        self.assert_empty_match("несподіваного для багатьох висновку")
        self.assert_empty_match("чотири десятих відсотка")

        # special for пів...
        self.assert_empty_match("останніх півроку")

        self.assert_empty_match("дві англійською")
        self.assert_empty_match("за два злотих (15 грн)")

        # TODO: adj+numr
        self.assert_empty_match("Дев'яноста річниця")
        self.assert_empty_match("сьома вода на киселі")
        self.assert_empty_match("років п'ять люди")
        self.assert_empty_match("років через десять Литва")

        self.assert_empty_match("у 2020 мати надійний фундамент")
        self.assert_empty_match("тижнів зо два мати горшком воду носила")

    def test_rule_tp(self):
        """TokenAgreementNumrNounRuleTest.testRuleTp"""
        self.assert_has_error("два пацана", "два пацани")
        self.assert_has_error("дві пацани", "два пацани")
        self.assert_has_error("дві сонця", "два сонця")
        self.assert_has_error("обидва дівчини", "обидві дівчини")
        self.assert_empty_match("дві крайнощі")
        self.assert_empty_match("дві угорські фракції")
        self.assert_empty_match("два місцеві вожді")
        self.assert_empty_match("дві білі групи")
        self.assert_empty_match("дві наглядачки-африканерки")
        self.assert_empty_match("дві турбопрофесії")
        self.assert_empty_match("два імені")

        self.assert_empty_match("один-два громадянини")
        self.assert_empty_match("Обидві ходи")
        self.assert_empty_match("обидва атентати")
        self.assert_empty_match("обидва римляна")
        self.assert_empty_match("обидва римляна пішли")
        self.assert_has_error("обидва римляни пішли")
        self.assert_empty_match("і обидва римляни.")
        self.assert_empty_match("і обидва громадяни Польщі.")

        self.assert_empty_match("два друга")
        self.assert_has_error("два друзі")

        self.assert_has_error("два подоляни", "два подолянина")
        self.assert_has_error("33 подоляни", "33 подолянина")
        self.assert_has_error("три рабина")

        # може бути як adj "до 3-ї секунди"
        #    self.assert_has_error("до 3 секунди");

        # TODO:
        #    self.assert_has_error("3 Механістична");

        # TOOD:
        #  self.assert_empty_match("місяців зо два заготовки для них роблять");
        # по гектарів два капусти
        # через рік або два дороги стануть
        # Обидва провини не визнали

        matches00 = self.rule_match("обидві боки")
        assert len(matches00) == 1
        assert "Можливо, не збігається рід однини для множинної форми?" in matches00[0].message, \
            "Message is wrong: " + matches00[0].message

        # too many FP
        #    self.assert_has_error("двох пацанам");
        self.assert_has_error("восьми пацани", "восьми пацанів", "восьми пацанам", "восьми пацанах")
        self.assert_has_error("вісьма пацанах")
        self.assert_has_error("декілька пацани", "декілька пацанів")
        #    self.assert_has_error("багато дарами");
        self.assert_has_error("двоє двері", "двоє дверей")

        self.assert_empty_match("на один-півтора відсотка")
        self.assert_empty_match("півтора року")
        self.assert_empty_match("півтори сотні")
        # TODO:
        #      self.assert_empty_match("надання півтора мільйонам школярів");
        #      self.assert_empty_match("до півтора-двох років");

        # TODO: we don't know if singular is fem or masc so can't catch this
        #    self.assert_has_error("півтори антисемітських інциденти");

        self.assert_has_error("півтора роки", "півтора року")
        self.assert_has_error("півтора разу", "півтора раза")
        self.assert_has_error("іспиту півтора роки тому")

        # special suggestions
        matches0 = self.rule_match("у півтора рази")
        assert len(matches0) == 1
        assert "«раза»" in matches0[0].message, "Message is wrong: " + matches0[0].message
        assert matches0[0].suggested_replacements == ["півтора раза"]

        self.assert_has_error("півтора рублі", "півтора рубля")
        self.assert_has_error("півтори рублі")
        self.assert_has_error("за півтора місяці", "півтора місяця")
        self.assert_empty_match("за півтора довгих місяці")
        self.assert_empty_match("півтори місячні норми")

        self.assert_has_error("пів ковбаса", "пів ковбаси")

        self.assert_has_error("Останні три розділі", "три розділи")

        #    self.assert_has_error("4, 7 мільйона");

        self.assert_empty_match("0,5 курки")
        self.assert_has_error("5,5 градуси", "5,5 градуса", "5,5 градусів")
        self.assert_has_error("10,5 ніч", "10,5 ночі", "10,5 ночей")

        self.assert_has_error("2,5 мільйонів", "2,5 мільйона", "2,5 мільйони")
        self.assert_has_error("3,5 ночей", "3,5 ночі")
        self.assert_empty_match("14,5 років")
        self.assert_empty_match("протягом 3,5 років")
        #    self.assert_empty_match("протягом останніх 3,5 років");
        self.assert_has_error("2-2,5 метрів", "2-2,5 метра", "2-2,5 метри")
        self.assert_empty_match("1,5 метра")
        self.assert_has_error("1,5 метри", "1,5 метра")

        #    self.assert_has_error("2 ковбаса");

        # adj
        self.assert_empty_match("стільки різноманітних об'єктів")
        self.assert_empty_match("два нових горнятка")
        self.assert_empty_match("два нових веселих горнятка")
        self.assert_empty_match("три десятих")
        self.assert_empty_match("три вихідних")
        self.assert_empty_match("243 хворих")
        self.assert_empty_match("2-3 підозрюваних.")
        self.assert_empty_match("п'ять нових горняток")
        self.assert_empty_match("двадцять першого століття")
        self.assert_empty_match("чотири одиночних та 12 парних титулів")
        self.assert_empty_match(", чотири попередніх канули в Лету")

        # should be cauth by adj-noun rule
        self.assert_empty_match("п'ять нових горнятка")

        self.assert_has_error("два великих автобуса", "два великих автобуси")
        self.assert_has_error("434,5 злоякісних новоутворень")  # , "434,5 злоякісних новоутворення");
        self.assert_has_error("на 3 метра за останні", "3 метри", "3 метрів")
        self.assert_has_error("обидва ймовірних кандидата", "обидва ймовірних кандидати")
        self.assert_has_error("4 маленьких єнота", "4 маленьких єноти", "4 маленьких єнотів")
        self.assert_has_error("два легкових автомобіля", "два легкових автомобілі")

        self.assert_empty_match("на мільйон населення")
        self.assert_empty_match("тисячі люду")

    def test_rule_force_noun(self):
        """TokenAgreementNumrNounRuleTest.testRuleForceNoun"""
        self.assert_has_error("фронтові сто грам", "сто грамів")
        self.assert_has_error("10—12 мегават", "12 мегаватів")
        self.assert_has_error("12 німецьких солдат")
        #  self.assert_has_error("тисячу петабайт", "тисячу петабайтів");
        #    self.assert_has_error("30 РЕНТГЕН", "30 РЕНТГЕНІВ");
        self.assert_has_error("десятки тисяч своїх солдат")

        self.assert_has_error("п'ять байт", "п'ять байтів")
        self.assert_has_error("5 байт", "5 байтів")
        self.assert_has_error("мільйон байт", "мільйон байтів")
        self.assert_empty_match("мільйон байтів")
        self.assert_empty_match("тримали п'ять бейсбольних біт")
        #    self.assert_empty_match("мільйони потрібні");

        # біт також мн. від біта
        #    self.assert_has_error("це 16 біт,");
        self.assert_has_error("60 мікрорентген", "60 мікрорентгенів")

        self.assert_has_error("10 чоловік і жінок", "10 чоловіків")
        # handled by another rule: cholovik_with_numr
        self.assert_empty_match("10 чоловік.")

    def test_rule_ton(self):
        """TokenAgreementNumrNounRuleTest.testRuleTon"""
        self.assert_has_error("на 200 тон", "тонн")
        self.assert_has_error("2 млн тон", "тонн")
        self.assert_has_error("кілька тон", "тонн")
        self.assert_has_error("вісім тисяч тон", "тонн")
        self.assert_has_error("вісім тис. тон", "тонн")
        self.assert_has_error("22 тон", "тонн")
        self.assert_has_error("8,5 тон", "тонн")

    def test_rule_fract(self):
        """TokenAgreementNumrNounRuleTest.testRuleFract"""
        self.assert_empty_match("дві з половиною кулі")

        self.assert_has_error("два з половиною автобуса", "два з половиною автобуси")

    def test_rule_fractionals(self):
        """TokenAgreementNumrNounRuleTest.testRuleFractionals"""
        self.assert_has_error("2,4 кілограми", "2,4 кілограма")
        self.assert_has_error("2,4 мільйони", "2,4 мільйона")
        self.assert_has_error("2,54 мільйони", "2,54 мільйона")
        self.assert_empty_match("33,77 тонни")
        self.assert_empty_match("2,19 бала")
        self.assert_empty_match("33,77 мм")
        self.assert_empty_match("33,77 тис")
        self.assert_empty_match("33,5 роки")
        self.assert_empty_match("33,5 Терещенко")
        self.assert_empty_match("1998,1999 рр.")  # <!-- should have space after comma, see next rule -->
        self.assert_empty_match("із результатом 28,91 вона посіла третє місце")
        self.assert_empty_match("Становлять відповідно 0,5 і 0,3 її оцінки.")
        self.assert_empty_match("це на 0,21 краще за попередній рекорд світу.")

        self.assert_has_error("або у 2,2 рази.", "2,2 раза")
        self.assert_has_error("або у 2,2 раз", "2,2 раза")
        self.assert_empty_match("або у 2,2 раза.")
        self.assert_empty_match("або у 2 рази.")

    def test_rule_disambig_vzna(self):
        """TokenAgreementNumrNounRuleTest.testRuleDisambigVzna"""
        self.assert_has_error("два додаткових років")

        readings = []

        readings.append(AnalyzedTokenReadings(AnalyzedToken("", SENTENCE_START_TAGNAME, ""), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("три", "numr:p:v_zna", "три"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("села", "noun:inanim:p:v_zna", "село"), 0))

        sent = AnalyzedSentence(list(readings))

        assert len(self.rule.match(sent)) == 0

        readings = []

        readings.append(AnalyzedTokenReadings(AnalyzedToken("", SENTENCE_START_TAGNAME, ""), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("три", "numr:p:v_zna", "три"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("основні", "adj:p:v_zna:rinanim:compb", "основний"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("села", "noun:inanim:p:v_zna", "село"), 0))

        sent = AnalyzedSentence(list(readings))

        assert len(self.rule.match(sent)) == 0

        readings = []

        readings.append(AnalyzedTokenReadings(AnalyzedToken("", SENTENCE_START_TAGNAME, ""), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("три", "numr:p:v_zna", "три"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("золоті", "adj:p:v_zna:rinanim:compb", "золотий"), 0))

        sent = AnalyzedSentence(list(readings))

        assert len(self.rule.match(sent)) == 0

        readings = []

        readings.append(AnalyzedTokenReadings(AnalyzedToken("", SENTENCE_START_TAGNAME, ""), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("три", "numr:p:v_zna", "три"), 0))
        readings.append(AnalyzedTokenReadings(
            AnalyzedToken("мільйони", "мільйон/noun:inanim:p:v_zna:numr", "мільйон"), 0))

        sent = AnalyzedSentence(list(readings))

        assert len(self.rule.match(sent)) == 0
