"""The pattern matching engine.

Port of org.languagetool.rules.patterns.AbstractPatternRulePerformer,
PatternTokenMatcher, PatternRuleMatcher, RuleFilterEvaluator,
RegexPatternRule.match and
org.languagetool.tagging.disambiguation.rules.DisambiguationPatternRuleReplacer.
"""

import regex

from .. import jregex
from .._base import speedups
from ..analysis import AnalyzedToken, AnalyzedTokenReadings, AnalyzedSentence
from ..rules.base import RuleMatch, rule_with_max_filter, SUGGESTION_START_TAG, SUGGESTION_END_TAG
from ..tools import (is_all_uppercase, starts_with_uppercase, is_positive_number, add_space, is_empty)
from . import rules as R
from .match import Match, convert_case, INCLUDE_NONE, NONE as CASE_NONE

MISTAKE = '<mistake/>'
# Pattern.compile("\\s+") of RuleFilterEvaluator (Java's \s is ASCII whitespace only, e.g. not U+2006)
_WS = regex.compile(r'[ \t\n\x0B\f\r]+')
PLEASE_SPELL_ME = '<pleasespellme/>'

_ALLOWED_CHARS = '[^<>()]*?'
_SUGGESTION_PATTERN_SUPPRESS = regex.compile(
    regex.escape(SUGGESTION_START_TAG + PLEASE_SPELL_ME) + _ALLOWED_CHARS + r'(\(' + _ALLOWED_CHARS + r'\)|' +
    regex.escape(MISTAKE) + ')' + _ALLOWED_CHARS + regex.escape(SUGGESTION_END_TAG))
_WHITESPACE_OR_PUNCT = regex.compile(r'[\s,:;.!?][^\n\r\x85  ]*')
_TAG_AND_PLEASE_SPELL_ME = SUGGESTION_START_TAG + PLEASE_SPELL_ME


class PatternTokenMatcher:
    """Port of PatternTokenMatcher: wraps a PatternToken, resolving token
    references and keeping track of AND groups."""

    __slots__ = ('base', 'pattern_token', 'and_group', 'and_group_check')

    def __init__(self, pattern_token):
        self.base = pattern_token
        self.pattern_token = pattern_token
        self.and_group = [PatternTokenMatcher(t) for t in pattern_token.and_group] if pattern_token.and_group else None
        self.and_group_check = None

    def resolve_reference(self, first_match_token, tokens, language):
        base = self.base
        if base.token_reference is not None:
            ref_pos = first_match_token + base.token_reference.token_ref
            if ref_pos < len(tokens):
                self.pattern_token = base.compile(tokens[ref_pos], language.synthesizer)

    def is_matched(self, token):
        matched = self.pattern_token.is_matched(token)
        if self.pattern_token.and_group is not None:
            self.and_group_check[0] = self.and_group_check[0] or matched
        return matched

    def prepare_and_group(self, first_match_token, tokens, language):
        if self.base.and_group is not None:
            for m in self.and_group:
                m.resolve_reference(first_match_token, tokens, language)
            self.and_group_check = [False] * (len(self.pattern_token.and_group) + 1)

    def add_member_and_group(self, token):
        if self.pattern_token.and_group is not None:
            check = self.and_group_check
            for i, m in enumerate(self.and_group):
                if not check[i + 1]:
                    if m.is_matched(token):
                        check[i + 1] = True

    def check_and_group(self, previous_value):
        if self.pattern_token.and_group is not None:
            return all(self.and_group_check)
        return previous_value


class AbstractPatternRulePerformer:

    def __init__(self, rule, unifier_config):
        self.rule = rule
        self.unifier_config = unifier_config
        self.unifier = None
        self.unified_tokens = None
        self.prev_matched = False
        self.matchers = [PatternTokenMatcher(t) for t in rule.pattern_tokens]
        self.pattern_size = len(self.matchers)
        self.min_occur_correction = sum(1 for t in rule.pattern_tokens if t.get_min_occurrence() == 0)
        if rule.test_unification:
            self.to_unify = {}
            self.neutral_readings = {}
        else:
            self.to_unify = self.neutral_readings = None
        self._compiled = None

    def _compile(self, check_immunized, element_no):
        """Prepare matching with the C extension, if possible."""
        rule = self.rule
        if speedups is None:
            return
        has_refs = False
        for t in rule.pattern_tokens:
            if t.token_reference is not None:
                has_refs = True
            if t.and_group:
                for a in t.and_group:
                    if a.token_reference is not None:
                        has_refs = True
        self._compiled = speedups.CompiledPattern(tuple(rule.pattern_tokens), self.min_occur_correction,
                                                  bool(rule.groups_or_unification), check_immunized, element_no)
        # the callbacks of CompiledPattern.match (not stored in the CompiledPattern, that would be a reference
        # cycle)
        self._c_unify = self._test_unification_lists if rule.test_unification else None
        self._c_resolver = self._resolve if has_refs else None

    def c_spec(self):
        """The entry of a speedups.MatcherTable (see there) for the rule"""
        compiled = self._compiled
        if compiled is None:
            return None
        rule = self.rule
        anchor = rule.anchor_hint
        if anchor is None:
            a_inflected, a_values, a_set, a_index = False, None, None, 0
        else:
            a_inflected, a_values, a_set, a_index = (anchor.inflected, anchor.lower_case_values,
                                                     anchor.lower_case_value_set, anchor.token_index)
        return (compiled, self._c_on_match, self._c_finish, self._c_unify, self._c_resolver, a_inflected, a_values,
                a_set, a_index, bool(rule.sent_start), self.is_interpret_pos_tags_pre_disambiguation(),
                self.pattern_size, self.min_occur_correction)

    def _resolve(self, pattern_token, token):
        """PatternTokenMatcher.resolve_reference for CompiledPattern"""
        return pattern_token.compile(token, self.rule.language.synthesizer)

    def _test_unification_lists(self, to_unify, neutral):
        """test_unification() for CompiledPattern: to_unify / neutral are
        the readings to unify and the neutral readings as lists, indexed by
        the (first) index of the pattern token"""
        pts = self.rule.pattern_tokens
        self.to_unify = {id(pts[i]): v for i, v in enumerate(to_unify) if v is not None}
        self.neutral_readings = {id(pts[i]): v for i, v in enumerate(neutral) if v is not None}
        self.unified_tokens = None
        return self.test_unification()

    def is_interpret_pos_tags_pre_disambiguation(self):
        return isinstance(self.rule, R.PatternRule) and self.rule.interpret_pos_tags_pre_disambiguation

    def do_match(self, sentence, tokens, consumer, min_start=0, max_start=2 ** 31):
        rule = self.rule
        anchor = rule.anchor_hint
        if anchor is None or self.is_interpret_pos_tags_pre_disambiguation():
            anchor_indices = None
        else:
            anchor_indices = anchor.get_possible_indices(sentence)
        positions = [0] * self.pattern_size
        if rule.sent_start:
            limit = 1
        else:
            limit = max(0, len(tokens) - self.pattern_size + 1) + self.min_occur_correction
        compiled = self._compiled
        if compiled is not None:
            if anchor_indices is not None:
                ti = anchor.token_index
                starts = [ai - ti for ai in anchor_indices if min_start <= ai - ti <= max_start and
                          0 <= ai - ti < limit]
                if starts:
                    compiled.match(tokens, starts, consumer, self._c_unify, self._c_resolver)
            else:
                lo, hi = max(0, min_start), min(limit - 1, max_start)
                if lo <= hi:
                    compiled.match(tokens, (lo, hi), consumer, self._c_unify, self._c_resolver)
            return
        if anchor_indices is not None:
            ti = anchor.token_index
            for ai in anchor_indices:
                i = ai - ti
                if min_start <= i <= max_start and 0 <= i < limit:
                    self.match_from(i, tokens, consumer, positions)
        else:
            for i in range(max(0, min_start), min(limit - 1, max_start) + 1):
                self.match_from(i, tokens, consumer, positions)

    def match_from(self, start_index, tokens, consumer, positions):
        matcher = None
        skip_shift_total = 0
        all_match = False
        self.unified_tokens = None
        matching_tokens = 0
        first_match_token = -1
        last_match_token = -1
        first_marker = -1
        last_marker = -1
        prev_skip_next = 0
        if self.to_unify is not None:
            self.to_unify.clear()
            self.neutral_readings.clear()
        min_occur_skip = 0
        matchers = self.matchers
        pattern_size = self.pattern_size
        ntokens = len(tokens)
        language = self.rule.language
        moc = self.min_occur_correction
        for k in range(pattern_size):
            prev_matcher = matcher
            matcher = matchers[k]
            matcher.resolve_reference(first_match_token, tokens, language)
            next_pos = start_index + k + skip_shift_total - min_occur_skip
            self.prev_matched = False
            if prev_skip_next + next_pos >= ntokens or prev_skip_next < 0:
                prev_skip_next = ntokens - (next_pos + 1)
            max_tok = min(next_pos + prev_skip_next, ntokens - (pattern_size - k) + moc)
            pt = matcher.base
            for m in range(next_pos, max_tok + 1):
                all_match = self.test_all_readings(tokens, matcher, prev_matcher, m, first_match_token,
                                                   prev_skip_next)
                if pt.may_be_omitted:
                    found_next = False
                    for k2 in range(k + 1, pattern_size):
                        nxt = matchers[k2]
                        if self.test_all_readings(tokens, nxt, matcher, m, first_match_token, prev_skip_next):
                            all_match = True
                            min_occur_skip += 1
                            positions[matching_tokens] = 0
                            matching_tokens += 1
                            found_next = True
                            break
                        elif not nxt.base.may_be_omitted:
                            break
                    if found_next:
                        break
                if all_match:
                    skip_for_max = self.skip_max_tokens(tokens, matcher, first_match_token, prev_skip_next,
                                                        prev_matcher, m, pattern_size - k - 1)
                    last_match_token = m + skip_for_max
                    skip_shift = last_match_token - next_pos
                    positions[matching_tokens] = skip_shift + 1
                    matching_tokens += 1
                    prev_skip_next = self.translate_element_no(pt.skip)
                    skip_shift_total += skip_shift
                    if first_match_token == -1:
                        first_match_token = last_match_token - skip_for_max
                    if first_marker == -1 and pt.inside_marker:
                        first_marker = last_match_token - skip_for_max
                    if pt.inside_marker:
                        last_marker = last_match_token
                    break
            if not all_match:
                break
        if all_match and matching_tokens == pattern_size and self.test_unification():
            consumer(positions, first_match_token, last_match_token, first_marker, last_marker)

    def test_all_readings(self, tokens, matcher, prev_element, token_no, first_match_token, prev_skip_next):
        any_matched = False
        atr = tokens[token_no]
        readings = atr.readings
        nreadings = len(readings)
        rule = self.rule
        matcher.prepare_and_group(first_match_token, tokens, rule.language)
        readings_to_unify = [] if self.to_unify is not None else None
        pt = matcher.base
        cur_pt = matcher.pattern_token
        prev_has_cn = prev_element is not None and prev_element.base.has_current_or_next_exceptions()
        groups_or_unification = rule.groups_or_unification
        for i in range(nreadings):
            match_token = readings[i]
            self.prev_matched = self.prev_matched or (prev_skip_next > 0 and prev_element is not None and
                                                      prev_element.pattern_token.is_matched_by_scope_next_exception(
                                                          match_token))
            self.prev_matched = self.prev_matched or (prev_skip_next == 0 and token_no <= len(tokens) - 2 and
                                                      cur_pt.is_matched_by_scope_next_exception(
                                                          tokens[token_no + 1].readings[0]))
            if self.prev_matched:
                return False
            reading_tested = False
            reading_matches = False
            if not any_matched:
                any_matched = reading_matches = matcher.is_matched(match_token)
                reading_tested = True
            if not any_matched and not prev_has_cn:
                if pt.get_pos_tag() is None:
                    if pt.inflected:
                        if atr.has_same_lemmas:
                            return False
                    else:
                        return False
                elif not pt.get_pos_negation() and not atr.is_tagged():
                    return False
            if groups_or_unification:
                if not reading_tested:
                    reading_matches = matcher.is_matched(match_token)
                is_last = i + 1 == nreadings
                if reading_matches and readings_to_unify is not None and pt.is_unified() and \
                        not pt.unification_neutral:
                    readings_to_unify.append(match_token)
                matcher.add_member_and_group(match_token)
                any_matched = any_matched and (not is_last or matcher.check_and_group(True))
        if any_matched:
            cpt = matcher.pattern_token
            for r in readings:
                if cpt.is_exception_matched_completely(r):
                    return False
            if token_no > 0 and cpt.has_previous_exception():
                if cpt.is_matched_by_previous_exception_readings(tokens[token_no - 1]):
                    return False
            if pt.unification_neutral and self.neutral_readings is not None:
                self.neutral_readings.setdefault(id(pt), []).append(atr)
        chunk = pt.chunk_tag
        if chunk is not None:
            if chunk.is_regexp:
                has = any(chunk.matches(c) for c in atr.chunk_tags)
            else:
                has = chunk in atr.chunk_tags
            any_matched = any_matched and (has != pt.negation)
        if pt.and_group is not None:
            for e in pt.and_group:
                if e.chunk_tag is not None:
                    any_matched = any_matched and ((e.chunk_tag in atr.chunk_tags) != e.negation)
        if any_matched and readings_to_unify:
            self.to_unify.setdefault(id(pt), []).append(readings_to_unify)
        return any_matched

    def test_unification(self):
        if self.to_unify is None:
            return True
        if self.unifier is None:
            self.unifier = self.unifier_config.create_unifier()
        unifier = self.unifier
        unifier.reset()
        for matcher in self.matchers:
            pt = matcher.base
            neutral = self.neutral_readings.get(id(pt))
            if neutral is not None:
                for atr in neutral:
                    unifier.add_neutral_element(atr)
                continue
            reading_sets = self.to_unify.get(id(pt))
            if reading_sets is None:
                continue
            for readings in reading_sets:
                any_matched = False
                n = len(readings)
                for i in range(n):
                    any_matched = unifier.is_unified(readings[i], pt.unification_features, i == n - 1) or any_matched
                if pt.uni_negation and any_matched:
                    return False
                if pt.last_in_unification and readings is reading_sets[-1]:
                    if not any_matched and not pt.uni_negation:
                        return False
                    if self.rule.get_unified:
                        self.unified_tokens = unifier.get_final_unified()
                    unifier.reset()
        return True

    def skip_max_tokens(self, tokens, matcher, first_match_token, prev_skip_next, prev_element, m, remaining):
        max_skip = 0
        mo = matcher.base.max_occurrence
        max_occ = 2 ** 31 if mo == -1 else mo
        j = 1
        ntokens = len(tokens)
        while j < max_occ and m + j < ntokens - remaining:
            if self.test_all_readings(tokens, matcher, prev_element, m + j, first_match_token, prev_skip_next):
                max_skip += 1
            else:
                break
            j += 1
        return max_skip

    def translate_element_no(self, i):
        return i


class PatternRuleMatcher(AbstractPatternRulePerformer):

    def __init__(self, rule, use_list, unifier_config=None):
        if unifier_config is None:
            unifier_config = rule.language.unifier_config
        super().__init__(rule, unifier_config)
        self.use_list = use_list
        self._compile(True, rule.element_no if use_list and isinstance(rule, R.PatternRule) else None)

    def _c_on_match(self, sentence, tokens, scratch, positions, first, last, first_marker, last_marker):
        """the consumer of the matches for the speedups.MatcherTable"""
        return self.create_rule_match(positions, tokens, first, last, first_marker, last_marker, sentence)

    def _c_finish(self, sentence, scratch, matches):
        """the result of PatternRule.match_unchecked() for the
        speedups.MatcherTable"""
        if len(matches) > 1:
            matches = rule_with_max_filter(matches)
        return self.rule.apply_anti_patterns(sentence, matches, self)

    def match(self, sentence, min_start=0, max_start=2 ** 31):
        if self.is_interpret_pos_tags_pre_disambiguation():
            tokens = sentence.non_blank_pre_disambig_tokens
        else:
            tokens = sentence.non_blank_tokens
        matches = []

        def consumer(positions, first, last, first_marker, last_marker):
            rm = self.create_rule_match(positions, tokens, first, last, first_marker, last_marker, sentence)
            if rm is not None:
                matches.append(rm)

        self.do_match(sentence, tokens, consumer, min_start, max_start)
        if len(matches) > 1:
            return rule_with_max_filter(matches)
        return matches

    def test_all_readings(self, tokens, matcher, prev_element, token_no, first_match_token, prev_skip_next):
        if tokens[token_no].immunized:
            return False
        return AbstractPatternRulePerformer.test_all_readings(self, tokens, matcher, prev_element, token_no,
                                                              first_match_token, prev_skip_next)

    def create_rule_match(self, positions, tokens, first_match_token, last_match_token, first_marker,
                          last_marker, sentence):
        rule = self.rule
        err_message = self.format_matches(tokens, positions, first_match_token, rule.message,
                                          rule.suggestion_matches)
        short_message = self.format_matches(tokens, positions, first_match_token, rule.get_short_message(),
                                            rule.suggestion_matches)
        sugg_out = self.format_matches(tokens, positions, first_match_token, rule.suggestions_out_msg,
                                       rule.suggestion_matches_out_msg)
        corrected_st_pos = 0
        if rule.start_position_correction > 0:
            for l in range(min(rule.start_position_correction, len(positions) - 1) + 1):
                corrected_st_pos += positions[l]
            corrected_st_pos -= 1
        idx = first_match_token + corrected_st_pos
        if idx >= len(tokens):
            idx = len(tokens) - 1
        first_tok = tokens[idx]
        input_tokens = [tokens[i].token for i in range(idx, last_match_token + 1)]
        is_input_all_upper = is_all_uppercase(input_tokens)
        preserves = (self._match_preserves_case(rule.suggestion_matches, rule.message) and
                     self._match_preserves_case(rule.suggestion_matches_out_msg, rule.suggestions_out_msg))
        is_all_upper = (is_input_all_upper and (len(first_tok.token.replace("'", '')) > 1 or last_match_token > idx)
                        and preserves)
        is_all_upper = is_all_upper and rule.adjust_suggestion_case
        starts_upper = starts_with_uppercase(first_tok.token) and preserves
        if first_tok.is_sentence_start and len(tokens) > first_match_token + corrected_st_pos + 1:
            first_tok = tokens[first_match_token + corrected_st_pos + 1]
            starts_upper = starts_with_uppercase(first_tok.token)
        starts_upper = starts_upper and rule.adjust_suggestion_case
        if first_marker == -1:
            first_marker = first_match_token
        from_pos = tokens[first_marker].start_pos
        if first_marker >= 1 and (SUGGESTION_START_TAG + ',' in err_message or
                                  SUGGESTION_START_TAG + ',' in sugg_out):
            ptok = tokens[first_marker - 1]
            from_pos = ptok.start_pos + len(ptok.token)
        if last_marker == -1:
            last_marker = last_match_token
        tok = tokens[min(last_marker, len(tokens) - 1)]
        to_pos = tok.end_pos
        if from_pos < to_pos:
            if not (PLEASE_SPELL_ME in err_message and SUGGESTION_START_TAG not in err_message and
                    SUGGESTION_START_TAG not in sugg_out):
                clear_msg = err_message.replace(PLEASE_SPELL_ME, '').replace(MISTAKE, '')
                rm = RuleMatch(rule, sentence, from_pos, to_pos, clear_msg, short_message,
                               pattern_from_pos=tokens[first_match_token].start_pos,
                               pattern_to_pos=tokens[last_match_token].end_pos,
                               start_with_uppercase=starts_upper, is_all_uppercase=is_all_upper,
                               suggestions_out_msg=sugg_out, set_original_error_str=True)
                rm.type = rule.get_type()
                if rule.filter is not None:
                    pattern_tokens = tokens[first_match_token:last_match_token + 1]
                    return run_filter(rule.filter, rule.filter_args, rm, pattern_tokens, first_match_token,
                                      list(positions))
                return rm
        return None

    @staticmethod
    def _match_preserves_case(suggestion_matches, msg):
        if suggestion_matches:
            sug_start = msg.find(SUGGESTION_START_TAG) + len(SUGGESTION_START_TAG)
            if PLEASE_SPELL_ME in msg:
                sug_start += len(PLEASE_SPELL_ME)
            for sm in suggestion_matches:
                if not sm.in_message_only and sm.converts_case() and sug_start < len(msg) and msg[sug_start] == '\\':
                    return False
        return True

    def translate_element_no(self, i):
        if not self.use_list or i < 0:
            return i
        j = 0
        en = self.rule.element_no
        for k in range(i):
            j += en[k]
        return j

    def format_matches(self, token_readings, positions, first_match_tok, error_msg, suggestion_matches):
        if not error_msg or '\\' not in error_msg:
            return _remove_suppress_misspelled(error_msg) if error_msg else error_msg
        suggestion_matches = list(suggestion_matches) if suggestion_matches else suggestion_matches
        error_message = error_msg
        match_counter = 0
        numbers_to_matches = [0] * len(error_msg)
        new_way = False
        processed = 0
        err_len = len(error_message)
        err_marker = error_message.find('\\', processed)
        number_follows = False
        if 0 <= err_marker < err_len - 1:
            number_follows = is_positive_number(error_message[err_marker + 1])
        npos = len(positions)
        while err_marker >= 0 and number_follows:
            backslash_pos = error_message.find('\\', processed)
            if backslash_pos >= 0 and backslash_pos + 1 < len(error_message) and \
                    is_positive_number(error_message[backslash_pos + 1]):
                num_len = 1
                while backslash_pos + num_len < len(error_message) and \
                        error_message[backslash_pos + num_len].isdigit() and \
                        '0' <= error_message[backslash_pos + num_len] <= '9':
                    num_len += 1
                j = int(error_message[backslash_pos + 1:backslash_pos + num_len]) - 1
                rep_token_pos = 0
                next_token_pos = 0
                for l in range(min(j, npos - 1) + 1):
                    rep_token_pos += positions[l]
                if j + 1 < npos:
                    next_token_pos = first_match_tok + rep_token_pos + positions[j + 1]
                if suggestion_matches:
                    if match_counter < len(suggestion_matches):
                        numbers_to_matches[j] = match_counter
                        if j >= npos:
                            matches = self.concat_matches(match_counter, j, first_match_tok + rep_token_pos,
                                                          token_readings, next_token_pos, suggestion_matches)
                        elif positions[j] != 0:
                            matches = self.concat_matches(match_counter, j, first_match_tok + rep_token_pos,
                                                          token_readings, next_token_pos, suggestion_matches)
                        else:
                            matches = ['']
                        left = error_message[:backslash_pos]
                        right = error_message[backslash_pos + num_len:]
                        if len(matches) == 1:
                            if not matches[0]:
                                error_message = _concat_without_extra_space(left, right)
                                processed = len(left)
                            else:
                                error_message = left + matches[0] + right
                                processed = len(left) + len(matches[0])
                        else:
                            error_message = format_multiple_synthesis(matches, left, right)
                        match_counter += 1
                        new_way = True
                    else:
                        suggestion_matches.append(suggestion_matches[numbers_to_matches[j]])
                if not new_way:
                    tok = token_readings[first_match_tok + rep_token_pos - 1].token
                    ref = '\\' + str(j + 1)
                    new_processed = error_message.rfind(ref) + len(tok)
                    error_message = error_message[:processed] + error_message[processed:].replace(ref, tok)
                    processed = new_processed
            err_marker = error_message.find('\\', processed)
            number_follows = False
            err_len = len(error_message)
            if 0 <= err_marker < err_len - 1:
                number_follows = is_positive_number(error_message[err_marker + 1])
        return _remove_suppress_misspelled(error_message)

    def concat_matches(self, start, index, token_index, tokens, next_token_pos, suggestion_matches):
        length = self.phrase_len(index)
        language = self.rule.language
        synth = language.synthesizer
        if length == 1:
            skipped = next_token_pos - token_index
            state = suggestion_matches[start].create_state(synth, tokens, token_index - 1, skipped)
            return state.to_final_string(language)
        match_list = []
        for i in range(length):
            skipped = next_token_pos - (token_index + i)
            state = suggestion_matches[start].create_state(synth, tokens, token_index - 1 + i, skipped)
            match_list.append(state.to_final_string(language))
        return _combine_lists(match_list, [None] * len(match_list), 0, language)

    def phrase_len(self, i):
        en = self.rule.element_no
        if not self.use_list or i > len(en) - 1:
            return 1
        return en[i]


def _combine_lists(inp, output, r, lang):
    out = []
    if r == len(inp):
        sb = []
        for k in range(len(output)):
            sb.append(output[k])
            if k < len(output) - 1:
                sb.append(add_space(output[k + 1], lang.short_code))
        out.append(''.join(sb))
    else:
        for c in range(len(inp[r])):
            output[r] = inp[r][c]
            out.extend(_combine_lists(inp, output, r + 1, lang))
    return out


def _concat_without_extra_space(left, right):
    if (left.endswith(' ') and right.startswith('</suggestion>')) or \
            (left.endswith(' ') and _WHITESPACE_OR_PUNCT.fullmatch(right)):
        return left[:-1] + right
    if left.endswith('suggestion>') and right.startswith(' '):
        return left + right[1:]
    return left + right


def _remove_suppress_misspelled(s):
    if PLEASE_SPELL_ME not in s:
        return s
    s = _SUGGESTION_PATTERN_SUPPRESS.sub('', s)
    return s.replace(_TAG_AND_PLEASE_SPELL_ME, SUGGESTION_START_TAG)


def format_multiple_synthesis(matches, left, right):
    suggestion_left = ''
    suggestion_right = ''
    right_new = right
    s_pos = left.rfind(SUGGESTION_START_TAG)
    if s_pos >= 0:
        suggestion_left = left[s_pos + len(SUGGESTION_START_TAG):]
    if not suggestion_left:
        error_message = left
    else:
        error_message = left[:left.rfind(SUGGESTION_START_TAG)] + SUGGESTION_START_TAG
    r_pos = right.find(SUGGESTION_END_TAG)
    if r_pos >= 0:
        suggestion_right = right[:r_pos]
    if suggestion_right:
        right_new = right[right.find(SUGGESTION_END_TAG):]
    last_left_sug_end = left.find(SUGGESTION_END_TAG)
    last_left_sug_start = left.rfind(SUGGESTION_START_TAG)
    sb = [error_message]
    for z, m in enumerate(matches):
        sb.append(suggestion_left)
        sb.append(m)
        sb.append(suggestion_right)
        if z < len(matches) - 1 and last_left_sug_end < last_left_sug_start:
            sb.append(SUGGESTION_END_TAG)
            sb.append(', ')
            sb.append(SUGGESTION_START_TAG)
    sb.append(right_new)
    return ''.join(sb)


# ---------------------------------------------------------------------------
# filters

def _skip_corrected_reference(positions, ref):
    corrected = 0
    for i, p in enumerate(positions):
        if i >= ref:
            break
        corrected += p
    return corrected - 1


def resolve_filter_arguments(filter_args, pattern_tokens, pattern_token_pos, positions):
    result = {}
    for arg in _WS.split(filter_args.strip(' \t\n\x0B\f\r')):
        if not arg:
            continue
        d = arg.find(':')
        if d == -1:
            raise ValueError("Invalid syntax for key/value, expected 'key:value', got: %r" % arg)
        key, val = arg[:d], arg[d + 1:]
        if val.startswith('\\'):
            ref = int(val.replace('\\', ''))
            if ref > len(positions):
                raise ValueError('Your reference number %d is bigger than the number of tokens: %d' % (
                    ref, len(positions)))
            cr = _skip_corrected_reference(positions, ref)
            if cr >= len(pattern_tokens):
                raise ValueError('Your reference number %d is bigger than number of matching tokens: %d' % (
                    ref, len(pattern_tokens)))
            if key in result:
                raise ValueError("Duplicate key '%s'" % key)
            result[key] = pattern_tokens[cr].token
        else:
            result[key] = val
    return result


def run_filter(rule_filter, filter_args, rule_match, pattern_tokens, pattern_token_pos, positions):
    args = resolve_filter_arguments(filter_args or '', pattern_tokens, pattern_token_pos, positions)
    return rule_filter.accept_rule_match(rule_match, args, pattern_token_pos, pattern_tokens, positions)


# ---------------------------------------------------------------------------
# regex rules

_SUGG_PATTERN = regex.compile(r'<suggestion>(.*?)</suggestion>')
_MATCH_PATTERN = regex.compile(r'\\\d')
MATCHES_IN_SUGGESTIONS_NUMBERED_FROM = 0


def _clause_positions(pattern, message):
    return [(m.start(), m.end()) for m in pattern.finditer(message)]


def _process_message(rule, m, message, back_refs, suggestions, matches):
    closest = -1
    all_passed = not suggestions
    if suggestions:
        closest = 0
    out = []
    start_part = 0
    for i, (left, right) in enumerate(back_refs):
        while not all_passed and left > suggestions[closest][1]:
            closest += 1
            if closest == len(suggestions):
                all_passed = True
        inside = not all_passed and left >= suggestions[closest][0]
        ref_no = int(message[left:right].split('\\')[1])
        actual = ref_no - (MATCHES_IN_SUGGESTIONS_NUMBERED_FROM if inside else 0)
        value = m.group(actual)
        if value is None:
            value = ''
        cur = matches[i]
        if cur.regex_replace is not None:
            sugg = jregex.java_replace(cur.regex_match, cur.regex_replace, value, count=1)
            sugg = convert_case(cur.case_conversion, sugg, value, rule.language.short_code)
        else:
            sugg = value
        out.append(message[start_part:left])
        out.append(sugg)
        start_part = right
    out.append(message[start_part:])
    return ''.join(out)


def match_regex_rule(rule, sentence):
    text = sentence.text
    if len(text) > rule.MAX_SENT_LENGTH:
        return []
    pattern = rule.pattern
    m = pattern.search(text)
    if m is None:
        return []
    message = rule.message
    sugg_in_msg = _clause_positions(_SUGG_PATTERN, message)
    refs_in_msg = _clause_positions(_MATCH_PATTERN, message)
    out_msg = rule.suggestions_out_msg
    sugg_in_out = _clause_positions(_SUGG_PATTERN, out_msg)
    refs_in_out = _clause_positions(_MATCH_PATTERN, out_msg)
    matches = []
    start_pos = 0
    n = len(text)
    while start_pos <= n:
        if start_pos > 0:
            m = pattern.search(text, start_pos)
            if m is None:
                break
        mark_start, mark_end = m.start(rule.mark_group), m.end(rule.mark_group)
        pmsg = _process_message(rule, m, message, refs_in_msg, sugg_in_msg, rule.suggestion_matches)
        pout = _process_message(rule, m, out_msg, refs_in_out, sugg_in_out, rule.suggestion_matches_out_msg)
        starts_upper = m.start() == 0 and n > 0 and text[0].isupper()
        if mark_end > mark_start:
            rm = RuleMatch(rule, sentence, mark_start, mark_end, pmsg, rule.short_message,
                           pattern_from_pos=m.start(), pattern_to_pos=m.end(), start_with_uppercase=starts_upper,
                           is_all_uppercase=False, suggestions_out_msg=pout, set_original_error_str=True)
            if rule.regex_filter is not None:
                args = {}
                for arg in _WS.split(rule.filter_args or ''):
                    if not arg:
                        continue
                    d = arg.find(':')
                    if d == -1:
                        raise ValueError("Invalid syntax for key/value, expected 'key:value', got: %r" % arg)
                    args[arg[:d]] = arg[d + 1:]
                if rule.regex_filter.accept_rule_match(rm, args, sentence, m) is not None:
                    matches.append(rm)
            else:
                matches.append(rm)
        start_pos = m.end() if m.end() > m.start() else m.end() + 1
    return matches


# ---------------------------------------------------------------------------
# disambiguation

class DisambiguationPatternRuleReplacer(AbstractPatternRulePerformer):

    def __init__(self, rule):
        super().__init__(rule, rule.unifier_config or rule.language.disambiguation_unifier_config)
        self._anti_matchers = None
        self._compile(False, None)

    def replace(self, sentence):
        tokens = sentence.non_blank_tokens
        scratch = []

        def consumer(positions, first, last, first_marker, last_marker):
            self._c_on_match(sentence, tokens, scratch, positions, first, last, first_marker, last_marker)

        self.do_match(sentence, tokens, consumer)
        return self._c_finish(sentence, scratch, None)

    def _c_on_match(self, sentence, tokens, scratch, positions, first, last, first_marker, last_marker):
        """the consumer of the matches of replace() (also called by the
        speedups.MatcherTable): scratch is [the new tokens, whether they were
        changed] (empty at the start)"""
        if not scratch:
            scratch.append(sentence.tokens)
            scratch.append(False)
        rfrom = tokens[first].start_pos if 0 <= first < len(tokens) else -1
        rto = tokens[last].end_pos if 0 <= last < len(tokens) else -1
        matching_tokens = sum(1 for p in positions if p != 0)
        if self._keep_despite_filter(tokens, positions, first, last) and \
                self._keep_by_disambig(sentence, rfrom, rto, first, last):
            if not scratch[1]:
                scratch[0] = list(scratch[0])
            scratch[0] = self.execute_action(sentence, scratch[0], self.unified_tokens, first, last_marker,
                                             matching_tokens, positions)
            scratch[1] = True

    def _c_finish(self, sentence, scratch, results):
        """the result of replace()"""
        if scratch and scratch[1]:
            action = self.rule.action
            readings_unchanged = action in (R.IMMUNIZE, R.IGNORE_SPELLING)
            previous = None if action == R.ADD else sentence
            return AnalyzedSentence(scratch[0], sentence.tokens, previous, readings_unchanged)
        return sentence

    def _keep_by_disambig(self, sentence, rfrom, rto, first, last):
        aps = self.rule.anti_patterns
        if not aps:
            return True
        if self._anti_matchers is None:
            cfg = self.unifier_config
            self._anti_matchers = [PatternRuleMatcher(ap, False, cfg) for ap in aps]
        for ap, am in zip(aps, self._anti_matchers):
            if not ap.can_be_ignored_for(sentence):
                ms = ap.max_span_tokens
                min_start = 0 if ms < 0 else max(0, first - ms)
                max_start = last
                for dm in am.match(sentence, min_start, max_start):
                    if (dm.from_pos <= rfrom and dm.to_pos >= rfrom) or \
                            (dm.from_pos <= rto and dm.to_pos >= rto) or \
                            (dm.from_pos >= rfrom and dm.to_pos <= rto):
                        return False
        return True

    def _keep_despite_filter(self, tokens, positions, first, last):
        f = self.rule.filter
        if f is not None:
            pos = list(positions)
            args = resolve_filter_arguments(self.rule.filter_args or '', tokens, first, pos)
            relevant = tokens[first:last + 1]
            return f.matches(args, relevant, first, pos)
        return True

    def execute_action(self, sentence, wh_tokens, unified_tokens, first_match_token, last_match_token,
                       matching_tokens, positions):
        rule = self.rule
        corrected_st_pos = 0
        spc = rule.start_position_correction
        epc = rule.end_position_correction
        mtwc = matching_tokens
        npos = len(positions)
        if spc > 0:
            corrected_st_pos -= 1
            l = 0
            while l <= spc and l < npos:
                corrected_st_pos += positions[l]
                l += 1
            w = spc
            for j in range(w + 1):
                if j < npos and positions[j] == 0:
                    spc -= 1
        if epc < 0:
            for d in range(spc, npos):
                if positions[d] == 0:
                    epc += 1
        if last_match_token != -1:
            max_pos_corr = max((last_match_token + 1 - (first_match_token + corrected_st_pos)) - matching_tokens, 0)
            mtwc += max_pos_corr
        orig = sentence.get_original_position
        from_pos = orig(first_match_token + corrected_st_pos)
        action = rule.action
        new_readings = rule.new_token_readings
        match_element = rule.match_element
        dpos = rule.disambiguated_pos
        count = mtwc - spc + epc
        synth = rule.language.synthesizer
        full_id = rule.get_full_id()
        if action == R.UNIFY:
            if unified_tokens is not None and len(unified_tokens) == count:
                if wh_tokens[orig(first_match_token + corrected_st_pos + len(unified_tokens) - 1)].is_sentence_end:
                    unified_tokens[-1].set_sentence_end()
                for i in range(len(unified_tokens)):
                    position = orig(first_match_token + corrected_st_pos + i)
                    wh_tokens[position] = AnalyzedTokenReadings.from_old(wh_tokens[position],
                                                                         unified_tokens[i].readings, full_id)
        elif action == R.REMOVE:
            if new_readings:
                if len(new_readings) == count:
                    for i in range(len(new_readings)):
                        position = orig(first_match_token + corrected_st_pos + i)
                        wh_tokens[position].remove_reading(new_readings[i], full_id)
            elif not is_empty(dpos):
                p = jregex.compile(dpos)
                tmp = list(wh_tokens[from_pos].readings)
                for at in tmp:
                    if at.pos_tag is not None and p.fullmatch(at.pos_tag):
                        position = orig(first_match_token + corrected_st_pos)
                        wh_tokens[position].remove_reading(at, full_id)
        elif action == R.ADD:
            if new_readings is not None and len(new_readings) == count:
                for i in range(len(new_readings)):
                    position = orig(first_match_token + corrected_st_pos + i)
                    nr = new_readings[i]
                    token = wh_tokens[position].token if not nr.token else nr.token
                    lemma = token if nr.lemma is None else nr.lemma
                    new_tok = AnalyzedToken(token, nr.pos_tag, lemma)
                    exists = False
                    for ex in wh_tokens[position].readings:
                        if ex.token == new_tok.token and ex.pos_tag == new_tok.pos_tag and ex.lemma == new_tok.lemma:
                            exists = True
                            break
                    if not exists:
                        wh_tokens[position].add_reading(new_tok, full_id)
        elif action == R.ADDCHUNK:
            if new_readings is not None and len(new_readings) == count:
                from ..chunking import ChunkTag
                for i in range(len(new_readings)):
                    position = orig(first_match_token + corrected_st_pos + i)
                    tags = list(wh_tokens[position].chunk_tags)
                    nc = ChunkTag(new_readings[i].pos_tag)
                    if nc not in tags:
                        tags.append(nc)
                    wh_tokens[position].set_chunk_tags(tags)
        elif action == R.FILTERALL:
            pts = rule.pattern_tokens
            for i in range(count):
                position = orig(first_match_token + corrected_st_pos + i)
                if positions[i + spc] > 0:
                    pt = pts[i + spc]
                else:
                    k = 1
                    while i + spc + k < len(pts) + epc and positions[i + spc + k] == 0:
                        k += 1
                    pt = pts[i + k + spc]
                tmp_match = Match(pt.get_pos_tag(), None, True, pt.get_pos_tag(), None, CASE_NONE, False, False,
                                  INCLUDE_NONE)
                state = tmp_match.create_state(synth, wh_tokens[position])
                wh_tokens[position] = AnalyzedTokenReadings.from_old(wh_tokens[position],
                                                                     state.filter_readings().readings, full_id)
        elif action == R.IMMUNIZE:
            for i in range(count):
                wh_tokens[orig(first_match_token + corrected_st_pos + i)].immunize(rule.xml_line_number)
        elif action == R.IGNORE_SPELLING:
            for i in range(count):
                wh_tokens[orig(first_match_token + corrected_st_pos + i)].ignore_spelling()
        else:
            if action == R.FILTER and match_element is None:
                tmp_match = Match(dpos, None, True, dpos, None, CASE_NONE, False, False, INCLUDE_NONE)
                new_pos_matches = False
                p = jregex.compile(dpos)
                for r in wh_tokens[from_pos].readings:
                    if not r.has_no_pos_tag and r.pos_tag is not None and p.fullmatch(r.pos_tag):
                        new_pos_matches = True
                        break
                if new_pos_matches:
                    state = tmp_match.create_state(synth, wh_tokens[from_pos])
                    wh_tokens[from_pos] = AnalyzedTokenReadings.from_old(wh_tokens[from_pos],
                                                                         state.filter_readings().readings, full_id)
                return wh_tokens
            # REPLACE (and FILTER with <match>)
            if new_readings:
                if len(new_readings) == count:
                    for i in range(len(new_readings)):
                        position = orig(first_match_token + corrected_st_pos + i)
                        nr = new_readings[i]
                        token = wh_tokens[position].token if nr.token == '' else nr.token
                        lemma = token if nr.lemma is None else nr.lemma
                        at = AnalyzedToken(token, nr.pos_tag, lemma)
                        to_replace = AnalyzedTokenReadings(at, wh_tokens[from_pos].start_pos)
                        wh_tokens[position] = AnalyzedTokenReadings.from_old(wh_tokens[position],
                                                                             to_replace.readings, full_id)
            elif match_element is None:
                lemma = ''
                for at in wh_tokens[from_pos].readings:
                    if at.pos_tag is not None and at.pos_tag == dpos and at.lemma is not None:
                        lemma = at.lemma
                if is_empty(lemma):
                    lemma = wh_tokens[from_pos].readings[0].lemma
                at = AnalyzedToken(wh_tokens[from_pos].token, dpos, lemma)
                to_replace = AnalyzedTokenReadings(at, wh_tokens[from_pos].start_pos)
                wh_tokens[from_pos] = AnalyzedTokenReadings.from_old(wh_tokens[from_pos], to_replace.readings, full_id)
            else:
                state = match_element.create_state(synth, wh_tokens[from_pos])
                wh_tokens[from_pos] = AnalyzedTokenReadings.from_old(wh_tokens[from_pos],
                                                                     state.filter_readings().readings, full_id)
        return wh_tokens
