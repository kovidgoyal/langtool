"""Port of org.languagetool.tagging.ru.RussianTagger."""

from ...analysis import AnalyzedTokenReadings
from ...chunking import ChunkTag
from ...tagging import BaseTagger

# vowels with a combining acute accent: a word with one of them may not miss a "ё"
_STRESSED = ('е́', 'о́', 'а́', 'у́', 'и́', 'ю́', 'ы́', 'э́', 'я́')

# the stress marks (acute and grave accents) that are removed before tagging,
# and the modifier letter apostrophe that is used for the hard sign
_REPLACEMENTS = (
    ('о́', 'о'), ('а́', 'а'), ('е́', 'е'), ('у́', 'у'), ('и́', 'и'), ('ы́', 'ы'), ('э́', 'э'), ('ю́', 'ю'),
    ('я́', 'я'), ('о̀', 'о'), ('а̀', 'а'), ('ѐ', 'е'), ('у̀', 'у'), ('ѝ', 'и'), ('ы̀', 'ы'), ('э̀', 'э'),
    ('ю̀', 'ю'), ('я̀', 'я'), ('ʼ', 'ъ'))

_MAY_MISSING_YO = 'MayMissingYO'


class RussianTagger(BaseTagger):
    """Russian part-of-speech tagger: a BaseTagger for /ru/russian.dict (with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt; the
    dictionary was originally developed by www.aot.ru, the POS tagset is
    described in tagset.txt) with its own tag(): in tokens longer than one
    character the stress marks are removed and "ʼ" is replaced by "ъ" (the
    token text changes too); tokens with "е" but without "ё" and without
    stress marks get the chunk tag "MayMissingYO" if the word with all "е"
    replaced by "ё" (lowercase) is known to the word tagger. Locale("ru")
    has no special case mapping (str.lower here)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'ru', resource_dir)

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            may_missing_yo = False
            if len(word) > 1:
                if ('ё' not in word and 'Ё' not in word and ('е' in word or 'Е' in word)
                        and not any(s in word for s in _STRESSED)):
                    may_missing_yo = True
                for old, new in _REPLACEMENTS:
                    word = word.replace(old, new)
            atr = AnalyzedTokenReadings(self.get_analyzed_tokens(word), pos)
            if may_missing_yo:
                word_lc = word.lower().replace('е', 'ё')
                if not self.word_tagger.tag(word_lc):
                    may_missing_yo = False
            if may_missing_yo:
                atr.set_chunk_tags([ChunkTag(_MAY_MISSING_YO)])
            token_readings.append(atr)
            pos += len(word)
        return token_readings
