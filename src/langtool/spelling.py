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
from .tools import (char_to_lower, char_to_upper, is_all_uppercase, is_digit, is_emoji, is_letter, is_lower_case,
                    is_mixed_case, is_upper_case, java_equals_ignore_case, java_split, starts_with_uppercase,
                    uppercase_first_char)

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
        self.runon_words = flag('runon-words')
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


def plain_text_speller_lines(plain_text_paths, prepare_line=None, language_variant_path=None):
    """The lines of the plain text speller of MorfologikMultiSpeller: the
    lines of the plain text word lists and (only with word lists) those of
    the word list of the language variant (getLanguageVariantSpellingFileName,
    e.g. en/hunspell/spelling_en-US.txt) plus "LanguageTool"."""
    if not plain_text_paths:
        return []
    lines = read_plain_text_lines(plain_text_paths, prepare_line)
    if language_variant_path is not None:
        lines.extend(read_plain_text_lines([language_variant_path], prepare_line))
        lines.append(LANGUAGETOOL.encode('utf-8'))  # adding here so it's also used for suggestions
    return lines


class MorfologikMultiSpeller:
    """MorfologikMultiSpeller.isMisspelled: a word is accepted if one of the
    spellers (the binary dictionary and the plain text word lists, which use
    the metadata of the binary dictionary) accepts it. No user dictionaries
    (UserConfig) are supported."""

    def __init__(self, binary_dict, plain_text_paths=(), prepare_line=None, language_variant_path=None):
        md = SpellerMetadata(binary_dict.metadata)
        self.spellers = [MorfologikSpeller(_FSAWords(binary_dict.fsa), md)]
        lines = plain_text_speller_lines(plain_text_paths, prepare_line, language_variant_path)
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
    # SpellingCheckRule.ignoreWordsWithLength: words up to this length are ignored (0: none)
    ignore_words_with_length = 0

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

    def get_additional_ignore_file_names(self):
        """Further word lists whose words are ignored (added with
        addIgnoreWords by the constructors of some Java rules)"""
        return []

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
            # (the dictionaries are cached statically in Java)
            key = (id(binary_dict), tuple(plain_text), variant, type(self).prepare_line_for_speller)
            with _cache_lock:
                speller = _multi_speller_cache.get(key)
                if speller is None or speller[0] is not binary_dict:
                    speller = _multi_speller_cache[key] = (binary_dict, MorfologikMultiSpeller(
                        binary_dict, plain_text, self.prepare_line_for_speller, variant))
            self._speller1 = speller[1]
            return self._speller1

    def _init_word_lists(self):
        with self._lock:
            if self._ignored is not None:
                return
            ignored = set()
            names = [self.get_ignore_file_name(), self.get_spelling_file_name()]
            names.extend(self.get_additional_spelling_file_names())
            names.extend(self.get_additional_ignore_file_names())
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
                    and self.is_in_ignored_set(java_to_lower(word, self.language.short_code)))
                or (self.ignore_words_with_length > 0 and len(word) <= self.ignore_words_with_length))

    def ignore_word(self, word):
        """SpellingCheckRule.ignoreWord(String) (ignore words considered)"""
        if len(word) > MAX_TOKEN_LENGTH:
            return True
        no_letter = _HAS_NO_LETTER_LATIN if self.is_latin_script() else _HAS_NO_LETTER
        if no_letter.fullmatch(word):
            return True
        if word.endswith('.') and not self.is_in_ignored_set(word):
            return self.is_ignored_no_case(word[:-1])  # e.g. word at end of sentence
        return self.is_ignored_no_case(word)

    def ignore_potentially_misspelled_word(self, word):
        """SpellingCheckRule.ignorePotentiallyMisspelledWord"""
        return False

    def tokenizing_pattern(self):
        """MorfologikSpellerRule.tokenizingPattern (None: words are not
        split)"""
        return None

    def sentence_has_match(self, sentence, ignore_tagged_words=False):
        """Whether MorfologikSpellerRule.match(sentence) would find a
        spelling error (spellerRule.match(sentence).length > 0): a token
        that cannot be ignored (canBeIgnored: sentence start, immunized,
        ignored by the speller, URL, e-mail, tagged if ignore_tagged_words
        (setIgnoreTaggedWords) and not prohibited, ignoreWord) that is
        misspelled or prohibited (and not
        ignorePotentiallyMisspelledWord). The anti-patterns of multi-word
        ignore entries (rules with tokenizeNewWords()) are not applied."""
        from .tokenizers import is_email, is_url
        for token in sentence.get_tokens_without_whitespace():
            t = token.token
            if (token.is_sentence_start or token.immunized or token.ignored_by_speller or is_url(t) or is_email(t)
                    or (ignore_tagged_words and token.is_tagged() and not self.is_prohibited(t))
                    or self.ignore_word(t)):
                continue
            # if we use token.getToken() we'll get ignored characters inside and speller will choke
            word = token.readings[0].token
            pattern = self.tokenizing_pattern()
            if pattern is None:
                parts = [word]
            else:
                parts = []
                index = 0
                for m in pattern.finditer(word):
                    parts.append(word[index:m.start()])
                    index = m.end()
                parts.append(word[index:])
            for part in parts:
                if ((self.is_misspelled(part) or self.is_prohibited(part))
                        and not self.ignore_potentially_misspelled_word(part)):
                    return True
        return False


# --- spelling suggestions: morfologik's Speller.findReplacements/findSimilarWords ---

_EXACT_MATCH, _SEQUENCE_IS_A_PREFIX, _AUTOMATON_HAS_PREFIX, _NO_MATCH = 0, 1, 2, 3


def _fsa_match(fsa, wb):
    """FSATraversal.match(sequence, rootNode): returns (kind, node)"""
    node = fsa.root
    if node == 0:
        return _NO_MATCH, node
    end = len(wb)
    for i in range(end):
        arc = fsa.get_arc(node, wb[i])
        if arc != 0:
            if i + 1 == end and fsa.is_final(arc):
                return _EXACT_MATCH, node
            dest = fsa.destination(arc)
            if dest == 0:  # terminal arc
                return _AUTOMATON_HAS_PREFIX, node
            node = dest
        else:
            return (_AUTOMATON_HAS_PREFIX if i > 0 else _NO_MATCH), node
    return _SEQUENCE_IS_A_PREFIX, node


def parse_replacement_pairs(value):
    """DictionaryAttribute.REPLACEMENT_PAIRS.fromString (a LinkedHashMap:
    key -> list of values, '_' stands for a space)"""
    pairs = {}
    if value is None:
        return pairs
    for string_pair in regex.split(r',\s*', value):
        two = string_pair.strip().split(' ')
        if len(two) != 2:
            raise ValueError('Attribute fsa.dict.speller.replacement-pairs is not in the proper format: ' + value)
        key = two[0].replace('_', ' ')
        val = two[1].replace('_', ' ')
        pairs.setdefault(key, []).append(val)
    return pairs


def parse_equivalent_chars(value):
    """DictionaryAttribute.EQUIVALENT_CHARS.fromString (char -> list of chars)"""
    chars = {}
    if value is None:
        return chars
    for char_pair in regex.split(r',\s*', value):
        two = char_pair.strip().split(' ')
        if len(two) == 2 and len(two[0]) == 1 and len(two[1]) == 1:
            chars.setdefault(two[0], []).append(two[1])
        else:
            raise ValueError('Attribute fsa.dict.speller.equivalent-chars is not in the proper format: ' + value)
    return chars


class HMatrix:
    """Port of morfologik.speller.HMatrix: the band of the edit distance
    matrix around the diagonal (see Oflazer), stored as a vector."""

    __slots__ = ('p', 'row_length', 'column_height', 'edit_distance')

    def __init__(self, distance, max_length):
        self.row_length = max_length + 2
        self.column_height = 2 * distance + 3
        self.edit_distance = distance
        self.p = [0] * (self.row_length * self.column_height)
        self._init()

    def _init(self):
        p = self.p
        size = len(p)
        ed = self.edit_distance
        rl = self.row_length
        # Initialize edges of the diagonal band to distance + 1 (i.e. distance too big)
        for i in range(rl - ed - 1):
            p[i] = ed + 1  # H(distance + j, j) = distance + 1
            p[size - i - 1] = ed + 1  # H(i, distance + i) = distance + 1
        # Initialize items H(i,j) with at least one index equal to zero to |i - j|
        for j in range(ed + 2):
            p[j * rl] = ed + 1 - j  # H(i=0..distance+1,0)=i
            p[(j + ed + 1) * rl + j] = j  # H(0,j=0..distance+1)=j

    def reset(self):
        self.p = [0] * len(self.p)
        self._init()

    def get(self, i, j):
        return self.p[(j - i + self.edit_distance + 1) * self.row_length + j]

    def set(self, i, j, val):
        self.p[(j - i + self.edit_distance + 1) * self.row_length + j] = val


class CandidateData:
    """Speller.CandidateData: a suggestion with its edit distance (distance
    is the sort key combining the edit distance and the word frequency)."""

    __slots__ = ('word', 'orig_distance', 'distance')

    def __init__(self, word, orig_distance, distance):
        self.word = word
        self.orig_distance = orig_distance
        self.distance = distance

    def __repr__(self):
        return '%s/%d' % (self.word, self.distance)


class _ReplacementPattern:
    __slots__ = ('chars', 'start_anchor', 'end_anchor')

    def __init__(self, chars, start_anchor, end_anchor):
        self.chars = chars
        self.start_anchor = start_anchor
        self.end_anchor = end_anchor


def _strip_anchors(key):
    start = 1 if key.startswith('^') else 0
    end = len(key) - 1 if key.endswith('$') else len(key)
    return key[start:end]


def _java_index_of(s, sub, from_index):
    """String(Builder).indexOf(str, fromIndex): a negative fromIndex is 0"""
    return s.find(sub, max(0, from_index))


def _is_utf8(encoding):
    import codecs
    try:
        return codecs.lookup(encoding).name == 'utf-8'
    except LookupError:
        return False


def _single_byte_table(encoding):
    """byte -> code point for single byte encodings in which every byte
    decodes to one character (None otherwise)"""
    if _is_utf8(encoding):
        return None
    table = []
    try:
        for b in range(256):
            d = bytes((b,)).decode(encoding)
            if len(d) != 1:
                return None
            table.append(ord(d))
    except (UnicodeDecodeError, LookupError):
        return None
    return table


def _native_fsa(fsa, dictionary):
    """The FSA for the C search: an FSADict for the binary FSAs, the arrays
    of a _TrieFSA"""
    from ._base import speedups
    from . import fsa as fsa_module
    if isinstance(fsa, _TrieFSA):
        return fsa.c_arrays()
    if isinstance(fsa, (fsa_module._FSA5, fsa_module._CFSA, fsa_module._CFSA2)):
        kind = 5 if isinstance(fsa, fsa_module._FSA5) else (0xc5 if isinstance(fsa, fsa_module._CFSA) else 0xc6)
        native = getattr(dictionary, '_native', None)
        if native is not None and isinstance(native, speedups.FSADict):
            return native
        return speedups.FSADict(bytes(fsa.arcs), kind, fsa.root, getattr(fsa, 'gtl', 0),
                                getattr(fsa, 'node_data_length', 0), bytes(getattr(fsa, 'label_mapping', b'')),
                                bool(getattr(fsa, 'has_numbers', False)), 0, 0, 'NONE')
    return None


class Speller:
    """Port of the suggestion search of morfologik.speller.Speller (version
    2.2.0, as used by LanguageTool): K. Oflazer's error-tolerant recognition
    on the dictionary's FSA with the replacement pairs, equivalent
    characters and diacritics/case settings of the dictionary's .info file,
    candidates sorted by edit distance and frequency. dictionary is a
    langtool.fsa.Dictionary (a speller or tagger dictionary).

    Like for the misspelling check (MorfologikSpeller above), morfologik's
    containsSeparators field is assumed to stay true (which it does for
    dictionaries whose entries all contain the separator). Words are
    processed as Python strings (UTF-16 code units in Java, the same for
    the BMP). Not thread safe (like in Java; see MorfologikSuggestionSpeller)."""

    MAX_WORD_LENGTH = 120
    FREQ_RANGES = ord('Z') - ord('A') + 1
    FIRST_RANGE_CODE = ord('A')
    UPPER_SEARCH_LIMIT = 15
    MIN_WORD_LENGTH = 4
    MAX_RECURSION_LEVEL = 6

    def __init__(self, dictionary, edit_distance=1):
        self.dictionary = dictionary
        self.fsa = dictionary.fsa
        self.edit_distance = edit_distance
        self.h_matrix = HMatrix(edit_distance, self.MAX_WORD_LENGTH)
        md = dictionary.metadata
        self.md = SpellerMetadata(md)
        props = md.props
        if self.fsa.root == 0:
            raise ValueError('Dictionary must have at least the root node.')
        self.encoding = md.encoding
        self.separator = md.separator
        self.separator_char = md.separator_char
        self.frequency_included = md.frequency_included
        self.input_conversion = md.input_conversion
        self.output_conversion = md.output_conversion
        rp = props.get('fsa.dict.speller.replacement-pairs')
        self.replacement_pairs = parse_replacement_pairs(rp.strip() if rp is not None else None)
        ec = props.get('fsa.dict.speller.equivalent-chars')
        self.equivalent_chars = parse_equivalent_chars(ec.strip() if ec is not None else None)
        idv = props.get('fsa.dict.speller.ignore-diacritics')
        self.ignore_diacritics = True if idv is None else _boolean_value(idv.strip())
        self.convert_case = self.md.convert_case
        self.locale = self.md.locale
        self._words = _FSAWords(self.fsa)
        self._create_replacements_maps()
        self.word_processed = ''
        self.word_len = 0
        self.candidate = None
        self.effect_edit_distance = 0
        self._equal_cache = {}
        try:
            # (the bytes 0-127 are ASCII characters in the encoding)
            self._ascii_compatible = bytes(range(128)).decode(self.encoding) == ''.join(map(chr, range(128)))
        except (UnicodeDecodeError, LookupError):
            self._ascii_compatible = False

    def _create_replacements_maps(self):
        self.replacements_any_to_one = {}
        self.replacements_any_to_two = {}
        rest = {}
        for raw_key, values in self.replacement_pairs.items():
            start_anchor = raw_key.startswith('^')
            end_anchor = raw_key.endswith('$')
            stripped = _strip_anchors(raw_key)
            for s in values:
                if len(s) == 1:
                    self.replacements_any_to_one.setdefault(s, []).append(
                        _ReplacementPattern(stripped, start_anchor, end_anchor))
                elif len(s) == 2:
                    self.replacements_any_to_two.setdefault(s, []).append(
                        _ReplacementPattern(stripped, start_anchor, end_anchor))
                else:
                    rest.setdefault(raw_key, []).append(s)
        # (a java.util.HashMap: its iteration order matters in getAllReplacements())
        from .rules.abstract_rules import java_hash_set_order
        self.replacements_the_rest = {k: rest[k] for k in java_hash_set_order(list(rest))}

    # --- dictionary lookups ---

    def _encode(self, word):
        try:
            return word.encode(self.encoding)
        except UnicodeEncodeError:
            return None

    def is_in_dictionary(self, word):
        wb = self._encode(word)
        if wb is None:
            return False
        return self._words.contains(wb, self.separator_char in word, self.separator)

    def get_frequency(self, word):
        """The frequency value (0..FREQ_RANGES-1) of the first entry of the
        word form."""
        if not self.frequency_included:
            return 0
        wb = self._encode(word)
        if wb is None:
            return 0
        fsa = self.fsa
        kind, node = _fsa_match(fsa, wb)
        if kind == _SEQUENCE_IS_A_PREFIX:
            arc = fsa.get_arc(node, self.separator)
            if arc != 0 and not fsa.is_final(arc):
                for seq in self.dictionary._sequences(fsa.destination(arc)):
                    b = seq[-1]
                    if b > 127:
                        b -= 256  # Java bytes are signed
                    return b - self.FIRST_RANGE_CODE
        return 0

    def _candidate_data(self, word, distance):
        return CandidateData(word, distance,
                             distance * self.FREQ_RANGES + self.FREQ_RANGES - self.get_frequency(word) - 1)

    # --- suggestions ---

    def find_similar_word_candidates(self, word):
        """Find similar words even if the original word is a correct word
        that exists in the dictionary."""
        return self._find_replacement_candidates(word, True)

    def find_similar_words(self, word):
        return [cd.word for cd in self.find_similar_word_candidates(word)]

    def find_replacement_candidates(self, word):
        return self._find_replacement_candidates(word, False)

    def find_replacements(self, word):
        return [cd.word for cd in self.find_replacement_candidates(word)]

    def replace_run_on_word_candidates(self, original):
        """Speller.replaceRunOnWordCandidates: propose suggestions for
        misspelled run-on words (inspired by spell.cc in s_fsa package by
        Jan Daciuk), as space-separated pairs of dictionary words."""
        candidates = []
        word_to_check = original
        if self.input_conversion:
            word_to_check = _apply_replacements(original, self.input_conversion)
        if not self.is_in_dictionary(word_to_check) and self.md.runon_words:
            locale = self.locale
            for i in range(1, len(word_to_check)):
                # chop from left to right
                prefix = word_to_check[:i]
                suffix = word_to_check[i:]
                if (self.is_in_dictionary(suffix)
                        # camel case words: e.g. GreatElephant
                        or (not _is_not_capitalized_word(suffix)
                            and self.is_in_dictionary(java_to_lower(suffix, locale)))):
                    if self.is_in_dictionary(prefix):
                        self._add_run_on_replacement(candidates, prefix + ' ' + suffix)
                    elif is_upper_case(prefix[0]) and self.is_in_dictionary(java_to_lower(prefix, locale)):
                        # a word that's uppercase just because used at sentence start
                        self._add_run_on_replacement(candidates, prefix + ' ' + suffix)
        return candidates

    def _add_run_on_replacement(self, candidates, replacement):
        if self.output_conversion:
            replacement = _apply_replacements(replacement, self.output_conversion)
        candidates.append(self._candidate_data(replacement, 1))

    def _find_replacement_candidates(self, word, even_if_word_in_dictionary):
        self.h_matrix.reset()
        if self.input_conversion:
            word = _apply_replacements(word, self.input_conversion)
        candidates = []
        if 0 < len(word) < self.MAX_WORD_LENGTH and (not self.is_in_dictionary(word) or even_if_word_in_dictionary):
            words_to_check = []
            if len(word) > 1:
                for word_checked in self.get_all_replacements(word, 0, 0):
                    if self.is_in_dictionary(word_checked):
                        candidates.append(self._candidate_data(word_checked, 0))
                    else:
                        lower_word = java_to_lower(word_checked, self.locale)
                        upper_word = word_checked.upper()
                        if self.is_in_dictionary(lower_word):
                            # add the word as it is in the dictionary, not mixed-case versions of it
                            candidates.append(self._candidate_data(lower_word, 0))
                        if self.is_in_dictionary(upper_word):
                            candidates.append(self._candidate_data(upper_word, 0))
                        if len(lower_word) > 1:
                            first_upper_word = char_to_upper(lower_word[0]) + lower_word[1:]
                            if self.is_in_dictionary(first_upper_word):
                                candidates.append(self._candidate_data(first_upper_word, 0))
                    words_to_check.append(word_checked)
            else:
                words_to_check.append(word)
            # Even if a candidate was found with the replacement pairs (which are usual errors),
            # there might be more good candidates (see issue #94):
            i = 1
            for word_checked in words_to_check:
                i += 1
                if i > self.UPPER_SEARCH_LIMIT:  # for performance reasons, do not search too deeply
                    break
                self.word_processed = word_checked
                self.word_len = len(word_checked)
                if self.word_len < self.MIN_WORD_LENGTH and i > 2:
                    # three-letter replacements make little sense anyway
                    break
                self.candidate = ['\0'] * self.MAX_WORD_LENGTH
                self.effect_edit_distance = (self.word_len - 1 if self.word_len <= self.edit_distance
                                             else self.edit_distance)
                native = self._native_search()
                if native is not None:
                    h = self.h_matrix
                    for w, dist in native[0].search(native[1], self.fsa.root, word_checked, h.p, h.edit_distance,
                                                    h.row_length, self.effect_edit_distance, self.MAX_WORD_LENGTH):
                        candidates.append(self._candidate_data(w, dist))
                else:
                    self._find_repl(candidates, 0, self.fsa.root, b'', 0, 0, -1, None, '\0')
        candidates.sort(key=lambda cd: cd.distance)  # stable, like Collections.sort
        # Apply replacements, prune duplicates while preserving the candidate order.
        words = set()
        result = []
        for cd in candidates:
            replaced = _apply_replacements(cd.word, self.output_conversion) if self.output_conversion else cd.word
            # Add only the first occurrence of a given word.
            if replaced not in words:
                words.add(replaced)
                if replaced != word:
                    result.append(self._candidate_data(replaced, cd.orig_distance))
        return result

    def _native_search(self):
        """(SpellerSearch, FSA argument) of the C implementation of the
        search (_find_repl), None without the C extension or for FSAs and
        encodings it doesn't support"""
        r = self.__dict__.get('_native_search_cache', False)
        if r is not False:
            return r
        r = None
        from ._base import speedups
        if speedups is not None and hasattr(speedups, 'SpellerSearch'):
            fsa_arg = _native_fsa(self.fsa, self.dictionary)
            table = _single_byte_table(self.encoding)
            utf8 = _is_utf8(self.encoding)
            if fsa_arg is not None and (utf8 or table is not None):
                m1 = [(k, [(p.chars, p.start_anchor, p.end_anchor) for p in v])
                      for k, v in self.replacements_any_to_one.items()]
                m2 = [(k, [(p.chars, p.start_anchor, p.end_anchor) for p in v])
                      for k, v in self.replacements_any_to_two.items()]
                if all(len(k) == 1 for k, _ in m1) and all(len(k) == 2 for k, _ in m2) and \
                        len(self.separator_char) == 1:
                    search = speedups.SpellerSearch(self._are_equal, m1, m2, utf8, table or [-1] * 256,
                                                    self.separator_char, self.separator)
                    r = (search, fsa_arg)
        self._native_search_cache = r
        return r

    def _find_repl(self, candidates, depth, node, prev_bytes, word_index, cand_index, min_lookback_word_index,
                   last_any_to_one_source, last_any_to_one_target):
        fsa = self.fsa
        candidate = self.candidate
        h_matrix = self.h_matrix
        effect_ed = self.effect_edit_distance
        word_len = self.word_len
        arc = fsa.first_arc(node)
        ascii_compatible = self._ascii_compatible
        while arc != 0:
            label = fsa.label(arc)
            if ascii_compatible and label < 0x80 and not prev_bytes:
                buf = b''
                decoded = chr(label)
            else:
                buf = prev_bytes + bytes((label,))
                try:
                    decoded = buf.decode(self.encoding)
                except UnicodeDecodeError:
                    decoded = None
            if decoded is None or not decoded:
                # incomplete multi-byte sequence: accumulate bytes and descend
                dest = fsa.destination(arc)
                if dest != 0:
                    self._find_repl(candidates, depth, dest, buf, word_index, cand_index, min_lookback_word_index,
                                    last_any_to_one_source, last_any_to_one_target)  # note: depth is not incremented
            else:
                c = decoded[0]
                if ord(c) > 0xffff:  # the first UTF-16 code unit
                    c = chr(0xd800 + ((ord(c) - 0x10000) >> 10))
                candidate[cand_index] = c
                # replacement "any to two"
                length_replacement = self._match_any_to_two(word_index, cand_index, min_lookback_word_index,
                                                            last_any_to_one_source, last_any_to_one_target)
                if length_replacement > 0:
                    # the replacement takes place at the end of the candidate
                    if self._is_end_of_candidate(arc, word_index):
                        dist = h_matrix.get(depth - 1, depth - 1)
                        if dist <= effect_ed:
                            extra = abs(word_len - 1 - (word_index + length_replacement - 2))
                            if extra > 0:
                                # there are extra letters in the word after the replacement
                                dist += extra
                            if dist <= effect_ed:
                                candidates.append(self._candidate_data(''.join(candidate[:cand_index + 1]), dist))
                    if self._is_arc_not_terminal(arc, cand_index):
                        x = h_matrix.get(depth, depth)
                        h_matrix.set(depth, depth, h_matrix.get(depth - 1, depth - 1))
                        self._find_repl(candidates, max(0, depth), fsa.destination(arc), b'',
                                        word_index + length_replacement - 1, cand_index + 1, min_lookback_word_index,
                                        last_any_to_one_source, last_any_to_one_target)
                        h_matrix.set(depth, depth, x)
                # replacement "any to one"
                length_replacement = self._match_any_to_one(word_index, cand_index)
                if length_replacement > 0:
                    # the replacement takes place at the end of the candidate
                    if self._is_end_of_candidate(arc, word_index):
                        dist = h_matrix.get(depth, depth)
                        if dist <= effect_ed:
                            extra = abs(word_len - 1 - (word_index + length_replacement - 1))
                            if extra > 0:
                                # there are extra letters in the word after the replacement
                                dist += extra
                            if dist <= effect_ed:
                                candidates.append(self._candidate_data(''.join(candidate[:cand_index + 1]), dist))
                    if self._is_arc_not_terminal(arc, cand_index):
                        new_any_to_one_source = self.word_processed[word_index:word_index + length_replacement]
                        self._find_repl(candidates, depth, fsa.destination(arc), b'', word_index + length_replacement,
                                        cand_index + 1, word_index + length_replacement, new_any_to_one_source,
                                        candidate[cand_index])
                # general
                if self.cuted(depth, word_index, cand_index) <= effect_ed:
                    if self._is_end_of_candidate(arc, word_index):
                        dist = self.ed(word_len - 1 - (word_index - depth), depth, word_len - 1, cand_index)
                        if dist <= effect_ed:
                            candidates.append(self._candidate_data(''.join(candidate[:cand_index + 1]), dist))
                    if self._is_arc_not_terminal(arc, cand_index):
                        self._find_repl(candidates, depth + 1, fsa.destination(arc), b'', word_index + 1,
                                        cand_index + 1, min_lookback_word_index, last_any_to_one_source,
                                        last_any_to_one_target)
            arc = fsa.next_arc(arc)

    def _is_arc_not_terminal(self, arc, cand_index):
        # (containsSeparators is true)
        return self.fsa.destination(arc) != 0 and self.candidate[cand_index] != self.separator_char

    def _is_end_of_candidate(self, arc, word_index):
        return ((self.fsa.is_final(arc) or self._is_before_separator(arc))
                # candidate has proper length
                and abs(self.word_len - 1 - word_index) <= self.effect_edit_distance)

    def _is_before_separator(self, arc):
        fsa = self.fsa
        arc1 = fsa.get_arc(fsa.destination(arc), self.separator)
        return arc1 != 0 and fsa.destination(arc1) != 0

    def ed(self, i, j, word_index, cand_index):
        """Calculates the edit distance (see Oflazer). i: length of the
        misspelled word - 1, j: length of the candidate - 1."""
        h = self.h_matrix
        p = h.p
        rl = h.row_length
        # index of H(i, j) in the vector of the HMatrix: (j - i + editDistance + 1) * rowLength + j
        base = (j - i + h.edit_distance + 1) * rl + j
        wp = self.word_processed
        cand = self.candidate
        x = wp[word_index]
        y = cand[cand_index]
        if x == y or self._are_equal(x, y):
            # last characters are the same
            result = p[base]
        elif word_index > 0 and cand_index > 0 and x == cand[cand_index - 1] and wp[word_index - 1] == y:
            # last two characters are transposed
            a = p[base - 1]  # H(i - 1, j - 1): transposition, e.g. ababab, ababba
            b = p[base - rl]  # H(i + 1, j): deletion, e.g. abab, aba
            c = p[base + rl + 1]  # H(i, j + 1): insertion e.g. aba, abab
            result = 1 + (a if a <= b and a <= c else (b if b <= c else c))
        else:
            a = p[base]  # H(i, j): replacement, e.g. ababa, ababb
            b = p[base - rl]  # H(i + 1, j): deletion, e.g. ab, a
            c = p[base + rl + 1]  # H(i, j + 1): insertion e.g. a, ab
            result = 1 + (a if a <= b and a <= c else (b if b <= c else c))
        p[base + 1] = result  # H(i + 1, j + 1)
        return result

    def _are_equal(self, x, y):
        """areEqual (memoized: the result only depends on the characters
        and the settings of the dictionary)"""
        cache = self._equal_cache
        key = (x, y)
        r = cache.get(key)
        if r is None:
            r = cache[key] = self._are_equal_uncached(x, y)
        return r

    def _are_equal_uncached(self, x, y):
        if x == y:
            return True
        chars = self.equivalent_chars.get(x)
        if chars is not None and y in chars:
            return True
        if self.ignore_diacritics:
            xn = unicodedata.normalize('NFD', x)[0]
            yn = unicodedata.normalize('NFD', y)[0]
            if xn == yn:  # avoid case conversion, if possible
                return True
            if self.convert_case:
                # again case conversion only when needed
                if is_letter(xn):
                    if is_lower_case(xn) != is_lower_case(yn):
                        return char_to_lower(xn) == char_to_lower(yn)
            return xn == yn
        return False

    def cuted(self, depth, word_index, cand_index):
        """Calculates the cut-off edit distance (see Oflazer). (ed() is
        inlined)"""
        effect_ed = self.effect_edit_distance
        lo = max(0, depth - effect_ed)  # min chars from word to consider - 1
        up = min(self.word_len - 1 - (word_index - depth), depth + effect_ed)  # max chars from word to consider - 1
        min_ed = effect_ed + 1  # what is to be computed
        wi = word_index + lo - depth
        h = self.h_matrix
        p = h.p
        rl = h.row_length
        e1 = h.edit_distance + 1
        wp = self.word_processed
        cand = self.candidate
        y = cand[cand_index]
        y_prev = cand[cand_index - 1] if cand_index > 0 else None
        cache = self._equal_cache
        j = depth
        for i in range(lo, up + 1):
            # ed(i, depth, wi, cand_index)
            base = (j - i + e1) * rl + j
            x = wp[wi]
            if x == y:
                eq = True
            else:
                eq = cache.get((x, y))
                if eq is None:
                    eq = self._are_equal(x, y)
            if eq:
                d = p[base]
            elif wi > 0 and cand_index > 0 and x == y_prev and wp[wi - 1] == y:
                a = p[base - 1]
                b = p[base - rl]
                c = p[base + rl + 1]
                d = 1 + (a if a <= b and a <= c else (b if b <= c else c))
            else:
                a = p[base]
                b = p[base - rl]
                c = p[base + rl + 1]
                d = 1 + (a if a <= b and a <= c else (b if b <= c else c))
            p[base + 1] = d
            if d < min_ed:
                min_ed = d
            wi += 1
        return min_ed

    def _match_any_to_one(self, word_index, cand_index):
        """Match the last letter of the candidate against two or more letters
        of the word."""
        patterns = self.replacements_any_to_one.get(self.candidate[cand_index])
        if patterns:
            wp = self.word_processed
            word_len = self.word_len
            for p in patterns:
                if p.start_anchor and word_index != 0:
                    continue
                chars = p.chars
                i = 0
                while i < len(chars) and word_index + i < word_len and chars[i] == wp[word_index + i]:
                    i += 1
                if i == len(chars):
                    if p.end_anchor and word_index + i != word_len:
                        continue
                    return i
        return 0

    def _match_any_to_two(self, word_index, cand_index, min_lookback_word_index, last_any_to_one_source,
                          last_any_to_one_target):
        cand = self.candidate
        if 0 < cand_index < len(cand) and word_index > 0:
            s_two_char = cand[cand_index - 1] + cand[cand_index]
            patterns = self.replacements_any_to_two.get(s_two_char)
            if patterns:
                wp = self.word_processed
                word_len = self.word_len
                for p in patterns:
                    if p.start_anchor and word_index - 1 != 0:
                        continue
                    chars = p.chars
                    if (len(chars) == 2 and word_index < word_len and cand[cand_index - 1] == wp[word_index - 1]
                            and cand[cand_index] == wp[word_index]):
                        return 0  # unnecessary replacements
                    i = 0
                    while i < len(chars) and word_index - 1 + i < word_len and chars[i] == wp[word_index - 1 + i]:
                        i += 1
                    if i == len(chars):
                        if p.end_anchor and word_index - 1 + i != word_len:
                            continue
                        # Reject if this match directly reverses a previous anyToOne match at an
                        # overlapping position
                        if (word_index - 1 < min_lookback_word_index and last_any_to_one_source is not None
                                and len(chars) == 1 and chars[0] == last_any_to_one_target
                                and s_two_char == last_any_to_one_source):
                            continue
                        return i
        return 0

    def get_all_replacements(self, s, from_index, level):
        """All possible replacements of s (with the replacement pairs whose
        target has more than two characters)."""
        replaced = []
        if level > self.MAX_RECURSION_LEVEL:  # Stop searching at some point
            replaced.append(s)
            return replaced
        index = self.MAX_WORD_LENGTH
        key = ''
        key_length = 0
        found = False
        # find first possible replacement after fromIndex position
        stripped_key_for_selected = ''
        for aux_key in self.replacements_the_rest:
            start_anchor = aux_key.startswith('^')
            end_anchor = aux_key.endswith('$')
            stripped = _strip_anchors(aux_key) if (start_anchor or end_anchor) else aux_key
            if start_anchor and from_index > 0:
                continue  # ^ anchor only valid from the beginning
            elif start_anchor:
                aux_index = 0 if s.startswith(stripped) else -1
            elif end_anchor:
                expected_index = len(s) - len(stripped)
                aux_index = (expected_index if expected_index >= from_index
                             and _java_index_of(s, stripped, expected_index) == expected_index else -1)
            else:
                aux_index = _java_index_of(s, aux_key, from_index)
            if aux_index > -1 and (aux_index < index or (aux_index == index and not len(stripped) < key_length)):
                # select the longest possible key
                index = aux_index
                key = aux_key
                key_length = len(stripped)
                stripped_key_for_selected = stripped
        if index < self.MAX_WORD_LENGTH:
            for rep in self.replacements_the_rest[key]:
                # start a branch without replacement (only once per key)
                if not found:
                    replaced.extend(self.get_all_replacements(s, index + len(stripped_key_for_selected), level + 1))
                    found = True
                # avoid unnecessary replacements (ex. don't replace L by L·L when L·L already present)
                ind = _java_index_of(s, rep, from_index - len(rep) + 1)
                if (len(rep) > len(stripped_key_for_selected) and ind > -1
                        and (ind == index or ind == index - len(rep) + 1)):
                    continue
                # start a branch with replacement
                sb = s[:index] + rep + s[index + len(stripped_key_for_selected):]
                replaced.extend(self.get_all_replacements(sb, index + len(rep), level + 1))
        if not found:
            replaced.append(s)
        return replaced


class MorfologikSuggestionSpeller:
    """The suggestion part of LanguageTool's
    org.languagetool.rules.spelling.morfologik.MorfologikSpeller: a
    morfologik Speller for a dictionary with a maximum edit distance
    (default 1), with synchronized findReplacements/findSimilarWords. Use
    morfologik_suggestion_speller() to share instances (LT caches the
    dictionaries)."""

    def __init__(self, dictionary, max_edit_distance=1):
        if max_edit_distance <= 0:
            raise ValueError('maxEditDistance must be > 0: %d' % max_edit_distance)
        self.dictionary = dictionary
        self.max_edit_distance = max_edit_distance
        self.speller = Speller(dictionary, max_edit_distance)
        self._lock = threading.Lock()

    def find_replacements(self, word):
        with self._lock:
            return self.speller.find_replacements(word)

    def find_similar_words(self, word):
        with self._lock:
            return self.speller.find_similar_words(word)

    def converts_case(self):
        return self.speller.convert_case


_suggestion_spellers = {}


def morfologik_suggestion_speller(language, file_name, max_edit_distance=1):
    """new MorfologikSpeller(fileInClassPath, maxEditDistance) for a
    dictionary of the language (file_name relative to the resource
    directory, like '/es/es-ES.dict'), shared per dictionary."""
    dictionary = language.dictionary(file_name.lstrip('/'))
    key = (id(dictionary), max_edit_distance)
    with _cache_lock:
        r = _suggestion_spellers.get(key)
        if r is None or r.dictionary is not dictionary:
            r = _suggestion_spellers[key] = MorfologikSuggestionSpeller(dictionary, max_edit_distance)
        return r


# --- spelling suggestions of MorfologikSpellerRule (getSpellingSuggestions) ---

class _TrieFSA:
    """An FSA (with the interface of langtool.fsa's automata) for a list of
    byte sequences, like the one morfologik's FSABuilder builds from the
    sorted lines of the plain text word lists (not minimized, which doesn't
    change the accepted sequences or the order of the arcs: by unsigned
    byte label). Nodes and arcs are positive integers, 0 is the terminal
    node (no outgoing arcs) and the missing arc."""

    def __init__(self, sequences):
        """sequences: sorted (unsigned byte order), without duplicates. The
        trie is built in one pass over the sorted sequences (the nodes on
        the path of the previous sequence are kept on a stack); a node gets
        its number (and its arcs their numbers) when all its children are
        known."""
        labels = [0]
        dests = [0]
        finals = [False]
        lasts = [False]
        first = [0]  # node -> first arc; nodes without arcs are 0
        arc_maps = [None]  # node -> {label: arc}

        def finish(arcs):
            if not arcs:
                return 0
            nid = len(first)
            first.append(len(labels))
            m = {}
            last = len(arcs) - 1
            for k, (label, child) in enumerate(arcs):
                m[label] = len(labels)
                labels.append(label)
                dests.append(child[0])
                finals.append(child[1])
                lasts.append(k == last)
            arc_maps.append(m)
            return nid

        # a stack entry: [arcs (a list of [label, (child node, child is final)]), final]
        stack = [[[], False]]
        prev = b''
        for seq in sequences:
            n = min(len(prev), len(seq))
            k = 0
            while k < n and prev[k] == seq[k]:
                k += 1
            while len(stack) > k + 1:
                node = stack.pop()
                stack[-1][0][-1][1] = (finish(node[0]), node[1])
            for b in seq[k:]:
                stack[-1][0].append([b, None])
                stack.append([[], False])
            stack[-1][1] = True
            prev = seq
        while len(stack) > 1:
            node = stack.pop()
            stack[-1][0][-1][1] = (finish(node[0]), node[1])
        self.root = finish(stack[0][0])
        self._first = first
        self._labels = labels
        self._dests = dests
        self._finals = finals
        self._lasts = lasts
        self._arc_maps = arc_maps

    def c_arrays(self):
        """The arrays of the trie for the C search (first arc, labels,
        destinations, final and last flags)"""
        r = getattr(self, '_c_arrays', None)
        if r is None:
            from array import array
            r = self._c_arrays = (array('i', self._first).tobytes(), bytes(self._labels),
                                  array('i', self._dests).tobytes(), bytes(self._finals), bytes(self._lasts))
        return r

    def first_arc(self, node):
        return self._first[node]

    def next_arc(self, arc):
        return 0 if self._lasts[arc] else arc + 1

    def label(self, arc):
        return self._labels[arc]

    def is_final(self, arc):
        return self._finals[arc]

    def destination(self, arc):
        return self._dests[arc]

    def get_arc(self, node, lbl):
        m = self._arc_maps[node]
        return m.get(lbl, 0) if m is not None else 0


class PlainTextDictionary:
    """The morfologik Dictionary that MorfologikMultiSpeller builds from the
    lines of the plain text word lists (spelling.txt etc.), with the
    metadata of the binary speller dictionary (its .info file)."""

    def __init__(self, lines, metadata):
        self.fsa = _TrieFSA(sorted(set(lines)))
        self.metadata = metadata

    def _sequences(self, node):
        """All byte sequences accepted from node, in arc order"""
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
            if dest != 0:
                stack.append(fsa.first_arc(dest))
            if fsa.is_final(arc):
                yield bytes(buf)


_MAX_MATCH_LENGTH = 250  # StringMatcher.MAX_MATCH_LENGTH


def _suggestion_index(suggestions, word):
    for i, (w, _weight) in enumerate(suggestions):
        if w == word:
            return i
    return -1


class _WeightedSpeller:
    """LanguageTool's MorfologikSpeller.getSuggestions (and getFrequency):
    the suggestions of a morfologik Speller with a maximum edit distance
    (replacement candidates and run-on words) as (word, weight) pairs, with
    the case of the word to check."""

    def __init__(self, dictionary, max_edit_distance):
        if max_edit_distance <= 0:
            raise ValueError('maxEditDistance must be > 0: %d' % max_edit_distance)
        self.dictionary = dictionary
        self.speller = Speller(dictionary, max_edit_distance)
        self._lock = threading.Lock()

    def get_frequency(self, word):
        with self._lock:
            freq = self.speller.get_frequency(word)
            if freq == 0 and word != word.lower():
                freq = self.speller.get_frequency(word.lower())
            return freq

    def get_suggestions(self, word):
        suggestions = []
        if len(word) > _MAX_MATCH_LENGTH:
            return suggestions
        with self._lock:
            # (Java creates a new Speller every time)
            if len(word) < 50:  # slow for long words (the limit is arbitrary)
                for candidate in self.speller.find_replacement_candidates(word):
                    suggestions.append((candidate.word, candidate.distance))
            for candidate in self.speller.replace_run_on_word_candidates(word):
                suggestions.append((candidate.word, candidate.distance))
        converts_case = self.speller.convert_case
        if converts_case and is_all_uppercase(word):
            # all upper-case suggestions if necessary
            i = 0
            while i < len(suggestions):
                sugg_word, weight = suggestions[i]
                all_uppercase = sugg_word.upper()
                # do not use capitalized word if it matches the original word or it's mixed case
                if all_uppercase == word or is_mixed_case(sugg_word):
                    all_uppercase = sugg_word
                # remove duplicates
                aux_index = _suggestion_index(suggestions, all_uppercase)
                if aux_index > i:
                    del suggestions[aux_index]
                if -1 < aux_index < i:
                    del suggestions[i]
                    i -= 1
                else:
                    suggestions[i] = (all_uppercase, weight)
                i += 1
        elif converts_case and starts_with_uppercase(word):
            # capitalize suggestions if necessary
            i = 0
            while i < len(suggestions):
                sugg_word, weight = suggestions[i]
                uppercase_first = uppercase_first_char(sugg_word)
                # do not use capitalized word if it matches the original word or it's mixed case
                if uppercase_first == word or is_mixed_case(sugg_word):
                    uppercase_first = sugg_word
                # remove capitalized duplicates
                aux_index = _suggestion_index(suggestions, uppercase_first)
                if aux_index > i:
                    del suggestions[aux_index]
                if -1 < aux_index < i:
                    del suggestions[i]
                    i -= 1
                else:
                    suggestions[i] = (uppercase_first, weight)
                i += 1
        return suggestions


class SuggestionMultiSpeller:
    """The suggestion part of MorfologikMultiSpeller (without user
    dictionaries): the binary speller dictionary and the dictionary built
    from the plain text word lists, with a maximum edit distance."""

    def __init__(self, binary_dict, plain_text_lines, max_edit_distance):
        self.spellers = [_WeightedSpeller(binary_dict, max_edit_distance)]
        if plain_text_lines:
            self.spellers.append(_WeightedSpeller(PlainTextDictionary(plain_text_lines, binary_dict.metadata),
                                                  max_edit_distance))
        self._cache = {}
        self._cache_lock = threading.Lock()

    def get_frequency(self, word):
        """Get the frequency of use of a word (0-27) from the dictionary"""
        for speller in self.spellers:
            freq = speller.get_frequency(word)
            if freq > 0:
                return freq
        return 0

    def _suggestions_from_spellers(self, word):
        result = []
        seen_words = set()
        for speller in self.spellers:
            for sugg_word, weight in speller.get_suggestions(word):
                if sugg_word not in seen_words and sugg_word != word:
                    result.append((sugg_word, weight))
                seen_words.add(sugg_word)
        result.sort(key=lambda s: s[1])  # stable, like Collections.sort
        return result

    def get_suggestions(self, word):
        """The suggestions from all dictionaries (without duplicates)."""
        return [w for w, _weight in self._suggestions_from_spellers(word)]

    def get_weighted_suggestions_from_default_dicts(self, word):
        """The (word, weight) suggestions from the built-in dictionaries
        (cached, like in Java)"""
        r = self._cache.get(word)
        if r is None:
            r = self._suggestions_from_spellers(word)
            with self._cache_lock:
                if len(self._cache) >= 2000:
                    self._cache.clear()
                self._cache[word] = r
        return list(r)


_suggestion_multi_spellers = {}


class WeightedStr(str):
    """A suggestion of the spellers with its weight (SuggestedReplacement
    with getWeight() in Java; plain strings have no weight)."""

    __slots__ = ('weight',)

    def __new__(cls, s, weight=None):
        self = super().__new__(cls, s)
        self.weight = weight
        return self


def suggestion_weight(s):
    """SuggestedReplacement.getWeight() of a suggestion (None without a
    weight)"""
    return getattr(s, 'weight', None)


_STARTS_WITH_NUMBERS_BULLETS = regex.compile(r'(\d[\.,\d]*|\P{L}+)(.*)', regex.DOTALL)
_STARTS_WITH_NUMBERS_BULLETS_EXCEPTIONS = regex.compile(r'([\p{C}\-\$%&]+)(.*)', regex.DOTALL)


class MorfologikSuggestions:
    """Mixin for MorfologikMisspellingCheck: the spelling suggestions of
    MorfologikSpellerRule.getSpellingSuggestions(word), i.e. of the rule
    match of the spelling rule for a sentence with just the (untagged)
    word (no user configuration, no translations, no suggestions for words
    split differently, which need neighbouring tokens). This is not a spell
    checking rule: it is used by ported filters that ask the spelling rule
    for suggestions. Subclasses may override (like the Java rules)
    get_only_suggestions(), get_additional_top_suggestions(),
    get_additional_suggestions(), add_hyphen_suggestions(),
    order_suggestions(), filter_no_suggest_words(),
    ignore_potentially_misspelled_word() and tokenizing_pattern().
    Suggestions are strings here (SuggestedReplacement in Java)."""

    def _suggestion_spellers(self):
        """speller1, speller2 and speller3 (maximum edit distance 1, 2 and 3)"""
        with self._lock:
            spellers = getattr(self, '_suggestion_spellers_cache', None)
            if spellers is not None:
                return spellers
        binary_dict = self.language.dictionary(self.get_file_name().lstrip('/'))
        plain_text = []
        for name in [self.get_spelling_file_name()] + list(self.get_additional_spelling_file_names()):
            p = self.resource_file(name)
            if p is not None:
                plain_text.append(p)
        variant = self.resource_file(self.get_language_variant_spelling_file_name())
        key = (id(binary_dict), tuple(plain_text), variant, type(self).prepare_line_for_speller)
        with _cache_lock:
            spellers = _suggestion_multi_spellers.get(key)
            if spellers is None or spellers[0] is not binary_dict:
                lines = plain_text_speller_lines(plain_text, self.prepare_line_for_speller, variant)
                spellers = _suggestion_multi_spellers[key] = (binary_dict, tuple(
                    SuggestionMultiSpeller(binary_dict, lines, distance) for distance in (1, 2, 3)))
        with self._lock:
            self._suggestion_spellers_cache = spellers[1]
        return spellers[1]

    # --- hooks (SpellingCheckRule/MorfologikSpellerRule defaults) ---

    def get_only_suggestions(self, word):
        return []

    def get_additional_top_suggestions(self, suggestions, word):
        more_suggestions = []
        if (word == 'Languagetool' or word == 'languagetool') and LANGUAGETOOL not in suggestions:
            more_suggestions.append(LANGUAGETOOL)
        if (word == 'Languagetooler' or word == 'languagetooler') and LANGUAGETOOLER not in suggestions:
            more_suggestions.append(LANGUAGETOOLER)
        return more_suggestions

    def get_additional_suggestions(self, suggestions, word):
        return []

    def add_hyphen_suggestions(self, split, top_suggestions):
        pass

    def order_suggestions(self, suggestions, word):
        return suggestions

    def filter_no_suggest_words(self, suggestions):
        return suggestions

    def ignore_potentially_misspelled_word(self, word):
        return False

    def tokenizing_pattern(self):
        return None

    # --- MorfologikSpellerRule ---

    def _can_be_ignored(self, word):
        """canBeIgnored for an untagged token, not immunized nor ignored by
        the speller (ignoreToken with MorfologikSpellerRule.ignoreWord)"""
        from .tokenizers import is_email, is_url
        return is_url(word) or is_email(word) or self.ignore_word(word) or is_emoji(word)

    def filter_suggestions(self, suggestions):
        """SpellingCheckRule.filterSuggestions: remove prohibited words from
        suggestions"""
        suggestions = [s for s in suggestions if not self.is_prohibited(s)]
        new_suggestions = []
        for replacement in suggestions:
            suggestion_without_s = replacement[:-2] if len(replacement) > 3 else ''
            if replacement.endswith(' s') and self._is_proper_noun(suggestion_without_s):
                # "Michael s" -> "Michael's"
                new_suggestions.insert(0, suggestion_without_s)
                new_suggestions.insert(0, suggestion_without_s + "'s")
            else:
                new_suggestions.append(replacement)
        new_suggestions = list(dict.fromkeys(new_suggestions))
        return self.filter_no_suggest_words(new_suggestions)

    def _is_proper_noun(self, word_without_s):
        return any(atr.has_pos_tag('NNP') for atr in self.language.tagger.tag([word_without_s]))

    def calc_speller_suggestions(self, word):
        """MorfologikSpellerRule.calcSpellerSuggestions (without full
        results and user dictionaries)"""
        only_suggestions = self.get_only_suggestions(word)
        if only_suggestions:
            return list(only_suggestions)
        speller1, speller2, speller3 = self._suggestion_spellers()
        # (convertWeighted: the suggestions of the spellers keep their weights)
        default_suggestions = [WeightedStr(w, wt)
                               for w, wt in speller1.get_weighted_suggestions_from_default_dicts(word)]
        only_case_differs = bool(default_suggestions) and java_equals_ignore_case(word, default_suggestions[0])
        if len(word) >= 3 and (only_case_differs or not default_suggestions):
            # speller1 uses a maximum edit distance of 1, it won't find suggestion for "garentee", "greatful" etc.
            default_suggestions.extend(WeightedStr(w, wt)
                                       for w, wt in speller2.get_weighted_suggestions_from_default_dicts(word))
            if len(word) >= 5 and not default_suggestions:
                default_suggestions.extend(WeightedStr(w, wt)
                                           for w, wt in speller3.get_weighted_suggestions_from_default_dicts(word))
        top_suggestions = []
        if not default_suggestions and '-' in word:
            self.add_hyphen_suggestions(java_split(word, '-'), top_suggestions)
        top_suggestions.extend(self.get_additional_top_suggestions(default_suggestions, word))
        default_suggestions[0:0] = top_suggestions
        default_suggestions.extend(self.get_additional_suggestions(default_suggestions, word))
        if not default_suggestions:
            return []
        default_suggestions = self.filter_suggestions(default_suggestions)
        return self.order_suggestions(default_suggestions, word)

    def _rule_match_suggestions(self, word):
        """getRuleMatches for the word of a one-token sentence: None without
        a rule match, the suggestions otherwise"""
        if not self.is_misspelled(word) and not self.is_prohibited(word):
            return None
        if self.ignore_potentially_misspelled_word(word):
            return None
        before_suggestion_str = ''
        suggestions = []
        prevent_further_suggestions = False
        # word starting with numbers or bullets
        clean_word = word
        m = _STARTS_WITH_NUMBERS_BULLETS.fullmatch(word)
        if m and not _STARTS_WITH_NUMBERS_BULLETS_EXCEPTIONS.fullmatch(word):
            first_part = m.group(1)
            second_part = m.group(2)
            second_part_tokens = self.language.word_tokenizer.tokenize(second_part)
            multitoken_is_misspelled = any(self.is_misspelled(t) for t in second_part_tokens)
            if ((not multitoken_is_misspelled or self.is_ignored_no_case(second_part))
                    and not self.is_prohibited(second_part)):
                suggestions.append(first_part + ' ' + second_part)
                prevent_further_suggestions = True
            else:
                before_suggestion_str = first_part + ' '
                clean_word = second_part
        if not prevent_further_suggestions:
            suggestions.extend(before_suggestion_str + s for s in self.calc_speller_suggestions(clean_word))
        return suggestions

    def get_spelling_suggestions(self, w):
        """MorfologikSpellerRule.getSpellingSuggestions: the suggestions of
        the first rule match for a sentence of the single untagged token w"""
        if self._can_be_ignored(w):
            return []
        pattern = self.tokenizing_pattern()
        if pattern is None:
            parts = [w]
        else:
            parts = []
            index = 0
            for m in pattern.finditer(w):
                parts.append(w[index:m.start()])
                index = m.end()
            parts.append(w[index:])
        for part in parts:
            r = self._rule_match_suggestions(part)
            if r is not None:
                return r
        return []
