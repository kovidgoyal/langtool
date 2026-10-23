"""Port of org.languagetool.tokenizers.br.BretonWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer

_REPL_PATTERN_1 = jregex.compile("([Cc])['’‘ʼ]([Hh])")
_REPL_PATTERN_2 = jregex.compile("(\\p{L})['’‘ʼ]")

_APOS = '\u0001\u0001BR@APOS\u0001\u0001'


class BretonWordTokenizer(WordTokenizer):
    """Tokenizes just like WordTokenizer with the exception that "c’h" is
    not split: "C’h" is considered as a letter in Breton (trigraph) and it
    occurs in many words. Also splits things like "n’eo" into 2 tokens only,
    "n’" + "eo". As in Java, apostrophes are replaced by a special string
    during tokenizing (a hack); an apostrophe after a letter gets a space
    appended so that the word is split there, the spurious space token is
    removed afterwards. All apostrophes become ’."""

    def tokenize(self, text):
        replaced = jregex.java_replace(_REPL_PATTERN_1, '$1' + _APOS + '$2', text)
        replaced = jregex.java_replace(_REPL_PATTERN_2, '$1' + _APOS + ' ', replaced)
        token_list = super().tokenize(replaced)
        tokens = []
        # Put back apostrophes and remove spurious spaces.
        it = iter(token_list)
        for word in it:
            word = word.replace(_APOS, '’')
            tokens.append(word)
            if word != '’' and word.endswith('’'):
                next(it, None)  # Skip the next spurious white space.
        return tokens
