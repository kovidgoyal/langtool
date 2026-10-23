"""Breton (br, br-FR). Port of the LanguageTool module language-br.

The Java module contains org.languagetool.language.Breton,
org.languagetool.tagging.br.BretonTagger,
org.languagetool.tokenizers.br.BretonWordTokenizer and the rules
org.languagetool.rules.br.TopoReplaceRule, BretonCompoundRule,
DateCheckFilter and MorfologikBretonSpellerRule. Breton is ported
declaratively in langtool.languages: the disambiguator is the
XmlRuleDisambiguator and the sentence tokenizer the SRXSentenceTokenizer.
BretonTagger is in langtool.lang.br.tagging, BretonWordTokenizer in
langtool.lang.br.tokenizers, the rules in langtool.lang.br.rules and
DateCheckFilter in langtool.lang.br.filters. BretonCompoundRule is not used
by Breton.getRelevantRules (it is registered anyway).
MorfologikBretonSpellerRule (relevant rule and default spelling rule) is not
ported (spell checking).
"""

from ...extensions import register
from .filters import DateCheckFilter
from .rules import BretonCompoundRule, TopoReplaceRule
from .tagging import BretonTagger
from .tokenizers import BretonWordTokenizer

register('tagger', 'BretonTagger',
         lambda language, spec: BretonTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='br')
register('word_tokenizer', 'BretonWordTokenizer', lambda language: BretonWordTokenizer(), language='br')
register('rule', 'TopoReplaceRule', lambda messages, language, user_config: TopoReplaceRule(messages, language),
         language='br')
register('rule', 'BretonCompoundRule',
         lambda messages, language, user_config: BretonCompoundRule(messages, language, user_config),
         language='br')
register('filter', 'org.languagetool.rules.br.DateCheckFilter', DateCheckFilter)
