"""Pattern based rules. Port of org.languagetool.rules.patterns
AbstractPatternRule, AbstractTokenBasedRule, PatternRule, RegexPatternRule
and org.languagetool.tagging.disambiguation.rules.DisambiguationPatternRule.
"""

import threading

from ..rules.base import Rule, TYPE_HINT, TYPE_OTHER


class AbstractPatternRule(Rule):

    def __init__(self, id, description, language, pattern_tokens=None, get_unified=False):
        super().__init__()
        if id is None:
            raise ValueError('id cannot be None')
        if description is None:
            raise ValueError('description cannot be None, rule id: %s' % id)
        self._id = id
        self.description = description
        self.language = language
        self.get_unified = get_unified
        self.sub_id = None
        self.start_position_correction = 0
        self.end_position_correction = 0
        self.suggestion_matches = []
        self.suggestion_matches_out_msg = []
        self.suggestions_out_msg = ''
        self.anti_patterns = []
        self.filter = None
        self.filter_args = None
        self.message = ''
        self.source_file = None
        self.match_type = None
        self.adjust_suggestion_case = True
        self.xml_line_number = -1
        if pattern_tokens is not None:
            self.pattern_tokens = list(pattern_tokens)
            self.test_unification = any(t.is_unified() for t in self.pattern_tokens)
            self.sent_start = bool(self.pattern_tokens) and self.pattern_tokens[0].is_sentence_start()
            if not self.test_unification:
                self.groups_or_unification = any(t.has_and_group() for t in self.pattern_tokens)
            else:
                self.groups_or_unification = True
        else:
            self.pattern_tokens = None
            self.groups_or_unification = False
            self.sent_start = False
            self.test_unification = False

    def get_id(self):
        return self._id

    def get_sub_id(self):
        return self.sub_id

    def get_description(self):
        return self.description

    def get_short_message(self):
        return ''

    def get_anti_patterns(self):
        return self.anti_patterns

    def set_anti_patterns(self, aps):
        self.anti_patterns = list(self.anti_patterns) + list(aps)

    def add_suggestion_match(self, m):
        self.suggestion_matches.append(m)

    def add_suggestion_match_out_msg(self, m):
        self.suggestion_matches_out_msg.append(m)

    def get_type(self):
        if self.match_type is None:
            t = self.loc_quality_issue_type
            if t in ('Style', 'LocaleViolation', 'Register'):
                return TYPE_HINT
            return TYPE_OTHER
        return self.match_type

    def __repr__(self):
        return '%s[%s]' % (self._id, self.sub_id)


class TokenHint:
    __slots__ = ('inflected', 'lower_case_values', 'lower_case_value_set', 'token_index')

    def __init__(self, inflected, possible_values, token_index):
        self.inflected = inflected
        self.token_index = token_index
        vals = []
        seen = set()
        for v in possible_values:
            lv = v.lower()
            if lv not in seen:
                seen.add(lv)
                vals.append(lv)
        self.lower_case_values = tuple(vals)
        self.lower_case_value_set = frozenset(vals)

    def key(self):
        return (self.inflected, self.token_index, self.lower_case_values)

    def _offsets(self, sentence):
        return sentence.lemma_offsets if self.inflected else sentence.token_offsets

    def get_possible_indices(self, sentence):
        offsets = self._offsets(sentence)
        result = None
        need_merge = False
        if len(self.lower_case_value_set) <= len(offsets):
            it = (offsets.get(h) for h in self.lower_case_values)
        else:
            vs = self.lower_case_value_set
            it = (offsets[v] for v in offsets if v in vs)
        for idx in it:
            if idx is not None:
                if result is None:
                    result = idx
                else:
                    if not need_merge:
                        result = list(result)
                        need_merge = True
                    result.extend(idx)
        if result is None:
            return []
        return sorted(set(result)) if need_merge else result

    def can_be_ignored_for(self, sentence):
        offsets = self._offsets(sentence)
        if len(self.lower_case_value_set) <= len(offsets):
            for h in self.lower_case_values:
                if h in offsets:
                    return False
        else:
            vs = self.lower_case_value_set
            for v in offsets:
                if v in vs:
                    return False
        return True


class AbstractTokenBasedRule(AbstractPatternRule):

    def __init__(self, id, description, language, pattern_tokens, get_unified):
        super().__init__(id, description, language, pattern_tokens, get_unified)
        self._init_hints()

    def _init_hints(self):
        pattern_tokens = self.pattern_tokens
        hints_by_key = {}
        anchor = None
        pos_hints = []
        fixed_offset = True
        min_token_count = 0 if (not pattern_tokens or _can_match_sentence_start(pattern_tokens[0])) else 1
        max_span = 0
        bounded = True
        for i, t in enumerate(pattern_tokens):
            if t.get_min_occurrence() > 0:
                min_token_count += 1
            ph = t.calc_pos_hints()
            if ph is not None:
                pos_hints.append(ph)
            if bounded:
                mo = t.max_occurrence
                if t.skip != 0 or mo < 0:
                    bounded = False
                else:
                    max_span += max(1, mo)
            inflected = False
            hints = t.calc_form_hints()
            if hints is None:
                inflected = True
                hints = t.calc_lemma_hints()
            if hints is not None:
                h = TokenHint(inflected, hints, i)
                hints_by_key.setdefault(h.key(), h)
                if fixed_offset and anchor is None:
                    anchor = h
            if fixed_offset and (t.get_min_occurrence() != 1 or t.skip != 0 or t.max_occurrence != 1):
                fixed_offset = False
        if hints_by_key:
            hs = list(hints_by_key.values())
            hs.sort(key=lambda th: (len(th.lower_case_values),
                                    -min((len(v) for v in th.lower_case_values), default=0)))
            self.token_hints = hs
        else:
            self.token_hints = None
        self.anchor_hint = anchor
        self.pos_hints = pos_hints or None
        self.max_span_tokens = max_span if bounded else -1
        self.min_token_count = min(min_token_count, 127)
        from .._base import speedups
        self._native_hints = None
        if speedups is not None:
            hs = tuple((th.inflected, th.lower_case_values, th.lower_case_value_set)
                       for th in (self.token_hints or ()))
            ph = tuple(frozenset(p) for p in self.pos_hints) if self.pos_hints else None
            self._native_hints = speedups.RuleHints(self.min_token_count, hs, ph)

    def is_interpret_pos_tags_pre_disambiguation(self):
        return False

    def can_be_ignored_for(self, sentence):
        nh = self._native_hints
        if nh is not None:
            return nh.ignorable(len(sentence.non_blank_tokens), sentence.token_offsets, sentence.lemma_offsets,
                                sentence.pos_tag_set, not self.is_interpret_pos_tags_pre_disambiguation())
        if len(sentence.non_blank_tokens) < self.min_token_count:
            return True
        if self.token_hints is not None:
            for th in self.token_hints:
                if th.can_be_ignored_for(sentence):
                    return True
        if self.pos_hints is not None and not self.is_interpret_pos_tags_pre_disambiguation():
            tags = sentence.pos_tag_set
            for ph in self.pos_hints:
                if tags.isdisjoint(ph):
                    return True
        return False


def _can_match_sentence_start(t):
    return t.is_sentence_start() or t.negation or not t.has_string_that_must_match()


class PatternRule(AbstractTokenBasedRule):

    def __init__(self, id, language, pattern_tokens, description, message, short_message, suggestions_out_msg='',
                 is_member=False, interpret_pos_tags_pre_disambiguation=False):
        super().__init__(id, description, language, pattern_tokens, False)
        self.message = message
        self.short_message = short_message
        self.suggestions_out_msg = suggestions_out_msg or ''
        self.is_member_of_disjunctive_set = is_member
        self.interpret_pos_tags_pre_disambiguation = interpret_pos_tags_pre_disambiguation
        element_no = []
        prev_name = ''
        cnt = 0
        loop_cnt = 0
        use_list = False
        n = len(self.pattern_tokens)
        for t in pattern_tokens:
            if t.is_part_of_phrase():
                cur_name = t.phrase_name
                if not prev_name or prev_name == cur_name:
                    cnt += 1
                    use_list = True
                else:
                    element_no.append(cnt)
                    cur_name = ''
                    cnt = 0
                prev_name = cur_name
                loop_cnt += 1
                if loop_cnt == n and prev_name:
                    element_no.append(cnt)
            else:
                if cnt > 0:
                    element_no.append(cnt)
                element_no.append(1)
                loop_cnt += 1
        self.element_no = element_no
        self.use_list = use_list
        # the matchers keep state while matching, so every thread gets its
        # own one (Java creates a new PatternRuleMatcher for every match())
        self._matchers = threading.local()

    def get_short_message(self):
        return self.short_message

    def is_interpret_pos_tags_pre_disambiguation(self):
        return self.interpret_pos_tags_pre_disambiguation

    def is_with_complex_phrase(self):
        return self.is_member_of_disjunctive_set

    def match(self, sentence):
        if self.can_be_ignored_for(sentence):
            return []
        matcher = self.get_matcher()
        matches = matcher.match(sentence)
        if matches and self.anti_patterns:
            immunized = self.get_sentence_with_immunization(sentence)
            for t in immunized.tokens:
                if t.immunized:
                    return matcher.match(immunized)
        return matches

    def get_matcher(self):
        m = getattr(self._matchers, 'm', None)
        if m is None:
            from .matcher import PatternRuleMatcher
            m = self._matchers.m = PatternRuleMatcher(self, self.use_list)
        return m

    def estimate_context_for_sure_match(self):
        from ..analysis import SENTENCE_END_TAGNAME
        extend_after_marker = 0
        marker_seen = False
        for t in self.pattern_tokens:
            if marker_seen and not t.inside_marker:
                extend_after_marker += 1
            if t.get_pos_tag() == SENTENCE_END_TAGNAME:
                extend_after_marker += 1
            if t.inside_marker:
                marker_seen = True
            if t.skip == -1:
                return -1
            extend_after_marker += t.skip
        lengths = [len(ap.pattern_tokens) for ap in self.anti_patterns]
        longest = max(lengths) if lengths else 0
        longest_skip = 0
        for ap in self.anti_patterns:
            for t in ap.pattern_tokens:
                if t.skip == -1:
                    return -1
                longest_skip = max(longest_skip, t.skip)
        return extend_after_marker + max(longest, longest + longest_skip)

    def to_pattern_string(self):
        return ', '.join(repr(t) for t in self.pattern_tokens)


class RegexPatternRule(AbstractPatternRule):

    MAX_SENT_LENGTH = 2000

    def __init__(self, id, description, message, short_message, suggestions_out_msg, language, regex,
                 regexp_mark, case_sensitive):
        super().__init__(id, description, language)
        self.message = message
        if isinstance(regex, tuple):
            self._pattern_src = regex
            self._pattern = None
        else:
            self._pattern_src = None
            self._pattern = regex
        self.short_message = short_message or ''
        self.suggestions_out_msg = suggestions_out_msg or ''
        self.mark_group = regexp_mark
        self.case_sensitive = case_sensitive
        self.regex_filter = None

    @property
    def pattern(self):
        p = self._pattern
        if p is None:
            from .. import jregex
            p = self._pattern = jregex.compile(*self._pattern_src)
        return p

    def get_short_message(self):
        return self.short_message

    def match(self, sentence):
        from .matcher import match_regex_rule
        return match_regex_rule(self, sentence)

    def estimate_context_for_sure_match(self):
        return -1


# disambiguator actions
ADD, FILTER, REMOVE, REPLACE, UNIFY, IMMUNIZE, IGNORE_SPELLING, FILTERALL, ADDCHUNK = (
    'ADD', 'FILTER', 'REMOVE', 'REPLACE', 'UNIFY', 'IMMUNIZE', 'IGNORE_SPELLING', 'FILTERALL', 'ADDCHUNK')
DISAMBIGUATOR_ACTIONS = frozenset((ADD, FILTER, REMOVE, REPLACE, UNIFY, IMMUNIZE, IGNORE_SPELLING, FILTERALL,
                                   ADDCHUNK))


class DisambiguationPatternRule(AbstractTokenBasedRule):

    def __init__(self, id, description, language, pattern_tokens, disambiguated_pos, pos_select, action):
        super().__init__(id, description, language, pattern_tokens, True)
        if disambiguated_pos is None and pos_select is None and action not in (
                UNIFY, ADD, REMOVE, IMMUNIZE, REPLACE, FILTERALL, IGNORE_SPELLING, ADDCHUNK):
            raise ValueError('disambiguated POS cannot be null with posSelect == null and ' + action)
        self.disambiguated_pos = disambiguated_pos
        self.match_element = pos_select
        self.action = action
        self.new_token_readings = None
        self.examples = []
        self.untouched_examples = []
        self.message = ''
        self.suggestions_out_msg = ''
        self.unifier_config = None
        # the replacers keep state while matching, so every thread gets its
        # own one (Java creates a new DisambiguationPatternRuleReplacer for
        # every replace())
        self._replacers = threading.local()

    def set_new_interpretations(self, readings):
        self.new_token_readings = list(readings)

    def replace(self, sentence):
        if self.can_be_ignored_for(sentence):
            return sentence
        r = getattr(self._replacers, 'r', None)
        if r is None:
            from .matcher import DisambiguationPatternRuleReplacer
            r = self._replacers.r = DisambiguationPatternRuleReplacer(self)
        return r.replace(sentence)


def make_anti_patterns(pattern_list, language):
    """Rule.makeAntiPatterns: an immunizing DisambiguationPatternRule for
    every list of pattern tokens (Rule.cacheAntiPatterns memoizes the
    result, callers keep it)"""
    return [DisambiguationPatternRule('INTERNAL_ANTIPATTERN', '(no description)', language, list(pattern_tokens),
                                      None, None, IMMUNIZE) for pattern_tokens in pattern_list]
