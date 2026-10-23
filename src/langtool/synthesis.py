"""Synthesizers (generate a word form from lemma + POS tag). Port of
org.languagetool.synthesis.BaseSynthesizer and ManualSynthesizer."""

import os

from . import jregex
from .tagging import iter_manual_lines
from .tools import java_trim

SPELLNUMBER_TAG = '_spell_number_'
SPELLNUMBER_FEMININE_TAG = '_spell_number_:feminine'
SPELLNUMBER_ROMAN_TAG = '_spell_number_:Roman'


class ManualSynthesizer:

    def __init__(self, paths):
        self.map = {}
        tags = set()
        for form, lemma, tag in iter_manual_lines(paths, check_nbsp=False):
            self.map.setdefault((lemma, tag), []).append(form)
            tags.add(tag)
        self.possible_tags = tags

    def lookup(self, lemma, pos_tag):
        if lemma is None or pos_tag is None:
            return None
        return self.map.get((lemma, pos_tag))


def load_words(path):
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = java_trim(line.rstrip('\r\n'))
            if not line or line[0] == '#':
                continue
            out.append(line)
    return out


class BaseSynthesizer:

    def __init__(self, dictionary, tags_path, lang_code, resource_dir=None, number_speller=None, roman_numberer=None):
        self.dictionary = dictionary
        self.tags_path = tags_path
        self.lang_code = lang_code
        self.number_speller = number_speller
        self.roman_numberer = roman_numberer
        self._possible_tags = None

        def manual(name):
            if resource_dir is not None:
                p = os.path.join(resource_dir, name)
                if os.path.exists(p):
                    return ManualSynthesizer([p])
            return None

        self.manual_synthesizer = manual('added.txt')
        self.removal_synthesizer = manual('removed.txt')
        self.removal_synthesizer2 = manual('do-not-synthesize.txt')
        self._cache = {}

    def lookup(self, lemma, pos_tag):
        key = (lemma, pos_tag)
        r = self._cache.get(key)
        if r is not None:
            return list(r)
        results = []
        if self.dictionary is not None:
            word = ('null' if lemma is None else lemma) + '|' + ('null' if pos_tag is None else pos_tag)
            for stem, tag in self.dictionary.lookup(word):
                results.append(stem)
        if self.manual_synthesizer is not None:
            mf = self.manual_synthesizer.lookup(lemma, pos_tag)
            if mf:
                results.extend(mf)
        for rs in (self.removal_synthesizer, self.removal_synthesizer2):
            if rs is not None:
                rf = rs.lookup(lemma, pos_tag)
                if rf:
                    rset = set(rf)
                    results = [x for x in results if x not in rset]
        if len(self._cache) > 50000:
            self._cache.clear()
        self._cache[key] = tuple(results)
        return results

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        if pos_tag_regexp:
            p = jregex.compile(pos_tag)
            return self.synthesize_for_pos_tags(token.lemma, lambda tag: p.fullmatch(tag) is not None)
        if pos_tag == SPELLNUMBER_TAG:
            return [self.get_spelled_number(token.token)]
        if pos_tag == SPELLNUMBER_FEMININE_TAG:
            return [self.get_spelled_number('feminine ' + token.token)]
        if pos_tag == SPELLNUMBER_ROMAN_TAG:
            return [self.get_roman_number(token.token)]
        return self.remove_exceptions(self.lookup(token.lemma, pos_tag))

    def synthesize_for_pos_tags(self, lemma, accept_tag):
        results = []
        for tag in self.get_possible_tags():
            if accept_tag(tag):
                results.extend(self.lookup(lemma, tag))
        return self.remove_exceptions(results)

    def get_possible_tags(self):
        if self._possible_tags is None:
            tags = load_words(self.tags_path) if self.tags_path and os.path.exists(self.tags_path) else []
            seen = set(tags)
            if self.manual_synthesizer is not None:
                for t in self.manual_synthesizer.possible_tags:
                    if t not in seen:
                        tags.append(t)
                        seen.add(t)
            self._possible_tags = tags
        return self._possible_tags

    def get_pos_tag_correction(self, pos_tag):
        return pos_tag

    def get_target_pos_tag(self, pos_tags, target_pos_tag):
        if not pos_tags:
            return target_pos_tag
        return pos_tags[-1]

    def get_spelled_number(self, arabic_numeral):
        if self.number_speller is not None:
            return self.number_speller.run(arabic_numeral)
        return arabic_numeral

    def get_roman_number(self, arabic_numeral):
        if self.roman_numberer is not None:
            return self.roman_numberer.run(arabic_numeral)
        return arabic_numeral

    def is_exception(self, w):
        return False

    def remove_exceptions(self, words):
        return [w for w in words if not self.is_exception(w)]
