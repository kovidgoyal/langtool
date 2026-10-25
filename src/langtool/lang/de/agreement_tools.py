"""Port of org.languagetool.rules.de.AgreementTools (and the GrammarCategory
enum of AgreementRule): the agreement categories (case, number, gender,
determination) of a token's readings."""

from .german_token import AnalyzedGermanToken, Determination, Genus


class GrammarCategory:
    """AgreementRule.GrammarCategory"""
    __slots__ = ('name', 'display_name')

    def __init__(self, name, display_name):
        self.name = name
        self.display_name = display_name

    def __repr__(self):
        return self.name


GrammarCategory.KASUS = GrammarCategory(
    'KASUS', "Kasus (Fall: Wer/Was, Wessen, Wem, Wen/Was - Beispiel: 'das Fahrrads' statt 'des Fahrrads')")
GrammarCategory.GENUS = GrammarCategory(
    'GENUS', "Genus (männlich, weiblich, sächlich - Beispiel: 'der Fahrrad' statt 'das Fahrrad')")
GrammarCategory.NUMERUS = GrammarCategory(
    'NUMERUS', "Numerus (Einzahl, Mehrzahl - Beispiel: 'das Fahrräder' statt 'die Fahrräder')")

_DEF = Determination.DEFINITE
_IND = Determination.INDEFINITE
_MAS_FEM_NEU = (Genus.MASKULINUM, Genus.FEMININUM, Genus.NEUTRUM)


def get_agreement_categories(a_token, omit=frozenset(), skip_sol=False):
    """AgreementTools.getAgreementCategories: Kasus, Numerus, Genus of those
    forms with a determiner (a set of strings like
    'Nominativ/Singular/Maskulinum/definit')."""
    result = set()
    for tmp_reading in a_token.readings:
        pos_tag = tmp_reading.pos_tag
        if skip_sol and pos_tag is not None and pos_tag.endswith(':SOL'):
            # SOL = alleinstehend - needs to be skipped so we find errors like "An der roter Ampel."
            continue
        reading = AnalyzedGermanToken(tmp_reading)
        casus, numerus, genus, determination = reading.casus, reading.numerus, reading.genus, reading.determination
        if casus is None and numerus is None and genus is None:
            continue
        if genus is Genus.ALLGEMEIN and pos_tag is not None and not pos_tag.endswith(':STV') and \
                not _possessive_special_case(a_token, tmp_reading):  # STV: stellvertretend (!= begleitend)
            # genus=ALG in the original data. Not sure if this is allowed, but expand this so
            # e.g. "Ich Arbeiter" doesn't get flagged as incorrect:
            if determination is None:
                # Nouns don't have the determination property (definite/indefinite), and as we don't want to
                # introduce a special case for that, we just pretend they always fulfill both properties:
                for g in _MAS_FEM_NEU:
                    result.add(_make_string(casus, numerus, g, _DEF, omit))
                    result.add(_make_string(casus, numerus, g, _IND, omit))
            else:
                for g in _MAS_FEM_NEU:
                    result.add(_make_string(casus, numerus, g, determination, omit))
        else:
            if determination is None or tmp_reading.lemma in ('jed', 'manch'):
                # "jeder" etc. needs a special case to avoid false alarm
                result.add(_make_string(casus, numerus, genus, _DEF, omit))
                result.add(_make_string(casus, numerus, genus, _IND, omit))
            else:
                result.add(_make_string(casus, numerus, genus, determination, omit))
    return result


def get_agreement_sol_categories(a_token, omit=frozenset()):
    """AgreementTools.getAgreementSOLCategories"""
    result = set()
    for tmp_reading in a_token.readings:
        if tmp_reading.pos_tag is not None and not tmp_reading.pos_tag.endswith(':SOL'):
            continue
        reading = AnalyzedGermanToken(tmp_reading)
        if reading.casus is None and reading.numerus is None and reading.genus is None:
            continue
        result.add(_make_string(reading.casus, reading.numerus, reading.genus, _DEF, omit))
        result.add(_make_string(reading.casus, reading.numerus, reading.genus, _IND, omit))
    return result


def _possessive_special_case(a_token, tmp_reading):
    # would cause error misses as it contains 'ALG', e.g. in "Der Zustand meiner Gehirns."
    return a_token.has_pos_tag_starting_with('PRO:POS') and tmp_reading.lemma in ('ich', 'sich')


def _make_string(casus, num, gen, determination, omit):
    parts = []
    if casus is not None and GrammarCategory.KASUS not in omit:
        parts.append(casus.name)
    if num is not None and GrammarCategory.NUMERUS not in omit:
        parts.append(num.name)
    if gen is not None and GrammarCategory.GENUS not in omit:
        parts.append(gen.name)
    if determination is not None:
        parts.append(determination.name)
    return '/'.join(parts)
