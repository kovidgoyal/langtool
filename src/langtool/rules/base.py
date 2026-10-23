"""Rule base class, categories and rule matches. Port of
org.languagetool.rules.Rule, Category, RuleMatch and the rule match
filters (RuleWithMaxFilter, SameRuleGroupFilter, CleanOverlappingFilter)."""

from ..tools import is_mixed_case, uppercase_first_char, is_all_whitespace

SUGGESTION_START_TAG = '<suggestion>'
SUGGESTION_END_TAG = '</suggestion>'

# RuleMatch types
TYPE_UNKNOWN_WORD = 'UnknownWord'
TYPE_HINT = 'Hint'
TYPE_OTHER = 'Other'

ITS_ISSUE_TYPES = {
    'terminology': 'Terminology', 'mistranslation': 'Mistranslation', 'omission': 'Omission',
    'untranslated': 'Untranslated', 'addition': 'Addition', 'duplication': 'Duplication',
    'inconsistency': 'Inconsistency', 'grammar': 'Grammar', 'legal': 'Legal', 'register': 'Register',
    'locale-specific-content': 'LocaleSpecificContent', 'locale-violation': 'LocaleViolation', 'style': 'Style',
    'characters': 'Characters', 'misspelling': 'Misspelling', 'typographical': 'Typographical',
    'formatting': 'Formatting', 'inconsistent-entities': 'InconsistentEntities', 'numbers': 'Numbers',
    'markup': 'Markup', 'pattern-problem': 'PatternProblem', 'whitespace': 'Whitespace', 'internationalization':
    'Internationalization', 'length': 'Length', 'non-conformance': 'NonConformance', 'uncategorized': 'Uncategorized',
    'other': 'Other',
}


def its_issue_type(name):
    if name is None:
        return 'Uncategorized'
    n = name.lower()
    if n in ITS_ISSUE_TYPES:
        return ITS_ISSUE_TYPES[n]
    for v in ITS_ISSUE_TYPES.values():
        if v.lower() == n.replace('-', '').replace('_', ''):
            return v
    return 'Uncategorized'


class Category:
    __slots__ = ('id', 'name', 'location', 'default_on', 'tab_name')

    def __init__(self, id, name, location='INTERNAL', default_on=True, tab_name=None):
        self.id = id
        self.name = name
        self.location = location
        self.default_on = default_on
        self.tab_name = tab_name

    def is_default_off(self):
        return not self.default_on

    def __repr__(self):
        return 'Category(%s, %r)' % (self.id, self.name)


MISC = Category('MISC', 'Miscellaneous')


class Rule:
    """Base class for all rules."""

    def __init__(self):
        self.category = MISC
        self.loc_quality_issue_type = 'Uncategorized'
        self.url = None
        self.default_off = False
        self.default_temp_off = False
        self.premium = False
        self.tags = []
        self.tone_tags = []
        self.goal_specific = False
        self.priority = 0
        self.min_prev_matches = 0
        self.distance_tokens = -1
        self.correct_examples = []
        self.incorrect_examples = []
        self.error_triggering_examples = []

    @property
    def id(self):
        return self.get_id()

    def get_id(self):
        raise NotImplementedError()

    def get_sub_id(self):
        return None

    def get_full_id(self):
        sub = self.get_sub_id()
        return self.get_id() if sub is None else '%s[%s]' % (self.get_id(), sub)

    def get_description(self):
        raise NotImplementedError()

    def match(self, sentence):
        raise NotImplementedError()

    def get_anti_patterns(self):
        return ()

    def estimate_context_for_sure_match(self):
        return 0

    def is_text_level_rule(self):
        return False

    def set_default_off(self):
        self.default_off = True

    def set_default_temp_off(self):
        self.default_off = True
        self.default_temp_off = True

    def set_default_on(self):
        self.default_off = False

    def add_tags(self, tags):
        for t in tags:
            if t and t not in self.tags:
                self.tags.append(t)

    def add_tone_tags(self, tags):
        for t in tags:
            if t and t not in self.tone_tags:
                self.tone_tags.append(t)

    def has_tag(self, tag):
        return tag in self.tags

    def get_sentence_with_immunization(self, sentence):
        anti = self.get_anti_patterns()
        if anti:
            immunized = sentence.copy()
            for ap in anti:
                immunized = ap.replace(immunized)
            return immunized
        return sentence

    def to_rule_match_array(self, matches):
        return list(matches)

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.get_full_id())


class TextLevelRule(Rule):
    """A rule that works on the whole text (list of sentences)."""

    def is_text_level_rule(self):
        return True

    def match(self, sentences, annotated_text=None):
        raise NotImplementedError()

    def min_to_check_paragraph(self):
        return -1


class SuggestedReplacement:
    __slots__ = ('replacement', 'short_description', 'suffix', 'confidence')

    def __init__(self, replacement, short_description=None, suffix=None):
        self.replacement = replacement
        self.short_description = short_description
        self.suffix = suffix
        self.confidence = None

    def copy(self, replacement=None):
        c = SuggestedReplacement(self.replacement if replacement is None else replacement, self.short_description,
                                 self.suffix)
        c.confidence = self.confidence
        return c

    def __eq__(self, o):
        return isinstance(o, SuggestedReplacement) and self.replacement == o.replacement and \
            self.short_description == o.short_description and self.suffix == o.suffix

    def __hash__(self):
        return hash((self.replacement, self.short_description, self.suffix))

    def __repr__(self):
        return repr(self.replacement)


class RuleMatch:
    """A potential error found by a rule."""

    __slots__ = ('rule', 'message', 'short_message', 'sentence', 'pattern_from_pos', 'pattern_to_pos',
                 'from_pos', 'to_pos', 'sentence_from_pos', 'sentence_to_pos', 'line', 'end_line', 'column',
                 'end_column', '_suggested_replacements', 'url', 'type', 'auto_correct', 'specific_rule_id',
                 'original_error_str', 'features')

    def __init__(self, rule, sentence, from_pos, to_pos, message, short_message=None, pattern_from_pos=None,
                 pattern_to_pos=None, start_with_uppercase=False, is_all_uppercase=False, suggestions_out_msg=None,
                 set_original_error_str=False, suggestions=None):
        if to_pos <= from_pos:
            raise ValueError('fromPos (%d) must be less than toPos (%d)' % (from_pos, to_pos))
        self.rule = rule
        self.sentence = sentence
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.pattern_from_pos = from_pos if pattern_from_pos is None else pattern_from_pos
        self.pattern_to_pos = to_pos if pattern_to_pos is None else pattern_to_pos
        self.sentence_from_pos = -1
        self.sentence_to_pos = -1
        self.line = self.end_line = self.column = self.end_column = -1
        self.message = message
        self.short_message = short_message
        self.url = None
        self.type = TYPE_OTHER
        self.auto_correct = False
        self.specific_rule_id = ''
        self.original_error_str = ''
        self.features = {}
        if set_original_error_str:
            self.set_original_error_str()
        replacements = []
        seen = set()
        sugg = message + (suggestions_out_msg if suggestions_out_msg is not None else '')
        pos = sugg.find(SUGGESTION_START_TAG)
        from ..patterns.matcher import MISTAKE
        while pos != -1:
            end = sugg.find(SUGGESTION_END_TAG, pos)
            if end == -1:
                break
            repl = sugg[pos + len(SUGGESTION_START_TAG):end]
            pos = end + len(SUGGESTION_END_TAG)
            if MISTAKE in repl:
                continue
            if is_all_uppercase and not (is_mixed_case(repl) and ' ' not in repl):
                if self.original_error_str != repl.upper():
                    repl = repl.upper()
            elif start_with_uppercase:
                repl = uppercase_first_char(repl)
            sr = SuggestedReplacement(repl)
            if sr not in seen:
                seen.add(sr)
                replacements.append(sr)
            pos = sugg.find(SUGGESTION_START_TAG, pos)
        if suggestions is not None:
            replacements = [SuggestedReplacement(s) for s in suggestions]
        self._suggested_replacements = replacements

    def copy(self):
        c = RuleMatch.__new__(RuleMatch)
        for k in RuleMatch.__slots__:
            setattr(c, k, getattr(self, k))
        c._suggested_replacements = list(self._suggested_replacements)
        return c

    @property
    def suggested_replacements(self):
        return [s.replacement for s in self._suggested_replacements]

    @property
    def suggested_replacement_objects(self):
        return list(self._suggested_replacements)

    def set_suggested_replacements(self, replacements):
        self._suggested_replacements = [SuggestedReplacement(r) for r in replacements]

    def set_suggested_replacement(self, replacement):
        self.set_suggested_replacements([replacement])

    def add_suggested_replacement(self, replacement):
        self._suggested_replacements.append(SuggestedReplacement(replacement))

    def add_suggested_replacements(self, replacements):
        for r in replacements:
            self.add_suggested_replacement(r)

    def set_suggested_replacement_objects(self, objs):
        self._suggested_replacements = list(objs)

    def set_offset_position(self, from_pos, to_pos):
        if to_pos <= from_pos:
            raise ValueError('fromPos (%d) must be less than toPos (%d)' % (from_pos, to_pos))
        self.from_pos = from_pos
        self.to_pos = to_pos

    def set_pattern_position(self, from_pos, to_pos):
        self.pattern_from_pos = from_pos
        self.pattern_to_pos = to_pos

    def set_sentence_position(self, from_pos, to_pos):
        self.sentence_from_pos = from_pos
        self.sentence_to_pos = to_pos

    def get_from_pos_sentence(self):
        return self.sentence_from_pos if self.sentence_from_pos > -1 else self.from_pos

    def get_to_pos_sentence(self):
        return self.sentence_to_pos if self.sentence_to_pos > -1 else self.to_pos

    def set_original_error_str(self, s=None):
        if s is not None:
            self.original_error_str = s
            return
        if self.original_error_str:
            return
        if self.sentence is None:
            return
        text = self.sentence.text
        if not text:
            return
        f, t = self.get_from_pos_sentence(), self.get_to_pos_sentence()
        if f > -1 and t > -1 and t <= len(text) and f < t:
            self.original_error_str = text[f:t]

    def get_specific_rule_id(self):
        return self.specific_rule_id or self.rule.get_id()

    def __lt__(self, other):
        return self.from_pos < other.from_pos

    def __eq__(self, o):
        if self is o:
            return True
        if type(o) is not type(self):
            return NotImplemented
        return self.rule.get_id() == o.rule.get_id() and \
            (self.pattern_from_pos, self.pattern_to_pos) == (o.pattern_from_pos, o.pattern_to_pos) and \
            (self.from_pos, self.to_pos) == (o.from_pos, o.to_pos) and self.message == o.message and \
            self.sentence == o.sentence and self.type == o.type

    def __hash__(self):
        return hash((self.rule.get_id(), self.from_pos, self.to_pos, self.pattern_from_pos, self.pattern_to_pos,
                     self.message, self.type))

    def trim_match_ends(self):
        """Port of RuleMatch.trimMatchEnds(): returns a match with the tokens
        that the error string and all the suggestions have in common at the
        start and end removed (or self if nothing can be trimmed)"""
        replacements = list(self._suggested_replacements)
        if not replacements:
            return self
        error_str = self.original_error_str
        if not error_str:
            self.set_original_error_str()
            error_str = self.original_error_str
        if not error_str or is_all_whitespace(error_str):
            return self
        from_pos, to_pos = self.from_pos, self.to_pos
        from_sent, to_sent = self.get_from_pos_sentence(), self.get_to_pos_sentence()
        changed = True
        while changed:
            changed = False
            last = error_str.rfind(' ')
            if last > 0:
                suffix = ' ' + error_str[last + 1:]
                trim = len(error_str) - last
                if all(r.replacement.endswith(suffix) for r in replacements) and to_pos - trim > from_pos:
                    replacements = [r.copy(r.replacement[:len(r.replacement) - len(suffix)]) for r in replacements]
                    to_pos -= trim
                    if to_sent >= 0:
                        to_sent -= trim
                    error_str = error_str[:last]
                    changed = True
            first = error_str.find(' ')
            if first > 0:
                prefix = error_str[:first] + ' '
                trim = first + 1
                if all(r.replacement.startswith(prefix) for r in replacements) and from_pos + trim < to_pos:
                    replacements = [r.copy(r.replacement[len(prefix):]) for r in replacements]
                    from_pos += trim
                    if from_sent >= 0:
                        from_sent += trim
                    error_str = error_str[trim:]
                    changed = True
        if from_pos == self.from_pos and to_pos == self.to_pos:
            return self
        m = self.copy()
        m._suggested_replacements = replacements
        m.set_offset_position(from_pos, to_pos)
        m.set_sentence_position(from_sent, to_sent)
        m.original_error_str = error_str
        return m

    def __repr__(self):
        return '%s:%d-%d:%s' % (self.rule.get_full_id(), self.from_pos, self.to_pos, self.message)


def _includes(m, n):
    return m.from_pos <= n.from_pos and m.to_pos >= n.to_pos


def _have_same_rule(m, n):
    from ..patterns.rules import AbstractPatternRule
    if not isinstance(m.rule, AbstractPatternRule) or not isinstance(n.rule, AbstractPatternRule):
        return False
    id1 = m.rule.get_id()
    s1 = m.rule.get_sub_id()
    s2 = n.rule.get_sub_id()
    if (s1 is None) != (s2 is None):
        return False
    return id1 is not None and id1 == n.rule.get_id() and (s1 == s2)


def rule_with_max_filter(matches):
    """Port of RuleWithMaxFilter: removes matches that are included in a
    previous match of the same rule."""
    matches = sorted(matches, key=lambda m: m.from_pos)
    out = []
    i = 0
    n = len(matches)
    while i < n:
        m = matches[i]
        if i < n - 1:
            nxt = matches[i + 1]
            while _includes(m, nxt) and _have_same_rule(m, nxt) and i < n:
                i += 1
                if i < n - 1:
                    nxt = matches[i + 1]
        out.append(m)
        i += 1
    return out


def same_rule_group_filter(matches):
    """Port of SameRuleGroupFilter: of overlapping matches from the same
    rule (group), keep only the first."""
    matches = sorted(matches, key=lambda m: m.from_pos)
    out = []
    i = 0
    n = len(matches)
    while i < n:
        m = matches[i]
        while i < n - 1 and _overlaps(m, matches[i + 1]) and m.rule.get_id() is not None and \
                m.rule.get_id() == matches[i + 1].rule.get_id():
            i += 1
        out.append(m)
        i += 1
    return out


def _overlaps(m, n):
    return m.from_pos <= n.to_pos and m.to_pos >= n.from_pos


def _keep_letters_and_digits(s):
    from ..tools import is_letter_or_digit
    return ''.join(c for c in s if is_letter_or_digit(c))


def _is_punctuation_only_change(m):
    sugg = m.suggested_replacements
    if not sugg:
        return False
    replacement = sugg[0]
    if replacement is None:
        return False
    original = m.original_error_str
    if not original:
        text = m.sentence.text if m.sentence is not None else None
        if not text:
            return False
        f, t = m.get_from_pos_sentence(), m.get_to_pos_sentence()
        if f > -1 and t > -1 and t <= len(text) and f < t:
            original = text[f:t]
        else:
            f, t = m.from_pos, m.to_pos
            if f > -1 and t > -1 and t <= len(text) and f < t:
                original = text[f:t]
            else:
                return False
    if replacement == original:
        return False
    return _keep_letters_and_digits(original) == _keep_letters_and_digits(replacement)


_NEGATIVE_CONSTANT = -(2 ** 31) + 10000
_MIN_VALUE = -(2 ** 31)


def clean_overlapping_filter(matches, language, hide_premium_matches=False):
    """Port of CleanOverlappingFilter. matches must be sorted by from_pos."""
    clean = []
    prev = None
    for m in matches:
        if prev is None:
            prev = m
            continue
        if m.from_pos < prev.from_pos:
            raise ValueError('The list of rule matches is not ordered')
        dup = False
        s1 = m.suggested_replacements
        s2 = prev.suggested_replacements
        if s1 and s2:
            sug, psug = s1[0], s2[0]
            if m.from_pos == prev.to_pos and psug.endswith(',') and sug.startswith(', '):
                dup = True
            if sug.find(' ') > 0 and psug.find(' ') > 0 and m.from_pos == prev.to_pos + 1:
                parts = sug.split(' ')
                pparts = psug.split(' ')
                if len(pparts) > 1 and len(parts) > 1 and pparts[1] == parts[0]:
                    dup = True
        if m.from_pos >= prev.to_pos and not dup:
            clean.append(prev)
            prev = m
            continue
        cur_p = language.get_rule_priority(m.rule)
        if m.rule.premium and hide_premium_matches:
            cur_p = _MIN_VALUE
        if 'picky' in m.rule.tags and cur_p != _MIN_VALUE:
            cur_p += _NEGATIVE_CONSTANT
        prev_p = language.get_rule_priority(prev.rule)
        if prev.rule.premium and hide_premium_matches:
            prev_p = _MIN_VALUE
        if 'picky' in prev.rule.tags and prev_p != _MIN_VALUE:
            prev_p += _NEGATIVE_CONSTANT
        if _is_punctuation_only_change(m) and _is_punctuation_only_change(prev):
            ca = m.rule.get_id() in ERRORS_THAT_CAN_BE_CORRECTED_ALL_AT_ONCE
            pa = prev.rule.get_id() in ERRORS_THAT_CAN_BE_CORRECTED_ALL_AT_ONCE
            if ca != pa:
                if ca:
                    if cur_p < prev_p:
                        cur_p = prev_p + 1
                elif prev_p < cur_p:
                    prev_p = cur_p + 1
        if cur_p == prev_p:
            cur_p = m.to_pos - m.from_pos
            prev_p = prev.to_pos - prev.from_pos
        if cur_p == prev_p:
            cur_p += 1
        if cur_p > prev_p:
            prev = m
    if prev is not None:
        clean.append(prev)
    return clean


ERRORS_THAT_CAN_BE_CORRECTED_ALL_AT_ONCE = frozenset((
    'FALSCHES_ANFUEHRUNGSZEICHEN', 'TYPOGRAFISCHE_ANFUEHRUNGSZEICHEN', 'TYPOGRAFISCHE_ANFUEHRUNGSZEICHEN_CH',
    'TYPOGRAFISCHE_ANFUEHRUNGSZEICHEN_2', 'TYPOGRAFISCHE_APOSTROPHE', 'EN_QUOTES', 'WRONG_APOSTROPHE',
    'PARAGRAF_LEERZEICHEN', 'CONSISTENCYRULE_JE_F', 'CONSISTENCYRULE_JE_M', 'COMILLAS_TIPOGRAFICAS',
    'COMETES_TIPOGRAFIQUES', 'TYPOGRAFISCHE_AANHALINGSTEKENS', 'PT_SMART_QUOTES', 'GL_SMART_QUOTES'))


class Example:
    __slots__ = ('example', 'corrections')

    def __init__(self, example, corrections=None):
        self.example = example
        self.corrections = corrections

    def __repr__(self):
        return '<Example %r %r>' % (self.example, self.corrections)
