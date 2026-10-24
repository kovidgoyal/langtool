"""Dutch (nl, nl-BE). Port of the LanguageTool module language-nl.

The Java module contains org.languagetool.language.Dutch and BelgianDutch,
org.languagetool.tagging.nl.DutchTagger and DutchHybridDisambiguator,
org.languagetool.synthesis.nl.DutchSynthesizer,
org.languagetool.tokenizers.nl.DutchWordTokenizer, the rules
org.languagetool.rules.nl.CheckCaseRule, CompoundRule,
DutchWrongWordInContextRule, PreferredWordRule, SimpleReplaceRule,
SpaceInCompoundRule, WordCoherencyRule and MorfologikDutchSpellerRule, the
helpers CompoundAcceptor, Tools, PreferredWordData,
PreferredWordRuleWithSuggestion and DutchMultitokenSpeller, the filters
CompoundFilter, DateCheckFilter, DutchNumberInWordFilter and
DutchSuppressMisspelledSuggestionsFilter and DutchConfusionProbabilityRule.

Dutch, BelgianDutch, DutchHybridDisambiguator (the MultiWordChunkers for
spelling_global.txt and nl/multiwords.txt followed by the
XmlRuleDisambiguator with the global disambiguation rules) and
DutchSynthesizer (a BaseSynthesizer with the number speller of nl/nl.sor)
are ported declaratively in langtool.languages. DutchTagger is in
langtool.lang.nl.tagging, CompoundAcceptor in
langtool.lang.nl.compound_acceptor, DutchWordTokenizer in
langtool.lang.nl.tokenizers, the rules and Tools (glue_parts) in
langtool.lang.nl.rules (registered for 'nl' only, other languages have rule
classes with the same names), the filters in langtool.lang.nl.filters and
DutchMultitokenSpeller in langtool.lang.nl.multitoken.

Not ported: MorfologikDutchSpellerRule (spell checking), except for its
misspelling check (langtool.lang.nl.spelling, registered as the default
spelling rule of Dutch), which CompoundAcceptor,
DutchSuppressMisspelledSuggestionsFilter, DutchNumberInWordFilter and
MultitokenSpellerFilter use. Also not ported: DutchConfusionProbabilityRule (language model; commented out in Dutch
anyway).
"""

from ...extensions import register
from .filters import CompoundFilter, DateCheckFilter, DutchNumberInWordFilter, DutchSuppressMisspelledSuggestionsFilter
from .multitoken import dutch_multitoken_speller
from .rules import (CheckCaseRule, CompoundRule, DutchWrongWordInContextRule, PreferredWordRule, SimpleReplaceRule,
                    SpaceInCompoundRule, WordCoherencyRule)
from .spelling import MorfologikDutchSpellerCheck
from .tagging import DutchTagger
from .tokenizers import DutchWordTokenizer

register('tagger', 'DutchTagger',
         lambda language, spec: DutchTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='nl')
register('word_tokenizer', 'DutchWordTokenizer', lambda language: DutchWordTokenizer(), language='nl')
register('default_spelling_rule', 'nl', MorfologikDutchSpellerCheck, language='nl')
register('multitoken_speller', 'nl', dutch_multitoken_speller, language='nl')
register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='nl')
register('rule', 'PreferredWordRule',
         lambda messages, language, user_config: PreferredWordRule(messages, language), language='nl')
for _cls in (CheckCaseRule, DutchWrongWordInContextRule, SimpleReplaceRule, SpaceInCompoundRule, WordCoherencyRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='nl')
_P = 'org.languagetool.rules.nl.'
register('filter', _P + 'CompoundFilter', CompoundFilter)
register('filter', _P + 'DateCheckFilter', DateCheckFilter)
register('filter', _P + 'DutchNumberInWordFilter', DutchNumberInWordFilter)
register('filter', _P + 'DutchSuppressMisspelledSuggestionsFilter', DutchSuppressMisspelledSuggestionsFilter)
