"""Port of org.languagetool.rules.el.GreekTest (LanguageSpecificTest) and
org.languagetool.rules.el.LanguageSpecificSpellcheckerTest, plus checks of
the Greek language definition against org.languagetool.language.Greek, of
GreekTagger (with the GreekAnalyzer of org.ioperm:morphology-el) and
GreekWordTokenizer. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py
(its WordListValidatorTest, with the additional characters "ισότπς",
checks the spelling word lists, which are not ported)."""

import os
import zipfile

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.el.rules import (GreekRedundancyRule, GreekSpecificCaseRule, GreekWordRepeatBeginningRule,
                                    NumeralStressRule, ReplaceHomonymsRule)
from langtool.lang.el.tagging import GreekAnalyzer, GreekTagger, _to_lower
from langtool.lang.el.tokenizers import GreekWordTokenizer
from langtool.messages import messages_for
from langtool.synthesis import BaseSynthesizer
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('el')


# --- GreekTest ---

def test_demo_text():
    """GreekTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Επικολλήστε το κείμενο σας εδώ και κάντε κλικ στο κουμπί ελέγχου. Κάντε κλικ στις χρωματιστές φράσεις '
         'για λεπτομέρειες σχετικά με πιθανά σφάλματα. Για παράδειγμα σε αυτή τη πρόταση υπάρχουν εσκεμμένα λάθη '
         'για να να δείτε πώς λειτουργει το LanguageTool..')
    matches = JLanguageTool(get_language('el')).check(s)
    # Java expects "GREEK_PUNC_2", "GREEK_ART_FEM_MISSING_N", "WORD_REPEAT_RULE", "MORFOLOGIK_RULE_EL_GR",
    # "DOUBLE_PUNCTUATION"; MORFOLOGIK_RULE_EL_GR (for "λειτουργει") is the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == ['GREEK_PUNC_2', 'GREEK_ART_FEM_MISSING_N',
                                                           'WORD_REPEAT_RULE', 'DOUBLE_PUNCTUATION']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists (MorfologikGreekSpellerRule)')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.el.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('el')
    assert lang.code == 'el-GR'
    assert get_language('el-GR') is lang
    assert lang.name == 'Greek'
    assert lang.countries == ['GR']
    assert isinstance(lang.tagger, GreekTagger)
    assert lang.tagger.tag_lowercase_with_uppercase
    # GreekSynthesizer is a plain BaseSynthesizer
    assert type(lang.synthesizer) is BaseSynthesizer
    assert lang.synthesizer.get_possible_tags() == ['V', 'INF', 'PARTICLE']
    assert lang.synthesizer.lookup('έχω', 'V')[:3] == ['έχω', 'έχει', 'έχεις']
    assert type(lang.word_tokenizer) is GreekWordTokenizer
    stages = lang.disambiguator.stages
    assert len(stages) == 1 and isinstance(stages[0], XmlRuleDisambiguator)
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['el', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('el')
    rules = lang.get_relevant_rules(messages_for('el'))
    # getRelevantRules without MorfologikGreekSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'EL_UNPAIRED_BRACKETS', 'TOO_LONG_SENTENCE',
        'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE', 'GREEK_WORD_REPEAT_BEGINNING_RULE', 'WORD_REPEAT_RULE',
        'GREEK_HOMONYMS_REPLACE', 'EL_SPECIFIC_CASE', 'GREEK_ORTHOGRAPHY_NUMERAL_STRESS', 'EL_REDUNDANCY_REPLACE']
    comma, brackets, long_sentence, upper = rules[0], rules[2], rules[3], rules[4]
    assert [(e.example, e.corrections) for e in comma.incorrect_examples] == [
        ('Το κόμμα χωρίζει προτάσεις<marker> ,</marker> όρους προτάσεων και φράσεις.', [','])]
    assert [e.example for e in comma.correct_examples] == [
        'Το κόμμα χωρίζει προτάσεις<marker>,</marker> όρους προτάσεων και φράσεις.']
    assert brackets.start_symbols == ['[', '(', '{', '“', '"', '«']
    assert brackets.end_symbols == [']', ')', '}', '”', '"', '»']
    assert long_sentence.max_words == 50
    assert [(e.example, e.corrections) for e in upper.incorrect_examples] == [
        ('Η τελεία είναι σημείο στίξης. <marker>δείχνει</marker> το τέλος μίας πρότασης.', ['Δείχνει'])]
    assert [e.example for e in upper.correct_examples] == [
        'Η τελεία είναι σημείο στίξης. <marker>Δείχνει</marker> το τέλος μίας πρότασης.']
    assert [type(r) for r in rules[6:]] == [GreekWordRepeatBeginningRule, type(rules[7]), ReplaceHomonymsRule,
                                            GreekSpecificCaseRule, NumeralStressRule, GreekRedundancyRule]
    assert not unsupported_components(lang)


def test_priorities():
    """Greek does not override getPriorityForId"""
    lang = get_language('el')
    for rule_id in ('GREEK_HOMONYMS_REPLACE', 'EL_REDUNDANCY_REPLACE', 'GREEK_PUNC_2'):
        assert lang.get_priority_for_id(rule_id) == 0


# --- GreekTagger ---

def _tags(tagger, word):
    r, = tagger.tag([word])
    return [(t.lemma, t.pos_tag) for t in r.readings]


def test_tagger():
    tagger = get_language('el').tagger
    # greek.dict (and added.txt)
    assert _tags(tagger, 'έχει') == [('έχω', 'V')]
    assert _tags(tagger, 'να') == [('να', 'PARTICLE')]
    # words that are not in greek.dict: GreekAnalyzer (as checked with Java)
    assert _tags(tagger, 'αγωγός') == [('αγωγός', 'N:MASC:SG:NOM')]
    assert _tags(tagger, 'ανταγωνισμό') == [('ανταγωνισμός', 'N:MASC:SG:ACC')]
    assert _tags(tagger, 'ήττα') == [('ήττα', 'N:FEM:SG:ACC'), ('ήττα', 'N:FEM:SG:NOM'), ('ήττα', 'N:FEM:SG:VOC')]
    assert _tags(tagger, 'αθλητισμέ') == [('αθλητισμός', 'N:MASC:SG:VOC')]
    # GreekAnalyzer.getLemma(word, false): no lowercase lookup
    assert _tags(tagger, 'Έδρας') == [(None, None)]
    assert _tags(tagger, 'ΕΔΡΑΣ') == [(None, None)]
    assert _tags(tagger, 'κείμενο') == [(None, None)]
    readings = tagger.tag(['Ο', ' ', 'αγωγός'])
    assert [r.start_pos for r in readings] == [0, 1, 2]


def test_greek_analyzer():
    """org.ioperm.morphology.el.GreekAnalyzer.getLemma and CharUtils.toLower"""
    analyzer = GreekAnalyzer(get_language('el').dictionary('el/analysis.dict'))
    assert analyzer.get_lemma('έδρας', False) == [('έδρα', 'N:FEM:SG:GEN')]
    assert analyzer.get_lemma('Έδρας', False) == []
    assert analyzer.get_lemma('Έδρας', True) == [('έδρα', 'N:FEM:SG:GEN')]
    assert analyzer.get_lemma('έδρας', True) == [('έδρα', 'N:FEM:SG:GEN')]
    assert analyzer.get_lemma('ΈΔΡΑΣ', True) == []
    assert analyzer.get_lemma('', True) == []
    assert _to_lower('Σ', True) == 'ς' and _to_lower('Σ', False) == 'σ'
    assert _to_lower('Ώ', False) == 'ώ' and _to_lower('Ϋ', False) == 'ϋ'
    assert _to_lower('A', False) == 'A' and _to_lower('ά', False) == 'ά'


def test_analyzer_dictionary_in_jar(tmp_path, monkeypatch):
    """el/analysis.dict is found in the morphology-el jar (at the jar path
    of the dictionary manifest) when given as a dictionary path, e.g. in the
    libs directory of a LanguageTool installation"""
    from langtool.dictionaries import locate
    lang = get_language('el')
    src = lang.dictionary('el/analysis.dict').path
    jar = tmp_path / 'libs' / 'morphology-el.jar'
    jar.parent.mkdir()
    with zipfile.ZipFile(jar, 'w') as z:
        z.write(src, 'org/ioperm/morphology/el/analysis.dict')
        z.write(os.path.splitext(src)[0] + '.info', 'org/ioperm/morphology/el/analysis.info')
    monkeypatch.setenv('LANGTOOL_CACHE_DIR', str(tmp_path / 'cache'))
    p = locate('el/analysis.dict', str(tmp_path), download=False)
    assert p.startswith(str(tmp_path / 'cache'))
    with open(p, 'rb') as f, open(src, 'rb') as f2:
        assert f.read() == f2.read()
    assert os.path.exists(os.path.splitext(p)[0] + '.info')


# --- GreekWordTokenizer ---

def test_word_tokenizer():
    t = GreekWordTokenizer()
    assert t.tokenize('') == []
    assert t.tokenize('Κάντε κλικ στο κουμπί ελέγχου.') == [
        'Κάντε', ' ', 'κλικ', ' ', 'στο', ' ', 'κουμπί', ' ', 'ελέγχου', '.']
    # "ό,τι" is a token (lowercase only), also at the beginning of a longer word (as checked with Java)
    assert t.tokenize('Ό,τι θέλεις, ό,τιδήποτε!') == [
        'Ό', ',', 'τι', ' ', 'θέλεις', ',', ' ', 'ό,τι', 'δήποτε', '!']
    assert t.tokenize('xό,τι') == ['xό', ',', 'τι']
    assert t.tokenize('«τέλος»\u0387 κ.λπ. 3,5 1.000 a\\b x/y') == [
        '«', 'τέλος', '»', '\u0387', ' ', 'κ', '.', 'λπ', '.', ' ', '3', ',', '5', ' ', '1', '.', '000', ' ', 'a', '\\',
        'b', ' ', 'x', '/', 'y']
    # the ano teleia is a delimiter, the middle dot is not (as checked with Java)
    assert t.tokenize('x\u0387y x\u00b7y') == ['x', '\u0387', 'y', ' ', 'x\u00b7y']
    # hyphens, question marks etc. are not delimiters, carriage return neither
    assert t.tokenize('e-mail; τι;? α-β\r\nγ\tδ') == [
        'e-mail', ';', ' ', 'τι', ';', '?', ' ', 'α-β\r', '\n', 'γ', '\t', 'δ']
    assert t.tokenize('a\u00a0b\u200bc\ufeffd') == ['a', '\u00a0', 'b', '\u200b', 'c', '\ufeff', 'd']
    # joinEMailsAndUrls
    assert t.tokenize('e-mail: test@example.com http://www.example.com/a?b=c') == [
        'e-mail', ':', ' ', 'test@example.com', ' ', 'http://www.example.com/a?b=c']
