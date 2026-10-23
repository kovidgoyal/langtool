"""Ports of the JUnit tests of the language independent core rules of
LanguageTool (languagetool-core/src/test/java/org/languagetool/rules/):
CommaWhitespaceRuleTest, DoublePunctuationRuleTest,
UppercaseSentenceStartRuleTest, MultipleWhitespaceRuleTest,
SentenceWhitespaceRuleTest, WordRepeatRuleTest,
GenericUnpairedBracketsRuleTest, LongSentenceRuleTest, LongParagraphRuleTest,
PunctuationMarkAtParagraphEndTest, PunctuationMarkAtParagraphEnd2Test and
WhitespaceBeforePunctuationRuleTest."""

import pytest

from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.languages import V, register_language
from langtool.messages import messages_for
from langtool.rules.core import (CommaWhitespaceRule, DoublePunctuationRule, GenericUnpairedBracketsRule,
                                 LongParagraphRule, LongSentenceRule, MultipleWhitespaceRule,
                                 PunctuationMarkAtParagraphEnd, PunctuationMarkAtParagraphEnd2,
                                 SentenceWhitespaceRule, UppercaseSentenceStartRule,
                                 WhitespaceBeforePunctuationRule, WordRepeatRule)
from langtool.tool import JLanguageTool

# Port of org.languagetool.FakeLanguage (code 'yy', no rules at all)
register_language('yy', dict(name='FakeLanguage', countries=['YY'], variants=[V('yy-YY')], tagger=None,
                             disambiguator=None, rules=[]))


def en_messages():
    """TestTools.getEnglishMessages()"""
    return messages_for('en')


def new_demo_lt():
    """new JLanguageTool(TestTools.getDemoLanguage())"""
    return JLanguageTool(get_language('xx-XX'))


def new_fake_lt():
    """new JLanguageTool(new FakeLanguage())"""
    return JLanguageTool(get_language('yy-YY'))


def disable_all_rules(lt):
    for rule in lt.get_all_rules():
        lt.disable_rule(rule.get_id())


# --- CommaWhitespaceRuleTest -------------------------------------------------

class TestCommaWhitespaceRule:

    @pytest.fixture(autouse=True)
    def setup(self, demo_lt):
        self.rule = CommaWhitespaceRule(en_messages())
        self.lt = demo_lt

    def assert_matches(self, text, expected):
        matches = self.rule.match(self.lt.get_analyzed_sentence(text))
        assert len(matches) == expected, (text, matches)

    def assert_matches_for_text(self, text, expected):
        count = 0
        for s in self.lt.analyze_text(text):
            count += len(self.rule.match(s))
        assert count == expected

    @pytest.mark.parametrize('text,expected', [
        ("This is a test sentence.", 0),
        ("I work with the technology .Net and Azure.", 0),
        ("I work with the technology .NET and Azure.", 0),
        ("I use .MP3 or .WAV file suffix", 0),
        ("This, is, a test sentence.", 0),
        ("This (foo bar) is a test!.", 0),
        ("Das kostet €2,45.", 0),
        ("Das kostet 50,- Euro", 0),
        ("This is a sentence with ellipsis ...", 0),
        ("This is a figure: .5 and it's correct.", 0),
        ("This is $1,000,000.", 0),
        ("This is 1,5.", 0),
        ("This is a ,,test''.", 0),
        ("Run ./validate.sh to check the file.", 0),
        ("This is, really, non-breaking whitespace.", 0),
        # test OpenOffice field codes:
        ("In his book,\u0002 Einstein proved this to be true.", 0),
        ("- [ ] A checkbox at GitHub", 0),
        ("- [x] A checked checkbox at GitHub", 0),
        ("A sentence 'with' ten \"correct\" examples of ’using’ quotation “marks” at «once» in it.", 0),
        ("I'd recommend resaving the .DOC as a PDF file.", 0),
        ("I'd recommend resaving the .mp3 as a WAV file.", 0),
        ("I'd suggest buying the .org domain.", 0),
        (". This isn't good.", 0),
        ("), this isn't good.", 0),
        ("Das sind .exe-Dateien", 0),
        ("I live in .Los Angeles", 1),
        # errors:
        ("This,is a test sentence.", 1),
        ("This , is a test sentence.", 1),
        ("This ,is a test sentence.", 2),
        (",is a test sentence.", 2),
        ("This ( foo bar) is a test!.", 1),
        ("This (foo bar ) is a test!.", 1),
        ("This is a sentence with an orphaned full stop .", 1),
        ("This is a test with a OOo footnote\u0002, which is denoted by 0x2 in the text.", 0),
        ("A sentence ' with ' ten \" incorrect \" examples of ’ using ’ quotation “ marks ” at « once » in it.", 10),
        ("A sentence ' with' one examples of wrong quotations marks in it.", 1),
        ("A sentence 'with ' one examples of wrong quotations marks in it.", 1),
        ("Ellipsis . . . as suggested by The Chicago Manual of Style", 3),
        ("Ellipsis . . . . as suggested by The Chicago Manual of Style", 4),
    ])
    def test_rule_count(self, text, expected):
        self.assert_matches(text, expected)

    @pytest.mark.parametrize('text', [
        "Die Vertriebsniederlassu­ng der Versorgungstechnik..­.",
        "Die Vertriebsniederlassu­ng der Versorgungstechnik..­.\n",
    ])
    def test_rule_for_text(self, text):
        self.assert_matches_for_text(text, 1)

    def test_positions_and_suggestions(self):
        rule, lt = self.rule, self.lt
        matches = rule.match(lt.get_analyzed_sentence("ABB (  z.B. )"))
        assert len(matches) == 2
        assert matches[0].from_pos == 4
        assert matches[0].to_pos == 6
        assert matches[1].from_pos == 11
        assert matches[1].to_pos == 13

        matches = rule.match(lt.get_analyzed_sentence("This ,"))
        assert len(matches) == 1
        assert matches[0].suggested_replacements[0] == ","
        matches = rule.match(lt.get_analyzed_sentence("This ,is a test sentence."))
        assert len(matches) == 2
        assert matches[0].suggested_replacements[0] == ", "
        matches = rule.match(lt.get_analyzed_sentence("This , is a test sentence."))
        assert len(matches) == 1
        assert matches[0].suggested_replacements[0] == ","
        matches = rule.match(lt.get_analyzed_sentence("You \" fixed\" it."))
        assert len(matches) == 1
        assert matches[0].suggested_replacements[0] == "\" "
        assert matches[0].suggested_replacements[1] == " \""
        assert matches[0].from_pos == 3
        assert matches[0].to_pos == 6
        matches = rule.match(lt.get_analyzed_sentence("You \"fixed \" it."))
        assert len(matches) == 1
        assert matches[0].suggested_replacements[0] == "\" "
        assert matches[0].suggested_replacements[1] == " \""
        assert matches[0].from_pos == 10
        assert matches[0].to_pos == 13


# --- DoublePunctuationRuleTest -----------------------------------------------

@pytest.mark.parametrize('text', [
    "This is a test sentence...",
    "Это тестовое предложение?..",
    "Это тестовое предложение!.. ",
    "This is a test sentence... More stuff....",
    "This is a test sentence..... More stuff....",
    "This, is, a test sentence.",
    "The path is ../data/vtest.avi",
    "The path is ..\\data\\vtest.avi",
    "Something … … ..",
    "Something … … ... …",
    "Something … … .... …",
    "Something … … .. …",
    "Something ……..",
])
def test_double_punctuation_correct(demo_lt, text):
    rule = DoublePunctuationRule(en_messages())
    assert len(rule.match(demo_lt.get_analyzed_sentence(text))) == 0


def test_double_punctuation_errors(demo_lt):
    rule = DoublePunctuationRule(en_messages())
    matches1 = rule.match(demo_lt.get_analyzed_sentence("This,, is a test sentence."))
    assert len(matches1) == 1
    assert matches1[0].from_pos == 4
    assert matches1[0].to_pos == 6
    matches2 = rule.match(demo_lt.get_analyzed_sentence("This is a test sentence.. Another sentence"))
    assert len(matches2) == 1
    assert matches2[0].from_pos == 23
    assert matches2[0].to_pos == 25


# --- UppercaseSentenceStartRuleTest ------------------------------------------

class TestUppercaseSentenceStartRule:

    @pytest.fixture(autouse=True)
    def setup(self, demo_lt, demo_language):
        self.rule = UppercaseSentenceStartRule(en_messages(), demo_language)
        self.lt = demo_lt

    @pytest.mark.parametrize('text', [
        "this",
        "a) This is a test sentence.",
        "iv. This is a test sentence...",
        "\"iv. This is a test sentence...\"",
        "»iv. This is a test sentence...",
        "This",
        "This is",
        "This is a test sentence",
        "",
        "http://www.languagetool.org",
        "eBay can be at sentence start in lowercase.",
        "¿Esto es una pregunta?",
        "¿Esto es una pregunta?, ¿y esto?",
        "ø This is a test sentence with a wrong bullet character.",
    ])
    def test_good(self, text):
        matches = self.rule.match(self.lt.analyze_text(text))
        assert len(matches) == 0, matches

    def test_bad_positions(self):
        matches = self.rule.match(self.lt.analyze_text("this is a test sentence."))
        assert len(matches) == 1
        assert matches[0].from_pos == 0
        assert matches[0].to_pos == 4
        matches2 = self.rule.match(self.lt.analyze_text("this!"))
        assert len(matches2) == 1
        assert matches2[0].from_pos == 0
        assert matches2[0].to_pos == 4

    @pytest.mark.parametrize('text', [
        "'this is a sentence'.",
        "\"this is a sentence.\"",
        "„this is a sentence.",
        "«this is a sentence.",
        "‘this is a sentence.",
        "¿esto es una pregunta?",
        ("¿Esto es una pregunta? ¿y esto?"),
    ])
    def test_bad(self, text):
        assert len(self.rule.match(self.lt.analyze_text(text))) == 1


# --- MultipleWhitespaceRuleTest ----------------------------------------------

class TestMultipleWhitespaceRule:

    @pytest.fixture(autouse=True)
    def setup(self, demo_language):
        lt = new_demo_lt()
        disable_all_rules(lt)
        lt.add_rule(MultipleWhitespaceRule(en_messages(), demo_language))
        self.lt = lt

    @pytest.mark.parametrize('text', [
        "This is a test sentence.",
        "This﻿ is a test sentence.",
        "This﻿﻿ is a test sentence.",
        "This ﻿is a test sentence.",
        "This﻿⁠ is a test sentence.",
        "﻿﻿This is a\n⁠\ntest sentence...",
        "This is a test sentence...",
        "\n\tThis is a test sentence...",
        "Multiple tabs\t\tare okay",
        "\n This is a test sentence...",
        "\n    This is a test sentence...",
    ])
    def test_good(self, text):
        assert len(self.lt.check(text)) == 0

    def test_bad(self):
        lt = self.lt
        matches = lt.check("This  is a test sentence.")
        assert len(matches) == 1
        assert (matches[0].from_pos, matches[0].to_pos) == (4, 6)
        matches = lt.check("\n   This  is a test sentence.")
        assert len(matches) == 1
        assert (matches[0].from_pos, matches[0].to_pos) == (8, 10)
        matches = lt.check("This is a test   sentence.")
        assert len(matches) == 1
        assert (matches[0].from_pos, matches[0].to_pos) == (14, 17)
        matches = lt.check("This is   a  test   sentence.")
        assert len(matches) == 3
        assert (matches[0].from_pos, matches[0].to_pos) == (7, 10)
        assert (matches[1].from_pos, matches[1].to_pos) == (11, 13)
        assert (matches[2].from_pos, matches[2].to_pos) == (17, 20)
        matches = lt.check("\t\t\t    \t\t\t\t  ")
        assert len(matches) == 2
        # with non-breakable spaces
        matches = lt.check("This  is a test sentence.")
        assert len(matches) == 1
        assert (matches[0].from_pos, matches[0].to_pos) == (4, 6)


# --- SentenceWhitespaceRuleTest ----------------------------------------------

class TestSentenceWhitespaceRule:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.rule = SentenceWhitespaceRule(en_messages())
        self.lt = new_fake_lt()
        self.lt.add_rule(self.rule)

    @pytest.mark.parametrize('text', [
        "This is a text. And there's the next sentence.",
        "This is a text! And there's the next sentence.",
        "This is a text\nAnd there's the next sentence.",
        "This is a text\n\nAnd there's the next sentence.",
        "This is a text.\n And there's the next sentence.",
        "This is a text.\n\n And there's the next sentence.",
        "This is a text.  \n\n And there's the next sentence.",
        "This is a text.  \n And there's the next sentence.",
        "This is a text. \n\n  And there's the next sentence.",
        "This is a text.\rAnd there's the next sentence.",
        "This is a text.\r And there's the next sentence.",
        "This is a text.  \r And there's the next sentence.",
        "This is a text.\r\nAnd there's the next sentence.",
        "This is a text.\r\n And there's the next sentence.",
        "This is a text.  \r\n And there's the next sentence.",
        ("This is a text. \r\n  And there's the next sentence."),
        "This is a text.\u2028And there's the next sentence.",
        "This is a text.  \u2028 And there's the next sentence.",
        "This is a text.\u2029And there's the next sentence.",
        "This is a text.  \u2029 And there's the next sentence.",
        "This is a text.\u0085And there's the next sentence.",
        "This is a text.  \u0085 And there's the next sentence.",
        "This is a text.\fAnd there's the next sentence.",
        "This is a text.  \f And there's the next sentence.",
        "This is a text.\u000BAnd there's the next sentence.",
        "This is a text.  \u000B And there's the next sentence.",
    ])
    def test_good(self, text):
        assert len(self.lt.check(text)) == 0

    @pytest.mark.parametrize('text', [
        ("This is a text.And there's the next sentence."),
        ("This is a text!And there's the next sentence."),
        ("This is a text?And there's the next sentence."),
        "This is a text.  And there's the next sentence.",
        "This is a text!   And there's the next sentence.",
    ])
    def test_bad(self, text):
        assert len(self.lt.check(text)) == 1

    def test_positions(self):
        matches = self.lt.check("This is a text.  And there's the next sentence.")
        assert matches[0].from_pos == 15
        assert matches[0].to_pos == 17
        assert matches[0].suggested_replacements[0] == " "

    def test_two_spaces_allowed_good(self):
        rule = SentenceWhitespaceRule(en_messages(), max_spaces_between_sentences=2)
        lt = new_fake_lt()
        lt.add_rule(rule)
        assert len(lt.check("This is a text.  And there's the next sentence.")) == 0

    def test_two_spaces_allowed_bad(self):
        rule = SentenceWhitespaceRule(en_messages(), max_spaces_between_sentences=2)
        lt = new_fake_lt()
        lt.add_rule(rule)
        assert len(lt.check("This is a text.   And there's the next sentence.")) == 1


# --- WordRepeatRuleTest ------------------------------------------------------

@pytest.mark.parametrize('text,expected', [
    ("A test", 0),
    ("A test.", 0),
    ("A test...", 0),
    ("1 000 000 years", 0),
    ("010 020 030", 0),
    ("\U0001F44D\U0001F49A\U0001F332\U0001F332", 0),  # 👍💚🌲🌲
    ("A A test", 1),
    ("A a test", 1),
    ("This is is a test", 1),
])
def test_word_repeat_rule(demo_lt, demo_language, text, expected):
    rule = WordRepeatRule(en_messages(), demo_language)
    assert len(rule.match(demo_lt.get_analyzed_sentence(text))) == expected


# --- GenericUnpairedBracketsRuleTest -----------------------------------------

def _brackets_lt():
    lt = new_fake_lt()
    disable_all_rules(lt)
    lt.add_rule(GenericUnpairedBracketsRule(en_messages(), start_symbols=["»"], end_symbols=["«"]))
    return lt


@pytest.fixture(scope='module')
def brackets_lt():
    return _brackets_lt()


@pytest.mark.parametrize('expected,text', [
    (0, "This is »correct«."),
    (0, "»Correct«\n»And »here« it ends.«"),
    (0, "»Correct. This is more than one sentence.«"),
    (0, "»Correct. This is more than one sentence.«\n»And »here« it ends.«"),
    (0, "»Correct«\n\n»And here it ends.«\n\nMore text."),
    (0, "»Correct, he said. This is the next sentence.« Here's another sentence."),
    (0, "»Correct, he said.\n\nThis is the next sentence.« Here's another sentence."),
    (0, "»Correct, he said.\n\n\n\nThis is the next sentence.« Here's another sentence."),
    (0, "This »is also »correct««."),
    (0, "Good.\n\nThis »is also »correct««."),
    (0, "Good.\n\n\nThis »is also »correct««."),
    (0, "Good.\n\n\n\nThis »is also »correct««."),
    (0, "This is funny :-)"),
    (0, "This is sad :-( isn't it"),
    (0, "This is funny :)"),
    (0, "This is sad :( isn't it"),
    (0, "a) item one\nb) item two"),
    (0, "a) item one\nb) item two\nc) item three"),
    (0, "\na) item one\nb) item two\nc) item three"),
    (0, "\n\na) item one\nb) item two\nc) item three"),
    (0, "This is a), not b)"),
    (0, "This is it (a, not b) some more test"),
    (0, "This is »not an error yet"),
    (0, "See https://de.wikipedia.org/wiki/Schlammersdorf_(Adelsgeschlecht)"),
    (1, "This is not correct«"),
    (1, "This is »not correct."),
    (1, "This is »not an error yet\n\nBut now it has become one"),
    (1, "This is correct.\n\n»But this is not."),
    (1, "This is correct.\n\nBut this is not«"),
    (1, "»This is correct«\n\nBut this is not«"),
    (1, "»This is correct«\n\nBut this »is« not«"),
    (1, "This is not correct. No matter if it's more than one sentence«"),
    (1, "»This is not correct. No matter if it's more than one sentence"),
    (1, "Correct, he said. This is the next sentence.« Here's another sentence."),
    (1, "»Correct, he said. This is the next sentence. Here's another sentence."),
    (1, "»Correct, he said. This is the next sentence.\n\nHere's another sentence."),
    (1, "»Correct, he said. This is the next sentence.\n\n\n\nHere's another sentence."),
])
def test_unpaired_brackets_rule(brackets_lt, expected, text):
    matches = brackets_lt.check(text)
    assert len(matches) == expected, matches


def test_unpaired_brackets_match_positions(brackets_lt):
    lt = brackets_lt
    match1 = lt.check("This »is a test.")[0]
    assert match1.from_pos == 5
    assert match1.to_pos == 6
    assert match1.line == 0
    assert match1.end_line == 0
    assert match1.column == 5
    assert match1.end_column == 6
    match2 = lt.check("This.\nSome stuff.\nIt »is a test.")[0]
    assert match2.from_pos == 21
    assert match2.to_pos == 22
    assert match2.line == 2  # first line is 0
    assert match2.end_line == 2
    assert match2.column == 4
    assert match2.end_column == 5
    match3 = lt.check("Th­is »is a test.")[0]
    assert match3.from_pos == 6
    assert match3.to_pos == 7


# --- LongSentenceRuleTest ----------------------------------------------------

def _assert_no_match(text, rule, lt):
    assert len(rule.match(lt.analyze_text(text))) == 0


def _assert_match(text, from_pos, to_pos, rule, lt):
    matches = rule.match(lt.analyze_text(text))
    assert len(matches) == 1, matches
    assert matches[0].from_pos == from_pos
    assert matches[0].to_pos == to_pos


_A44 = ("a a a a a a a a a a a " * 4)
_QUOTE_TEXT = ("The quote {0}When days grow dark and nights grow dreary, we can be thankful that our God combines in "
               "his nature a creative synthesis of love and justice which will lead us through life’s dark valleys "
               "and into sunlit pathways of hope and fulfillment{1} (p. 9) refers to God’s nature as a combination "
               "of love and justice.")


@pytest.mark.parametrize('text,span', [
    (" is a rather short text.", None),
    ("Now this is not " + _A44 + "rather that short text.", (0, 127)),
    ("Now this is not " + _A44 + "rather that short text", (0, 126)),
    ("The sun slowly set behind the majestic mountains, "
     "casting a warm golden glow over the tranquil valley below, where a "
     "gentle breeze rustled the leaves of the trees, and the sound of a "
     "distant stream provided a soothing backdrop to the peaceful scene.", (0, 249)),
    # test quotes
    (_QUOTE_TEXT.format('“', '”'), None),
    (_QUOTE_TEXT.format('"', '"'), None),
    (_QUOTE_TEXT.format('«', '»'), None),
    (_QUOTE_TEXT.format('„', '“'), None),
    pytest.param("The quote \"When days\" grow dark and nights grow dreary, we can be thankful that our God combines in "
     "his nature a creative synthesis of love and justice which will lead us through life’s dark valleys and into "
     "sunlit pathways of hope \"and fulfillment\" (p. 9) refers to God’s nature as a combination of love and "
     "justice.", (0, 253)),
    # no quotes
    (_QUOTE_TEXT.format('', ''), (0, 249)),
    # wrong or mismatched quotes: opening quote, with no closing quote
    (_QUOTE_TEXT.format('“', '»'), None),
])
def test_long_sentence_rule_40(demo_lt, text, span):
    rule = LongSentenceRule(en_messages(), max_words=40)
    if span is None:
        _assert_no_match(text, rule, demo_lt)
    else:
        _assert_match(text, span[0], span[1], rule, demo_lt)


@pytest.mark.parametrize('text,span', [
    ("This is a rather short text.", None),
    ("This is also a rather short text.", (0, 33)),
    ("These ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ don't count.", None),
    ("one two three four five six.", None),
    ("one two three (four) five six.", None),
    ("one two three four five six seven.", (0, 34)),
    ("Eins zwei drei vier fünf sechs.", None),
    ("\n\n\nEins zwei drei vier fünf sechs seven", (3, 39)),
    ("Eins zwei drei vier fünf sechs seven\n\n\n", (0, 36)),
    ("\n\n\nEins zwei drei vier fünf sechs seven\n\n\n", (3, 39)),
    ("\n\n\nEins zwei drei vier fünf sechs seven.", (3, 40)),
    ("Eins zwei drei vier fünf sechs seven.\n\n\n", (0, 37)),
    ("\n\n\nEins zwei drei vier fünf sechs seven.\n\n\n", (3, 40)),
])
def test_long_sentence_rule_6(demo_lt, text, span):
    rule = LongSentenceRule(en_messages(), max_words=6)
    if span is None:
        _assert_no_match(text, rule, demo_lt)
    else:
        _assert_match(text, span[0], span[1], rule, demo_lt)


# --- LongParagraphRuleTest ---------------------------------------------------

@pytest.mark.parametrize('text,expected', [
    ("This is a short paragraph.", 0),
    ("This is only almost long paragraph by unit test standards.", 0),
    ("Here's some text as a filler. This is a long paragraph by unit test standards.", 1),
    ("Here's some text as a filler.  A test. A long paragraph by unit test standards.", 1),
    ("Here's some text as a filler.  A test.\nNot a long paragraph.\nBecause of the line breaks.\n", 0),
    ("- [ ] A test.\n- [ ] Not a long paragraph.\n- [ ] Because of the line breaks.\n- [ ] More text even.\n", 0),
])
def test_long_paragraph_rule_count(demo_lt, demo_language, text, expected):
    rule = LongParagraphRule(en_messages(), demo_language, default_words=6)
    assert len(rule.match(demo_lt.analyze_text(text))) == expected


def test_long_paragraph_rule_positions(demo_lt, demo_language):
    rule = LongParagraphRule(en_messages(), demo_language, default_words=6)
    text1 = "This is a short paragraph.\n\nHere's some text as filler. This is a long paragraph by unit test standards."
    matches1 = rule.match(demo_lt.analyze_text(text1))
    assert len(matches1) == 1
    assert matches1[0].from_pos == 45  # "filler"
    assert matches1[0].to_pos == 54
    text2 = ("Here's some text as filler. This is a long paragraph by unit test standards.\n\nAnother paragraph.\n\n"
             "Here's some text as morefiller - this is a long paragraph by unit test standards.")
    matches2 = rule.match(demo_lt.analyze_text(text2))
    assert len(matches2) == 2
    assert matches2[0].from_pos == 17  # "filler"
    assert matches2[0].to_pos == 26
    assert matches2[1].from_pos == 115  # "morefiller"
    assert matches2[1].to_pos == 128


# --- PunctuationMarkAtParagraphEndTest ---------------------------------------

@pytest.fixture(scope='module')
def para_end_lt():
    lt = new_demo_lt()
    disable_all_rules(lt)
    rule = PunctuationMarkAtParagraphEnd(en_messages(), get_language('xx-XX'))
    rule.tags = []  # rule.setTags(Collections.emptyList())
    lt.add_rule(rule)
    return lt


@pytest.mark.parametrize('text,expected', [
    ("A paragraph.\n2. Some headline\n\n(a) A new sentence.", 0),
    ("A paragraph.\n\n2. Some headline\n\n(a) A new sentence.", 0),
    ("A paragraph.\n2.2.1 Some headline\n\n(a) A new sentence.", 0),
    ("A paragraph.\n\n2.2.1 Some headline\n\n(a) A new sentence.", 0),
    ("2. This is an item in a list", 0),
    ("2.2.2. This is an item in a list", 0),
    ("a) This is an item in a list", 0),
    ("a.) This is an item in a list", 0),
    ("✓ This is an item in a list", 0),
    ("* This is an item in a list", 0),
    ("This is a test sentence.", 0),
    ("This is a test headline", 0),
    ("This is a test sentence. This is a link: http://example.com", 0),  # no error because of colon
    ("This is a test sentence. It can be found at http://example.com/foobar", 1),
    ("This is a test sentence. And this is a second test sentence", 1),
    ("\"This is a test sentence. And this is a second test sentence", 1),
    ("This is a test sentence. And this is a second test sentence.", 0),
    ("B. v. – Beschluss vom", 0),
    ("This is a test sentence.\nAnd this is a second test sentence. Here is a dot missing", 1),
    ("This is a test sentence.\nAnd this is a second test sentence. Here is a dot missing.", 0),
    ("This is a sentence. Another one: https://languagetool.org/foo\n\nAnother sentence\n", 0),
])
def test_punctuation_mark_at_paragraph_end(para_end_lt, text, expected):
    assert len(para_end_lt.check(text)) == expected


# --- PunctuationMarkAtParagraphEnd2Test --------------------------------------

@pytest.fixture(scope='module')
def para_end2_lt():
    lt = new_demo_lt()
    disable_all_rules(lt)
    rule = PunctuationMarkAtParagraphEnd2(en_messages(), get_language('xx-XX'))
    rule.set_default_on()
    lt.add_rule(rule)
    return lt


@pytest.mark.parametrize('text,expected', [
    ("2. This is an item in a list", 0),
    ("2.2.2. This is an item in a list", 0),
    ("This is a test.", 0),
    ("This is a test", 0),  # too short
    ("This is a really nice test", 0),  # no error, might not be finished
    ("This is a really nice test, and it has enough tokens\n", 1),
    ("This is a really nice test, and it has enough tokens\n\n", 1),
    ("\"This is a really nice test, and it has enough tokens.\"\n\n", 0),
    ("\"This is a really nice test, and it has enough tokens\"\n", 0),
    ("\"This is a really nice test, and it has enough tokens\"\n\n", 0),
    ("This is a test.\n\nRegards,\nJim", 0),
    ("This is a test.\n\nRegards,\n\nJim", 0),
    ("This is a test.\n\nKind Regards,\nJim", 0),
    ("This is a test.\n\nKind Regards,\n\nJim", 0),
    ("This is a test.\n\nKind Regards,\n\nJim Tester", 0),
    ("This is a test.\n\nKind Regards,\n\nJim van Tester", 0),
    ("This is headline-style text", 0),
    ("This is headline-style text.", 0),
    ("This is headline-style text. If it gets longer, a dot is needed.", 0),
    ("This is headline-style text. If it gets longer, a dot is needed", 1),
    ("This is a test\n\nKind Regards,\n\nJim van Tester", 0),  # too short to find missing dot
    ("This is a really nice test, and it has enough tokens\n\nKind Regards,\n\nJim van Tester", 1),
])
def test_punctuation_mark_at_paragraph_end2(para_end2_lt, text, expected):
    assert len(para_end2_lt.check(text)) == expected


# --- WhitespaceBeforePunctuationRuleTest -------------------------------------

def test_whitespace_before_punctuation_okay():
    rule = WhitespaceBeforePunctuationRule(en_messages())
    sentence = AnalyzedSentence([
        AnalyzedTokenReadings(AnalyzedToken(" ", None, None), 0),
        AnalyzedTokenReadings(AnalyzedToken("%", "SYM", None), 1),
    ])
    assert len(rule.match(sentence)) == 0


def test_whitespace_before_punctuation_error():
    rule = WhitespaceBeforePunctuationRule(en_messages())
    sentence = AnalyzedSentence([
        AnalyzedTokenReadings(AnalyzedToken("2", None, None), 0),
        AnalyzedTokenReadings(AnalyzedToken(" ", None, None), 1),
        AnalyzedTokenReadings(AnalyzedToken("%", "SYM", None), 2),
    ])
    assert len(rule.match(sentence)) == 1
