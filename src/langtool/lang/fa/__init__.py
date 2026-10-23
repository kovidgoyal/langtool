"""Persian (fa). Port of the LanguageTool module language-fa.

The Java module contains org.languagetool.language.Persian,
org.languagetool.tokenizers.PersianWordTokenizer and the rules
org.languagetool.rules.fa.PersianCommaWhitespaceRule,
PersianDoublePunctuationRule, PersianWordRepeatBeginningRule,
PersianWordRepeatRule, SimpleReplaceRule, PersianSpaceBeforeRule and
WordCoherencyRule. Persian is ported declaratively in langtool.languages
(no tagger, no disambiguator, SRXSentenceTokenizer). PersianWordTokenizer is
in langtool.lang.fa.tokenizers, the rules are in langtool.lang.fa.rules;
they are registered for 'fa' only, other languages have rule classes named
SimpleReplaceRule and WordCoherencyRule too.
"""

from ...extensions import register
from .rules import (PersianCommaWhitespaceRule, PersianDoublePunctuationRule, PersianSpaceBeforeRule,
                    PersianWordRepeatBeginningRule, PersianWordRepeatRule, SimpleReplaceRule, WordCoherencyRule)
from .tokenizers import PersianWordTokenizer

register('word_tokenizer', 'PersianWordTokenizer', lambda language: PersianWordTokenizer(), language='fa')
register('rule', 'PersianCommaWhitespaceRule',
         lambda messages, language, user_config: PersianCommaWhitespaceRule(messages, language), language='fa')
register('rule', 'PersianDoublePunctuationRule',
         lambda messages, language, user_config: PersianDoublePunctuationRule(messages, language), language='fa')
register('rule', 'PersianWordRepeatBeginningRule',
         lambda messages, language, user_config: PersianWordRepeatBeginningRule(messages, language), language='fa')
register('rule', 'PersianWordRepeatRule',
         lambda messages, language, user_config: PersianWordRepeatRule(messages, language), language='fa')
register('rule', 'SimpleReplaceRule',
         lambda messages, language, user_config: SimpleReplaceRule(messages, language), language='fa')
register('rule', 'PersianSpaceBeforeRule',
         lambda messages, language, user_config: PersianSpaceBeforeRule(messages, language), language='fa')
register('rule', 'WordCoherencyRule',
         lambda messages, language, user_config: WordCoherencyRule(messages, language), language='fa')
