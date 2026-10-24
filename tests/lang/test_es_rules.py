"""Port of the tests of the Spanish rules: org.languagetool.rules.es.
CompoundRuleTest, QuestionMarkRuleTest, SimpleReplaceRuleTest,
SimpleReplaceVerbsRuleTest, SpanishRepeatedWordsRuleTest,
SpanishUnpairedBracketsRuleTest, SpanishWikipediaRuleTest,
SpanishWordRepeatBeginningRuleTest, SpanishWordRepeatRuleTest,
SpanishWrongWordInContextRuleTest, MorfologikSpanishSpellerRuleTest and
LanguageSpecificSpellcheckerTest (skipped, spell checking),
SpanishConfusionProbabilityRuleTest (skipped, language model) and
SpanishRemoteRuleFilterTest (skipped, remote rules), plus checks of the
Spanish filters."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.es import adapt_suggestion
from langtool.lang.es.filters import (ConfusionCheckFilter, DateCheckFilter, FindSuggestionsFilter, NewYearDateFilter,
                                      SpanishNumberInWordFilter, TextToNumberFilter)
from langtool.lang.es.rules import (CompoundRule, QuestionMarkRule, SimpleReplaceRule, SimpleReplaceVerbsRule,
                                    SpanishRepeatedWordsRule, SpanishUnpairedBracketsRule, SpanishWikipediaRule,
                                    SpanishWordRepeatRule, SpanishWrongWordInContextRule)
from langtool.lang.es.spelling import prepare_line_for_speller
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('es')


@pytest.fixture(scope='module')
def spanish():
    return get_language('es')


@pytest.fixture(scope='module')
def lt(spanish):
    return JLanguageTool(spanish)


class FakeRule(Rule):
    def __init__(self, language=None):
        super().__init__()
        self.language = language

    def get_id(self):
        return 'FAKE-RULE'

    def get_description(self):
        return 'Fake rule'


def _java_list(items):
    return '[' + ', '.join(items) + ']'


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule(spanish, lt):
    """CompoundRuleTest.testRule (setUp runs AbstractCompoundRuleTest.testAllCompounds,
    which only prints warnings for possibly misspelled suggestions)"""
    rule = CompoundRule(messages_for('es'), spanish, None)
    data = rule.get_compound_rule_data()
    for compound in data.incorrect_compounds:
        if compound in data.dash_suggestion:
            rule.is_misspelled(compound.replace(' ', '-'))
        if compound in data.joined_suggestion:
            rule.is_misspelled(rule.merge_compound(compound, compound in data.joined_lower_case_suggestion))
    # correct sentences:
    _check(lt, rule, 0, 'Guinea-Conakri')
    # incorrect sentences:
    _check(lt, rule, 1, 'Guinea Bisáu', 'Guinea-Bisáu')


def test_compound_rule_specific_ids(spanish, lt):
    rule = CompoundRule(messages_for('es'), spanish, None)
    m, = rule.match(lt.get_analyzed_sentence('Guinea Bisáu'))
    assert m.rule.get_id() == 'ES_COMPOUNDS_GUINEA_BISÁU'
    assert m.rule.get_description() == 'Palabras compuestas con guion: Guinea Bisáu'
    assert rule.is_misspelled('blablabla') and not rule.is_misspelled('casa')


# --- QuestionMarkRuleTest ---

@pytest.fixture(scope='module')
def question_lt(spanish):
    lt = JLanguageTool(spanish)
    for r in lt.get_all_active_rules():
        if r.get_id() != 'ES_QUESTION_MARK':
            lt.disable_rule(r.get_id())
    return lt


def test_question_mark_rule(spanish, question_lt):
    """QuestionMarkRuleTest.test"""
    rule = QuestionMarkRule(messages_for('en'))
    lt = question_lt

    def check(s):
        return rule.match(lt.analyze_text(s))

    def suggestions(m):
        return _java_list(m.suggested_replacements)

    assert len(check('Hola, ¿cómo estás?')) == 0
    matches = check('Hola, cómo estás?')
    assert len(matches) == 1
    assert suggestions(matches[0]) == '[¿cómo]'
    assert len(check('¿Que pasa?')) == 0
    matches = check('Que pasa?')
    assert len(matches) == 1
    assert suggestions(matches[0]) == '[¿Que]'
    matches = check('Que pasa?\n')
    assert len(matches) == 1
    assert suggestions(matches[0]) == '[¿Que]'
    for text in ('Que pasa?', 'Que pasa?\n', 'Que pasa?\n\n'):
        matches = lt.check(text)
        assert len(matches) == 1
        assert suggestions(matches[0]) == '[¿Que]'
    assert len(lt.check('¿Que pasa?\n\n')) == 0
    assert len(lt.check('¡¿Nunca tienes clases o qué?!')) == 0
    assert len(lt.check('¡Usted tiene un gusto caro! -exclamó la dependienta- ¿Está seguro?')) == 0
    assert len(lt.check('¿Quién sabe hablar francés mejor: Tom o Mary?')) == 0
    matches = lt.check('Esto es una prueba. Que pasa?\n\n')
    assert len(matches) == 1
    assert suggestions(matches[0]) == '[¿Que]'
    assert matches[0].from_pos == 20
    matches = check('Hola, de qué me hablas?')
    assert len(matches) == 1
    assert suggestions(matches[0]) == '[¿de]'
    matches = check('Después de todo lo que pasó, qué quieres que te diga?')
    assert len(matches) == 1
    assert suggestions(matches[0]) == '[¿qué]'
    assert suggestions(check('Pero cómo quieres que te lo diga?')[0]) == '[¿Pero]'
    assert suggestions(check('Pero, cómo quieres que te lo diga?')[0]) == '[¿cómo]'
    assert suggestions(check('Puedes imaginarte por qué no vino con nosotros?')[0]) == '[¿Puedes]'
    assert suggestions(check('Hola, Marco: Puedes darme tu dirección de correo?')[0]) == '[¿Puedes]'
    url = 'https://gtlb.com/smll-cued-datasets/hu[…]nitized/-/tree/main/beling?ref_type=heads'
    assert len(check('Están aquí: ' + url)) == 0
    # Exclamation marks:
    for text, expected in (('Qué irritante!', '[¡Qué]'), ('—Hola!', '[¡Hola]'),
                           ('Muchas gracias! ✌️', '[¡Muchas]'),
                           ('Muchas gracias! ✌️✌️', '[¡Muchas]'),
                           ('Muchas gracias! ✌️ ✌️', '[¡Muchas]'),
                           ('Muchas gracias!, le dijo entonces.', '[¡Muchas]'),
                           ('"Muchas gracias!".', '[¡Muchas]'),
                           ('Seguro que estás más habituado a algunas de estas formas verbales, pero cuál es la '
                            'correcta?', '[¿pero]'),
                           ('Tengo razón, o no?', '[¿o]'), ('Tengo razón, no?', '[¿no]'),
                           ('Tengo razón, eh?', '[¿eh]'), ('qué me recomendarías???….', '[¿qué]')):
        matches = lt.check(text)
        assert len(matches) == 1, text
        assert suggestions(matches[0]) == expected, text
    assert len(lt.check('¡Qué irritante!')) == 0


# --- SimpleReplaceRuleTest ---

def test_simple_replace_rule(spanish, lt):
    """SimpleReplaceRuleTest.testRule"""
    rule = SimpleReplaceRule(messages_for('es'), spanish)
    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence('sanitización'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'desinfección'
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Esta frase no tiene errores.'))) == 0


def test_simple_replace_rule_details(spanish, lt):
    rule = SimpleReplaceRule(messages_for('es'), spanish)
    m, = rule.match(lt.get_analyzed_sentence('Sanitización'))
    assert m.suggested_replacements == ['Desinfección']
    assert m.message == '¿Quería decir «desinfección»?'
    assert m.rule.get_id() == 'ES_SIMPLE_REPLACE_SIMPLE_SANITIZACIÓN'


# --- SimpleReplaceVerbsRuleTest ---

def test_simple_replace_verbs_rule(spanish, lt):
    """SimpleReplaceVerbsRuleTest.testRule"""
    rule = SimpleReplaceVerbsRule(messages_for('ca'), spanish)
    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence('clickeaban'))
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == '[clicaban, cliqueaban, hacían clic]'


# --- SpanishRepeatedWordsRuleTest ---

def _repeated_words_matches(rule, lt, sentences):
    return rule.match(lt.analyze_text(sentences))


def test_repeated_words_rule(spanish, lt):
    """SpanishRepeatedWordsRuleTest.testRule"""
    rule = SpanishRepeatedWordsRule(messages_for('es'))

    def assert_correct_text(sentences):
        assert len(_repeated_words_matches(rule, lt, sentences)) == 0

    assert_correct_text('Emplearon la fuerza. Pero los empleados se resistieron.')
    assert_correct_text('Antes dije esto. Antes de venir.')
    assert_correct_text('Propuse aquello. Pero la propuesta no fue acceptada.')
    assert_correct_text('Creó cosas interesantes. Pero creo que no eran útiles.')
    assert_correct_text(
        'Fue excelente. El arquitecto de la catedral parece ser que fue el maestro Enrique, seguramente natural '
        'de Francia, que ya había trabajado anteriormente en la catedral de Burgos. Es evidente que conocía la '
        'forma arquitectónica gótica de la isla de Francia. Falleció en el año 1277 y fue sustituido por el '
        'español Juan Pérez. En el año 1289 fallecía también el obispo Martín Fernández, cuando la cabecera del '
        'templo ya estaba abierta al culto. La estructura fundamental de la catedral se finaliza pronto, en el '
        'año 1302, abriendo el obispo Gonzalo Osorio la totalidad de la iglesia a los fieles, aunque en el siglo '
        'xiv aún se terminarían el claustro y la torre norte; la torre sur no se finalizó hasta la segunda mitad '
        'del siglo xv. Esta prontitud en el acabamiento de las obras le da una gran unidad de estilo '
        'arquitectónico. La catedral de León se inspira en la planta de la catedral de Reims (aunque esta es de '
        'menor superficie), que bien pudo conocer el maestro Enrique. Al igual que la mayoría de catedrales '
        'francesas, la de León está construida con un módulo geométrico basado en el triángulo (ad triangulum), '
        'cuyos miembros se relacionan con la raíz cuadrada de 3, al que responden la totalidad de sus partes y '
        'del todo. Este aspecto, como la planta, los alzados, y los repertorios decorativos y simbólicos '
        'convierten esta catedral en un auténtico edificio transpirenaico, alejado de la corriente hispánica, '
        'que le ha merecido los calificativos de «la más francesa de las catedrales españolas» o el de Pulchra '
        'Leonina. Fue excelente.')
    assert_correct_text('Yo propuse aquello. Pero también propuse esto otro.')
    assert_correct_text('Yo propuse aquello. Pero propuse también esto otro.')

    matches = _repeated_words_matches(
        rule, lt, 'Yo propuse aquello. Pero la sugerencia propuesta por el presidente no fue acceptada.')
    assert len(matches) == 1
    matches = _repeated_words_matches(
        rule, lt, 'Propuse aquello. Pero la sugerencia propuesta por el presidente no fue acceptada.')
    assert len(matches) == 1
    matches = _repeated_words_matches(rule, lt, 'Fue excelente. Fue un resultado excelente.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:3] == ['magnífico', 'fantástico', 'maravilloso']
    matches = _repeated_words_matches(rule, lt, 'Esto propuse. ¿Propones tu algo diferente?')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:2] == ['Sugieres', 'Recomiendas']
    matches = _repeated_words_matches(rule, lt, 'Inicia el debate. Inicia la conversación.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:3] == ['Comienza', 'Empieza', 'Pone en marcha']


def test_repeated_words_rule_details(spanish):
    rule = SpanishRepeatedWordsRule(messages_for('es'))
    assert rule.get_id() == 'ES_REPEATEDWORDS'
    assert rule.tags == ['picky']
    assert rule.adjust_postag('NCCN000') == 'NC..000'
    assert rule.adjust_postag('AQ0MS0') == 'AQ0[MC][SN]0'
    assert rule.adjust_postag('VMIP3S0') == 'VMIP3S0'
    assert len(rule.get_anti_patterns()) == 5


# --- SpanishUnpairedBracketsRuleTest ---

def test_unpaired_brackets_rule(spanish, lt):
    """SpanishUnpairedBracketsRuleTest.testSpanishRule"""
    rule = SpanishUnpairedBracketsRule(messages_for('en'))

    def assert_matches(text, expected):
        assert len(rule.match([lt.get_analyzed_sentence(text)])) == expected, text

    def assert_correct_text(text):
        assert len(rule.match(lt.analyze_text(text))) == 0, text

    # correct sentences:
    assert_matches('Soy un hombre (muy honrado).', 0)
    assert_matches("D'Hondt.", 0)
    assert_matches('Guns N’ Roses', 0)
    assert_matches("Guns N' Roses", 0)
    assert_matches('D’Hondt.', 0)
    assert_matches('L’Équipe', 0)
    assert_matches('rock ’n’ roll', 0)
    assert_matches("Harper's Dictionary of Classical Antiquities", 0)
    assert_matches('Harper’s Dictionary of Classical Antiquities', 0)
    # incorrect sentences:
    assert_matches('Soy un hombre muy honrado).', 1)
    assert_matches('Soy un hombre (muy honrado.', 1)
    assert_matches('Eso es “importante y qué pasa. ', 1)
    assert_matches('Eso es "importante y qué. ', 1)
    assert_matches('Eso es (imposible. ', 1)
    assert_matches('Eso es (imposible.\n\n', 1)
    assert_matches('Eso es) imposible. ', 1)
    assert_matches('Eso es imposible).\t\n ', 1)
    assert_matches('Eso es «importante, ¿ah que sí?', 1)
    assert_correct_text('\n\na) New York\nb) Boston\n')
    assert_correct_text('\n\n1.) New York\n2.) Boston\n')
    assert_correct_text('\n\nXII.) New York\nXIII.) Boston\n')
    assert_correct_text('\n\nA) New York\nB) Boston\nC) Foo\n')


def test_unpaired_brackets_rule_suggestions(spanish, lt):
    """The suggestions add the other symbol next to the unpaired one (in the
    right order for opening and closing symbols) or remove it"""
    rule = SpanishUnpairedBracketsRule(messages_for('es'))
    assert rule.get_id() == 'ES_UNPAIRED_BRACKETS'
    m, = rule.match([lt.get_analyzed_sentence('Soy un hombre (muy honrado.')])
    assert m.suggested_replacements == ['()', '']
    m, = rule.match([lt.get_analyzed_sentence('Soy un hombre muy honrado).')])
    assert m.suggested_replacements == ['()', '']
    m, = rule.match([lt.get_analyzed_sentence('Eso es «importante, ¿ah que sí?')])
    assert m.suggested_replacements == ['«»', '']


# --- SpanishWikipediaRuleTest ---

def test_wikipedia_rule(spanish, lt):
    """SpanishWikipediaRuleTest.testRule"""
    rule = SpanishWikipediaRule(messages_for('es'))
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('Estas frases no tienen errores frecuentes en la Wikipedia.'))) \
        == 0

    # incorrect sentences:
    def check_simple_replace_rule(sentence, word):
        matches = rule.match(lt.get_analyzed_sentence(sentence))
        assert len(matches) == 1, sentence
        assert len(matches[0].suggested_replacements) == 1, sentence
        assert matches[0].suggested_replacements[0] == word, sentence

    # at the beginning of a sentence (replace rule is case-sensitive)
    check_simple_replace_rule('Sucedió ayer. Murio sin que nadie lo esperase.', 'Murió')
    check_simple_replace_rule('Murio sin que nadie lo esperase.', 'Murió')
    # inside sentence
    check_simple_replace_rule('Ayer murio sin que nadie lo esperase.', 'murió')
    assert rule.default_off


# --- SpanishWordRepeatBeginningRuleTest ---

def test_word_repeat_beginning_rule(spanish):
    """SpanishWordRepeatBeginningRuleTest.testRule"""
    lt = JLanguageTool(spanish)
    lt.enable_rule('SPANISH_WORD_REPEAT_BEGINNING_RULE')  # even if it is temp_off
    lt.disable_rule('ES_REPEATEDWORDS')

    def get_rule_matches(text):
        return [m for m in lt.check(text, level='PICKY')]

    # ================== correct sentences ===================
    # two successive sentences that start with the same non-adverb word.
    assert len(get_rule_matches('Esto está bien. Esto es mejor, también.')) == 0
    # three successive sentences that start with the same exception word ("the").
    assert len(get_rule_matches('El coche. El profesor. El tercer elemento.')) == 0
    assert len(get_rule_matches(
        'Por un lado, confirmó que la palabra solo no debe llevar tilde, según las reglas generales de '
        'acentuación, ni cuando es adverbio, ni cuando es adjetivo. Por otro lado, y este es el tema que hoy nos '
        'interesa, confirmó que los demostrativos este, ese o aquel, y sus formas femeninas y plurales, no '
        'llevarán tampoco tilde funcionando tanto como pronombres como determinantes.')) == 0
    # =================== errors =============================
    assert len(get_rule_matches('Mañana me voy. Mañana vuelvo. Mañana se acabó todo.')) == 2
    # three successive sentences that start with the same non-exception word
    matches1 = get_rule_matches('Yo creo. Yo he visto esto antes. Yo no lo creo.')
    assert len(matches1) == 1
    # check suggestions
    assert matches1[0].suggested_replacements[:3] == ['Además, yo', 'Igualmente, yo', 'No solo eso, sino que yo']
    matches2 = get_rule_matches('También, juego a fútbol. También, juego a baloncesto.')
    assert len(matches2) == 1
    assert _java_list(matches2[0].suggested_replacements) == '[Adicionalmente, Asimismo, Además, Igualmente, ' \
                                                             'Así mismo]'
    matches3 = get_rule_matches('Sin embargo, me gusta. Sin embargo, otros me gustan más.')
    assert len(matches3) == 1
    # TODO add suggestions
    assert _java_list(matches3[0].suggested_replacements) == '[]'
    matches4 = get_rule_matches('Pero me gusta. Pero otros me gustan más.')
    assert len(matches4) == 1
    assert _java_list(matches4[0].suggested_replacements) == '[Aun así, Por otra parte, Sin embargo]'


# --- SpanishWordRepeatRuleTest ---

def test_word_repeat_rule(spanish, lt):
    """SpanishWordRepeatRuleTest.testRule"""
    rule = SpanishWordRepeatRule(messages_for('ca'), spanish)
    # correct
    assert len(rule.match(lt.get_analyzed_sentence('Bienvenido/a a LanguageTool.'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('HUCHA-GANGA.ES es la web de referencia.'))) == 0


def test_word_repeat_rule_allow_repeat(spanish, lt):
    """Words tagged _allow_repeat (by the disambiguator) are no
    repetitions"""
    rule = SpanishWordRepeatRule(messages_for('es'), spanish)
    assert rule.get_id() == 'SPANISH_WORD_REPEAT_RULE'
    assert len(rule.match(lt.get_analyzed_sentence('Era muy muy bonito.'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Era la la casa.'))) == 1


# --- SpanishWrongWordInContextRuleTest ---

def test_wrong_word_in_context_rule(spanish, lt):
    """SpanishWrongWordInContextRuleTest.testRule"""
    # (Java passes null messages, which the Python rules don't support)
    rule = SpanishWrongWordInContextRule(messages_for('es'), spanish)
    # infligir / infringir
    matches = rule.match(lt.get_analyzed_sentence('Le infringió un duro castigo'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'infligió'
    matches = rule.match(lt.get_analyzed_sentence('Infligía todas las normas.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Infringía'
    # baca /vaca
    matches = rule.match(lt.get_analyzed_sentence('La baca da leche.'))
    assert len(matches) == 2
    assert matches[0].suggested_replacements[0] == 'vaca'
    matches = rule.match(lt.get_analyzed_sentence('Pon la maleta en la vaca.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'baca'


# --- skipped Java tests ---

@pytest.mark.skip(reason='spell checking is not ported: MorfologikSpanishSpellerRuleTest tests the rule matches '
                         'and suggestions of MorfologikSpanishSpellerRule')
def test_morfologik_spanish_speller_rule():
    """Port of org.languagetool.rules.es.MorfologikSpanishSpellerRuleTest"""


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the '
                         'spelling.txt/ignore.txt word lists with MorfologikSpanishSpellerRule')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.es.LanguageSpecificSpellcheckerTest"""


@pytest.mark.skip(reason='language model rules are not ported: SpanishConfusionProbabilityRuleTest constructs '
                         'a SpanishConfusionProbabilityRule')
def test_confusion_probability_rule():
    """Port of org.languagetool.rules.es.SpanishConfusionProbabilityRuleTest"""


@pytest.mark.skip(reason='remote rules are not ported: SpanishRemoteRuleFilterTest tests the filters of '
                         'remote-rule-filters.xml for remote (AI) rules')
def test_remote_rule_filters():
    """Port of org.languagetool.rules.es.SpanishRemoteRuleFilterTest"""


# --- filters ---

def _fake_match(spanish, message='msg', suggestion=None, from_pos=0, to_pos=5, sentence=None):
    m = RuleMatch(FakeRule(spanish), sentence, from_pos, to_pos, message)
    if suggestion is not None:
        m.set_suggested_replacement(suggestion)
    return m


def test_confusion_check_filter(spanish, lt):
    """ConfusionCheckFilter with /es/confusion_pairs.txt: the confused
    form replaces {suggestion} (with the case of the form); with
    gendernumberFrom it must agree with that token"""
    f = ConfusionCheckFilter()
    m = f.accept_rule_match(_fake_match(spanish, 'La palabra se escribe con tilde.', '{suggestion}'),
                            {'form': 'Deposito', 'postag': 'N.*'}, 0, [], [])
    assert m is not None
    assert m.suggested_replacements == ['Depósito']
    assert m.message == 'La palabra se escribe con tilde.'
    assert f.accept_rule_match(_fake_match(spanish, 'x', '{suggestion}'),
                               {'form': 'casa', 'postag': 'N.*'}, 0, [], []) is None
    tokens = lt.get_analyzed_sentence('el deposito').non_blank_tokens
    m = f.accept_rule_match(_fake_match(spanish, 'x', '{suggestion}'),
                            {'form': 'deposito', 'postag': 'N.*', 'gendernumberFrom': '1'}, 1, tokens[1:], [])
    assert m is not None and m.suggested_replacements == ['depósito']
    tokens = lt.get_analyzed_sentence('las deposito').non_blank_tokens
    assert f.accept_rule_match(_fake_match(spanish, 'x', '{suggestion}'),
                               {'form': 'deposito', 'postag': 'N.*', 'gendernumberFrom': '1'}, 1, tokens[1:],
                               []) is None


def test_date_filters(spanish):
    """DateCheckFilter and NewYearDateFilter (DateFilterHelper)"""
    f = DateCheckFilter()
    assert f.get_day_of_week('Domingo') == 1
    assert f.get_day_of_week('sa') == 7
    assert f.get_day_of_week('miércoles') == 4
    assert f.get_month('marzo') == 3 and f.get_month('mzo') == 3 and f.get_month('jn') == 6
    assert f.get_month('Septiembre') == 9 and f.get_month('dic.') == 12
    with pytest.raises(RuntimeError):
        f.get_month('foo')
    with pytest.raises(RuntimeError):
        f.get_day_of_week('foo')
    assert NewYearDateFilter().get_month('Enero') == 1


def test_find_suggestions_filter(spanish, lt):
    """FindSuggestionsFilter: the similar words of the speller of
    es-ES.dict that match the desired POS tag"""
    sentence = lt.get_analyzed_sentence('Las faltes que tiene este texto.')
    tokens = sentence.non_blank_tokens
    m = RuleMatch(FakeRule(spanish), sentence, 4, 10, 'msg')
    m.set_suggested_replacement('{suggestion}')
    m = FindSuggestionsFilter().accept_rule_match(m, {'wordFrom': '2', 'desiredPostag': 'N..P.*|A...P.|V.+'}, 2,
                                                  tokens[1:], [])
    assert 'faltas' in m.suggested_replacements


def test_number_in_word_filter(spanish):
    """SpanishNumberInWordFilter (with the misspelling check of the default
    spelling rule, no spelling suggestions)"""
    f = SpanishNumberInWordFilter()
    m = f.accept_rule_match(_fake_match(spanish), {'word': 'Buen0s'}, 0, [], [])
    assert m.suggested_replacements == ['Buenos']
    assert f.accept_rule_match(_fake_match(spanish), {'word': 'xq3z'}, 0, [], []) is None


def test_text_to_number_filter(spanish, lt):
    """TextToNumberFilter"""
    sentence = lt.get_analyzed_sentence('doscientos treinta y cuatro')
    tokens = sentence.non_blank_tokens[1:]
    m = RuleMatch(FakeRule(spanish), sentence, 0, len(sentence.text), 'msg')
    m = TextToNumberFilter().accept_rule_match(m, {}, 1, tokens, [])
    assert m.suggested_replacements == ['234']
    f = TextToNumberFilter()
    assert f.is_comma('Coma') and not f.is_comma('punto')


def test_adapt_suggestion(spanish):
    """Spanish.adaptSuggestion"""
    assert adapt_suggestion(spanish, 'a el', '') == 'al'
    assert adapt_suggestion(spanish, 'Voy de el centro a el parque', '') == 'Voy del centro al parque'
    assert adapt_suggestion(spanish, 'la el', '') == 'la el'


def test_prepare_line_for_speller():
    """Spanish.prepareLineForSpeller"""
    assert prepare_line_for_speller('casa') == ['casa']
    assert prepare_line_for_speller('a priori\t_Latin_') == ['a priori']
    assert prepare_line_for_speller('Nueva York\tNPCNG00') == ['Nueva York']
    assert prepare_line_for_speller('a menudo\tLOC_ADV') == ['a menudo']
    assert prepare_line_for_speller('de repente\tRG') == ['']
    assert prepare_line_for_speller('#comment') == ['#comment']
    assert prepare_line_for_speller('x;NCMS000 # comment') == ['x']
