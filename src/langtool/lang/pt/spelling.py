"""The misspelling check of org.languagetool.rules.pt.MorfologikPortugueseSpellerRule.

Only the check whether a word is misspelled is ported (see
langtool.spelling), not the spell checking rule MORFOLOGIK_RULE_PT_* (no
rule matches, no suggestions, no dialect alternatives). It is the default
spelling rule of Portuguese here, used by
PortugueseSuppressMisspelledSuggestionsFilter, the
PortugueseMultitokenSpeller and the MultitokenSpellerFilter. The speller
dictionaries pt/spelling/pt-BR.dict, pt-PT-90.dict and pt-PT-45.dict
(portuguese-pos-dict) and the word lists pt/spelling.txt, pt/ignore.txt and
pt/prohibit.txt (language-pt) are obtained with the dictionary download
mechanism (langtool.dictionaries)."""

from ... import jregex
from ...spelling import MorfologikMisspellingCheck
from ...tools import java_split, java_trim

_FORM_TAG_SPLIT = jregex.compile('[\t;]')


def prepare_line_for_speller(line):
    """Portuguese.prepareLineForSpeller: lines of the word lists with a tag
    (multiwords.txt) are used only for nouns and _Latin_"""
    parts = java_split(line, '#')
    if not parts:
        return [line]
    form_tag = _FORM_TAG_SPLIT.split(parts[0])
    while form_tag and form_tag[-1] == '':
        form_tag.pop()
    form = java_trim(form_tag[0]) if form_tag else ''
    if len(form_tag) > 1:
        tag = java_trim(form_tag[1])
        if tag.startswith('N') or tag == '_Latin_':
            return [form]
        return ['']
    return [line]


def speller_dictionary(language):
    """MorfologikPortugueseSpellerRule.getDictFilename for the speller
    language (the default variant pt-PT for pt): pt-BR with the 1990
    spelling by default, pt-PT-90 for pt-PT, pt-PT-45 for pt-AO and
    pt-MZ"""
    code = language.short_code_with_country_and_variant
    if code == 'pt':
        code = language.default_variant.short_code_with_country_and_variant
    if code == 'pt-PT':
        return 'pt-PT-90'
    if code in ('pt-AO', 'pt-MZ'):
        return 'pt-PT-45'
    return 'pt-BR'


class MorfologikPortugueseSpellerCheck(MorfologikMisspellingCheck):
    """The files of MorfologikPortugueseSpellerRule (the other ones are the
    defaults of SpellingCheckRule)."""

    def get_file_name(self):
        return '/pt/spelling/' + speller_dictionary(self.language) + '.dict'

    def get_ignore_file_name(self):
        return 'pt/ignore.txt'

    def get_prohibit_file_name(self):
        return 'pt/prohibit.txt'

    def get_additional_spelling_file_names(self):
        return ['spelling_global.txt', 'pt/spelling.txt', 'pt/multiwords.txt']

    def prepare_line_for_speller(self, line):
        return prepare_line_for_speller(line)
