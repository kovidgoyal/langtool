"""Port of org.languagetool.tools.DiffsAsMatches and PseudoMatch: the
differences between a text and a revised version as pseudo matches, with
the needed parts of the java-diff-utils library (version 4.12):
DiffUtils.diff with the MeyersDiff algorithm (PathNode, Change, Patch
with its deltas sorted by source position) and
DiffRowGenerator.SPLITTER_BY_WORD."""

from . import jregex
from .tools import is_punctuation_mark, is_whitespace

# DeltaType
CHANGE = 'CHANGE'
DELETE = 'DELETE'
INSERT = 'INSERT'
EQUAL = 'EQUAL'

# DiffRowGenerator.SPLIT_BY_WORD_PATTERN
_SPLIT_BY_WORD_PATTERN = jregex.compile('\\s+|[,.\\[\\](){}/\\\\*+\\-#]')


def split_by_word(line):
    """DiffRowGenerator.SPLITTER_BY_WORD (splitStringPreserveDelimiter):
    the words and the delimiters (runs of whitespace, single punctuation
    characters) of the line"""
    tokens = []
    if line is not None:
        pos = 0
        for m in _SPLIT_BY_WORD_PATTERN.finditer(line):
            if pos < m.start():
                tokens.append(line[pos:m.start()])
            tokens.append(m.group())
            pos = m.end()
        if pos < len(line):
            tokens.append(line[pos:])
    return tokens


class _PathNode:
    """com.github.difflib.algorithm.myers.PathNode"""

    __slots__ = ('i', 'j', 'prev', 'snake', 'bootstrap')

    def __init__(self, i, j, snake, bootstrap, prev):
        self.i = i
        self.j = j
        self.bootstrap = bootstrap
        if snake:
            self.prev = prev
        else:
            self.prev = None if prev is None else prev.previous_snake()
        self.snake = snake

    def previous_snake(self):
        node = self
        while True:
            if node.bootstrap:
                return None
            if not node.snake and node.prev is not None:
                node = node.prev
                continue
            return node


def _build_path(orig, rev, equalizer):
    """MeyersDiff.buildPath"""
    n = len(orig)
    m = len(rev)
    max_ = n + m + 1
    size = 1 + 2 * max_
    middle = size // 2
    diagonal = [None] * size
    diagonal[middle + 1] = _PathNode(0, -1, True, True, None)
    for d in range(max_):
        for k in range(-d, d + 1, 2):
            kmiddle = middle + k
            kplus = kmiddle + 1
            kminus = kmiddle - 1
            if k == -d or (k != d and diagonal[kminus].i < diagonal[kplus].i):
                i = diagonal[kplus].i
                prev = diagonal[kplus]
            else:
                i = diagonal[kminus].i + 1
                prev = diagonal[kminus]
            diagonal[kminus] = None  # no longer used
            j = i - k
            node = _PathNode(i, j, False, False, prev)
            while i < n and j < m and equalizer(orig[i], rev[j]):
                i += 1
                j += 1
            if i != node.i:
                node = _PathNode(i, j, True, False, node)
            diagonal[kmiddle] = node
            if i >= n and j >= m:
                return diagonal[kmiddle]
        diagonal[middle + d - 1] = None
    # According to Myers, this cannot happen
    raise RuntimeError('could not find a diff path')


def _build_revision(actual_path):
    """MeyersDiff.buildRevision: the changes as (type, start_original,
    end_original, start_revised, end_revised), from the end"""
    path = actual_path
    changes = []
    if path.snake:
        path = path.prev
    while path is not None and path.prev is not None and path.prev.j >= 0:
        if path.snake:
            raise RuntimeError('bad diffpath: found snake when looking for diff')
        i = path.i
        j = path.j
        path = path.prev
        ianchor = path.i
        janchor = path.j
        if ianchor == i and janchor != j:
            changes.append((INSERT, ianchor, i, janchor, j))
        elif ianchor != i and janchor == j:
            changes.append((DELETE, ianchor, i, janchor, j))
        else:
            changes.append((CHANGE, ianchor, i, janchor, j))
        if path.snake:
            path = path.prev
    return changes


class Chunk:
    """com.github.difflib.patch.Chunk: a position and the lines there"""

    __slots__ = ('position', 'lines')

    def __init__(self, position, lines):
        self.position = position
        self.lines = lines


class Delta:
    """com.github.difflib.patch.AbstractDelta (ChangeDelta, DeleteDelta,
    InsertDelta)"""

    __slots__ = ('type', 'source', 'target')

    def __init__(self, delta_type, source, target):
        self.type = delta_type
        self.source = source
        self.target = target

    def __repr__(self):
        return '[%s %d %r -> %r]' % (self.type, self.source.position, self.source.lines, self.target.lines)


def _default_equalizer(a, b):
    return a == b


def diff(original, revised, equalizer=None):
    """DiffUtils.diff(source, target, equalizer) with the MeyersDiff
    algorithm: the deltas of the patch (Patch.getDeltas(), sorted by the
    source position)"""
    if equalizer is None:
        equalizer = _default_equalizer
    path = _build_path(original, revised, equalizer)
    deltas = []
    for delta_type, start_original, end_original, start_revised, end_revised in _build_revision(path):
        deltas.append(Delta(delta_type, Chunk(start_original, list(original[start_original:end_original])),
                            Chunk(start_revised, list(revised[start_revised:end_revised]))))
    # (stable, like List.sort)
    deltas.sort(key=lambda d: d.source.position)
    return deltas


class PseudoMatch:
    """Port of org.languagetool.tools.PseudoMatch"""

    __slots__ = ('replacements', 'from_pos', 'to_pos')

    def __init__(self, replacement, from_pos, to_pos):
        self.replacements = [replacement]
        self.from_pos = from_pos
        self.to_pos = to_pos

    @property
    def replacement(self):
        return self.replacements[0] if self.replacements else None

    def __repr__(self):
        return '%d-%d-[%s]' % (self.from_pos, self.to_pos, ', '.join(self.replacements))


_MAX_CONTIGUOUS_DISTANCE = 3
_INSERT_LOOKBACK_MAX = 2


class DiffsAsMatches:
    """Port of org.languagetool.tools.DiffsAsMatches: converts the diffs
    between two texts into PseudoMatch objects"""

    def __init__(self):
        self.filter_out_apostrophe_diffs = True
        self.join_contiguous_matches = True

    def get_pseudo_matches(self, original, revised):
        """Generate a list of PseudoMatches comparing original and revised
        text."""
        original_tokens = split_by_word(original)
        revised_tokens = split_by_word(revised)
        deltas = diff(original_tokens, revised_tokens)
        matches = self._process_deltas_into_matches(deltas, original_tokens, original)
        if self.filter_out_apostrophe_diffs:
            matches = self._filter_out_apostrophe_diffs(matches, original)
        if self.join_contiguous_matches:
            matches = self._join_contiguous_matches(matches, original)
        return matches

    def _process_deltas_into_matches(self, deltas, original_tokens, original_text):
        """Process all deltas and convert them into PseudoMatches."""
        matches = []
        last_match = None
        last_delta = None
        for delta in deltas:
            # Get the baseline replacement
            replacement = ''.join(delta.target.lines)
            # Compute initial position and adjustment for INSERTs (INSERTs need to underline the previous word)
            error_index = delta.source.position
            index_correction = self._get_index_correction_for_inserts(delta, error_index)
            from_pos = self._get_position_from_token_index(original_tokens, error_index - index_correction)
            # Information about previous token
            was_previous_token_whitespace = self._is_previous_token_whitespace(original_tokens, error_index)
            last_punctuation_str = self._get_previous_punctuation_if_any(original_tokens, error_index)
            # Compute underlined text and final position
            underlined_error = ''.join(delta.source.lines)
            to_pos = from_pos + len(underlined_error)
            # Add prefix for INSERTs
            prefix_replacement = self._build_prefix_for_insert(original_tokens, error_index, index_correction)
            to_pos += len(prefix_replacement)
            replacement = prefix_replacement + replacement
            # Get text from original
            underlined_error = original_text[from_pos:to_pos]
            # Remove leading white spaces
            while (underlined_error and replacement and is_whitespace(underlined_error[0])
                   and is_whitespace(replacement[0])):
                from_pos += 1
                underlined_error = underlined_error[1:]
                replacement = replacement[1:]
            # Special case: INSERT at the sentence start
            if from_pos == 0 and to_pos == 0:
                to_pos = len(original_tokens[0])
                replacement = replacement + original_tokens[0]
            # Remove trailing whitespace in INSERTs
            while (underlined_error and replacement and is_whitespace(underlined_error[-1])
                   and is_whitespace(replacement[-1])):
                to_pos -= 1
                underlined_error = underlined_error[:-1]
                replacement = replacement[:-1]
            # Check whether a merge with previous delta is needed
            if self._should_merge_change_with_insert(delta, last_delta, last_match, was_previous_token_whitespace,
                                                     last_punctuation_str):
                # Merge CHANGE + INSERT: esrealitza -> es realitza (1 match)
                new_replacement = last_match.replacements[0] + last_punctuation_str + replacement[to_pos - from_pos:]
                match = PseudoMatch(new_replacement, last_match.from_pos, to_pos)
                matches.pop()
            elif self._should_merge_with_delete(delta, last_match, from_pos, was_previous_token_whitespace):
                # Merge CHANGE + DELETE: Que el -> El (1 match)
                match = PseudoMatch(last_match.replacements[0], last_match.from_pos, to_pos - 1)
                matches.pop()
            else:
                # independent match
                match = PseudoMatch(replacement, from_pos, to_pos)
            matches.append(match)
            last_match = match
            last_delta = delta
        return matches

    @staticmethod
    def _get_index_correction_for_inserts(delta, error_index):
        """Compute index adjustment for INSERTs (lookback tokens): two tokens
        before (INSERT_LOOKBACK_MAX = 2): 1 whitespace + 1 previous words"""
        correction = 0
        if delta.type == INSERT:
            correction = _INSERT_LOOKBACK_MAX
            while error_index - correction < 0 and correction > 0:
                correction -= 1
        return correction

    @staticmethod
    def _is_previous_token_whitespace(tokens, error_index):
        if 0 <= error_index - 1 < len(tokens):
            return is_whitespace(tokens[error_index - 1])
        return False

    @staticmethod
    def _get_previous_punctuation_if_any(tokens, error_index):
        if 0 <= error_index - 1 < len(tokens):
            token = tokens[error_index - 1]
            if is_punctuation_mark(token):
                return token
        return ''

    @staticmethod
    def _build_prefix_for_insert(tokens, error_index, index_correction):
        return ''.join(tokens[error_index - index_correction:error_index])

    @staticmethod
    def _get_position_from_token_index(tokens, token_index):
        return sum(len(t) for t in tokens[:token_index])

    @staticmethod
    def _should_merge_change_with_insert(current_delta, previous_delta, previous_match, was_previous_whitespace,
                                         last_punctuation_str):
        if previous_match is None or previous_delta is None:
            return False
        if previous_delta.type != CHANGE or current_delta.type != INSERT:
            return False
        if not was_previous_whitespace and not last_punctuation_str:
            return False
        current_position = current_delta.source.position
        previous_end_position = previous_delta.source.position + len(previous_delta.source.lines)
        return current_position - 1 == previous_end_position

    @staticmethod
    def _should_merge_with_delete(current_delta, previous_match, current_from_pos, was_previous_whitespace):
        if previous_match is None:
            return False
        if current_delta.type != DELETE:
            return False
        if not was_previous_whitespace:
            return False
        return previous_match.to_pos + 1 == current_from_pos

    def get_joined_match(self, pseudo_matches, original_sentence, pattern_from, pattern_to):
        """Join all matches inside a specific segment"""
        if not pseudo_matches:
            return None
        min_from = -1
        max_to = -1
        previous_to = -1
        suggestion = []
        for match in pseudo_matches:
            if (min_from != -1 and max_to == -1) or self._is_match_in_range(match, pattern_from, pattern_to):
                if min_from == -1:
                    min_from = match.from_pos
                elif match.from_pos > previous_to:
                    # add text between matches
                    suggestion.append(original_sentence[previous_to:match.from_pos])
                suggestion.append(match.replacements[0])
                max_to = match.to_pos
            previous_to = match.to_pos
        if min_from > -1 and max_to > 0:
            return PseudoMatch(''.join(suggestion), min_from, max_to)
        return None

    @staticmethod
    def _is_match_in_range(match, pattern_from, pattern_to):
        return (pattern_from <= match.from_pos <= pattern_to) or (pattern_from <= match.to_pos <= pattern_to)

    @staticmethod
    def _filter_out_apostrophe_diffs(pseudo_matches, original):
        results = []
        for match in pseudo_matches:
            original_part = original[match.from_pos:match.to_pos]
            if original_part.replace('’', "'") != match.replacement.replace('’', "'"):
                results.append(match)
        return results

    @staticmethod
    def _join_contiguous_matches(pseudo_matches, original):
        """Join contiguous matches (less than 3 chars of separation)."""
        results = []
        previous_end_position = -1
        for match in pseudo_matches:
            if previous_end_position > -1 and match.from_pos - previous_end_position < _MAX_CONTIGUOUS_DISTANCE:
                results[-1] = DiffsAsMatches._join_with_previous_match(match, results[-1], original)
            else:
                results.append(match)
            previous_end_position = match.to_pos
        return results

    @staticmethod
    def _join_with_previous_match(current_match, previous_match, original):
        replacement = previous_match.replacement
        # text between matches
        if previous_match.to_pos < current_match.from_pos:
            replacement += original[previous_match.to_pos:current_match.from_pos]
        replacement += current_match.replacement
        return PseudoMatch(replacement, previous_match.from_pos, current_match.to_pos)
