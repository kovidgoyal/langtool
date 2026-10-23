"""Port of org.languagetool.tagging.pl.PolishTagger."""

import os

from ... import jregex
from ...rules.abstract_rules import load_word_list
from ...tagging import BaseTagger
from ...tools import is_mixed_case, java_split, uppercase_first_char

_NEGATION_PREFIX = 'nie'

# Comparative and superlative adverbs and adjectives, i.e. exactly the forms
# that "nie" may be joined to since the 2026 spelling reform. Matched against
# the whole tag, so that unrelated tags ending in similar strings (num:comp)
# are not caught.
_COMPAR_SUPERL = jregex.compile('(adv|adj:.+):(com|sup)')

# Shortest joined form worth trying: "nie" + a four-letter comparative.
_MIN_NEGATED_LENGTH = len(_NEGATION_PREFIX) + 4

_NEGATION_EXCEPTIONS_FILE = 'nie_compar_exceptions.txt'

_negation_exceptions_cache = {}


def _negation_exceptions(resource_dir):
    """The word list nie_compar_exceptions.txt (cached like
    CachingWordListLoader)."""
    path = os.path.join(resource_dir, _NEGATION_EXCEPTIONS_FILE) if resource_dir else None
    s = _negation_exceptions_cache.get(path)
    if s is None:
        s = _negation_exceptions_cache[path] = frozenset(load_word_list(path)) if path else frozenset()
    return s


def _split_tags(tagged):
    """PolishTagger.addTokens: a reading with a tag like
    "subst:sg:nom:m3+subst:sg:voc:m3" becomes one reading per tag."""
    out = []
    for lemma, tag in tagged:
        # StringTools.asString(null).split() would fail in Java; dictionary
        # readings always have a tag
        if tag is None:
            out.append((lemma, tag))
            continue
        for curr_tag in java_split(tag, '+'):
            out.append((lemma, curr_tag))
    return out


class PolishTagger(BaseTagger):
    """Polish part-of-speech tagger: a BaseTagger for /pl/polish.dict (with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt) with
    its own tag(): readings with several tags joined with '+' are split
    into one reading per tag; the lowercase readings are added for words
    that are not lowercase (also mixed case ones); lowercase words without
    readings are looked up with an uppercase first character; words still
    unknown get the additional tags of additional_tags() (a joined "nie" +
    comparative or superlative)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'pl', resource_dir)
        self.negation_exceptions = _negation_exceptions(resource_dir)

    def _compute_tags(self, word):
        result = []
        lower_word = self.to_lower(word)
        is_lowercase = word == lower_word
        # normal case
        result.extend(_split_tags(self._tagged(word)))
        if not is_lowercase:
            # lowercase
            result.extend(_split_tags(self._tagged(lower_word)))
        # uppercase
        if not result and is_lowercase:
            result.extend(_split_tags(self._tagged(uppercase_first_char(word))))
        # additional language-dependent tagging, e.g. joined "nie"
        if not result:
            add = self.additional_tags(word)
            if add:
                result.extend(_split_tags(add))
        if not result:
            result.append((None, None))
        return result

    def additional_tags(self, word):
        """Analyzes forms in which "nie" is joined to a comparative or
        superlative adverb or adjective, such as "nielepiej" or
        "nienajlepszy" (allowed as one word since the 2026 spelling reform,
        but not in the binary dictionary yet): the prefix is stripped and the
        remainder looked up. The lemma is the negated positive form. Returns
        a list of (lemma, tag), or None."""
        lower_word = self.to_lower(word)
        if (len(lower_word) < _MIN_NEGATED_LENGTH
                or not lower_word.startswith(_NEGATION_PREFIX)
                or is_mixed_case(word)
                or lower_word in self.negation_exceptions):
            return None
        # Only one lookup, so "nienielepiej" stays untagged. "nienajlepiej"
        # needs no extra handling, as "najlepiej" is in the dictionary already.
        base = lower_word[len(_NEGATION_PREFIX):]
        result = []
        for lemma, pos_tag in self._tagged(base):
            if pos_tag is not None and lemma is not None and _COMPAR_SUPERL.fullmatch(pos_tag):
                result.append((_NEGATION_PREFIX + lemma, pos_tag))
        return result or None
