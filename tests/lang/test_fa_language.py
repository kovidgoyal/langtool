"""Port of org.languagetool.rules.fa.PersianTest (LanguageSpecificTest),
org.languagetool.rules.fa.PersianSpaceBeforeRuleTest,
org.languagetool.rules.fa.WordCoherencyRuleTest,
org.languagetool.rules.fa.LanguageSpecificSpellcheckerTest and
org.languagetool.tokenizers.PersianSRXSentenceTokenizerTest, plus checks of
the Persian language definition against org.languagetool.language.Persian
and of PersianWordTokenizer and the other rules of org.languagetool.rules.fa.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import pytest

from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.fa.rules import (PersianCommaWhitespaceRule, PersianDoublePunctuationRule, PersianSpaceBeforeRule,
                                    PersianWordRepeatBeginningRule, PersianWordRepeatRule, SimpleReplaceRule,
                                    WordCoherencyRule)
from langtool.lang.fa.tokenizers import PersianWordTokenizer
from langtool.messages import messages_for
from langtool.tagging import DemoTagger
from langtool.tool import JLanguageTool


# --- PersianTest ---

def test_language():
    """PersianTest.testLanguage: runTests(new Persian(), null, "ā") (the demo
    text test is commented out in Java); the language independent checks are
    in tests/test_jlanguagetool.py. testCoherencyBaseformIsOtherForm is a
    no-op for Persian (no synthesizer)."""
    lang = get_language('fa')
    assert lang.synthesizer is None
    assert JLanguageTool(lang).check('این یک جمله است.') == []


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.fa.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('fa')
    assert lang.code == 'fa'
    assert lang.name == 'Persian'
    assert lang.countries == ['IR', 'AF']
    # no tagger and no disambiguator overrides: Language's DemoTagger and DemoDisambiguator
    assert isinstance(lang.tagger, DemoTagger)
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    assert lang.synthesizer is None
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert type(lang.word_tokenizer) is PersianWordTokenizer
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['fa', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('fa')
    rules = lang.get_relevant_rules(messages_for('fa'))
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'WHITESPACE_RULE', 'TOO_LONG_SENTENCE',
        'PERSIAN_COMMA_PARENTHESIS_WHITESPACE', 'PERSIAN_DOUBLE_PUNCTUATION', 'PERSIAN_WORD_REPEAT_BEGINNING_RULE',
        'PERSIAN_WORD_REPEAT_RULE', 'FA_SIMPLE_REPLACE', 'FA_SPACE_BEFORE_CONJUNCTION', 'FA_WORD_COHERENCY']
    assert [type(r) for r in rules[4:]] == [
        PersianCommaWhitespaceRule, PersianDoublePunctuationRule, PersianWordRepeatBeginningRule,
        PersianWordRepeatRule, SimpleReplaceRule, PersianSpaceBeforeRule, WordCoherencyRule]
    assert [r.get_id() for r in rules if r.default_off] == ['PERSIAN_COMMA_PARENTHESIS_WHITESPACE',
                                                            'FA_SPACE_BEFORE_CONJUNCTION']
    assert not unsupported_components(lang)


# --- PersianSRXSentenceTokenizerTest ---

def test_sentence_tokenizer():
    """PersianSRXSentenceTokenizerTest.test"""
    stokenizer = get_language('fa').sentence_tokenizer

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    # NOTE: sentences here need to end with a space character so they
    # have correct whitespace when appended:
    test_split('این یک جمله است. ', 'جملهٔ بعدی')
    test_split('آیا این یک جمله است؟ ', 'جملهٔ بعدی')
    test_split('یک جمله!!! ', 'جملهٔ بعدی')

    test_split('جملهٔ اول... خوب نیست؟ ', 'جملهٔ دوم.')
    test_split('جملهٔ اول (...) ادامهٔ متن. ')
    test_split('جملهٔ اول [...] ادامهٔ متن. ')


# --- PersianWordTokenizer ---

def test_word_tokenizer():
    """PersianWordTokenizer: the default tokenizing characters plus the Arabic
    comma, question mark and semicolon"""
    tokenizer = PersianWordTokenizer()
    assert tokenizer.tokenize('سلام،خوبی؟ آره؛ نه') == ['سلام', '،', 'خوبی', '؟', ' ', 'آره', '؛', ' ', 'نه']
    # the zero width non-joiner (U+200C) is a tokenizing character of WordTokenizer
    assert tokenizer.tokenize('می‌روم') == ['می', '‌', 'روم']
    assert tokenizer.tokenize('x@example.com، http://x.org/a') == ['x@example.com', '،', ' ', 'http://x.org/a']


# --- PersianSpaceBeforeRuleTest ---

def test_space_before_rule(demo_language):
    """PersianSpaceBeforeRuleTest.testRules"""
    rule = PersianSpaceBeforeRule(messages_for('en'), demo_language)
    lt = JLanguageTool(demo_language)

    def assert_matches(text, expected_matches):
        assert len(rule.match(lt.get_analyzed_sentence(text))) == expected_matches

    assert_matches('به اینجا', 1)
    assert_matches('من به اینجا', 0)
    assert_matches('(به اینجا', 0)


def test_space_before_rule_properties():
    lang = get_language('fa')
    rule = PersianSpaceBeforeRule(messages_for('fa'), lang)
    assert rule.get_id() == 'FA_SPACE_BEFORE_CONJUNCTION'
    assert rule.default_off
    assert rule.category.id == 'MISC'
    m, = rule.match(JLanguageTool(lang).get_analyzed_sentence('من،با تو'))
    assert (m.from_pos, m.to_pos) == (3, 5)
    assert m.suggested_replacements == [' با']
    assert m.message == 'فاصلهٔ قبل از حرف ربط حذف شده‌است'
    assert m.short_message == 'فاصلهٔ حذف‌شده'
    # the whole token must be a conjunction
    assert rule.match(JLanguageTool(lang).get_analyzed_sentence('من،باران')) == []


# --- WordCoherencyRuleTest ---

def test_word_coherency_rule():
    """WordCoherencyRuleTest.testRules"""
    lang = get_language('fa')
    lt = JLanguageTool(lang)
    rule = WordCoherencyRule(messages_for('fa'), lang)
    assert len(rule.match([lt.get_analyzed_sentence('این یک اتاق است.')])) == 0
    assert len(rule.match([lt.get_analyzed_sentence('این یک اتاق است. این یک اطاق است.')])) == 1


def test_word_coherency_rule_properties():
    lang = get_language('fa')
    rule = WordCoherencyRule(messages_for('fa'), lang)
    assert rule.get_id() == 'FA_WORD_COHERENCY'
    assert rule.incorrect_examples == [] and rule.correct_examples == []
    # (JLanguageTool.check reports FA_SIMPLE_REPLACE for the same span, اطاق is in replace.txt too)
    m, = rule.match(JLanguageTool(lang).analyze_text('این یک اتاق است. این یک اطاق است.'))
    assert (m.from_pos, m.to_pos) == (24, 28)
    assert m.suggested_replacements == ['اتاق']
    assert m.message == "'اطاق' و 'اتاق' نباید در یک جا استفاده شوند"


# --- other rules of org.languagetool.rules.fa ---

def test_simple_replace_rule():
    lang = get_language('fa')
    rule = SimpleReplaceRule(messages_for('fa'), lang)
    assert rule.get_id() == 'FA_SIMPLE_REPLACE'
    assert rule.category.id == 'CONFUSED_WORDS'
    assert rule.loc_quality_issue_type == 'Misspelling'
    assert not rule.is_case_sensitive()
    assert rule.get_wrong_words()['حاظر'] == ['حاضر']
    m, = rule.match(JLanguageTool(lang).get_analyzed_sentence('وی حاظر به همکاری شد.'))
    assert (m.from_pos, m.to_pos) == (3, 7)
    assert m.suggested_replacements == ['حاضر']
    assert m.message == 'اشتباه محتمل املائی پیداشده: حاضر.'
    assert m.short_message == 'اشتباه محتمل املائی'


def test_comma_whitespace_rule():
    lang = get_language('fa')
    rule = PersianCommaWhitespaceRule(messages_for('fa'), lang)
    assert rule.get_id() == 'PERSIAN_COMMA_PARENTHESIS_WHITESPACE'
    assert rule.default_off
    lt = JLanguageTool(lang)
    assert rule.match(lt.get_analyzed_sentence('من، تو و او.')) == []
    m, = rule.match(lt.get_analyzed_sentence('من ، تو و او.'))
    assert (m.from_pos, m.to_pos) == (2, 4)
    assert m.suggested_replacements == ['،']
    m, = rule.match(lt.get_analyzed_sentence('من،تو و او.'))
    assert m.suggested_replacements == ['، تو']


def test_double_punctuation_rule():
    lang = get_language('fa')
    rule = PersianDoublePunctuationRule(messages_for('fa'), lang)
    assert rule.get_id() == 'PERSIAN_DOUBLE_PUNCTUATION'
    lt = JLanguageTool(lang)
    assert rule.match(lt.get_analyzed_sentence('من، تو و او.')) == []
    m, = rule.match(lt.get_analyzed_sentence('من،، تو و او.'))
    assert (m.from_pos, m.to_pos) == (2, 4)
    assert m.suggested_replacements == ['،']


def test_word_repeat_rule():
    lang = get_language('fa')
    rule = PersianWordRepeatRule(messages_for('fa'), lang)
    assert rule.get_id() == 'PERSIAN_WORD_REPEAT_RULE'
    lt = JLanguageTool(lang)
    m, = rule.match(lt.get_analyzed_sentence('این کار برای برای تو بود.'))
    assert m.suggested_replacements == ['برای']
    for s in ('من لی لی را دیدم', 'آب درون بطری ۱۰۰ سی سی بود', 'لک لک یک پرنده است', 'غذایش را ریز ریز کرد',
              'جز جز این کتاب را بلدم', 'با من کل کل نکن'):
        assert rule.match(lt.get_analyzed_sentence(s)) == [], s


def test_word_repeat_beginning_rule():
    lang = get_language('fa')
    rule = PersianWordRepeatBeginningRule(messages_for('fa'), lang)
    assert rule.get_id() == 'PERSIAN_WORD_REPEAT_BEGINNING_RULE'
    lt = JLanguageTool(lang)
    # an adverb at the beginning of two successive sentences
    matches = rule.match(lt.analyze_text('همچنین، خیابان مسکونی است. همچنین، به افتخار یک شاعر است.'))
    assert len(matches) == 1
    assert matches[0].short_message == messages_for('fa')['desc_repetition_beginning_adv']
    # other words need three sentences
    assert rule.match(lt.analyze_text('خیابان مسکونی است. خیابان به افتخار یک شاعر است.')) == []
