"""Port of org.languagetool.rules.es.SpanishTest (LanguageSpecificTest) and
org.languagetool.JLanguageToolTest (language-es), plus checks of the
Spanish language definition against org.languagetool.language.Spanish and
SpanishVoseo. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.es.multitoken import SpanishMultitokenSpeller
from langtool.lang.es.rules import (CompoundRule, QuestionMarkRule, SimpleReplaceRule, SimpleReplaceVerbsRule,
                                    SpanishRepeatedWordsRule, SpanishUnpairedBracketsRule, SpanishWikipediaRule,
                                    SpanishWordRepeatBeginningRule, SpanishWordRepeatRule,
                                    SpanishWrongWordInContextRule)
from langtool.lang.es.spelling import MorfologikSpanishSpellerCheck
from langtool.lang.es.synthesis import SpanishSynthesizer
from langtool.lang.es.tagging import SpanishTagger
from langtool.lang.es.tokenizers import SpanishWordTokenizer
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('es')


# --- SpanishTest ---

def test_demo_text():
    """SpanishTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Escribe o pega tu texto aqui para tenerlo revisado contínuamente. los errores se subrayaran en '
         'diferentes colores: marcaremos los errores ortograficos en rojo; los errores de gramática son resaltado '
         'en amarillo; los problemas relacionados al estilo serán marcados en azul. Sabías que te proponemos '
         'sinónimos al hacer doble clic sobre una palabra? LanguageTool es un herramienta para textos impecables, '
         'sean e-mails, artículos, blogs o otros, incluso cuando el texto se complejice.')
    matches = JLanguageTool(get_language('es')).check(s)
    # Java expects two more matches of MORFOLOGIK_RULE_ES (for "contínuamente" after
    # ES_SIMPLE_REPLACE_SIMPLE_AQUI and "ortograficos" after SUBJUNTIVO_FUTURO), the spell checker, which
    # is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'ES_SIMPLE_REPLACE_SIMPLE_AQUI', 'UPPERCASE_SENTENCE_START', 'SUBJUNTIVO_FUTURO',
        'AGREEMENT_VERB_PARTICIPLE', 'RELACIONADO_A', 'ES_QUESTION_MARK', 'AGREEMENT_DET_NOUN', 'Y_E_O_U',
        'COMPLEJIZAR']


# --- JLanguageToolTest ---

def test_xml_rules():
    """JLanguageToolTest.testXMLRules. Java finds 4 matches, all of them of
    MORFOLOGIK_RULE_ES ("Busan", "Baek", "Seung", "Taek"), the spell checker,
    which is not ported."""
    tool = JLanguageTool(get_language('es'))
    matches = tool.check('Al cabo de 28 años, el vicealcalde de Busan, Baek Seung Taek, realiza una visita a Badajoz.')
    assert len(matches) == 0


@pytest.mark.parametrize('text,expected', [
    ('Helmut Khol', '[Helmut Kohl]'),
    ('Fredrik Willem de Klerk', '[Frederik Willem de Klerk]'),
    ('Maukalay Culkin', '[Macaulay Culkin]'),
    ('Dimitri Mendeléief', '[Dmitri Mendeléyev]'),
    ('Nikoláy Rimski-Kórsakov', '[Nikolái Rimski-Kórsakov]'),
    ('Luis Leante', '[]'),
    ('in vinos verita', '[in vino veritas]'),
    ('Marina Buisan', '[]'),
    ('Homos Sapiens', '[Homo sapiens]'),
    ('Garcia Horta', '[]'),
    ('Jon Benn', '[John Venn]'),
    ('josue garcia', '[]'),
    ('Franco more', '[]'),
    ('maria Lopez', '[]'),
    ('carlos fesi', '[]'),
    ('Johan Sebastián Bach', '[Johann Sebastian Bach]'),
    ('Johann Sebastián Bach', '[Johann Sebastian Bach]'),
    ('Plantation Boy', '[]'),
    ('Woodie Alen', '[Woody Allen]'),
    ('Eugenio Granjo', '[]'),
    ('Julia García', '[]'),
    ('Deustche Bank', '[Deutsche Bank]'),
    ('Caralp Mariné', '[]'),
    ('Andrew Cyrille', '[]'),
    ('Alejandro Varón', '[]'),
    ('Alejandro Mellado', '[]'),
    ('Alejandro Erazo', '[]'),
    ('Alberto Saoner', '[]'),
    ('è più', '[]'),
    ('Josep Maria Jové', '[]'),
    ('Josep Maria Canudas', '[]'),
    ('Francisco Javier Dra.', '[]'),
    ('the usage of our', '[]'),
    ('A sin', '[]'),
    ('A xente', '[]'),
    ('A lus', '[]'),
    ('A Month', '[]'),
    ('Jean-François Davy', '[]'),
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
def test_multitoken_speller(text, expected):
    """JLanguageToolTest.testMultitokenSpeller"""
    speller = get_language('es').get_multitoken_speller()
    assert '[' + ', '.join(speller.get_suggestions(text)) + ']' == expected


@pytest.mark.skip(reason='remote rules are not ported: JLanguageToolTest.testFilterRuleMatches tests '
                         'Spanish.filterRuleMatches, which only changes matches of the remote AI rules '
                         '(AI_ES_GGEC_*)')
def test_filter_rule_matches():
    """JLanguageToolTest.testFilterRuleMatches"""


# --- the language definition ---

def test_definition():
    lang = get_language('es')
    assert lang.code == 'es'
    assert lang.name == 'Spanish'
    assert lang.countries == ['ES', '', 'MX', 'GT', 'CR', 'PA', 'DO', 'VE', 'PE', 'AR', 'EC', 'CL', 'UY', 'PY',
                              'BO', 'SV', 'HN', 'NI', 'PR', 'US', 'CU']
    assert not lang.is_variant()
    voseo = get_language('es-AR')
    assert voseo.name == 'Spanish (voseo)' and voseo.countries == ['AR'] and voseo.is_variant()
    assert voseo.default_variant is lang
    assert voseo.get_default_disabled_rules_for_variant() == ['VOSEO']
    assert lang.get_default_disabled_rules_for_variant() == []
    assert isinstance(lang.tagger, SpanishTagger)
    assert isinstance(lang.synthesizer, SpanishSynthesizer)
    assert lang.synthesizer.number_speller is not None
    assert type(lang.word_tokenizer) is SpanishWordTokenizer
    # SpanishHybridDisambiguator: the chunkers for spelling_global.txt and es/multiwords.txt, then the
    # XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, MultiWordChunker, XmlRuleDisambiguator]
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'es', 'grammar.xml'], ['rules', 'es', 'style.xml']]
    assert isinstance(lang.get_default_spelling_rule(), MorfologikSpanishSpellerCheck)
    assert isinstance(lang.get_multitoken_speller(), SpanishMultitokenSpeller)


def test_typography():
    """Spanish.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    for code in ('es', 'es-AR'):
        lang = get_language(code)
        assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
                lang.get_closing_single_quote()) == ('«', '»', '‘', '’')
        assert lang.is_advanced_typography_enabled()
    assert get_language('es').to_advanced_typography('Use "esto" o \'aquello\'.') == 'Use «esto» o ‘aquello’.'


def test_priorities():
    """Spanish.getPriorityForId"""
    lang = get_language('es')
    p = lang.get_priority_for_id
    assert p('CONFUSIONS2') == 50
    assert p('RARE_WORDS') == 50
    assert p('MISSPELLING') == 40
    assert p('CONFUSIONS') == 40
    assert p('INCORRECT_EXPRESSIONS') == 40
    assert p('DIACRITICS') == 30
    assert p('ES_SIMPLE_REPLACE_SIMPLE_AQUI') == 30
    assert p('ES_COMPOUNDS') == 50
    assert p('ES_SIMPLE_REPLACE_MULTIWORDS') == 50
    assert p('NO_SEPARADO') == 40
    assert p('SE_CREO') == 35
    assert p('AGREEMENT_DET_NOUN') == 15
    assert p('SEPARADO') == 1
    assert p('ES_SPLIT_WORDS') == -10
    assert p('TOO_LONG_PARAGRAPH') == -15
    assert p('VOSEO') == -40
    assert p('REPETITIONS_STYLE') == -50
    assert p('MORFOLOGIK_RULE_ES') == -100
    assert p('SPANISH_WORD_REPEAT_RULE') == -150
    assert p('UPPERCASE_SENTENCE_START') == -200
    assert p('ES_QUESTION_MARK') == -250
    assert p('AI_ES_HYDRA_LEO_X') == -101
    assert p('AI_ES_GGEC_REPLACEMENT_OTHER') == -300
    assert p('AI_ES_GGEC_X') == 0
    assert p('ES_MULTITOKEN_SPELLING_TWO') == -95
    assert p('SOME_STYLE_RULE') == -50
    assert p('TOO_LONG_SENTENCE') == -101
    assert p('OTHER') == 0


def test_relevant_rules():
    lang = get_language('es')
    rules = lang.get_relevant_rules(messages_for('es'))
    # getRelevantRules without MorfologikSpanishSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'ES_UNPAIRED_BRACKETS', 'ES_QUESTION_MARK',
        'UPPERCASE_SENTENCE_START', 'SPANISH_WORD_REPEAT_RULE', 'WHITESPACE_RULE', 'ES_WIKIPEDIA_COMMON_ERRORS',
        'SPANISH_WRONG_WORD_IN_CONTEXT', 'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH', 'ES_SIMPLE_REPLACE_SIMPLE',
        'ES_SIMPLE_REPLACE_VERBS', 'SPANISH_WORD_REPEAT_BEGINNING_RULE', 'ES_COMPOUNDS', 'ES_REPEATEDWORDS']
    assert [type(r) for r in rules[2:4]] == [SpanishUnpairedBracketsRule, QuestionMarkRule]
    assert [type(r) for r in rules[5:9:2]] == [SpanishWordRepeatRule, SpanishWikipediaRule]
    assert type(rules[8]) is SpanishWrongWordInContextRule
    assert [type(r) for r in rules[11:]] == [SimpleReplaceRule, SimpleReplaceVerbsRule,
                                             SpanishWordRepeatBeginningRule, CompoundRule,
                                             SpanishRepeatedWordsRule]
    assert rules[9].max_words == 60
    assert rules[0].incorrect_examples[0].example == 'En su opinión<marker> ,</marker> no era verdad.'
    assert rules[4].incorrect_examples[0].example == 'Venta al público. <marker>ha</marker> subido mucho.'
    assert not unsupported_components(lang)
    assert not unsupported_components(get_language('es-AR'))
