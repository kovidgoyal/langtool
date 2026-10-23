"""Port of org.languagetool.rules.ro.RomanianTest (LanguageSpecificTest),
org.languagetool.rules.ro.SimpleReplaceRuleTest,
org.languagetool.rules.ro.CompoundRuleTest,
org.languagetool.rules.ro.GenericUnpairedBracketsRuleTest,
org.languagetool.rules.ro.LanguageSpecificSpellcheckerTest,
org.languagetool.tokenizers.ro.RomanianWordTokenizerTest,
org.languagetool.tokenizers.ro.RomanianSentenceTokenizerTest,
org.languagetool.tagging.ro.RomanianTaggerTest,
org.languagetool.tagging.ro.RomanianTaggerDiacriticsTest (both via
AbstractRomanianTaggerTest),
org.languagetool.tagging.disambiguation.rules.ro.RomanianRuleDisambiguatorTest
and org.languagetool.synthesis.ro.RomanianSynthesizerTest, plus checks of
the Romanian language definition against org.languagetool.language.Romanian
and of RomanianWordRepeatBeginningRule. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.ro.rules import CompoundRule, RomanianWordRepeatBeginningRule, SimpleReplaceRule
from langtool.lang.ro.tokenizers import RomanianWordTokenizer
from langtool.messages import messages_for
from langtool.rules.core import GenericUnpairedBracketsRule
from langtool.synthesis import BaseSynthesizer
from langtool.tagging import BaseTagger
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ro')


# --- RomanianTest ---

def test_language():
    """RomanianTest.testLanguage: runTests(new Romanian()) without a demo
    text; the language independent checks are in tests/test_jlanguagetool.py"""
    assert JLanguageTool(get_language('ro')).check('Aceasta este o propoziție.') == []


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.ro.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('ro')
    assert lang.code == 'ro-RO'
    assert get_language('ro-RO') is lang
    assert lang.name == 'Romanian'
    assert lang.countries == ['RO']
    assert lang.definition['disambiguator'] == [('xml', False)]
    stages = lang.disambiguator.stages
    assert len(stages) == 1 and isinstance(stages[0], XmlRuleDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert type(lang.word_tokenizer) is RomanianWordTokenizer
    tagger = lang.tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    synth = lang.synthesizer
    assert isinstance(synth, BaseSynthesizer)
    assert synth.number_speller is None
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['ro', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('ro')
    rules = lang.get_relevant_rules(messages_for('ro'))
    # getRelevantRules without MorfologikRomanianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE',
        'UNPAIRED_BRACKETS', 'WORD_REPEAT_RULE', 'ROMANIAN_WORD_REPEAT_BEGINNING_RULE', 'RO_SIMPLE_REPLACE',
        'RO_COMPOUND']
    brackets = rules[4]
    assert brackets.start_symbols == ['[', '(', '{', '„', '«', '»']
    assert brackets.end_symbols == [']', ')', '}', '”', '»', '«']
    assert isinstance(rules[6], RomanianWordRepeatBeginningRule)
    assert isinstance(rules[7], SimpleReplaceRule)
    assert isinstance(rules[8], CompoundRule)
    assert not unsupported_components(lang)


# --- SimpleReplaceRuleTest ---

@pytest.fixture(scope='module')
def replace_rule():
    lang = get_language('ro')
    return SimpleReplaceRule(messages_for('ro'), lang), JLanguageTool(lang)


def test_simple_replace_invalid_suggestion(replace_rule):
    """SimpleReplaceRuleTest.testInvalidSuggestion: the suggested word is not
    the same as the wrong word"""
    rule = replace_rule[0]
    invalid = []
    for rule_entry in rule.get_wrong_words():
        for from_word, (to_word, _msg) in rule_entry.items():
            if to_word is None or from_word == to_word:
                invalid.append(to_word)
    assert not invalid, 'Invalid suggestions found for: %s' % invalid


def test_simple_replace_rule(replace_rule):
    """SimpleReplaceRuleTest.testRule"""
    rule, lt = replace_rule

    def check(sentence, *words):
        matches = rule.match(lt.get_analyzed_sentence(sentence))
        assert len(matches) == len(words), 'Invalid matches.length while checking sentence: ' + sentence
        for m, word in zip(matches, words):
            assert m.suggested_replacements == word.split('/'), sentence

    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Paisprezece case.'))) == 0
    # incorrect sentences:
    # at the beginning of a sentence (Romanian replace rule is case-sensitive)
    check('Patrusprezece case.', 'Paisprezece')
    # inside sentence
    check('Satul are patrusprezece case.', 'paisprezece')
    check('Satul are (patrusprezece) case.', 'paisprezece')
    check('Satul are «patrusprezece» case.', 'paisprezece')
    check('El are șasesprezece ani.', 'șaisprezece')
    check('El a luptat pentru întâiele cărți.', 'întâile')
    check('El are cinsprezece cărți.', 'cincisprezece')
    check('El a fost patruzecioptist.', 'pașoptist')
    check('M-am adresat întâiei venite.', 'întâii')
    check('M-am adresat întâielor venite.', 'întâilor')
    check('A ajuns al douăzecelea.', 'douăzecilea')
    check('A ajuns al zecilea.', 'zecelea')
    check('A primit jumate de litru de lapte.', 'jumătate')
    # multiple words / compounds
    # space-delimited
    check('aqua forte', 'Acvaforte')
    check('aqua forte.', 'Acvaforte')
    check('A folosit «aqua forte».', 'acvaforte')
    check('Aqua forte.', 'Acvaforte')
    check('este aqua forte', 'acvaforte')
    check('este aqua forte.', 'acvaforte')
    check('este Aqua Forte.', 'Acvaforte')
    check('este AquA Forte.', 'acvaforte')
    check('A primit jumate de litru de lapte și este aqua forte.', 'jumătate', 'acvaforte')
    check('du-te vino', 'Du-te-vino')
    # dash-delimited
    check('cou-boi', 'Cowboy')
    check('cow-boy', 'Cowboy')
    check('cau-boi', 'Cowboy')
    check('Cau-boi', 'Cowboy')
    check('cowboy')  # correct, no replacement
    check('Iată un cau-boi', 'cowboy')
    check('Iată un cau-boi.', 'cowboy')
    check('Iată un (cau-boi).', 'cowboy')
    check('văcar=cau-boi', 'cowboy')
    # multiple suggestions
    check('A fost adăogită o altă regulă.', 'adăugită/adăugată')
    check('A venit adinioarea.', 'adineaori/adineauri')
    # words with multiple wrong forms
    check('A pus axterix.', 'asterisc')
    check('A pus axterics.', 'asterisc')
    check('A pus asterics.', 'asterisc')


def test_simple_replace_rule_properties(replace_rule):
    rule, lt = replace_rule
    assert rule.get_id() == 'RO_SIMPLE_REPLACE'
    assert rule.get_description() == 'Cuvinte sau grupuri de cuvinte incorecte sau ieșite din uz'
    assert rule.get_short() == 'Cuvânt incorect sau ieșit din uz'
    assert rule.category.id == 'MISC'
    m, = rule.match(lt.get_analyzed_sentence('A fost adăogită o altă regulă.'))
    assert m.message == ("'adăogită' este incorect sau ieșit din uz, folosiți <suggestion>adăugită</suggestion> "
                         "sau <suggestion>adăugată</suggestion>")


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule():
    """CompoundRuleTest.testRule"""
    lang = get_language('ro')
    lt = JLanguageTool(lang)
    rule = CompoundRule(messages_for('ro'), lang, None)
    # correct sentences:
    _check(lt, rule, 0, 'Au plecat câteșitrei.')
    # incorrect sentences:
    _check(lt, rule, 1, 'câte și trei', 'câteșitrei')
    _check(lt, rule, 1, 'Câte și trei', 'Câteșitrei')
    _check(lt, rule, 1, 'câte-și-trei', 'câteșitrei')
    _check(lt, rule, 1, 'tus trei', 'tustrei')
    _check(lt, rule, 1, 'tus-trei', 'tustrei')


def test_compound_rule_properties():
    lang = get_language('ro')
    rule = CompoundRule(messages_for('ro'), lang)
    assert rule.get_id() == 'RO_COMPOUND'
    assert rule.get_description() == 'Greșeală de scriere (cuvinte scrise legat sau cu cratimă)'
    m, = rule.match(JLanguageTool(lang).get_analyzed_sentence('Au plecat tus trei.'))
    assert m.message == 'Cuvântul se scrie legat.'
    assert m.short_message == 'Problemă de scriere (cratimă, spațiu, etc.)'


# --- GenericUnpairedBracketsRuleTest ---

def test_romanian_brackets_rule():
    """GenericUnpairedBracketsRuleTest.testRomanianRule"""
    lt = JLanguageTool(get_language('ro'))
    # GenericUnpairedBracketsRuleTest.getBracketsRule
    rule, = [r for r in lt.get_all_active_rules() if isinstance(r, GenericUnpairedBracketsRule)]

    def assert_matches(text, expected):
        assert len(rule.match([lt.get_analyzed_sentence(text)])) == expected, text

    # correct sentences:
    assert_matches('A fost plecat (pentru puțin timp).', 0)
    assert_matches("Nu's de prin locurile astea.", 0)
    assert_matches('A fost plecat pentru „puțin timp”.', 0)
    assert_matches('A fost plecat „pentru... puțin timp”.', 0)
    assert_matches('A fost plecat „pentru... «puțin» timp”.', 0)
    # correct sentences ( " is _not_ a Romanian symbol - just
    # ignore it, the correct form is [„] (start quote) and [”] (end quote)
    assert_matches('A fost plecat "pentru puțin timp.', 0)
    # incorrect sentences:
    assert_matches('A fost )plecat( pentru (puțin timp).', 2)
    assert_matches('A fost {plecat) pentru (puțin timp}.', 4)
    assert_matches('A fost plecat „pentru... puțin timp.', 1)
    assert_matches('A fost plecat «puțin.', 1)
    assert_matches('A fost plecat „pentru «puțin timp”.', 1)
    assert_matches('A fost plecat „pentru puțin» timp”.', 1)
    assert_matches('A fost plecat „pentru... puțin» timp”.', 1)
    assert_matches('A fost plecat „pentru... «puțin” timp».', 4)


# --- RomanianWordRepeatBeginningRule ---

def test_word_repeat_beginning_rule():
    lang = get_language('ro')
    lt = JLanguageTool(lang)
    rule = RomanianWordRepeatBeginningRule(messages_for('ro'), lang)
    assert rule.get_id() == 'ROMANIAN_WORD_REPEAT_BEGINNING_RULE'
    assert not rule.allow_ambiguous_adverbs()
    # "Acum" is only an adverb: a match for the second sentence already
    adv = lt.get_analyzed_sentence('Acum el vine.').non_blank_tokens[1]
    assert [r.pos_tag for r in adv.readings] == ['G00000p00t']
    assert rule.is_adverb(adv)
    m, = rule.match(lt.analyze_text('Acum el vine acasă. Acum ea pleacă la școală.'))
    assert (m.from_pos, m.to_pos) == (20, 24)
    assert m.short_message == messages_for('ro')['desc_repetition_beginning_adv']
    # "Și" has other readings besides the adverb ones: not an adverb, a match
    # only for three sentences in a row
    si = lt.get_analyzed_sentence('Și el vine.').non_blank_tokens[1]
    tags = [r.pos_tag for r in si.readings]
    assert any(t.startswith('G') for t in tags) and not all(t.startswith('G') for t in tags)
    assert not rule.is_adverb(si)
    assert rule.match(lt.analyze_text('Și el vine acasă. Și ea pleacă la școală.')) == []
    m, = rule.match(lt.analyze_text('Și el vine acasă. Și ea pleacă la școală. Și eu rămân aici.'))
    assert m.short_message == messages_for('ro')['desc_repetition_beginning_word']


# --- RomanianWordTokenizerTest ---

def test_word_tokenizer():
    """RomanianWordTokenizerTest.testTokenize"""
    w = RomanianWordTokenizer()
    # basic test - simple words, no diacritics
    assert w.tokenize('Aceaste mese sunt bune') == ['Aceaste', ' ', 'mese', ' ', 'sunt', ' ', 'bune']
    # basic test - simle words, with diacritics
    assert w.tokenize('Această carte este frumoasă') == ['Această', ' ', 'carte', ' ', 'este', ' ', 'frumoasă']
    # test for "-"
    assert w.tokenize('nu-ți doresc') == ['nu', '-', 'ți', ' ', 'doresc']
    # test for "„"
    assert w.tokenize('zicea „merge') == ['zicea', ' ', '„', 'merge']
    # test for "„" with white space
    assert w.tokenize('zicea „ merge') == ['zicea', ' ', '„', ' ', 'merge']
    # test for "„"
    assert w.tokenize('zicea merge”') == ['zicea', ' ', 'merge', '”']
    # test for "„" and "„"
    assert w.tokenize('zicea „merge bine”') == ['zicea', ' ', '„', 'merge', ' ', 'bine', '”']
    # ți-am
    assert w.tokenize('ți-am') == ['ți', '-', 'am']
    # test for "«" and "»"
    assert w.tokenize('zicea «merge bine»') == ['zicea', ' ', '«', 'merge', ' ', 'bine', '»']
    # test for "<" and ">"
    assert w.tokenize('zicea <<merge bine>>') == ['zicea', ' ', '<', '<', 'merge', ' ', 'bine', '>', '>']
    # test for "%"
    assert w.tokenize('avea 15% apă') == ['avea', ' ', '15', '%', ' ', 'apă']
    # test for "°"
    assert w.tokenize('are 30°C') == ['are', ' ', '30', '°', 'C']
    # test for "="
    assert w.tokenize('fructe=mere') == ['fructe', '=', 'mere']
    # test for "|"
    assert w.tokenize('pere|mere') == ['pere', '|', 'mere']
    # test for "\n"
    assert w.tokenize('pere\nmere') == ['pere', '\n', 'mere']
    # test for "\r"
    assert w.tokenize('pere\rmere') == ['pere', '\r', 'mere']
    # test for "\n\r"
    assert w.tokenize('pere\n\rmere') == ['pere', '\n', '\r', 'mere']
    # test for URLs
    assert len(w.tokenize('www.LanguageTool.org')) == 1


# --- RomanianSentenceTokenizerTest ---

def _stokenizer(single_line_breaks_marks_paragraph):
    st = SRXSentenceTokenizer(get_language('ro'))
    st.set_single_line_breaks_marks_paragraph(single_line_breaks_marks_paragraph)
    return st


def _test_split_with(stokenizer, *sentences):
    # TestTools.testSplit
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


def test_sentence_tokenize():
    """RomanianSentenceTokenizerTest.testTokenize"""
    # accept \n as paragraph:
    stokenizer = _stokenizer(True)
    # accept only \n\n as paragraph:
    stokenizer2 = _stokenizer(False)

    def test_split(*sentences):
        _test_split_with(stokenizer2, *sentences)

    test_split('Aceasta este o propozitie fara diacritice. ')
    test_split('Aceasta este o fraza fara diacritice. ', 'Propozitia a doua, tot fara diacritice. ')
    test_split('Aceasta este o propoziție cu diacritice. ')
    test_split('Aceasta este o propoziție cu diacritice. ', 'Propoziția a doua, cu diacritice. ')
    test_split('O propoziție! ', 'Și încă o propoziție. ')
    test_split('O propoziție... ', 'Și încă o propoziție. ')
    test_split('La adresa http://www.archeus.ro găsiți resurse lingvistice. ')
    test_split('Data de 10.02.2009 nu trebuie să fie separator de propoziții. ')
    test_split('Astăzi suntem în data de 07.05.2007. ')
    test_split('Astăzi suntem în data de 07/05/2007. ')
    test_split('La anumărul (1) avem puține informații. ')
    test_split('To jest 1. wydanie.')
    test_split('La anumărul 1. avem puține informații. ')
    test_split('La anumărul 13. avem puține informații. ')
    test_split('La anumărul 1.3.3 avem puține informații. ')
    test_split('O singură propoziție... ')
    test_split('Colegii mei s-au dus... ')
    test_split('O singură propoziție!!! ')
    test_split('O singură propoziție??? ')
    test_split('Propoziții: una și alta. ')
    test_split("Domnu' a plecat. ")
    test_split("Profu' de istorie tre' să predea lecția. ")
    test_split("Sal'tare! ")
    test_split("'Neaţa! ")
    test_split("Deodat'apare un urs. ")
    # accente
    test_split('A făcut două cópii. ')
    test_split('Ionel adúnă acum ceea ce Maria aduná înainte să vin eu. ')
    # incomplete sentences, need to work for on-thy-fly checking of texts:
    test_split("Domnu' a plecat")
    test_split("Domnu' a plecat. ", 'El nu a plecat')
    test_split('Se pot întâlni și abrevieri precum S.U.A. sau B.C.R. într-o singură propoziție.')
    test_split('Se pot întâlni și abrevieri precum S.U.A. sau B.C.R. ', 'Aici sunt două propoziții.')
    test_split('Același lucru aici... ', 'Aici sunt două propoziții.')
    test_split('Același lucru aici... dar cu o singură propoziție.')
    test_split('„O propoziție!” ', 'O alta.')
    test_split('„O propoziție!!!” ', 'O alta.')
    test_split('„O propoziție?” ', 'O alta.')
    test_split('„O propoziție?!?” ', 'O alta.')
    test_split('«O propoziție!» ', 'O alta.')
    test_split('«O propoziție!!!» ', 'O alta.')
    test_split('«O propoziție?» ', 'O alta.')
    test_split('«O propoziție???» ', 'O alta.')
    test_split('«O propoziție?!?» ', 'O alta.')
    test_split('O primă propoziție. ', '(O alta.)')
    test_split("A venit domnu' Vasile. ")
    test_split("A venit domnu' acela. ")
    # one/two returns = paragraph = new sentence:
    _test_split_with(stokenizer2, 'A venit domnul\n\n', 'Vasile.')
    _test_split_with(stokenizer, 'A venit domnul\n', 'Vasile.')
    _test_split_with(stokenizer2, "A venit domnu'\n\n", 'Vasile.')
    _test_split_with(stokenizer, "A venit domnu'\n", 'Vasile.')
    # Missing space after sentence end:
    test_split('El este din România!', 'Acum e plecat cu afaceri.')
    test_split('Temperatura este de 30°C.', 'Este destul de cald.')
    test_split('A alergat 50 m. ', 'Deja a obosit.')
    # From the abbreviation list:
    test_split('Pentru dvs. vom face o excepție.')
    test_split('Pt. dumneavoastră vom face o excepție.')
    test_split('Pt. dvs. vom face o excepție.')
    # din punct de vedere
    test_split('A expus problema d.p.d.v. artistic.')
    test_split('A expus problema dpdv. artistic.')
    # şi aşa mai departe.
    test_split('Are mere, pere, șamd. dar nu are alune.')
    test_split('Are mere, pere, ș.a.m.d. dar nu are alune.')
    test_split('Are mere, pere, ș.a.m.d. ', 'În schimb, nu are alune.')
    # şi celelalte
    test_split('Are mere, pere, ş.c.l. dar nu are alune.')
    test_split('Are mere, pere, ş.c.l. ', 'Nu are alune.')
    # etc. et cetera
    test_split('Are mere, pere, etc. dar nu are alune.')
    test_split('Are mere, pere, etc. ', 'Nu are alune.')
    # ş.a. - şi altele
    test_split('Are mere, pere, ș.a. dar nu are alune.')
    # pag, leg, art
    test_split('Lecția începe la pag. următoare și are trei pagini.')
    test_split('Lecția începe la pag. 20 și are trei pagini.')
    test_split('A acționat în conformitate cu lg. 144, art. 33.')
    test_split('A acționat în conformitate cu leg. 144, art. 33.')
    test_split('A acționat în conformitate cu legea nr. 11.')
    test_split('Lupta a avut loc în anul 2000 î.H. și a durat trei ani.')
    # lunile anului, abreviate
    test_split('Discuția a avut loc pe data de douăzeci aug. și a durat două ore.')
    test_split('Discuția a avut loc pe data de douăzeci ian. și a durat două ore.')
    test_split('Discuția a avut loc pe data de douăzeci feb. și a durat două ore.')
    test_split('Discuția a avut loc pe data de douăzeci ian.', 'A durat două ore.')
    # M.Ap.N. - Ministerul Apărării Nationale
    # there are 2 rules for this in segment.srx. Can this be done with only one rule?
    test_split('A fost și la M.Ap.N. dar nu l-au primit. ')
    test_split('A fost și la M.Ap.N. ', 'Nu l-au primit. ')
    # sic!
    test_split("Apo' da' tulai (sic!) că mult mai e de mers.")
    test_split("Apo' da' tulai(sic!) că mult mai e de mers.")
    # […]
    test_split('Aici este o frază […] mult prescurtată.')
    test_split('Aici este o frază [...] mult prescurtată.')


# --- AbstractRomanianTaggerTest, RomanianTaggerTest, RomanianTaggerDiacriticsTest ---

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


def _diacritics_tagger():
    # new RomanianTagger("/ro/test_diacritics.dict")
    lang = get_language('ro')
    return BaseTagger(lang.dictionary('ro/test_diacritics.dict'), 'ro', lang.resource_dir)


def _assert_has_lemma_and_pos(tagger, inflected, lemma, pos_tag):
    # AbstractRomanianTaggerTest.assertHasLemmaAndPos
    all_tags = []
    found = False
    for atr in tagger.tag([inflected]):
        for token in atr.readings:
            all_tags.append('[%s/%s]' % (token.lemma, token.pos_tag))
            found = (lemma is None or lemma == token.lemma) and (pos_tag is None or pos_tag == token.pos_tag)
            if found:
                break
        if found:
            break
    assert found, 'Lemma and POS not found for word [%s]! Expected [%s/%s]. Actual: %s' % (
        inflected, lemma, pos_tag, ''.join(all_tags))


@pytest.mark.parametrize('diacritics', [False, True])
def test_dictionary(diacritics):
    """AbstractRomanianTaggerTest.testDictionary (TestTools.testDictionary
    only prints warnings for entries without POS tags; check that the
    dictionary can be read completely)"""
    tagger = _diacritics_tagger() if diacritics else get_language('ro').tagger
    assert sum(1 for _ in tagger.dictionary.iter_all()) > 0


def test_tagger_merge():
    """RomanianTaggerTest.testTaggerMerge"""
    tagger = get_language('ro').tagger
    # merge - verb indicativ imperfect, persoana întâi, singular
    _assert_has_lemma_and_pos(tagger, 'mergeam', 'merge', 'V0s1000ii0')
    # merge - verb indicativ imperfect, persoana întâi, plural
    _assert_has_lemma_and_pos(tagger, 'mergeam', 'merge', 'V0p1000ii0')


def test_tagger_merseseram():
    """RomanianTaggerTest.testTaggerMerseseram"""
    tagger = get_language('ro').tagger
    # first make sure lemma is correct (ignore POS)
    _assert_has_lemma_and_pos(tagger, 'merseserăm', 'merge', None)
    # now that lemma is correct, also check POS
    _assert_has_lemma_and_pos(tagger, 'merseserăm', 'merge', 'V0p1000im0')
    _my_assert('merseserăm', 'merseserăm/[merge]V0p1000im0', WordTokenizer(), tagger)


def test_tagger_fi():
    """RomanianTaggerTest.testTagger_Fi"""
    tagger = get_language('ro').tagger
    # fi - verb indicativ prezent, persoana întâi, singular
    _assert_has_lemma_and_pos(tagger, 'sunt', 'fi', 'V0s1000izf')
    # fi verb indicativ prezent, persoana a treia, plural
    _assert_has_lemma_and_pos(tagger, 'sunt', 'fi', 'V0p3000izf')


def test_tagger_user_dict():
    """RomanianTaggerTest.testTaggerUserDict"""
    _assert_has_lemma_and_pos(get_language('ro').tagger, 'configurați', 'configura', 'V0p2000cz0')


def test_tagger():
    """RomanianTaggerTest.testTagger"""
    _my_assert('Cartea este frumoasă.',
               'Cartea/[carte]Sfs3aac000 -- este/[fi]V0s3000izb -- frumoasă/[frumos]Afs3an0000',
               WordTokenizer(), get_language('ro').tagger)


def test_tagger_diacritics_merseseram():
    """RomanianTaggerDiacriticsTest.testTaggerMerseseram"""
    tagger = _diacritics_tagger()
    _assert_has_lemma_and_pos(tagger, 'făcusem', 'face', '004')
    _assert_has_lemma_and_pos(tagger, 'cuțitul', 'cuțit', '002')
    # make sure lemma is correct (POS is hard-coded, not important)
    _assert_has_lemma_and_pos(tagger, 'merseserăm', 'merge', '002')


def test_tagger_diacritics_cusca_cutit():
    """RomanianTaggerDiacriticsTest.testTaggerCuscaCutit"""
    tagger = _diacritics_tagger()
    _assert_has_lemma_and_pos(tagger, 'cușcă', 'cușcă', '001')
    _assert_has_lemma_and_pos(tagger, 'cuțit', 'cuțit', '001')
    _assert_has_lemma_and_pos(tagger, 'cuțitul', 'cuțit', '002')


# --- RomanianRuleDisambiguatorTest ---

def _my_assert_disambiguated(text, expected, disambiguator):
    # TestTools.myAssert(input, expected, tokenizer, sentenceTokenizer, tagger, disambiguator)
    lang = get_language('ro')
    tokenizer = RomanianWordTokenizer()
    sentence_tokenizer = SRXSentenceTokenizer(lang)
    tagger = lang.tagger
    out = []
    for sentence in sentence_tokenizer.tokenize(text):
        tokens = tokenizer.tokenize(sentence)
        a_tokens = tagger.tag([t for t in tokens if _is_word(t)])
        token_array = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)]
        start_pos = 0
        no_whitespace_count = 0
        for token in tokens:
            if _is_word(token):
                pos_tag = a_tokens[no_whitespace_count]
                pos_tag.start_pos = start_pos
                no_whitespace_count += 1
            else:
                pos_tag = tagger.create_null_token(token, start_pos)
            token_array.append(pos_tag)
            start_pos += len(token)
        final_sentence = disambiguator.disambiguate(AnalyzedSentence(token_array))
        out.append(' '.join('|'.join(_as_strings(r.readings)) for r in final_sentence.tokens))
    assert ''.join(out) == expected


@pytest.fixture(scope='module')
def disambiguators():
    # new XmlRuleDisambiguator(language): the only stage of the language's disambiguator
    disambiguator, = get_language('ro').disambiguator.stages
    assert isinstance(disambiguator, XmlRuleDisambiguator)
    return disambiguator, DemoDisambiguator()


def test_disambiguator_care(disambiguators):
    """RomanianRuleDisambiguatorTest.testCare1"""
    disambiguator, disamb2 = disambiguators
    _my_assert_disambiguated(
        'Persoana care face treabă.',
        '/[null]SENT_START Persoana/[persoană]Sfs3aac000  /[null]null care/[car]Snp3anc000|care/[care]0000000000|'
        'care/[care]N000a0l000|care/[căra]V0p3000cz0|care/[căra]V0s3000cz0  /[null]null '
        'face/[face]V000000f00|face/[face]V0s3000iz0  /[null]null treabă/[treabă]Sfs3anc000 ./[null]null',
        disamb2)
    _my_assert_disambiguated(
        'Persoana care face treabă.',
        '/[null]SENT_START Persoana/[persoană]Sfs3aac000  /[null]null care/[care]N000a0l000  /[null]null '
        'face/[face]V000000f00|face/[face]V0s3000iz0  /[null]null treabă/[treabă]Sfs3anc000 ./[null]null',
        disambiguator)


def test_disambiguator_este_o(disambiguators):
    """RomanianRuleDisambiguatorTest.testEsteO"""
    disambiguator, disamb2 = disambiguators
    _my_assert_disambiguated(
        'este o masă.',
        '/[null]SENT_START este/[fi]V0s3000izb  /[null]null o/[o]Dfs3a0t000|o/[o]I00000o000|o/[o]Nfs3a0p00c|'
        'o/[o]Sms3anc000|o/[vrea]V0s3000iov  /[null]null masă/[masa]V0s3000is0|masă/[masă]Sfs3anc000 ./[null]null',
        disamb2)
    _my_assert_disambiguated(
        'este o masă.',
        '/[null]SENT_START este/[fi]V0s3000izb  /[null]null o/[o]Dfs3a0t000|o/[o]I00000o000|o/[o]Nfs3a0p00c|'
        'o/[o]Sms3anc000|o/[vrea]V0s3000iov  /[null]null masă/[masă]Sfs3anc000 ./[null]null',
        disambiguator)
    _my_assert_disambiguated(
        'este o masă',
        '/[null]SENT_START este/[fi]V0s3000izb  /[null]null o/[o]Dfs3a0t000|o/[o]I00000o000|o/[o]Nfs3a0p00c|'
        'o/[o]Sms3anc000|o/[vrea]V0s3000iov  /[null]null masă/[masă]Sfs3anc000',
        disambiguator)


def test_disambiguator_verb(disambiguators):
    """RomanianRuleDisambiguatorTest.testDezambiguizareVerb"""
    disambiguator, disamb2 = disambiguators
    _my_assert_disambiguated(
        'vom participa la',
        '/[null]SENT_START vom/[vrea]V0p1000ivv  /[null]null participa/[participa]V000000f00|'
        'participa/[participa]V0s3000ii0  /[null]null la/[la]P000000000|la/[la]Sms3anc000',
        disamb2)
    _my_assert_disambiguated(
        'vom participa la',
        '/[null]SENT_START vom/[vrea]V0p1000ivv  /[null]null participa/[participa]V000000f00  /[null]null '
        'la/[la]P000000000|la/[la]Sms3anc000',
        disambiguator)
    _my_assert_disambiguated(
        'vom culege',
        '/[null]SENT_START vom/[vrea]V0p1000ivv  /[null]null culege/[culege]V000000f00|culege/[culege]V0s2000m00|'
        'culege/[culege]V0s3000iz0',
        disamb2)
    _my_assert_disambiguated(
        'vom culege',
        '/[null]SENT_START vom/[vrea]V0p1000ivv  /[null]null culege/[culege]V000000f00',
        disambiguator)
    _my_assert_disambiguated(
        'veți culege',
        '/[null]SENT_START veți/[vrea]V0p2000ivv  /[null]null culege/[culege]V000000f00',
        disambiguator)


# --- RomanianSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string():
    """RomanianSynthesizerTest.testSynthesizeStringString"""
    synth = get_language('ro').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    # a alege
    # forma de infinitiv
    assert synth.synthesize(_dummy_token('alege'), 'V000000f00') == ['alege']
    # conjunctiv, pers a doua plural
    assert synth.synthesize(_dummy_token('alege'), 'V0p2000cz0') == ['alegeți']
    # a fi
    assert synth.synthesize(_dummy_token('fi'), 'V000000f0f') == ['fi']
    # indicativ prezent, pers a doua plural
    assert synth.synthesize(_dummy_token('fi'), 'V0p2000izf') == ['sunteți']
    # indicativ prezent, pers a treia plural
    assert synth.synthesize(_dummy_token('fi'), 'V0p3000izf') == ['sunt']
    # indicativ prezent, pers întâi plural
    assert synth.synthesize(_dummy_token('fi'), 'V0s1000izf') == ['sunt']
    # RegExp
    # indicativ prezent, pers a doua plural SAU indicativ prezent, pers a treia plural
    assert synth.synthesize(_dummy_token('fi'), 'V0p2000izf|V0p3000izf', True) == ['sunteți', 'sunt']
    # diverse
    # indicativ, mai mult ca perfect, persoana întâi, plural
    assert synth.synthesize(_dummy_token('merge'), 'V0p1000im0') == ['merseserăm']
    # indicativ, mai mult ca perfect, persoana întâi, singular
    assert synth.synthesize(_dummy_token('merge'), 'V0s1000im0') == ['mersesem']
    assert synth.synthesize(_dummy_token('legătură'), 'Sfs3aac000') == ['legătura']
    assert synth.synthesize(_dummy_token('legătură'), 'Sfs3anc000') == ['legătură']
    # user data (/ro/added.txt)
    assert synth.synthesize(_dummy_token('configura'), 'V0p2000cz0') == ['configurați']  # no reg exp
    assert synth.synthesize(_dummy_token('configura'), 'V0.2000cz0', True) == [
        'configurați', 'configurezi']  # using reg exp
