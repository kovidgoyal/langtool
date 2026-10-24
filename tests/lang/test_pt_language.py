"""Port of org.languagetool.rules.pt.PortugueseTest (LanguageSpecificTest)
and org.languagetool.JLanguageToolTest (language-pt), plus checks of the
Portuguese language definition against org.languagetool.language.Portuguese,
PortugalPortuguese, BrazilianPortuguese, AngolaPortuguese and
MozambiquePortuguese. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py
(testReplaceRuleReplacements is not ported, it needs the spell checker)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.pt.multitoken import PortugueseMultitokenSpeller
from langtool.lang.pt.rules import (BrazilianPortugueseReplaceRule, PortugalPortugueseReplaceRule,
                                    PortugueseArchaismsRule, PortugueseBarbarismsRule, PortugueseReadabilityRule,
                                    PostReformPortugueseCompoundRule, PreReformPortugueseCompoundRule)
from langtool.lang.pt.spelling import MorfologikPortugueseSpellerCheck
from langtool.lang.pt.tagging import PortugueseTagger
from langtool.lang.pt.tokenizers import PortugueseWordTokenizer
from langtool.messages import messages_for
from langtool.synthesis import BaseSynthesizer
from langtool.tool import JLanguageTool

DEMO_TEXT = ('Cole aqui seu texto...ou verifique esta texto, afim de revelar alguns dos dos problemas que o '
             'LanguageTool consegue detectar. Isto tal vez permita corrigir os seus erro. Nós prometo ajudá-lo. '
             'para testar a grafia e as regrs do antigo) Acordo Ortográfico,, verifique o mesmo texto mesmo texto '
             'em Português de Angola ou Português do Moçambique e faça a analise dos resultados.. Nossa equipe '
             'anuncia a versão 4.5, que será lançada sexta-feira, 26 de março de 2019.')


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pt')


# --- PortugueseTest ---

def test_demo_text_pt_pt():
    """PortugueseTest.testLanguage (testDemoText for pt-PT). Java expects one
    more match of MORFOLOGIK_RULE_PT_PT (for "regrs", after
    UPPERCASE_SENTENCE_START), the spell checker, which is not ported"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    matches = JLanguageTool(get_language('pt-PT')).check(DEMO_TEXT)
    assert [m.get_specific_rule_id() for m in matches] == [
        'POSSESSIVE_WITHOUT_ARTICLE', 'SPACE_AFTER_PUNCTUATION', 'RETICENCIAS_ESPACO',
        'GENERAL_GENDER_AGREEMENT_ERRORS', 'AFIM_DE', 'PORTUGUESE_WORD_REPEAT_RULE', 'PT_AGREEMENT_REPLACE_DETECTAR',
        'TAL_VEZ', 'GENERAL_NUMBER_AGREEMENT_ERRORS', 'GENERAL_VERB_AGREEMENT_ERRORS', 'UPPERCASE_SENTENCE_START',
        'UNPAIRED_BRACKETS', 'DOUBLE_PUNCTUATION', 'PHRASE_REPETITION', 'GENTILICOS_LINGUAS',
        'GENTILICOS_LINGUAS', 'ARTICLES_PRECEDING_LOCATIONS', 'PARONYM_ANALISE_363', 'DOUBLE_PUNCTUATION',
        'POSSESSIVE_WITHOUT_ARTICLE', 'EQUIPES', 'PT_DATE_WEEKDAY']


def test_demo_text_pt_br():
    """PortugueseTest.testLanguage (testDemoText for pt-BR). Java expects one
    more match of MORFOLOGIK_RULE_PT_BR (for "regrs", after
    UPPERCASE_SENTENCE_START), the spell checker, which is not ported"""
    matches = JLanguageTool(get_language('pt-BR')).check(DEMO_TEXT)
    assert [m.get_specific_rule_id() for m in matches] == [
        'SPACE_AFTER_PUNCTUATION', 'RETICENCIAS_ESPACO', 'GENERAL_GENDER_AGREEMENT_ERRORS', 'AFIM_DE',
        'PORTUGUESE_WORD_REPEAT_RULE', 'TAL_VEZ', 'GENERAL_NUMBER_AGREEMENT_ERRORS',
        'GENERAL_VERB_AGREEMENT_ERRORS', 'UPPERCASE_SENTENCE_START', 'UNPAIRED_BRACKETS', 'DOUBLE_PUNCTUATION',
        'PHRASE_REPETITION', 'GENTILICOS_LINGUAS', 'GENTILICOS_LINGUAS', 'PARONYM_ANALISE_363',
        'DOUBLE_PUNCTUATION', 'PT_DATE_WEEKDAY']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificTest.testReplaceRuleReplacements checks '
                         'that the replacements of the replace rules are accepted by the spell checker')
def test_replace_rule_replacements():
    """PortugueseTest.testLanguage (testReplaceRuleReplacements for pt-BR)"""


# --- JLanguageToolTest ---

@pytest.mark.parametrize('code', ['pt-PT', 'pt-BR', 'pt-AO', 'pt-MZ'])
def test_portuguese_variants(code):
    """JLanguageToolTest.testPortugueseVariants"""
    lt = JLanguageTool(get_language(code))
    assert len(lt.check('Isto é uma característica sua.')) == 0
    assert len(lt.check('Isto é uma características sua.')) == 1


def test_some_sentences():
    """JLanguageToolTest.testSomeSentences (no errors)"""
    lt = JLanguageTool(get_language('pt-BR'))
    lt.check('™ ® Marcas registradas da Corteva Agriscience e de suas companhias afiliadas.')
    lt.check('Vatatzes teve que lutar contra a reivindicação de Isaac e Aleixo, os irmãos de Teodoro I, que fugiram '
             'para o Império Latino e procuraram ajuda.\n'
             'Outros artistas que participaram do Vevo Lift são One Direction, 5 Seconds of Summer, Fifth Harmony, '
             'Sam Smith, Iggy Azalea, Rita Ora, Avicii, entre outros.\n'
             'Astarte (desambiguação)\n'
             'Drocourt (pas-de-calais)\n'
             'O principal trabalho do G.E.R.E.C foi desenvolver, a partir de 1976, a escrita do crioulo, incluindo uma '
             'família de padrões de ortografia.\n'
             'Zeth foi o mais novo de dez filhos.\n'
             'Segundo Ajahn Mudito, a proposta do site é dar às pessoas a oportunidade de ter esses ensinamentos '
             'traduzidos diretamente do tailandês para o português, sem ter que passar pela costumeira '
             '“retradução”, onde primeiro os ensinamentos são traduzidos para o inglês para, só depois, chegar ao '
             'nosso idioma, fato que, segundo ele, gera muitas distorções e perda de significado do ensinamento '
             'original.\n'
             'No entanto, em julho de 2016 foi anunciado como vice-prefeito na candidatura de Hélio Godoy.\n'
             'As dissecções que envolvem a aorta descendente são geralmente tratadas com medicação para baixar a '
             'pressão arterial e o ritmo cardíaco, a não ser que ocorram complicações.\n'
             'Margarethe era filha de Karl Krambeck e Catharina Neve, que emigraram de Sehestedt para o Brasil em '
             '10.03.1852, com o Vapor Princess Louize e Capitão Bähr, dirigindo-se ao Distrito de Valença/RJ, onde '
             'trabalharam na Fazenda Independência, A família Krambeck originou-se no Estado de '
             'Schleswig-Holstein, no Norte da Alemanha, e os registros existentes têm início com Claus Krambeck, '
             'por volta de 1700, em Sehestedt.')


# --- the language definition ---

def test_definition():
    lang = get_language('pt')
    assert lang.code == 'pt'
    assert lang.name == 'Portuguese'
    assert lang.countries == ['', 'CV', 'GW', 'MO', 'ST', 'TL']
    assert not lang.is_variant()
    assert lang.default_variant is get_language('pt-PT')
    for code, name, countries in (('pt-PT', 'Portuguese (Portugal)', ['PT']),
                                  ('pt-BR', 'Portuguese (Brazil)', ['BR']),
                                  ('pt-AO', 'Portuguese (Angola preAO)', ['AO']),
                                  ('pt-MZ', 'Portuguese (Moçambique preAO)', ['MZ'])):
        variant = get_language(code)
        assert (variant.name, variant.countries) == (name, countries)
        assert variant.is_variant()
        assert variant.default_variant is get_language('pt-PT')
        assert variant.get_default_disabled_rules_for_variant() == []
    assert isinstance(lang.tagger, PortugueseTagger)
    assert type(lang.synthesizer) is BaseSynthesizer
    assert lang.synthesizer.number_speller is not None
    assert type(lang.word_tokenizer) is PortugueseWordTokenizer
    # PortugueseHybridDisambiguator: the chunkers for spelling_global.txt and pt/multiwords.txt, then the
    # XmlRuleDisambiguator (of the default variant pt-PT)
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, MultiWordChunker, XmlRuleDisambiguator]
    assert stages[2].language is get_language('pt-PT')
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'pt', 'grammar.xml'], ['rules', 'pt', 'style.xml']]
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in get_language('pt-BR').get_rule_file_names()]
    assert files == [['rules', 'pt', 'grammar.xml'], ['rules', 'pt', 'style.xml'], ['pt', 'pt-BR', 'grammar.xml'],
                     ['pt', 'pt-BR', 'style.xml']]
    assert isinstance(lang.get_default_spelling_rule(), MorfologikPortugueseSpellerCheck)
    assert isinstance(lang.get_multitoken_speller(), PortugueseMultitokenSpeller)


def test_typography():
    """Portuguese.getOpeningDoubleQuote() etc. (PortugalPortuguese overrides
    the double quotes) and isAdvancedTypographyEnabled()"""
    for code in ('pt', 'pt-BR', 'pt-AO', 'pt-MZ'):
        lang = get_language(code)
        assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
                lang.get_closing_single_quote()) == ('“', '”', '‘', '’')
        assert lang.is_advanced_typography_enabled()
    pt_pt = get_language('pt-PT')
    assert (pt_pt.get_opening_double_quote(), pt_pt.get_closing_double_quote(), pt_pt.get_opening_single_quote(),
            pt_pt.get_closing_single_quote()) == ('«', '»', '‘', '’')
    assert pt_pt.is_advanced_typography_enabled()
    assert pt_pt.to_advanced_typography('Use "isto" ou \'aquilo\'.') == 'Use «isto» ou ‘aquilo’.'
    assert get_language('pt-BR').to_advanced_typography('Use "isto".') == 'Use “isto”.'


def test_priorities():
    """Portuguese.getPriorityForId and PortugalPortuguese.getPriorityForId"""
    p = get_language('pt').get_priority_for_id
    assert p('MORFOLOGIK_RULE_PT_PT') == -50
    assert p('PT_SIMPLE_REPLACE_ORTHOGRAPHY_JA') == -49
    assert p('AI_PT_GGEC_REPLACEMENT_ORTHOGRAPHY_SPELL_X') == -48
    assert p('PT_MULTITOKEN_SPELLING_X') == -48
    assert p('AI_PT_GGEC_REPLACEMENT_OTHER') == -4
    assert p('ACENTUAÇÃO_VOGAL_ÊNCLISE_X') == -51
    assert p('COLOCACAO_PRONOMINAL_COM_ATRATOR_X') == -52
    assert p('FRAGMENT_TWO_ARTICLES') == 50
    assert p('VERB_COMMA_CONJUNCTION') == 10
    assert p('PT_COMPOUNDS_POST_REFORM') == -45
    assert p('PT_BR_SIMPLE_REPLACE') == -51
    assert p('TOO_LONG_SENTENCE') == -997
    assert p('TOO_LONG_PARAGRAPH') == -998
    assert p('READABILITY_RULE_DIFFICULT_PT') == -1101
    assert p('UNKNOWN_WORD') == -2000
    assert p('PORTUGUESE_OLD_SPELLING_INTERNAL') == 0
    assert p('AI_PT_HYDRA_LEO_MISSING_COMMA') == -51
    assert p('AI_PT_HYDRA_LEO_X') == -51
    assert p('SOME_STYLE_RULE') == -50
    assert p('OTHER') == 0
    for code in ('pt-BR', 'pt-AO', 'pt-MZ'):
        assert get_language(code).get_priority_for_id('PT_COMPOUNDS_POST_REFORM') == -45
    p = get_language('pt-PT').get_priority_for_id
    assert p('PT_COMPOUNDS_POST_REFORM') == 1
    assert p('PORTUGUESE_OLD_SPELLING_INTERNAL') == -9
    assert p('MORFOLOGIK_RULE_PT_PT') == -50
    assert p('PT_PT_SIMPLE_REPLACE') == -11


_PT_RULES = [
    'COMMA_PARENTHESIS_WHITESPACE', 'UNPAIRED_BRACKETS', 'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH',
    'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE', 'SENTENCE_WHITESPACE', 'WHITESPACE_PARAGRAPH',
    'WHITESPACE_PARAGRAPH_BEGIN', 'EMPTY_LINE', 'PARAGRAPH_REPEAT_BEGINNING_RULE', 'PUNCTUATION_PARAGRAPH_END',
    'PT_COMPOUNDS_POST_REFORM', 'PT_COLOUR_HYPHENATION', 'PT_SIMPLE_REPLACE_ORTHOGRAPHY', 'PT_SIMPLE_REPLACE',
    'PT_BARBARISMS_REPLACE', 'PT_CLICHE_REPLACE', 'FILLER_WORDS_PT', 'PT_REDUNDANCY_REPLACE', 'PT_WORDINESS_REPLACE',
    'PT_WIKIPEDIA_COMMON_ERRORS', 'PORTUGUESE_WORD_REPEAT_RULE', 'PORTUGUESE_WORD_REPEAT_BEGINNING_RULE',
    'ACCENTUATION_CHECK_PT', 'PT_DIACRITICS_REPLACE', 'PORTUGUESE_WRONG_WORD_IN_CONTEXT', 'PT_WORD_COHERENCY',
    'UNIDADES_METRICAS', 'READABILITY_RULE_SIMPLE_PT', 'READABILITY_RULE_DIFFICULT_PT', 'DOUBLE_PUNCTUATION',
    'PT_ENGLISH_CONTRACTION_ORTHOGRAPHY']


def test_relevant_rules():
    """Portuguese.getRelevantRules (without MorfologikPortugueseSpellerRule,
    spell checking, not ported) and the rules added by the variants"""
    rules = get_language('pt').get_relevant_rules(messages_for('pt'))
    assert [r.get_id() for r in rules] == _PT_RULES
    assert rules[0].incorrect_examples[0].example == 'Tomamos café<marker> ,</marker> queijo, bolachas e uvas.'
    assert rules[4].incorrect_examples[0].example == 'Esta casa é velha. <marker>foi</marker> construida em 1950.'
    assert rules[2].max_words == 50
    assert [type(r) for r in rules[29:31]] == [PortugueseReadabilityRule, PortugueseReadabilityRule]
    assert [r.too_easy_test for r in rules[29:31]] == [True, False]
    assert [r.path for r in rules[16:22] if hasattr(r, 'path')] == [
        '/pt/barbarisms.txt', '/pt/cliches.txt', '/pt/redundancies.txt', '/pt/wordiness.txt', '/pt/wikipedia.txt']
    pt_pt = get_language('pt-PT').get_relevant_rules(messages_for('pt'))
    assert [r.get_id() for r in pt_pt] == _PT_RULES + [
        'PT_COMPOUNDS_POST_REFORM', 'PT_POSAO_DASH_RULE', 'PT_AGREEMENT_REPLACE', 'PT_PT_SIMPLE_REPLACE',
        'PT_BARBARISMS_REPLACE', 'PT_ARCHAISMS_REPLACE', 'PT_CLICHE_REPLACE', 'PT_REDUNDANCY_REPLACE',
        'PT_WORDINESS_REPLACE', 'PT_WIKIPEDIA_COMMON_ERRORS']
    assert type(pt_pt[33]) is PostReformPortugueseCompoundRule and type(pt_pt[36]) is PortugalPortugueseReplaceRule
    assert [r.path for r in pt_pt[36:]] == [
        '/pt/pt-PT/replace.txt', '/pt/pt-PT/barbarisms.txt', '/pt/pt-PT/archaisms.txt', '/pt/pt-PT/cliches.txt',
        '/pt/pt-PT/redundancies.txt', '/pt/pt-PT/wordiness.txt', '/pt/pt-PT/wikipedia.txt']
    pt_br = get_language('pt-BR').get_relevant_rules(messages_for('pt'))
    assert [r.get_id() for r in pt_br] == _PT_RULES + [
        'PT_COMPOUNDS_POST_REFORM', 'PT_POSAO_DASH_RULE', 'PT_BR_SIMPLE_REPLACE', 'PT_BARBARISMS_REPLACE',
        'PT_ARCHAISMS_REPLACE', 'PT_CLICHE_REPLACE', 'PT_REDUNDANCY_REPLACE', 'PT_WORDINESS_REPLACE',
        'PT_WIKIPEDIA_COMMON_ERRORS']
    assert type(pt_br[35]) is BrazilianPortugueseReplaceRule
    assert [type(r) for r in pt_br[36:38]] == [PortugueseBarbarismsRule, PortugueseArchaismsRule]
    assert [r.path for r in pt_br[35:]] == [
        '/pt/pt-BR/replace.txt', '/pt/pt-BR/barbarisms.txt', '/pt/pt-BR/archaisms.txt', '/pt/pt-BR/cliches.txt',
        '/pt/pt-BR/redundancies.txt', '/pt/pt-BR/wordiness.txt', '/pt/pt-BR/wikipedia.txt']
    for code in ('pt-AO', 'pt-MZ'):
        rules = get_language(code).get_relevant_rules(messages_for('pt'))
        assert [r.get_id() for r in rules] == _PT_RULES + ['PT_COMPOUNDS_PRE_REFORM', 'PT_PREAO_DASH_RULE']
        assert type(rules[33]) is PreReformPortugueseCompoundRule
    for code in ('pt', 'pt-PT', 'pt-BR', 'pt-AO', 'pt-MZ'):
        get_language(code).get_pattern_rules()
        assert not unsupported_components(get_language(code))
