"""Declarative definitions of the supported languages, derived from the Java
Language classes of the LanguageTool language modules.

Each language has:
 name, countries, variants: list of dicts with code (short code with country and
   variant), name, countries, variant, default_enabled_rules, default_disabled_rules
 default_variant: code of the default variant
 tagger: dict(dict=path of .dict relative to the resource dir,
              lowercase_with_uppercase=bool) or None for no tagging
 synthesizer: dict(dict=..., tags=..., sor=path of the .sor file of the number
   speller, optional) or None
 word_tokenizer: name of the tokenizer implementation ('core' by default)
 disambiguator: list of stages, each one of
     ('xml', use_global_disambiguation)
     ('xml_of', short_code, use_global_disambiguation) -- the XmlRuleDisambiguator
                             of the default variant of another language
     ('multiword', file, dict(allow_first_capitalized, allow_all_uppercase,
                             allow_titlecase, default_tag, ignore_spelling,
                             remove_previous_tags))
     ('multiword2', file, dict(allow_first_capitalized, ...))
     ('custom', name)  -- language specific code
 chunker: name of the chunker run on the tagged tokens (Language.getChunker())
 post_disambiguation_chunker: name of the chunker run on the disambiguated
   tokens (Language.getPostDisambiguationChunker())
 is_variant: Language.isVariant() (default: all variants but the first one)
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
    R('CommaWhitespaceRule',
      examples=('We had coffee<marker> ,</marker> cheese and crackers and grapes.',
                'We had coffee<marker>,</marker> cheese and crackers and grapes.')),
    R('DoublePunctuationRule'),
    R('UppercaseSentenceStartRule',
      examples=('This house is old. <marker>it</marker> was built in 1950.',
                'This house is old. <marker>It</marker> was built in 1950.')),
    R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule', max_spaces_between_sentences=2),
    R('WhiteSpaceBeforeParagraphEnd'), R('WhiteSpaceAtBeginOfParagraph'), R('EmptyLineRule'),
    R('LongSentenceRule', max_words=40), R('LongParagraphRule'), R('ParagraphRepeatBeginningRule'),
    R('PunctuationMarkAtParagraphEnd'), R('PunctuationMarkAtParagraphEnd2'),
    # specific to English:
    R('ConsistentApostrophesRule'), R('EnglishSpecificCaseRule'), R('EnglishUnpairedBracketsRule'),
    R('EnglishUnpairedQuotesRule'), R('EnglishWordRepeatRule'), R('AvsAnRule'),
    R('EnglishWordRepeatBeginningRule'), R('CompoundRule'), R('ContractionSpellingRule'),
    R('EnglishWrongWordInContextRule'), R('EnglishDashRule'), R('WordCoherencyRule'),
    R('EnglishDiacriticsRule'), R('EnglishPlainEnglishRule'), R('EnglishRedundancyRule'),
    R('SimpleReplaceRule'), R('SimpleReplaceProfanityRule'), R('ReadabilityRule', too_easy_test=False),
    R('ReadabilityRule', too_easy_test=True), R('EnglishRepeatedWordsRule'), R('StyleTooOftenUsedVerbRule'),
    R('StyleTooOftenUsedNounRule'), R('StyleTooOftenUsedAdjectiveRule'),
]

# org.languagetool.language.German.getRelevantRules (code in
# langtool.lang.de); the language model rules (UpperCaseNgramRule,
# GermanConfusionProbabilityRule, ProhibitedCompoundRule of
# getRelevantLanguageModelRules) and the spelling rules (GermanSpellerRule,
# AustrianGermanSpellerRule, SwissGermanSpellerRule of
# getRelevantLanguageModelCapableRules) are not created (language model,
# spell checking)
_DE_RULES = [
    R('GermanCommaWhitespaceRule',
      examples=('Die Partei<marker> ,</marker> die die letzte Wahl gewann.',
                'Die Partei<marker>,</marker> die die letzte Wahl gewann.'),
      url='https://languagetool.org/insights/de/beitrag/grammatik-leerzeichen/#fehler-1-leerzeichen-vor-und-nach-satzzeichen'),
    R('GermanUnpairedBracketsRule'), R('GermanUnpairedQuotesRule'),
    R('UppercaseSentenceStartRule',
      examples=('Das Haus ist alt. <marker>es</marker> wurde 1950 gebaut.',
                'Das Haus ist alt. <marker>Es</marker> wurde 1950 gebaut.'),
      url='https://languagetool.org/insights/de/beitrag/gross-klein-schreibung-rechtschreibung/'
          '#1-satzanf%C3%A4nge-schreiben-wir-gro%C3%9F'),
    R('MultipleWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'), R('WhiteSpaceAtBeginOfParagraph'),
    R('EmptyLineRule'), R('LongParagraphRule'), R('PunctuationMarkAtParagraphEnd'),
    # specific to German:
    R('SimpleReplaceRule'), R('OldSpellingRule'), R('SentenceWhitespaceRule'), R('GermanDoublePunctuationRule'),
    R('MissingVerbRule'), R('GermanWordRepeatRule'), R('GermanWordRepeatBeginningRule'),
    R('GermanWrongWordInContextRule'), R('AgreementRule'), R('AgreementRule2'), R('CaseRule'), R('DashRule'),
    R('VerbAgreementRule'), R('SubjectVerbAgreementRule'), R('WordCoherencyRule'), R('SimilarNameRule'),
    R('WiederVsWiderRule'), R('GermanStyleRepeatedWordRule'), R('CompoundCoherencyRule'),
    R('LongSentenceRule', max_words=40), R('GermanFillerWordsRule'), R('PassiveSentenceRule'),
    R('SentenceWithModalVerbRule'), R('SentenceWithManRule'), R('ConjunctionAtBeginOfSentenceRule'),
    R('NonSignificantVerbsRule'), R('UnnecessaryPhraseRule'), R('GermanParagraphRepeatBeginningRule'),
    R('DuUpperLowerCaseRule'), R('UnitConversionRule'), R('MissingCommaRelativeClauseRule'),
    R('MissingCommaRelativeClauseRule', behind=True), R('RedundantModalOrAuxiliaryVerb'),
    R('GermanReadabilityRule', too_easy_test=True), R('GermanReadabilityRule', too_easy_test=False),
    R('CompoundInfinitivRule'), R('StyleRepeatedVeryShortSentences'), R('StyleRepeatedSentenceBeginning'),
    R('GermanRepeatedWordsRule'), R('StyleTooOftenUsedVerbRule'), R('StyleTooOftenUsedNounRule'),
    R('StyleTooOftenUsedAdjectiveRule'),
]

_PT_RULES = [
    R('CommaWhitespaceRule',
      examples=('Tomamos café<marker> ,</marker> queijo, bolachas e uvas.',
                'Tomamos café<marker>,</marker> queijo, bolachas e uvas.')),
    brackets(['[', '(', '{', '"', '“'], [']', ')', '}', '"', '”']),
    R('LongSentenceRule', max_words=50), R('LongParagraphRule'),
    R('UppercaseSentenceStartRule',
      examples=('Esta casa é velha. <marker>foi</marker> construida em 1950.',
                'Esta casa é velha. <marker>Foi</marker> construida em 1950.')),
    R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
    R('WhiteSpaceAtBeginOfParagraph'), R('EmptyLineRule'), R('ParagraphRepeatBeginningRule'),
    R('PunctuationMarkAtParagraphEnd', default_active=True),
    # Specific to Portuguese:
    R('PostReformPortugueseCompoundRule'), R('PortugueseColourHyphenationRule'),
    R('PortugueseOrthographyReplaceRule'), R('PortugueseReplaceRule'),
    R('PortugueseBarbarismsRule', path='/pt/barbarisms.txt'),
    R('PortugueseClicheRule', path='/pt/cliches.txt'), R('PortugueseFillerWordsRule'),
    R('PortugueseRedundancyRule', path='/pt/redundancies.txt'),
    R('PortugueseWordinessRule', path='/pt/wordiness.txt'),
    R('PortugueseWikipediaRule', path='/pt/wikipedia.txt'),
    R('PortugueseWordRepeatRule'), R('PortugueseWordRepeatBeginningRule'), R('PortugueseAccentuationCheckRule'),
    R('PortugueseDiacriticsRule'), R('PortugueseWrongWordInContextRule'), R('PortugueseWordCoherencyRule'),
    R('PortugueseUnitConversionRule'), R('PortugueseReadabilityRule', too_easy_test=True),
    R('PortugueseReadabilityRule', too_easy_test=False), R('DoublePunctuationRule'),
    R('EnglishContractionSpellingRule'),
]

_CA_RULES = [
    R('CommaWhitespaceRule',
      examples=('A parer seu<marker> ,</marker> no era veritat.', 'A parer seu<marker>,</marker> no era veritat.')),
    R('DoublePunctuationRule'), R('CatalanUnpairedBracketsRule'),
    R('UppercaseSentenceStartRule',
      examples=('Preus de venda al públic. <marker>han</marker> pujat molt.',
                'Preus de venda al públic. <marker>Han</marker> pujat molt.')),
    R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('LongSentenceRule', max_words=60),
    # specific to Catalan:
    R('CatalanWordRepeatRule'), R('CatalanPhraseRepeatRule'), R('CatalanUnpairedQuestionMarksRule'),
    R('CatalanUnpairedExclamationMarksRule'), R('CatalanWrongWordInContextRule'), R('SimpleReplaceVerbsRule'),
    R('SimpleReplaceBalearicRule'), R('SimpleReplaceRule'), R('SimpleReplaceMultiwordsRule'),
    R('ReplaceOperationNamesRule'), R('SimpleReplaceDiacriticsIEC'), R('SimpleReplaceAnglicism'),
    R('PronomFebleDuplicateRule'), R('CheckCaseRule'), R('SimpleReplaceAdverbsMent'),
    R('CatalanWordRepeatBeginningRule'), R('CompoundRule'), R('SimpleReplaceDNVRule'),
    R('SimpleReplaceDNVColloquialRule'), R('SimpleReplaceDNVSecondaryRule'), R('WordCoherencyRule'),
    R('CatalanPunctuationMarkAtParagraphEnd'), R('CatalanSplitLongSentenceRule', max_words=60),
    R('IgnoreProperNouns'),
]

LANGUAGES = {
    # org.languagetool.language.Arabic (code in langtool.lang.ar); its
    # ArabicHunspellSpellerRule (after LongSentenceRule) is not ported (spell
    # checking), nor the ArabicConfusionProbabilityRule (language model)
    'ar': dict(
        name='Arabic', countries=['', 'SA', 'DZ', 'BH', 'EG', 'IQ', 'JO', 'KW', 'LB', 'LY', 'MA', 'OM', 'QA', 'SD',
                                  'SY', 'TN', 'AE', 'YE'],
        variants=[V('ar')], sentence_tokenizer='srx',
        tagger=dict(dict='ar/arabic.dict', impl='ArabicTagger'),
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
    # org.languagetool.language.Asturian (code in langtool.lang.ast); its
    # MorfologikAsturianSpellerRule (after GenericUnpairedBracketsRule) is not
    # ported (spell checking)
    'ast': dict(
        name='Asturian', countries=['ES'], variants=[V('ast-ES')], sentence_tokenizer='srx',
        tagger=dict(dict='ast/asturian.dict', lowercase_with_uppercase=True),
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Belarusian (code in langtool.lang.be); its
    # MorfologikBelarusianSpellerRule (after DoublePunctuationRule) is not
    # ported (spell checking)
    'be': dict(
        name='Belarusian', countries=['BY'], variants=[V('be-BY')], sentence_tokenizer='srx',
        quotes=('«', '»', '‘', '’'), advanced_typography=True,
        tagger=None, word_tokenizer='BelarusianWordTokenizer', ignored_characters_regex='[­́̀]',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
               R('WhiteSpaceAtBeginOfParagraph'), R('LongSentenceRule', max_words=50), R('LongParagraphRule'),
               R('ParagraphRepeatBeginningRule'), R('PunctuationMarkAtParagraphEnd2'), R('SimpleReplaceRule'),
               R('BelarusianSpecificCaseRule')],
    ),
    # org.languagetool.language.Breton (code in langtool.lang.br); its
    # MorfologikBretonSpellerRule (after DoublePunctuationRule) is not ported
    # (spell checking)
    'br': dict(
        name='Breton', countries=['FR'], variants=[V('br-FR')], sentence_tokenizer='srx',
        tagger=dict(dict='br/breton.dict', lowercase_with_uppercase=True, impl='BretonTagger'),
        word_tokenizer='BretonWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('TopoReplaceRule')],
    ),
    # org.languagetool.language.Catalan, ValencianCatalan and BalearicCatalan
    # (code in langtool.lang.ca); the MorfologikCatalanSpellerRule (after
    # CatalanPhraseRepeatRule) is not ported (spell checking), nor is
    # CatalanRemoteRule (after CatalanPunctuationMarkAtParagraphEnd, a remote
    # rule). CatalanHybridDisambiguator: the MultiWordChunkers for
    # spelling_global.txt and ca/multiwords.txt, the XmlRuleDisambiguator of
    # ca-ES with the global disambiguation rules, then the
    # CatalanMultitokenDisambiguator
    'ca': dict(
        name='Catalan', countries=['ES'], default_variant='ca-ES', sentence_tokenizer='srx',
        quotes=('«', '»', '‘', '’'), advanced_typography=True, default_rule_priority_for_style=-50,
        variants=[
            V('ca-ES', name='Catalan'),
            V('ca-ES-valencia', countries=['ES'], name='Catalan (Valencian)', variant='valencia',
              enabled=['EXIGEIX_VERBS_VALENCIANS', 'EXIGEIX_ACCENTUACIO_VALENCIANA', 'EXIGEIX_POSSESSIUS_U',
                       'EXIGEIX_VERBS_EIX', 'EXIGEIX_VERBS_ISC', 'PER_PER_A_INFINITIU', 'FINS_EL_AVL', 'LES_HA_FETES'],
              disabled=['EXIGEIX_VERBS_CENTRAL', 'EXIGEIX_ACCENTUACIO_GENERAL', 'EXIGEIX_POSSESSIUS_V',
                        'EVITA_PRONOMS_VALENCIANS', 'EVITA_DEMOSTRATIUS_EIXE', 'VOCABULARI_VALENCIA', 'EXIGEIX_US',
                        'FINS_EL_GENERAL', 'EVITA_INFINITIUS_INDRE', 'EVITA_DEMOSTRATIUS_ESTE', 'CASTIC_CASTIG'],
              extra_rules=[R('WordCoherencyValencianRule')]),
            V('ca-ES-balear', countries=['ES'], name='Catalan (Balearic)', variant='balear',
              enabled=['EXIGEIX_VERBS_BALEARS'], disabled=['EXIGEIX_VERBS_CENTRAL', 'CA_SIMPLE_REPLACE_BALEARIC']),
        ],
        tagger=dict(dict='ca/ca-ES.dict', lowercase_with_uppercase=False, impl='CatalanTagger'),
        synthesizer=dict(dict='ca/ca-ES_synth.dict', tags='ca/ca-ES_tags.txt', sor='ca/ca.sor',
                         impl='CatalanSynthesizer'),
        word_tokenizer='CatalanWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, 'NPCN000'),
                       mw('ca/multiwords.txt', True, True, False, remove_previous_tags=True), xml(True),
                       ('custom', 'CatalanMultitokenDisambiguator')],
        rules=_CA_RULES,
    ),
    # org.languagetool.language.CrimeanTatar (code in langtool.lang.crh); it
    # overrides getSentenceTokenizer() (not createDefaultSentenceTokenizer())
    # with an SRXSentenceTokenizer; its MorfologikCrimeanTatarSpellerRule
    # (after WhiteSpaceAtBeginOfParagraph) is not ported (spell checking)
    'crh': dict(
        name='Crimean Tatar', countries=['UA'], variants=[V('crh-UA')], sentence_tokenizer='srx',
        tagger=dict(dict='crh/crimean_tatar.dict', lowercase_with_uppercase=False, impl='CrimeanTatarTagger'),
        synthesizer=dict(dict='crh/crimean_tatar_synth.dict', tags='crh/crimean_tatar_synth.dict_tags.txt'),
        word_tokenizer='CrimeanTatarWordTokenizer',
        rules=[R('CommaWhitespaceRule',
                 examples=('Özü bir çaqrım uzaqta<marker> ,</marker> demiryol keçidi yanında yaşay.',
                           'Özü bir çaqrım uzaqta<marker>,</marker> demiryol keçidi yanında yaşay.')),
               R('DoublePunctuationRule'),
               R('UppercaseSentenceStartRule',
                 examples=('Meclis Haberleri 10.09.2003. <marker>qırımtatar</marker> Milliy Meclisiniñ 120-cı '
                           'toplaşuvı olıp keçti',
                           'Meclis Haberleri 10.09.2003. <marker>Qırımtatar</marker> Milliy Meclisiniñ 120-cı '
                           'toplaşuvı olıp keçti')),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
               R('WhiteSpaceAtBeginOfParagraph')],
    ),
    # org.languagetool.language.Danish (code in langtool.lang.da); its
    # HunspellRule (after GenericUnpairedBracketsRule) is not ported (spell
    # checking)
    'da': dict(
        name='Danish', countries=['DK'], variants=[V('da-DK')], sentence_tokenizer='srx',
        tagger=dict(dict='da/danish.dict', lowercase_with_uppercase=True),
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '"', '”'], [']', ')', '}', '"', '”']),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.German and its subclasses GermanyGerman,
    # AustrianGerman and SwissGerman (NonSwissGerman is not used by them, it
    # has the same rules and rule files as GermanyGerman and AustrianGerman);
    # code in langtool.lang.de. The disambiguator is GermanRuleDisambiguator
    # (the MultiWordChunkers for multitoken-ignore.txt, spelling_global.txt
    # and multitoken-suggest.txt, then the XmlRuleDisambiguator with the
    # global disambiguation rules), the post-disambiguation chunker is
    # GermanChunker. filterRuleMatches (AI_DE_GGEC match merging, and the
    # ß -> ss replacement of SwissGerman), toAdvancedTypography and the
    # priorities (langtool.priorities) are ported too.
    'de': dict(
        name='German', countries=['LU', 'LI', 'BE'], default_variant='de-DE', ignored_characters_regex=SOFT_HYPHEN,
        sentence_tokenizer='srx', quotes=('„', '“', '‚', '‘'), advanced_typography=True,
        variants=[
            V('de', name='German'),
            V('de-DE', countries=['DE'], name='German (Germany)', extra_rules=[R('GermanCompoundRule')],
              extra_rule_files=['de-DE-AT/grammar.xml']),
            V('de-AT', countries=['AT'], name='German (Austria)', extra_rules=[R('GermanCompoundRule')],
              extra_rule_files=['de-DE-AT/grammar.xml']),
            V('de-CH', countries=['CH'], name='German (Swiss)', extra_rules=[R('SwissCompoundRule')],
              tagger_impl='SwissGermanTagger', quotes=('«', '»', '‚', '‘')),
        ],
        tagger=dict(dict='de/german.dict', lowercase_with_uppercase=True, impl='GermanTagger'),
        synthesizer=dict(dict='de/german_synth.dict', tags='de/german_tags.txt', sor='de/de.sor', impl='GermanSynthesizer'),
        word_tokenizer='GermanWordTokenizer',
        disambiguator=[mw('de/multitoken-ignore.txt', True, True, False, _NONE, ignore_spelling=True),
                       mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('de/multitoken-suggest.txt', True, True, False, _NONE, ignore_spelling=True),
                       xml(True)],
        post_disambiguation_chunker='GermanChunker',
        rules=_DE_RULES,
    ),
    # org.languagetool.language.SimpleGerman, a subclass of GermanyGerman
    # (code in langtool.lang.de_simple): German's sentence tokenizer, tagger,
    # synthesizer, word tokenizer, post-disambiguation chunker, quotes,
    # typography, filterRuleMatches and multitoken speller; the disambiguator
    # is GermanRuleDisambiguator(GermanyGerman.getInstance()) (the
    # XmlRuleDisambiguator of de-DE); getRelevantRules is only the German
    # LongSentenceRule with 12 words, getRuleFileNames only its own
    # grammar.xml, no language model (capable) rules (so no speller rule);
    # the priorities of TOO_LONG_SENTENCE and LANGES_WORT, then German's
    # (langtool.priorities)
    'de-DE-x-simple-language': dict(
        name='Simple German', countries=['DE'], resource_language='de', ignored_characters_regex=SOFT_HYPHEN,
        is_variant=True, sentence_tokenizer='srx', quotes=('„', '“', '‚', '‘'), advanced_typography=True,
        variants=[V('de-DE-x-simple-language')],
        tagger=dict(dict='de/german.dict', lowercase_with_uppercase=True, impl='GermanTagger'),
        synthesizer=dict(dict='de/german_synth.dict', tags='de/german_tags.txt', sor='de/de.sor', impl='GermanSynthesizer'),
        word_tokenizer='GermanWordTokenizer',
        disambiguator=[mw('de/multitoken-ignore.txt', True, True, False, _NONE, ignore_spelling=True),
                       mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('de/multitoken-suggest.txt', True, True, False, _NONE, ignore_spelling=True),
                       ('xml_of', 'de', True)],
        post_disambiguation_chunker='GermanChunker',
        rules=[R('LongSentenceRule', max_words=12)],
    ),
    # org.languagetool.language.Greek (code in langtool.lang.el); its
    # MorfologikGreekSpellerRule (after LongSentenceRule) is not ported
    # (spell checking)
    'el': dict(
        name='Greek', countries=['GR'], variants=[V('el-GR')], sentence_tokenizer='srx',
        tagger=dict(dict='el/greek.dict', lowercase_with_uppercase=True, impl='GreekTagger'),
        synthesizer=dict(dict='el/greek_synth.dict', tags='el/greek_tags.txt'),
        word_tokenizer='GreekWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule',
                 examples=('Το κόμμα χωρίζει προτάσεις<marker> ,</marker> όρους προτάσεων και φράσεις.',
                           'Το κόμμα χωρίζει προτάσεις<marker>,</marker> όρους προτάσεων και φράσεις.')),
               R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '“', '"', '«'], [']', ')', '}', '”', '"', '»'], 'EL_UNPAIRED_BRACKETS'),
               R('LongSentenceRule', max_words=50),
               R('UppercaseSentenceStartRule',
                 examples=('Η τελεία είναι σημείο στίξης. <marker>δείχνει</marker> το τέλος μίας πρότασης.',
                           'Η τελεία είναι σημείο στίξης. <marker>Δείχνει</marker> το τέλος μίας πρότασης.')),
               R('MultipleWhitespaceRule'), R('GreekWordRepeatBeginningRule'), R('WordRepeatRule'),
               R('ReplaceHomonymsRule'), R('GreekSpecificCaseRule'), R('NumeralStressRule'),
               R('GreekRedundancyRule')],
    ),
    'en': dict(
        name='English', countries=[], default_variant='en-US', sentence_tokenizer='srx',
        quotes=('“', '”', '‘', '’'), advanced_typography=True, default_rule_priority_for_style=-50,
        mother_tongue_rule_files={'de': 'grammar-l2-de.xml', 'fr': 'grammar-l2-fr.xml'},
        variants=[
            V('en', name='English'),
            V('en-US', countries=['US'], name='English (US)',
              extra_rules=[R('AmericanReplaceRule', path='/en/en-US/replace.txt'), R('UnitConversionRuleUS')]),
            V('en-GB', countries=['GB'], name='English (GB)',
              priorities={'OXFORD_SPELLING_ISATION_NOUNS': -20, 'OXFORD_SPELLING_ISE_VERBS': -21,
                          'OXFORD_SPELLING_IZE': -22},
              extra_rules=[R('BritishReplaceRule', path='/en/en-GB/replace.txt'), R('UnitConversionRuleImperial')]),
            V('en-AU', countries=['AU'], name='English (Australian)', extra_rules=[R('UnitConversionRuleImperial')]),
            V('en-CA', countries=['CA'], name='English (Canadian)', extra_rules=[R('UnitConversionRuleImperial')]),
            V('en-NZ', countries=['NZ'], name='English (New Zealand)',
              extra_rules=[R('NewZealandReplaceRule', path='/en/en-NZ/replace.txt'), R('UnitConversionRuleImperial')]),
            V('en-ZA', countries=['ZA'], name='English (South African)'),
        ],
        tagger=dict(dict='en/english.dict', lowercase_with_uppercase=False, impl='EnglishTagger'),
        synthesizer=dict(dict='en/english_synth.dict', tags='en/english_tags.txt', sor='en/en.sor',
                         impl='EnglishSynthesizer'),
        word_tokenizer='EnglishWordTokenizer',
        # EnglishHybridDisambiguator
        disambiguator=[mw('spelling_global.txt', True, True, False, _NONE, ignore_spelling=True),
                       mw('en/multiwords.txt', True, True, False, ignore_spelling=True, remove_previous_tags=True),
                       xml(True)],
        chunker='EnglishChunker',
        rules=_EN_RULES,
    ),
    'eo': dict(
        name='Esperanto', countries=[], variants=[V('eo')], sentence_tokenizer='srx',
        tagger=dict(impl='EsperantoTagger'), word_tokenizer='EsperantoWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule'),
               R('SentenceWhitespaceRule')],
    ),
    # org.languagetool.language.Spanish and SpanishVoseo (code in
    # langtool.lang.es); the MorfologikSpanishSpellerRule (after
    # QuestionMarkRule) is not ported (spell checking), nor is
    # SpanishConfusionProbabilityRule (language model).
    # SpanishHybridDisambiguator: the MultiWordChunkers for
    # spelling_global.txt and es/multiwords.txt, then the XmlRuleDisambiguator
    'es': dict(
        name='Spanish', countries=['ES', '', 'MX', 'GT', 'CR', 'PA', 'DO', 'VE', 'PE', 'AR', 'EC', 'CL', 'UY', 'PY',
                                   'BO', 'SV', 'HN', 'NI', 'PR', 'US', 'CU'], default_variant='es',
        sentence_tokenizer='srx', quotes=('«', '»', '‘', '’'), advanced_typography=True,
        variants=[V('es', name='Spanish'), V('es-AR', countries=['AR'], name='Spanish (voseo)', disabled=['VOSEO'])],
        tagger=dict(dict='es/es-ES.dict', lowercase_with_uppercase=True, impl='SpanishTagger'),
        synthesizer=dict(dict='es/es-ES_synth.dict', tags='es/es-ES_tags.txt', sor='es/es.sor',
                         impl='SpanishSynthesizer'),
        word_tokenizer='SpanishWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, 'NPCN000'),
                       mw('es/multiwords.txt', True, True, False, remove_previous_tags=True), xml(True)],
        rules=[R('CommaWhitespaceRule',
                 examples=('En su opinión<marker> ,</marker> no era verdad.',
                           'En su opinión<marker>,</marker> no era verdad.')),
               R('DoublePunctuationRule'), R('SpanishUnpairedBracketsRule'), R('QuestionMarkRule'),
               R('UppercaseSentenceStartRule',
                 examples=('Venta al público. <marker>ha</marker> subido mucho.',
                           'Venta al público. <marker>Ha</marker> subido mucho.')),
               R('SpanishWordRepeatRule'), R('MultipleWhitespaceRule'), R('SpanishWikipediaRule'),
               R('SpanishWrongWordInContextRule'), R('LongSentenceRule', max_words=60), R('LongParagraphRule'),
               R('SimpleReplaceRule'), R('SimpleReplaceVerbsRule'), R('SpanishWordRepeatBeginningRule'),
               R('CompoundRule'), R('SpanishRepeatedWordsRule')],
    ),
    # org.languagetool.language.Persian (code in langtool.lang.fa)
    'fa': dict(
        name='Persian', countries=['IR', 'AF'], variants=[V('fa')], sentence_tokenizer='srx',
        tagger=None, word_tokenizer='PersianWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('MultipleWhitespaceRule'),
               R('LongSentenceRule', max_words=50), R('PersianCommaWhitespaceRule'),
               R('PersianDoublePunctuationRule'), R('PersianWordRepeatBeginningRule'), R('PersianWordRepeatRule'),
               R('SimpleReplaceRule'), R('PersianSpaceBeforeRule'), R('WordCoherencyRule')],
    ),
    # org.languagetool.language.French, CanadianFrench, SwissFrench and
    # BelgianFrench (code in langtool.lang.fr); the MorfologikFrenchSpellerRule
    # (after GenericUnpairedBracketsRule) is not ported (spell checking), nor
    # are FrenchConfusionProbabilityRule (language model) and GrammalecteRule
    # (remote server). FrenchHybridDisambiguator: the MultiWordChunkers for
    # spelling_global.txt and fr/multiwords.txt, then the XmlRuleDisambiguator
    'fr': dict(
        name='French', countries=['FR', '', 'LU', 'MC', 'CM', 'CI', 'HT', 'ML', 'SN', 'CD', 'MA', 'RE'],
        default_variant='fr', ignored_characters_regex=SOFT_HYPHEN, sentence_tokenizer='srx',
        quotes=('«', '»', '‘', '’'), advanced_typography=True,
        variants=[V('fr', name='French'), V('fr-CA', countries=['CA'], name='French (Canada)',
                                            disabled=['DOUBLER_UNE_CLASSE']),
                  V('fr-CH', countries=['CH'], name='French (Switzerland)', disabled=['DOUBLER_UNE_CLASSE']),
                  V('fr-BE', countries=['BE'], name='French (Belgium)', disabled=['DOUBLER_UNE_CLASSE'])],
        tagger=dict(dict='fr/french.dict', lowercase_with_uppercase=False, impl='FrenchTagger'),
        synthesizer=dict(dict='fr/french_synth.dict', tags='fr/french_tags.txt', sor='fr/fr.sor',
                         impl='FrenchSynthesizer'),
        word_tokenizer='FrenchWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('fr/multiwords.txt', True, True, False, remove_previous_tags=True), xml(True)],
        rules=[R('CommaWhitespaceRule', quotes_whitespace_check=False), R('DoublePunctuationRule'),
               brackets(['[', '(', '{'], [']', ')', '}']), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('LongSentenceRule', max_words=40),
               R('LongParagraphRule'), R('CompoundRule'), R('QuestionWhitespaceStrictRule'),
               R('QuestionWhitespaceRule'), R('SimpleReplaceRule'), R('FrenchRepeatedWordsRule')],
    ),
    # org.languagetool.language.Irish (code in langtool.lang.ga); its
    # MorfologikIrishSpellerRule (after WordRepeatRule) is not ported (spell
    # checking)
    'ga': dict(
        name='Irish', countries=['IE'], variants=[V('ga-IE')], sentence_tokenizer='srx',
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
    # org.languagetool.language.Galician (code in langtool.lang.gl); its
    # HunspellRule (after GenericUnpairedBracketsRule) is not ported (spell
    # checking)
    'gl': dict(
        name='Galician', countries=['ES'], variants=[V('gl-ES')], sentence_tokenizer='srx',
        tagger=dict(dict='gl/galician.dict', lowercase_with_uppercase=True, impl='GalicianTagger'),
        synthesizer=dict(dict='gl/galician_synth.dict', tags='gl/galician_tags.txt'),
        word_tokenizer='GalicianWordTokenizer',
        disambiguator=[mw('gl/multiwords.txt'), xml()],
        rules=[R('CommaWhitespaceRule',
                 examples=('Tomamos café<marker> ,</marker> queixo, bolachas e uvas.',
                           'Tomamos café<marker>,</marker> queixo, bolachas e uvas.')),
               R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '“', '«', '»', '‘', '"', "'"], [']', ')', '}', '”', '»', '«', '’', '"', "'"]),
               R('UppercaseSentenceStartRule',
                 examples=('Esta casa é vella. <marker>foi</marker> construida en 1950.',
                           'Esta casa é vella. <marker>Foi</marker> construida en 1950.')),
               R('MultipleWhitespaceRule'), R('LongSentenceRule', max_words=50),
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
    # org.languagetool.language.Italian (code in langtool.lang.it); its
    # MorfologikItalianSpellerRule (after GenericUnpairedBracketsRule) is not
    # ported (spell checking), nor is ItalianConfusionProbabilityRule
    # (language model)
    'it': dict(
        name='Italian', countries=['IT', 'CH'], variants=[V('it')], sentence_tokenizer='srx',
        tagger=dict(dict='it/italian.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='it/italian_synth.dict', tags='it/italian_tags.txt'),
        disambiguator=[xml()],
        rules=[R('WhitespaceBeforePunctuationRule'), R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '»', '«'], [']', ')', '}', '«', '»']), R('UppercaseSentenceStartRule'),
               R('ItalianWordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Japanese (code in langtool.lang.ja)
    'ja': dict(
        name='Japanese', countries=['JP'], variants=[V('ja-JP')], sentence_tokenizer='srx',
        tagger=dict(impl='JapaneseTagger'), word_tokenizer='JapaneseWordTokenizer',
        rules=[R('DoublePunctuationRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Khmer (code in langtool.lang.km); its
    # KhmerHunspellRule (first in getRelevantRules) is not ported (spell
    # checking)
    'km': dict(
        name='Khmer', countries=['KH'], variants=[V('km-KH')], sentence_tokenizer='srx',
        tagger=dict(dict='km/khmer.dict', lowercase_with_uppercase=True), word_tokenizer='KhmerWordTokenizer',
        disambiguator=[xml()],
        rules=[R('KhmerSimpleReplaceRule'), R('KhmerWordRepeatRule'), R('KhmerUnpairedBracketsRule'),
               R('KhmerSpaceBeforeRule')],
    ),
    # org.languagetool.language.Lithuanian (code in langtool.lang.lt); its
    # MorfologikLithuanianSpellerRule (after GenericUnpairedBracketsRule) is
    # not ported (spell checking)
    'lt': dict(
        name='Lithuanian', countries=['LT'], variants=[V('lt-LT')], tagger=None, sentence_tokenizer='srx',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Malayalam (code in langtool.lang.ml); its
    # MorfologikMalayalamSpellerRule (after GenericUnpairedBracketsRule) is
    # not ported (spell checking)
    'ml': dict(
        name='Malayalam', countries=['IN'], variants=[V('ml-IN')], sentence_tokenizer='srx',
        tagger=dict(dict='ml/malayalam.dict', lowercase_with_uppercase=True),
        word_tokenizer='MalayalamWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Dutch and BelgianDutch (code in
    # langtool.lang.nl); the MorfologikDutchSpellerRule (after
    # UppercaseSentenceStartRule) is not ported (spell checking)
    'nl': dict(
        name='Dutch', countries=['NL', 'BE'], default_variant='nl', sentence_tokenizer='srx',
        quotes=('“', '”', '‘', '’'), advanced_typography=True,
        variants=[V('nl', name='Dutch', extra_rule_files=['nl-NL/grammar.xml']),
                  V('nl-BE', countries=['BE'], name='Dutch (Belgium)')],
        tagger=dict(dict='nl/dutch.dict', lowercase_with_uppercase=True, impl='DutchTagger'),
        synthesizer=dict(dict='nl/dutch_synth.dict', tags='nl/dutch_tags.txt', sor='nl/nl.sor'),
        word_tokenizer='DutchWordTokenizer',
        # DutchHybridDisambiguator
        disambiguator=[mw('spelling_global.txt', False, True, False, _NONE, ignore_spelling=True),
                       mw('nl/multiwords.txt', True, True, False, _NONE, ignore_spelling=True), xml(True)],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '“', '‹', '“', '„', '"'], [']', ')', '}', '”', '›', '”', '”', '"']),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule'), R('CompoundRule'),
               R('DutchWrongWordInContextRule'), R('WordCoherencyRule'), R('SimpleReplaceRule'),
               R('LongSentenceRule', max_words=40), R('LongParagraphRule'), R('PreferredWordRule'),
               R('SpaceInCompoundRule'), R('SentenceWhitespaceRule'), R('CheckCaseRule')],
    ),
    # org.languagetool.language.Polish (code in langtool.lang.pl); its
    # MorfologikPolishSpellerRule (after PolishUnpairedBracketsRule) is not
    # ported (spell checking)
    'pl': dict(
        name='Polish', countries=['PL'], variants=[V('pl-PL')], sentence_tokenizer='srx',
        tagger=dict(dict='pl/polish.dict', lowercase_with_uppercase=True, impl='PolishTagger'),
        synthesizer=dict(dict='pl/polish_synth.dict', tags='pl/polish_tags.txt', impl='PolishSynthesizer'),
        word_tokenizer='PolishWordTokenizer',
        disambiguator=[xml(), mw('pl/multiwords.txt')],
        rules=[R('CommaWhitespaceRule'), R('UppercaseSentenceStartRule'), R('WordRepeatRule'),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('PolishUnpairedBracketsRule'),
               R('PolishWordRepeatRule'), R('CompoundRule'), R('SimpleReplaceRule'), R('WordCoherencyRule'),
               R('DashRule')],
    ),
    # org.languagetool.language.Portuguese, PortugalPortuguese,
    # BrazilianPortuguese, AngolaPortuguese and MozambiquePortuguese (code in
    # langtool.lang.pt); the MorfologikPortugueseSpellerRule (after
    # GenericUnpairedBracketsRule) is not ported (spell checking), nor is
    # PortugueseConfusionProbabilityRule (language model).
    # PortugueseHybridDisambiguator: the MultiWordChunkers for
    # spelling_global.txt and pt/multiwords.txt, then the XmlRuleDisambiguator
    # (of the default variant pt-PT) with the global disambiguation rules
    'pt': dict(
        name='Portuguese', countries=['', 'CV', 'GW', 'MO', 'ST', 'TL'], default_variant='pt-PT',
        sentence_tokenizer='srx', quotes=('“', '”', '‘', '’'), advanced_typography=True,
        variants=[
            V('pt', name='Portuguese'),
            V('pt-PT', countries=['PT'], name='Portuguese (Portugal)', quotes=('«', '»', '‘', '’'),
              priorities={'PT_COMPOUNDS_POST_REFORM': 1, 'PORTUGUESE_OLD_SPELLING_INTERNAL': -9},
              extra_rules=[R('PostReformPortugueseCompoundRule'), R('PostReformPortugueseDashRule'),
                           R('PortugueseAgreementReplaceRule'),
                           R('PortugalPortugueseReplaceRule', path='/pt/pt-PT/replace.txt'),
                           R('PortugueseBarbarismsRule', path='/pt/pt-PT/barbarisms.txt'),
                           R('PortugueseArchaismsRule', path='/pt/pt-PT/archaisms.txt'),
                           R('PortugueseClicheRule', path='/pt/pt-PT/cliches.txt'),
                           R('PortugueseRedundancyRule', path='/pt/pt-PT/redundancies.txt'),
                           R('PortugueseWordinessRule', path='/pt/pt-PT/wordiness.txt'),
                           R('PortugueseWikipediaRule', path='/pt/pt-PT/wikipedia.txt')]),
            V('pt-BR', countries=['BR'], name='Portuguese (Brazil)',
              extra_rules=[R('PostReformPortugueseCompoundRule'), R('PostReformPortugueseDashRule'),
                           R('BrazilianPortugueseReplaceRule', path='/pt/pt-BR/replace.txt'),
                           R('PortugueseBarbarismsRule', path='/pt/pt-BR/barbarisms.txt'),
                           R('PortugueseArchaismsRule', path='/pt/pt-BR/archaisms.txt'),
                           R('PortugueseClicheRule', path='/pt/pt-BR/cliches.txt'),
                           R('PortugueseRedundancyRule', path='/pt/pt-BR/redundancies.txt'),
                           R('PortugueseWordinessRule', path='/pt/pt-BR/wordiness.txt'),
                           R('PortugueseWikipediaRule', path='/pt/pt-BR/wikipedia.txt')]),
            V('pt-AO', countries=['AO'], name='Portuguese (Angola preAO)',
              extra_rules=[R('PreReformPortugueseCompoundRule'), R('PreReformPortugueseDashRule')]),
            V('pt-MZ', countries=['MZ'], name='Portuguese (Moçambique preAO)',
              extra_rules=[R('PreReformPortugueseCompoundRule'), R('PreReformPortugueseDashRule')]),
        ],
        tagger=dict(dict='pt/portuguese.dict', lowercase_with_uppercase=True, impl='PortugueseTagger'),
        synthesizer=dict(dict='pt/portuguese_synth.dict', tags='pt/portuguese_tags.txt', sor='pt/pt.sor'),
        word_tokenizer='PortugueseWordTokenizer',
        disambiguator=[mw('spelling_global.txt', False, True, True, 'NPCN000', ignore_spelling=True),
                       mw('pt/multiwords.txt', True, True, True, ignore_spelling=True, remove_previous_tags=True),
                       xml(True)],
        rules=_PT_RULES,
    ),
    # org.languagetool.language.Romanian (code in langtool.lang.ro); its
    # MorfologikRomanianSpellerRule (after WordRepeatRule) is not ported
    # (spell checking)
    'ro': dict(
        name='Romanian', countries=['RO'], variants=[V('ro-RO')], sentence_tokenizer='srx',
        tagger=dict(dict='ro/romanian.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='ro/romanian_synth.dict', tags='ro/romanian_tags.txt'),
        word_tokenizer='RomanianWordTokenizer',
        disambiguator=[xml()],
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('UppercaseSentenceStartRule'),
               R('MultipleWhitespaceRule'), brackets(['[', '(', '{', '„', '«', '»'], [']', ')', '}', '”', '»', '«']),
               R('WordRepeatRule'), R('RomanianWordRepeatBeginningRule'), R('SimpleReplaceRule'),
               R('CompoundRule')],
    ),
    # org.languagetool.language.Russian (code in langtool.lang.ru); its
    # MorfologikRussianSpellerRule (after UppercaseSentenceStartRule) and
    # MorfologikRussianYOSpellerRule (after PunctuationMarkAtParagraphEnd2)
    # are not ported (spell checking). RussianHybridDisambiguator: the
    # MultiWordChunker, then the XmlRuleDisambiguator
    'ru': dict(
        name='Russian', countries=['RU'], variants=[V('ru-RU')], ignored_characters_regex='[\u00AD\u0301\u0300]',
        sentence_tokenizer='srx', quotes=('«', '»', '‘', '’'), advanced_typography=True,
        tagger=dict(dict='ru/russian.dict', lowercase_with_uppercase=True, impl='RussianTagger'),
        synthesizer=dict(dict='ru/russian_synth.dict', tags='ru/tags_russian.txt'),
        word_tokenizer='RussianWordTokenizer',
        disambiguator=[mw('ru/multiwords.txt'), xml()],
        post_disambiguation_chunker='RussianChunker',
        rules=[R('CommaWhitespaceRule',
                 examples=('Не род<marker> ,</marker> а ум поставлю в воеводы.',
                           'Не род<marker>,</marker> а ум поставлю в воеводы.')),
               R('UppercaseSentenceStartRule',
                 examples=('Закончилось лето. <marker>дети</marker> снова сели за школьные парты.',
                           'Закончилось лето. <marker>Дети</marker> снова сели за школьные парты.')),
               R('MultipleWhitespaceRule'), R('SentenceWhitespaceRule'), R('WhiteSpaceBeforeParagraphEnd'),
               R('WhiteSpaceAtBeginOfParagraph'), R('LongSentenceRule', max_words=50), R('LongParagraphRule'),
               R('ParagraphRepeatBeginningRule'), R('RussianFillerWordsRule'), R('PunctuationMarkAtParagraphEnd2'),
               R('RussianUnpairedBracketsRule'), R('RussianCompoundRule'), R('RussianSimpleReplaceRule'),
               R('RussianSimpleWordRepeatRule'), R('RussianWordCoherencyRule'), R('RussianWordRepeatRule'),
               R('RussianWordRootRepeatRule'), R('RussianVerbConjugationRule'), R('RussianDashRule'),
               R('RussianSpecificCaseRule')],
    ),
    # org.languagetool.language.Slovak (code in langtool.lang.sk); its
    # MorfologikSlovakSpellerRule (after CompoundRule) is not ported (spell
    # checking)
    'sk': dict(
        name='Slovak', countries=['SK'], variants=[V('sk-SK')], extra_rule_files=['grammar-typography.xml'],
        sentence_tokenizer='srx',
        tagger=dict(dict='sk/slovak.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='sk/slovak_synth.dict', tags='sk/slovak_tags.txt'),
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '„', '»', '«', '"'], [']', ')', '}', '“', '«', '»', '"']),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule'),
               R('CompoundRule')],
    ),
    # org.languagetool.language.Slovenian (code in langtool.lang.sl); its
    # MorfologikSlovenianSpellerRule (after GenericUnpairedBracketsRule) is
    # not ported (spell checking)
    'sl': dict(
        name='Slovenian', countries=['SI'], variants=[V('sl-SI')], tagger=None, sentence_tokenizer='srx',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'),
               brackets(['[', '(', '{', '„', '»', '«', '"'], [']', ')', '}', '”', '«', '»', '"']),
               R('UppercaseSentenceStartRule'), R('WordRepeatRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Swedish (code in langtool.lang.sv); its
    # HunspellRule (after GenericUnpairedBracketsRule) is not ported (spell
    # checking). SwedishHybridDisambiguator: XmlRuleDisambiguator, then the
    # MultiWordChunker
    'sv': dict(
        name='Swedish', countries=['SE', 'FI'], variants=[V('sv')], sentence_tokenizer='srx',
        tagger=dict(dict='sv/swedish.dict', lowercase_with_uppercase=True),
        synthesizer=dict(dict='sv/swedish_synth.dict', tags='sv/swedish_synth.dict_tags.txt', sor='sv/sv.sor'),
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
    # org.languagetool.language.Tagalog (code in langtool.lang.tl); its
    # MorfologikTagalogSpellerRule (after MultipleWhitespaceRule) is not
    # ported (spell checking)
    'tl': dict(
        name='Tagalog', countries=['PH'], variants=[V('tl-PH')], sentence_tokenizer='srx',
        tagger=dict(dict='tl/tagalog.dict', lowercase_with_uppercase=True), word_tokenizer='TagalogWordTokenizer',
        rules=[R('CommaWhitespaceRule'), R('DoublePunctuationRule'), R('GenericUnpairedBracketsRule'),
               R('UppercaseSentenceStartRule'), R('MultipleWhitespaceRule')],
    ),
    # org.languagetool.language.Ukrainian (code in langtool.lang.uk); the
    # MorfologikUkrainianSpellerRule (after HiddenCharacterRule) is not ported
    # (spell checking), only its misspelling check and speller suggestions
    # (the default spelling rule, used by SimpleReplaceRule);
    # isAdvancedTypographyEnabled() is false
    'uk': dict(
        name='Ukrainian', countries=['UA'], variants=[V('uk-UA')], ignored_characters_regex='[­́]',
        quotes=('«', '»', '‘', '’'),
        extra_rule_files=['grammar-spelling.xml', 'grammar-grammar.xml', 'grammar-barbarism.xml',
                          'grammar-style.xml', 'grammar-punctuation.xml'],
        tagger=dict(dict='uk/ukrainian.dict', lowercase_with_uppercase=False, impl='UkrainianTagger'),
        synthesizer=dict(dict='uk/ukrainian_synth.dict', tags='uk/ukrainian_tags.txt',
                         impl='UkrainianSynthesizer'),
        word_tokenizer='UkrainianWordTokenizer',
        disambiguator=[('custom', 'UkrainianHybridDisambiguator')],
        rules=[R('UkrainianCommaWhitespaceRule',
                 examples=('Ми обідали борщем<marker> ,</marker> пловом і салатом,— все смачне.',
                           'Ми обідали борщем<marker>,</marker> пловом і салатом,— все смачне')),
               R('UkrainianUppercaseSentenceStartRule',
                 examples=('<marker>речення</marker> має починатися з великої.',
                           '<marker>Речення</marker> має починатися з великої')),
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

# All language modules override Language.createDefaultSentenceTokenizer()
# (Crimean Tatar: getSentenceTokenizer()) with an SRXSentenceTokenizer
for _d in LANGUAGES.values():
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
