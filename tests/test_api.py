"""Tests of the public API (langtool/__init__.py and langtool/api.py)."""

import pytest

import langtool
from langtool import api
from conftest import require_dictionaries


@pytest.fixture(scope='module')
def tool():
    require_dictionaries('en')
    return langtool.LanguageTool('en-US')


@pytest.fixture
def fresh_tool():
    require_dictionaries('en')
    return langtool.LanguageTool('en-US')


# --- module level functions --------------------------------------------------

def test_exports():
    for name in langtool.__all__:
        assert hasattr(langtool, name), name
    assert langtool.LanguageTool is api.LanguageTool
    assert langtool.Match is api.Match
    assert isinstance(langtool.__version__, str)
    assert isinstance(langtool.have_speedups(), bool)


def test_languages():
    codes = langtool.languages()
    for code in ('en-US', 'en-GB', 'de-DE', 'de-CH', 'fr', 'pl-PL', 'ca-ES-valencia', 'xx-XX'):
        assert code in codes, code
    assert len(codes) == len(set(codes))


def test_language_names():
    names = langtool.language_names()
    assert names['en-US'] == 'English (US)'
    assert names['xx-XX'] == 'Testlanguage'
    assert set(langtool.languages()) <= set(names)


@pytest.mark.parametrize('code,expected', [
    ('en-US', 'en-US'), ('en_US', 'en-US'), ('en-us', 'en-US'), ('pl-PL', 'pl-PL'), ('pl', 'pl-PL'),
    ('de-DE', 'de-DE'), ('xx', 'xx-XX'),
])
def test_get_language(code, expected):
    lang = langtool.get_language(code)
    assert lang.code == expected
    assert lang is langtool.get_language(expected)  # cached


def test_get_language_unknown():
    with pytest.raises(Exception):
        langtool.get_language('qqq-QQ')


def test_check_function():
    require_dictionaries('en')
    matches = langtool.check('He go to school.', 'en-US')
    assert [m.rule_id for m in matches] == ['HE_VERB_AGR']
    assert langtool.check('He goes to school.', 'en-US') == []


# --- LanguageTool.check -------------------------------------------------------

def test_language_code(tool):
    assert tool.language_code == 'en-US'
    assert tool.language.code == 'en-US'


@pytest.mark.parametrize('text', ['', ' ', '\n\n', 'This is a correct sentence.',
                                  'This is a test. And another one.\n\nA new paragraph.'])
def test_check_no_matches(tool, text):
    assert tool.check(text) == []


def test_match_fields(tool):
    text = 'He go to school.'
    matches = tool.check(text)
    assert len(matches) == 1
    m = matches[0]
    assert isinstance(m, langtool.Match)
    assert m.rule_id == 'HE_VERB_AGR'
    assert m.sub_id is not None
    assert m.full_rule_id == 'HE_VERB_AGR[%s]' % m.sub_id
    assert (m.offset, m.length, m.end) == (3, 2, 5)
    assert m.context == 'go'
    assert m.replacements[:1] == ['goes']
    assert '<suggestion>' not in m.message and '</suggestion>' not in m.message
    assert m.rule_description
    assert m.category == 'GRAMMAR'
    assert m.category_name
    assert m.issue_type == 'Grammar'
    assert m.type == 'Other'
    assert m.sentence == text
    assert (m.line, m.column, m.end_line, m.end_column) == (0, 4, 0, 6)
    assert m.rule.get_id() == m.rule_id
    d = m.as_dict()
    assert 'rule' not in d
    assert d['rule_id'] == 'HE_VERB_AGR' and d['offset'] == 3 and d['length'] == 2
    assert d['replacements'] == m.replacements
    assert 'HE_VERB_AGR' in repr(m)


def test_message_suggestion_markup(tool):
    # <suggestion> tags in messages are replaced by typographic quotes
    matches = tool.check('I want too go home.')
    assert [m.rule_id for m in matches] == ['TOO_TO']
    assert matches[0].message == 'Did you mean “to go”?'
    assert matches[0].replacements == ['to go']


def test_matches_sorted_by_position(tool):
    text = 'He go to school. She go home. this is it. I want too go home.'
    matches = tool.check(text)
    offsets = [m.offset for m in matches]
    assert offsets == sorted(offsets)
    assert [m.rule_id for m in matches] == ['HE_VERB_AGR', 'HE_VERB_AGR', 'UPPERCASE_SENTENCE_START', 'TOO_TO']
    for m in matches:
        assert text[m.offset:m.end] == m.context


@pytest.mark.parametrize('prefix', [
    'This is a sentence. ',
    'This is a sentence. And another one! ',
    'First paragraph.\n\nSecond paragraph, first sentence. ',
    'Line one.\nLine two. ',
])
def test_offsets_multi_sentence(tool, prefix):
    error = 'He go to school.'
    base = tool.check(error)
    matches = tool.check(prefix + error)
    assert [(m.rule_id, m.offset - len(prefix), m.length) for m in matches] == \
        [(m.rule_id, m.offset, m.length) for m in base]
    assert matches[0].context == 'go'
    assert matches[0].sentence == error


def _line_col(text, offset):
    """line and 1-based column of a text position"""
    line = text.count('\n', 0, offset)
    start = text.rfind('\n', 0, offset) + 1
    return line, offset - start + 1


def test_line_and_column(tool):
    text = 'This is fine.\nHe go to school. And she go home.\n\nSecond  paragraph. It go away.'
    matches = tool.check(text)
    # (for "she go", CC_NNP_VBP has a higher priority than HE_VERB_AGR)
    assert [m.rule_id for m in matches] == ['HE_VERB_AGR', 'CC_NNP_VBP', 'CONSECUTIVE_SPACES', 'IT_VBZ']
    for m in matches:
        # sentence level rules: lines start at 0, columns at 1 (like LanguageTool)
        assert (m.line, m.column) == _line_col(text, m.offset), m
        assert (m.end_line, m.end_column) == _line_col(text, m.end), m
    assert [m.line for m in matches] == [1, 1, 3, 3]


def test_line_and_column_text_level_rule(tool):
    # text level rules (here UPPERCASE_SENTENCE_START): as in Java's
    # JLanguageTool.checkInternal, the column in the first line is 0-based
    text = 'this is fine.\nyes, it is.'
    matches = tool.check(text)
    assert [(m.rule_id, m.offset) for m in matches] == [('UPPERCASE_SENTENCE_START', 0),
                                                       ('UPPERCASE_SENTENCE_START', 14)]
    assert (matches[0].line, matches[0].column, matches[0].end_line, matches[0].end_column) == (0, 0, 0, 4)
    assert (matches[1].line, matches[1].column, matches[1].end_line, matches[1].end_column) == (1, 1, 1, 4)


def test_check_with_bom(tool):
    # BOM characters are treated as markup, offsets refer to the original text
    text = '﻿He go to school.'
    matches = tool.check(text)
    assert [(m.rule_id, m.offset, m.context) for m in matches] == [('HE_VERB_AGR', 4, 'go')]


# --- correct / sentences / analyze ---------------------------------------------

def test_correct(tool):
    assert tool.correct('He go to school.') == 'He goes to school.'
    assert tool.correct('I want too go home. this is  it.') == 'I want to go home. This is it.'
    assert tool.correct('This is fine.') == 'This is fine.'
    assert tool.correct('') == ''


def test_sentences(tool):
    text = 'This is a test. And this is another one!\n\nA new paragraph? Yes.'
    sentences = tool.sentences(text)
    assert sentences == ['This is a test. ', 'And this is another one!\n\n', 'A new paragraph? ', 'Yes.']
    assert ''.join(sentences) == text
    assert tool.sentences('') == []


def test_analyze(tool):
    analyzed = tool.analyze('This is a test. Another one.')
    assert len(analyzed) == 2
    first = analyzed[0]
    assert first.text == 'This is a test. '
    words = [t.token for t in first.non_blank_tokens]
    assert words == ['', 'This', 'is', 'a', 'test', '.']
    assert first.non_blank_tokens[0].is_sentence_start
    test_token = first.non_blank_tokens[4]
    assert test_token.start_pos == 10
    assert any(r.pos_tag and r.pos_tag.startswith('NN') for r in test_token.readings)
    assert analyzed[1].tokens[-1].is_paragraph_end


# --- rule configuration --------------------------------------------------------

def test_rules(tool):
    rules = tool.rules()
    assert len(rules) > 1000
    by_id = {}
    for r in rules:
        assert isinstance(r, langtool.RuleInfo)
        assert r.id and r.description
        by_id.setdefault(r.id, r)
    for rid in ('HE_VERB_AGR', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE', 'COMMA_PARENTHESIS_WHITESPACE'):
        assert rid in by_id
    assert by_id['UPPERCASE_SENTENCE_START'].category == 'CASING'
    assert not by_id['UPPERCASE_SENTENCE_START'].default_off
    assert by_id['TOO_LONG_PARAGRAPH'].default_off
    he = [r for r in rules if r.id == 'HE_VERB_AGR']
    assert len(he) > 1  # rule groups are expanded
    assert all(r.full_id.startswith('HE_VERB_AGR[') for r in he)
    assert 'HE_VERB_AGR' in repr(he[0])


def test_disable_enable_rule(fresh_tool):
    t = fresh_tool
    text = 'He go to school. this is it.'
    assert [m.rule_id for m in t.check(text)] == ['HE_VERB_AGR', 'UPPERCASE_SENTENCE_START']
    t.disable_rule('HE_VERB_AGR')
    assert 'HE_VERB_AGR' in t.disabled_rules
    assert [m.rule_id for m in t.check(text)] == ['UPPERCASE_SENTENCE_START']
    t.disable_rules(['UPPERCASE_SENTENCE_START'])
    assert t.check(text) == []
    t.enable_rule('HE_VERB_AGR')
    assert 'HE_VERB_AGR' not in t.disabled_rules
    assert 'HE_VERB_AGR' in t.enabled_rules
    assert [m.rule_id for m in t.check(text)] == ['HE_VERB_AGR']


def test_enable_default_off_rule(fresh_tool):
    t = fresh_tool
    # LongParagraphRule is off by default (and picky)
    text = ' '.join(['This is a sentence with a few words in it.'] * 30)
    assert 'TOO_LONG_PARAGRAPH' not in [m.rule_id for m in t.check(text)]
    t.enable_rule('TOO_LONG_PARAGRAPH')
    t.picky = True
    assert t.picky
    assert 'TOO_LONG_PARAGRAPH' in [m.rule_id for m in t.check(text)]


def test_picky(fresh_tool):
    t = fresh_tool
    assert not t.picky
    picky_ids = {r.id for r in t.rules() if 'picky' in r.tags and not r.default_off}
    assert 'TOO_LONG_SENTENCE' in picky_ids
    long_text = 'This ' + 'is a very long sentence and ' * 12 + 'it ends here.'
    assert 'TOO_LONG_SENTENCE' not in [m.rule_id for m in t.check(long_text)]
    t.picky = True
    assert 'TOO_LONG_SENTENCE' in [m.rule_id for m in t.check(long_text)]
    t.picky = False
    assert 'TOO_LONG_SENTENCE' not in [m.rule_id for m in t.check(long_text)]


def test_picky_constructor():
    require_dictionaries('en')
    t = langtool.LanguageTool('en-US', picky=True)
    assert t.picky


def test_disable_enable_category(fresh_tool):
    t = fresh_tool
    text = 'He go to school. this is it.'
    t.disable_category('GRAMMAR')
    assert [m.rule_id for m in t.check(text)] == ['UPPERCASE_SENTENCE_START']
    t.enable_category('GRAMMAR')
    assert [m.rule_id for m in t.check(text)] == ['HE_VERB_AGR', 'UPPERCASE_SENTENCE_START']


def test_unsupported_components(tool):
    u = tool.unsupported_components()
    assert set(u) == {'components', 'skipped_rules'}
    # English is ported completely
    assert u == {'components': [], 'skipped_rules': []}
    require_dictionaries('de')
    u = langtool.LanguageTool('de-DE').unsupported_components()
    # the German tagger, synthesizer and word tokenizer are ported
    assert not [c for c in u['components'] if c[0] in ('tagger', 'synthesizer', 'word_tokenizer')]


def test_other_language():
    require_dictionaries('pl')
    t = langtool.LanguageTool('pl-PL')
    assert t.language_code == 'pl-PL'
    assert t.check('To jest dobre zdanie.') == []
    matches = t.check('to jest zdanie.')
    assert [m.rule_id for m in matches] == ['UPPERCASE_SENTENCE_START']
    assert matches[0].replacements == ['To']


def test_demo_language_via_api():
    t = langtool.LanguageTool('xx-XX')
    matches = t.check('This is my test.')
    assert [m.full_rule_id for m in matches] == ['test_unification_with_negation[1]']


def test_to_advanced_typography():
    """Language.toAdvancedTypography()"""
    from langtool.api import get_language
    en = get_language('en-US')
    assert en.to_advanced_typography('Use <suggestion>x</suggestion> here.') == 'Use “x” here.'
    # the suggestions are found in the input (Java: the matcher is not updated after the replacements), so the
    # second one is preserved too
    assert en.to_advanced_typography("Is it <suggestion>a’b</suggestion> or <suggestion>a'b</suggestion>?") == \
        "Is it “a’b” or “a'b”?"
    be = get_language('be-BY')
    assert be.is_advanced_typography_enabled()
    assert be.to_advanced_typography("Гэта 'x'... і \"y\", <suggestion>z</suggestion>") == \
        'Гэта ‘x’… і «y», «z»'
