"""Port of org.languagetool.rules.de.SimpleGermanPatternRuleTest (the
<example> sentences of rules/de-DE-x-simple-language/grammar.xml; as in
Java, PatternRuleTest does not skip the rules of the variant's own
grammar.xml for de-DE-x-simple-language)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.testing import PatternRuleTester
from langtool.tool import JLanguageTool


def test_rules():
    """SimpleGermanPatternRuleTest.testRules"""
    require_dictionaries('de')
    lang = get_language('de-DE-x-simple-language')
    tester = PatternRuleTester(JLanguageTool(lang))
    assert tester.rules
    assert all(r.source_file.replace('\\', '/').endswith('/rules/de-DE-x-simple-language/grammar.xml')
               for r in tester.rules)
    failures = tester.run()
    assert not failures, '\n'.join(map(str, failures))
    assert not lang._pattern_rule_problems
