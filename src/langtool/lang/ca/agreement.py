"""Port of org.languagetool.rules.ca.PostponedAdjectiveConcordanceFilter."""

from ... import jregex
from ...rules.filters import RuleFilter

_MAX_LEVELS = 4


def _c(p):
    return jregex.compile(p)


_NOM = _c('N.*')
_NOM_MS = _c('N.MS.*')
_NOM_FS = _c('N.FS.*')
_NOM_MP = _c('N.MP.*')
_NOM_MN = _c('N.MN.*')
_NOM_FP = _c('N.FP.*')
_NOM_CS = _c('N.CS.*')
_NOM_CP = _c('N.CP.*')

_NOM_DET = _c('N.*|D[NDA0I].*')
_GN_ = _c('_GN_.*')
_GN_MS_ = _c('_GN_MS')
_GN_FS_ = _c('_GN_FS')
_GN_MP_ = _c('_GN_MP')
_GN_FP_ = _c('_GN_FP')
_GN_CS_ = _c('_GN_[MF]S')
_GN_CP_ = _c('_GN_[MF]P')

_DET = _c('D[NDA0IP].*')
_DET_CS = _c('D[NDA0IP]0CS0')
_DET_MS = _c('D[NDA0IP]0MS0')
_DET_FS = _c('D[NDA0IP]0FS0')
_DET_MP = _c('D[NDA0IP]0MP0')
_DET_FP = _c('D[NDA0IP]0FP0')

_GN_MS = _c('N.[MC][SN].*|A..[MC][SN].*|V.P..SM.?|PX.MS.*|D[NDA0I]0MS0|PI0MS000')
_GN_FS = _c('N.[FC][SN].*|A..[FC][SN].*|V.P..SF.?|PX.FS.*|D[NDA0I]0FS0|PI0FS000')
_GN_MP = _c('N.[MC][PN].*|A..[MC][PN].*|V.P..PM.?|PX.MP.*|D[NDA0I]0MP0')
_GN_FP = _c('N.[FC][PN].*|A..[FC][PN].*|V.P..PF.?|PX.FP.*|D[NDA0I]0FP0')
_GN_CP = _c('N.[FMC][PN].*|A..[FMC][PN].*|D[NDA0I]0[FM]P0')
_GN_CS = _c('N.[FMC][SN].*|A..[FMC][SN].*|D[NDA0I]0[FM]S0')

_ADJECTIU = _c('AQ.*|V.P.*|PX.*|.*LOC_ADJ.*')
_ADJECTIU_MS = _c('A..[MC][SN].*|V.P..SM.?|PX.MS.*')
_ADJECTIU_FS = _c('A..[FC][SN].*|V.P..SF.?|PX.FS.*')
_ADJECTIU_MP = _c('A..[MC][PN].*|V.P..PM.?|PX.MP.*')
_ADJECTIU_FP = _c('A..[FC][PN].*|V.P..PF.?|PX.FP.*')
_ADJECTIU_CP = _c('A..C[PN].*')
_ADJECTIU_CS = _c('A..C[SN].*')
_ADJECTIU_S = _c('A...[SN].*|V.P..S..?|PX..S.*')
_ADJECTIU_P = _c('A...[PN].*|V.P..P..?|PX..P.*')
_ADVERBI = _c('R.|.*LOC_ADV.*')
_CONJUNCIO = _c('C.|.*LOC_CONJ.*')
_PUNTUACIO = _c('_PUNCT')
_LOC_ADV = _c('.*LOC_ADV.*')
_ADVERBIS_ACCEPTATS = _c('RG_anteposat')
_COORDINACIO_IONI = _c('i|o|ni')
_KEEP_COUNT = _c('A.*|N.*|D[NAIDP].*|SPS.*|.*LOC_ADV.*|V.P.*|_PUNCT.*|.*LOC_ADJ.*|PX.*|PI0.S000|UNKNOWN')
_KEEP_COUNT2 = _c(',|i|o|ni')  # |\d+%?|%
_STOP_COUNT = _c('[;:]')
_PREPOSICIONS = _c('SPS.*')
_PREPOSICIO_CANVI_NIVELL = _c("de|d'|en|sobre|a|entre|per|pe|amb|sense|contra|com|envers")
_VERB = _c('V.[^P].*|_GV_')
_GV = _c('_GV_')


def _match_postag_regexp(atr, pattern):
    """Match POS tag with regular expression (null tags are "UNKNOWN")"""
    for at in atr.readings:
        pos_tag = at.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if pattern.fullmatch(pos_tag):
            return True
    return False


def _match_regexp(s, pattern):
    return pattern.fullmatch(s) is not None


def _get_analyzed_token(atr, pattern):
    for at in atr.readings:
        pos_tag = at.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if pattern.fullmatch(pos_tag):
            return at
    return None


def _update_j_value(tokens, i, j):
    """updateJValue: dos o més"""
    if _match_regexp(tokens[i - j].token, _COORDINACIO_IONI):
        if i - j - 1 > 0 and i - j + 1 < len(tokens):
            if _match_postag_regexp(tokens[i - j - 1], _DET) and tokens[i - j + 1].token == 'més':
                j = j + 1
    return j


class _Apparitions:
    """The adverbAppeared, conjunctionAppeared and punctuationAppeared
    fields of the Java filter (kept per call here, Java's filter instance is
    shared)"""

    def __init__(self):
        self.initialize()

    def initialize(self):
        self.adverb = False
        self.conjunction = False
        self.punctuation = False

    def update(self, atr):
        self.conjunction |= _match_postag_regexp(atr, _CONJUNCIO)
        if atr.token == 'com':
            return
        if _match_postag_regexp(atr, _NOM) or _match_postag_regexp(atr, _ADJECTIU):
            self.initialize()
            return
        self.adverb |= _match_postag_regexp(atr, _ADVERBI)
        self.punctuation |= (_match_postag_regexp(atr, _PUNTUACIO) or atr.token == ',')

    def keep_counting(self, atr):
        if _match_regexp(atr.token, _PREPOSICIO_CANVI_NIVELL):
            return True
        if atr.token == '.':  # it is not sentence end, but abbreviation
            return True
        # stop searching if there is some of these combinations:
        # adverb+comma, adverb+conjunction, comma+conjunction,
        # punctuation+punctuation
        if ((self.adverb and self.conjunction) or (self.adverb and self.punctuation)
                or (self.conjunction and self.punctuation)
                or (self.punctuation and _match_postag_regexp(atr, _PUNTUACIO))):
            return False
        return ((_match_postag_regexp(atr, _KEEP_COUNT) or _match_regexp(atr.token, _KEEP_COUNT2)
                 or _match_postag_regexp(atr, _ADVERBIS_ACCEPTATS))
                and not _match_regexp(atr.token, _STOP_COUNT)
                and (not _match_postag_regexp(atr, _GV) or _match_postag_regexp(atr, _GN_)))


class PostponedAdjectiveConcordanceFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.PostponedAdjectiveConcordanceFilter:
    accepts the match if the adjective (the first token of the match)
    doesn't agree with the previous noun and at the same time it doesn't
    agree with any of the previous words. Takes care of some exceptions.
    The suggestions are the adjective forms synthesized for the possible
    gender/number (with a comma before the adjective if the argument
    addComma is "true")."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        add_comma = self.get_optional('addComma', arguments, 'false').lower() == 'true'
        tokens = match.sentence.non_blank_tokens
        i = pattern_token_pos
        is_plural = True
        is_prev_noun = False
        can_be_ms = can_be_fs = can_be_mp = can_be_fp = can_be_p = False
        # Count all nouns and determiners before the adjectives.
        # Takes care of acceptable combinations.
        c_nt = [0] * _MAX_LEVELS
        c_nms = [0] * _MAX_LEVELS
        c_nfs = [0] * _MAX_LEVELS
        c_nmp = [0] * _MAX_LEVELS
        c_nmn = [0] * _MAX_LEVELS
        c_nfp = [0] * _MAX_LEVELS
        c_ncs = [0] * _MAX_LEVELS
        c_ncp = [0] * _MAX_LEVELS
        c_dms = [0] * _MAX_LEVELS
        c_dfs = [0] * _MAX_LEVELS
        c_dmp = [0] * _MAX_LEVELS
        c_dfp = [0] * _MAX_LEVELS
        c_n = [0] * _MAX_LEVELS
        c_d = [0] * _MAX_LEVELS
        level = 0
        j = 1
        app = _Apparitions()
        while i - j > 0 and app.keep_counting(tokens[i - j]) and level < _MAX_LEVELS:
            t = tokens[i - j]
            if not is_prev_noun:
                if _match_postag_regexp(t, _NOM) or (
                        # adjectiu o participi sense nom, però amb algun determinant davant
                        i - j - 1 > 0 and not _match_postag_regexp(t, _NOM) and _match_postag_regexp(t, _ADJECTIU)
                        and _match_postag_regexp(tokens[i - j - 1], _DET)):
                    if _match_postag_regexp(t, _GN_MS_):
                        c_nms[level] += 1
                        can_be_ms = True
                    if _match_postag_regexp(t, _GN_FS_):
                        c_nfs[level] += 1
                        can_be_fs = True
                    if _match_postag_regexp(t, _GN_MP_):
                        c_nmp[level] += 1
                        can_be_mp = True
                    if _match_postag_regexp(t, _GN_FP_):
                        c_nfp[level] += 1
                        can_be_fp = True
                if not _match_postag_regexp(t, _GN_):
                    if _match_postag_regexp(t, _NOM_MS):
                        c_nms[level] += 1
                        can_be_ms = True
                    elif _match_postag_regexp(t, _NOM_FS):
                        c_nfs[level] += 1
                        can_be_fs = True
                    elif _match_postag_regexp(t, _NOM_MP):
                        c_nmp[level] += 1
                        can_be_mp = True
                    elif _match_postag_regexp(t, _NOM_MN):
                        c_nmn[level] += 1
                        can_be_ms = True
                        can_be_mp = True
                    elif _match_postag_regexp(t, _NOM_FP):
                        c_nfp[level] += 1
                        can_be_fp = True
                    elif _match_postag_regexp(t, _NOM_CS):
                        c_ncs[level] += 1
                        can_be_ms = True
                        can_be_fs = True
                    elif _match_postag_regexp(t, _NOM_CP):
                        c_ncp[level] += 1
                        can_be_fp = True
                        can_be_mp = True
            # avoid two consecutive nouns
            if _match_postag_regexp(t, _NOM):
                c_nt[level] += 1
                is_prev_noun = True
            else:
                is_prev_noun = False

            if _match_postag_regexp(t, _DET_CS):
                if _match_postag_regexp(tokens[i - j + 1], _NOM_MS):
                    c_dms[level] += 1
                    can_be_ms = True
                if _match_postag_regexp(tokens[i - j + 1], _NOM_FS):
                    c_dfs[level] += 1
                    can_be_fs = True
            if not _match_postag_regexp(t, _ADVERBI):
                # exception: tot el
                if not (t.has_lemma('tot') and tokens[i - j + 1].has_lemma('el')):
                    if _match_postag_regexp(t, _DET_MS):
                        c_dms[level] += 1
                        can_be_ms = True
                    if _match_postag_regexp(t, _DET_FS):
                        c_dfs[level] += 1
                        can_be_fs = True
                    if _match_postag_regexp(t, _DET_MP):
                        c_dmp[level] += 1
                        can_be_mp = True
                    if _match_postag_regexp(t, _DET_FP):
                        c_dfp[level] += 1
                        can_be_fp = True
            if i - j - 1 > 0:
                if (_match_regexp(t.token, _PREPOSICIO_CANVI_NIVELL)
                        and not _match_postag_regexp(t, _CONJUNCIO)  # "com" com a conjunció
                        and not _match_regexp(tokens[i - j - 1].token, _COORDINACIO_IONI)
                        and not _match_postag_regexp(tokens[i - j + 1], _ADVERBI)):
                    level += 1
            j = _update_j_value(tokens, i, j)
            app.update(tokens[i - j])
            j += 1
        level += 1
        if level > _MAX_LEVELS:
            level = _MAX_LEVELS
        j = 0
        c_ntotal = 0
        c_dtotal = 0
        while j < level:
            c_n[j] = c_nms[j] + c_nfs[j] + c_nmp[j] + c_nfp[j] + c_ncs[j] + c_ncp[j] + c_nmn[j]
            c_d[j] = c_dms[j] + c_dfs[j] + c_dmp[j] + c_dfp[j]
            c_ntotal += c_n[j]
            c_dtotal += c_d[j]
            # exceptions: adjective is plural and there are several nouns before
            if (_match_postag_regexp(tokens[i], _ADJECTIU_MP) and (c_n[j] > 1 or c_d[j] > 1)
                    and (c_nms[j] + c_nmn[j] + c_nmp[j] + c_ncs[j] + c_ncp[j] + c_dms[j] + c_dmp[j]) > 0
                    and (c_nfs[j] + c_nfp[j] <= c_nt[j])):
                return None
            if (_match_postag_regexp(tokens[i], _ADJECTIU_FP) and (c_n[j] > 1 or c_d[j] > 1)
                    and ((c_nms[j] + c_nmp[j] + c_nmn[j] + c_dms[j] + c_dmp[j]) == 0
                         or (c_nt[j] > 0 and c_nfs[j] + c_nfp[j] >= c_nt[j]))):
                return None
            # Adjective can't be singular
            if c_n[j] + c_d[j] > 0:  # && level>1
                is_plural = is_plural and c_d[j] > 1  # cN[j]>1
                can_be_p = can_be_p or c_n[j] > 1
            j += 1
        # comma + plural noun
        is_plural = is_plural or (i - 2 > 0 and c_nmp[0] + c_nfp[0] + c_ncp[0] > 0 and tokens[i - 2].token == ',')

        # there is no noun, (no determinant --> && cDtotal==0)
        if c_ntotal == 0 and c_dtotal == 0:
            return None

        # patterns according to the analyzed adjective
        if _match_postag_regexp(tokens[i], _ADJECTIU_CS):
            subst_pattern, adj_pattern, gn_pattern = _GN_CS, _ADJECTIU_S, _GN_CS_
        elif _match_postag_regexp(tokens[i], _ADJECTIU_CP):
            subst_pattern, adj_pattern, gn_pattern = _GN_CP, _ADJECTIU_P, _GN_CP_
        elif _match_postag_regexp(tokens[i], _ADJECTIU_MS):
            subst_pattern, adj_pattern, gn_pattern = _GN_MS, _ADJECTIU_MS, _GN_MS_
        elif _match_postag_regexp(tokens[i], _ADJECTIU_FS):
            subst_pattern, adj_pattern, gn_pattern = _GN_FS, _ADJECTIU_FS, _GN_FS_
        elif _match_postag_regexp(tokens[i], _ADJECTIU_MP):
            subst_pattern, adj_pattern, gn_pattern = _GN_MP, _ADJECTIU_MP, _GN_MP_
        elif _match_postag_regexp(tokens[i], _ADJECTIU_FP):
            subst_pattern, adj_pattern, gn_pattern = _GN_FP, _ADJECTIU_FP, _GN_FP_
        else:
            return None

        # combinations Det/Nom + adv (1,2..) + adj.
        # If there is agreement, the rule doesn't match
        j = 1
        keep_count = True
        while i - j > 0 and keep_count:
            t = tokens[i - j]
            if _match_postag_regexp(t, _NOM_DET) and _match_postag_regexp(t, gn_pattern):
                return None  # there is a previous agreeing noun
            elif not _match_postag_regexp(t, _GN_) and _match_postag_regexp(t, subst_pattern):
                return None  # there is a previous agreeing noun
            keep_count = not _match_postag_regexp(t, _NOM_DET)
            j += 1

        # Necessary condition: previous token is a non-agreeing noun
        # or it is adjective or adverb (not preceded by verb)
        prev = tokens[i - 1]
        if not ((_match_postag_regexp(prev, _NOM) and not _match_postag_regexp(prev, subst_pattern))
                or (_match_postag_regexp(prev, _ADJECTIU) and not _match_postag_regexp(prev, gn_pattern))
                or (_match_postag_regexp(prev, _ADJECTIU) and not _match_postag_regexp(prev, adj_pattern))
                or (i > 2 and _match_postag_regexp(prev, _ADVERBIS_ACCEPTATS)
                    and not _match_postag_regexp(tokens[i - 2], _VERB)
                    and not _match_postag_regexp(tokens[i - 2], _PREPOSICIONS))
                or (i > 3 and _match_postag_regexp(prev, _LOC_ADV) and _match_postag_regexp(tokens[i - 2], _LOC_ADV)
                    and not _match_postag_regexp(tokens[i - 3], _VERB)
                    and not _match_postag_regexp(tokens[i - 3], _PREPOSICIONS))):
            return None

        # Adjective can't be singular. The rule matches
        if not (is_plural and _match_postag_regexp(tokens[i], _ADJECTIU_S)):
            # look into previous words
            j = 1
            app.initialize()
            while i - j > 0 and app.keep_counting(tokens[i - j]):  # && (level > 1 || j < 4)
                t = tokens[i - j]
                # there is a previous agreeing noun
                if (not _match_postag_regexp(t, _GN_) and _match_postag_regexp(t, _NOM_DET)
                        and _match_postag_regexp(t, subst_pattern)):
                    return None
                # there is a previous agreeing adjective (in a nominal group)
                elif _match_postag_regexp(t, gn_pattern):
                    return None
                j = _update_j_value(tokens, i, j)
                app.update(tokens[i - j])
                j += 1

        synth = self.get_language_from_rule_match(match).synthesizer
        # The rule matches
        # Synthesize suggestions
        suggestions = []
        token = tokens[pattern_token_pos]
        at = _get_analyzed_token(token, _ADJECTIU_CS)
        if at is not None:
            suggestions.extend(synth.synthesize(at, 'A..CP.', True))
        if not suggestions:
            at = _get_analyzed_token(token, _ADJECTIU_CP)
            if at is not None:
                suggestions.extend(synth.synthesize(at, 'A..CS.', True))
        if not suggestions and is_plural:
            at = _get_analyzed_token(token, _ADJECTIU_P)
            if at is not None:
                suggestions.extend(synth.synthesize(at, 'A...P.|V.P..P..|PX..P.*', True))
        at = _get_analyzed_token(token, _ADJECTIU)
        if at is not None and not suggestions:
            if can_be_ms and not is_plural:
                suggestions.extend(synth.synthesize(at, 'A..MS.|V.P..SM.|PX.MS.*', True))
            if can_be_fs and not is_plural:
                suggestions.extend(synth.synthesize(at, 'A..FS.|V.P..SF.|PX.FS.*', True))
            if can_be_mp:
                suggestions.extend(synth.synthesize(at, 'A..MP.|V.P..PM.|PX.MP.*', True))
            if can_be_fp:
                suggestions.extend(synth.synthesize(at, 'A..FP.|V.P..PF.|PX.FP.*', True))
            if can_be_ms and (is_plural or can_be_p):
                suggestions.extend(synth.synthesize(at, 'A..MP.|V.P..PM.|PX.MP.*', True))
            if can_be_fs and not can_be_ms and (is_plural or can_be_p):
                suggestions.extend(synth.synthesize(at, 'A..FP.|V.P..PF.|PX.FP.*', True))
        # avoid the original token as suggestion (List.remove: the first occurrence)
        lower_token = token.token.lower()
        if lower_token in suggestions:
            suggestions.remove(lower_token)
        if not suggestions:
            return None
        if add_comma:
            definitive_suggestions = [', ' + token.token] + [' ' + s for s in suggestions]
            match.set_offset_position(match.from_pos - 1, match.to_pos)
            match.set_sentence_position(match.get_from_pos_sentence() - 1, match.get_to_pos_sentence())
        else:
            definitive_suggestions = suggestions
        match.set_suggested_replacements(list(dict.fromkeys(definitive_suggestions)))
        return match


FILTERS = (PostponedAdjectiveConcordanceFilter,)
RULES = {}
