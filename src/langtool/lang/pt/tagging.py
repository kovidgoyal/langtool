"""Port of org.languagetool.tagging.pt.PortugueseTagger."""

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...chunking import ChunkTag
from ...tagging import BaseTagger
from ...tools import is_mixed_case

_ADJ_PART_FS = jregex.compile('V.P..SF.|A[QO].[FC][SN].')
_VERB = jregex.compile('V.+')
# TODO: add more, we will need this
# Removed 're' and 'auto' because of 'reune', 'autossabotar', etc.; we need more robust logic for this elsewhere
_PREFIXES_FOR_VERBS = jregex.compile('(soto-)(...+)', jregex.IGNORECASE)
_ORDINAL_SUFFIX_MASC = 'oºᵒ'
_ORDINAL_SUFFIX_FEM = 'aªᵃ'
_ORDINAL_SUFFIX_PL = 'sˢ'
_ORDINAL_SUFFIXES = '[%s%s][%s]?' % (_ORDINAL_SUFFIX_MASC, _ORDINAL_SUFFIX_FEM, _ORDINAL_SUFFIX_PL)
_ORDINAL_SUFFIXES_PATTERN = jregex.compile(_ORDINAL_SUFFIXES)
_ORDINAL_PATTERN = jregex.compile('^\\d+[\\d,.]*\\.?' + _ORDINAL_SUFFIXES + '$')
_ORDINAL_MASC_SG = jregex.compile('[%s]$' % _ORDINAL_SUFFIX_MASC)
_ORDINAL_FEM_SG = jregex.compile('[%s]$' % _ORDINAL_SUFFIX_FEM)
_ORDINAL_MASC_PL = jregex.compile('[%s][%s]$' % (_ORDINAL_SUFFIX_MASC, _ORDINAL_SUFFIX_PL))
_ORDINAL_FEM_PL = jregex.compile('[%s][%s]$' % (_ORDINAL_SUFFIX_FEM, _ORDINAL_SUFFIX_PL))
_PERCENT_PATTERN = jregex.compile('−?\\d+[\\d,.]*%')
_DEGREE_PATTERN = jregex.compile('−?\\d+[\\d,.]*°')
_MENTE = jregex.compile('^(.+)mente$')

_CONTAINS_TYPEWRITER_APOSTROPHE = 'containsTypewriterApostrophe'


def _tag_number_expressions(word):
    """tagNumberExpressions: ordinals (1.º, 2ª, ...), degrees and percentages,
    as (lemma, tag) pairs"""
    if _ORDINAL_PATTERN.fullmatch(word):
        return _build_ordinal_tokens(word)
    if _DEGREE_PATTERN.fullmatch(word):
        return [(word, 'NCMP000')]
    if _PERCENT_PATTERN.fullmatch(word):
        # TODO: remove "PERCENTAGES" disambiguator rule
        return [(word, 'NCMP000')]
    return []


def _build_ordinal_tokens(word):
    # The lemma has the ordinal indicator form, this is arbitrary
    # It also keeps the ".", since we need to keep those forms distinct
    lemma = jregex.java_replace(_ORDINAL_SUFFIXES_PATTERN, 'º', word)
    number_gender_tags = ''
    if _ORDINAL_MASC_SG.search(word):
        number_gender_tags = 'MS'
    if _ORDINAL_FEM_SG.search(word):
        number_gender_tags = 'FS'
    if _ORDINAL_MASC_PL.search(word):
        number_gender_tags = 'MP'
    if _ORDINAL_FEM_PL.search(word):
        number_gender_tags = 'FP'
    return [(lemma, 'NC%s000' % number_gender_tags), (lemma, 'AO0%s0' % number_gender_tags)]


class PortugueseTagger(BaseTagger):
    """Portuguese part-of-speech tagger: a BaseTagger for /pt/portuguese.dict
    (with added.txt, added_custom.txt, removed.txt and removed_custom.txt)
    with its own tag(): typographic apostrophes of tokens longer than one
    character are replaced by typewriter apostrophes (the token text
    changes too) and tokens that contained a typewriter apostrophe get the
    chunk tag "containsTypewriterApostrophe"; the lowercase readings are
    added for words that are not lowercase and not mixed case (a hyphenated
    word is mixed case only if one of its parts is); there is no lookup
    with an uppercase first character. Unknown words are tagged as ordinals,
    degrees or percentages, and (if not mixed case) as adverbs of manner
    (-mente after a feminine singular adjective or participle) or as verbs
    with the prefix soto- (these are ignored by the speller).
    Locale("pt") has no special case mapping (str.lower here)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'pt', resource_dir)

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            # This hack allows all rules and dictionary entries to work with typewriter apostrophe
            contains_typewriter_apostrophe = False
            if len(word) > 1:
                if "'" in word:
                    contains_typewriter_apostrophe = True
                word = word.replace('’', "'")
            tags, ignore_spelling = self._cached_tags(word)
            atr = AnalyzedTokenReadings([AnalyzedToken(word, tag, lemma) for lemma, tag in tags], pos)
            if ignore_spelling:
                atr.ignore_spelling()
            if contains_typewriter_apostrophe:
                atr.set_chunk_tags([ChunkTag(_CONTAINS_TYPEWRITER_APOSTROPHE)])
            token_readings.append(atr)
            pos += len(word)
        return token_readings

    def get_analyzed_tokens(self, word):
        return [AnalyzedToken(word, tag, lemma) for lemma, tag in self._cached_tags(word)[0]]

    def _cached_tags(self, word):
        cached = self._cache.get(word)
        if cached is None:
            cached = self._compute(word)
            if len(self._cache) > 100000:
                self._cache.clear()
            self._cache[word] = cached
        return cached

    def _compute(self, word):
        """Returns ((lemma, tag) pairs, ignore_spelling)"""
        # to be used in case we also want to make sure this isn't flagged as a spelling error later
        # but we don't want to pass a blank cheque to the spell checker from the tagger
        ignore_spelling = False
        result = []
        lower_word = self.to_lower(word)
        is_lowercase = word == lower_word
        # if the word contains a hyphen, it is only mixed case if at least one element is mixed case
        if '-' in word:
            is_mixed = any(is_mixed_case(part) for part in word.split('-'))
        else:
            # No hyphens found, just do a regular isMixedCase check
            is_mixed = is_mixed_case(word)
        # normal case, i.e. something is found
        result.extend(self._tagged(word))
        # tag non-lowercase (alluppercase or startuppercase), but not mixedcase
        # word with lowercase word tags:
        if not is_lowercase and not is_mixed:
            result.extend(self._tagged(lower_word))
        # tag ordinals and percentages, i.e. expressions that include digits
        if not result:
            result.extend(_tag_number_expressions(word))
        # additional tagging with adverbs ending in -mente
        if not result and not is_mixed:
            result.extend(self._tag_mente_adverbs(word, lower_word))
        # additional tagging with prefixes for verbs
        if not result and not is_mixed:
            result.extend(self._tag_prefixed_verbs(word))
            if result:
                ignore_spelling = True
        if not result:
            result.append((None, None))
        return tuple(result), ignore_spelling

    def _tag_mente_adverbs(self, word, lower_word):
        """Any well-formed adverb with suffix -mente is tagged as an adverb of
        manner (RG); the Morfologik dictionary is looked up (not the manual
        additions)"""
        if word.endswith('mente'):
            possible_adj = jregex.java_replace(_MENTE, '$1', lower_word)
            for _lemma, pos_tag in self.dictionary.lookup(possible_adj):
                if pos_tag is not None and _ADJ_PART_FS.fullmatch(pos_tag):
                    return [(lower_word, 'RG')]
        return []

    def _tag_prefixed_verbs(self, word):
        """Any well-formed verb with prefixes is tagged as a verb copying the
        original tags (if the prefixed lemma is not in the dictionary)"""
        additional = []
        m = _PREFIXES_FOR_VERBS.fullmatch(word)
        if m:
            prefix = m.group(1).lower()
            possible_verb = m.group(2).lower()
            for lemma, pos_tag in self.dictionary.lookup(possible_verb):
                if pos_tag is not None and _VERB.fullmatch(pos_tag):
                    new_lemma = prefix + lemma
                    if not self.dictionary.lookup(new_lemma):
                        additional.append((new_lemma, pos_tag))
        return additional
