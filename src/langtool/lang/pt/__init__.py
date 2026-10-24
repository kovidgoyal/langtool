"""Portuguese (pt, pt-PT, pt-BR, pt-AO, pt-MZ). Port of the LanguageTool
module language-pt.

The Java module contains org.languagetool.language.Portuguese,
PortugalPortuguese, BrazilianPortuguese, AngolaPortuguese and
MozambiquePortuguese, org.languagetool.tagging.pt.PortugueseTagger,
org.languagetool.tagging.disambiguation.pt.PortugueseHybridDisambiguator,
org.languagetool.synthesis.pt.PortugueseSynthesizer,
org.languagetool.tokenizers.pt.PortugueseWordTokenizer, the rules of
org.languagetool.rules.pt (PortugueseReplaceRule,
PortugueseAgreementReplaceRule, PortugueseOrthographyReplaceRule,
EnglishContractionSpellingRule, PortugalPortugueseReplaceRule,
BrazilianPortugueseReplaceRule, PortugueseArchaismsRule,
PortugueseBarbarismsRule, PortugueseClicheRule, PortugueseRedundancyRule,
PortugueseWordinessRule, PortugueseWikipediaRule, PortugueseDiacriticsRule,
PortugueseWeaselWordsRule, PortugueseWordCoherencyRule,
PortugueseWrongWordInContextRule, PortugueseWordRepeatRule,
PortugueseWordRepeatBeginningRule, PortugueseFillerWordsRule,
PortugueseColourHyphenationRule, PostReformPortugueseCompoundRule,
PreReformPortugueseCompoundRule, PostReformPortugueseDashRule,
PreReformPortugueseDashRule, PortugueseReadabilityRule,
PortugueseUnitConversionRule, PortugueseAccentuationCheckRule with
PortugueseAccentuationDataLoader, MorfologikPortugueseSpellerRule and
PortugueseConfusionProbabilityRule), the filters (AdvancedSynthesizerFilter,
BrazilianToponymFilter with BrazilianToponymMap and
BrazilianToponymMapLoader, ConfusionCheckFilter with
ConfusionPairsDataLoader, DateCheckFilter, YMDDateCheckFilter,
FutureDateFilter, NewYearDateFilter, YMDNewYearDateFilter and
DateFilterHelper, NoDisambiguationPortuguesePartialPosTagFilter,
PortugueseEnclisisFilter, PortugueseProclisisFilter,
PortugueseSuppressMisspelledSuggestionsFilter,
RegularIrregularParticipleFilter and RomanNumeralFilter) and
PortugueseMultitokenSpeller.

The language classes, PortugueseSynthesizer (a plain BaseSynthesizer for
pt/portuguese_synth.dict with pt/portuguese_tags.txt and the number speller
pt/pt.sor) and PortugueseHybridDisambiguator (the MultiWordChunkers for
spelling_global.txt and pt/multiwords.txt followed by the
XmlRuleDisambiguator of pt-PT with the global disambiguation rules) are
ported declaratively in langtool.languages. PortugueseTagger is in
langtool.lang.pt.tagging, PortugueseWordTokenizer in
langtool.lang.pt.tokenizers, the rules in langtool.lang.pt.rules (registered
for 'pt' only), PortugueseAccentuationCheckRule in
langtool.lang.pt.accentuation, the filters in langtool.lang.pt.filters and
PortugueseMultitokenSpeller in langtool.lang.pt.multitoken.
Portuguese.prepareLineForSpeller is in langtool.lang.pt.spelling.

Not ported: MorfologikPortugueseSpellerRule (spell checking), except for its
misspelling check (langtool.lang.pt.spelling, registered as the default
spelling rule of Portuguese), and PortugueseConfusionProbabilityRule
(language model).
"""

from ...extensions import register
from .accentuation import PortugueseAccentuationCheckRule
from .filters import (AdvancedSynthesizerFilter, BrazilianToponymFilter, ConfusionCheckFilter, DateCheckFilter,
                      FutureDateFilter, NewYearDateFilter, NoDisambiguationPortuguesePartialPosTagFilter,
                      PortugueseEnclisisFilter, PortugueseProclisisFilter,
                      PortugueseSuppressMisspelledSuggestionsFilter, RegularIrregularParticipleFilter,
                      RomanNumeralFilter, YMDDateCheckFilter, YMDNewYearDateFilter)
from .rules import (BrazilianPortugueseReplaceRule, EnglishContractionSpellingRule, PortugalPortugueseReplaceRule,
                    PortugueseAgreementReplaceRule, PortugueseArchaismsRule, PortugueseBarbarismsRule,
                    PortugueseClicheRule, PortugueseColourHyphenationRule, PortugueseDiacriticsRule,
                    PortugueseFillerWordsRule, PortugueseOrthographyReplaceRule, PortugueseReadabilityRule,
                    PortugueseRedundancyRule, PortugueseReplaceRule, PortugueseWeaselWordsRule,
                    PortugueseUnitConversionRule, PortugueseWikipediaRule, PortugueseWordCoherencyRule,
                    PortugueseWordinessRule,
                    PortugueseWordRepeatBeginningRule, PortugueseWordRepeatRule, PortugueseWrongWordInContextRule,
                    PostReformPortugueseCompoundRule, PostReformPortugueseDashRule, PreReformPortugueseCompoundRule,
                    PreReformPortugueseDashRule)
from .multitoken import portuguese_multitoken_speller
from .spelling import MorfologikPortugueseSpellerCheck
from .tagging import PortugueseTagger
from .tokenizers import PortugueseWordTokenizer

register('tagger', 'PortugueseTagger',
         lambda language, spec: PortugueseTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='pt')
register('word_tokenizer', 'PortugueseWordTokenizer', lambda language: PortugueseWordTokenizer(language.tagger),
         language='pt')
register('default_spelling_rule', 'pt', MorfologikPortugueseSpellerCheck, language='pt')
register('multitoken_speller', 'pt', portuguese_multitoken_speller, language='pt')

# rules with the Java constructor (messages, language)
for _cls in (PortugueseReplaceRule, PortugueseAgreementReplaceRule, PortugueseOrthographyReplaceRule,
             EnglishContractionSpellingRule, PortugueseWrongWordInContextRule, PortugueseWordRepeatRule,
             PortugueseWordRepeatBeginningRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='pt')
# rules with the Java constructor (messages, path, language)
for _cls in (PortugalPortugueseReplaceRule, BrazilianPortugueseReplaceRule, PortugueseArchaismsRule,
             PortugueseBarbarismsRule, PortugueseClicheRule, PortugueseRedundancyRule, PortugueseWordinessRule,
             PortugueseWikipediaRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, path, _cls=_cls: _cls(messages, path, language), language='pt')
# rules with the Java constructor (messages, language, userConfig)
for _cls in (PortugueseFillerWordsRule, PortugueseColourHyphenationRule, PostReformPortugueseCompoundRule,
             PreReformPortugueseCompoundRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language, user_config),
             language='pt')
# (Java: new PortugueseReadabilityRule(messages, language, userConfig, tooEasyTest))
register('rule', 'PortugueseReadabilityRule',
         lambda messages, language, user_config, too_easy_test: PortugueseReadabilityRule(
             messages, language, user_config, too_easy_test), language='pt')
# rules with the Java constructor (messages); the language is used to find the data files
for _cls in (PortugueseDiacriticsRule, PortugueseWeaselWordsRule, PortugueseWordCoherencyRule,
             PortugueseUnitConversionRule, PortugueseAccentuationCheckRule, PostReformPortugueseDashRule,
             PreReformPortugueseDashRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='pt')

_P = 'org.languagetool.rules.pt.'
for _cls in (AdvancedSynthesizerFilter, ConfusionCheckFilter, DateCheckFilter, YMDDateCheckFilter, FutureDateFilter,
             NewYearDateFilter, YMDNewYearDateFilter, NoDisambiguationPortuguesePartialPosTagFilter,
             PortugueseEnclisisFilter, PortugueseProclisisFilter, PortugueseSuppressMisspelledSuggestionsFilter,
             RegularIrregularParticipleFilter, RomanNumeralFilter):
    register('filter', _P + _cls.__name__, _cls)
register('regex_filter', _P + 'BrazilianToponymFilter', BrazilianToponymFilter)
