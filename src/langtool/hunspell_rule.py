"""Hunspell based spell checking rules: port of
org.languagetool.rules.spelling.SpellingCheckRule (the word lists:
ignore.txt, spelling.txt, prohibit.txt, accepted phrases, ignoreWord ...),
org.languagetool.rules.spelling.hunspell.HunspellRule (the misspelling
check with Hunspell, the rule matches with suggestions) and
CompoundAwareHunspellRule (suggestions from a morfologik speller
dictionary, also for the parts of compounds, filtered with Hunspell).

The Hunspell dictionaries are checked with langtool.hunspell (a pure Python
port of Hunspell). The spell checking rules are not part of the rules of
the languages (spell checking is excluded from the port); these classes are
used as the default spelling rule of a language (see
Language.get_default_spelling_rule()), which other code asks whether a
word is misspelled (is_misspelled()), for suggestions (get_suggestions())
or for spelling errors in a sentence (match()). User configurations
(accepted words, preferred languages, suggestion limits) are not supported:
the rules behave like the Java rules without a UserConfig.
"""

import bisect
import os
import threading

import regex

from . import jregex
from .rules.base import Rule, RuleMatch, SuggestedReplacement, TYPE_UNKNOWN_WORD
from .rules.core import Categories
from .tools import is_mixed_case, is_all_uppercase, java_equals_ignore_case, java_trim, starts_with_uppercase, \
    uppercase_first_char

HIGH_CONFIDENCE = 0.99  # SpellingCheckRule.HIGH_CONFIDENCE
LANGUAGETOOL = 'LanguageTool'
LANGUAGETOOLER = 'LanguageTooler'
MAX_TOKEN_LENGTH = 200

_HAS_NO_LETTER_LATIN = regex.compile(r'[^\p{script=latin}]+')
_HAS_NO_LETTER = regex.compile(r'[^\p{L}]+')
_NON_ALPHABETIC = '[^\\p{L}]'
_NON_ALPHABETIC_PATTERN = jregex.compile(_NON_ALPHABETIC)
_STARTS_WITH_TWO_UPPERCASE_CHARS = jregex.compile('[A-Z][A-Z]\\p{javaLowerCase}+')
_MINUS_PLUS = jregex.compile('-+')
# StringTools.CHARS_NOT_FOR_SPELLING
_CHARS_NOT_FOR_SPELLING = jregex.compile('[^\\p{L}\\d\\p{P}\\p{Zs}]')
_ALPHABETIC_CATEGORIES = frozenset(('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl'))

# HunspellRule.commonPortugueseWords / commonGermanWords (no splitting suggestions next to them)
COMMON_PORTUGUESE_WORDS = frozenset((
    "eu", "ja", "so", "de", "e", "a", "o", "da", "do", "em", "que", "uma", "um", "com", "no", "se", "na", "para",
    "por", "os", "foi", "como", "dos", "as", "ao", "mais", "sua", "das", "não", "ou", "km", "seu", "pela", "ser",
    "pelo", "são", "também", "anos", "cidade", "entre", "era", "tem", "mas", "habitantes", "nos", "seus", "área",
    "até", "ele", "onde", "foram", "população", "região", "sobre", "nas", "nome", "parte", "quando", "ano", "aos",
    "grande", "mesmo", "pode", "primeiro", "segundo", "sendo", "suas", "ainda", "dois", "estado", "está", "família",
    "já", "muito", "outros", "americano", "depois", "durante", "maior", "primeira", "forma", "apenas", "banda",
    "densidade", "dia", "então", "município", "norte", "tempo", "após", "duas", "num", "pelos", "qual", "século",
    "ter", "todos", "três", "vez", "água", "acordo", "cobertos", "comuna", "contra", "ela", "grupo", "principal",
    "quais", "sem", "tendo", "às", "álbum", "alguns", "assim", "asteróide", "bem", "brasileiro", "cerca", "desde",
    "este", "localizada", "mundo", "outras", "período", "seguinte", "sido", "vida", "através", "cada", "conhecido",
    "final", "história", "partir", "país", "pessoas", "sistema", "terra", "teve", "tinha", "época",
    "administrativa", "censo", "departamento", "dias", "esta", "filme", "francesa", "música", "província", "série",
    "vezes", "além", "antes", "eles", "eram", "espécie", "governo", "podem", "vários", "censos", "distrito",
    "estão", "exemplo", "hoje", "início", "jogo", "lhe", "lugar", "muitos", "média", "novo", "numa", "número",
    "pois", "possui", "sob", "só", "todo", "tornou", "trabalho", "algumas", "devido", "estava", "fez", "filho",
    "fim", "grandes", "há", "isso", "lado", "local", "morte", "orbital", "outro", "passou", "países", "quatro",
    "representa", "seja", "sempre", "sul", "várias", "capital", "chamado", "começou", " enquanto", "fazer",
    "lançado", "meio", "nova", "nível", "pelas", "poder", "presidente", "redor", "rio", "tarde", "todas",
    "carreira", "casa", "década", "estimada", "guerra", "havia", "livro", "localidades", "maioria", "muitas",
    "obra", "origem", "pai", "pouco", "principais", "produção", "programa", "qualquer", "raio", "seguintes",
    "sucesso", "título", "aproximadamente", "caso", "centro", "conhecida", "construção", "desta", "diagrama",
    "faz", "ilha", "importante", "mar", "melhor", "menos", "mesma", "metros", "mil", "nacional", "populacional",
    "quase", "rei", "sede", "segunda", "tipo", "toda", "uso", "velocidade", "vizinhança", "volta", "base",
    "brasileira", "clube", "desenvolvimento", "deste", "diferentes", "diversos", "empresa", "entanto", "futebol",
    "geral", "junto", "longo", "obras", "outra", "pertencente", "política", "português", "principalmente",
    "processo", "quem", "seria", "têm", "versão", "TV", "acima", "atual", "bairro", "chamada", "cinco", "conta",
    "corpo", "dentro", "deve"))
COMMON_GERMAN_WORDS = frozenset((
    "-", "das", "sein", "mein", "meine", "meinen", "meines", "meiner", "haben", "kein", "keine", "keinen", "keinem",
    "keines", "keiner", "ein", "eines", "eins", "einen", "einem", "eine", "einer", "rund", "sehr", "mach", "noch",
    "nein", "ja", "hallo", "hi", "das", "die", "der", "den", "dem", "des", "nacht", "diesen", "dieser", "dies",
    "dieses", "diesem", "zum", "zur", "beim", "noch", "nichts", "aufs", "aufm", "aufn", "ausn", "ausm", "aus",
    "fürs", "für", "osten", "rein", "raus", "namen", "shippen", "amt", "wir"))


def is_alphabetic_char(c):
    """Character.isAlphabetic for one character"""
    import unicodedata
    if unicodedata.category(c) in _ALPHABETIC_CATEGORIES:
        return True
    return regex.match(r'\p{Alphabetic}', c) is not None


def java_pattern_split(pattern, s):
    """Pattern.split(s): the parts between the matches, trailing empty
    strings removed (a match at the start gives a leading empty string,
    unless it is a zero-width match)"""
    parts = []
    index = 0
    for m in pattern.finditer(s):
        if m.end() == 0:
            continue  # zero-width match at the beginning
        parts.append(s[index:m.start()])
        index = m.end()
    if index == 0:
        return [s]
    parts.append(s[index:])
    while parts and parts[-1] == '':
        parts.pop()
    return parts


def string_for_speller(s):
    """StringTools.stringForSpeller: characters like emojis are replaced by
    whitespace (only in strings that contain characters outside the BMP,
    i.e. a different number of code points and UTF-16 units in Java)"""
    if len(s) > 1 and any(ord(c) > 0xffff for c in s):
        for m in list(_CHARS_NOT_FOR_SPELLING.finditer(s)):
            found = m.group(0)
            s = s.replace(found, ' ' * len(found))
    return s


_BMP_END = '\U00010000'


def _utf16_key(s):
    """sort key of String.compareTo (UTF-16 code unit order): the string
    with the characters outside the BMP replaced by their surrogate pairs
    (whose code points are the UTF-16 code units), i.e. s itself for most
    strings"""
    if not s or max(s) < _BMP_END:
        return s
    return ''.join(c if c < _BMP_END else chr(0xd800 + ((ord(c) - 0x10000) >> 10)) + chr(0xdc00 + (ord(c) & 0x3ff))
                   for c in s)


def _case_insensitive_key(s):
    """sort key of String.CASE_INSENSITIVE_ORDER"""
    if s.isascii():
        return s if s.islower() else s.lower()  # (the same for ASCII strings)
    return ''.join(c.upper().lower() if len(c.upper()) == 1 else c.lower() for c in s)


def common_prefix(a, b):
    """Guava Strings.commonPrefix (does not split surrogate pairs; Python
    strings have no surrogate pairs)"""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return a[:i]


def filter_dupes(words):
    """SpellingCheckRule.filterDupes (Stream.distinct)"""
    return list(dict.fromkeys(words))


def resource_file(language, name):
    """The path of a resource file of the language (name relative to the
    resource directory, like '/de/hunspell/spelling.txt'), looked up in the
    resource directory and then with the dictionary download mechanism if
    the manifest lists it. None if it doesn't exist (JLanguageTool's
    ResourceDataBroker.resourceExists() is false)."""
    if name is None:
        return None
    name = name.lstrip('/')
    p = os.path.join(language.resource_root, name)
    if os.path.exists(p):
        return p
    from . import dictionaries
    lang = name.split('/', 1)[0]
    if name in dictionaries.required_files(lang):
        return dictionaries.locate(name, language.dictionary_path, language.download_dictionaries)
    return None


_word_list_cache = {}
_word_list_lock = threading.Lock()


def load_words(language, name):
    """CachingWordListLoader.loadWords: the lines of a word list without
    comments and empty lines, the part before '#', trimmed (no words if the
    file doesn't exist)"""
    path = resource_file(language, name)
    if path is None:
        return ()
    with _word_list_lock:
        r = _word_list_cache.get(path)
    if r is None:
        from .rules.abstract_rules import load_word_list
        r = tuple(load_word_list(path))
        with _word_list_lock:
            _word_list_cache[path] = r
    return r


def read_lines(path):
    """The lines of a UTF-8 text file (BufferedReader.readLine semantics)"""
    from .rules.abstract_rules import _read_lines
    return list(_read_lines(path))


_IMMUTABLE = (type(None), bool, int, float, str, bytes, frozenset, tuple)


def _comparable_state(attrs):
    """a hash for comparing the attributes of an object (a dict name ->
    value) with those of an object in another process: the values of the
    immutable attributes and of the containers of immutable values, the
    types of the other attributes and of the elements of the other
    containers"""
    out = []
    for name, v in sorted(attrs.items()):
        t = type(v)
        if t in _IMMUTABLE and t is not tuple and t is not frozenset:
            out.append((name, v))
        elif t in (set, frozenset, list, tuple, dict):
            items = list(v.items()) if t is dict else list(v)
            flat = [x for item in items for x in (item if t is dict else (item,))]
            if all(type(x) in _IMMUTABLE and type(x) is not tuple and type(x) is not frozenset for x in flat):
                if t in (set, frozenset, dict):
                    items = sorted(items, key=repr)
                out.append((name, t.__name__, items))
            else:
                out.append((name, t.__name__, len(items), [type(x).__qualname__ for x in flat]))
        else:
            out.append((name, t.__module__ + '.' + t.__qualname__))
    import hashlib
    return hashlib.sha256(repr(out).encode('utf-8', 'surrogatepass')).hexdigest()


def _attribute_changes(before, snapshot, after):
    """the changes of the attributes of an object (dicts name -> value)
    as a list of (name, kind, value), kind 'set' (a new immutable value),
    'add' (elements added to a set) or 'extend' (elements appended to a
    list); None if there are other changes"""
    changes = []
    for name, value in after.items():
        old = before.get(name, _attribute_changes)
        if value is old:
            snap = snapshot[name]
            t = type(value)
            if t is set:
                if value != snap:
                    if not snap <= value:
                        return None
                    changes.append((name, 'add', set(value - snap)))
            elif t is list:
                if len(value) < len(snap) or any(a is not b for a, b in zip(snap, value)):
                    return None
                if len(value) > len(snap):
                    changes.append((name, 'extend', value[len(snap):]))
            elif t is dict:
                if len(value) != len(snap) or any(k not in value or value[k] is not v for k, v in snap.items()):
                    return None
            continue
        if type(value) not in _IMMUTABLE:
            return None
        if type(value) is tuple and any(type(x) not in _IMMUTABLE for x in value):
            return None
        changes.append((name, 'set', value))
    if any(name not in after for name in before):
        return None
    return changes


class _LazyIgnoreSpellingAntiPattern:
    """The anti-pattern that SpellingCheckRule.addIgnoreWords creates for a
    multi-token line: a DisambiguationPatternRule (action IGNORE_SPELLING)
    with a case-sensitive, non-inflected pattern token for every non-blank
    token, created when it is first needed."""

    __slots__ = ('language', 'tokens', '_rule')

    def __init__(self, language, tokens):
        self.language = language
        self.tokens = tokens
        self._rule = None

    @property
    def rule(self):
        r = self._rule
        if r is None:
            from .patterns.pattern_token import PatternToken
            from .patterns.rules import DisambiguationPatternRule, IGNORE_SPELLING
            pattern_tokens = [PatternToken(token, True, False, False) for token in self.tokens]
            r = self._rule = DisambiguationPatternRule('INTERNAL_ANTIPATTERN', '(no description)', self.language,
                                                       pattern_tokens, None, None, IGNORE_SPELLING)
        return r


def _anti_pattern_rule(entry):
    return entry.rule if isinstance(entry, _LazyIgnoreSpellingAntiPattern) else entry


class _AntiPatternIndex:
    """The anti-patterns of a spelling rule (multi-word entries of the word
    lists, accepted phrases), indexed by the token of their first pattern
    token, so that only those that can match a sentence are applied (they
    match case-sensitively; the order in which IGNORE_SPELLING anti-patterns
    are applied doesn't matter)."""

    def __init__(self, entries, first_tokens):
        self.entries = entries
        self.by_first = {}
        self.other = []
        for i, first in enumerate(first_tokens):
            if first is None:
                self.other.append(i)
            else:
                self.by_first.setdefault(first, []).append(i)

    def candidates(self, sentence):
        idx = list(self.other)
        by_first = self.by_first
        for t in sentence.tokens:
            lst = by_first.get(t.token)
            if lst is not None:
                idx.extend(lst)
        return [_anti_pattern_rule(self.entries[i]) for i in sorted(set(idx))]


class SpellingCheckRule(Rule):
    """org.languagetool.rules.spelling.SpellingCheckRule: the word lists
    (ignore, spelling and prohibit files) and the ignore logic. Subclasses
    implement init() (calling super().init()), is_misspelled() and
    match()."""

    def __init__(self, messages, language, user_config=None):
        super().__init__()
        self.messages = messages
        self.language = language
        self.language_model = None
        self.loc_quality_issue_type = 'Misspelling'
        self.words_to_be_ignored = set()
        self.words_to_be_prohibited = set()
        self._ignored_sorted = None
        self._ignored_sorted_keys = None
        self._ignored_sorted_ci = None
        self._ignored_sorted_ci_keys = None
        self._anti_pattern_rules = []
        self._anti_pattern_first_tokens = []
        self._anti_pattern_index = None
        self.consider_ignore_words = True
        self._converts_case = False
        self.ignore_words_with_length = 0

    # --- file names ---

    def get_ignore_file_name(self):
        return self.language.short_code + '/hunspell/ignore.txt'

    def get_spelling_file_name(self):
        return self.language.short_code + '/hunspell/spelling.txt'

    def get_additional_spelling_file_names(self):
        return [self.language.short_code + '/hunspell/spelling_custom.txt', 'spelling_global.txt']

    def get_language_variant_spelling_file_name(self):
        return None

    def get_prohibit_file_name(self):
        return self.language.short_code + '/hunspell/prohibit.txt'

    def get_additional_prohibit_file_names(self):
        return [self.language.short_code + '/hunspell/prohibit_custom.txt']

    def tokenize_new_words(self):
        return True

    def is_latin_script(self):
        return True

    def is_dictionary_based_spelling_rule(self):
        return True

    # --- word lists ---

    def init(self):
        """SpellingCheckRule.init (the result is cached on disk, see
        langtool.diskcache and _cached_init())"""
        from . import diskcache
        cls_key = diskcache.function_key(type(self))
        if cls_key is None or diskcache.language_key(self.language) is None or not diskcache.is_enabled():
            self._init_word_lists()
        else:
            self._cached_init(cls_key)

    def _word_list_files(self):
        """the files read by _init_word_lists()"""
        names = [self.get_ignore_file_name(), self.get_spelling_file_name()]
        names.extend(self.get_additional_spelling_file_names())
        names.extend(self.get_additional_prohibit_file_names())
        names.append(self.get_prohibit_file_name())
        return [resource_file(self.language, n) if n is not None else None for n in names]

    def _cached_init(self, cls_key):
        """_init_word_lists() with the changes of the attributes cached on
        disk: they depend on the word lists, the class (its methods) and
        the language (its tokenizer and dictionaries, e.g. for the line
        expansion of German). The changes are replayed if the attributes
        are as when they were cached; they must be additions to sets and
        lists or new immutable values, else nothing is cached."""
        from . import diskcache
        from .dictionaries import dependency_files
        files = self._word_list_files()
        try:
            before = dict(vars(self))
        except TypeError:
            before = None
        if before is None:
            self._init_word_lists()
            return
        state = _comparable_state(before)
        snapshot = {k: (frozenset(v) if type(v) is set else list(v) if type(v) is list
                        else dict(v) if type(v) is dict else None) for k, v in before.items()}
        language = self.language
        built = []

        def build():
            self._init_word_lists()
            built.append(True)
            return state, _attribute_changes(before, snapshot, vars(self))

        def persist(obj):
            if obj is language:
                return 'L'
            t = type(obj)
            if t is _LazyIgnoreSpellingAntiPattern or t is type:
                return None
            raise diskcache.Uncacheable('unexpected %s %.100r' % (t.__qualname__, obj))

        def resolve(pid):
            if pid == 'L':
                return language
            raise ValueError(pid)

        key = (cls_key, language.code, tuple(files))
        built_state, changes = diskcache.load_or_build(
            'speller-init', key, build, persist=persist, resolve=resolve,
            deps=[f for f in files if f is not None] + dependency_files(language))
        if built:
            return
        if changes is None or built_state != state:
            # (the changes can't be replayed, or not to this state)
            self._init_word_lists()
            return
        d = vars(self)
        for name, kind, value in changes:
            if kind == 'set':
                d[name] = value
            elif kind == 'add':
                d[name].update(value)
            else:  # 'extend'
                d[name].extend(value)

    def _init_word_lists(self):
        """SpellingCheckRule.init: the word lists"""
        for ignore_word in load_words(self.language, self.get_ignore_file_name()):
            self.add_ignore_words(ignore_word)
        if self.get_spelling_file_name() is not None:
            for ignore_word in load_words(self.language, self.get_spelling_file_name()):
                self.add_ignore_words(ignore_word)
        for file_name in self.get_additional_spelling_file_names():
            if resource_file(self.language, file_name) is not None:
                for ignore_word in load_words(self.language, file_name):
                    self.add_ignore_words(ignore_word)
        self._update_ignored_word_dictionary()
        for prohibited_word in load_words(self.language, self.get_prohibit_file_name()):
            self.add_prohibited_words(self.expand_line(prohibited_word))
        for file_name in self.get_additional_prohibit_file_names():
            for prohibited_word in load_words(self.language, file_name):
                self.add_prohibited_words(self.expand_line(prohibited_word))

    def _update_ignored_word_dictionary(self):
        self._ignored_sorted = self._ignored_sorted_keys = None
        self._ignored_sorted_ci = self._ignored_sorted_ci_keys = None

    def add_ignore_tokens(self, tokens):
        """addIgnoreTokens: words that are accepted"""
        self.words_to_be_ignored.update(tokens)
        self._update_ignored_word_dictionary()

    def set_consider_ignore_words(self, consider_ignore_words):
        self.consider_ignore_words = consider_ignore_words

    def set_converts_case(self, converts_case):
        self._converts_case = converts_case

    def add_ignore_words(self, line):
        """SpellingCheckRule.addIgnoreWords: a line of several tokens
        becomes an anti-pattern (each token a case-sensitive, non-inflected
        pattern token) that marks the tokens as ignored by the speller"""
        if not self.tokenize_new_words():
            self.words_to_be_ignored.add(line)
        else:
            # (a line of letters is one token)
            tokens = (line,) if line.isalpha() else self.language.word_tokenizer.tokenize(line)
            if len(tokens) > 1:
                from .patterns.pattern_token import normalize_text_pattern
                pattern_tokens = tuple(token for token in tokens if java_trim(token))
                first = normalize_text_pattern(pattern_tokens[0]) if pattern_tokens else None
                self._add_anti_pattern(_LazyIgnoreSpellingAntiPattern(self.language, pattern_tokens), first)
            else:
                self.words_to_be_ignored.add(line)

    def _add_anti_pattern(self, rule, first_token):
        self._anti_pattern_rules.append(rule)
        self._anti_pattern_first_tokens.append(first_token)
        self._anti_pattern_index = None

    def add_prohibited_words(self, words):
        self.words_to_be_prohibited.update(words)

    def expand_line(self, line):
        return [line]

    def accept_phrases(self, phrases):
        """acceptPhrases: accept (case-sensitively, unless at the start of a
        sentence) the given phrases (replaces the anti-patterns)"""
        from .patterns.pattern_token import PatternTokenBuilder
        from .patterns.rules import make_anti_patterns
        from .analysis import SENTENCE_START_TAGNAME
        anti_patterns = []
        firsts = []
        for phrase in phrases:
            parts = phrase.split(' ')
            pattern_tokens = []
            starts_lowercase = False
            for i, part in enumerate(parts):
                if i == 0 and part != uppercase_first_char(part):
                    starts_lowercase = True
                pattern_tokens.append(PatternTokenBuilder().cs_token(part).build())
            anti_patterns.append(pattern_tokens)
            firsts.append(parts[0])
            if starts_lowercase:
                uc = []
                for j, part in enumerate(parts):
                    if j == 0:
                        # at sentence start, we also need to accept a phrase that starts with an uppercase char:
                        uc.append(PatternTokenBuilder().pos_regex(SENTENCE_START_TAGNAME).build())
                        uc.append(PatternTokenBuilder().cs_token(uppercase_first_char(part)).build())
                    else:
                        uc.append(PatternTokenBuilder().cs_token(part).build())
                anti_patterns.append(uc)
                firsts.append(None)
        self._anti_pattern_rules = make_anti_patterns(anti_patterns, self.language)
        self._anti_pattern_first_tokens = firsts
        self._anti_pattern_index = None

    def get_anti_patterns(self):
        return [_anti_pattern_rule(e) for e in self._anti_pattern_rules]

    def get_sentence_with_immunization(self, sentence):
        """Rule.getSentenceWithImmunization with the anti-patterns that can
        match the sentence"""
        if not self._anti_pattern_rules:
            return sentence
        index = self._anti_pattern_index
        if index is None:
            index = self._anti_pattern_index = _AntiPatternIndex(list(self._anti_pattern_rules),
                                                                 list(self._anti_pattern_first_tokens))
        candidates = index.candidates(sentence)
        if not candidates:
            return sentence
        immunized = sentence.copy()
        for ap in candidates:
            immunized = ap.replace(immunized)
        return immunized

    # --- checks ---

    def is_prohibited(self, word):
        return word in self.words_to_be_prohibited

    def is_in_ignored_set(self, word):
        return word in self.words_to_be_ignored

    def is_ignored_no_case(self, word):
        return (self.is_in_ignored_set(word)
                or (not is_mixed_case(word) and self._converts_case and self.is_in_ignored_set(word.lower()))
                or (self.ignore_words_with_length > 0 and len(word) <= self.ignore_words_with_length))

    def ignore_word(self, word):
        """SpellingCheckRule.ignoreWord(String)"""
        if len(word) > MAX_TOKEN_LENGTH:
            return True
        if not self.consider_ignore_words:
            return False
        # Tokens with no letters cannot have spelling errors. So ignore them.
        no_letter = _HAS_NO_LETTER_LATIN if self.is_latin_script() else _HAS_NO_LETTER
        if no_letter.fullmatch(word):
            return True
        if word.endswith('.') and not self.is_in_ignored_set(word):
            return self.is_ignored_no_case(word[:-1])  # e.g. word at end of sentence
        return self.is_ignored_no_case(word)

    def ignore_word_at(self, words, idx):
        """SpellingCheckRule.ignoreWord(List<String>, int)"""
        return self.ignore_word(words[idx])

    def ignore_token(self, tokens, idx):
        """SpellingCheckRule.ignoreToken"""
        return self.ignore_word_at([t.token for t in tokens], idx)

    def ignore_potentially_misspelled_word(self, word):
        return False

    def _sorted_ignored_words(self, case_sensitive):
        """the ignored words sorted by String.compareTo (case_sensitive) or
        String.CASE_INSENSITIVE_ORDER, and their sort keys (for
        starts_with_ignored_word()). Large lists are cached on disk (see
        langtool.diskcache), they are used if they have the ignored words."""
        words = self.words_to_be_ignored

        def build():
            if case_sensitive:
                if max((max(w) for w in words if w), default='') < _BMP_END:
                    arr = sorted(words)  # (the keys are the words)
                    return arr, arr
                arr = sorted(words, key=_utf16_key)
                return arr, [_utf16_key(w) for w in arr]
            # (sorted(words, key=_case_insensitive_key), computing the keys once)
            wl = list(words)
            ks = [_case_insensitive_key(w) for w in wl]
            order = sorted(range(len(wl)), key=ks.__getitem__)
            return [wl[i] for i in order], [ks[i] for i in order]
        from . import diskcache
        cls_key = diskcache.function_key(type(self))
        if cls_key is None or len(words) < 20000 or diskcache.language_key(self.language) is None:
            return build()
        arr, keys = diskcache.cached('speller-sorted-words', (cls_key, self.language.code, case_sensitive, len(words)),
                                     build)
        if len(arr) != len(words) or not words.issuperset(arr):
            return build()
        return arr, keys

    def starts_with_ignored_word(self, word, case_sensitive):
        """startsWithIgnoredWord: the length of the longest ignored word
        that word starts with (0 if none, or if the word is shorter than 4
        characters)"""
        if len(word) < 4:
            return 0
        if case_sensitive:
            if self._ignored_sorted is None:
                arr, self._ignored_sorted_keys = self._sorted_ignored_words(True)
                self._ignored_sorted = arr  # (set last: other threads check it)
            arr, keys, keyf = self._ignored_sorted, self._ignored_sorted_keys, _utf16_key
        else:
            if self._ignored_sorted_ci is None:
                arr, self._ignored_sorted_ci_keys = self._sorted_ignored_words(False)
                self._ignored_sorted_ci = arr  # (set last: other threads check it)
            arr, keys, keyf = self._ignored_sorted_ci, self._ignored_sorted_ci_keys, _case_insensitive_key
        while word:
            k = keyf(word)
            pos = bisect.bisect_left(keys, k)
            if pos < len(keys) and keys[pos] == k:
                break
            prev = pos - 1
            if prev < 0:
                return 0
            if case_sensitive:
                prefix = common_prefix(word, arr[prev])
            else:
                prefix = common_prefix(word.lower(), arr[prev].lower())
            word = prefix if case_sensitive else word[:len(prefix)]
        return len(word)

    # --- suggestions ---

    def get_additional_top_suggestions(self, suggestions, word):
        """suggestions and the result are lists of SuggestedReplacement"""
        more = []
        if word in ('Languagetool', 'languagetool') and not any(k.replacement == LANGUAGETOOL for k in suggestions):
            more.append(LANGUAGETOOL)
        if word in ('Languagetooler', 'languagetooler') and not any(
                k.replacement == LANGUAGETOOLER for k in suggestions):
            more.append(LANGUAGETOOLER)
        return [SuggestedReplacement(s) for s in more]

    def get_only_suggestions(self, word):
        return []

    def get_additional_suggestions(self, suggestions, word):
        return []

    def filter_suggestions(self, suggestions):
        """filterSuggestions: removes prohibited words (a list of
        SuggestedReplacement)"""
        suggestions = [s for s in suggestions if not self.is_prohibited(s.replacement)]
        new_suggestions = []
        for suggestion in suggestions:
            replacement = suggestion.replacement
            suggestion_without_s = replacement[:-2] if len(replacement) > 3 else ''
            if replacement.endswith(' s') and self._is_proper_noun(suggestion_without_s):
                # "Michael s" -> "Michael's"
                new_suggestions.insert(0, SuggestedReplacement(suggestion_without_s))
                new_suggestions.insert(0, SuggestedReplacement(suggestion_without_s + "'s"))
            else:
                new_suggestions.append(suggestion)
        new_suggestions = filter_dupes(new_suggestions)
        return self.filter_no_suggest_words(new_suggestions)

    def filter_no_suggest_words(self, suggestions):
        return suggestions

    def _is_proper_noun(self, word_without_s):
        tags = self.language.tagger.tag([word_without_s])
        return any(k.has_pos_tag('NNP') for k in tags)

    def create_wrong_split_match(self, sentence, rule_matches_so_far, pos, covered_word, suggestion1, suggestion2,
                                 prev_pos):
        if rule_matches_so_far:
            prev_match = rule_matches_so_far[-1]
            if prev_match.from_pos == prev_pos:
                # we'll later create a new match that covers the previous misspelled word and the current one:
                rule_matches_so_far.pop()
        rule_match = RuleMatch(self, sentence, prev_pos, pos + len(covered_word), self.messages.get('spelling'),
                               self.messages.get('desc_spelling_short'))
        rule_match.type = TYPE_UNKNOWN_WORD
        rule_match.set_suggested_replacement(java_trim(suggestion1 + ' ' + suggestion2))
        return rule_match


_non_word_patterns = {}


def compute_non_word_pattern(aff_path):
    """HunspellRule.computeNonWordPattern: the Java regex of the characters
    that split words: non-letters except the WORDCHARS of the .aff file"""
    r = _non_word_patterns.get(aff_path)
    if r is None:
        r = _NON_ALPHABETIC
        with open(aff_path, encoding='utf-8', errors='replace') as f:
            for line in f.read().splitlines():
                if line.startswith('WORDCHARS '):
                    word_chars = line[len('WORDCHARS '):]
                    r = '(?![' + word_chars.replace('-', '\\-') + '])' + _NON_ALPHABETIC
                    break
        _non_word_patterns[aff_path] = r
    return r


_ignore_file_contents = {}


class HunspellRule(SpellingCheckRule):
    """org.languagetool.rules.spelling.hunspell.HunspellRule: a Hunspell
    based spell checking rule. The dictionary is
    <lang>/hunspell/<lang>_<first country>.dic/.aff; without it the rule
    finds no errors (only prohibited words are misspelled)."""

    RULE_ID = 'HUNSPELL_RULE'

    def __init__(self, messages, language, user_config=None, alt_languages=None, language_model=None):
        super().__init__(messages, language, user_config)
        self.category = Categories.get('TYPOS', messages)
        self.user_config = user_config
        self.hunspell = None
        # nonWordPattern (Java regex source and compiled)
        self.non_word_pattern_source = None
        self.non_word_pattern = None
        self._needs_init = True
        self._init_lock = threading.RLock()

    def get_id(self):
        return self.RULE_ID

    def get_description(self):
        return self.messages.get('desc_spelling')

    def ensure_initialized(self):
        if self._needs_init:
            with self._init_lock:
                if self._needs_init:
                    try:
                        self.init()
                    finally:
                        self._needs_init = False

    def get_dict_filename_in_resources(self, lang_country):
        return '/' + self.language.short_code + '/hunspell/' + lang_country + '.dic'

    def init(self):
        """HunspellRule.init"""
        super().init()
        lang_country = self.language.short_code
        if self.language.countries:
            lang_country += '_' + self.language.countries[0]
        short_dic_path = self.get_dict_filename_in_resources(lang_country)
        dic = resource_file(self.language, short_dic_path)
        if dic is not None:
            aff_name = short_dic_path[:-3] + 'aff'
            aff = resource_file(self.language, aff_name)
            from .hunspell import get_dictionary
            self.hunspell = get_dictionary(dic, aff)
            self._add_ignore_words_from_ignore_file()
            self.set_non_word_pattern(compute_non_word_pattern(aff))
        if self.non_word_pattern is None:
            self.set_non_word_pattern(_NON_ALPHABETIC)

    def set_non_word_pattern(self, java_regex):
        self.non_word_pattern_source = java_regex
        self.non_word_pattern = jregex.compile(java_regex)

    def _add_ignore_words_from_ignore_file(self):
        """HunspellRule.addIgnoreWords: the (raw) lines of the ignore file"""
        path = resource_file(self.language, self.get_ignore_file_name())
        if path is None:
            return
        lines = _ignore_file_contents.get(path)
        if lines is None:
            lines = _ignore_file_contents[path] = tuple(line for line in read_lines(path) if not line.startswith('#'))
        self.words_to_be_ignored.update(lines)

    def is_in_ignored_set(self, word):
        # We don't add these words to the main set to prevent startsWithIgnoredWord honoring them
        return super().is_in_ignored_set(word) or word == LANGUAGETOOL or word == LANGUAGETOOLER

    def is_quoted_compound(self, sentence, idx, token):
        """Is the given token part of a hyphenated compound preceded by a
        quoted token (e.g., „Spiegel“-Magazin)"""
        return False

    def accept_suggestion(self, suggestion):
        return True

    def get_message(self, orig_word, first_suggestion):
        return self.messages.get('spelling')

    def get_short_message(self, orig_word, first_suggestion):
        return self.messages.get('desc_spelling_short')

    def tokenize_text(self, sentence):
        return java_pattern_split(self.non_word_pattern, sentence)

    def get_sentence_text_without_urls_and_immunized_tokens(self, sentence):
        from .tokenizers import is_email, is_url
        sb = []
        sentence_tokens = self.get_sentence_with_immunization(sentence).tokens
        for i in range(1, len(sentence_tokens)):
            atr = sentence_tokens[i]
            token = atr.token
            if (atr.immunized or atr.ignored_by_speller or is_url(token) or is_email(token)
                    or self.is_quoted_compound(sentence, i, token) or atr.has_pos_tag('_english_ignore_')):
                if self.is_quoted_compound(sentence, i, token):
                    sb.append(' ' + token[1:])
                else:
                    # replace URLs and immunized tokens with whitespace to ignore them for spell checking:
                    sb.append(' ' * len(token))
            else:
                sb.append(string_for_speller(token))
        return ''.join(sb)

    def match(self, sentence, with_suggestions=True):
        """HunspellRule.match: the spelling errors of the sentence (with
        suggestions unless with_suggestions is False, which is faster and
        gives the same matches)"""
        rule_matches = []
        self.ensure_initialized()
        if self.hunspell is None:
            # some languages might not have a dictionary, be silent about it
            return rule_matches
        tokens = self.tokenize_text(self.get_sentence_text_without_urls_and_immunized_tokens(sentence))
        # starting with the first token to skip the zero-length START_SENT
        if len(sentence.tokens) > 1:
            length = sentence.tokens[1].start_pos
        else:
            length = sentence.tokens[0].start_pos
        prev_start_pos = -1
        lang = self.language.short_code
        for i, word in enumerate(tokens):
            dash_corr = 0
            if ((self.ignore_word_at(tokens, i) or self.ignore_word(word))
                    and not self.is_prohibited(_cut_off_dot(word))):
                prev_start_pos = length
                length += len(word) + 1
                continue
            if self.is_misspelled(word):
                if self.ignore_potentially_misspelled_word(word):
                    prev_start_pos = length
                    length += len(word) + 1
                    continue
                clean_word = word[:-1] if word.endswith('.') else word
                if word.startswith('-'):
                    if not self.is_misspelled(clean_word[1:]) or _MINUS_PLUS.fullmatch(clean_word):
                        length += len(word) + 1
                        continue
                    else:
                        dash_corr += 1
                if i > 0 and prev_start_pos != -1:
                    prev_word = tokens[i - 1]
                    ignore_splitting = False
                    if lang == 'pt' and (prev_word.lower() in COMMON_PORTUGUESE_WORDS
                                         or word.lower() in COMMON_PORTUGUESE_WORDS):
                        ignore_splitting = True
                    if lang == 'de' and (prev_word.lower() in COMMON_GERMAN_WORDS
                                         or word.lower() in COMMON_GERMAN_WORDS):
                        ignore_splitting = True
                    if not ignore_splitting and len(prev_word) > 0:
                        # "thanky ou" -> "thank you"
                        sugg1a = prev_word[:-1]
                        sugg1b = _cut_off_dot(prev_word[-1:] + word)
                        if (not self.is_misspelled(sugg1a) and not self.is_misspelled(sugg1b)
                                and self.accept_suggestion(sugg1a + ' ' + sugg1b)):
                            rm = self.create_wrong_split_match(sentence, rule_matches, length, clean_word, sugg1a,
                                                               sugg1b, prev_start_pos)
                            if rm is not None:
                                rule_matches.append(rm)
                        # "than kyou" -> "thank you"
                        sugg2a = prev_word + word[0]
                        sugg2b = _cut_off_dot(word[1:])
                        if (not self.is_misspelled(sugg2a) and not self.is_misspelled(sugg2b)
                                and self.accept_suggestion(sugg2a + ' ' + sugg2b)):
                            rm = self.create_wrong_split_match(sentence, rule_matches, length, clean_word, sugg2a,
                                                               sugg2b, prev_start_pos)
                            if rm is not None:
                                rule_matches.append(rm)
                rule_match = RuleMatch(self, sentence, length + dash_corr, length + len(clean_word),
                                       self.messages.get('spelling'), self.messages.get('desc_spelling_short'))
                rule_match.type = TYPE_UNKNOWN_WORD
                clean_word2 = clean_word[dash_corr:]
                if with_suggestions:
                    sugg = self.calc_suggestions(word, clean_word2)
                    if self.is_first_item_high_confidence_suggestion(word, sugg):
                        sugg[0].confidence = HIGH_CONFIDENCE
                    if sugg:
                        rule_match.message = self.get_message(clean_word2, sugg[0])
                    rule_match.set_suggested_replacement_objects(sugg)
                rule_matches.append(rule_match)
            prev_start_pos = length + dash_corr
            length += len(word) + 1
        return rule_matches

    def is_first_item_high_confidence_suggestion(self, word, sugg):
        """finds cases like "HAus", where "Haus" is surely the proper
        suggestion (sugg: list of SuggestedReplacement)"""
        if (sugg and word != 'IPs' and java_equals_ignore_case(word, sugg[0].replacement)
                and _STARTS_WITH_TWO_UPPERCASE_CHARS.fullmatch(word) and self.language.short_code == 'de'):
            if word.endswith('s') and _is_all_upper_case_commons(sugg[0].replacement):
                # e.g. "DMs" could mean plural of "DM"
                return False
            return True
        return False

    def calc_suggestions(self, word, clean_word):
        """HunspellRule.calcSuggestions: a list of SuggestedReplacement"""
        only_suggestions = self.get_only_suggestions(clean_word)
        if only_suggestions:
            return list(only_suggestions)
        suggestions = [SuggestedReplacement(s) for s in self.get_suggestions(clean_word)]
        if word.endswith('.'):
            pos = 1
            for suggestion in self.get_suggestions(word):
                if not any(suggestion == sr.replacement for sr in suggestions):
                    suggestions.insert(min(pos, len(suggestions)), SuggestedReplacement(suggestion[:-1]))
                    pos += 2  # we mix the lists, as we don't know which one is the better one
        additional_top_suggestions = self.get_additional_top_suggestions(suggestions, clean_word)
        if not additional_top_suggestions and word.endswith('.'):
            converted = []
            for sugg in self.get_additional_top_suggestions(suggestions, word):
                if sugg.replacement.endswith('.'):
                    converted.append(sugg)
                else:
                    converted.append(sugg.copy(sugg.replacement + '.'))
            additional_top_suggestions = converted
        additional_top_suggestions = list(reversed(additional_top_suggestions))
        for additional_top_suggestion in additional_top_suggestions:
            if clean_word != additional_top_suggestion.replacement:
                suggestions.insert(0, additional_top_suggestion)
        additional_suggestions = self.get_additional_suggestions(suggestions, clean_word)
        for additional_suggestion in additional_suggestions:
            if clean_word != additional_suggestion.replacement:
                suggestions.extend(additional_suggestions)
        suggestions = [k for k in suggestions if self.accept_suggestion(k.replacement)]
        suggestions = filter_dupes(self.filter_suggestions(suggestions))
        return suggestions

    def is_misspelled(self, word):
        """HunspellRule.isMisspelled"""
        self.ensure_initialized()
        is_alphabetic = True
        if len(word) == 1 and ord(word) <= 0xffff:  # hunspell dictionaries usually do not contain punctuation
            is_alphabetic = is_alphabetic_char(word)
        return ((is_alphabetic and word != '--'
                 and (self.hunspell is not None and not self.hunspell.spell(word))
                 and not self.ignore_word(word))
                or self.is_prohibited(_cut_off_dot(word)))

    def get_suggestions(self, word):
        """HunspellRule.getSuggestions: Hunspell's suggestions"""
        self.ensure_initialized()
        if self.hunspell is None:
            return []
        return list(self.hunspell.suggest(word))

    def sort_suggestion_by_quality(self, misspelling, suggestions):
        return suggestions


def _is_all_upper_case_commons(s):
    """StringUtils.isAllUpperCase (commons-lang3): non-empty and only
    upper case characters"""
    from .tools import is_upper_case
    return bool(s) and all(is_upper_case(c) for c in s)


def _cut_off_dot(s):
    return s[:-1] if s.endswith('.') else s


MAX_SUGGESTIONS = 20  # CompoundAwareHunspellRule.MAX_SUGGESTIONS


class CompoundAwareHunspellRule(HunspellRule):
    """org.languagetool.rules.spelling.hunspell.CompoundAwareHunspellRule:
    the suggestions come from a morfologik speller (as Hunspell's are too
    slow), also for the parts of the compound, filtered with Hunspell.
    Subclasses implement filter_for_language(), get_morfo_speller() (a
    langtool.spelling.SuggestionMultiSpeller or None) and
    get_compound_splitter() (an object with tokenize(word))."""

    def filter_for_language(self, suggestions):
        raise NotImplementedError()

    def get_morfo_speller(self):
        raise NotImplementedError()

    def get_compound_splitter(self):
        raise NotImplementedError()

    def get_suggestions(self, word):
        """As a hunspell-based approach is too slow, we use Morfologik to
        create suggestions. As this won't work for compounds not in the
        dictionary, we split the word and also get suggestions on the
        compound parts. In the end, all candidates are filtered against
        Hunspell again (which supports compounds)."""
        self.ensure_initialized()
        candidates = self.get_candidates(word)
        simple_suggestions = self._get_correct_words(candidates)
        simple_suggestions = self.get_filtered_suggestions(simple_suggestions)
        morfo_speller = self.get_morfo_speller()
        # after getCorrectWords() so spelling.txt is considered:
        no_split_suggestions = morfo_speller.get_suggestions(word)
        _handle_word_end_punctuation('.', word, no_split_suggestions, morfo_speller)
        _handle_word_end_punctuation('...', word, no_split_suggestions, morfo_speller)
        no_split_lowercase_suggestions = []
        if starts_with_uppercase(word) and not is_all_uppercase(word):
            # almost all words can be uppercase because they can appear at the start of a sentence:
            no_split_lowercase_suggestions = morfo_speller.get_suggestions(word.lower())
        # We don't know about the quality of the results here, so mix both lists together,
        # taking elements from both lists on a rotating basis:
        suggestions = []
        for i in range(max(len(simple_suggestions), len(no_split_suggestions), len(no_split_lowercase_suggestions))):
            if i < len(no_split_suggestions):
                suggestions.append(no_split_suggestions[i])
            if i < len(no_split_lowercase_suggestions):
                suggestions.append(uppercase_first_char(no_split_lowercase_suggestions[i]))
            # put these behind suggestions by Morfologik, often low-quality / made-up words
            if i < len(simple_suggestions):
                suggestions.append(simple_suggestions[i])
        suggestions = filter_dupes(suggestions)
        self.filter_for_language(suggestions)
        sorted_suggestions = self.sort_suggestion_by_quality(word, suggestions)
        return sorted_suggestions[:MAX_SUGGESTIONS]

    def get_candidates(self, word):
        """Find potential corrections - it's okay if some of these are not
        valid words, this list will be filtered against the spellchecker
        before being returned to the user."""
        return self.get_compound_splitter().tokenize(word)

    def get_candidates_for_parts(self, parts):
        """CompoundAwareHunspellRule.getCandidates(List<String> parts)"""
        from .tools import lowercase_first_char
        candidates = []
        morfo_speller = None
        for part_count, part in enumerate(parts):
            if not self.hunspell.spell(part):
                # assume noun, so use uppercase:
                if morfo_speller is None:
                    morfo_speller = self.get_morfo_speller()
                do_upper_case = part_count > 0 and not starts_with_uppercase(part)
                suggestions = morfo_speller.get_suggestions(uppercase_first_char(part) if do_upper_case else part)
                if not suggestions:
                    suggestions = morfo_speller.get_suggestions(lowercase_first_char(part) if do_upper_case else part)
                append_s = False
                if do_upper_case and part.endswith('s'):  # maybe infix-s as in "Dampfschiffahrtskapitän"
                    suggestions.extend(morfo_speller.get_suggestions(part[:-1]))
                    append_s = True
                for suggestion in suggestions:
                    parts_copy = list(parts)
                    if append_s:
                        suggestion += 's'
                    if part_count > 0 and parts[part_count].startswith('-') and len(parts[part_count]) > 1:
                        parts_copy[part_count] = '-' + uppercase_first_char(suggestion[1:])
                    elif part_count > 0 and not parts[part_count - 1].endswith('-'):
                        parts_copy[part_count] = suggestion.lower()
                    else:
                        parts_copy[part_count] = suggestion
                    candidate = ''.join(parts_copy)
                    if not self.is_misspelled(candidate):
                        candidates.append(candidate)
                    # Arbeidszimmer -> Arbeitszimmer:
                    if part_count < len(parts) - 1 and part.endswith('s') and suggestion.endswith('-'):
                        parts_copy[part_count] = suggestion[:-1]
                        infix_candidate = ''.join(parts_copy)
                        if not self.is_misspelled(infix_candidate):
                            candidates.append(infix_candidate)
        return candidates

    def sort_suggestion_by_quality(self, misspelling, suggestions):
        result = []
        for suggestion in suggestions:
            if (suggestion.replace(' ', '') == misspelling
                    and not any(len(k) == 1 for k in suggestion.split(' ') if k)):
                # prefer run-on words unless a single letter is split off:
                result.insert(0, suggestion)
            else:
                result.append(suggestion)
        return result

    def _get_correct_words(self, words_or_phrases):
        """avoid over-accepting words, as the Morfologik approach above
        might construct compound words with parts that are correct but the
        compound is not correct (e.g. "Arbeit + Amt = Arbeitamt")"""
        result = []
        for word_or_phrase in words_or_phrases:
            # this might be a phrase like "aufgrund dessen", so it needs to be split:
            words = self.tokenize_text(word_or_phrase)
            word_is_okay = True
            for word in words:
                if not self.hunspell.spell(word):
                    word_is_okay = False
                    break
            if word_is_okay:
                result.append(word_or_phrase)
        return result

    def get_filtered_suggestions(self, words_or_phrases):
        return words_or_phrases


def _handle_word_end_punctuation(punct, word, no_split_suggestions, morfo_speller):
    if word.endswith(punct):
        # e.g. "informationnen." - the dot is a word char in hunspell, so it needs special treatment here
        for s in morfo_speller.get_suggestions(word[:-len(punct)]):
            no_split_suggestions.append(s + punct)
