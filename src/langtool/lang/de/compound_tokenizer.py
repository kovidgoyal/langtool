"""Port of jWordSplitter 4.7 (de.danielnaber.jwordsplitter:
AbstractWordSplitter, GermanWordSplitter, GermanInterfixDisambiguator,
ExceptionSplits, EmbeddedGermanDictionary) and of
org.languagetool.tokenizers.de.GermanCompoundTokenizer (with its
ExtendedGermanWordSplitter).

The word list and the exception splits of the jWordSplitter jar are
downloaded (de/jwordsplitter/wordsGerman.txt and exceptionsGerman.txt, see
dictionaries.json). Words are processed as Java strings (characters outside
the BMP as surrogate pairs), so the splits are the same as in Java.
"""

import threading

from ...tools import java_trim

_WORDS_FILE = 'de/jwordsplitter/wordsGerman.txt'
_EXCEPTIONS_FILE = 'de/jwordsplitter/exceptionsGerman.txt'

_lock = threading.Lock()
_embedded_words = None
_exception_lines = None


def _locate(name, dictionary_path=None, download=True):
    from ...dictionaries import locate
    return locate(name, dictionary_path, download)


def _to_java(s):
    """The string as UTF-16 code units (like a Java String)"""
    if not s or max(s) <= '￿':
        return s
    return ''.join(_java_chars(s))


def _java_chars(s):
    for c in s:
        o = ord(c)
        if o > 0xffff:
            o -= 0x10000
            yield chr(0xd800 + (o >> 10))
            yield chr(0xdc00 + (o & 0x3ff))
        else:
            yield c


def _from_java(s):
    """Inverse of _to_java (lone surrogates stay as they are)"""
    if not s or max(s) < '\ud800':
        return s
    return s.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'surrogatepass')


def embedded_german_words(dictionary_path=None, download=True):
    """EmbeddedGermanDictionary.getWords(): the lowercased lines of
    wordsGerman.txt (without the lines starting with '#')"""
    global _embedded_words
    if _embedded_words is None:
        with _lock:
            if _embedded_words is None:
                words = set()
                with open(_locate(_WORDS_FILE, dictionary_path, download), encoding='utf-8') as f:
                    for line in f:
                        line = line.rstrip('\r\n')
                        if not line.startswith('#'):
                            words.add(_to_java(java_trim(line).lower()))
                _embedded_words = frozenset(words)
    return _embedded_words


def _load_exception_lines(dictionary_path=None, download=True):
    global _exception_lines
    if _exception_lines is None:
        with _lock:
            if _exception_lines is None:
                with open(_locate(_EXCEPTIONS_FILE, dictionary_path, download), encoding='utf-8') as f:
                    _exception_lines = f.read().splitlines()
    return _exception_lines


def _java_split_pipe(s):
    """String.split("\\\\|") (trailing empty strings removed)"""
    parts = s.split('|')
    while len(parts) > 1 and parts[-1] == '':
        parts.pop()
    if parts == ['']:
        return ['']
    return parts


class InputTooLongException(ValueError):
    """de.danielnaber.jwordsplitter.InputTooLongException"""


class ExceptionSplits:
    """ExceptionSplits: exceptions for splitting, loaded from a file (one
    split per line, parts delimited by '|', '/NS' adds the variants with
    the suffixes 'n' and 's')"""

    def __init__(self, lines=None):
        self.exception_map = {}
        if lines is None:
            return
        for line in lines:
            line = java_trim(line)
            if line and not line.startswith('#'):
                line = _to_java(line)
                parts = _java_split_pipe(line.replace('/NS', ''))
                complete_word = line.replace('|', '')
                if '/' in complete_word:
                    if complete_word.endswith('/NS'):
                        real_word = complete_word.replace('/NS', '').lower()
                        self.exception_map[real_word] = list(parts)
                        self.exception_map[real_word + 'n'] = self._add_to_last_part(parts, 'n')
                        self.exception_map[real_word + 's'] = self._add_to_last_part(parts, 's')
                    else:
                        raise ValueError('Unknown suffix in line: ' + line)
                else:
                    self.exception_map[complete_word.lower()] = list(parts)

    @staticmethod
    def _add_to_last_part(parts, suffix):
        result = list(parts)
        result[-1] = result[-1] + suffix
        return result

    def get_exception_split_or_none(self, word):
        """getExceptionSplitOrNull(): a new list (the parts with the case of
        the given word if they make up the word)"""
        lc_word = word.lower()
        result = self.exception_map.get(lc_word)
        if result is not None:
            if lc_word == ''.join(result).lower():
                return self._split_equally(result, word)
            return list(result)
        return None

    @staticmethod
    def _split_equally(splitted, original):
        out = []
        offset = 0
        for s in splitted:
            out.append(original[offset:offset + len(s)])
            offset += len(s)
        return out

    def add_split(self, word, word_parts):
        self.exception_map[word.lower()] = list(word_parts)


class GermanInterfixDisambiguator:
    """GermanInterfixDisambiguator: resolves ambiguities like
    Urlaub+s+Orte vs. Urlaub+Sorte"""

    WORDS_REQUIRING_INTERFIX_S = frozenset(['Verhalten'])

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def disambiguate(self, parts):
        new_parts = list(parts)
        last_idx = len(parts) - 1
        if len(parts) > 1:
            last_part = parts[last_idx]
            if last_part in ('samt', 'samts', 'samtes'):
                # Verkehr+s+amt = Verkehrs+amt
                new_parts[last_idx - 1] = parts[last_idx - 1] + 's'
                new_parts[last_idx] = last_part[1:] if last_part.startswith('s') else last_part
                return new_parts
        for i in range(len(new_parts) - 1, 1, -1):
            part = new_parts[i]
            prev_part = new_parts[i - 1]
            prev_prev_part = new_parts[i - 2]
            if prev_part == 's':
                part_is_word = ('s' + part).lower() in self.dictionary
                if not part_is_word or prev_prev_part in self.WORDS_REQUIRING_INTERFIX_S:
                    # Schönheit+s+tempel = Schönheits-tempel
                    new_parts[i - 2] = prev_prev_part + 's'
                    del new_parts[i - 1]
        return new_parts


class GermanWordSplitter:
    """GermanWordSplitter (with AbstractWordSplitter): splits German
    compound words into their parts, based on a word list."""

    INTERFIXES = ('s-', 's', '-')

    def __init__(self, hide_interfix_characters, words=None, dictionary_path=None, download=True):
        self.hide_interfix_characters = hide_interfix_characters
        embedded = embedded_german_words(dictionary_path, download)
        self.words = embedded if words is None else words
        self.strict_mode = True
        self.minimum_word_length = 3
        self.maximum_word_length = 70
        # init(): the disambiguator uses the embedded dictionary
        self.disambiguator = GermanInterfixDisambiguator(embedded)
        self.exception_splits = ExceptionSplits(_load_exception_lines(dictionary_path, download))
        self._cache = {}

    def set_minimum_word_length(self, length):
        self.minimum_word_length = length
        self._cache.clear()

    def set_maximum_word_length(self, length):
        self.maximum_word_length = length
        self._cache.clear()

    def add_exception(self, complete_word, word_parts):
        self.exception_splits.add_split(_to_java(complete_word).lower(), [_to_java(p) for p in word_parts])
        self._cache.clear()

    def set_strict_mode(self, strict_mode):
        self.strict_mode = strict_mode
        self._cache.clear()

    def _check_length(self, word):
        if len(word) > self.maximum_word_length:
            raise InputTooLongException(
                "Input too long (%d characters), maximum is %d characters to avoid potentially long processing "
                "times: '%s'" % (len(word), self.maximum_word_length, _from_java(word)))

    # --- getAllSplits ---

    def get_all_splits(self, word):
        """getAllSplits(): all splits of the word (experimental in
        jWordSplitter), as lists of parts"""
        jword = _to_java(word)
        self._check_length(jword)
        return [[_from_java(p) for p in split] for split in self._get_all_splits(jword)]

    def _get_all_splits(self, word):
        result = self._get_all_splits_dir(word, True)
        for split in self._get_all_splits_dir(word, False):
            if split not in result:
                result.append(split)
        return result

    def _get_all_splits_dir(self, word, from_left):
        self._check_length(word)
        result = []
        mwl = self.minimum_word_length
        n = len(word)
        indexes = range(mwl, n - mwl) if from_left else range(n - mwl, mwl, -1)
        for i in indexes:
            left = word[:i]
            right = word[i:]
            relevant = left if from_left else right
            if self._is_simple_word(relevant):
                result.append([left, right])
                for other in self._get_all_splits(right if from_left else left):
                    result.append([left] + other if from_left else other + [right])
        return result

    # --- splitWord ---

    def get_sub_words(self, word):
        return self.split_word(word, True)

    def split_word(self, word, collect_subwords=False):
        """splitWord(): the compound parts, a list with the (trimmed) word
        itself if it cannot be split, an empty list for None"""
        if word is None:
            return []
        key = (word, collect_subwords)
        cached = self._cache.get(key)
        if cached is None:
            jword = _to_java(word)
            self._check_length(jword)
            cached = tuple(_from_java(p) for p in self._split_word(jword, collect_subwords))
            if len(self._cache) > 50000:
                self._cache.clear()
            self._cache[key] = cached
        return list(cached)

    def _split_word(self, word, collect_subwords):
        trimmed = java_trim(word)
        exception_split = self.exception_splits.get_exception_split_or_none(trimmed)
        if exception_split is not None:
            return exception_split
        parts = self._split(trimmed, False, collect_subwords)
        if parts is None:
            return [trimmed]
        parts = self.disambiguator.disambiguate(parts)
        # cleanLeadingAndTrailingHyphens
        for i, element in enumerate(parts):
            if element.startswith('-'):
                parts[i] = element[1:]
            if element.endswith('-'):
                parts[i] = element[:-1]
        return parts

    def _split(self, word, allow_interfix_removal, collect_subwords):
        parts = self.exception_splits.get_exception_split_or_none(word)
        if parts is not None:
            return parts
        lc_word = word.lower()
        removable_interfix = self._find_interfix_or_none(lc_word)
        word_without_interfix = word[:len(word) - len(removable_interfix)] if removable_interfix is not None \
            else word
        can_interfix_be_removed = removable_interfix is not None and allow_interfix_removal
        if self._is_simple_word(word) and not collect_subwords:
            parts = [word]
        elif can_interfix_be_removed and self._is_simple_word(word_without_interfix):
            if self.hide_interfix_characters:
                parts = [word_without_interfix]
            else:
                parts = [word_without_interfix, removable_interfix]
        else:
            parts = self._split_from_right(word, collect_subwords)
            if parts is None and self._is_simple_word(word):
                parts = [word]
            elif parts is not None and self._is_simple_word(word) and word not in parts:
                parts.append(word)
            if parts is None and self._ends_with_interfix(lc_word):
                parts = self._split_from_right(word_without_interfix, collect_subwords)
                if parts is not None and not self.hide_interfix_characters:
                    parts.append(removable_interfix)
        return parts

    def _split_from_right(self, word, collect_subwords):
        parts = self.exception_splits.get_exception_split_or_none(word)
        if parts is not None:
            return parts
        mwl = self.minimum_word_length
        strict = self.strict_mode
        for i in range(len(word) - mwl, mwl - 1, -1):
            left_part = word[:i]
            right_part = word[i:]
            if not strict:
                exception_split = self._get_exception_split_or_none2(right_part, left_part)
                if exception_split is not None:
                    return exception_split
            if self._is_simple_word(right_part):
                left_part_parts = self._split(left_part, True, collect_subwords)
                if left_part_parts is not None:
                    if collect_subwords:
                        if parts is None:
                            parts = []
                        for lpp in left_part_parts:
                            if lpp not in parts:
                                parts.append(lpp)
                        if right_part not in parts:
                            parts.append(right_part)
                        right_part_exceptions = self.exception_splits.get_exception_split_or_none(right_part)
                        if right_part_exceptions is not None:
                            for exception in right_part_exceptions:
                                if exception not in parts:
                                    parts.append(exception)
                    else:
                        parts = list(left_part_parts)
                        parts.append(right_part)
                elif not strict:
                    parts = [left_part, right_part]
            elif not strict:
                if self._is_simple_word(left_part):
                    parts = [left_part, right_part]
        return parts

    def _get_exception_split_or_none2(self, right_part, left_part):
        exception_split = self.exception_splits.get_exception_split_or_none(right_part)
        if exception_split is not None:
            return [left_part] + exception_split
        exception_split2 = self.exception_splits.get_exception_split_or_none(left_part)
        if exception_split2 is not None:
            return exception_split2 + [right_part]
        return None

    def _find_interfix_or_none(self, word):
        lc_word = word.lower()
        for interfix in self.INTERFIXES:
            if lc_word.endswith(interfix):
                return interfix
        return None

    def _ends_with_interfix(self, word):
        for interfix in self.INTERFIXES:
            if word.endswith(interfix):
                return True
        return False

    def _is_simple_word(self, part):
        return len(part) >= self.minimum_word_length and part.lower() in self.words


# GermanCompoundTokenizer.ExtendedGermanWordSplitter.extendedList(): compound
# parts added to the jWordSplitter word list
_EXTENDED_WORDS = (
    'influencer', 'katheterisierung', 'rücklass', 'abdichtung', 'laptop', 'verschattung', 'paradeiser',
    'einreichung', 'bestatter', 'divergenz', 'schrumpf', 'degustation', 'schaft', 'abstreifer', 'aufputz',
    'glühwürmchen', 'aufwertung', 'einhausung', 'lackier', 'zarge', 'pluralisierung', 'schanzen', 'abscheide',
    'rangier', 'temporal', 'kartonage', 'kartonagen', 'rebellion', 'binokular', 'umverlegung', 'umhausung',
    'überholung', 'chloroplasten', 'nachrangigkeit', 'spital', 'turnus', 'teilnehmenden', 'pensionisten',
    'graduierten', 'beladung', 'controller', 'resilienz', 'mitführ', 'trauma', 'abtau', 'normung', 'mikroskopie',
    'bitumen', 'erfolglosigkeit', 'pneumatik', 'anlasser', 'allozierung', 'alphabetisierung', 'aktuator',
    'akademisierung', 'allergiker', 'queer', 'filament', 'querung', 'curling', 'opioid', 'booster', 'schmuse',
    'thrombozyten', 'dysfunktion', 'storchen', 'nasch', 'esperanto', 'passivierung', 'radikalisierung',
    'erleuchtung', 'verwalter', 'verbiss', 'ausleih', 'rutsch', 'kufen', 'entferner', 'debitoren', 'terrakotta',
    'graffiti', 'auffahr', 'anmutung', 'kritzel', 'salami', 'eukalyptus', 'kreativ', 'hochvolt', 'trading',
    'extraktion', 'verstetigung', 'diagonal', 'margen', 'synonym', 'aufbringung', 'robustheit', 'nachuntersuchung',
    'erstkommunion', 'hauptstadt', 'neustart', 'polarisierung', 'vollstreckbarkeit', 'vollziehung', 'kasko',
    'blitzableiter', 'abschattungen', 'kuscheltier', 'gastro', 'hortensien',
)

# the exceptions added by the GermanCompoundTokenizer constructor (in order)
_EXCEPTIONS = (
    ('Absolventen', ['Absolventen']), ('Acetat', ['Acetat']), ('Alkoholabstinenz', ['Alkohol', 'abstinenz']),
    ('Androgen', ['Androgen']), ('Auberginen', ['Auberginen']), ('Auckland', ['Auckland']),
    ('Boston', ['Boston']), ('Brandenburg', ['Brandenburg']), ('Broadcast', ['Broadcast']),
    ('Buchsbaum', ['Buchsbaum']), ('Chiemsee', ['Chiemsee']), ('Coffein', ['Coffein']), ('Drohnen', ['Drohnen']),
    ('Eiben', ['Eiben']), ('Eingroschen', ['Eingroschen']), ('Einkomponenten', ['Einkomponenten']),
    ('Elster', ['Elster']), ('Engineering', ['Engineering']), ('Factoring', ['Factoring']),
    ('Flexodruck', ['Flexo', 'druck']), ('Graviton', ['Graviton']), ('Göttinnen', ['Göttinnen']),
    ('Hallesche', ['Hallesche']), ('Hinspiel', ['Hinspiel']), ('Homogen', ['Homogen']),
    ('Kolleggen', ['Kolleggen']), ('Karstadt', ['Karstadt']), ('Kartier', ['Kartier']),
    ('Kaukasus', ['Kaukasus']), ('Knoblauch', ['Knoblauch']), ('Kollagen', ['Kollagen']),
    ('Kommerz', ['Kommerz']), ('Mentoring', ['Mentoring']), ('Monarchen', ['Monarchen']),
    ('Oligarchen', ['Oligarchen']), ('Optimal', ['Optimal']), ('Saunieren', ['Saunieren']),
    ('Schiessen', ['Schiessen']), ('Spielgeleier', ['Spielgeleier']), ('Halleschen', ['Halleschen']),
    ('Reinigungstab', ['Reinigungs', 'tab']), ('Reinigungstabs', ['Reinigungs', 'tabs']),
    ('Tauschwerte', ['Tausch', 'werte']), ('Tauschwertes', ['Tausch', 'wertes']),
    ('Kinderspielen', ['Kinder', 'spielen']), ('Buchhaltungstrick', ['Buchhaltungs', 'trick']),
    ('Buchhaltungstricks', ['Buchhaltungs', 'tricks']), ('Haushaltstrick', ['Haushalts', 'trick']),
    ('Haushaltstricks', ['Haushalts', 'tricks']), ('Verkaufstrick', ['Verkaufs', 'trick']),
    ('Verkaufstricks', ['Verkaufs', 'tricks']), ('Ablenkungstrick', ['Ablenkungs', 'trick']),
    ('Ablenkungstricks', ['Ablenkungs', 'tricks']), ('Manipulationstrick', ['Manipulations', 'trick']),
    ('Manipulationstricks', ['Manipulations', 'tricks']), ('Erziehungstrick', ['Erziehungs', 'trick']),
    ('Erziehungstricks', ['Erziehungs', 'tricks']), ('Messetage', ['Messe', 'tage']),
    ('Messetagen', ['Messe', 'tagen']), ('karamelligen', ['karamelligen']), ('Häkelnadel', ['Häkel', 'nadel']),
    ('Häkelnadeln', ['Häkel', 'nadeln']), ('Freiberg', ['Freiberg']), ('Abtestat', ['Abtestat']),
    ('Abtestaten', ['Abtestaten']), ('Freibergs', ['Freibergs']), ('Kreuzberg', ['Kreuzberg']),
    ('Kreuzbergs', ['Kreuzbergs']), ('Digitalisierung', ['Digitalisierung']), ('Abtrocknung', ['Abtrocknung']),
    ('Erlösung', ['Erlösung']), ('Feuerung', ['Feuerung']), ('Aktivierung', ['Aktivierung']),
    ('Protokollierung', ['Protokollierung']), ('Budgetierung', ['Budgetierung']), ('Faltung', ['Faltung']),
    ('Anhäufung', ['Anhäufung']), ('Aufkohlung', ['Aufkohlung']), ('Festigung', ['Festigung']),
    ('Allerheiligen', ['Allerheiligen']), ('Druckerpressen', ['Drucker', 'pressen']), ('Habitat', ['Habitat']),
    ('Augarten', ['Augarten']), ('Auszeit', ['Auszeit']), ('Bewegtbild', ['Bewegt', 'bild']),
    ('Bigband', ['Bigband']), ('Bisexuelle', ['Bisexuelle']), ('Bisexuellen', ['Bisexuellen']),
    ('Bunsenbrenner', ['Bunsenbrenner']), ('Carbon', ['Carbon']), ('Carsharing', ['Carsharing']),
    ('Castor', ['Castor']), ('Catering', ['Catering']), ('Cholesterin', ['Cholesterin']), ('Damast', ['Damast']),
    ('Dispositiv', ['Dispositiv']), ('Emittent', ['Emittent']), ('Emittenten', ['Emittenten']),
    ('Express', ['Express']), ('Fairness', ['Fairness']), ('Fiberglas', ['Fiberglas']), ('Globus', ['Globus']),
    ('Göttinnen', ['Göttinnen']), ('Illustration', ['Illustration']), ('Muttertag', ['Muttertag']),
    ('Muttertags', ['Muttertags']), ('Patriarchen', ['Patriarchen']), ('Phosgen', ['Phosgen']),
    ('Vatertag', ['Vatertag']), ('Vatertags', ['Vatertags']), ('Vaterland', ['Vaterland']),
    ('Vaterlands', ['Vaterlands']), ('Wehrmacht', ['Wehrmacht']), ('Wehrmachts', ['Wehrmachts']),
)

_extended_list = None


def extended_list(dictionary_path=None, download=True):
    """ExtendedGermanWordSplitter.extendedList()"""
    global _extended_list
    if _extended_list is None:
        words = set(embedded_german_words(dictionary_path, download))
        words.update(_EXTENDED_WORDS)
        _extended_list = frozenset(words)
    return _extended_list


class GermanCompoundTokenizer:
    """GermanCompoundTokenizer: splits German compound nouns with
    jWordSplitter (the extended word list, interfixes not hidden, minimum
    part length 3, additional exceptions)."""

    def __init__(self, strict_mode=True, dictionary_path=None, download=True):
        ws = GermanWordSplitter(False, extended_list(dictionary_path, download), dictionary_path, download)
        ws.set_strict_mode(strict_mode)
        ws.set_minimum_word_length(3)
        for word, parts in _EXCEPTIONS:
            ws.add_exception(word, parts)
        self.word_splitter = ws

    def tokenize(self, word):
        try:
            return self.word_splitter.split_word(word)
        except InputTooLongException:
            return [word]


_instances = {}


def _instance(strict, dictionary_path, download):
    inst = _instances.get(strict)
    if inst is None:
        with _lock:
            inst = _instances.get(strict)
        if inst is None:
            inst = GermanCompoundTokenizer(strict, dictionary_path, download)
            _instances.setdefault(strict, inst)
            inst = _instances[strict]
    return inst


def get_strict_instance(dictionary_path=None, download=True):
    """GermanCompoundTokenizer.getStrictInstance() (a shared instance)"""
    return _instance(True, dictionary_path, download)


def get_non_strict_instance(dictionary_path=None, download=True):
    """GermanCompoundTokenizer.getNonStrictInstance() (a shared instance)"""
    return _instance(False, dictionary_path, download)
