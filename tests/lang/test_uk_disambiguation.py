"""Port of org.languagetool.tagging.disambiguation.uk.UkrainianHybridDisambiguationTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator, MultiWordChunker2
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.uk import helpers as lemma_helper
from langtool.lang.uk.disambiguation import SimpleDisambiguator, UkrainianHybridDisambiguator
from langtool.lang.uk.tokenizers import UkrainianWordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter

DEMO = DemoDisambiguator()


@pytest.fixture(autouse=True, scope='module')
def _dicts():
    require_dictionaries('uk')


def _language():
    return get_language('uk')


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _as_strings(readings):
    out = ['%s/[%s]%s' % (r.token, 'null' if r.lemma is None else r.lemma, 'null' if r.pos_tag is None else r.pos_tag)
           for r in readings]
    out.sort(key=lambda x: x.encode('utf-16-be', 'surrogatepass'))
    return out


def my_assert(text, expected, disambiguator=None):
    """TestTools.myAssert(input, expected, tokenizer, sentenceTokenizer,
    tagger, disambiguator) with the UkrainianWordTokenizer, the
    SRXSentenceTokenizer and the UkrainianTagger of Ukrainian (the
    UkrainianHybridDisambiguator by default)"""
    lang = _language()
    tagger = lang.tagger
    tokenizer = UkrainianWordTokenizer()
    sentence_tokenizer = SRXSentenceTokenizer(lang)
    if disambiguator is None:
        disambiguator = UkrainianHybridDisambiguator(lang)
    out = []
    for sentence in sentence_tokenizer.tokenize(text):
        tokens = tokenizer.tokenize(sentence)
        a_tokens = tagger.tag([t for t in tokens if _is_word(t)])
        token_array = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)]
        start_pos = 0
        no_whitespace_count = 0
        for token in tokens:
            if _is_word(token):
                pos_tag = a_tokens[no_whitespace_count]
                pos_tag.start_pos = start_pos
                no_whitespace_count += 1
            else:
                pos_tag = tagger.create_null_token(token, start_pos)
            token_array.append(pos_tag)
            start_pos += len(token)
        final_sentence = disambiguator.disambiguate(AnalyzedSentence(token_array))
        out.append(' '.join('|'.join(_as_strings(r.readings)) for r in final_sentence.tokens))
    assert ''.join(out) == expected


def test_disambiguator():
    """UkrainianHybridDisambiguationTest.testDisambiguator"""

    my_assert("Танцювати до впаду", "/[null]SENT_START Танцювати/[танцювати]verb:imperf:inf  /[null]null до/[до]prep  /[null]null " + "впаду/[впад]noun:inanim:m:v_dav|впаду/[впад]noun:inanim:m:v_rod|впаду/[впасти]verb:perf:futr:s:1:xp2")

    my_assert("Прийшла Люба додому.", "/[null]SENT_START Прийшла/[прийти]verb:perf:past:f|Прийшла/[прийшлий]adj:f:v_kly|Прийшла/[прийшлий]adj:f:v_naz  /[null]null Люба/[Люба]noun:anim:f:v_naz:prop:fname|Люба/[любий]adj:f:v_kly:compb|Люба/[любий]adj:f:v_naz:compb  /[null]null додому/[додому]adv ./[null]null", DEMO)

    my_assert("Прийшла Люба додому.", "/[null]SENT_START Прийшла/[прийти]verb:perf:past:f  /[null]null Люба/[Люба]noun:anim:f:v_naz:prop:fname  /[null]null додому/[додому]adv ./[null]null")

def test_disambiguator_dups():
    """UkrainianHybridDisambiguationTest.testDisambiguatorDups"""

    my_assert("підходу", "/[null]SENT_START підходу/[підхід]noun:inanim:m:v_dav|підходу/[підхід]noun:inanim:m:v_mis|підходу/[підхід]noun:inanim:m:v_rod")

def test_disambiguator_retag_fem_names():
    """UkrainianHybridDisambiguationTest.testDisambiguatorRetagFemNames"""
    #    німкеня Бахман була
    #    княгиня Кочубей перебудувала
    #    пані Грибан слухала
    #    Олександр П’ятниця метнув
    #    пані Сіроштан оприлюднила
    #    леді Черчилль передала
    #    поляк Дура швидко скоротив
    #    Анхель Ді Марія яскраво проявив
    # TODO:
    # ведучого ВВС Стівена Сакура принести
    # суд зобов’язав Олега Гаркота відшкодувати потерпілому
    # як не вмів Чіпріан Маріка реалізовувати моменти
    # TODO: non-v_naz

    my_assert("леді Черчилль була", "/[null]SENT_START" + " леді/[леді]noun:anim:f:v_dav:nv|леді/[леді]noun:anim:f:v_kly:nv|леді/[леді]noun:anim:f:v_mis:nv|леді/[леді]noun:anim:f:v_naz:nv|леді/[леді]noun:anim:f:v_oru:nv|леді/[леді]noun:anim:f:v_rod:nv|леді/[леді]noun:anim:f:v_zna:nv|леді/[леді]noun:anim:p:v_dav:nv|леді/[леді]noun:anim:p:v_kly:nv|леді/[леді]noun:anim:p:v_mis:nv|леді/[леді]noun:anim:p:v_naz:nv|леді/[леді]noun:anim:p:v_oru:nv|леді/[леді]noun:anim:p:v_rod:nv|леді/[леді]noun:anim:p:v_zna:nv" + "  /[null]null" + " Черчилль/[Черчилль]noun:anim:f:v_naz:prop:lname" + "  /[null]null" + " була/[бути]verb:imperf:past:f")

    #    my_assert("Олег П'ятниця метнув",
    #        "/[null]SENT_START"
    #        + " Олег/[Олег]noun:anim:m:v_naz:prop:fname"
    #        + "  /[null]null"
    #        + " П'ятниця/[П'ятниця]noun:anim:m:v_naz:prop:lname"
    #        + "  /[null]null"
    #        + " метнув/[метнути]verb:perf:past:m",
    #        tokenizer, sentenceTokenizer, tagger, disambiguator);

    my_assert("Віра Горобець метнула", "/[null]SENT_START" + " Віра/[Віра]noun:anim:f:v_naz:prop:fname" + "  /[null]null" + " Горобець/[Горобець]noun:anim:f:v_naz:prop:lname|Горобець/[Горобець]noun:anim:f:v_oru:nv:prop:lname|Горобець/[Горобець]noun:anim:f:v_zna:nv:prop:lname" + "  /[null]null" + " метнула/[метнути]verb:perf:past:f")

    my_assert("Віра Росії коштувала", "/[null]SENT_START Віра/[Віра]noun:anim:f:v_naz:prop:fname|Віра/[віра]intj|Віра/[віра]noun:inanim:f:v_naz  /[null]null Росії/[Росія]noun:inanim:f:v_dav:prop:geo|Росії/[Росія]noun:inanim:f:v_rod:prop:geo  /[null]null коштувала/[коштувати]verb:imperf:past:f")


def test_disambiguator_remove_vmis():
    """UkrainianHybridDisambiguationTest.testDisambiguatorRemoveVmis"""
    my_assert("У Зв'язку", "/[null]SENT_START У/[у]prep  /[null]null " + "Зв'язку/[зв'язка]noun:inanim:f:v_zna|Зв'язку/[зв'язок]noun:inanim:m:v_dav|Зв'язку/[зв'язок]noun:inanim:m:v_mis|Зв'язку/[зв'язок]noun:inanim:m:v_rod")

    my_assert("Зв'язку", "/[null]SENT_START " + "Зв'язку/[зв'язка]noun:inanim:f:v_zna|Зв'язку/[зв'язок]noun:inanim:m:v_dav|Зв'язку/[зв'язок]noun:inanim:m:v_rod")

    my_assert("нейтралітеті", "/[null]SENT_START " + "нейтралітеті/[нейтралітет]noun:inanim:m:v_mis")

    my_assert("— зовнішніх", "/[null]SENT_START " + "—/[null]null  /[null]null зовнішніх/[зовнішній]adj:p:v_mis|зовнішніх/[зовнішній]adj:p:v_rod|зовнішніх/[зовнішній]adj:p:v_zna:ranim")

    # TODO:
    my_assert("до зелені чортики", "/[null]SENT_START " + "до/[до]prep  /[null]null" + " зелені/[зелений]adj:p:v_naz:compb|зелені/[зелений]adj:p:v_zna:rinanim:compb|зелені/[зелень]noun:inanim:f:v_dav|зелені/[зелень]noun:inanim:f:v_rod|зелені/[зелені]noun:anim:p:v_naz:ns  /[null]null" + " чортики/[чортик]noun:anim:p:v_naz")

    my_assert("Харкові", "/[null]SENT_START " + "Харкові/[Харків]noun:inanim:m:v_mis:prop:geo")

    my_assert("з початку", "/[null]SENT_START " + "з/[з]prep  /[null]null " + "початку/[початок]noun:inanim:m:v_dav:xp1|початку/[початок]noun:inanim:m:v_dav:xp2|початку/[початок]noun:inanim:m:v_rod:xp2")

    # technically not related to v_mis but we can't test DIS_PROPER_NOUN_INSIDE_SENTENCE in xml as markup is removed in tests
    my_assert("<b>Чомусь", "/[null]SENT_START <b>/[null]null " + "Чомусь/[чомусь]adv:pron:ind|Чомусь/[щось]noun:inanim:n:v_dav:pron:ind")

def test_disambiguator_for_inanim_vkly():
    """UkrainianHybridDisambiguationTest.testDisambiguatorForInanimVKly"""

    my_assert("Поломане крило", "/[null]SENT_START Поломане/[поломаний]adj:n:v_kly:adjp:pasv:perf|Поломане/[поломаний]adj:n:v_naz:adjp:pasv:perf|Поломане/[поломаний]adj:n:v_zna:adjp:pasv:perf" + "  /[null]null крило/[крило]noun:inanim:n:v_naz|крило/[крило]noun:inanim:n:v_zna|крило/[крити]verb:imperf:past:n")

    my_assert("більше того,", "/[null]SENT_START більше/[більше]adv:compc:predic" + "  /[null]null того/[те]noun:inanim:n:v_rod:pron:dem|того/[той]adj:m:v_rod:pron:dem|того/[той]adj:m:v_zna:ranim:pron:dem|того/[той]adj:n:v_rod:pron:dem" + " ,/[null]null")

    my_assert("І до", "/[null]SENT_START" + " І/[і]conj:coord|І/[і]part  /[null]null" + " до/[до]noun:inanim:n:v_dav:nv|до/[до]noun:inanim:n:v_naz:nv|до/[до]noun:inanim:n:v_oru:nv|до/[до]noun:inanim:n:v_rod:nv" + "|до/[до]noun:inanim:n:v_zna:nv|до/[до]noun:inanim:p:v_dav:nv|до/[до]noun:inanim:p:v_naz:nv|до/[до]noun:inanim:p:v_oru:nv|до/[до]noun:inanim:p:v_rod:nv|до/[до]noun:inanim:p:v_zna:nv|до/[до]prep")

    #    my_assert("Такі різні фактори",
    #        "/[null]SENT_START Такі/[такий]adj:p:v_naz:pron:dem|Такі/[такий]adj:p:v_zna:rinanim:pron:dem"
    #        + "  /[null]null різні/[різний]adj:p:v_kly:compb|різні/[різний]adj:p:v_naz:compb|різні/[різний]adj:p:v_zna:rinanim:compb"
    #        + "  /[null]null фактори/[фактор]noun:anim:p:v_kly|фактори/[фактор]noun:anim:p:v_naz|фактори/[фактор]noun:inanim:p:v_naz|фактори/[фактор]noun:inanim:p:v_zna",
    #        tokenizer, sentenceTokenizer, tagger, disambiguator);

    # still v_kly
    my_assert("Мій лемківський краю...", "/[null]SENT_START Мій/[мій]adj:m:v_kly:pron:pos|Мій/[мій]adj:m:v_naz:pron:pos|Мій/[мій]adj:m:v_zna:rinanim:pron:pos  /[null]null" + " лемківський/[лемківський]adj:m:v_kly|лемківський/[лемківський]adj:m:v_naz|лемківський/[лемківський]adj:m:v_zna:rinanim  /[null]null" + " краю/[край]noun:inanim:m:v_dav|краю/[край]noun:inanim:m:v_kly|краю/[край]noun:inanim:m:v_rod .../[null]null")

    my_assert("Ясний місяцю!", "/[null]SENT_START Ясний/[ясний]adj:m:v_kly:compb|Ясний/[ясний]adj:m:v_naz:compb|Ясний/[ясний]adj:m:v_zna:rinanim:compb" +"  /[null]null місяцю/[місяць]noun:inanim:m:v_dav|місяцю/[місяць]noun:inanim:m:v_kly !/[null]null")

    my_assert("Мій Львове", "/[null]SENT_START Мій/[мій]adj:m:v_kly:pron:pos|Мій/[мій]adj:m:v_naz:pron:pos|Мій/[мій]adj:m:v_zna:rinanim:pron:pos" + "  /[null]null Львове/[Львів]noun:inanim:m:v_kly:prop:geo")


def test_disambiguator_for_plural_names():
    """UkrainianHybridDisambiguationTest.testDisambiguatorForPluralNames"""
    my_assert("Всіляких Василів", "/[null]SENT_START Всіляких/[всілякий]adj:p:v_rod:pron:gen|Всіляких/[всілякий]adj:p:v_zna:ranim:pron:gen" + "  /[null]null Василів/[Василь]noun:anim:p:v_rod:prop:fname|Василів/[Василь]noun:anim:p:v_zna:prop:fname|Василів/[Василів]adj:m:v_naz|Василів/[Василів]adj:m:v_zna:rinanim" + "|Василів/[Василів]noun:anim:f:v_dav:nv:prop:lname|Василів/[Василів]noun:anim:f:v_naz:nv:prop:lname|Василів/[Василів]noun:anim:f:v_oru:nv:prop:lname|Василів/[Василів]noun:anim:f:v_rod:nv:prop:lname|Василів/[Василів]noun:anim:f:v_zna:nv:prop:lname" + "|Василів/[Василів]noun:anim:m:v_naz:prop:lname" + "|Василів/[Василів]noun:inanim:m:v_naz:prop:geo|Василів/[Василів]noun:inanim:m:v_zna:prop:geo")

    my_assert("2 Андрії", "/[null]SENT_START 2/[2]number" + "  /[null]null Андрії/[Андрій]noun:anim:p:v_naz:prop:fname")

    # pluarl names are rare and create FP for "Романи Крісті наповнені інтригою"
    #    my_assert("Юріїв Луценків",
    #        "/[null]SENT_START Юріїв/[Юрій]noun:anim:p:v_rod:prop:fname|Юріїв/[Юрій]noun:anim:p:v_zna:prop:fname"
    #        + "  /[null]null Луценків/[Луценки]noun:inanim:p:v_rod:ns:prop:geo|Луценків/[Луценко]noun:anim:p:v_rod:prop:lname|Луценків/[Луценко]noun:anim:p:v_zna:prop:lname",
    #        tokenizer, sentenceTokenizer, tagger, disambiguator);

    my_assert("Всіляких Фрейдів", "/[null]SENT_START Всіляких/[всілякий]adj:p:v_rod:pron:gen|Всіляких/[всілякий]adj:p:v_zna:ranim:pron:gen" + "  /[null]null Фрейдів/[Фрейд]noun:anim:p:v_rod:prop:lname|Фрейдів/[Фрейд]noun:anim:p:v_zna:prop:lname|Фрейдів/[Фрейдів]adj:m:v_naz|Фрейдів/[Фрейдів]adj:m:v_zna:rinanim")

    # untouched
    #      + " |Василів/[Василів]noun:anim:m:v_naz:prop:lname:xp1|Василів/[Василів]noun:inanim:m:v_naz:prop:xp2|Василів/[Василів]noun:inanim:m:v_zna:prop:xp2"
    my_assert("Василів автомобіль", "/[null]SENT_START Василів/[Василів]adj:m:v_kly|Василів/[Василів]adj:m:v_naz|Василів/[Василів]adj:m:v_zna:rinanim" + "|Василів/[Василів]noun:anim:f:v_dav:nv:prop:lname|Василів/[Василів]noun:anim:f:v_naz:nv:prop:lname|Василів/[Василів]noun:anim:f:v_oru:nv:prop:lname|Василів/[Василів]noun:anim:f:v_rod:nv:prop:lname|Василів/[Василів]noun:anim:f:v_zna:nv:prop:lname|Василів/[Василів]noun:anim:m:v_naz:prop:lname|Василів/[Василів]noun:inanim:m:v_naz:prop:geo|Василів/[Василів]noun:inanim:m:v_zna:prop:geo" + "  /[null]null автомобіль/[автомобіль]noun:inanim:m:v_naz|автомобіль/[автомобіль]noun:inanim:m:v_zna")

    my_assert("на Андрії", "/[null]SENT_START на/[на]prep" + "  /[null]null Андрії/[Андрій]noun:anim:m:v_mis:prop:fname")

    my_assert("Леонідів Кравчука та Кучму", "/[null]SENT_START Леонідів/[Леонід]noun:anim:p:v_rod:prop:fname|Леонідів/[Леонід]noun:anim:p:v_zna:prop:fname|Леонідів/[Леонідів]adj:m:v_kly|Леонідів/[Леонідів]adj:m:v_naz|Леонідів/[Леонідів]adj:m:v_zna:rinanim" + "  /[null]null Кравчука/[Кравчук]noun:anim:m:v_rod:prop:lname|Кравчука/[Кравчук]noun:anim:m:v_zna:prop:lname" + "  /[null]null та/[та]conj:coord|та/[та]part|та/[той]adj:f:v_naz:pron:dem  /[null]null Кучму/[Кучма]noun:anim:m:v_zna:prop:lname")

    my_assert("молодшого з Вікторів", "/[null]SENT_START молодшого/[молодший]adj:m:v_rod:compc|молодшого/[молодший]adj:m:v_zna:ranim:compc|молодшого/[молодший]adj:n:v_rod:compc" + "  /[null]null з/[з]prep" + "  /[null]null Вікторів/[Віктор]noun:anim:p:v_rod:prop:fname|Вікторів/[Віктор]noun:anim:p:v_zna:prop:fname|Вікторів/[Вікторів]adj:m:v_naz|Вікторів/[Вікторів]adj:m:v_zna:rinanim|Вікторів/[Вікторів]noun:inanim:m:v_naz:prop:geo|Вікторів/[Вікторів]noun:inanim:m:v_zna:prop:geo")

def test_disambiguator_for_initials():
    """UkrainianHybridDisambiguationTest.testDisambiguatorForInitials"""
    my_assert("Є.Бакуліна", "/[null]SENT_START" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert("Є.  Бакуліна", "/[null]SENT_START" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + "  /[null]null" + "  /[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert(" Є. Бакуліна", "/[null]SENT_START" + "  /[null]null" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + "  /[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert(" Є.\u00A0Бакуліна", "/[null]SENT_START" + "  /[null]null" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + " \u00A0/[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert("Є.Л.Бакуліна", "/[null]SENT_START" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + " Л./[Л.]noun:anim:f:v_kly:nv:abbr:prop:pname|Л./[Л.]noun:anim:f:v_naz:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_rod:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_zna:nv:abbr:prop:pname" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert(" Є. Л. Бакуліна", "/[null]SENT_START" + "  /[null]null" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + "  /[null]null" + " Л./[Л.]noun:anim:f:v_kly:nv:abbr:prop:pname|Л./[Л.]noun:anim:f:v_naz:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_rod:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_zna:nv:abbr:prop:pname" + "  /[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")

    my_assert("Бакуліна Є.", "/[null]SENT_START" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname" + "  /[null]null" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname")

    my_assert(" Бакуліна Є. Л.", "/[null]SENT_START" + "  /[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname" + "  /[null]null" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + "  /[null]null" + " Л./[Л.]noun:anim:f:v_kly:nv:abbr:prop:pname|Л./[Л.]noun:anim:f:v_naz:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_rod:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_zna:nv:abbr:prop:pname")

    my_assert("Є.Л. Бакуліна", "/[null]SENT_START" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + " Л./[Л.]noun:anim:f:v_kly:nv:abbr:prop:pname|Л./[Л.]noun:anim:f:v_naz:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_rod:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_zna:nv:abbr:prop:pname" + "  /[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname")


    my_assert(" Є. Л. Бакуліна і Г. К. Бакулін", "/[null]SENT_START" + "  /[null]null" + " Є./[Є.]noun:anim:f:v_naz:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_rod:nv:abbr:prop:fname|Є./[Є.]noun:anim:m:v_zna:nv:abbr:prop:fname" + "  /[null]null" + " Л./[Л.]noun:anim:f:v_kly:nv:abbr:prop:pname|Л./[Л.]noun:anim:f:v_naz:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_rod:nv:abbr:prop:pname|Л./[Л.]noun:anim:m:v_zna:nv:abbr:prop:pname" + "  /[null]null" + " Бакуліна/[Бакулін]noun:anim:m:v_rod:prop:lname|Бакуліна/[Бакулін]noun:anim:m:v_zna:prop:lname|Бакуліна/[Бакуліна]noun:anim:f:v_naz:prop:lname" + "  /[null]null" + " і/[і]conj:coord|і/[і]part" + "  /[null]null" + " Г./[Г.]noun:anim:m:v_naz:nv:abbr:prop:fname" + "  /[null]null" + " К./[К.]noun:anim:m:v_naz:nv:abbr:prop:pname" + "  /[null]null" + " Бакулін/[Бакулін]noun:anim:m:v_naz:prop:lname")

    my_assert("С. Макаров.", "/[null]SENT_START" + " С./[С.]noun:anim:m:v_naz:nv:abbr:prop:fname" + "  /[null]null" + " Макаров/[Макаров]noun:anim:m:v_naz:prop:lname|Макаров/[Макаров]noun:inanim:m:v_naz:prop:geo|Макаров/[Макаров]noun:inanim:m:v_zna:prop:geo" + " ./[null]null")

    my_assert("для О.Волкова Л.Кучма", "/[null]SENT_START" + " для/[для]prep" + "  /[null]null" + " О./[О.]noun:anim:f:v_naz:nv:abbr:prop:fname|О./[О.]noun:anim:m:v_rod:nv:abbr:prop:fname|О./[О.]noun:anim:m:v_zna:nv:abbr:prop:fname" + " Волкова/[Волков]noun:anim:m:v_rod:prop:lname|Волкова/[Волков]noun:anim:m:v_zna:prop:lname|Волкова/[Волкова]noun:anim:f:v_naz:prop:lname" + "  /[null]null" + " Л./[Л.]noun:anim:m:v_naz:nv:abbr:prop:fname" + " Кучма/[Кучма]noun:anim:m:v_naz:prop:lname")


    # make sure we don't choke on complex test
    my_assert("Комендант, преподобний С.\u00A0С. Мокітімі, був чудовою людиною.", "/[null]SENT_START Комендант/[Комендант]noun:anim:m:v_naz:prop:lname|Комендант/[комендант]noun:anim:m:v_naz ,/[null]null" +"  /[null]null" +" преподобний/[преподобний]adj:m:v_kly|преподобний/[преподобний]adj:m:v_naz|преподобний/[преподобний]adj:m:v_zna:rinanim" +"|преподобний/[преподобний]noun:anim:m:v_kly|преподобний/[преподобний]noun:anim:m:v_naz" +"  /[null]null" +" С./[null]noninfl:abbr" +" \u00A0/[null]null" +" С./[null]noninfl:abbr" +"  /[null]null" +" Мокітімі/[null]null ,/[null]null  /[null]null" +" був/[бути]verb:imperf:past:m  /[null]null чудовою/[чудовий]adj:f:v_oru:compb  /[null]null людиною/[людина]noun:anim:f:v_oru ./[null]null")

    my_assert("Є. Тахкк", "/[null]SENT_START" + " Є./[null]noninfl:abbr  /[null]null Тахкк/[null]null")

    my_assert("В. Іпа", "/[null]SENT_START" + " В./[null]noninfl:abbr  /[null]null Іпа/[null]null")

    my_assert("С. Гокінґ", "/[null]SENT_START" + " С./[С.]noun:anim:m:v_naz:nv:abbr:prop:fname" + "  /[null]null" + " Гокінґ/[Гокінґ]noun:anim:m:v_naz:prop:lname:alt")

    # nv:nv
    my_assert("А. Маслоу", "/[null]SENT_START" + " А./[А.]noun:anim:m:v_dav:nv:abbr:prop:fname|А./[А.]noun:anim:m:v_naz:nv:abbr:prop:fname|А./[А.]noun:anim:m:v_oru:nv:abbr:prop:fname|А./[А.]noun:anim:m:v_rod:nv:abbr:prop:fname|А./[А.]noun:anim:m:v_zna:nv:abbr:prop:fname" + "  /[null]null Маслоу/[Маслоу]noun:anim:m:v_dav:nv:prop:lname|Маслоу/[Маслоу]noun:anim:m:v_naz:nv:prop:lname|Маслоу/[Маслоу]noun:anim:m:v_oru:nv:prop:lname|Маслоу/[Маслоу]noun:anim:m:v_rod:nv:prop:lname|Маслоу/[Маслоу]noun:anim:m:v_zna:nv:prop:lname")


def test_disambiguator_remove():
    """UkrainianHybridDisambiguationTest.testDisambiguatorRemove"""

    my_assert("По кривій", "/[null]SENT_START По/[по]prep  /[null]null" + " кривій/[крива]noun:inanim:f:v_dav|кривій/[крива]noun:inanim:f:v_mis|кривій/[кривий]adj:f:v_dav:compb|кривій/[кривий]adj:f:v_mis:compb")

    my_assert("Попри", "/[null]SENT_START Попри/[попри]prep")

    my_assert("Орися", "/[null]SENT_START Орися/[Орися]noun:anim:f:v_naz:prop:fname")

    my_assert("Цікавим", "/[null]SENT_START Цікавим/[цікавий]adj:m:v_oru:compb|Цікавим/[цікавий]adj:n:v_oru:compb|Цікавим/[цікавий]adj:p:v_dav:compb")

    my_assert("Вадим", "/[null]SENT_START Вадим/[Вадим]noun:anim:m:v_naz:prop:fname")

def test_disambiguator_for_st():
    """UkrainianHybridDisambiguationTest.testDisambiguatorForSt"""
    my_assert("І за ст. 208", "/[null]SENT_START" + " І/[і]conj:coord|І/[і]part  /[null]null" + " за/[за]prep" + "  /[null]null" + " ст./[ст.]noun:inanim:f:v_dav:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_naz:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_oru:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_rod:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_zna:nv:abbr:xp1" + "  /[null]null 208/[208]number")

    my_assert("І за ст. ст. 208", "/[null]SENT_START" + " І/[і]conj:coord|І/[і]part  /[null]null" + " за/[за]prep" + "  /[null]null" + " ст./[ст.]noun:inanim:p:v_dav:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_dav:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_naz:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_naz:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_oru:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_oru:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_rod:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_rod:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_zna:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_zna:nv:abbr:xp2" + "  /[null]null" + " ст./[ст.]noun:inanim:p:v_dav:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_dav:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_naz:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_naz:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_oru:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_oru:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_rod:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_rod:nv:abbr:xp2|ст./[ст.]noun:inanim:p:v_zna:nv:abbr:xp1|ст./[ст.]noun:inanim:p:v_zna:nv:abbr:xp2" + "  /[null]null 208/[208]number")

    my_assert("у XIX ст.", "/[null]SENT_START" +  " у/[у]prep" + "  /[null]null" + " XIX/[XIX]number:latin" + "  /[null]null" + " ст./[ст.]noun:inanim:n:v_dav:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_mis:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_naz:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_oru:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_rod:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_zna:nv:abbr:xp2")

    my_assert("1 ст. ложка", "/[null]SENT_START" +  " 1/[1]number" + "  /[null]null" + " ст./[ст.]adj:f:v_dav:nv:abbr|ст./[ст.]adj:f:v_naz:nv:abbr|ст./[ст.]adj:f:v_oru:nv:abbr|ст./[ст.]adj:f:v_rod:nv:abbr|ст./[ст.]adj:f:v_zna:nv:abbr|ст./[ст.]adj:p:v_dav:nv:abbr|ст./[ст.]adj:p:v_naz:nv:abbr|ст./[ст.]adj:p:v_oru:nv:abbr|ст./[ст.]adj:p:v_rod:nv:abbr|ст./[ст.]adj:p:v_zna:ranim:nv:abbr|ст./[ст.]adj:p:v_zna:rinanim:nv:abbr" + "  /[null]null ложка/[ложка]noun:inanim:f:v_naz")

    my_assert("1 ст. сержант", "/[null]SENT_START" +  " 1/[1]number" + "  /[null]null" + " ст./[ст.]adj:m:v_dav:nv:abbr|ст./[ст.]adj:m:v_naz:nv:abbr|ст./[ст.]adj:m:v_oru:nv:abbr|ст./[ст.]adj:m:v_rod:nv:abbr|ст./[ст.]adj:m:v_zna:ranim:nv:abbr|ст./[ст.]adj:m:v_zna:rinanim:nv:abbr" + "  /[null]null сержант/[сержант]noun:anim:m:v_naz")

    my_assert("18 ст.", "/[null]SENT_START" + " 18/[18]number" + "  /[null]null" + " ст./[ст.]noun:inanim:f:v_dav:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_naz:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_oru:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_rod:nv:abbr:xp1|ст./[ст.]noun:inanim:f:v_zna:nv:abbr:xp1|ст./[ст.]noun:inanim:n:v_dav:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_naz:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_oru:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_rod:nv:abbr:xp2|ст./[ст.]noun:inanim:n:v_zna:nv:abbr:xp2")

    my_assert("18 мм рт. ст.", "/[null]SENT_START" + " 18/[18]number" + "  /[null]null" + " мм/[мм]noun:inanim:m:v_dav:nv:abbr|мм/[мм]noun:inanim:m:v_naz:nv:abbr|мм/[мм]noun:inanim:m:v_oru:nv:abbr|мм/[мм]noun:inanim:m:v_rod:nv:abbr|мм/[мм]noun:inanim:m:v_zna:nv:abbr|мм/[мм]noun:inanim:p:v_dav:nv:abbr|мм/[мм]noun:inanim:p:v_naz:nv:abbr|мм/[мм]noun:inanim:p:v_oru:nv:abbr|мм/[мм]noun:inanim:p:v_rod:nv:abbr|мм/[мм]noun:inanim:p:v_zna:nv:abbr" + "  /[null]null" + " рт./[рт.]adj:m:v_dav:nv:abbr|рт./[рт.]adj:m:v_naz:nv:abbr|рт./[рт.]adj:m:v_oru:nv:abbr|рт./[рт.]adj:m:v_rod:nv:abbr|рт./[рт.]adj:m:v_zna:rinanim:nv:abbr" + "  /[null]null" + " ст./[ст.]noun:inanim:m:v_dav:nv:abbr:xp3|ст./[ст.]noun:inanim:m:v_naz:nv:abbr:xp3|ст./[ст.]noun:inanim:m:v_oru:nv:abbr:xp3|ст./[ст.]noun:inanim:m:v_rod:nv:abbr:xp3|ст./[ст.]noun:inanim:m:v_zna:nv:abbr:xp3|ст./[ст.]noun:inanim:p:v_dav:nv:abbr:xp3|ст./[ст.]noun:inanim:p:v_naz:nv:abbr:xp3|ст./[ст.]noun:inanim:p:v_oru:nv:abbr:xp3|ст./[ст.]noun:inanim:p:v_rod:nv:abbr:xp3|ст./[ст.]noun:inanim:p:v_zna:nv:abbr:xp3")

def test_tagger_uppger_good_and_lower_bad():
    """UkrainianHybridDisambiguationTest.testTaggerUppgerGoodAndLowerBad"""
    my_assert("Держдепартамент", "/[null]SENT_START Держдепартамент/[Держдепартамент]noun:inanim:m:v_naz:prop|Держдепартамент/[Держдепартамент]noun:inanim:m:v_zna:prop")

    my_assert("держземагентства", "/[null]SENT_START держземагентства/[держземагентство]noun:inanim:n:v_rod:bad:err")


def test_tagging_for_upper_case_abbreviations():
    """UkrainianHybridDisambiguationTest.testTaggingForUpperCaseAbbreviations"""
    my_assert("ВНЗ", "/[null]SENT_START ВНЗ/[ВНЗ]noun:inanim:m:v_dav:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:m:v_naz:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:m:v_oru:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:m:v_rod:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:m:v_zna:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:p:v_dav:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:p:v_naz:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:p:v_oru:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:p:v_rod:nv:abbr|ВНЗ/[ВНЗ]noun:inanim:p:v_zna:nv:abbr")
    my_assert("АТО", "/[null]SENT_START АТО/[АТО]noun:inanim:f:v_dav:nv:abbr|АТО/[АТО]noun:inanim:f:v_naz:nv:abbr|АТО/[АТО]noun:inanim:f:v_oru:nv:abbr|АТО/[АТО]noun:inanim:f:v_rod:nv:abbr|АТО/[АТО]noun:inanim:f:v_zna:nv:abbr")

def test_pron_pos():
    """UkrainianHybridDisambiguationTest.testPronPos"""
    my_assert("його машина", "/[null]SENT_START його/[воно]noun:unanim:n:v_rod:pron:pers:3|його/[воно]noun:unanim:n:v_zna:pron:pers:3|його/[він]noun:unanim:m:v_rod:pron:pers:3|його/[він]noun:unanim:m:v_zna:pron:pers:3|його/[його]adj:f:v_naz:nv:pron:pos" + "  /[null]null машина/[машина]noun:inanim:f:v_naz")
    my_assert("машина його мами", "/[null]SENT_START машина/[машина]noun:inanim:f:v_naz" + "  /[null]null його/[воно]noun:unanim:n:v_rod:pron:pers:3|його/[воно]noun:unanim:n:v_zna:pron:pers:3|його/[він]noun:unanim:m:v_rod:pron:pers:3|його/[він]noun:unanim:m:v_zna:pron:pers:3|його/[його]adj:f:v_naz:nv:pron:pos|його/[його]adj:f:v_rod:nv:pron:pos|його/[його]adj:p:v_naz:nv:pron:pos" + "  /[null]null мами/[мама]noun:anim:f:v_rod|мами/[мама]noun:anim:p:v_naz")
    my_assert("прийняв її до уваги", "/[null]SENT_START прийняв/[прийняти]verb:perf:past:m" + "  /[null]null її/[вона]noun:unanim:f:v_rod:pron:pers:3|її/[вона]noun:unanim:f:v_zna:pron:pers:3" + "  /[null]null до/[до]prep  /[null]null уваги/[увага]noun:inanim:f:v_rod|уваги/[увага]noun:inanim:p:v_naz|уваги/[увага]noun:inanim:p:v_zna")


def test_yih():
    """UkrainianHybridDisambiguationTest.testYih"""
    my_assert("їх кількість.", "/[null]SENT_START" + " їх/[вони]noun:unanim:p:v_rod:pron:pers:3|їх/[вони]noun:unanim:p:v_zna:pron:pers:3" + "  /[null]null кількість/[кількість]noun:inanim:f:v_naz|кількість/[кількість]noun:inanim:f:v_zna" + " ./[null]null")

    my_assert("їх забули.", "/[null]SENT_START" + " їх/[вони]noun:unanim:p:v_rod:pron:pers:3|їх/[вони]noun:unanim:p:v_zna:pron:pers:3" + "  /[null]null забули/[забути]verb:perf:past:p" + " ./[null]null")

    my_assert("ми досліджуємо їх, вони", "/[null]SENT_START" + " ми/[ми]noun:anim:p:v_naz:pron:pers:1" + "  /[null]null досліджуємо/[досліджувати]verb:imperf:pres:p:1" + "  /[null]null їх/[вони]noun:unanim:p:v_rod:pron:pers:3|їх/[вони]noun:unanim:p:v_zna:pron:pers:3" + " ,/[null]null" + "  /[null]null вони/[вони]noun:unanim:p:v_naz:pron:pers:3")

    my_assert("Загнав їх у кут.", "/[null]SENT_START" + " Загнав/[загнати]verb:perf:past:m" + "  /[null]null їх/[вони]noun:unanim:p:v_rod:pron:pers:3|їх/[вони]noun:unanim:p:v_zna:pron:pers:3" + "  /[null]null у/[у]prep  /[null]null кут/[кут]noun:inanim:m:v_naz|кут/[кут]noun:inanim:m:v_zna" + " ./[null]null")

    my_assert("Загнав їх.", "/[null]SENT_START" + " Загнав/[загнати]verb:perf:past:m" + "  /[null]null їх/[вони]noun:unanim:p:v_rod:pron:pers:3|їх/[вони]noun:unanim:p:v_zna:pron:pers:3" + " ./[null]null")

    my_assert("що їх не знали", "/[null]SENT_START" + " що/[що]conj:subord|що/[що]noun:inanim:n:v_naz:pron:int:rel|що/[що]noun:inanim:n:v_zna:pron:int:rel" + "  /[null]null їх/[вони]noun:unanim:p:v_rod:pron:pers:3|їх/[вони]noun:unanim:p:v_zna:pron:pers:3" + "  /[null]null" + " не/[не]part" + "  /[null]null знали/[знати]verb:imperf:past:p")

    my_assert("Загнав його у кут.", "/[null]SENT_START" + " Загнав/[загнати]verb:perf:past:m" + "  /[null]null його/[воно]noun:unanim:n:v_rod:pron:pers:3|його/[воно]noun:unanim:n:v_zna:pron:pers:3|його/[він]noun:unanim:m:v_rod:pron:pers:3|його/[він]noun:unanim:m:v_zna:pron:pers:3" + "  /[null]null у/[у]prep  /[null]null кут/[кут]noun:inanim:m:v_naz|кут/[кут]noun:inanim:m:v_zna" + " ./[null]null")

    my_assert("примусили її сказати.", "/[null]SENT_START" + " примусили/[примусити]verb:perf:past:p" + "  /[null]null її/[вона]noun:unanim:f:v_rod:pron:pers:3|її/[вона]noun:unanim:f:v_zna:pron:pers:3" + "  /[null]null сказати/[сказати]verb:perf:inf" + " ./[null]null")

    my_assert("на його душу.", "/[null]SENT_START" + " на/[на]prep" + "  /[null]null його/[воно]noun:unanim:n:v_rod:pron:pers:3|його/[воно]noun:unanim:n:v_zna:pron:pers:3|його/[він]noun:unanim:m:v_rod:pron:pers:3|його/[він]noun:unanim:m:v_zna:pron:pers:3|його/[його]adj:f:v_zna:nv:pron:pos|його/[його]adj:m:v_dav:nv:pron:pos|його/[його]adj:m:v_mis:nv:pron:pos|його/[його]adj:m:v_rod:nv:pron:pos" + "  /[null]null душу/[душ]noun:inanim:m:v_dav|душу/[душ]noun:inanim:m:v_mis|душу/[душ]noun:inanim:m:v_rod|душу/[душа]noun:inanim:f:v_zna" + " ./[null]null")

    # TODO: ignore these
    #  та її не надто швидка хода
    # триватимуть його не дуже успішні реформи
    # Це була її не перша спроба

def test_simple_remove():
    """UkrainianHybridDisambiguationTest.testSimpleRemove"""
    my_assert("була", "/[null]SENT_START була/[бути]verb:imperf:past:f")
    my_assert("була-то", "/[null]SENT_START була-то/[бути]verb:imperf:past:f")


def test_disambiguator_remove_present_in_dictionary():
    """UkrainianHybridDisambiguationTest.testDisambiguatorRemovePresentInDictionary"""
    simple_disambiguator = SimpleDisambiguator()
    tagger = _language().tagger

    # make sure our disambiguation lines are valid lines in dictionary
    for key, token_matcher in simple_disambiguator.disambig_remove_map.items():
        tagged = tagger.tag([key])
        tagged_token = tagged[0]
        assert any(token_matcher.matches(r) for r in tagged_token.readings), \
            '%s not found in dictionary, tags: %s' % (key, tagged)

    for key, values in simple_disambiguator.disambig_dups_map.items():
        for lemma in [key] + list(values):
            tagged = tagger.tag([lemma])
            assert lemma_helper.has_lemma(tagged[0], [lemma]), '%s lemma not in dictionary' % lemma


def test_chunker():
    """UkrainianHybridDisambiguationTest.testChunker"""
    lt = JLanguageTool(_language())
    analyzed_sentence = lt.get_analyzed_sentence("Для  годиться.")
    chunker = MultiWordChunker2(_language().resource_path('uk/multiwords.txt'), allow_first_capitalized=True)
    disambiguated = chunker.disambiguate(analyzed_sentence)
    tokens = disambiguated.tokens

    assert "<adv>" in str(tokens[1].readings)
    assert "<adv>" in str(tokens[4].readings)


def test_ignored_characters():
    """UkrainianHybridDisambiguationTest.testIgnoredCharacters"""
    lt = JLanguageTool(_language())
    analyzed_sentence = lt.get_analyzed_sentence("Іва\u0301н Петро\u0301вич.")

    # TODO: fix disambiguator - it should be: Петро\u0301вич[Петрович...
    assert str(analyzed_sentence) == "<S> Іван[Іван/noun:anim:m:v_naz:prop:fname]" + " Петрович[Петрович/noun:anim:f:v_dav:nv:prop:lname,Петрович/noun:anim:f:v_naz:nv:prop:lname,Петрович/noun:anim:f:v_oru:nv:prop:lname,Петрович/noun:anim:f:v_rod:nv:prop:lname,Петрович/noun:anim:f:v_zna:nv:prop:lname,Петрович/noun:anim:m:v_naz:prop:lname,Петрович/noun:anim:m:v_naz:prop:pname]" + ".[</S>]"

    analyzed_sentence = lt.get_analyzed_sentence("\u0301")
    assert str(analyzed_sentence) == "<S> </S> "


def test_plural_prop():
    """UkrainianHybridDisambiguationTest.testPluralProp"""

    my_assert("дві Франції", "/[null]SENT_START " + "дві/[два]numr:p:v_naz|дві/[два]numr:p:v_zna  " + "/[null]null Франції/[Франція]noun:inanim:p:v_naz:prop:geo")

    my_assert("два Володьки", "/[null]SENT_START " + "два/[два]numr:p:v_naz|два/[два]numr:p:v_zna  " + "/[null]null Володьки/[Володька]noun:anim:p:v_naz:prop:fname")

    my_assert("два Бойка", "/[null]SENT_START " + "два/[два]numr:p:v_naz|два/[два]numr:p:v_zna  " + "/[null]null Бойка/[Бойко]noun:anim:p:v_naz:prop:lname")

    # don't handle yet
    #    my_assert("два Рима",
    #        "/[null]SENT_START "
    #        + "два/[два]numr:p:v_naz|два/[два]numr:p:v_zna  "
    #        + "/[null]null Рима/[Рим]noun:inanim:m:v_rod:prop:geo:xp1|Рима/[рим]noun:inanim:m:v_rod|Рима/[рима]noun:inanim:f:v_naz",
    #        tokenizer, sentenceTokenizer, tagger, disambiguator);

def test_verb_impr():
    """UkrainianHybridDisambiguationTest.testVerbImpr"""
    my_assert("подальші суди", "/[null]SENT_START" + " подальші/[подальший]adj:p:v_kly|подальші/[подальший]adj:p:v_naz|подальші/[подальший]adj:p:v_zna:rinanim" + "  /[null]null суди/[суд]noun:inanim:p:v_naz|суди/[суд]noun:inanim:p:v_zna")

def test_vkly_zvert():
    """UkrainianHybridDisambiguationTest.testVklyZvert"""
    my_assert("Шановні депутати!", "/[null]SENT_START" + " Шановні/[шановний]adj:p:v_kly:compb" + "  /[null]null депутати/[депутат]noun:anim:p:v_kly" + " !/[null]null")

    my_assert("— Шановні колеги!", "/[null]SENT_START" + " —/[null]null  /[null]null" + " Шановні/[шановний]adj:p:v_kly:compb" + "  /[null]null колеги/[колега]noun:anim:p:v_kly" + " !/[null]null")



