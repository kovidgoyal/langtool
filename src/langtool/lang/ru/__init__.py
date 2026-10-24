"""Russian (ru, ru-RU). Port of the LanguageTool module language-ru.

The Java module contains org.languagetool.language.Russian,
org.languagetool.tagging.ru.RussianTagger,
org.languagetool.synthesis.ru.RussianSynthesizer,
org.languagetool.tagging.disambiguation.ru.RussianHybridDisambiguator,
org.languagetool.chunking.RussianChunker,
org.languagetool.tokenizers.ru.RussianWordTokenizer, the rules
org.languagetool.rules.ru.RussianCompoundRule, RussianDashRule,
RussianFillerWordsRule, RussianSimpleReplaceRule,
RussianSimpleWordRepeatRule, RussianSpecificCaseRule,
RussianUnpairedBracketsRule, RussianVerbConjugationRule,
RussianWordCoherencyRule, RussianWordRepeatRule, RussianWordRootRepeatRule,
MorfologikRussianSpellerRule, MorfologikRussianYOSpellerRule and
RussianConfusionProbabilityRule, and the filters AdvancedSynthesizerFilter,
DateCheckFilter (with DateFilterHelper), FutureDateFilter, INNNumberFilter,
NoDisambiguationRussianPartialPosTagFilter, RussianPartialPosTagFilter and
RussianSuppressMisspelledSuggestionsFilter.

Russian, RussianSynthesizer (a BaseSynthesizer for /ru/russian_synth.dict
and /ru/tags_russian.txt) and RussianHybridDisambiguator (the
MultiWordChunker for /ru/multiwords.txt followed by the
XmlRuleDisambiguator) are ported declaratively in langtool.languages; the
sentence tokenizer is the SRXSentenceTokenizer. RussianTagger is in
langtool.lang.ru.tagging, RussianWordTokenizer in langtool.lang.ru.tokenizers,
RussianChunker (the post-disambiguation chunker, based on the OpenRegex
port langtool.openregex) in langtool.lang.ru.chunking, the rules in
langtool.lang.ru.rules (registered for 'ru' only) and the filters in
langtool.lang.ru.filters. The spelling rules MorfologikRussianSpellerRule
and MorfologikRussianYOSpellerRule are not ported (spell checking), except
for the misspelling check of MorfologikRussianSpellerRule
(langtool.lang.ru.spelling, registered as the default spelling rule of
Russian), which RussianSuppressMisspelledSuggestionsFilter uses.
RussianConfusionProbabilityRule (n-gram language model) is not ported,
neither is the n-gram support of LanguageWithModel.
"""

from ...extensions import register
from .chunking import RussianChunker
from .filters import (AdvancedSynthesizerFilter, DateCheckFilter, FutureDateFilter, INNNumberFilter,
                      NoDisambiguationRussianPartialPosTagFilter, RussianPartialPosTagFilter,
                      RussianSuppressMisspelledSuggestionsFilter)
from .rules import (RussianCompoundRule, RussianDashRule, RussianFillerWordsRule, RussianSimpleReplaceRule,
                    RussianSimpleWordRepeatRule, RussianSpecificCaseRule, RussianUnpairedBracketsRule,
                    RussianVerbConjugationRule, RussianWordCoherencyRule, RussianWordRepeatRule,
                    RussianWordRootRepeatRule)
from .spelling import MorfologikRussianSpellerCheck
from .tagging import RussianTagger
from .tokenizers import RussianWordTokenizer

register('tagger', 'RussianTagger',
         lambda language, spec: RussianTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='ru')
register('word_tokenizer', 'RussianWordTokenizer', lambda language: RussianWordTokenizer(), language='ru')
register('chunker', 'RussianChunker', lambda language: RussianChunker(), language='ru')
register('default_spelling_rule', 'ru', MorfologikRussianSpellerCheck, language='ru')
for _cls in (RussianCompoundRule, RussianFillerWordsRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language, user_config), language='ru')
for _cls in (RussianDashRule, RussianSimpleReplaceRule, RussianSimpleWordRepeatRule, RussianSpecificCaseRule,
             RussianUnpairedBracketsRule, RussianVerbConjugationRule, RussianWordCoherencyRule, RussianWordRepeatRule,
             RussianWordRootRepeatRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='ru')
for _cls in (AdvancedSynthesizerFilter, DateCheckFilter, FutureDateFilter, INNNumberFilter,
             NoDisambiguationRussianPartialPosTagFilter, RussianPartialPosTagFilter,
             RussianSuppressMisspelledSuggestionsFilter):
    register('filter', 'org.languagetool.rules.ru.' + _cls.__name__, _cls)
