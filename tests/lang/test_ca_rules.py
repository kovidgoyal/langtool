"""Port of the tests of the Catalan rules (org.languagetool.rules.ca):
CatalanUnpairedBracketsRuleTest, CatalanWordRepeatRuleTest,
CatalanPhraseRepeatRuleTest, PronomFebleDuplicateRuleTest, CompoundRuleTest,
EndOfParagraphPunctuationRuleTest and CatalanRepeatedWordsRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.ca.rules import (CatalanPhraseRepeatRule, CatalanPunctuationMarkAtParagraphEnd,
                                    CatalanRepeatedWordsRule, CatalanUnpairedBracketsRule,
                                    CatalanWordRepeatBeginningRule, CatalanWordRepeatRule, CompoundRule,
                                    IgnoreProperNouns, PronomFebleDuplicateRule)
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ca')


@pytest.fixture(scope='module')
def catalan():
    return get_language('ca-ES')


@pytest.fixture(scope='module')
def lt(catalan):
    return JLanguageTool(catalan)


def _lt_with_rules(language, rule_ids):
    """new JLanguageTool(Catalan.getInstance()) with the given (default off)
    rules enabled, like the Java tests"""
    tool = JLanguageTool(language)
    for rule_id in rule_ids:
        tool.enable_rule(rule_id)
    return tool


# --- CatalanUnpairedBracketsRuleTest ---

@pytest.mark.parametrize('text,expected', [
    # correct sentences:
    ("The sport during the 90's.", 0),
    ("Guns N' Roses", 0),
    ('L\'«home és així»', 0),
    ("l'«home»", 0),
    ('«"És així" o no»', 0),
    ('«"És així", va dir.»', 0),
    ('«És "així" o no»', 0),
    ('(l\'execució a mans d\'"especialistes")', 0),
    ('(L\'"especialista")', 0),
    ('"Vine", li va dir.', 0),
    ('(Una frase de prova).', 0),
    ("Aquesta és la paraula 'prova'.", 0),
    ('This is a sentence with a smiley :-)', 0),
    ('This is a sentence with a smiley ;-) and so on...', 0),
    ("Aquesta és l'hora de les decisions.", 0),
    ('Aquesta és l’hora de les decisions.', 0),
    ('(fig. 20)', 0),
    ('"Sóc la teva filla. El corcó no et rosegarà més."\n\n', 0),
    ('–"Club dels llagoters" –va repetir en Ron.', 0),
    ('—"Club dels llagoters" –va repetir en Ron.', 0),
    ("»Això em porta a demanar-t'ho.", 0),
    ("»Això em porta (sí) a demanar-t'ho.", 0),
    ('al capítol 12 "Llavors i fruits oleaginosos"', 0),
    ('"Per què serveixen les forquilles?" i aquest respon "per menjar".', 0),
    ('És a 60º 50\' 23"', 0),
    ("És a 60º 50' 23'", 0),
    ("60° 50' 23'", 0),
    ("60° 50'", 0),
    ('El tràiler té una picada d\'ullet quan diu que "no es pot fer una pel·lícula \'slasher\' com si fos una '
     'sèrie".', 0),
    ('El tràiler –que té una picada d\'ullet quan diu que "no es pot fer una pel·lícula \'slasher\' com si fos una '
     'sèrie"– ja ', 0),
    ('This is a [test] sentence...', 0),
    ('The plight of Tamil refugees caused a surge of support from most of the Tamil political parties.[90]', 0),
    ('This is what he said: "We believe in freedom. This is what we do."', 0),
    ('(([20] [20] [20]))', 0),
    # test for a case that created a false alarm after disambiguation
    ('This is a "special test", right?', 0),
    # numerical bullets
    ('We discussed this in Chapter 1).', 0),
    ('The jury recommended that: (1) Four additional deputies be employed.', 0),
    ('We discussed this in section 1a).', 0),
    ('We discussed this in section iv).', 0),
    # inches exception shouldn't match " here:
    ('In addition, the government would pay a $1,000 "cost of education" grant to the schools.', 0),
    ("Porta'l cap ací.", 0),
    ("Porta-me'n cinquanta!", 0),
    # Saxon genitive
    ("Harper's Dictionary of Classical Antiquities", 0),
    ('Harper’s Dictionary of Classical Antiquities', 0),
    # incorrect sentences:
    ('Això és “important i ara què passa. ', 1),
    ('Això és "important i ara què passa. ', 1),
    ('Això és (impossible. ', 1),
    ('Això es (impossible. ', 1),
    ('Això és) impossible. ', 1),
    ('Això es impossible). ', 1),
    ('Això és «important, oi que sí?', 1),
    ("(aquesta 'és la solució)", 1),
    ('(L\'"especialista"', 0),
    ('(L\'"especialista".', 1),
    ("L'«home és així", 0),
    ("L'«home és així.", 1),
    ('S\'«esperava \'el\' (segon) "resultat"', 0),
    ('S\'«esperava \'el\' (segon) "resultat".', 1),
    ("l'«home", 0),
    ("l'«home.", 1),
    ('Ploraria."', 1),
    ('Aquesta és l555’hora de les decisions.', 1),
    ('Vine", li va dir.', 1),
    ('Aquesta és l‘hora de les decisions.', 1),
    ('(This is a test sentence.', 1),
    ("This is a test with an apostrophe &'.", 1),
    ("&'", 0),
    ("&'.", 1),
    ("!'", 0),
    ("!'.", 1),
    ("What?'", 0),
    ("What?'.", 1),
    # this is currently considered incorrect... although people often use smileys this way:
    ('Some text (and some funny remark :-) with more text to follow', 0),
    ('Some text (and some funny remark :-) with more text to follow?', 1),
    ('(This is a test” sentence.', 2),
    ('This [is (a test} sentence.', 3),
])
def test_unpaired_brackets_rule(catalan, lt, text, expected):
    """CatalanUnpairedBracketsRuleTest.testRule"""
    rule = CatalanUnpairedBracketsRule(messages_for('en'), catalan)
    assert len(rule.match([lt.get_analyzed_sentence(text)])) == expected


def test_unpaired_brackets_multiple_sentences(catalan):
    """CatalanUnpairedBracketsRuleTest.testMultipleSentences"""
    tool = _lt_with_rules(catalan, ['CA_UNPAIRED_BRACKETS'])
    assert len(tool.check('Aquesta és una sentència múltiple amb claudàtors: '
                          '[Ací hi ha un claudàtor. Amb algun text.] i ací continua.\n')) == 0
    assert len(tool.check('"Era la teva filla. El corcó no et rosegarà més."\n\n')) == 0
    assert len(tool.check('"Era la teva filla. El corcó no et rosegarà més".\n\n')) == 0
    assert len(tool.check('Aquesta és una sentència múltiple amb claudàtors: '
                          '[Ací hi ha un claudàtor. Amb algun text. I ací continua.\n\n')) == 1
    tool.check('«Els manaments diuen: "No desitjaràs la dona del teu veí"»')
    assert len(tool.check('Aquesta és una sentència múltiple amb parèntesis '
                          '(Ací hi ha un parèntesi. \n\n Amb algun text.) i ací continua.')) == 0


def test_question_exclamation(catalan):
    """CatalanUnpairedBracketsRuleTest.testQuestionExclamation"""
    tool = _lt_with_rules(catalan, ['CA_UNPAIRED_QUESTION', 'CA_UNPAIRED_EXCLAMATION'])
    matches = tool.check('-Com estàs?\n')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['¿Com']
    matches = tool.check('-Benvinguda!\n')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['¡Benvinguda']
    matches = tool.check('-Tinc raó, oi?\n')
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['¿oi']


# --- CatalanWordRepeatRuleTest ---

@pytest.mark.parametrize('text,expected', [
    # correct
    ('Sempre pensa en en Joan.', 0),
    ('Els els portaré aviat.', 0),
    ('Maximilià I i Maria de Borgonya', 0),
    ('De la A a la z', 0),
    ('Entre I i II.', 0),
    ('fills de Sigebert I i Brunegilda', 0),
    ('del segle I i del segle II', 0),
    ('entre el capítol I i el II', 0),
    ('cada una una casa', 0),
    ('cada un un llibre', 0),
    ('Si no no es gaudeix.', 0),
    ('HUCHA-GANGA.ES es presenta.', 0),
    ('Ja fa, arreu arreu, més de quaranta anys.', 0),
    ('obrim inscripcions\U0001F44D\U0001F49A\U0001F332\U0001F332', 0),
    ('Anirem del punt A al punt B.', 0),
    ("La grip A a l'abril repunta.", 0),
    ("L'apartat A a la part final.", 0),
    # incorrect
    ('Tots els els homes són iguals.', 1),
    ('Maximilià i i Maria de Borgonya', 1),
])
def test_word_repeat_rule(catalan, lt, text, expected):
    """CatalanWordRepeatRuleTest.testRule"""
    rule = CatalanWordRepeatRule(messages_for('ca'), catalan)
    assert len(rule.match(lt.get_analyzed_sentence(text))) == expected


# --- CatalanPhraseRepeatRuleTest ---

@pytest.mark.parametrize('text', [
    'sobretot, que dubta, que dubta constantment',
    'no deixava de tenir febre i més febre i més febre',
    'una vegada i una altra i una altra i una altra. ',
    'trobava aquest títol o aquest o aquest altre,',
    ' Que sí, que sí, que ho heu llegit bé.',
    '—Molt bé, molt bé, tampoc cal que et posis així ',
    'però la mort –la Mort–,',
    'Que…, que…, ja hi ha les entrades?',
    'Que et penses que parlant descobrirem res de res de per què som aquí?',
    "Què es podia esperar d'un… d'un…?",
    'Imperfet de subjuntiu [é] [é] [í]',
    'Soc molt vella molt vella, però que encara hi soc.',
    'No volia res més que mirar i mirar i mirar.',
    'A més a més, ho va fer a poc a poc.',
    'A diferència dels dels ocells.',
    'Puja pas a pas a les ruïnes',
    "No cal posar 'a' a tot arreu.",
    'estava malalt de bo de bo',
    "Ve ací de tant en tant en lloc d'anar allà",
    'Sigui qui sigui qui vingui.',
    "D'hereu a hereu a través de generacions.",
    "De dos en dos en l'arbre.",
    "No n'hi havia ni massa ni massa pocs",
    'Podia tractar qualsevol persona de tu a tu a qualsevol nivell.',
    'Eren xifres molt -molt- modestes.',
    'Revisa milions de milions de dades en pocs segons.',
    ' © © © © ©',
    ' © © © © © © © ©',
    'p=(16+16+1+1)',
    'p=(16 + + 16 + +)',
    '16 15 15 16 15 15',
    '16 15 16 15 16 15',
    '~~~~',
    '~~~~~~~~',
    "l'honestedat d’alguns ˗alguns˗ humans.",
    'Mader | Andorra | Andorra La Vella ',
    '==== Arc de Zou ====',
    '============',
    '=r=r[s[i]]||{}',
    'Serveis que ofereix el CRAI > Préstec > Préstec, reserves',
    'total de folis: 166 (III + III + I+ 156 + III) ff.',
    '📚📚📚📚📚📚📚📚📚📚',
])
def test_phrase_repeat_rule_correct(catalan, lt, text):
    """CatalanPhraseRepeatRuleTest.testRule (correct sentences)"""
    rule = CatalanPhraseRepeatRule(messages_for('ca'), catalan)
    assert rule.match(lt.get_analyzed_sentence(text)) == []


@pytest.mark.parametrize('text,suggestion', [
    ('Benvinguts a casa a casa meva.', 'a casa'),
    ('Benvinguts a la a la casa.', 'a la'),
    ('Benvinguts a casa meva a casa meva.', 'a casa meva'),
    ('Ho poso com a com a exemple', 'com a'),
    ("És l'americà l'americà.", "l'americà"),
    ("És d'aconseguir-los d'aconseguir-los així", "d'aconseguir-los"),
    ('La casa és la casa és verda', 'La casa és'),
])
def test_phrase_repeat_rule_incorrect(catalan, lt, text, suggestion):
    """CatalanPhraseRepeatRuleTest.testRule (incorrect sentences)"""
    rule = CatalanPhraseRepeatRule(messages_for('ca'), catalan)
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert matches
    assert matches[0].suggested_replacements[0] == suggestion


# --- PronomFebleDuplicateRuleTest ---

@pytest.mark.parametrize('text', [
    "És l'última oportunitat que hi ha de donar-los la paraula.",
    "És l'última oportunitat que hi ha d'anar-hi.",
    "N'hi ha d'haver.",
    'Hi podria haver un error.',
    'Es divertien llançant-se pedres.',
    'Es recomana tapar-se la boca.',
    "S'ordena dutxar-se cada dia.",
    'Es va quedar barallant-se amb el seu amic.',
    'Es va quedar se',
    'M’encantava enfilar-me',
    "t'obliguen a penjar-te",
    'ens permeten endinsar-nos',
    'els llepaven fins a donar-los',
    'em fa doblegar fins a tocar-me',
    'la batalla per defensar-la',
    "ens convida a treure'ns-la",
    'ens ve a buscar per ajudar-nos',
    "m'agrada enfonsar-me",
    'em dedico a fer-me',
    'la mira sense veure-la',
    "l'havia podat fins a a deixar-lo",
    'em costava deixar-me anar',
    "m'obliga a allunyar-me",
    'el papà havia de canviar-lo',
    'ens congregava per assabentar-nos',
    'es podia morir de taponar-se-li',
    'l’hagin preservada sense tocar-la',
    'li impedeixi aconseguir-la',
    'us he fet venir per llevar-vos',
    "ajuda'm a alçar-me",
    "l'esperava per agrair-li",
    'els va empènyer a adreçar-li',
    'em vaig oblidar de rentar-me',
    'ens ajudà a animar-nos',
    "l'encalçava sense poder atrapar-la",
    'em manava barrejar-me',
    'el convidà a obrir-los',
    'es disposava a despullar-se',
    'es mudà per dirigir-se',
    "li va costar d'aconseguir tenir-lo",
    "es va poder estar d'atansar-s'hi",
    'el dissuadeixi de matar-lo',
    'la va festejar per engalipar-la',
    "s'havia negat a casar-s'hi",
    'es disposaven a envolar-se',
    "li sabia d'haver-la repudiada",
    "li sabia greu d'haver-la repudiada",
    'el féu acostar per besar-li',
    'En acostar-se va fer-se això.',
    "Quan em va veure se'n va anar corrent.",
    'Li hauria agradat poder tenir-hi una conversa',
    'perquè els molts ulls que les volien veure poguessin saciar-se',
    'El pare el va fer anar a rentar-se la sang.',
    "se n'anà a veure'l",
    "Me n'aniria a queixar-me.",
    'se n’aniran a viure-hi',
    "Als exemples d'excepció que s'han presentat s'hi poden afegir per causes similars",
    "els nous materials que es vagin dipositant poden veure's encara afectats per forces",
    "i pensant que algú l'havia engaltada s'hi atansà",
    "hi anava a prendre'n possessió",
    "hi anava a veure'l cada dia",
    "se'n va a salvar-se",
    'Què els va fer seguir-lo?',
    'Això et fa adonar-te del que passa.',  # -> rule EL_FAN_AGENOLLAR
    'la mare em feia anar a exhibir-me a certes cases',  # dubtós
    'ja havia pensat en la recança que em feia haver-me d’allunyar d’ella',  # dubtós
])
def test_pronom_feble_duplicate_rule_correct(catalan, lt, text):
    """PronomFebleDuplicateRuleTest.testRule (correct sentences)"""
    rule = PronomFebleDuplicateRule(messages_for('en'))
    assert rule.match(lt.get_analyzed_sentence(text)) == []


@pytest.mark.parametrize('text,suggestions', [
    ("S'ha de fer-se", ('Ha de fer-se', "S'ha de fer")),
    ('Ell, en voldrà donar-nos-en més?', ('voldrà donar-nos-en', 'en voldrà donar')),
    ("N'ha d'haver-hi", ("N'hi ha d'haver", "Ha d'haver-n'hi")),
    ('Li ha de fer-se-li.', ('Ha de fer-se-li', 'Li ha de fer')),
    ("n'hi continuà havent-hi", ("n'hi continuà havent", "continuà havent-n'hi")),
    ("Hi ha d'haver-ne", ("N'hi ha d'haver", "Ha d'haver-n'hi")),
    ('Hi continuarà havent-hi', ('Continuarà havent-hi', 'Hi continuarà havent')),
    ('En continuarà havent-hi', ("N'hi continuarà havent", "Continuarà havent-n'hi")),
    ('Es va continuar barallant-se amb el seu amic.', ('Va continuar barallant-se', 'Es va continuar barallant')),
    ('Hi podria haver-hi', ('Podria haver-hi', 'Hi podria haver')),
    ("N'hi podria haver-n'hi", ("Podria haver-n'hi", "N'hi podria haver")),
    ('ho puc arreglar-ho', ('puc arreglar-ho', 'ho puc arreglar')),
    ('La volia veure-la.', ('Volia veure-la', 'La volia veure')),
    ('En vaig portar-ne quatre.', ('Vaig portar-ne', 'En vaig portar')),
    ('Ho hem hagut de fer-ho.', ('Hem hagut de fer-ho', 'Ho hem hagut de fer')),
    ('Hi hem hagut de continuar anant-hi.', ('Hem hagut de continuar anant-hi', 'Hi hem hagut de continuar anant')),
    ("M'he de rentar-me les dents.", ('He de rentar-me', "M'he de rentar")),
    ('Li ho hem hagut de continuar dient-li-ho.',
     ('Hem hagut de continuar dient-li-ho', 'Li ho hem hagut de continuar dient')),
    ('Et deu enganyar-te.', None),
    ('Et deu voler enganyar-te.', None),
    ('Et deu haver de dir-te.', None),
    ('Ho deu continuar dient-ho.', None),
    ("S'està rebel·lant-se.", None),
    ('Li va començar a dur-li problemes.', None),
    ("S'acabarà carregant-se.", None),
    ('Jo ho vaig ser-hi.', ('vaig ser-hi', 'ho vaig ser')),
    ('Jo hi vaig ser-ho.', ('vaig ser-ho', 'hi vaig ser')),
    ("És l'última oportunitat que hi ha d'haver-hi.", ("ha d'haver-hi", "hi ha d'haver")),
    ('No ho he arribat mai a processar-ho tot.', ('he arribat mai a processar-ho', 'ho he arribat mai a processar')),
    ("Moltes escoles l'estan deixant d'utilitzar-lo.", ("estan deixant d'utilitzar-lo", "l'estan deixant d'utilitzar")),
])
def test_pronom_feble_duplicate_rule_incorrect(catalan, lt, text, suggestions):
    """PronomFebleDuplicateRuleTest.testRule (incorrect sentences)"""
    rule = PronomFebleDuplicateRule(messages_for('en'))
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == 1
    if suggestions is not None:
        assert matches[0].suggested_replacements[:2] == list(suggestions)


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule(lt):
    """CompoundRuleTest.testRule (setUp runs AbstractCompoundRuleTest.testAllCompounds,
    which only prints warnings for possibly misspelled suggestions)"""
    ca = get_language('ca')
    rule = CompoundRule(messages_for('ca'), ca, None)
    data = rule.get_compound_rule_data()
    for compound in data.incorrect_compounds:
        if compound in data.dash_suggestion:
            rule.is_misspelled(compound.replace(' ', '-'))
        if compound in data.joined_suggestion:
            rule.is_misspelled(rule.merge_compound(compound, compound in data.joined_lower_case_suggestion))
    # correct sentences:
    _check(lt, rule, 0, 'tam-tam')
    # incorrect sentences:
    _check(lt, rule, 1, 'Ryan-Air', 'Ryanair')


def test_compound_rule_specific_ids(lt):
    rule = CompoundRule(messages_for('ca'), get_language('ca'), None)
    m, = rule.match(lt.get_analyzed_sentence('Ryan-Air'))
    assert m.rule.get_id() == 'CA_COMPOUNDS_RYAN_AIR'
    assert m.rule.get_description() == 'Paraules compostes amb guionet: Ryan-Air'
    assert rule.is_misspelled('blablabla') and not rule.is_misspelled('casa')


# --- EndOfParagraphPunctuationRuleTest ---

def test_end_of_paragraph_punctuation_rule(lt):
    """EndOfParagraphPunctuationRuleTest.testRule"""
    lang = get_language('ca')
    rule = CatalanPunctuationMarkAtParagraphEnd(messages_for('ca'), lang)
    assert len(rule.match(lt.analyze_text('Això és un paràgraf amb una frase només'))) == 0
    assert len(rule.match(lt.analyze_text('Això és un paràgraf amb una frase només,'))) == 0
    matches = rule.match(lt.analyze_text('Això és un paràgraf amb una frase només. Això és la segona frase'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'frase.'
    assert matches[0].from_pos == 59
    assert len(rule.match(lt.analyze_text('Això és un paràgraf amb una frase només.\\n'
                                          'Això és una única frase en un paràgraf'))) == 0
    assert len(rule.match(lt.analyze_text('Això és un paràgraf.\n\nAnnex: Videojocs cancel·lats'))) == 0
    assert len(rule.match(lt.analyze_text('Això és un paràgraf.\n\nArticle principal: Videojocs cancel·lats'))) == 0
    assert len(rule.match(lt.analyze_text('Això és un paràgraf.\n\nAltre prefix: Videojocs cancel·lats'))) == 1


# --- CatalanRepeatedWordsRuleTest ---

def test_repeated_words_rule(lt):
    """CatalanRepeatedWordsRuleTest.testRule"""
    rule = CatalanRepeatedWordsRule(messages_for('ca'), get_language('ca'))
    assert rule.match(lt.analyze_text('Abans de fer això. Abans, va fer allò')) == []
    assert rule.match(lt.analyze_text("Tema 4: L'alta edat mitjana. Tema 5: La baixa edat mitjana.")) == []
    matches = rule.match(lt.analyze_text('Realitzaven una cosa inesperada. Llavors en van realitzar una altra.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[:3] == ['fer', 'dur a terme', 'portar a cap']
    assert matches[0].rule.get_id() == 'CA_REPEATEDWORDS'


# --- further checks of the rules without Java tests ---

def test_word_repeat_beginning_rule(catalan, lt):
    rule = CatalanWordRepeatBeginningRule(messages_for('ca'), catalan)
    assert rule.get_id() == 'CATALAN_WORD_REPEAT_BEGINNING_RULE'
    matches = rule.match(lt.analyze_text('Però el carrer és tot modernista. Però té nom de poeta.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['Així i tot', "D'altra banda", 'Per altra part']
    matches = rule.match(lt.analyze_text('Perquè ho diu ell. Perquè ho vull jo.'))
    assert matches[0].suggested_replacements == ['Car', 'Ja que', 'Per tal com', 'Pel fet que', 'Puix que']
    assert rule.match(lt.analyze_text('El carrer és tot modernista. El carrer té nom de poeta.')) == []


def test_ignore_proper_nouns(catalan, lt):
    from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
    rule = IgnoreProperNouns(messages_for('ca'), catalan)
    assert rule.get_id() == 'IGNORE_PROPER_NOUNS'
    first, second = lt.analyze_text('Barcelona és bonica. Viu a Barcelona.')
    assert rule.match([first, second]) == []
    # an untagged occurrence of a word seen as a proper noun before
    tokens = list(second.tokens)
    i = next(k for k, t in enumerate(tokens) if t.token == 'Barcelona')
    tokens[i] = AnalyzedTokenReadings(AnalyzedToken('Barcelona', None, None), tokens[i].start_pos)
    matches = rule.match([first, AnalyzedSentence(tokens)])
    assert len(matches) == 1
    start = len(first.text) + tokens[i].start_pos
    assert (matches[0].from_pos, matches[0].to_pos) == (start, start + len('Barcelona'))
