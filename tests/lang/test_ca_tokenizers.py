"""Port of org.languagetool.tokenizers.ca.CatalanWordTokenizerTest and
CatalanSentenceTokenizerTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ca')


# --- CatalanWordTokenizerTest ---

# (text, expected tokens.toString() or None, expected number of tokens or None)
WORD_TOKENIZER_CASES = [
    ("-contar-se'n-", "[-, contar, -se, 'n, -]", None),
    ("-M'agradaria.", "[-, M', agradaria, .]", None),
    ("Visiteu 'http://www.softcatala.org'", "[Visiteu,  , ', http://www.softcatala.org, ']", None),
    ('Visiteu "http://www.softcatala.org"', '[Visiteu,  , ", http://www.softcatala.org, "]', None),
    ('name@example.com', None, 1),
    ('name@example.com.', None, 2),
    ('name@example.com:', None, 2),
    ("L'origen de name@example.com.", "[L', origen,  , de,  , name@example.com, .]", 7),
    ("L'origen de name@example.com i de name2@example.com.",
     "[L', origen,  , de,  , name@example.com,  , i,  , de,  , name2@example.com, .]", 13),
    ('L\'"ala bastarda".', '[L\', ", ala,  , bastarda, ", .]', 7),
    ('d\'"ala bastarda".', '[d\', ", ala,  , bastarda, ", .]', 7),
    ("Emporta-te'ls a l'observatori dels mars", None, 13),
    ('Emporta-te’ls a l’observatori dels mars', None, 13),
    ('‘El tren Barcelona-València’', '[‘, El,  , tren,  , Barcelona, -, València, ’]', 9),
    ('El tren Barcelona-València', '[El,  , tren,  , Barcelona, -, València]', 7),
    ('No acabava d’entendre’l bé', '[No,  , acabava,  , d’, entendre, ’l,  , bé]', 9),
    ("N'hi ha vint-i-quatre", "[N', hi,  , ha,  , vint-i-quatre]", 6),
    ('Mont-ras', '[Mont-ras]', 1),
    ("És d'1 km.", "[És,  , d', 1,  , km, .]", 7),
    ("És d'1,5 km.", "[És,  , d', 1,5,  , km, .]", 7),
    ("És d'5 km.", "[És,  , d', 5,  , km, .]", 7),
    ('la direcció E-SE', '[la,  , direcció,  , E, -, SE]', 7),
    ('la direcció NW-SE', '[la,  , direcció,  , NW, -, SE]', 7),
    ("Se'n dóna vergonya", "[Se, 'n,  , dóna,  , vergonya]", 6),
    ('Emília-Romanya', '[Emília-Romanya]', 1),
    ("L'Emília-Romanya", "[L', Emília-Romanya]", 2),
    ('col·laboració', None, 1),
    ('col.laboració', None, 1),
    ('col•laboració', None, 1),
    ('col·Laboració', None, 1),
    ('COL∙LABORADORES', None, 1),
    ('abans-d’ahir', None, 1),
    ("abans-d'ahir", None, 1),
    ('Sud-Est', '[Sud, -, Est]', 3),
    ('Sud-est', None, 1),
    ('10 000', None, 1),
    ('1 000 000', None, 1),
    ('2005 57 114', '[2005,  , 57 114]', 3),
    ('2005 454', '[2005,  , 454]', 3),
    ('$1', '[$1]', 1),
    ("AVALUA'T", "[AVALUA, 'T]", 2),
    ('Tel-Aviv', '[Tel-Aviv]', 1),
    ('"El cas \'Barcelona\'"', '[", El,  , cas,  , \', Barcelona, \', "]', 9),
    ('"El cas \'d\'aquell\'"', '[", El,  , cas,  , \', d\', aquell, \', "]', 10),
    ('"El cas ‘d’aquell’"', '[", El,  , cas,  , ‘, d’, aquell, ’, "]', 10),
    ("Sàsser-l'Alguer", "[Sàsser, -, l', Alguer]", 4),
    ('Castella-la Manxa', '[Castella, -, la,  , Manxa]', 5),
    ('Qui-sap-lo temps', '[Qui-sap-lo,  , temps]', 3),
    ('Sol Picó (🐌+🐚)', '[Sol,  , Picó,  , (, 🐌, +, 🐚, )]', None),
    ('🧡prova.', '[🧡, prova, .]', None),
    ('🧡🧡prova🧡', '[🧡, 🧡, prova, 🧡]', None),
    ('❤️', '[❤️]', None),
    ('❤️prova', '[❤️, prova]', None),
    ('H₂O', '[H₂O]', None),
    ('🧡', '[🧡]', None),
    ('sol∙licitud', '[sol.licitud]', None),
    ('És ell ㅡva dir.', '[És,  , ell,  , ㅡva,  , dir, .]', None),
]


@pytest.mark.parametrize('text,expected,size', WORD_TOKENIZER_CASES)
def test_tokenize(text, expected, size):
    """CatalanWordTokenizerTest.testTokenize (CatalanWordTokenizer.INSTANCE)"""
    tokens = get_language('ca-ES').word_tokenizer.tokenize(text)
    if expected is not None:
        # (List.toString())
        assert '[' + ', '.join(tokens) + ']' == expected
    if size is not None:
        assert len(tokens) == size


# --- CatalanSentenceTokenizerTest ---

SPLITS = [
    # Simple sentences
    ('Això és una frase. ', 'Això és una altra frase.'),
    ("Aquesta és l'egua. ", 'Aquell és el cavall.'),
    ("Aquesta és l'egua? ", 'Aquell és el cavall.'),
    ('Vols col·laborar? ', 'Sí, i tant.'),
    ("Com vas d'il·lusió? ", 'Bé, bé.'),
    ('Com vas d’il·lusió? ', 'Bé, bé.'),
    ('És d’abans-d’ahir? ', 'Bé, bé.'),
    ('És d’abans-d’ahir! ', 'Bé, bé.'),
    ('Què vols dir? ', 'Ja ho tinc!'),
    ('Què? ', 'Ja ho tinc!'),
    ('Ah! ', 'Ja ho tinc!'),
    ('Ja ho tinc! ', 'Què vols dir?'),
    ('Us explicaré com va anar: ', '»La Maria va engegar el cotxe'),
    ('diu que va dir. ', 'A mi em feia estrany.'),
    ('Són del s. III dC. ', 'Són importants les pintures.'),
    ('Primera frase.[4] ', 'Segona frase'),
    ('23. Article vint-i-tres',),
    ('Això és una frase.   ', 'Això és una altra frase.'),
    ('Això és una frase.\n', 'Això és una altra frase.'),
    ('Això és una frase. \n', 'Això és una altra frase.'),
    ('Això és una frase. \n  ', 'Això és una altra frase.'),
    ('Això és una frase.\r\n', 'Això és una altra frase.'),
    ('Això és una frase. \r\n  ', 'Això és una altra frase.'),
    ('Això és una frase. \n \n', '  Això és una altra frase.'),
    ('Això és una frase? \n', 'Sí, i tant.'),
    ('Ja ho tinc!\n', 'Què vols dir?'),
    # N., t.
    ('Vés-te’n. ', 'A mi em feia estrany.'),
    ("Vés-te'n. ", 'A mi em feia estrany.'),
    ("VÉS-TE'N. ", 'A mi em feia estrany.'),
    ('Canten. ', 'A mi em feia estrany.'),
    ('Desprèn. ', 'A mi em feia estrany.'),
    ('(n. 3).',),
    (' n. 3',),
    ('n. 3',),
    ('("n. 3".',),
    ('En el t. 2 de la col·lecció',),
    ("Llança't. ", 'Fes-ho.'),
    ("És professor a l'Inst. Joan Vives.",),
    # Initials
    ("A l'atenció d'A. Comes.",),
    ("A l'atenció d'À. Comes.",),
    ('Són els alumnes de Física I. ', 'Ara no venen ben preparats.'),
    ('Són els alumnes de Física II. ', 'Ara no venen ben preparats.'),
    ('Va ser obra de Felip V. ', 'Ara ho sabem.'),
    ("Va ser obra d'Alfons X. ", 'Ara ho sabem.'),
    ('La manera com funciona la publicació a X. ', 'No és una decisió fàcil.'),
    ('La manera com funciona la publicació a X. ', 'Probablement no és una decisió fàcil.'),
    ('Núm. operació 220130000138.',),
    # Ellipsis
    ('el vi no és gens propi de monjos, amb tot..." vetllant, això sí',),
    ('Desenganyeu-vos… ', "L’únic problema seriós de l'home en aquest món és el de subsistir."),
    ('és clar… traduir és una feina endimoniada',),
    ("«El cordó del frare…» surt d'una manera desguitarrada",),
    ('convidar el seu heroi –del ram que sigui–… a prendre cafè.',),
    # Abbreviations
    ('No Mr. Spock sinó un altre.',),
    ('Vegeu el cap. 24 del llibre.',),
    ('Vegeu el cap. IX del llibre.',),
    ("Viu al núm. 24 del carrer de l'Hort.",),
    ("Viu al núm. vint-i-quatre del carrer de l'Hort.",),
    ('El Dr. Joan no vindrà.',),
    ('Distingit Sr. Joan,',),
    ('Molt Hble. Sr. President',),
    ('de Sant Nicolau (del s. XII; cor gòtic del s. XIV) i de Sant ',),
    ('Va ser el 5è. classificat.',),
    ('Va ser el 5è. ', "I l'altre el 4t."),
    ('Art. 2.1: Són obligats els...',),
    ('Arriba fins a les pp. 50-52.',),
    ('Arriba fins a les pp. XI-XII.',),
    ('i no ho vol. ', 'Malgrat que és així.'),
    ('i és del vol. 3 de la col·lecció',),
    ('Els EE. UU. són un país.',),
    ('Els EE.UU. són un país.',),
    ('Els ee. uu. són un país.',),
    ('Els ee.uu. són un país.',),
    ("Me'n vaig als EE.UU. ", 'Bon viatge.'),
    ('Garcia, Joan (coords.)',),
    ('fins al curs de 8è. ', '"No es pot oblidar allò"'),
    ('fins al curs de 8è. ', '-No es pot oblidar allò'),
    ('Aprovació (ca. 2010), suspensió (c. 2011), segle (ca. XIX)',),
    ('La Dra. Ma. Victòria.',),
    ('la projectada Sta. Ma. de Gàllecs',),
    ("El fruit té de 6 a 8 cm de long. i 4 a 6 cm d'ample.",),
    ('Geiger (Proc. Roy. Soc. 1 de febrer de 1910).',),
    ('El poble tenia 50 hab. a finals de segle XX.',),
    ('Vam veure un documental sobre Warner Bros. Cartoons.',),
    ('Vam veure un documental sobre la Warner Bros. ', 'Era boníssim.'),
    ("La Warner Bros. feia coses que m'agradaven molt.",),
    ('Introduïu açí el vostre text. ',
     'o feu servir aquest texts com a a exemple per a alguns errades que LanguageTool hi pot detectat.'),
    # Unknown abbreviations inside parentheses
    ('(Impren. Disss)',),
    ('(Impren. 188-disss)',),
    ('[Impren. Disss]',),
    ('[Impren. 188-disss]',),
    ('{Impren. Disss}',),
    ('{Impren. 188-disss}',),
    ('(Impren. Disss. Ioo)',),
    ('(Impren. Disss. Ioo. A. B. Garcia)',),
    ('Impren. \n', 'Disss'),
    ('(Impren. \n', 'Disss)'),
    # Exception to abbreviations
    ('Ell és el número u. ', 'Jo el dos.'),
    ('Té un trau al cap. ', "Cal portar-lo a l'hospital."),
    ('Això passa en el PP. ', 'Però, per altra banda,'),
    ('Ceba, all, carabassa, etc. ', 'En comprem a la fruiteria.'),
    # Units
    ('1 500 m/s. ', 'Neix a'),
    ("Són d'1 g. ", 'Han estat condicionades.'),
    ("Són d'1 m. ", 'Han estat condicionades.'),
    ('Hi vivien 50 h. ', 'Després el poble va créixer.'),
    ("L'acte serà a les 15.30 h. de la vesprada.",),
    ('De 9:00 a 17:00 h. (aproximadament).',),
    ('Aquesta és la resolució No. 2 de les Corts.',),
    # Error: missing space. It is not split in order to trigger other errors.
    ("s'hi enfrontà quan G.Oueddei n'esdevingué líder",),
    ('el jesuïta alemany J.E. Nithard',),
    ('PERNIL DOLÇ\nBACON\nPEPERONI\nPEBROT VERD\nOLIVES',),
    ('El framework .NET o ASP.NET o Microsoft.Net',),
]


@pytest.mark.parametrize('sentences', SPLITS)
def test_sentence_tokenize(sentences):
    """CatalanSentenceTokenizerTest.testTokenize (TestTools.testSplit with
    new SRXSentenceTokenizer(Catalan.getInstance()))"""
    tokenizer = SRXSentenceTokenizer(get_language('ca-ES'))
    assert tokenizer.tokenize(''.join(sentences)) == list(sentences)
