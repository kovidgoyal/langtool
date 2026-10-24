"""The misspelling check of the morfologik based spell checkers.

Port of the parts of the Java speller stack that decide whether a word is
misspelled: morfologik's Speller.isMisspelled/isInDictionary (with the
encoding, input conversion, case and ignore settings of the dictionary's
.info file), LanguageTool's MorfologikSpeller.isMisspelled,
MorfologikMultiSpeller.isMisspelled (the binary speller dictionary plus the
plain text word lists like spelling.txt), MorfologikSpellerRule.isMisspelled
and the word lists of SpellingCheckRule (ignore.txt and the spelling files
for ignoreWord(), prohibit.txt for isProhibited()).

This is the misspelling check only: there are no suggestions and no spell
checking rules (the speller rules are still not provided). It is used by
ported code that asks the default spelling rule of a language whether a word
is spelled correctly (filters, compound acceptors etc.). A language provides
its check by registering a factory (language -> MorfologikMisspellingCheck)
with langtool.extensions.register('default_spelling_rule', ...), see
Language.get_default_spelling_rule().
"""

import os
import threading
import unicodedata

import regex

from .rules.abstract_rules import load_word_list
from .tools import is_digit, is_letter, is_lower_case, is_mixed_case, is_upper_case

LANGUAGETOOL = 'LanguageTool'  # SpellingCheckRule.LANGUAGETOOL
LANGUAGETOOLER = 'LanguageTooler'  # SpellingCheckRule.LANGUAGETOOLER
MAX_TOKEN_LENGTH = 200  # SpellingCheckRule.MAX_TOKEN_LENGTH

_HAS_NO_LETTER_LATIN = regex.compile(r'[^\p{script=latin}]+')
_HAS_NO_LETTER = regex.compile(r'[^\p{L}]+')
_LINE_BREAK = regex.compile('\r\n|\r|\n')  # BufferedReader.readLine
_ALPHABETIC_CATEGORIES = frozenset(('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl'))


def _boolean_value(value):
    """DictionaryAttribute.booleanValue"""
    v = value.lower()
    if v in ('true', 'yes', 'on'):
        return True
    if v in ('false', 'no', 'off'):
        return False
    raise ValueError('Not a boolean value: ' + value)


def java_to_lower(s, locale):
    """String.toLowerCase(Locale) for a locale language code (only Turkish,
    Azerbaijani and Lithuanian have special rules in Java; the Lithuanian
    ones only concern combining dots)"""
    if locale in ('tr', 'az'):
        s = s.replace('İ', 'i').replace('I', 'ı').replace('İ', 'i')
    return s.lower()


class SpellerMetadata:
    """The speller attributes of morfologik's DictionaryMetadata (defaults as
    in DictionaryMetadata.DEFAULT_ATTRIBUTES)."""

    def __init__(self, metadata):
        props = metadata.props

        def flag(key):
            v = props.get('fsa.dict.speller.' + key)
            return True if v is None else _boolean_value(v.strip())
        self.metadata = metadata
        self.encoding = metadata.encoding
        self.separator = metadata.separator
        self.separator_char = metadata.separator_char
        self.input_conversion = metadata.input_conversion
        self.ignore_punctuation = flag('ignore-punctuation')
        self.ignore_numbers = flag('ignore-numbers')
        self.ignore_camel_case = flag('ignore-camel-case')
        self.ignore_all_uppercase = flag('ignore-all-uppercase')
        self.convert_case = flag('convert-case')
        # new Locale(value), the default locale otherwise (no special case mapping assumed)
        self.locale = (props.get('fsa.dict.speller.locale') or '').strip().lower() or None


def _apply_replacements(word, replacements):
    """DictionaryLookup.applyReplacements"""
    for key, value in replacements.items():
        index = word.find(key)
        while index != -1:
            word = word[:index] + value + word[index + len(key):]
            index = word.find(key, index + len(key))
    return word


def _is_alphabetic(c):
    """Speller.isAlphabetic (Character.isAlphabetic for the BMP)"""
    return unicodedata.category(c) in _ALPHABETIC_CATEGORIES


def _contains_no_digit(s):
    return not any(is_digit(c) for c in s)


def _is_all_uppercase(s):
    return not any(is_letter(c) and is_lower_case(c) for c in s)


def _is_not_all_lowercase(s):
    return any(is_letter(c) and not is_lower_case(c) for c in s)


def _is_not_capitalized_word(s):
    if s and is_upper_case(s[0]):
        return any(is_letter(c) and not is_lower_case(c) for c in s[1:])
    return True


def _is_mixed_case(s):
    return not _is_all_uppercase(s) and _is_not_capitalized_word(s) and _is_not_all_lowercase(s)


def _is_camel_case(s):
    return (bool(s) and not _is_all_uppercase(s) and _is_not_capitalized_word(s) and is_upper_case(s[0])
            and (len(s) <= 1 or is_lower_case(s[1])) and _is_not_all_lowercase(s))


class _FSAWords:
    """The words of a binary morfologik speller dictionary (entries
    word + separator + frequency etc.): isInDictionary of morfologik's
    Speller with FSATraversal.match."""

    def __init__(self, fsa):
        self.fsa = fsa

    def contains(self, wb, has_separator, separator):
        fsa = self.fsa
        node = fsa.root
        last = len(wb) - 1
        for i, b in enumerate(wb):
            arc = fsa.get_arc(node, b)
            if arc == 0:
                return False  # NO_MATCH or AUTOMATON_HAS_PREFIX
            if i == last and fsa.is_final(arc):
                # EXACT_MATCH: accepted if the word doesn't contain the separator
                return not has_separator
            node = fsa.destination(arc)
            if node == 0:
                return False  # AUTOMATON_HAS_PREFIX (terminal arc)
        # SEQUENCE_IS_A_PREFIX: accepted if the separator follows
        return len(wb) > 0 and fsa.get_arc(node, separator) != 0


class _PlainWords:
    """The words of the plain text word lists (in Java an FSA built from the
    lines, with the metadata of the binary dictionary): a line is a word
    (exact match) or, if it contains the separator, the part before it is
    one (prefix match followed by the separator)."""

    def __init__(self, lines, separator):
        self.lines = frozenset(lines)
        prefixes = set()
        sep = bytes((separator,))
        for line in self.lines:
            i = line.find(sep)
            while i != -1:
                prefixes.add(line[:i])
                i = line.find(sep, i + 1)
        self.prefixes = frozenset(prefixes)

    def contains(self, wb, has_separator, separator):
        if wb in self.lines:
            return not has_separator
        return len(wb) > 0 and wb in self.prefixes


class MorfologikSpeller:
    """MorfologikSpeller.isMisspelled with morfologik's Speller.isMisspelled
    (the misspelling check only). words is the word store (_FSAWords or
    _PlainWords), metadata the SpellerMetadata of the dictionary.

    morfologik's Speller has a field containsSeparators that is switched off
    after the first exact match of a word without separator; here every
    lookup behaves like the first one (for binary speller dictionaries,
    whose entries all contain the separator, this makes no difference)."""

    def __init__(self, words, metadata):
        self.words = words
        self.md = metadata

    def is_in_dictionary(self, word):
        md = self.md
        try:
            wb = word.encode(md.encoding)
        except UnicodeEncodeError:
            return False  # UnmappableInputException
        return self.words.contains(wb, md.separator_char in word, md.separator)

    def is_misspelled(self, word):
        if not word or word == LANGUAGETOOL or word == LANGUAGETOOLER:
            return False
        md = self.md
        w = word
        if md.input_conversion:
            w = _apply_replacements(word, md.input_conversion)
        is_alphabetic = len(w) != 1 or _is_alphabetic(w)
        return (len(w) > 0
                and (not md.ignore_punctuation or is_alphabetic)
                and (not md.ignore_numbers or _contains_no_digit(w))
                and not (md.ignore_camel_case and _is_camel_case(w))
                and not (md.ignore_all_uppercase and is_alphabetic and _is_all_uppercase(w))
                and not self.is_in_dictionary(w)
                and (not md.convert_case
                     or not (not _is_mixed_case(w)
                             and (self.is_in_dictionary(java_to_lower(w, md.locale))
                                  or _is_all_uppercase(w)
                                  and self.is_in_dictionary(w[:1] + java_to_lower(w[1:], md.locale))))))

    def converts_case(self):
        return self.md.convert_case


def read_plain_text_lines(paths, prepare_line=None):
    """The lines of the plain text word lists as MorfologikMultiSpeller reads
    them (UTF-8 bytes): comments and empty lines are skipped, a '#' starts
    a comment, the rest is trimmed. prepare_line is
    Language.prepareLineForSpeller (a function line -> list of lines)."""
    lines = []
    text = []
    for path in paths:
        with open(path, encoding='utf-8') as f:
            text.append(f.read())
    # Java reads the files as one stream (SequenceInputStream)
    for original_line in _LINE_BREAK.split(''.join(text)):
        for line in (prepare_line(original_line) if prepare_line is not None else [original_line]):
            if line.startswith('#') or not line:
                continue
            line = line.split('#')[0].strip()
            if line:
                lines.append(line.encode('utf-8'))
    return lines


class MorfologikMultiSpeller:
    """MorfologikMultiSpeller.isMisspelled: a word is accepted if one of the
    spellers (the binary dictionary and the plain text word lists, which use
    the metadata of the binary dictionary) accepts it. No user dictionaries
    (UserConfig) are supported."""

    def __init__(self, binary_dict, plain_text_paths=(), prepare_line=None):
        md = SpellerMetadata(binary_dict.metadata)
        self.spellers = [MorfologikSpeller(_FSAWords(binary_dict.fsa), md)]
        lines = read_plain_text_lines(plain_text_paths, prepare_line) if plain_text_paths else []
        if lines:
            self.spellers.append(MorfologikSpeller(_PlainWords(lines, md.separator), md))
        self._converts_case = md.convert_case

    def is_misspelled(self, word):
        for speller in self.spellers:
            if not speller.is_misspelled(word):
                return False
        return True

    def converts_case(self):
        return self._converts_case


_word_list_cache = {}
_multi_speller_cache = {}
_cache_lock = threading.Lock()


def _cached_words(path):
    """CachingWordListLoader.loadWords (missing files give no words)"""
    with _cache_lock:
        r = _word_list_cache.get(path)
        if r is None:
            r = _word_list_cache[path] = tuple(load_word_list(path)) if path else ()
        return r


class MorfologikMisspellingCheck:
    """The misspelling check of a MorfologikSpellerRule subclass: its
    isMisspelled(word) (MorfologikSpellerRule.isMisspelled with speller1,
    including the optional compound check), and the word lists of
    SpellingCheckRule: ignore_word(word) (SpellingCheckRule.ignoreWord with
    the words of the ignore file and the spelling files) and
    is_prohibited(word) (the prohibit files).

    Subclasses (or the constructor arguments) give the file names like the
    Java rule (paths relative to the resource directory): get_file_name()
    (the binary dictionary), get_spelling_file_name(),
    get_additional_spelling_file_names(), get_ignore_file_name(),
    get_prohibit_file_name() and get_additional_prohibit_file_names().
    Files are looked up in the resource directory of the language and then
    with the dictionary download mechanism (langtool.dictionaries) if the
    language's manifest lists them; files that are not found are skipped,
    like in Java."""

    check_compound = False
    compound_regex = regex.compile('-')

    def __init__(self, language):
        self.language = language
        self._lock = threading.Lock()
        self._speller1 = None
        self._ignored = None
        self._prohibited = None

    # --- file names (SpellingCheckRule defaults) ---

    def get_file_name(self):
        raise NotImplementedError()

    def get_spelling_file_name(self):
        return self.language.short_code + '/hunspell/spelling.txt'

    def get_additional_spelling_file_names(self):
        return [self.language.short_code + '/hunspell/spelling_custom.txt', 'spelling_global.txt']

    def get_language_variant_spelling_file_name(self):
        return None

    def get_ignore_file_name(self):
        return self.language.short_code + '/hunspell/ignore.txt'

    def get_prohibit_file_name(self):
        return self.language.short_code + '/hunspell/prohibit.txt'

    def get_additional_prohibit_file_names(self):
        return [self.language.short_code + '/hunspell/prohibit_custom.txt']

    def is_latin_script(self):
        return True

    def tokenize_new_words(self):
        return True

    def expand_line(self, line):
        return [line]

    def prepare_line_for_speller(self, line):
        """Language.prepareLineForSpeller"""
        return [line]

    # --- files ---

    def resource_file(self, name):
        """The path of a resource file (None if it doesn't exist)."""
        if name is None:
            return None
        name = name.lstrip('/')
        p = self.language.resource_path(name)
        if os.path.exists(p):
            return p
        from . import dictionaries
        lang = name.split('/', 1)[0]
        if name in dictionaries.required_files(lang):
            return dictionaries.locate(name, self.language.dictionary_path, self.language.download_dictionaries)
        return None

    def _init_spellers(self):
        with self._lock:
            if self._speller1 is not None:
                return self._speller1
            binary_dict = self.language.dictionary(self.get_file_name().lstrip('/'))
            plain_text = []
            for name in [self.get_spelling_file_name()] + list(self.get_additional_spelling_file_names()):
                p = self.resource_file(name)
                if p is not None:
                    plain_text.append(p)
            variant = self.resource_file(self.get_language_variant_spelling_file_name())
            if variant is not None:
                raise NotImplementedError('language variant spelling files are not supported yet')
            # (the dictionaries are cached statically in Java)
            key = (id(binary_dict), tuple(plain_text), type(self).prepare_line_for_speller)
            with _cache_lock:
                speller = _multi_speller_cache.get(key)
                if speller is None or speller[0] is not binary_dict:
                    speller = _multi_speller_cache[key] = (binary_dict, MorfologikMultiSpeller(
                        binary_dict, plain_text, self.prepare_line_for_speller))
            self._speller1 = speller[1]
            return self._speller1

    def _init_word_lists(self):
        with self._lock:
            if self._ignored is not None:
                return
            ignored = set()
            names = [self.get_ignore_file_name(), self.get_spelling_file_name()]
            names.extend(self.get_additional_spelling_file_names())
            tokenizer = self.language.word_tokenizer if self.tokenize_new_words() else None
            for name in names:
                for line in _cached_words(self.resource_file(name)):
                    # SpellingCheckRule.addIgnoreWords: lines of several tokens become anti-patterns
                    # (multi-word ignore entries), which never match a single word
                    if tokenizer is None or len(tokenizer.tokenize(line)) <= 1:
                        ignored.add(line)
            prohibited = set()
            for name in [self.get_prohibit_file_name()] + list(self.get_additional_prohibit_file_names()):
                for line in _cached_words(self.resource_file(name)):
                    prohibited.update(self.expand_line(line))
            self._prohibited = frozenset(prohibited)
            self._ignored = frozenset(ignored)

    # --- checks ---

    def converts_case(self):
        return self._init_spellers().converts_case()

    def is_misspelled(self, word):
        """MorfologikSpellerRule.isMisspelled(word)"""
        speller = self._init_spellers()
        if not speller.is_misspelled(word):
            return False
        if self.check_compound and self.compound_regex.search(word):
            for single_word in self.compound_regex.split(word):
                if speller.is_misspelled(single_word):
                    return True
            return False
        return True

    def is_prohibited(self, word):
        """SpellingCheckRule.isProhibited"""
        self._init_word_lists()
        return word in self._prohibited

    def is_in_ignored_set(self, word):
        self._init_word_lists()
        return word in self._ignored

    def is_ignored_no_case(self, word):
        return (self.is_in_ignored_set(word)
                or (not is_mixed_case(word) and self.converts_case()
                    and self.is_in_ignored_set(java_to_lower(word, self.language.short_code))))

    def ignore_word(self, word):
        """SpellingCheckRule.ignoreWord(String) (ignore words considered, no
        ignoreWordsWithLength)"""
        if len(word) > MAX_TOKEN_LENGTH:
            return True
        no_letter = _HAS_NO_LETTER_LATIN if self.is_latin_script() else _HAS_NO_LETTER
        if no_letter.fullmatch(word):
            return True
        if word.endswith('.') and not self.is_in_ignored_set(word):
            return self.is_ignored_no_case(word[:-1])  # e.g. word at end of sentence
        return self.is_ignored_no_case(word)
