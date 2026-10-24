"""Port of org.languagetool.rules.uk.TokenAgreementAdjNounRule and
TokenAgreementAdjNounExceptionHelper."""

from ... import jregex
from ...analysis import PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import is_upper_case, java_equals_ignore_case
from . import helpers as lh
from . import pos_tag_helper as pth
from .agreement_prep_noun import has_vidm_pos_tag
from .helpers import Condition, Match, java_disjoint

FAKE_FEM_LIST = ('ступінь', 'степінь', 'продаж', 'собака', 'дріб', 'ярмарок', 'нежить', 'рукопис', 'накип', 'насип',
                 'путь')

ADJ_INFLECTION_PATTERN = lh.ADJ_INFLECTION_PATTERN
NOUN_INFLECTION_PATTERN = lh.NOUN_INFLECTION_PATTERN

_V_ZNA_VAR = jregex.compile('v_zna:var')
_U_INSTEAD_OF_A = jregex.compile('.*[ую]')
_NOUN_M_V_DAV = jregex.compile('noun.*?:m:v_dav.*')
_NUM_SUFFIX = jregex.compile('.*([23]-є|[02-9]-а|[0-9]-м[иа])')
_NUM_SUFFIX_REPL = jregex.compile('[-–]м[аи]$')
_NOUN_TAG_REPL = jregex.compile(':.:v_...')
_ADJ_TAG_REPL = jregex.compile(':.:v_...(:r(in)?anim)?')


class _State:
    __slots__ = ('adj_pos', 'adj_token_readings', 'adj_analyzed_token_readings')

    def __init__(self):
        self.adj_pos = 0
        self.adj_token_readings = []
        self.adj_analyzed_token_readings = None

    def is_empty(self):
        return not self.adj_token_readings

    def reset(self):
        self.adj_token_readings.clear()
        self.adj_analyzed_token_readings = None


class TokenAgreementAdjNounRule(Rule):
    """A rule that checks if adjective and following noun agree on gender and
    inflection"""

    def __init__(self, messages, language):
        super().__init__()
        self.category = Categories.get('MISC', messages)
        self.synthesizer = language.synthesizer

    def get_id(self):
        return 'UK_ADJ_NOUN_INFLECTION_AGREEMENT'

    def get_description(self):
        return 'Узгодження відмінків, роду і числа прикметника та іменника'

    def get_short(self):
        return 'Узгодження прикметника та іменника'

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        state = _State()
        n = len(tokens)

        for i in range(1, n):
            token_readings = tokens[i]
            pos_tag0 = token_readings.readings[0].pos_tag

            if pos_tag0 is None:
                state.reset()
                continue

            if state.is_empty():
                # no need to start checking on last token or if no noun
                if i == n - 1:
                    continue
            else:
                if ((pth.has_pos_tag_part_all(token_readings, 'adv')
                     or token_readings.get_clean_token() in ('дуже', 'небагато', 'багато'))
                        # TODO: temp for adv/prep
                        and not (i < n - 1 and pth.has_pos_tag_start(tokens[i], 'prep')
                                 and has_vidm_pos_tag(lh.get_case_governments(tokens[i], 'prep'), tokens[i + 1]))
                        and pth.has_pos_tag_part(state.adj_token_readings, 'adjp')):
                    continue

            # grab initial adjective inflections

            if pth.has_pos_tag_start(tokens[i], 'adj'):
                state.reset()

                # TODO: nv still can be wrong if :np/:ns is present to it's not much gain for lots of work
                if pth.has_pos_tag_part(tokens[i], pth.NO_VIDMINOK_SUBSTR) \
                        or lh.has_lemma(tokens[i], ('який', 'котрий', 'сам')) \
                        or pth.has_pos_tag_part(tokens[i], '<'):
                    continue

                if lh.has_lemma_part_pos(tokens[i], ('подібний',), ':n:'):
                    state.reset()
                    break

                for token in token_readings.readings:
                    adj_pos_tag = token.pos_tag
                    if adj_pos_tag is None:  # can happen for words with \u0301 or \u00AD
                        continue
                    if adj_pos_tag.startswith('adj'):
                        state.adj_pos = i
                        state.adj_token_readings.append(token)
                        state.adj_analyzed_token_readings = token_readings
                    elif (not lh.has_lemma_part_pos(token_readings, ('другий',), 'adj:f:')
                          or (i + 1 < n and not lh.has_lemma_part_pos(tokens[i + 1], FAKE_FEM_LIST, 'noun:inanim:m:'))
                          and not pth.is_predict_or_insert(token)):
                        state.reset()
                        break
                continue

            if state.is_empty():
                continue

            if pth.has_pos_tag_part(tokens[i], pth.NO_VIDMINOK_SUBSTR) or pth.has_pos_tag_part(tokens[i], 'pron'):
                state.reset()
                continue

            noun_token_readings = []
            for token in token_readings.readings:
                noun_pos_tag = token.pos_tag
                if noun_pos_tag is None:  # can happen for words with \u0301 or \u00AD
                    continue
                if noun_pos_tag.startswith('noun'):
                    noun_token_readings.append(token)
                elif noun_pos_tag == SENTENCE_END_TAGNAME or noun_pos_tag == PARAGRAPH_END_TAGNAME:
                    continue
                elif not pth.is_predict_or_insert(token):
                    noun_token_readings.clear()
                    break

            # no slave token - restart
            if not noun_token_readings:
                state.reset()
                continue

            # perform the check

            master_inflections = lh.get_adj_inflections(state.adj_token_readings)
            slave_inflections = lh.get_noun_inflections(noun_token_readings, _V_ZNA_VAR)

            if java_disjoint(master_inflections, slave_inflections):
                if is_exception(tokens, state.adj_pos, i, master_inflections, slave_inflections,
                                state.adj_token_readings, noun_token_readings):
                    state.reset()
                    continue

                msg = ('Потенційна помилка: прикметник не узгоджений з іменником: "%s": [%s] і "%s": [%s]' % (
                    state.adj_token_readings[0].token, format_inflections(master_inflections, True),
                    noun_token_readings[0].token, format_inflections(slave_inflections, False)))

                adj_atr = state.adj_analyzed_token_readings
                if pth.has_pos_tag_part(state.adj_token_readings, ':m:v_rod') \
                        and _U_INSTEAD_OF_A.fullmatch(tokens[i].token) \
                        and pth.has_pos_tag(noun_token_readings, _NOUN_M_V_DAV):
                    msg += lh.USED_U_INSTEAD_OF_A_MSG
                elif '-' in adj_atr.token and _NUM_SUFFIX.fullmatch(adj_atr.token):
                    msg += '. Можливо, вжито зайве літерне нарощення після кількісного числівника?'
                elif adj_atr.token.startswith('не') and pth.has_pos_tag(noun_token_readings, 'noun.*?:v_oru.*'):
                    msg += '. Можливо, тут «не» потрібно писати окремо?'
                elif not pth.has_pos_tag(state.adj_token_readings, 'adj.*?v_mis.*') \
                        and pth.has_pos_tag(noun_token_readings, 'noun.*?v_mis.*'):
                    msg += '. Можливо, пропущено прийменник на/в/у...?'

                potential_rule_match = RuleMatch(self, sentence, adj_atr.start_pos, token_readings.end_pos, msg,
                                                 self.get_short())

                suggestions = []
                for adj_inflection in master_inflections:
                    gender_tag = ':' + adj_inflection.gender + ':'
                    vidm_tag = adj_inflection.case
                    if adj_inflection.case != 'v_kly' and (adj_inflection.gender == 'p' or
                                                           pth.has_pos_tag_part(noun_token_readings, gender_tag)):
                        for noun_token in noun_token_readings:
                            if adj_inflection.anim_matters():
                                if ':' + adj_inflection.anim_tag not in noun_token.pos_tag:
                                    continue
                            new_noun_pos_tag = jregex.java_replace(_NOUN_TAG_REPL, gender_tag + vidm_tag,
                                                                   noun_token.pos_tag, 1)
                            for s in self.synthesizer.synthesize(noun_token, new_noun_pos_tag, False):
                                suggestion = adj_atr.token + ' ' + s
                                if suggestion not in suggestions:
                                    suggestions.append(suggestion)

                for noun_inflection in slave_inflections:
                    gender_tag = ':' + noun_inflection.gender + ':'
                    vidm_tag = noun_inflection.case
                    if noun_inflection.anim_matters():
                        vidm_tag += ':r' + noun_inflection.anim_tag
                    for adj_token in state.adj_token_readings:
                        new_adj_tag = jregex.java_replace(_ADJ_TAG_REPL, gender_tag + vidm_tag, adj_token.pos_tag, 1)
                        for s in self.synthesizer.synthesize(adj_token, new_adj_tag, False):
                            suggestion = s + ' ' + token_readings.token
                            if suggestion not in suggestions:
                                suggestions.append(suggestion)

                if 'кількісного числівника' in msg:
                    sugg_num = jregex.java_replace(_NUM_SUFFIX_REPL, '', adj_atr.get_clean_token(), 1) + ' ' + \
                        token_readings.token
                    suggestions.append(sugg_num)

                if suggestions:
                    potential_rule_match.set_suggested_replacements(suggestions)

                rule_matches.append(potential_rule_match)

            state.reset()

        return rule_matches


def format_inflections(inflections, adj):
    """formatInflections (sorts the list in place like Collections.sort)"""
    inflections.sort(key=lambda x: x.sort_key())
    m = {}
    for inflection in inflections:
        case_str = pth.VIDMINKY_MAP.get(inflection.case)
        if adj and inflection.anim_tag is not None:
            case_str = '%s (%s)' % (case_str, 'іст.' if inflection.anim_tag == 'anim' else 'неіст.')
        m.setdefault(inflection.gender, []).append(case_str if case_str is not None else 'null')
    out = []
    for gender, case_values in m.items():
        gender_str = pth.GENDER_MAP.get(gender)
        out.append('%s: %s' % ('null' if gender_str is None else gender_str, ', '.join(case_values)))
    return ', '.join(out)


# --- TokenAgreementAdjNounExceptionHelper ---

_VERB_ADVP_PATTERN = jregex.compile('(verb|advp).*')
_NUMBER_V_NAZ = jregex.compile('number|numr:p:v_naz|noun.*?:p:v_naz.*:numr.*')
# including latin 'a' and 'i' so the rules don't trip on them in Ukrainian sentences
CONJ_FOR_PLURAL_WITH_COMMA = ('і', 'а', 'й', 'та', 'чи', 'або', 'ані', 'також', 'плюс', 'то', 'a', 'i', ',')
CONJ_FOR_PLURAL = ('і', 'а', 'й', 'та', 'чи', 'або', 'ані', 'також', 'то', 'a', 'i')
CONJ_FOR_PLURAL_PATTERN = jregex.compile('|'.join(CONJ_FOR_PLURAL))
CONJ_FOR_PLURAL_WITH_COMMA_PATTERN = jregex.compile('|'.join(CONJ_FOR_PLURAL_WITH_COMMA))
_DOVYE_TROYE = jregex.compile(
    '.*[2-4]|.*[2-4][–—-].*[2-4]|два|обидва|двоє|двійко|три|троє|чотири|один[–—-]два'
    '|два[–—-]три|три[–—-]чотири|двоє[–—-]троє|троє[–—-]четверо|півтор[аи]')
_VERB_NOT_INSERT_PATTERN = jregex.compile('verb(?!.*insert)')

_P = jregex.compile


def _upper0(atr):
    t = atr.token
    return bool(t) and is_upper_case(t[0])


def is_exception(tokens, adj_pos, noun_pos, master_inflections, slave_inflections, adj_token_readings,
                 slave_token_readings):
    adj_atr = tokens[adj_pos]
    n = len(tokens)

    # схований всередині номера
    if noun_pos - adj_pos > 1:
        cases = lh.get_case_governments(tokens[adj_pos + 1], 'adv')
        if len(cases) > 0 and has_vidm_pos_tag(cases, tokens[noun_pos]):
            return True

    if lh.has_lemma_pos(tokens[adj_pos], _P('інститутський'), _P('adj:f:.*')) \
            and _P('І.*').fullmatch(tokens[adj_pos].get_clean_token()):
        return True

    if adj_pos > 1 and tokens[adj_pos - 1].get_clean_token() == 'більшості' \
            and tokens[adj_pos].get_clean_token() == 'своїй':
        return True

    if adj_pos > 1 and lh.is_capitalized(tokens[adj_pos].get_clean_token()) \
            and lh.is_capitalized(tokens[adj_pos - 1].get_clean_token()) \
            and (lh.has_lemma(tokens[adj_pos], 'вітчизняний') or lh.has_lemma(tokens[adj_pos], 'житомирський')) \
            and lh.has_lemma(tokens[adj_pos - 1], 'великий') and not lh.has_lemma(tokens[noun_pos], 'війна'):
        return True

    if adj_pos > 1 and lh.has_lemma(tokens[adj_pos], 'національний') and lh.has_lemma(tokens[adj_pos - 1], 'перший') \
            and _upper0(tokens[adj_pos]) and _upper0(tokens[adj_pos - 1]):
        return True

    if java_equals_ignore_case(tokens[adj_pos].get_clean_token(), 'голому') \
            and java_equals_ignore_case(tokens[noun_pos].get_clean_token(), 'сорочка'):
        return True

    # (ні)чого доброго
    if adj_pos > 1 and java_equals_ignore_case(tokens[adj_pos].get_clean_token(), 'доброго') \
            and _P('(ні)?чого').fullmatch(tokens[adj_pos - 1].get_clean_token()):
        return True

    if adj_pos > 1 and _P('(?iu)середньому|цілому|основному|подальшому').fullmatch(tokens[adj_pos].get_clean_token()) \
            and _P('(?iu)[ву]').fullmatch(tokens[adj_pos - 1].get_clean_token()):
        return True

    if lh.has_lemma_pos(tokens[adj_pos], ('бережений',), _P('adj:m:v_rod.*')) \
            and lh.has_lemma_pos(tokens[noun_pos], ('бог',), _P('noun:anim:m:v_naz.*')):
        return True

    if lh.has_lemma_pos(tokens[adj_pos], ('кожний',), _P('adj:f:v_naz.*')) \
            and lh.has_lemma_pos(tokens[noun_pos], ('вага', 'маса', 'вартість', 'потужність', 'тривалість',
                                                    'чисельність', 'номінал', 'наклад'),
                                 _P('noun:inanim:.:v_oru.*')):
        return True

    #  в день Хрещення Господнього священики
    if lh.has_lemma(tokens[adj_pos], ('божий', 'господній', 'Христовий')) and _upper0(tokens[adj_pos]):
        return True

    # князівством Литовським подоляни
    if adj_pos > 1 and pth.has_pos_tag_part(tokens[adj_pos - 1], 'noun') and _upper0(tokens[adj_pos]) \
            and not java_disjoint(master_inflections, lh.get_noun_inflections(tokens[adj_pos - 1].readings)):
        return True

    # 5-а клас
    if _P('([1-9]|1[0-2])[‘-][а-д]').fullmatch(adj_atr.token) and lh.has_lemma(tokens[noun_pos], 'клас'):
        return True

    # Першими голодування оголосили
    # одним із перших
    if noun_pos > 1 and lh.has_lemma(adj_atr, ('перший',)) \
            and not lh.has_lemma_part_pos(tokens[noun_pos], FAKE_FEM_LIST, 'noun:inanim:m:'):
        return True

    # абзац другий частини першої
    # пункт третій рішення міськради
    if adj_pos > 1 and noun_pos < n - 1 \
            and pth.has_pos_tag(adj_atr, _P('adj:[mf]:.*numr.*|number.*')) \
            and pth.has_pos_tag(slave_token_readings, _P('noun:inanim:.:v_rod.*')) \
            and lh.has_lemma(tokens[adj_pos - 1], ('абзац', 'розділ', 'пункт', 'підпункт', 'частина', 'стаття')):
        return True

    # статтю 6-ту закону
    if adj_pos > 1 and pth.has_pos_tag_part(adj_atr, 'num') and lh.has_lemma(tokens[adj_pos - 1], 'стаття') \
            and not java_disjoint(master_inflections, lh.get_noun_inflections(tokens[adj_pos - 1].readings)):
        return True

    # лава запасних партії
    if adj_pos > 1 and tokens[adj_pos].token == 'запасних' and lh.has_lemma(tokens[adj_pos - 1], 'лава'):
        return True

    # старший зміни
    if tokens[noun_pos].get_clean_token() in ('зміни', 'групи') and lh.has_lemma(tokens[adj_pos], 'старший'):
        return True

    # на повну людей розкрутили
    if adj_pos > 1 and tokens[adj_pos].token == 'повну' and java_equals_ignore_case(tokens[adj_pos - 1].token, 'на'):
        return True

    # у Другій світовій участь
    if adj_pos > 1 and lh.has_lemma_part_pos(tokens[adj_pos], ('світовий',), ':f:') \
            and lh.has_lemma_part_pos(tokens[adj_pos - 1], ('другий', 'перший'), ':f:'):
        return True

    # знайдений увечері понеділка
    if noun_pos > 1 and lh.has_lemma(tokens[noun_pos - 1], ('увечері', 'уранці', 'ввечері', 'вранці')) \
            and pth.has_pos_tag(tokens[noun_pos], _P('noun.*v_rod.*')):
        return True

    # площею 100 кв. м
    # довжиною до 500
    if noun_pos < n - 1 \
            and tokens[noun_pos].token in ('площею', "об'ємом", 'довжиною', 'висотою', 'зростом', 'вагою') \
            and pth.has_pos_tag(tokens[noun_pos + 1], 'prep.*|.*num.*'):
        return True

    # 10 метрів квадратних води
    if adj_pos > 1 and lh.has_lemma(tokens[adj_pos - 1], _P('.*метр.*')) \
            and lh.has_lemma(tokens[adj_pos], _P('квадратний|кубічний')) \
            and pth.has_pos_tag_part(tokens[noun_pos], 'v_rod'):
        return True

    # молодшого гвардії сержанта
    if noun_pos < n - 1 and tokens[noun_pos].token == 'гвардії' and pth.has_pos_tag(tokens[noun_pos + 1], 'noun.*') \
            and not java_disjoint(master_inflections, lh.get_noun_inflections(tokens[noun_pos + 1].readings)):
        return True

    # 200% річних прибутку
    if adj_pos > 1 and tokens[adj_pos - 1].token.endswith('%') and tokens[adj_pos].token == 'річних':
        return True

    # пасли задніх
    if adj_pos > 1 and lh.has_lemma(tokens[adj_pos - 1], 'пасти') and tokens[adj_pos].token == 'задніх':
        return True

    # не мати рівних
    if adj_pos > 1 and lh.has_lemma(tokens[adj_pos - 1], 'мати') and tokens[adj_pos].token == 'рівних':
        return True

    # taken care by barbarism rule
    # на манер
    if adj_pos > 1 and tokens[noun_pos].token == 'манер' and java_equals_ignore_case(tokens[adj_pos - 1].token, 'на'):
        return True

    # taken care by barbarism rule
    # усі до єдиного
    if adj_pos > 2 and tokens[adj_pos].token == 'єдиного' and tokens[adj_pos - 1].token == 'до' \
            and lh.has_lemma_part_pos(tokens[adj_pos - 2], ('весь', 'увесь'), ':p:'):
        return True

    # сильні світу цього
    if noun_pos < n - 1 and tokens[noun_pos].get_clean_token() in ('миру', 'світу') \
            and (lh.has_lemma(adj_atr, ('сильний', 'могутній', 'великий'))
                 or lh.has_lemma_part_pos(tokens[noun_pos + 1], ('цей', 'сей'), ':m:v_rod')):
        return True

    # колишня Маяковського
    if lh.has_lemma_pos(tokens[adj_pos], ('колишній', 'тодішній', 'теперішній', 'нинішній'), _P('adj.*:f:.*')) \
            and _upper0(tokens[noun_pos]):
        return True

    # імені Шевченка
    # 4-й Запорізький ім. гетьмана Б. Хмельницького
    if noun_pos < n - 1 and tokens[noun_pos].token in ('ім.', 'імені', 'ордена'):
        return True

    # на дівоче Анна
    if tokens[adj_pos].token == 'дівоче' and pth.has_pos_tag_part(tokens[noun_pos], 'name'):
        return True

    # вольному воля
    if adj_atr.token.lower() in ('вольному', 'вільному') and tokens[noun_pos].token == 'воля':
        return True

    # порядок денний
    if adj_pos > 1 and lh.has_lemma(adj_atr, 'денний') and lh.has_lemma(tokens[adj_pos - 1], 'порядок') \
            and not java_disjoint(master_inflections, lh.get_noun_inflections(tokens[adj_pos - 1].readings)):
        return True

    # ------------------------

    # Вони здатні екскаватором переорювати
    if lh.has_lemma(tokens[adj_pos], ('здатний', 'змушений', 'винний', 'повинний', 'готовий', 'спроможний')):
        return True

    # протягом минулих травня – липня
    if noun_pos < n - 2 and pth.has_pos_tag(adj_atr, 'adj:p:.*') \
            and _P('[—–-]').fullmatch(tokens[noun_pos + 1].token) \
            and pth.has_pos_tag(tokens[noun_pos + 2], '(adj|noun).*') \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True

    # моїх маму й сестер
    if noun_pos < n - 2 and pth.has_pos_tag(adj_atr, 'adj:p:.*') and _forward_conj_find(tokens, noun_pos + 1, 2) \
            and has_overlap_ignore_gender(master_inflections, slave_inflections, 'p', None):
        return True

    # зв'язаних ченця з черницею
    # на зарубаних матір з двома синами
    if noun_pos < n - 2 and pth.has_pos_tag(adj_atr, 'adj:p:.*') and tokens[noun_pos + 1].token in ('з', 'із', 'зі') \
            and pth.has_pos_tag(tokens[noun_pos + 2], '(noun|numr).*:v_oru.*') \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True

    # навчальної та середньої шкіл
    if adj_pos > 2 and pth.has_pos_tag(tokens[noun_pos], 'noun:.*:p:.*') \
            and (_reverse_conj_find(tokens, adj_pos - 1, 3) or _reverse_conj_adv_find(tokens, adj_pos - 1, 3)) \
            and has_overlap_ignore_gender(master_inflections, slave_inflections, None, 'p') \
            and lh.reverse_search(tokens, adj_pos - 2, 100, None, _P('(adj|numr).*')):
        return True

    # Большого та Маріїнського театрів
    # Пляжі 3, 4 і 5-ї категорій
    if adj_pos > 2 and pth.has_pos_tag(tokens[noun_pos], 'noun:.*:p:.*') \
            and _reverse_conj_find2(tokens, adj_pos - 1, 3) \
            and has_overlap_ignore_gender(master_inflections, slave_inflections, None, 'p'):
        return True

    # ні у методологічному, ні у практичному аспектах
    if adj_pos > 6 and pth.has_pos_tag(tokens[noun_pos], 'noun:.*:p:.*') \
            and pth.has_pos_tag(tokens[adj_pos], 'adj:.*') and pth.has_pos_tag(tokens[adj_pos - 1], 'prep.*') \
            and lh.has_lemma(tokens[adj_pos - 2], ('ні', 'ані', 'хоч', 'що', 'як')) \
            and tokens[adj_pos - 3].token == ',' \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True

    after_predic_verb_tags = _P('.*(inf|past:n|futr:s:3).*')
    if noun_pos < n - 1 and pth.has_pos_tag_part(tokens[noun_pos], 'predic') \
            and (pth.has_pos_tag(tokens[noun_pos + 1], after_predic_verb_tags)
                 or noun_pos < n - 2 and pth.has_pos_tag_start(tokens[noun_pos + 1], 'adv')
                 and pth.has_pos_tag(tokens[noun_pos + 2], after_predic_verb_tags)):
        return True

    # на проурядову і, здається, пропрезидентську частини
    if adj_pos > 5 and pth.has_pos_tag(tokens[noun_pos], 'noun:.*:p:.*') \
            and pth.has_pos_tag(tokens[adj_pos], 'adj:.*') and tokens[adj_pos - 1].token == ',' \
            and ((tokens[adj_pos - 3].token == ','
                  and tokens[adj_pos - 4].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA
                  and not pth.has_pos_tag(tokens[adj_pos - 2], _VERB_NOT_INSERT_PATTERN))
                 or (tokens[adj_pos - 4].token == ','
                     and tokens[adj_pos - 5].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA
                     and not pth.has_pos_tag(tokens[adj_pos - 2], _VERB_NOT_INSERT_PATTERN)
                     and not pth.has_pos_tag(tokens[adj_pos - 3], _VERB_NOT_INSERT_PATTERN))) \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True

    # коринфський з іонійським ордери
    if adj_pos > 2 and pth.has_pos_tag(tokens[noun_pos], 'noun:.*:p:.*') \
            and _P('з|із|зі').fullmatch(tokens[adj_pos - 1].token) \
            and pth.has_pos_tag(tokens[adj_pos], 'adj.*v_oru.*') \
            and has_overlap_ignore_gender(lh.get_adj_inflections(tokens[adj_pos - 2].readings), slave_inflections):
        return True

    # на довгих півстоліття
    if pth.has_pos_tag(adj_atr, 'adj:p:v_rod.*') and tokens[noun_pos].token.startswith('пів') \
            and pth.has_pos_tag(tokens[noun_pos], 'noun.*v_rod.*'):
        return True

    # розділеного вже чверть століття
    # створених близько чверті століття
    if noun_pos < n - 1 and pth.has_pos_tag(adj_atr, _P('adj:p:v_(rod|naz).*|adj.*adjp.*')) \
            and lh.has_lemma(tokens[noun_pos], ('чверть', 'третина')) \
            and pth.has_pos_tag(tokens[noun_pos + 1], 'noun.*v_rod.*'):
        return True

    # заклопотані чимало людей
    # NOTE: мало abmigs with verb
    if pth.has_pos_tag_part(adj_atr, 'adjp') \
            and lh.has_lemma(tokens[noun_pos - 1], ('чимало', 'багато', 'небагато', 'немало', 'обмаль')) \
            and pth.has_pos_tag(tokens[noun_pos], 'noun.*:p:v_rod.*'):
        return True

    # присудок ж.р. + професія ч.р.
    if adj_atr.token in ('переконана', 'впевнена', 'упевнена', 'годна', 'ладна', 'певна', 'причетна', 'обрана',
                         'призначена') \
            and pth.has_pos_tag(tokens[noun_pos], 'noun:anim:m:v_naz.*'):
        return True

    # До останніх італійці ставляться
    if adj_pos > 1 and noun_pos < n - 1 and lh.has_lemma(tokens[adj_pos], 'останній') \
            and pth.has_pos_tag(tokens[adj_pos - 1], 'prep.*') and pth.has_pos_tag(tokens[noun_pos], 'noun.*v_naz.*') \
            and not lh.has_lemma(tokens[noun_pos], ('час', 'путь', 'день', 'момент', 'барель', 'слово')):
        return True

    # представник останньої Василь Бердников відповів
    if adj_pos > 1 and noun_pos < n - 1 and lh.has_lemma_pos(tokens[adj_pos], ('останній',), _P('adj:.:v_rod.*')) \
            and pth.has_pos_tag(tokens[adj_pos - 1], 'noun.*v_naz.*') \
            and pth.has_pos_tag(tokens[noun_pos], 'noun.*v_naz.*'):
        return True

    # чинних станом на
    if noun_pos < n - 1 and tokens[noun_pos].token == 'станом' and tokens[noun_pos + 1].token == 'на':
        return True

    # pron section

    # на таку Богом забуту
    if pth.has_pos_tag_part(tokens[adj_pos], 'pron') \
            and java_equals_ignore_case(tokens[noun_pos].get_clean_token(), 'богом'):
        return True

    # той родом з
    if lh.has_lemma(tokens[adj_pos], 'той') \
            and tokens[noun_pos].get_clean_token().lower() in ('родом', 'кулею', 'розміром'):
        return True

    # такого світ ще не бачив
    if tokens[adj_pos].get_clean_token().lower() in ('таке', 'такого') \
            and pth.has_pos_tag(tokens[noun_pos], _P('noun.*:v_naz.*')) \
            and Match().target(Condition.postag(_P('verb.*'))).limit(2) \
            .skip(Condition.postag(_P('(part|adv).*'))).m_after(tokens, noun_pos + 1) > 0:
        return True

    # той мантію надів
    if noun_pos < n - 1 and tokens[adj_pos].get_clean_token().lower() == 'той' \
            and pth.has_pos_tag(tokens[noun_pos], _P('noun.*:v_(zna|oru).*')) \
            and pth.has_pos_tag_start(tokens[noun_pos + 1], 'verb'):
        return True

    # що таке звук
    if adj_pos > 1 and tokens[adj_pos].token == 'таке' and lh.reverse_search(tokens, adj_pos - 1, 3, _P('що'), None):
        return True

    if java_equals_ignore_case(tokens[adj_pos].token, 'таких') \
            and (pth.has_pos_tag_part(tokens[noun_pos], ':p:v_naz')
                 or tokens[noun_pos].get_clean_token().lower() in ('меншість', 'більшість')):
        return True

    # постійно на рівних міністри, президенти
    if adj_pos > 1 and tokens[adj_pos].token == 'рівних' and java_equals_ignore_case(tokens[adj_pos - 1].token, 'на'):
        return True

    # польські зразка 1620—1650 років
    if noun_pos < n - 1 and tokens[noun_pos].token == 'зразка':
        return True

    # три зелених плюс два червоних
    if tokens[noun_pos].token in ('мінус', 'плюс'):
        return True

    # важкими пару років
    # неконституційними низку законів
    # природний тисячею років підтверджений
    if noun_pos < n - 1 \
            and lh.has_lemma(tokens[noun_pos], ('пара', 'низка', 'ряд', 'купа', 'більшість', 'десятка', 'сотня',
                                                'тисяча', 'мільйон')) \
            and (pth.has_pos_tag(tokens[noun_pos + 1], 'noun.*?:p:v_rod.*')
                 or (noun_pos < n - 2 and pth.has_pos_tag(tokens[noun_pos + 1], 'adj:p:v_rod.*')
                     and pth.has_pos_tag(tokens[noun_pos + 2], 'noun.*?:p:v_rod.*'))):
        return True

    # разів (у) десять
    if noun_pos < n - 1 and lh.has_lemma_pos(tokens[noun_pos], ('раз',), _P('.*p:v_(naz|rod).*')) \
            and (pth.has_pos_tag(tokens[noun_pos + 1], 'number|numr:p:v_naz|noun.*?:p:v_naz.*:numr.*')
                 or pth.has_pos_tag_part(tokens[noun_pos + 1], 'prep')):
        return True

    # років 6, відсотків зо два
    if noun_pos < n - 1 and lh.has_lemma_pos(tokens[noun_pos], lh.TIME_PLUS_LEMMAS, _P('noun.*?p:v_(naz|rod).*')) \
            and (pth.has_pos_tag(tokens[noun_pos + 1], _NUMBER_V_NAZ)
                 or (noun_pos < n - 2
                     and lh.has_lemma_part_pos(tokens[noun_pos + 1], ('на', 'за', 'з', 'із', 'зо', 'через', 'під'),
                                               'prep')
                     and pth.has_pos_tag(tokens[noun_pos + 2], _NUMBER_V_NAZ))):
        return True

    # осіб на 30
    if noun_pos < n - 2 and lh.has_lemma_pos(tokens[noun_pos], ('особа',), _P('noun.*?p:v_(naz|rod).*')) \
            and lh.has_lemma_part_pos(tokens[noun_pos + 1], ('на', 'з', 'із', 'зо', 'під'), 'prep') \
            and pth.has_pos_tag(tokens[noun_pos + 2], _NUMBER_V_NAZ):
        return True

    # хвилини з 55-ї вірмени почали
    if adj_pos > 2 and lh.has_lemma(tokens[adj_pos - 2], lh.TIME_LEMMAS_SHORT) \
            and pth.has_pos_tag_start(tokens[adj_pos - 1], 'prep') and pth.has_pos_tag_part(tokens[adj_pos], 'num'):
        prep_governed_cases = lh.get_case_governments(tokens[adj_pos - 1], 'prep')
        if has_vidm_pos_tag(prep_governed_cases, tokens[adj_pos - 2]) \
                and has_vidm_pos_tag(prep_governed_cases, tokens[adj_pos]):
            return True

    # пофарбований рік тому
    if noun_pos < n - 1 and lh.has_lemma(tokens[noun_pos], lh.TIME_LEMMAS) \
            and lh.has_lemma(tokens[noun_pos + 1], 'тому'):
        return True

    # замість звичного десятиліттями
    if noun_pos < n - 1 and lh.has_lemma_pos(tokens[noun_pos], lh.TIME_PLUS_LEMMAS, _P('noun:inanim:p:v_oru.*')):
        return True

    # кількох десятих відсотка
    if lh.has_lemma(tokens[adj_pos], ('десятий', 'сотий', 'тисячний', 'десятитисячний', 'стотитисячний',
                                      'мільйонний', 'мільярдний')) \
            and pth.has_pos_tag(adj_atr, '.*:[fp]:.*') and pth.has_pos_tag(tokens[noun_pos], 'noun.*v_rod.*'):
        return True

    # два нових горнятка (див. #1 нижче)
    # два відомих імені
    # 33 народних обранці
    if adj_pos > 1 and noun_pos < n and pth.has_pos_tag(adj_atr, '.*:p:v_(rod|naz).*') \
            and lh.reverse_search(tokens, adj_pos - 1, 5, _DOVYE_TROYE, None) \
            and (pth.has_pos_tag(tokens[noun_pos], '.*(:p:v_naz|:n:v_rod).*')
                 or tokens[noun_pos].token in ('імені', 'ока')):
        return True

    # 1-3-й класи
    # на сьомому–восьмому поверхах
    if (_P('[0-9]+[—–-][0-9]+[–-][а-яіїєґ]{1,3}').fullmatch(adj_atr.get_clean_token())
            or (_P('.*[а-яїієґ][—–-].*').fullmatch(adj_atr.get_clean_token())
                and pth.has_pos_tag_part(adj_atr, 'numr'))) \
            and pth.has_pos_tag_part(slave_token_readings, ':p:') \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True
    # восьмого – дев’ятого класів
    if noun_pos > 2 and tokens[adj_pos - 1].token in ('–', '—') \
            and pth.has_pos_tag_part(adj_atr, 'num') and pth.has_pos_tag_part(tokens[adj_pos - 2], 'num') \
            and pth.has_pos_tag_part(slave_token_readings, ':p:') \
            and (pth.has_pos_tag_start(tokens[adj_pos - 2], 'number')
                 or has_overlap_ignore_gender(lh.get_adj_inflections(tokens[adj_pos - 2].readings),
                                              slave_inflections)) \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True

    # найближчі рік-два
    # понаднормові годину-півтори
    # суперкризовими січнем–лютим
    if pth.has_pos_tag(adj_atr, 'adj.*:p:.*') and _P('.*[—–-].*').fullmatch(tokens[noun_pos].token) \
            and (_first_lemma_part_in_time_plus(tokens[noun_pos])
                 # does not work for тиждень-два due to dynamic tagging returning singular
                 or has_overlap_ignore_gender(master_inflections, slave_inflections)):
        return True

    # Від наступних пари десятків
    if noun_pos < n - 1 and lh.has_lemma(tokens[noun_pos], 'пара') and pth.has_pos_tag(adj_atr, 'adj.*:p:.*') \
            and pth.has_pos_tag(tokens[noun_pos + 1], '.*:p:v_rod.*'):
        return True

    if noun_pos > 1 and pth.has_pos_tag_part(tokens[adj_pos - 1], 'num') \
            and pth.has_pos_tag(tokens[adj_pos], 'adj.*num.*'):
        # п'ять шостих світу
        if pth.has_pos_tag(tokens[adj_pos - 1], '(noun|numr).*') and pth.has_pos_tag(tokens[adj_pos], 'adj:p:v_rod.*'):
            # (вона й) дві других дівчини
            if lh.has_lemma(tokens[adj_pos], 'другий') and not lh.has_lemma(tokens[adj_pos - 1], 'один'):
                return False
            return True

        # одній восьмій
        if lh.has_lemma_pos(tokens[adj_pos - 1], ('один',), _P('numr:f:.*')) \
                and not java_disjoint(lh.get_numr_inflections(tokens[adj_pos - 1].readings),
                                      lh.get_adj_inflections(tokens[adj_pos].readings)):
            return True

    # 1/8-ї фіналу
    if noun_pos > 3 and tokens[adj_pos - 1].token == '/' and pth.has_pos_tag_part(tokens[adj_pos - 2], 'numb') \
            and has_overlap_ignore_gender(master_inflections, slave_inflections):
        return True

    # dates
    if pth.has_pos_tag_part(adj_atr, ':numr'):
        adj_token = adj_atr.token

        # Ставши 2003-го прем’єром
        if _P('([12][0-9])?[0-9][0-9][—–-](й|го|м|му)').fullmatch(adj_token) \
                or _P('([12][0-9])?[0-9]0[—–-](ті|тих|их|х)').fullmatch(adj_token) \
                or _P('([12][0-9])?[0-9][0-9][—–-]([12][0-9])?[0-9][0-9][—–-]'
                      '(й|го|м|му|ті|тих|их|х)').fullmatch(adj_token):
            return True
        # Призначений на 11-ту похід
        if noun_pos > 1 and pth.has_pos_tag_part(adj_atr, ':f:') \
                and lh.has_lemma(tokens[adj_pos - 1], ('на', 'в', 'у', 'за', 'о', 'до', 'після', 'близько', 'раніше')) \
                and not lh.has_lemma(tokens[noun_pos], ('хвилина', 'година')):
            return True
        # 11-й ранку
        if pth.has_pos_tag_part(adj_atr, ':f:') \
                and _P('ранку|дня|вечора|ночі|пополудня').fullmatch(tokens[noun_pos].token):
            return True
        # дев'яте травня
        if pth.has_pos_tag_part(adj_atr, ':n:') and lh.has_lemma_part_pos(tokens[noun_pos], lh.MONTH_LEMMAS, 'v_rod'):
            return True

    # обмежуючий власність, створивший історію
    # let simple replace rule take care of this
    if pth.has_pos_tag(adj_atr, '.*?adjp:actv.*:bad.*'):
        return True

    # нічого протизаконного жінка не зробила
    # нічого поганого людям не зробили
    # що нічим дієвим ініціативи не завершаться
    # писав про щось подібне Юрій
    if 2 < noun_pos <= n - 1 and lh.has_lemma(tokens[adj_pos - 1], ('ніщо', 'щось', 'ніхто', 'хтось')) \
            and not java_disjoint(lh.get_noun_inflections(tokens[adj_pos - 1].readings), master_inflections):
        return True

    # визнання неконституційним закону
    # визнання тут шкідливою орієнтацію
    if adj_pos > 1 and lh.rev_search(tokens, adj_pos - 1, _P('.*(ння|ття)'), None) \
            and pth.has_pos_tag(tokens[adj_pos], 'adj.*:v_oru.*') \
            and pth.has_pos_tag(tokens[noun_pos], 'noun:.*:v_rod.*') \
            and _gender_matches(master_inflections, slave_inflections, 'v_oru', 'v_rod'):
        return True

    verb_pos = lh.rev_search_idx(tokens, adj_pos - 1, _P('бути|ставати|стати|залишатися|залишитися'), None)
    if verb_pos != -1:
        if pth.has_pos_tag(adj_atr, 'adj.*v_naz.*adjp:pasv.*'):
            # був змушений
            # був заповнений відвідувачами
            if _gender_matches(master_inflections, slave_inflections, 'v_naz', 'v_naz'):
                return True
        elif pth.has_pos_tag(adj_atr, 'adj.*v_oru.*'):
            # була чинною заборона
            if pth.has_pos_tag(slave_token_readings, _P('noun.*v_naz.*')):
                if _gender_matches(master_inflections, slave_inflections, 'v_oru', 'v_naz'):
                    # не можуть бути толерантними ізраїльтяни
                    if pth.has_pos_tag_part(tokens[verb_pos], ':inf') \
                            or lh.verb_inflections_overlap(tokens[verb_pos].readings, tokens[noun_pos].readings):
                        return True
                # Стали дорожчими хліб чи бензин
                elif noun_pos < n - 1 and pth.has_pos_tag_part(tokens[adj_pos], 'adj:p:') \
                        and tokens[noun_pos + 1].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA:
                    return True
            # слід бути обережними туристам у горах
            elif pth.has_pos_tag(slave_token_readings, 'noun.*v_dav.*'):
                if _gender_matches(master_inflections, slave_inflections, 'v_oru', 'v_dav'):
                    return True

    verb_pos = lh.rev_search_idx(tokens, adj_pos - 1, None, 'verb.*')
    if verb_pos != -1:
        if pth.has_pos_tag(adj_atr, 'adj.*v_oru.*'):
            # визнали справедливою наставники обох команд
            if pth.has_pos_tag(slave_token_readings, 'noun.*v_naz.*') \
                    and lh.verb_inflections_overlap(tokens[verb_pos].readings, tokens[noun_pos].readings):
                return True

    # помальована в (усе) біле кімната
    if adj_pos > 2 \
            and tokens[adj_pos].token in ('біле', 'чорне', 'оранжеве', 'червоне', 'жовте', 'синє', 'зелене',
                                          'фіолетове') \
            and tokens[adj_pos - 1].token in ('в', 'у') and pth.has_pos_tag_part(tokens[adj_pos - 2], 'adjp:pasv'):
        if not java_disjoint(lh.get_adj_inflections(tokens[adj_pos - 2].readings), slave_inflections):
            return True
    if adj_pos > 3 and tokens[adj_pos].token in ('біле', 'чорне') and tokens[adj_pos - 1].token in ('усе', 'все') \
            and tokens[adj_pos - 2].token in ('в', 'у') and pth.has_pos_tag_part(tokens[adj_pos - 3], 'adjp:pasv'):
        if not java_disjoint(lh.get_adj_inflections(tokens[adj_pos - 3].readings), slave_inflections):
            return True

    # повторена тисячу разів
    if noun_pos < n - 1 and pth.has_pos_tag_part(adj_atr, 'adjp:pasv') \
            and tokens[noun_pos].token in ('тисячу', 'сотню', 'десятки') \
            and tokens[noun_pos + 1].token in ('разів', 'раз', 'років'):
        return True

    # покликана ще раз
    if java_equals_ignore_case(tokens[noun_pos].get_clean_token(), 'раз') \
            and java_equals_ignore_case(tokens[noun_pos - 1].token, 'ще'):
        return True

    if adj_pos > 2:
        # порівняно з попереднім
        if pth.has_pos_tag(adj_atr, 'adj.*v_oru.*') and lh.has_lemma(tokens[adj_pos - 2], ('порівняно', 'аналогічно')) \
                and lh.has_lemma(tokens[adj_pos - 1], _P('з|із|зі')):
            return True

        # наближена до сімейної форма
        if pth.has_pos_tag_part(tokens[adj_pos - 1], 'prep'):
            if pth.has_pos_tag(tokens[adj_pos - 2], '(adj|verb|part|noun|adv).*'):
                prep_governed_cases = lh.get_case_governments(tokens[adj_pos - 1], 'prep')
                if has_vidm_pos_tag(prep_governed_cases, tokens[adj_pos]):
                    # відрізнялася (б) від нинішньої ситуація
                    # відрізнялося від російського способом
                    # поряд з енергетичними Москва висувала
                    # на відміну від європейських санкції США
                    if ((pth.has_pos_tag_start(tokens[adj_pos - 2], 'verb')
                         or lh.has_lemma(tokens[adj_pos - 2], ('би', 'б')))
                        or tokens[adj_pos - 2].token.lower() in ('поряд', 'відміну', 'порівнянні')) \
                            and pth.has_pos_tag(tokens[noun_pos], 'noun.*v_(naz|zna|oru).*'):
                        return True

                    if not java_disjoint(lh.get_adj_inflections(tokens[adj_pos - 2].readings), slave_inflections):
                        return True

                    # тотожні із загальносоюзними герб і прапор
                    if noun_pos < n - 1 and pth.has_pos_tag_part(tokens[adj_pos], 'adj:p:') \
                            and tokens[noun_pos + 1].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA \
                            and pth.has_pos_tag_part(tokens[adj_pos - 2], 'adj:p:') \
                            and has_overlap_ignore_gender(lh.get_adj_inflections(tokens[adj_pos - 2].readings),
                                                          slave_inflections, 'p', None):
                        return True

    # adjp:pasv + adj:v_oru + noun (case governed by adjp)
    # підсвічений синім діамант
    if adj_pos > 1 and pth.has_pos_tag_part(tokens[adj_pos - 1], 'adjp:pasv') \
            and pth.has_pos_tag(tokens[adj_pos], 'adj.*v_oru.*') \
            and not java_disjoint(lh.get_adj_inflections(tokens[adj_pos - 1].readings), slave_inflections):
        return True

    # adjp:pasv + noun:v_oru
    # захищені законом (від образ)
    if pth.has_pos_tag_part(adj_atr, 'adjp:pasv') and pth.has_pos_tag_part(tokens[noun_pos], 'v_oru'):
        return True

    # Найнижчою частка таких є на Півдні
    # Слабшою критики вважають
    # розвинутою Україну назвати важко
    if not pth.has_pos_tag(tokens[adj_pos - 1], '.*adjp:pasv.*|prep.*') \
            and pth.has_pos_tag(adj_atr, 'adj.*v_oru.*') \
            and pth.has_pos_tag(slave_token_readings, 'noun.*v_(zna|naz).*'):
        v_pos = lh.token_search(tokens, noun_pos + 1, 'verb', None, None, lh.FORWARD)
        if 0 < v_pos <= noun_pos + 5:
            if pth.has_pos_tag(slave_token_readings, 'noun.*v_naz.*') \
                    or (lh.has_case_government(tokens[v_pos], 'v_zna')
                        and _gender_matches(master_inflections, slave_inflections, 'v_oru', 'v_zna')):
                return True

    # verb + adj:v_oru + noun:v_zna
    # зроблять неможливою ротацію влади
    if adj_pos > 1 and pth.has_pos_tag(adj_atr, 'adj:.:v_oru.*') \
            and pth.has_pos_tag(slave_token_readings, '.*v_zna.*') \
            and _gender_matches(master_inflections, slave_inflections, 'v_oru', 'v_zna'):
        v_pos = lh.token_search(tokens, adj_pos - 1, _VERB_ADVP_PATTERN, None, None, lh.REVERSE)
        if v_pos > 0 and v_pos >= adj_pos - 3:
            if lh.has_case_government(tokens[v_pos], _VERB_ADVP_PATTERN, 'v_oru') \
                    and lh.has_case_government(tokens[v_pos], _VERB_ADVP_PATTERN, 'v_zna'):
                return True

    # verb + adv + adj:v_oru + noun:v_zna
    # робив неймовірно високими шанси
    if adj_pos > 2 and pth.has_pos_tag(tokens[adj_pos - 1], _P('adv(?!p).*')) \
            and lh.has_case_government(tokens[adj_pos - 2], _VERB_ADVP_PATTERN, 'v_oru') \
            and pth.has_pos_tag_part(adj_atr, 'v_oru') and pth.has_pos_tag(slave_token_readings, '.*v_zna.*') \
            and _gender_matches(master_inflections, slave_inflections, 'v_oru', 'v_zna'):
        return True

    if case_government_matches(adj_token_readings, slave_inflections):
        if noun_pos < n - 1 and pth.has_pos_tag_part(tokens[noun_pos + 1], 'noun:'):
            # Нав’язаний Австрії коаліцією
            # будуть вдячні державі Україна
            # мають бути підпорядковані служінню
            # радий присутності генерала
            if pth.has_pos_tag(tokens[noun_pos + 1], 'noun.*v_(rod|oru|naz|dav).*'):
                return True
            # Нав’язаний Австрії нейтралитет
            slave2_inflections = lh.get_noun_inflections(tokens[noun_pos + 1].readings)
            if not java_disjoint(master_inflections, slave2_inflections):
                return True
        else:
            # Нав’язаний Австрії,
            return True

    # альтернативну олігархічній модель
    # альтернативні газовому варіанти
    if adj_pos > 1 and pth.has_pos_tag_part(tokens[adj_pos - 1], 'adj') \
            and case_government_matches(tokens[adj_pos - 1].readings, master_inflections):
        pre_adj_inflections = lh.get_adj_inflections(tokens[adj_pos - 1].readings)
        if not java_disjoint(pre_adj_inflections, slave_inflections):
            return True

    # not an exception
    return False


def _first_lemma_part_in_time_plus(atr):
    lemma = atr.readings[0].lemma
    if lemma is None:
        return False
    parts = _P('[—–-]').split(lemma)
    while len(parts) > 1 and parts[-1] == '':
        parts.pop()
    return parts[0] in lh.TIME_PLUS_LEMMAS


def _gender_matches(master_inflections, slave_inflections, master_case_filter, slave_case_filter):
    for m in master_inflections:
        for s in slave_inflections:
            if (master_case_filter is None or m.case == master_case_filter) \
                    and (slave_case_filter is None or s.case == slave_case_filter) and s.gender == m.gender:
                return True
    return False


def _reverse_conj_adv_find(tokens, pos, depth):
    i = pos
    while i > pos - depth and i >= 2:
        if tokens[i].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA \
                and (pth.has_pos_tag(tokens[i - 1], 'adv(?!p).*')
                     or pth.has_pos_tag(tokens[i + 1], '(adv(?!p)|part).*')):
            return True
        if pth.has_pos_tag_part(tokens[i], 'verb'):
            return False
        i -= 1
    return False


_ADJ_NUMR_CONJ = jregex.compile('(adj|numr|conj:coord).*')
_ADJ_CONJ_NUM_PREP_ADV = jregex.compile('(adj|conj:coord|num|prep|adv(?!p)).*')
_ADJ_NUMR = jregex.compile('adj.*?numr.*')
_ENDS_WITH_DASH = jregex.compile('.*[–-]')
_CLOSING = jregex.compile('[)»”]')
_NOUN_ADJ_NUM_ADV = jregex.compile('(noun|adj|num|adv(?!p)).*')
_QUOTE_CHARS = jregex.compile('["«“„]')
_NOUN_ADJ_PREP_ADV_LAT = jregex.compile('(noun|adj|prep|adv(?!p)|number:latin).*')


def _reverse_conj_find(tokens, pos, depth):
    i = pos
    while i > pos - depth and i >= 1:
        if tokens[i].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA:
            if i < 2 or not pth.has_pos_tag(tokens[i - 1], _ADJ_NUMR_CONJ):
                return False
            return True
        if i >= 1 and not pth.has_pos_tag(tokens[i - 1], _ADJ_CONJ_NUM_PREP_ADV) and tokens[i - 1].token != ',':
            return False
        i -= 1
    return False


def _is_non_plural_a(tokens, pos):
    """TokenAgreementNounVerbExceptionHelper.isNonPluralA"""
    # both Cyrillic and Latin :(
    return (tokens[pos].token == 'а' or tokens[pos].token == 'a') \
        and not lh.has_lemma(tokens[pos + 1], ('також', 'потім', 'пізніше'))


def _reverse_conj_find2(tokens, pos, depth):
    i = pos
    while i > pos - depth and i >= 1:
        if tokens[i].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA:
            if _is_non_plural_a(tokens, i):
                return False
            if i < 2 or (((not tokens[i - 1].has_pos_tag('number') or not pth.has_pos_tag(tokens[i + 1], _ADJ_NUMR))
                          and tokens[i - 1].token != ',')
                         and not _ENDS_WITH_DASH.fullmatch(tokens[i - 1].token)  # дво- і тривимірний формати
                         and not _CLOSING.fullmatch(tokens[i - 1].token)  # 1-й (...) та 2-й ряди
                         and (tokens[i - 1].token != '/' or tokens[i].token != 'або')
                         and not pth.is_unknown_word(tokens[i - 1])):
                return False
            return True
        if i >= 1 and not pth.has_pos_tag(tokens[i - 1], _ADJ_CONJ_NUM_PREP_ADV) and tokens[i - 1].token != ',':
            return False
        i -= 1
    return False


def _check_text_in_sent(tokens, pos, text):
    words = text.split(' ')
    i = 0
    while i < len(words) and i + pos < len(tokens):
        if not java_equals_ignore_case(tokens[i + pos].token, words[i]):
            return False
        i += 1
    return True


def _forward_conj_find(tokens, pos, depth):
    i = pos
    while i < len(tokens) and i <= pos + depth:
        if tokens[i].token.lower() in CONJ_FOR_PLURAL_WITH_COMMA:
            # check 2nd part of plural
            if i < len(tokens) - 3 and _check_text_in_sent(tokens, i + 1, 'а також') \
                    and pth.has_pos_tag(tokens[i + 3], _NOUN_ADJ_NUM_ADV):
                return True
            if i == len(tokens) - 1 or (not pth.has_pos_tag(tokens[i + 1], _NOUN_ADJ_NUM_ADV)
                                        and not lh.is_capitalized(tokens[i + 1].get_clean_token())
                                        and not _QUOTE_CHARS.fullmatch(tokens[i + 1].token)):
                return False
            return True
        # for unknown last names: згадувані Костянтин Скоркін та Олена Заславська
        if not pth.has_pos_tag(tokens[i], _NOUN_ADJ_PREP_ADV_LAT) \
                and not lh.is_capitalized(tokens[i].get_clean_token()):
            return False
        i += 1
    return False


def case_government_matches(adj_token_readings, slave_inflections):
    cgm = lh.case_government_map()
    for lemma in dict.fromkeys(r.lemma for r in adj_token_readings):
        inflections = cgm.get(lemma)
        if inflections is not None:
            for inflection in slave_inflections:
                if inflection.case in inflections:
                    return True
    return False


def has_overlap_ignore_gender(master_inflections, slave_inflections, master_gender_filter=None,
                              slave_gender_filter=None):
    for m in master_inflections:
        if master_gender_filter is not None and not java_equals_ignore_case(m.gender, master_gender_filter):
            continue
        for s in slave_inflections:
            if slave_gender_filter is not None and not java_equals_ignore_case(s.gender, slave_gender_filter):
                continue
            if m.equals_ignore_gender(s):
                return True
    return False
