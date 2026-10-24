"""Catalan replacement, case, coherency and confusion rules (port of the
rules of org.languagetool.rules.ca): AbstractSimpleReplaceLemmasRule,
SimpleReplaceVerbsRule, SimpleReplaceBalearicRule, SimpleReplaceRule,
SimpleReplaceMultiwordsRule, ReplaceOperationNamesRule,
SimpleReplaceDiacriticsIEC, SimpleReplaceAnglicism, SimpleReplaceAdverbsMent,
SimpleReplaceDNVRule, SimpleReplaceDNVColloquialRule,
SimpleReplaceDNVSecondaryRule, CheckCaseRule, CatalanWrongWordInContextRule,
WordCoherencyRule and WordCoherencyValencianRule.

The Java rules lowercase with new Locale("CA") (language "ca"), which has no
special case mapping (str.lower here). The rules whose Java constructors only
get the messages use Catalan.getInstance() (ca-ES)."""

import threading

from ... import jregex
from ...analysis import AnalyzedToken, PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME, SENTENCE_START_TAGNAME
from ...rules.abstract_rules import (AbstractCheckCaseRule, AbstractSimpleReplaceRule, AbstractSimpleReplaceRule2,
                                     AbstractWordCoherencyRule, WrongWordInContextRule)
from ...rules.base import Category
from ...rules.core import Categories
from ...tools import is_capitalized_word, java_equals_ignore_case
from .synthesis import P_VERB

FILTERS = ()


def _catalan():
    """Catalan.getInstance() (ca-ES)"""
    from ...api import get_language
    return get_language('ca-ES')


def _is_underlined_error_single_token(rule_match):
    """RuleMatch.isUnderlinedErrorSingleToken: the sentence positions of the
    match cover only one token of the sentence (whitespace tokens included)"""
    from_char = rule_match.get_from_pos_sentence()
    to_char = rule_match.get_to_pos_sentence()
    from_token = to_token = -1
    for i, t in enumerate(rule_match.sentence.tokens):
        token_start = t.start_pos
        token_end = token_start + len(t.token)
        if from_token == -1 and token_end > from_char:
            from_token = i
        if token_start < to_char:
            to_token = i
        else:
            break
    if from_token == -1 or to_token == -1:
        raise ValueError('No tokens found for sentencePosition [%d, %d]' % (from_char, to_char))
    return from_token == to_token


def _convert_to_gender_and_number(rule, potential_matches, check_single_token):
    """Adjust determinants and adjectives of the suggestions with a
    ConvertToGenderAndNumberFilter (lemmaSelect: [NA].*)"""
    from .verb_filters import ConvertToGenderAndNumberFilter
    rule_filter = ConvertToGenderAndNumberFilter(rule.language)
    rule_matches = []
    for potential_rule_match in potential_matches:
        # For multi-word expressions, skip the filter: it cannot adjust gender/number
        # reliably across tokens and causes incorrect position adjustments.
        if check_single_token and not _is_underlined_error_single_token(potential_rule_match):
            rule_matches.append(potential_rule_match)
            continue
        final_match = rule_filter.accept_rule_match(potential_rule_match, {'lemmaSelect': '[NA].*'}, 0, None, None)
        if final_match is not None:
            rule_matches.append(final_match)
    return rule_matches


class _LazyWords:
    """The words of a replacement file, loaded once (a static field in Java)"""

    def __init__(self, *paths):
        self.paths = paths
        self.words = None
        self.lock = threading.Lock()

    def get(self, rule):
        if self.words is None:
            with self.lock:
                if self.words is None:
                    self.words = rule.load_from_path(*self.paths)
        return self.words


_POS_GENDER_S = jregex.compile('[MFC]S')
_POS_GENDER_P = jregex.compile('[MFC]P')


class AbstractSimpleReplaceLemmasRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.AbstractSimpleReplaceLemmasRule:
    words whose lemma is in the replacement data (wrong_lemmas, set by the
    subclasses); the suggestions are the replacement lemmas synthesized with
    the POS tag of the word (or with any gender, or the lemmas themselves),
    case insensitive."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.wrong_lemmas = None
        self.synth = language.synthesizer

    def get_wrong_words(self):
        return self.wrong_lemmas

    def is_case_sensitive(self):
        return False

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.non_blank_tokens
        original_lemma = None
        for i in range(1, len(tokens)):
            replacement_lemmas = None
            replace_pos_tag = None
            b_rule_matches = False
            token_readings = tokens[i]
            if (token_readings.readings[0].pos_tag == SENTENCE_START_TAGNAME
                    or token_readings.immunized  # this rule is used mostly for spelling, so ignore both immunized
                    or token_readings.ignored_by_speller  # and speller-ignorable rules
                    or self.is_token_exception(token_readings)
                    or (self.ignore_tagged_words and self.is_tagged(token_readings))):
                continue
            wrong_words = self.get_wrong_words()
            for at in token_readings.readings:
                is_end_tag = (at.pos_tag is not None and at.pos_tag == SENTENCE_END_TAGNAME
                              and at.pos_tag != PARAGRAPH_END_TAGNAME)
                if not is_end_tag and at.lemma in wrong_words:
                    replacement_lemmas = wrong_words[at.lemma]
                    replace_pos_tag = at.pos_tag
                    b_rule_matches = True
                    original_lemma = at.lemma
                    break
            # find suggestions
            possible_replacements = []
            if replacement_lemmas is not None and replace_pos_tag is not None:
                # synthesize replacements
                for replacement_lemma in replacement_lemmas:
                    synthesized = self.synth.synthesize(
                        AnalyzedToken(replacement_lemma, replace_pos_tag, replacement_lemma), replace_pos_tag) or []
                    # try with another gender
                    if not synthesized:
                        replace_pos_tag2 = jregex.java_replace(_POS_GENDER_S, '.S', replace_pos_tag)
                        replace_pos_tag2 = jregex.java_replace(_POS_GENDER_P, '.P', replace_pos_tag2)
                        synthesized = self.synth.synthesize(
                            AnalyzedToken(replacement_lemma, replace_pos_tag, replacement_lemma),
                            replace_pos_tag2) or []
                    # add the suggestion without inflection
                    if not synthesized and len(replacement_lemma) > 1:
                        possible_replacements.append(replacement_lemma)
                    else:
                        possible_replacements.extend(synthesized)
            if b_rule_matches:
                rule_matches.append(self.create_rule_match(tokens[i], possible_replacements, sentence,
                                                           original_lemma))
        return rule_matches


class SimpleReplaceVerbsRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceVerbsRule: incorrect
    verbs (all inflected forms, tagged by the CatalanTagger with the chunk
    tag _incorrect_verb_; listed by their infinitive in
    /ca/replace_verbs.txt); the suggestions are the replacement infinitives
    adapted by the AdjustVerbSuggestionsFilter (actions: None).

    (In Java createRuleMatch capitalizes the replacements of the static
    word map in place for capitalized words, which changes the suggestions
    of later matches; the shared data is not modified here.)"""

    issue_type = 'Grammar'
    _words = _LazyWords('/ca/replace_verbs.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.set_ignore_tagged_words()
        self.synth = language.synthesizer
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self._words.get(self)

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_VERBS'

    def get_description(self):
        return 'Verb incorrecte: $match'

    def get_short(self):
        return 'Verb incorrecte'

    def get_message(self, token_str, replacements):
        return 'Verb incorrecte.'

    def match(self, sentence):
        from .verb_filters import AdjustVerbSuggestionsFilter
        rule_matches = []
        tokens = sentence.non_blank_tokens
        wrong_words = self.get_wrong_words()
        for index in range(1, len(tokens)):
            t = tokens[index]
            if (not any(c.chunk_tag == '_incorrect_verb_' for c in t.chunk_tags)
                    or t.has_pos_tag_starting_with('N') or t.has_pos_tag_starting_with('A')):
                continue
            # synthesize replacements
            at = t.reading_with_tag_regex(P_VERB)
            if at is None:
                continue
            replacement_infinitives = wrong_words.get(at.lemma)
            if replacement_infinitives is None:
                continue
            potential_rule_match = self.create_rule_match(t, list(replacement_infinitives), sentence, at.lemma)
            rule_filter = AdjustVerbSuggestionsFilter(self.language)
            final_match = rule_filter.accept_rule_match(potential_rule_match, {'actions': 'None'}, 0, None, None)
            if final_match is not None:
                rule_matches.append(final_match)
        return rule_matches


class SimpleReplaceBalearicRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceBalearicRule: verb
    forms of the Balearic variety (/ca/replace_balearic.txt), case
    insensitive, lemmas are not checked; proper nouns, immunized tokens,
    tokens ignored by the speller, _english_ignore_ and _Latin_ are
    exceptions."""

    issue_type = 'Grammar'
    _words = _LazyWords('/ca/replace_balearic.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.check_lemmas = False
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self._words.get(self)

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_BALEARIC'

    def get_description(self):
        return 'Suggeriments per a formes balears: $match'

    def get_short(self):
        return 'Possible error ortogràfic.'

    def get_message(self, token_str, replacements):
        return 'Possible error ortogràfic (forma verbal vàlida en la varietat balear).'

    def is_case_sensitive(self):
        return False

    def is_token_exception(self, atr):
        # proper nouns tagged in multiwords are exceptions
        return (atr.has_pos_tag_starting_with('NP') or atr.immunized or atr.ignored_by_speller
                or atr.has_pos_tag('_english_ignore_') or atr.has_pos_tag('_Latin_'))


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceRule: words of
    /ca/replace.txt and /ca/replace_custom.txt that should not be used, case
    insensitive; tagged words and lemmas are not checked. The determiners
    and adjectives around the word are adapted to the gender and number of
    the suggestions (ConvertToGenderAndNumberFilter), except when a
    suggestion is "perquè", "què" or "per què"."""

    issue_type = 'Grammar'
    _words = _LazyWords('/ca/replace.txt', '/ca/replace_custom.txt')
    _EXCEPTIONS = frozenset(('perquè', 'què', 'per què'))

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.set_ignore_tagged_words()
        self.check_lemmas = False
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self._words.get(self)

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_SIMPLE'

    def get_description(self):
        return 'Paraula incorrecta: $match'

    def get_short(self):
        return 'Paraula incorrecta'

    def get_message(self, token_str, replacements):
        if replacements:
            return '¿Volíeu dir «' + replacements[0] + '»?'
        return self.get_short()

    def match(self, sentence):
        from .verb_filters import ConvertToGenderAndNumberFilter
        potential_matches = super().match(sentence)
        rule_filter = ConvertToGenderAndNumberFilter(self.language)
        rule_matches = []
        # Adjust determinants and adjectives
        for potential_rule_match in potential_matches:
            if any(s.lower() in self._EXCEPTIONS for s in potential_rule_match.suggested_replacements):
                rule_matches.append(potential_rule_match)
                continue
            final_match = rule_filter.accept_rule_match(potential_rule_match, {'lemmaSelect': '[NA].*'}, 0, None,
                                                        None)
            if final_match is not None:
                rule_matches.append(final_match)
        return rule_matches

    def is_case_sensitive(self):
        return False


class SimpleReplaceMultiwordsRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.ca.SimpleReplaceMultiwordsRule:
    inadequate expressions of /ca/replace_multiwords.txt (for
    Catalan.getInstance())."""

    issue_type = 'Grammar'

    def __init__(self, messages, language=None):
        super().__init__(messages, _catalan())
        self.category = Categories.get('GRAMMAR', messages)
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_MULTIWORDS'

    def get_description(self):
        return 'Expressions inadequades: $match'

    def get_short(self):
        return 'Expressió inadequada'

    def get_file_names(self):
        return ['/ca/replace_multiwords.txt']

    def get_message(self):
        return 'Expressió incorrecta.'


_PREV_TOKEN_POS = jregex.compile('D[^R].*|PX.*|SPS00|SENT_START')
_PREV_TOKEN_POS_EXCEP = jregex.compile('RG_anteposat|N.*|CC|_PUNCT.*|_loc_unavegada|RN')
_NEXT_TOKEN_POS_EXCEP = jregex.compile('N.*')
_PUNTUACIO = jregex.compile('PUNCT.*|SENT_START')
_DETERMINANT = jregex.compile('D[^R].M.*')


def _match_postag_regexp(atr, pattern):
    """Match POS tag with regular expression (unknown words: "UNKNOWN")"""
    for reading in atr:
        pos_tag = reading.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if pattern.fullmatch(pos_tag):
            return True
    return False


class ReplaceOperationNamesRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.ReplaceOperationNamesRule:
    participles used as names of technical operations (/ca/replace_operationnames.txt,
    "el filtrat" -> "la filtració"), after a determiner, possessive or
    preposition; plural forms get plural suggestions. The determiners and
    adjectives are adapted to the suggestions (ConvertToGenderAndNumberFilter)
    for one-token matches."""

    issue_type = 'Style'
    _words = _LazyWords('/ca/replace_operationnames.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Category('FORMES_SECUNDARIES', 'C8) Formes secundàries')
        self.synth = language.synthesizer
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self._words.get(self)

    def get_id(self):
        return 'NOMS_OPERACIONS'

    def get_description(self):
        return "S'ha d'evitar com a nom d'operació tècnica: $match"

    def get_short(self):
        return 'Forma preferible'

    def get_message(self, token_str, replacements):
        return "Si és el nom d'una operació tècnica, val més usar una altra forma."

    def is_case_sensitive(self):
        return False

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        wrong_words = self.get_wrong_words()
        for i in range(1, n):
            token = tokens[i].token.lower()
            if len(token) > 3 and token.endswith('s'):
                token = token[:-1]
            replacement_lemmas = wrong_words.get(token)
            if replacement_lemmas is None:
                continue
            # exceptions
            if token == 'duplicat' and java_equals_ignore_case(tokens[i - 1].token, 'per'):
                continue
            # el polit Potos
            if i + 1 < n and java_equals_ignore_case(token, 'polit') and is_capitalized_word(tokens[i + 1].token):
                continue
            # Assecat el braç del riu
            if (i + 1 < n and _match_postag_regexp(tokens[i - 1], _PUNTUACIO)
                    and _match_postag_regexp(tokens[i + 1], _DETERMINANT)):
                continue
            # relevant token
            if tokens[i].has_pos_tag('_GV_'):
                continue
            # next token
            if i + 1 < n:
                nxt = tokens[i + 1]
                if (nxt.has_lemma('per') or nxt.has_lemma('com') or nxt.has_lemma('des') or nxt.has_lemma('amb')
                        or _match_postag_regexp(nxt, _NEXT_TOKEN_POS_EXCEP)):
                    continue
            # prev token
            if (not _match_postag_regexp(tokens[i - 1], _PREV_TOKEN_POS)
                    or _match_postag_regexp(tokens[i - 1], _PREV_TOKEN_POS_EXCEP)):
                continue
            # The rule matches!
            # synthesize replacements
            possible_replacements = []
            if not tokens[i].token.lower().endswith('s'):
                possible_replacements.extend(replacement_lemmas)
            else:
                # synthesize plural
                for replacement_lemma in replacement_lemmas:
                    possible_replacements.extend(self.synth.synthesize(
                        AnalyzedToken(replacement_lemma, 'NCMS000', replacement_lemma), 'NC.P.*') or [])
            if possible_replacements:
                rule_matches.append(self.create_rule_match(tokens[i], possible_replacements, sentence, token))
        return _convert_to_gender_and_number(self, rule_matches, True)


class SimpleReplaceDiacriticsIEC(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceDiacriticsIEC:
    diacritic accents removed by the new norms of the IEC (2017)
    (/ca/replace_diacritics_iec.txt), case insensitive, lemmas are not
    checked, proper nouns are exceptions."""

    issue_type = 'Grammar'
    _words = _LazyWords('/ca/replace_diacritics_iec.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Category('DIACRITICS_IEC', "Z) Accents diacrítics segons l'IEC")
        self.set_default_on()
        self.check_lemmas = False
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self._words.get(self)

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_DIACRITICS_IEC'

    def get_description(self):
        return 'Accents diacrítics segons les normes noves (2017): $match'

    def get_short(self):
        return "Hi sobra l'accent."

    def get_message(self, token_str, replacements):
        return "Hi sobra l'accent diacrític (segons les normes noves)."

    def is_case_sensitive(self):
        return False

    def is_token_exception(self, atr):
        return atr.has_pos_tag_starting_with('NP')


class SimpleReplaceAnglicism(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.ca.SimpleReplaceAnglicism:
    unnecessary anglicisms (/ca/replace_anglicism.txt, for
    Catalan.getInstance()). For one-token matches the determiners and
    adjectives are adapted to the suggestions
    (ConvertToGenderAndNumberFilter). English words in English contexts
    (_english_ignore_ before or after) and proper nouns are exceptions."""

    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, _catalan())
        self.category = Categories.get('STYLE', messages)
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_ANGLICISM'

    def get_description(self):
        return 'Anglicismes innecessaris: $match'

    def get_short(self):
        return 'Anglicisme innecessari'

    def get_file_names(self):
        return ['/ca/replace_anglicism.txt']

    def get_message(self):
        return 'Anglicisme innecessari. Considereu fer servir una altra paraula.'

    def match(self, sentence):
        return _convert_to_gender_and_number(self, super().match(sentence), True)

    def is_rule_match_exception(self, rule_match):
        # accept English words in English sentences
        start_index = 0
        tokens = rule_match.sentence.non_blank_tokens
        while start_index < len(tokens) and tokens[start_index].start_pos < rule_match.from_pos:
            start_index += 1
        end_index = start_index
        while end_index < len(tokens) and tokens[end_index].end_pos < rule_match.to_pos:
            end_index += 1
        if (start_index > 1 and tokens[start_index].has_pos_tag('_english_ignore_')
                and tokens[start_index - 1].has_pos_tag('_english_ignore_')):
            return True
        if (end_index + 1 < len(tokens) and tokens[end_index].has_pos_tag('_english_ignore_')
                and tokens[end_index + 1].has_pos_tag('_english_ignore_')):
            return True
        return False

    def is_token_exception(self, atr):
        # proper nouns tagged in multiwords are exceptions
        return ((atr.has_pos_tag_starting_with('NP') and len(atr.token) > 1) or atr.immunized
                or atr.ignored_by_speller)


class SimpleReplaceAdverbsMent(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceAdverbsMent:
    alternatives to adverbs ending in -ment (/ca/replace_adverbs_ment.txt,
    for Catalan.getInstance()), off by default, picky."""

    issue_type = 'Style'
    _words = _LazyWords('/ca/replace_adverbs_ment.txt')

    def __init__(self, messages, language=None):
        super().__init__(messages, _catalan())
        self.category = Category('PICKY_STYLE', "regles d'estil, mode perfeccionaista")
        self.set_default_off()
        self.check_lemmas = False
        self.tags = ['picky']
        self.url = 'https://esadir.cat/gramatica/sintaxi/advermanera'

    def get_wrong_words(self):
        return self._words.get(self)

    def get_id(self):
        return 'ADVERBIS_MENT'

    def get_description(self):
        return 'Alternatives a adverbis acabats en -ment: $match'

    def get_short(self):
        return 'Alternatives a adverbis acabats en -ment'

    def get_message(self, token_str, replacements):
        return "A vegades s'abusa dels adverbis acabats en -ment en detriment de formes més àgils."

    def is_case_sensitive(self):
        return False


class SimpleReplaceDNVRule(AbstractSimpleReplaceLemmasRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceDNVRule: words admitted
    only by the DNV of the AVL (lemmas of /ca/replace_dnv.txt)."""

    issue_type = 'Style'
    _words = _LazyWords('/ca/replace_dnv.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REGIONALISMS', messages)
        self.use_sub_rule_specific_ids()
        self.wrong_lemmas = self._words.get(self)

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_DNV'

    def get_description(self):
        return "Detecta paraules admeses només per l'AVL i proposa suggeriments de canvi"

    def get_short(self):
        return 'Paraula admesa només pel DNV (AVL).'

    def get_message(self, token_str, replacements):
        return 'Paraula admesa pel DNV (AVL), però no per altres diccionaris.'


class SimpleReplaceDNVColloquialRule(AbstractSimpleReplaceLemmasRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceDNVColloquialRule:
    words marked as colloquial in the DNV (lemmas of
    /ca/replace_dnv_colloquial.txt)."""

    issue_type = 'Style'
    _words = _LazyWords('/ca/replace_dnv_colloquial.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.wrong_lemmas = self._words.get(self)
        self.category = Categories.get('COLLOQUIALISMS', messages)
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_DNV_COLLOQUIAL'

    def get_description(self):
        return 'Detecta paraules marcades com a col·loquials en el DNV.'

    def get_short(self):
        return 'Paraula o expressió col·loquial.'

    def get_message(self, token_str, replacements):
        return 'Paraula o expressió col·loquial.'


class SimpleReplaceDNVSecondaryRule(AbstractSimpleReplaceLemmasRule):
    """Port of org.languagetool.rules.ca.SimpleReplaceDNVSecondaryRule:
    secondary forms (lemmas of /ca/replace_dnv_secondary.txt);
    _english_ignore_ tokens are exceptions."""

    issue_type = 'Style'
    _words = _LazyWords('/ca/replace_dnv_secondary.txt')

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REGIONALISMS', messages)
        self.use_sub_rule_specific_ids()
        self.wrong_lemmas = self._words.get(self)

    def get_id(self):
        return 'CA_SIMPLE_REPLACE_DNV_SECONDARY'

    def get_description(self):
        return 'Recomana paraules o formes preferents.'

    def get_short(self):
        return 'Forma secundària'

    def get_message(self, token_str, replacements):
        return 'Paraula o forma secundària.'

    def is_token_exception(self, atr):
        return atr.has_pos_tag('_english_ignore_')


class CheckCaseRule(AbstractCheckCaseRule):
    """Port of org.languagetool.rules.ca.CheckCaseRule: the case of the
    phrases of /ca/check_case.txt. (The message can be changed in Java
    with the system property lt.ca.checkcase.message; the default message
    is used here.)"""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.use_sub_rule_specific_ids()

    def get_file_names(self):
        return ['/ca/check_case.txt']

    def get_id(self):
        return 'CA_CHECKCASE'

    def get_description(self):
        return 'Comprova majúscules i minúscules: $match'

    def get_short(self):
        return 'Majúscules i minúscules'

    def get_message(self):
        return ("Majúscules i minúscules recomanades. Alguns llibres d'estil poden suggerir solucions diferents en "
                'alguns casos.')


class CatalanWrongWordInContextRule(WrongWordInContextRule):
    """Port of org.languagetool.rules.ca.CatalanWrongWordInContextRule:
    confusions according to the context (/ca/wrongWordInContext.txt), the
    context words are matched against the lemmas."""

    issue_type = 'Grammar'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.loc_quality_issue_type = 'Grammar'
        self.set_match_lemmas()

    def get_category_string(self):
        return 'Z) Confusions'

    def get_id(self):
        return 'CATALAN_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'Confusió segons el context: $match'

    def get_filename(self):
        return '/ca/wrongWordInContext.txt'

    def get_message_string(self):
        return '¿Volíeu dir <suggestion>$SUGGESTION</suggestion> en lloc de "$WRONGWORD"?'

    def get_short_message_string(self):
        return 'Possible confusió'

    def get_long_message_string(self):
        return ('¿Volíeu dir <suggestion>$SUGGESTION</suggestion> ($EXPLANATION_SUGGESTION) en lloc de '
                '"$WRONGWORD" ($EXPLANATION_WRONGWORD)?')


_ALLOWED_POSTAGS = jregex.compile('[VAND].*')


class _CatalanWordCoherencyRule(AbstractWordCoherencyRule):
    """The common code of WordCoherencyRule and WordCoherencyValencianRule:
    the replacement is synthesized (with the synthesizer of
    Languages.getLanguageForShortCode("ca"), i.e. ca-ES) with the POS tag of
    a verb, adjective, noun or determiner reading of the token."""

    _path = None

    def __init__(self, messages, language=None):
        super().__init__(messages, language if language is not None else _catalan())
        self.category = Categories.get('STYLE', messages)
        self.synth = _catalan().synthesizer

    def get_word_map(self):
        return self.load_word_map(self._path)

    def get_message(self, word1, word2):
        return "No és coherent usar '" + word1 + "' i '" + word2 + "' dins d'un mateix text."

    def get_short_message(self):
        return 'Coherència'

    def get_description(self):
        return "Detecta l'ús incoherent de diferents formes dins d'un text."

    def create_replacement(self, marked, token, other_spelling, atr):
        reading = atr.reading_with_tag_regex(_ALLOWED_POSTAGS)
        if reading is not None:
            synthesized_forms = self.synth.synthesize(AnalyzedToken('', '', other_spelling), reading.pos_tag)
            if synthesized_forms:
                return synthesized_forms[0]
        return super().create_replacement(marked, token, other_spelling, atr)


class WordCoherencyRule(_CatalanWordCoherencyRule):
    """Port of org.languagetool.rules.ca.WordCoherencyRule: coherent use of
    variant forms (/ca/coherency.txt)."""

    _path = '/ca/coherency.txt'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Un <marker>pesebre</marker> ací i un altre <marker>pessebre</marker> allà.',
                              'Un <marker>pesebre</marker> ací i un altre <marker>pesebre</marker> allà.')

    def get_id(self):
        return 'CA_WORD_COHERENCY'


class WordCoherencyValencianRule(_CatalanWordCoherencyRule):
    """Port of org.languagetool.rules.ca.WordCoherencyValencianRule: coherent
    use of variant forms in Valencian (/ca/coherency-valencia.txt)."""

    _path = '/ca/coherency-valencia.txt'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair("<marker>Este</marker> home d'ací parla amb <marker>aquest</marker> altre ací.",
                              "<marker>Este</marker> home d'ací parla amb <marker>este</marker> altre ací.")

    def get_id(self):
        return 'CA_WORD_COHERENCY_VALENCIA'


def _with_language(cls):
    """factory for the rules with the Java constructor (messages, language)"""
    return lambda messages, language, user_config, **kwargs: cls(messages, language)


def _messages_only(cls):
    """factory for the rules with the Java constructor (messages)"""
    return lambda messages, language, user_config, **kwargs: cls(messages)


RULES = {
    'SimpleReplaceVerbsRule': _with_language(SimpleReplaceVerbsRule),
    'SimpleReplaceBalearicRule': _with_language(SimpleReplaceBalearicRule),
    'SimpleReplaceRule': _with_language(SimpleReplaceRule),
    'SimpleReplaceMultiwordsRule': _messages_only(SimpleReplaceMultiwordsRule),
    'ReplaceOperationNamesRule': _with_language(ReplaceOperationNamesRule),
    'SimpleReplaceDiacriticsIEC': _with_language(SimpleReplaceDiacriticsIEC),
    'SimpleReplaceAnglicism': _messages_only(SimpleReplaceAnglicism),
    'SimpleReplaceAdverbsMent': _messages_only(SimpleReplaceAdverbsMent),
    'SimpleReplaceDNVRule': _with_language(SimpleReplaceDNVRule),
    'SimpleReplaceDNVColloquialRule': _with_language(SimpleReplaceDNVColloquialRule),
    'SimpleReplaceDNVSecondaryRule': _with_language(SimpleReplaceDNVSecondaryRule),
    'CheckCaseRule': _with_language(CheckCaseRule),
    'CatalanWrongWordInContextRule': _with_language(CatalanWrongWordInContextRule),
    'WordCoherencyRule': _messages_only(WordCoherencyRule),
    'WordCoherencyValencianRule': _messages_only(WordCoherencyValencianRule),
}
