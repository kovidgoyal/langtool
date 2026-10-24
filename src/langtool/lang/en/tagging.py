"""Port of org.languagetool.tagging.en.EnglishTagger."""

from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import BaseTagger
from ...tools import is_all_uppercase, is_mixed_case, uppercase_first_char


class EnglishTagger(BaseTagger):
    """English part-of-speech tagger: a BaseTagger for /en/english.dict
    (with added.txt, added_custom.txt, removed.txt and removed_custom.txt;
    no lookup of lowercase words with an uppercase first character) with
    its own tag(): typographic apostrophes of tokens longer than one
    character are replaced by typewriter apostrophes (the token text
    changes too, the token is marked as having a typographic apostrophe);
    words that are not lowercase and not mixed case also get the readings of
    the lowercase word; unknown all-uppercase words are looked up with an
    uppercase first character only (proper nouns like FRANCE), unknown
    words ending in "in'" as words ending in "ing" ("doin'"). The tagset is
    described in /en/tagset.txt. Locale.ENGLISH has no special case
    mapping (str.lower here)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'en', resource_dir, tag_lowercase_with_uppercase=False)

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            # This hack allows all rules and dictionary entries to work with typewriter apostrophe
            contains_typographic_apostrophe = False
            if len(word) > 1 and '’' in word:
                contains_typographic_apostrophe = True
                word = word.replace('’', "'")
            atr = AnalyzedTokenReadings(self.get_analyzed_tokens(word), pos)
            if contains_typographic_apostrophe:
                atr.typographic_apostrophe = True
            token_readings.append(atr)
            pos += len(word)
        return token_readings

    def _compute_tags(self, word):
        """The (lemma, tag) pairs of EnglishTagger.tag for a word"""
        result = []
        lower_word = word.lower()
        is_lowercase = word == lower_word
        is_mixed = is_mixed_case(word)
        is_all_upper = is_all_uppercase(word)
        # normal case:
        result.extend(self._tagged(word))
        # tag non-lowercase (alluppercase or startuppercase), but not mixed-case words with lowercase word tags:
        if not is_lowercase and not is_mixed:
            result.extend(self._tagged(lower_word))
        # tag all-uppercase proper nouns (ex. FRANCE)
        if not result and is_all_upper:
            result.extend(self._tagged(uppercase_first_char(lower_word)))
        if not result and lower_word.endswith("in'"):
            corrected_word = word[:-1] + ('G' if is_all_upper else 'g')
            # normal case:
            result.extend(self._tagged(corrected_word))
            # tag non-lowercase (alluppercase or startuppercase), but not mixed-case words with lowercase word tags:
            if not is_lowercase and not is_mixed:
                result.extend(self._tagged(corrected_word.lower()))
        if not result:
            result.append((None, None))
        return result

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)
