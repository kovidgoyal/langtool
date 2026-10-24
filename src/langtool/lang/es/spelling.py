"""The misspelling check of org.languagetool.rules.es.MorfologikSpanishSpellerRule.

Only the check whether a word is misspelled is ported (see
langtool.spelling), not the spell checking rule MORFOLOGIK_RULE_ES (no rule
matches, no suggestions). It is the default spelling rule of Spanish here,
used by SpanishSuppressMisspelledSuggestionsFilter, SpanishNumberInWordFilter,
the SpanishMultitokenSpeller and the MultitokenSpellerFilter. The speller
dictionary is the tagger dictionary es/es-ES.dict (spanish-pos-dict); the
word lists hunspell/spelling.txt, ignore.txt and prohibit.txt are part of
the module's resources."""

from ... import jregex
from ...spelling import MorfologikMisspellingCheck
from ...tools import java_split, java_trim

_FORM_TAG_SPLIT = jregex.compile('[\t;]')


def prepare_line_for_speller(line):
    """Spanish.prepareLineForSpeller: lines of the word lists with a tag
    (multiwords.txt) are used only for nouns, _Latin_ and LOC_ADV"""
    parts = java_split(line, '#')
    if not parts:
        return [line]
    form_tag = _FORM_TAG_SPLIT.split(parts[0])
    while form_tag and form_tag[-1] == '':
        form_tag.pop()
    if len(form_tag) > 1:
        tag = java_trim(form_tag[1])
        if tag.startswith('N') or tag == '_Latin_' or tag == 'LOC_ADV':
            return [java_trim(form_tag[0])]
        return ['']
    return [line]


class MorfologikSpanishSpellerCheck(MorfologikMisspellingCheck):
    """The files of MorfologikSpanishSpellerRule (the other ones are the
    defaults of SpellingCheckRule)."""

    def get_file_name(self):
        return '/es/es-ES.dict'

    def get_additional_spelling_file_names(self):
        # SpellingCheckRule.CUSTOM_SPELLING_FILE is "/hunspell/spelling_custom.txt": Java asks for
        # "/es//hunspell/spelling_custom.txt" (which doesn't exist)
        return ['/es//hunspell/spelling_custom.txt', 'spelling_global.txt', '/es/multiwords.txt']

    def tokenize_new_words(self):
        # Do not tokenize new words from spelling.txt...
        # Multi-token words should be in multiwords.txt
        return False

    def prepare_line_for_speller(self, line):
        return prepare_line_for_speller(line)
