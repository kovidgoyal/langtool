"""Port of org.languagetool.tokenizers.zh.ChineseWordTokenizerTest and
org.languagetool.tokenizers.zh.ChineseSentenceTokenizerTest, plus tests of
the port of HanLP (langtool.lang.zh.hanlp) with expected values produced by
the Java library (hanlp portable-1.8.2)."""

import pytest

from conftest import require_dictionaries
from langtool.lang.zh import hanlp
from langtool.lang.zh.tokenizers import ChineseSentenceTokenizer, ChineseWordTokenizer


@pytest.fixture(scope='module')
def tokenizer():
    require_dictionaries('zh')
    return ChineseWordTokenizer()


def test_tokenize(tokenizer):
    """ChineseWordTokenizerTest.testTokenize"""
    tokens = tokenizer.tokenize('主任强调指出错误的地方。')
    assert len(tokens) == 7
    assert tokens == ['主任/n', '强调/v', '指出/v', '错误/n', '的/uj', '地方/n', '。/w']

    tokens2 = tokenizer.tokenize('她胸前挂着一块碧绿的玉。')
    assert len(tokens2) == 9
    assert tokens2 == ['她/r', '胸前/s', '挂/v', '着/uz', '一块/s', '碧绿/z', '的/uj', '玉/n', '。/w']

    tokens3 = tokenizer.tokenize('“鲯鳅”的研究结果有什么奥妙？')
    assert len(tokens3) == 11
    assert tokens3 == ['“/w', '鲯/n', '鳅/x', '”/w', '的/uj', '研究/vn', '结果/n', '有/v', '什么/r', '奥妙/n', '？/w']

    tokens4 = tokenizer.tokenize('我们的女组长真是尺竿头更进一步。')
    assert len(tokens4) == 10
    assert tokens4 == ['我们/r', '的/uj', '女/b', '组长/n', '真是/d', '尺/q', '竿/ng', '头/n', '更进一步/l', '。/w']

    tokens5 = tokenizer.tokenize('国务院，非国家工作人员不能随便进去的地方。')
    assert len(tokens5) == 12
    assert tokens5 == ['国务院/nt', '，/w', '非/h', '国家/n', '工作/vn', '人员/n', '不能/v', '随便/ad', '进去/v',
                       '的/uj', '地方/n', '。/w']

    tokens6 = tokenizer.tokenize('“哇……”珠海北师大操场上的师生大吃一惊！')
    assert len(tokens6) == 12
    assert tokens6 == ['“/w', '哇/o', '……/w', '”/w', '珠海/ns', '北师大/j', '操场/n', '上/f', '的/uj', '师生/n',
                       '大吃一惊/l', '！/w']

    tokens7 = tokenizer.tokenize('在炎热的暑假里，我和其他同学们参加了姜老师的一个项目。')
    assert len(tokens7) == 19
    assert tokens7 == ['在/p', '炎热/a', '的/uj', '暑假/t', '里/f', '，/w', '我/r', '和/c', '其他/r', '同学/n', '们/k',
                       '参加/v', '了/ul', '姜/n', '老师/n', '的/uj', '一个/mq', '项目/n', '。/w']

    tokens8 = tokenizer.tokenize('“咕咚，”一台联想ThinkPad T系列电脑从关羽的宿舍飞了下来。')
    assert len(tokens8) == 21
    assert tokens8 == ['“/w', '咕咚/o', '，/w', '”/w', '一/m', '台/q', '联想/nz', 'ThinkPad/nx', ' /w', 'T/nx',
                       '系列/q', '电脑/n', '从/p', '关/v', '羽/q', '的/uj', '宿舍/n', '飞/v', '了/ul', '下来/v',
                       '。/w']


# outputs of ChineseWordTokenizer (HanLP portable-1.8.2) in Java
_JAVA_TOKENS = [
    # numbers (atoms of the same character type, decimal separators inside
    # numbers), times, units
    ('2019年10月5日下午3点，温度是12.5%，价格1,000元。',
     ['2019/m', '年/q', '10/m', '月/q', '5/m', '日/q', '下午/t', '3/m', '点/q', '，/w', '温度/n', '是/v', '12.5/m',
      '%/nx', '，/w', '价格/n', '1,000/m', '元/q', '。/w']),
    # Chinese numbers continue an atom over the following dictionary words
    ('一二三四五六七八九十个人，百分之五十', ['一二三四五六七八九十/m', '个/q', '人/n', '，/w', '百分之/m', '五十/m']),
    ('iPhone和C++以及x86都是“专有名词”……',
     ['iPhone/nx', '和/c', 'C/nx', '++/w', '以及/c', 'x/nx', '86/m', '都/d', '是/v', '“/w', '专有/b', '名词/n', '”/w',
      '……/w']),
    # runs of delimiters are one word
    ('http://www.hankcs.com/ 网址//斜杠a/b',
     ['http/nx', ':///w', 'www/nx', './w', 'hankcs/nx', './w', 'com/nx', '//w', ' /w', '网址/n', '///w', '斜/ad',
      '杠/ng', 'a/nx', '//w', 'b/nx']),
    ('他说：“你好！”她问：“为什么？”',
     ['他/r', '说/v', '：/w', '“/w', '你好/l', '！/w', '”/w', '她/r', '问/v', '：/w', '“/w', '为什么/r', '？/w', '”/w']),
    # characters outside the BMP (two UTF-16 units of the delimiter type)
    ('😀表情𠀀字符', ['😀/w', '表情/n', '𠀀/w', '字符/n']),
    ('Ｔ恤衫①②Ⅲ·《三国演义》', ['Ｔ/n', '恤衫/n', '①②Ⅲ/m', '·/w', '《/w', '三国演义/nz', '》/w']),
    ('第一次十点半3点钟', ['第一/m', '次/q', '十/m', '点/q', '半/m', '3/m', '点钟/qt']),
    # tags of the core dictionary that are not in the transition matrix
    ('不是梦幻般的梦回梁都，却惊天动地；',
     ['不/d', '是/v', '梦幻/n', '般/u', '的/uj', '梦/n', '回/v', '梁/n', '都/d', '，/w', '却/d', '惊天动地/i', '；/w']),
    ('', []),
    ('   ', ['   /w']),
]


@pytest.mark.parametrize('text,expected', _JAVA_TOKENS)
def test_java_tokens(tokenizer, text, expected):
    tokenizer.tokenize('')  # not the first word net (see test_first_word_net)
    assert tokenizer.tokenize(text) == expected


def test_first_word_net(tokenizer):
    """Vertex.newB() reads Predefine.TOTAL_FREQUENCY before the core
    dictionary is loaded (and the total frequency set) by the first word net
    of the JVM: its begin vertex has a different frequency, which changes
    some results (Java: the same text segmented first and again)"""
    tokenizer.data.first_word_net = True
    assert tokenizer.tokenize('不是词语的结尾') == ['不是/c', '词语/n', '的/uj', '结尾/n']
    assert tokenizer.tokenize('不是词语的结尾') == ['不/d', '是/v', '词语/n', '的/uj', '结尾/n']


def test_data(tokenizer):
    data = tokenizer.data
    assert len(data.attributes) == 85585
    assert data.total_frequency == 9727730  # the sum of the frequencies (no total in the file)
    assert data.get_word_id(hanlp.TAG_PROPER) == -1
    assert data.get_word_id('始##始') >= 0 and data.get_word_id('末##末') >= 0
    attribute = data.attributes[data.get_word_id('的')]
    assert [hanlp.NATURES[n] for n in attribute.nature][0] == 'uj'
    assert data.char_type[ord('a')] == hanlp.CT_SINGLE
    assert data.char_type[ord('9')] == hanlp.CT_NUM
    assert data.char_type[ord('一')] == hanlp.CT_CNUM
    assert data.char_type[ord('字')] == hanlp.CT_CHINESE
    assert data.char_type[0xd83d] == data.char_type[0xde00] == hanlp.CT_DELIMITER
    assert len(hanlp.NATURES) == 148 and hanlp.NATURES[-2:] == ['end', 'begin']


@pytest.fixture(scope='module')
def stokenizer():
    return ChineseSentenceTokenizer()


def test_sentence_tokenize(stokenizer):
    """ChineseSentenceTokenizerTest.testTokenize"""
    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    t2 = '我们是中国人'
    t3 = '中国人很好'
    for c in '_/:@#$%^&+*':
        test_split(t2 + c + t3)  # 例子：我们是中国人_中国人很好
    for c in '\uff0c\uff01\uff1f\uff1b\u3002':  # '，', '！', '？', '；', '。'
        test_split(t2 + c, t3)  # 例子：我们是中国人，/中国人很好


def test_sentence_tokenize2(stokenizer):
    """ChineseSentenceTokenizerTest.testTokenize2"""
    sentences = ('Linux是一種自由和開放源碼的類UNIX操作系統。', '该操作系统的内核由林纳斯·托瓦兹在1991年10月5日首次发布。',
                 '在加上使用者空間的應用程式之後，', '成為Linux作業系統。')
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


def test_tokenize_with_spaces(stokenizer):
    """ChineseSentenceTokenizerTest.testTokenizeWithSpaces"""
    def test_split(*sentences):
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('的', ' ', '诗的。')
    test_split('的', '  ', '诗的。')
    test_split('的', '\n', '诗的。')
    test_split('的', '\n\n', '诗的。')
    test_split('的', '\n \n', '诗的。')
    test_split('的', '\n \n')
    test_split(' ', '的', ' ')
    assert not stokenizer.single_line_breaks_marks_para()


# outputs of ChineseSentenceTokenizer (SentencesUtil) in Java
_JAVA_SENTENCES = [
    ('2019年10月5日下午3点，温度是12.5%，价格1,000元。', ['2019年10月5日下午3点，', '温度是12.5%，', '价格1,', '000元。']),
    ('他说：“你好！”她问：“为什么？”', ['他说：“你好！', '”她问：“为什么？', '”']),
    ('http://www.hankcs.com/ 网址//斜杠a/b', ['http://www.hankcs.com/', ' ', '网址//斜杠a/b']),
    ('iPhone和C++以及x86都是“专有名词”……', ['iPhone和C++以及x86都是“专有名词”……']),
]


@pytest.mark.parametrize('text,expected', _JAVA_SENTENCES)
def test_java_sentences(stokenizer, text, expected):
    assert stokenizer.tokenize(text) == expected


def test_sentences_util():
    """SentencesUtil.toSentenceList: whitespace at the start of a sentence is
    skipped, sentences are trimmed (String.trim), '.' ends a sentence before
    a non-ASCII character, '……' ends a sentence, commas and semicolons only
    in the shortest mode, a no-break space ends a sentence (expected values
    from Java)"""
    assert hanlp.to_sentence_list('a.b.中文…x……y') == ['a.b.', '中文…x……', 'y']
    assert hanlp.to_sentence_list('甲，乙;丙', False) == ['甲，乙;丙']
    assert hanlp.to_sentence_list('甲，乙;丙') == ['甲，', '乙;', '丙']
    assert hanlp.to_sentence_list('\x01甲\u00a0乙\x02') == ['甲\u00a0', '乙']
    assert hanlp.to_sentence_list('  甲 \t乙\r\n') == ['甲', '乙']
