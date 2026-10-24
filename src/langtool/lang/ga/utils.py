"""Irish helper utilities: port of org.languagetool.tagging.ga.Utils and
org.languagetool.tagging.ga.Retaggable (initial mutations, Irish case
folding, pre-standard dotted consonants, mathematical/halfwidth letters,
Greek lookalikes).

Java works on UTF-16 chars; the functions that deal with mathematical
alphanumeric symbols (surrogate pairs) work on UTF-16 code units here too.
Java's String.toLowerCase() (default locale) is str.lower() here."""

from ... import jregex
from ...tools import is_letter, is_lower_case, is_upper_case


class Retaggable:
    """Port of org.languagetool.tagging.ga.Retaggable: a candidate word for
    retagging, with a regex restricting the POS tags it may get, a tag
    suffix to append and an optional prefix."""

    __slots__ = ('word', 'restrict_to_pos', 'append_tag', 'prefix')

    def __init__(self, word, restrict_to_pos, append_tag, prefix=None):
        if word is None:
            raise TypeError('word must not be null')
        self.word = word
        self.restrict_to_pos = restrict_to_pos
        self.append_tag = append_tag
        self.prefix = prefix

    def set_append_tag(self, append_tag):
        if self.append_tag is None or self.append_tag == '':
            self.append_tag = append_tag
        else:
            self.append_tag = self.append_tag + append_tag

    def set_restrict_to_pos(self, restrict_to_pos):
        if self.restrict_to_pos is None or self.restrict_to_pos == '':
            self.restrict_to_pos = restrict_to_pos
        else:
            self.restrict_to_pos = self.restrict_to_pos + '|' + restrict_to_pos

    def __repr__(self):
        return 'Retaggable(%r, %r, %r, %r)' % (self.word, self.restrict_to_pos, self.append_tag, self.prefix)


# Utils.SuffixGuess: (suffix, suffixReplacement, restrictToTags, appendTags)
_GUESSES = (
    ('éaracht', 'éireacht', '.*Noun.*', ':MorphError'),
    ('éarachta', 'éireachta', '.*Noun.*', ':MorphError'),
    ('eamhail', 'iúil', '.*Noun.*|.*Adj.*', ':MorphError'),
    ('eamhuil', 'iúil', '.*Noun.*|.*Adj.*', ':MorphError'),
    ('eamhla', 'iúla', '.*Noun.*|.*Adj.*', ':MorphError'),
    ('amhail', 'úil', '.*Noun.*|.*Adj.*', ':MorphError'),
    ('amhuil', 'úil', '.*Noun.*|.*Adj.*', ':MorphError'),
)


def fix_suffix(s):
    for suffix, replacement, restrict, append in _GUESSES:
        if s.endswith(suffix):
            base = s[:len(s) - len(suffix)]
            return Retaggable(base + replacement, restrict, append)
    return Retaggable(s, '', '')


def morph_word(s):
    out = []
    # First, mutations
    mut = demutate(s)
    if mut.append_tag in (':Len:MorphError', ':Ecl:MorphError', ':EclLen'):
        out.append(mut)
        out.append(Retaggable(mut.word, mut.restrict_to_pos, ':DefArt:MorphError'))
    elif mut.append_tag != '':
        out.append(mut)
    # Second, suffixes
    sfx = fix_suffix(mut.word)
    if sfx.append_tag != '':
        sfx.set_append_tag(mut.append_tag)
        out.append(sfx)
    # TODO: prefix corrections
    # TODO: other alterations
    return out


def demutate(s):
    out = un_lenite_definite_s(s)
    if out is not None:
        return Retaggable(out, '(?:C[UMC]:)?Noun:.*:DefArt', ':MorphError')
    out = un_lenite(s)
    if out is not None:
        return Retaggable(out, '', ':Len:MorphError')
    out = un_eclipse(s)
    if out is not None:
        out2 = un_lenite(out)
        if out2 is None:
            return Retaggable(out, '', ':Ecl:MorphError')
        return Retaggable(out2, '', ':EclLen')
    return Retaggable(s, '', '')


def un_eclipse(s):
    if len(s) > 2:
        ch1 = s[1]
        c0 = s[0]
        if c0 in 'Nn':
            if len(s) > 3 and s[1] == '-':
                ch1 = s[2]
            if ch1 in 'GDgd' or is_upper_vowel(ch1) or is_lower_vowel(ch1):
                return un_eclipse_char(s, 'n', ch1.lower())
            return None
        if c0 in 'Bb':
            if ch1 in 'pP' or (len(s) > 3 and s[1] == '-'):
                return un_eclipse_char(s, 'b', 'p')
            return un_eclipse_f(s)
        if c0 in 'Dd':
            return un_eclipse_char(s, 'd', 't')
        if c0 in 'Gg':
            return un_eclipse_char(s, 'g', 'c')
        if c0 in 'Mm':
            return un_eclipse_char(s, 'm', 'b')
    return None


def un_lenite(s):
    """Attempts to unlenite a string (see lenite()). Deliberately does not
    check if the first character is one that ought to be lenited (this can be
    checked in XML rules)."""
    if len(s) < 2:
        return None
    if s[1] in 'hH':
        return s[0] + s[2:]
    return None


_DEF_S_UPPERS = ('Ts', 'T-s', 'TS', 'T-S', 't-S', 'tS')
_DEF_S_LOWERS = ('ts', 't-s')


def un_lenite_definite_s(s):
    """Removes lenition from a word beginning with 's', following the
    definite article; as an exception to conventional lenition, this is a
    't' prefix. The standard representation is a lowercase 't', regardless
    of the case of the word; this function additionally checks for
    incorrect (e.g., capital 'T') and prestandard (e.g., hyphenated 't-')
    versions."""
    for start in _DEF_S_UPPERS:
        if s.startswith(start):
            return 'S' + s[len(start):]
    for start in _DEF_S_LOWERS:
        if s.startswith(start):
            return 's' + s[len(start):]
    return None


_F_UPPERS = ('Bhf', 'bhF', 'Bf', 'bhF', 'bF', 'Bh-f', 'bh-F', 'B-f', 'bh-F', 'b-F')
_F_LOWERS = ('bhf', 'bh-f', 'bf', 'b-f')


def un_eclipse_f(s):
    for start in _F_UPPERS:
        if s.startswith(start):
            return 'F' + s[len(start):]
    for start in _F_LOWERS:
        if s.startswith(start):
            return 'f' + s[len(start):]
    return None


def un_eclipse_char(s, first, second):
    """Helper to uneclipse single-letter consonant eclipsis (i.e., not
    bhfear or n-éin), handling miscapitalised eclipsed words: Gcarr -> Carr,
    etc. Returns the uneclipsed word or None if there is no match."""
    frm = 2
    upper_first = first.upper()
    upper_second = second.upper()
    ret_second = upper_second if s[0] == upper_first else second
    # bail out if there's nothing to do
    if len(s) < 2:
        return None
    # no match
    if s[0] != first and s[0] != upper_first:
        return None
    # properly eclipsed
    if s[0] == first and (s[1] == second or s[1] == upper_second):
        return s[1:]
    ch1 = s[1]
    if len(s) > 3 and s[1] == '-':
        frm += 1
        ch1 = s[2]
    if ch1 == second or ch1 == upper_second:
        return ret_second + s[frm:]
    return None


_UPPER_VOWELS = frozenset('AEIOUÁÉÍÓÚ')
_LOWER_VOWELS = frozenset('aeiouáéíóú')
_UPPER_LENITABLE = frozenset('BCDFGMPST')
_LOWER_LENITABLE = frozenset('bcdfgmpst')
_S_LENITABLE = frozenset('lnraeiouáéíóú')


def is_upper_vowel(c):
    return c in _UPPER_VOWELS


def is_lower_vowel(c):
    return c in _LOWER_VOWELS


def is_vowel(c):
    return is_lower_vowel(c) or is_upper_vowel(c)


def is_upper_lenitable(c):
    return c in _UPPER_LENITABLE


def is_lower_lenitable(c):
    return c in _LOWER_LENITABLE


def is_s_lenitable(c):
    """The (non-definite) eclipsed form of 's', 'sh', is pronounced like 'h'
    in English; words beginning with 's' can only have lenition applied if
    the following letter (c) would be easily pronounced after this sound."""
    return c in _S_LENITABLE


def lenite(s):
    """Lenites a word ("lenition" in Irish grammar is an initial mutation,
    written as an 'h' after the initial consonant). Returns the lenited
    form, or the unmodified string if it cannot be lenited."""
    if len(s) < 2:
        return s
    # Java: (Character.isUpperCase(in.charAt(0)) && Character.isUpperCase(1)) ? "H" : "h" -- the second
    # check is on the code point 1, which is never uppercase, so it is always "h"
    outh = 'h'
    c0 = s[0]
    if is_lower_lenitable(c0) or is_upper_lenitable(c0):
        if c0 in 'Ss':
            if is_s_lenitable(s[1].lower()):
                return c0 + outh + s[1:]
            return s
        return c0 + outh + s[1:]
    return s


def eclipse(s):
    """Eclipses a word ("eclipsis" in Irish grammar is an initial mutation,
    represented as a prefix to the word: 'focal' becomes 'bhfocal'; with
    vowels an initial 'n' is added, hyphenated before a lowercase word).
    Returns the eclipsed form, or the unmodified string if it cannot be
    eclipsed."""
    if s is None or s == '':
        return s
    if is_upper_vowel(s[0]):
        return 'n' + s
    if is_lower_vowel(s[0]):
        return 'n-' + s
    c = s.lower()[0]
    if c == 'b':
        return 'm' + s
    if c == 'c':
        return 'g' + s
    if c in 'dg':
        return 'n' + s
    if c == 'f':
        return 'bh' + s
    if c == 'p':
        return 'b' + s
    if c == 't':
        return 'd' + s
    return s


def _is_bmp_letter(c):
    # Character.isLetter(char): the surrogates of supplementary characters are no letters
    return c <= '\uffff' and is_letter(c)


def _is_bmp_upper(c):
    # Character.isUpperCase(char)
    return c <= '\uffff' and is_upper_case(c)


def to_lower_case_irish(s):
    """Case folding in Irish is non-trivial: initial mutations that prefix
    the word are always written in lowercase; 'n' and 't' are written with a
    hyphen before a lowercase vowel."""
    if len(s) > 1 and s[0] in 'nt' and is_upper_vowel(s[1]):
        return s[0] + '-' + s[1:].lower()
    return s.lower()


def starts_with_uppercase(s):
    """StringTools.startsWithUppercase adapted for Irish case folding
    oddities (initial mutations which must remain lowercase)."""
    if _starts_with_mutated_uppercase(s):
        return True
    # otherwise, as normal
    return _is_bmp_upper(s[0])


def is_all_uppercase(s):
    start_from = 0
    if _starts_with_mutated_uppercase(s):
        start_from = 2 if s.startswith('bhF') else 1
    for c in s[start_from:]:
        if _is_bmp_letter(c) and is_lower_case(c):
            return False
    return True


def _starts_with_mutated_uppercase(s):
    # Consonant eclipsis
    if s.startswith(('mB', 'gC', 'nD', 'bhF', 'nG', 'bP', 'dT')):
        return True
    # Vowel eclipsis, t-prothesis, h-prothesis
    if len(s) > 1 and s[0] in 'nth' and is_upper_vowel(s[1]):
        return True
    # definite s lenition
    return s.startswith('tS')


_PONC = {'Ḃ': 'B', 'Ċ': 'C', 'Ḋ': 'D', 'Ḟ': 'F', 'Ġ': 'G', 'Ṁ': 'M', 'Ṗ': 'P', 'Ṡ': 'S', 'Ṫ': 'T',
         'ḃ': 'b', 'ċ': 'c', 'ḋ': 'd', 'ḟ': 'f', 'ġ': 'g', 'ṁ': 'm', 'ṗ': 'p', 'ṡ': 's', 'ṫ': 't'}
_UPPER_PONC = frozenset('ḂĊḊḞĠṀṖṠṪ')
_LOWER_PONC = frozenset('ḃċḋḟġṁṗṡṫ')


def is_ponc(c):
    """Check if the character is dotted ('ponc' in Irish)"""
    return c in _PONC


def contains_ponc(s):
    return any(c in _PONC for c in s)


def un_ponc(s):
    """Converts pre-standard lenition to modern (converts dotted (= ponc)
    letters to the equivalent undotted, followed by 'h')"""
    sb = []
    n = len(s)
    for i, c in enumerate(s):
        if c not in _PONC:
            sb.append(c)
        elif c in _LOWER_PONC:
            sb.append(_PONC[c])
            sb.append('h')
        elif i < n - 1 and _is_bmp_upper(s[i + 1]):
            sb.append(_PONC[c])
            sb.append('H')
        elif i == n - 1 and i > 0 and _is_bmp_upper(s[i - 1]):
            sb.append(_PONC[c])
            sb.append('H')
        else:
            sb.append(_PONC[c])
            sb.append('h')
    return ''.join(sb)


# --- mathematical alphanumeric symbols (low surrogates after \uD835) ---

MATHEMATICAL_BOLD_CAPITAL_A = 0xDC00
MATHEMATICAL_BOLD_CAPITAL_Z = 0xDC19
MATHEMATICAL_BOLD_SMALL_A = 0xDC1A
MATHEMATICAL_BOLD_SMALL_Z = 0xDC33
MATHEMATICAL_ITALIC_CAPITAL_A = 0xDC34
MATHEMATICAL_ITALIC_CAPITAL_Z = 0xDC4D
MATHEMATICAL_ITALIC_SMALL_A = 0xDC4E
MATHEMATICAL_ITALIC_SMALL_Z = 0xDC67
MATHEMATICAL_BOLD_ITALIC_CAPITAL_A = 0xDC68
MATHEMATICAL_BOLD_ITALIC_CAPITAL_Z = 0xDC81
MATHEMATICAL_BOLD_ITALIC_SMALL_A = 0xDC82
MATHEMATICAL_BOLD_ITALIC_SMALL_Z = 0xDC9B
MATHEMATICAL_SCRIPT_CAPITAL_A = 0xDC9C
MATHEMATICAL_SCRIPT_CAPITAL_Z = 0xDCB5
MATHEMATICAL_SCRIPT_SMALL_A = 0xDCB6
MATHEMATICAL_SCRIPT_SMALL_Z = 0xDCCF
MATHEMATICAL_BOLD_SCRIPT_CAPITAL_A = 0xDCD0
MATHEMATICAL_BOLD_SCRIPT_CAPITAL_Z = 0xDCE9
MATHEMATICAL_BOLD_SCRIPT_SMALL_A = 0xDCEA
MATHEMATICAL_BOLD_SCRIPT_SMALL_Z = 0xDD03
MATHEMATICAL_FRAKTUR_CAPITAL_A = 0xDD04
MATHEMATICAL_FRAKTUR_CAPITAL_Z = 0xDD1D
MATHEMATICAL_FRAKTUR_SMALL_A = 0xDD1E
MATHEMATICAL_FRAKTUR_SMALL_Z = 0xDD37
MATHEMATICAL_DOUBLESTRUCK_CAPITAL_A = 0xDD38
MATHEMATICAL_DOUBLESTRUCK_CAPITAL_Z = 0xDD51
MATHEMATICAL_DOUBLESTRUCK_SMALL_A = 0xDD52
MATHEMATICAL_DOUBLESTRUCK_SMALL_Z = 0xDD6B
MATHEMATICAL_BOLD_FRAKTUR_CAPITAL_A = 0xDD6C
MATHEMATICAL_BOLD_FRAKTUR_CAPITAL_Z = 0xDD85
MATHEMATICAL_BOLD_FRAKTUR_SMALL_A = 0xDD86
MATHEMATICAL_BOLD_FRAKTUR_SMALL_Z = 0xDD9F
MATHEMATICAL_SANSSERIF_CAPITAL_A = 0xDDA0
MATHEMATICAL_SANSSERIF_CAPITAL_Z = 0xDDB9
MATHEMATICAL_SANSSERIF_SMALL_A = 0xDDBA
MATHEMATICAL_SANSSERIF_SMALL_Z = 0xDDD3
MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_A = 0xDDD4
MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_Z = 0xDDED
MATHEMATICAL_SANSSERIF_BOLD_SMALL_A = 0xDDEE
MATHEMATICAL_SANSSERIF_BOLD_SMALL_Z = 0xDE07
MATHEMATICAL_SANSSERIF_ITALIC_CAPITAL_A = 0xDE08
MATHEMATICAL_SANSSERIF_ITALIC_CAPITAL_Z = 0xDE21
MATHEMATICAL_SANSSERIF_ITALIC_SMALL_A = 0xDE22
MATHEMATICAL_SANSSERIF_ITALIC_SMALL_Z = 0xDE3B
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_A = 0xDE3C
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_Z = 0xDE55
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_A = 0xDE56
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_Z = 0xDE6F
MATHEMATICAL_MONOSPACE_CAPITAL_A = 0xDE70
MATHEMATICAL_MONOSPACE_CAPITAL_Z = 0xDE89
MATHEMATICAL_MONOSPACE_SMALL_A = 0xDE8A
MATHEMATICAL_MONOSPACE_SMALL_Z = 0xDEA3
MATHEMATICAL_ITALIC_SMALL_DOTLESS_I = 0xDEA4
MATHEMATICAL_ITALIC_SMALL_DOTLESS_J = 0xDEA5
MATHEMATICAL_BOLD_CAPITAL_ALPHA = 0xDEA8
MATHEMATICAL_BOLD_CAPITAL_OMEGA = 0xDEC0
MATHEMATICAL_BOLD_SMALL_ALPHA = 0xDEC2
MATHEMATICAL_BOLD_SMALL_OMEGA = 0xDEDA
MATHEMATICAL_ITALIC_CAPITAL_ALPHA = 0xDEE2
MATHEMATICAL_ITALIC_CAPITAL_OMEGA = 0xDEFA
MATHEMATICAL_ITALIC_SMALL_ALPHA = 0xDEFC
MATHEMATICAL_ITALIC_SMALL_OMEGA = 0xDF14
MATHEMATICAL_BOLD_ITALIC_CAPITAL_ALPHA = 0xDF1C
MATHEMATICAL_BOLD_ITALIC_CAPITAL_OMEGA = 0xDF34
MATHEMATICAL_BOLD_ITALIC_SMALL_ALPHA = 0xDF36
MATHEMATICAL_BOLD_ITALIC_SMALL_OMEGA = 0xDF4E
MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_ALPHA = 0xDF56
MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_OMEGA = 0xDF6E
MATHEMATICAL_SANSSERIF_BOLD_SMALL_ALPHA = 0xDF70
MATHEMATICAL_SANSSERIF_BOLD_SMALL_OMEGA = 0xDF88
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_ALPHA = 0xDF90
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_OMEGA = 0xDFA8
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_ALPHA = 0xDFAA
MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_OMEGA = 0xDFC2
MATHEMATICAL_BOLD_DIGIT_ZERO = 0xDFCE
MATHEMATICAL_BOLD_DIGIT_NINE = 0xDFD7
MATHEMATICAL_DOUBLESTRUCK_DIGIT_ZERO = 0xDFD8
MATHEMATICAL_DOUBLESTRUCK_DIGIT_NINE = 0xDFE1
MATHEMATICAL_SANSSERIF_DIGIT_ZERO = 0xDFE2
MATHEMATICAL_SANSSERIF_DIGIT_NINE = 0xDFEB
MATHEMATICAL_SANSSERIF_BOLD_DIGIT_ZERO = 0xDFEC
MATHEMATICAL_SANSSERIF_BOLD_DIGIT_NINE = 0xDFF5
MATHEMATICAL_MONOSPACE_DIGIT_ZERO = 0xDFF6
MATHEMATICAL_MONOSPACE_DIGIT_NINE = 0xDFFF
CAPITAL_A = ord('A')
SMALL_A = ord('a')
CAPITAL_ALPHA = ord('Α')
SMALL_ALPHA = ord('α')
DIGIT_ZERO = ord('0')

_HIGH_SURROGATE_MATHS = 0xD835


def _utf16(s):
    """the UTF-16 code units of s"""
    b = s.encode('utf-16-le', 'surrogatepass')
    return [b[i] | (b[i + 1] << 8) for i in range(0, len(b), 2)]


def _from_utf16(units):
    return b''.join(u.to_bytes(2, 'little') for u in units).decode('utf-16-le', 'surrogatepass')


def is_all_maths_chars(s):
    units = _utf16(s)
    if len(units) % 2 != 0:
        return False
    for i, u in enumerate(units):
        if i % 2 == 0:
            if u != _HIGH_SURROGATE_MATHS:
                return False
        elif u < MATHEMATICAL_BOLD_CAPITAL_A or u > MATHEMATICAL_MONOSPACE_DIGIT_NINE:
            return False
    return True


_HALFWIDTH_LATIN_CAPITAL_A = ord('Ａ')
_HALFWIDTH_LATIN_CAPITAL_Z = ord('Ｚ')
_HALFWIDTH_LATIN_SMALL_A = ord('ａ')
_HALFWIDTH_LATIN_SMALL_Z = ord('ｚ')


def is_all_half_width_chars(s):
    for u in _utf16(s):
        if u < _HALFWIDTH_LATIN_CAPITAL_A:
            return False
        if _HALFWIDTH_LATIN_CAPITAL_Z < u < _HALFWIDTH_LATIN_SMALL_A:
            return False
        if u > _HALFWIDTH_LATIN_SMALL_Z:
            return False
    return True


def halfwidth_latin_to_latin(s):
    sb = []
    for c in s:
        v = ord(c)
        if _HALFWIDTH_LATIN_CAPITAL_A <= v <= _HALFWIDTH_LATIN_CAPITAL_Z:
            sb.append(chr(v - _HALFWIDTH_LATIN_CAPITAL_A + CAPITAL_A))
        elif _HALFWIDTH_LATIN_SMALL_A <= v <= _HALFWIDTH_LATIN_SMALL_Z:
            sb.append(chr(v - _HALFWIDTH_LATIN_SMALL_A + SMALL_A))
        else:
            sb.append(c)
    return ''.join(sb)


# getMathsChar: the Latin ranges, checked in order (upper bound, base, target)
_MATHS_LATIN = (
    (MATHEMATICAL_BOLD_CAPITAL_Z, MATHEMATICAL_BOLD_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_BOLD_SMALL_Z, MATHEMATICAL_BOLD_SMALL_A, SMALL_A),
    (MATHEMATICAL_ITALIC_CAPITAL_Z, MATHEMATICAL_ITALIC_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_ITALIC_SMALL_Z, MATHEMATICAL_ITALIC_SMALL_A, SMALL_A),
    (MATHEMATICAL_BOLD_ITALIC_CAPITAL_Z, MATHEMATICAL_BOLD_ITALIC_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_BOLD_ITALIC_SMALL_Z, MATHEMATICAL_BOLD_ITALIC_SMALL_A, SMALL_A),
    (MATHEMATICAL_SCRIPT_CAPITAL_Z, MATHEMATICAL_SCRIPT_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_SCRIPT_SMALL_Z, MATHEMATICAL_SCRIPT_SMALL_A, SMALL_A),
    (MATHEMATICAL_BOLD_SCRIPT_CAPITAL_Z, MATHEMATICAL_BOLD_SCRIPT_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_BOLD_SCRIPT_SMALL_Z, MATHEMATICAL_BOLD_SCRIPT_SMALL_A, SMALL_A),
    # Not all Fraktur capitals have valid characters, but include them anyway
    (MATHEMATICAL_FRAKTUR_CAPITAL_Z, MATHEMATICAL_FRAKTUR_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_FRAKTUR_SMALL_Z, MATHEMATICAL_FRAKTUR_SMALL_A, SMALL_A),
    (MATHEMATICAL_DOUBLESTRUCK_CAPITAL_Z, MATHEMATICAL_DOUBLESTRUCK_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_DOUBLESTRUCK_SMALL_Z, MATHEMATICAL_DOUBLESTRUCK_SMALL_A, SMALL_A),
    (MATHEMATICAL_BOLD_FRAKTUR_CAPITAL_Z, MATHEMATICAL_BOLD_FRAKTUR_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_BOLD_FRAKTUR_SMALL_Z, MATHEMATICAL_BOLD_FRAKTUR_SMALL_A, SMALL_A),
    (MATHEMATICAL_SANSSERIF_CAPITAL_Z, MATHEMATICAL_SANSSERIF_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_SANSSERIF_SMALL_Z, MATHEMATICAL_SANSSERIF_SMALL_A, SMALL_A),
    (MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_Z, MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_SANSSERIF_BOLD_SMALL_Z, MATHEMATICAL_SANSSERIF_BOLD_SMALL_A, SMALL_A),
    (MATHEMATICAL_SANSSERIF_ITALIC_CAPITAL_Z, MATHEMATICAL_SANSSERIF_ITALIC_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_SANSSERIF_ITALIC_SMALL_Z, MATHEMATICAL_SANSSERIF_ITALIC_SMALL_A, SMALL_A),
    (MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_Z, MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_Z, MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_A, SMALL_A),
    (MATHEMATICAL_MONOSPACE_CAPITAL_Z, MATHEMATICAL_MONOSPACE_CAPITAL_A, CAPITAL_A),
    (MATHEMATICAL_MONOSPACE_SMALL_Z, MATHEMATICAL_MONOSPACE_SMALL_A, SMALL_A),
)

# (first, last, target) of the Greek ranges (normaliseGreek)
_MATHS_GREEK = (
    (MATHEMATICAL_BOLD_CAPITAL_ALPHA, MATHEMATICAL_BOLD_CAPITAL_OMEGA, CAPITAL_ALPHA),
    (MATHEMATICAL_BOLD_SMALL_ALPHA, MATHEMATICAL_BOLD_SMALL_OMEGA, SMALL_ALPHA),
    (MATHEMATICAL_ITALIC_CAPITAL_ALPHA, MATHEMATICAL_ITALIC_CAPITAL_OMEGA, CAPITAL_ALPHA),
    (MATHEMATICAL_ITALIC_SMALL_ALPHA, MATHEMATICAL_ITALIC_SMALL_OMEGA, SMALL_ALPHA),
    (MATHEMATICAL_BOLD_ITALIC_CAPITAL_ALPHA, MATHEMATICAL_BOLD_ITALIC_CAPITAL_OMEGA, CAPITAL_ALPHA),
    (MATHEMATICAL_BOLD_ITALIC_SMALL_ALPHA, MATHEMATICAL_BOLD_ITALIC_SMALL_OMEGA, SMALL_ALPHA),
    (MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_ALPHA, MATHEMATICAL_SANSSERIF_BOLD_CAPITAL_OMEGA, CAPITAL_ALPHA),
    (MATHEMATICAL_SANSSERIF_BOLD_SMALL_ALPHA, MATHEMATICAL_SANSSERIF_BOLD_SMALL_OMEGA, SMALL_ALPHA),
    (MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_ALPHA, MATHEMATICAL_SANSSERIF_BOLD_ITALIC_CAPITAL_OMEGA,
     CAPITAL_ALPHA),
    (MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_ALPHA, MATHEMATICAL_SANSSERIF_BOLD_ITALIC_SMALL_OMEGA, SMALL_ALPHA),
)

# (upper bound, base) of the digit ranges (normaliseDigits); as in Java, only
# the first range also checks its lower bound
_MATHS_DIGITS = (
    (MATHEMATICAL_DOUBLESTRUCK_DIGIT_NINE, MATHEMATICAL_DOUBLESTRUCK_DIGIT_ZERO),
    (MATHEMATICAL_SANSSERIF_DIGIT_NINE, MATHEMATICAL_SANSSERIF_DIGIT_ZERO),
    (MATHEMATICAL_SANSSERIF_BOLD_DIGIT_NINE, MATHEMATICAL_SANSSERIF_BOLD_DIGIT_ZERO),
    (MATHEMATICAL_MONOSPACE_DIGIT_NINE, MATHEMATICAL_MONOSPACE_DIGIT_ZERO),
)


def _get_maths_char(u, normalise_greek=False, normalise_digits=False):
    """Utils.getMathsChar on a UTF-16 code unit (the low surrogate);
    returns a code unit (char arithmetic wraps around like Java's (char)
    cast)"""
    if u < MATHEMATICAL_BOLD_CAPITAL_A:
        return u
    for upper, base, target in _MATHS_LATIN:
        if u <= upper:
            return (u - base + target) & 0xFFFF
    if u == MATHEMATICAL_ITALIC_SMALL_DOTLESS_I:
        return ord('i')
    if u == MATHEMATICAL_ITALIC_SMALL_DOTLESS_J:
        return ord('j')
    if normalise_greek:
        for first, last, target in _MATHS_GREEK:
            if first <= u <= last:
                return (u - first + target) & 0xFFFF
    elif normalise_digits:
        if MATHEMATICAL_BOLD_DIGIT_ZERO <= u <= MATHEMATICAL_BOLD_DIGIT_NINE:
            return (u - MATHEMATICAL_BOLD_DIGIT_ZERO + DIGIT_ZERO) & 0xFFFF
        for upper, base in _MATHS_DIGITS:
            if u <= upper:
                return (u - base + DIGIT_ZERO) & 0xFFFF
    return u


def simplify_mathematical(s, normalise_greek=False, normalise_digits=False):
    """Replaces mathematical alphanumeric symbols by the plain letters (and,
    optionally, Greek letters and digits). As in Java, characters that are
    not mathematical symbols are dropped."""
    units = _utf16(s)
    out = []
    for i, u in enumerate(units):
        if u == _HIGH_SURROGATE_MATHS:
            j = i + 1
            if j < len(units) and MATHEMATICAL_BOLD_CAPITAL_A <= units[j] <= MATHEMATICAL_MONOSPACE_DIGIT_NINE:
                mapped = _get_maths_char(units[j], normalise_greek, normalise_digits)
                if mapped == units[j]:
                    out.append(u)
                    out.append(units[j])
                else:
                    out.append(mapped)
    return _from_utf16(out)


_GREEK_LOOKALIKES = {
    'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I', 'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O',
    'Ρ': 'P', 'Τ': 'T', 'Υ': 'Y', 'Χ': 'X', 'α': 'a', 'β': 'B', 'γ': 'y', 'δ': 'd', 'ε': 'e', 'η': 'n',
    'ι': 'i', 'κ': 'K', 'ν': 'v', 'ο': 'o', 'ρ': 'p', 'τ': 'T', 'χ': 'x', 'ω': 'w',
}


def greek_to_latin(s):
    return ''.join(_GREEK_LOOKALIKES.get(c, c) for c in s)


_HAS_LATIN = jregex.compile('.*[A-Za-z].*')
_HAS_GREEK = jregex.compile('.*\\p{InGREEK}.*')
_HAS_CYRILLIC = jregex.compile('.*\\p{InCYRILLIC}.*')


def has_mixed_greek_and_latin(s):
    return _HAS_LATIN.fullmatch(s) is not None and _HAS_GREEK.fullmatch(s) is not None


def has_mixed_greek_and_cyrillic(s):
    # as in Java, this checks for Latin and Cyrillic characters
    return _HAS_LATIN.fullmatch(s) is not None and _HAS_CYRILLIC.fullmatch(s) is not None
