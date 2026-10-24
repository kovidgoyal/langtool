"""Port of org.languagetool.rules.uk.TokenAgreementNounVerbRule and
TokenAgreementNounVerbExceptionHelper."""

import functools

from ... import jregex
from ...analysis import PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import is_upper_case
from . import helpers as lh
from . import pos_tag_helper as pth
from .helpers import Condition, Match

# TokenAgreementAdjNounExceptionHelper.CONJ_FOR_PLURAL_WITH_COMMA etc. (also
# defined in the adj/noun rule module)
CONJ_FOR_PLURAL_WITH_COMMA = ('і', 'а', 'й', 'та', 'чи', 'або', 'ані', 'також', 'плюс', 'то', 'a', 'i', ',')
CONJ_FOR_PLURAL = ('і', 'а', 'й', 'та', 'чи', 'або', 'ані', 'також', 'то', 'a', 'i')
CONJ_FOR_PLURAL_PATTERN = jregex.compile('|'.join(CONJ_FOR_PLURAL))


def has_vidm_pos_tag(pos_tags_to_find, token_readings):
    """TokenAgreementPrepNounRule.hasVidmPosTag (for readings or a list of
    AnalyzedToken)"""
    readings = token_readings.readings if hasattr(token_readings, 'readings') else token_readings
    vidminok_found = False  # because POS dictionary is not complete
    for token in readings:
        pos_tag = token.pos_tag
        if pos_tag is None:
            if len(readings) == 1:
                return True
            continue
        # shortcut
        if pth.NO_VIDMINOK_SUBSTR in pos_tag:
            return True
        if ':v_' in pos_tag:
            vidminok_found = True
            for p in pos_tags_to_find:
                if p in pos_tag:
                    return True
    return not vidminok_found


# --- TokenAgreementNounVerbExceptionHelper ---

@functools.lru_cache(maxsize=None)
def _masc_fem_set():
    s = lh.load_set('/uk/masc_fem.txt')
    s |= {'екс-' + line for line in s}
    return frozenset(s)


_INF_ARGREEMENT_PATTERN = jregex.compile(
    "(не)?(здатний|змушений|з?г[іо]дний|зобов'язаний|повинний|готовий|достойний|покликаний|спроможний|радий"
    "|налаштований|зацікавлений|повинно|змога|стан|можна)")
_GEO_QUALIFIERS = {
    'село', 'селище', 'місто', 'містечко', 'хутір', 'республіка', 'держава', 'гора', 'планета', 'мікрорайон',
    'райцентр', 'заповідник', 'мис', 'острів',
    'м.', 'с.', 'п.',  # (н.п.)
    'штат', 'округ', 'графство',
    'вірус', 'ураган'}
_V_PREZYDENTY_PREP_LIST = ('в', 'у', 'між', 'межи', 'поміж', 'на')
_OSOBYSTO = ('особисто', 'зокрема', 'загалом')
_PSEUDO_PLURAL_NOUNS = ('решта', 'частина', 'частка', 'половина', 'третина', 'чверть')

_C = jregex.compile
_P_NOUN_P_NAZ_NON_PRON = _C('noun:.*:p:v_naz(?!.*pron).*')
_P_NUMR_P_ZNA = _C('numr:p:v_zna')
_P_FLNAME = _C('noun:anim:.:v_naz:prop:[fl]name.*')
_P_NOUN_NAZ_PROP = _C('noun.*:v_naz.*prop.*')
_P_DASH = _C('[-–—]')
_P_VERB = _C('verb.*')
_P_NOUN_P_NAZ = _C('noun.*:p:v_naz.*')
_P_VERB_PAST_N = _C('verb.*?past:n.*')
_P_DIGITS_234 = _C('\\d+[234]')
_P_VERB_FP = _C('verb.*:[fp](:.*|$)')
_P_VERB_P = _C('verb.*:p(:.*|$)')
_P_POS0_SKIP = _C('(noun.*?v_naz|(adj|numr):.:v_naz|adv|part).*')
_P_COMMA_ETC = _C('[,»“”"]')
_P_TAKOZH = _C('також')
_P_TAKOZH_IGNORE = _C('(noun|adj:.:v_naz|adv|part).*')
_P_NOUN_ADJ = _C('(noun|adj).*')
_P_COMMA = _C(',')
_P_ADJ = _C('adj.*')
_P_IDX_SKIP1 = _C('(noun|adj).*?v_(naz|rod).*')
_P_IDX_SKIP2 = _C('і?з|зі|від|на|навіть|також|потім|згодом')
_P_ZHINKA = _C('жінк[аи]')
_P_ANY = _C('.*')
_P_PLUS = _C('плюс')
_P_PLUS_IGNORE = _C('(numr|adj).*.:v_naz.*')
_P_ENDS_1 = _C('.+1')
_P_VERB_PAST_P = _C('verb.*(past:p|:p:3).*')
_P_ANI = _C('а?ні|жодн.*|навіть')
_P_ANI2 = _C('а?ні')
_P_NOUN_ROD = _C('noun.*:v_rod.*')
_P_GEO = _C('noun:inanim:[mnf]:v_naz:prop:geo.*')
_P_NON_NAZ = _C('noun:inanim:[mnf]:v_(?!naz)(?!.*pron).*')
_P_ROD_ZNA_MIS = _C('noun.*:v_(rod|zna|mis).*')
_P_INANIM_NAZ_PROP = _C('noun:inanim:.:v_naz:prop.*')
_P_INANIM = _C('noun:inanim:.*')
_P_ADJ_ANY = _C('adj:.*')
_P_ADV = _C('adv.*')
_P_INANIM_NAZ = _C('noun:inanim:.:v_naz.*')
_P_VERB_F = _C('verb.*:f(:.*|$)')
_P_PN = _C('.*:[pn](:.*|$)')
_P_P = _C('.*:p(:.*|$)')
_P_NOUN_KLY = _C('noun.*?v_kly.*')
_P_YAK = _C('[Яя]к')
_P_NIHTO = _C('ніхто|усі')


def _is_all_upper_case(s):
    """StringUtils.isAllUpperCase"""
    return bool(s) and all(is_upper_case(c) for c in s)


def is_non_plural_a(tokens, pos):
    # both Cyrillic and Latin :(
    return ((tokens[pos].token == 'а' or tokens[pos].token == 'a')
            and not lh.has_lemma(tokens[pos + 1], ('також', 'потім', 'пізніше')))


def has_masc_fem_lemma(noun_token_readings):
    token = noun_token_readings[0].token
    if token.endswith('олог') or token.endswith('знавець'):
        return True
    for t in noun_token_readings:
        pos_tag = t.pos_tag
        if pos_tag is not None and 'noun:anim:m:v_naz' in pos_tag:
            lemma = t.lemma
            if _is_in_masc_fem_set(lemma) or ('-' in lemma and _is_in_masc_fem_set(lemma.split('-', 1)[0])):
                return True
    return False


def _is_in_masc_fem_set(lemma):
    return lemma.replace('‘', '-') in _masc_fem_set()


def is_exception(tokens, noun_pos, verb_pos, noun_inflections, verb_inflections, noun_token_readings,
                 verb_token_readings):
    """TokenAgreementNounVerbExceptionHelper.isException"""
    disjoint = lh.java_disjoint

    # Любителі фотографувати їжу
    # навичка збиратися швидко (але не «навички»)
    if pth.has_pos_tag(tokens[verb_pos], pth.VERB_INF_PATTERN):
        if lh.has_case_government(tokens[noun_pos], 'v_inf'):
            return True
        # handled by xml rule
        if Match().token_line('не сила').m_before(tokens, noun_pos) > 0:
            return True
        if Match().token_line('не проти').m_before(tokens, noun_pos) > 0:
            return True
        if tokens[noun_pos].get_clean_token().lower() in ('хтось', 'дехто'):
            return True
        if tokens[verb_pos - 1].get_clean_token().lower() in ('намагаючись',):
            return True

    # шкода було, годі буде
    if pth.has_pos_tag_part(tokens[noun_pos], 'predic') and tokens[verb_pos].get_clean_token() in ('було', 'буде'):
        return True

    if tokens[noun_pos].token.lower() == 'правда':
        return True

    # під три чорти відіслати
    if Match().token_line('під три чорти').m_before(tokens, noun_pos) > 0:
        return True
    if Match().token_line('не штука').m_before(tokens, noun_pos) > 0:
        return True
    if Match().token_line('бісики').m_before(tokens, noun_pos) > 0:
        return True

    # handled by WORDS_WITH_DASH
    if Match().token_line('будь якого').m_after(tokens, verb_pos) >= 1:
        return True
    if Match().token_line('не сказати б').m_after(tokens, verb_pos - 1) >= 1:
        return True

    # Не проти бізнесмени користуватися
    if Match().token_line('не проти').m_before(tokens, verb_pos - 1) > 0:
        return True

    # handled by xml rule (VONO_IMPERF)
    if lh.has_lemma(tokens[noun_pos], ('воно', 'решта')):
        if pth.has_pos_tag_part(tokens[verb_pos], ':impers'):
            return True

    # handled by xml rule
    if lh.has_lemma(tokens[verb_pos - 1], ('Газа',)):
        return True

    # чотири дні був
    if noun_pos > 1 and pth.has_pos_tag(tokens[noun_pos], _P_NOUN_P_NAZ_NON_PRON) \
            and lh.has_lemma_pos(tokens[noun_pos - 1], ('два', 'три', 'чотири'), _P_NUMR_P_ZNA):
        return True

    # кандидат в президенти поїхав
    # вона межі люди пішла
    if noun_pos > 1 and pth.has_pos_tag_start(tokens[noun_pos], 'noun:anim:p:v_naz') \
            and lh.has_lemma(tokens[noun_pos - 1], _V_PREZYDENTY_PREP_LIST):
        return True

    # кандидат в народні депутати поїхав
    if noun_pos > 2 and pth.has_pos_tag_start(tokens[noun_pos], 'noun:anim:p:v_naz') \
            and pth.has_pos_tag_start(tokens[noun_pos - 1], 'adj:p:v_zna:rinanim') \
            and lh.has_lemma(tokens[noun_pos - 2], _V_PREZYDENTY_PREP_LIST):
        return True

    # невідомі прізвища, що виглядають, як дієслово: Андрій Качала
    if lh.is_capitalized(tokens[verb_pos].token) and lh.is_capitalized(tokens[noun_pos].token):
        return True

    # на прізвисько Михайло відбулася
    if noun_pos > 1 and pth.has_pos_tag(tokens[noun_pos], _P_FLNAME) \
            and tokens[noun_pos - 1].get_clean_token().lower() in ("ім'я", 'прізвище', 'прізвисько'):
        return True

    # матч Туреччина — Україна зіграють
    if noun_pos > 2 and pth.has_pos_tag(tokens[noun_pos], _P_NOUN_NAZ_PROP) \
            and _P_DASH.fullmatch(tokens[noun_pos - 1].get_clean_token()) \
            and pth.has_pos_tag(tokens[noun_pos - 2], _P_NOUN_NAZ_PROP):
        return True

    # невідомі прізвища, як іменник
    # Любов Євтушок зауважила
    if verb_pos > 2 and lh.is_capitalized(tokens[noun_pos].token) \
            and lh.is_capitalized(tokens[noun_pos - 1].token) \
            and not disjoint(lh.get_verb_noun_inflections(tokens[noun_pos - 1].readings), verb_inflections):
        return True

    # Тарас ЗАКУСИЛО
    if _is_all_upper_case(tokens[verb_pos].token):
        return True

    # Збережені Я позбудуться необхідності
    if noun_pos > 1 and tokens[noun_pos].token == 'Я':
        return True

    # а він давай пити горілку
    if 2 < verb_pos < len(tokens) - 1 and tokens[verb_pos].token == 'давай':
        return True

    # Ви може образились
    # but not: Як ви може оцінити
    # and not: що ми не може просто так
    if 1 < verb_pos < len(tokens) - 1 and tokens[verb_pos].token == 'може' \
            and tokens[verb_pos - 1].token != 'не' \
            and not pth.has_pos_tag(tokens[verb_pos + 1], pth.VERB_INF_PATTERN):
        return True

    # можуть російськомовні громадяни вважатися
    if noun_pos > 1 and pth.has_pos_tag(tokens[verb_pos], pth.VERB_INF_PATTERN):
        found_idx = lh.reverse_search_idx(tokens, noun_pos - 1, 6, _INF_ARGREEMENT_PATTERN, None)
        if found_idx >= 0:
            if not pth.has_pos_tag_start(tokens[found_idx], 'adj') \
                    or not disjoint(lh.get_noun_inflections(tokens[noun_pos].readings),
                                    lh.get_adj_inflections(tokens[found_idx].readings)):
                return True

    # ці громадяни проголосувати готові лише...
    if verb_pos < len(tokens) - 1 and pth.has_pos_tag(tokens[verb_pos], pth.VERB_INF_PATTERN):
        found_idx = lh.forward_lemma_search_idx(tokens, verb_pos + 1, 7, _INF_ARGREEMENT_PATTERN, None)
        if found_idx >= 0:
            if not pth.has_pos_tag_start(tokens[found_idx], 'adj') \
                    or not disjoint(lh.get_noun_inflections(noun_token_readings),
                                    lh.get_adj_inflections(tokens[found_idx].readings)):
                return True

    # як навчила мене бабуся місити тісто
    if noun_pos > 1 and pth.has_pos_tag(tokens[verb_pos], pth.VERB_INF_PATTERN):
        prev_verb_idx = lh.reverse_search_idx(tokens, noun_pos - 1, 7, None, _P_VERB)
        if prev_verb_idx >= 0 \
                and not disjoint(lh.get_verb_inflections(tokens[prev_verb_idx].readings),
                                 lh.get_verb_noun_inflections(tokens[noun_pos].readings)):
            return True

    # ці громадяни проголосувати зможуть лише...
    if verb_pos < len(tokens) - 1 and pth.has_pos_tag(tokens[verb_pos], pth.VERB_INF_PATTERN):
        next_verb_pos = Match().ignore_inserts().limit(8).target(Condition.postag(_P_VERB)) \
            .m_after(tokens, verb_pos + 1)
        if next_verb_pos >= 0 \
                and not disjoint(lh.get_verb_inflections(tokens[next_verb_pos].readings),
                                 lh.get_verb_noun_inflections(tokens[noun_pos].readings)):
            return True

    # — це були невільники
    # — це передбачено
    if noun_pos > 1 and verb_pos < len(tokens) - 1 and tokens[noun_pos].token == 'це' \
            and lh.DASHES_PATTERN.fullmatch(tokens[noun_pos - 1].token):
        return True

    # це не передбачено
    if tokens[noun_pos].token == 'це' and pth.has_pos_tag_part(verb_token_readings, 'impers'):
        return True

    # 22 льотчики загинуло миттєво
    # два сини народилося там
    if noun_pos > 1 and pth.has_pos_tag(tokens[noun_pos], _P_NOUN_P_NAZ) \
            and pth.has_pos_tag(verb_token_readings, _P_VERB_PAST_N) \
            and (_P_DIGITS_234.fullmatch(tokens[noun_pos - 1].get_clean_token())
                 or tokens[noun_pos - 1].get_clean_token() in ('два', 'три', 'чотири')):
        return True

    # зіркова пара Леброн Джеймс-Дуейн Вейн вирішили вивести
    if pth.has_pos_tag(verb_token_readings, _P_VERB_FP):
        if Match().target(Condition.token('пара')) \
                .skip(Condition.token(CONJ_FOR_PLURAL_PATTERN).negate()) \
                .m_before(tokens, noun_pos - 1) > 0:
            return True

    if pth.has_pos_tag(verb_token_readings, _P_VERB_P):
        if _is_exception_plural(tokens, noun_pos, verb_pos, verb_token_readings, disjoint):
            return True

    # Сейм Республіки Польща проігнорував
    if noun_pos > 3 and pth.has_pos_tag_part(tokens[noun_pos], ':prop') \
            and pth.has_pos_tag(tokens[noun_pos - 1], _P_NOUN_ROD) \
            and not disjoint(lh.get_verb_noun_inflections(tokens[noun_pos - 2].readings), verb_inflections):
        return True

    # комітет порятунку села Оляниця вирішив
    # кандидат у губернатори штату Аризона їхав
    if noun_pos > 1:
        if pth.has_pos_tag(tokens[noun_pos], _P_GEO) and pth.has_pos_tag(tokens[noun_pos - 1], _P_NON_NAZ):
            return True
        if lh.is_possibly_proper_noun(tokens[noun_pos]) and lh.has_lemma(tokens[noun_pos - 1], _GEO_QUALIFIERS):
            return True
        # У місті Біла Церква було сформовано
        if noun_pos > 2 and lh.is_possibly_proper_noun(tokens[noun_pos]) \
                and lh.is_possibly_proper_noun(tokens[noun_pos - 1]) \
                and lh.has_lemma(tokens[noun_pos - 2], _GEO_QUALIFIERS):
            return True

    # У невизнаній республіці Південна Осетія відбулися вибори
    if noun_pos > 3 and pth.has_pos_tag_part(tokens[noun_pos], 'v_naz:prop') \
            and pth.has_pos_tag(tokens[noun_pos - 1], 'adj:.:v_naz.*') \
            and pth.has_pos_tag(tokens[noun_pos - 2], _P_ROD_ZNA_MIS):
        return True

    # У штатах Техас і Луїзіана запроваджено надзвичайний стан
    if noun_pos > 1 and pth.has_pos_tag_part(tokens[noun_pos], ':prop') \
            and pth.has_pos_tag(tokens[verb_pos], 'verb.*:impers.*'):
        return True

    # на австралійський штат Вікторія налетів сильний шторм
    if noun_pos > 3 and pth.has_pos_tag(tokens[noun_pos], _P_INANIM_NAZ_PROP) \
            and pth.has_pos_tag(tokens[noun_pos - 1], _P_INANIM) \
            and pth.has_pos_tag(tokens[noun_pos - 2], _P_ADJ_ANY) \
            and pth.has_pos_tag_part(tokens[noun_pos - 3], 'prep'):
        prep_governed_cases = lh.get_case_governments(tokens[noun_pos - 3], 'prep')
        if has_vidm_pos_tag(prep_governed_cases, tokens[noun_pos - 1]) \
                and has_vidm_pos_tag(prep_governed_cases, tokens[noun_pos - 2]):
            return True

    # Угорщина було пішла шляхом
    if verb_pos < len(tokens) - 1 and tokens[verb_pos].get_clean_token() == 'було':
        pos = lh.token_search(tokens, verb_pos + 1, 'verb:', None, _P_ADV, lh.FORWARD)
        if pos >= 0 and not disjoint(lh.get_verb_noun_inflections(tokens[noun_pos].readings),
                                     lh.get_verb_inflections(tokens[pos].readings)):
            return True

    # клан Рана було знищено
    if verb_pos < len(tokens) - 1 and pth.has_pos_tag_part(tokens[noun_pos], ':prop') \
            and tokens[verb_pos].get_clean_token() == 'було' \
            and pth.has_pos_tag(tokens[verb_pos + 1], 'verb.*:impers.*'):
        return True

    # діагноз дизентерія підтвердився
    # селище Криниця розташувалося
    if noun_pos > 1 and pth.has_pos_tag(tokens[noun_pos - 1], _P_INANIM_NAZ) \
            and not pth.has_pos_tag_part(tokens[noun_pos - 1], ':pron') \
            and not pth.has_pos_tag(tokens[noun_pos], 'noun.*pron.*') \
            and not disjoint(lh.get_verb_noun_inflections(tokens[noun_pos - 1].readings), verb_inflections):
        return True

    # Прем’єр-міністр повторила у телезверненні
    if pth.has_pos_tag_part(noun_token_readings, 'noun:anim:m:v_naz') \
            and pth.has_pos_tag(verb_token_readings, _P_VERB_F) \
            and has_masc_fem_lemma(noun_token_readings):
        return True

    # пора було
    if tokens[noun_pos].get_clean_token().lower() == 'пора' and tokens[verb_pos].get_clean_token() == 'було':
        return True

    # решта забороняються
    if tokens[noun_pos].get_clean_token().lower() in _PSEUDO_PLURAL_NOUNS \
            and pth.has_pos_tag(verb_token_readings, _P_PN):
        return True

    # з Василем Кричевським Оскар Германович разом брали участь
    if tokens[noun_pos + 1].get_clean_token().lower() == 'разом' and pth.has_pos_tag(verb_token_readings, _P_P):
        return True

    # більше ніж будь-хто маємо повне право
    if noun_pos > 2 and lh.has_lemma(tokens[noun_pos - 1], 'ніж'):
        return True

    # моя ти зоре
    if noun_pos > 1 and tokens[noun_pos].token.lower() == 'ти' \
            and pth.has_pos_tag(tokens[verb_pos], _P_NOUN_KLY):
        return True

    # вона візьми та й скажи
    if verb_pos < len(tokens) - 2 and tokens[verb_pos].token == 'візьми' \
            and lh.has_lemma(tokens[verb_pos + 1], ('і', 'й', 'та')):
        return True

    # ми в державі Україна маємо права
    v_pos = verb_pos
    if verb_pos > 3 and pth.has_pos_tag(tokens[verb_pos - 1], _P_INANIM_NAZ_PROP):
        # в селі Червона Слобода було вирішено
        token = tokens[noun_pos - 1].token
        if lh.is_capitalized(token) and pth.has_pos_tag_start(tokens[noun_pos - 1], 'adj'):
            v_pos -= 1
        if pth.has_pos_tag_start(tokens[v_pos - 2], 'noun:inanim') \
                and pth.has_pos_tag_part(tokens[v_pos - 3], 'prep'):
            prep_governed_cases = lh.get_case_governments(tokens[v_pos - 3], 'prep')
            if has_vidm_pos_tag(prep_governed_cases, tokens[v_pos - 2]):
                return True

    # чи готові ми сидіти
    if noun_pos > 1 and pth.has_pos_tag_part(tokens[noun_pos - 1], 'adj') \
            and pth.has_pos_tag(verb_token_readings, pth.VERB_INF_PATTERN) \
            and lh.has_case_government(tokens[noun_pos - 1], 'v_inf') \
            and not disjoint(lh.get_adj_inflections(tokens[noun_pos - 1].readings),
                             lh.get_noun_inflections(noun_token_readings)):
        return True

    # тому що, як австрієць маєте
    if noun_pos > 1 and _P_YAK.fullmatch(tokens[noun_pos - 1].get_clean_token()):
        if _P_NIHTO.fullmatch(tokens[noun_pos].get_clean_token()):
            return True
        if tokens[noun_pos].get_clean_token() == 'воно' \
                and pth.has_pos_tag(tokens[verb_pos], pth.VERB_INF_PATTERN):
            return True
        if noun_pos > 2 and lh.has_lemma(tokens[noun_pos - 2], ('такий', 'само')):
            return True

    # тому що, як австрієць маєте
    if pth.has_pos_tag(tokens[noun_pos], pth.NOUN_NON_PRON_V_NAZ_PATTERN) \
            and lh.token_search(tokens, noun_pos - 1, None, _P_YAK, pth.ADJ_V_NAZ_PATTERN, lh.REVERSE) != -1:
        return True

    return False


def _is_exception_plural(tokens, noun_pos, verb_pos, verb_token_readings, disjoint):
    """The part of isException for plural verbs (verb.*:p)"""
    # Колесніков/Ахметов посилили
    if noun_pos > 2 and (tokens[noun_pos - 1].token == '/' or tokens[noun_pos - 2].token == '/'):
        return True

    # кефаль, барабуля, хамса не затримуються
    if noun_pos > 2 and tokens[noun_pos - 1].token in CONJ_FOR_PLURAL_WITH_COMMA \
            and pth.has_pos_tag(tokens[noun_pos - 2], pth.NOUN_V_NAZ_PATTERN):
        return True

    # його побут, життєва поведінка не можуть
    if noun_pos > 3 and tokens[noun_pos - 2].token in CONJ_FOR_PLURAL_WITH_COMMA \
            and pth.has_pos_tag(tokens[noun_pos - 3], pth.NOUN_V_NAZ_PATTERN) \
            and not disjoint(lh.get_adj_inflections(tokens[noun_pos - 1].readings),
                             lh.get_noun_inflections(tokens[noun_pos].readings)):
        return True

    # моя мама й сестра мешкали
    # каналізація і навіть охорона пропонувалися
    # Ґорбачов і його дружина виглядали
    pos0left = Match().ignore_inserts().limit(7).target(Condition.token(CONJ_FOR_PLURAL_PATTERN)) \
        .skip(Condition.postag(_P_POS0_SKIP)).m_before(tokens, noun_pos - 1)

    pos0right = pos0left
    if pos0left > 0:
        if is_non_plural_a(tokens, pos0left):
            pos0left = -1

    # і мама, і тато
    if pos0left > 1 and tokens[pos0left - 1].token == ',':
        pos0left -= 1

    if pos0left > 1:
        if pos0right > 2:
            # і та й інша
            if pos0left < len(tokens) - 1 and lh.has_lemma(tokens[pos0right + 1], 'інший') \
                    and lh.has_lemma(tokens[pos0left - 1], 'той'):
                return True

            # як Німеччина, так і Україна
            if pth.has_pos_tag_part(tokens[pos0left - 1], 'conj'):
                pos0left -= 1

            # він особисто й облдержадміністрація винесли
            if tokens[pos0left - 1].get_clean_token() in _OSOBYSTO:
                pos0left -= 1

            # громада, або ти особисто закликаєте
            if tokens[verb_pos - 1].get_clean_token() in _OSOBYSTO:
                return True

            # Німеччина (ще демократична) та Росія почали
            if tokens[pos0left - 1].token == ')':
                return True

            # і уряд (noun+adv), і президент
            if pth.has_pos_tag(tokens[pos0left - 1], pth.NOUN_V_NAZ_PATTERN):
                return True

            # І спочатку Білорусь, а тепер і Україна пішли
            if verb_pos > 6:
                if pth.has_pos_tag_part(tokens[pos0left - 1], 'adv') \
                        and pth.has_pos_tag_part(tokens[pos0left - 2], 'conj'):
                    pos0left -= 2

            while pos0left > 2 and _P_COMMA_ETC.fullmatch(tokens[pos0left - 1].token):
                pos0left -= 1

        # моя мама й сестра мешкали
        if pth.has_pos_tag_start(tokens[pos0left - 1], 'noun') \
                or pth.has_pos_tag_start(tokens[pos0left - 1], 'number:latin') \
                or lh.is_possibly_proper_noun(tokens[pos0left - 1]):
            return True
        # біологічна і ядерна зброя стають товаром
        if pth.has_pos_tag(tokens[pos0left - 1], pth.ADJ_V_NAZ_PATTERN):
            return True

    # Усі розписи, а також архітектура відрізняються
    pos3 = lh.token_search(tokens, verb_pos - 2, None, _P_TAKOZH, _P_TAKOZH_IGNORE, lh.REVERSE)
    if pos3 > 1:
        return True

    # що пачка цигарок, що ковбаса коштують
    if noun_pos > 5:
        lower_case_prev_token = tokens[noun_pos - 1].token.lower()
        if lower_case_prev_token in ('що', 'не') \
                and lh.token_search(tokens, noun_pos - 3, None,
                                    jregex.compile(lower_case_prev_token, jregex.IGNORECASE),
                                    _P_NOUN_ADJ, lh.REVERSE) > noun_pos - 7:
            return True

    # Бразилія, Мексика, Індія збувають
    pos1 = lh.token_search(tokens, noun_pos - 1, None, _P_COMMA, _P_ADJ, lh.REVERSE)
    if (pos1 > 1 and pth.has_pos_tag(tokens[pos1 - 1], pth.NOUN_V_NAZ_PATTERN)) \
            or (pos1 > 2 and pth.has_pos_tag(tokens[pos1 - 1], 'noun.*:v_rod.*')
                and pth.has_pos_tag(tokens[pos1 - 2], pth.NOUN_V_NAZ_PATTERN)):
        return True

    # Мустафа Джемілєв, Рефат Чубаров зможуть
    # А. Кидисюк, В. Загорський відповідають
    if noun_pos > 4 and lh.is_capitalized(tokens[noun_pos].token) \
            and (pth.has_pos_tag_start(tokens[noun_pos - 1], 'noun:anim') or lh.is_initial(tokens[noun_pos - 1])) \
            and tokens[noun_pos - 2].token in CONJ_FOR_PLURAL_WITH_COMMA \
            and lh.is_capitalized(tokens[noun_pos - 3].token) \
            and (pth.has_pos_tag_start(tokens[noun_pos - 4], 'noun:anim') or lh.is_initial(tokens[noun_pos - 1])):
        return True

    # закордонний депутат і прем'єр Великої Британії Черчиль
    # а також/потім/навіть голова Європейської ради Дональд Туск провели
    idx = Match().target(Condition.token(CONJ_FOR_PLURAL_PATTERN)).ignore_inserts() \
        .skip(Condition.postag(_P_IDX_SKIP1), Condition.token(_P_IDX_SKIP2)).m_before(tokens, noun_pos - 1)
    if idx > 0:
        if is_non_plural_a(tokens, idx):
            idx = -1
    if idx > 1 and (pth.has_pos_tag(tokens[idx - 1], pth.NOUN_V_NAZ_PATTERN)
                    or lh.is_capitalized(tokens[idx - 1].get_clean_token())
                    or lh.has_lemma(tokens[idx + 1], ('навіть', 'також', 'потім', 'згодом'))
                    or lh.has_lemma(tokens[idx - 1], ('потім', 'згодом'))):
        return True

    # понад сотня отримали поранення
    if (pth.has_pos_tag_part(tokens[noun_pos], 'numr') and not lh.has_lemma(tokens[noun_pos], 'один')) \
            or lh.has_lemma(tokens[noun_pos], ('сотня', 'тисяча', 'десяток')):
        return True

    if noun_pos > 1 and pth.has_pos_tag_part(tokens[noun_pos - 1], 'number') \
            and (not tokens[noun_pos - 1].token.endswith('1') or tokens[noun_pos - 1].token.endswith('11')):
        return True

    # 100 чоловік - handled by styling rule
    if pth.has_pos_tag_part(tokens[noun_pos - 1], 'num') and tokens[noun_pos].token == 'чоловік' \
            and lh.token_search(tokens, 1, 'noun:anim:f:.*', _P_ZHINKA, _P_ANY, lh.FORWARD) == -1:
        return True

    # 50%+1 акція закріплюються
    # заінтересованість плюс гарна вивіска зіграли злий жарт
    if noun_pos > 1 and (tokens[noun_pos - 1].token.endswith('+1')
                         or lh.token_search(tokens, verb_pos - 2, None, _P_PLUS, _P_PLUS_IGNORE, lh.REVERSE) > 0):
        return True

    # Решта 121 депутат висловилися проти
    if noun_pos > 2 and lh.has_lemma(tokens[noun_pos - 2], 'решта') \
            and tokens[noun_pos - 1].token is not None and _P_ENDS_1.fullmatch(tokens[noun_pos - 1].token):
        return True

    # дві групи, кожна виконували просте завдання
    if noun_pos > 2 and lh.has_lemma(tokens[noun_pos], 'кожний') \
            and pth.has_pos_tag(verb_token_readings, _P_VERB_PAST_P):
        return True

    # душ, одеколони, навіть хлорка не допомогли
    if noun_pos > 2 and _P_ANI.fullmatch(tokens[noun_pos - 1].token):
        return True

    if noun_pos > 2 and tokens[verb_pos - 1].token == 'не' \
            and lh.reverse_search(tokens, noun_pos - 1, 5, _P_ANI2, None):
        return True

    if noun_pos > 3 and tokens[verb_pos - 1].token == 'не' and _P_ANI2.fullmatch(tokens[noun_pos - 2].token) \
            and not disjoint(lh.get_adj_inflections(tokens[noun_pos - 1].readings),
                             lh.get_noun_inflections(tokens[noun_pos].readings)):
        return True
    return False


# --- TokenAgreementNounVerbRule ---

_NOUN_V_NAZ_PATTERN = jregex.compile('noun.*:v_naz.*')
_HTO_VERB = jregex.compile('verb.*:[fp]\\b.*')
_PART = jregex.compile('part')
_ADV_ALL = jregex.compile('adv.*')
_ADJ_NAZ_KLY = jregex.compile('adj:.:(v_naz|v_kly).*')


class _State:
    __slots__ = ('noun_pos', 'noun_token_readings', 'noun_analyzed_token_readings', 'adj_token_readings')

    def __init__(self):
        self.noun_pos = 0
        self.noun_token_readings = []
        self.noun_analyzed_token_readings = None
        self.adj_token_readings = []


class TokenAgreementNounVerbRule(Rule):
    """A rule that checks if noun and verb agree"""

    def __init__(self, messages, language=None):
        super().__init__()
        self.category = Categories.get('MISC', messages)

    def get_id(self):
        return 'UK_NOUN_VERB_INFLECTION_AGREEMENT'

    def get_description(self):
        return 'Узгодження іменника та дієслова за родом, числом та особою'

    def get_short(self):
        return 'Узгодження іменника з дієсловом'

    def is_case_sensitive(self):
        return False

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        state = None
        i = 1
        n = len(tokens)
        while i < n:
            token_readings = tokens[i]
            clean_token = token_readings.get_clean_token()
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

            if pth.has_pos_tag(token_readings, _NOUN_V_NAZ_PATTERN) or clean_token == 'яка':
                state = _State()
                for token in token_readings:
                    noun_pos_tag = token.pos_tag
                    if noun_pos_tag is None:  # can happen for words with \u0301 or \u00AD
                        continue
                    if token.lemma == 'який' and ':f:v_naz' in token.pos_tag:
                        state.noun_pos = i
                        state.noun_token_readings.append(token)
                        state.noun_analyzed_token_readings = token_readings
                    elif clean_token.lower() == 'хто' \
                            and lh.token_search(tokens, i + 1, _HTO_VERB, None, _PART, lh.FORWARD) > 0:
                        # ignore: про те, хто була ця клята Пандора
                        state = None
                        break
                    elif i < n - 1 and clean_token.lower() == 'хто' \
                            and pth.has_pos_tag_all(tokens[i + 1].readings, _ADV_ALL) \
                            and lh.token_search(tokens, i + 2, _HTO_VERB, None, _PART, lh.FORWARD) > 0:
                        state = None
                        break
                    elif noun_pos_tag.startswith('noun') and 'v_naz' in noun_pos_tag:
                        state.noun_pos = i
                        state.noun_token_readings.append(token)
                        state.noun_analyzed_token_readings = token_readings
                    elif noun_pos_tag.startswith('noun') and 'v_kly' in noun_pos_tag:
                        pass  # ignore
                    elif pth.is_predict_or_insert(token):
                        pass  # ignore
                    elif _ADJ_NAZ_KLY.fullmatch(token.pos_tag) \
                            or (token.pos_tag.startswith('adj:m:v_zna:rinanim')
                                and not pth.has_pos_tag_start(tokens[i - 1], 'prep')
                                and token.token.lower() not in ('кожен', 'інший', 'старий', 'черговий')):
                        state.adj_token_readings.append(token)
                    else:
                        state = None
                        break
                i += 1
                continue

            if state is None:
                i += 1
                continue

            if token_readings.token in ('не', 'б', 'би', 'бодай'):
                i += 1
                continue

            if pth.has_pos_tag_part_all(token_readings, 'adv'):
                i += 1
                continue

            # see if we get a following verb
            verb_token_readings = []
            for token in token_readings:
                verb_pos_tag = token.pos_tag
                if verb_pos_tag is None or verb_pos_tag == SENTENCE_END_TAGNAME \
                        or verb_pos_tag == PARAGRAPH_END_TAGNAME:
                    continue
                if verb_pos_tag.startswith('<'):
                    verb_token_readings = []
                    break
                if verb_pos_tag.startswith('verb'):
                    verb_token_readings.append(token)
                elif pth.is_predict_or_insert(token):
                    pass  # ignore
                else:
                    verb_token_readings = []
                    break

            # no slave token - restart
            if not verb_token_readings:
                state = None
                i += 1
                continue

            # perform the check
            master_inflections = lh.get_verb_noun_inflections(state.noun_token_readings)
            slave_inflections = lh.get_verb_inflections(verb_token_readings)

            if lh.java_disjoint(master_inflections, slave_inflections):
                if is_exception(tokens, state.noun_pos, i, master_inflections, slave_inflections,
                                state.noun_token_readings, verb_token_readings):
                    state.noun_token_readings = []
                    break

                msg = 'Не узгоджено %s з дієсловом: "%s" (%s) і "%s" (%s)' % (
                    'займенник' if lh.has_lemma(state.noun_token_readings, ('який',)) else 'іменник',
                    state.noun_token_readings[0].token, _format_inflections(master_inflections, True),
                    verb_token_readings[0].token, _format_inflections(slave_inflections, False))
                rule_matches.append(RuleMatch(self, sentence, state.noun_analyzed_token_readings.start_pos,
                                              token_readings.end_pos, msg, self.get_short()))

            state = None
            i += 1

        return self.to_rule_match_array(rule_matches)


def _format_inflections(inflections, noun):
    inflections.sort(key=lambda x: x.sort_key())
    out = []
    for infl in inflections:
        s = ''
        if infl.gender is not None:
            s = pth.GENDER_MAP.get(infl.gender)
        else:
            if infl.person is not None:
                s = pth.PERSON_MAP.get(infl.person)
            if infl.plural is not None:
                if s:
                    s += ' '
                s += pth.GENDER_MAP.get(infl.plural)
        out.append(s)
    return ', '.join(dict.fromkeys(out))
