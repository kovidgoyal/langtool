"""Port of org.languagetool.rules.ar.ArabicTaggerTest,
org.languagetool.rules.ar.ArabicTagManagerTest,
org.languagetool.synthesis.ar.ArabicSynthesizerTest,
org.languagetool.tools.ArabicStringToolsTest and
org.languagetool.rules.ar.ArabicSRXSentenceTokenizerTest, plus checks of
ArabicTagger (affixes, new style pronoun tags), ArabicSynthesizer
(inflection helpers), ArabicWordTokenizer and ArabicNumbersWords."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.lang.ar import numbers
from langtool.lang.ar.synthesis import inflect_adjective_tanwin_nasb, inflect_mafoul_mutlq
from langtool.lang.ar.tagging import ArabicTagManager, ArabicTagger
from langtool.lang.ar.tokenizers import ArabicWordTokenizer
from langtool.lang.ar.tools import get_attached_pronoun, remove_tashkeel
from langtool.tokenizers import WordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module')
def lang():
    require_dictionaries('ar')
    return get_language('ar')


@pytest.fixture(scope='module')
def tagger(lang):
    return lang.tagger


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in r.readings))
           for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


# --- ArabicStringToolsTest ---

def test_remove_tashkeel():
    """ArabicStringToolsTest.testRemoveTashkeel"""
    assert remove_tashkeel('') == ''
    assert remove_tashkeel('a') == 'a'
    assert remove_tashkeel('öäü') == 'öäü'
    assert remove_tashkeel('كَتَب') == 'كتب'
    assert remove_tashkeel('عـــربي') == 'عربي'  # tatweel


# --- ArabicTaggerTest ---

def test_dictionary(tagger):
    """ArabicTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0


def test_tagger(tagger):
    """ArabicTaggerTest.testTagger"""
    tokenizer = WordTokenizer()
    _my_assert('الخياريتان',
               'الخياريتان/[خيار]NA-;F3--;--L|الخياريتان/[خيار]NJ-;F2--;--L|الخياريتان/[خيار]NJ-;F3--;--L',
               tokenizer, tagger)
    _my_assert('السماء زرقاء',
               'السماء/[سماء]NJ-;F1--;--L|السماء/[سماء]NJ-;F1A-;--L|السماء/[سماء]NJ-;F1I-;--L|'
               'السماء/[سماء]NJ-;F1U-;--L -- '
               'زرقاء/[زرقاء]NA-;F1--;---|زرقاء/[زرقاء]NA-;F1A-;---|زرقاء/[زرقاء]NA-;F1I-;---|'
               'زرقاء/[زرقاء]NA-;F1U-;---', tokenizer, tagger)
    # non-existing-word
    _my_assert('العباره', 'العباره/[null]null', tokenizer, tagger)
    _my_assert('والبلاد',
               'والبلاد/[بلاد]NJ-;F3--;W-L|والبلاد/[بلاد]NJ-;F3A-;W-L|والبلاد/[بلاد]NJ-;F3I-;W-L|'
               'والبلاد/[بلاد]NJ-;F3U-;W-L|والبلاد/[بلاد]NJ-;M1--;W-L|والبلاد/[بلاد]NJ-;M1A-;W-L|'
               'والبلاد/[بلاد]NJ-;M1I-;W-L|والبلاد/[بلاد]NJ-;M1U-;W-L', tokenizer, tagger)
    _my_assert('بلادهما',
               'بلادهما/[بلاد]NJ-;F3--;--H|بلادهما/[بلاد]NJ-;F3A-;--H|بلادهما/[بلاد]NJ-;F3I-;--H|'
               'بلادهما/[بلاد]NJ-;F3U-;--H|بلادهما/[بلاد]NJ-;M1--;--H|بلادهما/[بلاد]NJ-;M1A-;--H|'
               'بلادهما/[بلاد]NJ-;M1I-;--H|بلادهما/[بلاد]NJ-;M1U-;--H', tokenizer, tagger)
    _my_assert('وبلادهما',
               'وبلادهما/[بلاد]NJ-;F3--;W-H|وبلادهما/[بلاد]NJ-;F3A-;W-H|وبلادهما/[بلاد]NJ-;F3I-;W-H|'
               'وبلادهما/[بلاد]NJ-;F3U-;W-H|وبلادهما/[بلاد]NJ-;M1--;W-H|وبلادهما/[بلاد]NJ-;M1A-;W-H|'
               'وبلادهما/[بلاد]NJ-;M1I-;W-H|وبلادهما/[بلاد]NJ-;M1U-;W-H', tokenizer, tagger)
    _my_assert('كبلاد',
               'كبلاد/[بلاد]NJ-;F3--;-K-|كبلاد/[بلاد]NJ-;F3I-;-K-|كبلاد/[بلاد]NJ-;M1--;-K-|'
               'كبلاد/[بلاد]NJ-;M1I-;-K-', tokenizer, tagger)
    _my_assert('وكالبلاد',
               'وكالبلاد/[بلاد]NJ-;F3--;WKL|وكالبلاد/[بلاد]NJ-;F3I-;WKL|وكالبلاد/[بلاد]NJ-;M1--;WKL|'
               'وكالبلاد/[بلاد]NJ-;M1I-;WKL', tokenizer, tagger)
    _my_assert('فاستعملها',
               'فاستعملها/[اِسْتَعْمَلَ]V61;M1H-pa-;W-H|فاستعملها/[اِسْتَعْمَلَ]V61;M1Y-i--;W-H', tokenizer, tagger)
    _my_assert('سيعملون',
               'سيعملون/[أَعْمَلَ]V41;M3H-faU;-S-|سيعملون/[أَعْمَلَ]V41;M3H-fpU;-S-|'
               'سيعملون/[عَمِلَ]V31;M3H-faU;-S-|سيعملون/[عَمِلَ]V31;M3H-fpU;-S-|'
               'سيعملون/[عَمَّلَ]V41;M3H-faU;-S-|سيعملون/[عَمَّلَ]V41;M3H-fpU;-S-', tokenizer, tagger)
    _my_assert('فسيعملون',
               'فسيعملون/[أَعْمَلَ]V41;M3H-faU;WS-|فسيعملون/[أَعْمَلَ]V41;M3H-fpU;WS-|'
               'فسيعملون/[عَمِلَ]V31;M3H-faU;WS-|فسيعملون/[عَمِلَ]V31;M3H-fpU;WS-|'
               'فسيعملون/[عَمَّلَ]V41;M3H-faU;WS-|فسيعملون/[عَمَّلَ]V41;M3H-fpU;WS-', tokenizer, tagger)
    _my_assert('كتاب',
               'كتاب/[كتاب]NA-;-3--;---|كتاب/[كتاب]NA-;-3A-;---|كتاب/[كتاب]NA-;-3I-;---|كتاب/[كتاب]NA-;-3U-;---|'
               'كتاب/[كتاب]NJ-;M1--;---|كتاب/[كتاب]NJ-;M1A-;---|كتاب/[كتاب]NJ-;M1I-;---|كتاب/[كتاب]NJ-;M1U-;---|'
               'كتاب/[كتاب]NM-;M1--;---|كتاب/[كتاب]NM-;M1A-;---|كتاب/[كتاب]NM-;M1I-;---|كتاب/[كتاب]NM-;M1U-;---',
               tokenizer, tagger)
    _my_assert('للبلاد',
               'للبلاد/[بلاد]NJ-;F3--;-LL|للبلاد/[بلاد]NJ-;F3I-;-LL|للبلاد/[بلاد]NJ-;M1--;-LL|'
               'للبلاد/[بلاد]NJ-;M1I-;-LL', tokenizer, tagger)
    _my_assert('للاعب',
               'للاعب/[لاعب]NA-;M1--;-L-|للاعب/[لاعب]NA-;M1--;-LL|للاعب/[لاعب]NA-;M1I-;-L-|'
               'للاعب/[لاعب]NA-;M1I-;-LL|للاعب/[لَاعَبَ]V41;M1H-pa-;-L-|للاعب/[لَاعَبَ]V41;M1Y-i--;-L-',
               tokenizer, tagger)
    _my_assert('ببلاد',
               'ببلاد/[بلاد]NJ-;F3--;-B-|ببلاد/[بلاد]NJ-;F3I-;-B-|ببلاد/[بلاد]NJ-;M1--;-B-|'
               'ببلاد/[بلاد]NJ-;M1I-;-B-', tokenizer, tagger)


def test_tagger_details(lang, tagger):
    """ArabicTagger: tashkeel is ignored for the lookup, stop words get no
    readings with affixes, the single word tag(String), the new style
    pronoun tags and the affix helpers"""
    atr = tagger.tag('كَتَبَ')
    assert atr.token == 'كَتَبَ' and atr.readings and all(r.token == 'كَتَبَ' for r in atr.readings)
    # في is a stop word (it has POS tags P...): no additional readings (e.g. ف+ي)
    assert [(r.lemma, r.pos_tag) for r in tagger.tag('في').readings] == [
        ('في', 'PRD;---;---'), ('في', 'PR-;---;---'), ('وَفَى', 'VW1;F1Y-i--;---')]
    new_style = ArabicTagger(lang.dictionary('ar/arabic.dict'), lang.resource_dir)
    new_style.enable_new_style_pronoun_tag()
    assert {r.pos_tag[-1] for r in new_style.tag('بلادهما').readings} == {'j'}
    assert {r.pos_tag[-1] for r in tagger.tag('بلادهما').readings} == {'H'}
    tok = AnalyzedToken('وكالبلاد', 'NJ-;F3I-;WKL', 'بلاد')
    assert tagger.get_proclitic(tok) == 'وكال'
    assert tagger.get_jar_proclitic(tok) == 'ك'
    assert tagger.get_proclitic(AnalyzedToken('للبلاد', 'NJ-;F3I-;-LL', 'بلاد')) == 'لل'
    assert tagger.get_proclitic(AnalyzedToken('فسيعملون', 'V41;M3H-faU;WS-', 'عمل')) == 'فس'
    assert tagger.get_enclitic(AnalyzedToken('بلادهما', 'NJ-;F3I-;--H', 'بلاد')) == 'هما'
    assert tagger.get_enclitic(AnalyzedToken('بلاد', 'NJ-;F3I-;---', 'بلاد')) == ''
    assert tagger.get_enclitic(AnalyzedToken('بلادك', 'NJ-;F3I-;--d', 'بلاد')) == 'ك'
    readings = tagger.tag('سيعملون')
    assert sorted(tagger.get_lemmas(readings, 'verb')) == sorted({r.lemma for r in readings.readings})
    assert len(tagger.get_lemmas(readings, 'verb')) == 3
    assert tagger.get_lemmas(readings, 'adj') == []


# --- ArabicTagManagerTest ---

def test_tag_manager():
    """ArabicTagManagerTest.testTagger"""
    tag_manager = ArabicTagManager()
    assert tag_manager.set_jar('NJ-;M1I-;---', 'K') == 'NJ-;M1I-;-K-'
    assert tag_manager.set_jar('NJ-;M1I-;---', '-') == 'NJ-;M1I-;---'
    assert tag_manager.set_definite('NJ-;M1I-;---', 'L') == 'NJ-;M1I-;--L'
    assert tag_manager.set_definite('NJ-;M1I-;--H', 'L') == 'NJ-;M1I-;--H'
    assert tag_manager.set_pronoun('NJ-;M1I-;---', 'H') == 'NJ-;M1I-;--H'
    assert tag_manager.set_conjunction('NJ-;M1I-;---', 'W') == 'NJ-;M1I-;W--'
    assert tag_manager.set_conjunction('V-1;M1I----;---', 'W') == 'V-1;M1I----;W--'
    assert tag_manager.get_conjunction_prefix('V-1;M1I----;W--') == 'و'


def test_tag_manager_details():
    """ArabicTagManager: adding flags, incompatible flags, merging tags,
    flags beyond the end of short tags"""
    tm = ArabicTagManager()
    assert tm.modify_pos_tag('NJ-;M1I-;---', ['CONJ;W', 'JAR;B']) == 'NJ-;M1I-;WB-'
    assert tm.modify_pos_tag('NJ-;M1U-;---', ['JAR;B']) is None  # not majrour
    assert tm.modify_pos_tag('V41;M3H-faU;---', ['ISTIQBAL;S']) == 'V41;M3H-faU;-S-'
    assert tm.modify_pos_tag('V41;M3H-paU;---', ['ISTIQBAL;S']) is None  # not future
    assert tm.modify_pos_tag('V41;M3H-paU;---', ['JAR;L']) == 'V41;M3H-paU;-L-'
    assert tm.modify_pos_tag('NJ-;M1I-;--H', ['PRONOUN;D']) is None  # attached
    assert tm.modify_pos_tag('NJ-;M1I-;---', ['PRONOUN;D']) == 'NJ-;M1I-;--L'
    assert tm.modify_pos_tag('NJ-;M1I-;---', ['PRONOUN;k']) == 'NJ-;M1I-;--k'
    assert tm.merge_pos_tag('VW1;M3H-faU;WS-', 'V31;-------;---') == 'V31;M3H-faU;WS-'
    assert tm.merge_pos_tag('VW1;M3H-faU;WS-', 'V31;--------;---') == 'VW1;M3H-faU;WS-'  # different lengths
    assert tm.merge_pos_tag('VW1;M1H-pa-;--H', 'PRD;---;---') == 'PRD;---;--H'
    assert tm.merge_pos_tag('NJ-;M1I-;W-H', 'V31;-------;---') == 'V31;-------;W-H'
    assert tm.merge_pos_tag('', 'PRD;---;---') == 'PRD;---;---'
    assert tm.get_flag('N', 'PRONOUN') == '-'
    assert tm.set_flag('N', 'PRONOUN', 'H') == 'N'
    assert tm.get_pronoun_suffix('NJ-;M1I-;--k') == 'هم'
    assert tm.get_definite_prefix('NJ-;M1I-;-LL') == 'ل'
    assert tm.get_definite_prefix('NJ-;M1I-;-BL') == 'ال'
    assert tm.set_proclitic_flags('NJ-;M1I-;WBL') == 'NJ-;M1I-;---'
    assert tm.set_majrour('NJ-;M2U-;---') == 'NJ-;M2A-;---'
    assert tm.set_majrour('NJ-;M1U-;---') == 'NJ-;M1I-;---'
    assert tm.set_tanwin('NJ-;M1U-;---') == 'NJ-;M1U-;--n'
    assert tm.is_break('NJ-;M1U-;---') and not tm.is_break('NJ-;M1U-;W--')


# --- ArabicSynthesizerTest ---

def _dummy_token(token_str):
    return AnalyzedToken(token_str, token_str, token_str)


def test_synthesize_string_string(lang):
    """ArabicSynthesizerTest.testSynthesizeStringString"""
    synth = lang.synthesizer
    assert synth.synthesize(_dummy_token('خيار'), 'NJ-;F2--;---') == ['خيارتان', 'خياريتان']
    assert synth.synthesize(_dummy_token('بلاد'), 'NJ-;F3A-;--H') == ['بلادت', 'بلادتي', 'بلاد', 'بلادي']
    # an example with specific postag with regex flag enabled
    assert synth.synthesize(_dummy_token('اِسْتَعْمَلَ'), 'V61;M3Y-pa-;--H') == ['استعملتمو']
    # an example with specific postag without regex flag
    assert synth.synthesize(_dummy_token('اِسْتَكْمَلَ'), 'V61;M3Y-pa-;---') == ['استكملتم']
    # an example with specific postag without regex flag + code flag
    assert synth.synthesize(_dummy_token('اِسْتَمَعَ'), 'V51;M3Y-pa-;---') == ['استمعتم']


def test_synthesizer_details(lang):
    """ArabicSynthesizer: proclitics added to the synthesized stems, POS tag
    regular expressions, the inflection helpers"""
    synth = lang.synthesizer
    assert synth.synthesize(_dummy_token('بلاد'), 'NJ-;F3I-;WBL') == []  # the dictionary has no affixes
    # correct_tag does not remove the jar flag
    assert synth.synthesize(_dummy_token('بلاد'), 'NJ-;F3I-;WBL', True) == []
    forms = synth.synthesize(AnalyzedToken('x', None, 'بلاد'), 'NJ-;F3I-;---')
    assert forms[:2] == ['بلاد', 'بلادات']
    assert synth.synthesize(AnalyzedToken('x', None, 'بلاد'), 'NJ-;F3I-;W-L', True) == ['وال' + f for f in forms]
    assert synth.correct_tag('NJ-;F3I-;W-L') == 'NJ-;F3I-;---'
    assert synth.correct_tag('NJ-;F3I-;W-k') == 'NJ-;F3I-;---'  # not attached (H): the article is removed
    assert synth.get_pos_tag_correction('V41;M3H-faU;W-H') == 'V41;M3H-faU;--H'
    assert synth.correct_stem('بلاده', 'NJ-;F3I-;-BH') == 'ببلاد'
    assert synth.inflect_lemma_like('غير موجود', AnalyzedToken('بلاد', 'NJ-;F3I-;---', 'بلاد')) == ['[غير موجود]']
    source = tagger_reading(lang, 'يقومون', 'قَامَ')
    assert synth.inflect_lemma_like('عَمِلَ', source) == ['يعملون']
    # the first synthesized form
    assert synth.set_enclitic_multiple(AnalyzedToken('بلاد', 'NJ-;F3I-;---', 'بلاد'), 'هم') == [
        'بلاداتهم', 'بلادتهم', 'بلادهم', 'بلادياتهم']
    assert synth.set_enclitic(AnalyzedToken('بلاد', 'NJ-;F3I-;---', 'بلاد'), 'هم') == 'بلاداتهم'
    assert synth.set_enclitic(AnalyzedToken('بلاد', '', 'بلاد'), 'هم') == '(بلاد)'
    assert synth.set_procletic(AnalyzedToken('بلادهم', 'NJ-;F3I-;--H', 'بلاد'), 'و') == 'وبلاداتهم'
    assert synth.set_jar_procletic(AnalyzedToken('البلاد', 'NJ-;F3I-;--L', 'بلاد'), 'ب') == 'بالبلاد'
    assert inflect_mafoul_mutlq('عمل') == 'عملًا'
    assert inflect_mafoul_mutlq('إجابة') == 'إجابةً'
    assert inflect_adjective_tanwin_nasb('جيد', False) == 'جيدًا'
    assert inflect_adjective_tanwin_nasb('جيد', True) == 'جيدةً'
    assert inflect_adjective_tanwin_nasb('جيدة', False) == 'جيد'


def tagger_reading(lang, word, lemma):
    return next(r for r in lang.tagger.tag(word).readings if r.lemma == lemma)


# --- ArabicSRXSentenceTokenizerTest ---

def test_sentence_tokenizer(lang):
    """ArabicSRXSentenceTokenizerTest.test"""
    stokenizer = lang.sentence_tokenizer

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('مشوار التعلم طويل.')
    test_split('هل ستنام الليلة؟')
    test_split('قُل: توْأمٌ، وتوْأمانِ: وقلْ: هذانِ توْأمانِ.. ')
    test_split('قلْ: هذِهِ توْأمُ «هذا»، (وقلْ: هذِهِ توْأمةُ هذا)، وقلْ: هذانِ توْأمٌ!')


# --- ArabicWordTokenizer ---

def test_word_tokenizer():
    """ArabicWordTokenizer: the default tokenizing characters plus the Arabic
    comma, question mark and semicolon and '-'"""
    tokenizer = ArabicWordTokenizer()
    assert tokenizer.tokenize('نعم،لا؟هذا؛ذاك-هنا') == ['نعم', '،', 'لا', '؟', 'هذا', '؛', 'ذاك', '-', 'هنا']


# --- ArabicNumbersWords, ArabicUnitsHelper, ArabicWordMaps ---

def test_numbers_words():
    assert numbers.number_to_arabic_words('0') == 'صفر'
    assert numbers.number_to_arabic_words('2', False, True, 'jar') == 'اثنين'
    assert numbers.number_to_arabic_words('34', False, True, 'jar') == 'أربعة وثلاثين'
    assert numbers.number_to_arabic_words('125') == 'مائة وخمسة وعشرون'
    assert numbers.number_to_arabic_words('1922', False, True, 'jar') == 'ألف وتسعمائة واثنين وعشرين'
    assert numbers.number_to_arabic_words('10000') == 'عشرة آلاف'
    # BigDecimal arithmetic: 10.5 thousands is not in [3, 10]
    assert numbers.number_to_arabic_words('10500') == 'عشرة ألفاً وخمسمئة'
    assert numbers.number_to_arabic_words('2000') == 'ألفان'
    assert numbers.number_to_arabic_words('1245701', False, True, 'jar') == \
        'مليون ومئتين وخمسة وأربعين ألفاً وسبعمائة وواحد'
    assert numbers.text_to_number('خمسمئة وثلاث وعشرون') == 523
    assert numbers.text_to_number('مليون ومئتان وخمسة وأربعين ألفاً وسبعمائة وواحد') == 1245701
    assert numbers.text_to_number('عشرة وآلاف') == 10000
    assert numbers.check_numeric_phrase('مائة وخمسة وعشرون', False, True, '')
    assert numbers.get_suggestions_numeric_phrase('مائة وخمسة وعشرين', False, True, '') == [
        'مائة وخمسة وعشرون', 'مائة وخمسة وعشرين']
    assert numbers.number_to_words_with_units(3, 'دينار', 'jar') == 'ثلاثة دنانيرَ'
    assert numbers.number_to_words_with_units(11, 'دينار', '') == 'أحد عشر دينارًا'
    assert numbers.number_to_words_with_units(101, 'ليرة', '') == 'مائة ليرةٍ وليرة'
    assert numbers.get_unit_form(2, 'درهم', 'jar') == 'درهمين'
    assert numbers.get_form('سنة', 'one', '') == '[[سنة]]'
    assert numbers.is_feminin('ليرة') and not numbers.is_feminin('دينار')
    assert get_attached_pronoun('هي') == 'ها'
    assert get_attached_pronoun('كتاب') == '' and get_attached_pronoun(None) == ''
