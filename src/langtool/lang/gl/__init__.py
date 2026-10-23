"""Galician (gl, gl-ES). Port of the LanguageTool module language-gl.

The Java module contains org.languagetool.language.Galician,
org.languagetool.tagging.gl.GalicianTagger,
org.languagetool.synthesis.gl.GalicianSynthesizer,
org.languagetool.tagging.disambiguation.gl.GalicianHybridDisambiguator,
org.languagetool.tokenizers.gl.GalicianWordTokenizer and the rules
org.languagetool.rules.gl.SimpleReplaceRule, CastWordsRule,
GalicianRedundancyRule, GalicianWordinessRule, GalicianBarbarismsRule,
GalicianWikipediaRule and the filter AdvancedSynthesizerFilter. Galician,
GalicianSynthesizer and GalicianHybridDisambiguator are ported
declaratively in langtool.languages: GalicianSynthesizer is a plain
BaseSynthesizer for gl/galician_synth.dict with gl/galician_tags.txt,
GalicianHybridDisambiguator is the MultiWordChunker for gl/multiwords.txt
followed by the XmlRuleDisambiguator, and the sentence tokenizer is the
SRXSentenceTokenizer. GalicianTagger is in langtool.lang.gl.tagging,
GalicianWordTokenizer in langtool.lang.gl.tokenizers, the rules in
langtool.lang.gl.rules (registered for 'gl' only, other languages have rule
classes named SimpleReplaceRule too) and AdvancedSynthesizerFilter in
langtool.lang.gl.filters (its base class AbstractAdvancedSynthesizerFilter
is in langtool.rules.core_filters). HunspellRule (relevant rule and default
spelling rule) is not ported (spell checking).
"""

from ...extensions import register
from .filters import AdvancedSynthesizerFilter
from .rules import (CastWordsRule, GalicianBarbarismsRule, GalicianRedundancyRule, GalicianWikipediaRule,
                    GalicianWordinessRule, SimpleReplaceRule)
from .tagging import GalicianTagger
from .tokenizers import GalicianWordTokenizer

register('tagger', 'GalicianTagger',
         lambda language, spec: GalicianTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='gl')
register('word_tokenizer', 'GalicianWordTokenizer', lambda language: GalicianWordTokenizer(), language='gl')
for _cls in (SimpleReplaceRule, CastWordsRule, GalicianRedundancyRule, GalicianWordinessRule,
             GalicianBarbarismsRule, GalicianWikipediaRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='gl')
register('filter', 'org.languagetool.rules.gl.AdvancedSynthesizerFilter', AdvancedSynthesizerFilter)
