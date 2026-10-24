"""Port of org.languagetool.tokenizers.nl.DutchWordTokenizer."""

from ...tokenizers import WordTokenizer, string_tokenize

_QUOTES = ("'", '`', '’', '‘', '´')


def _starts_with_quote(token):
    return token.startswith(_QUOTES)


def _ends_with_quote(token):
    return token.endswith(_QUOTES)


class DutchWordTokenizer(WordTokenizer):
    """Tokenizes just like WordTokenizer with the exception for words such
    as "oma's" that contain an apostrophe in their middle: the apostrophes
    and similar quote characters are no tokenizing characters (the
    underscore is), quotes at the start and end of a token are split off."""

    def __init__(self):
        # remove the apostrophe etc. from the standard tokenizing characters:
        chars = WordTokenizer.get_tokenizing_characters(self) + '_'
        for quote in _QUOTES:
            chars = chars.replace(quote, '')
        self._nl_tokenizing_chars = chars
        self._nl_delimiters = frozenset(chars)
        super().__init__()

    def get_tokenizing_characters(self):
        return self._nl_tokenizing_chars

    def tokenize(self, text):
        out = []
        for token in string_tokenize(text, self._nl_delimiters):
            orig_token = token
            if len(token) > 1:
                if _starts_with_quote(token) and _ends_with_quote(token) and len(token) > 2:
                    out.append(token[0])
                    out.append(token[1:-1])
                    out.append(token[-1])
                elif _ends_with_quote(token):
                    cnt = 0
                    while _ends_with_quote(token):
                        token = token[:-1]
                        cnt += 1
                    out.append(token)
                    for i in range(len(orig_token) - cnt, len(orig_token)):
                        out.append(orig_token[i])
                elif _starts_with_quote(token):
                    while _starts_with_quote(token):
                        out.append(token[0])
                        token = token[1:]
                    out.append(token)
                else:
                    out.append(token)
            else:
                out.append(token)
        return self.join_emails_and_urls(out)
