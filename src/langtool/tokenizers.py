"""Word tokenizer, port of org.languagetool.tokenizers.WordTokenizer."""

import regex

from .tools import is_whitespace

TOKENIZING_CHARACTERS = (
    ' \xa0ᅟᅠ            ​‌'
    '‍‎‏  ‪‫‬‭‮  ⁠⁡⁢⁣⁪'
    '⁫⁬⁭⁮⁯　ㅤ﻿ﾠ￹￺￻'
    '¦‖∣|,.;()[]{}=*#∗+×·÷<>!?:~/\\"\'«»„”“‘’`´‛′›‹…¿¡‼⁇⁈⁉™®‽¶￫⸮'
    '‒–—―'
    '─ㅡ✓'
    '●○◆➢■□★❏➔↵❖▪❑•'
    '⮚≥→⇾⇉⇒⇨⇛'
    '¹²³⁰ⁱ⁴⁵⁶⁷⁸⁹'
    '\t\n\r\u000b'
)

PROTOCOLS = ('http', 'https', 'ws', 'wss', 'ftp', 'ftps', 'sftp', 'file', 'mailto', 'tel', 'sms', 'git', 'ssh',
             'data', 'magnet', 'smb', 'slack', 'spotify', 'magnet')
_PROTOCOL_SET = frozenset(PROTOCOLS)

_URL_CHARS = regex.compile(r"[a-zA-ZÄÖÜäöü0-9/%$-_.+!*'(),?#~]+")
_DOMAIN_CHARS = regex.compile(r'[a-zA-Z0-9][a-zA-Z0-9-]+')
_NO_PROTOCOL_URL = regex.compile(r'([a-zA-Z0-9][a-zA-Z0-9-]+\.)?([a-zA-Z0-9][a-zA-Z0-9-]+)\.([a-zA-Z0-9][a-zA-Z0-9-]+)/.*')
_E_MAIL = regex.compile(r"(?<!:)@?(?:(?<=[a-zA-Z0-9_])(?![a-zA-Z0-9_])|(?<![a-zA-Z0-9_])(?=[a-zA-Z0-9_]))"
                        r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|"
                        r"(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))"
                        r"(?:(?<=[a-zA-Z0-9_])(?![a-zA-Z0-9_])|(?<![a-zA-Z0-9_])(?=[a-zA-Z0-9_]))")
_CURRENCY_SYMBOLS = r'[A-Z]*[฿₿₵¢₡$₫֏€ƒ₲₴₭₾₺₼₦₱£៛₽₹₪৳₸₮₩¥¤]'
_CURRENCY_VALUE = r'\d+(?:[.,]\d+)*'
_CURRENCY_EXPRESSION = regex.compile('(?:(%s)(%s)|(%s)(%s))' % (
    _CURRENCY_SYMBOLS, _CURRENCY_VALUE, _CURRENCY_VALUE, _CURRENCY_SYMBOLS))


def string_tokenize(text, delimiters):
    """java.util.StringTokenizer(text, delimiters, returnDelims=true)"""
    out = []
    start = 0
    n = len(text)
    i = 0
    if isinstance(delimiters, str):
        delimiters = frozenset(delimiters)
    while i < n:
        c = text[i]
        if c in delimiters:
            if i > start:
                out.append(text[start:i])
            out.append(c)
            start = i + 1
        i += 1
    if start < n:
        out.append(text[start:])
    return out


def _make_splitter(chars):
    cls = ''.join(regex.escape(c) for c in sorted(set(chars)))
    return regex.compile('([%s])' % cls)


def is_url(token):
    for p in PROTOCOLS:
        if token.startswith(p + '://') or token.startswith('www.'):
            return True
    return _NO_PROTOCOL_URL.fullmatch(token) is not None


def is_email(token):
    return _E_MAIL.fullmatch(token) is not None


class WordTokenizer:
    """Splits a sentence into tokens. Whitespace is kept as separate tokens."""

    tokenizing_characters = TOKENIZING_CHARACTERS

    def __init__(self):
        self._splitter = _make_splitter(self.get_tokenizing_characters())

    def get_tokenizing_characters(self):
        return self.tokenizing_characters

    def tokenize(self, text):
        return self.join_emails_and_urls(self.split(text))

    def split(self, text):
        return [t for t in self._splitter.split(text) if t]

    def join_emails_and_urls(self, tokens):
        return self.join_urls(self.join_emails(tokens))

    def join_emails(self, tokens):
        text = ''.join(tokens)
        if '@' not in text or _E_MAIL.search(text) is None:
            return tokens
        l = []
        current = 0
        idx = 0
        for m in _E_MAIL.finditer(text):
            start, end = m.start(), m.end()
            while current < end:
                if current < start:
                    l.append(tokens[idx])
                elif current == start:
                    l.append(m.group())
                current += len(tokens[idx])
                idx += 1
        if current < len(text):
            l.extend(tokens[idx:])
        return l

    def join_urls(self, l):
        new_list = []
        in_url = False
        url = []
        url_quote = None
        for i in range(len(l)):
            if self._url_starts_at(i, l) and not in_url:
                in_url = True
                if i - 1 >= 0:
                    url_quote = l[i - 1]
                url.append(l[i])
            elif in_url and self._url_ends_at(i, l, url_quote):
                in_url = False
                url_quote = None
                new_list.append(''.join(url))
                url = []
                new_list.append(l[i])
            elif in_url:
                url.append(l[i])
            else:
                new_list.append(l[i])
        if url:
            new_list.append(''.join(url))
        return new_list

    def _url_starts_at(self, i, l):
        token = l[i]
        n = len(l)
        if token in _PROTOCOL_SET and n > i + 3:
            if l[i + 1] == ':' and l[i + 2] == '/' and l[i + 3] == '/':
                return True
        if n > i + 1:
            if l[i] == 'www' and l[i + 1] == '.':
                return True
        if (n > i + 3 and l[i + 1] == '.' and l[i + 3] == '/' and _DOMAIN_CHARS.fullmatch(token) and
                _DOMAIN_CHARS.fullmatch(l[i + 2])):
            return True
        return (n > i + 5 and l[i + 1] == '.' and l[i + 3] == '.' and l[i + 5] == '/' and
                _DOMAIN_CHARS.fullmatch(token) is not None and _DOMAIN_CHARS.fullmatch(l[i + 2]) is not None and
                _DOMAIN_CHARS.fullmatch(l[i + 4]) is not None)

    def _url_ends_at(self, i, l, url_quote):
        token = l[i]
        if is_whitespace(token) or token == ')' or token == ']':
            return True
        if len(l) > i + 1:
            nxt = l[i + 1]
            if (((is_whitespace(nxt) or nxt in ('"', '»', '«', '‘', '’', '“', '”', "'", '.')) and
                    (token in ('.', ',', ';', ':', '!', '?') or token == url_quote)) or
                    _URL_CHARS.fullmatch(token) is None):
                return True
        else:
            if _URL_CHARS.fullmatch(token) is None or token == '.' or token == url_quote:
                return True
        return False

    @staticmethod
    def is_currency_expression(token):
        return _CURRENCY_EXPRESSION.fullmatch(token) is not None

    @staticmethod
    def split_currency_expression(token):
        out = []
        for m in _CURRENCY_EXPRESSION.finditer(token):
            if m.group(1) is not None and m.group(2) is not None:
                out.extend((m.group(1), m.group(2)))
            elif m.group(3) is not None and m.group(4) is not None:
                out.extend((m.group(3), m.group(4)))
        if not out:
            out.append(token)
        return out
