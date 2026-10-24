"""Port of the rule tests of language-en: AvsAnRuleTest, CompoundRuleTest,
ConsistentApostrophesRuleTest, ContractionSpellingRuleTest,
EnglishDashRuleTest, EnglishSpecificCaseRuleTest,
EnglishUnpairedBracketsRuleTest, EnglishUnpairedQuotesRuleTest,
EnglishWordRepeatRuleTest, WordRepeatRuleTest,
EnglishWordRepeatBeginningRuleTest, EnglishWrongWordInContextRuleTest,
EnglishRepeatedWordsRuleTest, WordCoherencyRuleTest, AmericanReplaceRuleTest,
BritishReplaceRuleTest, NewZealandReplaceRuleTest, UnitConversionRuleTest,
UnitConversionRuleImperialTest, UnitConversionRuleUSTest (with
UnitConversionRuleTestHelper), UppercaseSentenceStartRuleTest,
DateCheckFilterTest and EnglishNumberInWordFilterTest, plus checks of the
other English rules and filters. The tests of the spelling rules
(MorfologikAmericanSpellerRuleTest etc., AbstractEnglishSpellerRuleTest,
SpellingCheckRuleTest, LanguageSpecificSpellcheckerTest), of the language
model rules (EnglishConfusionProbabilityRuleTest, UpperCaseNgramRuleTest),
of the remote rules (EnglishRemoteRuleFilterTest,
EnglishRemoteRuleSuppressMisspelledTest) and InflectorTest are skipped (not
ported, see the skip reasons)."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.lang.en import avsan
from langtool.lang.en.avsan import AvsAnRule, get_correct_determiner_for
from langtool.lang.en.filters import (AdverbFilter, DateCheckFilter, EnglishNumberInWordFilter, OrdinalSuffixFilter,
                                      YMDDateCheckFilter)
from langtool.lang.en.rules import (AmericanReplaceRule, BritishReplaceRule, CompoundRule, ConsistentApostrophesRule,
                                    ContractionSpellingRule, EnglishDashRule, EnglishRepeatedWordsRule,
                                    EnglishSpecificCaseRule, EnglishUnpairedBracketsRule, EnglishUnpairedQuotesRule,
                                    EnglishWordRepeatRule, EnglishWrongWordInContextRule, NewZealandReplaceRule,
                                    UnitConversionRule, UnitConversionRuleImperial, UnitConversionRuleUS,
                                    WordCoherencyRule)
from langtool.messages import messages_for
from langtool.rules.base import Rule, RuleMatch
from langtool.rules.core import WordRepeatRule
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('en')


@pytest.fixture(scope='module')
def messages():
    return messages_for('en')


@pytest.fixture(scope='module')
def lt():
    return JLanguageTool(get_language('en'))


@pytest.fixture(scope='module')
def lt_us():
    return JLanguageTool(get_language('en-US'))


def _count(rule, lt, text):
    return len(rule.match(lt.get_analyzed_sentence(text)))


def _text_matches(rule, lt, text):
    return rule.match(lt.analyze_text(text))


# --- AvsAnRuleTest ---

@pytest.mark.parametrize('text', [
    'It must be an xml name.', 'analyze an hprof file', 'This is an sbt project.', 'Import an Xcode project.',
    'This is a oncer.', 'She was a Oaxacan chef.', 'The doctor requested a urinalysis.', 'She brought a Ouija board.',
    'This is a test sentence.', 'It was an hour ago.', 'A university is ...', 'A one-way street ...',
    "An hour's work ...", 'Going to an "industry party".', 'An 8-year old boy ...', 'An 18-year old boy ...',
    'The A-levels are ...', 'An NOP check ...', 'A USA-wide license ...', '...asked a UN member.',
    'In an un-united Germany...',
    # fixed false alarms:
    'Here, a and b are supplementary angles.', "The Qur'an was translated into Polish.", 'See an:Grammatica',
    'See http://www.an.com', 'Station A equals station B.', 'e.g., the case endings -a -i -u and mood endings -u -a',
    "A'ight, y'all.", "He also wrote the comic strips Abbie an' Slats.", 'Do an ngram tokenization fix.',
    'A car with a unibody construction.', 'Given a Userset, create and return a matching PrincipalModel.',
    'An uninterpreted dream is like an unopened letter.',
    'Here ζ refers to the Riemann zeta function, the identity relating the product over primes to ζ(2) is an '
    'example of an Euler product, and the evaluation of ζ(2) as π2/6 is the Basel problem, solved by Leonhard Euler '
    'in 1735.',
    'In more technical terms, a navigation is in part made of a series of channels nearly parallel to the valley '
    'gradient and stream bed of an unimproved river, and which always shares the drainage basin of the river.',
    'This approach both allows the trial court to perform its gatekeeping function at the summary judgment stage '
    'of the proceedings and avoids placing an onerous burden upon the nonmoving party," the court said.',
    'The Queen travelled through the tunnel to Calais on a Eurostar train, which stopped nose to nose with the '
    'train that carried President Mitterrand from Paris.',
    'He has been a utilities lawyer for over 30 years.', 'He has a unibrow.',
    "When compensated for temperature, the forward voltage drop of a transistor's base-emitter junction can "
    'provide a usably accurate logarithmic or exponential function.',
    # With uppercase letters:
    'A University', 'A Europe wide something',
    # Test on acronyms/initials:
    'A. R.J. Turgot',
    # list items
    'Make sure that 3.a as well as 3.b are correct.',
    # mixed case as dictionary-based exception
    'Anyone for an MSc?',
    # mixed case from general case
    'Anyone for an XMR-based writer?',
    # Test on apostrophes
    "Its name in English is a[1] (), plural A's, As, as, or a's.",
    # Both are correct according to Merriam Webster
    'An historic event', 'A historic event',
])
def test_avs_an_correct(messages, lt, text):
    """AvsAnRuleTest.testRule (correct sentences)"""
    assert _count(AvsAnRule(messages), lt, text) == 0


@pytest.mark.parametrize('text', [
    'It was a hour ago.', "It was an sentence that's long.", 'It was a uninteresting talk.', 'An university',
    'A unintersting ...', "A hour's work ...", 'Going to a "industry party".', 'It was a unidentifiable object.',
    " I'll set you up with an userid and password so you can pick the...",
    # With uppercase letters:
    'then an University sdoj fixme sdoopsd', 'A 8-year old boy ...', 'A 18-year old boy ...',
    '...asked an UN member.', 'In a un-united Germany...', 'Anyone for a MSc?',
])
def test_avs_an_incorrect(messages, lt, text):
    """AvsAnRuleTest.testRule (errors)"""
    assert _count(AvsAnRule(messages), lt, text) == 1


def test_avs_an_two_matches(messages, lt):
    """AvsAnRuleTest.testRule"""
    assert _count(AvsAnRule(messages), lt, 'It was a uninteresting talk with an long sentence.') == 2


def test_avs_an_suggestions(messages):
    """AvsAnRuleTest.testSuggestions"""
    rule = AvsAnRule(messages)
    assert rule.suggest_a_or_an('string') == 'a string'
    assert rule.suggest_a_or_an('university') == 'a university'
    assert rule.suggest_a_or_an('hour') == 'an hour'
    assert rule.suggest_a_or_an('all-terrain') == 'an all-terrain'
    assert rule.suggest_a_or_an('UNESCO') == 'a UNESCO'
    assert rule.suggest_a_or_an('historical') == 'a historical'


@pytest.mark.parametrize('word,determiner', [
    ('string', avsan.A), ('university', avsan.A), ('UNESCO', avsan.A), ('one-way', avsan.A),
    ('interesting', avsan.AN), ('hour', avsan.AN), ('all-terrain', avsan.AN), ('historical', avsan.A_OR_AN),
    ('', avsan.UNKNOWN), ('-way', avsan.UNKNOWN), ('camelCase', avsan.UNKNOWN),
])
def test_get_correct_determiner_for(word, determiner):
    """AvsAnRuleTest.testGetCorrectDeterminerFor"""
    token = AnalyzedTokenReadings(AnalyzedToken(word, 'fake-postag', 'fake-lemma'), 0)
    assert get_correct_determiner_for(token) == determiner


def test_get_correct_determiner_for_exception():
    """AvsAnRuleTest.testGetCorrectDeterminerForException (Java: a
    NullPointerException)"""
    with pytest.raises(AttributeError):
        get_correct_determiner_for(None)


@pytest.mark.parametrize('text,from_pos,to_pos', [
    # no quotes etc.:
    ('a industry standard.', 0, 1),
    # quotes..
    ('a "industry standard".', 0, 1),
    ('a “industry standard”.', 0, 1),
    ('a ‘industry standard’.', 0, 1),
    ('a - industry standard".', 0, 1),
    ('This is a "industry standard".', 8, 9),
    ('"a industry standard".', 1, 2),
    ('"Many say this is a industry standard".', 18, 19),
    ('Like many "an desperado" before him, Bart headed south into Mexico.', 11, 13),
])
def test_avs_an_positions(messages, lt, text, from_pos, to_pos):
    """AvsAnRuleTest.testPositions"""
    m = AvsAnRule(messages).match(lt.get_analyzed_sentence(text))[0]
    assert (m.from_pos, m.to_pos) == (from_pos, to_pos)


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule(messages, lt_us):
    """CompoundRuleTest.testRule (setUp doesn't run
    AbstractCompoundRuleTest.testAllCompounds)"""
    rule = CompoundRule(messages, get_language('en-US'), None)
    # correct sentences:
    for text in ('The software supports case-sensitive search.', 'He is one-year-old.',
                 "If they're educated people, they will know.", 'Tiffany & Co chairman has to say something important',
                 'Another one bites the dust', 'We well received your email', 'air-to-air', 'non-party', 'age-old',
                 'able-bodied', 'non-scientific', 'This is the first ever green bond by a municipality.',
                 'Semi Automatic', 'Night Mare', 'This is a multi-module project.'):
        _check(lt_us, rule, 0, text)
    # incorrect sentences:
    _check(lt_us, rule, 1, 'case sensitive', 'case-sensitive')
    _check(lt_us, rule, 1, 'Young criminals must be re educated.')
    _check(lt_us, rule, 1, 'And an other one bites the dust')
    _check(lt_us, rule, 1, 'An other one bites the dust')
    for args in (('good-bye', 'goodbye'), ('back-fire', 'backfire'), ('back fire', 'backfire'),
                 ('air-to air', 'air-to-air'), ('air to air', 'air-to-air'), ('air to-air', 'air-to-air'),
                 ('air to -air', 'air-to-air'), ('age old', 'age-old'), ('able bodied', 'able-bodied'),
                 ('non scientific', 'non-scientific', 'nonscientific'), ('night-mare', 'nightmare'),
                 ('Night-mare', 'Nightmare'), ('Night mare', 'Nightmare'),
                 ('semi automatic', 'semi-automatic', 'semiautomatic'),
                 ('Semi automatic', 'Semi-automatic', 'Semiautomatic'), ('Dev-Ops', 'DevOps'), ('Dev Ops', 'DevOps'),
                 ('Night-mare', 'Nightmare'), ('Play Station', 'PlayStation'), ('Play-Station', 'PlayStation')):
        _check(lt_us, rule, 1, *args)


def test_compound_rule_all_compounds(messages):
    """AbstractCompoundRuleTest.testAllCompounds (only prints warnings for
    possibly misspelled suggestions in Java): the misspelling check of the
    default spelling rule works for all suggestions"""
    rule = CompoundRule(messages, get_language('en-US'), None)
    data = rule.get_compound_rule_data()
    misspelled = []
    for compound in data.incorrect_compounds:
        if compound in data.dash_suggestion and rule.is_misspelled(compound.replace(' ', '-')):
            misspelled.append(compound)
        if compound in data.joined_suggestion and rule.is_misspelled(
                rule.merge_compound(compound, compound in data.joined_lower_case_suggestion)):
            misspelled.append(compound)
    assert len(misspelled) < len(data.incorrect_compounds)


# --- ConsistentApostrophesRuleTest ---

def test_consistent_apostrophes(messages, lt):
    """ConsistentApostrophesRuleTest.testRule"""
    rule = ConsistentApostrophesRule(messages)
    matches = rule.match(lt.analyze_text('It\'s a nice idea. But it doesn’t work.'))
    assert len(matches) == 2
    assert (matches[0].from_pos, matches[0].to_pos) == (2, 4)
    assert matches[0].suggested_replacements == ['’s']
    assert (matches[1].from_pos, matches[1].to_pos) == (29, 32)
    assert matches[1].suggested_replacements == ["n't"]
    assert len(rule.match(lt.analyze_text("It’s a nice idea. But it doesn't work."))) == 2
    assert len(rule.match(lt.analyze_text("It's a nice idea. But it doesn't work."))) == 0
    assert len(rule.match(lt.analyze_text('It’s a nice idea. But it doesn’t work.'))) == 0


# --- ContractionSpellingRuleTest ---

def test_contraction_spelling(messages, lt):
    """ContractionSpellingRuleTest.testRule"""
    rule = ContractionSpellingRule(messages, lt.language)
    # correct sentences:
    for text in ("It wasn't me.", "I'm ill.", 'Staatszerfall im südlichen Afrika.', 'by IVE',
                 'Never mind the whys and wherefores.'):
        assert _count(rule, lt, text) == 0
    # incorrect sentences:
    for text, word in (('Wasnt this great', "Wasn't"), ('YOURE WRONG', "YOU'RE"), ('Dont do this', "Don't"),
                       ('It wasnt me', "wasn't"), ('You neednt do this', "needn't"), ('I know Im wrong', "I'm")):
        matches = rule.match(lt.get_analyzed_sentence(text))
        assert len(matches) == 1, text
        assert matches[0].suggested_replacements == [word], text
    # two suggestions
    matches = rule.match(lt.get_analyzed_sentence('Whereve you are'))
    assert matches[0].suggested_replacements == ["Where've", 'Wherever']


# --- EnglishDashRuleTest ---

def test_dash_rule(lt_us):
    """EnglishDashRuleTest.testRule"""
    rule = EnglishDashRule(lt_us.messages)

    def check(expected_errors, text, expected_suggestion=None):
        matches = rule.match(lt_us.get_analyzed_sentence(text))
        assert len(matches) == expected_errors, matches
        if expected_suggestion is not None:
            assert matches[0].suggested_replacements == [expected_suggestion]
    # correct sentences:
    check(0, 'This is my T-shirt.')
    check(0, 'This is water-proof.')
    check(0, 'This works semi-automatically.')
    check(0, "She's a newcomer.")  # compounds.txt: "new-comer+"
    check(0, 'I sent you and e-mail.')  # compounds.txt: "e-mail"
    # incorrect sentences:
    check(1, 'T – shirt', 'T-shirt')
    check(1, 'three–way street', 'three-way')
    check(1, 'surface — to — surface', 'surface-to-surface')
    # compounds.txt: "semi-automatic$" and "semi-automatically$"
    check(1, 'This works semi–automatically.', 'semi-automatically')
    check(1, 'This works semi – automatically.', 'semi-automatically')
    check(1, 'I sent you and e–mail.', 'e-mail')  # compounds.txt: "e-mail"


# --- EnglishSpecificCaseRuleTest ---

def test_specific_case(messages, lt):
    """EnglishSpecificCaseRuleTest.testRule"""
    rule = EnglishSpecificCaseRule(messages)
    for text in ('Harry Potter', 'I like Harry Potter.', 'I like HARRY POTTER.'):
        assert _count(rule, lt, text) == 0
    for text in ('harry potter', 'harry Potter', 'Harry potter'):
        assert _count(rule, lt, text) == 1
    matches1 = rule.match(lt.get_analyzed_sentence('I like Harry potter.'))
    assert len(matches1) == 1
    assert (matches1[0].from_pos, matches1[0].to_pos) == (7, 19)
    assert matches1[0].suggested_replacements == ['Harry Potter']
    assert matches1[0].message == 'If the term is a proper noun, use initial capitals.'
    matches2 = rule.match(lt.get_analyzed_sentence('Alexander The Great'))
    assert len(matches2) == 1
    assert matches2[0].message == 'If the term is a proper noun, use the suggested capitalization.'
    matches3 = rule.match(lt.get_analyzed_sentence('I like Harry  potter.'))  # note the two spaces
    assert len(matches3) == 1
    assert (matches3[0].from_pos, matches3[0].to_pos) == (7, 20)


# --- EnglishUnpairedBracketsRuleTest ---

def _bracket_count(rule, lt, text):
    return len(rule.match([lt.get_analyzed_sentence(text)]))


def test_unpaired_brackets(messages, lt):
    """EnglishUnpairedBracketsRuleTest.testRule"""
    rule = EnglishUnpairedBracketsRule(messages, get_language('en'))
    for text in ('(This is a test sentence).', "This is a word 'test'.", 'This is no smiley: (some more text)',
                 'This is a sentence with a smiley :)', 'This is a sentence with a smiley :(',
                 'This is a sentence with a smiley :-)', 'This is a sentence with a smiley ;-) and so on...',
                 'This is a [test] sentence...',
                 'The plight of Tamil refugees caused a surge of support from most of the Tamil political '
                 'parties.[90]',
                 '(([20] [20] [20]))',
                 # test for a case that created a false alarm after disambiguation
                 'This is a "special test", right?',
                 # numerical bullets
                 'We discussed this in Chapter 1).',
                 'The jury recommended that: (1) Four additional deputies be employed.',
                 'We discussed this in section 1a).', 'We discussed this in section iv).',
                 # some more cases
                 "(Ketab fi Isti'mal al-'Adad al-Hindi)", "(al-'Adad al-Hindi)", "will-o'-the-wisp",
                 'cat-o’-nine-tails',
                 # TODO: ambiguous
                 'a) item one\nb) item two\nc) item three',
                 'This is not so (neither a nor b',
                 # TODO: Why is this correct and the next one incorrect?
                 'Some text (and some funny remark :-) with more text to follow'):
        assert _bracket_count(rule, lt, text) == 0, text
    for text in ('\n\na) New York\nb) Boston\n', '\n\n1.) New York\n2.) Boston\n',
                 '\n\nXII.) New York\nXIII.) Boston\n', '\n\nA) New York\nB) Boston\nC) Foo\n'):
        assert len(_text_matches(rule, lt, text)) == 0, text
    # incorrect sentences:
    for text in ('(This is a test sentence.', 'This is not so (neither a nor b.', 'This is not so neither a nor b)',
                 'This is not so neither foo nor bar)',
                 # this is currently considered incorrect... although people often use smileys this way:
                 'Some text (and some funny remark :-) with more text to follow!'):
        assert _bracket_count(rule, lt, text) == 1, text
    assert _bracket_count(rule, lt, '(This is a test] sentence.') == 2
    assert _bracket_count(rule, lt, 'This [is (a test} sentence.') == 3


def test_unpaired_brackets_multiple_sentences(lt):
    """EnglishUnpairedBracketsRuleTest.testMultipleSentences"""
    assert len(lt.check('This is multiple sentence text that contains a bracket: '
                        '[This is a bracket. With some text.] and this continues.\n')) == 0
    assert len(lt.check('This is multiple sentence text that contains a bracket. '
                        '(This is a bracket. \n\n With some text.) and this continues.')) == 0
    assert len(lt.check('This is multiple sentence text that contains a bracket: '
                        '[This is a bracket. With some text. And this continues.\n\n')) == 1


# --- EnglishUnpairedQuotesRuleTest ---

_QUOTES_CORRECT = (
    "This is a word 'test'.", "I don't know.", "This is the joint presidents' declaration.", 'The screen is 20"',
    'The screen is 20" wide.', 'This is what he said: "We believe in freedom. This is what we do."',
    "He was an ol' man.", "'till the end.", "jack-o'-lantern", "jack o'lantern", "sittin' there", "Nothin'", "ya'",
    "I'm not goin'", "y'know", "Please find attached Fritz' revisions", "You're only foolin' round.",
    "I stayed awake 'till the morning.", "under the 'Global Markets' heading", "He's an 'admin'.",
    "However, he's still expected to start in the 49ers' next game on Oct.", "all of his great-grandfathers' names",
    "Though EES' past profits now are in question", "Networks' Communicator and FocusFocus' Conference.",
    "Additional funding came from MegaMags' founders and existing individual investors.", 'al-Jazā’er',
    'second Mu’taq and third', "second Mu'taq and third", 'The phrase ‘\\1 \\2’ is British English.',
    'The phrase ‘1 2’ is British English.', "22' N., long. ", "11º 22'", "11° 22'", "11° 22.5'",
    "In case I garbled mine, here 'tis.", "It's about three o’clock.", "It's about three o'clock.", 'Rory O’More',
    "Rory O'More", 'Côte d’Ivoire', "Côte d'Ivoire", 'Colonel d’Aubigni', "They are members of the Bahá'í Faith.",
    # test for a case that created a false alarm after disambiguation
    'This is a "special test", right?',
    # inches exception shouldn't match " here:
    'In addition, the government would pay a $1,000 "cost of education" grant to the schools.',
    "Paradise lost to the alleged water needs of Texas' big cities Thursday.", "Kill 'em all!",
    "Puttin' on the Ritz", "Dunkin' Donuts", "Hold 'em!",
    # some more cases
    "(Ketab fi Isti'mal al-'Adad al-Hindi)", "(al-'Adad al-Hindi)", "On their 'host' societies.",
    "On their 'host society'.",
    "Burke-rostagno the Richard S. Burkes' home in Wayne may be the setting for the wedding reception for their "
    "daughter.",
    "The '49 team was off to a so-so 5-5 beginning",
    "The best reason that can be advanced for the state adopting the practice was the advent of expanded highway "
    "construction during the 1920s and '30s.",
    "A Republican survey says Kennedy won the '60 election on the religious issue.",
    'Economy class seats have a seat pitch of 31-33", with newer aircraft having thinner seats that have a 31" '
    'pitch.',
    '"02" will sort before "10" as expected so it will have size of 10".',
    '"02" will sort before "10" as expected so it will have size of 10"',  # inch symbol is at the sentence end
    '"02" will sort before "10"',  # quotation mark is at the sentence end
    "On their 'host societies'.", "On their host 'societies'.",
    # TODO: ambiguous
    "On their host societies'.",
    'I think that Liszt\'s "Forgotten Waltz No.3" is a hidden masterpiece.',
    'I think that Liszt\'s "Forgotten Waltz No. 3" is a hidden masterpiece.',
    'Turkish distinguishes between dotted and dotless "I"s.',
    'It has recognized no "bora"-like pattern in his behaviour.',  # It's fixed with the new tokenizer
    'Some text. This is "12345", a number.', 'Some text.\n\nThis is "12345", a number.',
    'Some text. This is 12345", a number.',  # could be "inch", so no error
    '"When you bring someone," he said.\nGibson introduced the short-scale (30.5") bass in 1961.',
)
_QUOTES_INCORRECT = (
    'The screen is very" wide.', "On their 'host societies.", "This is a test with an apostrophe &'.",
    'He is making them feel comfortable all along."', '"He is making them feel comfortable all along.',
)


def test_unpaired_quotes(messages, lt):
    """EnglishUnpairedQuotesRuleTest.testRule"""
    rule = EnglishUnpairedQuotesRule(messages, get_language('en'))
    for text in _QUOTES_CORRECT:
        assert _bracket_count(rule, lt, text) == 0, text
    for text in _QUOTES_INCORRECT:
        assert _bracket_count(rule, lt, text) == 1, text
    assert _bracket_count(rule, lt, '"This is a test” sentence.') == 2
    assert _bracket_count(rule, lt, 'This "is \'a test” sentence.') == 3


def test_unpaired_quotes_multiple_sentences(lt):
    """EnglishUnpairedQuotesRuleTest.testMultipleSentences"""
    assert len(lt.check('This is multiple sentence text that contains Quotes: '
                        '"This is a bracket. With some text." and this continues.\n')) == 0
    assert len(lt.check('This is multiple sentence text that contains Quotes. '
                        '“This is a bracket. \n\n With some text.” and this continues.')) == 0
    assert len(lt.check('This is multiple sentence text that contains a Quote: '
                        '“This is a bracket. With some text. And this continues.\n\n')) == 1


# --- EnglishWordRepeatRuleTest, WordRepeatRuleTest ---

@pytest.mark.parametrize('text,expected', [
    ('This is a test.', 0), ('If I had had time, I would have gone to see him.', 0),
    ("I don't think that that is a problem.", 0),
    ('He also said that Azerbaijan had fulfilled a task he set, which was that that their defense budget should '
     'exceed the entire state budget of Armenia.', 0),
    ('Just as if that was proof that that English was correct.', 0),
    ('It was noticed after more than a month that that promise had not been carried out.', 0),
    ('It was said that that lady was an actress.', 0),
    ("Kurosawa's three consecutive movies after Seven Samurai had not managed to capture Japanese audiences in the "
     'way that that film had.', 0),
    ('The can can hold the water.', 0), ('May May awake up?', 0), ('May may awake up.', 0),
    ('The cat does meow meow', 0), ('Hah Hah', 0), ('Hip Hip Hooray', 0), ('Hip Hip', 1), ("It's S.T.E.A.M.", 0),
    ('Ok ok ok!', 0), ('O O O', 0), ('Alice and Bob had had a long-standing relationship.', 0),
    ('I may may awake up.', 1), ('That is May May.', 1), ('Will Will awake up?', 0), ('Will will awake up.', 0),
    ('I will will awake up.', 1), ('Please wait wait for me.', 1), ('Wait wait!', 0), ('That is Will Will.', 1),
    ('I will will hold the ladder.', 1),
    ('You can feel confident that that this administration will continue to support a free and open Internet.', 1),
    ('This is is a test.', 1), ('b a s i c a l l y', 0), ('You can contact E.ON on Instagram.', 0),
    ('But I i was not sure.', 1), ('I I am the best.', 1), ('In a land far far away.', 0),
    ('I love you so so much.', 0), ('Aye aye, sir!', 0), ("What Tom did didn't seem to bother Mary at all.", 0),
    ("Whatever you do don't leave the lid up on the toilet!", 0),
    ("Keep your chin up and whatever you do don't doubt yourself or your actions.", 0),
    ("I know that that can't really happen.", 0), ('Please pass her her phone.', 0), ('I have visited Bora Bora.', 0),
])
def test_english_word_repeat(messages, lt, text, expected):
    """EnglishWordRepeatRuleTest.testRepeatRule"""
    assert _count(EnglishWordRepeatRule(messages, get_language('en')), lt, text) == expected


@pytest.mark.parametrize('text,expected', [
    ('This is a test sentence.', 0), ('This is a test sentence...', 0),
    # make sure we ignore immunized tokens
    ('And side to side and top to bottom...', 0),
    ('This this is a test sentence.', 1), ('This is a test sentence sentence.', 1),
    ('This is is a a test sentence sentence.', 3),
])
def test_word_repeat(messages, lt, text, expected):
    """WordRepeatRuleTest.testRule"""
    assert _count(WordRepeatRule(messages, get_language('en')), lt, text) == expected


# --- EnglishWordRepeatBeginningRuleTest ---

def test_word_repeat_beginning(lt_us):
    """EnglishWordRepeatBeginningRuleTest.testRule"""
    # two successive sentences that start with the same non-adverb word.
    assert len(lt_us.check('This is good. This is good, too.')) == 0
    # three successive sentences that start with the same exception word ("the").
    assert len(lt_us.check("The car. The bicycle. The third sentence with 'the'.")) == 0
    # three successive sentences that start with the same non-exception word (personal pronoun "I")
    matches1 = lt_us.check("I think so. I have seen that before. I don't like it.")
    assert len(matches1) == 1
    assert matches1[0].suggested_replacements[:3] == ['Furthermore, I', 'Likewise, I', 'Not only that, but I']
    # three successive sentences that start with the same non-exception word (personal pronoun "He")
    matches2 = lt_us.check("He thinks so. He has seen that before. He doesn't like it.")
    assert len(matches2) == 1
    assert matches2[0].suggested_replacements[:3] == ['Furthermore, he', 'Likewise, he', 'Not only that, but he']
    # two successive sentences that start with one of the saved adverbs ("Also")
    matches3 = lt_us.check('Also, I play football. Also, I play basketball.')
    assert len(matches3) == 1
    for s in ('Additionally', 'Besides', 'Furthermore', 'Moreover', 'In addition', 'As well as'):
        assert s in matches3[0].suggested_replacements


# --- EnglishWrongWordInContextRuleTest ---

def test_wrong_word_in_context(messages, lt_us):
    """EnglishWrongWordInContextRuleTest.testRule (Java passes null messages,
    the English messages are used here)"""
    rule = EnglishWrongWordInContextRule(messages, get_language('en-US'))

    def bad(text):
        assert _count(rule, lt_us, text) == 1, text

    def good(text):
        assert _count(rule, lt_us, text) == 0, text
    # prescribe/proscribe
    bad('I have proscribed you a course of antibiotics.')
    good('I have prescribed you a course of antibiotics.')
    good('Name one country that does not proscribe theft.')
    bad('Name one country that does not prescribe theft.')
    m = rule.match(lt_us.get_analyzed_sentence('I have proscribed you a course of antibiotics.'))[0]
    assert m.suggested_replacements[0] == 'prescribed'
    # herion/heroine
    bad('We know that heroine is highly addictive.')
    good('He wrote about his addiction to heroin.')
    good('A heroine is the principal female character in a novel.')
    bad('A heroin is the principal female character in a novel.')
    # bizarre/bazaar
    bad('What a bazaar behavior!')
    good('I bought these books at the church bazaar.')
    good('She has a bizarre haircut.')
    bad('The Saturday morning bizarre is worth seeing even if you buy nothing.')
    # bridal/bridle
    bad('The bridle party waited on the lawn.')
    good('Forgo the champagne treatment a bridal boutique often provides.')
    good('He sat there holding his horse by the bridle.')
    bad('Each rider used his own bridal.')
    # desert/dessert
    bad('They have some great deserts on this menu.')
    good('They have some great desserts on this menu.')
    # statute/statue
    bad('They have some great marble statutes.')
    good('They have a great marble statue.')
    # neutron/neuron
    good('Protons and neutrons')
    bad('Protons and neurons')
    # hangar / hanger
    bad('The plane taxied to the hanger.')
    good('The plane taxied to the hangar.')


# --- EnglishRepeatedWordsRuleTest ---

@pytest.mark.parametrize('text', [
    # form
    'They went on to form a new group. The bacteria causes a blood clot to form in the jugular vein.',
    # global
    'Asia Global Crossing Ltd. Global Crossing and Asia Global Crossing.',
    'It was a global effort. Announcing the participation of Enron Global Markets.',
    # great
    'Matthew S. Anderson, Peter the Great. The Tomahawks were shipped from Great Britain.',
    'It was great. The Tomahawks were shipped from Great Britain.',
    # interesting
    'I found it very interesting. An interesting fact about me is that I have a twin.',
    # maybe
    "Maybe it's because I used to be a FLAMING LIBERAL? Or maybe it's because with age, I developed EYES THAT SEE!",
    # need
    'It needs to be done. That needs to be done.', 'This was needed. There is a need to do it.',
    'It needs to be done. That also needed to be done.',
    'I still need to sign in somewhere. You need to sign in too.',
    # new
    'This is a new experience. Happy New Year!',
    # often
    "It's often gloomy outside. More often than not, it's raining.",
    "We have bad weather here often. Often times, it's raining.",
    # problem
    'The students were given some problems. They needed help to solve the problems.',
    "Then, there were numerous problems after that. His initial interest lay in an attempt to solve Hilbert's fifth "
    'problem.',
    "There were some problems with the tests. No problem, I'm not in a rush.",
    'The students were given some problems. They were math problems.',
    # several
    'We noticed them several times. Several thousand people stormed the gate.',
    # suggest
    'I suggested that, but he also suggests that.',
    'He suggested that we review them again. What do these suggest about the transaction history?',
    'I suggested he look it over again. This strongly suggests that Mr. Batt is guilty.',
    # whole
    'In this example, persons is used instead of people because the law applies to the individuals and never to the '
    'group as a whole.',
    # ignore sentences without period at the end
    'I suggested this. She suggests that',
])
def test_repeated_words_correct(messages, lt, text):
    """EnglishRepeatedWordsRuleTest.testRule (correct texts)"""
    assert len(_text_matches(EnglishRepeatedWordsRule(messages), lt, text)) == 0


def test_repeated_words(messages, lt):
    """EnglishRepeatedWordsRuleTest.testRule"""
    rule = EnglishRepeatedWordsRule(messages)
    matches = _text_matches(rule, lt, 'I suggested this. She suggests that.')
    assert len(matches) == 1
    assert (matches[0].from_pos, matches[0].to_pos) == (22, 30)
    assert matches[0].suggested_replacements[:3] == ['proposes', 'recommends', 'submits']
    matches = _text_matches(rule, lt, 'I suggested this. She suggests that. And they suggested that.')
    assert len(matches) == 2
    assert matches[0].from_pos == 22
    assert matches[1].from_pos == 46
    assert matches[0].suggested_replacements[0] == 'proposes'
    assert matches[1].suggested_replacements[0] == 'proposed'
    matches = _text_matches(rule, lt, 'The problem was weird. And the solutions needed to be weird.')
    assert len(matches) == 1
    assert matches[0].suggested_replacements[0] == 'odd'


# --- WordCoherencyRuleTest ---

@pytest.fixture(scope='module')
def coherency_lt():
    lt = JLanguageTool(get_language('en-US'))
    # TestTools.disableAllRulesExcept(lt, "EN_WORD_COHERENCY")
    for rule in lt.get_all_rules():
        if rule.get_id() != 'EN_WORD_COHERENCY':
            lt.disable_rule(rule.get_id())
    return lt


def test_word_coherency(messages, coherency_lt):
    """WordCoherencyRuleTest.testRule, testCallIndependence and
    testMatchPosition"""
    lt = coherency_lt

    def count(text):
        return len(WordCoherencyRule(messages).match(lt.analyze_text(text)))
    # correct sentences:
    assert count('He likes archeology. She likes archeology, too.') == 0
    assert count('He likes archaeology. She likes archaeology, too.') == 0
    # errors:
    assert count('He likes archaeology. She likes archeology, too.') == 1
    matches1 = lt.check('He is reelected, or he will be re-elected.')
    assert len(matches1) == 1
    assert (matches1[0].from_pos, matches1[0].to_pos) == (31, 41)
    assert matches1[0].suggested_replacements == ['reelected']
    matches2 = lt.check('He was reelected, and I will re-elect him again in 2002.')
    assert len(matches2) == 1
    assert (matches2[0].from_pos, matches2[0].to_pos) == (29, 37)
    assert matches2[0].suggested_replacements == ['reelect']
    matches3 = lt.check('He oxidises o, or he oxidizes')
    assert len(matches3) == 1
    assert (matches3[0].from_pos, matches3[0].to_pos) == (21, 29)
    assert matches3[0].suggested_replacements == ['oxidises']
    # testCallIndependence
    assert count('He likes archaeology.') == 0
    assert count('She likes archeology, too.') == 0  # this won't be noticed, the calls are independent of each other
    # testMatchPosition
    matches = lt.check('He likes archaeology. She likes archeology, too.')
    assert len(matches) == 1
    assert (matches[0].from_pos, matches[0].to_pos) == (32, 42)


def test_word_coherency_complete_texts(coherency_lt):
    """WordCoherencyRuleTest.testRuleCompleteTexts"""
    lt = coherency_lt
    assert len(lt.check('He likes archaeology. Really? She likes archaeology, too.')) == 0
    assert len(lt.check('He likes archaeology. Really? She likes archeology, too.')) == 1
    assert len(lt.check('He likes archeology. Really? She likes archaeology, too.')) == 1
    assert len(lt.check('Mix of upper case and lower case: Westernize and westernise.')) == 1


# --- AmericanReplaceRuleTest, BritishReplaceRuleTest, NewZealandReplaceRuleTest ---

def _check_simple_replace_rule(rule, lt, sentence, word):
    matches = rule.match(lt.get_analyzed_sentence(sentence))
    assert len(matches) == 1, sentence
    assert matches[0].suggested_replacements == [word], sentence


def test_american_replace_rule(messages):
    """AmericanReplaceRuleTest.testRule"""
    rule = AmericanReplaceRule(messages, '/en/en-US/replace.txt')
    lt = JLanguageTool(get_language('en-US'))
    assert _count(rule, lt, 'Buy some gasoline.') == 0
    _check_simple_replace_rule(rule, lt, 'I love fish fingers.', 'fish sticks')


def test_british_replace_rule(messages):
    """BritishReplaceRuleTest.testRule"""
    rule = BritishReplaceRule(messages, '/en/en-GB/replace.txt')
    lt = JLanguageTool(get_language('en-GB'))
    assert _count(rule, lt, 'Buy some petrol.') == 0
    # at the beginning of a sentence
    _check_simple_replace_rule(rule, lt, 'Diapers for sale!', 'Nappies')
    # inside sentence
    _check_simple_replace_rule(rule, lt, 'We have some diapers for sale.', 'nappies')
    # expression
    _check_simple_replace_rule(rule, lt, 'Everyone loves cotton candy.', 'candy floss')


def test_new_zealand_replace_rule(messages):
    """NewZealandReplaceRuleTest.testRule"""
    rule = NewZealandReplaceRule(messages, '/en/en-NZ/replace.txt')
    lt = JLanguageTool(get_language('en-NZ'))
    assert _count(rule, lt, 'Walk on the footpath.') == 0
    # at the beginning of a sentence
    _check_simple_replace_rule(rule, lt, 'Sidewalk is not a place to park your car!', 'Footpath')
    # inside sentence
    _check_simple_replace_rule(rule, lt, 'I walked on the sidewalk', 'footpath')


# --- UnitConversionRuleTest, UnitConversionRuleImperialTest, UnitConversionRuleUSTest ---

def _assert_unit_matches(text, expected_matches, converted, rule, lt):
    # UnitConversionRuleTestHelper.assertMatches
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_matches, 'Got matches: %s' % matches
    if expected_matches > 0 and converted is not None:
        assert any(converted in s for s in matches[0].suggested_replacements), \
            'Suggestion is correct: %s / expected: %s' % (matches[0].suggested_replacements, converted)


def test_unit_conversion_rule(lt):
    """UnitConversionRuleTest.match"""
    rule = UnitConversionRule(lt.messages)
    _assert_unit_matches('I am 6 feet tall.', 1, '1.83 m', rule, lt)
    _assert_unit_matches('I am 6 feet (2.02 m) tall.', 1, '1.83 m', rule, lt)
    _assert_unit_matches('I am 6 feet (1.82 m) tall.', 0, None, rule, lt)
    _assert_unit_matches('Heat up to 18\u00a0°C (64.4 °F).', 0, None, rule, lt)
    _assert_unit_matches('Heat up to 18\u00a0°C (64.4\u00a0°F).', 0, None, rule, lt)
    _assert_unit_matches('Heat up to 18 °C (64.4\u00a0°F).', 0, None, rule, lt)
    _assert_unit_matches('The path is 100 miles long.', 1, '160.93 km', rule, lt)
    _assert_unit_matches('The path is 100 miles (160.93 km) long.', 0, None, rule, lt)
    _assert_unit_matches('The shipment weighs 10,000.75 pounds.', 1, '4.54 t', rule, lt)
    _assert_unit_matches('She is 5\'6".', 1, '1.68 m', rule, lt)
    _assert_unit_matches('My new apartment is 500 sq ft.', 1, '46.45 m²', rule, lt)
    _assert_unit_matches('It is 100 degrees Fahrenheit outside.', 1, '37.78 °C', rule, lt)
    _assert_unit_matches('It is 100 °F outside.', 1, '37.78 °C', rule, lt)
    _assert_unit_matches('It is -22 °F outside.', 1, '-30 °C', rule, lt)
    _assert_unit_matches('It is -22 degrees Fahrenheit outside.', 1, '-30 °C', rule, lt)
    # https://github.com/languagetool-org/languagetool/issues/2357
    _assert_unit_matches("Millions watched the 1989's Superbowl.", 0, None, rule, lt)
    # https://github.com/languagetool-org/languagetool/issues/2255
    _assert_unit_matches('Coordinates: 34°09′22″N 118°7′55″W', 0, None, rule, lt)
    assert rule.get_id() == 'METRIC_UNITS_EN_GENERAL' and 'picky' in rule.tags


def test_unit_conversion_rule_imperial():
    """UnitConversionRuleImperialTest.match"""
    lt = JLanguageTool(get_language('en-GB'))
    rule = UnitConversionRuleImperial(lt.messages)
    _assert_unit_matches('I just drank 3 pints.', 1, '1.7 l', rule, lt)
    _assert_unit_matches('I am 6 feet (2.02 m) tall.', 1, '1.83 metres', rule, lt)


def test_unit_conversion_rule_us():
    """UnitConversionRuleUSTest.match"""
    lt = JLanguageTool(get_language('en-US'))
    rule = UnitConversionRuleUS(lt.messages)
    _assert_unit_matches('I just drank 3 pints.', 1, '1.42 l', rule, lt)
    _assert_unit_matches('I am 6 feet (2.02 m) tall.', 1, '1.83 meters', rule, lt)
    _assert_unit_matches('16 kilometers (10 miles)', 1, None, rule, lt)
    _assert_unit_matches('16 kilometers (ca. 10 miles)', 0, None, rule, lt)
    _assert_unit_matches('16 kilometers (9.94 mi)', 0, None, rule, lt)
    # matched by antipattern;
    _assert_unit_matches('Use 3-5 pounds of butter.', 0, None, rule, lt)
    _assert_unit_matches("It's 1/4 mile away", 0, None, rule, lt)
    _assert_unit_matches('A 2:1 cup', 0, None, rule, lt)
    _assert_unit_matches('1⁄4 cup', 0, None, rule, lt)
    # matched by special case in the case as long as "x ft y inch" is not parsed properly:
    _assert_unit_matches('It is 0.76 metres (2 ft 6 inch)', 0, None, rule, lt)


# --- UppercaseSentenceStartRuleTest ---

def test_uppercase_sentence_start():
    """UppercaseSentenceStartRuleTest.testRule"""
    lt = JLanguageTool(get_language('en'))
    for text in ('v8.2.0 has been released', 'In Nov. next year.', 'www.languagetool.org is a website.',
                 'Languagetool.org is a website.', '1. an item in a list\n2. another item.',
                 'This is a sentence. microRNA is the start of another sentence.',
                 'This is a sentence. mRNA is the start of another sentence.',
                 'This is a sentence. iDeal is the start of another sentence.',
                 'languagetool.org is a website.',  # questionable
                 '— Dash introducing enumeration item!', '— dash introducing enumeration item!'):
        assert len(lt.check(text)) == 0, text
    assert len(lt.check('a sentence.')) == 1
    assert len(lt.check('a sentence!')) == 1
    lt.disable_rule('EN_CASE_AFTER_SALUTATION')
    # special case for paste from e.g. Outlook
    assert len(lt.check('Hi Mr. Miller,\n\n\u00a0\n\nhow are you?')) == 0
    assert len(lt.check('ℹ\ufe0f Tree Structure.')) == 0
    assert len(lt.check('ℹ Tree Structure.')) == 0


# --- filters ---

def test_date_check_filter():
    """DateCheckFilterTest.testGetDayOfWeek and testMonth"""
    f = DateCheckFilter()
    for day, n in (('Sun', 1), ('Mon', 2), ('mon', 2), ('Mon.', 2), ('Monday', 2), ('monday', 2), ('Tue', 3),
                   ('Fri', 6), ('Fr', 6), ('Saturday', 7)):
        assert f.get_day_of_week(day) == n, day
    for month, n in (('jan', 1), ('dec', 12), ('december', 12), ('December', 12), ('DECEMBER', 12)):
        assert f.get_month(month) == n, month
    with pytest.raises(RuntimeError):
        f.get_day_of_week('xx')
    assert f.get_day_str_like_original('2', '1') == '2'
    assert [f.get_day_str_like_original(d, '1st') for d in ('1', '2', '3', '4', '11', '12', '13', '21', '22')] == \
        ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd']


def test_ymd_date_check_filter_arguments():
    with pytest.raises(RuntimeError):
        YMDDateCheckFilter().accept_rule_match(None, {'year': '1'}, 0, [], [])


class _FakeRule(Rule):

    def get_id(self):
        return 'FAKE_ID'

    def get_description(self):
        return 'fake description'


def test_number_in_word_filter(lt):
    """EnglishNumberInWordFilterTest.testFilter"""
    sentence = lt.get_analyzed_sentence('Go0d morning, Potsdam.')
    match = RuleMatch(_FakeRule(), sentence, 0, 4, 'fake msg')
    match_tmp = EnglishNumberInWordFilter().accept_rule_match(match, {'word': 'Go0d'}, 2,
                                                              sentence.get_tokens_without_whitespace(), None)
    assert match_tmp is not None
    assert 'Good' in match_tmp.suggested_replacements


def test_adverb_filter(lt):
    """AdverbFilter: the suggestion is the adjective with the noun"""
    sentence = lt.get_analyzed_sentence('This is a simply test.')
    match = RuleMatch(_FakeRule(), sentence, 8, 21, 'fake msg')
    assert AdverbFilter().accept_rule_match(match, {'adverb': 'simply', 'noun': 'test'}, 0, [], None) \
        .suggested_replacements == ['simple test']
    match = RuleMatch(_FakeRule(), sentence, 8, 21, 'fake msg')
    assert AdverbFilter().accept_rule_match(match, {'adverb': 'fast', 'noun': 'car'}, 0, [], None) \
        .suggested_replacements == []


@pytest.mark.parametrize('suggestion,expected', [
    ('1', '1st'), ('2x', '2nd'), ('3', '3rd'), ('4', '4th'), ('11', '11th'), ('112', '112th'), ('113', '113th'),
    ('21', '21st'), ('102', '102nd'),
])
def test_ordinal_suffix_filter(lt, suggestion, expected):
    """OrdinalSuffixFilter"""
    sentence = lt.get_analyzed_sentence('The 1th time.')
    match = RuleMatch(_FakeRule(), sentence, 4, 7, 'fake msg')
    match.set_suggested_replacement(suggestion)
    assert OrdinalSuffixFilter().accept_rule_match(match, {}, 0, [], None).suggested_replacements == [expected]


# --- tests of excluded components ---

@pytest.mark.skip(reason='spell checking is not ported: MorfologikAmericanSpellerRuleTest, '
                         'MorfologikBritishSpellerRuleTest, MorfologikCanadianSpellerRuleTest, '
                         'MorfologikAustralianSpellerRuleTest, MorfologikNewZealandSpellerRuleTest, '
                         'MorfologikSouthAfricanSpellerRuleTest, AbstractEnglishSpellerRuleTest, '
                         'SpellingCheckRuleTest and LanguageSpecificSpellcheckerTest test the rule matches of the '
                         'spelling rules (MORFOLOGIK_RULE_EN_*)')
def test_speller_rules():
    pass


@pytest.mark.skip(reason='language model rules are not ported: EnglishConfusionProbabilityRuleTest and '
                         'UpperCaseNgramRuleTest need a LanguageModel (ngram data)')
def test_language_model_rules():
    pass


@pytest.mark.skip(reason='remote rules are not ported: EnglishRemoteRuleFilterTest and '
                         'EnglishRemoteRuleSuppressMisspelledTest test the filters of the remote rules')
def test_remote_rules():
    pass


@pytest.mark.skip(reason='spell checking is not ported: InflectorTest tests the Inflector of the translation '
                         'suggestions of the spelling rules (BeoLingusTranslator)')
def test_inflector():
    pass
