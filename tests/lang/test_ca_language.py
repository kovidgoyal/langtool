"""Port of org.languagetool.rules.ca.CatalanTest (LanguageSpecificTest) and
org.languagetool.JLanguageToolTest (language-ca), plus checks of the
Catalan language definition against org.languagetool.language.Catalan,
ValencianCatalan and BalearicCatalan. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py.
MorfologikCatalanSpellerRuleTest and LanguageSpecificSpellcheckerTest test
the spell checking rule MORFOLOGIK_RULE_CA_ES (not ported, see the skipped
tests below); CatalanDisambiguationProfile is a profiling program, not a
test."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ca.multitoken import CatalanMultitokenDisambiguator, CatalanMultitokenSpeller
from langtool.lang.ca.replace_rules import SimpleReplaceAnglicism, SimpleReplaceMultiwordsRule
from langtool.lang.ca.spelling import MorfologikCatalanSpellerCheck
from langtool.lang.ca.synthesis import CatalanSynthesizer
from langtool.lang.ca.tagging import CatalanTagger
from langtool.lang.ca.tokenizers import CatalanWordTokenizer
from langtool.messages import messages_for
from langtool.rules.core import CommaWhitespaceRule
from langtool.tool import LEVEL_PICKY, JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ca')


@pytest.fixture(scope='module')
def lang():
    return get_language('ca-ES')


@pytest.fixture(scope='module')
def tool(lang):
    return JLanguageTool(lang)


def _java_list(items):
    # List.toString()
    return '[' + ', '.join(items) + ']'


# --- CatalanTest ---

def test_demo_text(lang):
    """CatalanTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Introduïu açí el vostre text. o feu servir aquest texts com a a exemple per a alguns errades que '
         'LanguageTool hi pot detectat.')
    matches = JLanguageTool(lang).check(s)
    # Java expects a first match of MORFOLOGIK_RULE_CA_ES (for "açí"), the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'UPPERCASE_SENTENCE_START', 'CONCORDANCES_DET_NOM', 'CATALAN_WORD_REPEAT_RULE', 'CONCORDANCES_DET_NOM',
        'VERB_SEGUIT_DINFINITIU']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificTest.testReplaceRuleReplacements only '
                         'prints warnings for replacements of the replace rules that the spelling rule '
                         'MORFOLOGIK_RULE_CA_ES rejects')
def test_replace_rule_replacements():
    """CatalanTest.testLanguage (testReplaceRuleReplacements for ca-ES-valencia)"""


@pytest.mark.parametrize('text,full_id', [
    ('Iniciem les converses. Llavors s\'inicià una altra cosa.', 'REP_INICIAR[1]'),
    ('Iniciem les converses. Llavors inicià una altra cosa.', 'REP_INICIAR[2]'),
    ('Aleshores iniciem les converses. Llavors inicià una altra cosa.', 'REP_INICIAR[2]'),
    ('S\'inicia el debat. Llavors inicià una altra cosa.', 'REP_INICIAR[2]'),
    ('S\'inicia el debat. Llavors s\'inicià una altra cosa.', 'REP_INICIAR[1]'),
    ('Això no obstant, és clar. No obstant això, la cosa és clara.', 'REP_NO_OBSTANT_AIXO[1]'),
])
def test_repeated_pattern_rules(tool, text, full_id):
    """CatalanTest.testRepeatedPatternRules"""
    matches = tool.check(text, level=LEVEL_PICKY)
    # Matches across rules in a rule group
    assert len(matches) == 1
    assert matches[0].rule.get_full_id() == full_id


def test_trim_match_ends(lang):
    """CatalanTest.testTrimMatchEnds"""
    # SOLVENTAR_LA_PAPELETA: the verb prefix "Van" is common to error and all suggestions,
    # so the underline should be trimmed to "solventar la papeleta" only.
    lt = JLanguageTool(lang)
    lt.enable_rule('SOLVENTAR_LA_PAPELETA')
    sentence = 'Van solventar la papeleta.'
    matches = lt.check(sentence)
    assert len(matches) == 1
    match = matches[0]
    assert sentence[match.from_pos:match.to_pos] == 'solventar la papeleta'
    assert _java_list(match.suggested_replacements) == \
        '[sortir del pas, eixir del pas, treure les castanyes del foc, salvar els mobles]'


# --- MorfologikCatalanSpellerRuleTest, LanguageSpecificSpellcheckerTest ---

@pytest.mark.skip(reason='spell checking is not ported: MorfologikCatalanSpellerRuleTest tests the matches and '
                         'suggestions of the spelling rule MORFOLOGIK_RULE_CA_ES')
def test_morfologik_speller():
    """MorfologikCatalanSpellerRuleTest"""


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest '
                         '(SpellcheckerTest.runLanguageSpecificTest) tests the spelling rule of the language')
def test_language_specific_spellchecker():
    """LanguageSpecificSpellcheckerTest.testRules"""


# --- JLanguageToolTest ---

def test_clean_overlapping_errors(tool):
    """JLanguageToolTest.testCleanOverlappingErrors"""
    matches = tool.check('prosper')
    assert len(matches) == 1
    assert matches[0].rule.get_id() == 'CA_SIMPLE_REPLACE_BALEARIC_PROSPER'
    matches = tool.check('Potser siga el millor')
    assert len(matches) == 1
    assert matches[0].rule.get_id() == 'POTSER_SIGUI'
    # ChunkTags
    assert _java_list(str(s) for s in tool.analyze_text('Ho deu haver tornat a fer.')) == (
        '[<S> Ho[ho/PP3NN000] deu[deure/VMIP3S00,GV] haver[haver/VAN00000,haver/_GV_,haver/_perfet,GV] '
        'tornat[tornar/VMP00SM0,GV] a[a/SPS00,GV] fer[fer/VMN00000,fer/complement,GV].[</S>./_PUNCT,<P/>]]')
    assert _java_list(str(s) for s in tool.analyze_text('Ho he de continuar fent així.')) == (
        '[<S> Ho[ho/PP3NN000] he[haver/VAIP1S00,haver/_obligacio,GV] de[de/SPS00,GV] '
        'continuar[continuar/VMN00000,continuar/_GV_,GV] fent[fer/VMG00000,fent/_GV_,GV] '
        'així[així/RG].[</S>./_PUNCT,<P/>]]')


def test_global_spelling(tool):
    """JLanguageToolTest.testGlobalSpelling"""
    assert len(tool.check('Johann Sebastian Bach, cantata BWV 126')) == 0


def test_hyphenated_plus_compound(tool):
    """JLanguageToolTest.testHyphenatedPlusCompound"""
    matches = tool.check(
        'c) Quan el prefix precedeix una locució, un sintagma o un mot que ja porta guionet: manifestació '
        'anti-cascos blaus, al·legat anti-pena de mort, ex-conseller en cap, ex-directora general, ex-Unió '
        'Soviètica, l’ambient pre-Segona Guerra Mundial, manifestació pro-dret de vaga, pseudo-petita burgesia, '
        'vice-primer ministre; actitud anti-nord-americana.')
    assert len(matches) == 0


@pytest.mark.parametrize('text,suggestion', [
    ('Cal usar mètodes d\'anàlisi adequats.', None),
    ('Tant de bo s\'imposen el diàleg i la diplomàcia', None),
    ('Persones humanes', None),
    ('Aquests ganivets no corresponen amb estes forquilles.', 'aquestes'),
    ('Estes forquilles, aquestos ganivets.', 'estos'),
    ('Estes forquilles, aquests ganivets.', 'estos'),
    ('Aqueixes forquilles, eixos ganivets.', 'aqueixos'),
    ('Eixes forquilles, aqueixos ganivets.', 'eixos'),
    ('Estos ganivets no corresponen amb estes forquilles.', None),
    ('Aquests ganivets no corresponen amb aquestes forquilles.', None),
    ('Com no te vaig a estimar?', 'vols que no t\'estime'),
    # Java gets a match of MORFOLOGIK_RULE_CA_ES (the spell checker, not ported) with the suggestion "provar"
    ('Aquestes frases per a probar.', None),
    # Java gets a match of MORFOLOGIK_RULE_CA_ES with the suggestion "conéixer"
    ('Vull coneixer més coses.', None),
    ('Durant l\u0092estiu.', 'l\'estiu'),
])
def test_valencian_variant(text, suggestion):
    """JLanguageToolTest.testValencianVariant"""
    matches = JLanguageTool(get_language('ca-ES-valencia')).check(text)
    if suggestion is None:
        assert len(matches) == 0
    else:
        assert len(matches) == 1
        assert matches[0].suggested_replacements[0] == suggestion


def test_balearic_variant():
    """JLanguageToolTest.testBalearicVariant"""
    tool = JLanguageTool(get_language('ca-ES-balear'))
    assert len(tool.check('Cal usar mètodes d\'anàlisi adequats.')) == 0
    # Java gets a match of MORFOLOGIK_RULE_CA_ES (the spell checker, not ported) with the suggestion "provar"
    assert len(tool.check('Aquestes frases per a probar.')) == 0
    assert len(tool.check('Pens que és una cosa bona.')) == 0


def test_advanced_typography(lang):
    """JLanguageToolTest.testAdvancedTypography"""
    assert lang.to_advanced_typography('És l\'"hora"!') == 'És l’«hora»!'
    assert lang.to_advanced_typography('És l\'\'hora\'!') == 'És l’‘hora’!'
    assert lang.to_advanced_typography('És l\'«hora»!') == 'És l’«hora»!'
    assert lang.to_advanced_typography('És l\'\'hora\'.') == 'És l’‘hora’.'
    assert lang.to_advanced_typography('Cal evitar el "\'lo\' neutre".') == 'Cal evitar el «‘lo’ neutre».'
    assert lang.to_advanced_typography('És "molt \'important\'".') == 'És «molt ‘important’».'
    assert lang.to_advanced_typography('Si és del v. \'haver\'.') == 'Si és del v. ‘haver’.'
    assert lang.to_advanced_typography('Amb el so de \'s\'.') == 'Amb el so de ‘s’.'
    from langtool.rules.core_filters import adapt_suggestion
    assert adapt_suggestion(lang, 'L\'IEC', '') == 'L\'IEC'
    assert adapt_suggestion(lang, 'te estimava', 'Estimava') == 'T\'estimava'
    assert adapt_suggestion(lang, 'el Albert', '') == 'l\'Albert'
    assert adapt_suggestion(lang, 'l\'Albert', '') == 'l\'Albert'
    assert adapt_suggestion(lang, 'l\'«Albert»', '') == 'l\'«Albert»'
    assert adapt_suggestion(lang, 'l’«Albert»', '') == 'l’«Albert»'
    assert adapt_suggestion(lang, 'l\'"Albert"', '') == 'l\'"Albert"'
    assert adapt_suggestion(lang, 'm\'tancava', '') == 'em tancava'
    assert adapt_suggestion(lang, 's\'tancava', '') == 'es tancava'
    assert adapt_suggestion(lang, 'l\'R+D', '') == 'l\'R+D'
    assert adapt_suggestion(lang, 'l\'FBI', '') == 'l\'FBI'


def test_adapt_suggestions(tool):
    """JLanguageToolTest.testAdaptSuggestions"""
    matches = tool.check(
        'Els valencians hem sigut valencians des que Jaume I creà el regne de València i poc a poc es conformà una '
        'nova identitat política (que en l\'edat mitjana, per exemple, no entrava en contradicció amb la '
        'consciència clara que teníem un origen i una llengua comuns amb els catalans).')
    assert _java_list(matches[0].suggested_replacements) == '[a poc]'
    matches = tool.check('A nivell d\'ensenyament superior.')
    assert _java_list(matches[0].suggested_replacements) == \
        '[En l\'àmbit d\', A escala d\', A , En , Pel que fa a , Quant a ]'


def test_adjust_catalan_match(tool):
    """JLanguageToolTest.testAdjustCatalanMatch"""
    matches = tool.check('No sé què dir. No aconseguia a dormir per la calor.')
    # avoid two white spaces after removing word
    assert len(matches) == 1
    assert matches[0].get_from_pos_sentence() == 14
    assert matches[0].get_to_pos_sentence() == 16
    assert matches[0].from_pos == 29
    assert matches[0].to_pos == 31
    matches = tool.check('Se m\'han saltat les llàgrimes.')
    assert len(matches) == 1
    assert matches[0].get_from_pos_sentence() == 0
    assert matches[0].get_to_pos_sentence() == 5


@pytest.mark.parametrize('text,expected', [
    ('Hans-Herrmann Hoppe', '[Hans-Hermann Hoppe]'),
    ('Manuel sadosky', '[Manuel Sadosky]'),
    ('Manuel Sadusky', '[Manuel Sadosky]'),
    ('Jacques Louis David', '[Jacques-Louis David]'),
    ('Chiang Kaishek', '[Chiang Kai-shek]'),
    ('Comédie Français', '[Comédie-Française]'),
    ('Luis Leante', '[]'),
    ('in vinos verita', '[in vino veritas]'),
    ('Marina Buisan', '[]'),
    ('Homos Sapiens', '[Homo sapiens]'),
    ('Garcia Horta', '[]'),
    ('Jon Benn', '[John Venn]'),
    ('josue garcia', '[José Garcia, José García]'),
    ('Franco more', '[Franco Mori]'),
    ('maria Lopez', '[María López]'),
    ('carlos fesi', '[]'),
    ('Nicolai Rimski-Kórsakov', '[Nikolai Rimski-Kórsakov]'),
    ('Rimsky-Korsakov', '[Rimski-Kórsakov]'),
    ('Johan Sebastián Bach', '[Johann Sebastian Bach]'),
    ('Johan Sebastián Bach', '[Johann Sebastian Bach]'),
    ('Johann Sebastián Bach', '[Johann Sebastian Bach]'),
    ('Plantation Boy', '[]'),
    ('Woodie Alen', '[Woody Allen]'),
    ('Eugenio Granjo', '[]'),
    ('Julia García', '[Julio García]'),
    ('Deustche Bank', '[Deutsche Bank]'),
    ('Dimitri Mendeleev', '[Dmitri Mendeléiev]'),
    ('Caralp Mariné', '[]'),
    ('Alejandro Varón', '[]'),
    ('Alejandro Mellado', '[]'),
    ('Alejandro Erazo', '[]'),
    ('Alberto Saoner', '[]'),
    ('è più', '[]'),
    ('Josep Maria Canudas', '[]'),
    ('Francisco Javier Dra.', '[]'),
    ('the usage of our', '[]'),
    ('A paso', '[]'),
    ('A sin', '[]'),
    ('A xente', '[]'),
    ('A lus', '[]'),
    ('A Month', '[]'),
    ('peis espaba', '[peix espasa]'),
    ('finç abui', '[]'),
    ('Led Zepelin', '[Led Zeppelin]'),
    ('Led Sepelin', '[Led Zeppelin]'),
    ('Marie Cuirie', '[Marie Curie]'),
    ('William Bird', '[William Byrd]'),
    ('Lluis Llach', '[Lluís Llach]'),
    ('Universiti of Tejas', '[University of Texas]'),
    ('Cindy Lauper', '[Cyndi Lauper]'),
    ('Garcìa Mraquez', '[García Márquez]'),
    ('yuval Noha Harari', '[Yuval Noah Harari]'),
    ('Frederic Udina', '[]'),
    ('Josep Maria Piñol', '[]'),
    ('Jose Maria Asnar', '[José María Aznar]'),
    ('José María Asnar', '[José María Aznar]'),
])
def test_multitoken_speller(lang, text, expected):
    """JLanguageToolTest.testMultitokenSpeller"""
    assert _java_list(lang.get_multitoken_speller().get_suggestions(text)) == expected


def test_comma_whitespace_rule(tool):
    """JLanguageToolTest.testCommaWhitespaceRule"""
    rule = CommaWhitespaceRule(messages_for('en'), get_language('ca-ES'))
    assert len(rule.match(tool.get_analyzed_sentence('Sol Picó (\U0001f40c+\U0001f41a)'))) == 0
    assert len(rule.match(tool.get_analyzed_sentence('Els fitxers .edu i .htaccess són especials.'))) == 0
    matches1 = tool.check('Continuo veien cada dia gent amb ID baixa ')
    assert matches1[0].rule.get_id() == 'GERUNDI_PERD_T'


def test_replace_multiwords(tool):
    """JLanguageToolTest.testReplaceMultiwords"""
    rule = SimpleReplaceMultiwordsRule(messages_for('en'))
    matches = rule.match(tool.get_analyzed_sentence('Les persones membres'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Els membres'
    matches = rule.match(tool.get_analyzed_sentence('LES PERSONES MEMBRES'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'ELS MEMBRES'


def test_replace_anglicisms(tool):
    """JLanguageToolTest.testReplaceAnglicisms"""
    rule = SimpleReplaceAnglicism(messages_for('en'))
    assert len(rule.match(tool.get_analyzed_sentence('que són la revolució física (Bacon, Galileu)'))) == 0
    assert len(rule.match(tool.get_analyzed_sentence('de E-Commerce'))) == 1


def test_catalan_long_sentence_rule(lang):
    """JLanguageToolTest.testCatalanLongSentenceRule (with the cached
    response of CatalanRemoteRewriteHelper, no remote server)"""
    tool = JLanguageTool(lang)
    tool.enable_rule('CA_SPLIT_LONG_SENTENCE')
    matches = tool.check(
        'En una tarda grisa que avançava sense pressa sobre els carrers estrets de la ciutat, mentre els comerços '
        'abaixaven persianes i el soroll del trànsit es diluïa en un murmuri constant, un home caminava pensant en '
        'decisions ajornades, en paraules no dites i en projectes que havia volgut compondre amb rigor, però que el '
        'cansament havia anat desfigurant i, així i tot, convençut que encara disposava de prou lucidesa per a '
        'ordenar les idees, assumir els errors, fer servir l’experiència acumulada com a criteri i continuar '
        'avançant amb una determinació menys impulsiva però més sòlida.', level=LEVEL_PICKY)
    assert _java_list(matches[0].suggested_replacements) == '[desfigurant. I]'


def test_ignore_proper_nouns(tool):
    """JLanguageToolTest.testIgnoreProperNouns"""
    matches = tool.check(
        'Henna Virkkunen ha remarcat que la venda de productes il·legals a la UE era del tot prohibida. Virkkunen '
        'ha reivindicat la llei de serveis digitals.', level=LEVEL_PICKY)
    assert len(matches) == 0


def test_specific_xml_rule(tool):
    """JLanguageToolTest.testSpecificXMLRule"""
    matches = tool.check('Moldejant-les', level=LEVEL_PICKY)
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == '[Modelant-les, Afaiçonant-les]'


# --- the language definition ---

def test_definition(lang):
    assert lang.code == 'ca-ES'
    assert lang.name == 'Catalan'
    assert lang.countries == ['ES']
    assert not lang.is_variant()
    assert get_language('ca') is lang
    valencian = get_language('ca-ES-valencia')
    assert valencian.name == 'Catalan (Valencian)' and valencian.countries == ['ES'] and valencian.is_variant()
    assert valencian.variant == 'valencia' and valencian.default_variant is lang
    assert valencian.get_default_enabled_rules_for_variant() == [
        'EXIGEIX_VERBS_VALENCIANS', 'EXIGEIX_ACCENTUACIO_VALENCIANA', 'EXIGEIX_POSSESSIUS_U', 'EXIGEIX_VERBS_EIX',
        'EXIGEIX_VERBS_ISC', 'PER_PER_A_INFINITIU', 'FINS_EL_AVL', 'LES_HA_FETES']
    assert valencian.get_default_disabled_rules_for_variant() == [
        'EXIGEIX_VERBS_CENTRAL', 'EXIGEIX_ACCENTUACIO_GENERAL', 'EXIGEIX_POSSESSIUS_V', 'EVITA_PRONOMS_VALENCIANS',
        'EVITA_DEMOSTRATIUS_EIXE', 'VOCABULARI_VALENCIA', 'EXIGEIX_US', 'FINS_EL_GENERAL', 'EVITA_INFINITIUS_INDRE',
        'EVITA_DEMOSTRATIUS_ESTE', 'CASTIC_CASTIG']
    balear = get_language('ca-ES-balear')
    assert balear.name == 'Catalan (Balearic)' and balear.countries == ['ES'] and balear.is_variant()
    assert balear.variant == 'balear' and balear.default_variant is lang
    assert balear.get_default_enabled_rules_for_variant() == ['EXIGEIX_VERBS_BALEARS']
    assert balear.get_default_disabled_rules_for_variant() == ['EXIGEIX_VERBS_CENTRAL', 'CA_SIMPLE_REPLACE_BALEARIC']
    assert lang.get_default_enabled_rules_for_variant() == []
    assert lang.get_default_disabled_rules_for_variant() == []
    # CatalanTagger.INSTANCE_CAT (Catalan and BalearicCatalan) and INSTANCE_VAL (ValencianCatalan)
    assert isinstance(lang.tagger, CatalanTagger) and not lang.tagger.is_valencian
    assert balear.tagger is lang.tagger
    assert isinstance(valencian.tagger, CatalanTagger) and valencian.tagger.is_valencian
    # CatalanSynthesizer.INSTANCE_CAT, INSTANCE_VAL and INSTANCE_BAL
    for language in (lang, valencian, balear):
        assert isinstance(language.synthesizer, CatalanSynthesizer)
        assert language.synthesizer.variant_code == language.code
        assert language.synthesizer.number_speller is not None
        # CatalanWordTokenizer.INSTANCE (with CatalanTagger.INSTANCE_CAT)
        assert type(language.word_tokenizer) is CatalanWordTokenizer
        assert language.word_tokenizer.tagger is lang.tagger
        # CatalanHybridDisambiguator: the chunkers for spelling_global.txt and ca/multiwords.txt, the
        # XmlRuleDisambiguator, then the CatalanMultitokenDisambiguator
        stages = language.disambiguator.stages
        assert [type(s) for s in stages] == [MultiWordChunker, MultiWordChunker, XmlRuleDisambiguator,
                                             CatalanMultitokenDisambiguator]
        # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
        st = language.sentence_tokenizer
        assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
        assert isinstance(language.get_default_spelling_rule(), MorfologikCatalanSpellerCheck)
        assert isinstance(language.get_multitoken_speller(), CatalanMultitokenSpeller)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'ca', 'grammar.xml']]
    files = [f.replace('\\', '/').rsplit('/', 4)[-4:] for f in valencian.get_rule_file_names()]
    assert files == [['data', 'rules', 'ca', 'grammar.xml'], ['rules', 'ca', 'ca-ES-valencia', 'grammar.xml']]
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in balear.get_rule_file_names()]
    assert files == [['rules', 'ca', 'grammar.xml']]


def test_typography():
    """Catalan.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    for code in ('ca-ES', 'ca-ES-valencia', 'ca-ES-balear'):
        lang = get_language(code)
        assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
                lang.get_closing_single_quote()) == ('«', '»', '‘', '’')
        assert lang.is_advanced_typography_enabled()


def test_priorities():
    """Catalan.getPriorityForId and getDefaultRulePriorityForStyle"""
    lang = get_language('ca-ES')
    p = lang.get_priority_for_id
    assert p('CONFUSIONS2') == 80
    assert p('DEU_NI_DO') == 80
    assert p('FER_LOGIN') == 70
    assert p('INCORRECT_EXPRESSIONS') == 50
    assert p('PREGUEM_DISCULPIN') == 45
    assert p('ELA_GEMINADA') == 35
    assert p('REEMPRENDRE') == 28
    assert p('PRONOMS_FEBLES_SOLTS2') == 26
    assert p('CONTRACCIONS') == 0
    assert p('CASING_START') == -5
    assert p('AGREEMENT_POSTPONED_ADJ') == -15
    assert p('MAJOR_MES_GRAN0') == -40
    assert p('REPETITIONS_STYLE') == -50
    assert p('MORFOLOGIK_RULE_CA_ES') == -100
    assert p('EXIGEIX_ACCENTUACIO_VALENCIANA') == -120
    assert p('APOSTROFACIO_MOT_DESCONEGUT') == 0  # (commented out in Java)
    assert p('CATALAN_PHRASE_REPEAT_RULE') == -150
    assert p('UPPERCASE_SENTENCE_START') == -300
    assert p('CA_SPLIT_LONG_SENTENCE') == -90
    assert p('CA_MULTITOKEN_SPELLING_X') == -95
    assert p('CA_SIMPLE_REPLACE_MULTIWORDS_X') == 70
    assert p('CA_SIMPLE_REPLACE_ANGLICISM_X') == 65
    assert p('CA_SIMPLE_REPLACE_BALEARIC_X') == 60
    assert p('CA_SIMPLE_REPLACE_VERBS_X') == 28
    assert p('CA_COMPOUNDS') == 50
    assert p('CA_SIMPLE_REPLACE_DIACRITICS_IEC_X') == 0
    assert p('CA_SIMPLE_REPLACE_SIMPLE_X') == 30
    assert p('SOME_STYLE_RULE') == -50
    assert p('TOO_LONG_SENTENCE') == -101
    assert p('OTHER') == 0
    assert lang.get('default_rule_priority_for_style') == -50
    assert get_language('ca-ES-valencia').get_priority_for_id('CA_WORD_COHERENCY_VALENCIA') == -10


def test_relevant_rules():
    lang = get_language('ca-ES')
    rules = lang.get_relevant_rules(messages_for('ca'))
    # getRelevantRules without MorfologikCatalanSpellerRule (spell checking) and CatalanRemoteRule (a remote
    # rule), which are not ported
    ids = ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS', 'UPPERCASE_SENTENCE_START',
           'WHITESPACE_RULE', 'SENTENCE_WHITESPACE', 'TOO_LONG_SENTENCE', 'CATALAN_WORD_REPEAT_RULE',
           'CATALAN_PHRASE_REPEAT_RULE', 'CA_UNPAIRED_QUESTION', 'CA_UNPAIRED_EXCLAMATION',
           'CATALAN_WRONG_WORD_IN_CONTEXT', 'CA_SIMPLE_REPLACE_VERBS', 'CA_SIMPLE_REPLACE_BALEARIC',
           'CA_SIMPLE_REPLACE_SIMPLE', 'CA_SIMPLE_REPLACE_MULTIWORDS', 'NOMS_OPERACIONS',
           'CA_SIMPLE_REPLACE_DIACRITICS_IEC', 'CA_SIMPLE_REPLACE_ANGLICISM', 'PRONOMS_FEBLES_DUPLICATS',
           'CA_CHECKCASE', 'ADVERBIS_MENT', 'CATALAN_WORD_REPEAT_BEGINNING_RULE', 'CA_COMPOUNDS',
           'CA_SIMPLE_REPLACE_DNV', 'CA_SIMPLE_REPLACE_DNV_COLLOQUIAL', 'CA_SIMPLE_REPLACE_DNV_SECONDARY',
           'CA_WORD_COHERENCY', 'PUNCTUATION_PARAGRAPH_END', 'CA_SPLIT_LONG_SENTENCE', 'IGNORE_PROPER_NOUNS']
    assert [r.get_id() for r in rules] == ids
    assert rules[6].max_words == 60
    assert rules[29].max_words == 60
    assert rules[0].incorrect_examples[0].example == 'A parer seu<marker> ,</marker> no era veritat.'
    assert rules[3].incorrect_examples[0].example == 'Preus de venda al públic. <marker>han</marker> pujat molt.'
    valencian = get_language('ca-ES-valencia')
    valencian_ids = [r.get_id() for r in valencian.get_relevant_rules(messages_for('ca'))]
    assert valencian_ids == ids + ['CA_WORD_COHERENCY_VALENCIA']
    balear = get_language('ca-ES-balear')
    assert [r.get_id() for r in balear.get_relevant_rules(messages_for('ca'))] == ids
    for language in (lang, valencian, balear):
        assert not unsupported_components(language)
