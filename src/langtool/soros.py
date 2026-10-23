"""Port of org.languagetool.synthesis.Soros, the Soros interpreter of
numbertext.org (2009-2010 (c) László Németh, LGPL/BSD dual license): spells
out numbers ("21" -> "tjugoett") using the rules of a .sor file. Used by
BaseSynthesizer for the _spell_number_ POS tags."""

import os
import re
import threading

from . import jregex

_M = '\\";#'
_M2 = '$()|[]'
_C = '\ue000\ue001\ue002\ue003'
_C2 = '\ue004\ue005\ue006\ue007\ue008\ue009'
_SLASH = '\ue000'
_PIPE = '\ue003'


def _translate(s, chars, chars2, delim):
    for i, ch in enumerate(chars):
        s = s.replace(delim + ch, chars2[i])
    return s


def _replace_all(pattern, repl, s):
    # String.replaceAll
    return jregex.java_replace(jregex.compile(pattern), repl, s)


def _replace_first(pattern, repl, s):
    # String.replaceFirst
    return jregex.java_replace(jregex.compile(pattern), repl, s, 1)


def _str(s):
    # Java string concatenation of a possibly null String
    return 'null' if s is None else s


# pattern to recognize function calls in the replacement string
_FUNC = jregex.compile(_translate(
    '(?:\\|?(?:\\$\\()+)?'             # optional nested calls
    '(\\|?\\$\\(([^\\(\\)]*)\\)\\|?)'  # inner call (2 subgroups)
    '(?:\\)+\\|?)?',                   # optional nested calls
    _M2[:len(_C)], _C, '\\'))          # \$, \(, \), \| -> \uE000..\uE003

_LINE = jregex.compile('^\\s*("[^"]*"|[^\\s]*)\\s*(.*[^\\s])?\\s*$')
_MACRO = jregex.compile('== *(.*[^ ]?) ==')


class Soros:
    """Port of org.languagetool.synthesis.Soros"""

    def __init__(self, source, lang):
        self.patterns = []
        self.values = []
        self.begins = []
        self.ends = []
        source = _translate(source, _M, _C, '\\')  # \\, \", \;, \# -> \uE000..\uE003
        # switch off all country-dependent lines, and switch on the requested ones
        source = _replace_all('(^|[\n;])([^\n;#]*#[^\n]*\\[:[^\n:\\]]*:][^\n]*)', '$1#$2', source)
        source = _replace_all('(^|[\n;])#([^\n;#]*#[^\n]*\\[:' + lang.replace('_', '-') + ':][^\n]*)', '$1$2',
                              source)
        source = _replace_all('(#[^\n]*)?(\n|$)', ';', source)  # remove comments
        if '__numbertext__' not in source:
            source = '__numbertext__;' + source
        source = source.replace(
            '__numbertext__',
            # default left zero deletion
            '"([a-z][-a-z]* )?0+(0|[1-9]\\d*)" $(\\1\\2);'
            # separator function
            '"\ue00a(.*)\ue00a(.+)\ue00a(.*)" \\1\\2\\3;'
            # no separation, if subcall returns with empty string
            '"\ue00a.*\ue00a\ue00a.*"')

        prefix = ''
        for s in source.split(';'):
            matchmacro = _MACRO.fullmatch(s)
            if matchmacro:
                prefix = matchmacro.group(1)
                continue
            sp = _LINE.fullmatch(s)
            if prefix != '' and s != '' and sp:
                s = _replace_first('"$', '', _replace_first('^"', '', sp.group(1)))
                s = ('"' + ('^' if s.startswith('^') else '') + prefix + ('' if s == '' else ' ')
                     + _replace_first('^\\^', '', s) + '" ' + _str(sp.group(2)))
                sp = _LINE.fullmatch(s)
            if s != '' and sp:
                s = _translate(_replace_first('"$', '', _replace_first('^"', '', sp.group(1))),
                               _C[1:], _M[1:], '')
                s = s.replace(_SLASH, '\\\\')  # -> \\, ", ;, #
                s2 = ''
                if sp.group(2) is not None:
                    s2 = _replace_first('"$', '', _replace_first('^"', '', sp.group(2)))
                s2 = _translate(s2, _M2, _C2, '\\')  # \$, \(, \), \|, \[, \] -> \uE004..\uE009
                # call inner separator: [ ... $1 ... ] -> $(\uE00A ... \uE00A$1\uE00A ... )
                s2 = _replace_all('^\\[[$](\\d\\d?|\\([^\\)]+\\))', '\\$(\ue00a\ue00a|\\$$1\ue00a', s2)  # add "|"
                s2 = _replace_all('\\[([^$\\[\\\\]*)[$](\\d\\d?|\\([^\\)]+\\))', '\\$(\ue00a$1\ue00a\\$$2\ue00a', s2)
                s2 = _replace_all('\ue00a\\]$', '|\ue00a)', s2)  # add "|" in terminating position
                s2 = s2.replace(']', ')')
                s2 = _replace_all('(\\$\\d|\\))\\|\\$', '$1||\\$', s2)  # $()|$() -> $()||$()
                s2 = _translate(s2, _C, _M, '')  # \uE000..\uE003-> \, ", ;, #
                s2 = _translate(s2, _M2[:len(_C)], _C, '')  # $, (, ), | -> \uE000..\uE003
                s2 = _translate(s2, _C2, _M2, '')  # \uE004..\uE009 -> $, (, ), |, [, ]
                s2 = _replace_all('[$]', '\\$', s2)  # $ -> \$
                s2 = _replace_all('\ue000(\\d)', '\ue000\ue001\\$$1\ue002', s2)  # $n -> $(\n)
                s2 = _replace_all('\\\\(\\d)', '\\$$1', s2)  # \[n] -> $[n]
                s2 = s2.replace('\\n', '\n')  # \n -> [new line]
                self.patterns.append(jregex.compile(
                    '^' + _replace_first('\\$$', '', _replace_first('^\\^', '', s)) + '$'))
                self.begins.append(s.startswith('^'))
                self.ends.append(s.endswith('$'))
                self.values.append(s2)

    def run(self, input, begin=True, end=True):
        for i, pattern in enumerate(self.patterns):
            if (not begin and self.begins[i]) or (not end and self.ends[i]):
                continue
            if not pattern.fullmatch(input):
                continue
            s = jregex.java_replace(pattern, self.values[i], input)
            n = _FUNC.search(s)
            while n:
                b = False
                e = False
                if n.group(1).startswith(_PIPE) or n.group().startswith(_PIPE):
                    b = True
                elif n.start() == 0:
                    b = begin
                if n.group(1).endswith(_PIPE) or n.group().endswith(_PIPE):
                    e = True
                elif n.end() == len(s):
                    e = end
                s = s[:n.start(1)] + self.run(n.group(2), b, e) + s[n.end(1):]
                n = _FUNC.search(s)
            return s
        return ''


_LINE_BREAK = re.compile('\r\n|\r|\n')

_cache = {}
_cache_lock = threading.Lock()


def load_soros(path, lang):
    """A Soros for the .sor file at path (cached), or None if it cannot be
    read or compiled (BaseSynthesizer.createNumberSpeller and
    createRomanNumberer return null on any exception)."""
    key = (path, lang)
    with _cache_lock:
        if key in _cache:
            return _cache[key]
        s = None
        if path is not None and os.path.exists(path):
            try:
                with open(path, encoding='utf-8', newline='') as f:
                    text = f.read()
                # BufferedReader.readLine() + '\n' for each line
                lines = _LINE_BREAK.split(text)
                if lines and lines[-1] == '':
                    lines.pop()
                source = ''.join(line + '\n' for line in lines)
                s = Soros(source, lang)
            except Exception:  # noqa: BLE001 -- like Java, any problem means no number speller
                s = None
        _cache[key] = s
        return s
