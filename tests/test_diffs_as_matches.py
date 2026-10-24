"""Port of org.languagetool.tools.DiffsAsMatchesTest (languagetool-core)."""

from langtool.diffs import DiffsAsMatches


def _repl(match):
    """List.toString() of the replacements"""
    return '[' + ', '.join(match.replacements) + ']'


def test_diffs_as_matches():
    """DiffsAsMatchesTest.testDiffsAsMatches"""
    diffs_as_matches = DiffsAsMatches()
    original0 = "This is a \"thing\". This is."
    revised0 = "This is a \"thing.\" This is."
    matches0 = diffs_as_matches.get_pseudo_matches(original0, revised0)
    assert len(matches0) == 1
    assert _repl(matches0[0]) == "[\"thing.\"]"
    assert matches0[0].from_pos == 10
    assert matches0[0].to_pos == 18
    original = "This are a sentence with too mistakes."
    revised = "This is a sentence with two mistakes."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert 2 == len(matches)
    assert "[is]" == _repl(matches[0])
    assert 5 == matches[0].from_pos
    assert 8 == matches[0].to_pos
    assert "[two]" == _repl(matches[1])
    assert 25 == matches[1].from_pos
    assert 28 == matches[1].to_pos
    original = "I am going to er remove one word."
    revised = "I am going to remove one word."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[]"
    assert matches[0].from_pos == 14
    assert matches[0].to_pos == 17
    original = "And I am going to remove one word."
    revised = "I am going to remove one word."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 4
    original = "I am going to add word."
    revised = "I am going to add one word."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[add one]"
    assert matches[0].from_pos == 14
    assert matches[0].to_pos == 17
    original = "a word at the start."
    revised = "Add a word at the start."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[Add a]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 1
    original = "Add word at position 1."
    revised = "Add a word at position 1."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[Add a]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 3
    original = "Esta serealiza cada semana."
    revised = "Esta se realiza cada semana."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[se realiza]"
    assert matches[0].from_pos == 5
    assert matches[0].to_pos == 14
    original = "Una cosa,una altra."
    revised = "Una cosa, una altra."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[cosa, ]"
    assert matches[0].from_pos == 4
    assert matches[0].to_pos == 9
    original = "Que el año nuevo empezó."
    revised = "El año nuevo empezó."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[El]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 6
    original = "¡Holà ! Estamos aquí."
    revised = "¡Hola! Estamos aquí."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[¡Hola!]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 7
    original = "I truely reserve."
    revised = "I truly deserve."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[truly deserve]"
    assert matches[0].from_pos == 2
    assert matches[0].to_pos == 16
    original = "}Describes how plants are important"
    revised = "It describes how plants are important"
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[It describes]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 10
    original = "(Calle)Hace falta tener en cuenta una economía estable, un trabajo bueno."
    revised = "Hace falta tener en cuenta una economía estable, un trabajo bueno."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 7
    original = "(Calle)Hace falta tener en cuenta una economía estable, un trabajo bueno."
    revised = "(Calle) Hace falta tener en cuenta una economía estable, un trabajo bueno."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[Calle) ]"
    assert matches[0].from_pos == 1
    assert matches[0].to_pos == 7
    original = "Joan Caprí fou un actor humorista i monologuista català."
    revised = "Joan Caprí fou un actor, humorista i monologuista català."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[actor,]"
    assert matches[0].from_pos == 18
    assert matches[0].to_pos == 23
    original = "Ei he vist el teu amic!"
    revised = "Ei, he vist el teu amic!"
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
    assert _repl(matches[0]) == "[Ei,]"
    assert matches[0].from_pos == 0
    assert matches[0].to_pos == 2
    original = "Va arribar tard a l'examen, perdent així després tota oportunitat d'aprovar l'assignatura."
    revised = "Va arribar tard a l'examen i, per això, va perdre tota oportunitat d'aprovar l'assignatura."
    matches = diffs_as_matches.get_pseudo_matches(original, revised)
    assert len(matches) == 1
