"""Localized messages (port of the MessagesBundle ResourceBundle handling of
LanguageTool, with fallback to English for missing keys)."""

import os
from functools import lru_cache

from . import resources
from .fsa import read_properties


@lru_cache()
def _load(name):
    path = resources.path('data', 'messages', name)
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('iso-8859-1')
    return read_properties(text)


class Messages:
    """A message bundle for a language, e.g. Messages('de', 'CH')"""

    def __init__(self, lang='en', country=None):
        chain = []
        if country:
            chain.append(_load('MessagesBundle_%s_%s.properties' % (lang, country)))
        chain.append(_load('MessagesBundle_%s.properties' % lang))
        chain.append(_load('MessagesBundle.properties'))
        chain.append(_load('MessagesBundle_en.properties'))
        self.chain = chain

    def get(self, key, default=None):
        for d in self.chain:
            v = d.get(key)
            if v is not None:
                return v
        return default

    def __getitem__(self, key):
        v = self.get(key)
        if v is None:
            raise KeyError(key)
        return v

    def format(self, key, *args):
        return message_format(self[key], *args)


@lru_cache()
def messages_for(lang, country=None):
    return Messages(lang, country)


def message_format(pattern, *args):
    """java.text.MessageFormat.format for simple {n} arguments."""
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "'":
            if i + 1 < n and pattern[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            j = pattern.find("'", i + 1)
            if j < 0:
                out.append(pattern[i + 1:])
                break
            out.append(pattern[i + 1:j])
            i = j + 1
            continue
        if c == '{':
            j = pattern.find('}', i)
            if j > 0:
                spec = pattern[i + 1:j].split(',')[0].strip()
                if spec.isdigit():
                    k = int(spec)
                    if k < len(args):
                        a = args[k]
                        if isinstance(a, int) and not isinstance(a, bool):
                            a = '{:,}'.format(a)
                        out.append(str(a))
                    else:
                        out.append(pattern[i:j + 1])
                    i = j + 1
                    continue
        out.append(c)
        i += 1
    return ''.join(out)
