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


def test_shards(demo_lt):
    # the shards (run in parallel tests) check every rule exactly once, the rules with the same id together
    tester = PatternRuleTester(demo_lt)
    checked = []
    tester.test_correct_sentences = checked.append
    tester.test_bad_sentences = tester.test_error_triggering_sentences = lambda rule: None
    for k in range(3):
        before = len(checked)
        assert not tester.run(shard=(k, 3))
        ids = {r.get_id() for r in checked[before:]}
        assert not ids & {r.get_id() for r in checked[:before]}
    assert sorted(map(id, checked)) == sorted(map(id, tester.rules))
    assert len({r.get_id() for r in tester.rules}) > 10
