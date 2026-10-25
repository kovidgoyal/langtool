"""Port of org.languagetool.chunking.GermanChunker."""

import re

from ... import jregex
from ...chunking import ChunkTag, ChunkTaggedToken, TokenExpressionFactory
from ...openregex import RegularExpression
from ...patterns import string_matcher
from ...tools import char_to_lower, char_to_upper

# phrase types (GermanChunker.PhraseType)
NP = 'NP'  # "noun phrase", B-NP for the first token and I-NP for the following tokens (like OpenNLP)
NPS = 'NPS'  # "noun phrase singular"
NPP = 'NPP'  # "noun phrase plural"
PP = 'PP'  # "prepositional phrase" and similar

_FILTER_TAGS = frozenset(('PP', 'NPP', 'NPS'))
_FACTORY = TokenExpressionFactory(False)

_SIMPLE_FORM_REGEXP = jregex.compile('(^| )<([a-zäöüß|()\\[\\]?,]+)>\\+?( |$)', jregex.IGNORECASE)

_SYNTAX_EXPANSION = {
    '<NP>': '<chunk=B-NP> <chunk=I-NP>*',
    '&prozent;': 'Prozent|Kilo|Kilogramm|Gramm|Euro|Pfund',
}

_O = ChunkTag('O')
_B_NP = ChunkTag('B-NP')
_I_NP = ChunkTag('I-NP')

_debug = False


def set_debug(debug_mode):
    """For internal use only"""
    global _debug
    _debug = debug_mode


def is_debug():
    """For internal use only"""
    return _debug


def _ci_key(s):
    """Key of String.CASE_INSENSITIVE_ORDER equality"""
    return ''.join(char_to_lower(char_to_upper(c)) for c in s)


class _RegularExpressionWithPhraseType:

    __slots__ = ('expression', 'phrase_type', 'overwrite', 'form_hints')

    def __init__(self, expression, phrase_type, overwrite, form_hints):
        self.expression = expression
        self.phrase_type = phrase_type
        self.overwrite = overwrite
        # each element: the case-insensitive keys of the possible forms, one of which must be in the sentence
        self.form_hints = form_hints

    def __str__(self):
        return '%s <= %s (overwrite: %s)' % (self.phrase_type, self.expression, 'true' if self.overwrite else 'false')


def _build(expr, phrase_type, overwrite=False):
    expanded_expr = expr
    for key, value in _SYNTAX_EXPANSION.items():
        expanded_expr = expanded_expr.replace(key, value)
    return _build_expanded(expanded_expr, phrase_type, overwrite, _calc_form_hints(expanded_expr))


def _build_expanded(expanded_expr, phrase_type, overwrite, form_hints):
    expression = RegularExpression.compile(expanded_expr, _FACTORY.create)
    hints = tuple(frozenset(_ci_key(h) for h in hint) for hint in form_hints)
    return _RegularExpressionWithPhraseType(expression, phrase_type, overwrite, hints)


def _calc_form_hints(expanded_expr):
    form_hints = []
    for m in _SIMPLE_FORM_REGEXP.finditer(expanded_expr):
        possible_values = string_matcher.create(m.group(2), True, False).get_possible_values()
        if possible_values is not None:
            form_hints.append(possible_values)
    return form_hints


_UND_ODER_BZW = [('und', 'oder', 'bzw')]

# REGEXES1 and REGEXES2 are OpenRegex expressions (see langtool.openregex and
# langtool.chunking.TokenPredicate for the syntax:
# <string|regex|regexCS|chunk|pos|posregex|posre=value>, <foo> is short for
# <string=foo>, <pos=X> matches tokens with POS tags that contain X as a
# substring, conditions are combined with & and negated with !).
# REGEXES1 roughly emulates the behavior of the OpenNLP chunker by tagging the
# first token of a noun phrase with B-NP and the remaining ones with I-NP.
# REGEXES2 builds on those annotations to find complex noun phrases.
# See _SYNTAX_EXPANSION for strings that get expanded before interpreted by
# OpenRegex. The chunks are added to the existing chunks, unless overwrite is
# true, in which case existing chunks get overwritten.
_regexes = None


def _regex_lists():
    global _regexes
    if _regexes is None:
        regexes1 = [
            # "das Auto", "das schöne Auto", "das sehr schöne Auto", "die Pariser Innenstadt":
            _build('(<posre=^ART.*>|<pos=PRO>)? <pos=ADV>* <pos=PA2>* <pos=ADJ>* <pos=SUB>+', NP),
            # "Mythen und Sagen":
            _build_expanded('<pos=SUB> (<und|oder>|(<bzw> <.>)) <pos=SUB>', NP, False, _UND_ODER_BZW),
            # "ältesten und bekanntesten Maßnahmen":
            _build_expanded('<pos=ADJ> (<und|oder>|(<bzw> <.>)) <pos=PA2> <pos=SUB>', NP, False, _UND_ODER_BZW),
            # "räumliche und zeitliche Abstände":
            _build_expanded('<pos=ADJ> (<und|oder>|(<bzw> <.>)) <pos=ADJ> <pos=SUB>', NP, False, _UND_ODER_BZW),

            # "eine leckere Lasagne":
            _build('<posre=^ART.*> <pos=ADV>* <pos=ADJ>* <regexCS=[A-ZÖÄÜ][a-zöäü]+>', NP),  # Lexikon kennt nicht alle Nomen, also so...

            _build('<pos=PRO>? <pos=ZAL> <pos=SUB>', NP),  # "zwei Wochen", "[eines] ihrer drei Autos"

            _build('<Herr|Herrn|Frau> <pos=EIG>+', NP),
            _build('<Herr|Herrn|Frau> <regexCS=[A-ZÖÄÜ][a-zöäü-]+>+', NP),  # für seltene Nachnamen, die nicht im Lexikon sind

            _build('<der>', NP),  # simulate OpenNLP?!
        ]
        regexes2 = [
            # ===== plural and singular noun phrases, based on OpenNLP chunker output ===============
            # "In christlichen, islamischen und jüdischen Traditionen":
            _build('<pos=ADJ> <,> <chunk=B-NP> <chunk=I-NP>* <und|sowie> <NP>', NPP),
            # "ein Hund und eine Katze":
            _build('<chunk=B-NP & !regex=jede[rs]?> <chunk=I-NP>* <und|sowie> <pos=ADV>? <NP>', NPP),
            # "größte und erfolgreichste Erfindung" (fixes mistagging introduced above):
            _build('<pos=ADJ> <und|sowie> <chunk=B-NP & !pos=PLU> <chunk=I-NP>*', NPS, True),
            # "deren Bestimmung und Funktion" (fixes mistagging introduced above):
            _build('<deren> <chunk=B-NP & !pos=PLU> <und|sowie> <chunk=B-NP>*', NPS, True),
            # "Julia und Karsten":
            _build('<pos=EIG> <und> <pos=EIG>', NPP),
            # "die älteste und bekannteste Maßnahme" - OpenNLP won't detect that as one NP:
            _build('<pos=ART> <pos=ADJ> <und|sowie> (<pos=ADJ>|<pos=PA2>) <chunk=I-NP & !pos=PLU>+', NPS, True),
            # "eine Masseeinheit und keine Gewichtseinheit":
            _build('<chunk=B-NP & !pos=PLU> <chunk=I-NP>* <und|sowie> <keine> <chunk=I-NP>+', NPS, True),
            # "Der See und das anliegende Marschland":
            _build('<NP> <und|sowie> <pos=ART> <pos=PA1> <pos=SUB>', NPP, True),

            # "eins ihrer drei Autos":
            _build('<eins|eines> <chunk=B-NP> <chunk=I-NP>+', NPS),

            # "er und seine Schwester":
            _build('<ich|du|er|sie|es|wir|ihr|sie> <und|oder|sowie> <NP>', NPP),
            # "sowohl sein Vater als auch seine Mutter":
            _build('<sowohl> <NP> <als> <auch> <NP>', NPP),
            # "sowohl Tom als auch Maria":
            _build('<sowohl> <pos=EIG> <als> <auch> <pos=EIG>', NPP),
            # "sowohl er als auch seine Schwester":
            _build('<sowohl> <ich|du|er|sie|es|wir|ihr|sie> <als> <auch> <NP>', NPP),
            # "Rekonstruktionen oder der Wiederaufbau", aber nicht "Isolation und ihre Überwindung":
            _build('<pos=SUB> <und|oder|sowie> <chunk=B-NP & !ihre> <chunk=I-NP>*', NPP),
            # "Weder Gerechtigkeit noch Freiheit":
            _build('<weder> <pos=SUB> <noch> <pos=SUB>', NPP),

            # "drei Katzen" - needed as ZAL cannot be unified, as it has no features:
            _build('<zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf> <chunk=I-NP>', NPP),

            # "der von der Regierung geprüfte Hund ist grün":
            _build('<chunk=B-NP> <pos=PRP> <NP> <chunk=B-NP & pos=SIN> <chunk=I-NP>*', NPS),
            _build('<chunk=B-NP> <pos=PRP> <NP> <chunk=B-NP & pos=PLU> <chunk=I-NP>*', NPP),

            # "der von der Regierung geprüfte Hund":
            _build('<chunk=B-NP> <pos=PRP> <NP> <pos=PA2> <chunk=B-NP & !pos=PLU> <chunk=I-NP>*', NPS),
            _build('<chunk=B-NP> <pos=PRP> <NP> <pos=PA2> <chunk=B-NP & !pos=SIN> <chunk=I-NP>*', NPP),

            # "Herr und Frau Schröder":
            _build('<Herr|Frau> <und> <Herr|Frau> <pos=EIG>*', NPP),

            # "ein Hund", aber nicht: "[kaum mehr als] vier Prozent":
            _build('<chunk=B-NP & !pos=ZAL & !pos=PLU & !chunk=NPP & !einige & !(regex=&prozent;)> '
                   '<chunk=I-NP & !pos=PLU & !und>*', NPS),  # "!und": OpenNLP packt "Bob und Tom" in eine NP
            # "die Hunde":
            _build('<chunk=B-NP & !pos=SIN & !chunk=NPS & !Ellen> <chunk=I-NP & !pos=SIN>*', NPP),

            # "die hohe Zahl dieser relativ kleinen Verwaltungseinheiten":
            _build('<chunk=NPS> <pos=PRO> <pos=ADJ> <pos=ADJ> <NP>', NPS),

            # "eine der am meisten verbreiteten Krankheiten":
            _build('<regex=eine[rs]?> <der> <am> <pos=ADJ> <pos=PA2> <NP>', NPS),
            # "einer der beiden Höfe":
            _build('<regex=eine[rs]?> <der> <beiden> <pos=ADJ>* <pos=SUB>', NPS),
            # "Einer seiner bedeutendsten Kämpfe":
            _build('<regex=eine[rs]?> <seiner|ihrer> <pos=PA1> <pos=SUB>', NPS),

            # "xy Prozent" - beide Varianten okay (zumindest umgangssprachlich):
            # siehe https://dict.leo.org/grammatik/deutsch/Wort/Verb/Kategorien/Numerus-Person/ProblemNum.html#grammarAnchor-Mengenangabe-49575
            _build('<regex=[\\d,.]+> <&prozent;>', NPS),
            _build('<regex=[\\d,.]+> <&prozent;>', NPP),

            # "[alle Arbeitsplätze so umzugestalten,] dass sie wie ein Spiel":
            _build('<dass> <sie> <wie> <NP>', NPP),
            # "[so dass Knochenbrüche und] Platzwunden die Regel [sind]"
            _build('<pos=PLU> <die> <Regel>', NPP),
            # "Veranstaltung, die immer wieder ein kultureller Höhepunkt", aber nicht "... in der Geschichte des Museums, die Sammlung ist seit 2011 zugänglich.":
            _build('<chunk=B-NP & pos=SIN> <chunk=I-NP & pos=SIN>* <,> <die> <pos=ADV>+ <chunk=NPS>+', NPS),
            # "Die Nauheimer Musiktage, die immer wieder ein kultureller Höhepunkt sind":
            _build('<chunk=B-NP & pos=PLU> <chunk=I-NP & pos=PLU>* <,> <die> <pos=ADV>+ <chunk=NPS>+', NPP),

            # ===== genitive phrases and similar ====================================================

            # "Das letzte der teilnehmenden Länder":
            _build('<der|die|das> <pos=ADJ> <der> <pos=PA1> <pos=SUB>', NPS),
            # "Ursachen der vorliegenden Durchblutungsstörung":
            _build('<pos=SUB & pos=PLU> <der> <pos=PA1> <pos=SUB>', NPP),
            # "die ältere der beiden Töchter":
            _build('<der|die|das> <pos=ADJ> <der> <pos=PRO>? <pos=SUB>', NPS),
            # "Synthese organischer Verbindungen", "die Anordnung der vier Achsen", aber nicht "Einige der Inhaltsstoffe":
            _build('<chunk=NPS & !einige> <chunk=NPP & (pos=GEN |pos=ZAL)>+', NPS, True),
            # "die Kenntnisse der Sprache":
            _build('<chunk=NPP> <chunk=NPS & pos=GEN>+', NPP, True),
            # "die Pyramide des Friedens und der Eintracht":
            _build('<chunk=NPS>+ <und> <chunk=NP[SP] & (pos=GEN | pos=ADV)>+', NPS, True),
            # "Teil der dort ausgestellten Bestände":
            _build('<chunk=NPS>+ <der> <pos=ADV> <pos=PA2> <chunk=I-NP>', NPS, True),
            # "Autor der ersten beiden Bücher":
            _build('<chunk=NPS>+ <der> (<pos=ADJ>|<pos=ZAL>) <NP>', NPS, True),
            # "Autor der beiden Bücher":
            _build('<chunk=NPS>+ <der> <NP>', NPS, True),
            # "Teil der umfangreichen dort ausgestellten Bestände":
            _build('<chunk=NPS>+ <der> <pos=ADJ> <pos=ADV> <pos=PA2> <NP>', NPS, True),
            # "die Krankheit unserer heutigen Städte und Siedlungen":
            _build('<chunk=NPS>+ <pos=PRO:POS> <pos=ADJ> <NP>', NPS, True),
            # "der letzte der vier großen Flüsse":
            _build('<der|das> <pos=ADJ> <der> <pos=ZAL> <NP>', NPS, True),

            # "eine Menge englischer Wörter [sind aus dem Lateinischen abgeleitet]":
            # NPP stimmt aber nicht für Mathematik, dort NPS: "Eine Menge ist ein Konzept der Mathematik."
            _build('<eine> <menge> <NP>+', NPP, True),
            # "dass [sie und sein Sohn ein Paar] sind":
            _build('<er|sie|es> <und> <NP> <NP>', NPP),

            # ===== prepositional phrases ===========================================================

            # "laut den meisten Quellen":
            _build('<laut> <regex=.*>{0,3} <Quellen>', PP, True),
            # "bei den sehr niedrigen Oberflächentemperaturen" (OpenNLP doesn't find this)
            _build('<pos=PRP> <pos=ART:> <pos=ADV>* <pos=ADJ> <NP>', PP, True),
            # "in den alten Religionen, Mythen und Sagen":
            _build('<pos=PRP> <chunk=NPP>+ <,> <NP>', PP, True),
            # "für die Stadtteile und selbständigen Ortsteile":
            _build('<pos=PRP> <chunk=NPP>+', PP, True),
            # "Das Bündnis zwischen der Sowjetunion und Kuba":
            _build('<pos=PRP> <der> <chunk=NPP>+', PP),
            # "in chemischen Komplexverbindungen", "für die Fische":
            _build('<pos=PRP> <NP>', PP),
            # "einschließlich der biologischen und sozialen Grundlagen":
            _build('<pos=PRP> <NP> <pos=ADJ> <und|oder|bzw.> <NP>', PP),
            # "für Ärzte und Ärztinnen festgestellte Risikoprofil", "der als Befestigung gedachte östliche Teil der Burg":
            _build('<pos=PRP> (<NP>)+', PP),
            # "in den darauf folgenden Wochen":
            _build('<pos=PRP> <chunk=B-NP> <pos=ADV> <NP>', PP),
            # "in nur zwei Wochen":
            _build('<pos=PRP> <pos=ADV> <pos=ZAL> <chunk=B-NP>', PP),
            # "in deren deutschen Installationen":
            _build('<pos=PRP> <pos=PRO> <NP>', PP),
            # "nach sachlichen und militärischen Kriterien" - we need to help OpenNLP a bit with this one:
            _build('<pos=PRP> <pos=ADJ> <und|oder|sowie> <NP>', PP),
            # "mit über 1000 Handschriften":
            _build('<pos=PRP> <pos=ADV> <regex=\\d+> <NP>', PP),
            # "über laufende Sanierungsmaßnahmen":
            _build('<pos=PRP> <pos=PA1> <NP>', PP),
            # "Aufgrund stark schwankender Absatzmärkte war die GEFA-Flug..."
            _build('<pos=PRP> <pos=ADJ> <pos=PA1> <NP>', PP),
            # "durch Einsatz größerer Maschinen und bessere Kapazitätsplanung":
            _build('<pos=PRP> <NP> <NP> <und|oder> <NP>', PP),
            # "bei sehr guten Beobachtungsbedingungen":
            _build('<pos=PRP> <pos=ADV> <pos=ADJ> <NP>', PP),
            # "[Von ursprünglich drei Almhütten] ist noch eine erhalten":
            _build('<pos=PRP> <pos=ADJ:PRD:GRU> <pos=ZAL> <NP>', PP),

            # "die darauffolgenden Jahre" -> eigentlich "in den darauffolgenden Jahren":
            _build('<die> <pos=ADJ> <Sekunden|Minuten|Stunden|Tage|Wochen|Monate|Jahre|Jahrzehnte|Jahrhunderte> (<NP>)?',
                   PP),
            # "die letzten zwei Monate" -> eigentlich "in den letzten zwei Monaten":
            _build('<die> <pos=ADJ> <pos=ZAL> '
                   '<Sekunden|Minuten|Stunden|Tage|Wochen|Monate|Jahre|Jahrzehnte|Jahrhunderte> (<NP>)?', PP),
            # "letztes Jahr":
            _build('<regex=(vor)?letzte[sn]?> <Woche|Monat|Jahr|Jahrzehnt|Jahrhundert>', PP),
            # "Für in Österreich lebende Afrikaner und Afrikanerinnen":
            _build('<für> <in> <pos=EIG> <pos=PA1> <pos=SUB> <und> <pos=SUB>', PP, True),

            # "die Beziehungen zwischen Kanada und dem Iran":
            _build('<chunk=NPP> <zwischen> <pos=EIG> <und|sowie> <NP>', NPP),
            # ", die die hauptsächliche Beute der Eisbären", ", welche der Urstoff aller Körper":
            _build('<,> <die|welche> <NP> <chunk=NPS & pos=GEN>+', NPP),
            # "Kommentare, Korrekturen, Kritik":
            _build('<NP> <,> <NP> <,> <NP>', NPP),
            # "Details, Dialoge, wie auch die Typologie der Charaktere":
            _build('<NP> <,> <NP> <,> <wie> <auch> <chunk=NPS>+', NPP),
        ]
        _regexes = (regexes1, regexes2)
    return _regexes


def _all_forms(tokens):
    return {_ci_key(token.token) for token in tokens}


def _has_all_form_hints(regex, all_forms):
    for hints in regex.form_hints:
        if all_forms.isdisjoint(hints):
            return False
    return True


def _get_chunk_tag(regex, match, i):
    if regex.phrase_type == NP:
        # we assign the same tags as the OpenNLP chunker
        return _B_NP if i == match.start_index() else _I_NP
    return ChunkTag(regex.phrase_type)


class GermanChunker:
    """A rule-based German chunker for noun phrases (the post-disambiguation
    chunker of German). Please note that this chunker has not been evaluated
    as a stand-alone chunker, it has only been used and tested in the
    context of LanguageTool's error detection rules."""

    def __init__(self):
        _regex_lists()

    def add_chunk_tags(self, token_readings):
        all_forms = _all_forms(token_readings)
        chunk_tagged_tokens = self._get_basic_chunks(token_readings, all_forms)
        for regex in _regex_lists()[1]:
            self._apply(regex, chunk_tagged_tokens, all_forms)
        self._assign_chunks_to_readings(chunk_tagged_tokens)

    def get_basic_chunks(self, token_readings):
        return self._get_basic_chunks(token_readings, _all_forms(token_readings))

    def _get_basic_chunks(self, token_readings, all_forms):
        chunk_tagged_tokens = []
        for token_reading in token_readings:
            if not token_reading.is_whitespace:
                chunk_tagged_tokens.append(ChunkTaggedToken(token_reading.token, [_O], token_reading))
        if _debug:
            print('=============== CHUNKER INPUT ===============')
            print(self._get_debug_string(chunk_tagged_tokens))
        for regex in _regex_lists()[0]:
            self._apply(regex, chunk_tagged_tokens, all_forms)
        return chunk_tagged_tokens

    def _apply(self, regex, tokens, all_forms):
        if not _has_all_form_hints(regex, all_forms):
            return
        prev_debug = self._get_debug_string(tokens)
        try:
            affected_spans = self._do_apply_regex(regex, tokens)
            debug = self._get_debug_string(tokens)
            if debug != prev_debug:
                self._print_debug_info(regex, affected_spans, debug)
        except Exception as e:
            raise RuntimeError("Could not apply chunk regexp '%s' to tokens: %s" % (regex, tokens)) from e

    @staticmethod
    def _assign_chunks_to_readings(chunk_tagged_tokens):
        for tagged_token in chunk_tagged_tokens:
            readings = tagged_token.readings
            if readings is not None:
                readings.set_chunk_tags(tagged_token.chunk_tags)

    @staticmethod
    def _do_apply_regex(regex, tokens):
        matches = regex.expression.find_all(tokens)
        affected_spans = []
        for match in matches:
            start, end = match.start_index(), match.end_index()
            affected_spans.append((start, end))
            for i in range(start, end):
                token = tokens[i]
                new_chunk_tags = list(token.chunk_tags)
                if regex.overwrite:
                    new_chunk_tags = [t for t in new_chunk_tags if t.chunk_tag not in _FILTER_TAGS]
                new_tag = _get_chunk_tag(regex, match, i)
                if new_tag not in new_chunk_tags:
                    new_chunk_tags.append(new_tag)
                    if _O in new_chunk_tags:
                        new_chunk_tags.remove(_O)
                tokens[i] = ChunkTaggedToken(token.token, new_chunk_tags, token.readings)
        return affected_spans

    @staticmethod
    def _print_debug_info(regex, affected_spans, debug):
        print('=== Applied %s ===' % regex)
        if regex.overwrite:
            print('Note: overwrite mode, replacing old [PP, NPP, NPS] tags')
        debug_lines = debug.split('\n')
        while debug_lines and not debug_lines[-1]:
            debug_lines.pop()  # String.split() drops trailing empty strings
        for i, debug_line in enumerate(debug_lines):
            if any(start <= i < end for start, end in affected_spans):
                print(re.sub('^  ', ' *', debug_line, count=1))
            else:
                print(debug_line)
        print()

    @staticmethod
    def _get_debug_string(tokens):
        if not _debug:
            return ''
        sb = []
        for token in tokens:
            token_reading_str = str(token.readings).replace(token.token + '[', '[', 1)
            sb.append('  %s -- %s\n' % (token, token_reading_str))
        return ''.join(sb)
