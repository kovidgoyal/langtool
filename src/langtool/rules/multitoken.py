"""Port of org.languagetool.rules.spelling.multitoken.MultitokenSpeller:
an ultra-naive speller that provides spelling suggestions for multitoken
words (usually proper nouns) from a list of words."""

import threading

import regex

from ..tools import is_capitalized_word, remove_diacritics, char_to_lower
from .abstract_rules import java_hash_set_order, _read_lines, _substring_before
from ..tools import java_split, java_trim

MAX_LENGTH_DIFF = 3
_WHITESPACE_AND_SEP = regex.compile(r'\p{Zs}+')
_CACHE_SIZE = 20000


def _levenshtein_distance(s1, s2):
    """org.apache.commons.text.similarity.LevenshteinDistance (unlimited)"""
    if s1 == s2:
        return 0
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        cur = [i]
        for j, c2 in enumerate(s2, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (c1 != c2)))
        prev = cur
    return prev[-1]


from .._base import speedups as _speedups  # noqa: E402

levenshtein_distance = _speedups.levenshtein if _speedups is not None else _levenshtein_distance


def is_anagram(s1, s2):
    """StringTools.isAnagram"""
    return len(s1) == len(s2) and sorted(s1) == sorted(s2)


def _is_space_char(c):
    # Character.isSpaceChar: Zs, Zl, Zp
    return regex.match(r'[\p{Zs}\p{Zl}\p{Zp}]', c) is not None


def convert_to_title_case_iterating_chars(text):
    """StringTools.convertToTitleCaseIteratingChars"""
    if not text:
        return text
    out = []
    convert_next = True
    for ch in text:
        if _is_space_char(ch) or ch == '-':
            convert_next = True
        elif convert_next:
            t = ch.title()
            ch = t if len(t) == 1 else ch
            convert_next = False
        else:
            ch = char_to_lower(ch)
        out.append(ch)
    return ''.join(out)


def _split_by_space(s):
    """StringUtils.split(s, ' '): no empty parts"""
    return [p for p in s.split(' ') if p]


def get_normalize_key(word):
    return remove_diacritics(word.lower()).replace('-', ' ')


class WeightedSuggestion:
    __slots__ = ('word', 'weight')

    def __init__(self, word, weight):
        self.word = word
        self.weight = weight

    def __repr__(self):
        return '%s/%d' % (self.word, self.weight)


def _char_distance(a, b):
    # TODO: full keyboard distances
    if a == b:
        return 0
    if (a, b) in (('s', 'z'), ('z', 's'), ('b', 'v'), ('v', 'b')):
        return 0.2
    if (a, b) in (('i', 'y'), ('y', 'i')):
        return 0
    return 1


def _normalize_similar_chars(s):
    return s.replace('y', 'i').replace('ko', 'co').replace('ka', 'ca')


def _levenshtein(s1, s2):
    """MultitokenSpeller.levenshteinDistance"""
    if s1.replace(' ', '') == s2.replace(' ', ''):
        return 0
    distance = levenshtein_distance(s1, s2)
    ns1 = _normalize_similar_chars(s1)
    ns2 = _normalize_similar_chars(s2)
    if s1 != ns1 or s2 != ns2:
        distance = min(distance, levenshtein_distance(ns1, ns2))
    anagram = is_anagram(s1, s2)
    # consider transpositions without having a Damerau-Levenshtein method
    if distance > 1 and anagram:
        distance -= 1
    if distance > 0 and len(s1) == len(s2) and anagram:
        distance = 1
    return distance


class MultitokenSpeller:
    """Subclasses may override is_exception() and
    get_additional_suggestions(). spelling_rule is the language's default
    spelling rule (Language.getDefaultSpellingRule(), here its misspelling
    check, see langtool.spelling). Without one, discard_run_on_words(),
    which asks it whether the words of a different split are spelled
    correctly, never discards an input (in Java a missing spelling rule
    would cause a NullPointerException there)."""

    def __init__(self, language, file_paths, spelling_rule=None):
        self.language = language
        self.spelling_rule = spelling_rule
        self._lock = threading.Lock()
        self._cache = {}
        self.suggestions_map = {}
        self.suggestions_map_no_spaces_key = {}
        self.candidate_parts_by_key = {}
        self._init(file_paths)

    def _init(self, file_paths):
        by_char = self.suggestions_map
        for path in file_paths:
            for line_original in _read_lines(path):
                if not line_original or line_original[0] == '#':  # ignore comments
                    continue
                for line in self.prepare_line_for_speller(java_trim(_substring_before(line_original, '#'))):
                    if not line:
                        continue
                    normalized_key = get_normalize_key(line)
                    if ' ' not in normalized_key:
                        # Ignore one-token suggestions. They are provided by the spelling rule, or other rules
                        continue
                    m = by_char.setdefault(normalized_key[0], {})
                    if normalized_key not in m:
                        self.candidate_parts_by_key[normalized_key] = _split_by_space(normalized_key)
                    _add_to_map(m, normalized_key, line)
                    _add_to_map(self.suggestions_map_no_spaces_key, normalized_key.replace(' ', ''), line)
        # the iteration order of the Java HashMaps (the search depends on it)
        self._ordered_keys = {c: java_hash_set_order(list(m)) for c, m in by_char.items()}

    def prepare_line_for_speller(self, s):
        """Language.prepareLineForSpeller"""
        return [s]

    def get_suggestions(self, original_word, are_tokens_accepted_by_speller=False):
        original_word = _WHITESPACE_AND_SEP.sub(' ', original_word)
        r = self._cache.get(original_word)
        if r is None:
            # (the Java cache is keyed by the word only)
            r = self._compute_suggestions(original_word, are_tokens_accepted_by_speller)
            with self._lock:
                if len(self._cache) > _CACHE_SIZE:
                    self._cache.clear()
                self._cache[original_word] = r
        return list(r)

    def _compute_suggestions(self, original_word, are_tokens_accepted_by_speller):
        word = original_word.replace('- ', '-').replace(' -', '-')
        if self.discard_run_on_words(word):
            return []
        normalized_word = get_normalize_key(word)
        weighted = []
        # try searching the key
        normalized_word_no_spaces = normalized_word.replace(' ', '')
        candidates = self.suggestions_map_no_spaces_key.get(normalized_word_no_spaces)
        if candidates is not None:
            if self._stop_searching(candidates, original_word):
                return []
            for candidate in candidates:
                weighted.append(WeightedSuggestion(candidate, 0))
        first_char = normalized_word[0]
        candidates_by_key = self.suggestions_map.get(first_char)
        if not weighted and candidates_by_key is not None:
            word_parts = _split_by_space(normalized_word)
            min_length = len(word) - MAX_LENGTH_DIFF
            max_length = len(word) + MAX_LENGTH_DIFF
            for normalized_candidate in self._ordered_keys[first_char]:
                candidate_length = len(normalized_candidate)
                if candidate_length < min_length or candidate_length > max_length:
                    continue
                candidates = candidates_by_key[normalized_candidate]
                if self._stop_searching(candidates, original_word):
                    return []
                candidate_parts = self.candidate_parts_by_key[normalized_candidate]
                distances = self._distances_per_word(candidate_parts, word_parts, normalized_candidate,
                                                     normalized_word)
                total_distance = sum(distances)
                if total_distance < 1:
                    for candidate in candidates:
                        weighted.append(WeightedSuggestion(candidate, 0))
                    # "continue" allows several candidates with different casing
                    if len(weighted) == 2:
                        break
                    continue
                # for very short candidates, allow only distance=0 (casing and diacritics differences)
                if candidate_length < 7:
                    continue
                exceeds = False
                for i, d in enumerate(distances):
                    # usually 2, but 1 for short words
                    max_distance = 2 if len(word_parts[i]) > 5 and len(candidate_parts[i]) > 4 else 1
                    if d > max_distance:
                        exceeds = True
                        break
                if exceeds:
                    continue
                if total_distance <= self._max_edit_distance(normalized_candidate, normalized_word):
                    for candidate in candidates:
                        weighted.append(WeightedSuggestion(candidate, total_distance))
        for additional in self.get_additional_suggestions(word):
            if additional.word != original_word:
                weighted.append(additional)
            else:
                return []
        if not weighted:
            return []
        weighted.sort(key=lambda w: w.weight)  # stable, like Collections.sort
        weight_first = weighted[0].weight
        if are_tokens_accepted_by_speller and weighted[0].word.upper() == original_word:
            # don't correct all-upper case words accepted by the speller
            return []
        if are_tokens_accepted_by_speller and weight_first > 1:
            return []
        results = []
        for w in weighted:
            # keep only candidates with the distance of the first candidate
            if w.weight - weight_first < 1 and w.word not in results:
                results.append(w.word)
        return results

    def _stop_searching(self, candidates, original_word):
        for candidate in candidates:
            if self.is_exception(original_word, candidate):
                return True
            if candidate == original_word:
                return True
        for candidate in candidates:
            if candidate == candidate.lower() and convert_to_title_case_iterating_chars(candidate) == original_word:
                return True
        return False

    @staticmethod
    def _max_edit_distance(normalized_candidate, normalized_word):
        total_length = len(normalized_word)
        correct_length = total_length - _number_of_correct_chars(normalized_candidate, normalized_word)
        first_char_wrong = sum(_first_character_distances(normalized_candidate, normalized_word))
        if correct_length <= 7:
            return int(2 - first_char_wrong)
        return int(2 + 0.25 * (correct_length - 7) - 0.6 * first_char_wrong)

    @staticmethod
    def _distances_per_word(parts1, parts2, s1, s2):
        if len(parts1) == len(parts2) and len(parts1) > 1:
            return [_levenshtein(a, b) for a, b in zip(parts1, parts2)]
        return [_levenshtein(s1, s2)]

    def discard_run_on_words(self, underlined_error):
        parts = _split_by_space(underlined_error)
        if len(parts) == 2:
            if is_capitalized_word(parts[1]):
                return False
            if not parts[0] or not parts[1]:
                # probably emojis, or mal-formed chars
                return True
            if self.spelling_rule is None:
                # no spelling rule (see the class docstring)
                return False
            sr = self.spelling_rule
            sugg1a = parts[0][:-1]
            sugg1b = parts[0][-1:] + parts[1]
            if not sr.is_misspelled(sugg1a) and not sr.is_misspelled(sugg1b):
                return True
            sugg2a = parts[0] + parts[1][0]
            sugg2b = parts[1][1:]
            return not sr.is_misspelled(sugg2a) and not sr.is_misspelled(sugg2b)
        return False

    def is_exception(self, original, candidate):
        return False

    def get_additional_suggestions(self, original_word):
        return []


def _add_to_map(m, key, value):
    lst = m.setdefault(key, [])
    if value not in lst:
        lst.append(value)


def _number_of_correct_chars(s1, s2):
    parts1 = java_split(s1, ' ')
    parts2 = java_split(s2, ' ')
    correct = 0
    if len(parts1) == len(parts2) and len(parts1) > 1:
        for a, b in zip(parts1, parts2):
            if a == b:
                correct += len(a)
    return correct


def _first_character_distances(s1, s2):
    parts1 = _split_by_space(s1)
    parts2 = _split_by_space(s2)
    # for now, only phrase with two tokens
    if len(parts1) == len(parts2) == 2:
        return [_char_distance(a[0], b[0]) for a, b in zip(parts1, parts2)]
    return [0]
