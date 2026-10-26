"""Port of org.languagetool.rules.patterns.RuleSet: fast pre-selection of the
rules that can possibly match a sentence, based on the token/lemma hints of
pattern rules.

The rules can include StaticParts: the rules of a rule file of the static
rule tables (see langtool.patterns.static) with a mask of the active ones;
the C extension selects and matches them on the tables (their rule objects
are only created when they matched)."""

import threading

from .._base import speedups


class StaticPart:
    """the active rules of a StaticRules (mask[i] is 1 for the active rule i;
    None: all)"""

    __slots__ = ('rules', 'mask')

    def __init__(self, rules, mask=None):
        self.rules = rules
        self.mask = bytes(mask) if mask is not None else b'\x01' * len(rules)

    def active_rules(self):
        """the active rule objects (created if needed)"""
        m = self.mask
        return [self.rules.rule(i) for i in range(len(self.rules)) if m[i]]


def _is_direct(rule, method_name, unchecked_name):
    """whether the selector can check the hints of a (Pattern|Disambiguation)PatternRule itself and call the
    method without the check (the methods are not replaced on the instance)"""
    from .rules import PatternRule, DisambiguationPatternRule
    d = getattr(rule, '__dict__', {})
    return (getattr(rule, '_native_hints', None) is not None and type(rule) in (PatternRule, DisambiguationPatternRule)
            and method_name not in d and unchecked_name not in d and 'can_be_ignored_for' not in d and
            'is_interpret_pos_tags_pre_disambiguation' not in d)


class RuleSet:

    def __init__(self, rules, with_lemma_hints=True):
        entries = []
        parts = []
        for r in rules:
            if isinstance(r, StaticPart):
                if speedups is None:
                    entries.extend(r.active_rules())
                    continue
                parts.append((len(entries), r))
                entries.extend([None] * len(r.rules))
            else:
                entries.append(r)
        self._entries = entries
        self._parts = parts
        self.with_lemma_hints = with_lemma_hints
        self.by_token = {}
        self.by_lemma = {}
        self.unclassified = []
        for i, rule in enumerate(entries):
            if rule is None:
                continue
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
        self._all_rules = None if parts else entries
        self._match_selector = None
        self._replace_selector = None
        # the per thread speedups.MatcherTables of the selectors
        self._tables = threading.local()
        self._direct = {}
        self._static_modes = {}

    @property
    def all_rules(self):
        """the rules of the set, in order (the rule objects of the static parts are created)"""
        a = self._all_rules
        if a is None:
            a = []
            parts = dict(self._parts)
            i = 0
            n = len(self._entries)
            while i < n:
                p = parts.get(i)
                if p is not None:
                    a.extend(p.active_rules())
                    i += len(p.rules)
                    continue
                a.append(self._entries[i])
                i += 1
            self._all_rules = a
        return a

    def static_parts(self):
        """the StaticParts of the set"""
        return [p for _, p in self._parts]

    def _static(self, i):
        """(part, local index) of the static rule i of the selector, None for a Python rule"""
        if self._entries[i] is not None:
            return None
        for start, p in self._parts:
            if start <= i < start + len(p.rules):
                return p, i - start
        raise IndexError(i)

    def rules_for_sentence(self, sentence):
        if self._parts:
            # (the static rules are selected by the C extension; this is the reference implementation)
            return RuleSet(self.all_rules, self.with_lemma_hints).rules_for_sentence(sentence)
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
        rules = self._entries
        return [rules[i] for i in sorted(included)]

    def _selector(self, method_name, unchecked_name, skip_text_level_rules):
        """A speedups.RuleSelector whose items are the given methods of the
        rules (None for the skipped rules). For the PatternRules (DisambiguationPatternRules), whose
        match() (replace()) starts with the can_be_ignored_for() check, the
        selector does that check with the native hints and the item is the
        method without the check. The static rules are matched on the tables
        (or, if their objects were created and changed, like Python rules,
        see _static_mode())."""
        items = []
        hints = []
        check_pos = []
        direct = self._direct[method_name] = []  # whether the item is the method without the check
        for rule in self._entries:
            if rule is None:
                items.append(None)
                hints.append(None)
                check_pos.append(False)
                direct.append(False)
                continue
            if skip_text_level_rules and rule.is_text_level_rule():
                items.append(None)
                hints.append(None)
                check_pos.append(False)
                direct.append(False)
                continue
            if _is_direct(rule, method_name, unchecked_name):
                items.append(getattr(rule, unchecked_name))
                hints.append(rule._native_hints)
                check_pos.append(not rule.is_interpret_pos_tags_pre_disambiguation())
                direct.append(True)
            else:
                items.append(getattr(rule, method_name))
                hints.append(None)
                check_pos.append(False)
                direct.append(False)
        segments = []
        for start, p in self._parts:
            modes = bytearray(p.mask)
            for i, o in p.rules.materialized():
                if modes[i] and not self._static_object_ok(o, method_name, unchecked_name):
                    modes[i] = 2
            self._static_modes[(method_name, start)] = bytes(modes)
            segments.append((start, p.rules.blob, p.rules.unit, bytes(modes), self.with_lemma_hints))
        return speedups.RuleSelector(self.by_token, self.by_lemma or None, self.unclassified, tuple(items),
                                     tuple(hints), check_pos, segments)

    @staticmethod
    def _static_object_ok(rule, method_name, unchecked_name):
        """whether a created static rule can still be matched on the tables (its class and its methods were not
        replaced; the changes of its pattern can't be seen)"""
        from .rules import RegexPatternRule
        if type(rule) is RegexPatternRule:
            d = getattr(rule, '__dict__', {})
            return method_name not in d
        return _is_direct(rule, method_name, unchecked_name)

    def _static_rule_mode(self, method_name, i):
        part, local = self._static(i)
        for start, p in self._parts:
            if p is part:
                return part, local, self._static_modes[(method_name, start)][local]
        raise IndexError(i)

    def sentence_match_functions(self, sentence):
        """The functions to call (with the sentence) to get the matches of
        the sentence level rules for the sentence: like [r.match for r in
        rules_for_sentence(sentence) if not r.is_text_level_rule()], but
        (with the speedups) without the rules whose hints show that they
        can't match."""
        if speedups is None:
            return [r.match for r in self.rules_for_sentence(sentence) if not r.is_text_level_rule()]
        return self._get_match_selector().select(sentence, True, self._match_resolve)

    def _match_resolve(self, i):
        part, local, mode = self._static_rule_mode('match', i)
        rule = part.rules.rule(local)
        return rule.match_unchecked if mode == 1 and hasattr(rule, 'match_unchecked') else rule.match

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
            table = self._tables.match = speedups.MatcherTable(len(self._entries))
        return sel.match_sentence(sentence, table, self._match_spec, owner, self._match_callbacks)

    def _match_spec(self, i):
        """the speedups.MatcherTable entry of the rule i (for match_sentence)"""
        rule = self._entries[i]
        if rule is None:
            part, local, mode = self._static_rule_mode('match', i)
            rule = part.rules.rule(local)
            from .rules import RegexPatternRule
            if mode == 1 and type(rule) is not RegexPatternRule:
                return rule.get_matcher().c_spec()  # (a rule with token references)
            return rule.match
        if self._direct['match'][i]:
            return rule.get_matcher().c_spec()
        return None

    def _match_callbacks(self, i):
        """the callbacks of a static rule (for match_sentence, see speedups.MatcherTable)"""
        part, local = self._static(i)
        rule = part.rules.rule(local)
        from .static import register_rule
        register_rule(rule, part.rules.blob, part.rules.first + local)
        return rule.get_matcher().c_callbacks()

    def _replace_spec(self, i):
        """the speedups.MatcherTable entry of the rule i (for disambiguate)"""
        rule = self._entries[i]
        if rule is None:
            part, local, mode = self._static_rule_mode('replace', i)
            rule = part.rules.rule(local)
            if mode == 1:
                return rule.get_replacer().c_spec()  # (a rule with token references)
            return rule.replace
        if self._direct['replace'][i]:
            return rule.get_replacer().c_spec()
        return None

    def _replace_callbacks(self, i):
        part, local = self._static(i)
        return part.rules.rule(local).get_replacer().c_callbacks()

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
            table = self._tables.replace = speedups.MatcherTable(len(self._entries))
        return sel.disambiguate(sentence, None, table, self._replace_spec, self._replace_callbacks)


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
