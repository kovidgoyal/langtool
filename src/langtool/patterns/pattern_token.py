"""Port of org.languagetool.rules.patterns.PatternToken: a part of a pattern,
corresponding to a <token> element in the XML rule files."""

from .._base import PosTokenBase, PatternTokenBase
from ..analysis import SENTENCE_START_TAGNAME
from . import string_matcher
from .string_matcher import StringMatcher

UNKNOWN_TAG = 'UNKNOWN'


def normalize_text_pattern(token):
    from ..tools import trim_whitespace
    return '' if token is None else trim_whitespace(token)


class PosToken(PosTokenBase):
    __slots__ = ()

    def __init__(self, pos_tag, negation=False, matcher=None, regexp=None):
        if regexp is not None:
            matcher = string_matcher.regexp(pos_tag) if regexp and pos_tag is not None else None
        self.pos_tag = pos_tag
        self.negation = negation
        self.pos_pattern = matcher
        if pos_tag is None:
            self.pos_unknown = False
        elif matcher is not None:
            self.pos_unknown = matcher.matches(UNKNOWN_TAG)
        else:
            self.pos_unknown = pos_tag == UNKNOWN_TAG

    def __repr__(self):
        return str(self.pos_tag)


_PT_FIELDS = (
    'inflected', 'negation', 'test_whitespace', 'whitespace_before', 'inside_marker', 'exception_valid_next',
    'may_be_omitted', 'test_string', 'unification_neutral', 'uni_negation', 'last_in_unification',
    'text_matcher', 'pos_token', 'current_and_next_exceptions', 'previous_exceptions',
    'unification_features', 'phrase_name', 'and_group', 'or_group', 'token_reference', 'chunk_tag',
    'skip', 'max_occurrence')


class PatternToken(PatternTokenBase):
    """A token in a pattern. Attribute names mirror the Java fields/flags."""

    __slots__ = ('__weakref__',)

    def __init__(self, token=None, case_sensitive=False, regexp=False, inflected=False, matcher=None):
        if matcher is None:
            matcher = string_matcher.create(normalize_text_pattern(token), regexp, case_sensitive)
        self.inflected = bool(inflected)
        self.negation = False
        self.test_whitespace = False
        self.whitespace_before = False
        self.inside_marker = True
        self.exception_valid_next = False
        self.may_be_omitted = False
        self.unification_neutral = False
        self.uni_negation = False
        self.last_in_unification = False
        self.pos_token = None
        self.current_and_next_exceptions = ()
        self.previous_exceptions = ()
        self.unification_features = None
        self.phrase_name = None
        self.and_group = None
        self.or_group = None
        self.token_reference = None
        self.chunk_tag = None
        self.skip = 0
        self.max_occurrence = 1
        self.set_text_matcher(matcher)

    def clone(self):
        """Shallow copy, like Java's PatternToken.clone()"""
        c = PatternToken.__new__(PatternToken)
        for k in _PT_FIELDS:
            setattr(c, k, getattr(self, k))
        return c

    # --- matching ---

    def is_matched(self, token):
        if self.test_whitespace and self.whitespace_before != token.whitespace_before:
            return False
        pos = self.pos_token
        pos_negation = pos is not None and pos.negation
        if self.test_string:
            if self.inflected:
                test = token.lemma if token.lemma is not None else token.token
            else:
                test = token.token
            return ((self.text_matcher.matches(test) != self.negation)
                    and (self._is_pos_token_matched(token) != pos_negation))
        return (not self.negation) and (self._is_pos_token_matched(token) != pos_negation)

    def _is_pos_token_matched(self, token):
        pos = self.pos_token
        if pos is None or pos.pos_tag is None or (pos.pos_unknown and token.has_no_pos_tag):
            return True
        tp = token.pos_tag
        if tp is None:
            return False
        if pos.pos_pattern is not None:
            return pos.pos_pattern.matches(tp)
        return pos.pos_tag == tp

    def is_exception_matched(self, token):
        for e in self.current_and_next_exceptions:
            if not e.exception_valid_next and e.is_matched(token):
                return True
        return False

    def is_and_exception_group_matched(self, token):
        if self.and_group is None:
            return False
        for t in self.and_group:
            if t.is_exception_matched(token):
                return True
        return False

    def is_exception_matched_completely(self, token):
        return self.is_exception_matched(token) or self.is_and_exception_group_matched(token)

    def is_matched_by_scope_next_exception(self, token):
        for e in self.current_and_next_exceptions:
            if e.exception_valid_next and e.is_matched(token):
                return True
        return False

    def is_matched_by_previous_exception(self, token):
        for e in self.previous_exceptions:
            if not e.exception_valid_next and e.is_matched(token):
                return True
        return False

    def is_matched_by_previous_exception_readings(self, atr):
        for t in atr.readings:
            if self.is_matched_by_previous_exception(t):
                return True
        return False

    # --- properties ---

    def is_sentence_start(self):
        p = self.pos_token
        return p is not None and p.pos_tag == SENTENCE_START_TAGNAME and not p.negation

    def has_and_group(self):
        return self.and_group is not None

    def has_or_group(self):
        return self.or_group is not None

    def set_and_group_element(self, t):
        if self.and_group is None:
            self.and_group = []
        self.and_group.append(t)

    def set_or_group_element(self, t):
        if self.or_group is None:
            self.or_group = []
        self.or_group.append(t)

    def get_string(self):
        return self.text_matcher.pattern

    def set_string_element(self, token):
        self.set_text_matcher(string_matcher.create(normalize_text_pattern(token), self.is_regular_expression(),
                                                    self.is_case_sensitive()))

    def set_text_matcher(self, matcher):
        self.text_matcher = matcher
        self.test_string = bool(matcher.pattern)

    def is_case_sensitive(self):
        return self.text_matcher.case_sensitive

    def is_regular_expression(self):
        return self.text_matcher.is_regexp

    def get_pos_tag(self):
        return self.pos_token.pos_tag if self.pos_token is not None else None

    def is_pos_tag_regular_expression(self):
        return self.pos_token is not None and self.pos_token.pos_pattern is not None

    def get_pos_negation(self):
        return self.pos_token is not None and self.pos_token.negation

    def get_min_occurrence(self):
        return 0 if self.may_be_omitted else 1

    def set_min_occurrence(self, i):
        if i not in (0, 1):
            raise ValueError('minOccurrences must be 0 or 1: %s' % i)
        self.may_be_omitted = i == 0

    def set_max_occurrence(self, i):
        if i == 0:
            raise ValueError('maxOccurrences may not be 0')
        if i < -1 or i > 127:
            raise ValueError('maxOccurrences should be between -1 and 127')
        self.max_occurrence = i

    def set_skip_next(self, i):
        if i < -1 or i > 127:
            raise ValueError("'skip' should be between -1 and 127")
        self.skip = i

    def is_reference_element(self):
        return self.token_reference is not None

    def is_unified(self):
        return self.unification_features is not None

    def is_part_of_phrase(self):
        return self.phrase_name is not None

    def has_previous_exception(self):
        return len(self.previous_exceptions) > 0

    def has_current_or_next_exceptions(self):
        return len(self.current_and_next_exceptions) > 0

    def has_exception_list(self):
        return bool(self.current_and_next_exceptions) or bool(self.previous_exceptions)

    def set_whitespace_before(self, is_white):
        self.whitespace_before = is_white
        self.test_whitespace = True

    def set_exception_space_before(self, is_white):
        arr = self.previous_exceptions if self.previous_exceptions else self.current_and_next_exceptions
        if arr:
            arr[-1].set_whitespace_before(is_white)

    def add_exception(self, scope_next, scope_previous, exception):
        exception.exception_valid_next = scope_next
        if scope_previous:
            self.previous_exceptions = tuple(self.previous_exceptions) + (exception,)
        else:
            self.current_and_next_exceptions = tuple(self.current_and_next_exceptions) + (exception,)

    def set_string_pos_exception(self, token, regexp, inflected, negation, scope_next, scope_previous,
                                 pos_token, pos_regexp, pos_negation, case_sensitivity=None):
        cs = self.is_case_sensitive() if case_sensitivity is None else case_sensitivity
        exc = PatternToken(token, cs, regexp, inflected)
        exc.negation = negation
        exc.pos_token = PosToken(pos_token, pos_negation, regexp=pos_regexp)
        self.add_exception(scope_next, scope_previous, exc)

    # --- references ---

    def compile(self, token, synthesizer):
        """Resolve a <match> reference inside the token, returns a new
        PatternToken."""
        c = self.clone()
        ref = c.token_reference
        state = ref.create_state(synthesizer, token)
        reference = '\\' + str(ref.token_ref)
        if ref.set_pos:
            pos_ref = state.get_target_pos_tag()
            if pos_ref is not None:
                c.pos_token = PosToken(pos_ref, c.negation, regexp=ref.postag_regexp)
            c.set_string_element(c.get_string().replace(reference, ''))
        else:
            c.set_string_element(c.get_string().replace(reference, state.to_token_string()))
        return c

    # --- hints for rule pre-filtering ---

    def calc_form_hints(self):
        return self._calc_string_hints(False)

    def calc_lemma_hints(self):
        return self._calc_string_hints(True)

    def calc_pos_hints(self):
        p = self.pos_token
        if p is None or p.negation or p.pos_unknown:
            return None
        if self.may_be_omitted or self.is_reference_element():
            return None
        if p.pos_pattern is not None:
            pv = p.pos_pattern.get_possible_values()
            return pv if pv else None
        return None if p.pos_tag is None else frozenset((p.pos_tag,))

    def _calc_string_hints(self, inflected):
        result = None if inflected != self.inflected else self._calc_own_possible_string_values()
        if result is None:
            return None
        if self.and_group is not None:
            result = set(result)
            for t in self.and_group:
                h = t._calc_string_hints(inflected)
                if h is not None:
                    result &= h
        elif self.or_group is not None:
            result = set(result)
            for t in self.or_group:
                h = t._calc_string_hints(inflected)
                if h is None:
                    return None
                result |= h
        return frozenset(result) if result else None

    def _calc_own_possible_string_values(self):
        if self.negation or not self.has_string_that_must_match():
            return None
        return self.text_matcher.get_possible_values()

    def has_string_that_must_match(self):
        return not self.is_reference_element() and not self.may_be_omitted and bool(self.get_string())

    def __repr__(self):
        s = ('!' if self.negation else '') + self.get_string()
        if self.phrase_name is not None:
            s += ' {%s}' % self.phrase_name
        if self.pos_token is not None:
            s += '/' + str(self.pos_token)
        if self.chunk_tag is not None:
            s += '/' + str(self.chunk_tag)
        if self.current_and_next_exceptions:
            s += '/exceptions=' + repr(list(self.current_and_next_exceptions))
        return s
