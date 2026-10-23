"""Ports of the abstract rule classes of languagetool-core
(org.languagetool.rules.*) which the language modules subclass: simple
replacement rules, compound rules, word coherency, repetitions, style
statistics etc.

The subclasses supply the data files and messages by overriding the
corresponding methods, file paths are given like in Java, e.g.
'/de/coherency.txt', relative to the rules or resource directory.
"""

import math
import os

import regex

from .. import jregex
from ..analysis import AnalyzedToken, AnalyzedTokenReadings, SENTENCE_START_TAGNAME, SENTENCE_END_TAGNAME
from ..messages import message_format
from ..tools import (is_all_uppercase, is_capitalized_word, starts_with_uppercase, uppercase_first_char,
                     lowercase_first_char, is_camel_case, is_punctuation_mark, is_not_word_character, is_digit,
                     is_letter, java_trim, java_split, java_equals_ignore_case, is_emoji, is_numeric_space,
                     is_numeric, preserve_case)
from .base import Rule, RuleMatch, Category
from .core import CoreRule, CoreTextLevelRule, is_paragraph_end


# --- helpers ---------------------------------------------------------------

def _rules_file(language, path):
    from ..language import RULES_DIR
    rel = path.lstrip('/')
    p = os.path.join(language.rules_root, rel)
    if not os.path.exists(p) and language.rules_root != RULES_DIR:
        p = os.path.join(RULES_DIR, rel)
    return p


def _resource_file(language, path):
    return language.resource_path(path.lstrip('/'))


def _read_lines(path):
    with open(path, encoding='utf-8') as f:
        return [line.rstrip('\r\n') for line in f]


def _substring_before(s, sep):
    i = s.find(sep)
    return s if i < 0 else s[:i]


def _first_part(s, sep=' '):
    """s.split(sep)[0] in Java"""
    parts = java_split(s, sep)
    return parts[0] if parts else ''


def _replace_first(literal, repl, s):
    """s.replaceFirst(quote(literal), repl) with Java replacement string
    semantics"""
    if '$' not in repl and '\\' not in repl:
        return s.replace(literal, repl, 1)
    return jregex.java_replace(jregex.compile(regex.escape(literal)), repl, s, 1)


_TO_ID_NONCHAR = regex.compile('[^A-ZÀ-ÖØ-Þ]')


def to_id(s, language):
    """Port of StringTools.toId"""
    s = java_trim(s.upper()).replace(' ', '_').replace("'", '_Q_')
    if language is not None and language.short_code == 'de':
        s = s.replace('Ä', 'AE').replace('Ü', 'UE').replace('Ö', 'OE')
    return _TO_ID_NONCHAR.sub('_', s)


def _java_string_hash(s):
    h = 0
    for c in s:
        o = ord(c)
        if o > 0xffff:
            o -= 0x10000
            for u in (0xd800 + (o >> 10), 0xdc00 + (o & 0x3ff)):
                h = (31 * h + u) & 0xffffffff
        else:
            h = (31 * h + o) & 0xffffffff
    return h


def java_hash_set_order(items):
    """The iteration order of a java.util.HashSet built from items (with the
    default capacity), used where the Java code depends on it."""
    uniq = list(dict.fromkeys(items))
    cap = 16
    while len(uniq) > cap * 0.75:
        cap *= 2

    def bucket(x):
        if x is None:
            return 0
        h = _java_string_hash(x)
        return (h ^ (h >> 16)) & (cap - 1)
    return sorted(uniq, key=bucket)  # sorted() is stable: insertion order within a bucket


def _config_values(user_config, rule_id):
    """Values configured for a rule (UserConfig.getConfigValueByID). The user
    config can be a mapping rule id -> sequence of values, or an object with
    such a mapping as attribute config_values."""
    if user_config is None:
        return None
    m = getattr(user_config, 'config_values', user_config)
    try:
        return m.get(rule_id)
    except AttributeError:
        return None


def _jdiv(a, b):
    """Java double division"""
    if b == 0:
        if a == 0:
            return math.nan
        return math.inf if a > 0 else -math.inf
    return a / b


class SpecificIdRule(Rule):
    """A rule with an id specific for a sub-case of another rule."""

    def __init__(self, id, desc, premium, category, issue_type, tags):
        super().__init__()
        self._id = id
        self._desc = desc
        self.premium = premium
        self.category = category
        if issue_type is not None:
            self.loc_quality_issue_type = issue_type
        self.tags = list(tags)

    def get_id(self):
        return self._id

    def get_description(self):
        return self._desc

    def match(self, sentence):
        return []


def _specific_id_rule(rule, id, desc):
    return SpecificIdRule(id, desc, rule.premium, rule.category, rule.loc_quality_issue_type, rule.tags)


class _RuleBase(CoreRule):
    """CoreRule with the id/description supplied by methods of the
    subclasses (as in the Java abstract classes)."""

    rule_id = None
    description_key = None

    def get_description(self):
        if self.description_key is not None:
            return self.messages[self.description_key]
        raise NotImplementedError()


class _TextLevelRuleBase(CoreTextLevelRule):
    rule_id = None
    description_key = None

    def get_description(self):
        if self.description_key is not None:
            return self.messages[self.description_key]
        raise NotImplementedError()


# --- simple replace rules --------------------------------------------------

_simple_replace_cache = {}


def load_simple_replace_data(path):
    """Port of SimpleReplaceDataLoader.loadWords, path is an absolute file
    path. Returns a dict wrong form -> list of replacements."""
    r = _simple_replace_cache.get(path)
    if r is not None:
        return r
    m = {}
    for line in _read_lines(path):
        if not line or line[0] == '#':
            continue
        parts = java_split(line, '=')
        if len(parts) != 2:
            raise ValueError("Could not load simple replacement data from: %s. Error in line '%s', expected "
                             "format 'word=replacement'" % (path, line))
        if not java_trim(parts[1]):
            raise ValueError("Could not load simple replacement data from: %s. Error in line '%s', replacement "
                             "cannot be empty" % (path, line))
        replacements = java_split(parts[1], '|')
        for wrong in java_split(parts[0], '|'):
            m[wrong] = replacements
    _simple_replace_cache[path] = m
    return m


class AbstractSimpleReplaceRule(_RuleBase):
    """Port of AbstractSimpleReplaceRule: a rule that matches words which
    should not be used and suggests correct ones instead. Subclasses
    implement get_wrong_words() (e.g. with load_from_path())."""

    rule_id = 'SIMPLE_REPLACE'
    category_id = 'MISC'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.ignore_tagged_words = False
        self.sub_rule_specific_ids = False
        self.check_lemmas = True

    def load_from_path(self, *paths):
        """Load the replacement data from the rules directory, e.g.
        load_from_path('/pt/replace.txt')."""
        if len(paths) == 1:
            return load_simple_replace_data(_rules_file(self.language, paths[0]))
        m = {}
        for p in paths:
            m.update(load_simple_replace_data(_rules_file(self.language, p)))
        return m

    def get_wrong_words(self):
        raise NotImplementedError()

    def is_case_sensitive(self):
        return True

    def lower(self, s):
        """String.toLowerCase(getLocale())"""
        return s.lower()

    def set_ignore_tagged_words(self):
        self.ignore_tagged_words = True

    def use_sub_rule_specific_ids(self):
        self.sub_rule_specific_ids = True

    def get_description(self):
        return 'Checks for wrong words/phrases'

    def get_message(self, token_str, replacements):
        return token_str + ' is not valid. Use: ' + ', '.join(replacements) + '.'

    def get_short(self):
        return 'Wrong word'

    def get_synthesizer(self):
        return None

    def is_token_exception(self, atr):
        return False

    def is_tagged(self, atr):
        return atr.is_tagged()

    def _cleanup(self, word):
        return word if self.is_case_sensitive() else self.lower(word)

    def match(self, sentence):
        out = []
        for atr in sentence.non_blank_tokens:
            if atr.readings[0].pos_tag == SENTENCE_START_TAGNAME or atr.immunized or atr.ignored_by_speller or \
                    self.is_token_exception(atr) or (self.ignore_tagged_words and self.is_tagged(atr)):
                continue
            out.extend(self.find_matches(atr, sentence))
        return out

    def find_matches(self, atr, sentence):
        out = []
        original = atr.token
        token_string = self._cleanup(original)
        all_upper = is_all_uppercase(original)
        wrong_words = self.get_wrong_words()
        possible = wrong_words.get(original)
        if possible is None:
            possible = wrong_words.get(token_string)
        if possible is None and self.check_lemmas:
            possible = []
            lemmas = []
            for at in atr.readings:
                lemma = at.lemma
                if lemma is not None and lemma in wrong_words and lemma not in lemmas:
                    lemmas.append(self._cleanup(lemma))
            for lemma in lemmas:
                replacements = wrong_words.get(lemma)
                if replacements is not None:
                    synth = self.get_synthesizer()
                    if synth is not None:
                        for repl_lemma in replacements:
                            for at in atr.readings:
                                new_at = AnalyzedToken(at.lemma, at.pos_tag, repl_lemma)
                                possible.extend(synth.synthesize(new_at, at.pos_tag))
                    else:
                        possible.extend(replacements)
            possible = list(dict.fromkeys(possible))
        if possible:
            if all_upper:
                replacements = [s.upper() for s in possible]
            else:
                replacements = list(possible)
            if original in replacements:
                replacements.remove(original)
            if replacements:
                out.append(self.create_rule_match(atr, replacements, sentence, original))
        return out

    def create_rule_match(self, atr, replacements, sentence, original):
        token_string = atr.token
        pos = atr.start_pos
        rule = self
        if self.sub_rule_specific_ids:
            rule = _specific_id_rule(self, to_id(self.get_id() + '_' + original, self.language),
                                     self.get_description().replace('$match', original))
        rm = RuleMatch(rule, sentence, pos, pos + len(token_string), self.get_message(token_string, replacements),
                       self.get_short())
        if not self.is_case_sensitive() and starts_with_uppercase(token_string):
            replacements = [uppercase_first_char(r) for r in replacements]
        rm.set_suggested_replacements(replacements)
        return rm


# case sensitivity of AbstractSimpleReplaceRule2
CS = 'CS'
CI = 'CI'
CS_EXCEPT_AT_SENTENCE_START = 'CSExceptAtSentenceStart'

_MAX_TOKENS_IN_MULTIWORD = 20
_replace2_cache = {}


class AbstractSimpleReplaceRule2(_RuleBase):
    """Port of AbstractSimpleReplaceRule2: replacement of (multi-)word
    phrases, data files in the format 'wrong1|wrong2=suggestion1|suggestion2
    [TAB message]'. Subclasses implement get_file_names(), get_id(),
    get_description(), get_short() and get_message()."""

    category_id = 'MISC'
    MAX_LENGTH_SHORT_WORDS = 4

    def __init__(self, messages, language):
        if language is None:
            raise ValueError('language must not be None')
        super().__init__(messages, language)
        self.sub_rule_specific_ids = False
        self.ignore_short_uppercase_words = True
        self.rule_has_suggestions = True
        self._maps = None

    def is_checking_case(self):
        return False

    def get_file_names(self):
        raise NotImplementedError()

    def get_file_paths(self):
        """Additional absolute file paths"""
        return None

    def get_short(self):
        raise NotImplementedError()

    def get_message(self):
        raise NotImplementedError()

    def get_suggestions_separator(self):
        return ', '

    def use_sub_rule_specific_ids(self):
        self.sub_rule_specific_ids = True

    def get_case_sensitivity(self):
        return CI

    def is_rule_match_exception(self, rule_match):
        return False

    def is_exception(self, matched_text):
        return False

    def is_token_exception(self, atr):
        return False

    def set_ignore_short_uppercase_words(self, value):
        self.ignore_short_uppercase_words = value

    def set_rule_has_suggestions(self, value):
        self.rule_has_suggestions = value

    def is_punctuation_start(self, word):
        return any(is_digit(c) for c in word) or is_punctuation_mark(word) or is_not_word_character(word)

    def get_wrong_words(self):
        """[multi-word map, single-word map] of wrong form -> (suggestion,
        message)"""
        m = self._lazy_init()
        return [m[2], m[3]]

    def _all_file_paths(self):
        paths = list(self.get_file_paths() or ())
        for name in self.get_file_names():
            paths.append(_rules_file(self.language, name))
        return paths

    def _lazy_init(self):
        m = self._maps
        if m is None:
            paths = tuple(self._all_file_paths())
            key = (type(self), paths, self.is_checking_case(), self.get_case_sensitivity(),
                   self.rule_has_suggestions, self.language.short_code)
            m = _replace2_cache.get(key)
            if m is None:
                m = _replace2_cache[key] = self._fill_maps(paths)
            self._maps = m
        return m

    def _fill_maps(self, paths):
        start_space = {}
        start_no_space = {}
        full_space = {}
        full_no_space = {}
        checking_case = self.is_checking_case()
        ci = self.get_case_sensitivity() == CI
        for path in paths:
            for line in _read_lines(path):
                line = java_trim(line)
                if not line or line[0] == '#':
                    continue
                if '  ' in line and self.language.short_code != 'ar':
                    raise ValueError('More than one consecutive space in %s - use a tab character as a delimiter '
                                     'for the message: %s' % (path, line))
                line = java_trim(_substring_before(line, '#'))
                if checking_case:
                    parts = java_split(line, '=')
                    p0 = parts[0] if parts else ''
                    line = java_trim(p0.lower()) + '=' + java_trim(p0)
                    if len(parts) == 2:
                        line = line + '\t' + java_trim(parts[1])
                parts = java_split(line, '\t')
                conf_pair = parts[0] if parts else ''
                if len(parts) <= 1:
                    msg = None
                elif len(parts) == 2:
                    msg = parts[1]
                else:
                    raise ValueError("Format error in file %s. Expected at most 1 '=' character and at most 1 tab "
                                     "character. Line: %s" % (path, line))
                conf_parts = java_split(conf_pair, '=')
                suggestion = ''
                if self.rule_has_suggestions:
                    if len(conf_parts) < 2:
                        raise ValueError("Format error in file %s. Missing suggestion after character '='. Line: %s"
                                         % (path, line))
                    suggestion = conf_parts[1]
                for wrong in java_split(conf_parts[0] if conf_parts else '', '|'):
                    key = wrong.lower() if ci else wrong
                    if not checking_case and key == suggestion:
                        raise ValueError("Format error in file %s. Found same word on left and right side of '='. "
                                         "Line: %s" % (path, line))
                    swm = (suggestion, msg)
                    if wrong.find(' ') <= 0:
                        c = key[0]
                        if start_no_space.get(c, -1) < len(key):
                            start_no_space[c] = len(key)
                        full_no_space[key] = swm
                    else:
                        toks = java_split(key, ' ')
                        first = toks[0]
                        if start_space.get(first, -1) < len(toks):
                            start_space[first] = len(toks)
                        full_space[key] = swm
        return start_space, start_no_space, full_space, full_no_space

    def match(self, sentence):
        start_space, start_no_space, full_space, full_no_space = self._lazy_init()
        out = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        sent_start = 1
        while sent_start < n and self.is_punctuation_start(tokens[sent_start].token):
            sent_start += 1
        covered = [0]
        cs = self.get_case_sensitivity()
        ci = cs == CI
        cs_except_start = cs == CS_EXCEPT_AT_SENTENCE_START
        for start in range(sent_start, n):
            if self.is_token_exception(tokens[start]):
                continue
            tok = tokens[start].token
            if len(tok) < 1:
                continue
            k = start + 1
            while k < n and not tokens[k].whitespace_before:
                tok = tok + tokens[k].token
                k += 1
            if ci:
                tok = tok.lower()
            max_len = start_space.get(tok)
            if max_len is not None:
                key = []
                spaces = 0
                end = start
                while end < n and end - start < _MAX_TOKENS_IN_MULTIWORD:
                    if end > start and tokens[end].whitespace_before:
                        key.append(' ')
                        spaces += 1
                    key.append(tokens[end].token)
                    if spaces + 1 > max_len:
                        break
                    if spaces > 0:
                        original = ''.join(key)
                        key_str = original.lower() if ci else original
                        swm = full_space.get(key_str)
                        self._create_match(out, swm, start, end, original, tokens, sentence, sent_start, covered)
                        if swm is None and sent_start == start and cs_except_start and \
                                key_str != lowercase_first_char(key_str):
                            key_str = lowercase_first_char(key_str)
                            swm = full_space.get(key_str)
                            self._create_match(out, swm, start, end, original, tokens, sentence, sent_start,
                                               covered)
                    end += 1
            if start_no_space and tok[0] in start_no_space:
                end = start
                key = []
                while end < n and end - start < _MAX_TOKENS_IN_MULTIWORD:
                    if end > start and tokens[end].whitespace_before:
                        break
                    key.append(tokens[end].token)
                    original = ''.join(key)
                    key_str = original.lower() if ci else original
                    swm = full_no_space.get(key_str)
                    self._create_match(out, swm, start, end, original, tokens, sentence, sent_start, covered)
                    if swm is None and sent_start == start and cs_except_start and \
                            key_str != lowercase_first_char(key_str):
                        key_str = lowercase_first_char(key_str)
                        swm = full_no_space.get(key_str)
                        self._create_match(out, swm, start, end, original, tokens, sentence, sent_start, covered)
                    end += 1
        return out

    def _create_match(self, out, swm, start, end, original, tokens, sentence, sent_start, covered):
        if swm is None or self.is_exception(original):
            return
        suggestion, msg = swm
        replacements = java_split(suggestion, '|')
        from_pos = tokens[start].start_pos
        to_pos = tokens[end].end_pos
        if out:
            last = out[-1]
            if last.from_pos <= from_pos and last.to_pos >= to_pos:
                return
        camel = any(is_camel_case(_first_part(r)) for r in replacements)
        all_upper = is_all_uppercase(original)
        capitalized = is_capitalized_word(_first_part(original))
        checking_case = self.is_checking_case()
        if checking_case:
            if end <= covered[0]:
                return
            repl_cc = replacements[0]
            if (sent_start == start and original == uppercase_first_char(repl_cc)) or original == repl_cc:
                if out and out[-1].to_pos > from_pos:
                    out.pop()
                covered[0] = end
                return
            if not camel and original == original.upper():
                if self.ignore_short_uppercase_words or len(original) > self.MAX_LENGTH_SHORT_WORDS:
                    covered[0] = end
                    return
        final = []
        for repl in replacements:
            final_repl = repl
            if not camel and (sent_start == start or (capitalized and not checking_case)):
                final_repl = uppercase_first_char(repl)
            if not checking_case and all_upper:
                final_repl = repl.upper()
            if repl != original and final_repl != original and final_repl not in final:
                final.append(final_repl)
            if final_repl == original:
                final.clear()
                break
        if self.rule_has_suggestions and not final:
            return
        if msg is not None and (msg.startswith('http://') or msg.startswith('https://')):
            msg = None  # the URL is lost, as in Java
        if msg is None:
            ms = []
            for k, r in enumerate(replacements):
                if k > 0:
                    ms.append(self.get_suggestions_separator() if k == len(replacements) - 1 else ', ')
                ms.append('<suggestion>' + r + '</suggestion>')
            msg = _replace_first('$match', original, self.get_message())
            msg = _replace_first('$suggestions', ''.join(ms), msg)
        rule = self
        if self.sub_rule_specific_ids:
            rule = _specific_id_rule(self, to_id(self.get_id() + '_' + original, self.language),
                                     self.get_description().replace('$match', original))
        rm = RuleMatch(rule, sentence, from_pos, to_pos, msg, self.get_short())
        if self.rule_has_suggestions:
            rm.set_suggested_replacements(final)
        if self.is_rule_match_exception(rm):
            return
        if out:
            last = out[-1]
            if last.from_pos >= from_pos and last.to_pos <= to_pos:
                out.pop()
        out.append(rm)


class AbstractCheckCaseRule(AbstractSimpleReplaceRule2):
    """Port of AbstractCheckCaseRule"""

    category_id = 'CASING'
    issue_type = 'Typographical'

    def is_checking_case(self):
        return True


# --- compounds -------------------------------------------------------------

MAX_TERMS = 5
_compound_cache = {}


class CompoundRuleData:
    """Port of CompoundRuleData, paths are absolute file paths. expander is
    an optional function line -> list of lines (LineExpander)."""

    def __init__(self, *paths, expander=None):
        self.incorrect_compounds = set()
        self.joined_suggestion = set()
        self.joined_lower_case_suggestion = set()
        self.dash_suggestion = set()
        self.first_words = set()
        self.has_digit_patterns = False
        self.expander = expander
        for p in paths:
            self._load(p)

    def _load(self, path):
        for line in _read_lines(path):
            if not line or line.startswith('#'):
                continue
            line = java_trim(_substring_before(line, '#'))
            lines = self.expander(line) if self.expander is not None else [line]
            for exp in lines:
                exp = exp.replace('-', ' ')
                self._validate(path, exp)
                if exp.endswith('+'):
                    exp = exp[:-1]
                    self.joined_suggestion.add(exp)
                elif exp.endswith('*'):
                    exp = exp[:-1]
                    self.dash_suggestion.add(exp)
                elif exp.endswith('?'):
                    exp = exp[:-1]
                    self.joined_suggestion.add(exp)
                    self.joined_lower_case_suggestion.add(exp)
                elif exp.endswith('$'):
                    exp = exp[:-1]
                    self.joined_suggestion.add(exp)
                    self.dash_suggestion.add(exp)
                    self.joined_lower_case_suggestion.add(exp)
                else:
                    self.joined_suggestion.add(exp)
                    self.dash_suggestion.add(exp)
                self.incorrect_compounds.add(exp)
                sp = exp.find(' ')
                if sp > 0:
                    first = exp[:sp].lower()
                    if '\\d' not in first:
                        self.first_words.add(first)
                if '\\d' in exp:
                    self.has_digit_patterns = True

    def _validate(self, path, line):
        parts = java_split(line, ' ')
        if len(parts) == 1:
            raise ValueError('Not a compound in file %s: %s' % (path, line))
        if len(parts) > MAX_TERMS:
            raise ValueError('Too many compound parts in file %s: %s, maximum allowed: %d' % (path, line, MAX_TERMS))
        if line.lower() in self.incorrect_compounds:
            raise ValueError('Duplicated word in file %s: %s' % (path, line))


def load_compound_rule_data(language, *paths, expander=None):
    """Cached CompoundRuleData for resource paths like '/de/compounds.txt'"""
    files = tuple(_resource_file(language, p) for p in paths)
    key = (files, expander)
    d = _compound_cache.get(key)
    if d is None:
        d = _compound_cache[key] = CompoundRuleData(*files, expander=expander)
    return d


_DIGIT = regex.compile('[0-9]+')
_JAVA_WHITESPACE = regex.compile('[ \t\n\x0b\f\r]+')
_DASHES = regex.compile('--+')


def _normalize_compound(s):
    s = java_trim(s)
    s = s.replace(' - ', ' ')
    s = s.replace('-', ' ')
    return _JAVA_WHITESPACE.sub(' ', s)


class AbstractCompoundRule(_RuleBase):
    """Port of AbstractCompoundRule: checks that compounds (if in the list)
    are not written as separate words. Subclasses implement get_id(),
    get_description() and get_compound_rule_data()."""

    category_id = 'MISC'
    issue_type = 'Misspelling'

    def __init__(self, messages, language, user_config, with_hyphen_message, without_hyphen_message,
                 with_or_without_hyphen_message, short_message=None):
        super().__init__(messages, language)
        self.with_hyphen_message = with_hyphen_message
        self.without_hyphen_message = without_hyphen_message
        self.with_or_without_hyphen_message = with_or_without_hyphen_message
        self.short_desc = short_message
        self.lang = language
        self.sentence_starts_with_upper_case = True
        self.sub_rule_specific_ids = False

    def estimate_context_for_sure_match(self):
        return 1

    def use_sub_rule_specific_ids(self):
        self.sub_rule_specific_ids = True

    def get_compound_rule_data(self):
        raise NotImplementedError()

    def is_misspelled(self, word):
        return False

    def is_correct_spell(self, word):
        return not self.is_misspelled(word)

    def match(self, sentence):
        data = self.get_compound_rule_data()
        has_digits = data.has_digit_patterns
        first_words = None if has_digits else data.first_words
        if first_words is not None and not self._sentence_may_contain_compound(sentence, first_words):
            return []
        out = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        prev_rm = None
        prev_tokens = []
        n = len(tokens)
        incorrect = data.incorrect_compounds
        dash_sugg = data.dash_suggestion
        for i in range(n + MAX_TERMS):
            if i >= n:
                token = AnalyzedTokenReadings(AnalyzedToken('', '', None), prev_tokens[0].start_pos)
            else:
                token = tokens[i]
            if i == 0:
                self._add_to_queue(token, prev_tokens)
                continue
            elif token.immunized:
                continue
            first_match_token = prev_tokens[0]
            if first_words is not None and not self._could_start_compound(prev_tokens, first_words):
                self._add_to_queue(token, prev_tokens)
                continue
            strings, orig_strings, string_to_token = self._string_to_token_map(prev_tokens)
            for k in range(len(strings) - 1, -1, -1):
                s = strings[k]
                orig = orig_strings[k]
                digits_regexp = None
                contains_digits = has_digits and any(is_numeric(x) for x in java_split(s, ' '))
                # as in Java, digits_regexp is only computed if s is not in the set
                if s not in incorrect and contains_digits:
                    digits_regexp = _DIGIT.sub(r'\\d+', s)
                if s in incorrect or (digits_regexp is not None and digits_regexp in incorrect):
                    atr = string_to_token[s]
                    msg = None
                    replacement = []
                    if s in dash_sugg and ' ' not in orig:
                        break
                    if s in dash_sugg or (digits_regexp is not None and digits_regexp in incorrect):
                        replacement.append(orig.replace(' ', '-'))
                        msg = self.with_hyphen_message
                    if self._is_not_all_uppercase(orig) and s in data.joined_suggestion:
                        lc = any(x in s for x in data.joined_lower_case_suggestion)
                        replacement.append(self.merge_compound(orig, lc))
                        msg = self.without_hyphen_message
                    parts = java_split(s, ' ')
                    if parts and len(parts[0]) == 1:
                        replacement = [orig.replace(' ', '-')]
                        msg = self.with_hyphen_message
                    elif not replacement or len(replacement) == 2:
                        msg = self.with_or_without_hyphen_message
                    replacement = self.filter_replacements(
                        replacement, sentence.text[first_match_token.start_pos:atr.end_pos])
                    if not replacement:
                        break
                    start_pos = first_match_token.start_pos
                    end_pos = atr.end_pos
                    rule = self
                    if self.sub_rule_specific_ids:
                        rule = _specific_id_rule(self, to_id(self.get_id() + '_' + s, self.lang),
                                                 self.get_description().replace('$match', orig))
                    rm = RuleMatch(rule, sentence, start_pos, end_pos, msg, self.short_desc)
                    rm.set_suggested_replacements(replacement)
                    if prev_rm is not None and prev_rm.from_pos == rm.from_pos:
                        prev_rm = rm
                        break
                    prev_rm = rm
                    out.append(rm)
                    break
            self._add_to_queue(token, prev_tokens)
        return out

    def filter_replacements(self, replacements, original):
        out = []
        for r in replacements:
            nr = _DASHES.sub('-', r)
            if nr != original and self.is_correct_spell(nr):
                out.append(nr)
        return out

    def _string_to_token_map(self, prev_tokens):
        strings = []
        orig_strings = []
        string_to_token = {}
        sb = []
        first_sent_start = False
        for j, atr in enumerate(prev_tokens):
            if atr.whitespace_before:
                sb.append(' ')
            sb.append(atr.token)
            if j == 0:
                first_sent_start = atr.has_pos_tag(SENTENCE_START_TAGNAME)
            if j >= 1 or not first_sent_start:
                joined = ''.join(sb)
                s = _normalize_compound(joined)
                if self.sentence_starts_with_upper_case and first_sent_start:
                    s = lowercase_first_char(s)
                strings.append(s)
                orig_strings.append(java_trim(joined))
                if s not in string_to_token:
                    string_to_token[s] = atr
        return strings, orig_strings, string_to_token

    @staticmethod
    def _could_start_compound(prev_tokens, first_words):
        for atr in prev_tokens:
            token = atr.token
            if not token:
                continue
            normalized = token if ('-' not in token and ' ' not in token) else _normalize_compound(token)
            if not normalized or ' ' in normalized:
                return True
            return normalized.lower() in first_words
        return True

    @staticmethod
    def _sentence_may_contain_compound(sentence, first_words):
        for token in sentence.token_set:
            if not token:
                continue
            normalized = token if '-' not in token else _normalize_compound(token)
            sp = normalized.find(' ')
            if sp > 0:
                normalized = normalized[:sp]
            if normalized and normalized.lower() in first_words:
                return True
        return False

    @staticmethod
    def _is_not_all_uppercase(s):
        for part in java_split(s, ' '):
            if part != '-' and is_all_uppercase(part):
                return False
        return True

    def merge_compound(self, s, uncapitalize_mid_words):
        parts = java_split(s.replace('-', ' '), ' ')
        out = []
        for k, p in enumerate(parts):
            if k == 0:
                out.append(p)
            else:
                out.append(lowercase_first_char(p) if uncapitalize_mid_words else p)
        return ''.join(out)

    @staticmethod
    def _add_to_queue(token, prev_tokens):
        if len(prev_tokens) == MAX_TERMS:
            del prev_tokens[0]
        prev_tokens.append(token)


# --- word coherency --------------------------------------------------------

_coherency_cache = {}


def load_word_coherency_data(path):
    """Port of WordCoherencyDataLoader.loadWords, path is an absolute file
    path. Returns a dict word -> set of words that should not appear in the
    same text."""
    m = _coherency_cache.get(path)
    if m is not None:
        return m
    m = {}
    for line in _read_lines(path):
        if not line or line[0] == '#':
            continue
        parts = java_split(line, ';')
        if len(parts) != 2:
            raise ValueError('Could not load coherency data from %s: format error, line: %s' % (path, line))
        m.setdefault(parts[0], set()).add(parts[1])
        m.setdefault(parts[1], set()).add(parts[0])
    _coherency_cache[path] = m
    return m


class AbstractWordCoherencyRule(_TextLevelRuleBase):
    """Port of AbstractWordCoherencyRule: a text should consistently use one
    of two variant spellings. Subclasses implement get_word_map() (e.g. with
    load_word_map()), get_message(), get_id() and get_description()."""

    category_id = 'MISC'

    def load_word_map(self, path):
        return load_word_coherency_data(_rules_file(self.language, path))

    def get_word_map(self):
        raise NotImplementedError()

    def get_message(self, word1, word2):
        raise NotImplementedError()

    def get_short_message(self):
        return None

    def min_to_check_paragraph(self):
        return -1

    def match(self, sentences, annotated_text=None):
        out = []
        should_not_appear = {}
        word_map = self.get_word_map()
        pos = 0
        for sentence in sentences:
            for atr in sentence.non_blank_tokens:
                token = atr.token
                readings = atr.readings
                if readings:
                    for baseform in java_hash_set_order([r.lemma for r in readings]):
                        if baseform is not None:
                            token = baseform
                        from_pos = pos + atr.start_pos
                        to_pos = pos + atr.end_pos
                        other = should_not_appear.get(token)
                        if other is not None:
                            msg = self.get_message(token, other)
                            rm = RuleMatch(self, sentence, from_pos, to_pos, msg)
                            marked = sentence.text[atr.start_pos:atr.end_pos]
                            replacement = self.create_replacement(marked, token, other, atr)
                            if starts_with_uppercase(atr.token):
                                replacement = uppercase_first_char(replacement)
                            if not java_equals_ignore_case(marked, replacement):
                                rm.set_suggested_replacement(replacement)
                                out.append(rm)
                            rm.short_message = self.get_short_message()
                            break
                        elif token in word_map:
                            for w in word_map[token]:
                                should_not_appear[w] = token
            pos += sentence.get_corrected_text_length()
        return out

    def create_replacement(self, marked, token, other_spelling, atr):
        return jregex.java_replace(jregex.compile('(?i)' + token), other_spelling, marked, 1)


# --- repetitions -----------------------------------------------------------

_SENTENCE_END_PATTERN = jregex.compile('.+[.?!]$')


class WordRepeatBeginningRule(_TextLevelRuleBase):
    """Port of WordRepeatBeginningRule: successive sentences beginning with
    the same word."""

    rule_id = 'WORD_REPEAT_BEGINNING_RULE'
    category_id = 'REPETITIONS_STYLE'
    issue_type = 'Style'
    description_key = 'desc_repetition_beginning'
    _EXCEPTIONS = frozenset((':', '–', '-', '✔️', '➡️', '—', '⭐️', '⚠️'))

    def is_adverb(self, atr):
        return False

    def is_exception(self, token):
        return token in self._EXCEPTIONS

    def is_sentence_exception(self, sentence):
        return False

    def get_suggestions(self, atr):
        return []

    def min_to_check_paragraph(self):
        return 2

    def match(self, sentences, annotated_text=None):
        last_token = ''
        before_last_token = ''
        out = []
        pos = 0
        prev_sentence = None
        msgs = self.messages
        for sentence in sentences:
            if self.is_sentence_exception(sentence):
                prev_sentence = None
                continue
            tokens = sentence.non_blank_tokens
            token = ''
            if len(tokens) > 1:
                atr = tokens[1]
                token = atr.token
                if len(tokens) > 3:
                    is_word = not (len(token) == 1 and not is_letter(token))
                    if is_word and last_token == token and not self.is_exception(token) and \
                            not self.is_exception(tokens[2].token) and not self.is_exception(tokens[3].token) and \
                            prev_sentence is not None and \
                            _SENTENCE_END_PATTERN.fullmatch(java_trim(prev_sentence.text)) is not None:
                        if self.is_adverb(atr):
                            short_msg = msgs['desc_repetition_beginning_adv']
                        elif before_last_token == token:
                            short_msg = msgs['desc_repetition_beginning_word']
                        else:
                            short_msg = ''
                        if short_msg:
                            msg = short_msg + ' ' + msgs['desc_repetition_beginning_thesaurus']
                            start = atr.start_pos
                            rm = RuleMatch(self, sentence, pos + start, pos + start + len(token), msg, short_msg)
                            sugg = self.get_suggestions(atr)
                            if sugg:
                                rm.set_suggested_replacements(sugg)
                            out.append(rm)
            before_last_token = last_token
            last_token = token
            pos += sentence.get_corrected_text_length()
            prev_sentence = sentence
        return out


def _phrase_is_word(token):
    if is_emoji(token):
        return False
    if is_numeric_space(token):
        return False
    if len(token) == 1 and not is_letter(token):
        return False
    return True


class PhraseRepeatRule(_RuleBase):
    """Port of PhraseRepeatRule: repeated phrases of 2-3 tokens."""

    rule_id = 'PHRASE_REPEAT_RULE'
    category_id = 'MISC'
    issue_type = 'Duplication'
    description_key = 'desc_repetition'
    MAX_PHRASE_LENGTH = 3
    MIN_PHRASE_LENGTH = 2

    def ignore(self, tokens, position, phrase_length):
        return False

    def estimate_context_for_sure_match(self):
        return 1

    def match(self, sentence):
        out = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        n = len(tokens)
        i = 1
        while i < n:
            matched = 0
            for length in range(self.MAX_PHRASE_LENGTH, self.MIN_PHRASE_LENGTH - 1, -1):
                if i + 2 * length <= n and self.phrase_repeated_at(tokens, i, length) and \
                        not self.ignore(tokens, i, length):
                    matched = length
                    break
            if matched > 0:
                first_start = tokens[i].start_pos
                second_end = tokens[i + 2 * matched - 1].end_pos
                phrase = self._phrase_to_string(tokens, i, matched)
                out.append(self.create_rule_match(phrase, first_start, second_end, self.messages['desc_repetition'],
                                                  sentence))
                i += 2 * matched
            else:
                i += 1
        return out

    def create_rule_match(self, phrase, from_pos, to_pos, msg, sentence):
        rm = RuleMatch(self, sentence, from_pos, to_pos, msg, self.messages['desc_repetition_short'])
        rm.set_suggested_replacement(phrase)
        return rm

    def phrase_repeated_at(self, tokens, position, length):
        saw_word = False
        for j in range(length):
            first = tokens[position + j]
            second = tokens[position + length + j]
            if first.immunized or second.immunized:
                return False
            if not java_equals_ignore_case(first.token, second.token):
                return False
            if _phrase_is_word(first.token):
                saw_word = True
        return saw_word

    @staticmethod
    def _phrase_to_string(tokens, position, length):
        out = []
        for j in range(length):
            if j > 0 and tokens[position + j].whitespace_before:
                out.append(' ')
            out.append(tokens[position + j].token)
        return ''.join(out)


class AdvancedWordRepeatRule(_RuleBase):
    """Port of AdvancedWordRepeatRule: repetition of a lemma in a sentence.
    Subclasses implement get_excluded_words_pattern() (a set of lemmas),
    get_excluded_non_words_pattern() and get_excluded_pos() (compiled
    regexes, use jregex.compile), get_message() and get_short_message()."""

    category_id = 'MISC'
    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def get_excluded_words_pattern(self):
        raise NotImplementedError()

    def get_excluded_non_words_pattern(self):
        raise NotImplementedError()

    def get_excluded_pos(self):
        raise NotImplementedError()

    def get_message(self):
        raise NotImplementedError()

    def get_short_message(self):
        raise NotImplementedError()

    def match(self, sentence):
        out = []
        tokens = sentence.non_blank_tokens
        repetition = False
        inflected = set()
        cur_token = 0
        excluded_words = self.get_excluded_words_pattern()
        excluded_pos = self.get_excluded_pos()
        excluded_non_words = self.get_excluded_non_words_pattern()
        for i in range(1, len(tokens)):
            token = tokens[i].token
            is_word = len(token) >= 2
            has_lemma = True
            for at in tokens[i].readings:
                pos_tag = at.pos_tag
                if pos_tag is not None:
                    if not pos_tag:
                        is_word = False
                        break
                    lemma = at.lemma
                    if lemma is None:
                        has_lemma = False
                        break
                    if lemma in excluded_words:
                        is_word = False
                        break
                    if excluded_pos.fullmatch(pos_tag) is not None:
                        is_word = False
                        break
                else:
                    has_lemma = False
            if is_word and excluded_non_words.fullmatch(token) is not None:
                is_word = False
            prev_lemma = ''
            if is_word:
                not_sent_end = False
                for at in tokens[i].readings:
                    if at.pos_tag is not None:
                        not_sent_end |= at.pos_tag == SENTENCE_END_TAGNAME
                    if has_lemma:
                        cur_lemma = at.lemma
                        if prev_lemma != cur_lemma and not not_sent_end:
                            if cur_lemma in inflected and cur_token != i:
                                repetition = True
                            else:
                                inflected.add(cur_lemma)
                                cur_token = i
                        prev_lemma = cur_lemma
                    else:
                        if token in inflected and not not_sent_end:
                            repetition = True
                        else:
                            inflected.add(token)
            if repetition:
                p = tokens[i].start_pos
                out.append(RuleMatch(self, sentence, p, p + len(token), self.get_message(), self.get_short_message()))
                repetition = False
        return out


_repeated_words_cache = {}


class SynonymsData:
    __slots__ = ('synonyms', 'postag', 'chunk')

    def __init__(self, synonyms, postag, chunk):
        self.synonyms = synonyms
        self.postag = postag
        self.chunk = chunk


def load_repeated_words(path):
    """Port of AbstractRepeatedWordsRule.loadWords, path is an absolute file
    path."""
    m = _repeated_words_cache.get(path)
    if m is not None:
        return m
    m = {}
    for raw in _read_lines(path):
        line = java_trim(_substring_before(raw, '#'))
        if not line:
            continue
        main = java_split(line, '=')
        postag = chunk = None
        if len(main) == 2:
            parts = java_split(main[1], ';')
            wpc = java_split(main[0], '/')
            word = wpc[0] if wpc else ''
            if len(wpc) > 1:
                postag = wpc[1]
            if len(wpc) > 2:
                chunk = wpc[2]
        elif len(main) == 1:
            parts = java_split(line, ';')
            word = ''
        else:
            raise ValueError('Format error in file %s, line: %s' % (path, line))
        if (not word and len(parts) < 2) or (word and len(parts) < 1):
            raise ValueError('Format error in file %s, line: %s' % (path, line))
        if word:
            if word in m:
                raise ValueError('Word found in more than one line. "%s" in line: %s' % (word, line))
            m[word] = SynonymsData(list(parts), postag, chunk)
        else:
            for key in parts:
                if key in m:
                    raise ValueError('Word found in more than one line. "%s" in line: %s' % (key, line))
                m[key] = SynonymsData([v for v in parts if v != key], postag, chunk)
    _repeated_words_cache[path] = m
    return m


_PUNCT = jregex.compile(r'\p{P}')


class AbstractRepeatedWordsRule(_TextLevelRuleBase):
    """Port of AbstractRepeatedWordsRule: a word (from a list) repeated
    within a short distance, with synonyms as suggestions. Subclasses
    implement get_words_to_check() (e.g. with load_words()),
    get_synthesizer(), get_message(), get_short_message(),
    get_description() and is_exception()."""

    category_id = 'REPETITIONS_STYLE'
    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.rule_id = language.short_code.upper() + '_REPEATEDWORDS'

    def load_words(self, path):
        return load_repeated_words(_rules_file(self.language, path))

    def get_words_to_check(self):
        raise NotImplementedError()

    def get_synthesizer(self):
        raise NotImplementedError()

    def get_message(self):
        raise NotImplementedError()

    def get_short_message(self):
        raise NotImplementedError()

    def is_exception(self, tokens, i, sent_start, is_capitalized, is_all_upper):
        raise NotImplementedError()

    def min_to_check_paragraph(self):
        return 1

    def max_words_distance(self):
        return 150

    def adjust_postag(self, postag):
        return postag

    def match(self, sentences, annotated_text=None):
        out = []
        word_number = 0
        last_seen = {}
        pos = 0
        prev_len = 0
        words = self.get_words_to_check()
        for sentence in sentences:
            tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
            pos += prev_len
            prev_len = len(sentence.text)
            if tokens[-1].token not in ('.', '!', '?'):
                continue
            sent_start = True
            lemmas_in_sentence = []
            i = -1
            for atrs in tokens:
                if atrs.immunized:
                    continue
                token = atrs.token
                if token:
                    word_number += 1
                is_cap = is_capitalized_word(token)
                is_upper = is_all_uppercase(token)
                i += 1
                exc = not token or self.is_exception(tokens, i, sent_start, is_cap, is_upper)
                if sent_start and token and _PUNCT.fullmatch(token) is None:
                    sent_start = False
                if exc:
                    continue
                lemmas = []
                for atr in atrs.readings:
                    lemma = atr.lemma
                    lemmas.append(lemma)
                    seen = last_seen.get(lemma)
                    if seen is not None and lemma not in lemmas_in_sentence and \
                            word_number - seen <= self.max_words_distance():
                        create = True
                        data = words[lemma]
                        if data.postag is not None and (atr.pos_tag is None or
                                                        jregex.compile(data.postag).fullmatch(atr.pos_tag) is None):
                            create = False
                        if data.chunk is not None and not atrs.matches_chunk_regex(data.chunk):
                            create = False
                        if create:
                            rm = RuleMatch(self, sentence, pos + atrs.start_pos, pos + atrs.end_pos,
                                           self.get_message(), self.get_short_message())
                            rm.specific_rule_id = self.rule_id + '_' + to_id(lemma, self.language)
                            synth = self.get_synthesizer()
                            for repl_lemma in data.synonyms:
                                repls = []
                                if synth is not None:
                                    repls = synth.synthesize(AnalyzedToken(token, atr.pos_tag, repl_lemma),
                                                             self.adjust_postag(atr.pos_tag), True)
                                if not repls:
                                    repls = [repl_lemma]
                                for r in repls:
                                    if is_upper:
                                        r = r.upper()
                                    elif is_cap:
                                        r = uppercase_first_char(r)
                                    rm.add_suggested_replacement(r)
                            out.append(rm)
                            break
                for lemma in lemmas:
                    if lemma in words:
                        last_seen[lemma] = word_number
                        lemmas_in_sentence.append(lemma)
        return out


# --- style statistics ------------------------------------------------------

_OPENING_QUOTES = regex.compile('["“„»«]')
_ENDING_QUOTES = regex.compile('["“”»«]')
_SINGLE_QUOTES = regex.compile('[\'‚‘’\'›‹]')
_MARKS_REGEX = jregex.compile('[,;.:?•!-–—]')


def _creative_writing_category(messages):
    return Category('CREATIVE_WRITING', messages.get('category_creative_writing', 'Creative Writing'), 'INTERNAL',
                    False)


def _quote(pattern, s):
    return pattern.fullmatch(s) is not None


class AbstractStyleTooOftenUsedWordRule(_TextLevelRuleBase):
    """Port of AbstractStyleTooOftenUsedWordRule"""

    issue_type = 'Style'
    MIN_WORD_COUNT = 100

    def __init__(self, messages, language, user_config, min_percent, default_active=False):
        super().__init__(messages, language)
        self.category = _creative_writing_category(messages)
        if not default_active:
            self.set_default_off()
        self.default_min_percent = min_percent
        cf = _config_values(user_config, self.get_id())
        self.min_percent = int(cf[0]) if cf else min_percent
        self.word_map = {}
        self.without_direct_speech = False

    def is_to_counted_word(self, atr):
        raise NotImplementedError()

    def is_exception(self, tokens, n):
        raise NotImplementedError()

    def to_added_lemma(self, atr):
        raise NotImplementedError()

    def get_limit_message(self, min_percent):
        raise NotImplementedError()

    def get_configure_text(self):
        raise NotImplementedError()

    def set_without_direct_speech(self, value):
        self.without_direct_speech = value

    def min_to_check_paragraph(self):
        return -1

    def _counted_words(self, sentences, sentence_cb):
        exclude = self.without_direct_speech
        direct = False
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            for n in range(1, len(tokens)):
                atr = tokens[n]
                s = atr.token
                if exclude and not direct and _quote(_OPENING_QUOTES, s) and n < len(tokens) - 1 and \
                        not tokens[n + 1].whitespace_before:
                    direct = True
                elif exclude and direct and _quote(_ENDING_QUOTES, s) and n > 1 and not tokens[n].whitespace_before:
                    direct = False
                elif not direct and not atr.is_whitespace and not atr.is_non_word() and \
                        self.is_to_counted_word(atr) and not self.is_exception(tokens, n):
                    lemma = self.to_added_lemma(atr)
                    if lemma is not None:
                        yield sentence, atr, lemma
            if sentence_cb is not None:
                sentence_cb(sentence)

    def _fill_word_map(self, sentences):
        self.word_map.clear()
        for _, _, lemma in self._counted_words(sentences, None):
            self.word_map[lemma] = self.word_map.get(lemma, 0) + 1

    def _too_often_used_words(self):
        num = sum(self.word_map.values())
        if num < self.MIN_WORD_COUNT:
            return []
        return [w for w, c in self.word_map.items() if int((c * 100.) / num) >= self.min_percent]

    def match(self, sentences, annotated_text=None):
        out = []
        self._fill_word_map(sentences)
        too_often = set(self._too_often_used_words())
        if not too_often:
            return out
        pos = [0]

        def next_sentence(sentence):
            pos[0] += sentence.get_corrected_text_length()
        for sentence, atr, lemma in self._counted_words(sentences, next_sentence):
            if lemma in too_often:
                out.append(RuleMatch(self, sentence, atr.start_pos + pos[0], atr.end_pos + pos[0],
                                     self.get_limit_message(self.min_percent)))
        return out

    def get_lemma_for_pos_tag_starts_with(self, start_pos, atr):
        for r in atr.readings:
            if r.pos_tag is not None and r.pos_tag.startswith(start_pos):
                return r.lemma
        return None


class AbstractStatisticStyleRule(_TextLevelRuleBase):
    """Port of AbstractStatisticStyleRule"""

    issue_type = 'Style'

    def __init__(self, messages, language, user_config, min_percent, default_active=False):
        super().__init__(messages, language)
        self.category = _creative_writing_category(messages)
        if not default_active:
            self.set_default_off()
        self.default_min_percent = min_percent
        cf = _config_values(user_config, self.get_id())
        self.min_percent = cf[0] if cf and isinstance(cf[0], int) and not isinstance(cf[0], bool) \
            else min_percent
        if cf and len(cf) > 1 and isinstance(cf[1], bool):
            self._exclude_direct_speech = cf[1]
        else:
            self._exclude_direct_speech = self.exclude_direct_speech()
        self.word_count = 0
        self.num_matches = 0
        self.without_direct_speech = False

    def condition_fulfilled(self, tokens, n):
        raise NotImplementedError()

    def sentence_condition_fulfilled(self, tokens, n):
        raise NotImplementedError()

    def exclude_direct_speech(self):
        raise NotImplementedError()

    def get_limit_message(self, limit, percent):
        raise NotImplementedError()

    def get_sentence_message(self):
        raise NotImplementedError()

    def denominator(self):
        return 100.0

    def set_without_direct_speech(self, value):
        self.without_direct_speech = value

    def min_to_check_paragraph(self):
        return -1

    def match(self, sentences, annotated_text=None):
        out = []
        starts = []
        ends = []
        relevant = []
        pos = 0
        self.word_count = 0
        exclude = self._exclude_direct_speech
        direct = False
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            for n in range(1, len(tokens)):
                atr = tokens[n]
                s = atr.token
                if exclude and not direct and _quote(_OPENING_QUOTES, s) and n < len(tokens) - 1 and \
                        not tokens[n + 1].whitespace_before:
                    direct = True
                elif exclude and direct and _quote(_ENDING_QUOTES, s) and n > 1 and not tokens[n].whitespace_before:
                    direct = False
                elif (not direct or (self.min_percent == 0 and not self.without_direct_speech)) and \
                        not atr.is_whitespace and not atr.is_non_word():
                    self.word_count += 1
                    n_end = self.condition_fulfilled(tokens, n)
                    if n_end >= n:
                        if self.sentence_condition_fulfilled(tokens, n):
                            out.append(RuleMatch(self, sentence, atr.start_pos + pos, atr.end_pos + pos,
                                                 self.get_sentence_message()))
                        else:
                            starts.append(atr.start_pos + pos)
                            ends.append(tokens[n_end].end_pos + pos)
                            relevant.append(sentence)
            pos += sentence.get_corrected_text_length()
        self.num_matches = len(starts) + len(out)
        percent = (self.num_matches * self.denominator()) / self.word_count if self.word_count > 0 else 0
        if percent > self.min_percent:
            for i in range(len(starts)):
                out.append(RuleMatch(self, relevant[i], starts[i], ends[i],
                                     self.get_limit_message(self.min_percent, percent)))
        return out


class AbstractStatisticSentenceStyleRule(_TextLevelRuleBase):
    """Port of AbstractStatisticSentenceStyleRule"""

    issue_type = 'Style'

    def __init__(self, messages, language, user_config, min_percent, default_active=False):
        super().__init__(messages, language)
        self.category = _creative_writing_category(messages)
        if not default_active:
            self.set_default_off()
        self.default_min_percent = min_percent
        cf = _config_values(user_config, self.get_id())
        self.min_percent = int(cf[0]) if cf else min_percent
        self.sentence_count = 0
        self.num_matches = 0
        self.without_direct_speech = False

    def condition_fulfilled(self, tokens):
        """tokens: list of the relevant tokens of the sentence; returns the
        token to mark or None"""
        raise NotImplementedError()

    def exclude_direct_speech(self):
        raise NotImplementedError()

    def get_limit_message(self, limit, percent):
        raise NotImplementedError()

    def is_mark(self, atr):
        return _MARKS_REGEX.fullmatch(atr.token) is not None

    def is_opening_quote(self, atr):
        return _quote(_OPENING_QUOTES, atr.token)

    def denominator(self):
        return 100.0

    def set_without_direct_speech(self, value):
        self.without_direct_speech = value

    def min_to_check_paragraph(self):
        return -1

    def match(self, sentences, annotated_text=None):
        out = []
        starts = []
        ends = []
        relevant = []
        pos = 0
        self.sentence_count = 0
        exclude = self.exclude_direct_speech()
        direct = False
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            part = []
            is_counted = False
            found = None
            for n in range(1, len(tokens)):
                atr = tokens[n]
                s = atr.token
                if exclude and not direct and _quote(_OPENING_QUOTES, s) and n < len(tokens) - 1 and \
                        not tokens[n + 1].whitespace_before:
                    direct = True
                    if part:
                        is_counted = True
                        found = self.condition_fulfilled(part)
                        if found is not None:
                            break
                elif exclude and direct and _quote(_ENDING_QUOTES, s) and n > 1 and not tokens[n].whitespace_before:
                    direct = False
                    part = []
                elif (not direct or (self.min_percent == 0 and not self.without_direct_speech)) and \
                        not atr.is_whitespace:
                    part.append(atr)
                if n == len(tokens) - 1 and part:
                    is_counted = True
                    found = self.condition_fulfilled(part)
            if is_counted:
                self.sentence_count += 1
            if found is not None:
                starts.append(found.start_pos + pos)
                ends.append(found.end_pos + pos)
                relevant.append(sentence)
            pos += sentence.get_corrected_text_length()
        self.num_matches = len(starts)
        percent = (self.num_matches * self.denominator()) / self.sentence_count if self.sentence_count > 0 else 0
        if percent > self.min_percent:
            for i in range(len(starts)):
                out.append(RuleMatch(self, relevant[i], starts[i], ends[i],
                                     self.get_limit_message(self.min_percent, percent)))
        return out


class AbstractFillerWordsRule(AbstractStatisticStyleRule):
    """Port of AbstractFillerWordsRule. Subclasses implement
    is_filler_word(token)."""

    rule_id = 'FILLER_WORDS'
    description_key = 'filler_words_rule_desc'
    DEFAULT_MIN_PERCENT = 8

    def __init__(self, messages, language, user_config=None, default_active=False):
        # as in Java, default_active is not passed on: the rule is off by default
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)

    def is_filler_word(self, token):
        raise NotImplementedError()

    def get_message(self):
        return self.messages['filler_words_rule_msg']

    def is_exception(self, tokens, num):
        return False

    def condition_fulfilled(self, tokens, n):
        if self.is_filler_word(tokens[n].token) and not self.is_exception(tokens, n):
            return n
        return -1

    def sentence_condition_fulfilled(self, tokens, n):
        return False

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        return self.get_message()

    def get_sentence_message(self):
        return None

    def min_to_check_paragraph(self):
        return 0


_VOWELS = frozenset('aeiouyAEIOUY')


class ReadabilityRule(_TextLevelRuleBase):
    """Port of ReadabilityRule (Flesch reading ease)."""

    issue_type = 'Style'
    MARK_WORDS = 3
    MIN_WORDS = 10

    def __init__(self, messages, language, user_config=None, too_easy_test=False, level=-1, default_on=False):
        self.too_easy_test = too_easy_test
        super().__init__(messages, language)
        self.category = Category('TEXT_ANALYSIS', 'Text Analysis', 'INTERNAL', False)
        if not default_on:
            self.set_default_off()
        cf = _config_values(user_config, self.get_id())
        tmp = int(cf[0]) if cf else -1
        if tmp >= 0:
            self.level = tmp
        elif level >= 0:
            self.level = level
        else:
            self.level = 3
        self.n_all_sentences = self.n_all_words = self.n_all_syllables = 0

    def get_id(self, too_easy_test=None):
        if too_easy_test is None:
            too_easy_test = self.too_easy_test
        return 'READABILITY_RULE_SIMPLE' if too_easy_test else 'READABILITY_RULE_DIFFICULT'

    def get_description(self):
        return 'Readability: Too easy text' if self.too_easy_test else 'Readability: Too difficult text'

    def get_configure_text(self):
        return 'Level of readability 0 (very difficult) to 6 (very easy):'

    def print_message_level(self, level):
        names = ('Very difficult', 'Difficult', 'Fairly difficult', 'Medium', 'Fairly easy', 'Easy', 'Very easy')
        if 0 <= level < len(names):
            return ' {Level %d: %s}' % (level, names[level])
        return ''

    def get_message(self, level, fre, asl, asw):
        if self.too_easy_test:
            simple, few = 'simple', 'few'
        else:
            simple, few = 'difficult', 'many'
        return 'Readability: The text of this paragraph is too ' + simple + self.print_message_level(level) + \
            '. Too ' + few + ' words per sentence and too ' + few + ' syllables per word.'

    @staticmethod
    def _readability_level(fre):
        for limit, level in ((30, 0), (50, 1), (60, 2), (70, 3), (80, 4), (90, 5)):
            if fre < limit:
                return level
        return 6

    @staticmethod
    def get_flesch_reading_ease(asl, asw):
        return 206.835 - (1.015 * asl) - (84.6 * asw)

    def simple_syllables_count(self, word):
        if not word:
            return 0
        if len(word) == 1:
            return 1
        n = 0
        last_double = False
        for i in range(len(word) - 1):
            c = word[i]
            if c in _VOWELS:
                cn = word[i + 1]
                if last_double:
                    n += 1
                    last_double = False
                elif (c in 'eE' and cn in 'aoeiy') or (c in 'aA' and cn in 'eiu') or \
                        (c in 'oO' and cn in 'oiua') or (c in 'uU' and cn in 'ia') or (c in 'iI' and cn in 'eo'):
                    last_double = True
                else:
                    n += 1
                    last_double = False
            else:
                last_double = False
        c = word[-1]
        cl = word[-2]
        if (cl == 'e' and c in 'sd') or (cl == 'u' and c == 'e'):
            n -= 1
        elif c in _VOWELS and c != 'e':
            n += 1
        return 1 if n <= 0 else n

    def min_to_check_paragraph(self):
        return -1

    def match(self, sentences, annotated_text=None):
        out = []
        n_paragraph = 0
        self.n_all_sentences = self.n_all_words = self.n_all_syllables = 0
        n_sentences = n_words = n_syllables = 0
        pos = 0
        start_pos = end_pos = -1
        slb = getattr(self.language, 'single_line_breaks_marks_para', False)
        for n, sentence in enumerate(sentences):
            tokens = sentence.non_blank_tokens
            if start_pos < 0 and len(tokens) > 1:
                start_pos = pos + tokens[1].start_pos
            if end_pos < 0 and len(tokens) > self.MARK_WORDS:
                end_pos = pos + tokens[self.MARK_WORDS].end_pos
            n_sentences += 1
            for atr in tokens:
                if not atr.is_whitespace and not atr.is_non_word():
                    n_words += 1
                    n_syllables += self.simple_syllables_count(atr.token)
            if is_paragraph_end(sentences, n, slb):
                if n_words >= self.MIN_WORDS:
                    asl = n_words / n_sentences
                    asw = n_syllables / n_words
                    fre = self.get_flesch_reading_ease(asl, asw)
                    level = self._readability_level(fre)
                    if (self.too_easy_test and level > self.level) or (not self.too_easy_test and level < self.level):
                        out.append(RuleMatch(self, sentence, start_pos, end_pos,
                                             self.get_message(level, int(fre), int(asl), int(asw))))
                self.n_all_sentences += n_sentences
                self.n_all_words += n_words
                self.n_all_syllables += n_syllables
                n_sentences = n_words = n_syllables = 0
                start_pos = end_pos = -1
                n_paragraph += 1
            pos += sentence.get_corrected_text_length()
        asl = _jdiv(self.n_all_words, self.n_all_sentences)
        asw = _jdiv(self.n_all_syllables, self.n_all_words)
        level = self._readability_level(self.get_flesch_reading_ease(asl, asw))
        # operator precedence as in the Java code
        if (n_paragraph > 1 and (self.too_easy_test and level > self.level)) or \
                (not self.too_easy_test and level < self.level):
            return out
        return []


# --- style: repeated words in consecutive sentences ------------------------

class AbstractStyleRepeatedWordRule(_TextLevelRuleBase):
    """Port of AbstractStyleRepeatedWordRule. Subclasses implement
    message_same_sentence(), message_sentence_before(),
    message_sentence_after(), is_token_to_check(tokens, n) and
    is_token_pair(tokens, n, before)."""

    rule_id = 'STYLE_REPEATED_WORD_RULE'
    category_id = 'STYLE'
    issue_type = 'Style'
    MAX_TOKEN_TO_CHECK = 5

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language)
        self.set_default_off()
        self.lang = language
        self.max_distance_of_sentences = 1
        self.exclude_direct_speech = True
        cf = _config_values(user_config, self.get_id())
        if cf:
            if len(cf) > 0 and isinstance(cf[0], int) and not isinstance(cf[0], bool):
                self.max_distance_of_sentences = cf[0]
            if len(cf) > 1 and isinstance(cf[1], bool):
                self.exclude_direct_speech = cf[1]

    def get_description(self):
        return 'Repeated words in consecutive sentences'

    def message_same_sentence(self):
        raise NotImplementedError()

    def message_sentence_before(self):
        raise NotImplementedError()

    def message_sentence_after(self):
        raise NotImplementedError()

    def is_token_to_check(self, tokens, n):
        raise NotImplementedError()

    def is_token_pair(self, tokens, n, before):
        raise NotImplementedError()

    def is_part_of_word(self, test_token_text, token_text):
        return False

    def is_exception_pair(self, token1, token2):
        return False

    def set_url(self, atr):
        return None

    def min_to_check_paragraph(self):
        return -1 if self.exclude_direct_speech else self.max_distance_of_sentences

    def _has_break_token(self, tokens):
        for i in range(min(len(tokens), self.MAX_TOKEN_TO_CHECK)):
            if tokens[i].token in ('-', '—', '–'):
                return True
        return False

    @staticmethod
    def _is_question_response(n_act, n_test, token_list):
        dist = n_act - n_test
        if dist != 1 and dist != -1:
            return False
        act = token_list[n_act]
        test = token_list[n_test]
        if len(act) < 2 or len(test) < 2:
            return False
        act_token = act[-2].token if _quote(_ENDING_QUOTES, act[-1].token) else act[-1].token
        test_token = test[-2].token if _quote(_ENDING_QUOTES, test[-1].token) else test[-1].token
        return (act_token == '?' and test_token != '?') or (test_token == '?' and act_token != '?')

    @staticmethod
    def _is_in_quotes(tokens, i):
        return i > 0 and (_quote(_OPENING_QUOTES, tokens[i - 1].token) or _quote(_SINGLE_QUOTES, tokens[i - 1].token)) \
            and i < len(tokens) - 1 and (_quote(_ENDING_QUOTES, tokens[i + 1].token) or
                                         _quote(_SINGLE_QUOTES, tokens[i + 1].token))

    def _is_token_in_sentence(self, test_token, tokens, not_check, direct):
        if test_token is None or tokens is None:
            return False
        lemmas = [r.lemma for r in test_token.readings if r.lemma is not None]
        exclude = self.exclude_direct_speech
        for i in range(len(tokens)):
            t = tokens[i].token
            if exclude and not direct and _quote(_OPENING_QUOTES, t) and i < len(tokens) - 1 and \
                    not tokens[i + 1].whitespace_before:
                direct = True
            elif exclude and direct and _quote(_ENDING_QUOTES, t) and i > 1 and not tokens[i].whitespace_before:
                direct = False
            elif i != not_check and not direct and not self._is_in_quotes(tokens, i) and \
                    self.is_token_to_check(tokens, i):
                if (lemmas and tokens[i].has_any_lemma(*lemmas) and not self.is_exception_pair(test_token, tokens[i])) \
                        or self.is_part_of_word(test_token.token, t):
                    if not_check >= 0:
                        if not_check == i - 2:
                            return not self.is_token_pair(tokens, i, True)
                        elif not_check == i + 2:
                            return not self.is_token_pair(tokens, i, False)
                        elif (not_check == i + 1 or not_check == i - 1) and test_token.token == t:
                            return False
                    return True
        return False

    def _starts_with_direct_speech(self, n, sentences, direct):
        if not self.exclude_direct_speech or n <= 0:
            return False
        tokens = sentences[n - 1].non_blank_tokens
        for i, atr in enumerate(tokens):
            if not direct and _quote(_OPENING_QUOTES, atr.token) and i < len(tokens) - 1 and \
                    not tokens[i + 1].whitespace_before:
                direct = True
            elif direct and _quote(_ENDING_QUOTES, atr.token) and i > 1 and not tokens[i].whitespace_before:
                direct = False
        return direct

    def match(self, sentences, annotated_text=None):
        out = []
        token_list = []
        ds_list = []
        pos = 0
        starts_ds = False
        maxd = self.max_distance_of_sentences
        nsent = len(sentences)
        for n in range(min(maxd, nsent)):
            token_list.append(sentences[n].non_blank_tokens)
            starts_ds = self._starts_with_direct_speech(n, sentences, starts_ds)
            ds_list.append(starts_ds)
        direct = False
        exclude = self.exclude_direct_speech
        for n in range(nsent):
            if n + maxd < nsent:
                token_list.append(sentences[n + maxd].non_blank_tokens)
                starts_ds = self._starts_with_direct_speech(n + maxd, sentences, starts_ds)
                ds_list.append(starts_ds)
            if len(token_list) > 2 * maxd + 1:
                del token_list[0]
                del ds_list[0]
            n_tok = maxd
            if n < maxd:
                n_tok = n
            elif n >= nsent - maxd:
                n_tok = len(token_list) - (nsent - n)
            tokens = token_list[n_tok]
            if not self._has_break_token(tokens):
                for i in range(len(tokens)):
                    atr = tokens[i]
                    t = atr.token
                    if exclude and not direct and _quote(_OPENING_QUOTES, t) and i < len(tokens) - 1 and \
                            not tokens[i + 1].whitespace_before:
                        direct = True
                    elif exclude and direct and _quote(_ENDING_QUOTES, t) and i > 1 and not tokens[i].whitespace_before:
                        direct = False
                    elif not direct and not self._is_in_quotes(tokens, i) and self.is_token_to_check(tokens, i):
                        repeated = 0
                        if self._is_token_in_sentence(atr, tokens, i, ds_list[n_tok]):
                            repeated = 1
                        j = n_tok - 1
                        while repeated == 0 and j >= 0 and j >= n_tok - maxd:
                            if not self._is_question_response(n_tok, j, token_list) and \
                                    self._is_token_in_sentence(atr, token_list[j], -1, ds_list[j]):
                                repeated = 2
                            j -= 1
                        j = n_tok + 1
                        while repeated == 0 and j < len(token_list) and j <= n_tok + maxd:
                            if not self._is_question_response(n_tok, j, token_list) and \
                                    self._is_token_in_sentence(atr, token_list[j], -1, ds_list[j]):
                                repeated = 3
                            j += 1
                        if repeated:
                            if repeated == 1:
                                msg = self.message_same_sentence()
                            elif repeated == 2:
                                msg = self.message_sentence_before()
                            else:
                                msg = self.message_sentence_after()
                            rm = RuleMatch(self, None, pos + atr.start_pos, pos + atr.end_pos, msg)
                            url = self.set_url(atr)
                            if url is not None:
                                rm.url = url
                            out.append(rm)
            pos += sentences[n].get_corrected_text_length()
        return out


# --- unpaired quotes -------------------------------------------------------

_POSSIBLE_APOSTROPHE = regex.compile("[‘’']")
_INCH = regex.compile('[0-9]"')
_QUOTE_PUNCTUATION = jregex.compile('[\\p{Punct}…–—&&[^"\'_]]')
_PUNCT_MARKS = regex.compile(r'[?.!,]')


class _QuoteLocator:
    __slots__ = ('symbol', 'start_pos', 'sentence')

    def __init__(self, symbol, start_pos, sentence):
        self.symbol = symbol
        self.start_pos = start_pos
        self.sentence = sentence


class GenericUnpairedQuotesRule(_TextLevelRuleBase):
    """Port of GenericUnpairedQuotesRule"""

    category_id = 'PUNCTUATION'
    issue_type = 'Typographical'
    description_key = 'desc_unpaired_quotes'

    def __init__(self, messages, language=None, start_symbols=None, end_symbols=None, rule_id=None):
        super().__init__(messages, language)
        self.rule_id = rule_id if rule_id is not None else 'UNPAIRED_QUOTES'
        if start_symbols is None:
            start_symbols = ['“', '"', '‘', "'"]
            end_symbols = ['”', '"', '’', "'"]
        if len(start_symbols) != len(end_symbols):
            raise ValueError('Different number of start and end symbols: %s vs. %s' % (start_symbols, end_symbols))
        self.start_symbols = list(start_symbols)
        self.end_symbols = list(end_symbols)

    def min_to_check_paragraph(self):
        return -1

    def match(self, sentences, annotated_text=None):
        opening = []
        out = []
        last_apostrophe = None
        was_inch = False
        base = 0
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            for i in range(1, len(tokens)):
                if self._is_opening_quote(tokens, i):
                    symbol = tokens[i].token
                    if not self.is_not_beginning_apostrophe(tokens, i):
                        last_apostrophe = symbol
                        continue
                    if symbol == '"':
                        was_inch = False
                    if last_apostrophe is not None and last_apostrophe == symbol:
                        last_apostrophe = None
                    index = self._index_of_opening_quote(opening, symbol)
                    if index >= 0:
                        self._remove_all_open_inner_quotes(index - 1, opening, out)
                    opening.append(_QuoteLocator(symbol, tokens[i].start_pos + base, sentence))
                elif self._is_closing_quote(tokens, i, opening):
                    symbol = tokens[i].token
                    if not self.is_not_beginning_apostrophe(tokens, i):
                        last_apostrophe = symbol
                        continue
                    is_inch_symb = symbol == '"'
                    is_inch = is_inch_symb and _INCH.search(sentence.text) is not None
                    start_symbol = self.find_corresponding_symbol(symbol)
                    index = self._index_of_opening_quote(opening, start_symbol)
                    if index >= 0:
                        self._remove_all_open_inner_quotes(index, opening, out)
                        del opening[index]
                        if last_apostrophe is not None and last_apostrophe == start_symbol:
                            last_apostrophe = None
                        if is_inch:
                            was_inch = True
                    elif self.is_not_ending_apostrophe(tokens, i):
                        if not is_inch and (not is_inch_symb or not was_inch):
                            if last_apostrophe is None or last_apostrophe != symbol:
                                self._add_match(_QuoteLocator(symbol, tokens[i].start_pos + base, sentence), out)
                            else:
                                last_apostrophe = None
                        else:
                            was_inch = False
            base += sentence.get_corrected_text_length()
        self._remove_all_open_inner_quotes(-1, opening, out)
        return out

    def _is_start_symbol_before(self, tokens, i):
        for j in range(i - 1, 0, -1):
            if tokens[i].token != tokens[j].token and tokens[j].token in self.start_symbols:
                if tokens[j - 1].is_sentence_start or tokens[j].whitespace_before:
                    return True
            else:
                return False
        return True

    def _is_not_open_symbol(self, j, opening):
        if self.end_symbols[j] == self.start_symbols[j]:
            for q in opening:
                if self.end_symbols[j] == q.symbol:
                    return False
        return True

    def _is_not_quote(self, tokens, i, j):
        if (tokens[i - 1].is_sentence_start or tokens[i].whitespace_before) and \
                (i >= len(tokens) - 1 or tokens[i + 1].whitespace_before):
            return True
        if self.end_symbols[j] == self.start_symbols[j]:
            if i < len(tokens) - 1 and not tokens[i].whitespace_before and not tokens[i + 1].whitespace_before and \
                    _QUOTE_PUNCTUATION.fullmatch(tokens[i - 1].token) is not None and \
                    tokens[i + 1].token != '.' and _QUOTE_PUNCTUATION.fullmatch(tokens[i + 1].token) is not None:
                return True
        return False

    def _is_opening_quote(self, tokens, i):
        token = tokens[i].token
        for j, s in enumerate(self.start_symbols):
            if s == token:
                if self._is_not_quote(tokens, i, j):
                    return False
                if s in self.end_symbols:
                    return (tokens[i - 1].is_sentence_start
                            or tokens[i].whitespace_before
                            or (i < len(tokens) - 1 and not tokens[i + 1].whitespace_before
                                and ((_PUNCT_MARKS.fullmatch(tokens[i + 1].token) is None
                                      and _QUOTE_PUNCTUATION.fullmatch(tokens[i - 1].token) is not None)
                                     or tokens[i - 1].token.endswith('-')))
                            or self._is_start_symbol_before(tokens, i))
                return True
        return False

    def _is_closing_quote(self, tokens, i, opening):
        token = tokens[i].token
        for j, s in enumerate(self.end_symbols):
            if s == token:
                if self._is_not_quote(tokens, i, j) and self._is_not_open_symbol(j, opening):
                    return False
                return True
        return False

    def is_not_beginning_apostrophe(self, tokens, i):
        return _POSSIBLE_APOSTROPHE.fullmatch(tokens[i].token) is None or i >= len(tokens) - 1 or \
            tokens[i + 1].is_non_word() or tokens[i + 1].whitespace_before

    def is_not_ending_apostrophe(self, tokens, i):
        return _POSSIBLE_APOSTROPHE.fullmatch(tokens[i].token) is None or tokens[i].whitespace_before or \
            tokens[i - 1].is_non_word()

    @staticmethod
    def _index_of_opening_quote(opening, symbol):
        for i, q in enumerate(opening):
            if q.symbol == symbol:
                return i
        return -1

    def _add_match(self, q, out):
        msg = message_format(self.messages['unpaired_brackets'], self.find_corresponding_symbol(q.symbol))
        out.append(RuleMatch(self, q.sentence, q.start_pos, q.start_pos + len(q.symbol), msg))

    def _remove_all_open_inner_quotes(self, index, opening, out):
        for i in range(len(opening) - 1, index, -1):
            self._add_match(opening[i], out)
            del opening[i]

    def find_corresponding_symbol(self, symbol):
        if symbol in self.start_symbols:
            return self.end_symbols[self.start_symbols.index(symbol)]
        return self.start_symbols[self.end_symbols.index(symbol)]


# --- misc ------------------------------------------------------------------

class AbstractSpaceBeforeRule(_RuleBase):
    """Port of AbstractSpaceBeforeRule. Subclasses implement
    get_conjunctions() returning a compiled regex (jregex.compile)."""

    rule_id = 'SPACE_BEFORE_CONJUNCTION'
    category_id = 'MISC'

    def get_conjunctions(self):
        raise NotImplementedError()

    def get_description(self):
        return 'Checks for missing space before some conjunctions'

    def get_short(self):
        return 'Missing white space'

    def get_suggestion(self):
        return 'Missing white space before conjunction'

    def match(self, sentence):
        out = []
        tokens = sentence.tokens
        conj = self.get_conjunctions()
        for i in range(1, len(tokens)):
            token = tokens[i].token
            if conj.fullmatch(token) is not None:
                prev = tokens[i - 1].token
                if not (prev == ' ' or prev == '('):
                    p = tokens[i].start_pos
                    rm = RuleMatch(self, sentence, p, p + len(token), self.get_suggestion(), self.get_short())
                    rm.set_suggested_replacement(' ' + token)
                    out.append(rm)
        return out


_specific_case_cache = {}
_specific_case_max_len = [0]  # static in Java, shared by all subclasses


def load_word_list(path):
    """Port of CachingWordListLoader.loadWords for an absolute file path."""
    out = []
    if not os.path.exists(path):
        return out
    for line in _read_lines(path):
        if not line or line.startswith('#'):
            continue
        out.append(java_trim(_substring_before(java_trim(line), '#')))
    return out


class AbstractSpecificCaseRule(_RuleBase):
    """Port of AbstractSpecificCaseRule: phrases with a special
    capitalization. Subclasses implement get_phrases_path() (a resource path
    like '/en/specific_case.txt')."""

    rule_id = 'SPECIFIC_CASE'
    category_id = 'CASING'
    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self._load_phrases()

    def get_phrases_path(self):
        raise NotImplementedError()

    def get_description(self):
        return 'Checks upper/lower case expressions.'

    def get_initial_capital_message(self):
        return 'The initials of the particular phrase must be capitals.'

    def get_other_capitalization_message(self):
        return 'The particular expression should follow the suggested capitalization.'

    def get_short_message(self):
        return 'Special capitalization'

    def _load_phrases(self):
        cls = type(self)
        if cls not in _specific_case_cache:
            m = {}
            for line in load_word_list(_resource_file(self.language, self.get_phrases_path())):
                parts = len(java_split(line, ' '))
                _specific_case_max_len[0] = max(parts, _specific_case_max_len[0])
                phrase = java_trim(line)
                m[phrase.lower()] = phrase
            _specific_case_cache[cls] = m

    def match(self, sentence):
        out = []
        tokens = sentence.non_blank_tokens
        proper_map = _specific_case_cache[type(self)]
        max_len = _specific_case_max_len[0]
        n = len(tokens)
        for i in range(n):
            words = []
            j = 0
            while len(words) < max_len and i + j < n:
                words.append(tokens[i + j].token)
                j += 1
                phrase = ' '.join(words)
                proper = proper_map.get(phrase.lower())
                if proper is not None and not is_all_uppercase(phrase) and phrase != proper:
                    if i > 0 and tokens[i - 1].is_sentence_start and not starts_with_uppercase(proper):
                        continue
                    if all(starts_with_uppercase(w) for w in java_split(proper, ' ')):
                        msg = self.get_initial_capital_message()
                    else:
                        msg = self.get_other_capitalization_message()
                    rm = RuleMatch(self, sentence, tokens[i].start_pos, tokens[i + j - 1].end_pos, msg,
                                   self.get_short_message())
                    rm.set_suggested_replacement(proper)
                    out.append(rm)
        return out


_dash_cache = {}


def load_dash_compounds(path):
    """Port of AbstractDashRule.loadCompoundFile for an absolute file path:
    the set of the wrongly dashed variants."""
    s = _dash_cache.get(path)
    if s is not None:
        return s
    words = []
    for line in _read_lines(path):
        if not line or line[0] == '#':
            continue
        if line.endswith('+') or line.endswith('?'):
            continue
        elif line.endswith('*') or line.endswith('$'):
            line = line[:-1]
        words.append(line)
    s = set()
    for w in words:
        s.add(w.replace('-', '–'))
        s.add(w.replace('-', '—'))
        s.add(w.replace('-', ' – '))
        s.add(w.replace('-', ' — '))
    s = _dash_cache[path] = (frozenset(s), sorted({len(x) for x in s if x}))
    return s


_DASH_REPL = regex.compile(' ?[–—] ?')
_ASCII_LETTER = regex.compile('[a-zA-Z]')


class AbstractDashRule(_RuleBase):
    """Port of AbstractDashRule: compounds written with en/em dashes instead
    of hyphens. Subclasses implement get_description(), get_message() and
    get_compounds_data() (e.g. with self.load_compound_file())."""

    rule_id = 'DASH_RULE'
    category_id = 'TYPOGRAPHY'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.tags = ['picky']

    def load_compound_file(self, path):
        return load_dash_compounds(_resource_file(self.language, path))

    def get_message(self):
        raise NotImplementedError()

    def get_compounds_data(self):
        raise NotImplementedError()

    def estimate_context_for_sure_match(self):
        return 2

    def is_boundary(self, s):
        return _ASCII_LETTER.fullmatch(s) is None

    def _hits(self, text, data):
        """All occurrences, in the order of the Aho-Corasick trie output
        reversed: longest/last ending first."""
        keys, lengths = data
        hits = []
        n = len(text)
        for b in range(n):
            for ln in lengths:
                e = b + ln
                if e > n:
                    break
                if text[b:e] in keys:
                    hits.append((b, e))
        hits.sort(key=lambda h: (-h[1], -h[0]))
        return hits

    def match(self, sentence):
        out = []
        text = sentence.text
        if '–' not in text and '—' not in text:
            return out
        starts = set()
        for b, e in self._hits(text, self.get_compounds_data()):
            if b in starts:
                continue
            if b > 0 and not self.is_boundary(text[b - 1:b]):
                continue
            if e < len(text) and not self.is_boundary(text[e:e + 1]):
                continue
            rm = RuleMatch(self, sentence, b, e, self.get_message())
            rm.set_suggested_replacement(_DASH_REPL.sub('-', text[b:e]))
            out.append(rm)
            starts.add(b)
        return out


# --- confusion of words in context -----------------------------------------

_MIN_PREFIX_LENGTH = 3


def _split_top_level_alternatives(pattern):
    parts = []
    depth = 0
    start = 0
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == '\\':
            i += 2
            continue
        if c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif c == '|' and depth == 0:
            parts.append(pattern[start:i])
            start = i + 1
        i += 1
    parts.append(pattern[start:])
    return parts


def _extract_simple_prefix(alt):
    sb = []
    i = 0
    n = len(alt)
    while i < n:
        c = alt[i]
        if c == '\\' and i + 1 < n:
            i += 1
            escaped = alt[i]
            if i + 1 < n and alt[i + 1] in '?*':
                break
            sb.append(escaped)
            if i + 1 < n and alt[i + 1] == '+':
                i += 1
        elif c in '[(|.^$\\{':
            break
        elif c in '?*':
            if sb:
                sb.pop()
            break
        elif c == '+':
            break
        else:
            if i + 1 < n and alt[i + 1] in '?*':
                break
            sb.append(c)
        i += 1
    return ''.join(sb)


def _extract_word_prefix(pattern):
    prefixes = []
    for alt in _split_top_level_alternatives(pattern):
        p = _extract_simple_prefix(alt)
        if len(p) < _MIN_PREFIX_LENGTH:
            return ''
        prefixes.append(p.lower())
    if not prefixes:
        return ''
    common = prefixes[0]
    for p in prefixes[1:]:
        k = 0
        while k < min(len(common), len(p)) and common[k] == p[k]:
            k += 1
        common = common[:k]
        if len(common) < _MIN_PREFIX_LENGTH:
            return ''
    return common


def _add_boundaries(s):
    ic = ''
    if s.startswith('(?i)'):
        s = s[4:]
        ic = '(?i)'
    return ic + '\\b(' + s + ')\\b'


class ContextWords:
    __slots__ = ('matches', 'explanations', 'words', 'contexts', 'word_prefixes')

    def __init__(self):
        self.matches = ['', '']
        self.explanations = ['', '']
        self.words = [None, None]
        self.contexts = [None, None]
        self.word_prefixes = ['', '']

    def set_word(self, i, word):
        self.words[i] = jregex.compile(_add_boundaries(word))
        p = word
        if p.startswith('(?i)'):
            p = p[4:]
        elif p.startswith('(?-i)'):
            p = p[5:]
        self.word_prefixes[i] = _extract_word_prefix(p)

    def set_context(self, i, context):
        self.contexts[i] = jregex.compile(_add_boundaries(context))

    def could_match_sentence(self, sentence_lower):
        return (not self.word_prefixes[0] or self.word_prefixes[0] in sentence_lower) or \
            (not self.word_prefixes[1] or self.word_prefixes[1] in sentence_lower)


_context_words_cache = {}


def load_context_words(path):
    r = _context_words_cache.get(path)
    if r is not None:
        return r
    out = []
    for line in _read_lines(path):
        if not java_trim(line) or line[0] == '#':
            continue
        col = java_split(line, '\t')
        if len(col) >= 6:
            cw = ContextWords()
            cw.set_word(0, col[0])
            cw.set_word(1, col[1])
            cw.matches[0] = col[2]
            cw.matches[1] = col[3]
            cw.set_context(0, col[4])
            cw.set_context(1, col[5])
            if len(col) > 6:
                cw.explanations[0] = col[6]
                if len(col) > 7:
                    cw.explanations[1] = col[7]
            out.append(cw)
    r = _context_words_cache[path] = tuple(out)
    return r


class WrongWordInContextRule(_RuleBase):
    """Port of WrongWordInContextRule. Subclasses implement get_filename()
    (a rules path like '/de/wrongWordInContext.txt'), get_message_string(),
    get_short_message_string() and get_long_message_string()."""

    rule_id = 'WRONG_WORD_IN_CONTEXT'
    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Category('CONFUSED_WORDS', self.get_category_string())
        self.context_words_set = load_context_words(_rules_file(language, self.get_filename()))
        self.match_lemmas = False

    def get_filename(self):
        raise NotImplementedError()

    def get_category_string(self):
        return self.messages['category_misc']

    def get_description(self):
        return 'Confusion of words'

    def set_match_lemmas(self):
        self.match_lemmas = True

    def get_message_string(self):
        raise NotImplementedError()

    def get_short_message_string(self):
        raise NotImplementedError()

    def get_long_message_string(self):
        raise NotImplementedError()

    def match(self, sentence):
        out = []
        tokens = sentence.non_blank_tokens
        sentence_lower = sentence.text.lower()
        n = len(tokens)
        for cw in self.context_words_set:
            if not cw.could_match_sentence(sentence_lower):
                continue
            matched = [False, False]
            matchers = [cw.words[0], cw.words[1]]
            pos0 = pos1 = -1
            token1 = token2 = ''
            k = 1
            while k < n and (not matched[0] or not matched[1]):
                if not tokens[k].has_partial_pos_tag('IS_URL'):
                    t = tokens[k].token
                    if not matched[0] and matchers[0].search(t) is not None:
                        matched[0] = True
                        pos0 = k
                        token1 = t
                    if not matched[1] and matchers[1].search(t) is not None:
                        matched[1] = True
                        pos1 = k
                        token2 = t
                k += 1
            found = not_found = -1
            start_pos = end_pos = 0
            matched_token = ''
            if matched[0] and not matched[1]:
                found, not_found = 0, 1
                start_pos = tokens[pos0].start_pos
                end_pos = start_pos + len(token1)
                matched_token = token1
            elif matched[1] and not matched[0]:
                found, not_found = 1, 0
                start_pos = tokens[pos1].start_pos
                end_pos = start_pos + len(token2)
                matched_token = token2
            if found == -1:
                continue
            ctx = [False, False]
            matchers[found] = cw.contexts[found]
            matchers[not_found] = cw.contexts[not_found]
            k = 1
            while k < n and (not ctx[found] or not ctx[not_found]):
                if self.match_lemmas:
                    for at in tokens[k].readings:
                        if ctx[found] and ctx[not_found]:
                            break
                        lemma = at.lemma
                        if lemma:
                            if not ctx[found]:
                                ctx[found] = matchers[found].search(lemma) is not None
                            if not ctx[not_found]:
                                ctx[not_found] = matchers[not_found].search(lemma) is not None
                else:
                    t = tokens[k].token
                    if not ctx[found]:
                        ctx[found] = matchers[found].search(t) is not None
                    if not ctx[not_found]:
                        ctx[not_found] = matchers[not_found].search(t) is not None
                k += 1
            if ctx[not_found] and not ctx[found]:
                original = cw.matches[found]
                replacement = cw.matches[not_found]
                repl = preserve_case(jregex.java_replace(jregex.compile('(?i)' + original), replacement,
                                                         matched_token, 1), matched_token)
                msg = self._get_message(matched_token, repl, cw.explanations[not_found], cw.explanations[found])
                rule = _specific_id_rule(self, to_id(self.get_id() + '_' + matched_token + '_' + repl, self.language),
                                         self.get_description().replace('$match', matched_token + '/' + repl))
                out.append(RuleMatch(rule, sentence, start_pos, end_pos, msg, self.get_short_message_string()))
        return out

    def _get_message(self, wrong_word, suggestion, expl_suggestion, expl_wrong_word):
        if not expl_suggestion or not expl_wrong_word:
            s = self.get_message_string()
            s = s.replace('$SUGGESTION', suggestion, 1)
            return s.replace('$WRONGWORD', wrong_word, 1)
        s = self.get_long_message_string()
        s = s.replace('$SUGGESTION', suggestion, 1)
        s = s.replace('$WRONGWORD', wrong_word, 1)
        s = s.replace('$EXPLANATION_SUGGESTION', expl_suggestion, 1)
        return s.replace('$EXPLANATION_WRONGWORD', expl_wrong_word, 1)
