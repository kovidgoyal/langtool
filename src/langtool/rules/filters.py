"""Rule filters (the <filter class="..." args="..."/> element of pattern
rules). Port of org.languagetool.rules.patterns.RuleFilter, RegexRuleFilter
and the language independent filters of languagetool-core."""

import regex

from .. import jregex
from ..patterns.loader import UnsupportedFilter


class RuleFilter:
    """Base class: return the (possibly modified) match, or None to discard
    it."""

    def __init__(self, language=None):
        self.language = language

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        raise NotImplementedError()

    def matches(self, arguments, pattern_tokens, first_match_token, token_positions):
        """Used by disambiguation rules."""
        from .base import RuleMatch, Rule

        class _Fake(Rule):
            def get_id(self):
                return 'FAKE-RULE-FOR-FILTER'

            def get_description(self):
                return '<none>'

        fake = RuleMatch(_Fake(), None, 0, 1, '(internal rule)')
        return self.accept_rule_match(fake, arguments, first_match_token, pattern_tokens, token_positions) is not None

    @staticmethod
    def get_required(key, args):
        v = args.get(key)
        if v is None:
            raise ValueError("Missing key '%s'" % key)
        return v

    @staticmethod
    def get_optional(key, args, default=None):
        v = args.get(key)
        return default if v is None else v

    @staticmethod
    def get_position(from_str, pattern_tokens, match):
        if from_str.startswith('marker'):
            i = 0
            while (i < len(pattern_tokens) and pattern_tokens[i].start_pos < match.from_pos) or \
                    (i < len(pattern_tokens) and pattern_tokens[i].is_sentence_start):
                i += 1
            i += 1
            if len(from_str) > 6:
                i += int(from_str.replace('marker', ''))
        else:
            i = int(from_str)
        if i < 1 or i > len(pattern_tokens):
            raise ValueError('RuleFilter: Index out of bounds in %s, value: %s' % (match.rule.get_full_id(),
                                                                                 from_str))
        return i - 1

    @staticmethod
    def get_skip_corrected_reference(token_positions, ref):
        if ref < 0:
            return ref
        corrected = 0
        for i, p in enumerate(token_positions):
            if i >= ref:
                break
            corrected += p
        return corrected - 1


class RegexRuleFilter:

    def __init__(self, language=None):
        self.language = language

    def accept_rule_match(self, match, arguments, sentence, pattern_match):
        raise NotImplementedError()


class RegexAntiPatternFilter(RegexRuleFilter):

    def accept_rule_match(self, match, arguments, sentence, pattern_match):
        aps = arguments.get('antipatterns')
        if aps is None:
            raise ValueError("Missing 'antiPatterns:' in 'args' in <filter> of rule " + match.rule.get_full_id())
        text = sentence.text
        for ap in aps.split('|'):
            p = jregex.compile(ap)
            for m in p.finditer(text):
                if (m.start() <= match.to_pos <= m.end()) or (m.start() <= match.from_pos <= m.end()):
                    return None
        return match


class FilterFactory:

    def __init__(self):
        self.filters = {}
        self.regex_filters = {}

    def register(self, java_class_name, cls):
        self.filters[java_class_name] = cls

    def register_regex(self, java_class_name, cls):
        self.regex_filters[java_class_name] = cls

    def get_filter(self, class_name, language):
        cls = self.filters.get(class_name)
        if cls is None:
            from .. import extensions
            cls = extensions.lookup('filter', class_name)
        if cls is None:
            raise UnsupportedFilter(class_name)
        return cls(language)

    def get_regex_filter(self, class_name, language):
        cls = self.regex_filters.get(class_name)
        if cls is None:
            from .. import extensions
            cls = extensions.lookup('regex_filter', class_name)
        if cls is None:
            raise UnsupportedFilter(class_name)
        return cls(language)


_default = None


def default_filter_factory():
    global _default
    if _default is None:
        ff = FilterFactory()
        ff.register_regex('org.languagetool.rules.patterns.RegexAntiPatternFilter', RegexAntiPatternFilter)
        from . import core_filters
        core_filters.register(ff)
        _default = ff
    return _default
