"""Port of org.languagetool.tagging.eo.EsperantoTagger."""

import os
import threading

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import ManualTagger
from ...tools import java_trim

# Verbs always end with this pattern.
_PATTERN_VERB = jregex.compile('(..+)(as|os|is|us|u|i)$')
_PATTERN_PREFIX = jregex.compile('^(?:mal|mis|ek|re|fi|ne)(.*)')
_PATTERN_SUFFIX = jregex.compile('(.*)(?:ad|aĉ|eg|et)i$')

# Participles -ant-, -int, ont-, -it-, -it-, -ot-
_PATTERN_PARTICIPLE = jregex.compile('((..+)([aio])(n?)t)([aoe])(j?)(n?)$')
# Groups                              11111111111111111  55555  66  77
#                                      222  33333  44

# Pattern 'tabelvortoj'.
_PATTERN_TABELVORTO = jregex.compile('^(i|ti|ki|ĉi|neni)(?:(?:([uoae])(j?)(n?))|(am|al|es|el|om))$')
# Groups                               111111111111111        222222  33  44    55555555555555

# Pattern of 'tabelvortoj' which are also tagged adverbs.
_PATTERN_TABELVORTO_ADVERB = jregex.compile('^(?:ti|i|ĉi|neni)(?:am|om|el|e)$')

_X_SYSTEM = {'c': 'ĉ', 'g': 'ĝ', 'h': 'ĥ', 'j': 'ĵ', 's': 'ŝ', 'u': 'ŭ'}


def _x_system_to_unicode(s):
    """Transform a string such as "jxauxdo" into "ĵaŭdo". We only care about
    lower case, as this is always invoked on the lemma which has already been
    transformed into lower case."""
    result = []
    length = len(s)
    i = 0
    while i < length:
        c1 = s[i]
        c2 = s[i + 1] if i + 1 < length else ' '
        if c2 == 'x' and c1 in _X_SYSTEM:
            result.append(_X_SYSTEM[c1])
            i += 1
        else:
            result.append(c1)
        i += 1
    return ''.join(result)


def _java_length(s):
    """String.length() (UTF-16 code units)"""
    return len(s) + sum(1 for c in s if ord(c) > 0xffff)


def _load_words(path):
    """Load a set of words from a UTF-8 file (one word per line)."""
    words = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = java_trim(line.rstrip('\r\n'))
            if not line or line[0] == '#':  # ignore comments
                continue
            words.add(line)
    return words


_data_cache = {}
_data_lock = threading.Lock()


def _load_data(resource_dir, rules_dir):
    key = (resource_dir, rules_dir)
    with _data_lock:
        data = _data_cache.get(key)
        if data is None:
            # A manual tagger is used for closed words. Closed words are the small
            # limited set of words in Esperanto which have no standard ending, as
            # opposed to open words which are unlimited in numbers and which follow
            # strict rules for their suffixes.
            manual_tagger = ManualTagger([os.path.join(resource_dir, 'manual-tagger.txt')])
            # Files don't contain verbs with suffix -iĝ or -ig since transitivity is
            # obvious for those verbs. They also don't contain verbs with prefixes mal-,
            # ek-, re-, mis- fi- and suffixes -ad, -aĉ, -et, -eg since these affixes
            # never alter transitivity.
            data = _data_cache[key] = (manual_tagger,
                                       _load_words(os.path.join(rules_dir, 'verb-tr.txt')),
                                       _load_words(os.path.join(rules_dir, 'verb-ntr.txt')),
                                       _load_words(os.path.join(rules_dir, 'root-ant-at.txt')))
        return data


class EsperantoTagger:
    """A part-of-speech tagger for Esperanto: closed words are tagged by a
    manual tagger (/eo/manual-tagger.txt), open words by their ending; verbs
    get their transitivity from the lists of transitive and intransitive
    verbs (rules/eo/verb-tr.txt, verb-ntr.txt), participles are recognized
    unless their root is in rules/eo/root-ant-at.txt. The data is loaded
    lazily (as in Java) and shared."""

    def __init__(self, resource_dir, rules_dir):
        self._resource_dir = resource_dir
        self._rules_dir = rules_dir
        self._data = None

    def _lazy_init(self):
        if self._data is None:
            self._data = _load_data(self._resource_dir, self._rules_dir)
        return self._data

    def _find_transitivity(self, verb):
        """For a given verb (.*i) find whether it is transitive and/or non
        transitive. Returns "tr" for a verb which is transitive, "nt" for a
        verb which is non-transitive, "tn" for a verb which is transitive and
        non-transitive, "xx" for an unknown verb."""
        if verb.endswith('iĝi'):
            return 'nt'
        elif verb.endswith('igi'):
            # The verb "memmortigi is strange: even though it ends in -igi, it
            # is intransitive.
            return 'nt' if verb == 'memmortigi' else 'tr'
        _, transitive_verbs, intransitive_verbs, _ = self._data
        # This loop executes only once for most verbs (or very few times).
        while True:
            is_transitive = verb in transitive_verbs
            is_intransitive = verb in intransitive_verbs
            if is_transitive:
                return 'tn' if is_intransitive else 'tr'
            elif is_intransitive:
                return 'nt'
            # Verb is not explicitly listed as transitive or intransitive.
            # Try to remove a prefix mal-, ek-, re-, mis- fi- or suffix -ad,
            # -aĉ, -et, -eg since those never alter transitivity. Then look up
            # verb again in case we find a verb with a known transitivity. For
            # example, given a verb "malŝategi", we will probe "malŝategi",
            # "ŝategi" "ŝati" and then finally find out that "ŝati" is
            # transitive.
            m = _PATTERN_PREFIX.search(verb)
            if m:
                # Remove a prefix and try again.
                verb = m.group(1)
                continue
            m = _PATTERN_SUFFIX.search(verb)
            if m:
                # Remove a suffix and try again.
                verb = m.group(1) + 'i'
                continue
            break
        return 'xx'  # Unknown transitivity.

    def tag(self, sentence_tokens):
        manual_tagger, _, _, non_participles = self._lazy_init()
        token_readings = []
        for word in sentence_tokens:
            l = []
            length = _java_length(word)
            if length > 50:
                # avoid excessively long computation times for long (probably artificial) tokens:
                l.append(AnalyzedToken(word, None, None))
            elif length > 1:
                # No Esperanto word is made of one letter only. This check avoids
                # spurious tagging as single letter words "A", "O", "E", etc.
                # Lemma contains words in lower case, and with Unicode transcription
                # (as opposed to x-system).
                l_word = _x_system_to_unicode(word.lower())
                manual_tags = manual_tagger.tag(l_word)
                if manual_tags:
                    # This is a closed word for which we know its lemmas and tags.
                    for manual_tag in manual_tags:
                        l.append(AnalyzedToken(word, manual_tag.pos_tag, manual_tag.lemma))
                else:
                    self._tag_open_word(word, l_word, l, non_participles)
            else:
                # Single letter word (no tag).
                l.append(AnalyzedToken(word, None, None))
            token_readings.append(AnalyzedTokenReadings(l, 0))
        return token_readings

    def _tag_open_word(self, word, l_word, l, non_participles):
        """This is an open word, we need to look at the word ending to
        determine its lemma and POS tag. For verbs, we also need to look up
        the dictionary of known transitive and intransitive verbs."""
        # Tiu, kiu (tabelvortoj).
        m = _PATTERN_TABELVORTO.search(l_word)
        if m:
            type1_group = m.group(1)[0:1].lower()
            type2_group = m.group(2)
            pl_group = m.group(3)
            acc_group = m.group(4)
            type3_group = m.group(5)
            if acc_group is None:
                accusative = 'xxx'
            else:
                accusative = 'akz' if acc_group.lower() == 'n' else 'nak'
            if pl_group is None:
                plural = ' pn '
            else:
                plural = ' pl ' if pl_group.lower() == 'j' else ' np '
            type_ = (type3_group if type2_group is None else type2_group).lower()
            l.append(AnalyzedToken(word, 'T ' + accusative + plural + type1_group + ' ' + type_, None))
            if _PATTERN_TABELVORTO_ADVERB.search(l_word):
                l.append(AnalyzedToken(word, 'E nak', l_word))
        # Words ending in .*oj?n? are nouns.
        elif l_word.endswith('o'):
            l.append(AnalyzedToken(word, 'O nak np', l_word))
        elif len(l_word) >= 2 and l_word.endswith("'"):
            l.append(AnalyzedToken(word, 'O nak np', l_word[:-1] + 'o'))
        elif l_word.endswith('oj'):
            l.append(AnalyzedToken(word, 'O nak pl', l_word[:-1]))
        elif l_word.endswith('on'):
            l.append(AnalyzedToken(word, 'O akz np', l_word[:-1]))
        elif l_word.endswith('ojn'):
            l.append(AnalyzedToken(word, 'O akz pl', l_word[:-2]))
        # Words ending in .*aj?n? are adjectives.
        elif l_word.endswith('a'):
            l.append(AnalyzedToken(word, 'A nak np', l_word))
        elif l_word.endswith('aj'):
            l.append(AnalyzedToken(word, 'A nak pl', l_word[:-1]))
        elif l_word.endswith('an'):
            l.append(AnalyzedToken(word, 'A akz np', l_word[:-1]))
        elif l_word.endswith('ajn'):
            l.append(AnalyzedToken(word, 'A akz pl', l_word[:-2]))
        # Words ending in .*en? are adverbs.
        elif l_word.endswith('e'):
            l.append(AnalyzedToken(word, 'E nak', l_word))
        elif l_word.endswith('en'):
            l.append(AnalyzedToken(word, 'E akz', l_word[:-1]))
        else:
            m = _PATTERN_VERB.search(l_word)
            if m:
                # Verbs.
                verb = m.group(1) + 'i'
                tense = m.group(2)
                transitive = self._find_transitivity(verb)
                l.append(AnalyzedToken(word, 'V ' + transitive + ' ' + tense, verb))
            else:
                # Irregular word (no tag).
                l.append(AnalyzedToken(word, None, None))

        # Participle (can be combined with other tags).
        m = _PATTERN_PARTICIPLE.search(l_word)
        if m and m.group(1) not in non_participles:
            verb = m.group(2) + 'i'
            aio = m.group(3)
            ant_at = 'n' if m.group(4) == 'n' else '-'
            aoe = m.group(5)
            plural = 'pl' if m.group(6) == 'j' else 'np'
            accusative = 'akz' if m.group(7) == 'n' else 'nak'
            transitive = self._find_transitivity(verb)
            l.append(AnalyzedToken(word, 'C ' + accusative + ' ' + plural + ' ' + transitive + ' ' + aio + ' '
                                   + ant_at + ' ' + aoe, verb))

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)

    def create_token(self, token, pos_tag):
        return AnalyzedToken(token, pos_tag, None)
