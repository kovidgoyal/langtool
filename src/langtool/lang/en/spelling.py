"""The misspelling check of org.languagetool.rules.en.AbstractEnglishSpellerRule
and its subclasses MorfologikAmericanSpellerRule, MorfologikBritishSpellerRule,
MorfologikCanadianSpellerRule, MorfologikAustralianSpellerRule,
MorfologikNewZealandSpellerRule and MorfologikSouthAfricanSpellerRule,
English.prepareLineForSpeller and EnglishMultitokenSpeller.

Only the check whether a word is misspelled (and the single word spelling
suggestions used by EnglishNumberInWordFilter, see langtool.spelling) is
ported, not the spell checking rules MORFOLOGIK_RULE_EN_* (no rule matches).
They are the default spelling rules of the English variants here (English
itself uses the American one, as in Java), used by CompoundRule,
EnglishNumberInWordFilter, EnglishSuppressMisspelledSuggestionsFilter, the
EnglishMultitokenSpeller and the MultitokenSpellerFilter. The speller
dictionaries en/hunspell/en_US.dict etc. (english-pos-dict) and the word
lists en/hunspell/spelling.txt, spelling_custom.txt, spelling_en-US.txt
etc., ignore.txt, prohibit.txt and prohibit_custom.txt (language-en) are
obtained with the dictionary download mechanism (langtool.dictionaries)."""

import threading

from ... import jregex
from ...analysis import AnalyzedToken
from ...rules.multitoken import MultitokenSpeller
from ...spelling import MorfologikMisspellingCheck, MorfologikSuggestions
from ...tools import java_split, java_trim, starts_with_uppercase, uppercase_first_char
from .speller_data import LC_DO_NOT_SUGGEST_WORDS, ONLY_SUGGESTIONS, TOP_SUGGESTIONS, TOP_SUGGESTIONS_IGNORE_CASE


def prepare_line_for_speller(line):
    """English.prepareLineForSpeller: lines of the word lists with a tag
    (multiwords.txt) are used only for nouns and adjectives (NN*, JJ*),
    lines with a '+' are not used"""
    parts = java_split(line, '#')
    if not parts:
        return [line]
    if '+' in line:
        # while the morfologik separator is "+", multiwords with '+' can cause undesired results.
        return ['']
    form_tag = java_split(parts[0], '\t')
    form = java_trim(form_tag[0]) if form_tag else ''
    if len(form_tag) > 1:
        tag = java_trim(form_tag[1])
        if tag.startswith('NN') or tag.startswith('JJ'):
            return [form]
        return ['']
    return [line]


# speller dictionary and word list of the variants (the RESOURCE_FILENAME and
# LANGUAGE_SPECIFIC_PLAIN_TEXT_DICT of the speller rules)
_VARIANT_FILES = {
    'en-US': ('/en/hunspell/en_US.dict', 'en/hunspell/spelling_en-US.txt'),
    'en-GB': ('/en/hunspell/en_GB.dict', 'en/hunspell/spelling_en-GB.txt'),
    'en-CA': ('/en/hunspell/en_CA.dict', 'en/hunspell/spelling_en-CA.txt'),
    'en-AU': ('/en/hunspell/en_AU.dict', 'en/hunspell/spelling_en-AU.txt'),
    'en-NZ': ('/en/hunspell/en_NZ.dict', 'en/hunspell/spelling_en-NZ.txt'),
    'en-ZA': ('/en/hunspell/en_ZA.dict', 'en/hunspell/spelling_en-ZA.txt'),
}


_CONTAINS_TOKEN = jregex.compile('.* (b|c|d|e|f|g|h|j|k|l|m|n|o|p|q|r|s|t|v|w|y|z|ll|ve)')
_ONLY_SUGGESTIONS = tuple((jregex.compile(p), suggestions) for p, suggestions in ONLY_SUGGESTIONS)
_YS_END = jregex.compile('ys$')
# cleanSuggestions: suggestions of several words are not used if they start/end with these
_CLEAN_LC_PREFIXES = tuple(p + ' ' for p in (
    're', 'en', 'co', 'cl', 'de', 'ex', 'es', 'ab', 'ty', 'mid', 'non', 'bio', 'bi', 'op', 'con', 'pre', 'mis',
    'socio', 'proto', 'neo', 'geo', 'inter', 'multi', 'retro', 'extra', 'mega', 'meta', 'poly', 'para', 'uni',
    'anti', 'necro', 'photo', 'post', 'sub', 'auto', 'pl', 'ht', 'dis', 'est', 'mono', 'trans', 'neuro', 'hetero',
    'ultra', 'mini', 'hyper', 'micro', 'counter', 'over', 'overs', 'overt', 'under', 'cyber', 'hydro', 'ergo',
    'fore', 'pro', 'pseudo', 'psycho', 'mi', 'nano', 'ans', 'semi', 'infra', 'hypo', 'syn', 'adv', 'com', 'res',
    'resp', 'lo', 'ed', 'ac', 'al', 'ea', 'ge', 'mu', 'ma', 'la', 'bis', 'ger', 'inf', 'tar', 'f', 'k', 'l', 'b',
    'e', 'c', 'd', 'p', 'v', 'h', 'r', 's', 't', 'u', 'w', 'um', 'oft'))
_CLEAN_PREFIXES = ('i ', 'sh ', 'li ', 'ha ', 'st ', 'ins ')
_CLEAN_SUFFIXES = tuple(' ' + x for x in (
    'i', 'ING', 'able', 'om', 'ox', 'ht', 'wide', 'less', 'sly', 'OO', 'HHH', 'ally', 'ize', 'sh', 'st', 'est', 'em',
    'ward', 'ability', 'ware', 'logy', 'ting', 'ion', 'ions', 'cal', 'ted', 'sphere', 'ell', 'co', 'con', 'com',
    'sis', 'like', 'full', 'en', 'ne', 'ed', 'al', 'ans', 'mans', 'ti', 'de', 'ea', 'ge', 'ab', 'rs', 'mi', 'tar',
    'adv', 're', 'e', 'c', 'v', 'h', 's', 'r', 'l', 'u', 'um', 'er', 'es', 'ex', 'na', 'ifs', 'gs', 'don', 'dons',
    'la', 'ism', 'ma'))


def _clean_suggestion(rep):
    """AbstractEnglishSpellerRule.cleanSuggestions: whether the suggestion is
    kept (filter "re ..." etc., #2562)"""
    if ' ' not in rep:
        return True
    rep_lc = rep.lower()
    return not (rep_lc.startswith(_CLEAN_LC_PREFIXES) or rep.startswith(_CLEAN_PREFIXES)
                or rep.endswith(_CLEAN_SUFFIXES))


_word_lists = {}
_word_lists_lock = threading.Lock()


def load_word_list(language, path, column):
    """AbstractEnglishSpellerRule.loadWordlist: the lines of path (in the
    resource directory) are 'word;word', the word of column (lowercase) is
    mapped to the other one"""
    if column not in (0, 1):
        raise ValueError('Only column 0 and 1 are supported: %s' % column)
    key = (language.resource_path(path), column)
    with _word_lists_lock:
        words = _word_lists.get(key)
        if words is None:
            words = {}
            with open(key[0], encoding='utf-8') as f:
                for line in f.read().splitlines():
                    line = java_trim(line)
                    if not line or line.startswith('#'):
                        continue
                    parts = java_split(line, ';')
                    if len(parts) != 2:
                        raise ValueError("Unexpected format in %s: %s - expected two parts delimited by ';'" % (
                            path, line))
                    words[parts[column].lower()] = parts[1 if column == 0 else 0]
            _word_lists[key] = words
        return words


class AbstractEnglishSpellerCheck(MorfologikSuggestions, MorfologikMisspellingCheck):
    """The misspelling check of AbstractEnglishSpellerRule: the speller
    dictionary of the variant (variant_code, the class of the Java rule)
    with the word lists spelling.txt, spelling_custom.txt,
    spelling_global.txt, multiwords.txt (nouns and adjectives) and the one
    of the variant; compounds are accepted if all their parts are spelled
    correctly; words of one character are ignored. The word list of the
    language (e.g. spelling_en-US.txt for en-US) is also added to the
    ignored words."""

    variant_code = None
    check_compound = True
    ignore_words_with_length = 1

    def get_file_name(self):
        return _VARIANT_FILES[self.variant_code][0]

    def get_language_variant_spelling_file_name(self):
        return _VARIANT_FILES[self.variant_code][1]

    def get_additional_spelling_file_names(self):
        # NOTE: also add to GermanSpellerRule.getSpeller() when adding items here:
        return [self.language.short_code + '/hunspell/spelling_custom.txt', 'spelling_global.txt',
                '/en/multiwords.txt']

    def get_additional_ignore_file_names(self):
        # (constructor of AbstractEnglishSpellerRule)
        return [self.get_spelling_file_name().replace('.txt', '_' + self.language.short_code_with_country_and_variant
                                                      + '.txt')]

    def tokenize_new_words(self):
        # Do not tokenize new words from spelling.txt...
        # Multi-token words should be in multiwords.txt
        return False

    def prepare_line_for_speller(self, line):
        return prepare_line_for_speller(line)

    # --- suggestions ---

    def is_valid_in_other_variant(self, word):
        """isValidInOtherVariant: (variant name, the word in this variant) if
        the word is a spelling of another variant (en/en-US-GB.txt), None
        otherwise"""
        other_variant = load_word_list(self.language, 'en/en-US-GB.txt', 0).get(word.lower())
        if other_variant is not None:
            return 'American English', other_variant
        return None

    def filter_no_suggest_words(self, suggestions):
        return [s for s in suggestions if s.lower() not in LC_DO_NOT_SUGGEST_WORDS]

    def filter_suggestions(self, suggestions):
        # e.g. 'timezones' suggests 'timezone s'
        return [s for s in super().filter_suggestions(suggestions) if not _CONTAINS_TOKEN.fullmatch(s)]

    def get_only_suggestions(self, word):
        # NOTE: only add words here that would otherwise have more than one suggestion
        # and have apply to all variants of English (en-US, en-GB, ...):
        for pattern, suggestions in _ONLY_SUGGESTIONS:
            if pattern.fullmatch(word):
                # (StringUtils.replaceOnce for the (substring, replacement) pairs)
                return [s if isinstance(s, str) else word.replace(s[0], s[1], 1) for s in suggestions]
        return []

    def get_additional_top_suggestions(self, suggestions, word):
        curated_suggestions = list(TOP_SUGGESTIONS.get(word, ()))
        curated_suggestions.extend(TOP_SUGGESTIONS_IGNORE_CASE.get(word.lower(), ()))
        if curated_suggestions:
            return curated_suggestions
        if word.endswith('ys'):
            suggestion = jregex.java_replace(_YS_END, 'ies', word, 1)
            if not self._init_spellers().is_misspelled(suggestion):
                return [suggestion]
        return super().get_additional_top_suggestions(suggestions, word)

    def add_hyphen_suggestions(self, parts, top_suggestions):
        # trivial approach that assumes only one part of the hyphenated word has a typo...
        speller1, speller2 = self._suggestion_spellers()[:2]
        for i, part in enumerate(parts):
            if self.is_misspelled(part):
                part_suggestions = speller1.get_suggestions(part)
                if not part_suggestions:
                    part_suggestions = speller2.get_suggestions(part)
                if part_suggestions:
                    top_suggestions.append('-'.join(part_suggestions[0] if j == i else p
                                                    for j, p in enumerate(parts)))

    def _irregular_forms(self, word):
        """getIrregularFormsOrNull: the forms of a word with a regular ending
        that is misspelled ('readed' -> 'read'), or None"""
        for word_suffix, suffix, pos_tag in (('ed', 'ed', 'VBD'), ('ed', 'd', 'VBD'), ('s', 's', 'NNS'),
                                             ('es', 'es', 'NNS'), ('er', 'er', 'JJR'), ('est', 'est', 'JJS')):
            if word.endswith(word_suffix):
                base_form = word[:len(word) - len(suffix)]
                forms = self.language.synthesizer.synthesize(AnalyzedToken(word, None, base_form), pos_tag)
                speller1 = self._init_spellers()
                # only accept suggestions that the spellchecker will accept
                result = [form for form in forms if not speller1.is_misspelled(form)]
                # the internal dict might contain forms that the spell checker doesn't accept (e.g. 'criterions'),
                # but we trust the spell checker in this case:
                for w in (word, 'badder', 'baddest', 'spake'):  # non-standard usage, can be removed after dict update
                    if w in result:
                        result.remove(w)
                if result:
                    return result
        return None

    def _rule_match_suggestions(self, word):
        # AbstractEnglishSpellerRule.getRuleMatches
        suggestions = super()._rule_match_suggestions(word)
        if suggestions is None:
            return None
        # so 'word' is misspelled:
        forms = self._irregular_forms(word)
        if forms is not None:
            suggestions = list(dict.fromkeys(forms + suggestions))
        else:
            variant_info = self.is_valid_in_other_variant(word)
            if variant_info is not None:
                other_variant = variant_info[1]
                suggestions = [uppercase_first_char(other_variant) if starts_with_uppercase(word) else other_variant]
        # filter "re ..." (#2562):
        return [s for s in suggestions if _clean_suggestion(s)]


class MorfologikAmericanSpellerCheck(AbstractEnglishSpellerCheck):
    """MorfologikAmericanSpellerRule (MORFOLOGIK_RULE_EN_US)"""
    variant_code = 'en-US'

    def is_valid_in_other_variant(self, word):
        other_variant = load_word_list(self.language, 'en/en-US-GB.txt', 1).get(word.lower())
        if other_variant is not None:
            return 'British English', other_variant
        return None

    def get_additional_top_suggestions(self, suggestions, word):
        s = {'automize': 'automate', 'automized': 'automated', 'automizing': 'automating',
             'automizes': 'automates'}.get(word)
        if s is not None:
            return [s]
        return super().get_additional_top_suggestions(suggestions, word)


class MorfologikBritishSpellerCheck(AbstractEnglishSpellerCheck):
    """MorfologikBritishSpellerRule (MORFOLOGIK_RULE_EN_GB)"""
    variant_code = 'en-GB'


class MorfologikCanadianSpellerCheck(AbstractEnglishSpellerCheck):
    """MorfologikCanadianSpellerRule (MORFOLOGIK_RULE_EN_CA)"""
    variant_code = 'en-CA'


class MorfologikAustralianSpellerCheck(AbstractEnglishSpellerCheck):
    """MorfologikAustralianSpellerRule (MORFOLOGIK_RULE_EN_AU)"""
    variant_code = 'en-AU'


class MorfologikNewZealandSpellerCheck(AbstractEnglishSpellerCheck):
    """MorfologikNewZealandSpellerRule (MORFOLOGIK_RULE_EN_NZ)"""
    variant_code = 'en-NZ'


class MorfologikSouthAfricanSpellerCheck(AbstractEnglishSpellerCheck):
    """MorfologikSouthAfricanSpellerRule (MORFOLOGIK_RULE_EN_ZA)"""
    variant_code = 'en-ZA'


_SPELLER_CHECKS = {
    'en-US': MorfologikAmericanSpellerCheck, 'en-GB': MorfologikBritishSpellerCheck,
    'en-CA': MorfologikCanadianSpellerCheck, 'en-AU': MorfologikAustralianSpellerCheck,
    'en-NZ': MorfologikNewZealandSpellerCheck, 'en-ZA': MorfologikSouthAfricanSpellerCheck,
}


def english_default_spelling_rule(language):
    """createDefaultSpellingRule of the English language classes (English
    itself uses MorfologikAmericanSpellerRule)"""
    return _SPELLER_CHECKS.get(language.code, MorfologikAmericanSpellerCheck)(language)


class EnglishMultitokenSpeller(MultitokenSpeller):
    """Port of org.languagetool.rules.en.EnglishMultitokenSpeller: the
    MultitokenSpeller for /en/multiwords.txt and /spelling_global.txt (the
    lines are prepared with English.prepareLineForSpeller)."""

    def prepare_line_for_speller(self, s):
        return prepare_line_for_speller(s)


_instance = []
_lock = threading.Lock()


def english_multitoken_speller(language):
    """EnglishMultitokenSpeller.INSTANCE, for the language en (whose
    default spelling rule is used) in Java, for all variants"""
    with _lock:
        if not _instance:
            from ...api import get_language
            en = get_language('en')
            _instance.append(EnglishMultitokenSpeller(
                en, [en.resource_path('en/multiwords.txt'), en.resource_path('spelling_global.txt')],
                en.get_default_spelling_rule()))
        return _instance[0]
