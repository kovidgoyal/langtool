"""The misspelling check and the spelling suggestions of
org.languagetool.rules.ca.MorfologikCatalanSpellerRule, and
CatalanMorfologikMultitokenSpeller.

Only the check whether a word is misspelled (and whether a sentence would
get a spelling rule match, used by CatalanSuppressMisspelledSuggestionsFilter)
and the suggestions for a single word (getSpellingSuggestions, used by
CatalanNumberInWordFilter) are ported (see langtool.spelling), not the spell
checking rule MORFOLOGIK_RULE_CA_ES (no rule matches). It is the default
spelling rule of Catalan here. The speller dictionaries ca/ca-ES_spelling.dict
and ca/ca-ES_spelling_multitoken.dict (catalan-pos-dict) and the word lists
ca/spelling.txt, ca/hunspell/ignore.txt and prohibit.txt (language-ca) are
obtained with the dictionary download mechanism (langtool.dictionaries)."""

import threading

from ... import jregex
from ...spelling import MorfologikMisspellingCheck, MorfologikSuggestions, WeightedStr, suggestion_weight
from ...tools import (is_all_lowercase, is_capitalized_word, java_equals_ignore_case, java_split, java_trim,
                      remove_diacritics, split_camel_case, split_digits_at_end)
from .helpers import transform_darrere

_FORM_TAG_SPLIT = jregex.compile('[\t;]')
_SPELLER_EXCEPTIONS = ('San Juan', 'Copa América', 'Colección Jumex', 'Banco Santander', 'San Marcos', 'Santa Ana',
                       'San Joaquín', 'Naguib Mahfouz', 'Rosalía', 'Aristide Maillol', 'Alexia Putellas',
                       'Mónica Randall', 'Vicente Blasco Ibáñez', 'Copa Sudamericana', 'Série A', 'Banco Sabadell')


def prepare_line_for_speller(line):
    """Catalan.prepareLineForSpeller: lines of the word lists with a tag
    (multiwords.txt) are used only for nouns and _Latin_; some proper nouns
    are not used"""
    parts = java_split(line, '#')
    if not parts:
        return [line]
    form_tag = _FORM_TAG_SPLIT.split(parts[0])
    while form_tag and form_tag[-1] == '':
        form_tag.pop()
    if not form_tag:
        # String.split of an empty string gives [""]
        form_tag = ['']
    form = java_trim(form_tag[0])
    if form in _SPELLER_EXCEPTIONS:
        return ['']
    if len(form_tag) > 1:
        tag = java_trim(form_tag[1])
        if tag.startswith('N') or tag == '_Latin_':
            return [form]
        return ['']
    return [line]


_QUOTE_OR_HYPHEN = jregex.compile("['-]")
_MAX_WEIGHT_DIFF = 10
_PARTICULA_INICIAL = ('amb', 'sota', 'no', 'en', 'a', 'el', 'els', 'al', 'als', 'pel', 'pels', 'del', 'dels', 'del',
                      'de', 'per', 'un', 'uns', 'una', 'unes', 'la', 'les', 'teu', 'meu', 'seu', 'teus', 'meus', 'seus')
_PREPOSICIONS = ('amb', 'en', 'sota', 'a', 'al', 'als', 'pel', 'pels', 'pel', 'dels', 'del', 'de', 'per')
_PREFIX_AMB_ESPAI = ('pod', 'ultra', 'eco', 'tele', 'anti', 're', 'des', 'sen', 'sem', 's', 'avant', 'auto', 'ex',
                     'extra', 'macro', 'mega', 'meta', 'micro', 'multi', 'mono', 'mini', 'post', 'retro', 'semi',
                     'super', 'trans', 'pro', 'g', 'l', 'm', 'e', 'pos', 'acost')
_ESPAI_AMB_SUFIX_NO = ('mi', 'lis', 'isme')
_ESPAI_AMB_SUFIX_SI = ('a', 'o', 'i')
_PRONOM_INICIAL = ('em', 'et', 'es', 'se', 'ens', 'us', 'vos', 'li', 'hi', 'ho', 'el', 'la', 'els', 'les')

_CI = jregex.IGNORECASE
_APOSTROF_INICI_VERBS = jregex.compile('^([lnts])[90]?(h?[aeiouàéèíòóú].*)$', _CI)
_APOSTROF_INICI_VERBS_M = jregex.compile('^(m)[90]?(h?[aeiouàéèíòóú].*)$', _CI)
_APOSTROF_INICI_NOM_SING = jregex.compile('^([ld])[90]?(h?[aeiouàéèíòóú]...+)$', _CI)
_APOSTROF_INICI_NOM_PLURAL = jregex.compile('^(d)[90]?(h?[aeiouàéèíòóú].+)$', _CI)
_APOSTROF_FINAL = jregex.compile('^(...+[aei])[90]?(l|ls|m|ns|n|t)$', _CI)
_APOSTROF_FINAL_S = jregex.compile('^(.+e)[90]?(s)$', _CI)
_GUIONET_FINAL = jregex.compile("^([\\p{L}·]+)[’']?(hi|ho|la|les|li|lo|los|me|ne|nos|se|te|vos)$", _CI)
_GUIONET_FINAL_GERUNDI = jregex.compile('^([\\p{L}·]+n)(hi|ho|la|les|li|lo|los|me|ne|nos|se|te|vos)$', _CI)
_SPLIT_DIGITS_AT_END = ('en', 'de', 'del', 'al', 'dels', 'als', 'a', 'i', 'o', 'amb')
_VERB_INDSUBJ = jregex.compile('V.[SI].*')
_VERB_INDSUBJ_M = jregex.compile('V.[SI].[123]S.*|V.[SI].[23]P.*')
_NOM = jregex.compile('V.[NG].*|V.P.*|N.*|A.*|PX.*|DD.*')
_NOM_SING = jregex.compile('V.[NG].*|V.P..S..|N..[SN].*|A...[SN].|PX..S...|DD..S.')
_NOM_PLURAL = jregex.compile('V.P..P..|N..[PN].*|A...[PN].|PX..P...|DD..P.')
_VERB_INFGERIMP = jregex.compile('V.[NGM].*')
_VERB_INF = jregex.compile('V.N.*')
_VERB_GER = jregex.compile('V.G.*')
_VERB_BALEAR = jregex.compile('V......B')
_SPLIT_SPACE_APOS_HYPHEN = jregex.compile("[ '-]")

# lemma exceptions
LEMMAS_TO_IGNORE = ('enterar', 'sentar', 'conseguir', 'alcançar', 'entimar', 'pisar')
LEMMAS_TO_ALLOW = ('enter', 'sentir')

_INALAMBRIC = ('inalàmbric', 'inalàmbrica', 'inalàmbrics', 'inalàmbriques', 'inalàmbricament', 'inalàmbricamente')

_PRONOMS_DARRERE = (
    'losels', 'losles', 'nosels', 'nosles', 'vosels', 'vosens', 'vosles', 'lesen', 'leshi', 'liles', 'losel', 'losen',
    'loshi', 'losho', 'losla', 'lsels', 'lsles', 'meles', 'nosel', 'nosen', 'noshi', 'nosho', 'nosla', 'nosli',
    'nsels', 'nsles', 'seles', 'sevos', 'teles', 'usels', 'usens', 'usles', 'vosel', 'vosem', 'vosen', 'voshi',
    'vosho', 'vosla', 'vosli', 'lahi', 'lihi', 'liho', 'lila', 'lils', 'lsel', 'lsen', 'lshi', 'lsho', 'lsla', 'mela',
    'meli', 'mels', 'nsel', 'nsen', 'nshi', 'nsho', 'nsla', 'nsli', 'sela', 'seli', 'sels', 'sens', 'seus', 'tela',
    'teli', 'tels', 'tens', 'usel', 'usem', 'usen', 'ushi', 'usho', 'usla', 'usli', 'lan', 'len', 'les', 'lhi', 'lil',
    'lin', 'los', 'mel', 'men', 'mhi', 'mho', 'nhi', 'nos', 'sel', 'sem', 'sen', 'set', 'shi', 'sho', 'tel', 'tem',
    'ten', 'thi', 'tho', 'vos', 'hi', 'ho', 'la', 'li', 'lo', 'ls', 'me', 'ne', 'ns', 'se', 'te', 'us', 'mi', 'nosi',
    'losi', 'si', 'lis')
# "l", "m", "n", "s", "t"


def _equals_ignore_case_and_diacritics(a, b):
    """StringTools.equalsIgnoreCaseAndDiacritics"""
    return java_equals_ignore_case(remove_diacritics(a), remove_diacritics(b))


def _match_postag_regexp(atr, pattern):
    """Match POS tag with regular expression (unknown words: "UNKNOWN")"""
    for reading in atr:
        pos_tag = reading.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if pattern.fullmatch(pos_tag):
            return True
    return False


class MorfologikCatalanSpellerCheck(MorfologikSuggestions, MorfologikMisspellingCheck):
    """The files of MorfologikCatalanSpellerRule (the other ones are the
    defaults of SpellingCheckRule), its suggestion ordering and additional
    top suggestions. The rule ignores tagged words (setIgnoreTaggedWords);
    the tagger of the variant is used (CatalanTagger.INSTANCE_VAL for
    Valencian, INSTANCE_CAT otherwise)."""

    def get_file_name(self):
        return '/ca/ca-ES_spelling.dict'

    def get_spelling_file_name(self):
        return '/ca/spelling.txt'

    def get_additional_spelling_file_names(self):
        # SpellingCheckRule.CUSTOM_SPELLING_FILE is "/hunspell/spelling_custom.txt": Java asks for
        # "/ca//hunspell/spelling_custom.txt" (which doesn't exist)
        return ['/ca//hunspell/spelling_custom.txt', 'spelling_global.txt', '/ca/multiwords.txt',
                '/ca/spelling-special.txt']

    def tokenize_new_words(self):
        # Do not tokenize new words from spelling.txt...
        # Multi-token words should be in multiwords.txt
        return False

    def prepare_line_for_speller(self, line):
        return prepare_line_for_speller(line)

    def sentence_has_match(self, sentence, ignore_tagged_words=True):
        return super().sentence_has_match(sentence, ignore_tagged_words)

    @property
    def tagger(self):
        return self.language.tagger

    def _tag1(self, word):
        return self.tagger.tag([word])[0]

    def order_suggestions(self, suggestions, word):
        # move some run-on-words suggestions to the top
        suggestions = list(suggestions)
        new_suggestions = []
        word_without_diacritics = remove_diacritics(word)
        replacements = list(suggestions)
        n = len(suggestions)
        for i in range(n):
            replacement = replacements[i]
            # avoid duplicate capitalized replacement
            if word == word.lower() and is_capitalized_word(replacement) and replacement.lower() in replacements:
                continue
            # avoid capitalized suggestions if there are previous all lower case suggestions
            if (i > 0 and new_suggestions and is_all_lowercase(word) and is_capitalized_word(replacement)
                    and is_all_lowercase(new_suggestions[0])
                    and not _equals_ignore_case_and_diacritics(word, replacement)):
                continue
            if replacement.lower() in _INALAMBRIC:
                return ['sense fils', 'sense fil', 'sense cables', 'autònom']
            # remove always
            if java_equals_ignore_case(replacement, 'como'):
                continue
            ignore_suggestion = False
            words_to_analyze = _SPLIT_SPACE_APOS_HYPHEN.split(replacement)
            while words_to_analyze and words_to_analyze[-1] == '':
                words_to_analyze.pop()
            for newatr in self.tagger.tag(words_to_analyze):
                if newatr.has_any_lemma(*LEMMAS_TO_IGNORE) and not newatr.has_any_lemma(*LEMMAS_TO_ALLOW):
                    ignore_suggestion = True
                    break
            if ignore_suggestion:
                continue
            # l'_ : remove superfluous space
            if "' " in replacement:
                suggestions[i] = WeightedStr(replacement.replace("' ", "'"), suggestion_weight(suggestions[i]))
            parts = java_split(replacement, ' ')
            if len(parts) == 2:
                if java_equals_ignore_case(parts[1], 's'):
                    continue
                # remove wrong split prefixes
                if parts[0].lower() in _PREFIX_AMB_ESPAI:
                    continue
                # remove wrong split sufixes
                if parts[1].lower() in _ESPAI_AMB_SUFIX_NO:
                    continue
                # allow only one-letter second part " a", " o", " i"
                if len(parts[1]) == 1 and parts[1].lower() not in _ESPAI_AMB_SUFIX_SI:
                    continue
                # remove preposition + inflected verb
                if len(parts[1]) > 1 and parts[0].lower() in _PREPOSICIONS:
                    atkn = self._tag1(parts[1])
                    if atkn.matches_pos_tag_regex(_VERB_INDSUBJ) and not atkn.matches_pos_tag_regex(_NOM):
                        continue
            # Don't change first suggestions if they match word without diacritics
            pos_new_sugg = 0
            while (len(new_suggestions) > pos_new_sugg
                   and java_equals_ignore_case(remove_diacritics(new_suggestions[pos_new_sugg]),
                                               word_without_diacritics)):
                pos_new_sugg += 1
            # move some split words to first place
            if len(parts) == 2:
                atkn0 = self._tag1(parts[0])
                atkn1 = self._tag1(parts[1])
                is_balear0 = (atkn0.matches_pos_tag_regex(_VERB_BALEAR) and not atkn0.has_pos_tag_starting_with('N')
                              and not atkn0.has_pos_tag_starting_with('S'))
                is_balear1 = (atkn1.matches_pos_tag_regex(_VERB_BALEAR) and not atkn1.has_pos_tag_starting_with('N')
                              and not atkn1.has_pos_tag_starting_with('S'))
                if is_balear0 or is_balear1:
                    continue
                if len(parts[1]) > 1 and parts[0].lower() in _PARTICULA_INICIAL:
                    new_suggestions.insert(pos_new_sugg, suggestions[i])
                    continue
                if len(parts[1]) > 1 and parts[0].lower() in _PRONOM_INICIAL:
                    if atkn1.matches_pos_tag_regex(_VERB_INDSUBJ):
                        new_suggestions.insert(pos_new_sugg, suggestions[i])
                        continue
            sugg_without_diacritics = remove_diacritics(replacement)
            if java_equals_ignore_case(remove_diacritics(word), sugg_without_diacritics):
                new_suggestions.insert(pos_new_sugg, suggestions[i])
                continue
            # move words with apostrophe or hyphen to second position
            clean_suggestion = jregex.java_replace(_QUOTE_OR_HYPHEN, '', replacement)
            if i > 1 and n > 2 and java_equals_ignore_case(clean_suggestion, word):
                if pos_new_sugg == 0:
                    pos_new_sugg = 1
                new_suggestions.insert(pos_new_sugg, suggestions[i])
                continue
            # move "queda'n" to second position, but not anar-se'n
            if i == 1:
                first = suggestions[0]
                if '-' not in first and (first.endswith("'n") or first.endswith("'t")):
                    new_suggestions.insert(0, suggestions[i])
                    continue
            new_suggestions.append(suggestions[i])
        # filter by weight jump
        prev_weight = None
        prev_replacement_str = ''
        filtered_suggestions = []
        for sr in new_suggestions:
            weight = suggestion_weight(sr)
            if not _equals_ignore_case_and_diacritics(sr, prev_replacement_str):
                if weight is not None and prev_weight is not None and weight - prev_weight > _MAX_WEIGHT_DIFF:
                    break
                if weight is not None:
                    prev_weight = weight
            filtered_suggestions.append(sr)
            prev_replacement_str = sr
        return filtered_suggestions

    def get_additional_top_suggestions(self, suggestions, word):
        parts = split_camel_case(word)
        if len(parts) > 1 and len(parts[0]) > 1:
            speller1 = self._init_spellers()
            if all(not speller1.is_misspelled(part) for part in parts):
                return [' '.join(parts)]
        parts = split_digits_at_end(word)
        if len(parts) > 1:
            if (self._tag1(parts[0]).is_tagged()
                    and (len(parts[0]) > 2 or parts[0].lower() in _SPLIT_DIGITS_AT_END)):
                return [' '.join(parts)]
        suggestion = ''
        suggestion = self._find_suggestion(suggestion, word, _APOSTROF_INICI_VERBS, _VERB_INDSUBJ, 2, "'", '')
        suggestion = self._find_suggestion(suggestion, word, _APOSTROF_INICI_VERBS_M, _VERB_INDSUBJ_M, 2, "'", '')
        suggestion = self._find_suggestion(suggestion, word, _APOSTROF_INICI_NOM_SING, _NOM_SING, 2, "'", '')
        suggestion = self._find_suggestion(suggestion, word, _APOSTROF_INICI_NOM_PLURAL, _NOM_PLURAL, 2, "'", '')
        suggestion = self._find_suggestion(suggestion, word, _APOSTROF_FINAL, _VERB_INFGERIMP, 1, "'", '')
        suggestion = self._find_suggestion(suggestion, word, _APOSTROF_FINAL_S, _VERB_INF, 1, "'", '')
        suggestion = self._find_suggestion(suggestion, word, _GUIONET_FINAL_GERUNDI, _VERB_GER, 1, '-', 't')
        suggestion = self._find_suggestion(suggestion, word, _GUIONET_FINAL, _VERB_INFGERIMP, 1, '-', '')
        suggestion = self._find_suggestion_multiple_pronouns(suggestion, word)
        if suggestion:
            return [suggestion]
        return []

    def _find_suggestion(self, suggestion, word, word_pattern, postag_pattern, suggestion_position, separator,
                         add_str):
        if suggestion:
            return suggestion
        m = word_pattern.fullmatch(word)
        if m:
            new_suggestion = m.group(suggestion_position) + add_str
            newatr = self._tag1(new_suggestion)
            if ((not newatr.has_pos_tag('VMIP1S0B') or java_equals_ignore_case(new_suggestion, 'fer')
                 or java_equals_ignore_case(new_suggestion, 'ajust') or java_equals_ignore_case(new_suggestion, 'gran'))
                    and _match_postag_regexp(newatr, postag_pattern)):
                return m.group(1) + add_str + separator + m.group(2)
        return ''

    def _find_suggestion_multiple_pronouns(self, suggestion, word):
        """anarsen -> anar-se'n, danarsen -> d'anar-se'n"""
        if suggestion:
            return suggestion
        lcword = word.lower()
        pronouns = ''
        for pronoun in _PRONOMS_DARRERE:
            if lcword.endswith(pronoun):
                pronouns = pronoun
                break
        verb = lcword[:len(word) - len(pronouns)]
        newatr = self._tag1(verb)
        if _match_postag_regexp(newatr, _VERB_INFGERIMP):
            return verb + transform_darrere(pronouns, verb)
        if len(verb) < 5:
            return ''
        if lcword.startswith('d') or lcword.startswith('l'):
            verb = verb[1:]
            newatr = self._tag1(verb)
            if _match_postag_regexp(newatr, _VERB_INF):
                return lcword[0] + "'" + verb + transform_darrere(pronouns, verb)
        return ''


_multitoken_speller = []
_multitoken_lock = threading.Lock()


def multitoken_dictionary_speller(language):
    """CatalanMorfologikMultitokenSpeller.getSpeller(): the LT
    MorfologikSpeller of /ca/ca-ES_spelling_multitoken.dict (as an object
    with is_misspelled(word) and get_suggestions(word), the latter giving
    (word, weight) pairs), None if the dictionary is not available"""
    with _multitoken_lock:
        if not _multitoken_speller:
            from ...dictionaries import DictionaryNotFound
            from ...spelling import MorfologikSpeller, SpellerMetadata, _FSAWords, _WeightedSpeller
            try:
                dictionary = language.dictionary('ca/ca-ES_spelling_multitoken.dict')
            except DictionaryNotFound:
                _multitoken_speller.append(None)
            else:
                checker = MorfologikSpeller(_FSAWords(dictionary.fsa), SpellerMetadata(dictionary.metadata))
                _multitoken_speller.append(_MultitokenDictSpeller(checker, _WeightedSpeller(dictionary, 1)))
        return _multitoken_speller[0]


class _MultitokenDictSpeller:

    def __init__(self, checker, suggester):
        self._checker = checker
        self._suggester = suggester

    def is_misspelled(self, word):
        return self._checker.is_misspelled(word)

    def get_suggestions(self, word):
        return self._suggester.get_suggestions(word)
