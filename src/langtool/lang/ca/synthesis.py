"""Port of org.languagetool.synthesis.ca.CatalanSynthesizer and
VerbSynthesizer."""

import sys

from ... import jregex
from ...analysis import AnalyzedToken
from ...chunking import ChunkTag
from ...synthesis import SPELLNUMBER_TAG, BaseSynthesizer
from ...tools import java_list_sort
from .helpers import P_PRONOM_FEBLE

# the verb tags of the regional variants
_VERB_TAGS = {
    'ca-ES': '[0CXY12]',
    'ca-ES-valencia': '[0VXZ13567]',
    'ca-ES-balear': '[0BYZ1247]',
}

# Exceptions
LEMMAS_TO_IGNORE = ('enterar', 'sentar', 'conseguir', 'alcançar')

_P_VERB = jregex.compile('V.*[CVBXYZ0123456]')
_P_LEMMA_SPACE = jregex.compile('([^ ]+) (.+)')


def _postag_comparator(arg0, arg1):
    """CatalanSynthesizer.PostagComparator: give priority 3 person > 1
    person, Indicative > Subjunctive"""
    len0 = len(arg0)
    len1 = len(arg1)
    if len0 > 4 and len1 > 4:
        if '3S' in arg0 and arg1 == '1S':
            return 150
        if '1S' in arg0 and '3S' in arg1:
            return -150
        if arg0 == 'VMIP2P00' and arg1 == 'VMIS3S00':
            # feu (present/passat)
            return 150
        if arg1 == 'VMIP2P00' and arg0 == 'VMIS3S00':
            return -150
        if arg0[2] == 'I' and arg1[2] != 'I':
            return 100
        if arg1[2] == 'I' and arg0[2] != 'I':
            return -100
        if arg0[4] == '3' and arg1[4] == '1':
            return 50
        if arg1[4] == '1' and arg0[4] == '3':
            return -50
    return 0


class CatalanSynthesizer(BaseSynthesizer):
    """Catalan word form synthesizer (/ca/ca-ES_synth.dict with
    /ca/ca-ES_tags.txt and the number speller /ca/ca.sor), one instance per
    variant (INSTANCE_CAT, INSTANCE_VAL, INSTANCE_BAL in Java). The POS tag
    is always used as a regular expression; if a verb form is not found,
    the forms of the regional variant are tried (the last character of the
    tag is replaced by the variant's class of tags). The lemmas of verbs
    can have words after the verb ("fer servir"): the verb is synthesized
    and the other words are added after it. The forms are not filtered with
    removeExceptions (CatalanSynthesizer overrides both synthesize methods).
    getTargetPosTag prefers 3rd person to 1st person and indicative to
    subjunctive."""

    def __init__(self, dictionary, tags_path, lang_code, resource_dir=None, number_speller=None,
                 roman_numberer=None, variant_code='ca-ES'):
        super().__init__(dictionary, tags_path, lang_code, resource_dir, number_speller, roman_numberer)
        self.variant_code = variant_code

    @staticmethod
    def _split_lemma(lemma, pos_tag):
        to_add_after = ''
        # verbs with noun
        if pos_tag.startswith('V') and lemma is not None:
            m = _P_LEMMA_SPACE.fullmatch(lemma)
            if m:
                lemma = m.group(1)
                to_add_after = m.group(2)
        return lemma, to_add_after

    def _lookup_matching(self, lemma, p):
        results = []
        for tag in self.get_possible_tags():
            if p.fullmatch(tag):
                results.extend(self.lookup(lemma, tag))
        return results

    @staticmethod
    def _add_words_after(results, to_add_after):
        if to_add_after:
            return [r + ' ' + to_add_after for r in results]
        return results

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        if pos_tag_regexp:
            return self._synthesize_regexp(token, pos_tag)
        if pos_tag.startswith(SPELLNUMBER_TAG):
            return super().synthesize(token, pos_tag)
        lemma, to_add_after = self._split_lemma(token.lemma, pos_tag)
        results = self._lookup_matching(lemma, jregex.compile(pos_tag))
        # if not found, try verbs from a regional variant
        if not results and pos_tag.startswith('V'):
            return self.synthesize(token, pos_tag[:-1] + _VERB_TAGS[self.variant_code], True)
        return self._add_words_after(results, to_add_after)

    def _synthesize_regexp(self, token, pos_tag):
        if pos_tag.startswith(SPELLNUMBER_TAG):
            return self.synthesize(token, pos_tag)
        lemma = token.lemma
        if lemma in LEMMAS_TO_IGNORE:
            return []
        lemma, to_add_after = self._split_lemma(lemma, pos_tag)
        try:
            p = jregex.compile(pos_tag)
        except jregex.JavaRegexError as e:
            print('WARNING: Error trying to synthesize POS tag ' + pos_tag + ' from token ' + str(token) + ': '
                  + str(e), file=sys.stderr)
            return None
        results = self._lookup_matching(lemma, p)
        # if not found, try verbs from the active regional variant
        if not results and _P_VERB.fullmatch(pos_tag):
            p = jregex.compile(pos_tag[:-1] + _VERB_TAGS[self.variant_code])
            results = self._lookup_matching(lemma, p)
        return self._add_words_after(results, to_add_after)

    def get_target_pos_tag(self, pos_tags, target_pos_tag):
        if not pos_tags:
            return target_pos_tag
        # (sorted in place, like in Java)
        java_list_sort(pos_tags, _postag_comparator)
        # return the last one to keep the previous results
        return pos_tags[-1]


_GV = ChunkTag('GV')
P_VERB = jregex.compile('V.*')
P_INFLECTED_VERB = jregex.compile('V.[SIM].*')
P_IMPERATIVE_VERB = jregex.compile('V.M.*')
P_VERB_IS = jregex.compile('V.[IS].*')
_P_NON_PARTICIPLE = jregex.compile('V.[^P].*')
_P_PARTICIPLE = jregex.compile('V.P.*')


class VerbSynthesizer:
    """Port of org.languagetool.synthesis.ca.VerbSynthesizer: synthesize a
    new verb with new_lemma (used in the last token) and new_postag (used
    in the first token). The verb can be single-word or multi-word."""

    def __init__(self, tokens, start_pos, lang, search_backward=False):
        self.search_backward = search_backward
        self.tokens = tokens
        self.language = lang
        self.i_first_verb = -1
        self.i_last_verb = -1
        self.new_lemma = None
        self.new_postag = None
        self.num_pronouns_before = -1
        self.num_pronouns_after = -1
        self._set_indexes(start_pos)

    def set_lemma_and_postag(self, lemma, postag):
        self.new_lemma = lemma
        self.new_postag = postag

    def set_postag(self, postag):
        self.new_lemma = self.tokens[self.i_last_verb].reading_with_tag_regex(P_VERB).lemma
        self.new_postag = postag

    def set_lemma(self, lemma):
        self.new_lemma = lemma
        self.new_postag = self.tokens[self.i_first_verb].reading_with_tag_regex(P_VERB).pos_tag

    def _set_indexes(self, start_pos):
        tokens = self.tokens
        if start_pos < 0 or start_pos >= len(tokens):
            return  # no verb found; is_undefined() will be true
        j = start_pos
        # single participle
        if (tokens[j].reading_with_tag_regex(_P_PARTICIPLE) is not None and not tokens[j].has_pos_tag('_GV_')
                and _GV not in tokens[j].chunk_tags):
            self.i_first_verb = self.i_last_verb = j
            self.num_pronouns_before = self.num_pronouns_after = 0
            return
        # If it is not a verb, find the first one
        if self.search_backward:
            while j > 0 and not self._is_verb(j):
                j -= 1
            found_some_verb = False
            while j > 0 and self._is_verb(j):
                found_some_verb = True
                j -= 1
            if found_some_verb:
                j += 1
        else:
            while j < len(tokens) and not self._is_verb(j):
                j += 1
        if self._is_verb(j):
            self.i_first_verb = self.i_last_verb = j
            # enrere
            i = j - 1
            while self._is_multitoken_verb(i) and not self.is_first_verb_is():
                self.i_first_verb = i
                i -= 1
            # avant
            i = j + 1
            while self._is_multitoken_verb(i) and not (self.is_first_verb_is() and self._is_verb_is(i)):
                self.i_last_verb = i
                i += 1
        else:
            return
        i = 1
        pronouns_after = 0
        while (self.i_last_verb + i < len(tokens) and not tokens[self.i_last_verb + i].whitespace_before
               and tokens[self.i_last_verb + i].reading_with_tag_regex(P_PRONOM_FEBLE) is not None):
            pronouns_after += 1
            i += 1
        self.num_pronouns_after = pronouns_after
        i = -1
        pronouns_before_no_space_before = 0
        pronouns_before = 0
        first = self.i_first_verb
        while first + i > 0 and tokens[first + i].reading_with_tag_regex(P_PRONOM_FEBLE) is not None:
            if (tokens[first + i].whitespace_before or first + i == 1
                    or tokens[first + i - 1].has_pos_tag_starting_with('_QM')):
                pronouns_before = pronouns_before + pronouns_before_no_space_before + 1
                pronouns_before_no_space_before = 0
            else:
                pronouns_before_no_space_before += 1
            i -= 1
        self.num_pronouns_before = pronouns_before

    def _is_verb(self, i):
        if i < 0 or i > len(self.tokens) - 1:
            return False  # out of bounds
        t = self.tokens[i]
        return (_GV in t.chunk_tags or t.reading_with_tag_regex(_P_NON_PARTICIPLE) is not None
                or (t.reading_with_tag_regex(_P_PARTICIPLE) is not None and t.has_pos_tag('_GV_')))

    def _is_multitoken_verb(self, i):
        if i < 0 or i > len(self.tokens) - 1:
            return False  # out of bounds
        return _GV in self.tokens[i].chunk_tags or self.tokens[i].has_pos_tag('_GV_')

    def synthesize(self):
        from ...rules.core_filters import adapt_suggestion
        synth = self.language.synthesizer
        result = []
        tokens = self.tokens
        first_verb = tokens[self.i_first_verb].reading_with_tag_regex(P_VERB)
        if self.i_first_verb == self.i_last_verb:
            synthesized = synth.synthesize(AnalyzedToken('', self.new_postag, self.new_lemma),
                                           _adjust_postag_to_lemma(self.new_lemma, self.new_postag))
            if synthesized:
                result.append(synthesized[0])
        else:
            for i in range(self.i_first_verb, self.i_last_verb + 1):
                if i == self.i_first_verb:
                    if first_verb is not None:
                        synthesized = synth.synthesize(first_verb,
                                                       _adjust_postag_to_lemma(first_verb.lemma, self.new_postag))
                        if synthesized:
                            result.append(synthesized[0])
                elif i == self.i_last_verb:
                    if tokens[i].whitespace_before:
                        result.append(' ')
                    last_verb = tokens[self.i_last_verb].reading_with_tag_regex(P_VERB)
                    if last_verb is None:
                        last_verb = first_verb
                    if last_verb is not None:
                        postag = last_verb.pos_tag
                        to_synthesize = AnalyzedToken('', postag, self.new_lemma)
                        synthesized = synth.synthesize(to_synthesize, _adjust_postag_to_lemma(self.new_lemma, postag))
                        if synthesized:
                            result.append(synthesized[0])
                else:
                    if tokens[i].whitespace_before:
                        result.append(' ')
                    result.append(tokens[i].token)
        return adapt_suggestion(self.language, ''.join(result), '')

    def get_string_from_to(self, start, end):
        sb = []
        for i in range(start, end + 1):
            if i > start and self.tokens[i].whitespace_before:
                sb.append(' ')
            sb.append(self.tokens[i].token)
        return ''.join(sb)

    def get_pronouns_str_before(self):
        return self.get_string_from_to(self.i_first_verb - self.num_pronouns_before, self.i_first_verb - 1)

    def get_pronouns_str_after(self):
        return self.get_string_from_to(self.i_last_verb + 1, self.i_last_verb + self.num_pronouns_after)

    def get_whole_original_str(self):
        return self.get_string_from_to(self.i_first_verb - self.num_pronouns_before,
                                       self.i_last_verb + self.num_pronouns_after)

    def get_verb_str(self):
        return self.get_string_from_to(self.i_first_verb, self.i_last_verb)

    def get_first_verb_index(self):
        return self.i_first_verb

    def get_last_verb_index(self):
        return self.i_last_verb

    def get_last_index(self):
        return self.i_last_verb + self.num_pronouns_after

    def get_num_pronouns_after(self):
        return self.num_pronouns_after

    def get_num_pronouns_before(self):
        return self.num_pronouns_before

    def get_first_verb_persona_number(self):
        reading = self.tokens[self.i_first_verb].reading_with_tag_regex(P_INFLECTED_VERB)
        if reading is not None:
            return reading.pos_tag[4:6]
        return ''

    def get_first_verb_persona_number_imperative(self):
        reading = self.tokens[self.i_first_verb].reading_with_tag_regex(P_IMPERATIVE_VERB)
        if reading is not None:
            return reading.pos_tag[4:6]
        return ''

    def is_first_verb_is(self):
        if self.i_first_verb == -1:
            return False
        return self.tokens[self.i_first_verb].reading_with_tag_regex(P_VERB_IS) is not None

    def get_first_verb_is_postag(self):
        if self.i_first_verb == -1:
            return None
        reading = self.tokens[self.i_first_verb].reading_with_tag_regex(P_VERB_IS)
        if reading is not None:
            return reading.pos_tag
        return None

    def _is_verb_is(self, i):
        if i < 0 or i >= len(self.tokens):
            return False
        return self.tokens[i].reading_with_tag_regex(P_VERB_IS) is not None

    def get_casing_model(self):
        return self.get_string_from_to(self.i_first_verb - self.num_pronouns_before, self.i_first_verb)

    def is_undefined(self):
        return (self.i_first_verb == -1 or self.i_last_verb == -1 or self.num_pronouns_after == -1
                or self.num_pronouns_before == -1)

    def is_passat_perifrastic(self):
        if self.i_first_verb < 1 or self.i_first_verb + 1 > len(self.tokens) - 1:
            return False
        t = self.tokens[self.i_first_verb]
        return (t.has_pos_tag_starting_with('VA') and t.has_lemma('anar')
                and self.tokens[self.i_first_verb + 1].has_any_partial_pos_tag('VMN', 'VSN', 'VAN'))

    def is_perfet(self):
        if self.i_first_verb < 1 or self.i_first_verb + 1 > len(self.tokens) - 1:
            return False
        t = self.tokens[self.i_first_verb]
        return (t.has_pos_tag_starting_with('VA') and t.has_lemma('haver')
                and self.tokens[self.i_first_verb + 1].has_any_partial_pos_tag('VMP', 'VSP', 'VAP'))


def _adjust_postag_to_lemma(lemma, postag):
    if lemma == 'haver':
        postag = 'VA' + postag[2:]
    if lemma == 'ser':
        postag = 'VS' + postag[2:]
    return postag
