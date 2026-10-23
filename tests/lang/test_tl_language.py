"""Port of org.languagetool.rules.tl.TagalogTest (LanguageSpecificTest),
org.languagetool.language.tl.MorfologikTagalogSpellerRuleTest,
org.languagetool.rules.tl.LanguageSpecificSpellcheckerTest and
org.languagetool.tokenizers.tl.TagalogSRXSentenceTokenizerTest, plus checks
of the Tagalog language definition against org.languagetool.language.Tagalog,
TagalogTagger and TagalogWordTokenizer. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.tl.tokenizers import TagalogWordTokenizer
from langtool.messages import messages_for
from langtool.tagging import BaseTagger
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('tl')


def test_demo_text():
    """TagalogTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Ang LanguageTool ay maganda gamit sa araw-araw. Ang talatang ito ay nagpapakita ng ng kakayahan ng '
         'LanguageTool at hinahalimbawa kung paano ito gamitin. Litaw rin sa talatang ito na may mga bagaybagay na '
         'hindii pa kayang itama nng LanguageTool.')
    matches = JLanguageTool(get_language('tl')).check(s)
    # Java expects "ADJECTIVE-V_COMMON_NOUN", "NG_NG", "MORFOLOGIK_RULE_TL", "R_WORDS", "MORFOLOGIK_RULE_TL",
    # "MORFOLOGIK_RULE_TL", "MORFOLOGIK_RULE_TL"; MORFOLOGIK_RULE_TL is the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == ['ADJECTIVE-V_COMMON_NOUN', 'NG_NG', 'R_WORDS']


@pytest.mark.skip(reason='spell checking is not ported: MorfologikTagalogSpellerRuleTest tests '
                         'MorfologikTagalogSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.language.tl.MorfologikTagalogSpellerRuleTest"""


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.tl.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('tl')
    assert lang.code == 'tl-PH'
    assert get_language('tl-PH') is lang
    assert lang.name == 'Tagalog'
    assert lang.countries == ['PH']
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, TagalogWordTokenizer)


def test_word_tokenizer():
    """TagalogWordTokenizer: WordTokenizer that also splits at '-'"""
    tokenizer = TagalogWordTokenizer()
    assert tokenizer.get_tokenizing_characters() == WordTokenizer().get_tokenizing_characters() + '-'
    assert tokenizer.tokenize('gamit sa araw-araw.') == ['gamit', ' ', 'sa', ' ', 'araw', '-', 'araw', '.']
    assert tokenizer.tokenize('pinaka-prominanteng pinag--ugatang-') == [
        'pinaka', '-', 'prominanteng', ' ', 'pinag', '-', '-', 'ugatang', '-']
    # URLs and e-mail addresses are joined again (WordTokenizer.joinEMailsAndUrls)
    assert tokenizer.tokenize('Tingnan ang http://www.ex-ample.org/a-b at si foo-bar@ex-ample.org') == [
        'Tingnan', ' ', 'ang', ' ', 'http://www.ex-ample.org/a-b', ' ', 'at', ' ', 'si', ' ',
        'foo-bar@ex-ample.org']


def test_tagger():
    """TagalogTagger: BaseTagger for /tl/tagalog.dict"""
    tagger = get_language('tl-PH').tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    readings = tagger.tag(['Ang', 'maganda', 'araw', 'xyzzy'])
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in readings] == [
        [('ang', 'DECN NOM'), ('ang', 'NA')],
        [('maganda', 'ADMO S')],
        [('araw', 'NCOM 2')],
        [(None, None)]]


def test_relevant_rules():
    lang = get_language('tl-PH')
    rules = lang.get_relevant_rules(messages_for('tl'))
    # getRelevantRules without MorfologikTagalogSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE']
    assert rules[2].start_symbols == ['[', '(', '{', '"', "'"]
    assert rules[2].end_symbols == [']', ')', '}', '"', "'"]
    assert not unsupported_components(lang)


def test_tokenize():
    """TagalogSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('tl'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('Ang Linux ay isang operating system kernel para sa mga operating system na humahalintulad sa Unix. ',
               'Isa ang Linux sa mga pinaka-prominanteng halimbawa ng malayang software at pagsasagawa ng open source; '
               'madalas, malayang mapapalitan, gamitin, at maipamahagi ninuman ang '
               'lahat ng pinag-ugatang source code (pinagmulang kodigo).')
