"""Danish (da, da-DK). Port of the LanguageTool module language-da.

The Java module contains org.languagetool.language.Danish and
org.languagetool.tagging.da.DanishTagger. Both are ported declaratively in
langtool.languages: DanishTagger is a plain BaseTagger for da/danish.dict
(with the default tagLowercaseWithUppercase=true), the disambiguator is the
XmlRuleDisambiguator (without global disambiguation), the sentence tokenizer
is the SRXSentenceTokenizer and the rules are core rules, so there are no
components to register here. Its HunspellRule is not ported (spell checking).
"""
