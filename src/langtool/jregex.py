"""Translation of Java regular expressions (java.util.regex) to the syntax of
the Python ``regex`` module (version 1 behaviour).

LanguageTool rules are written using Java regex syntax and semantics. The
``regex`` module in V1 mode is very close to Java (scoped inline flags,
nested character classes, ``&&`` class intersection, possessive quantifiers,
atomic groups, variable length look-behind), so the translation is mostly a
matter of mapping a handful of constructs whose meaning differs:

* ``\\w``, ``\\d``, ``\\s``, ``\\b`` and the POSIX ``\\p{...}`` classes are
  ASCII-only in Java unless ``UNICODE_CHARACTER_CLASS`` is set.
* Java specific property names (``\\p{javaLowerCase}``, ``\\p{IsLetter}``, ...).
* ``\\Q...\\E`` quoting, ``\\h``, ``\\v``, ``\\R``, ``\\z``, ``\\Z``, ``\\e``.
* ``.`` does not match any line terminator in Java.
* Java uses simple case folding, ``regex`` V1 full case folding by default.
"""

import threading

import regex

__all__ = ['translate', 'compile', 'JavaRegexError', 'IGNORECASE']

IGNORECASE = 1
UNICODE_CHARACTER_CLASS = 2


class JavaRegexError(ValueError):
    pass


_ASCII_W = 'a-zA-Z0-9_'
_ASCII_D = '0-9'
_ASCII_S = ' \\t\\n\\x0B\\f\\r'
_U_W = '\\p{Alphabetic}\\p{M}\\p{Nd}\\p{Pc}\\u200c\\u200d'
_U_D = '\\p{Nd}'
_U_S = '\\p{White_Space}'
_H = ' \\t\\xA0\\u1680\\u180e\\u2000-\\u200a\\u202f\\u205f\\u3000'
_V = '\\n\\x0B\\f\\r\\x85\\u2028\\u2029'
_LINE_TERMINATORS = '\\n\\r\\x85\\u2028\\u2029'

# POSIX classes: (ascii set content, unicode set content)
_POSIX = {
    'lower': ('a-z', '\\p{Lowercase}'),
    'upper': ('A-Z', '\\p{Uppercase}'),
    'ascii': ('\\x00-\\x7F', '\\x00-\\x7F'),
    'alpha': ('a-zA-Z', '\\p{Alphabetic}'),
    'digit': ('0-9', '\\p{Nd}'),
    'alnum': ('a-zA-Z0-9', '\\p{Alphabetic}\\p{Nd}'),
    'punct': ('!-\\/:-@\\[-`{-~', '\\p{P}'),
    'graph': ('!-~', '[^\\p{White_Space}\\p{Cc}\\p{Cs}\\p{Cn}]'),
    'print': (' -~', '[[^\\p{White_Space}\\p{Cc}\\p{Cs}\\p{Cn}]\\p{Zs}\\t--\\p{Cc}]'),
    'blank': (' \\t', '\\p{Zs}\\t'),
    'cntrl': ('\\x00-\\x1F\\x7F', '\\p{Cc}'),
    'xdigit': ('0-9a-fA-F', '\\p{Nd}\\p{Hex_Digit}'),
    'space': (' \\t\\n\\x0B\\f\\r', '\\p{White_Space}'),
}

_JAVA_PROPS = {
    'javalowercase': '\\p{Lowercase}',
    'javauppercase': '\\p{Uppercase}',
    'javaletter': '\\p{L}',
    'javadigit': '\\p{Nd}',
    'javaletterordigit': '\\p{L}\\p{Nd}',
    'javawhitespace': '[\\t\\n\\x0B\\f\\r\\x1C-\\x1F\\p{Zs}\\p{Zl}\\p{Zp}--[\\xA0\\u2007\\u202F]]',
    'javaspacechar': '\\p{Z}',
    'javaalphabetic': '\\p{Alphabetic}',
    'javaideographic': '\\p{Ideographic}',
    'javatitlecase': '\\p{Lt}',
    'javamirrored': '\\p{Bidi_Mirrored}',
    'javaisocontrol': '\\x00-\\x1F\\x7F-\\x9F',
    'javadefined': '\\P{Cn}',
    'javaidentifierignorable': '\\x00-\\x08\\x0E-\\x1B\\x7F-\\x9F\\p{Cf}',
    'javajavaidentifierstart': '\\p{L}\\p{Nl}\\p{Sc}\\p{Pc}',
    'javajavaidentifierpart': '\\p{L}\\p{Nl}\\p{Sc}\\p{Pc}\\p{Nd}\\p{Mn}\\p{Mc}\\x00-\\x08\\x0E-\\x1B\\x7F-\\x9F\\p{Cf}',
    'javaunicodeidentifierstart': '\\p{ID_Start}',
    'javaunicodeidentifierpart': '\\p{ID_Continue}\\x00-\\x08\\x0E-\\x1B\\x7F-\\x9F\\p{Cf}',
}

_BINARY_PROPS = {
    'letter': '\\p{L}',
    'digit': '\\p{Nd}',
    'punctuation': '\\p{P}',
    'control': '\\p{Cc}',
    'titlecase': '\\p{Lt}',
    'assigned': '\\P{Cn}',
    'hexdigit': '\\p{Hex_Digit}',
    'hex_digit': '\\p{Hex_Digit}',
    'whitespace': '\\p{White_Space}',
    'white_space': '\\p{White_Space}',
    'alphabetic': '\\p{Alphabetic}',
    'lowercase': '\\p{Lowercase}',
    'uppercase': '\\p{Uppercase}',
    'ideographic': '\\p{Ideographic}',
    'noncharactercodepoint': '\\p{Noncharacter_Code_Point}',
    'noncharacter_code_point': '\\p{Noncharacter_Code_Point}',
    'joincontrol': '\\p{Join_Control}',
    'join_control': '\\p{Join_Control}',
    'emoji': '\\p{Emoji}',
    'emoji_presentation': '\\p{Emoji_Presentation}',
    'emoji_modifier': '\\p{Emoji_Modifier}',
    'emoji_modifier_base': '\\p{Emoji_Modifier_Base}',
    'emoji_component': '\\p{Emoji_Component}',
    'extended_pictographic': '\\p{Extended_Pictographic}',
}

_valid_prop_cache = {}


def _valid_regex_prop(name):
    r = _valid_prop_cache.get(name)
    if r is None:
        try:
            regex.compile('\\p{%s}' % name)
            r = True
        except Exception:
            r = False
        _valid_prop_cache[name] = r
    return r


_GENERAL_CATEGORIES = frozenset(
    'Cn Lu Ll Lt Lm Lo Mn Me Mc Nd Nl No Zs Zl Zp Cc Cf Co Cs Pd Ps Pe Pc Po Sm Sc Sk So Pi Pf '
    'L M N Z C P S LC LD L1 all'.split())

_POSIX_NAMES = ('Lower', 'Upper', 'ASCII', 'Alpha', 'Digit', 'Alnum', 'Punct', 'Graph', 'Print', 'Blank',
                'Cntrl', 'XDigit', 'Space')

_JAVA_PROP_NAMES = {k.lower(): k for k in (
    'javaLowerCase', 'javaUpperCase', 'javaLetter', 'javaDigit', 'javaLetterOrDigit', 'javaWhitespace',
    'javaSpaceChar', 'javaAlphabetic', 'javaIdeographic', 'javaTitleCase', 'javaMirrored', 'javaISOControl',
    'javaDefined', 'javaIdentifierIgnorable', 'javaJavaIdentifierStart', 'javaJavaIdentifierPart',
    'javaUnicodeIdentifierStart', 'javaUnicodeIdentifierPart')}


def _gc_set(name):
    if name == 'LC':
        return '\\p{Lu}\\p{Ll}\\p{Lt}'
    if name == 'LD':
        return '\\p{L}\\p{Nd}'
    if name == 'L1':
        return '\\x00-\\xFF'
    if name == 'all':
        return '\\x00-\\U0010FFFF'
    return '\\p{%s}' % name


def _property_set(name, unicode_classes):
    """Return the content of a V1 set (usable between [ and ]) matching the
    given Java property name. Names are validated like java.util.regex does
    (case sensitive, 'Is'/'In' prefixes, key=value forms)."""
    n = name
    if '=' in n:
        key, val = n.split('=', 1)
        lkey = key.lower()
        if lkey in ('gc', 'general_category'):
            if val in _GENERAL_CATEGORIES:
                return _gc_set(val)
            raise JavaRegexError('Unknown general category: %s' % name)
        if lkey in ('sc', 'script'):
            if _valid_regex_prop('Script=' + val):
                return '\\p{Script=%s}' % val
            raise JavaRegexError('Unknown script: %s' % name)
        if lkey in ('blk', 'block'):
            if _valid_regex_prop('Block=' + val):
                return '\\p{Block=%s}' % val
            raise JavaRegexError('Unknown block: %s' % name)
        raise JavaRegexError('Unknown Unicode property: %s' % name)
    if n.startswith('Is'):
        rest = n[2:]
        lr = rest.lower()
        if lr in _BINARY_PROPS:
            return _BINARY_PROPS[lr]
        if lr in _POSIX:
            return _POSIX[lr][1 if unicode_classes else 0]
        if rest in _GENERAL_CATEGORIES:
            return _gc_set(rest)
        if rest and _valid_regex_prop('Script=' + rest):
            return '\\p{Script=%s}' % rest
        raise JavaRegexError('Unknown property: %s' % name)
    if n.startswith('In'):
        rest = n[2:]
        if rest and _valid_regex_prop('Block=' + rest):
            return '\\p{Block=%s}' % rest
        raise JavaRegexError('Unknown block: %s' % name)
    if n in _POSIX_NAMES:
        return _POSIX[n.lower()][1 if unicode_classes else 0]
    if n.startswith('java'):
        low = n.lower()
        if _JAVA_PROP_NAMES.get(low) == n:
            return _JAVA_PROPS[low]
        raise JavaRegexError('Unknown Java property: %s' % name)
    if n in _GENERAL_CATEGORIES:
        return _gc_set(n)
    raise JavaRegexError('Unknown property: %s' % name)


def _escape_char(c):
    """Escape a literal character for use in a V1 pattern (in or out of a
    set)."""
    if c.isalnum() or c == '_' or ord(c) > 127:
        return c
    if c == '\n':
        return '\\n'
    if c == '\t':
        return '\\t'
    if c == '\r':
        return '\\r'
    if c == '\f':
        return '\\f'
    if c == '\x0b':
        return '\\x0B'
    if c == ' ':
        return '\\ '
    if ord(c) < 32:
        return '\\x%02x' % ord(c)
    return '\\' + c


def _count_groups(p):
    count = 0
    i, n = 0, len(p)
    depth = 0
    while i < n:
        c = p[i]
        if c == '\\':
            if p.startswith('Q', i + 1):
                j = p.find('\\E', i + 2)
                i = n if j < 0 else j + 2
                continue
            i += 2
            continue
        if depth:
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
        elif c == '[':
            depth = 1
            if p.startswith('^]', i + 1):
                i += 2
            elif p.startswith(']', i + 1):
                i += 1
        elif c == '(':
            if not p.startswith('?', i + 1) or (p.startswith('?<', i + 1) and p[i + 3:i + 4] not in ('=', '!')):
                count += 1
        i += 1
    return count


_CURLY = regex.compile(r'\{(\d+)(?:(,)(\d*))?\}')
_CURLY_X = regex.compile(r'\{(\d+)\s*(?:(,)\s*(\d*)\s*)?\}')
_GROUP_NAME = regex.compile(r'[A-Za-z][A-Za-z0-9]*\Z')
_MAX_REPEAT = 2 ** 31 - 1
_BIG_REPEAT = 100000

# special case of Java's CASE_INSENSITIVE|UNICODE_CASE matching:
# Character.toLowerCase(Character.toUpperCase(c)) is 'i' for all of these
_DOTTED_I = 'iIıİ'

# Java line terminators
_LT = '\\n\\r\\x85\\u2028\\u2029'
_DOLLAR = '(?=(?:\\r\\n|(?<!\\r)\\n|[\\r\\x85\\u2028\\u2029])?\\Z)'
_DOLLAR_UNIX = '(?=\\n?\\Z)'
_DOLLAR_M = '(?=\\r\\n|(?<!\\r)\\n|[\\r\\x85\\u2028\\u2029]|\\Z)'
_DOLLAR_M_UNIX = '(?=\\n|\\Z)'
_CARET_M = '(?:\\A|(?<=[\\n\\x85\\u2028\\u2029])|(?<=\\r)(?!\\n))(?!\\Z)'
_CARET_M_UNIX = '(?:\\A|(?<=\\n))(?!\\Z)'


def _ascii_swapcase_ranges(lo, hi):
    """Set fragments for the other case of the ASCII letters in [lo, hi]."""
    out = []
    for a, b in ((0x41, 0x5A), (0x61, 0x7A)):
        s, e = max(lo, a), min(hi, b)
        if s <= e:
            d = 32 if a == 0x41 else -32
            out.append('%s-%s' % (chr(s + d), chr(e + d)))
    return out


def _is_cased_set(val):
    """Whether a property set depends on the letter case, Java matches those
    case insensitively (like \\p{Lu} matching 'a' with CASE_INSENSITIVE)
    even without UNICODE_CASE."""
    return any(x in val for x in ('\\p{Lu', '\\p{Ll', '\\p{Lt', 'Lowercase', 'Uppercase'))


class _Flags:
    """The java.util.regex flags in effect at some point of the pattern."""
    __slots__ = ('ci', 'ucase', 'uclass', 'dotall', 'unix', 'multi', 'comments')

    def __init__(self):
        self.ci = self.ucase = self.uclass = self.dotall = self.unix = self.multi = self.comments = False

    def copy(self):
        f = _Flags.__new__(_Flags)
        for k in _Flags.__slots__:
            setattr(f, k, getattr(self, k))
        return f


class _Translator:

    def __init__(self, pattern, flags):
        self.p = pattern
        self.n = len(pattern)
        self.i = 0
        f = self.f = _Flags()
        if flags & IGNORECASE:
            f.ci = f.ucase = True
        if flags & UNICODE_CHARACTER_CLASS:
            f.uclass = f.ucase = True
        # whether the regex module currently matches case insensitively
        self.r_ci = bool(flags & IGNORECASE)
        self.out = []
        self.group_count = _count_groups(pattern)
        self.group_names = set()
        self._class_depth = 0

    # flag shortcuts
    @property
    def unicode_classes(self):
        return self.f.uclass

    @property
    def aci(self):
        """ASCII-only case insensitivity (CASE_INSENSITIVE without
        UNICODE_CASE), done by expanding the letters."""
        return self.f.ci and not self.f.ucase

    @property
    def uci(self):
        return self.f.ci and self.f.ucase

    def error(self, msg):
        raise JavaRegexError('%s at position %d in: %r' % (msg, self.i, self.p))

    def peek(self, k=0):
        j = self.i + k
        return self.p[j] if j < self.n else ''

    def skip_comments(self):
        """In COMMENTS mode skip whitespace and #-comments."""
        if not self.f.comments:
            return
        while self.i < self.n:
            c = self.p[self.i]
            if c in ' \t\n\r\x0b\f':
                self.i += 1
            elif c == '#':
                j = self.p.find('\n', self.i)
                self.i = self.n if j < 0 else j + 1
            else:
                break

    # ---- escapes ----

    def read_hex(self, count):
        s = self.p[self.i:self.i + count]
        if len(s) != count:
            self.error('Bad hex escape')
        try:
            v = int(s, 16)
        except ValueError:
            self.error('Bad hex escape')
        self.i += count
        return v

    def parse_escape(self, in_class):
        """Parse an escape sequence starting after the backslash. Returns a
        tuple (kind, value) where kind is 'char' (value is a literal
        character), 'set' (value is V1 set content), 'nset' (negated set
        content), 'quote' (a \\Q...\\E literal) or 'raw' (value is regex text,
        only outside of sets)."""
        if self.i >= self.n:
            self.error('Trailing backslash')
        c = self.p[self.i]
        self.i += 1
        uc = self.f.uclass
        if c == 'w':
            return 'set', _U_W if uc else _ASCII_W
        if c == 'W':
            return 'nset', _U_W if uc else _ASCII_W
        if c == 'd':
            return 'set', _U_D if uc else _ASCII_D
        if c == 'D':
            return 'nset', _U_D if uc else _ASCII_D
        if c == 's':
            return 'set', _U_S if uc else _ASCII_S
        if c == 'S':
            return 'nset', _U_S if uc else _ASCII_S
        if c == 'h':
            return 'set', _H
        if c == 'H':
            return 'nset', _H
        if c == 'v':
            return 'set', _V
        if c == 'V':
            return 'nset', _V
        if c in 'pP':
            if self.peek() == '{':
                end = self.p.find('}', self.i)
                if end < 0:
                    self.error('Unclosed character family')
                name = self.p[self.i + 1:end]
                self.i = end + 1
            else:
                name = self.peek()
                if not name:
                    self.error('Illegal character family')
                self.i += 1
            content = _property_set(name, uc)
            return ('nset' if c == 'P' else 'set'), content
        if c == 't':
            return 'char', '\t'
        if c == 'n':
            return 'char', '\n'
        if c == 'r':
            return 'char', '\r'
        if c == 'f':
            return 'char', '\f'
        if c == 'a':
            return 'char', '\x07'
        if c == 'e':
            return 'char', '\x1b'
        if c == '0':
            # octal: \0n, \0nn, \0mnn
            digits = ''
            while len(digits) < 3 and self.peek() and self.peek() in '01234567':
                if len(digits) == 2 and digits[0] > '3':
                    break
                digits += self.peek()
                self.i += 1
            if not digits:
                self.error('Illegal octal escape sequence')
            return 'char', chr(int(digits, 8))
        if c == 'x':
            if self.peek() == '{':
                end = self.p.find('}', self.i)
                try:
                    v = int(self.p[self.i + 1:end], 16)
                    ch = chr(v)
                except (ValueError, OverflowError):
                    self.error('Illegal hexadecimal escape sequence')
                self.i = end + 1
                return 'char', ch
            return 'char', chr(self.read_hex(2))
        if c == 'u':
            v = self.read_hex(4)
            # surrogate pairs written as \\uD83D\\uDE00
            if 0xD800 <= v <= 0xDBFF and self.p.startswith('\\u', self.i):
                save = self.i
                self.i += 2
                try:
                    lo = self.read_hex(4)
                except JavaRegexError:
                    lo = None
                if lo is not None and 0xDC00 <= lo <= 0xDFFF:
                    return 'char', chr(0x10000 + ((v - 0xD800) << 10) + (lo - 0xDC00))
                self.i = save
            return 'char', chr(v)
        if c == 'c':
            ch = self.peek()
            if not ch:
                self.error('Illegal control escape sequence')
            self.i += 1
            return 'char', chr(ord(ch) ^ 64)
        if c == 'N' and self.peek() == '{':
            end = self.p.find('}', self.i)
            name = self.p[self.i + 1:end]
            self.i = end + 1
            import unicodedata
            try:
                return 'char', unicodedata.lookup(name)
            except KeyError:
                self.error('Unknown character name ' + name)
        if c == 'Q':
            end = self.p.find('\\E', self.i)
            if end < 0:
                end = self.n
            lit = self.p[self.i:end]
            self.i = min(end + 2, self.n)
            return 'quote', lit
        if not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9'):
            return 'char', c
        if in_class:
            if c.isalnum():
                if c in 'bBAzZGRXkK' or c.isdigit():
                    self.error('Illegal escape in class: \\' + c)
                self.error('Unknown escape: \\' + c)
            return 'char', c
        # outside class only
        if c == 'b':
            if self.peek() == '{':
                end = self.p.find('}', self.i)
                self.i = end + 1
                return 'raw', '\\b'
            if uc:
                return 'raw', '\\b'
            return 'raw', '(?:(?<=[a-zA-Z0-9_])(?![a-zA-Z0-9_])|(?<![a-zA-Z0-9_])(?=[a-zA-Z0-9_]))'
        if c == 'B':
            if uc:
                return 'raw', '\\B'
            return 'raw', '(?:(?<=[a-zA-Z0-9_])(?=[a-zA-Z0-9_])|(?<![a-zA-Z0-9_])(?![a-zA-Z0-9_]))'
        if c == 'A':
            return 'raw', '\\A'
        if c == 'z':
            return 'raw', '\\Z'
        if c == 'Z':
            if self.f.unix:
                return 'raw', '(?=\\n?\\Z)'
            return 'raw', '(?=(?:\\r\\n|[\\n\\r\\x85\\u2028\\u2029])?\\Z)'
        if c == 'G':
            return 'raw', '\\G'
        if c == 'R':
            return 'raw', '(?:\\r\\n|[\\n\\x0B\\f\\r\\x85\\u2028\\u2029])'
        if c == 'X':
            return 'raw', '\\X'
        if c == 'k':
            if self.peek() != '<':
                self.error('\\k is not followed by \'<\' for named capturing group')
            end = self.p.find('>', self.i)
            if end < 0:
                self.error('named capturing group is missing trailing \'>\'')
            name = self.p[self.i + 1:end]
            self.i = end + 1
            if name not in self.group_names:
                self.error('named capturing group <%s> does not exist' % name)
            return 'raw', self._backref('(?P=%s)' % name)
        if c.isdigit():
            num = int(c)
            while self.peek().isdigit() and num * 10 + int(self.peek()) <= self.group_count:
                num = num * 10 + int(self.peek())
                self.i += 1
            if num > self.group_count or num == 0:
                return 'raw', '(?!)'
            return 'raw', self._backref('(?:\\g<%d>)' % num)
        self.error('Unknown escape: \\' + c)

    def _backref(self, text):
        if self.aci:
            return '(?i:%s)' % text
        return text

    # ---- literals ----

    def literal(self, c):
        """A literal character outside a class, honouring the case flags."""
        if self.f.ci:
            if self.f.ucase:
                if c in _DOTTED_I:
                    return '[' + _DOTTED_I + ']'
            elif ('a' <= c <= 'z') or ('A' <= c <= 'Z'):
                return '[' + c + c.swapcase() + ']'
        return _escape_char(c)

    def set_escape(self, kind, val):
        if self.aci and val in ('a-z', 'A-Z'):
            val = 'a-zA-Z'
        s = ('[' if kind == 'set' else '[^') + val + ']'
        if self.aci and _is_cased_set(val):
            # Java matches properties like \p{Lu} case insensitively even
            # without UNICODE_CASE
            return '(?i:' + s + ')'
        return s

    # ---- character classes ----

    def parse_class(self):
        """Parse a Java character class, self.i is just after '['. Returns V1
        set text including the brackets."""
        self._class_depth += 1
        try:
            return self._parse_class()
        finally:
            self._class_depth -= 1

    def _parse_class(self):
        neg = False
        if self.peek() == '^':
            neg = True
            self.i += 1
        items = []  # list of strings (V1 set fragments)
        intersections = []
        first = True
        has_set = [False]
        ci, ucase = self.f.ci, self.f.ucase

        def add_char(ch):
            items.append(_escape_char(ch))
            if ci:
                if ucase:
                    if ch in _DOTTED_I:
                        items.append(_DOTTED_I)
                elif ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'):
                    items.append(ch.swapcase())

        def add_range(lo, hi):
            items.append(_escape_char(lo) + '-' + _escape_char(hi))
            if ci:
                a, b = ord(lo), ord(hi)
                if ucase:
                    if a <= 0x69 <= b:
                        items.append('ıİ')
                    elif a <= 0x49 <= b:
                        items.append('ı')
                else:
                    items.extend(_ascii_swapcase_ranges(a, b))

        while True:
            self.skip_comments()
            if self.i >= self.n:
                self.error('Unclosed character class')
            c = self.p[self.i]
            if c == ']' and not first:
                self.i += 1
                break
            first = False
            if c == '[':
                self.i += 1
                items.append(self.parse_class())
                continue
            if c == '&' and self.peek(1) == '&':
                self.i += 2
                intersections.append(items)
                items = []
                continue
            # single char or escape, possibly a range
            kind, val = self.class_atom()
            if kind == 'char':
                save = self.i
                self.skip_comments()
                if self.peek() == '-':
                    self.i += 1
                    self.skip_comments()
                    if self.peek() not in (']', '', '['):
                        kind2, val2 = self.class_atom()
                        if kind2 == 'char':
                            if ord(val2) < ord(val):
                                self.error('Illegal character range')
                            add_range(val, val2)
                            continue
                    # not a range, e.g. [a-\\w] or [a-]: treat '-' literally
                self.i = save
                add_char(val)
            elif kind == 'quote':
                for ch in val:
                    add_char(ch)
            elif kind in ('set', 'nset'):
                if ci and not ucase and val in ('a-z', 'A-Z'):
                    val = 'a-zA-Z'
                if _is_cased_set(val):
                    has_set[0] = True
                items.append(('[' if kind == 'set' else '[^') + val + ']')
        intersections.append(items)
        parts = []
        for its in intersections:
            if not its:
                continue
            parts.append('[' + ''.join(its) + ']')
        if not parts:
            return '[^\\x00-\\U0010FFFF]' if not neg else '[\\x00-\\U0010FFFF]'
        if len(parts) == 1:
            inner = parts[0][1:-1]
        else:
            inner = '&&'.join(parts)
        s = ('[^' if neg else '[') + inner + ']'
        if has_set[0] and self.aci and self._class_depth == 1:
            s = '(?i:' + s + ')'
        return s

    def class_atom(self):
        c = self.p[self.i]
        self.i += 1
        if c == '\\':
            return self.parse_escape(True)
        return 'char', c

    # ---- main ----

    def _quantifier(self):
        """Parse a quantifier at self.i (after skipping comments). Returns
        (text, is_curly) or None."""
        c = self.peek()
        if c in ('*', '+', '?') and c:
            self.i += 1
            return c, False
        if c == '{':
            m = (_CURLY_X if self.f.comments else _CURLY).match(self.p, self.i)
            if m is None:
                self.error('Illegal repetition')
            lo = int(m.group(1))
            hi = m.group(3)
            if lo > _MAX_REPEAT or (hi and int(hi) > _MAX_REPEAT):
                self.error('Illegal repetition range')
            if m.group(2):
                if hi:
                    if int(hi) < lo:
                        self.error('Illegal repetition range')
                    # huge upper bounds make the regex module allocate a lot
                    # of memory, they are practically unbounded
                    q = '{%d,%d}' % (lo, int(hi)) if int(hi) <= _BIG_REPEAT else '{%d,}' % lo
                else:
                    q = '{%d,}' % lo
            else:
                q = '{%d}' % lo
            self.i = m.end()
            return q, True
        return None

    def _modifier(self):
        self.skip_comments()
        c = self.peek()
        if c in ('?', '+') and c:
            self.i += 1
            return c
        return ''

    def translate(self):
        out = self.out
        # index into out where the last complete atom starts (None if there
        # is nothing a quantifier could apply to)
        atom_start = None
        stack = []  # (flags, regex ci state, out index of the group start)
        while True:
            self.skip_comments()
            if self.i >= self.n:
                break
            c = self.p[self.i]
            if c in '*+?{':
                if atom_start is None:
                    self.error('Dangling meta character \'%s\'' % c)
                q, _ = self._quantifier()
                q += self._modifier()
                out.append(q)
                # Java ignores counted quantifiers directly following a
                # quantifier (a{2}{3} == a{2}), any other quantifier there is
                # a syntax error
                while True:
                    self.skip_comments()
                    nc = self.peek()
                    if nc == '{':
                        self._quantifier()
                        self._modifier()
                        continue
                    if nc and nc in '*+?':
                        self.error('Dangling meta character \'%s\'' % nc)
                    break
                atom_start = None
                continue
            if c == '\\':
                self.i += 1
                start = len(out)
                kind, val = self.parse_escape(False)
                if kind == 'char':
                    out.append(self.literal(val))
                elif kind == 'quote':
                    if not val:
                        start = None
                    elif len(val) == 1:
                        out.append(self.literal(val))
                    else:
                        out.append('(?:' + ''.join(self.literal(ch) for ch in val) + ')')
                elif kind in ('set', 'nset'):
                    out.append(self.set_escape(kind, val))
                else:
                    out.append(val)
                atom_start = start
            elif c == '[':
                self.i += 1
                atom_start = len(out)
                out.append(self.parse_class())
            elif c == '(':
                self.i += 1
                saved = (self.f.copy(), self.r_ci, len(out))
                g = self.parse_group_open()
                if g is None:
                    # (?flags) applying to the rest of the enclosing group
                    atom_start = None
                    continue
                stack.append(saved)
                out.append(g)
                atom_start = None
            elif c == ')':
                self.i += 1
                if not stack:
                    self.error('Unmatched closing \')\'')
                self.f, self.r_ci, start = stack.pop()
                out.append(')')
                atom_start = start
            elif c == '.':
                self.i += 1
                atom_start = len(out)
                f = self.f
                if f.dotall:
                    out.append('(?s:.)')
                elif f.unix:
                    out.append('[^\\n]')
                else:
                    out.append('[^' + _LT + ']')
            elif c == '^':
                self.i += 1
                atom_start = len(out)
                if self.f.multi:
                    out.append(_CARET_M_UNIX if self.f.unix else _CARET_M)
                else:
                    out.append('\\A')
            elif c == '$':
                self.i += 1
                atom_start = len(out)
                f = self.f
                if f.multi:
                    out.append(_DOLLAR_M_UNIX if f.unix else _DOLLAR_M)
                else:
                    out.append(_DOLLAR_UNIX if f.unix else _DOLLAR)
            elif c == '|':
                self.i += 1
                atom_start = None
                out.append('|')
            else:
                self.i += 1
                atom_start = len(out)
                out.append(self.literal(c))
        if stack:
            self.error('Unclosed group')
        return ''.join(out)

    def parse_group_open(self):
        """Parse a group opening after '('. Returns the regex text, or None
        for a (?flags) construct which isn't a group."""
        self.skip_comments()
        if self.peek() != '?':
            return '('
        self.i += 1
        c = self.peek()
        if c in (':', '=', '!', '>') and c:
            self.i += 1
            return '(?' + c
        if c == '<':
            c2 = self.peek(1)
            if c2 in ('=', '!') and c2:
                self.i += 2
                return '(?<' + c2
            end = self.p.find('>', self.i)
            name = self.p[self.i + 1:end] if end > 0 else ''
            if end < 0 or not _GROUP_NAME.match(name):
                self.error('capturing group name does not start with a Latin letter or contains '
                           'illegal characters')
            if name in self.group_names:
                self.error('Named capturing group <%s> is already defined' % name)
            self.group_names.add(name)
            self.i = end + 1
            return '(?P<%s>' % name
        # inline flags
        j = self.i
        on = True
        flags_on, flags_off = [], []
        while j < self.n and self.p[j] not in ':)':
            ch = self.p[j]
            if ch == '-':
                on = False
            elif ch in 'idmsuxUc':
                (flags_on if on else flags_off).append(ch)
            else:
                self.i = j
                self.error('Unknown inline modifier')
            j += 1
        if j >= self.n:
            self.error('Unclosed group')
        term = self.p[j]
        self.i = j + 1
        f = self.f
        for ch, val in [(x, True) for x in flags_on] + [(x, False) for x in flags_off]:
            if ch == 'i':
                f.ci = val
            elif ch == 'u':
                f.ucase = val
            elif ch == 'U':
                f.uclass = val
                if val:
                    f.ucase = True
            elif ch == 's':
                f.dotall = val
            elif ch == 'd':
                f.unix = val
            elif ch == 'm':
                f.multi = val
            elif ch == 'x':
                f.comments = val
        want = f.ci and f.ucase
        if term == ':':
            if want != self.r_ci:
                self.r_ci = want
                return '(?i:' if want else '(?-i:'
            return '(?:'
        if want != self.r_ci:
            self.r_ci = want
            self.out.append('(?i)' if want else '(?-i)')
        return None


_cache = {}
_cache_lock = threading.Lock()


def translate(pattern, flags=0):
    t = _Translator(pattern, flags)
    return t.translate()


def compile(pattern, flags=0):
    """Compile a Java regex. flags may include IGNORECASE (Java
    CASE_INSENSITIVE|UNICODE_CASE) and UNICODE_CHARACTER_CLASS."""
    key = (pattern, flags)
    r = _cache.get(key)
    if r is not None:
        return r
    py = translate(pattern, flags)
    rflags = regex.V1
    if flags & IGNORECASE:
        rflags |= regex.IGNORECASE
    try:
        r = regex.compile('(?-f)' + py, rflags)
    except regex.error as e:
        raise JavaRegexError('Cannot compile %r (translated: %r): %s' % (pattern, py, e)) from e
    with _cache_lock:
        _cache[key] = r
    return r


def _java_replacement(compiled, repl):
    """Convert a java.util.regex.Matcher replacement string (using $n and
    ${name} group references, backslash escapes) into a function suitable for
    regex.sub(). Invalid replacement strings raise JavaRegexError when the
    first match is replaced (like Matcher.appendReplacement)."""
    parts = []  # (is_group, value)
    lit = []
    i = 0
    n = len(repl)
    gcount = compiled.groups
    names = compiled.groupindex
    error = None

    def flush():
        if lit:
            parts.append((False, ''.join(lit)))
            lit.clear()

    while i < n:
        c = repl[i]
        if c == '\\':
            i += 1
            if i >= n:
                error = 'character to be escaped is missing'
                break
            lit.append(repl[i])
            i += 1
            continue
        if c == '$':
            i += 1
            if i >= n:
                error = 'Illegal group reference: group index is missing'
                break
            if repl[i] == '{':
                end = repl.find('}', i + 1)
                name = repl[i + 1:end] if end > 0 else ''
                if end < 0:
                    error = "named capturing group is missing trailing '}'"
                    break
                if not name:
                    error = 'named capturing group has 0 length name'
                    break
                if not _GROUP_NAME.match(name):
                    error = 'capturing group name {%s} starts with digit character' % name
                    break
                if name not in names:
                    error = 'No group with name {%s}' % name
                    break
                flush()
                parts.append((True, name))
                i = end + 1
                continue
            if not ('0' <= repl[i] <= '9'):
                error = 'Illegal group reference'
                break
            num = int(repl[i])
            i += 1
            if num > gcount:
                error = 'No group %d' % num
                break
            while i < n and '0' <= repl[i] <= '9' and num * 10 + int(repl[i]) <= gcount:
                num = num * 10 + int(repl[i])
                i += 1
            flush()
            parts.append((True, num))
            continue
        lit.append(c)
        i += 1
    flush()

    if error is not None:
        def fail(m):
            raise JavaRegexError('Invalid replacement %r: %s' % (repl, error))
        return fail

    def func(m):
        out = []
        for is_group, p in parts:
            if is_group:
                g = m.group(p)
                if g:
                    out.append(g)
            else:
                out.append(p)
        return ''.join(out)

    return func


_repl_cache = {}


def java_replace(compiled, repl, s, count=0):
    """Matcher.replaceAll (count=0) / replaceFirst (count=1)."""
    key = (compiled, repl)
    f = _repl_cache.get(key)
    if f is None:
        if '$' not in repl and '\\' not in repl:
            f = repl
        else:
            f = _java_replacement(compiled, repl)
        if len(_repl_cache) > 10000:
            _repl_cache.clear()
        _repl_cache[key] = f
    if isinstance(f, str):
        return compiled.sub(lambda m: f, s, count=count)
    return compiled.sub(f, s, count=count)
