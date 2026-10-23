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
