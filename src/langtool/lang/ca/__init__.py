"""Catalan (ca-ES, ca-ES-valencia, ca-ES-balear). Port of the LanguageTool
module language-ca.

The Java module contains org.languagetool.language.Catalan, ValencianCatalan
and BalearicCatalan, org.languagetool.tagging.ca.CatalanTagger and
VerbClassifier, org.languagetool.tagging.disambiguation.ca.CatalanHybridDisambiguator
and CatalanMultitokenDisambiguator, org.languagetool.synthesis.ca.CatalanSynthesizer
and VerbSynthesizer, org.languagetool.tokenizers.ca.CatalanWordTokenizer and
the rules, filters and helpers of org.languagetool.rules.ca.

The language classes and CatalanHybridDisambiguator (the MultiWordChunkers
for spelling_global.txt and ca/multiwords.txt, the XmlRuleDisambiguator of
ca-ES with the global disambiguation rules, then the
CatalanMultitokenDisambiguator) are ported declaratively in langtool.languages;
the code of Catalan (toAdvancedTypography, adaptSuggestion,
filterRuleMatches, filterRuleMatchesAfterOverlapping) is in
langtool.lang.ca.language and prepareLineForSpeller in langtool.lang.ca.spelling.
CatalanTagger and VerbClassifier are in langtool.lang.ca.tagging,
CatalanSynthesizer and VerbSynthesizer in langtool.lang.ca.synthesis,
CatalanWordTokenizer in langtool.lang.ca.tokenizers, CatalanMultitokenSpeller,
CatalanMorfologikMultitokenSpeller (langtool.lang.ca.spelling) and
CatalanMultitokenDisambiguator in langtool.lang.ca.multitoken,
PronomsFeblesHelper, ApostophationHelper, VerbsHelper and NounToVerbHelper in
langtool.lang.ca.helpers. The rules are in langtool.lang.ca.rules
(CatalanUnpairedBracketsRule, CatalanWordRepeatRule, CatalanPhraseRepeatRule,
CatalanUnpairedQuestionMarksRule, CatalanUnpairedExclamationMarksRule,
PronomFebleDuplicateRule, CatalanWordRepeatBeginningRule, CompoundRule,
CatalanPunctuationMarkAtParagraphEnd, IgnoreProperNouns,
CatalanRepeatedWordsRule) and langtool.lang.ca.replace_rules (the
SimpleReplace* rules, AbstractSimpleReplaceLemmasRule,
ReplaceOperationNamesRule, CheckCaseRule, CatalanWrongWordInContextRule,
WordCoherencyRule, WordCoherencyValencianRule), registered for 'ca' only.
The filters are in langtool.lang.ca.filters, verb_filters, phrase_filters,
que_inici (QueIniciFilter) and agreement (PostponedAdjectiveConcordanceFilter);
CatalanRemoteRewriteHelper, CatalanRemoteRewriteFilter and
CatalanSplitLongSentenceRule in langtool.lang.ca.remote.

Not ported: MorfologikCatalanSpellerRule (spell checking), except for its
misspelling check and single-word suggestions (langtool.lang.ca.spelling,
registered as the default spelling rule of Catalan), and CatalanRemoteRule
(a remote rule). Catalan.hasMinMatchesRules() and getAllPossibleTags() are
not used here.
"""

import os
import threading

from ...extensions import register, synthesizer_resources
from .language import (adapt_suggestion, filter_rule_matches, filter_rule_matches_after_overlapping,
                       to_advanced_typography)
from .multitoken import CatalanMultitokenDisambiguator, catalan_multitoken_speller
from .spelling import MorfologikCatalanSpellerCheck
from .synthesis import CatalanSynthesizer
from .tagging import CatalanTagger
from .tokenizers import CatalanWordTokenizer

_taggers = {}
_lock = threading.Lock()


def catalan_tagger(language, is_valencian=False):
    """CatalanTagger.INSTANCE_CAT (is_valencian false) or INSTANCE_VAL"""
    with _lock:
        t = _taggers.get(is_valencian)
        if t is None:
            from ...api import get_language
            ca = get_language('ca-ES')
            t = _taggers[is_valencian] = CatalanTagger(ca.dictionary('ca/ca-ES.dict'), ca.resource_dir,
                                                       os.path.join(ca.rules_root, 'ca'), is_valencian)
        return t


def _tagger(language, spec):
    return catalan_tagger(language, language.variant == 'valencia')


def _synthesizer(language, spec):
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return CatalanSynthesizer(dictionary, tags_path, 'ca', language.resource_dir, number_speller, roman_numberer,
                              language.code)


register('tagger', 'CatalanTagger', _tagger, language='ca')
register('synthesizer', 'CatalanSynthesizer', _synthesizer, language='ca')
# (CatalanWordTokenizer.INSTANCE uses CatalanTagger.INSTANCE_CAT for all variants)
register('word_tokenizer', 'CatalanWordTokenizer', lambda language: CatalanWordTokenizer(catalan_tagger(language)),
         language='ca')
register('disambiguator', 'CatalanMultitokenDisambiguator', CatalanMultitokenDisambiguator, language='ca')
register('default_spelling_rule', 'ca', MorfologikCatalanSpellerCheck, language='ca')
register('multitoken_speller', 'ca', catalan_multitoken_speller, language='ca')
register('adapt_suggestion', 'ca', adapt_suggestion, language='ca')
register('to_advanced_typography', 'ca', to_advanced_typography, language='ca')
register('filter_rule_matches', 'ca', filter_rule_matches, language='ca')
register('filter_rule_matches_after_overlapping', 'ca', filter_rule_matches_after_overlapping, language='ca')

# the filters and rules of the modules (each module lists its filter classes in FILTERS and its rule
# factories, called with (messages, language, user_config, **kwargs), in RULES)
from . import (agreement, filters, phrase_filters, que_inici, remote, replace_rules, rules,  # noqa: E402
               verb_filters)

_P = 'org.languagetool.rules.ca.'
for _module in (filters, verb_filters, phrase_filters, que_inici, agreement, remote, replace_rules, rules):
    for _cls in _module.FILTERS:
        register('filter', _P + _cls.__name__, _cls)
    for _name, _factory in _module.RULES.items():
        register('rule', _name, _factory, language='ca')
