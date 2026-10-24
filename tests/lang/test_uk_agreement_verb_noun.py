"""Port of org.languagetool.rules.uk.TokenAgreementVerbNounRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import SENTENCE_START_TAGNAME, AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.lang.uk.agreement_verb_noun import TokenAgreementVerbNounRule
from langtool.messages import messages_for
from uk_rule_test_base import RuleTestBase


def _assert_contains(s, sub):
    assert sub in s


class TestTokenAgreementVerbNounRule(RuleTestBase):

    @pytest.fixture(autouse=True)
    def set_up(self):
        require_dictionaries('uk')
        self.rule = TokenAgreementVerbNounRule(messages_for('uk'), self.lt.language)

    def test_rule_tpsuggestions(self):
        text = "перераховувати причин"
        sent = self.lt.get_analyzed_sentence(text)
        match = self.rule.match(sent)
        assert len(match) == 1
        assert text[match[0].from_pos:match[0].to_pos] == "перераховувати причин"
        assert match[0].suggested_replacements == ["перераховувати причинам", "перераховувати причинами", "перераховувати причини"]

        self.assert_has_error("зазнавати глибоке", "зазнавати глибокого")


    def test_rule_tp(self):

        #    self.assert_has_error("виграло війську");
        self.assert_matches(1, "вибирався Києві", lambda c: _assert_contains(c, "орудний"))
        self.assert_has_error("вповільнятися підлоги")
        self.assert_has_error("вповільнятися дерев'яні підлоги")
        self.assert_has_error("встановити електроні датчики")
        self.assert_has_error("пройтися трьом книгам")
        self.assert_has_error("Існує Західноєвропейській союз")
        self.assert_has_error("почався справжнісінькій абстинентний синдром")
        self.assert_has_error("досягнув піку")
        self.assert_has_error("сягне піку")
        self.assert_has_error("сягнувши піку")
        self.assert_has_error("побачив озброєнні формування")
        self.assert_has_error("втрапили халепу")
        self.assert_has_error("доведено світовім досвідом")
        self.assert_has_error("боятися закордоном")
        self.assert_has_error("з точки зори антилатинської")
        #    self.assert_has_error("поєднатися одне ціле");
        self.assert_has_error("не вірить свої очам")
        #    self.assert_has_error("Якщо вірити складеними львівськими митниками документам");
        self.assert_has_error("зменшити впив країні")
        self.assert_has_error("займатися модернізацію закладів")
        self.assert_has_error("вважать засобами масової інформації")
        self.assert_has_error("вийшли фотку")
        self.assert_has_error("визнання догорів недійсними")
        self.assert_has_error("що купуються нову техніку")
        self.assert_has_error("наживаються дільці")
        self.assert_has_error("зусилля наблизити перемовин")
        self.assert_has_error("витіснено протестувальники")
        self.assert_has_error("фіктивних догорів оренди")
        self.assert_has_error("Крим залишається територію України")
        self.assert_has_error("Навожу відомі слова")
        self.assert_has_error("розвиток рикну житла")
        self.assert_has_error("покращення епідемічного станув країні")
        self.assert_has_error("вчасно приходить всі профілактичні огляди")
        self.assert_has_error("із наймеш благополучної частини")
        self.assert_has_error("почуватиметься вправі")
        self.assert_has_error("важко уявити  країн Балтії")
        #    self.assert_has_error("все залежить нас");
        self.assert_has_error("користується попи том")
        self.assert_has_error("ще більше погрішать ситуацію")
        self.assert_has_error("стався також вибув метану")
        self.assert_has_error("від спати єдиного податку")
        self.assert_has_error("прочитати сааме цю книжку")
        self.assert_has_error("сиплять дуст", "сипати дуст")
        self.assert_has_error("Охочих навчитися цьому ремеслу")
        self.assert_has_error("поступилася португальці")
        self.assert_has_error("прориваються скрізь стару стріху")

        self.assert_has_error("за будь яку ціну")
        self.assert_has_error("також було велика непевність")

        # має бути мелють
        self.assert_has_error("мелять їхні українські папуги")

        # complicated case with понад
        #    self.assert_has_error("зайнявся понад двісті справ");
        self.assert_empty_match("сидять понад міру")
        self.assert_empty_match("стало відомо точну дату")
        self.assert_empty_match("стало видно тільки оранжеві щоки")
        #    self.assert_empty_match("тягнуться понад воду");
        #    self.assert_empty_match("прибуло понад мільйон");

        #TODO:
        #    self.assert_has_error("планується провесні церемонію");
        #    self.assert_has_error("Відчувається, що тримаєте рук на пульсі часу");
        # ADJ + PLURAL
        #      self.assert_empty_match("повинні складати нежирна їжа, білкові продукти");

    def test_rule_with_part(self):
        self.assert_has_error("сягнув би піку", "сягнув би піка")
        self.assert_has_error("це не відбувається не державному рівні")

        self.assert_empty_match("Вінні прощалася й охоронці виводили їх")
        self.assert_empty_match("Але працювати не те щоб складно")
        self.assert_empty_match("не піднявся не те що Київ")
        self.assert_empty_match("не піднявся не те, що Київ")

    def test_rule_tn(self):

        self.assert_empty_match("вкрадено державою")

        self.assert_empty_match("я буду каву")

        # case govt

        self.assert_empty_match("спроєктувати проект")
        self.assert_empty_match("купив книгу")
        self.assert_empty_match("позбавляло людину")
        self.assert_empty_match("залишати межі")
        self.assert_empty_match("залишаються джерелом")
        self.assert_empty_match("відкидати атрибути")

        self.assert_empty_match("належати людині")
        self.assert_empty_match("належати руку")
        self.assert_empty_match("забракло вмінь")
        self.assert_empty_match("Може поменшати ентузіазму")
        self.assert_empty_match("Може видатися парадоксальним твердження")

        self.assert_empty_match("розподілятиметься пропорційно вкладеній праці")
        self.assert_empty_match("зростатимуть прямо пропорційно україноненависництву")

        self.assert_empty_match("рухатися далі власної історії")

        # impr + oru
        self.assert_empty_match("запропоновано урядом")

        # disambig
        self.assert_empty_match("мало часу")
        self.assert_empty_match("з’явитися перед ним")

        # exceptions
        self.assert_empty_match("не було меблів")
        #    self.assert_empty_match("не можуть укладати угоди");

        self.assert_empty_match("оплачуватися повинна відповідно")

        self.assert_empty_match("відрізнятись один від одного")
        self.assert_empty_match("співпрацювати один із одним")
        self.assert_empty_match("допомагати одне одному")

        # prep + numr
        self.assert_empty_match("залучити інвестицій на 20—30 мільйонів")
        self.assert_empty_match("збереться людей зо 200")

        # question
        self.assert_empty_match("як боротися підприємцям")

        # rv_inf
        self.assert_empty_match("захиститися неспроможні")

        # insert
        self.assert_empty_match("висміювати такого роду забобони")
        self.assert_empty_match("вважається свого роду психологічним")
        self.assert_empty_match("хто мітингуватиме таким чином")
        self.assert_empty_match("уникнувши тим самим")

        # 2nd verb
        self.assert_empty_match("міг хитрістю змусити")
        self.assert_empty_match("могли займатися структури")
        self.assert_empty_match("могли б займатися структури")

        self.assert_empty_match("мусить чимось перекрити")
        self.assert_empty_match("довелося її розбирати")

        self.assert_empty_match("повинні існувати такі")
        self.assert_empty_match("робити здатна")

        # :n: + numr
        self.assert_empty_match("боротиметься кілька однопартійців")

        self.assert_empty_match("вийшла 1987-го")

        # його
        self.assert_empty_match("зігріває його серце")

        # should have comma?
        #    self.assert_empty_match("прокидайся країно");
        self.assert_empty_match("дай Боже")
        self.assert_empty_match("спробуймо йому відповісти")
        self.assert_empty_match("прокинься Тарасе")

        # abbr
        self.assert_empty_match("див. новинні")

        self.assert_empty_match("повинен відбудватися процес")
        # вірити одне одному

        # нікому
        self.assert_empty_match("виявилося нікому не потрібним")

        # самому
        self.assert_empty_match("покататися самому")

        # compound
        self.assert_empty_match("віддати-відрізати Донбас")

        #    self.assert_empty_match("серйозно каже Вадо");

        # називатися + н.в.
        self.assert_empty_match("вона називалася Оперативний злам")
        self.assert_empty_match("мене звати Ігор")

        self.assert_empty_match("підклали дров")

        # femin
        self.assert_empty_match("наголосила політик")

        self.assert_empty_match("тривав довгих десять раундів")

        self.assert_empty_match("лежали всю дорогу")
        self.assert_empty_match("мріяли все життя")

        # v:n + inf
        self.assert_empty_match("сподобалося гуляти")
        self.assert_empty_match("належить пройтися")

        # color
        self.assert_empty_match("стали каламутного кольору")

        self.assert_empty_match("ні сіло ні впало Комітет держбезпеки")

        self.assert_empty_match("звичайна, якщо не сказати слабка, людина")

        self.assert_empty_match("займаючись кожен своїми справами")

        self.assert_empty_match("підстрахуватися не зайве")

        self.assert_empty_match("поназбиравши купу обіцянок")

        self.assert_empty_match("пішов світ за очі")
        self.assert_empty_match("тікати куди очі бачать")

        self.assert_empty_match("Видно було також великий")
        self.assert_empty_match("буде видно тільки супутники")
        self.assert_empty_match("чути було лише стукіт")
        self.assert_empty_match("було дуже чутно стукіт")

        # homonym: adj/verb
        self.assert_empty_match("зеленій частині")

        self.assert_empty_match("будь то буряки чи малина")
        self.assert_empty_match("поліклініці не було де амбулаторні")
        self.assert_empty_match("чесніше було б державний фонд")

        self.assert_empty_match("Процвітати буде лише бізнес")

        # special case gov for бути і мати
        self.assert_empty_match("були б іншої думки")
        self.assert_empty_match("має своїм неодмінним наслідком")
        self.assert_empty_match("що є сил")

        self.assert_empty_match("Конкурс був десь шість")

        self.assert_empty_match("глузували тим більше, чим")

        # ADJ + бути + v_rod
        self.assert_empty_match("повна була образів")
        # IMPERS + бути + N
        self.assert_empty_match("відкрито було журнал")

        self.assert_empty_match("треба буде ще склянку")

        self.assert_empty_match("на Ролан Гаррос")

    def test_rule_tn_vdav(self):
        # rv_dav ??
        self.assert_empty_match("Не бачити вам цирку")

        self.assert_empty_match("розсміявся йому в обличчя")
        self.assert_empty_match("закружляли мені десь у тьмі")
        self.assert_empty_match("ірже вам у вічі")
        self.assert_empty_match("умоститися господареві на рамена")
        self.assert_empty_match("прилетів йому від посла")
        self.assert_empty_match("пробирається людині під шкіру")
        self.assert_empty_match("їхав їй назустріч")
        self.assert_empty_match("біжать йому навперейми")
        self.assert_has_error("Фабрика Миколая вперше запрацювала Львові у 2001 році")

        self.assert_empty_match("Квапитися їй нікуди")
        self.assert_empty_match("хворіти їй ніколи")
        self.assert_empty_match("Жити родині нема де.")
        self.assert_empty_match("Евакуюватися нам не було куди")

        self.assert_empty_match("нічим пишатися жителям")
        self.assert_empty_match("куди подітися селянам")

        self.assert_empty_match("у таких будиночках жити мешканцям")
        self.assert_empty_match("як тепер жити нам")
        self.assert_empty_match("сидіти б панові")

        self.assert_empty_match("не було де амбулаторні карточки ставити")

        #TODO:
        #    self.assert_has_error("не вчить нічому поганому");
        #    self.assert_empty_match("у разі неможливості зібратися і працювати Верховній Раді");

    def test_rule_tn_v_n_vinf(self):
        self.assert_empty_match("маю тобі щось підказати")
        self.assert_empty_match("вміємо цим зазвичай користуватися")
        self.assert_has_error("вміємо цьому зазвичай користуватися")
        self.assert_empty_match("вони воліли мені якнайбільш ефективно допомогти")
        self.assert_empty_match("воліли заворушень не допускати")
        self.assert_empty_match("не втомлюються десятиріччями боротися Берлін і Венеція")
        self.assert_empty_match("постарається таку двозначність усунути")
        self.assert_empty_match("розпорядився частину зарплати примусово видавати")
        self.assert_empty_match("не схотіли нам про це казати")

        # не
        self.assert_empty_match("Самі респонденти пояснити причин не можуть")

        self.assert_empty_match("довелося план «Б» застосовувати")

        self.assert_empty_match("сподіваючися щось розтлумачити")
        self.assert_empty_match("Резюмуючи політик наголосив")
        #TODO:
        self.assert_empty_match("пригадує посміхаючись Аскольд")
        self.assert_has_error("неопізнаний літаючи об’єкт")
        self.assert_has_error("знищила існуючи бази даних")

        self.assert_empty_match("сидячи ціле життя")
        self.assert_empty_match("Не претендуючи жодною мірою")

        self.assert_empty_match("є кого згадувати")

        #TODO: too long
        #    self.assert_empty_match("уміє одним жестом, одним нюансом інтонації сказати");



    def test_rule_tn_v_vinf_n(self):
        self.assert_empty_match("має відбуватися ротація")
        self.assert_empty_match("має також народитися власна ідея")
        self.assert_empty_match("мали змогу оцінити відвідувачі")
        self.assert_empty_match("має ж десь поміститися двигун")
        self.assert_empty_match("дав трохи передихнути бізнесу")
        self.assert_empty_match("дають змогу з комфортом мандрувати чотирьом пасажирам")
        self.assert_empty_match("дали б змогу розвиватися національному")
        self.assert_empty_match("дозволила на початку 1990-х узагалі виникнути такому інституту")
        self.assert_empty_match("заважає і далі нестримно поширюватися багатьом міфам")
        self.assert_empty_match("люблять у нас кричати панікери")
        self.assert_empty_match("Почав різко зростати курс долара")
        self.assert_empty_match("пропонує «об’єднатися патріотам»")
        self.assert_empty_match("став формуватися прошарок")

        self.assert_empty_match("ставимо розварюватися легко відтиснену")

        # advp
        self.assert_empty_match("не даючи виїхати ванатжівці")
        self.assert_empty_match("даючи можливість висловлюватися радикалам")
        self.assert_empty_match("дозволяючи рухатися російському")

        self.assert_empty_match("готувала їсти хлопцям")
        self.assert_empty_match("вкласти спати Маринку")
        self.assert_empty_match("поклавши спати старого Якима")

        # plural
        self.assert_empty_match("заважають розвиватися погане управління, війна")
        self.assert_empty_match("став все частіше згадуватися незвичайний наслідок")
        self.assert_empty_match(" починає швидко жовтіти й опадати листя")
        self.assert_empty_match("перестають діяти й розвиватися демократичні")

        #TODO:
        #    self.assert_has_error("не має змоги на сто відсотків реалізуватися себе в ролі");

    def test_rule_tn_adv_vinf_n(self):
        self.assert_empty_match("важко розібратися багатьом людям.")
        self.assert_empty_match("незручно займатися президентові")
        self.assert_empty_match("пізно готуватися нам")
        self.assert_empty_match("найлегше ігнорувати людям із категорій")
        self.assert_empty_match("треба всіма силами берегти кожному")
        self.assert_empty_match("треба дуже уважно прислухатися владі")
        self.assert_empty_match("слід реагувати Америці")
        self.assert_empty_match("слід з обережністю їсти людям")
        self.assert_empty_match("варто сюди прилетіти людині")
        self.assert_empty_match("неможливо засвоїти одній людині")
        self.assert_empty_match("тяжче стало жити селянам")
        self.assert_empty_match("приємно слухати вчителям")
        self.assert_empty_match("повинно боротися суспільство")
        self.assert_empty_match("слід реально готуватися суспільству")

    def test_rule_tn_adj_vinf_n(self):
        self.assert_empty_match("змушені ночувати пасажири")
        self.assert_empty_match("повинен усього добитися сам")
        self.assert_empty_match("схильна лякати така пропаганда")
        self.assert_empty_match("зацікавлена перейняти угорська сторона")

    def test_rule_tn_noun_vinf_n(self):
        self.assert_empty_match("Пора дорослішати всім")  # пора does not have predic :(
        self.assert_empty_match("можливість висловитися серійному вбивці?")
        self.assert_empty_match("рішення про можливість балотуватися Кучмі")
        self.assert_empty_match("гріх уже зараз зайнятися Генеральній прокуратурі...")
        self.assert_empty_match("готовність спілкуватися людини")

        self.assert_empty_match("небажання вибачатися пов’язане з національною гордістю")
        self.assert_has_error("бажання постійно вчитися новому")
        self.assert_has_error("Кіно вчить вмінню простими словами")
        self.assert_has_error("Черга вчитися мистецтву мовчання")
        self.assert_has_error("у своєму виступі на конференції порадив української владі звернуть увагу")
        #TODO:
        #    self.assert_empty_match("про потребу покаятися представникам влади");
        #    self.assert_has_error("Це зумовлює необхідність формувати резервів");
        #    self.assert_has_error("пацієнтів будь-якої можливості одужати неприпустима");

    def test_rule_tn_vinf_n_v(self):
        #advp
        self.assert_empty_match("дозволивши розвалитись імперії")
        self.assert_empty_match("зніматися йому доводилося рідко")
        self.assert_empty_match("Гуляти мешканки гуртожитку тепер можуть")
        self.assert_empty_match("працювати ці люди не вміють")
        self.assert_empty_match("реагувати Майдан має")
        self.assert_empty_match("працювати українці будуть")
        self.assert_empty_match("влаштуватися їй не вдається")
        self.assert_empty_match("працювати цьому політикові доводиться")
        # не -> v_rod
        self.assert_empty_match("Робити прогнозів не буду")
        self.assert_empty_match("панькатися наміру не має")

        # було -> v_rod
        self.assert_empty_match("було ввезено тракторів")

        #TODO:
        #    self.assert_empty_match("вижити шансів у нього не було");

    def test_rule_tn_vinf_n_adv(self):
        self.assert_empty_match("літати тобі не можна")
        self.assert_empty_match("Порозумітися обом сторонам було важко")
        self.assert_empty_match("втихомирюватися нам зарано")
        self.assert_empty_match("Зупинятися мені вже не можна")
        self.assert_empty_match("працювати правоохоронцям складно")
        self.assert_empty_match("працювати правоохоронцям досить складно")
        self.assert_empty_match("звертатися пенсіонерам не потрібно")
        self.assert_empty_match("Їхати мені було не страшно")
        self.assert_has_error("навчитися цьому досить легко")

    def test_rule_tn_vinf_n_adj(self):
        self.assert_empty_match("замислитися нащадки повинні")
        self.assert_empty_match("працювати студенти готові")
        self.assert_empty_match("платити Рига згодна")
        self.assert_empty_match("Владі не потрібен мир, хоча і війну вести вона не здатна.")
        # TODO:
        #    self.assert_empty_match("буваю йому вдячна"); // v_dav

    def test_rule_tn_vinf_v_n(self):
        self.assert_empty_match("Заспокоювати стали найагресивнішого")
        self.assert_empty_match("платити доведеться повну вартість")
        self.assert_empty_match("закінчити цей огляд хочеться словами")
        self.assert_has_error("все досліджуйте і постійно навчайтеся новому.")
        #TODO: їм also verb
        #    self.assert_empty_match("їсти їм доведеться траву");

    def test_rule_tn_n_vinf_adj(self):
        """testRuleTn_N_Vinf_ADJ: @Ignore in Java (TODO), passes here"""
        #TODO:
        self.assert_empty_match("Здатність ненавидіти прошита")
        self.assert_empty_match("рішення балотуватися продиктоване")
        self.assert_empty_match("Вони обманюватись раді")

    def test_rule_tn_numr(self):

        # numr
        self.assert_empty_match("купив три книги")
        self.assert_empty_match("входило двоє студентів")
        self.assert_empty_match("виповнилося шістнадцять")
        self.assert_empty_match("зобов'язав обох порушників")
        self.assert_matches(1, "зобов'язав обом порушникам", lambda msg: _assert_contains(msg, "давальний"))
        self.assert_empty_match("передав решту шкіл")

        self.assert_empty_match("одержав хабарів на суму 10")
        self.assert_empty_match("одержав хабарів на загальну суму")
        self.assert_empty_match("уклали договорів страхування на загальну суму")
        self.assert_empty_match("и втратили капіталовкладень нерезидентів замалим не на $13,6 млрд.")
        self.assert_empty_match("приготували сортів десять")
        self.assert_empty_match("зібрали сортів 10")
        self.assert_empty_match("зібрали сортів — 10")

        self.assert_empty_match("вчинено порушень обсягом на 27")

        self.assert_empty_match("завдав кілька ударів руками")
        self.assert_empty_match("завдав кількох ударів руками")
        self.assert_empty_match("потребувала мільйон")
        self.assert_empty_match("нарубав неймовірну кількість вугілля")
        self.assert_empty_match("відбувся чверть століття тому")

        self.assert_empty_match("слідкувало майже мільйон людей")
        self.assert_empty_match("не виїхало більшість автобусів")

        self.assert_empty_match("буде лежати двоє хворих")

    def test_rule_tnv_naz(self):
        # v_naz
        self.assert_empty_match("прийшов Тарас")
        self.assert_empty_match("було пасмо")
        self.assert_empty_match("сміялися смішні гієни")
        self.assert_empty_match("в мені наростали впевненість і сила")
        self.assert_empty_match("де є якість")
        self.assert_empty_match("в усіх країнах є міфи")

        # зватися + prop
        self.assert_empty_match("звалося Подєбради")

    def test_rule_tntime(self):
        # time
        self.assert_empty_match("тренувалися годину")
        self.assert_empty_match("відбудуться наступного дня")
        self.assert_empty_match("їхав цілу ніч")
        self.assert_empty_match("сколихнула минулого року")
        self.assert_empty_match("збираються цього вечора")
        self.assert_empty_match("чекати годинами")
        self.assert_empty_match("спостерігається останнім часом")
        self.assert_empty_match("відійшли метрів п'ять")
        self.assert_empty_match("публікується кожні два роки")
        self.assert_empty_match("зірватися всі ці 27 років")
        self.assert_empty_match("відбувся минулої неділі")
        self.assert_empty_match("закінчилося 18-го ввечері")
        self.assert_empty_match("не знімався останні 10 років")
        self.assert_empty_match("розпочнеться того ж дня")
        self.assert_empty_match("помер цього вересня")
        self.assert_empty_match("з’являться наступного ранку на суд")
        self.assert_empty_match("мучитися три з половиною роки")
        self.assert_empty_match("буде стояти двадцять і три роки")
        self.assert_empty_match("попрацювала місяць-півтора")
        self.assert_empty_match("сніг не тане всю зиму")

        self.assert_empty_match("вщухнуть протягом кількох днів")

        self.assert_empty_match("побутувала одночасно двома чи трьома мовами")

        # TODO: noun inside
        #  self.assert_empty_match("мучитися довжелезних три з половиною роки");
        self.assert_empty_match("працює більшу частину часу")
        #    self.assert_empty_match("доведеться наступні 6−8 років");
        self.assert_empty_match("які стартували цього та минулого року")

    def test_rule_tn_vrod(self):
        self.assert_empty_match("не мав меблів")
        #    self.assert_has_error("не мав меблі");
        self.assert_empty_match("не повинен пропускати жодного звуку")
        self.assert_empty_match("не став витрачати грошей")
        self.assert_empty_match("казала цього не робити")
        self.assert_empty_match("не повинно перевищувати граничної величини")
        self.assert_empty_match("здаватися коаліціанти не збираються")

        self.assert_empty_match("не існувало конкуренції")

        # не + X + verb
        self.assert_empty_match("не можна зберігати ілюзій")

        self.assert_empty_match("скільки отримує грошей")
        self.assert_empty_match("скільки буде людей")
        self.assert_empty_match("трохи маю контактів")
        self.assert_empty_match("скільки загалом здійснили постановок")
        self.assert_empty_match("стільки заплановано постановок")
        self.assert_empty_match("Багато в пресі з’явилося публікацій")
        self.assert_empty_match("небагато надходить книжок")
        self.assert_empty_match("ніж поставили стільців")

        self.assert_empty_match("Росія будує трубопроводів більше")

        self.assert_empty_match("вони мали більше прав")
        self.assert_empty_match("вони мали найменше прав")
        self.assert_has_error("видається найбільш наближеної")

        self.assert_empty_match("не стане сили")
        #TODO:
        #    self.assert_has_error("не відбувалися якихось серйозних");
        self.assert_empty_match("нарубав лісу")  # v_rod

    def test_rule_tn_insert_phrase(self):
        self.assert_empty_match("змалював дивовижної краси церкву")
        self.assert_empty_match("Піднявся страшенної сили крижаний шторм")
        self.assert_empty_match("поводиться дивним чином")
        self.assert_empty_match("триває повним ходом.")
        #TODO:
        #    self.assert_empty_match("скоюються незнайомими жертві злочинцями");

    def test_rule_disambig_naz_inf(self):
        readings = []

        readings.append(AnalyzedTokenReadings(AnalyzedToken("", SENTENCE_START_TAGNAME, ""), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("повинен", "adj:m:v_naz:short:predic", "повинний"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("був", "verb:imperf:past:m", "бути"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("випадок", "noun:inanim:m:v_zna", "випадок"), 0))
        readings.append(AnalyzedTokenReadings(AnalyzedToken("передбачити", "verb:perf:inf", "передбачити"), 0))

        sent = AnalyzedSentence(readings)

        assert len(self.rule.match(sent)) == 0



