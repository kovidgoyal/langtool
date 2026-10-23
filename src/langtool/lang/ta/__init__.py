"""Tamil (ta, ta-IN). Port of the LanguageTool module language-ta.

The Java module contains org.languagetool.language.Tamil and
org.languagetool.language.tagging.TamilTagger. Both are ported declaratively
in langtool.languages: TamilTagger is a plain BaseTagger for ta/tamil.dict
(with the default tagLowercaseWithUppercase=true), the sentence tokenizer is
the SRXSentenceTokenizer and the rules are core rules, so there are no
components to register here.
"""
