"""Port of OpenRegex (edu.washington.cs.knowitall:openregex 1.1.1), the
regular expression engine over sequences of arbitrary objects that the
rule based chunkers of LanguageTool (RussianChunker, GermanChunker) use via
org.languagetool.chunking.TokenExpressionFactory.

Two parts are ported:

* the logic expressions (edu.washington.cs.knowitall.logic): boolean
  expressions over arguments with ``!``, ``&``, ``|`` and parentheses, like
  ``posre='ADJ:.*' & !pos=PREP``, see LogicExpression.compile();
* the regular expressions (edu.washington.cs.knowitall.regex): sequences of
  token expressions ``<...>`` (or ``[...]``) with groups ``(...)``,
  ``(?:...)``, ``(<name>:...)``, the operators ``*``, ``+``, ``?``,
  ``{min,max}``, ``|`` and the assertions ``^`` and ``$``, compiled to an NFA
  (FiniteAutomaton) that is evaluated with the Thompson algorithm; see
  RegularExpression.compile().

The NFA is built exactly like in Java. The evaluation computes the same
result as Java's (the longest match that consumes at least one token, from
the given start index) with sets of states instead of Java's lists of
steps with back references, as the matches only report their token range
(start_index(), end_index(), tokens()): the matching groups of Java's Match
(groups(), group(name), pairs()), which LanguageTool does not use, are not
ported.
"""

from . import jregex


class RegexException(RuntimeError):
    """RegexException and TokenizationRegexException"""


class LogicException(RuntimeError):
    """LogicException (TokenizeLogicException, CompileLogicException,
    ApplyLogicException)"""


# --- logic expressions (edu.washington.cs.knowitall.logic) ---

class _Apply:
    def apply(self, entity):
        raise NotImplementedError()


class _Op(_Apply):
    precedence = 0

    def preceeds(self, that):
        return self.precedence < that.precedence


class _Not(_Op):
    precedence = 0

    def __init__(self):
        self.sub = None

    def apply(self, entity):
        return not self.sub.apply(entity)

    def __str__(self):
        return '!' if self.sub is None else '!(' + str(self.sub) + ')'


class _Bin(_Op):
    symbol = ''

    def __init__(self):
        self.left = self.right = None

    def __str__(self):
        if self.left is None or self.right is None:
            return self.symbol
        return '(' + str(self.left) + ' ' + self.symbol + ' ' + str(self.right) + ')'


class _And(_Bin):
    precedence = 1
    symbol = '&'

    def apply(self, entity):
        return self.left.apply(entity) and self.right.apply(entity)


class _Or(_Bin):
    precedence = 2
    symbol = '|'

    def apply(self, entity):
        return self.left.apply(entity) or self.right.apply(entity)


class Pred(_Apply):
    """Expression.Arg.Pred: an argument of a logic expression, a predicate
    with a description (subclasses implement apply(entity))."""

    def __init__(self, description):
        self.description = description

    def get_description(self):
        return self.description

    def __str__(self):
        return self.description


class _ParenL:
    def __str__(self):
        return '('


class _ParenR:
    def __str__(self):
        return ')'


_DOUBLE_QUOTE_STRING_LITERAL = jregex.compile(
    '"' + '([^"\\p{Cntrl}\\\\]*+(?:\\\\[\\\\\'"bfnrt])*+(?:\\\\u[a-fA-F0-9]{4})*+)*+' + '"')
_SINGLE_QUOTE_STRING_LITERAL = jregex.compile("'" + "(?:[^']*+)" + "'")
_REGEX_LITERAL = jregex.compile('/' + '(?:(?:[^/\\\\]*+(?:\\\\)*+(?:\\\\/)*+)*+)' + '/')
_LITERAL_PATTERNS = (_DOUBLE_QUOTE_STRING_LITERAL, _SINGLE_QUOTE_STRING_LITERAL, _REGEX_LITERAL)


def _read_logic_token(remainder):
    """LogicExpressionParser.readToken: the argument at the start of
    remainder (up to an unquoted '&', '|' or unbalanced ')')."""
    parens = 0
    i = 0
    n = len(remainder)
    while i < n:
        c = remainder[i]
        match = None
        for pattern in _LITERAL_PATTERNS:
            m = pattern.match(remainder, i)
            if m:
                match = m.group(0)
                break
        if match is not None:
            # we found and can consume a quotation
            i += len(match) - 1
        elif c == '(':
            parens += 1
        elif c == ')':
            if not parens:
                break
            parens -= 1
        elif c in '&|':
            break
        i += 1
    token = remainder[:i].strip()
    if not token:
        raise LogicException('zero-length token found.')
    return token


class LogicExpression:
    """Port of LogicExpression: a boolean expression of arguments (created
    with the factory, a function description -> Pred) that is applied to
    an entity."""

    def __init__(self, expressions):
        self.expression = self.build_ast(self.rpn(expressions))

    @classmethod
    def compile(cls, input_string, factory):
        return cls(cls.tokenize(input_string, factory))

    @staticmethod
    def tokenize(input_string, factory):
        """LogicExpressionParser.tokenize"""
        tokens = []
        i = 0
        while i < len(input_string):
            first_char = input_string[i]
            if first_char == ' ':
                i += 1
                continue
            if first_char == '(':
                tokens.append(_ParenL())
                i += 1
            elif first_char == ')':
                tokens.append(_ParenR())
                i += 1
            elif first_char == '!':
                tokens.append(_Not())
                i += 1
            elif first_char == '&':
                tokens.append(_And())
                i += 1
            elif first_char == '|':
                tokens.append(_Or())
                i += 1
            else:
                # parse out the token
                token = _read_logic_token(input_string[i:])
                tokens.append(factory(token))
                i += len(token)
        return tokens

    @staticmethod
    def rpn(tokens):
        """The tokens in reverse polish notation (shunting-yard)."""
        stack = []
        output = []
        for tok in tokens:
            if isinstance(tok, _ParenL):
                stack.append(tok)
            elif isinstance(tok, _ParenR):
                while True:
                    if not stack:
                        raise LogicException('Unbalanced parentheses.')  # EmptyStackException in Java
                    top = stack.pop()
                    if isinstance(top, _ParenL):
                        break
                    output.append(top)
            elif isinstance(tok, _Not):
                stack.append(tok)
            elif isinstance(tok, _Bin):
                # higher precedence
                while stack and isinstance(stack[-1], _Op) and stack[-1].preceeds(tok):
                    output.append(stack.pop())
                stack.append(tok)
            elif isinstance(tok, _Apply):
                output.append(tok)
        # empty out items remaining in the stack
        while stack:
            top = stack.pop()
            if isinstance(top, (_ParenL, _ParenR)):
                raise LogicException('Unbalanced parentheses.')
            output.append(top)
        return output

    @staticmethod
    def build_ast(rpn):
        if not rpn:
            return None
        stack = []
        for tok in rpn:
            if isinstance(tok, _Op):
                try:
                    if isinstance(tok, _Not):
                        tok.sub = stack.pop()
                    else:
                        tok.right = stack.pop()
                        tok.left = stack.pop()
                except IndexError:
                    raise LogicException('No argument for operator (stack empty): ' + str(tok))
                stack.append(tok)
            else:
                stack.append(tok)
        if len(stack) > 1:
            raise LogicException('Stack has multiple elements after apply: [%s]' % ', '.join(map(str, stack)))
        return stack.pop()

    def is_empty(self):
        return self.expression is None

    def apply(self, entity):
        if self.expression is None:
            return True
        return self.expression.apply(entity)

    def __str__(self):
        return '(empty)' if self.expression is None else str(self.expression)


# --- regular expressions (edu.washington.cs.knowitall.regex) ---

class _State:
    """FiniteAutomaton.State: consuming edges (dest, expression) and epsilon
    transitions."""

    __slots__ = ('edges', 'epsilons')

    def __init__(self):
        self.edges = []
        self.epsilons = []

    def connect(self, dest, expression=None):
        if expression is None:
            self.epsilons.append(dest)
        else:
            self.edges.append((dest, expression))


class _Automaton:
    """FiniteAutomaton.Automaton: a component automaton with a single start
    and a single end state."""

    __slots__ = ('start', 'end', 'expression')

    def __init__(self, expression):
        self.expression = expression
        self.start = _State()
        self.end = _State()

    def min_matching_length(self):
        return self.expression.min_matching_length()

    def _closure(self, states, has_start, remaining, total):
        """The states reachable with epsilon transitions and the assertions
        that pass (expandEpsilons and expandAssertions)."""
        seen = set(states)
        todo = list(states)
        while todo:
            s = todo.pop()
            for d in s.epsilons:
                if d not in seen:
                    seen.add(d)
                    todo.append(d)
            for d, expr in s.edges:
                if isinstance(expr, AssertionExpression) and d not in seen and \
                        expr.apply_assertion(has_start, remaining, total):
                    seen.add(d)
                    todo.append(d)
        return seen

    def evaluate(self, tokens, start_index, has_start):
        """The number of tokens of the longest match of tokens[start_index:]
        that consumes at least one token (0 for no match)."""
        total = len(tokens) - start_index
        states = {self.start}
        consumed = 0
        solution = 0
        end = self.end
        while states:
            states = self._closure(states, has_start, total - consumed, total)
            if end in states and consumed > 0:
                solution = consumed
            if consumed == total:
                break
            token = tokens[start_index + consumed]
            new_states = set()
            for s in states:
                for d, expr in s.edges:
                    if d not in new_states and not isinstance(expr, AssertionExpression) and expr.apply(token):
                        new_states.add(d)
            consumed += 1
            states = new_states
        return solution

    def looking_at(self, tokens, start_index=0):
        if len(tokens) - start_index - self.min_matching_length() < 0:
            # don't try if we can't possibly match
            return None
        n = self.evaluate(tokens, start_index, start_index == 0)
        if not n:
            return None
        return Match(start_index, tokens[start_index:start_index + n])


class Match:
    """Match (FinalMatch): the range of tokens matched."""

    __slots__ = ('_start_index', '_tokens')

    def __init__(self, start_index, tokens):
        self._start_index = start_index
        self._tokens = list(tokens)

    def start_index(self):
        """The index of the first token matched (inclusive start)."""
        return self._start_index

    def end_index(self):
        """The index one past the last token matched (exclusive end)."""
        return self._start_index + len(self._tokens)

    def tokens(self):
        return list(self._tokens)

    def length(self):
        return len(self._tokens)

    def is_empty(self):
        # a match always has its pairs (it consumes at least one token)
        return False

    def __repr__(self):
        return 'Match(%d, %d)' % (self.start_index(), self.end_index())


class Expression:
    """The interface Expression: a component of a regular expression."""

    def apply(self, entity):
        raise NotImplementedError()

    def build(self):
        raise NotImplementedError()

    def min_matching_length(self):
        raise NotImplementedError()


class MatchingGroup(Expression):
    """A matching group: (<foo> <bar>+)"""

    def __init__(self, expressions):
        self.expressions = list(expressions)

    def apply(self, entity):
        raise NotImplementedError()

    def subexp_string(self):
        return ' '.join(str(e) for e in self.expressions)

    def __str__(self):
        return '(' + self.subexp_string() + ')'

    def build(self):
        auto = _Automaton(self)
        prev = auto.start
        it = iter(self.expressions)
        first = next(it, None)
        if first is not None:
            # connect the start to the first subexpression
            sub = first.build()
            auto.start.connect(sub.start)
            prev = sub.end
        for expr in it:
            sub = expr.build()
            connector = _State()
            prev.connect(connector)
            connector.connect(sub.start)
            prev = sub.end
        prev.connect(auto.end)
        return auto

    def min_matching_length(self):
        return sum(e.min_matching_length() for e in self.expressions)


class NamedGroup(MatchingGroup):
    """A matching group referred to by name: (<name>:<foo> <bar>+)"""

    def __init__(self, name, expressions):
        super().__init__(expressions)
        self.name = name

    def __str__(self):
        return '(<' + self.name + '>:' + self.subexp_string() + ')'


class NonMatchingGroup(MatchingGroup):
    """A non-matching group: (?:<foo> <bar>+)"""

    def __str__(self):
        return '(?:' + self.subexp_string() + ')'


class Or(Expression):
    """Disjunction of two expressions: <foo>|<bar>"""

    def __init__(self, expr1, expr2):
        self.expr1 = expr1
        self.expr2 = expr2

    def apply(self, entity):
        return True

    def __str__(self):
        return str(self.expr1) + ' | ' + str(self.expr2)

    def build(self):
        auto = _Automaton(self)
        sub1 = self.expr1.build()
        sub2 = self.expr2.build()
        auto.start.connect(sub1.start)
        auto.start.connect(sub2.start)
        sub1.end.connect(auto.end)
        sub2.end.connect(auto.end)
        return auto

    def min_matching_length(self):
        return min(self.expr1.min_matching_length(), self.expr2.min_matching_length())


class Star(Expression):
    """Zero or more of the enclosed expression: <foo>*"""

    def __init__(self, expr):
        self.expr = expr

    def apply(self, entity):
        return self.expr.apply(entity)

    def __str__(self):
        return str(self.expr) + '*'

    def build(self):
        auto = _Automaton(self)
        sub = self.expr.build()
        sub.end.connect(sub.start)  # run it again
        auto.start.connect(sub.start)
        sub.end.connect(auto.end)
        auto.start.connect(auto.end)  # skip it completely
        return auto

    def min_matching_length(self):
        return 0


class Plus(Expression):
    """One or more of the enclosed expression: <foo>+"""

    def __init__(self, expr):
        self.expr = expr

    def apply(self, entity):
        return self.expr.apply(entity)

    def __str__(self):
        return str(self.expr) + '+'

    def build(self):
        auto = _Automaton(self)
        sub = self.expr.build()
        sub.end.connect(sub.start)  # run it again
        auto.start.connect(sub.start)
        sub.end.connect(auto.end)
        return auto

    def min_matching_length(self):
        return 1


class Option(Expression):
    """Zero or one of the enclosed expression: <foo>?"""

    def __init__(self, expr):
        self.expr = expr

    def apply(self, entity):
        return self.expr.apply(entity)

    def __str__(self):
        return str(self.expr) + '?'

    def build(self):
        auto = _Automaton(self)
        sub = self.expr.build()
        auto.start.connect(sub.start)
        sub.end.connect(auto.end)
        auto.start.connect(auto.end)  # skip it completely
        return auto

    def min_matching_length(self):
        return 0


class MinMax(Expression):
    """A minimum to maximum number of occurrences of the enclosed
    expression: <foo>{1,3}"""

    def __init__(self, expr, min_occurrences, max_occurrences):
        if min_occurrences < 0 or max_occurrences < 1:
            raise ValueError('minOccurrences must be >= 0 and maxOccurrences must be >= 1: %d, %d' % (
                min_occurrences, max_occurrences))
        if min_occurrences > max_occurrences:
            raise ValueError('minOccurrences must be <= maxOccurrences: %d > %d' % (
                min_occurrences, max_occurrences))
        self.expr = expr
        self.min_occurrences = min_occurrences
        self.max_occurrences = max_occurrences

    def apply(self, entity):
        return self.expr.apply(entity)

    def __str__(self):
        return '%s{%d,%d}' % (self.expr, self.min_occurrences, self.max_occurrences)

    def build(self):
        auto = _Automaton(self)
        sub_autos = [self.expr.build() for _ in range(self.max_occurrences)]
        auto.start.connect(sub_autos[0].start)
        for i, sub in enumerate(sub_autos):
            if i >= self.min_occurrences - 1:
                sub.end.connect(auto.end)
            if i < len(sub_autos) - 1:
                sub.end.connect(sub_autos[i + 1].start)
        if self.min_occurrences == 0:
            auto.start.connect(auto.end)  # skip it completely
        return auto

    def min_matching_length(self):
        return self.min_occurrences


class BaseExpression(Expression):
    """An expression without subexpressions that is evaluated against a
    token (subclasses or the predicate argument implement apply())."""

    def __init__(self, source, predicate=None):
        self.source = source
        self._predicate = predicate

    def apply(self, entity):
        return self._predicate(entity)

    def __str__(self):
        return '<' + self.source + '>'

    def build(self):
        auto = _Automaton(self)
        auto.start.connect(auto.end, self)
        return auto

    def min_matching_length(self):
        return 1


class AssertionExpression(Expression):
    """A non-consuming expression that matches a property of the position,
    such as the start or end of the sequence."""

    def apply(self, entity):
        return False

    def apply_assertion(self, has_start, remaining, total):
        """apply(hasStart, tokens, count) with the number of remaining
        tokens instead of the remaining tokens"""
        raise NotImplementedError()

    def build(self):
        auto = _Automaton(self)
        auto.start.connect(auto.end, self)
        return auto

    def min_matching_length(self):
        return 0


class StartAssertion(AssertionExpression):
    """^"""

    def apply_assertion(self, has_start, remaining, total):
        return has_start and remaining == total

    def __str__(self):
        return '^'


class EndAssertion(AssertionExpression):
    """$"""

    def apply_assertion(self, has_start, remaining, total):
        return remaining == 0

    def __str__(self):
        return '$'


_WHITESPACE = jregex.compile('\\s+')
_UNARY = jregex.compile('[*?+]')
_MIN_MAX = jregex.compile('\\{(\\d+),(\\d+)\\}')
_BINARY = jregex.compile('[|]')
_NAMED_GROUP = jregex.compile('<(\\w*)>:(.*)')
_UNNAMED_GROUP = jregex.compile('\\?:(.*)')


def _index_of_close(s, start, open_char, close_char):
    count = 0
    start -= 1
    while True:
        start += 1
        if start >= len(s):
            return -1
        c = s[start]
        if c == open_char:
            count += 1
        elif c == close_char:
            count -= 1
        if count <= 0:
            return start


def _read_token(remaining):
    """RegularExpressionParser.readToken"""
    c = remaining[0]
    if c == '<':
        end = _index_of_close(remaining, 0, '<', '>')
    elif c == '[':
        end = _index_of_close(remaining, 0, '[', ']')
    else:
        raise RegexException('illegal state')
    if end == -1:
        raise RegexException('bad token. Non-matching brackets (<> or []): 0:"' + remaining + '"')
    return remaining[:end + 1]


def tokenize(string, factory):
    """RegularExpressionParser.tokenize: the expressions of a regular
    expression string; factory creates a BaseExpression from the text
    between the angle (or square) brackets of a token."""
    expressions = []
    stack = ' '
    start = 0
    n = len(string)
    while start < n:
        m = _WHITESPACE.match(string, start)
        if m:
            # skip whitespace
            start = m.end()
            continue
        c = string[start]
        if c in '(<[$^':
            if c == '(':
                # group
                end = _index_of_close(string, start, '(', ')')
                if end == -1:
                    raise RegexException('unclosed parenthesis: %d:"%s)"' % (start, string[start:]))
                group = string[start + 1:end]
                start = end + 1
                gm = _NAMED_GROUP.fullmatch(group)
                if gm:
                    # named group (matching)
                    expressions.append(NamedGroup(gm.group(1), tokenize(gm.group(2), factory)))
                else:
                    gm = _UNNAMED_GROUP.fullmatch(group)
                    if gm:
                        # unnamed group
                        expressions.append(NonMatchingGroup(tokenize(gm.group(1), factory)))
                    else:
                        # group (matching)
                        expressions.append(MatchingGroup(tokenize(group, factory)))
            elif c in '<[':
                token = _read_token(string[start:])
                try:
                    # strip off enclosing characters
                    expressions.append(factory(token[1:-1]))
                except Exception as e:
                    raise RegexException('error parsing token: ' + token) from e
                start += len(token)
            elif c == '^':
                expressions.append(StartAssertion())
                start += 1
            else:
                expressions.append(EndAssertion())
                start += 1
            # check if we have a floating OR operator
            if stack == '|':
                stack = ' '
                if len(expressions) < 2:
                    raise RegexException('error parsing OR (|) operator.')
                expr1 = expressions.pop()
                expr2 = expressions.pop()
                expressions.append(Or(expr1, expr2))
            continue
        m = _UNARY.match(string, start)
        if m:
            # unary operator, applied to the last expression
            base = expressions.pop()
            op = m.group(0)
            if op == '?':
                expressions.append(Option(base))
            elif op == '*':
                expressions.append(Star(base))
            else:
                expressions.append(Plus(base))
            start = m.end()
            continue
        m = _MIN_MAX.match(string, start)
        if m:
            # min/max operator "{x,y}"
            base = expressions.pop()
            expressions.append(MinMax(base, int(m.group(1)), int(m.group(2))))
            start = m.end()
            continue
        m = _BINARY.match(string, start)
        if m:
            # binary operator (alternation)
            stack = '|'
            start = m.end()
            continue
        raise RegexException('unknown symbol: ' + string[start:])
    if stack == '|':
        raise RegexException('OR remains on the stack.')
    return expressions


class RegularExpression:
    """Port of RegularExpression: a regular expression over sequences of
    objects."""

    def __init__(self, expressions):
        self.expressions = list(expressions)
        self.auto = MatchingGroup(self.expressions).build()

    @classmethod
    def compile(cls, expression, factory):
        """Compile an expression string; factory creates a BaseExpression
        from the text of a token (e.g. TokenExpressionFactory.create)."""
        return cls(tokenize(expression, factory))

    def __str__(self):
        return ' '.join(str(e) for e in self.expressions)

    def __eq__(self, other):
        return isinstance(other, RegularExpression) and str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def apply(self, tokens):
        """Whether the expression is found within the tokens."""
        return self.find(tokens) is not None

    def matches(self, tokens):
        """Whether the expression matches all of the tokens."""
        m = self.looking_at(tokens, 0)
        return m is not None and m.end_index() == len(tokens)

    def find(self, tokens, start=0):
        """The first match at or after start, or None."""
        for i in range(start, len(tokens) - self.auto.min_matching_length() + 1):
            m = self.looking_at(tokens, i)
            if m is not None:
                return m
        return None

    def looking_at(self, tokens, start=0):
        """The match starting at start, or None."""
        return self.auto.looking_at(tokens, start)

    def match(self, tokens):
        m = self.looking_at(tokens)
        if m is not None and m.end_index() == len(tokens):
            return m
        return None

    def find_all(self, tokens):
        """All non-overlapping matches."""
        results = []
        start = 0
        while True:
            m = self.find(tokens, start)
            if m is None:
                return results
            start = m.end_index()
            # match may be empty if the query string has all optional parts
            if not m.is_empty():
                results.append(m)
