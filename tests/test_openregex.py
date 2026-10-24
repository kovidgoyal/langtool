"""Tests of langtool.openregex, the port of OpenRegex
(edu.washington.cs.knowitall:openregex): regular expressions over
sequences of objects and logic expressions."""

import pytest

from langtool.openregex import (BaseExpression, LogicException, LogicExpression, Pred, RegexException,
                                RegularExpression)


def _word_factory(s):
    # like RegularExpressionParsers.word: <foo> matches the string "foo"
    return BaseExpression(s, lambda token: token == s)


def _compile(expr):
    return RegularExpression.compile(expr, _word_factory)


def _spans(expr, text):
    return [(m.start_index(), m.end_index()) for m in _compile(expr).find_all(text.split())]


def test_parse_to_string():
    assert str(_compile('<a> <b>* <c>+ <d>? <e>{1,3}')) == '<a> <b>* <c>+ <d>? <e>{1,3}'
    assert str(_compile('(<a> <b>) (?:<c>) (<name>:<d>)')) == '(<a> <b>) (?:<c>) (<name>:<d>)'
    assert str(_compile('^ <a> $')) == '^ <a> $'
    # the OR operator combines the last two expressions (the second one first)
    assert str(_compile('<a> | <b>')) == '<b> | <a>'
    # unary operators after an alternation apply to the alternation
    assert str(_compile('<a> | <b>*')) == '<b> | <a>*'
    assert str(_compile('[a] <b>')) == '<a> <b>'
    assert _compile('<a> <b>') == _compile('<a>   <b>')


def test_matching():
    assert _spans('<a> <b>', 'x a b a b x a') == [(1, 3), (3, 5)]
    # longest match
    assert _spans('<a> <b>*', 'a b b x a') == [(0, 3), (4, 5)]
    assert _spans('<a>+', 'a a x a') == [(0, 2), (3, 4)]
    assert _spans('<a> <b>? <c>', 'a c a b c a b') == [(0, 2), (2, 5)]
    assert _spans('(<a> | <b>) <c>', 'a c b c c') == [(0, 2), (2, 4)]
    assert _spans('<a> (<b> <c>)+', 'a b c b c b a b') == [(0, 5)]
    assert _spans('<a>{2,3}', 'a a a a a') == [(0, 3), (3, 5)]
    assert _spans('<a>{0,2} <b>', 'a a a b b') == [(1, 4), (4, 5)]
    # matches that consume no token are not matches
    assert _spans('<a>*', 'b a a b') == [(1, 3)]
    assert _spans('<a>*', '') == []
    # assertions
    assert _spans('^ <a>', 'a a') == [(0, 1)]
    assert _spans('<a> $', 'a a') == [(1, 2)]
    assert _spans('<a>{1,2} $', 'a a a') == [(1, 3)]


def test_find_and_match():
    r = _compile('<a> <b>*')
    tokens = 'x a b'.split()
    assert r.apply(tokens)
    assert not r.matches(tokens)
    assert r.matches(tokens[1:])
    assert r.match(tokens) is None
    m = r.find(tokens)
    assert (m.start_index(), m.end_index(), m.tokens(), m.length()) == (1, 3, ['a', 'b'], 2)
    assert r.find(tokens, 2) is None
    assert r.looking_at(tokens) is None
    assert r.looking_at(tokens, 1).end_index() == 3


def test_parse_errors():
    for expr in ('<a', '(<a>', '<a> |', '<a> %'):
        with pytest.raises(RegexException):
            _compile(expr)
    with pytest.raises(ValueError):
        _compile('<a>{3,2}')


class _Is(Pred):
    def apply(self, entity):
        return self.description in entity


def _logic(expr):
    return LogicExpression.compile(expr, _Is)


def test_logic_expressions():
    assert _logic('a').apply('a')
    assert not _logic('a').apply('b')
    assert _logic('a & b').apply('ab')
    assert not _logic('a & b').apply('a')
    assert _logic('a | b').apply('b')
    assert _logic('!a').apply('b')
    assert not _logic('!a & b').apply('ab')
    assert _logic('!(a & b)').apply('a')
    # & binds stronger than |, ! stronger than &
    assert _logic('a | b & c').apply('a')
    assert not _logic('(a | b) & c').apply('a')
    assert _logic('!a | b').apply('b')
    assert str(_logic('a | b & !c')) == '(a | (b & !(c)))'
    # quoted strings may contain operators and parentheses
    assert _logic("x='a & (b'").expression.description == "x='a & (b'"
    assert _logic('x="a | b" & y').expression.right.description == 'y'
    assert _logic('/a|b/').expression.description == '/a|b/'
    assert LogicExpression([]).apply('anything')
    for expr in ('a &', '& a', '(a', 'a)'):
        with pytest.raises(LogicException):
            _logic(expr)
