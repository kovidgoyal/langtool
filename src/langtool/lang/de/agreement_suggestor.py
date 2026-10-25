"""Port of org.languagetool.rules.de.AgreementSuggestor2: suggestions for
noun phrases (determiner, up to two adjectives, noun) whose words do not
agree, created with the synthesizer."""

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...rules.multitoken import levenshtein_distance
from ...tools import is_upper_case, uppercase_first_char
from .preposition_to_cases import get_cases_for

# AgreementRule.ReplacementType
REPLACEMENT_INS = 'Ins'
REPLACEMENT_ZUR = 'Zur'

_DET_TEMPLATE = 'ART:IND/DEF:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU'
_PRO_POS_TEMPLATE = ('PRO:POS:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:BEG',
                     'PRO:POS:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:B/S')
_PRO_DEM_TEMPLATES = ('PRO:DEM:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:BEG',
                      'PRO:DEM:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:B/S')
_PRO_IND_TEMPLATES = ('PRO:IND:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:BEG',
                      'PRO:IND:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:B/S')
_ADJ_TEMPLATE = 'ADJ:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:GRU:IND/DEF'
_PA1_TEMPLATE = 'PA1:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:GRU:IND/DEF:VER'
_PA2_TEMPLATE = 'PA2:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:GRU:IND/DEF:VER'
_NOUN_TEMPLATES = ('SUB:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU',
                   'SUB:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:INF')  # INF is for cases like "das Züchten" etc.
_NUMBER = ('SIN', 'PLU')
_GENDER = ('MAS', 'FEM', 'NEU', 'NOG')
_CASES = ('NOM', 'AKK', 'DAT', 'GEN')
_NOUN_CASES = ['NOM', 'AKK', 'DAT', 'GEN']
_SKIP_SUGGESTIONS = frozenset(('unsren', 'unsrem', 'unsres', 'unsre', 'unsern', 'unserm', 'unsrer'))

_DERSELBE = jregex.compile('([Dd]as|[Dd]er|[Dd]ie|[Dd]em|[Dd]es)selben?')
_WELCHE = jregex.compile('[Ww]elche[nmsr]?')
_UP_TO_HYPHEN = jregex.compile('.*-')


class _Suggestion:
    __slots__ = ('phrase', 'token_level_edits', 'char_level_corrections')

    def __init__(self, phrase, token_level_edits, char_level_edits):
        self.phrase = phrase
        self.token_level_edits = token_level_edits
        self.char_level_corrections = char_level_edits

    def __repr__(self):
        return '%s/c=%d' % (self.phrase, self.token_level_edits)


class AgreementSuggestor2:
    """Suggestions for a determiner (+ adjective(s)) + noun phrase. The
    constructor takes the tokens like the Java constructors:
    (synthesizer, det, noun, repl_type), (synthesizer, det, adj1, noun,
    repl_type) or (synthesizer, det, adj1, adj2, noun, repl_type), where
    repl_type is None, REPLACEMENT_INS or REPLACEMENT_ZUR."""

    def __init__(self, synthesizer, determiner_token, *tokens_and_replacement_type):
        if not 2 <= len(tokens_and_replacement_type) <= 4:
            raise TypeError('AgreementSuggestor2(synthesizer, det, [adj1, [adj2,]] noun, replacementType)')
        *middle, noun_token, replacement_type = tokens_and_replacement_type
        self.synthesizer = synthesizer
        self.determiner_token = determiner_token
        self.adj_token1 = middle[0] if len(middle) > 0 else None
        self.adj_token2 = middle[1] if len(middle) > 1 else None
        self.noun_token = noun_token
        self.replacement_type = replacement_type
        self.orig_phrase = self._get_orig_phrase()
        self.preposition_token = None
        self.skipped_str = None
        self._synth_cache = {}

    def set_preposition(self, prep):
        self.preposition_token = prep

    def set_skipped(self, skipped_str):
        self.skipped_str = skipped_str

    def get_suggestions(self, filter=False):
        """filter: to filter only the best suggestions, as in: if there are
        suggestions that replace only one word in the original phrase, don't
        return those that replace two words etc."""
        if self.replacement_type == REPLACEMENT_ZUR:
            self.preposition_token = AnalyzedTokenReadings(AnalyzedToken('zu', '', 'zu'))
        elif self.replacement_type == REPLACEMENT_INS:
            self.preposition_token = AnalyzedTokenReadings(AnalyzedToken('in', '', 'zu'))
        suggestions = self._get_suggestions_internal()
        # sort so that suggestions with fewer edits come first (stable, like Java's List.sort)
        suggestions.sort(key=lambda s: (s.token_level_edits, s.char_level_corrections))
        suggestions = self._add_contraction(suggestions)
        if filter:
            filtered = []
            prev_corrections = suggestions[0].token_level_edits if suggestions else 0
            had_real_suggestions = False
            for suggestion in suggestions:
                if had_real_suggestions and suggestion.token_level_edits > prev_corrections:
                    break
                had_real_suggestions = suggestion.token_level_edits > 0
                filtered.append(suggestion)
            return [s.phrase for s in filtered]
        return [s.phrase for s in suggestions]

    def _add_contraction(self, suggestions):
        if self.replacement_type == REPLACEMENT_ZUR:
            for k in suggestions:
                if k.phrase.startswith('der'):
                    k.phrase = k.phrase.replace('der', 'zur', 1)
                elif k.phrase.startswith('den'):
                    k.phrase = k.phrase.replace('den', 'zu', 1)  # usually sounds more natural than "zu den"
                elif k.phrase.startswith('dem'):
                    k.phrase = k.phrase.replace('dem', 'zum', 1)
        elif self.replacement_type == REPLACEMENT_INS:
            kept = []
            for s in suggestions:
                if s.phrase.startswith('das'):
                    s.phrase = s.phrase.replace('das', 'ins', 1)
                elif s.phrase.startswith('dem'):
                    s.phrase = s.phrase.replace('dem', 'im', 1)
                elif s.phrase.startswith('den'):
                    s.phrase = s.phrase.replace('den', 'in den', 1)
                elif s.phrase.startswith('die'):
                    s.phrase = s.phrase.replace('die', 'in die', 1)
                else:
                    continue
                kept.append(s)
            return kept
        return suggestions

    def _get_suggestions_internal(self):
        noun_cases = self._get_noun_cases()
        result = []
        seen = set()
        # (the synthesized nouns and adjectives do not depend on the determiner reading (for the adjectives: only
        # on its definiteness), so they are computed once per combination instead of once per determiner reading)
        self._synth_cache = {}
        for num in _NUMBER:
            for gen in _GENDER:
                for a_case in _CASES:
                    if a_case not in noun_cases:
                        continue
                    for det_reading in self.determiner_token.readings:
                        if gen == 'NOG':  # needed to offer suggestions for e.g. "meinem Eltern" -> "meine Eltern, ..."
                            det_synthesized = self._get_det_or_pronoun_synth(num, 'MAS', a_case, det_reading)
                            adj1_synthesized = self._get_adj_synth(num, 'MAS', a_case, self.adj_token1, det_reading)
                            adj2_synthesized = self._get_adj_synth(num, 'MAS', a_case, self.adj_token2, det_reading)
                            noun_synthesized = self._get_noun_synth(num, 'NOG', a_case)
                        else:
                            det_synthesized = self._get_det_or_pronoun_synth(num, gen, a_case, det_reading)
                            adj1_synthesized = self._get_adj_synth(num, gen, a_case, self.adj_token1, det_reading)
                            adj2_synthesized = self._get_adj_synth(num, gen, a_case, self.adj_token2, det_reading)
                            noun_synthesized = self._get_noun_synth(num, gen, a_case)
                        self._combine_synth(result, seen, det_synthesized, adj1_synthesized, adj2_synthesized,
                                            noun_synthesized)
        return result

    def _get_noun_cases(self):
        # also "bis zur" = "bis" must not be considered preposition: "zur" = "zu der"
        if self.preposition_token is not None:
            # some prepositions require specific cases, so only generated those:
            result = []
            cases_for_token = get_cases_for(self.preposition_token.token)
            if cases_for_token:
                for a_case in cases_for_token:
                    val = a_case.lower()
                    if val not in result:  # (sic: compares the lowercase value)
                        result.append(val.upper())
                return result
        return _NOUN_CASES

    def _get_det_or_pronoun_synth(self, num, gen, a_case, det_reading):
        det_pos = det_reading.pos_tag
        if det_pos is None:
            return []
        is_def = ':DEF:' in det_pos
        det_token = det_reading.token
        if _DERSELBE.fullmatch(det_token):
            templates = ('PRO:DEM:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU',)
        elif _WELCHE.fullmatch(det_token):
            templates = ('PRO:RIN:NOM/AKK/DAT/GEN:SIN/PLU:MAS/FEM/NEU:B/S',)
        elif 'ART:' in det_pos:
            templates = (_DET_TEMPLATE,)
        elif 'PRO:POS:' in det_pos:
            templates = _PRO_POS_TEMPLATE
        elif 'PRO:DEM:' in det_pos:
            templates = _PRO_DEM_TEMPLATES
        elif 'PRO:IND:' in det_pos:
            templates = _PRO_IND_TEMPLATES
        elif det_token == 'zur':
            templates = (_DET_TEMPLATE,)
            det_reading = AnalyzedToken('der', '', 'der')
            is_def = True
        elif det_token == 'ins':
            templates = (_DET_TEMPLATE,)
            det_reading = AnalyzedToken('das', '', 'der')
            is_def = True
        else:
            return []
        synthesized = []
        orig_first_char = det_reading.token[:1]
        orig_first_lower = orig_first_char.lower()
        upper = is_upper_case(orig_first_char)
        for template in templates:
            template = template.replace('IND/DEF', 'DEF' if is_def else 'IND', 1)
            pos = _replace_vars(template, num, gen, a_case)
            for k in self.synthesizer.synthesize(det_reading, pos):
                if not k.lower().startswith(orig_first_lower):
                    continue
                if k.lower() in _SKIP_SUGGESTIONS:
                    continue
                # don't suggest "dein" for "mein" etc.
                synthesized.append(uppercase_first_char(k) if upper else k)
        return synthesized

    def _get_adj_synth(self, num, gen, a_case, adj_token, det_reading):
        if adj_token is None:
            return ['']  # noun phrase without an adjective
        det_pos = det_reading.pos_tag
        key = ('adj', num, gen, a_case, id(adj_token), det_pos is None,
               det_pos is not None and (':DEF:' in det_pos or det_reading.token == 'ins'))
        r = self._synth_cache.get(key)
        if r is None:
            r = self._synth_cache[key] = self._get_adj_synth0(num, gen, a_case, adj_token, det_reading)
        return r

    def _get_adj_synth0(self, num, gen, a_case, adj_token, det_reading):
        adj_synthesized = []
        if adj_token is not None:
            for adj_reading in adj_token.readings:
                adj_pos_tag = adj_reading.pos_tag
                if adj_pos_tag is None or det_reading.pos_tag is None:
                    continue
                if adj_reading.token == 'meisten' and num == 'SIN':
                    continue
                if adj_pos_tag.startswith('ADV:'):  # adverb, nothing to synthesize
                    adj_synthesized.append(adj_reading.token)
                    continue
                det_is_def = ':DEF:' in det_reading.pos_tag or det_reading.token == 'ins'
                if adj_pos_tag.startswith('PA1'):
                    template = _PA1_TEMPLATE
                elif adj_pos_tag.startswith('PA2'):
                    template = _PA2_TEMPLATE
                else:
                    template = _ADJ_TEMPLATE
                if ':KOM:' in adj_pos_tag:
                    template = template.replace(':GRU:', ':KOM:')
                elif ':SUP:' in adj_pos_tag:
                    template = template.replace(':GRU:', ':SUP:')
                template = template.replace('IND/DEF', 'DEF' if det_is_def else 'IND', 1)
                adj_pos = _replace_vars(template, num, gen, a_case)
                for synth in self.synthesizer.synthesize(adj_reading, adj_pos):
                    if synth not in adj_synthesized:
                        adj_synthesized.append(synth)
        else:
            adj_synthesized.append('')  # noun phrase without an adjective
        return adj_synthesized

    def _get_noun_synth(self, num, gen, a_case):
        key = ('noun', num, gen, a_case)
        r = self._synth_cache.get(key)
        if r is None:
            r = self._synth_cache[key] = self._get_noun_synth0(num, gen, a_case)
        return r

    def _get_noun_synth0(self, num, gen, a_case):
        result = []
        noun_token = self.noun_token
        for noun_reading in noun_token.readings:
            for noun_template in _NOUN_TEMPLATES:
                noun_pos = _replace_vars(noun_template, num, gen, a_case)
                noun_synthesized = self.synthesizer.synthesize(noun_reading, noun_pos)
                if not noun_synthesized and '-' in noun_reading.token:
                    first_part = noun_reading.token[:noun_reading.token.rfind('-') + 1]
                    last_token_part = _UP_TO_HYPHEN.sub('', noun_token.token, count=1)
                    last_lemma_part = _UP_TO_HYPHEN.sub('', noun_reading.lemma, count=1) \
                        if noun_reading.lemma is not None else None
                    noun_synthesized = self.synthesizer.synthesize(
                        AnalyzedToken(last_token_part, 'fake_value', last_lemma_part), noun_pos)
                    for last_part_inflected in noun_synthesized:
                        result.append(first_part + last_part_inflected)
                else:
                    result.extend(noun_synthesized)
        # remove forms like "Blutfluß" if there's also "Blutfluss" - must be old spelling then:
        old_spelling = {k.replace('ss', 'ß') for k in result if 'ss' in k}
        return [k for k in result if k not in old_spelling]

    def _combine_synth(self, result, seen, det_synthesized, adj1_synthesized, adj2_synthesized, noun_synthesized):
        det_token = self.determiner_token.token
        adj_token1 = self.adj_token1
        adj_token2 = self.adj_token2
        noun_token = self.noun_token.token
        skipped_str = self.skipped_str
        for det_elem in det_synthesized:
            for adj1_elem in adj1_synthesized:
                for adj2_elem in adj2_synthesized:
                    for noun_elem in noun_synthesized:
                        elem = det_elem
                        if skipped_str is not None:
                            elem += ' ' + skipped_str
                        if adj1_elem:
                            elem += ' ' + adj1_elem
                        if adj2_elem:
                            elem += ' ' + adj2_elem
                        elem += ' ' + noun_elem
                        edits = (0 if det_elem == det_token else 1) + \
                            (0 if adj_token1 is None or adj1_elem == adj_token1.token else 1) + \
                            (0 if adj_token2 is None or adj2_elem == adj_token2.token else 1) + \
                            (0 if noun_elem == noun_token else 1)
                        if edits == 0:
                            continue
                        key = (elem, edits)
                        if key not in seen:
                            seen.add(key)
                            result.append(_Suggestion(elem, edits, levenshtein_distance(elem, self.orig_phrase)))

    def _get_orig_phrase(self):
        orig_elem = self.determiner_token.token
        if self.adj_token1 is not None:
            orig_elem += ' ' + self.adj_token1.token
        if self.adj_token2 is not None:
            orig_elem += ' ' + self.adj_token2.token
        orig_elem += ' ' + self.noun_token.token
        return orig_elem


def _replace_vars(template, num, gen, a_case):
    template = template.replace('SIN/PLU', num, 1)
    template = template.replace('MAS/FEM/NEU', gen, 1)
    return template.replace('NOM/AKK/DAT/GEN', a_case, 1)
