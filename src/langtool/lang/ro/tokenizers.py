"""Port of org.languagetool.tokenizers.ro.RomanianWordTokenizer."""

from ...tokenizers import WordTokenizer, string_tokenize

# unlike the WordTokenizer, '-', '|', '=', '%', '°', '<', '>', '«', '»',
# '„' and '\r' are split off
_DELIMITERS = frozenset(
    '  ᅟᅠ '
    '        '
    '   ​‌‍‎‏'
    '  ‪‫‬‭‮ '
    ' ⁠⁡⁢⁣⁪⁫⁬⁭'
    '⁮⁯　ㅤ﻿ﾠ￹￺￻'
    ',.;()[]{}!?:"\'’‘„“”…\\/\t\n\r«»<>%°' '-|=')


class RomanianWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words at its own set of delimiters (a
    java.util.StringTokenizer with returnDelims=true), then joins e-mail
    addresses and URLs like WordTokenizer."""

    def tokenize(self, text):
        return self.join_emails_and_urls(string_tokenize(text, _DELIMITERS))
