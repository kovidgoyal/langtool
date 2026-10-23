"""Declarative definitions of the supported languages, derived from the Java
Language classes of the LanguageTool language modules.

Each language has:
 name, countries, variants: list of dicts with code (short code with country and
   variant), name, countries, variant, default_enabled_rules, default_disabled_rules
 default_variant: code of the default variant
 tagger: dict(dict=path of .dict relative to the resource dir,
              lowercase_with_uppercase=bool) or None for no tagging
 synthesizer: dict(dict=..., tags=...) or None
 word_tokenizer: name of the tokenizer implementation ('core' by default)
 disambiguator: list of stages, each one of
     ('xml', use_global_disambiguation)
     ('multiword', file, dict(allow_first_capitalized, allow_all_uppercase,
                             allow_titlecase, default_tag, ignore_spelling,
                             remove_previous_tags))
     ('multiword2', file, dict(allow_first_capitalized, ...))
     ('custom', name)  -- language specific code
 rules: list of (rule class name, kwargs) -- core rules are implemented in
   langtool.rules.core, others are language specific and are looked up in
   the extensions registry.
"""

_DEFAULT_BRACKETS = None

_NONE = '_NONE_'


def mw(path, afc=False, aau=False, atc=False, default_tag=None, ignore_spelling=False, remove_previous_tags=False):
    return ('multiword', path, dict(allow_first_capitalized=afc, allow_all_uppercase=aau, allow_titlecase=atc,
                                    default_tag=default_tag, ignore_spelling=ignore_spelling,
                                    remove_previous_tags=remove_previous_tags))


def xml(use_global=False):
    return ('xml', use_global)


def R(name, **kw):
    return (name, kw)


def brackets(start, end, rule_id=None):
    kw = dict(start_symbols=start, end_symbols=end)
    if rule_id:
        kw['rule_id'] = rule_id
    return R('GenericUnpairedBracketsRule', **kw)


def V(code, countries=None, name=None, variant=None, enabled=(), disabled=(), **kw):
    d = dict(code=code)
    if countries is not None:
        d['countries'] = countries
    if name is not None:
        d['name'] = name
    if variant is not None:
        d['variant'] = variant
    if enabled:
        d['default_enabled_rules'] = list(enabled)
    if disabled:
        d['default_disabled_rules'] = list(disabled)
    d.update(kw)
    return d


SOFT_HYPHEN = '[­]'

_EN_RULES = [
    R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
    R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule', max_spaces_between_sentences=2),
    R('WhiteSpaceBeforeParagraphEnd'), R('WhiteSpaceAtBeginOfParagraph'), R('EmptyLineRule'),
    R('LongSentenceRule', max_words=40), R('LongParagraphRule'), R('ParagraphRepeatBeginningRule'),
    R('PunctuationMarkAtParagraphEnd'), R('PunctuationMarkAtParagraphEnd2'),
    R('ConsistentApostrophesRule'), R('EnglishSpecificCaseRule'), R('EnglishUnpairedBracketsRule'),
    R('EnglishUnpairedQuotesRule'), R('EnglishWordRepeatRule'), R('AvsAnRule'),
    R('EnglishWordRepeatBeginningRule'), R('CompoundRule'), R('ContractionSpellingRule'),
    R('EnglishWrongWordInContextRule'), R('EnglishDashRule'), R('WordCoherencyRule'),
    R('EnglishDiacriticsRule'), R('EnglishPlainEnglishRule'), R('EnglishRedundancyRule'),
    R('SimpleReplaceRule'), R('SimpleReplaceProfanityRule'), R('ReadabilityRule', too_easy_test=False),
    R('ReadabilityRule', too_easy_test=True), R('EnglishRepeatedWordsRule'), R('StyleTooOftenUsedVerbRule'),
    R('StyleTooOftenUsedNounRule'), R('StyleTooOftenUsedAdjectiveRule'),
]

_DE_RULES = [
    R('GermanCommaWhitespaceRule'), R('GermanUnpairedBracketsRule'), R('GermanUnpairedQuotesRule'),
    R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
    R('WhiteSpaceAtBeginOfParagraph'), R('EmptyLineRule'), R('LongParagraphRule'),
    R('PunctuationMarkAtParagraphEnd'), R('SimpleReplaceRule'), R('OldSpellingRule'),
    R('GermanSentenceWhitespaceRule'), R('GermanDoublePunctuationRule'), R('MissingVerbRule'),
    R('GermanWordRepeatRule'), R('GermanWordRepeatBeginningRule'), R('GermanWrongWordInContextRule'),
    R('AgreementRule'), R('AgreementRule2'), R('CaseRule'), R('DashRule'), R('VerbAgreementRule'),
    R('SubjectVerbAgreementRule'), R('WordCoherencyRule'), R('SimilarNameRule'), R('WiederVsWiderRule'),
    R('GermanStyleRepeatedWordRule'), R('CompoundCoherencyRule'), R('GermanLongSentenceRule'),
    R('GermanFillerWordsRule'), R('PassiveSentenceRule'), R('SentenceWithModalVerbRule'),
    R('SentenceWithManRule'), R('ConjunctionAtBeginOfSentenceRule'), R('NonSignificantVerbsRule'),
    R('UnnecessaryPhraseRule'), R('GermanParagraphRepeatBeginningRule'), R('DuUpperLowerCaseRule'),
    R('UnitConversionRule'), R('MissingCommaRelativeClauseRule'), R('MissingCommaRelativeClauseRule', behind=True),
    R('RedundantModalOrAuxiliaryVerb'), R('GermanReadabilityRule', too_easy_test=True),
    R('GermanReadabilityRule', too_easy_test=False), R('CompoundInfinitivRule'),
    R('StyleRepeatedVeryShortSentences'), R('StyleRepeatedSentenceBeginning'), R('GermanRepeatedWordsRule'),
    R('StyleTooOftenUsedVerbRule'), R('StyleTooOftenUsedNounRule'), R('StyleTooOftenUsedAdjectiveRule'),
    R('ProhibitedCompoundRule'),
]

_PT_RULES = [
    R('CommaWhitespaceRule'),
    brackets(['[', '(', '{', '"', '“'], [']', ')', '}', '"', '”']),
    R('LongSentenceRule', max_words=50), R('LongParagraphRule'), R('UppercaseSentenceStartRule'),
    R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
    R('WhiteSpaceAtBeginOfParagraph'), R('EmptyLineRule'), R('ParagraphRepeatBeginningRule'),
    R('PunctuationMarkAtParagraphEnd', default_active=True), R('PostReformPortugueseCompoundRule'),
    R('PortugueseColourHyphenationRule'), R('PortugueseOrthographyReplaceRule'), R('PortugueseReplaceRule'),
    R('PortugueseBarbarismsRule'), R('PortugueseClicheRule'), R('PortugueseFillerWordsRule'),
    R('PortugueseRedundancyRule'), R('PortugueseWordinessRule'), R('PortugueseWikipediaRule'),
    R('PortugueseWordRepeatRule'), R('PortugueseWordRepeatBeginningRule'), R('PortugueseAccentuationCheckRule'),
    R('PortugueseDiacriticsRule'), R('PortugueseWrongWordInContextRule'), R('PortugueseWordCoherencyRule'),
    R('PortugueseUnitConversionRule'), R('PortugueseReadabilityRule', too_easy_test=True),
    R('PortugueseReadabilityRule', too_easy_test=False), R('DoublePunctuationRule'),
    R('EnglishContractionSpellingRule'),
]

_CA_RULES = [
    R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('CatalanUnpairedBracketsRule'),
    R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'),
    R('LongSentenceRule', max_words=60), R('CatalanWordRepeatRule'), R('CatalanPhraseRepeatRule'),
    R('CatalanUnpairedQuestionMarksRule'), R('CatalanUnpairedExclamationMarksRule'),
    R('CatalanWrongWordInContextRule'), R('SimpleReplaceVerbsRule'), R('SimpleReplaceBalearicRule'),
    R('SimpleReplaceRule'), R('SimpleReplaceMultiwordsRule'), R('ReplaceOperationNamesRule'),
    R('SimpleReplaceDiacriticsIEC'), R('SimpleReplaceAnglicism'), R('PronomFebleDuplicateRule'),
    R('CheckCaseRule'), R('SimpleReplaceAdverbsMent'), R('CatalanWordRepeatBeginningRule'), R('CompoundRule'),
    R('SimpleReplaceDNVRule'), R('SimpleReplaceDNVColloquialRule'), R('SimpleReplaceDNVSecondaryRule'),
    R('WordCoherencyRule'), R('CatalanPunctuationMarkAtParagraphEnd'), R('CatalanSplitLongSentenceRule'),
]

LANGUAGES = {
    'ar': dict(
        name='Arabic', countries=['', 'SA', 'DZ', 'BH', 'EG', 'IQ', 'JO', 'KW', 'LB', 'LY', 'MA', 'OM', 'QA', 'SD',
                                  'SY', 'TN', 'AE', 'YE'],
        variants=[V('ar')],
        tagger=dict(dict='ar/arabic.dict', lowercase_with_uppercase=True, impl='ArabicTagger'),
        synthesizer=dict(dict='ar/arabic_synth.dict', tags='ar/arabic_tags.txt', impl='ArabicSynthesizer'),
        word_tokenizer='ArabicWordTokenizer',
        disambiguator=[mw('ar/multiwords.txt'), xml()],
        rules=[R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'),
               brackets(['[', '(', '{', '«', '﴾', '"', "'"], [']', ')', '}', '»', '﴿', '"', "'"]),
               R('CommaWhitespaceRule'), R('LongSentenceRule', max_words=50), R('ArabicCommaWhitespaceRule'),
               R('ArabicQuestionMarkWhitespaceRule'), R('ArabicSemiColonWhitespaceRule'),
               R('ArabicDoublePunctuationRule'), R('ArabicWordRepeatRule'), R('ArabicSimpleReplaceRule'),
               R('ArabicDiacriticsRule'), R('ArabicDarjaRule'), R('ArabicHomophonesRule'), R('ArabicRedundancyRule'),
               R('ArabicWordCoherencyRule'), R('ArabicWordinessRule'), R('ArabicWrongWordInContextRule'),
               R('ArabicTransVerbRule'), R('ArabicInflectedOneWordReplaceRule')],
    ),
    'ast': dict(
        name='Asturian', countries=['ES'], variants=[V('ast-ES')],
        tagger=dict(dict='ast/asturian.dict', lowercase_with_uppercase=True),
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    'be': dict(
        name='Belarusian', countries=['BY'], variants=[V('be-BY')],
        tagger=None, word_tokenizer='BelarusianWordTokenizer', ignored_characters_regex='[­́̀]',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
               R('WhiteSpaceAtBeginOfParagraph'), R('LongSentenceRule', max_words=50), R('LongParagraphRule'),
               R('ParagraphRepeatBeginningRule'), R('PunctuationMarkAtParagraphEnd2'), R('SimpleReplaceRule'),
               R('BelarusianSpecificCaseRule')],
    ),
    'br': dict(
        name='Breton', countries=['FR'], variants=[V('br-FR')],
        tagger=dict(dict='br/breton.dict', lowercase_with_uppercase=True, impl='BretonTagger'),
        word_tokenizer='BretonWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('TopoReplaceRule')],
    ),
    'ca': dict(
        name='Catalan', countries=['ES'], default_variant='ca-ES',
        variants=[
            V('ca-ES', name='Catalan'),
            V('ca-ES-valencia', name='Catalan (Valencian)', variant='valencia',
              enabled=['EXIGEIX_VERBS_VALENCIANS', 'EXIGEIX_ACCENTUACIO_VALENCIANA', 'EXIGEIX_POSSESSIUS_U',
                       'EXIGEIX_VERBS_EIX', 'EXIGEIX_VERBS_ISC', 'PER_PER_A_INFINITIU', 'FINS_EL_AVL', 'LES_HA_FETES'],
              disabled=['EXIGEIX_VERBS_CENTRAL', 'EXIGEIX_ACCENTUACIO_GENERAL', 'EXIGEIX_POSSESSIUS_V',
                        'EVITA_PRONOMS_VALENCIANS', 'EVITA_DEMOSTRATIUS_EIXE', 'VOCABULARI_VALENCIA', 'EXIGEIX_US',
                        'FINS_EL_GENERAL', 'EVITA_INFINITIUS_INDRE', 'EVITA_DEMOSTRATIUS_ESTE', 'CASTIC_CASTIG'],
              extra_rules=[R('WordCoherencyValencianRule')]),
            V('ca-ES-balear', name='Catalan (Balearic)', variant='balear', enabled=['EXIGEIX_VERBS_BALEARS'],
              disabled=['EXIGEIX_VERBS_CENTRAL', 'CA_SIMPLE_REPLACE_BALEARIC']),
        ],
        tagger=dict(dict='ca/ca-ES.dict', lowercase_with_uppercase=False, impl='CatalanTagger'),
        synthesizer=dict(dict='ca/ca-ES_synth.dict', tags='ca/ca-ES_tags.txt', impl='CatalanSynthesizer'),
        word_tokenizer='CatalanWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, 'NPCN000'),
                       mw('ca/multiwords.txt', True, True, False, remove_previous_tags=True), xml(True),
                       ('custom', 'CatalanMultitokenDisambiguator')],
        rules=_CA_RULES,
    ),
    'crh': dict(
        name='Crimean Tatar', countries=['UA'], variants=[V('crh-UA')],
        tagger=dict(dict='crh/crimean_tatar.dict', lowercase_with_uppercase=False, impl='CrimeanTatarTagger'),
        synthesizer=dict(dict='crh/crimean_tatar_synth.dict', tags='crh/crimean_tatar_synth.dict_tags.txt'),
        word_tokenizer='CrimeanTatarWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
               R('WhiteSpaceAtBeginOfParagraph')],
    ),
    'da': dict(
        name='Danish', countries=['DK'], variants=[V('da-DK')],
        tagger=dict(dict='da/danish.dict', lowercase_with_uppercase=True),
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '"', '”'], [']', ')', '}', '"', '”']),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    'de': dict(
        name='German', countries=['LU', 'LI', 'BE'], default_variant='de-DE', ignored_characters_regex=SOFT_HYPHEN,
        variants=[
            V('de', name='German'),
            V('de-DE', countries=['DE'], name='German (Germany)', extra_rules=[R('GermanCompoundRule')],
              extra_rule_files=['de-DE-AT/grammar.xml']),
            V('de-AT', countries=['AT'], name='German (Austria)', extra_rules=[R('GermanCompoundRule')],
              extra_rule_files=['de-DE-AT/grammar.xml']),
            V('de-CH', countries=['CH'], name='German (Swiss)', extra_rules=[R('SwissCompoundRule')],
              tagger_impl='SwissGermanTagger'),
        ],
        tagger=dict(dict='de/german.dict', lowercase_with_uppercase=True, impl='GermanTagger'),
        synthesizer=dict(dict='de/german_synth.dict', tags='de/german_tags.txt', impl='GermanSynthesizer'),
        word_tokenizer='GermanWordTokenizer',
        disambiguator=[mw('de/multitoken-ignore.txt', True, True, False, _NONE, ignore_spelling=True),
                       mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('de/multitoken-suggest.txt', True, True, False, _NONE, ignore_spelling=True),
                       xml(True)],
        rules=_DE_RULES,
    ),
    'de-DE-x-simple-language': dict(
        name='Simple German', countries=['DE'], resource_language='de', ignored_characters_regex=SOFT_HYPHEN,
        variants=[V('de-DE-x-simple-language')],
        tagger=dict(dict='de/german.dict', lowercase_with_uppercase=True, impl='GermanTagger'),
        synthesizer=dict(dict='de/german_synth.dict', tags='de/german_tags.txt', impl='GermanSynthesizer'),
        word_tokenizer='GermanWordTokenizer',
        disambiguator=[mw('de/multitoken-ignore.txt', True, True, False, _NONE, ignore_spelling=True),
                       mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('de/multitoken-suggest.txt', True, True, False, _NONE, ignore_spelling=True),
                       ('xml_of', 'de', True)],
        rules=[R('SimpleGermanLongSentenceRule')],
    ),
    'el': dict(
        name='Greek', countries=['GR'], variants=[V('el-GR')],
        tagger=dict(dict='el/greek.dict', lowercase_with_uppercase=True, impl='GreekTagger'),
        synthesizer=dict(dict='el/greek_synth.dict', tags='el/greek_tags.txt'),
        word_tokenizer='GreekWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '“', '"', '«'], [']', ')', '}', '”', '"', '»'], 'EL_UNPAIRED_BRACKETS'),
               R('LongSentenceRule', max_words=50), R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'),
               R('GreekWordRepeatBeginningRule'), R('WordRepeatRule'), R('ReplaceHomonymsRule'),
               R('GreekSpecificCaseRule'), R('NumeralStressRule'), R('GreekRedundancyRule')],
    ),
    'en': dict(
        name='English', countries=[], default_variant='en-US',
        variants=[
            V('en', name='English'),
            V('en-US', countries=['US'], name='English (US)', extra_rules=[R('AmericanReplaceRule'),
                                                                           R('UnitConversionRuleUS')]),
            V('en-GB', countries=['GB'], name='English (GB)', extra_rules=[R('BritishReplaceRule'),
                                                                           R('UnitConversionRuleImperial')]),
            V('en-AU', countries=['AU'], name='English (Australian)', extra_rules=[R('UnitConversionRuleImperial')]),
            V('en-CA', countries=['CA'], name='English (Canadian)', extra_rules=[R('UnitConversionRuleImperial')]),
            V('en-NZ', countries=['NZ'], name='English (New Zealand)',
              extra_rules=[R('NewZealandReplaceRule'), R('UnitConversionRuleImperial')]),
            V('en-ZA', countries=['ZA'], name='English (South African)'),
        ],
        tagger=dict(dict='en/english.dict', lowercase_with_uppercase=False, impl='EnglishTagger'),
        synthesizer=dict(dict='en/english_synth.dict', tags='en/english_tags.txt', impl='EnglishSynthesizer'),
        word_tokenizer='EnglishWordTokenizer',
        disambiguator=[mw('spelling_global.txt', True, True, False, _NONE, ignore_spelling=True),
                       mw('en/multiwords.txt', True, True, False, ignore_spelling=True, remove_previous_tags=True),
                       xml(True)],
        chunker='EnglishChunker',
        rules=_EN_RULES,
    ),
    'eo': dict(
        name='Esperanto', countries=[], variants=[V('eo')],
        tagger=dict(impl='EsperantoTagger'), word_tokenizer='EsperantoWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule'),
               R('SentenceWhitespaceRule')],
    ),
    'es': dict(
        name='Spanish', countries=['ES', '', 'MX', 'GT', 'CR', 'PA', 'DO', 'VE', 'PE', 'AR', 'EC', 'CL', 'UY', 'PY',
                                   'BO', 'SV', 'HN', 'NI', 'PR', 'US', 'CU'], default_variant='es',
        variants=[V('es', name='Spanish'), V('es-AR', countries=['AR'], name='Spanish (voseo)', disabled=['VOSEO'])],
        tagger=dict(dict='es/es-ES.dict', lowercase_with_uppercase=True, impl='SpanishTagger'),
        synthesizer=dict(dict='es/es-ES_synth.dict', tags='es/es-ES_tags.txt', impl='SpanishSynthesizer'),
        word_tokenizer='SpanishWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, 'NPCN000'),
                       mw('es/multiwords.txt', True, True, False, remove_previous_tags=True), xml(True)],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('SpanishUnpairedBracketsRule'),
               R('QuestionMarkRule'), R('UppercaseSentenceStartRule'), R('SpanishWordRepeatRule'),
               R('MultipleWhitespaceRule'), R('SpanishWikipediaRule'), R('SpanishWrongWordInContextRule'),
               R('LongSentenceRule', max_words=60), R('LongParagraphRule'), R('SimpleReplaceRule'),
               R('SimpleReplaceVerbsRule'), R('SpanishWordRepeatBeginningRule'), R('CompoundRule'),
               R('SpanishRepeatedWordsRule')],
    ),
    'fa': dict(
        name='Persian', countries=['IR', 'AF'], variants=[V('fa')],
        tagger=None, word_tokenizer='PersianWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('MultipleWhitespaceRule'),
               R('LongSentenceRule', max_words=50), R('PersianCommaWhitespaceRule'),
               R('PersianDoublePunctuationRule'), R('PersianWordRepeatBeginningRule'), R('PersianWordRepeatRule'),
               R('SimpleReplaceRule'), R('PersianSpaceBeforeRule'), R('WordCoherencyRule')],
    ),
    'fr': dict(
        name='French', countries=['FR', '', 'LU', 'MC', 'CM', 'CI', 'HT', 'ML', 'SN', 'CD', 'MA', 'RE'],
        default_variant='fr', ignored_characters_regex=SOFT_HYPHEN,
        variants=[V('fr', name='French'), V('fr-CA', countries=['CA'], name='French (Canada)',
                                            disabled=['DOUBLER_UNE_CLASSE']),
                  V('fr-CH', countries=['CH'], name='French (Switzerland)', disabled=['DOUBLER_UNE_CLASSE']),
                  V('fr-BE', countries=['BE'], name='French (Belgium)', disabled=['DOUBLER_UNE_CLASSE'])],
        tagger=dict(dict='fr/french.dict', lowercase_with_uppercase=False, impl='FrenchTagger'),
        synthesizer=dict(dict='fr/french_synth.dict', tags='fr/french_tags.txt', impl='FrenchSynthesizer'),
        word_tokenizer='FrenchWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('fr/multiwords.txt', True, True, False, remove_previous_tags=True), xml(True)],
        rules=[R('CommaWhitespaceRule', quotes_whitespace_check=False), R('DoublePunctuationRule'),
               brackets(['[', '(', '{'], [']', ')', '}']), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('LongSentenceRule', max_words=40),
               R('LongParagraphRule'), R('CompoundRule'), R('QuestionWhitespaceStrictRule'),
               R('QuestionWhitespaceRule'), R('SimpleReplaceRule'), R('FrenchRepeatedWordsRule')],
    ),
    'ga': dict(
        name='Irish', countries=['IE'], variants=[V('ga-IE')],
        tagger=dict(dict='ga/irish.dict', lowercase_with_uppercase=True, impl='IrishTagger'),
        synthesizer=dict(dict='ga/irish_synth.dict', tags='ga/irish_tags.txt'),
        disambiguator=[mw('ga/multiwords.txt'), xml()],
        rules=[R('CommaWhitespaceRule'),
               brackets(['[', '(', '{', '"', '“'], [']', ')', '}', '"', '”']),
               R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'), R('LongSentenceRule', max_words=50),
               R('LongParagraphRule'), R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'),
               R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'), R('WhiteSpaceAtBeginOfParagraph'),
               R('ParagraphRepeatBeginningRule'), R('WordRepeatRule'), R('LogainmRule'), R('PeopleRule'),
               R('SpacesRule'), R('CompoundRule'), R('PrestandardReplaceRule'), R('IrishReplaceRule'),
               R('IrishFGBEqReplaceRule'), R('EnglishHomophoneRule'), R('DhaNoBeirtRule'),
               R('DativePluralStandardReplaceRule'), R('IrishSpecificCaseRule')],
    ),
    'gl': dict(
        name='Galician', countries=['ES'], variants=[V('gl-ES')],
        tagger=dict(dict='gl/galician.dict', lowercase_with_uppercase=True, impl='GalicianTagger'),
        synthesizer=dict(dict='gl/galician_synth.dict', tags='gl/galician_tags.txt'),
        word_tokenizer='GalicianWordTokenizer',
        disambiguator=[mw('gl/multiwords.txt'), xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '“', '«', '»', '‘', '"', "'"], [']', ')', '}', '”', '»', '«', '’', '"', "'"]),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'), R('LongSentenceRule', max_words=50),
               R('LongParagraphRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
               R('WhiteSpaceAtBeginOfParagraph'), R('EmptyLineRule'), R('ParagraphRepeatBeginningRule'),
               R('PunctuationMarkAtParagraphEnd'), R('SimpleReplaceRule'), R('CastWordsRule'),
               R('GalicianRedundancyRule'), R('GalicianWordinessRule'), R('GalicianBarbarismsRule'),
               R('GalicianWikipediaRule')],
    ),
    # org.languagetool.language.Icelandic (code in langtool.lang.is_); its
    # HunspellNoSuggestionRule (after GenericUnpairedBracketsRule) is not
    # ported (spell checking)
    'is': dict(
        name='Icelandic', countries=['IS'], variants=[V('is-IS')], tagger=None, sentence_tokenizer='srx',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    'it': dict(
        name='Italian', countries=['IT', 'CH'], variants=[V('it')],
        tagger=dict(dict='it/italian.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='it/italian_synth.dict', tags='it/italian_tags.txt'),
        disambiguator=[xml()],
        rules=[R('WhitespaceBeforePunctuationRule'), R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '»', '«'], [']', ')', '}', '«', '»']), R('UppercaseSentenceStartRule'),
               R('ItalianWordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    'ja': dict(
        name='Japanese', countries=['JP'], variants=[V('ja-JP')],
        tagger=dict(impl='JapaneseTagger'), word_tokenizer='JapaneseWordTokenizer',
        rules=[R('DoublePunctuationRule'), R('MultipleWhitespaceRule')],
    ),
    'km': dict(
        name='Khmer', countries=['KH'], variants=[V('km-KH')],
        tagger=dict(dict='km/khmer.dict', lowercase_with_uppercase=True), word_tokenizer='KhmerWordTokenizer',
        disambiguator=[xml()],
        rules=[R('KhmerSimpleReplaceRule'), R('KhmerWordRepeatRule'), R('KhmerUnpairedBracketsRule'),
               R('KhmerSpaceBeforeRule')],
    ),
    'lt': dict(
        name='Lithuanian', countries=['LT'], variants=[V('lt-LT')], tagger=None,
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    'ml': dict(
        name='Malayalam', countries=['IN'], variants=[V('ml-IN')],
        tagger=dict(dict='ml/malayalam.dict', lowercase_with_uppercase=True),
        word_tokenizer='MalayalamWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    'nl': dict(
        name='Dutch', countries=['NL', 'BE'], default_variant='nl',
        variants=[V('nl', name='Dutch', extra_rule_files=['nl-NL/grammar.xml']),
                  V('nl-BE', countries=['BE'], name='Dutch (Belgium)')],
        tagger=dict(dict='nl/dutch.dict', lowercase_with_uppercase=True, impl='DutchTagger'),
        synthesizer=dict(dict='nl/dutch_synth.dict', tags='nl/dutch_tags.txt'),
        word_tokenizer='DutchWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('nl/multiwords.txt', True, True, False, _NONE, ignore_spelling=True), xml(True)],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '“', '‹', '“', '„', '"'], [']', ')', '}', '”', '›', '”', '”', '"']),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'), R('CompoundRule'),
               R('DutchWrongWordInContextRule'), R('WordCoherencyRule'), R('SimpleReplaceRule'),
               R('LongSentenceRule', max_words=40), R('LongParagraphRule'), R('PreferredWordRule'),
               R('SpaceInCompoundRule'), R('SentenceWhitespaceRule'), R('CheckCaseRule')],
    ),
    'pl': dict(
        name='Polish', countries=['PL'], variants=[V('pl-PL')],
        tagger=dict(dict='pl/polish.dict', lowercase_with_uppercase=True, impl='PolishTagger'),
        synthesizer=dict(dict='pl/polish_synth.dict', tags='pl/polish_tags.txt', impl='PolishSynthesizer'),
        word_tokenizer='PolishWordTokenizer',
        disambiguator=[xml(), mw('pl/multiwords.txt')],
        rules=[R('CommaWhitespaceRule'), R('UppercaseSentenceStartRule'), R('WordRepeatRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('PolishUnpairedBracketsRule'),
               R('PolishWordRepeatRule'), R('CompoundRule'), R('SimpleReplaceRule'), R('WordCoherencyRule'),
               R('DashRule')],
    ),
    'pt': dict(
        name='Portuguese', countries=['', 'CV', 'GW', 'MO', 'ST', 'TL'], default_variant='pt-PT',
        variants=[
            V('pt', name='Portuguese'),
            V('pt-PT', countries=['PT'], name='Portuguese (Portugal)',
              extra_rules=[R('PostReformPortugueseCompoundRule'), R('PostReformPortugueseDashRule'),
                           R('PortugueseAgreementReplaceRule'), R('PortugalPortugueseReplaceRule'),
                           R('PortugueseArchaismsRule')]),
            V('pt-BR', countries=['BR'], name='Portuguese (Brazil)',
              extra_rules=[R('PostReformPortugueseCompoundRule'), R('PostReformPortugueseDashRule'),
                           R('BrazilianPortugueseReplaceRule'), R('PortugueseArchaismsRule')]),
            V('pt-AO', countries=['AO'], name='Portuguese (Angola preAO)',
              extra_rules=[R('PreReformPortugueseCompoundRule'), R('PreReformPortugueseDashRule')]),
            V('pt-MZ', countries=['MZ'], name='Portuguese (Moçambique preAO)',
              extra_rules=[R('PreReformPortugueseCompoundRule'), R('PreReformPortugueseDashRule')]),
        ],
        tagger=dict(dict='pt/portuguese.dict', lowercase_with_uppercase=True, impl='PortugueseTagger'),
        synthesizer=dict(dict='pt/portuguese_synth.dict', tags='pt/portuguese_tags.txt'),
        word_tokenizer='PortugueseWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, True, 'NPCN000', ignore_spelling=True),
                       mw('pt/multiwords.txt', True, True, True, ignore_spelling=True, remove_previous_tags=True),
                       xml(True)],
        rules=_PT_RULES,
    ),
    'ro': dict(
        name='Romanian', countries=['RO'], variants=[V('ro-RO')],
        tagger=dict(dict='ro/romanian.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='ro/romanian_synth.dict', tags='ro/romanian_tags.txt'),
        word_tokenizer='RomanianWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), brackets(['[', '(', '{', '„', '«', '»'], [']', ')', '}', '”', '»', '«']),
               R('WordRepeatRule'), R('RomanianWordRepeatBeginningRule'), R('SimpleReplaceRule'),
               R('CompoundRule')],
    ),
    'ru': dict(
        name='Russian', countries=['RU'], variants=[V('ru-RU')], ignored_characters_regex='[­́̀]',
        tagger=dict(dict='ru/russian.dict', lowercase_with_uppercase=True, impl='RussianTagger'),
        synthesizer=dict(dict='ru/russian_synth.dict', tags='ru/tags_russian.txt'),
        word_tokenizer='RussianWordTokenizer',
        disambiguator=[mw('ru/multiwords.txt'), xml()],
        rules=[R('CommaWhitespaceRule'), R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'),
               R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'), R('WhiteSpaceAtBeginOfParagraph'),
               R('LongSentenceRule', max_words=50), R('LongParagraphRule'), R('ParagraphRepeatBeginningRule'),
               R('RussianFillerWordsRule'), R('PunctuationMarkAtParagraphEnd2'), R('RussianUnpairedBracketsRule'),
               R('RussianCompoundRule'), R('RussianSimpleReplaceRule'), R('RussianSimpleWordRepeatRule'),
               R('RussianWordCoherencyRule'), R('RussianWordRepeatRule'), R('RussianWordRootRepeatRule'),
               R('RussianVerbConjugationRule'), R('RussianDashRule'), R('RussianSpecificCaseRule')],
    ),
    'sk': dict(
        name='Slovak', countries=['SK'], variants=[V('sk-SK')], extra_rule_files=['grammar-typography.xml'],
        tagger=dict(dict='sk/slovak.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='sk/slovak_synth.dict', tags='sk/slovak_tags.txt'),
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '„', '»', '«', '"'], [']', ')', '}', '“', '«', '»', '"']),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule'), R('CompoundRule')],
    ),
    'sl': dict(
        name='Slovenian', countries=['SI'], variants=[V('sl-SI')], tagger=None,
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '„', '»', '«', '"'], [']', ')', '}', '”', '«', '»', '"']),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    'sv': dict(
        name='Swedish', countries=['SE', 'FI'], variants=[V('sv')],
        tagger=dict(dict='sv/swedish.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='sv/swedish_synth.dict', tags='sv/swedish_synth.dict_tags.txt'),
        disambiguator=[xml(), mw('sv/multiwords.txt')],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('LongParagraphRule', default_words=150), R('UppercaseSentenceStartRule'),
               R('LongSentenceRule', max_words=40), R('WordRepeatRule'), R('WordCoherencyRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('CompoundRule')],
    ),
    'ta': dict(
        name='Tamil', countries=['IN'], variants=[V('ta-IN')], sentence_tokenizer='srx',
        tagger=dict(dict='ta/tamil.dict', lowercase_with_uppercase=True),
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('MultipleWhitespaceRule'),
               R('LongSentenceRule', max_words=50), R('SentenceWhitespaceRule')],
    ),
    'tl': dict(
        name='Tagalog', countries=['PH'], variants=[V('tl-PH')],
        tagger=dict(dict='tl/tagalog.dict', lowercase_with_uppercase=True), word_tokenizer='TagalogWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    'uk': dict(
        name='Ukrainian', countries=['UA'], variants=[V('uk-UA')], ignored_characters_regex='[­́]',
        extra_rule_files=['grammar-spelling.xml', 'grammar-grammar.xml', 'grammar-barbarism.xml',
                          'grammar-style.xml', 'grammar-punctuation.xml'],
        tagger=dict(dict='uk/ukrainian.dict', lowercase_with_uppercase=False, impl='UkrainianTagger'),
        synthesizer=dict(dict='uk/ukrainian_synth.dict', tags='uk/ukrainian_tags.txt'),
        word_tokenizer='UkrainianWordTokenizer',
        disambiguator=[('custom', 'UkrainianPreDisambiguator'),
                       ('multiword2', 'uk/multiwords.txt', dict(allow_first_capitalized=True,
                                                                impl='UkrainianMultiwordChunker')),
                       xml()],
        rules=[R('UkrainianCommaWhitespaceRule'), R('UkrainianUppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('UkrainianWordRepeatRule'), R('TypographyRule'),
               R('HiddenCharacterRule'), R('MissingHyphenRule'), R('TokenAgreementVerbNounRule'),
               R('TokenAgreementNounVerbRule'), R('TokenAgreementAdjNounRule'), R('TokenAgreementPrepNounRule'),
               R('TokenAgreementNumrNounRule'), R('MixedAlphabetsRule'), R('SimpleReplaceSoftRule'),
               R('SimpleReplaceRenamedRule'), R('SimpleReplaceRule')],
    ),
    'zh': dict(
        name='Chinese', countries=['CN'], variants=[V('zh-CN')],
        tagger=dict(impl='ChineseTagger'), word_tokenizer='ChineseWordTokenizer',
        sentence_tokenizer='ChineseSentenceTokenizer',
        rules=[R('DoublePunctuationRule'), R('MultipleWhitespaceRule')],
    ),
}

# All language modules except Crimean Tatar override
# Language.createDefaultSentenceTokenizer() with an SRXSentenceTokenizer
for _code, _d in LANGUAGES.items():
    if _code != 'crh':
        _d.setdefault('sentence_tokenizer', 'srx')


def all_codes():
    """All language codes, including variants."""
    out = []
    for short, d in LANGUAGES.items():
        for v in d['variants']:
            out.append(v['code'])
    return out


_ALIASES = {}
for _short, _d in LANGUAGES.items():
    for _v in _d['variants']:
        _ALIASES[_v['code'].lower()] = (_short, _v['code'])
    _ALIASES.setdefault(_short.lower(), (_short, _d.get('default_variant') or _d['variants'][0]['code']))


def resolve_code(code):
    """Return (short_code, variant_code) for a language code like 'en',
    'en-US', 'en_GB', 'de-DE', 'pt'. Note that a bare language code maps to the
    language without country when such a variant exists (like LanguageTool's
    Languages.getLanguageForShortCode)."""
    c = code.replace('_', '-').lower()
    if c in _ALIASES:
        short, vcode = _ALIASES[c]
        d = LANGUAGES[short]
        # an exact variant code like 'en' or 'de' exists: use it
        for v in d['variants']:
            if v['code'].lower() == c:
                return short, v['code']
        return short, vcode
    parts = c.split('-')
    if parts[0] in LANGUAGES:
        d = LANGUAGES[parts[0]]
        return parts[0], d['variants'][0]['code']
    raise KeyError('Unknown language: %s' % code)


def register_language(short_code, definition):
    """Add (or replace) a language definition at runtime."""
    LANGUAGES[short_code] = definition
    for v in definition['variants']:
        _ALIASES[v['code'].lower()] = (short_code, v['code'])
    _ALIASES[short_code.lower()] = (short_code, definition.get('default_variant') or definition['variants'][0]['code'])
    from . import api
    with api._lock:
        for v in definition['variants']:
            api._languages.pop(v['code'], None)
