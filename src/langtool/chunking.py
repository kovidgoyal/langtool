"""Chunk tags, port of org.languagetool.chunking.ChunkTag."""

from . import jregex


class ChunkTag:
    __slots__ = ('chunk_tag', 'is_regexp', '_pattern')

    def __init__(self, chunk_tag, is_regexp=False):
        if chunk_tag is None or not chunk_tag.strip():
            raise ValueError('chunkTag cannot be null or empty: %r' % chunk_tag)
        self.chunk_tag = chunk_tag
        self.is_regexp = is_regexp
        self._pattern = None

    @property
    def pattern(self):
        if self.is_regexp and self._pattern is None:
            self._pattern = jregex.compile(self.chunk_tag)
        return self._pattern

    def matches(self, tag):
        if self.is_regexp:
            return self.pattern.fullmatch(tag.chunk_tag) is not None
        return self.chunk_tag == tag.chunk_tag

    def __eq__(self, o):
        if self is o:
            return True
        if not isinstance(o, ChunkTag):
            return NotImplemented
        return self.chunk_tag == o.chunk_tag

    def __hash__(self):
        return hash(self.chunk_tag)

    def __repr__(self):
        return self.chunk_tag + ('[regex]' if self.is_regexp else '')

    __str__ = __repr__
