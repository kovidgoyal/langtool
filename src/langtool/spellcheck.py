"""User-facing spell checking with Hunspell dictionaries.

HunspellSpellingRule is a spell checking rule (id HUNSPELL_RULE, category
TYPOS, issue type misspelling) based on LanguageTool's HunspellRule and
SpellingCheckRule (langtool.hunspell_rule): the text of the sentence
without URLs, e-mail addresses and immunized tokens is split into words at
the non-word characters of the dictionary (non-letters except the
WORDCHARS of the .aff file), words are checked with Hunspell
(langtool.hunspell) and the misspelled ones are reported with Hunspell's
suggestions. Like in LanguageTool, words without letters, words of the
language's ignore and spelling lists (ignore.txt, spelling.txt, the list of
the variant ...; multi-word entries are applied as phrases), "LanguageTool"
and, as LanguageTool's spellers do it by default, words containing digits
are ignored; words of the prohibit lists are always errors. All-uppercase
words (abbreviations) and, in languages not written in Latin script, words
in Latin script are ignored too (see the class attributes).

The rule uses the Hunspell dictionary given by the API consumer or the
LibreOffice dictionary of the language (see langtool.hunspell_dictionaries).
It is independent of the internal speller lookups of the filters and rules
(Language.get_default_spelling_rule()), which keep using LanguageTool's own
dictionaries.

The rules are shared (one per language variant and dictionary); the
results of the misspelling check and the suggestions are cached per word.
"""

import os
import threading
import warnings

import regex

from .dictionaries import DictionaryNotFound
from .hunspell_rule import HunspellRule, SpellingCheckRule, compute_non_word_pattern, read_lines, resource_file
from .language import DATA_DIR
from .rules.base import SuggestedReplacement

RULE_ID = 'HUNSPELL_RULE'
SPELLING_DATA_DIR = os.path.join(DATA_DIR, 'spelling')
CACHE_SIZE = 100000
_LATIN_WORD = regex.compile(r"[\p{script=latin}\p{M}'’.-]+")

# languages whose words are not written in Latin script (SpellingCheckRule.isLatinScript() is false for
# their spelling rules in LanguageTool)
_NON_LATIN = frozenset(('ar', 'be', 'crh', 'el', 'fa', 'ja', 'km', 'ml', 'ru', 'ta', 'uk', 'zh'))


def _word_list_path(language, name):
    """The path of a word list (name relative to the resource directory,
    e.g. 'en/hunspell/spelling.txt'): a resource of the language (also
    downloaded with the dictionaries of the language), else the copy in
    data/spelling, else None"""
    if not name:
        return None
    try:
        p = resource_file(language, name)
    except DictionaryNotFound as e:
        warnings.warn('spell checking: word list %s not available: %s' % (name, e))
        p = None
    if p is None:
        cand = os.path.join(SPELLING_DATA_DIR, name.lstrip('/'))
        if os.path.exists(cand):
            p = cand
    return p


_word_lists = {}
_word_lists_lock = threading.Lock()


def _load_words(language, name):
    """CachingWordListLoader.loadWords for a word list (see
    _word_list_path), no words if it doesn't exist"""
    path = _word_list_path(language, name)
    if path is None:
        return ()
    with _word_lists_lock:
        r = _word_lists.get(path)
    if r is None:
        from .rules.abstract_rules import load_word_list
        r = tuple(load_word_list(path))
        with _word_lists_lock:
            _word_lists[path] = r
    return r


class HunspellSpellingRule(HunspellRule):
    """The spell checking rule: HunspellRule with a given Hunspell
    dictionary (aff and dic paths) and the word lists of the language.

    The file names of the word lists, the line expansion, the script and
    the ignored word length are those of the language's spelling rule in
    LanguageTool (taken from Language.get_default_spelling_rule() where it
    is ported, else SpellingCheckRule's defaults <lang>/hunspell/...)."""

    RULE_ID = RULE_ID
    # ignore words written in uppercase letters only (abbreviations)
    ignore_all_uppercase = True
    # ignore words that contain a digit (morfologik's ignore-numbers, on by default in LanguageTool)
    ignore_words_with_digits = True
    # ignore words in Latin script in languages written in another script (names, foreign words)
    ignore_latin_words = True
    # the time limit of Hunspell's suggestion search for a word in seconds (like the CPU time limits of
    # Hunspell, which the port does not emulate; some words take a minute without a limit), None: no limit
    suggestion_time_limit = 1.0

    def __init__(self, messages, language, aff_path, dic_path):
        super().__init__(messages, language)
        self.aff_path = aff_path
        self.dic_path = dic_path
        self._converts_case = True
        self._misspelled_cache = {}
        self._suggestion_cache = {}
        try:
            self._source = language.get_default_spelling_rule()
        except Exception:  # e.g. a missing dictionary of the internal speller
            self._source = None
        n = getattr(self._source, 'ignore_words_with_length', 0)
        self.ignore_words_with_length = n if isinstance(n, int) else 0

    def get_id(self):
        return RULE_ID

    # --- the word lists of the language's spelling rule ---

    def _from_source(self, method, default):
        f = getattr(self._source, method, None)
        return f() if f is not None else default

    def get_ignore_file_name(self):
        return self._from_source('get_ignore_file_name', super().get_ignore_file_name())

    def get_spelling_file_name(self):
        return self._from_source('get_spelling_file_name', super().get_spelling_file_name())

    def get_additional_spelling_file_names(self):
        names = list(self._from_source('get_additional_spelling_file_names',
                                       super().get_additional_spelling_file_names()))
        names.append(self._from_source('get_language_variant_spelling_file_name', None))
        names.extend(self._from_source('get_additional_ignore_file_names', ()))
        return [n for n in names if n]

    def get_prohibit_file_name(self):
        return self._from_source('get_prohibit_file_name', super().get_prohibit_file_name())

    def get_additional_prohibit_file_names(self):
        return list(self._from_source('get_additional_prohibit_file_names',
                                      super().get_additional_prohibit_file_names()))

    def tokenize_new_words(self):
        return self._from_source('tokenize_new_words', True)

    def is_latin_script(self):
        if self._source is not None and hasattr(self._source, 'is_latin_script'):
            return self._source.is_latin_script()
        return self.language.short_code not in _NON_LATIN

    def expand_line(self, line):
        f = getattr(self._source, 'expand_line', None)
        return f(line) if f is not None else [line]

    def _spelling_lines(self, line):
        """the words of a line of a spelling/ignore list: the line itself,
        and the words the language's speller takes from it
        (Language.prepareLineForSpeller, the line expansion of
        GermanSpellerRule)"""
        out = [line]
        prepare = getattr(self._source, 'prepare_line_for_speller', None)
        prepared = prepare(line) if prepare is not None else [line]
        for p in prepared:
            p = p.split('#')[0].strip()
            if not p:
                continue
            for w in (self.expand_line(p) if isinstance(self._source, SpellingCheckRule) else [p]):
                if w and w not in out:
                    out.append(w)
        return out

    def init(self):
        """SpellingCheckRule.init and HunspellRule.init with the dictionary of
        the rule"""
        lang = self.language
        names = [self.get_ignore_file_name(), self.get_spelling_file_name()]
        names.extend(self.get_additional_spelling_file_names())
        seen = set()
        for name in names:
            if not name or name in seen:
                continue
            seen.add(name)
            for line in _load_words(lang, name):
                for w in self._spelling_lines(line):
                    self.add_ignore_words(w)
        self._update_ignored_word_dictionary()
        for name in [self.get_prohibit_file_name()] + self.get_additional_prohibit_file_names():
            for line in _load_words(lang, name):
                self.add_prohibited_words(self.expand_line(line))
        from .hunspell import get_dictionary
        self.hunspell = get_dictionary(self.dic_path, self.aff_path)
        # HunspellRule.addIgnoreWords: the raw lines of the ignore file
        path = _word_list_path(lang, self.get_ignore_file_name())
        if path is not None:
            self.words_to_be_ignored.update(line for line in read_lines(path) if not line.startswith('#'))
        self.set_non_word_pattern(compute_non_word_pattern(self.aff_path))

    # --- checks ---

    def ignore_word(self, word):
        if super().ignore_word(word):
            return True
        if self.ignore_words_with_digits and any(c.isdigit() for c in word):
            return True
        if self.ignore_all_uppercase and len(word) > 1 and word.isupper():
            return True
        if self.ignore_latin_words and not self.is_latin_script() and _LATIN_WORD.fullmatch(word):
            return True
        return False

    def is_misspelled(self, word):
        self.ensure_initialized()
        cache = self._misspelled_cache
        r = cache.get(word)
        if r is None:
            r = HunspellRule.is_misspelled(self, word)
            if len(cache) >= CACHE_SIZE:
                cache.clear()
            cache[word] = r
        return r

    def create_wrong_split_match(self, sentence, rule_matches_so_far, pos, covered_word, suggestion1, suggestion2,
                                 prev_pos):
        # "thanky ou" -> "thank you", but not "a de facto" -> "ad e": no splits that leave a single letter
        # (LanguageTool's Hunspell languages avoid them with lists of common words)
        if len(suggestion1) < 2 or len(suggestion2) < 2:
            return None
        return super().create_wrong_split_match(sentence, rule_matches_so_far, pos, covered_word, suggestion1,
                                                suggestion2, prev_pos)

    def get_suggestions(self, word):
        """Hunspell's suggestions (with the time limit)"""
        self.ensure_initialized()
        return list(self.hunspell.suggest(word, self.suggestion_time_limit))

    def calc_suggestions(self, word, clean_word):
        key = (word, clean_word)
        cache = self._suggestion_cache
        r = cache.get(key)
        if r is None:
            r = tuple((s.replacement, s.short_description, s.suffix)
                      for s in HunspellRule.calc_suggestions(self, word, clean_word))
            if len(cache) >= CACHE_SIZE // 10:
                cache.clear()
            cache[key] = r
        return [SuggestedReplacement(*t) for t in r]

    def suggest(self, word):
        """The suggestions for a word (strings), as in the rule matches"""
        self.ensure_initialized()
        return [s.replacement for s in self.calc_suggestions(word, word[:-1] if word.endswith('.') else word)]


_rules = {}
_rules_lock = threading.Lock()


def get_rule(messages, language, aff_path, dic_path):
    """The (shared) spell checking rule for the language and dictionary."""
    key = (language.code, os.path.abspath(aff_path), os.path.abspath(dic_path))
    with _rules_lock:
        r = _rules.get(key)
        if r is None:
            r = _rules[key] = HunspellSpellingRule(messages, language, aff_path, dic_path)
        return r


__all__ = ['HunspellSpellingRule', 'RULE_ID', 'get_rule']
