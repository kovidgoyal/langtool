"""Slovak (sk, sk-SK). Port of the LanguageTool module language-sk.

The Java module contains org.languagetool.language.Slovak,
org.languagetool.tagging.sk.SlovakTagger,
org.languagetool.synthesis.sk.SlovakSynthesizer and
org.languagetool.rules.sk.CompoundRule. Slovak, SlovakTagger and
SlovakSynthesizer are ported declaratively in langtool.languages:
SlovakTagger is a plain BaseTagger for sk/slovak.dict (with the default
tagLowercaseWithUppercase=true; the Locale("sk") has no special case
mapping), SlovakSynthesizer is a plain BaseSynthesizer for
sk/slovak_synth.dict with sk/slovak_tags.txt, the disambiguator is the
default DemoDisambiguator and the sentence tokenizer is the
SRXSentenceTokenizer. CompoundRule is in langtool.lang.sk.rules; it is
registered for 'sk' only, other languages have rule classes named
CompoundRule too. Its MorfologikSlovakSpellerRule is not
ported (spell checking).
"""

from ...extensions import register
from .rules import CompoundRule

register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='sk')
