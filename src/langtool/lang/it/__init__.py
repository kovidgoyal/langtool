"""Italian (it). Port of the LanguageTool module language-it.

The Java module contains org.languagetool.language.Italian,
org.languagetool.tagging.it.ItalianTagger,
org.languagetool.synthesis.it.ItalianSynthesizer,
org.languagetool.tagging.disambiguation.rules.it.ItalianRuleDisambiguator,
org.languagetool.rules.it.ItalianWordRepeatRule,
org.languagetool.rules.it.DateCheckFilter,
org.languagetool.rules.it.MorfologikItalianSpellerRule and
org.languagetool.rules.it.ItalianConfusionProbabilityRule. Italian,
ItalianTagger, ItalianSynthesizer and ItalianRuleDisambiguator are ported
declaratively in langtool.languages: ItalianTagger is a plain BaseTagger for
it/italian.dict (Locale.ITALIAN has no special case mapping),
ItalianSynthesizer a plain BaseSynthesizer for it/italian_synth.dict with
it/italian_tags.txt (no number speller), ItalianRuleDisambiguator just the
XmlRuleDisambiguator and the sentence tokenizer is the SRXSentenceTokenizer.
ItalianWordRepeatRule is in langtool.lang.it.rules, DateCheckFilter in
langtool.lang.it.filters. MorfologikItalianSpellerRule (spell checking) and
ItalianConfusionProbabilityRule (language model) are not ported.
"""

from ...extensions import register
from .filters import DateCheckFilter
from .rules import ItalianWordRepeatRule

register('rule', 'ItalianWordRepeatRule',
         lambda messages, language, user_config: ItalianWordRepeatRule(messages, language), language='it')
register('filter', 'org.languagetool.rules.it.DateCheckFilter', DateCheckFilter)
