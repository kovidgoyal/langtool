"""Port of org.languagetool.tagging.zh.ChineseTagger."""

from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tools import java_split


class ChineseTagger:
    """Tags the tokens of ChineseWordTokenizer ("word/nature"): the token is
    the word with the nature as POS tag (no lemma)."""

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
        if '/' not in word:
            return AnalyzedToken(' ', None, None)
        parts = java_split(word, '/')
        if parts[0] == '' and parts[-1] == 'w':
            # the word is (a run of) slashes, e.g. "///w"
            return AnalyzedToken(word[:-2], word[-1:], None)
        return AnalyzedToken(parts[0], parts[1], None)
