"""Port of org.languagetool.tokenizers.ArabicWordTokenizer."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer


class ArabicWordTokenizer(WordTokenizer):
    """The default WordTokenizer, also splitting at the Arabic comma (U+060C),
    question mark (U+061F) and semicolon (U+061B) and at '-'."""

    tokenizing_characters = TOKENIZING_CHARACTERS + '،؟؛-'
