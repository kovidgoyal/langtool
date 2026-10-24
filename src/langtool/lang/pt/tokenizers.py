"""Port of org.languagetool.tokenizers.pt.PortugueseWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer, string_tokenize
from ...tools import java_equals_ignore_case

# Section copied from UkranianWordTokenizer.java for handling exceptions
# some unused character to hide comma in decimal number temporary for tokenizer run
_DECIMAL_COMMA_SUBST = ''
_NON_BREAKING_SPACE_SUBST = ''
# some unused character to hide dot in date temporary for tokenizer run
_NON_BREAKING_DOT_SUBST = ''
_NON_BREAKING_COLON_SUBST = ''
_HYPHEN_SUBST_TEXT = '\u0001\u0001PT_HYPHEN\u0001\u0001'

_CI = jregex.IGNORECASE
# decimal comma between digits
_DECIMAL_COMMA_PATTERN = jregex.compile('([\\d]),([\\d])', _CI)
_DECIMAL_COMMA_REPL = '$1' + _DECIMAL_COMMA_SUBST + '$2'
# space between digits
_DECIMAL_SPACE_PATTERN = jregex.compile('(?<=^|[\\s(])\\d{1,3}( \\d{3})+(?:[' + _DECIMAL_COMMA_SUBST
                                        + _NON_BREAKING_DOT_SUBST + ']\\d+)?(?=\\D|$)', _CI)
# dots in numbers
_DOTTED_NUMBERS_PATTERN = jregex.compile('([\\d])\\.([\\d])', _CI)
_DOTTED_NUMBERS_REPL = '$1' + _NON_BREAKING_DOT_SUBST + '$2'
# colon in numbers
_COLON_NUMBERS_PATTERN = jregex.compile('([\\d]):([\\d])', _CI)
_COLON_NUMBERS_REPL = '$1' + _NON_BREAKING_COLON_SUBST + '$2'
# dates
_DATE_PATTERN = jregex.compile('([\\d]{2})\\.([\\d]{2})\\.([\\d]{4})|([\\d]{4})\\.([\\d]{2})\\.([\\d]{2})|'
                               '([\\d]{4})-([\\d]{2})-([\\d]{2})', _CI)
_DATE_PATTERN_REPL = '$1' + _NON_BREAKING_DOT_SUBST + '$2' + _NON_BREAKING_DOT_SUBST + '$3'
# END of Section copied from UkranianWordTokenizer.java for handling exceptions

# dots in ordinals
_DOTTED_ORDINALS_PATTERN = jregex.compile('([\\d])\\.([aoªºᵃᵒ][sˢ]?)', _CI)
_DOTTED_ORDINALS_REPL = '$1' + _NON_BREAKING_DOT_SUBST + '$2'

# hyphens inside words (Java concatenates the Pattern HYPHEN_SUBST, i.e. its
# source text, into the replacements and the character class of wordChars)
_HYPHEN_PATTERN = jregex.compile('([\\p{L}])-([\\p{L}\\d])', _CI)
_HYPHEN_REPL = '$1' + _HYPHEN_SUBST_TEXT + '$2'
_NEARBY_HYPHENS_PATTERN = jregex.compile('([\\p{L}])-([\\p{L}])-([\\p{L}])', _CI)
_NEARBY_HYPHENS_REPL = '$1' + _HYPHEN_SUBST_TEXT + '$2' + _HYPHEN_SUBST_TEXT + '$3'

# ̀-ͯ is the range of combining diacritical marks
# ¨ is the diaeresis
# ⁰-₟ is the range of superscript characters
# The degree sign is included in the word characters, as it is used in temperatures and angles, and can appear
# in the middle of a token, e.g. "30°C".
_WORD_CHARS = ('°\\^\\-\\p{L}\\d\\u0300-\\u036F\\u00A8\\u2070-\\u209F' + _DECIMAL_COMMA_SUBST
               + _NON_BREAKING_DOT_SUBST + _NON_BREAKING_COLON_SUBST + _NON_BREAKING_SPACE_SUBST + _HYPHEN_SUBST_TEXT)
# The following characters might be included at some point, but, to preserve the current behaviour, they aren't:
# - ©®™
# - # (hashtags)
# This leads to some inconsistencies, e.g. '@user' is tokenised as '@user', but '#hashtag' as '#' + 'hashtag'.
_WORD_CHARS_LEFT_EDGE = '−@€£\\$¢¥¤'
_WORD_CHARS_RIGHT_EDGE = '€£\\$%‰‱ºªᵃᵒˢ'
_WORD_PATTERN = jregex.compile('[' + _WORD_CHARS_LEFT_EDGE + ']?[' + _WORD_CHARS + ']+[' + _WORD_CHARS_RIGHT_EDGE
                               + ']?|' + '[^' + _WORD_CHARS + ']', _CI)

# some camel-case words containing hyphen (is there any better fix?)
_HYPHENATED_EXCEPTIONS = ('mers-cov', 'mcgraw-hill', 'sars-cov-2', 'sars-cov', 'ph-metre', 'ph-metres', 'anti-ivg',
                          'anti-uv', 'anti-vih', 'al-qaïda')


class PortugueseWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words. Punctuation and whitespace gets its
    own token. Decimal commas, dots and colons between digits, the dots of
    dates and ordinals (1.º) and the spaces of numbers like "2 000 000" are
    kept inside the tokens; currency symbols at the start and currency,
    percent and ordinal signs at the end belong to the word. Words with
    hyphens are split at the hyphens unless the tagger (a new
    PortugueseTagger in Java, the tagger given to the constructor here)
    knows them; currency expressions (like "US$10") are split. Variation
    selectors (U+FE00..U+FE0F) are joined to the previous token."""

    def __init__(self, tagger=None):
        super().__init__()
        self.tagger = tagger

    def tokenize(self, text):
        tokenised_text = text
        if ',' in tokenised_text:
            tokenised_text = jregex.java_replace(_DECIMAL_COMMA_PATTERN, _DECIMAL_COMMA_REPL, tokenised_text)
        # if period is not the last character in the sentence
        dot_index = tokenised_text.find('.')
        dot_inside_sentence = 0 <= dot_index < len(tokenised_text) - 1
        if dot_inside_sentence:
            tokenised_text = jregex.java_replace(_DATE_PATTERN, _DATE_PATTERN_REPL, tokenised_text)
            tokenised_text = jregex.java_replace(_DOTTED_NUMBERS_PATTERN, _DOTTED_NUMBERS_REPL, tokenised_text)
            tokenised_text = jregex.java_replace(_DOTTED_ORDINALS_PATTERN, _DOTTED_ORDINALS_REPL, tokenised_text)
        # 2 000 000
        if _DECIMAL_SPACE_PATTERN.search(tokenised_text):
            parts = []
            last = 0
            for m in _DECIMAL_SPACE_PATTERN.finditer(tokenised_text):
                parts.append(tokenised_text[last:m.start()])
                parts.append(m.group(0).replace(' ', _NON_BREAKING_SPACE_SUBST)
                             .replace(' ', _NON_BREAKING_SPACE_SUBST))
                last = m.end()
            parts.append(tokenised_text[last:])
            tokenised_text = ''.join(parts)
        # 12:25
        if ':' in tokenised_text:
            tokenised_text = jregex.java_replace(_COLON_NUMBERS_PATTERN, _COLON_NUMBERS_REPL, tokenised_text)
        if '-' in tokenised_text:
            tokenised_text = jregex.java_replace(_NEARBY_HYPHENS_PATTERN, _NEARBY_HYPHENS_REPL, tokenised_text)
            tokenised_text = jregex.java_replace(_HYPHEN_PATTERN, _HYPHEN_REPL, tokenised_text)
        token_list = []
        for m in _WORD_PATTERN.finditer(tokenised_text):
            token = m.group()
            # 0xFE00-0xFE0F are non-spacing marks
            if token_list and len(token) == 1 and 0xFE00 <= ord(token) <= 0xFE0F:
                token_list[-1] = token_list[-1] + token
                continue
            token = token.replace(_DECIMAL_COMMA_SUBST, ',')
            token = token.replace(_NON_BREAKING_COLON_SUBST, ':')
            token = token.replace(_NON_BREAKING_SPACE_SUBST, ' ')
            # outside of if as we also replace back sentence-ending abbreviations
            token = token.replace(_NON_BREAKING_DOT_SUBST, '.')
            token = token.replace(_HYPHEN_SUBST_TEXT, '-')
            token_list.extend(self._words_to_add(token))
        return self.join_emails_and_urls(token_list)

    def _words_to_add(self, s):
        """Splits a word containing hyphen(-) if it doesn't exist in the
        dictionary."""
        if not s:
            return []
        if self.is_currency_expression(s):
            return self.split_currency_expression(s)
        if '-' not in s:
            return [s]
        # words containing hyphen (-) are looked up in the dictionary
        if self.tagger is not None and self.tagger.tag([s.replace('’', "'")])[0].is_tagged():
            # In the current POS tag, most apostrophes are curly: to be fixed
            return [s]
        if any(java_equals_ignore_case(s, e) for e in _HYPHENATED_EXCEPTIONS):
            return [s]
        # if not found, the word is split
        return string_tokenize(s, '-')
