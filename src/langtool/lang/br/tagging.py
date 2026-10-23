"""Port of org.languagetool.tagging.br.BretonTagger."""

from ... import jregex
from ...tagging import BaseTagger
from ...tools import uppercase_first_char

_PATTERN_SUFFIX = jregex.compile('(?iu)(..+)-(mañ|se|hont)$')


def _java_length(s):
    """String.length() (UTF-16 code units)"""
    return len(s) + sum(1 for c in s if ord(c) > 0xffff)


class BretonTagger(BaseTagger):
    """Breton part-of-speech tagger, based on the Breton dictionary from
    Apertium: a BaseTagger for /br/breton.dict (with added.txt,
    added_custom.txt, removed.txt and removed_custom.txt), whose tagging of a
    word is almost the same as BaseTagger's, except that the lowercase
    readings are added for every word that is not lowercase (no mixed case
    check), and that when probing the dictionary fails, it retries without
    the suffixes -mañ, -se, -hont. Java lowercases with Locale.getDefault()
    (str.lower here)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'br', resource_dir)

    def _compute_tags(self, word):
        if _java_length(word) > 50:
            # avoid excessively long computation times for long (probably artificial) tokens:
            return [(None, None)]
        probe_word = word
        # This loop happens when we need to retry probing the dictionary
        # which happens rarely when trying to remove suffixes -mañ, -se, etc.
        while True:
            readings = []
            lower_word = probe_word.lower()
            tagger_tokens = self._tagged(probe_word)
            lower_tagger_tokens = self._tagged(lower_word)
            is_lowercase = probe_word == lower_word

            # Normal case.
            readings.extend(tagger_tokens)
            if not is_lowercase:
                # Lowercase.
                readings.extend(lower_tagger_tokens)

            # Uppercase.
            if not lower_tagger_tokens and not tagger_tokens:
                if is_lowercase:
                    readings.extend(self._tagged(uppercase_first_char(probe_word)))
                if not readings:
                    m = _PATTERN_SUFFIX.search(probe_word)
                    if m:
                        # Remove the suffix and probe dictionary again.
                        # So given a word such as "xxx-mañ", we're going to
                        # try to probe the dictionary again with "xxx" this time.
                        probe_word = m.group(1)
                        continue
                    readings.append((None, None))
            return readings
