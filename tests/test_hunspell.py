"""Tests of langtool.hunspell, the pure Python port of Hunspell's spell
checking and suggestions (Hunspell 1.7.1, the version bundled with the Java
binding LanguageTool uses). The expected values were verified against the
native library with small synthetic dictionaries."""

import os
import threading

import pytest

from langtool import hunspell


def make_dict(tmp_path, name, aff, dic, encoding='utf-8'):
    aff_path = os.path.join(str(tmp_path), name + '.aff')
    dic_path = os.path.join(str(tmp_path), name + '.dic')
    with open(aff_path, 'wb') as f:
        f.write(aff.encode(encoding))
    with open(dic_path, 'wb') as f:
        f.write(dic.encode(encoding))
    return hunspell.Hunspell(dic_path, aff_path)


AFFIXES_AFF = """SET UTF-8
TRY esianrtolcdugmphbyfvkwz
PFX U Y 1
PFX U 0 un .
SFX S Y 2
SFX S 0 s [^s]
SFX S 0 es s
SFX E N 1
SFX E y ies [^aeiou]y
SFX D Y 2
SFX D 0 ed/S [^e]
SFX D 0 d e
NEEDAFFIX h
FORBIDDENWORD !
KEEPCASE k
"""

AFFIXES_DIC = """8
happy/U
city/E
boy/SE
glass/S
kind/USD
like/UD
foo/h
foo/S
bar/!
NASA/k
"""


def check(h, good, bad):
    for w in good:
        assert h.spell(w), w
    for w in bad:
        assert not h.spell(w), w


def test_affixes(tmp_path):
    """prefixes, suffixes with conditions, cross products, two-level
    suffixes (continuation classes), NEEDAFFIX, FORBIDDENWORD, KEEPCASE,
    casing and abbreviation dots"""
    h = make_dict(tmp_path, 'affixes', AFFIXES_AFF, AFFIXES_DIC)
    check(h, ['happy', 'unhappy', 'cities', 'boys', 'glasses', 'unkinds', 'unkind', 'kinded', 'kindeds', 'liked',
              'unliked', 'foo', 'foos', 'NASA', 'HAPPY', 'Happy', 'UNHAPPY', 'Unhappy', 'happy.', 'happy..',
              'Happy.'],
          ['citys', 'boies', 'glasss', 'likeds', 'bar', 'Bar', 'Nasa', 'nasa', 'hAppy', 'unglass', 'unglasses'])


def test_affix_suggestions(tmp_path):
    h = make_dict(tmp_path, 'affixes', AFFIXES_AFF, AFFIXES_DIC)
    assert h.suggest('citys') == ['city']
    assert h.suggest('boies') == ['boys']
    assert h.suggest('glasss') == ['glass', 'glasses']
    assert h.suggest('likeds') == ['liked', 'like']
    assert h.suggest('bar') == []


COMPOUNDS_AFF = """SET UTF-8
TRY esianrtolcdugmphbyfvkwz
COMPOUNDBEGIN x
COMPOUNDMIDDLE y
COMPOUNDEND z
COMPOUNDPERMITFLAG c
ONLYINCOMPOUND o
COMPOUNDMIN 2
FORBIDDENWORD d
CHECKSHARPS
WORDCHARS ß-.
SFX S Y 1
SFX S 0 s/co .
SFX N Y 1
SFX N 0 n .
"""

COMPOUNDS_DIC = """14
Haus/xN
haus/yz
Tür/xN
tür/yzN
Schlüssel/x
schlüssel/yz
Bund/xS
bund/yzS
Arbeit/xS
amt/z
s/o
Straße/xN
straße/yz
Hausamt/d
"""


def test_compounds(tmp_path):
    """COMPOUNDBEGIN/MIDDLE/END, COMPOUNDPERMITFLAG and ONLYINCOMPOUND
    (Fugen-s), forbidden compounds, CHECKSHARPS, BREAK and WORDCHARS"""
    h = make_dict(tmp_path, 'compounds', COMPOUNDS_AFF, COMPOUNDS_DIC)
    check(h, ['Haustür', 'Haustürschlüssel', 'Haustürschlüsselbund', 'Arbeitsamt', 'Arbeitamt', 'Bundsamt',
              'Haustürn', 'STRASSE', 'Straße', 'Straßetür', 'Haus-Tür', 'Haus-tür', 'Tür-', '-Tür', 'Haus.',
              'HAUSTÜR', 'Schlüsselbundamt', 'Haustüramt', 'Türhausamt', 'Haushausamt', 'Türhaus'],
          ['haustür', 'Bundesamt', 'Hausamt', 'Hauser', 'Amthaus', 'Strasse', 'STRASSENTÜR', 'Straßentür',
           'Haustürs', 's', 'Hauss'])


def test_compound_suggestions(tmp_path):
    h = make_dict(tmp_path, 'compounds', COMPOUNDS_AFF, COMPOUNDS_DIC)
    assert h.suggest('haustür') == ['haus tür', 'haus-tür', 'Haustür', 'haus']
    assert h.suggest('Bundesamt') == ['Bundsamt']
    assert h.suggest('Hauser') == ['Haus']
    assert h.suggest('Amthaus') == ['Amt haus', 'Amt-haus', 'Haus']
    assert h.suggest('Strasse') == ['Straße']


def test_circumfix(tmp_path):
    h = make_dict(tmp_path, 'circumfix', """SET UTF-8
CIRCUMFIX X
PFX G Y 1
PFX G 0 ge/X .
SFX T Y 2
SFX T 0 t/X .
SFX T 0 en .
""", """2
mach/GT
lieb/GT
""")
    check(h, ['gemacht', 'gemach', 'machen', 'geliebt', 'lieben', 'mach'], ['macht', 'gemachen', 'liebt'])
    assert h.suggest('macht') == ['mach']


def test_numbers_and_break(tmp_path):
    h = make_dict(tmp_path, 'break', """SET UTF-8
BREAK 3
BREAK -
BREAK ^-
BREAK -$
""", """3
foo
bar
e-mail
""")
    check(h, ['123', '1.000', '1,5', '12-', '-12', 'foo-bar', '-foo', 'foo-', 'e-mail', 'foo--bar', 'foo-bar-foo',
              '...', '.'],
          ['1..2', 'foo-baz'])
    assert h.suggest('foo-baz') == ['foo-bar']


def test_flag_types_and_aliases(tmp_path):
    h = make_dict(tmp_path, 'long', """SET UTF-8
FLAG long
AF 2
AF AaBb
AF Bb
SFX Aa Y 1
SFX Aa 0 s .
SFX Bb Y 1
SFX Bb 0 er .
""", """2
walk/1
talk/2
""")
    check(h, ['walk', 'walks', 'walker', 'talk', 'talker'], ['talks'])
    assert h.suggest('talks') == ['talk', 'walks']
    h = make_dict(tmp_path, 'num', """SET UTF-8
FLAG num
SFX 101 Y 1
SFX 101 0 s .
COMPOUNDFLAG 7
""", """2
cat/101,7
dog/7
""")
    check(h, ['cats', 'catdog', 'dogcat', 'dogcats'], ['dogs'])


def test_checkcompoundrep(tmp_path):
    h = make_dict(tmp_path, 'rep', """SET UTF-8
TRY ab
COMPOUNDFLAG Y
CHECKCOMPOUNDREP
REP 1
REP ss s
""", """4
foo/Y
bar/Y
bass/Y
foobas
""")
    check(h, ['foobar', 'barfoo', 'foobas'], ['foobass'])
    assert h.suggest('foobass') == ['foobas']


def test_iconv_and_ignore(tmp_path):
    h = make_dict(tmp_path, 'iconv', """SET UTF-8
ICONV 1
ICONV ’ '
IGNORE -
""", """2
don't
abc
""")
    check(h, ["don't", 'don’t', 'a-b-c', 'abc'], ['abd'])


def test_8bit_encoding(tmp_path):
    h = make_dict(tmp_path, 'latin1', """SET ISO8859-1
TRY aeo
SFX S Y 1
SFX S 0 s .
""", """2
caf\xe9/S
\xe9t\xe9
""", encoding='latin-1')
    check(h, ['café', 'cafés', 'CAFÉ', 'Café', 'été', 'ÉTÉ'], ['cafe'])
    assert h.suggest('cafe') == ['café']


def test_add_and_wordchars(tmp_path):
    h = make_dict(tmp_path, 'affixes', AFFIXES_AFF, AFFIXES_DIC)
    assert h.wordchars == ''
    assert not h.spell('LanguageTool')
    h.add('LanguageTool')
    assert h.spell('LanguageTool')
    assert h.spell('LANGUAGETOOL')
    assert not h.spell('languagetool')
    # add() removes the forbidden flag of a word
    h.add('bar')
    assert h.spell('bar')
    assert make_dict(tmp_path, 'compounds', COMPOUNDS_AFF, COMPOUNDS_DIC).wordchars == 'ß-.'


def test_get_dictionary_cache(tmp_path):
    make_dict(tmp_path, 'affixes', AFFIXES_AFF, AFFIXES_DIC)
    dic = os.path.join(str(tmp_path), 'affixes.dic')
    aff = os.path.join(str(tmp_path), 'affixes.aff')
    results = []
    threads = [threading.Thread(target=lambda: results.append(hunspell.get_dictionary(dic, aff)))
               for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r is results[0] for r in results)
    assert hunspell.get_dictionary(dic, aff).spell('unhappy')


def test_utf16_conversion():
    assert hunspell.u8_u16('Haus'.encode()) == 'Haus'
    assert hunspell.u8_u16('Straße'.encode()) == 'Straße'
    # characters outside the BMP end the conversion with U+FFFD, like in Hunspell
    assert hunspell.u8_u16('a\U0001F600b'.encode()) == 'a�'
    assert hunspell.u16_u8('Straße') == 'Straße'.encode()


def test_german_dictionary():
    """a few checks with the German dictionary (if it was downloaded)"""
    path = os.path.expanduser('~/.cache/langtool/dictionaries-v1/de/hunspell/de_DE')
    if not os.path.exists(path + '.dic'):
        pytest.skip('German Hunspell dictionary not downloaded')
    h = hunspell.get_dictionary(path + '.dic', path + '.aff')
    check(h, ['Haus', 'Haustürschlüssel', 'STRASSE', 'Straße', 'Arbeitsamt', 'Zweifelsfall', 'Hochschulreife',
              'Haus-Tür'],
          ['Hausx', 'Arbeitamt', 'Strasse', 'haus'])
    assert h.suggest('Teex')[:3] == ['Tee', 'Telex', 'Tees']
