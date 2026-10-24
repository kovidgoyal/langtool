"""Port of org.languagetool.tokenizers.es.SpanishWordTokenizerTest,
SpanishSentenceTokenizerTest, org.languagetool.tagging.es.SpanishTaggerTest
and org.languagetool.synthesis.es.SpanishSynthesizerTest, plus checks of
SpanishTagger, SpanishSynthesizer and SpanishWordTokenizer."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.es.synthesis import SpanishSynthesizer
from langtool.lang.es.tagging import SpanishTagger
from langtool.lang.es.tokenizers import SpanishWordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('es')


@pytest.fixture(scope='module')
def lang():
    return get_language('es')


@pytest.fixture(scope='module')
def tokenizer(lang):
    # new SpanishWordTokenizer() (which uses SpanishTagger.INSTANCE)
    return SpanishWordTokenizer(lang.tagger)


def _java_list(tokens):
    # List.toString()
    return '[' + ', '.join(tokens) + ']'


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _as_strings(readings):
    # TestTools.getAsStrings
    return sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in readings)


# --- SpanishWordTokenizerTest ---

def test_word_tokenize(tokenizer):
    """SpanishWordTokenizerTest.testTokenize"""
    tokens = tokenizer.tokenize('*test+')
    assert len(tokens) == 3
    assert _java_list(tokens) == '[*, test, +]'
    tokens = tokenizer.tokenize('best-seller Covid-19;sars-cov-2')
    assert len(tokens) == 5
    assert _java_list(tokens) == '[best-seller,  , Covid-19, ;, sars-cov-2]'
    tokens = tokenizer.tokenize('e-mails')
    assert len(tokens) == 1
    assert _java_list(tokens) == '[e-mails]'
    tokens = tokenizer.tokenize('$100')
    assert len(tokens) == 1
    assert _java_list(tokens) == '[$100]'
    tokens = tokenizer.tokenize('$1.000')
    assert len(tokens) == 1
    assert _java_list(tokens) == '[$1.000]'
    tokens = tokenizer.tokenize('$1,400.50')
    assert len(tokens) == 1
    assert _java_list(tokens) == '[$1,400.50]'
    tokens = tokenizer.tokenize('1,400.50$')
    assert len(tokens) == 1
    assert _java_list(tokens) == '[1,400.50$]'
    tokens = tokenizer.tokenize('Ven ‒dijo.')
    assert len(tokens) == 5
    assert _java_list(tokens) == '[Ven,  , ‒, dijo, .]'
    assert len(tokenizer.tokenize('1.º')) == 1
    assert len(tokenizer.tokenize('Es la 21.ª y el 45.º')) == 11
    assert len(tokenizer.tokenize('Es la 21.a y el 45.o')) == 11
    tokens = tokenizer.tokenize('11.as Jornadas de Estudio')
    assert len(tokens) == 7
    assert _java_list(tokens) == '[11.as,  , Jornadas,  , de,  , Estudio]'
    assert len(tokenizer.tokenize('al-Ándalus')) == 1


def test_word_tokenize_hyphens_and_variation_selectors(tokenizer):
    """Unknown words with hyphens are split, except the listed camel-case
    ones; (non-breaking) hyphens become hyphen-minus; variation selectors
    are joined to the previous token"""
    assert tokenizer.tokenize('blablo-blabla') == ['blablo', '-', 'blabla']
    assert tokenizer.tokenize('McGraw-Hill') == ['McGraw-Hill']
    assert tokenizer.tokenize('best‑seller') == ['best-seller']
    assert tokenizer.tokenize('gracias! ✌️') == ['gracias', '!', ' ', '✌️']
    assert tokenizer.tokenize('3,5 y 3.5') == ['3,5', ' ', 'y', ' ', '3.5']
    # without a tagger every word with hyphens is split
    assert SpanishWordTokenizer().tokenize('best-seller') == ['best', '-', 'seller']


# --- SpanishSentenceTokenizerTest ---

SPLITS = [
    # Simple sentences
    ('Esto es una frase. ', 'Esto es otra frase.'),
    ('Esto es una frase.[34] ', 'Esto es otra frase.'),
    ('¿Nos vamos? ', 'Hay que irse.'),
    ('¿Vamos? ', 'Hay que irse.'),
    ('¡Corre! ', 'Hay que irse.'),
    ('1. Artículo primero',),
    # Ellipsis
    ('Entonces... apareció él.',),
    ('Entonces… apareció él.',),
    ('Entoncess… ', 'Apareció él.'),
    ('«El tal del tal…» sale de aquí',),
    ('invitarle –cuando sea–… a tomar café.',),
    # Initials
    ('A la atención de A. Comes.',),
    ('A la atenció de À. Comes.',),
    ('Núm. operación 220130000138.',),
    ('N. operación 220130000138.',),
    ('N.º operación 220130000138.',),
    # Abbreviations
    ('las Sras. diputadas',),
    ('No Mr. Spock sino otro.',),
    ('Ver el cap. 24 del libro.',),
    ('Ver el cap. IX del libro.',),
    ('Vive en el núm. 24 de la calle.',),
    ('El Dr. Joan no vendrá.',),
    ('Distingguido Sr. Juan,',),
    ('Muy Hble. Sr. Presidente',),
    ('de San Nicolás (del s. XII; coro gótico del s. XIV) y de San Mateo.',),
    ('fue el 5o. clasificado.',),
    ('Fue el 5º. ', 'Y el otro el 4º.'),
    ('Art. 2.1: Estarán obligados...',),
    ('Hasta las pp. 50-52.',),
    ('Hasta las pp. XI-XII.',),
    ('y es del vol. 3 de la colección',),
    ('En EE.UU.',),
    ('En EE. UU. por los DD. HH. después de los JJ. OO.',),
    ('En U.S.A. años 30.',),
    ('En U. S. A. años 30.',),
    ('P. ej. esto.',),
    ('Ahora p. ej. esto.',),
    ('Ahora p. e. esto.',),
    ('Son las 5hrs. del domingo.',),
    ('Son las 2as. jornadas.',),
    ('En EE.UU. esto no pasa.',),
    ('En EE. UU. esto no pasa.',),
    ('Me voy a EE. UU. ', 'Buen viaje.'),
    ('Uno (ca. 2010), dos (c. 2011), tres (ca. XIX), cuatro (c. XX)',),
    ('Ayto. de Madrid.',),
    ('¿Quién sabe hablar francés mejor: Tom o Mary?',),
    ('Hola, Albert: ', 'Me puedes decir tu correo?'),
    ('LanguageTooler GmbH recaudará de tu cuenta a través de GoCardless Ltd. la cantidad debajo mencionada.',),
    ('El fruto es una nuez de 6 a 8 cm de long. y 4 a 6 cm de ancho',),
    ('Geiger (Proc. Roy. Soc. 1 de febrero de 1910).',),
    ('Es la resolución No. 2 del parlamento,',),
    ('Con un dto. del 50 %',),
    ('DTO. 50%',),
    ('DTO. DEL 50%',),
    ('Ayto. del Ferrol',),
    ('En el ayto. del municipio.',),
    ('Compré 6 Ltrs. de leche.',),
    ('Mi profesora trabaja los lun., mié. y vie.; los juev. y los dom., no.',),
    # Exception to abbreviations
    ('Esto pasa el PP. ', 'Pero, por otra parte,'),
    ('Cebolla, ajo, calabaza, etc. ', 'Compramos en fruitería.'),
    # Units
    ('1 500 m/s. ', 'Nacen en'),
    ('Son de 1 g. ', 'Han sido acondicionadas.'),
    ('Son de 1 m. ', 'Han sido acondicionadas.'),
    ('Vivían 50 h. ', 'Después el pueblo creció.'),
    ('El acto será a las 15.30 h. de la tarde.',),
    ('Se calcula un Vol. aproximado de 3.5 ml.',),
    ('Se aplicaron 5 cc. de anestesia local durante el procedimiento.',),
    ('El dispositivo opera a 2400 MHz. lo que garantiza una conexión estable.',),
    ('El paciente fue evaluado tras 12 hr. de observación continua.',),
    ('El medicamento se administró pb. dos veces al día.',),
    ('La reunión se realizará en la 3a. sala del edificio principal.',),
    ('El informe médico indica Dx. confirmado de neumonía.',),
    ('Cursó la lic. en Administración de Empresas.',),
    ('Cursó la Lic. En Administración de Empresas.',),
    # Error: missing space. It is not split in order to trigger other errors.
    ('cuando G.Oueddei se convierte en líder',),
    ('El jesuita alemán J.E. Nithard',),
]


@pytest.mark.parametrize('sentences', SPLITS)
def test_sentence_tokenize(lang, sentences):
    """SpanishSentenceTokenizerTest.testTokenize (TestTools.testSplit)"""
    stokenizer = SRXSentenceTokenizer(lang)
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


# --- SpanishTaggerTest ---

def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_dictionary(lang):
    """SpanishTaggerTest.testDictionary (TestTools.testDictionary only
    prints warnings for entries without POS tags; check that the dictionary
    can be read completely)"""
    entries, _ = lang.tagger.dictionary.count_entries()
    assert entries > 0


@pytest.mark.parametrize('text,expected', [
    ('destacadamente', 'destacadamente/[destacadamente]RG'),
    ('DESTACADAMENTE', 'DESTACADAMENTE/[destacadamente]RG'),
    ('alucinadamente', 'alucinadamente/[alucinadamente]RG'),
    ('disputadamente', 'disputadamente/[disputadamente]RG'),
    ('superincómodas', 'superincómodas/[superincómodo]AQ0FP0'),
    # all-upper case that is common noun & proper noun
    ('RIOJA', 'RIOJA/[Rioja]NPCNG00|RIOJA/[rioja]NCMS000'),
    ('dímelo', 'dímelo/[decir]VMM02S0:PP1CS000:PP3MSA00'),
    ('Soy un hombre muy honrado.',
     'Soy/[ser]VSIP1S0 -- un/[uno]DI0MS0 -- hombre/[hombre]I|hombre/[hombre]NCMS000 -- muy/[muy]RG -- '
     'honrado/[honrar]VMP00SM'),
    ('Tengo que ir a mi casa.',
     'Tengo/[tener]VMIP1S0 -- que/[que]CS|que/[que]PR0CN000 -- ir/[ir]VMN0000 -- a/[a]NCFS000|a/[a]SPS00 -- '
     'mi/[mi]DP1CSS|mi/[mi]NCMS000 -- casa/[casa]NCFS000|casa/[casar]VMIP3S0|casa/[casar]VMM02S0'),
    ('blablabla', 'blablabla/[null]null'),
    ('autoeducan', 'autoeducan/[autoeducar]VMIP3P0'),
    ('autorretratarán', 'autorretratarán/[autorretratar]VMIF3P0'),
    ('autorralentizan', 'autorralentizan/[autorralentizar]VMIP3P0'),
    ('autoralentizan', 'autoralentizan/[null]null'),
    ('autoretratarán', 'autoretratarán/[null]null'),
    ('económico-sociales', 'económico-sociales/[económico-social]AQ0CP0'),
    ('jurídico-económicas', 'jurídico-económicas/[jurídico-económico]AQ0FP0'),
])
def test_tagger(lang, tokenizer, text, expected):
    """SpanishTaggerTest.testTagger"""
    _my_assert(text, expected, tokenizer, lang.tagger)


def _my_assert_disambiguated(text, expected, tokenizer, sentence_tokenizer, tagger, disambiguator):
    # TestTools.myAssert(input, expected, tokenizer, sentenceTokenizer, tagger, disambiguator)
    out = []
    for sentence in sentence_tokenizer.tokenize(text):
        tokens = tokenizer.tokenize(sentence)
        a_tokens = tagger.tag([t for t in tokens if _is_word(t)])
        token_array = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)]
        start_pos = 0
        no_whitespace_count = 0
        for token in tokens:
            if _is_word(token):
                pos_tag = a_tokens[no_whitespace_count]
                pos_tag.start_pos = start_pos
                no_whitespace_count += 1
            else:
                pos_tag = tagger.create_null_token(token, start_pos)
            token_array.append(pos_tag)
            start_pos += len(token)
        final_sentence = disambiguator.disambiguate(AnalyzedSentence(token_array))
        out.append(' '.join('|'.join(_as_strings(r.readings)) for r in final_sentence.tokens))
    assert ''.join(out) == expected


def test_disambiguator(lang, tokenizer):
    """SpanishTaggerTest.testDisambiguator (SpanishHybridDisambiguator)"""
    _my_assert_disambiguated(
        'Era muy muy ',
        '/[null]SENT_START Era/[erar]VMIP3S0|Era/[erar]VMM02S0|Era/[ser]VSII1S0|Era/[ser]VSII3S0  /[null]null '
        'muy/[muy muy]LOC_ADV|muy/[muy]_allow_repeat  /[null]null muy/[muy muy]LOC_ADV  /[null]null',
        tokenizer, SRXSentenceTokenizer(lang), lang.tagger, lang.disambiguator)


def test_tagger_apostrophes_and_emojis(lang):
    """Typographic apostrophes are looked up as typewriter apostrophes
    (also single characters after "l"/"d" or before "s") and the readings
    are marked; unknown emojis get the tag _emoji_"""
    tagger = lang.tagger
    atr, = tagger.tag(['O’Neill'])
    assert atr.token == "O'Neill"
    assert atr.typographic_apostrophe
    assert not tagger.tag(["O'Neill"])[0].typographic_apostrophe
    tokens = tagger.tag(['l', '’', 'Alcúdia'])
    assert tokens[1].token == "'" and tokens[1].typographic_apostrophe
    tokens = tagger.tag(['a', '’', 'b'])
    assert tokens[1].token == '’' and not tokens[1].typographic_apostrophe
    emoji, = tagger.tag(['😂'])
    assert [(r.lemma, r.pos_tag) for r in emoji.readings] == [('_emoji_', '_emoji_')]
    assert isinstance(tagger, SpanishTagger)


# --- SpanishSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string(lang):
    """SpanishSynthesizerTest.testSynthesizeStringString"""
    synth = lang.synthesizer
    assert isinstance(synth, SpanishSynthesizer)
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('temer'), 'VMSI3S0') == ['temiera', 'temiese']
    assert synth.synthesize(_dummy_token('presidente'), 'NCCP000') == ['presidentes']
    assert synth.synthesize(_dummy_token('contar'), 'VMSP2P0') == ['contéis']
    assert synth.synthesize(_dummy_token('probar'), 'VMP00SM') == ['probado']
    assert synth.synthesize(_dummy_token('probar'), 'VMP00SM', False) == ['probado']
    # with regular expressions
    assert synth.synthesize(_dummy_token('probar'), 'VMP00SM', True) == ['probado']
    assert synth.synthesize(_dummy_token('probar'), 'VMP00SM|VMG0000', True) == ['probando', 'probado']


def test_synthesizer_verbs_with_words_after_and_numbers(lang):
    """Lemmas of verbs with words after the verb ("hacer clic"), the number
    speller of es.sor and getTargetPosTag (indicative before imperative)"""
    synth = lang.synthesizer
    assert synth.synthesize(AnalyzedToken('x', None, 'hacer clic'), 'VMII3P0') == ['hacían clic']
    assert synth.synthesize(AnalyzedToken('x', None, 'hacer clic'), 'VMII3P0', True) == ['hacían clic']
    assert synth.synthesize(AnalyzedToken('21', None, None), '_spell_number_') == ['veintiuno']
    tags = ['VMIP3S0', 'VMM02S0']
    assert synth.get_target_pos_tag(tags, 'X') == 'VMIP3S0'
    assert tags == ['VMM02S0', 'VMIP3S0']
    assert synth.get_target_pos_tag([], 'X') == 'X'
