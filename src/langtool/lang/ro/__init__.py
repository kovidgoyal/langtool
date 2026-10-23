"""Romanian (ro, ro-RO). Port of the LanguageTool module language-ro.

The Java module contains org.languagetool.language.Romanian,
org.languagetool.tagging.ro.RomanianTagger,
org.languagetool.synthesis.ro.RomanianSynthesizer,
org.languagetool.tokenizers.ro.RomanianWordTokenizer and the rules
org.languagetool.rules.ro.SimpleReplaceRule,
RomanianWordRepeatBeginningRule, CompoundRule and
MorfologikRomanianSpellerRule. Romanian, RomanianTagger and
RomanianSynthesizer are ported declaratively in langtool.languages:
RomanianTagger is a plain BaseTagger for ro/romanian.dict (with the default
tagLowercaseWithUppercase=true; the Locale("ro") has no special case
mapping), RomanianSynthesizer a plain BaseSynthesizer for
ro/romanian_synth.dict with ro/romanian_tags.txt, the disambiguator is the
XmlRuleDisambiguator and the sentence tokenizer is the SRXSentenceTokenizer.
RomanianWordTokenizer is in langtool.lang.ro.tokenizers, the rules are in
langtool.lang.ro.rules; they are registered for 'ro' only, other languages
have rule classes named SimpleReplaceRule and CompoundRule too.
MorfologikRomanianSpellerRule is not ported (spell checking).
"""

from ...extensions import register
from .rules import CompoundRule, RomanianWordRepeatBeginningRule, SimpleReplaceRule
from .tokenizers import RomanianWordTokenizer

register('word_tokenizer', 'RomanianWordTokenizer', lambda language: RomanianWordTokenizer(), language='ro')
register('rule', 'RomanianWordRepeatBeginningRule',
         lambda messages, language, user_config: RomanianWordRepeatBeginningRule(messages, language),
         language='ro')
register('rule', 'SimpleReplaceRule',
         lambda messages, language, user_config: SimpleReplaceRule(messages, language), language='ro')
register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='ro')
