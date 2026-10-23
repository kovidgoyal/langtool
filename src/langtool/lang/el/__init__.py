"""Greek (el, el-GR). Port of the LanguageTool module language-el.

The Java module contains org.languagetool.language.Greek,
org.languagetool.tagging.el.GreekTagger,
org.languagetool.synthesis.el.GreekSynthesizer,
org.languagetool.tokenizers.el.GreekWordTokenizer (with the JFlex scanner
GreekWordTokenizerImpl) and the rules org.languagetool.rules.el.
GreekWordRepeatBeginningRule, ReplaceHomonymsRule, GreekSpecificCaseRule,
NumeralStressRule, GreekRedundancyRule and MorfologikGreekSpellerRule.
Greek and GreekSynthesizer are ported declaratively in langtool.languages:
GreekSynthesizer is a plain BaseSynthesizer for el/greek_synth.dict with
el/greek_tags.txt, the disambiguator is the XmlRuleDisambiguator and the
sentence tokenizer the SRXSentenceTokenizer. GreekTagger is in
langtool.lang.el.tagging, together with the port of the GreekAnalyzer of
the library org.ioperm:morphology-el that it uses (its dictionary
analysis.dict is downloaded as el/analysis.dict, see dictionaries.json);
GreekWordTokenizer is in langtool.lang.el.tokenizers and the rules in
langtool.lang.el.rules. MorfologikGreekSpellerRule (relevant rule and
default spelling rule) is not ported (spell checking).
"""

from ...extensions import register
from .rules import (GreekRedundancyRule, GreekSpecificCaseRule, GreekWordRepeatBeginningRule, NumeralStressRule,
                    ReplaceHomonymsRule)
from .tagging import GreekTagger
from .tokenizers import GreekWordTokenizer

# the dictionary of org.ioperm.morphology.el.GreekAnalyzer
ANALYZER_DICTIONARY = 'el/analysis.dict'

register('tagger', 'GreekTagger',
         lambda language, spec: GreekTagger(language.dictionary(spec['dict']),
                                            language.dictionary(ANALYZER_DICTIONARY), language.resource_dir),
         language='el')
register('word_tokenizer', 'GreekWordTokenizer', lambda language: GreekWordTokenizer(), language='el')
for _cls in (GreekWordRepeatBeginningRule, ReplaceHomonymsRule, GreekSpecificCaseRule, NumeralStressRule,
             GreekRedundancyRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='el')
