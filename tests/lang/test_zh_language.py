"""Port of org.languagetool.rules.zh.ChineseTest (LanguageSpecificTest) and
org.languagetool.rules.zh.LanguageSpecificSpellcheckerTest, plus checks of
the Chinese language definition against org.languagetool.language.Chinese.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import os

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import unsupported_components
from langtool.lang.zh.tagging import ChineseTagger
from langtool.lang.zh.tokenizers import ChineseSentenceTokenizer, ChineseWordTokenizer
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('zh')


def test_demo_text():
    """ChineseTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = '将文本粘贴在此，或者检测以下文本：我和她去看了二部电影。'
    matches = JLanguageTool(get_language('zh-CN')).check(s)
    assert [m.get_specific_rule_id() for m in matches] == ['wa5']
    assert [(m.from_pos, m.to_pos, m.suggested_replacements) for m in matches] == [(23, 25, ['两部'])]


def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.zh.LanguageSpecificSpellcheckerTest
    (SpellcheckerTest.runLanguageSpecificTest for Chinese): no word may be
    both in zh/hunspell/prohibit.txt and zh/hunspell/spelling.txt (Chinese
    has neither file, so both lists are empty, as in Java)"""
    lang = get_language('zh')

    def load_words(name):
        path = lang.resource_path(name)
        if not os.path.exists(path):
            return []
        with open(path, encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    prohibited = load_words('zh/hunspell/prohibit.txt')
    spelling = load_words('zh/hunspell/spelling.txt')
    assert not set(prohibited) & set(spelling)


def test_definition():
    lang = get_language('zh')
    assert lang.code == 'zh-CN'
    assert get_language('zh-CN') is lang
    assert lang.name == 'Chinese'
    assert lang.countries == ['CN']
    assert lang.synthesizer is None
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    assert isinstance(lang.sentence_tokenizer, ChineseSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, ChineseWordTokenizer)
    assert isinstance(lang.tagger, ChineseTagger)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['zh', 'grammar.xml']]


def test_relevant_rules():
    """Chinese.getRelevantRules (getRelevantLanguageModelRules with
    ChineseConfusionProbabilityRule is not ported: language model rule)"""
    lang = get_language('zh')
    rules = lang.get_relevant_rules(messages_for('zh'))
    assert [r.get_id() for r in rules] == ['DOUBLE_PUNCTUATION', 'WHITESPACE_RULE']
    assert not unsupported_components(lang)


def test_analyzed_sentence():
    """JLanguageTool with ChineseSentenceTokenizer, ChineseWordTokenizer and
    ChineseTagger: whitespace is a sentence of its own, the tokens are the
    words with their natures as POS tags (positions checked against Java)"""
    lt = JLanguageTool(get_language('zh'))
    sentences = lt.analyze_text('我和她去看了二部电影。 你好')
    assert [s.text for s in sentences] == ['我和她去看了二部电影。', ' ', '你好']
    assert ' '.join('%d:%s' % (t.start_pos, t) for t in sentences[0].tokens) == (
        '0:[/SENT_START*] 0:我[我/r*] 1:和[和/c*] 2:她[她/r*] 3:去[去/v*] 4:看[看/v*] 5:了[了/ul*] 6:二[二/m*] '
        '7:部[部/q*] 8:电影[电影/n*] 10:。[。/w*,。/SENT_END*]')
    m1, m2 = lt.check('我和她去看了二部电影。 我和她去看了二部电影。')
    assert [(m.get_specific_rule_id(), m.from_pos, m.to_pos) for m in (m1, m2)] == [('wa5', 6, 8), ('wa5', 18, 20)]
