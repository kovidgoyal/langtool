"""Port of org.languagetool.rules.km.KhmerTest (LanguageSpecificTest),
org.languagetool.rules.km.KhmerSpaceBeforeRuleTest,
org.languagetool.rules.km.KhmerWordRepeatRuleTest and
org.languagetool.rules.km.LanguageSpecificSpellcheckerTest, plus checks of
the Khmer language definition against org.languagetool.language.Khmer,
KhmerTagger, KhmerWordTokenizer, KhmerSimpleReplaceRule and
KhmerUnpairedBracketsRule. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.km.rules import (KhmerSimpleReplaceRule, KhmerSpaceBeforeRule, KhmerUnpairedBracketsRule,
                                    KhmerWordRepeatRule)
from langtool.lang.km.tokenizers import KhmerWordTokenizer
from langtool.messages import messages_for
from langtool.tagging import BaseTagger
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('km')


# --- KhmerTest ---

def test_demo_text():
    """KhmerTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('ឃ្លា​នេះ​បង្ហាញ​ពី​ពី​កំហុស​វេយ្យាករណ៍ ដើម្បី​បញ្ជាក់​ពី'
         '​ប្រសិទ្ធភាព​របស់​កម្មវិធី LanguageTool សំរាប់​ភាសាខ្មែរ។')
    matches = JLanguageTool(get_language('km')).check(s)
    # Java expects "KM_WORD_REPEAT_RULE", 5 x "HUNSPELL_RULE", "KM_SIMPLE_REPLACE"; HUNSPELL_RULE
    # (KhmerHunspellRule) is the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == ['KM_WORD_REPEAT_RULE', 'KM_SIMPLE_REPLACE']
    m = matches[1]
    assert (m.from_pos, m.to_pos) == (96, 102)
    assert m.suggested_replacements == ['សម្រាប់']
    assert m.message == ' Consider following the spelling of Chuon Nath '
    assert m.short_message == 'Consider following the spelling of Chuon Nath'


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists (KhmerHunspellRule)')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.km.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('km')
    assert lang.code == 'km-KH'
    assert get_language('km-KH') is lang
    assert lang.name == 'Khmer'
    assert lang.countries == ['KH']
    assert lang.synthesizer is None
    assert lang.definition['disambiguator'] == [('xml', False)]
    stages = lang.disambiguator.stages
    assert len(stages) == 1 and isinstance(stages[0], XmlRuleDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert isinstance(lang.word_tokenizer, KhmerWordTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['km', 'grammar.xml']]


def test_tagger():
    """KhmerTagger: BaseTagger for /km/khmer.dict"""
    tagger = get_language('km').tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    readings = tagger.tag(['ពី', 'និង', 'xyzzy'])
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in readings] == [
        [('ពី', 'IN')],
        [('និង', 'IN'), ('និង', 'CC')],
        [(None, None)]]


def test_relevant_rules():
    lang = get_language('km')
    rules = lang.get_relevant_rules(messages_for('km'))
    # getRelevantRules without KhmerHunspellRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['KM_SIMPLE_REPLACE', 'KM_WORD_REPEAT_RULE', 'KM_UNPAIRED_BRACKETS',
                                           'KM_SPACE_BEFORE_CONJUNCTION']
    assert [type(r) for r in rules] == [KhmerSimpleReplaceRule, KhmerWordRepeatRule, KhmerUnpairedBracketsRule,
                                        KhmerSpaceBeforeRule]
    assert not unsupported_components(lang)


# --- KhmerWordTokenizer ---

def test_word_tokenizer():
    """KhmerWordTokenizer: a StringTokenizer that returns the delimiters, then
    joinEMailsAndUrls"""
    tokenizer = KhmerWordTokenizer()
    # zero width space (U+200B) and khan (U+17D4) are delimiters
    assert tokenizer.tokenize('ខ្ញុំ​និង​គាត់។') == [
        'ខ្ញុំ', '​', 'និង', '​', 'គាត់', '។']
    # not delimiters (unlike the default WordTokenizer): '-', '\r', U+17D5 is, U+17DA is not
    assert tokenizer.tokenize('a-b c\r«d»៕e៚') == ['a-b', ' ', 'c\r', '«', 'd', '»', '៕', 'e៚']
    assert tokenizer.tokenize('x@example.com http://x.org/a') == ['x@example.com', ' ', 'http://x.org/a']
    assert tokenizer.tokenize('') == []


# --- KhmerSpaceBeforeRuleTest ---

def test_space_before_rule():
    """KhmerSpaceBeforeRuleTest.testSpaceBeforeRule"""
    language = get_language('km')
    rule = KhmerSpaceBeforeRule(messages_for('en'), language)
    lt = JLanguageTool(language)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('គាត់​បាន​ទៅ ដើម្បី​ទិញ​ម្ហូប។'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('ខ្ញុំ និង​គាត់។'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('គាត់​ចង់​បាន ពីព្រោះ​គាត់​អត់​មាន។'))) == 0

    # incorrect sentences:
    assert len(rule.match(lt.get_analyzed_sentence('គាត់​បាន​ទៅ​ដើម្បី​ទិញ​ម្ហូប។'))) == 1
    assert len(rule.match(lt.get_analyzed_sentence('ខ្ញុំ​និង​គាត់។'))) == 1
    assert len(rule.match(lt.get_analyzed_sentence('គាត់​ចង់​បាន​ពីព្រោះ​គាត់​អត់​មាន។'))) == 1


def test_space_before_rule_properties():
    language = get_language('km')
    rule = KhmerSpaceBeforeRule(messages_for('en'), language)
    assert rule.get_id() == 'KM_SPACE_BEFORE_CONJUNCTION'
    m, = rule.match(JLanguageTool(language).get_analyzed_sentence('ខ្ញុំ​និង​គាត់។'))
    assert (m.from_pos, m.to_pos) == (6, 9)
    assert m.suggested_replacements == [' និង']
    assert m.message == 'Missing white space before conjunction'


# --- KhmerWordRepeatRuleTest ---

def test_word_repeat_rule():
    """KhmerWordRepeatRuleTest.testWordRepeatRule"""
    language = get_language('km')
    rule = KhmerWordRepeatRule(messages_for('en'), language)
    lt = JLanguageTool(language)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('នេះ​ហើយៗ​នោះ។'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('គាត់​ហើយ ហើយ​ខ្ញុំ។'))) == 0

    # incorrect sentences:
    assert len(rule.match(lt.get_analyzed_sentence('នេះ​ហើយ​ហើយ​នោះ។'))) == 1
    assert len(rule.match(lt.get_analyzed_sentence('ខ្ញុំ​និង​និង​គាត់។'))) == 1


def test_word_repeat_rule_properties():
    language = get_language('km')
    rule = KhmerWordRepeatRule(messages_for('en'), language)
    assert rule.get_id() == 'KM_WORD_REPEAT_RULE'
    assert rule.category.id == 'MISC'
    assert rule.loc_quality_issue_type == 'Uncategorized'
    m, = rule.match(JLanguageTool(language).get_analyzed_sentence('នេះ​ហើយ​ហើយ​នោះ។'))
    assert (m.from_pos, m.to_pos) == (4, 11)
    assert m.suggested_replacements == ['ហើយ ហើយ', 'ហើយ', 'ហើយៗ']
    assert m.message == 'Possible typo: you repeated a word.'
    assert m.short_message == 'Word repetition'
    # single non-letter characters are not words
    assert rule.match(JLanguageTool(language).get_analyzed_sentence('a​-​-​b')) == []


# --- KhmerSimpleReplaceRule, KhmerUnpairedBracketsRule ---

def test_simple_replace_rule_properties():
    rule = KhmerSimpleReplaceRule(messages_for('km'), get_language('km'))
    assert rule.get_id() == 'KM_SIMPLE_REPLACE'
    assert rule.get_description() == 'Words or groups of words that are incorrect or obsolete'
    assert rule.category.id == 'MISC'
    assert rule.get_suggestions_separator() == ' or '


def test_unpaired_brackets_rule():
    language = get_language('km')
    rule = KhmerUnpairedBracketsRule(messages_for('en'), language)
    assert rule.get_id() == 'KM_UNPAIRED_BRACKETS'
    assert rule.start_symbols == ['[', '(', '{', '“', '"', "'", '«']
    assert rule.end_symbols == [']', ')', '}', '”', '"', "'", '»']
    lt = JLanguageTool(language)
    assert lt.check('នេះ «ហើយ»​នោះ.') == []
    m, = lt.check('នេះ (ហើយ​នោះ.')
    assert (m.rule.get_id(), m.from_pos, m.to_pos) == ('KM_UNPAIRED_BRACKETS', 4, 5)
