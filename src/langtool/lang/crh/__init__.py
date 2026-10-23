"""Crimean Tatar (crh, crh-UA). Port of the LanguageTool module language-crh.

The Java module contains org.languagetool.language.CrimeanTatar,
org.languagetool.tagging.crh.CrimeanTatarTagger,
org.languagetool.synthesis.crh.CrimeanTatarSynthesizer and
org.languagetool.tokenizers.crh.CrimeanTatarWordTokenizer. CrimeanTatar and
CrimeanTatarSynthesizer are ported declaratively in langtool.languages:
CrimeanTatarSynthesizer is a plain BaseSynthesizer for
crh/crimean_tatar_synth.dict with crh/crimean_tatar_synth.dict_tags.txt, the
disambiguator is the default DemoDisambiguator, the sentence tokenizer is the
SRXSentenceTokenizer (CrimeanTatar overrides getSentenceTokenizer(), not
createDefaultSentenceTokenizer()) and the rules are core rules, two of them
with Crimean Tatar examples. CrimeanTatarTagger is in langtool.lang.crh.tagging
and CrimeanTatarWordTokenizer in langtool.lang.crh.tokenizers. Its
MorfologikCrimeanTatarSpellerRule (org.languagetool.rules.crh) is not ported
(spell checking).
"""

from ...extensions import register
from .tagging import CrimeanTatarTagger
from .tokenizers import CrimeanTatarWordTokenizer

register('tagger', 'CrimeanTatarTagger',
         lambda language, spec: CrimeanTatarTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='crh')
register('word_tokenizer', 'CrimeanTatarWordTokenizer', lambda language: CrimeanTatarWordTokenizer(), language='crh')
