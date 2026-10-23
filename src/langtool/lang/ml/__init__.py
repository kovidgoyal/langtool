"""Malayalam (ml, ml-IN). Port of the LanguageTool module language-ml.

The Java module contains org.languagetool.language.Malayalam,
org.languagetool.tagging.ml.MalayalamTagger and
org.languagetool.tokenizers.ml.MalayalamWordTokenizer. Malayalam and
MalayalamTagger are ported declaratively in langtool.languages:
MalayalamTagger is a plain BaseTagger for ml/malayalam.dict (with the default
tagLowercaseWithUppercase=true; the Locale("ml") has no special case
mapping), the disambiguator is the default DemoDisambiguator, the sentence
tokenizer is the SRXSentenceTokenizer and the rules are core rules.
MalayalamWordTokenizer is in langtool.lang.ml.tokenizers. Its
MorfologikMalayalamSpellerRule (org.languagetool.rules.ml) is not ported
(spell checking).
"""

from ...extensions import register
from .tokenizers import MalayalamWordTokenizer

register('word_tokenizer', 'MalayalamWordTokenizer', lambda language: MalayalamWordTokenizer())
