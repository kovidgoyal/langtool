"""Ports of filters of org.languagetool.rules.ca that build suggestions for
whole phrases: DonarseliBeFilter, OblidarseSugestionsFilter,
EnNoInfinitiuSuggestionFilter, AnarASuggestionsFilter,
PortarGerundiSuggestionsFilter, PortarTempsSuggestionsFilter and
DonarTempsSuggestionsFilter."""

from ... import jregex
from ...analysis import AnalyzedToken
from ...chunking import ChunkTag
from ...rules.base import RuleMatch
from ...rules.core_filters import adapt_suggestion
from ...rules.filters import RuleFilter
from ...tools import java_equals_ignore_case, preserve_case
from .helpers import (NORMALIZED, P_PRONOM_FEBLE, is_verb_dicendi_before, needs_apostrophation_ms, transform,
                      transform_darrere, transform_davant)
from .synthesis import P_VERB, VerbSynthesizer


def _first_token_index(tokens, match):
    """The index of the first token of the match (not the sentence start)"""
    pos_word = 0
    while pos_word < len(tokens) and (tokens[pos_word].start_pos < match.from_pos
                                      or tokens[pos_word].is_sentence_start):
        pos_word += 1
    return pos_word


def _new_match(match, from_pos, to_pos, message=None):
    rule_match = RuleMatch(match.rule, match.sentence, from_pos, to_pos,
                           match.message if message is None else message, match.short_message)
    rule_match.type = match.type
    return rule_match


def _replace_first(regexp, replacement, s):
    """String.replaceFirst(regexp, replacement)"""
    return jregex.java_replace(jregex.compile(regexp), replacement, s, 1)


class DonarseliBeFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.DonarseliBeFilter: suggestions for
    "donar-se-li bé/malament" (tenir-hi traça, fer-ho bé, sortir-se'n, anar
    bé, sortir/eixir bé)."""

    _DESPRES_DARRER_ADVERBI = jregex.compile('V.N.*|D.*|PD.*')
    _ADVERBI_FINAL = ('bé', 'malament', 'mal', 'millor', 'pitjor', 'fatal')
    _PRONOMS_PERSONALS = ('mi', 'tu', 'ell', 'ella', 'nosaltres', 'vosaltres', 'ells', 'elles')
    _EXCEPTIONS_QUE = ('ja', 'ara', 'per', 'de', 'a', 'en')

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        despres_darrer_adverbi = None
        lang = self.get_language_from_rule_match(match)
        tokens = match.sentence.get_tokens_without_whitespace()
        n = len(tokens)
        pos_word = _first_token_index(tokens, match)
        verb_synth = VerbSynthesizer(tokens, pos_word, lang)
        if verb_synth.is_undefined() or tokens[verb_synth.get_last_verb_index()].end_pos > match.to_pos:
            return None
        pos_donar = verb_synth.get_last_verb_index()
        pos_primer_verb = verb_synth.get_first_verb_index()
        pos_init_underline = pos_primer_verb - verb_synth.get_num_pronouns_before()
        is_pronom_feble_davant = verb_synth.get_num_pronouns_before() > 0
        pos_pronom_feble_relevant = -1
        if verb_synth.get_num_pronouns_after() == 2:
            pos_pronom_feble_relevant = pos_donar + 2
        elif verb_synth.get_num_pronouns_before() >= 2:
            # Si n'hi ha tres, suposem que és un "hi" que ignorem
            pos_pronom_feble_relevant = pos_primer_verb - (verb_synth.get_num_pronouns_before() - 1)
        if pos_pronom_feble_relevant < 1:
            return None
        pronom_feble_relevant = tokens[pos_pronom_feble_relevant].reading_with_tag_regex(P_PRONOM_FEBLE)
        if pronom_feble_relevant is None:
            return None
        # mira darrere: molt bé
        pos_word = verb_synth.get_last_verb_index() + verb_synth.get_num_pronouns_after() + 1
        primer_adverbi = pos_word
        while pos_word < n and tokens[pos_word].token.lower() not in self._ADVERBI_FINAL:
            pos_word += 1
        if pos_word == n or tokens[pos_word].token.lower() not in self._ADVERBI_FINAL:
            return None
        darrer_adverbi = pos_word
        darrer_adverbi_str = tokens[darrer_adverbi].token
        if java_equals_ignore_case(darrer_adverbi_str, 'mal') or java_equals_ignore_case(darrer_adverbi_str, 'fatal'):
            darrer_adverbi_str = 'malament'
        if primer_adverbi == -1 or darrer_adverbi == -1:
            return None
        if darrer_adverbi + 1 < n:
            despres_darrer_adverbi = tokens[darrer_adverbi + 1].reading_with_tag_regex(self._DESPRES_DARRER_ADVERBI)
        add_tokens_to_right = 0
        add_string_to_right = ''
        add_tokens_to_left = 0
        add_string_to_left = ''

        def tok(i):
            return tokens[i].token

        # analitza paraules prèvies: que a mi mai no se'm dona malament
        is_no = pos_init_underline - 1 > 0 and (java_equals_ignore_case(tok(pos_init_underline - 1), 'no')
                                                or java_equals_ignore_case(tok(pos_init_underline - 1), 'mai'))
        is_mai_no = is_no and pos_init_underline - 2 > 0 and java_equals_ignore_case(tok(pos_init_underline - 2),
                                                                                     'mai')
        is_malament = (java_equals_ignore_case(darrer_adverbi_str, 'malament')
                       or java_equals_ignore_case(darrer_adverbi_str, 'pitjor'))
        # No ... malament
        is_no_malament = is_no and is_malament
        # ... malement
        is_malament = is_malament and not is_no_malament
        if is_mai_no:
            add_tokens_to_left += 1
        if is_no:
            add_tokens_to_left += 1
        a_mi_string = ''
        if (pos_init_underline - add_tokens_to_left - 2 > 0
                and java_equals_ignore_case(tok(pos_init_underline - add_tokens_to_left - 2), 'a')
                and tok(pos_init_underline - add_tokens_to_left - 1).lower() in self._PRONOMS_PERSONALS):
            a_mi_string = (tok(pos_init_underline - add_tokens_to_left - 2) + ' '
                           + tok(pos_init_underline - add_tokens_to_left - 1) + ' ')
            add_tokens_to_left += 2
        i_prev = pos_init_underline - add_tokens_to_left - 1
        is_que = (i_prev > 0 and java_equals_ignore_case(tok(i_prev), 'que')
                  and not is_verb_dicendi_before(tokens, pos_init_underline - add_tokens_to_left - 2))
        is_que_accent = i_prev > 0 and java_equals_ignore_case(tok(i_prev), 'què')
        if (pos_init_underline - add_tokens_to_left - 2 > 0
                and tok(pos_init_underline - add_tokens_to_left - 2).lower() in self._EXCEPTIONS_QUE):
            is_que_accent = False
            is_que = False
        is_el_que = False
        is_a_qui = False
        if i_prev > 0 and java_equals_ignore_case(tok(i_prev), 'qui'):
            is_el_que = True
            if (pos_init_underline - add_tokens_to_left - 2 > 0
                    and java_equals_ignore_case(tok(pos_init_underline - add_tokens_to_left - 2), 'a')):
                is_a_qui = True
        if is_que and pos_init_underline - add_tokens_to_left - 2 > 0:
            t2 = tokens[pos_init_underline - add_tokens_to_left - 2]
            if t2.has_pos_tag_starting_with('DA') or t2.has_any_lemma('alumne', 'persona', 'estudiant', 'professor'):
                is_el_que = True
                is_que = False  # no subratllem "que"
        if is_que:
            add_tokens_to_left += 1
        if is_que_accent:
            add_tokens_to_left += 1
        for j in range(pos_init_underline - add_tokens_to_left, pos_init_underline):
            add_string_to_left = add_string_to_left + tok(j) + ' '

        # TODO: quines coses se li donen bé; les que no se't donen tan bé;
        # al teu fill no se li dona gaire bé dibuixar; La geografia se't donava prou bé
        # Altres suggeriments: tenir-hi la mà trencada, ser el meu fort

        # Crea suggeriments
        replacements = []
        casing_model = tok(pos_init_underline - add_tokens_to_left)
        persona = pronom_feble_relevant.pos_tag[2:3]
        nombre = pronom_feble_relevant.pos_tag[4:5]
        primer_verb = tokens[pos_primer_verb].reading_with_tag_regex(P_VERB)
        verb_postag = primer_verb.pos_tag
        new_verb_postag = verb_postag[0:4] + persona + nombre + verb_postag[6:8]

        # tinc traça (per a)
        add_string_to_left_tinc_traca = _replace_first('(?i)què ', 'en què ', add_string_to_left)
        add_string_to_left_tinc_traca = _replace_first('(?i)que ', 'en què ', add_string_to_left_tinc_traca)
        add_string_to_left_tinc_traca = _replace_first(a_mi_string, '', add_string_to_left_tinc_traca)
        if is_no_malament:
            add_string_to_left_tinc_traca = _replace_first('(?i)no ', '', add_string_to_left_tinc_traca)
            add_string_to_left_tinc_traca = _replace_first('(?i)mai ', '', add_string_to_left_tinc_traca)
        suggestion = [add_string_to_left_tinc_traca]
        if is_malament:
            suggestion.append('no ')
        if not add_string_to_left.lower().startswith('qu') and despres_darrer_adverbi is None:
            suggestion.append('hi ')
        verb_synth.set_lemma_and_postag('tenir', new_verb_postag)
        suggestion.append(verb_synth.synthesize())
        if not is_no_malament and not is_malament:
            suggestion.append(self._get_adverbs_for(tokens, primer_adverbi, darrer_adverbi, 'traça'))
        suggestion.append(' traça')
        if despres_darrer_adverbi is not None:
            if despres_darrer_adverbi.token.lower() == 'el':
                suggestion.append(' per al')
                add_tokens_to_right = 1
                add_string_to_right = ' el'
            elif despres_darrer_adverbi.token.lower() == 'els':
                suggestion.append(' per als')
                add_tokens_to_right = 1
                add_string_to_right = ' els'
            else:
                suggestion.append(' per a')
        if not is_el_que:
            replacements.append(preserve_case(''.join(suggestion), casing_model))

        # faig bé
        suggestion = [_replace_first(a_mi_string, '', add_string_to_left)]
        if not add_string_to_left.lower().startswith('qu') and despres_darrer_adverbi is None and not is_el_que:
            suggestion.append('ho ')
        verb_synth.set_lemma_and_postag('fer', new_verb_postag)
        suggestion.append(verb_synth.synthesize())
        suggestion.append(self._get_adverbs_for(tokens, primer_adverbi, darrer_adverbi, 'bé'))
        suggestion.append(' ' + darrer_adverbi_str)
        suggestion.append(add_string_to_right)
        if not is_a_qui:
            replacements.append(preserve_case(''.join(suggestion), casing_model))

        # me'n surto (en)
        suggestion = [add_string_to_left_tinc_traca]
        if is_malament:
            suggestion.append('no ')
        if is_pronom_feble_davant:
            pronom = pronom_feble_relevant.token
            if java_equals_ignore_case(pronom, "'ls") or java_equals_ignore_case(pronom, 'li'):
                pronom = 'es'
            pronoms_normalitzats = transform(pronom, NORMALIZED) + ' en'
            suggestion.append(transform_davant(pronoms_normalitzats, primer_verb.token))
        verb_synth.set_lemma_and_postag('sortir', new_verb_postag)
        suggestion.append(verb_synth.synthesize())
        if not is_pronom_feble_davant:
            pronom = pronom_feble_relevant.token
            if java_equals_ignore_case(pronom, "'ls") or java_equals_ignore_case(pronom, '-li'):
                pronom = 'es'
            pronoms_normalitzats = transform(pronom, NORMALIZED) + ' en'
            suggestion.append(transform_darrere(pronoms_normalitzats, primer_verb.token))
        if despres_darrer_adverbi is not None:
            if despres_darrer_adverbi.pos_tag.startswith('V'):
                suggestion.append(' a')
            else:
                suggestion.append(' en')
        suggestion.append(add_string_to_right)
        if not is_el_que:
            replacements.append(preserve_case(''.join(suggestion), casing_model))

        # em van bé
        suggestion = [add_string_to_left]
        verb_synth.set_lemma_and_postag('anar', verb_postag)
        verb = verb_synth.synthesize()
        if is_pronom_feble_davant:
            suggestion.append(transform_davant(pronom_feble_relevant.token, verb))
        suggestion.append(verb)
        if not is_pronom_feble_davant:
            suggestion.append(transform_darrere(pronom_feble_relevant.token, verb))
        suggestion.append(self._get_adverbs_for(tokens, primer_adverbi, darrer_adverbi, 'bé'))
        suggestion.append(' ' + darrer_adverbi_str)
        suggestion.append(add_string_to_right)
        replacements.append(preserve_case(''.join(suggestion), casing_model))

        # m'ixen bé, em surten bé
        suggestion = [add_string_to_left]
        new_lemma_sortir = 'eixir' if lang.code == 'ca-ES-valencia' else 'sortir'
        verb_synth.set_lemma_and_postag(new_lemma_sortir, verb_postag)
        verb = verb_synth.synthesize()
        if is_pronom_feble_davant:
            suggestion.append(transform_davant(pronom_feble_relevant.token, verb))
        suggestion.append(verb)
        if not is_pronom_feble_davant:
            suggestion.append(transform_darrere(pronom_feble_relevant.token, verb))
        suggestion.append(self._get_adverbs_for(tokens, primer_adverbi, darrer_adverbi, 'bé'))
        suggestion.append(' ' + darrer_adverbi_str)
        suggestion.append(add_string_to_right)
        replacements.append(preserve_case(''.join(suggestion), casing_model))

        if not replacements:
            return None
        rule_match = _new_match(match, tokens[pos_init_underline - add_tokens_to_left].start_pos,
                                tokens[darrer_adverbi + add_tokens_to_right].end_pos)
        rule_match.set_suggested_replacements(replacements)
        return rule_match

    @staticmethod
    def _get_adverbs_for(tokens, primer_adverbi, darrer_adverbi, target):
        result = []
        for i in range(primer_adverbi, darrer_adverbi):
            if tokens[i].whitespace_before:
                result.append(' ')
            result.append(tokens[i].token)
        result_str = ''.join(result)
        if target == 'traça':
            if java_equals_ignore_case(result_str, ' molt'):
                result_str = ' molta'
            elif java_equals_ignore_case(result_str, ' gens'):
                result_str = ' gens de'
            elif java_equals_ignore_case(result_str, ' tan'):
                result_str = ' tanta'
        return result_str


class OblidarseSugestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.OblidarseSugestionsFilter:
    "se m'ha oblidat (de)" -> "m'he oblidat (de)", "me n'he oblidat"
    (passar -> descuidar)."""

    _ADD_REFLEXIVE_VOWEL = {'1S': "m'", '2S': "t'", '3S': "s'", '1P': 'ens ', '2P': 'us ', '3P': "s'"}
    _ADD_REFLEXIVE_CONSONANT = {'1S': 'em ', '2S': 'et ', '3S': 'es ', '1P': 'ens ', '2P': 'us ', '3P': 'es '}
    _ADD_REFLEXIVE_EN_VOWEL = {'1S': "me n'", '2S': "te n'", '3S': "se n'", '1P': "ens n'", '2P': "us n'",
                               '3P': "se n'"}
    _ADD_REFLEXIVE_EN_CONSONANT = {'1S': "me'n ", '2S': "te'n ", '3S': "se'n ", '1P': 'ens en ', '2P': 'us en ',
                                   '3P': "se'n "}
    _WORD_AFTER = jregex.compile('D.*|V.N.*|P[DI].*|NC.*')
    _EXCEPTIONS = ('com', 'de', "d'", 'que')

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        from ...api import get_language
        lang = get_language('ca')
        synth = self.get_language_from_rule_match(match).synthesizer
        tokens = match.sentence.get_tokens_without_whitespace()
        pos_word = _first_token_index(tokens, match)
        pronom_postag = tokens[pos_word + 1].reading_with_tag_regex('P.*').pos_tag
        pronom_gender_number = pronom_postag[2:3] + pronom_postag[4]
        index_main_verb = pos_word + 2
        while not tokens[index_main_verb].has_any_lemma('oblidar', 'descuidar', 'passar'):
            index_main_verb += 1
        verb_reading = tokens[pos_word + 2].reading_with_tag_regex('V.*')
        verb_postag = verb_reading.pos_tag
        lemma = verb_reading.lemma
        if lemma == 'passar':
            lemma = 'descuidar'
        at = AnalyzedToken('', '', lemma)
        synth_forms = synth.synthesize(at, verb_postag[0:4] + pronom_gender_number + verb_postag[6:8])
        if not synth_forms:
            return None
        new_verb = synth_forms[0]
        for i in range(pos_word + 3, index_main_verb + 1):
            new_verb = (new_verb + tokens[i].whitespace_before_char
                        + tokens[i].token.replace('passar', 'descuidar').replace('passat', 'descuidat')
                        .replace('passant', 'descuidant'))
        verb_vowel = needs_apostrophation_ms(new_verb)
        word_after = ''
        if index_main_verb + 1 < len(tokens):
            word_after_reading = tokens[index_main_verb + 1].reading_with_tag_regex(self._WORD_AFTER)
            if word_after_reading is not None:
                word_after = word_after_reading.token
            if tokens[index_main_verb + 1].token.lower() in self._EXCEPTIONS:
                word_after = tokens[index_main_verb + 1].token
        if (not word_after and not java_equals_ignore_case(word_after, 'de')
                and not java_equals_ignore_case(word_after, "d'") and not java_equals_ignore_case(word_after, 'que')):
            transform_map = self._ADD_REFLEXIVE_EN_VOWEL if verb_vowel else self._ADD_REFLEXIVE_EN_CONSONANT
        else:
            transform_map = self._ADD_REFLEXIVE_VOWEL if verb_vowel else self._ADD_REFLEXIVE_CONSONANT
        # (StringBuilder.append(null) appends "null")
        sugg = [transform_map.get(pronom_gender_number, 'null'), new_verb]
        characters_after_correction = 0
        # contracció de + el -> del
        if java_equals_ignore_case(word_after, 'el') or java_equals_ignore_case(word_after, 'els'):
            sugg.append(' d')
            sugg.append(word_after.lower())
            characters_after_correction = len(word_after) + 1
        # apostrofació: de | d'
        elif (word_after and not java_equals_ignore_case(word_after, 'de')
              and not java_equals_ignore_case(word_after, "d'") and not java_equals_ignore_case(word_after, 'que')):
            word_after_apostrophe = needs_apostrophation_ms(word_after)
            sugg.append(" d'" if word_after_apostrophe else ' de')
            characters_after_correction = 1 if word_after_apostrophe else 0
        replacement = preserve_case(''.join(sugg), tokens[pos_word].token)
        replacements = [replacement]
        for s in match.suggested_replacements:
            if characters_after_correction == 1:
                s = s + ' '
            replacements.append(adapt_suggestion(lang, s, tokens[pos_word].token))
        rule_match = _new_match(match, tokens[pos_word].start_pos,
                                tokens[index_main_verb].end_pos + characters_after_correction,
                                match.message.replace('passar', 'descuidar'))
        rule_match.set_suggested_replacements(replacements)
        return rule_match


class EnNoInfinitiuSuggestionFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.EnNoInfinitiuSuggestionFilter: "en no
    + infinitiu" (causal) -> "com que no ..."/"perquè no ..." with the verb
    in the tense of the main verb."""

    _TEMPS_VERBALS_PRESENT = ('IP', 'IF')

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = self.get_language_from_rule_match(match)
        tokens = match.sentence.get_tokens_without_whitespace()
        pos_word = _first_token_index(tokens, match)
        verb_synth_infinitiu = VerbSynthesizer(tokens, pos_word, lang)
        pos_word = verb_synth_infinitiu.get_last_index() + 1
        verb_after = VerbSynthesizer(tokens, pos_word, lang)
        verb_before = VerbSynthesizer(tokens, verb_synth_infinitiu.get_first_verb_index() - 1, lang, True)
        # verb found out of bounds
        if (verb_synth_infinitiu.is_undefined()
                or tokens[verb_synth_infinitiu.get_last_verb_index()].end_pos > match.to_pos):
            return None
        verb_after_postag = verb_after.get_first_verb_is_postag()
        verb_before_postag = verb_before.get_first_verb_is_postag()
        if not verb_after.is_undefined() and verb_after_postag is not None:
            postag_temps_verbal = verb_after_postag
            is_passat_perifrastic = verb_after.is_passat_perifrastic()
        elif not verb_before.is_undefined() and verb_before_postag is not None:
            postag_temps_verbal = verb_before_postag
            is_passat_perifrastic = verb_before.is_passat_perifrastic()
        else:
            return None
        if postag_temps_verbal is None:
            return None
        # caldria incloure sempre l'oció 3S si no hi és.
        if postag_temps_verbal[2:4] in self._TEMPS_VERBALS_PRESENT and not is_passat_perifrastic:
            postag_prefix = 'VMIP'
        else:
            postag_prefix = 'VMII'
        synth_verbs = []
        if postag_temps_verbal[4:6] != '3S':
            verb_synth_infinitiu.set_postag(postag_prefix + '3S' + postag_temps_verbal[6:])
            synth_verbs.append(verb_synth_infinitiu.synthesize())
        verb_synth_infinitiu.set_postag(postag_prefix + postag_temps_verbal[4:])
        synth_verbs.append(verb_synth_infinitiu.synthesize())
        start_pos = verb_synth_infinitiu.get_first_verb_index() - 2
        if start_pos < 0:
            start_pos = 0
        elif java_equals_ignore_case(tokens[start_pos].token, 'l'):
            start_pos -= 1
        end_pos = verb_synth_infinitiu.get_last_index()
        original_str = match.sentence.text[tokens[start_pos].start_pos:tokens[end_pos].end_pos]
        suggestions = []
        for synth_verb in synth_verbs:
            if not verb_before.is_undefined() and verb_before_postag is not None:
                suggestion = 'perquè no '
            else:
                suggestion = 'com que no '
            pronouns_after = verb_synth_infinitiu.get_pronouns_str_after()
            if pronouns_after:
                suggestion += transform_davant(pronouns_after, synth_verb)
            suggestion += synth_verb
            suggestion_str = preserve_case(suggestion, original_str)
            if suggestion_str not in suggestions:
                suggestions.append(suggestion_str)
        if not suggestions:
            return None
        rule_match = _new_match(match, tokens[start_pos].start_pos, tokens[end_pos].end_pos)
        rule_match.set_suggested_replacements(suggestions)
        return rule_match


class AnarASuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.AnarASuggestionsFilter: "vaig a +
    infinitiu" -> future and present of the verb."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = self.get_language_from_rule_match(match)
        tokens = match.sentence.get_tokens_without_whitespace()
        init_pos = _first_token_index(tokens, match)
        verb_synthesizer = VerbSynthesizer(tokens, init_pos, lang)
        if verb_synthesizer.is_undefined() or tokens[verb_synthesizer.get_last_verb_index()].end_pos > match.to_pos:
            return None
        init_pos = verb_synthesizer.get_first_verb_index()
        verb_postag = tokens[init_pos].reading_with_tag_regex('V.IP.*').pos_tag
        lemma = tokens[init_pos + 2].reading_with_tag_regex('V.N.*').lemma
        at = AnalyzedToken('', '', lemma)
        synth = lang.synthesizer
        synth_forms_list = []
        # synthesize future
        synth_forms_list.extend(synth.synthesize(at, 'V[MS]IF' + verb_postag[4:8], True))
        # synthesize present
        synth_forms_list.extend(synth.synthesize(at, 'V[MS]IP' + verb_postag[4:8], True))
        if not synth_forms_list:
            return None
        pronoms_darrere = verb_synthesizer.get_pronouns_str_after()
        adjust_end_pos = verb_synthesizer.get_num_pronouns_after()
        pronoms_davant = verb_synthesizer.get_pronouns_str_before()
        adjust_start_pos = verb_synthesizer.get_num_pronouns_before()
        replacements = list(match.suggested_replacements)
        for verb in synth_forms_list:
            suggestion = ''
            if pronoms_darrere:
                suggestion = transform_davant(pronoms_darrere, verb)
            elif pronoms_davant:
                suggestion = transform_davant(pronoms_davant, verb)
            suggestion += verb
            suggestion = preserve_case(suggestion, tokens[init_pos - adjust_start_pos].token)
            replacements.append(suggestion)
        if not replacements:
            return None
        rule_match = _new_match(match, tokens[init_pos - adjust_start_pos].start_pos,
                                tokens[init_pos + 2 + adjust_end_pos].end_pos)
        # (Language.adaptSuggestionsList)
        rule_match.set_suggested_replacements([adapt_suggestion(lang, s, '') for s in replacements])
        return rule_match


class PortarGerundiSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.PortarGerundiSuggestionsFilter:
    "porto fent" -> "he fet", "faig" (optional argument newLemma)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = self.get_language_from_rule_match(match)
        synth = lang.synthesizer
        tokens = match.sentence.get_tokens_without_whitespace()
        new_lemma = self.get_optional('newLemma', arguments, '')
        pos_word = _first_token_index(tokens, match)
        atr1 = tokens[pos_word].reading_with_tag_regex('V.[IS].*')
        atr2 = tokens[pos_word + 1].reading_with_tag_regex('V.G.*')
        replacements = []
        # he fet
        lemma = atr2.lemma if not new_lemma else new_lemma
        synth_forms1 = synth.synthesize(AnalyzedToken('', '', 'haver'), 'VA' + atr1.pos_tag[2:], True)
        synth_forms2 = synth.synthesize(AnalyzedToken('', '', lemma), 'V.P..SM.', True)
        if synth_forms1 is not None and synth_forms2 is not None:
            for synth_form1 in synth_forms1:
                for synth_form2 in synth_forms2:
                    replacements.append(synth_form1 + ' ' + synth_form2)
        # faig
        synth_forms3 = synth.synthesize(AnalyzedToken('', '', lemma), 'V.' + atr1.pos_tag[2:], True)
        if synth_forms3:
            replacements.append(synth_forms3[0])
        if not replacements:
            return None
        verb_synthesizer = VerbSynthesizer(tokens, pos_word, lang)
        correct_start_index = 0
        correct_end_index = 0
        for i in range(len(replacements)):
            pronouns_suggestion = ''
            if verb_synthesizer.get_num_pronouns_after() > 0:
                pronouns_suggestion = transform_davant(verb_synthesizer.get_pronouns_str_after(), replacements[i])
                correct_end_index = verb_synthesizer.get_num_pronouns_after()
            elif verb_synthesizer.get_num_pronouns_before() > 0:
                pronouns_suggestion = transform_davant(verb_synthesizer.get_pronouns_str_before(), replacements[i])
                correct_start_index = -verb_synthesizer.get_num_pronouns_before()
            replacements[i] = preserve_case(pronouns_suggestion + replacements[i],
                                            tokens[pos_word + correct_start_index].token)
        rule_match = _new_match(match, tokens[pos_word + correct_start_index].start_pos,
                                tokens[pos_word + 1 + correct_end_index].end_pos)
        rule_match.set_suggested_replacements(replacements)
        return rule_match


_PTIME = ChunkTag('PTime')


class PortarTempsSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.PortarTempsSuggestionsFilter: "porto
    dos anys treballant" -> "fa dos anys que treballo"."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = self.get_language_from_rule_match(match)
        synth = lang.synthesizer
        tokens = match.sentence.get_tokens_without_whitespace()
        n = len(tokens)
        pos_word = _first_token_index(tokens, match)
        verb_postag = tokens[pos_word].reading_with_tag_regex('V.*').pos_tag
        at = AnalyzedToken('', '', 'fer')
        new_postag = verb_postag[0:4] + '[30][S0].' + verb_postag[7:8]
        synth_forms = synth.synthesize(at, new_postag, True)
        if not synth_forms:
            return None
        suggestion = [synth_forms[0]]
        i = pos_word + 1
        while i < n and _PTIME in tokens[i].chunk_tags:
            if tokens[i].whitespace_before:
                suggestion.append(' ')
            suggestion.append(tokens[i].token)
            i += 1
        last_token_pos = i
        if last_token_pos + 1 >= n:
            return None
        adjust_end_pos = 0
        last_token = tokens[last_token_pos]
        lt = last_token.token
        if lt == 'que':
            suggestion.append(' que')
        elif last_token.has_pos_tag_starting_with('VMG') or last_token.has_pos_tag_starting_with('VSG'):
            suggestion.append(' que ')
            verb_synth = VerbSynthesizer(tokens, last_token_pos, lang)
            pronoms = verb_synth.get_pronouns_str_after()
            adjust_end_pos += verb_synth.get_num_pronouns_after()
            at2 = AnalyzedToken('', '', last_token.reading_with_tag_regex('V.G.*').lemma)
            synth_forms2 = synth.synthesize(at2, 'V.I' + verb_postag[3:8], True)
            if not synth_forms2:
                return None
            if pronoms:
                suggestion.append(transform_davant(pronoms, synth_forms2[0]))
            suggestion.append(synth_forms2[0])
        elif lt == 'sense' and (tokens[last_token_pos + 1].has_pos_tag_starting_with('VSN')
                                or tokens[last_token_pos + 1].has_pos_tag_starting_with('VMN')):
            suggestion.append(' que no ')
            adjust_end_pos += 1
            verb_synth = VerbSynthesizer(tokens, last_token_pos + 1, lang)
            pronoms = verb_synth.get_pronouns_str_after()
            adjust_end_pos += verb_synth.get_num_pronouns_after()
            at2 = AnalyzedToken('', '', tokens[last_token_pos + 1].reading_with_tag_regex('V.N.*').lemma)
            synth_forms2 = synth.synthesize(at2, 'V.I' + verb_postag[3:8])
            if not synth_forms2:
                return None
            if pronoms:
                suggestion.append(transform_davant(pronoms, synth_forms2[0]))
            suggestion.append(synth_forms2[0])
        elif (lt in ('així', 'a', 'en', 'ací', 'aquí', 'ahí', 'allí', 'allà', 'de')
              or last_token.has_pos_tag_starting_with('AQ') or last_token.has_pos_tag_starting_with('VMP')):
            at2 = AnalyzedToken('', '', 'estar')
            synth_forms2 = synth.synthesize(at2, 'V.I' + verb_postag[3:8])
            if not synth_forms2:
                return None
            suggestion.append(' que ' + synth_forms2[0])
            adjust_end_pos -= 1
        else:
            return None
        replacement = preserve_case(''.join(suggestion), tokens[pos_word].token)
        if not replacement:
            return None
        rule_match = _new_match(match, tokens[pos_word].start_pos, tokens[last_token_pos + adjust_end_pos].end_pos)
        rule_match.set_suggested_replacement(replacement)
        return rule_match


class DonarTempsSuggestionsFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.DonarTempsSuggestionsFilter: "no em
    dona temps" -> "no hi ha temps", "no tinc temps"."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        tokens = match.sentence.get_tokens_without_whitespace()
        synth = self.get_language_from_rule_match(match).synthesizer
        pos_word = _first_token_index(tokens, match)
        pronom_postag = tokens[pos_word].reading_with_tag_regex('P.*').pos_tag
        pronom_gender_number = pronom_postag[2:3] + pronom_postag[4:5]
        index_first_verb = pos_word + 1
        index_main_verb = index_first_verb
        while not tokens[index_main_verb].has_any_lemma('donar'):
            index_main_verb += 1
        verb_postag = tokens[index_main_verb].reading_with_tag_regex('V.*').pos_tag

        # haver-hi temps
        at = AnalyzedToken('', '', 'haver')
        synth_forms = synth.synthesize(at, 'VA' + verb_postag[2:8])
        suggestion1 = ''
        if synth_forms:
            index = index_first_verb
            suggestion1 = 'hi'
            while index < index_main_verb:
                if tokens[index].whitespace_before or len(suggestion1) == 2:
                    suggestion1 += ' '
                suggestion1 += tokens[index].token
                index += 1
            suggestion1 += ' ' + synth_forms[0] + ' temps'
        replacements = []
        sugg1 = suggestion1.replace('de haver', "d'haver")
        sugg1 = preserve_case(sugg1, tokens[pos_word].token)
        if sugg1:
            replacements.append(sugg1)

        # tenir temps
        suggestion2 = ''
        index = index_first_verb
        if index == index_main_verb:
            synth_forms2 = synth.synthesize(AnalyzedToken('', '', 'tenir'),
                                            verb_postag[0:4] + pronom_gender_number + verb_postag[6:8])
            if synth_forms2:
                suggestion2 += synth_forms2[0] + ' temps'
        else:
            at2 = tokens[index_first_verb].readings[0]
            synth_forms2 = synth.synthesize(at2, at2.pos_tag[0:4] + pronom_gender_number + at2.pos_tag[6:8])
            if synth_forms2:
                suggestion2 += synth_forms2[0]
                index += 1
                while index < index_main_verb:
                    if tokens[index].whitespace_before:
                        suggestion2 += ' '
                    suggestion2 += tokens[index].token
                    index += 1
                synth_forms3 = synth.synthesize(AnalyzedToken('', '', 'tenir'),
                                                tokens[index_main_verb].readings[0].pos_tag)
                if synth_forms3:
                    suggestion2 += ' ' + synth_forms3[0] + ' temps'
                else:
                    suggestion2 = ''
        sugg2 = preserve_case(suggestion2, tokens[pos_word].token)
        if sugg2:
            replacements.append(sugg2)
        if not replacements:
            return None
        rule_match = _new_match(match, tokens[pos_word].start_pos, tokens[index_main_verb + 1].end_pos)
        rule_match.set_suggested_replacements(replacements)
        return rule_match


FILTERS = (DonarseliBeFilter, OblidarseSugestionsFilter, EnNoInfinitiuSuggestionFilter, AnarASuggestionsFilter,
           PortarGerundiSuggestionsFilter, PortarTempsSuggestionsFilter, DonarTempsSuggestionsFilter)
# rule factories of this module: Java class name -> factory(messages, language, user_config, **kwargs)
RULES = {}
