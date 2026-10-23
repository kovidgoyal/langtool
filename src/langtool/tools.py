"""String utilities, port of org.languagetool.tools.StringTools with Java
character semantics (java.lang.Character)."""

import sys
import unicodedata

import regex

_cat = unicodedata.category


def is_letter(c):
    """java.lang.Character.isLetter"""
    return _cat(c)[0] == 'L'


def is_digit(c):
    return _cat(c) == 'Nd'


def is_letter_or_digit(c):
    k = _cat(c)
    return k[0] == 'L' or k == 'Nd'


def is_lower_case(c):
    """java.lang.Character.isLowerCase: Ll or Other_Lowercase."""
    k = _cat(c)
    if k == 'Ll':
        return True
    if k[0] == 'L' or k == 'Mn' or k == 'So' or k == 'Lm':
        return c.islower() and k != 'Lt'
    return False


def is_upper_case(c):
    """java.lang.Character.isUpperCase: Lu or Other_Uppercase."""
    k = _cat(c)
    if k == 'Lu':
        return True
    if k == 'So' or k == 'Nl':
        return c.isupper()
    return False


def char_to_upper(c):
    """java.lang.Character.toUpperCase (simple case mapping)."""
    u = c.upper()
    return u if len(u) == 1 else c


def char_to_lower(c):
    """java.lang.Character.toLowerCase (simple case mapping)."""
    u = c.lower()
    return u if len(u) == 1 else c


_JAVA_WS = frozenset('\t\n\x0b\x0c\r\x1c\x1d\x1e\x1f')


def java_is_whitespace(c):
    """java.lang.Character.isWhitespace"""
    if c in _JAVA_WS:
        return True
    k = _cat(c)
    if k in ('Zs', 'Zl', 'Zp'):
        return c not in '   '
    return False


def java_trim(s):
    """java.lang.String.trim(): removes all chars <= U+0020 at both ends."""
    i, j = 0, len(s)
    while i < j and s[i] <= ' ':
        i += 1
    while j > i and s[j - 1] <= ' ':
        j -= 1
    return s[i:j]


def is_empty(s):
    return s is None or len(s) == 0


def is_whitespace(s):
    if s == '\u0002' or s == '\u0001':
        return False
    if s == '﻿':
        return True
    t = java_trim(s)
    if not t:
        return True
    if len(t) == 1:
        if s in ('​', ' ', ' '):
            return True
        return java_is_whitespace(t)
    return False


def is_all_whitespace(s):
    for c in s:
        if not is_whitespace(c):
            return False
    return True


def is_all_uppercase(s):
    if isinstance(s, (list, tuple)):
        all_upper = True
        all_not_letters = True
        for x in s:
            all_upper = all_upper and is_all_uppercase(x)
            all_not_letters = all_not_letters and (is_not_word_string(x) or is_punctuation_mark(x))
        return all_upper and not all_not_letters
    for c in s:
        if is_letter(c) and is_lower_case(c):
            return False
    return True


def is_not_all_lowercase(s):
    for c in s:
        if is_letter(c) and not is_lower_case(c):
            return True
    return False


def is_all_lowercase(s):
    return not is_not_all_lowercase(s)


def is_capitalized_word(s):
    if s and is_upper_case(s[0]):
        for c in s[1:]:
            if is_letter(c) and not is_lower_case(c):
                return False
        return True
    return False


def is_mixed_case(s):
    return not is_all_uppercase(s) and not is_capitalized_word(s) and is_not_all_lowercase(s)


def starts_with_uppercase(s):
    return bool(s) and is_upper_case(s[0])


def starts_with_lowercase(s):
    return bool(s) and is_lower_case(s[0])


def all_start_with_lowercase(s):
    parts = java_split(s, ' ')
    if len(parts) < 2:
        return starts_with_lowercase(s)
    return all(starts_with_lowercase(p) for p in parts)


def java_split(s, sep):
    """String.split with a literal separator: trailing empty strings are
    removed."""
    parts = s.split(sep)
    while parts and parts[-1] == '':
        parts.pop()
    return parts if parts else ([s] if s == '' else [])


def _change_first_char_case(s, to_upper):
    if not s:
        return s
    if len(s) == 1:
        return s.upper() if to_upper else s.lower()
    pos = 0
    n = len(s) - 1
    while not is_letter_or_digit(s[pos]) and n > pos:
        pos += 1
    c = s[pos]
    return s[:pos] + (char_to_upper(c) if to_upper else char_to_lower(c)) + s[pos + 1:]


def uppercase_first_char(s, lang_code=None):
    if lang_code == 'nl' and s is not None and s.lower().startswith('ij'):
        return 'IJ' + s[2:]
    return _change_first_char_case(s, True)


def lowercase_first_char(s):
    return _change_first_char_case(s, False)


def lowercase_first_char_if_capitalized(s):
    if not is_capitalized_word(s):
        return s
    return _change_first_char_case(s, False)


_TITLECASE_EXCEPTIONS = frozenset((
    # English
    'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet', 'so', 'as', 'at', 'by', 'in', 'of',
    'off', 'on', 'per', 'to', 'up', 'via', 'with', 'from', 'into', 'over', 'than',
    # Portuguese
    'e', 'o', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'por', 'para',
    'com', 'um', 'uma',
    # French
    'le', 'la', 'les', 'un', 'une', 'des', 'du', 'et', 'ou', 'à', 'au', 'aux', 'en', 'sur', 'pour', 'par',
    # Spanish
    'el', 'los', 'las', 'y', 'del', 'al', 'con', 'unos', 'unas',
    # German
    'der', 'die', 'das', 'und', 'oder', 'von', 'zu', 'mit', 'im', 'am', 'vom', 'zum', 'zur',
    # Dutch
    'het', 'een', 'van', 'op', 'voor', 'met',
))


def titlecase_global(s):
    parts = java_split(s, ' ')
    if len(parts) == 1:
        return uppercase_first_char(s)
    out = []
    for i, p in enumerate(parts):
        if i == 0:
            out.append(uppercase_first_char(p))
        elif p.lower() in _TITLECASE_EXCEPTIONS:
            out.append(lowercase_first_char_if_capitalized(p))
        else:
            out.append(uppercase_first_char(p))
    return ' '.join(out)


def trim_whitespace(s):
    """Port of StringTools.trimWhitespace: collapse internal runs of
    whitespace (chars <= ' ') and remove tabs/newlines."""
    st = java_trim(s)
    filt = []
    i = 0
    n = len(st)
    while i < n:
        while st[i] <= ' ' and i < n and ((i + 1 < n and st[i + 1] <= ' ') or (i > 1 and st[i - 1] <= ' ')):
            i += 1
        c = st[i]
        if c not in '\n\t\r':
            filt.append(c)
        i += 1
    r = ''.join(filt)
    return st if len(r) == len(st) else r


def add_space(word, lang_code):
    if len(word) == 1:
        c = word
        if lang_code == 'fr':
            if c in '.,':
                return ''
        elif c in '.,;:?!':
            return ''
    return ' '


def is_positive_number(c):
    return '1' <= c <= '9'


_PUNCTUATION = regex.compile(r"[\p{P}']")
_PUNCT_AND_SYMBOL = regex.compile(r"[\p{P}\p{S}']")
_NOT_WORD_CHARACTER = regex.compile(r'[^\p{L}]', regex.DOTALL)
_NOT_WORD_STR = regex.compile(r'[^\p{L}]+', regex.DOTALL)
_TASHKEEL = regex.compile('[ًٌٍَُِّْٕٖٓٔـ]')
_DIACRITICS = regex.compile(r'[\p{InCombiningDiacriticalMarks}]')


def is_punctuation_mark(s):
    return _PUNCTUATION.fullmatch(s) is not None


def is_punctuation_or_symbol(s):
    return _PUNCT_AND_SYMBOL.fullmatch(s) is not None


def is_not_word_character(s):
    return _NOT_WORD_CHARACTER.fullmatch(s) is not None


def is_not_word_string(s):
    return _NOT_WORD_STR.fullmatch(s) is not None


def remove_tashkeel(s):
    return _TASHKEEL.sub('', s)


def remove_diacritics(s):
    return _DIACRITICS.sub('', unicodedata.normalize('NFD', s))


def has_diacritics(s):
    return s != remove_diacritics(s)


_CAMEL_CASE = regex.compile(r'[a-z]+[A-Z][A-Za-z]+')


def is_camel_case(s):
    return _CAMEL_CASE.fullmatch(s) is not None


def preserve_case(input_string, model_string):
    if not model_string:
        return input_string
    if is_capitalized_word(model_string):
        return uppercase_first_char(input_string.lower())
    if is_all_uppercase(model_string):
        return input_string.upper()
    return input_string


def is_paragraph_end(sentence, single_line_breaks_marks_para):
    if single_line_breaks_marks_para:
        return sentence.endswith('\n') or sentence.endswith('\n\r')
    return sentence.endswith('\n\n') or sentence.endswith('\n\r\n\r') or sentence.endswith('\r\n\r\n')


def contains_line_break(token):
    for c in '\n\r\f\x0b\x85  ':
        if c in token:
            return True
    return False


def java_equals_ignore_case(a, b):
    """java.lang.String.equalsIgnoreCase"""
    if len(a) != len(b):
        return False
    if a == b:
        return True
    for x, y in zip(a, b):
        if x == y:
            continue
        ux, uy = char_to_upper(x), char_to_upper(y)
        if ux == uy:
            continue
        if char_to_lower(ux) == char_to_lower(uy):
            continue
        return False
    return True


def load_word_lines(path):
    """Load a resource file, ignoring empty lines and lines starting with #"""
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line or line[0] == '#':
                continue
            out.append(line)
    return out


def is_non_breaking_whitespace(s):
    return s == ' '


def is_field_code_token(s):
    return s in ('\u0001', '\u0002')


_WORD_FOR_SPELLER = regex.compile(r'^[\p{L}\d\p{P}\p{Zs}]+$')


def is_emoji(word):
    """StringTools.isEmoji: contains characters outside the BMP and is not a
    normal word."""
    if len(word) > 1 and any(ord(c) > 0xffff for c in word):
        return _WORD_FOR_SPELLER.match(word) is None
    return False


def is_numeric_space(s):
    """org.apache.commons.lang3.StringUtils.isNumericSpace"""
    if s is None:
        return False
    for c in s:
        if c != ' ' and not is_digit(c):
            return False
    return True


def is_numeric(s):
    """org.apache.commons.lang3.StringUtils.isNumeric"""
    if not s:
        return False
    return all(is_digit(c) for c in s)


_SPECIAL_CHARACTERS = None


def trim_special_characters(s):
    """StringTools.trimSpecialCharacters: removes all characters that are not
    (Unicode) whitespace, letters, digits or punctuation."""
    global _SPECIAL_CHARACTERS
    if _SPECIAL_CHARACTERS is None:
        from . import jregex
        _SPECIAL_CHARACTERS = jregex.compile(r'(?U)[^\p{Space}\p{Alnum}\p{Punct}]')
    return _SPECIAL_CHARACTERS.sub('', s)


def is_junit_test():
    """Port of org.languagetool.rules.TestHackHelper.isJUnitTest: true if
    called (directly or indirectly) from a unit test (pytest, the counterpart
    of org.junit) or from langtool.testing (the port of PatternRuleTest)."""
    f = sys._getframe(1)
    while f is not None:
        name = f.f_globals.get('__name__') or ''
        if name.startswith('_pytest.') or name == 'langtool.testing':
            return True
        f = f.f_back
    return False
