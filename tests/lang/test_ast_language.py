"""Port of org.languagetool.rules.ast.AsturianTest (LanguageSpecificTest),
org.languagetool.language.rules.ast.MorfologikAsturianSpellerRuleTest,
org.languagetool.rules.ast.LanguageSpecificSpellcheckerTest and
org.languagetool.tokenizers.ast.AsturianSRXSentenceTokenizerTest, plus checks
of the Asturian language definition against org.languagetool.language.Asturian
and AsturianTagger. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.messages import messages_for
from langtool.tagging import BaseTagger
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ast')


def test_demo_text():
    """AsturianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Apega testu equí. o revisa toes les pallabres de esti testu pa ver dalgún de los problemis que '
         'LanguageTool ye pa deteutar. ¿Tas avecáu con los correutores gramaticales? Has date cuenta de que entá '
         'nun son perfeutos.')
    matches = JLanguageTool(get_language('ast')).check(s)
    # Java expects "MORFOLOGIK_RULE_AST", "UPPERCASE_SENTENCE_START", "TOU_CONTR", "PREPOS_APOSTR",
    # "MORFOLOGIK_RULE_AST", "MORFOLOGIK_RULE_AST", "MORFOLOGIK_RULE_AST", "CON_CONTR", "QUE_APOSTR";
    # MORFOLOGIK_RULE_AST is the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'UPPERCASE_SENTENCE_START', 'TOU_CONTR', 'PREPOS_APOSTR', 'CON_CONTR', 'QUE_APOSTR']


@pytest.mark.skip(reason='spell checking is not ported: MorfologikAsturianSpellerRuleTest tests '
                         'MorfologikAsturianSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.language.rules.ast.MorfologikAsturianSpellerRuleTest"""


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.ast.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('ast')
    assert lang.code == 'ast-ES'
    assert get_language('ast-ES') is lang
    assert lang.name == 'Asturian'
    assert lang.countries == ['ES']
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)


def test_tagger():
    """AsturianTagger: BaseTagger for /ast/asturian.dict"""
    tagger = get_language('ast-ES').tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    readings = tagger.tag(['Ye', 'llingua', 'romance', 'xyzzy'])
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in readings] == [
        [('ser', 'VSIP3S00'), ('ye', 'NCFSV000')],
        [('llingua', 'NCFSV000')],
        [('romance', 'NCMSV000')],
        [(None, None)]]


def test_relevant_rules():
    lang = get_language('ast-ES')
    rules = lang.get_relevant_rules(messages_for('ast'))
    # getRelevantRules without MorfologikAsturianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE']
    assert not unsupported_components(lang)


def test_tokenize():
    """AsturianSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('ast'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('De secute, los hackers de Minix aportaron idegues y códigu al núcleu Linux, y güey recibiera '
               'contribuciones de miles de programadores. ',
               "Torvalds sigue lliberando nueves versiones del núcleu, consolidando aportes d'otros programadores y "
               'faciendo cambios el mesmu.')
    stokenizer.set_single_line_breaks_marks_paragraph(False)
    test_split('De secute,\nlos hackers de Minix...')
    test_split('De secute,\n\n', 'los hackers de Minix...')
    stokenizer.set_single_line_breaks_marks_paragraph(True)
    test_split('De secute,\n', 'los hackers de Minix...')
    test_split('De secute,\n', '\n', 'los hackers de Minix...')
