"""Belarusian (be, be-BY). Port of the LanguageTool module language-be.

The Java module contains org.languagetool.language.Belarusian,
org.languagetool.tokenizers.be.BelarusianWordTokenizer,
org.languagetool.rules.be.SimpleReplaceRule,
org.languagetool.rules.be.BelarusianSpecificCaseRule and
org.languagetool.rules.be.MorfologikBelarusianSpellerRule. Belarusian is
ported declaratively in langtool.languages: the tagger is the DemoTagger
(no tagging), the disambiguator is the default DemoDisambiguator and the
sentence tokenizer is the SRXSentenceTokenizer. BelarusianWordTokenizer is
in langtool.lang.be.tokenizers, SimpleReplaceRule and
BelarusianSpecificCaseRule are in langtool.lang.be.rules; they are
registered for 'be' only, other languages have classes named
SimpleReplaceRule too. MorfologikBelarusianSpellerRule is not ported (spell
checking), neither is the n-gram support of LanguageWithModel.
"""

from ...extensions import register
from .rules import BelarusianSpecificCaseRule, SimpleReplaceRule
from .tokenizers import BelarusianWordTokenizer

register('word_tokenizer', 'BelarusianWordTokenizer', lambda language: BelarusianWordTokenizer(), language='be')
register('rule', 'SimpleReplaceRule',
         lambda messages, language, user_config: SimpleReplaceRule(messages, language), language='be')
register('rule', 'BelarusianSpecificCaseRule',
         lambda messages, language, user_config: BelarusianSpecificCaseRule(messages, language), language='be')
