"""Port of org.languagetool.rules.patterns.RuleSet: fast pre-selection of the
rules that can possibly match a sentence, based on the token/lemma hints of
pattern rules."""

import threading

from .._base import speedups


class RuleSet:

    def __init__(self, rules, with_lemma_hints=True):
        self.all_rules = list(rules)
        self.by_token = {}
        self.by_lemma = {}
        self.unclassified = []
        for i, rule in enumerate(self.all_rules):
            hints = getattr(rule, 'token_hints', None)
            first = None
            if hints:
                if with_lemma_hints:
                    first = hints[0]
                else:
                    for th in hints:
                        if not th.inflected:
                            first = th
                            break
            if first is not None:
                m = self.by_lemma if first.inflected else self.by_token
                for h in first.lower_case_values:
                    m.setdefault(h, []).append(i)
            else:
                self.unclassified.append(i)
        self._match_selector = None
        self._replace_selector = None
        # the per thread speedups.MatcherTables of the selectors
        self._tables = threading.local()
        self._direct = {}

    def rules_for_sentence(self, sentence):
        included = set(self.unclassified)
        if self.by_lemma:
            bl = self.by_lemma
            for lemma in sentence.lemma_offsets:
                s = bl.get(lemma)
                if s is not None:
                    included.update(s)
        bt = self.by_token
        for token in sentence.token_offsets:
            s = bt.get(token)
            if s is not None:
                included.update(s)
        rules = self.all_rules
        return [rules[i] for i in sorted(included)]

    def _selector(self, method_name, unchecked_name, skip_text_level_rules):
        """A speedups.RuleSelector whose items are the given methods of the
        rules (None for the skipped rules). For the PatternRules (DisambiguationPatternRules), whose
        match() (replace()) starts with the can_be_ignored_for() check, the
        selector does that check with the native hints and the item is the
        method without the check."""
        from .rules import PatternRule, DisambiguationPatternRule
        items = []
        hints = []
        check_pos = []
        direct = self._direct[method_name] = []  # whether the item is the method without the check
        for rule in self.all_rules:
            if skip_text_level_rules and rule.is_text_level_rule():
                items.append(None)
                hints.append(None)
                check_pos.append(False)
                direct.append(False)
                continue
            nh = getattr(rule, '_native_hints', None)
            d = getattr(rule, '__dict__', {})
            if (nh is not None and type(rule) in (PatternRule, DisambiguationPatternRule) and
                    method_name not in d and unchecked_name not in d and 'can_be_ignored_for' not in d and
                    'is_interpret_pos_tags_pre_disambiguation' not in d):
                items.append(getattr(rule, unchecked_name))
                hints.append(nh)
                check_pos.append(not rule.is_interpret_pos_tags_pre_disambiguation())
                direct.append(True)
            else:
                items.append(getattr(rule, method_name))
                hints.append(None)
                check_pos.append(False)
                direct.append(False)
        return speedups.RuleSelector(self.by_token, self.by_lemma or None, self.unclassified, tuple(items),
                                     tuple(hints), check_pos)

    def sentence_match_functions(self, sentence):
        """The functions to call (with the sentence) to get the matches of
        the sentence level rules for the sentence: like [r.match for r in
        rules_for_sentence(sentence) if not r.is_text_level_rule()], but
        (with the speedups) without the rules whose hints show that they
        can't match."""
        if speedups is None:
            return [r.match for r in self.rules_for_sentence(sentence) if not r.is_text_level_rule()]
        return self._get_match_selector().select(sentence, True)

    def _get_match_selector(self):
        sel = self._match_selector
        if sel is None:
            sel = self._match_selector = self._selector('match', 'match_unchecked', True)
        return sel

    def match_sentence(self, sentence, owner=None):
        """The matches of the sentence level rules for the sentence, like
        matches = []
        for r in rules_for_sentence(sentence):
            if not r.is_text_level_rule():
                if owner is not None and owner.check_cancelled_callback is set and returns true: break
                matches.extend(r.match(sentence))"""
        if speedups is None:
            matches = []
            for r in self.rules_for_sentence(sentence):
                if r.is_text_level_rule():
                    continue
                cb = owner.check_cancelled_callback if owner is not None else None
                if cb is not None and cb():
                    break
                matches.extend(r.match(sentence))
            return matches
        sel = self._get_match_selector()
        table = getattr(self._tables, 'match', None)
        if table is None:
            table = self._tables.match = speedups.MatcherTable(len(self.all_rules))
        return sel.match_sentence(sentence, table, self._match_spec, owner)

    def _match_spec(self, i):
        """the speedups.MatcherTable entry of the rule i (for match_sentence)"""
        if self._direct['match'][i]:
            return self.all_rules[i].get_matcher().c_spec()
        return None

    def _replace_spec(self, i):
        """the speedups.MatcherTable entry of the rule i (for disambiguate)"""
        if self._direct['replace'][i]:
            return self.all_rules[i].get_replacer().c_spec()
        return None

    def disambiguate(self, sentence):
        """Applies the (disambiguation) rules for the sentence: like
        for r in rules_for_sentence(sentence): sentence = r.replace(sentence)"""
        if speedups is None:
            for rule in self.rules_for_sentence(sentence):
                sentence = rule.replace(sentence)
            return sentence
        sel = self._replace_selector
        if sel is None:
            sel = self._replace_selector = self._selector('replace', 'replace_unchecked', False)
        table = getattr(self._tables, 'replace', None)
        if table is None:
            table = self._tables.replace = speedups.MatcherTable(len(self.all_rules))
        return sel.disambiguate(sentence, None, table, self._replace_spec)


def anti_pattern_selector(anti_patterns):
    """A speedups.RuleSelector for applying the anti-patterns (in
    Rule.get_sentence_with_immunization), or None (pure Python mode or the
    anti-patterns are not all DisambiguationPatternRules)"""
    if speedups is None:
        return None
    from .rules import DisambiguationPatternRule
    items = []
    hints = []
    for ap in anti_patterns:
        d = getattr(ap, '__dict__', {})
        nh = getattr(ap, '_native_hints', None)
        if (type(ap) is not DisambiguationPatternRule or nh is None or 'replace' in d or
                'replace_unchecked' in d or 'can_be_ignored_for' in d):
            return None
        items.append(ap.replace_unchecked)
        hints.append(nh)
    n = len(items)
    return speedups.RuleSelector({}, None, range(n), tuple(items), tuple(hints), [True] * n)


def anti_pattern_spec(anti_patterns):
    """the init function of the speedups.MatcherTable for an
    anti_pattern_selector"""
    return lambda i: anti_patterns[i].get_replacer().c_spec()
