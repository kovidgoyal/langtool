"""Tests of the SRX segmentation (langtool.srx): the port of
net.loomchild.segment Util.finitize (the before patterns of exception rules
are used in a lookbehind of bounded length) and the running time of the
segmentation of long texts. The expected values were verified with
segment 2.0.3 (the version LanguageTool 6.8 uses) and segment.srx."""

import os
import time
import types

import pytest

import langtool
from langtool import resources, srx
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer

SRC_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'langtool', 'data')

# (generous: the segmentation of these texts takes well below a second, it took minutes or hours before
# the lookbehinds were finitized)
TIME_LIMIT = 10.0

EN_TEXT = ' '.join([
    'She go to school yesterday and buyed three apple.',
    'The quick brown fox jumps over the lazy dog.',
    '“What do you mean?” asked Elizabeth, her eyes wide with astonishment.',
    'Their going to the store tomorrow, isn’t it?',
    'Despite of the rain, we goes outside.',
    'He said that, he would come.  I has a idea.',
])


# (pattern, Util.finitize(pattern, 100) computed by segment 2.0.3)
FINITIZE_CASES = [
    ('a*b+c{2,}d{ 3 , }', 'a{0,100}b{1,100}c{2,100}d{3,100}'),
    ('\\*\\+\\{2,}', '\\*\\+\\{2,}'),
    ('\\\\*\\\\+\\\\{2,}', '\\\\{0,100}\\\\{1,100}\\\\{2,100}'),
    ('\\\\\\*\\\\\\+', '\\\\\\*\\\\\\+'),
    ('[*+]x', '[{0,100}{1,100}]x'),
    ('a*?b+?c*+d++', 'a{0,100}?b{1,100}?c{0,100}{1,100}d{1,100}+'),
    ('a{1}+b{1,}+c{10}+d{1,2}+e{12,}+', 'a{1}+b{1,100}+c{10}+d{1,2}+e{12,100}{1,100}'),
    ('a{12,13}+', 'a{12,13}{1,100}'),
    ('?+*+++', '?+{0,100}{1,100}++'),
    ('\\Qa*b+\\E*', '\\a\\*\\b\\+{0,100}'),
    ('\\Qab', '\\a\\b'),
    ('x\\\\Qa*\\E', 'x\\\\a\\*'),
    ('(?:\\.[\\s\\u00A0]){2,}', '(?:\\.[\\s\\u00A0]){2,100}'),
    ('a{2,3}*', 'a{2,3}{0,100}'),
    ('\\([^\\)]*?[\\.:][\\s ][^\\)]*?[\\.:][\\s ]',
     '\\([^\\)]{0,100}?[\\.:][\\s ][^\\)]{0,100}?[\\.:][\\s ]'),
    ('', ''),
]


@pytest.mark.parametrize('pattern,expected', FINITIZE_CASES)
def test_finitize(pattern, expected):
    assert srx.finitize(pattern) == expected


def test_finitize_infinity():
    assert srx.MAX_LOOKBEHIND_CONSTRUCT_LENGTH == 100
    assert srx.finitize('a*b+c{3,}', 7) == 'a{0,7}b{1,7}c{3,7}'


def test_remove_block_quotes():
    assert srx.remove_block_quotes('a\\Q.*\\Eb') == 'a\\.\\*b'
    assert srx.remove_block_quotes('\\Q(x)') == '\\(\\x\\)'
    assert srx.remove_block_quotes('no quotes') == 'no quotes'


def test_exception_lookbehind_is_finitized(monkeypatch):
    """RuleManager.createExceptionPatternString finitizes the before
    patterns of the exception rules (not the after patterns)"""
    doc = srx.SrxDocument(os.path.join(SRC_DATA, 'resource', 'segment.srx'))
    patterns = set()
    compile_ = srx.jregex.compile

    def record(pattern, flags=0):
        patterns.add(pattern)
        return compile_(pattern, flags)

    monkeypatch.setattr(srx.jregex, 'compile', record)
    doc.rule_manager('en_two')
    rules = [r for name in doc.get_language_rule_names('en_two') for r in doc.language_rules[name]
             if not r.is_break and '*' in r.before]
    assert rules
    for r in rules:
        assert any('(?<=' + srx.finitize(r.before) + ')' in p for p in patterns)
        assert not any('(?<=' + r.before + ')' in p for p in patterns)


def en_tokenizer():
    return get_language('en-US').sentence_tokenizer


def test_en_long_text():
    """The parenthesis exception rules of English have unbounded before
    patterns: without finitize the lookbehind made the segmentation
    polynomial/exponential in the number of sentences"""
    tokenizer = en_tokenizer()
    text = ' '.join([EN_TEXT] * 200)
    t = time.perf_counter()
    sentences = tokenizer.tokenize(text)
    assert time.perf_counter() - t < TIME_LIMIT
    assert ''.join(sentences) == text
    # (7 sentences per repetition: 'He said that, he would come.  I has a idea.' are two)
    assert len(sentences) == 7 * 200
    assert sentences[:7] == tokenizer.tokenize(EN_TEXT + ' ')


def test_en_long_text_with_parenthesis():
    tokenizer = en_tokenizer()
    for text, count in (('(' + ' '.join([EN_TEXT] * 200), 1400), ('(' + ' '.join([EN_TEXT] * 20) + ')', 133)):
        t = time.perf_counter()
        sentences = tokenizer.tokenize(text)
        assert time.perf_counter() - t < TIME_LIMIT
        assert ''.join(sentences) == text
        assert len(sentences) == count


def test_parenthesis_beyond_max_lookbehind_length():
    """A ( more than the maximum lookbehind length before a break does not
    suppress the break (as in Java, where the before pattern
    \\([^\\)]*?[\\.:][\\s ] is finitized to at most 103 characters)"""
    tokenizer = en_tokenizer()
    # the ( is 101 characters before the break: no break
    text = '(' + 'word ' * 19 + 'end. Next sentence.) More.'
    assert tokenizer.tokenize(text) == [text[:-5], 'More.']
    # 106 characters: break
    text = '(' + 'word ' * 20 + 'end. Next sentence.) More.'
    assert tokenizer.tokenize(text) == [text[:106], 'Next sentence.) ', 'More.']
    text = '(' + 'word ' * 40 + 'end. Next sentence.) More.'
    assert tokenizer.tokenize(text) == [text[:206], 'Next sentence.) ', 'More.']
    assert tokenizer.tokenize('(See the remark. It is here.) Next one.') == [
        '(See the remark. It is here.) ', 'Next one.']


# sentences in the script of the language (Latin otherwise)
SENTENCES = {
    'ar': 'ذهب الولد إلى المدرسة. هل أنت بخير؟ نعم، أنا بخير! ',
    'fa': 'پسر به مدرسه رفت. حال شما خوب است؟ بله، خوبم! ',
    'be': 'Хлопчык пайшоў у школу. Як ты маешся? Добра, дзякуй! ',
    'ru': 'Мальчик пошёл в школу. Как ты поживаешь? Хорошо, спасибо! ',
    'uk': 'Хлопчик пішов до школи. Як ти маєшся? Добре, дякую! ',
    'el': 'Ο σκύλος τρέχει γρήγορα. Πού είναι η γάτα; Κοιμάται στο σπίτι! ',
    'ja': '私は学生です。今日は晴れですか？はい、晴れです！',
    'zh': '我们去学校。你好吗？我很好！',
    'km': 'ខ្ញុំទៅផ្សារ។ គាត់ទៅសាលារៀន។ ',
    'ta': 'நான் பள்ளிக்கு சென்றேன். அவன் வீட்டில் இருக்கிறானா? ஆம்! ',
    'ml': 'ഞാൻ സ്കൂളിൽ പോയി. അവൻ വീട്ടിലുണ്ടോ? ഉണ്ട്! ',
}
LATIN = 'The cat sat on the mat. Where is the dog? It ran home! “Really?” she asked. Yes. '


def long_texts(code, n=None):
    s = SENTENCES.get(code.split('-')[0], LATIN)
    if n is None:
        n = 30000 // len(s)
    # many short sentences without parentheses, an unclosed ( near the start, and a ( at the start with the
    # ) at the end (the after patterns of the parenthesis rules match everywhere)
    return [s * n, 'A (b ' + s * n, '(' + s * n + ')']


# (the languages of the package: other test modules register fake languages)
LANGUAGES = [c for c in langtool.languages() if os.path.isdir(os.path.join(resources.rules_dir(), c.split('-')[0]))]


@pytest.mark.parametrize('code', LANGUAGES)
def test_long_texts_all_languages(code):
    tokenizer = get_language(code).sentence_tokenizer
    n = 30000 // len(SENTENCES.get(code.split('-')[0], LATIN))
    for text, short1, short2 in zip(long_texts(code), long_texts(code, 30), long_texts(code, 60)):
        t = time.perf_counter()
        sentences = tokenizer.tokenize(text)
        elapsed = time.perf_counter() - t
        assert elapsed < TIME_LIMIT, (code, len(text), elapsed)
        assert ''.join(sentences) == text
        # the number of sentences grows linearly with the repetitions of the sentences: the rules only look
        # a bounded distance back (sentences near the ( may be merged)
        c1 = len(tokenizer.tokenize(short1))
        c2 = len(tokenizer.tokenize(short2))
        # (Khmer has no segmentation rules: c1 == c2 == 1)
        assert len(sentences) == c1 + (c2 - c1) * (n - 30) // 30, (code, text[:20])


# --- emulation of the regions of the break rule matchers without slicing the text ---

SRX_REGION = '''<?xml version="1.0" encoding="UTF-8"?>
<srx xmlns="http://www.lisa.org/srx20" version="2.0">
<header segmentsubflows="yes" cascade="yes"/>
<body>
<languagerules>
<languagerule languagerulename="Test">
<rule break="yes"><beforebreak>\\.</beforebreak><afterbreak>a</afterbreak></rule>
<rule break="yes"><beforebreak>^x\\.</beforebreak><afterbreak></afterbreak></rule>
<rule break="yes"><beforebreak>\\bab\\.</beforebreak><afterbreak></afterbreak></rule>
<rule break="yes"><beforebreak>(?&lt;!q)c\\.</beforebreak><afterbreak></afterbreak></rule>
<rule break="yes"><beforebreak>;</beforebreak><afterbreak>\\bz</afterbreak></rule>
<rule break="yes"><beforebreak>a\\.?\\bq?</beforebreak><afterbreak>\\b</afterbreak></rule>
<rule break="yes"><beforebreak>(^| )c</beforebreak><afterbreak>(?&lt;=c)</afterbreak></rule>
<rule break="yes"><beforebreak>!</beforebreak><afterbreak>^y</afterbreak></rule>
</languagerule>
</languagerules>
<maprules>
<languagemap languagepattern="xx.*" languagerulename="Test"/>
</maprules>
</body>
</srx>
'''


@pytest.mark.parametrize('text,expected', [
        ('q;z..!y', ['q;', 'z..!', 'y']),
        ('x!y;zyb;', ['x!', 'y;', 'zyb;']),
        ('cazc..az.b', ['cazc.', '.', 'az.b']),
        ('cza.ab.x', ['cza.', 'ab.', 'x']),
        ('!;!y.!ybx!', ['!;!', 'y.!', 'ybx!']),
        (';z;;b!y', [';', 'z;;b!', 'y']),
        ('.ac!y bbx;', ['.', 'ac!', 'y bbx;']),
        ('c...ba;zq', ['c.', '..ba;', 'zq']),
        ('cx;z.;z!', ['cx;', 'z.;', 'z!']),
        ('!;z!ycq ', ['!;', 'z!', 'ycq ']),
        ('!yc.qb.qc', ['!', 'yc.', 'qb.qc']),
        ('q;bxy;!y;z', ['q;bxy;!', 'y;', 'z']),
        ('!yzbc.q', ['!', 'yzbc.', 'q']),
        ('.!y.ab;c !', ['.!', 'y.', 'ab;c !']),
])
def test_region_semantics(tmp_path, text, expected):
    """The break rules are searched (in Java) in a region starting at the
    last break, with opaque, anchoring bounds: ^ matches at the region
    start, \\b and lookbehind don't see the text before it. langtool searches
    the whole text where that gives the same results (see
    srx._region_dependence). The cases were selected from random texts
    where searching the whole text differs, the expected values computed
    with segment 2.0.3."""
    path = tmp_path / 'test.srx'
    path.write_text(SRX_REGION, encoding='utf-8')
    tokenizer = SRXSentenceTokenizer(types.SimpleNamespace(short_code='xx'), str(path))
    assert tokenizer.tokenize(text) == expected
