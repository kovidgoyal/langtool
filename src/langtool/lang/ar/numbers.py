"""Ports of org.languagetool.tools.ArabicNumbersWords,
ArabicNumbersWordsConstants and ArabicUnitsHelper: Arabic numbers as words
(and back), with the agreement of the units (Tamyeez)."""

from fractions import Fraction

from ...tools import java_split, java_trim
from .tools import remove_tashkeel

# --- ArabicNumbersWordsConstants ---

ARABIC_ONES = ('', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة', 'عشرة', 'أحد عشر',
               'اثنا عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر', 'ستة عشر', 'سبعة عشر', 'ثمانية عشر', 'تسعة عشر')
ARABIC_FEMININE_ONES = ('', 'إحدى', 'اثنتان', 'ثلاث', 'أربع', 'خمس', 'ست', 'سبع', 'ثمان', 'تسع', 'عشر',
                        'إحدى عشرة', 'اثنتا عشرة', 'ثلاث عشرة', 'أربع عشرة', 'خمس عشرة', 'ست عشرة', 'سبع عشرة',
                        'ثماني عشرة', 'تسع عشرة')
ARABIC_TENS = ('عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون')
ARABIC_HUNDREDS = ('', 'مائة', 'مئتان', 'ثلاثمئة', 'أربعمئة', 'خمسمئة', 'ستمئة', 'سبعمئة', 'ثمانمئة', 'تسعمئة')
ARABIC_TWOS = ('مئتان', 'ألفان', 'مليونان', 'ملياران', 'تريليونان', 'كوادريليونان', 'كوينتليونان', 'سكستيليونان')
ARABIC_APPENDED_TWOS = ('مئتا', 'ألفا', 'مليونا', 'مليارا', 'تريليونا', 'كوادريليونا', 'كوينتليونا', 'سكستيليونا')
ARABIC_GROUP = ('مائة', 'ألف', 'مليون', 'مليار', 'تريليون', 'كوادريليون', 'كوينتليون', 'سكستيليون')
ARABIC_APPENDED_GROUP = ('', 'ألفاً', 'مليوناً', 'ملياراً', 'تريليوناً', 'كوادريليوناً', 'كوينتليوناً',
                         'سكستيليوناً')
ARABIC_PLURAL_GROUPS = ('', 'آلاف', 'ملايين', 'مليارات', 'تريليونات', 'كوادريليونات', 'كوينتليونات',
                        'سكستيليونات')
# inflected forms (jar)
ARABIC_JAR_TENS = ('عشرين', 'ثلاثين', 'أربعين', 'خمسين', 'ستين', 'سبعين', 'ثمانين', 'تسعين')
ARABIC_JAR_TWOS = ('مئتين', 'ألفين', 'مليونين', 'مليارين', 'تريليونين', 'كوادريليونين', 'كوينتليونين',
                   'سكستيليونين')
ARABIC_JAR_APPENDED_TWOS = ('مئتي', 'ألفي', 'مليوني', 'ملياري', 'تريليوني', 'كوادريليوني', 'كوينتليوني',
                            'سكستيليوني')
ARABIC_JAR_ONES = ('', 'واحد', 'اثنين', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة', 'عشرة',
                   'أحد عشر', 'اثني عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر', 'ستة عشر', 'سبعة عشر',
                   'ثمانية عشر', 'تسعة عشر')
ARABIC_JAR_FEMININE_ONES = ('', 'إحدى', 'اثنتين', 'ثلاث', 'أربع', 'خمس', 'ست', 'سبع', 'ثمان', 'تسع', 'عشر',
                            'إحدى عشرة', 'اثنتي عشرة', 'ثلاث عشرة', 'أربع عشرة', 'خمس عشرة', 'ست عشرة',
                            'سبع عشرة', 'ثماني عشرة', 'تسع عشرة')
ARABIC_JAR_HUNDREDS = ('', 'مائة', 'مئتين', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 'ستمائة', 'سبعمائة', 'ثمانمائة',
                       'تسعمائة')

# words of numbers
NUMBER_WORDS = {
    'صفر': 0, 'واحد': 1, 'واحدة': 1, 'اثنان': 2, 'ثلاثة': 3, 'أربعة': 4, 'خمسة': 5, 'ستة': 6, 'سبعة': 7,
    'ثمانية': 8, 'تسعة': 9, 'عشرة': 10, 'عشرون': 20, 'ثلاثون': 30, 'أربعون': 40, 'خمسون': 50, 'ستون': 60,
    'سبعون': 70, 'ثمانون': 80, 'تسعون': 90, 'مئة': 100, 'مئتان': 200, 'ثلاثمئة': 300, 'أربعمئة': 400,
    'خمسمئة': 500, 'ستمئة': 600, 'سبعمئة': 700, 'ثمانمئة': 800, 'تسعمئة': 900, 'ثلاثمائة': 300,
    'أربعمائة': 400, 'خمسمائة': 500, 'ستمائة': 600, 'سبعمائة': 700, 'ثمانمائة': 800, 'تسعمائة': 900,
    'ألف': 1000, 'ألفا': 1000, 'مليون': 1000000, 'مليونا': 1000000, 'مليار': 1000000000, 'ألفان': 2000,
    'ألفين': 2000, 'مليونان': 2000000, 'مليونين': 2000000, 'ملياران': 2000000000, 'مليارين': 2000000000,
    'أحد': 1, 'إحدى': 1, 'اثنين': 2, 'إثنين': 2, 'إثنان': 2, 'اثني': 2, 'اثنتي': 2, 'اثنا': 2, 'إثني': 2,
    'إثنتي': 2, 'إثنا': 2, 'ثلاث': 3, 'أربع': 4, 'خمس': 5, 'ست': 6, 'سبع': 7, 'ثمان': 8, 'ثماني': 8, 'تسع': 9,
    'عشر': 10, 'ثلاثا': 3, 'أربعا': 4, 'خمسا': 5, 'ستا': 6, 'سبعا': 7, 'تسعا': 9, 'عشرا': 10, 'عشرين': 20,
    'ثلاثين': 30, 'أربعين': 40, 'خمسين': 50, 'ستين': 60, 'سبعين': 70, 'ثمانين': 80, 'تسعين': 90, 'مائة': 100,
    'مئتين': 200, 'آلاف': 1000, 'ملايين': 1000000, 'مليارات': 1000000000,
}


def _i32(n):
    """Java int overflow"""
    n &= 0xffffffff
    return n - 0x100000000 if n & 0x80000000 else n


def _jrem(a, b):
    """Java's % (the sign of the dividend)"""
    r = abs(a) % abs(b)
    return -r if a < 0 else r


# --- ArabicUnitsHelper ---

def _unit(feminin, *forms):
    keys = ('one_raf3', 'one_nasb', 'one_jar', 'two_raf3', 'two_nasb', 'two_jar', 'plural_raf3', 'plural_nasb',
            'plural_jar')
    d = dict(zip(keys, forms))
    d['feminin'] = feminin
    return d


UNITS_MAP = {
    'دينار': _unit('no', 'دينار', 'دينارًا', 'دينارٍ', 'ديناران', 'دينارين', 'دينارين', 'دنانيرُ', 'دنانيرَ',
                   'دنانيرَ'),
    'درهم': _unit('no', 'درهم', 'درهمًا', 'درهمٍ', 'درهمان', 'درهمين', 'درهمين', 'دراهمُ', 'دراهمَ', 'دراهمَ'),
    'دولار': _unit('no', 'دولار', 'دولارًا', 'دولارٍ', 'دولاران', 'دولارين', 'دولارين', 'دولاراتٌ', 'دولاراتٍ',
                   'دولاراتٍ'),
    'ليرة': _unit('yes', 'ليرة', 'ليرةً', 'ليرةٍ', 'ليرتان', 'ليرتين', 'ليرتين', 'ليراتٌ', 'ليراتٍ', 'ليراتٍ'),
}


def is_feminin(unit):
    """ArabicUnitsHelper.isFeminin (also ArabicNumbersWords.isFeminin)"""
    return unit in UNITS_MAP and UNITS_MAP[unit].get('feminin', 'no') == 'yes'


def is_unit(unit):
    return unit in UNITS_MAP


def get_form(unit, category, inflection):
    """ArabicUnitsHelper.getForm: the form of a unit for a category (one,
    two, plural) and an inflection (raf3, nasb, jar; empty is raf3)"""
    if not inflection:
        inflection = 'raf3'
    key = category + '_' + inflection
    if unit in UNITS_MAP:
        return UNITS_MAP[unit].get(key, '[' + unit + ']')
    return '[[' + unit + ']]'


def get_one_form(unit, inflection):
    return get_form(unit, 'one', inflection)


def get_two_form(unit, inflection):
    return get_form(unit, 'two', inflection)


def get_plural_form(unit, inflection):
    return get_form(unit, 'plural', inflection)


# --- ArabicNumbersWords ---

def number_to_arabic_words(number, is_feminine=False, is_attached=False, inflection_case=''):
    """ArabicNumbersWords.numberToArabicWords: number is a string (Java: new
    BigInteger(number)) or an int"""
    return java_trim(_convert_to_arabic(int(number), is_feminine, is_attached, inflection_case))


def _convert_to_arabic(number, is_feminine, is_attached, inflection_case):
    if number == 0:
        return 'صفر'
    if number == 1:
        return 'واحد'
    if number == 2:
        return _get_digit_inflected_status(2, 0, False, False, inflection_case)
    # BigDecimal arithmetic: the groups are divided exactly (the remaining
    # number is a decimal number)
    temp_number = Fraction(number)
    result = ''
    group = 0
    while temp_number >= 1:
        # separate number into groups
        number_to_process = temp_number % 1000
        temp_number = temp_number / 1000
        # convert group into its text
        temp_value = int(temp_number)  # setScale(0, FLOOR).intValue()
        group_int = int(number_to_process)
        group_description = _process_arabic_group(group_int, group, temp_value, is_feminine, is_attached,
                                                  inflection_case)
        if group_description:  # here we add the new converted group to the previous concatenated text
            if group > 0:
                if result:
                    result = 'و' + result
                if group_int != 2:
                    if int(number_to_process % 100) != 1:
                        if 3 <= number_to_process <= 10:  # for numbers between 3 and 9 we use plural name
                            result = ARABIC_PLURAL_GROUPS[group] + ' ' + result
                        elif result:  # use appending case
                            result = ARABIC_APPENDED_GROUP[group] + ' ' + result
                        else:  # use normal case
                            result = ARABIC_GROUP[group] + ' ' + result
            result = group_description + ' ' + result
        group += 1
    return result


def _process_arabic_group(group_number, group_level, remaining_number, is_feminine, is_attached, inflection_case):
    tens = group_number % 100
    hundreds = group_number // 100
    result = ''
    if hundreds > 0:
        if tens == 0 and hundreds == 2:  # the annexed case (حالة المضاف)
            if group_level == 0:
                result = _get_digit_hundred_jar_status(hundreds, inflection_case)
            else:
                result = _get_digit_twos_jar_status(0, inflection_case, True)
        else:  # the normal case
            result = _get_digit_hundred_jar_status(hundreds, inflection_case)
    if tens > 0:
        if tens < 20:  # if we are processing under 20 numbers
            if tens == 2 and hundreds == 0 and group_level > 0:
                # This is special case for number 2 when it comes alone in the group
                result = _get_digit_twos_jar_status(group_level, inflection_case, False)
            else:  # General case
                if result:
                    result += ' و'
                if tens == 1 and group_level > 0:
                    result += ARABIC_GROUP[group_level]
                elif tens in (1, 2) and group_level in (0, -1) and hundreds == 0 and remaining_number == 0:
                    result += ''  # Special case for 1 and 2 numbers like: ليرة سورية و ليرتان سوريتان
                else:
                    # Get Feminine status for this digit
                    result += _get_digit_inflected_status(tens, group_level, is_feminine, is_attached,
                                                          inflection_case)
        else:
            ones = tens % 10
            tens = tens // 10 - 2  # 20's offset
            if ones > 0:
                if result:
                    result += ' و'
                # Get Feminine status for this digit
                result += _get_digit_inflected_status(ones, group_level, is_feminine, is_attached, inflection_case)
            if result:
                result += ' و'
            # get ten text for inflected case jar or nasb
            result += _get_digit_tens_jar_status(tens, inflection_case)
    return result


def _get_digit_inflected_status(digit, group_level, is_feminine, is_attached, inflection_case):
    if inflection_case == 'jar':
        if group_level in (-1, 0):
            return ARABIC_JAR_FEMININE_ONES[digit] if is_feminine else ARABIC_JAR_ONES[digit]
    elif group_level in (-1, 0):
        return ARABIC_FEMININE_ONES[digit] if is_feminine else ARABIC_ONES[digit]
    return ARABIC_ONES[digit]


def _get_digit_tens_jar_status(digit, inflection_case):
    if inflection_case == 'jar':
        return ARABIC_JAR_TENS[digit]
    return ARABIC_TENS[digit]


def _get_digit_hundred_jar_status(digit, inflection_case):
    if inflection_case == 'jar':
        return ARABIC_JAR_HUNDREDS[digit]
    return ARABIC_HUNDREDS[digit]


def _get_digit_twos_jar_status(digit, inflection_case, is_appended):
    if not is_appended:
        if inflection_case == 'jar':
            return ARABIC_JAR_TWOS[digit]
        return ARABIC_TWOS[digit]
    if inflection_case == 'jar':
        return ARABIC_JAR_APPENDED_TWOS[digit]
    return ARABIC_APPENDED_TWOS[digit]


def text_to_number(text):
    """ArabicNumbersWords.textToNumber: convert Arabic text into a number,
    e.g. "خمسمئة وثلاث وعشرون" -> 523. text is a string or a list of words
    (Java's Integer arithmetic, including its overflow)."""
    if isinstance(text, str):
        words = java_split(remove_tashkeel(text), ' ')
    else:
        words = text
    total = 0
    # the partial total for the three number
    partial = 0
    for word in words:
        if word and word != 'واحد' and word[0] in 'وفبكل':  # strip first char
            word = word[1:]
        if word != 'واحد' and word.startswith('و'):  # strip first char
            word = word[1:]
        if is_numeric_word(word):
            actual_number = get_numeric_word_value(word)
            if actual_number % 1000 == 0:
                # the case of 1000 or 1 million
                if partial == 0:
                    partial = 1
                total = _i32(total + _i32(partial * actual_number))
                # re-initiate the partial total
                partial = 0
            else:
                partial = _i32(partial + actual_number)
    # add the final partial to total
    return _i32(total + partial)


def get_unit_form(n, unit_lemma, inflection):
    """ArabicNumbersWords.getUnitForm: the suitable form of a unit"""
    return number_to_words_with_units_map(n, unit_lemma, inflection).get('unit', '')


def number_to_words_with_units(n, unit, inflection):
    """ArabicNumbersWords.numberToWordsWithUnits: a number phrase with a
    unit"""
    return number_to_words_with_units_map(n, unit, inflection).get('all', '')


def number_to_words_with_units_map(n, unit, inflection):
    """ArabicNumbersWords.numberToWordsWithUnitsMap"""
    # get feminin from unit
    feminin = is_feminin(unit)
    unit_inflection = ''
    unit_number = ''
    # generate phrase from number
    number_phrase = number_to_arabic_words(str(n), feminin, True, inflection)
    phrase = []
    # generate suitable unit
    m100 = _jrem(n, 100)
    if n == 0:
        new_unit = get_form(unit, 'plural', 'nasb')
        unit_inflection = 'nasb'
        unit_number = 'plural'
        phrase += ['لا', ' ', new_unit]
    elif n == 1:  # دينار واحد / دينارا واحدا / دينارٍ واحدٍ
        new_unit = get_form(unit, 'one', inflection)
        unit_inflection = inflection
        unit_number = 'one'
        phrase += [new_unit, ' ', number_phrase]
    elif n == 2:  # ديناران / دينارين
        new_unit = get_form(unit, 'two', inflection)
        unit_inflection = inflection
        unit_number = 'two'
        phrase.append(new_unit)
    elif m100 == 1:  # مئة دينار ودينار, ألف دينار ودينار
        number_phrase_hundred = number_to_arabic_words(str(_i32(n - 1)), feminin, True, inflection)
        new_unit_hundred = get_form(unit, 'one', 'jar')
        # unit for one
        new_unit_one = get_form(unit, 'one', inflection)
        unit_inflection = inflection
        unit_number = 'one'
        new_unit = new_unit_one
        phrase += [number_phrase_hundred, ' ', new_unit_hundred, ' ', 'و', new_unit_one]
    elif m100 == 2:  # مئة دينار ودينارين, ألف دينار ودينارين
        number_phrase_hundred = number_to_arabic_words(str(_i32(n - 2)), feminin, True, inflection)
        new_unit_hundred = get_form(unit, 'one', 'jar')
        # unit for two
        new_unit_two = get_form(unit, 'two', inflection)
        unit_inflection = inflection
        unit_number = 'two'
        new_unit = new_unit_two
        phrase += [number_phrase_hundred, ' ', new_unit_hundred, ' ', 'و', new_unit_two]
    elif 3 <= m100 <= 10:  # خمسة دنانير, عشرة رجال
        new_unit = get_form(unit, 'plural', 'jar')
        unit_inflection = 'jar'
        unit_number = 'plural'
        phrase += [number_phrase, ' ', new_unit]
    elif m100 >= 11:  # أحد عشر رجلا, ثمانون رجلا, تسعة وتسعون رجلا
        new_unit = get_form(unit, 'one', 'nasb')
        unit_inflection = 'nasb'
        unit_number = 'one'
        phrase += [number_phrase, ' ', new_unit]
    elif m100 == 0:  # مئة دينار, ثمانون ألف دينار, تسعة وتسعون مليون دينار
        new_unit = get_form(unit, 'one', 'jar')
        unit_inflection = 'jar'
        unit_number = 'one'
        phrase += [number_phrase, ' ', new_unit]
    else:
        new_unit = ''
        phrase += [number_phrase, ' **', unit + '**']
    return {
        'all': ''.join(phrase),
        'phrase': number_phrase,
        'unit': new_unit,
        'number': str(n),
        'unitLemma': unit,
        'unitNumber': unit_number,
        'unitInflection': unit_inflection,
        'inflection': inflection,
        'feminin': 'true' if feminin else 'false',
    }


def check_numeric_phrase(phrase_input, feminin, attached, inflection):
    """ArabicNumbersWords.checkNumericPhrase: whether the numeric phrase is
    well spelled for the given options"""
    phrase = remove_tashkeel(phrase_input)
    x = text_to_number(phrase)
    auto_phrase = remove_tashkeel(number_to_arabic_words(str(x), feminin, attached, inflection))
    return auto_phrase == phrase


def get_suggestions_numeric_phrase(phrase_input, feminin, attached, inflection):
    """ArabicNumbersWords.getSuggestionsNumericPhrase: suggestions for an
    incorrect numeric phrase (for all cases if inflection is empty)"""
    suggestions = []
    phrase = remove_tashkeel(phrase_input)
    x = text_to_number(phrase)
    auto_phrase = remove_tashkeel(number_to_arabic_words(str(x), feminin, attached, inflection))
    if auto_phrase != phrase:
        if inflection:
            suggestions.append(auto_phrase)
        else:
            # raf3
            suggestions.append(number_to_arabic_words(str(x), feminin, attached, 'raf3'))
            # nasb + jar
            suggestions.append(number_to_arabic_words(str(x), feminin, attached, 'jar'))
    return suggestions


def get_suggestions_numeric_phrase_with_units(phrase_input, unit, feminin, attached, inflection):
    """ArabicNumbersWords.getSuggestionsNumericPhraseWithUnits: like
    get_suggestions_numeric_phrase, the suggestions are the maps of
    number_to_words_with_units_map"""
    suggestions = []
    phrase = remove_tashkeel(phrase_input)
    x = text_to_number(phrase)
    auto_phrase_map = number_to_words_with_units_map(x, unit, inflection)
    auto_phrase = remove_tashkeel(auto_phrase_map.get('phrase', ''))
    if auto_phrase != phrase:
        if inflection:
            suggestions.append(auto_phrase_map)
        else:
            # raf3
            suggestions.append(number_to_words_with_units_map(x, unit, 'raf3'))
            # nasb + jar
            suggestions.append(number_to_words_with_units_map(x, unit, 'jar'))
    return suggestions


def is_numeric_word(word):
    return word in NUMBER_WORDS


def get_numeric_word_value(word):
    return NUMBER_WORDS.get(word)
