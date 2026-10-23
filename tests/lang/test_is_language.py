"""Checks the Icelandic language definition against
org.languagetool.language.Icelandic (no Java test of its own)."""

from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.messages import messages_for
from langtool.tagging import DemoTagger


def test_definition():
    lang = get_language('is')
    assert lang.code == 'is-IS'
    assert get_language('is-IS') is lang
    assert lang.name == 'Icelandic'
    assert lang.countries == ['IS']
    assert isinstance(lang.tagger, DemoTagger)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert st.tokenize('Þetta er setning. Önnur setning.') == ['Þetta er setning. ', 'Önnur setning.']


def test_relevant_rules():
    lang = get_language('is-IS')
    rules = lang.get_relevant_rules(messages_for('is'))
    # getRelevantRules without HunspellNoSuggestionRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WORD_REPEAT_RULE', 'WHITESPACE_RULE']
    assert not unsupported_components(lang)


def test_check():
    from langtool.tool import JLanguageTool
    lt = JLanguageTool(get_language('is-IS'))
    matches = lt.check('Þetta er er setning.')
    assert [m.rule.get_id() for m in matches] == ['WORD_REPEAT_RULE']
