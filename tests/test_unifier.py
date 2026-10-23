"""Port of org.languagetool.rules.patterns.UnifierTest"""

from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.patterns.pattern_token import PatternToken, PosToken
from langtool.patterns.unifier import UnifierConfiguration


def AT(token, pos, lemma):
    return AnalyzedToken(token, pos, lemma)


def prepare_pos_element(pos_string):
    pt = PatternToken('', False, False, False)
    pt.pos_token = PosToken(pos_string, False, regexp=True)
    return pt


def java_array(tokens):
    """Arrays.toString()"""
    if tokens is None:
        return 'null'
    return '[' + ', '.join(str(t) for t in tokens) + ']'


# trivial unification = test if the character case is the same
def test_unification_case():
    cfg = UnifierConfiguration()
    el_lower = PatternToken('\\p{Ll}+', True, True, False)
    el_upper = PatternToken('\\p{Lu}\\p{Ll}+', True, True, False)
    el_all_upper = PatternToken('\\p{Lu}+$', True, True, False)
    cfg.set_equivalence('case-sensitivity', 'lowercase', el_lower)
    cfg.set_equivalence('case-sensitivity', 'uppercase', el_upper)
    cfg.set_equivalence('case-sensitivity', 'alluppercase', el_all_upper)
    lower1 = AT('lower', 'JJR', 'lower')
    lower2 = AT('lowercase', 'JJ', 'lowercase')
    upper1 = AT('Uppercase', 'JJ', 'Uppercase')
    upper2 = AT('John', 'NNP', 'John')
    upper_all1 = AT('JOHN', 'NNP', 'John')
    upper_all2 = AT('JAMES', 'NNP', 'James')

    uni = cfg.create_unifier()

    equiv = {}
    list1 = ['lowercase']
    equiv['case-sensitivity'] = list1
    satisfied = uni.is_satisfied(lower1, equiv)
    satisfied &= uni.is_satisfied(lower2, equiv)
    uni.start_unify()
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()

    satisfied = uni.is_satisfied(upper2, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(lower2, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is False
    uni.reset()

    satisfied = uni.is_satisfied(upper1, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(lower1, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is False
    uni.reset()

    satisfied = uni.is_satisfied(upper2, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(upper1, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is False
    uni.reset()
    equiv.clear()
    list1.clear()

    list1.append('uppercase')
    equiv['case-sensitivity'] = list1
    satisfied = uni.is_satisfied(upper2, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(upper1, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()
    equiv.clear()
    list1.clear()

    list1.append('alluppercase')
    equiv['case-sensitivity'] = list1
    satisfied = uni.is_satisfied(upper2, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(upper1, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is False
    uni.reset()

    satisfied = uni.is_satisfied(upper_all2, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(upper_all1, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True


# slightly non-trivial unification = test if the grammatical number is the same
def test_unification_number():
    cfg = UnifierConfiguration()
    cfg.set_equivalence('number', 'singular', prepare_pos_element('.*[\\.:]sg:.*'))
    cfg.set_equivalence('number', 'plural', prepare_pos_element('.*[\\.:]pl:.*'))
    uni = cfg.create_unifier()

    sing1 = AT('mały', 'adj:sg:blahblah', 'mały')
    sing2 = AT('człowiek', 'subst:sg:blahblah', 'człowiek')

    equiv = {}
    list1 = ['singular']
    equiv['number'] = list1

    satisfied = uni.is_satisfied(sing1, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()

    # for multiple readings - OR for interpretations, AND for tokens
    sing1a = AT('mały', 'adj:pl:blahblah', 'mały')
    satisfied = uni.is_satisfied(sing1, equiv)
    satisfied |= uni.is_satisfied(sing1a, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()

    # check if any of the equivalences is there
    list1.append('plural')
    equiv.clear()
    equiv['number'] = list1
    sing1a = AT('mały', 'adj:pl:blahblah', 'mały')
    satisfied = uni.is_satisfied(sing1, equiv)
    satisfied |= uni.is_satisfied(sing1a, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()

    # now test all possible feature equivalences by leaving type blank
    sing1a = AT('mały', 'adj:pl:blahblah', 'mały')
    equiv.clear()
    equiv['number'] = None
    satisfied = uni.is_satisfied(sing1, equiv)
    satisfied |= uni.is_satisfied(sing1a, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()

    # test non-agreeing tokens with blank types
    satisfied = uni.is_satisfied(sing1a, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is False
    uni.reset()


# slightly non-trivial unification = test if the grammatical number & gender is the same
def test_unification_number_gender():
    cfg = UnifierConfiguration()
    sg = PatternToken('', False, False, False)
    sg.pos_token = PosToken('.*[\\.:]sg:.*', False, regexp=True)
    cfg.set_equivalence('number', 'singular', sg)
    pl = PatternToken('', False, False, False)
    pl.pos_token = PosToken('.*[\\.:]pl:.*', False, regexp=True)
    cfg.set_equivalence('number', 'plural', pl)
    fem = PatternToken('', False, False, False)
    fem.pos_token = PosToken('.*[\\.:]f', False, regexp=True)
    cfg.set_equivalence('gender', 'feminine', fem)
    masc = PatternToken('', False, False, False)
    masc.pos_token = PosToken('.*[\\.:]m', False, regexp=True)
    cfg.set_equivalence('gender', 'masculine', masc)

    uni = cfg.create_unifier()

    sing1 = AT('mały', 'adj:sg:blahblah:m', 'mały')
    sing1a = AT('mała', 'adj:sg:blahblah:f', 'mały')
    sing1b = AT('małe', 'adj:pl:blahblah:m', 'mały')
    sing2 = AT('człowiek', 'subst:sg:blahblah:m', 'człowiek')

    equiv = {'number': None, 'gender': None}

    satisfied = uni.is_satisfied(sing1, equiv)
    satisfied |= uni.is_satisfied(sing1a, equiv)
    satisfied |= uni.is_satisfied(sing1b, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    uni.start_next_token()
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    assert java_array(uni.get_unified_tokens()) == \
        '[mały[mały/adj:sg:blahblah:m*], człowiek[człowiek/subst:sg:blahblah:m*]]'
    uni.reset()


# checks if all tokens share the same set of features to be unified
def test_multiple_feats():
    cfg = UnifierConfiguration()
    cfg.set_equivalence('number', 'singular', prepare_pos_element('.*[\\.:]sg:.*'))
    cfg.set_equivalence('number', 'plural', prepare_pos_element('.*[\\.:]pl:.*'))
    cfg.set_equivalence('gender', 'feminine', prepare_pos_element('.*[\\.:]f([\\.:].*)?'))
    cfg.set_equivalence('gender', 'masculine', prepare_pos_element('.*[\\.:]m([\\.:].*)?'))
    cfg.set_equivalence('gender', 'neutral', prepare_pos_element('.*[\\.:]n([\\.:].*)?'))

    uni = cfg.create_unifier()

    sing1 = AT('mały', 'adj:sg:blahblah:m', 'mały')
    sing1a = AT('mały', 'adj:pl:blahblah:f', 'mały')
    sing1b = AT('mały', 'adj:pl:blahblah:f', 'mały')
    sing2 = AT('zgarbiony', 'adj:pl:blahblah:f', 'zgarbiony')
    sing3 = AT('człowiek', 'subst:sg:blahblah:m', 'człowiek')

    equiv = {'number': None, 'gender': None}

    satisfied = uni.is_satisfied(sing1, equiv)
    satisfied |= uni.is_satisfied(sing1a, equiv)
    satisfied |= uni.is_satisfied(sing1b, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing2, equiv)
    uni.start_next_token()
    satisfied &= uni.is_satisfied(sing3, equiv)
    uni.start_next_token()
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is False
    uni.reset()

    # now test the simplified interface
    uni.is_unified(sing1, equiv, False)
    uni.is_unified(sing1a, equiv, False)
    uni.is_unified(sing1b, equiv, True)
    uni.is_unified(sing2, equiv, True)
    assert uni.is_unified(sing3, equiv, True) is False
    uni.reset()

    sing1a = AT('osobiste', 'adj:pl:nom.acc.voc:f.n.m2.m3:pos:aff', 'osobisty')
    sing1b = AT('osobiste', 'adj:sg:nom.acc.voc:n:pos:aff', 'osobisty')
    sing2 = AT('godło', 'subst:sg:nom.acc.voc:n', 'godło')

    uni.is_unified(sing1a, equiv, False)
    uni.is_unified(sing1b, equiv, True)
    assert uni.is_unified(sing2, equiv, True) is True
    assert java_array(uni.get_final_unified()) == \
        '[osobiste[osobisty/adj:sg:nom.acc.voc:n:pos:aff*], godło[godło/subst:sg:nom.acc.voc:n*]]'
    uni.reset()

    # now test a case when the last reading doesn't match at all
    sing1a = AT('osobiste', 'adj:pl:nom.acc.voc:f.n.m2.m3:pos:aff', 'osobisty')
    sing1b = AT('osobiste', 'adj:sg:nom.acc.voc:n:pos:aff', 'osobisty')
    sing2a = AT('godło', 'subst:sg:nom.acc.voc:n', 'godło')
    sing2b = AT('godło', 'indecl', 'godło')

    uni.is_unified(sing1a, equiv, False)
    uni.is_unified(sing1b, equiv, True)
    uni.is_unified(sing2a, equiv, False)
    assert uni.is_unified(sing2b, equiv, True) is True
    assert java_array(uni.get_final_unified()) == \
        '[osobiste[osobisty/adj:sg:nom.acc.voc:n:pos:aff*], godło[godło/subst:sg:nom.acc.voc:n*]]'
    uni.reset()

    # check if two features are left out correctly (both match)
    plur1 = AT('zgarbieni', 'adj:pl:foobar:m', 'zgarbiony')
    plur2 = AT('zgarbieni', 'adj:pl:blabla:m', 'zgarbiony')
    plur3 = AT('ludzie', 'subst:pl:blabla:m', 'człowiek')
    plur4 = AT('ludzie', 'subst:pl:pampam:m', 'człowiek')

    uni.is_unified(plur1, equiv, False)
    uni.is_unified(plur2, equiv, True)
    uni.is_unified(plur3, equiv, False)
    assert uni.is_unified(plur4, equiv, True)
    assert java_array(uni.get_final_unified()) == (
        '[zgarbieni[zgarbiony/adj:pl:foobar:m*,zgarbiony/adj:pl:blabla:m*], '
        'ludzie[człowiek/subst:pl:blabla:m*,człowiek/subst:pl:pampam:m*]]')

    # check with a sequence of many tokens
    uni.reset()

    case1a = AT('xx', 'abc:sg:f', 'xx')
    case1b = AT('xx', 'cde:pl:f', 'xx')
    case2a = AT('yy', 'abc:pl:f', 'yy')
    case2b = AT('yy', 'cde:as:f', 'yy')
    case2c = AT('yy', 'cde:pl:c', 'yy')
    case2d = AT('yy', 'abc:sg:f', 'yy')
    case2e = AT('yy', 'efg:aa:e', 'yy')

    uni.is_unified(case1a, equiv, False)
    uni.is_unified(case1b, equiv, True)
    uni.is_unified(case2a, equiv, False)
    uni.is_unified(case2b, equiv, False)
    uni.is_unified(case2c, equiv, False)
    uni.is_unified(case2d, equiv, False)
    assert uni.is_unified(case2e, equiv, True)
    assert java_array(uni.get_final_unified()) == '[xx[xx/abc:sg:f*,xx/cde:pl:f*], yy[yy/abc:pl:f*,yy/abc:sg:f*]]'

    uni.reset()

    tc1_1 = AT('xx', 'abc:sg:f', 'xx1')
    tc1_2 = AT('xx', 'cde:pl:f', 'xx2')
    tc2_1 = AT('yy', 'abc:sg:f', 'yy1')
    tc2_2 = AT('yy', 'cde:pl:f', 'yy2')
    tc3 = AT('zz', 'cde:sg:f', 'zz')

    uni.is_unified(tc1_1, equiv, False)
    uni.is_unified(tc1_2, equiv, True)
    uni.is_unified(tc2_1, equiv, False)
    uni.is_unified(tc2_2, equiv, True)

    # both readings of tokenComplex1 and tokenComplex2 should be here:
    assert java_array(uni.get_final_unified()) == \
        '[xx[xx1/abc:sg:f*,xx2/cde:pl:f*], yy[yy1/abc:sg:f*,yy2/cde:pl:f*]]'

    assert uni.is_unified(tc3, equiv, True)

    # only one reading of tokenComplex1 and tokenComplex2 - as only one agrees with tokenComplex3
    assert java_array(uni.get_final_unified()) == '[xx[xx1/abc:sg:f*], yy[yy1/abc:sg:f*], zz[zz/cde:sg:f*]]'


def test_multiple_feats_with_multiple_types():
    cfg = UnifierConfiguration()
    cfg.set_equivalence('number', 'singular', prepare_pos_element('.*[\\.:]sg:.*'))
    cfg.set_equivalence('number', 'plural', prepare_pos_element('.*[\\.:]pl:.*'))

    cfg.set_equivalence('gender', 'feminine', prepare_pos_element('.*[\\.:]f([\\.:].*)?'))
    cfg.set_equivalence('gender', 'masculine', prepare_pos_element('.*[\\.:]m1([\\.:].*)?'))
    cfg.set_equivalence('gender', 'masculine', prepare_pos_element('.*[\\.:]m2([\\.:].*)?'))
    cfg.set_equivalence('gender', 'masculine', prepare_pos_element('.*[\\.:]m3([\\.:].*)?'))
    cfg.set_equivalence('gender', 'neutral1', prepare_pos_element('.*[\\.:]n1(?:[\\.:].*)?'))
    cfg.set_equivalence('gender', 'neutral2', prepare_pos_element('.*[\\.:]n2(?:[\\.:].*)?'))

    cfg.set_equivalence('case', 'nominativus', prepare_pos_element('.*[\\.:]nom[\\.:]?.*'))
    cfg.set_equivalence('case', 'accusativus', prepare_pos_element('.*[\\.:]acc[\\.:]?.*'))
    cfg.set_equivalence('case', 'dativus', prepare_pos_element('.*[\\.:]dat[\\.:]?.*'))
    cfg.set_equivalence('case', 'vocativus', prepare_pos_element('.*[\\.:]voc[\\.:]?.*'))

    uni = cfg.create_unifier()

    sing1 = AT('niezgorsze', 'adj:sg:acc:n1.n2:pos', 'niezgorszy')
    sing1a = AT('niezgorsze', 'adj:pl:acc:m2.m3.f.n1.n2.p2.p3:pos', 'niezgorszy')
    sing1b = AT('niezgorsze', 'adj:pl:nom.voc:m2.m3.f.n1.n2.p2.p3:pos', 'niezgorszy')
    sing1c = AT('niezgorsze', 'adj:sg:nom.voc:n1.n2:pos', 'niezgorszy')
    sing2 = AT('lekarstwo', 'subst:sg:acc:n2', 'lekarstwo')
    sing2b = AT('lekarstwo', 'subst:sg:nom:n2', 'lekarstwo')
    sing2c = AT('lekarstwo', 'subst:sg:voc:n2', 'lekarstwo')

    equiv = {'number': None, 'gender': None, 'case': None}

    # now test the simplified interface
    uni.is_unified(sing1, equiv, False)
    uni.is_unified(sing1a, equiv, False)
    uni.is_unified(sing1b, equiv, False)
    uni.is_unified(sing1c, equiv, True)
    uni.is_unified(sing2, equiv, False)
    uni.is_unified(sing2b, equiv, False)
    assert uni.is_unified(sing2c, equiv, True) is True
    assert java_array(uni.get_unified_tokens()) == (
        '[niezgorsze[niezgorszy/adj:sg:acc:n1.n2:pos*,niezgorszy/adj:sg:nom.voc:n1.n2:pos*], '
        'lekarstwo[lekarstwo/subst:sg:acc:n2*,lekarstwo/subst:sg:nom:n2*,lekarstwo/subst:sg:voc:n2*]]')
    uni.reset()

    # test in a different order
    uni.is_unified(sing1a, equiv, False)
    uni.is_unified(sing1, equiv, False)
    uni.is_unified(sing1c, equiv, False)
    uni.is_unified(sing1b, equiv, True)
    uni.is_unified(sing2b, equiv, False)
    uni.is_unified(sing2c, equiv, False)
    assert uni.is_unified(sing2, equiv, True) is True
    assert java_array(uni.get_unified_tokens()) == (
        '[niezgorsze[niezgorszy/adj:sg:acc:n1.n2:pos*,niezgorszy/adj:sg:nom.voc:n1.n2:pos*], '
        'lekarstwo[lekarstwo/subst:sg:nom:n2*,lekarstwo/subst:sg:voc:n2*,lekarstwo/subst:sg:acc:n2*]]')
    uni.reset()


def test_negation():
    cfg = UnifierConfiguration()
    cfg.set_equivalence('number', 'singular', prepare_pos_element('.*[\\.:]sg:.*'))
    cfg.set_equivalence('number', 'plural', prepare_pos_element('.*[\\.:]pl:.*'))
    cfg.set_equivalence('gender', 'feminine', prepare_pos_element('.*:f'))
    cfg.set_equivalence('gender', 'masculine', prepare_pos_element('.*:m'))

    uni = cfg.create_unifier()

    # Latin adjectives
    sing_masc = AT('parvus', 'adj:sg:blahblah:m', 'parvus')
    plur_masc = AT('parvi', 'adj:sg:blahblah:m', 'parvus')
    plur_fem = AT('parvae', 'adj:pl:blahblah:f', 'parvus')
    sing_fem = AT('parva', 'adj:sg:blahblah:f', 'parvus')

    # Let's pretend Latin has determiners
    det_sing_fem = AT('una', 'det:sg:blahblah:f', 'unus')
    det_plur_fem = AT('unae', 'det:pl:blahblah:f', 'unus')
    det_sing_masc = AT('unus', 'det:sg:blahblah:m', 'unus')
    det_plur_masc = AT('uni', 'det:sg:blahblah:m', 'unus')

    # and nouns
    subst_sing_fem = AT('discrepatio', 'subst:sg:blahblah:f', 'discrepatio')
    subst_plur_fem = AT('discrepationes', 'subst:sg:blahblah:f', 'discrepatio')
    subst_sing_masc = AT('homo', 'sg:sg:blahblah:m', 'homo')
    subst_plur_masc = AT('homines', 'sg:sg:blahblah:m', 'homo')

    equiv = {'number': None, 'gender': None}

    satisfied = uni.is_satisfied(det_sing_masc, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing_masc, equiv)
    uni.start_next_token()
    satisfied &= uni.is_satisfied(subst_sing_masc, equiv)
    uni.start_next_token()
    satisfied &= uni.get_final_unification_value(equiv)
    assert satisfied is True
    uni.reset()

    # now test the simplified interface
    uni.is_unified(det_sing_masc, equiv, True)
    uni.is_unified(sing_masc, equiv, True)
    assert uni.is_unified(subst_sing_masc, equiv, True) is True
    uni.reset()

    # now let's negate this
    # traditional way
    satisfied = uni.is_satisfied(det_sing_masc, equiv)
    uni.start_unify()
    satisfied &= uni.is_satisfied(sing_masc, equiv)
    uni.start_next_token()
    satisfied &= uni.is_satisfied(subst_sing_masc, equiv)
    uni.start_next_token()
    satisfied &= uni.get_final_unification_value(equiv)
    assert (not satisfied) is False
    uni.reset()

    # now test the simplified interface
    uni.is_unified(det_sing_masc, equiv, True)
    uni.is_unified(sing_masc, equiv, True)
    assert (not uni.is_unified(subst_sing_masc, equiv, True)) is False
    uni.reset()

    for first, second, third in [
        (det_sing_fem, sing_masc, subst_sing_masc),   # not correct
        (det_sing_masc, sing_fem, subst_sing_masc),   # not correct
        (det_sing_masc, sing_masc, subst_sing_fem),   # second token does not match
        (det_sing_masc, plur_masc, subst_sing_fem),
        (det_sing_masc, plur_fem, subst_sing_fem),
        (det_plur_fem, plur_fem, subst_sing_fem),
        (det_sing_fem, plur_fem, subst_plur_fem),
        (det_sing_fem, plur_fem, subst_plur_masc),
        (det_plur_masc, plur_fem, subst_plur_masc),
    ]:
        uni.is_unified(first, equiv, True)
        uni.is_unified(second, equiv, True)
        assert (not uni.is_unified(third, equiv, True)) is True, (first, second, third)
        uni.reset()


def test_add_neutral_element():
    cfg = UnifierConfiguration()
    cfg.set_equivalence('number', 'singular', prepare_pos_element('.*[\\.:]sg:.*'))
    cfg.set_equivalence('number', 'plural', prepare_pos_element('.*[\\.:]pl:.*'))
    cfg.set_equivalence('gender', 'feminine', prepare_pos_element('.*[\\.:]f([\\.:].*)?'))
    cfg.set_equivalence('gender', 'masculine', prepare_pos_element('.*[\\.:]m([\\.:].*)?'))
    cfg.set_equivalence('gender', 'neutral', prepare_pos_element('.*[\\.:]n([\\.:].*)?'))

    uni = cfg.create_unifier()

    equiv = {'number': None, 'gender': None}

    sing1a = AT('osobiste', 'adj:pl:nom.acc.voc:f.n.m2.m3:pos:aff', 'osobisty')
    sing1b = AT('osobiste', 'adj:sg:nom.acc.voc:n:pos:aff', 'osobisty')
    sing2 = AT('godło', 'subst:sg:nom.acc.voc:n', 'godło')
    comma = AT(',', 'comma', ',')

    uni.is_unified(sing1a, equiv, False)
    uni.is_unified(sing1b, equiv, True)
    uni.add_neutral_element(AnalyzedTokenReadings(comma, 0))
    assert uni.is_unified(sing2, equiv, True) is True
    assert java_array(uni.get_final_unified()) == \
        '[osobiste[osobisty/adj:sg:nom.acc.voc:n:pos:aff*], ,[,/comma*], godło[godło/subst:sg:nom.acc.voc:n*]]'
    uni.reset()
