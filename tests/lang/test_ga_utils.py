"""Port of org.languagetool.tagging.disambiguation.rules.ga.UtilsTest (tests
of org.languagetool.tagging.ga.Utils), plus checks of the other Utils
functions."""

from langtool.lang.ga import utils
from langtool.lang.ga.utils import Retaggable


def test_to_lower_case_irish():
    """UtilsTest.testToLowerCaseIrish"""
    assert utils.to_lower_case_irish('TEST') == 'test'
    assert utils.to_lower_case_irish('Test') == 'test'
    assert utils.to_lower_case_irish('tAON') == 't-aon'
    assert utils.to_lower_case_irish('nAON') == 'n-aon'


def test_un_lenited():
    """UtilsTest.testUnLenited"""
    assert utils.un_lenite('Khate') == 'Kate'
    assert utils.un_lenite('chan') == 'can'
    assert utils.un_lenite('bha') == 'ba'
    assert utils.un_lenite('bh') == 'b'
    assert utils.un_lenite('can') is None
    assert utils.un_lenite('a') is None


def test_un_eclipse_char():
    """UtilsTest.testUnEclipseChar"""
    # properly eclipsed
    assert utils.un_eclipse_char('gcarr', 'g', 'c') == 'carr'
    assert utils.un_eclipse_char('gCarr', 'g', 'c') == 'Carr'
    # improperly eclipsed
    assert utils.un_eclipse_char('G-carr', 'g', 'c') == 'Carr'
    assert utils.un_eclipse_char('Gcarr', 'g', 'c') == 'Carr'
    assert utils.un_eclipse_char('GCARR', 'g', 'c') == 'CARR'
    # not eclipsed
    assert utils.un_eclipse_char('carr', 'g', 'c') is None


def test_un_eclipse():
    """UtilsTest.testUnEclipse"""
    assert utils.un_eclipse('g-carr') == 'carr'
    assert utils.un_eclipse('n-doras') == 'doras'
    assert utils.un_eclipse('N-geata') == 'Geata'
    assert utils.un_eclipse('bpeann') == 'peann'
    assert utils.un_eclipse('mbean') == 'bean'
    assert utils.un_eclipse('N-éin') == 'Éin'
    assert utils.un_eclipse('bhfocal') == 'focal'
    assert utils.un_eclipse('Bhfocal') == 'Focal'
    assert utils.un_eclipse('Bfocal') == 'Focal'
    assert utils.un_eclipse('carr') is None


def test_un_lenite_definite_s():
    """UtilsTest.testUnLeniteDefiniteS"""
    assert utils.un_lenite_definite_s('t-seomra1') == 'seomra1'
    assert utils.un_lenite_definite_s('tseomra2') == 'seomra2'
    assert utils.un_lenite_definite_s('tSeomra3') == 'Seomra3'
    assert utils.un_lenite_definite_s('TSeomra4') == 'Seomra4'
    assert utils.un_lenite_definite_s('Tseomra5') == 'Seomra5'
    assert utils.un_lenite_definite_s('t-Seomra6') == 'Seomra6'
    assert utils.un_lenite_definite_s('T-Seomra7') == 'Seomra7'
    assert utils.un_lenite_definite_s('T-seomra8') == 'Seomra8'
    assert utils.un_lenite_definite_s('seomra9') is None


def test_demutate():
    """UtilsTest.testDemutate"""
    tmp = utils.demutate('gcharr')
    assert tmp.word == 'carr'
    assert tmp.append_tag == ':EclLen'
    tmp = utils.demutate('t-seomra')
    assert tmp.word == 'seomra'
    assert tmp.restrict_to_pos == '(?:C[UMC]:)?Noun:.*:DefArt'


def test_fix_suffix():
    """UtilsTest.testFixSuffix"""
    tmp = utils.fix_suffix('caimiléaracht')
    assert tmp.word == 'caimiléireacht'


def test_un_ponc():
    """UtilsTest.testUnPonc"""
    assert utils.un_ponc('ċuir') == 'chuir'
    assert utils.un_ponc('ĊUIR') == 'CHUIR'
    assert utils.un_ponc('Ċuir') == 'Chuir'
    assert utils.un_ponc('FÉAĊ') == 'FÉACH'


def test_simplify():
    """UtilsTest.testSimplify"""
    bold_upper = '\U0001D412\U0001D404\U0001D400\U0001D40D\U0001D400\U0001D413\U0001D407\U0001D400\U0001D408\U0001D411'
    assert utils.simplify_mathematical(bold_upper) == 'SEANATHAIR'
    bold_lower = '\U0001D42C\U0001D41E\U0001D41A\U0001D427\U0001D41A\U0001D42D\U0001D421\U0001D41A\U0001D422\U0001D42B'
    assert utils.simplify_mathematical(bold_lower) == 'seanathair'
    assert utils.simplify_mathematical('\U0001D7FF\U0001D7FF\U0001D7FF', False, True) == '999'


def test_greek_to_latin():
    """UtilsTest.testGreekToLatin"""
    assert utils.greek_to_latin('ΒΟΤΤΟΜ') == 'BOTTOM'


def test_has_mixed_greek_and_latin():
    """UtilsTest.testHasMixedGreekAndLatin"""
    assert utils.has_mixed_greek_and_latin('Nοt') is True


def test_is_all_maths_chars():
    """UtilsTest.testIsAllMathsChars"""
    bold_upper = '\U0001D412\U0001D404\U0001D400\U0001D40D\U0001D400\U0001D413\U0001D407\U0001D400\U0001D408\U0001D411'
    assert utils.is_all_maths_chars('foo') is False
    assert utils.is_all_maths_chars('f\U0001D412') is False
    assert utils.is_all_maths_chars(bold_upper) is True


TORRACH = 'ｔｏｒｒａｃｈ'


def test_is_all_half_width_chars():
    """UtilsTest.testIsAllHalfWidthChars"""
    assert utils.is_all_half_width_chars(TORRACH) is True
    assert utils.is_all_half_width_chars(TORRACH + 'a') is False


def test_halfwidth_latin_to_latin():
    """UtilsTest.testHalfwidthLatinToLatin"""
    assert utils.halfwidth_latin_to_latin(TORRACH) == 'torrach'


# --- further checks of Utils (behaviour of the Java code) ---

def test_simplify_quirks():
    # characters that are no mathematical symbols are dropped (as in Java)
    assert utils.simplify_mathematical('a\U0001D400b') == 'A'
    # unmapped symbols (Greek without normaliseGreek) are kept
    assert utils.simplify_mathematical('\U0001D6A8') == '\U0001D6A8'
    assert utils.simplify_mathematical('\U0001D6A8', True, False) == 'Α'
    assert utils.simplify_mathematical('\U0001D6A4\U0001D7CE') == 'i\U0001D7CE'
    assert utils.simplify_mathematical('\U0001D7CE\U0001D7D8', False, True) == '00'


def test_lenite_eclipse():
    assert utils.lenite('bean') == 'bhean'
    # always a lowercase 'h' (the Java code checks Character.isUpperCase(1))
    assert utils.lenite('BEAN') == 'BhEAN'
    assert utils.lenite('sráid') == 'shráid'
    assert utils.lenite('sport') == 'sport'
    assert utils.lenite('athair') == 'athair'
    assert utils.lenite('b') == 'b'
    assert utils.eclipse('athair') == 'n-athair'
    assert utils.eclipse('Éire') == 'nÉire'
    assert utils.eclipse('focal') == 'bhfocal'
    assert utils.eclipse('Baile') == 'mBaile'
    assert utils.eclipse('carr') == 'gcarr'
    assert utils.eclipse('doras') == 'ndoras'
    assert utils.eclipse('peann') == 'bpeann'
    assert utils.eclipse('teach') == 'dteach'
    assert utils.eclipse('lá') == 'lá'
    assert utils.eclipse('') == ''
    assert utils.eclipse(None) is None


def test_case_functions():
    assert utils.starts_with_uppercase('mBaile')
    assert utils.starts_with_uppercase('bhFocal')
    assert utils.starts_with_uppercase('tÉan')
    assert utils.starts_with_uppercase('hÉireann')
    assert utils.starts_with_uppercase('tSeomra')
    assert utils.starts_with_uppercase('Baile')
    assert not utils.starts_with_uppercase('baile')
    assert utils.is_all_uppercase('bhFOCAL')
    assert utils.is_all_uppercase('nGAILLIMH')
    assert not utils.is_all_uppercase('nGaillimh')
    assert utils.is_all_uppercase('BAILE 1')
    assert utils.contains_ponc('aċ')
    assert not utils.contains_ponc('ach')


def test_morph_word():
    def as_tuples(rts):
        return [(r.word, r.restrict_to_pos, r.append_tag) for r in rts]
    assert as_tuples(utils.morph_word('t-seomra')) == [('seomra', '(?:C[UMC]:)?Noun:.*:DefArt', ':MorphError')]
    assert as_tuples(utils.morph_word('chaimiléaracht')) == [
        ('caimiléaracht', '', ':Len:MorphError'), ('caimiléaracht', '', ':DefArt:MorphError'),
        ('caimiléireacht', '.*Noun.*', ':MorphError:Len:MorphError')]
    assert as_tuples(utils.morph_word('gcarr')) == [('carr', '', ':Ecl:MorphError'),
                                                    ('carr', '', ':DefArt:MorphError')]
    assert as_tuples(utils.morph_word('carr')) == []
    r = Retaggable('a', None, None)
    r.set_append_tag(':X')
    r.set_restrict_to_pos('Noun.*')
    r.set_restrict_to_pos('Adj.*')
    assert (r.append_tag, r.restrict_to_pos) == (':X', 'Noun.*|Adj.*')


def test_has_mixed_greek_and_cyrillic():
    assert not utils.has_mixed_greek_and_latin('Not')
    # as in Java, this checks for Latin and Cyrillic characters
    assert utils.has_mixed_greek_and_cyrillic('Nоt')
    assert not utils.has_mixed_greek_and_cyrillic('Nοt')
