"""Tests of langtool.rules.unit_conversion, the port of
org.languagetool.rules.AbstractUnitConversionRule with its units of
measurement (indriya 1.3) and number format (java.text.DecimalFormat). The
expected values are those of Java (LanguageTool 6.6)."""

import pytest

from langtool.rules.unit_conversion import (CELSIUS, CUBIC_METRE, FAHRENHEIT, FEET, HOUR, INCH, KILOGRAM,
                                            KILOMETRE_PER_HOUR, LITRE, METRE, MILE, ONE, POUND, SQUARE_METRE,
                                            AbstractUnitConversionRule, AddConverter, DecimalFormat,
                                            MultiplyConverter, PairConverter, ParseException, ProductUnit,
                                            RationalConverter, TransformedUnit, UnconvertibleException, java_round,
                                            java_url_encode)


def test_unit_equality():
    """Units created in the same way are equal (TransformedUnit: parent and
    converter, ProductUnit: the elements), multiply(1) is the unit itself,
    integral factors give RationalConverters"""
    assert KILOGRAM.multiply(1e0) is KILOGRAM
    assert KILOGRAM.multiply(1e-3) == KILOGRAM.multiply(1e-3)
    assert METRE.multiply(1e3) == METRE.multiply(1000)
    assert METRE.multiply(1e3).converter == RationalConverter(1000, 1)
    assert METRE.multiply(1e-3).converter == MultiplyConverter(0.001)
    assert METRE.multiply(1e3) != METRE.multiply(1e-3)
    assert FEET.multiply(FEET) == FEET.multiply(FEET)
    assert FEET.multiply(FEET) != SQUARE_METRE
    assert FEET.multiply(FEET).system_unit() == SQUARE_METRE
    assert METRE.multiply(METRE) == SQUARE_METRE == ProductUnit([(METRE, 2, 1)])
    assert METRE.divide(METRE) is ONE
    assert len({METRE.multiply(1e3), METRE.multiply(1000.0), METRE}) == 2
    assert isinstance(MILE, TransformedUnit) and MILE.parent == FEET


def test_compatibility():
    assert FEET.is_compatible(METRE)
    assert INCH.multiply(INCH).is_compatible(SQUARE_METRE)
    assert LITRE.is_compatible(CUBIC_METRE)
    assert MILE.divide(HOUR).is_compatible(KILOMETRE_PER_HOUR)
    assert FAHRENHEIT.is_compatible(CELSIUS)
    assert not METRE.is_compatible(KILOGRAM)
    with pytest.raises(UnconvertibleException):
        METRE.get_converter_to(KILOGRAM)


def test_converters():
    """The converters are composed and simplified like in indriya, so that
    the floating point operations are the same"""
    assert FEET.get_converter_to(METRE) == MultiplyConverter(0.3048)
    assert FEET.get_converter_to(METRE).convert(6.0) == 1.8288000000000002
    mph = MILE.divide(HOUR).get_converter_to(KILOMETRE_PER_HOUR)
    assert mph == PairConverter(RationalConverter(22, 15), MultiplyConverter(0.3048 * (1.0 / 0.277778)))
    assert mph.convert(60.0) == 96.5605627515498
    f_to_c = FAHRENHEIT.get_converter_to(CELSIUS)
    assert f_to_c == PairConverter(MultiplyConverter(5.0 / 9.0), AddConverter(-32.0))
    assert f_to_c.convert(100.0) == 37.77777777777778
    assert CELSIUS.get_converter_to(FAHRENHEIT).convert(100.0) == 211.99999999999997
    # Pair(Rational(1/1000), Multiply(0.45359237)): first the multiplication, then the rational
    assert POUND.get_converter_to(KILOGRAM.multiply(1e3)).convert(10000.0) == 10000.0 * 0.45359237 * 1.0 / 1000.0
    assert METRE.get_converter_to(METRE).convert(2.5) == 2.5
    assert MultiplyConverter(2.0).concatenate(MultiplyConverter(3.0)) == MultiplyConverter(6.0)
    assert RationalConverter(2, 3).concatenate(RationalConverter(3, 2)).is_identity()
    assert RationalConverter(1, 3).inverse() == RationalConverter(3, 1)


def test_decimal_format():
    """NumberFormat.getNumberInstance(Locale.GERMANY) with at most 2 fraction
    digits and RoundingMode.HALF_UP"""
    f = DecimalFormat(decimal=',', grouping='.', maximum_fraction_digits=2)
    assert f.format(1.8288) == '1,83'
    assert f.format(160934.4) == '160.934,4'
    assert f.format(1.005) == '1'  # 1.00499999999999989...
    assert f.format(0.125) == '0,13'
    assert f.format(2.675) == '2,67'  # 2.67499999999999982...
    assert f.format(0.135) == '0,14'  # 0.13500000000000000888...
    assert f.format(-0.001) == '-0'
    assert f.format(0.0) == '0'
    assert f.format(1e23) == '100.000.000.000.000.000.000.000'
    assert f.format(10000) == '10.000'
    assert f.format(-1234567) == '-1.234.567'
    assert f.parse('10.000') == 10000.0
    assert f.parse('1,83') == 1.83
    assert f.parse('5,808,5') == 5.808
    assert f.parse('1.2.3') == 123.0
    assert f.parse('-5') == -5.0
    assert f.parse('12,') == 12.0
    with pytest.raises(ParseException):
        f.parse('-')
    with pytest.raises(ParseException):
        f.parse('.,')
    english = DecimalFormat()
    assert english.format(1234.5) == '1,234.5'
    assert english.parse('1,234.5') == 1234.5


def test_java_round_and_url_encode():
    assert [java_round(x) for x in (0.5, 1.5, -0.5, -1.5, 0.49999999999999994, 2.4)] == [1, 2, 0, -1, 0, 2]
    assert java_url_encode('convert 6 pés to metric') == 'convert+6+p%C3%A9s+to+metric'
    assert java_url_encode("5'6\" ~*") == '5%276%22+%7E*'


class _Rule(AbstractUnitConversionRule):

    def get_id(self):
        return 'TEST_UNIT_CONVERSION'

    def get_description(self):
        return 'test'


def test_rule_with_default_format(demo_lt):
    """AbstractUnitConversionRule with the default (English) number format
    and messages"""
    from langtool.messages import messages_for
    rule = _Rule(messages_for('en'))
    assert rule.match(demo_lt.get_analyzed_sentence('It is 5 miles long.')) == []  # 'mi' is a whole word
    matches = rule.match(demo_lt.get_analyzed_sentence('It is 5 mi long.'))
    assert len(matches) == 1
    # (at most MAX_SUGGESTIONS + 1)
    assert matches[0].suggested_replacements == ['5 mi (ca. 8 km)', '5 mi (8.05 km)', '5 mi (ca. 8,047 m)',
                                                 '5 mi (8,046.72 m)', '5 mi (ca. 804,672 cm)', '5 mi (804,672 cm)']
    assert matches[0].message == 'Writing for an international audience? Consider adding the metric equivalent.'
    assert matches[0].url == 'http://www.wolframalpha.com/input/?i=convert+5+mi+to+metric'
    assert rule.match(demo_lt.get_analyzed_sentence('It is 5 km long.')) == []
    matches = rule.match(demo_lt.get_analyzed_sentence('It is 5 mi (12 km) long.'))
    assert [m.message for m in matches] == ["This unit conversion doesn't seem right. Do you want to correct it "
                                            "automatically?"]
    # anti-patterns: ranges and fractions
    assert rule.match(demo_lt.get_analyzed_sentence('It is 3-5 lb heavy.')) == []
