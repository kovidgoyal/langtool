"""Port of org.languagetool.tagging.fr.FrenchTagger."""

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...chunking import ChunkTag
from ...rules.multitoken import convert_to_title_case_iterating_chars
from ...tagging import BaseTagger
from ...tools import is_all_uppercase, is_capitalized_word, is_emoji

_VERB = jregex.compile('V .+')
_PREFIXES_FOR_VERBS = jregex.compile('(auto|auto-|re-|sur-)([^-].*[aeiouêàéèíòóïü].+[aeiouêàéèíòóïü].*)',
                                     jregex.IGNORECASE)
_NOUN_ADJ = jregex.compile('[NJ] .+|V ppa.*')
_PREFIXES_NOUN_ADJ = jregex.compile(
    '(post-|sur-|mini-|méga-|demi-|péri-|anti-|géo-|nord-|sud-|néo-|méga-|ultra-|pro-|inter-|micro-|macro-|sous-|'
    'haut-|auto-|ré-|pré-|super-|vice-|hyper-|proto-|grand-|pseudo-)(.+)', jregex.IGNORECASE)
_PREFIXES_FOR_NOUN_ADJ = jregex.compile('(mini|méga)([^-].*[aeiouêàéèíòóïü].+[aeiouêàéèíòóïü].*)', jregex.IGNORECASE)

_AMBIGUOUS_TOKENS = frozenset(('-Le', '-Les', '-La', '-Elle', '-Elles', '-On', '-Tu', '-Vous', '-Il', '-Ils', '-Ce'))

_CACHE_SIZE = 100000


class FrenchTagger(BaseTagger):
    """French part-of-speech tagger (Dicollecte based /fr/french.dict with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt, the
    manual additions don't overwrite the dictionary). Typographic
    apostrophes are looked up as typewriter apostrophes (in tokens longer
    than one character, the token text changes too); tokens with
    apostrophes get the chunk tag containsTypewriterApostrophe or
    containsTypographicApostrophe. Uppercase words (all uppercase,
    capitalized or hyphenated title case like Saint-Étienne) also get the
    readings of the lowercase word, unknown all uppercase words those of
    the title case word; unknown words with "oe" are looked up with "œ";
    unknown words with some prefixes (auto-, re-, mini-, anti-, ...) get
    the verb, noun or adjective readings of the word without the prefix;
    unknown emojis get the tag _emoji_. Locale.FRENCH has no special case
    mapping (str.lower)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'fr', resource_dir, tag_lowercase_with_uppercase=False)

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            # This hack allows all rules and dictionary entries to work with
            # typewriter apostrophe
            contains_typewriter_apostrophe = False
            contains_typographic_apostrophe = False
            if len(word) > 1:
                if "'" in word:
                    contains_typewriter_apostrophe = True
                if '’' in word:
                    contains_typographic_apostrophe = True
                    word = word.replace('’', "'")
            atr = AnalyzedTokenReadings([AnalyzedToken(t, tag, lemma) for t, tag, lemma in self._cached_tags(word)],
                                        pos)
            if contains_typewriter_apostrophe:
                atr.set_chunk_tags([ChunkTag('containsTypewriterApostrophe')])
            if contains_typographic_apostrophe:
                atr.set_chunk_tags([ChunkTag('containsTypographicApostrophe')])
            token_readings.append(atr)
            pos += len(word)
        return token_readings

    def get_analyzed_tokens(self, word):
        return [AnalyzedToken(t, tag, lemma) for t, tag, lemma in self._cached_tags(word)]

    def _cached_tags(self, word):
        cached = self._cache.get(word)
        if cached is None:
            cached = tuple(self._compute(word))
            if len(self._cache) > _CACHE_SIZE:
                self._cache.clear()
            self._cache[word] = cached
        return cached

    def _compute(self, word):
        """The readings of a word as (token, tag, lemma) tuples."""
        result = self._tag_word(word, word)
        if not result and 'oe' in word.lower():
            result = self._tag_word(word.replace('oe', 'œ').replace('OE', 'Œ'), word)
        # emoji
        if not result and is_emoji(word):
            result.append((word, '_emoji_', '_emoji_'))
        if not result:
            result.append((word, None, None))
        return result

    def _tagged_tokens(self, token, word):
        """asAnalyzedTokenListForTaggedWords(token, getWordTagger().tag(word))
        as a list of (token, tag, lemma)"""
        return [(token, tag, lemma) for lemma, tag in self._tagged(word)]

    def _tag_word(self, word, original_word):
        result = []
        lower_word = word.lower()
        is_start_upper = is_capitalized_word(word)
        is_all_upper = is_all_uppercase(word)
        is_hyphenated_title_case = (original_word not in _AMBIGUOUS_TOKENS and '-' in original_word
                                    and original_word == convert_to_title_case_iterating_chars(lower_word))
        # normal case:
        result.extend(self._tagged_tokens(original_word, word))
        # tag non-lowercase (alluppercase, startuppercase, hyphenated title case),
        # but not mixedcase word, with lowercase word tags:
        if is_all_upper or is_start_upper or is_hyphenated_title_case:
            result.extend(self._tagged_tokens(original_word, lower_word))
        # tag all-uppercase proper nouns (ex. FRANCE)
        if not result and is_all_upper:
            first_upper = convert_to_title_case_iterating_chars(lower_word)
            result.extend(self._tagged_tokens(original_word, first_upper))
        # additional tagging with prefixes removed: && !isMixedCase
        if not result:
            add = self.additional_tags(word)
            if add:
                result.extend((word, tag, lemma) for lemma, tag in add)
        return result

    def additional_tags(self, word):
        """FrenchTagger.additionalTags: a list of (lemma, tag), or None"""
        additional = []
        # Any well-formed verb with prefixes is tagged as a verb copying the original tags
        m = _PREFIXES_FOR_VERBS.fullmatch(word)
        if m:
            possible_verb = m.group(2).lower()
            for lemma, pos_tag in self._tagged(possible_verb):
                if pos_tag is not None and _VERB.fullmatch(pos_tag):
                    additional.append((m.group(1).lower() + lemma, pos_tag))
            if additional:
                return additional
        # Any well-formed verb with prefixes is tagged as a verb copying the original tags
        m = _PREFIXES_FOR_NOUN_ADJ.fullmatch(word)
        if m:
            possible_noun = m.group(2).lower()
            for lemma, pos_tag in self._tagged(possible_noun):
                if pos_tag is not None and _NOUN_ADJ.fullmatch(pos_tag):
                    additional.append((m.group(1).lower() + lemma, pos_tag))
            if additional:
                return additional
        m = _PREFIXES_NOUN_ADJ.fullmatch(word)
        if m:
            possible_noun = m.group(2).lower()
            for lemma, pos_tag in self._tagged(possible_noun):
                if pos_tag is not None and _NOUN_ADJ.fullmatch(pos_tag):
                    additional.append((m.group(1).lower() + lemma, pos_tag))
            # with lower case
            if not additional:
                for lemma, pos_tag in self._tagged(possible_noun.lower()):
                    if pos_tag is not None and _NOUN_ADJ.fullmatch(pos_tag):
                        additional.append((m.group(1).lower() + lemma, pos_tag))
            return additional
        return None
