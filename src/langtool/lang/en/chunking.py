"""Port of org.languagetool.chunking.EnglishChunker and EnglishChunkFilter:
OpenNLP based chunker (with the OpenNLP tokenizer and POS tagger, see
langtool.opennlp). The models en-token.bin, en-pos-maxent.bin and
en-chunker.bin (OpenNLP 1.5 models from Maven Central, see
langtool.dictionaries) are loaded once and shared by all English
variants."""

import threading
import unicodedata

from ...chunking import ChunkTag, ChunkTaggedToken
from ...opennlp import ChunkerME, POSTaggerME, TokenizerME, java_length, java_string, load_package
from ...tools import java_split, java_trim

TOKENIZER_MODEL = 'en/en-token.bin'
POS_TAGGER_MODEL = 'en/en-pos-maxent.bin'
CHUNKER_MODEL = 'en/en-chunker.bin'

_models = None
_models_lock = threading.Lock()


def _load_models(language):
    """The (static, as in Java) tokenizer, POS tagger and chunker"""
    global _models
    with _models_lock:
        if _models is None:
            from ...dictionaries import locate

            def path(name):
                return locate(name, language.dictionary_path, language.download_dictionaries)
            _models = (TokenizerME(load_package(path(TOKENIZER_MODEL))),
                       POSTaggerME(load_package(path(POS_TAGGER_MODEL))),
                       ChunkerME(load_package(path(CHUNKER_MODEL))))
        return _models


_BEGIN_NOUN_PHRASE_TAG = ChunkTag('B-NP')
_IN_NOUN_PHRASE_TAG = ChunkTag('I-NP')
_SINGULAR, _PLURAL = 'SINGULAR', 'PLURAL'


class EnglishChunkFilter:
    """Port of org.languagetool.chunking.EnglishChunkFilter: our chunker
    detects noun phrases but not whether they are singular or plural noun
    phrases. We add this information here."""

    def filter(self, tokens):
        result = []
        new_chunk_tag = None
        for i, tagged_token in enumerate(tokens):
            chunk_tags = []
            if self._is_beginning_of_noun_phrase(tagged_token):
                chunk_type = self._get_chunk_type(tokens, i)
                if chunk_type == _SINGULAR or self._end_of_noun_phrase_is_singular(tokens, i):
                    chunk_tags.append(ChunkTag('B-NP-singular'))
                    new_chunk_tag = 'NP-singular'
                else:
                    chunk_tags.append(ChunkTag('B-NP-plural'))
                    new_chunk_tag = 'NP-plural'
            if new_chunk_tag is not None and self._is_end_of_noun_phrase(tokens, i):
                chunk_tags.append(ChunkTag('E-' + new_chunk_tag))
                new_chunk_tag = None
            if new_chunk_tag is not None and self._is_continuation_of_noun_phrase(tagged_token):
                chunk_tags.append(ChunkTag('I-' + new_chunk_tag))
            if chunk_tags:
                result.append(ChunkTaggedToken(tagged_token.token, chunk_tags, tagged_token.readings))
            else:
                result.append(tagged_token)
        return result

    def _end_of_noun_phrase_is_singular(self, tokens, i):
        for j in range(i, len(tokens)):
            if self._is_end_of_noun_phrase(tokens, j):
                return self._get_chunk_type(tokens, j) == _SINGULAR
        return False

    @staticmethod
    def _is_beginning_of_noun_phrase(tagged_token):
        return _BEGIN_NOUN_PHRASE_TAG in tagged_token.chunk_tags

    def _is_end_of_noun_phrase(self, tokens, i):
        if i > len(tokens) - 2:
            return True
        return not self._is_continuation_of_noun_phrase(tokens[i + 1])

    @staticmethod
    def _is_continuation_of_noun_phrase(tagged_token):
        return _IN_NOUN_PHRASE_TAG in tagged_token.chunk_tags

    def _get_chunk_type(self, tokens, chunk_start_pos):
        """Get the type of the chunk that starts at the given position."""
        is_plural = False
        for i in range(chunk_start_pos, len(tokens)):
            token = tokens[i]
            if not self._is_beginning_of_noun_phrase(token) and not self._is_continuation_of_noun_phrase(token):
                break
            # (Java: a disabled check for "and", e.g. "Tarzan and Jane" is a plural noun phrase)
            if self._has_noun_with_plural_reading(token):  # e.g. "ten books" is a plural noun phrase
                is_plural = True
        return _PLURAL if is_plural else _SINGULAR

    @staticmethod
    def _has_noun_with_plural_reading(token):
        if token.readings is not None:
            for analyzed_token in token.readings.readings:
                if analyzed_token.pos_tag == 'NNS':
                    return True
        return False


def _is_space_char(c):
    # Character.isSpaceChar
    return unicodedata.category(c) in ('Zs', 'Zl', 'Zp')


class EnglishChunker:
    """Port of org.languagetool.chunking.EnglishChunker: OpenNLP-based
    chunker. Also uses the OpenNLP tokenizer and POS tagger and maps the
    result to our own tokens (we have our own tokenizer), as far as
    trivially possible."""

    def __init__(self, language):
        self.language = language
        self.chunk_filter = EnglishChunkFilter()

    def _models(self):
        return _load_models(self.language)

    def add_chunk_tags(self, token_readings):
        orig_chunk_tags = self._get_chunk_tags_for_readings(token_readings)
        chunk_tags = self.chunk_filter.filter(orig_chunk_tags)
        self._assign_chunks_to_readings(chunk_tags)

    def _get_chunk_tags_for_readings(self, token_readings):
        sentence = java_string(''.join(t.token for t in token_readings))
        tokens = self._clean_zero_width_whitespaces(self.tokenize(sentence))
        tokenizer, pos_tagger, chunker = self._models()
        pos_tags = pos_tagger.tag(tokens)
        chunk_tags = chunker.chunk(tokens, pos_tags)
        if len(tokens) != len(pos_tags) or len(tokens) != len(chunk_tags):
            raise RuntimeError('Length of results must be the same: %d, %d, %d' % (
                len(tokens), len(pos_tags), len(chunk_tags)))
        return self._get_tokens_with_token_readings(token_readings, tokens, chunk_tags)

    @staticmethod
    def _clean_zero_width_whitespaces(tokens):
        """workaround for the add-on, which adds ZERO WIDTH NO-BREAK SPACE,
        which confuses the chunker"""
        clean_tokens = []
        for token in tokens:
            for split in java_split(token, '\ufeff'):
                clean_tokens.append('' if not split else token)
        return clean_tokens

    def tokenize(self, sentence):
        """The OpenNLP tokens of the sentence (a Java string, see
        langtool.opennlp.java_string)"""
        clean_string = sentence.replace('’', "'")  # this is the type of apostrophe that OpenNLP expects
        return self._models()[0].tokenize(clean_string)

    def _get_tokens_with_token_readings(self, token_readings, tokens, chunk_tags):
        # getAnalyzedTokenReadingsFor: only exact position matches, i.e. this
        # can only be used for a trivial mapping where tokens that are not
        # exactly at the same position will be skipped (e.g. the tokens of
        # "I'll": [I] ['ll] vs [I]['][ll])
        by_position = {}
        pos = 0
        for token_reading in token_readings:
            token = token_reading.token
            if not java_trim(token) or (len(token) == 1 and _is_space_char(token)):  # needed for non-breaking space
                continue  # the OpenNLP result has no whitespace, so we need to skip it
            end = pos + java_length(token)
            by_position.setdefault((pos, end), token_reading)
            pos = end
        result = []
        pos = 0
        for token, chunk_tag in zip(tokens, chunk_tags):
            end = pos + len(token)
            result.append(ChunkTaggedToken(token, [ChunkTag(chunk_tag)], by_position.get((pos, end))))
            pos = end
        return result

    @staticmethod
    def _assign_chunks_to_readings(chunk_tagged_tokens):
        for tagged_token in chunk_tagged_tokens:
            readings = tagged_token.readings
            if readings is not None:
                readings.set_chunk_tags(tagged_token.chunk_tags)
