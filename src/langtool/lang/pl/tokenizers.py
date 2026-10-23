"""Port of org.languagetool.tokenizers.pl.PolishWordTokenizer."""

from ...tokenizers import WordTokenizer, string_tokenize
from ...tools import is_digit, java_split

# Polish prefixes that should never be used to split parts of words
PREFIXES = frozenset((
    'arcy', 'neo',
    'pre', 'anty',
    'eks', 'bez',
    'beze', 'ekstra',
    'hiper', 'infra',
    'kontr', 'maksi',
    'midi', 'między',
    'mini', 'nad',
    'nade', 'około',
    'ponad', 'post',
    'pro', 'przeciw',
    'pseudo', 'super',
    'śród', 'ultra',
    'wice', 'wokół',
    'wokoło',
))


class PolishWordTokenizer(WordTokenizer):
    """Tokenizes text. The Polish tokenizer differs from the standard one in
    the following respects: it does not treat the hyphen as part of the word
    if the hyphen is at the end of the word; it includes n-dash and the
    single low quotation mark as tokenizing characters; it splits (with the
    tagger set by set_tagger()) two kinds of compound words containing a
    hyphen, such as "dziecko-geniusz" (two nouns), "polsko-indonezyjski" (an
    ad-adjectival adjective and adjective), "polsko-francusko-niemiecki"
    (two ad-adjectival adjectives and adjective), or
    "osiemnaście-dwadzieścia" (two numerals), and numbers like "1-10", but
    not words in which the hyphen occurs before a morphological ending (such
    as "SMS-y")."""

    def __init__(self):
        super().__init__()
        self._pl_tokenizing = frozenset(self.get_tokenizing_characters() + '–‚')  # n-dash
        self.tagger = None

    def set_tagger(self, tagger):
        """Set the tagger to use in tokenizing (the Polish tagger), needed
        for the hybrid hyphen-tokenizing."""
        self.tagger = tagger

    def tokenize(self, text):
        return self.join_emails_and_urls(self._tokenize(text))

    def _tokenize(self, text):
        out = []
        for token in string_tokenize(text, self._pl_tokenizing):
            if len(token) > 1:
                if token.endswith('-'):
                    out.append(token[:-1])
                    out.append('-')
                elif token[0] == '-':
                    out.append('-')
                    # (the recursive call of Java's tokenize() joins e-mails
                    # and URLs of the rest)
                    out.extend(self.tokenize(token[1:]))
                elif '-' in token:
                    self._split_hyphenated(token, out)
                else:
                    out.append(token)
            else:
                out.append(token)
        return out

    def _split_hyphenated(self, token, out):
        token_parts = java_split(token, '-')
        if token_parts[0] in PREFIXES or self.tagger is None:
            out.append(token)
        elif is_digit(token_parts[-1][0]):
            # split numbers at dash or minus sign, 1-10
            self._add_parts(token_parts, out)
        else:
            tested_tokens = list(token_parts)
            tested_tokens.append(token)
            tagged_toks = self.tagger.tag(tested_tokens)
            n = len(token_parts)
            if len(tagged_toks) == n + 1 and not tagged_toks[n].is_tagged():
                is_compound = False
                if n == 2:
                    if ((tagged_toks[0].has_pos_tag('adja')  # "niemiecko-indonezyjski"
                         and tagged_toks[1].has_partial_pos_tag('adj:'))
                            or (tagged_toks[0].has_partial_pos_tag('subst:')  # "kobieta-wojownik"
                                and tagged_toks[1].has_partial_pos_tag('subst:'))
                            or (tagged_toks[0].has_partial_pos_tag('num:')  # osiemnaście-dwadzieścia
                                and tagged_toks[1].has_partial_pos_tag('num:'))):
                        is_compound = True
                elif n == 3:
                    if (tagged_toks[0].has_pos_tag('adja')
                            and tagged_toks[1].has_pos_tag('adja')
                            and tagged_toks[2].has_partial_pos_tag('adj:')):
                        is_compound = True
                if is_compound:
                    self._add_parts(token_parts, out)
                else:
                    out.append(token)
            else:
                out.append(token)

    @staticmethod
    def _add_parts(token_parts, out):
        for i, part in enumerate(token_parts):
            out.append(part)
            if i != len(token_parts) - 1:
                out.append('-')
