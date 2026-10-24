"""Port of org.languagetool.tagging.uk.UkrainianTaggerTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.uk.tokenizers import UkrainianWordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('uk')


tokenizer = UkrainianWordTokenizer()


def _tagger():
    return get_language('uk').tagger


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _utf16(s):
    return s.encode('utf-16-be', 'surrogatepass')


def my_assert(text, expected):
    """TestTools.myAssert(input, expected, tokenizer, tagger)"""
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(sorted(('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in r.readings),
                           key=_utf16))
           for r in _tagger().tag(tokens)]
    assert ' -- '.join(out) == expected


def assert_not_tagged(word):
    my_assert(word, word + "/[null]null")


def assert_tagged(word, tagged):
    my_assert(word, tagged)


def test_dictionary():
    """testDictionary (TestTools.testDictionary only prints warnings for
    entries without POS tags; check that the dictionary can be read)"""
    entries, _ = _tagger().dictionary.count_entries()
    assert entries > 0


def test_tagger():

    # one-way case sensitivity
    my_assert("києві", "києві/[кий]noun:inanim:m:v_dav|києві/[кий]noun:inanim:m:v_mis")
    my_assert("Києві", "Києві/[Кий]noun:anim:m:v_dav:prop:fname|Києві/[Кий]noun:anim:m:v_mis:prop:fname|Києві/[Київ]noun:inanim:m:v_mis:prop:geo|Києві/[кий]noun:inanim:m:v_dav|Києві/[кий]noun:inanim:m:v_mis")
    my_assert("Ізюму", "Ізюму/[Ізюм]noun:inanim:m:v_dav:prop:geo|Ізюму/[Ізюм]noun:inanim:m:v_mis:prop:geo|Ізюму/[Ізюм]noun:inanim:m:v_rod:prop:geo|Ізюму/[ізюм]noun:inanim:m:v_dav:bad|Ізюму/[ізюм]noun:inanim:m:v_mis:bad|Ізюму/[ізюм]noun:inanim:m:v_rod:bad")
    my_assert("віл", "віл/[віл]noun:anim:m:v_naz")
    my_assert("Віл", "Віл/[віл]noun:anim:m:v_naz")
    my_assert("ВІЛ", "ВІЛ/[ВІЛ]noun:inanim:m:v_dav:nv:abbr|ВІЛ/[ВІЛ]noun:inanim:m:v_mis:nv:abbr|ВІЛ/[ВІЛ]noun:inanim:m:v_naz:nv:abbr|ВІЛ/[ВІЛ]noun:inanim:m:v_oru:nv:abbr|ВІЛ/[ВІЛ]noun:inanim:m:v_rod:nv:abbr|ВІЛ/[ВІЛ]noun:inanim:m:v_zna:nv:abbr|ВІЛ/[віл]noun:anim:m:v_naz")
    my_assert("далі", "далі/[даль]noun:inanim:f:v_dav|далі/[даль]noun:inanim:f:v_mis|далі/[даль]noun:inanim:f:v_rod|далі/[даль]noun:inanim:p:v_kly|далі/[даль]noun:inanim:p:v_naz|далі/[даль]noun:inanim:p:v_zna|далі/[далі]adv:compc:predic")
    my_assert("Далі", "Далі/[Даль]noun:anim:m:v_mis:prop:lname|Далі/[Даля]noun:anim:f:v_dav:prop:fname|Далі/[Даля]noun:anim:f:v_mis:prop:fname|Далі/[Даля]noun:anim:f:v_rod:prop:fname|Далі/[Даля]noun:anim:p:v_kly:prop:fname|Далі/[Даля]noun:anim:p:v_naz:prop:fname" + "|Далі/[Далі]noun:anim:m:v_dav:nv:prop:lname|Далі/[Далі]noun:anim:m:v_kly:nv:prop:lname|Далі/[Далі]noun:anim:m:v_mis:nv:prop:lname|Далі/[Далі]noun:anim:m:v_naz:nv:prop:lname|Далі/[Далі]noun:anim:m:v_oru:nv:prop:lname" + "|Далі/[Далі]noun:anim:m:v_rod:nv:prop:lname|Далі/[Далі]noun:anim:m:v_zna:nv:prop:lname|Далі/[даль]noun:inanim:f:v_dav|Далі/[даль]noun:inanim:f:v_mis|Далі/[даль]noun:inanim:f:v_rod|Далі/[даль]noun:inanim:p:v_kly|Далі/[даль]noun:inanim:p:v_naz|Далі/[даль]noun:inanim:p:v_zna|Далі/[далі]adv:compc:predic")
    my_assert("Бен", "Бен/[Бен]noun:anim:m:v_naz:prop:fname|Бен/[бен]part:pers")
    my_assert("бен", "бен/[бен]part:pers")

    my_assert("френдити", "френдити/[френдити]verb:imperf:inf:slang")

    my_assert("Справу порушено судом", "Справу/[справа]noun:inanim:f:v_zna -- порушено/[порушити]verb:perf:impers -- судом/[суд]noun:inanim:m:v_oru|судом/[судома]noun:inanim:p:v_rod")

    expected = "Майже/[майже]adv -- два/[два]numr:p:v_naz|два/[два]numr:p:v_zna -- роки/[рік]noun:inanim:p:v_kly|роки/[рік]noun:inanim:p:v_naz|роки/[рік]noun:inanim:p:v_zna" + " -- тому/[те]noun:inanim:n:v_dav:pron:dem|тому/[те]noun:inanim:n:v_mis:pron:dem|тому/[той]adj:m:v_dav:pron:dem|тому/[той]adj:m:v_mis:pron:dem|тому/[той]adj:n:v_dav:pron:dem|тому/[той]adj:n:v_mis:pron:dem|тому/[том]noun:inanim:m:v_dav|тому/[том]noun:inanim:m:v_mis|тому/[том]noun:inanim:m:v_rod|тому/[тому]adv|тому/[тому]conj:subord" + " -- Люба/[Люба]noun:anim:f:v_naz:prop:fname|Люба/[любий]adj:f:v_kly:compb|Люба/[любий]adj:f:v_naz:compb -- разом/[раз]noun:inanim:m:v_oru|разом/[разом]adv -- із/[із]prep" + " -- чоловіком/[чоловік]noun:anim:m:v_oru -- Степаном/[Степан]noun:anim:m:v_oru:prop:fname -- виїхали/[виїхати]verb:perf:past:p -- туди/[туди]adv:pron:dem" + " -- на/[на]intj|на/[на]part|на/[на]prep -- " + "проживання/[проживання]noun:inanim:n:v_kly|проживання/[проживання]noun:inanim:n:v_naz|проживання/[проживання]noun:inanim:n:v_rod|проживання/[проживання]noun:inanim:n:v_zna" + "|проживання/[проживання]noun:inanim:p:v_kly|проживання/[проживання]noun:inanim:p:v_naz|проживання/[проживання]noun:inanim:p:v_zna"

    my_assert("Майже два роки тому Люба разом із чоловіком Степаном виїхали туди на проживання.", expected)

    my_assert("аудіо-", "аудіо-/[аудіо-]noninfl")

def test_prop_lower_case():
    my_assert("вкраїна", "вкраїна/[вкраїна]noun:inanim:f:v_naz:prop:geo:bad:err")

def test_number_tagging():
    my_assert("101,234", "101,234/[101,234]number")
    my_assert("101 234", "101 234/[101 234]number")

    my_assert("3,5-5,6 7° 7,4°C", "3,5-5,6/[3,5-5,6]number -- 7/[7]number -- 7,4/[7,4]number -- C/[C]number:latin")

    my_assert("XIX", "XIX/[XIX]number:latin")
    my_assert("II", "II/[II]number:latin")
    my_assert("X", "X/[X]number:latin")

    my_assert("D", "D/[null]null")

    # latin number with cyrillic
    my_assert("ХІХ", "ХІХ/[ХІХ]number:latin:bad:err")
    my_assert("ІV", "ІV/[ІV]number:latin:bad")
    my_assert("ХІХ-го", "ХІХ-го/[ХІХ-го]number:latin:bad")
    my_assert("V-типу", "V-типу/[null]null")

    # done in disambig
    #    my_assert("Петром І", "Петром/[Петро]noun:anim:m:v_oru:prop:fname І/[І]number:latin:bad");

    my_assert("10–15", "10–15/[10–15]number")

    my_assert("14.07.2001", "14.07.2001/[14.07.2001]date")

    my_assert("15:33", "15:33/[15:33]time")
    my_assert("15:33:00", "15:33:00/[15:33:00]time")
    my_assert("о 15.33", "о/[о]intj|о/[о]prep -- 15.33/[15.33]time")
    # in the disambiguator
    #    my_assert("15.33", "15.33/[null]null");
    my_assert("О 1:05", "О/[о]intj|О/[о]prep -- 1:05/[1:05]time")

    assert_not_tagged("5610100000:01:041:0487")

    assert_not_tagged("H1")

def test_hashtag():
    my_assert("#янебоюсьсказати", "#янебоюсьсказати/[#янебоюсьсказати]hashtag")

def test_tagging_with_dots():
    my_assert("300 р. до н. е.", "300/[300]number -- р./[р.]noun:inanim:f:v_dav:nv:abbr:xp2|р./[р.]noun:inanim:f:v_mis:nv:abbr:xp2|р./[р.]noun:inanim:f:v_naz:nv:abbr:xp2|р./[р.]noun:inanim:f:v_oru:nv:abbr:xp2" +"|р./[р.]noun:inanim:f:v_rod:nv:abbr:xp2|р./[р.]noun:inanim:f:v_zna:nv:abbr:xp2|р./[р.]noun:inanim:m:v_dav:nv:abbr:xp1|р./[р.]noun:inanim:m:v_mis:nv:abbr:xp1" +"|р./[р.]noun:inanim:m:v_naz:nv:abbr:xp1|р./[р.]noun:inanim:m:v_oru:nv:abbr:xp1|р./[р.]noun:inanim:m:v_rod:nv:abbr:xp1|р./[р.]noun:inanim:m:v_zna:nv:abbr:xp1" +" -- до/[до]noun:inanim:n:v_dav:nv|до/[до]noun:inanim:n:v_kly:nv|до/[до]noun:inanim:n:v_mis:nv|до/[до]noun:inanim:n:v_naz:nv|до/[до]noun:inanim:n:v_oru:nv" +"|до/[до]noun:inanim:n:v_rod:nv|до/[до]noun:inanim:n:v_zna:nv|до/[до]noun:inanim:p:v_dav:nv|до/[до]noun:inanim:p:v_kly:nv|до/[до]noun:inanim:p:v_mis:nv" +"|до/[до]noun:inanim:p:v_naz:nv|до/[до]noun:inanim:p:v_oru:nv|до/[до]noun:inanim:p:v_rod:nv|до/[до]noun:inanim:p:v_zna:nv|до/[до]prep" +" -- н./[н.]adj:f:v_dav:nv:abbr|н./[н.]adj:f:v_mis:nv:abbr|н./[н.]adj:f:v_naz:nv:abbr|н./[н.]adj:f:v_oru:nv:abbr|н./[н.]adj:f:v_rod:nv:abbr|н./[н.]adj:f:v_zna:nv:abbr|н./[н.]noun:inanim:n:v_rod:nv:abbr" +" -- е./[е.]noun:inanim:f:v_dav:nv:abbr|е./[е.]noun:inanim:f:v_mis:nv:abbr|е./[е.]noun:inanim:f:v_naz:nv:abbr|е./[е.]noun:inanim:f:v_oru:nv:abbr|е./[е.]noun:inanim:f:v_rod:nv:abbr" +"|е./[е.]noun:inanim:f:v_zna:nv:abbr|е./[е.]noun:inanim:p:v_dav:nv:abbr|е./[е.]noun:inanim:p:v_mis:nv:abbr|е./[е.]noun:inanim:p:v_naz:nv:abbr|е./[е.]noun:inanim:p:v_oru:nv:abbr" +"|е./[е.]noun:inanim:p:v_rod:nv:abbr|е./[е.]noun:inanim:p:v_zna:nv:abbr")

    my_assert("300 тис. гривень", "300/[300]number " + "-- тис./[тис.]noun:inanim:f:v_dav:nv:numr:abbr|тис./[тис.]noun:inanim:f:v_mis:nv:numr:abbr|тис./[тис.]noun:inanim:f:v_naz:nv:numr:abbr|тис./[тис.]noun:inanim:f:v_oru:nv:numr:abbr|тис./[тис.]noun:inanim:f:v_rod:nv:numr:abbr|тис./[тис.]noun:inanim:f:v_zna:nv:numr:abbr|тис./[тис.]noun:inanim:n:v_dav:nv:abbr|тис./[тис.]noun:inanim:n:v_mis:nv:abbr|тис./[тис.]noun:inanim:n:v_naz:nv:abbr|тис./[тис.]noun:inanim:n:v_oru:nv:abbr|тис./[тис.]noun:inanim:n:v_rod:nv:abbr|тис./[тис.]noun:inanim:n:v_zna:nv:abbr|тис./[тис.]noun:inanim:p:v_dav:nv:abbr|тис./[тис.]noun:inanim:p:v_dav:nv:numr:abbr|тис./[тис.]noun:inanim:p:v_mis:nv:abbr|тис./[тис.]noun:inanim:p:v_mis:nv:numr:abbr|тис./[тис.]noun:inanim:p:v_naz:nv:abbr|тис./[тис.]noun:inanim:p:v_naz:nv:numr:abbr|тис./[тис.]noun:inanim:p:v_oru:nv:abbr|тис./[тис.]noun:inanim:p:v_oru:nv:numr:abbr|тис./[тис.]noun:inanim:p:v_rod:nv:abbr|тис./[тис.]noun:inanim:p:v_rod:nv:numr:abbr|тис./[тис.]noun:inanim:p:v_zna:nv:abbr|тис./[тис.]noun:inanim:p:v_zna:nv:numr:abbr " + "-- гривень/[гривня]noun:inanim:p:v_rod")

    #       "Валерій/[Валерій]noun:anim:m:v_naz:prop:fname -- міліціонер-пародист/[міліціонер-пародист]noun:anim:m:v_naz -- Авт./[null]null"
    my_assert("Валерій (міліціонер-пародист. – Авт.) стане пародистом.", "Валерій/[Валерій]noun:anim:m:v_naz:prop:fname -- міліціонер-пародист/[міліціонер-пародист]noun:anim:m:v_naz" + " -- Авт./[авт.]adj:f:v_dav:nv:abbr|Авт./[авт.]adj:f:v_mis:nv:abbr|Авт./[авт.]adj:f:v_naz:nv:abbr|Авт./[авт.]adj:f:v_oru:nv:abbr|Авт./[авт.]adj:f:v_rod:nv:abbr|Авт./[авт.]adj:f:v_zna:nv:abbr|Авт./[авт.]adj:m:v_dav:nv:abbr|Авт./[авт.]adj:m:v_mis:nv:abbr|Авт./[авт.]adj:m:v_naz:nv:abbr|Авт./[авт.]adj:m:v_oru:nv:abbr|Авт./[авт.]adj:m:v_rod:nv:abbr|Авт./[авт.]adj:m:v_zna:ranim:nv:abbr|Авт./[авт.]adj:m:v_zna:rinanim:nv:abbr|Авт./[авт.]adj:n:v_dav:nv:abbr|Авт./[авт.]adj:n:v_mis:nv:abbr|Авт./[авт.]adj:n:v_naz:nv:abbr|Авт./[авт.]adj:n:v_oru:nv:abbr|Авт./[авт.]adj:n:v_rod:nv:abbr|Авт./[авт.]adj:n:v_zna:nv:abbr|Авт./[авт.]adj:p:v_dav:nv:abbr|Авт./[авт.]adj:p:v_mis:nv:abbr|Авт./[авт.]adj:p:v_naz:nv:abbr|Авт./[авт.]adj:p:v_oru:nv:abbr|Авт./[авт.]adj:p:v_rod:nv:abbr|Авт./[авт.]adj:p:v_zna:ranim:nv:abbr|Авт./[авт.]adj:p:v_zna:rinanim:nv:abbr|Авт./[авт.]noun:anim:m:v_naz:nv:abbr" + " -- стане/[стан]noun:inanim:m:v_kly:xp1|стане/[стан]noun:inanim:m:v_kly:xp2|стане/[станути]verb:perf:futr:s:3|стане/[стати]verb:perf:futr:s:3 -- пародистом/[пародист]noun:anim:m:v_oru")

    #    my_assert("Сьогодні (у четвер. - Ред.), вранці.",
    #        "Сьогодні/[сьогодні]adv -- у/[у]prep -- четвер/[четвер]noun:inanim:m:v_naz|четвер/[четвер]noun:inanim:m:v_zna -- "
    #        +"Ред./[ред.]noun:inanim:f:v_dav:nv:abbr|Ред./[ред.]noun:inanim:f:v_mis:nv:abbr|Ред./[ред.]noun:inanim:f:v_naz:nv:abbr|Ред./[ред.]noun:inanim:f:v_oru:nv:abbr|Ред./[ред.]noun:inanim:f:v_rod:nv:abbr|Ред./[ред.]noun:inanim:f:v_zna:nv:abbr|Ред./[ред.]noun:inanim:m:v_naz:abbr|Ред./[ред.]noun:inanim:p:v_dav:nv:abbr|Ред./[ред.]noun:inanim:p:v_mis:nv:abbr|Ред./[ред.]noun:inanim:p:v_naz:nv:abbr|Ред./[ред.]noun:inanim:p:v_oru:nv:abbr|Ред./[ред.]noun:inanim:p:v_rod:nv:abbr|Ред./[ред.]noun:inanim:p:v_zna:nv:abbr -- вранці/[вранці]adv",
    #         tokenizer, tagger);

    my_assert("Є. Бакуліна.", "Є./[null]null -- Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_kly:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert("і т. д.", "і/[і]conj:coord|і/[і]part -- т./[т.]adj:n:v_dav:nv:abbr|т./[т.]adj:n:v_mis:nv:abbr|т./[т.]adj:n:v_naz:nv:abbr|т./[т.]adj:n:v_oru:nv:abbr|т./[т.]adj:n:v_rod:nv:abbr|т./[т.]adj:n:v_zna:nv:abbr|т./[т.]adv:abbr|т./[т.]noun:inanim:m:v_dav:nv:abbr|т./[т.]noun:inanim:m:v_mis:nv:abbr|т./[т.]noun:inanim:m:v_naz:nv:abbr|т./[т.]noun:inanim:m:v_oru:nv:abbr|т./[т.]noun:inanim:m:v_rod:nv:abbr|т./[т.]noun:inanim:m:v_zna:nv:abbr|т./[т.]noun:inanim:p:v_dav:nv:abbr|т./[т.]noun:inanim:p:v_mis:nv:abbr|т./[т.]noun:inanim:p:v_naz:nv:abbr|т./[т.]noun:inanim:p:v_oru:nv:abbr|т./[т.]noun:inanim:p:v_rod:nv:abbr|т./[т.]noun:inanim:p:v_zna:nv:abbr" + " -- д./[д.]adv:abbr")

def test_proper_name_all_caps():
    my_assert("УКРАЇНА", "УКРАЇНА/[Україна]noun:inanim:f:v_naz:prop:geo|УКРАЇНА/[україна]noun:inanim:f:v_naz:prop:geo:alt|УКРАЇНА/[україна]noun:inanim:f:v_naz:prop:geo:alt")
    my_assert("СИРІЮ", "СИРІЮ/[Сирія]noun:inanim:f:v_zna:prop:geo|СИРІЮ/[сиріти]verb:imperf:pres:s:1")
    my_assert("НЬЮ-ЙОРК", "НЬЮ-ЙОРК/[Нью-Йорк]noun:inanim:m:v_naz:prop:geo:xp1|НЬЮ-ЙОРК/[Нью-Йорк]noun:inanim:m:v_naz:prop:geo:xp2|НЬЮ-ЙОРК/[Нью-Йорк]noun:inanim:m:v_zna:prop:geo:xp1|НЬЮ-ЙОРК/[Нью-Йорк]noun:inanim:m:v_zna:prop:geo:xp2")
    assert_not_tagged("УКРАЇ")


def test_compound_numr():
    my_assert("п'ятсотдвадцятип'ятиріччя", "п'ятсотдвадцятип'ятиріччя/[п'ятсотдвадцятип'ятиріччя]noun:inanim:n:v_naz|п'ятсотдвадцятип'ятиріччя/[п'ятсотдвадцятип'ятиріччя]noun:inanim:n:v_rod|п'ятсотдвадцятип'ятиріччя/[п'ятсотдвадцятип'ятиріччя]noun:inanim:n:v_zna")
    my_assert("п’ятсотдвадцятип'ятирі\u0301ччям", "п'ятсотдвадцятип'ятиріччям/[п'ятсотдвадцятип'ятиріччя]noun:inanim:n:v_oru")
    my_assert("шістдесятип’ятимільйо\u0301нний", "шістдесятип'ятимільйонний/[шістдесятип'ятимільйонний]adj:m:v_naz:numr|шістдесятип'ятимільйонний/[шістдесятип'ятимільйонний]adj:m:v_zna:rinanim:numr")
    my_assert("стодвадцятип’ятирі\u0301чний", "стодвадцятип'ятирічний/[стодвадцятип'ятирічний]adj:m:v_naz|стодвадцятип'ятирічний/[стодвадцятип'ятирічний]adj:m:v_zna:rinanim")
    my_assert("кількадесятитисячної", "кількадесятитисячної/[кількадесятитисячний]adj:f:v_rod:numr")
    my_assert("Тридцятидвохрічний", "Тридцятидвохрічний/[Тридцятидвохрічний]adj:m:v_naz|Тридцятидвохрічний/[Тридцятидвохрічний]adj:m:v_zna:rinanim")
    assert_not_tagged("агатомільйонних")

def test_dynamic_tagging_numeric_pair():
    # numr-numr
    my_assert("одним-трьома", "одним-трьома/[один-три]numr:p:v_oru|одним-трьома/[один-троє]numr:p:v_oru")
    my_assert("одного-другого", "одного-другого/[один-другий]adj:m:v_rod:numr|одного-другого/[один-другий]adj:m:v_zna:ranim:numr|одного-другого/[один-другий]adj:n:v_rod:numr")
    #TODO: бере іменник п’ята
    my_assert("п'яти-шести", "п'яти-шести/[п'ять-шість]numr:p:v_dav|п'яти-шести/[п'ять-шість]numr:p:v_mis|п'яти-шести/[п'ять-шість]numr:p:v_rod")
    my_assert("три-чотири", "три-чотири/[три-чотири]numr:p:v_naz|три-чотири/[три-чотири]numr:p:v_zna")
    my_assert("два-чотири", "два-чотири/[два-чотири]numr:p:v_naz|два-чотири/[два-чотири]numr:p:v_zna")
    my_assert("одному-двох", "одному-двох/[один-два]numr:p:v_mis")
    my_assert("три–чотири", "три-чотири/[три-чотири]numr:p:v_naz|три-чотири/[три-чотири]numr:p:v_zna|три–чотири/[null]null")
    my_assert("шість-сім", "шість-сім/[шість-сім]numr:p:v_naz|шість-сім/[шість-сім]numr:p:v_zna")
    my_assert("три-сім", "три-сім/[три-сім]numr:p:v_naz|три-сім/[три-сім]numr:p:v_zna")

    # noun-numr
    my_assert("абзац-два", "абзац-два/[абзац-два]noun:inanim:m:v_naz|абзац-два/[абзац-два]noun:inanim:m:v_zna|абзац-два/[абзац-два]noun:inanim:p:v_naz|абзац-два/[абзац-два]noun:inanim:p:v_zna")
    my_assert("сотні-дві", "сотні-дві/[сотня-два]noun:inanim:p:v_naz|сотні-дві/[сотня-два]noun:inanim:p:v_zna")
    my_assert("тисячею-трьома", "тисячею-трьома/[тисяча-три]noun:inanim:f:v_oru:numr|тисячею-трьома/[тисяча-три]noun:inanim:p:v_oru:numr|тисячею-трьома/[тисяча-троє]noun:inanim:f:v_oru:numr|тисячею-трьома/[тисяча-троє]noun:inanim:p:v_oru:numr")

    my_assert("друге-третє", "друге-третє/[другий-третій]adj:n:v_kly:numr|друге-третє/[другий-третій]adj:n:v_naz:numr|друге-третє/[другий-третій]adj:n:v_zna:numr")

def test_dynamic_tagging_numbers():
    my_assert("100-річному", "100-річному/[100-річний]adj:m:v_dav|100-річному/[100-річний]adj:m:v_mis|100-річному/[100-річний]adj:n:v_dav|100-річному/[100-річний]adj:n:v_mis")
    my_assert("1-2-відсотковим", "1-2-відсотковим/[1-2-відсотковий]adj:m:v_oru|1-2-відсотковим/[1-2-відсотковий]adj:n:v_oru|1-2-відсотковим/[1-2-відсотковий]adj:p:v_dav")
    my_assert("10-класників", "10-класників/[10-класник]noun:anim:p:v_rod|10-класників/[10-класник]noun:anim:p:v_zna")
    my_assert("10-хвилинка", "10-хвилинка/[10-хвилинка]noun:inanim:f:v_naz")
    my_assert("11-12-річний", "11-12-річний/[11-12-річний]adj:m:v_kly|11-12-річний/[11-12-річний]adj:m:v_naz|11-12-річний/[11-12-річний]adj:m:v_zna:rinanim")

    my_assert("100-й", "100-й/[100-й]adj:f:v_dav:numr|100-й/[100-й]adj:f:v_mis:numr|100-й/[100-й]adj:m:v_naz:numr|100-й/[100-й]adj:m:v_zna:rinanim:numr")
    my_assert("50-х", "50-х/[50-й]adj:p:v_mis:numr|50-х/[50-й]adj:p:v_rod:numr|50-х/[50-й]adj:p:v_zna:ranim:numr")
    my_assert("11-ту", "11-ту/[11-й]adj:f:v_zna:numr")
    my_assert("3-ій", "3-ій/[3-й]adj:f:v_dav:numr|3-ій/[3-й]adj:f:v_mis:numr|3-ій/[3-й]adj:m:v_naz:numr|3-ій/[3-й]adj:m:v_zna:rinanim:numr")
    my_assert("5-ій", "5-ій/[5-й]adj:f:v_dav:numr|5-ій/[5-й]adj:f:v_mis:numr")
    my_assert("33-ми", "33-ми/[33-й]adj:p:v_oru:numr")
    my_assert("100%-й", "100%-й/[100%-й]adj:f:v_dav:numr|100%-й/[100%-й]adj:f:v_mis:numr|100%-й/[100%-й]adj:m:v_naz:numr|100%-й/[100%-й]adj:m:v_zna:rinanim:numr")
    my_assert("2000-ні", "2000-ні/[2000-й]adj:p:v_naz:numr|2000-ні/[2000-й]adj:p:v_zna:rinanim:numr")


    # too many letters
    my_assert("58-мою", "58-мою/[58-й]adj:f:v_oru:numr:bad")
    # invalid numr
    my_assert("3-ми", "3-ми/[3-й]adj:p:v_oru:numr")
    #    my_assert("7-ма", "7-ма/[7-й]adj:f:v_naz:numr|7-ма/[7]numr:p:v_oru:bad");
    my_assert("7-ма", "7-ма/[7-й]adj:f:v_naz:numr")
    my_assert("2-3-ма", "2-3-ма/[2-3]numr:p:v_oru:bad")
    my_assert("15-ти", "15-ти/[15]numr:p:v_dav:bad|15-ти/[15]numr:p:v_mis:bad|15-ти/[15]numr:p:v_rod:bad")
    my_assert("20-ці", "20-ці/[20]numr:f:v_dav:bad|20-ці/[20]numr:f:v_mis:bad")
    my_assert("42-ві", "42-ві/[42]numr:p:v_naz:bad|42-ві/[42]numr:p:v_zna:rinanim:bad")
    my_assert("148-ми", "148-ми/[148-й]adj:p:v_oru:numr")

    # n-dash
    my_assert("54–річна", "54-річна/[54-річний]adj:f:v_kly|54-річна/[54-річний]adj:f:v_naz|54–річна/[null]null")
    assert_not_tagged("54–бкх")

    my_assert("100-річчя", "100-річчя/[100-річчя]noun:inanim:n:v_kly|100-річчя/[100-річчя]noun:inanim:n:v_naz|100-річчя/[100-річчя]noun:inanim:n:v_rod|100-річчя/[100-річчя]noun:inanim:n:v_zna|100-річчя/[100-річчя]noun:inanim:p:v_kly|100-річчя/[100-річчя]noun:inanim:p:v_naz|100-річчя/[100-річчя]noun:inanim:p:v_zna")
    my_assert("100-РІЧЧЯМ", "100-РІЧЧЯМ/[100-річчя]noun:inanim:n:v_oru|100-РІЧЧЯМ/[100-річчя]noun:inanim:p:v_dav")
    my_assert("100-метрівка", "100-метрівка/[100-метрівка]noun:inanim:f:v_naz")
    my_assert("100-відсотково", "100-відсотково/[100-відсотково]adv")
    my_assert("120-мм", "120-мм/[120-мм]adj:f:v_dav|120-мм/[120-мм]adj:f:v_mis|120-мм/[120-мм]adj:f:v_naz|120-мм/[120-мм]adj:f:v_oru|120-мм/[120-мм]adj:f:v_rod|120-мм/[120-мм]adj:f:v_zna" + "|120-мм/[120-мм]adj:m:v_dav|120-мм/[120-мм]adj:m:v_mis|120-мм/[120-мм]adj:m:v_naz|120-мм/[120-мм]adj:m:v_oru|120-мм/[120-мм]adj:m:v_rod|120-мм/[120-мм]adj:m:v_zna" + "|120-мм/[120-мм]adj:n:v_dav|120-мм/[120-мм]adj:n:v_mis|120-мм/[120-мм]adj:n:v_naz|120-мм/[120-мм]adj:n:v_oru|120-мм/[120-мм]adj:n:v_rod|120-мм/[120-мм]adj:n:v_zna" + "|120-мм/[120-мм]adj:p:v_dav|120-мм/[120-мм]adj:p:v_mis|120-мм/[120-мм]adj:p:v_naz|120-мм/[120-мм]adj:p:v_oru|120-мм/[120-мм]adj:p:v_rod|120-мм/[120-мм]adj:p:v_zna")

def test_numbered_entities():
    my_assert("Євро-2014", "Євро-2014/[Євро-2014]noun:inanim:n:v_dav:nv:prop|Євро-2014/[Євро-2014]noun:inanim:n:v_mis:nv:prop|Євро-2014/[Євро-2014]noun:inanim:n:v_naz:nv:prop|Євро-2014/[Євро-2014]noun:inanim:n:v_oru:nv:prop|Євро-2014/[Євро-2014]noun:inanim:n:v_rod:nv:prop|Євро-2014/[Євро-2014]noun:inanim:n:v_zna:nv:prop")
    my_assert("Ігри-2014", "Ігри-2014/[Гра-2014]noun:inanim:p:v_naz:prop|Ігри-2014/[Гра-2014]noun:inanim:p:v_zna:prop")
    my_assert("ЧЄ-2014", "ЧЄ-2014/[ЧЄ-2014]noun:inanim:m:v_dav:nv:abbr:prop|ЧЄ-2014/[ЧЄ-2014]noun:inanim:m:v_mis:nv:abbr:prop|ЧЄ-2014/[ЧЄ-2014]noun:inanim:m:v_naz:nv:abbr:prop|ЧЄ-2014/[ЧЄ-2014]noun:inanim:m:v_oru:nv:abbr:prop|ЧЄ-2014/[ЧЄ-2014]noun:inanim:m:v_rod:nv:abbr:prop|ЧЄ-2014/[ЧЄ-2014]noun:inanim:m:v_zna:nv:abbr:prop")
    my_assert("Лондон-2014", "Лондон-2014/[Лондон-2014]noun:inanim:m:v_naz:prop|Лондон-2014/[Лондон-2014]noun:inanim:m:v_zna:prop")
    my_assert("Афіни-2014", "Афіни-2014/[Афіни-2014]noun:inanim:p:v_naz:ns:prop|Афіни-2014/[Афіни-2014]noun:inanim:p:v_zna:ns:prop")
    my_assert("Замок-2002", "Замок-2002/[Замок-2002]noun:inanim:m:v_naz:prop|Замок-2002/[Замок-2002]noun:inanim:m:v_zna:prop")
    my_assert("вибори-2002", "вибори-2002/[вибори-2002]noun:inanim:p:v_naz:ns|вибори-2002/[вибори-2002]noun:inanim:p:v_zna:ns")

    my_assert("Оскар-2021", "Оскар-2021/[Оскар-2021]noun:inanim:m:v_naz:prop|Оскар-2021/[Оскар-2021]noun:inanim:m:v_zna:prop")

    my_assert("Ан-140", "Ан-140/[Ан-140]noun:inanim:m:v_dav:nv|Ан-140/[Ан-140]noun:inanim:m:v_mis:nv|Ан-140/[Ан-140]noun:inanim:m:v_naz:nv|Ан-140/[Ан-140]noun:inanim:m:v_oru:nv|Ан-140/[Ан-140]noun:inanim:m:v_rod:nv|Ан-140/[Ан-140]noun:inanim:m:v_zna:nv|Ан-140/[Ан-140]noun:inanim:p:v_dav:nv|Ан-140/[Ан-140]noun:inanim:p:v_mis:nv|Ан-140/[Ан-140]noun:inanim:p:v_naz:nv|Ан-140/[Ан-140]noun:inanim:p:v_oru:nv|Ан-140/[Ан-140]noun:inanim:p:v_rod:nv|Ан-140/[Ан-140]noun:inanim:p:v_zna:nv")
    my_assert("ВАЗ-2104", "ВАЗ-2104/[ВАЗ-2104]noun:inanim:f:v_dav:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:f:v_mis:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:f:v_naz:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:f:v_oru:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:f:v_rod:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:f:v_zna:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:m:v_dav:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:m:v_mis:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:m:v_naz:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:m:v_oru:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:m:v_rod:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:m:v_zna:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:p:v_dav:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:p:v_mis:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:p:v_naz:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:p:v_oru:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:p:v_rod:nv|ВАЗ-2104/[ВАЗ-2104]noun:inanim:p:v_zna:nv")
    my_assert("Міг-21М", "Міг-21М/[Міг-21М]noun:inanim:m:v_dav:nv|Міг-21М/[Міг-21М]noun:inanim:m:v_mis:nv|Міг-21М/[Міг-21М]noun:inanim:m:v_naz:nv|Міг-21М/[Міг-21М]noun:inanim:m:v_oru:nv|Міг-21М/[Міг-21М]noun:inanim:m:v_rod:nv|Міг-21М/[Міг-21М]noun:inanim:m:v_zna:nv|Міг-21М/[Міг-21М]noun:inanim:p:v_dav:nv|Міг-21М/[Міг-21М]noun:inanim:p:v_mis:nv|Міг-21М/[Міг-21М]noun:inanim:p:v_naz:nv|Міг-21М/[Міг-21М]noun:inanim:p:v_oru:nv|Міг-21М/[Міг-21М]noun:inanim:p:v_rod:nv|Міг-21М/[Міг-21М]noun:inanim:p:v_zna:nv")
    #    my_assert("Площі–2006", "Площі–2006/[Площа-2006]noun:inanim:p:v_dav:ns:prop|Площі–2006/[Площа-2006]noun:inanim:p:v_mis:ns:prop|Площі–2006/[Площа-2006]noun:inanim:p:v_rod:ns:prop");

    my_assert("Ан-140-100", "Ан-140-100/[Ан-140-100]noun:inanim:m:v_dav:nv|Ан-140-100/[Ан-140-100]noun:inanim:m:v_mis:nv|Ан-140-100/[Ан-140-100]noun:inanim:m:v_naz:nv|Ан-140-100/[Ан-140-100]noun:inanim:m:v_oru:nv|Ан-140-100/[Ан-140-100]noun:inanim:m:v_rod:nv|Ан-140-100/[Ан-140-100]noun:inanim:m:v_zna:nv|Ан-140-100/[Ан-140-100]noun:inanim:p:v_dav:nv|Ан-140-100/[Ан-140-100]noun:inanim:p:v_mis:nv|Ан-140-100/[Ан-140-100]noun:inanim:p:v_naz:nv|Ан-140-100/[Ан-140-100]noun:inanim:p:v_oru:nv|Ан-140-100/[Ан-140-100]noun:inanim:p:v_rod:nv|Ан-140-100/[Ан-140-100]noun:inanim:p:v_zna:nv")

    my_assert("топ-10", "топ-10/[топ-10]noninfl:alt")


    my_assert("Формули-1", "Формули-1/[Формула-1]noun:inanim:f:v_rod:prop|Формули-1/[Формула-1]noun:inanim:p:v_naz:prop|Формули-1/[Формула-1]noun:inanim:p:v_zna:prop")
    my_assert("Карпати-2", "Карпати-2/[Карпати-2]noun:inanim:p:v_naz:ns:prop:geo|Карпати-2/[Карпати-2]noun:inanim:p:v_zna:ns:prop:geo")
    my_assert("ТЕЦ-1", "ТЕЦ-1/[ТЕЦ-1]noun:inanim:f:v_dav:nv|ТЕЦ-1/[ТЕЦ-1]noun:inanim:f:v_mis:nv|ТЕЦ-1/[ТЕЦ-1]noun:inanim:f:v_naz:nv|ТЕЦ-1/[ТЕЦ-1]noun:inanim:f:v_oru:nv|ТЕЦ-1/[ТЕЦ-1]noun:inanim:f:v_rod:nv|ТЕЦ-1/[ТЕЦ-1]noun:inanim:f:v_zna:nv")

    my_assert("омега-3", "омега-3/[омега-3]noninfl")

    my_assert("потік-2", "потік-2/[потік-2]noun:inanim:m:v_naz|потік-2/[потік-2]noun:inanim:m:v_zna")

    my_assert("СДПУ(о)", "СДПУ(о)/[СДПУ(о)]noun:inanim:f:v_dav:nv:abbr:prop|СДПУ(о)/[СДПУ(о)]noun:inanim:f:v_mis:nv:abbr:prop|СДПУ(о)/[СДПУ(о)]noun:inanim:f:v_naz:nv:abbr:prop|СДПУ(о)/[СДПУ(о)]noun:inanim:f:v_oru:nv:abbr:prop|СДПУ(о)/[СДПУ(о)]noun:inanim:f:v_rod:nv:abbr:prop|СДПУ(о)/[СДПУ(о)]noun:inanim:f:v_zna:nv:abbr:prop")
    #    my_assert("К°", "");

    assert_not_tagged("Берлін-7")

def test_dynamic_tagging_parts():
    my_assert("по-свинячому", "по-свинячому/[по-свинячому]adv")
    my_assert("по-сибірськи", "по-сибірськи/[по-сибірськи]adv")
    my_assert("по-абхазьки", "по-абхазьки/[по-абхазьки]adv")
    my_assert("по-авантурницьки", "по-авантурницьки/[по-авантурницьки]adv")

    my_assert("давай-но", "давай-но/[давати]verb:imperf:impr:s:2")
    my_assert("дивіться-но", "дивіться-но/[дивитися]verb:rev:imperf:impr:p:2")
    my_assert("гей-но", "гей-но/[гей]intj")
    my_assert("цить-но", "цить-но/[цить]intj")
    my_assert("хай-но", "хай-но/[хай]part")
    my_assert("бачиш-но", "бачиш-но/[бачити]verb:imperf:pres:s:2:insert")

    my_assert("той-таки", "той-таки/[той]adj:m:v_naz:pron:dem|той-таки/[той]adj:m:v_zna:rinanim:pron:dem|той-таки/[той]part")
    my_assert("буде-таки", "буде-таки/[бути]verb:imperf:futr:s:3")
    my_assert("там-таки", "там-таки/[там]adv:pron:dem|там-таки/[там]part")
    my_assert("зразу-таки", "зразу-таки/[зразу]adv")
    my_assert("першого-таки", "першого-таки/[перший]adj:m:v_rod:numr|першого-таки/[перший]adj:m:v_zna:ranim:numr|першого-таки/[перший]adj:n:v_rod:numr")
    my_assert("варто-таки", "варто-таки/[варто]noninfl:predic")
    #    my_assert("добряче-таки", "добряче-таки/[добряче]adv");

    my_assert("оцей-от", "оцей-от/[оцей]adj:m:v_naz:pron:dem|оцей-от/[оцей]adj:m:v_zna:rinanim:pron:dem")

    my_assert("ану-бо", "ану-бо/[ану]intj|ану-бо/[ану]part")
    my_assert("годі-бо", "годі-бо/[годі]adv:predic")

    my_assert("оттакий-то", "оттакий-то/[оттакий]adj:m:v_naz:pron:dem|оттакий-то/[оттакий]adj:m:v_zna:rinanim:pron:dem")
    my_assert("взагалі-то", "взагалі-то/[взагалі]adv:insert")
    my_assert("дуже-то", "дуже-то/[дуже]adv:compb|дуже-то/[дужий]adj:n:v_kly:compb|дуже-то/[дужий]adj:n:v_naz:compb|дуже-то/[дужий]adj:n:v_zna:compb")
    my_assert("десь-то", "десь-то/[десь]adv:pron:ind")  # TODO: :pron:ind
    my_assert("котрий-то", "котрий-то/[котрий]adj:m:v_naz:pron:int:rel|котрий-то/[котрий]adj:m:v_zna:rinanim:pron:int:rel")  # TODO: :pron:ind
    my_assert("ніби-то", "ніби-то/[ніби]conj:subord")
    my_assert("вони-то", "вони-то/[вони]noun:unanim:p:v_naz:pron:pers:3")
    my_assert("права-то", "права-то/[правий]adj:f:v_kly:compb|права-то/[правий]adj:f:v_naz:compb|права-то/[право]noun:inanim:n:v_rod|права-то/[право]noun:inanim:p:v_kly|права-то/[право]noun:inanim:p:v_naz|права-то/[право]noun:inanim:p:v_zna")

    my_assert("ти-ж", "ти-ж/[ти]noun:anim:s:v_kly:pron:pers:2:bad|ти-ж/[ти]noun:anim:s:v_naz:pron:pers:2:bad")
    my_assert("були-б", "були-б/[бути]verb:imperf:past:p:bad")
    assert_not_tagged("м-б")

    my_assert("був-єм", "був-єм/[бути]verb:imperf:past:m:arch")

    assert_not_tagged("хто-то")
    assert_not_tagged("що-то")
    #    assert_not_tagged("чи-то");
    assert_not_tagged("как-то")
    assert_not_tagged("кто-то")
    assert_not_tagged("до-пари")

def test_dynamic_tagging_vmisny():
    my_assert("Са-вмісні", "Са-вмісні/[Са-вмісний]adj:p:v_naz|Са-вмісні/[Са-вмісний]adj:p:v_zna:rinanim")
    my_assert("карбонат-вмісні", "карбонат-вмісні/[карбонат-вмісний]adj:p:v_naz|карбонат-вмісні/[карбонат-вмісний]adj:p:v_zna:rinanim")

def test_dynamic_tagging_xshaped():
    my_assert("Ш-подібному", "Ш-подібному/[Ш-подібний]adj:m:v_dav|Ш-подібному/[Ш-подібний]adj:m:v_mis|Ш-подібному/[Ш-подібний]adj:n:v_dav|Ш-подібному/[Ш-подібний]adj:n:v_mis")
    my_assert("S-подібної", "S-подібної/[S-подібний]adj:f:v_rod")
    my_assert("PR-складову", "PR-складову/[PR-складова]noun:inanim:f:v_zna")
    my_assert("VIP-батьків", "VIP-батьків/[VIP-батьки]noun:anim:p:v_rod:ns|VIP-батьків/[VIP-батьки]noun:anim:p:v_zna:ns|VIP-батьків/[VIP-батько]noun:anim:p:v_rod|VIP-батьків/[VIP-батько]noun:anim:p:v_zna")
    my_assert("COVID-вакцинованих", "COVID-вакцинованих/[COVID-вакцинований]adj:p:v_mis:adjp:pasv:imperf|COVID-вакцинованих/[COVID-вакцинований]adj:p:v_mis:adjp:pasv:perf|COVID-вакцинованих/[COVID-вакцинований]adj:p:v_rod:adjp:pasv:imperf|COVID-вакцинованих/[COVID-вакцинований]adj:p:v_rod:adjp:pasv:perf|COVID-вакцинованих/[COVID-вакцинований]adj:p:v_zna:ranim:adjp:pasv:imperf|COVID-вакцинованих/[COVID-вакцинований]adj:p:v_zna:ranim:adjp:pasv:perf")

def test_dynamic_tagging_prefixes():
    my_assert("VIP–будинок", "VIP-будинок/[VIP-будинок]noun:inanim:m:v_naz|VIP-будинок/[VIP-будинок]noun:inanim:m:v_zna|VIP–будинок/[null]null")
    my_assert("PR-департаменту", "PR-департаменту/[PR-департамент]noun:inanim:m:v_dav|PR-департаменту/[PR-департамент]noun:inanim:m:v_mis|PR-департаменту/[PR-департамент]noun:inanim:m:v_rod")
    my_assert("RPM-пакунок", "RPM-пакунок/[RPM-пакунок]noun:inanim:m:v_naz|RPM-пакунок/[RPM-пакунок]noun:inanim:m:v_zna")
    my_assert("3D-друк", "3D-друк/[3D-друк]noun:inanim:m:v_naz|3D-друк/[3D-друк]noun:inanim:m:v_zna")
    my_assert("n-векторний", "n-векторний/[n-векторний]adj:m:v_naz|n-векторний/[n-векторний]adj:m:v_zna:rinanim")
    my_assert("α-векторний", "α-векторний/[α-векторний]adj:m:v_naz|α-векторний/[α-векторний]adj:m:v_zna:rinanim")
    my_assert("α-діапазон", "α-діапазон/[α-діапазон]noun:inanim:m:v_naz|α-діапазон/[α-діапазон]noun:inanim:m:v_zna")

    my_assert("топ-десять", "топ-десять/[топ-десять]numr:p:v_naz:bad|топ-десять/[топ-десять]numr:p:v_zna:bad")
    #    my_assert("POS-термінальна", "");
    #    my_assert("IT-Академії", "IT-Академії/[IT-академія]noun:inanim:f:v_dav|IT-Академії/[IT-академія]noun:inanim:f:v_mis|IT-Академії/[IT-академія]noun:inanim:f:v_rod|IT-Академії/[IT-академія]noun:inanim:p:v_naz|IT-Академії/[IT-академія]noun:inanim:p:v_zna");

def test_name_suffix():
    my_assert("Мустафа-ага", "Мустафа-ага/[Мустафа-ага]noun:anim:m:v_naz:prop:fname")

def test_hypen_and_quote():
    my_assert("екс-«депутат»", "екс-«депутат»/[екс-депутат]noun:anim:m:v_naz:alt")
    my_assert("\"200\"-х", "\"200\"-х/[200-й]adj:p:v_mis:numr|\"200\"-х/[200-й]adj:p:v_rod:numr|\"200\"-х/[200-й]adj:p:v_zna:ranim:numr")
    my_assert("\"заступницю\"-колаборантку", "\"заступницю\"-колаборантку/[заступниця-колаборантка]noun:anim:f:v_zna")


def test_hypen_prefixes():
    my_assert("псевдо-ФОП", "псевдо-ФОП/[псевдо-ФОП]noun:anim:f:v_dav:nv:abbr|псевдо-ФОП/[псевдо-ФОП]noun:anim:f:v_mis:nv:abbr" + "|псевдо-ФОП/[псевдо-ФОП]noun:anim:f:v_naz:nv:abbr|псевдо-ФОП/[псевдо-ФОП]noun:anim:f:v_oru:nv:abbr" + "|псевдо-ФОП/[псевдо-ФОП]noun:anim:f:v_rod:nv:abbr|псевдо-ФОП/[псевдо-ФОП]noun:anim:f:v_zna:nv:abbr" + "|псевдо-ФОП/[псевдо-ФОП]noun:anim:m:v_naz:abbr|псевдо-ФОП/[псевдо-ФОП]noun:anim:p:v_dav:nv:abbr" + "|псевдо-ФОП/[псевдо-ФОП]noun:anim:p:v_mis:nv:abbr|псевдо-ФОП/[псевдо-ФОП]noun:anim:p:v_naz:nv:abbr" + "|псевдо-ФОП/[псевдо-ФОП]noun:anim:p:v_oru:nv:abbr|псевдо-ФОП/[псевдо-ФОП]noun:anim:p:v_rod:nv:abbr" + "|псевдо-ФОП/[псевдо-ФОП]noun:anim:p:v_zna:nv:abbr")


def test_dynamic_tagging_fixed_parts():
    my_assert("пів-України", "пів-України/[пів-України]noun:inanim:p:v_dav:prop:geo:nv:alt|пів-України/[пів-України]noun:inanim:p:v_mis:prop:geo:nv:alt" + "|пів-України/[пів-України]noun:inanim:p:v_naz:prop:geo:nv:alt|пів-України/[пів-України]noun:inanim:p:v_oru:prop:geo:nv:alt|пів-України/[пів-України]noun:inanim:p:v_rod:prop:geo:nv:alt" + "|пів-України/[пів-України]noun:inanim:p:v_zna:prop:geo:nv:alt" )

    my_assert("Пенсильванія-авеню", "Пенсильванія-авеню/[Пенсильванія-авеню]noun:inanim:f:v_dav:nv:prop|Пенсильванія-авеню/[Пенсильванія-авеню]noun:inanim:f:v_mis:nv:prop" + "|Пенсильванія-авеню/[Пенсильванія-авеню]noun:inanim:f:v_naz:nv:prop|Пенсильванія-авеню/[Пенсильванія-авеню]noun:inanim:f:v_oru:nv:prop|Пенсильванія-авеню/[Пенсильванія-авеню]noun:inanim:f:v_rod:nv:prop|Пенсильванія-авеню/[Пенсильванія-авеню]noun:inanim:f:v_zna:nv:prop" )
    my_assert("Уолл-стрит", "Уолл-стрит/[Уолл-стрит]noun:inanim:f:v_dav:nv:prop|Уолл-стрит/[Уолл-стрит]noun:inanim:f:v_mis:nv:prop|Уолл-стрит/[Уолл-стрит]noun:inanim:f:v_naz:nv:prop" + "|Уолл-стрит/[Уолл-стрит]noun:inanim:f:v_oru:nv:prop|Уолл-стрит/[Уолл-стрит]noun:inanim:f:v_rod:nv:prop|Уолл-стрит/[Уолл-стрит]noun:inanim:f:v_zna:nv:prop" )

    my_assert("пів-години", "пів-години/[пів-години]noun:inanim:p:v_dav:nv:bad|пів-години/[пів-години]noun:inanim:p:v_mis:nv:bad|пів-години/[пів-години]noun:inanim:p:v_naz:nv:bad|пів-години/[пів-години]noun:inanim:p:v_oru:nv:bad|пів-години/[пів-години]noun:inanim:p:v_rod:nv:bad|пів-години/[пів-години]noun:inanim:p:v_zna:nv:bad" )

def test_dynamic_missing_apostrophe():
    my_assert("зїзду", "зїзду/[з'їзд]noun:inanim:m:v_dav:bad|зїзду/[з'їзд]noun:inanim:m:v_mis:bad|зїзду/[з'їзд]noun:inanim:m:v_rod:bad")
    my_assert("обвязаний", "обвязаний/[обв'язаний]adj:m:v_kly:adjp:pasv:perf:bad|обвязаний/[обв'язаний]adj:m:v_naz:adjp:pasv:perf:bad|обвязаний/[обв'язаний]adj:m:v_zna:rinanim:adjp:pasv:perf:bad")
    my_assert("время", "время/[null]null")

def test_dynamic_missing_hyphen():
    my_assert("якогонебудь", "якогонебудь/[який-небудь]adj:m:v_rod:pron:int:rel:def:bad|якогонебудь/[який-небудь]adj:m:v_zna:ranim:pron:int:rel:def:bad|якогонебудь/[який-небудь]adj:n:v_rod:pron:int:rel:def:bad")
    my_assert("болнебудь", "болнебудь/[null]null")

def test_dynamic_tagging_piv():
    my_assert("півгодини-годину", "півгодини-годину/[півгодини-годину]noun:inanim:p:v_zna")

def test_dynamic_tagging_full_tag_match():

    my_assert("жило-було", "жило-було/[жити-бути]verb:imperf:past:n")
    my_assert("учиш-учиш", "учиш-учиш/[учити-учити]verb:imperf:pres:s:2")

    my_assert("а-а", "а-а/[а-а]intj")
    my_assert("Га-га", "Га-га/[га-га]intj")
    my_assert("кусь-кусь", "кусь-кусь/[кусь-кусь]noninfl:predic")
    my_assert("ось\u2013ось", "ось-ось/[ось-ось]adv|ось–ось/[null]null")
    my_assert("ось\u2011ось", "ось-ось/[ось-ось]adv")
    my_assert("Івано\u2013Франківськ", "Івано-Франківськ/[Івано-Франківськ]noun:inanim:m:v_naz:prop:geo|Івано-Франківськ/[Івано-Франківськ]noun:inanim:m:v_zna:prop:geo|Івано–Франківськ/[null]null")

    my_assert("вгору-вниз", "вгору-вниз/[вгору-вниз]adv")

    my_assert("Усе-усе", "Усе-усе/[увесь-увесь]adj:n:v_naz:pron:gen|Усе-усе/[увесь-увесь]adj:n:v_zna:pron:gen|Усе-усе/[усе-усе]adv|Усе-усе/[усе-усе]noun:inanim:n:v_naz:pron:gen|Усе-усе/[усе-усе]noun:inanim:n:v_zna:pron:gen")
    my_assert("всього-всього", "всього-всього/[ввесь-ввесь]adj:m:v_rod:pron:gen|всього-всього/[ввесь-ввесь]adj:m:v_zna:ranim:pron:gen|всього-всього/[ввесь-ввесь]adj:n:v_rod:pron:gen|всього-всього/[весь-весь]adj:m:v_rod:pron:gen|всього-всього/[весь-весь]adj:m:v_zna:ranim:pron:gen|всього-всього/[весь-весь]adj:n:v_rod:pron:gen" + "|всього-всього/[все-все]noun:inanim:n:v_rod:pron:gen|всього-всього/[всього-всього]adv")
    my_assert("Ка-КА", "Ка-КА/[null]null")

    my_assert("годину-півтори", "годину-півтори/[година-півтори]noun:inanim:f:v_zna|годину-півтори/[година-півтори]noun:inanim:p:v_zna")

    my_assert("вівторок-середа", "вівторок-середа/[вівторок-середа]noun:inanim:m:v_naz|вівторок-середа/[вівторок-середа]noun:inanim:p:v_naz")
    my_assert("лютого-березня", "лютого-березня/[лютий-березень]noun:inanim:m:v_rod|лютого-березня/[лютий-березень]noun:inanim:p:v_rod")


    # adv-adv
    my_assert("низенько-низенько", "низенько-низенько/[низенько-низенько]adv")

    #    my_assert("нічого-нічого", "нічого-нічого/[нічого-нічого]adv");

    my_assert("неприховано-вороже", "неприховано-вороже/[неприховано-вороже]adv")

    # adj-adj
    my_assert("такого-сякого", "такого-сякого/[такий-сякий]adj:m:v_rod:pron:def|такого-сякого/[такий-сякий]adj:m:v_zna:ranim:pron:def|такого-сякого/[такий-сякий]adj:n:v_rod:pron:def")
    my_assert("чорній-чорній", "чорній-чорній/[чорна-чорна]noun:anim:f:v_dav|чорній-чорній/[чорна-чорна]noun:anim:f:v_mis|чорній-чорній/[чорний-чорний]adj:f:v_dav|чорній-чорній/[чорний-чорний]adj:f:v_mis|чорній-чорній/[чорніти-чорніти]verb:imperf:impr:s:2")
    my_assert("писаного-переписаного", "писаного-переписаного/[писаний-переписаний]adj:m:v_rod:adjp:pasv:imperf|писаного-переписаного/[писаний-переписаний]adj:m:v_zna:ranim:adjp:pasv:imperf|писаного-переписаного/[писаний-переписаний]adj:n:v_rod:adjp:pasv:imperf")
    my_assert("минулого–позаминулого", "минулого-позаминулого/[минулий-позаминулий]adj:m:v_rod|минулого-позаминулого/[минулий-позаминулий]adj:m:v_zna:ranim|минулого-позаминулого/[минулий-позаминулий]adj:n:v_rod|минулого–позаминулого/[null]null")


    # noun-noun

    my_assert("дівчинка-дівчинка", "дівчинка-дівчинка/[дівчинка-дівчинка]noun:anim:f:v_naz")
    my_assert("лікар-гомеопат", "лікар-гомеопат/[лікар-гомеопат]noun:anim:m:v_naz")
    my_assert("лікаря-гомеопата", "лікаря-гомеопата/[лікар-гомеопат]noun:anim:m:v_rod|лікаря-гомеопата/[лікар-гомеопат]noun:anim:m:v_zna")
    my_assert("шмкр-гомеопат", "шмкр-гомеопат/[null]null")
    my_assert("лікар-ткр", "лікар-ткр/[null]null")
    my_assert("Жінка-Актриса", "Жінка-Актриса/[жінка-актриса]noun:anim:f:v_naz")

    my_assert("пане-товаришу", "пане-товаришу/[пан-товариш]noun:anim:m:v_kly|пане-товаришу/[паня-товариш]noun:anim:f:v_kly")

    my_assert("вчинок-приклад", "вчинок-приклад/[вчинок-приклад]noun:inanim:m:v_naz|вчинок-приклад/[вчинок-приклад]noun:inanim:m:v_zna")
    my_assert("міста-фортеці", "міста-фортеці/[місто-фортеця]noun:inanim:n:v_rod|міста-фортеці/[місто-фортеця]noun:inanim:p:v_naz|міста-фортеці/[місто-фортеця]noun:inanim:p:v_zna")

    # make sure lemma is lowercase
    my_assert("Інтернет-пошуковик", "Інтернет-пошуковик/[інтернет-пошуковик]noun:inanim:m:v_naz|Інтернет-пошуковик/[інтернет-пошуковик]noun:inanim:m:v_zna")

    #TODO: :p:ns -> lemma with :p
    #    my_assert("батьки-шляхтичі", "батьки-шляхтичі");
    #    my_assert("народом-дивотворцем", "");

    # TODO: unanim
    my_assert("ворог-стафілокок", "ворог-стафілокок/[null]null")
    my_assert("стафілокок-реагент", "стафілокок-реагент/[null]null")

    #TODO: бек, бег, ага, паша, хан
    #    my_assert("Каладжі-ага", "");
    my_assert("Каладжі-бей", "Каладжі-бей/[Каладжі-бей]noun:anim:m:v_naz:prop:fname")
    my_assert("Гасан-огли\u0301", "Гасан-огли/[Гасан-огли]noun:anim:m:v_naz:prop:fname")
    #    my_assert("капудан-паша", "два-чотири/[два-чотири]numr:v_naz|два-чотири/[два-чотири]numr:v_naz");
    #    my_assert("кальфа-ефенді", "два-чотири/[два-чотири]numr:v_naz|два-чотири/[два-чотири]numr:v_naz");

    my_assert("Москви-ріки", "Москви-ріки/[Москва-ріка]noun:inanim:f:v_rod:prop:geo|Москви-ріки/[москва-ріка]noun:inanim:f:v_rod:prop:geo:alt")
    my_assert("Кочубієва-Одеси", "Кочубієва-Одеси/[Кочубіїв-Одеса]noun:inanim:m:v_rod:prop:geo")

    my_assert("Дівчинка-першокласниця", "Дівчинка-першокласниця/[дівчинка-першокласниця]noun:anim:f:v_naz")

    my_assert("ненависть-шоу", "ненависть-шоу/[ненависть-шоу]noun:inanim:f:v_naz|ненависть-шоу/[ненависть-шоу]noun:inanim:f:v_zna")

    my_assert("Київ-Прага", "Київ-Прага/[Київ-Прага]noninfl:prop:geo")
    my_assert("Україна-ЄС", "Україна-ЄС/[Україна-ЄС]noninfl:prop")
    my_assert("Хуана-Карлоса", "Хуана-Карлоса/[Хуан-Карлос]noun:anim:m:v_rod:prop:fname|Хуана-Карлоса/[Хуан-Карлос]noun:anim:m:v_zna:prop:fname")
    # подружжя, сім'я, пара
    my_assert("Карпа-Хансен", "Карпа-Хансен/[Карпа-Хансен]noninfl:prop:lname")
    my_assert("Джолі-Пітт", "Джолі-Пітт/[Джолі-Пітт]noninfl:prop:lname")
    my_assert("Джеймса-Веніка", "Джеймса-Веніка/[Джеймса-Веніка]noninfl:prop:lname")
    my_assert("БАЛОГИ-КОЛЕСНІКОВА", "БАЛОГИ-КОЛЕСНІКОВА/[Балоги-Колеснікова]noninfl:prop:lname")
    my_assert("Івана-Павла", "Івана-Павла/[Іван-Павло]noun:anim:m:v_rod:prop:fname|Івана-Павла/[Іван-Павло]noun:anim:m:v_zna:prop:fname")

    # handled by different logic
    #    assert_not_tagged("напів-люкс");
    assert_not_tagged("Малишко-це")
    assert_not_tagged("відносини-коли")
    assert_not_tagged("лісо-та")
    assert_not_tagged("Ліс-наш")
    assert_not_tagged("Нью-Париж")
    assert_not_tagged("кохання-найщиріше")  # - мало би бути тире
    assert_not_tagged("Донець-кий")
    assert_not_tagged("мас-штаби")
    assert_not_tagged("підо-пічні")
    assert_not_tagged("рибо-полювання")
    assert_not_tagged("вовіки-вічні")
    #    assert_not_tagged("юре-юре");
    assert_not_tagged("Гірник-спорт")

    assert_not_tagged("Квітку-Основ'яненко")  # правильно: Квітку-Основ'яненка

def test_dynamic_tagging_intj():
    my_assert("Гей-гей-гей", "Гей-гей-гей/[гей-гей-гей]intj")
    my_assert("Ого-го-го-го", "Ого-го-го-го/[ого-го-го-го]intj")
    my_assert("фу-фу", "фу-фу/[фу-фу]intj")

    #TODO:
    #  my_assert("як-як", "");

    #TODO:
    assert_not_tagged("йо-йо-тусовки")

def test_compound_upper_case():
    # dictionary only has "соціал-демократичний" and LT only uppercases first letter
    my_assert("Соціал-Демократичний", "Соціал-Демократичний/[соціал-демократичний]adj:m:v_kly|Соціал-Демократичний/[соціал-демократичний]adj:m:v_naz|Соціал-Демократичний/[соціал-демократичний]adj:m:v_zna:rinanim")
    my_assert("Івано-Франківська", "Івано-Франківська/[Івано-Франківськ]noun:inanim:m:v_rod:prop:geo|Івано-Франківська/[івано-франківський]adj:f:v_kly|Івано-Франківська/[івано-франківський]adj:f:v_naz")
    my_assert("Івано-Франківської", "Івано-Франківської/[івано-франківський]adj:f:v_rod")
    my_assert("Переяслав-Хмельницького", "Переяслав-Хмельницького/[переяслав-хмельницький]adj:m:v_rod|Переяслав-Хмельницького/[переяслав-хмельницький]adj:m:v_zna:ranim|Переяслав-Хмельницького/[переяслав-хмельницький]adj:n:v_rod")
    # bad removed later in disambig
    my_assert("Південно-Західній", "Південно-Західній/[південно-західний]adj:f:v_dav|Південно-Західній/[південно-західний]adj:f:v_mis" + "|Південно-Західній/[південно-західній]adj:f:v_dav:bad:err|Південно-Західній/[південно-західній]adj:f:v_mis:bad:err|Південно-Західній/[південно-західній]adj:m:v_kly:bad:err|Південно-Західній/[південно-західній]adj:m:v_naz:bad:err|Південно-Західній/[південно-західній]adj:m:v_zna:rinanim:bad:err")
    my_assert("Південно-Східної", "Південно-Східної/[південно-східний]adj:f:v_rod")

    my_assert("аль-Каїда", "Аль-Каїда/[Аль-Каїда]noun:inanim:f:v_naz:prop:bad")

def test_dynamic_tagging_full_others():
    # others

    #    my_assert("етно-диско", "етно-диско/[null]null");
    my_assert("екс-партнер", "екс-партнер/[екс-партнер]noun:anim:m:v_naz:alt")
    my_assert("еспресо-машина", "еспресо-машина/[еспресо-машина]noun:inanim:f:v_naz")
    my_assert("міні-БПЛА", "міні-БПЛА/[міні-БПЛА]noun:inanim:m:v_dav:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:m:v_mis:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:m:v_naz:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:m:v_oru:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:m:v_rod:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:m:v_zna:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:p:v_dav:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:p:v_mis:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:p:v_naz:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:p:v_oru:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:p:v_rod:nv:abbr|міні-БПЛА/[міні-БПЛА]noun:inanim:p:v_zna:nv:abbr")
    my_assert("супер-Маріо", "супер-Маріо/[супер-Маріо]noun:anim:m:v_dav:nv:prop:fname|супер-Маріо/[супер-Маріо]noun:anim:m:v_kly:nv:prop:fname|супер-Маріо/[супер-Маріо]noun:anim:m:v_mis:nv:prop:fname|супер-Маріо/[супер-Маріо]noun:anim:m:v_naz:nv:prop:fname|супер-Маріо/[супер-Маріо]noun:anim:m:v_oru:nv:prop:fname|супер-Маріо/[супер-Маріо]noun:anim:m:v_rod:nv:prop:fname|супер-Маріо/[супер-Маріо]noun:anim:m:v_zna:nv:prop:fname")

    my_assert("кава-еспресо", "кава-еспресо/[кава-еспресо]noun:inanim:f:v_naz")
    my_assert("кави-еспресо", "кави-еспресо/[кава-еспресо]noun:inanim:f:v_rod|кави-еспресо/[кава-еспресо]noun:inanim:p:v_naz|кави-еспресо/[кава-еспресо]noun:inanim:p:v_zna")
    my_assert("програмою-максимум", "програмою-максимум/[програма-максимум]noun:inanim:f:v_oru")

    my_assert("чарку-другу", "чарку-другу/[чарка-друга]noun:inanim:f:v_zna")

    # jr/sr

    my_assert("Алієва-старшого", "Алієва-старшого/[Алієв-старший]noun:anim:m:v_rod:prop:lname|Алієва-старшого/[Алієв-старший]noun:anim:m:v_zna:prop:lname")
    # test ranim/rinanim
    #    assert_not_tagged("Алієва-старший");
    #    assert_not_tagged("Алієв-старшого");

    assert_not_tagged("дер-жав")

def test_dynamic_tagging_invalid_left():
    assert_tagged("авіа-переліт", "авіа-переліт/[авіа-переліт]noun:inanim:m:v_naz:bad|авіа-переліт/[авіа-переліт]noun:inanim:m:v_zna:bad")
    assert_tagged("авто-салон", "авто-салон/[авто-салон]noun:inanim:m:v_naz:bad|авто-салон/[авто-салон]noun:inanim:m:v_zna:bad")
    assert_tagged("квазі-держави", "квазі-держави/[квазі-держава]noun:inanim:f:v_rod:bad|квазі-держави/[квазі-держава]noun:inanim:p:v_kly:bad|квазі-держави/[квазі-держава]noun:inanim:p:v_naz:bad|квазі-держави/[квазі-держава]noun:inanim:p:v_zna:bad")
    assert_tagged("мульти-візу", "мульти-візу/[мульти-віза]noun:inanim:f:v_zna:bad")
    assert_tagged("контр-міри", "контр-міри/[контр-міра]noun:inanim:f:v_rod:bad|контр-міри/[контр-міра]noun:inanim:p:v_kly:bad|контр-міри/[контр-міра]noun:inanim:p:v_naz:bad|контр-міри/[контр-міра]noun:inanim:p:v_zna:bad")
    assert_tagged("кіно-критика", "кіно-критика/[кіно-критик]noun:anim:m:v_rod:bad|кіно-критика/[кіно-критик]noun:anim:m:v_zna:bad|кіно-критика/[кіно-критика]noun:inanim:f:v_naz:bad")
    assert_tagged("древньо-римський", "древньо-римський/[древньо-римський]adj:m:v_kly:bad|древньо-римський/[древньо-римський]adj:m:v_naz:bad|древньо-римський/[древньо-римський]adj:m:v_zna:rinanim:bad")
    assert_tagged("давньо-римський", "давньо-римський/[давньо-римський]adj:m:v_kly:bad|давньо-римський/[давньо-римський]adj:m:v_naz:bad|давньо-римський/[давньо-римський]adj:m:v_zna:rinanim:bad")
    # має бути "максимально можливу"
    assert_tagged("максимально-можливу", "максимально-можливу/[максимально-можливий]adj:f:v_zna:bad")
    assert_tagged("загально-правовий", "загально-правовий/[загально-правовий]adj:m:v_kly:bad|загально-правовий/[загально-правовий]adj:m:v_naz:bad|загально-правовий/[загально-правовий]adj:m:v_zna:rinanim:bad")
    assert_tagged("відео-навчання", "відео-навчання/[відео-навчання]noun:inanim:n:v_kly:bad|відео-навчання/[відео-навчання]noun:inanim:n:v_naz:bad|відео-навчання/[відео-навчання]noun:inanim:n:v_rod:bad|відео-навчання/[відео-навчання]noun:inanim:n:v_zna:bad|відео-навчання/[відео-навчання]noun:inanim:p:v_kly:bad|відео-навчання/[відео-навчання]noun:inanim:p:v_naz:bad|відео-навчання/[відео-навчання]noun:inanim:p:v_zna:bad")
    assert_tagged("В2В-рішень", "В2В-рішень/[В2В-рішення]noun:inanim:p:v_rod:bad")

    assert_tagged("кіно-Європа", "кіно-Європа/[кіно-Європа]noun:inanim:f:v_naz:prop:geo")
    assert_not_tagged("теле-та")
    assert_not_tagged("квазі-я")
    assert_not_tagged("макро-і")

def test_napiv():
    my_assert("напів-японка", "напів-японка/[напів-японка]noun:anim:f:v_naz:bad")
    my_assert("напів-Європа", "напів-Європа/[напів-Європа]noun:inanim:f:v_naz:prop:geo")
    my_assert("напів'японка", "напів'японка/[напів'японка]noun:anim:f:v_naz")
    my_assert("напів\u2013фантастичних", "напів-фантастичних/[напів-фантастичний]adj:p:v_mis:bad|напів-фантастичних/[напів-фантастичний]adj:p:v_rod:bad|напів-фантастичних/[напів-фантастичний]adj:p:v_zna:ranim:bad|напів–фантастичних/[null]null")
    my_assert("напівпольської-напіванглійської", "напівпольської-напіванглійської/[напівпольська-напіванглійська]noun:inanim:f:v_rod|напівпольської-напіванглійської/[напівпольський-напіванглійський]adj:f:v_rod")
    my_assert("напівбілоруски-напівукраїнки", "напівбілоруски-напівукраїнки/[напівбілоруска-напівукраїнка]noun:anim:f:v_rod|напівбілоруски-напівукраїнки/[напівбілоруска-напівукраїнка]noun:anim:p:v_kly|напівбілоруски-напівукраїнки/[напівбілоруска-напівукраїнка]noun:anim:p:v_naz|напівбілоруски-напівукраїнки/[напівбілоруска-напівукраїнка]noun:anim:p:v_zna:rare")
    #    my_assert("красунями-напівптахами", "");


def test_dynamic_tagging_no_dash():
    my_assert("Лангштрассе", "Лангштрассе/[Лангштрассе]noun:inanim:f:v_dav:nv:prop:alt|Лангштрассе/[Лангштрассе]noun:inanim:f:v_mis:nv:prop:alt" + "|Лангштрассе/[Лангштрассе]noun:inanim:f:v_naz:nv:prop:alt|Лангштрассе/[Лангштрассе]noun:inanim:f:v_oru:nv:prop:alt|Лангштрассе/[Лангштрассе]noun:inanim:f:v_rod:nv:prop:alt|Лангштрассе/[Лангштрассе]noun:inanim:f:v_zna:nv:prop:alt")

    my_assert("Єнукідзе", "Єнукідзе/[Єнукідзе]noun:inanim:f:v_dav:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:f:v_mis:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:f:v_naz:nv:prop:lname" + "|Єнукідзе/[Єнукідзе]noun:inanim:f:v_oru:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:f:v_rod:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:f:v_zna:nv:prop:lname" + "|Єнукідзе/[Єнукідзе]noun:inanim:m:v_dav:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:m:v_mis:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:m:v_naz:nv:prop:lname" + "|Єнукідзе/[Єнукідзе]noun:inanim:m:v_oru:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:m:v_rod:nv:prop:lname|Єнукідзе/[Єнукідзе]noun:inanim:m:v_zna:nv:prop:lname" )

    my_assert("антиаденовірусну", "антиаденовірусну/[антиаденовірусний]adj:f:v_zna")
    my_assert("транс'ядерний", "транс'ядерний/[транс'ядерний]adj:m:v_kly|транс'ядерний/[транс'ядерний]adj:m:v_naz|транс'ядерний/[транс'ядерний]adj:m:v_zna:rinanim")
    my_assert("напівядерний", "напівядерний/[напівядерний]adj:m:v_kly:bad|напівядерний/[напівядерний]adj:m:v_naz:bad|напівядерний/[напівядерний]adj:m:v_zna:rinanim:bad")
    my_assert("ексюрист", "ексюрист/[ексюрист]noun:anim:m:v_naz:bad")
    my_assert("екс'прес", "екс'прес/[null]null")

    my_assert("напівяпонка", "напівяпонка/[напів'японка]noun:anim:f:v_naz:bad")
    my_assert("Напівсправедливий", "Напівсправедливий/[напівсправедливий]adj:m:v_kly|Напівсправедливий/[напівсправедливий]adj:m:v_naz|Напівсправедливий/[напівсправедливий]adj:m:v_zna:rinanim")
    my_assert("напіврозслабленого", "напіврозслабленого/[напіврозслаблений]adj:m:v_rod|напіврозслабленого/[напіврозслаблений]adj:m:v_zna:ranim|напіврозслабленого/[напіврозслаблений]adj:n:v_rod")

    my_assert("північноазіатський", "північноазіатський/[північноазіатський]adj:m:v_kly|північноазіатський/[північноазіатський]adj:m:v_naz|північноазіатський/[північноазіатський]adj:m:v_zna:rinanim")

    assert_not_tagged("авіамені")
    assert_not_tagged("антиЄвропа")
    assert_not_tagged("напіврозслабеному")  # typo
    assert_not_tagged("напіви")

def test_dynamic_tagging_adv_pre():
    my_assert("гірко-прегірко", "гірко-прегірко/[гірко-прегірко]adv")
    my_assert("великий-превеликий", "великий-превеликий/[великий-превеликий]adj:m:v_kly|великий-превеликий/[великий-превеликий]adj:m:v_naz|великий-превеликий/[великий-превеликий]adj:m:v_zna:rinanim")
    my_assert("круглого-прекруглого", "круглого-прекруглого/[круглий-прекруглий]adj:m:v_rod|круглого-прекруглого/[круглий-прекруглий]adj:m:v_zna:ranim|круглого-прекруглого/[круглий-прекруглий]adj:n:v_rod")


def test_dynamic_tagging_owith_adj():
    # adv-adj

    my_assert("патолого-анатомічний", "патолого-анатомічний/[патолого-анатомічний]adj:m:v_kly|патолого-анатомічний/[патолого-анатомічний]adj:m:v_naz|патолого-анатомічний/[патолого-анатомічний]adj:m:v_zna:rinanim")

    assert_not_tagged("паталого-анатомічний")
    assert_not_tagged("патолога-анатомічний")
    assert_not_tagged("патолого-гмкнх")
    assert_not_tagged("патолого-голова")

    my_assert("дво-триметровий", "дво-триметровий/[дво-триметровий]adj:m:v_kly|дво-триметровий/[дво-триметровий]adj:m:v_naz|дво-триметровий/[дво-триметровий]adj:m:v_zna:rinanim")
    my_assert("три-чотириметровий", "три-чотириметровий/[три-чотириметровий]adj:m:v_kly|три-чотириметровий/[три-чотириметровий]adj:m:v_naz|три-чотириметровий/[три-чотириметровий]adj:m:v_zna:rinanim")
    my_assert("три-річний", "три-річний/[три-річний]adj:m:v_kly:bad|три-річний/[три-річний]adj:m:v_naz:bad|три-річний/[три-річний]adj:m:v_zna:rinanim:bad")
    my_assert("п'яти-зірковий", "п'яти-зірковий/[п'яти-зірковий]adj:m:v_kly:bad|п'яти-зірковий/[п'яти-зірковий]adj:m:v_naz:bad|п'яти-зірковий/[п'яти-зірковий]adj:m:v_zna:rinanim:bad")

    # :bad
    #    my_assert("трьох-чотирьохметровий", "трьох-чотирьохметровий/[трьох-чотирьохметровий]adj:m:v_kly:bad|трьох-чотирьохметровий/[трьох-чотирьохметровий]adj:m:v_naz:bad|трьох-чотирьохметровий/[трьох-чотирьохметровий]adj:m:v_zna:rinanim:bad");
    #    my_assert("двох-сторонній", "двох-сторонній/[двох-сторонній]adj:f:v_dav:bad|двох-сторонній/[двох-сторонній]adj:f:v_mis:bad|двох-сторонній/[двох-сторонній]adj:m:v_kly:bad|двох-сторонній/[двох-сторонній]adj:m:v_naz:bad|двох-сторонній/[двох-сторонній]adj:m:v_zna:rinanim:bad");

    my_assert("Художньо-культурний", "Художньо-культурний/[художньо-культурний]adj:m:v_kly|Художньо-культурний/[художньо-культурний]adj:m:v_naz|Художньо-культурний/[художньо-культурний]adj:m:v_zna:rinanim")
    my_assert("сліпуче-яскравого", "сліпуче-яскравого/[сліпуче-яскравий]adj:m:v_rod|сліпуче-яскравого/[сліпуче-яскравий]adj:m:v_zna:ranim|сліпуче-яскравого/[сліпуче-яскравий]adj:n:v_rod")
    my_assert("україно-болгарський", "україно-болгарський/[україно-болгарський]adj:m:v_kly|україно-болгарський/[україно-болгарський]adj:m:v_naz|україно-болгарський/[україно-болгарський]adj:m:v_zna:rinanim")

    my_assert("учбово-спортивної", "учбово-спортивної/[учбово-спортивний]adj:f:v_rod:bad")

    my_assert("етико-філологічний", "етико-філологічний/[етико-філологічний]adj:m:v_kly|етико-філологічний/[етико-філологічний]adj:m:v_naz|етико-філологічний/[етико-філологічний]adj:m:v_zna:rinanim")

    my_assert("Альпійсько-Карпатського", "Альпійсько-Карпатського/[альпійсько-карпатський]adj:m:v_rod|Альпійсько-Карпатського/[альпійсько-карпатський]adj:m:v_zna:ranim|Альпійсько-Карпатського/[альпійсько-карпатський]adj:n:v_rod")
    my_assert("Азово-Чорноморського", "Азово-Чорноморського/[азово-чорноморський]adj:m:v_rod|Азово-Чорноморського/[азово-чорноморський]adj:m:v_zna:ranim|Азово-Чорноморського/[азово-чорноморський]adj:n:v_rod")

    assert_not_tagged("бірмюково-блакитний")
    assert_not_tagged("во-політичний")
    assert_not_tagged("о-політичний")

    assert_not_tagged("рово-часового")

    # don't allow dash when the words spelled together
    #    assert_not_tagged("внутрішньо-економічний");
    #    assert_not_tagged("високо-релевантною");
    #    assert_not_tagged("всесвітньо-відомі");

    # :bad - має бути без дефісу: "важконапрацьований", Західноудмуртський тощо

    my_assert("Західно-Удмуртської", "Західно-Удмуртської/[західно-удмуртський]adj:f:v_rod:bad" )

    my_assert("Кримсько-Татарський", "Кримсько-Татарський/[кримсько-татарський]adj:m:v_kly|Кримсько-Татарський/[кримсько-татарський]adj:m:v_kly:bad:err|Кримсько-Татарський/[кримсько-татарський]adj:m:v_naz|Кримсько-Татарський/[кримсько-татарський]adj:m:v_naz:bad:err|Кримсько-Татарський/[кримсько-татарський]adj:m:v_zna:rinanim|Кримсько-Татарський/[кримсько-татарський]adj:m:v_zna:rinanim:bad:err" )

    my_assert("внутрішньо-економічної", "внутрішньо-економічної/[внутрішньо-економічний]adj:f:v_rod:bad:err" )

    my_assert("всесвітньо-відомої", "всесвітньо-відомої/[всесвітньо-відомий]adj:f:v_rod:bad" )

    my_assert("Червоно-градського", "Червоно-градського/[червоно-градський]adj:m:v_rod:bad|Червоно-градського/[червоно-градський]adj:m:v_zna:ranim:bad|Червоно-градського/[червоно-градський]adj:n:v_rod:bad" )

    my_assert("важко-напрацьований", "важко-напрацьований/[важко-напрацьований]adj:m:v_kly:adjp:pasv:perf:bad|важко-напрацьований/[важко-напрацьований]adj:m:v_naz:adjp:pasv:perf:bad|важко-напрацьований/[важко-напрацьований]adj:m:v_zna:rinanim:adjp:pasv:perf:bad")

    #    my_assert("американо-блакитний", "американо-блакитний/[null]null");

    #    assert_not_tagged("льотно-посадкова"); - загубилося початкове "з". Але це не спинило тегувальника - чому?

    #    my_assert("дітей-сиріт", "дітей-сиріт/[діти-сироти]noun:anim:p:v_rod");
    #    my_assert("курей-бройлерів", "кури-бройлери");

    #    my_assert("еко-ресурсний", "еко-ресурсний/[еко-ресурсний]adj:m:v_kly|еко-ресурсний/[еко-ресурсний]adj:m:v_naz|еко-ресурсний/[еко-ресурсний]adj:m:v_zna:rinanim");

def test_dynamic_anim_inanim():
    my_assert("вчених-новаторів", "вчених-новаторів/[вчений-новатор]noun:anim:p:v_rod|вчених-новаторів/[вчений-новатор]noun:anim:p:v_zna")
    my_assert("країна-виробник", "країна-виробник/[країна-виробник]noun:inanim:f:v_naz")
    my_assert("банк-виробник", "банк-виробник/[банк-виробник]noun:inanim:m:v_naz|банк-виробник/[банк-виробник]noun:inanim:m:v_zna")
    my_assert("банки-агенти", "банки-агенти/[банк-агент]noun:inanim:p:v_naz|банки-агенти/[банк-агент]noun:inanim:p:v_zna|банки-агенти/[банка-агент]noun:inanim:p:v_naz|банки-агенти/[банка-агент]noun:inanim:p:v_zna")
    my_assert("місто-гігант", "місто-гігант/[місто-гігант]noun:inanim:n:v_naz|місто-гігант/[місто-гігант]noun:inanim:n:v_zna")
    my_assert("країни-агресори", "країни-агресори/[країна-агресор]noun:inanim:p:v_naz|країни-агресори/[країна-агресор]noun:inanim:p:v_zna")
    my_assert("поселення-гігант", "поселення-гігант/[поселення-гігант]noun:inanim:n:v_naz|поселення-гігант/[поселення-гігант]noun:inanim:n:v_zna")
    #    my_assert("бот-учитель", "бот-учитель/[бот-учитель]noun:inanim:m:v_naz|бот-учитель/[бот-учитель]noun:inanim:m:v_zna");

    my_assert("сонях-красень", "сонях-красень/[сонях-красень]noun:inanim:m:v_naz|сонях-красень/[сонях-красень]noun:inanim:m:v_zna")
    my_assert("красень-сонях", "красень-сонях/[красень-сонях]noun:inanim:m:v_naz|красень-сонях/[красень-сонях]noun:inanim:m:v_zna")
    my_assert("депутатів-привидів", "депутатів-привидів/[депутат-привид]noun:anim:p:v_rod|депутатів-привидів/[депутат-привид]noun:anim:p:v_zna")
    #    my_assert("дівчата-зірочки", "дівчата-зірочки/[дівчина-зірочка]noun:anim:p:v_naz");

    # про місяця-місяченька
    #  my_assert("бабці-Австрії",  "");
    # змагання зі слалому-гіганту
    # голосувати за Тимошенко-прем’єра

def test_tagging_multidash():
    my_assert("україно-румуно-болгарський", "україно-румуно-болгарський/[україно-румуно-болгарський]adj:m:v_kly|україно-румуно-болгарський/[україно-румуно-болгарський]adj:m:v_naz|україно-румуно-болгарський/[україно-румуно-болгарський]adj:m:v_zna:rinanim")
    my_assert("синьо-біло-чорному", "синьо-біло-чорному/[синьо-біло-чорний]adj:m:v_dav|синьо-біло-чорному/[синьо-біло-чорний]adj:m:v_mis|синьо-біло-чорному/[синьо-біло-чорний]adj:n:v_dav|синьо-біло-чорному/[синьо-біло-чорний]adj:n:v_mis")
    my_assert("синьо-біло-жовтий", "синьо-біло-жовтий/[синьо-біло-жовтий]adj:m:v_kly|синьо-біло-жовтий/[синьо-біло-жовтий]adj:m:v_naz|синьо-біло-жовтий/[синьо-біло-жовтий]adj:m:v_zna:rinanim")
    my_assert("українсько-англійсько-французьким", "українсько-англійсько-французьким/[українсько-англійсько-французький]adj:m:v_oru|українсько-англійсько-французьким/[українсько-англійсько-французький]adj:n:v_oru|українсько-англійсько-французьким/[українсько-англійсько-французький]adj:p:v_dav")
    my_assert("седативного-снодійного-антигістамінного", "седативного-снодійного-антигістамінного/[снодійний-антигістамінний]adj:m:v_rod|седативного-снодійного-антигістамінного/[снодійний-антигістамінний]adj:m:v_zna:ranim|седативного-снодійного-антигістамінного/[снодійний-антигістамінний]adj:n:v_rod")
    #    TestTools.myAssert ignores tokens with no letters, need to do manual steps here
    readings = _tagger().tag(tokenizer.tokenize("–---–"))
    assert [(r.token, [(t.lemma, t.pos_tag, t.whitespace_before) for t in r.readings]) for r in readings] == \
        [("–---–", [(None, None, False)])]

    assert_not_tagged("військо-во-політичний")

    # nouns are too complicated
    #  assert_not_tagged("етно-джаз-рок");

    # dash-prefix2
    my_assert("хіп-хоп-гуртом", "хіп-хоп-гуртом/[хіп-хоп-гурт]noun:inanim:m:v_oru:xp1|хіп-хоп-гуртом/[хіп-хоп-гурт]noun:inanim:m:v_oru:xp2")
    my_assert("он-лайн-навчання", "он-лайн-навчання/[он-лайн-навчання]noun:inanim:n:v_naz:bad|он-лайн-навчання/[он-лайн-навчання]noun:inanim:n:v_rod:bad|он-лайн-навчання/[он-лайн-навчання]noun:inanim:n:v_zna:bad|он-лайн-навчання/[он-лайн-навчання]noun:inanim:p:v_naz:bad|он-лайн-навчання/[он-лайн-навчання]noun:inanim:p:v_zna:bad")

    #  assert_not_tagged("р--електронами");


def test_hypen_stretch():
    #    my_assert("ду-у-у-же", "ду-у-у-же/[дуже]adv:compb:coll|ду-у-у-же/[дужий]adj:n:v_kly:compb:coll|ду-у-у-же/[дужий]adj:n:v_naz:compb:coll|ду-у-у-же/[дужий]adj:n:v_zna:compb:coll");
    #    my_assert("ду-у-у-уже", "ду-у-у-уже/[дуже]adv:compb:coll|ду-у-у-уже/[дужий]adj:n:v_kly:compb:coll|ду-у-у-уже/[дужий]adj:n:v_naz:compb:coll|ду-у-у-уже/[дужий]adj:n:v_zna:compb:coll");
    my_assert("Та-а-ак", "Та-а-ак/[так]adv:pron:dem:alt|Та-а-ак/[так]conj:coord:alt|Та-а-ак/[так]conj:subord:alt|Та-а-ак/[так]part:alt")
    my_assert("Му-у-у", "Му-у-у/[му]noninfl:onomat:predic:alt")
    my_assert("С-с-с-лава", "С-с-с-лава/[Слава]noun:anim:f:v_naz:prop:fname:alt|С-с-с-лава/[Слава]noun:anim:m:v_naz:prop:fname:alt|С-с-с-лава/[Слава]noun:inanim:f:v_naz:prop:geo:alt|С-с-с-лава/[слава]noun:inanim:f:v_naz:alt")
    my_assert("ва-ре-ни-ки", "ва-ре-ни-ки/[вареник]noun:inanim:p:v_kly:alt|ва-ре-ни-ки/[вареник]noun:inanim:p:v_naz:alt|ва-ре-ни-ки/[вареник]noun:inanim:p:v_zna:alt")
    my_assert("ч-чо-л-ло-в-вік", "ч-чо-л-ло-в-вік/[чоловік]noun:anim:m:v_naz:alt|ч-чо-л-ло-в-вік/[чоловік]noun:anim:p:v_rod:subst:alt|ч-чо-л-ло-в-вік/[чоловік]noun:anim:p:v_zna:subst:alt")
    my_assert("Я-вор-рова", "Я-вор-рова/[Яворів]noun:inanim:m:v_rod:prop:geo:alt|Я-вор-рова/[яворовий]adj:f:v_kly:alt|Я-вор-рова/[яворовий]adj:f:v_naz:alt")
    # мілі- (з дефісом) є помилковим префіксом
    my_assert("мілі-ціо-нерів", "мілі-ціо-нерів/[null]null")

    my_assert("Тааак", "Тааак/[так]adv:pron:dem:alt|Тааак/[так]conj:coord:alt|Тааак/[так]conj:subord:alt|Тааак/[так]part:alt")
    my_assert("загубииилася", "загубииилася/[загубитися]verb:rev:perf:past:f:alt")

    my_assert("гаааа", "гаааа/[га]intj:alt")

    assert_not_tagged("ііі")
    #TODO:
    #    my_assert("та-ак", "");
    #      "Що-о"

    my_assert("з-зателефоную", "з-зателефоную/[зателефонувати]verb:perf:futr:s:1:alt")

    #    my_assert("відео-звер-нення", "");
    #TODO: should technically tag both lowercase and uppercase to get :fname as well
    #    my_assert("Да-а-ри", "");
    my_assert("т-то", "т-то/[null]null")

    assert_not_tagged("відео-конференц-зв'язком")
    assert_not_tagged("Шаабан")


def test_dynamic_tagging_skip():
    my_assert("г-г-г", "г-г-г/[null]null")
    my_assert("йо-га", "йо-га/[null]null")
    my_assert("с-г", "с-г/[null]null")
    my_assert("де-куди", "де-куди/[null]null")
    #    my_assert("чи-то", "чи-то/[null]null");
    #    my_assert("як-то", "як-то/[як-то]conj:subord:bad");

    my_assert("все-транс", "все-транс/[null]null")
    my_assert("транс-все", "транс-все/[null]null")
    assert_not_tagged("спа-салоне")

    assert_not_tagged("піт-стопою")

    assert_not_tagged("па-холка")

    # \n may happen in words when we have soft-hyphen wrap: \u00AD\n
    # in this case we strip \u00AD but leave \n in the word
    # but this may not happen often, need research if we need this
    #    my_assert("стін\nку", "");


def test_alt_spelling():
    my_assert("тренінґ", "тренінґ/[тренінґ]noun:inanim:m:v_naz:alt|тренінґ/[тренінґ]noun:inanim:m:v_zna:alt")
    my_assert("антирадіяційно", "антирадіяційно/[антирадіяційно]adv:alt")
    my_assert("фотометер", "фотометер/[фотометер]noun:inanim:m:v_naz:alt|фотометер/[фотометер]noun:inanim:m:v_zna:alt")
    my_assert("ідеольогічними", "ідеольогічними/[ідеольогічний]adj:p:v_oru:alt")
    my_assert("Мелітопольский", "Мелітопольский/[мелітопольский]adj:m:v_kly:bad|Мелітопольский/[мелітопольский]adj:m:v_naz:bad|Мелітопольский/[мелітопольский]adj:m:v_zna:rinanim:bad")
    #TODO:
    # сьпівати, сьвятинь тощо
    my_assert("сьвідомими", "сьвідомими/[сьвідомий]adj:p:v_oru:compb:arch")
    my_assert("сьвятинь", "сьвятинь/[сьвятиня]noun:inanim:p:v_rod:arch")

    my_assert("вДягнутися", "вДягнутися/[вдягнутися]verb:rev:perf:inf:alt")

    my_assert("зфотографував", "зфотографував/[зфотографувати]verb:perf:past:m:alt")
    my_assert("Зформувати", "Зформувати/[зформувати]verb:perf:inf:alt")

    assert_not_tagged("АвСтріях")
    assert_not_tagged("аВс")
    assert_not_tagged("вДягнУтися")

    assert_not_tagged("австріях")
    assert_not_tagged("польская")

def test_m2():
    my_assert("км2", "км/[км]noun:inanim:m:v_dav:nv:abbr|км/[км]noun:inanim:m:v_mis:nv:abbr|км/[км]noun:inanim:m:v_naz:nv:abbr|км/[км]noun:inanim:m:v_oru:nv:abbr|км/[км]noun:inanim:m:v_rod:nv:abbr|км/[км]noun:inanim:m:v_zna:nv:abbr|км/[км]noun:inanim:p:v_dav:nv:abbr|км/[км]noun:inanim:p:v_mis:nv:abbr|км/[км]noun:inanim:p:v_naz:nv:abbr|км/[км]noun:inanim:p:v_oru:nv:abbr|км/[км]noun:inanim:p:v_rod:nv:abbr|км/[км]noun:inanim:p:v_zna:nv:abbr -- 2/[2]number")
    my_assert("м3", "м/[м]noun:inanim:m:v_dav:nv:abbr|м/[м]noun:inanim:m:v_mis:nv:abbr|м/[м]noun:inanim:m:v_naz:nv:abbr|м/[м]noun:inanim:m:v_oru:nv:abbr|м/[м]noun:inanim:m:v_rod:nv:abbr|м/[м]noun:inanim:m:v_zna:nv:abbr|м/[м]noun:inanim:p:v_dav:nv:abbr|м/[м]noun:inanim:p:v_mis:nv:abbr|м/[м]noun:inanim:p:v_naz:nv:abbr|м/[м]noun:inanim:p:v_oru:nv:abbr|м/[м]noun:inanim:p:v_rod:nv:abbr|м/[м]noun:inanim:p:v_zna:nv:abbr -- 3/[3]number")
    #    my_assert("км2", "км2/[км2]noninfl");
    #    my_assert("мм²", "мм²/[мм²]noninfl");
    #    my_assert("7а", "7а/[7а]noninfl");

def test_bracketed_word():
    my_assert("д[окто]р[ом]", "д[окто]р[ом]/[доктор]noun:anim:m:v_oru:alt")
    my_assert("Акад[емія]", "Акад[емія]/[академія]noun:inanim:f:v_naz:alt")

def test_old_spelling():
    my_assert("дївчини", "дївчини/[дівчина]noun:anim:f:v_rod:alt|дївчини/[дівчина]noun:anim:p:v_kly:alt|дївчини/[дівчина]noun:anim:p:v_naz:alt|дївчини/[дівчина]noun:anim:p:v_zna:alt")

    #  @Test
    #  public void testSpecialChars() throws IOException {
    #    AnalyzedSentence analyzedSentence = new JLanguageTool(new Ukrainian()).getAnalyzedSentence("і карт\u00ADками.");
    #    String token = analyzedSentence.getTokens()[2].getToken();
    #    System.err.println(": " +analyzedSentence);
    #    System.err.println(": " +token);
    #    my_assert("і картками.", "");
    #  }


@pytest.mark.skip(reason="@Ignore in Java (the expected values are placeholders)")
def test_obscene_masked():
    my_assert("бл*ть", "бл*ть")
    my_assert("п#дарас", "п#дарас")

def test_special_chars():
    my_assert("П`єр", "П'єр/[П'єр]noun:anim:m:v_naz:prop:fname")
