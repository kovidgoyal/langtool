"""Port of org.languagetool.rules.ca.CatalanMultitokenSpeller and
org.languagetool.tagging.disambiguation.ca.CatalanMultitokenDisambiguator."""

import threading

from ...analysis import AnalyzedSentence, AnalyzedToken
from ...rules.multitoken import MultitokenSpeller, WeightedSuggestion
from ...tools import is_upper_case
from .spelling import multitoken_dictionary_speller, prepare_line_for_speller


class CatalanMultitokenSpeller(MultitokenSpeller):
    """The MultitokenSpeller for /ca/multiwords.txt, /spelling_global.txt
    and /ca/hyphenated_words.txt (the lines are prepared with
    Catalan.prepareLineForSpeller), with the additional suggestions of the
    speller of /ca/ca-ES_spelling_multitoken.dict (CatalanMorfologikMultitokenSpeller)."""

    def __init__(self, language, file_paths, spelling_rule=None):
        super().__init__(language, file_paths, spelling_rule)
        self.speller = multitoken_dictionary_speller(language)

    def prepare_line_for_speller(self, s):
        return prepare_line_for_speller(s)

    def get_additional_suggestions(self, original_word):
        if self.speller is not None:
            # the weights from the dict are different!
            return [WeightedSuggestion(w, weight) for w, weight in self.speller.get_suggestions(original_word)]
        return []


_instance = []
_lock = threading.Lock()


def catalan_multitoken_speller(language):
    """CatalanMultitokenSpeller.INSTANCE (for the language ca-ES in Java,
    i.e. Catalan, whose default spelling rule is used), for all variants"""
    with _lock:
        if not _instance:
            from ...api import get_language
            ca = get_language('ca-ES')
            _instance.append(CatalanMultitokenSpeller(
                ca, [ca.resource_path('ca/multiwords.txt'), ca.resource_path('spelling_global.txt'),
                     ca.resource_path('ca/hyphenated_words.txt')],
                ca.get_default_spelling_rule()))
        return _instance[0]


_WINDOW_FORWARD = 10
_WINDOW_BACKWARD = 6
# SearchType
_NONE, _SHRINK_FROM_END, _SHRINK_FROM_START = range(3)
_DICTIONARY_FIXES = ('Santa María', 'San Agustin')


def _starts_upper(atr):
    return bool(atr.token) and is_upper_case(atr.token[0])


class CatalanMultitokenDisambiguator:
    """Unknown words that are part of a multi-word proper noun accepted by
    the speller of /ca/ca-ES_spelling_multitoken.dict (searched in the
    surrounding phrase in title case, then forward from an uppercase word,
    then backward) get the reading NPCNM00 with the phrase as lemma (for all
    the tokens of the phrase). Without the dictionary nothing is done."""

    def __init__(self, language):
        self.speller = multitoken_dictionary_speller(language)

    def disambiguate(self, sentence):
        if self.speller is None:
            return sentence
        an_tokens = sentence.tokens
        n = len(an_tokens)
        for i in range(1, n):
            t = an_tokens[i]
            if not t.is_whitespace and not t.is_tagged() and not t.ignored_by_speller:
                from_index, to_index = self._get_to_and_for_indexes(an_tokens, i)
                found = self._search_in_dict_and_tag(an_tokens, from_index, to_index, _NONE)
                # Forward
                if not found and _starts_upper(t):
                    found = self._search_in_dict_and_tag(an_tokens, i, min(i + _WINDOW_FORWARD, n - 1),
                                                         _SHRINK_FROM_END)
                # Backward
                if not found:
                    self._search_in_dict_and_tag(an_tokens, max(1, i - _WINDOW_BACKWARD), i, _SHRINK_FROM_START)
        return AnalyzedSentence(an_tokens)

    def _search_in_dict_and_tag(self, tokens, from_, to, shrink_from):
        current_from = from_
        current_to = to
        while current_to > current_from:
            text_to_check = self._get_text_from_to(tokens, current_from, current_to)
            if text_to_check in _DICTIONARY_FIXES:
                return False
            if (not text_to_check.endswith(' ') and not text_to_check.startswith(' ') and text_to_check
                    and not self.speller.is_misspelled(text_to_check)):
                for j in range(current_from, current_to + 1):
                    if not tokens[j].is_whitespace:
                        tokens[j].add_reading(AnalyzedToken(tokens[j].token, 'NPCNM00', text_to_check),
                                              'HybridDisamb')
                return True
            if shrink_from == _SHRINK_FROM_END:
                current_to -= 1
            elif shrink_from == _SHRINK_FROM_START:
                current_from += 1
            else:
                return False
        return False

    @staticmethod
    def _get_to_and_for_indexes(tokens, start_index):
        """Search for phrases in Title Case (except prepositions)"""
        from_index = start_index
        while from_index > 1 and (_starts_upper(tokens[from_index - 1]) or tokens[from_index - 1].is_whitespace
                                  or len(tokens[from_index - 1].token) < 3):
            from_index -= 1
        while not _starts_upper(tokens[from_index]) and from_index < start_index:
            from_index += 1
        to_index = start_index
        while to_index < len(tokens) - 1 and (_starts_upper(tokens[to_index + 1]) or tokens[to_index + 1].is_whitespace
                                              or len(tokens[to_index + 1].token) < 3):
            to_index += 1
        while not _starts_upper(tokens[to_index]) and to_index > start_index:
            to_index -= 1
        return from_index, to_index

    @staticmethod
    def _get_text_from_to(an_tokens, index_from, index_to):
        sb = []
        for i in range(index_from, index_to + 1):
            if i > len(an_tokens) - 1:
                return ''
            sb.append(an_tokens[i].token)
        return ''.join(sb)
