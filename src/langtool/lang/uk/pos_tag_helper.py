"""Port of org.languagetool.tagging.uk.PosTagHelper and IPOSTag.

The Java methods are overloaded for AnalyzedTokenReadings, lists of
AnalyzedToken, single AnalyzedToken and TaggedWord lists, and for String
regexes and compiled Patterns: here the functions accept a readings object
(anything iterable over readings with pos_tag), and regexes either as
strings (compiled with langtool.jregex) or compiled patterns."""

from ... import jregex
from ...analysis import PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME, AnalyzedToken
from ...tagging import TaggedWord


def _p(regex):
    return jregex.compile(regex) if isinstance(regex, str) else regex


# --- IPOSTag ---

class IPOSTag:
    """Port of the enum org.languagetool.tagging.uk.IPOSTag (the names are the
    texts of the enum constants)"""
    noun = 'noun'
    adj = 'adj'
    verb = 'verb'
    adv = 'adv'
    part = 'part'
    intj = 'intj'
    numr = 'numr'
    number = 'number'
    date = 'date'
    time = 'time'
    advp = 'advp'
    prep = 'prep'
    predic = 'predic'
    insert = 'insert'
    abbr = 'abbr'
    bad = 'bad'
    onomat = 'onomat'
    hashtag = 'hashtag'

    @staticmethod
    def match(tag, pos_tag_prefix):
        """IPOSTag.match: the pos tag (prefix) starts with the tag name"""
        return pos_tag_prefix is not None and pos_tag_prefix.startswith(tag)

    @staticmethod
    def is_num(pos_tag):
        return IPOSTag.match('numr', pos_tag) or IPOSTag.match('number', pos_tag)

    @staticmethod
    def contains(pos_tag, postag_match):
        return pos_tag is not None and postag_match in pos_tag

    @staticmethod
    def starts_with(pos_tag_prefix, *pos_tags):
        if pos_tag_prefix is None:
            return False
        for t in pos_tags:
            if pos_tag_prefix.startswith(t):
                return True
        return False


# --- PosTagHelper ---

NUM_REGEX = jregex.compile('(noun:(?:[iu]n)?anim|numr|adj|adjp.*):(.):v_.*')
CONJ_REGEX = jregex.compile('(noun:(?:[iu]n)?anim|numr|adj|adjp.*):[mfnp]:(v_...).*')
GENDER_REGEX = NUM_REGEX
GENDER_CONJ_REGEX = jregex.compile('(noun:(?:[iu]n)?anim|adj|numr|adjp.*):(.:v_...).*')
_CLEANUP_PATTERN = jregex.compile(':(comp.|adjp:.*?(:(im)?perf)+)')

ADJ_COMP_REGEX = jregex.compile(':comp[bcs]')
# LinkedHashMap
VIDMINKY_MAP = {
    'v_naz': 'називний',
    'v_rod': 'родовий',
    'v_dav': 'давальний',
    'v_zna': 'знахідний',
    'v_oru': 'орудний',
    'v_mis': 'місцевий',
    'v_kly': 'кличний',
}
# a HashMap in Java (only used for lookups)
VIDMINKY_I_MAP = dict(VIDMINKY_MAP, v_inf='інфінітив')
GENDER_MAP = {
    'm': 'ч.р.',
    'f': 'ж.р.',
    'n': 'с.р.',
    'p': 'мн.',
    's': 'одн.',
    'i': 'інф.',
    'o': 'безос. форма',
}
BASE_GENDERS = ('m', 'f', 'n', 'p')
PERSON_MAP = {
    '1': '1-а особа',
    '2': '2-а особа',
    '3': '3-я особа',
    's': 'одн.',
    'p': 'мн.',
}
NO_VIDMINOK_SUBSTR = ':nv'

NOUN_V_NAZ_PATTERN = jregex.compile('noun.*:v_naz.*')
NOUN_NON_PRON_V_NAZ_PATTERN = jregex.compile('noun.*:v_naz(?!.*pron).*')
ADJ_V_NAZ_PATTERN = jregex.compile('adj:.:v_naz.*')
VERB_INF_PATTERN = jregex.compile('verb.*:inf.*')
ADJ_V_KLY_PATTERN = jregex.compile('adj:.:v_kly.*')
VERB_PATTERN = jregex.compile('verb.*')
VERB_ADVP_PATTERN = jregex.compile('(verb|advp).*')


def _readings(r):
    if isinstance(r, (AnalyzedToken, TaggedWord)):
        return (r,)
    return r


def get_gender(pos_tag):
    m = GENDER_REGEX.fullmatch(pos_tag)
    return m.group(2) if m else None


def get_num(pos_tag):
    m = NUM_REGEX.fullmatch(pos_tag)
    if m:
        g = m.group(2)
        return g if g == 'p' else 's'
    return None


def get_conj(pos_tag):
    m = CONJ_REGEX.fullmatch(pos_tag)
    return m.group(2) if m else None


def get_gender_conj(pos_tag):
    m = GENDER_CONJ_REGEX.fullmatch(pos_tag)
    return m.group(2) if m else None


def has_pos_tag(readings, pos_tag_regex):
    """hasPosTag(AnalyzedTokenReadings|List<AnalyzedToken>|AnalyzedToken|
    TaggedWord, Pattern|String): one of the readings has a pos tag that
    fully matches the regex"""
    p = _p(pos_tag_regex)
    for r in _readings(readings):
        t = r.pos_tag
        if t is not None and p.fullmatch(t):
            return True
    return False


def has_pos_tag_part(readings, pos_tag_part):
    for r in _readings(readings):
        t = r.pos_tag
        if t is not None and pos_tag_part in t:
            return True
    return False


def has_pos_tag_part_all(readings, pos_tag_part):
    found = False
    for r in _readings(readings):
        t = r.pos_tag
        if t is not None and t != SENTENCE_END_TAGNAME and t != PARAGRAPH_END_TAGNAME:
            if pos_tag_part not in t:
                return False
            found = True
    return found


def has_pos_tag_all(readings, pos_tag):
    p = _p(pos_tag)
    found = False
    for r in _readings(readings):
        t = r.pos_tag
        if t is not None and t != SENTENCE_END_TAGNAME and t != PARAGRAPH_END_TAGNAME:
            if not p.fullmatch(t):
                return False
            found = True
    return found


def has_pos_tag_start(readings, pos_tag_part):
    for r in _readings(readings):
        t = r.pos_tag
        if t is not None and t.startswith(pos_tag_part):
            return True
    return False


# the TaggedWord list variants (same implementation)
has_pos_tag_part2 = has_pos_tag_part
has_pos_tag2 = has_pos_tag
has_pos_tag_start2 = has_pos_tag_start


def get_genders(token_readings, pos_tag_regex):
    p = _p(pos_tag_regex)
    sb = []
    for r in token_readings:
        t = r.pos_tag
        if t is not None and p.fullmatch(t):
            g = get_gender(t)
            if g is not None and g not in sb:
                sb.append(g)
    return ''.join(sb)


def generate_tokens_for_nv(word, genders, extra_tags):
    out = []
    for gen in genders:
        base = 'noun:inanim:' + gen + ':'
        for vidm in VIDMINKY_MAP:
            if vidm == 'v_kly':
                continue
            pos_tag = base + vidm + NO_VIDMINOK_SUBSTR
            if extra_tags is not None:
                pos_tag += extra_tags
            out.append(AnalyzedToken(word, pos_tag, word))
    return out


def add_if_not_contains(tag, *add_tags):
    """addIfNotContains(String tag, String... addTags) (the single argument
    version also ignores null/empty)"""
    for a in add_tags:
        if a and a not in tag:
            tag += a
    return tag


def add_if_not_contains_words(tagged_words, add_tag, lemma=None):
    """addIfNotContains(List<TaggedWord>, addTag, lemma)"""
    return [TaggedWord(lemma if lemma is not None else w.lemma, add_if_not_contains(w.pos_tag, add_tag))
            for w in tagged_words]


def adjust(tagged_words, lemma_prefix=None, lemma_suffix=None, *add_tags):
    return [TaggedWord(_adjust_lemma(w, lemma_prefix, lemma_suffix),
                       add_if_not_contains(_clean_extra_tags(w.pos_tag), *add_tags))
            for w in tagged_words]


def _adjust_lemma(w, lemma_prefix, lemma_suffix):
    lemma = w.lemma
    if lemma_prefix is not None:
        lemma = lemma_prefix + lemma
    if lemma_suffix is not None:
        lemma += lemma_suffix
    return lemma


def _clean_extra_tags(tag):
    if tag is not None:
        tag = _CLEANUP_PATTERN.sub('', tag)
    return tag


def filter_tokens(analyzed_tokens, pos_tag):
    """filter(List<AnalyzedToken>, Pattern)"""
    p = _p(pos_tag)
    return [t for t in analyzed_tokens if t.pos_tag is not None and p.fullmatch(t.pos_tag)]


filter2 = filter_tokens


def filter2_negative(analyzed_tokens, pos_tag):
    p = _p(pos_tag)
    return [t for t in analyzed_tokens if not (t.pos_tag is not None and p.fullmatch(t.pos_tag))]


_WORD_PATTERN = jregex.compile("[а-яіїєґa-z'-]+", jregex.IGNORECASE)


def is_unknown_word(atr):
    return atr.readings[0].has_no_tag() and _WORD_PATTERN.fullmatch(atr.token) is not None


_PREDICT_INSERT_PATTERN = jregex.compile('noninfl:(predic|insert).*')


def is_predict_or_insert(token):
    return _PREDICT_INSERT_PATTERN.fullmatch(token.pos_tag) is not None


def filter_with_token(tokens, postag, token):
    """filter(AnalyzedTokenReadings, Pattern postag, Pattern token)"""
    pp = _p(postag)
    tp = _p(token)
    return [t for t in tokens.readings
            if t.pos_tag is not None and pp.fullmatch(t.pos_tag) and t.token is not None and tp.fullmatch(t.token)]


def has_pos_tag_and_token(tokens, postag, token):
    return len(filter_with_token(tokens, postag, token)) > 0


_MALE_UA_TAG = jregex.compile('noun:inanim:m:v_dav(?!:nv).*')
_MALE_UA_TOKEN = jregex.compile('.*[ую]')


def has_male_ua(token_readings):
    return has_pos_tag_and_token(token_readings, _MALE_UA_TAG, _MALE_UA_TOKEN)
