"""Breton specific rules (port of org.languagetool.rules.br)."""

import os
import threading
from collections import deque

from ...rules.abstract_rules import AbstractCompoundRule, load_compound_rule_data
from ...rules.base import RuleMatch
from ...rules.core import Categories, CoreRule
from ...tools import is_whitespace, java_split, java_trim, starts_with_uppercase, uppercase_first_char
from .tokenizers import BretonWordTokenizer

BRETON_TOPO = 'BR_TOPO'

_FILE_NAME = '/br/topo.txt'

_words_cache = {}
_words_lock = threading.Lock()


def _topo_file(language):
    from ...language import RULES_DIR
    rel = _FILE_NAME.lstrip('/')
    if language is not None:
        p = os.path.join(language.rules_root, rel)
        if os.path.exists(p):
            return p
    return os.path.join(RULES_DIR, rel)


def _load_words(path):
    """Load the list of words (TopoReplaceRule.loadWords): returns a list of
    dicts containing the error-corrections pairs; the n-th dict contains key
    strings of (n+1) words. Several wrong forms can be separated by '|'."""
    result = []
    word_tokenizer = BretonWordTokenizer()
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = java_trim(line.rstrip('\r\n'))
            if not line or line[0] == '#':  # ignore comments
                continue
            parts = java_split(line, '=')
            if len(parts) != 2:
                raise RuntimeError('Format error in file ' + path + ', line: ' + line)
            for wrong_form in java_split(parts[0], '|'):  # multiple incorrect forms
                word_count = sum(1 for token in word_tokenizer.tokenize(wrong_form) if not is_whitespace(token))
                # grow if necessary
                while len(result) < word_count:
                    result.append({})
                result[word_count - 1][wrong_form] = parts[1]
    return result


def _wrong_words(path):
    words = _words_cache.get(path)
    if words is None:
        with _words_lock:
            words = _words_cache.get(path)
            if words is None:
                words = _words_cache[path] = _load_words(path)
    return words


class TopoReplaceRule(CoreRule):
    """Port of org.languagetool.rules.br.TopoReplaceRule: place names in
    French which should be translated into Breton. Loads the list of words
    from rules/br/topo.txt (the n-th map contains the wrong forms of n+1
    words, they are matched longest first)."""

    category_id = 'MISC'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self._wrong_words = _wrong_words(_topo_file(language))

    def get_id(self):
        return BRETON_TOPO

    def get_description(self):
        return 'anvioù-lec’h e brezhoneg'

    def get_short(self):
        return 'anvioù lec’h'

    def get_suggestion(self):
        return ' zo un anv lec’h gallek. Ha fellout a rae deoc’h skrivañ '

    def get_suggestions_separator(self):
        """The word used to separate multiple suggestions; used only before
        the last suggestion, the rest are comma-separated."""
        return ' pe '

    def is_case_sensitive(self):
        return True

    def get_wrong_words(self):
        """The list of wrong words for which this rule can suggest
        corrections."""
        return self._wrong_words

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.non_blank_tokens
        wrong_words = self._wrong_words
        # Java: an ArrayBlockingQueue with capacity wrongWords.size(), the
        # oldest token is dropped when it is full
        prev_tokens = deque(maxlen=len(wrong_words))
        for i in range(1, len(tokens)):
            prev_tokens.append(tokens[i])
            variants = []
            prev_tokens_list = list(prev_tokens)
            sb = ''
            for j in range(len(prev_tokens_list) - 1, -1, -1):
                if j != len(prev_tokens_list) - 1 and prev_tokens_list[j + 1].whitespace_before:
                    sb = ' ' + sb
                sb = prev_tokens_list[j].token + sb
                variants.insert(0, sb)
            length = len(variants)  # prev_tokens_list and variants have now the same length
            for j in range(length):  # longest words first
                crt_word_count = length - j
                if prev_tokens_list[length - crt_word_count].immunized:
                    continue
                crt = variants[j]
                if self.is_case_sensitive():
                    crt_match = wrong_words[crt_word_count - 1].get(crt)
                else:
                    crt_match = wrong_words[crt_word_count - 1].get(crt.lower())
                if crt_match is not None:
                    replacements = java_split(crt_match, '|')
                    msg = crt + self.get_suggestion()
                    for k, replacement in enumerate(replacements):
                        if k > 0:
                            msg += self.get_suggestions_separator() if k == len(replacements) - 1 else ', '
                        msg += '<suggestion>' + replacement + '</suggestion>'
                    msg += '?'
                    start_pos = prev_tokens_list[length - crt_word_count].start_pos
                    end_pos = prev_tokens_list[length - 1].end_pos
                    potential_rule_match = RuleMatch(self, sentence, start_pos, end_pos, msg, self.get_short())
                    if not self.is_case_sensitive() and starts_with_uppercase(crt):
                        replacements = [uppercase_first_char(r) for r in replacements]
                    potential_rule_match.set_suggested_replacements(replacements)
                    rule_matches.append(potential_rule_match)
                    break
        return rule_matches


class BretonCompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.br.BretonCompoundRule: checks that
    compounds (if in the list /br/compounds.txt) are not written as separate
    words. (Not used by Breton.getRelevantRules.)"""

    issue_type = 'Grammar'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Skrivet e vez ar ger-mañ boaz gant ur varrennig-stagañ.',
                         'Ar ger-mañ a zo skrivet boaz evel unan hepken.',
                         'An droienn-mañ a zo skrivet evel ur ger hepken pe gant ur varrennig-stagañ.',
                         'Kudenn barrennig-stagañ')
        self.category = Categories.get('COMPOUNDING', messages)
        self.add_example_pair("Gwelet em eus un <marker>alc'hweder gwez</marker> e-kerzh an dibenn-sizhun-mañ.",
                              "Gwelet em eus un <marker>alc'hweder-gwez</marker> e-kerzh an dibenn-sizhun-mañ.")

    def get_id(self):
        return 'BR_COMPOUNDS'

    def get_description(self):
        return 'Mots composés'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/br/compounds.txt')
