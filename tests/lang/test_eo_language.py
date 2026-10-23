"""Port of org.languagetool.EsperantoTest,
org.languagetool.rules.eo.EsperantoTest (LanguageSpecificTest),
org.languagetool.rules.eo.LanguageSpecificSpellcheckerTest,
org.languagetool.tagging.eo.EsperantoTaggerTest and
org.languagetool.tokenizers.eo.EsperantoWordTokenizerTest, plus checks of the
Esperanto language definition against org.languagetool.language.Esperanto,
of EsperantoTagger and of org.languagetool.rules.eo.DateCheckFilter. The
language independent parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py."""

import pytest

from langtool.api import get_language
from langtool.disambiguation import XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.eo.filters import DateCheckFilter
from langtool.lang.eo.tagging import EsperantoTagger
from langtool.lang.eo.tokenizers import EsperantoWordTokenizer
from langtool.messages import messages_for
from langtool.rules.core_filters import CalendarDate
from langtool.rules.filters import default_filter_factory
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


# --- org.languagetool.EsperantoTest ---

def test_check():
    """org.languagetool.EsperantoTest.test"""
    language = get_language('eo')
    assert len(language.countries) == 0
    matches = JLanguageTool(language).check('La Mondaj Ludoj de 2013 estis plur-sporta evento...')
    # Java expects one match of HUNSPELL_RULE (for "plur-sporta"), the spell checker, which is not ported
    assert matches == []


# --- org.languagetool.rules.eo.EsperantoTest ---

def test_demo_text():
    """org.languagetool.rules.eo.EsperantoTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Algluu vian kontrolendan tekston ĉi tie... Aŭ nur kontrolu ĉi tiun ekzemplon. Ĉu vi vi rimarkis, ke '
         'estas gramatikaj eraro en tiu frazo? Rimarku, ke Lingvoilo ankaux atentigas pri literumaj erraroj kiel '
         'ĉi-tiu.')
    matches = JLanguageTool(get_language('eo')).check(s)
    # Java expects "WORD_REPEAT_RULE", "NEKONG_NOMBR", "X_SISTEMO", "HUNSPELL_RULE", "CXI_TIU"; HUNSPELL_RULE
    # (for "erraroj") is the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == ['WORD_REPEAT_RULE', 'NEKONG_NOMBR', 'X_SISTEMO',
                                                           'CXI_TIU']
    assert [(m.from_pos, m.to_pos) for m in matches] == [(81, 86), (106, 122), (159, 165), (203, 209)]
    assert matches[3].suggested_replacements == ['ĉi tiu']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists (HunspellRule)')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.eo.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('eo')
    assert lang.code == 'eo'
    assert lang.name == 'Esperanto'
    assert lang.countries == []
    assert lang.synthesizer is None
    assert isinstance(lang.tagger, EsperantoTagger)
    assert isinstance(lang.word_tokenizer, EsperantoWordTokenizer)
    stages = lang.disambiguator.stages
    assert len(stages) == 1 and isinstance(stages[0], XmlRuleDisambiguator)
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['eo', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('eo')
    rules = lang.get_relevant_rules(messages_for('eo'))
    # getRelevantRules without HunspellRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                           'UPPERCASE_SENTENCE_START', 'WORD_REPEAT_RULE', 'WHITESPACE_RULE',
                                           'SENTENCE_WHITESPACE']
    assert not unsupported_components(lang)


# --- EsperantoTaggerTest ---

def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _as_strings(readings):
    # TestTools.getAsStrings
    return sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in readings)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    # (getNoWhitespaceTokens: only the tokens with a letter or digit)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_tagger():
    """EsperantoTaggerTest.testTagger"""
    tagger = get_language('eo').tagger
    tokenizer = WordTokenizer()
    _my_assert('Tio estas simpla testo',
               'Tio/[null]T nak np t o -- estas/[esti]V nt as -- simpla/[simpla]A nak np -- testo/[testo]O nak np',
               tokenizer, tagger)
    _my_assert('Mi malsategas',
               'Mi/[mi]R nak np -- malsategas/[malsategi]V nt as', tokenizer, tagger)
    _my_assert('Li malŝategas sin',
               'Li/[li]R nak np -- malŝategas/[malŝategi]V tr as -- sin/[si]R akz np', tokenizer, tagger)

    # An Esperanto Pangram i.e. it includes all letters of the Esperanto
    # alphabet to check that lemma gets transformed from x-system into Unicode.
    _my_assert('Sxajnas ke sagaca monahxo lauxtvocxe rifuzadis pregxi sur herbajxo',
               'Sxajnas/[ŝajni]V nt as -- '
               'ke/[ke]_ -- '
               'sagaca/[sagaca]A nak np -- '
               'monahxo/[monaĥo]O nak np -- '
               'lauxtvocxe/[laŭtvoĉe]E nak -- '
               'rifuzadis/[rifuzadi]V tr is -- '
               'pregxi/[preĝi]V nt i -- '
               'sur/[sur]P kak -- '
               'herbajxo/[herbaĵo]O nak np', tokenizer, tagger)


def _tags(tagger, word):
    r, = tagger.tag([word])
    return [(t.lemma, t.pos_tag) for t in r.readings]


def test_tagger_open_words():
    """EsperantoTagger: tabelvortoj, word endings, participles,
    transitivity, single letters and long tokens"""
    tagger = get_language('eo').tagger
    assert _tags(tagger, 'kiujn') == [(None, 'T akz pl k u')]
    assert _tags(tagger, 'ĉiuj') == [(None, 'T nak pl ĉ u')]
    assert _tags(tagger, 'tiam') == [(None, 'T xxx pn t am'), ('tiam', 'E nak')]
    assert _tags(tagger, 'neniel') == [(None, 'T xxx pn n el'), ('neniel', 'E nak')]
    assert _tags(tagger, "hom'") == [('homo', 'O nak np')]
    assert _tags(tagger, 'Domojn') == [('domo', 'O akz pl')]
    assert _tags(tagger, 'belan') == [('bela', 'A akz np')]
    assert _tags(tagger, 'hejmen') == [('hejme', 'E akz')]
    assert _tags(tagger, 'kantanta') == [('kantanta', 'A nak np'), ('kanti', 'C nak np tn a n a')]
    assert _tags(tagger, 'legitajn') == [('legita', 'A akz pl'), ('legi', 'C akz pl tr i - a')]
    assert _tags(tagger, 'manĝanto') == [('manĝanto', 'O nak np'), ('manĝi', 'C nak np tr a n o')]
    assert _tags(tagger, 'memmortigis') == [('memmortigi', 'V nt is')]
    assert _tags(tagger, 'sidigos') == [('sidigi', 'V tr os')]
    assert _tags(tagger, 'naskiĝus') == [('naskiĝi', 'V nt us')]
    assert _tags(tagger, 'ludu') == [('ludi', 'V tn u')]
    assert _tags(tagger, 'xyzzy') == [(None, None)]
    assert _tags(tagger, 'A') == [(None, None)]
    assert _tags(tagger, 'o' * 51) == [(None, None)]
    assert _tags(tagger, 'o' * 50) == [('o' * 50, 'O nak np')]
    assert tagger.create_null_token('x', 3).readings[0].pos_tag is None
    assert tagger.create_token('x', 'O nak np').pos_tag == 'O nak np'


# --- EsperantoWordTokenizerTest ---

def test_tokenize():
    """EsperantoWordTokenizerTest.testTokenize"""
    word_tokenizer = EsperantoWordTokenizer()
    test_list = word_tokenizer.tokenize('Tio estas testo')
    assert len(test_list) == 5
    assert test_list == ['Tio', ' ', 'estas', ' ', 'testo']
    test_list = word_tokenizer.tokenize("dank' al 'tio'")
    assert len(test_list) == 7
    assert test_list == ["dank'", ' ', 'al', ' ', "'", 'tio', "'"]


def test_tokenize_apostrophe_before_letter():
    """EsperantoWordTokenizer: an apostrophe followed by a letter ends the
    word (the spurious space is removed)"""
    word_tokenizer = EsperantoWordTokenizer()
    assert word_tokenizer.tokenize("l'homo kaj dank'al") == ["l'", 'homo', ' ', 'kaj', ' ', "dank'", 'al']
    assert word_tokenizer.tokenize('') == []


# --- DateCheckFilter ---

def test_date_check_filter_get_day_of_week():
    f = DateCheckFilter()
    assert f.get_day_of_week('Dimanĉo') == 1
    assert f.get_day_of_week('lundon') == 2
    assert f.get_day_of_week('mardo') == 3
    assert f.get_day_of_week('merkredo') == 4
    assert f.get_day_of_week('ĵaŭdo') == 5
    assert f.get_day_of_week('jaudo') == 5
    assert f.get_day_of_week('jhaudo') == 5
    assert f.get_day_of_week('Jxauxdo') == 5
    assert f.get_day_of_week('vendredo') == 6
    assert f.get_day_of_week('sabato') == 7
    with pytest.raises(RuntimeError):
        f.get_day_of_week('Monday')


def test_date_check_filter_get_day_of_month():
    f = DateCheckFilter()
    assert f.get_day_of_month('unua') == 1
    assert f.get_day_of_month('Naŭan') == 9
    assert f.get_day_of_month('nauxa') == 9
    assert f.get_day_of_month('naua') == 9
    assert f.get_day_of_month('deka') == 10  # "dek" + "a": no ordinal is added
    assert f.get_day_of_month('dek-unua') == 11
    assert f.get_day_of_month('dudek-trian') == 23
    assert f.get_day_of_month('dudektria') == 23
    assert f.get_day_of_month('tridek-unuan') == 31
    assert f.get_day_of_month('12') == 0


def test_date_check_filter_get_month():
    f = DateCheckFilter()
    assert f.get_month('januaro') == 1
    assert f.get_month('Majo') == 5
    assert f.get_month('aŭgusto') == 8
    assert f.get_month('dec.') == 12
    with pytest.raises(RuntimeError):
        f.get_month('August')


def test_date_check_filter_day_names():
    f = DateCheckFilter()
    assert [f.get_day_of_week_name(CalendarDate(day_of_week=d)) for d in range(1, 8)] == [
        'dimanĉo', 'lundo', 'mardo', 'merkredo', 'jaŭdo', 'vendredo', 'sabato']
    # months are 0-based as in java.util.Calendar
    assert f.get_day_of_week_name(CalendarDate.of(2014, 7, 31)) == 'dimanĉo'


def test_date_check_filter_registered():
    lang = get_language('eo')
    assert isinstance(default_filter_factory().get_filter('org.languagetool.rules.eo.DateCheckFilter', lang),
                      DateCheckFilter)
