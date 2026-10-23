"""Base classes of the data model. When the C extension is available these are
C types, which lets the C matching code access their fields directly.
Otherwise equivalent pure Python classes are used. Set the environment
variable LANGTOOL_PURE_PYTHON=1 to force the pure Python implementation."""

import os

speedups = None
if not os.environ.get('LANGTOOL_PURE_PYTHON'):
    try:
        from . import _speedups as speedups
    except ImportError:
        speedups = None

if speedups is not None:
    AnalyzedTokenBase = speedups.AnalyzedTokenBase
    AnalyzedTokenReadingsBase = speedups.AnalyzedTokenReadingsBase
    StringMatcherBase = speedups.StringMatcherBase
    PosTokenBase = speedups.PosTokenBase
    PatternTokenBase = speedups.PatternTokenBase
else:
    class AnalyzedTokenBase:
        __slots__ = ('token', 'pos_tag', 'lemma', 'lemma_or_token', '_lemma_or_token_lower', '_token_lower',
                     '_lemma_lower', 'whitespace_before', 'has_no_pos_tag')

    class AnalyzedTokenReadingsBase:
        __slots__ = ('readings', 'token', '_token_lower', 'chunk_tags', 'is_whitespace', 'is_linebreak',
                     'is_sentence_start', 'is_pos_tag_unknown', 'is_sentence_end', 'is_paragraph_end',
                     'whitespace_before', 'immunized', 'has_same_lemmas', 'ignored_by_speller',
                     'typographic_apostrophe')

    class StringMatcherBase:
        __slots__ = ('pattern', 'value', 'value_lower', 'values', 'compiled', 'cache', 'possible_values', 'kind',
                     'case_sensitive', 'is_regexp')

    class PosTokenBase:
        __slots__ = ('pos_tag', 'pos_pattern', 'negation', 'pos_unknown')

    class PatternTokenBase:
        __slots__ = ('text_matcher', 'pos_token', 'current_and_next_exceptions', 'previous_exceptions',
                     'unification_features', 'phrase_name', 'and_group', 'or_group', 'token_reference',
                     'chunk_tag', 'skip', 'max_occurrence', 'inflected', 'negation', 'test_whitespace',
                     'whitespace_before', 'inside_marker', 'exception_valid_next', 'may_be_omitted',
                     'test_string', 'unification_neutral', 'uni_negation', 'last_in_unification')
