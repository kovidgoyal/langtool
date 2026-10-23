"""Khmer specific rules (port of org.languagetool.rules.km)."""

from ... import jregex
from ...rules.abstract_rules import AbstractSimpleReplaceRule2, AbstractSpaceBeforeRule
from ...rules.base import RuleMatch
from ...rules.core import CoreRule, GenericUnpairedBracketsRule
from ...tools import is_letter, java_equals_ignore_case

KHMER_SIMPLE_REPLACE_RULE = 'KM_SIMPLE_REPLACE'


class KhmerSimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.km.KhmerSimpleReplaceRule: words or
    groups of words of /km/coherency.txt that are incorrect or obsolete.
    (getLocale() returns Locale("km"); AbstractSimpleReplaceRule2 does not
    use it.)"""

    def get_file_names(self):
        return ['/km/coherency.txt']

    def get_id(self):
        return KHMER_SIMPLE_REPLACE_RULE

    def get_description(self):
        return 'Words or groups of words that are incorrect or obsolete'

    def get_short(self):
        return 'Consider following the spelling of Chuon Nath'

    def get_message(self):
        return ' Consider following the spelling of Chuon Nath '

    def get_suggestions_separator(self):
        return ' or '


class KhmerWordRepeatRule(CoreRule):
    """Port of org.languagetool.rules.km.KhmerWordRepeatRule: a word that is
    repeated directly (separated only by a zero width space, not by a real
    space)."""

    rule_id = 'KM_WORD_REPEAT_RULE'
    description_key = 'desc_repetition'

    def match(self, sentence):
        out = []
        tokens = sentence.non_blank_tokens
        tokens_with_ws = sentence.tokens
        prev = ''
        # we start from token 1, token 0 is SENT_START
        for i in range(1, len(tokens)):
            token = tokens[i].token
            if self._is_word(token) and java_equals_ignore_case(prev, token) \
                    and not self._ignore(sentence, tokens_with_ws, i):
                prev_pos = tokens[i - 1].start_pos
                pos = tokens[i].start_pos
                rm = RuleMatch(self, sentence, prev_pos, pos + len(prev), self.messages['repetition'],
                               self.messages['desc_repetition_short'])
                rm.set_suggested_replacements([
                    prev + ' ' + token,  # case 1: replace zero-width space w/ real space
                    prev,                # case 2: remove repeated word - same as original suggestion
                    prev + 'ៗ',          # case 3: same as case 2, just add "repetition character"
                ])
                out.append(rm)
            prev = token
        return out

    @staticmethod
    def _is_word(token):
        # avoid "..." etc. to be matched (token.length() == 1 is a UTF-16 length)
        if len(token) == 1 and ord(token) <= 0xffff and not is_letter(token):
            return False
        return True

    @staticmethod
    def _ignore(sentence, tokens_with_ws, position):
        orig_pos = sentence.get_original_position(position)
        return position >= 1 and tokens_with_ws[orig_pos - 1].token == ' '


KM_START_SYMBOLS = ['[', '(', '{', '“', '"', "'", '«']
KM_END_SYMBOLS = [']', ')', '}', '”', '"', "'", '»']


class KhmerUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.km.KhmerUnpairedBracketsRule."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, KM_START_SYMBOLS, KM_END_SYMBOLS)

    def get_id(self):
        return 'KM_UNPAIRED_BRACKETS'


_CONJUNCTIONS = jregex.compile('ដើម្បី|និង|ពីព្រោះ', jregex.IGNORECASE)  # CASE_INSENSITIVE|UNICODE_CASE


class KhmerSpaceBeforeRule(AbstractSpaceBeforeRule):
    """Port of org.languagetool.rules.km.KhmerSpaceBeforeRule: a missing
    space before the conjunctions ដើម្បី, និង and ពីព្រោះ."""

    def get_conjunctions(self):
        return _CONJUNCTIONS

    def get_id(self):
        return 'KM_SPACE_BEFORE_CONJUNCTION'
