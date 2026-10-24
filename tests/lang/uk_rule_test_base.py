"""Port of org.languagetool.rules.uk.AbstractRuleTest, the base class of the
Ukrainian rule tests (as functions/a small base class here)."""

from langtool.api import get_language
from langtool.tool import JLanguageTool

_lt = None


def uk_lt():
    """A JLanguageTool for Ukrainian (shared by the tests)"""
    global _lt
    if _lt is None:
        _lt = JLanguageTool(get_language('uk'))
    return _lt


class RuleTestBase:
    """AbstractRuleTest: set self.rule (and self.lt) in a fixture"""

    rule = None

    @property
    def lt(self):
        return uk_lt()

    def rule_match(self, text):
        return self.rule.match(self.lt.get_analyzed_sentence(text))

    def assert_empty_match(self, text):
        matches = self.rule_match(text)
        assert matches == [], (text, matches)

    def assert_has_error(self, text, *suggestions):
        matches = self.rule_match(text)
        assert len(matches) == 1, (text, matches)
        if suggestions:
            assert list(suggestions) == matches[0].suggested_replacements, text
        for sugg in suggestions:
            self.assert_empty_match(sugg)

    def assert_matches(self, num, text, consumer=None):
        matches = self.rule_match(text)
        assert len(matches) == num, 'Unexpected: %s' % (matches,)
        if consumer is not None:
            for m in matches:
                consumer(m.message)
