"""Port of org.languagetool.tokenizers.de.GermanWordTokenizer (the
compound tokenizer GermanCompoundTokenizer is in compound_tokenizer.py)."""

from ...tokenizers import TOKENIZING_CHARACTERS, WordTokenizer


class GermanWordTokenizer(WordTokenizer):
    """The WordTokenizer with '_' and '‚' as additional tokenizing
    characters ('‚' is not a comma, but a single quotation mark)."""

    tokenizing_characters = TOKENIZING_CHARACTERS + '_‚'
