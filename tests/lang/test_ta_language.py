"""Port of org.languagetool.rules.ta.TamilTest (LanguageSpecificTest) plus
checks of the Tamil language definition against
org.languagetool.language.Tamil and TamilTagger. The language independent
parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py (which includes ta)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.messages import messages_for
from langtool.tagging import BaseTagger
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ta')


def test_demo_text():
    """TamilTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('இந்த பெட்டியில் உங்கள் உரையை ஒட்டி சரிவர சோதிக்கிறதா என பாருங்கள். \'லேங்குவேஜ் டூல்\' '
         'சில இலக்கணப் பிழைகளைச் சரியாக கண்டுபிடிக்கும். பல பிழைகளைப் பிடிக்க தடுமாறலாம்.')
    matches = JLanguageTool(get_language('ta')).check(s)
    assert [m.get_specific_rule_id() for m in matches] == [
        'Ends_in_A_1', 'Ends_in_A_3', 'Ends_in_A_3', 'Ends_in_A_4', 'Ends_in_A_2']


def test_definition():
    lang = get_language('ta')
    assert lang.code == 'ta-IN'
    assert get_language('ta-IN') is lang
    assert lang.name == 'Tamil'
    assert lang.countries == ['IN']
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert st.tokenize('இந்த பெட்டியில். பல பிழைகளைப்.') == ['இந்த பெட்டியில். ', 'பல பிழைகளைப்.']


def test_tagger():
    """TamilTagger: BaseTagger for /ta/tamil.dict"""
    tagger = get_language('ta-IN').tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    readings = tagger.tag(['யானைகளை', 'அவன்', 'நல்ல', 'பெட்டியில்'])
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in readings] == [
        [('யானை', 'NNSA-S')], [('அவன்', 'NNPUM')], [('நல்ல', 'ADJ')], [(None, None)]]  # unknown word


def test_relevant_rules():
    lang = get_language('ta-IN')
    rules = lang.get_relevant_rules(messages_for('ta'))
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'WHITESPACE_RULE',
                                          'TOO_LONG_SENTENCE', 'SENTENCE_WHITESPACE']
    assert rules[3].max_words == 50
    assert not unsupported_components(lang)


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'prohibit.txt/spelling.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.ta.LanguageSpecificSpellcheckerTest"""
