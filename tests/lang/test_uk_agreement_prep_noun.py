"""Port of org.languagetool.rules.uk.TokenAgreementPrepNounRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.lang.uk import helpers as lh
from langtool.lang.uk.agreement_prep_noun import TokenAgreementPrepNounRule
from langtool.messages import messages_for
from uk_rule_test_base import RuleTestBase


class TestTokenAgreementPrepNounRule(RuleTestBase):

    @pytest.fixture(autouse=True)
    def _setup(self):
        require_dictionaries('uk')
        self.rule = TokenAgreementPrepNounRule(messages_for('uk'), self.lt.language)

    def test_rule(self):

        # correct sentences:
        self.assert_empty_match("без повного")
        self.assert_empty_match("без неба")

        self.assert_empty_match("по авеню")

        self.assert_empty_match("що за ганебна непослідовність?")

        self.assert_empty_match("щодо власне людини")
        self.assert_empty_match("у загалом симпатичній повістині")

        self.assert_empty_match("понад половина людей")
        self.assert_empty_match("з понад ста людей")

        self.assert_empty_match("по нервах")
        self.assert_empty_match("з особливою увагою")

        self.assert_empty_match("щодо бодай гіпотетичної здатності")
        self.assert_empty_match("хто їде на заробітки за кордон")

        self.assert_empty_match("піти в президенти")
        self.assert_empty_match("піти межі люди")
        self.assert_empty_match("вивів в люде")

        self.assert_empty_match("що то була за людина")
        self.assert_empty_match("що за людина")
        self.assert_has_error("що балотувався за цім округом")

        self.assert_empty_match("на дому")
        self.assert_empty_match("на біс")

        self.assert_empty_match("згідно з документом")
        self.assert_empty_match("Серед святкових товарів")
        self.assert_empty_match("зовсім не святкові товари Серед святкових товарів")

        self.assert_empty_match("при кому знайдено вогнепальну")
        self.assert_empty_match("За його словами Україна – це країна...")

        self.assert_empty_match("славетних од цареві")
        self.assert_empty_match("А шляхом тим була")

        self.assert_has_error("що, незважаючи стислі терміни візиту")

        # numr
        self.assert_has_error("до понад трьома")
        self.assert_has_error("до тисяча трьома")
        self.assert_empty_match("лежить із сотня срібних")

        self.assert_empty_match("залежно що вважати перемогою")

        self.assert_empty_match("окрім як українці")
        self.assert_empty_match("за двісті метрів")
        self.assert_empty_match("від мінус 1 до плюс 1")
        self.assert_empty_match("від мінус $1 до плюс 1")
        self.assert_empty_match("до мінус сорока град")
        self.assert_empty_match("до мінус шістдесяти")
        self.assert_empty_match("через років 10")
        self.assert_empty_match("через років зо два")
        self.assert_empty_match("на хвилин 9-10")
        self.assert_empty_match("співпрацювати із собі подібними")
        self.assert_empty_match("через усім відомі причини")
        self.assert_empty_match("через нікому не відомі причини")
        self.assert_empty_match("до нічим не виправданого нарцисизму")
        self.assert_empty_match("прийшли до ВАТ «Кривий Ріг цемент»")
        self.assert_empty_match("від А до Я")
        self.assert_empty_match("до та після")
        self.assert_empty_match("до схід сонця")
        self.assert_empty_match("з рана до вечора, від рана до ночі")
        self.assert_empty_match("до НАК «Надра України»")
        #    self.assert_empty_match("призвів до значною мірою демократичного середнього класу");
        self.assert_empty_match("Вони замість Андрій вибрали Юрій")
        self.assert_empty_match("час від часу нам доводилось")
        self.assert_empty_match("ні до чого доброго силові дії не призведуть")

        self.assert_empty_match("у святая святих")

        self.assert_empty_match("станом на зараз виконавча влада")

        self.assert_empty_match("в тисяча шістсот якомусь році")
        self.assert_empty_match("у ти\u0301сяча сімсо\u0301т вісімдеся\u0301т дев’я\u0301тому")
        self.assert_empty_match("на Піп Іван")

        #    self.assert_empty_match("Імена від Андрій до Юрій");  // називний між від і до рідко зустрічається але такий виняток ховає багато помилок

        #    self.assert_empty_match("як у Конана Дойла")).__len__()); //TODO
        #    self.assert_empty_match("як у Конану Дойла")).__len__());
        #    self.assert_empty_match("як у Конан Дойла")).__len__());

        #incorrect sentences:

        matches = self.rule_match("без небу")
        # check match positions:
        assert len(matches) == 1
        assert matches[0].suggested_replacements == ["неба"]
        assert "родовий" in matches[0].message, "Не містить «родовий»: " + matches[0].message

        matches = self.rule_match("не в останню чергу через корупцією, міжрелігійну ворожнечу")
        assert len(matches) == 1

        matches = self.rule_match("по нервам")
        # check match positions:
        assert len(matches) == 1
        assert matches[0].from_pos == 3
        assert matches[0].to_pos == 9
        assert matches[0].suggested_replacements == ["нервах", "нерви"]

        matches = self.rule_match("по швидко напруженим рукам")
        # check match positions:
        assert len(matches) == 1

        matches = self.rule_match("по «нервам»")
        assert len(matches) == 1

        self.assert_empty_match("про «справжній футбол»")

        self.assert_empty_match("на «ти»")
        self.assert_empty_match("писав про «Сновиди»")

        matches = self.rule_match("до не властиву")
        assert len(matches) == 1

        matches = self.rule_match("до не дуже властиву")
        assert len(matches) == 1

        self.assert_empty_match("На сьогодні рослинна їжа")

        # numr
        self.assert_has_error("в п'ятьом людям")
        self.assert_has_error("в понад п'ятьом людям")
        self.assert_empty_match("у тисяча якомусь")

        analyzed_sentence = self.lt.get_analyzed_sentence("О дівчина!")
        match = self.rule.match(analyzed_sentence)
        assert len(match) == 1
        suggested_replacements = match[0].suggested_replacements
        assert "дівчино" in suggested_replacements, "Did not find кличний «дівчино»: " + str(suggested_replacements)

        matches = self.rule_match("по церковним канонам")
        # check match positions:
        assert len(matches) == 1
        replacements = matches[0].suggested_replacements
        assert "церковних" in replacements, "Not found церковних among: " + str(replacements)

        # свята
        self.assert_empty_match("на Купала")
        self.assert_empty_match("на Явдохи")
        # вулиці
        self.assert_empty_match("на Мазепи")
        self.assert_empty_match("на Кульчицької")
        self.assert_empty_match("на Правди")
        self.assert_empty_match("на Ломоносова")
        # should be with hyphen
        #    self.assert_empty_match("переходить у Фрідріх Штрассе");
        # invert
        self.assert_empty_match("як на Кучми іменини")
        # ім'я, прізвище
        self.assert_empty_match("змінив ім'я на Фріц Ланг")
        self.assert_empty_match("Бо заміна прізвища Горбатий на Щербань передбачає i зміну ситуації.")
        #    self.assert_empty_match("поміняв Юрій Володимирович на Георгій Вурдалакович.");
        #  self.assert_empty_match("змінили з № 20 на 20-а");
        #  self.assert_empty_match("парні номери від 84-а до 104 включно");

        self.assert_empty_match("З одного боку на щастя сім’я Ющенків нарешті з’їжджає з державної дачі.")


        self.assert_empty_match("До сьогодні українська влада намагалася")

        self.assert_empty_match("Так висловлюються про екс-першого віце-спікера.")

        matches = self.rule_match("спиралося на місячної давнини рішенням")
        assert len(matches) == 1

        matches = self.rule_match("Від стягу Ататюрка до піратського прапору")
        assert len(matches) == 1

        matches = self.rule_match("згідно з документа")
        assert len(matches) == 1

        matches = self.rule_match("згідно зі змінам")
        assert len(matches) == 1

        matches = self.rule_match("зацікавлених у ви користанні")
        assert len(matches) == 1

        matches = self.rule_match("без правда")
        assert len(matches) == 1

        # TODO: ignored due to adj:v_zna "мінський"
        #    matches = self.rule_match("колега з Мінську");
        #    assertEquals(1, len(matches));

        matches = self.rule_match("В йому заграла кров.")
        assert len(matches) == 1

        matches = self.rule_match("  В йому заграла кров.")
        assert len(matches) == 1

        matches = self.rule_match("І от «В йому заграла кров».")
        assert len(matches) == 1

        matches = self.rule_match("похвалила при йому вкраїнську мову")
        assert len(matches) == 1

        matches = self.rule_match("думає на тим, як")
        assert len(matches) == 1

        self.assert_empty_match("гепатитів В та С")

        matches = self.rule_match("— О пан Єзус, захисти їх!")
        assert len(matches) == 1

        matches = self.rule_match("до Ленінграду")
        assert len(matches) == 1

        matches = self.rule_match("для логотипу")
        assert len(matches) == 1

        #    matches = self.rule_match("На фото: З Голлівуду Яринка Шуст привезла дві золоті медалі");
        #    assertEquals(1, len(matches));

    def test_zand_zna_as_rare(self):
        self.assert_empty_match("кілометрів зо три")
        self.assert_empty_match("години з 30")
        self.assert_empty_match("людей з десяток")  # десяток має омонімію з :f:
        self.assert_empty_match("насіння зі жменьку")
        self.assert_empty_match("розміром з долоню")
        self.assert_empty_match("шматок з кулак завбільшки")

        self.assert_empty_match("винайняло з тисячу модераторів")
        self.assert_empty_match("причеплено ще з сотню дерев'яних крамниць")
        #    self.assert_empty_match("виступав з повагом третій приводець");

        self.assert_empty_match("з 9-12-поверховий будинок")
        self.assert_empty_match("виниклу з нізвідки тему")
        self.assert_empty_match("з Ван Гогом")

        self.assert_has_error("зі землю")
        self.assert_has_error("туди ж з своє шкапою")
        self.assert_has_error("вискочив із барлоги")
        self.assert_has_error("від співпраці з компанію", "компанією", "компанії")

        # skip
        self.assert_empty_match("заввишки з її невеликий зріст")

        self.assert_empty_match("із добру годину")
        # TODO:
        #    self.assert_empty_match("ледь не з футбольне поле");
        #    self.assert_empty_match("з куряче яйце");

    # @Ignore in Java (TODO), passes here
    def test_rule_pron_pos_new(self):
        #TODO:
        self.assert_empty_match("від його покровителів")

    def test_rule_pron_pos(self):
        self.assert_empty_match("повернесть до них-таки.")

        self.assert_empty_match("колега поруч сонним виглядає")

        #TODO: temporary until we have a better logic
        self.assert_empty_match("при їх опублікуванні")
        self.assert_empty_match("всупереч їх рекомендаціям")
        self.assert_empty_match("на їх користь стягнуто")
        self.assert_empty_match("не всупереч, а тому, що він має")
        self.assert_empty_match("у його (лікаря) присутності")
        self.assert_has_error("до їх")

        self.assert_empty_match("Під його, без перебільшення, мудрим")
        self.assert_empty_match("до її, так би мовити, санітарного стану")
        self.assert_empty_match("в його, судячи з інтер’єру, службовому кабінеті")

        self.assert_empty_match("вплив на її або його здоров'я")
        self.assert_empty_match("щодо його \"лікування\":")
        self.assert_empty_match("За її словами,")

        self.assert_has_error("вище за їх?")
        #    self.assert_has_error("займався в їх помаленьку");
        self.assert_has_error("про їх говорилося")

        #  AnalyzedSentence analyzed_sentence = self.lt.get_analyzed_sentence("завдяки їх вдалим трюкам");
        analyzed_sentence = self.lt.get_analyzed_sentence("завдяки їх.")
        match = self.rule.match(analyzed_sentence)
        assert len(match) == 1
        suggested_replacements = match[0].suggested_replacements
        assert "їхнім" in suggested_replacements, "Did not find «їхній»: " + str(suggested_replacements)

        self.assert_empty_match("при її, м’яко кажучи, невеликій популярності")
        self.assert_empty_match("через її, м’яко кажучи, невелику популярність")

        self.assert_has_error("при його ж заняттів")

        # NEW
        self.assert_empty_match("освітою й без, адже останні, особливо робітники")
        self.assert_empty_match("сили від одне одного, як сусіди, партнери")
        self.assert_empty_match("вважали за краще брати")

    def test_rule_flexible_order(self):

        self.assert_has_error("по бодай маленьким справам")
        self.assert_has_error("по смішно маленьким справам")

        #TODO: insert
        #    self.assert_has_error("через, м’яко кажучи, невеликої популярності");
        #  self.assert_has_error("по, наприклад, постам");
        self.assert_empty_match("за цілком собі реалістичною соціальною")

        self.assert_empty_match("спиралося на місячної давнини рішення")

        self.assert_empty_match("На середньої довжини шубу")

        self.assert_empty_match("При різного роду процесах")

        self.assert_has_error("завдяки його прийомі")

        self.assert_empty_match("по лише їм цікавих місцях")
        self.assert_has_error("по лише їм цікавим місцям")

        self.assert_empty_match("від дуже близьких людей")
        self.assert_empty_match("завдяки саме цим сімом голосам")
        self.assert_empty_match("на мохом стеленому дні")
        self.assert_empty_match("який до речі вони присягалися")

        self.assert_empty_match("на нічого не вартий папірець")
        #TODO:
        #    self.assert_empty_match("до ледве що не членства");

        self.assert_has_error("призвів до значною мірою демократичному середньому класу")

        self.assert_has_error("це нас для дуже велика сума")

        self.assert_empty_match("для якої з мов воно первинне")

        self.assert_empty_match("об'єктивності заради слід зазначити")

        self.assert_has_error("у дуже обмеженим рамках")

        self.assert_empty_match("чи не проти я тієї церковної стройки")
        self.assert_empty_match("З точністю до навпаки ви все це побачите")

        self.assert_empty_match("Усупереч не те що лихим")
        self.assert_empty_match("весь світ замість спершу самому засвоїти")
        self.assert_empty_match("Йдеться про вже всім добре відому")

        self.assert_has_error("кинулися до мені перші з них")
        self.assert_has_error("Замість лимону можна брати")

        #TODO:
        #    self.assert_empty_match("не завдяки, а всупереч політиці, яку проводила влада");

        self.assert_empty_match("до дев’яносто дев’ятого")
        self.assert_empty_match("стосовно одне одного")
        self.assert_empty_match("ніч із тридцять першого серпня")

    def test_special_chars(self):
        self.assert_empty_match("до їм поді\u00ADбних")

        matches = self.rule_match("о справедли\u00ADвости.")
        assert len(matches) == 1

        matches = self.rule_match("по не\u0301рвам, по мо\u00ADстам, по воротам")
        # check match positions:
        assert len(matches) == 3

        assert matches[0].from_pos == 3
        assert matches[0].to_pos == 10
        assert matches[0].suggested_replacements == ["нервах", "нерви"]
        #    assertEquals(3, matches[1].from_pos);

        assert matches[1].from_pos == 15
        assert matches[1].suggested_replacements == ["мостах", "мости"]
        #    assertEquals(1, matches[1].from_pos);

        assert matches[2].from_pos == 27
        assert matches[2].suggested_replacements == ["воротах", "воротях", "ворота"]

    def test_unusual_characters(self):
        txt = "о стін\u00AD\nку"

        matches = self.rule_match(txt)
        assert len(matches) == 0


    def test_with_adv(self):
        match = self.rule_match("гречка у двічі дешевша ніж")
        assert len(match) == 1
        assert "Можливо, прийменник і прислівник" in match[0].message

    def test_is_capitalized(self):
        assert not lh.is_capitalized("боснія")
        assert lh.is_capitalized("Боснія")
        assert lh.is_capitalized("Боснія-Герцеговина")
        assert not lh.is_capitalized("По-перше")
        assert not lh.is_capitalized("ПаП")
        assert lh.is_capitalized("П'ятниця")
        assert not lh.is_capitalized("П'ЯТНИЦЯ")
        assert lh.is_capitalized("EuroGas")
        assert lh.is_capitalized("Рясна-2")
        assert not lh.is_capitalized("ДБЗПТЛ")
