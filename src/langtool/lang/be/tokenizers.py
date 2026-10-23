"""Port of org.languagetool.tokenizers.be.BelarusianWordTokenizer."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer, string_tokenize


class BelarusianWordTokenizer(WordTokenizer):
    """The default word tokenizer without the apostrophes ', ’ and ʼ as
    tokenizing characters (they are part of Belarusian words); the
    typographic apostrophe ’ in tokens longer than one character is
    replaced by '."""

    tokenizing_characters = TOKENIZING_CHARACTERS.replace("'", '').replace('’', '').replace('ʼ', '')

    def __init__(self):
        super().__init__()
        self._delimiters = frozenset(self.get_tokenizing_characters())

    def tokenize(self, text):
        out = []
        for token in self.join_emails_and_urls(string_tokenize(text, self._delimiters)):
            # token.length() > 1 (UTF-16 length)
            if len(token) > 1 or (token and ord(token) > 0xffff):
                out.append(token.replace('’', "'"))
            else:
                out.append(token)
        return out
