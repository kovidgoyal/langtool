"""Galician rule filters (port of org.languagetool.rules.gl filters)."""

from ...rules.core_filters import AbstractAdvancedSynthesizerFilter


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.gl.AdvancedSynthesizerFilter: the
    AbstractAdvancedSynthesizerFilter without changes (synthesize
    suggestions using the lemma from one token and the POS tag from
    another one)."""
