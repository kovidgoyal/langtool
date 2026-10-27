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


# --- the C implementation (_speedups.HunDict) compared with the Python one ---
#
# The C implementation must give exactly the same results as the pure Python
# implementation (use_c=False). Both are compared on samples of words of
# real dictionaries: spell() on dictionary words, affixed forms, typos,
# case variants, compounds etc., suggest() on misspelled words. The Python
# suggestions are slow, they are computed in parallel subprocesses.
# LANGTOOL_HUNSPELL_COMPARE=<n> sets the number of suggestion words per
# dictionary (default 25; the check words are 120 times as many, at most
# 6000, and about as many valid word forms are added).

import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

from langtool._base import speedups as _speedups  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'src')
COMPARE_SUGGESTIONS = int(os.environ.get('LANGTOOL_HUNSPELL_COMPARE', '25'))
COMPARE_CHECKS = min(6000, 120 * COMPARE_SUGGESTIONS)
PY_SUGGEST_TIMEOUT = 30  # (seconds per word)
# LibreOffice dictionaries (language codes of langtool.hunspell_dictionaries)
LO_DICTIONARIES = ['en-US', 'de-DE', 'fr', 'es', 'pt-BR', 'nl', 'pl', 'ru']
# LanguageTool's German dictionaries
LT_DICTIONARIES = ['de_DE', 'de_AT', 'de_CH']

needs_c = pytest.mark.skipif(_speedups is None or not hasattr(_speedups, 'HunDict'),
                             reason='C extension not available')


def _dic_encoding(prefix):
    with open(prefix + '.aff', 'rb') as f:
        for line in f:
            m = re.match(rb'\s*SET\s+(\S+)', line)
            if m:
                enc = m.group(1).decode('latin-1')
                enc = {'microsoft-cp1251': 'cp1251'}.get(enc, enc)
                try:
                    ''.encode(enc)
                    return enc
                except LookupError:
                    return 'latin-1'
    return 'latin-1'


def sample_words(prefix, n_check, n_sug, seed=7):
    """Deterministic samples of words for spell() and suggest()"""
    rnd = random.Random(seed)
    enc = _dic_encoding(prefix)
    with open(prefix + '.dic', 'rb') as f:
        lines = f.read().decode(enc, 'replace').splitlines()[1:]
    stems = [line.split('/')[0].split('\t')[0].strip() for line in lines]
    stems = [s for s in stems if s and ' ' not in s and len(s) > 1]
    affixes = []
    with open(prefix + '.aff', 'rb') as f:
        for line in f.read().decode(enc, 'replace').splitlines():
            p = line.split()
            if len(p) >= 5 and p[0] in ('SFX', 'PFX'):
                a = p[3].split('/')[0]
                if a != '0':
                    affixes.append((p[0], p[2], a))
    words = rnd.sample(stems, min(len(stems), max(n_check // 3, n_sug)))
    alphabet = sorted({c for w in words for c in w if c.isalpha()}) or ['a']

    def typo(w):
        i = rnd.randrange(len(w))
        k = rnd.randrange(5)
        if k == 0:
            return w[:i] + w[i + 1:]
        if k == 1:
            return w[:i] + rnd.choice(alphabet) + w[i:]
        if k == 2:
            return w[:i] + rnd.choice(alphabet) + w[i + 1:]
        if k == 3 and i + 1 < len(w):
            return w[:i] + w[i + 1] + w[i] + w[i + 2:]
        return w + rnd.choice(alphabet)

    def affixed(w):
        if not affixes:
            return w
        kind, strip, a = rnd.choice(affixes)
        if kind == 'SFX':
            return (w[:-len(strip)] if strip != '0' and w.endswith(strip) else w) + a
        return a + (w[len(strip):] if strip != '0' and w.startswith(strip) else w)

    half = len(words) // 2
    check = list(words) + [affixed(w) for w in words[:half]] + [typo(w) for w in words[:half]]
    check += [typo(affixed(w)) for w in words[half:]]
    check += [w.upper() for w in words[:100]] + [w.capitalize() for w in words[:100]]
    check += [w.lower() for w in words[100:200]]
    for k in range(150):
        a, b = rnd.choice(stems), rnd.choice(stems)
        check.append(a + b.lower())
        if k % 3 == 0:
            check.append(a + '-' + b)
        if k % 5 == 0:
            check.append(a + 's' + b.lower())
    check += [w + '.' for w in words[:30]] + ['12.5', '1,000', '3-4', '--', 'x' * 120, 'ß', 'SS', 'O\'NEIL']
    sug = []
    for w in words[:n_sug]:
        t = typo(w)
        r = rnd.random()
        if r < 0.15:
            t = t.capitalize()
        elif r < 0.2:
            t = t.upper()
        elif r < 0.25:
            t = typo(affixed(w))
        elif r < 0.3:
            t = t + '-' + typo(rnd.choice(stems))
        elif r < 0.35:
            t = t + rnd.choice(stems).lower()
        sug.append(t)
    return check[:n_check], sug


_PY_RUNNER = r'''
import json, random, signal, sys
sys.path.insert(0, sys.argv[1])
from langtool import hunspell
task = json.load(sys.stdin)
h = hunspell.Hunspell(task['prefix'] + '.dic', task['prefix'] + '.aff', use_c=False)
check = task['check']
if task['forms']:
    # valid word forms: sampled entries with the affixes of their flags (and cross products)
    rnd = random.Random(11)
    forms = []
    for e in rnd.sample(h._all_entries, min(task['forms'], len(h._all_entries))):
        out = [e.word]
        sfx = []
        for f in sorted(e.flags):
            for se in h._sflag.get(ord(f) & 0xff, ()):
                w = h._sfx_add(se, e.word) if se.aflag == f else b''
                if w:
                    out.append(w)
                    sfx.append((w, se))
            for pe in h._pflag.get(ord(f) & 0xff, ()):
                w = h._pfx_add(pe, e.word) if pe.aflag == f else b''
                if w:
                    out.append(w)
                    out += [h._pfx_add(pe, w2) for w2, se in sfx[:3] if pe.opts & se.opts & 1]
        rnd.shuffle(out)
        forms += [w for w in out[:8] if w]
    dec = (lambda b: b.decode('utf-8', 'replace')) if h.utf8 else (lambda b: b.decode(h._codec, 'replace'))
    forms = [dec(w) for w in forms]
    forms += [w.upper() for w in forms[:200]] + [w.capitalize() for w in forms[200:400]]
    forms += [rnd.choice(forms) + rnd.choice(forms).lower() for _ in range(300)]
    check = check + forms


def suggest(w):
    # (None: the suggestions took longer than the time limit)
    if task['timeout'] and hasattr(signal, 'setitimer'):
        signal.setitimer(signal.ITIMER_REAL, task['timeout'])
    try:
        return h.suggest(w)
    except TimeoutError:
        return None
    finally:
        if task['timeout'] and hasattr(signal, 'setitimer'):
            signal.setitimer(signal.ITIMER_REAL, 0)


def timeout(signum, frame):
    raise TimeoutError()


if hasattr(signal, 'SIGALRM'):
    signal.signal(signal.SIGALRM, timeout)
out = {'check': check, 'spell': [h.spell(w) for w in check], 'suggest': [suggest(w) for w in task['suggest']]}
json.dump(out, sys.stdout)
'''


def _python_results(tasks):
    """Run the pure Python implementation on the tasks (dicts with prefix,
    check and suggest words) in parallel subprocesses"""
    env = dict(os.environ)
    env['LANGTOOL_PURE_PYTHON'] = '1'
    pending = list(enumerate(tasks))
    running = []
    results = [None] * len(tasks)
    nproc = max(2, os.cpu_count() or 2)
    while pending or running:
        while pending and len(running) < nproc:
            i, task = pending.pop(0)
            p = subprocess.Popen([sys.executable, '-c', _PY_RUNNER, SRC], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
            p.stdin.write(json.dumps(task))
            p.stdin.close()
            running.append((i, p))
        i, p = running.pop(0)
        out = p.stdout.read()
        err = p.stderr.read()
        assert p.wait() == 0, err[-3000:]
        results[i] = json.loads(out)
    return results


def _compare_dictionaries(prefixes):
    tasks = []
    c_results = []
    for prefix in prefixes:
        check, sug = sample_words(prefix, COMPARE_CHECKS, COMPARE_SUGGESTIONS)
        h = hunspell.Hunspell(prefix + '.dic', prefix + '.aff', use_c=True)
        assert h._c is not None
        spell = [h.spell(w) for w in check]
        # the words whose suggestions would take long in Python (MAP explosions: the C version prunes the MAP
        # search, the Python version does not) are skipped: the time of the C search without the pruning tells
        # (the Python version is about 50 times slower). The times grow with the load of the machine (e.g. the
        # tests running in parallel): at least the fastest 40% of the words are kept. The C time is not always
        # a good predictor of the Python time: the Python suggestions have a time limit (the words that take
        # longer are not compared)
        times = []
        for w in sug:
            t = time.thread_time()
            h._c.suggest(h._encode(w), 1.0, True)
            times.append(time.thread_time() - t)
        fastest = sorted(times)[:max(1, int(0.4 * len(times)))]
        limit = max([0.1] + fastest[-1:])
        sugs = [(w, h.suggest(w)) for w, t in zip(sug, times) if t <= limit]
        c_results.append((prefix, h, spell, sugs, len(sug)))
        tasks.append({'prefix': prefix, 'check': check, 'suggest': [], 'forms': COMPARE_CHECKS // 3, 'timeout': 0})
        # (a subprocess per word: a slow word does not hold up the others)
        tasks += [{'prefix': prefix, 'check': [], 'suggest': [w], 'forms': 0, 'timeout': PY_SUGGEST_TIMEOUT}
                  for w, _ in sugs]
    py = _python_results(tasks)
    diffs = []
    k = 0
    for prefix, h, spell, sugs, n_sug in c_results:
        name = os.path.basename(prefix)
        check = py[k]['check']  # (with the word forms of the Python runner)
        py_spell = py[k]['spell']
        spell = spell + [h.spell(w) for w in check[len(spell):]]
        k += 1
        py_sugs = []
        for _ in sugs:
            py_sugs += py[k]['suggest']
            k += 1
        assert len(py_spell) == len(spell) and len(py_sugs) == len(sugs)
        diffs += ['%s: spell(%r): C %r, Python %r' % (name, w, a, b)
                  for w, a, b in zip(check, spell, py_spell) if a != b]
        diffs += ['%s: suggest(%r): C %r, Python %r' % (name, w, a, b)
                  for (w, a), b in zip(sugs, py_sugs) if b is not None and a != b]
        # sanity checks: the samples have correct and misspelled words, and suggestions
        assert 0.2 * len(check) < sum(spell) < 0.9 * len(check), name
        assert sum(1 for _, s in sugs if s) >= 0.5 * len(sugs), name
        assert sum(1 for b in py_sugs if b is not None) >= 0.2 * n_sug, name
    assert not diffs, '%d differences:\n' % len(diffs) + '\n'.join(diffs[:30])


@needs_c
@pytest.mark.parametrize('code', LO_DICTIONARIES)
def test_c_vs_python_libreoffice(code):
    from langtool import hunspell_dictionaries as hd
    try:
        aff, dic = hd.locate(code, download_allowed=not os.environ.get('LANGTOOL_NO_DOWNLOAD'))
    except Exception as e:  # (no network)
        pytest.skip('dictionary for %s not available: %s' % (code, e))
    assert aff[:-4] == dic[:-4]
    _compare_dictionaries([aff[:-4]])


@needs_c
def test_c_vs_python_languagetool_german():
    from conftest import require_dictionaries
    require_dictionaries('de')
    from langtool.hunspell_rule import resource_file
    from langtool.api import get_language
    prefixes = []
    for name in LT_DICTIONARIES:
        dic = resource_file(get_language('de-DE'), '/de/hunspell/%s.dic' % name)
        assert dic is not None
        prefixes.append(dic[:-4])
    _compare_dictionaries(prefixes)


# small dictionaries with the features of Hunspell (for the comparison of
# the implementations): (name, aff, dic, encoding)
FEATURE_DICTS = [
    ('affixes', AFFIXES_AFF, AFFIXES_DIC, 'utf-8'),
    ('compounds', COMPOUNDS_AFF, COMPOUNDS_DIC, 'utf-8'),
    ('circumfix', """SET UTF-8
CIRCUMFIX X
PFX G Y 1
PFX G 0 ge/X .
SFX T Y 2
SFX T 0 t/X .
SFX T 0 en .
""", """2
mach/GT
lieb/GT
""", 'utf-8'),
    ('aliases', """SET UTF-8
FLAG long
AF 2
AF AaBb
AF Bb
AM 1
AM po:noun ph:wolk
SFX Aa Y 1
SFX Aa 0 s .
SFX Bb Y 1
SFX Bb 0 er .
TRY aeiotlkw
""", """3
walk/1
talk/2
work/1	1
""", 'utf-8'),
    ('numflags', """SET UTF-8
FLAG num
SFX 101 Y 1
SFX 101 0 s .
COMPOUNDFLAG 7
""", """2
cat/101,7
dog/7
""", 'utf-8'),
    ('complexprefixes', """SET UTF-8
COMPLEXPREFIXES
TRY abcdeiou
PFX A Y 2
PFX A 0 ab .
PFX A 0 abc/B .
PFX B Y 1
PFX B 0 xy .
SFX C Y 1
SFX C 0 ok .
""", """3
idu/AC
oaid/A
duc/C
""", 'utf-8'),
    ('map_key_ph', """SET UTF-8
TRY aeoiuntrsl
KEY qwertzuiop|asdfghjkl|yxcvbnm
MAP 3
MAP aáàâ
MAP e(é)(ée)è
MAP (ss)ß
REP 3
REP ^ph f
REP f$ ph
REP ue ü
MAXDIFF 3
SUGSWITHDOTS
""", """6
café
Straße
Tür
phone
fluß	ph:fluss
résumé	ph:resume
""", 'utf-8'),
    ('compoundrules', """SET UTF-8
TRY 0123456789abcdefghijklmnopqrstuvwxyz
COMPOUNDMIN 1
ONLYINCOMPOUND c
COMPOUNDRULE 3
COMPOUNDRULE n*1t
COMPOUNDRULE n*mp
COMPOUNDRULE a?b+
CHECKCOMPOUNDPATTERN 2
CHECKCOMPOUNDPATTERN o b z
CHECKCOMPOUNDPATTERN a /x b
CHECKCOMPOUNDDUP
CHECKCOMPOUNDCASE
WORDCHARS 0123456789
""", """14
0/nm
1/n1
2/nm
3/nm
st/tc
nd/tc
th/tc
%/pc
foo/a
bar/b
baz/b
Ex/b
fob/x
zoo/a
""", 'utf-8'),
    ('casing', """SET UTF-8
TRY esianrtolcdugmphb
FORCEUCASE U
KEEPCASE K
WARN W
FORBIDWARN
COMPOUNDFLAG C
NOSUGGEST N
SUBSTANDARD S
""", """8
foo/UC
bar/C
iPod/K
NASA/K
Oops/W
damn/N
ain't/S
OpenOffice.org
""", 'utf-8'),
    ('fullstrip', """SET UTF-8
FULLSTRIP
NEEDAFFIX X
TRY aeiou
SFX A Y 2
SFX A andare vado/BX andare
SFX A are o/B are
SFX B Y 1
SFX B 0 ne/X .
PFX P Y 1
PFX P 0 ri .
""", """3
andare/AP
parlare/AP
dare/A
""", 'utf-8'),
    ('conv', """SET UTF-8
ICONV 2
ICONV ’ '
ICONV ﬁ fi
OCONV 1
OCONV ' ’
IGNORE ­
BREAK 2
BREAK -
BREAK –
TRY ' aeiou
""", """4
don't
o'clock
field
fine
""", 'utf-8'),
    ('latin2', """SET ISO8859-2
TRY aeoiuzsc
LANG pl
SFX S Y 1
SFX S 0 ów .
""", """3
żółw/S
źdźbło
Łódź
""", 'iso8859-2'),
]


def _feature_words(dic):
    out = []
    for line in dic.splitlines()[1:]:
        w = line.split('/')[0].split('\t')[0].strip()
        if not w:
            continue
        out += [w, w.upper(), w.capitalize(), w.lower(), w[1:], w[:-1], w + w, w + 's', w[::-1], w + '.', 'X' + w]
        if len(w) > 2:
            out += [w[:1] + w[2:], w[:2] + w[1] + w[2:], w[1] + w[0] + w[2:]]
    return out


@needs_c
def test_c_vs_python_features(tmp_path):
    """the synthetic dictionaries (compounds, COMPOUNDRULE, circumfix,
    flag types and aliases, complex prefixes, MAP, KEY, REP, ph: fields,
    ICONV/OCONV/IGNORE/BREAK, casing flags, FULLSTRIP, 8-bit encoding),
    add() and the time limit"""
    extra = ['happy', 'unhappy', 'citys', 'boies', 'glasss', 'likeds', 'NASA', 'Haustür', 'haustür', 'Bundesamt',
             'Strasse', 'STRASSE', 'Haustürschlüsselbund', 'Haus-Tür', 'HAUSTÜR', 'Arbeitsamt', 'gemacht', 'macht',
             'walks', 'talker', 'talks', 'cats', 'dogcats', 'abidu', 'abcxyidu', 'iduok', 'cafe', 'Strase', 'Tuer',
             'fone', 'flus', 'resume', 'Resume', 'RESUME.', '10th', '11st', '21st', '100%', 'foobar', 'barbaz',
             'foobaz', 'fobbar', 'foobarbaz', 'Foo', 'FOO', 'foofoo', 'Barfoo', 'ipod', 'IPOD', 'Nasa', 'Oops',
             'damn', 'aint', "ain't", 'openoffice.org', 'OPENOFFICE.ORG', 'vado', 'vadone', 'parlo', 'riparlo',
             'do', 'dane', 'don’t', "dont", 'o’clock', 'ﬁeld', 'ﬁne', 'fi\xadne', 'field-fine', 'field–fine',
             'zolw', 'żółwów', 'zdzblo', 'Lodz', 'ŁÓDŹ', 'x' * 99, 'x' * 101, '', '.', '1.5', '--', "'"]
    for name, aff, dic, enc in FEATURE_DICTS:
        hc = make_dict(tmp_path, name, aff, dic, enc)
        hp = hunspell.Hunspell(hc.dic_path, hc.aff_path, use_c=False)
        assert hc._c is not None and hp._c is None
        words = _feature_words(dic) + extra
        for w in words:
            assert hc.spell(w) == hp.spell(w), (name, w)
            assert hc.suggest(w) == hp.suggest(w), (name, w)
            assert hc.suggest(w, 10.0) == hp.suggest(w), (name, w)
        for h in (hc, hp):
            h.add('Zwiebelkuchen')
            h.add('bar')
            h.add('NEWword')
        for w in words + ['Zwiebelkuchen', 'ZWIEBELKUCHEN', 'zwiebelkuchen', 'Zwiebelkuche', 'newword', 'NEWWORD']:
            assert hc.spell(w) == hp.spell(w), (name, w)
            assert hc.suggest(w) == hp.suggest(w), (name, w)
        # (with an exhausted time limit the search stops early)
        assert isinstance(hc.suggest('Zwiebelkuche', 0.0), list)
