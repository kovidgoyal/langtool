"""Port of org.languagetool.tagging.uk.CompoundTagger (tagging of compound
words with hyphens by analyzing each part) and LetterEndingForNumericHelper.
CompoundDebugLogger only writes debug files when enabled with a system
property in Java, it is not ported (its calls are no-ops)."""

import functools

from ... import jregex
from ...analysis import AnalyzedToken
from ...rules.abstract_rules import java_hash_set_order
from ...tagging import TaggedWord
from ...tools import (is_capitalized_word, is_digit, is_lower_case, is_upper_case, java_equals_ignore_case,
                      java_split, java_string_hash, uppercase_first_char)
from . import helpers
from . import pos_tag_helper as pth

_c = jregex.compile

_TAG_ANIM = ':anim'
_TAG_INANIM = ':inanim'
_EXTRA_TAGS = _c(':bad')
_EXTRA_TAGS_DROP = _c(':(comp.|np|ns|slang|xp[1-9]|predic|insert)')
_EXTRA_TAGS_DROP_NONINFL = _c(':(comp.|np|ns|slang|xp[1-9]|insert)')
_NOUN_SING_V_ROD_REGEX = _c('noun.*?:[mfn]:v_rod.*')
_SING_REGEX_F = _c(':[mfn]:')
_O_ADJ_PATTERN = _c('.+?(о|[чшщ]е)')
_NUMR_ADJ_PATTERN = _c('.+?(одно|дво|ох|и)')
_DASH_PREFIX_LAT_PATTERN = _c('[a-zA-Z]{3,}|[α-ωΑ-Ω]')
_YEAR_NUMBER = _c('[12][0-9]{3}')
_NOUN_PREFIX_NUMBER = _c('[0-9]+')
_NOUN_WITH_INTERVAL_PREFIX_NUMBER = _c('([0-9]+[-–])?[0-9]+')
_NOUN_SUFFIX_NUMBER_LETTER = _c('[0-9][0-9А-ЯІЇЄҐ-]*')
_ADJ_PREFIX_NUMBER = _c('[0-9]+(,[0-9]+)?([-–—][0-9]+(,[0-9]+)?)?%?|(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})|І{2,3}')
_REQ_NUM_DVA_PATTERN = _c('(місн|томник|поверхів).{0,4}')
_REQ_NUM_DESYAT_PATTERN = _c('(класни[кц]|бальни[кц]|раундов|томн|томов|хвилин|десятиріч|кілометрів|річ).{0,4}')
_REQ_NUM_STO_PATTERN = _c('(річч|літт|метрів|грамов|тисячник).{0,3}')
_INTJ_PATTERN = _c('intj.*')
_NONINFL_PATTERN = _c('noninfl.*(onomat|predic).*')
_UKR_LETTERS_PATTERN = _c("[А-ЯІЇЄҐа-яіїєґ'-]+")
_GEO_V_NAZ = _c('noun:inanim:.:v_naz.*:geo.*')
_FNAME = _c('noun:anim:[mf].*fname.*')
_LNAME_V_NAZ = _c('noun:anim:[fm]:v_naz.*lname.*')
_LNAME_V_ROD = _c('noun:anim:[fm]:v_rod.*lname.*')
_NAME = _c('noun:anim:.*name.*')
_PROP_V_NAZ = _c('noun:inanim:.:v_naz.*prop.*')

_MNP_NAZ_REGEX = _c('.*?:[mnp]:v_naz.*')
_MNP_ZNA_REGEX = _c('.*?:[mnp]:v_zna.*')
_MNP_ROD_REGEX = _c('.*?:[mnp]:v_rod.*')

_STD_NOUN_TAG_REGEX = _c('noun:(?:in)?anim:(.):(v_...).*')
_ADJ_TAG_FOR_PO_ADV_MIS = 'adj:m:v_mis'
_ADJ_TAG_FOR_PO_ADV_NAZ = 'adj:m:v_naz'
_PREFIX_NO_DASH_POSTAG_PATTERN = _c('(noun|adj|adv)(?!.*pron).*')

# додаткові вкорочені прикметникові ліві частини, що не мають відповідного прикметника
_LEFT_O_ADJ = ('австро', 'адиго', 'американо', 'англо', 'афро', 'еко', 'індо', 'іспано', 'італо', 'історико',
               'києво', 'марокано', 'угро', 'японо', 'румуно')

LEFT_O_ADJ_INVALID = ('багато', 'мало', 'високо', 'низько', 'старо', 'важко', 'зовнішньо', 'внутрішньо', 'ново',
                      'середньо', 'південно', 'північно', 'західно', 'східно', 'центрально', 'ранньо', 'пізньо')

LEFT_O_ADJ_INVALID_PATTERN = _c('^(' + '|'.join(LEFT_O_ADJ_INVALID) + ')(.+)')

# TODO: чемпіонат світу-2014, людина року-2018, Червона рута-2011, Нова хвиля-2012, Фабрика зірок-2
_WORDS_WITH_YEAR = (
    'бюджет', 'вибори', 'гра', 'держбюджет', 'кошторис', 'кампанія',
    'єврокубок', 'єврокваліфікація', 'євровідбір', 'єврофорум',
    'конкурс', 'кінофестиваль', 'кубок', 'мундіаль', "м'яч", 'олімпіада', 'оцінювання', 'оскар',
    'пектораль', 'перегони', 'першість', 'політреформа', 'премія', 'рейтинг', 'реформа', 'сезон',
    'турнір', 'універсіада', 'фестиваль', 'форум', 'чемпіонат', 'чемпіон', 'чемпіонка', 'ярмарок', 'ЧУ', 'ЧЄ')
_WORDS_WITH_NUM = (
    'Формула', 'Карпати', 'Динамо', 'Шахтар', 'Фукусіма', 'Квартал', 'Золоте', 'Мінськ', 'Нюренберг',
    'омега', 'плутоній', 'полоній', 'стронцій', 'уран', 'потік')  # TODO: потік-2 - prop
_NAME_SUFFIX = ('ага', 'ефенді', 'бек', 'заде', 'огли', 'сан', 'кизи', 'сенсей')
_BAD_SUFFIX = ('б', 'би', 'ж', 'же')
_SKY_PATTERN = _c('.*[сзц]ьки')
_SKYI_PATTERN = _c('.*[сзц]ький')

# http://www.pravopys.net/sections/33/
_RIGHT_PARTS_WITH_LEFT_TAG_MAP = {
    'бо': _c('(verb|.*?pron|noun|adv|intj|part).*'),
    'но': _c('((verb(?!.*bad).*?:(impr|futr|insert))|intj|adv|part|conj).*'),
    'от': _c('(.*?pron|adv|part|verb).*'),
    'то': _c('(.*?pron|verb|noun|adj|adv|conj).*'),  # part|conj
    # noun gives false on зразу-таки
    'таки': _c('(verb|adv|adj|.*?pron|part|noninfl:predic).*'),
    'єм': _c('(verb).*'),
}

_TAGS_TO_REMOVE = _c(':comp.|:predic|:insert')
_NOUN_INANIM_P_NV = _c('noun:inanim:p:v_...:nv.*')
_NAPIV = _c('напів(.+?)-напів(.+)')
_XLIV_COMPOUND = _c('[XLIV]+-.*')
_INVALID_PREFIX_TAGS = _c('(noun|adj)(?!.*pron).*')
_FNAME_FILTER = _c('.*fname.*')
_VSE_LEMMAS = _c('[ув]?весь|[ву]с[еі]')
_PART_CONJ_PRON = _c('(part|conj).*|.*?:pron.*')
_LETTER_OR_LATIN = _c('[А-ЯІЇЄҐa-zA-Zα-ωΑ-Ω]|[a-zA-Z-]+')
_ADJ_NOT_PRON_BAD = _c('adj(?!.*(pron|bad|slang|arch)).*')
_COMP = _c(':comp.')
_LOWER_UKR = _c("[а-яіїєґ']+")
_ADJ_BAD = _c('adj.*bad')
_ADJ = _c('adj.*')
_NOUN_NOT_PROP = _c('noun(?!.prop).*')
_ABBR_PATTERN = _c('.*abbr.*')
_STRETCH_PATTERN = _c('([а-іяїєґА-ЯІЇЄҐ])\\1*-\\1+')
_GEO_RIGHT_LEMMAS = _c('(?iu)ріка|гора|місто|град|поле|море|парк')
_INTJ_NONINFL = _c('intj|noninfl.*')
_ADJP_REMOVE = _c(':adjp:(actv|pasv):(im)?perf')
_MFN = _c(':[mfn]:')
_P_V = _c(':[mfn]:v_')
_STRIP_PERF = _c(':(im)?perf|:adjp:(actv|pasv)')
_FLP_NAME = _c('.*?:[flp]name.*')
_JUNIOR_SENIOR = _c('.*(молодший|старший)')
_ADV_NUMR = _c('^adv.*|.*?numr.*')
_ADJ_START = _c('^adj.*')
_NOUN_START = _c('^noun.*')
_NOUN_F_NAZ_NUMR = _c('(noun:inanim:f:v_naz|numr).*')
_DVOH = _c('.*?(двох|трьох|чотирьох)')
_NUMR_PREFIXES = _c("(?iu)(дво|три|чотири|п'яти|шести|семи|вісьми|двох|трьох|чотирьох).+")
_NV_PREFIX = _c('.*?:nv')


# --- data ---

def _hash_bucket(s, cap):
    h = java_string_hash(s)
    return (h ^ (h >> 16)) & (cap - 1)


def _table_size_for(c):
    n = 1
    while n < c:
        n <<= 1
    return n


@functools.lru_cache(maxsize=None)
def _data():
    dash_prefixes = helpers.load_map('/uk/dash_prefixes.txt')
    dash_prefixes_invalid = helpers.load_set('/uk/dash_prefixes_invalid.txt')
    no_dash_prefixes_2019 = {k for k, v in dash_prefixes.items() if 'alt' in v}

    # noDashPrefixes = new HashSet<>(dashPrefixesInvalid); addAll(noDashPrefixes2019)
    # (the order of the prefixes matters for guessOtherTags): the HashSet
    # iteration order of the Java code
    invalid_order = java_hash_set_order(_file_lines('/uk/dash_prefixes_invalid.txt'))
    # Collectors.toMap (HashMap) of the HashSet of the lines, filtered into a HashSet
    lines_order = java_hash_set_order(_file_lines('/uk/dash_prefixes.txt'))
    keys = [java_split(line.strip(), ' ')[0] for line in lines_order]
    map_order = java_hash_set_order(keys)
    alt_order = java_hash_set_order([k for k in map_order if k in no_dash_prefixes_2019])
    seq = list(dict.fromkeys(invalid_order + alt_order))
    cap = _table_size_for(max(int(len(dash_prefixes_invalid) / 0.75) + 1, 16))
    while len(seq) > cap * 0.75:
        cap *= 2
    no_dash_prefixes = sorted(seq, key=lambda s: _hash_bucket(s, cap))
    # too many false positives
    for p in ('мілі', 'поп', 'прес'):
        if p in no_dash_prefixes:
            no_dash_prefixes.remove(p)

    left_master_set = helpers.load_set('/uk/dash_left_master.txt')
    # TODO: "бабуся", "лялька", "рятівник" - not quite followers, could be masters too
    follower_set = helpers.load_set('/uk/dash_follower.txt')
    numbered = helpers.load_spaced_lists('/uk/entities.txt')
    numbered_entities = [(_c(k), numbered[k]) for k in java_hash_set_order(list(numbered))]
    return dash_prefixes, dash_prefixes_invalid, no_dash_prefixes, left_master_set, follower_set, numbered_entities


def _file_lines(path):
    return [line for line in helpers._resource_lines(path) if not line.startswith('#')]


def dash_prefixes():
    return _data()[0]


# --- LetterEndingForNumericHelper ---

class _RegexToCaseList:
    __slots__ = ('pattern', 'cases')

    def __init__(self, regex, *cases):
        self.pattern = _c(regex) if regex is not None else None
        self.cases = cases


def _always(*cases):
    return _RegexToCaseList(None, *cases)


def _regex(regex, *cases):
    return _RegexToCaseList(regex, *cases)


# TODO: many of those depend on the last digit we can do better with regex
_NUMR_ADJ_ENDING_MAP = {
    'й': [_always(':m:v_naz', ':m:v_zna:rinanim', ':f:v_dav', ':f:v_mis')],  # 1-й
    'ий': [_always(':m:v_naz', ':m:v_zna:rinanim')],  # 2-ий
    'ій': [_regex('.*([^3]|13)', ':f:v_dav', ':f:v_mis'),  # 5-ій
           _always(':m:v_naz', ':m:v_zna:rinanim', ':f:v_dav', ':f:v_mis')],  # 3-ій
    'го': [_always(':m:v_rod', ':m:v_zna:ranim', ':n:v_rod')],
    'му': [_regex('.*(?!<1)7', ':m:v_dav', ':m:v_mis', ':n:v_dav', ':n:v_mis', ':f:v_zna'),  # 7-му
           _regex('.*(?!<1)8', ':f:v_zna', ':m:v_dav', ':m:v_mis', ':n:v_dav', ':n:v_mis'),  # 8-му
           _always(':m:v_dav', ':m:v_mis', ':n:v_dav', ':n:v_mis')],
    'ма': [_regex('.*(?!<1)[78]', ':f:v_naz')],
    'м': [_always(':m:v_oru', ':n:v_oru', ':p:v_dav')],  # theoretically can also be -ім v_mis but rare
    'им': [_always(':m:v_oru', ':n:v_oru', ':p:v_dav')],
    'ім': [_regex('.*(?!<1)3', ':m:v_oru', ':m:v_mis', ':n:v_oru', ':n:v_mis'),
           _always(':m:v_mis', ':n:v_oru', ':n:v_mis')],
    'а': [_always(':f:v_naz')],  # 1-а (також часто номер будинку)
    'ва': [_always(':f:v_naz')],  # 40-ва
    'ша': [_always(':f:v_naz')],  # 1-ша
    'га': [_always(':f:v_naz')],  # 2-га
    'тя': [_always(':f:v_naz')],  # 3-тя
    'я': [_regex('.*(?!<1)3', ':f:v_naz')],  # 3-я
    'та': [_always(':f:v_naz')],  # 4-та
    'ї': [_always(':f:v_rod')],  # 4-ї
    'ої': [_always(':f:v_rod')],  # 4-ої
    'у': [_always(':f:v_zna')],  # 1-у
    'шу': [_always(':f:v_zna')],  # 1-шу
    'гу': [_always(':f:v_zna')],  # 2-гу
    'ту': [_always(':f:v_zna')],  # 4-ту
    'тю': [_always(':f:v_zna')],  # 3-тю
    'ою': [_always(':f:v_oru')],  # 4-ою
    'ю': [_regex('.*([^3]|13)', ':f:v_oru'),  # 4-ю
          _always(':f:v_zna', ':f:v_oru')],  # 3-ю
    'е': [_always(':n:v_naz', ':n:v_zna')],  # 1-е
    'є': [_always(':n:v_naz', ':n:v_zna')],  # 3-є
    'ше': [_always(':n:v_naz', ':n:v_zna')],  # 1-ше
    'ге': [_always(':n:v_naz', ':n:v_zna')],  # 2-ге
    'тє': [_always(':n:v_naz', ':n:v_zna')],  # 3-тє
    'те': [_always(':n:v_naz', ':n:v_zna')],  # 4-те
    'ме': [_regex('.*(?!<1)[78]', ':n:v_naz', ':n:v_zna')],  # 7-те
    'і': [_always(':p:v_naz', ':p:v_zna:rinanim')],
    'ті': [_always(':p:v_naz', ':p:v_zna:rinanim')],
    'ні': [_always(':p:v_naz', ':p:v_zna:rinanim')],  # 2000-ні
    'ми': [_always(':p:v_oru')],  # 33-ми калібрами
    'х': [_always(':p:v_rod', ':p:v_zna:ranim', ':p:v_mis')],  # 5-х
    'их': [_always(':p:v_rod', ':p:v_zna:ranim', ':p:v_mis')],  # 5-их
    'ві': [_regex('.*40', ':p:v_naz', ':p:v_zna:rinanim'),  # 40-ві
           _regex('.*%', ':p:v_naz', ':p:v_zna:rinanim')],  # 40%-ві
    # bad
    'тій': [_regex('.*([^3]|13)', ':f:v_dav:bad', ':f:v_mis:bad'),  # 5-тій
            _always(':m:v_naz:bad', ':m:v_zna:rinanim:bad', ':f:v_dav:bad', ':f:v_mis:bad')],  # 3-ій
    'мій': [_always(':f:v_dav:bad', ':f:v_mis:bad')],  # 8-мій
    'мою': [_always(':f:v_oru:bad')],
    'тою': [_always(':f:v_oru:bad')],
    'тої': [_always(':f:v_rod:bad')],  # 4-тої
    'того': [_always(':m:v_rod:bad', ':n:v_rod:bad')],
    'тього': [_always(':m:v_rod:bad', ':n:v_rod:bad')],
    'тому': [_always(':m:v_dav:bad', ':m:v_mis:bad', ':n:v_rod:bad', ':n:v_mis:bad')],
    'тьому': [_always(':m:v_dav:bad', ':m:v_mis:bad', ':n:v_rod:bad', ':n:v_mis:bad')],
    'тими': [_always(':p:v_oru:bad')],
    'тім': [_always(':m:v_mis:bad', ':n:v_mis:bad')],
    'мої': [_always(':f:v_rod:bad')],
    'тий': [_always(':m:v_naz:bad', ':m:v_zna:rinanim:bad')],
    'мий': [_always(':m:v_naz:bad', ':m:v_zna:rinanim:bad')],
    'тих': [_always(':p:v_rod:bad', ':p:v_mis:bad')],
    'ого': [_always(':m:v_rod:bad', ':m:v_zna:ranim:bad', ':n:v_rod:bad')],
    'ому': [_always(':m:v_dav:bad', ':m:v_mis:bad', ':n:v_dav:bad', ':n:v_mis:bad')],
    'тим': [_always(':m:v_oru:bad', ':n:v_oru:bad', ':p:v_dav:bad')],
    'ома': [_always(':f:v_naz:bad', ':p:v_oru:bad')],  # 7-ома, 12-ома
    'ший': [_always(':m:v_naz:bad', ':m:v_zna:rinanim:bad')],
    'гій': [_always(':f:v_mis:bad', ':f:v_dav:bad')],
}

_NUMR_NOUN_ENDING_MAP = {
    'ти': [_regex('.*([0569]|1[0-9])', ':p:v_rod:bad', ':p:v_dav:bad', ':p:v_mis:bad')],  # 20-ти
    'ці': [_regex('.*([03456789]|1[0-9])', ':f:v_dav:bad', ':f:v_mis:bad')],  # 20-ці
    'ма': [_regex('.*([023456789]|1[0-9])', ':p:v_oru:bad')],  # 20-ма
    'ми': [_always(':p:v_rod:bad', ':p:v_mis:bad')],  # 148-ми
    'ох': [_always(':p:v_rod:bad', ':p:v_zna:ranim:bad')],  # 4-ох
    'ві': [_regex('.*(?!<1)2', ':p:v_naz:bad', ':p:v_zna:rinanim:bad')],  # 42-ві
    'ть': [_always(':p:v_naz:bad', ':p:v_zna:rinanim:bad')],  # 75-ть
    'ка': [_always(':f:v_naz:bad')],  # 40-ка
}


def _get_case_tags(left_word, case_lists):
    for r in case_lists:
        if r.pattern is None or r.pattern.fullmatch(left_word):
            return r.cases
    return None


def is_possible_adj_adj_ending(left_word, right_word):
    """LetterEndingForNumericHelper.isPossibleAdjAdjEnding"""
    return right_word in _NUMR_ADJ_ENDING_MAP


def find_tags_adj(left_word, right_word):
    if right_word in _NUMR_ADJ_ENDING_MAP:
        return _get_case_tags(left_word, _NUMR_ADJ_ENDING_MAP[right_word])
    return None


def find_tags_noun(left_word, right_word):
    if right_word in _NUMR_NOUN_ENDING_MAP:
        return _get_case_tags(left_word, _NUMR_NOUN_ENDING_MAP[right_word])
    return None


# --- CompoundTagger ---

def _tokens(word, tagged_words):
    """asAnalyzedTokenListForTaggedWords"""
    return [AnalyzedToken(word, tw.pos_tag, tw.lemma) for tw in tagged_words]


def _tag_starts(tag, *prefixes):
    return pth.IPOSTag.starts_with(tag, *prefixes)


def _capitalize(s):
    """StringUtils.capitalize (title case of the first char)"""
    if not s:
        return s
    t = s[0].title()
    return (t if len(t) == 1 else s[0]) + s[1:]


def _equal_parts(lemma):
    if '-' not in lemma:
        return False
    parts = lemma.split('-', 1)
    return parts[0] == parts[1]


def _strip_perf_imperf(tag):
    return _STRIP_PERF.sub('', tag)


def _drop_extra(postags):
    p = _EXTRA_TAGS_DROP_NONINFL if postags.startswith('noninfl') else _EXTRA_TAGS_DROP
    return p.sub('', postags)


def _is_min_max(right_token):
    return right_token == 'максимум' or right_token == 'мінімум'


def _is_same_anim_status(left_pos_tag, right_pos_tag):
    return (_TAG_ANIM in left_pos_tag) == (_TAG_ANIM in right_pos_tag)


def _is_plural(pos_tag):
    return pos_tag.startswith('noun:') and ':p:' in pos_tag


def _o_to_yj(left_word):
    return left_word[:-2] + 'ій' if left_word.endswith('ьо') else left_word[:-1] + 'ий'


def _collapse_stretch(word):
    capitalized = is_capitalized_word(word)
    merged = jregex.java_replace(_STRETCH_PATTERN, '$1', word.lower())
    merged = jregex.java_replace(_STRETCH_PATTERN, '$1', merged)
    merged = merged.replace('-', '')
    if capitalized:
        merged = _capitalize(merged)
    return merged


def _generate_tokens_with_right_inflected(word, left_word, right_analyzed_tokens, pos_tag_start, add_tag, drop_tag):
    out = []
    for at in right_analyzed_tokens:
        pos_tag = at.pos_tag
        if pos_tag.startswith(pos_tag_start) and 'v_kly' not in pos_tag:
            if drop_tag is not None:
                pos_tag = drop_tag.sub('', pos_tag)
            pos_tag = pth.add_if_not_contains(pos_tag, add_tag)
            out.append(AnalyzedToken(word, pos_tag, left_word + '-' + at.lemma))
    return out


def _get_nv_prefix_noun_match(word, analyzed_tokens, left_word, extra_tag):
    out = []
    for at in analyzed_tokens:
        pos_tag = at.pos_tag
        if pos_tag.startswith('noun') and 'v_kly' not in pos_tag:
            # міні-БПЛА - ok for up19 too
            if extra_tag != ':alt' or not is_upper_case(at.lemma[0]):
                if extra_tag:
                    pos_tag = pth.add_if_not_contains(pos_tag, extra_tag)
            out.append(AnalyzedToken(word, pos_tag, left_word + '-' + at.lemma))
    return out or None


def _po_adv_match(word, analyzed_tokens, adj_tag):
    for at in analyzed_tokens:
        if at.pos_tag.startswith(adj_tag):
            return [AnalyzedToken(word, 'adv', word)]
    return None


class CompoundTagger:

    def __init__(self, ukrainian_tagger, word_tagger):
        self.tagger = ukrainian_tagger
        self.word_tagger = word_tagger

    def _tag(self, word):
        return list(self.word_tagger.tag(word))

    def guess_compound_tag(self, word):
        return self._do_guess_compound_tag(word)

    def _do_guess_compound_tag(self, word):
        dash_prefixes_map, dash_prefixes_invalid = _data()[0], _data()[1]
        dash_idx = word.rfind('-')
        if dash_idx == len(word) - 1:
            return None
        first_dash_idx = word.find('-')
        if first_dash_idx == 0:
            return None

        starts_with_digit = is_digit(word[0])

        if not starts_with_digit and dash_idx != first_dash_idx:
            dash_count = word.count('-')
            if dash_count >= 2 and dash_idx > first_dash_idx + 1:
                tokens = self._do_guess_multi_hyphens(word, first_dash_idx, dash_idx)
                if tokens is not None:
                    return tokens
            if dash_count == 2 and dash_idx > first_dash_idx + 1:
                return self._do_guess_two_hyphens(word, first_dash_idx, dash_idx)
            return None

        left_word = word[:dash_idx]
        right_word = word[dash_idx + 1:]
        left_word_lower = left_word.lower()

        # з-зателефоную
        if len(left_word) == 1 and len(right_word) > 3 and right_word.startswith(left_word_lower):
            right_wd_list = pth.adjust(self._tag(right_word), None, None, ':alt')
            return _tokens(word, right_wd_list)

        dash_prefix_match = (left_word in dash_prefixes_map or left_word_lower in dash_prefixes_map or
                             _DASH_PREFIX_LAT_PATTERN.fullmatch(left_word) is not None)

        if not dash_prefix_match and (starts_with_digit or _XLIV_COMPOUND.fullmatch(word)):
            return self._match_digit_compound(word, left_word, right_word)

        if is_digit(right_word[0]):
            return self._match_numbered_proper_noun(word, left_word, right_word)

        # авіа..., авто... пишуться разом
        # TODO: але може бути: авто-пенсіонер
        if left_word_lower in dash_prefixes_invalid:
            right_wd_list = self._tag_either_case(right_word)
            right_wd_list = pth.filter2(right_wd_list, _INVALID_PREFIX_TAGS)
            if not right_wd_list:
                return None
            extra_tag = '' if is_upper_case(right_word[0]) else ':bad'
            right_wd_list = pth.adjust(right_wd_list, left_word + '-', None, extra_tag)
            return _tokens(word, right_wd_list)

        # wrong: пів-качана
        if left_word_lower == 'пів' and is_lower_case(right_word[0]):
            right_wd_list = self._tag_either_case(right_word)
            right_analyzed_tokens = _tokens(right_word, right_wd_list)
            return self._add_plural_nv_tokens(word, right_analyzed_tokens, ':bad')

        left_wd_list = self._tag_as_is_and_with_lower_case(left_word)

        # стривай-бо, чекай-но, прийшов-таки, такий-от, такий-то, ішов-єм (arch)
        right_word_lower = right_word.lower()
        if right_word_lower in _RIGHT_PARTS_WITH_LEFT_TAG_MAP and not pth.has_pos_tag_part2(left_wd_list, 'abbr'):
            if not left_wd_list:
                return None
            left_tag_regex = _RIGHT_PARTS_WITH_LEFT_TAG_MAP[right_word_lower]
            left_analyzed_tokens = _tokens(left_word, left_wd_list)
            new_tokens = []
            # ignore хто-то
            if right_word_lower == 'то' and helpers.has_lemma(left_analyzed_tokens, ('хто', 'що', 'чи')):
                return None
            for at in left_analyzed_tokens:
                pos_tag = at.pos_tag
                if java_equals_ignore_case(left_word, 'як') and pos_tag is not None and 'noun' in pos_tag:
                    continue
                if (pos_tag is not None and (left_word_lower == 'дуже' and 'adv' in pos_tag)) or \
                        left_tag_regex.fullmatch(pos_tag):
                    if right_word == 'єм':
                        pos_tag = pth.add_if_not_contains(pos_tag, ':arch')
                    new_tokens.append(AnalyzedToken(word, pos_tag, at.lemma))
            return new_tokens or None

        # по-болгарськи, по-болгарському
        if java_equals_ignore_case(left_word, 'по') and _SKY_PATTERN.fullmatch(right_word):
            right_word += 'й'

        # Пенсильванія-авеню
        if is_upper_case(left_word[0]) and right_word_lower in helpers.CITY_AVENU:
            add_pos = ':alt' if right_word == 'штрассе' else ''
            return pth.generate_tokens_for_nv(word, 'f', ':prop' + add_pos)

        # Fe-вмісний
        if right_word_lower.startswith('вмісн'):
            adjusted_word = 'боро' + right_word
            right_wd_list = self._tag_either_case(adjusted_word)
            right_wd_list = [TaggedWord('вмісний', wd.pos_tag) for wd in right_wd_list]
            right_analyzed_tokens = _tokens(right_word, right_wd_list)
            return _generate_tokens_with_right_inflected(word, left_word, right_analyzed_tokens, 'adj', None, _COMP)

        right_wd_list = self._tag_either_case(right_word)

        if word.lower().startswith('напів'):
            # напівпольської-напіванглійської
            m = _NAPIV.fullmatch(word)
            if m:
                napiv_left = pth.adjust(self._tag_as_is_and_with_lower_case(m.group(1)), 'напів', None)
                napiv_right = right_wd_list if right_wd_list else \
                    pth.adjust(self._tag_as_is_and_with_lower_case(m.group(2)), 'напів', None)
                if not napiv_left or not napiv_right:
                    return None
                napiv_left_tokens = _tokens(m.group(1), napiv_left)
                napiv_right_tokens = _tokens(m.group(2), napiv_right)
                tag_match = self._tag_match(word, napiv_left_tokens, napiv_right_tokens)
                if tag_match is not None:
                    return tag_match

        left_analyzed_tokens = _tokens(left_word, left_wd_list)

        # гірко-прегірко
        if right_word.startswith('пре') and left_word_lower == right_word[3:].lower():
            if pth.has_pos_tag_start2(left_wd_list, 'adv'):
                return [AnalyzedToken(word, _TAGS_TO_REMOVE.sub('', a.pos_tag), word)
                        for a in left_analyzed_tokens if a.pos_tag is not None and a.pos_tag.startswith('adv')]
            # гіркий-прегіркий
            elif pth.has_pos_tag_start2(left_wd_list, 'adj'):
                return [AnalyzedToken(word, _TAGS_TO_REMOVE.sub('', a.pos_tag), a.lemma + '-пре' + a.lemma)
                        for a in left_analyzed_tokens if a.pos_tag is not None and a.pos_tag.startswith('adj')]

        # Мустафа-ага
        if right_word in _NAME_SUFFIX and pth.has_pos_tag_part(left_analyzed_tokens, 'name'):
            word_list = pth.adjust(left_wd_list, None, '-' + right_word)
            return _tokens(word, word_list)

        if left_word == 'аль':
            wd = 'Аль-' + right_word
            wd_list = self._tag(wd)
            if wd_list:
                wd_list = pth.adjust(wd_list, None, None, ':bad')
                return _tokens(wd, wd_list)

        if not right_wd_list:
            return None

        right_analyzed_tokens = _tokens(right_word, right_wd_list)

        # півгодини-годину
        if word.startswith('пів') and pth.has_pos_tag(left_analyzed_tokens, _NOUN_INANIM_P_NV):
            return [AnalyzedToken(word, jregex.java_replace(_MFN, ':p:', a.pos_tag, 1), word)
                    for a in right_analyzed_tokens if a.pos_tag is not None and a.pos_tag.startswith('noun:inanim:')]

        if java_equals_ignore_case(left_word, 'по'):
            if right_word.endswith('ому'):
                return _po_adv_match(word, right_analyzed_tokens, _ADJ_TAG_FOR_PO_ADV_MIS)
            elif _SKYI_PATTERN.fullmatch(right_word):
                return _po_adv_match(word, right_analyzed_tokens, _ADJ_TAG_FOR_PO_ADV_NAZ)
            return None

        if is_upper_case(left_word[0]) and is_upper_case(right_word[0]):
            # Київ-Прага
            if pth.has_pos_tag(left_analyzed_tokens, _GEO_V_NAZ) and pth.has_pos_tag(right_analyzed_tokens, _GEO_V_NAZ):
                return [AnalyzedToken(word, 'noninfl:prop:geo', word)]
            # Хуана-Карлоса
            if pth.has_pos_tag(left_analyzed_tokens, _FNAME) and pth.has_pos_tag(right_analyzed_tokens, _FNAME):
                left_analyzed_tokens = pth.filter_tokens(left_analyzed_tokens, _FNAME_FILTER)
                right_analyzed_tokens = pth.filter_tokens(right_analyzed_tokens, _FNAME_FILTER)
                return self._tag_match(word, left_analyzed_tokens, right_analyzed_tokens)
            # подружжя Карпа-Хансен
            if pth.has_pos_tag(left_analyzed_tokens, _LNAME_V_NAZ) and \
                    pth.has_pos_tag(right_analyzed_tokens, _LNAME_V_NAZ):
                return [AnalyzedToken(word, 'noninfl:prop:lname', word)]
            # Джеймса-Веніка
            if pth.has_pos_tag(left_analyzed_tokens, _LNAME_V_ROD) and \
                    pth.has_pos_tag(right_analyzed_tokens, _LNAME_V_ROD):
                return [AnalyzedToken(word, 'noninfl:prop:lname', word)]
            # bad: Квітки-Основ'яненко
            if pth.has_pos_tag(left_analyzed_tokens, _NAME) and pth.has_pos_tag(right_analyzed_tokens, _NAME):
                return None
            # Україна-ЄС
            if pth.has_pos_tag(left_analyzed_tokens, _PROP_V_NAZ) and \
                    pth.has_pos_tag(right_analyzed_tokens, _PROP_V_NAZ):
                return [AnalyzedToken(word, 'noninfl:prop', word)]

        # exclude: Малишко-це, відносини-коли

        # був-би, but not м-б
        if len(left_word) > 1 and right_word in _BAD_SUFFIX:
            word_list = pth.add_if_not_contains_words(left_wd_list, ':bad', None)
            return _tokens(word, word_list)

        if java_equals_ignore_case(left_word, right_word) and left_analyzed_tokens and \
                helpers.has_lemma(left_analyzed_tokens, _VSE_LEMMAS):
            tag_match = self._tag_match(word, left_analyzed_tokens, right_analyzed_tokens)
            if tag_match is not None:
                return [m for m in tag_match if _equal_parts(m.lemma)]

        if pth.has_pos_tag_part(left_analyzed_tokens, 'pron') and \
                not pth.has_pos_tag_part(left_analyzed_tokens, 'numr'):
            return None

        if not java_equals_ignore_case(left_word, right_word) and \
                pth.has_pos_tag(right_analyzed_tokens, _PART_CONJ_PRON) and \
                not (pth.has_pos_tag_start(left_analyzed_tokens, 'numr') and
                     pth.has_pos_tag_start(right_analyzed_tokens, 'numr')):
            return None

        adj_compounds = []
        if _LETTER_OR_LATIN.fullmatch(left_word):
            if pth.has_pos_tag(right_analyzed_tokens, _ADJ_NOT_PRON_BAD):
                adj_compounds = _generate_tokens_with_right_inflected(word, left_word, right_analyzed_tokens, 'adj',
                                                                      None, _COMP)

        # майстер-класу
        if dash_prefix_match and not (java_equals_ignore_case(left_word, 'міді') and
                                      helpers.has_lemma(right_analyzed_tokens, ('бронза',))):
            new_tokens = []
            extra_tag = ''
            lower_cased = False
            if left_word in dash_prefixes_map:
                extra_tag = dash_prefixes_map[left_word]
            elif left_word_lower in dash_prefixes_map:
                extra_tag = dash_prefixes_map[left_word_lower]
                if _LOWER_UKR.fullmatch(left_word_lower):  # Інтернет-пошуковик
                    lower_cased = True

            new_tokens_noun = _get_nv_prefix_noun_match(word, right_analyzed_tokens,
                                                        left_word_lower if lower_cased else left_word, extra_tag)
            if new_tokens_noun is not None:
                new_tokens.extend(new_tokens_noun)

            # топ-десять
            if java_equals_ignore_case(left_word, 'топ') and pth.has_pos_tag_part(right_analyzed_tokens, 'numr:'):
                return _generate_tokens_with_right_inflected(word, left_word, right_analyzed_tokens, 'numr:', ':bad',
                                                             None)
            if not new_tokens:
                new_tokens.extend(adj_compounds)
            return new_tokens

        if adj_compounds:
            return adj_compounds

        # пів-України
        if is_upper_case(right_word[0]):
            if word.startswith('пів-'):
                return self._add_plural_nv_tokens(word, right_analyzed_tokens, ':alt')
            else:
                # we don't want Нью-Париж but want Австрійсько-Карпатський
                if is_capitalized_word(right_word) or left_word.endswith('о') or \
                        pth.has_pos_tag(right_analyzed_tokens, _ADJ):
                    # Кримсько-Татарський - :bad
                    lower_compound = self._tag_as_is_and_with_lower_case(word.lower())
                    if pth.has_pos_tag2(lower_compound, _ADJ_BAD):
                        return _tokens(word, lower_compound)

                    # tag Чорноморське/noun і чорноморське adj
                    right_wd_list2 = self._tag_as_is_and_with_lower_case(right_word)
                    right_analyzed_tokens2 = _tokens(right_word, right_wd_list2)
                    match = self._try_o_with_adj(word, left_word, right_analyzed_tokens2)
                    if match is not None:
                        return match

                # Жінка-Актриса
                if pth.has_pos_tag(left_analyzed_tokens, _NOUN_NOT_PROP) and \
                        pth.has_pos_tag(right_analyzed_tokens, _NOUN_NOT_PROP):
                    pass  # flow-through
                else:
                    return None

        # don't allow: Донець-кий, зовнішньо-економічний, мас-штаби
        # allow га-га!
        no_dash_analyzed_tokens = []
        has_intj = pth.has_pos_tag_start(left_analyzed_tokens, 'intj')
        if not has_intj:
            no_dash_word = word.replace('-', '')
            no_dash_word_list = self._tag_as_is_and_with_lower_case(no_dash_word)
            no_dash_analyzed_tokens = _tokens(no_dash_word, no_dash_word_list)

        # вгору-вниз, лікар-гомеопат, жило-було
        if not no_dash_analyzed_tokens:
            if left_wd_list and (len(left_word) > 2 or has_intj):
                tag_match = self._tag_match(word, left_analyzed_tokens, right_analyzed_tokens)
                if tag_match is not None:
                    return tag_match

        return self._try_o_with_adj(word, left_word, right_analyzed_tokens)

    def _add_plural_nv_tokens(self, word, right_analyzed_tokens, add_tag):
        out = []
        for rat in right_analyzed_tokens:
            right_pos_tag = rat.pos_tag
            if right_pos_tag is not None and _NOUN_SING_V_ROD_REGEX.fullmatch(right_pos_tag):
                for vid in pth.VIDMINKY_MAP:
                    if vid == 'v_kly':
                        continue
                    pos_tag = jregex.java_replace(_P_V, ':p:v_', right_pos_tag.replace('v_rod', vid), 1) + ':nv' + \
                        add_tag
                    token = AnalyzedToken(word, pos_tag, word)
                    if token not in out:
                        out.append(token)
        return out

    def _tag_either_case(self, word):
        if not word:
            return []
        wd_list = self._tag(word)
        if not wd_list and is_upper_case(word[0]):
            wd_list = self._tag(word.lower())
        return wd_list

    def _try_o_with_adj(self, word, left_word, right_analyzed_tokens):
        if len(left_word) < 3:
            return None
        # дво-триметровий...
        if _NUMR_ADJ_PATTERN.fullmatch(left_word):
            return self._numr_adj_match(word, right_analyzed_tokens, left_word)
        # яскраво-барвистий...
        if _O_ADJ_PATTERN.fullmatch(left_word):
            return self._o_adj_match(word, right_analyzed_tokens, left_word)
        return None

    def _do_guess_multi_hyphens(self, word, first_dash_idx, dash_idx):
        dash_prefixes_map, dash_prefixes_invalid = _data()[0], _data()[1]
        lower_word = word.lower()
        parts = java_split(lower_word, '-')
        uniq = list(dict.fromkeys(parts))
        # try intj
        left_wd = parts[0]
        if len(uniq) == 2:
            left_wd_list = self._tag_either_case(left_wd)
            right_wd_list = self._tag_either_case(uniq[1])
            if (pth.has_pos_tag2(left_wd_list, _INTJ_PATTERN) and pth.has_pos_tag2(right_wd_list, _INTJ_PATTERN) or
                    pth.has_pos_tag2(left_wd_list, _NONINFL_PATTERN) and
                    pth.has_pos_tag2(right_wd_list, _NONINFL_PATTERN)):
                return [AnalyzedToken(word, right_wd_list[0].pos_tag, lower_word)]
        elif len(uniq) == 1:
            if lower_word == 'ла':
                return [AnalyzedToken(word, 'intj', lower_word)]
            right_wd_list = self._tag_either_case(left_wd)
            if pth.has_pos_tag2(right_wd_list, _INTJ_PATTERN):
                return [AnalyzedToken(word, right_wd_list[0].pos_tag, lower_word)]

        if len(parts) == 3:
            tokens = self.generate_entities(word)
            if tokens:
                return tokens

        # filter out г-г-г
        if len(parts) >= 3 and len(uniq) > 1 and parts[0] not in dash_prefixes_map and \
                parts[0] not in dash_prefixes_invalid:
            # ва-ре-ни-ки
            merged = word.replace('-', '')
            tagged = self.tag_both_cases(merged, None)
            tagged = pth.filter2_negative(tagged, _ABBR_PATTERN)
            if tagged:
                return _tokens(word, pth.add_if_not_contains_words(tagged, ':alt'))
            # ду-у-у-же
            merged = _collapse_stretch(word)
            tagged = self.tag_both_cases(merged, None)
            tagged = pth.filter2_negative(tagged, _ABBR_PATTERN)
            if tagged:
                return _tokens(word, pth.add_if_not_contains_words(tagged, ':alt'))
        return None

    def _do_guess_two_hyphens(self, word, first_dash_idx, dash_idx):
        dash_prefixes_map = _data()[0]
        parts = java_split(word, '-')
        right_wd_list = self._tag_either_case(parts[2])
        if not right_wd_list:
            return None
        right_analyzed_tokens = _tokens(parts[2], right_wd_list)
        first_and_second = parts[0] + '-' + parts[1]

        two_dash = False
        extra_tag = ''
        if first_and_second in dash_prefixes_map:
            extra_tag = dash_prefixes_map[first_and_second]
            two_dash = True
        elif first_and_second.lower() in dash_prefixes_map:
            extra_tag = dash_prefixes_map[first_and_second.lower()]
            two_dash = True
        if two_dash:
            return _get_nv_prefix_noun_match(word, right_analyzed_tokens, first_and_second, extra_tag)

        second_wd_list = self._tag_either_case(parts[1])
        # try full match - only adj for now - nouns are complicated
        if pth.has_pos_tag_start2(second_wd_list, 'adj'):
            second_analyzed_tokens = _tokens(parts[1], second_wd_list)
            tag_match_second_and_third = self._tag_match(word, second_analyzed_tokens, right_analyzed_tokens)
            if tag_match_second_and_third is not None:
                left_wd_list = self._tag_either_case(parts[0])
                if left_wd_list:
                    left_analyzed_tokens = _tokens(parts[0], left_wd_list)
                    self._tag_match(word, left_analyzed_tokens, tag_match_second_and_third)
                return tag_match_second_and_third

        # try ірансько-нігерійсько-зімбабвійський
        second_and_third = self._try_o_with_adj(word, parts[1], right_analyzed_tokens)
        if second_and_third is not None:
            return self._try_o_with_adj(word, parts[0], second_and_third)
        return None

    def _match_numbered_proper_noun(self, word, left_word, right_word):
        # Ан-140
        if _NOUN_SUFFIX_NUMBER_LETTER.fullmatch(right_word):
            tokens = self.generate_entities(word)
            if tokens:
                return tokens

        # Вибори-2014
        if _YEAR_NUMBER.fullmatch(right_word):
            left_wd_list = self._tag_as_is_and_with_lower_case(left_word)
            if left_wd_list:
                left_analyzed_tokens = _tokens(left_word, left_wd_list)
                out = []
                is_uppercase = is_upper_case(left_word[0])
                for at in left_analyzed_tokens:
                    if not pth.has_pos_tag_part(at, ':prop') and at.lemma not in _WORDS_WITH_YEAR:
                        continue
                    pos_tag = at.pos_tag
                    # only noun - відкидаємо: вибори - вибороти
                    # Афіни-2014 - потрібне лише місто, не ім'я
                    # TODO: чемпіон-2012
                    if pos_tag is None or not pos_tag.startswith('noun:inanim'):
                        continue
                    if 'v_kly' in pos_tag:
                        continue
                    if ':p:' in pos_tag and at.lemma not in ('гра', 'бюджет') and ':ns' not in pos_tag:
                        continue
                    lemma = at.lemma
                    pos_tag = pos_tag.replace(':geo', '')
                    if ':prop' not in pos_tag:
                        if is_uppercase:
                            pos_tag += ':prop'
                            lemma = _capitalize(lemma)
                    out.append(AnalyzedToken(word, pos_tag, lemma + '-' + right_word))
                if out:
                    return out

        # Формула-1, Карпати-2, омега-3
        if _NOUN_PREFIX_NUMBER.fullmatch(right_word):
            left_wd_list = self._tag_as_is_and_with_lower_case(left_word)
            if left_wd_list:
                left_analyzed_tokens = _tokens(left_word, left_wd_list)
                out = []
                for at in left_analyzed_tokens:
                    pos_tag = at.pos_tag
                    lemma = at.lemma
                    if pos_tag is None or not pos_tag.startswith('noun:inanim'):
                        continue
                    if 'v_kly' in pos_tag:
                        continue
                    if ':prop' not in pos_tag:
                        if lemma not in _WORDS_WITH_NUM:
                            pos_tag += ':prop'
                            lemma = _capitalize(lemma)
                    if lemma not in _WORDS_WITH_NUM:
                        continue
                    out.append(AnalyzedToken(word, pos_tag, lemma + '-' + right_word))
                if out:
                    return out
        return None

    def generate_entities(self, word):
        """generateEntities: a list (the LinkedHashSet) of the tokens for the
        entities of entities.txt matching the word"""
        out = {}
        for pattern, tags in _data()[5]:
            if pattern.fullmatch(word):
                for tag in tags:
                    if ':nv' in tag:
                        tag_parts = tag.split(':')
                        extra_tags = jregex.java_replace(_NV_PREFIX, '', tag, 1).replace(':np', '')
                        for t in pth.generate_tokens_for_nv(word, tag_parts[1], extra_tags):
                            out[t] = None
                        if ':np' not in tag and ':p' not in tag:
                            for t in pth.generate_tokens_for_nv(word, 'p', extra_tags):
                                out[t] = None
                    else:
                        out[AnalyzedToken(word, tag, word)] = None
        return list(out)

    def _match_digit_compound(self, word, left_word, right_word):
        # 101-й, 100-річному
        if not _ADJ_PREFIX_NUMBER.fullmatch(left_word):
            return None
        out = []
        # e.g. 101-го
        tags = find_tags_adj(left_word, right_word)
        if tags is not None:
            for tag in tags:
                lemma = left_word + '-' + 'й'  # lemma is approximate here, we mostly care about the tag
                tag = tag.replace(':bad', ':numr:bad') if ':bad' in tag else tag + ':numr'
                out.append(AnalyzedToken(word, 'adj' + tag, lemma))
        else:
            if _NOUN_WITH_INTERVAL_PREFIX_NUMBER.fullmatch(left_word):
                tags_noun = find_tags_noun(left_word, right_word)
                if tags_noun is not None:
                    for tag in tags_noun:
                        out.append(AnalyzedToken(word, 'numr' + tag, left_word))
                    return out

                if right_word == 'мм':
                    for gender in pth.BASE_GENDERS:
                        for vidm in pth.VIDMINKY_MAP:
                            if vidm == 'v_kly':
                                continue
                            out.append(AnalyzedToken(word, 'adj:' + gender + ':' + vidm, word))
                    return out

                # 100-річчя
                try_prefix = _get_try_prefix(right_word.lower())
                if try_prefix is not None:
                    right_wd_list = self._tag(try_prefix + right_word.lower())
                    right_analyzed_tokens = _tokens(right_word, right_wd_list)
                    for at in right_analyzed_tokens:
                        lemma = at.lemma[len(try_prefix):]
                        out.append(AnalyzedToken(word, at.pos_tag, left_word + '-' + lemma))
                    return out

            # e.g. 100-річному, 100-відсотково
            right_wd_list = self._tag(right_word)
            if not right_wd_list or pth.has_pos_tag_part2(right_wd_list, 'pron'):
                return None
            right_analyzed_tokens = _tokens(right_word, right_wd_list)
            for at in right_analyzed_tokens:
                if at.pos_tag.startswith('adj') or at.lemma == 'відсотково':
                    out.append(AnalyzedToken(word, at.pos_tag, left_word + '-' + at.lemma))
        return out or None

    def _tag_match(self, word, left_analyzed_tokens, right_analyzed_tokens):
        new_tokens = []
        new_tokens_anim_inanim = []

        for lat in left_analyzed_tokens:
            left_pos_tag = lat.pos_tag
            if left_pos_tag is None or 'abbr' in left_pos_tag:
                continue
            if left_pos_tag.startswith('noun:inanim'):
                # we don't want to have v_kly for рибо-полювання
                # but we do for пане-товаришу
                if 'v_kly' in left_pos_tag:
                    continue

            left_pos_tag_extra = ''
            left_nv = False
            if pth.NO_VIDMINOK_SUBSTR in left_pos_tag:
                left_nv = True
                left_pos_tag = left_pos_tag.replace(pth.NO_VIDMINOK_SUBSTR, '')

            left_pos_tag = _drop_extra(left_pos_tag)

            m = _EXTRA_TAGS.search(left_pos_tag)
            if m:
                left_pos_tag_extra += m.group()
                left_pos_tag = _EXTRA_TAGS.sub('', left_pos_tag)

            for rat in right_analyzed_tokens:
                right_pos_tag = rat.pos_tag
                if right_pos_tag is None or 'abbr' in right_pos_tag or 'v_zna:var' in right_pos_tag:
                    continue
                if right_pos_tag.startswith('noun:inanim'):
                    if 'v_kly' in right_pos_tag:
                        continue
                    # skip Гірник geo for Гірник-спорт
                    if ':geo' in left_pos_tag and ':geo' not in right_pos_tag and \
                            not _GEO_RIGHT_LEMMAS.fullmatch(rat.lemma):
                        continue

                # країни-агресори - не треба v_zna:rare
                if right_pos_tag.startswith('noun:anim:p:v_zna:rare') and left_pos_tag.startswith('noun:inanim'):
                    continue

                extra_nv_tag = ''
                right_nv = False
                if pth.NO_VIDMINOK_SUBSTR in right_pos_tag:
                    right_nv = True
                    if left_nv:
                        extra_nv_tag += pth.NO_VIDMINOK_SUBSTR

                right_pos_tag = _drop_extra(right_pos_tag)
                if _EXTRA_TAGS.search(right_pos_tag):
                    right_pos_tag = _EXTRA_TAGS.sub('', right_pos_tag)

                new_lemma = lat.lemma + '-' + rat.lemma
                if _strip_perf_imperf(left_pos_tag) == _strip_perf_imperf(right_pos_tag) and \
                        (_tag_starts(left_pos_tag, 'numr', 'adv', 'adj', 'verb') or
                         (_INTJ_NONINFL.fullmatch(left_pos_tag) and java_equals_ignore_case(lat.lemma, rat.lemma))):
                    new_pos_tag = left_pos_tag + extra_nv_tag + left_pos_tag_extra
                    if ('adjp' in left_pos_tag) != ('adjp' in right_pos_tag):
                        new_pos_tag = jregex.java_replace(_ADJP_REMOVE, '', new_pos_tag, 1)
                    new_tokens.append(AnalyzedToken(word, new_pos_tag, new_lemma))
                # noun-noun
                elif left_pos_tag.startswith('noun') and right_pos_tag.startswith('noun'):
                    agreed_pos_tag = self._get_agreed_pos_tag(left_pos_tag, right_pos_tag, left_nv, word)
                    if agreed_pos_tag is None and right_pos_tag.startswith('noun:inanim:m:v_naz') and \
                            _is_min_max(rat.token):
                        agreed_pos_tag = left_pos_tag
                    if agreed_pos_tag is None and not _is_same_anim_status(left_pos_tag, right_pos_tag):
                        agreed_pos_tag = self._try_anim_inanim(left_pos_tag, right_pos_tag, lat.lemma, rat.lemma,
                                                               left_nv, right_nv, word)
                        if agreed_pos_tag is not None:
                            new_tokens_anim_inanim.append(
                                AnalyzedToken(word, agreed_pos_tag + extra_nv_tag + left_pos_tag_extra, new_lemma))
                            continue
                    if agreed_pos_tag is not None:
                        new_tokens.append(AnalyzedToken(word, agreed_pos_tag + extra_nv_tag + left_pos_tag_extra,
                                                        new_lemma))
                # numr-numr: один-три
                elif left_pos_tag.startswith('numr') and right_pos_tag.startswith('numr'):
                    agreed_pos_tag = _get_num_agreed_pos_tag(left_pos_tag, right_pos_tag, left_nv)
                    if agreed_pos_tag is not None:
                        if ':p:' in right_pos_tag and ':p:' not in agreed_pos_tag:
                            agreed_pos_tag = jregex.java_replace(_MFN, ':p:', agreed_pos_tag, 1)
                        new_tokens.append(AnalyzedToken(word, agreed_pos_tag + extra_nv_tag + left_pos_tag_extra,
                                                        new_lemma))
                # noun-numr match
                elif _tag_starts(left_pos_tag, 'noun') and _tag_starts(right_pos_tag, 'numr'):
                    if lat.lemma != "п'ята":
                        # gender tags match
                        left_gender_conj = pth.get_gender_conj(left_pos_tag)
                        if left_gender_conj is not None and left_gender_conj == pth.get_gender_conj(right_pos_tag):
                            new_tokens.append(AnalyzedToken(word, left_pos_tag + extra_nv_tag + left_pos_tag_extra,
                                                            new_lemma))
                            # година-півтори може бути як одниною так і множиною: минула година-півтори, минули
                            # година-півтори
                            if ':p:' not in left_pos_tag:
                                new_tokens.append(AnalyzedToken(
                                    word, _MFN.sub(':p:', left_pos_tag) + extra_nv_tag + left_pos_tag_extra,
                                    new_lemma))
                        else:
                            # (with different gender tags): сотні (:p:) - дві (:f:)
                            agreed_pos_tag = _get_num_agreed_pos_tag(left_pos_tag, right_pos_tag, left_nv)
                            if agreed_pos_tag is not None:
                                new_tokens.append(AnalyzedToken(
                                    word, agreed_pos_tag + extra_nv_tag + left_pos_tag_extra, new_lemma))
                                # рік-два може бути як одниною так і множиною: минулий рік-два, минули рік-два
                                if ':p:' not in agreed_pos_tag:
                                    new_tokens.append(AnalyzedToken(
                                        word, _MFN.sub(':p:', agreed_pos_tag) + extra_nv_tag + left_pos_tag_extra,
                                        new_lemma))
                # noun-adj match: Буш-молодший, рік-два
                # не робимо братів-православних — загальний noun-adj дає забагато фальшивих спрацьовувань
                elif (left_pos_tag.startswith('noun') and _tag_starts(right_pos_tag, 'numr') or
                      (_tag_starts(right_pos_tag, 'adj') and self._is_junior_senior(lat, rat))):
                    left_gender_conj = pth.get_gender_conj(left_pos_tag)
                    if left_gender_conj is not None and left_gender_conj == pth.get_gender_conj(right_pos_tag):
                        new_tokens.append(AnalyzedToken(word, left_pos_tag + extra_nv_tag + left_pos_tag_extra,
                                                        new_lemma))
                # чарка-друга
                elif left_pos_tag.startswith('noun') and rat.lemma == 'другий':
                    left_gender_conj = pth.get_gender_conj(left_pos_tag)
                    if left_gender_conj is not None and left_gender_conj == pth.get_gender_conj(right_pos_tag):
                        right_lemma = 'другий' if left_gender_conj.startswith('m') else \
                            'друга' if left_gender_conj.startswith('f') else 'друге'
                        new_tokens.append(AnalyzedToken(word, left_pos_tag + extra_nv_tag + left_pos_tag_extra,
                                                        lat.lemma + '-' + right_lemma))

        if new_tokens and not pth.has_pos_tag_part(new_tokens, ':p:'):
            if (helpers.has_lemma(left_analyzed_tokens, helpers.DAYS_OF_WEEK) and
                helpers.has_lemma(right_analyzed_tokens, helpers.DAYS_OF_WEEK)) or \
                    (helpers.has_lemma(left_analyzed_tokens, helpers.MONTH_LEMMAS) and
                     helpers.has_lemma(right_analyzed_tokens, helpers.MONTH_LEMMAS)):
                new_tokens.append(AnalyzedToken(word, _MFN.sub(':p:', new_tokens[0].pos_tag), new_tokens[0].lemma))

        # remove duplicates
        new_tokens = list(dict.fromkeys(new_tokens))
        if not new_tokens:
            new_tokens = new_tokens_anim_inanim
        return new_tokens or None

    @staticmethod
    def _is_junior_senior(lat, rat):
        return _FLP_NAME.fullmatch(lat.pos_tag) is not None and _JUNIOR_SENIOR.fullmatch(rat.lemma) is not None

    def _get_agreed_pos_tag(self, left_pos_tag, right_pos_tag, left_nv, word):
        if _is_plural(left_pos_tag) != _is_plural(right_pos_tag):
            return None
        if not _is_same_anim_status(left_pos_tag, right_pos_tag):
            return None
        ml = _STD_NOUN_TAG_REGEX.fullmatch(left_pos_tag)
        if ml:
            mr = _STD_NOUN_TAG_REGEX.fullmatch(right_pos_tag)
            if mr:
                if ml.group(2) == mr.group(2):
                    if ml.group(1) != mr.group(1):
                        # yes for вчителька-педагог
                        # no for піт-стопа
                        if len(word) < 10:
                            return None
                    if left_nv:
                        return right_pos_tag
                    return left_pos_tag
        return None

    def _try_anim_inanim(self, left_pos_tag, right_pos_tag, left_lemma, right_lemma, left_nv, right_nv, word):
        left_master_set, follower_set = _data()[3], _data()[4]
        agreed_pos_tag = None
        # підприємство-банкрут
        if left_lemma in left_master_set:
            if _TAG_ANIM in left_pos_tag:
                right_pos_tag = right_pos_tag.replace(_TAG_INANIM, _TAG_ANIM)
            else:
                right_pos_tag = right_pos_tag.replace(_TAG_ANIM, _TAG_INANIM)
            agreed_pos_tag = self._get_agreed_pos_tag(left_pos_tag, right_pos_tag, left_nv, word)
            if agreed_pos_tag is None:
                if _TAG_ANIM not in left_pos_tag:
                    if _MNP_ZNA_REGEX.fullmatch(left_pos_tag) and _MNP_NAZ_REGEX.fullmatch(right_pos_tag) and \
                            not left_nv and not right_nv:
                        agreed_pos_tag = left_pos_tag
                else:
                    if _MNP_ZNA_REGEX.fullmatch(left_pos_tag) and _MNP_ROD_REGEX.fullmatch(right_pos_tag) and \
                            not left_nv and not right_nv:
                        agreed_pos_tag = left_pos_tag
        # сонях-красень
        elif right_lemma in follower_set:
            right_pos_tag = right_pos_tag.replace(':anim', ':inanim')
            agreed_pos_tag = self._get_agreed_pos_tag(left_pos_tag, right_pos_tag, False, word)
            if agreed_pos_tag is None:
                if _TAG_INANIM in left_pos_tag:
                    if _MNP_ZNA_REGEX.fullmatch(left_pos_tag) and _MNP_NAZ_REGEX.fullmatch(right_pos_tag) and \
                            pth.get_num(left_pos_tag) == pth.get_num(right_pos_tag) and not left_nv and not right_nv:
                        agreed_pos_tag = left_pos_tag
        # красень-сонях
        elif left_lemma in follower_set:
            left_pos_tag = left_pos_tag.replace(':anim', ':inanim')
            agreed_pos_tag = self._get_agreed_pos_tag(right_pos_tag, left_pos_tag, False, word)
            if agreed_pos_tag is None:
                if _TAG_INANIM in right_pos_tag:
                    if _MNP_ZNA_REGEX.fullmatch(right_pos_tag) and _MNP_NAZ_REGEX.fullmatch(left_pos_tag) and \
                            pth.get_num(left_pos_tag) == pth.get_num(right_pos_tag) and not left_nv and not right_nv:
                        agreed_pos_tag = right_pos_tag
        # else
        # рослин-людожерів, слалому-гіганту, місяця-князя, депутатів-привидів
        return agreed_pos_tag

    def _o_adj_match(self, word, analyzed_tokens, left_word):
        out = []
        left_base = left_word[:-1]
        extra_tag = ''
        if left_word.lower() not in _LEFT_O_ADJ:
            # яскраво для яскраво-барвистий, три-чотириметровий
            tagged_words = self.tag_both_cases(left_word, _ADV_NUMR)
            if not tagged_words:
                tagged_words = self.tag_both_cases(_o_to_yj(left_word), _ADJ_START)  # кричущий для кричуще-яскравий
            if not tagged_words and len(left_word) > 4:
                tagged_words = self.tag_both_cases(left_base, _NOUN_START)  # паталог для паталого-анатомічний
            if not tagged_words:
                # два для дво-триметровий, етико-філологічний
                tagged_words = self.tag_both_cases(left_base + 'а', _NOUN_F_NAZ_NUMR)
            if not tagged_words:
                return None

            # важконапрацьований - разом
            if extra_tag != ':bad':
                all_cap_tokens = self.tagger.analyze_all_capitalized_adj(word)
                if tagged_words[0].pos_tag.startswith('adv') and pth.has_pos_tag_part(analyzed_tokens, 'adjp'):
                    extra_tag = ':bad'
                elif pth.has_pos_tag_part2(tagged_words, ':bad'):
                    extra_tag = ':bad'
                # багато..., мало.... пишуться разом
                elif left_word.lower() in LEFT_O_ADJ_INVALID:
                    # do not mark Центрально-Східної as :bad
                    if not all_cap_tokens:
                        extra_tag = ':bad'
                else:
                    # do not mark Івано-Франківської as :bad
                    if not all_cap_tokens:
                        # марк високо-продуктивний as :bad
                        no_dash_word = word.replace('-', '')
                        no_dash_word_list = self._tag_as_is_and_with_lower_case(no_dash_word)
                        if no_dash_word_list:
                            extra_tag = ':bad'

        for at in analyzed_tokens:
            pos_tag = at.pos_tag
            if pos_tag.startswith('adj'):
                if ':comp' in pos_tag:
                    pos_tag = jregex.java_replace(pth.ADJ_COMP_REGEX, '', pos_tag, 1)
                if ':bad' in extra_tag:
                    pos_tag = pos_tag.replace(':arch', '')
                pos_tag = pth.add_if_not_contains(pos_tag, extra_tag)
                out.append(AnalyzedToken(word, pos_tag, left_word.lower() + '-' + at.lemma))
        return out or None

    def _numr_adj_match(self, word, analyzed_tokens, left_word):
        out = []
        extra_tag = ''
        tagged_words = self._tag(left_word)
        if not pth.has_pos_tag_start2(tagged_words, 'numr'):
            return None
        left_word_lower = left_word.lower()
        # двох-трьохметровий - bad
        if _DVOH.fullmatch(left_word_lower):
            extra_tag = ':bad'
        # три-метровий - bad
        elif analyzed_tokens and not _NUMR_PREFIXES.fullmatch(analyzed_tokens[0].token):
            extra_tag = ':bad'
        for at in analyzed_tokens:
            pos_tag = at.pos_tag
            if pos_tag.startswith('adj'):
                if ':comp' in pos_tag:
                    pos_tag = jregex.java_replace(pth.ADJ_COMP_REGEX, '', pos_tag, 1)
                if ':bad' not in pos_tag:
                    pos_tag += extra_tag
                out.append(AnalyzedToken(word, pos_tag, left_word_lower + '-' + at.lemma))
        return out or None

    def tag_both_cases(self, left_word, pos_tag_matcher):
        left_wd_list = self._tag(left_word)
        left_lower = left_word.lower()
        if left_word != left_lower:
            left_wd_list.extend(self._tag(left_lower))
        else:
            left_upper = uppercase_first_char(left_word) if left_word else left_word
            if left_word != left_upper:
                left_wd_list.extend(self._tag(left_upper))
        if pos_tag_matcher is not None:
            left_wd_list = [w for w in left_wd_list if pos_tag_matcher.fullmatch(w.pos_tag)]
        return left_wd_list

    def _tag_as_is_and_with_lower_case(self, left_word):
        left_wd_list = self._tag(left_word)
        left_lower = left_word.lower()
        if left_word != left_lower:
            left_wd_list.extend(self._tag(left_lower))
        return left_wd_list

    def guess_other_tags(self, word):
        if len(word) <= 7 or not _UKR_LETTERS_PATTERN.fullmatch(word):
            return None

        if is_capitalized_word(word):
            if word.endswith('штрассе') or word.endswith('штрасе'):
                add_pos = ':alt' if word.endswith('штрассе') else ''
                return pth.generate_tokens_for_nv(word, 'f', ':prop' + add_pos)
            if word.endswith('дзе') or word.endswith('швілі') or word.endswith('іані'):
                return pth.generate_tokens_for_nv(word, 'mf', ':prop:lname')

        lower = word.lower()
        for prefix in _data()[2]:
            if not lower.startswith(prefix):
                continue
            right = word[len(prefix):]
            apo = ''
            add_tag = []
            if right.startswith("'"):
                right = right[1:]
                apo = "'"
            if len(right) < 2:
                continue
            apo_needed = False
            if right[0] in 'єїюя' and prefix[-1] not in 'аеєиіїоуюя':
                apo_needed = True
            # екс'прес
            if not apo_needed and apo:
                break
            if apo_needed == (not apo):
                add_tag.append(':bad')

            if len(right) >= 4 and not is_capitalized_word(right):
                right_wd_list = pth.filter2(self._tag(right), _PREFIX_NO_DASH_POSTAG_PATTERN)
                right_wd_list = [w for w in right_wd_list
                                 if not (w.pos_tag.startswith('noun:inanim') and 'v_kly' in w.pos_tag)]
                if right_wd_list:
                    right_wd_list = pth.adjust(right_wd_list, prefix + apo, None, *add_tag)
                    return _tokens(word, right_wd_list)
        return None


def _get_num_agreed_pos_tag(left_pos_tag, right_pos_tag, left_nv):
    """right part is numr"""
    agreed_pos_tag = None
    if ':p:' in left_pos_tag and _SING_REGEX_F.search(right_pos_tag) or \
            _SING_REGEX_F.search(left_pos_tag) and ':p:' in right_pos_tag:
        left_conj = pth.get_conj(left_pos_tag)
        if left_conj is not None and left_conj == pth.get_conj(right_pos_tag):
            agreed_pos_tag = left_pos_tag
    return agreed_pos_tag


def _get_try_prefix(right_word):
    if _REQ_NUM_STO_PATTERN.fullmatch(right_word):
        return 'сто'
    if _REQ_NUM_DESYAT_PATTERN.fullmatch(right_word):
        return 'десяти'
    if _REQ_NUM_DVA_PATTERN.fullmatch(right_word):
        return 'дво'
    return None
