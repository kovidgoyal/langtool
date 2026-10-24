"""Irish rule filters (port of org.languagetool.rules.ga.IrishPartialPosTagFilter
and NoDisambiguationIrishPartialPosTagFilter)."""

from ...analysis import AnalyzedSentence
from ...rules.core_filters import PartialPosTagFilter


def _irish():
    from ...api import get_language
    return get_language('ga')


class IrishPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.ga.IrishPartialPosTagFilter: a
    PartialPosTagFilter for Irish that also runs the disambiguator. Note
    that the disambiguator is called with a single token (without sentence
    start), so only rules will apply that have a single <match> element."""

    def tag(self, token):
        irish = _irish()
        tags = irish.tagger.tag([token])
        disambiguated = irish.disambiguator.disambiguate(AnalyzedSentence(list(tags)))
        return list(disambiguated.tokens)


class NoDisambiguationIrishPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.ga.NoDisambiguationIrishPartialPosTagFilter:
    a PartialPosTagFilter for Irish that only tags the token (it does not
    run the disambiguator)."""

    def tag(self, token):
        return list(_irish().tagger.tag([token]))
