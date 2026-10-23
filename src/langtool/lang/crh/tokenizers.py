"""Port of org.languagetool.tokenizers.crh.CrimeanTatarWordTokenizer."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer


class CrimeanTatarWordTokenizer(WordTokenizer):
    """The Crimean Tatar tokenizer differs from the standard one in two
    respects: it does not treat the hyphen as part of the word if the hyphen
    is at the end of the word, and it includes the n-dash as a tokenizing
    character, as it is used without a whitespace in Crimean Tatar."""

    # super.getTokenizingCharacters() + n-dash (which the default already
    # contains, so this changes nothing)
    tokenizing_characters = TOKENIZING_CHARACTERS + '–'

    def tokenize(self, text):
        l = []
        for token in self.split(text):
            if len(token) > 1 and token.endswith('-'):
                l.append(token[:-1])
                l.append('-')
            else:
                l.append(token)
        return self.join_emails_and_urls(l)
