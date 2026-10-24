"""Irish (ga, ga-IE). Port of the LanguageTool module language-ga.

The Java module contains org.languagetool.language.Irish,
org.languagetool.tagging.ga.IrishTagger (with Utils and Retaggable),
org.languagetool.synthesis.ga.IrishSynthesizer,
org.languagetool.tagging.disambiguation.ga.IrishHybridDisambiguator, the
rules org.languagetool.rules.ga.CompoundRule,
DativePluralStandardReplaceRule (with DativePluralsData and
DativePluralsEntry), DhaNoBeirtRule (with DhaNoBeirtData),
EnglishHomophoneRule, IrishFGBEqReplaceRule, IrishReplaceRule,
IrishSpecificCaseRule, LogainmRule, PeopleRule, PrestandardReplaceRule,
SpacesRule and MorfologikIrishSpellerRule, and the filters
IrishPartialPosTagFilter and NoDisambiguationIrishPartialPosTagFilter.

Irish, IrishSynthesizer (a BaseSynthesizer for /ga/irish_synth.dict and
/ga/irish_tags.txt) and IrishHybridDisambiguator (the MultiWordChunker for
/ga/multiwords.txt followed by the XmlRuleDisambiguator) are ported
declaratively in langtool.languages; the sentence tokenizer is the
SRXSentenceTokenizer and the word tokenizer the default WordTokenizer.
IrishTagger is in langtool.lang.ga.tagging, the helper utilities (Utils,
Retaggable) in langtool.lang.ga.utils, the rules in langtool.lang.ga.rules
(registered for 'ga' only) and the filters in langtool.lang.ga.filters.
MorfologikIrishSpellerRule (relevant rule and default spelling rule) is not
ported (spell checking); nothing else in the module asks the speller.
"""

from ...extensions import register
from .filters import IrishPartialPosTagFilter, NoDisambiguationIrishPartialPosTagFilter
from .rules import (CompoundRule, DativePluralStandardReplaceRule, DhaNoBeirtRule, EnglishHomophoneRule,
                    IrishFGBEqReplaceRule, IrishReplaceRule, IrishSpecificCaseRule, LogainmRule, PeopleRule,
                    PrestandardReplaceRule, SpacesRule)
from .tagging import IrishTagger

register('tagger', 'IrishTagger',
         lambda language, spec: IrishTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='ga')
register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='ga')
for _cls in (DativePluralStandardReplaceRule, DhaNoBeirtRule, EnglishHomophoneRule, IrishFGBEqReplaceRule,
             IrishReplaceRule, IrishSpecificCaseRule, LogainmRule, PeopleRule, PrestandardReplaceRule, SpacesRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='ga')
for _cls in (IrishPartialPosTagFilter, NoDisambiguationIrishPartialPosTagFilter):
    register('filter', 'org.languagetool.rules.ga.' + _cls.__name__, _cls)
