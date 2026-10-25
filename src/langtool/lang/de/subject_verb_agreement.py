"""Port of org.languagetool.rules.de.SubjectVerbAgreementRule: checks the
subject verb agreement for the verb forms "ist", "sind", "war" and "waren"
(DE_SUBJECT_VERB_AGREEMENT)."""

import threading

from ... import jregex
from ...analysis import SENTENCE_START_TAGNAME
from ...chunking import ChunkTag
from ...patterns.pattern_token import PatternTokenBuilder, cs_regex, cs_token, pos, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.base import RuleMatch
from ...rules.core import CoreRule

regex = token_regex  # PatternRuleBuilderHelper.regex()

_NPS = ChunkTag("NPS")  # noun phrase singular
_NPP = ChunkTag("NPP")  # noun phrase plural
_PP = ChunkTag("PP")  # prepositional phrase etc.
_QUESTION_PRONOUNS = ("wie",)
_CURRENCIES = ("Dollar", "Euro", "Yen")

# SingularPluralPair (singular, plural)
_PAIRS = (
    ("ist", "sind"),
    ("war", "waren"),
    # ("geht", "gehen")  # false alarm: "Wohin möchtest du nächsten Sonntag gehen?"
    # add more pairs here to activate more cases step by step
)

_LEFT_REGEX = jregex.compile("wer|(?i)alle[nr]?|(?i)jede[rs]?|(?i)manche[nrs]?")
_VERB_TO_THE_LEFT = jregex.compile("VER:[1-3]:.+")


def _anti_patterns():
    return [
        [
            # "Zwei Schülern war aufgefallen, dass man im Fernsehen..."
            pos("ZAL"),
            pos_regex("SUB:DAT:PLU:.*"),
            cs_regex("war|ist"),
            PatternTokenBuilder().pos_regex("NEG|PA2:.+").build()
        ],
        [  # "Wie viel Prozent der Menschen sind total bescheuert?"
            token("Prozent"),
            token("der"),
            pos_regex("SUB:.*:PLU:.*"),
            cs_regex("sind|waren")
        ],
        [  # "Die meisten der Spieler sind nicht vermögend"
            token("meisten"),
            token("der"),
            pos_regex("SUB:.*:PLU:.*"),
            cs_regex("sind|waren")
        ],
        [  # "er bemerkte, dass Experimente nicht gerade sein Ding sind"
            pos_regex("SUB:.*:PLU:.*"),
            PatternTokenBuilder().token("nicht").set_skip(1).build(),
            pos_regex("PRO:.*"),
            cs_regex("Ding"),
            cs_regex("sind|waren")
        ],
        [  # "Wenn Sie kein Teil der Lösung sind, ..."
            token("Teil"),
            token("der"),
            token("Lösung"),
            cs_regex("sind|waren")
        ],
        [
            # "Auch Studien zu Zink sind vielversprechend."
            pos_regex("SUB:NOM:PLU:.*"),
            token("zu"),
            pos_regex("SUB:.*"),
            token_regex("sind|waren")
        ],
        [
            # "Glaubt wirklich jemand, dass gute Fotos keine Arbeit sind?"
            pos_regex("SUB:.*:PLU:.*"),
            regex("keine|wenig|kaum|viel"),
            pos_regex("SUB:.*:SIN:.*"),
            token("sind")
        ],
        [
            # "Auch die Zehn Gebote sind Ausdruck davon."
            token("Zehn"),
            token("Gebote"),
            token("sind")
        ],
        [
            # "All diesen Stadtteilen ist die Nähe zum Hamburger Hafen..."
            token("all"),
            token_regex("d(ies)?en"),
            pos_regex("SUB:.*PLU.*"),
            token("ist"),
            pos_regex("ART:.*"),
            pos_regex("SUB:.*SIN.*")
        ],
        [
            # "Personen ist der Zugriff auf diese Daten verboten."
            pos(SENTENCE_START_TAGNAME),
            PatternTokenBuilder().token("Solchen").min(0).build(),
            pos_regex("SUB:.*PLU.*"),
            token("ist"),
            pos_regex("ART:.*"),
            pos_regex("SUB:.*SIN.*")
        ],
        [
            # "Auch die Reste eines sehr großen Insektenfressers sind unter den Fossilien." - Chunker zu fixen wäre
            # die bessere Lösung...
            token_regex("Reste|Überreste"),
            token_regex("eines|des"),
            pos_regex("ADV:.*"),
            pos_regex("ADJ:.*"),
            pos_regex("SUB:.*SIN.*"),
            token_regex("sind")
        ],
        [
            # "Die eiförmigen und oben abgerundeten Blätter sind grün." - Chunker zu fixen wäre die bessere Lösung...
            pos_regex("ADJ:.*"),
            token_regex("und|sowie"),
            pos_regex("ADV:.*"),
            pos_regex("PA2:.*"),
            pos_regex("SUB:.*PLU.*"),
            token_regex("sind")
        ],
        [
            # Gründer und Leiter des Zentrums ist der Rabbiner Marvin Hier, sein Stellvertreter ist Rabbi Abraham
            # Cooper.
            token_regex("Gründer(in)?|Gesellschafter(in)?|Leiter(in)?|Geschäftsführer(in)?|Chef(in)?"),
            token_regex("und|sowie|&"),
            PatternTokenBuilder().token_regex(
                "Gründer(in)?|Gesellschafter(in)?|Leiter(in)?|Geschäftsführer(in)?|Chef(in)?").set_skip(4).build(),
            token_regex("ist")
        ],
        [
            token_regex("ist|war"),
            token("gemeinsam")
        ],
        [
            pos(SENTENCE_START_TAGNAME),
            pos("ZAL"),
            token_regex("Minuten|Stunden|Tage|Monate|Jahre|Jahrzehnte"),
            pos_regex("VER:3:SIN:.*")
        ],
        [
            pos(SENTENCE_START_TAGNAME),
            token_regex("einige|viele|wenige|mehrere"),
            token_regex("Minuten|Stunden|Tage|Monate|Jahre|Jahrzehnte"),
            pos_regex("VER:3:SIN:.*")
        ],
        [
            pos(SENTENCE_START_TAGNAME),
            pos_regex("ADV:MOD|ADJ:PRD:GRU"),
            pos("ZAL"),
            token_regex("Minuten|Stunden|Tage|Monate|Jahre|Jahrzehnte"),
            pos_regex("VER:3:SIN:.*")
        ],
        [
            pos(SENTENCE_START_TAGNAME),
            PatternTokenBuilder().pos("PRP:CAU:GEN").set_skip(4).build(),
            PatternTokenBuilder().cs_token("und").set_skip(4).build(),
            token_regex("ist|war")
        ],
        [
            pos_regex(SENTENCE_START_TAGNAME + "|KON:UNT"),
            pos_regex("(EIG|SUB):.*"),
            PatternTokenBuilder().cs_token("und").set_skip(3).build(),
            token_regex("sind|waren")
        ],
        [
            pos("KON:UNT"),
            PatternTokenBuilder().token("sie").set_skip(3).build(),
            token_regex("sind|waren")
        ],
        [  # Bei komplexen und andauernden Störungen ist der Stress-Stoffwechsel des Hundes entgleist.
            pos(SENTENCE_START_TAGNAME),
            PatternTokenBuilder().pos_regex("PRP:.+").set_skip(4).build(),
            token_regex("ist|war"),
            token_regex("d(as|er)|eine?")
        ],
        [
            pos_regex("SUB:NOM:PLU:.+"),
            cs_token("vor"),
            cs_token("Ort"),
            token_regex("sind|waren")
        ],
        [
            token("zu"),
            cs_regex("Fuß|Hause|Bein|Besuch"),
            token_regex("sind|waren")
        ],
        [  # Eltern ist der bisherige Kita-Öffnungsplan zu unkonkret
            pos(SENTENCE_START_TAGNAME),
            pos("SUB:DAT:PLU:NOG"),
            token_regex("ist|war"),
            pos_regex(".+:NOM:.+")
        ],
        [  # Das Gestell, sowie der komplette Tisch sind leicht zu montieren.
            pos_regex("SUB:.+"),
            PatternTokenBuilder().pos("PKT").min(0).build(),
            token("sowie"),
            pos_regex("ART.*"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB:.+"),
            token_regex("sind|waren")
        ],
        [  # Das saisonale Obst und Gemüse ist köstlich und oft deutlich günstiger als in der Stadt.
            token_regex("das"),
            pos_regex("(ADJ|PA[12]).*NEU.*"),
            pos_regex("SUB:.*NEU.*"),
            token_regex("und"),
            pos_regex("SUB:.*NEU.*"),
            token_regex("ist|war")
        ],
        [  # Das saisonale Obst und Gemüse ist köstlich und oft deutlich günstiger als in der Stadt.
            token_regex("der"),
            pos_regex("(ADJ|PA[12]).*MAS.*"),
            pos_regex("SUB:.*MAS.*"),
            token_regex("und"),
            pos_regex("SUB:.*MAS.*"),
            token_regex("ist|war")
        ],
        [  # Das saisonale Obst und Gemüse ist köstlich und oft deutlich günstiger als in der Stadt.
            token_regex("die"),
            pos_regex("(ADJ|PA[12]).*FEM.*"),
            pos_regex("SUB:.*FEM.*"),
            token_regex("und"),
            pos_regex("SUB:.*FEM.*"),
            token_regex("ist|war")
        ],
        [  # Einer der bedeutendsten Māori-Autoren der Gegenwart ist Witi Ihimaera.
            token_regex("(irgend)?einer?|meisten|viele|einige|Betreiber|(Mit)?Gründer|Inhaber"),
            PatternTokenBuilder().token_regex("der|dieser").set_skip(4).build(),
            token_regex("ist|war")
        ],
        [  # Dank unserer Kunden, Freunde, Partner und unserer Mitarbeiter ist Alpenwahnsinn zur Heimatadresse für
            # schöne Trachtenmode geworden.
            PatternTokenBuilder().token("dank").set_skip(-1).build(),
            token_regex("ist|war"),
            pos_regex("EIG.*|SUB.*SIN.*")
        ],
        [  # Start und Ziel ist Innsbruck
            token("Start"),
            token("und"),
            token("Ziel"),
            token_regex("ist|war")
        ],
        [  # Abschluss und Höhepunkt ist der Festumzug
            pos_regex("SUB.*SIN.*"),
            token("und"),
            pos_regex("SUB.*SIN.*"),
            token_regex("ist|war")
        ],
        [  # Frisches Obst und Gemüse ist gut für die Gesundheit.
            token("Obst"),
            token("und"),
            token("Gemüse")
        ],
        [
            token("Sport"),
            token("und"),
            token("Spiel")
        ],
        [  # Das bedeutendste Bauwerk und Wahrzeichen der Stadt ist die …
            token("das"),
            pos_regex("(ADJ|PA[12]).*NEU.*"),
            pos_regex("SUB.*NEU.*"),
            token("und"),
            pos_regex("SUB.*NEU.*"),
            token_regex("der|dieser"),
            pos_regex("SUB.*"),
            token_regex("ist|war")
        ],
        [  # Die bedeutendsten Bauwerke und Wahrzeichen der Stadt ist die …
            token("die"),
            pos_regex("(ADJ|PA[12]).*PLU.*"),
            pos_regex("SUB.*PLU.*"),
            token("und"),
            pos_regex("SUB.*PLU.*"),
            token_regex("der|dieser"),
            pos_regex("SUB.*"),
            token_regex("sind|waren")
        ],
        [  # Die neueste Auflage von Toms Kindheitserinnerungen ist schon wieder vergriffen.
            pos_regex("(ADJ|PA[12]|ART).*SIN.*"),
            pos_regex("SUB.*SIN.*"),
            pos_regex("PRP.*"),
            pos_regex("EIG.*GEN.*"),
            pos_regex("SUB.*"),
            token_regex("ist|war")
        ],
        [  # Die Aussichten für Japans Zukunft sind düster.
            pos_regex("(ADJ|PA[12]|ART).*PLU.*"),
            pos_regex("SUB.*PLU.*"),
            pos_regex("PRP.*"),
            pos_regex("EIG.*GEN.*"),
            pos_regex("SUB.*"),
            token_regex("sind|waren")
        ],
        [  # Anfänger wie auch Fortgeschrittene sind herzlich willkommen!
            pos_regex("SUB.*PLU.*"),
            token("wie"),
            token("auch"),
            token_regex(".+"),
            token_regex("sind|waren")
        ],
        [
            # "Heute ist sie lieb."
            token_regex("ist|war|wäre?"),
            pos_regex("EIG:NOM:SIN.*|PRO:PER:NOM:SIN.*"),
            pos_regex("ADJ:PRD:GRU")
        ],
        [
            # "Heute bist du lieb."
            token_regex("bist|w[äa]rst"),
            token_regex("du"),
            pos_regex("ADJ:PRD:GRU")
        ],
        [
            # "Heute waren sie lieb."
            token_regex("sind|w[äa]ren|seid"),
            pos_regex("PRO:PER:NOM:PLU.*"),
            pos_regex("ADJ:PRD:GRU")
        ],
        [  # Der Eifer der Männer und Frauen ist enorm.
            pos("SUB:NOM:SIN:MAS"),
            pos_regex("ART:...:GEN:PLU:MAS"),
            pos_regex("SUB:GEN:PLU:.+"),
            pos("KON:NEB"),
            pos_regex("SUB:GEN:PLU:.+"),
            token_regex("ist|w[äa]r")
        ],
        [  # Einer der bedeutendsten Māori-Autoren der Gegenwart ist Witi Ihimaera.
            PatternTokenBuilder().cs_token("Laut").set_skip(4).build(),
            PatternTokenBuilder().cs_token("und").set_skip(5).build(),
            token_regex("ist|war"),
            token_regex("d(er|ie|as)"),
            pos_regex("SUB:NOM:SIN:.+")
        ],
        [  # Für Tunesiens Tourismusindustrie mit seinen Stränden, Oasen und antiken Kulturschätzen ist das Attentat
            # ein verheerender Rückschlag.
            token_regex("ist|war"),
            token_regex("d(er|ie|as)"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB:NOM:SIN:.+"),
            pos_regex("(ART|PRO:POS).*SIN.*"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB:NOM:SIN:.+")
        ],
        [  # Die gute Nachricht vorweg: Die Mehrheit der Ehen sind tatsächlich ein Bund fürs Leben.
            token_regex("die"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            token_regex("Mehrheit"),
            token_regex("der|dieser|aller|unse?rer|[dsm]einer|euer|eurer|ihrer"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB.*NOM.*PLU.*"),
            token_regex("sind|w[äa]ren")
        ],
        [  # Man darf jedoch auch nicht glauben, weil die Brustvergrößerungscremes ein Allheilmittel sind, jedoch
            # sind Sie optimal um Ihr Selbstvertrauen zu erhöhen
            token_regex("weil|da|denn|dass"),
            token_regex("die|diese|solche|alle|viele|beide|einige|[mkds]eine|eure|unse?re|ihre"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB.*NOM.*PLU.*"),
            token_regex("ein"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB.*NOM.*SIN.*"),
            token_regex("sind|w[äa]ren")
        ],
        [  # Die Rechte der Kinder sind universell.
            token_regex("alle|die(se)?|einige|keine|viele|solche"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB.*NOM.*PLU.*"),
            token_regex("der|unse?rer|euer|eurer|[dsm]einer|dieser|solcher|aller|einiger|vieler|ihrer|beider"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB.*GEN.*PLU.*"),
            pos_regex("VER.*PLU.*")
        ],
        [
            # Ich verspreche dir, dass wir ein tolles Team sind.
            token_regex("wir|sie|die|alle|diese|einige|manche|viele|sonstige"),
            pos_regex("ART.*|PRO:(POS|DEM|IND).*"),
            PatternTokenBuilder().pos_regex("(ADJ|PA[12]).*").min(0).build(),
            pos_regex("SUB.*SIN.*"),
            pos_regex("VER.*PLU.*")
        ],
        [
            # Ich verspreche dir, dass wir ein wirklich tolles Team sind.
            token_regex("wir|sie|die|alle|diese|einige|manche|viele|sonstige"),
            pos_regex("ART.*|PRO:(POS|DEM|IND).*"),
            pos_regex("(ADJ|PA[12]).*|ADV.*"),
            pos_regex("(ADJ|PA[12]).*"),
            pos_regex("SUB.*SIN.*"),
            pos_regex("VER.*PLU.*")
        ],
        [
            PatternTokenBuilder().token("sie").set_skip(-1).build(),
            token_regex("sind|w[äa]ren")
        ],
        [
            token_regex("weder"),
            token_regex("er|es|sie"),
            PatternTokenBuilder().token("noch").set_skip(-1).build(),
            token_regex("sind|w[äa]ren")
        ],
        [
            PatternTokenBuilder().pos_regex("SUB.*PLU.*").set_skip(5).build(),
            token_regex("sind|w[äa]ren")
        ],
        [
            # Halte ich für unwahrscheinlich, dass es Spannungsspitzen sind.
            PatternTokenBuilder().pos_regex("SUB.*INF|SUB.*PLU.*").build(),
            token_regex("sind|w[äa]ren")
        ],
        [
            token_regex("Teile"),
            token_regex("de[rs]|diese[sr]|[msd]?eine[rs]"),
            PatternTokenBuilder().pos_regex("SUB.*|EIG.*|UNKNOWN").set_skip(-1).build(),
            token_regex("sind|w[äa]ren")
        ],
        [
            token_regex("viele|alle"),
            PatternTokenBuilder().pos_regex("SUB.*ADJ").token_regex(".+e").build(),
            token_regex("sind|w[äa]ren")
        ],
        [
            # Sinn und Zweck dieser Prüfung ist, herauszufinden, ob der Druck
            token_regex("Sinn"),
            token_regex("und"),
            PatternTokenBuilder().token_regex("Zweck").set_skip(-1).build(),
            token_regex("ist|war")
        ],
    ]


_ANTI_PATTERNS = _anti_patterns()
_MAX_ANTI_PATTERN_SIZE = max(len(ap) for ap in _ANTI_PATTERNS)

_anti_pattern_cache = {}
_anti_pattern_lock = threading.Lock()


def _is_currency(token):
    return token.token in _CURRENCIES


def _has_unknown_token_at(tokens, start_pos, end_pos):
    for i in range(start_pos, end_pos):
        for analyzed_token in tokens[i].readings:
            if analyzed_token.has_no_tag():
                return True
    return False


def _has_unknown_token_to_the_left(tokens, start_pos):
    # needed to avoid false alarms, because we cannot unify noun phrases if we cannot analyse a noun
    return _has_unknown_token_at(tokens, 0, start_pos)


def _has_unknown_token_to_the_right(tokens, start_pos):
    return _has_unknown_token_at(tokens, start_pos, len(tokens) - 1)


def _has_question_pronoun_to_the_left(tokens, start_pos):
    for i in range(start_pos, 0, -1):
        if tokens[i].token.lower() in _QUESTION_PRONOUNS:
            return True
    return False


def _has_verb_to_the_left(tokens, start_pos):
    for i in range(start_pos, 0, -1):
        if tokens[i].matches_pos_tag_regex(_VERB_TO_THE_LEFT):
            return True
    return False


def _contains_regex_to_the_left(p, tokens, start_pos):
    for i in range(start_pos, 0, -1):
        if p.fullmatch(tokens[i].token):
            return True
    return False


def _get_singular_for(token):
    for singular, plural in _PAIRS:
        if plural == token:
            return singular
    raise RuntimeError("No singular found for '" + token + "'")


def _get_plural_for(token):
    for singular, plural in _PAIRS:
        if singular == token:
            return plural
    raise RuntimeError("No plural found for '" + token + "'")


def _tagger_lookup(tagger, word):
    """GermanTagger.lookup(word): the readings of word (tagged without
    ignoring the case), or None if it is unknown"""
    lookup = getattr(tagger, 'lookup', None)
    if lookup is not None:
        return lookup(word)
    atr = tagger.tag([word])[0]
    if atr.readings[0].pos_tag is None:
        return None
    return atr


class SubjectVerbAgreementRule(CoreRule):
    """Port of org.languagetool.rules.de.SubjectVerbAgreementRule. Detects
    e.g. the errors in "Das Auto sind schnell.", "Das Auto waren schnell.",
    "Die Autos ist schnell.", "Die Katze und der Hund ist schön." (relies on
    the chunk tags of the GermanChunker)."""

    rule_id = 'DE_SUBJECT_VERB_AGREEMENT'
    category_id = 'GRAMMAR'

    def __init__(self, messages, language, user_config=None, **kwargs):
        super().__init__(messages, language)
        self.singular = set(p[0] for p in _PAIRS)
        self.plural = set(p[1] for p in _PAIRS)
        self.add_example_pair("Die Autos <marker>ist</marker> schnell.",
                              "Die Autos <marker>sind</marker> schnell.")
        self.url = "https://dict.leo.org/grammatik/deutsch/Wort/Verb/Kategorien/Numerus-Person/ProblemNum.html"

    def get_description(self):
        return "Kongruenz von Subjekt und Prädikat (unvollständig)"

    def estimate_context_for_sure_match(self):
        return _MAX_ANTI_PATTERN_SIZE

    def get_anti_patterns(self):
        key = self.language.code
        aps = _anti_pattern_cache.get(key)
        if aps is None:
            with _anti_pattern_lock:
                aps = _anti_pattern_cache.get(key)
                if aps is None:
                    aps = _anti_pattern_cache[key] = make_anti_patterns(_ANTI_PATTERNS, self.language)
        return aps

    def match(self, sentence):
        rule_matches = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        for i in range(1, len(tokens)):  # start at 1 to skip SENT_START
            tok = tokens[i]
            if tok.immunized:
                continue
            token_str = tok.token
            # Detect e.g. "Der Hund und die Katze ist":
            singular_match = self._get_singular_match_or_none(tokens, i, tok, token_str, sentence)
            if singular_match is not None:
                rule_matches.append(singular_match)
            # Detect e.g. "Der Hund sind":
            plural_match = self._get_plural_match_or_none(tokens, i, tok, token_str, sentence)
            if plural_match is not None:
                rule_matches.append(plural_match)
        return rule_matches

    def _get_singular_match_or_none(self, tokens, i, token, token_str, sentence):
        if token_str in self.singular:
            prev_token = tokens[i - 1]
            next_token = tokens[i + 1] if i + 1 < len(tokens) else None
            prev_chunk_tags = prev_token.chunk_tags
            match = _NPP in prev_chunk_tags \
                and _PP not in prev_chunk_tags \
                and prev_token.token != "Uhr" \
                and not _is_currency(prev_token) \
                and not (next_token is not None and next_token.token == "es") \
                and self.prev_chunk_is_nominative(tokens, i - 1) \
                and not _has_unknown_token_to_the_left(tokens, i) \
                and not _has_question_pronoun_to_the_left(tokens, i - 1) \
                and not _has_verb_to_the_left(tokens, i - 1) \
                and not _contains_regex_to_the_left(_LEFT_REGEX, tokens, i - 1) \
                and not self._contains_only_infinitives_to_the_left(tokens, i - 1)
            # ('um 18 Uhr ist Feierabend', 'zehn Jahre ist es her')
            if match:
                message = "Bitte prüfen, ob hier <suggestion>" + _get_plural_for(token_str) + \
                          "</suggestion> stehen sollte."
                return RuleMatch(self, sentence, token.start_pos, token.end_pos, message)
        return None

    def _get_plural_match_or_none(self, tokens, i, token, token_str, sentence):
        if token_str in self.plural:
            prev_token = tokens[i - 1]
            prev_chunk_tags = prev_token.chunk_tags
            next_token = tokens[i + 1] if i + 1 < len(tokens) else None
            match = _NPS in prev_chunk_tags \
                and not (next_token is not None and next_token.token == "Sie") \
                and _NPP not in prev_chunk_tags \
                and _PP not in prev_chunk_tags \
                and not _is_currency(prev_token) \
                and self.prev_chunk_is_nominative(tokens, i - 1) \
                and not _has_unknown_token_to_the_left(tokens, i) \
                and not _has_unknown_token_to_the_right(tokens, i + 1) \
                and tokens[1].token not in ("Alle", "Viele") \
                and not self.is_followed_by_nominative_plural(tokens, i + 1)
            # ('Eine Persönlichkeit sind Sie selbst.', "Viele Brunnen in Italiens Hauptstadt sind bereits
            # abgeschaltet.", "Die Zielgruppe sind Männer." - beides Nominativ, aber 'Männer' ist das Subjekt)
            if match:
                message = "Bitte prüfen, ob hier <suggestion>" + _get_singular_for(token_str) + \
                          "</suggestion> stehen sollte."
                return RuleMatch(self, sentence, token.start_pos, token.end_pos, message)
        return None

    def prev_chunk_is_nominative(self, tokens, start_pos):
        for i in range(start_pos, 0, -1):
            chunk_tags = tokens[i].chunk_tags
            if _NPS in chunk_tags or _NPP in chunk_tags:
                if tokens[i].has_partial_pos_tag("NOM"):
                    return True
            else:
                return False
        return False

    def _contains_only_infinitives_to_the_left(self, tokens, start_pos):
        # No false alarm on ""Das Kopieren und Einfügen ist sehr nützlich." etc.
        infinitives = 0
        tagger = None
        for i in range(start_pos, 0, -1):
            tok = tokens[i].token
            if tokens[i].has_partial_pos_tag("SUB:"):
                if tagger is None:
                    tagger = self.language.tagger
                lookup = _tagger_lookup(tagger, tok.lower())
                if lookup is not None and lookup.has_pos_tag_starting_with("VER:INF"):
                    infinitives += 1
                else:
                    return False
        return infinitives >= 2

    def is_followed_by_nominative_plural(self, tokens, start_pos):
        for i in range(start_pos, len(tokens)):
            tok = tokens[i]
            if tok.has_any_partial_pos_tag("SUB", "PRO") \
                    and (tok.has_partial_pos_tag("NOM:PLU") or _NPP in tok.chunk_tags):  # NPP catches 'und' phrases
                return True
        return False
