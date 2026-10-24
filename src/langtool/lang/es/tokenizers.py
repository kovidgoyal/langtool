"""Port of org.languagetool.tokenizers.es.SpanishWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer, string_tokenize
from ...tools import java_equals_ignore_case

_WORD_CHARACTERS = '§©@€£\\$_\\p{L}\\d·\\-\u0300-\u036F\u00A8\u2070-\u209F°%‰‱&\uFFFD\u00AD\u00AC'
_TOKENIZER_PATTERN = jregex.compile('[' + _WORD_CHARACTERS + ']+|[^' + _WORD_CHARACTERS + ']')
# decimal point between digits
_DECIMAL_POINT = jregex.compile('([\\d])\\.([\\d])', jregex.IGNORECASE)
# decimal comma between digits
_DECIMAL_COMMA = jregex.compile('([\\d]),([\\d])', jregex.IGNORECASE)
# ordinals
_ORDINAL_POINT = jregex.compile('\\b([\\d]+)\\.(º|ª|o|a|er|os|as)\\b',
                                jregex.IGNORECASE | jregex.UNICODE_CHARACTER_CLASS)

# some camel-case words containing hyphen (is there any better fix?)
_HYPHENATED_EXCEPTIONS = ('mers-cov', 'mcgraw-hill', 'sars-cov-2', 'sars-cov', 'ph-metre', 'ph-metres')


class SpanishWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words. Punctuation and whitespace gets its
    own token. Words are sequences of letters, digits and some symbols
    (including the hyphen); decimal points and commas between digits and
    the dots of ordinals (21.ª) are kept inside the tokens. Words with
    hyphens are split at the hyphens unless the tagger (SpanishTagger.INSTANCE
    in Java, the tagger given to the constructor here) knows them. Variation
    selectors (U+FE00..U+FE0F) are joined to the previous token."""

    def __init__(self, tagger=None):
        super().__init__()
        self.tagger = tagger

    def tokenize(self, text):
        tokens = []
        # replace hyphen, non-break hyphen -> hyphen-minus
        aux_text = text.replace('‐', '-').replace('‑', '-')
        aux_text = jregex.java_replace(_DECIMAL_POINT, '$1xxES_DECIMAL_POINTxx$2', aux_text)
        aux_text = jregex.java_replace(_DECIMAL_COMMA, '$1xxES_DECIMAL_COMMAxx$2', aux_text)
        aux_text = jregex.java_replace(_ORDINAL_POINT, '$1xxES_ORDINAL_POINTxx$2', aux_text)
        for m in _TOKENIZER_PATTERN.finditer(aux_text):
            s = m.group()
            if tokens and len(s) == 1 and 0xFE00 <= ord(s) <= 0xFE0F:
                tokens[-1] = tokens[-1] + s
                continue
            s = s.replace('xxES_DECIMAL_POINTxx', '.').replace('xxES_DECIMAL_COMMAxx', ',')
            s = s.replace('xxES_ORDINAL_POINTxx', '.')
            tokens.extend(self._words_to_add(s))
        return self.join_emails_and_urls(tokens)

    def _words_to_add(self, s):
        """Splits a word containing hyphen(-) if it doesn't exist in the
        dictionary."""
        if not s:
            return []
        if '-' not in s:
            return [s]
        # words containing hyphen (-) are looked up in the dictionary
        if self.tagger is not None and self.tagger.tag([s.replace('\u00AD', '').replace('’', "'")])[0].is_tagged():
            return [s]
        if any(java_equals_ignore_case(s, e) for e in _HYPHENATED_EXCEPTIONS):
            return [s]
        # if not found, the word is split
        return string_tokenize(s, '-')
