"""Port of the tests of the Dutch rules: org.languagetool.rules.nl.
CheckCaseRuleTest, CompoundAcceptorTest, CompoundFilterTest,
CompoundRuleTest, DateCheckFilterTest (no test methods in Java),
DutchWrongWordInContextRuleTest (ignored in Java: "no tests yet"),
PreferredWordRuleTest, SimpleReplaceRuleTest, SpaceInCompoundRuleTest,
ToolsTest, WordCoherencyRuleTest, MorfologikDutchSpellerRuleTest (skipped,
spell checking), plus checks of the filters and of the core filters and
the MultitokenSpeller as used by Dutch."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.nl.filters import CompoundFilter, DateCheckFilter, DutchNumberInWordFilter
from langtool.lang.nl.multitoken import DutchMultitokenSpeller
from langtool.lang.nl.rules import (CheckCaseRule, CompoundRule, DutchWrongWordInContextRule, PreferredWordRule,
                                    SimpleReplaceRule, SpaceInCompoundRule, WordCoherencyRule, generate_variants,
                                    glue_parts)
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.multitoken import levenshtein_distance
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('nl')


@pytest.fixture(scope='module')
def dutch():
    return get_language('nl')


@pytest.fixture(scope='module')
def lt(dutch):
    return JLanguageTool(dutch)


class FakeRule(Rule):
    def get_id(self):
        return 'FAKE-RULE'

    def get_description(self):
        return 'Fake rule'


# --- CheckCaseRuleTest ---

def test_check_case_rule(dutch, lt):
    """CheckCaseRuleTest.testRule"""
    rule = CheckCaseRule(messages_for('nl'), dutch)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('een bisschop'))) == 0
    assert len(rule.match(lt.get_analyzed_sentence('Een bisschop'))) == 0
    # ignored sentence:
    assert len(rule.match(lt.get_analyzed_sentence('EEN BISSCHOP'))) == 0
    # incorrect sentences:
    matches = rule.match(lt.get_analyzed_sentence('Een Bisschop'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'Een bisschop'
    matches = rule.match(lt.get_analyzed_sentence('Hij is een Bisschop.'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'een bisschop'
    # less than 5chars:
    matches = rule.match(lt.get_analyzed_sentence('Mag ik die DVD lenen?'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'dvd'
    matches = rule.match(lt.get_analyzed_sentence('Heb je de nieuwe IPAD al gezien?'))
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'iPad'


# --- CompoundAcceptorTest ---

ACCEPTED = [
    'bedrijfsregels', 'Bedrijfsbrommer', 'straatpuzzel', 'zwangerschap', 'Papierversnipperaar', 'adresvervloeking',
    'sportagente', 'transferpersjes', 'kunstomlijning', 'webomlijning', 'webschoolboek', 'cryptodebacle',
    'bakfietsbedrijf', 'campustheater', 'tramschutter', 'zeespiegelonderzoeker', 'nepsupporters',
    'hidjabverplichting', 'faillissementspoging', 'spoedaanwijzingen', 'vaccinatieorganisaties', 'aanjaagpartij',
    # test areas
    'Zuidoost-Turkije', 'Noord-Afghanistan', 'Zuidwest-Gouda',
    # test for acronyms in compounds
    'IRA-akkoord', 'WK-finale', 'VRF-regels',
    # test for words that always need a hyphen
    'collega-burgemeester', 'aspirant-buschauffeur',
    # test for acronym exceptions
    'aidsafdeling', 'vipbehandeling', 'vipcriticus', 'vip-criticus', 'zzp-ondernemertje', 'cd-spelertje',
    'btw-toevoegingen', 'tv-poppetjes',
    # test part1 exceptions
    'belastingvrij',
    'tombeplunderaar', 'Zwangerschapsblijheid',
    # test for colliding vowels
    'privé-eigenaar', 'politie-eenheid', 'auto-uitlaat',
]
REJECTED = [
    'bedrijfregels', 'Bedrijfbrommer', 'straatspuzzel', 'zwangersschap', 'lingsboek',
    'gezondheidsomlijningssvervangingsinfluencers', 'Zuidwest-Frank', 'Papiersversnipperaar',
    # prevent duplicate part1 & part2 from being accepted
    'vriendenvrienden',
    'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'bedrijfskijkt', 'WIFI-verbinding', 'aspirantbuschauffeur',
    'AIDS-afdeling', 'VIP-behandeling', 'ZZP-ondernemertje', 'Zzp-ondernemertje', 'CD-spelertje',
    'BTW-toevoegingen', 'TV-poppetjes',
    'honingsbijtje', 'datingswebsite', 'belastingsvrij',
    # test part2 exceptions
    'mannenlijk', 'dienstvoor',
    'wetenschapbelasting',
    'privéeigenaar', 'politieeenheid', 'autouitlaat',
]


@pytest.fixture(scope='module')
def acceptor(dutch):
    return dutch.tagger.compound_acceptor


@pytest.mark.parametrize('word', ACCEPTED)
def test_accept_compound(acceptor, word):
    """CompoundAcceptorTest.testAcceptCompound (assertTrue)"""
    assert acceptor.accept_compound(word)


@pytest.mark.parametrize('word', REJECTED)
def test_reject_compound(acceptor, word):
    """CompoundAcceptorTest.testAcceptCompound (assertFalse)"""
    assert not acceptor.accept_compound(word)


def test_accept_compound_internal(acceptor):
    """CompoundAcceptorTest.testAcceptCompoundInternal (ignored in Java,
    "use for interactive debugging")"""
    assert acceptor.accept_compound('passagiers', 'schip')
    assert acceptor.accept_compound('papier', 'versnipperaar')
    assert not acceptor.accept_compound('politie', 'eenheid')
    assert acceptor.accept_compound('politie', '-eenheid')


def test_get_parts(acceptor):
    assert acceptor.get_parts('bedrijfsregels') == ['bedrijfs', 'regels']
    assert acceptor.get_parts('bedrijfregels') == []


# --- CompoundFilterTest ---

@pytest.mark.parametrize('words,expected', [
    (['tv', 'meubel'], 'tv-meubel'),
    (['test-tv', 'meubel'], 'test-tv-meubel'),
    (['onzin', 'tv'], 'onzin-tv'),
    (['auto', 'onderdeel'], 'auto-onderdeel'),
    (['test', 'e-mail'], 'test-e-mail'),
    (['taxi', 'jongen'], 'taxi-jongen'),
    (['rij', 'instructeur'], 'rijinstructeur'),
    (['ANWB', 'wagen'], 'ANWB-wagen'),
    (['pro-deo', 'advocaat'], 'pro-deoadvocaat'),
    (['ANWB', 'tv', 'wagen'], 'ANWB-tv-wagen'),
])
def test_compound_filter(words, expected):
    """CompoundFilterTest.testFilter"""
    match = RuleMatch(FakeRule(), None, 0, 10, 'message')
    args = {'word%d' % (i + 1): w for i, w in enumerate(words)}
    rule_match = CompoundFilter().accept_rule_match(match, args, -1, None, None)
    assert rule_match.suggested_replacements == [expected]


def test_compound_filter_message():
    match = RuleMatch(FakeRule(), None, 0, 10, 'Bedoelt u <suggestion>x</suggestion>?',
                      'Kort <suggestion>y</suggestion>')
    rule_match = CompoundFilter().accept_rule_match(match, {'word1': 'tv', 'word2': 'meubel'}, -1, None, None)
    assert rule_match.message == 'Bedoelt u <suggestion>tv-meubel</suggestion>?'
    assert rule_match.short_message == 'Kort <suggestion>tv-meubel</suggestion>'


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches


def test_compound_rule(dutch, lt):
    """CompoundRuleTest.testRule"""
    rule = CompoundRule(messages_for('en'), dutch, None)
    # correct sentences:
    _check(lt, rule, 0, 'Dit is een zee-egel.')
    _check(lt, rule, 0, 'Zee-egel is een woord.')
    # incorrect sentences:
    _check(lt, rule, 1, 'Dit is een zee egel.')
    _check(lt, rule, 1, 'Zee egel is een woord.')


# --- DateCheckFilterTest ---

def _date_args(year, month, day_of_month, week_day):
    return {'year': year, 'month': month, 'day': day_of_month, 'weekDay': week_day}


def test_date_check_filter(dutch, lt):
    """DateCheckFilterTest (the Java class has no test methods); checks
    the Dutch day and month names with the NL_DATE_WEEKDAY rule"""
    f = DateCheckFilter()
    assert f.get_day_of_week('Zondag') == 1
    assert f.get_day_of_week('za') == 7
    assert f.get_month('maart') == 3 and f.get_month('mrt') == 3 and f.get_month('Okt') == 10
    with pytest.raises(RuntimeError):
        f.get_month('foo')
    matches = [m for m in lt.check('Het is vrijdag 3 maart 2007.') if m.rule.get_id() == 'NL_DATE_WEEKDAY']
    assert len(matches) == 1
    assert matches[0].suggested_replacements == ['zaterdag 3', 'vrijdag 2']


# --- DutchWrongWordInContextRule ---

def test_wrong_word_in_context_rule(dutch):
    """DutchWrongWordInContextRuleTest.testRule is ignored in Java (no
    tests yet); check the rule properties"""
    rule = DutchWrongWordInContextRule(messages_for('nl'), dutch)
    assert rule.get_id() == 'DUTCH_WRONG_WORD_IN_CONTEXT'
    assert rule.category.name == 'Gemakkelijk te verwarren woorden'
    assert rule.context_words_set


# --- PreferredWordRuleTest ---

def test_preferred_word_rule(dutch, lt):
    """PreferredWordRuleTest.test"""
    rule = PreferredWordRule(messages_for('en'))
    sentence1 = lt.get_analyzed_sentence('rijwiel')
    assert len(rule.match(sentence1)) == 1
    assert rule.match(sentence1)[0].suggested_replacements == ['fiets']
    assert rule.match(sentence1)[0].rule.get_id() == 'NL_PREFERRED_WORD_RULE_INTERNAL'


# --- SimpleReplaceRuleTest ---

def _check_simple_replace_rule(rule, lt, sentence, suggestion):
    matches = rule.match(lt.get_analyzed_sentence(sentence))
    assert len(matches) == 1, 'Invalid matches.length while checking sentence: ' + sentence
    assert len(matches[0].suggested_replacements) == 1
    assert matches[0].suggested_replacements[0] == suggestion


def test_simple_replace_rule(dutch, lt):
    """SimpleReplaceRuleTest.testRule"""
    rule = SimpleReplaceRule(messages_for('nl'), dutch)
    # correct sentences:
    assert len(rule.match(lt.get_analyzed_sentence('all right'))) == 0
    # no match b/c case-sensitivity
    assert len(rule.match(lt.get_analyzed_sentence('De Kudde eigenschappen'))) == 0
    # incorrect sentences:
    _check_simple_replace_rule(rule, lt, 'klaa', 'Klaar')
    _check_simple_replace_rule(rule, lt, 'een BTW nummer', 'btw-nummer')
    _check_simple_replace_rule(rule, lt, 'kleurweergave eigenschappen.', 'Kleurweergave-eigenschappen')
    _check_simple_replace_rule(rule, lt, 'De kleurweergave eigenschappen.', 'kleurweergave-eigenschappen')


def test_simple_replace_rule_properties(dutch, lt):
    rule = SimpleReplaceRule(messages_for('nl'), dutch)
    assert rule.category.id == 'VERGISSINGEN'
    assert rule.get_description('x') == 'Snelle correctie van veel voorkomende vergissingen: x'
    m, = rule.match(lt.get_analyzed_sentence('klaa'))
    assert m.rule.get_id() == 'NL_SIMPLE_REPLACE_KLAA'


# --- SpaceInCompoundRuleTest ---

def test_space_in_compound_rule(dutch, lt):
    """SpaceInCompoundRuleTest.testRule"""
    rule = SpaceInCompoundRule(messages_for('en'), dutch)

    def count(text):
        return len(rule.match(lt.get_analyzed_sentence(text)))
    assert count('langeafstandloper') == 0
    assert count('Dat zie je nu weer met de zogenaamde oudelullendagen die in heel andere tijden met gulle hand in '
                 'cao’s werden uitgereikt aan werknemers van vijftig jaar en ouder.') == 0
    assert count('...jk aan voor de middelbare school tijdens de aanmeldw...') == 0
    assert count('...jk aan voor de middelbare school tijdens de..., lange afstand loper') == 1
    assert count('lange afstand loper') == 1
    assert count('langeafstand loper') == 1
    assert count('lange afstandloper') == 1
    m, = rule.match(lt.get_analyzed_sentence('lange afstand loper'))
    assert m.suggested_replacements == ['langeafstandloper']
    assert m.rule.get_id() == 'NL_SPACE_IN_COMPOUND_LANGE_AFSTAND_LOPER'


def test_generate_variants():
    """SpaceInCompoundRuleTest.testVariants"""
    res1 = set()
    generate_variants('', ['a', 'b'], res1)
    assert res1 == {'a b'}
    res2 = set()
    generate_variants('', ['a', 'b', 'c'], res2)
    assert res2 == {'a b c', 'ab c', 'a bc'}
    res3 = set()
    generate_variants('', ['a', 'b', 'c', 'd'], res3)
    assert res3 == {'a b c d', 'a bc d', 'ab cd', 'ab c d', 'a b cd', 'abc d', 'a bcd'}


# --- ToolsTest ---

@pytest.mark.parametrize('parts,expected', [
    (['huis', 'deur'], 'huisdeur'),
    (['tv', 'programma'], 'tv-programma'),
    (['auto2', 'deurs'], 'auto2-deurs'),
    (['zee', 'eend'], 'zee-eend'),
    (['mms', 'eend'], 'mms-eend'),
    (['EersteKlas', 'service'], 'EersteKlasservice'),
    (['3D', 'printer'], '3Dprinter'),
    (['groot', 'moeder', 'huis'], 'grootmoederhuis'),
    (['sport', 'tv', 'uitzending'], 'sport-tv-uitzending'),
    (['auto-', 'pilot'], 'auto-pilot'),
    (['foto', '5d', 'camera'], 'foto-5dcamera'),
    (['xyZ', 'xyz'], 'xyZ-xyz'),
    (['xyZ', 'Xyz'], 'xyZ-Xyz'),
    (['xyz', 'Xyz'], 'xyz-Xyz'),
    (['xxx-z', 'yyy'], 'xxx-z-yyy'),
])
def test_glue_parts(parts, expected):
    """ToolsTest.testBasicConcatenation"""
    assert glue_parts(parts) == expected


# --- WordCoherencyRuleTest ---

def test_word_coherency_rule(dutch, lt):
    """WordCoherencyRuleTest.testRule"""
    rule = WordCoherencyRule(messages_for('en'), dutch)
    assert len(rule.match(lt.analyze_text('organogram, organigram'))) == 1
    assert len(rule.match(lt.analyze_text('organogram, organogram'))) == 0


@pytest.mark.skip(reason='spell checking is not ported: MorfologikDutchSpellerRuleTest tests '
                         'MorfologikDutchSpellerRule')
def test_speller():
    """Port of MorfologikDutchSpellerRuleTest.testSpeller"""


# --- filters and the multitoken speller ---

def test_number_in_word_filter(dutch):
    """DutchNumberInWordFilter (with the misspelling check of
    MorfologikDutchSpellerRule, no spelling suggestions)"""
    f = DutchNumberInWordFilter(dutch)
    match = RuleMatch(FakeRule(), None, 0, 4, 'message')
    assert f.accept_rule_match(match, {'word': 'g0ede'}, 0, None, None).suggested_replacements == ['goede']
    assert f.accept_rule_match(match, {'word': 'xq1zz'}, 0, None, None) is None


def test_misspelling_check(dutch):
    """The misspelling check of MorfologikDutchSpellerRule (isMisspelled,
    ignoreWord, isProhibited), cases from MorfologikDutchSpellerRuleTest
    where they concern the check (not the rule)"""
    from langtool.lang.nl.spelling import MorfologikDutchSpellerCheck
    check = dutch.get_default_spelling_rule()
    assert isinstance(check, MorfologikDutchSpellerCheck)
    assert isinstance(get_language('nl-BE').get_default_spelling_rule(), MorfologikDutchSpellerCheck)
    assert check.converts_case()
    assert not check.is_misspelled('Amsterdam')
    assert not check.is_misspelled('huis')
    assert not check.is_misspelled('Huis')
    assert not check.is_misspelled('HUIS')
    assert not check.is_misspelled('doorrijbotsing')  # spelling.txt
    assert not check.is_misspelled('semi-indirect')
    assert not check.is_misspelled(' ')
    assert check.is_misspelled('gede')
    assert check.is_misspelled('foobarwrong')
    assert check.is_misspelled('FoobarWrongxx')  # camel case is not ignored (nl_NL.info)
    assert check.is_misspelled('déur')
    # in ignore.txt
    assert check.ignore_word('ipv')
    assert check.ignore_word('voorzover')
    assert check.ignore_word('ipv.')
    assert check.ignore_word('...')
    assert not check.ignore_word('huis')
    # prohibit.txt
    assert check.is_prohibited('Ajax-kampioen')
    assert not check.is_prohibited('huis')


def test_multitoken_speller(dutch):
    speller = dutch.get_multitoken_speller()
    assert isinstance(speller, DutchMultitokenSpeller)
    assert speller is dutch.get_multitoken_speller()
    assert speller.get_suggestions('britaney speers') == ['Britney Spears']
    assert speller.get_suggestions('Britney Spears') == []
    assert speller.is_exception("Britney Spears's", 'Britney Spears')
    assert not speller.is_exception('Britney Spears', 'Britney Spears')


def test_levenshtein_distance():
    assert levenshtein_distance('kitten', 'sitting') == 3
    assert levenshtein_distance('', 'abc') == 3
    assert levenshtein_distance('abc', 'abc') == 0
