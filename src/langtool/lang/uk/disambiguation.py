"""Port of org.languagetool.tagging.disambiguation.uk:
UkrainianHybridDisambiguator, SimpleDisambiguator and
UkrainianMultiwordChunker.

Note on iteration while removing readings: Java's getReadings() returns a
view of the readings array at the time of the call (removeReading() replaces
the array), here the readings list (remove_reading() replaces the list) -
the same snapshot semantics. The Iterable of AnalyzedTokenReadings however
iterates over the current array by index (removing readings while iterating
skips elements), that is emulated by _live_readings()."""

import functools
import threading

from ... import jregex
from ...analysis import PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME, AnalyzedToken, AnalyzedTokenReadings
from ...disambiguation import MultiWordChunker2
from ...tools import is_lower_case, is_upper_case, java_split, java_trim
from . import helpers as lh
from . import pos_tag_helper as pth

_c = jregex.compile


def _live_readings(atr):
    """for (AnalyzedToken t : atr): iterates by index over the current
    readings"""
    i = 0
    while i < len(atr.readings):
        yield atr.readings[i]
        i += 1


def _is_all_lower_case(s):
    """StringUtils.isAllLowerCase"""
    return bool(s) and all(is_lower_case(c) for c in s)


def _is_all_upper_case(s):
    """StringUtils.isAllUpperCase"""
    return bool(s) and all(is_upper_case(c) for c in s)


# --- SimpleDisambiguator ---

class _MatcherEntry:
    __slots__ = ('lemma', 'tag_regex')

    def __init__(self, lemma, tag_regex):
        self.lemma = lemma
        self.tag_regex = _c(tag_regex)

    def matches(self, analyzed_token):
        return ((self.lemma == '*' or self.lemma == analyzed_token.lemma) and not analyzed_token.has_no_tag()
                and self.tag_regex.fullmatch(analyzed_token.pos_tag) is not None)

    def __repr__(self):
        return 'MatcherEntry [lemma=%s, tagRegex=%s]' % (self.lemma, self.tag_regex.pattern)


class _TokenMatcher:
    __slots__ = ('matchers',)

    def __init__(self, matchers):
        self.matchers = matchers

    def matches(self, analyzed_token):
        for m in self.matchers:
            if m.matches(analyzed_token):
                return True
        return False


_COMMENT = _c(' *#.*')


def _data_lines(path):
    for line in lh._resource_lines(path):
        if line.startswith('#') or not java_trim(line):
            continue
        yield jregex.java_replace(_COMMENT, '', line, 1)


@functools.lru_cache(maxsize=None)
def _disambig_remove_map():
    result = {}
    for line in _data_lines('/uk/disambig_remove.txt'):
        line = java_trim(line)
        idx = line.find(' ')
        parts = [line] if idx < 0 else [line[:idx], line[idx + 1:]]
        entries = []
        for s in java_split(parts[1], '|'):
            mp = java_split(s, ' ')
            entries.append(_MatcherEntry(mp[0], mp[1]))
        result[parts[0]] = _TokenMatcher(entries)
    return result


@functools.lru_cache(maxsize=None)
def _disambig_dups_map():
    result = {}
    for line in _data_lines('/uk/disambig_dups.txt'):
        parts = java_split(java_trim(line), ' ')
        result[parts[0]] = parts[1:]
    return result


class SimpleDisambiguator:
    """Port of SimpleDisambiguator: removes rare forms (disambig_remove.txt)
    and readings of duplicate lemmas (disambig_dups.txt)"""

    _PATTERN = _c('.*-(то|от|таки|бо|но)')

    def __init__(self):
        self.disambig_remove_map = _disambig_remove_map()
        self.disambig_dups_map = _disambig_dups_map()

    def remove_rare_forms(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        for i in range(1, len(tokens)):
            token = tokens[i].get_clean_token()
            if not token:
                continue
            if is_lower_case(token[0]):
                token = token.lower()
            token_matcher = self.disambig_remove_map.get(token)
            if token_matcher is None:
                token_matcher = self.disambig_remove_map.get(token.lower())
                if token_matcher is None:
                    idx = token.rfind('-')
                    if idx > 0 and self._PATTERN.fullmatch(token):
                        token_matcher = self.disambig_remove_map.get(token[:idx])

            analyzed_tokens = tokens[i].readings
            if token_matcher is not None:
                for j in range(len(analyzed_tokens) - 1, -1, -1):
                    at = analyzed_tokens[j]
                    if token_matcher.matches(at):
                        tokens[i].remove_reading(at, 'dis_remove_rare')

            # dups
            lemmas = {t.lemma for t in analyzed_tokens if t.lemma is not None}
            lemmas &= self.disambig_dups_map.keys()
            if lemmas:
                to_remove = set()
                for lemma in lemmas:
                    to_remove.update(self.disambig_dups_map[lemma])
                for j in range(len(analyzed_tokens) - 1, -1, -1):
                    at = analyzed_tokens[j]
                    if at.lemma in to_remove:
                        tokens[i].remove_reading(at, 'dis_remove_dups')


# --- UkrainianMultiwordChunker ---

class UkrainianMultiwordChunker(MultiWordChunker2):
    """MultiWordChunker2 where an entry token starting with "/" is a POS tag
    regex"""

    def matches(self, match_text, atr):
        if not match_text.startswith('/'):
            return super().matches(match_text, atr)
        return pth.has_pos_tag(atr, _c(match_text[1:]))


# --- UkrainianHybridDisambiguator ---

_LAST_NAME_TAG = ':prop:lname'
_INITIAL_REGEX = _c('[А-ЯІЇЄҐ]\\.')
_INANIM_VKLY = _c('noun:inanim:.:v_kly.*')
_PLURAL_NAME = _c('noun:anim:p:.*:fname.*')
_PLURAL_LNAME_PATTERN = _c('noun:anim:p:.*:[lp]name.*')
_ST_ABBR = 'ст.'
_LATIN_DIGITS_PATTERN = _c('[XIVХІ]+([–—-][XIVХІ]+)?')
_DIGITS_PATTERN = _c('[0-9]+([–—-][0-9]+)?')
_STATION_NAME_PATTERN = _c("метро|[А-Я][а-яіїєґ'-]+")
_PATTERN_1 = _c('[а-яіїєґa-z0-9].*')
_PATTERN_2 = _c('[0-9]+([.,–—-][0-9]+)?')
_PATTERN_3 = _c('два|дві|три|чотири')
_PATTERN_4 = _c(':(alt|nv|up\\d{2}|xp\\d)')
_PATTERN_5 = _c(':[mfn]:v_rod')

_ADJ_PRON = _c('adj.*pron.*')
_YIH = _c('їх|його|її')
_YIH_NEXT_LEMMAS = _c(
    'кількість|розгляд|обговорення|використання|реалізація|виконання|звільнення|виробництво|застосування|проведення'
    '|утримання|вирішення|загибель|аналоги|однолітки|перелік|затримання|створення|розміщення|лікування|втілення|арешт'
    '|формування|наявність|збереження')
_NONINFL_PREDIC = _c('noninfl:predic.*')
_ADJ_NOUN = _c('(adj|noun).*')
_OBOH = _c('обох|ніхто|ніщо')
_PERS_OR_PREP = _c('.*pron:pers.*|prep.*')
_I_Z = _c('і?з')
_NE = _c('н[еі]')
_VERB = _c('verb.*')
_VERB_ADVP = _c('(verb|advp).*')
_ADV_PREP = _c('(adv|prep).*')
_PUNCT_DASH = _c('[,.;–—-]')
_VERB_INF = _c('(verb).*:inf.*')
_VERB_IMPR = _c('verb.*impr.*')
_NOUN = _c('noun.*')
_ADJ = _c('adj.*')
_V_ZNA_VAR = _c('v_zna:var')
_IGNORE_IN_PRON_POS = _c('pron|noun:anim:p:v_zna.*:rare.*')
_ADJ_PRON_POS = _c('adj.*pron:pos.*')
_CAP_LEMMA = _c("[А-ЯІЇЄҐ][а-яіїєґ'-].*")
_PROP = _c('.*?:prop')
_PUNCT_AFTER_KLY_PATTERN = _c('[!?,»"“”…]|[\\.!?]{2,3}')
_INANIM_VKLY_NOT_GEO = _c('noun:inanim:.:v_kly(?!.*:geo).*')
_LIKELY_V_KLY = ('суде', 'роде', 'заходе', 'місяченьку', 'редакціє')
_XP3 = _c('noun.*:xp3.*')
_NOT_XP3 = _c('(?!.*:xp3).*')
_PROP_ROD = _c('noun:.*:[fmn]:v_rod.*prop.*')

_FEM_PREFIX = ('пані', 'місіс', 'місис', 'міс', 'леді', 'княгиня', 'німкеня')
_MASC_PREFIX = ('пан', 'містер', 'м-р', 'сер', 'князь', 'німець', 'поляк')


@functools.lru_cache(maxsize=None)
def _v_mis_preps():
    cgm = lh.case_government_map()
    s = {k for k, v in cgm.items() if 'v_mis' in v}
    # add Latin y/B - often used instead of real prep
    # we'll catch it in MixedAlphabetsRule
    s.add('y')
    s.add('B')
    return frozenset(s)


def _remove_readings(main_token, pos_tag, label):
    for at in main_token.readings:
        if pth.has_pos_tag(at, pos_tag):
            main_token.remove_reading(at, label)


def _remove_tokens_without(readings, pattern):
    analyzed_tokens = readings.readings
    for j in range(len(analyzed_tokens) - 1, -1, -1):
        at = analyzed_tokens[j]
        if at.pos_tag != SENTENCE_END_TAGNAME and not pth.has_pos_tag(at, pattern):
            readings.remove_reading(at, 'UkranianHybridDisambiguator')


def _get_initial_readings(initials_readings, lname_tokens, initial_type):
    new_tokens = []
    for lname_token in lname_tokens.readings:
        t = lname_token.pos_tag
        if t is None or _LAST_NAME_TAG not in t:
            continue
        t = _PATTERN_4.sub('', t)
        initials_token = initials_readings.readings[0].token
        nt = AnalyzedToken(initials_token, t.replace(_LAST_NAME_TAG, ':nv:abbr:prop:' + initial_type), initials_token)
        nt.whitespace_before = initials_readings.whitespace_before
        new_tokens.append(nt)
    return AnalyzedTokenReadings(new_tokens, initials_readings.start_pos)


def _is_initial(tokens, pos):
    t = tokens[pos].token
    return t.endswith('.') and _INITIAL_REGEX.fullmatch(t) is not None


def _check_for_initial_retag(last_name, initials_idxs, tokens):
    if last_name is not None and len(initials_idxs) in (1, 2):
        fname_pos = initials_idxs[0]
        tokens[fname_pos] = _get_initial_readings(tokens[fname_pos], last_name, 'fname')
        if len(initials_idxs) == 2:
            pname_pos = initials_idxs[1]
            tokens[pname_pos] = _get_initial_readings(tokens[pname_pos], last_name, 'pname')


class UkrainianHybridDisambiguator:
    """Port of UkrainianHybridDisambiguator: pre-disambiguation in code
    (preDisambiguate), then the multiword chunker for /uk/multiwords.txt and
    the rule-based disambiguator (disambiguation.xml)."""

    def __init__(self, language):
        self.language = language
        self.chunker = UkrainianMultiwordChunker(language.resource_path('uk/multiwords.txt'),
                                                 allow_first_capitalized=True)
        self.simple_disambiguator = SimpleDisambiguator()
        self._xml = None
        self._lock = threading.Lock()

    @property
    def disambiguator(self):
        if self._xml is None:
            with self._lock:
                if self._xml is None:
                    from ...extensions import _xml_disambiguator
                    self._xml = _xml_disambiguator(self.language.default_variant, False)
        return self._xml

    def disambiguate(self, sentence):
        self.pre_disambiguate(sentence)
        return self.disambiguator.disambiguate(self.chunker.disambiguate(sentence))

    def pre_disambiguate(self, sentence):
        self.simple_disambiguator.remove_rare_forms(sentence)
        self._remove_yih(sentence)
        self._remove_vmis(sentence)
        self._retag_fem_names(sentence)
        self._retag_initials(sentence)
        self._retag_unknown_initials(sentence)
        self._remove_inanim_v_kly(sentence)
        self._remove_plural_for_names(sentence)
        self._remove_lower_case_homonyms_for_abbreviations(sentence)
        self._remove_lower_case_bad_for_upper_case_good(sentence)
        self._disambiguate_st(sentence)
        self._disambiguate_pron_pos(sentence)
        self._retag_plural_prop(sentence)
        self._remove_verb_impr(sentence)
        return sentence

    def _remove_yih(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        for i in range(1, n):
            main_token = tokens[i]
            clean_token = main_token.get_clean_token()
            if not clean_token:
                continue
            if not _YIH.fullmatch(clean_token.lower()):
                continue
            if i < n - 1:
                next_clean = tokens[i + 1].get_clean_token().lower()
                if lh.has_lemma(tokens[i + 1], _YIH_NEXT_LEMMAS) or pth.has_pos_tag(tokens[i + 1], _NONINFL_PREDIC):
                    _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                    continue
                # їх було
                if pth.has_pos_tag_start(tokens[i + 1], 'verb') and not pth.has_pos_tag(tokens[i + 1], _ADJ_NOUN):
                    _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                    continue
                if _OBOH.fullmatch(next_clean) or (pth.has_pos_tag(tokens[i + 1], _PERS_OR_PREP) and
                                                   not _I_Z.fullmatch(next_clean)):
                    _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                    continue
                if i < n - 2 and _NE.fullmatch(next_clean) and pth.has_pos_tag_start(tokens[i + 2], 'verb'):
                    _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                    continue
                # exclude на його душу
                if not pth.has_pos_tag(tokens[i + 1], _ADJ_NOUN):
                    cg = lh.get_case_governments(tokens[i + 1], _VERB)
                    if 'v_rod' in cg or 'v_zna' in cg:
                        _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                        continue
            # посунув їх
            if i > 1:
                prev_cg = lh.get_case_governments(tokens[i - 1], _VERB_ADVP)
                if 'v_rod' in prev_cg or 'v_zna' in prev_cg:
                    # посунув їх швидко/у ...
                    if i == n - 1 or pth.has_pos_tag(tokens[i + 1], _ADV_PREP) or \
                            _PUNCT_DASH.fullmatch(tokens[i + 1].token):
                        _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                        continue
                    # примусили їх сказати
                    if i <= n - 1 and pth.has_pos_tag(tokens[i - 1], _VERB_ADVP) and \
                            pth.has_pos_tag(tokens[i + 1], _VERB_INF) and 'v_inf' in prev_cg:
                        _remove_readings(main_token, _ADJ_PRON, 'dis_yih_pron_pos')
                        continue

    def _remove_verb_impr(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        for i in range(2, len(tokens)):
            analyzed_tokens = tokens[i].readings
            if pth.has_pos_tag(tokens[i], _VERB_IMPR) and pth.has_pos_tag(tokens[i], _NOUN) and \
                    pth.has_pos_tag(tokens[i - 1], _ADJ):
                master = lh.get_adj_inflections(tokens[i - 1].readings)
                slave = lh.get_noun_inflections(tokens[i].readings, _V_ZNA_VAR)
                if not lh.java_disjoint(master, slave):
                    for at in pth.filter_tokens(analyzed_tokens, _VERB_IMPR):
                        tokens[i].remove_reading(at, 'not_an_imperative_2')

    def _retag_fem_names(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        rule_applied = 'proper_name_gender_override'
        i = 1
        while i < len(tokens) - 2:
            for gen in ('f', 'm'):
                prefix = _FEM_PREFIX if gen == 'f' else _MASC_PREFIX
                anim_prop_tag_prefix = 'noun:anim:' + gen + ':v_naz:prop'
                if (lh.has_lemma_pos(tokens[i], prefix, _c('noun:anim:' + gen + ':v_naz.*'))
                        or pth.has_pos_tag_start(tokens[i], anim_prop_tag_prefix + ':fname')) \
                        and pth.has_pos_tag(tokens[i + 2], _c('verb.*:past:' + gen)):
                    name_token = tokens[i + 1]
                    if pth.has_pos_tag_start(name_token, anim_prop_tag_prefix):
                        for at in _live_readings(name_token):
                            if not pth.has_pos_tag_start(at, anim_prop_tag_prefix):
                                name_token.remove_reading(at, rule_applied)
                    # леді Черчилль
                    elif gen == 'f' and pth.has_pos_tag_start(name_token, 'noun:anim:m:v_naz:prop'):
                        for at in _live_readings(name_token):
                            name_token.remove_reading(at, rule_applied)
                        name_token.add_reading(AnalyzedToken(name_token.token, 'noun:anim:f:v_naz:prop:lname',
                                                             name_token.token), rule_applied)
                    # Олег П'ятниця
                    elif lh.is_capitalized(name_token.get_clean_token()) \
                            and not pth.has_pos_tag_part(name_token, ':prop') \
                            and pth.has_pos_tag_start(tokens[i], anim_prop_tag_prefix + ':fname'):
                        for at in _live_readings(name_token):
                            name_token.remove_reading(at, rule_applied)
                        name_token.add_reading(AnalyzedToken(name_token.token, anim_prop_tag_prefix + ':lname',
                                                             name_token.token), rule_applied)
                    i += 1
            i += 1

    def _remove_vmis(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        v_mis_preps = _v_mis_preps()
        start_check = False
        for i in range(1, len(tokens)):
            analyzed_tokens = tokens[i].readings
            lower = tokens[i].token.lower()
            has_prep = pth.has_pos_tag_part(tokens[i], 'prep')
            if not start_check:
                if has_prep:
                    start_check = True
                elif _PATTERN_1.fullmatch(lower):
                    # sometimes sentences incorrectly split, e.g. "захопленню зброї;" - leave it
                    if _is_all_lower_case(tokens[i].token):
                        continue
                    start_check = True
            if has_prep and lower in v_mis_preps:
                return
            if not self._can_remove_vmis(analyzed_tokens):
                continue
            for at in analyzed_tokens:
                if pth.has_pos_tag_part(at, 'v_mis'):
                    tokens[i].remove_reading(at, 'dis_v_mis')

    @staticmethod
    def _can_remove_vmis(analyzed_tokens):
        found_vmis = found_other = False
        for t in analyzed_tokens:
            if pth.has_pos_tag_part(t, 'v_mis'):
                found_vmis = True
            elif t.pos_tag is not None and not t.pos_tag.endswith('_END'):
                found_other = True
            if found_vmis and found_other:
                break
        return found_vmis and found_other

    def _disambiguate_pron_pos(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        for i in range(1, n):
            analyzed_tokens = tokens[i].readings
            lower = tokens[i].get_clean_token().lower()
            if lower in ('його', 'її', 'їх') and pth.has_pos_tag(tokens[i], _ADJ_PRON_POS):
                noun_inflections = []
                if i > 1:
                    noun_inflections.extend(lh.get_noun_inflections(tokens[i - 1].readings, _IGNORE_IN_PRON_POS))
                if i < n - 1:
                    noun_inflections.extend(lh.get_noun_inflections(tokens[i + 1].readings, _IGNORE_IN_PRON_POS))
                if noun_inflections:
                    for at in analyzed_tokens:
                        if pth.has_pos_tag_start(at, 'adj'):
                            adj_inflections = lh.get_adj_inflections([at])
                            if lh.java_disjoint(noun_inflections, adj_inflections):
                                tokens[i].remove_reading(at, 'dis_pron_pos')

    def _remove_lower_case_bad_for_upper_case_good(self, sentence):
        # correct: Єврокомісія, but often written: єврокомісія
        # we will tag 2nd as :bad but need to remove :bad from Єврокомісія (tagger brings lowercase lemma too)
        tokens = sentence.get_tokens_without_whitespace()
        for i in range(1, len(tokens)):
            if len(tokens[i].readings) > 1 and lh.is_capitalized(tokens[i].get_clean_token()) \
                    and lh.has_lemma_pos(tokens[i], _CAP_LEMMA, _PROP):
                lower_lemma = tokens[i].readings[0].lemma.lower()
                analyzed_tokens = tokens[i].readings
                for j in range(len(analyzed_tokens) - 1, -1, -1):
                    at = analyzed_tokens[j]
                    if pth.has_pos_tag_part(at, ':bad') and lower_lemma == at.lemma:
                        tokens[i].remove_reading(at, 'lowercase_bad_vs_uppercase_good')

    def _remove_lower_case_homonyms_for_abbreviations(self, sentence):
        # all uppercase mostly are abbreviations, e.g. "АТО" is not part/intj
        tokens = sentence.get_tokens_without_whitespace()
        for i in range(1, len(tokens)):
            if _is_all_upper_case(tokens[i].token) and pth.has_pos_tag_part(tokens[i], ':abbr'):
                analyzed_tokens = tokens[i].readings
                for j in range(len(analyzed_tokens) - 1, -1, -1):
                    at = analyzed_tokens[j]
                    if not pth.has_pos_tag_part(at, ':abbr') and at.pos_tag != SENTENCE_END_TAGNAME \
                            and at.pos_tag != PARAGRAPH_END_TAGNAME:
                        tokens[i].remove_reading(at, 'lowercase_vs_abbr')

    def _remove_inanim_v_kly(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        for i in range(1, len(tokens)):
            analyzed_tokens = tokens[i].readings
            if not pth.has_pos_tag(analyzed_tokens, _INANIM_VKLY_NOT_GEO) or self._likely_vkly_context(tokens, i):
                continue
            inanim = []
            other_found = False
            for at in analyzed_tokens:
                t = at.pos_tag
                if t is None:
                    break
                if t == SENTENCE_END_TAGNAME:
                    continue
                if _INANIM_VKLY.fullmatch(t):
                    inanim.append(at)
                else:
                    other_found = True
            if inanim and other_found:
                for at in inanim:
                    if at.lemma == 'зоря':
                        continue
                    tokens[i].remove_reading(at, 'inanim_v_kly')

    @staticmethod
    def _likely_vkly_context(tokens, i):
        if tokens[i].token.lower() in _LIKELY_V_KLY:
            return True
        prev = tokens[i - 1].token.lower()
        return (i < len(tokens) - 1
                and (prev == 'о' or not pth.has_pos_tag_start(tokens[i - 1], 'prep'))
                and _PUNCT_AFTER_KLY_PATTERN.fullmatch(tokens[i + 1].token) is not None
                and (pth.has_pos_tag(tokens[i - 1], pth.ADJ_V_KLY_PATTERN) or prev == 'о'))

    def _remove_plural_for_names(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        for i in range(1, n):
            analyzed_tokens = tokens[i].readings
            if i > 1 and (pth.has_pos_tag_start(tokens[i - 1], 'adj:p')
                          or pth.has_pos_tag_part(tokens[i - 1], 'num')
                          or lh.has_lemma(tokens[i - 1], ('багато', 'мало', 'півсотня', 'сотня'))):
                continue
            # Юріїв Луценків
            if i < n - 1 and pth.has_pos_tag(tokens[i + 1], _PLURAL_LNAME_PATTERN):
                continue
            # Андріїв Фартушняка й Варанкова
            if i < n - 3 and pth.has_pos_tag_part(tokens[i + 1], ':lname') and \
                    pth.has_pos_tag_part(tokens[i + 3], ':lname'):
                continue
            plural = []
            other_found = False
            for at in analyzed_tokens:
                t = at.pos_tag
                if t is None:
                    break
                if t == SENTENCE_END_TAGNAME:
                    continue
                if _PLURAL_NAME.fullmatch(t):
                    plural.append(at)
                else:
                    other_found = True
            if plural and other_found:
                # наймолодшого з Моцартів
                if not lh.has_lemma_part_pos(tokens[i - 1], ('з', 'із', 'зі'), 'prep'):
                    for at in plural:
                        tokens[i].remove_reading(at, 'plural_for_names')

    def _retag_initials(self, sentence):
        tokens = sentence.tokens
        initials_idxs = []
        last_name = None
        for i in range(1, len(tokens)):
            if tokens[i].is_whitespace:
                continue
            if tokens[i].has_partial_pos_tag(_LAST_NAME_TAG):
                last_name = tokens[i]
                # split before next initial starts: "для Л.Кучма Л.Кравчук"
                if initials_idxs:
                    _check_for_initial_retag(last_name, initials_idxs, tokens)
                    last_name = None
                    initials_idxs = []
                continue
            if _is_initial(tokens, i):
                initials_idxs.append(i)
                continue
            _check_for_initial_retag(last_name, initials_idxs, tokens)
            last_name = None
            initials_idxs = []
        _check_for_initial_retag(last_name, initials_idxs, tokens)

    def _retag_unknown_initials(self, sentence):
        tokens = sentence.tokens
        for i in range(1, len(tokens)):
            t = tokens[i].token
            if t.endswith('.') and _INITIAL_REGEX.fullmatch(t):
                if pth.has_pos_tag_part(tokens[i], 'name'):
                    continue
                for r in tokens[i].readings:
                    tokens[i].remove_reading(r, 'dis_unknown_initials')
                tokens[i].add_reading(AnalyzedToken(t, 'noninfl:abbr', None), 'dis_unknown_initials')

    def _disambiguate_st(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        i = 1
        while i < n:
            if tokens[i].token != _ST_ABBR:
                i += 1
                continue
            # 10 мм рт. ст.
            if i > 1:
                if tokens[i - 1].token == 'рт.':
                    _remove_tokens_without(tokens[i], _XP3)
                    i += 1
                    continue
                _remove_tokens_without(tokens[i], _NOT_XP3)
            # стаття/сторінка
            if i < n - 1 and _PATTERN_2.fullmatch(tokens[i + 1].token):
                pattern = _c('noun:inanim:f:.*')
                if i > 2 and tokens[i - 1].token == _ST_ABBR:
                    pattern = _c('noun:inanim:p:.*')
                    _remove_tokens_without(tokens[i - 1], pattern)
                _remove_tokens_without(tokens[i], pattern)
                i += 1
                continue
            if i < n - 1:
                # столова
                if lh.has_lemma(tokens[i + 1], 'ложка') or tokens[i + 1].token == 'л.':
                    _remove_tokens_without(tokens[i], _c('adj:[fp]:.*'))
                    i += 2
                    continue
                # старший
                if lh.has_lemma(tokens[i + 1], ('лейтенант', 'сержант', 'солдат', 'науковий', 'медсестра')):
                    _remove_tokens_without(tokens[i], _c('adj:m:.*'))
                    i += 2
                    continue
                # станція
                if _STATION_NAME_PATTERN.fullmatch(tokens[i + 1].token):
                    _remove_tokens_without(tokens[i], _c('noun:inanim:f:.*'))
                    i += 2
                    continue
            # століття
            if i > 1:
                if _LATIN_DIGITS_PATTERN.fullmatch(tokens[i - 1].token):
                    pattern = _c('noun:inanim:n:.*')
                    if i < n - 1 and tokens[i + 1].token == _ST_ABBR:
                        pattern = _c('noun:inanim:p:.*')
                        _remove_tokens_without(tokens[i + 1], pattern)
                    _remove_tokens_without(tokens[i], pattern)
                    i += 2
                    continue
                elif _DIGITS_PATTERN.fullmatch(tokens[i - 1].token):
                    pattern = _c('noun:inanim:[nf]:.*')  # 18 ст. - стаття або століття
                    if i < n - 1 and tokens[i + 1].token == _ST_ABBR:
                        pattern = _c('noun:inanim:p:.*')
                        _remove_tokens_without(tokens[i + 1], pattern)
                    _remove_tokens_without(tokens[i], pattern)
                    i += 2
                    continue
            i += 1

    def _retag_plural_prop(self, sentence):
        tokens = sentence.get_tokens_without_whitespace()
        # дві Франції, три Катерини, два Володьки
        i = 2
        while i < len(tokens):
            prop_tokens = tokens[i]
            if _PATTERN_3.fullmatch(tokens[i - 1].get_clean_token().lower()) \
                    and not pth.has_pos_tag(prop_tokens, 'noun.*:p:v_naz.*:prop.*') \
                    and not pth.has_pos_tag(prop_tokens, 'noun.*:[mfn]:v_naz.*:prop.*'):
                prop_only = pth.filter_tokens(prop_tokens.readings, _PROP_ROD)
                prop_only = [s for s in prop_only
                             if ':m:' not in s.pos_tag or s.lemma.endswith('а') or s.lemma.endswith('о')]
                if prop_only:
                    postag = jregex.java_replace(_PATTERN_5, ':p:v_naz', prop_only[0].pos_tag, 1)
                    lemma = prop_only[0].lemma
                    for r in prop_tokens.readings:
                        prop_tokens.remove_reading(r, 'dis_plural_prop')
                    prop_tokens.add_reading(AnalyzedToken(prop_tokens.token, postag, lemma), 'dis_plural_prop')
                    i += 1
            i += 1
