"""Swedish (sv). Port of the LanguageTool module language-sv.

The Java module contains org.languagetool.language.Swedish,
org.languagetool.tagging.sv.SwedishTagger,
org.languagetool.synthesis.sv.SwedishSynthesizer,
org.languagetool.tagging.disambiguation.sv.SwedishHybridDisambiguator,
org.languagetool.rules.sv.CompoundRule and
org.languagetool.rules.sv.WordCoherencyRule. Swedish, SwedishTagger,
SwedishSynthesizer and SwedishHybridDisambiguator are ported declaratively
in langtool.languages: SwedishTagger is a plain BaseTagger for
sv/swedish.dict (with the default tagLowercaseWithUppercase=true; the
Locale("sv") has no special case mapping), SwedishSynthesizer is a plain
BaseSynthesizer for sv/swedish_synth.dict with sv/swedish_synth.dict_tags.txt
and the number speller of sv/sv.sor (langtool.soros), the
SwedishHybridDisambiguator is the XmlRuleDisambiguator followed by the
MultiWordChunker for sv/multiwords.txt (chunker.disambiguate(
disambiguator.disambiguate(input))) and the sentence tokenizer is the
SRXSentenceTokenizer. CompoundRule and WordCoherencyRule are in
langtool.lang.sv.rules; they are registered for 'sv' only, other languages
have rule classes with the same names. Its HunspellRule is not ported (spell
checking).
"""

from ...extensions import register
from .rules import CompoundRule, WordCoherencyRule

register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='sv')
register('rule', 'WordCoherencyRule',
         lambda messages, language, user_config: WordCoherencyRule(messages, language), language='sv')
