"""English (en, en-US, en-GB, en-AU, en-CA, en-NZ, en-ZA). Port of the
LanguageTool module language-en.

The Java module contains org.languagetool.language.English, AmericanEnglish,
BritishEnglish, AustralianEnglish, CanadianEnglish, NewZealandEnglish and
SouthAfricanEnglish, org.languagetool.tagging.en.EnglishTagger and
EnglishHybridDisambiguator, org.languagetool.synthesis.en.EnglishSynthesizer,
org.languagetool.tokenizers.en.EnglishWordTokenizer,
org.languagetool.chunking.EnglishChunker and EnglishChunkFilter, the rules of
org.languagetool.rules.en (AvsAnRule with AvsAnData, CompoundRule,
ConsistentApostrophesRule, ContractionSpellingRule, EnglishDashRule,
EnglishSpecificCaseRule, EnglishUnpairedBracketsRule,
EnglishUnpairedQuotesRule, EnglishWordRepeatRule,
EnglishWordRepeatBeginningRule, EnglishWrongWordInContextRule,
EnglishRepeatedWordsRule, LongSentenceRule, StyleTooOftenUsedVerbRule,
StyleTooOftenUsedNounRule, StyleTooOftenUsedAdjectiveRule, WordCoherencyRule,
the AbstractSimpleReplaceRule2 subclasses AmericanReplaceRule,
BritishReplaceRule, NewZealandReplaceRule, SimpleReplaceRule,
SimpleReplaceProfanityRule, EnglishDiacriticsRule, EnglishPlainEnglishRule
and EnglishRedundancyRule, UnitConversionRule, UnitConversionRuleImperial and
UnitConversionRuleUS, GoogleStyleWordTokenizer, the speller rules
AbstractEnglishSpellerRule and Morfologik*SpellerRule with VariantInfo and
the translation classes BeoLingusTranslator and Inflector, the language model
rules EnglishConfusionProbabilityRule, EnglishNgramProbabilityRule,
UpperCaseNgramRule and EnglishFor*FalseFriendRule), the filters
(AdvancedSynthesizerFilter, AdverbFilter, DateCheckFilter,
YMDDateCheckFilter, FutureDateFilter, NewYearDateFilter,
YMDNewYearDateFilter and DateFilterHelper,
EnglishConvertToSentenceCaseFilter, EnglishNumberInWordFilter,
EnglishPartialPosTagFilter, NoDisambiguationEnglishPartialPosTagFilter,
EnglishSuppressMisspelledSuggestionsFilter, FindSuggestionsFilter and
OrdinalSuffixFilter) and EnglishMultitokenSpeller.

The language classes and EnglishHybridDisambiguator (the MultiWordChunkers
for spelling_global.txt and en/multiwords.txt followed by the
XmlRuleDisambiguator of en-US with the global disambiguation rules) are
ported declaratively in langtool.languages, English.filterRuleMatches in
langtool.lang.en.language. EnglishTagger is in langtool.lang.en.tagging,
EnglishSynthesizer in langtool.lang.en.synthesis, EnglishWordTokenizer and
GoogleStyleWordTokenizer in langtool.lang.en.tokenizers, EnglishChunker (with
the OpenNLP inference code ported in langtool.opennlp) in
langtool.lang.en.chunking, AvsAnRule in langtool.lang.en.avsan, the other
rules in langtool.lang.en.rules (registered for 'en' only), the filters in
langtool.lang.en.filters, English.prepareLineForSpeller and
EnglishMultitokenSpeller in langtool.lang.en.spelling.

Not ported: the speller rules (spell checking), except for their
misspelling check and single word suggestions (langtool.lang.en.spelling,
registered as the default spelling rules of the English variants), with
VariantInfo, BeoLingusTranslator and Inflector (only used for the
suggestions of the speller rules), and the language model rules
EnglishConfusionProbabilityRule, EnglishNgramProbabilityRule,
UpperCaseNgramRule, EnglishForL2SpeakersFalseFriendRule and its subclasses.
"""

from ...extensions import register, synthesizer_resources
from ...rules.abstract_rules import ReadabilityRule
from .avsan import AvsAnRule
from .chunking import EnglishChunker
from .filters import (AdvancedSynthesizerFilter, AdverbFilter, DateCheckFilter, EnglishConvertToSentenceCaseFilter,
                      EnglishNumberInWordFilter, EnglishPartialPosTagFilter, EnglishSuppressMisspelledSuggestionsFilter,
                      FindSuggestionsFilter, FutureDateFilter, NewYearDateFilter,
                      NoDisambiguationEnglishPartialPosTagFilter, OrdinalSuffixFilter, YMDDateCheckFilter,
                      YMDNewYearDateFilter)
from .language import filter_rule_matches
from .rules import (AmericanReplaceRule, BritishReplaceRule, CompoundRule, ConsistentApostrophesRule,
                    ContractionSpellingRule, EnglishDashRule, EnglishDiacriticsRule, EnglishPlainEnglishRule,
                    EnglishRedundancyRule, EnglishRepeatedWordsRule, EnglishSpecificCaseRule,
                    EnglishUnpairedBracketsRule, EnglishUnpairedQuotesRule, EnglishWordRepeatBeginningRule,
                    EnglishWordRepeatRule, EnglishWrongWordInContextRule, LongSentenceRule, NewZealandReplaceRule,
                    SimpleReplaceProfanityRule, SimpleReplaceRule, StyleTooOftenUsedAdjectiveRule,
                    StyleTooOftenUsedNounRule, StyleTooOftenUsedVerbRule, UnitConversionRule,
                    UnitConversionRuleImperial, UnitConversionRuleUS, WordCoherencyRule)
from .spelling import english_default_spelling_rule, english_multitoken_speller
from .synthesis import EnglishSynthesizer
from .tagging import EnglishTagger
from .tokenizers import EnglishWordTokenizer


def _synthesizer(language, spec):
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return EnglishSynthesizer(dictionary, tags_path, 'en', language.resource_dir, number_speller, roman_numberer)


register('tagger', 'EnglishTagger',
         lambda language, spec: EnglishTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='en')
register('synthesizer', 'EnglishSynthesizer', _synthesizer, language='en')
register('word_tokenizer', 'EnglishWordTokenizer', lambda language: EnglishWordTokenizer(language.tagger),
         language='en')
register('chunker', 'EnglishChunker', EnglishChunker, language='en')
register('default_spelling_rule', 'en', english_default_spelling_rule, language='en')
register('multitoken_speller', 'en', english_multitoken_speller, language='en')
register('filter_rule_matches', 'en', filter_rule_matches, language='en')

# rules with the Java constructor (messages, language)
for _cls in (EnglishUnpairedBracketsRule, EnglishUnpairedQuotesRule, EnglishWordRepeatRule,
             EnglishWordRepeatBeginningRule, ContractionSpellingRule, EnglishWrongWordInContextRule, SimpleReplaceRule,
             SimpleReplaceProfanityRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='en')
# rules with the Java constructor (messages, language, userConfig)
for _cls in (CompoundRule, StyleTooOftenUsedVerbRule, StyleTooOftenUsedNounRule, StyleTooOftenUsedAdjectiveRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language, user_config), language='en')
# rules with the Java constructor (messages); the language is used to find the data files (English or
# AmericanEnglish.getInstance() in Java, see the classes)
for _cls in (ConsistentApostrophesRule, EnglishSpecificCaseRule, AvsAnRule, EnglishDashRule, WordCoherencyRule,
             EnglishDiacriticsRule, EnglishPlainEnglishRule, EnglishRedundancyRule, EnglishRepeatedWordsRule,
             UnitConversionRule, UnitConversionRuleImperial, UnitConversionRuleUS):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='en')
# rules with the Java constructor (messages, path)
for _cls in (AmericanReplaceRule, BritishReplaceRule, NewZealandReplaceRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, path, _cls=_cls: _cls(messages, path), language='en')
# (Java: new ReadabilityRule(messages, this, userConfig, tooEasyTest), the core rule, which is for English)
register('rule', 'ReadabilityRule',
         lambda messages, language, user_config, too_easy_test: ReadabilityRule(messages, language, user_config,
                                                                                too_easy_test), language='en')
# (Java: new org.languagetool.rules.en.LongSentenceRule(messages, userConfig, maxWords))
register('rule', 'LongSentenceRule',
         lambda messages, language, user_config, max_words: LongSentenceRule(messages, language, max_words),
         language='en')

_P = 'org.languagetool.rules.en.'
for _cls in (AdvancedSynthesizerFilter, AdverbFilter, DateCheckFilter, YMDDateCheckFilter, FutureDateFilter,
             NewYearDateFilter, YMDNewYearDateFilter, EnglishConvertToSentenceCaseFilter, EnglishNumberInWordFilter,
             EnglishPartialPosTagFilter, NoDisambiguationEnglishPartialPosTagFilter,
             EnglishSuppressMisspelledSuggestionsFilter, FindSuggestionsFilter, OrdinalSuffixFilter):
    register('filter', _P + _cls.__name__, _cls)
