"""Port of org.languagetool.rules.uk.TokenAgreementNounVerbRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import SENTENCE_START_TAGNAME, AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.lang.uk.agreement_noun_verb import TokenAgreementNounVerbRule
from langtool.messages import messages_for
from uk_rule_test_base import RuleTestBase


GOOD_TEXT = ("Хоча упродовж десятиліть ширилися численні історії про те, що я був у ряду наступників трону Тембу, щойно наведений простий генеалогічний екскурс викриває міфічність таких тверджень."
             " Я був членом королівської родини, проте не належав до небагатьох привілейованих, що їх виховували на правителів."
             " Натомість мене як нащадка Лівого дому навчали — так само, як і раніше мого батька — бути радником правителів племені."
             " Мій батько був високим темношкірим чоловіком із прямою й величною поставою, яку я, хочеться думати, успадкував."
             " У батька було пасмо білого волосся якраз над чолом, і хлопчиком я бувало брав сірий попіл і втирав його у своє волосся, щоб воно було таке саме, як у тата."
             " Батько мій мав сувору вдачу й не шкодував різки, виховуючи дітей. Він міг бути дивовижно впертим, і це ще одна риса, яка, на жаль, теж могла перейти від батька до сина."
             " Мого батька інколи називали прем’єр-міністром Тембуленду за врядування Далінд’єбо, батька Сабати, який правив на початку 1900-х років, та його сина й наступника Джонгінтаба."
             " Насправді ж такого титулу не існувало, але мій батько справді відіграв роль, яка не надто відрізнялася від функції прем’єра."
             " Як шанований і високо цінований радник обох королів, він супроводжував їх у подорожах і зазвичай перебував поруч із ними на важливих зустрічах із урядовими чиновниками."
             " Він був також визнаним хоронителем історії коса, і частково через це його порадами так дорожили. Моє власне зацікавлення історією прокинулося рано, і батько його підживлював."
             " Він не вмів ні читати, ні писати, але мав репутацію чудового оратора, який захоплював слухачів, розважаючи й водночас повчаючи їх.")


class TestTokenAgreementNounVerbRule(RuleTestBase):

    @pytest.fixture(autouse=True)
    def set_up(self):
        require_dictionaries('uk')
        self.rule = TokenAgreementNounVerbRule(messages_for('uk'))

    def test_rule(self):

        self.assert_has_error("Тарас прибігла")
        self.assert_has_error("вони прибіг")
        self.assert_has_error("я прибіжиш")

        self.assert_has_error("вони швидко прибіг")

        self.assert_has_error("та з інших питань перевірка проведено не повно")

        self.assert_has_error("з часом пара вирішили узаконити")

        self.assert_has_error("як вони поводиться")
        self.assert_empty_match("таким як я радять")
        self.assert_empty_match("я не так само як ви думаю")

        self.assert_empty_match("На честь Джудіт Резнік названо кратер")

        #TODO:
        #    self.assert_empty_match("подружжя під прізвищем Крилови оселилося в Москві");

        # inf
        self.assert_empty_match("чи зуміє наша держава забезпечити власні потреби")
        self.assert_empty_match("так навчила мене бабуся місити пухке дріжджове тісто")
        self.assert_empty_match("чи можуть російськомовні громадяни вважатися українцями")

        # predic + inf
        self.assert_empty_match("не шкода віддати життя")
        self.assert_empty_match("не шкода було віддати життя")

        # correct sentences:
        self.assert_empty_match("чоловік прибіг")
        self.assert_empty_match("я прибіг")
        self.assert_empty_match("я прибігла")

        self.assert_empty_match("кандидат в президенти поїхав")
        self.assert_empty_match("кандидат в народні депутати поїхав")

        # handled by styling rule
        #  self.assert_has_error("40 тисяч чоловік виявили бажання");
        self.assert_empty_match("40 тисяч чоловік виявили бажання")

        # було + impers
        self.assert_empty_match("клан Алькапоне було знищено")

        # було + verb:past
        self.assert_empty_match("він було вмовк")
        self.assert_empty_match("тобто Угорщина було пішла шляхом")
        self.assert_empty_match("він було трохи скис")

        # ніж + v_naz
        self.assert_empty_match("більше ніж будь-хто маємо повне право")

        self.assert_empty_match("а вона візьми і зроби")

        self.assert_empty_match("Збережені Я позбудуться необхідності")

        # geo qualifier
        self.assert_empty_match("У місті Біла Церква було сформовано")
        self.assert_has_error("із містом юності Ви очікувала")

        # unknown name
        self.assert_empty_match("Андрій Качала")
        self.assert_empty_match("Любов Євтушок зауважила")

        self.assert_empty_match("а він давай пити горілку")

        self.assert_empty_match("Тарас ЗАКУСИЛО")

        self.assert_empty_match("не сила була йти далі")

        # пора було
        self.assert_empty_match("Вже давно пора було Мовчану відійти від керма.")

        # як
        self.assert_empty_match("тому, що як австрієць маєте")

        # TODO: would hide good occasions, Тунець тут inanim:v_zna
        #    self.assert_empty_match("Тунець розморозьте і поріжте на порційні частинки.");

        self.assert_has_error("не встиг вона отямитися")

        self.assert_empty_match("про припинення їхньої діяльності ми ухвалити, зрозуміло, не могли")
        #TODO: ignore insert words
        #    self.assert_empty_match("Почав, значить, я рости.");

        self.assert_has_error("Ми може спробувати знайти")

        self.assert_empty_match(GOOD_TEXT)

        self.assert_empty_match("— це були невільники")

        self.assert_has_error("щоб конкуренти підішли до виборів")

    def test_rule_ne(self):
        self.assert_has_error("Тарас не прибігла")
        self.assert_has_error("Тарас би не прибігла")
        self.assert_has_error("вони не прибіг")
        self.assert_has_error("я не прибіжиш")

        self.assert_empty_match("ні він, ні вона не хотіли")
        self.assert_empty_match("уряд та поліція не контролюють події")
        self.assert_empty_match("— це не була хвороба")
        self.assert_empty_match("— це не передбачено")
        self.assert_empty_match("Решта не мають жодних дозволів")
        self.assert_empty_match("ні лауреат, ні його жінка не розмовляють жодними мовами")
        self.assert_empty_match("Чи ж могла я не повернутися назад?")
        self.assert_empty_match("кефаль, хамса не затримуються")
        self.assert_has_error("інша мова, вона примітивізовано й")
        self.assert_empty_match("душ, одеколони, навіть хлорка не допомогли")
        self.assert_empty_match("і Виговський, ні навіть Мазепа не розглядали")
        self.assert_empty_match("уряд та поліція не контролюють")
        self.assert_empty_match("кадрове забезпечення, матеріальна база не дісталися")

        self.assert_empty_match("Волосожар/Морозов не припинили")
        self.assert_empty_match("ні Європа, ні тим більше Україна не мають")

    def test_proper_names(self):

        # posessive insert
        self.assert_empty_match("Конституційний суд Республіки Молдова визнав румунську державною")
        #    self.assert_empty_match("Творіння братів Люм’єр знало.");
        self.assert_empty_match("Мешканці планети Земля споживають щороку")
        self.assert_empty_match("жителі селища Новобудова зверталися.")

        self.assert_has_error("при своїх дружинах Крішна не роздягалася і одразу...")


        self.assert_empty_match("всі українські жінки з ім’ям Марія мають знати")
        self.assert_empty_match("а ім’я Франклін згадують не досить часто")
        self.assert_empty_match("шимпанзе на прізвисько Чита зіграли 16 «акторів»")

        # proper name insert
        self.assert_empty_match("лижний курорт Криниця розташувався в Бескидах")
        self.assert_empty_match("містечко Баришівка потрапило до історії")

        self.assert_empty_match("У місті Ліда незабаром мають встановити")

        # proper name passive place
        self.assert_empty_match("ми в державі Україна маємо такі підстави")
        self.assert_empty_match("У литовський порт Клайпеда прибуло плавуче сховище")
        self.assert_empty_match("на австралійський штат Вікторія налетів сильний шторм")
        self.assert_empty_match("в селі Червона Слобода було вирішено перейменувати")
        self.assert_empty_match("Хоча б межі курорту Східниця визначено?")
        self.assert_empty_match("комітет порятунку села Оляниця вирішив")
        self.assert_empty_match("колишній кандидат у губернатори штату Аризона їхав до Чернівців")
        self.assert_empty_match("У невизнаній республіці Південна Осетія відбулися вибори")
        self.assert_empty_match("Рибалки італійського острова Лампедуза заблокували")
        self.assert_empty_match("у латвійське курортне містечко Юрмала з’їхався весь бомонд")
        self.assert_empty_match("Суд американського штату Каліфорнія присудив акторці")
        self.assert_empty_match("У штатах Техас і Луїзіана запроваджено надзвичайний стан")

        self.assert_empty_match("на прізвисько Михайло відбулася")

        self.assert_has_error("Вистава зроблено чесно, професійно.")

        #TODO: next 2 fall into common exceptions
        #    self.assert_has_error("свою першу залікову вагу в поштовху Надія зафіксували лише (!) в третій спробі");
        #    self.assert_has_error("по втягуванні України в європейську орбіту Швеція усвідомлюють факт");



    def test_noun_as_adv(self):
        self.assert_empty_match("під три чорти пертися")

    def test_pron(self):
        self.assert_has_error("яка прибіг")
        self.assert_has_error("яка не мають паспортів")
        self.assert_has_error("яка не залежать від волі")
        self.assert_has_error("яка було нещодавно опубліковано")
        #    self.assert_has_error("хто прийшла");
        #    self.assert_has_error("одна інший радила");
        self.assert_empty_match("вони як ніхто інший знали")

        self.assert_empty_match("який прибила хвиля")
        self.assert_empty_match("Ті, хто зрозуміли")
        self.assert_empty_match("ті, хто сповідує")
        self.assert_empty_match("ті, хто не сповідують")
        self.assert_empty_match("Ті, хто просто зрозуміли")
        self.assert_empty_match("всі хто зрозуміли")  # пропущена кома
        self.assert_empty_match("про те, хто була ця клята Пандора")

        self.assert_empty_match("що можна було й інший пошукати")

    def test_verb_inf(self):
        # modal verb + noun + verb:inf
        self.assert_empty_match("не встиг я отямитися")
        self.assert_empty_match("що я зробити встиг")
        self.assert_empty_match("це я робити швидко вмію")
        self.assert_empty_match("Саудівську Аравію ми проходити зобов’язані")
        self.assert_has_error("я бігати")
        #    self.assert_has_error("машина бігати");

        self.assert_empty_match("ми воювати з нашими людьми не збираємося")

        # noun + inf + не + verb/adj:rv_inf
        self.assert_empty_match("що ми зробити не зможемо")
        self.assert_empty_match("Я уявити себе не можу без нашої програми.")
        self.assert_empty_match("ми розраховувати не повинні")
        self.assert_empty_match("Хотів би я подивитися")
        self.assert_empty_match("на останніх ми працювати не згідні")
        self.assert_has_error("на останніх ми працювати не питаючи нікого")
        self.assert_empty_match("те, чого я слухати не дуже хочу")
        self.assert_empty_match("чи гідні ми бути незалежними")
        self.assert_empty_match("Чи здатен її автор навести хоча б один факт")

        # rv_inf
        self.assert_empty_match("чи готові ми сидіти без світла")
        self.assert_empty_match("Чи повинен я просити")

        self.assert_empty_match("ніхто робити цього не буде")
        self.assert_empty_match("ніхто знижувати тарифи на газ, зрозуміло, не збирається")
        #TODO:
        #    self.assert_empty_match("Іноземець в’їздити і виїздити з цієї країни може тільки");

        self.assert_has_error("Та припинити ти переживати")

        self.assert_empty_match("та я купувати цю куртку не дуже хотіла")

        self.assert_empty_match("Правоохоронці зняти провокаційний стяг не змогли, оскільки")

        # ignore quotes
        self.assert_empty_match("Однак Банкова виконувати приписи Закону \"Про очищення влади\" не поспішає")

        self.assert_empty_match("Хтось намагається її торкнутися, хтось сфотографувати.")

        self.assert_empty_match("Ми не проти сплачувати податки")

    def test_plural(self):
        self.assert_has_error("21 гравець дивилися")
        self.assert_has_error("один гравець дивилися")
        self.assert_has_error("Серед вбитих і полонених радянських солдат були чоловіки")
        self.assert_has_error("Пригадую випадок, коли одна аудіокомпанія звернулися до провідних київських «ефемок»")
        self.assert_has_error("підписку про невиїзд двох молодиків, яких міліція затримали першими")
        self.assert_has_error("рук та ніг Параски, темниця розчинилася і дівчина опинилися за стінами фортеці")
        self.assert_has_error("його арештували і вислали у Воркуту, я залишилися одна з дитиною.")
        self.assert_has_error("На проспекті Чорновола, ближче до центру, вона зупинилися на перехресті")
        self.assert_has_error("порадилися і громада запропонували мені зайняти його місце")
        self.assert_has_error("то й небо вона бачите саме таким")
        self.assert_has_error("молочного туману, потім вона заснувалися")
        self.assert_has_error("Наташа смикала за волосся, а Софія намагалися бризнути")

        self.assert_empty_match("моя мама й сестра мешкали")
        self.assert_empty_match("чи то Вальтер, чи я вжили фразу")
        self.assert_empty_match("То вона, то Гриць виринають перед її душею")
        self.assert_empty_match("Кожен чоловік і кожна жінка мають")
        self.assert_empty_match("каналізація і навіть охорона пропонувалися")
        self.assert_empty_match("Кавказ загалом і Чечня зокрема лишаться")
        self.assert_empty_match("Європейський Союз і моя рідна дочка переживуть це збурення")
        self.assert_empty_match("Бразилія, Мексика, Індія збувають")
        self.assert_empty_match("Банкова й особисто президент дістали")
        self.assert_empty_match("українська мода та взагалі українська культура впливають")
        self.assert_empty_match("Тато і Юзь Федорків були прикладом")
        self.assert_empty_match("Клочкова ти Лисогор перемагають на своїх дистанціях")
        self.assert_empty_match("він особисто й облдержадміністрація винесли")
        self.assert_empty_match("тисяча й одна ознака вказують")

        self.assert_empty_match("і “більшовики”, і Президент звинуватили опозицію у зриві")
        self.assert_empty_match("І “швидка“, і міліція приїхали майже вчасно")
        self.assert_empty_match("І уряд, і президент позитивно оцінюють")

        self.assert_empty_match("Андрій Ярмоленко, Євген Коноплянка, Ярослав Ракицький допомогли вітчизняній «молодіжці»")
        #TODO: unknown proper nouns
        self.assert_empty_match("Мустафа Джемілєв, Рефат Чубаров зможуть")
        self.assert_empty_match("Єжи Тур, Александр Рибіцький перебороли")

        self.assert_empty_match("27-річний водій та 54-річна пасажирка були травмовані")
        self.assert_empty_match("фізична робота та щоденна 30–хвилинна фіззарядка приносять")

        self.assert_empty_match("Б. Єльцин і Л. Кучма погодилися вважати Азовське море внутрішнім морем")

        # unknown proper nouns
        self.assert_empty_match("Ґорбачов і його дружина виглядали")
        self.assert_empty_match("і Ципкалов, і Кисельов могли одразу")
        self.assert_empty_match("«Самопоміч» та Радикальна партія дали більшість голосів")

        # multiple adj + noun
        #TODO:
        #  self.assert_empty_match("Бережна й «мирна» тусовка перебувають");
        # TODO: can't easily detect special case with погода
        #    self.assert_has_error("Цього року дощова та холодна погода стояли практично в усіх регіонах");


        self.assert_empty_match("Канада, Австралія та й Західна Європа знають")
        self.assert_empty_match("процес формування уряду та його відставка залежать")
        self.assert_empty_match("Усі розписи, а також архітектура відрізняються")
        self.assert_empty_match("Німеччина (ще демократична) та Росія почали «дружити»")
        self.assert_empty_match("Як Україна, так і Німеччина відчувають")
        self.assert_empty_match("обласної ради, а й уся львівська громада виявилися обманутими")
        self.assert_empty_match("Авіація ж і космонавтика справили на розвиток науки")


        #TODO: conj + adv + conj
        self.assert_empty_match("І спочатку Білорусь, а тепер і Україна пішли")
        self.assert_empty_match("Саме тоді Англія, а невдовзі й уся Європа дізналися")
        self.assert_empty_match("але концепція, а потім і програма мають бути")

        self.assert_empty_match("Низка трагедій, а потім громадянська війна вигубили чимало люду")
        #TODO:
        #    self.assert_empty_match("допомога з безробіття, а згодом – невелика зарплатня покриють витрати на ліки.");

        #TODO: inserts
        #    self.assert_empty_match("для яких культура, а отже, і культурна дипломатія належать");
        #    self.assert_empty_match("Франція, Китай і, певною мірою, Росія зуміли поставити");
        self.assert_empty_match("Наша родина, я особисто і наша політична сила займаємося благодійністю")
        self.assert_empty_match("і держава, і, відповідно, посада перестали існувати")

        #  self.assert_empty_match("українка й на півтора роки молодша кубинка ведуть");

        #    self.assert_empty_match("Революція 1917-го і націоналізація стали стресом, але глобально на підприємстві нічого не змінили.");

        # noun:v_naz noun:v_rod
        #TODO: conflicts with test below
        #  self.assert_has_error("Згідно розуміння класиків, народна мова надавалися лише для творів");
        self.assert_empty_match("Швидке заселення земель, вирубування лісів, меліорація призвели")
        self.assert_empty_match("узагалі, почуття гумору, іронія були притаманні")
        self.assert_empty_match("почуття гумору, іронія були притаманні")
        self.assert_empty_match("оскільки назва фільму, прізвище режисера, країна будуть викарбувані на бронзовій плиті")
        self.assert_empty_match("Дух Києва, його атмосфера складаються")
        self.assert_empty_match("Верховний суд, Рада суддів, Кваліфікаційна комісія могли б перевірити")
        self.assert_empty_match("зеленкуваті плями моху, сіро-коричнева бруківка повертають нас на кілька століть назад")
        self.assert_empty_match("водій “Мазди” та її пасажир загинули")
        #    self.assert_empty_match("водій “Жигулів” та його пасажирка померли.");

        #TODO: noun:v_naz noun:v_oru conj
        #    self.assert_empty_match("Біг підтюпцем і швидка ходьба знижують ризик гіпертонії");

        # adj conj adj noun
        self.assert_empty_match("біологічна і ядерна зброя стають товаром")
        self.assert_empty_match("І та й інша група вводили в клітини шкіри")

        #TODO: noun+verb + conj ...
        #    self.assert_empty_match("бажання співати і наполеглива праця допомогли");

        #TODO: ignore quotes and parenthesis
        #    self.assert_empty_match("руки в мозолях та “робоча” засмага підказували");
        #    self.assert_empty_match("Ресурси та (або) політична воля закінчилися 21 лютого.");

        # пара
        #    self.assert_empty_match("зіркова пара Пишняк — Толстой вирішили вивести");
        self.assert_empty_match("матч Туреччина — Україна зіграють")
        self.assert_empty_match("у смузі Піски—Авдіївка оперують")

        # latin/cyr mix
        #  self.assert_empty_match("Дівчата та їхнiй брат належать до касти");

        #    self.assert_empty_match("за яким 50%+1 акція закріплюються у власності держави");
        self.assert_empty_match("злість плюс іронія можуть вбити")
        self.assert_empty_match("із яких 50% плюс одна акція знаходяться")
        self.assert_empty_match("Матеріальна заінтересованість плюс гарна вивіска зіграли злий жарт")

        self.assert_empty_match("Колесніков/Ахметов посилили")

        # plural "semi-numeric"
        self.assert_empty_match("решта забороняються")
        self.assert_empty_match("все решта відійшло на другий план")
        self.assert_empty_match("Більш ніж половина віддали голоси")
        self.assert_empty_match("Левова їхня частка працюють через російських туроператорів")
        self.assert_empty_match("дві групи з трьох осіб кожна виконували просте завдання")

        self.assert_empty_match("Що пачка цигарок, що ковбаса коштують")
        self.assert_empty_match("не вулична злочинність, не корупція відлякували")

        self.assert_empty_match("з Василем Кричевським Оскар Германович разом брали участь")

        # very long
        self.assert_empty_match("Леонід Новохатько й керівник головного управління з питань гуманітарного розвитку адміністрації\n" + "Президента Юрій Богуцький обговорили")
        self.assert_empty_match("інший нардеп та лідер «Правого сектору» Дмитро Ярош просили")

        #    self.assert_empty_match("Квіташвілі, міністр інфраструктури Андрій Пивоварський відкликали");

        #TODO:
        #    self.assert_empty_match("Ні світ, ані навіть Європа чекати не будуть");

        # пара
        self.assert_empty_match("пара Катерина Морозова/Дмитро Алексєєв тріумфувала")

    def test_num(self):
        self.assert_empty_match("понад тисяча отримали поранення")
        self.assert_empty_match("Решта 121 депутат висловилися проти")
        self.assert_empty_match("понад сотня отримали поранення")

        self.assert_has_error("22 льотчики удостоєно")
        self.assert_empty_match("два сини народилося там")
        #TODO:
        #self.assert_empty_match("Троє пілотів і 31 глядач загинули миттєво.");

    def test_masc_fem(self):
        # masc-fem
        self.assert_empty_match("німецький канцлер зателефонувала російському президенту")
        self.assert_empty_match("екс-міністр повторила у телезверненні")
        self.assert_empty_match("Прем’єр-міністр повторила у телезверненні")
        self.assert_empty_match("Прем’єр—міністр повторила у телезверненні")
        self.assert_empty_match("єврокомісар зазначила, що")
        self.assert_empty_match("кінолог пояснила")

        # compound
        self.assert_empty_match("автор-упорядник назвала збірник")

        self.assert_has_error("Прем’єр-міністр повторило у телезверненні")
        self.assert_has_error("приятель повторила у телезверненні")


    def test_ignore_by_intent(self):
        # handled by xml rule
        #  self.assert_has_error("тому що воно привнесено ззовні");
        #  self.assert_has_error("Воно просочено історією");
        self.assert_empty_match("тому що воно привнесено ззовні")
        self.assert_empty_match("Воно просочено історією")
        self.assert_empty_match("Все решта зафіксовано")
        self.assert_empty_match("решта зафіксовано")

        self.assert_empty_match("З охопленого війною Сектора Газа вивезли «більш як 80 громадян України».")

        # має бути «подружжя Обам» - ловиться в xml
        #    self.assert_has_error("подружжя Обама запросило 350 гостей");
        self.assert_empty_match("подружжя Обама запросило 350 гостей")

    def test_over_the_word(self):
        self.assert_empty_match("діагноз дизентерія підтвердився")

        #TODO:
        # self.assert_empty_match("Свого часу породу фокстер’єр вивели");

    def test_case_government(self):
        self.assert_empty_match("коли українцям пора показати")
        self.assert_empty_match("або пропозиція збільшити частку")

    def test_rule_with_adj_or_kly(self):
        self.assert_has_error("Ви постане перед вибором")
        self.assert_has_error("військовий прибігла")
        self.assert_has_error("Фехтувальна збірна було до цього готова")
        self.assert_has_error("наші дівчата виграти загальний залік")
        self.assert_has_error("окремі ентузіасти переймалася")
        self.assert_has_error("угорська влада пообіцяли переглянути")
        self.assert_has_error("точно також ви буде платити")

        self.assert_empty_match("багато хто в драматурги прийшов")
        self.assert_empty_match("з кандидатом у президенти не визначився")
        self.assert_empty_match("Мої співвітчизники терпіти це далі не повинні")
        self.assert_empty_match("Ви може образились")
        self.assert_empty_match("Моя ти зоре в тумані")
        self.assert_empty_match("На кожен покладіть по кільцю")
        self.assert_empty_match("Любителі фотографувати їжу")

    def test_special_chars(self):
        self.assert_empty_match("Тарас при\u00ADбіг.")

        matches = self.rule.match(self.lt.get_analyzed_sentence("Тарас при\u00ADбігла."))
        assert len(matches) == 1

        matches = self.rule.match(self.lt.get_analyzed_sentence("Та\u00ADрас прибігла."))
        assert len(matches) == 1

    def test_rule_disambig_naz_inf(self):
        readings = []

        readings.append(AnalyzedTokenReadings(AnalyzedToken("", SENTENCE_START_TAGNAME, ""), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("намагання", "noun:inanim:p:v_naz", "намагання"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("спам'ятати", "verb:perf:inf", "спам'ятати"), 0))

        sent = AnalyzedSentence(readings)

        assert len(self.rule.match(sent)) == 0

        #    readings.clear();






