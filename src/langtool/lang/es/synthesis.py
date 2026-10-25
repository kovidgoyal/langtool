"""Port of org.languagetool.synthesis.es.SpanishSynthesizer."""

import sys

from ... import jregex
from ...synthesis import SPELLNUMBER_TAG, BaseSynthesizer
from ...tools import java_list_sort

_LEMMA_SPACE = jregex.compile('([^ ]+) (.+)')


def _postag_comparator(arg0, arg1):
    """SpanishSynthesizer.PostagComparator: Indicative > Imperative"""
    if len(arg0) > 4 and len(arg1) > 4:
        if arg0 == 'VMIP3S0' and arg1 == 'VMM02S0':
            return 150
        if arg0 == 'VMM02S0' and arg1 == 'VMIP3S0':
            return -150
    return 0


class SpanishSynthesizer(BaseSynthesizer):
    """Spanish word form synthesizer (/es/es-ES_synth.dict with
    /es/es-ES_tags.txt and the number speller of /es/es.sor). The lemmas
    of verbs can have words after the verb ("hacer clic"): the verb is
    synthesized and the other words are added after it. The forms are not
    filtered with removeExceptions (SpanishSynthesizer overrides both
    synthesize methods). getTargetPosTag prefers VMIP3S0 to VMM02S0."""

    def _split_lemma(self, token, pos_tag):
        lemma = token.lemma
        to_add_after = ''
        # verbs with noun
        if pos_tag.startswith('V') and lemma is not None:
            m = _LEMMA_SPACE.fullmatch(lemma)
            if m:
                lemma = m.group(1)
                to_add_after = m.group(2)
        return lemma, to_add_after

    @staticmethod
    def _add_words_after(results, to_add_after):
        if to_add_after:
            return [r + ' ' + to_add_after for r in results]
        return results

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        if pos_tag.startswith(SPELLNUMBER_TAG):
            return super().synthesize(token, pos_tag)
        lemma, to_add_after = self._split_lemma(token, pos_tag)
        if pos_tag_regexp:
            try:
                p = jregex.compile(pos_tag)
            except jregex.JavaRegexError as e:
                print('WARNING: Error trying to synthesize POS tag ' + pos_tag + ' from token ' + token.token
                      + ': ' + str(e), file=sys.stderr)
                return None
            results = []
            for tag in self.tags_matching(p):
                results.extend(self.lookup(lemma, tag))
        else:
            results = self.lookup(lemma, pos_tag)
        return self._add_words_after(results, to_add_after)

    def get_target_pos_tag(self, pos_tags, target_pos_tag):
        if not pos_tags:
            return target_pos_tag
        # (sorted in place, like in Java)
        java_list_sort(pos_tags, _postag_comparator)
        # return the last one to keep the previous results
        return pos_tags[-1]
