"""Port of org.languagetool.tokenizers.en.EnglishWordTokenizerTest,
org.languagetool.rules.en.GoogleStyleWordTokenizerTest,
org.languagetool.tokenizers.en.TokenizeMultiwordsTest and
org.languagetool.tokenizers.EnglishSRXSentenceTokenizerTest."""

import os

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.en.tokenizers import EnglishWordTokenizer, GoogleStyleWordTokenizer
from langtool.tools import java_trim


@pytest.fixture(scope='module')
def tokenizer():
    require_dictionaries('en')
    return EnglishWordTokenizer(get_language('en').tagger)


def _str(tokens):
    # List.toString()
    return '[' + ', '.join(tokens) + ']'


@pytest.mark.parametrize('text,expected', [
    ('This is\u00a0a test', '[This,  , is, \u00a0, a,  , test]'),
    ('This\rbreaks', '[This, \r, breaks]'),
    # hyphen with no whitespace
    ('Now this is-really!-a test.', '[Now,  , this,  , is-really, !, -, a,  , test, .]'),
    # hyphen at the end of the word
    ('Now this is- really!- a test.', '[Now,  , this,  , is, -,  , really, !, -,  , a,  , test, .]'),
    # mdash
    ('Now this is—really!—a test.', '[Now,  , this,  , is, —, really, !, —, a,  , test, .]'),
    # exception
    ("fo'c'sle", "[fo'c'sle]"),
    # contractions
    ("I'm John.", "[I, 'm,  , John, .]"),
    ('You hadn’t.', '[You,  , had, n’t, .]'),
    ("We'are", "[We, ', are]"),
    ("'We're'", "[', We, 're, ']"),
    ("'We’re the best.'", "[', We, ’re,  , the,  , best, ., ']"),
    ("'Don't do it'", "[', Do, n't,  , do,  , it, ']"),
    ('‘Don’t do it’', '[‘, Do, n’t,  , do,  , it, ’]'),
    ("Don't do it", "[Do, n't,  , do,  , it]"),
    ('My address is address@email.com', '[My,  , address,  , is,  , address@email.com]'),
    ('@test@test.social you are aweesome!', '[@test@test.social,  , you,  , are,  , aweesome, !]'),
    ('My address is address@email.com or other@email.com.',
     '[My,  , address,  , is,  , address@email.com,  , or,  , other@email.com, .]'),
    ("doin' that", "[doin',  , that]"),
    ("ne’er e'er o’er jack-o'-lantern", "[ne’er,  , e'er,  , o’er,  , jack-o'-lantern]"),
    # vertical tab
    ("I'm a cool test\u000Bwith a line", "[I, 'm,  , a,  , cool,  , test, \u000B, with,  , a,  , line]"),
    ('fast⇿superfast', '[fast, ⇿, superfast]'),
])
def test_tokenize(tokenizer, text, expected):
    """EnglishWordTokenizerTest.testTokenize"""
    assert _str(tokenizer.tokenize(text)) == expected


def test_google_style_tokenize():
    """GoogleStyleWordTokenizerTest.testTokenize"""
    tokenizer = GoogleStyleWordTokenizer()
    assert tokenizer.tokenize('foo bar') == ['foo', ' ', 'bar']
    assert tokenizer.tokenize('foo-bar') == ['foo', '-', 'bar']
    assert tokenizer.tokenize("I'm here.") == ['I', "'m", ' ', 'here', '.']
    assert tokenizer.tokenize("I'll do that") == ['I', "'ll", ' ', 'do', ' ', 'that']
    assert tokenizer.tokenize("You're here") == ['You', "'re", ' ', 'here']
    assert tokenizer.tokenize("You've done that") == ['You', "'ve", ' ', 'done', ' ', 'that']


def _load_words(path):
    # TokenizeMultiwordsTest.loadWords
    import re
    lines = []
    with open(path, encoding='utf-8') as f:
        for line in f.read().splitlines():
            line = java_trim(re.sub('#.*', '', java_trim(line), count=1))
            if not line or line[0] == '#':  # ignore comments
                continue
            lines.append(line.split('\t')[0])
    return lines


def test_tokenize_multiwords(tokenizer):
    """TokenizeMultiwordsTest.testTokenize: the Java test only prints
    warnings for multi-token words in the word lists that are not in
    multiwords.txt; here the files are checked to be readable and the
    warnings are collected (not asserted, as in Java)"""
    from langtool.dictionaries import locate
    lang = get_language('en')
    multiwords = _load_words(lang.resource_path('en/multiwords.txt'))
    assert multiwords
    warnings = []
    for name in ('en/added.txt', 'en/removed.txt', 'en/hunspell/ignore.txt', 'en/hunspell/prohibit.txt',
                 'en/hunspell/prohibit_custom.txt', 'en/hunspell/spelling.txt', 'en/hunspell/spelling_custom.txt',
                 'en/hunspell/spelling_en-AU.txt', 'en/hunspell/spelling_en-CA.txt',
                 'en/hunspell/spelling_en-GB.txt', 'en/hunspell/spelling_en-NZ.txt',
                 'en/hunspell/spelling_en-US.txt', 'en/hunspell/spelling_en-ZA.txt'):
        path = lang.resource_path(name)
        if not os.path.exists(path):
            path = locate(name, lang.dictionary_path, lang.download_dictionaries)
        for word in _load_words(path):
            if word.replace('’', "'") not in multiwords:
                tokens = tokenizer.tokenize(word)
                if len(tokens) > 1 and [t for t in tokens if t != ' '] != word.split(' '):
                    warnings.append((name, word))
    assert isinstance(warnings, list)


# --- EnglishSRXSentenceTokenizerTest ---

@pytest.mark.parametrize('sentences', [
    # incomplete sentences, need to work for on-thy-fly checking of texts:
    ['What is the I.S?'],
    ['Where are the I.S and the M.Z notes? '],
    ["Here's a"],
    ["Here's a sentence. ", "And here's one that's not comp"],
    ['Or did you install it (i.e. MS Word) yourself?'],
    ['This is a sentence. '],
    ['This is a sentence. ', 'And this is another one.'],
    ['This is it. ', 'and this is another sentence.'],
    ['This is a sentence. ', 'and this is another sentence.'],
    ['This is a sentence.', "Isn't it?", 'Yes, it is.'],
    ['This is e.g. Mr. Smith, who talks slowly...', 'But this is another sentence.'],
    ['Chanel no. 5 is blah.'],
    ['Mrs. Jones gave Peter $4.5, to buy Chanel No 5.', 'He never came back.'],
    ["On p. 6 there's nothing. ", 'Another sentence.'],
    ['Leave me alone!, he yelled. ', 'Another sentence.'],
    ['"Leave me alone!", he yelled.'],
    ["'Leave me alone!', he yelled. ", 'Another sentence.'],
    ["'Leave me alone!,' he yelled. ", 'Another sentence.'],
    ['This works on the phrase level, i.e. not on the word level.'],
    ["Let's meet at 5 p.m. in the main street."],
    ['James comes from the U.K. where he worked as a programmer.'],
    ["Don't split strings like U.S.A. please."],
    ['Hello ( Hi! ) my name is Chris.'],
    ["Don't split strings like U. S. A. either."],
    ["Don't split strings like U.S.A either."],
    ["Don't split... ", 'Well you know. ', 'Here comes more text.'],
    ["Don't split... well you know. ", 'Here comes more text.'],
    ["Don't split . . . well you know. ", 'Here comes more text.'],
    ['This is a sentence. ', '.Net is a platform.'],
    ['The "." should not be a delimiter in quotes.'],
    ['"Here he comes!" she said.'],
    ['"Here he comes!", she said.'],
    ['"Here he comes." ', 'But this is another sentence.'],
    ['"Here he comes!". ', "That's what he said."],
    ['The sentence ends here. ', '(Another sentence.)'],
    ['The sentence (...) ends here.'],
    ['The sentence [...] ends here.'],
    ['The sentence ends here (...). ', 'Another sentence.'],
    # previously known failed but not now :)
    ["He won't. ", 'Really.'],
    ['He will not. ', 'Really.'],
    ["He won't go. ", 'Really.'],
    ["He won't say no.", 'Not really.'],
    ["He won't say No.", 'Not really.'],
    ["He won't say no. 5 is better. ", 'Not really.'],
    ["He won't say No. 5 is better. ", 'Not really.'],
    ['They met at 5 p.m. on Thursday.'],
    ['They met at 5 p.m. ', 'It was Thursday.'],
    ['This is it: a test.'],
    ['12) Make sure that the lamp is on. ', '12) Make sure that the lamp is on. '],
    ['He also offers a conversion table (see Cohen, 1988, p. 123). '],
    # Missing space after sentence end:
    ['James is from the Ireland!', 'He lives in Spain now.'],
    # From the abbreviation list:
    ['Jones Bros. have built a successful company.'],
    # parentheses:
    ['It (really!) works.'],
    ['It [really!] works.'],
    ['It works (really!). ', 'No doubt.'],
    ['It works [really!]. ', 'No doubt.'],
    ['It really(!) works well.'],
    ['It really[!] works well.'],
    # try to deal with at least some nbsp that appear in strange places (e.g. Google Docs, web editors)
    ['A test.\u00a0\n', 'Another test.'],
    ['A test.\u00a0', 'Another test.'],  # not clear whether this is the best behavior...
    ['A test.\n', 'Another test.'],
    ['A test. \n', 'Another test.'],
    ['A test. \n', '\n', 'Another test.'],
    ['"Here he comes."\u00a0', 'But this is another sentence.'],
    ['The new Yahoo! product is nice.'],
    ['Yahoo!, what is it?'],
    ['Yahoo!', 'What is it?'],
    ['This is a sentence.\u0002 ', 'And this is another one.'],  # footnotes in LibOO/OOo look like this
    ['Other good editions are in vol. 4.'],
    ['Other good editions are in vol. IX.'],
    ['Other good editions are in vol. I think.'],  # ambiguous
    ['Who Shall I Say is Calling & Other Stories S. Deziemianowicz, ed. (2009)'],
    ['Who Shall I Say is Calling & Other Stories S. Deziemianowicz, ed. ', 'And this is another one.'],
    ['This is a sentence written by Ed. ', 'And this is another one.'],
])
def test_srx_tokenize(sentences):
    """EnglishSRXSentenceTokenizerTest.testTokenize (single line breaks mark
    paragraphs)"""
    stokenizer = SRXSentenceTokenizer(get_language('en'))
    stokenizer.set_single_line_breaks_marks_paragraph(True)
    assert stokenizer.tokenize(''.join(sentences)) == sentences


def test_srx_tokenize_paragraphs():
    """EnglishSRXSentenceTokenizerTest.testTokenize: one/two returns =
    paragraph = new sentence"""
    lang = get_language('en')
    stokenizer = SRXSentenceTokenizer(lang)
    stokenizer.set_single_line_breaks_marks_paragraph(True)
    stokenizer2 = SRXSentenceTokenizer(lang)
    stokenizer2.set_single_line_breaks_marks_paragraph(False)
    assert stokenizer2.tokenize("He won't\n\nReally.") == ["He won't\n\n", 'Really.']
    assert stokenizer.tokenize("He won't\nReally.") == ["He won't\n", 'Really.']
    assert stokenizer2.tokenize("He won't\nReally.") == ["He won't\nReally."]
    # the default sentence tokenizer of English is the SRXSentenceTokenizer
    assert isinstance(lang.sentence_tokenizer, SRXSentenceTokenizer)
