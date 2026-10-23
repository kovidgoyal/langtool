"""Port of org.languagetool.rules.pl.PolishTest (LanguageSpecificTest),
org.languagetool.JLanguageToolTest (language-pl),
org.languagetool.tools.ToolsTest (language-pl),
org.languagetool.rules.pl.MatchTest, UppercaseSentenceStartRuleTest,
MultipleWhitespaceRuleTest, WordRepeatRuleTest and
LanguageSpecificSpellcheckerTest (skipped, spell checking), plus checks of
the Polish language definition against org.languagetool.language.Polish.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import io

import pytest

from conftest import require_dictionaries
from langtool import global_config
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.pl.rules import (CompoundRule, DashRule, PolishUnpairedBracketsRule, PolishWordRepeatRule,
                                    SimpleReplaceRule, WordCoherencyRule)
from langtool.lang.pl.synthesis import PolishSynthesizer
from langtool.lang.pl.tagging import PolishTagger
from langtool.lang.pl.tokenizers import PolishWordTokenizer
from langtool.messages import messages_for
from langtool.patterns import match as M
from langtool.patterns.match import Match, MatchState
from langtool.rules.core import MultipleWhitespaceRule, WordRepeatRule
from langtool.tool import JLanguageTool, correct_text


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pl')


# --- PolishTest ---

def test_demo_text():
    """PolishTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Wpisz tekst lub użyj istniejącego przykładu. To jest przykładowy tekst który pokazuje, jak jak działa '
         'LanguageTool. LanguageTool ma jusz korektor psowni, który wyrurznia bledy na czewrono.')
    matches = JLanguageTool(get_language('pl')).check(s)
    # Java expects four more matches of MORFOLOGIK_RULE_PL_PL (for "jusz", "psowni", "wyrurznia",
    # "czewrono"), the spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == [
        'BRAK_PRZECINKA_KTORY', 'WORD_REPEAT_RULE', 'PL_SIMPLE_REPLACE']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists (MorfologikPolishSpellerRule)')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.pl.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('pl')
    assert lang.code == 'pl-PL'
    assert get_language('pl-PL') is lang
    assert lang.name == 'Polish'
    assert lang.countries == ['PL']
    assert isinstance(lang.tagger, PolishTagger)
    assert isinstance(lang.synthesizer, PolishSynthesizer)
    # createDefaultWordTokenizer() sets the tagger of the language
    assert type(lang.word_tokenizer) is PolishWordTokenizer
    assert lang.word_tokenizer.tagger is lang.tagger
    # PolishHybridDisambiguator: XmlRuleDisambiguator, then MultiWordChunker
    stages = lang.disambiguator.stages
    assert len(stages) == 2
    assert isinstance(stages[0], XmlRuleDisambiguator) and isinstance(stages[1], MultiWordChunker)
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['pl', 'grammar.xml']]


def test_priorities():
    """Polish.getPriorityForId"""
    lang = get_language('pl')
    assert lang.get_priority_for_id('ZDANIA_ZLOZONE') == -1
    assert lang.get_priority_for_id('PL_COMPOUNDS') == 0


def test_relevant_rules():
    lang = get_language('pl')
    rules = lang.get_relevant_rules(messages_for('pl'))
    # getRelevantRules without MorfologikPolishSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'UPPERCASE_SENTENCE_START', 'WORD_REPEAT_RULE', 'WHITESPACE_RULE',
        'SENTENCE_WHITESPACE', 'PL_UNPAIRED_BRACKETS', 'PL_WORD_REPEAT', 'PL_COMPOUNDS', 'PL_SIMPLE_REPLACE',
        'PL_WORD_COHERENCY', 'DASH_RULE']
    assert [type(r) for r in rules[5:]] == [PolishUnpairedBracketsRule, PolishWordRepeatRule, CompoundRule,
                                            SimpleReplaceRule, WordCoherencyRule, DashRule]
    assert [r.get_id() for r in rules if r.default_off] == ['PL_WORD_REPEAT']
    assert not unsupported_components(lang)


# --- JLanguageToolTest ---

@pytest.fixture
def verbose_off():
    yield
    # Java's setOutput() switches the global verbose mode on for the rest of the JVM
    global_config.set_verbose(False)


def test_polish(verbose_off):
    """JLanguageToolTest.testPolish, without the matches of the spell checker
    (see test_polish_spelling)"""
    polish = get_language('pl')
    tool = JLanguageTool(polish)
    tool.set_output(io.StringIO())
    # a Polish without XML rules (getPatternRules() returns an empty list)
    no_rules_tool = JLanguageTool(polish, rules=polish.get_relevant_rules(tool.messages))
    assert polish.countries == ['PL']
    assert len(no_rules_tool.check('To jest całkowicie prawidłowe zdanie.')) == 0
    assert len(no_rules_tool.check('To jest jest problem.')) == 1
    # no error thanks to disambiguation
    assert len(no_rules_tool.check('Mają one niemałe znaczenie.')) == 0
    assert len(no_rules_tool.check('Często wystarczy obrócić na wspak wyroki świata, aby trafnie osądzić jakąś '
                                   'osobę.')) == 0
    # with immunization
    assert len(no_rules_tool.check('A teraz każcie mi dać jaki bądź posiłek.')) == 0
    assert len(no_rules_tool.check('Kiedym wóz zobaczył, byłbym przysiągł, że wielka przygoda mnie czeka.')) == 0
    # with antipatterns: "wymaluj" in "wypisz wymaluj" is immunized locally for punctuation mistakes,
    # so it should get no match
    assert len(no_rules_tool.check('Jurek wygląda wypisz wymaluj babcia.')) == 0
    # but it should get a match with word repetitions:
    assert len(no_rules_tool.check('Jurek wygląda wypisz wypisz wymaluj babcia.')) == 1
    assert len(no_rules_tool.check('Jurek wygląda wypisz wymaluj wymaluj babcia.')) == 1
    # check for a weird unification bug:
    assert len(no_rules_tool.check('Zawarł w niej, oprócz swojej twórczości, wybrane epigramaty czterdziestu ośmiu '
                                   'innych greckich poetów i poetek.')) == 0
    # checking on pattern rules now...
    # now this should be immunized:
    assert len(tool.check('Nudne brednie tak zamąciły głowę chłopu, że klął na czym ziemia stoi, zmuszonym będąc '
                          'słuchać tego wszystkiego.')) == 0
    # but this "chcąc, nie chcąc" immunized only by an antipattern
    assert len(tool.check('Chcąc, nie chcąc zjadłem pstrąga.')) == 1
    # this rule is by default off
    assert len(tool.check('Był on bowiem pięknym strzelcem bowiem.')) == 0
    tool.enable_rule('PL_WORD_REPEAT')
    assert len(tool.check('Był on bowiem pięknym strzelcem bowiem.')) == 1
    assert len(tool.check('Premier drapie się w ucho co i rusz.')) == 1
    # Polish rule has no effect with English error (Java: 6 matches of the spell checker)
    assert len(tool.check('I can give you more a detailed description')) == 0
    tool.set_list_unknown_words(True)
    # (Java: 3 matches of the spell checker)
    assert len(tool.check('This is not a Polish text.')) == 0
    assert tool.get_unknown_words() == ['.', 'Polish', 'This', 'is', 'text']
    # check positions relative to sentence ends
    matches = tool.check('To jest tekst.\nTest 1. To jest linia w której nie ma przecinka.')
    assert matches[0].column == 17
    # with a space...
    matches = tool.check('To jest tekst. \nTest 1. To jest linia w której nie ma przecinka.')
    assert matches[0].column == 16
    matches = tool.check('To jest tekst. Test 1. To jest linia w której nie ma przecinka.')
    assert matches[0].column == 32
    # recheck with the -b mode...
    st = polish.sentence_tokenizer
    st.set_single_line_breaks_marks_paragraph(True)
    try:
        tool = JLanguageTool(polish)
        matches = tool.check('To jest tekst.\nTest 1. To jest linia w której nie ma przecinka.')
        assert matches[0].column == 17
        # with a space...
        matches = tool.check('To jest tekst. \nTest 1. To jest linia w której nie ma przecinka.')
        assert matches[0].column == 17
        matches = tool.check('To jest tekst. To jest linia w której nie ma przecinka.')
        assert matches[0].column == 24
    finally:
        st.set_single_line_breaks_marks_paragraph(False)

    # and let's test other feats
    sent = tool.get_analyzed_sentence('Z powodu pogody dobre buty są wskazane.')
    assert sent.get_annotations() == (
        'Disambiguator log: \n'
        '\n'
        'prep_verb[2]: Z[z/prep:acc:nwok*,z/prep:gen:nwok*,z/prep:inst:nwok*] -> Z[z/prep:gen:nwok*]\n'
        'PREP_SUBST[1]: Z[z/prep:gen:nwok*] -> Z[z/prep:gen:nwok*]\n'
        'PREP_SUBST_2[1]: Z[z/prep:gen:nwok*] -> Z[z/prep:gen:nwok*]\n'
        'MULTIWORD_CHUNKER: Z[z/prep:gen:nwok*] -> Z[z/prep:gen:nwok*,Z powodu/<PREP:GEN>*]\n'
        '\n'
        'prep_verb[2]: powodu[powód/subst:sg:gen:m3] -> powodu[powód/subst:sg:gen:m3]\n'
        'PREP_SUBST[1]: powodu[powód/subst:sg:gen:m3] -> powodu[powód/subst:sg:gen:m3]\n'
        'PREP_SUBST_2[1]: powodu[powód/subst:sg:gen:m3] -> powodu[powód/subst:sg:gen:m3]\n'
        'MULTIWORD_CHUNKER: powodu[powód/subst:sg:gen:m3] -> powodu[powód/subst:sg:gen:m3,Z powodu/</PREP:GEN>]\n'
        '\n'
        'PREP_SUBST[17]: pogody[pogoda/subst:pl:acc:f,pogoda/subst:pl:nom:f,pogoda/subst:pl:voc:f,'
        'pogoda/subst:sg:gen:f] -> pogody[pogoda/subst:sg:gen:f]\n'
        '\n'
        'dobry_adj[1]: dobre[dobre/subst:pl:acc:n2,dobre/subst:pl:nom:n2,dobre/subst:pl:voc:n2,'
        'dobre/subst:sg:acc:n2,dobre/subst:sg:nom:n2,dobre/subst:sg:voc:n2,'
        'dobry/adj:pl:acc:m2.m3.f.n1.n2.p2.p3:pos,dobry/adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos,'
        'dobry/adj:sg:acc:n1.n2:pos,dobry/adj:sg:nom.voc:n1.n2:pos,dobry/depr:pl:nom:m2,dobry/depr:pl:voc:m2,'
        'dobry/subst:pl:acc:m3,dobry/subst:pl:nom:m3,dobry/subst:pl:voc:m3] -> '
        'dobre[dobry/adj:pl:acc:m2.m3.f.n1.n2.p2.p3:pos,dobry/adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos]\n'
        'unify_adj_subst[2]: dobre[dobry/adj:pl:acc:m2.m3.f.n1.n2.p2.p3:pos,'
        'dobry/adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos] -> dobre[dobry/adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos]\n'
        '\n'
        'dobry_adj[1]: buty[but/subst:pl:acc:m2,but/subst:pl:acc:m3,but/subst:pl:nom:m2,but/subst:pl:nom:m3,'
        'but/subst:pl:voc:m2,but/subst:pl:voc:m3,buta/subst:pl:acc:f,buta/subst:pl:nom:f,buta/subst:pl:voc:f,'
        'buta/subst:sg:gen:f] -> buty[but/subst:pl:acc:m2,but/subst:pl:acc:m3,but/subst:pl:nom:m2,'
        'but/subst:pl:nom:m3,but/subst:pl:voc:m2,but/subst:pl:voc:m3,buta/subst:pl:acc:f,buta/subst:pl:nom:f,'
        'buta/subst:pl:voc:f]\n'
        'buty[1]: buty[but/subst:pl:acc:m2,but/subst:pl:acc:m3,but/subst:pl:nom:m2,but/subst:pl:nom:m3,'
        'but/subst:pl:voc:m2,but/subst:pl:voc:m3,buta/subst:pl:acc:f,buta/subst:pl:nom:f,buta/subst:pl:voc:f] -> '
        'buty[but/subst:pl:acc:m2,but/subst:pl:acc:m3,but/subst:pl:nom:m2,but/subst:pl:nom:m3,'
        'but/subst:pl:voc:m2,but/subst:pl:voc:m3]\n'
        'nom_sa_nom[1]: buty[but/subst:pl:acc:m2,but/subst:pl:acc:m3,but/subst:pl:nom:m2,but/subst:pl:nom:m3,'
        'but/subst:pl:voc:m2,but/subst:pl:voc:m3] -> buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3]\n'
        'unify_adj_subst[2]: buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3] -> '
        'buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3]\n'
        'PPRON3_NOM_VERB_ADJ[1]: buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3] -> '
        'buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3]\n'
        'SUBST_NOM_VOC_VERB[6]: buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3] -> '
        'buty[but/subst:pl:nom:m2,but/subst:pl:nom:m3]\n'
        '\n'
        'ppas_jest[1]: są[być/verb:fin:pl:ter:imperf:nonrefl] -> są[być/verb:fin:pl:ter:imperf:nonrefl]\n'
        'nom_sa_nom[1]: są[być/verb:fin:pl:ter:imperf:nonrefl] -> są[być/verb:fin:pl:ter:imperf:nonrefl]\n'
        'PPRON3_NOM_VERB_ADJ[1]: są[być/verb:fin:pl:ter:imperf:nonrefl] -> są[być/verb:fin:pl:ter:imperf:nonrefl]\n'
        'SUBST_NOM_VOC_VERB[6]: są[być/verb:fin:pl:ter:imperf:nonrefl] -> są[być/verb:fin:pl:ter:imperf:nonrefl]\n'
        'BYC_ADJ_ACC_NOM[1]: są[być/verb:fin:pl:ter:imperf:nonrefl] -> są[być/verb:fin:pl:ter:imperf:nonrefl]\n'
        '\n'
        'ppas_jest[1]: wskazane[wskazany/adj:pl:acc:m2.m3.f.n1.n2.p2.p3:pos,'
        'wskazany/adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos,wskazany/adj:sg:acc:n1.n2:pos,'
        'wskazany/adj:sg:nom.voc:n1.n2:pos,wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff,'
        'wskazać/ppas:sg:nom.acc.voc:n1.n2:perf:aff] -> '
        'wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff]\n'
        'nom_sa_nom[1]: wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff] -> '
        'wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff]\n'
        'PPRON3_NOM_VERB_ADJ[1]: wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff] -> '
        'wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff]\n'
        'BYC_ADJ_ACC_NOM[1]: wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff] -> '
        'wskazane[wskazać/ppas:pl:nom.acc.voc:m2.m3.f.n1.n2.p2.p3:perf:aff]\n')


@pytest.mark.skip(reason='spell checking is not ported: in JLanguageToolTest.testPolish the 6 matches of '
                         '"I can give you more a detailed description" and the 3 matches of "This is not a Polish '
                         'text." come from MorfologikPolishSpellerRule')
def test_polish_spelling():
    """JLanguageToolTest.testPolish, the matches of the spell checker"""


def test_verbose_output(verbose_off):
    """JLanguageTool.setOutput: the analyzed sentences and the disambiguator
    log are printed, the annotations are only recorded in verbose mode"""
    polish = get_language('pl')
    tool = JLanguageTool(polish)
    assert tool.get_analyzed_sentence('Z powodu pogody.').get_annotations() == 'Disambiguator log: \n'
    out = io.StringIO()
    tool.set_output(out)
    assert global_config.is_verbose()
    tool.check('Z powodu pogody.')
    assert 'MULTIWORD_CHUNKER: Z[z/prep:gen:nwok*] -> Z[z/prep:gen:nwok*,Z powodu/<PREP:GEN>*]' in out.getvalue()
    tool.set_output(None)
    assert not global_config.is_verbose()
    with pytest.raises(RuntimeError):
        tool.get_unknown_words()


# --- ToolsTest ---

def test_tools_check():
    """ToolsTest.testCheck"""
    tool = JLanguageTool(get_language('pl'))
    assert len(tool.check('To jest całkowicie prawidłowe zdanie.')) == 0
    matches2 = tool.check('To jest problem problem.')
    assert len(matches2) == 1
    assert matches2[0].rule.get_id() == 'WORD_REPEAT_RULE'


def test_tools_correct():
    """ToolsTest.testCorrect"""
    tool = JLanguageTool(get_language('pl'))
    tool.clean_overlapping_matches = False
    assert correct_text('To jest całkowicie prawidłowe zdanie.', tool) == 'To jest całkowicie prawidłowe zdanie.'
    assert correct_text('To jest jest problem.', tool) == 'To jest problem.'
    # more sentences, need to apply more suggestions > 1 in subsequent sentences
    assert correct_text('To jest jest problem. Ale to już już nie jest problem.', tool) == \
        'To jest problem. Ale to już nie jest problem.'
    assert correct_text('To jest jest problem. Ale to już już nie jest problem. Tak sie nie robi. W tym zdaniu '
                        'brakuje przecinka bo go zapomniałem.', tool) == \
        ('To jest problem. Ale to już nie jest problem. Tak się nie robi. W tym zdaniu brakuje przecinka, bo go '
         'zapomniałem.')


# --- MatchTest ---

def _get_analyzed_token_readings(token, pos_tag, lemma):
    return AnalyzedTokenReadings(AnalyzedToken(token, pos_tag, lemma), 0)


def _get_match(pos_tag, pos_tag_replace, spell):
    return Match(pos_tag, pos_tag_replace, True, None, None, M.NONE, False, spell, M.INCLUDE_NONE)


def _get_text_match(regex_match, regexp_replace, spell):
    return Match(None, None, False, regex_match, regexp_replace, M.NONE, False, spell, M.INCLUDE_NONE)


def test_match_speller():
    """MatchTest.testSpeller (the "spell" argument is suppress_misspelled,
    which uses the tagger, not the spell checker)"""
    polish = get_language('pl')
    # tests with synthesizer
    match = _get_match('POS1', 'POS2', True)
    match_state = MatchState(match, polish.synthesizer)
    match_state.set_token(_get_analyzed_token_readings('inflectedform11', 'POS1', 'Lemma1'))
    # getting "<mistake/>" string, which is what we want. It will be removed later.
    assert match_state.to_final_string(polish) == ['<mistake/>']
    # contrast with a speller = false!
    match = _get_match('POS1', 'POS2', False)
    match_state = MatchState(match, polish.synthesizer)
    match_state.set_token(_get_analyzed_token_readings('inflectedform11', 'POS1', 'Lemma1'))
    assert match_state.to_final_string(polish) == ['(inflectedform11)']
    # and now a real word - we should get something
    match = _get_match('subst:sg:acc.nom:m3', 'subst:sg:gen:m3', True)
    match_state = MatchState(match, polish.synthesizer)
    match_state.set_token(_get_analyzed_token_readings('AON', 'subst:sg:acc.nom:m3', 'AON'))
    assert match_state.to_final_string(polish) == ['AON-u']
    # and now pure text changes
    match = _get_text_match('^(.*)$', '$0-u', True)
    match.set_lemma_string('AON')
    match_state = MatchState(match, polish.synthesizer)
    assert match_state.to_final_string(polish) == ['AON-u']
    match.set_lemma_string('batalion')
    # getting "<mistake/>" string, which is what we want. It will be removed later.
    match_state = MatchState(match, polish.synthesizer)
    assert match_state.to_final_string(polish) == ['<mistake/>']
    match.set_lemma_string('ASEAN')
    # and this one not
    match_state = MatchState(match, polish.synthesizer)
    assert match_state.to_final_string(polish) == ['ASEAN-u']


# --- UppercaseSentenceStartRuleTest ---

def test_polish_special_cases():
    """UppercaseSentenceStartRuleTest.testPolishSpecialCases"""
    lt = JLanguageTool(get_language('pl'))
    assert len(lt.check('Zdanie.')) == 0
    assert len(lt.check('To jest lista punktowana:\n\npunkt pierwszy,\n\npunkt drugi,\n\npunkt trzeci.')) == 0


# --- MultipleWhitespaceRuleTest ---

def test_multiple_whitespace_rule():
    """MultipleWhitespaceRuleTest.testRule"""
    polish = get_language('pl')
    rule = MultipleWhitespaceRule(messages_for('en'), polish)
    lt = JLanguageTool(polish)
    assert len(rule.match([lt.get_analyzed_sentence('To jest test.')])) == 0
    assert len(rule.match([lt.get_analyzed_sentence('To jest   test.')])) == 1


# --- WordRepeatRuleTest ---

def test_word_repeat_rule_polish():
    """WordRepeatRuleTest.testRulePolish"""
    polish = get_language('pl')
    rule = WordRepeatRule(messages_for('en'), polish)
    lt = JLanguageTool(polish)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('To jest zdanie.'))) == 0
    # with immunized words:
    assert len(rule.match(lt.get_analyzed_sentence('W w. XVI język jest jak kipiący kocioł.'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Co jeszcze było smutniejsze, to to, że im się jeść chciało '
                                                   'potężnie.'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Tra ta ta!'))) == 0
    # incorrect sentences:
    assert len(rule.match(lt.get_analyzed_sentence('To jest jest zdanie.'))) == 1
