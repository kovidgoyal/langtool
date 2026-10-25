"""German punctuation and typography rules: port of
org.languagetool.rules.de.GermanCommaWhitespaceRule,
GermanUnpairedBracketsRule, GermanUnpairedQuotesRule,
SentenceWhitespaceRule, GermanDoublePunctuationRule, DashRule and
UnitConversionRule."""

from ... import jregex
from ...rules.abstract_rules import GenericUnpairedQuotesRule
from ...rules.base import Rule, RuleMatch
from ...rules.core import (Categories, CommaWhitespaceRule, DoublePunctuationRule, GenericUnpairedBracketsRule)
from ...rules.core import SentenceWhitespaceRule as _CoreSentenceWhitespaceRule
from ...rules.unit_conversion import (AbstractUnitConversionRule, CELSIUS, CHECK, CHECK_UNKNOWN_UNIT, CUBIC_METRE,
                                      DecimalFormat, FAHRENHEIT, FEET, HOUR, INCH, KILOGRAM, KILOMETRE_PER_HOUR,
                                      LITRE, METRE, MILE, POUND, SQUARE_METRE, SUGGESTION, UNIT_MISMATCH, YARD)
from ...tools import is_upper_case

_DOMAINS = jregex.compile('[a-z]{2,10}-Domains?')


class GermanCommaWhitespaceRule(CommaWhitespaceRule):
    """Port of org.languagetool.rules.de.GermanCommaWhitespaceRule: a dot
    before "xy-Domain(s)" ("5 Millionen .de-Domains") is no error. (The
    example pair and the URL of the Java constructor are given in the rule
    spec of languages.py.)"""

    def is_exception(self, tokens, token_idx):
        if token_idx + 2 < len(tokens) and tokens[token_idx].token == '.' and \
                _DOMAINS.fullmatch(tokens[token_idx + 1].token):
            return True
        return False


class GermanUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.de.GermanUnpairedBracketsRule:
    unpaired (), [] and {} (the quotes are checked by
    GermanUnpairedQuotesRule)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, ['[', '(', '{'], [']', ')', '}'], 'UNPAIRED_BRACKETS')
        self.url = 'https://languagetool.org/insights/de/beitrag/klammern/'
        self.add_example_pair('Dem Präsidenten des Deutschen Bauernverbands <marker>(</marker>DBV zufolge habe die '
                              'Dürre einen Schaden von 1,4 Millionen verursacht.',
                              'Dem Präsidenten des Deutschen Bauernverbands <marker>(</marker>DBV) zufolge habe die '
                              'Dürre einen Schaden von 1,4 Millionen verursacht.')

    def get_id(self):
        return 'UNPAIRED_BRACKETS'  # no "DE_" to be compatible with old versions


class GermanUnpairedQuotesRule(GenericUnpairedQuotesRule):
    """Port of org.languagetool.rules.de.GermanUnpairedQuotesRule: unpaired
    „“, »«, «», "", '', ‚‘, ›‹ and ‹›."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, ['„', '»', '«', '"', "'", '‚', '›', '‹'],
                         ['“', '«', '»', '"', "'", '‘', '‹', '›'], 'DE_UNPAIRED_QUOTES')
        self.url = 'https://languagetool.org/insights/de/beitrag/klammern/'
        self.add_example_pair('»Hallo Hans ist das dein <marker>›</marker>neues Auto?«, fragte er.',
                              '»Hallo Hans ist das dein <marker>›</marker>neues‹ Auto?«, fragte er.')

    def get_id(self):
        return 'DE_UNPAIRED_QUOTES'


class SentenceWhitespaceRule(_CoreSentenceWhitespaceRule):
    """Port of org.languagetool.rules.de.SentenceWhitespaceRule: checks that
    there's whitespace between sentences and after ordinal numbers.
    Registered for 'de' under the name SentenceWhitespaceRule, replacing
    the core rule of that name."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.category = Categories.get('MISC', messages)
        self.loc_quality_issue_type = 'Whitespace'
        self.url = ('https://languagetool.org/insights/de/beitrag/grammatik-leerzeichen/'
                    '#fehler-1-leerzeichen-vor-und-nach-satzzeichen')
        self.add_example_pair('Hier steht ein Satz.<marker>Das</marker> ist ein weiterer Satz.',
                              'Hier steht ein Satz.<marker> Das</marker> ist ein weiterer Satz.')

    def get_id(self):
        return 'DE_SENTENCE_WHITESPACE'

    def get_description(self):
        return 'Fehlendes Leerzeichen zwischen Sätzen oder nach Ordnungszahlen'

    def get_message(self, prev_sentence_ends_with_number):
        if prev_sentence_ends_with_number:
            return 'Fügen Sie nach Ordnungszahlen (1., 2. usw.) ein Leerzeichen ein.'
        return 'Fügen Sie zwischen Sätzen ein Leerzeichen ein.'


class GermanDoublePunctuationRule(DoublePunctuationRule):
    """Port of org.languagetool.rules.de.GermanDoublePunctuationRule: double
    punctuation rule with German-specific error message."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.url = ('https://dict.leo.org/grammatik/deutsch/Rechtschreibung/Amtlich/Interpunktion/'
                    'pgf101-105.html#grammarpgf103')
        self.add_example_pair('Sein Vater ist Regierungsrat <marker>a. D..</marker>',
                              'Sein Vater ist Regierungsrat <marker>a. D.</marker>')

    def get_id(self):
        return 'DE_DOUBLE_PUNCTUATION'

    def get_dot_message(self):
        return 'Zwei aufeinander folgende Punkte. Auch wenn ein Satz mit einer Abkürzung endet, ' \
               'endet er nur mit einem Punkt (§103 Regelwerk).'


class DashRule(Rule):
    """Port of org.languagetool.rules.de.DashRule: prüft, dass in
    Bindestrich-Komposita kein Leerzeichen eingefügt wird (wie z.B. in
    'Diäten- Erhöhung')."""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.language = language
        self.category = Categories.get('COMPOUNDING', messages)
        self.url = ('https://languagetool.org/insights/de/beitrag/grammatik-leerzeichen/'
                    '#fehler-1-leerzeichen-vor-und-nach-satzzeichen')
        self.add_example_pair('Bundestag beschließt <marker>Diäten- Erhöhung</marker>',
                              'Bundestag beschließt <marker>Diäten-Erhöhung</marker>')

    def get_id(self):
        return 'DE_DASH'

    def get_description(self):
        return "Keine Leerzeichen in Bindestrich-Komposita (wie z.B. in 'Diäten- Erhöhung')"

    def match(self, sentence):
        rule_matches = []
        tokens = sentence.get_tokens_without_whitespace()
        prev_token = None
        for i in range(len(tokens)):
            token = tokens[i].token
            if prev_token is not None and prev_token.endswith('-') and prev_token != '-' \
                    and '--' not in prev_token and '–-' not in prev_token:  # first char is some special kind of dash, found in Wikipedia
                first_char = token[0]
                if ord(first_char) <= 0xFFFF and is_upper_case(first_char):  # (Java: token.charAt(0))
                    if token not in ('UND', 'ODER', 'BZW'):  # ignore "NORD- UND SÜDKOREA"
                        msg = "Möglicherweise fehlt ein 'und' oder ein Komma, oder es wurde nach dem Wort " \
                              'ein überflüssiges Leerzeichen eingefügt. Eventuell haben Sie auch versehentlich ' \
                              'einen Bindestrich statt eines Punktes eingefügt.'
                        short_msg = "Fehlendes 'und' oder Komma oder überflüssiges Leerzeichen?"
                        from_pos = tokens[i - 1].start_pos
                        rule_match = RuleMatch(self, sentence, from_pos, tokens[i].end_pos, msg, short_msg)
                        rule_match.add_suggested_replacement(tokens[i - 1].token + tokens[i].token)
                        if tokens[i - 1].token.count('-') + tokens[i].token.count('-') <= 1:
                            rule_match.add_suggested_replacement(tokens[i - 1].token + ', ' + tokens[i].token)
                        rule_matches.append(rule_match)
            prev_token = token
        return rule_matches


class UnitConversionRule(AbstractUnitConversionRule):
    """Port of org.languagetool.rules.de.UnitConversionRule: the
    AbstractUnitConversionRule with German unit names, the number format of
    Locale.GERMANY (at most 2 fraction digits, HALF_UP) and German
    messages."""

    _format = DecimalFormat(decimal=',', grouping='.', maximum_fraction_digits=2)

    _MESSAGES = {
        CHECK: 'Diese Umrechnung scheint falsch zu sein. Wollen Sie sie automatisch korrigieren lassen?',
        SUGGESTION: 'Wollen Sie eine Umwandlung ins metrische System automatisch hinzufügen?',
        CHECK_UNKNOWN_UNIT: 'Die in dieser Umrechnung verwendete Einheit wurde nicht erkannt.',
        UNIT_MISMATCH: 'Diese Einheiten sind nicht kompatibel.',
    }
    _SHORT_MESSAGES = {
        CHECK: 'Falsche Umrechnung. Automatisch korrigieren?',
        SUGGESTION: 'Metrisches Äquivalent hinzufügen?',
        CHECK_UNKNOWN_UNIT: 'Unbekannte Einheit.',
        UNIT_MISMATCH: 'Inkompatible Einheiten.',
    }

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('Ich bin <marker>6 Fuß</marker> groß.',
                              'Ich bin <marker>6 Fuß (1,83 m)</marker> groß.')
        add = self.add_unit
        add('Kilo(gramm)?', KILOGRAM, 'Kilogramm', 1, True)
        add('Gramm', KILOGRAM, 'Gramm', 1e-3, True)
        add('Tonnen?', KILOGRAM, 'Tonnen', 1e3, True)
        add('Pfund', POUND, 'Pfund', 1, False)
        add('Meilen?', MILE, 'Meile', 1, False)
        add('Yard', YARD, 'Yard', 1, False)
        add('Fuß', FEET, 'Fuß', 1, False)
        add('Zoll', INCH, 'Zoll', 1, False)
        add('(Kilometer pro Stunde|Stundenkilometer)', KILOMETRE_PER_HOUR, 'Kilometer pro Stunde', 1, True)
        add('Meilen pro Stunde', MILE.divide(HOUR), 'Meilen pro Stunde', 1, False)
        add('Meter', METRE, 'Meter', 1, True)
        add('Kilometer', METRE, 'Kilometer', 1e3, True)
        # add('Dezimeter', METRE, 'Dezimeter', 1e-1, False)  # metric, but should not be suggested
        add('Zentimeter', METRE, 'Zentimeter', 1e-2, True)
        add('Millimeter', METRE, 'Millimeter', 1e-3, True)
        add('Mikrometer', METRE, 'Mikrometer', 1e-6, True)
        add('Nanometer', METRE, 'Nanometer', 1e-9, True)
        add('Pikometer', METRE, 'Pikometer', 1e-12, True)
        add('Femtometer', METRE, 'Femtometer', 1e-15, True)
        add('Quadratmeter', SQUARE_METRE, 'Quadratmeter', 1, True)
        add('Hektar', SQUARE_METRE, 'Hektar', 1e4, True)
        add('Ar', SQUARE_METRE, 'Ar', 1e2, True)
        add('Quadratkilometer', SQUARE_METRE, 'Quadratkilometer', 1e6, True)
        # add('Quadratdezimeter', SQUARE_METRE, 'Quadratdezimeter', 1e-2, False)  # Metric, but not commonly used
        add('Quadratzentimeter', SQUARE_METRE, 'Quadratzentimeter', 1e-4, True)
        add('Quadratmillimeter', SQUARE_METRE, 'Quadratmillimeter', 1e-6, True)
        add('Quadratmikrometer', SQUARE_METRE, 'Quadratmikrometer', 1e-12, True)
        add('Quadratnanometer', SQUARE_METRE, 'Quadratnanometer', 1e-18, True)
        add('Kubikmeter', CUBIC_METRE, 'Kubikmeter', 1, True)
        add('Kubikkilometer', CUBIC_METRE, 'Kubikkilometer', 1e9, True)
        # add('Kubikdezimeter', CUBIC_METRE, 'Kubikdezimeter', 1e-3, False)  # Metric, but not commonly used
        add('Kubikzentimeter', CUBIC_METRE, 'Kubikzentimeter', 1e-6, True)
        add('Kubikmillimeter', CUBIC_METRE, 'Kubikmillimeter', 1e-9, True)
        add('Kubikmikrometer', CUBIC_METRE, 'Kubikmikrometer', 1e-18, True)
        add('Kubiknanometer', CUBIC_METRE, 'Kubiknanometer', 1e-27, True)
        add('Liter', LITRE, 'Liter', 1, True)
        add('Milliliter', LITRE, 'Milliliter', 1e-3, True)
        add('(?:Grad)? Fahrenheit', FAHRENHEIT, 'Grad Fahrenheit', 1, False)
        add('(?:Grad)? Celsius', CELSIUS, 'Grad Celsius', 1, True)

    def get_id(self):
        return 'EINHEITEN_METRISCH'

    def get_description(self):
        return 'Schlägt vor oder überprüft Angaben des metrischen Äquivalentes bei bestimmten Maßeinheiten.'

    def get_message(self, message):
        return self._MESSAGES[message]

    def get_short_message(self, message):
        return self._SHORT_MESSAGES[message]

    def get_number_format(self):
        return self._format


# the rule classes of this module (registered for 'de' under their class names; Java constructors
# (messages) or (messages, language), GermanCommaWhitespaceRule: (messages, examples, url), given in the spec)
RULES = (GermanCommaWhitespaceRule, GermanUnpairedBracketsRule, GermanUnpairedQuotesRule, SentenceWhitespaceRule,
         GermanDoublePunctuationRule, DashRule, UnitConversionRule)
