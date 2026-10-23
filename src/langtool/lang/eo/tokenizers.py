"""Port of org.languagetool.tokenizers.eo.EsperantoWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer

_PATTERN_1 = jregex.compile("(?<!')\\b([a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ]+)'(?![a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ-])")
_PATTERN_2 = jregex.compile("(?<!')\\b([a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ]+)'(?=[a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ-])")

_APOS1 = '\u0001\u0001EO@APOS1\u0001\u0001'
_APOS2 = '\u0001\u0001EO@APOS2\u0001\u0001'


class EsperantoWordTokenizer(WordTokenizer):
    """Tokenizes just like WordTokenizer with the exception that words such
    as "dank'" contain an apostrophe within it. As in Java, the apostrophe is
    replaced by a special string during tokenizing (a hack); an apostrophe
    followed by a letter gets a space appended so that the word is split
    there, the spurious space token is removed afterwards."""

    def tokenize(self, text):
        replaced = jregex.java_replace(_PATTERN_1, '$1' + _APOS1, text)
        replaced = jregex.java_replace(_PATTERN_2, '$1' + _APOS2 + ' ', replaced)
        token_list = super().tokenize(replaced)
        tokens = []
        # put back apostrophes and remove spurious spaces
        it = iter(token_list)
        for word in it:
            if word.endswith(_APOS2):
                next(it)  # skip the next spurious white space
            word = word.replace(_APOS1, "'").replace(_APOS2, "'")
            tokens.append(word)
        return tokens
