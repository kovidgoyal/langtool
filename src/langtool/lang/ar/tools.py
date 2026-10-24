"""Ports of org.languagetool.tools.ArabicStringTools, ArabicConstants,
ArabicConstantsMaps and ArabicWordMaps."""

from ...tools import remove_tashkeel  # noqa: F401 -- ArabicStringTools.removeTashkeel

# ArabicStringTools.TASHKEEL_CHARS: Fathatan, Dammatan, Kasratan, Fatha,
# Damma, Kasra, Shadda, Sukun, Maddah Above, Hamza Above, Hamza Below,
# Subscript Alef and Tatweel (langtool.tools.remove_tashkeel removes them)
TASHKEEL_CHARS = 'ًٌٍَُِّْٕٖٓٔـ'

# --- ArabicConstants ---

# Harakat
FATHATAN = 'ً'
DAMMATAN = 'ٌ'
KASRATAN = 'ٍ'
FATHA = 'َ'
DAMMA = 'ُ'
KASRA = 'ِ'
SHADDA = 'ّ'
SUKUN = 'ْ'
MADDAH_ABOVE = 'ٓ'

# letters
COMMA = '،'
SEMICOLON = '؛'
QUESTION = '؟'
HAMZA = 'ء'
ALEF_MADDA = 'آ'
ALEF_HAMZA_ABOVE = 'أ'
WAW_HAMZA = 'ؤ'
ALEF_HAMZA_BELOW = 'إ'
YEH_HAMZA = 'ئ'
ALEF = 'ا'
BEH = 'ب'
TEH_MARBUTA = 'ة'
TEH = 'ت'
THEH = 'ث'
JEEM = 'ج'
HAH = 'ح'
KHAH = 'خ'
DAL = 'د'
THAL = 'ذ'
REH = 'ر'
ZAIN = 'ز'
SEEN = 'س'
SHEEN = 'ش'
SAD = 'ص'
DAD = 'ض'
TAH = 'ط'
ZAH = 'ظ'
AIN = 'ع'
GHAIN = 'غ'
TATWEEL = 'ـ'
FEH = 'ف'
QAF = 'ق'
KAF = 'ك'
LAM = 'ل'
MEEM = 'م'
NOON = 'ن'
HEH = 'ه'
WAW = 'و'
ALEF_AKSURA = 'ى'
YEH = 'ي'
MADDA_ABOVE = 'ٓ'
HAMZA_ABOVE = 'ٔ'
HAMZA_BELOW = 'ٕ'

# digits
ZERO = '٠'
ONE = '١'
TWO = '٢'
THREE = '٣'
FOUR = '٤'
FIVE = '٥'
SIX = '٦'
SEVEN = '٧'
EIGHT = '٨'
NINE = '٩'

# Arabic symbols
PERCENT = '٪'
DECIMAL = '٫'
THOUSANDS = '٬'
STAR = '٭'
MINI_ALEF = 'ٰ'
ALEF_WASLA = 'ٱ'
FULL_STOP = '۔'
BYTE_ORDER_MARK = '﻿'

# --- ArabicConstantsMaps / ArabicWordMaps ---

# isolated pronoun -> attached pronoun
ISOLATED_TO_ATTACHED_PRONOUN = {
    'أنا': 'ني',
    'نحن': 'نا',
    'هو': 'ه',
    'هي': 'ها',
    'هم': 'هم',
    'هن': 'هن',
    'أنتما': 'كما',
    'أنتم': 'كم',
    'أنتن': 'كن',
}


def get_attached_pronoun(word):
    """ArabicWordMaps.getAttachedPronoun: the attached form of an isolated
    pronoun ('' for other words)"""
    if word is None:
        return ''
    return ISOLATED_TO_ATTACHED_PRONOUN.get(word, '')
