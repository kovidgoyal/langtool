"""Spanish (es, es-AR). Port of the LanguageTool module language-es.

The Java module contains org.languagetool.language.Spanish and
SpanishVoseo, org.languagetool.tagging.es.SpanishTagger,
org.languagetool.tagging.disambiguation.es.SpanishHybridDisambiguator,
org.languagetool.synthesis.es.SpanishSynthesizer,
org.languagetool.tokenizers.es.SpanishWordTokenizer, the rules
org.languagetool.rules.es.CompoundRule, QuestionMarkRule, SimpleReplaceRule,
SimpleReplaceVerbsRule, SpanishRepeatedWordsRule, SpanishUnpairedBracketsRule,
SpanishWikipediaRule, SpanishWordRepeatBeginningRule, SpanishWordRepeatRule,
SpanishWrongWordInContextRule, MorfologikSpanishSpellerRule and
SpanishConfusionProbabilityRule, the filters AdvancedSynthesizerFilter,
ConfusionCheckFilter (with ConfusionPairsDataLoader), DateCheckFilter,
NewYearDateFilter (with DateFilterHelper), FindSuggestionsFilter,
PostponedAdjectiveConcordanceFilter, SpanishNumberInWordFilter,
SpanishSuppressMisspelledSuggestionsFilter and TextToNumberFilter, and
SpanishMultitokenSpeller.

Spanish, SpanishVoseo and SpanishHybridDisambiguator (the MultiWordChunkers
for spelling_global.txt and es/multiwords.txt followed by the
XmlRuleDisambiguator with the global disambiguation rules) are ported
declaratively in langtool.languages. SpanishTagger is in
langtool.lang.es.tagging, SpanishSynthesizer in langtool.lang.es.synthesis,
SpanishWordTokenizer in langtool.lang.es.tokenizers, the rules in
langtool.lang.es.rules (registered for 'es' only, other languages have rule
classes with the same names), PostponedAdjectiveConcordanceFilter in
langtool.lang.es.agreement, the other filters in langtool.lang.es.filters
and SpanishMultitokenSpeller in langtool.lang.es.multitoken.
Spanish.adaptSuggestion (contractions "a el" -> "al", "de el" -> "del") is
registered as the 'adapt_suggestion' of es.

Not ported: MorfologikSpanishSpellerRule (spell checking), except for its
misspelling check (langtool.lang.es.spelling, registered as the default
spelling rule of Spanish), and SpanishConfusionProbabilityRule (language
model). Spanish.filterRuleMatches only changes the matches of the remote
AI rules (AI_ES_GGEC_*), which are not ported, so it is not needed;
Spanish.hasMinMatchesRules() is not used by LanguageTool.
"""

from ... import jregex
from ...extensions import register, synthesizer_resources
from .agreement import PostponedAdjectiveConcordanceFilter
from .filters import (AdvancedSynthesizerFilter, ConfusionCheckFilter, DateCheckFilter, FindSuggestionsFilter,
                      NewYearDateFilter, SpanishNumberInWordFilter, SpanishSuppressMisspelledSuggestionsFilter,
                      TextToNumberFilter)
from .multitoken import spanish_multitoken_speller
from .rules import (CompoundRule, QuestionMarkRule, SimpleReplaceRule, SimpleReplaceVerbsRule,
                    SpanishRepeatedWordsRule, SpanishUnpairedBracketsRule, SpanishWikipediaRule,
                    SpanishWordRepeatBeginningRule, SpanishWordRepeatRule, SpanishWrongWordInContextRule)
from .spelling import MorfologikSpanishSpellerCheck
from .synthesis import SpanishSynthesizer
from .tagging import SpanishTagger
from .tokenizers import SpanishWordTokenizer

_ES_CONTRACTIONS = jregex.compile('\\b([Aa]|[Dd]e) e(l)\\b')


def adapt_suggestion(language, replacement, original_error_str):
    """Spanish.adaptSuggestion"""
    return jregex.java_replace(_ES_CONTRACTIONS, '$1$2', replacement)


def _synthesizer(language, spec):
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return SpanishSynthesizer(dictionary, tags_path, 'es', language.resource_dir, number_speller, roman_numberer)


register('tagger', 'SpanishTagger',
         lambda language, spec: SpanishTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='es')
register('synthesizer', 'SpanishSynthesizer', _synthesizer, language='es')
register('word_tokenizer', 'SpanishWordTokenizer', lambda language: SpanishWordTokenizer(language.tagger),
         language='es')
register('default_spelling_rule', 'es', MorfologikSpanishSpellerCheck, language='es')
register('multitoken_speller', 'es', spanish_multitoken_speller, language='es')
register('adapt_suggestion', 'es', adapt_suggestion, language='es')
for _cls in (CompoundRule, SpanishWordRepeatBeginningRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='es')
for _cls in (QuestionMarkRule, SimpleReplaceRule, SimpleReplaceVerbsRule, SpanishRepeatedWordsRule,
             SpanishUnpairedBracketsRule, SpanishWikipediaRule, SpanishWordRepeatRule,
             SpanishWrongWordInContextRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='es')
_P = 'org.languagetool.rules.es.'
register('filter', _P + 'AdvancedSynthesizerFilter', AdvancedSynthesizerFilter)
register('filter', _P + 'ConfusionCheckFilter', ConfusionCheckFilter)
register('filter', _P + 'DateCheckFilter', DateCheckFilter)
register('filter', _P + 'FindSuggestionsFilter', FindSuggestionsFilter)
register('filter', _P + 'NewYearDateFilter', NewYearDateFilter)
register('filter', _P + 'PostponedAdjectiveConcordanceFilter', PostponedAdjectiveConcordanceFilter)
register('filter', _P + 'SpanishNumberInWordFilter', SpanishNumberInWordFilter)
register('filter', _P + 'SpanishSuppressMisspelledSuggestionsFilter', SpanishSuppressMisspelledSuggestionsFilter)
register('filter', _P + 'TextToNumberFilter', TextToNumberFilter)
