"""French (fr, fr-CA, fr-CH, fr-BE). Port of the LanguageTool module
language-fr.

The Java module contains org.languagetool.language.French, BelgianFrench,
CanadianFrench and SwissFrench, org.languagetool.tagging.fr.FrenchTagger,
org.languagetool.tagging.disambiguation.fr.FrenchHybridDisambiguator,
org.languagetool.synthesis.FrenchSynthesizer,
org.languagetool.tokenizers.fr.FrenchWordTokenizer, the rules
org.languagetool.rules.fr.CompoundRule, FrenchRepeatedWordsRule,
QuestionWhitespaceRule, QuestionWhitespaceStrictRule, SimpleReplaceRule,
GrammalecteRule, MorfologikFrenchSpellerRule and
FrenchConfusionProbabilityRule, the filters AdvancedSynthesizerFilter,
DateCheckFilter, DMYDateCheckFilter, NewYearDateFilter (with
DateFilterHelper), FindSuggestionsFilter, FrenchNumberInWordFilter,
FrenchPartialPosTagFilter, FrenchSuppressMisspelledSuggestionsFilter,
InterrogativeVerbFilter, MakeContractionsFilter,
PostponedAdjectiveConcordanceFilter, SuggestionsFilter and
WordWithDeterminerFilter, and FrenchMultitokenSpeller.

French and its variants and FrenchHybridDisambiguator (the
MultiWordChunkers for spelling_global.txt and fr/multiwords.txt followed by
the XmlRuleDisambiguator with the global disambiguation rules) are ported
declaratively in langtool.languages, French.toAdvancedTypography and
French.filterRuleMatches in langtool.lang.fr.language. FrenchTagger is in
langtool.lang.fr.tagging, FrenchSynthesizer in langtool.lang.fr.synthesis,
FrenchWordTokenizer in langtool.lang.fr.tokenizers, the rules in
langtool.lang.fr.rules (registered for 'fr' only, other languages have rule
classes with the same names), PostponedAdjectiveConcordanceFilter in
langtool.lang.fr.agreement, the other filters in langtool.lang.fr.filters
and FrenchMultitokenSpeller in langtool.lang.fr.multitoken.

Not ported: MorfologikFrenchSpellerRule (spell checking), except for its
misspelling check (langtool.lang.fr.spelling, registered as the default
spelling rule of French), FrenchConfusionProbabilityRule (language model)
and GrammalecteRule (a remote rule, only used with a Grammalecte server
configured in the GlobalConfig). French.filterRuleMatches and
adjustFrenchRuleMatch are ported except for the parts that only change the
matches of the remote AI rules (AI_FR_GGEC_*); French.hasMinMatchesRules()
is not used by LanguageTool.
"""

from ...extensions import register, synthesizer_resources
from .agreement import PostponedAdjectiveConcordanceFilter
from .filters import (AdvancedSynthesizerFilter, DateCheckFilter, DMYDateCheckFilter, FindSuggestionsFilter,
                      FrenchNumberInWordFilter, FrenchPartialPosTagFilter, FrenchSuppressMisspelledSuggestionsFilter,
                      InterrogativeVerbFilter, MakeContractionsFilter, NewYearDateFilter, SuggestionsFilter,
                      WordWithDeterminerFilter)
from .language import filter_rule_matches, to_advanced_typography
from .multitoken import french_multitoken_speller
from .rules import (CompoundRule, FrenchRepeatedWordsRule, QuestionWhitespaceRule, QuestionWhitespaceStrictRule,
                    SimpleReplaceRule)
from .spelling import MorfologikFrenchSpellerCheck
from .synthesis import FrenchSynthesizer
from .tagging import FrenchTagger
from .tokenizers import FrenchWordTokenizer


def _synthesizer(language, spec):
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return FrenchSynthesizer(dictionary, tags_path, 'fr', language.resource_dir, number_speller, roman_numberer)


register('tagger', 'FrenchTagger',
         lambda language, spec: FrenchTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='fr')
register('synthesizer', 'FrenchSynthesizer', _synthesizer, language='fr')
register('word_tokenizer', 'FrenchWordTokenizer', lambda language: FrenchWordTokenizer(language.tagger),
         language='fr')
register('default_spelling_rule', 'fr', MorfologikFrenchSpellerCheck, language='fr')
register('multitoken_speller', 'fr', french_multitoken_speller, language='fr')
register('to_advanced_typography', 'fr', to_advanced_typography, language='fr')
register('filter_rule_matches', 'fr', filter_rule_matches, language='fr')
register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='fr')
# (Java: new FrenchRepeatedWordsRule(messages), for French.getInstance())
register('rule', 'FrenchRepeatedWordsRule',
         lambda messages, language, user_config: FrenchRepeatedWordsRule(messages), language='fr')
for _cls in (QuestionWhitespaceRule, QuestionWhitespaceStrictRule, SimpleReplaceRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='fr')
_P = 'org.languagetool.rules.fr.'
for _cls in (AdvancedSynthesizerFilter, DateCheckFilter, DMYDateCheckFilter, FindSuggestionsFilter,
             FrenchNumberInWordFilter, FrenchPartialPosTagFilter, FrenchSuppressMisspelledSuggestionsFilter,
             InterrogativeVerbFilter, MakeContractionsFilter, NewYearDateFilter, PostponedAdjectiveConcordanceFilter,
             SuggestionsFilter, WordWithDeterminerFilter):
    register('filter', _P + _cls.__name__, _cls)
