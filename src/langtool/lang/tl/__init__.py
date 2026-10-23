"""Tagalog (tl, tl-PH). Port of the LanguageTool module language-tl.

The Java module contains org.languagetool.language.Tagalog,
org.languagetool.tagging.tl.TagalogTagger and
org.languagetool.language.tokenizers.TagalogWordTokenizer. Tagalog and
TagalogTagger are ported declaratively in langtool.languages: TagalogTagger
is a plain BaseTagger for tl/tagalog.dict (with the default
tagLowercaseWithUppercase=true; the Locale("tl") has no special case
mapping), the disambiguator is the default DemoDisambiguator, the sentence
tokenizer is the SRXSentenceTokenizer and the rules are core rules.
TagalogWordTokenizer is in langtool.lang.tl.tokenizers. Its
MorfologikTagalogSpellerRule (org.languagetool.language.tl) is not ported
(spell checking).
"""

from ...extensions import register
from .tokenizers import TagalogWordTokenizer

register('word_tokenizer', 'TagalogWordTokenizer', lambda language: TagalogWordTokenizer(), language='tl')
