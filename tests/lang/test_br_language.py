"""Port of org.languagetool.rules.br.BretonTest (LanguageSpecificTest),
org.languagetool.rules.br.TopoReplaceRuleTest,
org.languagetool.rules.br.MorfologikBretonSpellerRuleTest,
org.languagetool.rules.br.LanguageSpecificSpellcheckerTest and
org.languagetool.tokenizers.br.BretonWordTokenizerTest, plus checks of the
Breton language definition against org.languagetool.language.Breton, of
BretonTagger, BretonCompoundRule and org.languagetool.rules.br.DateCheckFilter.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.br.filters import DateCheckFilter
from langtool.lang.br.rules import BretonCompoundRule, TopoReplaceRule
from langtool.lang.br.tagging import BretonTagger
from langtool.lang.br.tokenizers import BretonWordTokenizer
from langtool.messages import messages_for
from langtool.rules.core_filters import CalendarDate
from langtool.rules.filters import default_filter_factory
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('br')


# --- BretonTest ---

def test_demo_text():
    """BretonTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Lakait amañ ho testenn vrezhonek da vezañ gwiriet. Pe implijit an frazenn-mañ gant meur a fazioù '
         'yezhadurel enni.')
    matches = JLanguageTool(get_language('br')).check(s)
    assert [m.get_specific_rule_id() for m in matches] == ['AR', 'LIES']
    assert [(m.from_pos, m.to_pos) for m in matches] == [(63, 65), (90, 96)]
    assert matches[0].suggested_replacements == ['ar']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists (MorfologikBretonSpellerRule)')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.br.LanguageSpecificSpellcheckerTest"""


@pytest.mark.skip(reason='spell checking is not ported: MorfologikBretonSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.rules.br.MorfologikBretonSpellerRuleTest"""


def test_definition():
    lang = get_language('br')
    assert lang.code == 'br-FR'
    assert get_language('br-FR') is lang
    assert lang.name == 'Breton'
    assert lang.countries == ['FR']
    assert lang.synthesizer is None
    assert isinstance(lang.tagger, BretonTagger)
    assert lang.tagger.tag_lowercase_with_uppercase
    assert type(lang.word_tokenizer) is BretonWordTokenizer
    stages = lang.disambiguator.stages
    assert len(stages) == 1 and isinstance(stages[0], XmlRuleDisambiguator)
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['br', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('br')
    rules = lang.get_relevant_rules(messages_for('br'))
    # getRelevantRules without MorfologikBretonSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == ['COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION',
                                           'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE', 'SENTENCE_WHITESPACE',
                                           'BR_TOPO']
    assert isinstance(rules[-1], TopoReplaceRule)
    assert not unsupported_components(lang)


# --- TopoReplaceRuleTest ---

def test_topo_replace_rule():
    """TopoReplaceRuleTest.testRule"""
    rule = TopoReplaceRule(messages_for('en'))
    lt = JLanguageTool(get_language('br'))
    # Wrong sentences.
    assert len(rule.match(lt.get_analyzed_sentence('France a zo ur vro.'))) == 1
    # Correct sentences.
    assert len(rule.match(lt.get_analyzed_sentence('France 3 a zo ur chadenn skinwel.'))) == 0


def test_topo_replace_rule_messages_and_multi_token_names():
    """TopoReplaceRule: message with several suggestions, names of more
    than one token (with an apostrophe), case sensitivity"""
    rule = TopoReplaceRule(messages_for('br'))
    lt = JLanguageTool(get_language('br'))
    m, = rule.match(lt.get_analyzed_sentence('France a zo ur vro.'))
    assert (m.from_pos, m.to_pos) == (0, 6)
    assert m.message == ('France zo un anv lec’h gallek. Ha fellout a rae deoc’h skrivañ '
                         '<suggestion>Frañs</suggestion> pe <suggestion>bro-C’hall</suggestion>?')
    assert m.short_message == 'anvioù lec’h'
    assert m.suggested_replacements == ['Frañs', 'bro-C’hall']
    for s in ('Bez ez eus e Pont-L’Abbé.', "Bez ez eus e Pont-L'Abbé."):
        m, = rule.match(lt.get_analyzed_sentence(s))
        assert (m.from_pos, m.to_pos) == (13, 24)
        assert m.suggested_replacements == ['Pont-’n-Abad']
    assert rule.match(lt.get_analyzed_sentence('france a zo ur vro.')) == []
    assert [len(m) for m in rule.get_wrong_words()] == [1675, 10]


# --- BretonWordTokenizerTest ---

def test_tokenize():
    """BretonWordTokenizerTest.testTokenize"""
    word_tokenizer = BretonWordTokenizer()
    tokens = word_tokenizer.tokenize("Test c'h")
    assert len(tokens) == 3
    assert tokens == ['Test', ' ', 'c’h']
    tokens = word_tokenizer.tokenize('Test c’h')
    assert len(tokens) == 3
    assert tokens == ['Test', ' ', 'c’h']
    tokens = word_tokenizer.tokenize("C'hwerc'h merc'h gwerc'h war c'hwerc'h marc'h kalloc'h")
    assert len(tokens) == 13
    assert tokens == ['C’hwerc’h', ' ', 'merc’h', ' ', 'gwerc’h', ' ', 'war', ' ', 'c’hwerc’h', ' ', 'marc’h',
                      ' ', 'kalloc’h']
    tokens2 = word_tokenizer.tokenize('Test n’eo')
    assert len(tokens2) == 4
    assert tokens2 == ['Test', ' ', 'n’', 'eo']


def test_tokenize_apostrophes():
    """BretonWordTokenizer: all apostrophes after a letter become ’ and end
    the word"""
    word_tokenizer = BretonWordTokenizer()
    assert word_tokenizer.tokenize("n'") == ['n’']
    assert word_tokenizer.tokenize("x'y‘z ’a") == ['x’', 'y’', 'z', ' ', '’', 'a']
    assert word_tokenizer.tokenize('CʼH') == ['C’H']
    assert word_tokenizer.tokenize('') == []


# --- BretonTagger ---

def _tags(tagger, word):
    r, = tagger.tag([word])
    return [(t.lemma, t.pos_tag) for t in r.readings]


def test_tagger():
    tagger = get_language('br').tagger
    assert _tags(tagger, 'levr') == [('levr', 'N m s')]
    assert _tags(tagger, 'Levr') == [('levr', 'N m s')]
    # unlike BaseTagger, the lowercase readings are added for mixed case words too
    assert _tags(tagger, 'LeVr') == [('levr', 'N m s')]
    # lowercase word found with an uppercase first character
    assert _tags(tagger, 'marc') == [('Marc', 'Z m s ant')]
    # the suffixes -mañ, -se, -hont are removed when the word is unknown
    assert _tags(tagger, 'levr-mañ') == [('levr', 'N m s')]
    assert _tags(tagger, 'LEVR-HONT') == [('levr', 'N m s')]
    r, = tagger.tag(['levr-se'])
    assert r.token == 'levr-se'
    assert _tags(tagger, 'xyzzy-se') == [(None, None)]
    assert _tags(tagger, 'a' * 51) == [(None, None)]
    readings = tagger.tag(['Penaos', ' ', 'emañ'])
    assert [r.start_pos for r in readings] == [0, 6, 7]


# --- BretonCompoundRule ---

def test_compound_rule():
    lang = get_language('br')
    rule = BretonCompoundRule(messages_for('br'), lang)
    assert rule.get_id() == 'BR_COMPOUNDS'
    assert rule.category.id == 'COMPOUNDING'
    assert rule.loc_quality_issue_type == 'Grammar'
    assert [e.example for e in rule.incorrect_examples] == [
        "Gwelet em eus un <marker>alc'hweder gwez</marker> e-kerzh an dibenn-sizhun-mañ."]
    lt = JLanguageTool(lang)
    m, = rule.match(lt.get_analyzed_sentence('An anv tiegezh a zo hir.'))
    assert (m.from_pos, m.to_pos) == (3, 14)
    assert m.message == 'Skrivet e vez ar ger-mañ boaz gant ur varrennig-stagañ.'
    assert m.suggested_replacements == ['anv-tiegezh']
    assert rule.match(lt.get_analyzed_sentence('An anv-tiegezh a zo hir.')) == []
    # As in Java, the example pair of the rule doesn't match: BretonWordTokenizer
    # turns "alc'hweder" into "alc’hweder", compounds.txt has "alc'hweder-gwez"
    # (the rule is not one of Breton's relevant rules, so Java doesn't test it)
    assert rule.match(lt.get_analyzed_sentence(
        "Gwelet em eus un alc'hweder gwez e-kerzh an dibenn-sizhun-mañ.")) == []


# --- DateCheckFilter ---

def test_date_check_filter_get_day_of_week():
    f = DateCheckFilter()
    assert f.get_day_of_week('Disul') == 1
    assert f.get_day_of_week('lun') == 2
    assert f.get_day_of_week('Dimeurzh') == 3
    assert f.get_day_of_week('Merc’her') == 4
    assert f.get_day_of_week('yaou') == 5
    assert f.get_day_of_week('Diriaou') == 5
    assert f.get_day_of_week('digwener') == 6
    assert f.get_day_of_week('Disadorn') == 7
    with pytest.raises(RuntimeError):
        f.get_day_of_week('Monday')


def test_date_check_filter_get_day_of_month():
    f = DateCheckFilter()
    assert f.get_day_of_month('c’hentañ') == 1
    assert f.get_day_of_month('Unan') == 1
    assert f.get_day_of_month('eil') == 2
    assert f.get_day_of_month('tri') == 3
    assert f.get_day_of_month('trede') == 3
    assert f.get_day_of_month('pevar') == 4
    assert f.get_day_of_month('pempvet') == 5
    assert f.get_day_of_month('pemvet') == 5
    assert f.get_day_of_month('navet') == 9
    assert f.get_day_of_month('ugentvet') == 20
    assert f.get_day_of_month('tregont') == 30
    assert f.get_day_of_month('12') == 0
    with pytest.raises(IndexError):  # Java: charAt(0) on an empty string
        f.get_day_of_month('')


def test_date_check_filter_get_month():
    f = DateCheckFilter()
    assert f.get_month('Genver') == 1
    assert f.get_month('c’hwevrer') == 2
    assert f.get_month('even') == 6
    assert f.get_month('gouhere') == 7
    assert f.get_month('kerzu') == 12
    with pytest.raises(RuntimeError):
        f.get_month('August')


def test_date_check_filter_day_names():
    f = DateCheckFilter()
    assert [f.get_day_of_week_name(CalendarDate(day_of_week=d)) for d in range(1, 8)] == [
        'Sul', 'Lun', 'Meurzh', 'Merc’her', 'Yaou', 'Gwener', 'Sadorn']
    # months are 0-based as in java.util.Calendar
    assert f.get_day_of_week_name(CalendarDate.of(2014, 7, 31)) == 'Sul'


def test_date_check_filter_registered():
    lang = get_language('br')
    assert isinstance(default_filter_factory().get_filter('org.languagetool.rules.br.DateCheckFilter', lang),
                      DateCheckFilter)
