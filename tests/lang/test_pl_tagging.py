"""Port of org.languagetool.tagging.pl.PolishTaggerTest,
org.languagetool.synthesis.pl.PolishSynthesizerTest,
org.languagetool.tokenizers.pl.PolishWordTokenizerTest,
org.languagetool.tokenizers.pl.PolishSentenceTokenizerTest and
org.languagetool.tagging.disambiguation.PolishDisambiguationRuleTest, plus
checks of PolishTagger, PolishSynthesizer and PolishWordTokenizer."""

import os

import pytest

from conftest import DATA, require_dictionaries
from langtool import jregex
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.pl.tagging import PolishTagger
from langtool.lang.pl.tokenizers import PolishWordTokenizer
from langtool.tokenizers import WordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('pl')


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _as_strings(readings):
    # TestTools.getAsStrings
    return sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in readings)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


# --- PolishTaggerTest ---

# Joined negations the dictionary build accepts but the tagger cannot reach,
# because the form is also an inflected form of an unrelated lexeme and so is
# never handed to PolishTagger.additional_tags(), which only runs for words
# nothing else matched (restored in disambiguation.xml).
KNOWN_MASKED = {'niegodniej', 'nieintratniej', 'nieprzydatniej', 'nieskładniej', 'nieżywotniej'}


@pytest.fixture(scope='module')
def tagger():
    return get_language('pl').tagger


def test_dictionary(tagger):
    """PolishTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0


def test_tagger(tagger):
    """PolishTaggerTest.testTagger"""
    tokenizer = WordTokenizer()
    _my_assert('To jest duży dom.',
               'To/[ten]adj:sg:acc:n1.n2:pos|To/[ten]adj:sg:nom.voc:n1.n2:pos|To/[to]conj|To/[to]qub|'
               'To/[to]subst:sg:acc:n2|To/[to]subst:sg:nom:n2 -- jest/[być]verb:fin:sg:ter:imperf:nonrefl -- '
               'duży/[duży]adj:sg:acc:m3:pos|duży/[duży]adj:sg:nom.voc:m1.m2.m3:pos -- '
               'dom/[dom]subst:sg:acc:m3|dom/[dom]subst:sg:nom:m3', tokenizer, tagger)
    _my_assert('Krowa pasie się na pastwisku.',
               'Krowa/[krowa]subst:sg:nom:f -- pasie/[pas]subst:sg:loc:m3|pasie/[pas]subst:sg:voc:m3|'
               'pasie/[paść]verb:fin:sg:ter:imperf:refl.nonrefl -- się/[się]qub|się/[się]siebie:acc:nakc|'
               'się/[się]siebie:gen:nakc -- na/[na]interj|na/[na]prep:acc|na/[na]prep:loc -- '
               'pastwisku/[pastwisko]subst:sg:dat:n2|pastwisku/[pastwisko]subst:sg:loc:n2', tokenizer, tagger)
    _my_assert('blablabla', 'blablabla/[null]null', tokenizer, tagger)


def test_joined_negation(tagger):
    """PolishTaggerTest.testJoinedNegation: "nie" joined to a comparative or
    superlative, allowed since the 2026 spelling reform"""
    tokenizer = WordTokenizer()
    # adverbs; the lemma is the negated positive form, as for "niepewien" -> "niepewny"
    _my_assert('nielepiej', 'nielepiej/[niedobrze]adv:com', tokenizer, tagger)
    _my_assert('nienajlepiej', 'nienajlepiej/[niedobrze]adv:sup', tokenizer, tagger)
    _my_assert('nieszybciej', 'nieszybciej/[nieszybko]adv:com', tokenizer, tagger)
    # adjectives, in all their case/gender forms
    _my_assert('nietańszy', 'nietańszy/[nietani]adj:sg:acc:m3:com|nietańszy/[nietani]adj:sg:nom.voc:m1.m2.m3:com',
               tokenizer, tagger)
    _my_assert('nielepsza', 'nielepsza/[niedobry]adj:sg:nom.voc:f:com', tokenizer, tagger)
    _my_assert('nienajlepszy',
               'nienajlepszy/[niedobry]adj:sg:acc:m3:sup|nienajlepszy/[niedobry]adj:sg:nom.voc:m1.m2.m3:sup',
               tokenizer, tagger)
    # sentence-initial and all-uppercase
    _my_assert('Nielepiej', 'Nielepiej/[niedobrze]adv:com', tokenizer, tagger)
    _my_assert('NIELEPIEJ', 'NIELEPIEJ/[niedobrze]adv:com', tokenizer, tagger)
    # an imperative homograph the dictionary build rejected: "niemdlej" is a
    # misspelled "nie mdlej", not the comparative adverb of "mdło"
    _my_assert('niemdlej', 'niemdlej/[null]null', tokenizer, tagger)
    _my_assert('niełysiej', 'niełysiej/[null]null', tokenizer, tagger)
    # ... but a homograph whose adverb reading is the strong one stays admissible
    _my_assert('niegorzej', 'niegorzej/[nieźle]adv:com', tokenizer, tagger)
    # banned by the spelling dictionary
    _my_assert('niebardziej', 'niebardziej/[null]null', tokenizer, tagger)
    _my_assert('nienajbardziej', 'nienajbardziej/[null]null', tokenizer, tagger)
    # the prefix is stripped once only, so this does not cascade
    _my_assert('nienielepiej', 'nienielepiej/[null]null', tokenizer, tagger)
    # words that merely start with "nie" must keep their own reading
    _my_assert('niemniej', 'niemniej/[niemniej]qub', tokenizer, tagger)
    _my_assert('niedaleko', 'niedaleko/[niedaleko]adv:pos', tokenizer, tagger)


def _read_verdicts():
    rows = []
    header_seen = False
    with open(os.path.join(DATA, 'pl', 'nie_verdicts.tsv'), encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            if not header_seen:
                header_seen = True
                continue
            rows.append(line.split('\t'))  # (Java: line.split("\t", -1))
    assert rows, 'nie_verdicts.tsv is empty'
    return rows


def _is_tagged(tagger, word):
    return any(r.is_tagged() for r in tagger.tag([word]))


def _has_reading(tagger, word, pos_tag, require_negated_lemma):
    for reading in tagger.tag([word]):
        for token in reading.readings:
            if token.pos_tag is None or not pos_tag.fullmatch(token.pos_tag):
                continue
            if not require_negated_lemma or (token.lemma is not None and token.lemma.startswith('nie')):
                return True
    return False


def test_joined_negation_against_dictionary_verdicts(tagger):
    """PolishTaggerTest.testJoinedNegationAgainstDictionaryVerdicts: the
    joined-negation analysis against the verdicts of the dictionary build
    (tests/data/pl/nie_verdicts.tsv, copied from the Java test resources)"""
    compar_superl = jregex.compile('(adv|adj:.+):(com|sup)')
    missing, masked, unexpected = [], [], []
    checked = 0
    for row in _read_verdicts():
        joined_form, stem = row[0], row[1]
        banned = row[4] == 'Y'
        verdict = row[5]
        if stem.startswith('nie'):
            # double negations such as "nieniepozorniej"
            continue
        if not _has_reading(tagger, stem, compar_superl, False):
            continue
        checked += 1
        tagged = _has_reading(tagger, joined_form, compar_superl, True)
        if verdict == 'admissible':
            if tagged:
                continue
            (masked if _is_tagged(tagger, joined_form) else missing).append(joined_form)
        elif banned or verdict == 'exclude-typo':
            # imperative homographs and spelling-dictionary bans: must stay untagged
            if tagged:
                unexpected.append(joined_form)
    assert checked > 2000, 'fixture did not yield enough testable rows: %d' % checked
    assert not missing, 'admissible joined forms left without any analysis: %s' % missing
    assert not unexpected, 'joined forms tagged although the dictionary build rejected them: %s' % unexpected
    assert KNOWN_MASKED.issuperset(masked), \
        'more joined forms are masked by an unrelated dictionary reading than expected: %s' % masked


def _tags(tagger, word):
    r, = tagger.tag([word])
    return [(t.lemma, t.pos_tag) for t in r.readings]


def test_tagger_case_handling(tagger):
    assert isinstance(tagger, PolishTagger)
    # tags joined with '+' in the dictionary are split into separate readings
    assert _tags(tagger, 'dom') == [('dom', 'subst:sg:acc:m3'), ('dom', 'subst:sg:nom:m3')]
    # the lowercase readings are added for words that are not lowercase, also mixed case ones
    assert _tags(tagger, 'DOM') == _tags(tagger, 'dom')
    assert _tags(tagger, 'DoM') == _tags(tagger, 'dom')
    # lowercase words without readings are looked up with an uppercase first character
    assert ('Kraków', 'subst:sg:nom:m3') in _tags(tagger, 'kraków')
    # no additional tags for mixed case words
    assert _tags(tagger, 'NieLepiej') == [(None, None)]
    readings = tagger.tag(['To', ' ', 'jest'])
    assert [r.start_pos for r in readings] == [0, 2, 3]


# --- PolishSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string():
    """PolishSynthesizerTest.testSynthesizeString"""
    synth = get_language('pl').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('Aaron'), 'subst:sg:gen:m1') == ['Aarona']
    assert synth.synthesize(_dummy_token('Abchaz'), 'subst:sg:inst:m1') == ['Abchazem']
    assert synth.synthesize(_dummy_token('mieć'), 'verb:praet:sg:f:ter:imperf:refl.nonrefl') == ['miała']
    assert synth.synthesize(_dummy_token('brzydko'), 'adv:com') == ['brzydziej']
    # with regular expressions
    assert sorted(synth.synthesize(_dummy_token('toner'), 'subst:sg:gen:m.*', True)) == ['tonera']
    assert sorted(synth.synthesize(_dummy_token('nieduży'), 'adj:sg.*(m[0-9]?|m.n):pos', True)) == [
        'niedużego', 'nieduży']
    assert sorted(synth.synthesize(_dummy_token('mieć'), '.*praet:sg.*', True)) == [
        'miał', 'miała', 'miałam', 'miałaś', 'miałem', 'miałeś', 'miało', 'miałom', 'miałoś']


def test_synthesize_negation_and_corrections():
    synth = get_language('pl').synthesizer
    assert synth.synthesize(_dummy_token('x'), None) is None
    assert synth.synthesize(_dummy_token('x'), None, True) is None
    # ":neg" forms are the ":aff" forms with the prefix "nie"
    token = AnalyzedToken('duży', 'adj:sg:nom.voc:m1.m2.m3:pos', 'duży')
    ger = AnalyzedToken('robienie', 'ger:sg:nom.acc:n2:imperf:aff:refl.nonrefl', 'robić')
    assert synth.synthesize(ger, 'ger:sg:gen:n2:imperf:neg:refl.nonrefl') == ['nierobienia']
    assert synth.synthesize(ger, 'ger:sg:gen:n2:imperf:neg:.*', True) == ['nierobienia']
    assert synth.synthesize(token, 'adj:sg:gen:m1.m2.m3.n1.n2:pos') == ['dużego']
    # '+' in a POS tag: alternatives of a regular expression
    assert sorted(synth.synthesize(token, 'adj:sg:gen:m1.m2.m3.n1.n2:pos+adj:sg:dat:m1.m2.m3.n1.n2:pos')) == [
        'dużego', 'dużemu']
    # an invalid regular expression gives no forms (Java catches the PatternSyntaxException)
    assert synth.synthesize(token, '(.*)(sg|pl.*acc.*', True) == []
    assert synth.get_pos_tag_correction('subst:sg:acc.nom:m3') == 'subst:sg:(.*acc.*|.*nom.*):m3'
    assert synth.get_pos_tag_correction('subst:sg:acc:m3') == 'subst:sg:acc:m3'
    assert synth.get_pos_tag_correction('subst:sg:a.1:m3') == 'subst:sg:a.1:m3'


# --- PolishWordTokenizerTest ---

def test_word_tokenize():
    """PolishWordTokenizerTest.testTokenize"""
    word_tokenizer = PolishWordTokenizer()
    assert word_tokenizer.tokenize('To jest  test') == ['To', ' ', 'jest', ' ', ' ', 'test']
    assert word_tokenizer.tokenize('To\rłamie') == ['To', '\r', 'łamie']
    # hyphen with no whitespace
    assert word_tokenizer.tokenize('A to jest-naprawdę-test!') == ['A', ' ', 'to', ' ', 'jest-naprawdę-test', '!']
    # hyphen at the end of the word
    assert word_tokenizer.tokenize('Niemiecko- i angielsko-polski') == [
        'Niemiecko', '-', ' ', 'i', ' ', 'angielsko-polski']
    # hyphen probably instead of mdash
    assert word_tokenizer.tokenize('Widzę krowę -i to dobrze!') == [
        'Widzę', ' ', 'krowę', ' ', '-', 'i', ' ', 'to', ' ', 'dobrze', '!']
    # mdash
    assert word_tokenizer.tokenize('A to jest zdanie—rzeczywiście—z wtrąceniem.') == [
        'A', ' ', 'to', ' ', 'jest', ' ', 'zdanie', '—', 'rzeczywiście', '—', 'z', ' ', 'wtrąceniem', '.']
    # compound words with hyphens
    compound_sentence = 'To jest kobieta-wojownik w polsko-czeskim ubraniu, która wysłała dwa SMS-y.'
    assert word_tokenizer.tokenize(compound_sentence) == [
        'To', ' ', 'jest', ' ', 'kobieta-wojownik', ' ', 'w', ' ', 'polsko-czeskim', ' ', 'ubraniu', ',', ' ',
        'która', ' ', 'wysłała', ' ', 'dwa', ' ', 'SMS-y', '.']
    # now setup the tagger...
    word_tokenizer.set_tagger(get_language('pl').tagger)
    # we should get 4 more tokens: two hyphen tokens and two for the split words
    assert word_tokenizer.tokenize(compound_sentence) == [
        'To', ' ', 'jest', ' ', 'kobieta', '-', 'wojownik', ' ', 'w', ' ', 'polsko', '-', 'czeskim', ' ',
        'ubraniu', ',', ' ', 'która', ' ', 'wysłała', ' ', 'dwa', ' ', 'SMS-y', '.']
    assert word_tokenizer.tokenize('Miała osiemnaście-dwadzieścia lat.') == [
        'Miała', ' ', 'osiemnaście', '-', 'dwadzieścia', ' ', 'lat', '.']
    # now three-part adja-adja-adj...:
    assert word_tokenizer.tokenize('Słownik polsko-niemiecko-indonezyjski') == [
        'Słownik', ' ', 'polsko', '-', 'niemiecko', '-', 'indonezyjski']
    # number ranges:
    assert word_tokenizer.tokenize('Impreza odbędzie się w dniach 1-23 maja.') == [
        'Impreza', ' ', 'odbędzie', ' ', 'się', ' ', 'w', ' ', 'dniach', ' ', '1', '-', '23', ' ', 'maja', '.']
    assert word_tokenizer.tokenize('Impreza odbędzie się w dniach 1--23 maja.') == [
        'Impreza', ' ', 'odbędzie', ' ', 'się', ' ', 'w', ' ', 'dniach', ' ', '1', '-', '', '-', '23', ' ', 'maja',
        '.']


def test_word_tokenize_more():
    word_tokenizer = get_language('pl').word_tokenizer
    assert isinstance(word_tokenizer, PolishWordTokenizer)
    assert word_tokenizer.tagger is get_language('pl').tagger
    # prefixes that are never split
    assert word_tokenizer.tokenize('anty-wojenny') == ['anty-wojenny']
    # n-dash and the single low quotation mark are tokenizing characters
    assert word_tokenizer.tokenize('a–b ‚c') == ['a', '–', 'b', ' ', '‚', 'c']
    # e-mails and URLs are joined, also after a leading hyphen
    assert word_tokenizer.tokenize('-http://www.example.com/a-b') == ['-', 'http://www.example.com/a-b']
    assert word_tokenizer.tokenize('') == []


# --- PolishSentenceTokenizerTest ---

def test_sentence_tokenize():
    """PolishSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('pl'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('To się wydarzyło 3.10.2000 i mam na to dowody.')
    test_split('To było 13.12 - nikt nie zapomni tego przemówienia.')
    test_split('Heute ist der 13.12.2004.')
    test_split('To jest np. ten debil spod jedynki.')
    test_split('To jest 1. wydanie.')
    test_split('Dziś jest 13. rocznica powstania wąchockiego.')
    test_split('Das in Punkt 3.9.1 genannte Verhalten.')
    test_split('To jest tzw. premier.')
    test_split('Jarek kupił sobie kurteczkę, tj. strój Marka.')
    test_split('„Prezydent jest niemądry”. ', 'Tak wyszło.')
    test_split('„Prezydent jest niemądry”, powiedział premier')
    # from user bug reports:
    test_split('Temperatura wody w systemie wynosi 30°C.',
               'W skład obiegu otwartego wchodzi zbiornik i armatura.')
    test_split('Zabudowano kolumny o długości 45 m. ', 'Woda z ujęcia jest dostarczana do zakładu.')
    # two-letter initials:
    test_split('Najlepszym polskim reżyserem był St. Różewicz. ', 'Chodzi o brata wielkiego poety.')
    # From the abbreviation list:
    test_split('Ks. Jankowski jest prof. teologii.')
    test_split('To wydarzyło się w 1939 r.', 'To był burzliwy rok.')
    test_split('Prezydent jest popierany przez 20 proc. społeczeństwa.')
    test_split('Moje wystąpienie ma na celu zmobilizowanie zarządu partii do działań, które umożliwią uzyskanie '
               '40 proc.',
               'Nie widzę dziś na scenie politycznej formacji, która lepiej by łączyła różne poglądy')
    test_split('To jest zmienna A.', 'Zaś to jest zmienna B.')
    # SKROTY_BEZ_KROPKI in ENDABREVLIST
    test_split('Mam już 20 mln.', 'To powinno mi wystarczyć')
    test_split('Mam już 20 mln. buraków.')
    # ellipsis
    test_split('Rytmem tej wiecznie przemijającej światowej egzystencji […] rytmem mesjańskiej natury jest '
               'szczęście.')
    # sic!
    test_split('W gazecie napisali, że pasy (sic!) pogryzły człowieka.')
    # Numbers with dots.
    test_split('Mam w magazynie dwie skrzynie LMD20. ', 'Jestem żołnierzem i wiem, jak można ich użyć')


# --- PolishDisambiguationRuleTest ---

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


def test_chunker():
    """PolishDisambiguationRuleTest.testChunker"""
    lang = get_language('pl')
    tagger = lang.tagger
    tokenizer = WordTokenizer()
    sentence_tokenizer = SRXSentenceTokenizer(lang)
    disambiguator = MultiWordChunker(lang.resource_path('pl/multiwords.txt'))

    def my_assert(text, expected):
        _my_assert_disambiguated(text, expected, tokenizer, sentence_tokenizer, tagger, disambiguator)

    my_assert('To test... dezambiguacji',
              '/[null]SENT_START To/[ten]adj:sg:acc:n1.n2:pos|To/[ten]adj:sg:nom.voc:n1.n2:pos|To/[to]conj|'
              'To/[to]qub|To/[to]subst:sg:acc:n2|To/[to]subst:sg:nom:n2  /[null]null test/[test]subst:sg:acc:m3|'
              'test/[test]subst:sg:nom:m3 ./[...]<ELLIPSIS> ./[null]null ./[...]</ELLIPSIS>  /[null]null '
              'dezambiguacji/[null]null')
    my_assert('On, to znaczy premier, jest niezbyt mądry',
              '/[null]SENT_START On/[on]adj:sg:acc:m3:pos|On/[on]adj:sg:nom.voc:m1.m2.m3:pos|'
              'On/[on]ppron3:sg:nom:m1.m2.m3:ter:akc.nakc:praep.npraep ,/[null]null  /[null]null '
              'to/[ten]adj:sg:acc:n1.n2:pos|to/[ten]adj:sg:nom.voc:n1.n2:pos|to/[to znaczy]<TO_ZNACZY>|'
              'to/[to]conj|to/[to]qub|to/[to]subst:sg:acc:n2|to/[to]subst:sg:nom:n2  /[null]null '
              'znaczy/[to znaczy]</TO_ZNACZY>|znaczy/[znaczyć]verb:fin:sg:ter:imperf:refl.nonrefl  /[null]null '
              'premier/[premier]subst:pl:acc:f|premier/[premier]subst:pl:dat:f|premier/[premier]subst:pl:gen:f|'
              'premier/[premier]subst:pl:inst:f|premier/[premier]subst:pl:loc:f|premier/[premier]subst:pl:nom:f|'
              'premier/[premier]subst:pl:voc:f|premier/[premier]subst:sg:acc:f|premier/[premier]subst:sg:dat:f|'
              'premier/[premier]subst:sg:gen:f|premier/[premier]subst:sg:inst:f|premier/[premier]subst:sg:loc:f|'
              'premier/[premier]subst:sg:nom:f|premier/[premier]subst:sg:nom:m1|premier/[premier]subst:sg:voc:f|'
              'premier/[premiera]subst:pl:gen:f ,/[null]null  /[null]null '
              'jest/[być]verb:fin:sg:ter:imperf:nonrefl  /[null]null niezbyt/[niezbyt]adv  /[null]null '
              'mądry/[mądry]adj:sg:acc:m3:pos|mądry/[mądry]adj:sg:nom.voc:m1.m2.m3:pos|'
              'mądry/[mądry]subst:sg:nom:m1|mądry/[mądry]subst:sg:voc:m1')
    my_assert('Lubię go z uwagi na krótkie włosy.',
              '/[null]SENT_START Lubię/[lubić]verb:fin:sg:pri:imperf:nonrefl|'
              'Lubię/[lubić]verb:fin:sg:pri:imperf:refl.nonrefl  /[null]null go/[go]subst:pl:acc:n2|'
              'go/[go]subst:pl:dat:n2|go/[go]subst:pl:gen:n2|go/[go]subst:pl:inst:n2|go/[go]subst:pl:loc:n2|'
              'go/[go]subst:pl:nom:n2|go/[go]subst:pl:voc:n2|go/[go]subst:sg:acc:n2|go/[go]subst:sg:dat:n2|'
              'go/[go]subst:sg:gen:n2|go/[go]subst:sg:inst:n2|go/[go]subst:sg:loc:n2|go/[go]subst:sg:nom:n2|'
              'go/[go]subst:sg:voc:n2|go/[on]ppron3:sg:acc:m1.m2.m3:ter:nakc:npraep|'
              'go/[on]ppron3:sg:gen:m1.m2.m3:ter:nakc:npraep|go/[on]ppron3:sg:gen:n1.n2:ter:nakc:npraep  '
              '/[null]null z/[z uwagi na]<PREP:ACC>|z/[z]prep:acc:nwok|z/[z]prep:gen:nwok|z/[z]prep:inst:nwok  '
              '/[null]null uwagi/[uwaga]subst:pl:acc:f|uwagi/[uwaga]subst:pl:nom:f|uwagi/[uwaga]subst:pl:voc:f|'
              'uwagi/[uwaga]subst:sg:gen:f  /[null]null na/[na]interj|na/[na]prep:acc|na/[na]prep:loc|'
              'na/[z uwagi na]</PREP:ACC>  /[null]null krótkie/[krótki]adj:pl:acc:m2.m3.f.n1.n2.p2.p3:pos|'
              'krótkie/[krótki]adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos|krótkie/[krótki]adj:sg:acc:n1.n2:pos|'
              'krótkie/[krótki]adj:sg:nom.voc:n1.n2:pos  /[null]null włosy/[włos]subst:pl:acc:m3|'
              'włosy/[włos]subst:pl:nom:m3|włosy/[włos]subst:pl:voc:m3|włosy/[włosy]subst:pl:acc:p3|'
              'włosy/[włosy]subst:pl:nom:p3|włosy/[włosy]subst:pl:voc:p3 ./[null]null')
    my_assert('Test...',
              '/[null]SENT_START Test/[test]subst:sg:acc:m3|Test/[test]subst:sg:nom:m3 ./[...]<ELLIPSIS> '
              './[null]null ./[...]</ELLIPSIS>')
    my_assert('Test... ',
              '/[null]SENT_START Test/[test]subst:sg:acc:m3|Test/[test]subst:sg:nom:m3 ./[...]<ELLIPSIS> '
              './[null]null ./[...]</ELLIPSIS>  /[null]null')
