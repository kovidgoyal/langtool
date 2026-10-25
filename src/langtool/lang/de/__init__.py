"""German (de, de-DE, de-AT, de-CH). Port of the LanguageTool module
language-de.

The Java classes org.languagetool.language.German, GermanyGerman,
AustrianGerman, SwissGerman and NonSwissGerman (and the
GermanRuleDisambiguator: the MultiWordChunkers for multitoken-ignore.txt,
spelling_global.txt and multitoken-suggest.txt followed by the
XmlRuleDisambiguator with the global disambiguation rules) are ported
declaratively in langtool.languages; their filterRuleMatches and
toAdvancedTypography are in language.py. The other Java classes:

- jWordSplitter 4.7 (GermanWordSplitter etc.) and
  tokenizers.de.GermanCompoundTokenizer: compound_tokenizer.py;
  GermanWordTokenizer: tokenizers.py
- tagging.de: GermanTagger, SwissGermanTagger, AdjectiveTags, VerbPrefixes
  (tagging.py), GermanToken, AnalyzedGermanToken (german_token.py)
- synthesis.GermanSynthesizer: synthesis.py
- chunking.GermanChunker: chunking.py
- rules.de: GermanHelper (german_helper.py), GermanTools
  (german_tools.py), LineExpander (line_expander.py), the "is misspelled",
  ignore, match detection and suggestion parts of GermanSpellerRule,
  AustrianGermanSpellerRule and SwissGermanSpellerRule (spelling.py,
  spelling_data.py, on langtool.hunspell and langtool.hunspell_rule),
  GermanMultitokenSpeller (multitoken.py); AgreementRule (agreement.py),
  AgreementRuleAntiPatterns1-3 (agreement_antipatterns.py), AgreementRule2
  (agreement2.py), AgreementSuggestor2 (agreement_suggestor.py),
  AgreementTools (agreement_tools.py), PrepositionToCases
  (preposition_to_cases.py); CaseRule and CaseRuleExceptions
  (case_rule.py), CaseRuleAntiPatterns (case_rule_antipatterns.py),
  LanguageNames (language_names.py), DuUpperLowerCaseRule (du_rule.py);
  VerbAgreementRule (verb_agreement.py), SubjectVerbAgreementRule
  (subject_verb_agreement.py), MissingVerbRule (missing_verb.py);
  MissingCommaRelativeClauseRule (comma_rules.py), GermanCompoundRule,
  SwissCompoundRule, CompoundCoherencyRule, CompoundInfinitivRule,
  ProhibitedCompoundRule (compound_rules.py), OldSpellingRule and
  SpellingData (old_spelling.py), SimpleReplaceRule,
  GermanWrongWordInContextRule, WordCoherencyRule, WiederVsWiderRule,
  SimilarNameRule (replace_rules.py); the style rules
  (style_rules.py), GermanReadabilityRule (readability.py), the repeat
  rules GermanRepeatedWordsRule, GermanParagraphRepeatBeginningRule,
  GermanWordRepeatBeginningRule, GermanWordRepeatRule (repeat_rules.py);
  GermanCommaWhitespaceRule, GermanUnpairedBracketsRule,
  GermanUnpairedQuotesRule, SentenceWhitespaceRule,
  GermanDoublePunctuationRule, DashRule, UnitConversionRule
  (punctuation_rules.py); all the filters (filters.py).

Not ported: the spelling rules themselves (rule matches with messages for
the user; spell checking), UpperCaseNgramRule and
GermanConfusionProbabilityRule (language model); ProhibitedCompoundRule is
ported but, as in Java, only created with a language model (lm argument).
The rules are registered for 'de' only (other languages have classes with
the same names); SimpleGerman (de-DE-x-simple-language, a subclass of
GermanyGerman) registers the components it inherits in langtool.lang.de_simple.
"""

from ...extensions import register  # noqa: F401

# Each section below registers the components of one group of modules.

# === tokenizers, compound splitter, taggers, synthesizer ===
from .synthesis import synthesizer_factory as _synthesizer_factory  # noqa: E402
from .tagging import swiss_tagger_factory as _swiss_tagger_factory, tagger_factory as _tagger_factory  # noqa: E402
from .tokenizers import GermanWordTokenizer  # noqa: E402

register('tagger', 'SwissGermanTagger', _swiss_tagger_factory, language='de')
register('tagger', 'GermanTagger', _tagger_factory, language='de')
register('synthesizer', 'GermanSynthesizer', _synthesizer_factory, language='de')
register('word_tokenizer', 'GermanWordTokenizer', lambda language: GermanWordTokenizer(), language='de')
# === end tokenizers, compound splitter, taggers, synthesizer ===

# === speller (misspelling check, suggestions), multitoken speller ===


def _default_spelling_rule(language):
    """GermanSpellerRule / AustrianGermanSpellerRule / SwissGermanSpellerRule
    (imported when first needed)"""
    from .spelling import default_spelling_rule
    return default_spelling_rule(language)


def _multitoken_speller(language):
    """GermanMultitokenSpeller.INSTANCE"""
    from .multitoken import german_multitoken_speller
    return german_multitoken_speller(language)


register('default_spelling_rule', 'de', _default_spelling_rule, language='de')
register('multitoken_speller', 'de', _multitoken_speller, language='de')
# === end speller ===

# === chunker, filters, punctuation and typography rules ===
from .chunking import GermanChunker  # noqa: E402

register('chunker', 'GermanChunker', lambda language: GermanChunker(), language='de')

from . import filters as _filters  # noqa: E402

for _f in _filters.FILTERS:
    register('filter', 'org.languagetool.rules.de.' + _f.__name__, _f)

from . import punctuation_rules as _punctuation_rules  # noqa: E402

# (SentenceWhitespaceRule replaces the core rule of that name)
for _r in _punctuation_rules.RULES:
    register('rule', _r.__name__, lambda messages, language, user_config, _r=_r: _r(messages, language),
             language='de')
# === end chunker, filters, punctuation and typography rules ===

# === agreement rules ===
from .agreement import AgreementRule as _AgreementRule  # noqa: E402
from .agreement2 import AgreementRule2 as _AgreementRule2  # noqa: E402

register('rule', 'AgreementRule', lambda messages, language, user_config, **kw: _AgreementRule(messages, language),
         language='de')
register('rule', 'AgreementRule2', lambda messages, language, user_config, **kw: _AgreementRule2(messages, language),
         language='de')
# === end agreement rules ===

# === case rules ===
from .case_rule import CaseRule as _CaseRule  # noqa: E402
from .du_rule import DuUpperLowerCaseRule as _DuUpperLowerCaseRule  # noqa: E402

register('rule', 'CaseRule', lambda messages, language, user_config, **kw: _CaseRule(messages, language),
         language='de')
register('rule', 'DuUpperLowerCaseRule',
         lambda messages, language, user_config, **kw: _DuUpperLowerCaseRule(messages, language), language='de')
# === end case rules ===

# === verb agreement rules ===
from .missing_verb import MissingVerbRule  # noqa: E402
from .subject_verb_agreement import SubjectVerbAgreementRule  # noqa: E402
from .verb_agreement import VerbAgreementRule  # noqa: E402

for _cls in (VerbAgreementRule, SubjectVerbAgreementRule, MissingVerbRule):
    register('rule', _cls.__name__, _cls, language='de')  # (messages, language, user_config, **kwargs)
del _cls
# === end verb agreement rules ===

# === comma, compound, spelling and replace rules ===
from .comma_rules import MissingCommaRelativeClauseRule  # noqa: E402
from .compound_rules import (CompoundCoherencyRule, CompoundInfinitivRule, GermanCompoundRule,  # noqa: E402
                             ProhibitedCompoundRule, SwissCompoundRule)
from .old_spelling import OldSpellingRule  # noqa: E402
from .replace_rules import (GermanWrongWordInContextRule, SimilarNameRule, SimpleReplaceRule,  # noqa: E402
                            WiederVsWiderRule, WordCoherencyRule)

register('rule', 'MissingCommaRelativeClauseRule',
         lambda messages, language, user_config, behind=False:
         MissingCommaRelativeClauseRule(messages, language, user_config, behind=behind), language='de')
for _cls in (CompoundInfinitivRule, GermanCompoundRule, SwissCompoundRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language, user_config), language='de')
for _cls in (CompoundCoherencyRule, OldSpellingRule, GermanWrongWordInContextRule, SimilarNameRule,
             SimpleReplaceRule, WiederVsWiderRule, WordCoherencyRule):
    register('rule', _cls.__name__,
             lambda messages, language, user_config, _cls=_cls: _cls(messages, language), language='de')
# needs a language model (Java: German.getRelevantLanguageModelRules), not in the rules of languages.py
register('rule', 'ProhibitedCompoundRule',
         lambda messages, language, user_config, lm=None: ProhibitedCompoundRule(messages, lm, user_config, language),
         language='de')
# === end comma, compound, spelling and replace rules ===

# === style rules ===
from . import readability as _readability, repeat_rules as _repeat_rules, style_rules as _style_rules  # noqa: E402

for _name in ('GermanFillerWordsRule', 'GermanStyleRepeatedWordRule', 'StyleRepeatedVeryShortSentences',
              'StyleTooOftenUsedVerbRule', 'StyleTooOftenUsedNounRule', 'StyleTooOftenUsedAdjectiveRule',
              'PassiveSentenceRule', 'SentenceWithModalVerbRule', 'SentenceWithManRule',
              'ConjunctionAtBeginOfSentenceRule', 'NonSignificantVerbsRule', 'UnnecessaryPhraseRule'):
    register('rule', _name, (lambda cls: lambda messages, language, user_config, **kw:
                             cls(messages, language, user_config, **kw))(getattr(_style_rules, _name)),
             language='de')
register('rule', 'StyleRepeatedSentenceBeginning',
         lambda messages, language, user_config: _style_rules.StyleRepeatedSentenceBeginning(messages, language),
         language='de')
register('rule', 'RedundantModalOrAuxiliaryVerb',
         lambda messages, language, user_config: _style_rules.RedundantModalOrAuxiliaryVerb(messages, language),
         language='de')
register('rule', 'LongSentenceRule',
         lambda messages, language, user_config, max_words=50:
         _style_rules.LongSentenceRule(messages, language, user_config, max_words), language='de')
register('rule', 'GermanReadabilityRule',
         lambda messages, language, user_config, too_easy_test=False, level=-1, default_on=False:
         _readability.GermanReadabilityRule(messages, language, user_config, too_easy_test, level, default_on),
         language='de')
register('rule', 'GermanRepeatedWordsRule',
         lambda messages, language, user_config: _repeat_rules.GermanRepeatedWordsRule(messages), language='de')
for _name in ('GermanParagraphRepeatBeginningRule', 'GermanWordRepeatBeginningRule', 'GermanWordRepeatRule'):
    register('rule', _name, (lambda cls: lambda messages, language, user_config:
                             cls(messages, language))(getattr(_repeat_rules, _name)), language='de')
# === end style rules ===

# === language (filterRuleMatches, typography) ===
from .language import filter_rule_matches, to_advanced_typography  # noqa: E402

register('to_advanced_typography', 'de', to_advanced_typography, language='de')
register('filter_rule_matches', 'de', filter_rule_matches, language='de')
# === end language ===
