"""Port of org.languagetool.tokenizers.ml.MalayalamWordTokenizer."""

from ...tokenizers import string_tokenize

# unlike the default WordTokenizer, this does not split at the zero width
# (non-)joiner U+200C/U+200D used inside Malayalam words (chillu letters)
_DELIMITERS = frozenset('  ᅟᅠ '
                        ',.;()[]{}!?:"\'’‘„“”…\\/\t\n')


class MalayalamWordTokenizer:
    """Tokenizes a sentence into words. Punctuation and whitespace gets its
    own token (a java.util.StringTokenizer with returnDelims=true)."""

    def tokenize(self, text):
        return string_tokenize(text, _DELIMITERS)
