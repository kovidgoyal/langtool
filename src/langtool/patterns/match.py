"""Port of org.languagetool.rules.patterns.Match, MatchState and
CaseConversionHelper: the <match> element used in messages, suggestions,
tokens and disambiguation actions."""

from .. import jregex
from ..analysis import (AnalyzedToken, AnalyzedTokenReadings, SENTENCE_START_TAGNAME, SENTENCE_END_TAGNAME,
                        PARAGRAPH_END_TAGNAME)
from ..tools import (starts_with_uppercase, is_all_uppercase, uppercase_first_char, remove_tashkeel)

# case conversions
NONE, STARTLOWER, STARTUPPER, ALLLOWER, ALLUPPER, PRESERVE, FIRSTUPPER, NOTASHKEEL = range(8)
CASE_CONVERSIONS = {'none': NONE, 'startlower': STARTLOWER, 'startupper': STARTUPPER, 'alllower': ALLLOWER,
                    'allupper': ALLUPPER, 'preserve': PRESERVE, 'firstupper': FIRSTUPPER, 'notashkeel': NOTASHKEEL}

# include ranges
INCLUDE_NONE, INCLUDE_FOLLOWING, INCLUDE_ALL = range(3)
INCLUDE_RANGES = {'none': INCLUDE_NONE, 'following': INCLUDE_FOLLOWING, 'all': INCLUDE_ALL}


def convert_case(conversion, s, sample, lang_code=None):
    if not s:
        return s
    if conversion == NONE:
        return s
    if conversion == PRESERVE:
        if starts_with_uppercase(sample):
            if is_all_uppercase(sample):
                return s.upper()
            return uppercase_first_char(s, lang_code)
        return s
    if conversion == STARTLOWER:
        return s[0].lower() + s[1:]
    if conversion == STARTUPPER:
        return uppercase_first_char(s, lang_code)
    if conversion == ALLUPPER:
        return s.upper()
    if conversion == FIRSTUPPER:
        return uppercase_first_char(s.lower(), lang_code)
    if conversion == ALLLOWER:
        return s.lower()
    if conversion == NOTASHKEEL:
        return remove_tashkeel(s)
    return s


class Match:

    __slots__ = ('pos_tag', 'suppress_misspelled', 'regex_replace', 'pos_tag_replace', 'case_conversion',
                 'include_skipped', '_regex_match', '_regex_match_src', 'set_pos', 'postag_regexp', 'static_lemma',
                 'lemma', 'token_ref', '_pos_regex_match', '_pos_regex_src', 'in_message_only')

    def __init__(self, pos_tag=None, pos_tag_replace=None, postag_regexp=False, regex_match=None,
                 regex_replace=None, case_conversion=NONE, set_pos=False, suppress_misspelled=False,
                 include_skipped=INCLUDE_NONE):
        self.pos_tag = pos_tag
        self.postag_regexp = postag_regexp
        self.case_conversion = case_conversion
        self._regex_match_src = regex_match
        self._regex_match = None
        if regex_match is not None:
            jregex.translate(regex_match)  # check syntax
        self._pos_regex_src = pos_tag if postag_regexp and pos_tag is not None else None
        self._pos_regex_match = None
        self.regex_replace = regex_replace
        self.pos_tag_replace = pos_tag_replace
        self.set_pos = set_pos
        self.include_skipped = include_skipped
        self.suppress_misspelled = suppress_misspelled
        self.static_lemma = False
        self.lemma = None
        self.token_ref = 0
        self.in_message_only = False

    @property
    def regex_match(self):
        r = self._regex_match
        if r is None and self._regex_match_src is not None:
            r = self._regex_match = jregex.compile(self._regex_match_src)
        return r

    @property
    def pos_regex_match(self):
        r = self._pos_regex_match
        if r is None and self._pos_regex_src is not None:
            r = self._pos_regex_match = jregex.compile(self._pos_regex_src)
        return r

    def set_lemma_string(self, lemma):
        if lemma:
            self.lemma = lemma
            self.static_lemma = True
            self.postag_regexp = True
            if self.pos_tag is not None:
                self._pos_regex_src = self.pos_tag
                self._pos_regex_match = None

    def converts_case(self):
        return self.case_conversion != NONE

    def create_state(self, synthesizer, token, index=None, nxt=None):
        """create_state(synth, atr) or create_state(synth, tokens, index,
        next)"""
        state = MatchState(self, synthesizer)
        if index is None:
            state.set_token(token)
        else:
            state.set_token_range(token, index, nxt)
        return state


class MatchState:

    __slots__ = ('match', 'synthesizer', 'formatted_token', 'matched_token', 'skipped_tokens')

    def __init__(self, match, synthesizer):
        self.match = match
        self.synthesizer = synthesizer
        self.formatted_token = None
        self.matched_token = None
        self.skipped_tokens = None
        if match.lemma:
            self.formatted_token = AnalyzedTokenReadings(AnalyzedToken(match.lemma, match.pos_tag, match.lemma), 0)

    def set_token(self, token):
        if self.match.static_lemma:
            self.matched_token = token
        else:
            self.formatted_token = token

    def set_token_range(self, tokens, index, nxt):
        idx = index
        if index >= len(tokens):
            idx = len(tokens) - 1
        self.set_token(tokens[idx])
        inc = self.match.include_skipped
        if inc == INCLUDE_FOLLOWING:
            self.formatted_token = None
        if nxt > 1 and inc != INCLUDE_NONE:
            sb = []
            for k in range(index + 1, index + nxt):
                if tokens[k].whitespace_before and not (k == index + 1 and inc == INCLUDE_FOLLOWING):
                    sb.append(' ')
                sb.append(tokens[k].token)
            self.skipped_tokens = ''.join(sb)
        else:
            self.skipped_tokens = ''

    def filter_readings(self):
        match = self.match
        l = []
        ft = self.formatted_token
        if ft is not None:
            if match.static_lemma:
                mt = self.matched_token
                mt.leave_reading(AnalyzedToken(mt.readings[0].token, match.pos_tag, ft.token))
                ft = self.formatted_token = mt
            token = ft.readings[0].token
            if match.regex_match is not None and match.regex_replace is not None:
                token = jregex.java_replace(match.regex_match, match.regex_replace, token)
            token = convert_case(match.case_conversion, token, token, None)
            pos_tag = match.pos_tag
            if pos_tag is not None:
                num_read = len(ft.readings)
                if match.postag_regexp:
                    p = match.pos_regex_match
                    rep = match.pos_tag_replace
                    for i in range(num_read):
                        test_tag = ft.readings[i].pos_tag
                        if test_tag is not None and p.fullmatch(test_tag):
                            target = test_tag
                            if rep is not None:
                                target = jregex.java_replace(p, rep, target)
                            at = AnalyzedToken(token, target, ft.readings[i].lemma)
                            at.whitespace_before = ft.whitespace_before
                            l.append(at)
                    if not l:
                        l.extend(self._new_token(num_read, token))
                else:
                    l.extend(self._new_token(num_read, token))
                lemma = ft.readings[0].lemma
                if ft.is_sentence_end:
                    l.append(AnalyzedToken(ft.token, SENTENCE_END_TAGNAME, lemma))
                if ft.is_paragraph_end:
                    l.append(AnalyzedToken(ft.token, PARAGRAPH_END_TAGNAME, lemma))
        if not l:
            return ft
        atr = AnalyzedTokenReadings(l, ft.start_pos)
        atr.set_whitespace_before(ft.whitespace_before_char)
        if ft.chunk_tags:
            atr.chunk_tags = ft.chunk_tags
        if ft.immunized:
            atr.immunize(ft.immunization_source_line)
        return atr

    def _new_token(self, num_read, token):
        pos_tag = self.match.pos_tag
        ft = self.formatted_token
        out = []
        lemma = ''
        for j in range(num_read):
            tmp = ft.readings[j].pos_tag
            if tmp is not None:
                if tmp == pos_tag and ft.readings[j].lemma is not None:
                    lemma = ft.readings[j].lemma
                if not lemma:
                    lemma = ft.readings[0].lemma
                at = AnalyzedToken(token, pos_tag, lemma)
                at.whitespace_before = ft.whitespace_before
                out.append(at)
        return out

    def to_final_string(self, lang=None):
        match = self.match
        ft = self.formatted_token
        formatted = [None]
        lang_code = lang.short_code if lang is not None else None
        if ft is not None:
            reading_count = len(ft.readings)
            formatted[0] = ft.token
            if match.regex_match is not None:
                if lang_code == 'ar':
                    formatted[0] = remove_tashkeel(formatted[0])
                formatted[0] = jregex.java_replace(match.regex_match, match.regex_replace or '', formatted[0])
            pos_tag = match.pos_tag
            if pos_tag is not None:
                synth = self.synthesizer
                if synth is None:
                    formatted[0] = ft.token
                elif match.postag_regexp:
                    word_forms = set()
                    one_form = False
                    for k in range(reading_count):
                        r = ft.readings[k]
                        if r.lemma is None:
                            pu = r.pos_tag
                            if pu is None:
                                word_forms.add(ft.token)
                                one_form = True
                            else:
                                if pu in (SENTENCE_START_TAGNAME, SENTENCE_END_TAGNAME, PARAGRAPH_END_TAGNAME):
                                    if not one_form:
                                        word_forms.add(ft.token)
                                    one_form = True
                                else:
                                    one_form = False
                    target = self.get_target_pos_tag()
                    if not one_form:
                        for i in range(reading_count):
                            forms = synth.synthesize(ft.readings[i], target, True)
                            if forms:
                                word_forms.update(forms)
                    if not word_forms:
                        formatted[0] = '(' + ft.token + ')'
                    else:
                        formatted = sorted(word_forms, key=_java_string_key)
                else:
                    word_forms = set()
                    for i in range(reading_count):
                        forms = synth.synthesize(ft.readings[i], pos_tag)
                        if forms:
                            word_forms.update(forms)
                    formatted = sorted(word_forms, key=_java_string_key)
        if match.static_lemma:
            original = self.matched_token.token if self.matched_token is not None else ''
        else:
            original = ft.token if ft is not None else ''
        formatted = [convert_case(match.case_conversion, f if f is not None else '', original, lang_code)
                     for f in formatted]
        if match.include_skipped != INCLUDE_NONE and self.skipped_tokens:
            formatted = [(f or '') + self.skipped_tokens for f in formatted]
        if match.suppress_misspelled and lang is not None:
            from .matcher import MISTAKE
            analyzed = lang.tagger.tag(formatted)
            for i in range(len(formatted)):
                at = analyzed[i].readings[0]
                if at.lemma is None and at.has_no_pos_tag:
                    formatted[i] = MISTAKE
        return formatted

    def get_target_pos_tag(self):
        match = self.match
        target = match.pos_tag
        pos_tags = []
        p = match.pos_regex_match
        rep = match.pos_tag_replace
        synth = self.synthesizer
        if match.static_lemma:
            for at in self.matched_token.readings:
                t = at.pos_tag
                if t is not None and p.fullmatch(t):
                    pos_tags.append(t)
            target = synth.get_target_pos_tag(pos_tags, target)
            if p is not None and rep is not None and pos_tags:
                target = jregex.java_replace(p, rep, target)
        else:
            for at in self.formatted_token.readings:
                t = at.pos_tag
                if t is not None and p.fullmatch(t):
                    pos_tags.append(t)
            target = synth.get_target_pos_tag(pos_tags, target)
            if p is not None and rep is not None:
                if not pos_tags:
                    pos_tags.append(target)
                parts = []
                for lp in pos_tags:
                    lp = jregex.java_replace(p, rep, lp)
                    if match.set_pos:
                        lp = synth.get_pos_tag_correction(lp)
                    parts.append(lp)
                target = '|'.join(parts)
        return target

    def to_token_string(self):
        return '|'.join(self.to_final_string(None))


def _java_string_key(s):
    """Sort key emulating Java String.compareTo (UTF-16 code unit order)."""
    return s.encode('utf-16-be', 'surrogatepass')
