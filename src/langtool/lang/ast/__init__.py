"""Asturian (ast, ast-ES). Port of the LanguageTool module language-ast.

The Java module contains org.languagetool.language.Asturian and
org.languagetool.tagging.ast.AsturianTagger. Both are ported declaratively in
langtool.languages: AsturianTagger is a plain BaseTagger for
ast/asturian.dict (with the default tagLowercaseWithUppercase=true; the
Locale("ast") has no special case mapping), the disambiguator is the default
DemoDisambiguator, the sentence tokenizer is the SRXSentenceTokenizer and the
rules are core rules, so there are no components to register here. Its
MorfologikAsturianSpellerRule (org.languagetool.language.rules.ast) is not
ported (spell checking).
"""
