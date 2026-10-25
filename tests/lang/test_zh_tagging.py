"""Port of org.languagetool.tagging.zh.ChineseTaggerTest, plus tests of
ChineseTagger's handling of tokens with slashes and malformed tokens."""

from conftest import require_dictionaries
from langtool.lang.zh.tagging import ChineseTagger
from langtool.lang.zh.tokenizers import ChineseWordTokenizer
from langtool.tools import is_digit, is_letter


def _is_word(token):
    """TestTools.isWord"""
    return any(is_letter(c) or is_digit(c) for c in token)


def _my_assert(text, expected, tokenizer, tagger):
    """TestTools.myAssert(input, expected, tokenizer, tagger)"""
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = []
    for readings in tagger.tag(tokens):
        out.append('|'.join(sorted('%s/[%s]%s' % (r.token, 'null' if r.lemma is None else r.lemma, r.pos_tag)
                                   for r in readings.readings)))
    assert ' -- '.join(out) == expected


def test_tagger():
    """ChineseTaggerTest.testTagger"""
    require_dictionaries('zh')
    tagger = ChineseTagger()
    tokenizer = ChineseWordTokenizer()
    _my_assert(
        '主任强调指出错误的地方。',
        '主任/[null]n -- 强调/[null]v -- 指出/[null]v -- 错误/[null]n -- 的/[null]uj -- 地方/[null]n -- 。/[null]w',
        tokenizer, tagger)
    _my_assert(
        '她胸前挂着一块碧绿的玉。',
        '她/[null]r -- 胸前/[null]s -- 挂/[null]v -- 着/[null]uz -- 一块/[null]s -- 碧绿/[null]z -- 的/[null]uj -- '
        '玉/[null]n -- 。/[null]w',
        tokenizer, tagger)
    _my_assert(
        '“鲯鳅”的研究结果有什么奥妙？',
        '“/[null]w -- 鲯/[null]n -- 鳅/[null]x -- ”/[null]w -- 的/[null]uj -- 研究/[null]vn -- 结果/[null]n -- '
        '有/[null]v -- 什么/[null]r -- 奥妙/[null]n -- ？/[null]w',
        tokenizer, tagger)
    _my_assert(
        '我们的女组长真是尺竿头更进一步。',
        '我们/[null]r -- 的/[null]uj -- 女/[null]b -- 组长/[null]n -- 真是/[null]d -- 尺/[null]q -- 竿/[null]ng -- '
        '头/[null]n -- 更进一步/[null]l -- 。/[null]w',
        tokenizer, tagger)
    _my_assert(
        '国务院，非国家工作人员不能随便进去的地方。',
        '国务院/[null]nt -- ，/[null]w -- 非/[null]h -- 国家/[null]n -- 工作/[null]vn -- 人员/[null]n -- '
        '不能/[null]v -- 随便/[null]ad -- 进去/[null]v -- 的/[null]uj -- 地方/[null]n -- 。/[null]w',
        tokenizer, tagger)
    _my_assert(
        '“哇……”珠海北师大操场上的师生大吃一惊！',
        '“/[null]w -- 哇/[null]o -- ……/[null]w -- ”/[null]w -- 珠海/[null]ns -- 北师大/[null]j -- 操场/[null]n -- '
        '上/[null]f -- 的/[null]uj -- 师生/[null]n -- 大吃一惊/[null]l -- ！/[null]w',
        tokenizer, tagger)
    _my_assert(
        '在炎热的暑假里，我和其他同学们参加了姜老师的一个项目。',
        '在/[null]p -- 炎热/[null]a -- 的/[null]uj -- 暑假/[null]t -- 里/[null]f -- ，/[null]w -- 我/[null]r -- '
        '和/[null]c -- 其他/[null]r -- 同学/[null]n -- 们/[null]k -- 参加/[null]v -- 了/[null]ul -- 姜/[null]n -- '
        '老师/[null]n -- 的/[null]uj -- 一个/[null]mq -- 项目/[null]n -- 。/[null]w',
        tokenizer, tagger)
    _my_assert(
        '“咕咚，”一台联想ThinkPad T系列电脑从关羽的宿舍飞了下来。',
        '“/[null]w -- 咕咚/[null]o -- ，/[null]w -- ”/[null]w -- 一/[null]m -- 台/[null]q -- 联想/[null]nz -- '
        'ThinkPad/[null]nx --  /[null]w -- T/[null]nx -- 系列/[null]q -- 电脑/[null]n -- 从/[null]p -- 关/[null]v -- '
        '羽/[null]q -- 的/[null]uj -- 宿舍/[null]n -- 飞/[null]v -- 了/[null]ul -- 下来/[null]v -- 。/[null]w',
        tokenizer, tagger)


def test_slashes_and_positions():
    """A word of slashes keeps all of them; other words with slashes (like
    "://", nature w) keep only the part before the first slash and get an
    empty POS tag, as in Java (String.split). Tokens without a slash become a
    single space without POS tag. The positions add up the token lengths."""
    tagger = ChineseTagger()
    readings = tagger.tag(['//w', '///w', ':///w', '网址/n', 'abc'])
    assert [(r.token, r.readings[0].pos_tag, r.start_pos) for r in readings] == [
        ('/', 'w', 0), ('//', 'w', 1), (':', '', 3), ('网址', 'n', 4), (' ', None, 6)]
    assert all(r.readings[0].lemma is None for r in readings)
    null = tagger.create_null_token('x', 3)
    assert (null.token, null.start_pos, null.readings[0].pos_tag) == ('x', 3, None)
    token = tagger.create_token('词', 'n')
    assert (token.token, token.pos_tag, token.lemma) == ('词', 'n', None)
