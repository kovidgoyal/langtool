"""Port of RepeatedPatternRuleTransformer and
ConsistencyPatternRuleTransformer: pattern rules that need to see the whole
text are wrapped in text level rules."""

from .base import TextLevelRule, same_rule_group_filter

DEFAULT_MAX_DISTANCE_TOKENS = 60


def _sentence_matches(self, sentence):
    """the matches of the rules for the sentence: like
    for rule in self.rules: sm.extend(rule.match(sentence))
    (with the fast rule selection and matching of a RuleSet)"""
    rs = self._rule_set
    if rs is None:
        from ..patterns.ruleset import RuleSet
        rs = self._rule_set = RuleSet(self.rules)
    return rs.match_sentence(sentence)


class RepeatedPatternRule(TextLevelRule):

    def __init__(self, rules, language):
        super().__init__()
        self.rules = list(rules)
        self.language = language
        self.premium = any(r.premium for r in self.rules)
        self._rule_set = None

    _sentence_matches = _sentence_matches

    def get_id(self):
        return self.rules[0].get_id()

    def get_description(self):
        return self.rules[0].get_description()

    def match(self, sentences, annotated_text=None):
        matches = []
        offset_chars = offset_tokens = prev_from_token = prev_matches = 0
        distances = []
        for s in sentences:
            sm = same_rule_group_filter(self._sentence_matches(s))
            nbt = s.non_blank_tokens
            slen = len(nbt)
            for m in sm:
                from_token = 0
                while from_token < slen and nbt[from_token].start_pos < m.from_pos:
                    from_token += 1
                from_token += offset_tokens
                m.set_offset_position(m.from_pos + offset_chars, m.to_pos + offset_chars)
                max_distance = m.rule.distance_tokens
                if max_distance < 1:
                    max_distance = DEFAULT_MAX_DISTANCE_TOKENS * m.rule.min_prev_matches
                distances.append(from_token - prev_from_token)
                mpm = m.rule.min_prev_matches
                if prev_matches >= mpm and self._is_distance_valid(distances, max_distance, mpm):
                    matches.append(m)
                prev_from_token = from_token
                prev_matches += 1
            offset_chars += len(s.text)
            offset_tokens += slen - 1
        return matches

    @staticmethod
    def _is_distance_valid(distances, max_distance, min_prev):
        i = 0
        size = len(distances)
        d = 0
        while i < min_prev and i < size:
            d += distances[size - 1 - i]
            i += 1
        return d < max_distance


def _main_rule_id(rid):
    parts = rid.split('_')
    return parts[0] + '_' + parts[1]


def _feature(rid):
    return rid.split('_')[2]


class ConsistencyPatternRule(TextLevelRule):

    def __init__(self, rules, language):
        super().__init__()
        self.rules = list(rules)
        self.language = language
        self.premium = any(r.premium for r in self.rules)
        self._rule_set = None

    _sentence_matches = _sentence_matches

    def get_id(self):
        return _main_rule_id(self.rules[0].get_id())

    def get_description(self):
        return self.rules[0].get_description()

    def match(self, sentences, annotated_text=None):
        counts = {}
        offset = 0
        matches = []
        for s in sentences:
            sm = same_rule_group_filter(self._sentence_matches(s))
            for rm in sm:
                rm.set_sentence_position(rm.from_pos, rm.to_pos)
                rm.set_offset_position(rm.from_pos + offset, rm.to_pos + offset)
                matches.append(rm)
            offset += len(s.text)
        for rm in matches:
            f = _feature(rm.rule.get_id())
            counts[f] = counts.get(f, 0) + 1
        if len(counts) < 2:
            return []
        mx = max(counts.values())
        with_max = [k for k, v in counts.items() if v == mx]
        keep = [k for k, v in counts.items() if v != mx]
        suggest = list(with_max)
        if len(with_max) > 1:
            keep.extend(with_max)
        return [self.language.adjust_match(rm, suggest) for rm in matches if _feature(rm.rule.get_id()) in keep]


def transform_pattern_rules(rules, language):
    """Returns the list of rules with the repeated/consistency rules wrapped."""
    remaining = []
    groups = {}
    for r in rules:
        if r.min_prev_matches > 0:
            groups.setdefault(r.get_id(), []).append(r)
        else:
            remaining.append(r)
    transformed = [RepeatedPatternRule(g, language) for g in groups.values()]
    rules = remaining
    remaining = []
    groups = {}
    prefix = language.get_consistency_rule_prefix()
    for r in rules:
        if r.get_id().startswith(prefix):
            groups.setdefault(_main_rule_id(r.get_id()), []).append(r)
        else:
            remaining.append(r)
    transformed.extend(ConsistencyPatternRule(g, language) for g in groups.values())
    transformed.extend(remaining)
    return transformed
