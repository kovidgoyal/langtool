"""Port of org.languagetool.synthesis.en.EnglishSynthesizer."""

from ... import jregex
from ...synthesis import SPELLNUMBER_TAG, BaseSynthesizer
from ...tools import lowercase_first_char_if_capitalized
from .avsan import suggest_a_or_an

_EXCEPTIONS = frozenset(("ne'er", "e'er", "o'er", "ol'", "ma'am", "n't", 'informations'))
# A special tag to add determiners.
ADD_DETERMINER = '+DT'
# A special tag to add only indefinite articles.
ADD_IND_DETERMINER = '+INDT'


class EnglishSynthesizer(BaseSynthesizer):
    """English word form synthesizer (/en/english_synth.dict with
    /en/english_tags.txt and the number speller of /en/en.sor). There are
    two special additions: +DT, a tag that adds "a" or "an" (according to
    the way the word is pronounced) and "the", and +INDT, a tag that adds
    only "a" or "an". Forms starting with an apostrophe ('ve, 's, 're...)
    and some others (ne'er, n't, informations...) are removed."""

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        if pos_tag.startswith(SPELLNUMBER_TAG):
            return super().synthesize(token, pos_tag)
        if pos_tag_regexp:
            # Special English regexp based synthesizer that allows adding articles
            # when the regexp-based tag ends with a special signature \\+INDT or \\+DT.
            my_pos_tag = pos_tag
            det = ''
            if pos_tag.endswith(ADD_IND_DETERMINER):
                my_pos_tag = my_pos_tag[:my_pos_tag.find(ADD_IND_DETERMINER) - len('\\')]
                det = suggest_a_or_an(token.lemma)
                det = det[:det.find(' ') + len(' ')]
            elif pos_tag.endswith(ADD_DETERMINER):
                my_pos_tag = my_pos_tag[:my_pos_tag.find(ADD_DETERMINER) - len('\\')]
                det = 'the '
            p = jregex.compile(my_pos_tag)
            results = []
            if token.lemma is not None:
                for tag in self.tags_matching(p):
                    for result in self.lookup(token.lemma, tag):
                        results.append(det + result)
            return self.remove_exceptions(results)
        a_or_an = suggest_a_or_an(token.token)
        if pos_tag == ADD_DETERMINER:
            return [a_or_an, 'the ' + lowercase_first_char_if_capitalized(token.token)]
        if pos_tag == ADD_IND_DETERMINER:
            return [a_or_an]
        return self.remove_exceptions(super().synthesize(token, pos_tag))

    def is_exception(self, w):
        # remove: 've, 's, 're...
        return w.startswith("'") or w in _EXCEPTIONS
