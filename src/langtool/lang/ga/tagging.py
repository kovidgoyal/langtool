"""Port of org.languagetool.tagging.ga.IrishTagger."""

import threading

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import BaseTagger
from ...tools import uppercase_first_char
from . import utils

_CACHE_SIZE = 100000


class IrishTagger(BaseTagger):
    """Irish part-of-speech tagger: a BaseTagger for /ga/irish.dict (with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt) with
    its own tag(): the word is tagged as is and in Irish lowercase
    (Utils.toLowerCaseIrish); unknown words are guessed from the forms with
    initial mutations or non-standard suffixes removed (Utils.morphWord),
    getting tags with ':MorphError' etc. appended, and lowercase words also
    from the uppercase-first form."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'ga', resource_dir)
        self._restrict_patterns = {}
        self._lock = threading.Lock()

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            readings = self._cache.get(word)
            if readings is None:
                readings = tuple(self._compute(word))
                with self._lock:
                    if len(self._cache) > _CACHE_SIZE:
                        self._cache.clear()
                    self._cache[word] = readings
            token_readings.append(AnalyzedTokenReadings(
                [AnalyzedToken(word, tag, lemma) for lemma, tag in readings], pos))
            pos += len(word)
        return token_readings

    def _compute(self, word):
        """the (lemma, tag) pairs of the readings of a word (IrishTagger.tag
        for one token)"""
        out = []
        lower_word = utils.to_lower_case_irish(word)
        tagger_tokens = self._tagged(word)
        lower_tagger_tokens = self._tagged(lower_word)
        is_lowercase = word == lower_word
        # normal case
        out.extend(tagger_tokens)
        if not is_lowercase:
            # lowercase
            out.extend(lower_tagger_tokens)
        # uppercase
        if not lower_tagger_tokens and not tagger_tokens:
            guessed_tokens = self._filter_morph(word)
            lower_guessed_tokens = self._filter_morph(utils.to_lower_case_irish(word))
            if guessed_tokens:
                out.extend(guessed_tokens)
            if not guessed_tokens and lower_guessed_tokens:
                out.extend(lower_guessed_tokens)
            if is_lowercase:
                upper_tagger_tokens = self._tagged(uppercase_first_char(word))
                if upper_tagger_tokens:
                    out.extend(upper_tagger_tokens)
                else:
                    upper_guessed_tokens = self._filter_morph(uppercase_first_char(word))
                    if upper_guessed_tokens:
                        out.extend(upper_guessed_tokens)
                    else:
                        out.append((None, None))
            else:
                out.append((None, None))
        return out

    def _restrict_pattern(self, regex):
        p = self._restrict_patterns.get(regex)
        if p is None:
            p = self._restrict_patterns[regex] = jregex.compile(regex)
        return p

    def _filter_morph(self, s):
        """IrishTagger.filterMorph: the (lemma, tag) pairs of the
        Retaggables of Utils.morphWord"""
        tagged = []
        tocheck = utils.morph_word(s)
        if not tocheck:
            return tagged
        word_tagger = self.word_tagger
        for rt in tocheck:
            pfx = False
            cur = word_tagger.tag(rt.word)
            if rt.prefix is not None and rt.prefix != '':
                tryword = rt.prefix + utils.lenite(rt.word)
                joined = word_tagger.tag(tryword)
                hyphword = rt.prefix + '-' + utils.lenite(rt.word)
                hyphen = word_tagger.tag(hyphword)
                if joined:
                    cur = joined
                    pfx = False
                elif hyphen:
                    pfx = False
                    cur = hyphen
                else:
                    pfx = True
            if not cur:
                continue
            restrict = self._restrict_pattern(rt.restrict_to_pos)
            for tw in cur:
                append = rt.append_tag + ':NonStdCmpd' if pfx else rt.append_tag
                if restrict.fullmatch(tw.pos_tag) is not None:
                    lemma = rt.prefix + utils.lenite(tw.lemma) if pfx else tw.lemma
                    tagged.append((lemma, tw.pos_tag + append))
        return tagged
