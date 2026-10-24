"""Tests of langtool.spelling, the misspelling check of the morfologik
spellers (morfologik's Speller.isMisspelled, MorfologikMultiSpeller,
MorfologikSpellerRule.isMisspelled and the word lists of
SpellingCheckRule). The binary dictionaries are tested with Dutch in
tests/lang/test_nl_rules.py."""

import pytest

from langtool.fsa import DictionaryMetadata, read_properties
from langtool.spelling import (MorfologikSpeller, SpellerMetadata, _PlainWords, java_to_lower,
                               read_plain_text_lines)


def _speller(lines, info=''):
    md = SpellerMetadata(DictionaryMetadata(read_properties('fsa.dict.separator=+\nfsa.dict.encoding=utf-8\n'
                                                            'fsa.dict.encoder=SUFFIX\n' + info)))
    return MorfologikSpeller(_PlainWords([s.encode('utf-8') for s in lines], md.separator), md)


def test_defaults():
    # DictionaryMetadata.DEFAULT_ATTRIBUTES: all ignore flags and convert-case are on
    s = _speller(['huis', 'Amsterdam', 'iPad', 'woord+x'])
    md = s.md
    assert md.ignore_punctuation and md.ignore_numbers and md.ignore_camel_case and md.ignore_all_uppercase
    assert md.convert_case
    assert not s.is_misspelled('huis')
    assert s.is_misspelled('hius')
    # case conversion: capitalized and all uppercase words are looked up in lowercase,
    # all uppercase words also with an uppercase first letter
    assert not s.is_misspelled('Huis')
    assert not s.is_misspelled('AMSTERDAM')  # (also ignore-all-uppercase)
    assert s.is_misspelled('amsterdam')
    assert not s.is_misspelled('HuisBoot')  # camel case ignored
    assert not s.is_misspelled('abc1')  # numbers ignored
    assert not s.is_misspelled('.')  # punctuation ignored
    assert s.is_misspelled('hUis')  # mixed case: no conversion
    # prefix followed by the separator
    assert not s.is_misspelled('woord')
    assert s.is_misspelled('woord+x')
    # LanguageTool is always accepted, the empty string is not misspelled
    assert not s.is_misspelled('LanguageTool')
    assert not s.is_misspelled('')


def test_flags_off():
    s = _speller(['huis', 'Amsterdam'], 'fsa.dict.speller.ignore-numbers=false\n'
                                        'fsa.dict.speller.ignore-all-uppercase=false\n'
                                        'fsa.dict.speller.ignore-camel-case=false\n'
                                        'fsa.dict.speller.ignore-punctuation=false\n'
                                        'fsa.dict.speller.convert-case=false\n'
                                        "fsa.dict.input-conversion=’ '\n")
    assert s.is_misspelled('abc1')
    assert s.is_misspelled('HuisBoot')
    assert s.is_misspelled('.')
    assert s.is_misspelled('Huis')
    assert s.is_misspelled('AMSTERDAM')
    assert not s.is_misspelled('Amsterdam')
    s = _speller(["oma's"], "fsa.dict.input-conversion=’ '\nfsa.dict.speller.convert-case=yes\n")
    assert not s.is_misspelled('oma’s')
    with pytest.raises(ValueError):
        _speller([], 'fsa.dict.speller.convert-case=maybe\n')


def test_locale():
    assert java_to_lower('ISTANBUL', 'tr') == 'ıstanbul'
    assert java_to_lower('İzmir', 'tr') == 'izmir'
    assert java_to_lower('ISTANBUL', 'nl') == 'istanbul'


def test_read_plain_text_lines(tmp_path):
    a = tmp_path / 'a.txt'
    b = tmp_path / 'b.txt'
    a.write_text('# comment\nwoord\n  spaties  \nmet # commentaar\n\n', encoding='utf-8')
    b.write_text('één\r\ntwee\rdrie', encoding='utf-8')
    assert read_plain_text_lines([str(a), str(b)]) == [
        b'woord', b'spaties', b'met', 'één'.encode('utf-8'), b'twee', b'drie']
    assert read_plain_text_lines([str(b)], lambda line: [line, line.upper()]) == [
        'één'.encode('utf-8'), 'ÉÉN'.encode('utf-8'), b'twee', b'TWEE', b'drie', b'DRIE']


def test_plain_text_speller_lines(tmp_path):
    """MorfologikMultiSpeller: the word list of the language variant
    (getLanguageVariantSpellingFileName) is added to the plain text word
    lists, with "LanguageTool", but only if there are plain text word
    lists"""
    from langtool.spelling import plain_text_speller_lines
    a = tmp_path / 'a.txt'
    v = tmp_path / 'v.txt'
    a.write_text('word\n', encoding='utf-8')
    v.write_text('colour\n# comment\n', encoding='utf-8')
    assert plain_text_speller_lines([str(a)]) == [b'word']
    assert plain_text_speller_lines([str(a)], None, str(v)) == [b'word', b'colour', b'LanguageTool']
    assert plain_text_speller_lines([], None, str(v)) == []


def test_weighted_suggestions():
    """The suggestions of the spellers keep their weights (SuggestedReplacement.getWeight())"""
    from langtool.spelling import WeightedStr, suggestion_weight
    s = WeightedStr('casa', 3)
    assert s == 'casa' and isinstance(s, str) and suggestion_weight(s) == 3
    assert suggestion_weight('casa') is None
    assert suggestion_weight(WeightedStr('casa')) is None


def test_sentence_has_match():
    """MorfologikMisspellingCheck.sentence_has_match: whether
    MorfologikSpellerRule.match(sentence) finds a spelling error (tokens that
    can be ignored are not checked)"""
    from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
    from langtool.spelling import MorfologikMisspellingCheck

    class Check(MorfologikMisspellingCheck):
        def __init__(self):
            super().__init__(None)
            self._ignored = frozenset(['ignorat'])
            self._prohibited = frozenset(['prohibit'])

        def is_misspelled(self, word):
            return word not in ('bo', 'prohibit')

        def converts_case(self):
            return False

    def sentence(*words, tagged=()):
        tokens = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)]
        pos = 0
        for w in words:
            tokens.append(AnalyzedTokenReadings([AnalyzedToken(w, 'X' if w in tagged else None, None)], pos))
            pos += len(w)
        return AnalyzedSentence(tokens)

    check = Check()
    assert not check.sentence_has_match(sentence('bo'))
    assert check.sentence_has_match(sentence('bo', 'dolent'))
    assert not check.sentence_has_match(sentence('ignorat', '123', 'http://example.com'))
    assert check.sentence_has_match(sentence('dolent', tagged=('dolent',)))
    assert not check.sentence_has_match(sentence('dolent', tagged=('dolent',)), ignore_tagged_words=True)
    # prohibited words are checked even if they are tagged
    assert check.sentence_has_match(sentence('prohibit', tagged=('prohibit',)), ignore_tagged_words=True)
