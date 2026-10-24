"""The misspelling check and the spelling suggestions of
org.languagetool.rules.fr.MorfologikFrenchSpellerRule.

Only the check whether a word is misspelled and the suggestions for a single
word (getSpellingSuggestions) are ported (see langtool.spelling), not the
spell checking rule FR_SPELLING_RULE (no rule matches). It is the default
spelling rule of French here, used by
FrenchSuppressMisspelledSuggestionsFilter, FrenchNumberInWordFilter,
FindSuggestionsFilter, InterrogativeVerbFilter, the FrenchMultitokenSpeller
and the MultitokenSpellerFilter. The speller
dictionary is the tagger dictionary fr/french.dict (french-pos-dict); the
word lists fr/hunspell/spelling.txt, spelling_custom.txt, ignore.txt and
prohibit.txt (language-fr) are obtained with the dictionary download
mechanism (langtool.dictionaries)."""

from ... import jregex
from ...spelling import MorfologikMisspellingCheck, MorfologikSuggestions
from ...tools import (java_equals_ignore_case, java_split, java_trim, remove_diacritics, split_camel_case,
                      split_digits_at_end)

_FORM_TAG_SPLIT = jregex.compile('[\t;]')
_SPELLER_EXCEPTIONS = ('Ho Chi Minh',)


def prepare_line_for_speller(line):
    """French.prepareLineForSpeller: lines of the word lists with a tag
    (multiwords.txt) are used only for nouns (N, Z) and adverbs (A); "Ho
    Chi Minh" is not used"""
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
        if tag.startswith('Z') or tag.startswith('N') or tag == 'A':
            return [form]
        return ['']
    return [line]


_CI = jregex.IGNORECASE
_TOKEN_AT_START = frozenset((
    'non', 'en', 'a', 'le', 'la', 'les', 'pour', 'de', 'du', 'des', 'un', 'une', 'mon', 'ma', 'mes', 'ton', 'ta',
    'tes', 'son', 'sa', 'ses', 'leur', 'leurs', 'ce', 'cet'))
_PREFIX_WITH_WHITESPACE = frozenset((
    'agro', 'anti', 'archi', 'auto', 'aéro', 'cardio', 'co', 'cyber', 'demi', 'ex', 'extra', 'géo', 'hospitalo',
    'hydro', 'hyper', 'hypo', 'infra', 'inter', 'macro', 'mega', 'meta', 'mi', 'micro', 'mini', 'mono', 'multi',
    'musculo', 'méga', 'méta', 'néo', 'omni', 'pan', 'para', 'pluri', 'poly', 'post', 'prim', 'pro', 'proto', 'pré',
    'pseudo', 'psycho', 'péri', 're', 'retro', 'ré', 'semi', 'simili', 'socio', 'super', 'supra', 'sus', 'trans',
    'tri', 'télé', 'ultra', 'uni', 'vice', 'éco'))
# grand, haut, nord, sud, sous, sur l|d|s|t
_EXCEPTIONS_EGRAVE = frozenset(('burkinabè', 'koinè', 'épistémè'))
_APOSTROF_INICI_VERBS = jregex.compile('^([lnts])(h?[aeiouàéèíòóú].*[^è])$', _CI)
_APOSTROF_INICI_VERBS_M = jregex.compile('^(m)(h?[aeiouàéèíòóú].*[^è])$', _CI)
_APOSTROF_INICI_VERBS_C = jregex.compile('^(c)([eiéèê].*)$', _CI)
_APOSTROF_INICI_NOM_SING = jregex.compile('^([ld])(h?[aeiouàéèíòóú]...+)$', _CI)
_APOSTROF_INICI_NOM_PLURAL = jregex.compile('^(d)(h?[aeiouàéèíòóú].+)$', _CI)
_APOSTROF_INICI_VERBS_INF = jregex.compile('^([lntsmd]|nous|vous)(h?[aeiouàéèíòóú].*[^è])$', _CI)
# je, tu, il, elle, ce, on, nous, vous, ils
_HYPHEN_ON = jregex.compile("^([\\p{L}]+[^aeiou])[’']?(il|elle|ce|on)$", _CI)
_HYPHEN_JE = jregex.compile("^([\\p{L}]+[^e])[’']?(je)$", _CI)
_HYPHEN_TU = jregex.compile("^([\\p{L}]+)[’']?(tu)$", _CI)
_HYPHEN_NOUS = jregex.compile("^([\\p{L}]+)[’']?(nous)$", _CI)
_HYPHEN_VOUS = jregex.compile("^([\\p{L}]+)[’']?(vous)$", _CI)
_HYPHEN_ILS = jregex.compile("^([\\p{L}]+)[’']?(ils|elles)$", _CI)
_SPLIT_DIGITS_AT_END = frozenset(('et', 'ou', 'de', 'en', 'à', 'aux', 'des'))
_IMPERATIVE_HYPHEN = jregex.compile("^([\\p{L}]+)[’']?(moi|toi|le|la|lui|nous|vous|les|leur|y|en)$", _CI)  # |vs|y
_VERB_INDSUBJ = jregex.compile('V .*(ind|sub).*')
_VERB_IMP = jregex.compile('V.* imp .*')
_VERB_INF = jregex.compile('V.* inf')
_VERB_INDSUBJ_M = jregex.compile('V .* [123] s|V .* [23] p')
_VERB_INDSUBJ_C = jregex.compile('V .* 3 s')
_NOM_SING = jregex.compile('[NJZ] .* (s|sp)|V .inf|V .*ppa.* s')
_NOM_PLURAL = jregex.compile('[NJZ] .* (p|sp)|V .*ppa.* p')
_VERB_1S = jregex.compile('V .*(ind).* 1 s')
_VERB_2S = jregex.compile('V .*(ind).* 2 s')
_VERB_3S = jregex.compile('V .*(ind).* 3 s')
_VERB_1P = jregex.compile('V .*(ind).* 1 p')
_VERB_2P = jregex.compile('V .*(ind).* 2 p')
_VERB_3P = jregex.compile('V .*(ind).* 3 p')
_HYPHEN_OR_QUOTE = jregex.compile("['-]")
_UNITS = (('mm2', 'mm²'), ('cm2', 'cm²'), ('dm2', 'dm²'), ('m2', 'm²'), ('km2', 'km²'), ('mm3', 'mm³'),
          ('cm3', 'cm³'), ('dm3', 'dm³'), ('m3', 'm³'), ('km3', 'km³'))
# the findSuggestion calls of getAdditionalTopSuggestions: (word pattern, POS tag pattern, suggestion
# position, separator)
_FIND_SUGGESTIONS = (
    (_APOSTROF_INICI_VERBS, _VERB_INDSUBJ, 2, "'"),
    (_APOSTROF_INICI_VERBS_M, _VERB_INDSUBJ_M, 2, "'"),
    (_APOSTROF_INICI_VERBS_C, _VERB_INDSUBJ_C, 2, "'"),
    (_APOSTROF_INICI_VERBS_INF, _VERB_INF, 2, "'"),
    (_APOSTROF_INICI_NOM_SING, _NOM_SING, 2, "'"),
    (_APOSTROF_INICI_NOM_PLURAL, _NOM_PLURAL, 2, "'"),
    (_IMPERATIVE_HYPHEN, _VERB_IMP, 1, '-'),
    (_HYPHEN_JE, _VERB_1S, 1, '-'),
    (_HYPHEN_TU, _VERB_2S, 1, '-'),
    (_HYPHEN_ON, _VERB_3S, 1, '-'),
    (_HYPHEN_NOUS, _VERB_1P, 1, '-'),
    (_HYPHEN_VOUS, _VERB_2P, 1, '-'),
    (_HYPHEN_ILS, _VERB_3P, 1, '-'),
)


def _match_postag_regexp(atr, pattern):
    """Match POS tag with regular expression (null tags are "UNKNOWN")"""
    for at in atr.readings:
        pos_tag = at.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if pattern.fullmatch(pos_tag):
            return True
    return False


class MorfologikFrenchSpellerCheck(MorfologikSuggestions, MorfologikMisspellingCheck):
    """The files of MorfologikFrenchSpellerRule (the other ones are the
    defaults of SpellingCheckRule), and its suggestion ordering and
    additional top suggestions."""

    def get_file_name(self):
        return '/fr/french.dict'

    def get_spelling_file_name(self):
        return '/fr/hunspell/spelling.txt'

    def prepare_line_for_speller(self, line):
        return prepare_line_for_speller(line)

    def order_suggestions(self, suggestions, word):
        # move some run-on-words suggestions to the top
        new_suggestions = []
        word_without_diacritics = remove_diacritics(word)
        n = len(suggestions)
        for i, suggestion in enumerate(suggestions):
            parts = java_split(suggestion.lower(), ' ')
            # remove wrong split prefixes
            if len(parts) == 2 and parts[0] in _PREFIX_WITH_WHITESPACE:
                continue
            if len(parts[0]) == 1 and parts[0] != 'a' and parts[0] != 'à' and parts[0] != 'y':
                continue
            # remove: informè V ind pres 1 s
            if suggestion.lower().endswith('è') and suggestion.lower() not in _EXCEPTIONS_EGRAVE:
                continue
            # Don't change first suggestions if they match word without diacritics
            pos_new_sugg = 0
            while (len(new_suggestions) > pos_new_sugg
                   and java_equals_ignore_case(remove_diacritics(new_suggestions[pos_new_sugg]),
                                               word_without_diacritics)):
                pos_new_sugg += 1
            # move some split words to first place
            if len(parts) == 2 and parts[0] in _TOKEN_AT_START and len(parts[1]) > 1:
                new_suggestions.insert(pos_new_sugg, suggestion)
                continue
            sugg_without_diacritics = remove_diacritics(suggestion)
            if java_equals_ignore_case(word_without_diacritics, sugg_without_diacritics):
                new_suggestions.insert(pos_new_sugg, suggestion)
                continue
            # move words with apostrophe or hyphen to second position
            clean_suggestion = jregex.java_replace(_HYPHEN_OR_QUOTE, '', suggestion)
            if i > 1 and n > 2 and java_equals_ignore_case(clean_suggestion, word):
                if pos_new_sugg == 0:
                    pos_new_sugg = 1
                new_suggestions.insert(pos_new_sugg, suggestion)
                continue
            new_suggestions.append(suggestion)
        return new_suggestions

    def get_additional_top_suggestions(self, suggestions, word):
        if word == 'voulai':
            return ['voulais', 'voulait']
        for unit, replacement in _UNITS:
            if java_equals_ignore_case(word, unit):
                return [replacement]
        parts = split_camel_case(word)
        if len(parts) > 1 and len(parts[0]) > 1:
            speller1 = self._init_spellers()
            if all(not speller1.is_misspelled(part) for part in parts):
                return [' '.join(parts)]
        parts = split_digits_at_end(word)
        if len(parts) > 1:
            if (self.language.tagger.tag([parts[0]])[0].is_tagged()
                    and (len(parts[0]) > 2 or parts[0].lower() in _SPLIT_DIGITS_AT_END)):
                return [' '.join(parts)]
        new_suggestions = []
        for word_pattern, postag_pattern, suggestion_position, separator in _FIND_SUGGESTIONS:
            new_suggestions.extend(self._find_suggestion(word, word_pattern, postag_pattern, suggestion_position,
                                                         separator, True))
        return new_suggestions

    def _find_suggestion(self, word, word_pattern, postag_pattern, suggestion_position, separator, recursive):
        new_suggestions = []
        m = word_pattern.fullmatch(word)
        if m:
            new_suggestion = m.group(suggestion_position)
            newatr = self.language.tagger.tag([new_suggestion])[0]
            if _match_postag_regexp(newatr, postag_pattern):
                return [m.group(1) + separator + m.group(2)]
            if recursive:
                # (speller1.getSuggestions: all dictionaries)
                more_sugg = self._suggestion_spellers()[0].get_suggestions(new_suggestion)
                for i, sugg in enumerate(more_sugg):
                    if suggestion_position == 1:
                        new_word = sugg + m.group(2)
                    else:
                        new_word = m.group(1) + sugg
                    new_suggestions.extend(self._find_suggestion(new_word, word_pattern, postag_pattern,
                                                                 suggestion_position, separator, False))
                    if i > 5:
                        break
        return new_suggestions


def spelling_suggestions(language, word):
    """MorfologikFrenchSpellerRule.getSpellingSuggestions(word), the
    suggestions of the rule match for a sentence of the single token word
    (French.getInstance().getDefaultSpellingRule() in Java, used by
    FindSuggestionsFilter, InterrogativeVerbFilter and
    FrenchNumberInWordFilter)"""
    return language.get_default_spelling_rule().get_spelling_suggestions(word)
