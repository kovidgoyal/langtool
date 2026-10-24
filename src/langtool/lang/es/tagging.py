"""Port of org.languagetool.tagging.es.SpanishTagger."""

from ... import jregex
from ...analysis import AnalyzedTokenReadings
from ...tagging import BaseTagger
from ...tools import is_all_uppercase, is_emoji, is_mixed_case, java_equals_ignore_case, uppercase_first_char

_ADJ_PART_FS = jregex.compile('VMP00SF|A[QO].[FC]S.')
_VERB = jregex.compile('V.+')
_PREFIXES_FOR_VERBS = jregex.compile('(auto)([^r]...+)', jregex.IGNORECASE)
_PREFIXES_FOR_VERBS2 = jregex.compile('(autor)(r...+)', jregex.IGNORECASE)
_PREFIXES_FOR_ADJ = jregex.compile('(.+)-(.+)', jregex.IGNORECASE)
_ADJ = jregex.compile('AQ.+')
_ADJ_MS = jregex.compile('AQ.MS.|AQ.CS.|AQ.MN.')
_NO_PREFIXES_FOR_ADJ = jregex.compile('(anti|pre|ex|pro|afro|ultra|super|súper)', jregex.IGNORECASE)
# adjectives with prefix + more than two syllables
_PREFIXES_FOR_ADJECTIVES = jregex.compile('(super)(.*[aeiouàéèíòóïü].+[aeiouàéèíòóïü].*)', jregex.IGNORECASE)
_ADJ_VP = jregex.compile('AQ.*|V.P.*')
_MENTE = jregex.compile('^(.+)mente$')


class SpanishTagger(BaseTagger):
    """Spanish part-of-speech tagger: a BaseTagger for /es/es-ES.dict (with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt) with
    its own tag(): typographic apostrophes are replaced by typewriter
    apostrophes (in tokens longer than one character or after "l"/"d" or
    before "s"; the token text changes too and the readings are marked
    with the typographic apostrophe flag); words that are not lowercase and
    not mixed case also get the readings of the lowercase word, all
    uppercase words those of the word with only the first character
    uppercase (FRANCIA); unknown words that are not mixed case are tagged
    as adverbs (-mente after a feminine singular adjective or participle),
    as verbs with the prefix auto-, as adjectives with the prefix super- or
    as compound adjectives (económico-sociales); unknown emojis get the
    tag _emoji_. Locale("es") has no special case mapping (str.lower)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'es', resource_dir)

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        n = len(sentence_tokens)
        for i, word in enumerate(sentence_tokens):
            previous_word = sentence_tokens[i - 1] if i > 0 else ''
            next_word = sentence_tokens[i + 1] if i < n - 1 else ''
            contains_typographic_apostrophe = False
            if (len(word) > 1 or java_equals_ignore_case(previous_word, 'l')
                    or java_equals_ignore_case(previous_word, 'd') or java_equals_ignore_case(next_word, 's')):
                if '’' in word:
                    contains_typographic_apostrophe = True
                    word = word.replace('’', "'")
            atr = AnalyzedTokenReadings(self.get_analyzed_tokens(word), pos)
            if contains_typographic_apostrophe:
                atr.typographic_apostrophe = True
            token_readings.append(atr)
            pos += len(word)
        return token_readings

    def _compute_tags(self, word):
        result = []
        lower_word = self.to_lower(word)
        is_lowercase = word == lower_word
        is_mixed = is_mixed_case(word)
        is_all_upper = is_all_uppercase(word)
        # normal case:
        result.extend(self._tagged(word))
        # tag non-lowercase (alluppercase or startuppercase), but not mixedcase
        # word with lowercase word tags:
        if not is_lowercase and not is_mixed:
            result.extend(self._tagged(lower_word))
        # tag all-uppercase proper nouns (ex. FRANCIA)
        if is_all_upper:
            result.extend(self._tagged(uppercase_first_char(lower_word)))
        # additional tagging with prefixes
        if not result and not is_mixed:
            add = self.additional_tags(word)
            if add:
                result.extend(add)
        # emoji
        if not result and is_emoji(word):
            result.append(('_emoji_', '_emoji_'))
        if not result:
            result.append((None, None))
        return result

    def _lookup(self, word):
        """DictionaryLookup.lookup of the Morfologik dictionary (without
        the manual additions), as (lemma, tag) pairs"""
        return self.dictionary.lookup(word)

    def additional_tags(self, word):
        """Returns a list of (lemma, tag), or None (SpanishTagger.additionalTags)."""
        additional = []
        # Any well-formed adverb with suffix -mente is tagged as an adverb (RG)
        # adjective o participle feminine singular + -mente
        lower_word = self.to_lower(word)
        if lower_word.endswith('mente'):
            possible_adj = jregex.java_replace(_MENTE, '$1', lower_word)
            for _lemma, pos_tag in self._lookup(possible_adj):
                if pos_tag is not None and _ADJ_PART_FS.fullmatch(pos_tag):
                    additional.append((lower_word, 'RG'))
                    return additional
        # Any well-formed verb with prefixes is tagged as a verb copying the
        # original tags
        for prefixes in (_PREFIXES_FOR_VERBS, _PREFIXES_FOR_VERBS2):
            m = prefixes.fullmatch(word)
            if m:
                possible_verb = m.group(2).lower()
                for lemma, pos_tag in self._lookup(possible_verb):
                    if pos_tag is not None and _VERB.fullmatch(pos_tag):
                        additional.append((m.group(1).lower() + lemma, pos_tag))
                return additional
        # Any well-formed adjective with prefixes is tagged copying the
        # original tags
        m = _PREFIXES_FOR_ADJECTIVES.fullmatch(word)
        if m:
            possible_adj = m.group(2).lower()
            for lemma, pos_tag in self._lookup(possible_adj):
                if pos_tag is not None and _ADJ_VP.fullmatch(pos_tag):
                    additional.append((m.group(1).lower() + lemma, pos_tag))
            return additional
        m = _PREFIXES_FOR_ADJ.fullmatch(word)
        if m:
            possible_adj_prefix = m.group(1).lower()
            if not _NO_PREFIXES_FOR_ADJ.fullmatch(possible_adj_prefix):
                possible_adj = m.group(2).lower()
                prefix_matches = False
                adj_matches = False
                new_postag = ''
                new_lemma = ''
                for _lemma, pos_tag in self._lookup(possible_adj_prefix):
                    if pos_tag is not None and _ADJ_MS.fullmatch(pos_tag):
                        prefix_matches = True
                        break
                for lemma, pos_tag in self._lookup(possible_adj):
                    if pos_tag is not None and _ADJ.fullmatch(pos_tag):
                        adj_matches = True
                        new_postag = pos_tag
                        new_lemma = possible_adj_prefix + '-' + lemma
                        break
                if adj_matches and prefix_matches:
                    additional.append((new_lemma, new_postag))
                    return additional
        return None
