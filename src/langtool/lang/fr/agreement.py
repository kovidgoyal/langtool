"""Port of org.languagetool.rules.fr.PostponedAdjectiveConcordanceFilter."""

from ... import jregex
from ...rules.filters import RuleFilter
from ...tools import java_equals_ignore_case

_MAX_LEVELS = 4


def _c(p):
    return jregex.compile(p)


_NOM = _c('[NZ] .*')
_NOM_MS = _c('[NZ] m s')
_NOM_FS = _c('[NZ] f s')
_NOM_MP = _c('[NZ] m p')
_NOM_MN = _c('[NZ] m sp')
_NOM_FP = _c('[NZ] f p')
_NOM_CS = _c('[NZ] e s')
_NOM_CP = _c('[NZ] e sp')

_NOM_DET = _c('[NZ] .*|(P\\+)?D .*')
_GN_ = _c('_GN_.*')
_GN_MS_ = _c('_GN_MS')
_GN_FS_ = _c('_GN_FS')
_GN_MP_ = _c('_GN_MP')
_GN_FP_ = _c('_GN_FP')
_GN_CS_ = _c('_GN_[MF]S')
_GN_CP_ = _c('_GN_[MF]P')
_GN_MN_ = _c('_GN_M[SP]')
_GN_FN_ = _c('_GN_F[SP]')

_DET = _c('(P\\+)?D .*')
_DET_CS = _c('(P\\+)?D e s')
_DET_MS = _c('(P\\+)?D m s')
_DET_FS = _c('(P\\+)?D f s')
_DET_MP = _c('(P\\+)?D m p')
_DET_FP = _c('(P\\+)?D f p')
_DET_CP = _c('(P\\+)?D e p')  # NEW for French!!

_GN_MS = _c('[NZ] [me] (s|sp)|J [me] (s|sp)|V ppa m s|(P\\+)?D m (s|sp)')
_GN_FS = _c('[NZ] [fe] (s|sp)|J [fe] (s|sp)|V ppa f s|(P\\+)?D f (s|sp)')
_GN_MP = _c('[NZ] [me] (p|sp)|J [me] (p|sp)|V ppa m p|(P\\+)?D m (p|sp)')
_GN_FP = _c('[NZ] [fe] (p|sp)|J [fe] (p|sp)|V ppa f p|(P\\+)?D f (p|sp)')
_GN_CP = _c('[NZ] [fme] (p|sp)|J [fme] (p|sp)|(P\\+)?D [fme] (p|sp)')
_GN_CS = _c('[NZ] [fme] (s|sp)|J [fme] (s|sp)|(P\\+)?D [fme] (s|sp)')
_GN_MN = _c('[NZ] [me] (s|p|sp)|J [me] (s|p|sp)|(P\\+)?D [me] (s|p|sp)')  # NEW for French!!
_GN_FN = _c('[NZ] [fe] (s|p|sp)|J [fe] (s|p|sp)|(P\\+)?D [fe] (s|p|sp)')  # NEW for French!!

_ADJECTIU = _c('J .*|V ppa .*|PX.*')
_ADJECTIU_MS = _c('J [me] (s|sp)|V ppa m s')
_ADJECTIU_FS = _c('J [fe] (s|sp)|V ppa f s')
_ADJECTIU_MP = _c('J [me] (p|sp)|V ppa m p')
_ADJECTIU_FP = _c('J [fe] (p|sp)|V ppa f p')
_ADJECTIU_CP = _c('J e (p|sp)')
_ADJECTIU_CS = _c('J e (s|sp)')
_ADJECTIU_MN = _c('J m sp')  # NEW for French!!
_ADJECTIU_FN = _c('J f sp')  # NEW for French!!

_ADJECTIU_S = _c('J .* (s|sp)|V ppa . s')
_ADJECTIU_P = _c('J .* (p|sp)|V ppa . p')
_ADJECTIU_M = _c('J [me] .*|V ppa [me] .*')  # NEW for French!!
_ADJECTIU_F = _c('J [fe] .*|V ppa [fe] .*')  # NEW for French!!
_ADVERBI = _c('A')
_CONJUNCIO = _c('C .*')
_PUNTUACIO = _c('_PUNCT')
_LOC_ADV = _c('A')
_ADVERBIS_ACCEPTATS = _c('A')
_COORDINACIO_IONI = _c('et|ou|ni')
_KEEP_COUNT = _c('Y|J .*|N .*|D .*|P.*|V ppa .*|M nonfin|UNKNOWN|Z.*|V.* inf|V ppr')
_KEEP_COUNT2 = _c(',|et|ou|ni')  # |\d+%?|%
_STOP_COUNT = _c('[;:\\(\\)\\[\\]–—―‒]')
_PREPOSICIONS = _c('P.*')
_PREPOSICIO_CANVI_NIVELL = _c('d\'|de|des|du|à|au|aux|en|dans|sur|entre|par|pour|avec|sans|contre|comme')  # ???
_VERB = _c('V.* (inf|ind|sub|con|ppr|imp).*')  # Any verb that is not V ppa
_INFINITIVE = _c('V.* inf')
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


class _Apparitions:
    """The adverbAppeared, conjunctionAppeared, punctuationAppeared and
    infinitiveAppeared fields of the Java filter (kept per call here, Java's
    filter instance is shared)"""

    def __init__(self):
        self.initialize()

    def initialize(self):
        self.adverb = False
        self.conjunction = False
        self.punctuation = False
        self.infinitive = False

    def update(self, atr):
        self.conjunction |= _match_postag_regexp(atr, _CONJUNCIO)
        if atr.token == 'com':
            return
        if _match_postag_regexp(atr, _NOM) or _match_postag_regexp(atr, _ADJECTIU):
            self.initialize()
            return
        self.adverb |= _match_postag_regexp(atr, _ADVERBI)
        self.punctuation |= (_match_postag_regexp(atr, _PUNTUACIO) or atr.token == ',')
        self.infinitive |= _match_postag_regexp(atr, _INFINITIVE)

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
                or (self.punctuation and _match_postag_regexp(atr, _PUNTUACIO))
                or (self.infinitive and _match_regexp(atr.token, _COORDINACIO_IONI))
                or (self.infinitive and self.adverb)):
            return False
        return ((_match_postag_regexp(atr, _KEEP_COUNT) or _match_regexp(atr.token, _KEEP_COUNT2)
                 or _match_postag_regexp(atr, _ADVERBIS_ACCEPTATS))
                and not _match_regexp(atr.token, _STOP_COUNT)
                and (not _match_postag_regexp(atr, _GV) or _match_postag_regexp(atr, _GN_)))


def _update_j_value(tokens, i, j, level):
    # deux ou plus
    if _match_regexp(tokens[i - j].token, _COORDINACIO_IONI):
        if i - j - 1 > 0 and i - j + 1 < len(tokens):
            if _match_postag_regexp(tokens[i - j - 1], _DET) and tokens[i - j + 1].token == 'plus':
                j = j + 1
    return j


class PostponedAdjectiveConcordanceFilter(RuleFilter):
    """Port of org.languagetool.rules.fr.PostponedAdjectiveConcordanceFilter:
    accepts the match if the adjective (the first token of the match)
    doesn't agree with the previous noun and at the same time it doesn't
    agree with any of the previous words. Takes care of some exceptions.
    The suggestions are the adjective forms synthesized for the possible
    gender/number."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
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
            if _match_postag_regexp(t, _DET_CP):
                if _match_postag_regexp(tokens[i - j + 1], _NOM_MP):
                    c_dms[level] += 1
                    can_be_mp = True
                if _match_postag_regexp(tokens[i - j + 1], _NOM_FP):
                    c_dfs[level] += 1
                    can_be_fp = True
            # TODO DET_CS, DET_CP without noun afterwards
            if not _match_postag_regexp(t, _ADVERBI):
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
                        and _match_postag_regexp(t, _PREPOSICIONS)  # exclude "des" when it is only determiner
                        and not _match_postag_regexp(t, _CONJUNCIO)  # "com" com a conjunció
                        and not _match_regexp(tokens[i - j - 1].token, _COORDINACIO_IONI)
                        and not _match_postag_regexp(tokens[i - j + 1], _ADVERBI)):
                    level += 1
                # exception: d'environ
                elif (java_equals_ignore_case(t.token, "d'")
                      and java_equals_ignore_case(tokens[i - j + 1].token, 'environ')):
                    level += 1
            j = _update_j_value(tokens, i, j, level)
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
                is_plural = is_plural and c_d[j] > 1 and level > 1  # cN[j]>1
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
        elif _match_postag_regexp(tokens[i], _ADJECTIU_MN):
            subst_pattern, adj_pattern, gn_pattern = _GN_MN, _ADJECTIU_M, _GN_MN_
        elif _match_postag_regexp(tokens[i], _ADJECTIU_FN):
            subst_pattern, adj_pattern, gn_pattern = _GN_FN, _ADJECTIU_FN, _GN_FN_
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
                or (_match_postag_regexp(prev, _GN_) and not _match_postag_regexp(prev, gn_pattern))
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
            while i - j > 0 and app.keep_counting(tokens[i - j]) and (level > 1 or j < 4):
                t = tokens[i - j]
                # there is a previous agreeing noun
                if (not _match_postag_regexp(t, _GN_) and _match_postag_regexp(t, _NOM_DET)
                        and _match_postag_regexp(t, subst_pattern)):
                    return None
                # there is a previous agreeing adjective (in a nominal group)
                elif _match_postag_regexp(t, gn_pattern):
                    return None
                j = _update_j_value(tokens, i, j, 0)
                app.update(tokens[i - j])
                j += 1

        synth = match.rule.language.synthesizer
        # The rule matches
        # Synthesize suggestions
        suggestions = []
        token = tokens[pattern_token_pos]
        at = _get_analyzed_token(token, _ADJECTIU_CS)
        if at is not None:
            suggestions.extend(synth.synthesize(at, 'J e p', True))
        if not suggestions:
            at = _get_analyzed_token(token, _ADJECTIU_CP)
            if at is not None:
                suggestions.extend(synth.synthesize(at, 'J e s', True))
        if not suggestions and is_plural:
            at = _get_analyzed_token(token, _ADJECTIU_P)
            if at is not None:
                suggestions.extend(synth.synthesize(at, 'J . p|V ppa . p', True))
        at = _get_analyzed_token(token, _ADJECTIU)
        if at is not None and not suggestions:
            if can_be_ms and not is_plural:
                suggestions.extend(synth.synthesize(at, 'J [me] sp?|V ppa m s', True))
            if can_be_fs and not is_plural:
                suggestions.extend(synth.synthesize(at, 'J [fe] sp?|V ppa f s', True))
            if can_be_mp:
                suggestions.extend(synth.synthesize(at, 'J [me] s?p|V ppa m p', True))
            if can_be_fp:
                suggestions.extend(synth.synthesize(at, 'J [fe] s?p|V ppa f p', True))
            if can_be_ms and (is_plural or can_be_p):
                suggestions.extend(synth.synthesize(at, 'J [me] s?p|V ppa m p', True))
            if can_be_fs and not can_be_ms and (is_plural or can_be_p):
                suggestions.extend(synth.synthesize(at, 'J [fe] s?p|V ppa f p', True))
        # set suggestion removing duplicates
        suggestions = list(dict.fromkeys(suggestions))
        # avoid the original token as suggestion
        lower_token = token.token.lower()
        if lower_token in suggestions:
            suggestions.remove(lower_token)
        if not suggestions:
            return None
        match.set_suggested_replacements(suggestions)
        return match
