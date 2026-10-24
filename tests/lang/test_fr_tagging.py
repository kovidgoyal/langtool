"""Port of org.languagetool.tokenizers.fr.FrenchWordTokenizerTest,
FrenchSentenceTokenizerTest, org.languagetool.tagging.fr.FrenchTaggerTest,
org.languagetool.synthesis.fr.FrenchSynthesizerTest and
org.languagetool.tagging.disambiguation.rules.fr.FrenchRuleDisambiguatorTest,
plus checks of FrenchTagger, FrenchSynthesizer and FrenchWordTokenizer."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import DemoDisambiguator
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.fr.synthesis import FrenchSynthesizer
from langtool.lang.fr.tagging import FrenchTagger
from langtool.lang.fr.tokenizers import FrenchWordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('fr')


@pytest.fixture(scope='module')
def lang():
    return get_language('fr')


@pytest.fixture(scope='module')
def tokenizer(lang):
    # new FrenchWordTokenizer() (which uses FrenchTagger.INSTANCE)
    return FrenchWordTokenizer(lang.tagger)


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


# --- FrenchWordTokenizerTest ---

@pytest.mark.parametrize('text,size', [
    ('name@example.com', 1),
    ('name@example.com.', 2),
    ('name@example.com:', 2),
    ("L'origen de name@example.com.", 7),
    ("jusqu'au bout", 4),
    ('d’aujourd’hui', 2),
    ("d'aujourd’hui", 2),
    ("d'aujourd'hui", 2),
    ("entr'ouvrions", 1),
    ('entr’ouvrions', 1),
    ('Penses-tu', 2),
    ('Strauss-Kahn', 1),
    ('Semble-t-elle', 2),
    ('N’est-il', 3),
    ('Faites-le-moi', 3),
    ('donne-t-on', 2),
    ("qu'est-ce", 3),
    ("t'es-tu", 3),
    ('rendez-vous', 1),
    ('Petit-déjeunes-tu', 2),
    ('Y-a-t-il', 4),
    ('va-t-en', 4),  # wrong, correct: va-t'en
    ("va-t'en", 3),
    ('va-t’en', 3),
    ("d'1", 2),
    ('Rendez-Vous', 1),
    ('sous-trai­tants', 1),
    ('10 000', 1),
    ('1 000 000', 1),
])
def test_tokenize_sizes(tokenizer, text, size):
    """FrenchWordTokenizerTest.testTokenize (the sizes)"""
    assert len(tokenizer.tokenize(text)) == size


@pytest.mark.parametrize('text,expected', [
    ("-L'homme.", "[-, L', homme, .]"),
    ("-Oui -l'homme.", "[-, Oui,  , -, l', homme, .]"),
    ('Qu’est-ce que ç’a à voir ?', '[Qu’, est, -ce,  , que,  , ç’, a,  , à,  , voir,  , ?]'),
    ("Qu’est-ce que ç'a à voir ?", "[Qu’, est, -ce,  , que,  , ç', a,  , à,  , voir,  , ?]"),
    ('Ç’allait être le rêve du XVIIIe siècle.',
     '[Ç’, allait,  , être,  , le,  , rêve,  , du,  , XVIIIe,  , siècle, .]'),
    ('2005 57 114', '[2005,  , 57 114]'),
    ('2005 454', '[2005,  , 454]'),
    ('$1', '[$1]'),
    ("Mais ça ne l'empêche pas de la « décomposer » avec humour.",
     "[Mais,  , ça,  , ne,  , l', empêche,  , pas,  , de,  , la,  , «,  , décomposer,  , »,  , avec,  , humour, .]"),
])
def test_tokenize(tokenizer, text, expected):
    """FrenchWordTokenizerTest.testTokenize (the token lists)"""
    assert _java_list(tokenizer.tokenize(text)) == expected


def test_tokenize_hyphens_and_variation_selectors(tokenizer):
    """Hyphens at the start and the end of a word are separate tokens,
    non-breaking hyphens are hyphens, words with hyphens unknown to the
    tagger are split, variation selectors are joined to the previous
    token"""
    assert tokenizer.tokenize('--bonjour--') == ['-', '-', 'bonjour', '-', '-']
    assert tokenizer.tokenize('arc‑en‑ciel') == ['arc-en-ciel']
    assert tokenizer.tokenize('blabla-blublu') == ['blabla', '-', 'blublu']
    assert tokenizer.tokenize('3,14 et 2.5') == ['3,14', ' ', 'et', ' ', '2.5']
    assert tokenizer.tokenize('❤️ ok') == ['❤️', ' ', 'ok']


# --- FrenchSentenceTokenizerTest ---

SPLITS = [
    ('Je suis Chris.',),
    ('Je suis Chris.',),
    ('Je suis Chris ?!',),
    ('Je suis Chris ?',),
    ('Je suis      Chris ?',),
    ('Je suis Chris...',),
    ('Je suis Chris ...',),
    ('Je suis Chris …',),
    ('Votre nom: Chris !',),
    ('Je suis (...) Chris',),
    ('Je suis Chris (Christopher?).',),
    ('Je suis Chris (Christopher ?).',),
    ('Je suis Chris (Christopher ?!).',),
    ('Je suis E. Macron de France.',),
    ("J'ai beaucoup d'amis (Tom, Lisa, ...).",),
    ("J'ai beaucoup d'amis (Tom, Lisa, ... ).",),
    ("J'ai beaucoup d'amis (Tom, Lisa, …).",),
    ('La fréquence des P.A. et le nombre de fibres recrutées.',),
    ('Mrs. America est une mini-série américaine créée par Dahvi Waller, diffusée depuis le 15 avril 2020 sur le '
     'site de VOD Hulu et la chaîne FX.',),
    ('Il travaille pour Tiffany & Co. à Paris.',),
    ("J'ai beaucoup d'amis (Tom, Lisa, ...) et je suis populaire !",),
    ("J'ai beaucoup d'amis (Tom, Lisa !) et je suis populaire !",),
    ('Ph.D. est un groupe de musique britannique.',),
    ('Google Inc. est une entreprise américaine',),
    ('Le discours de E. Philippe devrait nous éclairer (un peu, beaucoup, ...?) sur ce qui nous attend.',),
    ('Le discours de E. Philippe devrait nous éclairer (un peu, beaucoup, ...?) sur ce qui nous attend.',),
    ('Op. cit., op. cit.',),
    ('IVe siècle av. J.C. en architecture',),
    ('IVe\xa0siècle\xa0av.\xa0J.C.\xa0en\xa0architecture',),
    ('IVe siècle av. J.-C. en architecture',),
    ('sa mort le 19 août 14 apr. J.-C.',),
    ('Je suis Chris.[4] ', 'Je suis Chris.'),
    ('Je suis Chris.[4]\xa0', 'Je suis Chris.'),
    ('gaffa.org',),
    ("Notice BnF de l'éd. Jean Marx.",),
    ("L'Éducation nationale, impr. par ordre de la Convention nationale, Reprod. de l'éd. de : [Paris].",),
    ('Le discours de E. Philippe devrait nous éclairer (un peu, beaucoup, …?) sur ce qui nous attend.',),
    ('Le discours de E. Philippe devrait nous éclairer (un peu, beaucoup, … ?) sur ce qui nous attend.',),
    ('Comment ça va … ?',),
    # without nbsp
    ('« Le film était bien ? » ', '« Il était énorme ! ', "J'ai eu mal au ventre tellement je me suis marré ! »"),
    ('Si « cf. » désigne l’abréviation de « confer »',),
    # with nbsp
    ('«\xa0Le film était bien\xa0?\xa0» ', '«\xa0Il était énorme\xa0! ',
     "J'ai eu mal au ventre tellement je me suis marré\xa0!\xa0»"),
    ('Si «\xa0cf.\xa0» désigne l’abréviation de «\xa0confer\xa0»,',),
    ("Ça ne sert à rien de me dire «\xa0Salut, comment ça va\xa0?\xa0» si tu n'as rien d'autre à dire.",),
    ('«\xa0Madame est dans sa chambre.\xa0» dit le serviteur.',),
    ("«\xa0L'État, c'est moi\xa0!\xa0» dit le roi.",),
    ('Je ferai ça... un autre jour.',),
    ("Qu'en dites-vous ?, demanda-t-il.",),
    ("Qu'en dites-vous ? demanda-t-il.",),
    ("Qu'en dites-vous ! demanda-t-il.",),
    ('Première phrase.Deuxième phrase.',),
]


@pytest.mark.parametrize('sentences', SPLITS)
def test_sentence_tokenize(lang, sentences):
    """FrenchSentenceTokenizerTest.testTokenize (TestTools.testSplit)"""
    stokenizer = SRXSentenceTokenizer(lang)
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


@pytest.mark.parametrize('text', [
    'Je suis Chris. Comment allez vous ?',
    'Je suis Chris?   Comment allez vous ???',
    'Je suis Chris ! Comment allez vous ???',
    'Je suis Chris ? Comment allez vous ???',
    'Je suis Chris. comment allez vous',
    'Je suis Chris (...). comment allez vous',
    'Je suis Chris (la la la …). comment allez vous',
    'Je suis Chris (CHRISTOPHER!). Comment allez vous',
    'Je suis Chris... Comment allez vous.',
])
def test_sentence_tokenize_sizes(lang, text):
    """FrenchSentenceTokenizerTest.testTokenize (the sizes)"""
    assert len(SRXSentenceTokenizer(lang).tokenize(text)) == 2


# --- FrenchTaggerTest ---

def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_dictionary(lang):
    """FrenchTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    entries, _ = lang.tagger.dictionary.count_entries()
    assert entries > 0


@pytest.mark.parametrize('text,expected', [
    ("C'est la vie.",
     "C'/[ce]R dem m s -- est/[est]N m s|est/[être]V etre ind pres 3 s -- la/[la]N m sp|la/[le]D f s|"
     "la/[le]R pers obj 3 f s -- vie/[vie]N f s"),
    ('Je ne parle pas français.',
     'Je/[je]R pers suj 1 s -- ne/[ne]A -- parle/[parler]V imp pres 2 s|parle/[parler]V ind pres 1 s|'
     'parle/[parler]V ind pres 3 s|parle/[parler]V sub pres 1 s|parle/[parler]V sub pres 3 s -- pas/[pas]A|'
     'pas/[pas]N m sp -- français/[français]J m sp|français/[français]N m sp'),
    ('blablabla', 'blablabla/[blablabla]N m s'),
    ('passagère', 'passagère/[passager]J f s|passagère/[passager]N f s'),
    ('nonexistingword', 'nonexistingword/[null]null'),
    ('auto-mutile',
     'auto-mutile/[auto-mutiler]V imp pres 2 s|auto-mutile/[auto-mutiler]V ind pres 1 s|'
     'auto-mutile/[auto-mutiler]V ind pres 3 s|auto-mutile/[auto-mutiler]V sub pres 1 s|'
     'auto-mutile/[auto-mutiler]V sub pres 3 s'),
    ('auto-mutilées', 'auto-mutilées/[auto-mutiler]V ppa f p'),
    ('micro-plastiques', 'micro-plastiques/[micro-plastique]J e p|micro-plastiques/[micro-plastique]N e p'),
    ('sous-espace', 'sous-espace/[sous-espace]N m s'),
    ('sous-corps', 'sous-corps/[sous-corps]N m sp'),
    ('auto-empoisonnement', 'auto-empoisonnement/[auto-empoisonnement]N m s'),
    ('auto-équilibrage', 'auto-équilibrage/[auto-équilibrage]N m s'),
    ('Grand-Chambre', 'Grand-Chambre/[grand-chambre]N f s'),
    ('d’aujourd’hui', "d'/[de]D e sp|d'/[de]P -- aujourd'hui/[aujourd'hui]A"),
    ("d'aujourd’hui", "d'/[de]D e sp|d'/[de]P -- aujourd'hui/[aujourd'hui]A"),
    ("d’aujourd'hui", "d'/[de]D e sp|d'/[de]P -- aujourd'hui/[aujourd'hui]A"),
    ('Fontaine-l’Évêque', "Fontaine-l'Évêque/[Fontaine-l'Évêque]Z e sp"),
    ("Fontaine-l'Évêque", "Fontaine-l'Évêque/[Fontaine-l'Évêque]Z e sp"),
    ("entr'ouvrions",
     "entr'ouvrions/[entr'ouvrir]V ind impa 1 p|entr'ouvrions/[entr'ouvrir]V sub pres 1 p"),
    ('entr’ouvrions',
     "entr'ouvrions/[entr'ouvrir]V ind impa 1 p|entr'ouvrions/[entr'ouvrir]V sub pres 1 p"),
    ('Penses-tu', 'Penses/[penser]V ind pres 2 s|Penses/[penser]V sub pres 2 s -- -tu/[tu]R pers suj 2 s'),
    ('Strauss-Kahn', 'Strauss-Kahn/[Strauss-Kahn]Z e sp'),
    ("va-t'en",
     "va/[aller]V imp pres 2 s|va/[aller]V ind pres 3 s -- -t/[te]R pers obj 2 s -- 'en/[en]R pers obj 3 sp"),
    ('Al-Qaïda', 'Al-Qaïda/[Al-Qaïda]Z f sp'),
    ('minitélévision', 'minitélévision/[minitélévision]N f s'),
    ('soeur', 'soeur/[sœur]N f s'),
    ('oeils-de-boeuf', 'oeils-de-boeuf/[œils-de-bœuf]N m p'),
    ("Ç'avait", "Ç'/[cela]R dem m s -- avait/[avoir]V avoir ind impa 3 s"),
    ('aéro-club', 'aéro-club/[aéro-club]N m s'),
    ('Aéro-club', 'Aéro-club/[aéro-club]N m s'),
    ('Aéro-Club', 'Aéro-Club/[aéro-club]N m s'),
    ('AÉRO-CLUB', 'AÉRO-CLUB/[aéro-club]N m s'),
    ('ex-Le Pen', 'ex/[ex]A|ex/[ex]N e sp -- Le/[le]D m s|Le/[le]R pers obj 3 m s -- Pen/[null]null'),
    ('Saint-Côme-Le Mesnil',
     'Saint-Côme/[Saint-Côme]Z e sp -- Le/[le]D m s|Le/[le]R pers obj 3 m s -- Mesnil/[null]null'),
    ('Dieppe-Le Tréport',
     'Dieppe/[Dieppe]Z e sp -- Le/[le]D m s|Le/[le]R pers obj 3 m s -- Tréport/[null]null'),
    ('Caricaturistes-Les fantassins de la démocratie',
     'Caricaturistes/[caricaturiste]N e p -- Les/[le]D e p|Les/[les]R pers obj 3 e p -- '
     'fantassins/[fantassin]N m p -- de/[de]D e sp|de/[de]P -- la/[la]N m sp|la/[le]D f s|la/[le]R pers obj 3 f s'
     ' -- démocratie/[démocratie]N f s'),
])
def test_tagger(lang, tokenizer, text, expected):
    """FrenchTaggerTest.testTagger"""
    _my_assert(text, expected, tokenizer, lang.tagger)


def test_tagger_apostrophes_and_emojis(lang):
    """Typographic apostrophes are looked up as typewriter apostrophes (the
    token text changes too) in tokens longer than one character; tokens
    with apostrophes get the chunk tags containsTypewriterApostrophe or
    containsTypographicApostrophe; unknown emojis get the tag _emoji_"""
    tagger = lang.tagger
    assert isinstance(tagger, FrenchTagger)
    atr, = tagger.tag(['aujourd’hui'])
    assert atr.token == "aujourd'hui"
    assert [c.chunk_tag for c in atr.chunk_tags] == ['containsTypographicApostrophe']
    atr, = tagger.tag(["aujourd'hui"])
    assert [c.chunk_tag for c in atr.chunk_tags] == ['containsTypewriterApostrophe']
    atr, = tagger.tag(['’'])
    assert atr.token == '’' and not atr.chunk_tags
    emoji, = tagger.tag(['😂'])
    assert [(r.lemma, r.pos_tag) for r in emoji.readings] == [('_emoji_', '_emoji_')]


# --- FrenchSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string(lang):
    """FrenchSynthesizerTest.testSynthesizeStringString"""
    synth = lang.synthesizer
    assert isinstance(synth, FrenchSynthesizer)
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('nager'), 'V ind pres 3 p') == ['nagent']
    assert synth.synthesize(_dummy_token('le'), 'D (m|e) (p|sp)', True) == ['les']
    assert synth.synthesize(_dummy_token('marin'), 'J [me] (p|sp)', True) == ['marins']
    assert synth.synthesize(AnalyzedToken('marine', 'J f s', 'marin'), 'J [me] (p|sp)', True) == ['marins']
    assert synth.synthesize(AnalyzedToken('marine', 'V ind pres 1 s', 'mariner'), 'V ppa [me] (p|sp)',
                            True) == ['marinés']


def test_synthesizer_exceptions_and_numbers(lang):
    """FrenchSynthesizer.isException (forms ending with "è" except
    burkinabè, koinè and épistémè, forms starting with "qq") and the number
    speller of fr.sor"""
    synth = lang.synthesizer
    assert synth.is_exception('informè')
    assert not synth.is_exception('koinè') and not synth.is_exception('Koinè')
    assert synth.is_exception('qqe')
    assert not synth.is_exception('informe')
    assert synth.synthesize(_dummy_token('informer'), 'V ind pres 1 s') == ['informe']
    assert synth.synthesize(AnalyzedToken('21', None, None), '_spell_number_') == ['vingt et un']


# --- FrenchRuleDisambiguatorTest ---

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


_HYBRID = 'hybrid'
_DEMO = 'demo'


@pytest.mark.parametrize('text,expected,disambiguator', [
    ('Il a enfin publié son livre.',
     '/[null]SENT_START Il/[il]R pers suj 3 m s  /[null]null a/[avoir]V avoir ind pres 3 s  /[null]null '
     'enfin/[enfin]A  /[null]null publié/[publier]V ppa m s  /[null]null son/[son]D e s  /[null]null '
     'livre/[livre]N e s ./[null]null', _HYBRID),
    ('Je danse toutes les semaines au club.',
     '/[null]SENT_START Je/[je]R pers suj 1 s  /[null]null danse/[danser]V ind pres 1 s|danse/[danser]V sub pres 1 s'
     '  /[null]null toutes/[tout]D f p  /[null]null les/[le]D e p|les/[les]_GN_FP  /[null]null '
     'semaines/[semaine]N f p|semaines/[semaines]_GN_FP  /[null]null au/[à+le]P+D m s  /[null]null '
     'club/[club]N m s ./[null]null', _HYBRID),
    ('Je danse toutes les semaines au club.',
     '/[null]SENT_START Je/[je]R pers suj 1 s  /[null]null danse/[danse]N f s|danse/[danser]V imp pres 2 s|'
     'danse/[danser]V ind pres 1 s|danse/[danser]V ind pres 3 s|danse/[danser]V sub pres 1 s|'
     'danse/[danser]V sub pres 3 s  /[null]null toutes/[tout]A|toutes/[tout]D f p|toutes/[tout]R f p  /[null]null '
     'les/[le]D e p|les/[les]R pers obj 3 e p  /[null]null semaines/[semaine]N f p  /[null]null '
     'au/[à+le]P+D m s  /[null]null club/[club]N m s ./[null]null', _DEMO),
    ("Quand j'étais petit, je jouais au football.",
     "/[null]SENT_START Quand/[quand]A inte|Quand/[quand]C sub  /[null]null j'/[je]R pers suj 1 s "
     'étais/[être]V etre ind impa 1 s  /[null]null petit/[petit]J m s ,/[null]null  /[null]null '
     'je/[je]R pers suj 1 s  /[null]null jouais/[jouer]V ind impa 1 s  /[null]null au/[à+le]P+D m s  /[null]null '
     'football/[football]N m s ./[null]null', _HYBRID),
    ("Quand j'étais petit, je jouais au football.",
     "/[null]SENT_START Quand/[quand]A inte|Quand/[quand]C sub  /[null]null j'/[je]R pers suj 1 s "
     'étais/[étai]N m p|étais/[être]V etre ind impa 1 s|étais/[être]V etre ind impa 2 s  /[null]null '
     'petit/[petit]J m s|petit/[petit]N m s ,/[null]null  /[null]null je/[je]R pers suj 1 s  /[null]null '
     'jouais/[jouer]V ind impa 1 s|jouais/[jouer]V ind impa 2 s  /[null]null au/[à+le]P+D m s  /[null]null '
     'football/[football]N m s ./[null]null', _DEMO),
    ('Je suis petite.',
     '/[null]SENT_START Je/[je]R pers suj 1 s  /[null]null suis/[être]V etre ind pres 1 s  /[null]null '
     'petite/[petit]J f s ./[null]null', _HYBRID),
    ('Je suis petite.',
     '/[null]SENT_START Je/[je]R pers suj 1 s  /[null]null suis/[suivre]V imp pres 2 s|'
     'suis/[suivre]V ind pres 1 s|suis/[suivre]V ind pres 2 s|suis/[être]V etre ind pres 1 s  /[null]null '
     'petite/[petit]J f s|petite/[petit]N f s ./[null]null', _DEMO),
    ('sous-corps.', '/[null]SENT_START sous-corps/[sous-corps]N m sp ./[null]null', _DEMO),
    # multiwords: d'abord (locution adverbiale)
    ("Je suis d'abord allé au laboratoire.",
     "/[null]SENT_START Je/[je]R pers suj 1 s  /[null]null suis/[être]V etre ind pres 1 s  /[null]null "
     "d'/[d'abord]A abord/[d'abord]A  /[null]null allé/[aller]V ppa m s  /[null]null au/[à+le]P+D m s  /[null]null "
     "laboratoire/[laboratoire]N m s ./[null]null", _HYBRID),
])
def test_chunker(lang, tokenizer, text, expected, disambiguator):
    """FrenchRuleDisambiguatorTest.testChunker (FrenchHybridDisambiguator
    and DemoDisambiguator)"""
    d = lang.disambiguator if disambiguator == _HYBRID else DemoDisambiguator()
    _my_assert_disambiguated(text, expected, tokenizer, SRXSentenceTokenizer(lang), lang.tagger, d)
