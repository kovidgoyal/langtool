"""Port of org.languagetool.rules.it.ItalianTest (LanguageSpecificTest),
org.languagetool.rules.it.ItalianWordRepeatRuleTest,
org.languagetool.rules.it.MorfologikItalianSpellerRuleTest,
org.languagetool.rules.it.LanguageSpecificSpellcheckerTest,
org.languagetool.tokenizers.it.ItalianSRXSentenceTokenizerTest,
org.languagetool.tagging.it.ItalianTaggerTest and
org.languagetool.synthesis.it.ItalianSynthesizerTest, plus checks of the
Italian language definition against org.languagetool.language.Italian and of
org.languagetool.rules.it.DateCheckFilter. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.disambiguation import XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.it.filters import DateCheckFilter
from langtool.lang.it.rules import ItalianWordRepeatRule
from langtool.messages import messages_for
from langtool.rules.core_filters import CalendarDate
from langtool.rules.filters import default_filter_factory
from langtool.synthesis import BaseSynthesizer
from langtool.tagging import BaseTagger
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('it')


# --- ItalianTest ---

def test_demo_text():
    """ItalianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = ('Inserite qui il vostro testo... Oppure controlate direttamente questo ed avrete un assaggio di quali '
         'errori possono essere identificati con LanguageTool.')
    matches = JLanguageTool(get_language('it')).check(s)
    # Java expects "MORFOLOGIK_RULE_IT_IT", "ST_03_001"; MORFOLOGIK_RULE_IT_IT (for "controlate") is the
    # spell checker, which is not ported
    assert [m.get_specific_rule_id() for m in matches] == ['ST_03_001']


@pytest.mark.skip(reason='spell checking is not ported: MorfologikItalianSpellerRuleTest tests '
                         'MorfologikItalianSpellerRule')
def test_morfologik_speller():
    """Port of org.languagetool.rules.it.MorfologikItalianSpellerRuleTest"""


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.it.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('it')
    # two countries: getShortCodeWithCountryAndVariant() is just "it"
    assert lang.code == 'it'
    assert lang.name == 'Italian'
    assert lang.countries == ['IT', 'CH']
    # ItalianRuleDisambiguator: just the XmlRuleDisambiguator
    assert lang.definition['disambiguator'] == [('xml', False)]
    stages = lang.disambiguator.stages
    assert len(stages) == 1 and isinstance(stages[0], XmlRuleDisambiguator)
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert type(lang.word_tokenizer) is WordTokenizer
    tagger = lang.tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    synth = lang.synthesizer
    assert isinstance(synth, BaseSynthesizer)
    assert synth.number_speller is None
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['it', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('it')
    rules = lang.get_relevant_rules(messages_for('it'))
    # getRelevantRules without MorfologikItalianSpellerRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'WHITESPACE_PUNCTUATION', 'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS',
        'UPPERCASE_SENTENCE_START', 'ITALIAN_WORD_REPEAT_RULE', 'WHITESPACE_RULE']
    brackets = rules[3]
    assert brackets.start_symbols == ['[', '(', '{', '»', '«']
    assert brackets.end_symbols == [']', ')', '}', '«', '»']
    assert isinstance(rules[5], ItalianWordRepeatRule)
    assert not unsupported_components(lang)


# --- ItalianWordRepeatRuleTest ---

def test_word_repeat_rule():
    """ItalianWordRepeatRuleTest.testRule"""
    lang = get_language('it')
    rule = ItalianWordRepeatRule(messages_for('en'), lang)
    lt = JLanguageTool(lang)
    assert len(rule.match(lt.get_analyzed_sentence('Mi è sembrato così così'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Duran Duran'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Devi mescolare piano piano'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Seguo passo passo'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Mi mi è sembrato così'))) == 1


def test_word_repeat_rule_properties():
    lang = get_language('it')
    rule = ItalianWordRepeatRule(messages_for('it'), lang)
    assert rule.get_id() == 'ITALIAN_WORD_REPEAT_RULE'
    lt = JLanguageTool(lang)
    assert len(rule.match(lt.get_analyzed_sentence('Il lessico si andava via via modificando.'))) == 0
    m, = rule.match(lt.get_analyzed_sentence('Questo è è un test.'))
    assert (m.from_pos, m.to_pos) == (7, 10)
    assert m.suggested_replacements == ['è']


# --- DateCheckFilter ---

def test_date_check_filter_get_day_of_week():
    f = DateCheckFilter()
    assert f.get_day_of_week('Domenica') == 1
    assert f.get_day_of_week('lun') == 2
    assert f.get_day_of_week('Lunedì') == 2
    assert f.get_day_of_week('mar.') == 3
    assert f.get_day_of_week('mercoledì') == 4
    assert f.get_day_of_week('Gio') == 5
    assert f.get_day_of_week('ven') == 6
    assert f.get_day_of_week('sabato') == 7
    with pytest.raises(RuntimeError):
        f.get_day_of_week('Monday')
    assert [f.get_day_of_week_name(CalendarDate(day_of_week=d)) for d in range(1, 8)] == [
        'domenica', 'lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato']


def test_date_check_filter_get_month():
    f = DateCheckFilter()
    assert f.get_month('gennaio') == 1
    assert f.get_month('Feb') == 2
    assert f.get_month('MAGGIO') == 5
    assert f.get_month('giu') == 6
    assert f.get_month('ott') == 10
    assert f.get_month('dicembre') == 12
    with pytest.raises(RuntimeError):
        f.get_month('october')


def test_date_check_filter_registered():
    lang = get_language('it')
    assert isinstance(default_filter_factory().get_filter('org.languagetool.rules.it.DateCheckFilter', lang),
                      DateCheckFilter)


def test_date_weekday_rule():
    lt = JLanguageTool(get_language('it'))
    m, = [m for m in lt.check('Lunedì 7 ottobre 2014 siamo andati al mare.') if m.rule.get_id() == 'DATE_WEEKDAY']
    assert m.message == 'Questa data non è un lunedì ma un martedì.'
    assert m.url == 'https://www.timeanddate.com/calendar/?year=2014'
    assert not [m for m in lt.check('Martedì 7 ottobre 2014 siamo andati al mare.')
                if m.rule.get_id() == 'DATE_WEEKDAY']
    # invalid dates are left to other rules
    assert not [m for m in lt.check('Lunedì 30 febbraio 2014 siamo andati al mare.')
                if m.rule.get_id() == 'DATE_WEEKDAY']


# --- ItalianSRXSentenceTokenizerTest ---

def test_tokenize():
    """ItalianSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('it'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('Il Castello Reale di Racconigi è situato a Racconigi, in provincia di Cuneo ma poco distante da '
               'Torino. ',
               'Nel corso della sua quasi millenaria storia ha visto numerosi rimaneggiamenti e divenne di proprietà '
               'dei Savoia a partire dalla seconda metà del XIV secolo.')
    test_split('Dott. Bunsen Honeydew')  # abbreviation
    test_split(
        'Abbiamo isolato N. meningitidis da un campione di sangue. ',
        'La Prov. di Bolzano ha competenze autonome. ',
        'La Reg. d’Abruzzo confina con il Lazio. ',
        'Il cd. regolamento è stato approvato ieri. ',
        'Alcuni frutti, es. mele e pere, sono disponibili. ',
        'Nel XIX sec. si verificarono grandi cambiamenti. ',
        'Lavora nel sett. energetico da anni. ',
        'La diagnosi è compatibile con sdr. metabolica. ',
        '“Basta!” disse Maria. ',
        'Prima del ricovero, tutti gli accertamenti necessari (esami ematici, ECG, TAC, ecc.) sono stati '
        'completati secondo protocollo.'
    )


# --- ItalianTaggerTest ---

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


def test_dictionary():
    """ItalianTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    d = get_language('it').tagger.dictionary
    entries, _ = d.count_entries()
    assert entries > 0


def test_tagger():
    """ItalianTaggerTest.testTagger"""
    tagger = get_language('it').tagger
    tokenizer = WordTokenizer()
    _my_assert("Non c'è linguaggio senza inganno.",
               'Non/[non]ADV -- c/[C]NPR -- è/[essere]AUX:ind+pres+3+s|è/[essere]VER:ind+pres+3+s -- '
               'linguaggio/[linguaggio]NOUN-M:s -- senza/[senza]CON|senza/[senza]PRE -- '
               'inganno/[ingannare]VER:ind+pres+1+s|inganno/[inganno]NOUN-M:s', tokenizer, tagger)
    _my_assert("Amo quelli che desiderano l'impossibile.",
               'Amo/[amare]VER:ind+pres+1+s -- quelli/[quelli]PRO-DEMO-M-P|quelli/[quello]DET-DEMO:m+p -- '
               'che/[che]CON|che/[che]DET-WH:f+p|che/[che]DET-WH:f+s|che/[che]DET-WH:m+p|che/[che]DET-WH:m+s|'
               'che/[che]WH-CHE -- desiderano/[desiderare]VER:ind+pres+3+p -- l/[null]null -- '
               'impossibile/[impossibile]ADJ:pos+f+s|impossibile/[impossibile]ADJ:pos+m+s', tokenizer, tagger)
    _my_assert('blablabla', 'blablabla/[null]null', tokenizer, tagger)


# --- ItalianSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string():
    """ItalianSynthesizerTest.testSynthesizeStringString"""
    synth = get_language('it').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('richiedere'), 'VER:impr+pres+2+s') == ['richiedi']
    assert synth.synthesize(_dummy_token('esultare'), 'VER:part+past+s+f') == ['esultata']
    assert synth.synthesize(_dummy_token('libro'), 'NOUN-M:p') == ['libri']
