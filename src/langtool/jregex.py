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


def _property_set(name, unicode_classes):
    """Return the content of a V1 set (usable between [ and ]) matching the
    given Java property name."""
    n = name.strip()
    low = n.lower()
    if low in _POSIX:
        return _POSIX[low][1 if unicode_classes else 0]
    if low in _JAVA_PROPS:
        return _JAVA_PROPS[low]
    if '=' in n:
        key, val = n.split('=', 1)
        key = key.strip().lower()
        val = val.strip()
        if key in ('gc', 'general_category'):
            return '\\p{%s}' % val
        if key in ('sc', 'script'):
            return '\\p{Script=%s}' % val
        if key in ('blk', 'block'):
            return '\\p{Block=%s}' % val
        return '\\p{%s}' % n
    if low.startswith('is'):
        rest = n[2:]
        lr = rest.lower()
        if lr in _BINARY_PROPS:
            return _BINARY_PROPS[lr]
        if lr in _POSIX:
            return _POSIX[lr][1 if unicode_classes else 0]
        if _valid_regex_prop(rest):
            return '\\p{%s}' % rest
        if _valid_regex_prop(n):
            return '\\p{%s}' % n
        raise JavaRegexError('Unknown property: %s' % name)
    if low.startswith('in'):
        rest = n[2:]
        if _valid_regex_prop('Block=' + rest):
            return '\\p{Block=%s}' % rest
        if _valid_regex_prop(n):
            return '\\p{%s}' % n
        raise JavaRegexError('Unknown block: %s' % name)
    if _valid_regex_prop(n):
        return '\\p{%s}' % n
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
        return ' '
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


class _Translator:

    def __init__(self, pattern, flags):
        self.p = pattern
        self.n = len(pattern)
        self.i = 0
        self.unicode_classes = bool(flags & UNICODE_CHARACTER_CLASS)
        self.dotall = False
        self.comments = False
        self.out = []
        self.group_count = _count_groups(pattern)

    def error(self, msg):
        raise JavaRegexError('%s at position %d in: %r' % (msg, self.i, self.p))

    def peek(self, k=0):
        j = self.i + k
        return self.p[j] if j < self.n else ''

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
        content) or 'raw' (value is regex text, only outside of sets)."""
        if self.i >= self.n:
            self.error('Trailing backslash')
        c = self.p[self.i]
        self.i += 1
        uc = self.unicode_classes
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
                    self.error('Unclosed property')
                name = self.p[self.i + 1:end]
                self.i = end + 1
            else:
                name = self.peek()
                self.i += 1
            neg = c == 'P'
            if name.startswith('^'):
                neg = not neg
                name = name[1:]
            content = _property_set(name, uc)
            return ('nset' if neg else 'set'), content
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
                self.error('Bad octal escape')
            return 'char', chr(int(digits, 8))
        if c == 'x':
            if self.peek() == '{':
                end = self.p.find('}', self.i)
                v = int(self.p[self.i + 1:end], 16)
                self.i = end + 1
                return 'char', chr(v)
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
            self.i += 1
            return 'char', chr(ord(ch) ^ 64)
        if c == 'N' and self.peek() == '{':
            end = self.p.find('}', self.i)
            name = self.p[self.i + 1:end]
            self.i = end + 1
            import unicodedata
            return 'char', unicodedata.lookup(name)
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
            return 'raw', '(?=(?:\\r\\n|[\\n\\r\\x85\\u2028\\u2029])?\\Z)'
        if c == 'G':
            return 'raw', '\\G'
        if c == 'R':
            return 'raw', '(?:\\r\\n|[\\n\\x0B\\f\\r\\x85\\u2028\\u2029])'
        if c == 'X':
            return 'raw', '\\X'
        if c == 'k':
            if self.peek() != '<':
                self.error('Bad named backreference')
            end = self.p.find('>', self.i)
            name = self.p[self.i + 1:end]
            self.i = end + 1
            return 'raw', '(?P=%s)' % name
        if c.isdigit():
            num = int(c)
            while self.peek().isdigit() and num * 10 + int(self.peek()) <= self.group_count:
                num = num * 10 + int(self.peek())
                self.i += 1
            if num > self.group_count or num == 0:
                return 'raw', '(?!)'
            return 'raw', '(?:\\g<%d>)' % num
        self.error('Unknown escape: \\' + c)

    # ---- character classes ----

    def parse_class(self):
        """Parse a Java character class, self.i is just after '['. Returns V1
        set text including the brackets."""
        neg = False
        if self.peek() == '^':
            neg = True
            self.i += 1
        items = []  # list of strings (V1 set fragments)
        intersections = []
        first = True
        while True:
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
                if self.peek() == '-' and self.peek(1) not in (']', '') and self.peek(1) != '[':
                    save = self.i
                    self.i += 1
                    kind2, val2 = self.class_atom()
                    if kind2 == 'char':
                        if ord(val2) < ord(val):
                            self.error('Illegal character range')
                        items.append(_escape_char(val) + '-' + _escape_char(val2))
                        continue
                    # not a range, e.g. [a-\\w]: treat '-' literally
                    self.i = save
                items.append(_escape_char(val))
            elif kind == 'quote':
                items.extend(_escape_char(ch) for ch in val)
            elif kind == 'set':
                items.append('[' + val + ']')
            elif kind == 'nset':
                items.append('[^' + val + ']')
        intersections.append(items)
        parts = []
        for its in intersections:
            if not its:
                continue
            parts.append('[' + ''.join(its) + ']')
        if not parts:
            body = '[]' if not neg else ''
            return '[^]' if neg else '[^\\x00-\\U0010FFFF]'
        if len(parts) == 1:
            inner = parts[0][1:-1]
        else:
            inner = '&&'.join(parts)
        return ('[^' if neg else '[') + inner + ']'

    def class_atom(self):
        c = self.p[self.i]
        self.i += 1
        if c == '\\':
            return self.parse_escape(True)
        return 'char', c

    # ---- main ----

    def translate(self):
        out = self.out
        # index into out where the last complete atom starts, used to wrap
        # stacked quantifiers like X*{1,3}, which Java accepts
        atom_start = None
        quantified = False
        group_stack = []
        while self.i < self.n:
            c = self.p[self.i]
            if c in '*+?' or (c == '{' and self._curly_quantifier() is not None):
                if c == '{':
                    q = self._curly_quantifier()
                    self.i += len(q)
                else:
                    q = c
                    self.i += 1
                if self.peek() in ('?', '+') and self.peek():
                    q += self.peek()
                    self.i += 1
                if quantified and atom_start is not None:
                    out[atom_start:] = ['(?:' + ''.join(out[atom_start:]) + ')']
                out.append(q)
                quantified = True
                continue
            quantified = False
            if c == '\\':
                self.i += 1
                atom_start = len(out)
                kind, val = self.parse_escape(False)
                if kind == 'char':
                    out.append(_escape_char(val))
                elif kind == 'quote':
                    lit = ''.join(_escape_char(ch) for ch in val)
                    out.append('(?:' + lit + ')' if len(val) > 1 else lit)
                elif kind == 'set':
                    out.append('[' + val + ']')
                elif kind == 'nset':
                    out.append('[^' + val + ']')
                else:
                    out.append(val)
            elif c == '[':
                self.i += 1
                atom_start = len(out)
                out.append(self.parse_class())
            elif c == '(':
                self.i += 1
                group_stack.append(len(out))
                g = self.parse_group_open()
                if g:
                    out.append(g)
                else:
                    group_stack.pop()
                atom_start = None
            elif c == ')':
                self.i += 1
                atom_start = group_stack.pop() if group_stack else None
                out.append(')')
            elif c == '.':
                self.i += 1
                atom_start = len(out)
                out.append('.' if self.dotall else '[^' + _LINE_TERMINATORS + ']')
            elif c == '{':
                atom_start = len(out)
                out.append('\\{')
                self.i += 1
            elif c == '}':
                atom_start = len(out)
                out.append('\\}')
                self.i += 1
            elif c == '#' and self.comments:
                j = self.p.find('\n', self.i)
                self.i = self.n if j < 0 else j + 1
            elif c in ' \t\n\r' and self.comments:
                self.i += 1
            else:
                atom_start = len(out) if c not in '|^$' else None
                out.append(c)
                self.i += 1
        return ''.join(out)

    def _curly_quantifier(self):
        j = self.p.find('}', self.i)
        if j < 0:
            return None
        body = self.p[self.i + 1:j]
        if body and body[0].isdigit() and all(ch.isdigit() or ch == ',' for ch in body) and body.count(',') <= 1:
            return self.p[self.i:j + 1]
        return None

    def parse_group_open(self):
        if self.peek() != '?':
            return '('
        self.i += 1
        c = self.peek()
        if c in ':=!>':
            self.i += 1
            return '(?' + c
        if c == '<':
            c2 = self.peek(1)
            if c2 in '=!':
                self.i += 2
                return '(?<' + c2
            end = self.p.find('>', self.i)
            name = self.p[self.i + 1:end]
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
            elif ch in 'idmsuxU':
                (flags_on if on else flags_off).append(ch)
            else:
                self.error('Unknown inline flag ' + ch)
            j += 1
        if j >= self.n:
            self.error('Unclosed group')
        term = self.p[j]
        self.i = j + 1
        if 's' in flags_on:
            self.dotall = True
        if 's' in flags_off:
            self.dotall = False
        if 'x' in flags_on:
            self.comments = True
        if 'x' in flags_off:
            self.comments = False
        if 'U' in flags_on:
            self.unicode_classes = True
        if 'U' in flags_off:
            self.unicode_classes = False
        keep_on = ''.join(f for f in flags_on if f in 'imx')
        keep_off = ''.join(f for f in flags_off if f in 'imx')
        if 's' in flags_on or 's' in flags_off:
            pass  # handled by translating '.'
        flagstr = keep_on + ('-' + keep_off if keep_off else '')
        if term == ':':
            return '(?%s:' % flagstr if flagstr else '(?:'
        # (?flags) applying to the rest of the enclosing group
        return '(?%s)' % flagstr if flagstr else ''


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
    regex.sub()."""
    parts = []  # (is_group, value)
    lit = []
    i = 0
    n = len(repl)
    gcount = compiled.groups

    def flush():
        if lit:
            parts.append((False, ''.join(lit)))
            lit.clear()

    while i < n:
        c = repl[i]
        if c == '\\':
            i += 1
            if i < n:
                lit.append(repl[i])
                i += 1
            continue
        if c == '$' and i + 1 < n:
            if repl[i + 1] == '{':
                end = repl.find('}', i + 2)
                if end > 0:
                    flush()
                    parts.append((True, repl[i + 2:end]))
                    i = end + 1
                    continue
            if repl[i + 1].isdigit():
                num = int(repl[i + 1])
                i += 2
                while i < n and repl[i].isdigit() and num * 10 + int(repl[i]) <= gcount:
                    num = num * 10 + int(repl[i])
                    i += 1
                flush()
                parts.append((True, num))
                continue
        lit.append(c)
        i += 1
    flush()

    def func(m):
        out = []
        for is_group, p in parts:
            if is_group:
                try:
                    g = m.group(p)
                except (IndexError, regex.error):
                    g = None
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
