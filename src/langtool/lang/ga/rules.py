"""Irish specific rules (port of org.languagetool.rules.ga: CompoundRule,
DativePluralStandardReplaceRule (with DativePluralsData and
DativePluralsEntry), DhaNoBeirtRule (with DhaNoBeirtData),
EnglishHomophoneRule, IrishFGBEqReplaceRule, IrishReplaceRule,
IrishSpecificCaseRule, LogainmRule, PeopleRule, PrestandardReplaceRule and
SpacesRule).

The simple replace rules use Locale("GA") for case conversion, which has no
special case mapping (str.lower here)."""

import os
import threading

from ...rules.abstract_rules import AbstractCompoundRule, AbstractSimpleReplaceRule, load_compound_rule_data
from ...rules.base import RuleMatch
from ...rules.core import CoreRule
from ...tools import java_equals_ignore_case, java_split, java_trim
from . import utils


def _irish():
    """Irish.getInstance(), the language of the rules whose Java
    constructors only get the messages"""
    from ...api import get_language
    return get_language('ga')


def _rules_path(name):
    from ...resources import rules_dir
    return os.path.join(rules_dir(), 'ga', name)


def _read_lines(path):
    with open(path, encoding='utf-8') as f:
        return f.read().splitlines()


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.ga.CompoundRule: compounds (listed in
    /ga/compounds.txt) that are not written as separate words."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Litrítear an focal seo le fleiscín de ghnáth.',
                         'Litrítear an focal seo mar fhocal amháin de ghnáth.',
                         'Litrítear an nath seo mar fhocal amháin nó le fleiscín.',
                         'Fadhb leis an bhfleiscíniú')
        self.add_example_pair('Tá <marker>mí úsáid</marker> fhisiciúil i gceist.',
                              'Tá <marker>mí-úsáid</marker> fhisiciúil i gceist.')

    def get_id(self):
        return 'GA_COMPOUNDS'

    def get_description(self):
        return "Focail fhleiscínithe, e.g., Moltar 'ró-úsáid' seachas 'ró úsáid'"

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/ga/compounds.txt')


# --- DativePluralsEntry / DativePluralsData ---

class DativePluralsEntry:
    """Port of org.languagetool.rules.ga.DativePluralsEntry: a line of
    /ga/dative-plurals.txt (dative plural form, lemma, gender, nominative
    plural replacement, optionally with modern equivalents)."""

    def __init__(self, form, lemma, gender, replacement):
        self.form = form
        self.lemma = lemma
        self.gender = gender
        self.replacement = replacement
        self.modern = None
        self.lemma_modern = None
        self.equivalent = None

    def set_equivalent(self, equiv):
        self.equivalent = equiv

    def set_modernised(self, modernised):
        self.modern = modernised

    def set_modern_lemma(self, modernised):
        self.lemma_modern = modernised

    def has_equivalent(self):
        return not (self.equivalent is None or self.equivalent == '')

    def has_modernised(self):
        return not (self.modern is None or self.modern == '')

    def has_modern_lemma(self):
        return not (self.lemma_modern is None or self.lemma_modern == '')

    def get_base_tag(self):
        return 'Noun:Fem:Dat:Pl' if self.gender == 'f' else 'Noun:Masc:Dat:Pl'

    def get_standard(self):
        return self.equivalent if self.has_equivalent() else self.replacement


def _split_modern(value, what, line):
    if ':' in value:
        parts = java_split(value, ':')
        if len(parts) != 2:
            raise ValueError('%s has more than 1 modern form:%s' % (what, line))
        return parts[0], parts[1]
    return value, None


def _load_datives(path):
    """DativePluralsData.loadWords. Java collects the entries in a HashSet
    (identity hashes, i.e. no defined order); the file order is used here
    (the generated maps do not depend on it for the current data)."""
    out = []
    for line in _read_lines(path):
        line = java_trim(line)
        if not line or line[0] == '#':
            continue
        parts = java_split(line, ';')
        if len(parts) != 4:
            raise ValueError('Incorrect number of fields: ' + line)
        form, form_modern = _split_modern(parts[0], 'Form', line)
        repl, repl_modern = _split_modern(parts[3], 'Replacement', line)
        lemma, lemma_modern = _split_modern(parts[1], 'Lemma', line)
        entry = DativePluralsEntry(form, lemma, parts[2], repl)
        if form_modern is not None:
            entry.set_modernised(form_modern)
        if repl_modern is not None:
            entry.set_equivalent(repl_modern)
        if lemma_modern is not None:
            entry.set_modern_lemma(lemma_modern)
        out.append(entry)
    return out


def _add_mutated(out, form, repl, plain_repl):
    """the lenited, eclipsed and h-prefixed forms of buildSimpleReplacements
    and getModernisations"""
    lenited_form = utils.lenite(form)
    if lenited_form != form:
        out[lenited_form] = utils.lenite(repl)
    eclipsed_form = utils.eclipse(form)
    if eclipsed_form != form:
        out[eclipsed_form] = utils.eclipse(repl)
    # h-prothesis
    if utils.is_vowel(form[0]):
        out['h' + form] = 'h' + plain_repl
        out['h-' + form] = 'h' + plain_repl


def _build_simple_replacements(datives):
    out = {}
    for entry in datives:
        out[entry.form] = entry.get_standard()
        _add_mutated(out, entry.form, entry.get_standard(), entry.get_standard())
        if entry.has_modernised():
            out[entry.modern] = entry.get_standard()
            _add_mutated(out, entry.modern, entry.get_standard(), entry.get_standard())
    return out


def _get_modernisations(datives):
    """Makes a map of modernisations (i.e., if there is a more modern dative
    plural). This is only relevant to Munster Irish. Additionally generates
    mutated forms (as in Java, the lenited and eclipsed forms map to the
    mutated nominative plural replacement)."""
    out = {}
    for entry in datives:
        if entry.has_modernised():
            out[entry.form] = entry.modern
            _add_mutated(out, entry.form, entry.replacement, entry.modern)
    return out


class DativePluralsData:
    """Port of org.languagetool.rules.ga.DativePluralsData (loaded once from
    /ga/dative-plurals.txt)."""

    _data = None
    _lock = threading.Lock()

    @classmethod
    def _load(cls):
        with cls._lock:
            if cls._data is None:
                datives = _load_datives(_rules_path('dative-plurals.txt'))
                cls._data = (_get_modernisations(datives), _build_simple_replacements(datives))
            return cls._data

    @classmethod
    def get_modernisations(cls):
        return cls._load()[0]

    @classmethod
    def get_simple_replacements(cls):
        return cls._load()[1]


_dative_wrong_words = None


def _dative_plural_wrong_words():
    global _dative_wrong_words
    if _dative_wrong_words is None:
        _dative_wrong_words = {k: [v] for k, v in DativePluralsData.get_simple_replacements().items()}
    return _dative_wrong_words


class DativePluralStandardReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.DativePluralStandardReplaceRule:
    pre-standard dative plurals (DativePluralsData), case sensitive."""

    category_id = 'TYPOS'
    issue_type = 'Grammar'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('Dá mba thruamhéalach é cás an sclábhaí fir, ba mheasa fós do na <marker>mnáibh</marker> '
                              'a gcás siúd.',
                              'Dá mba thruamhéalach é cás an sclábhaí fir, ba mheasa fós do na <marker>mná</marker> '
                              'a gcás siúd.')
        self.check_lemmas = False

    def get_wrong_words(self):
        return _dative_plural_wrong_words()

    def get_id(self):
        return 'GA_DATIVE_PLURALS_STD'

    def get_description(self):
        return 'Tuiseal tabharthach iolra'

    def get_short(self):
        return 'Tabharthach iolra'

    def get_message(self, token_str, replacements):
        return 'Is litriú réamhchaighdeánach (tabharthach iolra) é "' + token_str + '"; an "' + \
            ', '.join(replacements) + '" a bhí i gceist agat?'


# --- DhaNoBeirtData / DhaNoBeirtRule ---

class DhaNoBeirtData:
    """Port of org.languagetool.rules.ga.DhaNoBeirtData: the words for
    people (/ga/people.txt) and the personal numbers."""

    _daoine = None
    _lock = threading.Lock()
    _numbers = {'dhá': 'beirt', 'trí': 'triúr', 'ceathair': 'ceathrar', 'cúig': 'cúigear', 'sé': 'seisear',
                'seacht': 'seachtar', 'ocht': 'ochtar', 'naoi': 'naonúr', 'deich': 'deichniúr'}

    @classmethod
    def get_daoine(cls):
        with cls._lock:
            if cls._daoine is None:
                cls._daoine = frozenset(cls._load_words(_rules_path('people.txt')))
            return cls._daoine

    @classmethod
    def get_number_replacements(cls):
        return cls._numbers

    @staticmethod
    def _load_words(path):
        """Load words, normalized to lowercase unless starting with '*'."""
        out = set()
        for line in _read_lines(path):
            line = java_trim(line)
            if not line or line[0] == '#':
                continue
            if line[0] == '*':
                out.add(line[1:])
            else:
                out.add(line.lower())
        return out


class DhaNoBeirtRule(CoreRule):
    """Port of org.languagetool.rules.ga.DhaNoBeirtRule: personal numbers
    ('beirt' instead of 'dhá' etc.) before words for people."""

    category_id = 'MISC'
    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Tá <marker>dhá</marker> dheartháireacha agam.',
                              'Tá <marker>beirt</marker> dheartháireacha agam.')

    def get_id(self):
        return 'GA_DHA_NO_BEIRT'

    def get_description(self):
        return "'dhá' nó 'beirt'"

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        mark_deag = 1
        prev_token_index = 0
        replacement = None
        msg = None
        for i in range(1, n):  # ignoring token 0, i.e., SENT_START
            if self._is_number(tokens[i]) and (i < n - 2 and self._is_person(tokens[i + 1])):
                if java_equals_ignore_case('dhá', tokens[i].token) and i < n - 2:
                    for j in range(i + 2, n):
                        if java_equals_ignore_case('déag', tokens[j].token):
                            mark_deag = j
                            replacement = 'dháréag'
                            msg = 'Ba chóir duit <suggestion>' + replacement + '</suggestion> a scríobh'
                            tok = tokens[prev_token_index + 1]
                            rule_matches.append(RuleMatch(self, sentence, tok.start_pos, tok.end_pos, msg,
                                                          'Uimhir phearsanta'))
                            msg = 'Ba chóir duit "déag" a scriosadh.'
                            tok = tokens[mark_deag]
                            rule_matches.append(RuleMatch(self, sentence, tok.start_pos, tok.end_pos, msg,
                                                          'Uimhir phearsanta'))
                            msg = None
                if replacement is None:
                    replacement = DhaNoBeirtData.get_number_replacements().get(tokens[i].token)
                    if msg is None:
                        # Java string concatenation of a null replacement gives "null"
                        msg = 'Ba chóir duit <suggestion>' + ('null' if replacement is None else replacement) + \
                            ' ' + tokens[i + 1].token + '</suggestion> a scríobh'
            if msg is not None:
                tok = tokens[prev_token_index + 1]
                rule_matches.append(RuleMatch(self, sentence, tok.start_pos, tok.end_pos, msg, 'Uimhir phearsanta'))
                msg = None
            prev_token_index = i
        return rule_matches

    @staticmethod
    def _is_number(tok):
        return any(java_equals_ignore_case(num, tok.token) for num in DhaNoBeirtData.get_number_replacements())

    @staticmethod
    def _is_person(tok):
        daoine = DhaNoBeirtData.get_daoine()
        if tok.token.lower() in daoine:
            return True
        return any(reading.lemma in daoine for reading in tok.readings)


# --- the simple replace rules ---

class _IrishSimpleReplaceRule(AbstractSimpleReplaceRule):
    """the common parts of the Irish AbstractSimpleReplaceRule subclasses:
    category TYPOS, Misspelling, case insensitive, no lemma checks"""

    category_id = 'TYPOS'
    issue_type = 'Misspelling'
    file_name = None

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.check_lemmas = False

    def get_wrong_words(self):
        return self.load_from_path('/ga/' + self.file_name)

    def is_case_sensitive(self):
        return False


class EnglishHomophoneRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.EnglishHomophoneRule: English words
    written instead of their Irish homophones (/ga/english-homophones.txt)."""

    file_name = 'english-homophones.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('An bhialann <marker>sushi</marker> sin ba chúis leis.',
                              'An bhialann <marker>súisí</marker> sin ba chúis leis.')

    def get_id(self):
        return 'GA_ENGLISH_HOMOPHONE'

    def get_description(self):
        return 'Is homafóin iad na focail, m.sh., "well" agus "bhuel"'

    def get_short(self):
        return 'Homafón Béarla.'

    def get_message(self, token_str, replacements):
        return 'Is é ' + ', '.join(replacements) + ' an litriú Gaelach ar "' + token_str + '"'


class IrishFGBEqReplaceRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.IrishFGBEqReplaceRule: uncommon
    headwords of the FGB dictionary (/ga/replace-fgb-eq.txt)."""

    file_name = 'replace-fgb-eq.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('An bhfuil tú <marker>urlamh</marker>?', 'An bhfuil tú <marker>ullamh</marker>?')

    def get_id(self):
        return 'GA_FGB_EQ_REPLACE'

    def get_description(self):
        return 'Ceannfhocal FGB neamhchoitianta, m.sh., "urlamh" in áit "ullamh"'

    def get_short(self):
        return 'Neamhchoitianta'

    def get_message(self, token_str, replacements):
        return 'Focal ceart ach tá "' + ', '.join(replacements) + '" níos coitianta.'


class IrishReplaceRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.IrishReplaceRule: misspellings
    (/ga/replace.txt)."""

    file_name = 'replace.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('Níl beann agam oraibh, ar <marker>bhúr</marker> gcuid cainte.',
                              'Níl beann agam oraibh, ar <marker>bhur</marker> gcuid cainte.')

    def get_id(self):
        return 'GA_REPLACE'

    def get_description(self):
        return 'Litriú mícheart, m.sh., "agsu" in áit "agus"'

    def get_short(self):
        return 'Litriú mícheart'

    def get_message(self, token_str, replacements):
        return 'Litriú mícheart: "' + ', '.join(replacements) + '".'


class LogainmRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.LogainmRule: English place names
    (/ga/placenames.txt), tagged words are ignored."""

    file_name = 'placenames.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.set_ignore_tagged_words()
        self.url = 'https://www.logainm.ie/ga/'

    def get_id(self):
        return 'GA_LOGAINM'

    def get_description(self):
        return "Logainm Béarla, m.sh., 'Dublin' in áit 'Baile Átha Cliath'."

    def get_short(self):
        return 'Logainm Béarla'

    def get_message(self, token_str, replacements):
        return 'Is logainm Béarla é "' + token_str + '" ar "' + ', '.join(replacements) + '".'


class PeopleRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.PeopleRule: English forms of names
    (/ga/names.txt)."""

    file_name = 'names.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('Bhí sí cosúil le claíomh <marker>Damocles</marker> ar crochadh sa spéir.',
                              'Bhí sí cosúil le claíomh <marker>Dámaicléas</marker> ar crochadh sa spéir.')

    def get_id(self):
        return 'GA_PEOPLE'

    def get_description(self):
        return "Ainm Béarla, m.sh., 'Damocles' in áit 'Dámaicléas'."

    def get_short(self):
        return 'Ainm Béarla'

    def get_message(self, token_str, replacements):
        return 'Ainm Béarla. "' + ', '.join(replacements) + '".'


class PrestandardReplaceRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.PrestandardReplaceRule: pre-standard
    spellings (/ga/replace-prestandard.txt)."""

    file_name = 'replace-prestandard.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('“Ní <marker>baoghal</marker> daoibh,” ar sise.',
                              '“Ní <marker>baol</marker> daoibh,” ar sise.')

    def get_id(self):
        return 'GA_PRESTANDARD_REPLACE'

    def get_description(self):
        return 'Litriú réamhchaighdeánach, m.sh., "baoghal" in áit "baol"'

    def get_short(self):
        return 'Litriú réamhchaighdeánach'

    def get_message(self, token_str, replacements):
        return 'Litriú réamhchaighdeánach:"' + ', '.join(replacements) + '".'


class SpacesRule(_IrishSimpleReplaceRule):
    """Port of org.languagetool.rules.ga.SpacesRule: missing spaces
    (/ga/spaces.txt), tagged words are ignored."""

    file_name = 'spaces.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.set_ignore_tagged_words()

    def get_id(self):
        return 'GA_SPASANNA'

    def get_description(self):
        return 'Spás ar iarraidh'

    def get_short(self):
        return 'Spás ar iarraidh'

    def get_message(self, token_str, replacements):
        return 'Spás ar iarraidh: "' + ', '.join(replacements) + '".'


# --- IrishSpecificCaseRule ---

_phrases = None
_phrases_lock = threading.Lock()


def _specific_case_data(language):
    """(maxLen, lcToProperSpelling) of IrishSpecificCaseRule, loaded from
    /ga/specific_case.txt (the lowercase forms of the phrases are unique, so
    the order of the Java HashSet does not matter)"""
    global _phrases
    with _phrases_lock:
        if _phrases is None:
            max_len = 0
            phrases = []
            for line in _read_lines(os.path.join(language.resource_dir, 'specific_case.txt')):
                if not line or line.startswith('#'):
                    continue
                max_len = max(len(java_split(line, ' ')), max_len)
                phrases.append(java_trim(line))
            lc_to_proper_spelling = {}
            for phrase in dict.fromkeys(phrases):
                lc_to_proper_spelling[phrase.lower()] = phrase
            _phrases = (max_len, lc_to_proper_spelling)
        return _phrases


class IrishSpecificCaseRule(CoreRule):
    """Port of org.languagetool.rules.ga.IrishSpecificCaseRule: phrases of
    /ga/specific_case.txt that need a specific upper/lowercase spelling
    (with the Irish case functions of Utils)."""

    category_id = 'CASING'
    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _irish())
        self.add_example_pair('Rugadh agus tógadh i <marker>mbéal Feirste</marker> é.',
                              'Rugadh agus tógadh i <marker>mBéal Feirste</marker> é.')

    def get_id(self):
        return 'GA_SPECIFIC_CASE'

    def get_description(self):
        return 'Checks upper/lower case spelling of some proper nouns'

    def match(self, sentence):
        max_len, lc_to_proper_spelling = _specific_case_data(self.language)
        matches = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        for i in range(n):
            words = []
            j = 0
            while len(words) < max_len and i + j < n:
                words.append(tokens[i + j].token)
                j += 1
                phrase = ' '.join(words)
                proper_spelling = lc_to_proper_spelling.get(phrase.lower())
                if proper_spelling is not None and not utils.is_all_uppercase(phrase) and phrase != proper_spelling:
                    if i > 0 and tokens[i - 1].is_sentence_start and not utils.starts_with_uppercase(proper_spelling):
                        # avoid suggesting e.g. "vitamin C" at sentence start:
                        continue
                    if self._all_words_uppercase(proper_spelling):
                        msg = 'Más ainmfhocal dílis é, scríobh é i gceannlitreacha.'
                    else:
                        msg = 'If the term is a proper noun, use the suggested capitalization.'
                    match = RuleMatch(self, sentence, tokens[i].start_pos, tokens[i].start_pos + len(phrase), msg)
                    match.set_suggested_replacement(proper_spelling)
                    matches.append(match)
        return matches

    @staticmethod
    def _all_words_uppercase(s):
        return all(utils.starts_with_uppercase(w) for w in java_split(s, ' '))
