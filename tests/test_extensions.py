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
