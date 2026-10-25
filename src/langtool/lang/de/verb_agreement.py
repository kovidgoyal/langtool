"""Port of org.languagetool.rules.de.VerbAgreementRule: simple agreement
checker for German verbs and subject (DE_VERBAGREEMENT)."""

import threading

from ...analysis import SENTENCE_START_TAGNAME, AnalyzedSentence, AnalyzedToken
from ...patterns.pattern_token import PatternTokenBuilder, cs_token, pos, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.base import RuleMatch
from ...rules.core import CoreTextLevelRule
from ...rules.multitoken import levenshtein_distance
from ...tools import is_lower_case, is_upper_case, java_hash_set_copy_order, uppercase_first_char

regex = token_regex  # PatternRuleBuilderHelper.regex()


def _anti_patterns():
    return [
        [  # "Ken dachte, du wärst ich."
            token("du"),
            token("wärst"),
            token("ich")
        ],
        [  # "*runterguck* das ist aber tief" (Inflektiv)
            token("*"),
            pos_regex("VER:1:SIN:PRÄ:.*"),
            token("*")
        ],
        [  # "Weder Peter noch ich wollen das."
            PatternTokenBuilder().token("weder").set_skip(8).build(),
            token("noch"),
            token("ich")
        ],
        [  # "Kümmerst dich ja gar nicht um sie." (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:PRÄ:.*"),
            pos_regex("PRO:.*")
        ],
        [  # "Stehst einfach nicht zu mir." (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:PRÄ:.*"),
            token_regex("einfach|denn|schon")
        ],
        [  # "Stellst für deinen Dad etwas zu Essen bereit." (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:PRÄ:.*"),
            pos_regex("PRP:.*")
        ],
        [  # "Springst weit, oder?" (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:PRÄ:.*"),
            pos_regex("ADJ:PRD:.*")
        ],
        [  # "Siehst aus wie ein Wachhund." (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:PRÄ:.*"),
            pos("ZUS")
        ],
        [  # "Könntest was erfinden, wie dein Papa." (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos("VER:MOD:2:SIN:KJ2"),
            pos_regex("PRO:.*")
        ],
        [  # "Darfst nicht so reden, Franz!" (okay for colloquial language)
            pos(SENTENCE_START_TAGNAME),
            pos("VER:MOD:2:SIN:PRÄ"),
            PatternTokenBuilder().token("ich|er|sie|es|wir|ihr|sie").negate().build()
        ],
        [  # "sobald wir frische und neue Akkus haben."
            token("wir"),
            token("frische")
        ],
        [  # "wo der Stadtrat gleich mal zum Du übergeht."
            token("zum"),
            cs_token("Du"),
            PatternTokenBuilder().token_regex("wechseln|übergehen|schwenken").match_inflected_forms().build()
        ],
        [
            token("ich"),
            token("schlafen"),
            token("gehe")
        ],
        [
            # Ich bin du
            token("ich"),
            token_regex("bin|war"),
            token("du")
        ],
        [
            # Dann beende du den Auftrag und bring sie ihrem Vater.
            token_regex("darum|deswegen|dann|bitte|so|,|-"),
            pos_regex("VER:IMP:SIN.*"),
            token("du")
        ],
        [
            # - Wirst du ausflippen?
            token_regex("[-–]"),
            pos_regex("VER:.*(AUX|MOD).*"),
            token("du"),
            pos_regex("VER:INF.*")
        ],
        [
            token_regex("-(du|ich|er|sie|wir|ihr)"),
            pos_regex("VER.*")
        ],
        [
            token_regex("bin|war|wär"),
            token_regex("i|icke?")
        ],
        [
            token_regex("i|icke?"),
            token_regex("bin|war|wär")
        ],
        [
            token("du"),
            token("schlafen"),
            token("gehst")
        ],
        [
            token("per"),
            token("du"),
            token_regex("sind|waren|sein|wären|war|ist|gewesen")
        ],
        [
            token("schnellst"),
            token("möglich")
        ],
        [
            # "Da freut er sich, wenn er schlafen geht und was findet."
            token("er"),
            token("schlafen"),
            token("geht")
        ],
        [
            token("vermittelst")  # "Sie befestigen die Regalbretter vermittelst dreier Schrauben."
        ],
        [
            token("du"),
            token("denkst"),
            token("ich")
        ],
        [
            token("na"),
            token("komm")
        ],
        [
            token_regex("muß|mußten?|müßt?en?"),  # alte rechtschreibung (andere fehler)
            token_regex("ich|wir|sie|er|es")
        ],
        [
            token_regex("ich|wir|sie|er|es"),
            pos_regex("VER.*INF.*"),
            token_regex("muß|mußten?|müßt?en?")  # alte rechtschreibung (andere fehler)
        ],
        [
            token_regex("mußt|müßtest|mußtest"),  # alte rechtschreibung (andere fehler)
            token("du")
        ],
        [
            token("du"),
            pos_regex("VER.*INF.*"),
            token_regex("mußt|müßtest|mußtest")  # alte rechtschreibung (andere fehler)
        ],
        [
            token("ich"),
            token_regex("würd|könnt|werd|wollt|sollt|müsst|fürcht"),
            token_regex("['’`´‘]")
        ],
        [
            token_regex("wir|sie|zu"),
            token_regex("seh|steh|geh"),
            token_regex("['’`´‘]"),
            token("n")
        ],
        [
            token("ick"),  # different error (berlinerisch)
            token_regex("bin|war|wär|hab|hatte")
        ],
        [
            # hash tag
            token("#"),
            pos_regex("VER.*")
        ],
        [
            # wie du war ich auch
            token("wie"),
            token_regex("du|ihr|er|es|sie"),
            pos_regex("VER.*")
        ],
        [
            token_regex("[-:]"),
            pos_regex("VER.*(MOD|AUX).*")
        ],
        [
            # Arabic names: Aryat Abraha bin Sabah Kaaba
            pos_regex("UNKNOWN|EIG.*"),
            token("bin"),
            pos_regex("UNKNOWN|EIG.*")
        ],
        [
            # Du scheiß Idiot
            token_regex("du|sie"),
            token_regex("schei(ß|ss)"),
            pos_regex("SUB.*|UNKNOWN")
        ],
        [
            token("Du"),
            token_regex("bist|warst|wärst")
        ],
        [
            token("als"),
            token("auch"),
            token_regex("er|sie|wir|du|ich|ihr")
        ],
        [
            token_regex("so|wie|zu"),
            token("lange"),
            token_regex("er|sie|wir|du|ich|ihr")
        ],
        [
            # Ich will nicht so wie er enden.
            PatternTokenBuilder().token_regex("so|genauso|ähnlich").match_inflected_forms().set_skip(2).build(),
            token("wie"),
            token_regex("er|sie|du|ihr|ich"),
            pos_regex("VER.*")
        ],
        [
            # Ich will wie er aussehen
            pos_regex("VER.*(MOD|AUX).*"),
            token("wie"),
            token_regex("er|sie|du|ihr|ich"),
            pos_regex("VER.*INF.*")
        ],
        [
            # Ich will wie er aussehen
            token("wie"),
            pos_regex("ADJ:PRD:GRU.*"),
            token_regex("er|sie|du|ihr|ich"),
            pos_regex("VER.*")
        ],
        [
            # "Bekommst sogar eine Sicherheitszulage"
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:.*"),
            pos_regex("ART.*|ADV.*|PRO:POS.*")
        ],
        [
            # "A, B und auch ich"
            token(","),
            pos_regex("EIG:.*|UNKNOWN"),
            regex("und|oder"),
            token("auch"),
            token("ich")
        ],
        [
            # "Dallun sagte nur, dass er gleich kommen wird und legte wieder auf."
            # "Sie fragte, ob er bereit für die zweite Runde ist."
            pos_regex("VER.*"),  # z.B. "Bist"
            token_regex("er|sie|ich|wir|du|es|ihr"),
            token_regex("gleich|bereit|lange|schnelle?|halt|bitte|dank")  # ist hier kein Verb
        ],
        [
            # "Dallun sagte nur, dass er gleich kommen wird und legte wieder auf."
            pos_regex("ADV.*|KON.*"),
            token_regex("er|sie|ich|wir|du|es|ihr"),
            token_regex("gleich|bereit|lange|schnelle?|halt|bitte|dank")  # ist hier kein Verb
        ],
        [
            # "Woraufhin ich verlegen lächelte"
            pos_regex("ADV.*|KON.*"),
            token_regex("er|sie|ich|wir|du|es|ihr"),
            token_regex("verlegen"),
            pos_regex("VER.*")
        ],
        [
            # "Bringst nicht einmal so etwas Einfaches zustande!"
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:2:SIN:.*"),
            token("nicht")
        ],
        [
            # "Da machte er auch vor dem eigenen Volk nicht halt."
            PatternTokenBuilder().token("machen").match_inflected_forms().set_skip(-1).build(),
            token("halt")
        ],
        [  # "Ich hoffe du auch."
            pos_regex("VER:.*"),
            token_regex("du|ihr"),
            token("auch")
        ],
        [
            # "Für Sie mache ich eine Ausnahme."
            token("für"),
            token("Sie"),
            pos("VER:3:SIN:KJ1:SFT"),
            token("ich")
        ],
        [
            # "Einer wie du kennt ...", "Aber wenn jemand wie Du daherkommt"
            token_regex("(irgend)?einer?|(irgend)?jemand"),
            token("wie"),
            token("du"),
            pos_regex("VER:3:.*")
        ],
        [
            # "Kannst mich gerne anrufen" (ugs.)
            pos("VER:MOD:2:SIN:PRÄ"),
            pos_regex("PRO:PER:.*")
        ],
        [
            token_regex("die|welche"),
            token_regex(".*"),
            token_regex("mehr|weniger"),
            token("als"),
            token_regex("ich|du|e[rs]|sie")
        ],
        [
            token("wenn"),
            token("du"),
            token("anstelle")
        ],
        [  # "Ok bin ab morgen bei euch." (umgangssprachlich, benötigt eigene Regel)
            token_regex("ok(ay)?|ja|nein|vielleicht|oh"),
            token_regex("bin|sind")
        ],
        [
            token("das"),
            cs_token("Du"),
            PatternTokenBuilder().token("anbieten").match_inflected_forms().build()
        ],
        [
            cs_token("Du"),  # "jemanden mit Du anreden"
            PatternTokenBuilder().token_regex("anreden|ansprechen").match_inflected_forms().build()
        ],
        [
            pos_regex("SUB:.*PLU.*"),
            token("wie"),  # "Schreibtischtäter wie Du sind doch eher selten."
            token("Du"),
            pos_regex("VER:3:PLU.*")
        ],
        [
            token("würd"),
            token_regex("[nm]ich|man|ichs|'")
        ],
        [
            token(","),
            pos_regex("VER:MOD:2:.*")
        ],
        [
            cs_token("Soll"),
            token("ich")
        ],
        [
            cs_token("Solltest"),
            token("du")
        ],
        [
            cs_token("Müsstest"),  # Müsstest dir das mal genauer anschauen.
            token("dir")
        ],
        [
            cs_token("Könntest"),  # Könntest dir mal eine Scheibe davon abschneiden!
            token("dir")
        ],
        [
            cs_token("Sollte"),
            token_regex("er|sie")
        ],
        [
            pos(SENTENCE_START_TAGNAME),  # "Bin gleich wieder da"
            token_regex("Bin|Kannst|Musst")
        ],
        [
            token(","),  # "..., hast aber keine Ahnung!"
            token_regex("bin|hast|kannst|musst")
        ],
        [
            token("er"),  # "egal, was er sagen wird, ..."
            pos_regex("VER:.*"),
            token("wird")
        ],
        [
            token_regex("wie|als"),  # "Ein Mann wie ich braucht einen Hut"
            token("ich"),
            pos_regex("VER:.*")
        ],
        [
            # "Wir haben da ein monatliches Limit, in das wir glaube ich schon für September reingelaufen sind."
            token_regex("glaube?|denke?|hoffe?|vermute?|behaupte?|wette?"),
            token("ich"),
            pos_regex("ADV.*|SUB.*|UNKNOWN|ADJ.*|PA[12].*|ART.*|PRP.*|PRO.*")
        ],
        [
            token_regex("ich"),  # "Ich weiß, was ich tun werde, falls etwas geschehen sollte."
            pos("VER:INF:NON"),
            token("werde")
        ],
        [
            pos_regex("VER:IMP:SIN:.*"),  # "Kümmere du dich mal nicht darum!"
            token("du"),
            token_regex("dich|dein|deine[srnm]?|mal")
        ],
        [
            pos_regex("VER:IMP:SIN:.*"),  # "Nee, geh du!"
            token("du"),
            token("!")
        ],
        [
            token("sei"),
            token("du"),
            token("selbst")
        ],
        [
            token("bin"),
            token_regex("dran|dabei")
        ],
        [
            token("als"),  # "Du bist in dem Moment angekommen, als ich gegangen bin."
            token("ich"),
            pos_regex("PA2:.*"),
            token("bin")
        ],
        [
            token("als"),
            token_regex("du|e[rs]|sie|ich"),
            PatternTokenBuilder().token("sein").match_inflected_forms().build(),
            token_regex("[\\.,]")
        ],
        [  # Musst du gehen?
            token_regex("D[au]rf.*|Muss.*"),
            pos_regex("PRO:PER:NOM:.+"),
            pos_regex("VER:INF:.+"),
            pos("PKT"),
            token_regex("(?!die).+")
        ],
        [
            cs_token("("),
            pos_regex("VER:2:SIN:.+"),
            cs_token(")")
        ],
        [
            pos_regex("VER:MOD:1:PLU:.+"),
            cs_token("wir"),
            cs_token("bitte")
        ],
        [  # Ohne sie hätte ich das nie geschafft.
            token("ohne"),
            token("sie"),
            token("hätte"),
            token("ich")
        ],
        [  # Geh du mal!
            pos(SENTENCE_START_TAGNAME),
            pos_regex("VER:IMP:SIN.+"),
            token("du"),
            PatternTokenBuilder().cs_token("?").negate().build()
        ],
        [  # -Du fühlst dich unsicher?
            token_regex("[^a-zäöüß]+du"),
            pos("VER:2:SIN:PRÄ:SFT")
        ],
        [  # Mir ist bewusst, dass viele Menschen wie du empfinden.
            pos_regex("PRO:IND.*"),
            pos_regex("SUB:.+:PLU.*"),
            token_regex("wie|als"),
            pos_regex("PRO:PER.+"),
            pos_regex("VER:[1-3]:PLU.*")
        ],
        [  # Weniger als du arbeitet keiner.
            pos("ADV:MOD"),
            token_regex("als"),
            pos_regex("PRO:PER.+"),
            pos_regex("VER:3:SIN.*"),
            pos_regex("PRO:IND:NOM:SIN.*")
        ],
        [  # So was wie er könnte ich nicht machen, dich einfach dann zu verlassen
            pos_regex("PRO:IND.*"),
            token_regex("wie"),
            pos_regex("PRO:PER.+"),
            pos_regex("VER:.*:SIN.*"),
            pos_regex("PRO:PER:NOM:SIN.*")
        ],
        [  # Kein anderer als du kann mich glücklich machen
            token_regex("kein|keine"),
            token_regex("anderer|andere"),
            token("als"),
            token_regex("ich|du|er|sie|es"),
            pos_regex("VER:MOD.*:PRÄ")
        ],
        [  # Ich will nicht die gleiche Luft wie er einatmen
            pos_regex("ART:DEF.*"),
            token_regex("gleich(e|en)|selb(e|en)"),
            pos_regex("SUB:.+"),
            token("wie"),
            pos_regex("PRO:PER:NOM:SIN.*"),
            pos_regex("VER:INF.*")
        ],
        [  # Was würdest du sagen, wenn du ich wärst?
            token("wenn"),
            pos_regex("PRO:PER:NOM:SIN.+"),
            pos_regex("PRO:PER:NOM.+"),
            pos_regex("VER:AUX:[1-3]:SIN:KJ2")
        ],
        [  # Was würdet ihr sagen, wenn ihr ich wärt?
            token("wenn"),
            pos_regex("PRO:PER:NOM:PLU.+"),
            pos_regex("PRO:PER:NOM.+"),
            pos_regex("VER:AUX:[1-3]:PLU:KJ2")
        ],
        [  # Wenn du gehen willst, dann geh!
            token("wenn"),
            token("du"),
            token("gehen"),
            token("willst"),
            token(","),
            token("dann"),
            token("geh")
        ],
        [  # Ich habe mich noch nicht entschieden, ob ich studieren oder arbeiten gehen soll.
            token("ob"),
            token("ich"),
            pos_regex("VER:1.+"),
            token("oder"),
            pos_regex("VER:1.+"),
            PatternTokenBuilder().token("gehen").match_inflected_forms().build(),
            pos_regex("VER:MOD:1.*")
        ],
        [  # Mal seh’n, wie’s Wetter wird.
            token("mal"),
            token("seh"),
            token_regex("’|'"),
            token("n")
        ],
    ]


_ANTI_PATTERNS = _anti_patterns()

# Words that prevent a rule match when they occur directly before "bin":
_BIN_IGNORE = frozenset((
    "Suleiman", "Mohamed", "Muhammad", "Muhammed", "Mohammed", "Mohammad", "Mansour", "Qaboos", "Qabus", "Tamim",
    "Majid", "Salman", "Ghazi", "Mahathir", "Madschid", "Maktum", "al-Aziz", "Asis", "Numan", "Hussein", "Abdul",
    "Abdulla", "Abdullah", "Isa", "Osama", "Said", "Zayid", "Zayed", "Hamad", "Chalifa", "Raschid", "Turki", "/",
))

_CONJUNCTIONS = frozenset((
    "weil",
    "obwohl",
    "dass",
    "indem",
    "sodass",  # , "damit", "wenn"
))

_QUOTATION_MARKS = frozenset(('"', '„'))

_anti_pattern_cache = {}
_anti_pattern_lock = threading.Lock()


def _cached_anti_patterns(language, pattern_list, cache):
    """Rule.cacheAntiPatterns: the anti-patterns are built once per
    language"""
    key = language.code
    aps = cache.get(key)
    if aps is None:
        with _anti_pattern_lock:
            aps = cache.get(key)
            if aps is None:
                aps = cache[key] = make_anti_patterns(pattern_list, language)
    return aps


def _is_near(a, b):
    """true if |a - b| < 5, and a != -1"""
    return a != -1 and abs(a - b) < 5


def _is_quotation_mark(token):
    return token.token in _QUOTATION_MARKS


def _next_but_one_is_modal(tokens, pos):
    # avoid false alarm on 'wenn ich sterben sollte ...':
    return pos < len(tokens) - 2 and tokens[pos + 2].has_partial_pos_tag(":MOD:")


def _has_unambiguously_person_and_number(token_readings, person, number):
    """true if the verb token_readings (if it is a verb) matches person and
    number, and matches no other person/number"""
    t = token_readings.token
    if len(t) == 0 or (is_upper_case(t[0]) and token_readings.start_pos != 0) \
            or not token_readings.has_pos_tag_starting_with("VER"):
        return False
    pn = ":" + person + ":" + number
    for analyzed_token in token_readings:
        postag = analyzed_token.pos_tag
        if postag is None or postag.endswith("_END"):  # ignore SENT_END and PARA_END
            continue
        if pn not in postag:
            return False
    return True


def _is_finite_verb(token):
    """true if token is a finite verb, and it is no participle, pronoun or
    number"""
    t = token.token
    if len(t) == 0 or (is_upper_case(t[0]) and token.start_pos != 0) \
            or not token.has_pos_tag_starting_with("VER") \
            or token.has_any_partial_pos_tag("PA2", "PRO:", "ZAL") \
            or t == "einst":
        return False
    return token.has_any_partial_pos_tag(":1:", ":2:", ":3:")


def _verb_does_match_person_and_number(token1, token2, person, number, finite_verb):
    """(False, verb) if neither the verb token1 (if any) nor token2 match
    person and number, and none of them is "und" or ","; the finite verb
    found (if any) is returned as second value (BooleanAndFiniteVerb)"""
    if token1.token in (",", "und", "sowie", "&") or token2.token in (",", "und", "sowie", "&"):
        return True, finite_verb
    found_finite_verb = False
    pn = ":" + person + ":" + number
    if _is_finite_verb(token1):
        found_finite_verb = True
        finite_verb = token1
        if token1.has_partial_pos_tag(pn):
            return True, finite_verb
    if _is_finite_verb(token2):
        found_finite_verb = True
        finite_verb = token2
        if token2.has_partial_pos_tag(pn):
            return True, finite_verb
    return not found_finite_verb, finite_verb


def _get_pronoun_suggestions(verb, to_uppercase):
    """pronouns which match the person and number of verb"""
    result = []
    if verb.has_partial_pos_tag(":1:SIN"):
        result.append("ich")
    if verb.has_partial_pos_tag(":2:SIN"):
        result.append("du")
    if verb.has_partial_pos_tag(":3:SIN"):
        result.append("er")
        result.append("sie")
        result.append("es")
    if verb.has_partial_pos_tag(":1:PLU"):
        result.append("wir")
    if verb.has_partial_pos_tag(":2:PLU"):
        result.append("ihr")
    if verb.has_partial_pos_tag(":3:PLU") and "sie" not in result:  # do not add "sie" twice
        result.append("sie")
    if to_uppercase:
        result = [uppercase_first_char(s) for s in result]
    return result


def _sort_by_similarity(suggestions, marked_text):
    suggestions.sort(key=lambda s: levenshtein_distance(marked_text, s))


class VerbAgreementRule(CoreTextLevelRule):
    """Port of org.languagetool.rules.de.VerbAgreementRule. Checks agreement
    in:

    - VER:1:SIN w/o ich: e.g. "Max bin da." (incorrect) [same for VER:2:SIN
      w/o du, VER:1:PLU w/o wir]
    - ich + VER:[123]:.* (not VER:1:SIN): e.g. "ich bist" (incorrect) [same
      for du, er, wir]
    """

    rule_id = 'DE_VERBAGREEMENT'
    category_id = 'GRAMMAR'

    def __init__(self, messages, language, user_config=None, **kwargs):
        super().__init__(messages, language)
        self.add_example_pair("Ich <marker>bist</marker> über die Entwicklung sehr froh.",
                              "Ich <marker>bin</marker> über die Entwicklung sehr froh.")

    def get_description(self):
        return "Kongruenz von Subjekt und Prädikat (nur 1. u. 2. Person oder m. Personalpronomen), z.B. 'Er bist (ist)'"

    def get_anti_patterns(self):
        return _cached_anti_patterns(self.language, _ANTI_PATTERNS, _anti_pattern_cache)

    def match(self, sentences, annotated_text=None):
        rule_matches = []
        pos = 0
        for sentence in sentences:
            idx = 0
            tokens = sentence.tokens
            for i in range(2, len(tokens)):
                if tokens[i - 2].token == "," and tokens[i].token in _CONJUNCTIONS:
                    partial_sentence = AnalyzedSentence(tokens[idx:i])
                    rule_matches.extend(self._match(partial_sentence, pos, sentence))
                    idx = i
            partial_sentence = AnalyzedSentence(tokens[idx:])
            rule_matches.extend(self._match(partial_sentence, pos, sentence))
            pos += sentence.get_corrected_text_length()
        return rule_matches

    def _match(self, sentence, pos, whole_sentence):
        finite_verb = None
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        n = len(tokens)

        if n < 4:  # ignore one-word sentences (3 tokens: SENT_START, one word, SENT_END)
            return rule_matches

        # position of the pronouns:
        pos_ich = -1
        pos_du = -1
        pos_er = -1
        pos_wir = -1
        # positions of verbs which do match in person and number, and do not match any other person nor number:
        pos_ver1_sin = -1
        pos_ver2_sin = -1
        pos_ver1_plu = -1
        # positions of verbs which do match in person and number:
        pos_possible_ver1_sin = -1
        pos_possible_ver2_sin = -1
        pos_possible_ver3_sin = -1
        pos_possible_ver1_plu = -1

        for i in range(1, n):  # ignore SENT_START
            tok = tokens[i]
            str_token = tok.token.lower().replace('‚', '')

            if str_token == "ich":
                pos_ich = i
            elif str_token == "du":
                pos_du = i
            elif str_token == "er":
                pos_er = i
            elif str_token == "wir":
                pos_wir = i

            if tok.has_partial_pos_tag("VER") \
                    and (is_lower_case(tok.token[0]) or i == 1 or _is_quotation_mark(tokens[i - 1])):
                if _has_unambiguously_person_and_number(tok, "1", "SIN") \
                        and not (str_token == "bin" and (tokens[i - 1].token in _BIN_IGNORE
                                                         or (n != i + 1
                                                             and tokens[i + 1].token.startswith("Laden")))):
                    pos_ver1_sin = i
                elif _has_unambiguously_person_and_number(tok, "2", "SIN") and tok.token != "Probst":
                    pos_ver2_sin = i
                elif _has_unambiguously_person_and_number(tok, "1", "PLU"):
                    pos_ver1_plu = i

                if tok.has_partial_pos_tag(":1:SIN"):
                    pos_possible_ver1_sin = i
                if tok.has_partial_pos_tag(":2:SIN"):
                    pos_possible_ver2_sin = i
                if tok.has_partial_pos_tag(":3:SIN"):
                    pos_possible_ver3_sin = i
                if tok.has_partial_pos_tag(":1:PLU"):
                    pos_possible_ver1_plu = i

        # "ich", "du", and "wir" must be subject (no other interpretation possible)
        # "ich", "du", "er", and "wir" must have a matching verb

        if pos_ver1_sin != -1 and pos_ich == -1 and not _is_quotation_mark(tokens[pos_ver1_sin - 1]):
            # 1st pers sg verb but no "ich"
            if not tokens[pos_ver1_sin].immunized:
                rule_matches.append(self._rule_match_wrong_verb(tokens[pos_ver1_sin], pos, whole_sentence))
        elif pos_ich > 0 and not _is_near(pos_possible_ver1_sin, pos_ich) \
                and (tokens[pos_ich].token == "ich" or tokens[pos_ich].start_pos <= 1
                     or (tokens[pos_ich].token == "Ich" and pos_ich >= 2 and tokens[pos_ich - 2].token == ":")
                     or (tokens[pos_ich].token == "Ich" and pos_ich >= 1 and tokens[pos_ich - 1].token == ":")) \
                and (not _is_quotation_mark(tokens[pos_ich - 1]) or pos_ich < 3
                     or (pos_ich > 1 and tokens[pos_ich - 2].token == ":")):  # ignore "lyrisches Ich" etc.
            plus1 = 0 if (pos_ich + 1) == n else 1  # prevent posIch+1 segfault
            ok, verb = _verb_does_match_person_and_number(tokens[pos_ich - 1], tokens[pos_ich + plus1], "1", "SIN",
                                                          finite_verb)
            if not ok and not _next_but_one_is_modal(tokens, pos_ich) and "äußerst" != verb.token:
                if not tokens[pos_ich].immunized:
                    rule_matches.append(self._rule_match_wrong_verb_subject(tokens[pos_ich], verb, "1:SIN", pos,
                                                                            whole_sentence))

        if pos_ver2_sin != -1 and pos_du == -1 and not _is_quotation_mark(tokens[pos_ver2_sin - 1]):
            if not tokens[pos_ver2_sin].immunized:
                rule_matches.append(self._rule_match_wrong_verb(tokens[pos_ver2_sin], pos, whole_sentence))
        elif pos_du > 0 and not _is_near(pos_possible_ver2_sin, pos_du) \
                and (not _is_quotation_mark(tokens[pos_du - 1]) or pos_du < 3
                     or (pos_du > 1 and tokens[pos_du - 2].token == ":")):
            plus1 = 0 if (pos_du + 1) == n else 1
            ok, verb = _verb_does_match_person_and_number(tokens[pos_du - 1], tokens[pos_du + plus1], "2", "SIN",
                                                          finite_verb)
            nxt = tokens[pos_du + plus1]
            if not ok \
                    and not nxt.has_pos_tag_starting_with("VER:1:SIN:KJ2") \
                    and not (nxt.has_pos_tag_starting_with("ADJ:") and not nxt.has_pos_tag("ADJ:PRD:GRU")) \
                    and not tokens[pos_du - 1].has_pos_tag_starting_with("VER:1:SIN:KJ2") \
                    and not _next_but_one_is_modal(tokens, pos_du) \
                    and not tokens[pos_du].immunized:
                # ("Wenn ich du wäre", "dass du billige Klamotten...")
                rule_matches.append(self._rule_match_wrong_verb_subject(tokens[pos_du], verb, "2:SIN", pos,
                                                                        whole_sentence))

        if pos_er > 0 and not _is_near(pos_possible_ver3_sin, pos_er) \
                and (not _is_quotation_mark(tokens[pos_er - 1]) or pos_er < 3
                     or (pos_er > 1 and tokens[pos_er - 2].token == ":")):
            plus1 = 0 if (pos_er + 1) == n else 1
            ok, verb = _verb_does_match_person_and_number(tokens[pos_er - 1], tokens[pos_er + plus1], "3", "SIN",
                                                          finite_verb)
            if not ok \
                    and not _next_but_one_is_modal(tokens, pos_er) \
                    and "äußerst" != verb.token \
                    and "regen" != verb.token \
                    and not tokens[pos_er].immunized:  # "wo er regen Anteil nahm"
                rule_matches.append(self._rule_match_wrong_verb_subject(tokens[pos_er], verb, "3:SIN", pos,
                                                                        whole_sentence))

        if pos_ver1_plu != -1 and pos_wir == -1 and not _is_quotation_mark(tokens[pos_ver1_plu - 1]):
            if not tokens[pos_ver1_plu].immunized:
                rule_matches.append(self._rule_match_wrong_verb(tokens[pos_ver1_plu], pos, whole_sentence))
        elif pos_wir > 0 and not _is_near(pos_possible_ver1_plu, pos_wir) \
                and not _is_quotation_mark(tokens[pos_wir - 1]):
            plus1 = 0 if (pos_wir + 1) == n else 1
            ok, verb = _verb_does_match_person_and_number(tokens[pos_wir - 1], tokens[pos_wir + plus1], "1", "PLU",
                                                          finite_verb)
            if not ok and not _next_but_one_is_modal(tokens, pos_wir) and not tokens[pos_wir].immunized \
                    and verb.token != "äußerst":
                rule_matches.append(self._rule_match_wrong_verb_subject(tokens[pos_wir], verb, "1:PLU", pos,
                                                                        whole_sentence))

        return rule_matches

    def _get_verb_suggestions(self, verb, expected_verb_pos, to_uppercase):
        """forms of verb which match expected_verb_pos (person:number)"""
        # find the first verb reading
        verb_token = AnalyzedToken("", "", "")
        for t in verb.readings:
            if t.pos_tag is not None and t.pos_tag.startswith("VER:"):
                verb_token = t
                break
        synthesized = self.language.synthesizer.synthesize(verb_token, "VER.*:" + expected_verb_pos + ".*", True)
        suggestions = java_hash_set_copy_order(list(synthesized))  # remove duplicates
        if to_uppercase:
            suggestions = [uppercase_first_char(s) for s in suggestions]
        return suggestions

    def _rule_match_wrong_verb(self, token, pos, sentence):
        msg = ("Möglicherweise fehlende grammatische Übereinstimmung zwischen Subjekt und Prädikat (" +
               token.token + ") bezüglich Person oder Numerus (Einzahl, Mehrzahl - Beispiel: " +
               "'Max bist' statt 'Max ist').")
        return RuleMatch(self, sentence, pos + token.start_pos, pos + token.end_pos, msg)

    def _rule_match_wrong_verb_subject(self, subject, verb, expected_verb_pos, pos, sentence):
        msg = ("Möglicherweise fehlende grammatische Übereinstimmung zwischen Subjekt (" + subject.token +
               ") und Prädikat (" + verb.token + ") bezüglich Person oder Numerus (Einzahl, Mehrzahl - Beispiel: " +
               "'ich sind' statt 'ich bin').")
        suggestions = []
        if subject.start_pos < verb.start_pos:
            rule_match = RuleMatch(self, sentence, pos + subject.start_pos, pos + verb.start_pos + len(verb.token), msg)
            for verb_suggestion in self._get_verb_suggestions(verb, expected_verb_pos, False):
                suggestions.append(subject.token + " " + verb_suggestion)
            for pronoun_suggestion in _get_pronoun_suggestions(verb, is_upper_case(subject.token[0])):
                suggestions.append(pronoun_suggestion + " " + verb.token)
            marked_text = sentence.text[subject.start_pos:verb.start_pos + len(verb.token)]
        else:
            rule_match = RuleMatch(self, sentence, pos + verb.start_pos, pos + subject.start_pos + len(subject.token),
                                   msg)
            for verb_suggestion in self._get_verb_suggestions(verb, expected_verb_pos, is_upper_case(verb.token[0])):
                suggestions.append(verb_suggestion + " " + subject.token)
            for pronoun_suggestion in _get_pronoun_suggestions(verb, False):
                suggestions.append(verb.token + " " + pronoun_suggestion)
            marked_text = sentence.text[verb.start_pos:subject.start_pos + len(subject.token)]
        _sort_by_similarity(suggestions, marked_text)
        rule_match.set_suggested_replacements(suggestions)
        return rule_match

    def min_to_check_paragraph(self):
        return 0
