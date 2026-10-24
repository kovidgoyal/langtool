"""Spanish specific rules (port of org.languagetool.rules.es).

The Java rules lowercase with Locale("es") (or new Locale("ES"), whose
language is "es" too), which has no special case mapping (str.lower
here)."""

import threading

from ... import jregex
from ...analysis import AnalyzedToken
from ...patterns.pattern_token import cs_regex, token
from ...patterns.rules import make_anti_patterns
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractRepeatedWordsRule, AbstractSimpleReplaceRule,
                                     AbstractSimpleReplaceRule2, WordRepeatBeginningRule, WrongWordInContextRule,
                                     java_hash_set_order, load_compound_rule_data, load_repeated_words, _rules_file)
from ...rules.base import RuleMatch
from ...rules.core import Categories, CoreTextLevelRule, GenericUnpairedBracketsRule, WordRepeatRule
from ...tools import is_digit, is_punctuation_mark, java_equals_ignore_case


def _spanish():
    """Spanish.getInstance(), the language of the rules whose Java
    constructors only get the messages"""
    from ...api import get_language
    return get_language('es')


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.es.CompoundRule: compounds (listed in
    /es/compounds.txt) that are not written as separate words. A word is
    misspelled if the Spanish tagger doesn't know it."""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Se escribe con un guion.',
                         'Se escribe junto sin espacio ni guion.',
                         'Se escribe junto o con un guion.',
                         'Error de palabra compuesta')
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>Guinea Conakri</marker>.', '<marker>Guinea-Conakri</marker>.')

    def get_id(self):
        return 'ES_COMPOUNDS'

    def get_description(self):
        return 'Palabras compuestas con guion: $match'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/es/compounds.txt')

    def is_misspelled(self, word):
        return not self.language.tagger.tag([word])[0].is_tagged()


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.es.SimpleReplaceRule: words of
    /es/replace.txt and /es/replace_custom.txt that should not be used,
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
            cls._wrong_words = self.load_from_path('/es/replace.txt', '/es/replace_custom.txt')
        return cls._wrong_words

    def get_id(self):
        return 'ES_SIMPLE_REPLACE_SIMPLE'

    def get_description(self):
        return 'Palabra incorrecta: $match'

    def get_short(self):
        return 'Palabra incorrecta'

    def get_message(self, token_str, replacements):
        if replacements:
            return '¿Quería decir «' + replacements[0] + '»?'
        return self.get_short()

    def is_case_sensitive(self):
        return False


_ENDINGS = ('a|aba|abais|aban|abas|ad|ada|adas|ado|ados|amos|an|ando|ar|ara|'
            'arais|aran|aras|are|areis|aremos|aren|ares|aron|ará|arán|arás|aré|aréis|aría|aríais|aríamos|arían|'
            'arías|as|ase|aseis|asen|ases|aste|asteis|e|emos|en|es|o|ábamos|áis|áramos|áremos|ásemos|é|éis|ó|'
            'arse|arme|arte|arlos|arles|arlas|arnos|aros')
_DESINENCIES_1CONJ_0 = jregex.compile('(.+?)(' + _ENDINGS + ')')
_DESINENCIES_1CONJ_1 = jregex.compile('(.+)(' + _ENDINGS + ')')


class SimpleReplaceVerbsRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.es.SimpleReplaceVerbsRule: incorrect
    verbs of the first conjugation (all inflected forms, listed by their
    infinitive in /es/replace_verbs.txt); the suggestions are the forms of
    the replacement verbs synthesized with the POS tags of the same form of
    "amar"."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.set_ignore_tagged_words()
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self.load_from_path('/es/replace_verbs.txt')

    def get_id(self):
        return 'ES_SIMPLE_REPLACE_VERBS'

    def get_description(self):
        return 'Detecta verbos incorrectos y propone sugerencias.'

    def get_short(self):
        return 'Verbo incorrecto'

    def get_message(self, token_str, replacements):
        return 'Verbo incorrecto: $match'

    def match(self, sentence):
        rule_matches = []
        wrong_words = self.get_wrong_words()
        tagger = self.language.tagger
        synth = self.language.synthesizer
        for token_readings in sentence.non_blank_tokens:
            original_token_str = token_readings.token
            if self.ignore_tagged_words and token_readings.is_tagged():
                continue
            token_string = self.lower(original_token_str)
            analyzed_token_readings = None
            infinitive = None
            i = 0
            while i < 2 and analyzed_token_readings is None:
                m = (_DESINENCIES_1CONJ_0 if i == 0 else _DESINENCIES_1CONJ_1).fullmatch(token_string)
                if m:
                    lexeme = m.group(1)
                    desinence = m.group(2)
                    if desinence.startswith(('e', 'é', 'i', 'ï')):
                        if lexeme.endswith('c'):
                            lexeme = lexeme[:-1] + 'z'
                        elif lexeme.endswith('qu'):
                            lexeme = lexeme[:-2] + 'c'
                        elif lexeme.endswith('g'):
                            lexeme = lexeme[:-1] + 'j'
                        elif lexeme.endswith('gü'):
                            lexeme = lexeme[:-2] + 'gu'
                        elif lexeme.endswith('gu'):
                            lexeme = lexeme[:-2] + 'g'
                    infinitive = lexeme + 'ar'
                    if infinitive in wrong_words:
                        atrs = tagger.tag(['am' + desinence])
                        if atrs[0].readings[0].pos_tag is not None:
                            analyzed_token_readings = atrs[0]
                i += 1
            # synthesize replacements
            if analyzed_token_readings is not None:
                possible_replacements = []
                for replacement_infinitive in wrong_words[infinitive]:
                    if replacement_infinitive.startswith('('):
                        possible_replacements.append(replacement_infinitive)
                    else:
                        parts = replacement_infinitive.split(' ')  # the first part is the verb
                        infinitive_as_token = AnalyzedToken(parts[0], 'V.*', parts[0])
                        for analyzed_token in analyzed_token_readings.readings:
                            pos_tag = analyzed_token.pos_tag
                            if infinitive_as_token.lemma == 'haver':
                                pos_tag = 'VA' + pos_tag[2:]
                            for s in synth.synthesize(infinitive_as_token, pos_tag):
                                for part in parts[1:]:
                                    s = s + ' ' + part
                                if s not in possible_replacements:
                                    possible_replacements.append(s)
                if possible_replacements:
                    rule_matches.append(self.create_rule_match(token_readings, possible_replacements, sentence,
                                                               infinitive))
        return rule_matches


class SpanishWikipediaRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.es.SpanishWikipediaRule: common
    errors of Wikipedia articles (/es/wikipedia.txt), default off."""

    issue_type = 'Grammar'

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _spanish())
        self.category = Categories.get('WIKIPEDIA', messages)
        self.add_example_pair('<marker>a basto</marker>', '<marker>abasto</marker>')
        self.set_default_off()
        self.url = ('https://es.wikipedia.org/wiki/Wikipedia:Lista_de_errores_ortogr%C3%A1ficos_comunes/'
                    'M%C3%A1quinas')

    def get_file_names(self):
        return ['/es/wikipedia.txt']

    def get_id(self):
        return 'ES_WIKIPEDIA_COMMON_ERRORS'

    def get_description(self):
        return 'Errores frecuentes en los artículos de la Wikipedia'

    def get_short(self):
        return 'Error gramatical u ortográfico'

    def get_message(self):
        return "'$match' es una expresión errónea. Pruebe a utilizar $suggestions"

    def get_suggestions_separator(self):
        return ' o '


class SpanishWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.es.SpanishWordRepeatRule: no false
    alarms for words tagged _allow_repeat."""

    rule_id = 'SPANISH_WORD_REPEAT_RULE'

    def ignore(self, tokens, position):
        if position > 0 and (tokens[position].has_pos_tag('_allow_repeat')
                             or tokens[position - 1].has_pos_tag('_allow_repeat')):
            return True
        return super().ignore(tokens, position)


class SpanishWrongWordInContextRule(WrongWordInContextRule):
    """Port of org.languagetool.rules.es.SpanishWrongWordInContextRule
    (/es/wrongWordInContext.txt, the contexts are matched with the
    lemmas)."""

    issue_type = 'Grammar'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.set_match_lemmas()

    def get_category_string(self):
        return 'Confusiones'

    def get_id(self):
        return 'SPANISH_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'Confusión según el contexto: $match'

    def get_filename(self):
        return '/es/wrongWordInContext.txt'

    def get_message_string(self):
        return '¿Quería decir <suggestion>$SUGGESTION</suggestion> en vez de "$WRONGWORD"?'

    def get_short_message_string(self):
        return 'Posible confusión'

    def get_long_message_string(self):
        return ('¿Quería decir <suggestion>$SUGGESTION</suggestion> ($EXPLANATION_SUGGESTION) en vez de '
                '"$WRONGWORD" ($EXPLANATION_WRONGWORD)?')


_ANTI_PATTERNS = (
    (token('también'), cs_regex('.+')),
    (cs_regex('.+'), token('también')),
    (cs_regex('[Aa]ntes|[Dd]espués'), cs_regex('de|del')),
    (cs_regex('[Tt]ema|TEMA'), cs_regex('\\d+|[IXVC]+')),
    (cs_regex('[Aa]sí'), token('que')),
)


def _replace_once(s, search, replacement):
    """StringUtils.replaceOnce"""
    return s.replace(search, replacement, 1)


class SpanishRepeatedWordsRule(AbstractRepeatedWordsRule):
    """Port of org.languagetool.rules.es.SpanishRepeatedWordsRule: words of
    /es/synonyms.txt repeated within a short distance (picky)."""

    _anti_patterns = None
    _lock = threading.Lock()

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _spanish())
        self.tags = ['picky']

    def get_anti_patterns(self):
        cls = type(self)
        if cls._anti_patterns is None:
            with cls._lock:
                if cls._anti_patterns is None:
                    cls._anti_patterns = make_anti_patterns(_ANTI_PATTERNS, _spanish())
        return cls._anti_patterns

    def get_words_to_check(self):
        return load_repeated_words(_rules_file(self.language, '/es/synonyms.txt'))

    def get_message(self):
        return ('Esta palabra ya ha aparecido en una de las frases inmediatamente anteriores. Puede usar un '
                'sinónimo para hacer más interesante el texto, excepto si la repetición es intencionada.')

    def get_description(self):
        return 'Sinónimos para palabras repetidas.'

    def get_short_message(self):
        return 'Estilo: palabra repetida'

    def get_synthesizer(self):
        return _spanish().synthesizer

    def adjust_postag(self, postag):
        if 'CN' in postag:
            return _replace_once(postag, 'CN', '..')
        if 'MS' in postag:
            return _replace_once(postag, 'MS', '[MC][SN]')
        if 'FS' in postag:
            return _replace_once(postag, 'FS', '[FC][SN]')
        if 'MP' in postag:
            return _replace_once(postag, 'MP', '[MC][PN]')
        if 'FP' in postag:
            return _replace_once(postag, 'FP', '[FC][PN]')
        if 'CS' in postag:
            return _replace_once(postag, 'CS', '[MC][SN]')  # also F ?
        if 'CP' in postag:
            return _replace_once(postag, 'CP', '[MC][PN]')  # also F ?
        if 'MN' in postag:
            return _replace_once(postag, 'MN', '[MC][SPN]')
        if 'FN' in postag:
            return _replace_once(postag, 'FN', '[FC][SPN]')
        return postag

    def is_exception(self, tokens, i, sent_start, is_capitalized, is_all_upper):
        if is_all_upper or (is_capitalized and not sent_start):
            return True
        return tokens[i].has_pos_tag_starting_with('NP') or tokens[i].has_pos_tag('_english_ignore_')


ES_START_SYMBOLS = ['[', '(', '{', '“', '«', '"', "'", '‘']
ES_END_SYMBOLS = [']', ')', '}', '”', '»', '"', "'", '’']
_VALID_BEFORE_CLOSING_PARENTHESIS = jregex.compile('\\d+|[a-zA-Z]')
_NUMBER = jregex.compile('\\d[\\d., ]+\\d|\\d{1,2}')


def _is_quote(token_str):
    return token_str == "'" or token_str == '’'


class SpanishUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.es.SpanishUnpairedBracketsRule, with
    exceptions for apostrophes in nouns and adjectives, the English Saxon
    genitive, degrees/minutes/seconds, "»" at the sentence start and
    enumerations like "a)". The suggestions add the missing symbol next to
    the unpaired one, or remove it."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, ES_START_SYMBOLS, ES_END_SYMBOLS)

    def get_id(self):
        return 'ES_UNPAIRED_BRACKETS'

    def is_no_exception(self, token_str, tokens, i, j, prec_space, foll_space, stack):
        if i < 1:
            return True
        if not super().is_no_exception(token_str, tokens, i, j, prec_space, foll_space, stack):
            return False
        if ((token_str == '’' or token_str == "'")
                and (tokens[i].has_pos_tag_starting_with('N') or tokens[i].has_pos_tag_starting_with('A')
                     or tokens[i].has_pos_tag('_allow_apostrophe'))):
            return False
        # Exception for English plural Saxon genitive
        if i + 1 < len(tokens) and _is_quote(token_str) and java_equals_ignore_case('s', tokens[i + 1].token):
            return False
        # degrees, minutes, seconds...
        if ((token_str == '"' or token_str == "'")
                and _NUMBER.fullmatch(tokens[i - 1].token)
                and not tokens[i].whitespace_before
                and ((i > 2 and ('º' in tokens[i - 2].token or '°' in tokens[i - 2].token))
                     or (i > 4 and ('º' in tokens[i - 4].token or '°' in tokens[i - 4].token)))):
            return False
        if i == 1 and token_str == '»':
            return False
        if i > 1 and token_str == ')':
            is_there_opening_parenthesis = False
            k = 1
            while i - k > 0:
                if tokens[i - k].token == ')':
                    break
                if tokens[i - k].token == '(':
                    is_there_opening_parenthesis = True
                    break
                k += 1
            if not is_there_opening_parenthesis:
                if _VALID_BEFORE_CLOSING_PARENTHESIS.fullmatch(tokens[i - 1].token):
                    return False
        return True

    def get_suggestions(self, full_text, start_pos, end_pos, symbol, other_symbol, symbol_type=None):
        # add the other symbol together with the original symbol, needs to be
        # moved by the user
        if symbol_type == 'Closing':
            replacements = [other_symbol + symbol]
        else:
            replacements = [symbol + other_symbol]
        # add the option to remove the original symbol
        replacements.append('')
        return replacements


class QuestionMarkRule(CoreTextLevelRule):
    """Port of org.languagetool.rules.es.QuestionMarkRule: checks there's a
    '¿' character if the sentence ends with '?', same for '¡' and '!'."""

    category_id = 'TYPOGRAPHY'
    issue_type = 'Typographical'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('<marker>Qué</marker> pasa?', '<marker>¿Qué</marker> pasa?')

    def min_to_check_paragraph(self):
        return 1

    def get_id(self):
        return 'ES_QUESTION_MARK'

    def get_description(self):
        return 'Signos de exclamación / interrogación desparejados'

    def match(self, sentences, annotated_text=None):
        matches = []
        pos = 0
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            needs_inv_question_mark_at = self._has_token_at_pos('?', tokens)
            needs_inv_excl_mark_at = self._has_token_at_pos('!', tokens)
            if needs_inv_question_mark_at > 1 or needs_inv_excl_mark_at > 1:
                has_inv_question_mark = False
                has_inv_excl_mark = False
                first_token = None
                n = len(tokens)
                for i in range(n):
                    t = tokens[i]
                    if first_token is None and not t.is_sentence_start and not is_punctuation_mark(t.token):
                        first_token = t
                    if t.token == '¿' and i < needs_inv_question_mark_at:
                        has_inv_question_mark = True
                    elif t.token == '¡' and i < needs_inv_excl_mark_at:
                        has_inv_excl_mark = True
                    # possibly a sentence end
                    if not t.is_sentence_end and (t.token == '?' and i > needs_inv_question_mark_at
                                                  or t.token == '!' and i > needs_inv_excl_mark_at):
                        first_token = None
                    # put the question mark in: ¿de qué... ¿para cuál... ¿cómo...
                    if i > 2 and i + 2 < n:
                        prev_comma = tokens[i - 1].token == ','
                        if (prev_comma and t.has_pos_tag('CC') and tokens[i + 1].has_pos_tag('SPS00')
                                and (tokens[i + 2].has_pos_tag_starting_with('PT')
                                     or tokens[i + 2].has_pos_tag_starting_with('DT'))):
                            first_token = t
                        if (prev_comma and t.has_pos_tag('SPS00')
                                and (tokens[i + 1].has_pos_tag_starting_with('PT')
                                     or tokens[i + 1].has_pos_tag_starting_with('DT'))):
                            first_token = t
                        if (prev_comma and t.has_pos_tag('CC')
                                and (tokens[i + 1].has_pos_tag_starting_with('PT')
                                     or tokens[i + 1].has_pos_tag_starting_with('DT'))):
                            first_token = t
                        if prev_comma and (t.has_pos_tag_starting_with('PT') or t.has_pos_tag_starting_with('DT')):
                            first_token = t
                        if (prev_comma and t.has_pos_tag('CC')
                                and (tokens[i + 1].token == 'no' or tokens[i + 1].token == 'sí')):
                            first_token = t
                    if i > 2:
                        if tokens[i - 1].token == ',' and t.token in ('no', 'sí', 'eh'):
                            first_token = t
                if first_token is not None and not first_token.has_pos_tag('_english_ignore_'):
                    s = None
                    if needs_inv_question_mark_at > 1 and needs_inv_excl_mark_at > 1:
                        # ignore for now, e.g. "¡¿Nunca tienes clases o qué?!"
                        pass
                    elif needs_inv_question_mark_at > 1 and not has_inv_question_mark:
                        s = '¿'
                    elif needs_inv_excl_mark_at > 1 and not has_inv_excl_mark:
                        s = '¡'
                    if s is not None:
                        # (Java doesn't skip the sentences after one ending with ':')
                        message = "Símbolo desparejado: Parece que falta un '" + s + "'"
                        match = RuleMatch(self, sentence, pos + first_token.start_pos, pos + first_token.end_pos,
                                          message)
                        match.set_suggested_replacement(s + first_token.token)
                        matches.append(match)
            pos += sentence.get_corrected_text_length()
        return matches

    @staticmethod
    def _has_token_at_pos(ch, tokens):
        i = len(tokens) - 1
        while i > 0:
            if tokens[i].token == ch:
                if (i < len(tokens) - 1 and not tokens[i + 1].whitespace_before
                        and not is_punctuation_mark(tokens[i + 1].token)
                        and not tokens[i + 1].is_whitespace):
                    # ignore question marks joined to the next word, as in URLs
                    pass
                else:
                    return i
            i -= 1
        return -1


# adverbs used to add to what the previous sentence mentioned
_ADD_ADVERBS = ('Asimismo', 'Igualmente', 'Además', 'También', 'Adicionalmente')
# adverbs used to express contrast to what the previous sentence mentioned
_CONTRAST_CONJ = ('Pero', 'Empero', 'Mas')
# adverbs used to express emphasis to what the previous sentence mentioned
_EMPHASIS_ADVERBS = ('Obviamente', 'Claramente', 'Absolutamente', 'Definitivamente')
# adverbs used to explain what the previous sentence mentioned
_EXPLAIN_ADVERBS = ('Específicamente', 'Concretamente', 'Particularmente', 'Precisamente')
# personal pronouns
_PERSONAL_PRONOUNS = frozenset(('yo', 'tú', 'él', 'ella', 'nosostros', 'nosotras', 'vosotros', 'vosotras',
                                'ellos', 'ellas', 'usted', 'ustedes'))
# linking expressions that can be used instead of the ADD_ADVERBS
_ADD_EXPRESSIONS = ('Así mismo',)
# linking expressions that can be used instead of the CONTRAST_ADVERBS
_CONTRAST_EXPRESSIONS = ('Aun así', 'Por otra parte', 'Sin embargo')
_EXCEPCIONS_START = frozenset(('el', 'la', 'los', 'las', 'punto', 'artículo', 'módulo', 'parte', 'sesión',
                               'unidad', 'tema', 'n'))
_SENTENCE_EXCEPCIONS = ('por un', 'por otro', 'por otra', 'por una')
# (the iteration order of the Java HashSets)
_ADD_ADVERBS_ORDER = java_hash_set_order(_ADD_ADVERBS)
_EMPHASIS_ADVERBS_ORDER = java_hash_set_order(_EMPHASIS_ADVERBS)
_EXPLAIN_ADVERBS_ORDER = java_hash_set_order(_EXPLAIN_ADVERBS)


def _different_adverbs_of_same_category(adverb, adverbs_of_category):
    return [adv for adv in adverbs_of_category if adv != adverb]


class SpanishWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.es.SpanishWordRepeatBeginningRule:
    WordRepeatBeginningRule with Spanish adverbs, exceptions and
    suggestions (picky)."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.tags = ['picky']
        self.add_example_pair(
            'Asimismo, la calle es casi toda residencial. <marker>Asimismo</marker>, lleva el nombre de un poeta.',
            'Además, la calle es casi toda residencal. También lleva el nombre de un poeta.')

    def get_id(self):
        return 'SPANISH_WORD_REPEAT_BEGINNING_RULE'

    def is_exception(self, token_str):
        return (super().is_exception(token_str) or is_digit(token_str[0])
                or token_str.lower() in _EXCEPCIONS_START)

    def is_adverb(self, atr):
        if atr.has_pos_tag('RG') or atr.has_pos_tag('LOC_ADV'):
            return True
        tok = atr.token
        return tok in _ADD_ADVERBS or tok in _CONTRAST_CONJ or tok in _EMPHASIS_ADVERBS or tok in _EXPLAIN_ADVERBS

    def get_suggestions(self, atr):
        tok = atr.token
        lower_tok = tok.lower()
        # the repeated word is a personal pronoun
        if lower_tok in _PERSONAL_PRONOUNS:
            return ['Además, ' + lower_tok, 'Igualmente, ' + lower_tok, 'No solo eso, sino que ' + lower_tok]
        if tok in _ADD_ADVERBS:
            return _different_adverbs_of_same_category(tok, _ADD_ADVERBS_ORDER) + list(_ADD_EXPRESSIONS)
        if tok in _CONTRAST_CONJ:
            return list(_CONTRAST_EXPRESSIONS)
        if tok in _EMPHASIS_ADVERBS:
            return _different_adverbs_of_same_category(tok, _EMPHASIS_ADVERBS_ORDER)
        if tok in _EXPLAIN_ADVERBS:
            return _different_adverbs_of_same_category(tok, _EXPLAIN_ADVERBS_ORDER)
        return []

    def is_sentence_exception(self, sentence):
        s = sentence.text.lower()
        for exception in _SENTENCE_EXCEPCIONS:
            if s.startswith(exception):
                return True
        return False
