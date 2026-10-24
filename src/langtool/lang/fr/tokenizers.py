"""Port of org.languagetool.tokenizers.fr.FrenchWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer, string_tokenize

_WORD_CHARACTERS = '§©@€£\\$_\\p{L}\\d\\-̀-ͯ¨⁰-₟°%‰‱&�­¬'
_TOKENIZER_PATTERN = jregex.compile('[' + _WORD_CHARACTERS + ']+|[^' + _WORD_CHARACTERS + ']')

# Patterns to avoid splitting words in certain special cases

_CI = jregex.IGNORECASE
# apostrophe
_TYPEWRITER_APOSTROPHE = jregex.compile("([\\p{L}])'([\\p{L}1\"‘“«])", _CI)
_TYPOGRAPHIC_APOSTROPHE = jregex.compile("([\\p{L}])’([\\p{L}1\"‘“«])", _CI)
# nearby hyphens.
_NEARBY_HYPHENS = jregex.compile('([\\p{L}])-([\\p{L}])-([\\p{L}])', _CI)
# hyphens.
_HYPHENS = jregex.compile('([\\p{L}])-([\\p{L}\\d])', _CI)
# decimal point between digits
_DECIMAL_POINT = jregex.compile('([\\d])\\.([\\d])', _CI)
# decimal comma between digits
_DECIMAL_COMMA = jregex.compile('([\\d]),([\\d])', _CI)
# space between digits
# the first is an exception to the two next patterns
_SPACE_DIGITS0 = jregex.compile('([\\d]{4}) ', _CI)
_SPACE_DIGITS = jregex.compile('([\\d]) ([\\d][\\d][\\d])\\b', _CI)
_SPACE_DIGITS2 = jregex.compile('([\\d]) ([\\d][\\d][\\d]) ([\\d][\\d][\\d])\\b', _CI)

_DO_NOT_SPLIT = frozenset((
    'mers-cov', 'mcgraw-hill', 'sars-cov-2', 'sars-cov', 'ph-metre', 'ph-metres', 'anti-ivg', 'anti-uv', 'anti-vih',
    'al-qaïda', "c'est-à-dire", 'add-on', 'add-ons', 'rendez-vous', 'garde-à-vous', 'chez-eux', 'chez-moi',
    'chez-nous', 'chez-soi', 'chez-toi', 'chez-vous', "m'as-tu-vu"))

_PRONOUNS = ('-ce|-elle|-t-elle|-elles|-t-elles|-en|-il|-t-il|-ils|-t-ils|-je|-la|-le|-les|-leur|-lui|-moi|-nous|'
             '-on|-t-on|-toi|-tu|-vous|-vs|-y')
_ELIDED = "[cç]['’]|j['’]|n['’]|m['’]|t['’]|s['’]|l['’]|d['’]|qu['’]|jusqu['’]|lorsqu['’]|puisqu['’]|quoiqu['’]"
_PATTERNS = (
    # words not to be split
    jregex.compile("^(c['’]te?|m['’]as-tu-vu|c['’]est-à-dire|add-on|add-ons|rendez-vous|garde-à-vous|chez-eux|"
                   "chez-moi|chez-nous|chez-soi|chez-toi|chez-vous)$", _CI),
    jregex.compile('^(' + _ELIDED + ')([^\\-]*)(' + _PRONOUNS + ')$', _CI),
    # Apostrophe at the beginning of a word. ce, je, ne, me, te, se, le, la, de, que, si // NO: presqu['’] |quelqu['’]
    # It creates 2 tokens: <token>l'</token><token>homme</token>
    jregex.compile('^(' + _ELIDED + ")([^'’\\-].*)$", _CI),
    jregex.compile('^([^\\-\\d]+)(-ce|-t-elle|-t-elles|-elle|-elles|-en|-il|-t-il|-ils|-t-ils|-je|-la|-le|-les|'
                   '-leur|-lui|-moi|-nous|-on|-t-on|-toi|-tu|-vous|-vs|-y)(' + _PRONOUNS + ')$', _CI),
    jregex.compile("^([^\\-]*)(-t|-m)(['’]en|['’]y)$", _CI),
    jregex.compile('^(.*)(-t-elle|-t-elles|-t-il|-t-ils|-t-on)$', _CI),
    jregex.compile('^(.*)(' + _PRONOUNS + ')$', _CI),
)


class FrenchWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words. Punctuation and whitespace get its
    own token. Special treatment for hyphens and apostrophes in French:
    elided words (l', qu', ...) and the pronouns after verbs (-t-il, -moi,
    ...) are separate tokens, other words with hyphens are split unless the
    tagger (FrenchTagger.INSTANCE in Java, the tagger given to the
    constructor here) knows them; decimal points and commas and the spaces
    of numbers like "1 000 000" are kept inside the tokens. Variation
    selectors (U+FE00..U+FE0F) are joined to the previous token."""

    def __init__(self, tagger=None):
        super().__init__()
        self.tagger = tagger

    def tokenize(self, text):
        tokens = []
        # replace hyphen, non-break hyphen -> hyphen-minus
        aux_text = text.replace('‐', '-').replace('‑', '-')
        aux_text = jregex.java_replace(_TYPEWRITER_APOSTROPHE, '$1xxFR_APOS_TYPEWxx$2', aux_text)
        aux_text = jregex.java_replace(_TYPOGRAPHIC_APOSTROPHE, '$1xxFR_APOS_TYPOGxx$2', aux_text)
        aux_text = jregex.java_replace(_NEARBY_HYPHENS, '$1xxFR_HYPHENxx$2xxFR_HYPHENxx$3', aux_text)
        aux_text = jregex.java_replace(_HYPHENS, '$1xxFR_HYPHENxx$2', aux_text)
        aux_text = jregex.java_replace(_DECIMAL_POINT, '$1xxFR_DECIMALPOINTxx$2', aux_text)
        aux_text = jregex.java_replace(_DECIMAL_COMMA, '$1xxFR_DECIMALCOMMAxx$2', aux_text)
        aux_text = jregex.java_replace(_SPACE_DIGITS2, '$1xxFR_SPACExx$2xxFR_SPACExx$3', aux_text)
        aux_text = jregex.java_replace(_SPACE_DIGITS0, '$1xxFR_SPACE0xx', aux_text)
        aux_text = jregex.java_replace(_SPACE_DIGITS, '$1xxFR_SPACExx$2', aux_text)
        aux_text = aux_text.replace('xxFR_SPACE0xx', ' ')
        for m in _TOKENIZER_PATTERN.finditer(aux_text):
            s = m.group()
            if tokens and len(s) == 1 and 0xFE00 <= ord(s) <= 0xFE0F:
                tokens[-1] = tokens[-1] + s
                continue
            s = (s.replace('xxFR_APOS_TYPEWxx', "'").replace('xxFR_APOS_TYPOGxx', '’')
                 .replace('xxFR_HYPHENxx', '-').replace('xxFR_DECIMALPOINTxx', '.')
                 .replace('xxFR_DECIMALCOMMAxx', ',').replace('xxFR_SPACExx', ' '))
            while len(s) > 1 and s.startswith('-'):
                tokens.append('-')
                s = s[1:]
            hyphens_at_end = 0
            while len(s) > 1 and s.endswith('-'):
                s = s[:-1]
                hyphens_at_end += 1
            for p in _PATTERNS:
                pm = p.search(s)
                if pm:
                    for group in pm.groups():
                        tokens.extend(self._words_to_add(group))
                    break
            else:
                tokens.extend(self._words_to_add(s))
            tokens.extend('-' * hyphens_at_end)
        return self.join_emails_and_urls(tokens)

    def _words_to_add(self, s):
        """Splits a word containing hyphen(-) if it doesn't exist in the
        dictionary."""
        if not s:
            return []
        if '-' not in s:
            return [s]
        # words containing hyphen (-) are looked up in the dictionary
        normalized = s.replace('­', '').replace('’', "'")
        if self.tagger is not None and self.tagger.tag([normalized])[0].is_tagged():
            # In the current POS tag, most apostrophes are curly: to be fixed
            return [s]
        # some camel-case words containing hyphen (is there any better fix?)
        if s.lower() in _DO_NOT_SPLIT:
            return [s]
        # if not found, the word is split
        return string_tokenize(s, '-')
