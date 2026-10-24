"""Port of org.languagetool.rules.uk.TokenAgreementVerbNounRule and
TokenAgreementVerbNounExceptionHelper."""

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import is_upper_case
from . import helpers as lh
from . import pos_tag_helper as pth
from .agreement_noun_verb import has_masc_fem_lemma, has_vidm_pos_tag
from .helpers import Condition, Match, RuleException

_C = jregex.compile


def format_adj_noun_inflections(inflections, adj):
    """TokenAgreementAdjNounRule.formatInflections (sorts the list)"""
    inflections.sort(key=lambda x: x.sort_key())
    groups = {}
    for infl in inflections:
        case_str = pth.VIDMINKY_MAP.get(infl.case)
        if adj and infl.anim_tag is not None:
            case_str += ' (' + ('іст.' if infl.anim_tag == 'anim' else 'неіст.') + ')'
        groups.setdefault(infl.gender, []).append(case_str)
    return ', '.join('%s: %s' % (pth.GENDER_MAP.get(g), ', '.join(v)) for g, v in groups.items())


# --- TokenAgreementVerbNounExceptionHelper ---

_VCHYTY_PATTERN = _C('.*вч[аи]ти(ся)?')
_ADV_PREDICT_PATTERN = _C('(adv|noninfl:predic).*')
_MODALS_ADJ = _C('змушений|вимушений|повинний|здатний|готовий|ладний|радий')
_V_ROD_DRIVER_PATTERN = _C('не|(на)?с[кт]ільки|(най)?більше|(най)?менше|(не|за)?багато|(не|чи|за)?мало|трохи|годі'
                           '|неможливо|а?ніж|вдосталь|купу', jregex.IGNORECASE)
_LAT = _C('[a-z].*')

_P_NUMR_NAZ = _C('numr.*v_naz.*')
_P_QUANT_TAG = _C('noun.*v_naz.*|adv.*|part.*')
_P_SN = _C('.*:[sn](:.*|$)')
_P_VERB_INF = _C('verb.*inf.*')
_P_BUTY_MUSYTY = _C('бути|мусити')
_P_PAST_N_S3 = _C('verb.*(past:n|:s:3).*')
_P_ADJ_NAZ = _C('adj:.:v_naz.*')
_P_MOHTY = _C('з?могти')
_P_VIDOMO = _C('відомо|видно|зрозуміло')
_P_BILSHE = _C('(най)?(більше|менше)')
_P_ROD = _C('.*:v_rod.*')
_P_VERB = _C('verb.*')
_P_NOUN_ZNA = _C('noun:inanim:.:v_zna.*|adj:.:v_zna(?!:ranim).*')
_P_MATY = _C('мати|маючи|мавши')
_P_BUTY = _C('бути')
_P_S3_PAST_N = _C('verb.*(:s:3|past:n).*')
_P_BUL = _C('би?')
_P_BYLO_BUDE = _C('було|буде')
_P_ZAIVE = _C('зайве|резон')
_P_ROD2 = _C('.*v_rod.*')
_P_ZNA = _C('.*v_zna.*')
_P_PREDIC = _C('.*predic.*')
_P_TREBA = _C('треба|потрібно')
_P_LYUDYNA = _C('людина|знаменитість')
_P_LYUDYNA2 = _C('людина')
_P_S3_PAST_M = _C('verb.*(:s:3|past:m).*')
_P_NUM = _C('num.*')
_P_ADV_NON_P = _C('adv(?!p).*')
_P_NUMERIC_DASH = _C('[0-9]+-.+|дорогою|толком|дивом|чверть|третину|половину|святая')
_P_ADJ_FN_ZNA_ORU = _C('adj:[fn]:v_(zna|oru).*')
_P_DOROHA_TAG = _C('noun:inanim:[fn]:v_(zna|oru).*')
_P_ORU = _C('.*v_oru.*')
_P_NAZ = _C('.*v_naz.*')
_P_TRYVATY_TAG = _C('(adj|numr|noun:inanim).*v_zna.*')
_P_NUMR_ZNA = _C('numr.*?v_zna.*|noun.*v_zna.*numr.*')
_P_NOUN_ADJ_ROD = _C('(noun|adj):.*:v_rod.*')
_P_NOUN_INANIM_ADJ_ROD = _C('(noun:inanim|adj):.:v_rod.*')
_P_NA = _C('на')
_P_NOUN_ROD_ZNA = _C('noun.*v_(rod|zna).*')
_P_NA_Z = _C('на|з|із|зо|під')
_P_NUMBER_NUMR_ZNA = _C('number|numr.*v_zna.*')
_P_NIKOLY = _C('ніколи|нікуди|нічого|нічим|ніде|немає?|не')
_P_NIKOLY2 = _C('ніколи|нікуди|нічого|нічим|ніде|де|немає?|не')
_P_NE_ANI = _C('не|а?ні')
_P_SLID = _C('слід|снаги|силу')
_P_PREPS = _C('в|у|на|від|під|по|до|і?з|з[іо]|над|з-під|перед|попід|поза|напереріз')
_P_NOUN_ADJ = _C('(noun|adj).*')
_P_DAV = _C('.*v_dav.*')
_P_NAZUSTRICH = _C('назустріч|навперейми|навздогін|услід')
_P_DAV_PRON = _C('noun.*?v_dav.*:pron:(pers|refl).*')
_P_TIME_SKIP = _C('.*v_(rod|zna|oru).*|part.*|number')
_P_NUMR_ZNA2 = _C('numr.*v_zna.*')
_P_MOVA_SKIP = _C('.*v_oru.*|part.*|adv.*')
_P_MOVA = _C('мова')
_P_MOVA_TAG = _C('noun:inanim:.:v_oru.*')
_P_VERB_F = _C('verb.*:f(:.*|$)')
_P_VERB_FUTR_PAST = _C('verb.*?(futr|past):(s:3.*|n($|:.+))')
_P_MENSHATY = _C('(по)?меншати|(по)?більшати|стати')
_P_VERB_SN = _C('verb.*:[sn](:.*|$)')
_P_NOUN_ADJ_ROD2 = _C('(noun|adj).*v_rod.*')
_P_NOUN_ROD = _C('noun:.*v_rod.*')
_P_MENSHE = _C('менше|більше|удвічі|утричі')
_P_ZMOZI = _C('змозі|змогу|силі|силах')
_P_NOUN_ADJ_NAZ = _C('(noun|adj).*v_naz.*')
_P_NOUN_ADJ_NUMR_NAZ = _C('(noun|adj|numr).*v_naz.*')
_P_PREDIC2 = _C('noninfl:predic.*')
_P_VERB_P = _C('verb.*:p($|:.*)')
_P_YISTY = _C('(по)?їсти')
_P_ADJ_NAZ2 = _C('adj:.:v_naz.*')
_P_VERB_P2 = _C('verb.*:p(:.*)?')
_P_ADJ_ROD_NON_PRON = _C('adj:.:v_rod(?!.*pron).*')
_P_NOUN_ROD_NON_PRON = _C('noun:.*v_rod(?!.*pron).*')
_P_NOUN_ADJ_NON_PRON = _C('(noun|adj)(?!.*pron).*')
_P_VCHYTY = _C('.*вчити(ся)?')
_P_COMP = _C('(adv:comp[cs].*|.*predic.*)')
_P_PERF = _C('adj:.:v_naz.*:adjp:.*:perf.*')


def _agrees(verb_token_readings, noun_adj_naz_inflections, noun_adj_indir_token_readings):
    if noun_adj_naz_inflections:
        verb_inflections = lh.get_verb_inflections(verb_token_readings.readings)
        if not lh.java_disjoint(verb_inflections, noun_adj_naz_inflections):
            return True
    if noun_adj_indir_token_readings:
        cases = lh.get_case_governments(verb_token_readings, pth.VERB_ADVP_PATTERN)
        if len(cases) > 0 and has_vidm_pos_tag(cases, noun_adj_indir_token_readings):
            return True
    return False


def _genders_overlap(genders1, genders2):
    """genders1.matches(".*[" + genders2 + "].*")"""
    return any(c in genders1 for c in genders2)


def is_exception(tokens, state, verb_inflections, noun_adj_inflections, verb_token_readings, noun_token_readings):
    """TokenAgreementVerbNounExceptionHelper.isException"""
    verb_pos = state.verb_pos
    noun_adj_pos = state.noun_pos
    n = len(tokens)

    def low(i):
        return tokens[i].get_clean_token().lower()

    clean_token_lower = low(noun_adj_pos)

    # боротиметься кілька однопартійців
    # входило двоє студентів
    if pth.has_pos_tag(tokens[noun_adj_pos], _P_NUMR_NAZ) \
            or lh.has_lemma_pos(tokens[noun_adj_pos], lh.ADV_QUANT_PATTERN, _P_QUANT_TAG):
        if pth.has_pos_tag(state.verb_analyzed_token_readings, _P_SN):
            return True
        # буде лежати двоє хворих
        if verb_pos > 1 and pth.has_pos_tag(state.verb_analyzed_token_readings, _P_VERB_INF) \
                and lh.has_lemma_pos(tokens[verb_pos - 1], _P_BUTY_MUSYTY, _P_PAST_N_S3):
            return True

    # була марки Ford
    if noun_adj_pos < n - 1 and lh.has_lemma(tokens[verb_pos], 'бути') and low(noun_adj_pos) == 'марки':
        return True

    if verb_pos > 1 and lh.has_lemma(tokens[verb_pos], 'бути'):
        # здатна була
        if lh.has_lemma_pos(tokens[verb_pos - 1], _MODALS_ADJ, _P_ADJ_NAZ):
            return True

    # TODO: temp: коли зможе силою розуму освоїти
    if lh.has_lemma(tokens[verb_pos], _P_MOHTY) and pth.has_pos_tag(tokens[noun_adj_pos], '.*v_oru.*'):
        return True

    # глузували тим більше, чим...
    if noun_adj_pos < n - 2 and low(noun_adj_pos) == 'тим' and low(noun_adj_pos + 1) == 'більше':
        return True
    # чим могла
    if verb_pos > 1 and lh.has_lemma(tokens[verb_pos], _P_MOHTY) and low(verb_pos - 1) == 'чим':
        return True

    # стало відомо ...
    if low(verb_pos) == 'стало' and _P_VIDOMO.fullmatch(low(verb_pos + 1)):
        return True

    # вони мали більше прав
    if state.noun_pos == verb_pos + 2 and lh.has_lemma(tokens[verb_pos + 1], _P_BILSHE) \
            and pth.has_pos_tag(tokens[noun_adj_pos], _P_ROD) \
            and lh.has_case_government(tokens[verb_pos], _P_VERB, 'v_zna'):
        return True

    # я буду каву
    if verb_pos > 1 and low(verb_pos - 1) == 'я' and low(verb_pos) == 'буду' \
            and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_ZNA):
        return True

    # хоче маляром
    if lh.has_lemma(tokens[verb_pos], 'хотіти') and pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_oru'):
        return True

    # має своїм неодмінним наслідком
    if lh.has_lemma(tokens[verb_pos], _P_MATY) and pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_oru'):
        return True

    # були б іншої думки/такого змісту
    if lh.has_lemma(tokens[verb_pos], _P_BUTY) and pth.has_pos_tag(tokens[noun_adj_pos], '(adj|numr).*v_rod.*'):
        return True

    # що є сил
    if verb_pos > 1 and low(verb_pos - 1) == 'що' and lh.has_lemma_pos(tokens[verb_pos], _P_BUTY, _P_S3_PAST_N) \
            and pth.has_pos_tag(tokens[noun_adj_pos], '(adj|noun).*v_rod.*'):
        return True

    # навіщо було город городити
    if verb_pos > 1 and low(verb_pos) == 'було' and low(verb_pos - 1) == 'навіщо':
        return True

    # чесніше було б державний фонд
    if verb_pos > 1 and low(verb_pos) == 'було' and pth.has_pos_tag(tokens[verb_pos - 1], _P_COMP):
        return True

    if verb_pos > 2 and low(verb_pos) == 'було' and _P_BUL.fullmatch(low(verb_pos - 1)) \
            and pth.has_pos_tag(tokens[verb_pos - 2], _P_COMP):
        return True

    # квітне притухлий було пафос
    if verb_pos > 1 and low(verb_pos) == 'було' and pth.has_pos_tag(tokens[noun_adj_pos], _P_NAZ) \
            and pth.has_pos_tag(tokens[verb_pos - 1], _P_PERF):
        return True

    # підстрахуватися не зайве
    if _P_ZAIVE.fullmatch(clean_token_lower):
        return True

    # навіщо було город городити
    if low(noun_adj_pos - 1) == 'далі' and pth.has_pos_tag(tokens[noun_adj_pos], _P_ROD2):
        return True

    # було всі 90-ті
    if _P_BYLO_BUDE.fullmatch(low(verb_pos)) and lh.has_lemma_pos(tokens[noun_adj_pos], ('весь',), _P_ZNA):
        return True

    # буде видно тільки супутники
    if _P_BYLO_BUDE.fullmatch(low(verb_pos)) \
            and Match().target(Condition.postag(_P_PREDIC)).limit(noun_adj_pos - verb_pos) \
            .m_after(tokens, verb_pos + 1) >= 0:
        return True

    # потрібно буде ше склянку
    if _P_BYLO_BUDE.fullmatch(low(verb_pos)) \
            and Match().target(Condition.lemma(_P_TREBA)).m_now(tokens, verb_pos - 1) >= 0:
        return True

    # він був талановита людина
    if low(verb_pos) == 'був':
        if _P_LYUDYNA.fullmatch(low(noun_adj_pos)):
            return True
        if noun_adj_pos < n - 1 and _P_LYUDYNA2.fullmatch(low(noun_adj_pos + 1)):
            return True

    # Конкурс був десь шість
    if verb_pos > 1 and low(verb_pos - 1) == 'конкурс' \
            and lh.has_lemma_pos(tokens[verb_pos], _P_BUTY, _P_S3_PAST_M) \
            and pth.has_pos_tag(tokens[noun_adj_pos], _P_NUM):
        return True

    # розподілятиметься пропорційно вкладеній праці
    if noun_adj_pos - verb_pos > 1:
        adv_req = lh.get_case_governments(tokens[noun_adj_pos - 1], _P_ADV_NON_P)
        if len(adv_req) > 0:
            for ii in range(verb_pos + 1, noun_adj_pos):
                if has_vidm_pos_tag(adv_req, tokens[ii]):
                    return True

    if clean_token_lower in lh.PLUS_MINUS:
        return True

    # закінчилося 18-го ввечері
    # наслухатися дорогою
    if _P_NUMERIC_DASH.fullmatch(clean_token_lower):
        return True

    # сміялася всю дорогу/цілою дорогою
    if noun_adj_pos < n - 1 and pth.has_pos_tag(tokens[noun_adj_pos], _P_ADJ_FN_ZNA_ORU) \
            and lh.has_lemma_pos(tokens[noun_adj_pos + 1], ('дорога', 'життя', 'міра'), _P_DOROHA_TAG):
        return True

    # запропоновано відділом
    if pth.has_pos_tag_part(tokens[verb_pos], 'impers') and pth.has_pos_tag(tokens[noun_adj_pos], _P_ORU):
        return True

    # займаючись кожен своїми справами
    if lh.has_lemma_pos(tokens[noun_adj_pos], ('кожний',), _P_NAZ):
        return True

    # звалося Подєбради
    if lh.has_lemma(tokens[verb_pos], ('звати', 'називати', 'зватися', 'називатися')) \
            and is_upper_case(tokens[noun_adj_pos].get_clean_token()[0]):
        return True

    # тривав довгих десять раундів.
    if lh.has_lemma(tokens[verb_pos], ('тривати', 'протривати', 'йти', 'іти', 'ходити', 'їхати')) \
            and pth.has_pos_tag(tokens[noun_adj_pos], _P_TRYVATY_TAG):
        return True

    # ні сіло ні впало
    if verb_pos > 3 and low(verb_pos) == 'впало' and tokens[verb_pos - 1].get_clean_token() == 'ні':
        return True
    # звичайна, якщо не сказати слабка, людина
    if verb_pos > 2 and low(verb_pos) == 'сказати' and tokens[verb_pos - 1].get_clean_token() == 'не' \
            and pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_naz'):
        return True

    # потребувала мільйон
    if 'v_rod' in state.cases and pth.has_pos_tag(tokens[noun_adj_pos], _P_NUMR_ZNA):
        return True

    # виростили сортів 10
    if noun_adj_pos < n - 1 and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_ADJ_ROD) \
            and pth.has_pos_tag(tokens[noun_adj_pos + 1], _P_NUM):
        return True

    # виростили сортів — 10
    if noun_adj_pos < n - 2 and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_ADJ_ROD) \
            and lh.is_dash(tokens[noun_adj_pos + 1]) and pth.has_pos_tag(tokens[noun_adj_pos + 2], _P_NUM):
        return True

    # одержав хабарів на суму 10
    if noun_adj_pos < n - 2 and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_INANIM_ADJ_ROD):
        v2pos = lh.token_search(tokens, state.noun_pos + 1, None, _P_NA, _LAT, lh.FORWARD)
        if 0 <= v2pos <= state.noun_pos + 5 and v2pos < n - 1:
            return True

    # залучити інвестицій на 20—30
    if noun_adj_pos < n - 2 and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_ROD_ZNA) \
            and _P_NA_Z.fullmatch(tokens[noun_adj_pos + 1].get_clean_token()) \
            and pth.has_pos_tag(tokens[noun_adj_pos + 2], _P_NUMBER_NUMR_ZNA):
        return True

    # V_DAV
    if pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_dav'):
        # INF + V_DAV
        if pth.has_pos_tag_part(tokens[verb_pos], ':inf'):
            # як боротися підприємцям
            if verb_pos > 1 and lh.has_lemma(tokens[verb_pos - 1], ('як', 'куди', 'де', 'що', 'чого', 'чи')):
                return True
            # Квапитися їй нікуди
            if noun_adj_pos < n - 1 and _P_NIKOLY.fullmatch(low(noun_adj_pos + 1)):
                return True
            # тут жити мешканцям було б добре
            if lh.has_lemma(tokens[verb_pos], ('жити', 'сидіти', 'судити')):
                return True
            # нічим пишатися селянам
            if verb_pos > 1 and _P_NIKOLY2.fullmatch(low(verb_pos - 1)):
                return True
            # не бачити вам цирку
            if verb_pos > 1 and noun_adj_pos < n - 1 and _P_NE_ANI.fullmatch(low(verb_pos - 1)) \
                    and pth.has_pos_tag_part(tokens[noun_adj_pos + 1], 'v_rod'):
                return True
            # слід проходити людям
            if verb_pos > 1 and _P_SLID.fullmatch(low(verb_pos - 1)):
                return True

        # розсміявся брату в обличчя
        if noun_adj_pos < n - 2 and _P_PREPS.fullmatch(low(noun_adj_pos + 1)) \
                and pth.has_pos_tag(tokens[noun_adj_pos + 2], _P_NOUN_ADJ):
            return True
        if noun_adj_pos < n - 1 and pth.has_pos_tag(tokens[noun_adj_pos], _P_DAV) \
                and _P_NAZUSTRICH.fullmatch(low(noun_adj_pos + 1)):
            return True

        # закружляли мені десь у тьмі
        if noun_adj_pos < n - 2 and pth.has_pos_tag(tokens[noun_adj_pos], _P_DAV_PRON):
            return True

    # сміятися гріх
    if pth.has_pos_tag_part(tokens[verb_pos], ':inf') and low(noun_adj_pos) == 'гріх':
        return True

    # відбувається кожні два роки
    # розпочнеться того ж дня
    if Match().skip(Condition.postag(_P_TIME_SKIP)).target(Condition.lemma(lh.TIME_PLUS_LEMMAS_PATTERN)) \
            .limit(4).m_after(tokens, noun_adj_pos) > 0:
        return True

    # йде три з половиною години
    if noun_adj_pos < n - 3 and pth.has_pos_tag(tokens[noun_adj_pos], _P_NUMR_ZNA2) \
            and Match().target(Condition.lemma(lh.TIME_PLUS_LEMMAS_PATTERN)).limit(4) \
            .m_after(tokens, noun_adj_pos + 1) > 0:
        return True

    if Match().skip(Condition.postag(_P_MOVA_SKIP)).target(Condition(_P_MOVA, _P_MOVA_TAG)).limit(4) \
            .m_after(tokens, noun_adj_pos) > 0:
        return True

    # став жовтого кольору
    if noun_adj_pos < n - 1 and low(noun_adj_pos + 1) == 'кольору' \
            and pth.has_pos_tag_start(tokens[noun_adj_pos], 'adj:m:v_rod'):
        return True

    # дай Боже
    if pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_kly') and pth.has_pos_tag_part(tokens[verb_pos], 'impr'):
        return True

    # повторила прем’єр-міністр у телезверненні
    if pth.has_pos_tag_part(noun_token_readings, 'noun:anim:m:v_naz') \
            and pth.has_pos_tag(verb_token_readings, _P_VERB_F) and has_masc_fem_lemma(noun_token_readings):
        return True

    # не існувало конкуренції
    # не було мізків
    # стане сили
    if pth.has_pos_tag_part(tokens[state.noun_pos], 'v_rod') \
            and pth.has_pos_tag(state.verb_token_readings, _P_VERB_FUTR_PAST):
        return True

    # меншає людей
    if lh.has_lemma_pos(state.verb_analyzed_token_readings, _P_MENSHATY, _P_VERB_SN) \
            and pth.has_pos_tag(tokens[state.noun_pos], _P_NOUN_ADJ_ROD2):
        return True

    # споживає газу менше
    if noun_adj_pos < n - 1 and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_ROD) \
            and _P_MENSHE.fullmatch(tokens[noun_adj_pos + 1].get_clean_token()):
        return True

    # небагато надходить книжок
    # трохи зменшується матерії
    if state.verb_pos > 1 and pth.has_pos_tag_part(tokens[state.noun_pos], 'v_rod'):
        xpos = lh.token_search(tokens, state.verb_pos - 1, None, _V_ROD_DRIVER_PATTERN, _LAT, lh.REVERSE)
        if xpos >= 0 and xpos >= state.verb_pos - 4:
            return True

    # V + N + V:INF
    # вміємо цим зазвичай користуватися
    if noun_adj_pos < n - 1 \
            and lh.has_case_government(state.verb_analyzed_token_readings, pth.VERB_ADVP_PATTERN, 'v_inf'):
        v2pos = lh.token_search(tokens, state.noun_pos + 1, pth.VERB_PATTERN, None, _LAT, lh.FORWARD)
        if 0 <= v2pos <= state.noun_pos + 5 \
                and _agrees(tokens[v2pos], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
            return True

    # V:INF + N + V
    # працювати ці люди не вміють
    # робити прогнозів не буду
    if noun_adj_pos < n - 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf'):
        v2pos = lh.token_search(tokens, state.noun_pos + 1, pth.VERB_PATTERN, None, _LAT, lh.FORWARD)
        if 0 <= v2pos <= state.noun_pos + 4 and lh.has_case_government(tokens[v2pos], pth.VERB_PATTERN, 'v_inf'):
            if _agrees(tokens[v2pos], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
                return True
            if tokens[v2pos - 1].get_clean_token() == 'не':
                return True

    # ADVP + N + V
    # резюмуючи політик наголосив
    if noun_adj_pos < n - 1 and pth.has_pos_tag_start(tokens[verb_pos], 'advp'):
        v2pos = lh.token_search(tokens, state.noun_pos + 1, pth.VERB_PATTERN, None, _LAT, lh.FORWARD)
        if 0 <= v2pos <= state.noun_pos + 3:
            if _agrees(tokens[v2pos], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
                return True

    # V + ADVP + N
    # пригадує посміхаючись Аскольд - only: сміючись, посміхаючись; if more generic hides TP
    if verb_pos > 1 and pth.has_pos_tag_start(tokens[verb_pos], 'advp') \
            and tokens[verb_pos].get_clean_token() in ('посміхаючись', 'сміючись') \
            and pth.has_pos_tag_start(tokens[verb_pos - 1], 'verb'):
        if _agrees(tokens[verb_pos - 1], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
            return True

    # V:INF + N + ADV
    # розібратися людям важко
    if noun_adj_pos < n - 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf'):
        if not lh.has_lemma(tokens[verb_pos], _VCHYTY_PATTERN):
            v2pos = lh.token_search(tokens, state.noun_pos + 1, _ADV_PREDICT_PATTERN, None, _LAT, lh.FORWARD)
            while 0 <= v2pos <= state.noun_pos + 4:
                cases = lh.get_case_governments(tokens[v2pos], _ADV_PREDICT_PATTERN)
                if has_vidm_pos_tag(cases, state.noun_adj_indir_token_readings):
                    return True
                v2pos = lh.token_search(tokens, v2pos + 1, _ADV_PREDICT_PATTERN, None, _LAT, lh.FORWARD)

    # V:INF + N + ADJ
    # працювати студенти готові
    if noun_adj_pos < n - 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf'):
        v2pos = lh.token_search(tokens, state.noun_pos + 1, pth.ADJ_V_NAZ_PATTERN, None, _LAT, lh.FORWARD)
        if 0 <= v2pos <= state.noun_pos + 3:
            if lh.has_case_government(tokens[v2pos], pth.ADJ_V_NAZ_PATTERN, 'v_inf'):
                genders1 = pth.get_genders(tokens[noun_adj_pos], _P_NOUN_ADJ_NAZ)
                genders2 = pth.get_genders(tokens[v2pos], pth.ADJ_V_NAZ_PATTERN)
                if _genders_overlap(genders1, genders2):
                    return True

    # V:INF + ADJ
    # працювати неспроможні
    if pth.has_pos_tag_part(tokens[verb_pos], ':inf') \
            and pth.has_pos_tag(tokens[noun_adj_pos], pth.ADJ_V_NAZ_PATTERN):
        if lh.has_case_government(tokens[noun_adj_pos], pth.ADJ_V_NAZ_PATTERN, 'v_inf'):
            return True

    # V + V:INF + N
    # дають (змогу з комфортом) мандрувати чотирьом пасажирам
    # заважають розвиватися погане управління, війна
    if verb_pos > 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf'):
        lookup_pos = state.verb_pos - 1
        # перестають діяти й розвиватися демократичні
        if verb_pos > 3:
            if lh.has_lemma(tokens[verb_pos - 1], ('і', 'й', 'та')) \
                    and pth.has_pos_tag_part(tokens[verb_pos - 2], ':inf'):
                lookup_pos = verb_pos - 3
        v2pos = lh.token_search(tokens, lookup_pos, pth.VERB_ADVP_PATTERN, None, _LAT, lh.REVERSE)
        if v2pos >= 0 and v2pos >= state.verb_pos - 5 \
                and (lh.has_case_government(tokens[v2pos], pth.VERB_ADVP_PATTERN, 'v_inf')
                     or _P_YISTY.fullmatch(tokens[verb_pos].get_clean_token())):
            if _agrees(tokens[v2pos], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
                return True
            # заважають розвиватися погане управління, війна
            if pth.has_pos_tag(tokens[v2pos], _P_VERB_P) and pth.has_pos_tag(tokens[state.noun_pos], _P_NAZ):
                return True

    # ADV + V:INF + N
    # важко розібратися багатьом людям
    if verb_pos > 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf'):
        v2pos = lh.token_search(tokens, state.verb_pos - 1, _ADV_PREDICT_PATTERN, None, _LAT, lh.REVERSE)
        while v2pos >= 0 and v2pos >= state.verb_pos - 3:
            if pth.has_pos_tag(tokens[v2pos], _P_PREDIC2) and pth.has_pos_tag_part(tokens[state.noun_pos], 'v_naz'):
                return True
            cases = lh.get_case_governments(tokens[v2pos], _ADV_PREDICT_PATTERN)
            if has_vidm_pos_tag(cases, state.noun_adj_indir_token_readings):
                return True
            v2pos = lh.token_search(tokens, v2pos - 1, _ADV_PREDICT_PATTERN, None, _LAT, lh.REVERSE)

    # ADJ + V:INF + N
    # зацікавлена перейняти угорська сторона
    if verb_pos > 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf') \
            and pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_naz'):
        # не в змозі приховати офіційна статистика
        if _P_ZMOZI.fullmatch(low(verb_pos - 1)):  # але "під силу" + v_dav
            return True
        v2pos = lh.token_search(tokens, state.verb_pos - 1, pth.ADJ_V_NAZ_PATTERN, None, _LAT, lh.REVERSE)
        if v2pos >= 0 and v2pos >= state.verb_pos - 3:
            if lh.has_case_government(tokens[v2pos], pth.ADJ_V_NAZ_PATTERN, 'v_inf'):
                genders1 = pth.get_genders(tokens[noun_adj_pos], _P_NOUN_ADJ_NUMR_NAZ)
                genders2 = pth.get_genders(tokens[v2pos], pth.ADJ_V_NAZ_PATTERN)
                if _genders_overlap(genders1, genders2):
                    return True

    # ADJ + бути + N
    if verb_pos > 1 and lh.has_lemma(tokens[verb_pos], 'бути') \
            and pth.has_pos_tag(tokens[verb_pos - 1], 'adj:.:v_naz.*') \
            and lh.has_case_government(tokens[verb_pos - 1], 'v_rod') \
            and pth.has_pos_tag(tokens[noun_adj_pos], _P_NOUN_ADJ_ROD2):
        return True

    # V:IMPERS + бути + N
    if verb_pos > 1 and lh.has_lemma(tokens[verb_pos], 'бути') \
            and pth.has_pos_tag(tokens[verb_pos - 1], 'verb.*impers.*') \
            and _agrees(tokens[verb_pos - 1], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
        return True

    # NOUN + V:INF + N
    # гріх зайнятися Генеральній прокуратурі
    # готовність спілкуватися людини
    # небажання вибачатися пов’язане з
    if verb_pos > 1 and pth.has_pos_tag_part(tokens[verb_pos], ':inf') \
            and (pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_dav')
                 or pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_rod')
                 or pth.has_pos_tag(tokens[noun_adj_pos], _P_ADJ_NAZ2)):
        v2pos = lh.token_search(tokens, state.verb_pos - 1, pth.NOUN_V_NAZ_PATTERN, None, _LAT, lh.REVERSE)
        if v2pos >= 0 and v2pos >= state.verb_pos - 3:
            if lh.has_case_government(tokens[v2pos], pth.NOUN_V_NAZ_PATTERN, 'v_inf'):
                # exc: бажання вчитися новому
                if pth.has_pos_tag_part(tokens[noun_adj_pos], 'v_dav') \
                        and lh.has_lemma(tokens[verb_pos], _P_VCHYTY):
                    return False
                return True

    # V:INF + V + N
    # платити доведеться повну вартість
    if verb_pos > 1 \
            and lh.has_case_government(state.verb_analyzed_token_readings, pth.VERB_PATTERN, 'v_inf'):
        v2pos = lh.token_search(tokens, state.verb_pos - 1, pth.VERB_PATTERN, None, _LAT, lh.REVERSE)
        if v2pos >= 0 and v2pos >= state.verb_pos - 3 and pth.has_pos_tag_part(tokens[v2pos], ':inf') \
                and _agrees(tokens[v2pos], state.noun_adj_naz_inflections, state.noun_adj_indir_token_readings):
            return True

    # в мені наростали впевеність і ...
    if noun_adj_pos < n - 2 and pth.has_pos_tag(tokens[verb_pos], _P_VERB_P2) \
            and pth.has_pos_tag_part(tokens[noun_adj_pos], ':v_naz'):
        return True

    # змалював дивовижної краси церкву
    if noun_adj_pos < n - 2 and pth.has_pos_tag(tokens[noun_adj_pos], _P_ADJ_ROD_NON_PRON) \
            and pth.has_pos_tag(tokens[noun_adj_pos + 1], _P_NOUN_ROD_NON_PRON) \
            and pth.has_pos_tag(tokens[noun_adj_pos + 2], _P_NOUN_ADJ_NON_PRON):
        readings = tokens[noun_adj_pos + 2].readings
        readings_vnaz = [r for r in readings if pth.has_pos_tag_part(r, 'v_naz')]
        infl_vnaz = lh.get_verb_noun_inflections(readings_vnaz)
        infl_vnaz.extend(lh.get_verb_adj_inflections(readings_vnaz))
        readings_indir = [r for r in readings if not pth.has_pos_tag_part(r, 'v_naz')]
        if _agrees(tokens[verb_pos], infl_vnaz, readings_indir):
            return True

    # могли б займатися структури
    # має також народитися власна ідея
    # мали змогу оцінити відвідувачі
    if verb_pos > 2 and pth.has_pos_tag_part(tokens[verb_pos], ':inf') \
            and pth.has_pos_tag_start(tokens[verb_pos - 2], 'verb') \
            and (lh.has_lemma(tokens[verb_pos - 1], ('б', 'би'))
                 or pth.has_pos_tag(tokens[verb_pos - 1], _P_ADV_NON_P)
                 or lh.has_lemma_part_pos(tokens[verb_pos - 2], ('мати',), 'verb')):
        return True

    return False


_P_HARD1 = _C('[0-9]{4}-.+|нікому|нічому|нічого|нікого|нічим|решту|ніщо')
_P_ADJ_M_ROD = _C('adj:m:v_rod.*')
_P_RODU = _C('роду|разу|типу|штибу|розміру')
_P_ADJ_NUMR_MP_ORU = _C('(adj|numr):[mp]:v_oru.*')
_P_CHYNOM = _C('чином|способом|робом|ходом|шляхом|коштом')
_P_ADJ_F_ORU = _C('adj:f:v_oru.*')
_P_MIROYU = _C('мірою')
_P_ADJ_F_ROD = _C('adj:f:v_rod.*')
_P_YAKOSTI = _C('якості|свіжості')
_P_TEMPAMY = _C('темпами')
_P_UKAZ = _C('указ|варіант|рідкість')


def is_exception_hard_adj_noun(tokens, i, state):
    """TokenAgreementVerbNounExceptionHelper.isExceptionHardAdjNoun"""
    n = len(tokens)
    clean_token_lower = tokens[i].get_clean_token().lower()
    if _P_HARD1.fullmatch(clean_token_lower):
        return 1
    if lh.has_lemma(tokens[i], ('сам', 'самий', 'себе', 'один')):
        return 1
    # висміювати такого роду забобони
    if i < n - 1 and pth.has_pos_tag(tokens[i], _P_ADJ_M_ROD) \
            and _P_RODU.fullmatch(tokens[i + 1].get_clean_token()):
        return 1
    if i < n - 1 and pth.has_pos_tag(tokens[i], _P_ADJ_NUMR_MP_ORU) \
            and _P_CHYNOM.fullmatch(tokens[i + 1].get_clean_token()):
        return 1
    # уникнувши тим самим
    if i < n - 1 and pth.has_pos_tag_start(state.verb_token_readings, 'advp') \
            and tokens[i].get_clean_token().lower() == 'тим' and tokens[i + 1].get_clean_token().lower() == 'самим':
        return 1
    if i < n - 1 and pth.has_pos_tag(tokens[i], _P_ADJ_F_ORU) and _P_MIROYU.fullmatch(tokens[i + 1].get_clean_token()):
        return 1
    if i < n - 1 and pth.has_pos_tag(tokens[i], _P_ADJ_F_ROD) and _P_YAKOSTI.fullmatch(tokens[i + 1].get_clean_token()):
        return 1
    if i < n - 1 and _P_TEMPAMY.fullmatch(tokens[i + 1].get_clean_token().lower()):
        return 1

    if Match().token_line('не те щоб').m_now(tokens, i) == i + 2 \
            or Match().token_line('не те що').m_now(tokens, i) == i + 2 \
            or Match().token_line('не останньою чергою').m_now(tokens, i) == i + 2:
        return 3
    if Match().token_line('не те, що').m_now(tokens, i) == i + 3:
        return 4
    if Match().token_line('світ за очі').m_now(tokens, i) == i + 2:
        return 3
    if Match().token_line('ні світ ні').m_now(tokens, i) == i + 2:
        return 3
    if Match().token_line('куди очі').m_now(tokens, i) == i + 1:
        return 3
    if Match().token_line('станом на').m_now(tokens, i) == i + 1:
        return 3
    if Match().token_line('страх як').m_now(tokens, i) == i + 1:
        return 3
    if Match().token_line('жах як').m_now(tokens, i) == i + 1:
        return 3

    if tokens[i - 1].get_clean_token() == 'не' and _P_UKAZ.fullmatch(tokens[i].get_clean_token()):
        return 0
    return -1


_PARTS_CANT_SKIP = _C('і|й|та|чи|або|але|як|де|куди|наче|ніби|хоч|навіщо|немов|вдвічі|дедалі|щойно|наскільки')
_P_PART_ADV = _C('(part|adv).*')
_P_PART = _C('part.*')
_P_PART_CONJ_ADV = _C('(part|conj|adv).*')


def is_exception_skip(tokens, i):
    """TokenAgreementVerbNounExceptionHelper.isExceptionSkip"""
    clean_token_lower = tokens[i].get_clean_token().lower()
    if pth.has_pos_tag_all(tokens[i].readings, _P_PART_ADV) \
            and not lh.ADV_QUANT_PATTERN.fullmatch(clean_token_lower) \
            and not _PARTS_CANT_SKIP.fullmatch(clean_token_lower):
        return 0
    if pth.has_pos_tag(tokens[i].readings, _P_PART) \
            and pth.has_pos_tag_all(tokens[i].readings, _P_PART_CONJ_ADV) \
            and not _PARTS_CANT_SKIP.fullmatch(clean_token_lower):
        return 0
    return -1


_P_KLASTY = _C('(по|в)?кла(сти|вши)')
_P_BUV = _C('був|було')
_P_BULY = _C('були|було')
_P_BULA = _C('була|було')
_P_PAST_M = _C('verb.*:past:m.*')
_P_PAST_P = _C('verb.*:past:p.*')
_P_PAST_N = _C('verb.*:past:n.*')
_P_PAST_F = _C('verb.*:past:f.*')
_P_IMPERS_PREDIC = _C('verb.*(impers|predic).*')


def is_exception_verb(tokens, i, state):
    """TokenAgreementVerbNounExceptionHelper.isExceptionVerb"""
    if lh.has_lemma(tokens[i], ('мусити',)):
        return RuleException(RuleException.exception)

    clean_token_lower = tokens[i].get_clean_token().lower()
    if clean_token_lower == 'може':
        return RuleException(RuleException.exception)

    # як є
    if i > 1 and (clean_token_lower == 'є' or lh.has_lemma(tokens[i], 'могти')) \
            and tokens[i - 1].get_clean_token().lower() == 'як':
        return RuleException(RuleException.exception)

    # будь то
    if i < len(tokens) - 2 and clean_token_lower == 'будь' and tokens[i + 1].get_clean_token().lower() == 'то':
        return RuleException(RuleException.exception)

    # вкласти спати Маринку
    if 1 < i < len(tokens) - 1 and clean_token_lower == 'спати' and lh.has_lemma(tokens[i - 1], _P_KLASTY):
        return RuleException(RuleException.skip_type)

    # розпочав був
    if i > 1 and state is not None:
        if _P_BUV.fullmatch(clean_token_lower) and pth.has_pos_tag(tokens[i - 1], _P_PAST_M):
            return RuleException(0)
        if _P_BULY.fullmatch(clean_token_lower) and pth.has_pos_tag(tokens[i - 1], _P_PAST_P):
            return RuleException(0)
        if clean_token_lower == 'було' and pth.has_pos_tag(tokens[i - 1], _P_PAST_N):
            return RuleException(0)
        if _P_BULA.fullmatch(clean_token_lower) and pth.has_pos_tag(tokens[i - 1], _P_PAST_F):
            return RuleException(0)

    if i > 1 and _P_BYLO_BUDE.fullmatch(clean_token_lower):
        # чути/проголошено було
        if state is not None and pth.has_pos_tag(tokens[i - 1], _P_IMPERS_PREDIC):
            return RuleException(0)

    return RuleException(RuleException.none)


# --- TokenAgreementVerbNounRule ---

_VERB_ADVP = _C('(verb|advp).*')
_ARCH = _C('.*(arch|bad|slang|alt).*')
_ZNACHYT = _C('значить|читай|бува|здавалось|здається|здалося')
_NODASH_LEMMA = _C('.+ти(ся)?-.+ти(ся)?')
_NODASH_REPL = _C('(ти(ся)?)-.*')
_BULO = _C('було')
_IMPERS = _C('verb.*impers.*')
_HROSHEI = _C('грошей|грошенят|дров|товарів|пісень')
_PRON_ROD = _C('noun:.*v_rod.*')
_V_N = _C('(noun|adj).*')


class State:
    """TokenAgreementVerbNounRule.State"""

    def __init__(self):
        self.verb_pos = 0
        self.noun_pos = 0
        self.verb_token_readings = []
        self.verb_analyzed_token_readings = None
        self.noun_adj_naz_inflections = None
        self.cases = set()
        self.noun_adj_indir_token_readings = []


class TokenAgreementVerbNounRule(Rule):
    """A rule that checks if noun and verb agree"""

    def __init__(self, messages, language):
        super().__init__()
        self.category = Categories.get('MISC', messages)
        self.language = language

    @property
    def synthesizer(self):
        return self.language.synthesizer

    def get_id(self):
        return 'UK_VERB_NOUN_INFLECTION_AGREEMENT'

    def get_description(self):
        return 'Узгодження дієслова з іменником'

    def get_short(self):
        return 'Узгодження дієслова з іменником'

    def is_case_sensitive(self):
        return False

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        n = len(tokens)
        state = None
        i = 1
        while i < n:
            token_readings = tokens[i]
            pos_tag0 = token_readings.readings[0].pos_tag

            if pos_tag0 is None:
                state = None
                i += 1
                continue

            if state is None:
                # no need to start checking on last token or if no noun
                if i == n - 1:
                    i += 1
                    continue

            if pth.has_pos_tag(token_readings, _VERB_ADVP):
                exception = is_exception_verb(tokens, i, state)
                if exception.type != RuleException.none:
                    if exception.type == RuleException.exception:
                        state = None
                    i += exception.skip + 1
                    continue
                state = self._get_verb_state(tokens, i)
                if state is None or state.verb_pos == i:  # got the verb, move on
                    i += 1
                    continue

            if state is None:
                i += 1
                continue

            # check for noun/adj
            exception_skip = is_exception_hard_adj_noun(tokens, i, state)
            if exception_skip > -1:
                i += exception_skip + 1
                state = None
                continue

            exception_skip = is_exception_skip(tokens, i)
            if exception_skip > -1:
                i += exception_skip + 1
                continue

            noun_adj_token_readings_vnaz = []
            for token in token_readings:
                noun_adj_pos_tag = token.pos_tag
                if noun_adj_pos_tag is None or noun_adj_pos_tag.endswith('_END'):
                    continue
                if noun_adj_pos_tag.startswith('<'):
                    state = None
                    break
                if noun_adj_pos_tag.startswith('noun') or noun_adj_pos_tag.startswith('adj') \
                        or noun_adj_pos_tag.startswith('numr'):
                    if 'v_naz' in noun_adj_pos_tag:
                        noun_adj_token_readings_vnaz.append(token)
                    else:
                        state.noun_adj_indir_token_readings.append(token)
                    state.noun_pos = i
                else:
                    state = None
                    break

            # no following token - restart
            if state is None or (not noun_adj_token_readings_vnaz and not state.noun_adj_indir_token_readings):
                state = None
                i += 1
                continue

            # perform the check
            verb_inflections = None
            passed = False

            if noun_adj_token_readings_vnaz:
                state.noun_adj_naz_inflections = lh.get_verb_noun_inflections(noun_adj_token_readings_vnaz)
                state.noun_adj_naz_inflections.extend(lh.get_verb_adj_inflections(noun_adj_token_readings_vnaz))
                verb_inflections = lh.get_verb_inflections(state.verb_token_readings)
                passed = not lh.java_disjoint(verb_inflections, state.noun_adj_naz_inflections)

            if not passed and state.noun_adj_indir_token_readings:
                cases = lh.get_case_governments(state.verb_analyzed_token_readings, 'verb')

                # віддати-відрізати Донбас
                if len(cases) == 0 and '-' in state.verb_analyzed_token_readings.get_clean_token() \
                        and lh.has_lemma(state.verb_analyzed_token_readings, _NODASH_LEMMA):
                    nodash_readings = [AnalyzedToken(r.token, r.pos_tag,
                                                     jregex.java_replace(_NODASH_REPL, '$1', r.lemma, 1))
                                       for r in state.verb_analyzed_token_readings.readings
                                       if pth.has_pos_tag_start(r, 'verb')]
                    new_readings = AnalyzedTokenReadings.from_old(state.verb_analyzed_token_readings,
                                                                  nodash_readings, 'nodash')
                    cases = lh.get_case_governments(new_readings, 'verb')

                # було ввезено тракторів
                if _BULO.fullmatch(tokens[state.verb_pos - 1].get_clean_token().lower()) \
                        and pth.has_pos_tag(tokens[state.verb_pos], _IMPERS):
                    cases.add('v_rod')

                state.cases = cases

                token_lower_case = tokens[i].get_clean_token().lower()

                if 'v_zna' in cases and _HROSHEI.fullmatch(token_lower_case):
                    state = None
                    i += 1
                    continue

                if len(cases) == 0 or not has_vidm_pos_tag(cases, state.noun_adj_indir_token_readings):
                    pass
                else:
                    passed = True

            if not passed:
                if i < n - 1 and lh.has_lemma_pos(tokens[i], ('він', 'вона', 'вони'), _PRON_ROD) \
                        and pth.has_pos_tag(tokens[i + 1], _V_N):
                    # skip pron and try next token
                    i += 1
                    continue

                if is_exception(tokens, state, verb_inflections, state.noun_adj_naz_inflections,
                                state.verb_token_readings, noun_adj_token_readings_vnaz):
                    state.verb_token_readings = []
                    break

                if noun_adj_token_readings_vnaz or state.noun_adj_indir_token_readings:
                    cases = lh.get_case_governments(state.verb_analyzed_token_readings, 'verb')
                    if not has_vidm_pos_tag(cases, state.noun_adj_indir_token_readings):
                        rule_matches.append(self._create_match(sentence, tokens, state, token_readings, cases,
                                                               noun_adj_token_readings_vnaz))

            state = None
            i += 1

        return self.to_rule_match_array(rule_matches)

    def _create_match(self, sentence, tokens, state, token_readings, cases, noun_adj_token_readings_vnaz):
        infl2 = lh.get_noun_inflections(state.noun_adj_indir_token_readings)
        infl2.extend(lh.get_adj_inflections(state.noun_adj_indir_token_readings))
        infl2.extend(lh.get_numr_inflections(state.noun_adj_indir_token_readings))

        if noun_adj_token_readings_vnaz:
            infl0 = lh.get_noun_inflections(noun_adj_token_readings_vnaz)
            infl0.extend(lh.get_adj_inflections(noun_adj_token_readings_vnaz))
            infl0.extend(lh.get_numr_inflections(noun_adj_token_readings_vnaz))
            infl2.extend(infl0)

        msg = 'Не узгоджено дієслово з іменником: "%s" (%s) і "%s" (%s)' % (
            state.verb_token_readings[0].token, _format_cases(cases),
            state.noun_adj_indir_token_readings[0].token, format_adj_noun_inflections(infl2, False))

        # TODO: need to adjust highlight to the verb to replace instead of the noun
        verb_replace = None
        if state.verb_token_readings[0].lemma == 'сипіти':
            msg += '. Можливо ви мали на увазі слово «си\u0301пати», а не «сипі\u0301ти»?'
            verb_replace = 'сипати'
        elif state.verb_token_readings[0].lemma == 'сиплячи':
            msg += '. Можливо ви мали на увазі «сиплючи»?'
            verb_replace = 'сиплючи'

        start_pos = state.verb_analyzed_token_readings.start_pos
        match = RuleMatch(self, sentence, start_pos, token_readings.end_pos, msg, self.get_short())

        suggestions = self._get_suggestions(state.cases, token_readings)
        if token_readings.get_clean_token() == 'піку' and 'піка' in suggestions:
            suggestions = ['піка']

        inside_words = ''.join(' ' + tokens[ii].token for ii in range(state.verb_pos + 1, state.noun_pos))

        if verb_replace is not None:
            suggestions = ['%s%s %s' % (verb_replace, inside_words, token_readings.token)]
        else:
            suggestions = ['%s%s %s' % (state.verb_analyzed_token_readings.token, inside_words, s)
                           for s in suggestions]
        match.add_suggested_replacements(suggestions)
        return match

    def _get_verb_state(self, tokens, i):
        token_readings = tokens[i]
        clean_token_lower = token_readings.get_clean_token().lower()

        if pth.has_pos_tag(token_readings, _ARCH):
            return None
        if _ZNACHYT.fullmatch(clean_token_lower):
            return None

        state = None
        for token in token_readings:
            verb_pos_tag = token.pos_tag
            if verb_pos_tag is None:  # can happen for words with \u0301 or \u00AD
                continue
            if not _VERB_ADVP.fullmatch(verb_pos_tag) or 'abbr' in verb_pos_tag:
                return None
            if state is None:
                state = State()
                state.verb_pos = i
                state.verb_analyzed_token_readings = token_readings
            state.verb_token_readings.append(token)
        return state

    def _get_suggestions(self, cases, token_readings):
        if len(cases) == 0:
            return []
        required_post_tags_regex = ':(' + '|'.join(cases) + ')'
        suggestions = {}
        repl = _C(':v_[a-z]+')
        for at in token_readings.readings:
            old_pos_tag = at.pos_tag
            if old_pos_tag is None or ':v_' not in old_pos_tag:
                continue
            pos_tag = jregex.java_replace(repl, required_post_tags_regex.replace('$', '\\$'), old_pos_tag, 1)
            for s in self.synthesizer.synthesize(at, pos_tag, True):
                suggestions[s] = None
        return list(suggestions)


def _format_cases(cases):
    if len(cases) == 0:
        return 'неперех.'
    return 'вимагає: ' + ', '.join(pth.VIDMINKY_I_MAP.get(c, 'null') for c in cases)
