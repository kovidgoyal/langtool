"""Icelandic (is, is-IS). Port of the LanguageTool module language-is.

The package is called ``is_`` because ``is`` is a Python keyword; the
language code stays ``is``.

The Java module only contains org.languagetool.language.Icelandic, which is
ported declaratively in langtool.languages (DemoTagger, SRXSentenceTokenizer
and the core rules), so there are no components to register here. Its
HunspellNoSuggestionRule is not ported (spell checking).
"""
