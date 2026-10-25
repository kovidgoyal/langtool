"""Port of org.languagetool.synthesis.GermanSynthesizer: the German word
form synthesizer (de/german_synth.dict with de/german_tags.txt, the number
speller of de/de.sor), which also supports compounds (the last part of a
compound is inflected)."""

import threading

from ...analysis import AnalyzedToken
from ...synthesis import BaseSynthesizer
from ...tools import java_split, lowercase_first_char, starts_with_lowercase, starts_with_uppercase, \
    uppercase_first_char

REMOVE = frozenset((
    'unsren', 'unsrem', 'unsres', 'unsre', 'unsern', 'unserm', 'unsrer',
    # old spellings still in the synthesizer dict:
    'angepaßt', 'beschloß', 'biß', 'entschloß', 'ergoß', 'faßt', 'genoß', 'paßt', 'paßte', 'preßt', 'preßte', 'riß',
    'schloß', 'streßtest', 'vergißt', 'verlaß', 'verläßt', 'vermiß', 'vermißt',
    'wißt', 'wußtest', 'wüßtest'))


class GermanSynthesizer(BaseSynthesizer):
    """German word form synthesizer. Forms whose first character has
    another case than the lemma's are not generated (except for the lemmas
    "mein" and "ich"), some forms (old spellings, "unsre" etc.) are
    removed, and if a lemma has no forms, it is split with the strict
    GermanCompoundTokenizer and the forms of its last part are used."""

    def __init__(self, dictionary, tags_path, resource_dir=None, number_speller=None, roman_numberer=None,
                 dictionary_path=None, download=True):
        super().__init__(dictionary, tags_path, 'de', resource_dir, number_speller, roman_numberer)
        self._dictionary_path = dictionary_path
        self._download = download

    def _compound_tokenizer(self):
        from .compound_tokenizer import get_strict_instance
        return get_strict_instance(self._dictionary_path, self._download)

    def lookup(self, lemma, pos_tag):
        lookup = super().lookup(lemma, pos_tag)
        results = []
        lc_lemma = starts_with_lowercase(lemma)
        for s in lookup:
            # don't inflect a lowercase lemma to an uppercase word and vice versa
            # https://github.com/languagetool-org/languagetool/issues/4712
            if lc_lemma == starts_with_lowercase(s) or lemma == 'mein' or (lemma == 'ich' and s not in REMOVE):
                results.append(s)  # mein/ich wegen Ihr/Sie
        return results

    def synthesize_for_tag_list(self, lemma, tags):
        """synthesizeForPosTags(lemma, acceptTag) for the possible tags
        accepted by acceptTag, given as a list (same result, faster: the
        dictionary is accessed directly, without the lookup caches)"""
        results = []
        lc_lemma = starts_with_lowercase(lemma)
        keep_all = lemma == 'mein'
        is_ich = lemma == 'ich'
        dict_lookup = self.dictionary._lookup if self.dictionary is not None else None
        manual = self.manual_synthesizer.map if self.manual_synthesizer is not None else None
        removals = [rs.map for rs in (self.removal_synthesizer, self.removal_synthesizer2) if rs is not None]
        for tag in tags:
            forms = [stem for stem, _ in dict_lookup(lemma + '|' + tag)] if dict_lookup is not None else []
            if manual is not None:
                mf = manual.get((lemma, tag))
                if mf:
                    forms.extend(mf)
            for rmap in removals:
                rf = rmap.get((lemma, tag))
                if rf:
                    forms = [x for x in forms if x not in rf]
            for s in forms:
                if lc_lemma == starts_with_lowercase(s) or keep_all or (is_ich and s not in REMOVE):
                    results.append(s)
        return self.remove_exceptions(results)

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        result = super().synthesize(token, pos_tag, pos_tag_regexp)
        if not result:
            return self._get_compound_forms(token, pos_tag, pos_tag_regexp)
        return [k for k in result if k not in REMOVE]

    def _get_compound_forms(self, token, pos_tag, pos_tag_regexp):
        lemma = token.lemma
        if lemma is None:
            return []  # splitWord(null) is empty
        parts = self._compound_tokenizer().tokenize(lemma)
        if not parts:
            return []
        maybe_hyphen = ''
        if len(parts) == 1:
            parts = java_split(lemma, '-')
            if len(parts) > 1:
                maybe_hyphen = '-'
        first_part = maybe_hyphen.join(parts[:-1])
        last_part = uppercase_first_char(parts[-1])
        uppercase_last_part = maybe_hyphen != '' and starts_with_uppercase(parts[-1])
        last_part_token = AnalyzedToken(last_part, pos_tag, last_part)
        last_part_forms = BaseSynthesizer.synthesize(self, last_part_token, pos_tag, pos_tag_regexp)
        results = {}  # LinkedHashSet, avoid dupes
        for part in last_part_forms:
            if uppercase_last_part:
                results[first_part + maybe_hyphen + part] = None
            else:
                results[first_part + maybe_hyphen + lowercase_first_char(part)] = None
        return list(results)


_lock = threading.Lock()
_instance = None


def create_german_synthesizer(language, spec=None):
    """A new GermanSynthesizer with the resources of the language (the
    synthesizer spec of its definition; de/de.sor is the number speller as
    in Java)."""
    from ...extensions import synthesizer_resources
    spec = dict(spec or language.get('synthesizer'))
    spec.setdefault('sor', 'de/de.sor')
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return GermanSynthesizer(dictionary, tags_path, language.resource_dir, number_speller, roman_numberer,
                             language.dictionary_path, language.download_dictionaries)


def get_german_synthesizer(language=None):
    """GermanSynthesizer.INSTANCE: the shared German synthesizer (created
    with the resources of the given language, by default de-DE, on first
    use)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                if language is None:
                    from ...api import get_language
                    language = get_language('de-DE')
                _instance = create_german_synthesizer(language)
    return _instance


def synthesizer_factory(language, spec):
    """The 'synthesizer' factory: German.createDefaultSynthesizer() returns
    GermanSynthesizer.INSTANCE"""
    return get_german_synthesizer(language)
