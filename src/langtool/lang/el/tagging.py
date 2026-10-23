"""Port of org.languagetool.tagging.el.GreekTagger and of the parts of the
library org.ioperm:morphology-el (org.ioperm.morphology.el.GreekAnalyzer,
Lemma, CharUtils) that it uses."""

from ...tagging import BaseTagger


def _to_lower(upper, last):
    """Port of org.ioperm.morphology.el.CharUtils.toLower: the lowercase of a
    Greek uppercase letter (final sigma if last), other characters are
    returned unchanged."""
    if upper == 'Σ':
        return 'ς' if last else 'σ'
    return _LOWER.get(upper, upper)


_LOWER = dict(zip('ΑΆΒΓΔΕΈΖΗΉΘΙΊΪΚΛΜΝΞΟΌΠΡΤΥΎΫΦΧΨΩΏ', 'αάβγδεέζηήθιίϊκλμνξοόπρτυύϋφχψωώ'))


class GreekAnalyzer:
    """Port of org.ioperm.morphology.el.GreekAnalyzer: a morphological
    analyzer for Greek, a lookup in the morfologik dictionary analysis.dict
    of the morphology-el jar (el/analysis.dict in the dictionary
    manifest)."""

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def get_lemma(self, word, capitalized):
        """The (lemma, tag) pairs of the word (the lemma and tag of a
        org.ioperm.morphology.el.Lemma, None if the dictionary has none). If
        capitalized, the first character of the word may be an uppercase
        letter: the lookup is repeated with it in lowercase."""
        result = list(self.dictionary.lookup(word))
        if capitalized and word:
            lower = _to_lower(word[0], False) + word[1:]
            for lemma in self.dictionary.lookup(lower):
                # Lemma.equals compares word form (the same here), lemma and tag
                if lemma not in result:
                    result.append(lemma)
        return result


class GreekTagger(BaseTagger):
    """Port of org.languagetool.tagging.el.GreekTagger: a BaseTagger for
    /el/greek.dict (with added.txt, removed.txt etc.); words it does not know
    are analyzed with the GreekAnalyzer (BaseTagger.additionalTags)."""

    def __init__(self, dictionary, analyzer_dictionary, resource_dir=None):
        super().__init__(dictionary, 'el', resource_dir)
        self.analyzer = GreekAnalyzer(analyzer_dictionary)

    def additional_tags(self, word):
        # new AnalyzedToken(word, lm.getTag(), lm.getLemma())
        return [(lemma, tag) for lemma, tag in self.analyzer.get_lemma(word, False)]
