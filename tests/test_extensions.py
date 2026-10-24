"""Tests of the registry of language specific components."""

from langtool import extensions


def test_register_per_language():
    a, b, g = object(), object(), object()
    extensions.register('rule', '_TestRule', a, language='aa')
    extensions.register('rule', '_TestRule', b, language='bb')
    extensions.register('rule', '_TestRule', g)
    assert extensions.lookup('rule', '_TestRule', 'aa') is a
    assert extensions.lookup('rule', '_TestRule', 'bb') is b
    assert extensions.lookup('rule', '_TestRule', 'cc') is g
    assert extensions.lookup('rule', '_TestRule') is g
    assert extensions.lookup('rule', '_NoSuchRule', 'aa') is None


def test_rule_examples():
    """examples=(wrong, fixed) in a rule spec: the IncorrectExample and
    CorrectExample constructor arguments of the Java rules
    (Rule.addExamplePair); the spec itself is not changed"""
    from langtool.api import get_language
    from langtool.messages import messages_for
    lang = get_language('en-US')
    spec = ('CommaWhitespaceRule', dict(examples=('a<marker> ,</marker> b', 'a<marker>,</marker> b')))

    class _Lang:
        definition = dict(rules=[spec, ('UppercaseSentenceStartRule', dict(examples=('<marker>x</marker>', 'X')))])
        variant_definition = {}
        short_code = 'xx'
        code = 'xx'

        def __getattr__(self, name):
            return getattr(lang, name)

    comma, upper = extensions.create_rules(_Lang(), messages_for('en'))
    assert [(e.example, e.corrections) for e in comma.incorrect_examples] == [('a<marker> ,</marker> b', [','])]
    assert [e.example for e in comma.correct_examples] == ['a<marker>,</marker> b']
    # no marker in the fixed sentence: the incorrect example has no correction
    assert [(e.example, e.corrections) for e in upper.incorrect_examples] == [('<marker>x</marker>', None)]
    assert [e.example for e in upper.correct_examples] == ['X']
    assert 'examples' in spec[1]


def test_language_hooks():
    """The 'to_advanced_typography' and 'filter_rule_matches' extensions of
    a language (French.toAdvancedTypography, French.filterRuleMatches); the
    JLanguageTool calls filter_rule_matches (LanguageDependentRuleMatchFilter)
    with the ids of the active rules"""
    from langtool.api import get_language
    from langtool.tool import LEVEL_DEFAULT, JLanguageTool, is_rule_active_for_level
    lang = get_language('xx')
    assert lang.to_advanced_typography('a "b"') == lang.base_to_advanced_typography('a "b"')
    calls = []

    def filter_rule_matches(language, matches, annotated_text, enabled_rules):
        calls.append((language, annotated_text.plain_text, set(enabled_rules)))
        return matches[:1]

    extensions.register('to_advanced_typography', 'xx', lambda language, text: text.upper(), language='xx')
    extensions.register('filter_rule_matches', 'xx', filter_rule_matches, language='xx')
    try:
        assert lang.to_advanced_typography('a "b"') == 'A "B"'
        lt = JLanguageTool(lang)
        matches = lt.check('a a a a.')
        assert len(matches) <= 1
        assert calls and calls[0][0] is lang and calls[0][1] == 'a a a a.'
        assert calls[0][2] == {r.get_id() for r in lt.get_all_active_rules()
                               if is_rule_active_for_level(r, LEVEL_DEFAULT)}
    finally:
        extensions._registry.pop(('to_advanced_typography', 'xx', 'xx'))
        extensions._registry.pop(('filter_rule_matches', 'xx', 'xx'))
    assert lang.filter_rule_matches(['m1', 'm2'], None, set()) == ['m1', 'm2']
