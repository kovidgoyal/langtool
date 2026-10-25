"""A pure Python port of Hunspell's spell checking (Hunspell 1.7.1).

Port of the parts of the C++ library Hunspell (https://hunspell.github.io/,
version 1.7.1 as bundled with the dumonts Java binding that LanguageTool
uses, see org.languagetool.rules.spelling.hunspell.Hunspell and
DumontsHunspellDictionary) that decide whether a word is spelled correctly:
HunspellImpl::spell (casing, abbreviation dots, numbers, CHECKSHARPS,
KEEPCASE, FORBIDDENWORD, BREAK), HunspellImpl::checkword, HashMgr (the .dic
file and the hash table with homonyms and hidden capitalized forms),
AffixMgr (the .aff file, prefix/suffix checks with conditions, cross
products, continuation classes and two-level suffixes, compound_check with
COMPOUNDFLAG/BEGIN/MIDDLE/END, COMPOUNDRULE, CHECKCOMPOUNDPATTERN etc.),
PfxEntry/SfxEntry and RepList (ICONV/OCONV). Hunspell::suggest is also
ported (HunspellImpl::suggest, SuggestMgr: REP, MAP, KEY, TRY based
suggestions, two words, compound suggestions and the ngram suggestions).

The bundled library of the Java binding behaves like Hunspell 1.7.1 (e.g.
compounds of three or more words are accepted without the simple suggestion
test of 1.7.2), so that version is ported, not the newer system Hunspell.

Words are handled as encoded bytes (UTF-8 or the 8-bit encoding of the
dictionary), like in Hunspell, so that affix conditions, compound
boundaries etc. behave exactly the same. Case conversion uses Hunspell's own
Unicode table (utf_info.hxx, BMP only; characters outside the BMP make the
word end with U+FFFD in the UTF-16 conversions, like in Hunspell).

Not ported: morphological analysis/generation, Hungarian specific rules
(LANG hu), and the CPU time limits of Hunspell (compound_check and the
suggestion search stop after a fixed CPU time in C++; here they never time
out; suggest() has an optional time limit instead). PHONE tables are not
used for suggestions. For 8-bit encodings the
character tables are derived from Python's codecs and the Unicode table
(Hunspell has its own tables in csutil.cxx).

Use get_dictionary(dic_path, aff_path) to get a (cached, shared) Hunspell
instance; Hunspell.spell(word) is thread-safe.
"""

import os
import re
import threading
from time import perf_counter

from ._base import speedups as _speedups

__all__ = ['Hunspell', 'get_dictionary']

# --- constants (atypes.hxx, csutil.hxx, hunspell.hxx) ---

NOCAP, INITCAP, ALLCAP, HUHCAP, HUHINITCAP = 0, 1, 2, 3, 4

SPELL_COMPOUND = 1 << 0
SPELL_FORBIDDEN = 1 << 1
SPELL_ALLCAP = 1 << 2
SPELL_NOCAP = 1 << 3
SPELL_INITCAP = 1 << 4
SPELL_ORIGCAP = 1 << 5
SPELL_WARN = 1 << 6
SPELL_COMPOUND_2 = 1 << 7

IN_CPD_NOT, IN_CPD_BEGIN, IN_CPD_END, IN_CPD_OTHER = 0, 1, 2, 3

AE_XPRODUCT = 1 << 0
AE_UTF8 = 1 << 1

FLAG_CHAR, FLAG_LONG, FLAG_NUM, FLAG_UNI = 0, 1, 2, 3

DEFAULTFLAGS = 65510
FLAG_NULL = '\x00'
FORBIDDENWORD = chr(65510)
ONLYUPCASEFLAG = chr(65511)

MINCPDLEN = 3
MAXWORDLEN = 100
MAXWORDUTF8LEN = MAXWORDLEN * 3
MAXSHARPS = 5
MAXSUGGESTION = 15
MAXCOMPOUNDSUGS = 3
MAXNGRAMSUGS = 4
MAX_CHAR_DISTANCE = 4
SPELL_XML = b'<?xml?>'
SPELL_KEYSTRING = b'qwertyuiop|asdfghjkl|zxcvbnm'

LANG_az, LANG_crh, LANG_de, LANG_hu, LANG_tr = 100, 102, 49, 36, 90
_LANGS = {'ar': 96, 'az': LANG_az, 'az_AZ': LANG_az, 'bg': 41, 'ca': 37, 'crh': LANG_crh, 'cs': 42, 'da': 45,
          'de': LANG_de, 'el': 30, 'en': 1, 'es': 34, 'eu': 10, 'gl': 38, 'fr': 2, 'hr': 78, 'hu': LANG_hu,
          'hu_HU': LANG_hu, 'it': 39, 'la': 99, 'lv': 101, 'nl': 31, 'pl': 48, 'pt': 3, 'sv': 50, 'tr': LANG_tr,
          'tr_TR': LANG_tr, 'ru': 7, 'uk': 80}
LANG_xx = 999

# --- Hunspell's Unicode case table (utf_info.hxx): runs start:count:step:delta ---

_UPPER_RUNS = (
    '61:26:1:-32 b5::743 e0:23:1:-32 f8:7:1:-32 ff::121 101:24:2:-1 131::-232 133:3:2:-1 13a:8:2:-1 '
    '14b:23:2:-1 17a:3:2:-1 17f::-300 183:2:2:-1 188::-1 18c::-1 192::-1 195::97 199::-1 19a::163 '
    '19e::130 1a1:3:2:-1 1a8::-1 1ad::-1 1b0::-1 1b4:2:2:-1 1b9::-1 1bd::-1 1bf::56 1c5::-1 1c6::-2 '
    '1c8::-1 1c9::-2 1cb::-1 1cc::-2 1ce:8:2:-1 1dd::-79 1df:9:2:-1 1f2::-1 1f3::-2 1f5::-1 1f9:20:2:-1 '
    '223:9:2:-1 23c::-1 253::-210 254::-206 256:2:1:-205 259::-202 25b::-203 260::-205 263::-207 '
    '268::-209 269::-211 26f::-211 272::-213 275::-214 280::-218 283::-218 288::-218 28a:2:1:-217 '
    '292::-219 294::-83 345::84 3ac::-38 3ad:3:1:-37 3b1:17:1:-32 3c2::-31 3c3:9:1:-32 3cc::-64 '
    '3cd:2:1:-63 3d0::-62 3d1::-57 3d5::-47 3d6::-54 3d9:12:2:-1 3f0::-86 3f1::-80 3f2::7 3f5::-96 '
    '3f8::-1 3fb::-1 430:32:1:-32 450:16:1:-80 461:17:2:-1 48b:27:2:-1 4c2:7:2:-1 4d1:21:2:-1 501:8:2:-1 '
    '561:38:1:-48 1e01:75:2:-1 1e9b::-59 1ea1:45:2:-1 1f00:8:1:8 1f10:6:1:8 1f20:8:1:8 1f30:8:1:8 '
    '1f40:6:1:8 1f51:4:2:8 1f60:8:1:8 1f70:2:1:74 1f72:4:1:86 1f76:2:1:100 1f78:2:1:128 1f7a:2:1:112 '
    '1f7c:2:1:126 1f80:8:1:8 1f90:8:1:8 1fa0:8:1:8 1fb0:2:1:8 1fb3::9 1fbe::-7205 1fc3::9 1fd0:2:1:8 '
    '1fe0:2:1:8 1fe5::7 1ff3::9 2c30:47:1:-48 2c81:50:2:-1 2d00:38:1:-7264 ff41:26:1:-32 '
)
_LOWER_RUNS = (
    '41:26:1:32 c0:23:1:32 d8:7:1:32 100:24:2:1 130::-199 132:3:2:1 139:8:2:1 14a:23:2:1 178::-121 '
    '179:3:2:1 181::210 182:2:2:1 186::206 187::1 189:2:1:205 18b::1 18e::79 18f::202 190::203 191::1 '
    '193::205 194::207 196::211 197::209 198::1 19c::211 19d::213 19f::214 1a0:3:2:1 1a6::218 1a7::1 '
    '1a9::218 1ac::1 1ae::218 1af::1 1b1:2:1:217 1b3:2:2:1 1b7::219 1b8::1 1bc::1 1c4::2 1c5::1 1c7::2 '
    '1c8::1 1ca::2 1cb:9:2:1 1de:9:2:1 1f1::2 1f2:2:2:1 1f6::-97 1f7::-56 1f8:20:2:1 220::-130 222:9:2:1 '
    '23b::1 23d::-163 241::83 386::38 388:3:1:37 38c::64 38e:2:1:63 391:17:1:32 3a3:9:1:32 3d8:12:2:1 '
    '3f4::-60 3f7::1 3f9::-7 3fa::1 400:16:1:80 410:32:1:32 460:17:2:1 48a:27:2:1 4c1:7:2:1 4d0:21:2:1 '
    '500:8:2:1 531:38:1:48 10a0:38:1:7264 1e00:75:2:1 1ea0:45:2:1 1f08:8:1:-8 1f18:6:1:-8 1f28:8:1:-8 '
    '1f38:8:1:-8 1f48:6:1:-8 1f59:4:2:-8 1f68:8:1:-8 1f88:8:1:-8 1f98:8:1:-8 1fa8:8:1:-8 1fb8:2:1:-8 '
    '1fba:2:1:-74 1fbc::-9 1fc8:4:1:-86 1fcc::-9 1fd8:2:1:-8 1fda:2:1:-100 1fe8:2:1:-8 1fea:2:1:-112 '
    '1fec::-7 1ff8:2:1:-128 1ffa:2:1:-126 1ffc::-9 2126::-7517 212a::-8383 212b::-8262 2c00:47:1:48 '
    '2c80:50:2:1 ff21:26:1:32 '
)


def _case_table(runs):
    table = {}
    for run in runs.split():
        parts = run.split(':')
        start = int(parts[0], 16)
        delta = int(parts[-1])
        n = int(parts[1]) if len(parts) == 4 else 1
        st = int(parts[2]) if len(parts) == 4 else 1
        for k in range(n):
            c = start + k * st
            table[c] = c + delta
    return table


_UPPER = _case_table(_UPPER_RUNS)  # unicodetoupper (BMP code units)
_LOWER = _case_table(_LOWER_RUNS)  # unicodetolower


def _case_maps(langnum):
    upper = dict(_UPPER)
    lower = dict(_LOWER)
    if langnum in (LANG_az, LANG_tr, LANG_crh):
        upper[0x69] = 0x130
        lower[0x49] = 0x131
    return upper, lower


# --- UTF-8 <-> UTF-16 (csutil.cxx u8_u16/u16_u8) ---

_NON_BMP_OR_INVALID = re.compile(rb'[\x80-\xff]')
_FOUR_BYTE = re.compile(rb'[\xf0-\xff]')


def u8_u16(b):
    """csutil's u8_u16: the UTF-16 code units (as a str of BMP characters)
    of UTF-8 bytes. A 4-byte sequence (outside the BMP) ends the conversion
    with U+FFFD, invalid bytes become U+FFFD."""
    if b.isascii():
        return b.decode('ascii')
    if _FOUR_BYTE.search(b) is None:
        try:
            return b.decode('utf-8')
        except UnicodeDecodeError:
            pass
    # literal port of the conversion for the unusual cases
    out = []
    i = 0
    n = len(b)

    def at(k):
        return b[k] if k < n else 0
    while i < n:
        c = b[i]
        hi = c & 0xf0
        if hi < 0x80:
            out.append(c)
        elif hi < 0xc0:
            out.append(0xfffd)
        elif hi < 0xe0:
            if (at(i + 1) & 0xc0) == 0x80:
                out.append(((c & 0x1f) << 6) | (at(i + 1) & 0x3f))
                i += 1
            else:
                out.append(0xfffd)
        elif hi == 0xe0:
            if (at(i + 1) & 0xc0) == 0x80:
                h = (((c & 0x0f) << 4) + ((at(i + 1) & 0x3f) >> 2)) & 0xff
                i += 1
                if (at(i + 1) & 0xc0) == 0x80:
                    lo = ((b[i] << 6) + (at(i + 1) & 0x3f)) & 0xff
                    i += 1
                    out.append((h << 8) | lo)
                else:
                    out.append(0xfffd)
            else:
                out.append(0xfffd)
        else:
            out.append(0xfffd)
            break
        i += 1
    return ''.join(map(chr, out))


def u16_u8(s):
    """csutil's u16_u8 for a str of BMP code units"""
    return s.encode('utf-8', 'surrogatepass')


def _atoi(b):
    m = re.match(rb'\s*([+-]?\d+)', b)
    return int(m.group(1)) if m else 0


def _mychomp(s):
    k = len(s)
    newsize = k
    if k > 0 and s[k - 1] in (13, 10):
        newsize -= 1
    if k > 1 and s[k - 2] == 13:
        newsize -= 1
    return s[:newsize]


def _pieces(line):
    """mystrsep: fields separated by spaces and tabs"""
    return line.replace(b'\t', b' ').split()


def _read_lines(path):
    """The lines of a file as FileMgr::getline returns them (split at \\n,
    no trailing empty line)"""
    with open(path, 'rb') as f:
        data = f.read()
    lines = data.split(b'\n')
    if lines and lines[-1] == b'':
        lines.pop()
    return lines


def _is_subset(key, word, start):
    """AffixMgr::isSubset(key, word + start) ('.' matches any character)"""
    if b'.' not in key:
        return word.startswith(key, start)
    n = len(word)
    for k, c in enumerate(key):
        p = start + k
        if c != 46 and (p >= n or c != word[p]):
            return False
    return True


def _is_rev_subset(key, word, end, length):
    """AffixMgr::isRevSubset(key, word + end - 1, length)"""
    if len(key) > length:
        return False
    if b'.' not in key:
        p = end - 1
        for c in key:
            if word[p] != c:
                return False
            p -= 1
        return True
    p = end - 1
    for c in key:
        if c != word[p] and c != 46:
            return False
        p -= 1
    return True


class _Entry:
    """hentry: a dictionary word with its flags and the next homonym"""

    __slots__ = ('word', 'flags', 'next')

    def __init__(self, word, flags):
        self.word = word
        self.flags = flags
        self.next = None


class _AffEntry:
    """PfxEntry/SfxEntry"""

    __slots__ = ('appnd', 'strip', 'aflag', 'opts', 'conds', 'numconds', 'cont', 'key', 'next', 'nexteq', 'nextne',
                 'utf8', 'mgr')

    def __init__(self, mgr):
        self.mgr = mgr
        self.appnd = b''
        self.strip = b''
        self.aflag = FLAG_NULL
        self.opts = 0
        self.conds = b''
        self.numconds = 0
        self.cont = ''
        self.key = b''
        self.next = None
        self.nexteq = None
        self.nextne = None
        self.utf8 = False

    # PfxEntry::test_condition
    def pfx_test_condition(self, s):
        if self.numconds == 0:
            return True
        c = self.conds
        nc = len(c)
        utf8 = self.utf8
        slen = len(s)
        st = 0
        pos = -1
        neg = False
        ingroup = False
        p = 0
        while True:
            ch = c[p]
            if ch == 91:  # [
                neg = False
                ingroup = False
                p = p + 1 if p + 1 < nc else None
                pos = st
            elif ch == 94:  # ^
                p = p + 1 if p + 1 < nc else None
                neg = True
            elif ch == 93:  # ]
                if neg == ingroup:
                    return False
                pos = -1
                p = p + 1 if p + 1 < nc else None
                # skip the next character
                if not ingroup and st < slen:
                    st += 1
                    while utf8 and st < slen and (s[st] & 0xc0) == 0x80:
                        st += 1
                if st == slen and p is not None:
                    return False  # word <= condition
            elif ch == 46 and pos == -1:  # . (not in a group)
                p = p + 1 if p + 1 < nc else None
                # skip the next character
                st += 1
                while utf8 and st < slen and (s[st] & 0xc0) == 0x80:
                    st += 1
                if st == slen and p is not None:
                    return False  # word <= condition
            else:
                if st < slen and s[st] == ch:
                    st += 1
                    p = p + 1 if p + 1 < nc else None
                    if utf8 and (s[st - 1] & 0x80):  # multibyte
                        while p is not None and (c[p] & 0xc0) == 0x80:  # character
                            if c[p] != (s[st] if st < slen else 0):
                                if pos == -1:
                                    return False
                                st = pos
                                break
                            p = p + 1 if p + 1 < nc else None
                            st += 1
                        if pos != -1 and st != pos:
                            ingroup = True
                            while p is not None and c[p] != 93:
                                p = p + 1 if p + 1 < nc else None
                    elif pos != -1:
                        ingroup = True
                        while p is not None and c[p] != 93:
                            p = p + 1 if p + 1 < nc else None
                elif pos != -1:  # group
                    p = p + 1 if p + 1 < nc else None
                else:
                    return False
            if p is None:
                return True

    # SfxEntry::test_condition(end, beg) for s[0:end]
    def sfx_test_condition(self, s, end):
        if self.numconds == 0:
            return True
        c = self.conds
        nc = len(c)
        utf8 = self.utf8
        numconds = self.numconds
        slen = len(s)

        def at(k):
            return s[k] if 0 <= k < slen else 0
        pos = None
        neg = False
        ingroup = False
        p = 0
        st = end - 1
        i = 1
        while True:
            ch = c[p]
            if ch == 91:  # [
                p = p + 1 if p + 1 < nc else None
                pos = st
            elif ch == 94:  # ^
                p = p + 1 if p + 1 < nc else None
                neg = True
            elif ch == 93:  # ]
                if not neg and not ingroup:
                    return False
                i += 1
                # skip the next character
                if not ingroup:
                    while utf8 and st >= 0 and (at(st) & 0xc0) == 0x80:
                        st -= 1
                    st -= 1
                pos = None
                neg = False
                ingroup = False
                p = p + 1 if p + 1 < nc else None
                if st < 0 and p is not None:
                    return False  # word <= condition
            elif ch == 46 and pos is None:  # . (not in a group)
                p = p + 1 if p + 1 < nc else None
                # skip the next character
                st -= 1
                while utf8 and st >= 0 and (at(st) & 0xc0) == 0x80:
                    st -= 1
                if st < 0:  # word <= condition
                    return p is None
                if utf8 and (at(st) & 0x80):  # head of the UTF-8 character
                    st -= 1
                    if st < 0:  # word <= condition
                        return p is None
            else:
                if at(st) == ch:
                    p = p + 1 if p + 1 < nc else None
                    if utf8 and (at(st) & 0x80):
                        st -= 1
                        while p is not None and st >= 0:
                            if c[p] != at(st):
                                if pos is None:
                                    return False
                                st = pos
                                break
                            # first byte of the UTF-8 multibyte character
                            if (c[p] & 0xc0) != 0x80:
                                break
                            p = p + 1 if p + 1 < nc else None
                            st -= 1
                        if pos is not None and st != pos:
                            if neg:
                                return False
                            elif i == numconds:
                                return True
                            ingroup = True
                            while p is not None and c[p] != 93:
                                p = p + 1 if p + 1 < nc else None
                            st -= 1
                        if p is not None and c[p] != 93:
                            p = p + 1 if p + 1 < nc else None
                    elif pos is not None:
                        if neg:
                            return False
                        elif i == numconds:
                            return True
                        ingroup = True
                        while p is not None and c[p] != 93:
                            p = p + 1 if p + 1 < nc else None
                        st -= 1
                    if pos is None:
                        i += 1
                        st -= 1
                    if st < 0 and p is not None and c[p] != 93:
                        return False  # word <= condition
                elif pos is not None:  # group
                    p = p + 1 if p + 1 < nc else None
                else:
                    return False
            if p is None:
                return True


class Hunspell:
    """A Hunspell dictionary (.aff and .dic file): spell(word) is
    Hunspell::spell, suggest(word) Hunspell::suggest, add(word)
    Hunspell::add."""

    def __init__(self, dic_path, aff_path):
        self.dic_path = dic_path
        self.aff_path = aff_path
        self._lock = threading.RLock()
        # state of AffixMgr (pfx, sfx etc. are not stateless in Hunspell)
        self.pfx = None
        self.sfx = None
        self.sfxflag = FLAG_NULL
        self.sfxappnd = None
        self.sfxextra = 0
        self.words = {}
        self._spell_cache = {}  # word -> spell(word)
        self._all_entries = []  # all entries in the order they were added (hash table order: see _hash)
        self._phon = {}  # entry -> its ph: field
        self._tablesize = 1
        self._pflag = {}  # flag & 0xff -> prefix entries (AffixMgr::pFlag lists)
        self._sflag = {}
        self._load_config(aff_path)
        self._parse_aff(aff_path)
        self._load_tables(dic_path)
        self._sug_data = None
        self._deadline = None  # the time limit of the running suggest() call (perf_counter), None: no limit
        self._time_limit = None
        self._map_timer = None

    # ------------------------------------------------------------------
    # flags (HashMgr::decode_flag(s))

    def decode_flags(self, b):
        """HashMgr::decode_flags: the flags as a str of flag characters"""
        if not b:
            return ''
        mode = self.flag_mode
        if mode == FLAG_CHAR:
            return b.decode('latin-1')
        if mode == FLAG_LONG:
            n = len(b) >> 1
            r = []
            for k in range(n):
                r.append(chr((b[2 * k] << 8) | b[2 * k + 1]))
            return ''.join(r)
        if mode == FLAG_NUM:
            r = []
            for part in b.split(b','):
                r.append(chr(_atoi(part) & 0xffff))
            return ''.join(r)
        return u8_u16(b)  # FLAG_UNI

    def decode_flag(self, b):
        mode = self.flag_mode
        if mode == FLAG_LONG:
            s = ((b[0] if len(b) > 0 else 0) << 8) | (b[1] if len(b) > 1 else 0)
        elif mode == FLAG_NUM:
            s = _atoi(b) & 0xffff
        elif mode == FLAG_UNI:
            w = u8_u16(b)
            s = ord(w[0]) if w else 0
        else:
            s = b[0] if b else 0
        return chr(s)

    # ------------------------------------------------------------------
    # HashMgr::load_config

    def _load_config(self, aff_path):
        self.flag_mode = FLAG_CHAR
        self.complexprefixes = False
        self.utf8 = False
        self.forbiddenword = FORBIDDENWORD
        self.langnum = 0
        self.encoding = b''
        self.ignorechars = b''
        self.aliasf = []
        self.aliasm = []
        self.has_aliasm = False
        self.reptable = []  # [pattern, [out0, out1, out2, out3]]
        lines = _read_lines(aff_path)
        it = iter(enumerate(lines))
        enc_set = False
        lang_set = False
        ignore_set = False
        for idx, line in it:
            line = _mychomp(line)
            if idx == 0 and line.startswith(b'\xef\xbb\xbf'):
                line = line[3:]
            if line.startswith(b'FLAG') and len(line) > 4 and line[4:5].isspace():
                if b'long' in line:
                    self.flag_mode = FLAG_LONG
                if b'num' in line:
                    self.flag_mode = FLAG_NUM
                if b'UTF-8' in line:
                    self.flag_mode = FLAG_UNI
            if line.startswith(b'FORBIDDENWORD'):
                p = _pieces(line)
                if len(p) < 2:
                    return
                self.forbiddenword = self.decode_flag(p[1])
            if line.startswith(b'SET'):
                p = _pieces(line)
                if len(p) < 2 or enc_set:
                    return
                enc_set = True
                self.encoding = p[1]
                if p[1] == b'UTF-8':
                    self.utf8 = True
            if line.startswith(b'LANG'):
                p = _pieces(line)
                if len(p) < 2 or lang_set:
                    return
                lang_set = True
                self.langnum = _LANGS.get(p[1].decode('latin-1'), LANG_xx)
            if line.startswith(b'IGNORE'):
                p = _pieces(line)
                if len(p) < 2 or ignore_set:
                    return
                ignore_set = True
                self.ignorechars = p[1]
            if line.startswith(b'AF') and len(line) > 2 and line[2:3].isspace():
                if not self._parse_aliasf(line, it):
                    return
            if line.startswith(b'AM') and len(line) > 2 and line[2:3].isspace():
                if not self._parse_aliasm(line, it):
                    return
            if line.startswith(b'COMPLEXPREFIXES'):
                self.complexprefixes = True
            if line.startswith(b'REP'):
                if not self._parse_reptable(line, it):
                    return
            if ((line.startswith(b'SFX') or line.startswith(b'PFX')) and len(line) > 3 and line[3:4].isspace()
                    and self.reptable):
                break

    def _parse_aliasf(self, line, it):
        if self.aliasf:
            return False
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            self.aliasf = []
            return False
        aliases = []
        for _ in range(num):
            alias = None
            nxt = next(it, None)
            if nxt is not None:
                nl = _pieces(_mychomp(nxt[1]))
                if nl and nl[0].startswith(b'AF'):
                    alias = self.decode_flags(nl[1]) if len(nl) > 1 else None
            if alias is None:
                self.aliasf = []
                return False
            aliases.append(alias)
        self.aliasf = aliases
        return True

    def _parse_aliasm(self, line, it):
        if self.has_aliasm:
            return False
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            return False
        aliases = []
        for _ in range(num):
            nxt = next(it, None)
            raw = _mychomp(nxt[1]) if nxt is not None else b''
            nl = _pieces(raw)
            if not nl or not nl[0].startswith(b'AM') or len(nl) < 2:
                self.has_aliasm = False
                return False
            # the rest of the line from the second field
            rest = raw.replace(b'\t', b' ')
            k = rest.find(nl[0]) + len(nl[0])
            k = rest.find(nl[1], k)
            aliases.append(raw[k:])
        self.aliasm = aliases
        self.has_aliasm = True
        return True

    def _parse_reptable(self, line, it):
        if self.reptable:
            return False
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            return False
        table = []
        for _ in range(num):
            entry = [b'', [b'', b'', b'', b'']]
            table.append(entry)
            rtype = 0
            nxt = next(it, None)
            if nxt is not None:
                nl = _pieces(_mychomp(nxt[1]))
                if nl and nl[0].startswith(b'REP'):
                    if len(nl) > 1:
                        pat = nl[1]
                        if pat.startswith(b'^'):
                            rtype = 1
                            pat = pat[1:]
                        pat = pat.replace(b'_', b' ')
                        if pat.endswith(b'$'):
                            rtype += 2
                            pat = pat[:-1]
                        entry[0] = pat
                    if len(nl) > 2:
                        entry[1][rtype] = nl[2].replace(b'_', b' ')
            if not entry[0] or not entry[1][rtype]:
                self.reptable = []
                return False
            self.reptable = table
        self.reptable = table
        return True

    # ------------------------------------------------------------------
    # AffixMgr::parse_file

    def _parse_aff(self, aff_path):
        self.keystring = b''
        self.trystring = b''
        self.a_encoding = b''
        self.a_complexprefixes = False
        self.a_utf8 = False
        self.compoundflag = FLAG_NULL
        self.compoundbegin = FLAG_NULL
        self.compoundmiddle = FLAG_NULL
        self.compoundend = FLAG_NULL
        self.compoundroot = FLAG_NULL
        self.compoundpermitflag = FLAG_NULL
        self.compoundforbidflag = FLAG_NULL
        self.compoundmoresuffixes = False
        self.checkcompounddup = False
        self.checkcompoundrep = False
        self.checkcompoundcase = False
        self.checkcompoundtriple = False
        self.simplifiedtriple = False
        self.a_forbiddenword = FORBIDDENWORD
        self.nosuggest = FLAG_NULL
        self.nongramsuggest = FLAG_NULL
        self.needaffix = FLAG_NULL
        self.lemma_present = FLAG_NULL
        self.circumfix = FLAG_NULL
        self.onlyincompound = FLAG_NULL
        self.cpdwordmax = -1
        self.cpdmin = -1
        self.cpdmaxsyllable = 0
        self.cpdvowels = ''
        self.cpdsyllablenum = b''
        self.checknum = False
        self.havecontclass = False
        self.contclasses = set()
        self.maxngramsugs = -1
        self.maxdiff = -1
        self.onlymaxdiff = False
        self.maxcpdsugs = -1
        self.nosplitsugs = False
        self.sugswithdots = False
        self.keepcase = FLAG_NULL
        self.forceucase = FLAG_NULL
        self.warn = FLAG_NULL
        self.forbidwarn = False
        self.checksharps = False
        self.substandard = FLAG_NULL
        self.fullstrip = False
        self.wordchars_b = b''
        self.a_ignorechars = b''
        self.iconvtable = None
        self.oconvtable = None
        self.checkcpdtable = []  # [pattern, pattern2, pattern3, cond, cond2]
        self.simplifiedcpd = False
        self.defcpdtable = []  # lists of flag characters
        self.maptable = []  # lists of byte strings
        self.breaktable = []
        self.a_langnum = 0
        self.phone = None
        self.version = b''
        self.pstart = [None] * 256
        self.sstart = [None] * 256
        parsed_break = False
        parsed_map = False
        parsed_checkcpd = False
        parsed_defcpd = False
        lines = _read_lines(aff_path)
        self._aff_lines = lines
        it = iter(enumerate(lines))
        error = False
        string_opts = {}  # parse_string: multiple definitions are errors
        dupflags = {}

        def parse_string(line, name):
            if name in string_opts:
                return None
            p = _pieces(line)
            if len(p) < 2:
                return None
            string_opts[name] = True
            return p[1]

        def parse_flag(line, name, current):
            if current != FLAG_NULL and not (ord(current) >= DEFAULTFLAGS):
                return None
            p = _pieces(line)
            if len(p) < 2:
                return None
            return self.decode_flag(p[1])

        def parse_num(line, current):
            if current != -1:
                return None
            p = _pieces(line)
            if len(p) < 2:
                return None
            return _atoi(p[1])

        for idx, line in it:
            line = _mychomp(line)
            if idx == 0 and line.startswith(b'\xef\xbb\xbf'):
                line = line[3:]
            sw = line.startswith
            if sw(b'KEY'):
                v = parse_string(line, 'KEY')
                if v is None:
                    error = True
                    break
                self.keystring = v
            if sw(b'TRY'):
                v = parse_string(line, 'TRY')
                if v is None:
                    error = True
                    break
                self.trystring = v
            if sw(b'SET'):
                v = parse_string(line, 'SET')
                if v is None:
                    error = True
                    break
                self.a_encoding = v
                if v == b'UTF-8':
                    self.a_utf8 = True
            if sw(b'COMPLEXPREFIXES'):
                self.a_complexprefixes = True
            for name, attr in ((b'COMPOUNDFLAG', 'compoundflag'),
                               (b'COMPOUNDBEGIN', 'compoundend' if self.a_complexprefixes else 'compoundbegin'),
                               (b'COMPOUNDMIDDLE', 'compoundmiddle'),
                               (b'COMPOUNDEND', 'compoundbegin' if self.a_complexprefixes else 'compoundend'),
                               (b'COMPOUNDROOT', 'compoundroot'),
                               (b'COMPOUNDPERMITFLAG', 'compoundpermitflag'),
                               (b'COMPOUNDFORBIDFLAG', 'compoundforbidflag'),
                               (b'NOSUGGEST', 'nosuggest'),
                               (b'NONGRAMSUGGEST', 'nongramsuggest'),
                               (b'FORBIDDENWORD', 'a_forbiddenword'),
                               (b'LEMMA_PRESENT', 'lemma_present'),
                               (b'CIRCUMFIX', 'circumfix'),
                               (b'ONLYINCOMPOUND', 'onlyincompound'),
                               (b'PSEUDOROOT', 'needaffix'),
                               (b'NEEDAFFIX', 'needaffix'),
                               (b'KEEPCASE', 'keepcase'),
                               (b'FORCEUCASE', 'forceucase'),
                               (b'WARN', 'warn'),
                               (b'SUBSTANDARD', 'substandard')):
                if sw(name):
                    v = parse_flag(line, attr, getattr(self, attr))
                    if v is None:
                        error = True
                        break
                    setattr(self, attr, v)
            if error:
                break
            if sw(b'COMPOUNDWORDMAX'):
                v = parse_num(line, self.cpdwordmax)
                if v is None:
                    error = True
                    break
                self.cpdwordmax = v
            if sw(b'COMPOUNDMORESUFFIXES'):
                self.compoundmoresuffixes = True
            if sw(b'CHECKCOMPOUNDDUP'):
                self.checkcompounddup = True
            if sw(b'CHECKCOMPOUNDREP'):
                self.checkcompoundrep = True
            if sw(b'CHECKCOMPOUNDTRIPLE'):
                self.checkcompoundtriple = True
            if sw(b'SIMPLIFIEDTRIPLE'):
                self.simplifiedtriple = True
            if sw(b'CHECKCOMPOUNDCASE'):
                self.checkcompoundcase = True
            if sw(b'COMPOUNDMIN'):
                v = parse_num(line, self.cpdmin)
                if v is None:
                    error = True
                    break
                self.cpdmin = max(v, 1)
            if sw(b'COMPOUNDSYLLABLE'):
                p = _pieces(line)
                if len(p) < 2:
                    error = True
                    break
                self.cpdmaxsyllable = _atoi(p[1])
                if len(p) > 2:
                    v = p[2]
                    self.cpdvowels = ''.join(sorted(u8_u16(v) if self.a_utf8 else v.decode('latin-1')))
                else:
                    self.cpdvowels = 'AEIOUaeiou'
            if sw(b'SYLLABLENUM'):
                v = parse_string(line, 'SYLLABLENUM')
                if v is None:
                    error = True
                    break
                self.cpdsyllablenum = v
            if sw(b'CHECKNUM'):
                self.checknum = True
            if sw(b'WORDCHARS'):
                v = parse_string(line, 'WORDCHARS')
                if v is None:
                    error = True
                    break
                self.wordchars_b = v
            if sw(b'IGNORE'):
                v = parse_string(line, 'IGNORE')
                if v is None:
                    error = True
                    break
                self.a_ignorechars = v
            if sw(b'ICONV'):
                tbl = self._parse_convtable(line, it, b'ICONV', self.iconvtable)
                if tbl is None:
                    error = True
                    break
                self.iconvtable = tbl
            if sw(b'OCONV'):
                tbl = self._parse_convtable(line, it, b'OCONV', self.oconvtable)
                if tbl is None:
                    error = True
                    break
                self.oconvtable = tbl
            if sw(b'PHONE'):
                if not self._parse_phonetable(line, it):
                    error = True
                    break
            if sw(b'CHECKCOMPOUNDPATTERN'):
                if parsed_checkcpd or not self._parse_checkcpdtable(line, it):
                    error = True
                    break
                parsed_checkcpd = True
            if sw(b'COMPOUNDRULE'):
                if parsed_defcpd or not self._parse_defcpdtable(line, it):
                    error = True
                    break
                parsed_defcpd = True
            if sw(b'MAP'):
                if parsed_map or not self._parse_maptable(line, it):
                    error = True
                    break
                parsed_map = True
            if sw(b'BREAK'):
                if parsed_break:
                    error = True
                    break
                parsed_break = True
                if not self._parse_breaktable(line, it):
                    error = True
                    break
            if sw(b'LANG'):
                v = parse_string(line, 'LANG')
                if v is None:
                    error = True
                    break
                self.a_langnum = _LANGS.get(v.decode('latin-1'), LANG_xx)
            if sw(b'VERSION'):
                self.version = line[7:].lstrip(b' \t')
            if sw(b'MAXNGRAMSUGS'):
                v = parse_num(line, self.maxngramsugs)
                if v is None:
                    error = True
                    break
                self.maxngramsugs = v
            if sw(b'ONLYMAXDIFF'):
                self.onlymaxdiff = True
            if sw(b'MAXDIFF'):
                v = parse_num(line, self.maxdiff)
                if v is None:
                    error = True
                    break
                self.maxdiff = v
            if sw(b'MAXCPDSUGS'):
                v = parse_num(line, self.maxcpdsugs)
                if v is None:
                    error = True
                    break
                self.maxcpdsugs = v
            if sw(b'NOSPLITSUGS'):
                self.nosplitsugs = True
            if sw(b'FULLSTRIP'):
                self.fullstrip = True
            if sw(b'SUGSWITHDOTS'):
                self.sugswithdots = True
            if sw(b'FORBIDWARN'):
                self.forbidwarn = True
            if sw(b'CHECKSHARPS'):
                self.checksharps = True
            ft = None
            if sw(b'PFX'):
                ft = 'S' if self.a_complexprefixes else 'P'
            if sw(b'SFX'):
                ft = 'P' if self.a_complexprefixes else 'S'
            if ft is not None:
                if not self._parse_affix(line, ft, it, dupflags):
                    error = True
                    break
        # finishFileMgr: convert the affix trees to sorted lists
        for start in (self.pstart, self.sstart):
            for k in range(1, 256):
                start[k] = self._process_in_order(start[k], None)
        if not error:
            self._process_order(self.pstart)
            self._process_order(self.sstart)
            # default BREAK definition
            if not parsed_break:
                self.breaktable = [b'-', b'^-', b'-$']
        if self.cpdmin == -1:
            self.cpdmin = MINCPDLEN
        self._post_init()

    def _parse_convtable(self, line, it, keyword, current):
        if current is not None:
            return None
        p = _pieces(line)
        if len(p) < 2:
            return None
        num = _atoi(p[1])
        if num < 1:
            return None
        rl = _RepList()
        for _ in range(num):
            nxt = next(it, None)
            if nxt is None:
                return None
            nl = _pieces(_mychomp(nxt[1]))
            if not nl or not nl[0].startswith(keyword):
                return None
            if len(nl) < 3:
                return None
            rl.add(nl[1], nl[2])
        return rl

    def _parse_phonetable(self, line, it):
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            return False
        for _ in range(num):
            nxt = next(it, None)
            if nxt is None:
                return False
        self.phone = True
        return True

    def _parse_checkcpdtable(self, line, it):
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            return False
        for _ in range(num):
            nxt = next(it, None)
            if nxt is None:
                return False
            nl = _pieces(_mychomp(nxt[1]))
            entry = [b'', b'', b'', FLAG_NULL, FLAG_NULL]
            self.checkcpdtable.append(entry)
            if nl and not nl[0].startswith(b'CHECKCOMPOUNDPATTERN'):
                return False
            if len(nl) > 1:
                pat = nl[1]
                k = pat.find(b'/')
                if k != -1:
                    entry[3] = self.decode_flag(pat[k + 1:])
                    pat = pat[:k]
                entry[0] = pat
            if len(nl) > 2:
                pat = nl[2]
                k = pat.find(b'/')
                if k != -1:
                    entry[4] = self.decode_flag(pat[k + 1:])
                    pat = pat[:k]
                entry[1] = pat
            if len(nl) > 3:
                entry[2] = nl[3]
                self.simplifiedcpd = True
        return True

    def _parse_defcpdtable(self, line, it):
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            return False
        for _ in range(num):
            nxt = next(it, None)
            if nxt is None:
                return False
            nl = _pieces(_mychomp(nxt[1]))
            rule = []
            self.defcpdtable.append(rule)
            if nl and not nl[0].startswith(b'COMPOUNDRULE'):
                return False
            if len(nl) > 1:
                piece = nl[1]
                if b'(' in piece:
                    k = 0
                    while k < len(piece):
                        chb, che = k, k + 1
                        if piece[k] == 40:  # (
                            par = piece.find(b')', k)
                            if par != -1:
                                chb, che = k + 1, par
                                k = par
                        if piece[chb:chb + 1] in (b'*', b'?'):
                            rule.append(chr(piece[chb]))
                        else:
                            rule.extend(self.decode_flags(piece[chb:che]))
                        k += 1
                else:
                    rule.extend(self.decode_flags(piece))
            if not rule:
                return False
        return True

    def _parse_maptable(self, line, it):
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 1:
            return False
        for _ in range(num):
            nxt = next(it, None)
            if nxt is None:
                return False
            nl = _pieces(_mychomp(nxt[1]))
            entry = []
            self.maptable.append(entry)
            if nl and not nl[0].startswith(b'MAP'):
                return False
            if len(nl) > 1:
                piece = nl[1]
                k = 0
                n = len(piece)
                while k < n:
                    chb, che = k, k + 1
                    if piece[k] == 40:  # (
                        par = piece.find(b')', k)
                        if par != -1:
                            chb, che = k + 1, par
                            k = par
                    elif self.a_utf8 and (piece[k] & 0xc0) == 0xc0:
                        k += 1
                        while k < n and (piece[k] & 0xc0) == 0x80:
                            k += 1
                        che = k
                        k -= 1
                    entry.append(piece[chb:che])
                    k += 1
            if not entry:
                return False
        return True

    def _parse_breaktable(self, line, it):
        p = _pieces(line)
        if len(p) < 2:
            return False
        num = _atoi(p[1])
        if num < 0:
            return False
        if num == 0:
            return True
        for _ in range(num):
            nxt = next(it, None)
            if nxt is None:
                return False
            nl = _pieces(_mychomp(nxt[1]))
            if nl and not nl[0].startswith(b'BREAK'):
                return False
            if len(nl) > 1:
                self.breaktable.append(nl[1])
        return len(self.breaktable) == num

    @staticmethod
    def _reverse_condition(piece):
        piece = bytearray(piece)
        n = len(piece)
        neg = False

        def put(k, c):
            if k < n:
                piece[k] = c
        for k in range(n - 1, -1, -1):
            c = piece[k]
            if c == 91:  # [
                if neg:
                    put(k + 1, 91)
                else:
                    piece[k] = 93
            elif c == 93:  # ]
                piece[k] = 91
                if neg:
                    put(k + 1, 94)
                neg = False
            elif c == 94:  # ^
                if k + 1 < n and piece[k + 1] == 93:
                    neg = True
                elif neg:
                    put(k + 1, c)
            else:
                if neg:
                    put(k + 1, c)
        return bytes(piece)

    def _condlen(self, s):
        n = 0
        group = False
        for c in s:
            if c == 91:
                group = True
                n += 1
            elif c == 93:
                group = False
            elif not group and (not self.a_utf8 or not (c & 0x80) or (c & 0xc0) == 0x80):
                n += 1
        return n

    def _redundant_condition(self, ft, strip, cond):
        stripl = len(strip)
        condl = len(cond)
        if ft == 'P':
            if strip[:condl] == cond:
                return True
            if not self.a_utf8:
                i = j = 0
                while i < stripl and j < condl:
                    if cond[j] != 91:
                        if cond[j] != strip[i]:
                            return False
                    else:
                        neg = j + 1 < condl and cond[j + 1] == 94
                        inn = False
                        while True:
                            j += 1
                            if j < condl and strip[i] == cond[j]:
                                inn = True
                            if not (j < condl - 1 and cond[j] != 93):
                                break
                        if j == condl - 1 and cond[j] != 93:
                            return False
                        if (not neg and not inn) or (neg and inn):
                            return False
                    i += 1
                    j += 1
                if j >= condl:
                    return True
        else:
            if stripl >= condl and strip[stripl - condl:] == cond:
                return True
            if not self.a_utf8:
                i = stripl - 1
                j = condl - 1
                while i >= 0 and j >= 0:
                    if cond[j] != 93:
                        if cond[j] != strip[i]:
                            return False
                    elif j > 0:
                        inn = False
                        while True:
                            j -= 1
                            if strip[i] == cond[j]:
                                inn = True
                            if not (j > 0 and cond[j] != 91):
                                break
                        if j == 0 and cond[j] != 91:
                            return False
                        neg = cond[j + 1] == 94
                        if (not neg and not inn) or (neg and inn):
                            return False
                    i -= 1
                    j -= 1
                if j < 0:
                    return True
        return False

    def _parse_affix(self, line, at, it, dupflags):
        p = _pieces(line)
        if len(p) < 4:
            return False
        aflag = self.decode_flag(p[1])
        ff = AE_XPRODUCT if p[2][:1] == b'Y' else 0
        numents = _atoi(p[3])
        if numents <= 0:
            return False
        opts = ff | (AE_UTF8 if self.a_utf8 else 0)
        entries = []
        for ent in range(numents):
            nxt = next(it, None)
            if nxt is None:
                return False
            nl = _pieces(_mychomp(nxt[1]))
            entry = _AffEntry(self)
            entry.opts = opts
            entry.aflag = aflag
            entry.utf8 = bool(opts & AE_UTF8)
            entries.append(entry)
            if len(nl) > 1 and self.decode_flag(nl[1]) != aflag:
                return False
            if len(nl) > 2:
                strip = nl[2]
                if self.a_complexprefixes:
                    strip = _reverse_utf(strip) if self.a_utf8 else strip[::-1]
                if strip == b'0':
                    strip = b''
                entry.strip = strip
            if len(nl) > 3:
                piece = nl[3]
                dash = piece.find(b'/')
                if dash != -1:
                    appnd = piece[:dash]
                    dash_str = piece[dash + 1:]
                    appnd = self._remove_ignored(appnd, self.a_ignorechars)
                    if self.a_complexprefixes:
                        appnd = _reverse_utf(appnd) if self.a_utf8 else appnd[::-1]
                    if self.aliasf:
                        index = _atoi(dash_str)
                        cont = self.aliasf[index - 1] if 0 < index <= len(self.aliasf) else ''
                    else:
                        cont = self.decode_flags(dash_str)
                    entry.cont = cont
                    self.havecontclass = True
                    self.contclasses.update(cont)
                else:
                    appnd = self._remove_ignored(piece, self.a_ignorechars)
                    if self.a_complexprefixes:
                        appnd = _reverse_utf(appnd) if self.a_utf8 else appnd[::-1]
                if appnd == b'0':
                    appnd = b''
                entry.appnd = appnd
            if len(nl) > 4:
                chunk = nl[4]
                if self.a_complexprefixes:
                    chunk = _reverse_utf(chunk) if self.a_utf8 else chunk[::-1]
                    chunk = self._reverse_condition(chunk)
                if entry.strip and chunk != b'.' and self._redundant_condition(at, entry.strip, chunk):
                    chunk = b'.'
                if at == 'S':
                    chunk = self._reverse_condition(chunk[::-1])
                if chunk != b'.':
                    entry.numconds = self._condlen(chunk)
                    entry.conds = chunk
                else:
                    entry.numconds = 0
                    entry.conds = b''
            if len(nl) < 4:
                return False
        for entry in entries:
            if at == 'P':
                entry.key = entry.appnd
                self._build_tree(self.pstart, entry)
                self._pflag.setdefault(ord(entry.aflag) & 0xff, []).insert(0, entry)
            else:
                entry.key = entry.appnd[::-1]
                self._build_tree(self.sstart, entry)
                self._sflag.setdefault(ord(entry.aflag) & 0xff, []).insert(0, entry)
        return True

    @staticmethod
    def _build_tree(start, ep):
        """AffixMgr::build_pfxtree/build_sfxtree (the index by affix string)"""
        key = ep.key
        if not key:
            ep.next = start[0]
            start[0] = ep
            return
        ep.nexteq = None
        ep.nextne = None
        sp = key[0]
        ptr = start[sp]
        if ptr is None:
            start[sp] = ep
            return
        while True:
            pptr = ptr
            if key <= ptr.key:
                ptr = ptr.nexteq
                if ptr is None:
                    pptr.nexteq = ep
                    break
            else:
                ptr = ptr.nextne
                if ptr is None:
                    pptr.nextne = ep
                    break

    def _process_in_order(self, ptr, nptr):
        # iterative version of process_pfx_in_order (reverse in-order: NE subtree, node, EQ subtree)
        stack = []
        node = ptr
        result = nptr
        # traversal order: process(node.nextne), node.next = result, result = node, process(node.nexteq)
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.nextne
            node = stack.pop()
            node.next = result
            result = node
            node = node.nexteq
        return result

    @staticmethod
    def _process_order(start):
        for k in range(1, 256):
            ptr = start[k]
            while ptr is not None:
                nptr = ptr.next
                while nptr is not None:
                    if not _is_subset_keys(ptr.key, nptr.key):
                        break
                    nptr = nptr.next
                ptr.nextne = nptr
                ptr.nexteq = None
                if ptr.next is not None and _is_subset_keys(ptr.key, ptr.next.key):
                    ptr.nexteq = ptr.next
                ptr = ptr.next
            ptr = start[k]
            while ptr is not None:
                nptr = ptr.next
                mptr = None
                while nptr is not None:
                    if not _is_subset_keys(ptr.key, nptr.key):
                        break
                    mptr = nptr
                    nptr = nptr.next
                if mptr is not None:
                    mptr.nextne = None
                ptr = ptr.next

    def _post_init(self):
        """HunspellImpl/AffixMgr/SuggestMgr initialization after parsing"""
        if self.a_utf8:
            self._units = u8_u16
            self._from_units = u16_u8
            self._upper_map, self._lower_map = _case_maps(self.a_langnum)
        else:
            enc = _python_encoding(self.a_encoding or b'ISO8859-1')
            self._units = lambda b: b.decode('latin-1')
            self._from_units = lambda s: s.encode('latin-1')
            self._upper_map, self._lower_map = _8bit_case_maps(enc, self.a_langnum)
            self._codec = enc
        self._upper_tr = {k: v for k, v in self._upper_map.items()}
        self._lower_tr = {k: v for k, v in self._lower_map.items()}
        self.is_compound = (self.compoundflag != FLAG_NULL or self.compoundbegin != FLAG_NULL
                            or bool(self.defcpdtable))
        if self.a_utf8:
            self.wordchars = self.wordchars_b.decode('utf-8', 'replace')
        else:
            self.wordchars = self.wordchars_b.decode(self._codec, 'replace')
        # SuggestMgr
        key = self.keystring or SPELL_KEYSTRING
        self.ckey = self._units(key)
        self.ctry = self._units(self.trystring) if self.trystring else ''
        if self.a_utf8:
            self.ckey = _truncate_bad(self.ckey, key)
            self.ctry = _truncate_bad(self.ctry, self.trystring)
        self.lang_with_dash_usage = b'-' in self.trystring or b'a' in self.trystring
        self.maxsug = MAXSUGGESTION
        self.s_maxngramsugs = self.maxngramsugs if self.maxngramsugs >= 0 else MAXNGRAMSUGS
        self.s_maxcpdsugs = self.maxcpdsugs if self.maxcpdsugs >= 0 else MAXCOMPOUNDSUGS
        self.wordbreak = list(self.breaktable)
        self._ignore_units = sorted(set(self._units(self.a_ignorechars))) if self.a_ignorechars else None
        # caches of the affix searches
        self._max_sfx_key = 1
        self._max_pfx_key = 1
        for start, attr in ((self.sstart, '_max_sfx_key'), (self.pstart, '_max_pfx_key')):
            for k in range(1, 256):
                e = start[k]
                while e is not None:
                    setattr(self, attr, max(getattr(self, attr), len(e.key)))
                    e = e.next
        self._sfx_cache = {}
        self._pfx_cache = {}
        self._sfx_groups, self._sfx_lengths = self._affix_groups(self.sstart, lambda e: e.appnd)
        self._pfx_groups, self._pfx_lengths = self._affix_groups(self.pstart, lambda e: e.appnd)

    @staticmethod
    def _affix_groups(start, affix):
        """the affix entries of the sorted lists grouped by affix (None if a
        key contains '.' or the lists are not in search order)"""
        groups = {}
        for k in range(1, 256):
            e = start[k]
            prev = None
            while e is not None:
                if b'.' in e.key or (prev is not None and prev.key > e.key):
                    return None, None
                groups.setdefault(affix(e), []).append(e)
                prev = e
                e = e.next
        return {a: tuple(g) for a, g in groups.items()}, sorted(set(len(a) for a in groups))

    # ------------------------------------------------------------------
    # case helpers (csutil)

    def to_lower_units(self, u):
        return u.translate(self._lower_tr)

    def to_upper_units(self, u):
        return u.translate(self._upper_tr)

    def captype_units(self, u):
        """get_captype_utf8 (and get_captype for 8-bit encodings)"""
        low = u.translate(self._lower_tr)
        if low == u:
            return NOCAP
        ncap = 0
        nneutral = 0
        up = u.translate(self._upper_tr)
        for a, lo, upc in zip(u, low, up):
            if a != lo:
                ncap += 1
            if upc == lo:
                nneutral += 1
        firstcap = u[0] != low[0]
        if ncap == 1 and firstcap:
            return INITCAP
        if ncap == len(u) or ncap + nneutral == len(u):
            return ALLCAP
        if ncap > 1 and firstcap:
            return HUHINITCAP
        return HUHCAP

    def _remove_ignored(self, b, ignore):
        if not ignore:
            return b
        if self.a_utf8:
            ig = set(u8_u16(ignore))
            u = u8_u16(b)
            if not any(c in ig for c in u):
                return b
            return u16_u8(''.join(c for c in u if c not in ig))
        return bytes(c for c in b if c not in ignore)

    # ------------------------------------------------------------------
    # HashMgr::load_tables

    def _load_tables(self, dic_path):
        lines = _read_lines(dic_path)
        if not lines:
            return
        first = _mychomp(lines[0])
        if first.startswith(b'\xef\xbb\xbf'):
            first = first[3:]
        tablesize = _atoi(first)
        if tablesize <= 0:
            return  # error: the table stays empty
        tablesize += 5 + 1000
        if tablesize % 2 == 0:
            tablesize += 1
        self._tablesize = tablesize
        decode_flags = self.decode_flags
        aliasf = self.aliasf
        utf8 = self.utf8
        flag_cache = {}
        ignore = self.ignorechars
        units = u8_u16 if utf8 else (lambda b: b.decode('latin-1'))
        lower_tr = self._lower_tr
        add_word = self._add_word
        add_hidden = self._add_hidden_capitalized_word
        cpx = self.complexprefixes
        for line in lines[1:]:
            ts = line
            if ts and ts[-1] == 13:
                ts = _mychomp(ts)
            desc = None
            if b':' in ts:
                dp_pos = -1
                k = ts.find(b':')
                while k != -1:
                    if k > 3 and ts[k - 3] in (32, 9):
                        q = k - 3
                        while q > 0 and ts[q - 1] in (32, 9):
                            q -= 1
                        dp_pos = -1 if q == 0 else q + 1
                        break
                    k = ts.find(b':', k + 1)
                tab = ts.find(b'\t')
                if tab != -1 and (dp_pos == -1 or tab < dp_pos):
                    dp_pos = tab + 1
                if dp_pos != -1:
                    desc = ts[dp_pos:]
                    ts = ts[:dp_pos - 1]
            else:
                tab = ts.find(b'\t')
                if tab != -1:
                    desc = ts[tab + 1:]
                    ts = ts[:tab]
            ap = ts.find(b'/')
            while ap != -1:
                if ap == 0:
                    ap += 1
                    continue_check = ts[ap - 1] != 92
                    if continue_check:
                        break
                elif ts[ap - 1] != 92:
                    break
                ts = ts[:ap - 1] + ts[ap:]
                ap = ts.find(b'/', ap)
            if ap != -1 and ap != len(ts):
                fb = ts[ap + 1:]
                ts = ts[:ap]
                if aliasf:
                    index = _atoi(fb)
                    flags = aliasf[index - 1] if 0 < index <= len(aliasf) else ''
                else:
                    flags = flag_cache.get(fb)
                    if flags is None:
                        flags = flag_cache[fb] = decode_flags(fb)
            else:
                flags = ''
            # get_clen_and_captype
            if ts.isascii():
                u = ts.decode('ascii')
            else:
                u = units(ts)
            low = u.translate(lower_tr)
            if low == u:
                captype = NOCAP
            elif u[1:] == low[1:]:
                captype = INITCAP
            else:
                captype = self.captype_units(u)
            if ignore or cpx:
                ts = self._prepare_word(ts)
            if desc:
                self._add_word_desc(ts, flags, False, desc, captype)
                if captype >= ALLCAP:
                    self._add_hidden_capitalized_word(u, flags, captype, desc)
                continue
            add_word(ts, flags, False)
            if captype >= ALLCAP:
                add_hidden(u, flags, captype)

    def _prepare_word(self, ts):
        if self.ignorechars:
            ts = self._remove_ignored(ts, self.ignorechars)
        if self.complexprefixes:
            ts = _reverse_utf(ts) if self.utf8 else ts[::-1]
        return ts

    def _add_word(self, word, flags, onlyupcase):
        """HashMgr::add_word (homonyms, hidden onlyupcase homonyms)"""
        words = self.words
        dp = words.get(word)
        if dp is None:
            e = words[word] = _Entry(word, flags)
            self._all_entries.append(e)
            return e
        while dp.next is not None:
            dp = dp.next
        if not onlyupcase:
            if dp.flags and ONLYUPCASEFLAG in dp.flags:
                dp.flags = flags  # remove hidden onlyupcase homonym
            else:
                e = dp.next = _Entry(dp.word, flags)
                self._all_entries.append(e)
                return e
        return None

    def _add_word_desc(self, word, flags, onlyupcase, desc, captype):
        """HashMgr::add_word for a word with a morphological description:
        ph: fields are used by the suggestions (also as REP replacements)"""
        if self.ignorechars or self.complexprefixes:
            word = self._prepare_word(word)
        e = self._add_word(word, flags, onlyupcase)
        if self.has_aliasm:
            index = _atoi(desc)
            desc = self.aliasm[index - 1] if 0 < index <= len(self.aliasm) else None
        if desc is None or b'ph:' not in desc:
            return
        if e is not None:
            k = desc.find(b'ph:')
            v = desc[k + 3:]
            m = re.match(rb'[^ \t\n]*', v)
            self._phon[e] = m.group(0)
        in_word = word
        for field in _pieces(desc):
            if not field.startswith(b'ph:'):
                continue
            ph = field[3:]
            if not ph:
                continue
            strippatt = ph.find(b'->')
            if strippatt != -1 and 0 < strippatt < len(ph) - 2:
                wordpart = ph[strippatt + 2:]
                ph = ph[:strippatt]
            else:
                wordpart = in_word
            if ph.endswith(b'*'):
                strippatt = 1
                stripword = 0
                if self.utf8:
                    while strippatt < len(ph) and (ph[len(ph) - strippatt - 1] & 0xc0) == 0x80:
                        strippatt += 1
                    while stripword < len(wordpart) and (wordpart[len(wordpart) - stripword - 1] & 0xc0) == 0x80:
                        stripword += 1
                strippatt += 1
                stripword += 1
                if len(ph) > strippatt and len(wordpart) > stripword:
                    ph = ph[:len(ph) - strippatt]
                    k = len(in_word) - stripword
                    wordpart = wordpart[:k] + wordpart[k + stripword:]
            if captype == INITCAP:
                ph_capitalized = b''
                u = self._units(ph)
                if self.captype_units(u) == NOCAP:
                    ph_capitalized = self._from_units(u[:1].translate(self._upper_tr) + u[1:])
                if ph_capitalized:
                    if self.langnum in (LANG_de, LANG_hu):
                        wordpart_lower = self._from_units(self._units(wordpart).translate(self._lower_tr))
                        self.reptable.append([ph, [wordpart_lower, b'', b'', b'']])
                    self.reptable.append([ph_capitalized, [wordpart, b'', b'', b'']])
            self.reptable.append([ph, [wordpart, b'', b'', b'']])

    def _add_hidden_capitalized_word(self, u, flags, captype, desc=None):
        """HashMgr::add_hidden_capitalized_word (u: the UTF-16 units)"""
        if ((captype == HUHCAP or captype == HUHINITCAP or (captype == ALLCAP and flags))
                and not (flags and self.forbiddenword in flags)):
            flags2 = flags + ONLYUPCASEFLAG
            st = u.translate(self._lower_tr)
            if st:
                st = st[0].translate(self._upper_tr) + st[1:]
            w = self._from_units(st)
            if desc:
                self._add_word_desc(w, flags2, True, desc, INITCAP)
                return True
            if self.ignorechars or self.complexprefixes:
                w = self._prepare_word(w)
            self._add_word(w, flags2, True)
        return True

    # ------------------------------------------------------------------
    # AffixMgr checks

    def lookup(self, word):
        return self.words.get(word)

    def prefix_check(self, word, start, length, in_compound, needflag=FLAG_NULL):
        self.pfx = None
        self.pfxappnd = None
        self.sfxappnd = None
        self.sfxextra = 0
        oic = self.onlyincompound
        cpf = self.compoundpermitflag
        pe = self.pstart[0]
        while pe is not None:
            cont = pe.cont
            if ((in_compound != IN_CPD_NOT or not (cont and oic in cont))
                    and (in_compound != IN_CPD_END or (cont and cpf in cont))):
                rv = self._pfx_checkword(pe, word, start, length, in_compound, needflag)
                if rv is not None:
                    self.pfx = pe
                    return rv
            pe = pe.next
        for pptr in self._pfx_matches(word, start):
            cont = pptr.cont
            if ((in_compound != IN_CPD_NOT or not (cont and oic in cont))
                    and (in_compound != IN_CPD_END or (cont and cpf in cont))):
                rv = self._pfx_checkword(pptr, word, start, length, in_compound, needflag)
                if rv is not None:
                    self.pfx = pptr
                    return rv
        return None

    def _pfx_checkword(self, pe, word, start, length, in_compound, needflag):
        """PfxEntry::checkword"""
        la = len(pe.appnd)
        tmpl = length - la
        if tmpl > 0 or (tmpl == 0 and self.fullstrip):
            tmpword = pe.strip + word[start + la:start + la + tmpl]
            if pe.pfx_test_condition(tmpword):
                tmpl += len(pe.strip)
                he = self.words.get(tmpword)
                if he is not None:
                    cont = pe.cont
                    aflag = pe.aflag
                    needaffix = self.needaffix
                    while he is not None:
                        fl = he.flags
                        if (aflag in fl and not (needaffix in cont)
                                and (needflag == FLAG_NULL or needflag in fl or (cont and needflag in cont))):
                            return he
                        he = he.next
                if pe.opts & AE_XPRODUCT:
                    he = self.suffix_check(tmpword, 0, tmpl, AE_XPRODUCT, pe, FLAG_NULL, needflag, in_compound)
                    if he is not None:
                        return he
        return None

    def prefix_check_twosfx(self, word, start, length, in_compound, needflag=FLAG_NULL):
        self.pfx = None
        self.sfxappnd = None
        self.sfxextra = 0
        pe = self.pstart[0]
        while pe is not None:
            rv = self._pfx_check_twosfx(pe, word, start, length, in_compound, needflag)
            if rv is not None:
                return rv
            pe = pe.next
        for pptr in self._pfx_matches(word, start):
            rv = self._pfx_check_twosfx(pptr, word, start, length, in_compound, needflag)
            if rv is not None:
                self.pfx = pptr
                return rv
        return None

    def _pfx_check_twosfx(self, pe, word, start, length, in_compound, needflag):
        """PfxEntry::check_twosfx"""
        la = len(pe.appnd)
        tmpl = length - la
        if (tmpl > 0 or (tmpl == 0 and self.fullstrip)) and tmpl + len(pe.strip) >= pe.numconds:
            tmpword = pe.strip + word[start + la:]
            if pe.pfx_test_condition(tmpword):
                tmpl += len(pe.strip)
                if (pe.opts & AE_XPRODUCT) and in_compound != IN_CPD_BEGIN:
                    he = self.suffix_check_twosfx(tmpword, 0, tmpl, AE_XPRODUCT, pe, needflag)
                    if he is not None:
                        return he
        return None

    def _sfx_allowed(self, se, ppfx, cclass, in_compound):
        """the conditions of suffix_check for a suffix entry"""
        cont = se.cont
        if not ((in_compound != IN_CPD_BEGIN)
                or (cont and self.compoundpermitflag != FLAG_NULL and self.compoundpermitflag in cont)):
            return False
        circumfix = self.circumfix
        if circumfix != FLAG_NULL:
            pcont = ppfx.cont if ppfx is not None else ''
            if not (((not pcont or circumfix not in pcont) and (not cont or circumfix not in cont))
                    or (pcont and circumfix in pcont and cont and circumfix in cont)):
                return False
        if not (in_compound or not (cont and self.onlyincompound in cont)):
            return False
        if not (cclass != FLAG_NULL or not (cont and self.needaffix in cont)
                or (ppfx is not None and not (ppfx.cont and self.needaffix in ppfx.cont))):
            return False
        return True

    def suffix_check(self, word, start, length, sfxopts, ppfx, cclass, needflag, in_compound):
        se = self.sstart[0]
        if se is not None:
            whole = word[start:start + length]
            words = self.words
            if length == 0 and not self.fullstrip:
                se = None  # (no zero length suffix can match)
        while se is not None:
            # (shortcut: the entry can only match if the stem is a dictionary word)
            if (cclass == FLAG_NULL or se.cont) and (whole + se.strip) in words:
                if self._sfx_allowed(se, ppfx, cclass, in_compound):
                    rv = self._sfx_checkword(se, word, start, length, sfxopts, ppfx, cclass, needflag,
                                             FLAG_NULL if in_compound else self.onlyincompound)
                    if rv is not None:
                        self.sfx = se
                        return rv
            se = se.next
        if length == 0:
            return None  # FULLSTRIP
        end = start + length
        words = self.words
        fullstrip = self.fullstrip
        for sptr in self._sfx_matches(word, start, end):
            # (shortcut: the entry can only match if the stem is a dictionary word)
            tmpl = length - len(sptr.appnd)
            if tmpl < 0 or (tmpl == 0 and not fullstrip):
                continue
            if (word[start:start + tmpl] + sptr.strip) not in words:
                continue
            if self._sfx_allowed(sptr, ppfx, cclass, in_compound):
                cont = sptr.cont
                if in_compound != IN_CPD_END or ppfx is not None or not (cont and self.onlyincompound in cont):
                    rv = self._sfx_checkword(sptr, word, start, length, sfxopts, ppfx, cclass, needflag,
                                             FLAG_NULL if in_compound else self.onlyincompound)
                    if rv is not None:
                        self.sfx = sptr
                        self.sfxflag = sptr.aflag
                        if not cont:
                            self.sfxappnd = sptr.key
                        return rv
        return None

    def _sfx_matches(self, word, start, end):
        """the suffix entries whose (reversed) key matches the end of
        word[start:end], in the order of the search with the NextEQ/NextNE
        links of the sorted suffix list (cached per word ending)"""
        seg = word[max(start, end - self._max_sfx_key):end]
        r = self._sfx_cache.get(seg)
        if r is None:
            if self._sfx_groups is not None:
                # without '.' in the keys the search finds all the entries whose
                # affix ends the word, sorted by key (i.e. by affix length)
                r = []
                groups = self._sfx_groups
                n = len(seg)
                for k in self._sfx_lengths:
                    if k > n:
                        break
                    g = groups.get(seg[n - k:])
                    if g is not None:
                        r.extend(g)
            else:
                r = []
                n = len(seg)
                sptr = self.sstart[seg[-1]]
                while sptr is not None:
                    if _is_rev_subset(sptr.key, seg, n, n):
                        r.append(sptr)
                        sptr = sptr.nexteq
                    else:
                        sptr = sptr.nextne
            r = tuple(r)
            if len(self._sfx_cache) > 200000:
                self._sfx_cache.clear()
            self._sfx_cache[seg] = r
        return r

    def _pfx_matches(self, word, start):
        """the prefix entries whose key matches word[start:], in the order
        of the search with the NextEQ/NextNE links (cached)"""
        seg = word[start:start + self._max_pfx_key]
        r = self._pfx_cache.get(seg)
        if r is None:
            r = []
            if self._pfx_groups is not None:
                groups = self._pfx_groups
                n = len(seg)
                for k in self._pfx_lengths:
                    if k > n:
                        break
                    g = groups.get(seg[:k])
                    if g is not None:
                        r.extend(g)
            else:
                pptr = self.pstart[seg[0] if seg else 0]
                while pptr is not None:
                    if _is_subset(pptr.key, seg, 0):
                        r.append(pptr)
                        pptr = pptr.nexteq
                    else:
                        pptr = pptr.nextne
            r = tuple(r)
            if len(self._pfx_cache) > 200000:
                self._pfx_cache.clear()
            self._pfx_cache[seg] = r
        return r

    def _sfx_checkword(self, se, word, start, length, optflags, ppfx, cclass, needflag, badflag):
        """SfxEntry::checkword"""
        if (optflags & AE_XPRODUCT) and not (se.opts & AE_XPRODUCT):
            return None
        tmpl = length - len(se.appnd)
        if (tmpl > 0 or (tmpl == 0 and self.fullstrip)) and tmpl + len(se.strip) >= se.numconds:
            tmpstring = word[start:start + tmpl] + se.strip if se.strip else word[start:start + tmpl]
            if se.sfx_test_condition(tmpstring, len(tmpstring)):
                he = self.words.get(tmpstring)
                if he is not None:
                    aflag = se.aflag
                    cont = se.cont
                    ep = ppfx
                    while he is not None:
                        fl = he.flags
                        if ((aflag in fl or (ep is not None and ep.cont and aflag in ep.cont))
                                and (not (optflags & AE_XPRODUCT)
                                     or (ep is not None and ep.aflag in fl)
                                     or (cont and ep is not None and ep.aflag in cont))
                                and (cclass == FLAG_NULL or (cont and cclass in cont))
                                and (badflag == FLAG_NULL or badflag not in fl)
                                and (needflag == FLAG_NULL or needflag in fl or (cont and needflag in cont))):
                            return he
                        he = he.next
        return None

    def suffix_check_twosfx(self, word, start, length, sfxopts, ppfx, needflag):
        contclasses = self.contclasses
        se = self.sstart[0]
        while se is not None:
            if se.aflag in contclasses:
                rv = self._sfx_check_twosfx(se, word, start, length, sfxopts, ppfx, needflag)
                if rv is not None:
                    return rv
            se = se.next
        if length == 0:
            return None
        end = start + length
        for sptr in self._sfx_matches(word, start, end):
            if sptr.aflag in contclasses:
                rv = self._sfx_check_twosfx(sptr, word, start, length, sfxopts, ppfx, needflag)
                if rv is not None:
                    self.sfxflag = sptr.aflag
                    if not sptr.cont:
                        self.sfxappnd = sptr.key
                    return rv
        return None

    def _sfx_check_twosfx(self, se, word, start, length, optflags, ppfx, needflag):
        """SfxEntry::check_twosfx"""
        if (optflags & AE_XPRODUCT) and not (se.opts & AE_XPRODUCT):
            return None
        tmpl = length - len(se.appnd)
        if (tmpl > 0 or (tmpl == 0 and self.fullstrip)) and tmpl + len(se.strip) >= se.numconds:
            tmpword = word[start:start + tmpl] + se.strip
            tmpl += len(se.strip)
            if se.sfx_test_condition(tmpword, tmpl):
                if ppfx is not None:
                    if se.cont and ppfx.aflag in se.cont:
                        he = self.suffix_check(tmpword, 0, tmpl, 0, None, se.aflag, needflag, IN_CPD_NOT)
                    else:
                        he = self.suffix_check(tmpword, 0, tmpl, optflags, ppfx, se.aflag, needflag, IN_CPD_NOT)
                else:
                    he = self.suffix_check(tmpword, 0, tmpl, 0, None, se.aflag, needflag, IN_CPD_NOT)
                if he is not None:
                    return he
        return None

    def affix_check(self, word, start, length, needflag=FLAG_NULL, in_compound=IN_CPD_NOT):
        rv = self.prefix_check(word, start, length, in_compound, needflag)
        if rv is not None:
            return rv
        rv = self.suffix_check(word, start, length, 0, None, FLAG_NULL, needflag, in_compound)
        if self.havecontclass:
            self.sfx = None
            self.pfx = None
            if rv is not None:
                return rv
            rv = self.suffix_check_twosfx(word, start, length, 0, None, needflag)
            if rv is not None:
                return rv
            rv = self.prefix_check_twosfx(word, start, length, IN_CPD_NOT, needflag)
        return rv

    # --- compounding ---

    def _candidate_check(self, word):
        if self.words.get(word) is not None:
            return True
        return self.affix_check(word, 0, len(word)) is not None

    def _cpdrep_check(self, in_word, wl):
        if wl < 2 or not self.reptable:
            return False
        word = in_word[:wl]
        for pattern, outs in self.reptable:
            out = outs[0]
            if out:
                lenp = len(pattern)
                r = word.find(pattern)
                while r != -1:
                    candidate = word[:r] + out + word[r + lenp:]
                    if self._candidate_check(candidate):
                        return True
                    r = word.find(pattern, r + 1)
        return False

    def _cpdwordpair_check(self, word, wl):
        if wl > 2:
            candidate = word[:wl]
            utf8 = self.utf8
            for i in range(1, len(candidate)):
                if utf8 and (candidate[i] & 0xc0) == 0x80:
                    continue
                if self._candidate_check(candidate[:i] + b' ' + candidate[i:]):
                    return True
        return False

    def _cpdpat_check(self, word, pos, r1, r2, affixed):
        for pattern, pattern2, _pattern3, cond, cond2 in self.checkcpdtable:
            if (_is_subset(pattern2, word, pos)
                    and (r1 is None or cond == FLAG_NULL or (r1.flags and cond in r1.flags))
                    and (r2 is None or cond2 == FLAG_NULL or (r2.flags and cond2 in r2.flags))
                    and (not pattern
                         or (pattern[0] == 48 and len(r1.word) <= pos
                             and word[pos - len(r1.word):pos] == r1.word)
                         or (pattern[0] != 48 and len(pattern) <= pos
                             and word[pos - len(pattern):pos] == pattern))):
                return True
        return False

    def _cpdcase_check(self, word, pos):
        if self.utf8:
            p = pos - 1
            while p > 0 and (word[p] & 0xc0) == 0x80:
                p -= 1
            pair = u8_u16(word[p:])
            a = ord(pair[1]) if len(pair) > 1 else 0
            b = ord(pair[0]) if pair else 0
        else:
            a = word[pos - 1]
            b = word[pos]
            # 8-bit: ccase (is upper case)
            return ((self._lower_map.get(a, a) != a or self._lower_map.get(b, b) != b)
                    and a != 45 and b != 45)
        up = self._upper_map
        return (up.get(a, a) == a or up.get(b, b) == b) and a != 45 and b != 45

    def _get_syllable(self, word):
        if self.cpdmaxsyllable == 0:
            return 0
        if not self.utf8:
            return sum(1 for c in word.decode('latin-1') if c in self.cpdvowels)
        if not self.cpdvowels:
            return 0
        return sum(1 for c in u8_u16(word) if c in self.cpdvowels)

    def _setcminmax(self, word, length):
        if self.utf8:
            cpdmin = self.cpdmin
            cmin = 0
            i = 0
            while i < cpdmin and cmin < length:
                cmin += 1
                while cmin < length and (word[cmin] & 0xc0) == 0x80:
                    cmin += 1
                i += 1
            cmax = length
            i = 0
            while i < cpdmin - 1 and cmax >= 0:
                cmax -= 1
                while cmax >= 0 and (word[cmax] & 0xc0) == 0x80:
                    cmax -= 1
                i += 1
            return cmin, cmax
        return self.cpdmin, length - self.cpdmin + 1

    def _defcpd_check(self, words, wnum, rv, def_, all_):
        """AffixMgr::defcpd_check: returns (result, words)"""
        w = False
        if words is None:
            w = True
            words = def_
        if words is None:
            return False, None
        words[wnum] = rv
        if not rv.flags:
            words[wnum] = None
            return False, (None if w else words)
        ok = False
        for rule in self.defcpdtable:
            for f in rule:
                if f != '*' and f != '?' and f in rv.flags:
                    ok = True
                    break
        if not ok:
            words[wnum] = None
            return False, (None if w else words)
        for rule in self.defcpdtable:
            btinfo = [[0, 0, 0]]
            bt = 0
            pp = 0
            wp = 0
            ok2 = True
            ok = True
            rlen = len(rule)
            while True:
                while pp < rlen and wp <= wnum:
                    if pp + 1 < rlen and (rule[pp + 1] == '*' or rule[pp + 1] == '?'):
                        wend = wp if rule[pp + 1] == '?' else wnum
                        ok2 = True
                        pp += 2
                        btinfo[bt][0] = pp
                        btinfo[bt][1] = wp
                        while wp <= wend:
                            ww = words[wp]
                            if ww is None or not ww.flags or rule[pp - 2] not in ww.flags:
                                ok2 = False
                                break
                            wp += 1
                        if wp <= wnum:
                            ok2 = False
                        btinfo[bt][2] = wp - btinfo[bt][1]
                        if btinfo[bt][2] > 0:
                            bt += 1
                            btinfo.append([0, 0, 0])
                        if ok2:
                            break
                    else:
                        ok2 = True
                        ww = words[wp]
                        if ww is None or not ww.flags or rule[pp] not in ww.flags:
                            ok = False
                            break
                        pp += 1
                        wp += 1
                        if rlen == pp and not (wp > wnum):
                            ok = False
                if ok and ok2:
                    r = pp
                    while rlen > r and r + 1 < rlen and (rule[r + 1] == '*' or rule[r + 1] == '?'):
                        r += 2
                    if rlen <= r:
                        return True, words
                # backtrack
                if bt:
                    while True:
                        ok = True
                        btinfo[bt - 1][2] -= 1
                        pp = btinfo[bt - 1][0]
                        wp = btinfo[bt - 1][1] + btinfo[bt - 1][2]
                        if btinfo[bt - 1][2] < 0:
                            bt -= 1
                            if bt:
                                continue
                        break
                if not bt:
                    break
            if ok and ok2 and (not all_ or rlen <= pp):
                return True, words
            while ok and ok2 and rlen > pp and pp + 1 < rlen and (rule[pp + 1] == '*' or rule[pp + 1] == '?'):
                pp += 2
            if ok and ok2 and rlen <= pp:
                return True, words
        words[wnum] = None
        return False, (None if w else words)

    def compound_check(self, word, wordnum, numsyllable, maxwordnum, wnum, words, rwords, hu_mov_rule, is_sug,
                       info):
        """AffixMgr::compound_check (without the time limit, except in
        suggest() calls with a time limit)"""
        if is_sug and self._deadline is not None and perf_counter() > self._deadline:
            return None
        utf8 = self.utf8
        cf = self.compoundflag
        cb = self.compoundbegin
        cm = self.compoundmiddle
        ce = self.compoundend
        cff = self.compoundforbidflag
        needaffix = self.needaffix
        forbiddenword = self.a_forbiddenword
        nosuggest = self.nosuggest
        defcpd = self.defcpdtable
        checkcpd = self.checkcpdtable
        lookup = self.words.get
        rv = None
        striple = 0
        soldi = 0
        oldcmin = oldcmax = oldlen = 0
        checkedstriple = 0
        oldwords = words
        scpd = 0
        length = len(word)
        wlen = len(word)

        def wb(k):
            return word[k] if 0 <= k < wlen else 0
        cmin, cmax = self._setcminmax(word, length)
        st = bytearray(word)
        i = cmin
        while i < cmax:
            if utf8:
                while (st[i] if i < len(st) else 0) & 0xc0 == 0x80:
                    i += 1
                if i >= cmax:
                    return None
            words = oldwords
            onlycpdrule = 1 if words else 0
            while True:  # onlycpdrule loop
                oldnumsyllable = numsyllable
                oldwordnum = wordnum
                checked_prefix = 0
                while True:  # simplified checkcompoundpattern loop
                    exit_inner = False
                    for _once in (0,):
                        if scpd > 0:
                            while scpd <= len(checkcpd) and (
                                    not checkcpd[scpd - 1][2] or i > len(word)
                                    or word[i:i + len(checkcpd[scpd - 1][2])] != checkcpd[scpd - 1][2]):
                                scpd += 1
                            if scpd > len(checkcpd):
                                exit_inner = True
                                break
                            pat, pat2, pat3 = checkcpd[scpd - 1][0], checkcpd[scpd - 1][1], checkcpd[scpd - 1][2]
                            del st[i:]
                            st += pat
                            soldi = i
                            i += len(pat)
                            del st[i:]
                            st += pat2
                            del st[i + len(pat2):]
                            st += word[soldi + len(pat3):]
                            oldlen = length
                            length += len(pat) + len(pat2) - len(pat3)
                            oldcmin = cmin
                            oldcmax = cmax
                            cmin, cmax = self._setcminmax(bytes(st), length)
                            cmax = length - self.cpdmin + 1
                        if i > len(st):
                            return None
                        first = bytes(st[:i])
                        self.sfx = None
                        self.pfx = None
                        # FIRST WORD
                        affixed = 1
                        rv = lookup(first)
                        if (rv is not None and cff != FLAG_NULL and cff in rv.flags and not hu_mov_rule):
                            break  # continue
                        # search homonym with compound flag
                        while rv is not None and not hu_mov_rule:
                            fl = rv.flags
                            if needaffix != FLAG_NULL and needaffix in fl:
                                rv = rv.next
                                continue
                            ok = ((cf != FLAG_NULL and not words and not onlycpdrule and cf in fl)
                                  or (cb != FLAG_NULL and not wordnum and not onlycpdrule and cb in fl)
                                  or (cm != FLAG_NULL and wordnum and not words and not onlycpdrule and cm in fl))
                            if not ok and defcpd and onlycpdrule:
                                if not words and not wordnum:
                                    ok, words = self._defcpd_check(words, wnum, rv, rwords, 0)
                                if not ok and words:
                                    ok, words = self._defcpd_check(words, wnum, rv, rwords, 0)
                            if not ok or (scpd != 0 and checkcpd[scpd - 1][3] != FLAG_NULL
                                          and checkcpd[scpd - 1][3] not in fl):
                                rv = rv.next
                                continue
                            break
                        if rv is not None:
                            affixed = 0
                        if rv is None:
                            if onlycpdrule:
                                exit_inner = True
                                break
                            in_cpd = IN_CPD_OTHER if hu_mov_rule else IN_CPD_BEGIN
                            if cf != FLAG_NULL:
                                rv = self.prefix_check(first, 0, i, in_cpd, cf)
                                if rv is None:
                                    rv = self.suffix_check(first, 0, i, 0, None, FLAG_NULL, cf, in_cpd)
                                    if rv is None and self.compoundmoresuffixes:
                                        rv = self.suffix_check_twosfx(first, 0, i, 0, None, cf)
                                    if (rv is not None and not hu_mov_rule and self.sfx is not None and self.sfx.cont
                                            and ((cff != FLAG_NULL and cff in self.sfx.cont)
                                                 or (ce != FLAG_NULL and ce in self.sfx.cont))):
                                        rv = None
                            if rv is not None:
                                checked_prefix = 1
                            else:
                                if wordnum == 0 and cb != FLAG_NULL:
                                    rv = self.suffix_check(first, 0, i, 0, None, FLAG_NULL, cb, in_cpd)
                                    if rv is None and self.compoundmoresuffixes:
                                        rv = self.suffix_check_twosfx(first, 0, i, 0, None, cb)
                                    if rv is None:
                                        rv = self.prefix_check(first, 0, i, in_cpd, cb)
                                elif wordnum > 0 and cm != FLAG_NULL:
                                    rv = self.suffix_check(first, 0, i, 0, None, FLAG_NULL, cm, in_cpd)
                                    if rv is None and self.compoundmoresuffixes:
                                        rv = self.suffix_check_twosfx(first, 0, i, 0, None, cm)
                                    if rv is None:
                                        rv = self.prefix_check(first, 0, i, in_cpd, cm)
                                if rv is not None:
                                    checked_prefix = 1
                        elif rv.flags and (forbiddenword in rv.flags or needaffix in rv.flags
                                           or ONLYUPCASEFLAG in rv.flags
                                           or (is_sug and nosuggest != FLAG_NULL and nosuggest in rv.flags)):
                            exit_inner = True
                            break
                        pfx = self.pfx
                        sfx = self.sfx
                        # check non_compound flag in suffix and prefix
                        if (rv is not None and not hu_mov_rule
                                and ((pfx is not None and pfx.cont and cff in pfx.cont)
                                     or (sfx is not None and sfx.cont and cff in sfx.cont))):
                            rv = None
                        # check compoundend flag in suffix and prefix
                        if (rv is not None and not checked_prefix and ce != FLAG_NULL and not hu_mov_rule
                                and ((pfx is not None and pfx.cont and ce in pfx.cont)
                                     or (sfx is not None and sfx.cont and ce in sfx.cont))):
                            rv = None
                        # check compoundmiddle flag in suffix and prefix
                        if (rv is not None and not checked_prefix and wordnum == 0 and cm != FLAG_NULL
                                and not hu_mov_rule
                                and ((pfx is not None and pfx.cont and cm in pfx.cont)
                                     or (sfx is not None and sfx.cont and cm in sfx.cont))):
                            rv = None
                        # check forbiddenwords
                        if (rv is not None and rv.flags
                                and (forbiddenword in rv.flags or ONLYUPCASEFLAG in rv.flags
                                     or (is_sug and nosuggest != FLAG_NULL and nosuggest in rv.flags))):
                            return None
                        # increment word number, if the second root has a compoundroot flag
                        if rv is not None and self.compoundroot != FLAG_NULL and self.compoundroot in rv.flags:
                            wordnum += 1
                        # first word is acceptable in compound words?
                        first_ok = False
                        if rv is not None:
                            fl = rv.flags
                            if ((checked_prefix or (words and words[wnum] is not None)
                                 or (cf != FLAG_NULL and cf in fl)
                                 or (oldwordnum == 0 and cb != FLAG_NULL and cb in fl)
                                 or (oldwordnum > 0 and cm != FLAG_NULL and cm in fl))
                                    and (scpd == 0 or checkcpd[scpd - 1][3] == FLAG_NULL
                                         or checkcpd[scpd - 1][3] in fl)
                                    and not ((self.checkcompoundtriple and scpd == 0 and not words
                                              and wb(i - 1) == wb(i)
                                              and ((i > 1 and wb(i - 1) == wb(i - 2)) or wb(i - 1) == wb(i + 1)))
                                             or (self.checkcompoundcase and scpd == 0 and not words
                                                 and i < len(word) and self._cpdcase_check(word, i)))):
                                first_ok = True
                        if first_ok:
                            # NEXT WORD(S)
                            rv_first = rv
                            while True:  # striple loop
                                for _once2 in (0,):
                                    # check simplifiedtriple
                                    if self.simplifiedtriple:
                                        if striple:
                                            checkedstriple = 1
                                            i -= 1  # check "fahrt" instead of "ahrt" in "Schiffahrt"
                                        elif i > 2 and i <= len(word) and wb(i - 1) == wb(i - 2):
                                            striple = 1
                                    rest = bytes(st[i:])
                                    rv = lookup(rest)
                                    # search homonym with compound flag
                                    while rv is not None:
                                        fl = rv.flags
                                        if needaffix != FLAG_NULL and needaffix in fl:
                                            rv = rv.next
                                            continue
                                        ok = ((cf != FLAG_NULL and not words and cf in fl)
                                              or (ce != FLAG_NULL and not words and ce in fl))
                                        if not ok and defcpd and words:
                                            ok, words = self._defcpd_check(words, wnum + 1, rv, None, 1)
                                        if not ok or (scpd != 0 and checkcpd[scpd - 1][4] != FLAG_NULL
                                                      and checkcpd[scpd - 1][4] not in fl):
                                            rv = rv.next
                                            continue
                                        break
                                    # check FORCEUCASE
                                    if (rv is not None and self.forceucase != FLAG_NULL
                                            and self.forceucase in rv.flags
                                            and not (info is not None and info & SPELL_ORIGCAP)):
                                        rv = None
                                    if rv is not None and words and words[wnum + 1] is not None:
                                        return rv_first
                                    oldnumsyllable2 = numsyllable
                                    oldwordnum2 = wordnum
                                    # increment word number, if the second root has a compoundroot flag
                                    if (rv is not None and self.compoundroot != FLAG_NULL
                                            and self.compoundroot in rv.flags):
                                        wordnum += 1
                                    # check forbiddenwords
                                    if (rv is not None and rv.flags
                                            and (forbiddenword in rv.flags or ONLYUPCASEFLAG in rv.flags
                                                 or (is_sug and nosuggest != FLAG_NULL and nosuggest in rv.flags))):
                                        return None
                                    # second word is acceptable, as a root?
                                    if (rv is not None
                                            and ((cf != FLAG_NULL and cf in rv.flags)
                                                 or (ce != FLAG_NULL and ce in rv.flags))
                                            and ((self.cpdwordmax == -1 or wordnum + 1 < self.cpdwordmax)
                                                 or (self.cpdmaxsyllable != 0
                                                     and numsyllable + self._get_syllable(rv.word)
                                                     <= self.cpdmaxsyllable))
                                            and (not checkcpd or scpd != 0
                                                 or (i < len(word)
                                                     and not self._cpdpat_check(word, i, rv_first, rv, 0)))
                                            and (not self.checkcompounddup or rv is not rv_first)
                                            and (scpd == 0 or checkcpd[scpd - 1][4] == FLAG_NULL
                                                 or checkcpd[scpd - 1][4] in rv.flags)):
                                        # forbid compound word, if it is a non-compound word with typical fault
                                        if ((self.checkcompoundrep and self._cpdrep_check(word, length))
                                                or self._cpdwordpair_check(word, length)):
                                            return None
                                        return rv_first
                                    numsyllable = oldnumsyllable2
                                    wordnum = oldwordnum2
                                    # perhaps second word has prefix or/and suffix
                                    self.sfx = None
                                    self.sfxflag = FLAG_NULL
                                    rv = (self.affix_check(word, i, len(word) - i, cf, IN_CPD_END)
                                          if (cf != FLAG_NULL and not onlycpdrule and i < len(word)) else None)
                                    if rv is None and ce != FLAG_NULL and not onlycpdrule:
                                        self.sfx = None
                                        self.pfx = None
                                        if i < len(word):
                                            rv = self.affix_check(word, i, len(word) - i, ce, IN_CPD_END)
                                    if rv is None and defcpd and words:
                                        if i < len(word):
                                            rv = self.affix_check(word, i, len(word) - i, FLAG_NULL, IN_CPD_END)
                                        if rv is not None:
                                            ok, words = self._defcpd_check(words, wnum + 1, rv, None, 1)
                                            if ok:
                                                return rv_first
                                        rv = None
                                    # test CHECKCOMPOUNDPATTERN conditions (allowed forms)
                                    if (rv is not None and not (scpd == 0 or checkcpd[scpd - 1][4] == FLAG_NULL
                                                                or checkcpd[scpd - 1][4] in rv.flags)):
                                        rv = None
                                    # test CHECKCOMPOUNDPATTERN conditions (forbidden compounds)
                                    if (rv is not None and checkcpd and scpd == 0
                                            and self._cpdpat_check(word, i, rv_first, rv, affixed)):
                                        rv = None
                                    pfx = self.pfx
                                    sfx = self.sfx
                                    # check non_compound flag in suffix and prefix
                                    if (rv is not None
                                            and ((pfx is not None and pfx.cont and cff in pfx.cont)
                                                 or (sfx is not None and sfx.cont and cff in sfx.cont))):
                                        rv = None
                                    # check FORCEUCASE
                                    if (rv is not None and self.forceucase != FLAG_NULL
                                            and self.forceucase in rv.flags
                                            and not (info is not None and info & SPELL_ORIGCAP)):
                                        rv = None
                                    # check forbiddenwords
                                    if (rv is not None and rv.flags
                                            and (forbiddenword in rv.flags or ONLYUPCASEFLAG in rv.flags
                                                 or (is_sug and nosuggest != FLAG_NULL and nosuggest in rv.flags))):
                                        return None
                                    # increment word number, if the second word has a compoundroot flag
                                    if (rv is not None and self.compoundroot != FLAG_NULL
                                            and self.compoundroot in rv.flags):
                                        wordnum += 1
                                    # second word is acceptable, as a word with prefix or/and suffix?
                                    if (rv is not None
                                            and ((self.cpdwordmax == -1 or wordnum + 1 < self.cpdwordmax)
                                                 or (self.cpdmaxsyllable != 0
                                                     and numsyllable <= self.cpdmaxsyllable))
                                            and (not self.checkcompounddup or rv is not rv_first)):
                                        # forbid compound word, if it is a non-compound word with typical fault
                                        if ((self.checkcompoundrep and self._cpdrep_check(word, length))
                                                or self._cpdwordpair_check(word, length)):
                                            return None
                                        return rv_first
                                    numsyllable = oldnumsyllable2
                                    wordnum = oldwordnum2
                                    # perhaps second word is a compound word (recursive call)
                                    if wordnum + 2 < maxwordnum:
                                        rv = self.compound_check(bytes(st[i:]), wordnum + 1, numsyllable,
                                                                 maxwordnum, wnum + 1, words, rwords, 0, is_sug, info)
                                        if (rv is not None and checkcpd and i < len(word)
                                                and ((scpd == 0 and self._cpdpat_check(word, i, rv_first, rv, affixed))
                                                     or (scpd != 0
                                                         and not self._cpdpat_check(word, i, rv_first, rv, affixed)))):
                                            rv = None
                                    else:
                                        rv = None
                                    if rv is not None:
                                        # forbid compound word, if it is a non-compound word with typical
                                        # fault, or a dictionary word pair
                                        if self._cpdwordpair_check(word, length):
                                            return None
                                        if self.checkcompoundrep or forbiddenword != FLAG_NULL:
                                            if self.checkcompoundrep and self._cpdrep_check(word, length):
                                                return None
                                            # check first part
                                            if i < len(word) and word[i:i + len(rv.word)] == rv.word:
                                                n = i + len(rv.word)
                                                stn = bytes(st[:n])
                                                if ((self.checkcompoundrep and self._cpdrep_check(stn, n))
                                                        or self._cpdwordpair_check(stn, n)):
                                                    break  # continue (striple loop)
                                                if forbiddenword != FLAG_NULL:
                                                    rv2 = lookup(word)
                                                    if rv2 is None and length <= len(word):
                                                        rv2 = self.affix_check(word, 0, length)
                                                    if (rv2 is not None and rv2.flags and forbiddenword in rv2.flags
                                                            and rv2.word.startswith(stn)):
                                                        return None
                                        return rv_first
                                if not (striple and not checkedstriple):
                                    break
                            if checkedstriple:
                                i += 1
                                checkedstriple = 0
                                striple = 0
                        if soldi != 0:
                            i = soldi
                            soldi = 0
                            length = oldlen
                            cmin = oldcmin
                            cmax = oldcmax
                        scpd += 1
                    if exit_inner:
                        break
                    if not (not onlycpdrule and self.simplifiedcpd and scpd <= len(checkcpd)):
                        break
                scpd = 0
                wordnum = oldwordnum
                numsyllable = oldnumsyllable
                if soldi != 0:
                    i = soldi
                    st = bytearray(word)
                    soldi = 0
                if not (defcpd and oldwordnum == 0 and onlycpdrule < 1):
                    break
                onlycpdrule += 1
            i += 1
        return None

    # ------------------------------------------------------------------
    # HunspellImpl

    def _clean_ignore(self, w):
        if self._ignore_units is None:
            return w
        return self._remove_ignored(w, self.a_ignorechars)

    def _checkword(self, w, info):
        """HunspellImpl::checkword; info is a one-element list"""
        word = self._clean_ignore(w)
        if not word:
            return None
        if self.a_complexprefixes:
            word = _reverse_utf(word) if self.utf8 else word[::-1]
        he = self.words.get(word)
        if he is not None:
            if he.flags and self.a_forbiddenword in he.flags:
                info[0] |= SPELL_FORBIDDEN
                return None
            needaffix = self.needaffix
            oic = self.onlyincompound
            while he is not None and he.flags and (
                    (needaffix != FLAG_NULL and needaffix in he.flags)
                    or (oic != FLAG_NULL and oic in he.flags)
                    or ((info[0] & SPELL_INITCAP) and ONLYUPCASEFLAG in he.flags)):
                he = he.next
        if he is None:
            he = self.affix_check(word, 0, len(word))
            if he is not None and he.flags and (
                    (self.onlyincompound != FLAG_NULL and self.onlyincompound in he.flags)
                    or ((info[0] & SPELL_INITCAP) and ONLYUPCASEFLAG in he.flags)):
                he = None
            if he is not None:
                if he.flags and self.a_forbiddenword in he.flags:
                    info[0] |= SPELL_FORBIDDEN
                    return None
            elif self.is_compound:
                rwords = [None] * 100
                he = self.compound_check(word, 0, 0, 100, 0, None, rwords, 0, 0, info[0])
                if he is not None:
                    info[0] |= SPELL_COMPOUND
        return he

    def _is_keepcase(self, rv):
        return bool(rv.flags) and self.keepcase != FLAG_NULL and self.keepcase in rv.flags

    def _spellsharps(self, base, n_pos, n, repnum, info):
        pos = base.find(b'ss', n_pos)
        if pos != -1 and n < MAXSHARPS:
            sharp = b'\xc3\x9f' if self.utf8 else b'\xdf'
            h = self._spellsharps(base[:pos] + sharp + base[pos + 2:], pos + len(sharp), n + 1, repnum + 1, info)
            if h is not None:
                return h
            h = self._spellsharps(base, pos + 2, n + 1, repnum, info)
            if h is not None:
                return h
        elif repnum > 0:
            return self._checkword(base, info)
        return None

    def _cleanword2(self, src):
        """returns (scw, sunicw, captype, abbv)"""
        w2 = self._clean_ignore(src)
        q = 0
        nl = len(w2)
        while q < len(w2) and w2[q] == 32:
            q += 1
            nl -= 1
        abbv = 0
        while nl > 0 and w2[q + nl - 1] == 46:
            nl -= 1
            abbv += 1
        if nl <= 0:
            return b'', '', NOCAP, abbv
        dest = w2[q:q + nl]
        u = self._units(dest)
        return dest, u, self.captype_units(u), abbv

    def _mkallsmall2(self, u):
        u = u.translate(self._lower_tr)
        return self._from_units(u), u

    def _mkinitcap2(self, u):
        if u:
            u = u[0].translate(self._upper_tr) + u[1:]
        return self._from_units(u), u

    def spell(self, word):
        """Hunspell::spell(word): whether the word is spelled correctly
        (the word is encoded like the Java binding does it: unmappable
        characters become '?', the word ends at a NUL character)."""
        r = self._spell_cache.get(word)
        if r is not None:
            return r
        b = self._encode(word)
        with self._lock:
            r = self._spell(b, [])
            if len(self._spell_cache) >= 100000:
                self._spell_cache.clear()
            self._spell_cache[word] = r
        return r

    def _encode(self, word):
        if self.utf8:
            b = word.encode('utf-8', 'replace')
        else:
            b = word.encode(self._codec, 'replace')
        k = b.find(b'\x00')
        if k != -1:
            b = b[:k]
        return b

    def _spell(self, word, candidate_stack):
        if word in candidate_stack:
            return False
        candidate_stack.append(word)
        try:
            return self._spell_internal(word, candidate_stack)
        finally:
            candidate_stack.pop()

    def _spell_internal(self, word, candidate_stack):
        info = [0]
        if word == SPELL_XML:
            return True
        if len(word) >= (MAXWORDUTF8LEN if self.utf8 else MAXWORDLEN):
            return False
        if self.iconvtable is not None:
            converted = self.iconvtable.conv(word)
            if converted is not None:
                word = converted
        scw, sunicw, captype, abbv = self._cleanword2(word)
        if not scw:
            return True
        # allow numbers with dots, dashes and commas (but forbid double separators: "..", "--" etc.)
        nstate = 0  # NBEGIN
        i = 0
        wl = len(scw)
        while i < wl:
            c = scw[i]
            if 48 <= c <= 57:
                nstate = 1  # NNUM
            elif c in (44, 46, 45):
                if nstate == 2 or i == 0:
                    break
                nstate = 2  # NSEP
            else:
                break
            i += 1
        if i == wl and nstate == 1:
            return True
        rv = None
        checkword = self._checkword
        if captype in (HUHCAP, HUHINITCAP, NOCAP):
            if captype != NOCAP:
                info[0] |= SPELL_ORIGCAP
            rv = checkword(scw, info)
            if abbv and rv is None:
                rv = checkword(scw + b'.', info)
        else:
            done = False
            if captype == ALLCAP:
                info[0] |= SPELL_ORIGCAP
                rv = checkword(scw, info)
                if rv is not None:
                    done = True
                if not done and abbv:
                    rv = checkword(scw + b'.', info)
                    if rv is not None:
                        done = True
                if not done:
                    # Spec. prefix handling for Catalan, French, Italian:
                    # prefixes separated by apostrophe (SANT'ELIA -> Sant'+Elia).
                    apos = scw.find(b"'")
                    if apos != -1:
                        scw, sunicw = self._mkallsmall2(sunicw)
                        if apos < len(scw) - 1:
                            part1 = scw[:apos + 1]
                            part2 = scw[apos + 1:]
                            if self.utf8:
                                part1u = u8_u16(part1)
                                part2, part2u = self._mkinitcap2(u8_u16(part2))
                                scw = part1 + part2
                                sunicw = part1u + part2u
                                rv = checkword(scw, info)
                                if rv is not None:
                                    done = True
                            else:
                                part2, _ = self._mkinitcap2(self._units(part2))
                                scw = part1 + part2
                                rv = checkword(scw, info)
                                if rv is not None:
                                    done = True
                            if not done:
                                scw, sunicw = self._mkinitcap2(sunicw)
                                rv = checkword(scw, info)
                                if rv is not None:
                                    done = True
                if not done and self.checksharps and b'SS' in scw:
                    scw, sunicw = self._mkallsmall2(sunicw)
                    u8buffer = scw
                    rv = self._spellsharps(u8buffer, 0, 0, 0, info)
                    if rv is None:
                        scw, sunicw = self._mkinitcap2(sunicw)
                        rv = self._spellsharps(scw, 0, 0, 0, info)
                    if abbv and rv is None:
                        u8buffer = u8buffer + b'.'
                        rv = self._spellsharps(u8buffer, 0, 0, 0, info)
                        if rv is None:
                            u8buffer = scw + b'.'
                            rv = self._spellsharps(u8buffer, 0, 0, 0, info)
                    if rv is not None:
                        done = True
            if not done:
                # INITCAP (and ALLCAP falling through)
                idot = self.utf8 and scw[:2] == b'\xc4\xb0'
                info[0] |= SPELL_ORIGCAP
                if captype == ALLCAP:
                    scw, sunicw = self._mkallsmall2(sunicw)
                    scw, sunicw = self._mkinitcap2(sunicw)
                    if idot:
                        scw = b'\xc4\xb0' + scw[1:]
                if captype == INITCAP:
                    info[0] |= SPELL_INITCAP
                rv = checkword(scw, info)
                if captype == INITCAP:
                    info[0] &= ~SPELL_INITCAP
                # forbid bad capitalization
                if info[0] & SPELL_FORBIDDEN:
                    rv = None
                else:
                    if rv is not None and self._is_keepcase(rv) and captype == ALLCAP:
                        rv = None
                    if not (rv is not None or (idot and self.langnum not in (LANG_az, LANG_tr, LANG_crh))):
                        scw, sunicw = self._mkallsmall2(sunicw)
                        u8buffer = scw
                        scw, sunicw = self._mkinitcap2(sunicw)
                        rv = checkword(u8buffer, info)
                        finished = False
                        if abbv and rv is None:
                            u8buffer = u8buffer + b'.'
                            rv = checkword(u8buffer, info)
                            if rv is None:
                                u8buffer = scw + b'.'
                                if captype == INITCAP:
                                    info[0] |= SPELL_INITCAP
                                rv = checkword(u8buffer, info)
                                if captype == INITCAP:
                                    info[0] &= ~SPELL_INITCAP
                                if rv is not None and self._is_keepcase(rv) and captype == ALLCAP:
                                    rv = None
                                finished = True
                        if not finished:
                            sharp = b'\xc3\x9f' if self.utf8 else b'\xdf'
                            if (rv is not None and self._is_keepcase(rv)
                                    and (captype == ALLCAP or not (self.checksharps and sharp in u8buffer))):
                                rv = None
        if rv is not None:
            if self.warn != FLAG_NULL and rv.flags and self.warn in rv.flags:
                info[0] |= SPELL_WARN
                return not self.forbidwarn
            return True
        # recursive breaking at break points
        if self.wordbreak and not (info[0] & SPELL_FORBIDDEN):
            nbr = 0
            wl = len(scw)
            for j in self.wordbreak:
                if j:
                    nbr += scw.count(j)
            if nbr >= 10:
                return False
            spell = self._spell
            # check boundary patterns (^begin and end$)
            for j in self.wordbreak:
                plen = len(j)
                if plen == 1 or plen > wl:
                    continue
                if j[0] == 94 and scw[:plen - 1] == j[1:] and spell(scw[plen - 1:], candidate_stack):
                    return True
                if j[plen - 1] == 36 and scw[wl - plen + 1:] == j[:plen - 1]:
                    if spell(scw[:wl - plen + 1], candidate_stack):
                        return True
            # other patterns
            for j in self.wordbreak:
                plen = len(j)
                found = scw.find(j)
                if 0 < found < wl - plen:
                    found2 = scw.find(j, found + 1)
                    # try to break at the second occurance to recognize dictionary words with wordbreak
                    if 0 < found2 < wl - plen:
                        found = found2
                    if not spell(scw[found + plen:], candidate_stack):
                        continue
                    # examine 2 sides of the break point
                    if spell(scw[:found], candidate_stack):
                        return True
            # other patterns (break at first break point)
            for j in self.wordbreak:
                plen = len(j)
                found = scw.find(j)
                if 0 < found < wl - plen:
                    if not spell(scw[found + plen:], candidate_stack):
                        continue
                    if spell(scw[:found], candidate_stack):
                        return True
        return False

    def add(self, word):
        """Hunspell::add (HashMgr::add): add a word without flags"""
        with self._lock:
            self._spell_cache.clear()
            b = self._encode(word)
            dp = self.words.get(b)
            if dp is not None:
                # remove_forbidden_flag
                while dp is not None:
                    if dp.flags and self.forbiddenword in dp.flags:
                        dp.flags = ''
                    dp = dp.next
                return
            u = self._units(b)
            captype = self.captype_units(u)
            self._add_word(b, '', False)
            self._add_hidden_capitalized_word(u, '', captype)
            self._sug_data = None

    # ------------------------------------------------------------------
    # SuggestMgr (Hunspell 1.7.1, without the CPU time limits)

    def _sug_checkword(self, word, cpdsuggest):
        """SuggestMgr::checkword"""
        if cpdsuggest == 1:
            if self.is_compound:
                rwords = [None] * 100
                rv = self.compound_check(word, 0, 0, 100, 0, None, rwords, 0, 1, None)
                if rv is not None:
                    rv2 = self.words.get(word)
                    if (rv2 is None or not rv2.flags
                            or not (self.a_forbiddenword in rv2.flags or self.nosuggest in rv2.flags)):
                        return 3
            return 0
        nosuffix = 0
        rv = self.words.get(word)
        if rv is not None:
            fl = rv.flags
            if fl and (self.a_forbiddenword in fl or self.nosuggest in fl or self.substandard in fl):
                return 0
            while rv is not None:
                fl = rv.flags
                if fl and (self.needaffix in fl or ONLYUPCASEFLAG in fl or self.onlyincompound in fl):
                    rv = rv.next
                else:
                    break
        else:
            rv = self.prefix_check(word, 0, len(word), 0)
        if rv is not None:
            nosuffix = 1
        else:
            rv = self.suffix_check(word, 0, len(word), 0, None, FLAG_NULL, FLAG_NULL, IN_CPD_NOT)
        if rv is None and self.havecontclass:
            rv = self.suffix_check_twosfx(word, 0, len(word), 0, None, FLAG_NULL)
            if rv is None:
                rv = self.prefix_check_twosfx(word, 0, len(word), 0, FLAG_NULL)
        if rv is not None and rv.flags and (self.a_forbiddenword in rv.flags or ONLYUPCASEFLAG in rv.flags
                                            or self.nosuggest in rv.flags or self.onlyincompound in rv.flags):
            return 0
        if rv is not None:
            if self.compoundflag != FLAG_NULL and self.compoundflag in rv.flags:
                return 2 + nosuffix
            return 1
        return 0

    def _testsug(self, wlst, candidate, cpdsuggest):
        """SuggestMgr::testsug"""
        if len(wlst) == self.maxsug:
            return
        if candidate in wlst:
            return
        if self._sug_checkword(candidate, cpdsuggest):
            wlst.append(candidate)

    def _sm_suggest(self, slst, word, onlycmpdsug):
        """SuggestMgr::suggest: returns whether there is a good suggestion;
        onlycmpdsug is a one-element list"""
        nocompoundtwowords = 0
        nsugorig = len(slst)
        old_sug = 0
        good_suggestion = False
        if self.a_complexprefixes:
            word = _reverse_utf(word) if self.utf8 else word[::-1]
        if self.utf8:
            if _FOUR_BYTE.search(word):
                return False
            u = u8_u16(word)
        else:
            u = word.decode('latin-1')
        maxsug = self.maxsug
        maxcpdsugs = self.s_maxcpdsugs
        cpdsuggest = 0
        while cpdsuggest < 2 and nocompoundtwowords == 0 and not good_suggestion:
            if cpdsuggest > 0:
                old_sug = len(slst)

            def room():
                if self._deadline is not None and perf_counter() > self._deadline:
                    return False
                return len(slst) < maxsug and (not cpdsuggest or len(slst) < old_sug + maxcpdsugs)
            # suggestions for an uppercase word (html -> HTML)
            if len(slst) < maxsug:
                i = len(slst)
                self._testsug(slst, self._from_units(u.translate(self._upper_tr)), cpdsuggest)
                if len(slst) > i:
                    good_suggestion = True
            # perhaps we made a typical fault of spelling
            if room():
                i = len(slst)
                self._replchars(slst, word, cpdsuggest)
                if len(slst) > i:
                    good_suggestion = True
            # perhaps we made chose the wrong char from a related set
            if room():
                self._mapchars(slst, word, cpdsuggest)
            # only suggest compound words when no other suggestion
            if cpdsuggest == 0 and len(slst) > nsugorig:
                nocompoundtwowords = 1
            if room():
                self._swapchar(slst, u, cpdsuggest)
            if room():
                self._longswapchar(slst, u, cpdsuggest)
            if room():
                self._badcharkey(slst, u, cpdsuggest)
            if room():
                self._extrachar(slst, u, cpdsuggest)
            if room():
                self._forgotchar(slst, u, cpdsuggest)
            if room():
                self._movechar(slst, u, cpdsuggest)
            if room():
                self._badchar(slst, u, cpdsuggest)
            if room():
                self._doubletwochars(slst, u, cpdsuggest)
            # perhaps we forgot to hit space and two words ran together
            if not cpdsuggest or (not self.nosplitsugs and len(slst) < old_sug + maxcpdsugs):
                good_suggestion = self._twowords(slst, word, cpdsuggest, good_suggestion)
            cpdsuggest += 1
        if not nocompoundtwowords and slst and onlycmpdsug is not None:
            onlycmpdsug[0] = 1
        return good_suggestion

    def _mapchars(self, wlst, word, cpdsuggest):
        if len(word) < 2 or not self.maptable:
            return
        if self._deadline is None:
            self._map_related(word, b'', 0, wlst, cpdsuggest)
            return
        # with a time limit: like Hunspell's map_related timer (a quarter of the limit, checked every 100 calls)
        self._map_timer = [100, min(self._deadline, perf_counter() + self._time_limit / 4)]
        try:
            self._map_related(word, b'', 0, wlst, cpdsuggest)
        except _TimeLimit:
            pass
        finally:
            self._map_timer = None

    def _map_related(self, word, candidate, wn, wlst, cpdsuggest):
        timer = self._map_timer
        if timer is not None:
            timer[0] -= 1
            if not timer[0]:
                if perf_counter() > timer[1]:
                    raise _TimeLimit()
                timer[0] = 100
        if wn >= len(word):
            if candidate not in wlst and self._sug_checkword(candidate, cpdsuggest):
                if len(wlst) < self.maxsug:
                    wlst.append(candidate)
            return
        in_map = False
        for entry in self.maptable:
            for k in entry:
                if k and word.startswith(k, wn):
                    in_map = True
                    for repl in entry:
                        self._map_related(word, candidate + repl, wn + len(k), wlst, cpdsuggest)
        if not in_map:
            self._map_related(word, candidate + word[wn:wn + 1], wn + 1, wlst, cpdsuggest)

    def _replchars(self, wlst, word, cpdsuggest):
        wl = len(word)
        if wl < 2:
            return
        for pattern, outs in self.reptable:
            r = word.find(pattern)
            while r != -1:
                rtype = 1 if r == 0 else 0
                if r + len(pattern) == wl:
                    rtype += 2
                while rtype and not outs[rtype]:
                    rtype = 0 if (rtype == 2 and r != 0) else rtype - 1
                out = outs[rtype]
                if out:
                    candidate = word[:r] + out + word[r + len(pattern):]
                    self._testsug(wlst, candidate, cpdsuggest)
                    sp = candidate.find(b' ')
                    prev = 0
                    while sp != -1:
                        prev_chunk = candidate[prev:sp]
                        if self._sug_checkword(prev_chunk, 0):
                            oldns = len(wlst)
                            self._testsug(wlst, candidate[sp + 1:], cpdsuggest)
                            if oldns < len(wlst):
                                wlst[-1] = candidate
                        prev = sp + 1
                        sp = candidate.find(b' ', prev)
                r = word.find(pattern, r + 1)

    def _doubletwochars(self, wlst, u, cpdsuggest):
        wl = len(u)
        if wl < 5:
            return
        state = 0
        for i in range(2, wl):
            if u[i] == u[i - 2]:
                state += 1
                if state == 3 or (state == 2 and i >= 4):
                    self._testsug(wlst, self._from_units(u[:i - 1] + u[i + 1:]), cpdsuggest)
                    state = 0
            else:
                state = 0

    def _badcharkey(self, wlst, u, cpdsuggest):
        to8 = self._from_units
        upper = _UPPER  # upper_utf(c, 1): no language specific casing
        ckey = self.ckey
        nk = len(ckey)
        for i in range(len(u)):
            tmpc = u[i]
            if self.utf8:
                up = chr(upper.get(ord(tmpc), ord(tmpc)))
            else:
                up = tmpc.translate(self._upper_tr)
            if up != tmpc:
                self._testsug(wlst, to8(u[:i] + up + u[i + 1:]), cpdsuggest)
            if not ckey:
                continue
            loc = ckey.find(tmpc)
            while loc != -1:
                if loc > 0 and ckey[loc - 1] != '|':
                    self._testsug(wlst, to8(u[:i] + ckey[loc - 1] + u[i + 1:]), cpdsuggest)
                if loc + 1 < nk and ckey[loc + 1] != '|':
                    self._testsug(wlst, to8(u[:i] + ckey[loc + 1] + u[i + 1:]), cpdsuggest)
                loc = ckey.find(tmpc, loc + 1)

    def _badchar(self, wlst, u, cpdsuggest):
        to8 = self._from_units
        for t in self.ctry:
            for i in range(len(u) - 1, -1, -1):
                if u[i] == t:
                    continue
                self._testsug(wlst, to8(u[:i] + t + u[i + 1:]), cpdsuggest)

    def _extrachar(self, wlst, u, cpdsuggest):
        n = len(u)
        if n < 2:
            return
        for i in range(n):
            index = n - 1 - i
            self._testsug(wlst, self._from_units(u[:index] + u[index + 1:]), cpdsuggest)

    def _forgotchar(self, wlst, u, cpdsuggest):
        n = len(u)
        to8 = self._from_units
        for k in self.ctry:
            for i in range(n + 1):
                index = n - i
                self._testsug(wlst, to8(u[:index] + k + u[index:]), cpdsuggest)

    def _mystrlen(self, b):
        if self.utf8:
            return -1 if _FOUR_BYTE.search(b) else len(u8_u16(b))
        return len(b)

    def _twowords(self, wlst, word, cpdsuggest, good):
        """SuggestMgr::twowords"""
        wl = len(word)
        if wl < 3:
            return False
        cw = self._sug_checkword
        utf8 = self.utf8
        maxsug = self.maxsug
        k = 0
        while True:
            # split after the next character
            if k + 1 >= wl:
                break
            k += 1
            while utf8 and k < wl and (word[k] & 0xc0) == 0x80:
                k += 1
            if utf8 and k >= wl:
                break  # last UTF-8 character
            candidate = word[:k] + b' ' + word[k:]
            if not cpdsuggest and cw(candidate, cpdsuggest):
                if not good:
                    good = True
                    del wlst[:]
                wlst.insert(0, candidate)
            if self.lang_with_dash_usage:
                candidate = word[:k] + b'-' + word[k:]
                if not cpdsuggest and cw(candidate, cpdsuggest):
                    if not good:
                        good = True
                        del wlst[:]
                    wlst.insert(0, candidate)
            if len(wlst) < maxsug and not self.nosplitsugs and not good:
                if cw(word[:k], cpdsuggest) and cw(word[k:], cpdsuggest):
                    candidate = word[:k] + b' ' + word[k:]
                    cwrd = candidate not in wlst
                    if cwrd and len(wlst) < maxsug:
                        wlst.append(candidate)
                    if (not self.nosplitsugs and self.lang_with_dash_usage
                            and self._mystrlen(word[k:]) > 1 and self._mystrlen(word[:k]) > 1):
                        candidate = word[:k] + b'-' + word[k:]
                        if candidate in wlst:
                            cwrd = False
                        if len(wlst) < maxsug and cwrd:
                            wlst.append(candidate)
        return good

    def _swapchar(self, wlst, u, cpdsuggest):
        n = len(u)
        if n < 2:
            return
        to8 = self._from_units
        for i in range(n - 1):
            self._testsug(wlst, to8(u[:i] + u[i + 1] + u[i] + u[i + 2:]), cpdsuggest)
        if n == 4 or n == 5:
            c = list(u)
            c[0] = u[1]
            c[1] = u[0]
            c[2] = u[2]
            c[n - 2] = u[n - 1]
            c[n - 1] = u[n - 2]
            self._testsug(wlst, to8(''.join(c)), cpdsuggest)
            if n == 5:
                c[0] = u[0]
                c[1] = u[2]
                c[2] = u[1]
                self._testsug(wlst, to8(''.join(c)), cpdsuggest)

    def _longswapchar(self, wlst, u, cpdsuggest):
        n = len(u)
        to8 = self._from_units
        for p in range(n):
            for q in range(n):
                d = abs(q - p)
                if 1 < d <= MAX_CHAR_DISTANCE:
                    c = list(u)
                    c[p], c[q] = c[q], c[p]
                    self._testsug(wlst, to8(''.join(c)), cpdsuggest)

    def _movechar(self, wlst, u, cpdsuggest):
        n = len(u)
        if n < 2:
            return
        to8 = self._from_units
        for p in range(n):
            c = list(u)
            q = p + 1
            while q < n and q - p <= MAX_CHAR_DISTANCE:
                c[q], c[q - 1] = c[q - 1], c[q]
                if q - p >= 2:
                    self._testsug(wlst, to8(''.join(c)), cpdsuggest)
                q += 1
        for p in range(n - 1, -1, -1):
            c = list(u)
            q = p - 1
            while q >= 0 and p - q <= MAX_CHAR_DISTANCE:
                c[q], c[q + 1] = c[q + 1], c[q]
                if p - q >= 2:
                    self._testsug(wlst, to8(''.join(c)), cpdsuggest)
                q -= 1

    # --- ngram suggestions (SuggestMgr::ngsuggest) ---

    def _hash(self, word):
        """HashMgr::hash (Hunspell 1.7.1, signed chars, 64-bit unsigned long)"""
        mask = 0xffffffffffffffff
        hv = 0
        n = len(word)
        i = 0
        while i < 4 and i < n:
            c = word[i]
            if c >= 128:
                c |= 0xffffffffffffff00
            hv = ((hv << 8) | c) & mask
            i += 1
        while i < n:
            hv = ((hv << 5) | ((hv >> 27) & 31)) & mask
            c = word[i]
            if c >= 128:
                c |= 0xffffffffffffff00
            hv ^= c
            i += 1
        return hv % self._tablesize

    def _ngram_data(self):
        """the dictionary entries in the order of walk_hashtable with the
        data the ngram search needs (computed once)"""
        data = self._sug_data
        if data is not None:
            return data
        entries = self._all_entries
        order = sorted(range(len(entries)), key=lambda k: (self._hash(entries[k].word), k))
        skip_flags = [self.a_forbiddenword, ONLYUPCASEFLAG, self.nosuggest, self.nongramsuggest, self.onlyincompound]
        by_len = {}
        units_list = []
        info = []
        units = self._units
        for pos, k in enumerate(order):
            e = entries[k]
            fl = e.flags
            skip = bool(fl) and any(f in fl for f in skip_flags)
            if self.utf8:
                nonbmp = bool(_FOUR_BYTE.search(e.word))
                u = u8_u16(e.word)
                clen = 255 if nonbmp else len(u) & 0xff
            else:
                u = units(e.word)
                clen = len(u) & 0xff
            if ONLYUPCASEFLAG in fl:
                initcap = True
            else:
                initcap = self.captype_units(u) == INITCAP
            phon = self._phon.get(e)
            units_list.append(u)
            info.append((e, skip, initcap, phon))
            by_len.setdefault(clen, []).append(pos)
        data = self._sug_data = (units_list, info, by_len)
        return data

    def _ngram_lowered(self, units_list):
        """the lowercase versions of the entries of _ngram_data (cached)"""
        c = getattr(self, '_sug_lowered', None)
        if c is None or c[0] is not units_list:
            lower_tr = self._lower_tr
            c = self._sug_lowered = (units_list, [u.translate(lower_tr) for u in units_list])
        return c[1]

    def _leftcommon(self, su1, su2):
        """SuggestMgr::leftcommonsubstring (UTF-16 units)"""
        l1 = len(su1)
        l2 = len(su2)
        if self.a_complexprefixes:
            if l1 and l2 and su1[l1 - 1] == su2[l2 - 1]:
                return 1
            return 0
        idx = su2[0] if l2 else '\x00'
        otheridx = su1[0] if l1 else '\x00'
        if otheridx != idx and otheridx != idx.translate(self._lower_tr):
            return 0
        i = 1
        while i < l1 and i < l2 and su1[i] == su2[i]:
            i += 1
        return i

    @staticmethod
    def _ngram(n, s1, s2, opt):
        """SuggestMgr::ngram (on UTF-16 units or bytes)"""
        l2 = len(s2)
        if l2 == 0:
            return 0
        l1 = len(s1)
        nscore = 0
        weighted = opt & 8
        for j in range(1, n + 1):
            ns = 0
            for i in range(l1 - j + 1):
                if s1[i:i + j] in s2:
                    ns += 1
                elif weighted:
                    ns -= 1
                    if i == 0 or i == l1 - j:
                        ns -= 1  # side weight
            nscore += ns
            if ns < 2 and not weighted:
                break
        ns = 0
        if opt & 1:  # NGRAM_LONGER_WORSE
            ns = (l2 - l1) - 2
        if opt & 2:  # NGRAM_ANY_MISMATCH
            ns = abs(l2 - l1) - 2
        return nscore - (ns if ns > 0 else 0)

    @staticmethod
    def _lcslen(s, s2):
        m = len(s)
        n = len(s2)
        prev = [0] * (n + 1)
        for i in range(1, m + 1):
            cur = [0] * (n + 1)
            a = s[i - 1]
            for j in range(1, n + 1):
                if a == s2[j - 1]:
                    cur[j] = prev[j - 1] + 1
                elif prev[j] >= cur[j - 1]:
                    cur[j] = prev[j]
                else:
                    cur[j] = cur[j - 1]
            prev = cur
        return prev[n]

    def _commoncharacterpositions(self, s1, s2):
        """returns (num, is_swap); s1, s2 are bytes"""
        if self.utf8:
            if _FOUR_BYTE.search(s1) or _FOUR_BYTE.search(s2):
                su1 = u8_u16(s1)
                su2 = u8_u16(s2)
                if _FOUR_BYTE.search(s1) and len(su1) <= 1 or _FOUR_BYTE.search(s2) and len(su2) <= 1:
                    return 0, 0
            su1 = u8_u16(s1)
            su2 = u8_u16(s2)
            l1 = len(su1)
            l2 = len(su2)
            if l1 <= 0 or l2 <= 0:
                return 0, 0
            if self.a_complexprefixes:
                su2 = su2[:-1] + su2[-1].translate(self._lower_tr)
            else:
                su2 = su2[0].translate(self._lower_tr) + su2[1:]
            num = 0
            diff = 0
            diffpos = [0, 0]
            for i in range(min(l1, l2)):
                if su1[i] == su2[i]:
                    num += 1
                else:
                    if diff < 2:
                        diffpos[diff] = i
                    diff += 1
            is_swap = 1 if (diff == 2 and l1 == l2 and su1[diffpos[0]] == su2[diffpos[1]]
                            and su1[diffpos[1]] == su2[diffpos[0]]) else 0
            return num, is_swap
        t = self._units(s2)
        if self.a_complexprefixes:
            t = t[:-1] + t[-1:].translate(self._lower_tr)
        else:
            t = t.translate(self._lower_tr)
        su1 = self._units(s1)
        num = 0
        diff = 0
        diffpos = [0, 0]
        i = 0
        while i < len(t) and i < len(su1):
            if su1[i] == t[i]:
                num += 1
            else:
                if diff < 2:
                    diffpos[diff] = i
                diff += 1
            i += 1
        is_swap = 1 if (diff == 2 and i == len(su1) and i == len(t) and su1[diffpos[0]] == t[diffpos[1]]
                        and su1[diffpos[1]] == t[diffpos[0]]) else 0
        return num, is_swap

    def _expand_rootword(self, maxn, ts, flags, bad, phon):
        """AffixMgr::expand_rootword: [(word, allow, orig)]"""
        wlst = []
        needaffix = self.needaffix
        oic = self.onlyincompound
        circumfix = self.circumfix
        ap = sorted(flags)
        if len(wlst) < maxn and not (ap and ((needaffix != FLAG_NULL and needaffix in flags)
                                             or (oic != FLAG_NULL and oic in flags))):
            wlst.append((ts, False, None))
            if phon is not None and len(wlst) < maxn:
                wlst.append((phon, False, ts))
        badl = len(bad)

        def cont_ok(e):
            cont = e.cont
            return not (cont and ((needaffix != FLAG_NULL and needaffix in cont)
                                  or (circumfix != FLAG_NULL and circumfix in cont)
                                  or (oic != FLAG_NULL and oic in cont)))
        # handle suffixes
        for f in ap:
            for sptr in self._sflag.get(ord(f) & 0xff, ()):
                if (sptr.aflag == f and (not sptr.appnd or (badl > len(sptr.appnd) and bad.endswith(sptr.appnd)))
                        and cont_ok(sptr)):
                    newword = self._sfx_add(sptr, ts)
                    if newword and len(wlst) < maxn:
                        wlst.append((newword, bool(sptr.opts & AE_XPRODUCT), None))
                        if phon is not None and len(wlst) < maxn:
                            wlst.append((phon + sptr.key[::-1], False, newword))
        n = len(wlst)
        # handle cross products of prefixes and suffixes
        for j in range(1, n):
            if wlst[j][1]:
                for f in ap:
                    for cptr in self._pflag.get(ord(f) & 0xff, ()):
                        if (cptr.aflag == f and (cptr.opts & AE_XPRODUCT)
                                and (not cptr.appnd or (badl > len(cptr.appnd) and bad.startswith(cptr.appnd)))):
                            newword = self._pfx_add(cptr, wlst[j][0])
                            if newword and len(wlst) < maxn:
                                wlst.append((newword, bool(cptr.opts & AE_XPRODUCT), None))
        # now handle pure prefixes
        for f in ap:
            for ptr in self._pflag.get(ord(f) & 0xff, ()):
                if (ptr.aflag == f and (not ptr.appnd or (badl > len(ptr.appnd) and bad.startswith(ptr.appnd)))
                        and cont_ok(ptr)):
                    newword = self._pfx_add(ptr, ts)
                    if newword and len(wlst) < maxn:
                        wlst.append((newword, bool(ptr.opts & AE_XPRODUCT), None))
        return wlst

    def _pfx_add(self, pe, word):
        """PfxEntry::add"""
        n = len(word)
        strip = pe.strip
        if ((n > len(strip) or (n == 0 and self.fullstrip)) and n >= pe.numconds and pe.pfx_test_condition(word)
                and (not strip or word.startswith(strip))):
            return pe.appnd + word[len(strip):]
        return b''

    def _sfx_add(self, se, word):
        """SfxEntry::add"""
        n = len(word)
        strip = se.strip
        if ((n > len(strip) or (n == 0 and self.fullstrip)) and n >= se.numconds
                and se.sfx_test_condition(word, n) and (not strip or word.endswith(strip))):
            return word[:n - len(strip)] + se.appnd
        return b''

    def _ngsuggest(self, wlst, word, captype):
        """SuggestMgr::ngsuggest (without PHONE tables)"""
        MAX_ROOTS = 100
        MAX_WORDS = 100
        MAX_GUESS = 200
        roots = [None] * MAX_ROOTS
        scores = [-100 * i for i in range(MAX_ROOTS)]
        lp = MAX_ROOTS - 1
        low = True  # NGRAM_LOWERING
        if self.a_complexprefixes:
            word = _reverse_utf(word) if self.utf8 else word[::-1]
        nc = len(word)
        nonbmp = False
        utf8 = self.utf8
        if utf8 and _FOUR_BYTE.search(word):
            # character based ngram suggestion for words with non-BMP characters
            utf8 = False
            nonbmp = True
            low = False
        if utf8:
            w_word = u8_u16(word)
        else:
            w_word = word.decode('latin-1')
        n = len(w_word) if utf8 else nc
        lower_tr = self._lower_tr
        units_list, info, by_len = self._ngram_data()
        ph = None
        de = self.langnum == LANG_de
        # the entries to check, in the order of the hash table
        if nonbmp:
            positions = range(len(info))
        else:
            positions = []
            for clen in range(n - 4, n + 5):
                positions.extend(by_len.get(clen, ()))
            positions.sort()
        g1 = [w_word[i:i + 1] for i in range(n)]
        g2 = [w_word[i:i + 2] for i in range(n - 1)]
        g3 = [w_word[i:i + 3] for i in range(n - 2)]
        first = w_word[:1]
        complexprefixes = self.a_complexprefixes
        if self._deadline is not None:
            # with a time limit: the scan of the dictionary stops at the deadline (or half the limit after its start)
            ng_deadline = max(self._deadline, perf_counter() + self._time_limit / 2)
            positions = _until(positions, ng_deadline)
        if _speedups is not None and not complexprefixes and not nonbmp:
            # the loop below in C
            lowered = self._ngram_lowered(units_list)

            def phon_score(pos, sc):
                phon = info[pos][3]
                fu = u8_u16(phon) if utf8 else phon.decode('latin-1')
                lc2 = self._leftcommon(w_word, fu) if utf8 else self._leftcommon_8bit(word, phon)
                if low:
                    fu = fu.translate(lower_tr)
                sc2 = self._ngram(3, w_word, fu, 1) + lc2
                return sc2 if sc2 > sc else sc

            lp = _speedups.ng_scan(positions, info, units_list, lowered, w_word, g1, g2, g3,
                                   captype == NOCAP and ph is None and not de, lower_tr, roots, scores, lp, phon_score)
            positions = ()
        for pos in positions:
            e, skip, initcap, phon = info[pos]
            if skip or (captype == NOCAP and initcap and ph is None and not de and phon is None):
                continue
            f = units_list[pos]
            if not utf8:
                f = e.word.decode('latin-1')
                leftcommon = self._leftcommon_8bit(word, e.word)
            else:
                # leftcommonsubstring
                if complexprefixes:
                    leftcommon = self._leftcommon(w_word, f)
                else:
                    idx = f[:1]
                    if first != idx and first != idx.translate(lower_tr):
                        leftcommon = 0
                    else:
                        i = 1
                        lf = len(f)
                        while i < n and i < lf and w_word[i] == f[i]:
                            i += 1
                        leftcommon = i
            fl = f.translate(lower_tr) if low else f
            l2 = len(fl)
            if l2 == 0:
                sc = leftcommon
            else:
                ns = sum(map(fl.__contains__, g1))
                nscore = ns
                if ns >= 2:
                    ns = sum(map(fl.__contains__, g2))
                    nscore += ns
                    if ns >= 2:
                        nscore += sum(map(fl.__contains__, g3))
                pen = l2 - n - 2
                sc = nscore - (pen if pen > 0 else 0) + leftcommon
            if phon is not None:
                fu = u8_u16(phon) if utf8 else phon.decode('latin-1')
                lc2 = self._leftcommon(w_word, fu) if utf8 else self._leftcommon_8bit(word, phon)
                if low:
                    fu = fu.translate(lower_tr)
                sc2 = self._ngram(3, w_word, fu, 1) + lc2
                if sc2 > sc:
                    sc = sc2
            if sc > scores[lp]:
                scores[lp] = sc
                roots[lp] = e
                lval = sc
                for j in range(MAX_ROOTS):
                    if scores[j] < lval:
                        lp = j
                        lval = scores[j]
        # find minimum threshold for a passable suggestion
        thresh = 0
        for sp in range(1, 4):
            mw = list(w_word)
            for k in range(sp, n, 4):
                mw[k] = '*'
            mw = ''.join(mw)
            if low:
                mw = mw.translate(lower_tr)
            thresh += self._ngram(n, w_word, mw, 2)
        thresh = int(thresh / 3)
        thresh -= 1
        # now expand affixes on each of these root words and use length adjusted ngram scores
        guess = [None] * MAX_GUESS
        guessorig = [None] * MAX_GUESS
        gscore = [-100 * i for i in range(MAX_GUESS)]
        lp = MAX_GUESS - 1
        for i in range(MAX_ROOTS):
            rp = roots[i]
            if rp is None:
                continue
            field = self._phon.get(rp)
            for gw, _allow, gorig in self._expand_rootword(MAX_WORDS, rp.word, rp.flags, word, field):
                if utf8:
                    w_f = u8_u16(gw)
                    leftcommon = self._leftcommon(w_word, w_f)
                    if low:
                        w_f = w_f.translate(lower_tr)
                    sc = self._ngram(n, w_word, w_f, 2) + leftcommon
                else:
                    f = gw.decode('latin-1')
                    leftcommon = 0 if nonbmp else self._leftcommon_8bit(word, gw)
                    if low:
                        f = f.translate(lower_tr)
                    sc = self._ngram(n, w_word, f, 2) + leftcommon
                if sc > thresh and sc > gscore[lp]:
                    gscore[lp] = sc
                    guess[lp] = gw
                    guessorig[lp] = gorig
                    lval = sc
                    for j in range(MAX_GUESS):
                        if gscore[j] < lval:
                            lp = j
                            lval = gscore[j]
        _bubblesort(guess, guessorig, gscore)
        # weight suggestions with a similarity index, based on the longest common subsequent algorithm
        fact = 1.0
        if self.maxdiff >= 0:
            fact = (10.0 - self.maxdiff) / 5.0
        for i in range(MAX_GUESS):
            if guess[i] is None:
                continue
            if utf8:
                w_gl = u8_u16(guess[i]).translate(lower_tr)
                glen = len(u8_u16(guess[i]))
                if _FOUR_BYTE.search(guess[i]):
                    glen = -1
                gl = u16_u8(w_gl)
                lcs = self._lcslen(w_word, u8_u16(gl))
            else:
                gl = guess[i]
                if not nonbmp:
                    gl = self._from_units(self._units(gl).translate(lower_tr))
                glen = len(guess[i])
                w_gl = gl.decode('latin-1')
                lcs = self._lcslen(word, gl)
            # same characters with different casing
            if n == glen and n == lcs:
                gscore[i] += 2000
                break
            # using 2-gram instead of 3, and other weightening
            if utf8:
                w_gl = u8_u16(gl)
            re_ = self._ngram(2, w_word, w_gl, 2 | 8)
            if low:
                re_ += self._ngram(2, w_gl, w_word.translate(lower_tr), 2 | 8)
            else:
                re_ += self._ngram(2, w_gl, w_word, 2 | 8)
            ngram_score = self._ngram(4, w_word, w_gl, 2)
            if utf8:
                leftcommon_score = self._leftcommon(w_word, w_gl)
            else:
                leftcommon_score = 0 if nonbmp else self._leftcommon_8bit(word, gl)
            if nonbmp:
                ccp, is_swap = 0, 0
            else:
                ccp, is_swap = self._commoncharacterpositions(word, gl)
            gscore[i] = (2 * lcs - abs(n - glen) + leftcommon_score + (1 if ccp else 0) + (10 if is_swap else 0)
                         + ngram_score + re_ + (-1000 if re_ < (n + glen) * fact else 0))
        _bubblesort(guess, guessorig, gscore)
        # copy over
        oldns = len(wlst)
        same = False
        for i in range(MAX_GUESS):
            if guess[i] is None:
                continue
            if len(wlst) < oldns + self.s_maxngramsugs and len(wlst) < self.maxsug and (not same or gscore[i] > 1000):
                unique = True
                # leave only excellent suggestions, if exists
                if gscore[i] > 1000:
                    same = True
                elif gscore[i] < -100:
                    same = True
                    # keep the best ngram suggestions, unless in ONLYMAXDIFF mode
                    if len(wlst) > oldns or self.onlymaxdiff:
                        continue
                for prev in wlst:
                    # don't suggest previous suggestions or a previous suggestion with prefixes or affixes
                    if ((guessorig[i] is None and prev in guess[i])
                            or (guessorig[i] is not None and prev in guessorig[i])
                            or not self._sug_checkword(guess[i], 0)):
                        unique = False
                        break
                if unique:
                    wlst.append(guessorig[i] if guessorig[i] is not None else guess[i])

    def _leftcommon_8bit(self, s1, s2):
        """SuggestMgr::leftcommonsubstring for 8-bit encodings (bytes)"""
        if self.a_complexprefixes:
            l1 = len(s1)
            l2 = len(s2)
            if l1 <= l2 and l1 and s2[l1 - 1] == s2[l2 - 1]:
                return 1
            return 0
        if self.utf8:
            return 0  # no csconv for UTF-8 dictionaries (non-BMP words)
        a = s1[0] if s1 else 0
        b = s2[0] if s2 else 0
        if a != b and a != self._lower_map.get(b, b):
            return 0
        i = 1
        while i < len(s1) and i < len(s2) and s1[i] == s2[i]:
            i += 1
        return i

    # --- HunspellImpl::suggest ---

    def suggest(self, word, time_limit=None):
        """Hunspell::suggest(word): the suggestions for a misspelled word
        (like Hunspell_suggest; Hunspell's CPU time limits are not
        emulated, the search always completes).

        time_limit (seconds) bounds the search (approximately; the result
        may then differ from Hunspell's): the MAP suggestions stop after a
        quarter of it (like Hunspell's timer), the other phases and the
        compound suggestions after the limit, the ngram search after the
        limit or at least half the limit after its start."""
        b = self._encode(word)
        with self._lock:
            if time_limit is not None:
                self._time_limit = time_limit
                self._deadline = perf_counter() + time_limit
            try:
                return [s.decode('utf-8', 'replace') if self.utf8 else s.decode(self._codec, 'replace')
                        for s in self._hsuggest(b)]
            finally:
                self._deadline = self._time_limit = None

    def _mkinitcap_b(self, b):
        u = self._units(b)
        return self._from_units(u[:1].translate(self._upper_tr) + u[1:])

    def _mkallcap_b(self, b):
        return self._from_units(self._units(b).translate(self._upper_tr))

    def _hsuggest(self, word):
        """HunspellImpl::suggest"""
        slst, capwords, abbv, captype = self._suggest_internal(word)
        if self.a_complexprefixes:
            slst = [(_reverse_utf(s) if self.utf8 else s[::-1]) for s in slst]
        if capwords:
            slst = [self._mkinitcap_b(s) for s in slst]
        if abbv and self.sugswithdots:
            slst = [s + word[len(word) - abbv:] for s in slst]
        # remove bad capitalized and forbidden forms
        if self.keepcase != FLAG_NULL or self.a_forbiddenword != FLAG_NULL:
            if captype in (INITCAP, ALLCAP):
                kept = []
                for s in slst:
                    if b' ' not in s and not self._spell(s, []):
                        u = self._units(s).translate(self._lower_tr)
                        s2 = self._from_units(u)
                        if self._spell(s2, []):
                            kept.append(s2)
                        else:
                            s2 = self._from_units(u[:1].translate(self._upper_tr) + u[1:])
                            if self._spell(s2, []):
                                kept.append(s2)
                    else:
                        kept.append(s)
                slst = kept
        # remove duplications
        out = []
        for s in slst:
            if s not in out:
                out.append(s)
        # output conversion
        if self.oconvtable is not None:
            out = [(self.oconvtable.conv(s) or s) for s in out]
        return out

    def _suggest_internal(self, word):
        captype = NOCAP
        abbv = 0
        capwords = False
        slst = []
        onlycmpdsug = [0]
        if word.startswith(SPELL_XML[:len(SPELL_XML) - 2]):
            return slst, capwords, abbv, captype  # (XML API not supported)
        if len(word) >= (MAXWORDUTF8LEN if self.utf8 else MAXWORDLEN):
            return slst, capwords, abbv, captype
        if self.iconvtable is not None:
            converted = self.iconvtable.conv(word)
            if converted is not None:
                word = converted
        scw, sunicw, captype, abbv = self._cleanword2(word)
        if not scw:
            return slst, capwords, abbv, captype
        wl = len(scw)
        good = False
        sm = self._sm_suggest
        # check capitalized form for FORCEUCASE
        if captype == NOCAP and self.forceucase != FLAG_NULL:
            info = [SPELL_ORIGCAP]
            if self._checkword(scw, info) is not None:
                slst.append(self._mkinitcap_b(scw))
                return slst, capwords, abbv, captype
        if captype == NOCAP:
            good |= sm(slst, scw, onlycmpdsug)
            if abbv:
                good |= sm(slst, scw + b'.', onlycmpdsug)
        elif captype == INITCAP:
            capwords = True
            good |= sm(slst, scw, onlycmpdsug)
            wspace, sunicw = self._mkallsmall2(sunicw)
            good |= sm(slst, wspace, onlycmpdsug)
        elif captype in (HUHINITCAP, HUHCAP):
            if captype == HUHINITCAP:
                capwords = True
            good |= sm(slst, scw, onlycmpdsug)
            # something.The -> something. The
            dot_pos = scw.find(b'.')
            if dot_pos != -1:
                postdot = scw[dot_pos + 1:]
                if self.captype_units(self._units(postdot)) == INITCAP:
                    slst.insert(0, scw[:dot_pos + 1] + b' ' + scw[dot_pos + 1:])
            if captype == HUHINITCAP:
                # TheOpenOffice.org -> The OpenOffice.org
                sunicw = sunicw[:1].translate(self._lower_tr) + sunicw[1:]
                wspace = self._from_units(sunicw)
                good |= sm(slst, wspace, onlycmpdsug)
            wspace, sunicw = self._mkallsmall2(sunicw)
            if self._spell(wspace, []):
                slst.insert(0, wspace)
            prevns = len(slst)
            good |= sm(slst, wspace, onlycmpdsug)
            if captype == HUHINITCAP:
                wspace, sunicw = self._mkinitcap2(sunicw)
                if self._spell(wspace, []):
                    slst.insert(0, wspace)
                good |= sm(slst, wspace, onlycmpdsug)
            # aNew -> "a New" (instead of "a new")
            j = prevns
            while j < len(slst):
                s = slst[j]
                sp = s.find(b' ')
                if sp != -1:
                    second = s[sp + 1:]
                    slen = len(second)
                    if slen < wl and scw[wl - slen:] != second:
                        first = s[:sp + 1]
                        second = self._mkinitcap_b(second)
                        del slst[j]
                        slst.insert(0, first + second)
                j += 1
        elif captype == ALLCAP:
            wspace, sunicw = self._mkallsmall2(sunicw)
            good |= sm(slst, wspace, onlycmpdsug)
            if self.keepcase != FLAG_NULL and self._spell(wspace, []):
                slst.insert(0, wspace)
            wspace, sunicw = self._mkinitcap2(sunicw)
            good |= sm(slst, wspace, onlycmpdsug)
            for j in range(len(slst)):
                s = self._mkallcap_b(slst[j])
                if self.checksharps:
                    s = s.replace(b'\xc3\x9f' if self.utf8 else b'\xdf', b'SS')
                slst[j] = s
        # try ngram approach since found nothing good suggestion
        if not good and (not slst or onlycmpdsug[0]) and self.maxngramsugs != 0:
            if captype == NOCAP:
                self._ngsuggest(slst, scw, NOCAP)
            elif captype in (HUHINITCAP, HUHCAP):
                if captype == HUHINITCAP:
                    capwords = True
                wspace = self._from_units(sunicw.translate(self._lower_tr))
                self._ngsuggest(slst, wspace, HUHCAP)
            elif captype == INITCAP:
                capwords = True
                wspace = self._from_units(sunicw.translate(self._lower_tr))
                self._ngsuggest(slst, wspace, INITCAP)
            elif captype == ALLCAP:
                wspace = self._from_units(sunicw.translate(self._lower_tr))
                oldns = len(slst)
                self._ngsuggest(slst, wspace, ALLCAP)
                for j in range(oldns, len(slst)):
                    slst[j] = self._mkallcap_b(slst[j])
        # try dash suggestion (Afo-American -> Afro-American)
        dash_pos = scw.find(b'-')
        if dash_pos != -1:
            nodashsug = not any(b'-' in s for s in slst)
            prev_pos = 0
            last = False
            while not good and nodashsug and not last:
                if dash_pos == len(scw):
                    last = True
                chunk = scw[prev_pos:dash_pos]
                if not self._spell(chunk, []):
                    nlst = self._hsuggest(chunk)
                    for s in reversed(nlst):
                        wspace = scw[:prev_pos] + s
                        if not last:
                            wspace += b'-' + scw[dash_pos + 1:]
                        info = [0]
                        if self.a_forbiddenword != FLAG_NULL:
                            self._checkword(wspace, info)
                        if not (info[0] & SPELL_FORBIDDEN):
                            slst.insert(0, wspace)
                    nodashsug = False
                if not last:
                    prev_pos = dash_pos + 1
                    dash_pos = scw.find(b'-', prev_pos)
                if dash_pos == -1:
                    dash_pos = len(scw)
        return slst, capwords, abbv, captype


def _bubblesort(rword, rword2, rsc):
    """SuggestMgr::bubblesort: sort in decreasing order of score (stable)"""
    n = len(rsc)
    m = 1
    while m < n:
        j = m
        while j > 0:
            if rsc[j - 1] < rsc[j]:
                rsc[j - 1], rsc[j] = rsc[j], rsc[j - 1]
                rword[j - 1], rword[j] = rword[j], rword[j - 1]
                if rword2 is not None:
                    rword2[j - 1], rword2[j] = rword2[j], rword2[j - 1]
                j -= 1
            else:
                break
        m += 1


def _is_subset_keys(s1, s2):
    """AffixMgr::isSubset for two affix keys"""
    if 46 not in s1:  # no '.' (any character): a prefix test
        return s2.startswith(s1)
    n2 = len(s2)
    for k, c in enumerate(s1):
        if c != 46 and (k >= n2 or c != s2[k]):
            return False
    return True


def _reverse_utf(b):
    """reverseword_utf: reverse the characters of UTF-8 bytes"""
    return u16_u8(u8_u16(b)[::-1])


class _TimeLimit(Exception):
    pass


def _until(items, deadline):
    """the items until the deadline (perf_counter) has passed (checked every 256 items)"""
    for i, x in enumerate(items):
        if not (i & 255) and perf_counter() > deadline:
            return
        yield x


def _truncate_bad(u, b):
    """a KEY/TRY string with characters outside the BMP is not used (u8_u16 fails)"""
    return '' if _FOUR_BYTE.search(b) else u


_PY_ENCODINGS = {'microsoft-cp1251': 'cp1251', 'TIS620-2533': 'tis-620', 'ISCII-DEVANAGARI': 'latin-1'}


def _python_encoding(enc):
    e = enc.decode('latin-1')
    e = _PY_ENCODINGS.get(e, e)
    try:
        import codecs
        codecs.lookup(e)
        return e
    except LookupError:
        return 'latin-1'


def _8bit_case_maps(enc, langnum):
    """the case tables (csconv) of an 8-bit encoding, as maps of the
    latin-1 characters that stand for the bytes"""
    upper_u, lower_u = _case_maps(langnum)
    upper = {}
    lower = {}
    for i in range(256):
        try:
            ch = bytes([i]).decode(enc)
        except UnicodeDecodeError:
            continue
        if len(ch) != 1:
            continue
        for src, dst in ((upper_u, upper), (lower_u, lower)):
            c = src.get(ord(ch))
            if c is not None:
                try:
                    b = chr(c).encode(enc)
                except UnicodeEncodeError:
                    continue
                if len(b) == 1 and b[0] != i:
                    dst[i] = b[0]
    return upper, lower


class _RepList:
    """RepList (ICONV/OCONV tables)"""

    def __init__(self):
        self.dat = []  # [pattern, [out0..out3]] sorted by pattern

    def _find(self, word, i):
        p1 = 0
        p2 = len(self.dat) - 1
        ret = -1
        while p1 <= p2:
            m = (p1 + p2) >> 1
            pat = self.dat[m][0]
            seg = word[i:i + len(pat)]
            # strncmp(word, pattern, len(pattern))
            if seg < pat:
                c = -1
            elif seg > pat:
                c = 1
            else:
                c = 0
            if c < 0:
                p2 = m - 1
            elif c > 0:
                p1 = m + 1
            else:
                ret = m
                p1 = m + 1
        return ret

    def add(self, pat1, pat2):
        rtype = 0
        if pat1.startswith(b'_'):
            pat1 = pat1[1:]
            rtype = 1
        if pat1.endswith(b'_'):
            rtype += 2
            pat1 = pat1[:-1]
        pat1 = pat1.replace(b'_', b' ')
        m = self._find(pat1, 0)
        if m >= 0 and self.dat[m][0] == pat1:
            self.dat[m][1][rtype] = pat2.replace(b'_', b' ')
            return
        entry = [pat1, [b'', b'', b'', b'']]
        entry[1][rtype] = pat2.replace(b'_', b' ')
        self.dat.append(entry)
        i = len(self.dat) - 1
        while i > 0 and pat1 < self.dat[i - 1][0]:
            self.dat[i] = self.dat[i - 1]
            i -= 1
        self.dat[i] = entry

    def _replace(self, wordlen, ind, atstart):
        rtype = 1 if atstart else 0
        if wordlen == len(self.dat[ind][0]):
            rtype = 3 if atstart else 2
        outs = self.dat[ind][1]
        while rtype and not outs[rtype]:
            rtype = 0 if (rtype == 2 and not atstart) else rtype - 1
        return outs[rtype]

    def conv(self, word):
        """the converted word, None if nothing changed"""
        dest = bytearray()
        change = False
        i = 0
        n = len(word)
        while i < n:
            m = self._find(word, i)
            if m < 0:
                dest.append(word[i])
                i += 1
                continue
            rep = self._replace(n - i, m, i == 0)
            if not rep:
                dest.append(word[i])
                i += 1
                continue
            dest += rep
            if self.dat[m][0]:
                i += len(self.dat[m][0]) - 1
            change = True
            i += 1
        return bytes(dest) if change else None


_cache = {}
_cache_lock = threading.Lock()


def get_dictionary(dic_path, aff_path):
    """The Hunspell dictionary for a .dic and an .aff file, cached per pair
    of paths (Java: Hunspell.getDictionary)."""
    key = (os.path.abspath(dic_path), os.path.abspath(aff_path))
    with _cache_lock:
        h = _cache.get(key)
        if h is None:
            h = _cache[key] = Hunspell(dic_path, aff_path)
        return h
