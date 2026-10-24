"""Port of org.languagetool.chunking.RussianChunker."""

import re

from ...chunking import ChunkTag, ChunkTaggedToken, TokenExpressionFactory
from ...openregex import RegularExpression

# phrase types (RussianChunker.PhraseType)
NP = 'NP'  # "noun phrase", B-NP for the first token and I-NP for the following tokens (like OpenNLP)
NPS = 'NPS'  # "noun phrase singular"
NPP = 'NPP'  # "noun phrase plural"
PP = 'PP'  # "prepositional phrase" and similar
MAY_MISSING_YO = 'MayMissingYO'
VP = 'VP'  # verb phrase
SBAR = 'SBAR'
ADJP = 'ADJP'  # participle
DPT = 'DPT'  # adverbial participle

_FILTER_TAGS = frozenset(('PP', 'NPP', 'NPS', 'MayMissingYO', 'VP', 'SBAR', 'ADJP', 'DPT'))
_FACTORY = TokenExpressionFactory(False)

_SYNTAX_EXPANSION = {
    '<NP>': '<chunk=B-NP> <chunk=I-NP>*',
    '<VP>': '<chunk=B-VP> <chunk=I-VP>*',
    '<ADJP>': '<chunk=B-ADJP> <chunk=I-ADJP>*',
    '<DPT>': '<chunk=B-DPT> <chunk=I-DPT>*',
}

# phrase types whose first token gets "B-<type>" and the following ones
# "I-<type>" (the other types are used as the chunk tag)
_BEGIN_INSIDE_TAGS = {
    NP: ('B-NP', 'I-NP'),
    NPP: ('B-NP-plural', 'I-NP-plural'),  # plural noun
    VP: ('B-VP', 'I-VP'),
    ADJP: ('B-ADJP', 'I-ADJP'),
    DPT: ('B-DPT', 'I-DPT'),
}

_O = ChunkTag('O')
_MAY_MISSING_YO_TAG = ChunkTag(MAY_MISSING_YO)

_debug = False


def set_debug(debug_mode):
    """For internal use only"""
    global _debug
    _debug = debug_mode


def is_debug():
    """For internal use only"""
    return _debug


class _RegularExpressionWithPhraseType:

    __slots__ = ('expression', 'phrase_type', 'overwrite')

    def __init__(self, expression, phrase_type, overwrite):
        self.expression = expression
        self.phrase_type = phrase_type
        self.overwrite = overwrite

    def __str__(self):
        return '%s <= %s (overwrite: %s)' % (self.phrase_type, self.expression, 'true' if self.overwrite else 'false')


def _build(expr, phrase_type, overwrite=False):
    expanded_expr = expr
    for key, value in _SYNTAX_EXPANSION.items():
        expanded_expr = expanded_expr.replace(key, value)
    return _RegularExpressionWithPhraseType(RegularExpression.compile(expanded_expr, _FACTORY.create),
                                            phrase_type, overwrite)


# REGEXES1 and REGEXES2 are OpenRegex expressions (see langtool.openregex
# and langtool.chunking.TokenPredicate for the syntax). REGEXES1 roughly
# emulates the behavior of the OpenNLP chunker by tagging the first token of
# a noun phrase with B-NP and the remaining ones with I-NP. REGEXES2 builds on
# those annotations to find complex noun phrases. The chunks are added to the
# existing chunks, unless overwrite is true, in which case existing chunks
# get overwritten.
_regexes = None


def _regex_lists():
    global _regexes
    if _regexes is None:
        regexes1 = [
            # Иванов Иван Иванович
            _build("<posre='NN:(Name|Fam|Patr):.*'> <posre='NN:(Name|Fam|Patr):.*'>+ ", NP, True),
            # Иванов И.И.
            _build("<posre='NN:Fam:.*'> <regexCS=[А-ЯЁ]> <.> <regexCS=[А-ЯЁ]> <.> ", NP, True),
            # И.И. Иванов
            _build("<regexCS=[А-ЯЁ]> <.> <regexCS=[А-ЯЁ]> <.> <posre='NN:Fam:.*'> ", NP, True),
            # verb+verb
            _build("<posre='VB:.*:.*' & !posre='NN:.*'>* ", VP, False),
            _build('<если>', SBAR),
            _build('<поэтому>', SBAR),
            # noun phrase
            _build("<posre='ADJ:Posit:.*:.*'> <posre='NN:(Anim|Inanim):.*' & !posre='NN:(Anim|Inanim):.*:(R|D|T|P)'> ",
                   NP, True),
            _build("<posre='ADJ:Posit:.*:.*'> <posre='NN:(Anim|Inanim):.*' & !posre='NN:(Anim|Inanim):.*:(R|D|T|P)'> "
                   "<posre='NN:(Anim|Inanim):.*'> ", NP, True),
            # adj -> participle phrase
            _build("<posre='ADJ:Posit:.*:.*'> <posre='NN:(Anim|Inanim):.*' & !posre='NN:(Anim|Inanim):.*:(Nom|V)'> "
                   "<posre='NN:(Anim|Inanim):.*:(Nom|V)' & !posre='NN:(Anim|Inanim):.*:(R|D|T|P)'> ", ADJP, True),
            # adverbial participle
            _build("<posre='DPT:.*:.*' & !pos='PREP'> ", DPT),
            _build("<posre='DPT:.*:.*' & !pos='PREP'> <posre='NN:.*:.*:(R|D|T|P)' > ", DPT, True),
            _build("<posre='DPT:.*:.*' & !pos='PREP'> <posre='PREP'> <posre='NN:.*:.*:(R|D|T|P)' > ", DPT, True),
            # participle
            _build("<posre='PT:.*:.*'> ", ADJP),
            _build("<posre='PT:.*:.*'> <pos='ADV' > ", ADJP, True),
            _build("<posre='PT:.*:.*'> <posre='NN:.*:.*:(R|D|T|P)' > ", ADJP, True),
            _build("<posre='PT:.*:.*'> <posre='PREP'> <posre='NN:.*:.*:(R|D|T|P|V)' > ", ADJP, True),
            _build("<posre='PT:.*:.*'> <posre='PREP'> <posre='ADJ:.*:.*:(R|D|T|P|V)' > "
                   "<posre='NN:.*:.*:(R|D|T|P|V)' > ", ADJP, True),
            _build("<posre='PT:.*:.*'> <posre='NN:(Anim|Inanim):.*' & !posre='NN:(Anim|Inanim):.*:(Nom|V)'> "
                   "<posre='NN:(Anim|Inanim):.*:(Nom|V)' & !posre='NN:(Anim|Inanim):.*:(R|D|T|P)'> ", ADJP, True),
            _build("<posre='PT:.*:.*'> <posre='PNN:.*' & !posre='PNN:.*:Nom:.*'> "
                   "<posre='NN:(Anim|Inanim):.*:(Nom|V)' & !posre='NN:(Anim|Inanim):.*:(R|D|T|P)'> ", ADJP, True),
            _build("<posre='PT:.*:.*'> <posre='ADJ:.*:.*' > ", ADJP, False),
            _build('<тов>', NP),  # simulate OpenNLP?!
        ]
        regexes2 = [
            # ===== plural and singular noun phrases, based on OpenNLP chunker output ===============
            # "Маша и Миша":
            _build('<posre=NN:Name:.*> <и> <posre=NN:Name:.*>', NPP, True),
            _build('<posre=NN:Name:.*> <или> <posre=NN:Name:.*>', NPP, True),
            # не + VB
            _build("<не> <posre='VB:.*:.*' & !posre='NN:.*'>* ", VP, False),
        ]
        _regexes = (regexes1, regexes2)
    return _regexes


def _get_chunk_tag(regex, match, i):
    tags = _BEGIN_INSIDE_TAGS.get(regex.phrase_type)
    if tags is not None:
        return ChunkTag(tags[0] if i == match.start_index() else tags[1])
    return ChunkTag(regex.phrase_type)


class RussianChunker:
    """A rule-based prototype Russian chunker (the post-disambiguation
    chunker of Russian), based on the idea of the German LanguageTool
    chunker. It has not been evaluated as a stand-alone chunker, it has only
    been used in the context of LanguageTool's error detection rules."""

    def __init__(self):
        _regex_lists()

    def add_chunk_tags(self, token_readings):
        chunk_tagged_tokens = self.get_basic_chunks(token_readings)
        for regex in _regex_lists()[1]:
            self._apply(regex, chunk_tagged_tokens)
        self._assign_chunks_to_readings(chunk_tagged_tokens)

    def get_basic_chunks(self, token_readings):
        chunk_tagged_tokens = []
        for token_reading in token_readings:
            if not token_reading.is_whitespace and _MAY_MISSING_YO_TAG not in token_reading.chunk_tags:
                chunk_tagged_tokens.append(ChunkTaggedToken(token_reading.token, [_O], token_reading))
        if _debug:
            print('=============== CHUNKER INPUT ===============')
            print(self._get_debug_string(chunk_tagged_tokens))
        for regex in _regex_lists()[0]:
            self._apply(regex, chunk_tagged_tokens)
        return chunk_tagged_tokens

    def _apply(self, regex, tokens):
        prev_debug = self._get_debug_string(tokens)
        try:
            affected_spans = self._do_apply_regex(regex, tokens)
        except Exception as e:
            raise RuntimeError("Could not apply chunk regexp '%s' to tokens: %s" % (regex, tokens)) from e
        debug = self._get_debug_string(tokens)
        if debug != prev_debug:
            self._print_debug_info(regex, affected_spans, debug)

    @staticmethod
    def _assign_chunks_to_readings(chunk_tagged_tokens):
        for tagged_token in chunk_tagged_tokens:
            readings = tagged_token.readings
            if readings is not None:
                readings.set_chunk_tags(tagged_token.chunk_tags)

    @staticmethod
    def _do_apply_regex(regex, tokens):
        matches = regex.expression.find_all(tokens)
        affected_spans = []
        for match in matches:
            affected_spans.append((match.start_index(), match.end_index()))
            for i in range(match.start_index(), match.end_index()):
                token = tokens[i]
                new_chunk_tags = list(token.chunk_tags)
                if regex.overwrite:
                    new_chunk_tags = [t for t in new_chunk_tags if t.chunk_tag not in _FILTER_TAGS]
                new_tag = _get_chunk_tag(regex, match, i)
                if new_tag not in new_chunk_tags:
                    new_chunk_tags.append(new_tag)
                    if _O in new_chunk_tags:
                        new_chunk_tags.remove(_O)
                tokens[i] = ChunkTaggedToken(token.token, new_chunk_tags, token.readings)
        return affected_spans

    @staticmethod
    def _print_debug_info(regex, affected_spans, debug):
        print('=== Applied %s ===' % regex)
        if regex.overwrite:
            print('Note: overwrite mode, replacing old [%s] tags' % ', '.join(sorted(_FILTER_TAGS)))
        debug_lines = debug.split('\n')
        while debug_lines and not debug_lines[-1]:
            debug_lines.pop()  # String.split() drops trailing empty strings
        for i, debug_line in enumerate(debug_lines):
            if any(start <= i < end for start, end in affected_spans):
                print(re.sub('^  ', ' *', debug_line, count=1))
            else:
                print(debug_line)
        print()

    @staticmethod
    def _get_debug_string(tokens):
        if not _debug:
            return ''
        sb = []
        for token in tokens:
            token_reading_str = str(token.readings).replace(token.token + '[', '[', 1)
            sb.append('  %s -- %s\n' % (token, token_reading_str))
        return ''.join(sb)
