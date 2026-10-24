"""Port of org.languagetool.tokenizers.uk.UkrainianWordTokenizer."""

from ... import jregex
from ...tools import java_trim

_I = jregex.IGNORECASE  # Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE
_U = jregex.UNICODE_CHARACTER_CLASS

_SPLIT_CHARS = (
    '(!{2,3}|\\?{2,3}|\\.{3}|[!?][!?.]{1,2}'
    '|[ \u00A0\\n\\r\\t'
    ',.;!?—―:()\\[\\]{}<>/|\\\\…°$€₴=№§¿¡~×]'
    '|%(?![-–][а-яіїєґ])'  # allow 5%-й
    '|(?<!\uE109)["«»„”“]'  # quotes have special cases
    '|(?<=[а-яіїєґА-ЯІЇЄҐ])[¹²³⁰-⁹]'  # superscript for regular words only
    # preserve * inside words (sometimes used instead of apostrophe or to mask profane words)
    # but split if it's the beginning or end of the word (often used for mark-up and footnotes)
    '|(?<![а-яіїєґА-ЯІЇЄҐa-zA-Z])[_*]+'
    '|[_*]+(?![а-яіїєґА-ЯІЇЄҐa-zA-Z0-9])'
    '|[\u2000-\u200F'
    '‚†-\u202F‰-\u206F'
    '␀-⟿'  # Control Pictures
    '↵'  # wikipedia: ↵
    '\U0001F000-\U0001FFFF'  # Emojis
    '\uF000-\uFFFF'  # private unicode area: U+E000..U+F8FF
    '\uE110])(?!\uE120)')

_SPLIT_CHARS_REGEX = jregex.compile(_SPLIT_CHARS)

# for handling exceptions
_DECIMAL_COMMA_SUBST = '\uE001'  # some unused character to hide comma in decimal number temporary for tokenizer run
_NON_BREAKING_SPACE_SUBST = '\uE002'
_NON_BREAKING_DOT_SUBST = '\uE003'  # some unused character to hide dot in date temporary for tokenizer run
_NON_BREAKING_COLON_SUBST = '\uE004'
_LEFT_BRACE_SUBST = '\uE005'
_RIGHT_BRACE_SUBST = '\uE006'
_NON_BREAKING_SLASH_SUBST = '\uE007'  # hide slash in с/г
_LEFT_ANGLE_SUBST = '\uE008'
_RIGHT_ANGLE_SUBST = '\uE009'
_SLASH_SUBST = '\uE010'
_NON_BREAKING_PLACEHOLDER = '\uE109'
_BREAKING_PLACEHOLDER = '\uE110'
_NON_BREAKING_PLACEHOLDER2 = '\uE120'

_WEIRD_APOSTROPH_PATTERN = jregex.compile('([бвджзклмнпрстфхш])(["”‟`´])([єїюя])', _I)
WORDS_WITH_BRACKETS_PATTERN = jregex.compile('([а-яіїєґ])\\[([а-яіїєґ]+)\\]', _I)

# decimal comma between digits
_DECIMAL_COMMA_PATTERN = jregex.compile('([\\d]),([\\d])', _I)
_DECIMAL_COMMA_REPL = '$1' + _DECIMAL_COMMA_SUBST + '$2'

# space between digits
_DECIMAL_SPACE_PATTERN = jregex.compile('(?<=^|[\\h\\v(])\\d{1,3}([\\h][\\d]{3})+(?=[\\h\\v(]|$)', _I)

# numbers with n-dash
_DASH_NUMBERS_PATTERN = jregex.compile('([IVXІХ]+)([–-])([IVXІХ]+)')
_DASH_NUMBERS_REPL = '$1' + _BREAKING_PLACEHOLDER + '$2' + _BREAKING_PLACEHOLDER + '$3'
_N_DASH_SPACE_PATTERN = jregex.compile('([а-яіїєґa-z0-9])(–\\h)(?!(та|чи|і|й)[\\h\\v])', _I)
_N_DASH_SPACE_PATTERN2 = jregex.compile('([\\h.,;!?]–)([а-яіїєґa-z])', _I)
_N_DASH_SPACE_REPL = '$1' + _BREAKING_PLACEHOLDER + '$2'

# dots in numbers
_DOTTED_NUMBERS_PATTERN = jregex.compile('([\\d])\\.([\\d])')
_DOTTED_NUMBERS_PATTERN3 = jregex.compile('([\\d])\\.([\\d]+)\\.([\\d])')

# colon in numbers
_COLON_NUMBERS_PATTERN = jregex.compile('([\\d]):([\\d])')
_COLON_NUMBERS_REPL = '$1' + _NON_BREAKING_COLON_SUBST + '$2'

# braces in words
_BRACE_IN_WORD_PATTERN = jregex.compile("([а-яіїєґ])\\(([а-яіїєґ']+)\\)", _I)

# Pattern.CASE_INSENSITIVE only (ASCII)
_XML_TAG_PATTERN = jregex.compile('(?i)<(/?[a-z_]+/?)>')

# tokenize initials with dot before last name, e.g. "А.", "Ковальчук"
_INITIALS_DOT_PATTERN_SP_2 = jregex.compile(
    "([А-ЯІЇЄҐ])\\.([\\h\\v]{0,5}[А-ЯІЇЄҐ])\\.([\\h\\v]{0,5}[А-ЯІЇЄҐ][а-яіїєґ']+)")
_INITIALS_DOT_PATTERN_SP_1 = jregex.compile("([А-ЯІЇЄҐ])\\.([\\h\\v]{0,5}[А-ЯІЇЄҐ][а-яіїєґ']+)")

# tokenize initials with dot after last name, e.g.  "Ковальчук", "А."
_INITIALS_DOT_PATTERN_RSP_2 = jregex.compile("([А-ЯІЇЄҐ][а-яіїєґ']+)([\\h\\v]?[А-ЯІЇЄҐ])\\.([\\h\\v]?[А-ЯІЇЄҐ])\\.")
_INITIALS_DOT_PATTERN_RSP_1 = jregex.compile("([А-ЯІЇЄҐ][а-яіїєґ']+)([\\h\\v]?[А-ЯІЇЄҐ])\\.")

_INITIALS_DOT_REPL_SP_2 = ('$1' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER + '$2' + _NON_BREAKING_DOT_SUBST +
                           _BREAKING_PLACEHOLDER + '$3')
_INITIALS_DOT_REPL_SP_1 = '$1' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER + '$2'
_INITIALS_DOT_REPL_RSP_2 = ('$1' + _BREAKING_PLACEHOLDER + '$2' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER +
                            '$3' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER)
_INITIALS_DOT_REPL_RSP_1 = '$1' + _BREAKING_PLACEHOLDER + '$2' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER

# abbreviation dot
_ABBR_DOT_VO_PATTERN1 = jregex.compile('\\b([вВу])\\.([\\h\\v]*о)\\.', _U)
_ABBR_DOT_VO_PATTERN2 = jregex.compile('\\b(к)\\.([\\h\\v]*с)\\.', _U)
_ABBR_DOT_VO_PATTERN3 = jregex.compile('\\b(ч|ст)\\.([\\h\\v]*л)\\.', _U)
_ABBR_DOT_TYS_PATTERN1 = jregex.compile('([0-9IІ][\\h\\v]+)(тис|арт)\\.')
_ABBR_DOT_TYS_PATTERN2 = jregex.compile('(тис|арт)\\.([\\h\\v]+[а-яіїєґ0-9])')
_ABBR_DOT_VYD_PATTERN = jregex.compile('([0-9IІVXХ](-[а-яєі]+)?[\\h\\v]+)(вид)\\.')
_ABBR_DOT_ART_PATTERN = jregex.compile('([Аа]рт|[Мм]ал|[Рр]ис|[Сс]пр)\\.([\\h]*(№[\\h]*)?[0-9])')
_ABBR_DOT_MAN_PATTERN = jregex.compile('(Ман)\\.([\\h]*(Сіті|[Юю]н))')
_ABBR_DOT_LAT_PATTERN = jregex.compile("([^а-яіїєґА-ЯІЇЄҐ'\u0301-]лат)\\.([\\h\\v]+[a-zA-Z])")
_ABBR_DOT_PROF_PATTERN = jregex.compile(
    "(?<![а-яіїєґА-ЯІЇЄҐ'\u0301-])([Аа]кад|[Пп]роф|[Дд]оц|[Аа]сист|[Аа]рх|ап|тов|вул|бул|бульв|о|р|ім|упорядн?|др"
    "|[Пп]реп|Ів|Дж|Ол|[сС]вт|Авг)\\.([\\h\\v]+[А-ЯІЇЄҐа-яіїєґ])")
_ABBR_DOT_GUB_PATTERN = jregex.compile("(.[А-ЯІЇЄҐ][а-яіїєґ'-]+[\\h\\v]+губ)\\.")
_ABBR_DOT_DASH_PATTERN = jregex.compile("\\b([А-ЯІЇЄҐ]ж?)\\.([-–]([А-ЯІЇЄҐ][а-яіїєґ']{2}|[А-ЯІЇЄҐ]\\.))", _U)
_ABBR_DOT_KUB_SM_PATTERN = jregex.compile('(кв|куб)\\.([\\h\\v]*(?:[смкд]|мк)?м)')
_ABBR_DOT_S_G_PATTERN = jregex.compile('\\b(с)\\.(-г)\\.', _U)
_ABBR_DOT_CHL_KOR_PATTERN = jregex.compile('(чл)\\.(-кор)\\.')
_ABBR_DOT_NAUK_PATTERN = jregex.compile('(наук)\\.(-[а-яіїєґ]+)\\.')
_ABBR_DOT_PN_ZAH_PATTERN = jregex.compile('(пн|пд)\\.(-(зах|сх))\\.')
_INVALID_MLN_DOT_PATTERN = jregex.compile('(млн|млрд)\\.( [а-яіїєґ])')
_ABBR_DOT_2_SMALL_LETTERS_PATTERN = jregex.compile(
    "([^а-яіїєґА-ЯІЇЄҐ'\u0301-][векнпрстцч]{1,2})\\.(\\h*(?![смкд]?м\\.)[екмнпрстч]{1,2})\\.")
_ABBR_DOT_2_SMALL_LETTERS_REPL = ('$1' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER + '$2' +
                                  _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER)

_ONE_DOT_TWO_REPL = '$1' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER + '$2'

# скорочення що не можуть бути в кінці речення
_ABBR_DOT_NON_ENDING_PATTERN = jregex.compile(
    "(?<![а-яіїєґА-ЯІЇЄҐ'\u0301-])(абз|австрал|ам|амер|англ|акад(ем)?|арк|ауд|біол|бл(?:изьк)?|болг|буд|в(?!\\.+)"
    "|вип|вірм|грец(?:ьк)?"
    "|держ|див|дир|діал|дод|дол|досл|доц|доп|екон|ел|жін|зав|заст|зах|зб|зв|зневажл?|зовн|іл|ім|івр|інж|ісп|іст|італ"
    "|к|каб|каф|канд|кв|[1-9]-кімн|кімн|кін|кл|кн|коеф|крим|латин|мал|моб|н|[Нн]апр|нач|нім|нац|нпр|образн|оз|оп|оф|п"
    "|пен|перекл|перен|пл|пол|пом|пор|порівн|[Пп]оч|пп|прибл|прикм|прим|присл|пров|пром|просп"
    "|[Рр]ед|[Рр]еж|розд|розм|рос|рт|рум|с|санскр|[Сс]вв?|скор|соц|співавт|[сС]т|стор|суч|сх|табл|тт|[тТ]ел|техн"
    "|укр|філол|фр|франц|худ|[цЦ]ит|ч|чайн|част|ц|яп|япон)\\.(?!\uE120|\\.+[\\h\\v]*$)")
_ABBR_DOT_NON_ENDING_PATTERN_2 = jregex.compile("([^а-яіїєґА-ЯІЇЄҐ'-]м\\.)([\\h\\v]*[А-ЯІЇЄҐ])")

_ABBR_DOT_NAR_PATTERN_1 = jregex.compile('(([0-9]|рік|[рp]\\.|[-–—])[\\h\\v]+нар)\\.')
_ABBR_DOT_NAR_PATTERN_2 = jregex.compile('\\b(нар)\\.([\\h\\v]+[0-9а-яіїєґ])', _U)

# скорочення що можуть бути в кінці речення
_ABBR_DOT_ENDING_PATTERN = jregex.compile(
    "([^а-яіїєґА-ЯІЇЄҐ'\u0301-]((та|й|і) (інш?|под)|атм|відс|гр|коп|дес|дол|обл|пов|р|рр|РР|руб|ст|стст|стол|стор|чол"
    "|шт))\\.(?!\uE120)")
_ABBR_DOT_I_T_P_PATTERN = jregex.compile('([ій][\\h\\v]+т\\.)([\\h\\v]*(д|п|ін)\\.)')
_ABBR_DOT_I_T_CH_PATTERN = jregex.compile('([ву][\\h\\v]+т\\.)([\\h\\v]*ч\\.)')
_ABBR_DOT_T_ZV_PATTERN = jregex.compile('([\\h\\v\\(]+т\\.)([\\h\\v]*зв\\.)')

_ABBR_AT_THE_END = jregex.compile("(?<![а-яіїєґА-ЯІЇЄҐ'\u0301])(тис|губ|[А-ЯІЇЄҐ])\\.[\\h\\v]*$")

_APOSTROPHE_BEGIN_PATTERN = jregex.compile("(^|[\\h\\v(„«\"'])'(?!дно)(\\p{L})")
_APOSTROPHE_END_PATTER = jregex.compile("(\\p{L})(?<!\\b(?:мо|тре|тра|чо|нічо|бо|зара|пра))'([^\\p{L}-]|$)", _I | _U)

_YEAR_WITH_R = jregex.compile('((?:[12][0-9]{3}[—–-])?[12][0-9]{3})(рр?\\.)')

_COMPOUND_WITH_QUOTES1 = jregex.compile("([а-яіїє]-)([«\"„])([а-яіїєґ'-]+)([»\"“])", _I)
_COMPOUND_WITH_QUOTES2 = jregex.compile("([«\"„])([а-яіїєґ0-9'-]+)([»\\\"“])(-[а-яіїє])", _I)

# Сьогодні (у четвер. - Ред.), вранці.
_ABBR_DOT_RED_AVT_PATTERN = jregex.compile('([\\h\\v]+(?:[Рр]ед|[Аа]вт))\\.(\\h*[)\\]а-яіїєґ])')

_SOFT_HYPHEN_WRAP = '\u00AD\n'
_SOFT_HYPHEN_WRAP_SUBST = '\uE103'
# url (Pattern.CASE_INSENSITIVE only)
_URL_PATTERN = jregex.compile(
    '(?i)((https?|ftp)://|www\\.)[^\\h\\v/$.?#),]+\\.[^\\h\\v),">]*'
    '|(mailto:)?[\\p{L}\\d._-]+@[\\p{L}\\d_-]+(\\.[\\p{L}\\d_-]+)+')
_URL_START_REPLACE_CHAR = 0xE300

_LEADING_DASH_PATTERN = jregex.compile('^([—–])([а-яіїєґА-ЯІЇЄҐA-Z])')
_LEADING_DASH_PATTERN_2 = jregex.compile('^(-)([А-ЯІЇЄҐA-Z])')

_NUMBER_MISSING_SPACE = jregex.compile(
    "((?:[\\h\\v\uE110]|^)[а-яїієґА-ЯІЇЄҐ'-]*[а-яїієґ']?[а-яїієґ])([0-9]+(?![а-яіїєґА-ЯІЇЄҐa-zA-Z»\"“]))")

_WEB_ENTITIES = jregex.compile('([а-яіїєґ])\\.(НЕТ|net|Інфо|Info|City|Life|UA|юа|лі|media|com|фм|ru|ру|орг)\\b',
                               _I | _U)
_WEB_ENTITIES2 = jregex.compile('\\.([a-z_-]+)\\.(ua)', _I)

_EM_DASH_SPACE = jregex.compile('—([\\h\\v])')
_PERCENT = jregex.compile('%([^-])')
_RTRIM = jregex.compile('[\\h\\v]*$')
_DASH_AFTER_LETTER = jregex.compile('([а-яіїєґА-ЯІЇЄҐ])([»"-]+-)')
_DASH_BEFORE_LETTER = jregex.compile('([»"-]+-)([а-яіїєґА-ЯІЇЄҐ])')
_SOFT_HYPHEN_WRAP_PATTERN = jregex.compile('(?<!\\s)' + _SOFT_HYPHEN_WRAP)
_PLUS = jregex.compile('\\+(?=[а-яіїєґА-ЯІЇЄҐ0-9])')
_MINUS_NUMBER = jregex.compile('(?<=(^|[\\h\\v]))([-–])(?=[0-9])')

_TOKEN_REPLACEMENTS = (
    (_DECIMAL_COMMA_SUBST, ','),
    (_NON_BREAKING_SLASH_SUBST, '/'),
    (_NON_BREAKING_COLON_SUBST, ':'),
    (_NON_BREAKING_SPACE_SUBST, ' '),
    (_LEFT_BRACE_SUBST, '('),
    (_RIGHT_BRACE_SUBST, ')'),
    (_LEFT_ANGLE_SUBST, '<'),
    (_RIGHT_ANGLE_SUBST, '>'),
    (_SLASH_SUBST, '/'),
    # also replaces back sentence-ending abbreviations
    (_NON_BREAKING_DOT_SUBST, '.'),
    (_SOFT_HYPHEN_WRAP_SUBST, _SOFT_HYPHEN_WRAP),
    (_NON_BREAKING_PLACEHOLDER, ''),
    (_NON_BREAKING_PLACEHOLDER2, ''),
)


def _rep(pattern, repl, text):
    return jregex.java_replace(pattern, repl, text)


class UkrainianWordTokenizer:
    """Tokenizes a sentence into words. Punctuation and whitespace gets its
    own token. Specific to Ukrainian: apostrophes (0x27 and U+2019) are not
    in the list as they are part of the word."""

    def tokenize(self, text):
        urls = {}
        if java_trim(text):
            text = self._adjust_text_for_tokenizing(text, urls)
        out = []
        for token in _split_with_delimiters(text, _SPLIT_CHARS_REGEX):
            if token == _BREAKING_PLACEHOLDER:
                continue
            for a, b in _TOKEN_REPLACEMENTS:
                if a in token:
                    token = token.replace(a, b)
            if urls:
                for k, v in urls.items():
                    token = token.replace(k, v)
            out.append(token)
        return out

    def _adjust_text_for_tokenizing(self, text, urls):
        text = _cleanup(text)

        if text[0] in '—–-':
            if _LEADING_DASH_PATTERN.search(text):
                text = jregex.java_replace(_LEADING_DASH_PATTERN, '$1' + _BREAKING_PLACEHOLDER + '$2', text, 1)
            elif _LEADING_DASH_PATTERN_2.search(text):
                text = jregex.java_replace(_LEADING_DASH_PATTERN_2, '$1' + _BREAKING_PLACEHOLDER + '$2', text, 1)

        if ',' in text:
            text = _rep(_DECIMAL_COMMA_PATTERN, _DECIMAL_COMMA_REPL, text)

        # check for urls
        if 'http' in text or 'www' in text or '@' in text or 'ftp' in text:
            url_replace_char = _URL_START_REPLACE_CHAR
            m = _URL_PATTERN.search(text)
            while m:
                replace_char = chr(url_replace_char)
                urls[replace_char] = m.group()
                text = text[:m.start()] + replace_char + text[m.end():]
                url_replace_char += 1
                m = _URL_PATTERN.search(text)

        if '—' in text:
            text = _rep(_EM_DASH_SPACE, _BREAKING_PLACEHOLDER + '—$1', text)

        n_dash_present = '–' in text
        if '-' in text or n_dash_present:
            text = _rep(_DASH_NUMBERS_PATTERN, _DASH_NUMBERS_REPL, text)
            if n_dash_present:
                text = _rep(_N_DASH_SPACE_PATTERN, _N_DASH_SPACE_REPL, text)
                text = _rep(_N_DASH_SPACE_PATTERN2, _N_DASH_SPACE_REPL, text)

        if 'с/г' in text:
            text = text.replace('с/г', 'с' + _NON_BREAKING_SLASH_SUBST + 'г')

        if 'Л/ДНР' in text:
            text = text.replace('Л/ДНР', 'Л' + _NON_BREAKING_SLASH_SUBST + 'ДНР')

        if 'р.' in text:
            if _YEAR_WITH_R.search(text):
                text = _rep(_YEAR_WITH_R, '$1' + _BREAKING_PLACEHOLDER + '$2', text)

        # leave only potential hashtags together
        text = text.replace('#', _BREAKING_PLACEHOLDER + '#')
        # leave numbers with following % together
        if '%' in text:
            text = _rep(_PERCENT, '%' + _BREAKING_PLACEHOLDER + '$1', text)

        text = _rep(_COMPOUND_WITH_QUOTES1, '$1$2\uE120$3\uE120$4\uE120', text)
        text = _rep(_COMPOUND_WITH_QUOTES2, '$1\uE120$2\uE120$3\uE120$4', text)
        if '[' in text:
            text = _rep(WORDS_WITH_BRACKETS_PATTERN, '$1\\[\uE120$2\\]\uE120', text)

        # if period is not the last character in the sentence
        dot_index = text.find('.')
        text_rtrimmed = jregex.java_replace(_RTRIM, '', text, 1)
        dot_inside_sentence = 0 <= dot_index < len(text_rtrimmed) - 1

        if dot_inside_sentence or (dot_index == len(text_rtrimmed) - 1 and _ABBR_AT_THE_END.search(text)):
            # ugly - special case for тис. та ініціалів
            text = _rep(_DOTTED_NUMBERS_PATTERN3, '$1.\uE120$2.\uE120$3', text)
            text = _rep(_DOTTED_NUMBERS_PATTERN, '$1.\uE120$2', text)

            text = _rep(_ABBR_DOT_NAR_PATTERN_1, '$1.\uE120\uE110', text)
            text = _rep(_ABBR_DOT_NAR_PATTERN_2, '$1.\uE120\uE110$2', text)

            text = _rep(_ABBR_DOT_2_SMALL_LETTERS_PATTERN, '$1.\uE120\uE110$2.\uE120\uE110', text)
            text = _rep(_ABBR_DOT_VO_PATTERN1, _ABBR_DOT_2_SMALL_LETTERS_REPL, text)
            text = _rep(_ABBR_DOT_VO_PATTERN2, _ABBR_DOT_2_SMALL_LETTERS_REPL, text)
            text = _rep(_ABBR_DOT_VO_PATTERN3, _ABBR_DOT_2_SMALL_LETTERS_REPL, text)
            text = _rep(_ABBR_DOT_ART_PATTERN, _ONE_DOT_TWO_REPL, text)
            text = _rep(_ABBR_DOT_MAN_PATTERN, _ONE_DOT_TWO_REPL, text)
            text = _rep(_ABBR_DOT_TYS_PATTERN1, '$1$2' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER, text)
            text = _rep(_ABBR_DOT_TYS_PATTERN2, _ONE_DOT_TWO_REPL, text)
            text = _rep(_ABBR_DOT_VYD_PATTERN, '$1$3' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER, text)
            text = _rep(_ABBR_DOT_LAT_PATTERN, _ONE_DOT_TWO_REPL, text)
            text = _rep(_ABBR_DOT_PROF_PATTERN, _ONE_DOT_TWO_REPL, text)
            text = _rep(_ABBR_DOT_GUB_PATTERN, '$1' + _NON_BREAKING_DOT_SUBST + _BREAKING_PLACEHOLDER, text)
            text = _rep(_ABBR_DOT_DASH_PATTERN, '$1' + _NON_BREAKING_DOT_SUBST + '$2', text)

            text = _rep(_INITIALS_DOT_PATTERN_SP_2, _INITIALS_DOT_REPL_SP_2, text)
            text = _rep(_INITIALS_DOT_PATTERN_SP_1, _INITIALS_DOT_REPL_SP_1, text)
            text = _rep(_INITIALS_DOT_PATTERN_RSP_2, _INITIALS_DOT_REPL_RSP_2, text)
            text = _rep(_INITIALS_DOT_PATTERN_RSP_1, _INITIALS_DOT_REPL_RSP_1, text)

            text = _rep(_ABBR_DOT_KUB_SM_PATTERN, '$1.\uE120\uE110$2', text)
            text = _rep(_ABBR_DOT_S_G_PATTERN, '$1' + _NON_BREAKING_DOT_SUBST + '$2' + _NON_BREAKING_DOT_SUBST +
                        _BREAKING_PLACEHOLDER, text)
            text = _rep(_ABBR_DOT_CHL_KOR_PATTERN, '$1.\uE120$2.\uE120\uE110', text)
            text = _rep(_ABBR_DOT_NAUK_PATTERN, '$1.\uE120$2.\uE120\uE110', text)
            text = _rep(_ABBR_DOT_PN_ZAH_PATTERN, '$1.\uE120\uE110$2.\uE120\uE110', text)
            text = _rep(_ABBR_DOT_I_T_P_PATTERN, '$1\uE120\uE110$2\uE120\uE110', text)
            text = _rep(_ABBR_DOT_I_T_CH_PATTERN, '$1\uE120\uE110$2\uE120\uE110', text)
            text = _rep(_ABBR_DOT_T_ZV_PATTERN, '$1\uE120\uE110$2\uE120\uE110', text)
            text = _rep(_ABBR_DOT_RED_AVT_PATTERN, '$1.\uE120\uE110$2', text)
            text = _rep(_ABBR_DOT_NON_ENDING_PATTERN, '$1.\uE120\uE110', text)
            text = _rep(_ABBR_DOT_NON_ENDING_PATTERN_2, '$1\uE120\uE110$2', text)
            text = _rep(_INVALID_MLN_DOT_PATTERN, '$1.\uE120\uE110$2', text)

        if dot_inside_sentence:
            text = _rep(_WEB_ENTITIES, '$1.\uE120$2', text)
            text = _rep(_WEB_ENTITIES2, '.\uE120$1.\uE120$2', text)

        text = _rep(_ABBR_DOT_ENDING_PATTERN, '$1.\uE120\uE110', text)

        # 2 000 000
        def spaced(m):
            return m.group(0).replace(' ', _NON_BREAKING_SPACE_SUBST).replace(
                '\u00A0', _NON_BREAKING_SPACE_SUBST).replace('\u202F', _NON_BREAKING_SPACE_SUBST)
        # (Matcher.appendReplacement: the group text is a replacement
        # string, it has no $ or \ here)
        text = _DECIMAL_SPACE_PATTERN.sub(spaced, text)

        # 12:25
        if ':' in text:
            text = _rep(_COLON_NUMBERS_PATTERN, _COLON_NUMBERS_REPL, text)

        # ВКПБ(о)
        if '(' in text:
            text = _rep(_BRACE_IN_WORD_PATTERN, '$1' + _LEFT_BRACE_SUBST + '$2' + _RIGHT_BRACE_SUBST, text)

        if '<' in text:
            text = _rep(_XML_TAG_PATTERN, _BREAKING_PLACEHOLDER + _LEFT_ANGLE_SUBST + '$1' + _RIGHT_ANGLE_SUBST +
                        _BREAKING_PLACEHOLDER, text)
            text = text.replace(_LEFT_ANGLE_SUBST + '/', _LEFT_ANGLE_SUBST + _SLASH_SUBST)
            text = text.replace('/' + _RIGHT_ANGLE_SUBST, _SLASH_SUBST + _RIGHT_ANGLE_SUBST)

        if '-' in text:
            text = _rep(_DASH_AFTER_LETTER, '$1' + _BREAKING_PLACEHOLDER + '$2', text)
            text = _rep(_DASH_BEFORE_LETTER, '$1' + _BREAKING_PLACEHOLDER + '$2', text)

        if _SOFT_HYPHEN_WRAP in text:
            text = _rep(_SOFT_HYPHEN_WRAP_PATTERN, _SOFT_HYPHEN_WRAP_SUBST, text)

        if "'" in text:
            text = _rep(_APOSTROPHE_BEGIN_PATTERN, "$1'" + _BREAKING_PLACEHOLDER + '$2', text)
            text = _rep(_APOSTROPHE_END_PATTER, '$1' + _BREAKING_PLACEHOLDER + "'$2", text)

        if '+' in text:
            text = _rep(_PLUS, _BREAKING_PLACEHOLDER + '+' + _BREAKING_PLACEHOLDER, text)

        # -20C
        if len(text) > 1 and ('-' in text or '–' in text):
            text = _rep(_MINUS_NUMBER, '$2' + _BREAKING_PLACEHOLDER, text)

        text = _rep(_NUMBER_MISSING_SPACE, '$1' + _BREAKING_PLACEHOLDER + '$2', text)
        return text


def _cleanup(text):
    text = (text.replace('’', "'")
            .replace('ʼ', "'")
            .replace('‘', "'")
            .replace('‚', ',')  # SINGLE LOW-9 QUOTATION MARK sometimes used as a comma
            .replace('‑', '-'))  # we handle – in tagger so we can base our rule on it
    return _rep(_WEIRD_APOSTROPH_PATTERN, '$1\uE120$2\uE120$3', text)


def _split_with_delimiters(s, delim_pattern):
    parts = []
    last_end = 0
    for m in delim_pattern.finditer(s):
        start = m.start()
        if last_end != start:
            parts.append(s[last_end:start])
        parts.append(m.group())
        last_end = m.end()
    if last_end != len(s):
        parts.append(s[last_end:])
    return parts
