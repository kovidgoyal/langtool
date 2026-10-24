"""Port of org.languagetool.rules.uk.TokenAgreementPrepNounRule and
TokenAgreementPrepNounExceptionHelper."""

from ... import jregex
from ...analysis import AnalyzedToken
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import is_upper_case, java_equals_ignore_case
from . import helpers as lh
from . import pos_tag_helper as pth
from .helpers import Condition, Match, RuleException

QUOTES = ('«', '"', '„', '“')
Z_ZI_IZ = ('з', 'зі', 'із')
_Z_ZI_IZ_ZO = ('з', 'зі', 'із', 'зо')
_NOUN_ANIM_V_NAZ_PATTERN = jregex.compile('noun:anim:.:v_naz.*')
_VIDMINOK_SUBSTR = ':v_'
_VIDMINOK_REGEX = ':(v_[a-z]+)'
_REQ_ANIM_INANIM_REGEX = ':r(?:in)?anim'
_REQ_ANIM_INANIM_PATTERN = jregex.compile(_REQ_ANIM_INANIM_REGEX)
_V_TAG = jregex.compile(':v_[a-z]+')
_VIDM_NAME = jregex.compile('^.*' + _VIDMINOK_REGEX + '.*$')
_ENDS_WITH_LETTER_OR_DIGIT = jregex.compile('.*[а-яіїєґ0-9]')
_SHLYAKHOM = jregex.compile('шляхом|од|поруч|ради')
_PRON_POS_NOUN = jregex.compile('noun:unanim:.:v_rod.*pron.*')
_PRON_POS_NOUN_LEMMAS = ('вони', 'він', 'вона', 'воно')
_NYKH = jregex.compile('(них|нього|неї)(-[а-я]+)?')
_NEXT_AFTER_PRON = jregex.compile('(noun|adj|adv|part|num|conj:coord|noninfl).*')
_NEXT_AFTER_PRON_TOKEN = jregex.compile("[\"«„“/$€…]|[a-zA-Z'-]+")
_PRON_POS_ADJ = jregex.compile('adj.*pron:pos(?!:bad).*')
_PRON_POS_ADJ_LEMMAS = ('їх', 'його', 'її')
_U_INSTEAD_OF_A = jregex.compile('.*[ую]')
_NOUN_M_V_DAV = jregex.compile('noun.*?:m:v_dav.*')
_POVERKH = jregex.compile('.*поверх(ов|ів).*')
_APPROX_NUM = jregex.compile('noun:inanim:[fnm]:v_zna.*num.*|num.*')
_APPROX_NOUN = jregex.compile('noun:inanim:[mnf]:v_zna.*')
_APPROX_ADJ = jregex.compile('adj:[mnf]:v_zna.*')
_ZHE = jregex.compile('же?')
_COMMA_OR_PAREN = jregex.compile('[,(]')
_COMMA_OR_PAREN_CLOSE = jregex.compile('[,)]')

_APPROX_LEMMAS = (
    'розмір', 'величина', 'товщина', 'вартість', 'ріст', 'зріст', 'висота', 'глибина', 'діаметр', 'вага', 'обсяг',
    'площа', 'приблизно', 'десь', 'завбільшки', 'завширшки', 'завдовжки', 'завтовшки', 'заввишки', 'завглибшки',
    'накладом')
_APPROX_TAG = jregex.compile('noun.*v_oru.*|adv.*|part.*')
_LEMMAS = set(lh.TIME_LEMMAS) | set(lh.DISTANCE_LEMMAS) | set(lh.PSEUDO_NUM_LEMMAS) | {'ложка', 'ложечка'}


class State:
    __slots__ = ('prep_pos', 'prep_token_readings', 'zi_zna_removed', 'pos_tags_to_find')

    def __init__(self):
        self.prep_pos = 0
        self.prep_token_readings = None
        self.zi_zna_removed = False
        self.pos_tags_to_find = None


def has_vidm_pos_tag(pos_tags_to_find, token_readings):
    """TokenAgreementPrepNounRule.hasVidmPosTag (for AnalyzedTokenReadings or
    a list of AnalyzedToken)"""
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
        if _VIDMINOK_SUBSTR in pos_tag:
            vidminok_found = True
            for p in pos_tags_to_find:
                if p in pos_tag:
                    return True
    return not vidminok_found


def _get_multiword_token(atr):
    for r in atr.readings:
        if r.pos_tag is not None and r.pos_tag.startswith('<'):
            return r
    return None


class TokenAgreementPrepNounRule(Rule):
    """A rule that checks if preposition and a noun agree on inflection
    etc."""

    def __init__(self, messages, language):
        super().__init__()
        self.category = Categories.get('MISC', messages)
        self.ukrainian = language
        self.synthesizer = language.synthesizer

    def get_id(self):
        return 'UK_PREP_NOUN_INFLECTION_AGREEMENT'

    def get_description(self):
        return 'Узгодження прийменника та іменника у реченні'

    def get_short(self):
        return 'Узгодження прийменника та іменника'

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        state = None
        i = 0
        n = len(tokens)
        while True:
            i += 1
            if i >= n:
                break
            token_readings = tokens[i]
            pos_tag = token_readings.readings[0].pos_tag
            this_token = token_readings.get_clean_token()

            if tokens[i].get_clean_token() in QUOTES:
                continue

            if pos_tag is None or token_readings.immunized:
                state = None
                continue

            # часто вживають укр. В замість лат.: гепатит В
            # first token is always SENT_START
            if (i > 1 and len(this_token) == 1 and is_upper_case(this_token[0]) and token_readings.whitespace_before
                    and _ENDS_WITH_LETTER_OR_DIGIT.fullmatch(tokens[i - 1].token)):
                state = None
                continue

            multiword_req_token = _get_multiword_token(token_readings)
            if multiword_req_token is not None:
                if token_readings.get_clean_token().lower() in Z_ZI_IZ \
                        and multiword_req_token.lemma.startswith('згідно '):  # напр. "згідно з"
                    pos_tag = multiword_req_token.pos_tag
                    state = State()
                    state.prep_token_readings = token_readings
                    state.prep_pos = i
                    continue
                else:
                    if pos_tag.startswith('prep'):
                        state = None
                        continue
                    mw_pos_tag = multiword_req_token.pos_tag
                    if 'adv' not in mw_pos_tag and 'insert' not in mw_pos_tag:
                        state = None
                continue

            token = token_readings.get_clean_token()
            if pos_tag.startswith('prep'):
                prep = token.lower()
                # з понад тисячі
                if prep == 'понад':
                    continue
                if _SHLYAKHOM.fullmatch(prep):
                    state = None
                    continue
                state = State()
                state.prep_token_readings = token_readings
                state.prep_pos = i
                continue

            if state is None:
                continue

            # з Ван Дамом
            if this_token.lower() == 'ван':
                continue
            if this_token == 'Фон':
                continue
            # до та після
            if this_token.lower() == 'та':
                state = None
                continue

            # Do actual check

            state.pos_tags_to_find = {}
            prep = state.prep_token_readings.readings[0].lemma

            # замість Андрій вибрали Федір
            if prep == 'замість':
                state.pos_tags_to_find['v_naz'] = None
            # що за ганебна послідовність
            elif prep == 'за':
                if i > 1 and java_equals_ignore_case(tokens[state.prep_pos - 1].get_clean_token(), 'що'):
                    state.pos_tags_to_find['v_naz'] = None

            # писав про «Сновиди»
            # замість «урані»
            if tokens[i - 1].get_clean_token() in QUOTES:
                if lh.is_capitalized(tokens[i].get_clean_token()) or \
                        java_equals_ignore_case(state.prep_token_readings.get_clean_token(), 'замість'):
                    state = None
                    continue
                state.pos_tags_to_find['v_naz'] = None

            expected_cases = list(lh.get_case_governments(state.prep_token_readings, 'prep'))

            # згідно з документа
            if prep in _Z_ZI_IZ_ZO:
                if java_equals_ignore_case('нізвідки', tokens[i].get_clean_token()):
                    state = None
                    continue
                if prep in Z_ZI_IZ and i >= 3 and java_equals_ignore_case(tokens[i - 2].get_clean_token(), 'згідно'):
                    expected_cases = ['v_oru']
                elif not self._is_likely_approx_with_zi(tokens, i, state):
                    if 'v_zna' in expected_cases:
                        expected_cases.remove('v_zna')
                    state.zi_zna_removed = True

            if 'v_inf' in expected_cases:
                expected_cases.remove('v_inf')  # we don't care about rv_inf here
            for c in expected_cases:
                state.pos_tags_to_find[c] = None

            exception = get_exception_strong(tokens, i, state.prep_token_readings)
            if exception.type == RuleException.exception:
                state = None
                continue
            if exception.type == RuleException.skip_type:
                i += exception.skip
                continue

            if pth.has_pos_tag_part(token_readings, ':v_'):
                # домовився за їх. - ненормативна форма
                pron_pos_noun_readings = [r for r in token_readings.readings
                                          if pth.has_pos_tag(r, _PRON_POS_NOUN) and r.lemma in _PRON_POS_NOUN_LEMMAS]

                # нього-таки тощо
                if pron_pos_noun_readings and not _NYKH.fullmatch(this_token.lower()):
                    if i < n - 1 and (pth.has_pos_tag(tokens[i + 1], _NEXT_AFTER_PRON) or
                                      _NEXT_AFTER_PRON_TOKEN.fullmatch(_default_if_blank(
                                          tokens[i + 1].get_clean_token()))):
                        # test next
                        # при його ділянці
                        continue
                    else:
                        insert_end_pos = _find_insert_end(state.prep_token_readings, tokens, i + 1, True)
                        if insert_end_pos > 0:
                            i = insert_end_pos
                            continue
                        rule_matches.append(self._create_rule_match(state, sentence, tokens, i))
                        state = None
                        continue

                pron_pos_adj_readings = [r for r in token_readings.readings
                                         if pth.has_pos_tag(r, _PRON_POS_ADJ) and r.lemma in _PRON_POS_ADJ_LEMMAS]

                # to detect: завдяки його зусиллі
                if pron_pos_adj_readings:
                    if not has_vidm_pos_tag(state.pos_tags_to_find, pron_pos_adj_readings):
                        rule_matches.append(self._create_rule_match(state, sentence, tokens, i))
                        state = None
                        continue
                    if i < n - 1:
                        # test next
                        # при їхній ділянці
                        continue
                elif this_token == 'їх':
                    rule_matches.append(self._create_rule_match(state, sentence, tokens, i))
                    state = None
                    continue

                if has_vidm_pos_tag(state.pos_tags_to_find, token_readings):
                    state = None
                    continue

                exception = get_exception_non_infl(tokens, i, state)
                if exception.type == RuleException.exception:
                    state = None
                    continue
                if exception.type == RuleException.skip_type:
                    i += exception.skip
                    continue

                exception = get_exception_infl(tokens, i, state)
                if exception.type == RuleException.exception:
                    state = None
                    continue
                if exception.type == RuleException.skip_type:
                    i += exception.skip
                    continue

                rule_matches.append(self._create_rule_match(state, sentence, tokens, i))
            else:  # no _v found
                exception = get_exception_non_infl(tokens, i, state)
                if exception.type == RuleException.exception:
                    state = None
                    continue
                if exception.type == RuleException.skip_type:
                    i += exception.skip
                    continue
            state = None

        return rule_matches

    def _is_likely_approx_with_zi(self, tokens, i, state):
        # з 2-поверховий, з 10-поверхівку
        if _POVERKH.fullmatch(tokens[i].get_clean_token()):
            return True
        return (pth.has_pos_tag(tokens[i], _APPROX_NUM)
                or lh.has_lemma_pos(tokens[i], _LEMMAS, _APPROX_NOUN)
                or (i < len(tokens) - 1 and pth.has_pos_tag(tokens[i], _APPROX_ADJ)
                    and lh.has_lemma_pos(tokens[i + 1], _LEMMAS, _APPROX_NOUN))
                or lh.has_lemma_pos(tokens[state.prep_pos - 1], _APPROX_LEMMAS, _APPROX_TAG)
                or (i < len(tokens) - 1 and lh.has_lemma_pos(tokens[i + 1], _APPROX_LEMMAS, _APPROX_TAG)))

    def _create_rule_match(self, state, sentence, tokens, i):
        token_readings = tokens[i]
        token_string = token_readings.get_clean_token().lower()

        suggestions = []
        required_post_tags_regex = ':(' + '|'.join(state.pos_tags_to_find) + ')'
        for analyzed_token in token_readings.readings:
            old_pos_tag = analyzed_token.pos_tag
            if old_pos_tag is None:
                continue
            regex_to_apply = required_post_tags_regex
            m = _REQ_ANIM_INANIM_PATTERN.search(old_pos_tag)
            if m:
                regex_to_apply += m.group(0)
            else:
                regex_to_apply += '(?:' + _REQ_ANIM_INANIM_REGEX + ')?'
            pos_tag = jregex.java_replace(_V_TAG, regex_to_apply, old_pos_tag, 1)
            suggestions.extend(self.synthesizer.synthesize(analyzed_token, pos_tag, True))

        if suggestions:  # remove duplicates
            suggestions = list(dict.fromkeys(suggestions))

        req_vidminky_names = [pth.VIDMINKY_MAP.get(v) for v in state.pos_tags_to_find]

        found_vidminky_names = []
        for token in token_readings.readings:
            pos_tag2 = token.pos_tag
            if pos_tag2 is not None and _VIDMINOK_SUBSTR in pos_tag2:
                vidm_name = pth.VIDMINKY_MAP.get(jregex.java_replace(_VIDM_NAME, '$1', pos_tag2, 1))
                if vidm_name in found_vidminky_names:
                    if ':p:' in pos_tag2:
                        vidm_name = _jstr(vidm_name) + ' (мн.)'
                        found_vidminky_names.append(vidm_name)
                    # else skip dup
                else:
                    found_vidminky_names.append(vidm_name)

        msg = 'Прийменник «%s» вимагає іншого відмінка: %s, а знайдено: %s' % (
            state.prep_token_readings.token, ', '.join(map(_jstr, req_vidminky_names)),
            ', '.join(map(_jstr, found_vidminky_names)))

        if state.zi_zna_removed:
            msg += '. Але з.в. вимагається у випадках порівнянн предметів.'

        if 'v_rod' in state.pos_tags_to_find and _U_INSTEAD_OF_A.fullmatch(tokens[i].token) \
                and pth.has_pos_tag(token_readings.readings, _NOUN_M_V_DAV):
            msg += lh.USED_U_INSTEAD_OF_A_MSG
        elif token_string == 'їх':
            msg += '. Можливо, тут потрібно присвійний займенник «їхній» або нормативна форма р.в. «них»?'
            new_yih_postag = 'adj:p' + required_post_tags_regex + '.*'
            suggestions.extend(self.synthesizer.synthesize(
                AnalyzedToken('їхній', 'adj:m:v_naz.*:pron:pos', 'їхній'), new_yih_postag, True))
        elif token_string in ('його', 'її'):
            repl = 'нього' if token_string == 'його' else 'неї'
            msg += '. Можливо, тут потрібно присвійний займенник «' + repl + '»?'
            new_yih_postag = 'adj:p' + required_post_tags_regex + '.*'
            suggestions.extend(self.synthesizer.synthesize(
                AnalyzedToken('їхній', 'adj:m:v_naz.*:pron:pos', 'їхній'), new_yih_postag, True))
            suggestions.append(repl)
        elif java_equals_ignore_case(state.prep_token_readings.get_clean_token(), 'о'):
            for token in token_readings.readings:
                if pth.has_pos_tag(token, _NOUN_ANIM_V_NAZ_PATTERN):
                    msg += '. Можливо, тут «о» — це вигук і потрібно кличний відмінок?'
                    new_postag = token.pos_tag.replace('v_naz', 'v_kly')
                    for s in self.synthesizer.synthesize(token, new_postag, False):
                        if s != token.token and s not in suggestions:
                            suggestions.append(s)
                    break
        elif pth.has_pos_tag_start(tokens[i - 1], 'adv'):
            merged_token = state.prep_token_readings.get_clean_token() + tokens[i - 1].get_clean_token()
            merged_tagged = self.ukrainian.tagger.tag([merged_token])
            if pth.has_pos_tag_start(merged_tagged[0], 'adv'):
                msg += '. Можливо, прийменник і прислівник мають бути одним словом?'

        rm = RuleMatch(self, sentence, token_readings.start_pos, token_readings.end_pos, msg, self.get_short())
        rm.set_suggested_replacements(suggestions)
        return rm


def _jstr(s):
    return 'null' if s is None else s


def _default_if_blank(s):
    return '' if s is None or not s.strip() else s


def _find_insert_end(prep_token_readings, tokens, i, look_for_part):
    if i >= len(tokens) - 2:
        return -1
    next_pos = i
    token_readings = tokens[i]
    if i > len(tokens) - 2:
        return -1
    if _ZHE.fullmatch(token_readings.get_clean_token()):
        next_pos = i + 1
    if next_pos > len(tokens) - 3:
        return -1 if next_pos == i else next_pos - 1
    if token_readings.is_pos_tag_unknown and _COMMA_OR_PAREN.fullmatch(token_readings.get_clean_token()):
        comma_pos = lh.token_search(tokens, i + 1, None, _COMMA_OR_PAREN_CLOSE, None, lh.FORWARD)
        if i + 1 < comma_pos < i + 6 and comma_pos < len(tokens) - 1 \
                and tokens[comma_pos + 1].get_clean_token() != 'що':
            if token_readings.get_clean_token().replace('(', ')') == tokens[comma_pos].get_clean_token():
                return comma_pos
    return -1 if next_pos == i else next_pos - 1


# --- TokenAgreementPrepNounExceptionHelper ---

_NAMES = {"ім'я", 'прізвище'}
_NUMR_CASES = jregex.compile('.*v_(rod|dav|zna|oru|mis).*')
_NOUN_V_ROD = jregex.compile('noun.*?:.:v_rod.*')
_NAME_V_NAZ = jregex.compile('noun:anim:.:v_naz:prop:[fl]name.*')
_TY_VY = jregex.compile('ти|ви')
_SPRAVEDLYVOSTI = jregex.compile('(?iu)справедливості|об.єктивності')
_TIME_PLUS_P = jregex.compile('noun:inanim:p:v_(rod|zna).*')
_PRON_DAV = jregex.compile('noun.*v_dav.*:pron:(refl|pers).*')
_PRON_NEG = jregex.compile('noun.*v_(dav|oru).*:pron:neg.*')
_TIME_ADV = jregex.compile('сьогодні|[ву]чора|позавчора|(після)?завтра|тепер|зараз|нині|опівдня|опівночі|досі|навпаки')
_TIME_ADV2 = jregex.compile('сьогодні|[ву]чора|позавчора|(після)?завтра|тепер|зараз|нині|тоді|потім|щодень|повсякдень')
_TIME_ADV3 = jregex.compile('сьогодні|[ву]чора|позавчора|(після)?завтра')
_ZA_Z = jregex.compile('за|зі?|із')
_ADV = jregex.compile('adv.*')
_ADV_NOT_P = jregex.compile('adv(?!p).*')
_VERB_INF = jregex.compile('verb.*:inf.*')
_LYSH = jregex.compile('лиш(е(нь)?)?')
_PRON_DAV2 = jregex.compile('noun:(un)?anim:.:v_dav.*:pron.*')


def get_exception_infl(tokens, i, state):
    token_readings = tokens[i]
    token = token_readings.get_clean_token()
    token_lower = token.lower()
    prep = state.prep_token_readings.get_clean_token().lower()

    # на дивом уцілілій техніці
    if token == 'дивом':
        return RuleException(0)

    # в тисяча шістсот якомусь році
    if i < len(tokens) - 1 and token == 'тисяча' \
            and (pth.has_pos_tag_part(tokens[i + 1], 'numr') or lh.has_lemma(tokens[i + 1], 'якийсь')):
        return RuleException(0)
    # в дев'яносто восьмому
    if i < len(tokens) - 1 and pth.has_pos_tag_part(token_readings, 'numr') \
            and pth.has_pos_tag_part(token_readings, 'v_naz') and pth.has_pos_tag_part(tokens[i + 1], 'numr') \
            and pth.has_pos_tag(token_readings, _NUMR_CASES):
        return RuleException(1)

    if prep == 'на':
        # 1) на (свято) Купала, на (вулиці) Мазепи, на (вулиці) Тюльпанів
        if lh.is_capitalized(token) and pth.has_pos_tag(token_readings, _NOUN_V_ROD):
            return RuleException(RuleException.exception)
        if pth.has_pos_tag(token_readings, _NAME_V_NAZ) and (
                (i > 1 and tokens[i - 2].readings[0].token in _NAMES)
                or (i > 2 and tokens[i - 3].readings[0].lemma in _NAMES)):
            return RuleException(RuleException.exception)
        if _TY_VY.fullmatch(token_lower):
            return RuleException(RuleException.exception)
        # на Піп Іван
        if i < len(tokens) - 1 and token == 'Піп' and tokens[i + 1].get_clean_token() == 'Іван':
            return RuleException(RuleException.exception)
        # handled by xml rule
        if token_lower == 'манер':
            return RuleException(RuleException.exception)

    # справедливості заради слід зазначити
    if state.prep_pos > 1 and prep == 'заради':
        if _SPRAVEDLYVOSTI.fullmatch(tokens[state.prep_pos - 1].get_clean_token()):
            return RuleException(RuleException.exception)

    # TODO: temporary until we have better logic - skip
    # при їх виборі
    if prep == 'при':
        if token == 'їх':
            return RuleException(RuleException.skip_type)
    elif prep == 'з':
        if token == 'рана':
            return RuleException(RuleException.exception)
    elif prep == 'від':
        if java_equals_ignore_case(token, 'а') or token in ('рана', 'корки', 'мала'):
            return RuleException(RuleException.exception)
    elif prep == 'до':
        if java_equals_ignore_case(token, 'я') or token in ('корки', 'велика'):
            return RuleException(RuleException.exception)

    # exceptions
    if len(tokens) > i + 1:
        # від мінус 1 до плюс 1
        if (pth.has_pos_tag_start(tokens[i + 1], 'num') or tokens[i + 1].token == '$') \
                and token_lower in lh.PLUS_MINUS:
            return RuleException(RuleException.exception)

        # на мохом стеленому дні - пропускаємо «мохом»
        if pth.has_pos_tag(token_readings, 'noun.*?:v_oru.*') and tokens[i + 1].has_partial_pos_tag('adjp:pasv'):
            return RuleException(1)

        if token == 'святая' and tokens[i + 1].token == 'святих':
            return RuleException(RuleException.exception)

        if prep in ('через', 'на') \
                and lh.has_lemma_pos(token_readings, lh.TIME_PLUS_LEMMAS, _TIME_PLUS_P) \
                and (tokens[i + 1].has_partial_pos_tag('num')
                     # відсотки зо 3
                     or (i < len(tokens) - 2 and lh.has_lemma(tokens[i + 1], ('зо', 'з', 'із'))
                         and tokens[i + 2].has_partial_pos_tag('num'))):
            return RuleException(RuleException.exception)

        if pth.has_pos_tag(token_readings, _PRON_DAV) and tokens[i + 1].get_clean_token().startswith('подібн'):
            return RuleException(0)
        if token in ('усім', 'всім') and tokens[i + 1].get_clean_token().startswith('відом'):
            return RuleException(0)

        if prep.lower() == 'до' and token == 'схід' and tokens[i + 1].get_clean_token() == 'сонця':
            return RuleException(RuleException.exception)

        if len(tokens) > i + 2:
            # спиралося на місячної давнини рішення
            if pth.has_pos_tag(token_readings, 'adj:[mfn]:v_rod.*'):
                genders = pth.get_genders(token_readings, 'adj:[mfn]:v_rod.*')
                if pth.has_pos_tag(tokens[i + 1], 'noun.*?:[' + genders + ']:v_rod.*'):
                    return RuleException(1)

            if pth.has_pos_tag(token_readings, _PRON_NEG) and tokens[i + 1].get_clean_token() == 'не':
                return RuleException(RuleException.skip_type)

    return RuleException(RuleException.none)


def get_exception_strong(tokens, i, prep_token_readings):
    token_readings = tokens[i]
    token = token_readings.get_clean_token()
    token_lower = token.lower()
    prep = prep_token_readings.get_clean_token().lower()

    if prep in ('до', 'по'):
        if _TIME_ADV.fullmatch(token_lower):
            return RuleException(RuleException.exception)

    if prep in ('на', 'від', 'про'):
        if _TIME_ADV2.fullmatch(token_lower):
            return RuleException(RuleException.exception)

    if _ZA_Z.fullmatch(prep):
        if _TIME_ADV3.fullmatch(token_lower):
            return RuleException(RuleException.exception)

    if prep in ('в', 'у'):
        if token_lower == 'нікуди':
            return RuleException(RuleException.exception)

    # помилка: до не властиву йому функцію
    if i < len(tokens) - 1 and token == 'не' and pth.has_pos_tag_start(tokens[i + 1], 'ad'):
        return RuleException(0)

    # про чимало обмежень
    if i < len(tokens) - 1 and lh.has_lemma_pos(token_readings, lh.ADV_QUANT_PATTERN, _ADV):
        return RuleException(RuleException.exception)

    # лежить із сотня срібних
    if i < len(tokens) - 1 and prep in Z_ZI_IZ and lh.has_lemma(tokens[i], lh.PSEUDO_NUM_LEMMAS):
        return RuleException(RuleException.exception)

    # за цілком собі реалістичною соціальною
    if pth.has_pos_tag_all(token_readings.readings, _ADV_NOT_P):
        if i < len(tokens) - 1 and tokens[i + 1].get_clean_token() == 'собі':
            return RuleException(1)
        return RuleException(0)

    # замість вже самому засвоїти
    if prep == 'замість':
        if Match().target(Condition.postag(_VERB_INF)).limit(4).skip(Condition.token('можна').negate()) \
                .m_after(tokens, i + 1) > 0:
            return RuleException(RuleException.exception)

    # Усупереч не те що лихим
    if Match().token_line('не те').m_before(tokens, i) > 0:
        return RuleException(RuleException.exception)

    return RuleException(RuleException.none)


def get_exception_non_infl(tokens, i, state):
    token_readings = tokens[i]
    token = token_readings.get_clean_token()

    if pth.has_pos_tag_start(token_readings, 'part'):
        if lh.PART_INSERT_PATTERN.fullmatch(token.lower()):
            return RuleException(0)

    if _LYSH.fullmatch(token):
        return RuleException(0)

    if token == 'наприклад':
        return RuleException(0)

    if pth.has_pos_tag(token_readings, _ADV_NOT_P):
        # по швидко напруженим рукам
        if i < len(tokens) - 1 and pth.has_pos_tag_start(tokens[i + 1], 'adj') \
                and pth.has_pos_tag_part_all(token_readings, 'adv'):
            return RuleException(0)
        return RuleException(RuleException.exception)

    if len(tokens) > i + 1:
        # на лише їм відомому ...
        # на вже всім відомому ...
        if pth.has_pos_tag(tokens[i], _PRON_DAV2):
            if pth.has_pos_tag_start(tokens[i + 1], 'adj') and lh.has_case_government(tokens[i + 1], 'v_dav'):
                return RuleException(1)
            if len(tokens) > i + 2 and pth.has_pos_tag_start(tokens[i + 1], 'adv') \
                    and pth.has_pos_tag_start(tokens[i + 2], 'adj') and lh.has_case_government(tokens[i + 2], 'v_dav'):
                return RuleException(2)
    if len(tokens) > i + 2:
        # на нічого не вартий папірець
        if token == 'нічого' and tokens[i + 1].token == 'не' and pth.has_pos_tag_start(tokens[i + 2], 'adj'):
            return RuleException(1)
    return RuleException(RuleException.none)
