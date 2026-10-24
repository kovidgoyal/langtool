"""English rule filters (port of the filters of org.languagetool.rules.en:
AdvancedSynthesizerFilter, AdverbFilter, DateCheckFilter,
YMDDateCheckFilter, FutureDateFilter, NewYearDateFilter,
YMDNewYearDateFilter and DateFilterHelper,
EnglishConvertToSentenceCaseFilter, EnglishNumberInWordFilter,
EnglishPartialPosTagFilter, NoDisambiguationEnglishPartialPosTagFilter,
EnglishSuppressMisspelledSuggestionsFilter, FindSuggestionsFilter and
OrdinalSuffixFilter)."""

from ... import jregex
from ...analysis import AnalyzedSentence
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckWithSuggestionsFilter,
                                   AbstractFindSuggestionsFilter, AbstractFutureDateFilter, AbstractNewYearDateFilter,
                                   AbstractNumberInWordFilter, AbstractSuppressMisspelledSuggestionsFilter,
                                   ConvertToSentenceCaseFilter, PartialPosTagFilter, YMDDateHelper,
                                   SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RuleFilter
from ...tools import is_numeric, trim_special_characters


def _english():
    """Languages.getLanguageForShortCode("en")"""
    from ...api import get_language
    return get_language('en')


def _american_english():
    """AmericanEnglish.getInstance()"""
    from ...api import get_language
    return get_language('en-US')


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.en.AdvancedSynthesizerFilter:
    synthesize suggestions using the lemma from one token (lemma_from) and
    the POS tag from another one (postag_from)."""


_ADVERB_TO_ADJECTIVE = {
    # irregular ones: well, fast, hard, late, early, daily, straight; the rest are regular ones
    # ("twice" -> "second" is a special case; Java puts "jokily" twice, the second value wins)
    'well': 'good', 'fast': 'fast', 'hard': 'hard', 'late': 'late', 'early': 'early', 'daily': 'daily',
    'straight': 'straight', 'simply': 'simple', 'cheaply': 'cheap', 'quickly': 'quick', 'slowly': 'slow',
    'easily': 'easy', 'angrily': 'angry', 'happily': 'happy', 'luckily': 'lucky', 'terribly': 'terrible',
    'tragically': 'tragic', 'economically': 'economic', 'greatly': 'great', 'highly': 'high', 'generally': 'general',
    'differently': 'different', 'rightly': 'right', 'largely': 'large', 'really': 'real',
    'philosophically': 'philosophical', 'directly': 'direct', 'clearly': 'clear', 'merely': 'mere',
    'exactly': 'exact', 'recently': 'recent', 'rapidly': 'rapid', 'suddenly': 'sudden', 'extremely': 'extreme',
    'properly': 'proper', 'politically': 'political', 'probably': 'probable', 'self-consciously': 'self-conscious',
    'successfully': 'successful', 'unusually': 'unusual', 'obviously': 'obvious', 'currently': 'current',
    'residentially': 'residential', 'fully': 'full', 'accidentally': 'accidental', 'medicinally': 'medicinal',
    'automatically': 'automatic', 'completely': 'complete', 'chronologically': 'chronological',
    'accurately': 'accurate', 'necessarily': 'necessary', 'temporarily': 'temporary', 'significantly': 'significant',
    'hastily': 'hasty', 'immediately': 'immediate', 'rarely': 'rare', 'totally': 'total', 'literally': 'literal',
    'gently': 'gentle', 'finally': 'final', 'increasingly': 'increasing', 'decreasingly': 'decreasing',
    'considerably': 'considerable', 'effectively': 'effective', 'briefly': 'brief', 'exceedingly': 'exceeding',
    'physically': 'physical', 'enthusiastically': 'enthusiastic', 'incredibly': 'incredible',
    'permanently': 'permanent', 'entirely': 'entire', 'surely': 'sure', 'positively': 'positive',
    'negatively': 'negative', 'devastatingly': 'devastating', 'relatively': 'relative', 'absolutely': 'absolute',
    'socially': 'social', 'industriously': 'industrious', 'solely': 'sole', 'asynchronously': 'asynchronous',
    'fortunately': 'fortunate', 'unfortunately': 'unfortunate', 'ideally': 'ideal', 'privately': 'private',
    'unreasonably': 'unreasonable', 'personally': 'personal', 'basically': 'basic', 'definitely': 'definite',
    'potentially': 'potential', 'manually': 'manual', 'continuously': 'continuous', 'sadly': 'sad',
    'eventually': 'eventual', 'possibly': 'possible', 'visually': 'visual', 'predominantly': 'predominant',
    'predominately': 'predominant', 'quietly': 'quiet', 'slightly': 'slight', 'cleverly': 'clever',
    'roughly': 'rough', 'environmentally': 'environmental', 'geographically': 'geographical', 'usually': 'usual',
    'normally': 'normal', 'deliciously': 'delicious', 'steadily': 'steady', 'actively': 'active',
    'schematically': 'schematic', 'mindfully': 'mindful', 'statistically': 'statistical', 'culturally': 'cultural',
    'vicariously': 'vicarious', 'vividly': 'vivid', 'partially': 'partial', 'unduly': 'undue',
    'seriously': 'serious', 'non-verbally': 'non-verbal', 'nonverbally': 'nonverbal', 'verbally': 'verbal',
    'shortly': 'short', 'mildly': 'mild', 'secretly': 'secret', 'especially': 'especial', 'specially': 'special',
    'previously': 'previous', 'whitely': 'white', 'traditionally': 'traditional', 'individually': 'individual',
    'carefully': 'careful', 'essentially': 'essential', 'originally': 'original', 'alarmingly': 'alarming',
    'newly': 'new', 'wrongfully': 'wrongful', 'structurally': 'structural', 'globally': 'global',
    'pacifically': 'pacific', 'seemingly': 'seeming', 'seamlessly': 'seamless', 'sustainably': 'sustainable',
    'momentarily': 'momentary', 'coldly': 'cold', 'densely': 'dense', 'grimly': 'grim', 'calmly': 'calm',
    'racially': 'racial', 'widely': 'wide', 'heavily': 'heavy', 'authentically': 'authentic', 'honestly': 'honest',
    'desperately': 'desperate', 'immensely': 'immense', 'apparently': 'apparent',
    'straightforwardly': 'straightforward', 'anatomically': 'anatomical', 'uniquely': 'unique',
    'systemically': 'systemic', 'jokily': 'joking', 'critically': 'critical', 'equally': 'equal',
    'strongly': 'strong', 'purposely': 'intentional', 'thoroughly': 'thorough', 'outwardly': 'outward',
    'horizontally': 'horizontal', 'vertically': 'vertical', 'technically': 'technical', 'swiftly': 'swift',
    'accessibly': 'accessible', 'occasionally': 'occasional', 'specifically': 'specific', 'subtly': 'subtle',
    'actually': 'actual', 'particularly': 'particular', 'gloomily': 'gloomy', 'nicely': 'nice',
    'progressively': 'progressive', 'genuinely': 'genuine', 'characteristically': 'characteristic', 'deeply': 'deep',
    'spiritually': 'spiritual', 'purely': 'pure', 'satisfyingly': 'satisfying', 'indolently': 'indolent',
    'obliquely': 'oblique', 'preferably': 'preferable', 'oddly': 'odd', 'professionally': 'professional',
    'indispensably': 'indispensable', 'dispensably': 'dispensable', 'consistently': 'consistent', 'truly': 'true',
    'commonly': 'common', 'safely': 'safe', 'evolutionarily': 'evolutionary', 'internally': 'internal',
    'magically': 'magical', 'annually': 'annual', 'brightly': 'bright', 'officially': 'official',
    'inofficially': 'inofficial', 'perfectly': 'perfect', 'overly': 'over', 'tropically': 'tropical',
    'brilliantly': 'brilliant', 'exclusively': 'exclusive', 'commercially': 'commercial',
    'mischievously': 'mischievous', 'weirdly': 'weird', 'routinely': 'routine', 'gruffly': 'gruff',
    'naturally': 'natural', 'lightly': 'light', 'haphazardly': 'haphazard', 'lovingly': 'loving', 'sagely': 'sage',
    'systematically': 'systematical', 'academically': 'academical', 'jokingly': 'joking', 'primarily': 'primary',
    'secondarily': 'secondary', 'peacefully': 'peaceful', 'thankfully': 'thankful', 'reliably': 'reliable',
    'unreliably': 'unreliable', 'infinitesimally': 'infinitesimal', 'hugely': 'huge', 'strictly': 'strict',
    'morally': 'moral', 'involuntarily': 'involuntary', 'voluntarily': 'voluntary', 'vanishingly': 'vanishing',
    'typically': 'typical', 'playfully': 'playful', 'wonderfully': 'wonderful', 'roguishly': 'roguish',
    'emotionally': 'emotional', 'efficiently': 'efficient', 'unkindly': 'unkind', 'mentally': 'mental',
    'credibly': 'credible', 'seductively': 'seductive', 'rashly': 'rash', 'outwards': 'outward',
    'periodically': 'periodical', 'comparatively': 'comparative', 'confidentially': 'confidential',
    'dominantly': 'dominant', 'forcibly': 'forcible', 'formerly': 'former', 'financially': 'financial',
    'urgently': 'urgent', 'inherently': 'inherent', 'historically': 'historical', 'tightly': 'tight',
    'greedily': 'greedy', 'fluently': 'fluent', 'ordinarily': 'ordinary', 'inevitably': 'inevitable',
    'partly': 'partial', 'liquidly': 'liquid', 'supremely': 'supreme', 'initially': 'initial', 'unjustly': 'unjust',
    'justly': 'just', 'plausibly': 'plausible', 'amiably': 'amiable', 'massively': 'massive', 'lowly': 'low',
    'notoriously': 'notorious', 'meaningfully': 'meaningful', 'approximately': 'approximate',
    'extraordinarily': 'extraordinary', 'warmly': 'warm', 'nearly': 'near', 'strategically': 'strategical',
    'endlessly': 'endless', 'virtually': 'virtual', 'regularly': 'regular', 'deliberately': 'deliberate',
    'reasonably': 'reasonable', 'similarly': 'similar', 'flexibly': 'flexible', 'softly': 'soft',
    'responsibly': 'responsible', 'irresponsibly': 'irresponsible', 'sweetly': 'sweet', 'comfortably': 'comfortable',
    'uncomfortably': 'uncomfortable', 'intricately': 'intricate', 'unnecessarily': 'unnecessary',
    'obstinately': 'obstinate', 'reportedly': 'reported', 'loosely': 'loose', 'profusely': 'profuse',
    'mortally': 'mortal', 'dynamically': 'dynamical', 'illegally': 'illegal', 'legally': 'legal',
    'undoubtedly': 'undoubted', 'humanly': 'human', 'likewise': 'similar', 'intrinsically': 'intrinsic',
    'substantially': 'substantial', 'suspiciously': 'suspicious', 'generationally': 'generational', 'loudly': 'loud',
    'moderately': 'moderate', 'gravely': 'grave', 'temporally': 'temporal', 'digitally': 'digital', 'finely': 'fine',
    'respectfully': 'respectful', 'questioningly': 'questioning', 'diagonally': 'diagonal',
    'additionally': 'additional', 'sexually': 'sexual', 'remarkably': 'remarkable', 'acutely': 'acute',
    'linearly': 'linear', 'perfunctorily': 'perfunctory', 'unbelievably': 'unbelievable', 'merrily': 'merry',
    'beneath': 'below', 'lest': 'least', 'either': 'other', 'nasally': 'nasal', 'concretely': 'concrete',
    'intuitively': 'intuitive', 'please': 'pleasing', 'intermediately': 'intermediate', 'powerfully': 'powerful',
    'fairly': 'fair', 'wholly': 'whole', 'keenly': 'keen', 'unconsciously': 'unconscious',
    'consciously': 'conscious', 'humanely': 'humane', 'honorably': 'honorable', 'rudely': 'rude',
    'incorrectly': 'incorrect', 'correctly': 'correct', 'mistakenly': 'mistaken', 'wrongly': 'wrong',
    'morosely': 'morose', 'worryingly': 'worrying', 'drastically': 'drastical', 'willingly': 'willing',
    'additively': 'additive', 'drolly': 'droll', 'statically': 'statical', 'hopefully': 'hopeful',
    'untruthfully': 'untruthful', 'truthfully': 'truthful', 'attractively': 'attractive', 'supposedly': 'supposed',
    'overwhelmingly': 'overwhelming', 'imperfectly': 'imperfect', 'deftly': 'deft', 'wildly': 'wild',
    'sheepishly': 'sheepish', 'hotly': 'hot', 'genetically': 'genetic', 'inexplicably': 'inexplicable',
    'explicably': 'explicable', 'domestically': 'domestical', 'invisibly': 'invisible', 'visibly': 'visible',
    'noteworthily': 'noteworthy', 'unexpectably': 'unexpectable', 'expectably': 'expectable',
    'foreseeably': 'foreseeable', 'unforeseeably': 'unforeseeable', 'distinctly': 'distinct',
    'unequivocally': 'unequivocal', 'signally': 'signal', 'medically': 'medical', 'certainly': 'certain',
    'beautifully': 'beautiful', 'firmly': 'firm', 'electrically': 'electrical', 'gradually': 'gradual',
    'grossly': 'gross', 'memorably': 'memorable', 'unmemorably': 'unmemorable', 'shelly': 'shell',
    'strangely': 'strange', 'unhealthily': 'unhealthy', 'healthily': 'healthy', 'harshly': 'harsh',
    'proudly': 'proud', 'lately': 'late', 'remotely': 'remote', 'longly': 'long', 'politely': 'polite',
    'ethically': 'ethical', 'noticeably': 'noticeable', 'unnoticeably': 'unnoticeable', 'consequently': 'consequent',
    'snugly': 'snug', 'mainly': 'main', 'popularly': 'popular', 'improperly': 'improper', 'deliverly': 'delivery',
    'rushingly': 'rushing', 'gravitationally': 'gravitational', 'cruelly': 'cruel', 'optimally': 'optimal',
    'fictionally': 'fictional', 'manageably': 'manageable', 'unmanageably': 'unmanageable',
    'fashionably': 'fashionable', 'secondly': 'second', 'thirdly': 'third', 'curtly': 'curt',
    'secretively': 'secretive', 'surprisingly': 'surprising', 'sociologically': 'sociological', 'severely': 'severe',
    'ruffianly': 'ruffian', 'bigly': 'big', 'frequently': 'frequent', 'irrationally': 'irrational',
    'rationally': 'rational', 'riotously': 'riotous', 'excruciatingly': 'excruciating', 'intensively': 'intensive',
    'separately': 'separate', 'favorably': 'favorable', 'favourably': 'favourable', 'unfavorably': 'unfavorable',
    'unfavourably': 'unfavourable', 'fittingly': 'fitting', 'orally': 'oral', 'jointly': 'joint',
    'methodically': 'methodical', 'ecologically': 'ecological', 'irrepressibly': 'irrepressible',
    'repressibly': 'repressible', 'heartily': 'hearty', 'smoothly': 'smooth', 'dreamily': 'dreamy',
    'indirectly': 'indirect', 'fascinatingly': 'fascinating', 'scientifically': 'scientific', 'unhappily': 'unhappy',
    'publicly': 'public', 'healthfully': 'healthful', 'uncharacteristically': 'uncharacteristic',
    'genially': 'genial', 'ineludibly': 'ineludible', 'tenderly': 'tender', 'arguably': 'arguable',
    'comparably': 'comparable', 'procedurally': 'procedural', 'interchangeably': 'interchangeable',
    'conceivably': 'conceivable', 'resignedly': 'resigned', 'vehemently': 'vehement', 'horribly': 'horrible',
    'teasingly': 'teasing', 'figuratively': 'figurative', 'excitingly': 'exciting', 'haltingly': 'halting',
    'phonetically': 'phonetic', 'proverbially': 'proverbial', 'informally': 'informal', 'cozily': 'cozy',
    'cosily': 'cosy', 'constantly': 'constant', 'rightfully': 'rightful', 'reluctantly': 'reluctant',
    'externally': 'external', 'intellectually': 'intellectual', 'dramatically': 'dramatic', 'freshly': 'fresh',
    'casually': 'casual', 'unevenly': 'uneven', 'enormously': 'enormous', 'callously': 'callous',
    'imperiously': 'imperious', 'messily': 'messy', 'alternatively': 'alternative', 'gladly': 'glad',
    'adversely': 'adverse', 'petulantly': 'petulant', 'shakily': 'shaky', 'menacingly': 'menacing',
    'consensually': 'consensual', 'bitterly': 'bitter', 'terminally': 'terminal', 'faintly': 'faint',
    'brusquely': 'brusque', 'humbly': 'humble', 'promptly': 'prompt', 'identically': 'identical',
    'militarily': 'military', 'neatly': 'neat', 'insanely': 'insane', 'analytically': 'analytical',
    'firstly': 'first', 'twice': 'second',
}


class AdverbFilter(RuleFilter):
    """Port of org.languagetool.rules.en.AdverbFilter: maps the suggestion
    from adverb to adjective (arguments adverb and noun, the suggestion is
    "<adjective> <noun>"). Also see
    https://www.ef.com/wwen/english-resources/english-grammar/forming-adverbs-adjectives/"""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        adverb = arguments.get('adverb')
        noun = arguments.get('noun')
        adjective = _ADVERB_TO_ADJECTIVE.get(adverb)
        if adjective is not None and adjective != adverb:
            # we can't simply cut off "ly" because of cases like "simply" -> "simple" etc.
            match.set_suggested_replacement(adjective + ' ' + noun)
        return match


# --- DateFilterHelper ---

def _get_day_of_week(day_str):
    """DateFilterHelper.getDayOfWeek(String)"""
    day = trim_special_characters(day_str).lower()
    if day.startswith('su'):
        return SUNDAY
    if day.startswith('mo'):
        return MONDAY
    if day.startswith('tu'):
        return TUESDAY
    if day.startswith('we'):
        return WEDNESDAY
    if day.startswith('th'):
        return THURSDAY
    if day.startswith('fr'):
        return FRIDAY
    if day.startswith('sa'):
        return SATURDAY
    raise RuntimeError("Could not find day of week for '" + day_str + "'")


_DAY_NAMES = {SUNDAY: 'Sunday', MONDAY: 'Monday', TUESDAY: 'Tuesday', WEDNESDAY: 'Wednesday', THURSDAY: 'Thursday',
              FRIDAY: 'Friday', SATURDAY: 'Saturday'}


def _get_day_of_week_name(date):
    """DateFilterHelper.getDayOfWeek(Calendar): the name of the day of week
    (Locale.UK)"""
    return _DAY_NAMES.get(date.day_of_week, '')


_MONTHS = (('jan', 1), ('feb', 2), ('mar', 3), ('apr', 4), ('may', 5), ('jun', 6), ('jul', 7), ('aug', 8),
           ('sep', 9), ('oct', 10), ('nov', 11), ('dec', 12))


def _get_month(month_str):
    """DateFilterHelper.getMonth"""
    mon = trim_special_characters(month_str).lower()
    for prefix, month in _MONTHS:
        if mon.startswith(prefix):
            return month
    raise RuntimeError("Could not find month '" + month_str + "'")


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.en.DateCheckFilter, the English
    localization of AbstractDateCheckWithSuggestionsFilter (with
    DateFilterHelper); suggested days of the month get an ordinal suffix
    if the original has one."""

    def get_day_of_week(self, day_str):
        return _get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return _get_day_of_week_name(date)

    def get_month(self, month_str):
        return _get_month(month_str)

    def get_error_message_wrong_year(self):
        return 'This date is wrong. Did you mean "{currentYear}"?'

    def get_day_str_like_original(self, day, original):
        if is_numeric(original):
            return day
        number = int(day)
        if 11 <= number <= 13:
            return str(number) + 'th'
        last = number % 10
        if last == 1:
            return str(number) + 'st'
        if last == 2:
            return str(number) + 'nd'
        if last == 3:
            return str(number) + 'rd'
        return str(number) + 'th'


class YMDDateCheckFilter(DateCheckFilter):
    """Port of org.languagetool.rules.en.YMDDateCheckFilter: a date filter
    that expects a 'date' argument in the format 'yyyy-mm-dd'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for YMDDateCheckFilter")
        return super().accept_rule_match(match, YMDDateHelper.parse_date(args), pattern_token_pos, pattern_tokens,
                                         token_positions)


class FutureDateFilter(AbstractFutureDateFilter):
    """Port of org.languagetool.rules.en.FutureDateFilter (with
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return _get_month(localized_month)


class NewYearDateFilter(AbstractNewYearDateFilter):
    """Port of org.languagetool.rules.en.NewYearDateFilter (with
    DateFilterHelper)."""

    def get_month(self, localized_month):
        return _get_month(localized_month)


class YMDNewYearDateFilter(NewYearDateFilter):
    """Port of org.languagetool.rules.en.YMDNewYearDateFilter: a new year
    date filter that expects a 'date' argument in the format
    'yyyy-mm-dd'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for YMDDateCheckFilter")
        args = YMDDateHelper.parse_date(args)
        return super().accept_rule_match(YMDDateHelper.correct_date(match, args), args, pattern_token_pos,
                                         pattern_tokens, token_positions)


class EnglishConvertToSentenceCaseFilter(ConvertToSentenceCaseFilter):
    """Port of org.languagetool.rules.en.EnglishConvertToSentenceCaseFilter:
    "me" is not converted."""

    def token_is_exception(self, s):
        return s == 'me'


class EnglishNumberInWordFilter(AbstractNumberInWordFilter):
    """Port of org.languagetool.rules.en.EnglishNumberInWordFilter: the
    misspelling check and the spelling suggestions of the
    MorfologikAmericanSpellerRule (the default spelling rule of en-US, see
    langtool.lang.en.spelling)."""

    def __init__(self, language=None):
        super().__init__(_american_english())

    def is_misspelled(self, word):
        return self.language.get_default_spelling_rule().is_misspelled(word)

    def get_suggestions(self, word):
        return self.language.get_default_spelling_rule().get_spelling_suggestions(word)


class EnglishPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.en.EnglishPartialPosTagFilter: a
    PartialPosTagFilter for English that also runs the disambiguator."""

    def tag(self, token):
        english = _english()
        tags = english.tagger.tag([token])
        disambiguated = english.disambiguator.disambiguate(AnalyzedSentence(list(tags)))
        return list(disambiguated.tokens)


class NoDisambiguationEnglishPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.en.NoDisambiguationEnglishPartialPosTagFilter:
    a PartialPosTagFilter for English that does not run the disambiguator
    (the token is only tagged)."""

    def tag(self, token):
        return _english().tagger.tag([token])


class EnglishSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.en.EnglishSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of the language, see
    langtool.lang.en.spelling)."""


class FindSuggestionsFilter(AbstractFindSuggestionsFilter):
    """Port of org.languagetool.rules.en.FindSuggestionsFilter: the
    suggestions are the similar words of the MorfologikSpeller for the
    tagger dictionary /en/english.dict (with the maximum edit distance 1),
    tagged with the English tagger. There is no synthesizer (as in
    Java)."""

    def get_tagger(self):
        return _english().tagger  # EnglishTagger.INSTANCE

    def get_spelling_suggestions(self, atr):
        from ...spelling import morfologik_suggestion_speller
        return morfologik_suggestion_speller(_english(), '/en/english.dict').find_similar_words(atr.token)


_ORDINAL_PATTERN = jregex.compile('.*(11|12|13)')
_NON_DIGITS = jregex.compile('[^0-9]')


class OrdinalSuffixFilter(RuleFilter):
    """Port of org.languagetool.rules.en.OrdinalSuffixFilter: the suggestion
    (the digits of the first suggestion) gets the right ordinal suffix
    (1st, 2nd, 3rd, 11th...)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        ordinal = jregex.java_replace(_NON_DIGITS, '', match.suggested_replacements[0])
        if _ORDINAL_PATTERN.fullmatch(ordinal):
            match.set_suggested_replacement(ordinal + 'th')
        elif ordinal.endswith('1'):
            match.set_suggested_replacement(ordinal + 'st')
        elif ordinal.endswith('2'):
            match.set_suggested_replacement(ordinal + 'nd')
        elif ordinal.endswith('3'):
            match.set_suggested_replacement(ordinal + 'rd')
        else:
            match.set_suggested_replacement(ordinal + 'th')
        return match
