"""Port of org.languagetool.rules.sk.SlovakTest (LanguageSpecificTest),
org.languagetool.rules.sk.CompoundRuleTest,
org.languagetool.rules.sk.LanguageSpecificSpellcheckerTest,
org.languagetool.tokenizers.sk.SlovakSentenceTokenizerTest,
org.languagetool.tagging.sk.SlovakTaggerTest and
org.languagetool.synthesis.sk.SlovakSynthesizerTest, plus checks of the
Slovak language definition against org.languagetool.language.Slovak. The
language independent parts of LanguageSpecificTest.runTests are ported in
tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.sk.rules import CompoundRule
from langtool.messages import messages_for
from langtool.synthesis import BaseSynthesizer
from langtool.tagging import BaseTagger
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('sk')


def test_language():
    """SlovakTest.testLanguage: the demo text is commented out in Java (it is
    outdated), so only the language independent checks of runTests remain"""
    assert JLanguageTool(get_language('sk')).check('Toto je jednoduchá veta.') == []


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.sk.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('sk')
    assert lang.code == 'sk-SK'
    assert get_language('sk-SK') is lang
    assert lang.name == 'Slovak'
    assert lang.countries == ['SK']
    assert isinstance(lang.disambiguator, DemoDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert type(lang.word_tokenizer) is WordTokenizer
    tagger = lang.tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    assert isinstance(lang.synthesizer, BaseSynthesizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['sk', 'grammar.xml'], ['sk', 'grammar-typography.xml']]


def test_relevant_rules():
    lang = get_language('sk-SK')
    rules = lang.get_relevant_rules(messages_for('sk'))
    # getRelevantRules without MorfologikSlovakSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS', 'UPPERCASE_SENTENCE_START',
        'WORD_REPEAT_RULE', 'WHITESPACE_RULE', 'SK_COMPOUNDS']
    assert rules[2].start_symbols == ['[', '(', '{', '„', '»', '«', '"']
    assert rules[2].end_symbols == [']', ')', '}', '“', '«', '»', '"']
    assert isinstance(rules[-1], CompoundRule)
    assert not unsupported_components(lang)


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule():
    """CompoundRuleTest.testRule"""
    lang = get_language('sk')
    lt = JLanguageTool(lang)
    rule = CompoundRule(messages_for('en'), lang, None)
    # correct:
    _check(lt, rule, 0, 'česko-slovenský')
    _check(lt, rule, 0, 'rakúsko-uhorský')
    # incorrect:
    _check(lt, rule, 1, 'bim bam', 'bim-bam')


def test_compound_rule_properties():
    lang = get_language('sk')
    rule = CompoundRule(messages_for('sk'), lang)
    assert rule.get_id() == 'SK_COMPOUNDS'
    assert rule.get_description() == 'Slová so spojovníkom napr. použite „česko-slovenský” namiesto „česko slovenský”'
    m, = rule.match(JLanguageTool(lang).get_analyzed_sentence('To je bim bam.'))
    assert m.message == 'Toto slovo sa zvyčajne píše so spojovníkom.'
    assert m.short_message == 'Problém spájania slov'


# --- SlovakTaggerTest ---

def _null(s):
    return 'null' if s is None else s


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    # (getNoWhitespaceTokens: only the tokens with a letter or digit)
    tokens = [t for t in tokenizer.tokenize(text) if any(is_letter(c) or is_digit(c) for c in t)]
    out = []
    for r in tagger.tag(tokens):
        out.append('|'.join(sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in r.readings)))
    assert ' -- '.join(out) == expected


def test_dictionary():
    """SlovakTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    d = get_language('sk').tagger.dictionary
    assert sum(1 for _ in d.iter_all()) > 0


def test_tagger():
    """SlovakTaggerTest.testTagger"""
    tagger = get_language('sk').tagger
    tokenizer = WordTokenizer()
    _my_assert('Tu nájdete vybrané čísla a obsahy časopisu Kultúra slova.',
               'Tu/[tu]J|Tu/[tu]PD|Tu/[tu]T -- nájdete/[nájsť]VKdpb+ -- vybrané/[vybraný]Gtfp1x|'
               'vybrané/[vybraný]Gtfp4x|vybrané/[vybraný]Gtfp5x|vybrané/[vybraný]Gtip1x|vybrané/[vybraný]Gtip4x|'
               'vybrané/[vybraný]Gtip5x|vybrané/[vybraný]Gtnp1x|vybrané/[vybraný]Gtnp4x|vybrané/[vybraný]Gtnp5x|'
               'vybrané/[vybraný]Gtns1x|vybrané/[vybraný]Gtns4x|vybrané/[vybraný]Gtns5x -- čísla/[číslo]SSnp1|'
               'čísla/[číslo]SSnp4|čísla/[číslo]SSnp5|čísla/[číslo]SSns2 -- a/[a]J|a/[a]O|a/[a]Q|a/[a]SUnp1|'
               'a/[a]SUnp2|a/[a]SUnp3|a/[a]SUnp4|a/[a]SUnp5|a/[a]SUnp6|a/[a]SUnp7|a/[a]SUns1|a/[a]SUns2|'
               'a/[a]SUns3|a/[a]SUns4|a/[a]SUns5|a/[a]SUns6|a/[a]SUns7|a/[a]T|a/[a]W|a/[as]W -- '
               'obsahy/[obsah]SSip1|obsahy/[obsah]SSip4|obsahy/[obsah]SSip5 -- časopisu/[časopis]SSis2|'
               'časopisu/[časopis]SSis3 -- Kultúra/[kultúra]SSfs1|Kultúra/[kultúra]SSfs5 -- slova/[slovo]SSns2',
               tokenizer, tagger)
    _my_assert('blabla', 'blabla/[null]null', tokenizer, tagger)


# --- SlovakSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string():
    """SlovakSynthesizerTest.testSynthesizeStringString"""
    synth = get_language('sk').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('časopis'), 'SSis2') == ['časopisu']
    # with regular expressions
    assert synth.synthesize(_dummy_token('časopis'), 'SS.*', True) == [
        'časopisy', 'časopisov', 'časopisom', 'časopisy', 'časopisy', 'časopisoch', 'časopismi', 'časopis',
        'časopisu', 'časopisu', 'časopis', 'časopis', 'časopise', 'časopisom']


# --- SlovakSentenceTokenizerTest ---

def _stokenizer(single_line_breaks_marks_paragraph):
    st = SRXSentenceTokenizer(get_language('sk'))
    st.set_single_line_breaks_marks_paragraph(single_line_breaks_marks_paragraph)
    return st


def _test_split_with(stokenizer, *sentences):
    # TestTools.testSplit
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


def _test_split(*sentences):
    _test_split_with(_stokenizer(False), *sentences)


def test_tokenize():
    """SlovakSentenceTokenizerTest.testTokenize"""
    # accept \n as paragraph:
    stokenizer = _stokenizer(True)
    # accept only \n\n as paragraph:
    stokenizer2 = _stokenizer(False)

    _test_split('This is a sentence. ')

    # NOTE: sentences here need to end with a space character so they
    # have correct whitespace when appended:
    _test_split('Dies ist ein Satz.')
    _test_split('Dies ist ein Satz. ', 'Noch einer.')
    _test_split('Ein Satz! ', 'Noch einer.')
    _test_split('Ein Satz... ', 'Noch einer.')
    _test_split('Unter http://www.test.de gibt es eine Website.')

    _test_split('Das ist,, also ob es bla.')
    _test_split('Das ist es.. ', 'So geht es weiter.')

    _test_split('Das hier ist ein(!) Satz.')
    _test_split('Das hier ist ein(!!) Satz.')
    _test_split('Das hier ist ein(?) Satz.')
    _test_split('Das hier ist ein(???) Satz.')
    _test_split('Das hier ist ein(???) Satz.')

    # ganzer Satz kommt oder nicht:
    _test_split('Das war es: gar nichts.')
    _test_split('Das war es: Dies ist ein neuer Satz.')

    # incomplete sentences, need to work for on-thy-fly checking of texts:
    _test_split("Here's a")
    _test_split("Here's a sentence. ", "And here's one that's not comp")

    _test_split('„Prezydent jest niemądry”. ', 'Tak wyszło.')
    _test_split('„Prezydent jest niemądry”, powiedział premier')

    _test_split('Das Schreiben ist auf den 3.10. datiert.')
    _test_split('Das Schreiben ist auf den 31.1. datiert.')
    _test_split('Das Schreiben ist auf den 3.10.2000 datiert.')
    _test_split('Toto 2. vydanie bolo rozobrané za 1,5 roka.')
    _test_split('Festival Bažant Pohoda slávi svoje 10. výročie.')
    _test_split('Dlho odkladané parlamentné voľby v Angole sa uskutočnia 5. septembra.')
    _test_split('Das in Punkt 3.9.1 genannte Verhalten.')

    # From the abbreviation list:
    _test_split('Aké sú skutočné príčiny tzv. transformačných príznakov?')
    _test_split('Aké príplatky zamestnancovi (napr. za nadčas) stanovuje Zákonník práce?')
    _test_split('Počas neprítomnosti zastupuje MUDr. Marianna Krupšová.')
    _test_split('Staroveký Egypt vznikol okolo r. 3150 p.n.l. (tzn. 3150 pred Kr.). ',
                'A zanikol v r. 31 pr. Kr.')

    # from user bug reports:
    _test_split('Temperatura wody w systemie wynosi 30°C.',
                'W skład obiegu otwartego wchodzi zbiornik i armatura.')
    _test_split('Zabudowano kolumny o długości 45 m. ',
                'Woda z ujęcia jest dostarczana do zakładu.')

    # two-letter initials:
    _test_split('Najlepszym polskim reżyserem był St. Różewicz. ', 'Chodzi o brata wielkiego poety.')
    _test_split('Nore M. hrozí za podvod 10 až 15 rokov.')
    _test_split('To jest zmienna A.', 'Zaś to jest zmienna B.')
    # Numbers with dots.
    _test_split('Mam w magazynie dwie skrzynie LMD20. ', 'Jestem żołnierzem i wiem, jak można ich użyć')
    # ellipsis
    _test_split('Rytmem tej wiecznie przemijającej światowej egzystencji […] rytmem mesjańskiej natury jest '
                'szczęście.')

    # Tests taken from LanguageTool's SentenceSplitterTest.py:
    _test_split('This is a sentence. ')
    _test_split('This is a sentence. ', 'And this is another one.')
    _test_split('This is a sentence.', "Isn't it?", 'Yes, it is.')

    _test_split("Don't split strings like U. S. A. either.")
    _test_split("Don't split strings like U.S.A. either.")
    _test_split("Don't split... ", 'Well you know. ', 'Here comes more text.')
    _test_split("Don't split... well you know. ", 'Here comes more text.')
    _test_split('The "." should not be a delimiter in quotes.')
    _test_split('"Here he comes!" she said.')
    _test_split('"Here he comes!", she said.')
    _test_split('"Here he comes." ', 'But this is another sentence.')
    _test_split('"Here he comes!". ', "That's what he said.")
    _test_split('The sentence ends here. ', '(Another sentence.)')
    # known to fail:
    # _test_split("He won't. ", 'Really.')
    _test_split("He won't go. ", 'Really.')
    _test_split("He won't say no.", 'Not really.')
    _test_split('This is it: a test.')
    # one/two returns = paragraph = new sentence:
    _test_split_with(stokenizer2, "He won't\n\n", 'Really.')
    _test_split_with(stokenizer, "He won't\n", 'Really.')
    _test_split_with(stokenizer2, "He won't\n\n", 'Really.')
    _test_split_with(stokenizer2, "He won't\nReally.")
    # Missing space after sentence end:
    _test_split('James is from the Ireland!', 'He lives in Spain now.')
