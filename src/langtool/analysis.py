"""Analyzed tokens and sentences, the data model the rules operate on.

Port of org.languagetool.AnalyzedToken, AnalyzedTokenReadings and
AnalyzedSentence.
"""

import regex

from .tools import is_whitespace

SENTENCE_START_TAGNAME = 'SENT_START'
SENTENCE_END_TAGNAME = 'SENT_END'
PARAGRAPH_END_TAGNAME = 'PARA_END'

_NON_WORD_REGEX = regex.compile(r'[.?!…:;,~’\'"„“”»«‚‘›‹()\[\]\-–—*×∗·+÷/=]')


class AnalyzedToken:
    """A single reading of a token: the token text, its POS tag and lemma."""

    __slots__ = ('token', 'pos_tag', 'lemma', 'lemma_or_token', 'whitespace_before', 'has_no_pos_tag',
                 '_lemma_or_token_lower')

    def __init__(self, token, pos_tag=None, lemma=None):
        if token is None:
            raise ValueError('token cannot be None')
        self.token = token
        self.pos_tag = pos_tag.strip() if pos_tag is not None else None
        self.lemma = lemma
        self.lemma_or_token = token if lemma is None else lemma
        self.whitespace_before = False
        self.has_no_pos_tag = (pos_tag is None or pos_tag == SENTENCE_END_TAGNAME or pos_tag == PARAGRAPH_END_TAGNAME)
        self._lemma_or_token_lower = None

    @property
    def lemma_or_token_lower(self):
        r = self._lemma_or_token_lower
        if r is None:
            r = self._lemma_or_token_lower = self.lemma_or_token.lower()
        return r

    def has_no_tag(self):
        return self.has_no_pos_tag

    def matches(self, an):
        """Used to remove/filter readings: an empty token/lemma/postag in an
        acts as wildcard."""
        if self == an:
            return True
        if not an.token and an.lemma is None and an.pos_tag is None:
            return False
        found = True
        if an.token:
            found = an.token == self.token
        if an.lemma is not None:
            found = found and an.lemma == self.lemma
        if an.pos_tag is not None:
            found = found and an.pos_tag == self.pos_tag
        return found

    def copy(self):
        c = AnalyzedToken(self.token, self.pos_tag, self.lemma)
        c.whitespace_before = self.whitespace_before
        return c

    def __eq__(self, o):
        if self is o:
            return True
        if not isinstance(o, AnalyzedToken):
            return NotImplemented
        return (self.token == o.token and self.pos_tag == o.pos_tag and self.lemma == o.lemma
                and self.whitespace_before == o.whitespace_before)

    def __hash__(self):
        return hash((self.whitespace_before, self.lemma, self.pos_tag, self.token))

    def __repr__(self):
        return '%s/%s' % (self.lemma_or_token, self.pos_tag)

    __str__ = __repr__


def _is_linebreak(token):
    return token in ('\n', '\r\n', '\r', '\n\r')


class AnalyzedTokenReadings:
    """All readings of a token, plus token level information (position,
    whitespace, chunk tags, immunization...)."""

    __slots__ = ('readings', 'start_pos', 'pos_fix', 'token', '_token_lower', 'clean_token', 'chunk_tags',
                 'is_whitespace', 'is_linebreak', 'is_sentence_start', 'is_pos_tag_unknown', 'is_sentence_end',
                 'is_paragraph_end', 'whitespace_before', 'whitespace_before_char', 'typographic_apostrophe',
                 'immunized', 'immunization_source_line', 'ignored_by_speller', 'historical_annotations',
                 'has_same_lemmas', '__weakref__')

    def __init__(self, readings, start_pos=0):
        if isinstance(readings, AnalyzedToken):
            readings = [readings]
        else:
            readings = list(readings)
        self.readings = readings
        self.start_pos = start_pos
        self.pos_fix = 0
        first = readings[0]
        self.token = first.token
        self._token_lower = None
        self.clean_token = None
        self.chunk_tags = ()
        self.is_whitespace = is_whitespace(self.token)
        self.whitespace_before = first.whitespace_before
        self.is_linebreak = _is_linebreak(self.token)
        self.is_sentence_start = first.pos_tag == SENTENCE_START_TAGNAME
        self.is_paragraph_end = self.has_pos_tag(PARAGRAPH_END_TAGNAME)
        self.is_sentence_end = self.has_pos_tag(SENTENCE_END_TAGNAME)
        self.is_pos_tag_unknown = len(readings) == 1 and first.pos_tag is None
        self.whitespace_before_char = ''
        self.typographic_apostrophe = False
        self.immunized = False
        self.immunization_source_line = 0
        self.ignored_by_speller = False
        self.historical_annotations = ''
        self._set_no_real_pos_tag()
        self.has_same_lemmas = self._are_lemmas_same()

    @classmethod
    def from_old(cls, old, new_readings, rule_applied=''):
        """Port of AnalyzedTokenReadings(oldAtr, newReadings, ruleApplied)."""
        self = cls(new_readings, old.start_pos)
        if old.is_sentence_end:
            self.set_sentence_end()
        if old.is_paragraph_end:
            self.set_paragraph_end()
        self.set_whitespace_before(old.whitespace_before_char)
        self.chunk_tags = old.chunk_tags
        if old.immunized:
            self.immunize(old.immunization_source_line)
        if old.ignored_by_speller:
            self.ignored_by_speller = True
        if old.typographic_apostrophe:
            self.typographic_apostrophe = True
        return self

    # --- queries ---

    def __iter__(self):
        return iter(self.readings)

    def __len__(self):
        return len(self.readings)

    def __getitem__(self, i):
        return self.readings[i]

    @property
    def token_lower(self):
        r = self._token_lower
        if r is None:
            r = self._token_lower = self.token.lower()
        return r

    @property
    def end_pos(self):
        return self.start_pos + len(self.token)

    def has_pos_tag(self, pos_tag):
        for r in self.readings:
            if r.pos_tag == pos_tag:
                return True
        return False

    def has_pos_tag_and_lemma(self, pos_tag, lemma):
        for r in self.readings:
            if r.pos_tag == pos_tag and r.lemma == lemma:
                return True
        return False

    def has_lemma(self, lemma):
        for r in self.readings:
            if r.lemma is not None and r.lemma == lemma:
                return True
        return False

    def has_any_lemma(self, *lemmas):
        for lemma in lemmas:
            if self.has_lemma(lemma):
                return True
        return False

    def has_partial_pos_tag(self, pos_tag):
        for r in self.readings:
            if r.pos_tag is not None and pos_tag in r.pos_tag:
                return True
        return False

    def has_any_partial_pos_tag(self, *pos_tags):
        return any(self.has_partial_pos_tag(p) for p in pos_tags)

    def has_pos_tag_starting_with(self, pos_tag):
        for r in self.readings:
            if r.pos_tag is not None and r.pos_tag.startswith(pos_tag):
                return True
        return False

    def matches_pos_tag_regex(self, pattern):
        from . import jregex
        if isinstance(pattern, str):
            pattern = jregex.compile(pattern)
        for r in self.readings:
            if r.pos_tag is not None and pattern.fullmatch(r.pos_tag):
                return True
        return False

    def reading_with_tag_regex(self, pattern):
        from . import jregex
        if isinstance(pattern, str):
            pattern = jregex.compile(pattern)
        for r in self.readings:
            if r.pos_tag is not None and pattern.fullmatch(r.pos_tag):
                return r
        return None

    def reading_with_lemma(self, lemma):
        for r in self.readings:
            if r.lemma is not None and r.lemma == lemma:
                return r
        return None

    def matches_chunk_regex(self, chunk_regex):
        from . import jregex
        p = jregex.compile(chunk_regex)
        for c in self.chunk_tags:
            if p.fullmatch(c.chunk_tag):
                return True
        return False

    def has_reading(self):
        return bool(self.readings)

    def is_tagged(self):
        for r in self.readings:
            if not r.has_no_pos_tag:
                return True
        return False

    def is_non_word(self):
        return _NON_WORD_REGEX.fullmatch(self.token) is not None

    def is_field_code(self):
        return self.token in ('\u0001', '\u0002')

    def get_clean_token(self):
        return self.clean_token if self.clean_token is not None else self.token

    # --- modification ---

    def add_reading(self, token, rule_applied=''):
        l = list(self.readings[:-1])
        if self.readings[-1].pos_tag is not None:
            l.append(self.readings[-1])
        token.whitespace_before = self.whitespace_before
        l.append(token)
        self.readings = l
        if len(token.token) > len(self.token):
            self.token = token.token
            self._token_lower = None
        l[-1].whitespace_before = self.whitespace_before
        self.is_paragraph_end = self.has_pos_tag(PARAGRAPH_END_TAGNAME)
        self.is_sentence_end = self.has_pos_tag(SENTENCE_END_TAGNAME)
        self._set_no_real_pos_tag()
        self.has_same_lemmas = self._are_lemmas_same()

    def remove_reading(self, token, rule_applied=''):
        tmp = AnalyzedToken(token.token, token.pos_tag, token.lemma)
        tmp.whitespace_before = self.whitespace_before
        l = []
        removed_sent_end = removed_para_end = False
        for r in self.readings:
            if not r.matches(tmp):
                l.append(r)
            elif r.pos_tag == SENTENCE_END_TAGNAME:
                removed_sent_end = True
            elif r.pos_tag == PARAGRAPH_END_TAGNAME:
                removed_para_end = True
        if not l:
            n = AnalyzedToken(self.token, None, None)
            n.whitespace_before = self.whitespace_before
            l.append(n)
        self.readings = l
        self._set_no_real_pos_tag()
        if removed_sent_end:
            self.is_sentence_end = False
            self.set_sentence_end()
        if removed_para_end:
            self.is_paragraph_end = False
            self.set_paragraph_end()
        self.has_same_lemmas = self._are_lemmas_same()

    def leave_reading(self, token):
        tmp = AnalyzedToken(token.token, token.pos_tag, token.lemma)
        tmp.whitespace_before = self.whitespace_before
        l = [r for r in self.readings if r.matches(tmp)]
        if not l:
            n = AnalyzedToken(self.token, None, None)
            n.whitespace_before = self.whitespace_before
            l.append(n)
        self.readings = l
        self._set_no_real_pos_tag()
        self.has_same_lemmas = self._are_lemmas_same()

    def set_paragraph_end(self):
        if not self.is_paragraph_end:
            self.add_reading(AnalyzedToken(self.token, PARAGRAPH_END_TAGNAME, self.readings[0].lemma),
                             'add_paragaph_end')

    def set_sentence_end(self):
        if not self.is_sentence_end:
            self.add_reading(AnalyzedToken(self.token, SENTENCE_END_TAGNAME, self.readings[0].lemma), '')

    def set_whitespace_before(self, prev_token):
        wb = bool(prev_token) and is_whitespace(prev_token)
        self.whitespace_before = wb
        for r in self.readings:
            r.whitespace_before = wb
        if wb:
            self.whitespace_before_char = prev_token

    def immunize(self, source_line=0):
        self.immunized = True
        self.immunization_source_line = source_line

    def ignore_spelling(self):
        self.ignored_by_speller = True

    def set_chunk_tags(self, tags):
        self.chunk_tags = tuple(tags)

    def _set_no_real_pos_tag(self):
        has_no = not self.is_linebreak
        for r in self.readings:
            p = r.pos_tag
            if p == PARAGRAPH_END_TAGNAME or p == SENTENCE_END_TAGNAME:
                continue
            if p is not None:
                has_no = False
                break
        for r in self.readings:
            r.has_no_pos_tag = has_no

    def _are_lemmas_same(self):
        rs = self.readings
        prev = rs[0].lemma
        if prev is None:
            for r in rs:
                if r.lemma is not None:
                    return False
            return True
        for r in rs:
            if prev != r.lemma:
                return False
        return True

    def __eq__(self, o):
        if self is o:
            return True
        if not isinstance(o, AnalyzedTokenReadings):
            return NotImplemented
        return (self.readings == o.readings and self.is_linebreak == o.is_linebreak and
                self.is_paragraph_end == o.is_paragraph_end and self.is_sentence_end == o.is_sentence_end and
                self.is_sentence_start == o.is_sentence_start and self.is_whitespace == o.is_whitespace and
                self.whitespace_before == o.whitespace_before and self.immunized == o.immunized and
                self.start_pos == o.start_pos and tuple(self.chunk_tags) == tuple(o.chunk_tags) and
                self.has_same_lemmas == o.has_same_lemmas and self.ignored_by_speller == o.ignored_by_speller and
                self.token == o.token and self.typographic_apostrophe == o.typographic_apostrophe)

    __hash__ = object.__hash__

    def __repr__(self):
        parts = []
        for r in self.readings:
            parts.append(str(r) + ('' if r.whitespace_before else '*'))
        s = self.token + '[' + ','.join(parts)
        if self.chunk_tags:
            s += ',' + '|'.join(str(c) for c in self.chunk_tags)
        s += ']'
        if self.immunized:
            s += '{!},'
        return s

    __str__ = __repr__


def copy_readings(tokens):
    """Port of AnalyzedSentence.copyReadings: deep copy of readings."""
    out = []
    for atr in tokens:
        readings = [r.copy() for r in atr.readings]
        out.append(AnalyzedTokenReadings.from_old(atr, readings, ''))
    return out


class AnalyzedSentence:
    """A sentence, as a list of AnalyzedTokenReadings including whitespace
    tokens."""

    __slots__ = ('tokens', 'pre_disambig_tokens', 'non_blank_tokens', 'non_blank_pre_disambig_tokens',
                 'wh_positions', 'token_offsets', 'lemma_offsets', 'pos_tag_set', '_text', '_native')

    def __init__(self, tokens, pre_disambig_tokens=None, previous=None, readings_unchanged=False):
        if pre_disambig_tokens is None:
            pre_disambig_tokens = tokens
        self.tokens = tokens
        self.pre_disambig_tokens = pre_disambig_tokens
        mapping = [0] * (len(tokens) + 1)
        self.wh_positions = mapping
        self.non_blank_tokens = self._non_blank(tokens, mapping)
        self.non_blank_pre_disambig_tokens = self._non_blank(pre_disambig_tokens, mapping)
        same_tokens = previous is not None and _same_token_strings(previous.non_blank_tokens, self.non_blank_tokens)
        self.token_offsets = previous.token_offsets if same_tokens else _index_tokens(self.non_blank_tokens)
        if same_tokens and readings_unchanged:
            self.lemma_offsets = previous.lemma_offsets
            self.pos_tag_set = previous.pos_tag_set
        else:
            self.lemma_offsets = _index_lemmas(self.non_blank_tokens)
            self.pos_tag_set = _index_pos_tags(self.non_blank_tokens)
        self._text = None
        self._native = None

    @staticmethod
    def _non_blank(tokens, mapping):
        l = []
        nwh = 0
        for wh, t in enumerate(tokens):
            if not t.is_whitespace or t.is_sentence_start or t.is_sentence_end or t.is_paragraph_end:
                l.append(t)
                mapping[nwh] = wh
                nwh += 1
        return l

    def copy(self):
        """Port of AnalyzedSentence.copy(sentence)."""
        copy_tokens = [AnalyzedTokenReadings.from_old(t, t.readings, '') for t in self.tokens]
        s = AnalyzedSentence.__new__(AnalyzedSentence)
        s.tokens = copy_tokens
        s.pre_disambig_tokens = copy_tokens
        s.wh_positions = self.wh_positions
        # non blank tokens must refer to the new token objects
        s.non_blank_tokens = [copy_tokens[self.wh_positions[i]] for i in range(len(self.non_blank_tokens))]
        s.non_blank_pre_disambig_tokens = list(self.non_blank_pre_disambig_tokens)
        s.token_offsets = self.token_offsets
        s.lemma_offsets = self.lemma_offsets
        s.pos_tag_set = self.pos_tag_set
        s._text = self._text
        s._native = None
        return s

    def get_tokens_without_whitespace(self):
        return list(self.non_blank_tokens)

    def get_pre_disambig_tokens_without_whitespace(self):
        return list(self.non_blank_pre_disambig_tokens)

    @property
    def non_whitespace_token_count(self):
        return len(self.non_blank_tokens)

    def get_original_position(self, non_wh_position):
        return self.wh_positions[non_wh_position]

    @property
    def text(self):
        r = self._text
        if r is None:
            r = self._text = ''.join(t.token for t in self.tokens)
        return r

    def get_corrected_text_length(self):
        n = 0
        last = len(self.tokens) - 1
        for i, t in enumerate(self.tokens):
            n += len(t.get_clean_token())
            if i == last:
                n += t.pos_fix
        return n

    @property
    def token_set(self):
        return self.token_offsets.keys()

    @property
    def lemma_set(self):
        return self.lemma_offsets.keys()

    def __str__(self):
        return self.to_string(',', True)

    __repr__ = __str__

    def to_short_string(self, reading_delimiter):
        return self.to_string(reading_delimiter, False)

    def to_string(self, reading_delimiter=',', include_chunks=True):
        sb = []
        for el in self.tokens:
            if not el.is_whitespace:
                sb.append(el.token)
                sb.append('[')
            n = len(el.readings)
            for i, tok in enumerate(el.readings):
                pos = tok.pos_tag
                if el.is_sentence_start:
                    sb.append('<S>')
                elif pos == SENTENCE_END_TAGNAME:
                    sb.append('</S>')
                elif pos == PARAGRAPH_END_TAGNAME:
                    sb.append('<P/>')
                elif pos is None and not include_chunks:
                    sb.append(tok.token)
                else:
                    if not el.is_whitespace:
                        sb.append(str(tok))
                        if i < n - 1:
                            sb.append(reading_delimiter)
            if not el.is_whitespace:
                if include_chunks and el.chunk_tags:
                    sb.append(',')
                    sb.append('|'.join(str(c) for c in el.chunk_tags))
                if el.immunized:
                    sb.append('{!}')
                sb.append(']')
            else:
                sb.append(' ')
        return ''.join(sb)

    def __eq__(self, o):
        if self is o:
            return True
        if not isinstance(o, AnalyzedSentence):
            return NotImplemented
        return (self.non_blank_tokens == o.non_blank_tokens and self.tokens == o.tokens
                and self.wh_positions == o.wh_positions)

    __hash__ = object.__hash__


def _same_token_strings(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x.token != y.token:
            return False
    return True


def _index_tokens(tokens):
    result = {}
    for i, t in enumerate(tokens):
        result.setdefault(t.token_lower, []).append(i)
    return result


def _index_lemmas(tokens):
    result = {}
    for i, t in enumerate(tokens):
        for r in t.readings:
            lst = result.get(r.lemma_or_token_lower)
            if lst is None:
                result[r.lemma_or_token_lower] = [i]
            elif lst[-1] != i:
                lst.append(i)
    return result


def _index_pos_tags(tokens):
    result = set()
    for t in tokens:
        for r in t.readings:
            if r.pos_tag is not None:
                result.add(r.pos_tag)
    return frozenset(result)
