"""Ukrainian (uk, uk-UA). Port of the LanguageTool module language-uk.

The Java module contains org.languagetool.language.Ukrainian (ported
declaratively in langtool.languages: SRX sentence tokenizer, quotes « » ‘ ’,
advanced typography disabled, the rule files grammar*.xml),
org.languagetool.tokenizers.uk.UkrainianWordTokenizer (tokenizers.py),
org.languagetool.tagging.uk: UkrainianTagger (tagging.py), CompoundTagger
and LetterEndingForNumericHelper (compound_tagger.py), PosTagHelper and
IPOSTag (pos_tag_helper.py), CompoundDebugLogger (debug output only, not
ported), org.languagetool.synthesis.uk.UkrainianSynthesizer (synthesis.py),
org.languagetool.tagging.disambiguation.uk: UkrainianHybridDisambiguator
(with the pre-disambiguation used by DisambiguationRuleTest),
SimpleDisambiguator and UkrainianMultiwordChunker (disambiguation.py), and
org.languagetool.rules.uk: the helpers ExtraDictionaryLoader, LemmaHelper,
InflectionHelper, VerbInflectionHelper, CaseGovernmentHelper, SearchHelper
and RuleException (helpers.py), the agreement rules
TokenAgreementAdjNounRule (agreement_adj_noun.py), TokenAgreementPrepNounRule
(agreement_prep_noun.py), TokenAgreementVerbNounRule
(agreement_verb_noun.py), TokenAgreementNounVerbRule
(agreement_noun_verb.py) and TokenAgreementNumrNounRule
(agreement_numr_noun.py) with their exception helpers, SimpleReplaceRule,
SimpleReplaceSoftRule and SimpleReplaceRenamedRule (replace_rules.py),
UkrainianCommaWhitespaceRule, UkrainianUppercaseSentenceStartRule,
UkrainianWordRepeatRule, TypographyRule, HiddenCharacterRule,
MissingHyphenRule, MixedAlphabetsRule and PunctuationCheckRule (rules.py),
and DateCheckFilter (filters.py). MorfologikUkrainianSpellerRule (spell
checking) is not ported, except for the misspelling check and the
suggestions SimpleReplaceRule asks for (spelling.py, the default spelling
rule of Ukrainian). The rules are registered for 'uk' only.
"""

from ...extensions import register
from .agreement_adj_noun import TokenAgreementAdjNounRule
from .agreement_noun_verb import TokenAgreementNounVerbRule
from .agreement_numr_noun import TokenAgreementNumrNounRule
from .agreement_prep_noun import TokenAgreementPrepNounRule
from .agreement_verb_noun import TokenAgreementVerbNounRule
from .disambiguation import UkrainianHybridDisambiguator
from .filters import DateCheckFilter
from .replace_rules import SimpleReplaceRenamedRule, SimpleReplaceRule, SimpleReplaceSoftRule
from .rules import (HiddenCharacterRule, MissingHyphenRule, MixedAlphabetsRule, PunctuationCheckRule,
                    TypographyRule, UkrainianCommaWhitespaceRule, UkrainianUppercaseSentenceStartRule,
                    UkrainianWordRepeatRule)
from .spelling import MorfologikUkrainianSpellerCheck
from .synthesis import create_ukrainian_synthesizer
from .tagging import UkrainianTagger
from .tokenizers import UkrainianWordTokenizer

register('word_tokenizer', 'UkrainianWordTokenizer', lambda language: UkrainianWordTokenizer(), language='uk')
register('tagger', 'UkrainianTagger',
         lambda language, spec: UkrainianTagger(language.dictionary(spec['dict']), language.resource_dir),
         language='uk')
register('synthesizer', 'UkrainianSynthesizer', create_ukrainian_synthesizer, language='uk')
register('disambiguator', 'UkrainianHybridDisambiguator', UkrainianHybridDisambiguator, language='uk')
register('default_spelling_rule', 'uk', MorfologikUkrainianSpellerCheck, language='uk')
for _cls in (UkrainianCommaWhitespaceRule, UkrainianUppercaseSentenceStartRule, UkrainianWordRepeatRule,
             TypographyRule, HiddenCharacterRule, TokenAgreementVerbNounRule, TokenAgreementNounVerbRule,
             TokenAgreementAdjNounRule, TokenAgreementPrepNounRule, TokenAgreementNumrNounRule, MixedAlphabetsRule,
             SimpleReplaceSoftRule, SimpleReplaceRenamedRule, PunctuationCheckRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='uk')
register('rule', 'MissingHyphenRule',
         lambda messages, language, user_config: MissingHyphenRule(messages, language.tagger.get_word_tagger()),
         language='uk')
register('rule', 'SimpleReplaceRule',
         lambda messages, language, user_config: SimpleReplaceRule(messages, language.get_default_spelling_rule(),
                                                                   language),
         language='uk')
register('filter', 'org.languagetool.rules.uk.DateCheckFilter', DateCheckFilter)
