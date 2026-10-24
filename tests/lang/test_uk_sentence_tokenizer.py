"""Port of org.languagetool.tokenizers.uk.UkrainianSRXSentenceTokenizerTest."""

from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer


def _split_tester():
    stokenizer = SRXSentenceTokenizer(get_language('uk'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)
    return test_split


def test_tokenize():
    """UkrainianSRXSentenceTokenizerTest.testTokenize"""
    test_split = _split_tester()
    test_split("Це просте речення.")
    test_split("Вони приїхали в Париж. ", "Але там їм геть не сподобалося.")
    test_split("Панк-рок — напрям у рок-музиці, що виник у середині 1970-х рр. у США і Великобританії.")
    test_split("Разом із втечами, вже у XV ст. почастішали збройні виступи селян.")
    test_split("На початок 1994 р. державний борг України становив 4,8 млрд. дол. США")
    test_split("4,8 млрд. дол. США. ", "Але наступного року...")
    test_split("Київ, вул. Сагайдачного, буд. 43, кв. 4.")
    test_split("на вул.\n  Сагайдачного.")

    test_split("Є.Бакуліна")
    test_split("Є.В.Бакуліна")
    test_split("Засідав І. П. Єрмолюк.")
    test_split("І. П. Єрмолюк скликав нараду.")
    test_split("Наша зустріч з А. Марчуком і Г. В. Тріскою відбулася в грудні минулого року.")
    test_split("Наша зустріч з А.Марчуком і М.В.Хвилею відбулася в грудні минулого року.")
    test_split("Комендант преподобний С.\u00A0Мокітімі")
    test_split("Комендант преподобний С.\u00A0С.\u00A0Мокітімі 1.")
    test_split("Комендант преподобний С.\u00A0С. Мокітімі 2.")
    test_split("Склад: акад. Вернадський, проф. Харченко, доц. Семеняк.")
    test_split("для др.  Харченко.")
    test_split("и др. ", "Потім вони пішли.")
    test_split("Ів. Франко.")
    test_split("Алисов Н. В. , Хореев Б. С.")
    test_split("і Г.-К. Андерсена")
    test_split(" — К. : Наук. думка, 1990.")
    test_split("Маркс К. «Показова держава»")

    test_split("Приходь! — буркнула йому.")
    test_split("«Приходь!» — буркнула йому.")

    # latin I
    test_split("М. Л. Гончарука, I. О. Денисюка")
    test_split("I. I. Дорошенко")

    test_split("елементів множини A. Отже, нехай")

    test_split("Опергрупа приїхала в с. Лісове.")
    test_split("Біля с. Березичі.")
    test_split("300 р. до н. е.")
    test_split("З 300 р. до н.е., і по цей день.")
    test_split("Пролісок (рос. пролесок) — маленька квітка.")
    test_split("Квітка Цісик (англ. Kvitka Cisyk також Kacey Cisyk від ініціалів К.С.); 4 квітня 1953р., Квінз, "
               "Нью-Йорк — 29 березня 1998 р., Мангеттен, Нью-Йорк) — американська співачка українського походження.")
    test_split("До Інституту ім. Глієра під'їжджає чорне авто.")
    test_split("До Інституту ім. акад. Вернадського.")
    test_split("До вулиці гетьмана Скоропадського під'їжджає чорне авто.")
    test_split("До табору «Артек».")
    #    test_split("Спільні пральні й т. д.", "Перемогли!");
    test_split("Спільні пральні й т. д. й т. п. ", "Перемогли!")
    test_split("в Хоролі з п. Кушніренком договорилися")
    test_split("і п. 10 від 23.1.33 р.")
    test_split("і т. п. ", "10 від 23.1.33 р.")
    test_split("і т.п. ", "10 від 23.1.33 р.")
    test_split("див. стор. 24.")
    test_split("Від англ.\n  File.")
    test_split("Від фр.  \nparachute.")
    test_split("фільму\nС. Ейзенштейна")

    test_split("Від р. Дніпро.")
    test_split("В 1941 р. Конрад Цузе побудував.")
    test_split("Наприкінці 1254 р. Данило почав")
    test_split("У травні 1949 р. Грушківський район")
    test_split("У травні 1949 р. \nГрушківський район")
    test_split("Упродовж 2011–2014 р. Швейцарія надасть")
    test_split("15 вересня 1995 р. Україною було підписано")
    test_split("Але закінчилося аж у січні 2013 р. ", "Як бачимо")

    test_split("інкримінують ч. 1 ст. 11")

    test_split("В цих світлих просторих апартаментах...  м’які крісла, килими, дорогі статуетки")
    test_split("А та — навперейми... «давайте мені!»")
    test_split("слугував ...    «витяг з протоколу зустрічі")
    test_split("на... Луганському")
    test_split("(вони самі це визнали. - Ред.)")

    test_split("Всього 33 тис. 356 особи")
    test_split("Всього 33 тис. (за словами прораба)")
    test_split("з яких приблизно   1,2 тис. – чоловіки.")
    test_split("У с. Вижва")
    test_split("Книжка (с. 200)")
    test_split("позначені: «с. Вижва»")
    test_split("в м.Києві")
    test_split("Микола Васюк (с. Корнієнки, Полтавська обл.)")
    test_split("U.S. Marine")
    test_split("B.B. King")
    test_split("Церква Св. Духа і церква св. Духа")
    test_split("Валерій (міліціонер-пародист.  –  Авт.) стане пародистом.")
    test_split("пише ред. Бойків")
    test_split("Сьогодні (у четвер.  - Ред.), вранці.")
    test_split(" ([27]див. Тиждень № 9, 2008)")

    test_split("і «Р. Б. К.»")
    test_split("У. Т: ")
    test_split("Іван Ч. (1914 р. н.)")
    test_split("альбом “Сніжність” (2006 р.) – разом із Юрієм")
    test_split("СК “Слон” (2008 р.) ", "У минулому харків’янка")

    test_split("рис. 14, Мал. 5; Арт. 88-99")

    test_split("нар. 1945 р.")
    test_split("Гліба (1995 р. нар.)")
    test_split("нар. бл. 1720 р.")
    test_split("(нар. у серпні 1904)")
    test_split("977 — нар. Кріс Мартін")
    test_split("Ради нар. депутатів")
    test_split("нар. арт. ", "України")
    test_split("біля нар. ", "У таких умовах")

    test_split("поч. 1945 - кін. 1946 р.")
    test_split("кін. ХІ — поч. ХІІІ ст.")


def test_web_entities():
    """UkrainianSRXSentenceTokenizerTest.testWebEntities"""
    test_split = _split_tester()
    test_split("Паляниця.Інфо")
    test_split("Жмеринка.City")


def test_tokenize_with_split():
    """UkrainianSRXSentenceTokenizerTest.testTokenizeWithSplit"""
    test_split = _split_tester()
    test_split("Всього 33 тис.", "А можей й більше")
    test_split("Їх було 7,5 млн.", "В кожного була сорочка.")
    test_split("Довжиною 30 с. ", "Поїхали.")
    test_split("Швидкістю 30 м/с. ", "Поїхали.")
    test_split("до 0,64 г/куб. дм. ", "Найчистіша")
    test_split("Останні 100 м. ", "І тут все пропало.")
    test_split("всього 20 м. ", "Почалося")
    test_split("Корисна площа 67 тис. кв.  м. ", "У 1954 році над Держпромом...")
    test_split("На 0,6°C. ", "Проте ми все маємо.")  # лат С
    test_split("На 0,6°С. ", "Проте ми все маємо.")  # укр С
    test_split("На 0,6 °C. ", "Проте ми все маємо.")  # лат С
    test_split("На 0,6 °С. ", "Проте ми все маємо.")  # укр С
    test_split("Приїхав у США. ", "Проте на другий рік.")
    test_split("Маємо страшне диво з див. ", "І кращого варіанту немає.")
    test_split("Взяти бодай XIII—XIX ст.", "Раніше п’єса була домінантою.")
    test_split("...Після перемоги у кваліфікації у стрільбі")
    test_split("...Somebody else")
    test_split("доволі стабільну стрільбу. ", "...Після перемоги у кваліфікації у стрільбі")
    test_split("доволі стабільну стрільбу\n ", "...Після перемоги у кваліфікації у стрільбі")
    # test_split("Категорії А. ", "Від якої");
    test_split("Лі Куан Ю. ", "Наприклад")
    test_split("король Георг V. ", "А нині")
    test_split("цар Петро I. ", "Він ухвалив")
    test_split("група В. ", "Усі віруси")


def test_tokenize_with_special_chars():
    """UkrainianSRXSentenceTokenizerTest.testTokenizeWithSpecialChars"""
    test_split = _split_tester()
    test_split("– С.\u202f5-7.")
    # still no split for initials
    test_split("товариш С.\u202fОхримович.")
    test_split("З особливим обуренням сприймав С.\u202f Шелухин легітимізацію")
    test_split("відбув у тюрмах.\u202f", "Нещодавно письменник")
    test_split("закрито бібліотеку української літератури.\u202f ", "Раніше відділ боротьби з екстремізмом...")
