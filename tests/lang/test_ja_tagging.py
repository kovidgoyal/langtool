"""Port of org.languagetool.tagging.ja.JapaneseTaggerTest, plus tests of
JapaneseTagger's handling of malformed tokens."""

from conftest import require_dictionaries
from langtool.lang.ja.tagging import JapaneseTagger
from langtool.lang.ja.tokenizers import JapaneseWordTokenizer
from langtool.tools import is_letter, is_digit


def _is_word(token):
    """TestTools.isWord"""
    return any(is_letter(c) or is_digit(c) for c in token)


def _my_assert(text, expected, tokenizer, tagger):
    """TestTools.myAssert(input, expected, tokenizer, tagger)"""
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = []
    for readings in tagger.tag(tokens):
        out.append('|'.join(sorted('%s/[%s]%s' % (r.token, r.lemma, r.pos_tag) for r in readings.readings)))
    assert ' -- '.join(out) == expected


def test_tagger():
    """JapaneseTaggerTest.testTagger"""
    require_dictionaries('ja')
    tagger = JapaneseTagger()
    tokenizer = JapaneseWordTokenizer()
    _my_assert('これは簡単なテストです。',
               'これ/[これ]名詞-代名詞-一般 -- は/[は]助詞-係助詞 -- 簡単/[簡単]名詞-形容動詞語幹 -- な/[だ]助動詞 -- '
               'テスト/[テスト]名詞-サ変接続 -- です/[です]助動詞 -- 。/[。]記号-句点', tokenizer, tagger)
    _my_assert('私は眠い。',
               '私/[私]名詞-代名詞-一般 -- は/[は]助詞-係助詞 -- 眠い/[眠い]形容詞-自立 -- 。/[。]記号-句点', tokenizer, tagger)
    _my_assert('とても冷たい飲み物。',
               'とても/[とても]副詞-助詞類接続 -- 冷たい/[冷たい]形容詞-自立 -- 飲み物/[飲み物]名詞-一般 -- 。/[。]記号-句点',
               tokenizer, tagger)


def test_tag_positions_and_malformed_tokens():
    """Tokens that are not "surface POS lemma" become a single space without
    POS tag; the positions add up the token lengths"""
    tagger = JapaneseTagger()
    readings = tagger.tag(['私 名詞-代名詞-一般 私', 'x', ' 未知語 ', 'は 助詞-係助詞 は', 'a b c d'])
    assert [(r.token, r.start_pos, r.readings[0].pos_tag, r.readings[0].lemma) for r in readings] == [
        ('私', 0, '名詞-代名詞-一般', '私'), (' ', 1, None, None), (' ', 2, None, None),
        ('は', 3, '助詞-係助詞', 'は'), (' ', 4, None, None)]
    null_token = tagger.create_null_token('x', 3)
    assert (null_token.token, null_token.start_pos, null_token.readings[0].pos_tag) == ('x', 3, None)
    token = tagger.create_token('x', 'POS')
    assert (token.token, token.pos_tag, token.lemma) == ('x', 'POS', None)
