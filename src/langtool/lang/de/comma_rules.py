"""Port of org.languagetool.rules.de.MissingCommaRelativeClauseRule: checks
a sentence for a missing comma before (behind=False) or after (behind=True)
a relative clause."""

import threading

from ... import jregex
from ...patterns.pattern_token import PatternTokenBuilder, cs_token, pos, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.base import Category, RuleMatch
from ...rules.core import CoreRule
from ...tools import java_equals_ignore_case

# (as in Java, the range "!-–" covers all characters from U+0021 to U+2013)
_MARKS_REGEX = jregex.compile("[,;.:?•!-–—’'\"„“”…»«‚‘›‹()\\/\\[\\]]")
_PRONOUN = jregex.compile('(d(e[mnr]|ie|as|e([nr]|ss)en)|welche[mrs]?|wessen|was)')
_VERB_PATTERN = jregex.compile('(VER:[1-3]:|VER:.*:[1-3]:).*')
_ZAL_ETC_PATTERN = jregex.compile('(ZAL|AD[JV]|ART|SUB|PRO:POS|PRP).*')


def _anti_patterns():
    return [
        [token_regex('gerade|wenn'), token('das')],
        [token('anstelle'),
         token_regex('diese[rsm]|de[rsm]|dessen|jene[rsm]|[dms]?eine[rsm]|ihre[rs]|eure[sr]|unse?re[sr]')],
        [token('im'), token('Zuge'), token('dessen')],
        [cs_token('mit'), token_regex('de[mr]'), token_regex('de[mrs]'), pos_regex('SUB:.+'), cs_token('verbindet')],
        [token_regex('eine'), cs_token('menge'), pos_regex('SUB:.+')],
        [  # dass sich wie folgt formulieren lässt
            token_regex('wie'), cs_token('folgt'), pos_regex('VER:.+')],
        [  # das sollte gut überlegt sein
            token_regex('gut'), cs_token('überlegt'), cs_token('sein')],
        [  # samt Auftraggeber
            cs_token('samt'), pos_regex('SUB:DAT.*')],
        [  # ... denen sie ausgesetzt sind.
            pos_regex('PA2:PRD:GRU:VER|VER:PA2.*'), cs_token('sind'), pos_regex('PKT')],
        [cs_token('am'), pos('ADJ:PRD:SUP'), pos_regex('PRP:.+'), token_regex('d(e[mnr]|ie|as|e([nr]|ss)en)')],
        [  # Aber denen etwas beibringen zu müssen, die sich sträuben, das ist die wahre Hölle.
            pos('SENT_START'), token('Aber'),
            token_regex('der|die|denen|das|jenen|einigen|anderen|vielen|manchen|allen')],
        [  # Aus diesem Grund sind die Wörter nicht direkt übersetzt, stattdessen wird der Zustand oder die
            # Situation beschrieben in der die Wörter benutzt werden.
            pos_regex('PA2.*|VER:PA2.*'), token('werden'), token_regex('[\\.\\!\\?…\\:;]+')],
        [  # Plan von Maßnahmen, mit denen das Ansteckungsrisiko während des Aufenthalts an einem Ort verringert
            # werden soll
            token('werden'),
            PatternTokenBuilder().pos_regex('SENT_END').match_inflected_forms().token_regex(
                'sollen|können|müssen').build()],
        [  # Aus diesem Grund sind die Wörter nicht direkt übersetzt, stattdessen wird der Zustand oder die
            # Situation beschrieben in der die Wörter benutzt werden.
            pos_regex('PA2.*|VER:PA2.*'),
            PatternTokenBuilder().pos_regex('SENT_END').match_inflected_forms().token_regex('haben|werden').build()],
        [  # Es würde noch sehr helfen eine Kopie der Google Slide dort zu verlinken damit wir das direkt
            # nachstellen können
            pos_regex('VER:INF.*'),
            PatternTokenBuilder().pos_regex('SENT_END').match_inflected_forms().token_regex(
                'können|werden|sollen|dürfen|müssen|wollen|mögen').build()],
        [  # Komma an der falschen Stelle
            token_regex('ja|mal'), cs_token('was')],
        [  # Komma an der falschen Stelle
            pos_regex('SENT_START|PKT'), cs_token('aber'), token_regex('solange|wenn|wo|wie|was'),
            token_regex('du|er|sie|sich|man|euch|uns|die|der|das')],
        [  # Komma an der falschen Stelle
            cs_token('selbst'), cs_token('wenn'), token_regex('du|er|sie|sich|man|euch|uns|die|der|das'),
            token_regex('die|der|das')],
        [  # Komma an der falschen Stelle
            cs_token('wie'), token_regex('die|der|das')],
        [  # Kein Komma in "weder ... noch ..."
            PatternTokenBuilder().set_skip(12).match_inflected_forms().token('weder').build(), token('noch')],
        [pos_regex('VER:.*1:SIN:KJ1:.+'), pos_regex('VER:MOD:[12]:.+'), pos_regex('PKT|KON:NEB')],
        [  # Er warnt auch vor Autos, die soeben überholt haben bzw. überholt wurden.
            pos_regex('VER:.+'), cs_token('bzw'), cs_token('.'), pos_regex('VER:.+')],
        # … Planungen, die sich noch auf die ganze Stadt bezogen wurden aufgegeben.
        [token_regex('w[eu]rden'), pos_regex('PA2:PRD:GRU:VER|VER:PA2.*'), pos('PKT')],
        # Der Beitrag, den Sie versucht haben aufzurufen, existiert nicht mehr oder wurde verschoben.
        [pos_regex('PA2:PRD:GRU:VER|VER:PA2.*'), token_regex('haben?|hatten?'), pos_regex('VER:EIZ.*'), pos('PKT')],
        [pos_regex('VER.*'), token_regex('\\u2063')],
    ]


_anti_patterns_cache = []
_anti_patterns_lock = threading.Lock()


def _get_anti_patterns():
    if not _anti_patterns_cache:
        with _anti_patterns_lock:
            if not _anti_patterns_cache:
                from ...api import get_language
                _anti_patterns_cache.append(make_anti_patterns(_anti_patterns(), get_language('de-DE')))
    return _anti_patterns_cache[0]


def _is_separator(token):
    """is a separator"""
    return _MARKS_REGEX.fullmatch(token) is not None or token == 'und' or token == 'oder'


def _next_separator(tokens, start):
    """get the position of the next separator"""
    for i in range(start, len(tokens)):
        if _is_separator(tokens[i].token):
            return i
    return len(tokens) - 1


def _is_prp(token):
    """is preposition"""
    return token.has_pos_tag_starting_with('PRP:') and not token.immunized


def _is_verb(tokens, n):
    """is a potential verb used in sentence or subclause"""
    return (tokens[n].matches_pos_tag_regex(_VERB_PATTERN)
            and not tokens[n].matches_pos_tag_regex(_ZAL_ETC_PATTERN)
            and (not tokens[n].has_pos_tag_starting_with('VER:INF:') or tokens[n - 1].token != 'zu')
            and not tokens[n].immunized)


def _is_any_verb(tokens, n):
    """is any verb but not an "Infinitiv mit zu" """
    return (tokens[n].has_pos_tag_starting_with('VER:')
            or (n < len(tokens) - 1
                and ((tokens[n].token == 'zu' and tokens[n + 1].has_pos_tag_starting_with('VER:INF:'))
                     or (tokens[n].has_pos_tag('NEG') and tokens[n + 1].has_pos_tag_starting_with('VER:')))))


def is_verb_behind(tokens, end):
    """is a verb after sub clause"""
    return end < len(tokens) - 1 and tokens[end].token == ',' and tokens[end + 1].has_pos_tag_starting_with('VER:')


def _verb_pos(tokens, start, end):
    """gives the positions of verbs in a subclause"""
    verbs = []
    for i in range(start, end):
        if _is_verb(tokens, i):
            if tokens[i].has_pos_tag_starting_with('PA'):
                gender = _get_gender(tokens[i])
                s_str = '(ADJ|PA[12]):.*' + gender + '.*'
                j = i + 1
                while j < end and tokens[j].matches_pos_tag_regex(s_str):
                    j += 1
                if not tokens[j].matches_pos_tag_regex('(SUB|EIG):.*' + gender + '.*') and \
                        not tokens[j].is_pos_tag_unknown:
                    verbs.append(i)
            else:
                verbs.append(i)
    return verbs


def _is_kon_unt(token):
    """first token initiate a subclause"""
    t = token.token
    return token.has_pos_tag('KON:UNT') or any(java_equals_ignore_case(t, w) for w in ('wer', 'wo', 'wohin'))


def _has_potential_subclause(tokens, start, end):
    """checks to what position a test of relative clause should done,
    returns -1 if no potential relative clause is assumed"""
    verbs = _verb_pos(tokens, start, end)
    if len(verbs) == 1 and end < len(tokens) - 2 and verbs[0] == end - 1:
        next_end = _next_separator(tokens, end + 1)
        next_verbs = _verb_pos(tokens, end + 1, next_end)
        if _is_kon_unt(tokens[start]):
            if len(next_verbs) > 1 or (len(next_verbs) == 1 and next_verbs[0] == end - 1):
                return verbs[0]
        elif len(next_verbs) > 0:
            return verbs[0]
        return -1
    if len(verbs) == 2:
        if tokens[verbs[0]].matches_pos_tag_regex('VER:(MOD|AUX):.*') and \
                tokens[verbs[1]].has_pos_tag_starting_with('VER:INF:'):
            return verbs[0]
        if tokens[verbs[0]].has_pos_tag_starting_with('VER:AUX:') and \
                tokens[verbs[1]].has_pos_tag_starting_with('VER:PA2:'):
            return -1
        if end == len(tokens) - 1 and verbs[0] == end - 2 and \
                tokens[verbs[0]].has_pos_tag_starting_with('VER:INF:') and \
                tokens[verbs[1]].has_pos_tag_starting_with('VER:MOD:'):
            return -1
    if len(verbs) == 3:
        if tokens[verbs[0]].has_pos_tag_starting_with('VER:MOD:') and (
                (tokens[verbs[2] - 1].matches_pos_tag_regex('VER:(INF|PA2):.*')
                 and tokens[verbs[2]].has_pos_tag_starting_with('VER:INF:'))
                or (tokens[verbs[1] - 1].token == 'weder' and tokens[verbs[1]].has_pos_tag_starting_with('VER:INF:')
                    and tokens[verbs[2] - 1].token == 'noch'
                    and tokens[verbs[1]].has_pos_tag_starting_with('VER:INF:'))):
            return -1
    if len(verbs) > 1:
        return verbs[-1]
    return -1


def _is_pronoun(tokens, n):
    """is potential relative pronoun"""
    return _PRONOUN.fullmatch(tokens[n].token) is not None and tokens[n - 1].token != 'sowie'


def _get_gender(token):
    """get the gender of a token"""
    n_matches = 0
    ret = ''
    if token.matches_pos_tag_regex('.*:SIN:FEM.*'):
        ret += 'SIN:FEM'
        n_matches += 1
    if token.matches_pos_tag_regex('.*:SIN:MAS.*'):
        if n_matches > 0:
            ret += '|'
        ret += 'SIN:MAS'
        n_matches += 1
    if token.matches_pos_tag_regex('.*:SIN:NEU.*'):
        if n_matches > 0:
            ret += '|'
        ret += 'SIN:NEU'
        n_matches += 1
    if token.matches_pos_tag_regex('.*:PLU.*'):
        if n_matches > 0:
            ret += '|'
        ret += 'PLU'
        n_matches += 1
    if n_matches > 1:
        ret = '(' + ret + ')'
    return ret


def _matches_gender(gender, tokens, from_, to):
    """does the gender match with a subject or name?"""
    if not gender:
        m_str = 'PRO:DEM:.*SIN:NEU.*'
    else:
        m_str = '(SUB|EIG):.*' + gender + '.*'
    for i in range(to - 1, from_ - 1, -1):
        if tokens[i].matches_pos_tag_regex(m_str) and (i != 1 or not tokens[i].has_pos_tag_starting_with('VER:')):
            return True
    return False


def _is_article_without_sub(gender, tokens, n):
    """is the token a potential article without a noun"""
    if not gender:
        return False
    return tokens[n].has_pos_tag_starting_with('VER:') and \
        tokens[n - 1].matches_pos_tag_regex('(ADJ|PA[12]|PRO:POS):.*' + gender + '.*')


def _skip_sub(tokens, n, to):
    """skip tokens till the next noun, check for e.g. "das in die dunkle
    Garage fahrende Auto" -> "das" is article"""
    gender = _get_gender(tokens[n])
    for i in range(n + 1, to):
        if tokens[i].matches_pos_tag_regex('(SUB|EIG):.*' + gender + '.*'):
            return i
    return -1


def _skip_to_sub(gender, tokens, n, to):
    """skip tokens till the next noun, check for e.g. "das in die dunkle
    Garage fahrende Auto" -> "das" is article"""
    if tokens[n + 1].matches_pos_tag_regex('PA[12]:.*' + gender + '.*'):
        return n + 1
    i = n + 1
    while i < to:
        if tokens[i].matches_pos_tag_regex('(ADJ|PA[12]):.*' + gender + '.*') or tokens[i].is_pos_tag_unknown:
            return i
        if tokens[i].has_pos_tag_starting_with('ART'):
            i = _skip_sub(tokens, i, to)
            if i < 0:
                return i
        i += 1
    return -1


def _is_article(gender, tokens, from_, to):
    """check if token is potentially an article"""
    if not gender:
        return False
    s_sub = '(SUB|EIG):.*' + gender + '.*'
    s_adj = '(ZAL|PRP:|KON:|ADV:|ADJ:PRD:|(ADJ|PA[12]|PRO:(POS|DEM|IND)):.*' + gender + ').*'
    i = from_ + 1
    while i < to:
        if tokens[i].matches_pos_tag_regex(s_sub) or tokens[i].is_pos_tag_unknown:
            return True
        if tokens[i].has_pos_tag_starting_with('ART') or not tokens[i].matches_pos_tag_regex(s_adj):
            if _is_article_without_sub(gender, tokens, i):
                return True
            skip_to = _skip_to_sub(gender, tokens, i, to)
            if skip_to > 0:
                i = skip_to
            else:
                return False
        i += 1
    return to < len(tokens) and _is_article_without_sub(gender, tokens, to)


def _missed_comma_in_front(tokens, start, end, last_verb):
    """gives back position where a comma is missed, PRP has to be treated
    separately"""
    for i in range(start, last_verb - 1):
        if tokens[i].immunized:
            continue
        if _is_pronoun(tokens, i):
            gender = _get_gender(tokens[i])
            if not _is_any_verb(tokens, i + 1) and _matches_gender(gender, tokens, start, i) and \
                    not _is_article(gender, tokens, i, last_verb):
                return i
    return -1


def _is_two_combined_verbs(first, second):
    """is a special combination of two verbs combination"""
    return first.matches_pos_tag_regex('(VER:.*INF|.*PA[12]:).*') and second.has_pos_tag_starting_with('VER:')


def _is_three_combined_verbs(tokens, first, last):
    """is a special combination of three verbs combination"""
    return (tokens[first].matches_pos_tag_regex('VER:(AUX|INF|PA[12]).*')
            and tokens[first + 1].matches_pos_tag_regex('VER:(.*INF|PA[12]).*')
            and tokens[last].matches_pos_tag_regex('VER:(MOD|AUX).*'))


def _is_four_combined_verbs(tokens, first, last):
    """is a special combination of four verbs combination"""
    return (tokens[first].has_partial_pos_tag('KJ2') and tokens[first + 1].has_partial_pos_tag('PA2')
            and tokens[first + 2].matches_pos_tag_regex('VER:(.*INF|PA[12]).*')
            and tokens[last].matches_pos_tag_regex('VER:(MOD|AUX).*'))


def _is_par(token):
    """is participle"""
    return token.has_pos_tag_starting_with('PA2:') or token.has_pos_tag_starting_with('VER:PA2')


def _is_infinitiv_zu(tokens, last):
    """is participle plus special combination of two verbs combination"""
    return tokens[last - 1].token == 'zu' and tokens[last].matches_pos_tag_regex('VER:.*INF.*')


def _is_two_plus_combined_verbs(tokens, first, last):
    """is verb plus special combination of two verbs combination"""
    return tokens[first].matches_pos_tag_regex('.*PA[12]:.*') and tokens[last - 1].matches_pos_tag_regex('VER:.*INF.*')


def _is_kon_after_verb(tokens, start, end):
    """conjunction follows last verb"""
    if tokens[start].matches_pos_tag_regex('VER:(MOD|AUX).*') and \
            tokens[start + 1].matches_pos_tag_regex('(KON|PRP).*'):
        if start + 3 == end:
            return True
        for i in range(start + 2, end):
            if tokens[i].matches_pos_tag_regex('(SUB|PRO:PER).*'):
                return True
    return False


def _is_special_pair(tokens, first, second):
    """two infinitive verbs as pair"""
    if first + 3 >= second and tokens[first].matches_pos_tag_regex('VER:.*INF.*') \
            and tokens[first + 1].token in ('als', 'noch') \
            and tokens[first + 2].matches_pos_tag_regex('VER:.*INF.*'):
        if first + 2 == second:
            return True
        return _is_two_combined_verbs(tokens[second - 1], tokens[second])
    return False


def _is_perfect(tokens, first, second):
    """is a pair of verbs to build the perfect"""
    return tokens[first].has_pos_tag_starting_with('VER:AUX:') and tokens[second].matches_pos_tag_regex(
        'VER:.*(INF|PA2).*')


def _is_special_inf(tokens, first, second, start):
    """is Infinitive in combination with substantiv"""
    if not tokens[first].has_pos_tag_starting_with('VER:INF'):
        return False
    for i in range(first - 1, start, -1):
        if tokens[i].has_pos_tag_starting_with('ART'):
            i = _skip_sub(tokens, i, second)
            return i > 0
    return False


def _is_perfect3(tokens, first, second, third):
    """is a pair of verbs to build the perfect"""
    return tokens[second].matches_pos_tag_regex('VER:.*INF.*') and _is_perfect(tokens, first, third)


def _is_separator_or_inf(tokens, n):
    """is separator or VER:INF"""
    return (_is_separator(tokens[n].token) or tokens[n].has_pos_tag_starting_with('VER:INF')
            or (len(tokens) > n + 1 and tokens[n].token == 'zu'
                and tokens[n + 1].matches_pos_tag_regex('VER:.*INF.*')))


def _get_comma_behind(tokens, verbs, start, end):
    """gives back position where a comma is missed"""
    if len(verbs) == 1:
        if _is_separator(tokens[verbs[0] + 1].token):
            return -1
        return verbs[0]
    elif len(verbs) == 2:
        if _is_special_pair(tokens, verbs[0], verbs[1]):
            if _is_separator_or_inf(tokens, verbs[1] + 1):
                return -1
            return verbs[1]
        elif verbs[0] + 1 == verbs[1]:
            if _is_two_combined_verbs(tokens[verbs[0]], tokens[verbs[1]]):
                if _is_separator_or_inf(tokens, verbs[1] + 1) or _is_kon_after_verb(tokens, verbs[1], end):
                    return -1
                return verbs[1]
        elif verbs[0] + 2 == verbs[1]:
            if _is_three_combined_verbs(tokens, verbs[0], verbs[1]):
                if _is_separator_or_inf(tokens, verbs[1] + 1):
                    return -1
                return verbs[1]
        if _is_par(tokens[verbs[0]]) or _is_perfect(tokens, verbs[0], verbs[1]) \
                or _is_infinitiv_zu(tokens, verbs[1]) or _is_special_inf(tokens, verbs[0], verbs[1], start):
            if _is_separator_or_inf(tokens, verbs[1] + 1):
                return -1
            return verbs[1]
    elif len(verbs) == 3:
        if _is_two_plus_combined_verbs(tokens, verbs[0], verbs[2]):
            if _is_separator_or_inf(tokens, verbs[2] + 1):
                return -1
            return verbs[2]
        elif verbs[0] + 2 == verbs[2]:
            if verbs[0] + 1 == verbs[1] and _is_three_combined_verbs(tokens, verbs[0], verbs[2]):
                if _is_separator_or_inf(tokens, verbs[2] + 1):
                    return -1
                return verbs[2]
        elif verbs[0] + 3 == verbs[2] and _is_four_combined_verbs(tokens, verbs[0], verbs[2]):
            if _is_separator_or_inf(tokens, verbs[2] + 1):
                return -1
            return verbs[2]
        elif tokens[verbs[2]].has_pos_tag_starting_with('VER:MOD:') and _is_special_pair(tokens, verbs[0], verbs[1]):
            if _is_separator_or_inf(tokens, verbs[2] + 1):
                return -1
            return verbs[2]
        if _is_perfect3(tokens, verbs[0], verbs[1], verbs[2]):
            if _is_separator_or_inf(tokens, verbs[2] + 1):
                return -1
            return verbs[1]
    return verbs[0]


def _missed_comma_behind(tokens, in_front, start, end):
    """gives back position where a comma is missed, PRP has to be treated
    separately"""
    for i in range(start, end):
        if _is_pronoun(tokens, i):
            verbs = _verb_pos(tokens, i, end)
            if verbs:
                gender = _get_gender(tokens[i])
                if not _is_any_verb(tokens, i + 1) and _matches_gender(gender, tokens, in_front, i - 1) and \
                        not _is_article(gender, tokens, i, verbs[-1]):
                    return _get_comma_behind(tokens, verbs, i, end)
    return -1


def _get_sin_or_plu_of_pro(token):
    """checks if personal pronoun is singular or plural, gives back None if
    token is not a personal pronoun"""
    if not token.has_partial_pos_tag('PRO:PER:') and not token.has_pos_tag_starting_with('IND:'):
        return None
    ret = ''
    n_matches = 0
    if token.matches_pos_tag_regex('.*:SIN.*'):
        ret += 'SIN'
        n_matches += 1
    if token.matches_pos_tag_regex('.*:PLU.*'):
        if ret:
            ret += '|'
        ret += 'PLU'
        n_matches += 1
    if n_matches > 1:
        ret = '(' + ret + ')'
    return ret


def _is_verb_pro_pair(tokens, n):
    sin_or_plu = _get_sin_or_plu_of_pro(tokens[n + 1])
    if sin_or_plu is None:
        return False
    return tokens[n].matches_pos_tag_regex('VER:.*' + sin_or_plu + '.*')


class MissingCommaRelativeClauseRule(CoreRule):
    """Port of MissingCommaRelativeClauseRule (by Fred Kruse): a missing
    comma before (behind=False, COMMA_IN_FRONT_RELATIVE_CLAUSE) or after
    (behind=True, COMMA_BEHIND_RELATIVE_CLAUSE) a relative clause."""

    def __init__(self, messages, language=None, user_config=None, behind=False):
        super().__init__(messages, language)
        self.category = Category('HILFESTELLUNG_KOMMASETZUNG', 'Kommasetzung', 'INTERNAL', True)
        self.behind = behind

    def get_id(self):
        return 'COMMA_BEHIND_RELATIVE_CLAUSE' if self.behind else 'COMMA_IN_FRONT_RELATIVE_CLAUSE'

    def get_description(self):
        return 'Fehlendes Komma nach Relativsatz' if self.behind else 'Fehlendes Komma vor Relativsatz'

    def get_anti_patterns(self):
        return _get_anti_patterns()

    def match(self, sentence):
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        if len(tokens) <= 1:
            return rule_matches
        sub_start = 1
        if _is_separator(tokens[sub_start].token):
            sub_start += 1
        if self.behind:
            sub_in_front = sub_start
            sub_start = _next_separator(tokens, sub_in_front) + 1
            while sub_start < len(tokens):
                sub_end = _next_separator(tokens, sub_start)
                last_verb = _has_potential_subclause(tokens, sub_start, sub_end)
                if last_verb > 0:
                    n_token = _missed_comma_behind(tokens, sub_in_front, sub_start, sub_end)
                    if n_token > 0:
                        if _is_verb_pro_pair(tokens, n_token):
                            match = RuleMatch(self, sentence, tokens[n_token - 1].start_pos,
                                              tokens[n_token + 1].end_pos,
                                              'Sollten Sie hier ein Komma einfügen oder zwei?')
                            t0 = tokens[n_token - 1].token
                            t1 = tokens[n_token].token
                            t2 = tokens[n_token + 1].token
                            match.set_suggested_replacements([t0 + ', ' + t1 + ' ' + t2 + ',',
                                                              t0 + ' ' + t1 + ' ' + t2 + ',',
                                                              t0 + ' ' + t1 + ', ' + t2])
                            rule_matches.append(match)
                        else:
                            match = RuleMatch(self, sentence, tokens[n_token].start_pos, tokens[n_token + 1].end_pos,
                                              'Sollten Sie hier ein Komma einfügen?')
                            match.set_suggested_replacement(tokens[n_token].token + ', ' + tokens[n_token + 1].token)
                            rule_matches.append(match)
                sub_in_front = sub_start
                sub_start = sub_end + 1
        else:
            while sub_start < len(tokens):
                sub_end = _next_separator(tokens, sub_start)
                last_verb = _has_potential_subclause(tokens, sub_start, sub_end)
                if last_verb > 0:
                    n_token = _missed_comma_in_front(tokens, sub_start, sub_end, last_verb)
                    if n_token > 0:
                        start_token = n_token - (2 if _is_prp(tokens[n_token - 1]) else 1)
                        match = RuleMatch(self, sentence, tokens[start_token].start_pos, tokens[n_token].end_pos,
                                          'Sowohl angehängte als auch eingeschobene Relativsätze werden durch Kommas '
                                          'vom Hauptsatz getrennt.')
                        if n_token - start_token > 1:
                            match.set_suggested_replacement(tokens[start_token].token + ', '
                                                            + tokens[n_token - 1].token + ' ' + tokens[n_token].token)
                        else:
                            match.set_suggested_replacement(tokens[start_token].token + ', ' + tokens[n_token].token)
                        rule_matches.append(match)
                sub_start = sub_end + 1
        return rule_matches
