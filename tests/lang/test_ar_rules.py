"""Port of the tests of the Arabic rules and filters:
org.languagetool.rules.ar.ArabicCommaWhitespaceRuleTest,
ArabicQuestionMarkWhitespaceRuleTest, ArabicSemiColonWhitespaceRuleTest,
ArabicSimpleReplaceRuleTest, ArabicDiacriticsCheckRuleTest,
ArabicDarjaRuleTest, ArabicHomophonesCheckRuleTest, ArabicRedundancyRuleTest,
ArabicWordCoherencyRuleTest, ArabicWordinessRuleTest, ArabicTransVerbRuleTest,
ArabicInflectedOneWordReplaceRuleTest, ArabicHunspellSpellerRuleTest and
ArabicConfusionProbabilityRuleTest (skipped: spell checking and language
model), and org.languagetool.rules.ar.filters.ArabicDateCheckFilterTest,
ArabicMasdarToVerbFilterTest, ArabicNumberPhraseFilterTest and
ArabicVerbToMasdarFilterTest; plus checks of the other rules and filters."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.ar.filters import (ArabicAdjectiveToExclamationFilter, ArabicDateCheckFilter,
                                      ArabicDMYDateCheckFilter, ArabicMasdarToVerbFilter, ArabicNumberPhraseFilter,
                                      ArabicVerbToMafoulMutlaqFilter, FRIDAY, MONDAY, SATURDAY, SUNDAY, THURSDAY,
                                      TUESDAY, WEDNESDAY)
from langtool.lang.ar.rules import (ArabicCommaWhitespaceRule, ArabicDarjaRule, ArabicDiacriticsRule,
                                    ArabicDoublePunctuationRule, ArabicHomophonesRule,
                                    ArabicInflectedOneWordReplaceRule, ArabicQuestionMarkWhitespaceRule,
                                    ArabicRedundancyRule, ArabicSemiColonWhitespaceRule, ArabicSimpleReplaceRule,
                                    ArabicTransVerbRule, ArabicWordCoherencyRule, ArabicWordinessRule,
                                    ArabicWordRepeatRule, ArabicWrongWordInContextRule)
from langtool.lang.ar.tokenizers import ArabicWordTokenizer
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.core_filters import CalendarDate
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module')
def lang():
    require_dictionaries('ar')
    return get_language('ar')


@pytest.fixture(scope='module')
def lt(lang):
    return JLanguageTool(lang)


@pytest.fixture(scope='module')
def en_messages():
    return messages_for('en')


@pytest.fixture(scope='module')
def ar_messages():
    return messages_for('ar')


def _match(rule, lt, text):
    return rule.match(lt.get_analyzed_sentence(text))


# --- ArabicCommaWhitespaceRuleTest ---

def test_comma_whitespace_rule(lang, lt, en_messages):
    """ArabicCommaWhitespaceRuleTest.testRule"""
    rule = ArabicCommaWhitespaceRule(en_messages, lang)
    for text, n in [
            # correct
            ('هذه جملة تجريبية.', 0),
            ('هذه, هي, جملة التجربة.', 0),
            ('قل (كيت وكيت) تجربة!.', 0),
            ('تكلف €2,45.', 0),
            ('ثمنها 50,- يورو', 0),
            ('جملة مع علامات الحذف ...', 0),
            ('هذه صورة: .5 وهي صحيحة.', 0),
            ('هذه $1,000,000.', 0),
            ('هذه 1,5.', 0),
            ("هذا ,,فحص''.", 0),
            ('نفّذ ./validate.sh لفحص الملف.', 0),
            ('هذه, حقا, فراغ غير فاصل.', 0),
            # errors: arabic comma
            ('هذه،جملة للتجربة.', 1),
            ('هذه ، جملة للتجربة.', 1),
            ('هذه ،تجربة جملة.', 2),
            ('،هذه جملة للتجربة.', 2)]:
        assert len(_match(rule, lt, text)) == n, text


# --- ArabicQuestionMarkWhitespaceRuleTest ---

def test_question_mark_whitespace_rule(lang, lt, en_messages):
    """ArabicQuestionMarkWhitespaceRuleTest.testRule"""
    rule = ArabicQuestionMarkWhitespaceRule(en_messages, lang)
    # correct
    assert len(_match(rule, lt, 'أهذه تجربة؟')) == 0
    assert len(_match(rule, lt, 'This is a test sentence?')) == 0
    assert len(_match(rule, lt, 'أهذه تجربة?')) == 0
    # errors: arabic question mark
    assert len(_match(rule, lt, 'This is a test sentence؟')) == 0
    assert len(_match(rule, lt, 'أهذه تجربة ؟')) == 1


# --- ArabicSemiColonWhitespaceRuleTest ---

def test_semicolon_whitespace_rule(lang, lt, en_messages):
    """ArabicSemiColonWhitespaceRuleTest.testRule"""
    rule = ArabicSemiColonWhitespaceRule(en_messages, lang)
    # correct
    assert len(_match(rule, lt, 'This is a test sentence؛')) == 0
    assert len(_match(rule, lt, 'أهذه تجربة؛')) == 0
    # errors: Arabic semi colon
    assert len(_match(rule, lt, 'أهذه تجربة ؛')) == 1


def test_double_punctuation_and_word_repeat_rules(lang, lt, en_messages):
    """ArabicDoublePunctuationRule and ArabicWordRepeatRule"""
    rule = ArabicDoublePunctuationRule(en_messages, lang)
    assert rule.get_id() == 'ARABIC_DOUBLE_PUNCTUATION'
    assert len(_match(rule, lt, 'نعم،، لقد نجحنا.')) == 1
    assert len(_match(rule, lt, 'نعم، لقد نجحنا.')) == 0
    rule = ArabicWordRepeatRule(en_messages, lang)
    assert rule.get_id() == 'ARABIC_WORD_REPEAT_RULE'
    matches = _match(rule, lt, 'هذا فقط فقط مثال.')
    assert len(matches) == 1 and matches[0].suggested_replacements == ['فقط']
    assert len(_match(rule, lt, 'نفذت التعليمات خطوة خطوة.')) == 0
    assert len(_match(rule, lt, 'سار رويدا رويدا.')) == 0


# --- ArabicSimpleReplaceRuleTest ---

def test_simple_replace_rule(lang, lt, ar_messages):
    """ArabicSimpleReplaceRuleTest.testRule"""
    rule = ArabicSimpleReplaceRule(ar_messages, lang)
    assert len(_match(rule, lt, 'عبد الله')) == 0
    # incorrect sentences:
    matches = _match(rule, lt, 'عبدالله')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'عبد الله'
    assert len(_match(rule, lt, 'يافطة')) == 1
    assert len(_match(rule, lt, 'المائة')) == 1
    assert len(_match(rule, lt, 'الذى')) == 1


# --- ArabicDiacriticsCheckRuleTest ---

def test_diacritics_rule(lang, lt, en_messages):
    """ArabicDiacriticsCheckRuleTest.testRule"""
    rule = ArabicDiacriticsRule(en_messages, lang)
    # incorrect sentences:
    assert len(_match(rule, lt, 'تجربة')) == 1


# --- ArabicDarjaRuleTest ---

def test_darja_rule(lang, lt, ar_messages):
    """ArabicDarjaRuleTest.testRule"""
    rule = ArabicDarjaRule(ar_messages, lang)
    # correct sentences:
    assert len(_match(rule, lt, 'إن شاء')) == 0
    # incorrect sentences:
    matches = _match(rule, lt, 'طرشي')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'فلفل حلو'
    assert len(_match(rule, lt, 'فايدة')) == 1


# --- ArabicHomophonesCheckRuleTest ---

def test_homophones_rule(lang, lt, en_messages):
    """ArabicHomophonesCheckRuleTest.testRule"""
    rule = ArabicHomophonesRule(en_messages, lang)
    # incorrect sentences:
    assert len(_match(rule, lt, 'ضن')) == 1
    assert len(_match(rule, lt, 'حاضر')) == 1
    assert len(_match(rule, lt, 'حض')) == 1
    # FIXME (in Java): AbstractSimpleReplaceRule2 doesn't support lemma checking (الحاضر)


# --- ArabicRedundancyRuleTest ---

def test_redundancy_rule(lang, lt, ar_messages):
    """ArabicRedundancyRuleTest.testRule"""
    rule = ArabicRedundancyRule(ar_messages, lang)
    # incorrect sentences:
    matches = _match(rule, lt, 'سوف لن')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'لن'


# --- ArabicWordCoherencyRuleTest ---

def test_word_coherency_rule(lang, lt, en_messages):
    """ArabicWordCoherencyRuleTest.testRule (the Java test has no active
    assertion; check the example pair of the rule instead)"""
    rule = ArabicWordCoherencyRule(en_messages, lang)
    matches = rule.match(lt.analyze_text('وزارة الشؤون الخارجية تهتم  بكل شئون العالم.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['شؤون']
    assert matches[0].message == "تجنب استعمال شكلين للكلمة نفسها ('شئون' و 'شؤون') في  النص نفسه."


# --- ArabicWordinessRuleTest ---

def test_wordiness_rule(lang, lt, en_messages):
    """ArabicWordinessRuleTest.testRule"""
    rule = ArabicWordinessRule(en_messages, lang)
    # errors:
    assert len(_match(rule, lt, 'وأخيرا وليس آخرا')) == 1


def test_wrong_word_in_context_rule(lang, lt, en_messages):
    """ArabicWrongWordInContextRule: /ar/wrongWordInContext.txt has no
    entries yet (only comments), so even its example pair is not found"""
    rule = ArabicWrongWordInContextRule(en_messages, lang)
    assert rule.get_id() == 'ARABIC_WRONG_WORD_IN_CONTEXT'
    assert not rule.context_words_set
    assert len(_match(rule, lt, 'من سوء الضن بالله ترك الأمر بالمعروف.')) == 0


# --- ArabicTransVerbRuleTest ---

def test_trans_verb_rule(lang, lt, en_messages):
    """ArabicTransVerbRuleTest.testRule"""
    rule = ArabicTransVerbRule(en_messages, lang)
    # correct sentences:
    assert len(_match(rule, lt, 'كان أَفَاضَ في الحديث')) == 0
    # errors:
    assert len(_match(rule, lt, 'كان أفاض من الحديث')) == 1
    assert len(_match(rule, lt, 'لقد أفاضت من الحديث')) == 1
    assert len(_match(rule, lt, 'لقد أفاضت الحديث')) == 1
    assert len(_match(rule, lt, 'كان أفاضها الحديث')) == 1
    assert len(_match(rule, lt, 'إذ استعجل الأمر')) == 1


def test_trans_verb_rule_suggestion(lang, lt, en_messages):
    """ArabicTransVerbRule: the verb without the pronoun followed by the
    preposition with the pronoun"""
    rule = ArabicTransVerbRule(en_messages, lang)
    matches = _match(rule, lt, 'كان أفاضها الحديث')
    assert (matches[0].from_pos, matches[0].to_pos) == (4, 10)
    # the preposition is synthesized with the POS tag PRD;---;--H, which is not in the
    # dictionary (the tags of في with pronouns are like PRD;---;F1H), so it is empty (as in Java)
    assert matches[0].suggested_replacements == ['أفاض ']


# --- ArabicInflectedOneWordReplaceRuleTest ---

def test_inflected_one_word_replace_rule(lang, lt, en_messages):
    """ArabicInflectedOneWordReplaceRuleTest.testRule"""
    rule = ArabicInflectedOneWordReplaceRule(en_messages, lang)
    # correct sentences:
    assert len(_match(rule, lt, 'أجريت بحوثا في المخبر')) == 0
    assert len(_match(rule, lt, 'وجعل لكم من أزواجكم بنين وحفدة')) == 0
    # errors:
    assert len(_match(rule, lt, 'أجريت أبحاثا في المخبر')) != 0
    assert len(_match(rule, lt, 'وجعل لكم من أزواجكم بنين وأحفاد')) != 0


@pytest.mark.skip(reason='spell checking is not ported: ArabicHunspellSpellerRuleTest tests the '
                         'ArabicHunspellSpellerRule (HunspellRule)')
def test_hunspell_speller_rule():
    """Port of ArabicHunspellSpellerRuleTest.testRuleWithArabic"""


@pytest.mark.skip(reason='language model rules are not ported: ArabicConfusionProbabilityRuleTest tests the '
                         'ArabicConfusionProbabilityRule (ConfusionProbabilityRule)')
def test_confusion_probability_rule():
    """Port of ArabicConfusionProbabilityRuleTest.testConstructor"""


# --- filters ---

class _FakeRule(Rule):
    def get_id(self):
        return 'FAKE-RULE'

    def get_description(self):
        return 'fake rule'


def _fake_match():
    return RuleMatch(_FakeRule(), None, 0, 10, 'message')


# --- ArabicDateCheckFilterTest ---

def _make_map(year, month, day_of_month, week_day):
    return {'year': year, 'month': month, 'day': day_of_month, 'weekDay': week_day}


def test_date_check_filter_accept(lang):
    """ArabicDateCheckFilterTest.testAccept"""
    f = ArabicDateCheckFilter(lang)
    assert f.accept_rule_match(_fake_match(), _make_map('2022', '3', '12', 'السبت'), -1, None, None) is None
    assert f.accept_rule_match(_fake_match(), _make_map('2022', '3', '12', 'الأحد'), -1, None, None) is not None


def test_date_check_filter_accept_incomplete_args(lang):
    """ArabicDateCheckFilterTest.testAcceptIncompleteArgs"""
    f = ArabicDateCheckFilter(lang)
    m = _make_map('2022', '3', '12', 'السبت')
    del m['weekDay']
    with pytest.raises(ValueError):
        f.accept_rule_match(_fake_match(), m, -1, None, None)


def test_date_check_filter_get_day_of_week1(lang):
    """ArabicDateCheckFilterTest.testGetDayOfWeek1"""
    f = ArabicDateCheckFilter(lang)
    assert f.get_day_of_week('الأحد') == SUNDAY
    assert f.get_day_of_week('الإثنين') == MONDAY
    assert f.get_day_of_week('الثلاثاء') == TUESDAY
    assert f.get_day_of_week('الأربعاء') == WEDNESDAY
    assert f.get_day_of_week('الخميس') == THURSDAY
    assert f.get_day_of_week('الجمعة') == FRIDAY
    assert f.get_day_of_week('السبت') == SATURDAY
    # inverse
    assert f.get_day_of_week_name_for_day(SUNDAY) == 'الأحد'
    assert f.get_day_of_week_name_for_day(MONDAY) == 'الإثنين'
    assert f.get_day_of_week_name_for_day(TUESDAY) == 'الثلاثاء'
    assert f.get_day_of_week_name_for_day(WEDNESDAY) == 'الأربعاء'
    assert f.get_day_of_week_name_for_day(THURSDAY) == 'الخميس'
    assert f.get_day_of_week_name_for_day(FRIDAY) == 'الجمعة'
    assert f.get_day_of_week_name_for_day(SATURDAY) == 'السبت'
    assert f.get_day_of_week_name_for_day(0) == 'غير محدد'


def test_date_check_filter_get_day_of_week2(lang):
    """ArabicDateCheckFilterTest.testGetDayOfWeek2"""
    f = ArabicDateCheckFilter(lang)
    assert f.get_day_of_week_name(CalendarDate.of(2022, 2, 25)) == 'الجمعة'
    assert f.get_day_of_week_name(CalendarDate.of(2022, 2, 26)) == 'السبت'


def test_date_check_filter_get_month(lang):
    """ArabicDateCheckFilterTest.testGetMonth"""
    f = ArabicDateCheckFilter(lang)
    assert f.get_month('جانفي') == 1
    assert f.get_month('جانفييه') == 1
    assert f.get_month('يناير') == 1
    assert f.get_month('ديسمبر') == 12
    assert f.get_month('كانون الأول') == 12
    assert f.get_month('كانون أول') == 12
    assert f.get_month('أبريل') == 4
    assert f.get_month('نيسان') == 4


def test_dmy_date_check_filter(lang):
    """ArabicDMYDateCheckFilter: the date in the format dd-mm-yyyy"""
    f = ArabicDMYDateCheckFilter(lang)
    assert f.accept_rule_match(_fake_match(), {'date': '12-3-2022', 'weekDay': 'السبت'}, -1, None, None) is None
    m = f.accept_rule_match(RuleMatch(_FakeRule(), None, 0, 10, '{day} / {realDay}'),
                            {'date': '12-3-2022', 'weekDay': 'الإثنين'}, -1, None, None)
    assert m.message == 'الاثنين / السبت'
    with pytest.raises(RuntimeError):
        f.accept_rule_match(_fake_match(), {'date': '12-3-2022', 'day': '12', 'weekDay': 'السبت'}, -1, None, None)


# --- ArabicMasdarToVerbFilterTest ---

@pytest.mark.parametrize('word,expected', [('عمل', 'يعمل'), ('إعمال', 'يعمل'), ('سؤال', 'يسأل'), ('أكل', 'يأكل')])
def test_masdar_to_verb_filter(lang, word, expected):
    """ArabicMasdarToVerbFilterTest.testFilter"""
    f = ArabicMasdarToVerbFilter(lang)
    word1 = 'يقوم'
    word2 = 'بال' + word
    args = {'verb': word1, 'noun': word2}
    pattern_tokens = lang.tagger.tag([word1, word2])
    rule_match = f.accept_rule_match(_fake_match(), args, -1, pattern_tokens, None)
    assert rule_match is not None
    assert rule_match.suggested_replacements == [expected]


def test_masdar_to_verb_filter_data(lang):
    """ArabicMasdarToVerbFilterTest.testRule"""
    assert ArabicMasdarToVerbFilter(lang).masdar2verb_list is not None


# --- ArabicVerbToMasdarFilterTest ---

def test_verb_to_mafoul_mutlaq_filter(lang):
    """ArabicVerbToMasdarFilterTest.testFilter"""
    f = ArabicVerbToMafoulMutlaqFilter(lang)
    word, word2, word3 = 'يعمل', 'بأسلوب', 'جيد'
    args = {'verb': word, 'adj': word3}
    pattern_tokens = lang.tagger.tag([word, word2, word3])
    rule_match = f.accept_rule_match(_fake_match(), args, -1, pattern_tokens, None)
    assert rule_match is not None
    assert 'يعمل عملًا جيدًا' in rule_match.suggested_replacements


# --- ArabicNumberPhraseFilterTest ---

def _assert_number_suggestion(lang, phrase, expected_suggestion, previous_word, next_word, inflection):
    f = ArabicNumberPhraseFilter(lang)
    args = {'previous': previous_word, 'previousPos': '1', 'next': next_word, 'inflect': inflection,
            # the value -1, used to say that the last word is the given next word
            'nextPos': '-1'}
    # tokenize the phrase
    full_phrase = previous_word + ' ' + phrase + ' ' + next_word
    tokens = [t for t in ArabicWordTokenizer().tokenize(full_phrase) if t != ' ']
    pattern_tokens = lang.tagger.tag(tokens)
    rule_match = f.accept_rule_match(_fake_match(), args, -1, pattern_tokens, None)
    expected_size = len(expected_suggestion.split('|'))
    assert rule_match is not None
    assert len(rule_match.suggested_replacements) == expected_size, phrase


@pytest.mark.parametrize('phrase,expected', [
    ('صفر', ''),
    ('واحد', ''),
    ('اثنان', 'اثنين'),
    ('ثلاثة', ''),
    ('إحدى عشر', 'أحد عشر'),
    ('اثنتي عشر', 'اثني عشر'),
    ('أربعة عشر', ''),
    ('أربعة وثلاثون', 'أربعة وثلاثين'),
    ('مائةٍ', ''),
    ('مائة وخمسة وعشرون', 'مائة وخمسة وعشرين'),
    ('مائة وأربعة وثلاثين', ''),
    ('ألف وتسعمائة واثنان وعشرين', 'ألف وتسعمائة واثنين وعشرين'),
    ('مليون ومئتان وخمسة وأربعين ألفاً وسبعمائة وواحد', 'مليون ومئتين وخمسة وأربعين ألفا وسبعمائة وواحد'),
    ('مائة واثنين', ''),
    ('عشرة وآلاف', 'عشرة آلاف'),
])
def test_number_phrase_filter(lang, phrase, expected):
    """ArabicNumberPhraseFilterTest.testFilter"""
    _assert_number_suggestion(lang, phrase, expected, 'في', '', '')


@pytest.mark.parametrize('phrase,expected', [
    ('واحد', 'في دينار واحد'),
    ('ثلاثة', 'في ثلاثة دنانير'),
    ('إحدى عشر', 'في أحد عشر دينارا'),
    ('اثنتي عشر', 'في اثني عشر دينارا'),
    ('أربعة عشر', 'في أربعة عشر دينارا'),
    ('أربعة وثلاثون', 'في أربعة وثلاثين دينارا'),
    ('مائةٍ', 'في مائة دينار'),
    ('مائة وخمسة وعشرون', 'في مائة وخمسة وعشرين دينارا'),
    ('مائة وأربعة وثلاثين', 'في مائة وأربعة وثلاثين دينارا'),
    ('ألف وتسعمائة واثنان وعشرين', 'في ألف وتسعمائة واثنين وعشرين دينارا'),
    ('مليون ومئتان وخمسة وأربعين ألفاً وسبعمائة وواحد', 'في مليون ومئتين وخمسة وأربعين ألفا وسبعمائة وواحد دينار'),
    ('عشرة وآلاف', 'في عشرة آلاف دينار'),
])
def test_number_phrase_unit_filter(lang, phrase, expected):
    """ArabicNumberPhraseFilterTest.testUnitFilter"""
    _assert_number_suggestion(lang, phrase, expected, 'في', 'دينار', '')


def test_number_phrase_filter_suggestions(lang):
    """ArabicNumberPhraseFilter: the suggestions (the numeric phrase starts
    with the previous word, as in Java with previousPos:1)"""
    f = ArabicNumberPhraseFilter(lang)
    tokens = lang.tagger.tag(['في', 'اثنان', 'وعشرون', 'كتاب'])
    m = f.accept_rule_match(_fake_match(), {'previous': 'في', 'previousPos': '1', 'nextPos': '-1'}, -1, tokens,
                            None)
    assert m.suggested_replacements == ['في اثنين وعشرين']
    m = f.accept_rule_match(_fake_match(), {'previous': 'في', 'previousPos': '1', 'nextPos': '-1',
                                            'next': 'دينار'}, -1, lang.tagger.tag(['في', 'ثلاثة', 'دينار']), None)
    # (the dictionary has the plural form دينارين of دينار)
    assert m.suggested_replacements == ['في ثلاثة دينارين']


# --- ArabicAdjectiveToExclamationFilter ---

def test_adjective_to_exclamation_filter(lang):
    """ArabicAdjectiveToExclamationFilter: the entries of the data file
    start with a space, so (as in Java) no comparative is found"""
    f = ArabicAdjectiveToExclamationFilter(lang)
    tokens = lang.tagger.tag(['كم', 'الولد', 'جميل'])
    m = f.accept_rule_match(_fake_match(), {'adj': 'جميل', 'adj_pos': '3', 'noun': 'الولد'}, -1, tokens, None)
    assert m is not None and m.suggested_replacements == []
    assert ' جميل' in f.adj2comp_list
    assert f.prepare_suggestions(['ما أجمل', 'أجمِل ب'], 'الولد') == ['ما أجمل الولد', 'أجمِل بالولد']
    assert f.prepare_suggestions(['ما أجمل', 'أجمِل ب'], 'هو') == ['ما أجمله', 'أجمِل به']
    assert f.prepare_suggestions(['ما أجمل'], '') == ['ما أجمل']
    with pytest.raises(RuntimeError):
        f.accept_rule_match(_fake_match(), {'adj': 'جميل', 'adj_pos': 'x'}, -1, tokens, None)
