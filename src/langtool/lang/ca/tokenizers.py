"""Port of org.languagetool.tokenizers.ca.CatalanWordTokenizer."""

from ... import jregex
from ...tokenizers import WordTokenizer, string_tokenize
from ...tools import java_equals_ignore_case

_F = jregex.IGNORECASE | jregex.UNICODE_CHARACTER_CLASS
_WORD_CHARACTERS = '§©@€£\\$_\\p{L}\\d·\\-̀-ͯ¨⁰-₟°%‰‱&�­¬'
_TOKENIZER_PATTERN = jregex.compile('[' + _WORD_CHARACTERS + ']+|[^' + _WORD_CHARACTERS + ']')
# all possible forms of "pronoms febles" after a verb.
_PF = ("(['’]en|['’]hi|['’]ho|['’]l|['’]ls|['’]m|['’]n|['’]ns|['’]s|['’]t|-el|-els|-em|-en|-ens|-hi|-ho|-l|-la|"
       "-les|-li|-lo|-los|-m|-me|-n|-ne|-nos|-s|-se|-t|-te|-us|-vos)")

# Patterns to avoid splitting words in certain special cases
# allows correcting typographical errors in "ela geminada"
_ELA_GEMINADA = jregex.compile(
    '([aeiouàéèíóòúïüAEIOUÀÈÉÍÒÓÚÏÜ])l[\\.•⋅∙]l([aeiouàéèíóòúïü])',
    jregex.UNICODE_CHARACTER_CLASS)
_ELA_GEMINADA_UPPERCASE = jregex.compile(
    '([AEIOUÀÈÉÍÒÓÚÏÜ])L[\\.•⋅∙]L([AEIOUÀÈÉÍÒÓÚÏÜ])', jregex.UNICODE_CHARACTER_CLASS)
# apostrophe
_APOSTROF_RECTE = jregex.compile("([\\p{L}])'([\\p{L}\"‘“«])", _F)
_APOSTROF_RODO = jregex.compile('([\\p{L}])’([\\p{L}"‘“«])', _F)
# apostrophe before number 1. Ex.: d'1 km, és l'1 de gener, és d'1.4 kg
_APOSTROF_RECTE_1 = jregex.compile("([dlDL])'(\\d[\\d\\s\\.,]?)", _F)
_APOSTROF_RODO_1 = jregex.compile('([dlDL])’(\\d[\\d\\s\\.,]?)', _F)
# decimal point between digits
_DECIMAL_POINT = jregex.compile('([\\d])\\.([\\d])', _F)
# decimal comma between digits
_DECIMAL_COMMA = jregex.compile('([\\d]),([\\d])', _F)
# space between digits
# the first is an exception to the two next patterns
_SPACE_DIGITS0 = jregex.compile('([\\d]{4}) ', _F)
_SPACE_DIGITS = jregex.compile('([\\d]) ([\\d][\\d][\\d])', _F)
_SPACE_DIGITS2 = jregex.compile('([\\d]) ([\\d][\\d][\\d]) ([\\d][\\d][\\d])', _F)
# Sàsser-l'Alguer
_HYPHEN_L = jregex.compile("([\\p{L}]+)(-)([Ll]['’])([\\p{L}]+)", _F)

_PATTERNS = (
    # Apostrophe at the beginning of a word. Ex.: l'home, s'estima, n'omple, hivern, etc.
    # It creates 2 tokens: <token>l'</token><token>home</token>
    jregex.compile("^([lnmtsd]['’])([^'’\\-]*)$", _F),
    # Exceptions to (Match verb+1 pronom feble)
    # It creates 1 token: <token>qui-sap-lo</token>
    jregex.compile('^(qui-sap-lo|qui-sap-la|qui-sap-los|qui-sap-les)|(Castella)(-)(la)$', _F),
    # Match verb+3 pronoms febles (rare but possible!). Ex: Emporta-te'ls-hi.
    # It creates 4 tokens: <token>Emporta</token><token>-te</token><token>'ls</token><token>-hi</token>
    jregex.compile("^([lnmtsd]['’])(.{2,})" + _PF + _PF + _PF + '$', _F),
    jregex.compile('^(.{2,})' + _PF + _PF + _PF + '$', _F),
    # Match verb+2 pronoms febles. Ex: Emporta-te'ls.
    # It creates 3 tokens: <token>Emporta</token><token>-te</token><token>'ls</token>
    jregex.compile("^([lnmtsd]['’])(.{2,})" + _PF + _PF + '$', _F),
    jregex.compile('^(.{2,})' + _PF + _PF + '$', _F),
    # match verb+1 pronom feble. Ex: Emporta't, vés-hi, porta'm.
    # It creates 2 tokens: <token>Emporta</token><token>'t</token>
    jregex.compile("^([lnmtsd]['’])(.{2,})" + _PF + '$', _F),
    jregex.compile('^(.+[^wo])' + _PF + '$', _F),
    # d'emportar
    jregex.compile("^([lnmtsd]['’])(.*)$", _F),
)

# some camel-case words containing hyphen (is there any better fix?)
_HYPHENATED_EXCEPTIONS = ('mers-cov', 'mcgraw-hill', 'sars-cov-2', 'sars-cov', 'ph-metre', 'ph-metres')


class CatalanWordTokenizer(WordTokenizer):
    """Tokenizes a sentence into words. Punctuation and whitespace gets its
    own token. Special treatment for hyphens and apostrophes in Catalan:
    apostrophes and the weak pronouns after verbs ("pronoms febles") are
    split from the words (l'home -> l' home, emporta-te'ls -> emporta -te
    'ls), the contractions al, als, del, dels, pel, pels and can are split
    (a l, de ls, ...); decimal points and commas between digits, spaces
    between groups of digits and the "ela geminada" with a wrong middle dot
    are kept inside the tokens. Words with hyphens are split at the hyphens
    unless the tagger (CatalanTagger.INSTANCE_CAT in Java, the tagger given
    to the constructor here) knows them."""

    def __init__(self, tagger=None):
        super().__init__()
        self.tagger = tagger

    def tokenize(self, text):
        tokens = []
        # replace hyphen, non-break hyphen -> hyphen-minus
        aux_text = text.replace('‐', '-').replace('‑', '-')
        # replace  'MODIFIER LETTER APOSTROPHE' (U+02BC) -> typographical apostrophe
        aux_text = aux_text.replace('ʼ', '’')
        aux_text = jregex.java_replace(_ELA_GEMINADA, '$1xxELA_GEMINADAxx$2', aux_text)
        aux_text = jregex.java_replace(_ELA_GEMINADA_UPPERCASE, '$1xxELA_GEMINADA_UPPERCASExx$2', aux_text)
        aux_text = jregex.java_replace(_APOSTROF_RECTE, '$1xxCA_APOS_RECTExx$2', aux_text)
        aux_text = jregex.java_replace(_APOSTROF_RECTE_1, '$1xxCA_APOS_RECTExx$2', aux_text)
        aux_text = jregex.java_replace(_APOSTROF_RODO, '$1xxCA_APOS_RODOxx$2', aux_text)
        aux_text = jregex.java_replace(_APOSTROF_RODO_1, '$1xxCA_APOS_RODOxx$2', aux_text)
        aux_text = jregex.java_replace(_DECIMAL_POINT, '$1xxCA_DECIMALPOINTxx$2', aux_text)
        aux_text = jregex.java_replace(_DECIMAL_COMMA, '$1xxCA_DECIMALCOMMAxx$2', aux_text)
        aux_text = jregex.java_replace(_SPACE_DIGITS0, '$1xxCA_SPACE0xx', aux_text)
        aux_text = jregex.java_replace(_SPACE_DIGITS2, '$1xxCA_SPACExx$2xxCA_SPACExx$3', aux_text)
        aux_text = jregex.java_replace(_SPACE_DIGITS, '$1xxCA_SPACExx$2', aux_text)
        aux_text = aux_text.replace('xxCA_SPACE0xx', ' ')
        for m in _TOKENIZER_PATTERN.finditer(aux_text):
            s = m.group()
            if tokens and len(s) == 1 and 0xFE00 <= ord(s) <= 0xFE0F:
                tokens[-1] = tokens[-1] + s
                continue
            s = s.replace('xxCA_APOS_RECTExx', "'").replace('xxCA_APOS_RODOxx', '’').replace('xxCA_HYPHENxx', '-')
            s = s.replace('xxCA_DECIMALPOINTxx', '.').replace('xxCA_DECIMALCOMMAxx', ',')
            s = s.replace('xxCA_SPACExx', ' ').replace('xxELA_GEMINADAxx', 'l.l')
            s = s.replace('xxELA_GEMINADA_UPPERCASExx', 'L.L')
            matcher = None
            while len(s) > 1 and s.startswith('-'):
                tokens.append('-')
                s = s[1:]
            hyphens_at_end = 0
            while len(s) > 1 and s.endswith('-'):
                s = s[:-1]
                hyphens_at_end += 1
            # patterns need an apostrophe or hyphen; contractions (al, als, del, dels, pel, pels, can) are
            # short plain words
            contraction_handled = False
            if "'" in s or '’' in s or '-' in s:
                for p in _PATTERNS:
                    matcher = p.search(s)
                    if matcher is not None:
                        break
            elif len(s) <= 4:
                # split_index: 1 for al/als (a+l/ls), 2 for del/dels/pel/pels/can (de/pe/ca+l/ls/n)
                if java_equals_ignore_case(s, 'al') or java_equals_ignore_case(s, 'als'):
                    split_index = 1
                elif any(java_equals_ignore_case(s, w) for w in ('del', 'dels', 'pel', 'pels', 'can')):
                    split_index = 2
                else:
                    split_index = -1
                if split_index > 0:
                    tokens.append(s[:split_index])
                    tokens.append(s[split_index:])
                    contraction_handled = True
            if not contraction_handled:
                if matcher is not None:
                    for group_str in matcher.groups():
                        if group_str is not None:
                            tokens.extend(self._words_to_add(group_str))
                else:
                    tokens.extend(self._words_to_add(s))
            tokens.extend('-' * hyphens_at_end)
        return self.join_emails_and_urls(tokens)

    def _is_tagged(self, word):
        return self.tagger is not None and self.tagger.tag([word])[0].is_tagged()

    def _words_to_add(self, s):
        """Splits a word containing hyphen(-) if it doesn't exist in the
        dictionary. Split apostrophe in the last char"""
        if not s:
            return []
        if '-' not in s and not s.endswith("'") and not s.endswith('’'):
            return [s]
        # words containing hyphen (-) are looked up in the dictionary
        if self._is_tagged(s.replace('­', '').replace('’', "'")):
            return [s]
        # some camel-case words containing hyphen (is there any better fix?)
        if any(java_equals_ignore_case(s, e) for e in _HYPHENATED_EXCEPTIONS):
            return [s]
        # words with "ela geminada" with typo: col-legi (col·legi)
        if self._is_tagged(s.replace('­', '').replace('l-l', 'l·l')):
            return [s]
        # apostrophe in the last char
        if (s.endswith("'") or s.endswith('’')) and len(s) > 1:
            return self._words_to_add(s[:-1]) + [s[-1]]
        m = _HYPHEN_L.fullmatch(s)
        if m:
            out = []
            for group_str in m.groups():
                out.extend(self._words_to_add(group_str))
            return out
        # if not found, the word is split
        return string_tokenize(s, '-')
