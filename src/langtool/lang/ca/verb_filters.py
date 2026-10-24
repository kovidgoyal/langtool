"""Ports of the filters of org.languagetool.rules.ca that change verbs,
weak pronouns and the gender/number of nominal groups:
AdjustVerbSuggestionsFilter, AdjustPronounsFilter,
ConvertToGenderAndNumberFilter, SynthesizeWithDAFilter,
SynthesizeWithAnyDeterminerFilter and PossessiusRedundantsFilter."""

from ... import jregex
from ...analysis import AnalyzedToken
from ...chunking import ChunkTag
from ...rules.base import RuleMatch
from ...rules.core_filters import _default_tool, adapt_suggestion
from ...rules.filters import RuleFilter
from ...tools import is_digit, is_punctuation_mark, java_split, java_trim, preserve_case, uppercase_first_char
from .helpers import (NORMALIZED, REFLEXIVE_PRONOUNS, all_need_same_apostrophation_ms,
                      convert_pronouns_for_intransitive_verb, do_add_pronoun_en, do_add_pronoun_reflexive,
                      do_add_pronoun_reflexive_en, do_add_pronoun_reflexive_imperative, do_remove_pronoun_reflexive,
                      do_replace_em_en, fix_apostrophes, get_dative_pronoun, get_preposition_and_determiner,
                      get_reflexive_pronoun, needs_apostrophation_ms, transform, transform_darrere, transform_davant)
from .synthesis import VerbSynthesizer


def _first_token_index(tokens, match):
    """The index of the first token (without whitespace) of the match"""
    pos_word = 0
    while pos_word < len(tokens) and (tokens[pos_word].start_pos < match.from_pos
                                      or tokens[pos_word].is_sentence_start):
        pos_word += 1
    return pos_word


def _new_match(match, from_pos, to_pos):
    """new RuleMatch(match.getRule(), match.getSentence(), from, to, message, shortMessage) + setType"""
    rule_match = RuleMatch(match.rule, match.sentence, from_pos, to_pos, match.message, match.short_message)
    rule_match.type = match.type
    return rule_match


def _preserve_case_word_by_word(input_string, model_string):
    """StringTools.preserveCaseWordByWord"""
    input_words = input_string.split(' ')
    model_words = model_string.split(' ')
    if len(input_words) != len(model_words):
        return preserve_case(input_string, model_string)
    return ' '.join(preserve_case(w, m) for w, m in zip(input_words, model_words))


def _is_match_at_sentence_start(tokens, match):
    """RuleFilter.isMatchAtSentenceStart"""
    i = 0
    while i < len(tokens) and tokens[i].start_pos < match.from_pos:
        i += 1
    while i > 0 and is_punctuation_mark(tokens[i].token):
        i -= 1
    return i == 0


_NEEDS_APOSTROPHE_CHANGE = ('de', "d'", 'l', "l'", 'el')
_NEEDS_CONTRACTION_CHANGE = ('a', 'de', 'per', 'pe')
_PERSONA = jregex.compile('[123]')


def _any_change_vowel_consonant(original_verb, replacements):
    original_verb_needs_apostrophe = needs_apostrophation_ms(original_verb)
    return any(original_verb_needs_apostrophe != needs_apostrophation_ms(r) for r in replacements)


class AdjustVerbSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.AdjustVerbSuggestionsFilter: the
    suggestions are lemmas (optionally with words after the verb and the
    marks " [intr]", " [3s]" and "[datiu] "); the verb of the match
    (single or multi-word) is synthesized with the new lemma and the
    weak pronouns are adjusted (argument actions: removePronounReflexive by
    default, addPronounEn, addPronounReflexive...; lemmas ending in -se,
    -se'n, -hi, -s'ho, -se-les, -s'hi set the action). The match is
    extended to the pronouns and, if the apostrophation changes, to the
    preceding article/preposition."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = self.get_language_from_rule_match(match)
        lt = _default_tool(lang)
        synth = lang.synthesizer
        replacements = []
        number_from_next_words = self.get_optional('numberFromNextWords', arguments, 'false').lower() == 'true'
        actions = java_split(self.get_optional('actions', arguments, 'removePronounReflexive'), ',')
        force_number = self.get_optional('forceNumber', arguments, '')
        tokens = match.sentence.get_tokens_without_whitespace()
        pos_word = _first_token_index(tokens, match)
        verb_synthesizer = VerbSynthesizer(tokens, pos_word, lang)
        # verb found out of bounds
        if verb_synthesizer.is_undefined() or tokens[verb_synthesizer.get_last_verb_index()].end_pos > match.to_pos:
            return None
        for original_suggestion in match.suggested_replacements:
            original_suggestion = original_suggestion.lower()
            make_intransitive = False
            desired_number = ''
            desired_persona = ''
            action = actions[0]
            if original_suggestion.endswith(' [intr]'):
                original_suggestion = original_suggestion[:-7]
                make_intransitive = True
            if original_suggestion.endswith(' [3s]'):
                original_suggestion = original_suggestion[:-5]
                desired_number = 'S'
                desired_persona = '3'
            if original_suggestion.startswith('[datiu] '):
                original_suggestion = original_suggestion[8:]
                action = 'addPronounDative'
            first_space_index = original_suggestion.find(' ')
            new_lemma = original_suggestion
            after_lemma = ''
            if first_space_index != -1:
                new_lemma = original_suggestion[:first_space_index]
                after_lemma = original_suggestion[first_space_index + 1:]
                tokens_after_lemma = lt.analyze_text(after_lemma)
                if number_from_next_words:
                    desired_number = ('S' if tokens_after_lemma[0].get_tokens_without_whitespace()[1]
                                      .has_partial_pos_tag('S') else 'P')
            if 'haver-hi' in new_lemma:
                desired_number = 'S'
            if force_number:
                desired_number = force_number
            if new_lemma.endswith("-se'n"):
                new_lemma = new_lemma[:-5]
                action = 'addPronounReflexiveEn'
            elif new_lemma.endswith('-se'):
                new_lemma = new_lemma[:-3]
                action = 'addPronounReflexive'
            elif new_lemma.endswith("'s"):
                new_lemma = new_lemma[:-2]
                action = 'addPronounReflexive'
            elif new_lemma.endswith('-hi'):
                new_lemma = new_lemma[:-3]
                action = 'addPronounHi'
            elif new_lemma.endswith("-s'ho"):
                new_lemma = new_lemma[:-5]
                action = 'addPronounReflexiveHo'
            elif new_lemma.endswith('-se-les'):
                new_lemma = new_lemma[:-7]
                action = 'addPronounReflexiveLes'
            elif new_lemma.endswith("-s'hi"):
                new_lemma = new_lemma[:-5]
                action = 'addPronounReflexiveHi'
            # synthesize with new lemma
            postags = []
            for reading in tokens[verb_synthesizer.get_first_verb_index()]:
                if reading.pos_tag is not None and reading.pos_tag.startswith('V'):
                    postag = reading.pos_tag
                    if desired_number:
                        if postag[2:3] != 'P' and (postag[5:6] == 'S' or postag[5:6] == 'P'):
                            postag = postag[:5] + desired_number + postag[6:]
                    if desired_persona:
                        if postag[2:3] != 'P' and _PERSONA.fullmatch(postag[4:5]):
                            postag = postag[:4] + desired_persona + postag[5:]
                    postags.append(postag)
            target_postag = synth.get_target_pos_tag(postags, '')
            if not target_postag:
                return None
            verb_synthesizer.set_lemma_and_postag(new_lemma, target_postag)
            verb_str = verb_synthesizer.synthesize()
            pronouns_str = ''
            is_pronouns_after = verb_synthesizer.get_num_pronouns_after() > 0 or not verb_synthesizer.is_first_verb_is()
            if verb_synthesizer.get_num_pronouns_before() > 0:
                pronouns_str = verb_synthesizer.get_pronouns_str_before()
            elif verb_synthesizer.get_num_pronouns_after() > 0:
                pronouns_str = verb_synthesizer.get_pronouns_str_after()
            pronouns_str = pronouns_str.lower()
            if action == 'addPronounDative':
                first_verb_persona_number = verb_synthesizer.get_first_verb_persona_number()
            else:
                first_verb_persona_number = target_postag[4:6]
            replacement = ''
            if action == 'addPronounEn':
                new_pronoun = do_add_pronoun_en(pronouns_str, verb_str, not verb_synthesizer.is_first_verb_is())
                if new_pronoun:
                    replacement = (new_pronoun + verb_str if verb_synthesizer.is_first_verb_is()
                                   else verb_str + new_pronoun)
            elif action == 'removePronounReflexive':
                replacement = do_remove_pronoun_reflexive(pronouns_str, verb_str, is_pronouns_after)
            elif action == 'addPronounReflexiveEn':
                replacement = do_add_pronoun_reflexive_en(pronouns_str, verb_str, first_verb_persona_number,
                                                          is_pronouns_after)
            elif action == 'replaceEmEn':  # not used
                replacement = do_replace_em_en(pronouns_str, verb_str, is_pronouns_after)
            elif action == 'addPronounReflexive':
                replacement = do_add_pronoun_reflexive(pronouns_str, verb_str, first_verb_persona_number,
                                                       is_pronouns_after)
            elif action == 'addPronounReflexiveHi':
                replacement = do_add_pronoun_reflexive('', 'hi ' + verb_str, first_verb_persona_number,
                                                       is_pronouns_after)
            elif action == 'addPronounReflexiveLes':
                replacement = do_add_pronoun_reflexive(transform(pronouns_str.lower(), NORMALIZED) + ' les', verb_str,
                                                       first_verb_persona_number, is_pronouns_after)
            elif action == 'addPronounDative':
                dative_pronoun = get_dative_pronoun(first_verb_persona_number)
                if is_pronouns_after:
                    replacement = verb_str + transform_darrere(dative_pronoun, verb_str)
                else:
                    replacement = transform_davant(dative_pronoun, verb_str) + verb_str
            elif action == 'addPronounReflexiveHo':
                reflexive_pronoun = get_reflexive_pronoun(first_verb_persona_number)
                if not reflexive_pronoun and pronouns_str:
                    rp = transform(pronouns_str, NORMALIZED)
                    if rp in REFLEXIVE_PRONOUNS:
                        reflexive_pronoun = rp
                if not reflexive_pronoun:
                    reflexive_pronoun = 'es'
                pronouns_normalized = reflexive_pronoun + ' ho'
                if is_pronouns_after:
                    replacement = verb_str + transform_darrere(pronouns_normalized, verb_str)
                else:
                    replacement = transform_davant(pronouns_normalized, verb_str) + verb_str
            elif action == 'addPronounHi':  # S'ignoren altres pronoms?
                replacement = 'hi ' + verb_str
            elif action == 'addPronounReflexiveImperative':  # TODO
                replacement = do_add_pronoun_reflexive_imperative(pronouns_str, verb_str, first_verb_persona_number)
            elif action == 'None':
                if is_pronouns_after:
                    replacement = verb_str + transform_darrere(pronouns_str, verb_str)
                else:
                    replacement = transform_davant(pronouns_str, verb_str) + verb_str
            if replacement:
                if make_intransitive:
                    replacement = convert_pronouns_for_intransitive_verb(replacement)
                replacement = fix_apostrophes(replacement)
                replacement = java_trim(replacement + ' ' + after_lemma)
                replacements.append(preserve_case(replacement, verb_synthesizer.get_casing_model()))
        if not replacements:
            return None
        pos_start_underline = verb_synthesizer.get_first_verb_index() - verb_synthesizer.get_num_pronouns_before()
        if (verb_synthesizer.get_num_pronouns_before() == 0 and pos_start_underline > 1
                and tokens[pos_start_underline - 1].token.lower() in _NEEDS_APOSTROPHE_CHANGE
                and _any_change_vowel_consonant(verb_synthesizer.get_verb_str(), replacements)):
            prefix = []
            if (pos_start_underline > 2
                    and tokens[pos_start_underline - 2].token.lower() in _NEEDS_CONTRACTION_CHANGE):
                prefix.append(verb_synthesizer.get_string_from_to(pos_start_underline - 2,
                                                                  pos_start_underline - 1).lower())
                if tokens[pos_start_underline].whitespace_before:
                    prefix.append(' ')
                pos_start_underline -= 2
            else:
                prefix.append(tokens[pos_start_underline - 1].token.lower())
                if tokens[pos_start_underline].whitespace_before:
                    prefix.append(' ')
                pos_start_underline -= 1
            prefix = ''.join(prefix)
            replacements = [prefix + r for r in replacements]
        # extend the ending position if there are pronouns after the verb
        ending_pos = max(match.to_pos, tokens[verb_synthesizer.get_last_index()].end_pos)
        rule_match = _new_match(match, tokens[pos_start_underline].start_pos, ending_pos)
        original_str = match.sentence.text[tokens[pos_start_underline].start_pos:match.to_pos]
        rule_match.set_suggested_replacements([adapt_suggestion(lang, r, original_str) for r in replacements])
        return rule_match


class AdjustPronounsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.AdjustPronounsFilter: adds or
    removes weak pronouns ("en", reflexive...) of the verb of the match in
    the required place with all the necessary transformations (argument
    actions, optionally newLemma and newOnlyLemma), moving the match
    positions to the verb and its pronouns."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        replacements = []
        actions = java_split(self.get_required('actions', arguments), ',')
        new_lemma = self.get_optional('newLemma', arguments)
        new_only_lemma = self.get_optional('newOnlyLemma', arguments)
        tokens = match.sentence.get_tokens_without_whitespace()
        pos_word = _first_token_index(tokens, match)
        verb_synthesizer = VerbSynthesizer(tokens, pos_word, self.get_language_from_rule_match(match))
        if verb_synthesizer.is_undefined():
            return None
        verb_str = verb_synthesizer.get_verb_str()
        if new_lemma is not None:
            verb_synthesizer.set_lemma(new_lemma)
            verb_str = verb_synthesizer.synthesize()
        verb_str2 = verb_str
        if new_only_lemma is not None:
            verb_synthesizer.set_lemma(new_only_lemma)
            verb_str2 = verb_synthesizer.synthesize()
        first_verb_persona_number = verb_synthesizer.get_first_verb_persona_number()
        pronouns_str = ''
        if verb_synthesizer.get_num_pronouns_before() > 0:
            pronouns_str = verb_synthesizer.get_pronouns_str_before()
        elif verb_synthesizer.get_num_pronouns_after() > 0:
            pronouns_str = verb_synthesizer.get_pronouns_str_after()
        start_underline_index = verb_synthesizer.get_first_verb_index() - verb_synthesizer.get_num_pronouns_before()
        end_underline_index = verb_synthesizer.get_last_verb_index() + verb_synthesizer.get_num_pronouns_after()
        for action in actions:
            replacement = ''
            if action == 'removePronounEn':
                pr = pronouns_str.replace('en', '').replace("n'", '').replace("'n", '').strip()
                replacement = transform_davant(pr, verb_str) + verb_str
            elif action == 'addPronounEn':
                new_pronoun = do_add_pronoun_en(pronouns_str, verb_str, not verb_synthesizer.is_first_verb_is())
                if new_pronoun:
                    replacement = (new_pronoun + verb_str if verb_synthesizer.is_first_verb_is()
                                   else verb_str + new_pronoun)
            elif action == 'removePronounReflexive':
                replacement = do_remove_pronoun_reflexive(pronouns_str, verb_str, False)
            elif action == 'replaceEmEn':
                replacement = do_replace_em_en(pronouns_str, verb_str, False)
            elif action == 'replaceHiEn':
                replacement = do_add_pronoun_en(transform(java_trim(pronouns_str.replace('hi', '')), NORMALIZED),
                                                verb_str, False) + verb_str
            elif action == 'addPronounReflexive':
                replacement = do_add_pronoun_reflexive(pronouns_str, verb_str, first_verb_persona_number,
                                                       not verb_synthesizer.is_first_verb_is())
            elif action == 'addPronounReflexiveHi':
                replacement = do_add_pronoun_reflexive(pronouns_str, 'hi ' + verb_str, first_verb_persona_number,
                                                       False)
            elif action == 'addPronounReflexiveImperative':
                replacement = do_add_pronoun_reflexive_imperative(
                    pronouns_str, verb_str, verb_synthesizer.get_first_verb_persona_number_imperative())
            elif action == 'changeOnlyLemma':
                if 'replaceHiEn' in actions:
                    pronouns_str = java_trim(pronouns_str.replace('hi', ''))
                pronouns_str = transform_davant(pronouns_str, verb_str2)
                replacement = pronouns_str + verb_str2
            if replacement and replacement.lower() != verb_synthesizer.get_whole_original_str().lower():
                replacements.append(preserve_case(replacement, verb_synthesizer.get_casing_model()))
        if not replacements:
            return None
        rule_match = _new_match(match, tokens[start_underline_index].start_pos, tokens[end_underline_index].end_pos)
        rule_match.set_suggested_replacements(replacements)
        return rule_match


_SPLIT_GENDER_NUMBER = jregex.compile('(N.|A..|V.P..|D..|PX.)(.)(.)(.*)')
_SPLIT_GENDER_NUMBER_NO_NOUN = jregex.compile('(A..|V.P..|D..|PX.)(.)(.)(.*)')
_SPLIT_GENDER_NUMBER_ADJECTIVE = jregex.compile('(A..|V.P..|PX.)(.)(.)(.*)')
_FORMS_TO_IGNORE = ('mes', 'las')
_POSTAG_EXCEPTIONS = jregex.compile('NP.*|AQ0CN0|SPS00|[CP].*')
_GV = ChunkTag('GV')


class _GenderAndNumberSplit:
    __slots__ = ('prefix', 'suffix', 'gender', 'number')


def _split_gender_and_number(atr):
    """ConvertToGenderAndNumberFilter.splitGenderAndNumber"""
    if atr is None or atr.pos_tag is None:
        return None
    m = _SPLIT_GENDER_NUMBER.fullmatch(atr.pos_tag)
    if m:
        results = _GenderAndNumberSplit()
        results.prefix = m.group(1)
        results.suffix = m.group(4)
        g2 = m.group(2)
        g3 = m.group(3)
        if results.prefix.startswith('V'):
            results.gender = g3
            results.number = g2
        else:
            results.gender = g2
            results.number = g3
        return results
    return None


def _synthesize_with_gender_and_number(atr, split_postag, gender, number, synth):
    """ConvertToGenderAndNumberFilter.synthesizeWithGenderAndNumber"""
    parts = atr.token.split(' ', 1)
    remainder = parts[1] if len(parts) > 1 else ''
    if split_postag.prefix.startswith('V'):
        gender, number = number, gender
    add_gender = 'C'
    if split_postag.prefix.startswith('DA'):
        add_gender = ''
    synthesized = synth.synthesize(atr, split_postag.prefix + '[' + gender + add_gender + ']' + '[' + number + 'N'
                                   + ']' + split_postag.suffix, True)
    if synthesized:
        synthesized_suggestion = synthesized[0]
        if remainder:
            synthesized_suggestion = synthesized_suggestion + ' ' + remainder
        return synthesized_suggestion
    return ''


class ConvertToGenderAndNumberFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.ConvertToGenderAndNumberFilter:
    converts the word of the match (the reading matching lemmaSelect, or
    the suggestions, or the word with newLemma) and the words of its
    nominal group before (determiners, adjectives) and after (adjectives)
    it to the desired gender and number (arguments gender and number, by
    default those of the word), adding the article and preposition if
    needed (keepOriginal: the word itself is not changed)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        tokens = match.sentence.get_tokens_without_whitespace()
        lang = self.get_language_from_rule_match(match)
        synth = lang.synthesizer
        tagger = lang.tagger
        pos_word = _first_token_index(tokens, match)
        desired_gender_orig_str = self.get_optional('gender', arguments, '')
        desired_number_orig_str = self.get_optional('number', arguments, '')
        lemma_select = self.get_required('lemmaSelect', arguments)  # it could be optional
        new_lemma = self.get_optional('newLemma', arguments, '')
        keep_original = self.get_optional('keepOriginal', arguments, 'false').lower() == 'true'
        suggestions = []
        atr_noun_list = []
        atr_noun_orig = tokens[pos_word].reading_with_tag_regex(lemma_select)
        if new_lemma and atr_noun_orig is not None:
            atr_noun_list.append(AnalyzedToken(atr_noun_orig.token, atr_noun_orig.pos_tag, new_lemma))
        elif match.suggested_replacements:
            split_noun_orig_postag = None
            if atr_noun_orig is not None:
                split_noun_orig_postag = _split_gender_and_number(atr_noun_orig)
            for suggestion in match.suggested_replacements:
                parts = suggestion.split(' ', 1)
                word = parts[0]
                remainder = parts[1] if len(parts) > 1 else ''
                atrs = tagger.tag([word])
                at = atrs[0].reading_with_tag_regex(_SPLIT_GENDER_NUMBER)
                if at is None or at.pos_tag is None or atrs[0].reading_with_tag_regex(_POSTAG_EXCEPTIONS) is not None:
                    # if there is any suggestion without gender and number, use the list of suggestions with no
                    # change
                    suggestions.extend(match.suggested_replacements)
                    atr_noun_list.clear()
                    break
                split_postag = _split_gender_and_number(at)
                new_postag = [split_postag.prefix]
                if desired_number_orig_str:
                    number = desired_number_orig_str
                elif split_noun_orig_postag is not None and split_noun_orig_postag.number != 'N':
                    number = split_noun_orig_postag.number
                else:
                    number = split_postag.number
                gender = desired_gender_orig_str if desired_gender_orig_str else split_postag.gender
                if split_postag.prefix.startswith('V'):
                    new_postag.append(number + gender)
                else:
                    new_postag.append(gender + number)
                new_postag.append(split_postag.suffix)
                complete_form = at.lemma
                if remainder:
                    complete_form = word + ' ' + remainder
                atr_noun_list.append(AnalyzedToken(complete_form, ''.join(new_postag), at.lemma))
        else:
            atr_noun_list.append(atr_noun_orig)
        start_pos = pos_word
        end_pos = pos_word
        all_need_same = all_need_same_apostrophation_ms(tokens[pos_word].token, atr_noun_list)
        for atr_noun in atr_noun_list:
            start_pos = pos_word
            end_pos = pos_word
            split_postag = _split_gender_and_number(atr_noun)
            desired_gender_str = desired_gender_orig_str if desired_gender_orig_str else split_postag.gender
            desired_number_str = desired_number_orig_str if desired_number_orig_str else split_postag.number
            # if gender = C, look into the words before and after
            if desired_gender_str == 'C' and pos_word - 1 > 0:
                split_postag2 = _split_gender_and_number(
                    tokens[pos_word - 1].reading_with_tag_regex(_SPLIT_GENDER_NUMBER))
                if split_postag2 is not None and split_postag2.gender in ('F', 'M'):
                    desired_gender_str = split_postag2.gender
            if desired_gender_str == 'C' and pos_word + 1 < len(tokens):
                split_postag2 = _split_gender_and_number(
                    tokens[pos_word + 1].reading_with_tag_regex(_SPLIT_GENDER_NUMBER))
                if split_postag2 is not None and split_postag2.gender in ('F', 'M'):
                    desired_gender_str = split_postag2.gender
            # if number = N, look into the words before and after
            if desired_number_str == 'N' and pos_word - 1 > 0:
                split_postag2 = _split_gender_and_number(
                    tokens[pos_word - 1].reading_with_tag_regex(_SPLIT_GENDER_NUMBER))
                if split_postag2 is not None and split_postag2.number in ('S', 'P'):
                    desired_number_str = split_postag2.number
            if desired_number_str == 'N' and pos_word + 1 < len(tokens):
                split_postag2 = _split_gender_and_number(
                    tokens[pos_word + 1].reading_with_tag_regex(_SPLIT_GENDER_NUMBER))
                if split_postag2 is not None and split_postag2.number in ('S', 'P'):
                    desired_number_str = split_postag2.number
            # Prioritize gender and number in the original
            if split_postag is not None:
                if split_postag.gender in desired_gender_str:
                    desired_gender_str = split_postag.gender + desired_gender_str.replace(split_postag.gender, '')
                if split_postag.number in desired_number_str:
                    desired_number_str = split_postag.number + desired_number_str.replace(split_postag.number, '')
            for desired_gender in desired_gender_str:
                for desired_number in desired_number_str:
                    suggestion = self._suggestion(match, tokens, pos_word, atr_noun, split_postag, desired_gender,
                                                  desired_number, keep_original, all_need_same, synth)
                    if suggestion is None:
                        continue
                    suggestion, start_pos, end_pos, ignore_this_suggestion = suggestion
                    # TODO: una d'aquests vessants; una dels vessants
                    if not ignore_this_suggestion:
                        suggestions.append(suggestion)
        if not suggestions:
            return None
        original_str = match.sentence.text[tokens[start_pos].start_pos:tokens[end_pos].end_pos]
        if original_str in suggestions:
            return None
        rule_match = _new_match(match, tokens[start_pos].start_pos, tokens[end_pos].end_pos)
        rule_match.set_suggested_replacements(suggestions)
        return rule_match

    @staticmethod
    def _suggestion(match, tokens, pos_word, atr_noun, split_postag, desired_gender, desired_number, keep_original,
                    all_need_same, synth):
        """One suggestion: (suggestion, start_pos, end_pos,
        ignore_this_suggestion), None if it is the unchanged word"""
        start_pos = pos_word
        end_pos = pos_word
        suggestion_builder = ''
        ignore_this_suggestion = False
        if not keep_original:
            s = _synthesize_with_gender_and_number(atr_noun, split_postag, desired_gender, desired_number, synth)
            if not s:
                ignore_this_suggestion = True
            suggestion_builder += s
        else:
            suggestion_builder += atr_noun.token
        # backwards
        stop = False
        i = pos_word
        preposition_to_add = ''
        add_determiner = False
        added_demonstrative = False
        conditional_added_string = ''
        add_tot = ''
        while not stop and i > 1:
            i -= 1
            t = tokens[i]
            atr = t.reading_with_tag_regex(_SPLIT_GENDER_NUMBER_NO_NOUN)
            if ((not t.has_pos_tag_starting_with('D')  # incloem l'article fins i tot si està marcat com a _GV_
                 and (t.has_pos_tag('_perfet') or t.has_pos_tag('_GV_') or _GV in t.chunk_tags))
                    or t.token.lower() in _FORMS_TO_IGNORE):
                atr = None
            if atr is not None and atr.pos_tag is not None and atr.lemma is not None:
                if atr.pos_tag.startswith('DA'):
                    suggestion_builder = conditional_added_string + suggestion_builder
                    conditional_added_string = ''
                    add_determiner = True
                    start_pos = i
                elif not add_determiner and not added_demonstrative:
                    s = _synthesize_with_gender_and_number(atr, _split_gender_and_number(atr), desired_gender,
                                                           desired_number, synth)
                    if not s:
                        ignore_this_suggestion = True
                    if s == 'bo':
                        s = 'bon'
                    suggestion_builder = conditional_added_string + suggestion_builder
                    conditional_added_string = ''
                    if tokens[i + 1].whitespace_before:
                        suggestion_builder = ' ' + suggestion_builder
                    suggestion_builder = s + suggestion_builder
                    start_pos = i
                    if atr.pos_tag.startswith('DD'):
                        added_demonstrative = True
                    if (atr.pos_tag.startswith('D') and not atr.pos_tag.startswith('DN') and not added_demonstrative
                            and atr.lemma.lower() != 'quant'):
                        stop = True
                else:
                    # only before "el/aquest/aquell...": tota l'estona, tota aquella estona
                    if atr.lemma == 'tot':
                        s = _synthesize_with_gender_and_number(atr, _split_gender_and_number(atr), desired_gender,
                                                               desired_number, synth)
                        if s:
                            add_tot = s + ' '
                            start_pos = i
                    stop = True
            elif t.has_pos_tag('SPS00') or t.has_pos_tag('LOC_PREP'):
                if add_determiner:
                    preposition = t.token.lower()
                    if preposition == 'pe':
                        preposition = 'per'
                    if preposition == "d'":
                        preposition = 'de'
                    if preposition in ('a', 'de', 'per'):
                        preposition_to_add = preposition
                        start_pos = i
                elif not all_need_same and (t.token.lower() == "d'" or t.token.lower() == 'de'):
                    start_pos = i
                    preposition_to_add = 'de'
                stop = True
            elif t.has_pos_tag('_PUNCT_CONT') or t.has_pos_tag('CC'):
                if (pos_word - i == 1
                        # tot i que
                        or (i > 1 and t.token.lower() == 'i' and tokens[i - 1].token.lower() == 'tot')):
                    stop = True
                else:
                    conditional_added_string = t.token + ' ' + conditional_added_string
            elif (t.has_pos_tag_starting_with('RG')
                  # adverbi envoltat d'elements que tenen gènere i nombre
                  and (i <= 1 or tokens[i - 1].reading_with_tag_regex(_SPLIT_GENDER_NUMBER) is not None)
                  and (i >= len(tokens) - 1 or tokens[i + 1].reading_with_tag_regex(_SPLIT_GENDER_NUMBER) is not None)):
                conditional_added_string = t.token + ' ' + conditional_added_string
            else:
                stop = True
        # forwards
        stop = False
        i = pos_word
        conditional_added_string = ''
        is_there_conjunction = False
        while not stop and i < len(tokens) - 1:
            i += 1
            t = tokens[i]
            if t.token.lower() in _FORMS_TO_IGNORE:
                break
            atr = t.reading_with_tag_regex(_SPLIT_GENDER_NUMBER_ADJECTIVE)
            if is_there_conjunction and t.has_pos_tag_starting_with('NC'):
                atr = None
            if atr is not None:
                s = _synthesize_with_gender_and_number(atr, _split_gender_and_number(atr), desired_gender,
                                                       desired_number, synth)
                if not s:
                    ignore_this_suggestion = True
                suggestion_builder += conditional_added_string
                conditional_added_string = ''
                suggestion_builder += ' ' + s
                end_pos = i
            elif t.has_pos_tag_starting_with('RG'):
                conditional_added_string += ' ' + t.token
            elif t.has_pos_tag('CC'):
                is_there_conjunction = True
                conditional_added_string += ' ' + t.token
            elif t.has_pos_tag('_PUNCT_CONT'):
                conditional_added_string += t.token
            else:
                stop = True
        if add_determiner:
            suggestion_builder = get_preposition_and_determiner(suggestion_builder, desired_gender + desired_number,
                                                                preposition_to_add) + suggestion_builder
        elif preposition_to_add:
            if preposition_to_add == 'de' and needs_apostrophation_ms(suggestion_builder):
                preposition_to_add = "d'"
            else:
                preposition_to_add = preposition_to_add + ' '
            suggestion_builder = preposition_to_add + suggestion_builder
        suggestion_builder = add_tot + suggestion_builder
        original_span = match.sentence.text[tokens[start_pos].start_pos:tokens[end_pos].end_pos]
        suggestion = _preserve_case_word_by_word(suggestion_builder, original_span)
        if end_pos == pos_word and start_pos == pos_word and tokens[pos_word].token == suggestion:
            return None
        return suggestion, start_pos, end_pos, ignore_this_suggestion


_GENDER_NUMBER_LIST = ('MS', 'FS', 'MP', 'FP')
_GENDER_NUMBER_PATTERNS = {
    'MS': jregex.compile('(N|A.).[MC][SN].*|V.P.*SM.'),
    'FS': jregex.compile('(N|A.).[FC][SN].*|V.P.*SF.'),
    'MP': jregex.compile('(N|A.).[MC][PN].*|V.P.*PM.'),
    'FP': jregex.compile('(N|A.).[FC][PN].*|V.P.*PF.'),
}
_DET = jregex.compile('D.*')


def _is_numeric(s):
    """StringUtils.isNumeric"""
    return bool(s) and all(is_digit(c) for c in s)


class SynthesizeWithDAFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.SynthesizeWithDAFilter: adds
    suggestions with the definite article (and the preposition of the
    argument prepositionFrom) before the forms of the word at lemmaFrom
    (the reading matching lemmaSelect; all the synthesized forms with
    synthAllForms)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        synth = self.get_language_from_rule_match(match).synthesizer
        lemma_from_str = self.get_required('lemmaFrom', arguments)
        lemma_select = self.get_required('lemmaSelect', arguments)
        synth_all_forms = self.get_optional('synthAllForms', arguments, 'false').lower() == 'true'
        preposition_from_str = self.get_optional('prepositionFrom', arguments, '')
        lemma_from = self.get_position(lemma_from_str, pattern_tokens, match)
        preposition = ''
        if _is_numeric(preposition_from_str):
            preposition_from = self.get_position(preposition_from_str, pattern_tokens, match)
            preposition = pattern_tokens[preposition_from].token[:1].lower()
        elif preposition_from_str:
            # a=a d=de per=p
            preposition = preposition_from_str[:1]
        suggestions = []
        original_word = pattern_tokens[lemma_from].token
        p = jregex.compile(lemma_select)
        is_sentence_start = _is_match_at_sentence_start(match.sentence.get_tokens_without_whitespace(), match)
        # original word form in the first place
        original_at = pattern_tokens[lemma_from].reading_with_tag_regex(lemma_select)
        if original_at is None:
            raise ValueError('Cannot find analyzed token readings with postag ' + lemma_select + ' in sentence'
                             + match.sentence.text)
        potential_suggestions = [original_at]
        # second-best suggestion
        second_gender_number = ''
        if lemma_from - 1 > 0:
            reading = pattern_tokens[lemma_from - 1].reading_with_tag_regex(_DET)
            if reading is not None:
                second_gender_number = reading.pos_tag[3:5]
        for tag in list(synth.get_possible_tags()):
            if p.fullmatch(tag):
                for synth_form in synth.synthesize(original_at, tag) or ():
                    at = AnalyzedToken(synth_form, tag, original_at.lemma)
                    if not synth_all_forms and synth_form.lower() != original_word.lower():
                        continue
                    if at not in potential_suggestions:
                        if (second_gender_number in tag
                                or second_gender_number[1:2] + second_gender_number[0:1] in tag):
                            potential_suggestions.insert(1, at)
                        else:
                            potential_suggestions.append(at)
        for potential_suggestion in potential_suggestions:
            new_form = potential_suggestion.token
            for gender_number in _GENDER_NUMBER_LIST:
                if _GENDER_NUMBER_PATTERNS[gender_number].fullmatch(potential_suggestion.pos_tag):
                    suggestion = (get_preposition_and_determiner(new_form, gender_number, preposition)
                                  + preserve_case(new_form, original_word))
                    if is_sentence_start:
                        suggestion = uppercase_first_char(suggestion)
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        match.add_suggested_replacements(suggestions)
        return match


_PREPOSITIONS = ('a', 'de', 'per', 'pe')


def _list_contains_analyzed_token(items, at):
    return any(item.lemma == at.lemma and item.pos_tag == at.pos_tag for item in items)


class SynthesizeWithAnyDeterminerFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.SynthesizeWithAnyDeterminerFilter:
    the suggestions are the forms of the word of the match (the reading
    matching lemmaSelect) with the determiner before it (any determiner,
    synthesized for the gender and number; definite articles with the
    preposition), the match is extended to the determiner and
    preposition."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        synth = self.get_language_from_rule_match(match).synthesizer
        synth_all_forms = self.get_optional('synthAllForms', arguments, 'false').lower() == 'true'
        lemma_select = self.get_required('lemmaSelect', arguments)
        tokens = match.sentence.get_tokens_without_whitespace()
        pos_word = _first_token_index(tokens, match)
        if pos_word >= len(tokens):
            pos_word = len(tokens) - 1
        original_word = tokens[pos_word].token
        original_at = tokens[pos_word].reading_with_tag_regex(lemma_select)
        if original_at is None:
            raise ValueError('Cannot find analyzed token readings with postag ' + lemma_select + ' in sentence'
                             + match.sentence.text)
        second_gender_number = ''
        determiner_type = ''
        determiner_reading = None
        between_token = None
        preposition = ''
        done = False
        k = 1
        first_underlined_token = pos_word
        while pos_word - k > 0 and not done:
            done = True
            t = tokens[pos_word - k]
            if determiner_reading is None:
                determiner_reading = t.reading_with_tag_regex(_DET)
                if determiner_reading is not None:
                    second_gender_number = determiner_reading.pos_tag[3:5]
                    determiner_type = determiner_reading.pos_tag[0:2]
                    done = determiner_type != 'DA'
                    first_underlined_token = pos_word - k
            if t.has_pos_tag('_QM_OPEN'):
                between_token = t
                done = False
            if t.token in _PREPOSITIONS:
                # a=a d=de per=p
                preposition = t.token[:1].lower()
                first_underlined_token = pos_word - k
            k += 1
        between_string = between_token.token if between_token is not None else ''
        suggestions = []
        p = jregex.compile(lemma_select)
        # original word form in the first place
        potential_suggestions = [original_at]
        # second-best suggestion from the determiner
        for tag in list(synth.get_possible_tags()):
            if p.fullmatch(tag):
                for synth_form in synth.synthesize(original_at, tag) or ():
                    at = AnalyzedToken(synth_form, tag, original_at.lemma)
                    if not synth_all_forms and synth_form.lower() != original_word.lower():
                        continue
                    if not _list_contains_analyzed_token(potential_suggestions, at):
                        if (second_gender_number in tag
                                or second_gender_number[1:2] + second_gender_number[0:1] in tag):
                            potential_suggestions.insert(1, at)
                        else:
                            potential_suggestions.append(at)
        first_token = tokens[first_underlined_token].token
        for potential_suggestion in potential_suggestions:
            new_form = potential_suggestion.token
            for gender_number in _GENDER_NUMBER_LIST:
                if not _GENDER_NUMBER_PATTERNS[gender_number].fullmatch(potential_suggestion.pos_tag):
                    continue
                if determiner_type == 'DA' or not determiner_type:
                    suggestion = (preserve_case(get_preposition_and_determiner(new_form, gender_number, preposition),
                                                first_token)
                                  + between_string + preserve_case(new_form, original_word))
                    if first_underlined_token == 1:
                        suggestion = uppercase_first_char(suggestion)
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
                else:
                    synth_forms = synth.synthesize(determiner_reading, determiner_type + '.[C' + gender_number[0]
                                                   + ']' + gender_number[1] + '.', True)
                    for synth_form in synth_forms or ():
                        suggestion = (preserve_case(synth_form, first_token) + ' ' + between_string
                                      + preserve_case(new_form, original_word))
                        if first_underlined_token == 1:
                            suggestion = uppercase_first_char(suggestion)
                        if suggestion not in suggestions:
                            suggestions.append(suggestion)
        rule_match = _new_match(match, tokens[first_underlined_token].start_pos, match.to_pos)
        rule_match.set_suggested_replacements(suggestions)
        return rule_match


_PX = jregex.compile('PX.*')
_P = jregex.compile('P.*')


class PossessiusRedundantsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.PossessiusRedundantsFilter: a
    possessive that repeats the person of a weak pronoun of the verb is
    removed ("l'" before a vowel); without any pronoun, the dative pronoun
    of the possessive's person is added to the verb instead."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        tokens = match.sentence.get_tokens_without_whitespace()
        pos_possessive = pattern_token_pos
        while pos_possessive < len(tokens) and not tokens[pos_possessive].has_partial_pos_tag('PX'):
            pos_possessive += 1
        possessive_postag = tokens[pos_possessive].reading_with_tag_regex(_PX).pos_tag
        number = possessive_postag[6:7]
        persona = possessive_postag[2:3]
        pos_verb = pattern_token_pos - 1
        while pos_verb > 0 and any(x.chunk_tag == 'GV' for x in tokens[pos_verb].chunk_tags):
            pos_verb -= 1
        pos_verb += 1
        pronoun_found = False
        has_some_pronoun = False

        def is_pronoun(t):
            return t.has_pos_tag_starting_with('PP') or t.has_pos_tag_starting_with('P0')

        def agrees(t):
            pronoun_postag = t.reading_with_tag_regex(_P).pos_tag
            return pronoun_postag[2:3] == persona and (number == 'C' or pronoun_postag[4:5] == number)

        # pronom enrere
        pos_pronoun = pos_verb - 1
        while not pronoun_found and pos_pronoun > 0 and is_pronoun(tokens[pos_pronoun]):
            has_some_pronoun = True
            pronoun_found = agrees(tokens[pos_pronoun])
            pos_pronoun -= 1
        # pronom avant
        pos_pronoun = pattern_token_pos + 1
        while not pronoun_found and pos_pronoun < len(tokens) and is_pronoun(tokens[pos_pronoun]):
            has_some_pronoun = True
            pronoun_found = agrees(tokens[pos_pronoun])
            pos_pronoun += 1
        # Cal apostrofar
        apostrophe_needed = (tokens[pos_possessive - 1].has_any_partial_pos_tag('DA0MS0', 'DA0FS0')
                             and needs_apostrophation_ms(tokens[pos_possessive + 1].token))
        if pronoun_found:
            if apostrophe_needed:
                match.set_offset_position(tokens[pos_possessive - 1].start_pos, tokens[pos_possessive + 1].end_pos)
                match.set_suggested_replacement("l'" + tokens[pos_possessive + 1].token)
            else:
                match.set_offset_position(tokens[pos_possessive].start_pos, tokens[pos_possessive].end_pos)
                match.set_suggested_replacement('')
            return match
        if not has_some_pronoun:
            suggestion = []
            verb_token = tokens[pos_verb].token
            if tokens[pos_verb].has_any_partial_pos_tag('VMN', 'VMG'):
                pronoun_sugg = transform_darrere(get_dative_pronoun(persona + number), verb_token)
                suggestion.append(verb_token)
                suggestion.append(pronoun_sugg)
            else:
                pronoun_sugg = transform_davant(get_dative_pronoun(persona + number), verb_token)
                suggestion.append(preserve_case(pronoun_sugg, verb_token))
                suggestion.append(verb_token.lower())
            for i in range(pos_verb + 1, pos_possessive - 1):
                if tokens[i].whitespace_before:
                    suggestion.append(' ')
                suggestion.append(tokens[i].token.lower())
            if apostrophe_needed:
                suggestion.append(' ')
                suggestion.append("l'" + tokens[pos_possessive + 1].token)
            else:
                for i in range(pos_possessive - 1, pos_possessive + 2):
                    if i == pos_possessive:
                        continue
                    if tokens[i].whitespace_before:
                        suggestion.append(' ')
                    suggestion.append(tokens[i].token)
            match.set_offset_position(tokens[pos_verb].start_pos, tokens[pos_possessive + 1].end_pos)
            match.set_suggested_replacement(''.join(suggestion))
            return match
        return None


FILTERS = (AdjustVerbSuggestionsFilter, AdjustPronounsFilter, ConvertToGenderAndNumberFilter, SynthesizeWithDAFilter,
           SynthesizeWithAnyDeterminerFilter, PossessiusRedundantsFilter)
RULES = {}
