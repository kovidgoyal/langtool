"""Reader for morfologik finite state automata dictionaries (.dict files).

Port of the relevant parts of morfologik-fsa (FSA5, CFSA2) and
morfologik-stemming (DictionaryLookup, DictionaryMetadata and the sequence
encoders). Only lookups are supported, not building of dictionaries.
"""

import os
import sys
import threading

__all__ = ['Dictionary', 'DictionaryMetadata', 'read_properties']

FSA_MAGIC = b'\\fsa'
VERSION_FSA5 = 5
VERSION_CFSA = 0xc5
VERSION_CFSA2 = 0xc6

# FSA flags
FLEXIBLE, STOPBIT, NEXTBIT = 1, 2, 4
NUMBERS = 1 << 8


def read_properties(text):
    """Parse a Java .properties file, returns a dict."""
    props = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].lstrip()
        i += 1
        if not line or line[0] in '#!':
            continue
        # line continuations
        while line.endswith('\\') and not line.endswith('\\\\') and i < len(lines):
            line = line[:-1] + lines[i].lstrip()
            i += 1
        # split key/value
        key_chars = []
        j = 0
        n = len(line)
        while j < n:
            c = line[j]
            if c == '\\' and j + 1 < n:
                key_chars.append(line[j:j + 2])
                j += 2
                continue
            if c in '=: \t\f':
                break
            key_chars.append(c)
            j += 1
        while j < n and line[j] in ' \t\f':
            j += 1
        if j < n and line[j] in '=:':
            j += 1
        while j < n and line[j] in ' \t\f':
            j += 1
        key = _unescape(''.join(key_chars))
        props[key] = _unescape(line[j:])
    return props


def _unescape(s):
    if '\\' not in s:
        return s
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            d = s[i + 1]
            if d == 'u' and i + 5 < n + 0:
                try:
                    out.append(chr(int(s[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            out.append({'t': '\t', 'n': '\n', 'r': '\r', 'f': '\f'}.get(d, d))
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _parse_conversion_pairs(value):
    import re
    pairs = {}
    if value is None:
        return pairs
    for sp in re.split(r',\s*', value):
        two = sp.strip().split(' ')
        if len(two) == 2:
            if two[0] not in pairs:
                pairs[two[0]] = two[1]
        else:
            raise ValueError('Bad conversion pairs: %r' % value)
    return pairs


_ENCODING_ALIASES = {'utf8': 'utf-8'}


class DictionaryMetadata:

    def __init__(self, props):
        self.props = props
        enc = props.get('fsa.dict.encoding', 'UTF-8').strip()
        self.encoding = _ENCODING_ALIASES.get(enc.lower(), enc)
        sep = props.get('fsa.dict.separator', '+')
        if len(sep) != 1:
            raise ValueError('Separator must be a single character: %r' % sep)
        self.separator_char = sep
        self.separator = sep.encode(self.encoding)
        if len(self.separator) != 1:
            raise ValueError('Separator must encode to a single byte')
        self.separator = self.separator[0]
        if 'fsa.dict.encoder' in props:
            self.encoder = props['fsa.dict.encoder'].strip().upper()
        else:
            if props.get('fsa.dict.uses-infixes', 'false').lower() == 'true':
                self.encoder = 'INFIX'
            elif props.get('fsa.dict.uses-prefixes', 'false').lower() == 'true':
                self.encoder = 'PREFIX'
            elif props.get('fsa.dict.uses-suffixes', 'true').lower() == 'true':
                self.encoder = 'SUFFIX'
            else:
                self.encoder = 'NONE'
        if self.encoder not in ('SUFFIX', 'PREFIX', 'INFIX', 'NONE'):
            raise ValueError('Unknown encoder: %s' % self.encoder)
        self.frequency_included = props.get('fsa.dict.frequency-included', 'false').strip().lower() == 'true'
        self.input_conversion = _parse_conversion_pairs(props.get('fsa.dict.input-conversion'))
        self.output_conversion = _parse_conversion_pairs(props.get('fsa.dict.output-conversion'))
        self.locale = props.get('fsa.dict.speller.locale') or props.get('fsa.dict.locale')

    @classmethod
    def read(cls, path):
        with open(path, 'rb') as f:
            raw = f.read()
        return cls(read_properties(raw.decode('utf-8')))


def apply_replacements(word, replacements):
    for key, val in replacements.items():
        idx = word.find(key)
        while idx != -1:
            word = word[:idx] + val + word[idx + len(key):]
            idx = word.find(key, idx + len(val))
    return word


class _FSA5:

    def __init__(self, data, offset):
        self.filler = data[offset]
        self.annotation = data[offset + 1]
        hgtl = data[offset + 2]
        self.node_data_length = (hgtl >> 4) & 0x0f
        self.gtl = hgtl & 0x0f
        self.arcs = data[offset + 3:]
        self.flags = FLEXIBLE | STOPBIT | NEXTBIT | (NUMBERS if (hgtl & 0xf0) else 0)
        epsilon = self._skip_arc(self.first_arc(0))
        self.root = self.destination(self.first_arc(epsilon))

    def first_arc(self, node):
        return self.node_data_length + node

    def next_arc(self, arc):
        if self.arcs[arc + 1] & 2:  # last arc
            return 0
        return self._skip_arc(arc)

    def _skip_arc(self, offset):
        return offset + (2 if self.arcs[offset + 1] & 4 else 1 + self.gtl)

    def label(self, arc):
        return self.arcs[arc]

    def is_final(self, arc):
        return (self.arcs[arc + 1] & 1) != 0

    def destination(self, arc):
        arcs = self.arcs
        if arcs[arc + 1] & 4:
            return self._skip_arc(arc)
        r = 0
        for i in range(self.gtl - 1, -1, -1):
            r = (r << 8) | arcs[arc + 1 + i]
        return r >> 3

    def get_arc(self, node, lbl):
        arcs = self.arcs
        arc = self.node_data_length + node
        while True:
            if arcs[arc] == lbl:
                return arc
            if arcs[arc + 1] & 2:
                return 0
            arc = arc + (2 if arcs[arc + 1] & 4 else 1 + self.gtl)


class _CFSA:
    """The (deprecated) CFSA format, version 0xc5."""

    def __init__(self, data, offset):
        hgtl = data[offset + 2]
        if hgtl & 0xf0:
            self.node_data_length = (hgtl >> 4) & 0x0f
        else:
            self.node_data_length = 0
        self.gtl = hgtl & 0x0f
        self.label_mapping = data[offset + 3:offset + 3 + 32]
        self.arcs = data[offset + 3 + 32:]
        epsilon = self._skip_arc(self.first_arc(0))
        self.root = self.destination(self.first_arc(epsilon))

    def first_arc(self, node):
        return self.node_data_length + node

    def next_arc(self, arc):
        if self.arcs[arc] & 2:
            return 0
        return self._skip_arc(arc)

    def _skip_arc(self, offset):
        f = self.arcs[offset]
        if f & 4:
            return offset + (1 if (f & 0xf8) else 2)
        return offset + 1 + self.gtl

    def label(self, arc):
        f = self.arcs[arc]
        if (f & 4) and (f & 0xf8):
            return self.label_mapping[(f >> 3) & 0x1f]
        return self.arcs[arc + 1]

    def is_final(self, arc):
        return (self.arcs[arc] & 1) != 0

    def destination(self, arc):
        arcs = self.arcs
        if arcs[arc] & 4:
            return self._skip_arc(arc)
        r = 0
        for i in range(self.gtl - 1, 0, -1):
            r = (r << 8) | arcs[arc + 1 + i]
        r = (r << 8) | arcs[arc]
        return r >> 3

    def get_arc(self, node, lbl):
        arc = self.first_arc(node)
        while True:
            if self.label(arc) == lbl:
                return arc
            if self.arcs[arc] & 2:
                return 0
            arc = self._skip_arc(arc)


class _CFSA2:

    BIT_TARGET_NEXT = 1 << 7
    BIT_LAST_ARC = 1 << 6
    BIT_FINAL_ARC = 1 << 5
    LABEL_INDEX_MASK = (1 << 5) - 1

    def __init__(self, data, offset):
        flag_bits = (data[offset] << 8) | data[offset + 1]
        self.flags = flag_bits
        self.has_numbers = bool(flag_bits & NUMBERS)
        n = data[offset + 2]
        self.label_mapping = data[offset + 3:offset + 3 + n]
        self.arcs = data[offset + 3 + n:]
        self.root = self.destination(self.first_arc(0))

    def first_arc(self, node):
        if self.has_numbers:
            arcs = self.arcs
            while arcs[node] & 0x80:
                node += 1
            return node + 1
        return node

    def next_arc(self, arc):
        if self.arcs[arc] & self.BIT_LAST_ARC:
            return 0
        return self._skip_arc(arc)

    def _skip_arc(self, offset):
        arcs = self.arcs
        flag = arcs[offset]
        offset += 1
        if (flag & 0x1f) == 0:
            offset += 1
        if (flag & 0x80) == 0:
            while arcs[offset] & 0x80:
                offset += 1
            offset += 1
        return offset

    def label(self, arc):
        idx = self.arcs[arc] & 0x1f
        if idx > 0:
            return self.label_mapping[idx]
        return self.arcs[arc + 1]

    def is_final(self, arc):
        return (self.arcs[arc] & self.BIT_FINAL_ARC) != 0

    def destination(self, arc):
        arcs = self.arcs
        if arcs[arc] & 0x80:
            while not (arcs[arc] & 0x40):
                arc = self._skip_arc(arc)
            return self._skip_arc(arc)
        off = arc + (2 if (arcs[arc] & 0x1f) == 0 else 1)
        b = arcs[off]
        value = b & 0x7f
        shift = 7
        while b & 0x80:
            off += 1
            b = arcs[off]
            value |= (b & 0x7f) << shift
            shift += 7
        return value

    def get_arc(self, node, lbl):
        arc = self.first_arc(node)
        arcs = self.arcs
        mapping = self.label_mapping
        while True:
            flag = arcs[arc]
            idx = flag & 0x1f
            if (mapping[idx] if idx else arcs[arc + 1]) == lbl:
                return arc
            if flag & 0x40:
                return 0
            arc = self._skip_arc(arc)


def read_fsa(data):
    if data[:4] != FSA_MAGIC:
        raise ValueError('Not an FSA file')
    version = data[4]
    if version == VERSION_FSA5:
        return _FSA5(data, 5)
    if version == VERSION_CFSA2:
        return _CFSA2(data, 5)
    if version == VERSION_CFSA:
        return _CFSA(data, 5)
    raise ValueError('Unsupported FSA version: 0x%02x' % version)


def _decode_suffix(source, encoded):
    trunc = (encoded[0] - 65) & 0xff
    if trunc == 255:
        trunc = len(source)
    return source[:len(source) - trunc] + encoded[1:]


def _decode_prefix(source, encoded):
    tp = (encoded[0] - 65) & 0xff
    ts = (encoded[1] - 65) & 0xff
    if tp == 255 or ts == 255:
        tp = len(source)
        ts = 0
    return source[tp:len(source) - ts] + encoded[2:]


def _decode_infix(source, encoded):
    ii = (encoded[0] - 65) & 0xff
    il = (encoded[1] - 65) & 0xff
    ts = (encoded[2] - 65) & 0xff
    if il == 255 or ts == 255:
        ii = 0
        il = len(source)
        ts = 0
    return source[:ii] + source[ii + il:len(source) - ts] + encoded[3:]


def _decode_none(source, encoded):
    return encoded


_DECODERS = {'SUFFIX': (_decode_suffix, 1), 'PREFIX': (_decode_prefix, 2), 'INFIX': (_decode_infix, 3),
             'NONE': (_decode_none, 0)}


class Dictionary:
    """A morfologik dictionary: maps word forms to (lemma, tag) pairs."""

    def __init__(self, dict_path, info_path=None):
        if info_path is None:
            info_path = os.path.splitext(dict_path)[0] + '.info'
        self.path = dict_path
        self.metadata = DictionaryMetadata.read(info_path)
        with open(dict_path, 'rb') as f:
            data = f.read()
        self.fsa = read_fsa(data)
        self._decode, self._prefix_bytes = _DECODERS[self.metadata.encoder]
        self._native = None
        try:
            from . import _speedups
        except ImportError:
            pass
        else:
            fsa = self.fsa
            kind = 5 if isinstance(fsa, _FSA5) else (0xc5 if isinstance(fsa, _CFSA) else 0xc6)
            self._native = _speedups.FSADict(
                bytes(fsa.arcs), kind, fsa.root,
                getattr(fsa, 'gtl', 0), getattr(fsa, 'node_data_length', 0),
                bytes(getattr(fsa, 'label_mapping', b'')), bool(getattr(fsa, 'has_numbers', False)),
                self.metadata.separator, self._prefix_bytes, self.metadata.encoder)
        self._cache = {}
        self._lock = threading.Lock()

    def lookup(self, word):
        """Return a list of (lemma, tag) tuples for word. Tags may be None."""
        r = self._cache.get(word)
        if r is not None:
            return r
        r = self._lookup(word)
        if len(self._cache) > 200000:
            self._cache.clear()
        self._cache[word] = r
        return r

    def _lookup(self, word):
        md = self.metadata
        if md.input_conversion:
            word = apply_replacements(word, md.input_conversion)
        if md.separator_char in word:
            return ()
        try:
            wb = word.encode(md.encoding)
        except UnicodeEncodeError:
            return ()
        if self._native is not None:
            raw = self._native.lookup(wb)
        else:
            raw = self._raw_lookup(wb)
        if not raw:
            return ()
        enc = md.encoding
        freq = md.frequency_included
        out = []
        for stem, tag in raw:
            stem = stem.decode(enc, 'replace')
            if tag is not None:
                tag = tag.decode(enc, 'replace')
                if freq and len(tag) > 1:
                    tag = tag[:-1]
            if md.output_conversion:
                # morfologik applies output conversion to the word, not the stem
                pass
            out.append((stem, tag))
        return tuple(out)

    def _raw_lookup(self, wb):
        """Returns list of (stem bytes, tag bytes or None)."""
        fsa = self.fsa
        node = fsa.root
        last = len(wb) - 1
        for i, b in enumerate(wb):
            arc = fsa.get_arc(node, b)
            if arc == 0:
                return ()
            if i == last and fsa.is_final(arc):  # exact match, no separator
                return ()
            node = fsa.destination(arc)
            if node == 0:  # terminal arc
                return ()
        sep = self.metadata.separator
        arc = fsa.get_arc(node, sep)
        if arc == 0 or fsa.is_final(arc):
            return ()
        start = fsa.destination(arc)
        if start == 0:
            return ()
        results = []
        prefix_bytes = self._prefix_bytes
        decode = self._decode
        for seq in self._sequences(start):
            sep_pos = prefix_bytes
            n = len(seq)
            while sep_pos < n and seq[sep_pos] != sep:
                sep_pos += 1
            stem = decode(wb, seq[:sep_pos])
            tag = seq[sep_pos + 1:] if sep_pos + 1 < n else None
            if tag is not None and len(tag) == 0:
                tag = None
            results.append((bytes(stem), bytes(tag) if tag is not None else None))
        return results

    def _sequences(self, node):
        """Iterate over all byte sequences accepted from node, in the same
        order as morfologik's ByteSequenceIterator."""
        fsa = self.fsa
        buf = bytearray()
        stack = [fsa.first_arc(node)]
        while stack:
            arc = stack[-1]
            depth = len(stack) - 1
            if arc == 0:
                stack.pop()
                continue
            stack[-1] = fsa.next_arc(arc)
            del buf[depth:]
            buf.append(fsa.label(arc))
            dest = fsa.destination(arc)
            final = fsa.is_final(arc)
            if dest != 0:
                stack.append(fsa.first_arc(dest))
            if final:
                yield bytes(buf)

    def count_entries(self):
        """Return (entries, entries_without_tag): the number of entries that
        iter_all() yields and how many of them have no tag (None), computed
        on the automaton (memoized per node) without enumerating the entries,
        which is much faster for dictionaries with millions of word forms."""
        fsa = self.fsa
        sep = self.metadata.separator
        p = self._prefix_bytes
        # states: -1 in the word; 0..p bytes of the encoded stem read (the
        # tag separator is only looked for after the p prefix bytes); p + 1
        # tag separator just read (empty tag so far); p + 2 in the tag
        in_word, empty_tag, in_tag = -1, p + 1, p + 2

        def step(state, b):
            if state == in_word:
                return 0 if b == sep else in_word
            if state <= p:
                if state == p and b == sep:
                    return empty_tag
                return min(state + 1, p)
            return in_tag

        memo = {}

        def count(node, state):
            key = (node, state)
            r = memo.get(key)
            if r is not None:
                return r
            total = untagged = 0
            arc = fsa.first_arc(node)
            while arc:
                s2 = step(state, fsa.label(arc))
                if fsa.is_final(arc) and s2 != in_word:
                    total += 1
                    if s2 != in_tag:
                        untagged += 1
                dest = fsa.destination(arc)
                if dest:
                    t, u = count(dest, s2)
                    total += t
                    untagged += u
                arc = fsa.next_arc(arc)
            memo[key] = r = (total, untagged)
            return r

        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old_limit, 20000))
        try:
            return count(fsa.root, in_word)
        finally:
            sys.setrecursionlimit(old_limit)

    def iter_all(self):
        """Iterate over all (word, lemma, tag) entries in the dictionary."""
        md = self.metadata
        sep = md.separator
        enc = md.encoding
        for seq in self._sequences(self.fsa.root):
            i = seq.find(bytes((sep,)))
            if i < 0:
                continue
            word = seq[:i]
            rest = seq[i + 1:]
            j = rest.find(bytes((sep,)), self._prefix_bytes)
            if j < 0:
                enc_stem, tag = rest, None
            else:
                enc_stem, tag = rest[:j], rest[j + 1:] or None
            stem = self._decode(word, enc_stem)
            t = tag.decode(enc, 'replace') if tag is not None else None
            if t is not None and md.frequency_included and len(t) > 1:
                t = t[:-1]
            yield word.decode(enc, 'replace'), bytes(stem).decode(enc, 'replace'), t
