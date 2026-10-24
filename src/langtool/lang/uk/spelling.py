"""The misspelling check and the speller suggestions of
org.languagetool.rules.uk.MorfologikUkrainianSpellerRule.

Only the check whether a word is misspelled and the suggestions (see
langtool.spelling) are ported, not the spell checking rule
MORFOLOGIK_RULE_UK_UA itself (no rule matches). It is the default spelling
rule of Ukrainian here; SimpleReplaceRule asks its speller1 for suggestions
for words tagged as :bad (getSpeller1().getSuggestionsFromDefaultDicts()).
The speller dictionary uk/hunspell/uk_UA.dict (morfologik-ukrainian-lt) and
the word lists uk/hunspell/spelling.txt and ignore.txt (language-uk) are
obtained with the dictionary download mechanism (langtool.dictionaries)."""

from ... import jregex
from ...rules.abstract_rules import java_hash_set_order
from ...spelling import MorfologikMisspellingCheck, MorfologikSuggestions
from ...tools import is_capitalized_word
from . import helpers

_DO_NOT_SUGGEST_SPACED_PATTERN = jregex.compile(
    '(авіа|авто|анти|аудіо|відео|водо|гідро|екстра|квазі|кіно|лже|мета|моно|мото|псевдо|пост|радіо|стерео|супер'
    '|ультра|фото) .*')
_BAD_ALT_SLANG = jregex.compile(':(bad|alt|slang)')
_UK_PREFIX = jregex.compile('[а-яіїєґ]{3,}')
_dash_prefixes_2019 = None


def _dash_prefixes2019():
    """The prefixes of dash_prefixes.txt that are written with a hyphen (in
    the iteration order of the Java HashMap, as far as it matters)"""
    global _dash_prefixes_2019
    if _dash_prefixes_2019 is None:
        m = helpers.load_map('/uk/dash_prefixes.txt')
        keys = [k for k in java_hash_set_order(list(m))
                if not _BAD_ALT_SLANG.fullmatch(m[k]) and _UK_PREFIX.fullmatch(k)]
        _dash_prefixes_2019 = keys
    return _dash_prefixes_2019


class MorfologikUkrainianSpellerCheck(MorfologikSuggestions, MorfologikMisspellingCheck):
    """The files and the overrides of MorfologikUkrainianSpellerRule that
    concern the misspelling check and the suggestions (the word lists are
    the defaults of SpellingCheckRule: uk/hunspell/spelling.txt,
    ignore.txt, ...)."""

    def get_file_name(self):
        return '/uk/hunspell/uk_UA.dict'

    def is_latin_script(self):
        return False

    def is_misspelled(self, word):
        if word.endswith('-'):
            return not word.startswith('-')
        return super().is_misspelled(word)

    def get_additional_suggestions(self, suggestions, word):
        if is_capitalized_word(word):
            word = word.lower()
        for key in _dash_prefixes2019():
            if word.startswith(key) and len(word) > len(key) + 2 and word[len(key)] != '-':
                suggestions.append(key + '-' + word[len(key):])
        return suggestions

    def filter_suggestions(self, suggestions):
        suggestions = super().filter_suggestions(suggestions)
        # do not suggest "кіно прокат, вело- прогулянка...":
        return [s for s in suggestions
                if not ((' ' in s and _DO_NOT_SUGGEST_SPACED_PATTERN.fullmatch(s)) or '- ' in s)]

    def speller1_suggestions_from_default_dicts(self, word):
        """getSpeller1().getSuggestionsFromDefaultDicts(word)"""
        speller1 = self._suggestion_spellers()[0]
        return [w for w, _weight in speller1.get_weighted_suggestions_from_default_dicts(word)]
