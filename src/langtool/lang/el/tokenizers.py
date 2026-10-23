"""Port of org.languagetool.tokenizers.el.GreekWordTokenizer (with its
JFlex scanner GreekWordTokenizerImpl, src/main/jflex/GreekWordTokenizerImpl.jflex)."""

from ...tokenizers import WordTokenizer

# Delim of the JFlex specification: white space and invisible characters,
# punctuation (with the Greek ano teleia U+0387, not the middle dot U+00B7), quotes, slashes, tab and
# newline (not carriage return)
_DELIMS = frozenset(
    ' \u00a0\u115f\u1160\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a'
    '\u200b\u200c\u200d\u200e\u200f\u2028\u2029\u202a\u202b\u202c\u202d\u202e\u202f\u205f\u2060\u2061'
    '\u2062\u2063\u206a\u206b\u206c\u206d\u206e\u206f\u3000\u3164\ufeff\uffa0\ufff9\ufffa\ufffb'
    ',.;()[]{}!:"\''
    '\u0387'  # Greek ano teleia
    '’‘„“”…«»\\/\t\n')

_O_TI = 'ό,τι'


class GreekWordTokenizer(WordTokenizer):
    """Greek word tokenizer: a token is "ό,τι", a maximal run of characters
    that are not delimiters or a single delimiter (the JFlex rule
    Word = ("ό,τι" | (!(![^] | {Delim}))* | {Delim}) with longest match).
    Emails and URLs are joined afterwards (WordTokenizer.joinEMailsAndUrls)."""

    def tokenize(self, text):
        tokens = []
        n = len(text)
        i = 0
        delims = _DELIMS
        while i < n:
            if text.startswith(_O_TI, i):
                # longer than any other match at i: the run of non-delimiters
                # ends at the comma
                end = i + len(_O_TI)
            elif text[i] in delims:
                end = i + 1
            else:
                end = i + 1
                while end < n and text[end] not in delims:
                    end += 1
            tokens.append(text[i:end])
            i = end
        return self.join_emails_and_urls(tokens)
