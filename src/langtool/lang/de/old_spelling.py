"""Port of org.languagetool.rules.de.OldSpellingRule and SpellingData
(spellings that were only correct in the pre-reform orthography, from
/de/alt_neu.csv), plus the Aho-Corasick search (com.hankcs.algorithm.
AhoCorasickDoubleArrayTrie.parseText) with the hit order of the Java
library, also used by ProhibitedCompoundRule."""

import threading

from ... import jregex
from ...rules.abstract_rules import _read_lines, _resource_file
from ...rules.base import RuleMatch
from ...rules.core import CoreRule
from ...tools import java_split, starts_with_lowercase, uppercase_first_char


class AhoCorasickSearch:
    """The hits of AhoCorasickDoubleArrayTrie (built from an ordered map
    keyword -> value) in the order of parseText(): by end position, and for
    the same end position by descending keyword index (the trie's output
    sets are TreeSets in reverse order). Hits are tuples (begin, end,
    value)."""

    def __init__(self, items):
        self._index = {}
        self._values = []
        for k, v in items:
            if not k:
                continue
            if k in self._index:
                self._values[self._index[k]] = v
            else:
                self._index[k] = len(self._values)
                self._values.append(v)
        self._lengths = sorted({len(k) for k in self._index})

    def parse_text(self, text):
        hits = []
        index = self._index
        values = self._values
        lengths = self._lengths
        for end in range(1, len(text) + 1):
            found = []
            for ln in lengths:
                if ln > end:
                    break
                i = index.get(text[end - ln:end])
                if i is not None:
                    found.append((i, end - ln))
            if found:
                found.sort(reverse=True)
                for i, begin in found:
                    hits.append((begin, end, values[i]))
        return hits


_manual_tags_cache = {}


def _manual_tags(manual):
    """lemma -> set of tags of a ManualSynthesizer"""
    r = _manual_tags_cache.get(id(manual))
    if r is None or r[0] is not manual:
        m = {}
        for lem, tag in manual.map:
            m.setdefault(lem, set()).add(tag)
        r = _manual_tags_cache[id(manual)] = (manual, m)
    return r[1]


def _tags_of_lemma(synthesizer, lemma):
    """The POS tags for which the synthesizer may have forms of lemma (the
    tags of the dictionary entries 'lemma|tag' and of the manual
    synthesizer), or None if they cannot be determined."""
    d = getattr(synthesizer, 'dictionary', None)
    manual = getattr(synthesizer, 'manual_synthesizer', None)
    if d is None or d.metadata.input_conversion or (manual is not None and not hasattr(manual, 'map')):
        return None
    md = d.metadata
    tags = set()
    if manual is not None:
        tags.update(_manual_tags(manual).get(lemma, ()))
    try:
        wb = (lemma + '|').encode(md.encoding)
    except UnicodeEncodeError:
        return tags
    fsa = d.fsa
    node = fsa.root
    for b in wb:
        arc = fsa.get_arc(node, b)
        if arc == 0:
            return tags
        node = fsa.destination(arc)
        if node == 0:
            return tags
    # the input parts (tags) of the entries, up to the separator
    sep = md.separator
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
        label = fsa.label(arc)
        if label == sep:
            tags.add(bytes(buf).decode(md.encoding, 'replace'))
            continue
        buf.append(label)
        dest = fsa.destination(arc)
        if dest != 0:
            stack.append(fsa.first_arc(dest))
    return tags


def _synthesize_all_forms(synthesizer, lemma):
    """synthesizer.synthesizeForPosTags(lemma, s -> true), only looking up
    the tags that the dictionary has for lemma (same result, much faster
    than looking up all tags)"""
    tags = _tags_of_lemma(synthesizer, lemma)
    if tags is None:
        return synthesizer.synthesize_for_pos_tags(lemma, lambda s: True)
    return synthesizer.synthesize_for_pos_tags(lemma, lambda s: s in tags)


class SpellingData:
    """Port of SpellingData: old to new spelling data loaded from a CSV
    resource file (the trie and the sentence start trie, in which lowercase
    entries are uppercased). Old spellings with 'ß' whose new spelling only
    replaces it by 'ss' are also added with all their inflected forms (from
    the synthesizer of German (Germany))."""

    def __init__(self, language, file_path):
        lines = _read_lines(_resource_file(language, file_path))
        self._forms = {}  # synthesized forms, computed once for both maps
        self.trie = AhoCorasickSearch(self._coherency_map(lines, file_path, False).items())
        self.sentence_start_trie = AhoCorasickSearch(self._coherency_map(lines, file_path, True).items())

    @staticmethod
    def _synthesizer():
        from ...api import get_language
        return get_language('de-DE').synthesizer

    def _coherency_map(self, lines, file_path, sent_start_mode):
        coherency_map = {}
        for line in lines:
            if line.startswith('#'):
                continue
            parts = java_split(line, ';')
            if len(parts) < 2:
                raise RuntimeError('Unexpected format in file ' + file_path + ': ' + line)
            old_spelling = parts[0]
            new_spelling = parts[1]
            self._sanity_checks(file_path, line, old_spelling, new_spelling, coherency_map)
            if sent_start_mode and starts_with_lowercase(old_spelling) and starts_with_lowercase(new_spelling):
                # lowercase words can be uppercase at sentence start:
                coherency_map[uppercase_first_char(old_spelling)] = uppercase_first_char(new_spelling)
            else:
                coherency_map[old_spelling] = new_spelling
            if 'ß' in old_spelling and old_spelling.replace('ß', 'ss') == new_spelling:
                forms = self._forms.get(old_spelling)
                if forms is None:
                    forms = self._forms[old_spelling] = _synthesize_all_forms(self._synthesizer(), old_spelling)
                for form in forms:
                    if 'ss' not in form:  # avoid e.g. "Schlüsse" as form of "Schluß", as that's the new spelling
                        coherency_map[form] = form.replace('ß', 'ss')
        return coherency_map

    @staticmethod
    def _sanity_checks(file_path, line, old_spelling, new_spelling, coherency_map):
        if old_spelling == new_spelling:
            raise RuntimeError('Old and new spelling are the same in ' + file_path + ': ' + line)
        lookup = coherency_map.get(new_spelling)
        if lookup is not None and lookup == old_spelling:
            raise RuntimeError('Contradictory entry in ' + file_path + ": '" + old_spelling + "' suggests '" + lookup
                               + "' and vice versa")
        if old_spelling in coherency_map and coherency_map[old_spelling] != new_spelling:
            raise RuntimeError('Duplicate key in ' + file_path + ': ' + old_spelling + ', val: '
                               + coherency_map[old_spelling] + ' vs. ' + new_spelling)


_FILE_PATH = '/de/alt_neu.csv'
_EXCEPTIONS = (
    'Schloß Holte',
    'Schloß Neuhaus',
    'Schloß Ricklingen',
    'Schloß-Nauses',
    'Schloß Rötteln',
    'Klinikum Schloß Winnenden',
    'Grazer Schloßberg',
    'Höchster Schloß',
    'Bell Telephone',
    'Telephone Company',
    'American Telephone',
    'England Telephone',
    'Mobile Telephone',
    'Cordless Telephone',
    'Telephone Line',
    'World Telephone',
    'Tip Top',
    'Hans Joachim Blaß',
    'kurz fassen',
)
_CHARS = jregex.compile('[a-zA-Zöäüß]')
_data = []
_data_lock = threading.Lock()


def _spelling_data(language):
    """Suppliers.memoize(() -> new SpellingData(FILE_PATH))"""
    if not _data:
        with _data_lock:
            if not _data:
                _data.append(SpellingData(language, _FILE_PATH))
    return _data[0]


def _region_matches_ignore_case(text, offset, other):
    """text.regionMatches(true, offset, other, 0, other.length())"""
    if offset < 0 or offset + len(other) > len(text):
        return False
    for a, b in zip(text[offset:offset + len(other)], other):
        if a == b:
            continue
        ua = a.upper()
        ub = b.upper()
        if ua == ub:
            continue
        if ua.lower() == ub.lower():
            continue
        return False
    return True


class OldSpellingRule(CoreRule):
    """Port of OldSpellingRule: finds spellings that were only correct in the
    pre-reform orthography."""

    category_id = 'TYPOS'
    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('Der <marker>Abfluß</marker> ist schon wieder verstopft.',
                              'Der <marker>Abfluss</marker> ist schon wieder verstopft.')

    def get_id(self):
        return 'OLD_SPELLING_RULE'

    def get_description(self):
        return 'Findet Schreibweisen, die nur in der alten Rechtschreibung gültig waren'

    def match(self, sentence):
        matches = []
        text = sentence.text
        data = _spelling_data(self.language)
        hits = data.trie.parse_text(text)
        sent_start_hits = data.sentence_start_trie.parse_text(text)
        start_positions = set()
        hits.reverse()  # work on longest matches first
        for hit in hits:
            if hit[0] in start_positions:
                continue  # avoid overlapping matches
            if not self._ignore_match(hit, text):
                self._add_match(sentence, hit, matches)
                start_positions.add(hit[0])
        for hit in sent_start_hits:
            if hit[0] in start_positions:
                continue  # avoid overlapping matches
            if hit[0] == 0 and not self._ignore_match(hit, text):
                # e.g. "Läßt du das bitte", i.e. uppercase at start of sentence
                self._add_match(sentence, hit, matches)
                break  # there can only be one match at the start of a sentence
        return matches

    def _add_match(self, sentence, hit, matches):
        begin, end, value = hit
        message = 'Diese Schreibweise war nur in der alten Rechtschreibung korrekt.'
        match = RuleMatch(self, sentence, begin, end, message, 'Alte Rechtschreibung')
        suggestions = java_split(value, '|')
        match.set_suggested_replacements(suggestions)
        covered = sentence.text[begin:end]
        if suggestions and suggestions[0].replace('ss', 'ß', 1) == covered:
            if self.language.short_code_with_country_and_variant == 'de-AT' and 'geschoß' in covered.lower():
                # special case for Austria: "Geschoß" is correct in both old and new spelling in de-AT
                # (because of the pronunciation)
                return
            match.message = (message + " Das Wort wird mit 'ss' geschrieben, wenn davor eine kurz gesprochene Silbe "
                                       "steht.")
        matches.append(match)

    def _ignore_match(self, hit, text):
        begin, end, _value = hit
        for exception in _EXCEPTIONS:
            if _region_matches_ignore_case(text, begin, exception) or \
                    _region_matches_ignore_case(text, end - len(exception), exception):
                return True
        if begin > 0 and not self._is_boundary(text[begin - 1:begin]):  # prevent substring matches
            return True
        if end < len(text) and not self._is_boundary(text[end:end + 1]):
            # prevent substring matches, e.g. "Foto" for "Photons"
            return True
        if begin - 6 >= 0:
            if text.startswith('Prof.', begin - 6):
                return True
        if begin - 5 >= 0:
            before5 = text[begin - 5:begin - 1]
            if before5 == 'Herr' or before5 == 'Frau':
                return True
        if begin - 4 >= 0:
            before4 = text[begin - 4:begin - 1]
            if before4 in ('Hr.', 'Fr.', 'Dr.'):
                return True
        return False

    @staticmethod
    def _is_boundary(s):
        return _CHARS.fullmatch(s) is None
