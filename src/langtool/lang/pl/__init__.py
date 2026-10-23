"""Polish (pl, pl-PL). Port of the LanguageTool module language-pl.

The Java module contains org.languagetool.language.Polish,
org.languagetool.tagging.pl.PolishTagger,
org.languagetool.synthesis.pl.PolishSynthesizer,
org.languagetool.tagging.disambiguation.pl.PolishHybridDisambiguator,
org.languagetool.tokenizers.pl.PolishWordTokenizer, the rules
org.languagetool.rules.pl.CompoundRule, DashRule, PolishUnpairedBracketsRule,
PolishWordRepeatRule, SimpleReplaceRule, WordCoherencyRule and
MorfologikPolishSpellerRule and the filters DateCheckFilter and
DecadeSpellingFilter. Polish and PolishHybridDisambiguator are ported
declaratively in langtool.languages: PolishHybridDisambiguator is the
XmlRuleDisambiguator followed by the MultiWordChunker for pl/multiwords.txt,
and the sentence tokenizer is the SRXSentenceTokenizer. PolishTagger is in
langtool.lang.pl.tagging, PolishSynthesizer in langtool.lang.pl.synthesis,
PolishWordTokenizer (which gets the language's tagger, as in
Polish.createDefaultWordTokenizer()) in langtool.lang.pl.tokenizers, the
rules in langtool.lang.pl.rules (registered for 'pl' only, other languages
have rule classes with the same names) and the filters in
langtool.lang.pl.filters. MorfologikPolishSpellerRule (relevant rule and
default spelling rule) is not ported (spell checking).
"""

import os

from ...extensions import register
from .filters import DateCheckFilter, DecadeSpellingFilter
from .rules import (CompoundRule, DashRule, PolishUnpairedBracketsRule, PolishWordRepeatRule, SimpleReplaceRule,
                    WordCoherencyRule)
from .synthesis import PolishSynthesizer
from .tagging import PolishTagger
from .tokenizers import PolishWordTokenizer


def _word_tokenizer(language):
    tokenizer = PolishWordTokenizer()
    tokenizer.set_tagger(language.tagger)
    return tokenizer


def _synthesizer(language, spec):
    tags_path = language.resource_path(spec['tags'])
    return PolishSynthesizer(language.dictionary(spec['dict']), tags_path if os.path.exists(tags_path) else None,
                             language.resource_dir)


register('tagger', 'PolishTagger',
         lambda language, spec: PolishTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='pl')
register('synthesizer', 'PolishSynthesizer', _synthesizer, language='pl')
register('word_tokenizer', 'PolishWordTokenizer', _word_tokenizer, language='pl')
register('rule', 'CompoundRule',
         lambda messages, language, user_config: CompoundRule(messages, language, user_config), language='pl')
for _cls in (DashRule, PolishUnpairedBracketsRule, PolishWordRepeatRule, SimpleReplaceRule, WordCoherencyRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='pl')
register('filter', 'org.languagetool.rules.pl.DateCheckFilter', DateCheckFilter)
register('filter', 'org.languagetool.rules.pl.DecadeSpellingFilter', DecadeSpellingFilter)
