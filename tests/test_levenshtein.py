"""The C implementation of the Levenshtein distance used by the multitoken
speller must give the same results as the pure Python one."""

import random

import pytest

from langtool._base import speedups
from langtool.rules import multitoken


@pytest.mark.skipif(speedups is None, reason='C extension not available')
def test_c_levenshtein_matches_python():
    rnd = random.Random(1)
    for _ in range(5000):
        a = ''.join(rnd.choice('abcé ') for _ in range(rnd.randint(0, 9)))
        b = ''.join(rnd.choice('abcé ') for _ in range(rnd.randint(0, 9)))
        assert speedups.levenshtein(a, b) == multitoken._levenshtein_distance(a, b)


def test_levenshtein():
    assert multitoken.levenshtein_distance('kitten', 'sitting') == 3
    assert multitoken.levenshtein_distance('', 'abc') == 3
    assert multitoken.levenshtein_distance('abc', 'abc') == 0
