"""Port of org.languagetool.tagging.ru.RussianTaggerTest and
org.languagetool.synthesis.ru.RussianSynthesizerTest, plus checks of
RussianTagger (stress marks, "MayMissingYO"), RussianWordTokenizer and
RussianChunker (the expected chunk tags are the output of the Java
RussianChunker of LanguageTool)."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.lang.ru.tokenizers import RussianWordTokenizer
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ru')


@pytest.fixture(scope='module')
def tagger():
    return get_language('ru').tagger


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in r.readings))
           for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


# --- RussianTaggerTest ---

def test_dictionary(tagger):
    """RussianTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0


def test_tagger(tagger):
    """RussianTaggerTest.testTagger"""
    tokenizer = WordTokenizer()
    _my_assert('Все счастливые семьи похожи друг на друга,  каждая  несчастливая  семья несчастлива по-своему.',
               'Все/[весь]ADJ:MPR:PL:Nom|Все/[весь]ADJ:MPR:PL:V|Все/[все]PNN:PL:Nom|Все/[все]PNN:PL:V|'
               'Все/[все]PNN:Sin:Nom|Все/[все]PNN:Sin:V -- счастливые/[счастливый]ADJ:Posit:PL:Nom|'
               'счастливые/[счастливый]ADJ:Posit:PL:V -- семьи/[семья]NN:Inanim:Fem:PL:Nom|'
               'семьи/[семья]NN:Inanim:Fem:PL:V|семьи/[семья]NN:Inanim:Fem:Sin:R -- похожи/[похожий]ADJ:Short:PL -- '
               'друг/[друг]NN:Anim:Masc:Sin:Nom -- на/[на]PREP -- друга/[друг]NN:Anim:Masc:Sin:R|'
               'друга/[друг]NN:Anim:Masc:Sin:V -- каждая/[каждый]ADJ:MPR:Fem:Nom -- '
               'несчастливая/[несчастливый]ADJ:Posit:Fem:Nom -- семья/[семья]NN:Inanim:Fem:Sin:Nom -- '
               'несчастлива/[несчастливый]ADJ:Short:Fem -- по-своему/[по-своему]ADV', tokenizer, tagger)
    _my_assert('Все смешалось в доме Облонских.',
               'Все/[весь]ADJ:MPR:PL:Nom|Все/[весь]ADJ:MPR:PL:V|Все/[все]PNN:PL:Nom|Все/[все]PNN:PL:V|'
               'Все/[все]PNN:Sin:Nom|Все/[все]PNN:Sin:V -- смешалось/[смешаться]VB:Past:INTR:PFV:Neut -- в/[в]PREP -- '
               'доме/[дом]NN:Inanim:Masc:Sin:P -- Облонских/[null]null', tokenizer, tagger)
    _my_assert('Абдуллаевы', 'Абдуллаевы/[абдуллаев]NN:Fam:PL:Nom', tokenizer, tagger)
    _my_assert('блукать', 'блукать/[блукать]VB:INF:', tokenizer, tagger)


def _tag(tagger, word):
    atr = tagger.tag([word])[0]
    return atr.token, sorted((t.lemma, t.pos_tag) for t in atr.readings), [c.chunk_tag for c in atr.chunk_tags]


def test_stress_marks_and_may_missing_yo(tagger):
    """RussianTagger.tag: stress marks are removed (the token text changes),
    "ʼ" becomes "ъ", and words with "е" that are known with "ё" get the
    chunk tag MayMissingYO"""
    assert _tag(tagger, 'ежик') == ('ежик', [('ёжик', 'NN:Anim:Masc:Sin:Nom')], ['MayMissingYO'])
    assert _tag(tagger, 'Ежик')[2] == ['MayMissingYO']
    assert _tag(tagger, 'ёжик')[2] == []
    # a stressed word may not miss a "ё"
    assert _tag(tagger, 'е́жик') == ('ежик', [('ёжик', 'NN:Anim:Masc:Sin:Nom')], [])
    assert _tag(tagger, 'молоко́')[:2] == ('молоко', [('молоко', 'NN:Inanim:Neut:Sin:Nom'),
                                                      ('молоко', 'NN:Inanim:Neut:Sin:V')])
    assert _tag(tagger, 'молоко̀')[0] == 'молоко'
    assert _tag(tagger, 'обʼём')[:2] == _tag(tagger, 'объём')[:2] == (
        'объём', [('объём', 'NN:Inanim:Masc:Sin:Nom'), ('объём', 'NN:Inanim:Masc:Sin:V')])
    # no "ё" form known
    assert _tag(tagger, 'дерево')[2] == []
    # tokens of one character are not changed
    assert _tag(tagger, 'е') == ('е', [('е', 'NN:Inanim:Neut')], [])


# --- RussianSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string():
    """RussianSynthesizerTest.testSynthesizeString"""
    synth = get_language('ru').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('семья'), 'NN:Inanim:Fem:Sin:Nom') == ['семья']
    assert synth.synthesize(_dummy_token('семья'), 'NN:Inanim:Fem:Sin:R') == ['семьи']


# --- RussianWordTokenizer ---

def test_word_tokenize():
    tokenizer = RussianWordTokenizer()
    assert tokenizer.tokenize('Товар б/у и б/н.') == ['Товар', ' ', 'б/у', ' ', 'и', ' ', 'б/н', '.']
    # the apostrophe and the period are tokenizing characters, a period after a space stays attached to
    # the following text (but not " . " and " .. ")
    assert tokenizer.tokenize("Д'Артаньян") == ['Д', "'", 'Артаньян']
    assert tokenizer.tokenize('Это .. тест . а .5 и т.д.') == [
        'Это', ' ', '.', '.', ' ', 'тест', ' ', '.', ' ', 'а', ' ', '.5', ' ', 'и', ' ', 'т', '.', 'д', '.']
    assert tokenizer.tokenize('Пишите на a@b.ru или http://x.ru/a.html') == [
        'Пишите', ' ', 'на', ' ', 'a@b.ru', ' ', 'или', ' ', 'http://x.ru/a.html']


# --- RussianChunker ---

def _chunks(lt, text):
    sentence = lt.get_analyzed_sentence(text)
    return ' '.join('%s/%s' % (t.token, '|'.join(c.chunk_tag for c in t.chunk_tags))
                    for t in sentence.tokens if not t.is_whitespace)


@pytest.mark.parametrize('text,expected', [
    ('Дети, гуляющие во дворе не спешили идти домой.',
     'Дети/O ,/O гуляющие/B-ADJP во/I-ADJP дворе/I-ADJP не/B-VP спешили/B-VP|I-VP идти/I-VP домой/I-VP ./O'),
    ('Маша и Миша пошли гулять.',
     'Маша/B-NP-plural и/I-NP-plural Миша/I-NP-plural пошли/B-VP гулять/I-VP ./O'),
    ('Иванов И.И. и Пётр Петрович Сидоров если поэтому.',
     'Иванов/B-NP И/I-NP ./I-NP И/I-NP ./I-NP и/O Пётр/B-NP Петрович/I-NP Сидоров/I-NP если/SBAR '
     'поэтому/SBAR ./O'),
    ('Читая книгу, он улыбался красивой девушке.',
     'Читая/B-DPT книгу/O ,/O он/O улыбался/B-VP красивой/O девушке/O ./O'),
    ('Картинка, висящая на белой стене, упала.',
     'Картинка/O ,/O висящая/B-ADJP на/I-ADJP белой/I-ADJP стене/I-ADJP ,/O упала/B-VP ./O'),
    # tokens with the chunk tag MayMissingYO are left out
    ('Ежик бежал по дороге.', 'Ежик/MayMissingYO бежал/B-VP по/O дороге/O ./O'),
])
def test_chunker(text, expected):
    lt = JLanguageTool(get_language('ru'))
    assert _chunks(lt, text) == expected
