"""POS taggers. Port of org.languagetool.tagging.BaseTagger, ManualTagger,
CombiningTagger and MorfologikTagger."""

import os

from .analysis import AnalyzedToken, AnalyzedTokenReadings
from .tools import is_mixed_case, java_trim, uppercase_first_char


class TaggedWord:
    __slots__ = ('lemma', 'pos_tag')

    def __init__(self, lemma, pos_tag):
        self.lemma = lemma
        self.pos_tag = pos_tag

    def __eq__(self, o):
        return isinstance(o, TaggedWord) and self.lemma == o.lemma and self.pos_tag == o.pos_tag

    def __hash__(self):
        return hash((self.lemma, self.pos_tag))

    def __repr__(self):
        return '%s/%s' % (self.lemma, self.pos_tag)


def _java_split(line, sep):
    import regex
    if sep == '\t':
        parts = line.split('\t')
    else:
        from . import jregex
        parts = jregex.compile(sep).split(line)
    while parts and parts[-1] == '':
        parts.pop()
    return parts


def iter_manual_lines(paths):
    """Yield the (form, lemma, tag) triplets from LT manual tagger files."""
    for path in paths:
        sep = '\t'
        with open(path, encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                line = java_trim(line.rstrip('\r\n'))
                if line.startswith('#separatorRegExp='):
                    sep = line.replace('#separatorRegExp=', '')
                if not line or line[0] == '#':
                    continue
                if '#' in line:
                    line = java_trim(line[:line.index('#')])
                parts = _java_split(line, sep)
                if len(parts) != 3:
                    raise ValueError('Unknown line format in line %d of %s: %r' % (lineno, path, line))
                yield parts[0], parts[1], java_trim(parts[2])


class ManualTagger:

    def __init__(self, paths):
        self.map = {}
        for form, lemma, tag in iter_manual_lines(paths):
            self.map.setdefault(form, []).append(TaggedWord(lemma, tag))

    def tag(self, word):
        return self.map.get(word, ())


class MorfologikTagger:

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def tag(self, word):
        return [TaggedWord(stem, tag) for stem, tag in self.dictionary.lookup(word)]


class CombiningTagger:

    def __init__(self, tagger1, tagger2, removal_tagger=None, overwrite_with_second_tagger=False):
        self.tagger1 = tagger1
        self.tagger2 = tagger2
        self.removal_tagger = removal_tagger
        self.overwrite = overwrite_with_second_tagger

    def tag(self, word):
        result = list(self.tagger2.tag(word))
        if not (self.overwrite and result):
            result.extend(self.tagger1.tag(word))
        if self.removal_tagger is not None:
            removal = self.removal_tagger.tag(word)
            if removal:
                rs = set(removal)
                result = [t for t in result if t not in rs]
        return result


class DemoTagger:
    """Tags every token with a null tag."""

    def tag(self, sentence_tokens):
        out = []
        pos = 0
        for w in sentence_tokens:
            out.append(AnalyzedTokenReadings(AnalyzedToken(w, None, None), pos))
            pos += len(w)
        return out

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)

    def create_token(self, token, pos_tag):
        return AnalyzedToken(token, pos_tag, None)


class BaseTagger:
    """Dictionary based tagger, with manual additions (added.txt) and
    removals (removed.txt)."""

    def __init__(self, dictionary, lang_code, resource_dir=None, tag_lowercase_with_uppercase=True,
                 overwrite_with_manual_tagger=False, manual_additions=None, manual_removals=None):
        self.dictionary = dictionary
        self.lang_code = lang_code
        self.tag_lowercase_with_uppercase = tag_lowercase_with_uppercase
        self.overwrite_with_manual_tagger = overwrite_with_manual_tagger
        if manual_additions is None:
            manual_additions = ['added.txt', 'added_custom.txt']
        if manual_removals is None:
            manual_removals = ['removed.txt', 'removed_custom.txt']
        self.word_tagger = self._init_word_tagger(resource_dir, manual_additions, manual_removals)
        self._cache = {}

    def _init_word_tagger(self, resource_dir, additions, removals):
        mt = MorfologikTagger(self.dictionary) if self.dictionary is not None else _NullWordTagger()

        def existing(names):
            if resource_dir is None:
                return []
            return [os.path.join(resource_dir, n) for n in names if os.path.exists(os.path.join(resource_dir, n))]

        rem = existing(removals)
        removal_tagger = ManualTagger(rem) if rem else None
        add = existing(additions)
        if add:
            return CombiningTagger(mt, ManualTagger(add), removal_tagger, self.overwrite_with_manual_tagger)
        return mt

    def tag(self, sentence_tokens):
        out = []
        pos = 0
        for w in sentence_tokens:
            out.append(AnalyzedTokenReadings(self.get_analyzed_tokens(w), pos))
            pos += len(w)
        return out

    def get_analyzed_tokens(self, word):
        cached = self._cache.get(word)
        if cached is None:
            cached = tuple(self._compute_tags(word))
            if len(self._cache) > 100000:
                self._cache.clear()
            self._cache[word] = cached
        out = []
        for lemma, tag in cached:
            out.append(AnalyzedToken(word, tag, lemma))
        return out

    def _tagged(self, w):
        return [(t.lemma, t.pos_tag) for t in self.word_tagger.tag(w)]

    def _compute_tags(self, word):
        """Returns list of (lemma, tag) tuples; (None, None) for an unknown
        word."""
        result = []
        lower = self.to_lower(word)
        is_lower = word == lower
        is_mixed = is_mixed_case(word)
        tagger_tokens = self._tagged(word)
        lower_tokens = self._tagged(lower) if not is_lower else tagger_tokens
        result.extend(tagger_tokens)
        if not is_lower and not is_mixed:
            result.extend(lower_tokens)
        if self.tag_lowercase_with_uppercase and not lower_tokens and not tagger_tokens and is_lower:
            upper = self._tagged(uppercase_first_char(word))
            result.extend(upper)
        if not result:
            add = self.additional_tags(word)
            if add:
                result.extend(add)
        if not result:
            result.append((None, None))
        return result

    def to_lower(self, word):
        return word.lower()

    def additional_tags(self, word):
        """Hook for subclasses, returns list of (lemma, tag)."""
        return None

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)

    def create_token(self, token, pos_tag):
        return AnalyzedToken(token, pos_tag, None)


class _NullWordTagger:
    def tag(self, word):
        return ()
