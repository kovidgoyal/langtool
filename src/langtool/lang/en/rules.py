"""English specific rules (port of org.languagetool.rules.en).

The Java rules get a Locale("en") (or "en-US" etc.) from getLocale(), used
for case conversion; it has no special case mapping, so the default lower()
is used. The rules whose Java constructors take no language use
English/AmericanEnglish.getInstance() as in Java."""

import threading

from ... import jregex
from ...patterns.pattern_token import PatternTokenBuilder, pos, pos_regex, token, token_regex
from ...patterns.rules import make_anti_patterns
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractDashRule, AbstractRepeatedWordsRule,
                                     AbstractSimpleReplaceRule, AbstractSimpleReplaceRule2, AbstractSpecificCaseRule,
                                     AbstractStyleTooOftenUsedWordRule, AbstractWordCoherencyRule,
                                     GenericUnpairedQuotesRule, WordRepeatBeginningRule, WrongWordInContextRule,
                                     java_hash_set_order, load_compound_rule_data, load_repeated_words,
                                     load_word_coherency_data, _rules_file)
from ...rules.base import RuleMatch
from ...rules.core import Categories, CoreTextLevelRule, GenericUnpairedBracketsRule, WordRepeatRule
from ...rules.core import LongSentenceRule as _CoreLongSentenceRule
from ...rules.unit_conversion import (AbstractUnitConversionRule, CELSIUS, CUBIC_METRE, DecimalFormat, FAHRENHEIT,
                                      FEET, HOUR, IMP_FL_OUNCE, IMP_GALLON, IMP_PINT, IMP_QUART, INCH, KILOGRAM,
                                      KILOMETRE_PER_HOUR, LITRE, METRE, MILE, OUNCE, POUND, SQUARE_METRE,
                                      US_CUP, US_FL_OUNCE, US_GALLON, US_PINT, US_QUART, YARD)
from ...tools import java_equals_ignore_case


def _english():
    """new English() / Languages.getLanguageForShortCode("en")"""
    from ...api import get_language
    return get_language('en')


def _american_english():
    """AmericanEnglish.getInstance()"""
    from ...api import get_language
    return get_language('en-US')


# --- AbstractSimpleReplaceRule2 subclasses ---

class _PathReplaceRule(AbstractSimpleReplaceRule2):
    """The AbstractSimpleReplaceRule2 subclasses whose Java constructors get
    the path of the replacement file (one per variant)."""

    def __init__(self, messages, path, language):
        super().__init__(messages, language)
        if path is None:
            raise ValueError('path must not be None')
        self.path = path

    def get_file_names(self):
        return [self.path]


class AmericanReplaceRule(_PathReplaceRule):
    """Port of org.languagetool.rules.en.AmericanReplaceRule: British words
    easily confused in American English (/en/en-US/replace.txt)."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language=None):
        super().__init__(messages, path, _american_english())
        self.use_sub_rule_specific_ids()
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('Are baked <marker>crisps</marker> healthy?',
                              'Are baked <marker>chips</marker> healthy?')

    def get_id(self):
        return 'EN_US_SIMPLE_REPLACE'

    def get_description(self):
        return 'British words easily confused in American English: $match'

    def get_short(self):
        return 'British word'

    def get_message(self):
        return "'$match' is a common British expression. Consider using expressions more common to American English."


class BritishReplaceRule(_PathReplaceRule):
    """Port of org.languagetool.rules.en.BritishReplaceRule: American words
    easily confused in British English (/en/en-GB/replace.txt)."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language=None):
        from ...api import get_language
        super().__init__(messages, path, get_language('en-GB'))  # BritishEnglish.getInstance()
        self.use_sub_rule_specific_ids()
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair(
            'We can produce <marker>drapes</marker> of any size or shape from a choice of over 500 different fabrics.',
            'We can produce <marker>curtains</marker> of any size or shape from a choice of over 500 different '
            'fabrics.')

    def get_id(self):
        return 'EN_GB_SIMPLE_REPLACE'

    def get_description(self):
        return 'American words easily confused in British English: $match'

    def get_short(self):
        return 'American word'

    def get_message(self):
        return "'$match' is a common American expression. Consider using expressions more common to British English."


class NewZealandReplaceRule(_PathReplaceRule):
    """Port of org.languagetool.rules.en.NewZealandReplaceRule: words that
    are not New Zealand English (/en/en-NZ/replace.txt)."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language=None):
        from ...api import get_language
        super().__init__(messages, path, get_language('en-NZ'))  # new NewZealandEnglish()
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('A <marker>sidewalk</marker> is a path along the side of a road.',
                              'A <marker>footpath</marker> is a path along the side of a road.')

    def get_id(self):
        return 'EN_NZ_SIMPLE_REPLACE'

    def get_description(self):
        return 'English words easily confused in New Zealand English'

    def get_short(self):
        return 'Not a New Zealand English word'

    def get_message(self):
        return ("'$match' is a non-standard expression. Consider using expressions more common to New Zealand "
                "English.")


class SimpleReplaceRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.en.SimpleReplaceRule: wrong
    words/phrases of /en/replace.txt and /en/replace_custom.txt."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.use_sub_rule_specific_ids()

    def get_file_names(self):
        return ['/en/replace.txt', '/en/replace_custom.txt']

    def get_id(self):
        return 'EN_SIMPLE_REPLACE'

    def get_description(self):
        return 'Check for wrong words/phrases: $match'

    def get_short(self):
        return 'Wrong word'

    def get_message(self):
        return 'Did you mean $suggestions?'


class SimpleReplaceProfanityRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.en.SimpleReplaceProfanityRule:
    expressions of /en/replace_profanity.txt that can be considered
    offensive (picky, no suggestions)."""

    issue_type = 'Style'  # needs ITS issue to be 'Style' in order to get purple underline + lower prio

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('STYLE', messages)
        self.url = 'https://en.wiktionary.org/wiki/Category:English_offensive_terms'
        self.tags = ['picky']
        self.set_rule_has_suggestions(False)

    def get_file_names(self):
        return ['/en/replace_profanity.txt']

    def get_id(self):
        return 'PROFANITY'

    def get_description(self):
        return 'Profanity'

    def get_short(self):
        return 'Profanity'

    def get_message(self):
        return 'This expression can be considered offensive.'


class EnglishDiacriticsRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.en.EnglishDiacriticsRule: foreign
    names and expressions that originally have a diacritic
    (/en/diacritics.txt)."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, _english())
        self.use_sub_rule_specific_ids()
        self.category = Categories.get('TYPOS', messages)
        self.add_example_pair('<marker>blase</marker>', '<marker>blasé</marker>')
        self.url = 'https://en.wikipedia.org/wiki/English_terms_with_diacritical_marks'

    def get_file_names(self):
        return ['/en/diacritics.txt']

    def get_id(self):
        return 'EN_DIACRITICS_REPLACE_ORTHOGRAPHY'

    def get_description(self):
        return "Suggest diacritics for '$match'"

    def get_short(self):
        return 'The original word has a diacritic'

    def get_message(self):
        return "'$match' is an imported foreign name or expression, which originally has a diacritic."

    def get_suggestions_separator(self):
        return ' or '


class EnglishPlainEnglishRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.en.EnglishPlainEnglishRule: wordy or
    complex expressions of /en/wordiness.txt (default off)."""

    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, _english())
        self.set_default_off()  # reactivate after feature freeze
        self.category = Categories.get('PLAIN_ENGLISH', messages)
        self.add_example_pair('<marker>fatal outcome</marker>', '<marker>death</marker>')
        self.url = 'https://en.wikipedia.org/wiki/List_of_plain_English_words_and_phrases'

    def get_file_names(self):
        return ['/en/wordiness.txt']

    def get_id(self):
        return 'EN_PLAIN_ENGLISH_REPLACE'

    def get_description(self):
        return '1. Wordiness (General)'

    def get_short(self):
        return 'Wordiness'

    def get_message(self):
        return "'$match' is a wordy or complex expression. In some cases, it might be preferable to use $suggestions."

    def get_suggestions_separator(self):
        return ' or '


class EnglishRedundancyRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.en.EnglishRedundancyRule: redundant
    expressions of /en/redundancies.txt (default off)."""

    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, _english())
        self.category = Categories.get('REDUNDANCY', messages)
        self.set_default_off()  # see #1997
        self.add_example_pair('<marker>tuna fish</marker>', '<marker>tuna</marker>')
        self.url = 'https://en.wikipedia.org/wiki/Redundancy_(linguistics)'

    def get_file_names(self):
        return ['/en/redundancies.txt']

    def get_id(self):
        return 'EN_REDUNDANCY_REPLACE'

    def get_description(self):
        return '1. Redundancy (General)'

    def get_short(self):
        return 'Redundancy'

    def get_message(self):
        return "'$match' is a redundancy. In some cases, it might be preferable to use $suggestions"

    def get_suggestions_separator(self):
        return ' or '


# --- AbstractSimpleReplaceRule subclasses ---

class ContractionSpellingRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.en.ContractionSpellingRule:
    contractions without apostrophe (/en/contractions.txt), case
    sensitive, lemmas are not checked."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.add_example_pair('We <marker>havent</marker> earned anything.',
                              "We <marker>haven't</marker> earned anything.")
        self.url = 'https://languagetool.org/insights/post/grammar-contractions/'
        self.check_lemmas = False

    def get_wrong_words(self):
        return self.load_from_path('/en/contractions.txt')

    def get_id(self):
        return 'EN_CONTRACTION_SPELLING'

    def get_description(self):
        return 'Spelling of English contractions'

    def get_short(self):
        return 'Spelling mistake'

    def get_message(self, token_str, replacements):
        return 'Possible spelling mistake found.'

    def is_case_sensitive(self):
        return True


# --- other rules ---

def _compound_anti_patterns():
    b = PatternTokenBuilder
    return [
        [token_regex("['’`´‘]"), token('re')],
        [  # We well received your email
            b().pos_regex('SENT_START|CC|PCT').build(), token_regex('we|you|they|I|s?he|it'), token('well'),
            b().pos_regex('VB.*').build()],
        [token('how'), token('well'), b().pos_regex('VB.*').build()],
        [token_regex('and|&'), token('co')],
        [token('power'), token('off'), token('key')],  # off-key
        [token('see'), token('saw'), token('seen')],  # see saw seen
        [token('forward'), token('looking'), b().pos_regex('IN|TO').build()],  # moving forward looking for ...
        [token('store'), token('front'), token_regex('doors?')],  # Go through the store front door
        [token('from'), token('surface'), token('to'), token('surface')],  # It goes from surface to surface
        [token_regex('senior|junior'), token('year'), token('end')],  # year end
        [token('under'), token('investment'), token('banking')],  # under investment
        [token('spring'), token_regex('cleans?|cleaned|cleaning'), token_regex('up|the|my|our|his|her')],
        [token_regex('series?'), token_regex('a')],  # Serie A team (A-Team)
        [token('hard'), token('time'), b().pos('VBG').build()],  # They had a hard time sharing their ...
        [token('first'), token_regex('ever'), token_regex('green')],  # the first ever green bond by a municipality
        [token_regex('.+'), token('.'), token_regex('(com|io|de|nl|co|net|org|es)')],  # inter-state.com
    ]


_compound_lock = threading.Lock()
_compound_anti_patterns_cache = []


class CompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.en.CompoundRule: compounds of
    /en/compounds.txt written as separate words. A word is misspelled
    according to the misspelling check of the language's default spelling
    rule."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'This word is normally spelled with a hyphen.',
                         'This word is normally spelled as one.',
                         'This expression is normally spelled as one or with a hyphen.',
                         'Compound')
        self.english = language
        self.use_sub_rule_specific_ids()
        self.add_example_pair('I now have a <marker>part time</marker> job.',
                              'I now have a <marker>part-time</marker> job.')
        self.url = 'https://languagetool.org/insights/post/hyphen/'

    def get_id(self):
        return 'EN_COMPOUNDS'

    def get_description(self):
        return 'Hyphenated words: $match'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/en/compounds.txt')

    def get_anti_patterns(self):
        with _compound_lock:
            if not _compound_anti_patterns_cache:
                _compound_anti_patterns_cache.append(make_anti_patterns(_compound_anti_patterns(),
                                                                        _american_english()))
            return _compound_anti_patterns_cache[0]

    def is_misspelled(self, word):
        speller = self.english.get_default_spelling_rule()
        if speller is None:
            raise ValueError('No default spelling rule for ' + self.english.code)
        return speller.is_misspelled(word)


class ConsistentApostrophesRule(CoreTextLevelRule):
    """Port of org.languagetool.rules.en.ConsistentApostrophesRule: checks
    if the two types of apostrophes (' and ’) are used consistently in a
    text (default temp off)."""

    rule_id = 'EN_CONSISTENT_APOS'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_temp_off()  # TODO
        self.url = 'https://languagetool.org/insights/post/punctuation-guide/#what-is-an-apostrophe'
        self.add_example_pair("It's nice, but it <marker>doesn’t</marker> work.",
                              "It's nice, but it <marker>doesn't</marker> work.")

    def get_description(self):
        return "Checks if the two types of apostrophes (' and ’) are used consistently in a text."

    def match(self, sentences, annotated_text=None):
        matches = []
        pos = 0
        if not self._has_two_apostrophe_types(sentences):
            return matches
        for sentence in sentences:
            for tok in sentence.tokens:
                message = None
                repl = None
                if tok is not None and "'" in tok.token and not tok.typographic_apostrophe:
                    message = ('You used a typewriter-style apostrophe here, but a typographic apostrophe elsewhere '
                               'in this text.')
                    repl = tok.token.replace("'", '’')
                elif tok is not None and "'" in tok.token and tok.typographic_apostrophe:
                    message = ('You used a typographic apostrophe here, but a typewriter-style apostrophe elsewhere '
                               'in this text.')
                    repl = tok.token
                if message is not None:
                    match = RuleMatch(self, sentence, pos + tok.start_pos, pos + tok.end_pos,
                                      message + ' Both are correct, but consider using the same type everywhere in '
                                                'your text.')
                    match.set_suggested_replacement(repl)
                    matches.append(match)
            pos += sentence.get_corrected_text_length()
        return matches

    @staticmethod
    def _has_two_apostrophe_types(sentences):
        has_typewriter_style = False
        has_typographic_style = False
        for sentence in sentences:
            for tok in sentence.tokens:
                if tok is not None and "'" in tok.token and not tok.typographic_apostrophe:
                    has_typewriter_style = True
                elif tok is not None and "'" in tok.token and tok.typographic_apostrophe:
                    has_typographic_style = True
                if has_typewriter_style and has_typographic_style:
                    return True
        return False

    def min_to_check_paragraph(self):
        return -1


class EnglishDashRule(AbstractDashRule):
    """Port of org.languagetool.rules.en.EnglishDashRule: compounds of
    /en/compounds.txt written with dashes instead of hyphens."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _english())
        self.add_example_pair("I'll buy a new <marker>T—shirt</marker>.", "I'll buy a new <marker>T-shirt</marker>.")
        self.url = 'https://languagetool.org/insights/post/hyphen/'

    def get_id(self):
        return 'EN_DASH_RULE'

    def get_description(self):
        return "Checks if hyphenated words were spelled with dashes (e.g., 'T — shirt' instead 'T-shirt')."

    def get_message(self):
        return 'A dash was used instead of a hyphen.'

    def get_compounds_data(self):
        return self.load_compound_file('/en/compounds.txt')


class EnglishSpecificCaseRule(AbstractSpecificCaseRule):
    """Port of org.languagetool.rules.en.EnglishSpecificCaseRule: proper
    nouns of /en/specific_case.txt with a special capitalization."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _english())
        self.url = 'https://languagetool.org/insights/post/spelling-capital-letters/'
        self.add_example_pair('I really like <marker>Harry potter</marker>.',
                              'I really like <marker>Harry Potter</marker>.')

    def get_phrases_path(self):
        return '/en/specific_case.txt'

    def get_initial_capital_message(self):
        return 'If the term is a proper noun, use initial capitals.'

    def get_other_capitalization_message(self):
        return 'If the term is a proper noun, use the suggested capitalization.'

    def get_short_message(self):
        return 'Proper noun'

    def get_id(self):
        return 'EN_SPECIFIC_CASE'

    def get_description(self):
        return 'Checks upper/lower case spelling of some proper nouns'


class EnglishUnpairedBracketsRule(GenericUnpairedBracketsRule):
    """Port of org.languagetool.rules.en.EnglishUnpairedBracketsRule:
    unpaired (), [] and {} (quotes are handled by EnglishUnpairedQuotesRule
    since 6.4)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, ['[', '(', '{'], [']', ')', '}'], 'EN_UNPAIRED_BRACKETS')
        self.url = 'https://languagetool.org/insights/post/punctuation-guide/#what-are-parentheses'
        self.add_example_pair('He lived in a <marker>(</marker>large house.',
                              'He lived in a <marker>(</marker>large<marker>)</marker> house.')


class EnglishUnpairedQuotesRule(GenericUnpairedQuotesRule):
    """Port of org.languagetool.rules.en.EnglishUnpairedQuotesRule:
    unpaired “”, "", '' and ‘’; apostrophes of contractions, possessives
    and proper nouns are no quotes."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language, ['“', '"', "'", '‘'], ['”', '"', "'", '’'], 'EN_UNPAIRED_QUOTES')
        self.url = 'https://languagetool.org/insights/post/punctuation-guide/#what-are-quotation-marks'
        self.add_example_pair('"I\'m over here,<marker></marker> she said.',
                              '"I\'m over here,<marker>"</marker> she said.')

    def is_not_beginning_apostrophe(self, tokens, i):
        t = tokens[i]
        return not (t.has_pos_tag('_apostrophe_contraction_') or t.has_pos_tag('POS') or t.has_pos_tag('NNP'))

    def is_not_ending_apostrophe(self, tokens, i):
        t = tokens[i]
        return not (t.has_pos_tag('_apostrophe_contraction_') or t.has_pos_tag('POS') or t.has_pos_tag('NNP'))


class LongSentenceRule(_CoreLongSentenceRule):
    """Port of org.languagetool.rules.en.LongSentenceRule"""

    def __init__(self, messages, language=None, max_words=50):
        super().__init__(messages, language, max_words)
        self.url = 'https://languagetool.org/insights/post/splitting-long-sentences/'

    def get_short_message(self):
        return 'Long sentence'


_SINGLE_CHAR = jregex.compile('(?i)^[a-z]$')
_QUOTE_CHARS = jregex.compile("['’`´‘]")
_LOG_SIGN = jregex.compile('log(ged|s)?|sign(ed|s)?')
# the repeated words that are not errors ("aye aye", "blah blah", ...)
_IGNORED_REPETITIONS = (
    'aye', 'blah', 'mau', 'uh', 'paw', 'cha', 'yum', 'wop', 'woop', 'fnarr', 'fnar', 'ha', 'omg', 'boo', 'tick',
    'twinkle', 'ta', 'la', 'x', 'hi', 'ho', 'heh', 'jay', 'walla', 'sri', 'hey', 'hah', 'heh', 'oh', 'ouh', 'chop',
    'ring', 'beep', 'bleep', 'yeah', 'gout')
_IGNORED_REPETITIONS2 = (
    'quack', 'meow', 'squawk', 'whoa', 'si', 'honk', 'brum', 'chi', 'santorio', 'lapu', 'chow', 'beep', 'shh',
    'yummy', 'boom', 'bye', 'ah', 'aah', 'bang', 'woof', 'wink', 'yes', 'tsk', 'hush', 'ding', 'choo', 'miu', 'tuk',
    'yadda', 'walla', 'doo', 'sapiens', 'tse', 'no', 'Bora')


class EnglishWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.en.EnglishWordRepeatRule: word
    repetitions, with many exceptions ("had had", "that that", "blah
    blah", ...)."""

    rule_id = 'ENGLISH_WORD_REPEAT_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('This <marker>is is</marker> just an example sentence.',
                              'This <marker>is</marker> just an example sentence.')

    @staticmethod
    def _pos_is_in(tokens, position, *pos_tags):
        if 0 <= position < len(tokens):
            for pos_tag in pos_tags:
                if tokens[position].has_partial_pos_tag(pos_tag):
                    return True
        return False

    @staticmethod
    def _repetition_of(word, tokens, position):
        return (position > 0 and java_equals_ignore_case(tokens[position - 1].token, word)
                and java_equals_ignore_case(tokens[position].token, word))

    @staticmethod
    def _next_is(tokens, position, word):
        return position + 1 < len(tokens) and java_equals_ignore_case(tokens[position + 1].token, word)

    def ignore(self, tokens, position):
        if position == 0:
            return False
        # TODO:
        # What that is is a ...
        # but you you're my best friend ...
        # I'm so so happy
        # I'm very very happy
        rep = self._repetition_of
        pos_is_in = self._pos_is_in
        next_is = self._next_is
        word = tokens[position].token
        n = len(tokens)
        if ((rep('did', tokens, position) or rep('do', tokens, position) or rep('does', tokens, position))
                and next_is(tokens, position, "n't")):
            return True
        if (rep('her', tokens, position) and pos_is_in(tokens, position - 2, 'VB', 'VBP', 'VBZ', 'VBG', 'VBD', 'VBN')
                and pos_is_in(tokens, position + 1, 'NN', 'NNS', 'NN:U', 'NN:UN', 'NNP')):
            return True  # "Please pass her her phone."
        if rep('had', tokens, position) and pos_is_in(tokens, position - 2, 'PRP', 'NN'):
            return True  # "If I had had time, I would have gone to see him."
        if rep('that', tokens, position) and pos_is_in(tokens, position + 1, 'MD', 'NN', 'PRP$', 'JJ', 'VBZ', 'VBD'):
            return True  # "I don't think that that is a problem."
        if rep('can', tokens, position) and pos_is_in(tokens, position - 1, 'NN'):
            return True  # "The can can hold the water."
        if rep('hip', tokens, position) and next_is(tokens, position, 'hooray'):
            return True
        if rep('bam', tokens, position) and next_is(tokens, position, 'bigelow'):
            return True
        if rep('wild', tokens, position) and next_is(tokens, position, 'west'):
            return True  # In the wild wild west (https://en.wikipedia.org/wiki/Wild_Wild_West)
        if rep('far', tokens, position) and next_is(tokens, position, 'away'):
            return True
        if rep('so', tokens, position) and next_is(tokens, position, 'much'):
            return True
        if rep('so', tokens, position) and next_is(tokens, position, 'many'):
            return True
        if rep('s', tokens, position) and position > 1 and _QUOTE_CHARS.fullmatch(tokens[position - 2].token):
            return True  # It's S.T.E.A.M.
        if rep('in', tokens, position) and position > 2 and _LOG_SIGN.fullmatch(tokens[position - 3].token):
            return True  # log them in in the
        if rep('in', tokens, position) and position > 1 and _LOG_SIGN.fullmatch(tokens[position - 2].token):
            return True  # log in in the
        if rep('a', tokens, position) and position > 1 and tokens[position - 2].token == '.':
            return True  # "a.k.a a"
        if rep('on', tokens, position) and position > 1 and tokens[position - 2].token == '.':
            return True  # "You can contact E.ON on Instagram"
        if java_equals_ignore_case(tokens[position - 1].token, word) and (
                (position + 1 < n and java_equals_ignore_case(tokens[position + 1].token, word))
                or (position > 1 and java_equals_ignore_case(tokens[position - 2].token, word))):
            # three time word repetition
            return True
        if (_SINGLE_CHAR.fullmatch(tokens[position].token) and position > 1
                and _SINGLE_CHAR.fullmatch(tokens[position - 2].token)
                and position + 1 < n and _SINGLE_CHAR.fullmatch(tokens[position + 1].token)):
            # spelling with spaces in between: "b a s i c a l l y"
            return True
        for w in _IGNORED_REPETITIONS:
            if rep(w, tokens, position):
                return True
        if rep('wait', tokens, position) and position == 2:
            return True
        for w in _IGNORED_REPETITIONS2:
            if rep(w, tokens, position):
                return True
        if tokens[position].token.endswith('ay'):
            if tokens[position - 1].token == 'may' and tokens[position].token == 'May':
                return True  # "may May"
            if tokens[position - 1].token == 'May' and tokens[position].token == 'may':
                return True  # "May may"
            if tokens[1].token == 'May' and tokens[2].token == 'May':
                return True  # "May May" SENT_START
        elif tokens[position].token.endswith('ill'):
            return ((position > 0 and tokens[position - 1].token == 'will'
                     and tokens[position].token == 'Will')  # will Wills
                    or (tokens[position - 1].token == 'Will' and tokens[position].token == 'will')  # Will will ...
                    or (tokens[1].token == 'Will' and tokens[2].token == 'Will'))  # "Will Will" SENT_START
        return super().ignore(tokens, position)


# adverbs used to add to what the previous sentence mentioned
_ADD_ADVERBS = java_hash_set_order(('Additionally', 'Besides', 'Furthermore', 'Moreover', 'Also'))
# adverbs used to express contrast to what the previous sentence mentioned
_CONTRAST_ADVERBS = java_hash_set_order(('Nevertheless', 'Nonetheless', 'Alternatively'))
# adverbs used to express emphasis to what the previous sentence mentioned
_EMPHASIS_ADVERBS = java_hash_set_order(('Undoubtedly', 'Indeed', 'Obviously', 'Clearly', 'Importantly',
                                         'Absolutely', 'Definitely'))
# adverbs used to explain what the previous sentence mentioned
_EXPLAIN_ADVERBS = java_hash_set_order(('Particularly', 'Especially', 'Specifically'))
# linking expressions that can be used instead of the ADD_ADVERBS
_ADD_EXPRESSIONS = ('In addition', 'As well as')
# linking expressions that can be used instead of the CONTRAST_ADVERBS
_CONTRAST_EXPRESSIONS = ('Even so', 'On the other hand')


class EnglishWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.en.EnglishWordRepeatBeginningRule:
    successive sentences beginning with the same word, with suggestions
    for personal pronouns and some adverbs (the other adverbs of the same
    category, in the iteration order of the Java HashSets)."""

    rule_id = 'ENGLISH_WORD_REPEAT_BEGINNING_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair(
            'Moreover, the street is almost entirely residential. <marker>Moreover</marker>, it was named after a '
            'poet.',
            'Moreover, the street is almost entirely residential. <marker>It</marker> was named after a poet.')

    def is_exception(self, tok):
        return super().is_exception(tok) or tok == 'The' or tok == 'A' or tok == 'An'

    def is_adverb(self, atr):
        tok = atr.token
        return tok in _ADD_ADVERBS or tok in _CONTRAST_ADVERBS or tok in _EMPHASIS_ADVERBS or tok in _EXPLAIN_ADVERBS

    def get_suggestions(self, atr):
        tok = atr.token
        # the repeated word is a personal pronoun
        if atr.has_pos_tag('PRP'):
            adapted_token = tok if tok == 'I' else tok.lower()
            return ['Furthermore, ' + adapted_token, 'Likewise, ' + adapted_token,
                    'Not only that, but ' + adapted_token]
        if tok in _ADD_ADVERBS:
            return self._different_adverbs_of_same_category(tok, _ADD_ADVERBS) + list(_ADD_EXPRESSIONS)
        if tok in _CONTRAST_ADVERBS:
            return self._different_adverbs_of_same_category(tok, _CONTRAST_ADVERBS) + list(_CONTRAST_EXPRESSIONS)
        if tok in _EMPHASIS_ADVERBS:
            return self._different_adverbs_of_same_category(tok, _EMPHASIS_ADVERBS)
        if tok in _EXPLAIN_ADVERBS:
            return self._different_adverbs_of_same_category(tok, _EXPLAIN_ADVERBS)
        return []

    @staticmethod
    def _different_adverbs_of_same_category(adverb, adverbs_of_category):
        """Gives suggestions to replace the given adverb: the other adverbs of
        the category"""
        return [adv for adv in adverbs_of_category if adv != adverb]


class EnglishWrongWordInContextRule(WrongWordInContextRule):
    """Port of org.languagetool.rules.en.EnglishWrongWordInContextRule:
    commonly confused words (/en/wrongWordInContext.txt)."""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('I have <marker>proscribed</marker> you a course of antibiotics.',
                              'I have <marker>prescribed</marker> you a course of antibiotics.')

    def get_category_string(self):
        return 'Commonly Confused Words'

    def get_id(self):
        return 'ENGLISH_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'commonly confused words: $match'

    def get_filename(self):
        return '/en/wrongWordInContext.txt'

    def get_message_string(self):
        return "Possibly confused word: Did you mean <suggestion>$SUGGESTION</suggestion> instead of '$WRONGWORD'?"

    def get_short_message_string(self):
        return 'Possibly confused word'

    def get_long_message_string(self):
        return ('Possibly confused word: Did you mean <suggestion>$SUGGESTION</suggestion> (= $EXPLANATION_SUGGESTION) '
                "instead of '$WRONGWORD' (= $EXPLANATION_WRONGWORD)?")


def _repeated_words_anti_patterns():
    b = PatternTokenBuilder
    return [
        [b().cs_token('need').match_inflected_forms().build(), token('to')],  # "I still need -> require to sign in"
        [b().token_regex('solve(s|d|ing)?').set_skip(3).build(),  # "solve the problem" is a unique collocation
         token_regex('problems?')],  # "solve the issue|concern|difficulty" sounds bizarre
        [pos_regex('SENT_START|PCT'), token('no'), token('problem'), pos('PCT')],  # "No problem, I'm not in a rush."
        [token_regex('math|word'), token_regex('problems?')],  # "math/word problem"
        [token_regex('as'), token_regex('a'), token_regex('whole')],  # "doesn't apply to the group as a whole"
        [token('more'), token('often'), token('than'), token('not')],
        [token('often'), token('times')],
        [token_regex('details?|facts?|it|journals?|questions?|research|results?|study|studies|this|these|those|'
                     'which'),
         b().pos('RB').min(0).build(),
         b().cs_token('suggest').match_inflected_forms().build()],
        [b().cs_token('form').match_inflected_forms().build(),  # "form in the bloodstream"
         pos_regex('IN|PCT|RP|TO|SENT_END')],
        [b().token_regex('bonds?|crystals?|ions?|rocks?|.*valence').set_skip(10).build(),
         b().cs_token('form').match_inflected_forms().build()],
        [b().token_regex('form(s|ed|ing)?').set_skip(10).build(),
         token_regex('bonds?|crystals?|ions?|rocks?|.*valence')],
        [token('interesting'), token_regex('facts?|things?')],
        [token('several'), token_regex('hundreds?|thousands?|millions?')],
        [token('must'), token('be'), token('nice')],
        [token('nice'), token('day')],
        [token('nice'), token('to'), b().token('meet').min(0).build(), pos_regex('PRP_O.*')],
        [b().cs_token('be').match_inflected_forms().build(),  # nice and plump
         token('nice'), token('and'), pos('JJ'), pos_regex('PCT|SENT_END')],
        [pos_regex('P?DT|PRP$.*'),  # the proposed agreement
         token('proposed'), pos_regex('N.*')],
        [b().cs_token('propose').match_inflected_forms().build(), token_regex('to|marriage')],
        [token('too'), token('literally')],
        [token('literally'), token('and'), token('figuratively')],
        [token('literally'), token('everything')],
        [token('literally'), pos_regex('PCT|SENT_END')],
        [pos_regex('CC'), token('maybe')],  # "Or maybe it's because I have eyes that see!"
    ]


_repeated_words_lock = threading.Lock()
_repeated_words_anti_patterns_cache = []


class EnglishRepeatedWordsRule(AbstractRepeatedWordsRule):
    """Port of org.languagetool.rules.en.EnglishRepeatedWordsRule: words of
    /en/synonyms.txt repeated within a short distance, with synonyms as
    suggestions (picky)."""

    def __init__(self, messages, language=None):
        super().__init__(messages, _american_english())
        self.tags = ['picky']
        # (Java sets URLs for the ids EN_REPEATEDWORDS_DEFINITELY and EN_REPEATEDWORDS_CHOOSE, which are never
        # the id of this rule)

    def get_anti_patterns(self):
        with _repeated_words_lock:
            if not _repeated_words_anti_patterns_cache:
                _repeated_words_anti_patterns_cache.append(make_anti_patterns(_repeated_words_anti_patterns(),
                                                                              _american_english()))
            return _repeated_words_anti_patterns_cache[0]

    def get_message(self):
        return ('This word has been used in one of the immediately preceding sentences. Using a synonym could make '
                'your text more interesting to read, unless the repetition is intentional.')

    def get_description(self):
        return 'Suggest synonyms for repeated words.'

    def get_words_to_check(self):
        return load_repeated_words(_rules_file(self.language, '/en/synonyms.txt'))

    def get_short_message(self):
        return 'Style: repeated word'

    def get_synthesizer(self):
        return _english().synthesizer  # EnglishSynthesizer.INSTANCE

    def is_exception(self, tokens, i, sent_start, is_capitalized, is_all_upper):
        if is_all_upper or (is_capitalized and not sent_start):
            return True
        return tokens[i].has_pos_tag_starting_with('NNP')


class StyleTooOftenUsedVerbRule(AbstractStyleTooOftenUsedWordRule):
    """Port of org.languagetool.rules.en.StyleTooOftenUsedVerbRule (default
    off)"""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, 5)

    def get_limit_message(self, limit):
        return ('The verb is used more than ' + str(limit) + '% times of all verbs. '
                'It may be better to replace it with a synonym.')

    def get_id(self):
        return 'TOO_OFTEN_USED_VERB_EN'

    def get_description(self):
        return 'Statistical Style Analysis: Overused Verb'

    def get_configure_text(self):
        return 'Show when a verb is used more often than ...% of all verbs:'

    def is_to_counted_word(self, atr):
        return atr.has_pos_tag_starting_with('VB')

    def is_exception(self, tokens, n):
        atr = tokens[n]
        return (atr.has_any_lemma('be', 'have', 'do') or atr.has_pos_tag_starting_with('IN')
                or atr.has_pos_tag_starting_with('NN'))

    def to_added_lemma(self, atr):
        return self.get_lemma_for_pos_tag_starts_with('VB', atr)


class StyleTooOftenUsedNounRule(AbstractStyleTooOftenUsedWordRule):
    """Port of org.languagetool.rules.en.StyleTooOftenUsedNounRule (default
    off)"""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, 5)

    def get_limit_message(self, limit):
        return ('The noun is used more than ' + str(limit) + '% times of all nouns. '
                'It may be better to replace it with a synonym.')

    def get_id(self):
        return 'TOO_OFTEN_USED_NOUN_EN'

    def get_description(self):
        return 'Statistical Style Analysis: Overused Noun'

    def get_configure_text(self):
        return 'Show when a noun is used more often than ...% of all nouns:'

    def is_to_counted_word(self, atr):
        return atr.has_pos_tag_starting_with('NN')

    def is_exception(self, tokens, n):
        atr = tokens[n]
        return (atr.has_pos_tag_starting_with('NNP') or atr.has_pos_tag_starting_with('IN')
                or atr.has_pos_tag_starting_with('JJ') or atr.has_pos_tag_starting_with('RB')
                or atr.has_pos_tag_starting_with('VB'))

    def to_added_lemma(self, atr):
        return self.get_lemma_for_pos_tag_starts_with('NN', atr)


class StyleTooOftenUsedAdjectiveRule(AbstractStyleTooOftenUsedWordRule):
    """Port of org.languagetool.rules.en.StyleTooOftenUsedAdjectiveRule
    (default off)"""

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, 5)

    def get_limit_message(self, limit):
        return ('The adjective is used more than ' + str(limit) + '% times of all adjectives. '
                'It may be better to replace it with a synonym.')

    def get_id(self):
        return 'TOO_OFTEN_USED_ADJECTIVE_EN'

    def get_description(self):
        return 'Statistical Style Analysis: Overused Adjective'

    def get_configure_text(self):
        return 'Show when a adjective is used more often than ...% of all adjectives:'

    def is_to_counted_word(self, atr):
        return atr.has_pos_tag_starting_with('JJ')

    def is_exception(self, tokens, n):
        atr = tokens[n]
        return (atr.has_pos_tag_starting_with('RB') or atr.has_pos_tag_starting_with('IN')
                or atr.has_pos_tag_starting_with('CD') or atr.has_pos_tag_starting_with('DT')
                or atr.has_pos_tag_starting_with('NN'))

    def to_added_lemma(self, atr):
        return self.get_lemma_for_pos_tag_starts_with('JJ', atr)


class WordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.en.WordCoherencyRule: variant
    spellings of /en/coherency.txt should not be mixed in a text."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _english())
        self.add_example_pair('He likes archaeology. Really? She likes <marker>archeology</marker>, too.',
                              'He likes archaeology. Really? She likes <marker>archaeology</marker>, too.')

    def get_word_map(self):
        return load_word_coherency_data(_rules_file(self.language, '/en/coherency.txt'))

    def get_message(self, word1, word2):
        return ("Do not mix variants of the same word ('" + word1 + "' and '" + word2
                + "') within a single text.")

    def get_id(self):
        return 'EN_WORD_COHERENCY'

    def get_description(self):
        return 'Coherent spelling of words with two admitted variants.'


# --- unit conversion ---

class UnitConversionRule(AbstractUnitConversionRule):
    """Port of org.languagetool.rules.en.UnitConversionRule: the
    AbstractUnitConversionRule with English unit names and the number
    format of Locale.ENGLISH (picky)."""

    _format = DecimalFormat(maximum_fraction_digits=2)

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.tags = ['picky']
        add = self.add_unit
        add('miles per hour', MILE.divide(HOUR), 'miles per hour', 1, False)
        add('kilograms?', KILOGRAM, 'kilogram', 1e0, True)
        add('grams?', KILOGRAM, 'gram', 1e-3, True)
        add('tons?', KILOGRAM, 'ton', 1e3, True)
        add('pounds?', POUND, 'pounds', 1, False)
        add('ounces?', OUNCE, 'ounces', 1, False)
        add('feet', FEET, 'feet', 1, False)
        add('miles?', MILE, 'miles', 1, False)
        add('yards?', YARD, 'yards', 1, False)
        add('inch(es)?', INCH, 'inches', 1, False)
        add('(?:degrees?)? Fahrenheit', FAHRENHEIT, 'degree Fahrenheit', 1, False)
        add('(?:degrees?)? Celsius', CELSIUS, 'degree Celsius', 1, True)

    def get_id(self):
        return 'METRIC_UNITS_EN_GENERAL'

    def get_description(self):
        return 'Suggests or checks conversion of units to their metric equivalents.'

    def get_number_format(self):
        return self._format


class UnitConversionRuleImperial(UnitConversionRule):
    """Port of org.languagetool.rules.en.UnitConversionRuleImperial: with
    the British metric unit names, imperial volumes and the number format
    of Locale.UK."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        add = self.add_unit
        add('(kilometre|kilometer)s? per hour', KILOMETRE_PER_HOUR, 'kilometres per hour', 1, True)
        add('kilomet(re|er)s?', METRE, 'kilometres', 1e3, True)
        add('met(re|er)s?', METRE, 'metres', 1e0, True)
        add('decimet(re|er)s?', METRE, 'decimetres', 1e-1, False)  # Metric, but not commonly used
        add('centimet(re|er)s?', METRE, 'centimetres', 1e-2, True)
        add('millimet(re|er)s?', METRE, 'micrometres', 1e-3, True)
        add('micromet(re|er)s?', METRE, 'micrometres', 1e-6, True)
        add('nanomet(re|er)s?', METRE, 'nanometres', 1e-9, True)
        add('square met(re|er)s?', SQUARE_METRE, 'square metres', 1, True)
        add('square kilomet(re|er)s?', SQUARE_METRE, 'square kilometres', 1e6, True)
        add('square decimet(re|er)s?', SQUARE_METRE, 'square decimetres', 1e-2, False)  # Metric, not commonly used
        add('square centimet(re|er)s?', SQUARE_METRE, 'square centimetres', 1e-4, True)
        add('square millimet(re|er)s?', SQUARE_METRE, 'square millimetres', 1e-6, True)
        add('square micromet(re|er)s?', SQUARE_METRE, 'square micrometres', 1e-12, True)
        add('square nanomet(re|er)s?', SQUARE_METRE, 'square nanometres', 1e-18, True)
        add('cubic met(re|er)s?', CUBIC_METRE, 'cubic metres', 1, True)
        add('cubic kilomet(re|er)s?', CUBIC_METRE, 'cubic kilometres', 1e9, True)
        add('cubic decimet(re|er)s?', CUBIC_METRE, 'cubic decimetres', 1e-3, False)  # Metric, not commonly used
        add('cubic centimet(re|er)s?', CUBIC_METRE, 'cubic centimetres', 1e-6, True)
        add('cubic millimet(re|er)s?', CUBIC_METRE, 'cubic millimetres', 1e-9, True)
        add('cubic micromet(re|er)s?', CUBIC_METRE, 'cubic micrometres', 1e-18, True)
        add('cubic nanomet(re|er)s?', CUBIC_METRE, 'cubic nanometres', 1e-27, True)
        add('lit(re|er)s?', LITRE, 'litres', 1, True)
        add('millilit(re|er)s?', LITRE, 'millilitres', 1e-3, True)
        add('qt\\.', IMP_QUART, 'qt.', 1, False)
        add('gal', IMP_GALLON, 'gal', 1, False)
        add('pt', IMP_PINT, 'pt', 1, False)
        add('(?:fl.? oz.?|oz. fl.)', IMP_FL_OUNCE, 'fl oz', 1, False)
        add('quarts?', IMP_QUART, 'quarts', 1, False)
        add('gallons?', IMP_GALLON, 'gallons', 1, False)
        add('pints?', IMP_PINT, 'pints', 1, False)
        add('(fluid )?ounces?', IMP_FL_OUNCE, 'fluid ounces', 1, False)

    def get_id(self):
        return 'METRIC_UNITS_EN_IMPERIAL'


class UnitConversionRuleUS(UnitConversionRule):
    """Port of org.languagetool.rules.en.UnitConversionRuleUS: with the
    American metric unit names, US volumes and the number format of
    Locale.US."""

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.url = 'https://languagetool.org/insights/post/imperial-metric-system/'
        add = self.add_unit
        add('(kilometre|kilometer)s? per hour', KILOMETRE_PER_HOUR, 'kilometers per hour', 1, True)
        add('kilomet(re|er)s?', METRE, 'kilometers', 1e3, True)
        add('met(re|er)s?', METRE, 'meters', 1e0, True)
        add('decimet(re|er)s?', METRE, 'decimeters', 1e-1, False)  # Metric, but not commonly used
        add('centimet(re|er)s?', METRE, 'centimeters', 1e-2, True)
        add('millimet(re|er)s?', METRE, 'micrometers', 1e-3, True)
        add('micromet(re|er)s?', METRE, 'micrometers', 1e-6, True)
        add('nanomet(re|er)s?', METRE, 'nanometers', 1e-9, True)
        add('square met(re|er)s?', SQUARE_METRE, 'square meters', 1, True)
        add('square kilomet(re|er)s?', SQUARE_METRE, 'square kilometers', 1e6, True)
        add('square decimet(re|er)s?', SQUARE_METRE, 'square decimeters', 1e-2, False)  # Metric, not commonly used
        add('square centimet(re|er)s?', SQUARE_METRE, 'square centimeters', 1e-4, True)
        add('square millimet(re|er)s?', SQUARE_METRE, 'square millimeters', 1e-6, True)
        add('square micromet(re|er)s?', SQUARE_METRE, 'square micrometers', 1e-12, True)
        add('square nanomet(re|er)s?', SQUARE_METRE, 'square nanometers', 1e-18, True)
        add('cubic met(re|er)s?', CUBIC_METRE, 'cubic meters', 1, True)
        add('cubic kilomet(re|er)s?', CUBIC_METRE, 'cubic kilometers', 1e9, True)
        add('cubic decimet(re|er)s?', CUBIC_METRE, 'cubic decimeters', 1e-3, False)  # Metric, not commonly used
        add('cubic centimet(re|er)s?', CUBIC_METRE, 'cubic centimeters', 1e-6, True)
        add('cubic millimet(re|er)s?', CUBIC_METRE, 'cubic millimeters', 1e-9, True)
        add('cubic micromet(re|er)s?', CUBIC_METRE, 'cubic micrometers', 1e-18, True)
        add('cubic nanomet(re|er)s?', CUBIC_METRE, 'cubic nanometers', 1e-27, True)
        add('lit(re|er)s?', LITRE, 'liters', 1, True)
        add('millilit(re|er)s?', LITRE, 'milliliters', 1e-3, True)
        add('qt\\.', US_QUART, 'qt.', 1, False)
        add('gal', US_GALLON, 'gal', 1, False)
        add('pt', US_PINT, 'pt', 1, False)
        add('cup', US_CUP, 'cups', 1, False)
        add('(?:fl.? oz.?|oz. fl.)', US_FL_OUNCE, 'fl oz', 1, False)
        add('quarts?', US_QUART, 'quarts', 1, False)
        add('gallons?', US_GALLON, 'gallons', 1, False)
        add('pints?', US_PINT, 'pints', 1, False)
        add('cups?', US_CUP, 'cups', 1, False)
        add('(fluid )?ounces?', US_FL_OUNCE, 'fluid ounces', 1, False)

    def get_id(self):
        return 'METRIC_UNITS_EN_US'
