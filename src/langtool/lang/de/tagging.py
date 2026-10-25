"""Port of org.languagetool.tagging.de.GermanTagger, SwissGermanTagger,
AdjectiveTags and VerbPrefixes.

GermanTagger is the BaseTagger for de/german.dict (with the manual
additions added.txt/added_custom.txt and removals removed.txt/
removed_custom.txt, see langtool.tagging.BaseTagger) with custom code for
words not in the dictionary: the expansions of de/hunspell/spelling.txt
(prefix_verb lines, adjectives with /A and participles with /P), compounds
(the last part, found with the strict GermanCompoundTokenizer, governs the
POS tags), gender gap forms ("Freund*innen"), verbs with separable and
non-separable prefixes, alternative imperative forms ("Geh!") and
substantivated adjectives ("Verletzter").
"""

import threading

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import BaseTagger, TaggedWord
from ...tools import is_digit, is_letter_or_digit, is_upper_case, java_equals_ignore_case, java_is_whitespace, \
    java_split, java_trim, lowercase_first_char, starts_with_lowercase, starts_with_uppercase, uppercase_first_char


# --- AdjectiveTags ---

class AdjectiveTags:
    """AdjectiveTags: the POS tags of the adjective forms (used for the /A
    and /P lines of spelling.txt)"""

    # adjective forms for base form, like "chemisch":
    tags_for_adj = ('ADJ:PRD:GRU',)

    # adjective forms ending in -e, like "chemische":
    tags_for_adj_e = (
        'ADJ:AKK:PLU:FEM:GRU:SOL', 'ADJ:AKK:PLU:MAS:GRU:SOL', 'ADJ:AKK:PLU:NEU:GRU:SOL', 'ADJ:AKK:SIN:FEM:GRU:DEF',
        'ADJ:AKK:SIN:FEM:GRU:IND', 'ADJ:AKK:SIN:FEM:GRU:SOL', 'ADJ:AKK:SIN:NEU:GRU:DEF',
        'ADJ:NOM:PLU:FEM:GRU:SOL', 'ADJ:NOM:PLU:MAS:GRU:SOL', 'ADJ:NOM:PLU:NEU:GRU:SOL', 'ADJ:NOM:SIN:FEM:GRU:DEF',
        'ADJ:NOM:SIN:FEM:GRU:IND', 'ADJ:NOM:SIN:FEM:GRU:SOL', 'ADJ:NOM:SIN:MAS:GRU:DEF', 'ADJ:NOM:SIN:NEU:GRU:DEF')

    tags_for_adj_en = (
        'ADJ:AKK:PLU:FEM:GRU:DEF', 'ADJ:AKK:PLU:FEM:GRU:IND', 'ADJ:AKK:PLU:MAS:GRU:DEF', 'ADJ:AKK:PLU:MAS:GRU:IND',
        'ADJ:AKK:PLU:NEU:GRU:DEF', 'ADJ:AKK:PLU:NEU:GRU:IND', 'ADJ:AKK:SIN:MAS:GRU:DEF', 'ADJ:AKK:SIN:MAS:GRU:IND',
        'ADJ:AKK:SIN:MAS:GRU:SOL', 'ADJ:DAT:PLU:FEM:GRU:DEF', 'ADJ:DAT:PLU:FEM:GRU:IND', 'ADJ:DAT:PLU:FEM:GRU:SOL',
        'ADJ:DAT:PLU:MAS:GRU:DEF', 'ADJ:DAT:PLU:MAS:GRU:IND', 'ADJ:DAT:PLU:MAS:GRU:SOL', 'ADJ:DAT:PLU:NEU:GRU:DEF',
        'ADJ:DAT:PLU:NEU:GRU:IND', 'ADJ:DAT:PLU:NEU:GRU:SOL', 'ADJ:DAT:SIN:FEM:GRU:DEF', 'ADJ:DAT:SIN:FEM:GRU:IND',
        'ADJ:DAT:SIN:MAS:GRU:DEF', 'ADJ:DAT:SIN:MAS:GRU:IND', 'ADJ:DAT:SIN:NEU:GRU:DEF', 'ADJ:DAT:SIN:NEU:GRU:IND',
        'ADJ:GEN:PLU:FEM:GRU:DEF', 'ADJ:GEN:PLU:FEM:GRU:IND', 'ADJ:GEN:PLU:MAS:GRU:DEF', 'ADJ:GEN:PLU:MAS:GRU:IND',
        'ADJ:GEN:PLU:NEU:GRU:DEF', 'ADJ:GEN:PLU:NEU:GRU:IND', 'ADJ:GEN:SIN:FEM:GRU:DEF', 'ADJ:GEN:SIN:FEM:GRU:IND',
        'ADJ:GEN:SIN:MAS:GRU:DEF', 'ADJ:GEN:SIN:MAS:GRU:IND', 'ADJ:GEN:SIN:MAS:GRU:SOL', 'ADJ:GEN:SIN:NEU:GRU:DEF',
        'ADJ:GEN:SIN:NEU:GRU:IND', 'ADJ:GEN:SIN:NEU:GRU:SOL', 'ADJ:NOM:PLU:FEM:GRU:DEF', 'ADJ:NOM:PLU:FEM:GRU:IND',
        'ADJ:NOM:PLU:MAS:GRU:DEF', 'ADJ:NOM:PLU:MAS:GRU:IND', 'ADJ:NOM:PLU:NEU:GRU:DEF', 'ADJ:NOM:PLU:NEU:GRU:IND')

    tags_for_adj_er = (
        'ADJ:DAT:SIN:FEM:GRU:SOL', 'ADJ:GEN:PLU:FEM:GRU:SOL', 'ADJ:GEN:PLU:MAS:GRU:SOL', 'ADJ:GEN:PLU:NEU:GRU:SOL',
        'ADJ:GEN:SIN:FEM:GRU:SOL', 'ADJ:NOM:SIN:MAS:GRU:IND', 'ADJ:NOM:SIN:MAS:GRU:SOL')

    tags_for_adj_em = ('ADJ:DAT:SIN:MAS:GRU:SOL', 'ADJ:DAT:SIN:NEU:GRU:SOL')

    tags_for_adj_es = ('ADJ:AKK:SIN:NEU:GRU:IND', 'ADJ:AKK:SIN:NEU:GRU:SOL', 'ADJ:NOM:SIN:NEU:GRU:IND',
                       'ADJ:NOM:SIN:NEU:GRU:SOL')


# --- VerbPrefixes ---

# https://deutschegrammatik20.de/spezielle-verben/verben-mit-praefix-trennbare-und-nicht-trennbare-verben/uebersicht-trennbare-praefixe/
_VERB_PREFIXES = [
    "ab", "an", "auf", "aus", "auseinander", "bei", "ein", "empor", "entgegen", "entlang", "entzwei",
    "fehl", "fern", "fest", "fort", "gegenüber", "heim", "hinterher", "hoch", "los", "mit", "nach", "neben", "nieder",
    "vor", "weg", "weiter", "zu", "zurecht", "zurück", "zusammen", "da", "hin", "her",
    "herab", "heran", "herauf", "heraus", "herbei", "herein", "hernieder", "herüber", "herum", "herunter", "hervor",
    "herzu", "hinab", "hinan", "hinauf", "hinaus", "hinein", "hinüber", "hinunter", "hinweg", "hinzu", "vorab",
    "voran", "vorauf", "voraus", "vorbei", "vorweg", "vorher", "vorüber",
    "dabei", "dafür", "dagegen", "daher", "dahin", "dahinter", "daneben", "daran", "darauf", "darein", "darüber",
    "darunter", "hinter", "dran", "drauf", "drein", "drüber", "drunter",
    "davon", "davor", "dazu", "dazwischen",
    "durch", "über", "unter", "um", "wider", "wieder", "rüber", "aneinander", "ran", "rauf", "runter", "rein",
    # not listed in source above (deutschegrammatik20.de):
    "umher", "ent", "frei", "ver", "zer", "gegen"]
# sort alphabetically and then longest first:
_VERB_PREFIXES.sort()
_VERB_PREFIXES.sort(key=len, reverse=True)
_VERB_PREFIXES = tuple(_VERB_PREFIXES)


class VerbPrefixes:
    """VerbPrefixes: separable verb prefixes, longest first"""

    @staticmethod
    def get():
        return _VERB_PREFIXES


# --- GermanTagger constants ---

def _all_adj_gru_tags():
    tags = []
    for nom_akk_gen_dat in ('NOM', 'AKK', 'GEN', 'DAT'):
        for plu_sin in ('PLU', 'SIN'):
            for mas_fem_neu in ('MAS', 'FEM', 'NEU'):
                for def_ind_sol in ('DEF', 'IND', 'SOL'):
                    tags.append('ADJ:%s:%s:%s:GRU:%s' % (nom_akk_gen_dat, plu_sin, mas_fem_neu, def_ind_sol))
    return tuple(tags)


_ALL_ADJ_GRU_TAGS = _all_adj_gru_tags()
_MITARBEITENDEN_PATTERN = jregex.compile('[A-ZÖÄÜ][a-zöäüß]{2,25}mitarbeitenden?')
_GENDER_GAP_CHARS = jregex.compile('[*:_/]')
_AFTER_ASTERISK = jregex.compile('in(nen)?|r|e')
_INNEN_PATTERN1 = jregex.compile('in(nen)-[A-ZÖÄÜ][a-zöäüß-]+')
_ANYTHING_DASH = jregex.compile('.*-')
_INNEN_PATTERN2 = jregex.compile('innen[a-zöäüß-]+')
_DDD_ER_PATTERN = jregex.compile('\\d{4}+er')
_I_PATTERN = jregex.compile('.*i.+')  # word.matches(".*i.+")
_DOMAINS = frozenset(('com', 'net', 'org', 'de', 'at', 'ch', 'fr', 'uk', 'gov'))

# do not add noun tags to these words, e.g. don't add noun tags to "Wegstrecken" for weg_strecken from spelling.txt:
_NOUN_TAG_EXPANSION_EXCEPTIONS = frozenset(['Wegstrecken'])

# ordered by length: 'zurück' > 'zu' + 'rück'
_PREFIXES_SEPARABLE_VERBS = (
    "gegeneinander", "durcheinander", "nebeneinander", "übereinander", "aufeinander", "auseinander", "beieinander",
    "aneinander", "ineinander", "zueinander", "gegenüber", "beisammen", "gegenüber", "hernieder", "rückwärts",
    "wiederauf", "wiederein", "wiederher", "zufrieden", "zwangsvor", "entgegen", "hinunter", "abhanden", "aufrecht",
    "aufwärts", "auswärts", "beiseite", "danieder", "drauflos", "einwärts", "herunter", "hindurch", "verrückt",
    "vorwärts", "zunichte", "zusammen", "zwangsum", "zwischen", "abseits", "abwärts", "entlang", "hinfort", "ähnlich",
    "daneben", "general", "herüber", "hierher", "hierhin", "hinüber", "schwarz", "trocken", "überein", "vorlieb",
    "vorüber", "wichtig", "zurecht", "zuwider", "hinweg", "allein", "besser", "daheim", "doppel", "feinst", "fertig",
    "herauf", "heraus", "herbei", "hinauf", "hinaus", "hinein", "kaputt", "kennen", "kürzer", "mittag", "nieder",
    "runter", "sicher", "sitzen", "voraus", "vorbei", "vorweg", "weiter", "wieder", "zugute", "zurück", "zwangs",
    "abend", "blank", "brust", "dahin", "davon", "drauf", "drein", "durch", "einig", "empor", "grund", "herum",
    "höher", "klein", "knapp", "krank", "krumm", "kugel", "näher", "neben", "offen", "preis", "rüber", "ruhig",
    "statt", "still", "übrig", "umher", "unter", "voran", "zweck", "acht", "drei", "fehl", "feil", "fort", "frei",
    "groß", "hand", "hart", "heim", "hier", "hoch", "klar", "lahm", "miss", "nach", "nahe", "quer", "rauf", "raus",
    "rein", "rück", "satt", "stoß", "teil", "über", "voll", "wach", "wahr", "warm", "wert", "wohl", "auf", "aus",
    "bei", "ehe", "ein", "eis", "end", "her", "hin", "los", "maß", "mit", "out", "ran", "rum", "tot", "vor", "weg",
    "weh", "ab", "an", "da", "um", "zu")
_PREFIXES_SEPARABLE_VERBS_SET = frozenset(_PREFIXES_SEPARABLE_VERBS)
# Excludes "ge" (both too rare as verb prefix and prone to FP)
_PREFIXES_NON_SEPARABLE_VERBS = ("be", "emp", "ent", "er", "hinter", "miss", "un", "ver", "zer")
_PREFIXES_NON_SEPARABLE_VERBS_SET = frozenset(_PREFIXES_NON_SEPARABLE_VERBS)
_PREFIXES_NON_SEPARABLE_VERBS_REGEXP = jregex.compile("^(be|emp|ent|er|hinter|miss|un|ver|zer)")
_PREFIXES_VERBS = (
    "gegeneinander", "durcheinander", "nebeneinander", "übereinander", "aufeinander", "auseinander", "beieinander",
    "aneinander", "ineinander", "zueinander", "gegenüber", "beisammen", "gegenüber", "hernieder", "rückwärts",
    "wiederauf", "wiederein", "wiederher", "zufrieden", "zwangsvor", "entgegen", "hinunter", "abhanden", "aufrecht",
    "aufwärts", "auswärts", "beiseite", "danieder", "drauflos", "einwärts", "herunter", "hindurch", "verrückt",
    "vorwärts", "zunichte", "zusammen", "zwangsum", "zwischen", "abseits", "abwärts", "entlang", "hinfort", "ähnlich",
    "daneben", "general", "herüber", "hierher", "hierhin", "hinüber", "schwarz", "trocken", "überein", "vorlieb",
    "vorüber", "wichtig", "zurecht", "zuwider", "hinweg", "hinter", "allein", "besser", "daheim", "doppel", "feinst",
    "fertig", "herauf", "heraus", "herbei", "hinauf", "hinaus", "hinein", "kaputt", "kennen", "kürzer", "mittag",
    "nieder", "runter", "sicher", "sitzen", "voraus", "vorbei", "vorweg", "weiter", "wieder", "zugute", "zurück",
    "zwangs", "abend", "blank", "brust", "dahin", "davon", "drauf", "drein", "durch", "einig", "empor", "grund",
    "herum", "höher", "klein", "knapp", "krank", "krumm", "kugel", "näher", "neben", "offen", "preis", "rüber",
    "ruhig", "statt", "still", "übrig", "umher", "unter", "voran", "zweck", "miss", "acht", "drei", "fehl", "feil",
    "fort", "frei", "groß", "hand", "hart", "heim", "hier", "hoch", "klar", "lahm", "miss", "nach", "nahe", "quer",
    "rauf", "raus", "rein", "rück", "satt", "stoß", "teil", "über", "voll", "wach", "wahr", "warm", "wert", "wohl",
    "emp", "ent", "ver", "zer", "auf", "aus", "bei", "ehe", "ein", "eis", "end", "her", "hin", "los", "maß", "mit",
    "out", "ran", "rum", "tot", "vor", "weg", "weh", "be", "er", "un", "ab", "an", "da", "um", "zu")
_PREFIXES_VERBS_REGEXP = jregex.compile(
    "^(gegeneinander|durcheinander|nebeneinander|übereinander|aufeinander|auseinander|beieinander|aneinander|"
    "ineinander|zueinander|gegenüber|beisammen|gegenüber|hernieder|rückwärts|wiederauf|wiederein|wiederher|zufrieden|"
    "zwangsvor|entgegen|hinunter|abhanden|aufrecht|aufwärts|auswärts|beiseite|danieder|drauflos|einwärts|herunter|"
    "hindurch|verrückt|vorwärts|zunichte|zusammen|zwangsum|zwischen|abseits|abwärts|entlang|hinfort|ähnlich|daneben|"
    "general|herüber|hierher|hierhin|hinüber|schwarz|trocken|überein|vorlieb|vorüber|wichtig|zurecht|zuwider|hinweg|"
    "hinter|allein|besser|daheim|doppel|feinst|fertig|herauf|heraus|herbei|hinauf|hinaus|hinein|kaputt|kennen|kürzer|"
    "mittag|nieder|runter|sicher|sitzen|voraus|vorbei|vorweg|weiter|wieder|zugute|zurück|zwangs|abend|blank|brust|"
    "dahin|davon|drauf|drein|durch|einig|empor|grund|herum|höher|klein|knapp|krank|krumm|kugel|näher|neben|offen|"
    "preis|rüber|ruhig|statt|still|übrig|umher|unter|voran|zweck|miss|acht|drei|fehl|feil|fort|frei|groß|hand|hart|"
    "heim|hier|hoch|klar|lahm|miss|nach|nahe|quer|rauf|raus|rein|rück|satt|stoß|teil|über|voll|wach|wahr|warm|wert|"
    "wohl|emp|ent|ver|zer|auf|aus|bei|ehe|ein|eis|end|her|hin|los|maß|mit|not|out|ran|rum|tot|vor|weg|weh|be|er|un|"
    "ab|an|da|um|zu)")
_PARTIZIP2_CONTAINS_1_PLU_PRA = (
    "blasen", "fahren", "fallen", "fangen", "fressen", "geben", "halten", "kommen", "laden", "lassen", "laufen",
    "lesen", "messen", "raten", "schlafen", "schlagen", "sehen", "tragen", "treten")
_PARTIZIP2_CONTAINS_1_PLU_PRT = (
    "bieten", "bleiben", "fliegen", "fließen", "heben", "leiden", "meiden", "scheiden", "schließen", "schreiben",
    "stehen", "steigen", "streiten", "treiben", "weisen", "ziehen")
_POSTAGS_PARTIZIP = {
    'e': ("AKK:PLU:FEM:GRU:SOL:VER", "AKK:PLU:MAS:GRU:SOL:VER", "AKK:PLU:NEU:GRU:SOL:VER", "AKK:SIN:FEM:GRU:DEF:VER",
          "AKK:SIN:FEM:GRU:IND:VER", "AKK:SIN:FEM:GRU:SOL:VER", "AKK:SIN:NEU:GRU:DEF:VER", "NOM:PLU:FEM:GRU:SOL:VER",
          "NOM:PLU:MAS:GRU:SOL:VER", "NOM:PLU:NEU:GRU:SOL:VER", "NOM:SIN:FEM:GRU:DEF:VER", "NOM:SIN:FEM:GRU:IND:VER",
          "NOM:SIN:FEM:GRU:SOL:VER", "NOM:SIN:MAS:GRU:DEF:VER", "NOM:SIN:NEU:GRU:DEF:VER"),
    'em': ("DAT:SIN:MAS:GRU:SOL:VER", "DAT:SIN:NEU:GRU:SOL:VER"),
    'en': ("AKK:PLU:FEM:GRU:DEF:VER", "AKK:PLU:FEM:GRU:IND:VER", "AKK:PLU:MAS:GRU:DEF:VER", "AKK:PLU:MAS:GRU:IND:VER",
           "AKK:PLU:NEU:GRU:DEF:VER", "AKK:PLU:NEU:GRU:IND:VER", "AKK:SIN:MAS:GRU:DEF:VER", "AKK:SIN:MAS:GRU:IND:VER",
           "AKK:SIN:MAS:GRU:SOL:VER", "DAT:PLU:FEM:GRU:DEF:VER", "DAT:PLU:FEM:GRU:IND:VER", "DAT:PLU:FEM:GRU:SOL:VER",
           "DAT:PLU:MAS:GRU:DEF:VER", "DAT:PLU:MAS:GRU:IND:VER", "DAT:PLU:MAS:GRU:SOL:VER", "DAT:PLU:NEU:GRU:DEF:VER",
           "DAT:PLU:NEU:GRU:IND:VER", "DAT:PLU:NEU:GRU:SOL:VER", "DAT:SIN:FEM:GRU:DEF:VER", "DAT:SIN:FEM:GRU:IND:VER",
           "DAT:SIN:MAS:GRU:DEF:VER", "DAT:SIN:MAS:GRU:IND:VER", "DAT:SIN:NEU:GRU:DEF:VER", "DAT:SIN:NEU:GRU:IND:VER",
           "GEN:PLU:FEM:GRU:DEF:VER", "GEN:PLU:FEM:GRU:IND:VER", "GEN:PLU:MAS:GRU:DEF:VER", "GEN:PLU:MAS:GRU:IND:VER",
           "GEN:PLU:NEU:GRU:DEF:VER", "GEN:PLU:NEU:GRU:IND:VER", "GEN:SIN:FEM:GRU:DEF:VER", "GEN:SIN:FEM:GRU:IND:VER",
           "GEN:SIN:MAS:GRU:DEF:VER", "GEN:SIN:MAS:GRU:IND:VER", "GEN:SIN:MAS:GRU:SOL:VER", "GEN:SIN:NEU:GRU:DEF:VER",
           "GEN:SIN:NEU:GRU:IND:VER", "GEN:SIN:NEU:GRU:SOL:VER", "NOM:PLU:FEM:GRU:DEF:VER", "NOM:PLU:FEM:GRU:IND:VER",
           "NOM:PLU:MAS:GRU:DEF:VER", "NOM:PLU:MAS:GRU:IND:VER", "NOM:PLU:NEU:GRU:DEF:VER", "NOM:PLU:NEU:GRU:IND:VER"),
    'er': ("DAT:SIN:FEM:GRU:SOL:VER", "GEN:PLU:FEM:GRU:SOL:VER", "GEN:PLU:MAS:GRU:SOL:VER", "GEN:PLU:NEU:GRU:SOL:VER",
           "GEN:SIN:FEM:GRU:SOL:VER", "NOM:SIN:MAS:GRU:IND:VER", "NOM:SIN:MAS:GRU:SOL:VER", "DAT:SIN:FEM:GRU:SOL:VER",
           "GEN:PLU:FEM:GRU:SOL:VER", "GEN:PLU:MAS:GRU:SOL:VER", "GEN:PLU:NEU:GRU:SOL:VER", "GEN:SIN:FEM:GRU:SOL:VER",
           "NOM:SIN:MAS:GRU:IND:VER", "NOM:SIN:MAS:GRU:SOL:VER"),
    'es': ("AKK:SIN:NEU:GRU:IND:VER", "AKK:SIN:NEU:GRU:SOL:VER", "NOM:SIN:NEU:GRU:IND:VER", "NOM:SIN:NEU:GRU:SOL:VER"),
}
_PARTIZIP_SUFFIXES = ("e", "em", "en", "er", "es")
_NOT_A_VERB = (
    "angebot", "anteil", "aufenthalt", "ausdruck", "auswärtsspiel", "beispiel", "bereich", "besondere", "daring",
    "einfach", "einfachst", "endkasten", "freibetrag", "grautöne", "grüntöne", "großherzöge", "großteil", "hochhaus",
    "klarerweise", "maßnahme", "mitglieder", "nachricht", "nebenfach", "niederlage", "nothing", "notscheid",
    "preisver", "reinweiß", "schwarzweiß", "schwarzgrau", "schwarzgrün", "schwarztöne", "unbesiegt", "unmenge",
    "unrat", "unver", "verrückterweise", "versonnen", "vorlieb", "vorteil", "warmweiß", "wohldefiniert",
    "wohlergehen", "wohlgemerkt", "zuende", "zuhause", "zumal", "zuver", "darauf", "einmal", "kleinkram",
    "hochsicher", "ehering", "freitag", "großmeister", "handwerk", "herpes", "nachfolger")
_NOT_A_VERB_PATTERN = jregex.compile('|'.join(_NOT_A_VERB))  # StringUtils.containsAny(word, notAVerb)

# "kofferweise", "idealerweise" etc.
_TAGS_FOR_WEISE = (
    "ADJ:AKK:PLU:FEM:GRU:SOL", "ADJ:AKK:PLU:MAS:GRU:SOL", "ADJ:AKK:PLU:NEU:GRU:SOL", "ADJ:AKK:SIN:FEM:GRU:DEF",
    "ADJ:AKK:SIN:FEM:GRU:IND", "ADJ:AKK:SIN:FEM:GRU:SOL", "ADJ:AKK:SIN:NEU:GRU:DEF", "ADJ:NOM:PLU:FEM:GRU:SOL",
    "ADJ:NOM:PLU:MAS:GRU:SOL", "ADJ:NOM:PLU:NEU:GRU:SOL", "ADJ:NOM:SIN:FEM:GRU:DEF", "ADJ:NOM:SIN:FEM:GRU:IND",
    "ADJ:NOM:SIN:FEM:GRU:SOL", "ADJ:NOM:SIN:MAS:GRU:DEF", "ADJ:NOM:SIN:NEU:GRU:DEF", "ADJ:PRD:GRU")

_INTENSIFIER_PREFIXES = ("bitter", "dunkel", "erz", "extra", "früh", "gemein", "hyper", "lau", "mega", "minder",
                         "stock", "super", "tod", "ultra", "un", "ur")
_INTENSIFIER_REGEXP = jregex.compile(
    "^(bitter|dunkel|erz|extra|früh|gemein|grund|hyper|lau|mega|minder|stock|super|tod|ultra|u[nr]|voll)")
_FREIE = ("freie", "freier", "freien", "freies", "freiem")

# the first parts of compounds that are treated as separable verb prefixes
_PRFXS = frozenset((
    "ab", "abend", "abhanden", "acht", "ähnlich", "allein", "an", "auf", "aufeinander", "aufrecht", "aufwärts", "aus",
    "auseinander", "auswärts", "bei", "beieinander", "beisammen", "beiseite", "besser", "blank", "brust", "da",
    "daheim", "dahin", "daneben", "danieder", "davon", "doppel", "drauflos", "drei", "drein", "durch",
    "durcheinander", "ehe", "ein", "einig", "einwärts", "eis", "empor", "end", "fehl", "feil", "feinst", "fort",
    "frei", "gegenüber", "general", "groß", "grund", "hand", "hart", "heim", "her", "herauf", "heraus", "herbei",
    "hernieder", "herüber", "herum", "herunter", "hier", "hierher", "hierhin", "hin", "hinauf", "hinaus", "hindurch",
    "hinein", "hinüber", "hoch", "höher", "ineinander", "kaputt", "kennen", "klar", "klein", "knapp", "krank",
    "krumm", "kugel", "kürzer", "lahm", "los", "maß", "miss", "mit", "mittag", "nach", "nahe", "näher", "neben",
    "nebeneinander", "nieder", "offen", "out", "preis", "quer", "ran", "rauf", "raus", "rein", "rüber", "rück",
    "rückwärts", "ruhig", "rum", "runter", "satt", "schwarz", "sicher", "sitzen", "statt", "still", "stoß", "teil",
    "tot", "trocken", "über", "überein", "übereinander", "übrig", "um", "umher", "unter", "verrückt", "voll", "vor",
    "voran", "voraus", "vorbei", "vorlieb", "vorüber", "vorwärts", "vorweg", "wach", "wahr", "warm", "weg", "weh",
    "weiter", "wert", "wichtig", "wieder", "wiederauf", "wiederein", "wiederher", "wohl", "zu", "zueinander",
    "zufrieden", "zugute", "zunichte", "zurecht", "zurück", "zusammen", "zuwider", "zwangs", "zwangsum", "zwangsvor",
    "zweck", "zwischen"))

_IMPERATIVE_PREV_WORDS = ("ich", "er", "es", "sie", "bitte", "aber", "nun", "jetzt", "„")

_WT_CACHE_SIZE = 200000


# --- StringUtils helpers ---

def _is_ws(s):
    """StringUtils.isWhitespace (true for the empty string)"""
    for c in s:
        if not java_is_whitespace(c):
            return False
    return True


def _is_alphanumeric(s):
    """StringUtils.isAlphanumeric"""
    if not s:
        return False
    for c in s:
        if not is_letter_or_digit(c):
            return False
    return True


def _remove_end(s, remove):
    """StringUtils.removeEnd"""
    if s and remove and s.endswith(remove):
        return s[:len(s) - len(remove)]
    return s


def _cap_rest_lower(word):
    """word.substring(0, 1).toUpperCase() + word.substring(1).toLowerCase()"""
    return word[:1].upper() + word[1:].lower()


def _contains_any(s, subs):
    """StringUtils.containsAny(CharSequence, CharSequence...)"""
    for x in subs:
        if x in s:
            return True
    return False


def _readings_string(readings):
    """List<AnalyzedToken>.toString()"""
    return '[' + ', '.join('%s/%s' % (r.lemma_or_token, r.pos_tag) for r in readings) + ']'


# --- expansion infos from spelling.txt ---

class _PrefixInfixVerb:
    __slots__ = ('prefix', 'infix', 'verb_baseform')

    def __init__(self, prefix, infix, verb_baseform):
        self.prefix = prefix
        self.infix = infix
        self.verb_baseform = verb_baseform


class _ExpansionInfos:
    __slots__ = ('verb_infos', 'nominalized_verb_infos', 'nominalized_gen_verb_infos', 'adj_infos')

    def __init__(self, verb_infos, nominalized_verb_infos, nominalized_gen_verb_infos, adj_infos):
        self.verb_infos = verb_infos
        self.nominalized_verb_infos = nominalized_verb_infos
        self.nominalized_gen_verb_infos = nominalized_gen_verb_infos
        self.adj_infos = adj_infos


def _to_pa2(tags):
    return tuple(k.replace('ADJ:', 'PA2:') + ':VER' for k in tags)


def load_word_list(path):
    """CachingWordListLoader.loadWords(): the lines without comments
    (empty lines and lines starting with '#' are skipped, the rest is cut
    at '#' and trimmed)"""
    result = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            line = java_trim(line)
            i = line.find('#')
            if i >= 0:
                line = line[:i]
            result.append(java_trim(line))
    return result


def _fill_adj_infos(word, suffix, tags_for_form, adj_infos):
    # (Java: a list of AdjInfo(baseform, fullForm, tag) for the tags)
    adj_infos[word + suffix] = (word, tags_for_form)


def _init_expansion_infos(path, synthesizer):
    verb_infos = {}
    nominalized_verb_infos = {}
    nominalized_gen_verb_infos = {}
    adj_infos = {}
    filename = 'de/hunspell/spelling.txt'
    pa2 = [_to_pa2(t) for t in (AdjectiveTags.tags_for_adj, AdjectiveTags.tags_for_adj_e,
                                AdjectiveTags.tags_for_adj_en, AdjectiveTags.tags_for_adj_er,
                                AdjectiveTags.tags_for_adj_em, AdjectiveTags.tags_for_adj_es)]
    adj = [AdjectiveTags.tags_for_adj, AdjectiveTags.tags_for_adj_e, AdjectiveTags.tags_for_adj_en,
           AdjectiveTags.tags_for_adj_er, AdjectiveTags.tags_for_adj_em, AdjectiveTags.tags_for_adj_es]
    suffixes = ('', 'e', 'en', 'er', 'em', 'es')
    verb_forms = {}
    verb_tags = [t for t in synthesizer.get_possible_tags() if t.startswith('VER:')]

    for line in load_word_list(path):
        # '/A' adds the typical adjective endings, so assume it's an adjective:
        if line.endswith('/PA') or line.endswith('/AP'):
            raise ValueError("Use '/P' or '/A', but not both for a word in " + filename + ': ' + line)
        if line.endswith('/P'):
            word = line[:line.index('/')]
            for suffix, tags in zip(suffixes, pa2):
                _fill_adj_infos(word, suffix, tags, adj_infos)
        elif line.endswith('/A') and not line.endswith('ste/A') and not line.endswith('er/A'):
            # don't tag e.g. "fünftjünste/A", would miss the comparative tagging
            # don't tag e.g. "margenstärker/A", would miss the comparative tagging
            word = line[:line.index('/')]
            for suffix, tags in zip(suffixes, adj):
                _fill_adj_infos(word, suffix, tags, adj_infos)
        elif '_' in line and not line.endswith('_in'):
            parts = java_split(java_trim(line), '_')
            prefix = parts[0]
            verb_baseform = parts[1]
            forms = verb_forms.get(verb_baseform)
            if forms is None:
                # GermanSynthesizer.INSTANCE.synthesizeForPosTags(verbBaseform, s -> s.startsWith("VER:"))
                forms = verb_forms[verb_baseform] = synthesizer.synthesize_for_tag_list(verb_baseform, verb_tags)
            for form in forms:
                # skip these, it's too risky to introduce old spellings like "gewußt" from the synthesizer:
                if 'ß' not in form:
                    verb_infos[prefix + form] = _PrefixInfixVerb(prefix, '', verb_baseform)
            # "zu<verb>" is not part of forms from synthesizer
            verb_infos[prefix + 'zu' + verb_baseform] = _PrefixInfixVerb(prefix, 'zu', verb_baseform)
            uc_prefix = uppercase_first_char(prefix)
            nominalized_verb_infos[uc_prefix + verb_baseform] = (uc_prefix, verb_baseform)
            nominalized_gen_verb_infos[uc_prefix + verb_baseform + 's'] = (uc_prefix, verb_baseform)
    return _ExpansionInfos(verb_infos, nominalized_verb_infos, nominalized_gen_verb_infos, adj_infos)


_expansion_lock = threading.Lock()
_expansion_infos = {}


def _get_expansion_infos(path, synthesizer):
    infos = _expansion_infos.get(path)
    if infos is None:
        with _expansion_lock:
            infos = _expansion_infos.get(path)
            if infos is None:
                infos = _expansion_infos[path] = _init_expansion_infos(path, synthesizer)
    return infos


# --- GermanTagger ---

class GermanTagger(BaseTagger):
    """German part-of-speech tagger (de/german.dict). The POS tagset is
    described in tagset.txt."""

    def __init__(self, language):
        from ...dictionaries import locate
        spec = language.get('tagger') or {}
        super().__init__(language.dictionary(spec.get('dict', 'de/german.dict')), 'de', language.resource_dir, True)
        self.language = language
        self.removal_tagger = getattr(self.word_tagger, 'removal_tagger', None)
        self._spelling_path = locate('de/hunspell/spelling.txt', language.dictionary_path,
                                     language.download_dictionaries)
        self._wt_cache = {}
        self._compound_tokenizer = None

    # -- helpers --

    @property
    def expansion_infos(self):
        from .synthesis import get_german_synthesizer
        return _get_expansion_infos(self._spelling_path, get_german_synthesizer(self.language))

    def strict_compound_tokenizer(self):
        """GermanCompoundTokenizer.getStrictInstance()"""
        t = self._compound_tokenizer
        if t is None:
            from .compound_tokenizer import get_strict_instance
            t = self._compound_tokenizer = get_strict_instance(self.language.dictionary_path,
                                                               self.language.download_dictionaries)
        return t

    def _wt(self, word):
        """getWordTagger().tag(word) as a (cached) tuple of TaggedWord"""
        r = self._wt_cache.get(word)
        if r is None:
            r = tuple(self.word_tagger.tag(word))
            if len(self._wt_cache) > _WT_CACHE_SIZE:
                self._wt_cache.clear()
            self._wt_cache[word] = r
        return r

    def tag_word(self, word):
        """tag(String word): the TaggedWords of the word tagger (the
        dictionary with the manual additions and removals)"""
        return list(self._wt(word))

    def _add_stem(self, analyzed_word_results, stem):
        result = []
        for tw in analyzed_word_results:
            lemma = tw.lemma
            if stem and stem[-1] != '-' and tw.pos_tag.startswith('SUB'):
                lemma = lemma.lower()
            result.append(TaggedWord(stem + lemma, tw.pos_tag))
        return result

    def _sanitize_word(self, word):
        """Removes the irrelevant part of dash-linked words (SSL-Zertifikat -> Zertifikat)"""
        result = word
        # Find the last part of the word that is not nothing
        # Skip words ending in a dash as they'll be misrecognized
        if not word.endswith('-'):
            split_word = java_split(word, '-')
            last_part = split_word[-1] if len(split_word) > 1 and java_trim(split_word[-1]) != '' else word
            # Find only the actual important part of the word
            compounded_word = self.strict_compound_tokenizer().tokenize(last_part)
            if len(compounded_word) > 1 and starts_with_uppercase(word):
                # don't uppercase last part of e.g. "vanillig-karamelligen"
                last_part = uppercase_first_char(compounded_word[-1])
            else:
                last_part = compounded_word[-1]
            # Only give result if the last part is either a noun or an adjective (or adjective written in Uppercase)
            tagged = self._wt(last_part)
            if tagged and ((tagged[0].pos_tag is not None and tagged[0].pos_tag.startswith(('SUB', 'ADJ')))
                           or self._matches_uppercase_adjective(last_part)):
                result = last_part
        return result

    def lookup(self, word):
        """Return only the first reading of the given word (an
        AnalyzedTokenReadings) or None."""
        atr = self.tag([word], False)[0]
        if atr.readings[0].pos_tag is None:
            return None
        return atr

    def _matches_uppercase_adjective(self, unknown_uppercase_token):
        temp = self._wt(lowercase_first_char(unknown_uppercase_token))
        return len(temp) > 0 and temp[0].pos_tag is not None and temp[0].pos_tag.startswith('ADJ')

    # -- tagging --

    def get_analyzed_tokens(self, word):
        return self.tag([word])[0].readings

    def tag(self, sentence_tokens, ignore_case=True):
        first_word = True
        token_readings = []
        pos = 0
        idx_pos = 0
        n_tokens = len(sentence_tokens)
        first_index = {}
        for i, t in enumerate(sentence_tokens):
            first_index.setdefault(t, i)
        wt = self._wt
        prev_word = None
        for word in sentence_tokens:
            readings = []
            tagger_tokens = None
            # Gender star etc:
            if idx_pos + 2 < n_tokens and _GENDER_GAP_CHARS.fullmatch(sentence_tokens[idx_pos + 1]):
                after = sentence_tokens[idx_pos + 2]
                if _AFTER_ASTERISK.fullmatch(after):  # "jede*r", "sein*e"
                    tagger_tokens = list(wt(word))
                    tagger_tokens.extend(wt(word + after))
                elif _INNEN_PATTERN1.fullmatch(after):
                    # e.g. Werkstudent:innen-Zielgruppe -> take tags of 'Zielgruppe':
                    last_part = _ANYTHING_DASH.sub('', after, count=1)
                    tagger_tokens = list(wt(last_part))
                elif _INNEN_PATTERN2.fullmatch(after):
                    # e.g. Werkstudent:innenzielgruppe -> take tags of 'Zielgruppe':
                    idx = after.rfind('innen')
                    last_part = uppercase_first_char(after[idx + len('innen'):])
                    tagger_tokens = list(wt(last_part))
            if tagger_tokens is None:
                tagger_tokens = list(wt(word))

            # Only first iteration. Consider ":" as a potential sentence start marker
            if (first_word or prev_word == ':') and not tagger_tokens and ignore_case:
                # e.g. "Das" -> "das" at start of sentence
                tagger_tokens = list(wt(word.lower()))
                first_word = not _is_alphanumeric(word)
            elif pos == 0 and ignore_case:  # "Haben", "Sollen", "Können", "Gerade" etc. at start of sentence
                tagger_tokens.extend(wt(word.lower()))
            elif pos > 1 and not tagger_tokens and ignore_case:
                idx = first_index[word]
                # add lowercase token readings to words at start of direct speech
                if idx > 2 and sentence_tokens[idx - 1] == '„' and sentence_tokens[idx - 3] == ':':
                    tagger_tokens.extend(wt(word.lower()))

            if tagger_tokens:  # Word known, just add analyzed token to readings
                readings.extend(self._get_analyzed_tokens(tagger_tokens, word))
                self._add_imperative_sft_readings(word, readings, first_index)
            else:  # Word not known, try to decompose it and use the last part for POS tagging:
                self._tag_unknown(word, readings, sentence_tokens, first_index, pos, idx_pos)
                if not readings:
                    readings.append(AnalyzedToken(word, None, None))
            token_readings.append(AnalyzedTokenReadings(readings, pos))
            pos += len(word)
            prev_word = word
            idx_pos += 1
        return token_readings

    def _add_imperative_sft_readings(self, word, readings, first_index):
        """For non separable verbs with prefix and for verbs without any prefix:
        if (base) verb has tag 'VER:IMP:SIN:SFT', then add 'VER:1:SIN:PRÄ:SFT',
        if (base) verb has tag 'VER:1:SIN:PRÄ:SFT', then add 'VER:IMP:SIN:SFT'.
        'NON' is excluded, because for a given lemma 'VER:IMP:SIN:NON' and 'VER:1:SIN:PRÄ:NON' can differ,
        e. g. (ver)nimm is 'VER:IMP:SIN:NON', but (ver)nehm is 'VER:1:SIN:PRÄ:NON'"""
        lower = word.lower()
        if lower.startswith(_PREFIXES_SEPARABLE_VERBS) or lower.startswith(_NOT_A_VERB):
            return
        if not (word == _cap_rest_lower(word) or word == lower):
            return
        if lower.startswith(_PREFIXES_NON_SEPARABLE_VERBS):
            lst_prt = _PREFIXES_NON_SEPARABLE_VERBS_REGEXP.sub('', lower)
            frst_prt = _remove_end(word, lst_prt)
        else:
            lst_prt = word
            frst_prt = ''
        verbs = self._wt(lst_prt)
        if not verbs:
            return
        if not ((first_index[word] == 0 or word == word[:1].lower() + word[1:])
                and lst_prt not in ('gar', 'mal', 'null', 'trotz')):
            return
        for v in verbs:
            tag = v.pos_tag
            if tag is None:
                continue
            if tag.startswith('VER:IMP:SIN:SFT') and 'VER:1:SIN:PRÄ:SFT' not in _readings_string(readings):
                readings.append(AnalyzedToken(word, 'VER:1:SIN:PRÄ:SFT', frst_prt.lower() + v.lemma))
            if tag.startswith('VER:1:SIN:PRÄ:SFT') and 'VER:IMP:SIN:SFT' not in _readings_string(readings):
                readings.append(AnalyzedToken(word, 'VER:IMP:SIN:SFT', frst_prt.lower() + v.lemma))

    def _tag_unknown(self, word, readings, sentence_tokens, first_index, pos, idx_pos):
        wt = self._wt
        infos = self.expansion_infos
        verb_info = infos.verb_infos.get(word)
        nom_verb_info = infos.nominalized_verb_infos.get(word)
        nom_gen_verb_info = infos.nominalized_gen_verb_infos.get(word)
        adj_infos = infos.adj_infos.get(word)
        add_noun_tags = word not in _NOUN_TAG_EXPANSION_EXCEPTIONS
        if verb_info is not None:  # e.g. "herumgeben" with "herum_geben" in spelling.txt
            if starts_with_lowercase(verb_info.prefix):
                self._tag_prefix_infix_verb(word, verb_info, readings, first_index)
        elif nom_verb_info is not None and add_noun_tags:
            # e.g. "herum_geben" in spelling.txt -> "(das) Herumgeben"
            lemma = nom_verb_info[0] + nom_verb_info[1]
            readings.append(AnalyzedToken(word, 'SUB:NOM:SIN:NEU:INF', lemma))
            readings.append(AnalyzedToken(word, 'SUB:AKK:SIN:NEU:INF', lemma))
            readings.append(AnalyzedToken(word, 'SUB:DAT:SIN:NEU:INF', lemma))
        elif nom_gen_verb_info is not None and add_noun_tags:
            # e.g. "herum_geben" in spelling.txt -> "(des) Herumgebens"
            readings.append(AnalyzedToken(word, 'SUB:GEN:SIN:NEU:INF', nom_gen_verb_info[0] + nom_gen_verb_info[1]))
        elif adj_infos is not None:
            baseform, tags = adj_infos
            for tag in tags:
                readings.append(AnalyzedToken(word, tag, baseform))
        elif self.is_weise_exception(word):  # "idealerweise" etc. but not "überweise", "eimerweise"
            for tag in _TAGS_FOR_WEISE:
                readings.append(AnalyzedToken(word, tag, word))
        elif not _is_ws(word) and _MITARBEITENDEN_PATTERN.fullmatch(word):
            idx = word.find('mitarbeitende')
            first_part = word[:idx]  # we might tag invalid words, but that should be okay
            last_part = word[idx:]
            for mt in wt(uppercase_first_char(last_part)):
                readings.append(AnalyzedToken(word, mt.pos_tag, first_part + 'mitarbeitende'))
        elif not _is_ws(word):
            compound_parts = self.strict_compound_tokenizer().tokenize(word)
            if len(compound_parts) <= 1:  # Could not find simple compound parts
                self._tag_non_compound(word, readings, sentence_tokens, first_index, pos)
            elif not (idx_pos + 2 < len(sentence_tokens) and sentence_tokens[idx_pos + 1] == '.'
                      and sentence_tokens[idx_pos + 2] in _DOMAINS):  # TODO: find better way to ignore domains
                self._tag_compound(word, compound_parts, readings, first_index)

    def _tag_prefix_infix_verb(self, word, verb_info, readings, first_index):
        no_prefix_form = word[len(verb_info.prefix) + len(verb_info.infix):]  # infix can be "zu"
        tags = self._wt(no_prefix_form)
        is_sft = False  # SFT = schwaches Verb
        prefix = verb_info.prefix
        for tag in tags:
            pt = tag.pos_tag
            if pt is not None and pt.startswith(('VER:', 'PA1:', 'PA2:')) \
                    and not pt.startswith(('VER:MOD', 'VER:AUX')):  # e.g. "schicke" is verb and adjective
                flektion = pt[len(pt) - 3:]
                if prefix.startswith(_PREFIXES_SEPARABLE_VERBS) and not _NOT_A_VERB_PATTERN.search(word):
                    if pt.startswith(('VER:1', 'VER:2', 'VER:3')) and (
                            first_index[word] == 0 or word == word[:1].lower() + word[1:]):
                        readings.append(AnalyzedToken(word, pt + ':NEB', prefix + tag.lemma))
                    elif not pt.startswith('VER:IMP'):
                        readings.append(AnalyzedToken(word, pt, prefix + tag.lemma))
                    elif pt.startswith('VER:IMP:SIN'):
                        # (Java: !readings.contains("VER:1:SIN:PRÄ") is always true)
                        if flektion == 'SFT' or not _I_PATTERN.fullmatch(word):  # Avoids 'aufnimm'
                            readings.append(AnalyzedToken(word, 'VER:1:SIN:PRÄ:' + flektion + ':NEB',
                                                          prefix + tag.lemma))
                elif prefix.startswith(_PREFIXES_NON_SEPARABLE_VERBS) and not _NOT_A_VERB_PATTERN.search(word):
                    # Excludes "ge" (both too rare as verb prefix and prone to FP)
                    if pt.startswith('VER:IMP:SIN') or pt.startswith('VER:1:SIN:PRÄ'):
                        if flektion == 'SFT' or not _I_PATTERN.fullmatch(word):  # Avoids 'zernimm'
                            readings.append(AnalyzedToken(word, 'VER:IMP:SIN' + flektion, prefix + tag.lemma))
                            readings.append(AnalyzedToken(word, 'VER:1:SIN:PRÄ:' + flektion, prefix + tag.lemma))
                    else:
                        readings.append(AnalyzedToken(word, pt, prefix + tag.lemma))
                if ':SFT' in pt:
                    is_sft = True
        if verb_info.infix == 'zu':
            del readings[:]
            readings.append(AnalyzedToken(word, 'VER:EIZ:' + ('SFT' if is_sft else 'NON'),
                                          prefix + verb_info.verb_baseform))

    def _tag_non_compound(self, word, readings, sentence_tokens, first_index, pos):
        wt = self._wt
        # Recognize alternative imperative forms (e.g., "Geh bitte!" in addition to "Gehe bitte!")
        imperative_form_list = self._get_imperative_form(word, sentence_tokens, first_index, pos)
        if imperative_form_list:
            readings.extend(imperative_form_list)
            return
        substantivated_forms_list = self._get_substantivated_forms(word, sentence_tokens, first_index)
        if substantivated_forms_list:
            readings.extend(substantivated_forms_list)
            return
        if word.startswith(_INTENSIFIER_PREFIXES):
            last_part = _INTENSIFIER_REGEXP.sub('', word)
            if len(last_part) > 3:
                first_part = _remove_end(word, last_part)
                for tagged_word in wt(last_part):
                    if not (len(first_part) == 2 and tagged_word.pos_tag.startswith('VER')):
                        readings.append(AnalyzedToken(word, tagged_word.pos_tag, first_part + tagged_word.lemma))
        # Separate dash-linked words
        # Only check single word tokens and skip words containing numbers because it's unpredictable
        if len([p for p in word.split(' ') if p]) == 1 and not is_digit(word[0]):
            word_orig = word
            word = self._sanitize_word(word)
            word_stem = word_orig[:len(word_orig) - len(word)]
            # Tokenize, start word uppercase if it's a result of splitting
            compounded_word = self.strict_compound_tokenizer().tokenize(word)
            if len(compounded_word) > 1:
                word = uppercase_first_char(compounded_word[-1])
            else:
                word = compounded_word[-1]
            linked_tagger_tokens = self._add_stem(wt(word), word_stem)  # Try to analyze the last part found
            # Some words that are linked with a dash ('-') will be written in uppercase, even adjectives
            if '-' in word_orig and not linked_tagger_tokens and self._matches_uppercase_adjective(word):
                word = lowercase_first_char(word)
                linked_tagger_tokens = list(wt(word))
            word = word_orig
            word_starts_uppercase = starts_with_uppercase(word)
            if not linked_tagger_tokens:
                self._tag_verb_with_prefix(word, readings, first_index)
            elif word_starts_uppercase:  # Choose between uppercase/lowercase Lemma
                readings.extend(self._get_analyzed_tokens(linked_tagger_tokens, word))
            else:
                readings.extend(self._get_analyzed_compound_tokens(linked_tagger_tokens, word, compounded_word))
        else:
            readings.append(AnalyzedToken(word, None, None))

    def _tag_verb_with_prefix(self, word, readings, first_index):
        """Verbs with certain prefixes (e. g. "ab", "ein", "zwischen") are always separable.
        For better performance of rules, forms like 'einlädst' and 'lädst ein' should be tagged differently:
        einlädst [VER:2:SIN:PRÄ:NON:NEB] ('NEB' indicates that this form can only appear in a subordinate clause),
        lädst ein [VER:2:SIN:PRÄ:NON] + [ZUS]"""
        wt = self._wt
        lower = word.lower()
        if not (lower.startswith(_PREFIXES_VERBS) and not _NOT_A_VERB_PATTERN.search(lower)
                and (word == _cap_rest_lower(word) or word == lower)):  # avoids CamelCase, ALLCAPS...
            readings.append(AnalyzedToken(word, None, None))
            return
        last_part = _PREFIXES_VERBS_REGEXP.sub('', lower)
        if len(last_part) <= 2:  # e. g. 'kau', 'iss', 'ess'
            return
        first_part = _remove_end(word, last_part)
        first_lower = first_part.lower()
        is_lower_or_first = word == lower or first_index[word] == 0
        # Erweiterter Infinitiv mit zu
        if last_part.startswith('zu'):
            infinitiv = last_part[2:]
            for inf in wt(infinitiv):
                if inf.pos_tag.startswith('VER:INF'):
                    pstg = inf.pos_tag.replace('INF', 'EIZ', 1)
                    readings.append(AnalyzedToken(word, pstg, first_part + inf.lemma))
        # Checks for postag information in the last part of given word
        for tagged_word in wt(last_part):
            pt = tagged_word.pos_tag
            lemma = tagged_word.lemma
            if (pt.startswith('VER') and not pt.startswith('VER:PA')) and not pt.startswith('VER:AUX') \
                    and not pt.startswith('VER:MOD') and first_part != 'un':  # avoids 'unbeeindruckt' -> VER.*
                if pt.startswith('VER:INF'):
                    if word == word[:1].upper() + word[1:]:
                        readings.append(AnalyzedToken(word, 'SUB:NOM:SIN:NEU:INF', word))
                        readings.append(AnalyzedToken(word, 'SUB:DAT:SIN:NEU:INF', word))
                        readings.append(AnalyzedToken(word, 'SUB:AKK:SIN:NEU:INF', word))
                        if first_index[word] == 0:
                            readings.append(AnalyzedToken(word, pt, first_lower + lemma))
                    else:
                        readings.append(AnalyzedToken(word, pt, first_lower + lemma))
                elif pt.startswith('VER:IMP'):
                    flekt = pt[len(pt) - 3:]
                    if is_lower_or_first:
                        # Separable verbs do not have imperative form.
                        if first_lower not in _PREFIXES_SEPARABLE_VERBS_SET:
                            readings.append(AnalyzedToken(word, pt, first_lower + lemma))
                            # (Java: !readings.contains(...) on the token list is always true)
                            if pt.startswith('VER:IMP:SIN'):
                                readings.append(AnalyzedToken(word, 'VER:1:SIN:PRÄ:' + flekt, first_part + lemma))
                        elif flekt == 'SFT' or not _I_PATTERN.fullmatch(word):
                            readings.append(AnalyzedToken(word, 'VER:1:SIN:PRÄ:' + flekt + ':NEB', first_part + lemma))
                elif first_lower in _PREFIXES_SEPARABLE_VERBS_SET and is_lower_or_first:
                    if pt.endswith(':NEB'):
                        readings.append(AnalyzedToken(word, pt, first_lower + lemma))
                    else:
                        readings.append(AnalyzedToken(word, pt + ':NEB', first_lower + lemma))
                    if pt.startswith('VER:3:SIN:PRÄ') and (first_part == 'durch' or first_part == 'um'):
                        # Verbs with prefixes 'durch' or 'um' can be both separable and non separable
                        # 'Tom läuft durch den Wald', 'Tom durchläuft eine Durststrecke'. This avoids false alarms
                        readings.append(AnalyzedToken(word, 'VER:PA2:SFT', first_part + lemma))
                        readings.append(AnalyzedToken(word, 'PA2:PRD:GRU:VER', word))
                elif first_lower in _PREFIXES_NON_SEPARABLE_VERBS_SET and is_lower_or_first:
                    readings.append(AnalyzedToken(word, pt, first_lower + lemma))
                    # Postag of 'lastPart' never starts with PA2: erstickt = er + stickt
                    # Derives 'VER:PA2:SFT' and 'PA2:PRD:GRU:VER', if postag of 'lastPart' equals 'VER:3:SIN:PRÄ:SFT'
                    # Using other postags is not safe, especially 'VER.*NON'
                    if pt.startswith('VER:3:SIN:PRÄ:SFT') \
                            or (pt.startswith('VER:1:PLU:PRÄ:NON')
                                and _contains_any(lemma, _PARTIZIP2_CONTAINS_1_PLU_PRA)) \
                            or (pt.startswith('VER:1:PLU:PRT:NON')
                                and _contains_any(lemma, _PARTIZIP2_CONTAINS_1_PLU_PRT)):
                        if first_part != 'un':  # Avoids 'unbeeindruckt' -> 'VER.*'
                            fl = pt[len(pt) - 3:]
                            readings.append(AnalyzedToken(word, 'VER:PA2:' + fl, first_part + lemma))
                        readings.append(AnalyzedToken(word, 'PA2:PRD:GRU:VER', word))
            elif (pt.startswith('PA') or pt.startswith('VER:PA')) and is_lower_or_first:
                if not (first_part == 'un' and pt.startswith('VER:PA')):
                    readings.append(AnalyzedToken(word, pt, first_lower + lemma))
        # Postag of 'lastPart' never starts with PA2: erstickter = er + stickter
        # Derives 'PA2:[NGDA].*', if word has suffix 'e[mnrs]?' and 'middlePart' has tagging 'VER:3:SIN:PRÄ:SFT'
        # e. g. erstickter = er + stickt + er
        middle_part = ''
        suffix = ''
        for sffx in _PARTIZIP_SUFFIXES:
            if last_part.endswith(sffx):
                middle_part = last_part[:len(last_part) - len(sffx)]
                suffix = sffx
        for tagged_m in wt(middle_part):
            if tagged_m.pos_tag.startswith('VER:3:SIN:PRÄ:SFT') and is_lower_or_first:
                lemma = word[:len(word) - len(suffix)]
                for p in _POSTAGS_PARTIZIP.get(suffix, ()):
                    readings.append(AnalyzedToken(word, 'PA2:' + p, lemma))

    def _tag_compound(self, word, compound_parts, readings, first_index):
        # last part governs a word's POS:
        last_part = compound_parts[-1]
        if starts_with_uppercase(word) and not _contains_any(last_part, _FREIE):
            last_part = uppercase_first_char(last_part)
        part_tagger_tokens = self._wt(last_part)
        if not part_tagger_tokens:
            readings.append(AnalyzedToken(word, None, None))
            return
        first_part = compound_parts[0]
        if first_part in _PRFXS:
            for tag in part_tagger_tokens:
                pt = tag.pos_tag
                if pt.startswith(('VER:1', 'VER:2', 'VER:3')) and (
                        first_index[word] == 0 or word == word[:1].lower() + word[1:]):
                    if pt.endswith('NEB'):
                        readings.append(AnalyzedToken(word, pt, first_part + tag.lemma))
                    else:
                        readings.append(AnalyzedToken(word, pt + ':NEB', first_part + tag.lemma))
                elif not pt.startswith('VER:IMP'):
                    readings.append(AnalyzedToken(word, pt, first_part + tag.lemma))
        else:
            temp = self._get_analyzed_compound_tokens(part_tagger_tokens, word, compound_parts)
            readings.extend(k for k in temp if 'VER' not in k.pos_tag)

    def prefixed_verb_last_part(self, word):
        """prefixedVerbLastPart(): the part of "aufstöhnen" etc. after a verb
        prefix (VerbPrefixes) if it is a verb, else None (not used by the
        tagger, see https://github.com/languagetool-org/languagetool/issues/2740)"""
        for prefix in VerbPrefixes.get():
            if word.startswith(prefix):
                tags = self._wt(word[len(prefix):])
                if any(k.pos_tag is not None and k.pos_tag.startswith('VER') for k in tags):
                    return word[len(prefix):]
        return None

    def is_weise_exception(self, word):
        if word.endswith('erweise'):  # "idealerweise" etc.
            tags = self._wt(word[:len(word) - len('erweise')])
            return any(k.pos_tag is not None and k.pos_tag.startswith('ADJ') for k in tags)
        return False

    def _get_imperative_form(self, word, sentence_tokens, first_index, pos):
        """Tag alternative imperative forms (e.g., "Geh bitte!" in addition to "Gehe bitte!").
        To avoid false positives and conflicts with DE_CASE the tagging is restricted to
        [a] words at the start of a sentence ("Geh bitte!") if the sentence counts more than one word,
        [b1] words preceded by ich/ihr/er/es/sie to catch some real errors ("Er geh jetzt.") by the new rule in
        rulegroup SUBJECT_VERB_AGREEMENT,
        [b2] words preceded by aber/nun/jetzt (e.g., "Bitte geh!", "Jetzt sag schon!" etc.)"""
        idx = first_index[word]
        previous_word = ''
        idx -= 1
        while idx > -1:
            previous_word = sentence_tokens[idx]
            if not _is_ws(previous_word):
                break
            idx -= 1
        if not (pos == 0 and len(sentence_tokens) > 1) \
                and not any(java_equals_ignore_case(previous_word, w) for w in _IMPERATIVE_PREV_WORDS):
            return []
        w = word.lower() if pos == 0 or previous_word == '„' else word
        for tagged in self._wt(w + 'e'):
            if tagged.pos_tag.startswith('VER:IMP:SIN'):
                # do not overwrite manually removed tags
                if self.removal_tagger is None or tagged not in self.removal_tagger.tag(w):
                    return self._get_analyzed_tokens([tagged], word)
                break
        return []

    def _get_substantivated_forms(self, word, sentence_tokens, first_index):
        """Tag substantivated adjectives and participles, which are currently tagged not tagged correctly
        (e.g., "Verletzter" in "Ein Verletzter kam ins Krankenhaus" needs to be tagged as "SUB:NOM:SIN:MAS")"""
        if word.endswith('er'):
            if _DDD_ER_PATTERN.fullmatch(word):
                # e.g. "Den 2019er Wert hatten sie geschätzt"
                return [AnalyzedToken(word, tag, word) for tag in _ALL_ADJ_GRU_TAGS]
            lower_case_tags = self._wt(word.lower())
            # do not add tag words whose lower case variant is an adverb (e.g, "Früher") to avoid false negatives
            # for DE_CASE
            if any(t.pos_tag.startswith('ADV') for t in lower_case_tags):
                return []
            idx = first_index[word]
            # is followed by an uppercase word? If 'yes', the word is probably not substantivated
            idx += 1
            while idx < len(sentence_tokens):
                next_word = sentence_tokens[idx]
                if _is_ws(next_word):
                    idx += 1
                    continue
                if next_word and (is_upper_case(next_word[0]) or next_word == 'als'):
                    return []
                break
            female_form = word[:-1]
            if any(t.pos_tag == 'SUB:NOM:SIN:FEM:ADJ' for t in self._wt(female_form)):
                return [AnalyzedToken(word, 'SUB:NOM:SIN:MAS:ADJ', word),
                        AnalyzedToken(word, 'SUB:GEN:PLU:MAS:ADJ', word)]
        return []

    @staticmethod
    def _get_analyzed_tokens(tagged_words, word):
        return [AnalyzedToken(word, tw.pos_tag, tw.lemma) for tw in tagged_words]

    @staticmethod
    def _get_analyzed_compound_tokens(tagged_words, word, compound_parts):
        result = []
        all_but_last = compound_parts[:-1]
        prefix = ''.join(s if i == 0 else lowercase_first_char(s) for i, s in enumerate(all_but_last))
        for tw in tagged_words:
            if tw.pos_tag is not None and tw.pos_tag.startswith('VER:IMP'):
                # ignore imperative, as otherwise e.g. "zehnfach" will be interpreted as a verb (zehn + fach)
                continue
            result.append(AnalyzedToken(word, tw.pos_tag, prefix + lowercase_first_char(tw.lemma)))
        return result


class SwissGermanTagger(GermanTagger):
    """SwissGermanTagger: the GermanTagger, untagged words containing "ss"
    get the readings of the word with "ß" instead of "ss"."""

    def tag(self, sentence_tokens, ignore_case=True):
        tokens = super().tag(sentence_tokens, ignore_case)
        for reading in tokens:
            if reading is not None and reading.token is not None and 'ss' in reading.token \
                    and not reading.is_tagged():
                replacement_reading = self.lookup(reading.token.replace('ss', 'ß'))
                if replacement_reading is not None:
                    for at in replacement_reading.readings:
                        reading.add_reading(AnalyzedToken(reading.token, at.pos_tag, at.lemma), 'SwissGermanTagger')
        return tokens


# --- instances ---

_lock = threading.Lock()
_instance = None


def get_german_tagger(language=None):
    """GermanTagger.INSTANCE: the shared GermanTagger (created with the
    resources of the given language, by default de-DE, on first use)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                if language is None:
                    from ...api import get_language
                    language = get_language('de-DE')
                _instance = GermanTagger(language)
    return _instance


def tagger_factory(language, spec):
    """The 'tagger' factory for 'GermanTagger': German.createDefaultTagger()
    returns GermanTagger.INSTANCE"""
    return get_german_tagger(language)


def swiss_tagger_factory(language, spec):
    """The 'tagger' factory for 'SwissGermanTagger' (a new instance, as
    SwissGerman.createDefaultTagger())"""
    return SwissGermanTagger(language)
