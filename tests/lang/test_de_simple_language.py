"""Port of org.languagetool.rules.de.SimpleGermanTest (LanguageSpecificTest;
the language independent parts of runTests are ported in
tests/test_jlanguagetool.py, which also runs them for
de-DE-x-simple-language), plus checks of the language definition against
org.languagetool.language.SimpleGerman."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, unsupported_components
from langtool.lang.de.chunking import GermanChunker
from langtool.lang.de.style_rules import LongSentenceRule
from langtool.messages import messages_for
from langtool.tool import JLanguageTool, LEVEL_PICKY

CODE = 'de-DE-x-simple-language'

# NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
DEMO_TEXT = ('Fügen Sie hier Ihren Text ein oder benutzen Sie diesen Text als Beispiel. Dieser Text wurde nur zum '
             'Testen geschrieben. Die Donaudampfschifffahrt darf da nicht fehlen. Und die Nutzung des Genitivs auch '
             'nicht.')


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


def test_language():
    """SimpleGermanTest.testLanguage (testDemoText)"""
    matches = JLanguageTool(get_language(CODE)).check(DEMO_TEXT)
    assert [m.get_specific_rule_id() for m in matches] == [
        'ZWEI_INFORMATIONSEINHEITEN_PRO_SATZ',  # "TOO_LONG_SENTENCE_DE" -- filtered due to overlapping other errors
        'PASSIV', 'LANGES_WORT', 'VERNEINUNG', 'ABSTRAKTE_WOERTER', 'GENITIV']


def test_long_sentence_rule_examples():
    """LanguageSpecificTest.testJavaRules for SimpleGerman's only Java rule
    (the examples of org.languagetool.rules.de.LongSentenceRule)"""
    lang = get_language(CODE)
    lt = JLanguageTool(lang)
    java_rules = [r for r in lt.get_all_rules() if isinstance(r, LongSentenceRule)]
    assert len(java_rules) == 1
    rule = java_rules[0]
    rule.tags = [t for t in rule.tags if t != 'picky']  # make sure "picky" rules also run
    for r in lt.get_all_rules():
        lt.disable_rule(r.get_id())
    lt.enable_rule(rule.get_id())
    for ex in rule.correct_examples:
        assert lt.check(ex.example.replace('<marker>', '').replace('</marker>', '')) == []
    for ex in rule.incorrect_examples:
        assert len(lt.check(ex.example.replace('<marker>', '').replace('</marker>', ''))) == 1


def test_long_sentence_rule_12_words():
    """SimpleGerman.getRelevantRules: LongSentenceRule(messages, userConfig, 12)"""
    lt = JLanguageTool(get_language(CODE))
    for r in lt.get_all_rules():
        lt.disable_rule(r.get_id())
    lt.enable_rule('TOO_LONG_SENTENCE_DE')
    # (a picky rule)
    assert lt.check('Eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn.') == []
    assert lt.check('Eins zwei drei vier fünf sechs sieben acht neun zehn elf.', level=LEVEL_PICKY) == []
    matches = lt.check('Eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn.', level=LEVEL_PICKY)
    assert [m.rule.get_id() for m in matches] == ['TOO_LONG_SENTENCE_DE']


def test_definition():
    """SimpleGerman (extends GermanyGerman): name, code, countries,
    isVariant, the inherited components, rules, rule files, priorities"""
    lang = get_language(CODE)
    assert lang.name == 'Simple German'
    assert lang.short_code == CODE and lang.code == CODE
    assert lang.countries == ['DE']
    assert lang.is_variant()
    assert isinstance(lang.sentence_tokenizer, SRXSentenceTokenizer)
    assert lang.sentence_tokenizer.tokenize('Das ist z. B. ein Satz. Und noch einer.') == \
        get_language('de-DE').sentence_tokenizer.tokenize('Das ist z. B. ein Satz. Und noch einer.')
    assert isinstance(lang.post_disambiguation_chunker, GermanChunker)
    assert [lang._quote(i) for i in range(4)] == ['„', '“', '‚', '‘']
    assert lang.is_advanced_typography_enabled()
    assert lang.to_advanced_typography('z.B.') == 'z.\u00a0B.'
    assert lang.get_multitoken_speller() is get_language('de-DE').get_multitoken_speller()
    # getRuleFileNames: only the rules of de-DE-x-simple-language/grammar.xml
    files = [f.replace('\\', '/') for f in lang.get_rule_file_names()]
    assert len(files) == 1 and files[0].endswith('/rules/de-DE-x-simple-language/grammar.xml')
    # getRelevantRules: only the German LongSentenceRule, no language model (capable) rules
    rules = lang.get_relevant_rules(messages_for('de'))
    assert [(type(r), r.get_id(), r.max_words) for r in rules] == [(LongSentenceRule, 'TOO_LONG_SENTENCE_DE', 12)]
    # getPriorityForId
    assert lang.get_priority_for_id('TOO_LONG_SENTENCE') == 10
    assert lang.get_priority_for_id('LANGES_WORT') == -1
    de = get_language('de-DE')
    for id in ('DE_PROHIBITED_COMPOUNDS_X', 'CONFUSION_RULE_X', 'AI_DE_HYDRA_LEO_CP_X', 'SOME_STYLE_RULE',
               'TOO_LONG_SENTENCE_DE', 'FOO'):
        assert lang.get_priority_for_id(id) == de.get_priority_for_id(id)


def test_disambiguator():
    """SimpleGerman.createDefaultDisambiguator: GermanRuleDisambiguator with
    the XmlRuleDisambiguator of GermanyGerman"""
    lang = get_language(CODE)
    de = get_language('de-DE')
    text = 'Das ist ein Haus, das ich gerne sehe.'
    simple_sentence = JLanguageTool(lang).get_analyzed_sentence(text)
    de_sentence = JLanguageTool(de).get_analyzed_sentence(text)
    assert str(simple_sentence) == str(de_sentence)


def test_all_components_supported():
    """All the components referenced by the definition are ported"""
    lang = get_language(CODE)
    JLanguageTool(lang).check('Ein Test, der keine Fehler geben sollte.')
    assert lang.tagger and lang.synthesizer and lang.disambiguator
    assert not unsupported_components(lang)
