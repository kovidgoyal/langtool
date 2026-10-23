"""Loading of XML rule files (grammar.xml, style.xml, disambiguation.xml).

Port of org.languagetool.rules.patterns.XMLRuleHandler, PatternRuleHandler
and org.languagetool.tagging.disambiguation.rules.DisambiguationRuleHandler.
The SAX state machine of the Java code is kept, driven by an lxml parser
target.
"""

import os
import re

from lxml import etree

from .. import jregex
from ..analysis import AnalyzedToken
from ..chunking import ChunkTag
from ..rules.base import Category, Example, its_issue_type
from ..tools import is_empty
from . import string_matcher
from .match import Match, CASE_CONVERSIONS, INCLUDE_RANGES, NONE as CASE_NONE, INCLUDE_NONE
from .matcher import PLEASE_SPELL_ME
from .pattern_token import PatternToken, PosToken, normalize_text_pattern
from . import rules as R

YES = 'yes'
OFF = 'off'
TEMP_OFF = 'temp_off'
MARKER_TAG = '<marker>'


class RuleLoadError(Exception):
    pass


class UnsupportedFilter(Exception):
    pass


class _EntityResolver(etree.Resolver):

    def __init__(self, resource_dir):
        super().__init__()
        self.resource_dir = resource_dir

    def resolve(self, url, pubid, context):
        if url and url.endswith('.ent'):
            p = re.sub(r'.*/resource/', '', url).replace('../', '')
            path = os.path.join(self.resource_dir, p)
            if os.path.exists(path):
                return self.resolve_filename(path, context)
        return None


def parse_events(path, target, resource_dir):
    parser = etree.XMLParser(target=target, load_dtd=True, resolve_entities=True, no_network=True, huge_tree=True,
                             remove_comments=True)
    if resource_dir:
        parser.resolvers.add(_EntityResolver(resource_dir))
    with open(path, 'rb') as f:
        etree.parse(f, parser, base_url=path)


def _local(tag):
    if isinstance(tag, str) and tag.startswith('{'):
        return tag.rsplit('}', 1)[1]
    return tag


def _has_posix_character_class(s, rule_id):
    res = '\\p{Lu}' in s or '\\p{Ll}' in s
    if res and '(?i' in s:
        raise RuleLoadError("Contradicting regex contains both '?i' (case-insensitive) and \\p{Lu}/\\p{Ll} "
                            "(case-sensitive): %s in rule %s" % (s, rule_id))
    return res


class XMLRuleHandler:
    """Base state machine shared by the grammar and disambiguation rule
    handlers."""

    def __init__(self, language, filter_factory=None):
        self.language = language
        self.filter_factory = filter_factory
        self.rules = []
        self.problems = []
        self.correct_example = []
        self.incorrect_example = []
        self.error_trigger_example = []
        self.anti_pattern_example = []
        self.anti_pattern_for_rule_group_example = []
        self.example_correction = None
        self.message = []
        self.suggestions_out_msg = []
        self.match = []
        self.elements = []
        self.exceptions = []
        self.correct_examples = []
        self.antipattern_examples = []
        self.antipattern_for_rule_groups_examples = []
        self.incorrect_examples = []
        self.error_triggering_examples = []
        self.in_pattern = self.in_correct_example = self.in_incorrect_example = False
        self.in_error_trigger_example = self.in_anti_pattern_example = False
        self.in_anti_pattern_for_rule_group_example = False
        self.in_message = self.in_suggestion = self.in_match = self.in_rule_group = False
        self.in_token = self.in_exception = self.in_phrases = self.in_and_group = self.in_or_group = False
        self.token_space_before = self.token_space_before_set = False
        self.pos_token = None
        self.chunk_tag = None
        self.pos_negation = self.pos_regexp = False
        self.case_sensitive = False
        self.reg_expression = self.token_negated = self.token_inflected = False
        self.premium_rule_group_attribute = self.premium_category_attribute = self.premium_file_attribute = None
        self.is_premium_rule = False
        self.category_tags, self.rule_group_tags, self.rule_tags = [], [], []
        self.category_tone_tags, self.rule_group_tone_tags, self.rule_tone_tags = [], [], []
        self.is_goal_specific_category_attribute = self.is_goal_specific_rule_group_attribute = None
        self.is_goal_specific = False
        self.prio_category_attribute = self.prio_rule_group_attribute = self.prio_rule_attribute = 0
        self.token_level_case_sensitive = self.token_level_case_set = False
        self.exception_pos_token = None
        self.exception_string_regexp = self.exception_string_negation = self.exception_string_inflected = False
        self.exception_pos_negation = self.exception_pos_regexp = False
        self.exception_valid_next = self.exception_valid_prev = False
        self.exception_set = False
        self.exception_space_before = self.exception_space_before_set = False
        self.exception_level_case_sensitive = None
        self.exception_level_case_set = False
        self.pattern_tokens = []
        self.last_phrase = False
        self.phrase_id_ref = None
        self.phrase_id = None
        self.skip_pos = 0
        self.min_occurrence = 1
        self.max_occurrence = 1
        self.rule_group_id = None
        self.id = None
        self.pattern_token = None
        self.token_reference = None
        self.suggestion_matches = []
        self.suggestion_matches_out_msg = []
        self.xml_line_number = -1
        self.xml_line_number_anti_pattern = -1
        self.start_position_correction = 0
        self.end_position_correction = 0
        self.token_counter = 0
        self.phrase_map = None
        self.phrase_pattern_tokens = []
        self.and_group_counter = 0
        self.or_group_counter = 0
        self.in_url = self.in_url_for_rule_group = False
        self.url = []
        self.url_for_rule_group = []
        self.in_regex = False
        self.regex = []
        self.regex_mode_exact = False
        self.regex_case_sensitive = False
        self.regexp_mark = 0
        self.in_short_message = self.in_short_message_for_rule_group = False
        self.short_message = []
        self.short_message_for_rule_group = []
        self.in_unification = self.in_marker = self.in_unification_def = False
        self.uni_negation = self.in_unification_neutral = False
        self.u_feature = None
        self.u_type = ''
        self.u_type_list = []
        self.equivalence_features = {}
        self.current_filter_error = None

    # lxml target interface
    def start(self, tag, attrib):
        self.start_element(_local(tag), attrib)

    def end(self, tag):
        self.end_element(_local(tag))

    def data(self, text):
        self.characters(text)

    def comment(self, text):
        pass

    def close(self):
        return self.rules

    # shared helpers

    def reset_token(self):
        self.pos_negation = False
        self.pos_regexp = False
        self.in_token = False
        self.token_space_before = False
        self.token_space_before_set = False
        self.reset_exception()
        self.exception_set = False
        self.token_reference = None

    def reset_exception(self):
        self.exception_string_negation = False
        self.exception_string_inflected = False
        self.exception_pos_negation = False
        self.exception_pos_regexp = False
        self.exception_string_regexp = False
        self.exception_valid_next = False
        self.exception_valid_prev = False
        self.exception_space_before = False
        self.exception_space_before_set = False

    def prepare_phrase(self, attrs):
        # Note: like the Java code (ObjectUtils.clone on a List is a shallow
        # copy) the PatternToken objects of a phrase are shared between all
        # uses of the phrase.
        self.phrase_id_ref = attrs.get('idref')
        if self.phrase_map is not None and self.phrase_id_ref in self.phrase_map:
            for cur in self.phrase_map[self.phrase_id_ref]:
                for t in cur:
                    t.phrase_name = self.phrase_id_ref
                cp = list(cur)
                for t in cp:
                    t.inside_marker = self.in_marker
                if not self.pattern_tokens:
                    self.phrase_pattern_tokens.append(list(cp))
                else:
                    self.phrase_pattern_tokens.append(list(self.pattern_tokens) + cp)
            self.last_phrase = True

    def finalize_phrase(self):
        if self.phrase_map is None:
            self.phrase_map = {}
        for t in self.pattern_tokens:
            t.inside_marker = self.in_marker
        if not self.phrase_pattern_tokens:
            self.phrase_pattern_tokens.append(list(self.pattern_tokens))
        else:
            for ph in self.phrase_pattern_tokens:
                ph.extend(self.pattern_tokens)
        self.phrase_map[self.phrase_id] = list(self.phrase_pattern_tokens)
        self.pattern_tokens = []
        self.phrase_pattern_tokens = []

    def start_pattern(self, attrs):
        self.token_counter = 0
        self.in_pattern = True
        self.case_sensitive = attrs.get('case_sensitive') == YES

    def process_element(self, tokens):
        counter = 0
        for t in tokens:
            if t.phrase_name is not None and counter > 0 and t.is_reference_element():
                tok_ref = t.token_reference.token_ref
                t.token_reference.token_ref = tok_ref + counter - 1
                t.set_string_element(t.get_string().replace('\\' + str(tok_ref), '\\' + str(tok_ref + counter - 1)))
            counter += 1

    def set_match_element(self, attrs, is_suppress_misspelled):
        self.in_match = True
        self.match = []
        cc = CASE_NONE
        if attrs.get('case_conversion') is not None:
            cc = CASE_CONVERSIONS[attrs.get('case_conversion').lower()]
        ir = INCLUDE_NONE
        if attrs.get('include_skipped') is not None:
            ir = INCLUDE_RANGES[attrs.get('include_skipped').lower()]
        m = Match(attrs.get('postag'), attrs.get('postag_replace'), attrs.get('postag_regexp') == YES,
                  attrs.get('regexp_match'), attrs.get('regexp_replace'), cc, attrs.get('setpos') == YES,
                  is_suppress_misspelled, ir)
        m.in_message_only = not self.in_suggestion
        if self.in_message:
            self.suggestion_matches.append(m)
            self.message.append('\u0001\\')
            self.message.append(attrs.get('no') or '')
            self.check_number(attrs)
        elif self.in_suggestion:
            self.suggestion_matches_out_msg.append(m)
            self.suggestions_out_msg.append('\u0001\\')
            self.suggestions_out_msg.append(attrs.get('no') or '')
            self.check_number(attrs)
        elif self.in_token and attrs.get('no') is not None:
            ref = int(attrs.get('no'))
            self.check_ref_number(ref)
            m.token_ref = ref
            self.token_reference = m
            self.elements.append('\\')
            self.elements.append(str(ref))

    def check_number(self, attrs):
        no = attrs.get('no')
        if is_empty(no):
            raise RuleLoadError('References cannot be empty')
        if int(no) < 1 and not self.regex:
            raise RuleLoadError('References must be larger than 0: ' + no)

    def check_ref_number(self, ref):
        if ref > len(self.pattern_tokens):
            raise RuleLoadError('Only backward references in match elements are possible, tried to specify token %d'
                                % ref)

    def set_exceptions(self, attrs):
        self.in_exception = True
        self.exceptions = []
        self.reset_exception()
        self.exception_string_negation = attrs.get('negate') == YES
        self.exception_valid_next = attrs.get('scope') == 'next'
        self.exception_valid_prev = attrs.get('scope') == 'previous'
        self.exception_string_inflected = attrs.get('inflected') == YES
        if attrs.get('postag') is not None:
            self.exception_pos_token = attrs.get('postag')
            self.exception_pos_regexp = attrs.get('postag_regexp') == YES
            self.exception_pos_negation = attrs.get('negate_pos') == YES
        self.exception_string_regexp = attrs.get('regexp') == YES
        if attrs.get('spacebefore') is not None:
            self.exception_space_before = attrs.get('spacebefore') == YES
            self.exception_space_before_set = attrs.get('spacebefore') != 'ignore'
        if attrs.get('case_sensitive') is not None:
            self.exception_level_case_set = True
            self.exception_level_case_sensitive = attrs.get('case_sensitive') == YES
        else:
            self.exception_level_case_set = False

    def finalize_exceptions(self):
        self.in_exception = False
        if not self.exception_set:
            token_case = self.case_sensitive
            if self.token_level_case_set:
                token_case = self.token_level_case_sensitive
            self.pattern_token = PatternToken(inflected=self.token_inflected, matcher=self.intern_matcher(
                ''.join(self.elements).strip(), self.reg_expression, token_case))
            self.exception_set = True
        self.pattern_token.negation = self.token_negated
        exc_text = ''.join(self.exceptions)
        if exc_text or self.exception_pos_token is not None:
            if _has_posix_character_class(exc_text, self.id):
                self.exception_level_case_sensitive = True
            cs = self.pattern_token.is_case_sensitive() if self.exception_level_case_sensitive is None \
                else self.exception_level_case_sensitive
            exc = PatternToken(inflected=self.exception_string_inflected, matcher=self.intern_matcher(
                exc_text.strip(), self.exception_string_regexp, cs))
            exc.negation = self.exception_string_negation
            exc.pos_token = self.obtain_pos_token(self.exception_pos_token, self.exception_pos_regexp,
                                                  self.exception_pos_negation)
            self.pattern_token.add_exception(self.exception_valid_next, self.exception_valid_prev, exc)
            self.exception_pos_token = None
            self.exception_level_case_sensitive = None
        if self.exception_space_before_set:
            self.pattern_token.set_exception_space_before(self.exception_space_before)
        self.reset_exception()

    def set_token(self, attrs):
        self.in_token = True
        if self.last_phrase:
            self.pattern_tokens = []
        self.last_phrase = False
        self.token_negated = attrs.get('negate') == YES
        self.token_inflected = attrs.get('inflected') == YES
        if attrs.get('skip') is not None:
            self.skip_pos = int(attrs.get('skip'))
        if attrs.get('min') is not None:
            self.min_occurrence = int(attrs.get('min'))
        if attrs.get('max') is not None:
            self.max_occurrence = int(attrs.get('max'))
        self.elements = []
        if attrs.get('postag') is not None:
            self.pos_token = attrs.get('postag')
            self.pos_regexp = attrs.get('postag_regexp') == YES
            self.pos_negation = attrs.get('negate_pos') == YES
        if attrs.get('chunk') is not None and attrs.get('chunk_re') is not None:
            raise RuleLoadError("You cannot set both 'chunk' and 'chunk_re' for " + str(self.id))
        if attrs.get('chunk') is not None:
            self.chunk_tag = ChunkTag(attrs.get('chunk'))
        elif attrs.get('chunk_re') is not None:
            self.chunk_tag = ChunkTag(attrs.get('chunk_re'), True)
        self.reg_expression = attrs.get('regexp') == YES
        if attrs.get('spacebefore') is not None:
            self.token_space_before = attrs.get('spacebefore') == YES
            self.token_space_before_set = attrs.get('spacebefore') != 'ignore'
        if not self.in_and_group and not self.in_or_group:
            self.token_counter += 1
        if attrs.get('case_sensitive') is not None:
            self.token_level_case_set = True
            self.token_level_case_sensitive = attrs.get('case_sensitive') == YES
        else:
            self.token_level_case_sensitive = False
            self.token_level_case_set = False

    def add_legacy_matches(self, existing, message_str, in_message):
        sug = []
        pos = 0
        ind = 0
        counter = 0
        buf = self.message if in_message else self.suggestions_out_msg
        # buf is a list of fragments; work on a joined copy and write back
        text = ''.join(buf)
        deletions = []
        while pos != -1:
            pos = message_str.find('\\', ind)
            if pos != -1 and len(message_str) > pos + 1 and message_str[pos + 1].isdigit():
                if pos == 0 or message_str[pos - 1] != '\u0001':
                    m = Match(None, None, False, None, None, CASE_NONE, False, False, INCLUDE_NONE)
                    m.in_message_only = True
                    sug.append(m)
                elif message_str[pos - 1] == '\u0001':
                    sug.append(existing[counter])
                    deletions.append(pos - 1 - counter)
                    counter += 1
            ind = pos + 1
        if deletions:
            chars = list(text)
            for d in deletions:
                del chars[d]
            text = ''.join(chars)
            buf[:] = [text]
        if not sug:
            return existing
        return sug

    def finalize_tokens(self, unifier_config):
        el = ''.join(self.elements)
        if not self.exception_set or self.pattern_token is None:
            token_case = self.case_sensitive or _has_posix_character_class(el, self.id)
            if self.token_level_case_set:
                token_case = self.token_level_case_sensitive
            self.pattern_token = PatternToken(inflected=self.token_inflected,
                                              matcher=self.intern_matcher(el.strip(), self.reg_expression, token_case))
            self.pattern_token.negation = self.token_negated
        else:
            cs = self.pattern_token.is_case_sensitive() or _has_posix_character_class(el, self.id)
            self.pattern_token.set_text_matcher(self.intern_matcher(el.strip(),
                                                                    self.pattern_token.is_regular_expression(), cs))
        pt = self.pattern_token
        if self.skip_pos != 0:
            pt.set_skip_next(self.skip_pos)
            self.skip_pos = 0
        if self.min_occurrence == 0:
            pt.set_min_occurrence(0)
        if self.max_occurrence != 1:
            pt.set_max_occurrence(self.max_occurrence)
            self.max_occurrence = 1
        if self.pos_token is not None:
            pt.pos_token = self.obtain_pos_token(self.pos_token, self.pos_regexp, self.pos_negation)
            self.pos_token = None
        if self.chunk_tag is not None:
            pt.chunk_tag = self.chunk_tag
            self.chunk_tag = None
        if self.token_reference is not None:
            pt.token_reference = self.token_reference
        if self.in_and_group and self.and_group_counter > 0:
            self.pattern_tokens[-1].set_and_group_element(pt)
            if self.min_occurrence != 1 or self.max_occurrence != 1:
                raise RuleLoadError('Please set min and max attributes on the first token in the AND group.')
        elif self.in_or_group and self.or_group_counter > 0:
            self.pattern_tokens[-1].set_or_group_element(pt)
        else:
            if self.min_occurrence < 1:
                self.pattern_tokens.append(pt)
            for i in range(self.min_occurrence):
                self.pattern_tokens.append(pt)
            self.min_occurrence = 1
        if self.in_and_group:
            self.and_group_counter += 1
        if self.in_or_group:
            self.or_group_counter += 1
        if self.in_unification:
            pt.unification_features = self.equivalence_features
        if self.in_unification_neutral:
            pt.unification_neutral = True
        pt.inside_marker = self.in_marker
        if self.in_unification_def:
            unifier_config.set_equivalence(self.u_feature, self.u_type, pt)
            self.pattern_tokens = []
        if self.token_space_before_set:
            pt.set_whitespace_before(self.token_space_before)
        self.reset_token()

    def obtain_pos_token(self, pos, regexp, negated):
        if pos is None:
            return PosToken(None, negated, None)
        key = (pos, regexp, negated)
        cache = self.language.pos_token_cache
        r = cache.get(key)
        if r is None:
            matcher = string_matcher.create(pos, True, True) if regexp else None
            r = cache[key] = PosToken(pos, negated, matcher)
        return r

    def intern_matcher(self, text, regexp, case_sensitive):
        text = normalize_text_pattern(text)
        return string_matcher.create(text, regexp, case_sensitive)

    def set_rule_filter(self, class_name, args, rule):
        if class_name is not None and args is not None:
            if self.filter_factory is None:
                raise UnsupportedFilter(class_name)
            if isinstance(rule, R.RegexPatternRule):
                f = self.filter_factory.get_regex_filter(class_name, self.language)
                rule.regex_filter = f
                rule.filter_args = args
            else:
                f = self.filter_factory.get_filter(class_name, self.language)
                rule.filter = f
                rule.filter_args = args


class PatternRuleHandler(XMLRuleHandler):

    def __init__(self, language, source_file=None, filter_factory=None, messages=None):
        super().__init__(language, filter_factory)
        self.source_file = source_file
        self.messages = messages or {}
        self.category = None
        self.category_issue_type = self.rule_group_issue_type = self.rule_issue_type = None
        self.name = None
        self.filter_class_name = None
        self.filter_args = None
        self.rulegroup_anti_patterns = []
        self.rule_anti_patterns = []
        self.sub_id = 0
        self.interpret_pos_tags_pre_disambiguation = False
        self.default_off = self.default_temp_off = False
        self.rule_group_default_off = self.rule_group_default_temp_off = False
        self.rule_group_description = None
        self.start_pos = -1
        self.end_pos = -1
        self.token_count_for_marker = 0
        self.anti_pattern_counter = 0
        self.in_rule = False
        self.in_anti_pattern = False
        self.is_rule_suppress_misspelled = False
        self.is_suggestion_suppress_misspelled = False
        self.min_prev_matches = 0
        self.rule_group_min_prev_matches = 0
        self.distance_tokens = 0
        self.rule_group_distance_tokens = 0
        self.id_prefix = None
        self.skipped_rules = []

    def start_element(self, q, attrs):
        if q == 'category':
            cat_name = attrs.get('name')
            self.premium_category_attribute = attrs.get('premium')
            cat_id = attrs.get('id')
            location = 'EXTERNAL' if attrs.get('external') == YES else 'INTERNAL'
            on = attrs.get('default') != OFF
            self.category = Category(cat_id, cat_name, location, on, attrs.get('tab'))
            if attrs.get('type') is not None:
                self.category_issue_type = attrs.get('type')
            if attrs.get('tags') is not None:
                self.category_tags.extend(attrs.get('tags').split(' '))
            if attrs.get('tone_tags') is not None:
                self.category_tone_tags.extend(attrs.get('tone_tags').split(' '))
            self.is_goal_specific_category_attribute = attrs.get('is_goal_specific')
            if attrs.get('prio') is not None:
                self.prio_category_attribute = int(attrs.get('prio'))
        elif q == 'rules':
            self.premium_file_attribute = attrs.get('premium')
            self.id_prefix = attrs.get('idprefix')
        elif q == 'regexp':
            self.in_regex = True
            self.regex_mode_exact = attrs.get('type') == 'exact'
            self.regex_case_sensitive = attrs.get('case_sensitive') == YES
            self.regexp_mark = int(attrs.get('mark')) if attrs.get('mark') is not None else 0
        elif q == 'rule':
            self.regex = []
            self.in_rule = True
            self.short_message = []
            self.message = []
            self.suggestions_out_msg = []
            self.url = []
            self.id = attrs.get('id')
            self.name = attrs.get('name')
            mpm = attrs.get('min_prev_matches')
            if mpm is not None:
                if self.in_rule_group and self.rule_group_min_prev_matches > 0:
                    raise RuleLoadError('Rule group %s has min_prev_matches, thus rule %s cannot specify it' % (
                        self.rule_group_id, self.id))
                self.min_prev_matches = int(mpm)
            else:
                self.min_prev_matches = self.rule_group_min_prev_matches
            dt = attrs.get('distance_tokens')
            if dt is not None:
                if self.in_rule_group and self.rule_group_distance_tokens > 0:
                    raise RuleLoadError('Rule group %s has distance_tokens, thus rule %s cannot specify it' % (
                        self.rule_group_id, self.id))
                self.distance_tokens = int(dt)
            else:
                self.distance_tokens = self.rule_group_distance_tokens
            premium = attrs.get('premium')
            for v in (premium, self.premium_rule_group_attribute, self.premium_category_attribute,
                      self.premium_file_attribute):
                if v is not None:
                    if v == YES:
                        self.is_premium_rule = True
                    elif v == 'no':
                        self.is_premium_rule = False
                    break
            else:
                self.is_premium_rule = False
            if self.in_rule_group:
                self.sub_id += 1
                if self.id is None:
                    self.id = self.rule_group_id
                if self.name is None:
                    self.name = self.rule_group_description
            if self.id is None:
                raise RuleLoadError("id is null for rule with name '%s'" % self.name)
            if self.id_prefix is not None:
                self.id = self.id_prefix + self.id
            if self.in_rule_group and (self.rule_group_default_off or self.rule_group_default_temp_off) and \
                    attrs.get('default') is not None:
                raise RuleLoadError('Rule group %s is off by default, thus a subrule cannot specify default=...' %
                                    self.rule_group_id)
            if self.in_rule_group and self.rule_group_default_off:
                self.default_off = True
            elif self.in_rule_group and self.rule_group_default_temp_off:
                self.default_temp_off = True
            else:
                self.default_off = attrs.get('default') == OFF
                self.default_temp_off = attrs.get('default') == TEMP_OFF
            self.correct_examples = []
            self.antipattern_examples = []
            self.incorrect_examples = []
            self.error_triggering_examples = []
            self.suggestion_matches = []
            self.suggestion_matches_out_msg = []
            if attrs.get('type') is not None:
                self.rule_issue_type = attrs.get('type')
            self.is_rule_suppress_misspelled = False
            if attrs.get('tags') is not None:
                self.rule_tags.extend(attrs.get('tags').split(' '))
            if attrs.get('tone_tags') is not None:
                self.rule_tone_tags.extend(attrs.get('tone_tags').split(' '))
            gs = attrs.get('is_goal_specific')
            for v in (gs, self.is_goal_specific_rule_group_attribute, self.is_goal_specific_category_attribute):
                if v is not None:
                    if v == 'true':
                        self.is_goal_specific = True
                    elif v == 'false':
                        self.is_goal_specific = False
                    break
            else:
                self.is_goal_specific = False
            if attrs.get('prio') is not None:
                self.prio_rule_attribute = int(attrs.get('prio'))
            self.current_filter_error = None
        elif q == 'pattern':
            self.start_pattern(attrs)
            self.token_count_for_marker = 0
            self.interpret_pos_tags_pre_disambiguation = attrs.get('raw_pos') == YES
        elif q == 'antipattern':
            self.in_anti_pattern = True
            self.anti_pattern_counter += 1
            self.case_sensitive = attrs.get('case_sensitive') == YES
            self.token_counter = 0
            self.token_count_for_marker = 0
        elif q == 'and':
            self.in_and_group = True
            self.token_count_for_marker += 1
        elif q == 'or':
            self.in_or_group = True
            self.token_count_for_marker += 1
        elif q == 'unify':
            self.in_unification = True
            self.uni_negation = attrs.get('negate') == YES
        elif q == 'unify-ignore':
            self.in_unification_neutral = True
        elif q == 'feature':
            self.u_feature = attrs.get('id')
        elif q == 'type':
            self.u_type = attrs.get('id')
            self.u_type_list.append(self.u_type)
        elif q == 'token':
            self.set_token(attrs)
            if not self.in_and_group and not self.in_or_group:
                self.token_count_for_marker += 1
        elif q == 'exception':
            self.set_exceptions(attrs)
        elif q == 'example':
            type_val = attrs.get('type')
            if self.in_anti_pattern:
                if self.in_rule_group and not self.in_rule:
                    self.in_anti_pattern_for_rule_group_example = True
                    self.anti_pattern_for_rule_group_example = []
                else:
                    self.in_anti_pattern_example = True
                    self.anti_pattern_example = []
            elif type_val == 'incorrect' or attrs.get('correction') is not None:
                self.in_incorrect_example = True
                self.incorrect_example = []
                if attrs.get('correction') is not None:
                    self.example_correction = attrs.get('correction')
            elif type_val == 'triggers_error':
                self.in_error_trigger_example = True
                self.error_trigger_example = []
            else:
                self.in_correct_example = True
                self.correct_example = []
        elif q == 'filter':
            self.filter_class_name = attrs.get('class')
            self.filter_args = attrs.get('args')
        elif q == 'message':
            self.in_message = True
            self.in_suggestion = False
            self.message = []
            self.is_rule_suppress_misspelled = attrs.get('suppress_misspelled') == YES
            if self.is_rule_suppress_misspelled:
                self.message.append(PLEASE_SPELL_ME)
        elif q == 'suggestion':
            s = '<suggestion>'
            self.is_suggestion_suppress_misspelled = attrs.get('suppress_misspelled') == YES
            if self.is_suggestion_suppress_misspelled or self.is_rule_suppress_misspelled:
                s += PLEASE_SPELL_ME
            if self.in_message:
                self.message.append(s)
            else:
                self.suggestions_out_msg.append(s)
            self.in_suggestion = True
        elif q == 'short':
            if self.in_rule:
                self.in_short_message = True
                self.short_message = []
            else:
                self.in_short_message_for_rule_group = True
                self.short_message_for_rule_group = []
        elif q == 'url':
            if self.in_rule:
                self.in_url = True
                self.url = []
            else:
                self.in_url_for_rule_group = True
                self.url_for_rule_group = []
        elif q == 'rulegroup':
            self.rule_group_id = attrs.get('id')
            self.premium_rule_group_attribute = attrs.get('premium')
            self.rule_group_description = attrs.get('name')
            self.rule_group_default_off = attrs.get('default') == OFF
            self.rule_group_default_temp_off = attrs.get('default') == TEMP_OFF
            self.url_for_rule_group = []
            self.short_message_for_rule_group = []
            self.in_rule_group = True
            self.sub_id = 0
            if attrs.get('type') is not None:
                self.rule_group_issue_type = attrs.get('type')
            if attrs.get('tags') is not None:
                self.rule_group_tags.extend(attrs.get('tags').split(' '))
            if attrs.get('tone_tags') is not None:
                self.rule_group_tone_tags.extend(attrs.get('tone_tags').split(' '))
            self.is_goal_specific_rule_group_attribute = attrs.get('is_goal_specific')
            if attrs.get('min_prev_matches') is not None:
                self.rule_group_min_prev_matches = int(attrs.get('min_prev_matches'))
            if attrs.get('distance_tokens') is not None:
                self.rule_group_distance_tokens = int(attrs.get('distance_tokens'))
            self.antipattern_for_rule_groups_examples = []
            if attrs.get('prio') is not None:
                self.prio_rule_group_attribute = int(attrs.get('prio'))
        elif q == 'match':
            self.set_match_element(attrs, self.in_suggestion and (self.is_suggestion_suppress_misspelled or
                                                                  self.is_rule_suppress_misspelled))
        elif q == 'marker':
            if self.in_marker:
                raise RuleLoadError("'<marker>' may not be nested in rule '%s'" % self.id)
            if self.in_incorrect_example:
                self.incorrect_example.append(MARKER_TAG)
            elif self.in_correct_example:
                self.correct_example.append(MARKER_TAG)
            elif self.in_error_trigger_example:
                self.error_trigger_example.append(MARKER_TAG)
            elif self.in_pattern or self.in_anti_pattern:
                self.start_pos = self.token_counter
                self.in_marker = True
        elif q == 'unification':
            self.u_feature = attrs.get('feature')
            self.in_unification_def = True
        elif q == 'equivalence':
            self.u_type = attrs.get('type')
        elif q == 'phrases':
            self.in_phrases = True
        elif q == 'phrase':
            if self.in_phrases:
                self.phrase_id = attrs.get('id')
        elif q == 'phraseref':
            if attrs.get('idref') is not None:
                self.prepare_phrase(attrs)
                self.token_count_for_marker += 1

    def end_element(self, q):
        if q == 'category':
            self.category_issue_type = None
            self.category_tags = []
            self.category_tone_tags = []
            self.is_goal_specific = False
            self.premium_category_attribute = None
            self.is_goal_specific_category_attribute = None
            self.prio_category_attribute = 0
        elif q == 'regexp':
            self.in_regex = False
        elif q == 'rule':
            self.suggestion_matches_out_msg = self.add_legacy_matches(
                self.suggestion_matches_out_msg, ''.join(self.suggestions_out_msg), False)
            if not self.phrase_pattern_tokens:
                self.create_rules(list(self.pattern_tokens), [], 0)
            else:
                if self.pattern_tokens:
                    for ph in self.phrase_pattern_tokens:
                        ph.extend(self.pattern_tokens)
                for ph in self.phrase_pattern_tokens:
                    self.process_element(ph)
                    self.create_rules(ph, [], 0)
            self.pattern_tokens = []
            self.phrase_pattern_tokens = []
            self.rule_issue_type = None
            self.in_rule = False
            self.filter_class_name = None
            self.filter_args = None
            self.min_prev_matches = 0
            self.distance_tokens = 0
            self.rule_tags = []
            self.rule_tone_tags = []
            self.is_premium_rule = False
            self.is_goal_specific = False
            self.prio_rule_attribute = 0
        elif q == 'exception':
            self.finalize_exceptions()
        elif q == 'and':
            self.in_and_group = False
            self.and_group_counter = 0
            self.token_counter += 1
        elif q == 'or':
            self.in_or_group = False
            self.or_group_counter = 0
            self.token_counter += 1
        elif q == 'token':
            self.finalize_tokens(self.language.unifier_config)
        elif q == 'pattern':
            self.in_pattern = False
            if self.last_phrase:
                self.pattern_tokens = []
            self.token_counter = 0
        elif q == 'antipattern':
            anti_id = self.id
            if self.in_rule_group:
                anti_id = '%s[%d]' % (self.rule_group_id, self.sub_id) if self.sub_id > 0 else self.rule_group_id
            rule = R.DisambiguationPatternRule('%s_antipattern:%d' % (anti_id, self.anti_pattern_counter),
                                               'antipattern', self.language, self.pattern_tokens, None, None,
                                               R.IMMUNIZE)
            rule.unifier_config = self.language.disambiguation_unifier_config
            rule.xml_line_number = self.xml_line_number_anti_pattern
            if self.start_pos != -1 and self.end_pos != -1:
                rule.start_position_correction = self.start_pos
                rule.end_position_correction = self.end_pos - self.token_count_for_marker
            else:
                for t in self.pattern_tokens:
                    t.inside_marker = True
            self.pattern_tokens = []
            if self.in_rule:
                self.rule_anti_patterns.append(rule)
            else:
                self.rulegroup_anti_patterns.append(rule)
            self.token_counter = 0
            self.in_anti_pattern = False
            self.end_pos = -1
            self.start_pos = -1
            self.in_anti_pattern_example = False
            self.xml_line_number_anti_pattern = -1
        elif q == 'example':
            if self.in_anti_pattern_example:
                self.antipattern_examples.append(Example(''.join(self.anti_pattern_example)))
            elif self.in_anti_pattern_for_rule_group_example:
                self.antipattern_for_rule_groups_examples.append(Example(''.join(
                    self.anti_pattern_for_rule_group_example)))
            elif self.in_correct_example:
                self.correct_examples.append(Example(''.join(self.correct_example)))
            elif self.in_incorrect_example:
                if self.in_anti_pattern:
                    raise RuleLoadError('<antipattern>s can only contain <example>s without errors')
                if self.example_correction is None:
                    ex = Example(''.join(self.incorrect_example))
                else:
                    corrections = [c for c in self.example_correction.split('|')]
                    # Java's split() drops trailing empty strings, then adds back one if the value ends with |
                    while corrections and corrections[-1] == '':
                        corrections.pop()
                    if self.example_correction.endswith('|'):
                        corrections.append('')
                    ex = Example(''.join(self.incorrect_example), corrections)
                self.incorrect_examples.append(ex)
            elif self.in_error_trigger_example:
                self.error_triggering_examples.append(Example(''.join(self.error_trigger_example)))
            self.in_correct_example = self.in_incorrect_example = self.in_error_trigger_example = False
            self.correct_example = []
            self.incorrect_example = []
            self.error_trigger_example = []
            self.example_correction = None
            self.anti_pattern_example = []
            self.anti_pattern_for_rule_group_example = []
            self.in_anti_pattern_example = self.in_anti_pattern_for_rule_group_example = False
        elif q == 'message':
            self.suggestion_matches = self.add_legacy_matches(self.suggestion_matches, ''.join(self.message), True)
            self.in_message = False
        elif q == 'suggestion':
            if self.in_message:
                self.message.append('</suggestion>')
            else:
                self.suggestions_out_msg.append('</suggestion>')
            self.in_suggestion = False
        elif q == 'short':
            self.in_short_message = False
            self.in_short_message_for_rule_group = False
        elif q == 'url':
            self.in_url = False
            self.in_url_for_rule_group = False
        elif q == 'match':
            if self.in_message:
                self.suggestion_matches[-1].set_lemma_string(''.join(self.match))
            elif self.in_suggestion:
                self.suggestion_matches_out_msg[-1].set_lemma_string(''.join(self.match))
            elif self.in_token:
                self.token_reference.set_lemma_string(''.join(self.match))
            self.in_match = False
        elif q == 'rulegroup':
            self.url_for_rule_group = []
            self.short_message_for_rule_group = []
            self.in_rule_group = False
            self.rule_group_issue_type = None
            self.rulegroup_anti_patterns = []
            self.anti_pattern_counter = 0
            self.rule_group_default_off = self.rule_group_default_temp_off = False
            self.default_off = self.default_temp_off = False
            self.rule_group_min_prev_matches = 0
            self.rule_group_distance_tokens = 0
            self.rule_group_tags = []
            self.rule_group_tone_tags = []
            self.premium_rule_group_attribute = None
            self.is_goal_specific_rule_group_attribute = None
            self.antipattern_for_rule_groups_examples = []
            self.prio_rule_group_attribute = 0
        elif q == 'marker':
            if self.in_correct_example:
                self.correct_example.append('</marker>')
            elif self.in_incorrect_example:
                self.incorrect_example.append('</marker>')
            elif self.in_error_trigger_example:
                self.error_trigger_example.append('</marker>')
            elif self.in_pattern or self.in_anti_pattern:
                self.end_pos = self.token_count_for_marker
                self.in_marker = False
        elif q == 'phrase':
            if self.in_phrases:
                self.finalize_phrase()
        elif q == 'includephrases':
            self.pattern_tokens = []
        elif q == 'phrases':
            if self.in_phrases:
                self.in_phrases = False
        elif q == 'unification':
            self.in_unification_def = False
        elif q == 'feature':
            self.equivalence_features[self.u_feature] = self.u_type_list
            self.u_type_list = []
        elif q == 'unify':
            self.in_unification = False
            self.equivalence_features = {}
            last = self.pattern_tokens[-1]
            last.last_in_unification = True
            if self.uni_negation:
                last.uni_negation = True
        elif q == 'unify-ignore':
            self.in_unification_neutral = False

    def create_rules(self, elem_list, tmp_tokens, num_element):
        short_message = ''
        if self.short_message:
            short_message = ''.join(self.short_message)
        elif self.short_message_for_rule_group:
            short_message = ''.join(self.short_message_for_rule_group)
        if self.min_prev_matches > 0 and not short_message:
            short_message = self.messages.get('desc_repetition_short', '')
        if num_element >= len(elem_list):
            if tmp_tokens:
                rule = R.PatternRule(self.id, self.language, tmp_tokens, self.name, ''.join(self.message),
                                     short_message, ''.join(self.suggestions_out_msg),
                                     len(self.phrase_pattern_tokens) > 1, self.interpret_pos_tags_pre_disambiguation)
                rule.add_tags(self.rule_tags)
                rule.add_tags(self.rule_group_tags)
                rule.add_tags(self.category_tags)
                rule.add_tone_tags(self.rule_tone_tags)
                rule.add_tone_tags(self.rule_group_tone_tags)
                rule.source_file = self.source_file
                rule.min_prev_matches = self.min_prev_matches
                rule.distance_tokens = self.distance_tokens
                rule.xml_line_number = self.xml_line_number
            elif self.regex:
                flags = jregex.UNICODE_CHARACTER_CLASS | (0 if self.regex_case_sensitive else jregex.IGNORECASE)
                regex_str = ''.join(self.regex)
                if not self.regex_mode_exact:
                    regex_str = replace_spaces_in_regex(regex_str)
                if self.rule_anti_patterns or self.rulegroup_anti_patterns:
                    raise RuleLoadError('<regexp> rules currently cannot be used together with <antipattern>. '
                                        'Rule id: %s[%d]' % (self.id, self.sub_id))
                jregex.translate(regex_str, flags)  # check syntax
                rule = R.RegexPatternRule(self.id, self.name, ''.join(self.message), short_message,
                                          ''.join(self.suggestions_out_msg), self.language,
                                          (regex_str, flags), self.regexp_mark, self.regex_case_sensitive)
                rule.source_file = self.source_file
            else:
                raise RuleLoadError("Neither '<pattern>' tokens nor '<regexp>' is set in rule '%s'" % self.id)
            filter_ok = True
            try:
                self.set_rule_filter(self.filter_class_name, self.filter_args, rule)
            except UnsupportedFilter as e:
                filter_ok = False
                self.skipped_rules.append((self.id, self.sub_id, 'unsupported filter: %s' % e))
            self.prepare_rule(rule)
            if filter_ok:
                self.rules.append(rule)
        else:
            pt = elem_list[num_element]
            if pt.has_or_group():
                sm_backup = list(self.suggestion_matches)
                smo_backup = list(self.suggestion_matches_out_msg)
                sp_backup, ep_backup = self.start_pos, self.end_pos
                rap_backup = list(self.rule_anti_patterns)
                for t in pt.or_group:
                    tmp2 = list(tmp_tokens)
                    tmp2.append(t.clone())
                    self.create_rules(elem_list, tmp2, num_element + 1)
                    self.start_pos, self.end_pos = sp_backup, ep_backup
                    self.suggestion_matches = sm_backup
                    self.suggestion_matches_out_msg = smo_backup
                    self.rule_anti_patterns.extend(rap_backup)
            tmp_tokens.append(pt.clone())
            self.create_rules(elem_list, tmp_tokens, num_element + 1)

    def prepare_rule(self, rule):
        rule.premium = self.is_premium_rule
        rule.source_file = self.source_file
        if self.start_pos != -1 and self.end_pos != -1:
            rule.start_position_correction = self.start_pos
            rule.end_position_correction = self.end_pos - self.token_count_for_marker
        self.start_pos = -1
        self.end_pos = -1
        rule.correct_examples = list(self.correct_examples) + list(self.antipattern_examples) + list(
            self.antipattern_for_rule_groups_examples)
        rule.incorrect_examples = list(self.incorrect_examples)
        rule.error_triggering_examples = list(self.error_triggering_examples)
        rule.category = self.category
        if self.rulegroup_anti_patterns:
            rule.set_anti_patterns(self.rulegroup_anti_patterns)
        if self.rule_anti_patterns:
            rule.set_anti_patterns(self.rule_anti_patterns)
            self.rule_anti_patterns = []
        rule.add_tags(self.rule_tags)
        rule.add_tags(self.rule_group_tags)
        rule.add_tags(self.category_tags)
        rule.add_tone_tags(self.rule_tone_tags)
        rule.add_tone_tags(self.rule_group_tone_tags)
        rule.add_tone_tags(self.category_tone_tags)
        rule.goal_specific = self.is_goal_specific
        rule.sub_id = str(self.sub_id) if self.in_rule_group else '1'
        self.case_sensitive = False
        for m in self.suggestion_matches:
            rule.add_suggestion_match(m)
        if len(self.phrase_pattern_tokens) <= 1:
            self.suggestion_matches = []
        for m in self.suggestion_matches_out_msg:
            rule.add_suggestion_match_out_msg(m)
        self.suggestion_matches_out_msg = []
        if self.category is None:
            raise RuleLoadError("Cannot activate rule '%s', it is outside of a <category>...</category>" % self.id)
        if self.default_off:
            rule.set_default_off()
        if self.default_temp_off:
            rule.set_default_temp_off()
        if self.url:
            rule.url = ''.join(self.url)
        elif self.url_for_rule_group:
            rule.url = ''.join(self.url_for_rule_group)
        it = self.rule_issue_type or self.rule_group_issue_type or self.category_issue_type
        if it is not None:
            rule.loc_quality_issue_type = its_issue_type(it)
        prio = 0
        if self.prio_category_attribute != 0:
            prio = self.prio_category_attribute
        if self.prio_rule_group_attribute != 0:
            prio = self.prio_rule_group_attribute
        if self.prio_rule_attribute != 0:
            prio = self.prio_rule_attribute
        rule.priority = prio

    def characters(self, s):
        if self.in_exception:
            self.exceptions.append(s)
        elif self.in_token:
            self.elements.append(s)
        elif self.in_correct_example:
            self.correct_example.append(s)
        elif self.in_anti_pattern_example:
            self.anti_pattern_example.append(s)
        elif self.in_anti_pattern_for_rule_group_example:
            self.anti_pattern_for_rule_group_example.append(s)
        elif self.in_incorrect_example:
            self.incorrect_example.append(s)
        elif self.in_error_trigger_example:
            self.error_trigger_example.append(s)
        elif self.in_match:
            self.match.append(s)
        elif self.in_message:
            self.message.append(s)
        elif self.in_suggestion:
            self.suggestions_out_msg.append(s)
        elif self.in_short_message:
            self.short_message.append(s)
        elif self.in_short_message_for_rule_group:
            self.short_message_for_rule_group.append(s)
        elif self.in_url:
            self.url.append(s)
        elif self.in_url_for_rule_group:
            self.url_for_rule_group.append(s)
        elif self.in_regex:
            self.regex.append(s)


def replace_spaces_in_regex(s):
    out = []
    in_bracket = False
    for c in s:
        if c == '[':
            in_bracket = True
        elif c == ']':
            in_bracket = False
        if c == ' ' and not in_bracket:
            out.append('(?:[\\s  ]+)')
        else:
            out.append(c)
    return ''.join(out)


class DisambiguationRuleHandler(XMLRuleHandler):

    def __init__(self, language, source_file=None, filter_factory=None):
        super().__init__(language, filter_factory)
        self.source_file = source_file
        self.disamb_rules = []
        self.in_disambiguation = False
        self.sub_id = 0
        self.name = None
        self.rule_group_name = None
        self.filter_class_name = None
        self.filter_args = None
        self.disamb = []
        self.wd = []
        self.example = []
        self.anti_pattern_counter = 0
        self.in_rule = False
        self.rulegroup_anti_patterns = []
        self.rule_anti_patterns = []
        self.in_anti_pattern = False
        self.in_word = False
        self.disambiguated_pos = None
        self.start_pos = -1
        self.end_pos = -1
        self.token_count_for_marker = 0
        self.pos_selector = None
        self.uni_counter = 0
        self.new_wd_list = None
        self.wd_lemma = None
        self.wd_pos = None
        self.in_example = False
        self.untouched = False
        self.untouched_examples = None
        self.disamb_examples = None
        self.input = None
        self.output = None
        self.disambig_action = None
        self.skipped_rules = []

    @property
    def unifier_config(self):
        return self.language.disambiguation_unifier_config

    def start_element(self, q, attrs):
        if q == 'rule':
            self.in_rule = True
            self.id = attrs.get('id')
            if self.in_rule_group:
                self.sub_id += 1
            self.name = attrs.get('name')
            if self.in_rule_group and self.id is None:
                self.id = self.rule_group_id
            if self.in_rule_group and self.name is None:
                self.name = self.rule_group_name
        elif q == 'pattern':
            self.in_pattern = True
            self.token_count_for_marker = 0
            if attrs.get('case_sensitive') == YES:
                self.case_sensitive = True
        elif q == 'antipattern':
            self.in_anti_pattern = True
            self.anti_pattern_counter += 1
            self.case_sensitive = attrs.get('case_sensitive') == YES
            self.token_counter = 0
            self.token_count_for_marker = 0
        elif q == 'exception':
            self.set_exceptions(attrs)
        elif q == 'and':
            self.in_and_group = True
            self.token_count_for_marker += 1
            if self.in_unification:
                self.uni_counter += 1
        elif q == 'unify':
            self.in_unification = True
            self.uni_negation = attrs.get('negate') == YES
            self.uni_counter = 0
        elif q == 'unify-ignore':
            self.in_unification_neutral = True
        elif q == 'feature':
            self.u_feature = attrs.get('id')
        elif q == 'type':
            self.u_type = attrs.get('id')
            self.u_type_list.append(self.u_type)
        elif q == 'token':
            self.set_token(attrs)
            if not self.in_and_group:
                self.token_count_for_marker += 1
        elif q == 'disambig':
            self.in_disambiguation = True
            self.disambiguated_pos = attrs.get('postag')
            a = attrs.get('action')
            self.disambig_action = R.REPLACE if a is None else a.upper()
            if self.disambig_action not in R.DISAMBIGUATOR_ACTIONS:
                raise RuleLoadError('Unknown disambiguator action: %s' % a)
            self.disamb = []
        elif q == 'match':
            self.in_match = True
            self.match = []
            cc = CASE_NONE
            if attrs.get('case_conversion') is not None:
                cc = CASE_CONVERSIONS[attrs.get('case_conversion').lower()]
            ir = INCLUDE_NONE
            if attrs.get('include_skipped') is not None:
                ir = INCLUDE_RANGES[attrs.get('include_skipped').lower()]
            m = Match(attrs.get('postag'), attrs.get('postag_replace'), attrs.get('postag_regexp') == YES,
                      attrs.get('regexp_match'), attrs.get('regexp_replace'), cc, attrs.get('setpos') == YES,
                      attrs.get('suppress_mispelled') == YES, ir)
            if self.in_disambiguation:
                if attrs.get('no') is not None:
                    ref = int(attrs.get('no'))
                    self._ref_check(ref)
                    m.token_ref = ref
                    self.pos_selector = m
            elif self.in_token and attrs.get('no') is not None:
                ref = int(attrs.get('no'))
                self._ref_check(ref)
                m.token_ref = ref
                self.token_reference = m
                self.elements.append('\\')
                self.elements.append(str(ref))
        elif q == 'rulegroup':
            self.rule_group_id = attrs.get('id')
            self.rule_group_name = attrs.get('name')
            self.in_rule_group = True
            self.sub_id = 0
            self.rulegroup_anti_patterns = []
            self.anti_pattern_counter = 0
        elif q == 'unification':
            self.u_feature = attrs.get('feature')
            self.in_unification_def = True
        elif q == 'equivalence':
            self.u_type = attrs.get('type')
        elif q == 'wd':
            self.wd_lemma = attrs.get('lemma')
            self.wd_pos = attrs.get('pos')
            self.in_word = True
            self.wd = []
        elif q == 'example':
            self.in_example = True
            if self.untouched_examples is None:
                self.untouched_examples = []
            if self.disamb_examples is None:
                self.disamb_examples = []
            t = attrs.get('type')
            self.untouched = t == 'untouched'
            if t == 'ambiguous':
                self.input = attrs.get('inputform')
                self.output = attrs.get('outputform')
            self.example = []
        elif q == 'filter':
            self.filter_class_name = attrs.get('class')
            self.filter_args = attrs.get('args')
        elif q == 'marker':
            if self.in_marker:
                raise RuleLoadError("'<marker>' may not be nested in rule '%s'" % self.id)
            self.example.append('<marker>')
            if self.in_pattern or self.in_anti_pattern:
                self.start_pos = self.token_counter
                self.in_marker = True

    def _ref_check(self, ref):
        if ref > len(self.pattern_tokens):
            raise RuleLoadError('Only backward references in match elements are possible, tried to specify token %d'
                                % ref)

    def end_element(self, q):
        if q == 'rule':
            rule = R.DisambiguationPatternRule(self.id, self.name, self.language, self.pattern_tokens,
                                               self.disambiguated_pos, self.pos_selector, self.disambig_action)
            rule.unifier_config = self.unifier_config
            rule.source_file = self.source_file
            self.end_position_correction = self.end_pos - self.token_count_for_marker
            if self.start_pos != -1 and self.end_pos != -1:
                rule.start_position_correction = self.start_pos
                rule.end_position_correction = self.end_position_correction
            else:
                self.start_pos = 0
                self.end_pos = self.token_count_for_marker
            rule.sub_id = str(self.sub_id) if self.in_rule_group else '1'
            matched_token_count = self.end_pos - self.start_pos
            if self.new_wd_list is not None:
                if self.disambig_action in (R.ADDCHUNK, R.ADD, R.REMOVE, R.REPLACE):
                    if self.new_wd_list and self.disambig_action == R.REPLACE and \
                            len(self.new_wd_list) != matched_token_count:
                        raise RuleLoadError('%s rule error. The number of interpretations specified with wd: %d must '
                                            'be equal to the number of matched tokens (%d)' % (
                                                self.id, len(self.new_wd_list), matched_token_count))
                    rule.set_new_interpretations(self.new_wd_list)
                self.new_wd_list = []
            self.case_sensitive = False
            if self.disamb_examples is not None:
                rule.examples = self.disamb_examples
            if self.untouched_examples is not None:
                rule.untouched_examples = self.untouched_examples
            filter_ok = True
            try:
                self.set_rule_filter(self.filter_class_name, self.filter_args, rule)
            except UnsupportedFilter as e:
                filter_ok = False
                self.skipped_rules.append((self.id, self.sub_id, 'unsupported filter: %s' % e))
            if self.rulegroup_anti_patterns:
                rule.set_anti_patterns(self.rulegroup_anti_patterns)
            if self.rule_anti_patterns:
                rule.set_anti_patterns(self.rule_anti_patterns)
                self.rule_anti_patterns = []
            if filter_ok:
                self.rules.append(rule)
            if self.disambig_action == R.UNIFY and matched_token_count != self.uni_counter:
                raise RuleLoadError('%s rule error. The number unified tokens: %d must be equal to the number of '
                                    'matched tokens: %d' % (self.id, self.uni_counter, matched_token_count))
            single_token_correction = self.end_pos - self.start_pos > 1
            if (not single_token_correction and self.disambig_action in (R.FILTER, R.REPLACE)) and \
                    matched_token_count > 1:
                raise RuleLoadError('Cannot replace or filter more than one token at a time.')
            self.pattern_tokens = []
            self.pos_selector = None
            self.disamb_examples = None
            self.untouched_examples = None
            self.start_pos = -1
            self.end_pos = -1
            self.filter_class_name = None
            self.filter_args = None
            self.in_rule = False
        elif q == 'exception':
            self.finalize_exceptions()
        elif q == 'and':
            self.in_and_group = False
            self.and_group_counter = 0
            self.token_counter += 1
        elif q == 'token':
            if self.in_unification and not self.in_and_group:
                self.uni_counter += 1
            self.finalize_tokens(self.unifier_config)
        elif q == 'pattern':
            self.in_pattern = False
            self.token_counter = 0
        elif q == 'match':
            if self.in_disambiguation:
                self.pos_selector.set_lemma_string(''.join(self.match))
            elif self.in_token:
                self.token_reference.set_lemma_string(''.join(self.match))
            self.in_match = False
        elif q == 'disambig':
            self.in_disambiguation = False
        elif q == 'rulegroup':
            self.in_rule_group = False
        elif q == 'unification':
            if self.in_unification_def:
                self.in_unification_def = False
                self.token_counter = 0
        elif q == 'feature':
            self.equivalence_features[self.u_feature] = self.u_type_list
            self.u_type_list = []
        elif q == 'unify':
            self.in_unification = False
            self.equivalence_features = {}
            last = self.pattern_tokens[-1]
            last.last_in_unification = True
            if self.uni_negation:
                last.uni_negation = True
        elif q == 'unify-ignore':
            self.in_unification_neutral = False
        elif q == 'wd':
            if self.new_wd_list is None:
                self.new_wd_list = []
            self.new_wd_list.append(AnalyzedToken(''.join(self.wd), self.wd_pos, self.wd_lemma))
            self.in_word = False
        elif q == 'antipattern':
            rule = R.DisambiguationPatternRule('%s_antipattern:%d' % (self.id, self.anti_pattern_counter),
                                               'antipattern', self.language, self.pattern_tokens, None, None,
                                               R.IMMUNIZE)
            rule.unifier_config = self.unifier_config
            if self.start_pos != -1 and self.end_pos != -1:
                rule.start_position_correction = self.start_pos
                rule.end_position_correction = self.end_pos - self.token_count_for_marker
            self.pattern_tokens = []
            if self.in_rule:
                self.rule_anti_patterns.append(rule)
            else:
                self.rulegroup_anti_patterns.append(rule)
            self.token_counter = 0
            self.in_anti_pattern = False
        elif q == 'example':
            self.in_example = False
            if self.untouched:
                self.untouched_examples.append(''.join(self.example))
            else:
                self.disamb_examples.append((''.join(self.example), self.input, self.output))
        elif q == 'marker':
            self.example.append('</marker>')
            if self.in_pattern or self.in_anti_pattern:
                self.end_pos = self.token_count_for_marker
                self.in_marker = False

    def characters(self, s):
        if self.in_exception:
            self.exceptions.append(s)
        elif self.in_token and (self.in_pattern or self.in_anti_pattern):
            self.elements.append(s)
        elif self.in_match:
            self.match.append(s)
        elif self.in_word:
            self.wd.append(s)
        elif self.in_disambiguation:
            self.disamb.append(s)
        elif self.in_example:
            self.example.append(s)


def load_pattern_rules(path, language, resource_dir, filter_factory=None, messages=None):
    h = PatternRuleHandler(language, path, filter_factory, messages)
    parse_events(path, h, resource_dir)
    return h.rules, h.skipped_rules


def load_disambiguation_rules(path, language, resource_dir, filter_factory=None):
    h = DisambiguationRuleHandler(language, path, filter_factory)
    parse_events(path, h, resource_dir)
    return h.rules, h.skipped_rules
