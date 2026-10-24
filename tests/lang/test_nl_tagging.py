"""Port of org.languagetool.tokenizers.nl.DutchWordTokenizerTest,
DutchSRXSentenceTokenizerTest, org.languagetool.tagging.nl.DutchTaggerTest
and org.languagetool.synthesis.nl.DutchSynthesizerTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.nl.tokenizers import DutchWordTokenizer
from langtool.tools import is_digit, is_letter


def _java_list(tokens):
    # List.toString()
    return '[' + ', '.join(tokens) + ']'


# --- DutchWordTokenizerTest ---

@pytest.mark.parametrize('text,expected', [
    ('This is\u00A0a test', '[This,  , is, \u00A0, a,  , test]'),
    ("Bla bla oma's bla bla 'test", "[Bla,  , bla,  , oma's,  , bla,  , bla,  , ', test]"),
    ("Bla bla oma`s bla bla 'test", "[Bla,  , bla,  , oma`s,  , bla,  , bla,  , ', test]"),
    ("Ik zie het''", "[Ik,  , zie,  , het, ', ']"),
    ('Ik zie het``', '[Ik,  , zie,  , het, `, `]'),
    ("''Ik zie het", "[', ', Ik,  , zie,  , het]"),
    ("Ik 'zie' het", "[Ik,  , ', zie, ',  , het]"),
    ('Ik ‘zie’ het', '[Ik,  , ‘, zie, ’,  , het]'),
    ('Ik "zie" het', '[Ik,  , ", zie, ",  , het]'),
    ('Ik “zie” het', '[Ik,  , “, zie, ”,  , het]'),
    ("'zie'", "[', zie, ']"),
    ('‘zie’', '[‘, zie, ’]'),
    ('"zie"', '[", zie, "]'),
    ('“zie”', '[“, zie, ”]'),
    ('Ik `zie het', '[Ik,  , `, zie,  , het]'),
    ('Ik ``zie het', '[Ik,  , `, `, zie,  , het]'),
    ("'", "[']"),
    ("''", "[, ', ']"),
    ("'x'", "[', x, ']"),
    ('`x`', '[`, x, `]'),
])
def test_word_tokenize(text, expected):
    """DutchWordTokenizerTest.testTokenize"""
    assert _java_list(DutchWordTokenizer().tokenize(text)) == expected


def test_word_tokenizer_characters():
    """The apostrophes are no tokenizing characters, the underscore is"""
    chars = DutchWordTokenizer().get_tokenizing_characters()
    assert '_' in chars
    assert not any(q in chars for q in ("'", '`', '’', '‘', '´'))
    assert DutchWordTokenizer().tokenize('a_b') == ['a', '_', 'b']


# --- DutchSRXSentenceTokenizerTest ---

SPLITS = [
    ('Dit is een zin.',),
    ('Dit is een zin. ', 'Nog een.'),
    ('Een zin! ', 'Nog een.'),
    ('‘Dat meen je niet!’ kirde Mandy.',),
    ('Een zin... ', 'Nog een.'),
    ("'En nu.. daden!' aan premier Mark Rutte.",),
    ('Op http://www.test.de vind je een website.',),
    ('De brief is op 3-10 gedateerd.',),
    ('De brief is op 31-1 gedateerd.',),
    ('De brief is op 3-10-2000 gedateerd.',),
    ('Vandaag is het 13-12-2004.',),
    ('Op 24.09 begint het.',),
    ('Om 17:00 begint het.',),
    ('In paragraaf 3.9.1 is dat beschreven.',),
    ('Januari jl. is dat vastgelegd.',),
    ('Appel en pruimen enz. werden gekocht.',),
    ('De afkorting n.v.t. betekent niet van toepassing.',),
    ('Bla et al. blah blah.',),
    ('Dat is,, of het is bla.',),
    ('Dat is het.. ', 'Zo gaat het verder.'),
    ('Dit hier is een(!) zin.',),
    ('Dit hier is een(!!) zin.',),
    ('Dit hier is een(?) zin.',),
    ('Dit hier is een(???) zin.',),
    ('Dit hier is een(???) zin.',),
    ('Als voetballer wordt hij nooit een prof. ', 'Maar prof. N.A.W. Th.Ch. Janssen wordt dat wel.'),
    # TODO, zin na dubbele punt
    ('Dat was het: helemaal niets.',),
    ('Dat was het: het is een nieuwe zin.',),
    # https://nl.wikipedia.org/wiki/Aanhalingsteken
    ('Jan zei: "Hallo."',),
    ('Jan zei: “Hallo.”',),
    ('„Hallo,” zei Jan, „waar ga je naartoe?”',),
    ('„Gisteren”, zei Jan, „was het veel beter weer.”',),
    ('Jan zei: „Annette zei ‚Hallo’.”',),
    ('Jan zei: “Annette zei ‘Hallo’.”',),
    ('Jan zei: «Annette zei ‹Hallo›.»',),
    ('Wegens zijn „ziekte” hoefde hij niet te werken.',),
    ('de letter „a”',),
    ('het woord „beta” is afkomstig van ...',),
    # http://taaladvies.net/taal/advies/vraag/11
    ("De voorzitter zei: 'Ik zie hier geen been in.'",),
    ('De voorzitter zei: "Ik zie hier geen been in."',),
    ('De koning zei: "Ik herinner me nog dat iemand \'Vive la république\' riep tijdens mijn eedaflegging."',),
    ('De koning zei: \'Ik herinner me nog dat iemand "Vive la république" riep tijdens mijn eedaflegging.\'',),
    ("De koning zei: 'Ik herinner me nog dat iemand 'Vive la république' riep tijdens mijn eedaflegging.'",),
    ('Otto dacht: wat een nare verhalen hoor je toch tegenwoordig.',),
    # http://taaladvies.net/taal/advies/vraag/871
    ("'Ik vrees', zei Rob, 'dat de brug zal instorten.'",),
    ("'Ieder land', aldus minister Powell, 'moet rekenschap afleggen over de wijze waarop het zijn burgers "
     "behandelt.'",),
    ("'Zeg Rob,' vroeg Jolanda, 'denk jij dat de brug zal instorten?'",),
    ("'Deze man heeft er niets mee te maken,' aldus korpschef Jan de Vries, 'maar hij heeft momenteel geen "
     "leven.'",),
    ("'Ik vrees,' zei Rob, 'dat de brug zal instorten.'",),
    ("'Ieder land,' aldus minister Powell, 'moet rekenschap afleggen over de wijze waarop het zijn burgers "
     "behandelt.'",),
    # http://taaladvies.net/taal/advies/vraag/872
    ("Zij antwoordde: 'Ik denk niet dat ik nog langer met je om wil gaan.'",),
    ("Zij fluisterde iets van 'eeuwig trouw' en 'altijd blijven houden van'.",),
    ("'Heb je dat boek al gelezen?', vroeg hij.",),
    ("De auteur vermeldt: 'Deze opvatting van het vorstendom heeft lang doorgewerkt.'",),
    # http://taaladvies.net/taal/advies/vraag/1557
    ("'Gaat u zitten', zei zij. ", "'De dokter komt zo.'"),
    ("'Mijn broer woont ook in Den Haag', vertelde ze. ", "'Hij woont al een paar jaar samen.'"),
    ("'Je bent grappig', zei ze. ", "'Echt, ik vind je grappig.'"),
    ("'Is Jan thuis?', vroeg Piet. ", "'Ik wil hem wat vragen.'"),
    ("'Ik denk er niet over!', riep ze. ", "'Dat gaat echt te ver, hoor!'"),
    ("'Ik vermoed', zei Piet, 'dat Jan al wel thuis is.'",),
    ('Het is een .Net programma. ', 'Of een .NEt programma.'),
    ('Het is een .Net-programma. ', 'Of een .NEt-programma.'),
    ('SP werd in 2001 de sp.a (Socialistische Partij Anders) en heet sinds 2021 Vooruit.',),
    ('SP.A grijpt terug naar naam met geschiedenis: VOORUIT.',),
]


@pytest.mark.parametrize('sentences', SPLITS)
def test_sentence_tokenize(sentences):
    """DutchSRXSentenceTokenizerTest.testTokenize (TestTools.testSplit)"""
    stokenizer = SRXSentenceTokenizer(get_language('nl'))
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


# --- DutchTaggerTest ---

@pytest.fixture(scope='module')
def tagger():
    require_dictionaries('nl')
    return get_language('nl').tagger


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in r.readings))
           for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_dictionary(tagger):
    """DutchTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0


@pytest.mark.parametrize('text,expected', [
    ('Aardappels koken.', 'Aardappels/[aardappel]ZNW:MRV:DE_ -- koken/[koken]WKW:TGW:INF'),
    ('zwijnden', 'zwijnden/[zwijnen]WKW:VLT:INF'),
    # Tag random accepted compound words
    ('oorlogsbeker', 'oorlogsbeker/[oorlogsbeker]ZNW:EKV:DE_'),
    ('dorpswezen', 'dorpswezen/[dorpswees]ZNW:MRV:DE_|dorpswezen/[dorpswezen]ZNW:EKV:HET'),
    ('varkensweer', 'varkensweer/[varkensweer]ZNW:EKV:HET'),
    ('jongenstablet', 'jongenstablet/[jongenstablet]ZNW:EKV:DE_|jongenstablet/[jongenstablet]ZNW:EKV:HET'),
    ('passagierssituaties', 'passagierssituaties/[passagierssituatie]ZNW:MRV:DE_'),
    # As this does not end in "ings", should not be accepted by CompoundAcceptor
    ('beoordelinggeschiedenis', 'beoordelinggeschiedenis/[null]null'),
    # These do, and are tagged
    ('beoordelingsgeschiedenis', 'beoordelingsgeschiedenis/[beoordelingsgeschiedenis]ZNW:EKV:DE_'),
    ('beoordelingsgeschiedenisje', 'beoordelingsgeschiedenisje/[beoordelingsgeschiedenis]ZNW:EKV:VRK:HET'),
    ('Beoordelingsgeschiedenisjes', 'Beoordelingsgeschiedenisjes/[beoordelingsgeschiedenis]ZNW:MRV:VRK:DE_'),
    # Test regions
    ('Zuidoost-Gouda', 'Zuidoost-Gouda/[Gouda]ENM:LOC:PTS'),
    ('West-Bergambacht', 'West-Bergambacht/[Bergambacht]ENM:LOC:PTS'),
    # Test compound words with 2 parts
    ('beroertegeschiedenisje', 'beroertegeschiedenisje/[beroertegeschiedenis]ZNW:EKV:VRK:HET'),
    ('aspirant-burgemeestertje', 'aspirant-burgemeestertje/[aspirant-burgemeester]ZNW:EKV:VRK:HET'),
    # Test compound words with 3 parts
    ('gastkritiekgeschiedenis', 'gastkritiekgeschiedenis/[null]null'),
    # Test compound words with 3+ parts
    ('haarhalfbergnacht', 'haarhalfbergnacht/[null]null'),
    # Make sure part1 and part2 as duplicates are not accepted
    ('vriendenvrienden', 'vriendenvrienden/[null]null'),
    # This is not modified, as it's already found in dictionary. If it was, getCompoundPOS would give it
    # postag ZNW:EKV, from "mout".
    ('havermout', 'havermout/[havermout]ZNW:EKV:DE_'),
    ('déúr', 'déúr/[deur]ZNW:EKV:DE_'),
    ('kómen', 'kómen/[komen]WKW:TGW:INF'),
    ('kán', 'kán/[kan]ZNW:EKV:DE_|kán/[kunnen]WKW:TGW:1EP|kán/[kunnen]WKW:TGW:3EP'),
    ('ín', 'ín/[in]VRZ|ín/[innen]WKW:TGW:1EP'),
    ('deur-knop', 'deur-knop/[deurknop]ZNW:EKV:DE_'),
])
def test_tagger(tagger, text, expected):
    """DutchTaggerTest.testTagger"""
    _my_assert(text, expected, DutchWordTokenizer(), tagger)


def test_tagger_ignore_spelling(tagger):
    """Words only found after removing accents are ignored by the speller,
    unless they are lowercase and known with an uppercase first character;
    typographic apostrophes are looked up as typewriter apostrophes"""
    kan, = tagger.tag(['kán'])
    assert kan.ignored_by_speller
    deur, = tagger.tag(['deur'])
    assert not deur.ignored_by_speller
    omas, = tagger.tag(['oma’s'])
    assert omas.token == 'oma’s'
    assert omas.is_tagged() == tagger.tag(["oma's"])[0].is_tagged()


# --- DutchSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string():
    """DutchSynthesizerTest.testSynthesizeStringString"""
    require_dictionaries('nl')
    synth = get_language('nl').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('zwemmen'), 'WKW:VLT:INF') == ['zwommen']
    assert synth.synthesize(_dummy_token('hebben'), 'WKW:TGW:3EP', True) == ['hebt', 'heeft']
    # with regular expressions
    assert synth.synthesize(_dummy_token('doorseinen'), 'WKW:VTD:ONV', True) == ['doorgeseind']


def test_synthesizer_number_speller():
    """DutchSynthesizer passes nl.sor (numbers spelled with the
    _spell_number_ POS tag)"""
    require_dictionaries('nl')
    synth = get_language('nl').synthesizer
    assert synth.synthesize(_dummy_token('13'), '_spell_number_') == ['dertien']
