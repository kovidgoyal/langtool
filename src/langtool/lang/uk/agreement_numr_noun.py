"""Port of org.languagetool.rules.uk.TokenAgreementNumrNounRule and
TokenAgreementNumrNounExceptionHelper: the agreement of numerals and the
following nouns (case, gender and number)."""

from ... import jregex
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import java_equals_ignore_case
from . import helpers as lh
from . import pos_tag_helper as pth
from .helpers import Inflection, java_contains, java_disjoint

_NOUN_IGNORE_PATTERN = jregex.compile('.*(prop|noun.*pron|v_oru).*')
_NUMR_PATTERN = jregex.compile('numr(?!.*abbr).*')
_NOUN_NUMR_ALL_PATTERN = jregex.compile('noun:inanim:([mf]:v_naz|p:v_(naz|rod)).*:numr.*|numr.*abbr.*|number')
DVA_3_4_PATTERN = jregex.compile('оби(два|дві)|(.+-)?((два|дві)|три|чотири)')
_DVA_PATTERN = jregex.compile('(оби)?два|.+-два', jregex.IGNORECASE)
_DVI_PATTERN = jregex.compile('(оби)?дві|.+-дві', jregex.IGNORECASE)
_1_5 = jregex.compile('([0-9]+[–-])?1,5')
_2_5 = jregex.compile('.*(?<!1)[234],5')
_5_5 = jregex.compile('([0-9]+[–-])?([0-9\\h]*[05-9]|[0-9\\h]*1[1-4]),5')
_FRACT = jregex.compile('.*,[1-9]+')
_2TO4 = jregex.compile('([0-9]+[–-])?[^,]*(?<!1)[234]')
_5TO9 = jregex.compile('[0-9\\h]*([5-90]|1[2-4])')
_5TO9_ALPHA = jregex.compile(
    '(.+-)?(п.ять|шість|сім|вісім|(три)?дев.?ять|.*дцять|сорок|.*десять?|дев.яносто|сто|двісті|триста|чотириста'
    '|півтораста|.+сот)|(де)?кілька|кількох|аніскільки')
_NOUN_FORCE_PATTERN = jregex.compile(
    'чоловік|солдат|тон|(нано|мікро|мілі|дека|кіло|мега|гіга|тера|пета)?(герц|байт|біт|бар|бер|ват|вольт|децибел'
    '|рентген|моль|мікрон|грам|аршин|лат|карат)')

_ADJ_P_V_ROD = jregex.compile('adj:p:v_rod.*')
_NUM_ADJ_SUFFIX = jregex.compile('.*[0-9]-[а-яіїєґ].*')
_Z_IZ_ZI = jregex.compile('з|із|зі')
_POLOVYNOYU = jregex.compile('половиною|третиною|чвертю|гаком')
_ADJ_P_V_ROD_NAZ = jregex.compile('adj:p:v_(rod|naz).*')
_M_V_ROD = jregex.compile('.*:m:v_rod.*')
_ENDS_AYA = jregex.compile('.*[ая]')
_PIVTORA = jregex.compile('(один-|одне-)?півтора')
_PIVTORY = jregex.compile('(одн.+-)?півтори')
_RAZ = jregex.compile('раз|рази|разу|разів')
_DVOYE = jregex.compile('((.+-)?(двоє|двох|троє|.+еро|.+ьох))|обидвоє|обидвох|обоє|обох|двійко')
_BAHATO = jregex.compile('(не)?багато|багато-багато|(не|чи)?мало|с[тк]ільки(-то|сь)?|.+-скільки|кілько')
_SENT_PUNCT = jregex.compile('[.,;!?)—–-]')
_GEO_V_ROD = jregex.compile('noun:inanim:.:v_rod:prop:geo.*')
_NOUN_INANIM_P_V_ZNA = jregex.compile('noun:inanim:p:v_zna.*')
_ADJ_P_V_ZNA = jregex.compile('adj:p:v_zna.*')
_NOUN_P_V_ROD = jregex.compile('(noun:.*p:v_rod).*')
_ENDS_UYU = jregex.compile('.*[ую]')
_NOUN_M_V_DAV = jregex.compile('noun.*?:m:v_dav.*')
_ADJ_V_MIS = jregex.compile('adj.*?v_mis.*')
_NOUN_V_MIS = jregex.compile('noun.*?v_mis.*')
_GENDER_VIDM = jregex.compile(':.:v_...')
_NOUN_ANIM_M_V_ROD = jregex.compile('noun:anim:m:v_rod.*')
_NYN_A = jregex.compile('.*нин[ая]')
_NOUN_ANIM_P_V_NAZ = jregex.compile('noun:anim:p:v_naz.*')
_NY = jregex.compile('.*ни')
_AYA_END = jregex.compile('[ая]$')
_NY_END = jregex.compile('ни$')
_VAR_BAD_ARCH = jregex.compile(':(var|bad|arch)')
_FRACTIONS = ('десятих', 'сотих', 'тисячних', 'третіх', 'четвертих')


def _infl(gender, case, anim=None):
    return Inflection(gender, case, anim)


def _remove_all(items, to_remove):
    """ArrayList.removeAll: removes the elements e with to_remove.contains(e)"""
    items[:] = [e for e in items if not java_contains(to_remove, e)]


def _linked_hash_set(items):
    """new ArrayList<>(new LinkedHashSet<>(items)) for Inflections: an
    element is dropped if an earlier one has the same hashCode (case and
    gender) and the new element equals() it"""
    out = []
    for e in items:
        if not any(x.case == e.case and x.gender == e.gender and e == x for x in out):
            out.append(e)
    return out


class State:
    """TokenAgreementNumrNounRule.State"""

    def __init__(self):
        self.number = False
        self.numr_pos = 0
        self.noun_pos = 0
        self.numr_token_readings = []
        self.numr_analyzed_token_readings = None

    def is_empty(self):
        return not self.numr_token_readings

    def reset(self):
        self.number = False
        self.numr_token_readings = []
        self.numr_analyzed_token_readings = None


class TokenAgreementNumrNounRule(Rule):
    """Checks that a numeral and the following noun agree on case, gender and
    number"""

    def __init__(self, messages, language):
        super().__init__()
        self.messages = messages
        self.category = Categories.get('MISC', messages)
        self.synthesizer = language.synthesizer

    def get_id(self):
        return 'UK_NUMR_NOUN_INFLECTION_AGREEMENT'

    def get_description(self):
        return 'Узгодження відмінків, роду і числа числівника та іменника'

    def get_short(self):
        return 'Узгодження числівника та іменника'

    def match(self, sentence):
        from .agreement_adj_noun import format_inflections
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        state = State()
        i = 0
        while True:
            i += 1
            if i >= n:
                break
            atr = tokens[i]
            pos_tag0 = atr.readings[0].pos_tag
            clean_token = atr.get_clean_token()
            if pos_tag0 is None or clean_token is None:
                state.reset()
                continue
            # no need to start checking on last token or if no noun
            if i == n - 1 and state.is_empty():
                continue
            clean_token_lower = clean_token.lower()

            # grab initial numr inflections
            if pth.has_pos_tag(tokens[i], _NOUN_NUMR_ALL_PATTERN):
                if i < n - 1 and _NOUN_FORCE_PATTERN.fullmatch(tokens[i + 1].get_clean_token().lower()):
                    self._start(state, i, atr, tokens)
                    continue
                if i < n - 2 and pth.has_pos_tag(tokens[i + 1], _ADJ_P_V_ROD) \
                        and _NOUN_FORCE_PATTERN.fullmatch(tokens[i + 2].get_clean_token().lower()):
                    self._start(state, i, atr, tokens)
                    i += 1
                    continue

            if pth.has_pos_tag(tokens[i], _NUMR_PATTERN):
                state.reset()
                # 57-ма вулиця
                if _NUM_ADJ_SUFFIX.fullmatch(clean_token):
                    continue
                if lh.has_lemma_part_pos(atr, ('мати',), 'verb'):
                    state.reset()
                    continue
                # один одному руки
                if lh.has_lemma(atr, ('один',)):
                    state.reset()
                    continue
                for token in atr.readings:
                    adj_pos_tag = token.pos_tag
                    # null can happen for words with \u0301 or \u00AD
                    if adj_pos_tag is not None and (adj_pos_tag.startswith('numr')
                                                    or _NOUN_NUMR_ALL_PATTERN.fullmatch(adj_pos_tag)):
                        state.numr_pos = i
                        state.numr_token_readings.append(token)
                        state.numr_analyzed_token_readings = atr
                continue
            elif pth.has_pos_tag(tokens[i], 'number'):
                state.numr_pos = i
                state.numr_token_readings.extend(tokens[i].readings)
                state.numr_analyzed_token_readings = atr
                state.number = True
                continue

            if state.is_empty():
                continue

            # skip for: два з половиною
            if i < n - 2 and _Z_IZ_ZI.fullmatch(clean_token_lower) \
                    and _POLOVYNOYU.fullmatch(tokens[i + 1].get_clean_token().lower()):
                i += 1
                continue

            numr_clean_lower = state.numr_analyzed_token_readings.get_clean_token().lower()
            if i < n - 1 and (_2TO4.fullmatch(numr_clean_lower) or DVA_3_4_PATTERN.fullmatch(numr_clean_lower)) \
                    and pth.has_pos_tag(tokens[i], _ADJ_P_V_ROD_NAZ) \
                    and pth.has_pos_tag_and_token(tokens[i + 1], _M_V_ROD, _ENDS_AYA):
                # skip adj for frequent mistakes, e.g. :m:v_rod: 4 маленьких єнота
                continue

            numr_clean_token = state.numr_analyzed_token_readings.get_clean_token()
            numr_token = numr_clean_token.lower()

            if _PIVTORA.fullmatch(numr_token) or _FRACT.fullmatch(numr_token):
                if _RAZ.fullmatch(clean_token_lower):
                    msg = 'Після десяткового дробу або «півтора» треба вживати «раза»'
                    rm = RuleMatch(self, sentence, state.numr_analyzed_token_readings.start_pos, atr.end_pos, msg,
                                   self.get_short())
                    rm.add_suggested_replacement(state.numr_analyzed_token_readings.token + ' раза')
                    rm.url = 'http://www.kulturamovy.org.ua/KM/pdfs/mix/61-12-65-26.pdf'
                    rule_matches.append(rm)
                    state.reset()
                    continue

            if clean_token_lower == 'тон':
                rm = RuleMatch(self, sentence, atr.start_pos, atr.end_pos, 'Ви мали на увазі: «тонн»?',
                               self.get_short())
                rm.add_suggested_replacement('тонн')
                rule_matches.append(rm)
                state.reset()
                continue

            noun_token_readings = []
            for token in atr.readings:
                noun_pos_tag = token.pos_tag
                if noun_pos_tag is None:  # can happen for words with \u0301 or \u00AD
                    continue
                if noun_pos_tag.endswith('_END'):
                    continue
                if pth.has_pos_tag(token, _NOUN_IGNORE_PATTERN):
                    noun_token_readings = []
                    break
                if noun_pos_tag.startswith('noun') or noun_pos_tag.startswith('adj'):
                    noun_token_readings.append(token)
                elif not pth.is_predict_or_insert(token):
                    noun_token_readings = []
                    break

            # limit багато with m:v_rod - багато білку
            if numr_clean_lower.endswith('багато'):
                if not (pth.has_male_ua(atr) or _NOUN_FORCE_PATTERN.fullmatch(clean_token_lower)):
                    state.reset()
                    continue

            # no noun token - restart
            if not noun_token_readings:
                state.reset()
                continue

            state.noun_pos = i

            # perform the check
            gender_of_plural_not_found = None
            master_inflections = []

            # чотири десятих відсотка
            if state.numr_pos == i - 2 and tokens[i - 1].get_clean_token().lower() in _FRACTIONS:
                master_inflections = [_infl('m', 'v_rod'), _infl('f', 'v_rod'), _infl('n', 'v_rod')]
            elif state.number:
                if _5_5.fullmatch(numr_clean_token):
                    master_inflections = [_infl('p', 'v_rod'), _infl('m', 'v_rod'), _infl('f', 'v_rod'),
                                          _infl('n', 'v_rod')]
                elif _2_5.fullmatch(numr_clean_token):
                    master_inflections = [_infl('p', 'v_naz'), _infl('p', 'v_zna', 'inanim'), _infl('m', 'v_rod'),
                                          _infl('f', 'v_rod'), _infl('n', 'v_rod')]
                elif _1_5.fullmatch(numr_clean_token) or _FRACT.fullmatch(numr_clean_token):
                    master_inflections = [_infl('m', 'v_rod'), _infl('f', 'v_rod'), _infl('n', 'v_rod')]
                elif _2TO4.fullmatch(numr_clean_token) and pth.has_pos_tag_and_token(tokens[i], _M_V_ROD, _ENDS_AYA):
                    # limited scope: otherwise too many positives
                    # 2 подолянина
                    if self._is_nyn_case(tokens, i):
                        master_inflections = [_infl('m', 'v_rod')]
                    else:
                        master_inflections = [_infl('p', 'v_naz'), _infl('p', 'v_zna')]
                elif _2TO4.fullmatch(numr_clean_token):
                    # 2 подоляни
                    if self._is_nyn_case(tokens, i):
                        master_inflections = [_infl('m', 'v_rod')]
                    else:
                        state.reset()
                        continue
                # 5-9/0 is very limited in xml rules
                elif _5TO9.fullmatch(numr_clean_token) and _NOUN_FORCE_PATTERN.fullmatch(clean_token_lower):
                    master_inflections = [_infl('p', 'v_rod')]
                else:
                    state.reset()
                    continue
            else:
                if pth.has_pos_tag(state.numr_token_readings, _NUMR_PATTERN):
                    master_inflections = lh.get_numr_inflections(state.numr_token_readings)
                else:
                    master_inflections = [_infl('p', 'v_rod')]

                p_vnaz_zna = [inf for inf in master_inflections
                              if inf.gender == 'p' and (inf.case == 'v_naz' or inf.case == 'v_zna')]

                if p_vnaz_zna:
                    if _5TO9_ALPHA.fullmatch(numr_token):
                        _remove_all(master_inflections, p_vnaz_zna)
                        master_inflections.append(_infl('p', 'v_rod'))
                    elif _DVOYE.fullmatch(numr_token):
                        _remove_all(master_inflections, p_vnaz_zna)
                        master_inflections.append(_infl('p', 'v_rod'))
                    elif _BAHATO.fullmatch(numr_token):
                        _remove_all(master_inflections, p_vnaz_zna)
                        master_inflections.extend([_infl('p', 'v_rod'), _infl('m', 'v_rod'), _infl('n', 'v_rod'),
                                                   _infl('f', 'v_rod')])
                    elif numr_token == 'пів':
                        master_inflections = [_infl('m', 'v_rod'), _infl('f', 'v_rod'), _infl('n', 'v_rod')]
                    # на три дерева
                    elif DVA_3_4_PATTERN.fullmatch(numr_token):
                        _remove_all(master_inflections, p_vnaz_zna)
                        if lh.has_lemma(tokens[i], 'друг'):
                            master_inflections = [_infl('m', 'v_rod')]
                        # 2 подолянина
                        elif self._is_nyn_case(tokens, i):
                            master_inflections.append(_infl('m', 'v_rod'))
                            if numr_token == 'обидва':
                                # обидва волинянина (пішли)
                                # вони обидва волиняни.
                                if i == n - 1 or _SENT_PUNCT.fullmatch(tokens[i + 1].get_clean_token()) \
                                        or pth.has_pos_tag(tokens[i + 1], _GEO_V_ROD):
                                    master_inflections.append(_infl('p', 'v_naz'))
                            if numr_token == 'обидві':
                                master_inflections.append(_infl('p', 'v_naz'))
                        else:
                            master_inflections.append(_infl('p', 'v_naz'))
                            if pth.has_pos_tag(noun_token_readings, _NOUN_INANIM_P_V_ZNA):
                                master_inflections.append(_infl('p', 'v_zna'))
                            elif pth.has_pos_tag(noun_token_readings, _ADJ_P_V_ZNA) and (
                                    i == n - 1 or not pth.has_pos_tag(tokens[i + 1], _NOUN_P_V_ROD)):
                                master_inflections.append(_infl('p', 'v_zna'))

                        if _DVI_PATTERN.fullmatch(numr_token):
                            gender_of_plural_not_found = self._check_plural_gender(
                                master_inflections, noun_token_readings, ':f:', 'f', gender_of_plural_not_found)
                        elif _DVA_PATTERN.fullmatch(numr_token):
                            gender_of_plural_not_found = self._check_plural_gender(
                                master_inflections, noun_token_readings, ':[mn]:', 'mn', gender_of_plural_not_found)
                else:
                    if _PIVTORA.fullmatch(numr_token):
                        # TODO: force only direct inflections for півтора
                        master_inflections = [_infl('m', 'v_rod'), _infl('n', 'v_rod')]
                    elif _PIVTORY.fullmatch(numr_token):
                        master_inflections = [_infl('f', 'v_rod')]

            noun_inflections = lh.get_noun_inflections(noun_token_readings)
            noun_inflections.extend(lh.get_adj_inflections(noun_token_readings))
            # remove dups
            noun_inflections = _linked_hash_set(noun_inflections)

            disjoint = java_disjoint(master_inflections, noun_inflections)
            if gender_of_plural_not_found is not None or disjoint:
                if is_exception(tokens, state, master_inflections, noun_inflections, noun_token_readings):
                    state.reset()
                    continue

                msg = ('Потенційна помилка: числівник не узгоджений з іменником: "%s" вимагає: [%s], а далі йде '
                       '"%s": [%s]' % (state.numr_token_readings[0].token,
                                       format_inflections(master_inflections, True),
                                       noun_token_readings[0].token, format_inflections(noun_inflections, False)))

                if _1_5.fullmatch(numr_clean_token):
                    msg = 'Після «1,5» треба вживати родовий відмінок однини'
                elif _2_5.fullmatch(numr_clean_token):
                    msg = ('Після числівника, що закінчується на 2-4 і потім «,5», іменник має стояти в називному '
                           'відмінку множини (якщо вимовляємо «з половиною»)')
                    msg += ', або в родовом відмінку однини (якщо вимовляємо «і п\'ять десятих»)'
                elif numr_clean_token.endswith(',5'):
                    msg = ('Після числівника, що закінчується на 5-9 і потім «,5», іменник має стояти в родовому '
                           'відмінку множини (якщо вимовляємо «з половиною»)')
                    msg += ', або в родовом відмінку однини (якщо вимовляємо «і п\'ять десятих»)'
                elif java_equals_ignore_case(numr_clean_token, 'півтора'):
                    msg = ('Існує правило, що після «півтора» треба вживати родовий відмінок ч. або с.р., однак у '
                           'текстах в багатьох випадках вживають і форму множини, надто коли перед іменником іде '
                           'прикметник')
                elif java_equals_ignore_case(numr_clean_token, 'півтори'):
                    msg = ('Існує правило, що після «півтора» треба вживати родовий відмінок ж.р., однак у текстах в '
                           'багатьох випадках вживають і форму множини, надто коли перед іменником іде прикметник')
                elif java_contains(master_inflections, _infl('m', 'v_rod')) and _ENDS_UYU.fullmatch(tokens[i].token) \
                        and pth.has_pos_tag(noun_token_readings, _NOUN_M_V_DAV):
                    msg += lh.USED_U_INSTEAD_OF_A_MSG
                elif not pth.has_pos_tag(state.numr_token_readings, _ADJ_V_MIS) \
                        and pth.has_pos_tag(noun_token_readings, _NOUN_V_MIS):
                    msg += '. Можливо, пропущено прийменник на/в/у...?'

                if not disjoint and gender_of_plural_not_found is not None:
                    msg += '. Можливо, не збігається рід однини для множинної форми?'

                rm = RuleMatch(self, sentence, state.numr_analyzed_token_readings.start_pos, atr.end_pos, msg,
                               self.get_short())

                suggestions = []
                if not disjoint and gender_of_plural_not_found is not None:
                    if gender_of_plural_not_found == 'f':
                        sugg1 = jregex.java_replace(jregex.compile('і$'), 'а', numr_clean_token, 1)  # два -> дві
                    else:
                        sugg1 = jregex.java_replace(jregex.compile('а$'), 'і', numr_clean_token, 1)  # дві -> два
                    suggestions = [sugg1 + ' ' + tokens[state.noun_pos].token]
                else:
                    for numr_inflection in master_inflections:
                        gender_tag = ':' + numr_inflection.gender + ':'
                        vidm_tag = numr_inflection.case
                        for noun_token in noun_token_readings:
                            if numr_inflection.anim_matters():
                                if noun_token.pos_tag.startswith('noun'):
                                    anim_tag = ':' + numr_inflection.anim_tag
                                else:
                                    anim_tag = ':r' + numr_inflection.anim_tag
                                if anim_tag not in noun_token.pos_tag:
                                    continue
                            new_noun_pos_tag = _GENDER_VIDM.sub(lambda m: gender_tag + vidm_tag,
                                                                noun_token.pos_tag, count=1)
                            for s in self.synthesizer.synthesize(noun_token, new_noun_pos_tag, False):
                                if java_equals_ignore_case(numr_clean_token, 'півтора') \
                                        and noun_token.lemma == 'раз' and s != 'раза':
                                    continue
                                suggestion = state.numr_analyzed_token_readings.token
                                for j in range(state.numr_pos + 1, state.noun_pos):
                                    suggestion += ' ' + tokens[j].token  # add middle adj
                                suggestion += ' ' + s
                                if suggestion not in suggestions:
                                    suggestions.append(suggestion)

                if suggestions:
                    rm.set_suggested_replacements(suggestions)
                rule_matches.append(rm)

            state.reset()
        return rule_matches

    @staticmethod
    def _start(state, i, atr, tokens):
        state.reset()
        state.numr_pos = i
        state.numr_token_readings.append(atr.readings[0])
        state.numr_analyzed_token_readings = atr
        state.number = pth.has_pos_tag_start(tokens[i], 'number')

    def _check_plural_gender(self, master_inflections, noun_token_readings, look_for, gender, current):
        vidm = '(naz|zna)' if len(master_inflections) == 2 else 'naz'
        if len(master_inflections) == 2:
            pattern = jregex.compile('noun.*:p:v_' + vidm + '(?!:ns).*')
        else:
            pattern = jregex.compile('noun.*:p:v_' + vidm + '.*')
        if pth.has_pos_tag(noun_token_readings, pattern) \
                and not pth.has_pos_tag(noun_token_readings, jregex.compile('adj:p:v_' + vidm + '.*')):
            found = self._find_singulars(noun_token_readings, pattern, look_for)
            if found is not None and not found:
                return gender
        return current

    @staticmethod
    def _is_nyn_case(tokens, i):
        m_vrod = pth.filter_with_token(tokens[i], _NOUN_ANIM_M_V_ROD, _NYN_A)
        if m_vrod:
            return any(r.lemma == _AYA_END.sub('', r.token.lower(), count=1) for r in m_vrod)
        p_vnaz = pth.filter_with_token(tokens[i], _NOUN_ANIM_P_V_NAZ, _NY)
        return any(r.lemma == _NY_END.sub('нин', r.token.lower(), count=1) for r in p_vnaz)

    def _find_singulars(self, noun_token_readings, pattern, look_for):
        found = set()
        for tr in noun_token_readings:
            if pth.has_pos_tag(tr, pattern):
                synth_tokens0 = self.synthesizer.synthesize(tr, tr.pos_tag, False)
                if not synth_tokens0:  # dynamically tagged: // наглядачки-африканерки
                    return None
                if tr.lemma not in found:
                    # два ока - noun:inanim:p:v_naz:var
                    singular_tag = _VAR_BAD_ARCH.sub('.*', tr.pos_tag.replace(':p:', look_for))
                    found.update(self.synthesizer.synthesize(tr, singular_tag, True))
        return found


# --- TokenAgreementNumrNounExceptionHelper ---

_EXC_NUMR = jregex.compile('багать(ох|ом|ма)|обо(х|м|ма)|(дв|трь|чотирь)о[хм]|скільки(сь)?(-небудь)?|стільки')
_EXC_NOUN = jregex.compile(
    'плюс|мінус|ранку|вечора|ночі|тепла|морозу|родом|зростом|дивом|станом|вагою|слід|типу|формату|вартістю|році'
    '|населення')
_EXC_LEMMA = jregex.compile(
    'у?весь|який(сь)?|свій|сам|цей|решта|кількість|вартий|кожний|жодний|менший|більший|вищий|нижчий')
_NOUN_V_NAZ_ROD = jregex.compile('noun.*?.:v_(naz|rod).*')
_PIVTORA_TORY = jregex.compile('(один-|одне-)?півтора|(одна-)?півтори')
_ADJ_P_NAZ_ROD = jregex.compile('adj:p:v_(naz|rod).*')
_NOUN_P_V_NAZ = jregex.compile('noun.*?:p:v_naz.*')
_NOUN_P_V_NAZ_ROD = jregex.compile('noun.*?p:v_(naz|rod).*')
_NUMR_P_V_ZNA = jregex.compile('numr:p:v_zna.*')
_NOUN_ANIM_V_NAZ = jregex.compile('noun:anim:.:v_naz.*')
_ADJ_V_ROD = jregex.compile('adj:.:v_rod.*')
_NOUN_INANIM_V_ROD_NON_PRON = jregex.compile('noun:inanim:.:v_rod(?!.*pron).*')
_NOUN_NON_PRON = jregex.compile('noun(?!.*pron).*')
_TON_TYS = jregex.compile('тон|тис|коп')
_FROM_TO = jregex.compile('від|до|протягом|[ув]продовж|близько|після|для|більше|менше')
_OBOYE = jregex.compile('обоє|двоє|троє|.+еро')
_ADJ_P_V_NAZ = jregex.compile('adj:p:v_naz.*')
_ENDS_I = jregex.compile('.+і')
_OBOYE2 = jregex.compile('обоє|обидвоє|троє')
_ARTICLE_LEMMAS = ('ч.', 'ст.', 'п.', 'частина', 'стаття', 'пункт', 'підпункт', 'абзац', '№', 'номер')
_ADJ_NUMR = jregex.compile('adj.*numr.*')
_ADJ_NON_NUMR_P_V_ROD = jregex.compile('adj(?!.*numr).*:p:v_rod.*')
_NEXT_OK = jregex.compile('adj(?!.*numr).*:p:v_rod.*|noun.*:p:v_naz.*|prep')
_ADJ_OR_NOUN = jregex.compile('(adj|noun).*')
_NEXT_PUNCT = jregex.compile('[.,:;()«»—–-]|і|й|та')
_NOUN_P_V_ROD2 = jregex.compile('noun.*:p:v_rod.*')
_SOMA = jregex.compile('сьома|дев.яноста')
_NOUN_ADJ_FP_V_NAZ = jregex.compile('(noun:.*?|adj):[fp]:v_naz.*')


def is_exception(tokens, state, numr_inflections, slave_inflections, slave_token_readings):
    """TokenAgreementNumrNounExceptionHelper.isException"""
    n = len(tokens)
    numr_token_lower = state.numr_analyzed_token_readings.get_clean_token().lower()
    noun_atr = tokens[state.noun_pos]

    # для багатьох несподіванкою стало
    if _EXC_NUMR.fullmatch(numr_token_lower):
        return True

    noun_lower_token = noun_atr.get_clean_token().lower()
    # |десятих|сотих|тисячних - done in main rule
    if _EXC_NOUN.fullmatch(noun_lower_token):
        return True

    # рази може у два більший
    if lh.has_lemma(noun_atr, _EXC_LEMMA):
        return True

    # хвилин п'ять люди
    # сотні дві персон
    if state.numr_pos > 1 and lh.has_lemma_pos(tokens[state.numr_pos - 1], lh.TIME_PLUS_LEMMAS, _NOUN_V_NAZ_ROD):
        noun_inflections = lh.get_noun_inflections(tokens[state.numr_pos - 1].readings)
        if not java_disjoint(numr_inflections, noun_inflections):
            return True

    # півтора довгих роки
    if state.noun_pos < n - 1:
        if _PIVTORA_TORY.fullmatch(state.numr_analyzed_token_readings.get_clean_token()) \
                and pth.has_pos_tag(tokens[state.noun_pos], _ADJ_P_NAZ_ROD) \
                and pth.has_pos_tag(tokens[state.noun_pos + 1], _NOUN_P_V_NAZ):
            return True

    # хвилин зо п'ять люди
    if state.numr_pos > 2 and pth.has_pos_tag_start(tokens[state.numr_pos - 1], 'prep') \
            and lh.has_lemma_pos(tokens[state.numr_pos - 2], lh.TIME_PLUS_LEMMAS, _NOUN_P_V_NAZ_ROD):
        noun_inflections = lh.get_noun_inflections(tokens[state.numr_pos - 2].readings)
        if not java_disjoint(numr_inflections, noun_inflections):
            return True

    # У свої вісімдесят пан Василь
    if state.numr_pos > 2 and pth.has_pos_tag_start(tokens[state.numr_pos - 2], 'prep') \
            and tokens[state.numr_pos - 1].get_clean_token().lower() == 'свої' \
            and pth.has_pos_tag(tokens[state.numr_pos], _NUMR_P_V_ZNA) \
            and pth.has_pos_tag(tokens[state.noun_pos], _NOUN_ANIM_V_NAZ):
        return True

    # два провінційного вигляду персонажі
    if state.noun_pos <= n - 3 and pth.has_pos_tag(tokens[state.noun_pos], _ADJ_V_ROD) \
            and pth.has_pos_tag(tokens[state.noun_pos + 1], _NOUN_INANIM_V_ROD_NON_PRON) \
            and pth.has_pos_tag(tokens[state.noun_pos + 2], _NOUN_NON_PRON):
        adj1_genders = pth.get_genders(tokens[state.noun_pos], _ADJ_V_ROD)
        noun1_genders = pth.get_genders(tokens[state.noun_pos + 1], _NOUN_INANIM_V_ROD_NON_PRON)
        if jregex.compile('.*[' + noun1_genders + '].*').fullmatch(adj1_genders):
            noun_inflections = lh.get_noun_inflections(tokens[state.noun_pos + 2].readings)
            if not java_disjoint(numr_inflections, noun_inflections):
                return True

    # handled by another rule
    if numr_token_lower.endswith(',5'):
        if _TON_TYS.fullmatch(noun_lower_token) or (
                state.numr_pos > 1 and _FROM_TO.fullmatch(tokens[state.numr_pos - 1].get_clean_token().lower())):
            return True

    # обоє горбаті
    if _OBOYE.fullmatch(numr_token_lower):
        if pth.has_pos_tag_and_token(noun_atr, _ADJ_P_V_NAZ, _ENDS_I):
            return True

    # обоє режисери
    if _OBOYE2.fullmatch(numr_token_lower):
        if pth.has_pos_tag(noun_atr, _NOUN_ANIM_P_V_NAZ):
            return True

    # handled in the rule
    # 22 червня
    if state.number and lh.has_lemma_part_pos(tokens[state.noun_pos], lh.MONTH_LEMMAS, ':m:v_rod'):
        return True

    # 3 / 4 понеділка
    if state.numr_pos > 2:
        if tokens[state.numr_pos - 1].get_clean_token() == '/':
            return True

    if state.numr_pos > 1 and (lh.has_lemma(tokens[state.numr_pos - 1], _ARTICLE_LEMMAS)
                               or tokens[state.numr_pos - 1].get_clean_token() == '№'):
        return True

    # двадцять перший; дві соті
    if pth.has_pos_tag(noun_atr, _ADJ_NUMR):
        return True

    if DVA_3_4_PATTERN.fullmatch(numr_token_lower) or state.number:
        # два нових горнятка
        # три вихідних
        if pth.has_pos_tag(tokens[state.noun_pos], _ADJ_NON_NUMR_P_V_ROD) and (
                state.noun_pos == n - 1
                or pth.has_pos_tag(tokens[state.noun_pos + 1], _NEXT_OK)
                or not pth.has_pos_tag(tokens[state.noun_pos + 1], _ADJ_OR_NOUN)
                or _NEXT_PUNCT.fullmatch(tokens[state.noun_pos + 1].get_clean_token())):
            return True
        # 2 хворих/злотих...
        if tokens[state.noun_pos].get_clean_token().lower().endswith('их') \
                and pth.has_pos_tag(tokens[state.noun_pos], _NOUN_P_V_ROD2):
            return True

    # сьома вода
    if _SOMA.fullmatch(numr_token_lower):
        if pth.has_pos_tag(noun_atr, _NOUN_ADJ_FP_V_NAZ):
            return True

    return False
