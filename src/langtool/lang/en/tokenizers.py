"""Port of org.languagetool.tokenizers.en.EnglishWordTokenizer and
org.languagetool.rules.en.GoogleStyleWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer, string_tokenize
from ...tools import java_equals_ignore_case

# # _ \\u2070-\\u209f
# \\uFF0C -> rule NON_STANDARD_COMMA
# \\uFF1F -> rule NON_STANDARD_QUESTION_MARK
_WORD_CHARACTERS = ('±§©@€£¥\\$\\p{L}\\d\\-\u0300-\u036f¨°%‰‱&\ufffd\u00ad¬，？')
_TOKENIZER_PATTERN = jregex.compile('[' + _WORD_CHARACTERS + ']+|[^' + _WORD_CHARACTERS + ']')
_CI = jregex.IGNORECASE
_PATTERN_LIST = (
    jregex.compile("^(fo['’]c['’]sle|rec['’][ds]|OK['’]d|cc['’][ds]|DJ['’][d]|[pd]m['’]d|rsvp['’]d)$", _CI),
    jregex.compile("^(['’]?)(are|is|were|was|do|does|did|have|has|had|wo|would|ca|could|sha|should|must|ai|ought|"
                   "might|need|may|am|dare|das|dass|hai|used|use)(n['’]t)$", _CI),
    jregex.compile("^(.+)(['’]m|['’]re|['’]ll|['’]ve|['’]d|['’]s)(['’-]?)$", _CI),
    jregex.compile("^(['’]t)(was|were|is)$", _CI),
)
# some camel-case words containing hyphen (is there any better fix?)
_HYPHENATED_EXCEPTIONS = ('mers-cov', 'mcgraw-hill', 'sars-cov-2', 'sars-cov', 'ph-metre', 'ph-metres', 'anti-ivg',
                          'anti-uv', 'anti-vih', 'al-qaida')


class EnglishWordTokenizer(WordTokenizer):
    """Tokenizes text. The English tokenizer differs from the standard one in
    two respects: it does not treat the hyphen as part of the word if the
    hyphen is at the end of the word, and it includes n-dash as a
    tokenizing character, as it is used without a whitespace in English.
    Contractions are split ("I'm" -> "I", "'m"; "don't" -> "do", "n't").
    Words with hyphens or apostrophes are split at the apostrophes unless
    the tagger (EnglishTagger.INSTANCE in Java, the tagger given to the
    constructor here) knows them. Variation selectors (U+FE00..U+FE0F) are
    joined to the previous token."""

    def __init__(self, tagger=None):
        super().__init__()
        self.tagger = tagger

    def get_tokenizing_characters(self):
        # enTokenizingChars (unused by tokenize())
        return super().get_tokenizing_characters() + '_'  # underscore

    def tokenize(self, text):
        tokens = []
        aux_text = text.replace("'", 'xxAPOSTYPEWxx').replace('’', 'xxAPOSTYPOGxx')
        for m in _TOKENIZER_PATTERN.finditer(aux_text):
            s = m.group()
            if tokens and len(s) == 1 and 0xFE00 <= ord(s) <= 0xFE0F:
                tokens[-1] = tokens[-1] + s
                continue
            s = s.replace('xxAPOSTYPEWxx', "'").replace('xxAPOSTYPOGxx', '’')
            matcher = None
            if "'" in s or '’' in s:
                for pattern in _PATTERN_LIST:
                    matcher = pattern.search(s)
                    if matcher is not None:
                        break
            if matcher is not None:
                for i in range(1, len(matcher.groups()) + 1):
                    tokens.extend(self._words_to_add(matcher.group(i)))
            else:
                tokens.extend(self._words_to_add(s))
        return self.join_emails_and_urls(tokens)

    def _is_tagged(self, word):
        return self.tagger is not None and self.tagger.tag([word])[0].is_tagged()

    def _words_to_add(self, s):
        """Splits a word containing hyphen(-’') if it doesn't exist in the
        dictionary."""
        tokens = []
        hyphens_at_end = 0
        if s:
            while s.startswith('-'):
                tokens.append('-')
                s = s[1:]
            while s.endswith('-'):
                s = s[:-1]
                hyphens_at_end += 1
            if s:
                if '-' not in s and "'" not in s and '’' not in s:
                    tokens.append(s)
                else:
                    normalized = s.replace('\u00ad', '').replace('’', "'")
                    if self._is_tagged(normalized):
                        tokens.append(s)
                    elif any(java_equals_ignore_case(s, e) for e in _HYPHENATED_EXCEPTIONS):
                        tokens.append(s)
                    else:
                        # if not found, the word is split
                        tokens.extend(string_tokenize(s, "’'"))
        tokens.extend('-' * hyphens_at_end)
        return tokens


class GoogleStyleWordTokenizer(WordTokenizer):
    """Port of org.languagetool.rules.en.GoogleStyleWordTokenizer: a word
    tokenizer that splits at hyphens and keeps 'm, 're, 've and 'll
    together, like the Google ngram data."""

    def get_tokenizing_characters(self):
        return super().get_tokenizing_characters() + '-'

    def tokenize(self, text):
        tokens = super().tokenize(text)
        prev = None
        out = []
        for token in tokens:
            if prev == "'":
                # TODO: add more cases if needed:
                if token in ('m', 're', 've', 'll'):
                    out.pop()
                    out.append("'" + token)
                else:
                    out.append(token)
            else:
                out.append(token)
            prev = token
        return out
