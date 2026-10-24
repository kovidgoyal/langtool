"""Tests of the abstract rule classes of languagetool-core that the language
modules subclass (langtool.rules.abstract_rules). The tests of
AbstractSimpleReplaceRule2 and GenericUnpairedQuotesRule are ports of
AbstractSimpleReplaceRule2Test and GenericUnpairedQuotesRuleTest; the Java
code has no tests of its own for the other classes, their tests here are
new and the expected results follow the Java code."""

import pytest

from langtool.api import get_language
from langtool.languages import V, register_language, LANGUAGES
from langtool.messages import messages_for
from langtool.rules import abstract_rules as ar
from langtool.tool import JLanguageTool


if 'yy' not in LANGUAGES:
    # port of org.languagetool.FakeLanguage, as in test_core_rules.py
    register_language('yy', dict(name='FakeLanguage', countries=['YY'], variants=[V('yy-YY')], tagger=None,
                                 disambiguator=None, rules=[]))


@pytest.fixture(scope='module')
def lt(demo_language):
    return JLanguageTool(demo_language)


@pytest.fixture(scope='module')
def messages():
    return messages_for('en')


def sentences(lt, *texts):
    return [lt.get_analyzed_sentence(t) for t in texts]


# --- AbstractSimpleReplaceRule2Test ---

class MyCaseSensitiveRule(ar.AbstractSimpleReplaceRule2):
    def get_file_names(self):
        return ['/xx/abstract_simple_replace2.txt']

    def get_id(self):
        return 'ABSTRACT_TEST_RULE'

    def get_description(self):
        return 'internal test rule'

    def get_short(self):
        return 'internal test rule'

    def get_message(self):
        return 'fake suggestion'

    def get_suggestions_separator(self):
        return ','

    def get_case_sensitivity(self):
        return ar.CS


class MyCaseInsensitiveRule(MyCaseSensitiveRule):
    def get_case_sensitivity(self):
        return ar.CI


@pytest.mark.parametrize('text,cs,ci', [
    ('But a propos', 1, 1),
    ('But A propos', 0, 1),
    ('A propos', 0, 1),
    ('a propos', 1, 1),
    ('A Pokemon', 1, 1),
    ('A pokemon', 0, 1),
])
def test_simple_replace_rule2(lt, messages, demo_language, text, cs, ci):
    cs_rule = MyCaseSensitiveRule(messages, demo_language)
    ci_rule = MyCaseInsensitiveRule(messages, demo_language)
    s = lt.get_analyzed_sentence(text)
    assert len(cs_rule.match(s)) == cs
    assert len(ci_rule.match(s)) == ci


def test_simple_replace_rule2_suggestions(lt, messages, demo_language):
    rule = MyCaseInsensitiveRule(messages, demo_language)
    m, = rule.match(lt.get_analyzed_sentence('But a propos'))
    assert (m.from_pos, m.to_pos) == (4, 12)
    assert m.suggested_replacements == ['à propos']
    m, = rule.match(lt.get_analyzed_sentence('A POKEMON'))
    assert m.suggested_replacements == ['POKÉMON']


class MyCheckCaseRule(MyCaseSensitiveRule, ar.AbstractCheckCaseRule):
    def get_case_sensitivity(self):
        return ar.CI


def test_check_case_rule(lt, messages, demo_language):
    rule = MyCheckCaseRule(messages, demo_language)
    assert rule.is_checking_case()
    assert rule.category.id == 'CASING'
    # the data is read as "lowercase=original"
    m, = rule.match(lt.get_analyzed_sentence('I like pokemon.'))
    assert m.suggested_replacements == ['Pokemon']
    assert not rule.match(lt.get_analyzed_sentence('I like Pokemon.'))


# --- AbstractSimpleReplaceRule ---

class MySimpleReplaceRule(ar.AbstractSimpleReplaceRule):
    def get_wrong_words(self):
        return {'wrongy': ['right', 'correct'], 'Big Apple': ['NYC']}

    def is_case_sensitive(self):
        return False


def test_simple_replace_rule(lt, messages, demo_language):
    rule = MySimpleReplaceRule(messages, demo_language)
    m, = rule.match(lt.get_analyzed_sentence('This is wrongy.'))
    assert (m.from_pos, m.to_pos) == (8, 14)
    assert m.suggested_replacements == ['right', 'correct']
    assert m.message == 'wrongy is not valid. Use: right, correct.'
    m, = rule.match(lt.get_analyzed_sentence('Wrongy, I say.'))
    assert m.suggested_replacements == ['Right', 'Correct']
    m, = rule.match(lt.get_analyzed_sentence('WRONGY!'))
    assert m.suggested_replacements == ['RIGHT', 'CORRECT']
    assert not rule.match(lt.get_analyzed_sentence('This is right.'))


def test_simple_replace_rule_sub_rule_ids(lt, messages, demo_language):
    rule = MySimpleReplaceRule(messages, demo_language)
    rule.use_sub_rule_specific_ids()
    m, = rule.match(lt.get_analyzed_sentence("It's wrongy."))
    assert m.rule.get_id() == 'SIMPLE_REPLACE_WRONGY'


def test_simple_replace_data_loader(tmp_path):
    p = tmp_path / 'replace.txt'
    p.write_text('# comment\na|b=c|d\n', encoding='utf-8')
    assert ar.load_simple_replace_data(str(p)) == {'a': ['c', 'd'], 'b': ['c', 'd']}
    p2 = tmp_path / 'bad.txt'
    p2.write_text('a=\n', encoding='utf-8')
    with pytest.raises(ValueError):
        ar.load_simple_replace_data(str(p2))


def test_to_id(demo_language):
    assert ar.to_id("rock 'n roll", demo_language) == 'ROCK__Q_N_ROLL'
    assert ar.to_id('x-ray', demo_language) == 'X_RAY'
    de = get_language('de-DE')
    assert ar.to_id('Gerät', de) == 'GERAET'


# --- AbstractCompoundRule ---

class MyCompoundRule(ar.AbstractCompoundRule):
    def __init__(self, messages, language):
        super().__init__(messages, language, None, 'with hyphen', 'without hyphen', 'with or without hyphen',
                         'compound')

    def get_id(self):
        return 'TEST_COMPOUND'

    def get_description(self):
        return 'compounds: $match'

    def get_compound_rule_data(self):
        return ar.load_compound_rule_data(self.language, '/xx/compounds-test.txt')


@pytest.mark.parametrize('text,suggestions,msg', [
    ('This is an e mail.', ['e-mail'], 'with hyphen'),
    ('This is a web site.', ['website'], 'without hyphen'),
    ('This is a fun park.', ['fun-park'], 'with hyphen'),
    ('Play tic tac toe.', ['tic-tac-toe', 'tictactoe'], 'with or without hyphen'),
    ('Play tic-tac toe.', ['tic-tac-toe', 'tictactoe'], 'with or without hyphen'),
    ('This is an e-mail.', None, None),
    ('This is a website.', None, None),
    ('Nothing to see here.', None, None),
])
def test_compound_rule(lt, messages, demo_language, text, suggestions, msg):
    rule = MyCompoundRule(messages, demo_language)
    matches = rule.match(lt.get_analyzed_sentence(text))
    if suggestions is None:
        assert matches == []
    else:
        m, = matches
        assert m.suggested_replacements == suggestions
        assert m.message == msg
        assert m.short_message == 'compound'


def test_compound_rule_data(demo_language):
    data = ar.load_compound_rule_data(demo_language, '/xx/compounds-test.txt')
    assert data.incorrect_compounds == {'e mail', 'web site', 'fun park', 'tic tac toe'}
    assert data.joined_suggestion == {'e mail', 'web site', 'tic tac toe'}
    assert data.dash_suggestion == {'e mail', 'fun park', 'tic tac toe'}
    assert data.first_words == {'e', 'web', 'fun', 'tic'}
    assert not data.has_digit_patterns


def test_merge_compound(messages, demo_language):
    rule = MyCompoundRule(messages, demo_language)
    assert rule.merge_compound('Web Site', False) == 'WebSite'
    assert rule.merge_compound('Web Site', True) == 'Website'
    assert rule.merge_compound('tic-tac toe', False) == 'tictactoe'


def test_compound_rule_data_errors(tmp_path):
    p = tmp_path / 'c.txt'
    p.write_text('single\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Not a compound'):
        ar.CompoundRuleData(str(p))
    p.write_text('a-b-c-d-e-f\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Too many'):
        ar.CompoundRuleData(str(p))
    p.write_text('a-b\na b\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicated'):
        ar.CompoundRuleData(str(p))


# --- AbstractWordCoherencyRule ---

class MyCoherencyRule(ar.AbstractWordCoherencyRule):
    rule_id = 'TEST_COHERENCY'

    def get_word_map(self):
        return self.load_word_map('/xx/coherency-test.txt')

    def get_message(self, word1, word2):
        return "'%s' and '%s' should not be used in the same text" % (word1, word2)

    def get_description(self):
        return 'coherency'


def test_word_coherency_rule(lt, messages, demo_language):
    rule = MyCoherencyRule(messages, demo_language)
    m, = rule.match(sentences(lt, 'Das ist aufwändig. ', 'Und das ist aufwendig.'))
    assert (m.from_pos, m.to_pos) == (31, 40)
    assert m.suggested_replacements == ['aufwändig']
    assert m.message == "'aufwendig' and 'aufwändig' should not be used in the same text"
    # the lookup is case sensitive: without a tagger (no lowercase lemma) the
    # capitalized word is not found, as in Java
    assert not rule.match(sentences(lt, 'Das ist aufwändig. ', 'Aufwendig ist das.'))
    assert not rule.match(sentences(lt, 'Das ist aufwändig. ', 'Und das ist aufwändig.'))


def test_word_coherency_loader(tmp_path):
    p = tmp_path / 'c.txt'
    p.write_text('a;b\na;c\n', encoding='utf-8')
    assert ar.load_word_coherency_data(str(p)) == {'a': {'b', 'c'}, 'b': {'a'}, 'c': {'a'}}


def test_java_hash_set_order():
    # java: new HashSet<>(Arrays.asList("b", "a", null, "Aa", "BB")) iterates as [null, Aa, BB, a, b]
    # ("Aa" and "BB" have the same hash code as each other and land in bucket 0, like null)
    assert ar.java_hash_set_order(['b', 'a', None, 'Aa', 'BB']) == [None, 'Aa', 'BB', 'a', 'b']


# --- WordRepeatBeginningRule ---

def test_word_repeat_beginning_rule(lt, messages, demo_language):
    rule = ar.WordRepeatBeginningRule(messages, demo_language)
    assert rule.get_id() == 'WORD_REPEAT_BEGINNING_RULE'
    matches = rule.match(sentences(lt, 'This is a test. ', 'This is a test. ', 'This is a test.'))
    m, = matches
    assert (m.from_pos, m.to_pos) == (32, 36)
    assert m.message == 'Three successive sentences begin with the same word. Consider rewording the sentence or ' \
                        'use a thesaurus to find a synonym.'
    assert not rule.match(sentences(lt, 'This is a test. ', 'This is a test. ', 'That is a test.'))
    # two sentences only are not enough (no adverb detection in the base class)
    assert not rule.match(sentences(lt, 'This is a test. ', 'This is a test.'))
    # the previous sentence must end like a real sentence
    assert not rule.match(sentences(lt, 'This is a test ', 'This is a test ', 'This is a test.'))


# --- PhraseRepeatRule ---

def test_phrase_repeat_rule(lt, messages, demo_language):
    rule = ar.PhraseRepeatRule(messages, demo_language)
    m, = rule.match(lt.get_analyzed_sentence('I like it I like it very much.'))
    assert (m.from_pos, m.to_pos) == (0, 19)
    assert m.suggested_replacements == ['I like it']
    m, = rule.match(lt.get_analyzed_sentence('This is a test a test.'))
    assert m.suggested_replacements == ['a test']
    assert not rule.match(lt.get_analyzed_sentence('This is a test.'))
    assert not rule.match(lt.get_analyzed_sentence('Call 1 2 1 2 now.'))


# --- AdvancedWordRepeatRule ---

class MyAdvancedWordRepeatRule(ar.AdvancedWordRepeatRule):
    rule_id = 'TEST_ADVANCED_REPEAT'

    def get_excluded_words_pattern(self):
        return set()

    def get_excluded_non_words_pattern(self):
        return ar.jregex.compile('[.,]')

    def get_excluded_pos(self):
        return ar.jregex.compile('XXX')

    def get_message(self):
        return 'repeated'

    def get_short_message(self):
        return 'repeated'

    def get_description(self):
        return 'advanced repeat'


def test_advanced_word_repeat_rule(lt, messages, demo_language):
    rule = MyAdvancedWordRepeatRule(messages, demo_language)
    assert rule.default_off
    m, = rule.match(lt.get_analyzed_sentence('The house is a house.'))
    assert (m.from_pos, m.to_pos) == (15, 20)
    assert not rule.match(lt.get_analyzed_sentence('The house is big.'))


# --- AbstractDashRule ---

class MyDashRule(ar.AbstractDashRule):
    def get_description(self):
        return 'dashes'

    def get_message(self):
        return 'Use a hyphen'

    def get_compounds_data(self):
        return self.load_compound_file('/xx/dash-test.txt')


@pytest.mark.parametrize('text,expected', [
    ('Send an e–mail now.', (8, 14, 'e-mail')),
    ('Send an e — mail now.', (8, 16, 'e-mail')),
    ('Visit the fun—park.', (10, 18, 'fun-park')),
    ('Send ane–mail now.', None),
    ('Send an e-mail now.', None),
    ('A web–site.', None),  # lines ending with + are skipped
])
def test_dash_rule(lt, messages, demo_language, text, expected):
    rule = MyDashRule(messages, demo_language)
    matches = rule.match(lt.get_analyzed_sentence(text))
    if expected is None:
        assert matches == []
    else:
        m, = matches
        assert (m.from_pos, m.to_pos, m.suggested_replacements[0]) == expected


# --- AbstractSpecificCaseRule ---

class MySpecificCaseRule(ar.AbstractSpecificCaseRule):
    def get_phrases_path(self):
        return '/xx/specific-case-test.txt'


def test_specific_case_rule(lt, messages, demo_language):
    rule = MySpecificCaseRule(messages, demo_language)
    m, = rule.match(lt.get_analyzed_sentence('I read harry potter.'))
    assert (m.from_pos, m.to_pos) == (7, 19)
    assert m.suggested_replacements == ['Harry Potter']
    assert m.message == rule.get_initial_capital_message()
    m, = rule.match(lt.get_analyzed_sentence('My iphone is old.'))
    assert m.suggested_replacements == ['iPhone']
    assert m.message == rule.get_other_capitalization_message()
    assert not rule.match(lt.get_analyzed_sentence('I read HARRY POTTER.'))
    assert not rule.match(lt.get_analyzed_sentence('I read Harry Potter.'))
    # lowercase phrases at the sentence start are not reported
    assert not rule.match(lt.get_analyzed_sentence('IPhone is old.'))


# --- AbstractSpaceBeforeRule ---

class MySpaceBeforeRule(ar.AbstractSpaceBeforeRule):
    def get_conjunctions(self):
        return ar.jregex.compile('and|or')


def test_space_before_rule(lt, messages, demo_language):
    rule = MySpaceBeforeRule(messages, demo_language)
    m, = rule.match(lt.get_analyzed_sentence('This,and that.'))
    assert (m.from_pos, m.to_pos) == (5, 8)
    assert m.suggested_replacements == [' and']
    assert not rule.match(lt.get_analyzed_sentence('This and that (or not).'))


# --- AbstractPunctuationCheckRule ---

class MyPunctuationCheckRule(ar.AbstractPunctuationCheckRule):
    def is_puncts_join_ok(self, tokens):
        return tokens in ('...', '!?')

    def is_punctuation(self, token):
        return token in ('.', ',', '!', '?')


def test_punctuation_check_rule(lt, messages, demo_language):
    rule = MyPunctuationCheckRule(messages, demo_language)
    assert rule.get_id() == 'PUNCTUATION_GENERIC_CHECK'
    assert rule.category.id == 'PUNCTUATION'
    m, = rule.match(lt.get_analyzed_sentence('This,, and that'))
    assert (m.from_pos, m.to_pos) == (4, 6)
    assert m.suggested_replacements == [',']
    assert m.message == 'bad duplication or combination of punctuation signs'
    # a sequence at the end of the sentence
    m, = rule.match(lt.get_analyzed_sentence('This and that.,'))
    assert (m.from_pos, m.to_pos) == (13, 15)
    assert not rule.match(lt.get_analyzed_sentence('This and that... Or not!?'))


# --- WrongWordInContextRule ---

class MyWrongWordInContextRule(ar.WrongWordInContextRule):
    def get_filename(self):
        return '/xx/wrong-word-in-context-test.txt'

    def get_message_string(self):
        return "Possibly confused word: Did you mean <suggestion>$SUGGESTION</suggestion> instead of '$WRONGWORD'?"

    def get_short_message_string(self):
        return 'Possibly confused word'

    def get_long_message_string(self):
        return "Possibly confused word: Did you mean <suggestion>$SUGGESTION</suggestion> " \
               "(= $EXPLANATION_SUGGESTION) instead of '$WRONGWORD' (= $EXPLANATION_WRONGWORD)?"


def test_wrong_word_in_context_rule(lt, messages, demo_language):
    rule = MyWrongWordInContextRule(messages, demo_language)
    m, = rule.match(lt.get_analyzed_sentence('He was a heroine addict and needed morphine.'))
    assert (m.from_pos, m.to_pos) == (9, 16)
    assert m.suggested_replacements == ['heroin']
    assert m.rule.get_id() == 'WRONG_WORD_IN_CONTEXT_HEROINE_HEROIN'
    assert '(= highly addictive narcotic)' in m.message
    m, = rule.match(lt.get_analyzed_sentence('The doctors proscribed antibiotics.'))
    assert m.suggested_replacements == ['prescribed']
    assert not rule.match(lt.get_analyzed_sentence('He was a heroin addict and needed morphine.'))
    assert not rule.match(lt.get_analyzed_sentence('The heroine of the novel.'))


def test_context_words_prefix():
    assert ar._extract_word_prefix('prescribe[ds]?') == 'prescribe'
    assert ar._extract_word_prefix('heroes?') == 'heroe'
    assert ar._extract_word_prefix('stor(y|ies)') == 'stor'
    assert ar._extract_word_prefix('abc|abd') == 'ab' or ar._extract_word_prefix('abc|abd') == ''
    assert ar._extract_word_prefix('ab') == ''


# --- AbstractRepeatedWordsRule ---

def test_repeated_words_loader(demo_language):
    words = ar.load_repeated_words(ar._rules_file(demo_language, '/xx/repeated-words-test.txt'))
    assert words['large'].synonyms == ['big', 'huge']
    assert words['fast'].synonyms == ['quick', 'rapid']
    assert words['rapid'].synonyms == ['fast', 'quick']


# --- ReadabilityRule ---

def test_readability_syllables(messages, demo_language):
    rule = ar.ReadabilityRule(messages, demo_language, None, False)
    assert rule.get_id() == 'READABILITY_RULE_DIFFICULT'
    assert ar.ReadabilityRule(messages, demo_language, None, True).get_id() == 'READABILITY_RULE_SIMPLE'
    assert rule.default_off
    assert rule.simple_syllables_count('a') == 1
    assert rule.simple_syllables_count('table') == 1  # it's a simple heuristic
    assert rule.simple_syllables_count('reading') == 2
    assert rule.simple_syllables_count('readability') == 5
    assert rule.simple_syllables_count('used') == 1


def test_readability_rule(lt, messages, demo_language):
    easy = ar.ReadabilityRule(messages, demo_language, None, True)
    difficult = ar.ReadabilityRule(messages, demo_language, None, False)
    simple = sentences(lt, 'The cat sat on the mat and the dog ran to the cat.\n\n',
                       'It was a fun day for all of us in the sun.')
    m1, m2 = easy.match(simple)
    assert (m1.from_pos, m1.to_pos) == (0, 11)
    assert m1.message == 'Readability: The text of this paragraph is too simple {Level 6: Very easy}. Too few ' \
                         'words per sentence and too few syllables per word.'
    assert not difficult.match(simple)
    # as in Java (operator precedence in ReadabilityRule.match()), texts that
    # are too easy are only reported if there is more than one paragraph
    assert not easy.match(simple[1:])
    hard = sentences(lt, 'Institutional accountability necessitates comprehensive organizational '
                         'transformation incorporating multidimensional evaluation methodologies '
                         'systematically.')
    assert difficult.match(hard)
    assert not easy.match(hard)


# --- GenericUnpairedQuotesRuleTest ---

@pytest.fixture(scope='module')
def quotes_lt(messages):
    lt = JLanguageTool(get_language('yy-YY'))
    for rule in lt.get_all_rules():
        lt.disable_rule(rule.get_id())
    lt.add_rule(ar.GenericUnpairedQuotesRule(messages, None, ['»', '«', '"', "'", '›', '‹'],
                                             ['«', '»', '"', "'", '‹', '›']))
    return lt


@pytest.mark.parametrize('expected,text', [
    (0, 'This is »correct«.'),
    (0, 'This is «correct».'),
    (0, '»Correct«\n»And ›here‹ it ends.«'),
    (0, '«Correct»\n«And ‹here› it ends.»'),
    (0, '»Correct. This is more than one sentence.«'),
    (0, '»Correct. This is more than one sentence.«\n»And ›here‹ it ends.«'),
    (0, '»Correct«\n\n»And here it ends.«\n\nMore text.'),
    (0, "»Correct, he said. This is the next sentence.« Here's another sentence."),
    (0, "»Correct«, he said.\n\n»This is the next sentence.« »Here's another sentence.«"),
    (0, "»Correct«, he said. »This is the next sentence.«\n»Here's another sentence.«"),
    (0, 'This »is also ›correct‹«.'),
    (0, 'Good.\n\nThis »is also ›correct‹«.'),
    (0, 'Good.\n\n\nThis »is also ›correct‹«.'),
    (0, 'Good.\n\n\n\nThis »is also ›correct‹«.'),
    (0, 'This is "correct".'),
    (0, "This is 'correct'."),
    (0, '"Correct"\n"And \'here\' it ends."'),
    (0, '\'Correct\'\n\'And "here" it ends.\''),
    (0, 'This "is also \'correct\'".'),
    (0, 'This isn\'t "incorrect".'),
    (0, '"This isn\'t incorrect."'),
    (0, 'The screen is 20" wide.'),
    (0, '"The screen is 20" wide."'),
    (1, 'This is not correct«'),
    (1, 'This is »not correct.'),
    (1, 'This is »not correct'),
    (1, 'This is »not an error yet\n\nBut now it has become one'),
    (1, 'This is correct.\n\n»But this is not.'),
    (1, 'This is correct.\n\nBut this is not«'),
    (1, '»This is correct«\n\nBut this is not«'),
    (1, '»This is correct«\n\nBut this »is« not«'),
    (1, "This is not correct. No matter if it's more than one sentence«"),
    (1, "»This is not correct. No matter if it's more than one sentence"),
    (1, "Correct, he said. This is the next sentence.« Here's another sentence."),
    (1, "»Correct, he said. This is the next sentence. Here's another sentence."),
    (1, "»Correct, he said. This is the next sentence.\n\nHere's another sentence."),
    (1, "»Correct, he said. This is the next sentence.\n\n\n\nHere's another sentence."),
    (2, '»Correct«\n»And »here« it ends with two matches.«'),
    (2, '»Correct. This is more than one sentence.«\n»And »here« it ends.«'),
    (2, 'Good.\n\nThis »is also »correct««.'),
    (2, 'Good.\n\n\nThis »is also »correct««.'),
    (2, 'Good.\n\n\n\nThis »is also »correct««.'),
])
def test_unpaired_quotes_rule(quotes_lt, expected, text):
    matches = quotes_lt.check(text)
    assert len(matches) == expected, matches


def test_unpaired_quotes_rule_positions(quotes_lt):
    m = quotes_lt.check('This »is a test.')[0]
    assert (m.from_pos, m.to_pos, m.line, m.end_line, m.column, m.end_column) == (5, 6, 0, 0, 5, 6)
    m = quotes_lt.check('This.\nSome stuff.\nIt »is a test.')[0]
    assert (m.from_pos, m.to_pos, m.line, m.end_line, m.column, m.end_column) == (21, 22, 2, 2, 4, 5)
    m = quotes_lt.check('Th­is »is a test.')[0]
    assert (m.from_pos, m.to_pos) == (6, 7)
