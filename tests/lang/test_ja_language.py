"""Port of org.languagetool.rules.ja.JapaneseTest (LanguageSpecificTest),
org.languagetool.JLanguageToolTest (of the Japanese module) and
org.languagetool.rules.ja.LanguageSpecificSpellcheckerTest, plus checks of
the Japanese language definition against org.languagetool.language.Japanese.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import os

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ja.tagging import JapaneseTagger
from langtool.lang.ja.tokenizers import JapaneseWordTokenizer
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ja')


def test_language():
    """JapaneseTest.testLanguage: the demo text test is commented out in Java,
    runTests is in tests/test_jlanguagetool.py"""
    assert get_language('ja').name == 'Japanese'


def test_japanese():
    """JLanguageToolTest.testJapanese"""
    tool = JLanguageTool(get_language('ja'))
    assert len(tool.check('エラーを含まないテスト文です。')) == 0
    assert len(tool.check('エラーお含むテスト文です。')) == 1


def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.ja.LanguageSpecificSpellcheckerTest
    (SpellcheckerTest.runLanguageSpecificTest for Japanese): no word may be
    both in ja/hunspell/prohibit.txt and ja/hunspell/spelling.txt (Japanese
    has neither file, so both lists are empty, as in Java)"""
    lang = get_language('ja')

    def load_words(name):
        path = lang.resource_path(name)
        if not os.path.exists(path):
            return []
        with open(path, encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    prohibited = load_words('ja/hunspell/prohibit.txt')
    spelling = load_words('ja/hunspell/spelling.txt')
    assert not set(prohibited) & set(spelling)


def test_definition():
    lang = get_language('ja')
    assert lang.code == 'ja-JP'
    assert get_language('ja-JP') is lang
    assert lang.name == 'Japanese'
    assert lang.countries == ['JP']
    assert lang.synthesizer is None
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, JapaneseWordTokenizer)
    assert isinstance(lang.tagger, JapaneseTagger)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['ja', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('ja')
    rules = lang.get_relevant_rules(messages_for('ja'))
    assert [r.get_id() for r in rules] == ['DOUBLE_PUNCTUATION', 'WHITESPACE_RULE']
    assert not unsupported_components(lang)


def test_analyzed_sentence():
    """JLanguageTool with JapaneseWordTokenizer and JapaneseTagger: as in Java,
    the whitespace is not part of the tokens, so the positions of the tokens
    after whitespace (and of rule matches) do not count it"""
    lt = JLanguageTool(get_language('ja'))
    sentence, = lt.analyze_text('これは ペン です。')
    assert ' '.join('%d:%s' % (t.start_pos, t) for t in sentence.tokens) == (
        '0:[/SENT_START*] 0:これ[これ/名詞-代名詞-一般*] 2:は[は/助詞-係助詞*] 3:ペン[ペン/名詞-一般*] '
        '5:です[です/助動詞*] 7:。[。/記号-句点*,。/SENT_END*,。/PARA_END*]')
    m, = lt.check('  エラー お含むテスト文です。')
    assert (m.rule.get_id(), m.from_pos, m.to_pos, m.suggested_replacements) == ('O', 0, 4, ['名詞を'])
