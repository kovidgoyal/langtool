"""Chunk tags, port of org.languagetool.chunking.ChunkTag."""

from . import jregex
from .openregex import BaseExpression, LogicExpression, Pred


class ChunkTag:
    __slots__ = ('chunk_tag', 'is_regexp', '_pattern')

    def __init__(self, chunk_tag, is_regexp=False):
        if chunk_tag is None or not chunk_tag.strip():
            raise ValueError('chunkTag cannot be null or empty: %r' % chunk_tag)
        self.chunk_tag = chunk_tag
        self.is_regexp = is_regexp
        self._pattern = None

    @property
    def pattern(self):
        if self.is_regexp and self._pattern is None:
            self._pattern = jregex.compile(self.chunk_tag)
        return self._pattern

    def matches(self, tag):
        if self.is_regexp:
            return self.pattern.fullmatch(tag.chunk_tag) is not None
        return self.chunk_tag == tag.chunk_tag

    def __eq__(self, o):
        if self is o:
            return True
        if not isinstance(o, ChunkTag):
            return NotImplemented
        return self.chunk_tag == o.chunk_tag

    def __hash__(self):
        return hash(self.chunk_tag)

    def __repr__(self):
        return self.chunk_tag + ('[regex]' if self.is_regexp else '')

    __str__ = __repr__


class ChunkTaggedToken:
    """Port of org.languagetool.chunking.ChunkTaggedToken: a token with its
    chunk tags and its readings (which may be None)."""

    __slots__ = ('token', 'chunk_tags', 'readings')

    def __init__(self, token, chunk_tags, readings):
        if token is None or chunk_tags is None:
            raise ValueError('token and chunk_tags must not be None')
        self.token = token
        self.chunk_tags = list(chunk_tags)
        self.readings = readings

    def get_token(self):
        return self.token

    def get_chunk_tags(self):
        return self.chunk_tags

    def get_readings(self):
        return self.readings

    def __repr__(self):
        return self.token + '/' + ','.join(str(c) for c in self.chunk_tags)

    __str__ = __repr__


def _unquote(s):
    return s[1:-1] if len(s) >= 2 and s.startswith("'") and s.endswith("'") else s


class TokenPredicate(Pred):
    """Port of org.languagetool.chunking.TokenPredicate: an argument of the
    logic expressions of TokenExpressionFactory, matching a ChunkTaggedToken.
    Syntax: <string|regex|regexCS|chunk|pos|posregex|posre=value> (values
    may be quoted with single quotes); without a type, the value is
    compared with the token ("string")."""

    def __init__(self, description, case_sensitive):
        from .patterns import string_matcher
        from .tools import java_split
        super().__init__(description)
        parts = java_split(description, '=')
        if len(parts) == 1:
            expr_type, expr_value = 'string', _unquote(parts[0])
        elif len(parts) == 2:
            expr_type, expr_value = parts[0], _unquote(parts[1])
        else:
            raise ValueError('Could not parse expression: ' + description)
        if expr_type in ('string', 'regex', 'regexCS'):
            matcher = string_matcher.create(expr_value, expr_type != 'string',
                                            case_sensitive or expr_type == 'regexCS')
            self._test = lambda t: matcher.matches(t.token)
        elif expr_type == 'chunk':
            chunk_pattern = string_matcher.regexp(expr_value)
            self._test = lambda t: any(chunk_pattern.matches(c.chunk_tag) for c in t.chunk_tags)
        elif expr_type == 'pos':
            def test(t):
                if t.readings is not None:
                    for at in t.readings.readings:
                        if at.pos_tag is not None and expr_value in at.pos_tag:
                            return True
                return False
            self._test = test
        elif expr_type in ('posre', 'posregex'):
            pos_pattern = string_matcher.regexp(expr_value)

            def test(t):
                if t.readings is not None:
                    for at in t.readings.readings:
                        if at.pos_tag is not None and pos_pattern.matches(at.pos_tag):
                            return True
                return False
            self._test = test
        else:
            raise ValueError("Expression type not supported: '" + expr_type + "'")

    def apply(self, chunk_tagged_token):
        return self._test(chunk_tagged_token)


class TokenExpressionFactory:
    """Port of org.languagetool.chunking.TokenExpressionFactory: creates the
    token expressions of OpenRegex regular expressions over ChunkTaggedTokens
    (langtool.openregex.RegularExpression.compile(expr, factory.create)):
    logic expressions of TokenPredicates, e.g. <posre='ADJ:.*' & !pos=PREP>.
    case_sensitive: whether word tokens are compared case-sensitively (also
    used for regular expressions)."""

    def __init__(self, case_sensitive):
        self.case_sensitive = case_sensitive

    def create(self, expr):
        logic_expression = LogicExpression.compile(expr, lambda s: TokenPredicate(s, self.case_sensitive))
        return BaseExpression(expr, logic_expression.apply)

    __call__ = create
