"""Esperanto (eo). Port of the LanguageTool module language-eo.

The Java module contains org.languagetool.language.Esperanto,
org.languagetool.tagging.eo.EsperantoTagger,
org.languagetool.tokenizers.eo.EsperantoWordTokenizer and
org.languagetool.rules.eo.DateCheckFilter. Esperanto is ported declaratively
in langtool.languages: the disambiguator is the XmlRuleDisambiguator, the
sentence tokenizer the SRXSentenceTokenizer and the rules are core rules.
EsperantoTagger is in langtool.lang.eo.tagging, EsperantoWordTokenizer in
langtool.lang.eo.tokenizers and DateCheckFilter in langtool.lang.eo.filters.
Its HunspellRule (relevant rule and default spelling rule) is not ported
(spell checking).
"""

from ...extensions import register
from .filters import DateCheckFilter
from .tagging import EsperantoTagger
from .tokenizers import EsperantoWordTokenizer

register('tagger', 'EsperantoTagger',
         lambda language, spec: EsperantoTagger(language.resource_dir, language.rules_dir), language='eo')
register('word_tokenizer', 'EsperantoWordTokenizer', lambda language: EsperantoWordTokenizer(), language='eo')
register('filter', 'org.languagetool.rules.eo.DateCheckFilter', DateCheckFilter)
