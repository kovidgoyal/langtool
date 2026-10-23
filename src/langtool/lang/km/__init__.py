"""Khmer (km, km-KH). Port of the LanguageTool module language-km.

The Java module contains org.languagetool.language.Khmer,
org.languagetool.tagging.km.KhmerTagger,
org.languagetool.tokenizers.km.KhmerWordTokenizer and the rules
org.languagetool.rules.km.KhmerSimpleReplaceRule, KhmerWordRepeatRule,
KhmerUnpairedBracketsRule, KhmerSpaceBeforeRule and KhmerHunspellRule.
Khmer and KhmerTagger are ported declaratively in langtool.languages:
KhmerTagger is a plain BaseTagger for km/khmer.dict (with the default
tagLowercaseWithUppercase=true; the Locale("km") has no special case
mapping), the disambiguator is the XmlRuleDisambiguator and the sentence
tokenizer is the SRXSentenceTokenizer. KhmerWordTokenizer is in
langtool.lang.km.tokenizers, the rules are in langtool.lang.km.rules.
KhmerHunspellRule is not ported (spell checking).
"""

from ...extensions import register
from .rules import KhmerSimpleReplaceRule, KhmerSpaceBeforeRule, KhmerUnpairedBracketsRule, KhmerWordRepeatRule
from .tokenizers import KhmerWordTokenizer

register('word_tokenizer', 'KhmerWordTokenizer', lambda language: KhmerWordTokenizer(), language='km')
register('rule', 'KhmerSimpleReplaceRule',
         lambda messages, language, user_config: KhmerSimpleReplaceRule(messages, language), language='km')
register('rule', 'KhmerWordRepeatRule',
         lambda messages, language, user_config: KhmerWordRepeatRule(messages, language), language='km')
register('rule', 'KhmerUnpairedBracketsRule',
         lambda messages, language, user_config: KhmerUnpairedBracketsRule(messages, language), language='km')
register('rule', 'KhmerSpaceBeforeRule',
         lambda messages, language, user_config: KhmerSpaceBeforeRule(messages, language), language='km')
