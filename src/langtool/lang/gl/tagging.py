"""Port of org.languagetool.tagging.gl.GalicianTagger."""

from ... import jregex
from ...analysis import AnalyzedTokenReadings
from ...chunking import ChunkTag
from ...tagging import BaseTagger
from ...tools import is_mixed_case

_ADJ_PART_FS = jregex.compile('V.P..SF.|A[QO].[FC][SN].')
_VERB = jregex.compile('V.+')
_PREFIXES_FOR_VERBS = jregex.compile('(auto|re)(...+)', jregex.IGNORECASE)
_MENTE = jregex.compile('^(.+)mente$')

_CONTAINS_TYPEWRITER_APOSTROPHE = 'containsTypewriterApostrophe'


class GalicianTagger(BaseTagger):
    """Galician part-of-speech tagger: a BaseTagger for /gl/galician.dict
    (with added.txt, added_custom.txt, removed.txt and removed_custom.txt)
    with its own tag(): typographic apostrophes of tokens longer than one
    character are replaced by typewriter apostrophes (the token text
    changes too) and tokens that contained a typewriter apostrophe get the
    chunk tag "containsTypewriterApostrophe"; the lowercase readings are
    added for words that are not lowercase and not mixed case (there is no
    lookup with an uppercase first character); unknown words that are not
    mixed case are tagged as adverbs of manner (-mente after a feminine
    adjective or participle) or as verbs with the prefixes auto-/re-.
    Locale("gl") has no special case mapping (str.lower here)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'gl', resource_dir)

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            # This hack allows all rules and dictionary entries to work with
            # typewriter apostrophe
            contains_typewriter_apostrophe = False
            if len(word) > 1:
                if "'" in word:
                    contains_typewriter_apostrophe = True
                word = word.replace('’', "'")
            atr = AnalyzedTokenReadings(self.get_analyzed_tokens(word), pos)
            if contains_typewriter_apostrophe:
                atr.set_chunk_tags([ChunkTag(_CONTAINS_TYPEWRITER_APOSTROPHE)])
            token_readings.append(atr)
            pos += len(word)
        return token_readings

    def _compute_tags(self, word):
        result = []
        lower_word = self.to_lower(word)
        is_lowercase = word == lower_word
        is_mixed = is_mixed_case(word)
        # normal case:
        result.extend(self._tagged(word))
        # tag non-lowercase (alluppercase or startuppercase), but not mixedcase
        # word with lowercase word tags:
        if not is_lowercase and not is_mixed:
            result.extend(self._tagged(lower_word))
        # additional tagging with prefixes
        if not result and not is_mixed:
            add = self.additional_tags(word)
            if add:
                result.extend(add)
        if not result:
            result.append((None, None))
        return result

    def additional_tags(self, word):
        """Returns a list of (lemma, tag), or None (GalicianTagger.additionalTags,
        which looks up the Morfologik dictionary only, not the manual
        additions)."""
        additional = []
        # Any well-formed adverb with suffix -mente is tagged as an adverb of manner (RM)
        if word.endswith('mente'):
            lower_word = self.to_lower(word)
            possible_adj = jregex.java_replace(_MENTE, '$1', lower_word)
            for _lemma, pos_tag in self.dictionary.lookup(possible_adj):
                if pos_tag is not None and _ADJ_PART_FS.fullmatch(pos_tag):
                    additional.append((lower_word, 'RM'))
                    return additional
        # Any well-formed verb with prefixes is tagged as a verb copying the original tags
        m = _PREFIXES_FOR_VERBS.fullmatch(word)
        if m:
            possible_verb = m.group(2).lower()
            for lemma, pos_tag in self.dictionary.lookup(possible_verb):
                if pos_tag is not None and _VERB.fullmatch(pos_tag):
                    additional.append((m.group(1).lower() + lemma, pos_tag))
            return additional
        return None
