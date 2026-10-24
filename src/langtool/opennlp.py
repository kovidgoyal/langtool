"""Inference with Apache OpenNLP maxent models (the en-token.bin,
en-pos-maxent.bin and en-chunker.bin models of OpenNLP 1.5 that
LanguageTool's EnglishChunker uses), a pure Python port of the relevant
parts of opennlp-tools 1.9.5:

- the model packages (BaseModel: a zip with manifest.properties and the
  artifacts) and the binary GIS model format (GenericModelReader,
  GISModelReader, BinaryFileDataReader with Java's modified UTF-8 strings)
- GISModel.eval (UniformPrior, ArrayMath.sumFeatures)
- BeamSearch with Sequence and java.util.PriorityQueue (whose order of equal
  elements is kept)
- TokenizerME with DefaultTokenContextGenerator and WhitespaceTokenizer
- POSTaggerME with DefaultPOSContextGenerator, POSDictionary (tags.tagdict)
  and DefaultPOSSequenceValidator
- ChunkerME with DefaultChunkerContextGenerator and
  DefaultChunkerSequenceValidator

Only inference is supported (no training). Strings are processed as Java
strings, i.e. as UTF-16 code units: use java_string() to convert a Python
string (characters outside the BMP become surrogate pairs) before passing it
to the tokenizer, tagger or chunker. The models use StrictMath.exp/log in
Java (fdlibm); math.exp/math.log are used here, which may differ in the last
bit for some values (this only matters for exact ties, which are resolved
the same way for equal values)."""

import io
import heapq
import math
import operator
import struct
import threading
import unicodedata
import zipfile
from xml.etree import ElementTree

from ._base import speedups as _speedups
from .fsa import read_properties
from .tools import java_is_whitespace, java_split, java_trim

_cat = unicodedata.category


def java_string(s):
    """The string as UTF-16 code units (characters outside the BMP as
    surrogate pairs), like a Java String"""
    if not s or max(s) <= '￿':
        return s
    out = []
    for c in s:
        o = ord(c)
        if o > 0xffff:
            o -= 0x10000
            out.append(chr(0xd800 + (o >> 10)))
            out.append(chr(0xdc00 + (o & 0x3ff)))
        else:
            out.append(c)
    return ''.join(out)


def java_length(s):
    """String.length() (number of UTF-16 code units)"""
    if not s or max(s) <= '￿':
        return len(s)
    return len(s) + sum(1 for c in s if c > '￿')


def is_whitespace(c):
    """opennlp.tools.util.StringUtil.isWhitespace(char)"""
    return java_is_whitespace(c) or _cat(c) == 'Zs'


# --- model reading ---

class _DataReader:
    """java.io.DataInputStream (readInt, readDouble, readUTF) on bytes"""

    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_int(self):
        v, = struct.unpack_from('>i', self.data, self.pos)
        self.pos += 4
        return v

    def read_double(self):
        v, = struct.unpack_from('>d', self.data, self.pos)
        self.pos += 8
        return v

    def read_doubles(self, n):
        v = struct.unpack_from('>%dd' % n, self.data, self.pos)
        self.pos += 8 * n
        return v

    def read_utf(self):
        n, = struct.unpack_from('>H', self.data, self.pos)
        b = self.data[self.pos + 2:self.pos + 2 + n]
        self.pos += 2 + n
        # modified UTF-8: NUL is C0 80, supplementary characters are two
        # 3 byte encoded surrogates (kept as surrogates, like in Java)
        if b'\xc0\x80' in b:
            b = b.replace(b'\xc0\x80', b'\x00')
        return b.decode('utf-8', 'surrogatepass')


def _java_exp(x):
    """StrictMath.exp (Infinity on overflow)"""
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


def _java_div(x, y):
    """x / y with Java's double semantics for y == 0.0 or infinite y"""
    if y == 0.0:
        return math.nan if x == 0.0 or x != x else math.copysign(math.inf, x)
    return x / y


class _NaNList(list):
    """The probabilities of a degenerate evaluation (with NaN values)"""


class GISModel:
    """opennlp.tools.ml.maxent.GISModel (with the UniformPrior): pmap maps
    the context predicates to (outcome indices, parameters)"""

    def __init__(self, outcome_names, pmap):
        self.outcome_names = outcome_names
        self.num_outcomes = len(outcome_names)
        self.pmap = pmap
        # UniformPrior.setLabels: StrictMath.log(1.0 / numOutcomes)
        self.r = math.log(1.0 / self.num_outcomes)
        self._index = {}
        for i, o in enumerate(outcome_names):
            self._index.setdefault(o, i)

    def eval(self, context):
        """GISModel.eval(String[] context): the probabilities of the
        outcomes"""
        return self.eval_from([self.r] * self.num_outcomes, context)

    def sum_features(self, prior, context):
        """ArrayMath.sumFeatures: adds the parameters of the context
        predicates (in their order) to prior"""
        pmap = self.pmap
        for c in context:
            e = pmap.get(c)
            if e is not None:
                for oid, p in zip(e[0], e[1]):
                    prior[oid] += p

    def normalize(self, prior):
        """The rest of GISModel.eval: exp and normalization"""
        exp = math.exp
        try:
            prior = [exp(x) for x in prior]
        except OverflowError:
            prior = [_java_exp(x) for x in prior]
        normal = 0.0
        for x in prior:
            normal += x
        if normal == 0.0 or normal == math.inf:
            # Java: x / 0.0 and inf / inf are NaN, x / inf is 0.0
            return _NaNList(_java_div(x, normal) for x in prior)
        return [x / normal for x in prior]

    def prefix_sums(self, context):
        """The sums of the parameters of the first predicates of a context
        (the start of sumFeatures; the rest is added with eval_from)"""
        prior = [self.r] * self.num_outcomes
        if _speedups is not None:
            return _speedups.gis_sum(prior, self.pmap, context)
        self.sum_features(prior, context)
        return prior

    def eval_from(self, prefix_sums, context_rest):
        """eval(context) for a context whose first predicates gave
        prefix_sums: the same additions in the same order, so the result is
        identical"""
        if _speedups is not None:
            r = _speedups.gis_eval(prefix_sums, self.pmap, context_rest)
            if r is not None:
                return r
        prior = list(prefix_sums)
        self.sum_features(prior, context_rest)
        return self.normalize(prior)

    def get_best_outcome(self, ocs):
        """AbstractModel.getBestOutcome (the first maximum)"""
        max_idx = 0
        for i in range(1, len(ocs)):
            if ocs[max_idx] < ocs[i]:
                max_idx = i
        return self.outcome_names[max_idx]

    def get_outcome(self, i):
        return self.outcome_names[i]

    def get_index(self, outcome):
        return self._index.get(outcome, -1)


def read_gis_model(data):
    """GenericModelReader for a binary GIS model (the *.model entries of
    the model packages)"""
    r = _DataReader(data)
    model_type = r.read_utf()
    if model_type != 'GIS':
        raise ValueError('Unsupported model format: ' + model_type)
    r.read_int()  # correction constant (not used anymore)
    r.read_double()  # correction params (not used anymore)
    outcome_labels = [r.read_utf() for _ in range(r.read_int())]
    outcome_patterns = []
    for _ in range(r.read_int()):
        # StringTokenizer(readUTF(), " ")
        outcome_patterns.append([int(x) for x in r.read_utf().split(' ') if x])
    num_preds = r.read_int()
    pred_labels = [r.read_utf() for _ in range(num_preds)]
    pmap = {}
    pid = 0
    for pattern in outcome_patterns:
        outcomes = tuple(pattern[1:])
        n = len(outcomes)
        count = pattern[0]
        values = r.read_doubles(count * n)
        for j in range(count):
            # LinkedHashMap.put: a later duplicate predicate replaces the earlier one
            pmap[pred_labels[pid]] = (outcomes, values[j * n:(j + 1) * n])
            pid += 1
    return GISModel(outcome_labels, pmap)


class ModelPackage:
    """opennlp.tools.util.model.BaseModel: the zip file of a model with its
    manifest properties and artifacts"""

    def __init__(self, path_or_bytes):
        if isinstance(path_or_bytes, (bytes, bytearray)):
            path_or_bytes = io.BytesIO(path_or_bytes)
        with zipfile.ZipFile(path_or_bytes) as z:
            self.artifacts = {name: z.read(name) for name in z.namelist()}
        self.manifest = read_properties(self.artifacts['manifest.properties'].decode('iso-8859-1'))

    def get_manifest_property(self, key):
        return self.manifest.get(key)

    def gis_model(self, name):
        return read_gis_model(self.artifacts[name])

    def beam_size(self, default):
        v = self.get_manifest_property('BeamSize')
        return int(v) if v is not None else default


# --- beam search ---

def _log(p):
    # StrictMath.log
    if p > 0:
        return math.log(p)
    return -math.inf if p == 0 else math.nan


# A sequence (opennlp.tools.util.Sequence) is a tuple (score, outcome,
# parent sequence, probability of the outcome); the empty sequence is
# _EMPTY_SEQUENCE. score is the sum of the logs of the probabilities.
_EMPTY_SEQUENCE = (0.0, None, None, None)


def sequence_outcomes(seq):
    """Sequence.getOutcomes()"""
    out = []
    while seq[2] is not None:
        out.append(seq[1])
        seq = seq[2]
    out.reverse()
    return out


def sequence_probs(seq):
    """Sequence.getProbs()"""
    out = []
    while seq[2] is not None:
        out.append(seq[3])
        seq = seq[2]
    out.reverse()
    return out


class _JavaPriorityQueue:
    """java.util.PriorityQueue of sequences ordered by Sequence.compareTo
    (the highest score first): a binary heap with Java's siftUp/siftDown,
    so that sequences with equal scores are removed in the same order as
    in Java. (Scores are never -0.0; NaN scores are not ordered like
    Double.compare, they don't occur for valid models.)"""

    __slots__ = ('queue',)

    def __init__(self):
        self.queue = []

    def __len__(self):
        return len(self.queue)

    def add(self, x):
        q = self.queue
        q.append(x)
        k = len(q) - 1
        xs = x[0]
        while k > 0:
            parent = (k - 1) >> 1
            e = q[parent]
            if e[0] >= xs:  # x.compareTo(e) >= 0
                break
            q[k] = e
            k = parent
        q[k] = x

    def remove(self):
        q = self.queue
        result = q[0]
        x = q.pop()
        n = len(q)
        if n > 0:
            xs = x[0]
            k = 0
            half = n >> 1
            while k < half:
                child = 2 * k + 1
                c = q[child]
                right = child + 1
                if right < n and q[right][0] > c[0]:  # c.compareTo(queue[right]) > 0
                    child = right
                    c = q[child]
                if xs >= c[0]:  # x.compareTo(c) <= 0
                    break
                q[k] = c
                k = child
            q[k] = x
        return result

    def clear(self):
        self.queue = []


class BeamSearch:
    """opennlp.tools.ml.BeamSearch (without the contexts cache, which is not
    used by the taggers here)"""

    ZERO_LOG = -100000

    def __init__(self, size, model):
        self.size = size
        self.model = model

    def best_sequences(self, num_sequences, length, evaluate, allowed_outcomes, min_sequence_score=ZERO_LOG):
        """The best sequences (see Sequence above) for an input sequence of
        the given length. evaluate(i, sequence) -> the probabilities of the
        outcomes, i.e. model.eval(contextGenerator.getContext(i, input,
        outcomes of sequence)); allowed_outcomes(i, sequence) -> the indices
        (ascending) of the outcomes that are valid after the sequence
        (SequenceValidator.validSequence), None for all.

        Java adds the extended sequences to a PriorityQueue and removes the
        best ones from it; here they are collected in the same order and the
        best ones are selected by sorting, unless there are equal scores
        that make the order depend on the heap (then the PriorityQueue is
        simulated), see _select()."""
        size = self.size
        names = self.model.outcome_names
        n_outcomes = self.model.num_outcomes
        all_outcomes = range(n_outcomes)
        size_index = max(0, n_outcomes - size)
        # (id(scores), id(allowed)) -> (scores, allowed, the extensions of a sequence with these scores: (outcome,
        # log of the probability, probability) of the valid outcomes with one of the best probabilities, the same
        # extensions ordered by probability); the scores and allowed outcome lists are kept here, so their ids are
        # not reused
        expansions = {}
        tops = [_EMPTY_SEQUENCE]
        for i in range(length):
            evaluated = []
            for top in tops:
                scores = evaluate(i, top)
                allowed = allowed_outcomes(i, top)
                key = (id(scores), id(allowed))
                e = expansions.get(key)
                if e is None:
                    min_score = _java_sorted(scores)[size_index]
                    ext = [(names[p], _log(scores[p]), scores[p])
                           for p in (all_outcomes if allowed is None else allowed) if scores[p] >= min_score]
                    e = expansions[key] = (scores, allowed, ext, sorted(ext, key=_log_p, reverse=True))
                evaluated.append((top, e))
            candidates = self._candidates(evaluated, size, names, all_outcomes, min_sequence_score, True)
            tops = self._select(candidates, size)
            if tops is None:
                # equal scores: the order depends on the PriorityQueue, which needs all the candidates
                tops = self._select_from_queue(self._candidates(evaluated, size, names, all_outcomes,
                                                                min_sequence_score, False), size)
        if length == 0:
            return tops[:num_sequences]
        selected = self._select(candidates, num_sequences)
        if selected is None:
            selected = self._select_from_queue(self._candidates(evaluated, size, names, all_outcomes,
                                                                min_sequence_score, False), num_sequences)
        return selected

    @staticmethod
    def _candidates(evaluated, size, names, all_outcomes, min_sequence_score, prune):
        """The extended sequences of the tops (in the order in which Java adds
        them to the PriorityQueue). With prune, the extensions that are
        worse than size + 1 extensions found before are left out, as they
        can't be among the best size + 1 sequences (and the order of the
        candidates is not the one of Java)."""
        candidates = []
        append = candidates.append
        best = []  # with prune: a min heap of the size + 1 best scores
        k = size + 1
        threshold = -math.inf
        added = False
        for top, (scores, allowed, ext, ext_sorted) in evaluated:
            top_score = top[0]
            if prune:
                # the extensions in the order of their probabilities, until they are worse than the threshold
                if ext_sorted and top_score + ext_sorted[0][1] > min_sequence_score:
                    added = True
                for out, log_p, p in ext_sorted:
                    ns_score = top_score + log_p
                    if ns_score < threshold or not ns_score > min_sequence_score:
                        break
                    append((ns_score, out, top, p))
                    if len(best) < k:
                        heapq.heappush(best, ns_score)
                        if len(best) == k:
                            threshold = best[0]
                    elif ns_score > threshold:
                        heapq.heapreplace(best, ns_score)
                        threshold = best[0]
            else:
                for out, log_p, p in ext:
                    ns_score = top_score + log_p
                    if ns_score > min_sequence_score:
                        append((ns_score, out, top, p))
                        added = True
            if not added:  # if no advanced sequences, advance all valid
                for p in (all_outcomes if allowed is None else allowed):
                    score = scores[p]
                    ns_score = top_score + _log(score)
                    if ns_score > min_sequence_score:
                        append((ns_score, names[p], top, score))
                        added = True
                        if prune:
                            if len(best) < k:
                                heapq.heappush(best, ns_score)
                                if len(best) == k:
                                    threshold = best[0]
                            elif ns_score > threshold:
                                heapq.heapreplace(best, ns_score)
                                threshold = best[0]
        return candidates

    @staticmethod
    def _select(candidates, k):
        """The first k sequences removed from a java.util.PriorityQueue to
        which the candidates were added (in their order), if this doesn't
        depend on the order of the queue (no equal scores among the k best
        and the next one; there are no NaN scores, they are not >
        min_sequence_score), None otherwise"""
        k = min(k, len(candidates))
        ordered = sorted(candidates, key=_score, reverse=True)
        prev = None
        for c in ordered[:k + 1]:
            sc = c[0]
            if sc == prev:
                return None
            prev = sc
        return ordered[:k]

    @staticmethod
    def _select_from_queue(candidates, k):
        """The first k sequences removed from a java.util.PriorityQueue to
        which the candidates were added (in their order)"""
        q = _JavaPriorityQueue()
        for c in candidates:
            q.add(c)
        return [q.remove() for _ in range(min(k, len(candidates)))]

    def best_sequence(self, length, evaluate, allowed_outcomes):
        sequences = self.best_sequences(1, length, evaluate, allowed_outcomes)
        return sequences[0] if sequences else None


_score = operator.itemgetter(0)
_log_p = operator.itemgetter(1)


def _java_sorted(values):
    """Arrays.sort(double[]) (NaN values last; only probabilities of
    degenerate evaluations, _NaNList, may contain NaN)"""
    if type(values) is _NaNList:
        return sorted(x for x in values if x == x) + [x for x in values if x != x]
    return sorted(values)


# --- tokenizer ---

def whitespace_tokenize_pos(d):
    """WhitespaceTokenizer.tokenizePos: the (start, end) spans of the
    tokens separated by whitespace"""
    tokens = []
    tok_start = -1
    in_tok = False
    for i, c in enumerate(d):
        if is_whitespace(c):
            if in_tok:
                tokens.append((tok_start, i))
                in_tok = False
                tok_start = -1
        elif not in_tok:
            tok_start = i
            in_tok = True
    if in_tok:
        tokens.append((tok_start, len(d)))
    return tokens


def _add_char_preds(key, c, preds):
    """DefaultTokenContextGenerator.addCharPreds"""
    preds.append(key + '=' + c)
    k = _cat(c)
    if k[0] == 'L':  # Character.isLetter
        preds.append(key + '_alpha')
        if k == 'Lu' or ((k == 'So' or k == 'Nl') and c.isupper()):  # Character.isUpperCase
            preds.append(key + '_caps')
    elif k == 'Nd':  # Character.isDigit
        preds.append(key + '_num')
    elif is_whitespace(c):
        preds.append(key + '_ws')
    elif c == '.' or c == '?' or c == '!':
        preds.append(key + '_eos')
    elif c == '`' or c == '"' or c == "'":
        preds.append(key + '_quote')
    elif c == '[' or c == '{' or c == '(':
        preds.append(key + '_lp')
    elif c == ']' or c == '}' or c == ')':
        preds.append(key + '_rp')


def token_context(sentence, index, induced_abbreviations=frozenset()):
    """DefaultTokenContextGenerator.getContext"""
    preds = ['p=' + sentence[:index], 's=' + sentence[index:]]
    if index > 0:
        _add_char_preds('p1', sentence[index - 1], preds)
        if index > 1:
            _add_char_preds('p2', sentence[index - 2], preds)
            preds.append('p21=' + sentence[index - 2] + sentence[index - 1])
        else:
            preds.append('p2=bok')
        preds.append('p1f1=' + sentence[index - 1] + sentence[index])
    else:
        preds.append('p1=bok')
    _add_char_preds('f1', sentence[index], preds)
    if index + 1 < len(sentence):
        _add_char_preds('f2', sentence[index + 1], preds)
        preds.append('f12=' + sentence[index] + sentence[index + 1])
    else:
        preds.append('f2=bok')
    if sentence[0] == '&' and sentence[-1] == ';':
        preds.append('cc')  # character code
    if index == len(sentence) - 1 and sentence in induced_abbreviations:
        preds.append('pabb')
    return preds


def _is_default_alphanumeric(tok):
    # TokenizerFactory.getAlphaNumericPattern(): Factory.DEFAULT_ALPHANUMERIC "^[A-Za-z0-9]+$" (matches())
    for c in tok:
        if not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9'):
            return False
    return bool(tok)


class TokenizerME:
    """opennlp.tools.tokenize.TokenizerME for a model package of OpenNLP 1.5
    (TokenizerFactory defaults: no abbreviation dictionary, the default
    alphanumeric pattern, which is not language specific for English)"""

    SPLIT = 'T'

    def __init__(self, package):
        self.model = package.gis_model('token.model')
        self.use_alpha_numeric_optimization = (
            (package.get_manifest_property('useAlphaNumericOptimization') or '').lower() == 'true')
        if package.get_manifest_property('alphaNumericPattern') is not None:
            raise ValueError('alphaNumericPattern of tokenizer models is not supported')
        if 'abbreviations.dictionary' in package.artifacts:
            raise ValueError('abbreviation dictionaries of tokenizer models are not supported')
        language = package.get_manifest_property('Language')
        if language in ('pt', 'por'):
            raise ValueError('Portuguese tokenizer models are not supported')

    def tokenize_pos(self, d):
        """The (start, end) spans of the tokens of the (Java) string d"""
        new_tokens = []
        model = self.model
        best_outcome = model.get_best_outcome
        split = self.SPLIT
        for start, end in whitespace_tokenize_pos(d):
            tok = d[start:end]
            # Can't tokenize single characters
            if len(tok) < 2 or (self.use_alpha_numeric_optimization and _is_default_alphanumeric(tok)):
                new_tokens.append((start, end))
                continue
            orig_start = start
            for j in range(orig_start + 1, end):
                best = best_outcome(model.eval(token_context(tok, j - orig_start)))
                if best == split:
                    new_tokens.append((start, j))
                    start = j
            new_tokens.append((start, end))
        return new_tokens

    def tokenize(self, d):
        return [d[s:e] for s, e in self.tokenize_pos(d)]


# --- POS tagger ---

def read_pos_dictionary(data):
    """POSDictionary.create (DictionaryEntryPersistor): word -> list of tags;
    returns (dictionary, case_sensitive)"""
    case_sensitive = True
    dictionary = {}
    for event, elem in ElementTree.iterparse(io.BytesIO(data), events=('start', 'end')):
        tag = elem.tag
        if event == 'start':
            if tag == 'dictionary':
                v = elem.get('case_sensitive')
                if v is not None:
                    case_sensitive = v.lower() == 'true'
            continue
        if tag == 'entry':
            tokens = [java_trim(t.text or '') for t in elem.findall('token')]
            if len(tokens) != 1:
                raise ValueError('Each entry must have exactly one token! %r' % tokens)
            tags = java_split(elem.get('tags'), ' ')
            dictionary[java_string(tokens[0])] = tags
            elem.clear()
    if not case_sensitive:
        dictionary = {k.lower(): v for k, v in dictionary.items()}
    return dictionary, case_sensitive


_SE = '*SE*'
_SB = '*SB*'


def _has_ascii(s, lo, hi):
    for c in s:
        if lo <= c <= hi:
            return True
    return False


def pos_context_prefix(index, tokens):
    """The first predicates of DefaultPOSContextGenerator.getContext (without
    an ngram dictionary), which don't depend on the previous tags"""
    lex = tokens[index]
    e = ['default', 'w=' + lex]
    # do some basic suffix analysis
    ln = len(lex)
    for li in range(4):
        e.append('suf=' + lex[max(ln - li - 1, 0):])
    for li in range(4):
        e.append('pre=' + lex[:min(li + 1, ln)])
    # see if the word has any special characters
    if '-' in lex:
        e.append('h')
    if _has_ascii(lex, 'A', 'Z'):
        e.append('c')
    if _has_ascii(lex, '0', '9'):
        e.append('d')
    # add the words and pos's of the surrounding context
    e.append('p=' + (tokens[index - 1] if index >= 1 else _SB))
    return e


def pos_context_rest(index, tokens, tags):
    """The rest of DefaultPOSContextGenerator.getContext: the predicates
    from the tag of the previous token on"""
    e = []
    if index >= 1:
        tagprev = tags[index - 1]
        e.append('t=' + tagprev)
        if index >= 2:
            e.append('pp=' + tokens[index - 2])
            e.append('t2=' + tags[index - 2] + ',' + tagprev)
        else:
            e.append('pp=' + _SB)
    n = len(tokens)
    if n > index + 1:
        e.append('n=' + tokens[index + 1])
        e.append('nn=' + (tokens[index + 2] if n > index + 2 else _SE))
    else:
        e.append('n=' + _SE)
    return e


def pos_context(index, tokens, tags):
    """DefaultPOSContextGenerator.getContext (without an ngram dictionary;
    its cache doesn't change the results)"""
    return pos_context_prefix(index, tokens) + pos_context_rest(index, tokens, tags)


class POSTaggerME:
    """opennlp.tools.postag.POSTaggerME for a model package of OpenNLP 1.5
    (DefaultPOSContextGenerator, the tag dictionary tags.tagdict with
    DefaultPOSSequenceValidator)"""

    DEFAULT_BEAM_SIZE = 3

    def __init__(self, package):
        version = package.get_manifest_property('OpenNLP-Version') or ''
        parts = version.split('.')
        if len(parts) < 2 or int(parts[0]) != 1 or int(parts[1]) >= 8:
            raise ValueError('Only POS models of OpenNLP 1.5 - 1.7 are supported, not ' + version)
        if 'ngram.dictionary' in package.artifacts:
            raise ValueError('ngram dictionaries of POS models are not supported')
        self.model = package.gis_model('pos.model')
        self.beam = BeamSearch(package.beam_size(self.DEFAULT_BEAM_SIZE), self.model)
        tagdict = package.artifacts.get('tags.tagdict')
        if tagdict is not None:
            self.tag_dictionary, self.case_sensitive = read_pos_dictionary(tagdict)
        else:
            self.tag_dictionary, self.case_sensitive = None, True

    def tag(self, tokens):
        """The POS tags of the (Java string) tokens"""
        model = self.model
        prefixes = {}
        cache = {}

        def evaluate(i, seq):
            # the context depends on the position and the last two tags only
            last = seq[1]
            key = (i, last, seq[2][1] if i >= 2 else None)
            r = cache.get(key)
            if r is None:
                prefix = prefixes.get(i)
                if prefix is None:
                    prefix = prefixes[i] = model.prefix_sums(pos_context_prefix(i, tokens))
                tags = [None] * i
                if i >= 1:
                    tags[i - 1] = last
                    if i >= 2:
                        tags[i - 2] = key[2]
                r = cache[key] = model.eval_from(prefix, pos_context_rest(i, tokens, tags))
            return r

        allowed = [self._allowed_outcomes(word) for word in tokens]
        return sequence_outcomes(self.beam.best_sequence(len(tokens), evaluate, lambda i, seq: allowed[i]))

    def _allowed_outcomes(self, word):
        """DefaultPOSSequenceValidator.validSequence: the tags of the tag
        dictionary for a known word (None: all tags)"""
        if self.tag_dictionary is None:
            return None
        tags = self.tag_dictionary.get(word if self.case_sensitive else word.lower())
        if tags is None:
            return None
        tags = set(tags)
        return [i for i, outcome in enumerate(self.model.outcome_names) if outcome in tags]


# --- chunker ---

def chunker_context_prefix(i, toks, tags):
    """The first predicates of DefaultChunkerContextGenerator.getContext,
    which don't depend on the previous chunk tags"""
    if i < 2:
        w_2 = 'w_2=bos'
        t_2 = 't_2=bos'
    else:
        w_2 = 'w_2=' + toks[i - 2]
        t_2 = 't_2=' + tags[i - 2]
    if i < 1:
        w_1 = 'w_1=bos'
        t_1 = 't_1=bos'
    else:
        w_1 = 'w_1=' + toks[i - 1]
        t_1 = 't_1=' + tags[i - 1]
    w0 = 'w0=' + toks[i]
    t0 = 't0=' + tags[i]
    n = len(toks)
    if i + 1 >= n:
        w1 = 'w1=eos'
        t1 = 't1=eos'
    else:
        w1 = 'w1=' + toks[i + 1]
        t1 = 't1=' + tags[i + 1]
    if i + 2 >= n:
        w2 = 'w2=eos'
        t2 = 't2=eos'
    else:
        w2 = 'w2=' + toks[i + 2]
        t2 = 't2=' + tags[i + 2]
    return [
        # add word features
        w_2, w_1, w0, w1, w2, w_1 + w0, w0 + w1,
        # add tag features
        t_2, t_1, t0, t1, t2, t_2 + t_1, t_1 + t0, t0 + t1, t1 + t2, t_2 + t_1 + t0, t_1 + t0 + t1, t0 + t1 + t2,
    ], (w_2, w_1, w0, w1, w2, t_2, t_1, t0, t1, t2)


def chunker_context_rest(i, preds, words_and_tags):
    """The rest of DefaultChunkerContextGenerator.getContext: the predicates
    with the previous chunk tags (preds)"""
    w_2, w_1, w0, w1, w2, t_2, t_1, t0, t1, t2 = words_and_tags
    p_2 = 'p_2=bos' if i < 2 else 'p_2' + preds[i - 2]  # sic, no '='
    p_1 = 'p_1=bos' if i < 1 else 'p_1=' + preds[i - 1]
    return [
        # add pred tags
        p_2, p_1, p_2 + p_1,
        # add pred and tag
        p_1 + t_2, p_1 + t_1, p_1 + t0, p_1 + t1, p_1 + t2, p_1 + t_2 + t_1, p_1 + t_1 + t0, p_1 + t0 + t1,
        p_1 + t1 + t2, p_1 + t_2 + t_1 + t0, p_1 + t_1 + t0 + t1, p_1 + t0 + t1 + t2,
        # add pred and word
        p_1 + w_2, p_1 + w_1, p_1 + w0, p_1 + w1, p_1 + w2, p_1 + w_1 + w0, p_1 + w0 + w1,
    ]


def chunker_context(i, toks, tags, preds):
    """DefaultChunkerContextGenerator.getContext"""
    prefix, words_and_tags = chunker_context_prefix(i, toks, tags)
    return prefix + chunker_context_rest(i, preds, words_and_tags)


def _valid_chunk_outcome(prev_outcome, outcome):
    """DefaultChunkerSequenceValidator.validSequence (prev_outcome: the last
    outcome of the sequence, None for the empty sequence)"""
    if outcome.startswith('I-'):
        if prev_outcome is None:
            return False
        if prev_outcome == 'O':
            return False
        return prev_outcome[2:] == outcome[2:]
    return True


class ChunkerME:
    """opennlp.tools.chunker.ChunkerME (ChunkerFactory defaults)"""

    DEFAULT_BEAM_SIZE = 10

    def __init__(self, package):
        factory = package.get_manifest_property('factory')
        if factory is not None and factory != 'opennlp.tools.chunker.ChunkerFactory':
            raise ValueError('Unsupported chunker factory: ' + factory)
        self.model = package.gis_model('chunker.model')
        self.beam = BeamSearch(package.beam_size(self.DEFAULT_BEAM_SIZE), self.model)
        # the valid outcomes after each outcome (and at the start)
        names = self.model.outcome_names
        self._allowed = {prev: [i for i, out in enumerate(names) if _valid_chunk_outcome(prev, out)]
                         for prev in [None] + list(names)}

    def chunk(self, toks, tags):
        """The chunk tags (B-NP, I-NP, O, ...) of the (Java string) tokens
        with their POS tags"""
        model = self.model
        prefixes = {}
        cache = {}

        def evaluate(i, seq):
            # the context depends on the position and the last two chunk tags only
            last = seq[1]
            key = (i, last, seq[2][1] if i >= 2 else None)
            r = cache.get(key)
            if r is None:
                prefix = prefixes.get(i)
                if prefix is None:
                    context, words_and_tags = chunker_context_prefix(i, toks, tags)
                    prefix = prefixes[i] = (model.prefix_sums(context), words_and_tags)
                preds = [None] * i
                if i >= 1:
                    preds[i - 1] = last
                    if i >= 2:
                        preds[i - 2] = key[2]
                r = cache[key] = model.eval_from(prefix[0], chunker_context_rest(i, preds, prefix[1]))
            return r
        allowed = self._allowed
        return sequence_outcomes(self.beam.best_sequence(len(toks), evaluate, lambda i, seq: allowed[seq[1]]))


_packages = {}
_packages_lock = threading.Lock()


def load_package(path):
    """The (cached) ModelPackage of the model file path"""
    with _packages_lock:
        p = _packages.get(path)
        if p is None:
            p = _packages[path] = ModelPackage(path)
        return p
