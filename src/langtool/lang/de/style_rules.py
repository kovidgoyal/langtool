"""German style rules (port of the style rules of org.languagetool.rules.de):
GermanFillerWordsRule, GermanStyleRepeatedWordRule,
StyleRepeatedVeryShortSentences, StyleRepeatedSentenceBeginning,
StyleTooOftenUsedVerbRule, StyleTooOftenUsedNounRule,
StyleTooOftenUsedAdjectiveRule, PassiveSentenceRule,
SentenceWithModalVerbRule, SentenceWithManRule,
ConjunctionAtBeginOfSentenceRule, NonSignificantVerbsRule,
UnnecessaryPhraseRule, RedundantModalOrAuxiliaryVerb and the German
LongSentenceRule.

The user configuration (UserConfig.getConfigValueByID) is a mapping rule id
-> sequence of values (see abstract_rules._config_values). LinguServices
(LibreOffice/OpenOffice only) are not supported."""

import threading

from ... import jregex
from ...rules.abstract_rules import (AbstractStatisticSentenceStyleRule, AbstractStatisticStyleRule,
                                     AbstractStyleRepeatedWordRule, AbstractStyleTooOftenUsedWordRule,
                                     _config_values)
from ...rules.base import Category, RuleMatch
from ...rules.core import CoreRule, CoreTextLevelRule, is_paragraph_end
from ...rules.core import LongSentenceRule as _CoreLongSentenceRule
from ...tools import java_equals_ignore_case, lowercase_first_char, uppercase_first_char


def _creative_writing_category(messages):
    return Category('CREATIVE_WRITING', messages['category_creative_writing'], 'INTERNAL', False)


def _is_bool(v):
    return isinstance(v, bool)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


_OPENING_QUOTES = jregex.compile('["“„»«]')
_ENDING_QUOTES = jregex.compile('["“”»«]')


# --- GermanFillerWordsRule --------------------------------------------------

_FILLER_WORDS = frozenset((
    "aber", "abermals", "allein", "allemal", "allenfalls", "allenthalben", "allerdings", "allesamt", "allzu", "also",
    "alt", "andauernd", "andererseits", "andernfalls", "anscheinend", "auch", "auffallend", "augenscheinlich",
    "ausdrücklich", "ausgerechnet", "ausnahmslos",
    "außerdem", "äußerst", "beinahe", "bekanntlich", "bereits", "besonders", "bestenfalls", "bestimmt", "bloß",
    "dabei", "dadurch", "dafür", "dagegen", "daher", "damals",
    "danach", "demgegenüber", "demgemäß", "demnach", "denkbar", "denn", "dennoch", "deshalb", "deswegen", "doch",
    "durchaus", "durchweg", "eben", "eigentlich",
    "einerseits", "einfach", "einige", "einigermaßen", "einmal", "ergo", "erheblich", "etliche", "etwa", "etwas",
    "fast", "folgendermaßen", "folglich", "förmlich",
    "fortwährend", "fraglos", "freilich", "ganz", "gänzlich", "gar", "gelegentlich", "gemeinhin", "genau", "geradezu",
    "gewiss", "gewissermaßen", "glatt", "gleichsam",
    "gleichwohl", "glücklicherweise", "gottseidank", "größtenteils", "häufig", "hingegen", "hinlänglich", "höchst",
    "höchstens", "immer", "immerhin", "immerzu",
    "indessen", "infolgedessen", "insbesondere", "inzwischen", "irgend", "irgendein", "irgendjemand", "irgendwann",
    "irgendwie", "irgendwo", "ja", "je",
    "jedenfalls", "jedoch", "jemals", "kaum", "keinesfalls", "keineswegs", "längst", "lediglich", "leider",
    "letztlich", "manchmal", "mehrfach", "meinetwegen",
    "meist", "meistens", "meistenteils", "mindestens", "mithin", "mitunter", "möglicherweise", "möglichst",
    "nämlich", "naturgemäß", "natürlich", "neuerdings",
    "neuerlich", "neulich", "nichtsdestoweniger", "nie", "niemals", "nun", "nur", "offenbar", "offenkundig",
    "offensichtlich", "oft", "ohnedies", "partout",
    "plötzlich", "praktisch", "quasi", "recht", "reichlich", "reiflich", "relativ", "restlos", "richtiggehend",
    "rundheraus", "rundum", "sattsam", "schlicht",
    "schlichtweg", "schließlich", "schlussendlich", "schon", "sehr", "selbst", "selbstredend", "selbstverständlich",
    "selten", "seltsamerweise", "sicher",
    "sicherlich", "so", "sogar", "sonst", "sowieso", "sozusagen", "stellenweise", "stets", "trotzdem", "überaus",
    "überdies", "überhaupt", "übrigens",
    "umständehalber", "unbedingt", "unerhört", "ungefähr", "ungemein", "ungewöhnlich", "ungleich",
    "unglücklicherweise", "unlängst", "unmaßgeblich",
    "unsagbar", "unsäglich", "unstreitig", "unzweifelhaft", "vergleichsweise", "vermutlich", "vielfach",
    "vielleicht", "voll", "vollends", "völlig",
    "vollkommen", "vollständig", "wahrscheinlich", "weidlich", "weitgehend", "wenigstens", "wieder", "wiederum",
    "wirklich", "wohl", "wohlgemerkt",
    "womöglich", "ziemlich", "zudem", "zugegeben", "zumeist", "zusehends", "zuweilen", "zweifellos", "zweifelsfrei",
    "zweifelsohne"))


def _filler_is_exception(tokens, num):
    if num == 1 or tokens[num - 1].token == ',':
        return True
    tok = tokens[num].token
    if tok == 'allein':
        for i in range(1, len(tokens)):
            if tokens[i].has_lemma('sein'):
                return True
        return False
    if tok == 'recht':
        for i in range(1, len(tokens)):
            if tokens[i].has_any_lemma('haben', 'geben'):
                return True
    if num < len(tokens) - 1 and tok in ('so', 'besonders') and tokens[num + 1].has_pos_tag_starting_with('ADJ'):
        return True
    if tokens[num].has_pos_tag_starting_with('ADJ') and tokens[num - 1].token == 'so':
        return True
    if tok == 'nur' and tokens[num - 1].token == 'nicht':
        for i in range(num + 1, len(tokens) - 2):
            if tokens[i].token == ',' and (tokens[i + 1].token == 'auch' or
                                           (tokens[i + 1].token == 'sondern' and tokens[i + 2].token == 'auch')):
                return True
    if num > 2 and tok == 'auch' and tokens[num - 1].token == 'sondern' and tokens[num - 2].token == ',':
        for i in range(1, num - 2):
            if tokens[i].token == 'nicht' and tokens[i + 1].token == 'nur':
                return True
    return False


def _is_two_word_exception(first, second):
    return ((first == 'aber' and second in ('nur', 'auch'))
            or (first == 'auch' and second == 'nur')
            or (first == 'immer' and second == 'wieder')
            or (first == 'genau' and second == 'so')
            or (first == 'so' and second in ('etwas', 'viel', 'oft'))
            or (first == 'schon' and second == 'fast'))


class GermanFillerWordsRule(AbstractStatisticStyleRule):
    """Port of GermanFillerWordsRule: a statistic style rule for filler
    words (default off); optionally (user configuration values 2) shows two
    consecutive filler words or more than two in a sentence."""

    DEFAULT_MIN_PERCENT = 8
    DEFAULT_TWO_FOLLOWING = False
    DEFAULT_MANY_IN_SENTENCE = False
    DEFAULT_SENTENCE_MSG1 = 'Zwei potentielle Füllwörter hintereinander. Mindestens eins sollte gelöscht werden.'
    DEFAULT_SENTENCE_MSG2 = ('Mehr als zwei potentielle Füllwörter in einem Satz. Mindestens eins sollte gelöscht '
                             'werden.')

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)
        self.sentence_message = None
        self.test_two_following = self._get_option(user_config, self.DEFAULT_TWO_FOLLOWING)
        # (as in Java, both options are read from the third value)
        self.test_many_in_sentence = self._get_option(user_config, self.DEFAULT_MANY_IN_SENTENCE)

    def _get_option(self, user_config, default):
        cf = _config_values(user_config, self.get_id())
        if cf is not None and len(cf) > 2 and _is_bool(cf[2]):
            return cf[2]
        return default

    def condition_fulfilled(self, tokens, n):
        if tokens[n].token in _FILLER_WORDS and not _filler_is_exception(tokens, n) \
                and (n < 2 or not _is_two_word_exception(tokens[n - 1].token, tokens[n].token)) \
                and (n > len(tokens) - 2 or not _is_two_word_exception(tokens[n].token, tokens[n + 1].token)):
            return n
        return -1

    def sentence_condition_fulfilled(self, tokens, n):
        if self.test_two_following:
            if (n > 1 and tokens[n - 1].token in _FILLER_WORDS and not _filler_is_exception(tokens, n - 1)) or \
                    (n < len(tokens) - 1 and tokens[n + 1].token in _FILLER_WORDS and
                     not _filler_is_exception(tokens, n + 1)):
                self.sentence_message = self.DEFAULT_SENTENCE_MSG1
                return True
        if self.test_many_in_sentence:
            num = 0
            for i in range(n - 2, 0, -1):
                if self.condition_fulfilled(tokens, i) == i:
                    num += 1
                    if num > 1:
                        self.sentence_message = self.DEFAULT_SENTENCE_MSG2
                        return True
            for i in range(n + 2, len(tokens)):
                if self.condition_fulfilled(tokens, i) == i:
                    num += 1
                    if num > 1:
                        self.sentence_message = self.DEFAULT_SENTENCE_MSG2
                        return True
        return False

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return 'Dieses Wort könnte ein Füllwort sein. Möglicherweise ist es besser es zu löschen.'
        return 'Mehr als ' + str(limit) + '% Füllwörter {' + str(int(percent + 0.5)) + \
            '%} gefunden. Möglicherweise ist es besser dieses potentielle Füllwort zu löschen.'

    def get_sentence_message(self):
        return self.sentence_message

    def get_id(self):
        return 'FILLER_WORDS_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Füllwörter'

    def get_configure_percent_text(self):
        return 'Anzeigen wenn mehr als ...% eines Kapitels Füllwörter sind:'

    def get_configure_without_direct_speach_text(self):
        return 'Keine wörtliche Rede und Zitate berücksichtigen'


# --- GermanStyleRepeatedWordRule --------------------------------------------

_SYNONYMS_URL = 'https://www.openthesaurus.de/synonyme/'
_LETTERS = jregex.compile('^[A-Za-zÄÖÜäöüß]+$')
_TITLES = ('Frau', 'Fräulein', 'Herr', 'Herrn', 'Lady', 'Mister')
_NOT_TO_CHECK = ('sicher', 'weit', 'Sie', 'Ich', 'Euch', 'Eure', 'Der', 'all')
_TO_CHECK_POS = jregex.compile('(SUB|EIG|VER|ADJ):.*')
_NOT_TO_CHECK_POS = jregex.compile('(PRO|A(RT|DV)|VER:(AUX|MOD)):.*')

_speller_lock = threading.Lock()
_spellers = {}


def _morfologik_speller(language):
    """new Speller(MorfologikSpeller.getDictionaryWithCaching("/de/hunspell/de_DE.dict"))
    (morfologik's misspelling check on the dictionary alone)"""
    from ...spelling import MorfologikMultiSpeller
    binary_dict = language.dictionary('de/hunspell/de_DE.dict')
    with _speller_lock:
        r = _spellers.get(id(binary_dict))
        if r is None or r[0] is not binary_dict:
            r = _spellers[id(binary_dict)] = (binary_dict, MorfologikMultiSpeller(binary_dict))
        return r[1]


def _is_unknown_word(atr):
    """Is a unknown word (has only letters and no PosTag)"""
    return atr.is_pos_tag_unknown and len(atr.token) > 2 and _LETTERS.fullmatch(atr.token) is not None


class GermanStyleRepeatedWordRule(AbstractStyleRepeatedWordRule):
    """Port of GermanStyleRepeatedWordRule: repeated nouns, verbs and
    adjectives in the same or consecutive sentences (default off); with the
    third user configuration value also parts of compound words."""

    MAX_DISTANCE_OF_SENTENCES = 1
    EXCLUDE_DIRECT_SPEECH = True
    TEST_COMPOUND_WORDS = False

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config)
        self.add_example_pair('Ich gehe zum Supermarkt, danach <marker>gehe</marker> ich nach Hause.',
                              'Ich gehe zum Supermarkt, danach nach Hause.')
        self.speller = None
        self.test_compound_words = self.TEST_COMPOUND_WORDS
        cf = _config_values(user_config, self.get_id())
        if cf is not None and len(cf) > 2:
            self.test_compound_words = bool(cf[2])

    def get_id(self):
        return 'STYLE_REPEATED_WORD_RULE_DE'

    def get_description(self):
        return 'Wiederholte Worte in aufeinanderfolgenden Sätzen'

    def message_same_sentence(self):
        return 'Mögliches Stilproblem: Das Wort wird noch einmal im selben Satz verwendet.'

    def message_sentence_before(self):
        return 'Mögliches Stilproblem: Das Wort wird bereits in einem vorhergehenden Satz verwendet.'

    def message_sentence_after(self):
        return 'Mögliches Stilproblem: Das Wort wird auch in einem nachfolgenden Satz verwendet.'

    def _is_correct_spell(self, word):
        """is a correct spelled word"""
        word = uppercase_first_char(word)
        if self.speller is None:
            # (Java creates the speller lazily, too)
            self.speller = _morfologik_speller(self.lang)
        return not self.speller.is_misspelled(word)

    def is_token_to_check(self, tokens, n):
        """Only substantive, names, verbs and adjectives are checked"""
        if 0 < n < len(tokens) - 1 and \
                (tokens[n + 1].has_pos_tag_starting_with('EIG') or _is_unknown_word(tokens[n + 1])) and \
                tokens[n].token in _TITLES:
            return False
        atr = tokens[n]
        return ((atr.matches_pos_tag_regex(_TO_CHECK_POS) and not atr.matches_pos_tag_regex(_NOT_TO_CHECK_POS))
                or _is_unknown_word(atr)) and atr.token not in _NOT_TO_CHECK

    def is_token_pair(self, tokens, n, before):
        """Pairs of substantive are excluded like "Arm in Arm", "Seite an
        Seite", etc. (operator precedence as in Java)"""
        if before:
            if (2 < n < len(tokens) and tokens[n - 2].has_pos_tag_starting_with('SUB') and
                    tokens[n - 1].has_pos_tag_starting_with('PRP') and tokens[n].has_pos_tag_starting_with('SUB')) \
                    or (tokens[n - 2].token == 'hart' and tokens[n - 1].token == 'auf' and tokens[n].token == 'hart') \
                    or (tokens[n - 2].token == 'dicht' and tokens[n - 1].token == 'an' and
                        tokens[n].token == 'dicht') \
                    or (tokens[n - 2].token == 'fressen' and tokens[n - 1].token == 'und' and
                        tokens[n].token == 'gefressen'):
                return True
        else:
            if (0 < n < len(tokens) - 2 and tokens[n].has_pos_tag_starting_with('SUB') and
                    tokens[n + 1].has_pos_tag_starting_with('PRP') and tokens[n + 2].has_pos_tag_starting_with('SUB')) \
                    or (tokens[n].token == 'hart' and tokens[n + 1].token == 'auf' and tokens[n + 2].token == 'hart') \
                    or (tokens[n].token == 'dicht' and tokens[n + 1].token == 'an' and
                        tokens[n + 2].token == 'dicht') \
                    or (tokens[n].token == 'fressen' and tokens[n + 1].token == 'und' and
                        tokens[n + 2].token == 'gefressen'):
                return True
        return False

    def _is_second_part_of_word(self, test_token_text, token_text):
        if len(test_token_text) - len(token_text) < 3:
            return False
        lower_token_text = lowercase_first_char(token_text)
        if lower_token_text == 'frei' or (lower_token_text == 'alten' and test_token_text.endswith('halten')):
            return False
        if lowercase_first_char(test_token_text).startswith(lower_token_text):
            word = test_token_text[len(token_text):]
            if self._is_correct_spell(word):
                return True
            elif word.startswith('s'):
                word = word[1:]
                if self._is_correct_spell(word):
                    return True
            return False
        elif test_token_text.endswith(lower_token_text):
            word = test_token_text[:len(test_token_text) - len(token_text)]
            if self._is_correct_spell(word):
                return True
            elif word.endswith('s'):
                word = word[len(word) - 1:]  # (sic, as in Java)
                if self._is_correct_spell(word):
                    return True
            return False
        return False

    def is_part_of_word(self, test_token_text, token_text):
        if not self.test_compound_words or len(test_token_text) < 3 or len(token_text) < 3:
            return False
        if len(test_token_text) > len(token_text):
            return self._is_second_part_of_word(test_token_text, token_text)
        return self._is_second_part_of_word(token_text, test_token_text)

    def is_exception_pair(self, token1, token2):
        """true if is an exception of token pair (called after two tokens are
        tested to share the same lemma)"""
        if (token1.has_lemma('nah') and token1.has_lemma('nächst') and not token2.has_lemma('nächst')) or \
                (token2.has_lemma('nah') and token2.has_lemma('nächst') and not token1.has_lemma('nächst')):
            return True
        if token1.has_lemma('gut') and \
                ((token1.token.startswith('gut') and not token2.token.startswith('gut')) or
                 (token2.token.startswith('gut') and not token1.token.startswith('gut'))):
            return True
        return False

    def set_url(self, atr):
        """an URL to the German openThesaurus"""
        if atr is not None:
            lemmas = [r.lemma for r in atr.readings if r.lemma is not None]
            if len(lemmas) == 1:
                return _SYNONYMS_URL + lemmas[0]
            return _SYNONYMS_URL + atr.token
        return None


# --- StyleRepeatedVeryShortSentences ----------------------------------------

class StyleRepeatedVeryShortSentences(CoreTextLevelRule):
    """Port of StyleRepeatedVeryShortSentences: several very short sentences
    in a row (staccato, default off)."""

    rule_id = 'STYLE_REPEATED_SHORT_SENTENCES'
    issue_type = 'Style'
    MIN_REPEATED = 3
    MIN_WORDS = 4
    EXCLUDE_DIRECT_SPEECH = True

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language)
        self.category = _creative_writing_category(messages)
        self.lang = language
        self.set_default_off()
        self.add_example_pair('Das Auto kam <marker>näher.</marker> Der Hund <marker>schlief.</marker> Die Reifen '
                              '<marker>quietschten.</marker>',
                              'Das Auto kam näher. Tief und fest schlief der Hund. Die Reifen quietschten.')
        self.min_words = self.MIN_WORDS
        self.min_repeated = self.MIN_REPEATED
        self.exclude_direct_speech = self.EXCLUDE_DIRECT_SPEECH
        cf = _config_values(user_config, self.get_id())
        if cf is not None:
            if len(cf) > 0 and _is_int(cf[0]):
                self.min_repeated = cf[0]
            if len(cf) > 1 and _is_int(cf[1]):
                self.min_words = cf[1]
            if len(cf) > 2 and _is_bool(cf[2]):
                self.exclude_direct_speech = cf[2]

    def get_description(self):
        return 'Stakkato-Sätze'

    def min_to_check_paragraph(self):
        return self.min_repeated

    def match(self, sentences, annotated_text=None):
        out = []
        if len(sentences) < self.min_repeated:
            return out
        slb = getattr(self.lang, 'single_line_breaks_marks_para', False)
        pos = 0
        n_repeated = 0
        starts = []
        ends = []
        repeated = []
        n_para = -1
        begins_ds = False
        ends_ds = False
        for n, sentence in enumerate(sentences):
            n_para += 1
            tokens = sentence.non_blank_tokens
            if self.exclude_direct_speech:
                begins_ds = ends_ds
                for i in range(len(tokens)):
                    if not begins_ds and _OPENING_QUOTES.fullmatch(tokens[i].token) and i < len(tokens) - 1 and \
                            not tokens[i + 1].whitespace_before:
                        begins_ds = True
                        ends_ds = True
                    elif begins_ds and _ENDING_QUOTES.fullmatch(tokens[i].token) and i > 1 and \
                            not tokens[i].whitespace_before:
                        ends_ds = False
            paragraph_end = is_paragraph_end(sentences, n, slb)
            # 3 -> skip one word sentences; max tokens: minWords + SENT_START + punctuation mark
            if not begins_ds and (not paragraph_end or n_para > 0) and 3 < len(tokens) <= self.min_words + 2:
                repeated.append(sentence)
                starts.append(tokens[-2].start_pos + pos)
                ends.append(tokens[-1].end_pos + pos)
                n_repeated += 1
            else:
                if n_repeated >= self.min_repeated:
                    for i in range(len(repeated)):
                        out.append(RuleMatch(self, repeated[i], starts[i], ends[i], self.get_description()))
                repeated = []
                starts = []
                ends = []
                n_repeated = 0
            pos += sentence.get_corrected_text_length()
            if paragraph_end:
                n_para = -1
        if n_repeated >= self.min_repeated:
            for i in range(len(repeated)):
                out.append(RuleMatch(self, repeated[i], starts[i], ends[i], self.get_description()))
        return out


# --- StyleRepeatedSentenceBeginning -----------------------------------------

class StyleRepeatedSentenceBeginning(CoreTextLevelRule):
    """Port of StyleRepeatedSentenceBeginning: several sentences in a row
    beginning with the subject (default off)."""

    rule_id = 'STYLE_REPEATED_SENTENCE_BEGINNING'
    issue_type = 'Style'
    MIN_REPEATED = 3

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.category = _creative_writing_category(messages)
        self.set_default_off()
        self.add_example_pair('<marker>Das Auto</marker> kam näher. <marker>Der Hund</marker> lief langsam über die '
                              'Straße. <marker>Die Reifen</marker> quietschten.',
                              'Das Auto kam näher. Langsam lief der Hund über die Straße. Die Reifen quietschten.')

    def get_description(self):
        return 'Subjekt als wiederholter Satzanfang'

    def min_to_check_paragraph(self):
        return self.MIN_REPEATED

    def match(self, sentences, annotated_text=None):
        out = []
        if len(sentences) < self.MIN_REPEATED:
            return out
        starts = []
        ends = []
        repeated = []
        pos = 0
        n_repeated = 0
        for sentence in sentences:
            tokens = sentence.non_blank_tokens
            if tokens[1].has_pos_tag_starting_with('ART:DEF:NOM') or tokens[1].has_pos_tag_starting_with('ART:IND:NOM'):
                no_sub = True
                i = 2
                while i < len(tokens) and not tokens[i].has_pos_tag_starting_with('VER'):
                    if tokens[i].has_pos_tag_starting_with('SUB'):
                        no_sub = False
                        ends.append(tokens[i].end_pos + pos)
                        break
                    i += 1
                if no_sub:
                    ends.append(tokens[1].end_pos + pos)
                repeated.append(sentence)
                starts.append(tokens[1].start_pos + pos)
                n_repeated += 1
            elif tokens[1].has_pos_tag_starting_with('PRO:PER:NOM'):
                repeated.append(sentence)
                starts.append(tokens[1].start_pos + pos)
                ends.append(tokens[1].end_pos + pos)
                n_repeated += 1
            else:
                if n_repeated >= self.MIN_REPEATED:
                    for i in range(len(repeated)):
                        out.append(RuleMatch(self, repeated[i], starts[i], ends[i], self.get_description()))
                repeated = []
                starts = []
                ends = []
                n_repeated = 0
            pos += sentence.get_corrected_text_length()
        if n_repeated >= self.MIN_REPEATED:
            for i in range(len(repeated)):
                out.append(RuleMatch(self, repeated[i], starts[i], ends[i], self.get_description()))
        return out


# --- StyleTooOftenUsed{Verb,Noun,Adjective}Rule ------------------------------

class StyleTooOftenUsedVerbRule(AbstractStyleTooOftenUsedWordRule):
    """Port of org.languagetool.rules.de.StyleTooOftenUsedVerbRule (default
    off)"""

    DEFAULT_MIN_PERCENT = 5

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)

    def get_limit_message(self, limit):
        return 'Das Verb wird häufiger verwendet als ' + str(limit) + '% aller Verben. ' + \
            'Möglicherweise ist es besser es durch ein Synonym zu ersetzen.'

    def get_id(self):
        return 'TOO_OFTEN_USED_VERB_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Zu häufig genutztes Verb'

    def get_configure_text(self):
        return 'Anzeigen wenn ein Verb häufiger verwendet wird als ...% aller Verben:'

    def is_to_counted_word(self, atr):
        return atr.has_pos_tag_starting_with('VER:')

    def is_exception(self, tokens, n):
        atr = tokens[n]
        return atr.has_pos_tag_starting_with('VER:MOD') or atr.has_pos_tag_starting_with('VER:AUX') or \
            atr.has_pos_tag_starting_with('ART') or atr.has_pos_tag_starting_with('ADJ')

    def to_added_lemma(self, atr):
        return self.get_lemma_for_pos_tag_starts_with('VER:', atr)


class StyleTooOftenUsedNounRule(AbstractStyleTooOftenUsedWordRule):
    """Port of org.languagetool.rules.de.StyleTooOftenUsedNounRule (default
    off)"""

    DEFAULT_MIN_PERCENT = 5

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)

    def get_limit_message(self, limit):
        return 'Das Substantiv wird häufiger verwendet als ' + str(limit) + '% aller Substantive. ' + \
            'Möglicherweise ist es besser es durch ein Synonym zu ersetzen.'

    def get_id(self):
        return 'TOO_OFTEN_USED_NOUN_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Zu häufig genutztes Substantiv'

    def get_configure_text(self):
        return 'Anzeigen wenn ein Substantiv häufiger verwendet wird als ...% aller Substantive:'

    def is_to_counted_word(self, atr):
        return atr.has_pos_tag_starting_with('SUB:')

    def is_exception(self, tokens, n):
        atr = tokens[n]
        return atr.has_pos_tag_starting_with('PRO:') \
            or atr.token == 'Ich' \
            or atr.token == 'Aber' \
            or atr.token == 'Ja' \
            or (n < len(tokens) - 1 and atr.token in ('Frau', 'Herr') and
                (tokens[n + 1].has_pos_tag_starting_with('EIG:') or tokens[n + 1].is_pos_tag_unknown))

    def to_added_lemma(self, atr):
        return self.get_lemma_for_pos_tag_starts_with('SUB:', atr)


class StyleTooOftenUsedAdjectiveRule(AbstractStyleTooOftenUsedWordRule):
    """Port of org.languagetool.rules.de.StyleTooOftenUsedAdjectiveRule
    (default off)"""

    DEFAULT_MIN_PERCENT = 5

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)

    def get_limit_message(self, limit):
        return 'Das Adjektiv wird häufiger verwendet als ' + str(limit) + '% aller Adjektive . ' + \
            'Möglicherweise ist es besser es durch ein Synonym zu ersetzen.'

    def get_id(self):
        return 'TOO_OFTEN_USED_ADJECTIVE_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Zu häufig genutztes Adjektiv'

    def get_configure_text(self):
        return 'Anzeigen wenn ein Adjektiv häufiger verwendet wird als ...% aller Adjektive:'

    def is_to_counted_word(self, atr):
        return atr.has_pos_tag_starting_with('ADJ:')

    def is_exception(self, tokens, n):
        atr = tokens[n]
        return atr.has_pos_tag_starting_with('PRO:') or atr.has_pos_tag_starting_with('ADV:') or \
            atr.has_pos_tag_starting_with('ZUS')

    def to_added_lemma(self, atr):
        return self.get_lemma_for_pos_tag_starts_with('ADJ:', atr)


# --- sentence statistics -----------------------------------------------------

class PassiveSentenceRule(AbstractStatisticSentenceStyleRule):
    """Port of PassiveSentenceRule: statistic of passive sentences (default
    off)"""

    DEFAULT_MIN_PERCENT = 8

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)
        self.sentence_message = None

    def condition_fulfilled(self, sentence):
        """Is passive sentence"""
        i = 0
        n = len(sentence)
        while i < n:
            if sentence[i].has_lemma('werden'):
                atr = sentence[i]
                i += 1
                while i < n:
                    if sentence[i].has_pos_tag_starting_with('VER:PA2:'):
                        return atr
                    elif self.is_mark(sentence[i]):
                        return None
                    i += 1
            elif sentence[i].has_pos_tag_starting_with('VER:PA2:'):
                i += 1
                while i < n:
                    if sentence[i].has_lemma('werden'):
                        return sentence[i]
                    elif self.is_mark(sentence[i]):
                        return None
                    i += 1
            i += 1
        return None

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return 'Passivsatz: Aktiv formulierte Sätze sprechen im Regelfall den Leser stärker an.'
        return 'Mehr als ' + str(limit) + '% Passivsätze {' + str(int(percent + 0.5)) + \
            '%} gefunden. Aktiv formulierte Sätze sprechen im Regelfall den Leser stärker an.'

    def get_id(self):
        return 'PASSIVE_SENTENCE_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Passivsätze'

    def get_configure_text(self):
        return 'Anzeigen wenn mehr als ...% Sätze eines Kapitels Passivsätze sind:'


def _is_modal_verb(atr):
    return atr.has_pos_tag_starting_with('VER:MOD')


class SentenceWithModalVerbRule(AbstractStatisticSentenceStyleRule):
    """Port of SentenceWithModalVerbRule: statistic of sentences with modal
    verbs (default off)"""

    DEFAULT_MIN_PERCENT = 18

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)
        self.sentence_message = None

    def condition_fulfilled(self, sentence):
        """Is sentence with modal verb"""
        i = 0
        n = len(sentence)
        while i < n:
            if _is_modal_verb(sentence[i]):
                atr = sentence[i]
                i += 1
                while i < n:
                    if sentence[i].has_pos_tag_starting_with('VER:INF'):
                        return atr
                    elif self.is_mark(sentence[i]):
                        return None
                    i += 1
            elif sentence[i].has_pos_tag_starting_with('VER:INF'):
                i += 1
                while i < n:
                    if _is_modal_verb(sentence[i]):
                        return sentence[i]
                    elif self.is_mark(sentence[i]):
                        return None
                    i += 1
            i += 1
        return None

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return 'Modalverb: Modalverben blähen den Text häufig auf und sollten vermieden werden.'
        return 'Mehr als ' + str(limit) + '% Sätze mit Modalverben {' + str(int(percent + 0.5)) + \
            '%} gefunden. Modalverben blähen den Text häufig auf und sollten vermieden werden.'

    def get_id(self):
        return 'SENTENCE_WITH_MODAL_VERB_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Sätze mit Modalverben'

    def get_configure_text(self):
        return 'Anzeigen wenn mehr als ...% Sätze eines Kapitels Modalverben enthalten:'


class SentenceWithManRule(AbstractStatisticSentenceStyleRule):
    """Port of SentenceWithManRule: statistic of sentences with 'man'
    (default off, the limit is given in per mil)"""

    DEFAULT_MIN_PERCENT = 15

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)
        self.sentence_message = None

    def condition_fulfilled(self, sentence):
        """Is sentence with 'man'"""
        for atr in sentence:
            if atr.has_lemma('man'):
                return atr
        return None

    def exclude_direct_speech(self):
        return True

    def denominator(self):
        """Minimal value is given in per mil"""
        return 1000.0

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return "Sätze mit der indirekten Leseransprache 'man' sind stilistisch wenig elegant formuliert. " \
                   "Lässt sich das Wort vermeiden?"
        return 'Mehr als ' + str(limit) + "‰ Sätze mit der indirekten Leseransprache 'man' {" + \
            str(int(percent + 0.5)) + '‰} gefunden. Lässt sich das Wort vermeiden?'

    def get_id(self):
        return 'SENTENCE_WITH_MAN_DE'

    def get_description(self):
        return "Statistische Stilanalyse: Sätze mit indirekter Leseransprache 'man'"

    def get_configure_text(self):
        return "Anzeigen wenn mehr als ...‰ Sätze eines Kapitels 'man' enthalten:"


def _is_conjunction(atr):
    return atr.has_pos_tag_starting_with('KON')


def _is_comma(atr):
    return atr.token == ','


class ConjunctionAtBeginOfSentenceRule(AbstractStatisticSentenceStyleRule):
    """Port of ConjunctionAtBeginOfSentenceRule: statistic of sentences
    beginning with a conjunction (default off)"""

    DEFAULT_MIN_PERCENT = 10

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PERCENT)
        self.sentence_message = None

    def condition_fulfilled(self, sentence):
        if len(sentence) < 3:
            return None
        atr = None
        num = 0
        if self.is_opening_quote(sentence[0]):
            num += 1
        if _is_conjunction(sentence[num]):
            atr = sentence[num]
        if atr is None or atr.token in ('Wie', 'Seit', 'Allerdings') or \
                (atr.token == 'Aber' and sentence[num + 1].token == 'auch'):
            return None
        if atr.token == 'Um':
            for i in range(1, len(sentence)):
                if _is_comma(sentence[i]) or sentence[i].token == 'herum':
                    return None
            return atr
        if not atr.has_pos_tag_starting_with('KON:UNT') or atr.token == 'Sondern' or \
                (atr.token == 'Auch' and sentence[num + 1].token == 'wenn'):
            if atr.token == 'Entweder':
                for i in range(1, len(sentence)):
                    if sentence[i].token == 'oder':
                        return None
            elif atr.token == 'Sowohl':
                for i in range(1, len(sentence) - 1):
                    if sentence[i].token == 'als' and sentence[i + 1].token == 'auch':
                        return None
            elif atr.token == 'Weder':
                for i in range(1, len(sentence)):
                    if sentence[i].token == 'noch':
                        return None
            else:
                if sentence[-1].token == '?':
                    return None
                return atr
        for i in range(2, len(sentence)):
            if _is_comma(sentence[i]):
                return None
        return atr

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return 'Eine Konjunktion sollte nur in Ausnahmefällen am Satzanfang verwendet werden. Formulieren Sie ' \
                   'den Satz um, falls möglich.'
        return 'Mehr als ' + str(limit) + '% Sätze beginnen mit einer Konjunktion {' + str(int(percent + 0.5)) + \
            '%} gefunden. Formulieren Sie den Satz um, falls möglich.'

    def get_id(self):
        return 'SENTENCE_BEGINNING_WITH_CONJUNCTION_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Sätze beginnend mit Konjunktion'

    def get_configure_text(self):
        return 'Anzeigen wenn mehr als ...% Sätze eines Kapitels mit einer Konjunktion beginnen:'


# --- word statistics ---------------------------------------------------------

_NON_SIGNIFICANT = ('haben', 'sein', 'machen', 'tun')


def _nsv_is_exception(tokens, num):
    tok = tokens[num].token
    if tok.startswith('sein') or tok.startswith('Sein'):
        return True
    elif tokens[num].has_lemma('machen'):
        for i in range(1, len(tokens)):
            if tokens[i].token in ('Angst', 'Weg', 'frisch', 'bemerkbar', 'aufmerksam'):
                return True
    else:
        is_haben = tokens[num].has_lemma('haben')
        if is_haben:
            for i in range(1, len(tokens)):
                if tokens[i].token in ('Glück', 'Angst', 'Mühe', 'Recht', 'recht'):
                    return True
        if is_haben or tokens[num].has_lemma('sein'):
            for i in range(1, len(tokens)):
                if tokens[i].has_pos_tag_starting_with('PA2') or tokens[i].has_pos_tag_starting_with('VER:PA2') or \
                        tokens[i].token == 'Flucht' or _is_unknown_word(tokens[i]):
                    return True
    return False


class NonSignificantVerbsRule(AbstractStatisticStyleRule):
    """Port of NonSignificantVerbsRule: statistic of verbs with little
    significance (haben, sein, machen, tun; default off, the limit is given
    in per mil)"""

    DEFAULT_MIN_PER_MILL = 8

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PER_MILL)
        self.add_example_pair('Er <marker>machte</marker> einen Kuchen.', 'Das macht mir Angst.')

    def denominator(self):
        """Minimal value is given in per mil"""
        return 1000.0

    def condition_fulfilled(self, tokens, n):
        if tokens[n].has_any_lemma(*_NON_SIGNIFICANT) and not _nsv_is_exception(tokens, n):
            return n
        return -1

    def sentence_condition_fulfilled(self, tokens, n):
        return False

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return 'Dieses Verb hat wenig Aussagekraft. Verwenden Sie wenn möglich ein anderes oder formulieren Sie ' \
                   'den Satz um.'
        return 'Mehr als ' + str(limit) + '‰ wenig aussagekräftige Verben {' + str(int(percent + 0.5)) + \
            '‰} gefunden. Verwenden Sie wenn möglich ein anderes Verb oder formulieren Sie den Satz um.'

    def get_sentence_message(self):
        return None

    def get_id(self):
        return 'NON_SIGNIFICANT_VERB_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Verben mit wenig Aussagekraft'

    def get_configure_percent_text(self):
        return 'Anzeigen wenn mehr als ...‰ eines Kapitels wenig aussagekräftige Verben sind:'

    def get_configure_without_direct_speach_text(self):
        return 'Keine direkte Rede und Zitate berücksichtigen'


_UNNECESSARY_PHRASES = (
    ('dann', 'und', 'wann'),
    ('des', 'Ungeachtet'),
    ('ganz', 'und', 'gar'),
    ('hie', 'und', 'da'),
    ('im', 'Allgemeinen'),
    ('in', 'der', 'Tat'),
    ('in', 'diesem', 'Zusammenhang'),
    ('mehr', 'oder', 'weniger'),
    ('meines', 'Erachtens'),
    ('ohne', 'weiteres'),
    ('ohne', 'Zweifel'),
    ('samt', 'und', 'sonders'),
    ('sowohl', 'als', 'auch'),
    ('voll', 'und', 'ganz'),
    ('von', 'Neuem'),
    ('allem', 'Anschein', 'nach'),
    ('aufs', 'Neue'),
    ('ein', 'bisschen'),
    ('ein', 'wenig'),
    ('des', 'Öfteren'),
    ('bei', 'weitem'),
    ('an', 'sich'),
)


def _first_char_to_lower(tokens, n):
    """the first char of the first word of the sentence in lower case"""
    tok = tokens[n].token
    return tok if (n != 1 or len(tok) < 2) else tok[0].lower() + tok[1:]


def _phrase_is_exception(tokens, phrase):
    if len(phrase) == 2:
        if phrase[0] == 'an' and phrase[1] == 'sich':
            for j in range(1, len(tokens)):
                if tokens[j].has_lemma('drücken'):
                    return True
    return False


class UnnecessaryPhraseRule(AbstractStatisticStyleRule):
    """Port of UnnecessaryPhraseRule: statistic of unnecessary phrases
    (default off, the limit is given in per ten thousand)"""

    DEFAULT_MIN_PER_MILL = 8

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config, self.DEFAULT_MIN_PER_MILL)
        self.add_example_pair('Das ist <marker>allem Anschein nach</marker> eine Phrase.', 'Das ist eine Phrase.')

    def denominator(self):
        return 10000.0

    def condition_fulfilled(self, tokens, n):
        nt = len(tokens)
        for phrase in _UNNECESSARY_PHRASES:
            j = 0
            while j < len(phrase) and n + j < nt and phrase[j] == _first_char_to_lower(tokens, n + j):
                j += 1
            if j == len(phrase):
                if _phrase_is_exception(tokens, phrase):
                    return -1
                return n + len(phrase) - 1
        return -1

    def sentence_condition_fulfilled(self, tokens, n):
        return False

    def exclude_direct_speech(self):
        return True

    def get_limit_message(self, limit, percent):
        if limit == 0:
            return 'Der Ausdruck gilt als Phrase. Es wird empfohlen ihn zu löschen, falls möglich.'
        return 'Mehr als ' + str(limit) + '‱ potenzielle Phrasen {' + str(int(percent + 0.5)) + \
            '‱} gefunden. Es wird empfohlen den Ausdruck zu löschen, falls möglich.'

    def get_sentence_message(self):
        return None

    def get_id(self):
        return 'UNNECESSARY_PHRASES_DE'

    def get_description(self):
        return 'Statistische Stilanalyse: Potenzielle Phrasen'

    def get_configure_percent_text(self):
        return 'Anzeigen wenn mehr als ...‱ eines Kapitels potenzielle Phrasen sind:'

    def get_configure_without_direct_speach_text(self):
        return 'Keine direkte Rede und Zitate berücksichtigen'


# --- RedundantModalOrAuxiliaryVerb -------------------------------------------

_VERB_TEXT = ' scheint redundant zu sein. Prüfen Sie, ob es gelöscht oder der Satz umformuliert werden kann.'
_SUB_TEXT = 'Der Satzteil scheint redundant zu sein. Prüfen Sie, ob es gelöscht oder der Satz umformuliert ' \
            'werden kann.'
_MARKS_REGEX = jregex.compile('[,;.:?!-–—’\'"„“”»«‚‘›‹()\\[\\]]')
_CONJUNCTIONS = ('und', 'oder', 'sowie')
_MOD_AUX_KJ1 = jregex.compile('VER:(AUX|MOD):.*KJ1')


def _is_break_token(s):
    return _MARKS_REGEX.fullmatch(s) is not None or s in _CONJUNCTIONS


def _has_participle_at(n_conj, n_start, tokens):
    if tokens[n_conj - 1].has_pos_tag_starting_with('PA2'):
        participle = tokens[n_conj - 1].token
        for i in range(n_start, len(tokens)):
            s = tokens[i].token
            if _is_break_token(s):
                return -1
            elif s == participle:
                if i == len(tokens) - 1 or _is_break_token(tokens[i + 1].token):
                    return i
                return -1
    return -1


class RedundantModalOrAuxiliaryVerb(CoreRule):
    """Port of RedundantModalOrAuxiliaryVerb: a modal or auxiliary verb
    repeated after a conjunction (default off)."""

    rule_id = 'REDUNDANT_MODAL_VERB'
    category_id = 'STYLE'
    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def get_description(self):
        return 'Redundantes Modal- oder Hilfsverb'

    @staticmethod
    def _verb_msg(is_mod):
        return 'Das ' + ('Modalverb' if is_mod else 'Hilfsverb') + _VERB_TEXT

    def _repeated_verb_match(self, sentence, tokens, nt, n_verb, n_conj, is_mod):
        """the match for the repeated verb at nt (None where the Java code
        breaks without a match) and the suggestion"""
        length = len(tokens)
        if nt - 1 == n_conj:
            if n_verb == n_conj - 1:
                return None, None
            n = 1
            while nt + n < length and java_equals_ignore_case(tokens[nt + n].token, tokens[n_verb + n].token):
                n += 1
            if n > 1:
                if n_verb + n == n_conj:
                    return None, None
                return RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[nt + n - 1].end_pos, _SUB_TEXT), None
            return RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[nt].end_pos, self._verb_msg(is_mod)), None
        if java_equals_ignore_case(tokens[nt - 1].token, tokens[n_verb - 1].token) and \
                tokens[nt - 1].has_pos_tag_starting_with('PRO:PER') and \
                not tokens[nt - 1].has_pos_tag_starting_with('ART'):
            if n_verb == n_conj - 1:
                return RuleMatch(self, sentence, tokens[n_verb - 2].end_pos, tokens[n_verb].end_pos, _SUB_TEXT), None
            return RuleMatch(self, sentence, tokens[nt - 2].end_pos, tokens[nt].end_pos, _SUB_TEXT), None
        if nt + 1 < length and java_equals_ignore_case(tokens[nt + 1].token, tokens[n_verb + 1].token) and \
                (tokens[nt + 1].has_pos_tag_starting_with('PRO:IND') or
                 (tokens[nt + 1].has_pos_tag_starting_with('PRO:PER') and tokens[nt + 1].token != 'Sie' and
                  not tokens[nt + 1].has_pos_tag_starting_with('ART'))):
            if tokens[nt + 1].has_pos_tag_starting_with('PRO:PER:AKK') and \
                    tokens[nt].matches_pos_tag_regex(_MOD_AUX_KJ1):
                return RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[nt].end_pos,
                                 self._verb_msg(is_mod)), None
            return RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[nt + 1].end_pos, _SUB_TEXT), None
        prev = tokens[nt - 1].token
        if tokens[nt - 1].has_pos_tag_starting_with('PRO:PER') \
                or prev == 'da' or prev == 'zu' \
                or tokens[n_verb + 1].token == prev \
                or (nt + 1 < length and (tokens[nt + 1].has_pos_tag_starting_with('PRO:PER')
                                         or prev == tokens[nt + 1].token
                                         or tokens[n_verb - 1].token == tokens[nt + 1].token
                                         or (tokens[n_verb + 1].has_pos_tag_starting_with('VER:MOD') and
                                             tokens[nt + 1].has_pos_tag_starting_with('VER:MOD'))
                                         or (n_verb == n_conj - 1 and not _is_break_token(tokens[nt + 1].token)))) \
                or (n_verb < n_conj - 1 and (nt + 1 == length or _is_break_token(tokens[nt + 1].token))):
            return None, None
        if n_verb == n_conj - 1:
            n = 1
            while n_verb - n > 0 and nt - n > n_conj and tokens[n_verb - n].token == tokens[nt - n].token:
                n += 1
            if n > 1:
                return RuleMatch(self, sentence, tokens[n_verb - n].end_pos, tokens[n_verb].end_pos, _SUB_TEXT), None
            return RuleMatch(self, sentence, tokens[n_verb - 1].end_pos, tokens[n_verb].end_pos,
                             self._verb_msg(is_mod)), None
        pa_at = _has_participle_at(n_conj, nt + 1, tokens)
        if pa_at > 0:
            rm = RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[pa_at].end_pos, _SUB_TEXT)
            suggestion = ''.join(' ' + tokens[i].token for i in range(nt + 1, pa_at))
            return rm, suggestion
        n = 1
        while n + n_verb < n_conj and n + nt < length and tokens[n_verb + n].token == tokens[nt + n].token:
            n += 1
        if n + n_verb == n_conj:
            return RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[nt + n - 1].end_pos, _SUB_TEXT), None
        return RuleMatch(self, sentence, tokens[nt - 1].end_pos, tokens[nt].end_pos, self._verb_msg(is_mod)), None

    def match(self, sentence):
        out = []
        tokens = sentence.non_blank_tokens
        length = len(tokens)
        nt = 2
        while nt < length:
            is_mod = tokens[nt].has_pos_tag_starting_with('VER:MOD')
            if (is_mod or tokens[nt].has_pos_tag_starting_with('VER:AUX')) and nt + 1 < length and \
                    tokens[nt - 1].token != tokens[nt + 1].token:
                verb = tokens[nt].token
                n_verb = nt
                do_break = False
                nt += 1
                while nt < length:
                    s = tokens[nt].token
                    if _MARKS_REGEX.fullmatch(s):
                        break
                    if s in _CONJUNCTIONS:
                        n_conj = nt
                        do_break = True
                        nt += 1
                        while nt < length:
                            s = tokens[nt].token
                            if _is_break_token(s):
                                break
                            if s == verb:
                                rm, suggestion = self._repeated_verb_match(sentence, tokens, nt, n_verb, n_conj,
                                                                           is_mod)
                                if rm is not None:
                                    rm.set_suggested_replacements(['' if suggestion is None else suggestion])
                                    out.append(rm)
                                break
                            nt += 1
                    if do_break:
                        break
                    nt += 1
            nt += 1
        return out


# --- LongSentenceRule (de) ---------------------------------------------------

class LongSentenceRule(_CoreLongSentenceRule):
    """Port of org.languagetool.rules.de.LongSentenceRule: the core
    LongSentenceRule with a German id, description and example (the maximum
    number of words can be configured with the user configuration)."""

    rule_id = 'TOO_LONG_SENTENCE_DE'

    def __init__(self, messages, language=None, user_config=None, max_words=50):
        cf = _config_values(user_config, self.rule_id)
        if cf:
            max_words = int(cf[0])
        super().__init__(messages, language, max_words)
        self.add_example_pair(
            '<marker>Dies ist ein Bandwurmsatz, der immer weiter geht, obwohl das kein guter Stil ist, den man '
            'eigentlich berücksichtigen sollte, obwohl es auch andere Meinungen gibt, die aber in der Minderzahl '
            'sind, weil die meisten Autoren sich doch an die Stilvorgaben halten, wenn auch nicht alle, was aber '
            'letztendlich wiederum eine Sache des Geschmacks ist</marker>.',
            '<marker>Dies ist ein kurzer Satz.</marker>')

    def get_description(self):
        return 'Findet lange Sätze'

    def get_short_message(self):
        return 'Langer Satz'
