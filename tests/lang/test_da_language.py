"""Port of org.languagetool.rules.da.DanishTest (LanguageSpecificTest),
org.languagetool.rules.da.DanishSpellerRuleTest,
org.languagetool.rules.da.LanguageSpecificSpellcheckerTest and
org.languagetool.tokenizers.da.DanishSRXSentenceTokenizerTest, plus checks of
the Danish language definition against org.languagetool.language.Danish and
DanishTagger. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.messages import messages_for
from langtool.tagging import BaseTagger
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('da')


def test_demo_text():
    """DanishTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Indsæt din egen tekst her , eller brug denne tekst for at se nogle af de fejl LanguageTool fanger. '
         'vær opmærksom på at den langtfra er er perfect, men skal være en hjælp til at få standartfejl frem '
         'i lyset.')
    matches = JLanguageTool(get_language('da')).check(s)
    # Java expects "COMMA_PARENTHESIS_WHITESPACE", "UPPERCASE_SENTENCE_START", "Ordgentagelse",
    # "HUNSPELL_RULE", "standart_standard"; HUNSPELL_RULE (for "perfect") is the spell checker,
    # which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'UPPERCASE_SENTENCE_START', 'Ordgentagelse', 'standart_standard']


def test_dash_and_hyphen_etc():
    """DanishSpellerRuleTest.testDashAndHyphenEtc (the speller itself is not
    ported, the other rules must not match either)"""
    assert JLanguageTool(get_language('da')).check('De står under ----') == []


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.da.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('da')
    assert lang.code == 'da-DK'
    assert get_language('da-DK') is lang
    assert lang.name == 'Danish'
    assert lang.countries == ['DK']
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)


def test_tagger():
    """DanishTagger: BaseTagger for /da/danish.dict"""
    tagger = get_language('da-DK').tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    readings = tagger.tag(['Vi', 'går', 'huset'])
    assert [[(t.lemma, t.pos_tag) for t in r.readings] for r in readings] == [
        [('Vi', 'pro:nom'), ('vi', 'pron:plu:nom'), ('vi', 'sub:ube:sin:neu:nom'), ('vi', 'ver:imp:akt'),
         ('vi', 'ver:inf:akt')],
        [(None, None)],  # not in the dictionary (same in Java)
        [('huse', 'ver:kor:akt'), ('hus', 'sub:bes:sin:neu:nom')]]


def test_relevant_rules():
    lang = get_language('da-DK')
    rules = lang.get_relevant_rules(messages_for('da'))
    # getRelevantRules without HunspellRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
                                          'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE']
    assert rules[2].start_symbols == ['[', '(', '{', '"', '”']
    assert rules[2].end_symbols == [']', ')', '}', '"', '”']
    assert not unsupported_components(lang)


def _test_split(*sentences):
    # TestTools.testSplit
    stokenizer = SRXSentenceTokenizer(get_language('da'))
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


def test_tokenize():
    """DanishSRXSentenceTokenizerTest.testTokenize"""
    # NOTE: sentences here need to end with a space character so they
    # have correct whitespace when appended:
    _test_split('Dette er en sætning.')
    _test_split('Dette er en sætning. ', 'Her er den næste.')
    _test_split('En sætning! ', 'Yderlige en.')
    _test_split('En sætning... ', 'Yderlige en.')
    _test_split('På hjemmesiden http://www.stavekontrolden.dk bygger vi stavekontrollen.')
    _test_split('Den 31.12. går ikke!')
    _test_split('Den 3.12.2011 går ikke!')
    _test_split('I det 18. og tidlige 19. århundrede hentede amerikansk kunst det meste af sin inspiration fra '
                'Europa.')

    _test_split('Hendes Majestæt Dronning Margrethe II (Margrethe Alexandrine Þórhildur Ingrid, Danmarks dronning) '
                '(født 16. april 1940 på Amalienborg Slot) er siden 14. januar 1972 Danmarks regent.')
    _test_split("Hun har residensbolig i Christian IX's Palæ på Amalienborg Slot.")
    _test_split("Tronfølgeren ledte herefter statsrådsmøderne under Kong Frederik 9.'s fravær.")
    _test_split('Marie Hvidt, Frederik IV - En letsindig alvorsmand, Gads Forlag, 2004.')
    _test_split('Da vi første gang besøgte Restaurant Chr. IV, var vi de eneste gæster.')

    _test_split('I dag er det den 25.12.2010.')
    _test_split('I dag er det d. 25.12.2010.')
    _test_split('I dag er den 13. december.')
    _test_split('Arrangementet starter ca. 17:30 i dag.')
    _test_split('Arrangementet starter ca. 17:30.')
    _test_split('Det er nævnt i punkt 3.6.4 Rygbelastende helkropsvibrationer.')

    _test_split('Rent praktisk er det også lettest lige at mødes, så der kan udveksles nøgler og brugsanvisninger '
                'etc.')
    _test_split('Andre partier incl. borgerlige partier har deres særlige problemer: nogle samarbejder med '
                'apartheidstyret i Sydafrika, med NATO-landet Tyrkiet etc., men det skal så sandelig ikke begrunde '
                'en SF-offensiv for et samarbejde med et parti.')

    _test_split('Hvad nu,, den bliver også.')
    _test_split('Det her er det.. ', 'Og her fortsætter det.')

    _test_split('Dette er en(!) sætning.')
    _test_split('Dette er en(!!) sætning.')
    _test_split('Dette er en(?) sætning.')
    _test_split('Dette er en(??) sætning.')
    _test_split('Dette er en(???) sætning.')
    _test_split('Militær værnepligt blev indført (traktaten krævede, at den tyske hær ikke oversteg 100.000 mand).')

    _test_split('Siden illustrerede hun "Historierne om Regnar Lodbrog" 1979 og "Bjarkemål" 1982 samt Poul Ørums '
                '"Komedie i Florens" 1990.')
