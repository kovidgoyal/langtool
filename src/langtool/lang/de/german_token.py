"""Port of org.languagetool.tagging.de.GermanToken and
AnalyzedGermanToken: the parts of a German POS tag (word class, case,
number, gender, determination) of one reading."""


class _Value:
    """A constant of the GermanToken classes (POSType, Kasus, ...): compared
    by identity like the Java constants, str() is the Java toString()"""

    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    __repr__ = __str__


class POSType:
    """GermanToken.POSType"""
    NOMEN = _Value('Nomen')
    VERB = _Value('Verb')
    ADJEKTIV = _Value('Adjektiv')
    DETERMINER = _Value('Determiner')
    PRONOMEN = _Value('Pronomen')
    PARTIZIP = _Value('Partizip')
    PROPER_NOUN = _Value('Eigenname')
    OTHER = _Value('Other')  # e.g. sentence start


class Kasus:
    """GermanToken.Kasus"""
    NOMINATIV = _Value('Nominativ')
    AKKUSATIV = _Value('Akkusativ')
    DATIV = _Value('Dativ')
    GENITIV = _Value('Genitiv')
    OTHER = _Value('Other')


class Numerus:
    """GermanToken.Numerus"""
    SINGULAR = _Value('Singular')
    PLURAL = _Value('Plural')
    OTHER = _Value('Other')


class Genus:
    """GermanToken.Genus"""
    NEUTRUM = _Value('Neutrum')
    MASKULINUM = _Value('Maskulinum')
    FEMININUM = _Value('Femininum')
    OTHER = _Value('Other')
    ALLGEMEIN = _Value('Allgemein')  # Morphy ALG = Mas, Fem, or Neu


class Determination:
    """GermanToken.Determination"""
    DEFINITE = _Value('definit')
    INDEFINITE = _Value('indefinit')


_KASUS = {'AKK': Kasus.AKKUSATIV, 'GEN': Kasus.GENITIV, 'NOM': Kasus.NOMINATIV, 'DAT': Kasus.DATIV}
_NUMERUS = {'PLU': Numerus.PLURAL, 'SIN': Numerus.SINGULAR}
_GENUS = {'MAS': Genus.MASKULINUM, 'FEM': Genus.FEMININUM, 'NEU': Genus.NEUTRUM,
          'NOG': Genus.FEMININUM,  # NOG = no genus because only used as plural
          'ALG': Genus.ALLGEMEIN}
_DETERMINATION = {'IND': Determination.INDEFINITE, 'DEF': Determination.DEFINITE}
_TYPE_IF_NONE = {'SUB': POSType.NOMEN, 'VER': POSType.VERB, 'ADJ': POSType.ADJEKTIV, 'PRO': POSType.PRONOMEN,
                 'ART': POSType.DETERMINER}


class AnalyzedGermanToken:
    """Port of AnalyzedGermanToken: one reading of a German word, parsed
    from the POS tag of an AnalyzedToken (type, casus, numerus, genus and
    determination are None if not part of the tag)."""

    __slots__ = ('type', 'casus', 'numerus', 'genus', 'determination')

    def __init__(self, token):
        self.type = self.casus = self.numerus = self.genus = self.determination = None
        pos_tag = token.pos_tag
        if pos_tag is None:
            return
        # StringUtils.split(posTag, ':') (empty parts are dropped)
        parts = [p for p in pos_tag.split(':') if p]
        if len(parts) < 3:
            return
        for part in parts:
            if part == 'EIG':
                self.type = POSType.PROPER_NOUN
            elif part in ('PA1', 'PA2'):
                self.type = POSType.PARTIZIP
            elif part in _TYPE_IF_NONE:
                if self.type is None:
                    self.type = _TYPE_IF_NONE[part]
            elif part in _KASUS:
                self.casus = _KASUS[part]
            elif part in _NUMERUS:
                self.numerus = _NUMERUS[part]
            elif part in _GENUS:
                self.genus = _GENUS[part]
            elif part in _DETERMINATION:
                self.determination = _DETERMINATION[part]

    def get_type(self):
        return self.type

    def get_casus(self):
        return self.casus

    def get_numerus(self):
        return self.numerus

    def get_genus(self):
        return self.genus

    def get_determination(self):
        return self.determination
