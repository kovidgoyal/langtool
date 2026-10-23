"""Port of org.languagetool.tokenizers.km.KhmerWordTokenizer."""

from ...tokenizers import WordTokenizer, string_tokenize

# the Khmer signs khan (U+17D4) and bariyoosan (U+17D5) end sentences and
# are split off like punctuation; the zero width space U+200B separates
# Khmer words
_DELIMITERS = frozenset(
    '។៕  ᅟᅠ '
    '        '
    '   ​‌‍‎‏'
    '  ‪‫‬‭‮ '
    ' ⁠⁡⁢⁣⁪⁫⁬⁭'
    '⁮⁯　ㅤ﻿ﾠ￹￺￻'
    ',.;()[]{}«»!?:"\'’‘„“”…\\/\t\n')


class KhmerWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words at its own set of delimiters (a
    java.util.StringTokenizer with returnDelims=true), then joins e-mail
    addresses and URLs like WordTokenizer."""

    def tokenize(self, text):
        return self.join_emails_and_urls(string_tokenize(text, _DELIMITERS))
