"""Port of the tests of the Catalan replacement rules of
org.languagetool.rules.ca: SimpleReplaceRuleTest, SimpleReplaceVerbsRuleTest,
SimpleReplaceBalearicRuleTest, SimpleReplaceDNVRuleTest,
SimpleReplaceDNVSecondaryRuleTest, SimpleReplaceAnglicismTest,
ReplaceOperationNamesRuleTest, CheckCaseRuleTest and
CatalanWrongWordInContextRuleTest, plus checks of the rules without Java
tests (WordCoherencyRule, WordCoherencyValencianRule)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.ca.replace_rules import (CatalanWrongWordInContextRule, CheckCaseRule, ReplaceOperationNamesRule,
                                            SimpleReplaceAnglicism, SimpleReplaceBalearicRule,
                                            SimpleReplaceDNVRule, SimpleReplaceDNVSecondaryRule, SimpleReplaceRule,
                                            SimpleReplaceVerbsRule, WordCoherencyRule, WordCoherencyValencianRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ca')


@pytest.fixture(scope='module')
def catalan():
    return get_language('ca-ES')


@pytest.fixture(scope='module')
def valencian():
    return get_language('ca-ES-valencia')


@pytest.fixture(scope='module')
def lt(catalan):
    return JLanguageTool(catalan)


@pytest.fixture(scope='module')
def lt_val(valencian):
    return JLanguageTool(valencian)


@pytest.fixture(scope='module')
def messages():
    return messages_for('ca')


def _java_list(items):
    return '[' + ', '.join(items) + ']'


def _match(rule, lt, text):
    return rule.match(lt.get_analyzed_sentence(text))


# --- SimpleReplaceRuleTest ---

def test_simple_replace_rule(lt, messages):
    """SimpleReplaceRuleTest.testRule"""
    rule = SimpleReplaceRule(messages, lt.language)
    # correct sentences:
    assert len(_match(rule, lt, 'Això està força bé.')) == 0
    assert len(_match(rule, lt, 'Joan Navarro no és de Navarra ni de Jerez.')) == 0
    # incorrect sentences:
    matches = _match(rule, lt, 'El recader fa huelga.')
    assert len(matches) == 2
    assert matches[0].suggested_replacements[0] == "L'ordinari"
    assert matches[0].suggested_replacements[1] == 'El transportista'
    assert matches[1].suggested_replacements[0] == 'vaga'
    matches = _match(rule, lt, 'Aconteixements')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Esdeveniments'
    matches = _match(rule, lt, 'Els desencontres.')
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == (
        "[Les desavinences, Els desacords, Les topades, La manca d'acord, La manca de coincidència]")
    matches = _match(rule, lt, 'La seguent solució.')
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == '[La següent, El seient]'
    matches = _match(rule, lt, 'Un caminet poc ciclable baixa uns metres.')
    assert _java_list(matches[0].suggested_replacements) == '[poc pedalable, poc ciclista]'
    matches = _match(rule, lt, 'La seva escola transformada pq les seves filles encaixen molt bé.')
    assert _java_list(matches[0].suggested_replacements) == '[perquè]'
    matches = _match(rule, lt, 'Aquesta àbside.')
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == '[Aquest absis, Aquesta àbsida]'
    matches = _match(rule, lt, 'Un àbside.')
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == '[Un absis, Una àbsida]'
    matches = _match(rule, lt, "Sumats als kms d'anar i tornar.")
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == '[als km]'


# --- SimpleReplaceVerbsRuleTest ---

def _assert_suggestions(matches, expected):
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:len(expected)] == expected


def test_simple_replace_verbs_rule(catalan, lt, messages):
    """SimpleReplaceVerbsRuleTest.testRule"""
    rule = SimpleReplaceVerbsRule(messages, catalan)
    _assert_suggestions(_match(rule, lt, 'permanegué'), ['restà', 'estigué', 'quedà', 'romangué'])
    _assert_suggestions(_match(rule, lt, 'permanesqué'), ['restà', 'estigué', 'quedà', 'romangué'])
    _assert_suggestions(_match(rule, lt, 'permanéixer'), ['restar', 'estar', 'quedar', 'romandre'])
    _assert_suggestions(_match(rule, lt, 'pringava'), ['enfangava', 'empastifava', 'llepava', 'cagava',
                                                       'havia begut oli', 'tocava el rebre', 'es fotia',
                                                       'es feia fotre'])
    _assert_suggestions(_match(rule, lt, 'abarca'), ['abraça', 'abasta', 'comprèn', 'inclou'])
    _assert_suggestions(_match(rule, lt, 'abarcaven'), ['abraçaven', 'abastaven', 'comprenien', 'incloïen'])
    _assert_suggestions(_match(rule, lt, 'abarquéssim'), ['abracéssim'])
    _assert_suggestions(_match(rule, lt, 'antojà'), ['passà pel cap', 'passà pel magí', 'antullà'])
    _assert_suggestions(_match(rule, lt, 'alardeaven'), ['feien gala', 'feien ostentació'])
    _assert_suggestions(_match(rule, lt, 'alardejo'), ['faig gala', 'faig ostentació'])
    _assert_suggestions(_match(rule, lt, 'aclares'), ['aclareixes'])
    _assert_suggestions(_match(rule, lt, 'atossigues'), ['acuites', 'apresses', 'dones pressa', 'atabuixes',
                                                         'aclapares', 'afeixugues', 'mareges', 'afanyes'])
    _assert_suggestions(_match(rule, lt, 'agobiem'), ['aclaparem', 'atabalem', 'angoixem', 'estressem', 'ofeguem'])
    _assert_suggestions(_match(rule, lt, 'agobiïs'), ['aclaparis', 'atabalis', 'angoixis', 'estressis', 'ofeguis',
                                                      'estiguis molt a sobre', 'cansis molt', 'siguis molt pesat'])
    assert _match(rule, lt, 'desabasteix')[0].suggested_replacements[0] == 'desproveeix'
    assert _match(rule, lt, 'desabastíssim')[0].suggested_replacements[0] == 'desproveíssim'
    assert _match(rule, lt, 'desabasta')[0].suggested_replacements[0] == 'desproveeix'
    assert _match(rule, lt, 'sobresegueix')[0].suggested_replacements[0] == 'sobreseu'
    assert _match(rule, lt, 'sobreseguir')[0].suggested_replacements[0] == 'sobreseure'
    assert _match(rule, lt, 'coretgeix')[0].suggested_replacements[0] == 'corregeix'
    assert _match(rule, lt, 'coretjit')[0].suggested_replacements[0] == 'corregit'
    assert _java_list(_match(rule, lt, 'encandilen')[0].suggested_replacements) == (
        '[enlluernen, esbalaeixen, fascinen, enceguen, al·lucinen, espurnegen, resten enlluernat]')
    assert _match(rule, lt, 'permitisc')[0].suggested_replacements[0] == 'permeto'
    assert len(_match(rule, lt, 'Influí en pràcticament tots els gèneres de la música dance des dels anys 70 '
                                'fins ara.')) == 0
    assert _java_list(_match(rule, lt, 'Moldejant-les')[0].suggested_replacements) == (
        '[Modelant-les, Afaiçonant-les]')
    assert _java_list(_match(rule, lt, "Me s'ha ocurrit.")[0].suggested_replacements) == "[Se m'ha ocorregut]"
    assert _java_list(_match(rule, lt, "Com te s'ha ocurrit.")[0].suggested_replacements) == (
        "[se t'ha ocorregut]")
    assert _java_list(_match(rule, lt, 'liar-te-la')[0].suggested_replacements) == (
        '[embolicar-te-la, enredar-te-la, enrotllar-te-la, armar-te-la, engalipar-te-la, entabanar-te-la, '
        'embullar-te-la, embrollar-te-la]')


# --- SimpleReplaceBalearicRuleTest ---

def test_simple_replace_balearic_rule(lt, messages):
    """SimpleReplaceBalearicRuleTest.testRule"""
    rule = SimpleReplaceBalearicRule(messages, lt.language)
    # correct sentences:
    assert len(_match(rule, lt, 'Això està força bé.')) == 0
    assert len(_match(rule, lt, 'Joan Navarro no és de Navarra ni de Jerez.')) == 0
    assert len(_match(rule, lt, 'Prosper Mérimée.')) == 0
    assert len(_match(rule, lt, 'Index Librorum Prohibitorum')) == 0
    # incorrect sentences:
    matches = _match(rule, lt, 'El calcul del telefon.')
    assert len(matches) == 2
    assert matches[0].suggested_replacements[0] == 'càlcul'
    assert matches[1].suggested_replacements[0] == 'telèfon'
    matches = _match(rule, lt, 'EL CALCUL DEL TELEFON.')
    assert len(matches) == 2
    assert matches[0].suggested_replacements[0] == 'CÀLCUL'
    assert matches[1].suggested_replacements[0] == 'TELÈFON'


# --- SimpleReplaceDNVRuleTest ---

def test_simple_replace_dnv_rule(valencian, lt_val, messages):
    """SimpleReplaceDNVRuleTest.testRule"""
    rule = SimpleReplaceDNVRule(messages, valencian)
    lt = lt_val
    # correct sentences:
    assert len(_match(rule, lt, 'Ella és molt incauta.')) == 0
    # incorrect sentences:
    matches = _match(rule, lt, "L'arxipèleg.")
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'arxipèlag'
    _assert_suggestions(_match(rule, lt, 'colmena'), ['buc', 'rusc'])
    _assert_suggestions(_match(rule, lt, 'colmenes'), ['bucs', 'ruscos', 'ruscs'])
    _assert_suggestions(_match(rule, lt, 'afincaments'), ['establiments', 'instal·lacions'])
    _assert_suggestions(_match(rule, lt, 'Els arxipèlegs'), ['arxipèlags'])
    _assert_suggestions(_match(rule, lt, 'acevéssiu'), ['encebéssiu'])
    _assert_suggestions(_match(rule, lt, "S'arropeixen"), ['arrupeixen', 'arrupen'])
    _assert_suggestions(_match(rule, lt, 'incautaren'), ['confiscaren', 'requisaren', 'comissaren', 'decomissaren'])


# --- SimpleReplaceDNVSecondaryRuleTest ---

def test_simple_replace_dnv_secondary_rule(valencian, lt_val, messages):
    """SimpleReplaceDNVSecondaryRuleTest.testRule"""
    rule = SimpleReplaceDNVSecondaryRule(messages, valencian)
    # correct sentences:
    assert len(_match(rule, lt_val, 'Estan dispostes, estan indisposts, dispost a tot.')) == 0
    # incorrect sentences:
    matches = _match(rule, lt_val, "S'ha dispost a fer-ho.")
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'disposat'


# --- SimpleReplaceAnglicismTest ---

def _assert_anglicism(rule, lt, text, expected, from_pos=None, to_pos=None):
    matches = _match(rule, lt, text)
    assert len(matches) == 1
    assert _java_list(matches[0].suggested_replacements) == expected
    if from_pos is not None:
        assert matches[0].from_pos == from_pos
        assert matches[0].to_pos == to_pos


def test_simple_replace_anglicism(lt, messages):
    """SimpleReplaceAnglicismTest.testRule"""
    rule = SimpleReplaceAnglicism(messages)
    # frases correctes:
    assert len(_match(rule, lt, 'Això és un zombi molt perillós.')) == 0
    assert len(_match(rule, lt, "El pòdcast d'avui ha estat molt interessant.")) == 0
    assert len(_match(rule, lt, 'Hem rebut molts tiquets de suport.')) == 0
    assert len(_match(rule, lt, 'La bretxa digital és un problema greu.')) == 0
    # frases incorrectes — adaptacions gràfiques:
    _assert_anglicism(rule, lt, 'El zombie era molt perillós.', '[El zombi]')
    _assert_anglicism(rule, lt, 'Els zombies eren molt perillosos.', '[Els zombis]')
    _assert_anglicism(rule, lt, 'He sentit el podcast.', '[el pòdcast]')
    _assert_anglicism(rule, lt, 'He sentit els podcasts.', '[els pòdcasts]')
    _assert_anglicism(rule, lt, 'Tenim un ticket de suport obert.', '[un tiquet]')
    _assert_anglicism(rule, lt, 'Tenim dos tickets de suport oberts.', '[dos tiquets]')
    _assert_anglicism(rule, lt, 'El troll va inundar el fòrum de missatges.', '[El trol]')
    _assert_anglicism(rule, lt, 'El footing és un esport popular.', '[El fúting]')
    _assert_anglicism(rule, lt, "Hi ha un canvi en l'snorkeling gratuït.",
                      "[l'esnòrquel gratuït, la immersió lleugera gratuïta]")
    # frases incorrectes — anglicismes innecessaris:
    _assert_anglicism(rule, lt, 'El spam és un problema al correu electrònic.',
                      '[El correu brossa, El contingut brossa]')
    _assert_anglicism(rule, lt, 'Hi ha un gap important entre els salaris.', '[una bretxa important]')
    _assert_anglicism(rule, lt, 'El cringe que em va fer aquell moment.', "[L'angúnia, La vergonya, La incomoditat]")
    _assert_anglicism(rule, lt, 'Ens van programar uns briefings.',
                      '[unes sessions informatives, unes reunions informatives, uns reports, uns brífings]', 18, 31)
    # frases incorrectes — sintagmes multiparaula (el filtre de gènere/nombre no s'aplica):
    _assert_anglicism(rule, lt, 'El vol era low cost.', '[baix cost, de baix cost, barat, barats]', 11, 19)
    online = '[en línia, digital, electrònic, connectat, per internet, en remot, en internet]'
    _assert_anglicism(rule, lt, 'Farem el seminari online.', online)
    _assert_anglicism(rule, lt, 'Farem el seminari on line.', online, 18, 25)
    _assert_anglicism(rule, lt, 'Farem el seminari on-line.', online, 18, 25)
    _assert_anglicism(rule, lt, 'Necessitem el know-how necessari per fer-ho.', '[saber fer]', 14, 22)
    # majúscula a l'inici de frase:
    _assert_anglicism(rule, lt, 'Zombie és el nom de la pel·lícula.', '[Zombi]')
    # diverses coincidències en una mateixa frase:
    assert len(_match(rule, lt, 'El spam i el troll fan malbé les discussions en línia.')) == 2
    _assert_anglicism(rule, lt, 'La primera masterclass serà la de literatura barroca.',
                      '[La primera classe magistral, Les primeres classes magistrals]')


# --- ReplaceOperationNamesRuleTest ---

_OPERATION_NAMES_CORRECT = (
    'tot tenyit amb llum de nostàlgia', 'Ho van fer per duplicat.', 'Assecat el braç del riu', 'el llibre empaquetat',
    'un resultat equilibrat', 'el nostre equip era bastant equilibrat', 'un llibre ben empaquetat',
    "l'informe filtrat pel ministre", "L'informe filtrat és terrible", 'ha liderat la batalla', 'Els tinc empaquetats',
    'amb tractament unitari i equilibrat', 'Processat després de la mort de Carles II', 'Processat diverses vegades',
    'moltes vegades empaquetat amb pressa', 'és llavors embotellat i llançat al mercat',
    'la comercialització de vi embotellat amb les firmes comercials',
    'eixia al mercat el vi blanc embotellat amb la marca', 'que arribi a un equilibrat matrimoni',
    'És un cafè amb molt de cos i molt equilibrat.', 'i per tant etiquetat com a observat',
    'Molt equilibrat en les seves característiques', 'filtrat per Wikileaks', 'una vegada filtrat', 'no equilibrat',
)
_OPERATION_NAMES_INCORRECT = (
    'Assecat del braç del riu', 'Cal vigilar el filtrat del vi', "El procés d'empaquetat",
    'Els equilibrats de les rodes', "El procés d'etiquetat de les ampolles", 'El rentat de cotes',
)


def test_replace_operation_names_rule(catalan, lt):
    """ReplaceOperationNamesRuleTest.testRule (with the English messages, as
    in Java)"""
    rule = ReplaceOperationNamesRule(messages_for('en'), catalan)
    for sentence in _OPERATION_NAMES_CORRECT:
        assert len(_match(rule, lt, sentence)) == 0, sentence
    for sentence in _OPERATION_NAMES_INCORRECT:
        assert len(_match(rule, lt, sentence)) == 1, sentence
    assert len(_match(rule, lt, 'El repicat i el rejuntat.')) == 2
    matches = _match(rule, lt, 'El procés de relligat dels llibres.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:3] == ['relligadura', 'relligament', 'relligada']
    matches = _match(rule, lt, 'Els rentats de cervell.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:3] == ['Les rentades', 'Els rentatges', 'Els rentaments']


# --- CheckCaseRuleTest ---

def test_check_case_rule(lt, messages):
    """CheckCaseRuleTest.testRule"""
    rule = CheckCaseRule(messages, lt.language)
    # correct sentences:
    for sentence in ('Sap que tinc dos bons amics?',
                     "La seua millor amiga no sap què passa amb l'avi, però en parla en YouTube.",
                     'El país necessita tecnologia més moderna.', "'Da Vinci'", "‒ 'Da Vinci'", "‒ ¡'Da Vinci'!",
                     'El Prat de Llobregat', '08820 - El Prat de Llobregat', 'el Prat de Llobregat', 'Da Vinci',
                     'Amb Joan Pau i Josep Maria.', "ESTAT D'ALARMA", "d'educació secundària",
                     'Educació Secundària Obligatòria'):
        assert len(_match(rule, lt, sentence)) == 0, sentence
    assert len(_match(rule, lt, 'Educació Secundària obligatòria')) == 1
    for sentence in ('Educació secundària obligatòria', "d'educació secundària obligatòria",
                     '\\u2022 Intel·ligència artificial', '● Intel·ligència artificial', 'Els drets humans',
                     'Declaració Universal dels Drets Humans', 'El codi Da Vinci'):
        assert len(_match(rule, lt, sentence)) == 0, sentence
    assert len(_match(rule, lt, 'Declaració Universal dels drets humans')) == 1
    # incorrect sentences:
    for sentence, expected in (('Joan pau', 'Joan Pau'),
                               ("Expedient de Regulació Temporal d'Ocupació",
                                "Expedient de regulació temporal d'ocupació"),
                               ('Em vaig entrevistar amb Joan maria', 'Joan Maria'),
                               ('Em vaig entrevistar amb Da Vinci', 'da Vinci'),
                               ('-"Leonardo Da Vinci"', 'Leonardo da Vinci'),
                               ('-"¿Leonardo Da Vinci?"', 'Leonardo da Vinci'),
                               ('Baixar Al-Assad', 'Baixar al-Assad')):
        matches = _match(rule, lt, sentence)
        assert len(matches) == 1, sentence
        assert matches[0].suggested_replacements[0] == expected


# --- CatalanWrongWordInContextRuleTest ---

def test_catalan_wrong_word_in_context_rule(catalan, lt):
    """CatalanWrongWordInContextRuleTest.testRule (Java passes null messages,
    which the rule doesn't use; the core rule classes need a message bundle
    here)"""
    rule = CatalanWrongWordInContextRule(messages_for('ca'), catalan)
    assert len(_match(rule, lt, 'Li va infringir un mal terrible.')) == 1
    assert len(_match(rule, lt, 'És un terreny abonat per als problemes.')) == 1
    assert len(_match(rule, lt, 'No li va cosir bé les betes.')) == 1
    assert len(_match(rule, lt, 'Sempre li seguia la beta.')) == 1
    # pali, pal·li
    assert len(_match(rule, lt, 'Sota els palis.')) == 1
    assert len(_match(rule, lt, 'Els pal·lis.')) == 0
    assert len(_match(rule, lt, 'El pal·li i el sànscrit.')) == 1
    assert len(_match(rule, lt, 'El pali i el sànscrit.')) == 0
    assert len(_match(rule, lt, 'Vam comprar xocolate de mànec.')) == 1
    assert len(_match(rule, lt, "El pic de l'ocell.")) == 1


# --- WordCoherencyRule, WordCoherencyValencianRule (no Java tests) ---

def test_word_coherency_rule(lt, messages):
    """The example pair of WordCoherencyRule"""
    rule = WordCoherencyRule(messages)
    assert rule.get_id() == 'CA_WORD_COHERENCY'
    matches = rule.match(lt.analyze_text('Un pesebre ací i un altre pessebre allà.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['pesebre']
    assert matches[0].short_message == 'Coherència'
    assert rule.incorrect_examples[0].corrections == ['pesebre']


def test_word_coherency_valencian_rule(lt_val, messages):
    """The example pair of WordCoherencyValencianRule"""
    rule = WordCoherencyValencianRule(messages)
    assert rule.get_id() == 'CA_WORD_COHERENCY_VALENCIA'
    matches = rule.match(lt_val.analyze_text("Este home d'ací parla amb aquest altre ací."))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['este']
