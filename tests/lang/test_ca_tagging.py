"""Port of org.languagetool.tagging.ca.CatalanTaggerTest,
org.languagetool.synthesis.ca.CatalanSynthesizerTest and
org.languagetool.tagging.disambiguation.CatalanDisambiguationRuleTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ca')


@pytest.fixture(scope='module')
def lang():
    return get_language('ca-ES')


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


# --- CatalanTaggerTest ---

def test_dictionary(lang):
    """CatalanTaggerTest.testDictionary (TestTools.testDictionary only
    prints warnings for entries without POS tags; check that the dictionary
    can be read completely)"""
    entries, _ = lang.tagger.dictionary.count_entries()
    assert entries > 0


@pytest.mark.parametrize('text,expected', [
    # verbs incorrectes, analitzats amb flexió
    ('enfotia', 'enfotia/[enfotre]VMII1S00|enfotia/[enfotre]VMII3S00'),
    ('quebrada', 'quebrada/[quebrar]VMP00SF0'),
    ('liava', 'liava/[liar]VMII1S00|liava/[liar]VMII3S00'),
    ('UPF', 'UPF/[UPF]NPFSO00'),
    ('Sóc un home molt honrat.',
     'Sóc/[ser]VSIP1S00 -- un/[un]DI0MS0|un/[un]PI0MS000 -- home/[home]I|home/[home]NCMS000 -- '
     'molt/[moldre]VMP00SM0|molt/[molt]DI0MS0|molt/[molt]PI0MS000|molt/[molt]RG -- '
     'honrat/[honrar]VMP00SM0|honrat/[honrat]AQ0MS0'),
    ('blablabla', 'blablabla/[null]null'),
    ('inajornablement', 'inajornablement/[inajornablement]RG'),
    ('Acomplexadament', 'Acomplexadament/[acomplexadament]RG'),
    ('FRANÇA', 'FRANÇA/[França]NPFSG00'),
    # combining characters
    ('demà', 'demà/[demà]NCMS000|demà/[demà]RG'),
    ('Folklòrico-populars', 'Folklòrico-populars/[folklòrico-popular]AQ0CP0'),
])
def test_tagger(lang, text, expected):
    """CatalanTaggerTest.testTagger (CatalanTagger.INSTANCE_CAT,
    CatalanWordTokenizer.INSTANCE)"""
    _my_assert(text, expected, lang.word_tokenizer, lang.tagger)


# --- CatalanSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def _java_array(forms):
    # Arrays.toString()
    return '[' + ', '.join(forms) + ']'


def test_synthesize_string_string(lang):
    """CatalanSynthesizerTest.testSynthesizeStringString
    (CatalanSynthesizer.INSTANCE_CAT)"""
    synth = lang.synthesizer

    def synth_(word, pos):
        return _java_array(synth.synthesize(_dummy_token(word), pos))

    def synth_regex(word, pos):
        return _java_array(synth.synthesize(_dummy_token(word), pos, True))

    assert synth_('1', '_spell_number_') == '[un]'
    assert synth_('11', '_spell_number_') == '[onze]'
    assert synth_('21', '_spell_number_') == '[vint-i-un]'
    assert synth_('24', '_spell_number_') == '[vint-i-quatre]'
    assert synth_('21', '_spell_number_:feminine') == '[vint-i-una]'
    assert synth_('22', '_spell_number_:feminine') == '[vint-i-dues]'
    assert synth_('2', '_spell_number_') == '[dos]'
    assert synth_('2', '_spell_number_:feminine') == '[dues]'
    assert synth_('242', '_spell_number_:feminine') == '[dues-centes quaranta-dues]'
    assert synth_('2251241', '_spell_number_:feminine') == \
        '[dos milions dues-centes cinquanta-una mil dues-centes quaranta-una]'
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth_('sentir', 'VMIP1S0C') == '[sento]'
    assert synth_('sentir', 'VMIP1S0Z') == '[sent]'
    assert synth_('sentir', 'VMSP3S0V') == '[senta]'
    assert synth_('nostre', 'PX1CP0P0') == '[nostres]'
    assert synth_('president', 'NCMP000') == '[presidents]'
    assert synth_('comprovar', 'VMP00SM.?') == '[comprovat]'
    assert synth_regex('albèrxic', 'NCMP000') == '[albèrxics]'
    assert synth_('fer servir', 'VMIP1S0C') == '[faig servir]'
    # with regular expressions:
    assert synth_regex('comprovar', 'V.P.*') == '[comprovades, comprovats, comprovada, comprovat]'
    assert synth_regex('contestar', 'VM[GN]0000.?') == '[contestant, contestar]'


# --- CatalanDisambiguationRuleTest ---

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


@pytest.mark.parametrize('text,expected', [
    ('Santa María del Páramo',
     '/[null]SENT_START Santa/[Santa María del Páramo]NPCNM00|Santa/[sant]AQ0FS0|Santa/[sant]NCFS000  '
     '/[null]null María/[Santa María del Páramo]NPCNM00  /[null]null de/[Santa María del '
     'Páramo]NPCNM00|de/[de]SPS00 l/[Santa María del Páramo]NPCNM00|l/[el]DA0MS0  /[null]null '
     'Páramo/[Santa María del Páramo]NPCNM00'),
    ('Astragalus germaini',
     '/[null]SENT_START Astragalus/[Astragalus germaini]NPCNM00  /[null]null germaini/[Astragalus germaini]NPCNM00'),
    ('Ammoxenus amphalodes',
     '/[null]SENT_START Ammoxenus/[Ammoxenus amphalodes]NPCNM00|Ammoxenus/[Ammoxenus]NPCN000  /[null]null '
     'amphalodes/[Ammoxenus amphalodes]NPCNM00'),
    ('COVID-19', '/[null]SENT_START COVID-19/[COVID-19]NCFS000|COVID-19/[covid-19]NCFS000'),
    ('New York University',
     '/[null]SENT_START New/[New York University]NPCN000  /[null]null York/[New York '
     'University]NPCN000|York/[York]_possible_nompropi  /[null]null University/[New York '
     'University]NPCN000|University/[University]_possible_nompropi'),
    ('Jean-Luc Mélanchon',
     '/[null]SENT_START Jean-Luc/[Jean-Luc Mélanchon]NPMSSP0  /[null]null Mélanchon/[Jean-Luc '
     'Mélanchon]NPMSSP0|Mélanchon/[Mélanchon]_possible_nompropi'),
    ('Yuval Noha Hariri',
     '/[null]SENT_START Yuval/[Yuval]NPCN000  /[null]null Noha/[null]null  /[null]null Hariri/[null]null'),
    ('Yuval Noah Harari',
     '/[null]SENT_START Yuval/[Yuval Noah Harari]NPCN000  /[null]null '
     'Noah/[Noah]_possible_nompropi|Noah/[Yuval Noah Harari]NPCN000  /[null]null '
     'Harari/[Harari]_possible_nompropi|Harari/[Yuval Noah Harari]NPCN000'),
    ("Abans-d'ahir va ser",
     "/[null]SENT_START Abans-d'ahir/[Abans-d'ahir]_marca_passat|Abans-d'ahir/[abans-d'ahir]RG  "
     '/[null]null va/[anar]VAIP3S00|va/[va]_GV_  /[null]null ser/[ser]VSN00000|ser/[ser]_GV_'),
    ('Las Palmas de Gran Canaria',
     '/[null]SENT_START Las/[Las Palmas de Gran Canaria]NPCNG00  /[null]null Palmas/[Las Palmas de Gran '
     'Canaria]NPCNG00|Palmas/[Palmas]_possible_nompropi  /[null]null de/[Las Palmas de Gran '
     'Canaria]NPCNG00  /[null]null Gran/[Las Palmas de Gran Canaria]NPCNG00  /[null]null '
     'Canaria/[Canaria]_possible_nompropi|Canaria/[Las Palmas de Gran Canaria]NPCNG00'),
    ('De tal manera que no vingué.',
     '/[null]SENT_START De/[de tal manera que]LOC_CONJ  /[null]null tal/[de tal manera que]LOC_CONJ  '
     '/[null]null manera/[de tal manera que]LOC_CONJ  /[null]null que/[de tal manera que]LOC_CONJ  '
     '/[null]null no/[no]RN  /[null]null vingué/[venir]VMIS3S00 ./[.]_PUNCT'),
    ('De tal manera ho va fer.',
     '/[null]SENT_START De/[de tal manera]LOC_ADV  /[null]null tal/[de tal manera]LOC_ADV  /[null]null '
     'manera/[de tal manera]LOC_ADV  /[null]null ho/[ho]PP3NN000  /[null]null '
     'va/[anar]VAIP3S00|va/[va]_GV_  /[null]null fer/[fer]VMN00000|fer/[fer]_GV_ ./[.]_PUNCT'),
    ('Al capdavant del Front del Partit.',
     '/[null]SENT_START A/[al capdamunt de]LOC_PREP l/[al capdamunt de]LOC_PREP  /[null]null '
     'capdavant/[al capdamunt de]LOC_PREP  /[null]null de/[al capdamunt de]LOC_PREP '
     'l/[el]DA0MS0|l/[l]_GN_MS  /[null]null '
     'Front/[Front]_GN_MS|Front/[Front]_possible_nompropi|Front/[Front]complement|Front/[front]NCMS000  '
     '/[null]null de/[de]SPS00 l/[el]DA0MS0|l/[l]_GN_MS  /[null]null '
     'Partit/[Partit]_GN_MS|Partit/[Partit]_possible_nompropi|Partit/[Partit]complement|Partit/[partit]NCMS'
     '000 ./[.]_PUNCT'),
    ('Hem manta vegada participat.',
     '/[null]SENT_START Hem/[haver]VAIP1P00|Hem/[haver]_GV_|Hem/[haver]_perfet  /[null]null manta/[manta '
     'vegada]LOC_ADV  /[null]null vegada/[manta vegada]LOC_ADV  /[null]null '
     'participat/[participar]VMP00SM0|participat/[participat]_GV_ ./[.]_PUNCT'),
    ('et al.',
     '/[null]SENT_START et/[et al.]LOC_ADV  /[null]null a/[et al.]LOC_ADV l/[et al.]LOC_ADV ./[et al.]LOC_ADV'),
    ("Al marge d'aquells",
     "/[null]SENT_START A/[al marge d']LOC_PREP l/[al marge d']LOC_PREP  /[null]null marge/[al marge "
     "d']LOC_PREP  /[null]null d'/[al marge d']LOC_PREP "
     'aquells/[aquell]DD0MP0|aquells/[aquell]PD0MP000|aquells/[aquells]complement'),
    ("L'Aquila", "/[null]SENT_START L'/[L'Aquila]NPFSG00 Aquila/[Aquila]_possible_nompropi|Aquila/[L'Aquila]NPFSG00"),
    ('Al després-dinar',
     '/[null]SENT_START A/[al després-dinar]LOC_ADV l/[al després-dinar]LOC_ADV  /[null]null després/[al '
     'després-dinar]LOC_ADV -/[al després-dinar]LOC_ADV dinar/[al després-dinar]LOC_ADV'),
    ("d'una vegada",
     "/[null]SENT_START d'/[d'una vegada]LOC_ADV una/[d'una vegada]LOC_ADV  /[null]null vegada/[d'una "
     'vegada]LOC_ADV'),
    ("D'una vegada",
     "/[null]SENT_START D'/[d'una vegada]LOC_ADV una/[d'una vegada]LOC_ADV  /[null]null vegada/[d'una "
     'vegada]LOC_ADV'),
    ('Puerta del Sol',
     '/[null]SENT_START Puerta/[Puerta del Sol]NPFSG00  /[null]null de/[Puerta del Sol]NPFSG00 l/[Puerta '
     'del Sol]NPFSG00  /[null]null Sol/[Puerta del Sol]NPFSG00|Sol/[Sol]_possible_nompropi'),
    ("A costa d'ell",
     "/[null]SENT_START A/[a costa d']LOC_PREP  /[null]null costa/[a costa d']LOC_PREP  /[null]null d'/[a "
     "costa d']LOC_PREP ell/[ell]PP3MSN00"),
    ('A costa d’ell',
     "/[null]SENT_START A/[a costa d']LOC_PREP  /[null]null costa/[a costa d']LOC_PREP  /[null]null d'/[a "
     "costa d']LOC_PREP ell/[ell]PP3MSN00"),
    ('Els fons voltor',
     '/[null]SENT_START Els/[Els]_GN_MP|Els/[el]DA0MP0  /[null]null fons/[fons]NCMP000|fons/[fons]_GN_MP  '
     '/[null]null voltor/[fons voltor]AQ0MN0|voltor/[voltor]_GN_MP|voltor/[voltor]ignore_concordance'),
    ('La crème de la crème',
     '/[null]SENT_START La/[La]_GN_FS|La/[el]DA0FS0  /[null]null crème/[crème de la '
     'crème]NCFS000|crème/[crème]_GN_FS  /[null]null de/[crème de la '
     'crème]AQ0FS0|de/[de]_GN_FS|de/[de]ignore_concordance  /[null]null la/[crème de la '
     'crème]AQ0FS0|la/[la]_GN_FS|la/[la]ignore_concordance  /[null]null crème/[crème de la '
     'crème]AQ0FS0|crème/[crème]_GN_FS'),
])
def test_chunker(lang, text, expected):
    """CatalanDisambiguationRuleTest.testChunker (CatalanHybridDisambiguator
    of Catalan.getInstance())"""
    _my_assert_disambiguated(text, expected, lang.word_tokenizer, SRXSentenceTokenizer(lang), lang.tagger,
                             lang.disambiguator)
