"""Port of org.languagetool.rules.de.GermanTools."""

_VOWELS = 'aeiouyAEIOUYäöüÄÖÜ'


def is_vowel(c):
    """GermanTools.isVowel(char)"""
    return len(c) == 1 and c in _VOWELS
