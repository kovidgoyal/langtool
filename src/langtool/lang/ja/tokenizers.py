"""Port of org.languagetool.tokenizers.ja.JapaneseWordTokenizer."""

from ...dictionaries import locate
from . import sen


class JapaneseWordTokenizer:
    """Splits a text into morphemes with the Sen morphological analyzer of
    lucene-gosen (SenFactory.getStringTagger(null, false), see
    langtool.lang.ja.sen). Each token is "surface partOfSpeech basicForm"
    (the basic form is the surface for morphemes without one), which
    JapaneseTagger splits again. Spaces, tabs and line breaks are not part
    of any token.

    Sen works on UTF-16 code units: a character outside the BMP is not in the
    dictionary and becomes two unknown morphemes in Java, one for each
    surrogate. Here they are one token (the character, with the part of
    speech of the first one), so that the token positions are character
    positions like everywhere in langtool."""

    def __init__(self, dictionary_path=None, download=True):
        self.string_tagger = sen.get_string_tagger(
            lambda name: locate('ja/' + name, dictionary_path, download))

    def tokenize(self, text):
        ret = []
        try:
            tokens = self.string_tagger.analyze(text)
        except sen.TooManyResultsError:
            return ret  # Java catches the exception and returns the empty list
        high_surrogate = None
        for token in tokens:
            surface = token.surface
            morpheme = token.morpheme
            if high_surrogate is not None and len(surface) == 1 and '\udc00' <= surface <= '\udfff':
                c = (high_surrogate[0] + surface).encode('utf-16-le', 'surrogatepass').decode('utf-16-le')
                ret[-1] = c + ' ' + high_surrogate[1] + ' ' + c
                high_surrogate = None
                continue
            basic_form = morpheme.basic_form
            if basic_form == '*':
                basic_form = surface
            ret.append(surface + ' ' + morpheme.part_of_speech + ' ' + basic_form)
            high_surrogate = (surface, morpheme.part_of_speech) \
                if len(surface) == 1 and '\ud800' <= surface <= '\udbff' else None
        return ret
