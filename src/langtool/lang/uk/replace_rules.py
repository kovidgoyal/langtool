"""Ports of the replacement rules of org.languagetool.rules.uk:
SimpleReplaceRule (rules/uk/replace.txt), SimpleReplaceSoftRule
(rules/uk/replace_soft.txt) and SimpleReplaceRenamedRule
(rules/uk/replace_renamed.txt)."""

from ... import jregex
from ...analysis import PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME
from ...rules.abstract_rules import AbstractSimpleReplaceRule, java_hash_set_order
from ...rules.base import Rule, RuleMatch
from ...rules.core import Categories
from ...tools import java_trim
from . import helpers
from . import pos_tag_helper as pth

_ADJP_ACTV_BAD = jregex.compile('.*?adjp:actv.*?:bad.*')


class SimpleReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.uk.SimpleReplaceRule: words which should
    not be used (replace.txt), wrong adverbial participles (derivatives of
    the words of replace.txt), active participles and other words tagged as
    :bad (with the suggestions of speller1 of the spelling rule)"""

    def __init__(self, messages, speller_rule, language):
        super().__init__(messages, language)
        self.set_ignore_tagged_words()
        self.morfologik_speller_rule = speller_rule

    def get_wrong_words(self):
        return self.load_from_path('/uk/replace.txt')

    def get_id(self):
        return 'UK_SIMPLE_REPLACE'

    def get_description(self):
        return 'Пошук помилкових слів'

    def get_short(self):
        return 'Помилка?'

    def get_message(self, token_str, replacements):
        return '«' + token_str + '» - помилкове слово, виправлення: ' + ', '.join(replacements) + '.'

    def is_case_sensitive(self):
        return False

    def is_tagged(self, atr):
        for token in atr.readings:
            # optimize
            if token.has_no_tag():
                return False
            if _is_good_pos_tag(token.pos_tag):
                return True
        return False

    def find_matches(self, atr, sentence):
        matches = super().find_matches(atr, sentence)
        if not matches:
            if pth.has_pos_tag(atr, _ADJP_ACTV_BAD):
                msg = 'Активні дієприкметники не властиві українській мові.'
                if atr.readings[0].lemma.endswith('ший'):
                    msg += (' Їх можна замінити на що + дієслово (випавший сніг - сніг, що випав), або на форму з '
                            'суфіксом -л- (промокший - промоклий)')
                    url = 'http://padaread.com/?book=53784&pg=94'
                else:  # -ючий, -ющий тощо
                    msg += (' Їх можна замінити питомими словами в різний спосіб: що + дієслово (роблячий  - що '
                            'робить), дієслівний корінь+ суфікси -льн-, -лив- тощо (збираючий - збиральний, '
                            'обтяжуючий - обтяжливий), заміна іменником (завідуючий - завідувач), заміна '
                            'прикметником із відповідним значенням (діюча модель - робоча модель), зміна конструкції '
                            '(з наступаючим Новим роком - з настанням Нового року) тощо.')
                    url = 'http://nbuv.gov.ua/j-pdf/Nchnpu_8_2013_5_2.pdf'
                rm = RuleMatch(self, sentence, atr.start_pos, atr.start_pos + len(atr.token), msg, self.get_short())
                rm.url = url
                matches.append(rm)
            else:
                derivat_suggestions = self._find_in_deriv(atr.get_clean_token().lower())
                if derivat_suggestions:
                    rm = RuleMatch(self, sentence, atr.start_pos, atr.start_pos + len(atr.token),
                                   'Неправильне слово.', self.get_short())
                    rm.set_suggested_replacements(derivat_suggestions)
                    matches.append(rm)
                    return matches
                if pth.has_pos_tag_part(atr, ':bad') and not pth.has_pos_tag_start(atr, 'number'):
                    rm = RuleMatch(self, sentence, atr.start_pos, atr.start_pos + len(atr.token),
                                   'Неправильно написане слово.', self.get_short())
                    suggestions = self.morfologik_speller_rule.speller1_suggestions_from_default_dicts(atr.token)
                    rm.set_suggested_replacements([s for s in suggestions if ' ' not in s])
                    matches.append(rm)
        return matches

    def _find_in_deriv(self, w):
        derivatives = helpers.derivatives_map()
        derivats = derivatives.get(w)
        if derivats is None:
            return []
        ending = w[-3:]
        wrong_words = self.get_wrong_words()
        suggestions = []
        for d in derivats:
            for t in wrong_words.get(d) or ():
                # filter -ючи vs -вши (findAny of a sequential stream: the
                # first entry in the iteration order of the map)
                found = t
                for key in _derivatives_keys_by_verb().get(t, ()):
                    if key.endswith(ending):
                        found = key
                        break
                suggestions.append(found)
        return suggestions


_derivatives_by_verb = None


def _derivatives_keys_by_verb():
    """verb -> the keys of DERIVATIVES_MAP whose values contain the verb, in
    the iteration order of the Java HashMap"""
    global _derivatives_by_verb
    if _derivatives_by_verb is None:
        derivatives = helpers.derivatives_map()
        m = {}
        for key in _java_hash_map_order(list(derivatives)):
            for verb in derivatives[key]:
                m.setdefault(verb, []).append(key)
        _derivatives_by_verb = m
    return _derivatives_by_verb


def _java_hash_map_order(keys):
    """The iteration order of a java.util.HashMap built by put() in the given
    order (the buckets of the table, the insertion order within a bucket)"""
    return java_hash_set_order(keys)


def _is_good_pos_tag(pos_tag):
    return (pos_tag is not None and pos_tag != PARAGRAPH_END_TAGNAME and pos_tag != SENTENCE_END_TAGNAME
            and 'bad' not in pos_tag and 'subst' not in pos_tag and not pos_tag.startswith('<'))


_CONTEXT_PREFIX = 'ctx:'
_CTX_SPLIT = jregex.compile(', *')


class SimpleReplaceSoftRule(AbstractSimpleReplaceRule):
    """Port of SimpleReplaceSoftRule: words for which better alternatives
    exist (replace_soft.txt), with allowed contexts (спасіння=ctx:
    релігія,поезія|рятування|...)"""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.loc_quality_issue_type = 'Style'

    def get_wrong_words(self):
        return self.load_from_path('/uk/replace_soft.txt')

    def get_id(self):
        return 'UK_SIMPLE_REPLACE_SOFT'

    def get_description(self):
        return 'Пошук нерекомендованих слів'

    def get_short(self):
        return 'Нерекомендоване слово'

    def get_message(self, token_str, replacements):
        contexts, repls = _find_context(replacements)
        replace_text = ', '.join(repls)
        # this is a bit ugly as we're modifying original list
        replacements[:] = [r for r in replacements if r in repls]
        if contexts:
            return ('«' + token_str + '» вживається лише в таких контекстах: ' + ', '.join(contexts) +
                    ', можливо, ви мали на увазі: ' + replace_text + '?')
        return '«' + token_str + '» — нерекомендоване слово, кращий варіант: ' + replace_text + '.'

    def is_token_exception(self, atr):
        # завидна - could be normal adv
        return atr.get_clean_token() == 'завидна' or super().is_token_exception(atr)

    def is_case_sensitive(self):
        return False


def _find_context(replacements):
    contexts = []
    repls = []
    for r in replacements:
        if r.startswith(_CONTEXT_PREFIX):
            parts = _CTX_SPLIT.split(java_trim(r.replace(_CONTEXT_PREFIX, '')))
            while len(parts) > 1 and parts[-1] == '':
                parts.pop()
            contexts.extend(parts)
        else:
            repls.append(r)
    return contexts, repls


_GEO_POSTAG_PATTERN = jregex.compile('noun:inanim.*?:prop.*|adj.*')
_DECOMUNIZATION_URL = (
    'https://uk.wikipedia.org/wiki/%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA_%D1%82%D0%BE%D0%BF%D0%BE%D0%BD%D1%96%D0%BC'
    '%D1%96%D0%B2_%D0%A3%D0%BA%D1%80%D0%B0%D1%97%D0%BD%D0%B8,_%D0%BF%D0%B5%D1%80%D0%B5%D0%B9%D0%BC%D0%B5%D0%BD%D0%BE'
    '%D0%B2%D0%B0%D0%BD%D0%B8%D1%85_%D0%B2%D0%BD%D0%B0%D1%81%D0%BB%D1%96%D0%B4%D0%BE%D0%BA_%D0%B4%D0%B5%D0%BA%D0%BE'
    '%D0%BC%D1%83%D0%BD%D1%96%D0%B7%D0%B0%D1%86%D1%96%D1%97')
_renamed_list = None


def _renamed():
    global _renamed_list
    if _renamed_list is None:
        _renamed_list = helpers.load_lists('/uk/replace_renamed.txt')
    return _renamed_list


class SimpleReplaceRenamedRule(Rule):
    """Port of SimpleReplaceRenamedRule: proper names that have been renamed
    (replace_renamed.txt)"""

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.category = Categories.get('MISC', messages)
        self.loc_quality_issue_type = 'Style'

    def get_id(self):
        return 'UK_SIMPLE_REPLACE_RENAMED'

    def get_description(self):
        return 'Пропозиція поточної назви для перейменованих власних назв'

    def match(self, sentence):
        out = []
        renamed_list = _renamed()
        for atr in sentence.get_tokens_without_whitespace():
            renamed_lemmas = []
            for reading in atr.readings:
                lemma = reading.lemma
                if reading.pos_tag == SENTENCE_END_TAGNAME:
                    continue
                if lemma is not None:
                    if lemma in renamed_list and pth.has_pos_tag(reading, _GEO_POSTAG_PATTERN):
                        if lemma not in renamed_lemmas:
                            renamed_lemmas.append(lemma)
                    else:
                        # overlaps with normal lemma
                        renamed_lemmas = []
                        break
            if renamed_lemmas:
                info = ''
                replacements = []
                for lemma in renamed_lemmas:
                    repl = renamed_list[lemma]
                    replacements.append(repl[0])
                    for i in range(1, len(repl) - 1):
                        replacements.append(repl[i])
                    # kinda cheating - getting first explanation we find
                    # but usually we'll get a noun and adj for the same name so it's ok
                    if not info and len(repl) > 1:
                        info = repl[-1]
                out.append(self._create_rule_match(atr, replacements, renamed_lemmas[0], info, sentence))
        return out

    @staticmethod
    def _get_message(token_str, info):
        msg = '«' + token_str + '» було перейменовано'
        if info:
            msg += ' (' + info + ')'
        return msg

    def _create_rule_match(self, atr, replacements, msg, info, sentence):
        msg = self._get_message(msg, info)
        rm = RuleMatch(self, sentence, atr.start_pos, atr.end_pos, msg, 'Перейменована назва')
        rm.set_suggested_replacements(replacements)
        if 'декомуніз' in info:
            rm.url = _DECOMUNIZATION_URL
        return rm
