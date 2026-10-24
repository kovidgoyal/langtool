"""Port of org.languagetool.tokenizers.ru.RussianWordTokenizer."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer, string_tokenize


class RussianWordTokenizer(WordTokenizer):
    """The default word tokenizer with the apostrophe ' and the period as
    additional tokenizing characters; the abbreviations "б/у" and "б/н" are
    kept as one token, and a period after a space (" .", but not " . " and
    " .. ") stays attached to the following text."""

    tokenizing_characters = TOKENIZING_CHARACTERS + "'."

    def __init__(self):
        super().__init__()
        self._delimiters = frozenset(self.get_tokenizing_characters())

    def tokenize(self, text):
        aux_text = (text.replace('б/у', '\u0001\u0001SOCR_BU\u0001\u0001')
                    .replace('б/н', '\u0001\u0001SOCR_BN\u0001\u0001')
                    .replace(' .. ', '\u0001\u0001SP_DDOT_SP\u0001\u0001')
                    .replace(' . ', '\u0001\u0001SP_DOT_SP\u0001\u0001')
                    .replace(' .', ' \u0001\u0001SP_DOT\u0001\u0001')
                    .replace('\u0001\u0001SP_DDOT_SP\u0001\u0001', ' .. ')
                    .replace('\u0001\u0001SP_DOT_SP\u0001\u0001', ' . '))
        out = []
        for s in string_tokenize(aux_text, self._delimiters):
            out.append(s.replace('\u0001\u0001SOCR_BU\u0001\u0001', 'б/у')
                       .replace('\u0001\u0001SOCR_BN\u0001\u0001', 'б/н')
                       .replace('\u0001\u0001SP_DOT\u0001\u0001', '.'))
        return self.join_emails_and_urls(out)
