"""Arabic (ar). Port of the LanguageTool module language-ar.

The Java module contains org.languagetool.language.Arabic,
org.languagetool.tagging.ar.ArabicTagger, ArabicTagManager and
ArabicHybridDisambiguator, org.languagetool.synthesis.ar.ArabicSynthesizer,
org.languagetool.tokenizers.ArabicWordTokenizer, the helpers
org.languagetool.tools.ArabicStringTools, ArabicConstants,
ArabicConstantsMaps, ArabicWordMaps, ArabicNumbersWords,
ArabicNumbersWordsConstants and ArabicUnitsHelper, the rules
org.languagetool.rules.ar.ArabicCommaWhitespaceRule,
ArabicQuestionMarkWhitespaceRule, ArabicSemiColonWhitespaceRule,
ArabicDoublePunctuationRule, ArabicWordRepeatRule, ArabicSimpleReplaceRule,
ArabicDiacriticsRule, ArabicDarjaRule, ArabicHomophonesRule,
ArabicRedundancyRule, ArabicWordCoherencyRule, ArabicWordinessRule,
ArabicWrongWordInContextRule, ArabicTransVerbRule,
ArabicInflectedOneWordReplaceRule, ArabicHunspellSpellerRule and
ArabicConfusionProbabilityRule and the filters of
org.languagetool.rules.ar.filters: ArabicAdjectiveToExclamationFilter,
ArabicAdvancedSynthesizerFilter, ArabicDateCheckFilter,
ArabicDMYDateCheckFilter (with ArabicDateFilterHelper),
ArabicMasdarToVerbFilter, ArabicNumberPhraseFilter and
ArabicVerbToMafoulMutlaqFilter.

Arabic and ArabicHybridDisambiguator (the MultiWordChunker for
ar/multiwords.txt followed by the XmlRuleDisambiguator) are ported
declaratively in langtool.languages. ArabicTagger and ArabicTagManager are
in langtool.lang.ar.tagging, ArabicSynthesizer in langtool.lang.ar.synthesis,
ArabicWordTokenizer in langtool.lang.ar.tokenizers, the string tools and
constants in langtool.lang.ar.tools, the numbers and units helpers in
langtool.lang.ar.numbers, the rules in langtool.lang.ar.rules (registered
for 'ar' only) and the filters in langtool.lang.ar.filters.

Not ported: ArabicHunspellSpellerRule (spell checking; Arabic has no
code that asks the speller whether a word is misspelled) and
ArabicConfusionProbabilityRule (language model).
"""

from ...extensions import register
from .filters import (ArabicAdjectiveToExclamationFilter, ArabicAdvancedSynthesizerFilter, ArabicDateCheckFilter,
                      ArabicDMYDateCheckFilter, ArabicMasdarToVerbFilter, ArabicNumberPhraseFilter,
                      ArabicVerbToMafoulMutlaqFilter)
from .rules import (ArabicCommaWhitespaceRule, ArabicDarjaRule, ArabicDiacriticsRule, ArabicDoublePunctuationRule,
                    ArabicHomophonesRule, ArabicInflectedOneWordReplaceRule, ArabicQuestionMarkWhitespaceRule,
                    ArabicRedundancyRule, ArabicSemiColonWhitespaceRule, ArabicSimpleReplaceRule, ArabicTransVerbRule,
                    ArabicWordCoherencyRule, ArabicWordinessRule, ArabicWordRepeatRule,
                    ArabicWrongWordInContextRule)
from .synthesis import ArabicSynthesizer
from .tagging import ArabicTagger
from .tokenizers import ArabicWordTokenizer


def _synthesizer(language, spec):
    # ArabicSynthesizer.INSTANCE, with its own ArabicTagger (as in Java)
    tagger = ArabicTagger(language.dictionary(language.get('tagger')['dict']), language.resource_dir)
    tags = spec.get('tags')
    return ArabicSynthesizer(language.dictionary(spec['dict']), language.resource_path(tags) if tags else None,
                             language.resource_dir, tagger)


register('tagger', 'ArabicTagger',
         lambda language, spec: ArabicTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='ar')
register('synthesizer', 'ArabicSynthesizer', _synthesizer, language='ar')
register('word_tokenizer', 'ArabicWordTokenizer', lambda language: ArabicWordTokenizer(), language='ar')
for _cls in (ArabicCommaWhitespaceRule, ArabicQuestionMarkWhitespaceRule, ArabicSemiColonWhitespaceRule,
             ArabicDoublePunctuationRule, ArabicWordRepeatRule, ArabicSimpleReplaceRule, ArabicDiacriticsRule,
             ArabicDarjaRule, ArabicHomophonesRule, ArabicRedundancyRule, ArabicWordCoherencyRule,
             ArabicWordinessRule, ArabicWrongWordInContextRule, ArabicTransVerbRule,
             ArabicInflectedOneWordReplaceRule):
    register('rule', _cls.__name__, lambda messages, language, user_config, _cls=_cls: _cls(messages, language),
             language='ar')
_P = 'org.languagetool.rules.ar.filters.'
for _cls in (ArabicAdjectiveToExclamationFilter, ArabicAdvancedSynthesizerFilter, ArabicDateCheckFilter,
             ArabicDMYDateCheckFilter, ArabicMasdarToVerbFilter, ArabicNumberPhraseFilter,
             ArabicVerbToMafoulMutlaqFilter):
    register('filter', _P + _cls.__name__, _cls)
