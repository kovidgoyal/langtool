"""Japanese (ja, ja-JP). Port of the LanguageTool module language-ja.

The Java module contains org.languagetool.language.Japanese,
org.languagetool.tokenizers.ja.JapaneseWordTokenizer and
org.languagetool.tagging.ja.JapaneseTagger. Japanese is ported
declaratively in langtool.languages (DoublePunctuationRule and
MultipleWhitespaceRule, the SRXSentenceTokenizer). JapaneseWordTokenizer
(langtool.lang.ja.tokenizers) uses the Sen morphological analyzer of
lucene-gosen with its IPADIC dictionary, ported in langtool.lang.ja.sen;
JapaneseTagger is in langtool.lang.ja.tagging.
"""

from ...extensions import register
from .tagging import JapaneseTagger
from .tokenizers import JapaneseWordTokenizer

register('word_tokenizer', 'JapaneseWordTokenizer',
         lambda language: JapaneseWordTokenizer(language.dictionary_path, language.download_dictionaries),
         language='ja')
register('tagger', 'JapaneseTagger', lambda language, spec: JapaneseTagger(), language='ja')
