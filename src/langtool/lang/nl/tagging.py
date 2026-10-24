"""Port of org.languagetool.tagging.nl.DutchTagger."""

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import BaseTagger
from ...tools import is_all_uppercase, is_mixed_case, uppercase_first_char

_PATTERN1 = [(jregex.compile('([^aeiouáéíóú])(%s)([^aeiouáéíóú])' % acc), '$1%s$3' % plain)
             for acc, plain in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'))]
# the allowed accented characters, replaced literally
_CHAR_PATTERNS = (('áá', 'aa'), ('áé', 'ae'), ('áí', 'ai'), ('áú', 'au'), ('éé', 'ee'), ('éí', 'ei'),
                  ('éú', 'eu'), ('íé', 'ie'), ('óé', 'oe'), ('óí', 'oi'), ('óó', 'oo'), ('óú', 'ou'),
                  ('úí', 'ui'), ('úú', 'uu'), ('íj', 'ij'))
_PATTERN2 = [(jregex.compile('(^|[^aeiou])%s([^aeiou]|$)' % acc), '$1%s$2' % plain)
             for acc, plain in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'))]
_HYPHEN1_PATTERN = jregex.compile('(^.*)-(.*$)')
_HYPHEN2_PATTERN = jregex.compile('([a-z])-([a-z])')

_ALWAYS_NEEDS_HET = frozenset(('patroon', 'punt', 'gemaal', 'weer', 'kussen', 'deel'))
_ALWAYS_NEEDS_DE = frozenset(('keten', 'boor', 'dans'))
_ALWAYS_NEEDS_MRV = frozenset(('pies', 'koeken', 'heden'))

_CACHE_SIZE = 100000


class DutchTagger(BaseTagger):
    """Dutch part-of-speech tagger: a BaseTagger for /nl/dutch.dict (with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt) with
    custom code to deal with words carrying optional accents (like "kómen")
    and unknown compound words (CompoundAcceptor). Typographic apostrophes
    are looked up as typewriter apostrophes. Words only found after
    removing accents or hyphens are ignored by the speller, unless they are
    lowercase and the dictionary knows them with an uppercase first
    character. Locale("nl") has no special case mapping (str.lower here)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'nl', resource_dir)
        self.resource_dir = resource_dir
        self._compound_acceptor = None

    @property
    def compound_acceptor(self):
        """The CompoundAcceptor that uses this tagger (Java:
        Dutch.getCompoundAcceptor(), CompoundAcceptor.INSTANCE)."""
        a = self._compound_acceptor
        if a is None:
            from .compound_acceptor import CompoundAcceptor
            a = self._compound_acceptor = CompoundAcceptor(self, self.resource_dir)
        return a

    def _tagged_tokens(self, token, word):
        """asAnalyzedTokenListForTaggedWords(token, getWordTagger().tag(word))
        as a list of (token, tag, lemma)"""
        return [(token, tag, lemma) for lemma, tag in self._tagged(word)]

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            readings, ignore_spelling = self._cached_tags(word)
            atr = AnalyzedTokenReadings([AnalyzedToken(t, tag, lemma) for t, tag, lemma in readings], pos)
            if ignore_spelling:
                atr.ignore_spelling()
            token_readings.append(atr)
            pos += len(word)
        return token_readings

    def get_analyzed_tokens(self, word):
        return [AnalyzedToken(t, tag, lemma) for t, tag, lemma in self._cached_tags(word)[0]]

    def _cached_tags(self, word):
        cached = self._cache.get(word)
        if cached is None:
            cached = self._compute(word)
            if len(self._cache) > _CACHE_SIZE:
                self._cache.clear()
            self._cache[word] = cached
        return cached

    def _compute(self, word):
        """Returns (tuple of (token, tag, lemma), ignore_spelling)."""
        ignore_spelling = False
        # make treatment of weird apostrophes same as in tokenizer (R. Baars, 2020-11-06)
        original_word = word
        word = word.replace('`', "'").replace('’', "'").replace('‘', "'").replace('´', "'")
        readings = []
        lower_word = self.to_lower(word)
        is_lowercase = word == lower_word
        is_mixed = is_mixed_case(word)
        is_all_upper = is_all_uppercase(word)
        # assign tokens for flattened word to original word; normal case:
        readings.extend(self._tagged_tokens(original_word, word))
        # tag non-lowercase (alluppercase or startuppercase), but not mixedcase
        # word with lowercase word tags:
        if not is_lowercase and not is_mixed:
            readings.extend(self._tagged_tokens(original_word, lower_word))
        # tag all-uppercase proper nouns
        if not readings and is_all_upper:
            readings.extend(self._tagged_tokens(original_word, uppercase_first_char(lower_word)))
        if not readings:
            # there is still no postag found
            word2 = word
            # remove single accented characters
            for p, repl in _PATTERN1:
                word2 = jregex.java_replace(p, repl, word2)
            # remove allowed accented characters
            for acc, plain in _CHAR_PATTERNS:
                word2 = word2.replace(acc, plain)
            for p, repl in _PATTERN2:
                word2 = jregex.java_replace(p, repl, word2)
            # best would be to check the parts as well (uncompound)
            if '-' in word2:
                part2 = jregex.java_replace(_HYPHEN1_PATTERN, '$2', word2)
                if self._tagged(part2):
                    # word is split on a likely location
                    word2 = jregex.java_replace(_HYPHEN2_PATTERN, '$1$2', word2)
            if word2 != word:
                l2 = self._tagged_tokens(original_word, word2)
                if l2:
                    # woord bestaat
                    readings.extend(l2)
                    ignore_spelling = True
            # Tag unknown compound words:
            if not readings and len(word) > 5:
                self._tag_compound(word, readings)
        if not readings:
            readings.append((original_word, None, None))
        if ignore_spelling and is_lowercase:
            # it might be a word that needs captials! Check this in dictionary
            if self._tagged(uppercase_first_char(original_word)):
                # there is an uppercased form in the dictionary; so this one is probably
                # wrong (Java clears the list of readings here, which has no effect, as
                # the readings have been copied already)
                ignore_spelling = False
        return tuple(readings), ignore_spelling

    def _tag_compound(self, word, readings):
        parts = self.compound_acceptor.get_parts(word)
        if len(parts) != 2:
            return
        part1, part2 = parts
        part1lc = part1.lower()
        for part2_reading in self.tag([part2])[0].readings:
            tag = part2_reading.pos_tag
            if tag is None:
                continue
            # if part1 ends with a hyphen, check if we are dealing with geographical compound word
            if part1.endswith('-') and tag.startswith('ENM:LOC'):
                readings.append((word, tag, part2))
                break
            if tag.startswith('ZNW'):
                if part2 in _ALWAYS_NEEDS_HET:
                    new_tag = 'ZNW:EKV:HET'
                elif part2 in _ALWAYS_NEEDS_DE:
                    new_tag = 'ZNW:EKV:DE_'
                elif part2 in _ALWAYS_NEEDS_MRV:
                    new_tag = 'ZNW:MRV:DE_'
                else:
                    new_tag = tag
                readings.append((word, new_tag, part1lc + part2_reading.lemma))
                # if any of these lists contain part2 of the compound, exit the loop after adding a single tag
                if part2 in _ALWAYS_NEEDS_HET or part2 in _ALWAYS_NEEDS_DE or part2 in _ALWAYS_NEEDS_MRV:
                    break

    def get_postags(self, word):
        """Tags without the compound handling (prevents the tagger from
        passing the value back to CompoundAcceptor, going into a tagging
        loop): a list of AnalyzedToken."""
        return [AnalyzedToken(word, tag, lemma) for lemma, tag in self._tagged(word)]
