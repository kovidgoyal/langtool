"""HanLP portable-1.8.2 (com.hankcs.hanlp), a pure Python port of the parts
that LanguageTool's ChineseWordTokenizer and ChineseSentenceTokenizer use:

- the segmenter of ``HanLP.newSegment()`` (ViterbiSegment, with the
  configuration of ChineseWordTokenizer: no named entity recognition, no
  custom dictionary, part of speech tagging; no number/quantifier merging,
  index mode, offsets or multithreading, which are off by default):
  Segment.seg, ViterbiSegment.segSentence and viterbi,
  WordBasedSegment.generateWordNet and speechTagging, Segment.quickAtomSegment
  and convert, WordNet, Vertex, MathUtility.calculateWeight, Term.toString;
- the dictionaries and models it reads, from the binary caches that the
  portable jar ships: CoreDictionary (CoreNatureDictionary.mini.txt.bin: the
  attributes and the DoubleArrayTrie with its Searcher), CoreBiGramTableDictionary
  (CoreNatureDictionary.ngram.mini.txt.table.bin, two serialized Java int
  arrays), CoreDictionaryTransformMatrixDictionary (TransformMatrix,
  CoreNatureDictionary.tr.txt), CharType (CharType.bin), Nature (the
  predefined part of speech tags, whose ordinals the binary dictionary uses),
  Predefine (the total frequency and the smoothing factors);
- the POS tagging of algorithm.Viterbi.compute;
- utility.SentencesUtil.toSentenceList.

The files are part of the hanlp-portable-1.8.2.jar on Maven Central and are
downloaded by langtool.dictionaries (as zh/*).

The segmenter works on Java strings (UTF-16 code units, one Python character
per unit, see langtool.lang.zh.tokenizers). Doubles are computed with the same
operations in the same order as in Java, including the infinities that occur
when a tag of the core dictionary is missing from the transition matrix.
Math.log of the JVM is the platform's intrinsic (allowed to be 1 ulp off),
math.log here is the C library's: the two agree for nearly all arguments, and
a difference could only matter for two paths whose costs are equal up to the
last bit.
"""

import array
import bisect
import math
import struct
import sys
import threading

# CharType
CT_SINGLE = 5
CT_DELIMITER = 6
CT_CHINESE = 7
CT_LETTER = 8
CT_NUM = 9
CT_INDEX = 10
CT_CNUM = 11
CT_OTHER = 17

# Predefine
TAG_PLACE = '未##地'
TAG_BIGIN = '始##始'
TAG_GROUP = '未##团'
TAG_NUMBER = '未##数'
TAG_PROPER = '未##专'
TAG_TIME = '未##时'
TAG_CLUSTER = '未##串'
TAG_END = '末##末'
TAG_PEOPLE = '未##人'
_DEFAULT_TOTAL_FREQUENCY = 25146057  # Predefine.TOTAL_FREQUENCY before CoreDictionary is loaded
_LAMBDA = 0.9
_DOUBLE_MAX = sys.float_info.max

# The predefined natures (part of speech tags) in the order of their
# declaration in com.hankcs.hanlp.corpus.tag.Nature: the index is the
# ordinal, which the binary core dictionary stores. Nature.create appends
# unknown ones (only the transition matrix could create them here).
NATURES = [
    'bg', 'mg', 'nl', 'nx', 'qg', 'ud', 'uj', 'uz', 'ug', 'ul', 'uv', 'yg', 'zg', 'n', 'nr', 'nrj', 'nrf',
    'nr1', 'nr2', 'ns', 'nsf', 'nt', 'ntc', 'ntcf', 'ntcb', 'ntch', 'nto', 'ntu', 'nts', 'nth', 'nh', 'nhm',
    'nhd', 'nn', 'nnt', 'nnd', 'ng', 'nf', 'ni', 'nit', 'nic', 'nis', 'nm', 'nmc', 'nb', 'nba', 'nbc', 'nbp',
    'nz', 'g', 'gm', 'gp', 'gc', 'gb', 'gbc', 'gg', 'gi', 'j', 'i', 'l', 't', 'tg', 's', 'f', 'v', 'vd', 'vn',
    'vshi', 'vyou', 'vf', 'vx', 'vi', 'vl', 'vg', 'a', 'ad', 'an', 'ag', 'al', 'b', 'bl', 'z', 'r', 'rr',
    'rz', 'rzt', 'rzs', 'rzv', 'ry', 'ryt', 'rys', 'ryv', 'rg', 'Rg', 'm', 'mq', 'Mg', 'q', 'qv', 'qt', 'd',
    'dg', 'dl', 'p', 'pba', 'pbei', 'c', 'cc', 'u', 'uzhe', 'ule', 'uguo', 'ude1', 'ude2', 'ude3', 'usuo',
    'udeng', 'uyy', 'udh', 'uls', 'uzhi', 'ulian', 'e', 'y', 'o', 'h', 'k', 'x', 'xx', 'xu', 'w', 'wkz',
    'wky', 'wyz', 'wyy', 'wj', 'ww', 'wt', 'wd', 'wf', 'wn', 'wm', 'ws', 'wp', 'wb', 'wh', 'end', 'begin']
_NATURE_IDS = {name: i for i, name in enumerate(NATURES)}
_N = _NATURE_IDS['n']
_NX = _NATURE_IDS['nx']
_NIT = _NATURE_IDS['nit']
_M = _NATURE_IDS['m']
_T = _NATURE_IDS['t']
_W = _NATURE_IDS['w']
_BEGIN = _NATURE_IDS['begin']
_END = _NATURE_IDS['end']


def nature_create(name):
    """Nature.create: the ordinal of a nature, created if it is unknown"""
    i = _NATURE_IDS.get(name)
    if i is None:
        i = _NATURE_IDS[name] = len(NATURES)
        NATURES.append(name)
    return i


class Attribute:
    """CoreDictionary.Attribute: natures (ordinals) with their frequencies"""
    __slots__ = ('nature', 'frequency', 'total_frequency')

    def __init__(self, nature, frequency, total_frequency):
        self.nature = nature
        self.frequency = frequency
        self.total_frequency = total_frequency

    @classmethod
    def of(cls, nature, frequency):
        """new Attribute(Nature, int)"""
        return cls((nature,), (frequency,), frequency)

    def get_nature_frequency(self, nature):
        for i, pos in enumerate(self.nature):
            if pos == nature:
                return self.frequency[i]
        return 0


def _be_ints(data):
    a = array.array('i')
    a.frombytes(data)
    if sys.byteorder == 'little':
        a.byteswap()
    return a


def _read_int_arrays(data):
    """The int[] objects written one after the other to an
    ObjectOutputStream (CoreBiGramTableDictionary.saveDat)"""
    if data[:4] != b'\xac\xed\x00\x05':
        raise ValueError('not a Java serialization stream')
    pos = 4
    out = []
    while pos < len(data):
        if data[pos] != 0x75:  # TC_ARRAY
            raise ValueError('int array expected')
        pos += 1
        if data[pos] == 0x72:  # TC_CLASSDESC
            n, = struct.unpack_from('>H', data, pos + 1)
            if data[pos + 3:pos + 3 + n] != b'[I':
                raise ValueError('int array expected')
            pos += 3 + n + 8 + 1  # name, serialVersionUID, flags
            fields, = struct.unpack_from('>H', data, pos)
            pos += 2
            if fields != 0 or data[pos] != 0x78 or data[pos + 1] != 0x70:  # TC_ENDBLOCKDATA, TC_NULL
                raise ValueError('unexpected class description')
            pos += 2
        elif data[pos] == 0x71:  # TC_REFERENCE
            pos += 5
        else:
            raise ValueError('unexpected serialization content')
        n, = struct.unpack_from('>i', data, pos)
        pos += 4
        out.append(_be_ints(data[pos:pos + 4 * n]))
        pos += 4 * n
    return out


class HanLPData:
    """The dictionaries and models (loaded once, see get_data). paths: a
    function returning the path of a file name like 'CharType.bin'."""

    def __init__(self, paths):
        self._load_char_type(paths('CharType.bin'))
        self._load_core_dictionary(paths('CoreNatureDictionary.mini.txt.bin'))
        self._load_bigram(paths('CoreNatureDictionary.ngram.mini.txt.table.bin'))
        self._load_transform_matrix(paths('CoreNatureDictionary.tr.txt'))
        # Vertex.newB() evaluates Predefine.TOTAL_FREQUENCY / 10 before
        # CoreDictionary.getWordID loads the core dictionary (which sets the
        # total frequency): the very first word net of the JVM has a begin
        # vertex with the frequency of the default total
        self.first_word_net = True
        self.lock = threading.Lock()

    def _load_char_type(self, path):
        """CharType: ranges (char begin, char end, byte type)"""
        with open(path, 'rb') as f:
            data = f.read()
        t = bytearray(65536)
        for pos in range(0, len(data) - 4, 5):
            b, e = struct.unpack_from('>HH', data, pos)
            t[b:e + 1] = bytes([data[pos + 4]]) * (e - b + 1)
        self.char_type = bytes(t)

    def _load_core_dictionary(self, path):
        """CoreDictionary.loadDat"""
        with open(path, 'rb') as f:
            ints = _be_ints(f.read())
        size = ints[0]
        pos = 1
        attributes = []
        total = 0
        for _ in range(size):
            current_total = ints[pos]
            length = ints[pos + 1]
            pos += 2
            values = ints[pos:pos + 2 * length]
            pos += 2 * length
            attributes.append(Attribute(tuple(values[0::2]), tuple(values[1::2]), current_total))
            total += current_total
        dat_size = ints[pos]
        pos += 1
        self.base = ints[pos:pos + 2 * dat_size:2]
        self.check = ints[pos + 1:pos + 2 * dat_size:2]
        pos += 2 * dat_size
        if pos < len(ints):  # since 1.8.2 the last int may be the total frequency
            total = ints[pos]
        self.attributes = attributes
        # Predefine.setTotalFrequency (int arithmetic as in Java)
        self.total_frequency = (total + 2 ** 31) % 2 ** 32 - 2 ** 31
        self.myu = 1 - (1 / self.total_frequency + 0.00001)
        self.nr_word_id = self.get_word_id(TAG_PEOPLE)
        self.ns_word_id = self.get_word_id(TAG_PLACE)
        self.nt_word_id = self.get_word_id(TAG_GROUP)
        self.t_word_id = self.get_word_id(TAG_TIME)
        self.x_word_id = self.get_word_id(TAG_CLUSTER)
        self.m_word_id = self.get_word_id(TAG_NUMBER)
        self.nx_word_id = self.get_word_id(TAG_PROPER)
        self.begin_word_id = self.get_word_id(TAG_BIGIN)
        self.end_word_id = self.get_word_id(TAG_END)

    def _load_bigram(self, path):
        """CoreBiGramTableDictionary.loadDat"""
        with open(path, 'rb') as f:
            start, pair = _read_int_arrays(f.read())
        if len(self.attributes) != len(start) - 1:
            raise ValueError('the bigram table does not belong to the core dictionary')
        self.bigram_start = start
        self.bigram_keys = pair[0::2]
        self.bigram_values = pair[1::2]

    def _load_transform_matrix(self, path):
        """TransformMatrix.load (with CoreDictionaryTransformMatrixDictionary's
        ordinal = Nature.create) and the extension to all natures that
        Viterbi.compute makes"""
        with open(path, encoding='utf-8') as f:
            lines = f.read().split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        labels = lines[0].split(',')[1:]
        ordinary_array = [nature_create(label) for label in labels]
        ordinary_max = max(ordinary_array) + 1
        matrix = [[0] * ordinary_max for _ in range(ordinary_max)]
        for line in lines[1:]:
            params = line.split(',')
            current = nature_create(params[0])
            for i, o in enumerate(ordinary_array):
                matrix[current][o] = int(params[1 + i])
        total = [sum(row) for row in matrix]
        for j in range(ordinary_max):
            if total[j] == 0:
                total[j] = sum(matrix[i][j] for i in range(ordinary_max))
        n = max(ordinary_max, len(NATURES))
        trans = [[0.0] * n for _ in range(n)]
        for f in ordinary_array:
            for t in ordinary_array:
                trans[f][t] = -_log_div(matrix[f][t] + 1e-8, total[f])
        self.transition = trans
        self.tag_total = total + [0] * (n - ordinary_max)

    def get_word_id(self, key):
        """DoubleArrayTrie.exactMatchSearch"""
        base, check = self.base, self.check
        size = len(base)
        b = base[0]
        for c in key:
            p = b + ord(c) + 1
            if p < size and b == check[p]:
                b = base[p]
            else:
                return -1
        if b < size:
            n = base[b]
            if b == check[b] and n < 0:
                return -n - 1
        return -1

    def search(self, chars):
        """DoubleArrayTrie.Searcher over the char codes: (begin, length,
        index) of all words of the core dictionary in the text, by begin,
        then by length. (Java's arrays have 65535 more zeros after the
        loaded size: positions beyond it never match.)"""
        base, check = self.base, self.check
        size = len(base)
        root = base[0]
        length = len(chars)
        for begin in range(length):
            b = root
            for i in range(begin, length):
                p = b + chars[i] + 1
                if p < size and b == check[p]:
                    b = base[p]
                else:
                    break
                if b < size:
                    n = base[b]
                    if b == check[b] and n < 0:
                        yield begin, i - begin + 1, -n - 1

    def bi_frequency(self, id_a, id_b):
        """CoreBiGramTableDictionary.getBiFrequency(int, int)"""
        if id_a < 0:
            return -id_a
        if id_b < 0:
            return -id_b
        start = self.bigram_start
        lo, hi = start[id_a], start[id_a + 1]
        i = bisect.bisect_left(self.bigram_keys, id_b, lo, hi)
        if i < hi and self.bigram_keys[i] == id_b:
            return self.bigram_values[i]
        return 0


def _log_div(a, b):
    """Math.log(a / b) for a double a > 0 and an int b >= 0 (a / 0 is
    infinity in Java)"""
    if b == 0:
        return math.inf
    return math.log(a / b)


_data_lock = threading.Lock()
_data = {}


def get_data(paths, key='portable-1.8.2'):
    """The HanLP data, loaded once per key (static initializers in Java)"""
    with _data_lock:
        data = _data.get(key)
        if data is None:
            data = _data[key] = HanLPData(paths)
    return data


class Vertex:
    """seg.common.Vertex (word, the placeholder word like 未##数, only
    matters for debugging output and is not kept)"""
    __slots__ = ('real_word', 'attribute', 'word_id', 'from_', 'weight')

    def __init__(self, real_word, attribute, word_id):
        self.real_word = real_word
        self.attribute = attribute
        self.word_id = word_id
        self.from_ = None
        self.weight = 0.0

    def confirm_nature(self, nature):
        """Vertex.confirmNature(Nature)"""
        attribute = self.attribute
        if len(attribute.nature) == 1 and attribute.nature[0] == nature:
            return
        frequency = attribute.get_nature_frequency(nature)
        if frequency == 0:
            frequency = 1000
        self.attribute = Attribute.of(nature, frequency)


def _dictionary_vertex(data, real_word, attribute, word_id):
    """new Vertex(realWord, attribute, wordID) with the word ID and
    attribute changes of Vertex.compileRealWord"""
    if len(attribute.nature) == 1:
        name = NATURES[attribute.nature[0]]
        if name.startswith('nr'):
            word_id = data.nr_word_id
        elif name.startswith('ns'):
            word_id = data.ns_word_id
        elif name == 'nx':
            word_id = data.nx_word_id
            if word_id == -1:
                word_id = data.x_word_id
        elif name.startswith('nt') or name == 'nit':
            word_id = data.nt_word_id
        elif name[0] == 'm':
            word_id = data.m_word_id
            attribute = data.attributes[word_id]
        elif name[0] == 'x':
            word_id = data.x_word_id
            attribute = data.attributes[word_id]
        elif name == 't':
            word_id = data.t_word_id
            attribute = data.attributes[word_id]
    return Vertex(real_word, attribute, word_id)


def _quick_atom_segment(char_type, chars, text, start, end):
    """Segment.quickAtomSegment: (atom, char type) runs of chars of the
    same type, with decimal separators inside numbers"""
    atoms = []
    offset = start
    pre_type = char_type[chars[offset]]
    offset += 1
    while offset < end:
        cur_type = char_type[chars[offset]]
        if cur_type != pre_type:
            if pre_type == CT_NUM and text[offset] in '，,．.':
                if offset + 1 < end and char_type[chars[offset + 1]] == CT_NUM:
                    offset += 1
                    continue
            atoms.append((text[start:offset], pre_type))
            start = offset
        pre_type = cur_type
        offset += 1
    atoms.append((text[start:offset], pre_type))
    return atoms


def _add(line_list, vertex):
    """WordNet.add(int, Vertex): one word per length at a position"""
    n = len(vertex.real_word)
    for old in line_list:
        if len(old.real_word) == n:
            return
    line_list.append(vertex)


def _calculate_weight(data, from_, to):
    """MathUtility.calculateWeight"""
    f_from = from_.attribute.total_frequency
    f_bigram = data.bi_frequency(from_.word_id, to.word_id)
    f_to = to.attribute.total_frequency
    myu = data.myu
    return -math.log(_LAMBDA * (myu * f_bigram / (f_from + 1) + 1 - myu)
                     + (1 - _LAMBDA) * f_to / data.total_frequency)


def _update_from(data, vertex, from_):
    """Vertex.updateFrom"""
    weight = from_.weight + _calculate_weight(data, from_, vertex)
    if vertex.from_ is None or vertex.weight > weight:
        vertex.from_ = from_
        vertex.weight = weight


def seg(data, text):
    """Segment.seg(String) of ChineseWordTokenizer's ViterbiSegment: a list
    of (word, nature name); text is a string of UTF-16 code units"""
    chars = [ord(c) for c in text]
    char_type = data.char_type
    n = len(text)
    # WordNet(char[])
    lines = [[] for _ in range(n + 2)]
    with data.lock:
        first = data.first_word_net
        data.first_word_net = False
    b_frequency = (_DEFAULT_TOTAL_FREQUENCY if first else data.total_frequency) // 10
    lines[0].append(Vertex(' ', Attribute.of(_BEGIN, b_frequency), data.begin_word_id))
    lines[n + 1].append(Vertex(' ', Attribute.of(_END, data.total_frequency // 10), data.end_word_id))
    # WordBasedSegment.generateWordNet: the words of the core dictionary...
    attributes = data.attributes
    for begin, length, index in data.search(chars):
        _add(lines[begin + 1], _dictionary_vertex(data, text[begin:begin + length], attributes[index], index))
    # ... and atoms where no word starts, so that the graph is connected
    i = 1
    while i < len(lines):
        if not lines[i]:
            j = i + 1
            while j < len(lines) - 1:
                if lines[j] and char_type[chars[j - 1]] != CT_CNUM:
                    break
                j += 1
            offset = 0
            for atom, ct in _quick_atom_segment(char_type, chars, text, i - 1, j - 1):  # WordNet.add(int, List)
                if ct in (CT_NUM, CT_INDEX, CT_CNUM):
                    vertex = Vertex(atom, Attribute.of(_M, 10000), data.m_word_id)
                elif ct in (CT_DELIMITER, CT_OTHER):
                    vertex = Vertex(atom, Attribute.of(_W, 10000), -1)
                elif ct == CT_SINGLE:
                    vertex = Vertex(atom, Attribute.of(_NX, 10000), data.x_word_id)
                else:
                    vertex = Vertex(atom, Attribute.of(_N, 10000), -1)
                _add(lines[i + offset], vertex)
                offset += len(atom)
            i = j
        else:
            i += len(lines[i][-1].real_word)
    # ViterbiSegment.viterbi
    start = lines[0][0]
    for node in lines[1]:
        _update_from(data, node, start)
    for i in range(1, len(lines) - 1):
        for node in lines[i]:
            if node.from_ is None:
                continue
            for to in lines[i + len(node.real_word)]:
                _update_from(data, to, node)
    vertex_list = []
    v = lines[-1][0]
    while v is not None:
        vertex_list.append(v)
        v = v.from_
    vertex_list.reverse()
    _speech_tagging(data, vertex_list)
    return [(v.real_word, NATURES[v.attribute.nature[0]]) for v in vertex_list[1:-1]]


def _speech_tagging(data, vertex_list):
    """WordBasedSegment.speechTagging: Viterbi.compute(List<Vertex>,
    TransformMatrix), which confirms one nature for each vertex"""
    trans = data.transition
    tag_total = data.tag_total
    length = len(vertex_list) - 1
    pre = vertex_list[0].attribute.nature[0]
    item = vertex_list[1]
    attribute = item.attribute
    cost = [trans[pre][cur] - _log_div(attribute.frequency[k] + 1e-8, tag_total[cur])
            for k, cur in enumerate(attribute.nature)]
    pre_tag_set = attribute.nature
    pre_item = item
    for i in range(1, length):
        item = vertex_list[i + 1]
        attribute = item.attribute
        cur_tag_set = attribute.nature
        new_cost = []
        perfect_cost_line = _DOUBLE_MAX
        for k, cur in enumerate(cur_tag_set):
            best = _DOUBLE_MAX
            emission = _log_div(attribute.frequency[k] + 1e-8, tag_total[cur])
            for j, p in enumerate(pre_tag_set):
                now = cost[j] + trans[p][cur] - emission
                if now < best:
                    best = now
                    if now < perfect_cost_line:
                        perfect_cost_line = now
                        pre = p
            new_cost.append(best)
        pre_item.confirm_nature(pre)
        cost = new_cost
        pre_tag_set = cur_tag_set
        pre_item = item


def to_sentence_list(content, shortest=True):
    """SentencesUtil.toSentenceList(String, boolean)"""
    from ...tools import java_is_whitespace, java_trim
    sentences = []
    sb = []

    def insert():
        s = java_trim(''.join(sb))
        if s:
            sentences.append(s)

    i = 0
    n = len(content)
    while i < n:
        c = content[i]
        if not sb and (java_is_whitespace(c) or c == ' '):
            i += 1
            continue
        sb.append(c)
        if c == '.':
            if i < n - 1 and ord(content[i + 1]) > 128:
                insert()
                sb = []
        elif c == '…':
            if i < n - 1 and content[i + 1] == '…':
                sb.append('…')
                i += 1
                insert()
                sb = []
        elif c in '，,;；':
            if shortest:
                insert()
                sb = []
        elif c in ' \t\u00a0。!！?？\n\r':
            insert()
            sb = []
        i += 1
    if sb:
        insert()
    return sentences
