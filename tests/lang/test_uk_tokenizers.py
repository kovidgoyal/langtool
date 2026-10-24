"""Port of org.languagetool.tokenizers.uk.UkrainianWordTokenizerTest."""

from langtool.lang.uk.tokenizers import UkrainianWordTokenizer

w = UkrainianWordTokenizer()

def test_tokenize_url():
    url = "http://youtube.com:80/herewego?start=11&quality=high%3F"
    test_list = w.tokenize(url + " ")
    assert test_list == [url, " "]

    url = "http://example.org"
    test_list = w.tokenize(" " + url)
    assert test_list == [" ", url]

    url = "www.example.org"
    test_list = w.tokenize(url)
    assert test_list == [url]

    url = "elect@ombudsman.gov.ua"
    test_list = w.tokenize(url)
    assert test_list == [url]

    parts = ["https://www.foo.com/foo", " ", "https://youtube.com", " ", "Зе"]
    test_list = w.tokenize(''.join(parts))
    assert test_list == parts

    parts = ["https://www.phpbb.com/downloads/", "\"", ">", "сторінку"]
    test_list = w.tokenize(''.join(parts))
    assert test_list == parts

def test_tokenize_tags():
    txt = "<sup>3</sup>"
    test_list = w.tokenize(txt)
    assert test_list == ["<sup>", "3", "</sup>"]

def test_numbers():
    test_list = w.tokenize("300 грн на балансі")
    assert test_list == ["300", " ", "грн", " ", "на", " ", "балансі"]

    test_list = w.tokenize("надійшло 2,2 мільйона")
    assert test_list == ["надійшло", " ", "2,2", " ", "мільйона"]

    test_list = w.tokenize("надійшло 84,46 мільйона")
    assert test_list == ["надійшло", " ", "84,46", " ", "мільйона"]

    #TODO:
    #    test_list = w.tokenize("в 1996,1997,1998");
    #    assertEquals(Arrays.asList("в", " ", "1996,1997,1998"), test_list);

    test_list = w.tokenize("2 000 тон з 12 000 відер")
    assert test_list == ["2 000", " ", "тон", " ", "з", " ", "12 000", " ", "відер"]

    test_list = w.tokenize("надійшло 12 000 000 тон")
    assert test_list == ["надійшло", " ", "12 000 000", " ", "тон"]

    test_list = w.tokenize("надійшло 12\u202F000\u202F000 тон")
    assert test_list == ["надійшло", " ", "12 000 000", " ", "тон"]

    test_list = w.tokenize("до 01.01.42 400 000 шт.")
    assert test_list == ["до", " ", "01.01.42", " ", "400 000", " ", "шт."]


    # should not merge these numbers
    test_list = w.tokenize("2 15 мільярдів")
    assert test_list == ["2", " ", "15", " ", "мільярдів"]

    test_list = w.tokenize("у 2004 200 мільярдів")
    assert test_list == ["у", " ", "2004", " ", "200", " ", "мільярдів"]

    test_list = w.tokenize("в бюджеті-2004 200 мільярдів")
    assert test_list == ["в", " ", "бюджеті-2004", " ", "200", " ", "мільярдів"]

    test_list = w.tokenize("з 12 0001 відер")
    assert test_list == ["з", " ", "12", " ", "0001", " ", "відер"]


    test_list = w.tokenize("сталося 14.07.2001 вночі")
    assert test_list == ["сталося", " ", "14.07.2001", " ", "вночі"]

    test_list = w.tokenize("вчора о 7.30 ранку")
    assert test_list == ["вчора", " ", "о", " ", "7.30", " ", "ранку"]

    test_list = w.tokenize("вчора о 7:30 ранку")
    assert test_list == ["вчора", " ", "о", " ", "7:30", " ", "ранку"]

    test_list = w.tokenize("3,5-5,6% 7° 7,4°С")
    assert test_list == ["3,5-5,6", "%", " ", "7", "°", " ", "7,4", "°", "С"]

    # still want together Т-80М, 9б, 3x6
    #    test_list = w.tokenize("+400C");
    #    assertEquals(Arrays.asList("+", "400", "C"), test_list);

    test_list = w.tokenize("відбулася 17.8.1245")
    assert test_list == ["відбулася", " ", "17.8.1245"]

    test_list = w.tokenize("1814.03.09")
    assert test_list == ["1814.03.09"]

def test_numbers_missing_space():
    test_list = w.tokenize("від 12 до14 років")
    assert test_list == ["від", " ", "12", " ", "до", "14", " ", "років"]

    test_list = w.tokenize("до14-15")
    assert test_list == ["до", "14-15"]

    test_list = w.tokenize("Т.Шевченка53")
    assert test_list == ["Т.", "Шевченка", "53"]

    #    test_list = w.tokenize("«Тен»103.");
    #    assertEquals(Arrays.asList("«", "Тен", "»", "103", "."), test_list);

    test_list = w.tokenize("«Мак2»")
    assert test_list == ["«", "Мак2", "»"]

    test_list = w.tokenize("км2")
    assert test_list == ["км", "2"]

    test_list = w.tokenize("Мі17")
    assert test_list == ["Мі", "17"]

    test_list = w.tokenize("000ххх000")
    assert test_list == ["000ххх000"]

def test_plus():
    test_list = w.tokenize("+20")
    assert test_list == ["+", "20"]

    test_list = w.tokenize("-20")
    assert test_list == ["-", "20"]

    test_list = w.tokenize("–20")
    assert test_list == ["\u2013", "20"]

    test_list = w.tokenize("прислівник+займенник")
    assert test_list == ["прислівник", "+", "займенник"]

    test_list = w.tokenize("+займенник")
    assert test_list == ["+", "займенник"]

    test_list = w.tokenize("Роттердам+ ")
    assert test_list == ["Роттердам+", " "]

def test_superscript():
    test_list = w.tokenize("дружини¹")
    assert test_list == ["дружини", "¹"]

    test_list = w.tokenize("км²")
    assert test_list == ["км", "²"]

    test_list = w.tokenize("примітка³²")
    assert test_list == ["примітка", "³", "²"]

    test_list = w.tokenize("X²")
    assert test_list == ["X²"]

def test_tokenize():
    test_list = w.tokenize("Вони прийшли додому.")
    assert test_list == ["Вони", " ", "прийшли", " ", "додому", "."]

    test_list = w.tokenize("Вони прийшли пʼятими зів’ялими.")
    assert test_list == ["Вони", " ", "прийшли", " ", "п'ятими", " ", "зів'ялими", "."]

    #    test_list = w.tokenize("Вони\u0301 при\u00ADйшли пʼя\u0301тими зів’я\u00ADлими.");
    #    assertEquals(Arrays.asList("Вони", " ", "прийшли", " ", "п'ятими", " ", "зів'ялими", "."), test_list);

    test_list = w.tokenize("я українець(сміється")
    assert test_list == ["я", " ", "українець", "(", "сміється"]

    test_list = w.tokenize("ОУН(б) та КП(б)У")
    assert test_list == ["ОУН(б)", " ", "та", " ", "КП(б)У"]

    test_list = w.tokenize("Негода є... заступником")
    assert test_list == ["Негода", " ", "є", "...", " ", "заступником"]

    test_list = w.tokenize("Запагубили!.. також")
    assert test_list == ["Запагубили", "!..", " ", "також"]

    test_list = w.tokenize("Цей графин.")
    assert test_list == ["Цей", " ", "графин", "."]

    test_list = w.tokenize("— Гм.")
    assert test_list == ["—", " ", "Гм", "."]

    test_list = w.tokenize("стін\u00ADку")
    assert test_list == ["стін\u00ADку"]

    test_list = w.tokenize("стін\u00AD\nку")
    assert test_list == ["стін\u00AD\nку"]

    test_list = w.tokenize("п\"яний")
    assert test_list == ["п\"яний"]

    test_list = w.tokenize("▶Трансформація")
    assert test_list == ["▶", "Трансформація"]

    test_list = w.tokenize("усмішку😁")
    assert test_list == ["усмішку", "😁"]

def test_initials():
    test_list = w.tokenize("Засідав І.Єрмолюк.")
    assert test_list == ["Засідав", " ", "І.", "Єрмолюк", "."]

    test_list = w.tokenize("Засідав І.   Єрмолюк.")
    assert test_list == ["Засідав", " ", "І.", " ", " ", " ", "Єрмолюк", "."]

    test_list = w.tokenize("Засідав І. П. Єрмолюк.")
    assert test_list == ["Засідав", " ", "І.", " ", "П.", " ", "Єрмолюк", "."]

    test_list = w.tokenize("Засідав І.П.Єрмолюк.")
    assert test_list == ["Засідав", " ", "І.", "П.", "Єрмолюк", "."]

    test_list = w.tokenize("І.\u00A0Єрмолюк.")
    assert test_list == ["І.", "\u00A0", "Єрмолюк", "."]

    test_list = w.tokenize("Засідав Єрмолюк І.")
    assert test_list == ["Засідав", " ", "Єрмолюк", " ", "І."]

    test_list = w.tokenize("Засідав Єрмолюк І. П.")
    assert test_list == ["Засідав", " ", "Єрмолюк", " ", "І.", " ", "П."]

    test_list = w.tokenize("Засідав Єрмолюк І. та інші")
    assert test_list == ["Засідав", " ", "Єрмолюк", " ", "І.", " ", "та", " ", "інші"]

def test_abbreviations():
    # скорочення
    test_list = w.tokenize("140 тис. працівників")
    assert test_list == ["140", " ", "тис.", " ", "працівників"]

    test_list = w.tokenize("450 тис. 297 грн")
    assert test_list == ["450", " ", "тис.", " ", "297", " ", "грн"]

    test_list = w.tokenize("297 грн...")
    assert test_list == ["297", " ", "грн", "..."]

    test_list = w.tokenize("297 грн.")
    assert test_list == ["297", " ", "грн", "."]

    #    test_list = w.tokenize("297 грн.!!!");
    #    assertEquals(Arrays.asList("297", " ", "грн.", "!!!"), test_list);

    #    test_list = w.tokenize("297 грн.??");
    #    assertEquals(Arrays.asList("297", " ", "грн.", "??"), test_list);

    test_list = w.tokenize("450 тис.")
    assert test_list == ["450", " ", "тис."]

    test_list = w.tokenize("450 тис.\n")
    assert test_list == ["450", " ", "тис.", "\n"]

    test_list = w.tokenize("354\u202Fтис.")
    assert test_list == ["354", "\u202F", "тис."]

    test_list = w.tokenize("911 тис.грн. з бюджету")
    assert test_list == ["911", " ", "тис.", "грн", ".", " ", "з", " ", "бюджету"]

    test_list = w.tokenize("за $400\n  тис., здавалося б")
    assert test_list == ["за", " ", "$", "400", "\n", " ", " ", "тис.", ",", " ", "здавалося", " ", "б"]

    test_list = w.tokenize("найважчого жанру— оповідання")
    assert test_list == ["найважчого", " ", "жанру", "—", " ", "оповідання"]

    test_list = w.tokenize("\u2015оповідання")
    assert test_list == ["\u2015", "оповідання"]

    test_list = w.tokenize("проф. Артюхов")
    assert test_list == ["проф.", " ", "Артюхов"]

    test_list = w.tokenize("чл.-кор. Артюхов")
    assert test_list == ["чл.-кор.", " ", "Артюхов"]


    test_list = w.tokenize("проф.\u00A0Артюхов")
    assert test_list == ["проф.", "\u00A0", "Артюхов"]

    test_list = w.tokenize("Ів. Франко")
    assert test_list == ["Ів.", " ", "Франко"]

    test_list = w.tokenize("кутю\u00A0— щедру")
    assert test_list == ["кутю", "\u00A0", "—", " ", "щедру"]

    test_list = w.tokenize("також зав. відділом")
    assert test_list == ["також", " ", "зав.", " ", "відділом"]

    test_list = w.tokenize("до н. е.")
    assert test_list == ["до", " ", "н.", " ", "е."]

    test_list = w.tokenize("до н.е.")
    assert test_list == ["до", " ", "н.", "е."]

    test_list = w.tokenize("в. о. начальника")
    assert test_list == ["в.", " ", "о.", " ", "начальника"]

    test_list = w.tokenize("в.о. начальника")
    assert test_list == ["в.", "о.", " ", "начальника"]

    test_list = w.tokenize("100 к.с.")
    assert test_list == ["100", " ", "к.", "с."]

    test_list = w.tokenize("1998 р.н.")
    assert test_list == ["1998", " ", "р.", "н."]

    test_list = w.tokenize("22 коп.")
    assert test_list == ["22", " ", "коп."]

    test_list = w.tokenize("800 гр. м'яса")
    assert test_list == ["800", " ", "гр.", " ", "м'яса"]

    test_list = w.tokenize("18-19 ст.ст. були")
    assert test_list == ["18-19", " ", "ст.", "ст.", " ", "були"]

    test_list = w.tokenize("І ст. 11")
    assert test_list == ["І", " ", "ст.", " ", "11"]

    test_list = w.tokenize("куб. м")
    assert test_list == ["куб.", " ", "м"]

    test_list = w.tokenize("куб.м")
    assert test_list == ["куб.", "м"]

    test_list = w.tokenize("ам. долл")
    assert test_list == ["ам.", " ", "долл"]

    test_list = w.tokenize("4 дол.")
    assert test_list == ["4", " ", "дол."]

    test_list = w.tokenize("св. ап. Петра")
    assert test_list == ["св.", " ", "ап.", " ", "Петра"]

    test_list = w.tokenize("У с. Вижва")
    assert test_list == ["У", " ", "с.", " ", "Вижва"]

    test_list = w.tokenize("оз. Вижва")
    assert test_list == ["оз.", " ", "Вижва"]

    test_list = w.tokenize("Довжиною 30 см. з гаком.")
    assert test_list == ["Довжиною", " ", "30", " ", "см", ".", " ", "з", " ", "гаком", "."]

    test_list = w.tokenize("Довжиною 30 см. Поїхали.")
    assert test_list == ["Довжиною", " ", "30", " ", "см", ".", " ", "Поїхали", "."]

    test_list = w.tokenize("100 м. дороги.")
    assert test_list == ["100", " ", "м", ".", " ", "дороги", "."]

    test_list = w.tokenize("в м.Київ")
    assert test_list == ["в", " ", "м.", "Київ"]

    test_list = w.tokenize("На висоті 4000 м...")
    assert test_list == ["На", " ", "висоті", " ", "4000", " ", "м", "..."]

    test_list = w.tokenize("№47 (м. Слов'янськ)")
    assert test_list == ["№", "47", " ", "(", "м.", " ", "Слов'янськ", ")"]

    test_list = w.tokenize("с.-г.")
    assert test_list == ["с.-г."]

    test_list = w.tokenize("100 грн. в банк")
    assert test_list == ["100", " ", "грн", ".", " ", "в", " ", "банк"]

    test_list = w.tokenize("таке та ін.")
    assert test_list == ["таке", " ", "та", " ", "ін."]

    test_list = w.tokenize("і т. ін.")
    assert test_list == ["і", " ", "т.", " ", "ін."]

    test_list = w.tokenize("і т.д.")
    assert test_list == ["і", " ", "т.", "д."]

    test_list = w.tokenize("в т. ч.")
    assert test_list == ["в", " ", "т.", " ", "ч."]

    test_list = w.tokenize("до т. зв. сальону")
    assert test_list == ["до", " ", "т.", " ", "зв.", " ", "сальону"]

    test_list = w.tokenize("(т. зв. сальон)")
    assert test_list == ["(", "т.", " ", "зв.", " ", "сальон", ")"]

    test_list = w.tokenize(" і под.")
    assert test_list == [" ", "і", " ", "под."]

    test_list = w.tokenize("Інститут ім. акад. Вернадського.")
    assert test_list == ["Інститут", " ", "ім.", " ", "акад.", " ", "Вернадського", "."]

    test_list = w.tokenize("Палац ім. гетьмана Скоропадського.")
    assert test_list == ["Палац", " ", "ім.", " ", "гетьмана", " ", "Скоропадського", "."]

    test_list = w.tokenize("від лат. momento")
    assert test_list == ["від", " ", "лат.", " ", "momento"]

    test_list = w.tokenize("отримав рос. орден")
    assert test_list == ["отримав", " ", "рос.", " ", "орден"]

    test_list = w.tokenize("на 1-кімн. кв. в центрі")
    assert test_list == ["на", " ", "1-кімн.", " ", "кв.", " ", "в", " ", "центрі"]

    test_list = w.tokenize("1 кв. км.")
    assert test_list == ["1", " ", "кв.", " ", "км", "."]

    test_list = w.tokenize("Валерій (міліціонер-пародист.\n–  Авт.) стане пародистом.")
    assert test_list == ["Валерій", " ", "(", "міліціонер-пародист", ".", "\n", "–", " ", " ", "Авт.", ")", " ", "стане", " ", "пародистом", "."]

    test_list = w.tokenize("Сьогодні (у четвер.  — Ред.), вранці.")
    assert test_list == ["Сьогодні", " ", "(", "у", " ", "четвер", ".", " ", " ", "—", " ", "Ред.", ")", ",", " ", "вранці", "."]

    test_list = w.tokenize("Fair trade [«Справедлива торгівля». –    Авт.], який стежить за тим, щоб у країнах")
    assert "Авт." in test_list, test_list

    test_list = w.tokenize("яку авт. устиг")
    assert test_list == ["яку", " ", "авт.", " ", "устиг"]

    test_list = w.tokenize("пише ред. Бойків")
    assert test_list == ["пише", " ", "ред.", " ", "Бойків"]

    test_list = w.tokenize("диво з див.")
    assert test_list == ["диво", " ", "з", " ", "див", "."]

    test_list = w.tokenize("диво з див...")
    assert test_list == ["диво", " ", "з", " ", "див", "..."]

    test_list = w.tokenize("тел.: 044-425-20-63")
    assert test_list == ["тел.", ":", " ", "044-425-20-63"]

    test_list = w.tokenize("с/г")
    assert test_list == ["с/г"]

    test_list = w.tokenize("ім.Василя")
    assert test_list == ["ім.", "Василя"]

    test_list = w.tokenize("ст.231")
    assert test_list == ["ст.", "231"]

    test_list = w.tokenize("2016-2017рр.")
    assert test_list == ["2016-2017", "рр."]

    test_list = w.tokenize("30.04.2010р.")
    assert test_list == ["30.04.2010", "р."]

    test_list = w.tokenize("ні могили 6в. ")
    assert test_list == ["ні", " ", "могили", " ", "6в", ".", " "]

    test_list = w.tokenize("в... одягненому")
    assert test_list == ["в", "...", " ", "одягненому"]

    # invaild but happens
    test_list = w.tokenize("10 млн. чоловік")
    assert test_list == ["10", " ", "млн.", " ", "чоловік"]

    test_list = w.tokenize("від Таврійської губ.5")
    assert test_list == ["від", " ", "Таврійської", " ", "губ.", "5"]

    test_list = w.tokenize("від червоних губ.")
    assert test_list == ["від", " ", "червоних", " ", "губ", "."]

    test_list = w.tokenize("К.-Святошинський")
    assert test_list == ["К.-Святошинський"]

    test_list = w.tokenize("К.-Г. Руффман")
    assert test_list == ["К.-Г.", " ", "Руффман"]

    test_list = w.tokenize("Рис. 10")
    assert test_list == ["Рис.", " ", "10"]

    test_list = w.tokenize("худ. фільм")
    assert test_list == ["худ.", " ", "фільм"]

    # нар. - complicated

    test_list = w.tokenize("рік нар. невідомий")
    assert test_list == ["рік", " ", "нар.", " ", "невідомий"]

    test_list = w.tokenize("нар. 1945")
    assert test_list == ["нар.", " ", "1945"]

    test_list = w.tokenize("(1995 р. нар.)")
    assert test_list == ["(", "1995", " ", "р.", " ", "нар.", ")"]

    test_list = w.tokenize("нар. бл. 1720")
    assert test_list == ["нар.", " ", "бл.", " ", "1720"]

    test_list = w.tokenize("(нар. у серпні 1904)")
    assert test_list == ["(", "нар.", " ", "у", " ", "серпні", " ", "1904", ")"]

    test_list = w.tokenize("977 — нар. Кріс Мартін")
    assert test_list == ["977", " ", "—", " ", "нар.", " ", "Кріс", " ", "Мартін"]

    test_list = w.tokenize("Ради нар. депутатів")
    assert test_list == ["Ради", " ", "нар.", " ", "депутатів"]

    test_list = w.tokenize("нар. арт.")
    assert test_list == ["нар.", " ", "арт", "."]

    test_list = w.tokenize("біля нар. Сумно")
    assert test_list == ["біля", " ", "нар", ".", " ", "Сумно"]

    test_list = w.tokenize("- Вибори-2019")
    assert test_list == ["-", " ", "Вибори-2019"]

    test_list = w.tokenize("порівн. з англ")
    assert test_list == ["порівн.", " ", "з", " ", "англ"]

    # not too frequent
    #    test_list = w.tokenize("30.04.10р.");
    #    assertEquals(Arrays.asList("30.04.10", "р."), test_list);

    test_list = w.tokenize("поч. 1945 - кін. 1946")
    assert test_list == ["поч.", " ", "1945", " ", "-", " ", "кін.", " ", "1946"]

    test_list = w.tokenize("Поч. XX ст.")
    assert test_list == ["Поч.", " ", "XX", " ", "ст."]

    test_list = w.tokenize("Чигиринський пов. Такої губернії")
    assert test_list == ["Чигиринський", " ", "пов.", " ", "Такої", " ", "губернії"]

    test_list = w.tokenize("Чигиринський пов.")
    assert test_list == ["Чигиринський", " ", "пов."]

    test_list = w.tokenize("З пов. Горобець")
    assert test_list == ["З", " ", "пов.", " ", "Горобець"]

    test_list = w.tokenize("пом. 1994")
    assert test_list == ["пом.", " ", "1994"]

    test_list = w.tokenize("щиколоток. с. жел")
    assert test_list == ["щиколоток", ".", " ", "с.", " ", "жел"]

    test_list = w.tokenize("2-ге вид.,")
    assert test_list == ["2-ге", " ", "вид.", ","]

    test_list = w.tokenize("наук.-метод.")
    assert test_list == ["наук.-метод."]

def test_brackets():
    # скорочення
    test_list = w.tokenize("д[окто]р[ом]")
    assert test_list == ["д[окто]р[ом]"]

def test_apostrophe():
    test_list = w.tokenize("’продукти харчування’")
    assert test_list == ["'", "продукти", " ", "харчування", "'"]

    test_list = w.tokenize("схема 'гроші'")
    assert test_list == ["схема", " ", "'", "гроші", "'"]

    test_list = w.tokenize("(‘дзеркало’)")
    assert test_list == ["(", "'", "дзеркало", "'", ")"]

    test_list = w.tokenize("все 'дно піду")
    assert test_list == ["все", " ", "'дно", " ", "піду"]

    test_list = w.tokenize("трохи 'дно 'дному сказано")
    assert test_list == ["трохи", " ", "'дно", " ", "'дному", " ", "сказано"]

    test_list = w.tokenize("а мо',")
    assert test_list == ["а", " ", "мо'", ","]

    test_list = w.tokenize("підемо'")
    assert test_list == ["підемо", "'"]

    test_list = w.tokenize("ЗДОРОВ’Я.")
    assert test_list == ["ЗДОРОВ'Я", "."]

    test_list = w.tokenize("''український''")
    assert test_list == ["''", "український", "''"]

    # 'тсе, 'ддати  'го

    test_list = w.tokenize("'є")
    assert test_list == ["'", "є"]

    test_list = w.tokenize("'(є)")
    assert test_list == ["'", "(", "є", ")"]


def test_dash():
    test_list = w.tokenize("Кан’-Ка Но Рей")
    assert test_list == ["Кан'-Ка", " ", "Но", " ", "Рей"]

    test_list = w.tokenize("і екс-«депутат» вибув")
    assert test_list == ["і", " ", "екс-«депутат»", " ", "вибув"]

    test_list = w.tokenize("тих \"200\"-х багато")
    assert test_list == ["тих", " ", "\"200\"-х", " ", "багато"]

    test_list = w.tokenize("«діди»-українці")
    assert test_list == ["«діди»-українці"]

    #    test_list = w.tokenize("«краб»-переросток");
    #    assertEquals(Arrays.asList("«", "краб", "»", "-", "переросток"), test_list);

    test_list = w.tokenize("вересні--жовтні")
    assert test_list == ["вересні", "--", "жовтні"]

    test_list = w.tokenize("—У певному")
    assert test_list == ["—", "У", " ", "певному"]

    test_list = w.tokenize("-У певному")
    assert test_list == ["-", "У", " ", "певному"]

    test_list = w.tokenize("праця—голова")
    assert test_list == ["праця", "—", "голова"]

    test_list = w.tokenize("Людина—")
    assert test_list == ["Людина", "—"]

    test_list = w.tokenize("Х–ХІ")
    assert test_list == ["Х", "–", "ХІ"]

    test_list = w.tokenize("VII-VIII")
    assert test_list == ["VII", "-", "VIII"]

    test_list = w.tokenize("Стрий– ")
    assert test_list == ["Стрий", "–", " "]

    test_list = w.tokenize("фіто– та термотерапії")
    assert test_list == ["фіто–", " ", "та", " ", "термотерапії"]

    test_list = w.tokenize(" –Виділено")
    assert test_list == [" ", "–", "Виділено"]

    test_list = w.tokenize("так,\u2013так")
    assert test_list == ["так", ",", "\u2013", "так"]

def test_special_chars():
    text = "РЕАЛІЗАЦІЇ \u00AD\n" + "СІЛЬСЬКОГОСПОДАРСЬКОЇ"

    test_list = [s.replace("\n", "\\n").replace("\u00AD", "\\xAD") for s in w.tokenize(text)]
    assert test_list == ["РЕАЛІЗАЦІЇ", " ", "\\xAD", "\\n", "СІЛЬСЬКОГОСПОДАРСЬКОЇ"]

    test_list = w.tokenize("а%його")
    assert test_list == ["а", "%", "його"]

    test_list = w.tokenize("5%-го")
    assert test_list == ["5%-го"]

    test_list = w.tokenize("5′")  # U+2032
    assert test_list == ["5", "′"]

    test_list = w.tokenize("'⚪'")  # U+26AA + U+FE0F
    assert test_list == ["'", "⚪", "'"]

def test_tokenize_markdown():
    txt = "_60-річний_"
    test_list = w.tokenize(txt)
    assert test_list == ["_", "60-річний", "_"]

    txt = "**25 жінок України:**"
    test_list = w.tokenize(txt)
    assert test_list == ["**", "25", " ", "жінок", " ", "України", ":", "**"]

    test_list = w.tokenize("Веретениця**")
    assert test_list == ["Веретениця", "**"]

    test_list = w.tokenize("мові***,")
    assert test_list == ["мові", "***", ","]

    test_list = w.tokenize("*Оренбург")
    assert test_list == ["*", "Оренбург"]

    test_list = w.tokenize("з*ясував")
    assert test_list == ["з*ясував"]

    test_list = w.tokenize("#робота_редактора")
    assert test_list == ["#робота_редактора"]

    test_list = w.tokenize("https://uk.wikipedia.org/wiki/Список_аеропортів_України")
    assert test_list == ["https://uk.wikipedia.org/wiki/Список_аеропортів_України"]

    txt = "ОСОБА_5"
    test_list = w.tokenize(txt)
    assert test_list == [txt]

def test_tokenize_web_entities():
    #        "Київ.proUA.com",
    entities = ["Паляниця.Інфо", "Житомир.info", "Жмеринка.City", "Ліга.Life", "ЛІГА.net", "Точка.net", "Цензор.НЕТ", "Гайдамака.UA", "Тиждень.ua", "Срана.юа", "Рагу.лі", "МК.ru", "Лента.Ру", "Слух.media", "Олігарх.com", "блогер.фм", "ЗМІ.ck.ua", "Закарпаття.depo.ua"]

    for e in entities:
        test_list = w.tokenize(e)
        assert test_list == [e]

