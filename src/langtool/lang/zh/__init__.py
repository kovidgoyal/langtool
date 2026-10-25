"""Chinese (zh, zh-CN). Port of the LanguageTool module language-zh.

The Java module contains org.languagetool.language.Chinese,
org.languagetool.tokenizers.zh.ChineseWordTokenizer and
ChineseSentenceTokenizer, org.languagetool.tagging.zh.ChineseTagger and
org.languagetool.rules.zh.ChineseConfusionProbabilityRule. Chinese is ported
declaratively in langtool.languages (DoublePunctuationRule and
MultipleWhitespaceRule); ChineseConfusionProbabilityRule is a language model
rule and not ported. The tokenizers (langtool.lang.zh.tokenizers) use the
HanLP library, ported in langtool.lang.zh.hanlp; ChineseTagger is in
langtool.lang.zh.tagging.
"""

from ...extensions import register
from .tagging import ChineseTagger
from .tokenizers import ChineseSentenceTokenizer, ChineseWordTokenizer

register('word_tokenizer', 'ChineseWordTokenizer',
         lambda language: ChineseWordTokenizer(language.dictionary_path, language.download_dictionaries),
         language='zh')
register('sentence_tokenizer', 'ChineseSentenceTokenizer', lambda language: ChineseSentenceTokenizer(),
         language='zh')
register('tagger', 'ChineseTagger', lambda language, spec: ChineseTagger(), language='zh')
