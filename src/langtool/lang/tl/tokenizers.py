"""Port of org.languagetool.language.tokenizers.TagalogWordTokenizer."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer


class TagalogWordTokenizer(WordTokenizer):
    """The default word tokenizer that also splits at hyphens (since 2.8)."""

    tokenizing_characters = TOKENIZING_CHARACTERS + '-'
