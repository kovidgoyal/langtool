"""Ports of the helper classes of org.languagetool.rules.uk:
ExtraDictionaryLoader, LemmaHelper, InflectionHelper, VerbInflectionHelper,
CaseGovernmentHelper, SearchHelper and RuleException.

The overloaded Java methods taking lemma collections, single lemmas or lemma
Patterns are one function here: a str is a single lemma, a compiled regex is
a lemma pattern (full match) and anything else a collection of lemmas."""

import functools
import os
import threading

from ... import jregex
from ...language import RESOURCE_DIR, RULES_DIR
from ...rules.abstract_rules import java_hash_set_order
from ...tools import is_digit, is_lower_case, is_upper_case, java_split, java_trim
from . import pos_tag_helper as pth

_lock = threading.Lock()


def _resource(path):
    return os.path.join(RESOURCE_DIR, path.lstrip('/'))


def _resource_lines(path):
    with open(_resource(path), encoding='utf-8', newline='') as f:
        text = f.read()
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def _is_pattern(x):
    return hasattr(x, 'fullmatch')


# --- ExtraDictionaryLoader ---

@functools.lru_cache(maxsize=None)
def _load_set(path):
    return frozenset(line for line in _resource_lines(path) if not line.startswith('#'))


def load_set(path):
    """ExtraDictionaryLoader.loadSet: the lines of a resource file (path like
    /uk/dash_follower.txt) that don't start with #"""
    return set(_load_set(path))


def load_map(path):
    """ExtraDictionaryLoader.loadMap: "key value" lines (the value is empty
    if missing)"""
    out = {}
    for line in _load_set(path):
        x = java_split(java_trim(line), ' ')
        if x[0] in out:
            raise ValueError('Duplicate key %r in %s' % (x[0], path))
        out[x[0]] = x[1] if len(x) > 1 else ''
    return out


def load_spaced_lists(path):
    """ExtraDictionaryLoader.loadSpacedLists"""
    out = {}
    split = jregex.compile(' |\\|')
    comment = jregex.compile('#.*')
    for line in _resource_lines(path):
        if not line.startswith('#') and java_trim(line):
            line = java_trim(comment.sub('', line, count=1))
            parts = split.split(line)
            while len(parts) > 1 and parts[-1] == '':
                parts.pop()
            out[parts[0]] = parts[1:]
    return out


def load_lists(path):
    """ExtraDictionaryLoader.loadLists: word=suggestion1|suggestion2 lines of a
    file in the rules directory (path like /uk/replace_renamed.txt)"""
    out = {}
    split = jregex.compile(' *= *|\\|')
    with open(os.path.join(RULES_DIR, path.lstrip('/')), encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if not line.startswith('#') and java_trim(line):
                parts = split.split(line)
                while len(parts) > 1 and parts[-1] == '':
                    parts.pop()
                out[parts[0]] = parts[1:]
    return out


# --- RuleException ---

class RuleException:
    """Port of org.languagetool.rules.uk.RuleException"""

    none = 'none'
    exception = 'exception'
    skip_type = 'skip'

    __slots__ = ('type', 'skip')

    def __init__(self, type_or_skip):
        if isinstance(type_or_skip, int):
            self.type = RuleException.skip_type
            self.skip = type_or_skip
        else:
            self.type = type_or_skip
            self.skip = 0

    def __repr__(self):
        return 'RuleException(%s, %d)' % (self.type, self.skip)


# --- LemmaHelper ---

_IGNORE_CHARS = '\u00AD\u0301'
CITY_AVENU = {'сіті', 'ситі', 'стріт', 'стрит', 'рівер', 'ривер', 'авеню', 'штрасе', 'штрассе', 'сьоркл', 'сквер',
              'плац'}
MONTH_LEMMAS = ('січень', 'лютий', 'березень', 'квітень', 'травень', 'червень', 'липень', 'серпень', 'вересень',
                'жовтень', 'листопад', 'грудень')
DAYS_OF_WEEK = ('понеділок', 'вівторок', 'середа', 'четвер', "п'ятниця", 'субота', 'неділя')
TIME_LEMMAS = (
    'секунда', 'хвилина', 'хвилинка', 'хвилина-дві', 'хвилинка-друга',
    'година', 'годинка', 'півгодини', 'година-друга', 'година-дві',
    'час', 'день', 'день-другий', 'півдня', 'ніч', 'ніченька', 'вечір', 'ранок', 'тиждень', 'тиждень-два',
    'тиждень-другий',
    'місяць', 'місяць-два', 'місяць-другий', 'місяць-півтора', 'доба', 'мить', 'хвилька',
    'рік', 'рік-два', 'рік-півтора', 'півроку', 'півроку-рік', 'десятиліття', 'десятиріччя', 'століття',
    'півстоліття', 'сторіччя', 'півсторіччя', 'тисячоліття', 'півтисячоліття', 'квартал', 'годочок',
    'літо', 'зима', 'весна', 'осінь',
    'тайм', 'мить', 'період', 'термін', 'сезон', 'декада', 'каденція', 'раунд', 'сезон')
DISTANCE_LEMMAS = (
    'міліметр', 'сантиметр', 'метр', 'кілометр', 'кілограм', 'кілограм–півтора',
    'гектар', 'миля', 'аршин', 'дециметр', 'верства', 'верста',
    'грам', 'літр', 'фунт', 'тонна', 'центнер')
PSEUDO_NUM_LEMMAS = (
    'десяток', 'десяток-другий', 'сотня', 'сотка', 'тисяча', "п'ятірка", 'пара', 'третина', 'чверть', 'половина',
    'дюжина', 'жменя', 'жменька', 'купа', 'купка', 'парочка', 'оберемок', 'безліч')
ADV_QUANT_PATTERN = jregex.compile(
    'більше|менше|чимало|багато|мало|забагато|замало|немало|багатенько|чималенько|стільки|обмаль|вдосталь|удосталь'
    '|трохи|трошки|досить|достатньо|недостатньо|предостатньо'
    '|багацько|чимбільше|побільше|порівну|більшість|трішки|предосить|повно|повнісінько'
    '|мільйон|тисяча|сотня|мільярд|трильйон|десяток|нуль|безліч'
    '|кілька|декілька|пара|парочка|купа|купка|безліч|мінімум|максимум')
MONEY_LEMMAS = ('гривня', 'копійка')
TIME_LEMMAS_SHORT = ('секунда', 'хвилина', 'година', 'рік')
PART_INSERT_PATTERN = jregex.compile(
    'бодай|буцім(то)?|геть|дедалі|десь|іще|ледве|мов(би(то)?)?|навіть|наче(б(то)?)?|неначе(бто)?|немов(би(то)?)?'
    '|ніби(то)?|попросту|просто(-напросто)?|справді|усього-на-всього|хай|хоча?|якраз|ж|би?|власне')
PLUS_MINUS = {'плюс', 'мінус', 'максимум', 'мінімум'}

TIME_PLUS_LEMMAS = set(TIME_LEMMAS) | set(DISTANCE_LEMMAS) | set(DAYS_OF_WEEK) | set(MONTH_LEMMAS) | \
    set(PSEUDO_NUM_LEMMAS) | set(MONEY_LEMMAS) | {'вихідний', 'уїк-енд', 'уїкенд', 'вікенд', 'відсоток', 'раз', 'крок'}
# only used with matches(), the order of the alternatives doesn't matter
TIME_PLUS_LEMMAS_PATTERN = jregex.compile('|'.join(sorted(TIME_PLUS_LEMMAS)))


def _readings(atr):
    return atr.readings if hasattr(atr, 'readings') else atr


def has_lemma(atr, lemmas):
    """hasLemma(AnalyzedTokenReadings|List<AnalyzedToken>, Collection<String>|
    String|Pattern)"""
    rs = _readings(atr)
    if isinstance(lemmas, str):
        for r in rs:
            if lemmas == r.lemma:
                return True
        return False
    if _is_pattern(lemmas):
        for r in rs:
            if r.lemma is not None and lemmas.fullmatch(r.lemma):
                return True
        return False
    for r in rs:
        if r.lemma is not None and r.lemma in lemmas:
            return True
    return False


def has_lemma_part_pos(atr, lemmas, part_pos):
    """hasLemma(AnalyzedTokenReadings, List<String> lemmas, String partPos)"""
    for r in atr.readings:
        for lemma in lemmas:
            if lemma == r.lemma and r.pos_tag is not None and part_pos in r.pos_tag:
                return True
    return False


def has_lemma_pos(atr, lemmas, pos_regex):
    """hasLemma(AnalyzedTokenReadings, Collection<String> lemmas, Pattern
    posRegex) and hasLemma(AnalyzedTokenReadings, Pattern lemma, Pattern
    posTagRegex)"""
    pos_regex = pth._p(pos_regex)
    if _is_pattern(lemmas):
        for r in atr.readings:
            lemma = r.lemma
            if lemma is not None and lemmas.fullmatch(lemma) and pos_regex is not None \
                    and r.pos_tag is not None and pos_regex.fullmatch(r.pos_tag):
                return True
        return False
    if not atr.has_reading():
        return False
    for r in atr.readings:
        if r.pos_tag is not None and pos_regex.fullmatch(r.pos_tag):
            if r.lemma in lemmas:
                return True
    return False


def has_lemma_base(atr, lemmas, pos_regex):
    pos_regex = pth._p(pos_regex)
    if not atr.has_reading():
        return False
    for r in atr.readings:
        if r.pos_tag is not None and pos_regex.fullmatch(r.pos_tag):
            lemma = r.lemma
            if lemma in lemmas:
                return True
            idx = lemma.find('-')
            if 2 < idx < len(lemma) - 1 and lemma[:idx] in lemmas:
                return True
    return False


def reverse_search(tokens, pos, depth, lemma, postag):
    return reverse_search_idx(tokens, pos, depth, lemma, postag) >= 0


def reverse_search_idx(tokens, pos, depth, lemma, postag):
    i = pos
    while i > pos - depth and i >= 0:
        if (lemma is None or has_lemma(tokens[i], lemma)) and (postag is None or pth.has_pos_tag(tokens[i], postag)):
            return i
        i -= 1
    return -1


def forward_lemma_search_idx(tokens, pos, depth, lemma, postag):
    i = pos
    while i < pos + depth and i < len(tokens):
        if (lemma is None or has_lemma(tokens[i], lemma)) and (postag is None or pth.has_pos_tag(tokens[i], postag)):
            return i
        i += 1
    return -1


def forward_pos_tag_search(tokens, pos, pos_tag, max_skip):
    i = pos
    while i < len(tokens) and i <= pos + max_skip:
        if pth.has_pos_tag_part(tokens[i], pos_tag):
            return True
        i += 1
    return False


FORWARD = 'FORWARD'
REVERSE = 'REVERSE'

_QUOTES = jregex.compile('[«»„““]')


def token_search(tokens, pos, pos_tag, token, pos_tags_to_ignore, direction):
    """tokenSearch(tokens, pos, String posTag (part) | Pattern posTag, Pattern
    token, Pattern posTagsToIgnore, Dir dir)"""
    step = 1 if direction == FORWARD else -1
    is_part = isinstance(pos_tag, str)
    i = pos
    while 0 < i < len(tokens):
        cur = tokens[i]
        if pos_tag is None:
            ok = True
        elif is_part:
            ok = pth.has_pos_tag_part(cur, pos_tag)
        else:
            ok = pth.has_pos_tag(cur, pos_tag)
        if ok and (token is None or token.fullmatch(cur.get_clean_token())):
            return i
        if pos_tags_to_ignore is not None:
            if not pth.has_pos_tag(cur, pos_tags_to_ignore) and not _QUOTES.fullmatch(cur.get_clean_token()):
                break
        i += step
    return -1


def rev_search(tokens, start_pos, lemma, postag_regex):
    return rev_search_idx(tokens, start_pos, lemma, postag_regex) != -1


def rev_search_idx(tokens, start_pos, lemma, postag_regex):
    if start_pos > 0 and pth.has_pos_tag(tokens[start_pos], 'part.*'):
        start_pos -= 1
    if start_pos > 0 and pth.has_pos_tag(tokens[start_pos], 'adv(:.*)?|.*pron.*'):
        start_pos -= 1
    if start_pos > 0 and pth.has_pos_tag(tokens[start_pos], 'part.*'):
        start_pos -= 1
    if start_pos > 0:
        if lemma is not None and not has_lemma(tokens[start_pos], lemma):
            return -1
        if postag_regex is not None and not pth.has_pos_tag(tokens[start_pos], postag_regex):
            return -1
        return start_pos
    return -1


def _chars(word):
    """The chars of a string for Character.isUpperCase(char) etc.: the
    surrogates of supplementary characters are neither upper nor lower
    case (None here)"""
    return (c if ord(c) < 0x10000 else None for c in word)


def is_all_uppercase_uk(word):
    for ch in _chars(word):
        if ch is None or (ch not in "-\u2013'\u0301\u00AD" and not is_upper_case(ch)):
            return False
    return True


def is_all_lowercase_uk(word):
    for ch in _chars(word):
        if ch is None or (ch not in "-\u2013'\u0301\u00AD" and not is_lower_case(ch)):
            return False
    return True


def _char_upper(ch):
    u = ch.upper()
    return u if len(u) == 1 else ch


def _char_lower(ch):
    lo = ch.lower()
    return lo if len(lo) == 1 else ch


def capitalize_proper_name(word):
    out = []
    prev = '-'
    for ch in word:
        out.append(_char_upper(ch) if prev == '-' else _char_lower(ch))
        prev = '-' if ch == '–' else ch
    return ''.join(out)


def is_capitalized(word):
    if word is None or len(word) < 2:
        return False
    char0 = word[0]
    if not is_upper_case(char0):
        return False
    # lax on Latin: EuroGas
    if 'A' <= char0 <= 'Z' and is_lower_case(word[1]):
        return True
    prev_dash = False
    sz = len(word)
    for i in range(1, sz):
        ch = word[i]
        if ch in _IGNORE_CHARS:
            continue
        dash = ch == '-' or ch == '–'
        if dash:
            if i == sz - 2 and is_digit(word[i + 1]):
                return True
            prev_dash = dash
            continue
        if ch != "'" and ch != '\u0301' and ch != '\u00AD' and prev_dash != is_upper_case(ch):
            return False
        prev_dash = False
    return True


DASHES_PATTERN = jregex.compile('[‐-―-]')
QUOTES_PATTERN = jregex.compile('[\\p{Pi}\\p{Pf}]')
_INITIAL = jregex.compile('[А-ЯІЇЄҐA-Z]\\.')


def is_possibly_proper_noun(atr):
    return is_capitalized(atr.get_clean_token())


def is_initial(atr):
    t = atr.get_clean_token()
    return t.endswith('.') and _INITIAL.fullmatch(t) is not None


def is_dash(atr):
    t = atr.get_clean_token()
    return t is not None and DASHES_PATTERN.fullmatch(t) is not None


# --- InflectionHelper ---

GEN_ORDER = {'m': 0, 'f': 1, 'n': 3, 's': 4, 'p': 5, 'i': 6, 'o': 7}
VIDM_ORDER = {'v_naz': 10, 'v_rod': 20, 'v_dav': 30, 'v_zna': 40, 'v_oru': 50, 'v_mis': 60, 'v_kly': 70}

ADJ_INFLECTION_PATTERN = jregex.compile(':([mfnp]):(v_...)(:r(in)?anim)?')
NOUN_INFLECTION_PATTERN = jregex.compile('((?:[iu]n)?anim):([mfnps]):(v_...)')
_MFN = ('m', 'f', 'n')


class Inflection:
    """Port of InflectionHelper.Inflection: gender, case (v_...) and
    animacy. Note that equals() is not symmetric/transitive in Java either;
    use contains()/disjoint() with Java semantics (o.equals(element))."""

    __slots__ = ('gender', 'case', 'anim_tag')

    def __init__(self, gender, case, anim_tag):
        self.gender = gender
        self.case = case
        self.anim_tag = anim_tag

    def __hash__(self):
        # the Java hashCode() (case and gender only)
        result = 1
        result = 31 * result + (0 if self.case is None else hash(self.case))
        return 31 * result + (0 if self.gender is None else hash(self.gender))

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Inflection):
            return False
        return (_gender_equals(self.gender, other.gender) and self.case == other.case and
                (self.anim_tag is None or other.anim_tag is None or not self.anim_matters() or
                 not other._is_animal_sensitive() or self.anim_tag == other.anim_tag))

    def equals_ignore_gender(self, other):
        return self.case == other.case and (self.anim_tag is None or other.anim_tag is None or
                                            not self.anim_matters() or self.anim_tag == other.anim_tag)

    def anim_matters(self):
        return (self.anim_tag is not None and self.anim_tag != 'unanim' and self.case == 'v_zna' and
                self._is_animal_sensitive())

    def _is_animal_sensitive(self):
        return self.gender in 'mp'

    def __str__(self):
        return ':' + self.gender + ':' + self.case + ('_' + self.anim_tag if self.anim_matters() else '')

    __repr__ = __str__

    def sort_key(self):
        return (GEN_ORDER[self.gender], VIDM_ORDER[self.case])

    def __lt__(self, o):
        return self.sort_key() < o.sort_key()


def _gender_equals(g1, g2):
    if g1 == g2:
        return True
    return (g1 == 's' and g2 in _MFN) or (g2 == 's' and g1 in _MFN)


def java_contains(items, o):
    """Collection.contains(o): o.equals(element) (for the non symmetric
    equals of the inflections)"""
    for e in items:
        if o == e:
            return True
    return False


def java_disjoint(c1, c2):
    """Collections.disjoint(c1, c2) for lists (not sets): returns True if
    one is empty, iterates over the smaller one (c1 if the sizes are
    equal) and checks other.contains(e), i.e. e.equals(element of other)"""
    if not c1 or not c2:
        return True
    iterate, contains = (c2, c1) if len(c1) > len(c2) else (c1, c2)
    for e in iterate:
        if java_contains(contains, e):
            return False
    return True


def java_retain_all(c1, c2):
    """c1.retainAll(c2) for lists: keeps the elements e of c1 for which
    c2.contains(e)"""
    c1[:] = [e for e in c1 if java_contains(c2, e)]
    return c1


def get_adj_inflections(adj_token_readings, postag_start='adj'):
    out = []
    for token in adj_token_readings:
        pos_tag = token.pos_tag
        if pos_tag is None or not pos_tag.startswith(postag_start):
            continue
        m = ADJ_INFLECTION_PATTERN.search(pos_tag)
        gen = m.group(1)
        vidm = m.group(2)
        anim_tag = m.group(3)[2:] if m.group(3) is not None else None
        infl = Inflection(gen, vidm, anim_tag)
        if not java_contains(out, infl):
            out.append(infl)
    return out


def get_numr_inflections(adj_token_readings):
    return get_adj_inflections(adj_token_readings, 'numr')


def get_noun_inflections(noun_token_readings, ignore_tag=None):
    out = []
    for token in noun_token_readings:
        pos_tag = token.pos_tag
        if pos_tag is None:
            continue
        if ignore_tag is not None and ignore_tag.search(pos_tag):
            continue
        m = NOUN_INFLECTION_PATTERN.search(pos_tag)
        if not m:
            continue
        infl = Inflection(m.group(2), m.group(3), m.group(1))
        if not java_contains(out, infl):
            out.append(infl)
    return out


# --- VerbInflectionHelper ---

_VERB_INFLECTION_PATTERN = jregex.compile(':([mfnps])(:([123])?|$)')
_VERB_NOUN_INFLECTION_PATTERN = jregex.compile('(?::((?:[iu]n)?anim))?:([mfnps]):(v_naz)')
_VERB_ADJ_INFLECTION_PATTERN = jregex.compile('(adj|numr):([mfnps]):(v_naz)')
_NOUN_PERSON_PATTERN = jregex.compile(':([123])')


class VerbInflection:
    """Port of VerbInflectionHelper.Inflection"""

    __slots__ = ('gender', 'plural', 'person')

    def __init__(self, gender, person):
        if gender in ('s', 'p'):
            self.gender = None
            self.plural = gender
        elif gender == 'i':
            self.gender = gender
            self.plural = gender
        else:
            self.gender = gender
            self.plural = 's'
        self.person = person

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, VerbInflection):
            return False
        if self.person is not None and other.person is not None and self.person != other.person:
            return False
        if self.gender is not None and other.gender is not None and self.gender != other.gender:
            return False
        return self.plural == other.plural

    def __hash__(self):
        return hash((self.gender, self.plural, self.person))

    def __str__(self):
        return 'Gender: %s/%s/%s' % (_jstr(self.gender), _jstr(self.plural), _jstr(self.person))

    __repr__ = __str__

    def sort_key(self):
        return GEN_ORDER[self.gender] if self.gender is not None else 0

    def __lt__(self, o):
        return self.sort_key() < o.sort_key()


def _jstr(s):
    return 'null' if s is None else s


def get_verb_inflections(token_readings):
    out = []
    for token in token_readings:
        pos_tag = token.pos_tag
        if pos_tag is None or not pos_tag.startswith('verb'):
            continue
        if ':inf' in pos_tag:
            out.append(VerbInflection('i', None))
            continue
        if ':impers' in pos_tag:
            out.append(VerbInflection('o', None))
            continue
        m = _VERB_INFLECTION_PATTERN.search(pos_tag)
        out.append(VerbInflection(m.group(1), m.group(3)))
    return out


def get_verb_noun_inflections(noun_token_readings):
    """VerbInflectionHelper.getNounInflections"""
    out = []
    for token in noun_token_readings:
        pos_tag = token.pos_tag
        if pos_tag is None:
            continue
        m = _VERB_NOUN_INFLECTION_PATTERN.search(pos_tag)
        if not m:
            continue
        mp = _NOUN_PERSON_PATTERN.search(pos_tag)
        out.append(VerbInflection(m.group(2), mp.group(1) if mp else None))
    return out


def get_verb_adj_inflections(token_readings):
    """VerbInflectionHelper.getAdjInflections"""
    out = []
    for token in token_readings:
        pos_tag = token.pos_tag
        if pos_tag is None:
            continue
        m = _VERB_ADJ_INFLECTION_PATTERN.search(pos_tag)
        if not m:
            continue
        mp = _NOUN_PERSON_PATTERN.search(pos_tag)
        out.append(VerbInflection(m.group(2), mp.group(1) if mp else None))
    return out


def verb_inflections_overlap(verb_token_readings, noun_token_readings):
    """VerbInflectionHelper.inflectionsOverlap"""
    return not java_disjoint(get_verb_inflections(verb_token_readings),
                             get_verb_noun_inflections(noun_token_readings))


# --- CaseGovernmentHelper ---

class _JavaSet:
    """A java.util.LinkedHashSet (linked=True) or HashSet of strings with
    the Java iteration order"""

    __slots__ = ('items', 'linked')

    def __init__(self, items=(), linked=True):
        self.items = dict.fromkeys(items)
        self.linked = linked

    def add(self, x):
        self.items[x] = None

    def update(self, xs):
        for x in xs:
            self.items[x] = None

    def discard(self, x):
        self.items.pop(x, None)

    def __contains__(self, x):
        return x in self.items

    def __iter__(self):
        if self.linked:
            return iter(list(self.items))
        return iter(java_hash_set_order(list(self.items)))

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return '[' + ', '.join(self) + ']'


def _load_case_map(path):
    out = {}
    for line in _resource_lines(path):
        parts = java_split(line, ' ')
        vidm = java_split(parts[1], ':')
        if parts[0] in out:
            out[parts[0]].update(vidm)
        else:
            out[parts[0]] = _JavaSet(vidm)
    return out


@functools.lru_cache(maxsize=None)
def _case_maps():
    case_government_map = _load_case_map('/uk/case_government.txt')
    derivatives_map = _load_case_map('/uk/derivats.txt')
    case_government_map['згідно з'] = _JavaSet(['v_oru'], linked=False)
    for key, verbs in derivatives_map.items():
        s = _JavaSet(linked=False)
        case_government_map[key] = s
        for verb in verbs:
            rvs = case_government_map.get(verb)
            if rvs is not None:
                s.update(rvs)
    return case_government_map, derivatives_map


def case_government_map():
    return _case_maps()[0]


def derivatives_map():
    return _case_maps()[1]


def has_case_government(atr, start_pos_tag, rv_case=None):
    """hasCaseGovernment(atr, rvCase) / hasCaseGovernment(atr, Pattern
    startPosTag, rvCase)"""
    if rv_case is None:
        start_pos_tag, rv_case = None, start_pos_tag
    return rv_case in get_case_governments(atr, start_pos_tag)


def get_case_governments(atr, pos_tag):
    """getCaseGovernments(atr, String startPosTag) for a str pos_tag,
    getCaseGovernments(atr, Pattern posTag) for a compiled pattern or None"""
    cgm = case_government_map()
    out = _JavaSet()
    out.update(_get_custom_govs(atr))
    if isinstance(pos_tag, str):
        start_pos_tag = pos_tag
        if start_pos_tag == 'verb' and pth.has_pos_tag_start(atr.readings[0], 'advp'):
            start_pos_tag = 'advp'
        for token in atr.readings:
            t = token.pos_tag
            if not token.has_no_tag() and (t is not None and t.startswith(start_pos_tag) or
                                           (start_pos_tag == 'prep' and t is not None and t == '<prep>')) \
                    and token.lemma in cgm:
                rv_list = cgm[token.lemma]
                out.update(rv_list)
                if 'adjp:pasv' in t:
                    rv_list.add('v_oru')
        return out
    for token in atr.readings:
        if token.has_no_tag():
            continue
        t = token.pos_tag
        if pos_tag is None or (t is not None and pos_tag.fullmatch(t)):
            v_lemma = token.lemma
            if v_lemma not in cgm:
                if t is not None and t.startswith('advp'):
                    v_lemma = _get_advp_verb_lemma(token)
            if v_lemma in cgm:
                out.update(cgm[v_lemma])
        if pth.has_pos_tag_part(token, 'adjp:pasv'):
            out.add('v_oru')
    return out


_MATY_TAG = jregex.compile('verb:imperf:(futr|past|pres).*')
_BUTY_TAG = jregex.compile('verb:imperf:(futr|past:n|pres:s:3).*')
_INF_VERBS = ('вимагатися', 'випадати', 'випасти', 'личити', 'належати', 'тягнути', 'щастити',
              'плануватися', 'рекомендуватися', 'пропонуватися', 'сподобатися', 'плануватися', 'прийтися',
              'удатися', 'годитися', 'доводитися')
_INF_VERBS_TAG = jregex.compile('verb.*(pres:s:3|futr:s:3|past:n).*')
_NALEZHYT_TAG = jregex.compile('verb:imperf:inf.*')
_BILSHATY = jregex.compile('(по)?більшати|(по)?меншати')
_BILSHATY_TAG = jregex.compile('verb.*(inf|pres:s:3|futr:s:3|past:n).*')


def _get_custom_govs(atr):
    out = []
    if has_lemma_pos(atr, ('мати',), _MATY_TAG):
        out.append('v_inf')
    elif has_lemma_pos(atr, ('бути',), _BUTY_TAG):
        out.append('v_inf')
    elif has_lemma_pos(atr, _INF_VERBS, _INF_VERBS_TAG):
        out.append('v_inf')
    elif has_lemma_pos(atr, ('належить',), _NALEZHYT_TAG):
        out.append('v_inf')
    elif has_lemma_pos(atr, _BILSHATY, _BILSHATY_TAG):
        out.append('v_rod')
    return out


_ADVP1 = jregex.compile('лячи(с[яь])?')
_ADVP2 = jregex.compile('(ючи|вши)(с[яь])?')


def _get_advp_verb_lemma(token):
    v_lemma = token.lemma
    if v_lemma == 'даючи':
        return 'давати'
    if v_lemma == 'змушуючи':
        return 'змушувати'
    v_lemma = jregex.java_replace(_ADVP1, 'ити$1', token.lemma, 1)
    return jregex.java_replace(_ADVP2, 'ти$2', v_lemma, 1)


USED_U_INSTEAD_OF_A_MSG = ('. Можливо, вжито невнормований родовий відмінок ч.р. з закінченням -у/-ю замість -а/-я '
                           '(така тенденція є в сучасній мові)?')


# --- SearchHelper ---

_WHITESPACE = jregex.compile('\\s')
_INSERT_LEMMAS = ('зокрема', 'відповідно')


class Condition:
    """Port of SearchHelper.Condition"""

    def __init__(self, lemma=None, postag=None):
        self.lemma_p = pth._p(lemma) if lemma is not None else None
        self.postag_p = pth._p(postag) if postag is not None else None
        self.token_pattern = None
        self.token_str = None
        self._negate = False

    @staticmethod
    def postag(pattern):
        return Condition(postag=pattern)

    @staticmethod
    def lemma(pattern):
        return Condition(lemma=pattern)

    @staticmethod
    def token(token):
        """Condition.token(Pattern) for a compiled pattern, Condition.token(
        String) (case insensitive equality) for a str"""
        c = Condition()
        if isinstance(token, str):
            c.token_str = token
        else:
            c.token_pattern = token
        return c

    def negate(self):
        self._negate = True
        return self

    def matches(self, atr, context=None):
        from ...tools import java_equals_ignore_case
        r = ((self.postag_p is None or pth.has_pos_tag(atr, self.postag_p)) and
             (self.lemma_p is None or has_lemma(atr, self.lemma_p)) and
             (self.token_pattern is None or self.token_pattern.fullmatch(atr.get_clean_token()) is not None) and
             (self.token_str is None or java_equals_ignore_case(self.token_str, atr.get_clean_token())))
        return self._negate != bool(r)

    def __repr__(self):
        return 'Condition [postag=%s, lemma=%s, token=%s, tokenStr=%s]' % (
            self.postag_p, self.lemma_p, self.token_pattern, self.token_str)


class Match:
    """Port of SearchHelper.Match"""

    def __init__(self):
        self.ignore_quotes = True
        self._ignore_inserts = False
        self.targets = None
        self._limit = -1
        self.skips = []

    def token_line(self, token_line):
        self.targets = [Condition.token(s) for s in _WHITESPACE.split(token_line.replace(',', ' ,'))]
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def ignore_inserts(self):
        self._ignore_inserts = True
        return self

    def skip(self, *conditions):
        self.skips = list(conditions)
        return self

    def target(self, *conditions):
        self.targets = list(conditions)
        return self

    def m_before(self, tokens, pos):
        found_first = False
        logical_distance = 0
        i_cond = len(self.targets) - 1
        while i_cond >= 0:
            if pos - 1 < i_cond:
                return -1
            if self._limit > 0 and logical_distance > self._limit:
                return -1
            logical_distance += 1
            current = tokens[pos]
            if self.ignore_quotes and QUOTES_PATTERN.fullmatch(current.token):
                pos -= 1
                continue
            if self._is_insert(tokens, pos, -1):
                pos -= 2
                pos -= 1
                continue
            if self._ignore_inserts and tokens[pos].token == ')':
                # (the Java loop's "continue" only continues the inner loop)
                for i in range(pos - 1, 0, -1):
                    if tokens[i].token == '(':
                        pos = i
            if not self.targets[i_cond].matches(current, (tokens, pos)):
                if found_first:
                    return -1
                if not self._can_skip(current, (tokens, pos)):
                    return -1
                pos -= 1
                continue
            found_first = True
            i_cond -= 1
            pos -= 1
        return pos + 1

    def m_after(self, tokens, pos):
        found_first = False
        logical_distance = 0
        i_cond = 0
        n = len(self.targets)
        while i_cond < n:
            if pos + n - i_cond > len(tokens):
                return -1
            if self._limit > 0 and logical_distance > self._limit:
                return -1
            logical_distance += 1
            current = tokens[pos]
            if self.ignore_quotes and QUOTES_PATTERN.fullmatch(current.token):
                pos += 1
                continue
            if self._is_insert(tokens, pos, 1):
                pos += 2
                pos += 1
                continue
            if self._ignore_inserts and tokens[pos].token == '(':
                for i in range(pos + 1, len(tokens)):
                    if tokens[i].token == ')':
                        pos = i
            if not self.targets[i_cond].matches(current, (tokens, pos)):
                if found_first:
                    return -1
                if not self._can_skip(current, (tokens, pos)):
                    return -1
                pos += 1
                continue
            found_first = True
            i_cond += 1
            pos += 1
        return pos - 1

    def m_now(self, tokens, pos):
        return self.limit(0).m_after(tokens, pos)

    def _can_skip(self, current, context):
        return not self.skips or any(s.matches(current, context) for s in self.skips)

    def _is_insert(self, tokens, pos, d):
        return (self._ignore_inserts and
                (pos + 3 < len(tokens) if d > 0 else pos - 3 > 0) and
                tokens[pos].token == ',' and tokens[pos + 2 * d].token == ',' and
                (pth.has_pos_tag_part(tokens[pos + d], 'insert') or has_lemma(tokens[pos + d], _INSERT_LEMMAS)))
