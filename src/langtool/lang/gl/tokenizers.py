"""Port of org.languagetool.tokenizers.gl.GalicianWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer, string_tokenize

_SPLIT_CHARS = frozenset(
    ' - '
    'ᅟᅠ '
    '         '
    ' –—― ​‌‍‎'
    '‏  ‪‫‬‭‮ '
    ' ⁠⁡⁢⁣⁪⁫⁬⁭'
    '⁮⁯　ㅤ﻿ﾠ￹￺￻'
    '*+×∗·÷:=≠≂≃≄≅≆≇≈≉≤≥≪≫∧∨∩∪∈∉∊∋∌∍'
    ',.;<>()[]{}¿¡!?:"«»`\'’‘„“”…\\/\t\r\n')

# Section copied from UkranianWordTokenizer.java for handling exceptions

# some unused character to hide comma in decimal number temporary for tokenizer run
_DECIMAL_COMMA_SUBST = ''
_NON_BREAKING_SPACE_SUBST = ''
# some unused character to hide dot in date temporary for tokenizer run
_NON_BREAKING_DOT_SUBST = ''
_NON_BREAKING_COLON_SUBST = ''

# decimal comma between digits
_DECIMAL_COMMA_PATTERN = jregex.compile('([\\d]),([\\d])', jregex.IGNORECASE)
_DECIMAL_COMMA_REPL = '$1' + _DECIMAL_COMMA_SUBST + '$2'

# space between digits
_DECIMAL_SPACE_PATTERN = jregex.compile('(?<=^|[\\s(])\\d{1,3}( [\\d]{3})+(?=[\\s(]|$)', jregex.IGNORECASE)

# dots in numbers
_DOTTED_NUMBERS_PATTERN = jregex.compile('([\\d])\\.([\\d])', jregex.IGNORECASE)
_DOTTED_NUMBERS_REPL = '$1' + _NON_BREAKING_DOT_SUBST + '$2'

# colon in numbers
_COLON_NUMBERS_PATTERN = jregex.compile('([\\d]):([\\d])', jregex.IGNORECASE)
_COLON_NUMBERS_REPL = '$1' + _NON_BREAKING_COLON_SUBST + '$2'

# dates
_DATE_PATTERN = jregex.compile('([\\d]{2})\\.([\\d]{2})\\.([\\d]{4})|([\\d]{4})\\.([\\d]{2})\\.([\\d]{2})|'
                               '([\\d]{4})-([\\d]{2})-([\\d]{2})', jregex.IGNORECASE)
# (as in Java, only the groups of the first alternative are used: the other
# two kinds of dates lose their digits)
_DATE_PATTERN_REPL = '$1' + _NON_BREAKING_DOT_SUBST + '$2' + _NON_BREAKING_DOT_SUBST + '$3'
# END of Section copied from UkranianWordTokenizer.java for handling exceptions

# dots in ordinals
_DOTTED_ORDINALS_PATTERN = jregex.compile('([\\d])\\.([aoªº][sˢ]?)', jregex.IGNORECASE)
_DOTTED_ORDINALS_REPL = '$1' + _NON_BREAKING_DOT_SUBST + '$2'


def _hide_spaces(m):
    return m.group(0).replace(' ', _NON_BREAKING_SPACE_SUBST).replace(' ', _NON_BREAKING_SPACE_SUBST)


class GalicianWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words. Punctuation and whitespace gets its
    own token (a java.util.StringTokenizer with returnDelims=true and its
    own delimiters, including '-'). Decimal commas, dots in numbers, dates
    and ordinals, colons in numbers and spaces in numbers like "2 000 000"
    are hidden from the tokenizer. E-mail addresses and URLs are joined like
    in WordTokenizer."""

    def tokenize(self, text):
        if ',' in text:
            text = jregex.java_replace(_DECIMAL_COMMA_PATTERN, _DECIMAL_COMMA_REPL, text)

        # if period is not the last character in the sentence
        dot_index = text.find('.')
        dot_inside_sentence = 0 <= dot_index < len(text) - 1
        if dot_inside_sentence:
            text = jregex.java_replace(_DATE_PATTERN, _DATE_PATTERN_REPL, text)
            text = jregex.java_replace(_DOTTED_NUMBERS_PATTERN, _DOTTED_NUMBERS_REPL, text)
            text = jregex.java_replace(_DOTTED_ORDINALS_PATTERN, _DOTTED_ORDINALS_REPL, text)

        # 2 000 000
        text = _DECIMAL_SPACE_PATTERN.sub(_hide_spaces, text)

        # 12:25
        if ':' in text:
            text = jregex.java_replace(_COLON_NUMBERS_PATTERN, _COLON_NUMBERS_REPL, text)
        token_list = []
        for token in string_tokenize(text, _SPLIT_CHARS):
            token = token.replace(_DECIMAL_COMMA_SUBST, ',')
            token = token.replace(_NON_BREAKING_COLON_SUBST, ':')
            token = token.replace(_NON_BREAKING_SPACE_SUBST, ' ')
            # outside of if as we also replace back sentence-ending abbreviations
            token = token.replace(_NON_BREAKING_DOT_SUBST, '.')
            token_list.append(token)
        return self.join_emails_and_urls(token_list)
