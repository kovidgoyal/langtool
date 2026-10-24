"""Port of org.languagetool.rules.ca.QueIniciFilter: the filter shared by the
rules about "que/què" at the start of an interrogative sentence.

It decides whether the sentence should start with "que" (yes/no question) or
"què" ("quina cosa": subject or direct object). The model analyses the main
verb (the GV chunk), the weak pronouns, the transitivity of the verb
(VerbClassifier) and whether the role of "què" (direct object or subject) is
empty or already filled by a postponed complement/subject. Rules with
AMBACCENT (que -> què) keep the match only if "què" is predicted, rules with
SENSEACCENT (què -> que) only if "que" is predicted; if nothing can be
decided the match is kept."""

from ... import jregex
from ...chunking import ChunkTag
from ...rules.filters import RuleFilter
from ...tools import java_equals_ignore_case
from .helpers import DAVANT, NORMALIZED, transform
from .synthesis import VerbSynthesizer
from .tagging import VerbClassifier

_PRONOM = jregex.compile('P0.{6}|PP3CN000|PP3NN000|PP3..A00|PP[123]CP000|PP3CSD00')
_FINITE_VERB = jregex.compile('V.[SI].*')
_ANY_VERB = jregex.compile('V.*')
_DET = jregex.compile('D.*')
_ANY = jregex.compile('.*')

_PTIME_CHUNK = ChunkTag('PTime')

_SINO_LAST_WORDS = ('potser', 'oi')
# Verbs copulatius: al classificador surten com a intransitius, però amb ells "què" fa
# d'atribut/subjecte; els traiem del resultat intransitiu i deixem que la lògica general
# de complements decideixi ("Que pot ser més versemblant?" -> "Què...").
_COPULAR_VERBS = frozenset(('ser', 'ésser', 'estar', 'semblar', 'parèixer'))
# Noms comuns animats que poden ser subjecte posposat ("Que vol aquesta gent?" -> "Què...").
_ANIMATE_SUBJECT_NOUNS = frozenset((
    'persona', 'gent', 'home', 'dona', 'noi', 'noia', 'nen', 'nena', 'nan', 'senyor',
    'senyora', 'senyoreta', 'pare', 'mare', 'fill', 'filla', 'germà', 'germana',
    'amic', 'amiga', 'professor', 'professora', 'mestre', 'mestra', 'metge', 'metgessa',
    'doctor', 'doctora', 'alcalde', 'rei', 'reina', 'policia', 'nadó', 'avi', 'àvia',
    'tia', 'tio', 'oncle', 'cosí', 'cosina', 'veí', 'veïna', 'client', 'clienta',
    'jutge', 'gos', 'gossa', 'gat', 'gata', 'nena', 'criatura', 'company', 'companya',
    'merdós', 'cabró', 'imbècil', 'idiota', 'desgraciat', 'malparit', 'beneit', 'tio',
    'individu', 'paio', 'tipus', 'subjecte', 'element', 'marit', 'muller', 'xiquet'))
_NEVER_SUBJECT_NOUNS = frozenset((
    'cop', 'vegada', 'volta', 'mica', 'miqueta', 'moment', 'instant',
    'dilluns', 'dimarts', 'dimecres', 'dijous', 'divendres', 'dissabte', 'diumenge',
    'dia', 'nit', 'matí', 'tarda', 'vespre', 'hora', 'temps', 'setmana', 'mes', 'any'))
_TEMPORAL_ADJUNCT_NOUNS = frozenset((
    'cop', 'vegada', 'volta', 'moment', 'instant',
    'dilluns', 'dimarts', 'dimecres', 'dijous', 'divendres', 'dissabte', 'diumenge',
    'dia', 'nit', 'nit_1', 'matí', 'tarda', 'vespre', 'hora', 'temps', 'setmana', 'mes', 'any'))
_WEEKDAY_NOUNS = frozenset(('dilluns', 'dimarts', 'dimecres', 'dijous', 'divendres', 'dissabte', 'diumenge'))
_ACCUSATIVE_PRONOUNS = frozenset(('em', 'et', 'el', 'la', 'ens', 'us', 'les', 'els'))
_DATIVE_PRONOUNS = frozenset(('em', 'et', 'li', 'ens', 'us', 'els'))
_INTERROGATIVE_WORDS = frozenset((
    'que', 'què', 'quin', 'quina', 'quins', 'quines', 'qui', 'quant', 'quants', 'quanta', 'quantes', 'res'))
# Verbs que introdueixen una completiva "que ..." (see _completive_has_gap)
_COMPLETIVE_GAP_VERBS = frozenset((
    'creure', 'pensar', 'dir', 'opinar', 'afirmar', 'suposar', 'imaginar', 'saber',
    'considerar', 'sospitar', 'témer', 'voler', 'desitjar', 'necessitar', 'esperar', 'preferir'))
# Pronoms/formes que, com a atribut d'un copulatiu, deixen el buit al "què"
_NEUTER_ATTRIBUTE_WORDS = frozenset(('això', 'allò', 'açò', 'ho'))
_CONFIRMATION_TAGS = frozenset(('veritat', 'oi', 'eh', 'no', 'cert', 'potser'))
_EXPLETIVES = frozenset((
    'collons', 'coi', 'cony', 'dimonis', 'dimoni', 'carai', 'diantre', 'caram',
    'carall', 'punyeta', 'punyetes', 'redimonis', 'diables', 'diable', 'hòstia',
    'dimontri', 'dimontris', 'redéu', 'redeu', 'punyetera', 'leche', 'putes',
    'fotons', 'llamps', 'trons'))


class _VerbGroupInfo:
    __slots__ = ('first_verb_index', 'last_verb_index', 'last_index', 'num_pronouns_before')

    def __init__(self, first_verb_index, last_verb_index, last_index, num_pronouns_before):
        self.first_verb_index = first_verb_index
        self.last_verb_index = last_verb_index
        self.last_index = last_index
        self.num_pronouns_before = num_pronouns_before


class QueIniciFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.QueIniciFilter (see the module
    docstring). The argument mode:completive restricts the decision to main
    verbs followed by a completive clause."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule_id = match.rule.get_id()
        is_amb = 'AMBACCENT' in rule_id or 'AMB_ACCENT' in rule_id
        is_sense = 'SENSEACCENT' in rule_id or 'SENSE_ACCENT' in rule_id
        if not is_amb and not is_sense:
            return match
        completive_only = arguments.get('mode') == 'completive'
        predicts_accent = _predicts_accent(match.sentence, self.get_language_from_rule_match(match), completive_only)
        if predicts_accent is None:
            return match
        if is_amb:
            # Text "que", suggerim "què": confirmem només si la predicció és "què".
            return match if predicts_accent else None
        # SENSE: text "què", suggerim "que": confirmem només si la predicció és "que".
        return None if predicts_accent else match


def _predicts_accent(sentence, language, completive_only):
    """Whether the interrogative start must have the accent ("què") or not
    ("que"); None if it cannot be analysed"""
    tokens = sentence.get_tokens_without_whitespace()
    n = len(tokens)
    que_pos = find_que(tokens)
    if que_pos < 0:
        return None
    starts_with_accent = java_equals_ignore_case(tokens[que_pos].token, 'què')
    question_pos = find_question_mark(tokens, que_pos)
    core_end = strip_confirmation_tag(tokens, que_pos, question_pos) if question_pos >= 0 else n
    last_word = tokens[n - 2].token if n > 2 else ''
    is_si_no_question = n > 2 and (last_word.lower() in _SINO_LAST_WORDS
                                   or (last_word == 'què' and tokens[n - 1].token == 'o')
                                   or (last_word == 'no' and tokens[n - 1].token == ','))
    is_another_subject = last_word == 'això'

    # Subjecte dislocat al final (", el professor?"): si el subjecte ja hi és, el SN
    # postverbal és el CD -> no s'ha de comptar com a possible subjecte.
    j = n - 2
    while j > que_pos and tokens[j].matches_pos_tag_regex('D.*|N.*|A.*|PP3.*|PX.*|PD.*'):
        j -= 1
    trailing_dislocation = j < n - 2 and j > que_pos and tokens[j].token == ','

    verb_group = _verb_group_after_que(tokens, que_pos, core_end, language)
    if verb_group is None:
        return None
    first_verb_pos = verb_group.first_verb_index
    main_verb_pos = verb_group.last_verb_index
    verb3s = tokens[first_verb_pos].matches_pos_tag_regex('V.[SI].3S.*')
    verb3p = tokens[first_verb_pos].matches_pos_tag_regex('V.[SI].3P.*')
    verb2p = tokens[first_verb_pos].matches_pos_tag_regex('V.[SI].2P.*')
    main_verb_reading = tokens[main_verb_pos].reading_with_tag_regex(_ANY_VERB)
    main_verb_lemma = main_verb_reading.lemma

    first_token_after_verb_pos = verb_group.last_index + 1
    first_postag_after_verb = ''
    if first_token_after_verb_pos < n:
        at = tokens[first_token_after_verb_pos].reading_with_tag_regex(_ANY)
        first_postag_after_verb = at.pos_tag if at is not None and at.pos_tag is not None else 'UNKNOWN'

    if completive_only and not (main_verb_pos >= 0 and main_verb_pos + 1 < n
                                and tokens[main_verb_pos + 1].token == 'que'
                                and main_verb_lemma in _COMPLETIVE_GAP_VERBS):
        return None

    # "voler dir" ('to mean') is a lexicalized predicate
    voler_dir = _voler_dir_prediction(tokens, verb_group, core_end)
    if voler_dir is not None:
        return voler_dir

    pronoms = []
    for i in range(first_verb_pos - verb_group.num_pronouns_before, first_verb_pos):
        _add_pronoun_token(tokens, i, pronoms)
    for i in range(main_verb_pos + 1, verb_group.last_index + 1):
        _add_pronoun_token(tokens, i, pronoms)
    has_ho = 'ho' in pronoms
    has_accusative_pronoun = False
    has_dative_pronoun = False
    has_accusative_not_dative_pronoun = False
    for p in pronoms:
        accusative = p in _ACCUSATIVE_PRONOUNS
        dative = p in _DATIVE_PRONOUNS
        has_accusative_pronoun |= accusative
        has_dative_pronoun |= dative
        has_accusative_not_dative_pronoun |= accusative and not dative
    pronom_str = ''
    if pronoms:
        pronom_str = transform(' '.join(pronoms), DAVANT)

    # El complement posposat pot ser subjecte?
    complement_can_be_subject = ((verb3s or verb3p or verb2p) and first_token_after_verb_pos > 0
                                 and first_token_after_verb_pos < n
                                 and _postverbal_can_be_subject(tokens, first_token_after_verb_pos, verb3s, verb3p,
                                                                verb2p))

    # El complement posposat pot ser complement directe?
    complement_can_be_object = has_accusative_not_dative_pronoun
    if first_postag_after_verb.startswith('N'):
        complement_can_be_object = True
    elif (first_token_after_verb_pos > 0 and first_token_after_verb_pos + 1 < n
          and (tokens[first_token_after_verb_pos].matches_pos_tag_regex(_DET)
               or tokens[first_token_after_verb_pos].token.lower() in _INTERROGATIVE_WORDS)):
        complement_can_be_object = True

    # veure't (i potser altres verbs)
    if main_verb_lemma == 'veure' and has_accusative_pronoun:
        complement_can_be_object = True

    # Excepcions: complements de temps o oracions de relatiu, "tot"...
    is_exception_object = False
    is_exception_subject = False
    if first_token_after_verb_pos > 0 and first_token_after_verb_pos + 1 < n:
        readings_after_verb = tokens[first_token_after_verb_pos]
        readings_after_verb2 = tokens[first_token_after_verb_pos + 1]
        is_common_exception = (_PTIME_CHUNK in readings_after_verb2.chunk_tags
                               or readings_after_verb2.has_pos_tag('_loc_unavegada')
                               or readings_after_verb2.has_pos_tag('_data_concreta')
                               or readings_after_verb.has_lemma('tot'))
        is_exception_object = not has_accusative_not_dative_pronoun and is_common_exception
        is_exception_subject = is_common_exception
    complement_can_be_object = complement_can_be_object and not is_exception_object
    if (main_verb_lemma == 'fer'
            and _postverbal_starts_temporal_adjunct(tokens, first_token_after_verb_pos, core_end)):
        complement_can_be_object = False
    complement_can_be_subject = (complement_can_be_subject and not is_exception_subject and not is_another_subject
                                 and not trailing_dislocation)

    # Transitivitat i rol de "què"
    is_que_subject = False
    if verb3s and main_verb_pos > 1:
        que_found_pos = _find_first_form(tokens, main_verb_pos + 1, 'que')
        nearby_que = main_verb_pos < que_found_pos < main_verb_pos + 5
        fer_has_subject_que = nearby_que or has_accusative_not_dative_pronoun
        previous_verb = tokens[main_verb_pos - 1].reading_with_tag_regex(_ANY_VERB)
        is_que_subject = fer_has_subject_que and (main_verb_lemma == 'fer'
                                                  or (previous_verb is not None and previous_verb.lemma == 'fer'))
    is_que_object = False
    # Subordinada saturada ("que" de sí/no): força la predicció a no-accent.
    saturated_completive = False
    main_verb_finite = tokens[main_verb_pos].reading_with_tag_regex(_FINITE_VERB)
    if (main_verb_finite is not None and main_verb_pos + 1 < n and tokens[main_verb_pos + 1].token == 'que'
            and main_verb_finite.lemma != 'veure'):
        if main_verb_lemma in _COMPLETIVE_GAP_VERBS:
            # "[verb epistèmic/volitiu] que [subordinada]": decidim segons si hi ha buit.
            gap = _completive_has_gap(tokens, main_verb_pos, core_end, language)
            if gap is False:
                saturated_completive = True
            else:
                # buit detectat o no decidible: "què" lliga un argument de la subordinada.
                is_que_object = True
        else:
            is_que_object = True
    is_fer = main_verb_lemma == 'fer'
    fer_por_mal_polar = not starts_with_accent and _is_fer_por_mal_polar(
        tokens, main_verb_pos, first_token_after_verb_pos, core_end, has_dative_pronoun)
    if fer_por_mal_polar or (is_fer and _is_fer_por_que(tokens, first_token_after_verb_pos)):
        is_que_subject = False
        complement_can_be_object = True
    elif is_fer and _is_fer_mal(tokens, first_token_after_verb_pos):
        is_que_subject = True
        complement_can_be_object = False

    is_intransitive = ((VerbClassifier.is_intransitive(main_verb_lemma) and main_verb_lemma not in _COPULAR_VERBS)
                       or (main_verb_lemma == 'ser' and pronom_str == 'hi'))
    if main_verb_lemma in ('passar', 'agradar'):
        is_intransitive = True
        is_que_subject = not complement_can_be_object
    elif is_intransitive:
        is_que_subject = False
    is_que_subject = is_que_subject and not is_another_subject

    if starts_with_accent and main_verb_lemma == 'fer' and _is_fer_mal(tokens, first_token_after_verb_pos):
        # duplicate code, except for isTransitive
        is_intransitive = False
        is_que_subject = True
        complement_can_be_object = False

    predicts_accent = (is_que_subject or is_que_object
                       or (not is_intransitive and ((not complement_can_be_object and not has_ho)
                                                    or complement_can_be_subject)))
    # Subordinada saturada d'un verb epistèmic/volitiu ("Que creus que té raó?"): sí/no,
    # tret que "què" quedi clarament com a subjecte de l'oració principal.
    if saturated_completive and not is_que_subject:
        predicts_accent = False
    # Una cua "..., potser?"/"..., oi?" indica sí/no, tret que "què" sigui clarament
    # subjecte o CD (interrogativa retòrica: "Què passa, ..., potser?").
    if is_si_no_question and not is_que_subject and not is_que_object:
        predicts_accent = False
    return bool(predicts_accent)


def _voler_dir_prediction(tokens, verb_group, core_end):
    """The lexicalized predicate "voler dir" ('significar'): True if it is
    "voler dir" with the accent, False if it is "voler dir" with an
    indefinite object (yes/no question), None if it is not this
    predicate."""
    if verb_group is None or verb_group.last_verb_index <= verb_group.first_verb_index:
        return None
    last_verb = tokens[verb_group.last_verb_index].reading_with_tag_regex(_ANY_VERB)
    if last_verb is None or last_verb.lemma != 'dir':
        return None
    has_voler = False
    for i in range(verb_group.first_verb_index, verb_group.last_verb_index + 1):
        verb = tokens[i].reading_with_tag_regex(_ANY_VERB)
        if verb is not None and verb.lemma == 'voler':
            has_voler = True
    if not has_voler:
        return None
    # Objecte indefinit immediat ("res", "alguna cosa"...): lectura de sí/no.
    object_pos = verb_group.last_index + 1
    while object_pos < core_end and object_pos < len(tokens) and tokens[object_pos].matches_pos_tag_regex(_DET):
        object_pos += 1
    if object_pos < core_end and object_pos < len(tokens):
        form = tokens[object_pos].token.lower()
        if form in ('res', 'quelcom', 'alguna', 'algun', 'cap'):
            return False
    return True


def _completive_has_gap(tokens, main_verb_pos, core_end, language):
    """Analyses the completive clause "que ..." after the epistemic/volitive
    verb at main_verb_pos: True if "què" binds an argument gap in it
    (accent), False if it is saturated (no accent), None if it cannot be
    decided"""
    que_pos = main_verb_pos + 1
    emb = _verb_group_after_que(tokens, que_pos, core_end, language)
    if emb is None:
        return None
    emb_verb_reading = tokens[emb.last_verb_index].reading_with_tag_regex(_ANY_VERB)
    if emb_verb_reading is None or emb_verb_reading.lemma is None:
        return None
    emb_lemma = emb_verb_reading.lemma
    # Clítics de la subordinada (davant del primer verb i enclítics darrere l'últim).
    emb_pron = []
    for k in range(emb.first_verb_index - emb.num_pronouns_before, emb.first_verb_index):
        _add_pronoun_token(tokens, k, emb_pron)
    for k in range(emb.last_verb_index + 1, emb.last_index + 1):
        _add_pronoun_token(tokens, k, emb_pron)
    for p in emb_pron:
        # Un clític acusatiu o neutre/partitiu ("ho", "en") ja ocupa el CD -> saturada.
        if (p in _ACCUSATIVE_PRONOUNS and p not in _DATIVE_PRONOUNS) or p == 'ho' or p == 'en':
            return False
    # Subjecte overt preverbal (pronom fort o nom propi entre "que" i el verb).
    overt_subject = False
    for k in range(que_pos + 1, min(emb.first_verb_index, len(tokens))):
        if tokens[k].matches_pos_tag_regex('PP[123].*|NP.*'):
            overt_subject = True
    copular = emb_lemma in _COPULAR_VERBS
    intransitive = VerbClassifier.is_intransitive(emb_lemma) and not copular
    content_pos = _first_argument_token_after(tokens, emb.last_index + 1, core_end)
    if copular:
        if content_pos < 0:
            return True  # atribut buit: "que ha estat?", "que és?"
        c_form = tokens[content_pos].token.lower()
        if c_form in _NEUTER_ATTRIBUTE_WORDS or c_form in _INTERROGATIVE_WORDS:
            return True  # "que és això?", "que és qui?"
        # Atribut ple (adjectiu, participi, SN o complement preposicional) -> saturada.
        if tokens[content_pos].matches_pos_tag_regex('A.*|V.P.*|N.*|D.*|PI.*|PX.*|Z.*|SPS.*'):
            return False
        return True
    if content_pos < 0:
        # Res darrere el verb. Amb subjecte overt (i sense CD) la subordinada és completa;
        # si no, el "què" pot ser el subjecte ("que ha passat?") o el CD ("que diria?").
        return not (overt_subject and intransitive)
    c_form = tokens[content_pos].token.lower()
    if tokens[content_pos].matches_pos_tag_regex('D.*|N.*|PI.*|PX.*|PD.*|Z.*') and c_form not in _INTERROGATIVE_WORDS:
        verb3s = tokens[emb.first_verb_index].matches_pos_tag_regex('V.[SI].3S.*')
        verb3p = tokens[emb.first_verb_index].matches_pos_tag_regex('V.[SI].3P.*')
        verb2p = tokens[emb.first_verb_index].matches_pos_tag_regex('V.[SI].2P.*')
        # SN posposat animat/propi -> és el subjecte, el CD queda buit ("que va dir en Joan?").
        # SN inanimat -> és el CD i la subordinada queda saturada ("que té raó?").
        return _postverbal_can_be_subject(tokens, content_pos, verb3s, verb3p, verb2p)
    # Darrere el verb només hi ha un complement no nominal (preposició, adverbi, infinitiu...).
    # Amb verb transitiu el CD continua buit ("que va dir a algú?"); amb intransitiu, no.
    return not intransitive


def _first_argument_token_after(tokens, start, end):
    """The first token after the verb that can be an argument (direct
    object/attribute), skipping adverbs; -1 if only punctuation is left or
    the core of the question ends"""
    for i in range(start, min(end, len(tokens))):
        form = tokens[i].token
        if form == '?' or form == ',':
            return -1
        if tokens[i].matches_pos_tag_regex('R.|RG|RN'):
            continue  # adverbis
        return i
    return -1


def _postverbal_can_be_subject(tokens, start, verb3s, verb3p, verb2p):
    """Can the noun phrase starting at start be the postponed subject? True
    if its head is a proper noun or an animate common noun that agrees in
    number with the verb; an inanimate common noun is a direct object"""
    verb_p = verb3p or verb2p
    for i in range(start, min(len(tokens), start + 5)):
        form = tokens[i].token
        if form == '?' or form == ',':
            break
        if tokens[i].reading_with_tag_regex('NP.*') is not None:
            # nom propi: normalment animat/subjecte (el nombre sovint no hi és marcat)
            return True
        common_noun = tokens[i].reading_with_tag_regex('NC.*')
        if common_noun is not None:
            if common_noun.lemma in _NEVER_SUBJECT_NOUNS:
                return False
            if not (common_noun.lemma in _ANIMATE_SUBJECT_NOUNS or tokens[i].has_pos_tag('NCCN000')):  # numeral
                return False
            noun_singular = tokens[i].matches_pos_tag_regex('NC.S.*')
            noun_plural = tokens[i].matches_pos_tag_regex('NC.P.*|NCCN000')
            return (verb3s and noun_singular) or (verb_p and noun_plural) or (not noun_singular and not noun_plural)
    return False


def _is_fer_mal(tokens, start):
    if start <= 0 or start >= len(tokens):
        return False
    first = tokens[start].token.lower()
    if first in ('cap', 'algun', 'alguna', 'un', 'una'):
        return False
    return tokens[start].has_lemma('mal') or (tokens[start].has_lemma('por') and not _next_token_is(tokens, start,
                                                                                                    'que'))


def _is_fer_por_mal_polar(tokens, main_verb_pos, start, end, has_dative_pronoun):
    if (main_verb_pos <= 0 or start <= 0 or start >= len(tokens) or end <= start
            or not tokens[main_verb_pos].has_lemma('fer')):
        return False
    noun_pos = _first_lexical_token(tokens, start, end)
    if noun_pos < 0 or not (tokens[noun_pos].has_lemma('por') or tokens[noun_pos].has_lemma('mal')):
        return False
    if tokens[noun_pos].has_lemma('por') and _next_token_is(tokens, noun_pos, 'que'):
        return False
    return (has_dative_pronoun or _has_infinitive_after_noun(tokens, noun_pos, end)
            or _has_subject_after_fer_mal(tokens, noun_pos, end) or _has_auxiliary_before_fer(tokens, main_verb_pos))


def _first_lexical_token(tokens, start, end):
    for i in range(start, min(end, len(tokens))):
        token = tokens[i].token
        if token == ',' or token == '?':
            break
        if (java_equals_ignore_case(token, 'pas') or java_equals_ignore_case(token, 'gaire')
                or java_equals_ignore_case(token, 'més')):
            continue
        return i
    return -1


def _has_subject_after_fer_mal(tokens, noun_pos, end):
    for i in range(noun_pos + 1, min(end, len(tokens), noun_pos + 5)):
        if tokens[i].token == ',' or tokens[i].token == '?':
            break
        if tokens[i].matches_pos_tag_regex('D.*|N.*|NP.*|PI.*'):
            return True
    return False


def _has_infinitive_after_noun(tokens, noun_pos, end):
    for i in range(noun_pos + 1, min(end, len(tokens), noun_pos + 4)):
        if tokens[i].token == ',' or tokens[i].token == '?':
            break
        if tokens[i].matches_pos_tag_regex('V.N.*'):
            return True
    return False


def _has_auxiliary_before_fer(tokens, verb_pos):
    i = verb_pos - 1
    while i > 0 and i >= verb_pos - 4:
        if tokens[i].token == ',' or tokens[i].token == '?':
            break
        verb = tokens[i].reading_with_tag_regex(_ANY_VERB)
        if verb is not None and verb.lemma in ('voler', 'poder', 'deure', 'haver'):
            return True
        i -= 1
    return False


def _is_fer_por_que(tokens, start):
    return 0 < start < len(tokens) and tokens[start].has_lemma('por') and _next_token_is(tokens, start, 'que')


def _next_token_is(tokens, start, token):
    return start + 1 < len(tokens) and java_equals_ignore_case(tokens[start + 1].token, token)


def _postverbal_starts_temporal_adjunct(tokens, start, end):
    if start <= 0 or start >= len(tokens) or end <= start:
        return False
    has_determiner = False
    for i in range(start, min(end, start + 4)):
        if tokens[i].matches_pos_tag_regex('D.*'):
            has_determiner = True
            continue
        noun = tokens[i].reading_with_tag_regex('NC.*')
        return (noun is not None and noun.lemma in _TEMPORAL_ADJUNCT_NOUNS
                and (has_determiner or noun.lemma in _WEEKDAY_NOUNS))
    return False


def is_animate_subject_noun(lemma):
    return lemma in _ANIMATE_SUBJECT_NOUNS


def is_never_subject_noun(lemma):
    return lemma in _NEVER_SUBJECT_NOUNS


def _add_pronoun_token(tokens, index, pronoms):
    if index < 0 or index >= len(tokens):
        return
    pronoun = tokens[index].reading_with_tag_regex(_PRONOM)
    if pronoun is not None:
        pronoms.append(transform(pronoun.token, NORMALIZED))


def _find_first_form(tokens, start, form):
    for i in range(start, len(tokens)):
        if java_equals_ignore_case(tokens[i].token, form):
            return i
    return -1


# ----- Helpers auxiliars usats també pel test de corpus -----

def has_verb_structure(sentence):
    """Whether the interrogative sentence starts with the structure
    "que/què (no) (pronoms febles) verb" (the confirmation tag ", veritat?"
    is ignored)"""
    tokens = sentence.get_tokens_without_whitespace()
    que_idx = find_que(tokens)
    if que_idx < 0:
        return False
    question_idx = find_question_mark(tokens, que_idx)
    if question_idx < 0:
        return False
    core_end = strip_confirmation_tag(tokens, que_idx, question_idx)
    return verb_index_after_que(tokens, que_idx, core_end) >= 0


def verb_index_after_que(tokens, que_idx, core_end, language=None):
    if language is None:
        from ...api import get_language
        language = get_language('ca-ES')  # Catalan.getInstance()
    verb_group = _verb_group_after_que(tokens, que_idx, core_end, language)
    return -1 if verb_group is None else verb_group.last_verb_index


def _verb_group_after_que(tokens, que_idx, core_end, language):
    verb_synthesizer = VerbSynthesizer(tokens, que_idx + 1, language)
    if verb_synthesizer.is_undefined() or verb_synthesizer.get_first_verb_index() >= core_end:
        return None
    first_verb = verb_synthesizer.get_first_verb_index()
    next_que = _find_first_form(tokens, que_idx + 1, 'que')
    if que_idx < next_que < first_verb:
        return None
    boundary = next_que if first_verb < next_que < core_end else core_end
    last_index = min(verb_synthesizer.get_last_index(), boundary - 1)
    last_verb = min(verb_synthesizer.get_last_verb_index(), last_index)
    while last_verb >= first_verb and tokens[last_verb].reading_with_tag_regex(_ANY_VERB) is None:
        last_verb -= 1
    if last_verb < first_verb:
        return None
    return _VerbGroupInfo(first_verb, last_verb, last_index, verb_synthesizer.get_num_pronouns_before())


def _is_skippable_before_verb(token):
    form = token.token.lower()
    if form == 'no' or form in _EXPLETIVES:
        return True
    if _is_weak_pronoun(token):
        return True
    return token.matches_pos_tag_regex('R.|I')


def _is_weak_pronoun(token):
    return token.matches_pos_tag_regex(_PRONOM)


def _is_verb(token):
    return token.matches_pos_tag_regex(_ANY_VERB)


def find_que(tokens):
    for i, t in enumerate(tokens):
        if java_equals_ignore_case(t.token, 'que') or java_equals_ignore_case(t.token, 'què'):
            return i
    return -1


def find_question_mark(tokens, from_idx):
    for i in range(from_idx + 1, len(tokens)):
        if tokens[i].token == '?':
            return i
    return -1


def strip_confirmation_tag(tokens, que_idx, question_idx):
    last_core = question_idx - 1
    comma_idx = last_core - 1
    if (comma_idx > que_idx and tokens[comma_idx].token == ','
            and tokens[last_core].token.lower() in _CONFIRMATION_TAGS):
        return comma_idx
    return question_idx


def verb_lemma(token):
    for reading in token.readings:
        pos_tag = reading.pos_tag
        if pos_tag is not None and pos_tag.startswith('V'):
            return reading.lemma
    return None


FILTERS = (QueIniciFilter,)
# rule factories of this module: Java class name -> factory(messages, language, user_config, **kwargs)
RULES = {}
