"""Port of org.languagetool.rules.en.AvsAnRule and AvsAnData."""

import os
import threading

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...language import RULES_DIR
from ...rules.base import RuleMatch
from ...rules.core import CoreRule
from ...tools import (is_all_uppercase, is_empty, is_mixed_case, java_trim, lowercase_first_char_if_capitalized,
                      starts_with_uppercase)

A, AN, A_OR_AN, UNKNOWN = 'A', 'AN', 'A_OR_AN', 'UNKNOWN'

_CLEANUP_PATTERN = jregex.compile("[^αa-zA-Z0-9.;,:']")
_DELIM_PATTERN = jregex.compile('[-"“\'‘()\\[\\]]+')
_DASH_QUOTE_PATTERN = jregex.compile("[-']")
_AN_PREFIXES = jregex.compile('^(unidentif|uni[mn])[a-z]+$', jregex.IGNORECASE)
_AN_EXCEPTION_PREFIXES = jregex.compile('^(eu|one|uni|u[rst][aeiou])[a-z]*$', jregex.IGNORECASE)

_data = None
_data_lock = threading.Lock()


def _load_words(path):
    """AvsAnData.loadWords: words normalized to lowercase unless starting
    with '*'"""
    words = set()
    with open(path, encoding='utf-8') as f:
        for line in f.read().splitlines():
            line = java_trim(line)
            if not line or line[0] == '#':
                continue
            if line[0] == '*':
                words.add(line[1:])
            else:
                words.add(line.lower())
    return frozenset(words)


def _avs_an_data():
    """(words requiring 'a', words requiring 'an'): /en/det_a.txt and
    /en/det_an.txt of the rules directory"""
    global _data
    with _data_lock:
        if _data is None:
            _data = (_load_words(os.path.join(RULES_DIR, 'en', 'det_a.txt')),
                     _load_words(os.path.join(RULES_DIR, 'en', 'det_an.txt')))
        return _data


def _java_regex_split(pattern, s):
    """String.split(regex) for a pattern without zero-width matches:
    trailing empty strings are removed"""
    if pattern.search(s) is None:
        return [s]
    parts = pattern.split(s)
    while parts and parts[-1] == '':
        parts.pop()
    return parts


def _is_vowel(c):
    return c.lower() in ('a', 'e', 'i', 'o', 'u')


def get_correct_determiner_for(token):
    """AvsAnRule.getCorrectDeterminerFor(AnalyzedTokenReadings)"""
    requires_a, requires_an = _avs_an_data()
    word = token.token
    determiner = UNKNOWN
    parts = _java_regex_split(_DASH_QUOTE_PATTERN, word)  # for example, in "one-way" only "one" is relevant
    if len(parts) >= 1 and parts[0].lower() != 'a':  # avoid false alarm on "A-levels are..."
        word = parts[0]
    if token.whitespace_before or word != '-':  # e.g., 'a- or anti- are prefixes'
        word = jregex.java_replace(_CLEANUP_PATTERN, '', word)  # e.g. >>an "industry party"<<
        if is_empty(word):
            return UNKNOWN
    if word.lower() in requires_a or word in requires_a:
        determiner = A
    if word.lower() in requires_an or word in requires_an:
        if determiner == A:
            determiner = A_OR_AN  # e.g. for 'historical'
        else:
            determiner = AN
    if determiner == UNKNOWN:
        token_first_char = word[0]
        if is_all_uppercase(word) or is_mixed_case(word):
            # we don't know how all-uppercase words (often abbreviations) are pronounced,
            # so never complain about these
            determiner = UNKNOWN
        elif _AN_PREFIXES.search(token.token):
            determiner = AN
        elif _is_vowel(token_first_char) and not _AN_EXCEPTION_PREFIXES.search(token.token):
            determiner = AN
        else:
            determiner = A
    return determiner


class AvsAnRule(CoreRule):
    """Check if the determiner (if any) preceding a word is "an" if the next
    word starts with a vowel, "a" if the next word does not start with a
    vowel. This rule loads some exceptions from external files det_a.txt
    and det_an.txt (e.g. for "an hour")."""

    rule_id = 'EN_A_VS_AN'
    category_id = 'MISC'
    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.url = 'https://languagetool.org/insights/post/indefinite-articles/'
        self.add_example_pair('The train arrived <marker>a hour</marker> ago.',
                              'The train arrived <marker>an hour</marker> ago.')

    def get_description(self):
        return "Use of 'a' vs. 'an'"

    def estimate_context_for_sure_match(self):
        return 1

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        prev_token_index = 0
        for i in range(1, len(tokens)):  # ignoring token 0, i.e., SENT_START
            token = tokens[i]
            prev_token_str = tokens[prev_token_index].token if prev_token_index > 0 else None
            is_sentence_start = prev_token_index == 1
            if not is_sentence_start:
                equals_a = prev_token_str == 'a'
                equals_an = prev_token_str == 'an'
            else:
                equals_a = prev_token_str is not None and prev_token_str.lower() == 'a'
                equals_an = prev_token_str is not None and prev_token_str.lower() == 'an'
            if equals_a or equals_an:
                determiner = get_correct_determiner_for(token)
                msg = None
                if equals_a and determiner == AN:
                    replacement = 'An' if starts_with_uppercase(prev_token_str) else 'an'
                    msg = ('Use <suggestion>' + replacement + "</suggestion> instead of '" + prev_token_str
                           + "' if the following word starts with a vowel sound, e.g. 'an article', 'an hour'.")
                elif equals_an and determiner == A:
                    replacement = 'A' if starts_with_uppercase(prev_token_str) else 'a'
                    msg = ('Use <suggestion>' + replacement + "</suggestion> instead of '" + prev_token_str
                           + "' if the following word doesn't start with a vowel sound, e.g. 'a sentence', "
                             "'a university'.")
                if msg is not None:
                    prev = tokens[prev_token_index]
                    rule_matches.append(RuleMatch(self, sentence, prev.start_pos, prev.end_pos, msg,
                                                  'Wrong article', pattern_from_pos=prev.start_pos,
                                                  pattern_to_pos=token.end_pos))
            next_token = tokens[i + 1].token if i + 1 < len(tokens) else ''
            if token.has_pos_tag('DT'):
                prev_token_index = i
            elif len(next_token) > 1 and _DELIM_PATTERN.fullmatch(token.token):
                pass  # skip e.g. the quote in >>an "industry party"<<
            else:
                prev_token_index = 0
        return rule_matches

    def suggest_a_or_an(self, orig_word):
        """Adds "a" or "an" to the English noun. Used for suggesting the
        proper form of the indefinite article. For the rare cases where both
        "a" and "an" are considered okay (e.g. for "historical"), "a" is
        returned. Returns the word with a determiner, or just the word if
        the word is an abbreviation."""
        return suggest_a_or_an(orig_word)


def suggest_a_or_an(orig_word):
    """AvsAnRule.suggestAorAn"""
    token = AnalyzedTokenReadings(AnalyzedToken(orig_word, None, None), 0)
    determiner = get_correct_determiner_for(token)
    if determiner == A or determiner == A_OR_AN:
        return 'a ' + lowercase_first_char_if_capitalized(orig_word)
    if determiner == AN:
        return 'an ' + lowercase_first_char_if_capitalized(orig_word)
    return orig_word
