"""Port of org.languagetool.tagging.uk.UkrainianTagger."""

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import BaseTagger, TaggedWord
from ...tools import is_mixed_case
from . import helpers
from . import pos_tag_helper as pth
from .compound_tagger import LEFT_O_ADJ_INVALID_PATTERN, CompoundTagger, is_possible_adj_adj_ending
from .tokenizers import WORDS_WITH_BRACKETS_PATTERN

_c = jregex.compile
_I = jregex.IGNORECASE

IGNORED_CHARS = _c('[\u00AD\u0301]')

_NUMBER = _c('[-+±]?[0-9]+(,[0-9]+)?([-–—][0-9]+(,[0-9]+)?)?|\\d{1,3}([\\s\u00A0\u202F]\\d{3})+')
# full latin number regex: M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})
_LATIN_NUMBER = _c('(?=[MDCLXVI])M*(C[MD]|D?C*)(X[CL]|L?X*)(I[XV]|V?I*)')
_LATIN_NUMBER_CYR = _c('[IXІХV]{2,4}(-[а-яі]{1,4})?|[IXІХV](-[а-яі]{1,4})')
_HASHTAG = _c('#[а-яіїєґa-z_][а-яіїєґa-z0-9_]*', _I)

_DATE = _c('[\\d]{1,2}\\.[\\d]{1,2}\\.[\\d]{4}')
_TIME = _c('([01]?[0-9]|2[0-3])[.:][0-5][0-9]|([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]')
_ALT_DASHES_IN_WORD = _c('[а-яіїєґ0-9a-z]–[а-яіїєґ]|[а-яіїєґ]–[0-9]', _I)
_COMPOUND_WITH_QUOTES_REGEX = _c('[-–][«"„]')
_COMPOUND_WITH_QUOTES_REGEX2 = _c('[»"“][-–]')
_MISSING_APO = _c('([бвгґдзкмнпрстфхш])([єїюя])')
_MISSING_HYPHEN = _c("([а-яіїєґ']+)(небудь)", _I)
_CAPS_INSIDE_WORD = _c("[а-яіїєґ'-]*[а-яіїєґ][А-ЯІЇЄҐ][а-яіїєґ][а-яіїєґ'-]*")
_PATTERN_MD = _c('[MD]+')
_QUOTES = _c('[«»"„“]')
_YI_PATTERN = _c('([бвгґджзклмнпрстфхцчшщ])ї', _I)
_RICCHA = _c("(сто|[а-яіїєґ']+?(?:сот))?([а-яіїє']+?(?:ти|ка|то))?([а-яіїє']+?(?:ти|ри|ох|ми|во))?(річч[а-яі]{1,3})",
             _I)
_OTYI = _c("(сто|[а-яіїєґ']+?(?:сот))?([а-яіїє']+?(?:ти|ка|то))?([а-яіїє']+?(?:ти|ри|ох|ми|во|но))?"
           "((?:мільйон|тисяч|річн)[а-яії]+)", _I)
_Z_INSTEAD_OF_S = _c('(?iu)з[кптфх].+')
_MISSING_APO_FILTER = _c('(?!.*:(bad|arch|alt|abbr|slang|subst|short|long)).*')
_NUM_BAD = _c('.*(bad|subst).*')
_ADJ_START = _c('^adj.*')
_REPEATED_VOWELS = _c('([аеєиіїоуюя])\\1{2,}', _I)
_NOT_PROP_ABBR = _c('(?!noun.*:prop|.*abbr).*')
_PROP_OR_NONINFL = _c('noun.*?:prop.*|noninfl.*')
_ADJ = _c('adj.*')
_S_START = _c('^с')
_S_START_UPPER = _c('^С')
_Z_START = _c('^з')
_Z_START_UPPER = _c('^З')


def _tokens(word, tagged_words):
    return [AnalyzedToken(word, tw.pos_tag, tw.lemma) for tw in tagged_words]


class UkrainianTagger(BaseTagger):
    """Ukrainian part-of-speech tagger: a BaseTagger for /uk/ukrainian.dict
    (from the morfologik-ukrainian-lt dictionary, with added.txt,
    added_custom.txt, removed.txt and removed_custom.txt; uppercase words are
    not tagged with lowercase readings: tagLowercaseWithUppercase false), the
    tagset is described in tagset.txt. Unknown words get additional tags:
    numbers, Latin numbers, times, dates, entities, hashtags, typos (missing
    apostrophe, з for с, ї for і, ...) and compound words with hyphens (see
    CompoundTagger). The results are cached per word."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'uk', resource_dir, tag_lowercase_with_uppercase=False)
        self.compound_tagger = CompoundTagger(self, self.word_tagger)
        self._uk_cache = {}

    def get_word_tagger(self):
        """we need to expose this as some rules want to know if the word is in
        the dictionary"""
        return self.word_tagger

    def as_analyzed_token_list_for_tagged_words(self, word, tagged_words):
        return _tokens(word, tagged_words)

    def tag(self, sentence_tokens):
        out = []
        pos = 0
        for word in sentence_tokens:
            out.append(AnalyzedTokenReadings(self.get_analyzed_tokens(word), pos))
            pos += len(word)
        return out

    def get_analyzed_tokens(self, word):
        cached = self._uk_cache.get(word)
        if cached is None:
            cached = tuple((t.token, t.pos_tag, t.lemma) for t in self._get_analyzed_tokens(word))
            if len(self._uk_cache) > 100000:
                self._uk_cache.clear()
            self._uk_cache[word] = cached
        return [AnalyzedToken(token, tag, lemma) for token, tag, lemma in cached]

    # --- BaseTagger.getAnalyzedTokens (with the Ukrainian additionalTags) ---

    def _word_tag(self, word):
        return list(self.word_tagger.tag(word))

    def _base_analyzed_tokens(self, word):
        result = []
        lower_word = word.lower()
        is_lowercase = word == lower_word
        is_mixed = is_mixed_case(word)
        tagger_tokens = _tokens(word, self._word_tag(word))
        lower_tagger_tokens = _tokens(word, self._word_tag(lower_word)) if not is_lowercase else tagger_tokens
        result.extend(tagger_tokens)
        if not is_lowercase and not is_mixed:
            result.extend(lower_tagger_tokens)
        # (tagLowercaseWithUppercase is false)
        if not result:
            additional = self.additional_tags_uk(word)
            if additional:
                result.extend(additional)
        if not result:
            result.append(AnalyzedToken(word, None, None))
        return result

    def additional_tags_uk(self, word):
        """UkrainianTagger.additionalTags: a list of AnalyzedToken or None"""
        word_tagger = self.word_tagger
        if _NUMBER.fullmatch(word):
            return [AnalyzedToken(word, 'number', word)]

        if _LATIN_NUMBER.fullmatch(word) and not _PATTERN_MD.fullmatch(word):
            return [AnalyzedToken(word, 'number:latin', word)]

        if _LATIN_NUMBER_CYR.fullmatch(word):
            ordinal = False
            dash_idx = word.rfind('-')
            if dash_idx > 0:
                left = word[:dash_idx]
                right = word[dash_idx + 1:]
                ordinal = is_possible_adj_adj_ending(left, right)
            if dash_idx == -1 or ordinal:
                return [AnalyzedToken(word, 'number:latin:bad', word)]

        if _TIME.fullmatch(word):
            return [AnalyzedToken(word, 'time', word)]

        if _DATE.fullmatch(word):
            return [AnalyzedToken(word, 'date', word)]

        if word.find('(') > 0 or word.find('/') > 0:
            new_tokens = self.compound_tagger.generate_entities(word)
            if new_tokens:
                return new_tokens

        if word.startswith('#') and _HASHTAG.fullmatch(word):
            return [AnalyzedToken(word, 'hashtag', word)]

        if len(word) > 5 and _CAPS_INSIDE_WORD.fullmatch(word):
            wd_list = list(word_tagger.tag(word.lower()))
            if wd_list:
                wd_list = pth.adjust(wd_list, None, None, ':alt')
                return _tokens(word, wd_list)

        # помилка - «з» замість «с» перед губними
        if len(word) > 5 and _Z_INSTEAD_OF_S.fullmatch(word):
            new_word = jregex.java_replace(_Z_START_UPPER, 'С', jregex.java_replace(_Z_START, 'с', word, 1), 1)
            wd_list = self.compound_tagger.tag_both_cases(new_word, None)
            if wd_list:
                wd_list = [TaggedWord(jregex.java_replace(_S_START_UPPER, 'З',
                                                          jregex.java_replace(_S_START, 'з', w.lemma, 1), 1),
                                      pth.add_if_not_contains(w.pos_tag, ':alt'))
                           for w in wd_list]
                return _tokens(word, wd_list)

        # дївчина
        if len(word) > 3 and 'ї' in word:
            word2 = jregex.java_replace(_YI_PATTERN, '$1і', word)
            wd_list = list(word_tagger.tag(word2))
            if wd_list:
                wd_list = pth.adjust(wd_list, None, None, ':alt')
                return _tokens(word, wd_list)

        if len(word) > 4:
            if _MISSING_APO.search(word):
                wd_list = list(word_tagger.tag(jregex.java_replace(_MISSING_APO, "$1'$2", word, 1)))
                wd_list = pth.filter2(wd_list, _MISSING_APO_FILTER)
                if wd_list:
                    wd_list = [TaggedWord(w.lemma, pth.add_if_not_contains(w.pos_tag, ':bad')) for w in wd_list]
                    return _tokens(word, wd_list)

        if len(word) > 5:
            m = _MISSING_HYPHEN.fullmatch(word)
            if m:
                wd_list = list(word_tagger.tag(m.group(1).lower()))
                if wd_list and pth.has_pos_tag_part2(wd_list, 'pron'):
                    wd_list = pth.adjust(wd_list, None, '-' + m.group(2).lower(), ':bad')
                    return _tokens(word, wd_list)

        word = IGNORED_CHARS.sub('', word)

        if len(word) >= 3 and word.find('-') > 0:
            # екс-«депутат»
            # "заступницю"-колаборантку
            if len(word) >= 6:
                if _COMPOUND_WITH_QUOTES_REGEX.search(word) or _COMPOUND_WITH_QUOTES_REGEX2.search(word):
                    adjusted_word = _QUOTES.sub('', word)
                    return self._get_adjusted_analyzed_tokens(word, adjusted_word, None, None, None)
            return self.compound_tagger.guess_compound_tag(word)

        # стодвадцятиріччя
        if len(word) >= 10:
            m1 = _RICCHA.fullmatch(word)
            if m1:
                end_word = m1.group(4)
                right_wd_list = list(word_tagger.tag('сто' + end_word))
                if not right_wd_list:
                    return []
                if not self._is_all_num(m1, 1, 3):
                    return []
                out = []
                for at in right_wd_list:
                    pos_tag = at.pos_tag
                    if pos_tag is None or 'v_kly' in pos_tag or ':p:' in pos_tag:
                        continue
                    lemma = _concat_groups(m1, 1, 3) + at.lemma[3:]
                    out.append(AnalyzedToken(word, at.pos_tag, lemma))
                return out
            m2 = _OTYI.fullmatch(word)
            if m2:
                end_word = m2.group(4)
                right_wd_list = list(word_tagger.tag(end_word))
                if not right_wd_list:
                    return []
                if not self._is_all_num(m2, 1, 3):
                    return []
                out = []
                for at in right_wd_list:
                    pos_tag = at.pos_tag
                    if pos_tag is None or not pos_tag.startswith('adj') or 'v_kly' in pos_tag:
                        continue
                    lemma = _concat_groups(m2, 1, 3) + at.lemma
                    out.append(AnalyzedToken(word, at.pos_tag, lemma))
                return out

        return self.compound_tagger.guess_other_tags(word)

    def _is_all_num(self, m, frm, to):
        for ii in range(frm, to + 1):
            group = m.group(ii)
            if group:
                w = list(self.word_tagger.tag(group.lower()))
                if not pth.has_pos_tag_part2(w, 'num') or pth.has_pos_tag2(w, _NUM_BAD):
                    return False
        return True

    # --- UkrainianTagger.getAnalyzedTokens ---

    def _get_analyzed_tokens(self, word):
        if word.find('`') > 0:
            word = word.replace('`', "'")

        tokens = self._base_analyzed_tokens(word)

        if len(word) < 2:
            return tokens

        if tokens[0].has_no_tag():
            orig_word = word

            if len(word) > 2:
                if word.find('–') > 0 and _ALT_DASHES_IN_WORD.search(word):
                    word = orig_word.replace('–', '-')
                    new_tokens = self._base_analyzed_tokens(word)
                    if new_tokens and not new_tokens[0].has_no_tag():
                        new_tokens.append(AnalyzedToken(orig_word, None, None))
                        tokens = new_tokens
                # try г instead of ґ
                elif 'ґ' in word or 'Ґ' in word:
                    tokens = self._convert_tokens(tokens, word, 'ґ', 'г', ':alt')
                elif 'ія' in word:
                    tokens = self._convert_tokens(tokens, word, 'ія', 'іа', ':alt')
                elif word.endswith('тер'):
                    tokens = self._convert_tokens(tokens, word, 'тер', 'тр', ':alt')
                elif 'льо' in word:
                    tokens = self._convert_tokens(tokens, word, 'льо', 'ло', ':alt')
                elif word.startswith('сьвя'):
                    tokens = self._convert_tokens(tokens, word, 'сьвя', 'свя', ':arch')
                elif word.startswith('сьві'):
                    tokens = self._convert_tokens(tokens, word, 'сьві', 'сві', ':arch')
                elif 'ьск' in word and not word.endswith('ская') and word != 'Комсомольском':
                    tokens = self._convert_tokens(tokens, word, 'ьск', 'ьськ', ':bad')

                if tokens[0].has_no_tag():
                    if len(word) >= 3:
                        if len(word) >= 9:
                            m2 = LEFT_O_ADJ_INVALID_PATTERN.fullmatch(word)
                            if m2:
                                prefix = m2.group(1)
                                adjusted_word = m2.group(2)
                                new_tokens = self._get_adjusted_analyzed_tokens(
                                    word, adjusted_word, _ADJ_START, None, lambda lemma: prefix + lemma)
                                if new_tokens:
                                    tokens = new_tokens
                        # гааа
                        if tokens[0].has_no_tag() and word.lower() != 'ііі':  # often stands for Latin number
                            if _REPEATED_VOWELS.search(word):
                                adjusted_word = jregex.java_replace(_REPEATED_VOWELS, '$1', word)
                                new_tokens = self._get_adjusted_analyzed_tokens(
                                    word, adjusted_word, _NOT_PROP_ABBR, ':alt', lambda lemma: lemma)
                                if new_tokens:
                                    tokens = new_tokens
                        if tokens[0].has_no_tag() and '[' in word and ']' in word and \
                                WORDS_WITH_BRACKETS_PATTERN.search(word):
                            adjusted_word = word.replace('[', '').replace(']', '')
                            new_tokens = self._get_adjusted_analyzed_tokens(word, adjusted_word, None, ':alt',
                                                                            lambda lemma: lemma)
                            if new_tokens:
                                tokens = new_tokens

        # try УКРАЇНА as Україна and СИРІЮ as Сирію
        if len(word) > 2 and helpers.is_all_uppercase_uk(word):
            new_word = helpers.capitalize_proper_name(word)
            new_tokens = self._get_adjusted_analyzed_tokens(word, new_word, _PROP_OR_NONINFL, None, None)
            if new_tokens:
                if tokens[0].has_no_tag():
                    # TODO: add special tags if necessary
                    tokens = new_tokens
                else:
                    tokens.extend(new_tokens)

        # Івано-Франківська as adj from івано-франківський
        analyzed_tokens = self.analyze_all_capitalized_adj(word)
        if analyzed_tokens:
            if tokens[0].has_no_tag():
                tokens = analyzed_tokens
            else:
                # compound tagging has already been performed and may have added tokens
                for token in analyzed_tokens:
                    if token not in tokens:
                        tokens.append(token)
        return tokens

    def analyze_all_capitalized_adj(self, word):
        """analyzeAllCapitamizedAdj"""
        if word.find('-') > 1 and not word.endswith('-'):
            parts = word.split('-')
            while parts and parts[-1] == '':
                parts.pop()
            if all(helpers.is_capitalized(p) for p in parts):
                lower_cased_word = word.lower()
                wd_list = list(self.word_tagger.tag(lower_cased_word))
                if pth.has_pos_tag_part2(wd_list, 'adj'):
                    return pth.filter_tokens(_tokens(word, wd_list), _ADJ)
        return []

    def _convert_tokens(self, orig_tokens, word, s, dict_s, additional_tag):
        adjusted_word = word.replace(s, dict_s)
        if len(s) == 1:
            adjusted_word = adjusted_word.replace(s.upper(), dict_s.upper())
        new_tokens = self._get_adjusted_analyzed_tokens(word, adjusted_word, None, additional_tag,
                                                        lambda lemma: lemma.replace(dict_s, s))
        if not new_tokens:
            return orig_tokens
        return new_tokens

    def _get_adjusted_analyzed_tokens(self, word, adjusted_word, pos_tag_regex, additional_tag, lemma_function):
        new_tokens = self._base_analyzed_tokens(adjusted_word)
        if new_tokens[0].has_no_tag():
            return []
        out = []
        for at in new_tokens:
            pos_tag = at.pos_tag
            # filter out tokens with accents etc with null pos tag
            if adjusted_word == at.token and (pos_tag_regex is None or pos_tag_regex.fullmatch(pos_tag)):
                lemma = at.lemma
                if lemma_function is not None:
                    lemma = lemma_function(lemma)
                if additional_tag is not None:
                    pos_tag = pth.add_if_not_contains(pos_tag, additional_tag)
                out.append(AnalyzedToken(word, pos_tag, lemma))
        return out


def _concat_groups(m, i, j):
    return ''.join(m.group(ii) for ii in range(i, j + 1) if m.group(ii) is not None)
