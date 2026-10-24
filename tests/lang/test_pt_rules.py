"""Port of the rule tests of org.languagetool.rules.pt:
BrazilianPortugueseSimpleReplaceRuleTest, PortugueseBarbarismRuleTest,
PortugueseClicheRuleTest, PortugueseColourHyphenationRuleTest,
PortugueseDiacriticsRuleTest, PortugueseOrthographyReplaceRuleTest,
PortugueseUnitConversionRuleTest (with UnitConversionRuleTestHelper),
PortugueseWordRepeatBeginningRuleTest, PortugueseWordRepeatRuleTest,
PostReformCompoundRuleTest, PostReformPortugueseDashRuleTest,
PreReformPortugueseDashRuleTest, UppercaseSentenceStartRuleTest,
MorfologikPortugueseSpellerRuleTest (skipped, spell checking) and
PortugueseRemoteRuleFilterTest (skipped, remote rules), plus checks of the
other Portuguese rules, the filters, the misspelling check and the
multitoken speller. (AccentuationCheckRuleTest._java is not compiled in
Java: it tests the Catalan rule with a Catalan JLanguageTool.)"""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.lang.pt.accentuation import PortugueseAccentuationCheckRule
from langtool.lang.pt.filters import (AdvancedSynthesizerFilter, BrazilianToponymFilter, ConfusionCheckFilter,
                                      DateCheckFilter, FutureDateFilter, NewYearDateFilter,
                                      NoDisambiguationPortuguesePartialPosTagFilter, PortugueseEnclisisFilter,
                                      PortugueseProclisisFilter, RegularIrregularParticipleFilter,
                                      RomanNumeralFilter, YMDDateCheckFilter, YMDNewYearDateFilter,
                                      _brazilian_toponym_map, _relevant_words)
from langtool.lang.pt.multitoken import PortugueseMultitokenSpeller
from langtool.lang.pt.rules import (BrazilianPortugueseReplaceRule, EnglishContractionSpellingRule,
                                    PortugueseBarbarismsRule, PortugueseClicheRule, PortugueseFillerWordsRule,
                                    PortugueseOrthographyReplaceRule, PortugueseReadabilityRule,
                                    PortugueseUnitConversionRule, PortugueseWeaselWordsRule, PortugueseWordRepeatRule,
                                    PostReformPortugueseCompoundRule)
from langtool.lang.pt.spelling import MorfologikPortugueseSpellerCheck, prepare_line_for_speller
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.tool import LEVEL_PICKY, JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pt')


def _disable_all_rules_except(lt, *rule_ids):
    # TestTools.disableAllRulesExcept
    for rule in lt.get_all_rules():
        lt.disable_rule(rule.get_id())
    for rule_id in rule_ids:
        lt.enable_rule(rule_id)


def _check_picky(lt, text):
    # lt.check(new AnnotatedTextBuilder().addText(text).build(), true, NORMAL, null, Mode.ALL, Level.PICKY)
    return lt.check(text, level=LEVEL_PICKY)


def _check_simple_replace_rule(rule, lt, sentence, word):
    matches = rule.match(lt.get_analyzed_sentence(sentence))
    assert len(matches) == 1, 'Invalid matches.length while checking sentence: ' + sentence
    assert len(matches[0].suggested_replacements) == 1, \
        'Invalid replacement count while checking sentence: ' + sentence
    assert matches[0].suggested_replacements[0] == word, \
        'Invalid suggested replacement while checking sentence: ' + sentence


def _assert_no_matches(rule, lt, sentence):
    assert len(rule.match(lt.get_analyzed_sentence(sentence))) == 0


# --- BrazilianPortugueseSimpleReplaceRuleTest ---

def test_brazilian_portuguese_simple_replace_rule():
    """BrazilianPortugueseSimpleReplaceRuleTest.testRule"""
    lt = JLanguageTool(get_language('pt'))
    rule = BrazilianPortugueseReplaceRule(messages_for('pt'), '/pt/pt-BR/replace.txt', lt.language)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Fui de ônibus até o açougue italiano.'))) == 0
    # incorrect sentences:
    _check_simple_replace_rule(rule, lt, 'Vou de autocarro.', 'ônibus')
    _check_simple_replace_rule(rule, lt, 'O lançamento de dardo é um desporto.', 'esporte')
    _check_simple_replace_rule(rule, lt, 'Está no meu ADN!', 'DNA')
    # these are dialect-dependent but are marked as exceptions (e.g. named entities)
    _assert_no_matches(rule, lt, 'José António Miranda Coutinho')
    _assert_no_matches(rule, lt, 'Jerónimo Soares')


# --- PortugueseBarbarismRuleTest ---

def test_replace_barbarisms():
    """PortugueseBarbarismRuleTest.testReplaceBarbarisms"""
    lt = JLanguageTool(get_language('pt-BR'))
    rule = PortugueseBarbarismsRule(messages_for('pt'), '/pt/pt-BR/barbarisms.txt', lt.language)
    # These should not have matches, since they are *exceptions* (named entities, known multi-token matches,
    # etc.)
    _assert_no_matches(rule, lt, 'New York Stock Exchange')
    _assert_no_matches(rule, lt, 'Yankee Doodle, faça o morra')
    _assert_no_matches(rule, lt, 'mas inferior ao Opera Browser.')


# --- PortugueseClicheRuleTest ---

def test_cliche_rule():
    """PortugueseClicheRuleTest.testRule"""
    lt = JLanguageTool(get_language('pt'))
    rule = PortugueseClicheRule(messages_for('pt'), '/pt/cliches.txt', lt.language)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Evite as frases-feitas e as expressões idiomáticas.'))) == 0
    # incorrect sentences:
    _check_simple_replace_rule(rule, lt, 'Teste. A todo o vapor!', 'O mais rápido possível')
    _check_simple_replace_rule(rule, lt, 'A todo o vapor!', 'O mais rápido possível')
    _check_simple_replace_rule(rule, lt, 'Teste, a todo o vapor!', 'o mais rápido possível')


# --- PortugueseColourHyphenationRuleTest ---

def test_colour_hyphenation_rule():
    """PortugueseColourHyphenationRuleTest.test"""
    lt = JLanguageTool(get_language('pt-BR'))
    _disable_all_rules_except(lt, 'PT_COLOUR_HYPHENATION')
    assert len(_check_picky(lt, 'azul-claro')) == 0
    assert len(_check_picky(lt, 'azul claro')) == 1
    assert _check_picky(lt, 'azul claro')[0].get_specific_rule_id() == 'PT_COLOUR_HYPHENATION_AZUL_CLARO'


# --- PortugueseDiacriticsRuleTest ---

def test_diacritics_rule():
    """PortugueseDiacriticsRuleTest.test"""
    lt_pt = JLanguageTool(get_language('pt-PT'))
    lt_br = JLanguageTool(get_language('pt-BR'))
    _disable_all_rules_except(lt_pt, 'DIACRITICS')
    _disable_all_rules_except(lt_br, 'DIACRITICS')
    test_sentence = 'Carrinho de bebe.'
    assert _check_picky(lt_pt, test_sentence)[0].suggested_replacements[0] == 'bebé'
    assert _check_picky(lt_br, test_sentence)[0].suggested_replacements[0] == 'bebê'


# --- PortugueseOrthographyReplaceRuleTest ---

def test_orthography_replace_rule():
    """PortugueseOrthographyReplaceRuleTest.testRule"""
    lt = JLanguageTool(get_language('pt'))
    rule = PortugueseOrthographyReplaceRule(messages_for('pt'), lt.language)

    def assert_single_match(sentence, *suggestions):
        matches = rule.match(lt.get_analyzed_sentence(sentence))
        assert len(matches) == 1
        assert matches[0].rule.get_id().startswith('PT_SIMPLE_REPLACE_ORTHOGRAPHY')
        assert matches[0].suggested_replacements == list(suggestions)

    _assert_no_matches(rule, lt, 'Já volto.')
    assert_single_match('Ja volto.', 'Já')
    _assert_no_matches(rule, lt, 'Gosto de você.')
    assert_single_match('Gosto de voce.', 'você')
    _assert_no_matches(rule, lt, 'Disse-me sotto voce.')  # multi-token spelling of Italian expression


# --- PortugueseUnitConversionRuleTest ---

def _assert_unit_matches(text, expected_matches, converted, rule, lt):
    # UnitConversionRuleTestHelper.assertMatches
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_matches, 'Got matches: %s' % matches
    if expected_matches > 0 and converted is not None:
        assert any(converted in s for s in matches[0].suggested_replacements), \
            'Suggestion is correct: %s / expected: %s' % (matches[0].suggested_replacements, converted)


def test_unit_conversion_rule():
    """PortugueseUnitConversionRuleTest.match"""
    lt = JLanguageTool(get_language('pt'))
    rule = PortugueseUnitConversionRule(messages_for('pt'))
    _assert_unit_matches('Eu tenho 6 pés de altura.', 1, '1,83 metros', rule, lt)
    _assert_unit_matches('Eu tenho 6 pés (2,02 m) de altura.', 1, '1,83 metros', rule, lt)
    _assert_unit_matches('Eu tenho 6 pés (1,82 m) de altura.', 0, None, rule, lt)
    _assert_unit_matches('A via tem 100 milhas de comprimento.', 1, '160,93 quilômetros', rule, lt)
    _assert_unit_matches('A via tem 10 km (20 milhas) de comprimento.', 1, '6,21', rule, lt)
    _assert_unit_matches('A via tem 10 km (6,21 milhas) de comprimento.', 0, None, rule, lt)
    _assert_unit_matches('A via tem 100 milhas (160,93 quilômetros) de comprimento.', 0, None, rule, lt)
    _assert_unit_matches('A carga é de 10.000 libras.', 1, '4,54 toneladas', rule, lt)
    _assert_unit_matches('Isto tem 5\'6" de altura.', 1, '1,68 m', rule, lt)
    _assert_unit_matches('O meu novo apartamento tem 500 sq ft de área.', 1, '46,45 metros quadrados', rule, lt)
    _assert_unit_matches('Sendo a latitude 8º 32\' 00" e a longitude 39º 22\' 49".', 0, None, rule, lt)
    _assert_unit_matches('Sendo a latitude 8º32\'00" e a longitude 39º22\'49".', 0, None, rule, lt)
    # Same unit, assume something shady, but don't suggest conversion to the same one!
    _assert_unit_matches('Com altura de 4,8 cm (22,08 cm).', 0, None, rule, lt)
    # Composite expression (squaring); should work properly at some point, but at least now it doesn't fail
    _assert_unit_matches('Com altura de 4,8 mm x 5,2 cm (2,5 cm²).', 0, None, rule, lt)
    _assert_unit_matches('Com altura de 4,8 mm × 5,2 cm (2,5 cm²).', 0, None, rule, lt)


@pytest.mark.parametrize('text,expected', [
    # matches and suggestions of LanguageTool 6.6 (-l pt-BR -eo -e UNIDADES_METRICAS)
    ('A carga é de 10.000 libras.',
     ['10.000 libras (4,54 t)', '10.000 libras (4,54 toneladas)', '10.000 libras (aprox. 4.536 kg)',
      '10.000 libras (4.535,92 kg)', '10.000 libras (aprox. 4.536 quilogramas)',
      '10.000 libras (4.535,92 quilogramas)']),
    ('O carro ia a 60 mph na estrada.',
     ['60 mph (aprox. 97 km/h)', '60 mph (96,56 km/h)', '60 mph (aprox. 97 quilômetros por hora)',
      '60 mph (96,56 quilômetros por hora)']),
    ('A temperatura era de 100 graus Fahrenheit ontem.', None),
    ('A temperatura era de 100 °F ontem.',
     ['100 °F (aprox. 38 °C)', '100 °F (37,78 °C)', '100 °F (aprox. 38 graus Celsius)',
      '100 °F (37,78 graus Celsius)']),
    ('A caixa pesa 12 onças.',
     ['12 onças (0,45 kg)', '12 onças (0,45 quilogramas)', '12 onças (aprox. 454 g)', '12 onças (453,59 g)',
      '12 onças (aprox. 454 gramas)', '12 onças (453,59 gramas)']),
    ('Usaram 10 cubic feet de material.',
     ['10 cubic feet (0,28 m³)', '10 cubic feet (0,28 metros cúbicos)', '10 cubic feet (aprox. 283 l)',
      '10 cubic feet (283,17 l)', '10 cubic feet (aprox. 283 litros)', '10 cubic feet (283,17 litros)']),
    ('Comprou 0,125 polegadas de fio.',
     ['0,125 polegadas (3,18 mm)', '0,125 polegadas (3,18 milímetros)', '0,125 polegadas (0,32 cm)',
      '0,125 polegadas (0,32 centímetros)', '0,125 polegadas (aprox. 3.175 µm)', '0,125 polegadas (3.175 µm)']),
    # a wrong conversion to an incompatible unit: the metric equivalents of the value
    ('A sala tem 12 pés (5 kg) de largura.',
     ['12 pés (3,66 m)', '12 pés (3,66 metros)', '12 pés (aprox. 366 cm)', '12 pés (365,76 cm)',
      '12 pés (aprox. 366 centímetros)', '12 pés (365,76 centímetros)']),
    # an unknown unit in the conversion
    ('A sala tem 12 pés (3,7 xyz) de largura.',
     ['3,66 m', '3,66 metros', 'aprox. 366 cm', '365,76 cm', 'aprox. 366 centímetros', '365,76 centímetros']),
    # a metric value with a wrong conversion
    ('A velocidade foi de 100 km/h (60 mph) na reta.',
     ['aprox. 62 mph', '62,14 mph', 'aprox. 62 milhas por hora', '62,14 milhas por hora']),
    ('A velocidade foi de 100 km/h (62,14 mph) na reta.', None),
])
def test_unit_conversion_rule_like_java(text, expected):
    """The suggestions of PortugueseUnitConversionRule as in LanguageTool 6.6
    (None: no match; the Fahrenheit sentence has no match because "graus
    Fahrenheit" needs a space before "graus" in the pattern, as in Java)"""
    lt = JLanguageTool(get_language('pt-BR'))
    rule = PortugueseUnitConversionRule(messages_for('pt'))
    matches = rule.match(lt.get_analyzed_sentence(text))
    if expected is None:
        assert matches == []
    else:
        assert len(matches) == 1
        assert matches[0].suggested_replacements == expected


# --- PortugueseWordRepeatBeginningRuleTest ---

def test_word_repeat_beginning_rule():
    """PortugueseWordRepeatBeginningRuleTest.testRule"""
    lt = JLanguageTool(get_language('pt'))
    _disable_all_rules_except(lt, 'PORTUGUESE_WORD_REPEAT_BEGINNING_RULE')
    # correct sentences:
    assert len(lt.check('Este exemplo está correto. Este exemplo também está.')) == 0
    assert len(lt.check('2011: Setembro já passou. 2011: Outubro também já passou. 2011: Novembro já se foi.')) == 0
    assert len(lt.check('Certo, isto está bem. Este exemplo está correto. Certo que este também.')) == 0
    # errors:
    assert len(lt.check('Este exemplo está correto. Este segundo também. Este terceiro exemplo não.')) == 1
    assert len(lt.check('Então, este está correto. Então, este está errado, por causa da repetição.')) == 1
    # this used to cause false alarms because reset() was not implemented
    assert len(lt.check('Então, este deve ser considerado uma nova frase.')) == 0


# --- PortugueseWordRepeatRuleTest ---

def test_word_repeat_rule_ignore():
    """PortugueseWordRepeatRuleTest.testIgnore"""
    lang = get_language('pt')
    lt = JLanguageTool(lang)
    rule = PortugueseWordRepeatRule(messages_for('en'), lang)

    def ignore(text, position):
        return rule.ignore(lt.get_analyzed_sentence(text).non_blank_tokens, position)

    assert not ignore('no repetition', 2)
    assert ignore('blá blá', 2)
    assert ignore('Aaptos aaptos', 2)
    assert ignore('Logo logo vamos ao mercado', 2)
    # as of the v0.13 dict, the following is not a repetition, since 'coloquem-na' is a single token
    assert not ignore('Coloquem-na na sala.', 2)


# --- PostReformCompoundRuleTest ---

def test_post_reform_compounds():
    """PostReformCompoundRuleTest.testPostReformCompounds"""
    lt = JLanguageTool(get_language('pt-BR'))
    _disable_all_rules_except(lt, 'PT_COMPOUNDS_POST_REFORM')

    def assert_invalid_compound(text, suggestion):
        checked = _check_picky(lt, text)
        assert len(checked) == 1
        assert checked[0].suggested_replacements == [suggestion]

    assert not _check_picky(lt, 'super-herói')
    assert len(_check_picky(lt, 'super herói')) == 1
    assert _check_picky(lt, 'super herói')[0].get_specific_rule_id() == 'PT_COMPOUNDS_POST_REFORM_SUPER_HERÓI'
    assert _check_picky(lt, 'super herói')[0].rule.get_description() == \
        'Erro na formação da palavra composta "super herói"'
    assert_invalid_compound('Super estrela', 'Superestrela')
    assert_invalid_compound('web-site', 'website')
    assert_invalid_compound('Grã Bretanha', 'Grã-Bretanha')
    assert_invalid_compound('ultra-som', 'ultrassom')
    assert_invalid_compound('ultra-realismo', 'ultrarrealismo')
    assert_invalid_compound('anti semita', 'antissemita')
    assert_invalid_compound('arqui-rabino', 'arquirrabino')
    assert_invalid_compound('ópera rock', 'ópera-rock')


def test_post_reform_merge_compound():
    """PostReformPortugueseCompoundRule.mergeCompound doubles an initial r or
    s after a vowel"""
    rule = PostReformPortugueseCompoundRule(messages_for('pt'), get_language('pt-BR'))
    assert rule.merge_compound('ultra-som', False) == 'ultrassom'
    assert rule.merge_compound('Super Estrela', True) == 'Superestrela'
    assert rule.merge_compound('Super Estrela', False) == 'SuperEstrela'
    assert rule.merge_compound('auto retrato', False) == 'autorretrato'
    assert rule.merge_compound('web site', False) == 'website'


# --- PostReformPortugueseDashRuleTest, PreReformPortugueseDashRuleTest ---

def test_post_reform_dash_rule():
    """PostReformPortugueseDashRuleTest.test"""
    lt = JLanguageTool(get_language('pt-PT'))
    _disable_all_rules_except(lt, 'PT_POSAO_DASH_RULE')
    assert len(_check_picky(lt, 'ab-reação')) == 0
    assert len(_check_picky(lt, 'ab—reação')) == 1


def test_pre_reform_dash_rule():
    """PreReformPortugueseDashRuleTest.test"""
    lt = JLanguageTool(get_language('pt-AO'))
    _disable_all_rules_except(lt, 'PT_PREAO_DASH_RULE')
    assert len(_check_picky(lt, 'abaixa-língua')) == 0
    assert len(_check_picky(lt, 'abaixa—língua')) == 1


# --- UppercaseSentenceStartRuleTest ---

@pytest.mark.parametrize('text,expected', [
    ('hora de começar', 1),
    ('palavra', 0),  # not a real sentence
    ('Frase', 0),
    ('Começamos uma frase. E agora vem a outra.', 0),
    ('Mais outra frase. Âmbar é meu álbum favorito da Bethânia.', 0),
    ('Agora com abreviaturas, p. ex. esta.', 0),
    ('Agora com aspas. "Essas aqui!".', 0),
    ('"Aspas desde o começo!"', 0),
    ('— Esta, com travessão (M), é nova!', 0),
    ('– Esta, com travessão (N), é nova!', 0),
    ('- Esta, com travessão (H), é nova!', 0),
    ('Prezado Dr. Stein,\ngostaria de marcar uma nova data.', 0),
    ('legal!', 1),
    ('Começamos uma frase. e agora vem a outra.', 1),
    ('Mais outra frase. âmbar é meu álbum favorito da Bethânia.', 1),
    ('Agora com aspas. "essas aqui!".', 1),
    ('"aspas desde o começo!"', 1),
    ('— esta, com travessão, é nova!', 1),
    ('– esta, com travessão, é nova!', 1),
    ('- esta, com travessão, é nova!', 1),
])
def test_uppercase_rule(text, expected):
    """UppercaseSentenceStartRuleTest.testUppercaseRule"""
    lt = JLanguageTool(get_language('pt'))
    _disable_all_rules_except(lt, 'UPPERCASE_SENTENCE_START')
    assert len(lt.check(text)) == expected


# --- tests of excluded components ---

@pytest.mark.skip(reason='spell checking is not ported: MorfologikPortugueseSpellerRuleTest tests the rule matches, '
                         'suggestions and dialect messages of MorfologikPortugueseSpellerRule')
def test_morfologik_portuguese_speller_rule():
    """Port of org.languagetool.rules.pt.MorfologikPortugueseSpellerRuleTest"""


@pytest.mark.skip(reason='remote rules are not ported: PortugueseRemoteRuleFilterTest tests the filters of the '
                         'remote rules (remote-rule-filters.xml)')
def test_remote_rule_filters():
    """Port of org.languagetool.rules.pt.PortugueseRemoteRuleFilterTest"""


# --- other rules ---

def test_english_contraction_spelling_rule():
    """EnglishContractionSpellingRule: case sensitive, the example pair"""
    lt = JLanguageTool(get_language('pt-BR'))
    rule = EnglishContractionSpellingRule(messages_for('pt'), lt.language)
    matches = rule.match(lt.get_analyzed_sentence('Ele adorava assistir whats cooking às sextas-feiras.'))
    assert [m.suggested_replacements for m in matches] == [["what's"]]
    assert matches[0].message == 'Caso seja uma contração da língua inglesa, prefira "what\'s".'


def test_weasel_words_rule():
    """PortugueseWeaselWordsRule (not used by Portuguese, commented out in
    Java): uses Portuguese.getInstance()"""
    rule = PortugueseWeaselWordsRule(messages_for('pt'))
    assert rule.language is get_language('pt')
    assert rule.get_id() == 'PT_WEASELWORD_REPLACE'


def test_filler_words_rule():
    """PortugueseFillerWordsRule: id FILLER_WORDS_PT, "mas" after a comma is
    no filler word, default off"""
    lang = get_language('pt')
    rule = PortugueseFillerWordsRule(messages_for('pt'), lang)
    assert rule.get_id() == 'FILLER_WORDS_PT'
    assert rule.default_off
    tokens = JLanguageTool(lang).get_analyzed_sentence('Sim, mas mas.').non_blank_tokens
    assert rule.is_exception(tokens, 3)
    assert not rule.is_exception(tokens, 4)


def test_readability_rule():
    """PortugueseReadabilityRule: ids, messages, the Portuguese Flesch
    reading ease and syllable count"""
    lang = get_language('pt')
    easy = PortugueseReadabilityRule(messages_for('pt'), lang, None, True)
    hard = PortugueseReadabilityRule(messages_for('pt'), lang, None, False)
    assert (easy.get_id(), hard.get_id()) == ('READABILITY_RULE_SIMPLE_PT', 'READABILITY_RULE_DIFFICULT_PT')
    assert easy.default_off and hard.default_off
    assert easy.category.id == 'TEXT_ANALYSIS'
    assert easy.get_flesch_reading_ease(10.0, 2.0) == pytest.approx(206.84 - 10.2 - 120.0)
    assert [easy.simple_syllables_count(w) for w in ('', 'casa', 'saudade', 'aéreo', 'Brasil', 'rua', 'x')] == \
        [0, 2, 3, 3, 2, 1, 1]
    assert hard.get_message(1, 40, 25, 2) == ('Legibilidade {FRE: 40, ASL: 25, ASW: 2}: O texto deste parágrafo é '
                                              'difícil {Nível 1: Complexo}. Tem muitas palavras por frase e muitas '
                                              'sílabas por palavra.')


def test_accentuation_check_rule():
    """PortugueseAccentuationCheckRule: verbs without accent that are nouns
    or adjectives with accent in the context (default off)"""
    lt = JLanguageTool(get_language('pt-BR'))
    rule = PortugueseAccentuationCheckRule(messages_for('pt'), lt.language)
    assert rule.default_off
    assert rule.get_id() == 'ACCENTUATION_CHECK_PT'
    matches = rule.match(lt.get_analyzed_sentence('Ele fez uma critica dura.'))
    assert [(m.from_pos, m.to_pos, m.suggested_replacements) for m in matches] == [(12, 19, ['crítica'])]
    assert matches[0].message == 'Se é um nome ou um adjectivo, tem acento.'
    assert not rule.match(lt.get_analyzed_sentence('Ele critica a decisão.'))


# --- filters ---

def _match(lt, sentence, from_pos, to_pos, suggestions=(), message='msg'):
    class _Rule(Rule):
        def get_id(self):
            return 'TEST_RULE'

        def get_description(self):
            return 'test'

    rule = _Rule()
    rule.language = lt.language
    rm = RuleMatch(rule, lt.get_analyzed_sentence(sentence), from_pos, to_pos, message)
    rm.set_suggested_replacements(list(suggestions))
    return rm


def test_enclisis_filter():
    """PortugueseEnclisisFilter: the verb with the pronoun attached"""
    lt = JLanguageTool(get_language('pt-BR'))
    tokens = lt.get_analyzed_sentence('Eu o vi ontem.').non_blank_tokens
    m = _match(lt, 'Eu o vi ontem.', 3, 7)
    f = PortugueseEnclisisFilter()
    r = f.accept_rule_match(m, {'verbPos': '3', 'pronounPos': '2'}, 0, tokens, [])
    assert r.suggested_replacements == ['vi-o']
    # no personal pronoun: no match
    assert f.accept_rule_match(m, {'verbPos': '3', 'pronounPos': '4'}, 0, tokens, []) is None


def test_proclisis_filter():
    """PortugueseProclisisFilter: the pronoun before the verb"""
    lt = JLanguageTool(get_language('pt-BR'))
    tokens = lt.get_analyzed_sentence('Não fá-lo.').non_blank_tokens
    m = _match(lt, 'Não fá-lo.', 4, 9)
    r = PortugueseProclisisFilter().accept_rule_match(m, {}, 0, tokens[:3], [])
    # fá-lo: the present (faz) and the imperative (faze), in the order of the Java HashSet
    assert r.suggested_replacements == ['o faz', 'o faze']


def test_regular_irregular_participle_filter():
    """RegularIrregularParticipleFilter: the other participle of verbs with
    two participles"""
    lt = JLanguageTool(get_language('pt-BR'))
    sentence = 'Ele tinha imprimido o livro.'
    tokens = lt.get_analyzed_sentence(sentence).non_blank_tokens
    m = _match(lt, sentence, 10, 19, ['{suggestion}'])
    f = RegularIrregularParticipleFilter()
    r = f.accept_rule_match(m, {'direction': 'RegularToIrregular'}, 0, tokens, [])
    assert r.suggested_replacements == ['impresso']
    assert f.accept_rule_match(m, {'direction': 'IrregularToRegular'}, 0, tokens, []) is None


def test_confusion_check_filter():
    """ConfusionCheckFilter: the confusion pairs of the variant"""
    lt = JLanguageTool(get_language('pt-BR'))
    words_br = _relevant_words(lt.language, 'pt-BR')
    words_pt = _relevant_words(lt.language, 'pt-PT')
    form = next(iter(words_br))
    token, tag = words_br[form][0]
    m = _match(lt, 'Um teste.', 3, 8, ['{suggestion}'])
    r = ConfusionCheckFilter().accept_rule_match(m, {'form': form, 'postag': tag}, 0, [], [])
    assert r.suggested_replacements == [token]
    assert ConfusionCheckFilter().accept_rule_match(m, {'form': 'xyzxyz', 'postag': '.*'}, 0, [], []) is None
    assert len(words_pt) > 0


def test_brazilian_toponym_filter():
    """BrazilianToponymFilter (a regex rule filter) with
    BrazilianToponymMap"""
    lt = JLanguageTool(get_language('pt-BR'))
    toponym_map = _brazilian_toponym_map(lt.language)
    assert toponym_map.is_valid_toponym('Rio de Janeiro')
    assert toponym_map.is_valid_toponym('Venho do Rio de Janeiro')
    assert toponym_map.is_valid_toponym('Feira-de-Santana')
    assert not toponym_map.is_valid_toponym('Xyzópolis')
    assert toponym_map.is_toponym_in_state('feira de santana', 'BA')
    assert 'SP' in toponym_map.get_states_with_municipality('campinas')

    class _M:
        def __init__(self, *groups):
            self.groups = groups

        def group(self, i):
            return self.groups[i - 1]

    m = _match(lt, 'Campinas-SP', 8, 11)
    r = BrazilianToponymFilter().accept_rule_match(m, {}, None, _M('Campinas', '-SP', 'SP'))
    assert r.suggested_replacements == ['–SP']
    assert BrazilianToponymFilter().accept_rule_match(m, {}, None, _M('Campinas', '–SP', 'SP')) is None
    assert BrazilianToponymFilter().accept_rule_match(m, {}, None, _M('Xyzópolis', '-SP', 'SP')) is None


def test_roman_numeral_filter():
    """RomanNumeralFilter"""
    lt = JLanguageTool(get_language('pt'))
    m = _match(lt, 'Século 21.', 7, 9)
    assert RomanNumeralFilter().accept_rule_match(m, {'arabicSource': '21'}, 0, [], []).suggested_replacements == \
        ['XXI']


def test_advanced_synthesizer_filter():
    """AdvancedSynthesizerFilter: isSuggestionException and the
    keepPronoun POS tag replacement"""
    f = AdvancedSynthesizerFilter()
    assert f.is_suggestion_exception('amamo', 'VMIP1P0')
    assert not f.is_suggestion_exception('amamos', 'VMIP1P0')
    assert not f.is_suggestion_exception('ama', 'VMIP3S0')
    assert f.get_composite_postag('V.*', 'V.*', 'VMIP3S0:PP3MSA00', 'VMIS3S0', 'keepPronoun') == 'VMIS3S0:PP3MSA00'
    assert f.get_composite_postag('V.*', 'V.*', 'VMIP3S0', 'VMIS3S0', 'keepPronoun') == 'VMIS3S0'


def test_date_filters():
    """DateCheckFilter, FutureDateFilter, NewYearDateFilter and the YMD
    filters (with DateFilterHelper)"""
    lt = JLanguageTool(get_language('pt'))
    f = DateCheckFilter()
    assert f.get_day_of_week('Segunda-feira') == 2
    assert f.get_day_of_week('sáb.') == 7
    assert f.get_month('Fevereiro') == 2
    assert f.get_month('dez') == 12
    with pytest.raises(RuntimeError):
        f.get_month('xyz')
    from langtool.rules.core_filters import CalendarDate
    assert f.get_day_of_week_name(CalendarDate.of(2014, 0, 1)) == 'quarta-feira'
    assert FutureDateFilter().get_month('março') == 3
    m = _match(lt, 'Um teste.', 3, 8, message='Ano {year}, {realYear}')
    r = NewYearDateFilter().accept_rule_match(m, {'year': '2013', 'month': 'out', 'day': '3'}, 0, [], [])
    assert r.message == 'Ano 2013, 2014'
    m = _match(lt, 'Um teste.', 3, 8, message='{realDate}')
    r = YMDNewYearDateFilter().accept_rule_match(m, {'date': '2013-10-31'}, 0, [], [])
    assert r.message == '2014-10-31'
    with pytest.raises(RuntimeError):
        YMDNewYearDateFilter().accept_rule_match(m, {'date': '2013-10-31', 'year': '2013'}, 0, [], [])
    # as in Java, the 'date' argument (a date, not a token position) cannot be parsed by
    # AbstractDateCheckWithSuggestionsFilter (NumberFormatException, an IllegalArgumentException)
    tokens = lt.get_analyzed_sentence('Quinta-feira, 2013-10-31.').non_blank_tokens
    with pytest.raises(ValueError):
        YMDDateCheckFilter().accept_rule_match(m, {'weekDay': '1', 'date': '2013-10-31'}, 0, tokens, [1, 1, 1])


def test_no_disambiguation_partial_pos_tag_filter():
    """NoDisambiguationPortuguesePartialPosTagFilter: tags without
    disambiguation"""
    f = NoDisambiguationPortuguesePartialPosTagFilter()
    tokens = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0),
              AnalyzedTokenReadings([AnalyzedToken('Lisboa™', None, None)], 0)]
    m = _match(JLanguageTool(get_language('pt')), 'Lisboa™', 0, 7)
    args = {'no': '2', 'regexp': '(\\w+)[™®]', 'postag_regexp': 'NP.+'}
    assert f.accept_rule_match(m, args, 0, tokens, []) is m
    assert f.accept_rule_match(m, dict(args, postag_regexp='V.+'), 0, tokens, []) is None


# --- the misspelling check and the multitoken speller ---

def test_spelling_check():
    """The misspelling check of MorfologikPortugueseSpellerRule (the default
    spelling rule): the speller dictionary of the variant (the default
    variant pt-PT for pt)"""
    checks = {code: get_language(code).get_default_spelling_rule() for code in ('pt', 'pt-PT', 'pt-BR', 'pt-AO')}
    assert all(isinstance(c, MorfologikPortugueseSpellerCheck) for c in checks.values())
    assert [checks[c].get_file_name() for c in ('pt', 'pt-PT', 'pt-BR', 'pt-AO')] == [
        '/pt/spelling/pt-PT-90.dict', '/pt/spelling/pt-PT-90.dict', '/pt/spelling/pt-BR.dict',
        '/pt/spelling/pt-PT-45.dict']
    assert get_language('pt-MZ').get_default_spelling_rule().get_file_name() == '/pt/spelling/pt-PT-45.dict'
    assert not checks['pt-BR'].is_misspelled('fato')
    assert checks['pt-BR'].is_misspelled('facto')
    assert not checks['pt-PT'].is_misspelled('facto')
    assert checks['pt-PT'].is_misspelled('acção')
    assert not checks['pt-AO'].is_misspelled('acção')
    assert checks['pt'].is_misspelled('xyzzq')


def test_prepare_line_for_speller():
    """Portuguese.prepareLineForSpeller"""
    assert prepare_line_for_speller('São Paulo\tNPCSG00') == ['São Paulo']
    assert prepare_line_for_speller('ad hoc\t_Latin_') == ['ad hoc']
    assert prepare_line_for_speller('a cada semana\tRG') == ['']
    assert prepare_line_for_speller('palavra') == ['palavra']
    assert prepare_line_for_speller('Nova Iorque;NPCNG00 # comment') == ['Nova Iorque']


def test_multitoken_speller():
    """PortugueseMultitokenSpeller (for pt-PT, used by all variants)"""
    speller = get_language('pt-BR').get_multitoken_speller()
    assert isinstance(speller, PortugueseMultitokenSpeller)
    assert speller is get_language('pt').get_multitoken_speller()
    assert speller.language is get_language('pt-PT')
    assert speller.get_suggestions('Nova Iorqe') == ['Nova Iorque']
    assert speller.get_suggestions('Nova Iorque') == []
