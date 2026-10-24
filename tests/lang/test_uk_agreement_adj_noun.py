"""Port of org.languagetool.rules.uk.TokenAgreementAdjNounRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.lang.uk.agreement_adj_noun import TokenAgreementAdjNounRule
from langtool.messages import messages_for
from uk_rule_test_base import RuleTestBase


class TestTokenAgreementAdjNounRule(RuleTestBase):

    @pytest.fixture(autouse=True)
    def _setup(self):
        require_dictionaries('uk')
        self.rule = TokenAgreementAdjNounRule(messages_for('uk'), self.lt.language)

    def test_rule_tp(self):
        self.assert_has_error("скрутна справі")
        self.assert_has_error("район імпозантних віл")
        self.assert_has_error("офіційний статистика")
        self.assert_has_error("зелена яблуко.")
        self.assert_has_error("сп’янілі свободою")
        self.assert_has_error("кволий депутата")
        self.assert_has_error("кволого тюльпан")
        self.assert_has_error("цинічна винахідливості")
        self.assert_has_error("наступній рік свого життя")
        self.assert_has_error("жодного кубічного метру в Україні не буде")
        self.assert_has_error("складний рік на фондовим ринку")
        self.assert_has_error("є найкращий засобом для очистки")
        self.assert_has_error("має вчену ступінь з хімії")
        self.assert_has_error("розкішні чорні коси й, засукавши широкі рукава своєї сорочки,")
        self.assert_has_error("то коло стола її вишивані рукава мають, то коло печі")
        self.assert_has_error("валялись одірвані рукава кунтушів та поли жупанів")
        self.assert_has_error("вчинили страшенний диплома тичний галас")
        self.assert_has_error("Раймон Бенжамен і керівник європейського філії")
        self.assert_has_error("обвинувачення у вчинені злочину, передбаченого")

        self.assert_has_error("перша ступінь")
        self.assert_has_error("друга ступінь")

        self.assert_has_error("встановлена Верховної Радою 17 січня 2017 року")
        self.assert_has_error("фракцію у Верховні Раді й мати")

        # не працює через іменник "французька" (мова)
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("французька політик")).__len__());

        matches0 = self.rule_match("4 російських винищувача")
        assert len(matches0) == 1
        assert "[ч.р.: родовий, знахідний]" in matches0[0].message, "Message is wrong: " + matches0[0].message
        assert matches0[0].suggested_replacements == ["російських винищувачів", "російського винищувача"]

        # і-и
        self.assert_has_error("під зеківській нуль")
        self.assert_has_error("у повітряній простір")
        self.assert_has_error("в дитячий лікарні")
        self.assert_has_error("у Київський філармонії")
        self.assert_has_error("на керівні посаді")
        self.assert_has_error("незворотній процес")
        # taken care by xml rule
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("408 зниклих безвісті")).__len__());
        self.assert_has_error("нинішній російські владі")
        self.assert_has_error("заробітної платі")
        self.assert_has_error("сталеві панцирі")
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("бейсбольною битою машини")).__len__());
        self.assert_has_error("У львівській та київський Книгарнях")
        # relies on disambiguation
        self.assert_has_error("— робочій день.")
        self.assert_empty_match("президентів Леонідів Кравчука та Кучму")

        self.assert_has_error("угода на 30 років зі щорічного поставкою росіянами ...")

        # missing/extra letter
        self.assert_has_error("сприймали так власні громадян")
        self.assert_has_error("прокатні транспорті засоби")
        self.assert_has_error("Ви не притягнене капіталу")
        self.assert_has_error("потрібна змін поколінь")
        self.assert_has_error("Незадовільне забезпеченням паливом")
        self.assert_has_error("сочиться коштовний камінням")
        self.assert_has_error("будь-якої демократичної крани")
        # case government
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("що найбільший досягненням")).__len__());
        self.assert_has_error("Генеральній прокураторі")
        self.assert_has_error("була низька передумов")
        self.assert_has_error("після смерті легендарного Фреді Меркюрі")
        self.assert_has_error("юна викрадача й не здогадувалася")

        self.assert_has_error("По повернені кореспондентів")
        self.assert_has_error("в очікувані експериментатора")

        # wrong letter
        self.assert_has_error("певної мірою")
        self.assert_has_error("люмпенізується дедалі більша частини")
        self.assert_has_error("Державна фіскальну служба")
        self.assert_has_error("Як правило, це чоловіки, годувальними сімей")
        self.assert_has_error("з московською боку")

        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("від войовничих хозар")).__len__());

        # wrong gender
        self.assert_has_error("з насиджених барліг")
        self.assert_has_error("У польському Лодзі")
        self.assert_has_error("панування зимових сутінок")

        self.assert_has_error("за наявною інформацію")
        self.assert_has_error("асоціюється в нас із сучасною цивілізацію")
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("які вимагалися за тендерною документацію")).__len__());

        self.assert_has_error("зловживання монопольних становищем")
        self.assert_has_error("проживання та дворазове харчуванням")

        # we don't care much about adjp:actv:imperf
        # FIXME: ignored by adjp:actv:imperf + noun.*v_naz
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("нова правляча верстви")).__len__());
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("паралельно приймаючі пацієнтів")).__len__());

        # false v_rod with -у
        matches = self.rule_match("кримського безсмертнику")
        assert len(matches) == 1
        assert "Можливо" in matches[0].message, "Missing message for v_rod/v_dav -у/ю"

        # false кількисний числівник з v_rod
        matches = self.rule_match("до 7-ми відсотків ВВП")
        assert len(matches) == 1
        assert "Можливо" in matches[0].message, "Missing message for кількисний числівник"
        assert "7 відсотків" in matches[0].suggested_replacements

        #    self.assert_has_error("використати 25-ю бригаду");

        matches = self.rule_match("Та пахових ділянках")
        assert len(matches) == 1
        assert "Можливо" in matches[0].message, "Missing message for v_mis"

        # false v_rod with -а
        self.assert_has_error("федерального округа")

        # ne- together
        #TODO: fix later
        #    matches = rule.match(langTool.getAnalyzedSentence("пропонує незламані ураганами сучасності"));
        #    assertEquals(1, len(matches));
        #    assertTrue("Missing message for «не» пишеться окремо", matches[0].message.contains("писати окремо"));

        # false :nv
        self.assert_has_error("затверджений народним віче")
        self.assert_has_error("На великому родинному віче")
        self.assert_has_error("в листопаді 2015 року на народні віче до Кривого Рогу")
        self.assert_has_error("як японські ніндзя")
        self.assert_has_error("приталені пальто")

        # missing/extra space, dash etc
        self.assert_has_error("соціальними мережа ми")
        self.assert_has_error("принциповими країна ми")
        self.assert_has_error("отримала мандатна ведення")
        self.assert_has_error("по вуличному Копійчина")

        # lowercase city
        self.assert_has_error("У мінську влада")

        # barbarism
        # will be caught by barbarism rule
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("двометрові забори")).__len__());
        self.assert_empty_match("на пострадянський манер")


        self.assert_has_error("вздовж дніпровської вісі")
        self.assert_has_error("ніщо так не зближає приморських партизан")
        #FIXME: FN due to ignoring adj.v_oru + noun.*v_naz/zna
        #    self.assert_has_error("що робить її найвищою будівля");
        self.assert_has_error("як боротьбу сунітської більшість")

        self.assert_has_error("найцікавішій час")

        #    self.assert_empty_match("Ти, сякий-такий сину!");
        self.assert_has_error("відкинутий набагато років назад")  # should be "на багато"
        self.assert_has_error("символічною акцію стало складання")
        self.assert_has_error("в будь–яким момент")
        self.assert_has_error("хронічними порушення торговельних угод")

        # 148-ми правильно лише adj (восьмими), а numr (восьми) - є помилкою
        self.assert_has_error("вбивство 148-ми селян")


    def test_rule(self):

        # correct sentences:
        self.assert_empty_match("холодний яр")
        self.assert_empty_match("страшне плацебо")
        self.assert_empty_match("військової продукції")

        self.assert_empty_match("Ім'я Мандели, дане йому при народженні")
        self.assert_empty_match("Я не бачив сенсу в тому, щоб виклика\u0301ти свідків і захищатися.")
        self.assert_empty_match("погоджувальної комісії Інституту")
        self.assert_empty_match("відштовхнути нового колегу.")
        self.assert_empty_match("державну зраду.")
        self.assert_empty_match("(Пізніше Вальтер став першим")
        self.assert_empty_match("складовою успіху")
        self.assert_empty_match("про екс-першого віце-спікера.")
        self.assert_empty_match("Маю лишній квиток і подумав за свого найкращого друга")


        self.assert_empty_match("Засвідчувана досить часто наукою «гнучкість» — один із коренів\n" + "паранаукових явищ на кшталт «нової хронології» Фоменка.")

        # skip adv after adjp
        self.assert_empty_match("прикрита швидко рука")
        self.assert_has_error("прикрита швидко руку")
        self.assert_empty_match("прикрита отруйливо гарячим")
        self.assert_empty_match("після короткого резюме справи")
        self.assert_empty_match("білий як полотно")
        self.assert_empty_match("розділеного вже чверть століття")
        self.assert_empty_match("розділеного третину століття")
        self.assert_empty_match("заклопотані чимало людей")
        self.assert_empty_match("заклопотані дуже обмаль людей")
        #    self.assert_empty_match("З усіх опитаних майже половина відверто");
        self.assert_empty_match("заданою відносно спостерігача")
        self.assert_empty_match("опублікований увечері понеділка")

        self.assert_empty_match("зареєстровані зокрема БЮТівець Микола Булатецький та самовисуванець")

        self.assert_empty_match("схований всередині номера")

        self.assert_empty_match("надана як раз")
        self.assert_empty_match("підірваною ще раз")

        # from real examples


        # nv no plural
        #    self.assert_has_error("спортивні ЦРУ");
        self.assert_empty_match("спортивні ЦРУ")
        self.assert_empty_match("Сумське НПО")

    def test_proper_nouns(self):
        self.assert_empty_match("на Інститутській адвокати просили")

    def test_exceptions(self):
        # adj not noun
        self.assert_empty_match("у могутні Максимові обійми")

        # adj as noun
        self.assert_empty_match("надання болгарській статусу")

        self.assert_empty_match("старший зміни")

        self.assert_empty_match("Наступні півроку.")

        # pron
        self.assert_empty_match("одної шостої світу")
        self.assert_empty_match("Кожному наглядач кивав")

        # pron + adj:n:v_rod
        self.assert_empty_match("чогось схожого Європа")
        self.assert_empty_match("писав про щось подібне Юрій")

        self.assert_empty_match("з 11-ма годинами")

        # нічого нового
        self.assert_empty_match("ще чого доброго ціна впаде")

        # площею, об'ємом...
        self.assert_empty_match("чотирициліндровий об’ємом 1000 куб. см.")
        self.assert_empty_match("10 жовтих площею 1,5 ")
        self.assert_empty_match("безплатні довжиною від 100 до 1000 метрів")

        self.assert_empty_match("за метр кубічний води")

        # річних
        self.assert_empty_match("200% річних прибутку")

        # плюс
        self.assert_empty_match("муніципальна плюс виробнича")

        # головне
        self.assert_empty_match("Головне центр правильно вибити")
        self.assert_empty_match("вибране сучукрліту")

        # insert - має бути виділений комами
        #    self.assert_empty_match("Та схоже суд таки вийшов");
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("Та схоже суд таки вийшов")).__len__());

        # adv
        self.assert_empty_match("Менше народу – більше кисню")
        self.assert_empty_match("Найчастіше випадки прямого підкупу")
        self.assert_empty_match("– щонайперше олівець, простий, твердий")
        self.assert_empty_match("Найбільше звинувачень у відьомстві")
        self.assert_empty_match("— Раніше Україна неодноразово заявляла")

        # пара
        self.assert_empty_match("Від наступних пари десятків")
        # «низка» тут, як і пара, дозволяє множинний іменник
        self.assert_empty_match("Суд визнав неконституційними низку положень")

        self.assert_has_error("від наступних пари")

        self.assert_empty_match("Північний Рейн-Вестфалія")

        #TODO: too many FN with this exception
        #    self.assert_empty_match("тепер хоч по Підвальній трамваї можуть пройти");


    def test_exceptions_ostanni(self):
        self.assert_empty_match("До останніх італійці ставляться")
        self.assert_has_error("за останні час вони прийшли до влади")
        self.assert_empty_match("представник останньої Василь Бердников відповів")


    def test_exceptions_numbers(self):

        # два/три/чотири чоловіки
        self.assert_empty_match("33 народних обранці")
        self.assert_empty_match("ще троє автокефальних єпископи")
        self.assert_empty_match("два-три реальних кандидати")
        self.assert_empty_match("три жовтих обірваних чоловіки")
        self.assert_empty_match("обидва вітчизняних наукових ступені")
        self.assert_empty_match("3-4 реально хворих депутати")
        self.assert_empty_match("два–три колишніх кандидати")
        self.assert_empty_match("два (чи навіть три) різних завершення роману")

        self.assert_empty_match("два нових горнятка")
        self.assert_empty_match("два жіночих імені")
        self.assert_empty_match("два різних міста")
        self.assert_empty_match("два абсолютно різних міста")

        self.assert_empty_match("три предкові слов’янські племені")

        self.assert_empty_match("два «круглих столи»")

        self.assert_has_error("два високих депутат")
        self.assert_has_error("дві високих дівчині")
        self.assert_has_error("83,7 квадратних кілометра")

        # дріб
        self.assert_empty_match("дві мільярдних метра")
        self.assert_empty_match("п’ять шостих населення")
        self.assert_empty_match("чотирьох п’ятих прибутку")

        self.assert_has_error("п'ять шості світу")

        self.assert_empty_match("1/8-ї фіналу")
        self.assert_has_error("1/8-ї фіналом")

        self.assert_empty_match("В одній другій українка здолала")
        self.assert_empty_match("поступився в одній восьмій французу")

        self.assert_empty_match("дві других дівчини")
        self.assert_has_error("дві других дівчині")


        # 1–3-й класи
        self.assert_empty_match("1–3-й класи поснідали й побігли")
        self.assert_empty_match("у 5–8-му класах")
        self.assert_empty_match("на сьомому–восьмому поверхах")
        self.assert_empty_match("на 14—16-те місця")

        self.assert_has_error("3-й класи поснідали")
        self.assert_has_error("одному-два непоганих шанси")

        match = self.rule_match("залишилося сиротами 22-є дітей")
        assert len(match) == 1
        assert "літерне нарощення після кількісного числівника" in match[0].message

        self.assert_empty_match("восьмого – дев’ятого класів")
        self.assert_empty_match("перший — дев’ятий класи")

        # time
        self.assert_empty_match("і о 7-й ранку нас зустрічає")
        self.assert_empty_match("Призначений на 11-ту похід")
        self.assert_empty_match("о шостій ранку")
        self.assert_empty_match("дванадцята дня")

        # years
        self.assert_empty_match("Ставши 2003-го прем’єром")
        self.assert_empty_match("У 1990-х скрута змусила")
        self.assert_empty_match("за 2009-й відомство зобов’язало")
        self.assert_empty_match("підвів риску під 2011-м програмою «ТОП-100»")
        self.assert_empty_match("Лише в 1990-ті частину саду вдруге зробили доступною")
        self.assert_empty_match("У 2009–2010-му дефіцит бюджету сягав близько 1/3 видатків")
        self.assert_empty_match("в 1920–1930-х батько митця показав себе як український патріот")
        self.assert_empty_match("за часів «конфронтації» 2008–2009-го квота на них зросла")
        self.assert_empty_match("тільки за 1986–1988-й країна втратила близько 40 млрд крб")
        self.assert_empty_match("На початку двотисячних режисер зустрів двох людей")
        self.assert_empty_match("корифеї американської поезії 1950-60-х Лоренс Ферлінгетті")
        self.assert_empty_match("На зламі 80-90-их функціонери ...")

        self.assert_empty_match("щороку під Дев’яте травня")
        self.assert_empty_match("з четвертого по одинадцяте липня")

        self.assert_empty_match("замість звичного десятиліттями «Українського»")
        self.assert_empty_match("природний тисячею років підтверджений")

        self.assert_has_error("на 131-му хвилині")
        self.assert_has_error("О 12–ї годині")


        self.assert_empty_match("Анонсована тиждень тому домовленість")
        self.assert_empty_match("забули про популярні пару років тому")

        self.assert_empty_match("завищена разів у десять")
        self.assert_empty_match("інвестиція на найближчі років п’ять")
        self.assert_empty_match("до розташованого кілометрів за шість")
        self.assert_empty_match("заповнені відсотків на 80")
        self.assert_empty_match("лячно було перші хвилин 40")
        self.assert_empty_match("і посаджений років на 10–15")
        self.assert_empty_match("і піднятий відсотки на 3")
        self.assert_empty_match("Поховавши році в п'ятдесятому жінку")

        self.assert_empty_match("хвилини з 55-ї вірмени почали застосовувати пресинг")

        self.assert_empty_match("один 5-а клас")
        self.assert_empty_match("маршрутка номер 29-а фірми “Фіакр”")

        self.assert_empty_match("на вул. Рубчака, 17-а Тарас Стецьків")
        self.assert_empty_match("вулиці Володимира Великого, 35-а Юрій Борсук")

    def test_exceptions_other(self):

        # case government
        self.assert_empty_match("Завдяки останнім бізнес")

        # reverse order
        self.assert_empty_match("порядок денний парламенту")
        self.assert_empty_match("зокрема статтю 6-ту закону")
        self.assert_empty_match("князівством Литовським подоляни")
        self.assert_empty_match("абзац перший частини другої")
        self.assert_empty_match("абзац другий частини першої")
        self.assert_empty_match("частина четверта статті 53")

        # мати рівних
        self.assert_empty_match("яких не мала рівних українка")

        # імені
        self.assert_empty_match("Київський імені Шевченка")
        self.assert_empty_match("і колишня Маяковського")
        self.assert_empty_match("Львівської ім. С. Крушельницької")
        self.assert_empty_match("4-й Запорізький ім. гетьмана Б. Хмельницького")

        self.assert_has_error("у Великій Вітчизняній Війн")
        self.assert_has_error("у Великій Вітчизняній війна")
        self.assert_empty_match("Після Великої Вітчизняної будівництво істотно розширилося")

        # зразка
        self.assert_empty_match("польські зразка 1620—1650 років")

        # станом на
        self.assert_empty_match("чинних станом на 4 червня")

        self.assert_empty_match("а старший групи")

        # stable multiword
        self.assert_empty_match("Не пасли задніх міліціонери")
        self.assert_empty_match("сильних світу цього")
        self.assert_empty_match("найвпливовіших світу сього")
        self.assert_empty_match("усіх до єдиного")
        self.assert_empty_match("усі до єдиного депутати")
        self.assert_empty_match("Вольному воля")
        self.assert_empty_match("порядку денного засідань")
        self.assert_empty_match("лаву запасних партії")
        self.assert_empty_match("викладатися на повну артисти")
        self.assert_empty_match("молодшого гвардії сержанта")
        self.assert_empty_match("постійно на рівних міністри, президенти")

        self.assert_empty_match("під час Другої світової командири")

        self.assert_empty_match("до слова Божого людей")
        self.assert_empty_match("Різдва Христова вигнанець")
        self.assert_empty_match("ведуча Першого Національного Марія Орлова")

        self.assert_empty_match("дівоче Анна")

        self.assert_empty_match("В середньому тривалість курсів для отримання")
        self.assert_empty_match("в цілому результатом задоволені")

        self.assert_empty_match("на червень поточного року $29,3 млрд")

        # перший
        self.assert_empty_match("Одним із перших бажання придбати")
        self.assert_empty_match("Першими голодування оголосили депутати")
        self.assert_empty_match("Перший людина проходить")
        self.assert_empty_match("Перший митців принуджував")
        self.assert_empty_match("вважаючи перших джерелом")

        #TODO: due to ignoring перший we missing these:
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("Один із перший творів")).__len__());

        # нічого такого
        self.assert_empty_match("нічого протизаконного жінка не зробила")
        self.assert_empty_match("Нічого подібного Сергій не казав")
        self.assert_empty_match("Нічого поганого людям")
        self.assert_empty_match("що нічим дієвим ініціативи не завершаться")

        # TODO: streets
        #    self.assert_empty_match("бачити на Різницький представника донецького регіону");

        self.assert_has_error("на Західній України")


        # присудок ж.р. + професія
        self.assert_empty_match("переконана психолог")

        # adj as noun
        self.assert_empty_match("Серед присутніх Микола")
        self.assert_empty_match("контраргументами рідних засновника структури")
        self.assert_empty_match("спіймали на гарячому хабарників")

        self.assert_empty_match("була б зовсім іншою динаміка")
        self.assert_empty_match("була такою жорстокою політика")
        self.assert_empty_match("стали архаїчними структури")
        self.assert_empty_match("назвав винним Юрія")

        self.assert_empty_match("відмінних від російської моделей")

        self.assert_empty_match("не перевищував кількох десятих відсотка")

        self.assert_empty_match("Береженого Бог береже")

    def test_exceptions_predic(self):
        self.assert_empty_match("всі сумнівні слід викинути")
        self.assert_empty_match("все зроблене слід обов'язково перетворити")

    def test_exceptions_adjp(self):

        #////// adjp ////////////

        # adjp:actv:imperf + noun (case government)
        # we ignore adjp:actv.*:bad - it's handled by simple replace rule
        self.assert_empty_match("обмежуючий власність")
        self.assert_empty_match("створивший історію")


        # adjp + (весь) в біле/чорне
        self.assert_empty_match("Помальована в біле кімната")
        self.assert_empty_match("Помальована в усе біле кімната")

        self.assert_has_error("помальований в біле кімната")

        # adjp + noun.*v_oru
        self.assert_empty_match("вкриті плющем будинки")
        self.assert_empty_match("всі вкриті плющем")
        self.assert_empty_match("оприлюднений депутатом Луценком")
        self.assert_empty_match("щойно оголошених спікером як відсутніх")
        self.assert_empty_match("групи захищені законом від образ")
        self.assert_empty_match("змучений тягарем життя")
        self.assert_empty_match("відправлені глядачами протягом 20 хвилин")
        self.assert_empty_match("здивований запалом, який проступав")
        self.assert_empty_match("охопленому насильством ваальському трикутнику")
        self.assert_empty_match("переданих заповідником церкві")
        self.assert_empty_match("більше занепокоєних захистом власних прав")

        #TODO:
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("вкриті плющем будинок")).__len__());


        # adjp + adj:v_oru + noun (case governed by adjp)
        self.assert_empty_match("підсвічений синім діамант")


        # adjp + тисячу
        self.assert_empty_match("повторена тисячу разів")

        # adjp + a:v_oru + noun: (case from adjp)
        self.assert_empty_match("підсвічений синім діамант")

        self.assert_has_error("підсвічений синім діамантів")


        # adjp + noun (case government)
        self.assert_empty_match("Нав’язаний Австрії нейтралітет")
        self.assert_empty_match("Нав’язаний Австрії коаліцією")
        self.assert_empty_match("Наймилішою українцеві залишається бронза")
        self.assert_empty_match("на цих загальновідомих американцям зразках")
        self.assert_empty_match("слід бути свідомими необхідності")
        self.assert_empty_match("влаштованою Мазепі Петром")
        self.assert_empty_match("будуть вдячні державі Україна")
        self.assert_empty_match("мають бути підпорядковані служінню чоловікові")
        self.assert_empty_match("більше відомої загалу як")  # TODO: теоретично має бути кома перед «як»
        self.assert_empty_match("одержимі суверенітетом")

        self.assert_has_error("Нав’язаний Австрії нейтралітеті")
        #TODO:
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("змучений тягарем життю")).__len__());


    def test_exceptions_verb(self):

        # бути/стати/лишитися + adj:v_oru + noun:v_dav (gender matches adj)
        self.assert_empty_match("слід бути обережними туристам у горах")

        self.assert_has_error("слід бути обережною туристам у горах")


        # modal
        self.assert_empty_match("зараз повинне ділом довести")
        self.assert_empty_match("Вони здатні екскаватором переорювати")
        self.assert_empty_match("яке готове матір рідну продати")
        self.assert_empty_match("Через якийсь час був змушений академію покинути")


        # бути/стати/лишитися + adj:v_oru + noun:v_naz (gender matches adj)
        self.assert_empty_match("Досі була чинною заборона")
        self.assert_empty_match("Досі була б чинною заборона")
        self.assert_empty_match("Стає очевидною наявність")
        # стало adv messes it up
        #    self.assert_empty_match("стало незрозумілим повернення");
        self.assert_empty_match("було куди зрозумілішим гасло самостійності")
        self.assert_empty_match("є очевидною війна")
        self.assert_empty_match("була б такою ж суттєвою явка")
        self.assert_empty_match("і була б дещо абсурдною ситуація.")
        self.assert_empty_match("Стали дорожчими хліб чи бензин")

        #TODO: ignored by "визнали справедливою наставники" exception
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("Стає очевидним наявність")).__len__());
        # adj + noun agrees, verb + adj/noun agreement will be different rule
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("була чинним закон")).__len__());

        # verb + a:v_oru + n:v_naz (case matches verb)
        self.assert_empty_match("дівчат не залишила байдужими інформація")
        self.assert_empty_match("визнали справедливою наставники обох команд")
        self.assert_empty_match("визнало незаконною Міністерство юстиції")
        self.assert_empty_match("яку роблять знаковою плями на мундирі")
        self.assert_empty_match("видається цілком стабільною демократія")
        self.assert_empty_match("може бути не ідеальною форма тістечок")
        self.assert_empty_match("не можуть бути толерантними ізраїльтяни")
        #TODO: v_oru + v_oru
        #    self.assert_empty_match("визнано справедливою наставниками обох команд");


        # verb + adj.v_oru + noun:v_zna (case matches adj)
        self.assert_empty_match("які зроблять неможливою ротацію влади")
        self.assert_empty_match("зробити відкритим доступ")
        self.assert_empty_match("визнають регіональними облради")
        self.assert_empty_match("залишивши незруйнованим Карфаген")
        self.assert_empty_match("зробить обтяжливим використання")
        self.assert_empty_match("На сьогодні залишається невідомою доля близько 200 людей")

        self.assert_empty_match("виявлено побитою Катю")
        self.assert_empty_match("лишаючи порожньою клітку")
        self.assert_empty_match("роблячи жорсткішими правила")
        # adv
        self.assert_empty_match("вважає повністю вірною постанову")
        # conj
        self.assert_empty_match("визнав протиправним і недійсним внесення")

        # triggers необхідний + появу (д.в. ч.р від появ)
        self.assert_empty_match("зробило можливою і необхідною появу нового гравця")

        # TODO:
        #    self.assert_has_error("нашою територію кокаїн проходить");
        #    self.assert_has_error("будується з просторовою космологічною орієнтацію");
        #    self.assert_has_error("атеїстичною ідеологію не мала перетинатися");
        #    self.assert_has_error("завісивши його потертим пальто");
        #    self.assert_has_error("Європа визнає Голодомор своєю трагедію");
        #    self.assert_has_error("забезпечити визнання недійсним результат");
        #    self.assert_has_error("дайте таким волю");
        #    self.assert_has_error("вважати ж такими Сергія Таруту в «Батьківщині» чи Віктора Медведчука");
        self.assert_has_error("саме з такою тенденцію стикнулися")

        self.assert_has_error("був продиктований глибоким розуміння")

        #    self.assert_empty_match("чи має бути «доцільною участь»?");

        self.assert_has_error("вважають нелегітимними анексію")
        self.assert_has_error("не залишили байдужими адміністрацію")

        # ння + adj:v_oru + noun:v_rod
        self.assert_empty_match("визнання неконституційним закону")
        self.assert_empty_match("визнання недійсним рішення")
        self.assert_has_error("через визнання тут шкідливою орієнтацію на народну мову")

        self.assert_has_error("визнання неконституційними закону")
        self.assert_has_error("визнання недійсним рішенню")
        #TODO: FN due to ignoring adj.v_oru + noun.*v_naz/zna
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("визнання неконституційним закон")).__len__());
        #TODO:
        #  self.assert_empty_match("визнання легітимними президента і прем'єра");        // v_rod??


    def test_exceptions_adj(self):
        #////////// adj ///////////////

        # adj + noun (case government)
        self.assert_empty_match("жадібна землі")
        self.assert_empty_match("вдячного батьку")
        self.assert_empty_match("Я вдячний редакторові Вільяму Філліпсу")
        self.assert_empty_match("радий присутності генерала")
        self.assert_empty_match("відомий мешканцям")
        self.assert_empty_match("менш незрозумілу киянам")
        self.assert_empty_match("найстарший віком із нас")
        self.assert_empty_match("таких немилих серцю Булгакова")
        self.assert_empty_match("експозиція, присвячена Леоніду Іллічу")
        self.assert_empty_match("печаткою та вручене платнику")

        self.assert_empty_match("і кожна масою 10 кг")

        self.assert_has_error("жадібна землею")

        # adj + (case government) adj + noun (case match 1st adj)
        self.assert_empty_match("протилежний очікуваному результат")
        self.assert_empty_match("альтернативну олігархічній модель")
        self.assert_empty_match("альтернативні газовому варіанти")

        self.assert_has_error("альтернативну олігархічній порядку")
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("альтернативну олігархічному модель")).__len__());

        # adj.*v_oru + noun.*v_naz (case matches adj) (+ verb)
        self.assert_empty_match("найчисленнішими цеховики були саме в Грузії")
        self.assert_empty_match("Дефіцитною торгівля США є")
        self.assert_empty_match("Не менш виснажливою війна є і для ворога")
        #    self.assert_empty_match("Так, відносно чеснішими новини, за даними соціологів, стали");
        self.assert_empty_match("Найнижчою частка таких є на Півдні")
        self.assert_empty_match("розвинутою Україну назвати важко")

        #     ... -verb
        #    self.assert_empty_match("то сильнішим інтерес до альтернативної думки");
        self.assert_empty_match("кількість визнаних недійсними бюлетенів")

        # adj.v_oru + noun.*v_naz (no case match) (+verb)
        self.assert_empty_match("Слабшою критики вважають")
        self.assert_empty_match("найбільш райдужною перспектива членства в ЄС залишається")

        # adj.v_oru + noun:v_zna (+ verb)
        self.assert_empty_match("Однак безлюдним місто також не назвеш")
        self.assert_empty_match("Вагомим експерти називають той факт")
        # таким + v_zna
        self.assert_empty_match("такою ситуацію бачить сам")
        self.assert_empty_match("таким піднесеним президента не бачили давно")


        # adj:p: + риска
        self.assert_empty_match("Найближчі півроку-рік")
        self.assert_empty_match("найближчих тиждень-два")
        self.assert_empty_match("протягом минулих травня-липня")
        self.assert_empty_match("Перші рік-два влада відбивалася")
        self.assert_empty_match("суперкризовими січнем–лютим")

        self.assert_has_error("найближчі тиждень")

    def test_exceptions_prep_adj(self):
        # пропустити оборот prep+adj

        self.assert_empty_match("діє подібний до попереднього закон")
        self.assert_empty_match("з відмінним від їхнього набором цінностей")
        self.assert_empty_match("Про далеку від взірцевої поведінку")
        self.assert_empty_match("нижчими від ринкових цінами")
        self.assert_empty_match("протилежний до загальнодержавного процес")
        self.assert_empty_match("Схожої з тамтешньою концепції")
        self.assert_empty_match("відрізнялася від нинішньої ситуація")
        self.assert_empty_match("відрізнялася б від нинішньої ситуація")
        self.assert_empty_match("відрізнялося від російського способом")

        self.assert_has_error("асоціюється в нас із сучасною цивілізацію")

        self.assert_empty_match("На відміну від європейських санкції США")
        self.assert_empty_match("поряд з енергетичними Москва висувала")
        self.assert_empty_match("тотожні із загальносоюзними герб і прапор")

        self.assert_empty_match("чотири подібних до естонських звіти.")

        self.assert_empty_match("порівняно з попереднім результат")
        self.assert_empty_match("порівняно з російським рівень")

        # mistake 1999-им is not noun
        #    self.assert_empty_match("порівняно із 1999-им доходи автопідприємств");

        self.assert_has_error("він є одним із найстаріший амфітеатрів")
        self.assert_has_error("подібний до попереднього закони")
        self.assert_has_error("порівняний з попереднім результатів")
        self.assert_has_error("Схожої з тамтешньою концепція")
        self.assert_has_error("протилежний до загальнодержавному процес")
        self.assert_has_error("вдалися до збройної боротьбі")

        #  self.assert_empty_match("її острови відрізняються від Південної природою");


    def test_exceptions_plural(self):
        #///////// plurals /////////

        # plural + пів...
        self.assert_empty_match("на довгих півстоліття")
        self.assert_empty_match("цілих півмісяця")
        self.assert_empty_match("на довгих чверть століття")

        self.assert_has_error("на довгих місяця")

        self.assert_has_error("продукту, а просунути український фільми")

        # plural

        # adj:.:p + multiple nouns
        self.assert_empty_match("щоб моїх маму й сестер")
        self.assert_empty_match("власними потом i кров’ю")  # latin i -  we want AlphabetMixedRule to take care of this
        self.assert_empty_match("Перші тиждень чи два")
        self.assert_empty_match("зазначені ім'я, прізвище та місто")
        self.assert_empty_match("Житомирська, Кіровоградська області")
        self.assert_empty_match("ані судова, ані правоохоронна системи")
        self.assert_empty_match("шиїтську та сунітську, а також курдську частини")
        self.assert_empty_match("Чорного і Азовського морів")
        self.assert_empty_match("називає й традиційні корупцію, «відкати», хабарі")
        self.assert_empty_match("державні Ощадбанк, «Укргазбанк»")
        self.assert_empty_match("коринфський з іонійським ордери")
        self.assert_empty_match("від однієї й другої сторін")
        self.assert_empty_match("під’їздить один, другий автобуси")
        #    self.assert_empty_match("можуть зробити доступнішими фосфор чи калій");
        self.assert_empty_match("зв'язаних ченця з черницею")
        self.assert_empty_match("на зарубаних матір з двома синами")
        self.assert_empty_match("повоєнні Австрія з Фінляндією")
        self.assert_empty_match("Опозиційні Андрієвський і Черников")
        self.assert_empty_match("директори навчальної та середньої шкіл")
        self.assert_empty_match("протягом минулих травня – липня")
        self.assert_empty_match("практично відсутні транспорт, гомінкі базари")
        self.assert_empty_match("ВАЖЛИВІ МОТОРИКА І ВІДЧУТТЯ РІВНОВАГИ")
        self.assert_empty_match("канонізовані Іоанн XXIII і Іван Павло II")
        self.assert_empty_match("у дво- й тривимірному форматах")
        self.assert_empty_match("Однак ні паровий, ні електричний двигуни не могли")
        self.assert_empty_match("сміттєпереробного і/або сміттєспалювального заводів")
        self.assert_empty_match("130-те (мінус вісім позицій порівняно з 2009-м) та 145-те місця")
        self.assert_empty_match("ні у методологічному, ні у практичному аспектах.")
        self.assert_empty_match("Хоч в англомовній, хоч в україномовній версіях")

        # problem with anim/inanim
        #    self.assert_empty_match("Хто любить їсти сирі рибу та м’ясо.");

        # unknown words
        self.assert_empty_match("Большого та Маріїнського театрів")
        self.assert_empty_match("Пляжі 3, 4 і 5-ї категорій.")

        self.assert_has_error("У львівській та київський Книгарнях")
        #    self.assert_has_error("повоєнні Австрія з Фінляндію");
        self.assert_has_error("налякані Австрія з Фінляндію")
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("«Старий паразите...» І кокетлива інтонації ведучої не замасковує зовсім невиправдану")).__len__());

        self.assert_has_error("Судячи з січневих продаж, 2009-й може стати")
        self.assert_has_error("які наполягали на введені санкцій, будуть продовжуватися.")

        # multiple adj + noun:.*:p
        self.assert_empty_match("символізують творчий, оберігальний та руйнівний аспекти Вищої Сили")
        self.assert_empty_match("на місцевому, так і на центральному рівнях")
        self.assert_empty_match("передався повоєнним Відню та Парижу")

        # "long" plural
        self.assert_empty_match("найхарактерніші лояльність до влади й відданість місцевим лідерам.")
        self.assert_empty_match("і з першим, і з другим чоловіками")
        self.assert_empty_match("молодші Олександр Ірванець, Оксана Луцишина, Євгенія Кононенко")
        self.assert_empty_match("230 вчилися за старшинською і 120 за підстаршинською програмами")

    def test_exceptions_plural_conj_adv(self):

        self.assert_empty_match("уражені штаб ІДІЛ, а також збройний завод.")

        self.assert_empty_match("в соціальному, а згодом і в економічному аспектах")
        self.assert_empty_match("до апеляційного, а відтак і до конституційного судів")
        self.assert_empty_match("У переносному та навіть у прямому сенсах слова")
        self.assert_empty_match("в Чернівецькій і частково у Закарпатській областях")
        self.assert_empty_match("парламентської, а згодом і президентської кампаній")
        self.assert_empty_match("на західноєвропейському, а потім і на американському ринках")
        #TODO:
        #    self.assert_empty_match("Дохідна, а за нею й видаткова частини держбюджету");
        self.assert_empty_match("навчався в реальному, потім у землемірному училищах")

        self.assert_has_error("для того, щоб пожвавити культурне середовища села")

        #    self.assert_empty_match("канонізованих царя Давида, і князя Володимира");    // unnecessary comma

    def test_exceptions_insert_phrase(self):
        self.assert_empty_match("трагедію російського й, особливо, українського народів")
        self.assert_empty_match("Китай і, певною мірою, Росія зуміли поставити")

        self.assert_has_error("що, однак, не змінюють загальної картин")

        #TODO: here single gender for plural would help, but we don't have that in POS tag
        # alternatively we could try to use synthesizer to guess singular gender
        #    self.assert_has_error("історичне рішення, доки у виборчий кампанії");
        #    self.assert_has_error("На останньому відрізку, вже на український землі");
        #    self.assert_has_error("почувався в ньому не гірше, ніж у парламентський президії");
        #    self.assert_has_error("у сільському господарстві (як, зокрема, сербська компанії «МК груп»)");
        self.assert_has_error("про те, що в різних міста")
        self.assert_has_error("Він додав, що у комунальних підприємства")
        self.assert_has_error("наставник сказав, що на світовий першості")
        self.assert_has_error("Аль-Каїда, і чи не найстрашніше терористичний об’єднання")
        self.assert_has_error("буде очікувати, коли нова редакції")
        self.assert_has_error("вважає Порошенко, одночасно закликаючи європейську коаліції")
        self.assert_has_error("пішли вперед, хай і міліметровим кроками")
        self.assert_has_error("Словом, у проблематиці подвійного громадянств")
        self.assert_has_error("Правоохоронцями, зокрема, проведена масштабна операції")
        self.assert_has_error("Він так і не прийняв односторонню капітуляції")
        self.assert_has_error("Так, наприклад, косівським аматорами")
        self.assert_has_error("Якщо третина чи навіть половинна населення")
        self.assert_has_error("Думаю, це фейковий вкидання")
        self.assert_has_error("Сьогодні, наприклад, часта машинобудування")
        #TODO:
        self.assert_empty_match("латиську і, здається, молдавську поезії")
        self.assert_empty_match("в Житомирській чи, скажімо, Миколаївській областях")

        # we ignore all pronouns now but this may be useful in the future
    def test_pronouns(self):
        # pron
        self.assert_empty_match("усі решта")
        self.assert_empty_match("єдину для всіх схему")

        self.assert_empty_match("без таких документів")
        self.assert_empty_match("згідно з якими африканцям")
        self.assert_empty_match("чиновників, яким доступ")

        self.assert_empty_match("так само")
        self.assert_empty_match("перед тим гарант")
        self.assert_empty_match("усього місяць тому")

        # this, that...
        self.assert_empty_match("це мова сото")
        self.assert_empty_match("без якої сім’я не проживе")

        self.assert_empty_match("ВО «Свобода», лідер котрої Олег Тягрибок")

        self.assert_empty_match("стільки само свідків")

        self.assert_empty_match("що таке звук?")

        self.assert_empty_match("обстрілює один за одним охоронців.")

        self.assert_empty_match("повів сам військо")
        self.assert_empty_match("що ж таке геноцид")
        self.assert_empty_match("що воно таке еліта")
        self.assert_empty_match("Таких меншість.")

        self.assert_empty_match("той родом з Білорусі")
        self.assert_empty_match("в нашу Богом забуту Данину")

        self.assert_empty_match("той кібернетикою займається")

        self.assert_empty_match("такого світ ще не бачив")
        #  self.assert_empty_match("на таке Євросоюз напевне не наважиться");
        self.assert_has_error("позицію у такій спосіб, — ділиться думками")

        #    self.assert_empty_match("до такого студенти не готові");

        #TODO: turn back on when we can handle pron
        #    assertEquals(1, rule.match(langTool.getAnalyzedSentence("із такою самого зневагою")).__len__());
        #    self.assert_has_error("на вибори само висуванцем");

    def test_special_chars(self):
        self.assert_empty_match("зелений поді\u00ADум")

        self.assert_has_error("зелений по\u00ADділка.")

        self.assert_has_error("зе\u00ADлений поділка.")
