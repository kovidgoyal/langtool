"""Port of the language module de-DE-x-simple-language of LanguageTool:
org.languagetool.language.SimpleGerman (Simple German, "Leichte Sprache"),
a subclass of GermanyGerman that only has its own rules (the package name is
de_simple as the language code has dashes).

The language itself is declarative (the 'de-DE-x-simple-language' entry of
langtool.languages, the priorities in langtool.priorities). This package
registers for the language code the components SimpleGerman inherits from
German and GermanyGerman (the code is in langtool.lang.de): GermanTagger,
GermanSynthesizer, GermanWordTokenizer, GermanChunker (the
post-disambiguation chunker), German.filterRuleMatches,
German.toAdvancedTypography, German.getMultitokenSpeller, and the rule of
SimpleGerman.getRelevantRules, org.languagetool.rules.de.LongSentenceRule
(constructed with 12 words).

Not registered: the default spelling rule (German.createDefaultSpellingRule).
In Java it is a GermanSpellerRule for SimpleGerman without dictionaries
(there is no de-DE-x-simple-language/hunspell/ data), which no rule or
filter of SimpleGerman uses; the spelling rules are excluded anyway.
"""

from ...extensions import register
from ..de.chunking import GermanChunker
from ..de.language import filter_rule_matches, to_advanced_typography
from ..de.style_rules import LongSentenceRule
from ..de.synthesis import synthesizer_factory
from ..de.tagging import tagger_factory
from ..de.tokenizers import GermanWordTokenizer

CODE = 'de-DE-x-simple-language'


def _multitoken_speller(language):
    """GermanMultitokenSpeller.INSTANCE (German.getMultitokenSpeller)"""
    from ..de.multitoken import german_multitoken_speller
    return german_multitoken_speller(language)


register('tagger', 'GermanTagger', tagger_factory, language=CODE)
register('synthesizer', 'GermanSynthesizer', synthesizer_factory, language=CODE)
register('word_tokenizer', 'GermanWordTokenizer', lambda language: GermanWordTokenizer(), language=CODE)
register('chunker', 'GermanChunker', lambda language: GermanChunker(), language=CODE)
register('multitoken_speller', CODE, _multitoken_speller, language=CODE)
register('to_advanced_typography', CODE, to_advanced_typography, language=CODE)
register('filter_rule_matches', CODE, filter_rule_matches, language=CODE)
# SimpleGerman.getRelevantRules: new LongSentenceRule(messages, userConfig, 12)
# (org.languagetool.rules.de.LongSentenceRule, replaces the core rule)
register('rule', 'LongSentenceRule',
         lambda messages, language, user_config, max_words=12:
         LongSentenceRule(messages, language, user_config, max_words), language=CODE)
