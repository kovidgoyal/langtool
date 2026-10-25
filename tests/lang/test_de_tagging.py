"""Port of org.languagetool.tagging.de.GermanTaggerTest,
SwissGermanTaggerTest, GermanDisambiguationTest and
org.languagetool.rules.de.GermanHelperTest."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.lang.de import german_helper
from langtool.lang.de.german_token import POSType
from langtool.lang.de.tagging import GermanTagger, SwissGermanTagger, VerbPrefixes, get_german_tagger
from langtool.tool import JLanguageTool


@pytest.fixture(autouse=True, scope='module')
def _dicts():
    require_dictionaries('de')


@pytest.fixture(scope='module')
def tagger():
    return GermanTagger(get_language('de-DE'))


def to_sorted_string(token_readings):
    """GermanTaggerTest.toSortedString: like toString(), but the readings
    are sorted alphabetically (TreeSet of AnalyzedToken.toString())"""
    elements = sorted({'%s/%s' % (r.lemma_or_token, 'null' if r.pos_tag is None else r.pos_tag)
                       for r in token_readings.readings}, key=lambda s: s.encode('utf-16-be'))
    return token_readings.token + '[' + ', '.join(elements) + ']'


def _str(readings):
    # List<AnalyzedTokenReadings>.toString() (Python prints None for null)
    return '[' + ', '.join(str(r) for r in readings) + ']'


# --- GermanTaggerTest ---

def test_adjectives_from_spelling_txt(tagger):
    """GermanTaggerTest.testAdjectivesFromSpellingTxt"""
    assert to_sorted_string(tagger.lookup('abgemindert')) == 'abgemindert[abgemindert/PA2:PRD:GRU:VER]'
    assert to_sorted_string(tagger.lookup('abgemindertes')) == (
        'abgemindertes[abgemindert/PA2:AKK:SIN:NEU:GRU:IND:VER, '
        'abgemindert/PA2:AKK:SIN:NEU:GRU:SOL:VER, abgemindert/PA2:NOM:SIN:NEU:GRU:IND:VER, '
        'abgemindert/PA2:NOM:SIN:NEU:GRU:SOL:VER]')
    assert tagger.lookup('fünftjüngste') is None  # skipped to avoid false tagging that misses comparative
    assert to_sorted_string(tagger.lookup('meistgewünschtes')) == (
        'meistgewünschtes[meistgewünscht/ADJ:AKK:SIN:NEU:GRU:IND, meistgewünscht/ADJ:AKK:SIN:NEU:GRU:SOL, '
        'meistgewünscht/ADJ:NOM:SIN:NEU:GRU:IND, meistgewünscht/ADJ:NOM:SIN:NEU:GRU:SOL]')
    assert to_sorted_string(tagger.lookup('meistgewünschter')) == (
        'meistgewünschter[meistgewünscht/ADJ:DAT:SIN:FEM:GRU:SOL, meistgewünscht/ADJ:GEN:PLU:FEM:GRU:SOL, '
        'meistgewünscht/ADJ:GEN:PLU:MAS:GRU:SOL, meistgewünscht/ADJ:GEN:PLU:NEU:GRU:SOL, '
        'meistgewünscht/ADJ:GEN:SIN:FEM:GRU:SOL, meistgewünscht/ADJ:NOM:SIN:MAS:GRU:IND, '
        'meistgewünscht/ADJ:NOM:SIN:MAS:GRU:SOL]')
    assert to_sorted_string(tagger.lookup('meistgewünscht')) == 'meistgewünscht[meistgewünscht/ADJ:PRD:GRU]'


def test_lemma_of_for_dash_compounds(tagger):
    """GermanTaggerTest.testLemmaOfForDashCompounds"""
    a_token = tagger.lookup('Zahn-Arzt-Verband')
    assert 'Zahnarztverband' in [r.lemma for r in a_token.readings]


def test_gender_gap(tagger):
    """GermanTaggerTest.testGenderGap"""
    # https://github.com/languagetool-org/languagetool/issues/2417
    assert tagger.tag(['viele', 'Freund', '*', 'innen'])[1].has_partial_pos_tag(':PLU:FEM')
    assert tagger.tag(['viele', 'Freund', '_', 'innen'])[1].has_partial_pos_tag(':PLU:FEM')
    assert tagger.tag(['viele', 'Freund', ':', 'innen'])[1].has_partial_pos_tag(':PLU:FEM')
    assert tagger.tag(['viele', 'Freund', '/', 'innen'])[1].has_partial_pos_tag(':PLU:FEM')
    tokens = ['jede', '*', 'r', 'Mitarbeiter', '*', 'in']
    assert tagger.tag(tokens)[0].has_partial_pos_tag('PRO:IND:NOM:SIN:FEM')
    assert tagger.tag(tokens)[0].has_partial_pos_tag('PRO:IND:NOM:SIN:MAS')
    assert tagger.tag(tokens)[3].has_partial_pos_tag('SUB:NOM:SIN:FEM')
    assert tagger.tag(tokens)[3].has_partial_pos_tag('SUB:NOM:SIN:MAS')


def test_ignore_domain(tagger):
    """GermanTaggerTest.testIgnoreDomain"""
    assert not tagger.tag(['bundestag', '.', 'de'])[0].is_tagged()


def test_ignore_imperative(tagger):
    """GermanTaggerTest.testIgnoreImperative"""
    assert not tagger.tag(['zehnfach'])[0].is_tagged()


def test_tagger(tagger):
    """GermanTaggerTest.testTagger"""
    a_token = tagger.lookup('Haus')
    assert to_sorted_string(a_token) == 'Haus[Haus/SUB:AKK:SIN:NEU, Haus/SUB:DAT:SIN:NEU, Haus/SUB:NOM:SIN:NEU]'
    assert [r.lemma for r in a_token.readings[:3]] == ['Haus', 'Haus', 'Haus']

    a_token2 = tagger.lookup('Hauses')
    assert to_sorted_string(a_token2) == 'Hauses[Haus/SUB:GEN:SIN:NEU]'
    assert a_token2.readings[0].lemma == 'Haus'

    assert tagger.lookup('hauses') is None
    assert tagger.lookup('Groß') is None

    assert to_sorted_string(tagger.lookup('Lieblingsbuchstabe')) == \
        'Lieblingsbuchstabe[Lieblingsbuchstabe/SUB:NOM:SIN:MAS]'

    a_token3 = tagger.lookup('großer')
    assert to_sorted_string(tagger.lookup('großer')) == (
        'großer[groß/ADJ:DAT:SIN:FEM:GRU:SOL, groß/ADJ:GEN:PLU:FEM:GRU:SOL, groß/ADJ:GEN:PLU:MAS:GRU:SOL, '
        'groß/ADJ:GEN:PLU:NEU:GRU:SOL, groß/ADJ:GEN:SIN:FEM:GRU:SOL, groß/ADJ:NOM:SIN:MAS:GRU:IND, '
        'groß/ADJ:NOM:SIN:MAS:GRU:SOL]')
    assert a_token3.readings[0].lemma == 'groß'

    # checks for github issue #635: Some German verbs on the beginning of a sentences are identified only as
    # substantive
    assert 'VER' in _str(tagger.tag(['Haben'], True))
    assert 'VER' in _str(tagger.tag(['Können'], True))
    assert 'ADJ' in _str(tagger.tag(['Gerade'], True))

    # from both german.dict and added.txt:
    a_token4 = tagger.lookup('Interessen')
    assert to_sorted_string(a_token4) == (
        'Interessen[Interesse/SUB:AKK:PLU:NEU, Interesse/SUB:DAT:PLU:NEU, '
        'Interesse/SUB:GEN:PLU:NEU, Interesse/SUB:NOM:PLU:NEU]')
    assert [r.lemma for r in a_token4.readings[:4]] == ['Interesse'] * 4

    # words that are not in the dictionary but that are recognized thanks to noun splitting:
    a_token5 = tagger.lookup('Donaudampfschiff')
    assert to_sorted_string(a_token5) == (
        'Donaudampfschiff[Donaudampfschiff/SUB:AKK:SIN:NEU, Donaudampfschiff/SUB:DAT:SIN:NEU, '
        'Donaudampfschiff/SUB:NOM:SIN:NEU]')
    assert a_token5.readings[0].lemma == 'Donaudampfschiff'
    assert a_token5.readings[1].lemma == 'Donaudampfschiff'

    a_token6 = tagger.lookup('Häuserkämpfe')
    assert to_sorted_string(a_token6) == \
        'Häuserkämpfe[Häuserkampf/SUB:AKK:PLU:MAS, Häuserkampf/SUB:GEN:PLU:MAS, Häuserkampf/SUB:NOM:PLU:MAS]'
    assert [r.lemma for r in a_token6.readings[:3]] == ['Häuserkampf'] * 3

    a_token7 = tagger.lookup('Häuserkampfes')
    assert to_sorted_string(a_token7) == 'Häuserkampfes[Häuserkampf/SUB:GEN:SIN:MAS]'
    assert a_token7.readings[0].lemma == 'Häuserkampf'

    a_token8 = tagger.lookup('Häuserkampfs')
    assert to_sorted_string(a_token8) == 'Häuserkampfs[Häuserkampf/SUB:GEN:SIN:MAS]'
    assert a_token8.readings[0].lemma == 'Häuserkampf'

    a_token9 = tagger.lookup('Lieblingsfarben')
    assert to_sorted_string(a_token9) == (
        'Lieblingsfarben[Lieblingsfarbe/SUB:AKK:PLU:FEM, Lieblingsfarbe/SUB:DAT:PLU:FEM, '
        'Lieblingsfarbe/SUB:GEN:PLU:FEM, Lieblingsfarbe/SUB:NOM:PLU:FEM]')
    assert a_token9.readings[0].lemma == 'Lieblingsfarbe'

    a_token10 = tagger.lookup('Autolieblingsfarben')
    assert to_sorted_string(a_token10) == (
        'Autolieblingsfarben[Autolieblingsfarbe/SUB:AKK:PLU:FEM, Autolieblingsfarbe/SUB:DAT:PLU:FEM, '
        'Autolieblingsfarbe/SUB:GEN:PLU:FEM, Autolieblingsfarbe/SUB:NOM:PLU:FEM]')
    assert a_token10.readings[0].lemma == 'Autolieblingsfarbe'

    a_token11 = tagger.lookup('übrigbleibst')
    assert to_sorted_string(a_token11) == 'übrigbleibst[übrigbleiben/VER:2:SIN:PRÄ:NON:NEB]'
    assert a_token11.readings[0].lemma == 'übrigbleiben'

    a_token12 = tagger.lookup('IT-Dienstleistungsunternehmen')
    assert a_token12.readings[0].pos_tag.startswith('SUB')
    assert a_token12.readings[0].lemma == 'IT-Dienstleistungsunternehmen'

    a_token13 = tagger.lookup('Entweder-oder')
    assert a_token13.readings[0].pos_tag.startswith('SUB')
    assert a_token13.readings[0].lemma == 'Entweder-oder'

    a_token14 = tagger.lookup('Verletzter')
    assert a_token14.readings[0].pos_tag == 'SUB:NOM:SIN:MAS:ADJ'
    assert a_token14.readings[0].lemma == 'Verletzter'
    assert a_token14.readings[1].pos_tag == 'SUB:GEN:PLU:MAS:ADJ'

    assert tagger.lookup('erzkatholisch').readings[0].pos_tag == 'ADJ:PRD:GRU'
    assert tagger.lookup('unerbeten').readings[0].pos_tag == 'PA2:PRD:GRU:VER'
    assert tagger.lookup('under') is None

    # tag old forms
    assert to_sorted_string(tagger.lookup('Zuge')) == 'Zuge[Zug/SUB:DAT:SIN:MAS]'
    assert to_sorted_string(tagger.lookup('Tische')) == \
        'Tische[Tisch/SUB:AKK:PLU:MAS, Tisch/SUB:DAT:SIN:MAS, Tisch/SUB:GEN:PLU:MAS, Tisch/SUB:NOM:PLU:MAS]'

    assert tagger.lookup('vanillig-karamelligen') is None

    assert to_sorted_string(tagger.lookup('Polizeimitarbeitende')) == (
        'Polizeimitarbeitende[Polizeimitarbeitende/SUB:AKK:SIN:FEM:ADJ, Polizeimitarbeitende/SUB:AKK:SIN:NEU:ADJ, '
        'Polizeimitarbeitende/SUB:NOM:SIN:FEM:ADJ, Polizeimitarbeitende/SUB:NOM:SIN:MAS:ADJ, '
        'Polizeimitarbeitende/SUB:NOM:SIN:NEU:ADJ]')
    assert to_sorted_string(tagger.lookup('Polizeimitarbeitenden')) == (
        'Polizeimitarbeitenden[Polizeimitarbeitende/SUB:AKK:PLU:FEM:ADJ, Polizeimitarbeitende/SUB:AKK:PLU:MAS:ADJ, '
        'Polizeimitarbeitende/SUB:AKK:PLU:NEU:ADJ, Polizeimitarbeitende/SUB:AKK:SIN:MAS:ADJ, '
        'Polizeimitarbeitende/SUB:DAT:PLU:FEM:ADJ, '
        'Polizeimitarbeitende/SUB:DAT:PLU:MAS:ADJ, Polizeimitarbeitende/SUB:DAT:PLU:NEU:ADJ, '
        'Polizeimitarbeitende/SUB:DAT:SIN:FEM:ADJ, '
        'Polizeimitarbeitende/SUB:DAT:SIN:MAS:ADJ, Polizeimitarbeitende/SUB:DAT:SIN:NEU:ADJ, '
        'Polizeimitarbeitende/SUB:GEN:PLU:FEM:ADJ, '
        'Polizeimitarbeitende/SUB:GEN:PLU:MAS:ADJ, Polizeimitarbeitende/SUB:GEN:PLU:NEU:ADJ, '
        'Polizeimitarbeitende/SUB:GEN:SIN:FEM:ADJ, '
        'Polizeimitarbeitende/SUB:GEN:SIN:MAS:ADJ, Polizeimitarbeitende/SUB:GEN:SIN:NEU:ADJ, '
        'Polizeimitarbeitende/SUB:NOM:PLU:FEM:ADJ, '
        'Polizeimitarbeitende/SUB:NOM:PLU:MAS:ADJ, Polizeimitarbeitende/SUB:NOM:PLU:NEU:ADJ]')


def test_extended_tagger(tagger):
    """GermanTaggerTest.testExtendedTagger: make sure we use the version of
    the POS data that was extended with post spelling reform data"""
    assert to_sorted_string(tagger.lookup('Kuß')) == 'Kuß[Kuß/SUB:AKK:SIN:MAS, Kuß/SUB:DAT:SIN:MAS, Kuß/SUB:NOM:SIN:MAS]'
    assert to_sorted_string(tagger.lookup('Kuss')) == \
        'Kuss[Kuss/SUB:AKK:SIN:MAS, Kuss/SUB:DAT:SIN:MAS, Kuss/SUB:NOM:SIN:MAS]'
    assert to_sorted_string(tagger.lookup('Haß')) == 'Haß[Haß/SUB:AKK:SIN:MAS, Haß/SUB:DAT:SIN:MAS, Haß/SUB:NOM:SIN:MAS]'
    assert to_sorted_string(tagger.lookup('Hass')) == \
        'Hass[Hass/SUB:AKK:SIN:MAS, Hass/SUB:DAT:SIN:MAS, Hass/SUB:NOM:SIN:MAS]'


def test_after_colon(tagger):
    """GermanTaggerTest.testAfterColon"""
    # a colon doesn't start a new sentence in LT, but often it should, so we check the special case for that
    tags = tagger.tag(['Er', 'sagte', ':', 'Als', 'Erstes', 'würde', 'ich'])
    assert len(tags) == 7
    assert tags[3].token == 'Als'
    assert len(tags[3].readings) == 4


def test_tagger_baseforms(tagger):
    """GermanTaggerTest.testTaggerBaseforms"""
    readings1 = tagger.lookup('übrigbleibst').readings
    assert len(readings1) == 1
    assert readings1[0].lemma == 'übrigbleiben'
    readings2 = tagger.lookup('Haus').readings
    assert [r.lemma for r in readings2] == ['Haus'] * 3
    readings3 = tagger.lookup('Häuser').readings
    assert [r.lemma for r in readings3] == ['Haus'] * 3


def test_tag(tagger):
    """GermanTaggerTest.testTag"""
    assert _str(tagger.tag(['Das'], False)) == '[Das[Das/None*]]'
    assert _str(tagger.tag(['Das'], True)).startswith('[Das[der/ART:')


def test_tag_with_manual_dict_extension(tagger):
    """GermanTaggerTest.testTagWithManualDictExtension"""
    # words not originally in Morphy but added in LT 1.8 (moved from added.txt to german.dict)
    assert _str(tagger.tag(['Wichtigtuerinnen'])) == (
        '[Wichtigtuerinnen[Wichtigtuerin/SUB:AKK:PLU:FEM*,'
        'Wichtigtuerin/SUB:DAT:PLU:FEM*,Wichtigtuerin/SUB:GEN:PLU:FEM*,Wichtigtuerin/SUB:NOM:PLU:FEM*]]')


def test_dictionary():
    """GermanTaggerTest.testDictionary (Java only prints warnings for words
    without POS tag; here: the dictionary can be read and has tags)"""
    d = get_language('de-DE').dictionary('de/german.dict')
    assert d.lookup('Haus')
    assert all(tag for _, tag in d.lookup('Haus'))


def test_is_weise_exception(tagger):
    """GermanTaggerTest.testIsWeiseException"""
    for w in ('überweise', 'verweise', 'eimerweise', 'meterweise', 'literweise', 'blätterweise', 'erweise'):
        assert not tagger.is_weise_exception(w), w
    assert tagger.is_weise_exception('lustigerweise')
    assert tagger.is_weise_exception('idealerweise')


def _check(tagger, word, size, contains=(), not_contains=()):
    result = tagger.tag([word])
    assert len(result) == 1
    assert len(result[0].readings) == size, str(result)
    res = _str(result)
    for c in contains:
        assert c in res, (c, res)
    for c in not_contains:
        assert c not in res, (c, res)


def test_prefix_verbs_from_spelling_txt(tagger):
    """GermanTaggerTest.testPrefixVerbsFromSpellingTxt"""
    _check(tagger, 'herausfallen', 5,
           ['herausfallen/VER:1:PLU:KJ1:NON:NEB*', 'herausfallen/VER:1:PLU:PRÄ:NON:NEB*',
            'herausfallen/VER:3:PLU:KJ1:NON:NEB*', 'herausfallen/VER:3:PLU:PRÄ:NON:NEB*', 'herausfallen/VER:INF:NON*'],
           ['ADJ:', 'PA1:', 'PA2:'])
    _check(tagger, 'herumgeben', 5,
           ['herumgeben/VER:1:PLU:KJ1:NON:NEB*', 'herumgeben/VER:1:PLU:PRÄ:NON:NEB*',
            'herumgeben/VER:3:PLU:KJ1:NON:NEB*', 'herumgeben/VER:3:PLU:PRÄ:NON:NEB*', 'herumgeben/VER:INF:NON*'],
           ['ADJ:', 'PA1:', 'PA2:'])
    _check(tagger, 'herumgab', 2, ['herumgeben/VER:1:SIN:PRT:NON:NEB*', 'herumgeben/VER:3:SIN:PRT:NON:NEB*'],
           ['ADJ:'])
    _check(tagger, 'zurückgeschickt', 2, ['zurückschicken/VER:PA2:SFT*', 'PA2:PRD:GRU:VER*'], ['ADJ:'])
    _check(tagger, 'abzuschicken', 1, ['abschicken/VER:EIZ:SFT'], ['ADJ:'])
    _check(tagger, 'reinzunehmen', 1, ['reinnehmen/VER:EIZ:NON'], ['ADJ:'])
    _check(tagger, 'Mitmanagen', 3,
           ['Mitmanagen/SUB:NOM:SIN:NEU:INF', 'Mitmanagen/SUB:AKK:SIN:NEU:INF', 'Mitmanagen/SUB:DAT:SIN:NEU:INF'],
           ['ADJ:'])
    _check(tagger, 'Mitmanagens', 1, ['Mitmanagen/SUB:GEN:SIN:NEU:INF'], ['ADJ:'])
    _check(tagger, 'Wegstrecken', 7, [], ['Wegstrecken/SUB:GEN:SIN:NEU:INF'])


def test_prefix_verbs_separable(tagger):
    """GermanTaggerTest.testPrefixVerbsSeparable"""
    _check(tagger, 'nachguckst', 1, ['nachgucken/VER:2:SIN:PRÄ:SFT:NEB'], ['ADJ:', 'PA1:', 'PA2:'])
    _check(tagger, 'nachgucke', 4,
           ['nachgucken/VER:1:SIN:PRÄ:SFT:NEB*', 'nachgucken/VER:1:SIN:KJ1:SFT:NEB*',
            'nachgucken/VER:3:SIN:KJ1:SFT:NEB*'],
           ['nachgucken/VER:1:SIN:PRÄ:SFT*', 'nachgucken/VER:1:SIN:KJ1:SFT*', 'nachgucken/VER:3:SIN:KJ1:SFT*',
            'nachgucken/VER:IMP:SIN:SFT*', 'nachgucken/VER:IMP:SIN:SFT:NEB*', 'ADJ:', 'PA1:', 'PA2:'])
    _check(tagger, 'nachzugucken', 1, ['nachgucken/VER:EIZ:SFT*'],
           ['nachgucken/VER:INF:SFT*', 'nachzugucken/VER:1:PLU:PRÄ:SFT*', 'nachzugucken/VER:1:PLU:KJ1:SFT*',
            'nachzugucken/VER:3:PLU:PRÄ:SFT*', 'nachzugucken/VER:3:PLU:KJ1:SFT*'])
    _check(tagger, 'nachguckend', 2, ['nachgucken/VER:PA1:SFT*', 'nachguckend/PA1:PRD:GRU:VER*'],
           ['nachgucken/VER:PA1:SFT:NEB*'])
    _check(tagger, 'nachgeguckt', 2, ['nachgucken/VER:PA2:SFT*', 'nachgeguckt/PA2:PRD:GRU:VER*'],
           ['nachgucken/VER:PA2:SFT:NEB*'])
    _check(tagger, 'Nachgucken', 3, ['Nachgucken/SUB:NOM:SIN:NEU:INF*', 'Nachgucken/SUB:DAT:SIN:NEU:INF*',
                                     'Nachgucken/SUB:AKK:SIN:NEU:INF*'])
    _check(tagger, 'Nachguckens', 1, ['Nachgucken/SUB:GEN:SIN:NEU:INF*'])
    _check(tagger, 'Nachzudenken', 1, ['nachdenken/VER:EIZ:NON*'],
           ['Nachzudenken/SUB:NOM:SIN:NEU:INF*', 'Nachzudenken/SUB:DAT:SIN:NEU:INF*',
            'Nachzudenken/SUB:AKK:SIN:NEU:INF*'])
    _check(tagger, 'entlangblicken', 5, ['entlangblicken/VER:INF:SFT*', 'NEB*'])
    _check(tagger, 'wiederaufbauen', 5, ['NEB'], ['NEB:NEB'])


def test_prefix_verbs_not_mod(tagger):
    """GermanTaggerTest.testPrefixVerbsNotMod"""
    _check(tagger, 'rauslassen', 5,
           ['rauslassen/VER:1:PLU:PRÄ:NON:NEB*', 'rauslassen/VER:1:PLU:KJ1:NON:NEB*',
            'rauslassen/VER:3:PLU:PRÄ:NON:NEB*', 'rauslassen/VER:3:PLU:KJ1:NON:NEB*', 'rauslassen/VER:INF:NON*'],
           ['rauslassen/VER:1:PLU:PRÄ:NON*', 'rauslassen/VER:1:PLU:KJ1:NON*', 'rauslassen/VER:3:PLU:PRÄ:NON*',
            'rauslassen/VER:3:PLU:KJ1:NON*', 'rauslassen/VER:MOD:1:PLU:PRÄ*', 'rauslassen/VER:MOD:1:PLU:KJ1*',
            'rauslassen/VER:MOD:3:PLU:PRÄ*', 'rauslassen/VER:MOD:3:PLU:KJ1*', 'rauslassen/VER:MOD:INF*'])
    _check(tagger, 'rauslass', 2, ['rauslassen/VER:1:SIN:PRÄ:NON:NEB*'],
           ['rauslassen/VER:IMP:SIN:NON*', 'rauslassen/VER:MOD:IMP:SIN', 'rauslassen/VER:IMP:SIN:NON:NEB*'])
    _check(tagger, 'rauszulassen', 1, ['rauslassen/VER:EIZ:NON*'])
    _check(tagger, 'rausgelassen', 2, ['rauslassen/VER:PA2:NON*', 'rausgelassen/PA2:PRD:GRU:VER*'],
           ['rauslassen/VER:MOD:PA2'])


def test_prefix_verbs_non_separable(tagger):
    """GermanTaggerTest.testPrefixVerbsNonSeparable"""
    _check(tagger, 'vergären', 15,
           ['vergären/VER:1:PLU:PRÄ:NON*', 'vergären/VER:1:PLU:KJ1:NON*', 'vergären/VER:3:PLU:PRÄ:NON*',
            'vergären/VER:3:PLU:KJ1:NON*', 'vergären/VER:INF:NON*', 'vergären/VER:1:PLU:PRÄ:SFT*',
            'vergären/VER:1:PLU:KJ1:SFT*', 'vergären/VER:3:PLU:PRÄ:SFT*', 'vergären/VER:3:PLU:KJ1:SFT*',
            'vergären/VER:INF:SFT*'])
    _check(tagger, 'Vergären', 24,
           ['Vergären/SUB:NOM:SIN:NEU:INF', 'Vergären/SUB:DAT:SIN:NEU:INF', 'Vergären/SUB:AKK:SIN:NEU:INF',
            'vergären/VER:1:PLU:PRÄ:NON*', 'vergären/VER:1:PLU:KJ1:NON*', 'vergären/VER:3:PLU:PRÄ:NON*',
            'vergären/VER:3:PLU:KJ1:NON*', 'vergären/VER:INF:SFT*', 'vergären/VER:1:PLU:PRÄ:SFT*',
            'vergären/VER:1:PLU:KJ1:SFT*', 'vergären/VER:3:PLU:PRÄ:SFT*', 'vergären/VER:3:PLU:KJ1:SFT*',
            'vergären/VER:INF:SFT*'])
    _check(tagger, 'unbeglückt', 2, ['PA2:PRD:GRU:VER'], ['VER:'])
    _check(tagger, 'erstritten', 6, ['erstreiten/VER:1:PLU:PRT:NON', 'erstreiten/VER:PA2:NON',
                                     'erstritten/PA2:PRD:GRU:VER'])
    _check(tagger, 'bemessen', 7, ['bemessen/VER:INF:NON', 'bemessen/VER:PA2:NON', 'bemessen/PA2:PRD:GRU:VER'])
    _check(tagger, 'bemisst', 8, [], ['bemessen/PA2:PRD:GRU:VER'])
    _check(tagger, 'hinterlass', 3, ['hinterlassen/VER:IMP:SIN:NON', 'hinterlassen/VER:1:SIN:PRÄ:NON'], ['NEB'])


def test_no_verb(tagger):
    """GermanTaggerTest.testNoVerb"""
    _check(tagger, 'geschichte', 1, [], ['VER'])
    _check(tagger, 'bereich', 1, [], ['VER'])
    _check(tagger, 'beispiel', 1, [], ['VER'])
    _check(tagger, 'keksdose', 1, [], ['VER'])
    _check(tagger, 'aktienarten', 1, [], ['VER'])
    _check(tagger, 'schwarzgrau', 2, ['ADJ', 'VER'])
    _check(tagger, 'unmenge', 1, [], ['VER'])
    _check(tagger, 'entlang', 4, ['PRP', 'ZUS'], ['VER'])


def test_verb_and_pa2(tagger):
    """GermanTaggerTest.testVerbAndPa2"""
    _check(tagger, 'erstickt', 5, ['ersticken/VER:2:PLU:PRÄ:SFT', 'ersticken/VER:3:SIN:PRÄ:SFT',
                                   'ersticken/VER:IMP:PLU:SFT', 'ersticken/VER:PA2:SFT', 'erstickt/PA2:PRD:GRU:VER'])
    _check(tagger, 'erstickte', 19, ['erstickt/PA2', 'ersticken/VER:1:SIN:KJ2:SFT', 'ersticken/VER:1:SIN:PRT:SFT',
                                     'ersticken/VER:3:SIN:KJ2:SFT', 'ersticken/VER:3:SIN:PRT:SFT'], ['NEB'])
    _check(tagger, 'erstickend', 2, ['ersticken/VER:PA1:SFT', 'erstickend/PA1:PRD:GRU:VER'])
    _check(tagger, 'erstickender', 7, ['erstickend/PA1:DAT:SIN:FEM:GRU:SOL:VER'])


def test_instances():
    """German.createDefaultTagger() returns GermanTagger.INSTANCE,
    SwissGerman a SwissGermanTagger"""
    assert get_language('de-DE').tagger is get_german_tagger()
    assert get_language('de-AT').tagger is get_german_tagger()
    assert isinstance(get_language('de-CH').tagger, SwissGermanTagger)


def test_verb_prefixes():
    """VerbPrefixes.get(): sorted alphabetically, then longest first"""
    prefixes = VerbPrefixes.get()
    assert prefixes[:3] == ('auseinander', 'aneinander', 'dazwischen')
    assert prefixes[-1] == 'zu'
    assert all(len(a) >= len(b) for a, b in zip(prefixes, prefixes[1:]))


# --- SwissGermanTaggerTest ---

def test_swiss_tagger(tagger):
    """SwissGermanTaggerTest.testTagger"""
    swiss_tagger = SwissGermanTagger(get_language('de-CH'))
    a_token = swiss_tagger.lookup('gross')
    assert to_sorted_string(a_token) == 'gross[groß/ADJ:PRD:GRU]'
    assert a_token.readings[0].lemma == 'groß'
    a_token2 = swiss_tagger.lookup('Anmassung')
    assert to_sorted_string(a_token2) == ('Anmassung[Anmaßung/SUB:AKK:SIN:FEM, Anmaßung/SUB:DAT:SIN:FEM, '
                                          'Anmaßung/SUB:GEN:SIN:FEM, Anmaßung/SUB:NOM:SIN:FEM]')
    assert a_token2.readings[0].lemma == 'Anmaßung'
    assert str(swiss_tagger.lookup('die')) == str(tagger.lookup('die'))
    assert str(swiss_tagger.lookup('Auto')) == str(tagger.lookup('Auto'))


# --- GermanHelperTest ---

def test_has_reading_of_type():
    """GermanHelperTest.testHasReadingOfType"""
    readings = AnalyzedTokenReadings(AnalyzedToken('der', 'ART:DEF:DAT:SIN:FEM', None), 0)
    assert german_helper.has_reading_of_type(readings, POSType.DETERMINER)
    assert not german_helper.has_reading_of_type(readings, POSType.NOMEN)


def test_get_determiner_number():
    """GermanHelperTest.testGetDeterminerNumber"""
    assert german_helper.get_determiner_number('ART:DEF:DAT:SIN:FEM') == 'SIN'


def test_get_determiner_definiteness():
    """GermanHelperTest.testGetDeterminerDefiniteness"""
    assert german_helper.get_determiner_definiteness('ART:DEF:DAT:SIN:FEM') == 'DEF'


def test_get_determiner_case():
    """GermanHelperTest.testGetDeterminerCase"""
    assert german_helper.get_determiner_case('ART:DEF:DAT:SIN:FEM') == 'DAT'


def test_get_determiner_gender():
    """GermanHelperTest.testGetDeterminerGender"""
    assert german_helper.get_determiner_gender(None) == ''
    assert german_helper.get_determiner_gender('') == ''
    assert german_helper.get_determiner_gender('ART:DEF:DAT:SIN:FEM') == 'FEM'


def test_get_comparison():
    """GermanHelper.getComparison (not covered by GermanHelperTest)"""
    assert german_helper.get_comparison('ADJ:AKK:PLU:MAS:KOM:SOL') == 'KOM'
    assert german_helper.get_comparison('PA2:PRD:GRU:VER') == 'GRU'
    assert german_helper.get_noun_case('SUB:AKK:SIN:NEU') == 'AKK'
    assert german_helper.get_noun_number('SUB:AKK:SIN:NEU') == 'SIN'
    assert german_helper.get_noun_gender('SUB:AKK:SIN:NEU') == 'NEU'


# --- GermanDisambiguationTest ---

@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('de-DE'))


def test_chunker(lt):
    """GermanDisambiguationTest.testChunker"""
    assert str(lt.analyze_text('für Ihrer Sicherheit.')) == (
        '[<S> für[für/PRP:TMP+MOD+CAU:AKK,für/PRP:TMP+MOD+CAU:AKK,PP] '
        'Ihrer[Ihr/PRO:POS:DAT:SIN:FEM:BEG,Ihr/PRO:POS:DAT:SIN:FEM:STV,Ihr/PRO:POS:GEN:SIN:FEM:BEG,'
        'Ihr/PRO:POS:GEN:SIN:FEM:STV,B-NP|NPS|PP] Sicherheit[Sicherheit/SUB:DAT:SIN:FEM,Sicherheit/SUB:GEN:SIN:FEM,'
        'I-NP|NPS|PP].[</S>./PKT,<P/>,O]]')
    # FIXME: missing tags for "Ihrer"
    assert str(lt.analyze_text('Wir entwickeln ein Konzept für Ihrer Sicherheit.')) == (
        '[<S> Wir[ich/PRO:PER:NOM:PLU:ALG,O] entwickeln[entwickeln/VER:1:PLU:KJ1:SFT,entwickeln/VER:1:PLU:PRÄ:SFT,'
        'entwickeln/VER:3:PLU:KJ1:SFT,entwickeln/VER:3:PLU:PRÄ:SFT,entwickeln/VER:INF:SFT,O] '
        'ein[ein/ART:IND:AKK:SIN:NEU,ein/ART:IND:NOM:SIN:NEU,B-NP|NPS] Konzept[Konzept/SUB:AKK:SIN:NEU,'
        'Konzept/SUB:NOM:SIN:NEU,I-NP|NPS] für[für/PRP:TMP+MOD+CAU:AKK,PP] Ihrer[Ihr/PRO:POS:DAT:SIN:FEM:BEG,'
        'Ihr/PRO:POS:DAT:SIN:FEM:STV,Ihr/PRO:POS:GEN:SIN:FEM:BEG,Ihr/PRO:POS:GEN:SIN:FEM:STV,B-NP|NPS|PP] '
        'Sicherheit[Sicherheit/SUB:DAT:SIN:FEM,Sicherheit/SUB:GEN:SIN:FEM,I-NP|NPS|PP].[</S>./PKT,<P/>,O]]')
    for text, ignored in (('3-adische System', True), ('3-adische Systeme', True), ('3-adischen Systems', True),
                          ('Kelassurier Mauer', True), ('Kelassurier Mauern', True), ('Kelassurier Mauers', False)):
        tokens = lt.analyze_text(text)[0].tokens
        assert tokens[1].ignored_by_speller is ignored, text
        assert tokens[2].ignored_by_speller is ignored, text


@pytest.mark.parametrize('sentence,expected', [
    ('Wer, wie ich, seit vielen Jahre in dieser Branche tätig ist, kennt sich damit gut aus.',
     'vielen[viel/PRO:IND:DAT:PLU:NEU:B/S,viel/PRO:IND:GEN:PLU:NEU'),
    ('Der Ort bekam eine Schule samt ansässigen Lehrer.', 'ansässig/ADJ:DAT:SIN:MAS:GRU:DEF'),
    ('Die Norm formuliert, was Unternehmen tun können und sollten, um den Qualitätsanforderungen ihrer Kunden '
     'gerecht zu werden.', 'ihr/PRO:POS:GEN:PLU:MAS:BEG'),
    ('Mit welches Verkehrsmittel fahrt ihr in die Schule?', 'welches[welch/PRO:RIN:AKK:SIN:NEU:B/S'),
    ('Er hat zu meiner Fragen nichts gesagt.', 'mein/PRO:POS:GEN:PLU:FEM:BEG'),
    ('Sie verlangen das von viele europäischen Bürgern.', 'viel/PRO:IND:AKK:PLU:MAS:B/S'),
    ('Die regelmäßigen Begegnungen junge Menschen in diesem Haus dienen der Friedensförderung.',
     'junge[jung/ADJ:AKK:PLU:MAS:GRU:SOL'),
    ('Sie hatte zwei kleiner Fragen.', 'klein/ADJ:GEN:PLU:FEM:GRU:SOL'),
    ('Die Erkennung von typischen Fehler bereitet viel Mühe.', 'typisch/ADJ:DAT:SIN:MAS:GRU:DEF'),
    ('Sie wollte nie etwas mit deinem Freunden unternehmen.', 'dein/PRO:POS:DAT:SIN:NEU:BEG'),
])
def test_unification_keeps_readings_for_potential_agreement_errors(lt, sentence, expected):
    """GermanDisambiguationTest.testUnificationKeepsReadingsForPotentialAgreementErrors"""
    analyzed = str(lt.analyze_text(sentence))
    assert expected in analyzed, analyzed
