"""Port of org.languagetool.tokenizers.PersianWordTokenizer."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer


class PersianWordTokenizer(WordTokenizer):
    """The default WordTokenizer, also splitting at the Arabic comma (U+060C),
    question mark (U+061F) and semicolon (U+061B)."""

    tokenizing_characters = TOKENIZING_CHARACTERS + '،؟؛'
