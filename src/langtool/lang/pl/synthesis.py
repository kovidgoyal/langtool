"""Port of org.languagetool.synthesis.pl.PolishSynthesizer."""

import threading

from ... import jregex
from ...rules.abstract_rules import _java_string_hash
from ...synthesis import BaseSynthesizer, load_words
from ...tools import java_split

_POTENTIAL_NEGATION_TAG = ':aff'
_NEGATION_TAG = ':neg'
_COMP_TAG = 'com'
_SUP_TAG = 'sup'
_PATTERN = jregex.compile('.*[a-z]\\.[a-z].*')


def _java_hash_set_order(items):
    """The iteration order of new HashSet<>(items) (java.util.HashMap
    buckets; the bucket lists keep the insertion order). Unlike
    abstract_rules.java_hash_set_order, the capacity is the one of the
    HashSet(Collection) constructor."""
    unique = list(dict.fromkeys(items))
    # HashSet(Collection): capacity max(c.size() / .75f + 1, 16) (with the
    # duplicates of the collection), rounded up to a power of two by HashMap
    n = len(items)
    cap = 1
    while cap < max(int(n / 0.75) + 1, 16):
        cap <<= 1

    def bucket(s):
        h = _java_string_hash(s)
        return (h ^ (h >> 16)) & (cap - 1)

    return sorted(unique, key=bucket)  # stable: insertion order in a bucket


class PolishSynthesizer(BaseSynthesizer):
    """Polish word form synthesizer, based on the Morfologik dictionary
    /pl/polish_synth.dict (only the binary dictionary is used, like in Java,
    where the lookups bypass the manual additions and removals). Handles the
    negation of adjectives, participles and gerunds: the forms with ":neg"
    are synthesized from the ":aff" forms with the prefix "nie". POS tags
    with '+' are treated as regular expressions with the alternatives
    joined by '+'."""

    def __init__(self, dictionary, tags_path, resource_dir=None):
        super().__init__(dictionary, tags_path, 'pl', resource_dir)
        self._polish_possible_tags = None
        self._tags_lock = threading.Lock()

    def _is_negated(self, token, pos_tag):
        if token.pos_tag is None:
            return False
        return (pos_tag.find(_NEGATION_TAG) > 0
                or token.pos_tag.find(_NEGATION_TAG) > 0
                and not pos_tag.find(_COMP_TAG) > 0
                and not pos_tag.find(_SUP_TAG) > 0)

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        if pos_tag is None:
            return None
        if pos_tag_regexp:
            return self._synthesize_regexp(token, pos_tag)
        is_negated = self._is_negated(token, pos_tag)
        if pos_tag.find('+') > 0:
            return self._synthesize_regexp(token, pos_tag)
        return self._get_word_forms(token, pos_tag, is_negated)

    def _possible_tags_list(self):
        # (only the tags file, like SynthesizerTools.loadWords in Java)
        if self._polish_possible_tags is None:
            with self._tags_lock:
                if self._polish_possible_tags is None:
                    self._polish_possible_tags = load_words(self.tags_path)
        return self._polish_possible_tags

    def _synthesize_regexp(self, token, pos_tag):
        possible_tags = self._possible_tags_list()
        results = []
        is_negated = self._is_negated(token, pos_tag)
        if is_negated:
            pos_tag = pos_tag.replace(_NEGATION_TAG, _POTENTIAL_NEGATION_TAG + '?')
        try:
            p = jregex.compile(pos_tag.replace('+', '|'))
        except jregex.JavaRegexError:
            # Java catches the PatternSyntaxException of this rare error
            # (languagetool issue #1651) and prints its stack trace
            p = None
        if p is not None:
            for tag in possible_tags:
                if p.fullmatch(tag):
                    results.extend(self._get_word_forms(token, tag, is_negated))
        # remove duplicates (in the order of Java's HashSet)
        return _java_hash_set_order(results)

    def get_pos_tag_correction(self, pos_tag):
        if '.' in pos_tag:
            tags = java_split(pos_tag, ':')
            pos = -1
            for i, t in enumerate(tags):
                if _PATTERN.fullmatch(t):
                    tags[i] = '(.*' + t.replace('.', '.*|.*') + '.*)'
                    pos = i
            if pos == -1:
                return pos_tag
            return ':'.join(tags)
        return pos_tag

    def _get_word_forms(self, token, pos_tag, is_negated):
        lemma = 'null' if token.lemma is None else token.lemma
        forms = []
        if is_negated:
            for stem, _tag in self.dictionary.lookup(
                    lemma + '|' + pos_tag.replace(_NEGATION_TAG, _POTENTIAL_NEGATION_TAG, 1)):
                forms.append('nie' + ('null' if stem is None else stem))
        else:
            for stem, _tag in self.dictionary.lookup(lemma + '|' + pos_tag):
                if stem is not None:
                    forms.append(stem)
        return forms
