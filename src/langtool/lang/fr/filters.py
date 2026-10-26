"""French rule filters (port of the filters of org.languagetool.rules.fr:
AdvancedSynthesizerFilter, DateCheckFilter, DMYDateCheckFilter,
NewYearDateFilter and DateFilterHelper, FindSuggestionsFilter,
FrenchNumberInWordFilter, FrenchPartialPosTagFilter,
FrenchSuppressMisspelledSuggestionsFilter, InterrogativeVerbFilter,
MakeContractionsFilter, SuggestionsFilter and WordWithDeterminerFilter;
PostponedAdjectiveConcordanceFilter is in langtool.lang.fr.agreement)."""

from ... import jregex
from ...analysis import AnalyzedSentence
from ...rules.base import RuleMatch
from ...rules.core_filters import (AbstractAdvancedSynthesizerFilter, AbstractDateCheckWithSuggestionsFilter,
                                   AbstractFindSuggestionsFilter, AbstractNewYearDateFilter,
                                   AbstractNumberInWordFilter, AbstractSuppressMisspelledSuggestionsFilter,
                                   PartialPosTagFilter, _default_tool,
                                   SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY)
from ...rules.filters import RuleFilter
from ...tools import (is_all_uppercase, is_capitalized_word, java_equals_ignore_case, make_wrong, preserve_case,
                      uppercase_first_char)
from .spelling import spelling_suggestions


def _french():
    """French.getInstance()"""
    from ...api import get_language
    return get_language('fr')


class AdvancedSynthesizerFilter(AbstractAdvancedSynthesizerFilter):
    """Port of org.languagetool.rules.fr.AdvancedSynthesizerFilter: the
    AbstractAdvancedSynthesizerFilter without changes (synthesize
    suggestions using the lemma from one token and the POS tag from
    another one)."""


class FrenchSuppressMisspelledSuggestionsFilter(AbstractSuppressMisspelledSuggestionsFilter):
    """Port of org.languagetool.rules.fr.FrenchSuppressMisspelledSuggestionsFilter
    (AbstractSuppressMisspelledSuggestionsFilter with the misspelling check
    of the default spelling rule of French, see langtool.lang.fr.spelling)."""


class FrenchNumberInWordFilter(AbstractNumberInWordFilter):
    """Port of org.languagetool.rules.fr.FrenchNumberInWordFilter: asks the
    MorfologikFrenchSpellerRule (the default spelling rule of French, see
    langtool.lang.fr.spelling) whether a word is misspelled and for its
    spelling suggestions."""

    def is_misspelled(self, word):
        return _french().get_default_spelling_rule().is_misspelled(word)

    def get_suggestions(self, word):
        return spelling_suggestions(_french(), word)


class MakeContractionsFilter(RuleFilter):
    """Port of org.languagetool.rules.fr.MakeContractionsFilter
    (AbstractMakeContractionsFilter): "de le" -> "du", "à le" -> "au",
    "de les" -> "des", "à les" -> "aux" in the suggestions."""

    _DE_LE = jregex.compile('\\bde le\\b', jregex.IGNORECASE | jregex.UNICODE_CHARACTER_CLASS)
    _A_LE = jregex.compile('\\bà le\\b', jregex.IGNORECASE | jregex.UNICODE_CHARACTER_CLASS)
    _DE_LES = jregex.compile('\\bde les\\b', jregex.IGNORECASE | jregex.UNICODE_CHARACTER_CLASS)
    _A_LES = jregex.compile('\\bà les\\b', jregex.IGNORECASE | jregex.UNICODE_CHARACTER_CLASS)

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        new_match = match
        new_match.set_suggested_replacements([self.fix_contractions(s) for s in match.suggested_replacements])
        return new_match

    def fix_contractions(self, suggestion):
        suggestion = jregex.java_replace(self._DE_LE, 'du', suggestion)
        suggestion = jregex.java_replace(self._A_LE, 'au', suggestion)
        suggestion = jregex.java_replace(self._DE_LES, 'des', suggestion)
        suggestion = jregex.java_replace(self._A_LES, 'aux', suggestion)
        return suggestion


class SuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.fr.SuggestionsFilter: removes the
    suggestions that match the regular expression RemoveSuggestionsRegexp
    (case insensitive)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        remove_suggestions_regexp = self.get_required('RemoveSuggestionsRegexp', arguments)
        rule_match = match
        p = jregex.compile(remove_suggestions_regexp, jregex.IGNORECASE)
        rule_match.set_suggested_replacements([r for r in match.suggested_replacements if not p.fullmatch(r)])
        return rule_match


# --- DateFilterHelper ---

# Calendar.getDisplayName(DAY_OF_WEEK, LONG, Locale.FRENCH)
_DAY_NAMES = {SUNDAY: 'dimanche', MONDAY: 'lundi', TUESDAY: 'mardi', WEDNESDAY: 'mercredi', THURSDAY: 'jeudi',
              FRIDAY: 'vendredi', SATURDAY: 'samedi'}
_DAY_PREFIXES = (('dim', SUNDAY), ('lun', MONDAY), ('mar', TUESDAY), ('mer', WEDNESDAY), ('jeu', THURSDAY),
                 ('ven', FRIDAY), ('sam', SATURDAY))
_MONTH_PREFIXES = (('jan', 1), ('fév', 2), ('fev', 2), ('mar', 3), ('avr', 4), ('mai', 5),
                   # "juin" and "juillet" are never abbreviated with 3 letters
                   # since it would be ambiguous (both start with "jui").
                   ('juin', 6), ('juil', 7), ('aou', 8), ('aoû', 8), ('sep', 9), ('oct', 10), ('nov', 11),
                   ('déc', 12), ('dec', 12))


def _get_day_of_week(day_str):
    """DateFilterHelper.getDayOfWeek(String)"""
    day = day_str.lower()
    for prefix, d in _DAY_PREFIXES:
        if day.startswith(prefix):
            return d
    raise RuntimeError("Could not find day of week for '" + day_str + "'")


def _get_day_of_week_name(date):
    """DateFilterHelper.getDayOfWeek(Calendar)"""
    return _DAY_NAMES.get(date.day_of_week, '')


def _get_month(month_str):
    """DateFilterHelper.getMonth"""
    mon = month_str.lower()
    for prefix, m in _MONTH_PREFIXES:
        if mon.startswith(prefix):
            return m
    raise RuntimeError("Could not find month '" + month_str + "'")


class DateCheckFilter(AbstractDateCheckWithSuggestionsFilter):
    """Port of org.languagetool.rules.fr.DateCheckFilter, the French
    localization of AbstractDateCheckWithSuggestionsFilter (with
    DateFilterHelper)."""

    def get_day_of_week(self, day_str):
        return _get_day_of_week(day_str)

    def get_day_of_week_name(self, date):
        return _get_day_of_week_name(date)

    def get_month(self, month_str):
        return _get_month(month_str)

    def get_error_message_wrong_year(self):
        return 'Cette date est incorrecte. Faites-vous référence à l\'année "{currentYear}" ?'


class DMYDateCheckFilter(DateCheckFilter):
    """Port of org.languagetool.rules.fr.DMYDateCheckFilter: a date filter
    that expects a 'date' argument in the format 'dd-mm-yyyy'."""

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if 'year' in args or 'month' in args or 'day' in args:
            raise RuntimeError("Set only 'weekDay' and 'date' for DMYDateCheckFilter")
        date_string = self.get_required('date', args)
        parts = date_string.split('-')
        while parts and parts[-1] == '':
            parts.pop()
        if len(parts) != 3:
            raise RuntimeError("Expected date in format 'dd-mm-yyyy': '" + date_string + "'")
        args = dict(args)
        args['day'] = parts[0]
        args['month'] = parts[1]
        args['year'] = parts[2]
        return super().accept_rule_match(match, args, pattern_token_pos, pattern_tokens, token_positions)


class NewYearDateFilter(AbstractNewYearDateFilter):
    """Port of org.languagetool.rules.fr.NewYearDateFilter (with
    DateFilterHelper)."""

    def get_month(self, month_str):
        return _get_month(month_str)


class FrenchPartialPosTagFilter(PartialPosTagFilter):
    """Port of org.languagetool.rules.fr.FrenchPartialPosTagFilter: a
    PartialPosTagFilter for French that also runs the disambiguator. Note
    that the disambiguator is called with a single token, so only rules
    will apply that have a single <match> element."""

    def tag(self, token):
        french = _french()
        tags = french.tagger.tag([token])
        disambiguated = french.disambiguator.disambiguate(AnalyzedSentence(list(tags)))
        return list(disambiguated.tokens)


_ENDS_IN_VOWEL = jregex.compile('[aeioué]$')
_PRONOUNS_BEFORE_VERBS = jregex.compile("^[smntl]'|^(nous|vous|le|la|les|me|te|se|leur|en|y) ")


class FindSuggestionsFilter(AbstractFindSuggestionsFilter):
    """Port of org.languagetool.rules.fr.FindSuggestionsFilter: the
    spelling suggestions are those of the MorfologikFrenchSpellerRule for
    the word (a wrong word made from it if it is tagged), the word without
    a final "s" and the word with an "s" added after a final vowel; they are
    tagged with the French tagger, the French synthesizer synthesizes
    suggestions from their lemmas. Pronouns before verbs are removed from
    the suggestions (only the first word is kept)."""

    def get_tagger(self):
        return _french().tagger

    def get_synthesizer(self):
        return _french().synthesizer

    def get_spelling_suggestions(self, atr):
        if atr.is_tagged():
            w = make_wrong(atr.token)
        else:
            w = atr.token
        suggestions = []
        words_to_check = [w]
        if w.endswith('s'):
            words_to_check.append(w[:-1])
        if _ENDS_IN_VOWEL.fullmatch(w):  # (Matcher.matches(), so only for one character)
            words_to_check.append(w + 's')
        french = _french()
        for word in words_to_check:
            suggestions.extend(spelling_suggestions(french, word))
        return suggestions

    def clean_suggestion(self, s):
        # remove pronouns before verbs
        output = jregex.java_replace(_PRONOUNS_BEFORE_VERBS, '', s)
        # check only first element
        return output.split(' ')[0] if output.split(' ') else output


def _invented_wrong_word(s):
    """InterrogativeVerbFilter.makeWrong: invent a wrong word to find
    possible replacements. This is a hack to obtain suggestions from the
    speller when the original word is a correct word."""
    # this doesn't work for some cases: ex. tarta / trata
    for c, r in (('a', 'ä'), ('e', 'ë'), ('i', 'í'), ('o', 'ö'), ('u', 'ü'), ('é', 'ë'), ('à', 'ä'), ('è', 'ë'),
                 ('ù', 'ü'), ('â', 'ä'), ('ê', 'ë'), ('î', 'ï'), ('ô', 'ö'), ('û', 'ü')):
        if c in s:
            return s.replace(c, r)
    return s + '-'


class InterrogativeVerbFilter(RuleFilter):
    """Port of org.languagetool.rules.fr.InterrogativeVerbFilter: gets
    appropriate suggestions for French verbs in interrogative form
    (préfères-tu) and imperative (dépêche-toi): the spelling suggestions of
    the verb (or of a wrong word made from it if it is a known word) whose
    POS tag agrees with the pronoun, joined to the pronoun with a hyphen.
    With "je", the past participle of the verb ending in -é is suggested
    with é and è (trompé-je, trompè-je)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        replacements = []
        pronoun_from = self.get_required('PronounFrom', arguments)
        verb_from = self.get_required('VerbFrom', arguments)
        desired_postag = None
        extra_suggestions = []
        if pronoun_from is not None and verb_from is not None:
            pos_pronoun = int(pronoun_from)
            if pos_pronoun < 1 or pos_pronoun > len(pattern_tokens):
                raise ValueError('ConfusionCheckFilter: Index out of bounds in ' + match.rule.get_full_id()
                                 + ', PronounFrom: ' + str(pos_pronoun))
            pos_verb = int(verb_from)
            if pos_verb < 1 or pos_verb > len(pattern_tokens):
                raise ValueError('ConfusionCheckFilter: Index out of bounds in ' + match.rule.get_full_id()
                                 + ', VerbFrom: ' + str(pos_verb))
            atr_pronoun = pattern_tokens[pos_pronoun - 1]
            # vous
            if atr_pronoun.matches_pos_tag_regex('R pers obj 2 p'):
                desired_postag = 'V.* (imp) [23] [sp]|V .*(ind|cond).* 2 p'
            # nous
            elif atr_pronoun.matches_pos_tag_regex('R pers obj 1 p'):
                desired_postag = 'V.* (imp) .*|V .*(ind|cond).* 1 p'
            # moi, toi, le, la, lui, nous, vous, les, leur
            elif atr_pronoun.matches_pos_tag_regex('R pers obj.*'):
                desired_postag = 'V.* (imp) .*'
            elif atr_pronoun.matches_pos_tag_regex('.* 1 s'):
                desired_postag = 'V .*(ind|cond).* 1 s'
                atr_verb = pattern_tokens[pos_verb - 1]
                reading = atr_verb.reading_with_tag_regex('V .*')
                if reading is not None:
                    participles = _french().synthesizer.synthesize(reading, 'V ppa [me] sp?', True)
                    if participles:
                        if participles[0].endswith('é'):
                            extra_suggestions.append(participles[0])
                            extra_suggestions.append(participles[0][:-1] + 'è')
            elif atr_pronoun.matches_pos_tag_regex('.* 2 s'):
                desired_postag = 'V .*(ind|cond).* 2 s'
            elif atr_pronoun.matches_pos_tag_regex('.* 3( [mfe])? s'):
                desired_postag = 'V .*(ind|cond).* 3 s'
            elif atr_pronoun.matches_pos_tag_regex('.* 1 p'):
                desired_postag = 'V .*(ind|cond).* 1 p'
            elif atr_pronoun.matches_pos_tag_regex('.* 2 p'):
                desired_postag = 'V .*(ind|cond).* 2 p'
            elif atr_pronoun.matches_pos_tag_regex('.* 3( [mf])? p'):
                desired_postag = 'V .*(ind|cond).* 3 p'

            separator = '' if atr_pronoun.token.startswith('-') else '-'
            # add: trompè-je and trompé-je for original sentence "trompe-je"
            if extra_suggestions:
                for extra_suggestion in extra_suggestions:
                    complete_suggestion = extra_suggestion + separator + atr_pronoun.token
                    if complete_suggestion not in replacements and not complete_suggestion.endswith('e-je'):
                        # exclude trompe-je
                        replacements.append(complete_suggestion)
            elif desired_postag is not None:
                verb = pattern_tokens[pos_verb - 1]
                word = _invented_wrong_word(verb.token) if verb.is_tagged() else verb.token
                french = _french()
                suggestions = spelling_suggestions(french, word)
                if suggestions:
                    desired = jregex.compile(desired_postag)
                    for analyzed_suggestion in french.tagger.tag(suggestions):
                        if analyzed_suggestion.matches_pos_tag_regex(desired):
                            complete_suggestion = analyzed_suggestion.token + separator + atr_pronoun.token
                            if java_equals_ignore_case(complete_suggestion, 'peux-je'):
                                complete_suggestion = preserve_case('puis-je', complete_suggestion)
                            if complete_suggestion.endswith('e-je'):
                                # exclude trompe-je -> trompé-je, trompè-je
                                complete_suggestion = complete_suggestion[:-4] + 'é-je'
                                if complete_suggestion not in replacements:
                                    replacements.append(complete_suggestion)
                                complete_suggestion = complete_suggestion[:-4] + 'è-je'
                                if complete_suggestion not in replacements:
                                    replacements.append(complete_suggestion)
                            elif complete_suggestion not in replacements:
                                replacements.append(complete_suggestion)
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                               match.short_message)
        rule_match.type = match.type
        if replacements:
            rule_match.set_suggested_replacements(replacements)
        return rule_match


# --- WordWithDeterminerFilter ---

_DET_PATTERN = jregex.compile('(P.)?D .*|J .*|V.* ppa .*')
_WORD_PATTERN = jregex.compile('[ZNJ] .*|V.* ppa .*')
# 0=MS, 1=FS, 2=MP, 3=FP
_GENDER_NUMBER = ('([me]) (s|sp)', '([fe]) (s|sp)', '([me]) (p|sp)', '([fe]) (p|sp)')
_GENDER_NUMBER_SUFFIX = tuple(jregex.compile('.+' + gn) for gn in _GENDER_NUMBER)
_DETERMINER = '((P.)?D |J |V.* ppa )'
_EXCEPTIONS_DETERMINER = frozenset(('bels', 'fols', 'mols', 'nouvels'))
_CATEGORY_TO_CHECK = 'CAT_ELISION'
_RULES_TO_CHECK = frozenset(('CET_CE', 'CE_CET', 'MA_VOYELLE', 'MON_NFS', 'VIEUX'))


def _get_analyzed_token(atr, pattern):
    for at in atr.readings:
        pos_tag = at.pos_tag
        if pos_tag is None:
            pos_tag = 'UNKNOWN'
        if pattern.fullmatch(pos_tag):
            return at
    return None


class WordWithDeterminerFilter(RuleFilter):
    """Port of org.languagetool.rules.fr.WordWithDeterminerFilter: creates
    suggestions for determiner + noun/adjective (arguments determinerFrom
    and wordFrom): both words are synthesized in all genders and numbers;
    the combinations that the elision rules (category CAT_ELISION and the
    rules CET_CE, CE_CET, MA_VOYELLE, MON_NFS and VIEUX) find errors in are
    discarded. The suggestions of the XML rule come first."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lt = _default_tool(_french())
        word_from = self.get_required('wordFrom', arguments)
        determiner_from = self.get_required('determinerFrom', arguments)
        if word_from is not None and determiner_from is not None:
            pos_word = int(word_from)
            if pos_word < 1 or pos_word > len(pattern_tokens):
                raise ValueError('WordWithDeterminerFilter: Index out of bounds in ' + match.rule.get_full_id()
                                 + ', wordFrom: ' + str(pos_word))
            pos_determiner = int(determiner_from)
            if pos_determiner < 1 or pos_determiner > len(pattern_tokens):
                raise ValueError('WordWithDeterminerFilter: Index out of bounds in ' + match.rule.get_full_id()
                                 + ', posDeterminer: ' + str(pos_word))
        else:
            raise ValueError('WordWithDeterminerFilter: undefined parameters wordFrom or determinerFrom in '
                             + match.rule.get_full_id())
        atr_determiner = pattern_tokens[pos_determiner - 1]
        atr_word = pattern_tokens[pos_word - 1]
        is_determiner_capitalized = is_capitalized_word(atr_determiner.token)
        is_word_capitalized = is_capitalized_word(atr_word.token)
        is_determiner_allupper = (is_all_uppercase(atr_determiner.token)
                                  and not java_equals_ignore_case(atr_determiner.token, "L'"))
        is_word_allupper = is_all_uppercase(atr_word.token)
        at_determiner = _get_analyzed_token(atr_determiner, _DET_PATTERN)
        at_word = _get_analyzed_token(atr_word, _WORD_PATTERN)
        if at_word is None or at_determiner is None:
            raise RuntimeError("Error analyzing sentence: '" + match.sentence.text + "' with rule "
                               + match.rule.get_full_id())
        is_noun = at_word.pos_tag.startswith('N') or at_word.pos_tag.startswith('Z')
        is_adjective = at_word.pos_tag.startswith('J')
        prefix = '[ZNJ] '
        if is_noun and not is_adjective:
            prefix = '[NZ] '
        elif not is_noun and is_adjective:
            prefix = 'J '
        synth = _french().synthesizer
        # synthesize all forms
        determiner_forms = []
        word_forms = []
        for i in range(4):
            det_forms = synth.synthesize(at_determiner, _DETERMINER + _GENDER_NUMBER[i], True)
            w_forms = synth.synthesize(at_word, prefix + _GENDER_NUMBER[i], True)
            # if it cannot be synthesyzed, keep the original determiner
            if not det_forms and _GENDER_NUMBER_SUFFIX[i].fullmatch(at_determiner.pos_tag):
                det_forms = [at_determiner.token]
            # if it cannot be synthesyzed, keep the original word
            if not w_forms and _GENDER_NUMBER_SUFFIX[i].fullmatch(at_word.pos_tag):
                w_forms = [at_word.token]
            determiner_forms.append(det_forms)
            word_forms.append(w_forms)
        # generate suggestions
        replacements = []
        for i in range(4):
            for word in word_forms[i]:
                for determiner in determiner_forms[i]:
                    if determiner in _EXCEPTIONS_DETERMINER:
                        continue
                    if determiner is not None and word is not None:
                        if is_determiner_capitalized:
                            determiner = uppercase_first_char(determiner)
                        if is_word_capitalized:
                            word2 = uppercase_first_char(word)
                        else:
                            word2 = word
                        if is_determiner_allupper:
                            determiner = determiner.upper()
                        if is_word_allupper:
                            word2 = word2.upper()
                        r = determiner + ' ' + word2
                        r = r.replace("' ", "'")
                        # remove suggestions with errors
                        if self._suggestion_has_no_errors(r, lt) and r not in replacements:
                            if r.endswith(at_word.token):
                                replacements.insert(0, r)
                            else:
                                replacements.append(r)
        rule_match = RuleMatch(match.rule, match.sentence, match.from_pos, match.to_pos, match.message,
                               match.short_message)
        rule_match.type = match.type
        # add existing suggestion in the XML rule
        replacements[0:0] = match.suggested_replacements
        if replacements:
            rule_match.set_suggested_replacements(replacements)
        return rule_match

    @staticmethod
    def _suggestion_has_no_errors(new_suggestion, lt):
        analyzed_sentence = lt.analyze_text(new_suggestion)[0]
        # (= the rules of lt.get_all_active_rules() with the category or id, in order; the cheap tests first)
        rules_with = getattr(lt, 'rules_with', None)
        rules = rules_with(_RULES_TO_CHECK, (_CATEGORY_TO_CHECK,)) if rules_with is not None else lt.get_all_rules()
        for r in rules:
            if ((r.category is not None and r.category.id == _CATEGORY_TO_CHECK)
                    or r.get_id() in _RULES_TO_CHECK) and not lt.ignore_rule(r):
                if r.match(analyzed_sentence):
                    return False
        return True
