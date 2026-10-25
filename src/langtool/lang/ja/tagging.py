"""Port of org.languagetool.tagging.ja.JapaneseTagger."""

from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tools import java_split


class JapaneseTagger:
    """Tags the tokens of JapaneseWordTokenizer ("surface partOfSpeech
    basicForm"): the token is the surface with the part of speech as POS tag
    and the basic form as lemma."""

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            at = self._as_analyzed_token(word)
            token_readings.append(AnalyzedTokenReadings(at, pos))
            pos += len(at.token)
        return token_readings

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)

    def create_token(self, token, pos_tag):
        return AnalyzedToken(token, pos_tag, None)

    @staticmethod
    def _as_analyzed_token(word):
        parts = java_split(word, ' ')
        if len(parts) != 3:
            return AnalyzedToken(' ', None, None)
        return AnalyzedToken(parts[0], parts[1], parts[2])
