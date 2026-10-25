"""The Sen Japanese morphological analyzer of lucene-gosen 6.2.1 (package
net.java.sen), a pure Python port of the parts that LanguageTool's
JapaneseWordTokenizer uses: SenFactory (reading the compiled IPADIC
dictionary: header.sen, connectionCost.sen, partOfSpeech.sen, token.sen,
trie.sen, posIndex.sen), Dictionary, DictionaryUtil, TrieSearcher, CToken,
Node, Morpheme, Token, Sentence (its ConstrainedIterator), Viterbi,
Tokenizer, tokenizers.ja.JapaneseTokenizer and StringTagger (without
StreamFilters, which JapaneseWordTokenizer does not add).

The dictionary files are part of the lucene-gosen-6.2.1-ipadic.jar on Maven
Central; they are downloaded by langtool.dictionaries (as ja/*.sen).

Strings are processed as Java strings (UTF-16 code units): characters
outside the BMP are two units (two unknown tokens of one surrogate each, like
in Java; JapaneseWordTokenizer joins them again). The token start and length
are in UTF-16 code units. Reading constraints and breaking ignore spans of Sentence are only
set by StreamFilters, so they are always empty here and are not ported.
"""

import array
import struct
import sys
import threading

from ...tools import java_split

UNKNOWN_POS = '未知語'  # SenFactory.unknownPOS

_INT_MAX = 2147483647
_INT_MIN = -2147483648
_CTOKEN_SIZE = 14  # CToken.SIZE
_ctoken_struct = struct.Struct('>hhhhhi')
_WHITESPACE = (0x20, 0x09, 0x0d, 0x0a)  # ' ', '\t', '\r', '\n' (Sentence)


class TooManyResultsError(IndexError):
    """The ArrayIndexOutOfBoundsException that Dictionary.commonPrefixSearch
    throws when more than 255 morphemes start at one position (its result
    arrays have 256 elements)."""


def _java_str(s):
    """A Python string from a string of UTF-16 code units (surrogate pairs are
    joined, unpaired surrogates are kept)"""
    for c in s:
        if '\ud800' <= c <= '\udfff':
            return s.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'surrogatepass')
    return s


def _utf16_units(s):
    """A Python string as a string of UTF-16 code units (one character per
    unit, characters outside the BMP as surrogate pairs)"""
    if not s or max(s) <= '\uffff':
        return s
    return ''.join(_split_astral(c) for c in s)


def _split_astral(c):
    o = ord(c)
    if o <= 0xffff:
        return c
    o -= 0x10000
    return chr(0xd800 + (o >> 10)) + chr(0xdc00 + (o & 0x3ff))


def _read_utf(data, pos):
    """DataInputStream.readUTF (modified UTF-8) at pos: (string, new pos)"""
    n, = struct.unpack_from('>H', data, pos)
    b = data[pos + 2:pos + 2 + n]
    if b'\xc0\x80' in b:
        b = b.replace(b'\xc0\x80', b'\x00')
    return _java_str(b.decode('utf-8', 'surrogatepass')), pos + 2 + n


def _read_vint(data, pos):
    """DictionaryUtil.readVInt: (value, new pos)"""
    b = data[pos]
    i = b & 0x7f
    shift = 7
    while b & 0x80:
        pos += 1
        b = data[pos]
        i |= (b & 0x7f) << shift
        shift += 7
    if i > _INT_MAX:
        i -= 1 << 32
    return i, pos + 1


def _read_string(data, pos, length):
    """DictionaryUtil.readString (length big endian chars): (string, new pos)"""
    end = pos + 2 * length
    return _java_str(data[pos:end].decode('utf-16-be', 'surrogatepass')), end


def _read_katakana(data, pos, length):
    """DictionaryUtil.readKatakana: (string, new pos)"""
    end = pos + length
    return ''.join(chr(0x30a0 + b) for b in data[pos:end]), end


def _load_array(path, typecode):
    a = array.array(typecode)
    with open(path, 'rb') as f:
        a.frombytes(f.read())
    if sys.byteorder == 'little':
        a.byteswap()
    return a


class SenDictionaryData:
    """The data files of a compiled dictionary (SenFactory): the connection
    cost matrix, part of speech info, tokens, trie and the POS /
    conjugation indexes."""

    def __init__(self, paths):
        """paths: function returning the file path for a file name like
        'header.sen'"""
        with open(paths('header.sen'), 'rb') as f:
            sizes = struct.unpack('>4i', f.read(16))
        self.costs = _load_array(paths('connectionCost.sen'), 'h')
        with open(paths('partOfSpeech.sen'), 'rb') as f:
            self.pos = f.read()
        with open(paths('token.sen'), 'rb') as f:
            self.tokens = f.read()
        self.trie = _load_array(paths('trie.sen'), 'i')
        for name, data, size in (('connectionCost.sen', self.costs, sizes[0] // 2),
                                 ('partOfSpeech.sen', self.pos, sizes[1]),
                                 ('token.sen', self.tokens, sizes[2]), ('trie.sen', self.trie, sizes[3] // 4)):
            if len(data) != size:
                raise IOError('%s: expected %d elements, found %d' % (name, size, len(data)))
        with open(paths('posIndex.sen'), 'rb') as f:
            data = f.read()
        pos = 0
        indexes = []
        for _ in range(3):
            n, = struct.unpack_from('>H', data, pos)
            pos += 2
            index = []
            for _ in range(n):
                s, pos = _read_utf(data, pos)
                index.append(s)
            indexes.append(index)
        self.pos_index, self.conj_type_index, self.conj_form_index = indexes
        self.ctokens = {}  # cache of the CTokens read from token.sen, by index


class CToken:
    """net.java.sen.dictionary.CToken: a dictionary entry (connection
    attributes, length, cost, index of its part of speech info). The
    CTokens of the dictionary are cached and share the Morpheme of their
    part of speech info (morpheme, created by the JapaneseTokenizer)."""

    __slots__ = ('rc_attr2', 'rc_attr1', 'lc_attr', 'length', 'cost', 'part_of_speech_index', 'morpheme')

    def __init__(self, values):
        (self.rc_attr2, self.rc_attr1, self.lc_attr, self.length, self.cost,
         self.part_of_speech_index) = values
        self.morpheme = None


class Dictionary:
    """net.java.sen.dictionary.Dictionary"""

    def __init__(self, data):
        self.data = data
        costs = data.costs
        self.connection_size1, self.connection_size2, self.connection_size3 = costs[0], costs[1], costs[2]
        expected = 3 + self.connection_size1 * self.connection_size2 * self.connection_size3
        if expected != len(costs):
            raise RuntimeError('Expected connection cost file to be %d bytes, but was %d'
                               % (2 * expected, 2 * len(costs)))
        # connectionCostBuffer.slice() after the three sizes: the matrix
        # starts at index 3 of connection_costs (not copied)
        self.connection_costs = costs
        self.part_of_speech_info = data.pos
        self.token_data = data.tokens
        self.trie = data.trie
        self.trie_limit = len(data.trie)
        self.bos_token = CToken(_ctoken_struct.unpack_from(data.tokens, 0))
        self.eos_token = CToken(_ctoken_struct.unpack_from(data.tokens, _CTOKEN_SIZE))
        self.unknown_token = CToken(_ctoken_struct.unpack_from(data.tokens, 2 * _CTOKEN_SIZE))
        self.pos_index = data.pos_index
        self.conj_type_index = data.conj_type_index
        self.conj_form_index = data.conj_form_index
        self._ctokens = data.ctokens

    def get_cost(self, l_node2, l_node, r_node):
        position = self.connection_size3 * (self.connection_size2 * l_node2.rc_attr2 + l_node.rc_attr1) + \
            r_node.lc_attr
        return self.connection_costs[3 + position] + r_node.dictionary_cost

    def common_prefix_search(self, chars, start, end):
        """Dictionary.commonPrefixSearch with TrieSearcher.commonPrefixSearch:
        the CTokens of the morphemes that are prefixes of chars[start:end]
        (UTF-16 code units as ints; end is where the iterator's hasNext()
        becomes false)"""
        trie = self.trie
        limit = self.trie_limit
        results = []
        b = trie[0]
        i = start
        while i < end:
            p = b
            n = trie[p << 1]
            if n < 0 and b == trie[(p << 1) + 1]:
                results.append(-n - 1)
            p = b + chars[i] + 1
            i += 1
            if ((p << 1) + 1) >= limit:
                break
            if b == trie[(p << 1) + 1]:
                b = trie[p << 1]
            else:
                break
        else:
            p = b
            n = trie[p << 1]
            if n < 0 and b == trie[(p << 1) + 1]:
                results.append(-n - 1)
        if len(results) > 256:
            raise TooManyResultsError('trie search results')
        out = []
        ctokens = self._ctokens
        token_data = self.token_data
        for r in results:
            k = r & 0xff
            p = r >> 8
            for j in range(p + 3, p + 3 + k):
                t = ctokens.get(j)
                if t is None:
                    t = ctokens[j] = CToken(_ctoken_struct.unpack_from(token_data, j * _CTOKEN_SIZE))
                out.append(t)
        if len(out) > 255:
            raise TooManyResultsError('morphemes')
        return out


class Morpheme:
    """net.java.sen.dictionary.Morpheme: the part of speech info of a
    morpheme, read lazily from partOfSpeech.sen"""

    __slots__ = ('_dictionary', '_part_of_speech_index', '_loaded', '_conjugational_type', '_conjugational_form',
                 '_basic_form', '_readings', '_pronunciations', '_part_of_speech', 'additional_information')

    _NONE, _BASIC, _FULL = 0, 1, 2

    def __init__(self, dictionary=None, part_of_speech_index=0, part_of_speech=None, conjugational_type=None,
                 conjugational_form=None, basic_form=None, readings=None, pronunciations=None,
                 additional_information=None):
        """Morpheme(dictionary, partOfSpeechIndex) or (without dictionary)
        Morpheme(partOfSpeech, conjugationalType, conjugationalForm, basicForm,
        readings, pronunciations, additionalInformation)"""
        self._dictionary = dictionary
        self._part_of_speech_index = part_of_speech_index
        self._part_of_speech = part_of_speech
        self._conjugational_type = conjugational_type
        self._conjugational_form = conjugational_form
        self._basic_form = basic_form
        self._readings = list(readings) if readings is not None else []
        self._pronunciations = list(pronunciations) if pronunciations is not None else []
        self.additional_information = additional_information
        self._loaded = self._NONE if dictionary is not None else self._FULL

    def _load(self, requested):
        if self._loaded >= requested:
            return
        d = self._dictionary
        data = d.part_of_speech_info
        pos = self._part_of_speech_index
        if self._loaded == self._NONE:
            i, pos = _read_vint(data, pos)
            self._part_of_speech = d.pos_index[i]
            i, pos = _read_vint(data, pos)
            self._conjugational_type = d.conj_type_index[i]
            i, pos = _read_vint(data, pos)
            self._conjugational_form = d.conj_form_index[i]
            length, pos = _read_vint(data, pos)
            if length == 0:
                self._basic_form = '*'  # basic form is the same as surface form
            else:
                self._basic_form, pos = _read_string(data, pos, length)
        else:
            for _ in range(3):
                _, pos = _read_vint(data, pos)
            length, pos = _read_vint(data, pos)
            pos += 2 * length
        self._loaded = self._BASIC
        if requested == self._FULL:
            reading_data, pos = _read_vint(data, pos)
            num_readings = reading_data >> 1
            read = _read_string if reading_data & 1 else _read_katakana
            self._readings = []
            self._pronunciations = []
            for _ in range(num_readings):
                length, pos = _read_vint(data, pos)
                reading, pos = read(data, pos, length >> 1)
                self._readings.append(reading)
                if length & 1:
                    pronunciation_length, pos = _read_vint(data, pos)
                    pronunciation, pos = read(data, pos, pronunciation_length)
                    self._pronunciations.append(pronunciation)
                else:
                    self._pronunciations.append(reading)
            self._loaded = self._FULL

    @property
    def conjugational_type(self):
        self._load(self._BASIC)
        return self._conjugational_type

    @property
    def conjugational_form(self):
        self._load(self._BASIC)
        return self._conjugational_form

    @property
    def basic_form(self):
        self._load(self._BASIC)
        return self._basic_form

    @property
    def readings(self):
        self._load(self._FULL)
        return self._readings

    @property
    def pronunciations(self):
        self._load(self._FULL)
        return self._pronunciations

    @property
    def part_of_speech(self):
        self._load(self._BASIC)
        return self._part_of_speech

    def __str__(self):
        self._load(self._FULL)
        parts = java_split(self._part_of_speech, '-')
        out = [parts[i] if i < len(parts) else '*' for i in range(4)]
        for v in (self._conjugational_type, self._conjugational_form, self._basic_form):
            out.append('null' if v is None else v)
        out += [self._readings[0] if self._readings else 'null',
                self._pronunciations[0] if self._pronunciations else 'null']
        return ','.join(out)


class Node:
    """net.java.sen.dictionary.Node: a node of the Viterbi lattice. cbase is
    the index in Dictionary.connection_costs of the row of the connection
    cost matrix for the node and its prev node as left nodes
    (3 + size3 * (size2 * prev.rc_attr2 + rc_attr1), computed when the node
    is added to the lattice)."""

    __slots__ = ('rc_attr2', 'rc_attr1', 'lc_attr', 'dictionary_cost', 'prev', 'next', 'lnext', 'rnext',
                 'morpheme', 'start', 'length', 'span', 'cost', 'cbase')

    def __init__(self, ctoken=None):
        if ctoken is not None:
            self.rc_attr2 = ctoken.rc_attr2
            self.rc_attr1 = ctoken.rc_attr1
            self.lc_attr = ctoken.lc_attr
            self.dictionary_cost = ctoken.cost
        else:
            self.rc_attr2 = self.rc_attr1 = self.lc_attr = self.dictionary_cost = 0
        self.prev = self.next = self.lnext = self.rnext = self.morpheme = None
        self.start = self.length = self.span = self.cost = 0
        self.cbase = 0

    def clone(self):
        n = Node.__new__(Node)
        n.rc_attr2 = self.rc_attr2
        n.rc_attr1 = self.rc_attr1
        n.lc_attr = self.lc_attr
        n.dictionary_cost = self.dictionary_cost
        n.prev = self.prev
        n.next = self.next
        n.lnext = self.lnext
        n.rnext = self.rnext
        n.morpheme = self.morpheme
        n.start = self.start
        n.length = self.length
        n.span = self.span
        n.cost = self.cost
        n.cbase = self.cbase
        return n


def _new_node(ctoken, start, length, span):
    """new Node() with setCToken(ctoken) and the given start, length and span
    (a faster Node(ctoken))"""
    n = _node_new(Node)
    n.rc_attr2 = ctoken.rc_attr2
    n.rc_attr1 = ctoken.rc_attr1
    n.lc_attr = ctoken.lc_attr
    n.dictionary_cost = ctoken.cost
    n.prev = n.next = n.lnext = n.rnext = n.morpheme = None
    n.start = start
    n.length = length
    n.span = span
    n.cost = n.cbase = 0
    return n


_node_new = Node.__new__


class Token:
    """net.java.sen.dictionary.Token: a morpheme of the analysed text"""

    __slots__ = ('surface', 'cost', 'start', 'length', 'morpheme', 'sentence_start')

    def __init__(self, surface, cost, start, length, morpheme):
        self.surface = surface
        self.cost = cost
        self.start = start
        self.length = length
        self.morpheme = morpheme
        self.sentence_start = False

    def end(self):
        return self.start + self.length

    def __repr__(self):
        return self.surface


# JapaneseTokenizer character classes
OTHER = 0x80
SPACE = 0x81
KANJI = 0x82
KATAKANA = 0x83
HIRAGANA = 0x84
HALF_WIDTH = 0x85


def _ascii_char_types():
    """Character.getType(Character.toLowerCase(c)) for c <= 0x7F (the
    general categories as Java's constants; ASCII has no unassigned
    characters, upper case letters become lower case letters)"""
    import unicodedata
    java_types = {'Lu': 1, 'Ll': 2, 'Nd': 9, 'Zs': 12, 'Cc': 15, 'Pd': 20, 'Ps': 21, 'Pe': 22, 'Pc': 23,
                  'Po': 24, 'Sm': 25, 'Sc': 26, 'Sk': 27}
    out = []
    for c in range(0x80):
        if c in (0x20, 0x09, 0x0d, 0x0a):
            out.append(SPACE)
        else:
            out.append(java_types[unicodedata.category(chr(c).lower())])
    return out


_ASCII_TYPES = _ascii_char_types()


def get_char_class(c):
    """JapaneseTokenizer.getCharClass for the code unit c (an int)"""
    if c <= 0x7f:
        return _ASCII_TYPES[c]
    if 0x3040 <= c <= 0x309f:
        return HIRAGANA
    if 0x30a0 <= c <= 0x30ff and c != 0x30fb:
        return KATAKANA
    if 0x4e00 <= c <= 0x9fff:
        return KANJI
    if 0xff00 <= c <= 0xffef:
        return HALF_WIDTH
    return OTHER


class JapaneseTokenizer:
    """net.java.sen.tokenizers.ja.JapaneseTokenizer (with its superclass
    net.java.sen.dictionary.Tokenizer): dictionary lookup at a position of
    the sentence, synthesizing unknown morphemes"""

    def __init__(self, dictionary, unknown_part_of_speech_description=UNKNOWN_POS,
                 tokenize_unknown_katakana=False):
        self.dictionary = dictionary
        self.unknown_part_of_speech_description = unknown_part_of_speech_description
        self.bos_node = Node(dictionary.bos_token)
        self.eos_node = Node(dictionary.eos_token)
        unknown = CToken((dictionary.unknown_token.rc_attr2, dictionary.unknown_token.rc_attr1,
                          dictionary.unknown_token.lc_attr, dictionary.unknown_token.length, 30000,
                          dictionary.unknown_token.part_of_speech_index))
        self.unknown_ctoken = unknown
        self.unknown_morpheme = Morpheme(part_of_speech=unknown_part_of_speech_description, basic_form='*')
        self.tokenize_unknown_katakana = tokenize_unknown_katakana

    def get_bos_node(self):
        bos = self.bos_node.clone()
        bos.prev = self.bos_node.clone()  # why does it clone its prev pointer also?
        return bos

    def get_eos_node(self):
        return self.eos_node.clone()

    def get_unknown_node(self, start, length, span):
        node = _new_node(self.unknown_ctoken, start, length, span)
        node.morpheme = self.unknown_morpheme
        return node

    def _find_unknown_token(self, chars, start, end):
        length = 0
        if start < end:
            char_class = get_char_class(chars[start])
            if char_class == HIRAGANA or char_class == KANJI or char_class == OTHER or \
                    (char_class == KATAKANA and self.tokenize_unknown_katakana):
                length = 1
            else:
                length = 1
                i = start + 1
                while i < end and get_char_class(chars[i]) == char_class:
                    length += 1
                    i += 1
        return length

    def lookup(self, chars, origin, end, skipped):
        """lookup(iterator, surface) for the iterator at origin (chars:
        UTF-16 code units as ints, end: the end of the run of non-space
        characters at origin, skipped: iterator.skippedCharCount())"""
        result = None
        char_class = get_char_class(chars[origin])
        dictionary = self.dictionary
        for t in dictionary.common_prefix_search(chars, origin, end):
            node = _new_node(t, origin, t.length, t.length + skipped)
            node.rnext = result
            morpheme = t.morpheme
            if morpheme is None:
                # Java creates a new Morpheme for every node; they are
                # immutable here, so the nodes of a CToken share one
                morpheme = t.morpheme = Morpheme(dictionary, t.part_of_speech_index)
            node.morpheme = morpheme
            result = node
        if result is not None and (char_class == HIRAGANA or char_class == KANJI or
                                   (self.tokenize_unknown_katakana and char_class == KATAKANA)):
            return result
        # Synthesize token for longest consecutive run of same character class
        length = self._find_unknown_token(chars, origin, end)
        unknown = self.get_unknown_node(origin, length, skipped + length)
        unknown.rnext = result
        return unknown


class Viterbi:
    """net.java.sen.dictionary.Viterbi: finds the most likely sequence of
    morphemes"""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def get_best_tokens(self, text):
        """getBestTokens(new Sentence(text)): text is a Python string, the
        token surfaces are Python strings, their start and length are in
        UTF-16 code units"""
        jtext = _utf16_units(text)
        chars = [ord(c) for c in jtext]
        length = len(chars)
        tokenizer = self.tokenizer
        dictionary = tokenizer.dictionary
        size2 = dictionary.connection_size2
        size3 = dictionary.connection_size3
        # the ends of the runs of non-space characters (where the
        # ConstrainedIterator's hasNext() becomes false) and the iteration
        # origins (positions of non-space characters)
        run_end = [0] * length
        end = length
        origins = []
        for i in range(length - 1, -1, -1):
            if chars[i] in _WHITESPACE:
                end = i
            else:
                run_end[i] = end
        for i in range(length):
            if chars[i] not in _WHITESPACE:
                origins.append(i)
        bos = tokenizer.get_bos_node()
        bos.cbase = 3 + size3 * (size2 * bos.prev.rc_attr2 + bos.rc_attr1)
        eos = tokenizer.get_eos_node()
        end_nodes = [None] * (length + 1)
        end_nodes[0] = bos
        costs = dictionary.connection_costs

        def add_node(node, x):
            node.cbase = 3 + size3 * (size2 * node.prev.rc_attr2 + node.rc_attr1)
            node.lnext = end_nodes[x]
            end_nodes[x] = node

        def calculate_connection_costs(position, r_node):
            while r_node is not None:
                best_cost = _INT_MAX
                best_node = None
                lc = r_node.lc_attr
                dcost = r_node.dictionary_cost
                l_node = end_nodes[position]
                while l_node is not None:
                    cost = l_node.cost + costs[l_node.cbase + lc] + dcost
                    if cost > _INT_MAX or cost < _INT_MIN:
                        cost = (cost + 0x80000000) % 0x100000000 - 0x80000000
                    if cost <= best_cost:
                        best_node = l_node
                        best_cost = cost
                    l_node = l_node.lnext
                r_node.prev = best_node
                r_node.cost = best_cost
                add_node(r_node, position + r_node.span)
                if r_node.rc_attr2 != 0:
                    pos2 = r_node.span + position
                    if pos2 != length:
                        # winding a new iterator to pos2: the origin after
                        # pos2 + 1 calls of nextOrigin() (as far as there
                        # are origins)
                        k = min(pos2, len(origins) - 1)
                        pos3 = origins[k] if origins else 0
                        if pos2 == pos3:  # safety check
                            skipped = pos3 - (origins[k - 1] + 1 if k > 0 else 0)
                            r_node2 = tokenizer.lookup(chars, pos2, run_end[pos2], skipped)
                            while r_node2 is not None:
                                r_node2 = r_node2.clone()
                                cost = r_node.cost + dictionary.get_cost(r_node.prev, r_node, r_node2)
                                if cost > _INT_MAX or cost < _INT_MIN:
                                    cost = (cost + 0x80000000) % 0x100000000 - 0x80000000
                                r_node2.cost = cost
                                r_node2.prev = r_node
                                add_node(r_node2, pos2 + r_node2.span)
                                r_node2 = r_node2.rnext
                r_node = r_node.rnext

        prev_origin = -1
        for position in origins:
            skipped = position - prev_origin - 1
            prev_origin = position
            base = position - skipped
            if end_nodes[base] is not None:
                r_node = tokenizer.lookup(chars, position, run_end[position], skipped)
                if r_node is not None:
                    calculate_connection_costs(base, r_node)
        for position in range(length, -1, -1):
            if end_nodes[position] is not None:
                calculate_connection_costs(position, eos)
                break
        node = eos
        while node.prev is not None:
            prev = node.prev
            prev.next = node
            node = prev
        tokens = []
        node = bos.next
        while node is not None and node.next is not None:
            tokens.append(Token(_java_str(jtext[node.start:node.start + node.length]), node.cost, node.start,
                                node.length, node.morpheme))
            node = node.next
        return tokens


class StringTagger:
    """net.java.sen.StringTagger (without StreamFilters)"""

    def __init__(self, tokenizer):
        self.viterbi = Viterbi(tokenizer)

    def analyze(self, surface):
        return self.viterbi.get_best_tokens(surface)


_lock = threading.Lock()
_data = {}


def get_string_tagger(paths, key='ipadic', tokenize_unknown_katakana=False):
    """SenFactory.getStringTagger: the dictionary data is loaded once per key
    (SenFactory.getInstance), each tagger gets its own Dictionary and
    JapaneseTokenizer. paths: function returning the file path for a
    dictionary file name like 'header.sen'."""
    with _lock:
        data = _data.get(key)
        if data is None:
            data = _data[key] = SenDictionaryData(paths)
    return StringTagger(JapaneseTokenizer(Dictionary(data), UNKNOWN_POS, tokenize_unknown_katakana))
