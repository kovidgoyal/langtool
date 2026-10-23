"""Port of org.languagetool.rules.gl.GalicianTest (LanguageSpecificTest),
org.languagetool.rules.gl.LanguageSpecificSpellcheckerTest and
org.languagetool.tagging.gl.GalicianTaggerTest, plus checks of the Galician
language definition against org.languagetool.language.Galician, of
GalicianTagger, GalicianWordTokenizer, the Galician rules
(org.languagetool.rules.gl) and org.languagetool.rules.gl.AdvancedSynthesizerFilter.
The language independent parts of LanguageSpecificTest.runTests are ported
in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.gl.filters import AdvancedSynthesizerFilter
from langtool.lang.gl.rules import (CastWordsRule, GalicianBarbarismsRule, GalicianRedundancyRule,
                                    GalicianWikipediaRule, GalicianWordinessRule, SimpleReplaceRule)
from langtool.lang.gl.tagging import GalicianTagger
from langtool.lang.gl.tokenizers import GalicianWordTokenizer
from langtool.messages import messages_for
from langtool.rules.filters import default_filter_factory
from langtool.synthesis import BaseSynthesizer
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('gl')


# --- GalicianTest ---

def test_demo_text():
    """GalicianTest.testLanguage (testDemoText)"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    s = 'Esta vai a ser unha mostra de de exemplo para amosar  o funcionamento de LanguageTool.'
    matches = JLanguageTool(get_language('gl')).check(s)
    assert [m.get_specific_rule_id() for m in matches] == ['IR_A_INF', 'WORD_REPETITION', 'WHITESPACE_RULE']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists (HunspellRule)')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.gl.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('gl')
    assert lang.code == 'gl-ES'
    assert get_language('gl-ES') is lang
    assert lang.name == 'Galician'
    assert lang.countries == ['ES']
    assert isinstance(lang.tagger, GalicianTagger)
    assert isinstance(lang.synthesizer, BaseSynthesizer)
    assert type(lang.word_tokenizer) is GalicianWordTokenizer
    # GalicianHybridDisambiguator: MultiWordChunker, then XmlRuleDisambiguator
    stages = lang.disambiguator.stages
    assert len(stages) == 2
    assert isinstance(stages[0], MultiWordChunker) and isinstance(stages[1], XmlRuleDisambiguator)
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['gl', 'grammar.xml']]


def test_priorities():
    """Galician.getPriorityForId"""
    lang = get_language('gl')
    assert lang.get_priority_for_id('DEGREE_MINUTES_SECONDS') == 30
    assert lang.get_priority_for_id('UNPAIRED_BRACKETS') == -5
    assert lang.get_priority_for_id('GL_BARBARISM_REPLACE') == -10
    assert lang.get_priority_for_id('GL_SIMPLE_REPLACE') == -11
    assert lang.get_priority_for_id('GL_REDUNDANCY_REPLACE') == -12
    assert lang.get_priority_for_id('GL_WORDINESS_REPLACE') == -13
    assert lang.get_priority_for_id('TOO_LONG_PARAGRAPH') == -15
    assert lang.get_priority_for_id('GL_WIKIPEDIA_COMMON_ERRORS') == -45
    assert lang.get_priority_for_id('HUNSPELL_RULE') == -50
    assert lang.get_priority_for_id('REPEATED_WORDS') == -210
    assert lang.get_priority_for_id('REPEATED_WORDS_3X') == -211
    assert lang.get_priority_for_id('TOO_LONG_SENTENCE_20') == -997
    assert lang.get_priority_for_id('TOO_LONG_SENTENCE_60') == -1004
    assert lang.get_priority_for_id('GL_CAST_WORDS') == 0


def test_relevant_rules():
    lang = get_language('gl')
    rules = lang.get_relevant_rules(messages_for('gl'))
    # getRelevantRules without HunspellRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS', 'UPPERCASE_SENTENCE_START',
        'WHITESPACE_RULE', 'TOO_LONG_SENTENCE', 'TOO_LONG_PARAGRAPH', 'SENTENCE_WHITESPACE', 'WHITESPACE_PARAGRAPH',
        'WHITESPACE_PARAGRAPH_BEGIN', 'EMPTY_LINE', 'PARAGRAPH_REPEAT_BEGINNING_RULE', 'PUNCTUATION_PARAGRAPH_END',
        'GL_SIMPLE_REPLACE', 'GL_CAST_WORDS', 'GL_REDUNDANCY_REPLACE', 'GL_WORDINESS_REPLACE',
        'GL_BARBARISM_REPLACE', 'GL_WIKIPEDIA_COMMON_ERRORS']
    brackets = rules[2]
    assert brackets.start_symbols == ['[', '(', '{', '“', '«', '»', '‘', '"', "'"]
    assert brackets.end_symbols == [']', ')', '}', '”', '»', '«', '’', '"', "'"]
    assert [e.example for e in rules[0].incorrect_examples] == [
        'Tomamos café<marker> ,</marker> queixo, bolachas e uvas.']
    assert [e.example for e in rules[3].correct_examples] == [
        'Esta casa é vella. <marker>Foi</marker> construida en 1950.']
    assert rules[5].max_words == 50
    assert [type(r) for r in rules[13:]] == [SimpleReplaceRule, CastWordsRule, GalicianRedundancyRule,
                                             GalicianWordinessRule, GalicianBarbarismsRule, GalicianWikipediaRule]
    assert not unsupported_components(lang)


# --- GalicianTaggerTest ---

def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _null(s):
    return 'null' if s is None else s


def _as_strings(readings):
    # TestTools.getAsStrings
    return sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in readings)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_tagger():
    """GalicianTaggerTest.testTagger"""
    tagger = get_language('gl').tagger
    tokenizer = WordTokenizer()
    _my_assert('Todo vai mudar',
               'Todo/[todo]DI0MS0|Todo/[todo]PI0MS000 -- vai/[ir]VMIP3S0|vai/[ir]VMM02S0 -- '
               'mudar/[mudar]VMN0000|mudar/[mudar]VMN01S0|mudar/[mudar]VMN03S0|mudar/[mudar]VMSF1S0|'
               'mudar/[mudar]VMSF3S0', tokenizer, tagger)
    _my_assert('Se aínda somos galegos é por obra e graza do idioma',
               'Se/[se]CS|Se/[se]PP3PN000|Se/[se]PP3SN000 -- aínda/[aínda]CS|aínda/[aínda]RG -- '
               'somos/[ser]VSIP1P0 -- galegos/[galego]AQ0MP0|galegos/[galego]NCMP000 -- é/[ser]VSIP3S0 -- '
               'por/[por]SPS00 -- obra/[obra]NCFS000|obra/[obrar]VMIP3S0|obra/[obrar]VMM02S0 -- '
               'e/[e]CC|e/[e]NCMS000 -- graza/[graza]NCFS000 -- do/[de]SPS00:DA -- idioma/[idioma]NCMS000',
               tokenizer, tagger)


def _tags(tagger, word):
    r, = tagger.tag([word])
    return [(t.lemma, t.pos_tag) for t in r.readings]


def test_tagger_case_and_additional_tags():
    tagger = get_language('gl').tagger
    # lowercase readings for words that are not mixed case
    assert _tags(tagger, 'OBRA') == _tags(tagger, 'obra')
    assert _tags(tagger, 'ObRa') == [(None, None)]
    # no lookup with an uppercase first character (unlike BaseTagger)
    assert _tags(tagger, 'galipedia') == [(None, None)]
    # -mente after a feminine singular adjective: adverb of manner, lemma is the lowercase word
    assert _tags(tagger, 'rapidísimamente') == [(None, None)]
    assert _tags(tagger, 'Rápidamente') == [('rápidamente', 'RM')]
    assert _tags(tagger, 'galegamente') == [('galegamente', 'RM')]
    # verbs with the prefixes auto- and re-: the tags of the verb, the prefix is added to the lemma
    assert _tags(tagger, 'Remudar') == [('remudar', t) for t in ('VMN0000', 'VMN01S0', 'VMN03S0', 'VMSF1S0',
                                                                 'VMSF3S0')]
    assert _tags(tagger, 'Automudaron') == [('automudar', 'VMIS3P0')]
    assert _tags(tagger, 'AUTOMUDARON') == [('automudar', 'VMIS3P0')]
    # no additional tags for mixed case words
    assert _tags(tagger, 'AUTOmudaron') == [(None, None)]
    # prefix but no verb: no readings at all
    assert _tags(tagger, 'reidioma') == [(None, None)]
    assert _tags(tagger, 'autoxyzzy') == [(None, None)]
    readings = tagger.tag(['Todo', ' ', 'vai'])
    assert [r.start_pos for r in readings] == [0, 4, 5]


def test_tagger_apostrophes():
    tagger = get_language('gl').tagger
    # typographic apostrophes of tokens longer than one character become typewriter apostrophes
    r, = tagger.tag(['d’aquel'])
    assert r.token == "d'aquel"
    assert not r.chunk_tags
    r, = tagger.tag(["d'aquel"])
    assert r.token == "d'aquel"
    assert [c.chunk_tag for c in r.chunk_tags] == ['containsTypewriterApostrophe']
    r, = tagger.tag(['’'])
    assert r.token == '’'
    r, = tagger.tag(["'"])
    assert not r.chunk_tags


# --- GalicianWordTokenizer ---

def test_word_tokenizer():
    t = GalicianWordTokenizer()
    assert t.tokenize('Tódo-los días') == ['Tódo', '-', 'los', ' ', 'días']
    assert t.tokenize('Custa 2,5 euros, non 3.') == ['Custa', ' ', '2,5', ' ', 'euros', ',', ' ', 'non', ' ', '3', '.']
    assert t.tokenize('Son 2 000 000 persoas') == ['Son', ' ', '2 000 000', ' ', 'persoas']
    assert t.tokenize('Ás 12:25 h.') == ['Ás', ' ', '12:25', ' ', 'h', '.']
    assert t.tokenize('O 1.º e a 2.ª') == ['O', ' ', '1.º', ' ', 'e', ' ', 'a', ' ', '2.ª']
    assert t.tokenize('Naceu o 12.05.2020 en Lugo.') == ['Naceu', ' ', 'o', ' ', '12.05.2020', ' ', 'en', ' ',
                                                         'Lugo', '.']
    assert t.tokenize('1.999.349 a×b÷c') == ['1.999.349', ' ', 'a', '×', 'b', '÷', 'c']
    assert t.tokenize('a=b+c*d') == ['a', '=', 'b', '+', 'c', '*', 'd']
    assert t.tokenize('d’aquel') == ['d', '’', 'aquel']
    assert t.tokenize('Ve a http://www.example.com/x-y hoxe') == ['Ve', ' ', 'a', ' ', 'http://www.example.com/x-y',
                                                                  ' ', 'hoxe']
    assert t.tokenize('') == []


def test_word_tokenizer_dates_as_java():
    """As in Java, the DATE_PATTERN replacement only uses the groups of its
    first alternative: the digits of yyyy.mm.dd and yyyy-mm-dd dates are
    lost (when there is a dot inside the sentence)"""
    t = GalicianWordTokenizer()
    assert t.tokenize('O 2020.05.12 e 2020-05-12 x.') == ['O', ' ', '..', ' ', 'e', ' ', '..', ' ', 'x', '.']
    assert t.tokenize('O 2020-05-12.') == ['O', ' ', '2020', '-', '05', '-', '12', '.']


# --- rules ---

@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('gl'))


def _match(rule, lt, sentence):
    return [(m.from_pos, m.to_pos, m.suggested_replacements, m.message)
            for m in rule.match(lt.get_analyzed_sentence(sentence))]


def test_simple_replace_rule(lt):
    rule = SimpleReplaceRule(messages_for('gl'), get_language('gl'))
    assert rule.get_id() == 'GL_SIMPLE_REPLACE'
    assert rule.category.id == 'MISC'
    assert _match(rule, lt, 'Atopei un achádego.') == [
        (10, 18, ['achado'], "'achádego' non existe en galego. Talvez quería vostede dicir: achado.")]
    assert _match(rule, lt, 'Un Aeroxenerador.') == [
        (3, 16, ['Aeroxerador'], "'Aeroxenerador' non existe en galego. Talvez quería vostede dicir: aeroxerador.")]
    assert _match(rule, lt, 'Atopei un achado.') == []


def test_cast_words_rule(lt):
    rule = CastWordsRule(messages_for('gl'), get_language('gl'))
    assert rule.get_id() == 'GL_CAST_WORDS'
    assert rule.get_short() == 'Castelanismos léxicos'
    assert _match(rule, lt, 'A ACERA está mollada.') == [
        (2, 7, ['BEIRARRÚA'], "'ACERA' é un castelanismo. Empregue no seu sitio: BEIRARRÚA.")]
    assert _match(rule, lt, 'Acera.') == [
        (0, 5, ['Beirarrúa'], "'Acera' é un castelanismo. Empregue no seu sitio: beirarrúa.")]


@pytest.mark.parametrize('cls, rule_id, category, issue_type, url, sentence, expected', [
    (GalicianBarbarismsRule, 'GL_BARBARISM_REPLACE', 'STYLE', 'LocaleViolation',
     'https://gl.wikipedia.org/wiki/Xenismo', 'Ese é o meu curriculum vitae.',
     (12, 28, ['currículo'], "'curriculum vitae' é un xenismo. É preferíbel dicir <suggestion>currículo</suggestion>")),
    (GalicianRedundancyRule, 'GL_REDUNDANCY_REPLACE', 'REDUNDANCY', 'Style',
     'https://gl.wikipedia.org/wiki/Pleonasmo', 'Era unha duna de area.',
     (9, 21, ['duna'], "'duna de area' é un pleonasmo. É preferible dicir <suggestion>duna</suggestion>")),
    (GalicianWikipediaRule, 'GL_WIKIPEDIA_COMMON_ERRORS', 'WIKIPEDIA', 'Grammar',
     'https://gl.wikipedia.org/wiki/Wikipedia:Erros_de_ortograf%C3%ADa_e_desviaci%C3%B3ns',
     'Fíxoo a efectos de nada.',
     (6, 18, ['para os efectos de'],
      "'a efectos de' é un erro. Considere utilizar <suggestion>para os efectos de</suggestion>")),
    (GalicianWordinessRule, 'GL_WORDINESS_REPLACE', 'REDUNDANCY', 'Style', None,
     'Raramente é o caso en que acontece isto.',
     (0, 34, ['Raramente acontece'], "'Raramente é o caso en que acontece' é unha expresión innecesariamente "
                                     "complexa. É preferíbel dicir <suggestion>raramente acontece</suggestion>")),
])
def test_simple_replace_rule2_rules(lt, cls, rule_id, category, issue_type, url, sentence, expected):
    rule = cls(messages_for('gl'), get_language('gl'))
    assert rule.get_id() == rule_id
    assert rule.category.id == category
    assert rule.loc_quality_issue_type == issue_type
    assert rule.url == url
    assert rule.get_suggestions_separator() == ' ou '
    assert _match(rule, lt, sentence) == [expected]
    # the example pair of the rule
    example, = rule.incorrect_examples
    m, = rule.match(lt.get_analyzed_sentence(example.example.replace('<marker>', '').replace('</marker>', '')))
    assert m.suggested_replacements[0].lower() == example.corrections[0].lower()


# --- AdvancedSynthesizerFilter ---

def test_advanced_synthesizer_filter(lt):
    """CLITICS_01: lemma of the verb (token 3), POS tag of the pronoun
    (token 2), postagReplace V\\a1:\\b1"""
    assert isinstance(default_filter_factory().get_filter('org.languagetool.rules.gl.AdvancedSynthesizerFilter',
                                                          get_language('gl')), AdvancedSynthesizerFilter)
    result = [(m.get_specific_rule_id(), m.from_pos, m.to_pos, m.suggested_replacements)
              for m in lt.check('Volo dixen.')]
    assert result == [('CLITICS_01', 0, 10, ['Díxenvolo'])]
    result = [(m.get_specific_rule_id(), m.suggested_replacements) for m in lt.check('VOLO DIXEN.')]
    assert result == [('CLITICS_01', ['DÍXENVOLO'])]
    result = [(m.get_specific_rule_id(), m.suggested_replacements) for m in lt.check('Me dixo que si.')]
    assert result == [('CLITICS_01', ['Díxome'])]
