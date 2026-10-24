"""Port of org.languagetool.tokenizers.pt.PortugueseWordTokenizerTest and
PortugueseSRXSentenceTokenizerTest."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.pt.tokenizers import PortugueseWordTokenizer


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pt')


@pytest.fixture(scope='module')
def word_tokenizer():
    # new PortugueseWordTokenizer() (which creates a new PortugueseTagger)
    return PortugueseWordTokenizer(get_language('pt').tagger)


# --- PortugueseWordTokenizerTest ---

@pytest.mark.parametrize('sentence,tokens', [
    # testTokeniseBreakChars
    ('Isto é\u00A0um teste', ['Isto', ' ', 'é', '\u00A0', 'um', ' ', 'teste']),
    ('Isto\rquebra', ['Isto', '\r', 'quebra']),
    # testTokeniseHyphenNoWhiteSpace
    ('Agora isto sim é-mesmo!-um teste.',
     ['Agora', ' ', 'isto', ' ', 'sim', ' ', 'é', '-', 'mesmo', '!', '-', 'um', ' ', 'teste', '.']),
    # testTokeniseWordFinalHyphen
    ('Agora isto é- realmente!- um teste.',
     ['Agora', ' ', 'isto', ' ', 'é', '-', ' ', 'realmente', '!', '-', ' ', 'um', ' ', 'teste', '.']),
    # testTokeniseMDash
    ('Agora isto é—realmente!—um teste.',
     ['Agora', ' ', 'isto', ' ', 'é', '—', 'realmente', '!', '—', 'um', ' ', 'teste', '.']),
    # testTokeniseHyphenatedSingleToken
    ('sex-appeal', ['sex-appeal']),
    ('Aix-en-Provence', ['Aix-en-Provence']),
    ('Montemor-o-Novo', ['Montemor-o-Novo']),
    ('Andorra-a-Velha', ['Andorra-a-Velha']),
    ('Tsé-Tung', ['Tsé-Tung']),
    # testTokeniseHyphenatedSplitRegardlessOfLetterCase
    ('jiu-jitsu', ['jiu-jitsu']),
    ('Jiu-jitsu', ['Jiu-jitsu']),
    ('JIU-JITSU', ['JIU-JITSU']),
    ('Jiu-Jitsu', ['Jiu-Jitsu']),
    ('franco-prussiano', ['franco-prussiano']),
    ('Franco-prussiano', ['Franco-prussiano']),
    ('Franco-Prussiano', ['Franco-Prussiano']),
    # testTokeniseHyphenatedSplit
    ('Paris-São Paulo', ['Paris', '-', 'São', ' ', 'Paulo']),
    # this word exists in the speller but not the tagger dict; this may become a problem
    ('Sem-Peixe', ['Sem', '-', 'Peixe']),
    ('húngaro-americano', ['húngaro', '-', 'americano']),
    # testTokeniseHyphenatedClitics (as of dict v0.13!)
    ('diz-se', ['diz-se']),
    ('amamo-lo', ['amamo-lo']),
    ('fi-lo', ['fi-lo']),
    ('pusé-lo', ['pusé-lo']),
    ('canta-lo', ['canta-lo']),  # cantas + o, may not be in speller!
    # pretty rare, but we need to generate these because the 'nos' in 'no-lo' triggers elision in -mos forms
    ('dar-no-lo', ['dar-no-lo']),
    # rare contractions like these are NOT generated
    ('dê-mo', ['dê', '-', 'mo']),
    # testTokeniseMesoclisis (as of dict v0.13!)
    ('fá-lo-á', ['fá-lo-á']),
    ('dir-lhe-ia', ['dir-lhe-ia']),
    ('banhar-nos-emos', ['banhar-nos-emos']),
    # testTokeniseProductivePrefixes: forms that are NOT in the tagger dict (though they might be in the
    # speller); the tagger tags them by identifying the prefix
    ('soto-pôr', ['soto-pôr']),  # speller, but not tagger
    ('soto-trepar', ['soto-trepar']),  # neither speller nor tagger
    # testTokeniseApostrophe (is; should be "d’", "água")
    ("d'água", ['d', "'", 'água']),
    ('d’água', ['d', '’', 'água']),
    # testTokeniseHashtags: Twitter and whatnot; same as English
    ('#CantadasDoBem', ['#', 'CantadasDoBem']),
    # testDoNotTokeniseUserMentions
    ('@user', ['@user']),
    # testTokeniseCurrency
    ('R$45,00', ['R$', '45,00']),
    ('5£', ['5', '£']),
    ('US$249,99', ['US$', '249,99']),
    ('€2.000,00', ['€', '2.000,00']),
    # testTokeniseSplitsPercent
    ('50%', ['50%']),
    ('50%%', ['50%', '%']),  # "%" is a right-edge character that can repeat ONCE
    ('50%OFF', ['50%', 'OFF']),
    ('%50', ['%', '50']),
    ('%', ['%']),
    # testTokeniseNumberAbbreviation
    ('Nº666', ['Nº666']),  # ordinal indicator 'o'
    ('N°666', ['N°666']),  # degree symbol
    ('Nº 420', ['Nº', ' ', '420']),
    ('N.º69', ['N', '.', 'º69']),  # the '.' char splits it
    ('N.º 80085', ['N', '.', 'º', ' ', '80085']),  # the '.' char splits it
    # testDoNotTokeniseOrdinalSuperscript: ordinal indicators
    ('1º', ['1º']), ('2.º', ['2.º']), ('3ºˢ', ['3ºˢ']), ('4.ºˢ', ['4.ºˢ']), ('5ª', ['5ª']), ('6ª', ['6ª']),
    ('7ªˢ', ['7ªˢ']), ('8ªˢ', ['8ªˢ']),
    # superscripts
    ('9ᵒ', ['9ᵒ']), ('10.ᵒ', ['10.ᵒ']), ('11ᵒˢ', ['11ᵒˢ']), ('12.ᵒˢ', ['12.ᵒˢ']), ('13ᵃ', ['13ᵃ']),
    ('14.ᵃ', ['14.ᵃ']), ('15ᵃˢ', ['15ᵃˢ']), ('16.ᵃˢ', ['16.ᵃˢ']),
    # regular lowercase
    ('17o', ['17o']), ('18.o', ['18.o']), ('19os', ['19os']), ('20.os', ['20.os']), ('21a', ['21a']),
    ('22.a', ['22.a']), ('23as', ['23as']), ('24.as', ['24.as']),
    # testDoNotTokeniseDegreeExpressions
    ('25°', ['25°']), ('26,0°', ['26,0°']), ('27.0°', ['27.0°']), ('28,0°C', ['28,0°C']),
    ('29.0°C', ['29.0°C']), ('30,0°c', ['30,0°c']), ('31.0°c', ['31.0°c']), ('32°Ra', ['32°Ra']),
    ('33,1°Rø', ['33,1°Rø']), ('34°N', ['34°N']),
    # testDoNotTokeniseSpaceSeparatedThousands
    ('35 000', ['35 000']), ('36 000 000', ['36 000 000']), ('37 000,00', ['37 000,00']),
    ('38 000 000,00', ['38 000 000,00']), ('39 000°', ['39 000°']), ('40 000%', ['40 000%']),
    ('41 000º', ['41 000º']), ('42 000o', ['42 000o']), ('43 00', ['43', ' ', '00']),
    # testTokeniseExponent
    ('km²', ['km', '²']),
    # testTokeniseCopyrightAndSimilarSymbols
    ('Copyright©', ['Copyright', '©']),
    ('Bacana®', ['Bacana', '®']),
    ('Legal™', ['Legal', '™']),
    # testTokeniseEmoji
    ('☺☺☺Só', ['☺', '☺', '☺', 'Só']),
    # testDoNotTokeniseModifierDiacritics: the tilde here is a unicode modifier char; normally, the unicode
    # a-tilde (ã) is used
    ('Não', ['Não']),
    # testTokeniseExtraWordEdgeChars: left-edge
    ('@50', ['@50']),  # single char
    ('@@50', ['@', '@50']),  # two chars
    ('50@', ['50', '@']),  # wrong edge
    ('666@50', ['666', '@50']),  # middle of the word
    # right-edge
    ('50‰', ['50‰']),  # single char
    ('50‰‰', ['50‰', '‰']),  # two chars
    ('‰50', ['‰', '50']),  # wrong edge
    ('50‰666', ['50‰', '666']),  # middle of the word
    # testTokeniseRarePunctuation
    ('⌈Herói⌋', ['⌈', 'Herói', '⌋']),
    ('″Santo Antônio do Manga″', ['″', 'Santo', ' ', 'Antônio', ' ', 'do', ' ', 'Manga', '″']),
    # testTokeniseParagraphSymbol
    ('§1º', ['§', '1º']),
    # testTokeniseComplexEmoji
    ('🧝🏽‍♀️', ['🧝', '🏽', '‍', '♀️']),
    # testTokeniseUnitsOfMeasure
    ('100mm', ['100mm']),
    ('10x10mm', ['10x10mm']),
    ('10×10mm', ['10', '×', '10mm']),
])
def test_tokenise(word_tokenizer, sentence, tokens):
    """PortugueseWordTokenizerTest (testTokenise)"""
    assert word_tokenizer.tokenize(sentence) == tokens


def test_tokeniser_of_the_language():
    """The word tokenizer of the language is a PortugueseWordTokenizer with
    the Portuguese tagger"""
    lang = get_language('pt-BR')
    assert type(lang.word_tokenizer) is PortugueseWordTokenizer
    assert lang.word_tokenizer.tokenize('Fá-lo-á no dia 12.03.2024 às 12:30.') == [
        'Fá-lo-á', ' ', 'no', ' ', 'dia', ' ', '12.03.2024', ' ', 'às', ' ', '12:30', '.']


# --- PortugueseSRXSentenceTokenizerTest ---

# NOTE: sentences here need to end with a space character so they have correct whitespace when appended
SPLITS = [
    ('Cola o teu próprio texto aqui.',),
    ('Cola o teu próprio texto aqui. ', 'Ou verifica este texto.'),
    # Missing white space between sentences: do not split
    ('Esta é a primeira frase.Esta é a segunda.',),
    # Basic sentence splitting
    ('O Brasil é um país muito grande. ', 'Tem muitos estados e cidades.'),
    ('Hoje está fazendo muito calor. ', 'Vamos tomar sorvete. ', 'Que boa ideia!'),
    ('Você gosta de futebol? ', 'Eu adoro!'),
    # Abbreviations that should NOT split
    ('O Sr. João foi ao mercado.',),
    ('A Sra. Silva mora na Rua das Flores.',),
    ('O Dr. Carlos atendeu o paciente ontem.',),
    ('A Dra. Ana é especialista em pediatria.',),
    ('O Prof. Souza deu uma aula excelente.',),
    ('Comprei frutas, legumes, etc. no supermercado.',),
    ('São precisos documentos, certidões, etc. para o processo.',),
    ('Havia problemas de logística, infraestrutura, etc. ', 'Tudo precisava ser resolvido.'),
    ('Comprei maçãs, peras, laranjas, etc. ', 'Depois fui para casa.'),
    ('O endereço é Av. Paulista, 1000.',),
    ('Moro na R. das Flores, n.º 25.',),
    ('Consulte o cap. 3 para mais informações.',),
    ('Veja a fig. 2 abaixo.',),
    ('O evento ocorreu em jan. de 2023.',),
    # Abbreviations followed by sentence boundary
    ('O contrato foi assinado ontem. ', 'Depois foi registrado em cartório.'),
    ('O Prof. Silva chegou tarde. ', 'A aula começou com atraso.'),
    ('Consulte o Dr. Almeida. ', 'Ele poderá ajudá-lo.'),
    # Question marks and exclamation marks
    ('Você viu o filme? ', 'Eu achei incrível!'),
    ('Como você está? ', 'Estou bem, obrigado.'),
    ('Que dia bonito! ', 'Vamos passear no parque.'),
    ('Será que vai chover? ', 'Melhor levar guarda-chuva.'),
    # Ellipsis
    ('Não sei o que dizer... ', 'É uma situação muito difícil.'),
    ('Ele hesitou por um momento... e então decidiu partir.',),
    ('Ele viria ... ?',),
    ('Ele viria, ... ?',),
    # Ordinal numbers with dot
    ('O 1.º lugar foi do Brasil.',),
    ('A 2.ª colocada foi a Argentina. ', 'O 3.º lugar ficou com o Uruguai.'),
    # Numbers with dots (should not split)
    ('O evento começa às 10.30 e termina às 12.00.',),
    ('O texto tem 3.500 palavras ao todo.',),
    # Initials and proper names
    ('J. K. Rowling é a autora de Harry Potter.',),
    ('O presidente L. I. Lula assinou o decreto. ', 'Será implementado em breve.'),
    # Quotes with sentence boundaries
    ('"Vou embora!", avisou ela. ', 'Todos ficaram tristes.'),
    ('"Não aguento mais!", gritou ela. ', 'Todos olharam.'),
    # URLs (should not split)
    ('Acesse o site em http://www.exemplo.com.br para mais informações.',),
    # Mixed punctuation
    ('O Brasil ganhou! ', 'Que festa incrível! ', 'Todos comemoraram.'),
]


@pytest.mark.parametrize('sentences', SPLITS)
def test_sentence_tokenize(sentences):
    """PortugueseSRXSentenceTokenizerTest.testTokenize (TestTools.testSplit)"""
    tokenizer = SRXSentenceTokenizer(get_language('pt'))
    assert tokenizer.tokenize(''.join(sentences)) == list(sentences)
