"""Port of org.languagetool.rules.patterns.DemoPatternRuleTest and of the
example sentence checks (PatternRuleTest) for the demo language."""

from langtool.testing import PatternRuleTester


def test_demo_rule_examples(demo_lt):
    tester = PatternRuleTester(demo_lt)
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))


def test_check_demo(demo_lt):
    # rules from tests/data/rules/xx/grammar.xml
    matches = demo_lt.check('This is a test sentence foo bar.')
    assert isinstance(matches, list)
