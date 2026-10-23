"""Port of org.languagetool.tools.StringToolsTest (only for the functions
that exist in langtool.tools). Not ported: assureSet, toId, readStream,
readerToString, escapeXML/escapeHTML, listToString, filterXML, asString,
stringForSpeller (not part of langtool.tools)."""

import pytest

from langtool import tools


def test_is_all_uppercase():
    assert tools.is_all_uppercase('A')
    assert tools.is_all_uppercase('ABC')
    assert tools.is_all_uppercase('ASV-EDR')
    assert tools.is_all_uppercase('ASV-ÖÄÜ')
    assert tools.is_all_uppercase('')

    assert not tools.is_all_uppercase('ß')
    assert not tools.is_all_uppercase('AAAAAAAAAAAAq')
    assert not tools.is_all_uppercase('a')
    assert not tools.is_all_uppercase('abc')


def test_is_mixed_case():
    assert tools.is_mixed_case('AbC')
    assert tools.is_mixed_case('MixedCase')
    assert tools.is_mixed_case('iPod')
    assert tools.is_mixed_case('AbCdE')

    assert not tools.is_mixed_case('')
    assert not tools.is_mixed_case('ABC')
    assert not tools.is_mixed_case('abc')
    assert not tools.is_mixed_case('!')
    assert not tools.is_mixed_case('Word')


def test_is_capitalized_word():
    assert tools.is_capitalized_word('Abc')
    assert tools.is_capitalized_word('Uppercase')
    assert tools.is_capitalized_word('Ipod')

    assert not tools.is_capitalized_word('')
    assert not tools.is_capitalized_word('ABC')
    assert not tools.is_capitalized_word('abc')
    assert not tools.is_capitalized_word('!')
    assert not tools.is_capitalized_word('wOrD')


def test_starts_with_uppercase():
    assert tools.starts_with_uppercase('A')
    assert tools.starts_with_uppercase('ÄÖ')

    assert not tools.starts_with_uppercase('')
    assert not tools.starts_with_uppercase('ß')
    assert not tools.starts_with_uppercase('-')


def test_uppercase_first_char():
    assert tools.uppercase_first_char(None) is None
    assert tools.uppercase_first_char('') == ''
    assert tools.uppercase_first_char('A') == 'A'
    assert tools.uppercase_first_char('öäü') == 'Öäü'
    assert tools.uppercase_first_char('ßa') == 'ßa'
    assert tools.uppercase_first_char("'test'") == "'Test'"
    assert tools.uppercase_first_char("''test") == "''Test"
    assert tools.uppercase_first_char("''t") == "''T"
    assert tools.uppercase_first_char("'''") == "'''"


def test_lowercase_first_char():
    assert tools.lowercase_first_char(None) is None
    assert tools.lowercase_first_char('') == ''
    assert tools.lowercase_first_char('A') == 'a'
    assert tools.lowercase_first_char('Öäü') == 'öäü'
    assert tools.lowercase_first_char('ßa') == 'ßa'
    assert tools.lowercase_first_char("'Test'") == "'test'"
    assert tools.lowercase_first_char("''Test") == "''test"
    assert tools.lowercase_first_char("''T") == "''t"
    assert tools.lowercase_first_char("'''") == "'''"


def test_contains_line_break():
    assert not tools.contains_line_break('')
    assert not tools.contains_line_break('foo bar')
    assert not tools.contains_line_break('foo\tbar')
    assert tools.contains_line_break('foo\nbar')
    assert tools.contains_line_break('foo\rbar')
    assert tools.contains_line_break('foo\r\nbar')
    assert tools.contains_line_break('foo\fbar')
    assert tools.contains_line_break('foo\u000Bbar')
    assert tools.contains_line_break('foo\u0085bar')
    assert tools.contains_line_break('foo bar')
    assert tools.contains_line_break('foo bar')


def test_is_all_whitespace():
    assert tools.is_all_whitespace('')
    assert tools.is_all_whitespace('   ')
    assert tools.is_all_whitespace('  \t')
    assert not tools.is_all_whitespace(' foo ')
    assert not tools.is_all_whitespace('foo')


def test_trim_whitespace():
    with pytest.raises((TypeError, AttributeError)):  # Java: NullPointerException
        tools.trim_whitespace(None)
    assert tools.trim_whitespace('') == ''
    assert tools.trim_whitespace(' ') == ''
    assert tools.trim_whitespace(' \nXX\t Y') == 'XXY'
    assert tools.trim_whitespace(' \r\nXX\t Y') == 'XXY'
    assert tools.trim_whitespace('word') == 'word'
    # only one space in the middle of the word is significant:
    assert tools.trim_whitespace('1 234,56') == '1 234,56'
    assert tools.trim_whitespace('1  234,56') == '1234,56'


def test_add_space(demo_language):
    xx = demo_language.short_code
    assert tools.add_space('word', xx) == ' '
    assert tools.add_space(',', xx) == ''
    assert tools.add_space('.', 'fr') == ''
    assert tools.add_space('.', 'de') == ''
    assert tools.add_space('!', 'fr') == ' '
    assert tools.add_space('!', 'de') == ''


def test_is_whitespace():
    assert tools.is_whitespace('﻿') is True
    assert tools.is_whitespace('  ') is True
    assert tools.is_whitespace('\t') is True
    assert tools.is_whitespace(' ') is True
    # non-breaking space is also a whitespace
    assert tools.is_whitespace(' ') is True
    assert tools.is_whitespace('abc') is False
    # non-breaking OOo field
    assert tools.is_whitespace('\\u02') is False
    assert tools.is_whitespace('\u0001') is False
    # narrow nbsp:
    assert tools.is_whitespace(' ') is True


def test_is_positive_number():
    assert tools.is_positive_number('3') is True
    assert tools.is_positive_number('a') is False


def test_is_empty():
    assert tools.is_empty('') is True
    assert tools.is_empty(None) is True
    assert tools.is_empty('a') is False


def test_is_camel_case():
    assert not tools.is_camel_case('abc')
    assert not tools.is_camel_case('ABC')
    assert tools.is_camel_case('iSomething')
    assert tools.is_camel_case('iSomeThing')
    assert tools.is_camel_case('mRNA')
    assert tools.is_camel_case('microRNA')
    assert tools.is_camel_case('microSomething')
    assert tools.is_camel_case('iSomeTHING')


def test_titlecase_global():
    assert tools.titlecase_global('the lord of the rings') == 'The Lord of the Rings'
    assert tools.titlecase_global('rhythm And blues') == 'Rhythm and Blues'
    assert tools.titlecase_global('memória de leitura') == 'Memória de Leitura'
    assert tools.titlecase_global('fond du lac') == 'Fond du Lac'
    assert tools.titlecase_global('el niño de Las islas') == 'El Niño de las Islas'


def test_all_start_with_lowercase():
    assert tools.all_start_with_lowercase('the lord of the rings')
    assert not tools.all_start_with_lowercase('the Fellowship of the Ring')
    assert tools.all_start_with_lowercase('bilbo')
    assert not tools.all_start_with_lowercase('Baggins')


def test_trim_special_characters():
    # StringTools.trimSpecialCharacters: keeps whitespace, letters, digits and punctuation
    assert tools.trim_special_characters('ott­.') == 'ott.'
    assert tools.trim_special_characters('Dez€ember 3, ß') == 'Dezember 3, ß'
    assert tools.trim_special_characters('a b-c!') == 'a b-c!'


def test_is_junit_test():
    # TestHackHelper.isJUnitTest: true when called from a pytest test
    assert tools.is_junit_test()
