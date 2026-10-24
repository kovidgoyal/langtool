"""French specific rules (port of org.languagetool.rules.fr).

The Java rules lowercase with Locale.FRENCH or new Locale("FR") (whose
language is "fr"), which have no special case mapping (str.lower here)."""

import threading

from ... import jregex
from ...patterns.pattern_token import cs_token, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractRepeatedWordsRule, AbstractSimpleReplaceRule,
                                     load_compound_rule_data, load_repeated_words, _rules_file)
from ...rules.base import RuleMatch
from ...rules.core import Categories, CoreRule
from ...tools import is_empty


def _french():
    """French.getInstance(), the language of the rules whose Java
    constructors only get the messages"""
    from ...api import get_language
    return get_language('fr')


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.fr.CompoundRule: compounds (listed in
    /fr/compounds.txt) that are not written as separate words. A word is
    misspelled if the French tagger doesn't know it."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Écrivez avec un trait d’union.',
                         'Écrivez avec un mot seul sans espace ni trait d’union.',
                         'Écrivez avec un mot seul ou avec trait d’union.',
                         'Erreur de trait d’union')
        self.add_example_pair('Le <marker>Haut Rhin</marker>.', 'Le <marker>Haut-Rhin</marker>.')
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'FR_COMPOUNDS'

    def get_description(self):
        return 'Mots avec trait d’union : $match'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/fr/compounds.txt')

    def is_misspelled(self, word):
        return not self.language.tagger.tag([word])[0].is_tagged()


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.fr.SimpleReplaceRule: words of
    /fr/replace.txt and /fr/replace_custom.txt that should not be used,
    case insensitive; tagged words and lemmas are not checked."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.set_ignore_tagged_words()
        self.check_lemmas = False
        self.use_sub_rule_specific_ids()

    _wrong_words = None

    def get_wrong_words(self):
        cls = type(self)
        if cls._wrong_words is None:
            cls._wrong_words = self.load_from_path('/fr/replace.txt', '/fr/replace_custom.txt')
        return cls._wrong_words

    def get_id(self):
        return 'FR_SIMPLE_REPLACE_SIMPLE'

    def get_description(self):
        return 'Mot incorrect : $match'

    def get_short(self):
        return 'Mot incorrect'

    def get_message(self, token_str, replacements):
        if replacements:
            return 'Vouliez-vous dire « ' + replacements[0] + ' » ?'
        return self.get_short()

    def is_case_sensitive(self):
        return False


def _replace_once(s, search, replacement):
    """StringUtils.replaceOnce"""
    return s.replace(search, replacement, 1)


class FrenchRepeatedWordsRule(AbstractRepeatedWordsRule):
    """Port of org.languagetool.rules.fr.FrenchRepeatedWordsRule: words of
    /fr/synonyms.txt repeated within a short distance."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _french())

    def get_words_to_check(self):
        return load_repeated_words(_rules_file(self.language, '/fr/synonyms.txt'))

    def get_message(self):
        return ("Ce mot apparaît déjà dans l'une des phrases précédant immédiatement celle-ci. Utilisez un synonyme "
                "pour apporter plus de variété à votre texte, excepté si la répétition est intentionnelle.")

    def get_description(self):
        return 'Synonymes de mots répétés.'

    def get_short_message(self):
        return 'Style : Mot répété'

    def get_synthesizer(self):
        return _french().synthesizer

    def adjust_postag(self, postag):
        if postag.endswith('e sp'):
            return _replace_once(postag, 'e sp', '. .*')
        if postag.endswith('m s'):
            return _replace_once(postag, 'm s', '[me] sp?')
        if postag.endswith('f s'):
            return _replace_once(postag, 'f s', '[fe] sp?')
        if postag.endswith('m p'):
            return _replace_once(postag, 'm p', '[me] s?p')
        if postag.endswith('f p'):
            return _replace_once(postag, 'f p', '[fe] s?p')
        if postag.endswith('e s'):
            return _replace_once(postag, 'e s', '[me] sp?')  # also F ?
        if postag.endswith('e p'):
            return _replace_once(postag, 'e p', '[me] s?p')  # also F ?
        if postag.endswith('m sp'):
            return _replace_once(postag, 'm sp', '[me] s?p?')
        if postag.endswith('f sp'):
            return _replace_once(postag, 'f sp', '[fe] s?p?')
        return postag

    def is_exception(self, tokens, i, sent_start, is_capitalized, is_all_upper):
        if is_all_upper or (is_capitalized and not sent_start):
            return True
        return tokens[i].has_pos_tag_starting_with('Z')


# Pattern used to avoid false positive when signaling missing
# space before and after colon ':' in URL with common schemes.
_URL_PATTERN = jregex.compile(
    '^(file|s?ftp|finger|git|gopher|hdl|https?|shttp|imap|mailto|mms|nntp|s?news(post|reply)?|prospero|rsync|'
    'rtspu|sips?|svn|svn\\+ssh|telnet|wais)$')

_ESPACE_FINE_INSECABLE = ' '
_NBSP = ' '


def _no_ws(t):
    """PatternTokenBuilder.setIsWhiteSpaceBefore(false)"""
    t.set_whitespace_before(False)
    return t


def _question_whitespace_anti_patterns():
    return (
        # ignore smileys, such as :-)
        (token_regex('[:;]'), _no_ws(cs_token('-')), _no_ws(token_regex('[\\(\\)D]'))),
        # ignore smileys, such as :)
        (token_regex('[:;]'), _no_ws(token_regex('[\\(\\)D]'))),
        # times like 23:20
        (token_regex('.*\\d{1,2}'), token(':'), token_regex('\\d{1,2}')),
        # "??"
        (token_regex('[?!]'), token_regex('[?!]')),
        # mac address
        (token_regex('[a-z0-9]{2}'), token(':'), token_regex('[a-z0-9]{2}'), token(':'),
         token_regex('[a-z0-9]{2}')),
        # csv markup (not sure why we need this, but there were a lot of users ignoring
        # this specific case)
        (token(';'), _no_ws(token_regex('.+')), _no_ws(token(';'))),
        # csv markup (not sure why we need this, but there were a lot of users ignoring
        # this specific case)
        (_no_ws(token_regex('.+')), _no_ws(token(';')), _no_ws(token_regex('.+'))),
    )


class QuestionWhitespaceRule(CoreRule):
    """Port of org.languagetool.rules.fr.QuestionWhitespaceRule: a rule that
    matches missing spaces before ?, :, ; and ! and inside « » (required for
    correct French punctuation). A normal space is accepted too (see
    QuestionWhitespaceStrictRule)."""

    category_id = 'MISC'
    # Rule.cacheAntiPatterns: per language
    _anti_patterns = {}
    _lock = threading.Lock()

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _french())

    def get_anti_patterns(self):
        cache = QuestionWhitespaceRule._anti_patterns
        code = self.language.code
        r = cache.get(code)
        if r is None:
            with QuestionWhitespaceRule._lock:
                r = cache.get(code)
                if r is None:
                    r = cache[code] = make_anti_patterns(_question_whitespace_anti_patterns(), self.language)
        return r

    def get_id(self):
        return 'FRENCH_WHITESPACE'

    def get_description(self):
        return 'Insertion des espaces fines insécables'

    def is_allowed_whitespace_char(self, tokens, i):
        return tokens[i].is_whitespace if i >= 0 else False

    def match(self, sentence):
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).tokens
        prev_prev_token = ''
        prev_token = ''
        for i in range(1, len(tokens)):
            tok = tokens[i].token
            if tokens[i].immunized or prev_token == '(' or prev_token == '[':
                prev_prev_token = prev_token
                prev_token = tok
                continue
            msg = None
            suggestion_text = None
            i_from = i - 1
            i_to = i
            is_previous_whitespace = tokens[i - 1].is_whitespace if i > 0 else False
            prev_token_to_change = prev_token
            if is_previous_whitespace:
                prev_token_to_change = ''
            if not self.is_allowed_whitespace_char(tokens, i - 1):
                # Strictly speaking, the character before ?!; should be an "espace fine
                # insécable" (U+202f). In practise, an "espace insécable" (U+00a0) is also
                # often used - or even a common space. Let's accept all - use
                # QuestionWhitespaceStrictRule if this is not strict enough.
                if tok == '?' and prev_token != '!':
                    msg = "Le point d'interrogation est précédé d'une espace fine insécable."
                    suggestion_text = prev_token_to_change + _ESPACE_FINE_INSECABLE + '?'
                elif tok == '!' and prev_token != '?':
                    msg = "Le point d'exclamation est précédé d'une espace fine insécable."
                    suggestion_text = prev_token_to_change + _ESPACE_FINE_INSECABLE + '!'
                elif tok == ';':
                    msg = "Le point-virgule est précédé d'une espace fine insécable."
                    suggestion_text = prev_token_to_change + _ESPACE_FINE_INSECABLE + ';'
                elif tok == ':':
                    # Avoid false positive for URL like http://www.languagetool.org.
                    if not _URL_PATTERN.search(prev_token):
                        msg = "Les deux-points sont précédés d'une espace insécable."
                        suggestion_text = prev_token_to_change + _NBSP + ':'
                elif tok == '»':
                    if prev_prev_token == '«':
                        msg = "Les guillemets sont toujours accompagnés d'une espace insécable."
                        suggestion_text = '«' + _NBSP + prev_token_to_change + _NBSP + '»'
                        i_from = i - 2
                    else:
                        msg = "Le guillemet fermant est précédé d'une espace insécable."
                        suggestion_text = prev_token_to_change + _NBSP + '»'
            if prev_token == '«':
                if is_empty(tok):
                    msg = "Le guillemet ouvrant est suivi d'une espace insécable."
                    suggestion_text = '«' + _NBSP
                    i_to = i - 1
                elif not self.is_allowed_whitespace_char(tokens, i):
                    next_token = ''
                    if i + 1 < len(tokens):
                        next_token = tokens[i + 1].token
                    if next_token != '»':
                        msg = "Le guillemet ouvrant est suivi d'une espace insécable."
                        if not tokens[i].is_whitespace:
                            suggestion_text = '«' + _NBSP + tok
                        else:
                            suggestion_text = '«' + _NBSP
            if msg is not None:
                from_pos = tokens[i_from].start_pos
                to_pos = tokens[i_to].end_pos
                rule_match = RuleMatch(self, sentence, from_pos, to_pos, msg, 'Insérer une espace insécable')
                rule_match.set_suggested_replacement(suggestion_text)
                rule_matches.append(rule_match)
            prev_prev_token = prev_token
            prev_token = tok
        return rule_matches


class QuestionWhitespaceStrictRule(QuestionWhitespaceRule):
    """Port of org.languagetool.rules.fr.QuestionWhitespaceStrictRule: like
    QuestionWhitespaceRule, but the space before ?!; must be a (thin)
    non-breaking space (picky, temp_off)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.tags = ['picky']
        self.set_default_temp_off()

    def get_id(self):
        return 'FRENCH_WHITESPACE_STRICT'

    def get_description(self):
        return 'Insertion des espaces fines insécables'

    def is_allowed_whitespace_char(self, tokens, i):
        # Strictly speaking, the character before ?!; should be an
        # "espace fine insécable" (U+202f). In practise, an
        # "espace insécable" (U+00a0) is also often used. Let's accept both.
        if i < 0:
            return False
        return (tokens[i].token == ' ' or tokens[i].token == ' '
                # covered by FRENCH_WHITESPACE (non strict). This makes both rules mutually exclusive
                or not tokens[i].is_whitespace)
