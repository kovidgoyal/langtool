"""Port of org.languagetool.rules.AbstractUnitConversionRule, with the parts of
its Java dependencies that the rule needs:

- the units of measurement (javax.measure with the reference
  implementation tech.units.indriya 1.3, the version LanguageTool uses):
  base, transformed and product units, their equality, dimensions and the
  conversions between them. The converters are composed and simplified
  like indriya does it (AbstractConverter.concatenate with its Simplifier),
  so that a conversion performs the same floating point operations in the
  same order as in Java (e.g. Units.KILOMETRE_PER_HOUR is METRE_PER_SECOND
  multiplied by 0.277778, as in indriya 1.3);
- java.text.DecimalFormat for parsing and formatting the numbers
  (grouping, maximum fraction digits, RoundingMode.HALF_UP).
"""

import math
import urllib.parse
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from functools import reduce
from math import gcd

from .. import jregex
from ..tools import java_trim
from .base import RuleMatch
from .core import CoreRule


# --- converters (tech.units.indriya.AbstractConverter and its subclasses) ---

# Simplifier.normalFormOrder
_ORDER_IDENTITY, _ORDER_RATIONAL, _ORDER_MULTIPLY, _ORDER_ADD, _ORDER_PAIR = 0, 2, 4, 5, 99


class Converter:
    """A unit converter (UnitConverter)"""

    order = None

    def is_identity(self):
        return False

    def is_linear(self):
        return True

    def convert(self, value):
        """UnitConverter.convert(double)"""
        if self.is_identity():
            return value
        return self.convert_when_not_identity(value)

    def convert_when_not_identity(self, value):
        raise NotImplementedError()

    def inverse(self):
        if self.is_identity():
            return self
        return self.inverse_when_not_identity()

    def inverse_when_not_identity(self):
        raise NotImplementedError()

    def is_simple_composition_with(self, other):
        return False

    def simple_compose(self, other):
        raise NotImplementedError()

    def conversion_steps(self):
        return [self]

    def concatenate(self, other):
        """AbstractConverter.concatenate: the converter equivalent to first
        converting by other and then by this converter, simplified
        (Simplifier.compose)"""
        return _compose(self, other)


class _Identity(Converter):
    order = _ORDER_IDENTITY

    def is_identity(self):
        return True

    def __eq__(self, other):
        return isinstance(other, _Identity)

    def __hash__(self):
        return 0

    def __repr__(self):
        return 'IDENTITY'


IDENTITY = _Identity()


class RationalConverter(Converter):
    """value * dividend / divisor (exact integers, not normalized)"""

    order = _ORDER_RATIONAL

    def __init__(self, dividend, divisor):
        if divisor <= 0:
            raise ValueError('Negative or zero divisor')
        self.dividend = dividend
        self.divisor = divisor

    def is_identity(self):
        return self.dividend == self.divisor

    def convert_when_not_identity(self, value):
        return value * _big_integer_to_double(self.dividend) / _big_integer_to_double(self.divisor)

    def inverse_when_not_identity(self):
        if self.dividend < 0:
            return RationalConverter(-self.divisor, -self.dividend)
        return RationalConverter(self.divisor, self.dividend)

    def is_simple_composition_with(self, other):
        return isinstance(other, RationalConverter)

    def simple_compose(self, other):
        dividend = self.dividend * other.dividend
        divisor = self.divisor * other.divisor
        g = gcd(dividend, divisor)
        dividend //= g
        divisor //= g
        if dividend == 1 and divisor == 1:
            return IDENTITY
        return RationalConverter(dividend, divisor)

    def __eq__(self, other):
        return (isinstance(other, RationalConverter) and self.dividend == other.dividend
                and self.divisor == other.divisor)

    def __hash__(self):
        return hash((self.dividend, self.divisor))

    def __repr__(self):
        return 'Rational(%d/%d)' % (self.dividend, self.divisor)


def _big_integer_to_double(i):
    """RationalConverter.toDouble (BigInteger.longValue or doubleValue)"""
    return float(i)


class MultiplyConverter(Converter):
    """value * factor (a double)"""

    order = _ORDER_MULTIPLY

    def __init__(self, factor):
        self.factor = factor

    def is_identity(self):
        return self.factor == 1.0

    def convert_when_not_identity(self, value):
        return value * self.factor

    def inverse_when_not_identity(self):
        return MultiplyConverter(_jdiv(1.0, self.factor))

    def is_simple_composition_with(self, other):
        return isinstance(other, MultiplyConverter)

    def simple_compose(self, other):
        return MultiplyConverter(self.factor * other.factor)

    def __eq__(self, other):
        # (Double.equals: compares the bits)
        return isinstance(other, MultiplyConverter) and _double_bits_equal(self.factor, other.factor)

    def __hash__(self):
        return hash(self.factor)

    def __repr__(self):
        return 'Multiply(%r)' % self.factor


class AddConverter(Converter):
    """value + offset (a double)"""

    order = _ORDER_ADD

    def __init__(self, offset):
        self.offset = offset

    def is_identity(self):
        return self.offset == 0.0

    def is_linear(self):
        return self.is_identity()

    def convert_when_not_identity(self, value):
        return value + self.offset

    def inverse_when_not_identity(self):
        return AddConverter(-self.offset)

    def is_simple_composition_with(self, other):
        return isinstance(other, AddConverter)

    def simple_compose(self, other):
        return AddConverter(self.offset + other.offset)

    def __eq__(self, other):
        return isinstance(other, AddConverter) and _double_bits_equal(self.offset, other.offset)

    def __hash__(self):
        return hash(self.offset)

    def __repr__(self):
        return 'Add(%r)' % self.offset


class PairConverter(Converter):
    """AbstractConverter.Pair: left(right(value))"""

    order = _ORDER_PAIR

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def is_linear(self):
        return self.left.is_linear() and self.right.is_linear()

    def convert_when_not_identity(self, value):
        return self.left.convert(self.right.convert(value))

    def inverse_when_not_identity(self):
        return PairConverter(self.right.inverse(), self.left.inverse())

    def conversion_steps(self):
        return self.left.conversion_steps() + self.right.conversion_steps()

    def __eq__(self, other):
        return isinstance(other, PairConverter) and self.left == other.left and self.right == other.right

    def __hash__(self):
        return hash((self.left, self.right))

    def __repr__(self):
        return 'Pair(%r, %r)' % (self.left, self.right)


def _double_bits_equal(a, b):
    if math.isnan(a) and math.isnan(b):
        return True
    return a == b and math.copysign(1.0, a) == math.copysign(1.0, b)


def _jdiv(a, b):
    """Java double division"""
    if b == 0:
        if a == 0 or math.isnan(a):
            return math.nan
        return math.copysign(math.inf, a) * math.copysign(1.0, b)
    return a / b


def _is_normal_form_order_when_identity(a, b):
    if type(a) is type(b):
        return True
    return a.order <= b.order


def _is_normal_form_order_when_commutative(a, b):
    # (no PowersOfIntConverter here)
    if type(a) is type(b):
        return True
    return a.order <= b.order


def _compose(a, b):
    """Simplifier.compose with isSimpleCompositionWith and simpleCompose"""
    if a.is_identity():
        if b.is_identity():
            return a if _is_normal_form_order_when_identity(a, b) else b
        return b
    if b.is_identity():
        return a
    if a.is_simple_composition_with(b):
        return a.simple_compose(b)
    commutative = a.is_linear() and b.is_linear()
    if commutative and not _is_normal_form_order_when_commutative(a, b):
        pair = PairConverter(b, a)
    else:
        pair = PairConverter(a, b)
    return _simplify(pair.conversion_steps())


def _normal_form_compare(a, b):
    """The comparator of SimplificationWorker.sortToNormalFormOrder (it
    never returns 0)"""
    if a.is_identity():
        if b.is_identity():
            return -1 if _is_normal_form_order_when_identity(a, b) else 1
        return -1
    if b.is_identity():
        return 1
    return -1 if _is_normal_form_order_when_commutative(a, b) else 1


def _java_small_sort(a, lo, hi, compare):
    """Arrays.sort(a, lo, hi, comparator) for less than 32 elements
    (TimSort: countRunAndMakeAscending and binarySort), which matters here
    because the comparator is inconsistent for converters of the same
    class"""
    if hi - lo < 2:
        return
    # countRunAndMakeAscending
    run_hi = lo + 1
    if compare(a[run_hi], a[lo]) < 0:
        run_hi += 1
        while run_hi < hi and compare(a[run_hi], a[run_hi - 1]) < 0:
            run_hi += 1
        a[lo:run_hi] = a[lo:run_hi][::-1]
    else:
        run_hi += 1
        while run_hi < hi and compare(a[run_hi], a[run_hi - 1]) >= 0:
            run_hi += 1
    # binarySort
    for start in range(run_hi, hi):
        pivot = a[start]
        left, right = lo, start
        while left < right:
            mid = (left + right) >> 1
            if compare(pivot, a[mid]) < 0:
                right = mid
            else:
                left = mid + 1
        a[left + 1:start + 1] = a[left:start]
        a[left] = pivot


def _sort_to_normal_form_order(steps):
    """Sorts the runs of linear converters (BitScanner.visitBitSequences)"""
    i = 0
    n = len(steps)
    while i < n:
        if not steps[i].is_linear():
            i += 1
            continue
        j = i
        while j < n and steps[j].is_linear():
            j += 1
        _java_small_sort(steps, i, j, _normal_form_compare)
        i = j


def _simplify(steps):
    """SimplificationWorker.simplify"""
    steps = list(steps)
    _sort_to_normal_form_order(steps)
    while True:
        # trySimplify (ArrayAdapter.visitSequentialPairsAndSimplify)
        count = 0
        if len(steps) >= 2:
            for i in range(1, len(steps)):
                left = steps[i - 1]
                if left is None:
                    continue
                right = steps[i]
                if left.is_identity():
                    r = right
                elif right.is_identity():
                    r = left
                elif left.is_simple_composition_with(right):
                    r = left.simple_compose(right)
                else:
                    r = None
                if r is not None:
                    steps[i - 1] = r
                    steps[i] = None
                    count += 1
        if count <= 0:
            break
        steps = [s for s in steps if s is not None]
        _sort_to_normal_form_order(steps)
    # sequenceToConverter
    if not steps:
        return IDENTITY
    if len(steps) == 1:
        return steps[0]
    return reduce(PairConverter, steps[2:], PairConverter(steps[0], steps[1]))


def _converter_of(factor):
    """AbstractUnit.converterOf"""
    if _is_long_value(factor):
        return RationalConverter(int(factor), 1)
    return MultiplyConverter(factor)


def _is_long_value(d):
    return -9.223372036854776e18 <= d <= 9.223372036854776e18 and math.floor(d) == d


# --- units (tech.units.indriya.AbstractUnit and its subclasses) ---

class UnconvertibleException(Exception):
    """javax.measure.UnconvertibleException"""


class Unit:
    """A unit of measurement (AbstractUnit)"""

    def system_unit(self):
        raise NotImplementedError()

    def system_converter(self):
        raise NotImplementedError()

    def dimension(self):
        """The dimension as a sorted tuple of (base dimension, exponent)"""
        raise NotImplementedError()

    def is_system_unit(self):
        s = self.system_unit()
        return self is s or self == s

    def transform(self, operation):
        system_unit = self.system_unit()
        if self.is_system_unit():
            cvtr = self.system_converter().concatenate(operation)
        else:
            cvtr = operation
        if cvtr.is_identity():
            return system_unit
        return TransformedUnit(self, cvtr)

    def multiply(self, factor):
        """Unit.multiply(double) or Unit.multiply(Unit)"""
        if isinstance(factor, Unit):
            if self == ONE:
                return factor
            if factor == ONE:
                return self
            return _of_product(self, factor)
        if factor == 1:
            return self
        return self.transform(_converter_of(factor))

    def divide(self, divisor):
        """Unit.divide(double) or Unit.divide(Unit)"""
        if isinstance(divisor, Unit):
            return self.multiply(divisor.inverse())
        if divisor == 1:
            return self
        if _is_long_value(divisor):
            return self.transform(RationalConverter(1, int(divisor)))
        return self.transform(MultiplyConverter(_jdiv(1.0, divisor)))

    def shift(self, offset):
        if offset == 0:
            return self
        return self.transform(AddConverter(offset))

    def inverse(self):
        if self == ONE:
            return self
        return _of_quotient(ONE, self)

    def pow(self, n):
        if n > 0:
            return self.multiply(self.pow(n - 1))
        if n == 0:
            return ONE
        return ONE.divide(self.pow(-n))

    def is_compatible(self, that):
        if self is that or self == that:
            return True
        return self.dimension() == that.dimension()

    def get_converter_to(self, that):
        """Unit.getConverterTo; raises UnconvertibleException"""
        if self is that or self == that:
            return IDENTITY
        this_system_unit = self.system_unit()
        that_system_unit = that.system_unit()
        if this_system_unit != that_system_unit:
            # getConverterToAny (the dimensional transforms of the default model are identities)
            if not self.is_compatible(that):
                raise UnconvertibleException('%r is not compatible with %r' % (self, that))
            return that.system_converter().inverse().concatenate(self.system_converter())
        this_to_si = self.system_converter()
        that_to_si = that.get_converter_to(that_system_unit)
        return that_to_si.inverse().concatenate(this_to_si)


class BaseUnit(Unit):

    def __init__(self, symbol, dimension):
        self.symbol = symbol
        self._dimension = ((dimension, 1),)

    def system_unit(self):
        return self

    def system_converter(self):
        return IDENTITY

    def dimension(self):
        return self._dimension

    def __eq__(self, other):
        return isinstance(other, BaseUnit) and self.symbol == other.symbol and self._dimension == other._dimension

    def __hash__(self):
        return hash(self.symbol)

    def __repr__(self):
        return self.symbol


class TransformedUnit(Unit):

    def __init__(self, parent, converter, system_unit=None):
        self.parent = parent
        self.converter = converter
        self._system_unit = system_unit if system_unit is not None else parent.system_unit()

    def system_unit(self):
        return self._system_unit

    def system_converter(self):
        return self.parent.system_converter().concatenate(self.converter)

    def dimension(self):
        return self.parent.dimension()

    def __eq__(self, other):
        return isinstance(other, TransformedUnit) and self.parent == other.parent and \
            self.converter == other.converter

    def __hash__(self):
        return hash((self.parent, self.converter))

    def __repr__(self):
        return 'Transformed(%r, %r)' % (self.parent, self.converter)


class ProductUnit(Unit):
    """elements: tuple of (unit, pow, root)"""

    def __init__(self, elements=()):
        self.elements = tuple(elements)

    def system_unit(self):
        result = ONE
        for unit, pw, root in self.elements:
            u = unit.system_unit().pow(pw)
            u = _of_root(u, root)
            result = result.multiply(u)
        return result

    def system_converter(self):
        converter = IDENTITY
        for unit, pw, root in self.elements:
            cvtr = unit.system_converter()
            if not cvtr.is_linear():
                raise ValueError('%r is non-linear, cannot convert' % (unit,))
            if root != 1:
                raise ValueError('%r holds a base unit with fractional exponent' % (unit,))
            if pw < 0:
                pw = -pw
                cvtr = cvtr.inverse()
            for _ in range(pw):
                converter = converter.concatenate(cvtr)
        return converter

    def dimension(self):
        dims = {}
        for unit, pw, root in self.elements:
            for d, e in unit.dimension():
                dims[d] = dims.get(d, Fraction(0)) + Fraction(e) * pw / root
        return tuple(sorted((d, e) for d, e in dims.items() if e != 0))

    def __eq__(self, other):
        if not isinstance(other, ProductUnit):
            return False
        if len(self.elements) != len(other.elements):
            return False
        for unit, pw, root in self.elements:
            for unit2, pw2, root2 in other.elements:
                if unit == unit2:
                    if pw != pw2 or root != root2:
                        return False
                    break
            else:
                return False
        return True

    def __hash__(self):
        return hash(frozenset(self.elements))

    def __repr__(self):
        return 'Product%r' % (self.elements,)


ONE = ProductUnit()


def _elements(unit):
    return unit.elements if isinstance(unit, ProductUnit) else ((unit, 1, 1),)


def _get_instance(left, right):
    """ProductUnit.getInstance"""
    result = []
    for unit, pw1, root1 in left:
        pw2, root2 = 0, 1
        for unit2, p, r in right:
            if unit == unit2:
                pw2, root2 = p, r
                break
        pw = pw1 * root2 + pw2 * root1
        root = root1 * root2
        if pw != 0:
            g = gcd(abs(pw), root)
            result.append((unit, pw // g, root // g))
    for element in right:
        if not any(element[0] == unit for unit, _p, _r in left):
            result.append(element)
    if not result:
        return ONE
    if len(result) == 1 and result[0][1] == result[0][2]:
        return result[0][0]
    return ProductUnit(result)


def _of_product(left, right):
    return _get_instance(_elements(left), _elements(right))


def _of_quotient(left, right):
    return _get_instance(_elements(left), tuple((u, -p, r) for u, p, r in _elements(right)))


def _of_root(unit, n):
    if n == 1 and not isinstance(unit, ProductUnit):
        return unit
    return _get_instance(tuple((u, p, r * n) for u, p, r in _elements(unit)), ())


# tech.units.indriya.unit.Units (the units used by the rules)
KELVIN = BaseUnit('K', 'TEMPERATURE')
KILOGRAM = BaseUnit('kg', 'MASS')
METRE = BaseUnit('m', 'LENGTH')
SECOND = BaseUnit('s', 'TIME')
CELSIUS = TransformedUnit(KELVIN, AddConverter(273.15))
METRE_PER_SECOND = ProductUnit(_elements(METRE.divide(SECOND)))
SQUARE_METRE = ProductUnit(_elements(METRE.multiply(METRE)))
CUBIC_METRE = ProductUnit(_elements(SQUARE_METRE.multiply(METRE)))
KILOMETRE_PER_HOUR = METRE_PER_SECOND.multiply(0.277778)
HOUR = TransformedUnit(SECOND, RationalConverter(3600, 1), SECOND)
LITRE = TransformedUnit(CUBIC_METRE, RationalConverter(1, 1000))

# AbstractUnitConversionRule
POUND = KILOGRAM.multiply(0.45359237)
OUNCE = POUND.divide(12)
FEET = METRE.multiply(0.3048)
YARD = FEET.multiply(3)
INCH = FEET.divide(12)
MILE = FEET.multiply(5280)
US_QUART = LITRE.multiply(0.946352946)
US_GALLON = US_QUART.multiply(4)
US_PINT = US_QUART.divide(2)
US_CUP = US_QUART.divide(4)
US_FL_OUNCE = US_QUART.divide(32)
IMP_PINT = LITRE.multiply(0.5682612532)
IMP_QUART = IMP_PINT.multiply(2)
IMP_GALLON = IMP_QUART.multiply(4)
IMP_FL_OUNCE = IMP_PINT.divide(20)
FAHRENHEIT = CELSIUS.multiply(5.0 / 9.0).shift(-32)


# --- java.text.DecimalFormat ---

class ParseException(ValueError):
    """java.text.ParseException"""


class DecimalFormat:
    """The parts of java.text.DecimalFormat used by the unit conversion
    rules: a number format with grouping (by three digits) and at most
    maximum_fraction_digits fraction digits, rounding with
    RoundingMode.HALF_UP (on the exact value of the double). The default
    symbols are those of the root/English locale; NumberFormat for
    Locale.GERMANY is DecimalFormat(decimal=',', grouping='.')."""

    def __init__(self, decimal='.', grouping=',', maximum_fraction_digits=2):
        self.decimal = decimal
        self.grouping = grouping
        self.maximum_fraction_digits = maximum_fraction_digits

    def format(self, number):
        """NumberFormat.format(double) / format(long)"""
        if isinstance(number, int):
            negative = number < 0
            digits = str(abs(number))
            fraction = ''
        else:
            if math.isnan(number):
                return 'NaN'
            negative = number < 0.0 or (number == 0.0 and math.copysign(1.0, number) < 0.0)
            if math.isinf(number):
                return ('-' if negative else '') + '∞'
            s = format(self._round(abs(number)), 'f')
            if '.' in s:
                digits, fraction = s.split('.')
                fraction = fraction.rstrip('0')
            else:
                digits, fraction = s, ''
        groups = []
        while len(digits) > 3:
            groups.insert(0, digits[-3:])
            digits = digits[:-3]
        groups.insert(0, digits)
        out = self.grouping.join(groups)
        if fraction:
            out += self.decimal + fraction
        return ('-' if negative else '') + out

    def _round(self, x):
        """Rounds a non-negative double with HALF_UP like DecimalFormat
        (DigitList.set): the digits are those of the shortest decimal
        representation of the double (large numbers are padded with zeros),
        ties are decided by the exact binary value"""
        with localcontext() as ctx:
            ctx.prec = 1000
            shortest = Decimal(repr(x))
            exp = Decimal(1).scaleb(-self.maximum_fraction_digits)
            rounding = ROUND_HALF_UP
            scaled = shortest.scaleb(self.maximum_fraction_digits)
            if scaled - scaled.to_integral_value(ROUND_DOWN) == Decimal('0.5') and Decimal(x) < shortest:
                rounding = ROUND_DOWN
            return shortest.quantize(exp, rounding)

    def parse(self, text):
        """NumberFormat.parse(text).doubleValue(): the longest number at the
        start of the text (grouping separators are skipped in the integer
        part); raises ParseException if there is none"""
        pos = 0
        negative = False
        if text.startswith('-'):
            negative = True
            pos = 1
        digits = []
        decimal_at = -1
        saw_digit = False
        saw_decimal = False
        while pos < len(text):
            ch = text[pos]
            if '0' <= ch <= '9':
                saw_digit = True
                digits.append(ch)
            elif ch == self.decimal:
                if saw_decimal:
                    break
                decimal_at = len(digits)
                saw_decimal = True
            elif ch == self.grouping:
                if saw_decimal:
                    break
            else:
                break
            pos += 1
        if not saw_digit:
            raise ParseException('Unparseable number: "%s"' % text)
        if decimal_at < 0:
            decimal_at = len(digits)
        s = ''.join(digits[:decimal_at]) + '.' + ''.join(digits[decimal_at:])
        value = float(s if s != '.' else '0')
        return -value if negative else value


def java_round(x):
    """Math.round(double): floor(x + 1/2) in exact arithmetic"""
    if math.isnan(x):
        return 0
    if math.isinf(x):
        return 2 ** 63 - 1 if x > 0 else -2 ** 63
    r = math.floor(Fraction(x) + Fraction(1, 2))
    return max(-2 ** 63, min(2 ** 63 - 1, r))


def java_url_encode(s):
    """URLEncoder.encode(s, "utf-8")"""
    return urllib.parse.quote_plus(s, safe='*').replace('~', '%7E')


def _java_hash_map_int_order(keys):
    """The iteration order of a java.util.HashMap with Integer keys (in
    insertion order), with the default capacity"""
    cap = 16
    while len(keys) > cap * 0.75:
        cap *= 2

    def bucket(k):
        h = k & 0xffffffff
        return (h ^ (h >> 16)) & (cap - 1)
    return sorted(keys, key=bucket)


# --- AbstractUnitConversionRule ---

# limit size of matched number to (possibly) avoid hangups
# we need a different regex for including a word boundary (\b), instead of just prepending that
# because otherwise negative numbers aren't correctly recognized
NUMBER_REGEX = '(-?[0-9]{1,32}[0-9,.]{0,32})'
NUMBER_REGEX_WITH_BOUNDARY = '(-?\\b[0-9]{1,32}[0-9,.]{0,32})'
_ASCII_DIGIT = jregex.compile('[0-9]')

_DELTA = 1e-2
_ROUNDING_DELTA = 0.05
_MAX_SUGGESTIONS = 5
_WHITESPACE_LIMIT = 5

# messages (AbstractUnitConversionRule.Message)
SUGGESTION, CHECK, CHECK_UNKNOWN_UNIT, UNIT_MISMATCH = 'SUGGESTION', 'CHECK', 'CHECK_UNKNOWN_UNIT', 'UNIT_MISMATCH'

_ANTI_PATTERNS = (
    jregex.compile("\\s?\\d+'\\d\\d\\d\\s?"),  # "100'000", thousands separator in de-CH
    jregex.compile('\\d+[-‐–]\\d+'),  # "3-5 pounds"
    jregex.compile('\\d+/\\d+'),  # "1/4 mile"
    jregex.compile('\\d+:\\d+'),  # "A 2:1 cup"
    jregex.compile('Pfund Sterling'),  # "1.800 Pfund Sterling" (German)
    jregex.compile('\\d+⁄\\d+'),  # "1⁄4 cup" (it's not the standard slash)
)
_FEET_INCH_CONVERSION = jregex.compile('\\(\\d+ (feet|ft) \\d+ inch\\)')


def _naturalness(number):
    """smaller score -> better"""
    a = abs(number)
    if a < 1.0:
        return _jdiv(1.0, a * a * 2)
    if a < 100:
        return a - 50
    return a * a


class AbstractUnitConversionRule(CoreRule):
    """Port of org.languagetool.rules.AbstractUnitConversionRule: detects
    measurements in non-metric units and suggests adding the metric
    equivalent, checks existing conversions (e.g. "5 miles (8 km)").
    Subclasses add their units with add_unit() and override
    get_number_format(), get_message(), get_short_message(),
    get_suggestion() and format_rounded()."""

    category_id = 'STYLE'
    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.number_range_part = jregex.compile(NUMBER_REGEX_WITH_BOUNDARY + '$')
        # (pattern, unit) in the order of insertion (a LinkedHashMap in Java)
        self.unit_patterns = []
        # for patterns that require a custom number parsing function: (pattern, unit, function)
        self.special_patterns = []
        self.unit_symbols = {}
        # for recognizing conversions made by this rule or the user
        self.converted_patterns = []
        # units to use for conversions
        self.metric_units = []
        self.add_unit('kg', KILOGRAM, 'kg', 1e0, True)
        self.add_unit('g', KILOGRAM, 'g', 1e-3, True)
        self.add_unit('t', KILOGRAM, 't', 1e3, True)
        self.add_unit('lb', POUND, 'lb', 1, False)
        # addUnit("oz", OUNCE, "oz", 1, false); -- probably not useful
        self.add_unit('mi', MILE, 'mi', 1, False)
        self.add_unit('yd', YARD, 'yd', 1, False)
        # negative lookahead here to avoid matching "'s" and so on
        self.add_unit("(?:ft|′|')(?!(\\w|\\d))", FEET, 'ft', 1, False)
        # removed 'in', " because of many false positives
        self.add_unit('(?:inch|″)(?!(\\w|\\d))', INCH, 'inch', 1, False)
        self.add_unit('(?:km/h|kmh)', KILOMETRE_PER_HOUR, 'km/h', 1, True)
        self.add_unit('(?:mph)', MILE.divide(HOUR), 'mph', 1, False)
        self.add_unit('km', METRE, 'km', 1e3, True)
        self.add_unit('m', METRE, 'm', 1e0, True)
        # addUnit("dm", METRE, "dm", 1e-1,  /*true*/); // Metric, but not commonly used
        self.add_unit('cm', METRE, 'cm', 1e-2, True)
        self.add_unit('mm', METRE, 'mm', 1e-3, True)
        self.add_unit('µm', METRE, 'µm', 1e-6, True)
        self.add_unit('nm', METRE, 'nm', 1e-9, True)
        self.add_unit('m(?:\\^2|2|²)', SQUARE_METRE, 'm²', 1, True)
        self.add_unit('ha', SQUARE_METRE, 'ha', 1e4, True)
        self.add_unit('a', SQUARE_METRE, 'a', 1e2, True)
        self.add_unit('km(?:\\^2|2|²)', SQUARE_METRE, 'km²', 1e6, True)
        # addUnit("dm(?:\\^2|2|²)", SQUARE_METRE, "dm²", 1e-2,  false/*true*/); // Metric, but not commonly used
        self.add_unit('cm(?:\\^2|2|²)', SQUARE_METRE, 'cm²', 1e-4, True)
        self.add_unit('mm(?:\\^2|2|²)', SQUARE_METRE, 'mm²', 1e-6, True)
        self.add_unit('µm(?:\\^2|2|²)', SQUARE_METRE, 'µm²', 1e-12, True)
        self.add_unit('nm(?:\\^2|2|²)', SQUARE_METRE, 'nm²', 1e-18, True)
        self.add_unit('(?:sq|square) (?:in(?:ch)?|inches)', INCH.multiply(INCH), 'sq in', 1, False)
        self.add_unit('(?:inches|in|inch) (?:\\^2|2|²)', INCH.multiply(INCH), 'in²', 1, False)
        self.add_unit('(?:sq|square) (?:ft|feet|foot)', FEET.multiply(FEET), 'sq ft', 1, False)
        self.add_unit('sf', FEET.multiply(FEET), 'sf', 1, False)
        self.add_unit('ft(?:\\^2|2|²)', FEET.multiply(FEET), 'ft²', 1, False)
        self.add_unit('(?:sq|square) (?:yds?|yards?)', YARD.multiply(YARD), 'sq yd', 1, False)
        self.add_unit('(?:yards?|yds?)(?:\\^2|2|²)', YARD.multiply(YARD), 'yd²', 1, False)
        self.add_unit('m(?:\\^3|3|³)', CUBIC_METRE, 'm³', 1, True)
        self.add_unit('km(?:\\^3|3|³)', CUBIC_METRE, 'km³', 1e9, True)
        # addUnit("dm(?:\\^3|3|³)", CUBIC_METRE, "dm³", 1e-3,  false/*true*/); // Metric, but not commonly used
        self.add_unit('cm(?:\\^3|3|³)', CUBIC_METRE, 'cm³', 1e-6, True)
        self.add_unit('mm(?:\\^3|3|³)', CUBIC_METRE, 'mm³', 1e-9, True)
        self.add_unit('µm(?:\\^3|3|³)', CUBIC_METRE, 'µm³', 1e-18, True)
        self.add_unit('nm(?:\\^3|3|³)', CUBIC_METRE, 'nm³', 1e-27, True)
        self.add_unit('(?:cubic|cu) (?:feet|ft|foot)', FEET.multiply(FEET).multiply(FEET), 'cubic feet', 1, False)
        self.add_unit('(?:feet|ft|foot)(?:\\^3|3|³)', FEET.multiply(FEET).multiply(FEET), 'ft³', 1, False)
        self.add_unit('(?:cubic|cu) (?:inch|in|inches)', INCH.multiply(INCH).multiply(INCH), 'cubic inch', 1,
                      False)
        self.add_unit('(?:inch|in)(?:\\^3|3|³)', INCH.multiply(INCH).multiply(INCH), 'inch³', 1, False)
        self.add_unit('(?:cubic|cu) (?:yards?|yds?)', YARD.multiply(YARD).multiply(YARD), 'cubic yard', 1, False)
        self.add_unit('(?:yard|yd)(?:\\^3|3|³)', YARD.multiply(YARD).multiply(YARD), 'yard³', 1, False)
        self.add_unit('l', LITRE, 'l', 1, True)
        self.add_unit('ml', LITRE, 'ml', 1e-3, True)
        self.add_unit('°F', FAHRENHEIT, '°F', 1, False)
        self.add_unit('°C', CELSIUS, '°C', 1, True)
        self.converted_patterns.append(jregex.compile('\\s*\\((?:ca. )?' + NUMBER_REGEX + '\\s*([^)]+)\\s*\\)'))
        # recognizes 5'6" = 5 feet + 6 inches = 5.5 feet (a HashMap keyed by the patterns in Java: the
        # iteration order is not defined, the patterns cannot match the same number)
        self.special_patterns.append((jregex.compile('(?:(?<=[^º°\\d]))\\s(\\d+)(?:ft|′|\')\\s*(\\d+)\\s*'
                                                     '(?:in|"|″)?'), FEET, self._parse_feet_and_inch))
        self.special_patterns.append((jregex.compile('(?:(?<=[^º°\\d\\s]))(\\d+)(?:ft|′|\')\\s*(\\d+)\\s*'
                                                     '(?:in|"|″)?'), FEET, self._parse_feet_and_inch))

    def _parse_feet_and_inch(self, match):
        try:
            feet = self.get_number_format().parse(match.group(1))
        except ParseException:
            return None
        try:
            inch = self.get_number_format().parse(match.group(2))
        except ParseException:
            inch = 0.0
        return feet + inch / 12.0

    @staticmethod
    def _build_url_for_explanation(original):
        return 'http://www.wolframalpha.com/input/?i=' + java_url_encode('convert ' + original + ' to metric')

    _default_number_format = DecimalFormat()

    def get_number_format(self):
        """Override in subclasses: the locale-specific number format"""
        return self._default_number_format

    def get_message(self, message):
        """Override in subclasses"""
        return {CHECK: "This unit conversion doesn't seem right. Do you want to correct it automatically?",
                SUGGESTION: 'Writing for an international audience? Consider adding the metric equivalent.',
                CHECK_UNKNOWN_UNIT: "This unit conversion doesn't seem right, unable to recognize the used unit.",
                UNIT_MISMATCH: "These units don't seem to be compatible."}[message]

    def get_short_message(self, message):
        """Override in subclasses"""
        return {CHECK: 'Incorrect unit conversion. Correct it?', SUGGESTION: 'Add metric equivalent?',
                CHECK_UNKNOWN_UNIT: 'Unknown unit used in conversion.', UNIT_MISMATCH: 'Units incompatible.'}[message]

    def get_suggestion(self, original, converted):
        """Format suggestion: original is the text matched, converted
        computed by this rule"""
        return original + ' (' + converted + ')'

    def format_rounded(self, s):
        """Override in subclasses: the formatting of rounded numbers
        according to the locale"""
        return 'ca. ' + s

    def add_unit(self, pattern, base, symbol, factor, metric):
        """Associate a notation with a given unit: pattern is the regex for
        recognizing the unit (word boundaries and numbers are added), base
        the unit, symbol the suffix used for suggestions, factor a
        convenience parameter for prefixes (the unit is multiplied with
        it), metric registers this notation for suggestions."""
        unit = base.multiply(factor)
        self.unit_patterns.append((jregex.compile(NUMBER_REGEX_WITH_BOUNDARY + '[\\s ]{0,'
                                                  + str(_WHITESPACE_LIMIT) + '}' + pattern + '\\b',
                                                  jregex.UNICODE_CHARACTER_CLASS), unit))
        self.unit_symbols.setdefault(unit, []).append(symbol)
        if metric and unit not in self.metric_units:
            self.metric_units.append(unit)

    def get_metric_equivalent(self, value, unit):
        """Suggestions of the given number converted into metric units,
        sorted by naturalness, as a list of (unit, value), or None if no
        conversion is necessary / possible"""
        conversions = []
        for metric in self.metric_units:
            if unit == metric:  # don't convert to itself
                return None
            if unit.is_compatible(metric):
                converted = unit.get_converter_to(metric).convert(value)
                conversions.append((metric, converted))
        # sort according to "naturalness" of this unit, i.e. numbers not being too small/large
        conversions.sort(key=lambda c: _naturalness(c[1]))
        return conversions or None

    def format_measurement(self, value, unit):
        equivalents = self.get_metric_equivalent(value, unit)
        if equivalents is None:
            return None
        formatted = self._get_formatted_conversions(equivalents)
        return formatted or None

    def _get_formatted_conversions(self, conversions):
        """Adds different formatted variants of the given conversions up to
        MAX_SUGGESTIONS: formatted numbers, with various units and unit
        symbols, rounded to integers or according to get_number_format()"""
        formatted = []
        number_format = self.get_number_format()
        for metric, converted in conversions:
            rounded = java_round(converted)
            for symbol in self.unit_symbols.get(metric, ()):
                if len(formatted) > _MAX_SUGGESTIONS:
                    break
                if _jdiv(abs(converted - rounded), abs(converted)) < _ROUNDING_DELTA and rounded != 0:
                    formatted_str = self.format_rounded(number_format.format(rounded) + ' ' + symbol)
                    if formatted_str not in formatted:
                        formatted.append(formatted_str)
                formatted_number = number_format.format(converted)
                formatted_str = formatted_number + ' ' + symbol
                # TODO: be cleverer than !equals("0"), can prevent valid conversions
                if formatted_str not in formatted and formatted_number != '0':
                    formatted.append(formatted_str)
        return formatted

    def _unit_patterns_with_metric_flag(self):
        """[(pattern, unit, unit in self.metric_units)] (cached, the
        membership test compares units with __eq__, which is slow)"""
        key = (len(self.unit_patterns), len(self.metric_units))
        c = getattr(self, '_unit_patterns_cache', None)
        if c is None or c[0] != key:
            metric = self.metric_units
            c = self._unit_patterns_cache = (key, [(p, u, u in metric) for p, u in self.unit_patterns])
        return c[1]

    def _match_units(self, sentence, matches, ignore_ranges, is_metric):
        text = sentence.text
        if _ASCII_DIGIT.search(text) is None:
            return  # (all unit patterns start with NUMBER_REGEX_WITH_BOUNDARY, see add_unit)
        # find specific unit through lookup of pattern
        for unit_pattern, unit, unit_is_metric in self._unit_patterns_with_metric_flag():
            if unit_is_metric != is_metric:
                continue
            for unit_matcher in unit_pattern.finditer(text):
                if not any(unit_matcher.start() >= a and unit_matcher.end() <= b for a, b in ignore_ranges):
                    self._try_conversion(sentence, matches, unit, None, unit_matcher, ignore_ranges)

    def detect_number_range(self, sentence, matcher):
        hyphen_in_number = matcher.group(1).startswith('-')
        if not hyphen_in_number:
            return False
        text_before = sentence.text[:matcher.start()]
        return self.number_range_part.search(text_before) is not None

    def _try_conversion(self, sentence, matches, unit, custom_value, unit_matcher, ignore_ranges):
        """unit: the unit of the pattern (unitPatterns.getOrDefault(pattern,
        customUnit)); custom_value: the value of a special pattern"""
        text = sentence.text
        ignore_ranges.append((unit_matcher.start(), unit_matcher.end()))
        # search for an existing conversion, e.g. "5 miles (8km)"
        converted_in_text = None
        converted_offset = unit_matcher.end()
        converted_matcher = None
        for converted_pattern in self.converted_patterns:
            converted_matcher = converted_pattern.search(text[converted_offset:])
            if converted_matcher is not None and converted_matcher.start() == 0:
                converted_in_text = converted_matcher.group(0)
                break
        number_format = self.get_number_format()
        if custom_value is None:
            try:
                value_as_string = unit_matcher.group(1)
                # remove hyphen at start if it belongs to a range (e.g 1-5 miles)
                # see https://github.com/languagetool-org/languagetool/issues/2170
                # TODO convert whole range, not only end
                if self.detect_number_range(sentence, unit_matcher):
                    value_as_string = value_as_string[1:]
                value = number_format.parse(value_as_string)
            except ParseException:
                return
        else:
            value = custom_value
        converted = self.format_measurement(value, unit)
        if converted is None and converted_in_text is None:
            pass  # no conversion necessary, e.g. already metric
        elif converted_in_text is None:  # no conversion found -> suggest one
            match = RuleMatch(self, sentence, unit_matcher.start(), unit_matcher.end(),
                              self.get_message(SUGGESTION), self.get_short_message(SUGGESTION))
            match.set_suggested_replacements([self.get_suggestion(unit_matcher.group(0), formatted)
                                              for formatted in converted])
            match.url = self._build_url_for_explanation(unit_matcher.group(0))
            matches.append(match)
        else:  # check given conversion for accuracy
            ignore_ranges.append((converted_matcher.start(0) + converted_offset,
                                  converted_matcher.end(0) + converted_offset))
            # already using one of our conversions?
            final_converted_in_text = java_trim(converted_in_text)
            converted_trimmed = final_converted_in_text[1:-1]
            if converted is not None and converted_trimmed in converted:
                return
            converted_unit = None
            for pattern, pattern_unit in self.unit_patterns:
                if pattern.search(final_converted_in_text):
                    converted_unit = pattern_unit
                    break
            if converted_unit is not None:  # known unit used for conversion
                # If the unit before and after conversion is the same, e.g. "22.3 cm (20.4 cm)", assume users
                # either:
                # 1. know what they're doing; or
                # 2. there's a more complex expression at play here, which we can't parse
                if unit == converted_unit:
                    return
                try:
                    converted_value_in_text = number_format.parse(converted_matcher.group(1))
                    if _FEET_INCH_CONVERSION.fullmatch(java_trim(converted_matcher.group())):
                        # e.g. "(2 ft 6 inch)" would be interpreted as just "2 ft", given a wrong suggestion
                        return
                except ParseException:
                    return
                if converted is None:
                    # already metric, check conversion in convertedUnit / convertedValueInText (order may be
                    # reversed)
                    reverse_converted = None
                    try:
                        unit_converted = unit.get_converter_to(converted_unit).convert(value)
                        diff = abs(unit_converted - converted_value_in_text)
                        if diff > _DELTA:
                            match = RuleMatch(self, sentence, converted_matcher.start(1) + converted_offset,
                                              converted_matcher.end(1) + converted_offset,
                                              self.get_message(CHECK), self.get_short_message(CHECK))
                            match.url = self._build_url_for_explanation(converted_trimmed)
                            reverse_converted = self._get_formatted_conversions([(converted_unit, unit_converted)])
                            if converted_trimmed in reverse_converted:
                                return
                            match.set_suggested_replacements(reverse_converted)
                            matches.append(match)
                    except UnconvertibleException:
                        match = RuleMatch(self, sentence, unit_matcher.start(),
                                          converted_matcher.end() + converted_offset,
                                          self.get_message(UNIT_MISMATCH), self.get_short_message(UNIT_MISMATCH))
                        if reverse_converted is not None:
                            match.set_suggested_replacements(reverse_converted)
                        match.url = self._build_url_for_explanation(converted_trimmed)
                        matches.append(match)
                else:  # found conversion to metric, check for accuracy
                    metric_equivalents = self.get_metric_equivalent(value, unit)
                    if not metric_equivalents:
                        return
                    metric_unit, converted_value_computed = metric_equivalents[0]
                    original = unit_matcher.group(0)
                    corrected = [self.get_suggestion(original, suggestion) for suggestion in converted]
                    if not (converted_unit == metric_unit
                            and abs(converted_value_in_text - converted_value_computed) < _DELTA):
                        match = RuleMatch(self, sentence, unit_matcher.start(),
                                          converted_matcher.end(0) + converted_offset,
                                          self.get_message(CHECK), self.get_short_message(CHECK))
                        match.set_suggested_replacements(corrected)
                        match.url = self._build_url_for_explanation(unit_matcher.group(0))
                        matches.append(match)
            elif converted is not None:  # unknown unit used for conversion
                match = RuleMatch(self, sentence, converted_matcher.start(1) + converted_offset,
                                  converted_matcher.end(2) + converted_offset,
                                  self.get_message(CHECK_UNKNOWN_UNIT), self.get_short_message(CHECK_UNKNOWN_UNIT))
                match.set_suggested_replacements(converted)
                matches.append(match)

    def match(self, sentence):
        matches = []
        ignore_ranges = []
        text = sentence.text
        # handle special patterns where simple number parsing is not enough, e.g. 5'6"
        for special_pattern, unit, parse in self.special_patterns:
            for matcher in special_pattern.finditer(text):
                value = parse(matcher)
                if value is None:
                    continue
                if not any(matcher.start() >= a and matcher.end() <= b for a, b in ignore_ranges):
                    self._try_conversion(sentence, matches, unit, value, matcher, ignore_ranges)
        # check for numbers with a given set of units (e.g. imperial)
        # two runs: first metric units, so that ignore ranges are set up properly
        # then match other units
        # should fix sentences like 10 km (5 miles), where 5 miles matches first and matching 10 km first would
        # have prevented that
        # there should be no influence on other results
        self._match_units(sentence, matches, ignore_ranges, True)
        self._match_units(sentence, matches, ignore_ranges, False)
        # deduplicate matches with equal start, longer match should win, e.g. miles per hour over just miles
        matches_by_start = {}
        for match in matches:
            other = matches_by_start.get(match.from_pos)
            if other is None or match.to_pos > other.to_pos:
                matches_by_start[match.from_pos] = match
        if matches:
            self._remove_anti_pattern_matches(text, matches_by_start)
        # (the iteration order of the Java HashMap)
        return [matches_by_start[k] for k in _java_hash_map_int_order(list(matches_by_start))]

    @staticmethod
    def _remove_anti_pattern_matches(text, matches_by_start):
        for anti_pattern in _ANTI_PATTERNS:
            pos = 0
            while pos < len(text):
                m = anti_pattern.search(text, pos)
                if m is None:
                    break
                for k in [k for k, rm in matches_by_start.items()
                          if (m.start() <= rm.from_pos and m.end() >= rm.from_pos)
                          or (m.start() <= rm.to_pos and m.end() >= rm.to_pos)]:
                    del matches_by_start[k]
                pos = m.end() + 1
