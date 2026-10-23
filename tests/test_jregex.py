"""Focused tests of the Java regex dialect (langtool.jregex).

LanguageTool rules use java.util.regex syntax and semantics, which jregex
translates to the Python ``regex`` module. All expected values below were
obtained by running the same patterns/inputs through java.util.regex
(OpenJDK 27) with a small Java program:

* M(pattern, {input: expected}) - Matcher.matches() (full match)
* F(pattern, {input: expected}) - first Matcher.find(): [start, end, group1, ...] or None
* C(pattern, expected)          - Pattern.compile() succeeds (OK) or throws (ERROR)
* R/R1(pattern, input, replacement, expected) - Matcher.replaceAll/replaceFirst,
  ERROR if Java throws (bad group reference etc.)

flags: 'i' = Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE (jregex.IGNORECASE),
'u' = Pattern.UNICODE_CHARACTER_CLASS (jregex.UNICODE_CHARACTER_CLASS).
ERROR for M/F means Pattern.compile() throws a PatternSyntaxException.

Note: since JDK 19 (JDK-8264160) \b is ASCII based unless
UNICODE_CHARACTER_CLASS is set (older JDKs used Character.isLetterOrDigit).

More cases (case insensitivity incl. i/I/\u0131/\u0130, line terminators,
scoped flags, comments mode, stacked quantifiers, property names, replacement
strings), also with java.util.regex results, are in
tests/data/java_regex_cases.json.gz (test_java_regex_more).
"""

import pytest

from langtool import jregex

ERROR = 'ERROR'
OK = 'OK'

def _param(op, pattern, flags, args, expected):
    ident = '%s:%s:%s:%s' % (op, flags, pattern, '|'.join(map(repr, args)))
    return pytest.param(op, pattern, flags, args, expected, id=ident)


def M(pattern, cases, flags=''):
    return [_param('M', pattern, flags, (s,), e) for s, e in cases.items()]


def F(pattern, cases, flags=''):
    return [_param('F', pattern, flags, (s,), e) for s, e in cases.items()]


def C(pattern, expected, flags=''):
    return [_param('C', pattern, flags, (), expected)]


def R(pattern, s, repl, expected, flags=''):
    return [_param('R', pattern, flags, (s, repl), expected)]


def R1(pattern, s, repl, expected, flags=''):
    return [_param('R1', pattern, flags, (s, repl), expected)]


def _flags(fl):
    f = 0
    if 'i' in fl:
        f |= jregex.IGNORECASE
    if 'u' in fl:
        f |= jregex.UNICODE_CHARACTER_CLASS
    return f


CASES = [p for group in [

    # --- Unicode properties and Java specific property names
    M(r'\p{Lu}', {'A': True, 'Ä': True, 'a': False, 'ǅ': False, '1': False, 'Σ': True, 'ß': False}),
    M(r'\p{Ll}', {'a': True, 'ß': True, 'A': False, 'ª': False, 'ǅ': False}),
    M(r'\p{L}', {'a': True, 'ä': True, '1': False, '_': False, 'ǅ': True, '中': True, 'ʰ': True, '\u0301': False}),
    M(r'\p{IsL}', {'a': True, '1': False}),
    M(r'\p{IsLu}', {'A': True, 'a': False}),
    M(r'\p{Lt}', {'ǅ': True, 'A': False}),
    M(r'\p{M}', {'\u0301': True, 'a': False}),
    M(r'\p{N}', {'1': True, '٣': True, 'Ⅷ': True, '½': True, 'a': False}),
    M(r'\p{Nd}', {'1': True, '٣': True, 'Ⅷ': False, '½': False}),
    M(r'\p{S}', {'$': True, '+': True, '€': True, '©': True, 'a': False, '!': False}),
    M(r'\p{Sc}', {'$': True, '€': True, '+': False}),
    M(r'\p{P}', {'!': True, '-': True, '_': True, '$': False, '+': False, '«': True, '—': True, '¿': True}),
    M(r'\p{Pd}', {'-': True, '—': True, '‐': True, '_': False}),
    M(r'\p{IsPunctuation}', {'!': True, '$': False, '«': True}),
    M(r'\p{javaLowerCase}', {'a': True, 'A': False, 'ß': True, 'ª': True, 'ʰ': True, 'ǅ': False, '1': False}),
    M(r'\p{javaUpperCase}', {'A': True, 'a': False, 'Ⓐ': True, 'ǅ': False}),
    M(r'\p{javaLetter}', {'a': True, 'ʰ': True, '1': False, 'Ⅷ': False}),
    M(r'\p{javaLetterOrDigit}', {'a': True, '1': True, '٣': True, '_': False}),
    M(r'\p{javaWhitespace}', {' ': True, '\x09': True, '\xa0': False, '\u2003': True, '\u2007': False, '\x1c': True, '\x0a': True}),
    M(r'\p{javaSpaceChar}', {' ': True, '\xa0': True, '\x09': False, '\u2028': True}),
    M(r'\p{javaDigit}', {'1': True, '٣': True, 'Ⅷ': False}),
    M(r'\p{javaAlphabetic}', {'a': True, 'Ⅷ': True, '1': False}),
    M(r'\p{IsAlphabetic}', {'a': True, 'Ⅷ': True, '\u0345': True, '1': False, 'ʰ': True, '_': False}),
    M(r'\p{Alphabetic}', {'a': ERROR, '1': ERROR}),
    M(r'\p{IsLetter}', {'a': True, '1': False}),
    M(r'\p{IsDigit}', {'1': True, '٣': True, 'a': False}),
    M(r'\p{IsWhite_Space}', {' ': True, '\xa0': True, 'a': False}),
    M(r'\p{IsUppercase}', {'A': True, 'Ⓐ': True, 'a': False}),
    M(r'\p{IsLowercase}', {'a': True, 'ª': True, 'A': False}),
    M(r'\p{IsLatin}', {'a': True, 'é': True, 'α': False, '1': False}),
    M(r'\p{IsGreek}', {'α': True, 'a': False}),
    M(r'\p{script=Cyrillic}', {'ж': True, 'a': False}),
    M(r'\p{sc=Latn}', {'a': True, 'ж': False}),
    M(r'\p{InGreek}', {'α': True, 'a': False}),
    M(r'\p{InBasicLatin}', {'a': True, 'é': False}),
    M(r'\p{block=Latin-1 Supplement}', {'é': True, 'a': False}),
    M(r'\p{gc=Lu}', {'A': True, 'a': False}),
    M(r'\p{general_category=Ll}', {'a': True, 'A': False}),
    M(r'\P{L}', {'a': False, '1': True}),
    M(r'\P{Lu}', {'a': True, 'A': False}),
    M(r'[\P{L}]', {'a': False, '1': True}),
    M(r'[^\p{L}]', {'a': False, '1': True}),
    M(r'\pL', {'a': True, '1': False}),
    M(r'\p{Emoji}', {'😀': ERROR, 'a': ERROR}),

    # --- POSIX classes, \w \d \s \b \h \v: ASCII only unless UNICODE_CHARACTER_CLASS (flag "u")
    M(r'\p{Punct}', {'!': True, '-': True, '_': True, '~': True, '$': True, '+': True, '"': True, '¡': False, '«': False, '—': False, 'a': False}),
    M(r'\p{Alpha}', {'a': True, 'Z': True, 'ä': False, '1': False}),
    M(r'\p{Alnum}', {'a': True, '1': True, 'ä': False, '٣': False}),
    M(r'\p{Lower}', {'a': True, 'A': False, 'ä': False, 'ª': False}),
    M(r'\p{Upper}', {'A': True, 'a': False, 'Ä': False}),
    M(r'\p{Digit}', {'1': True, '٣': False}),
    M(r'\p{XDigit}', {'a': True, 'F': True, 'g': False, '٣': False}),
    M(r'\p{Space}', {' ': True, '\x0b': True, '\xa0': False, '\u2003': False}),
    M(r'\p{Blank}', {' ': True, '\x09': True, '\xa0': False, '\x0a': False}),
    M(r'\p{Cntrl}', {'\x01': True, '\x7f': True, '\x85': False}),
    M(r'\p{Graph}', {'a': True, ' ': False, 'é': False}),
    M(r'\p{Print}', {'a': True, ' ': True, 'é': False}),
    M(r'\p{ASCII}', {'a': True, 'é': False}),
    M(r'\w', {'a': True, '_': True, '1': True, 'é': False, 'ß': False, '٣': False, '\u0301': False, '-': False}),
    M(r'\W', {'a': False, 'é': True, '-': True}),
    M(r'\d', {'1': True, '٣': False, '²': False}),
    M(r'\D', {'1': False, '٣': True}),
    M(r'\s', {' ': True, '\x09': True, '\x0a': True, '\x0b': True, '\xa0': False, '\u2003': False, '\x85': False, '\x1c': False}),
    M(r'\S', {' ': False, '\xa0': True}),
    M(r'[\w-]+', {'ab-c': True, 'äb': False}),
    M(r'\bé', {'é': False}),
    F(r'\bé\b', {'café': None, 'x é y': None, 'é': None}),
    F(r'\b\w+\b', {'  été  ': [3, 4], 'naïve x': [0, 2]}),
    F(r'\Bb', {'ab': [1, 2], 'éb': None, ' b': None}),
    F(r'a\b', {'aé': [0, 1], 'a1': None, 'a-': [0, 1]}),
    M(r'\h', {' ': True, '\xa0': True, '\x09': True, '\x0a': False}),
    M(r'\v', {'\x0a': True, '\x0b': True, '\u2028': True, ' ': False}),
    M(r'\p{Punct}', {'!': True, '-': True, '_': True, '~': False, '$': False, '+': False, '"': True, '¡': True, '«': True, '—': True, 'a': False}, flags='u'),
    M(r'\p{Alpha}', {'a': True, 'Z': True, 'ä': True, '1': False}, flags='u'),
    M(r'\p{Alnum}', {'a': True, '1': True, 'ä': True, '٣': True}, flags='u'),
    M(r'\p{Lower}', {'a': True, 'A': False, 'ä': True, 'ª': True}, flags='u'),
    M(r'\p{Upper}', {'A': True, 'a': False, 'Ä': True}, flags='u'),
    M(r'\p{Digit}', {'1': True, '٣': True}, flags='u'),
    M(r'\p{XDigit}', {'a': True, 'F': True, 'g': False, '٣': True}, flags='u'),
    M(r'\p{Space}', {' ': True, '\x0b': True, '\xa0': True, '\u2003': True}, flags='u'),
    M(r'\p{Blank}', {' ': True, '\x09': True, '\xa0': True, '\x0a': False}, flags='u'),
    M(r'\p{Cntrl}', {'\x01': True, '\x7f': True, '\x85': True}, flags='u'),
    M(r'\p{Graph}', {'a': True, ' ': False, 'é': True}, flags='u'),
    M(r'\p{Print}', {'a': True, ' ': True, 'é': True}, flags='u'),
    M(r'\p{ASCII}', {'a': True, 'é': False}, flags='u'),
    M(r'\w', {'a': True, '_': True, '1': True, 'é': True, 'ß': True, '٣': True, '\u0301': True, '-': False}, flags='u'),
    M(r'\W', {'a': False, 'é': False, '-': True}, flags='u'),
    M(r'\d', {'1': True, '٣': True, '²': False}, flags='u'),
    M(r'\D', {'1': False, '٣': False}, flags='u'),
    M(r'\s', {' ': True, '\x09': True, '\x0a': True, '\x0b': True, '\xa0': True, '\u2003': True, '\x85': True, '\x1c': False}, flags='u'),
    M(r'\S', {' ': False, '\xa0': False}, flags='u'),
    M(r'[\w-]+', {'ab-c': True, 'äb': True}, flags='u'),
    M(r'\bé', {'é': True}, flags='u'),
    F(r'\bé\b', {'café': None, 'x é y': [2, 3], 'é': [0, 1]}, flags='u'),
    F(r'\b\w+\b', {'  été  ': [2, 5], 'naïve x': [0, 5]}, flags='u'),
    F(r'\Bb', {'ab': [1, 2], 'éb': [1, 2], ' b': None}, flags='u'),
    F(r'a\b', {'aé': None, 'a1': None, 'a-': [0, 1]}, flags='u'),
    M(r'\h', {' ': True, '\xa0': True, '\x09': True, '\x0a': False}, flags='u'),
    M(r'\v', {'\x0a': True, '\x0b': True, '\u2028': True, ' ': False}, flags='u'),

    # --- inline (?U) = UNICODE_CHARACTER_CLASS
    M(r'(?U)\w+', {'éa': True, 'a-': False}),
    M(r'(?U)\p{Alpha}', {'ä': True}),
    M(r'a(?U)\w', {'aé': True}),
    M(r'(?U:\w)\w', {'éé': False, 'éa': True, 'aé': False}),

    # --- case insensitivity: scoped inline flags, flag "i" = CASE_INSENSITIVE|UNICODE_CASE
    M('a(?i)b', {'ab': True, 'aB': True, 'AB': False, 'Ab': False}),
    M('(?i)a(?-i)b', {'Ab': True, 'AB': False, 'ab': True}),
    M('(?i:a)b', {'Ab': True, 'AB': False}),
    M('(a(?i)b)c', {'aBc': True, 'aBC': False, 'ABc': False}),
    M('(?:x(?i)y|z)w', {'xYw': True, 'Zw': True, 'xyW': False}),
    M('(?i)ä', {'Ä': False, 'ä': True}),
    M('(?iu)ä', {'Ä': True}),
    M('(?i)[ä]', {'Ä': False}),
    M(r'(?i)\p{Lower}', {'A': True, 'a': True}),
    M(r'(?i)\p{Lu}', {'a': True, 'A': True}),
    M('(?i)[a-z]', {'K': True, 'Q': True, '\u212a': False}),
    M('(?i)k', {'\u212a': False}),
    M('(?i)s', {'ſ': False}),
    M('ä', {'Ä': True, 'ä': True}, flags='i'),
    M('Straße', {'STRASSE': False, 'STRAßE': True, 'straße': True}, flags='i'),
    M('ß', {'ẞ': True, 'ss': False}, flags='i'),
    M('s', {'ſ': True, 'S': True}, flags='i'),
    M('[a-z]', {'ſ': True, 'K': True, 'S': True, 'ǅ': False, '\u212a': True}, flags='i'),
    M('k', {'K': True, '\u212a': True}, flags='i'),  # KELVIN SIGN
    M('i', {'İ': True, 'I': True, 'ı': True}, flags='i'),
    M('ı', {'I': True, 'i': True}, flags='i'),
    M('σ', {'Σ': True, 'ς': True}, flags='i'),
    M('ǆ', {'ǅ': True, 'Ǆ': True}, flags='i'),
    M('(?-i)a', {'A': False}, flags='i'),
    M(r'\p{Lu}', {'a': True}, flags='i'),
    M(r'\p{Lower}', {'A': True}, flags='i'),
    M('[^a]', {'A': False}, flags='i'),
    M(r'(a)\1', {'aA': True}, flags='i'),
    M(r'(?i)(a)\1', {'aA': True}),
    M(r'\x{10428}', {'𐐀': True}, flags='i'),

    # --- character classes: intersection, union, nested classes, quirks
    M('[a-z&&[^aeiou]]', {'b': True, 'a': False, 'z': True, '1': False}),
    M('[a-z&&[def]]', {'d': True, 'a': False}),
    M('[a-z&&def]', {'e': True, 'a': False}),
    M(r'[\w&&[^\d]]', {'a': True, '1': False, '_': True}),
    M(r'[\p{L}&&[^\p{Lu}]]', {'a': True, 'A': False}),
    M('[^a-z&&[aeiou]]', {'a': False, 'b': True, '1': True, 'A': True}),
    M('[^a&&b]', {'a': True, 'b': True, 'c': True}),
    M('[a-c[x-z]]', {'y': True, 'b': True, 'm': False}),
    M('[a[b]]', {'a': True, 'b': True, 'c': False}),
    M('[^a[b]]', {'a': False, 'b': False, 'c': True}),
    M('[^a[^b]]', {'a': False, 'b': True, 'c': False}),
    M('[[a]&&[b]]', {'a': False, 'b': False}),
    M('[a-z&&[^m-p]&&[^x]]', {'a': True, 'n': False, 'x': False}),
    M('[a&&]', {'a': True}),
    M('[&&a]', {'a': True, '&': False}),
    M('[a&b]', {'&': True, 'a': True}),
    M('[a-]', {'-': True, 'a': True}),
    M('[-a]', {'-': True}),
    M(r'[\[\]]', {'[': True, ']': True}),
    M(r'[\Q]\E]', {']': True}),
    M(r'[\Q^-\E]', {'-': True, '^': True, 'a': False}),
    M(r'[\u00e0-\u00e5]', {'ä': True, 'æ': False}),
    M(r'[\x{1F600}-\x{1F64F}]', {'😀': True, 'a': False}),
    M('[😀-🙏]', {'😃': True, 'a': False}),
    M('[.]', {'.': True, 'a': False}),
    M('[$^]', {'$': True, '^': True}),
    M('[a-c-e]', {'-': True, 'd': False, 'e': True}),
    M(r'[\d-z]', {'-': True, '5': True, 'y': False, 'z': True}),
    M(r'[\s\S]', {'\x0a': True}),
    M('[#]', {'#': True}),
    M(r'[\0141]', {'a': True}),
    M(r'[\x41-\x43]', {'B': True}),
    M('[^]a]', {'b': True, ']': False, 'a': False}),
    C('[]a]', OK),
    C('[^]', ERROR),
    C('[]', ERROR),
    C('[a-', ERROR),
    C('[z-a]', ERROR),

    # --- \Q...\E quoting
    M(r'\Q.*\E', {'.*': True, 'ab': False}),
    M(r'\Qa+b', {'a+b': True, 'aab': False}),
    M(r'x\Q[\Ey', {'x[y': True}),
    M(r'\Q\\E', {'\\': True}),
    M(r'\Qa\E+', {'aaa': True}),
    M(r'a\Q\Eb', {'ab': True}),
    M(r'\Q(?i)\Ex', {'(?i)x': True}),
    M(r'\Q\E*', {'': ERROR}),

    # --- quantifiers: possessive, atomic, stacked, invalid
    M('a*+a', {'aaa': False}),
    M('a++b', {'aab': True}),
    M('(ab)?+ab', {'ab': False, 'abab': True}),
    M('a{1,2}+a', {'aa': False, 'aaa': True}),
    M('(?>a|ab)c', {'abc': False, 'ac': True}),
    M('a*?b', {'aab': True}),
    M('a*{2,3}', {'aaa': True, '': True}),
    M('a{2}{3}', {'aaaaaa': False, 'aa': True, 'aaaaa': False}),
    M('a{2}*', {'aaaa': ERROR, 'aaa': ERROR, '': ERROR}),
    M('(?:a{2}){3}', {'aaaaaa': True}),
    M('a+{2}', {'aa': True, 'a': True}),
    M('a?{2}', {'': True, 'a': True, 'aa': False, 'aaa': False}),
    M('a{,3}', {'a{,3}': ERROR, 'aaa': ERROR}),
    M('a{2,}', {'aa': True, 'a': False, 'aaaaa': True}),
    M('a{0}b', {'b': True, 'ab': False}),
    M('x{', {'x{': ERROR}),
    M('x}', {'x}': True}),
    M('{x', {'{x': ERROR}),
    M('a{1}?', {'a': True}),
    M('a{1,2}?+', {'a': ERROR}),
    C('a**', ERROR),
    C('a*+*', ERROR),
    C('*a', ERROR),
    C('a{2,1}', ERROR),
    C('a{', ERROR),
    C('a{1', ERROR),
    C('a{1,', ERROR),
    C('a{x}', ERROR),
    C('(?:)*', OK),
    C('a??+', ERROR),

    # --- groups, back references (also to missing groups), look-behind, group names
    M(r'(a)\2', {'a': False, 'a2': False, 'aa': False}),
    M(r'(a)\11', {'aa1': True, 'aaa': False}),
    M(r'(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)\10', {'abcdefghijj': True, 'abcdefghija0': False}),
    M(r'(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)\11', {'abcdefghija1': True}),
    M(r'\1(a)', {'a': False, 'aa': False}),
    M(r'(a)?b\1', {'b': False, 'aba': True}),
    M(r'(a|(b))\2', {'a': False, 'bb': True}),
    M(r'(?<x>a)\k<x>', {'aa': True, 'ab': False}),
    M(r'(?<x>a)(?<y>b)\2', {'abb': True}),
    M(r'(a)(?:b)\1', {'aba': True}),
    M('(?<!ab|c)d', {'d': True}),
    F('(?<!ab|c)d', {'abd': None, 'cd': None, 'xd': [1, 2]}),
    F('(?<=a{1,3})b', {'aab': [2, 3], 'b': None}),
    F(r'(?<=\b\w{1,10})x', {'abcx': [3, 4]}),
    C('(?<x>a)(?<x>b)', ERROR),
    C('(?<1x>a)', ERROR),
    C(r'\k<nope>', ERROR),
    C('(?<x_y>a)', ERROR),
    C(r'(?<xY1>a)\k<xY1>', OK),
    C('(?P<x>a)', ERROR),
    C('(?P=x)', ERROR),
    C('(?#comment)a', ERROR),
    C('(?<=a+)b', OK),
    C('(?<=a*)b', OK),
    C('(a', ERROR),
    C('a)', ERROR),
    C('(?', ERROR),
    C('(?z)a', ERROR),

    # --- '.' and line terminators, anchors, \R, \X, comments mode
    M('.', {'a': True}),
    M('(?s).', {'a': True}),
    M('(?d).', {'a': True}),
    M('.', {'\x0a': False}),
    M('(?s).', {'\x0a': True}),
    M('(?d).', {'\x0a': False}),
    M('.', {'\x0d': False}),
    M('(?s).', {'\x0d': True}),
    M('(?d).', {'\x0d': True}),
    M('.', {'\x85': False}),
    M('(?s).', {'\x85': True}),
    M('(?d).', {'\x85': True}),
    M('.', {'\u2028': False}),
    M('(?s).', {'\u2028': True}),
    M('(?d).', {'\u2028': True}),
    M('.', {'\u2029': False}),
    M('(?s).', {'\u2029': True}),
    M('(?d).', {'\u2029': True}),
    M('.', {'\x0b': True}),
    M('(?s).', {'\x0b': True}),
    M('(?d).', {'\x0b': True}),
    M('.', {'\x0c': True}),
    M('(?s).', {'\x0c': True}),
    M('(?d).', {'\x0c': True}),
    M('a.b', {'a\x0db': False, 'a\x09b': True}),
    F('a$', {'a\x0a': [0, 1], 'a\x0d\x0a': [0, 1], 'a\x0d': [0, 1], 'a\x85': [0, 1], 'a\x0a\x0a': None, 'ab': None}),
    F(r'a\Z', {'a\x0a': [0, 1], 'a\x0a\x0a': None}),
    F(r'a\z', {'a\x0a': None, 'a': [0, 1]}),
    F(r'\Aa', {'ba': None, 'ab': [0, 1]}),
    F('(?m)^b', {'a\x0ab': [2, 3], 'a\x0db': [2, 3], 'a\u2028b': [2, 3], 'a\x0d\x0ab': [3, 4]}),
    F('(?m)a$', {'a\x0db': [0, 1], 'a\x85': [0, 1]}),
    F('(?d)(?m)^b', {'a\x0db': None, 'a\x0ab': [2, 3]}),
    F('^b', {'a\x0ab': None}),
    M(r'\R', {'\x0d\x0a': True, '\x0a': True, '\u2028': True, '\x0b': True, 'a': False}),
    M(r'\R\R', {'\x0d\x0a': True}),
    M(r'[\R]', {'R': ERROR}),
    M(r'\X', {'e\u0301': True, 'a': True}),
    M('(?x) a b # comment', {'ab': True}),
    M('(?x)[ ]a', {' a': ERROR}),
    M(r'(?x)a\ b', {'a b': True}),
    M('(?x)a#b', {'a': True}),

    # --- escapes
    M(r'\t\n\r\f\a\e', {'\x09\x0a\x0d\x0c\x07\x1b': True}),
    M(r'\cA', {'\x01': True}),
    M(r'\x41\u0042\x{43}\0104', {'ABCD': True}),
    M(r'\0101', {'A': True}),
    M(r'\00', {'\x00': True}),
    M(r'\uD83D\uDE00', {'😀': True}),
    M(r'\N{LATIN SMALL LETTER A}', {'a': True}),
    M('\\-\\.\\,\\:\\;\\!\\"\\#\\%\\&\\\'\\<\\>\\=\\@\\`\\~\\/\\_', {'-.,:;!"#%&\'<>=@`~/_': True}),
    C(r'\y', ERROR),
    C(r'\i', ERROR),
    C(r'\l', ERROR),
    C(r'\8', OK),
    C(r'\x4', ERROR),
    C(r'\u004', ERROR),
    C(r'\p{Foo}', ERROR),
    C(r'\p{IsFoo}', ERROR),
    C(r'\p{InFoo}', ERROR),
    C(r'\p{^L}', ERROR),
    C(r'\p{L', ERROR),
    C(r'\c', ERROR),
    C(r'\0', ERROR),
    C(r'\0a', ERROR),
    C(r'\K', ERROR),
    C(r'\G', OK),
    C(r'\b{g}', OK),
    C('tú|?', ERROR),
    C('?', ERROR),
    C('+a', ERROR),
    C('a|*', ERROR),
    C('(?i)', OK),
    C('', OK),
    C(r'\Q', OK),
    C(r'\E', ERROR),
    C('\\', ERROR),
    C('abc\\', ERROR),

    # --- find() details: leftmost alternative, group values
    F('a|ab', {'ab': [0, 1]}),
    F('(a|ab)(c|bcd)', {'abcd': [0, 4, 'a', 'bcd']}),
    F('(a*)*b', {'aab': [0, 3, '']}),
    F('(a*)+', {'b': [0, 0, '']}),
    F('(a|b)*', {'ab': [0, 2, 'b']}),
    F('(?:(a)|b)+', {'ab': [0, 2, 'a']}),
    F('(a)|b', {'b': [0, 1, None]}),
    F('x*', {'abc': [0, 0]}),

    # --- java_replace(): $n, ${name}, \$ escapes, invalid replacements, empty matches
    R('(a)(b)?', 'ab a', '[$2$1]', '[ba] [a]'),
    R(r'(\w+) (\w+)', 'hello world', '$2 $1', 'world hello'),
    R(r'(?<first>\w+) (?<second>\w+)', 'hello world', '${second} ${first}', 'world hello'),
    R('a', 'a', r'\$1', '$1'),
    R('a', 'a', '\\\\', '\\'),
    R('a', 'a', r'\n', 'n'),
    R('a', 'a', r'x\y', 'xy'),
    R('(a)', 'a', '$10', 'a0'),
    R('(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)', 'abcdefghij', '$10$11', 'ja1'),
    R('(a)', 'a', '$2', ERROR),
    R('a', 'a', '$', ERROR),
    R('a', 'a', 'x$', ERROR),
    R('a', 'a', '${nope}', ERROR),
    R('(a)', 'a', '${1}', ERROR),
    R('(a)', 'a', '$a', ERROR),
    R('(a)', 'a', '$$1', ERROR),
    R('(a)', 'a', '\\', ERROR),
    R('(a)', 'a', '$0$0', 'aa'),
    R('(a)', 'a', '${', ERROR),
    R('(?<n>a)', 'a', '${n', ERROR),
    R('x*', 'abc', '-', '-a-b-c-'),
    R('a*', 'baaac', '-', '-b--c-'),
    R('a|', 'xa', '-', '-x--'),
    R(r'\b', 'ab cd', '|', '|ab| |cd|'),
    R('(?<=a)', 'aaa', '-', 'a-a-a-'),
    R('', '', 'x', 'x'),
    R('a', 'aaa', 'b', 'bbb'),
    R1('a', 'aaa', 'b', 'baa'),
    R1('(a+)', 'baab', '<$1>', 'b<aa>b'),
    R(r'(\d)(?=(\d{3})+$)', '1234567', '$1,', '1,234,567'),
    R('(é)', 'café', '[$1]', 'caf[é]', flags='i'),
    R('É', 'café', 'E', 'cafE', flags='i'),
    R('(a)|b', 'ab', '[$1]', '[a][]'),
    R('^', 'a\nb', '>', '>a\nb'),
    R('(?m)^', 'a\nb', '>', '>a\n>b'),
    R('$', 'a\n', '<', 'a<\n<'),
]
    for p in group]


def _load_more():
    import gzip
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'java_regex_cases.json.gz')
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    out = []
    for case, java in data:
        op, pattern, flags = case[:3]
        if java == 'E':
            java = ERROR
        elif op == 'F' and java is not None:
            java = list(java)
        out.append(pytest.param(op, pattern, flags, tuple(case[3:]), java,
                                id='%s:%s:%s:%s' % (op, flags, pattern, '|'.join(map(repr, case[3:])))))
    return out


@pytest.mark.parametrize('op,pattern,flags,args,expected', _load_more())
def test_java_regex_more(op, pattern, flags, args, expected):
    test_java_regex(op, pattern, flags, args, expected)


@pytest.mark.parametrize('op,pattern,flags,args,expected', CASES)
def test_java_regex(op, pattern, flags, args, expected):
    f = _flags(flags)
    if expected == ERROR and op != 'R' and op != 'R1':
        with pytest.raises(jregex.JavaRegexError):
            jregex.compile(pattern, f)
        return
    compiled = jregex.compile(pattern, f)
    if op == 'C':
        assert expected == OK
    elif op == 'M':
        assert (compiled.fullmatch(args[0]) is not None) == expected
    elif op == 'F':
        m = compiled.search(args[0])
        got = None if m is None else [m.start(), m.end()] + list(m.groups())
        assert got == expected
    else:
        count = 0 if op == 'R' else 1
        if expected == ERROR:
            with pytest.raises(Exception):
                jregex.java_replace(compiled, args[1], args[0], count)
        else:
            assert jregex.java_replace(compiled, args[1], args[0], count) == expected


def test_translate_is_cached_and_compile_flags_differ():
    assert jregex.compile('a', 0) is jregex.compile('a', 0)
    assert jregex.compile('a', jregex.IGNORECASE).fullmatch('A')
    assert not jregex.compile('a', 0).fullmatch('A')
