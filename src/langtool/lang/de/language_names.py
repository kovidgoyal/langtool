"""Port of org.languagetool.rules.de.LanguageNames: German names of
languages (used by CaseRule and its anti-patterns)."""

from ...tools import java_hash_set_copy_order

_LANGUAGE_LIST = (
    'Angelsächsisch', 'Afrikanisch', 'Albanisch', 'Altarabisch', 'Altchinesisch', 'Altgriechisch',
    'Althochdeutsch', 'Altpersisch', 'Amerikanisch', 'Arabisch', 'Armenisch', 'Bairisch', 'Baskisch',
    'Bengalisch', 'Bulgarisch', 'Chinesisch', 'Dänisch', 'Deutsch', 'Englisch', 'Estnisch', 'Finnisch',
    'Französisch', 'Frühneuhochdeutsch', 'Germanisch', 'Georgisch', 'Griechisch', 'Hebräisch',
    'Hocharabisch', 'Hochchinesisch', 'Hochdeutsch', 'Holländisch', 'Indonesisch', 'Irisch', 'Isländisch',
    'Italienisch', 'Japanisch', 'Jiddisch', 'Jugoslawisch', 'Kantonesisch', 'Katalanisch', 'Klingonisch',
    'Koreanisch', 'Kroatisch', 'Kurdisch', 'Lateinisch', 'Lettisch', 'Litauisch', 'Luxemburgisch',
    'Mittelhochdeutsch', 'Mongolisch', 'Neuhochdeutsch', 'Niederländisch', 'Norwegisch', 'Persisch',
    'Plattdeutsch', 'Polnisch', 'Portugiesisch', 'Rätoromanisch', 'Rumänisch', 'Russisch', 'Sächsisch',
    'Schwäbisch', 'Schwedisch', 'Schweizerisch', 'Serbisch', 'Serbokroatisch', 'Slawisch', 'Slowakisch',
    'Slowenisch', 'Spanisch', 'Syrisch', 'Tamilisch', 'Tibetisch', 'Tschechisch', 'Tschetschenisch',
    'Türkisch', 'Turkmenisch', 'Uigurisch', 'Ukrainisch', 'Ungarisch', 'Usbekisch', 'Vietnamesisch',
    'Walisisch', 'Weißrussisch',
)

_LANGUAGES = frozenset(_LANGUAGE_LIST)

# String.join("|", languages): the iteration order of the Java HashSet
_AS_REGEX = '|'.join(java_hash_set_copy_order(_LANGUAGE_LIST))


def get():
    """LanguageNames.get()"""
    return _LANGUAGES


def get_as_regex():
    """LanguageNames.getAsRegex()"""
    return _AS_REGEX
