"""Dutch specific rules (port of org.languagetool.rules.nl): CheckCaseRule,
CompoundRule, DutchWrongWordInContextRule, PreferredWordRule (with
PreferredWordData and PreferredWordRuleWithSuggestion), SimpleReplaceRule,
SpaceInCompoundRule, WordCoherencyRule and the helper class Tools
(glue_parts).

The Java rules that use a Locale("nl") for case conversion (it has no
special case mapping) use the default lower() here."""

import os
import threading

from ... import jregex
from ...rules.abstract_rules import (CS, AbstractCheckCaseRule, AbstractCompoundRule, AbstractSimpleReplaceRule2,
                                     AbstractWordCoherencyRule, SpecificIdRule, WrongWordInContextRule,
                                     load_compound_rule_data, to_id, _read_lines, _resource_file)
from ...rules.base import MISC, Category, RuleMatch
from ...rules.core import CoreRule
from ...tools import is_lower_case, is_upper_case, java_split

# --- Tools -----------------------------------------------------------------

_SPELLED_WORDS = ('abc|adv|aed|apk|b2b|bh|bhv|bso|btw|bv|cao|cd|cfk|ckv|cv|dc|dj|dtp|dvd|fte|gft|ggo|ggz|gm|gmo|gps|'
                  'gsm|hbo|hd|hiv|hr|hrm|hst|ic|ivf|kmo|lcd|lp|lpg|lsd|mbo|mdf|mkb|mms|msn|mt|ngo|nv|ob|ov|ozb|p2p|pc|'
                  'pcb|pdf|pk|pps|pr|pvc|roc|rvs|sms|tbc|tbs|tl|tv|uv|vbo|vj|vmbo|vsbo|vwo|wc|wo|xtc|zzp')
_SPELLED_WORDS_SET = frozenset(_SPELLED_WORDS.split('|'))
_ENDS_IN_DIGIT = jregex.compile('.*[0-9]$')
_STARTS_WITH_DIGIT = jregex.compile('^[0-9].*')
_ENDS_IN_HYPHEN_AND_CHAR = jregex.compile('.+-[a-z]$')
_STARTS_WITH_CHAR_AND_HYPHEN = jregex.compile('^[a-z]-.+')
_HYPHEN_CHARS = jregex.compile('(^|.+-)?(' + _SPELLED_WORDS + ')')
_CHARS_HYPHEN = jregex.compile('(' + _SPELLED_WORDS + ')(-.+|$)?')
_CONNECTIONS = ('aa', 'ae', 'ai', 'ao', 'au', 'ee', 'ei', 'eu', 'ée', 'éi', 'éu', 'ie', 'ii', 'oe', 'oi', 'oo', 'ou',
                'ui', 'uu', 'ij')


def glue_parts(s):
    """Port of Tools.glueParts: joins the parts of a compound, with a
    hyphen where Dutch spelling needs one (colliding vowels, case changes,
    digits, spelled abbreviations like "tv")."""
    compound = s[0]
    for word2 in s[1:]:
        if len(compound) > 2 or compound in _SPELLED_WORDS_SET:
            last_char = compound[-1]
            first_char = word2[0]
            connection = last_char + first_char
            if (any(c in connection for c in _CONNECTIONS)
                    or is_upper_case(first_char) and is_lower_case(last_char)
                    or is_upper_case(last_char) and is_lower_case(first_char)
                    or is_upper_case(last_char) and is_upper_case(first_char)
                    or _ENDS_IN_DIGIT.fullmatch(compound)
                    or _STARTS_WITH_DIGIT.fullmatch(word2)
                    or _HYPHEN_CHARS.fullmatch(compound)
                    or _CHARS_HYPHEN.fullmatch(word2)
                    or _ENDS_IN_HYPHEN_AND_CHAR.fullmatch(compound)
                    or _STARTS_WITH_CHAR_AND_HYPHEN.fullmatch(word2)):
                compound = compound + '-' + word2
            else:
                compound += word2
        else:
            compound += word2
    return compound


# --- rules -----------------------------------------------------------------

class CheckCaseRule(AbstractCheckCaseRule):
    """Port of org.languagetool.rules.nl.CheckCaseRule: words of
    /nl/check_case.txt with a wrong case; abbreviations like "apk, dvd" are
    not ignored."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.use_sub_rule_specific_ids()
        # do not ignore abbreviations like "apk, dvd" etc
        self.set_ignore_short_uppercase_words(False)

    def get_file_names(self):
        return ['/nl/check_case.txt']

    def get_id(self):
        return 'NL_CHECKCASE'

    def get_description(self):
        return 'Controle op hoofd- en kleine letters: $match'

    def get_short(self):
        return 'Schrijfwijze'

    def get_message(self):
        return 'Juiste schrijfwijze'


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.nl.CompoundRule: compounds (listed in
    /nl/compounds.txt) that are not written as separate words."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Dit woord hoort waarschijnlijk aaneengeschreven met een koppelteken.',
                         'Dit woord hoort waarschijnlijk aaneengeschreven.',
                         'Deze uitdrukking hoort mogelijk aan elkaar, eventueel met een koppelteken.',
                         'Koppeltekenprobleem')
        self.sentence_starts_with_upper_case = True
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'NL_COMPOUNDS'

    def get_description(self):
        return "Woorden die aaneengeschreven horen, bijvoorbeeld 'zee-egel' i.p.v. 'zee egel': $match"

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/nl/compounds.txt')


class DutchWrongWordInContextRule(WrongWordInContextRule):
    """Port of org.languagetool.rules.nl.DutchWrongWordInContextRule: easily
    confused words (/nl/wrongWordInContext.txt)."""

    def get_category_string(self):
        return 'Gemakkelijk te verwarren woorden'

    def get_id(self):
        return 'DUTCH_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'Woordverwarring: $match'

    def get_filename(self):
        return '/nl/wrongWordInContext.txt'

    def get_message_string(self):
        return "Mogelijk verwarring: Bedoelde u <suggestion>$SUGGESTION</suggestion> i.p.v. '$WRONGWORD'?"

    def get_short_message_string(self):
        return 'Mogelijk verwarring'

    def get_long_message_string(self):
        return ('Mogelijk verwarring: Bedoelde u <suggestion>$SUGGESTION</suggestion> (= $EXPLANATION_SUGGESTION) '
                "i.p.v. '$WRONGWORD' (= $EXPLANATION_WRONGWORD)?")


class PreferredWordRuleWithSuggestion:
    """Port of org.languagetool.rules.nl.PreferredWordRuleWithSuggestion."""

    __slots__ = ('rule', 'old_word', 'new_word')

    def __init__(self, rule, old_word, new_word):
        if rule is None or old_word is None or new_word is None:
            raise TypeError('rule, old_word and new_word must not be None')
        self.rule = rule
        self.old_word = old_word
        self.new_word = new_word


_preferred_word_data = {}
_preferred_word_lock = threading.Lock()


def preferred_word_data(rule_desc, file_path, rule_id):
    """Port of org.languagetool.rules.nl.PreferredWordData: less to more
    common words loaded from CSV (file_path relative to the resource
    directory, like '/nl/preferredwords.csv'); a list of
    PreferredWordRuleWithSuggestion, each with a PatternRule
    '<rule_id>_INTERNAL' with case sensitive tokens for the old word.
    Cached (static in Java)."""
    from ...api import get_language
    from ...patterns.pattern_token import PatternToken
    from ...patterns.rules import PatternRule
    key = (rule_desc, file_path, rule_id)
    with _preferred_word_lock:
        data = _preferred_word_data.get(key)
        if data is not None:
            return data
        dutch = get_language('nl')
        message = 'Voor dit woord is een gebruikelijker alternatief.'
        short_message = 'Gebruikelijker woord'
        data = []
        for line in _read_lines(_resource_file(dutch, file_path)):
            if line.startswith('#'):
                continue
            parts = java_split(line, ';')
            if len(parts) != 2:
                raise ValueError('Unexpected format in file ' + file_path + ': ' + line)
            old_word, new_word = parts
            pattern_tokens = [PatternToken(part, case_sensitive=True) for part in java_split(old_word, ' ')]
            rule = PatternRule(rule_id + '_INTERNAL', dutch, pattern_tokens, rule_desc, message, short_message)
            data.append(PreferredWordRuleWithSuggestion(rule, old_word, new_word))
        _preferred_word_data[key] = data
        return data


class PreferredWordRule(CoreRule):
    """Port of org.languagetool.rules.nl.PreferredWordRule: finds words for
    which a better variant exists (/nl/preferredwords.csv). As in Java, the
    matches are those of the internal pattern rules
    (NL_PREFERRED_WORD_RULE_INTERNAL)."""

    category_id = 'STYLE'
    issue_type = 'Style'

    DESC = 'Suggereert een gebruikelijker woord.'
    RULE_ID = 'NL_PREFERRED_WORD_RULE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Hij vindt <marker>rijwiel</marker> een ouderwets woord.',
                              'En ik vind <marker>fiets</marker> ook beter.')

    def get_id(self):
        return self.RULE_ID

    def get_description(self):
        return self.DESC

    def estimate_context_for_sure_match(self):
        return 1

    def get_data(self):
        return preferred_word_data(self.DESC, '/nl/preferredwords.csv', self.RULE_ID)

    def match(self, sentence):
        rule_matches = []
        text = sentence.text
        for rule_with_suggestion in self.get_data():
            matches = rule_with_suggestion.rule.match(sentence)
            if matches:
                match = matches[0]
                matched_text = text[match.from_pos:match.to_pos]
                suggestion = matched_text.replace(rule_with_suggestion.old_word, rule_with_suggestion.new_word)
                if suggestion != matched_text:
                    match.set_suggested_replacement(suggestion)
                    rule_matches.extend(matches)
        return rule_matches


DUTCH_SIMPLE_REPLACE_RULE = 'NL_SIMPLE_REPLACE'


class SimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.nl.SimpleReplaceRule: words or phrases
    of /nl/replace.txt which should not be used, case sensitive (Java
    passes a new Dutch() as the language)."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.use_sub_rule_specific_ids()
        self.category = Category('VERGISSINGEN', 'Vergissingen')
        self.add_example_pair('<marker>klaa</marker>.', '<marker>klaar</marker>.')

    def get_case_sensitivity(self):
        # edit by R. Baars 19-11-2022 to make routine case sensitive
        return CS

    def get_file_names(self):
        return ['/nl/replace.txt']

    def get_id(self):
        return DUTCH_SIMPLE_REPLACE_RULE

    def get_description(self, details=None):
        if details is not None:
            return 'Snelle correctie van veel voorkomende vergissingen: ' + details
        return 'Snelle correctie van veel voorkomende vergissingen ($match)'

    def get_short(self):
        return 'Vergissing?'

    def get_message(self):
        return "'$match' zou fout kunnen zijn. Misschien bedoelt u: $suggestions"


_SPACE_IN_COMPOUND_FILE = '/nl/multipartcompounds.txt'
_space_in_compound_data = {}
_space_in_compound_lock = threading.Lock()


def generate_variants(so_far, parts, result):
    """SpaceInCompoundRule.generateVariants: adds the variants of the parts
    with at least one space to the set result."""
    if len(parts) == 1:
        if ' ' in so_far:
            result.add(so_far + parts[0])
        result.add(so_far + ' ' + parts[0])
    else:
        rest = parts[1:]
        generate_variants(so_far + parts[0], rest, result)
        if so_far:
            generate_variants(so_far + ' ' + parts[0], rest, result)


def _space_in_compound_data_for(path):
    """normalizedCompound2message and the variants (Java: a static
    Aho-Corasick trie), here a character trie of nested dicts, None marking
    the end of a variant."""
    with _space_in_compound_lock:
        r = _space_in_compound_data.get(path)
        if r is not None:
            return r
        # (cached on disk, see langtool.diskcache)
        from ... import diskcache
        r = _space_in_compound_data[path] = diskcache.cached(
            'nl-space-in-compound', (os.path.abspath(path),), lambda: _build_space_in_compound_data(path),
            deps=[os.path.abspath(path)])
        return r


def _build_space_in_compound_data(path):
    result = set()
    normalized_compound2message = {}
    lines = _read_lines(path)
    line_counts = {}
    for line in lines:
        line_counts[line] = line_counts.get(line, 0) + 1
    for line in lines:
        if line.startswith('#'):
            continue
        line_parts = java_split(line, '|')
        word_parts = line_parts[0]
        if ' ' not in word_parts:
            raise ValueError('Unexpected format in ' + _SPACE_IN_COMPOUND_FILE + ", expected multi-word (i.e. "
                             "spaces) left of the '|': " + line)
        words = java_split(word_parts, ' ')
        generate_variants('', words, result)
        # Spaces in different places should not be counted as duplicates
        if line_counts.get(word_parts, 0) > 1:
            raise ValueError("Duplicate item '" + word_parts + "' in file " + _SPACE_IN_COMPOUND_FILE)
        message = 'Waarschijnlijk bedoelt u: ' + glue_parts(words)
        if len(line_parts) == 2:
            message += ' (' + line_parts[1] + ')'
        normalized_compound2message[glue_parts(words)] = message
    trie = {}
    for variant in result:
        node = trie
        for c in variant:
            node = node.setdefault(c, {})
        node[None] = True
    return normalized_compound2message, trie


def _is_boundary(c):
    return not ('a' <= c <= 'z' or 'A' <= c <= 'Z')


class SpaceInCompoundRule(CoreRule):
    """Port of org.languagetool.rules.nl.SpaceInCompoundRule: compounds of
    /nl/multipartcompounds.txt written with spaces ("lange afstand loper"
    instead of "langeafstandloper"). Java finds the variants with an
    Aho-Corasick trie; here the variants are looked up with a character
    trie at every position, and the hits are processed in the order of the
    Aho-Corasick search (by end position, longer hits first)."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        # Java calls the Rule() constructor, without messages
        self.category = MISC

    def get_id(self):
        return 'NL_SPACE_IN_COMPOUND'

    def get_description(self):
        return 'Detecteert spatiefouten'

    def _data(self):
        return _space_in_compound_data_for(_resource_file(self.language, _SPACE_IN_COMPOUND_FILE))

    def _hits(self, text, trie):
        hits = []
        n = len(text)
        for begin in range(n):
            if begin > 0 and not _is_boundary(text[begin - 1]):
                # prevent substring matches
                continue
            node = trie
            i = begin
            while i < n:
                node = node.get(text[i])
                if node is None:
                    break
                i += 1
                if None in node and (i == n or _is_boundary(text[i])):
                    hits.append((begin, i))
        hits.sort(key=lambda h: (h[1], h[0]))
        return hits

    def match(self, sentence):
        normalized_compound2message, trie = self._data()
        matches = []
        text = sentence.text
        for begin, end in self._hits(text, trie):
            covered = text[begin:end]
            covered_no_spaces = glue_parts(java_split(covered, ' '))
            message = normalized_compound2message.get(covered_no_spaces)
            if message is not None:
                id = to_id(self.get_id() + '_' + covered, self.language)
                specific_id_rule = SpecificIdRule(id, self.get_description(), self.premium, self.category,
                                                  self.loc_quality_issue_type, self.tags)
                match = RuleMatch(specific_id_rule, sentence, begin, end, message, None, begin, end, False,
                                  suggestions_out_msg='')
                match.set_suggested_replacement(covered_no_spaces)
                matches.append(match)
        return matches


class WordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.nl.WordCoherencyRule: words with
    several correct spellings (/nl/coherency.txt) should be written
    consistently."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair(
            'We raden af om in één tekst zowel <marker>organogram</marker> als <marker>organigram</marker> te '
            'schrijven.',
            'We raden af om in één tekst zowel <marker>organogram</marker> als <marker>organogram</marker> te '
            'schrijven.')

    def get_word_map(self):
        return self.load_word_map('/nl/coherency.txt')

    def get_message(self, word1, word2):
        return "Gebruik liever niet '" + word1 + "' en '" + word2 + "' door elkaar in een tekst."

    def get_id(self):
        return 'NL_WORD_COHERENCY'

    def get_description(self):
        return 'Consistente spelling van woorden met meerdere correcte vormen.'
