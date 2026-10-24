"""Ports of the helper classes of org.languagetool.rules.ca:
PronomsFeblesHelper, ApostophationHelper, VerbsHelper and
NounToVerbHelper."""

from ... import jregex
from ...tools import java_equals_ignore_case, java_trim

# --- ApostophationHelper ---------------------------------------------------

_PREP_DET = {
    'MS': 'el ', 'FS': 'la ', 'MP': 'els ', 'FP': 'les ', 'MSapos': "l'", 'FSapos': "l'",
    'aMS': 'al ', 'aFS': 'a la ', 'aMP': 'als ', 'aFP': 'a les ', 'aMSapos': "a l'", 'aFSapos': "a l'",
    'dMS': 'del ', 'dFS': 'de la ', 'dMP': 'dels ', 'dFP': 'de les ', 'dMSapos': "de l'", 'dFSapos': "de l'",
    'pMS': 'pel ', 'pFS': 'per la ', 'pMP': 'pels ', 'pFP': 'per les ', 'pMSapos': "per l'", 'pFSapos': "per l'",
}

# Patterns for apostrophation
P_APOSTROPHE_MASC_YES = jregex.compile('h?[aeiouàèéíòóú].*', jregex.IGNORECASE)
P_APOSTROPHE_MASC_NO = jregex.compile('h?[ui][aeioàèéóò].+', jregex.IGNORECASE)
P_APOSTROPHE_FEM_YES = jregex.compile('h?[aeoàèéíòóú].*|h?[ui][^aeiouàèéíòóúüï]+[aeiou][ns]?|urbs', jregex.IGNORECASE)
P_APOSTROPHE_FEM_NO = jregex.compile('host|ira|inxa', jregex.IGNORECASE)
# (Java: Pattern.CASE_INSENSITIVE without UNICODE_CASE)
P_APOSTROPHE_NEEDED_END = jregex.compile('(?i)' + '.*[aei]')
# From mots_HAC_ASPIRADA2 and mots_HAC_ASPIRADA in entities.ent
P_HAC_ASPIRADA = jregex.compile(
    'Higgs|high|Hildesheim|Hill|hijabs?|Hillary|Himmler|hip-hop|hippies|hippy|hipsters?|Hirado|His|hits?|Hubei|'
    'Hudson|Hunter|Husserl|Huygens|husky|Utah|hides?|honey.*|Hartle.*|happy|happi.*|Hulk|Heart.*|Haakon|'
    'Halberstadt|Harley|Huck.*|Hanna|haka|hakes|Hama|Hornbostel|Heidi|Hayao|Hansi|Haas|Hindemith|user|users|one|'
    'head|history|Human|Hampshire|Hovedstaden|Handmade|Helm|Hahnem.*|hikimor.*|Houdini|Hugging|Heritage|hardcore|'
    'hancock|hender.*|h[ei][zs]b[ou]l.*|harira|Hawth.*|Henk.*|Humphry|Hohle|Höhle|Hooke|hajj.*|Hochschule|Hoch.*|'
    'Hutt|Hansel|Henley|hook|Handstand|Hull|Hatshepsut|Hatchepsut|Hana|Hamri|Hanley|Halis|Huxley|Hess|Hatteras|'
    'Herzberg|Hanlon|Harriet|hawl.*|hard|hip|herderi.*|Hangouts|Hayes|hostings?|Hal|hajj|Hermann|Hannah|'
    'Hertzsprung|Hotmail|Homrani|Harris|Harvey|Hunspell|Hassan|Haddock|Haarle[mn].*|Hainan|haendel.*|händel.*|'
    'habermas.*|hadits?|Hanuk?kà|hack.*|Harlem|Harper|Hartford|Haifa|haikus?|haima|haimes|Haikou|halal|halar|'
    'Halifax|Halmstad|halls?|Halle|Halley|Hallstatt|Hallstein|Halloweens?|Hals|herr|Herut|Hamadan|Hamas|Hamàs|'
    'hamilton.*|Hamlet.*|hammams?|Hammond|Hampton|hàmsters?|h[aà]ndicaps?|Hangzhou|Hannover|Hanoi|Hans|Hansa|'
    'hanseàti[cq].*|happenings?|Harbin|hardware|Haneke|harolds?|Hatay|Hamleigh |Harrisburg|Harrison|harrods?|harry|'
    'Hartley|Hartmann?|Hartree|Haruki|Har[td]?vard|Harz|hash.*|Hastings|Havel|Havilland|hawai.*|hawk.*|Hayek|'
    'Haydn.*|Hayworth|Heard|hearst|Heathrow|heav.*|hegel.*|Hebei|Hedmark|Heerenveen|Hedw.*|Heerlen|Hefei|'
    'Heidelberg|Heide[gn].*|Heilbronn|Heilongjiang|Heilig.*|hei[nk].*|Heisen.*|Heitz|Helmand|Helmholtz|Helen|'
    'Helsingborg|Hèlsinki|Heming.*|Henan|henna|hennes|Henry|Hepburn|herbert.*|Herder|Hereford|Herford|Herning|'
    'Hertfordshire|Herzog|Hesse|Hessen.*|Hewlett.*|H[ie]zbol·?l.+|high.*|hilbert.*|Hilda|Hillingdon|hinden.*|'
    'Hilton|hinterlands?|Hirsch.*|Hitch.*|hitler.*|Hilversum|Hobart|Hockenheim|Hodeida|Hohhot|Hokkaido|hobbes.*|'
    'hobby|Hogw.*|hobbies|Hodgkin|Hohen.*|Hölderlin|h[òo]ldings?|holy.*|hollywood.*|Holmes.*|Holstein|Hong|'
    'Hong-Kong|hongk.+|Honolu.+|Honsh[uū]|h[òo]bbits?|hooligan.*|hoover.*|hopkins|Hork.*|Horowitz|horst|H[ou]f.*|'
    'Houla|house|Houston|Howard|Hoyerswerda|Hunan|Huddersfield|Hunedoara|huskys?|huskies|hubs?|Hubble|humbold.*|'
    'Hume|hunting.*|Hussein|husseinit.+|Unity|university|united.*|European|OneDrive',
    jregex.IGNORECASE)


def get_preposition_and_determiner(new_form, gender_number, preposition):
    """ApostophationHelper.getPrepositionAndDeterminer"""
    apos = ''  # s'apostrofa o no
    if gender_number.startswith('C'):
        gender_number = 'M' + gender_number[1]
    if gender_number.endswith('N'):
        gender_number = gender_number[0] + 'S'
    if preposition:
        # a=a d=de per=p
        preposition = preposition[:1].lower()
    if not P_HAC_ASPIRADA.fullmatch(new_form):
        if gender_number == 'MS':
            if P_APOSTROPHE_MASC_YES.fullmatch(new_form) and not P_APOSTROPHE_MASC_NO.fullmatch(new_form):
                apos = 'apos'
        elif gender_number == 'FS':
            if P_APOSTROPHE_FEM_YES.fullmatch(new_form) and not P_APOSTROPHE_FEM_NO.fullmatch(new_form):
                apos = 'apos'
    return _PREP_DET.get(preposition + gender_number + apos)


def needs_apostrophation_ms(word):
    """ApostophationHelper.needsApostrophationMS"""
    return (P_APOSTROPHE_MASC_YES.fullmatch(word) is not None and not P_APOSTROPHE_MASC_NO.fullmatch(word)
            and not P_HAC_ASPIRADA.fullmatch(word))


def all_need_same_apostrophation_ms(firstword, words):
    """ApostophationHelper.allNeedSameApostrophationMS"""
    if not words:
        return True
    first = needs_apostrophation_ms(firstword)
    return all(needs_apostrophation_ms(w.lemma) == first for w in words)


# --- PronomsFeblesHelper ---------------------------------------------------

# PronounPosition (the ordinal is the index in each group of _PRONOMS_FEBLES)
DAVANT = 0
DAVANT_APOS = 1
DARRERE = 2
DARRERE_APOS = 3
DARRERE_NOGUIONET_NOAPOS = 4
DARRE_APOS_NOGUIONET_NOAPOS = 5
NORMALIZED = 6
_NUM_POSITIONS = 7

_PRONOMS_FEBLES = (
    'el', "l'", '-lo', "'l", 'lo', 'l', 'el', 'els el', "els l'", '-los-el', "'ls-el", 'losel', 'lsel', 'els el',
    'els els', 'els els', '-los-els', "'ls-els", 'losels', 'lsels', 'els els', 'els en', "els n'", '-los-en',
    "'ls-en", 'losen', 'lsen', 'els en', 'els hi', 'els hi', '-los-hi', "'ls-hi", 'loshi', 'lshi', 'els hi',
    'els ho', 'els ho', '-los-ho', "'ls-ho", 'losho', 'lsho', 'els ho', 'els la', "els l'", '-los-la', "'ls-la",
    'losla', 'lsla', 'els la', 'els les', 'els les', '-los-les', "'ls-les", 'losles', 'lsles', 'els les', 'els',
    'els', '-los', "'ls", 'los', 'ls', 'els', 'em', "m'", '-me', "'m", 'me', 'm', 'em', 'en', "n'", '-ne', "'n",
    'ne', 'n', 'en', 'ens el', "ens l'", '-nos-el', "'ns-el", 'nosel', 'nsel', 'ens el', 'ens els', 'ens els',
    '-nos-els', "'ns-els", 'nosels', 'nsels', 'ens els', 'ens en', "ens n'", '-nos-en', "'ns-en", 'nosen', 'nsen',
    'ens en', 'ens hi', 'ens hi', '-nos-hi', "'ns-hi", 'noshi', 'nshi', 'ens hi', 'ens ho', 'ens ho', '-nos-ho',
    "'ns-ho", 'nosho', 'nsho', 'ens ho', 'ens la', "ens l'", '-nos-la', "'ns-la", 'nosla', 'nsla', 'ens la',
    'ens les', 'ens les', '-nos-les', "'ns-les", 'nosles', 'nsles', 'ens les', 'ens li', 'ens li', '-nos-li',
    "'ns-li", 'nosli', 'nsli', 'ens li', 'ens', 'ens', '-nos', "'ns", 'nos', 'ns', 'ens', 'es', "s'", '-se', "'s",
    'se', 's', 'es', 'et', "t'", '-te', "'t", 'te', 't', 'et', 'hi', 'hi', '-hi', '-hi', 'hi', 'hi', 'hi', 'ho',
    'ho', '-ho', '-ho', 'ho', 'ho', 'ho', "l'en", "el n'", "-l'en", "-l'en", 'len', 'len', 'el en', "l'hi", "l'hi",
    "-l'hi", "-l'hi", 'lhi', 'lhi', 'el hi', 'la hi', 'la hi', '-la-hi', '-la-hi', 'lahi', 'lahi', 'la hi', 'la',
    "l'", '-la', '-la', 'la', 'la', 'la', "la'n", "la n'", "-la'n", "-la'n", 'lan', 'lan', 'la en', 'les en',
    "les n'", '-les-en', '-les-en', 'lesen', 'lesen', 'les en', 'les hi', 'les hi', '-les-hi', '-les-hi', 'leshi',
    'leshi', 'les hi', 'les', 'les', '-les', '-les', 'les', 'les', 'les', 'li hi', 'li hi', '-li-hi', '-li-hi',
    'lihi', 'lihi', 'li hi', 'li ho', 'li ho', '-li-ho', '-li-ho', 'liho', 'liho', 'li ho', 'li la', "li l'",
    '-li-la', '-li-la', 'lila', 'lila', 'li la', 'li les', 'li les', '-li-les', '-li-les', 'liles', 'liles',
    'li les', 'li', 'li', '-li', '-li', 'li', 'li', 'li', "li'l", "li l'", "-li'l", "-li'l", 'lil', 'lil', 'li el',
    "li'ls", "li'ls", "-li'ls", "-li'ls", 'lils', 'lils', 'li els', "li'n", "li n'", "-li'n", "-li'n", 'lin', 'lin',
    'li en', "m'hi", "m'hi", "-m'hi", "-m'hi", 'mhi', 'mhi', 'em hi', "m'ho", "m'ho", "-m'ho", "-m'ho", 'mho', 'mho',
    'em ho', 'me la', "me l'", '-me-la', '-me-la', 'mela', 'mela', 'em la', 'me les', 'me les', '-me-les', '-me-les',
    'meles', 'meles', 'em les', 'me li', 'me li', '-me-li', '-me-li', 'meli', 'meli', 'em li', "me'l", "me l'",
    "-me'l", "-me'l", 'mel', 'mel', 'em el', "me'ls", "me'ls", "-me'ls", "-me'ls", 'mels', 'mels', 'em els', "me'n",
    "me n'", "-me'n", "-me'n", 'men', 'men', 'em en', "n'hi", "n'hi", "-n'hi", "-n'hi", 'nhi', 'nhi', 'en hi',
    "s'hi", "s'hi", "-s'hi", "-s'hi", 'shi', 'shi', 'es hi', "s'ho", "s'ho", "-s'ho", "-s'ho", 'sho', 'sho', 'es ho',
    'se la', "se l'", '-se-la', '-se-la', 'sela', 'sela', 'es la', 'se les', 'se les', '-se-les', '-se-les', 'seles',
    'seles', 'es les', 'se li', 'se li', '-se-li', '-se-li', 'seli', 'seli', 'es li', 'se us', 'se us', '-se-us',
    '-se-us', 'seus', 'seus', 'es us', 'se vos', 'se vos', '-se-vos', '-se-vos', 'sevos', 'sevos', 'es vos', "se'l",
    "se l'", "-se'l", "-se'l", 'sel', 'sel', 'es el', "se'ls", "se'ls", "-se'ls", "-se'ls", 'sels', 'sels', 'es els',
    "se'm", "se m'", "-se'm", "-se'm", 'sem', 'sem', 'es em', "se'n", "se n'", "-se'n", "-se'n", 'sen', 'sen',
    'es en', "se'ns", "se'ns", "-se'ns", "-se'ns", 'sens', 'sens', 'es ens', "se't", "se t'", "-se't", "-se't",
    'set', 'set', 'es et', "t'hi", "t'hi", "-t'hi", "-t'hi", 'thi', 'thi', 'et hi', "t'ho", "t'ho", "-t'ho", "-t'ho",
    'tho', 'tho', 'et ho', 'te la', "te l'", '-te-la', '-te-la', 'tela', 'tela', 'et la', 'te les', 'te les',
    '-te-les', '-te-les', 'teles', 'teles', 'et les', 'te li', 'te li', '-te-li', '-te-li', 'teli', 'teli', 'et li',
    "te'l", "te l'", "-te'l", "-te'l", 'tel', 'tel', 'et el', "te'ls", "te'ls", "-te'ls", "-te'ls", 'tels', 'tels',
    'et els', "te'm", "te m'", "-te'm", "-te'm", 'tem', 'tem', 'et em', "te'n", "te n'", "-te'n", "-te'n", 'ten',
    'ten', 'et en', "te'ns", "te'ns", "-te'ns", "-te'ns", 'tens', 'tens', 'et ens', 'us el', "us l'", '-vos-el',
    '-us-el', 'vosel', 'usel', 'us el', 'us els', 'us els', '-vos-els', '-us-els', 'vosels', 'usels', 'us els',
    'us em', "us m'", '-vos-em', '-us-em', 'vosem', 'usem', 'us em', 'us en', "us n'", '-vos-en', '-us-en', 'vosen',
    'usen', 'us en', 'us ens', 'us ens', '-vos-ens', '-us-ens', 'vosens', 'usens', 'us ens', 'us hi', 'us hi',
    '-vos-hi', '-us-hi', 'voshi', 'ushi', 'us hi', 'us ho', 'us ho', '-vos-ho', '-us-ho', 'vosho', 'usho', 'us ho',
    'us la', "us l'", '-vos-la', '-us-la', 'vosla', 'usla', 'us la', 'us les', 'us les', '-vos-les', '-us-les',
    'vosles', 'usles', 'us les', 'us li', 'us li', '-vos-li', '-us-li', 'vosli', 'usli', 'us li', 'us', 'us', '-vos',
    '-us', 'vos', 'us', 'us', "se me'n", "se me n'", "-se-me'n", "-se-me'n", 'semen', 'semen', 'es em en', "se te'n",
    "se te n'", "-se-te'n", "-se-te'n", 'seten', 'seten', 'es et en', "se li'n", "se li n'", "-se-li'n", "-se-li'n",
    'selin', 'selin', 'es li en', "se'ns en", "se'ns n'", "-se'ns-en", "-se'ns-en", 'sensen', 'sensen', 'es ens en',
    'se us en', "se us n'", '-se-us-en', '-se-us-en', 'seusen', 'seusen', 'es us en', 'se vos en', "se vos n'",
    '-se-vos-en', '-se-vos-en', 'sevosen', 'sevosen', 'es vos en', "se'ls en", "se'ls n'", "-se'ls-en", "-se'ls-en",
    'selsen', 'selsen', 'es els en',
)

_INCORRECT_ORDERS = {
    'me se': "se'm", "me s'": "se m'", 'te se': "se't", "te s'": "se t'", 'li se': 'se li', "li s'": 'se li',
    'mi': "m'hi", 'si': "s'hi", 'nosi': '-nos-hi', 'losi': '-los-hi', 'lis': 'els', "m'en": "me'n",
    "t'en": "te'n", "s'en": "se'n",
}

P_PRONOM_FEBLE = jregex.compile('P0.{6}|PP3CN000|PP3NN000|PP3..A00|PP[123]CP000|PP3CSD00')

_REFLEXIVE_PRONOUN = {'1S': 'em', '2S': 'et', '3S': 'es', '1P': 'ens', '2P': 'us', '3P': 'es'}
_DATIVE_PRONOUN = {'1S': 'em', '2S': 'et', '3S': 'li', '3C': 'li', '1P': 'ens', '2P': 'us', '3P': 'els'}


def get_reflexive_pronoun(key):
    return _REFLEXIVE_PRONOUN.get(key, '')


def get_dative_pronoun(key):
    return _DATIVE_PRONOUN.get(key, '')


def transform(input_pronom, pronoun_pos):
    """PronomsFeblesHelper.transform"""
    input_pronom = java_trim(input_pronom.lower())
    input_pronom = _INCORRECT_ORDERS.get(input_pronom, input_pronom)
    i = 0
    n = len(_PRONOMS_FEBLES)
    while i < n and not java_equals_ignore_case(input_pronom, _PRONOMS_FEBLES[i]):
        i += 1
    pf_pos = _NUM_POSITIONS * (i // _NUM_POSITIONS) + pronoun_pos
    if pf_pos > n - 1:
        # pronom inexistent, p.ex. -t
        return ''
    pronom = _PRONOMS_FEBLES[pf_pos]
    if pronoun_pos == DAVANT or (pronoun_pos == DAVANT_APOS and not pronom.endswith("'")):
        pronom = pronom + ' '
    return pronom


def transform_davant(input_pronom, next_word):
    """PronomsFeblesHelper.transformDavant"""
    next_word = next_word.lower()
    if needs_apostrophation_ms(next_word):
        return transform(input_pronom, DAVANT_APOS)
    pronom = transform(input_pronom, DAVANT)
    # se senten, se cenyeix...
    if pronom == 'es ' and (next_word.startswith('s') or next_word.startswith('ce') or next_word.startswith('ci')):
        return 'se '
    return pronom


def transform_darrere(input_pronom, previous_word):
    """PronomsFeblesHelper.transformDarrere"""
    if P_APOSTROPHE_NEEDED_END.fullmatch(previous_word):
        return transform(input_pronom, DARRERE_APOS)
    return transform(input_pronom, DARRERE)


def do_add_pronoun_en(pronouns_str, verb_str, pronouns_after):
    pronoun_normalized = transform(pronouns_str, NORMALIZED)
    if pronoun_normalized.endswith('hi'):
        pronoun_normalized = pronoun_normalized.replace('hi', 'en hi')
    else:
        pronoun_normalized += ' en'
    if pronouns_after:
        return transform_darrere(pronoun_normalized, verb_str)
    return transform_davant(pronoun_normalized, verb_str)


_REFLEXIVE_TO_REMOVE = jregex.compile('(?i)(em|et|es|ens|us|vos)')


def do_remove_pronoun_reflexive(pronouns_str, verb_str, pronouns_after):
    pronouns_replacement = java_trim(jregex.java_replace(
        _REFLEXIVE_TO_REMOVE, '', transform(pronouns_str.lower(), NORMALIZED), 1))
    replacement = verb_str
    if pronouns_after:
        pronouns_replacement = transform_darrere(pronouns_replacement, verb_str)
        if pronouns_replacement:
            replacement = verb_str + pronouns_replacement
        return replacement
    pronouns_replacement = transform_davant(pronouns_replacement, verb_str)
    if pronouns_replacement:
        replacement = pronouns_replacement + verb_str
    return replacement


_CONTAINS_REFLEXIVE_PRONOUN = jregex.compile(".*([mts][e']|[e'][mts]|vos|us|ens|-nos|-vos).*")
REFLEXIVE_PRONOUNS = ('em', 'et', 'es', 'ens', 'us', 'vos')


def do_add_pronoun_reflexive(pronouns_str, verb_str, first_verb_persona_number, pronouns_after):
    if pronouns_after:
        if _CONTAINS_REFLEXIVE_PRONOUN.fullmatch(pronouns_str.lower()):
            return verb_str + transform_darrere(pronouns_str, verb_str)
        if verb_str.endswith('r') or verb_str.endswith('re'):
            return verb_str + transform_darrere('-se', verb_str)
        return verb_str
    pronoun_to_add = transform(pronouns_str, NORMALIZED)
    if not _contains_any_reflexive_pronoun(pronouns_str.lower()):
        pronoun_to_add = get_reflexive_pronoun(first_verb_persona_number) + ' ' + pronoun_to_add
    return transform_davant(pronoun_to_add, verb_str) + verb_str


def _contains_any_reflexive_pronoun(pronouns_str):
    normalized_pronouns = transform(pronouns_str.lower(), NORMALIZED).split(' ')
    return any(p in REFLEXIVE_PRONOUNS for p in normalized_pronouns)


def do_add_pronoun_reflexive_en(pronouns_str, verb_str, first_verb_persona_number, pronouns_after):
    if pronouns_after:
        if _CONTAINS_REFLEXIVE_PRONOUN.fullmatch(pronouns_str.lower()):
            return verb_str + transform_darrere(pronouns_str + "'n", verb_str)  # no sempre correcte
        return verb_str + transform_darrere("-se'n", verb_str)
    if not pronouns_str:
        pronoun_to_add = transform_davant(get_reflexive_pronoun(first_verb_persona_number) + ' en', verb_str)
        return pronoun_to_add + verb_str
    pronoun_to_add = transform_davant('es ' + transform(pronouns_str, NORMALIZED) + ' en', verb_str)
    # TODO: add reflexive pronoun to another pronoun
    return pronoun_to_add + verb_str


def do_add_pronoun_reflexive_imperative(pronouns_str, verb_str, first_verb_persona_number):
    replacement = ''
    if not pronouns_str:
        pronoun_to_add = transform_darrere(get_reflexive_pronoun(first_verb_persona_number), verb_str)
        replacement = verb_str + pronoun_to_add
    return replacement


def do_replace_em_en(pronouns_str, verb_str, pronouns_after):
    replacement = ''
    if java_equals_ignore_case(pronouns_str, 'em'):
        replacement = 'en' + ' ' + verb_str
    if java_equals_ignore_case(pronouns_str, "m'"):
        replacement = "n'" + verb_str
    if java_equals_ignore_case(pronouns_str, "m'hi"):
        replacement = "n'hi " + verb_str
    return replacement


def do_replace_hi_en(pronouns_str, verb_str, pronouns_after):
    replacement = ''
    if java_equals_ignore_case(pronouns_str, 'hi'):
        replacement = 'en' + ' ' + verb_str
    if java_equals_ignore_case(pronouns_str, "m'"):
        replacement = "n'" + verb_str
    if java_equals_ignore_case(pronouns_str, "m'hi"):
        replacement = "n'hi " + verb_str
    return replacement


def convert_pronouns_for_intransitive_verb(s):
    return (s.replace("-se'l", '-se-li').replace("se'l ", 'se li ').replace("l'", 'li ').replace('-lo', '-li')
            .replace('-la', '-li').replace('la ', 'li ').replace('el ', 'li ').replace('ho', 'hi'))


# (Java: Pattern.CASE_INSENSITIVE without UNICODE_CASE)
_DE_WRONG_APOSTROPHATION = jregex.compile("(?i).*d'[^aeiouh].*")
_PRONOUN_WRONG_APOSTROPHATION = jregex.compile("(?i)([mts])'([^aeiouh].*)")
_PRONOUN_MISSING_APOSTROPHATION = jregex.compile('(?i)(.*)\\be([stm]) (h?[aeiouh].*)')
_PRONOUN_WRONG_HYPPHEN = jregex.compile('(?i)(.*)(-[stm])e-(h[oi])')


def fix_apostrophes(s):
    """PronomsFeblesHelper.fixApostrophes"""
    if _DE_WRONG_APOSTROPHATION.fullmatch(s):
        s = s.replace("d'", 'de ')
    m = _PRONOUN_MISSING_APOSTROPHATION.fullmatch(s)
    if m:
        s = m.group(1) + m.group(2) + "'" + m.group(3)
    m = _PRONOUN_WRONG_APOSTROPHATION.fullmatch(s)
    if m:
        s = 'e' + m.group(1) + ' ' + m.group(2)
    m = _PRONOUN_WRONG_HYPPHEN.fullmatch(s)
    if m:
        s = m.group(1) + m.group(2) + "'" + m.group(3)
    return s


# --- VerbsHelper -----------------------------------------------------------

_VERBS_DICENDI = frozenset((
    'amollar', 'afluixar', 'entaferrar', 'espletar', 'soltar', 'engaltar', 'acceptar', 'aclarir', 'aconsellar',
    'acusar', 'adduir', 'admetre', 'advertir', 'afegir', 'afirmar', 'agregar', 'al·legar', 'al·ludir', 'amenaçar',
    'amonestar', 'ampliar', 'anunciar', 'apuntar', 'argumentar', 'assegurar', 'assentir', 'assenyalar', 'atorgar',
    'atribuir', 'avançar', 'avisar', 'barbotejar', 'bordar', 'bramar', 'calcular', 'callar', 'citar', 'comentar',
    'concedir', 'concloure', 'concretar', 'confessar', 'confiar', 'confirmar', 'considerar', 'contestar', 'creure',
    'cridar', 'culpar', 'decidir', 'declamar', 'declarar', 'decretar', 'defensar', 'definir', 'delimitar', 'demanar',
    'descobrir', 'descriure', 'desitjar', 'desmentir', 'destacar', 'desvelar', 'detallar', 'determinar', 'dir',
    'dogmatitzar', 'dubtar', 'elogiar', 'emfasitzar', 'emfatitzar', 'engegar', 'enumerar', 'esclafir', 'escopir',
    'escridassar', 'esgrimir', 'esmentar', 'especificar', 'establir', 'etzibar', 'exclamar', 'exigir', 'explicar',
    'exposar', 'expressar', 'formular', 'garantir', 'gemegar', 'imaginar', 'implorar', 'imputar', 'increpar',
    'indicar', 'informar', 'inquirir', 'insinuar', 'insistir', 'insultar', 'interrogar', 'intervenir', 'ironitzar',
    'jurar', 'justificar', 'lamentar', 'lladrar', 'lloar', 'maleir', 'manar', 'manifestar', 'matisar', 'mentir',
    'mostrar', 'murmurar', 'negar', 'observar', 'oferir', 'opinar', 'ordenar', 'pensar', 'plantejar', 'pontificar',
    'pregar', 'preguntar', 'presumir', 'preveure', 'prometre', 'proposar', 'protestar', 'puntualitzar', 'quequejar',
    'ratificar', 'reafirmar', 'rebutjar', 'recalcar', 'recitar', 'reclamar', 'recomanar', 'reconèixer', 'referir',
    'refermar', 'reflexionar', 'refusar', 'refutar', 'relatar', 'remarcar', 'rematar', 'remugar', 'renegar',
    'renyar', 'repetir', 'replicar', 'reprendre', 'resar', 'respondre', 'retreure', 'revelar', 'sol·licitar',
    'somicar', 'sospirar', 'sospitar', 'sostenir', 'subratllar', 'suggerir', 'suposar', 'xisclar', 'xiuxiuejar',
    'trobar',
))
_KEEP_LOOKING = jregex.compile('V.*|RG.*|LOC_ADV')


def is_verb_dicendi_before(tokens, i):
    """VerbsHelper.isVerbDicendiBefore"""
    while 0 < i < len(tokens):
        reading = tokens[i].reading_with_tag_regex(_KEEP_LOOKING)
        if reading is None:
            break
        if reading.lemma.lower() in _VERBS_DICENDI:
            return True
        i -= 1
    return False


# --- NounToVerbHelper ------------------------------------------------------

_NOUN_TO_VERB = {
    'acceptació': 'acceptar',
    'acumulació': 'acumular',
    'adaptació': 'adaptar',
    'adhesió': 'adherir',
    'admiració': 'admirar',
    'adopció': 'adoptar',
    'afectació': 'afectar',
    'agregació': 'agregar',
    'agressió': 'agredir',
    'ajuda': 'ajudar',
    'ampliació': 'ampliar',
    'anàlisi': 'analitzar',
    'aplicació': 'aplicar',
    'aprovació': 'aprovar',
    'arribada': 'arribar',
    'ascensió': 'ascendir',
    'assignació': 'assignar',
    'associació': 'associar',
    'atracció': 'atreure',
    'augment': 'augmentar',
    'avaluació': 'avaluar',
    'cessió': 'cedir',
    'circulació': 'circular',
    'citació': 'citar',
    'col·laboració': 'col·laborar',
    'col·locació': 'col·locar',
    'comparació': 'comparar',
    'compensació': 'compensar',
    'competició': 'competir',
    'composició': 'compondre',
    'compra': 'comprar',
    'comprensió': 'comprendre',
    'comunicació': 'comunicar',
    'concreció': 'concretar',
    'conducció': 'conduir',
    'confecció': 'confeccionar',
    'confirmació': 'confirmar',
    'connexió': 'connectar',
    'consideració': 'considerar',
    'construcció': 'construir',
    'consulta': 'consultar',
    'contaminació': 'contaminar',
    'contractació': 'contractar',
    'contribució': 'contribuir',
    'conversió': 'convertir',
    'convocatòria': 'convocar',
    'creació': 'crear',
    'càlcul': 'calcular',
    'declaració': 'declarar',
    'dedicació': 'dedicar',
    'definició': 'definir',
    'demostració': 'demostrar',
    'dependència': 'dependre',
    'deposició': 'depondre',
    'descripció': 'descriure',
    'designació': 'designar',
    'desocupació': 'desocupar',
    'detecció': 'detectar',
    'determinació': 'determinar',
    'devolució': 'tornar',
    'difusió': 'difondre',
    'direcció': 'dirigir',
    'distribució': 'distribuir',
    'documentació': 'documentar',
    'donació': 'donar',
    'dubte': 'dubtar',
    'educació': 'educar',
    'elaboració': 'elaborar',
    'elecció': 'elegir',
    'eliminació': 'eliminar',
    'emissió': 'emetre',
    'ensenyament': 'ensenyar',
    'entrada': 'entrar',
    'enumeració': 'enumerar',
    'enviament': 'enviar',
    'evacuació': 'evacuar',
    'exploració': 'explorar',
    'exposició': 'exposar',
    'extinció': 'extingir',
    'fabricació': 'fabricar',
    'formulació': 'formular',
    'gestió': 'gestionar',
    'identificació': 'identificar',
    'il·lustració': 'il·lustrar',
    'implantació': 'implantar',
    'implementació': 'implementar',
    'importació': 'importar',
    'impressió': 'imprimir',
    'inauguració': 'inaugurar',
    'indicació': 'indicar',
    'informació': 'informar',
    'inspecció': 'inspeccionar',
    'instal·lació': 'instal·lar',
    'instrucció': 'instruir',
    'integració': 'integrar',
    'interpretació': 'interpretar',
    'interrupció': 'interrompre',
    'intervenció': 'intervenir',
    'introducció': 'introduir',
    'investigació': 'investigar',
    'invitació': 'invitar',
    'justificació': 'justificar',
    'limitació': 'limitar',
    'liquidació': 'liquidar',
    'llista': 'llistar',
    'localització': 'localitzar',
    'manifestació': 'manifestar',
    'manipulació': 'manipular',
    'modificació': 'modificar',
    'motivació': 'motivar',
    'neteja': 'netejar',
    'notificació': 'notificar',
    'observació': 'observar',
    'ocupació': 'ocupar',
    'organització': 'organitzar',
    'participació': 'participar',
    'percepció': 'percebre',
    'perdó': 'perdonar',
    'pertorbació': 'pertorbar',
    'planificació': 'planificar',
    'preparació': 'preparar',
    'prevenció': 'prevenir',
    'producció': 'produir',
    'programació': 'programar',
    'prohibició': 'prohibir',
    'protecció': 'protegir',
    'publicació': 'publicar',
    'qualificació': 'qualificar',
    'quantificació': 'quantificar',
    'recaptació': 'recaptar',
    'recepció': 'rebre',
    'reclamació': 'reclamar',
    'recomanació': 'recomanar',
    'reconstrucció': 'reconstruir',
    'recuperació': 'recuperar',
    'redacció': 'redactar',
    'reducció': 'reduir',
    'reflexió': 'reflexionar',
    'reforma': 'reformar',
    'regulació': 'regular',
    'relació': 'relacionar',
    'reparació': 'reparar',
    'representació': 'representar',
    'reproducció': 'reproduir',
    'resolució': 'resoldre',
    'resposta': 'respondre',
    'restricció': 'restringir',
    'revisió': 'revisar',
    'salutació': 'saludar',
    'selecció': 'seleccionar',
    'separació': 'separar',
    'significació': 'significar',
    'sol·licitud': 'sol·licitar',
    'substitució': 'substituir',
    'suspensió': 'suspendre',
    'temptació': 'temptar',
    'traducció': 'traduir',
    'tramitació': 'tramitar',
    'transformació': 'transformar',
    'transmissió': 'transmetre',
    'transport': 'transportar',
    'utilització': 'usar',
    'valoració': 'valorar',
    'venda': 'vendre',
    'verificació': 'verificar',
    'visita': 'visitar',
    'votació': 'votar',
}


def get_verb_from_noun(noun):
    """NounToVerbHelper.getVerbFromNoun"""
    return _NOUN_TO_VERB.get(noun.lower())
