"""Port of org.languagetool.rules.nl.CompoundAcceptor."""

import os
import threading

from ... import jregex
from ...rules.abstract_rules import load_word_list

_ACRONYM_PATTERN = jregex.compile('[A-Z]{2,4}-')
_SPECIAL_ACRONYM_PATTERN = jregex.compile('[A-Za-z]{2,4}-')
_NORMAL_CASE_PATTERN = jregex.compile('[A-Za-z][a-zé]*')
MAX_WORD_SIZE = 35

_COMPOUND_NO_S_FILE = 'compound_acceptor/no_s.txt'
_COMPOUND_NEEDS_S_FILE = 'compound_acceptor/needs_s.txt'
_COMPOUND_DIRECTIONS_FILE = 'compound_acceptor/directions.txt'
_COMPOUND_ALWAYS_NEEDS_S_FILE = 'compound_acceptor/always_needs_s.txt'
_COMPOUND_ALWAYS_NEEDS_HYPHEN_FILE = 'compound_acceptor/always_needs_hyphen.txt'
_COMPOUND_PART1_EXCEPTIONS_FILE = 'compound_acceptor/part1_exceptions.txt'
_COMPOUND_PART2_EXCEPTIONS_FILE = 'compound_acceptor/part2_exceptions.txt'
_COMPOUND_ACRONYM_EXCEPTIONS_FILE = 'compound_acceptor/acronym_exceptions.txt'

# Make sure we don't allow compound words where part 1 ends with a specific vowel and part2 starts with one,
# for words like "politieeenheid".
_COLLIDING_VOWELS = frozenset(('aa', 'ae', 'ai', 'au', 'ee', 'ée', 'ei', 'éi', 'eu', 'éu', 'ie', 'ii', 'ij', 'oe',
                               'oi', 'oo', 'ou', 'ui', 'uu'))

_word_lists = {}
_lock = threading.Lock()


def _words(resource_dir, name):
    """CachingWordListLoader.loadWords as a set (cached)"""
    path = os.path.join(resource_dir, name) if resource_dir else None
    with _lock:
        s = _word_lists.get(path)
        if s is None:
            s = _word_lists[path] = frozenset(load_word_list(path)) if path else frozenset()
        return s


class CompoundAcceptor:
    """Accept Dutch compounds that are not accepted by the speller. This
    code is supposed to accept more words in order to extend the speller,
    but it's not meant to accept all valid compounds. It works on 2-part
    compounds only for now.

    Java checks the spelling of the parts with MorfologikDutchSpellerRule
    (spell checking, not ported): a part is spelled correctly if it is in
    the speller dictionary, or if it is an accepted compound itself
    (MorfologikDutchSpellerRule.ignorePotentiallyMisspelledWord). The
    spell checking rule is not ported, its misspelling check is
    (langtool.lang.nl.spelling): a part (in lowercase) is spelled correctly
    if the speller rule would not match it as a sentence of its own, i.e.
    if it is ignored (ignore.txt, spelling.txt etc.), or not misspelled and
    not prohibited, or an accepted compound."""

    def __init__(self, tagger, resource_dir):
        self.dutch_tagger = tagger
        self.no_s = _words(resource_dir, _COMPOUND_NO_S_FILE)
        self.needs_s = _words(resource_dir, _COMPOUND_NEEDS_S_FILE)
        self.geographical_directions = _words(resource_dir, _COMPOUND_DIRECTIONS_FILE)
        self.always_needs_s = _words(resource_dir, _COMPOUND_ALWAYS_NEEDS_S_FILE)
        self.always_needs_hyphen = _words(resource_dir, _COMPOUND_ALWAYS_NEEDS_HYPHEN_FILE)
        self.part1_exceptions = _words(resource_dir, _COMPOUND_PART1_EXCEPTIONS_FILE)
        self.part2_exceptions = _words(resource_dir, _COMPOUND_PART2_EXCEPTIONS_FILE)
        self.acronym_exceptions = _words(resource_dir, _COMPOUND_ACRONYM_EXCEPTIONS_FILE)
        self._acronym_exceptions_upper = frozenset(e.upper() for e in self.acronym_exceptions)
        self._speller = None
        self._spelling_cache = {}

    def accept_compound(self, word, part2=None):
        """acceptCompound(word): whether one of the splits of word is an
        accepted compound; accept_compound(part1, part2): whether the two
        parts form an accepted compound."""
        if part2 is not None:
            return self._accept_parts(word, part2)
        if len(word) > MAX_WORD_SIZE:  # prevent long runtime
            return False
        for i in range(3, len(word) - 3):
            part1 = word[:i]
            part2 = word[i:]
            if part1 != part2 and self._accept_parts(part1, part2):
                return True
        return False

    def get_parts(self, word):
        if len(word) > MAX_WORD_SIZE:  # prevent long runtime
            return []
        for i in range(3, len(word) - 3):
            part1 = word[:i]
            part2 = word[i:]
            if part1 != part2 and self._accept_parts(part1, part2):
                return [part1, part2]
        return []

    def _accept_parts(self, part1, part2):
        part1lc = part1.lower()
        # reject if it's in the exceptions list or if a wildcard is the entirety of part1
        if part1.endswith('s') and part1[:-1] not in self.part1_exceptions and part1 not in self.always_needs_s \
                and part1 not in self.no_s and '-' not in part1:
            for suffix in self.always_needs_s:
                if part1lc.endswith(suffix):
                    return self._is_noun(part2) and self._is_existing_word(part1lc[:-1]) and \
                        self._spelling_ok(part2)
            return part1lc in self.needs_s and self._is_noun(part2) and self._spelling_ok(part1[:-1]) and \
                self._spelling_ok(part2)
        elif part1 in self.geographical_directions:
            return self._is_geographical_compound(part2)  # directions
        elif part1.endswith('-'):  # abbreviations
            return (self._acronym_ok(part1) or part1lc in self.always_needs_hyphen) and self._spelling_ok(part2)
        elif part2.startswith('-'):  # vowel collision
            part2 = part2[1:]
            return part1lc in self.no_s and self._is_noun(part2) and self._spelling_ok(part1) and \
                self._spelling_ok(part2) and self._has_colliding_vowels(part1, part2)
        else:
            return (part1lc in self.no_s or part1lc in self.part1_exceptions) and self._is_noun(part2) and \
                self._spelling_ok(part1) and not self._has_colliding_vowels(part1, part2)

    def _is_noun(self, word):
        if word in self.part2_exceptions:
            return False
        return any(k.pos_tag is not None and k.pos_tag.startswith('ZNW')
                   for k in self.dutch_tagger.get_postags(word))

    def _is_existing_word(self, word):
        return any(k.pos_tag is not None for k in self.dutch_tagger.get_postags(word))

    def _is_geographical_compound(self, word):
        return any(k.pos_tag is not None and k.pos_tag.startswith('ENM:LOC')
                   for k in self.dutch_tagger.get_postags(word))

    @staticmethod
    def _has_colliding_vowels(part1, part2):
        vowels = part1[-1] + part2[0]
        return vowels.lower() in _COLLIDING_VOWELS

    def _acronym_ok(self, non_compound):
        # for compound words like IRA-akkoord, MIDI-bestanden, WK-finalisten
        if _ACRONYM_PATTERN.fullmatch(non_compound):
            return non_compound[:-1] not in self._acronym_exceptions_upper
        elif _SPECIAL_ACRONYM_PATTERN.fullmatch(non_compound):
            # special case acronyms that are accepted only with specific casing
            return non_compound[:-1] in self.acronym_exceptions
        return False

    def _get_speller(self):
        """The misspelling check of MorfologikDutchSpellerRule for Dutch (a
        static speller in Java)"""
        if self._speller is None:
            from ...api import get_language
            self._speller = get_language('nl').get_default_spelling_rule()
        return self._speller

    def _spelling_ok(self, non_compound):
        if not _NORMAL_CASE_PATTERN.fullmatch(non_compound):
            return False  # e.g. kinderenHet -> split as kinder,enHet
        word = non_compound.lower()
        ok = self._spelling_cache.get(word)
        if ok is None:
            # speller.match() of a sentence with this word only (see the class docstring)
            speller = self._get_speller()
            ok = (speller.ignore_word(word) or (not speller.is_misspelled(word) and not speller.is_prohibited(word))
                  or self.accept_compound(word))
            if len(self._spelling_cache) > 100000:
                self._spelling_cache.clear()
            self._spelling_cache[word] = ok
        return ok
