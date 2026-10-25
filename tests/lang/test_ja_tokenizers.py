"""Port of org.languagetool.tokenizers.ja.JapaneseWordTokenizerTest and
org.languagetool.tokenizers.ja.JapaneseSRXSentenceTokenizerTest, plus tests
of the port of the Sen morphological analyzer of lucene-gosen
(langtool.lang.ja.sen) with expected values produced by the Java library."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.ja import sen
from langtool.lang.ja.tokenizers import JapaneseWordTokenizer


@pytest.fixture(scope='module')
def tokenizer():
    require_dictionaries('ja')
    return JapaneseWordTokenizer()


def test_tokenize(tokenizer):
    """JapaneseWordTokenizerTest.testTokenize"""
    test_list = tokenizer.tokenize('これはペンです。')
    assert len(test_list) == 5
    assert test_list == ['これ 名詞-代名詞-一般 これ', 'は 助詞-係助詞 は', 'ペン 名詞-一般 ペン', 'です 助動詞 です',
                         '。 記号-句点 。']
    test_list = tokenizer.tokenize('私は「うん、そうだ」と答えた。')
    assert len(test_list) == 12
    assert test_list == ['私 名詞-代名詞-一般 私', 'は 助詞-係助詞 は', '「 記号-括弧開 「', 'うん 感動詞 うん',
                         '、 記号-読点 、', 'そう 副詞-助詞類接続 そう', 'だ 助動詞 だ', '」 記号-括弧閉 」',
                         'と 助詞-格助詞-引用 と', '答え 動詞-自立 答える', 'た 助動詞 た', '。 記号-句点 。']


# outputs of JapaneseWordTokenizer (lucene-gosen 6.2.1 with its IPADIC
# dictionary) in Java
_JAVA_TOKENS = [
    # spaces, tabs and line breaks are skipped (not part of any token)
    ('これは ペン です。',
     ['これ 名詞-代名詞-一般 これ', 'は 助詞-係助詞 は', 'ペン 名詞-一般 ペン', 'です 助動詞 です', '。 記号-句点 。']),
    ('  先頭と末尾の空白  ',
     ['先頭 名詞-一般 先頭', 'と 助詞-並立助詞 と', '末尾 名詞-一般 末尾', 'の 助詞-連体化 の', '空白 名詞-一般 空白']),
    ('タブ\tと\n改行\r\nです',
     ['タブ 名詞-一般 タブ', 'と 助詞-格助詞-一般 と', '改行 名詞-サ変接続 改行', 'です 助動詞 です']),
    ('コンピュータープログラムを書いています。',
     ['コンピューター 名詞-一般 コンピューター', 'プログラム 名詞-サ変接続 プログラム', 'を 助詞-格助詞-一般 を',
      '書い 動詞-自立 書く', 'て 助詞-接続助詞 て', 'い 動詞-非自立 いる', 'ます 助動詞 ます', '。 記号-句点 。']),
    # unknown words: runs of the same character class (ASCII by Character.getType)
    ('ABCabc123、ＡＢＣ１２３ｱｲｳ・カタカナ',
     ['ABCabc 未知語 ABCabc', '123 未知語 123', '、 記号-読点 、', 'ＡＢＣ１２３ｱｲｳ 未知語 ＡＢＣ１２３ｱｲｳ',
      '・ 記号-一般 ・', 'カタカナ 名詞-一般 カタカナ']),
    ('!!??...$$ a-b_c', ['!!??... 未知語 !!??...', '$$ 未知語 $$', 'a 未知語 a', '- 未知語 -', 'b 未知語 b',
                         '_ 未知語 _', 'c 未知語 c']),
    ('東京都に住んでいる友達に手紙を書いた。',
     ['東京 名詞-固有名詞-地域-一般 東京', '都 名詞-接尾-地域 都', 'に 助詞-格助詞-一般 に', '住ん 動詞-自立 住む',
      'で 助詞-接続助詞 で', 'いる 動詞-非自立 いる', '友達 名詞-一般 友達', 'に 助詞-格助詞-一般 に',
      '手紙 名詞-一般 手紙', 'を 助詞-格助詞-一般 を', '書い 動詞-自立 書く', 'た 助動詞 た', '。 記号-句点 。']),
    # morphemes with a second right context attribute (rcAttr2: て, く, ...)
    ('早く走って、暖かくなくてもよい。',
     ['早く 形容詞-自立 早い', '走っ 動詞-自立 走る', 'て 助詞-接続助詞 て', '、 記号-読点 、', '暖かく 形容詞-自立 暖かい',
      'なく 助動詞 ない', 'て 助詞-接続助詞 て', 'も 助詞-係助詞 も', 'よい 形容詞-自立 よい', '。 記号-句点 。']),
    ('彼は「ありがとう」と言いながら、の',
     ['彼 名詞-代名詞-一般 彼', 'は 助詞-係助詞 は', '「 記号-括弧開 「', 'ありがとう 感動詞 ありがとう',
      '」 記号-括弧閉 」', 'と 助詞-格助詞-引用 と', '言い 動詞-自立 言う', 'ながら 助詞-接続助詞 ながら',
      '、 記号-読点 、', 'の 名詞-非自立-一般 の']),
    # the ideographic space is not skipped
    ('\u3000全角スペース\u3000です',
     ['\u3000 記号-空白 \u3000', '全角 名詞-一般 全角', 'スペース 名詞-一般 スペース', '\u3000 記号-空白 \u3000',
      'です 助動詞 です']),
    ('', []),
    (' \t\n', []),
]


@pytest.mark.parametrize('text,expected', _JAVA_TOKENS)
def test_tokenize_like_java(tokenizer, text, expected):
    assert tokenizer.tokenize(text) == expected


def test_supplementary_characters(tokenizer):
    """Java splits a character outside the BMP into two unknown morphemes
    (one per surrogate, Sen works on UTF-16 code units); the tokenizer joins
    them again"""
    tokens = tokenizer.string_tagger.analyze('😀エ')
    assert [(t.surface, t.start, t.length, t.morpheme.part_of_speech) for t in tokens] == [
        ('\ud83d', 0, 1, '未知語'), ('\ude00', 1, 1, '未知語'), ('エ', 2, 1, '未知語')]
    assert tokenizer.tokenize('😀エ😀😀 𠮷a') == [
        '😀 未知語 😀', 'エ 未知語 エ', '😀 未知語 😀', '😀 未知語 😀', '𠮷 未知語 𠮷', 'a 未知語 a']


def test_morphemes(tokenizer):
    """Token and Morpheme attributes (costs, readings, pronunciations,
    Morpheme.toString) as in Java"""
    tokens = tokenizer.string_tagger.analyze('東京へ行った ABC')
    assert [(t.surface, t.start, t.length, t.cost, str(t.morpheme), t.morpheme.readings,
             t.morpheme.pronunciations) for t in tokens] == [
        ('東京', 0, 2, 2028, '名詞,固有名詞,地域,一般,*,*,*,トウキョウ,トーキョー', ['トウキョウ'], ['トーキョー']),
        ('へ', 2, 1, 3879, '助詞,格助詞,一般,*,*,*,*,ヘ,エ', ['ヘ'], ['エ']),
        ('行っ', 3, 2, 4876, '動詞,自立,*,*,五段・ワ行促音便,連用タ接続,行う,オコナッ,オコナッ', ['オコナッ'], ['オコナッ']),
        ('た', 5, 1, 5089, '助動詞,*,*,*,特殊・タ,基本形,*,タ,タ', ['タ'], ['タ']),
        ('ABC', 7, 3, 36228, '未知語,*,*,*,null,null,*,null,null', [], [])]


def test_char_class():
    """JapaneseTokenizer.getCharClass"""
    assert sen.get_char_class(ord(' ')) == sen.SPACE
    assert sen.get_char_class(ord('A')) == sen.get_char_class(ord('a')) == 2  # LOWERCASE_LETTER
    assert sen.get_char_class(ord('1')) == 9  # DECIMAL_DIGIT_NUMBER
    assert sen.get_char_class(ord('!')) == sen.get_char_class(ord('.')) == 24  # OTHER_PUNCTUATION
    assert sen.get_char_class(ord('あ')) == sen.HIRAGANA
    assert sen.get_char_class(ord('ア')) == sen.KATAKANA
    assert sen.get_char_class(ord('・')) == sen.OTHER
    assert sen.get_char_class(ord('字')) == sen.KANJI
    assert sen.get_char_class(ord('Ａ')) == sen.get_char_class(ord('ｱ')) == sen.HALF_WIDTH
    assert sen.get_char_class(0xd83d) == sen.OTHER


def test_srx_tokenize():
    """JapaneseSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('ja'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('これはテスト用の文です。')
    test_split('これはテスト用の文です。', '追加のテスト用の文です。')
    test_split('これは、テスト用の文です。')
    test_split('テスト用の文です！', '追加のテスト用の文です。')
    test_split('テスト用の文です... ', '追加のテスト用の文です。')
    test_split('アドレスはhttp://www.test.deです。')

    test_split('これは(!)の文です。')
    test_split('これは(!!)の文です。')
    test_split('これは(?)の文です。')
    test_split('これは(??)の文です。')
