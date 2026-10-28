"""Tests of the disk cache of derived data (langtool.diskcache): invalidation,
corruption, concurrent writers, the disabled mode, the regular expression
store, the pickling of the C types, and that the rules loaded from the cache
are the same as those loaded from the XML files (and give the same
results)."""

import copyreg
import enum
import json
import os
import pickle
import subprocess
import sys
import threading
import types

import pytest

from langtool import diskcache, jregex, resources
from langtool._base import speedups

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')


@pytest.fixture
def cache_dir(tmp_path):
    """an empty disk cache directory for the test (restores the settings)"""
    old_enabled, old_dir, old_max = diskcache._enabled, diskcache._directory, diskcache._max_size
    old_store, old_new = diskcache._regex_store, dict(diskcache._regex_new)
    diskcache.set_disk_cache(True, tmp_path / 'derived')
    diskcache._regex_store = None
    diskcache._regex_new.clear()
    yield tmp_path / 'derived'
    diskcache._enabled, diskcache._directory, diskcache._max_size = old_enabled, old_dir, old_max
    diskcache._regex_store = old_store
    diskcache._regex_new.clear()
    diskcache._regex_new.update(old_new)


def _counting_build(value):
    calls = []

    def build():
        calls.append(1)
        return value
    return build, calls


def _entries(d):
    out = []
    for root, dirs, files in os.walk(str(d)):
        out.extend(os.path.join(root, f) for f in files if f.endswith('.pkl'))
    return out


@pytest.mark.pure_smoke
def test_roundtrip_and_hit(cache_dir):
    value = {'a': [1, 2.5, 'x'], 'b': frozenset({'y', 'z'}), 'c': (None, True)}
    build, calls = _counting_build(value)
    assert diskcache.cached('test-kind', ('k', 1), build) == value
    assert len(calls) == 1
    assert len(_entries(cache_dir)) == 1
    assert diskcache.cached('test-kind', ('k', 1), build) == value
    assert len(calls) == 1  # (from the cache)
    # another key: another entry
    assert diskcache.cached('test-kind', ('k', 2), build) == value
    assert len(calls) == 2
    assert len(_entries(cache_dir)) == 2


@pytest.mark.pure_smoke
def test_disabled(cache_dir, monkeypatch):
    build, calls = _counting_build([1, 2])
    diskcache.set_disk_cache(False)
    assert not diskcache.is_enabled()
    for _ in range(2):
        assert diskcache.cached('test-kind', 'k', build) == [1, 2]
    assert len(calls) == 2
    assert not os.path.exists(str(cache_dir))
    # the environment variable (when nothing is set with set_disk_cache)
    diskcache.set_disk_cache(None)
    for v in ('0', 'off', 'No', 'false'):
        monkeypatch.setenv('LANGTOOL_DISK_CACHE', v)
        assert not diskcache.is_enabled()
    monkeypatch.setenv('LANGTOOL_DISK_CACHE', '1')
    assert diskcache.is_enabled()
    monkeypatch.delenv('LANGTOOL_DISK_CACHE')
    assert diskcache.is_enabled()
    # nothing compiled is stored when disabled
    diskcache.set_disk_cache(False)
    jregex._cache.pop(('x(?:y|z)+disabled', 0), None)
    jregex.compile('x(?:y|z)+disabled')
    assert ('x(?:y|z)+disabled', 0) not in diskcache._regex_new


def test_api(cache_dir, tmp_path):
    import langtool
    langtool.set_disk_cache(True, tmp_path / 'other')
    assert langtool.get_disk_cache_dir() == str(tmp_path / 'other')
    diskcache.cached('test-kind', 'k', lambda: 1)
    assert _entries(tmp_path / 'other')
    langtool.clear_disk_cache()
    assert not _entries(tmp_path / 'other')
    langtool.set_disk_cache(False)
    assert not diskcache.is_enabled()


def test_invalidation_when_a_dependency_changes(cache_dir, tmp_path):
    dep = tmp_path / 'words.txt'
    dep.write_text('a\nb\n')

    def build():
        return dep.read_text().split()
    assert diskcache.cached('test-dep', 'k', build, deps=[str(dep)]) == ['a', 'b']
    assert diskcache.stats['test-dep']['write'] == 1
    misses = diskcache.stats['test-dep']['miss']
    assert diskcache.cached('test-dep', 'k', build, deps=[str(dep)]) == ['a', 'b']
    assert diskcache.stats['test-dep']['miss'] == misses
    dep.write_text('a\nb\nc\n')
    assert diskcache.cached('test-dep', 'k', build, deps=[str(dep)]) == ['a', 'b', 'c']
    assert diskcache.stats['test-dep']['miss'] == misses + 1
    # a removed dependency
    dep.unlink()
    assert diskcache.cached('test-dep', 'k', lambda: 'gone', deps=[str(dep)]) == 'gone'
    # dependencies noted during the build (e.g. entity files of XML rule files)
    dep2 = tmp_path / 'noted.txt'
    dep2.write_text('1')

    def build2():
        diskcache.note_dependency(str(dep2))
        return int(dep2.read_text())
    assert diskcache.cached('test-dep2', 'k', build2) == 1
    os.utime(str(dep2), ns=(1, 1))
    dep2.write_text('2')
    os.utime(str(dep2), ns=(10 ** 18, 10 ** 18))
    assert diskcache.cached('test-dep2', 'k', build2) == 2


def test_nested_builds(cache_dir, tmp_path):
    dep = tmp_path / 'inner.txt'
    dep.write_text('1')
    calls = []

    def inner():
        diskcache.note_dependency(str(dep))
        return int(dep.read_text())

    def outer():
        calls.append(1)
        # (an inner build without dependencies too: its (empty) set of dependencies equals the outer one's)
        return diskcache.cached('test-inner0', 'k', lambda: 0) + diskcache.cached('test-inner', 'k', inner)
    assert diskcache.cached('test-outer', 'k', outer) == 1
    assert diskcache.cached('test-outer', 'k', outer) == 1
    assert len(calls) == 1
    # the outer value depends on the file noted by the inner build
    dep.write_text('22')
    assert diskcache.cached('test-outer', 'k', outer) == 22
    assert len(calls) == 2
    assert not getattr(diskcache._local, 'deps', None)


def test_invalidation_when_the_package_changes(cache_dir, tmp_path, monkeypatch):
    # the package fingerprint covers the code and data files (size and modification time)
    pkg = tmp_path / 'pkg'
    (pkg / 'data').mkdir(parents=True)
    (pkg / 'mod.py').write_text('x = 1\n')
    (pkg / 'data' / 'rules.xml').write_text('<rules/>')
    (pkg / '__pycache__').mkdir()
    monkeypatch.setattr(diskcache, '_PACKAGE_DIR', str(pkg))
    monkeypatch.setattr(resources, '_root', str(pkg))  # (the resource root is the package directory)
    monkeypatch.setattr(diskcache, '_fingerprint', None)
    fp1 = diskcache.package_fingerprint()
    monkeypatch.setattr(diskcache, '_fingerprint', None)
    (pkg / '__pycache__' / 'mod.cpython.pyc').write_text('ignored')
    assert diskcache.package_fingerprint() == fp1
    for path, text in ((pkg / 'mod.py', 'x = 2\n'), (pkg / 'data' / 'rules.xml', '<rules></rules>')):
        monkeypatch.setattr(diskcache, '_fingerprint', None)
        path.write_text(text)
        fp2 = diskcache.package_fingerprint()
        assert fp2 != fp1
        fp1 = fp2
    # a new fingerprint means another directory: the entries of the old one are not used
    monkeypatch.setattr(diskcache, '_fingerprint', 'a' * 64)
    build, calls = _counting_build('v')
    diskcache.cached('test-kind', 'k', build)
    diskcache.cached('test-kind', 'k', build)
    assert len(calls) == 1
    monkeypatch.setattr(diskcache, '_fingerprint', 'b' * 64)
    diskcache.cached('test-kind', 'k', build)
    assert len(calls) == 2
    assert sorted(os.listdir(str(cache_dir))) == ['a' * 20, 'b' * 20]


@pytest.mark.pure_smoke
def test_fingerprint_of_an_installed_package(tmp_path, monkeypatch):
    # an installed package has a manifest (written by setup.py when it is built: a hash of the contents of its
    # files); the files are then not looked at, only the manifest and the extension modules
    pkg = tmp_path / 'pkg'
    (pkg / 'data').mkdir(parents=True)
    (pkg / 'mod.py').write_text('x = 1\n')
    (pkg / 'data' / 'rules.xml').write_text('<rules/>')
    (pkg / '_speedups.so').write_bytes(b'\0' * 10)
    monkeypatch.setattr(diskcache, '_PACKAGE_DIR', str(pkg))
    monkeypatch.setattr(resources, '_root', str(pkg))  # (the resource root is the package directory)
    monkeypatch.delenv('LANGTOOL_DISK_CACHE_VERIFY', raising=False)

    def fingerprint():
        monkeypatch.setattr(diskcache, '_fingerprint', None)
        monkeypatch.setattr(diskcache, '_manifest', None)
        return diskcache.package_fingerprint()
    monkeypatch.setattr(diskcache, '_manifest', None)
    assert diskcache.installed_manifest() is None
    walked = fingerprint()
    digest = diskcache.write_manifest(str(pkg))
    monkeypatch.setattr(diskcache, '_manifest', None)
    assert diskcache.installed_manifest() == {
        'format': diskcache.MANIFEST_FORMAT, 'sha256': digest, 'files': 2,
        'hashes': {'mod.py': diskcache.file_hash(str(pkg / 'mod.py')),
                   'data/rules.xml': diskcache.file_hash(str(pkg / 'data' / 'rules.xml'))}}
    # the digest depends on the contents (not on the modification times), not on __pycache__ and extension modules
    os.utime(str(pkg / 'mod.py'), ns=(1, 1))
    (pkg / '__pycache__').mkdir()
    (pkg / '__pycache__' / 'mod.pyc').write_text('x')
    assert diskcache.manifest_digest(str(pkg)) == (digest, 2)
    fp1 = fingerprint()
    assert fp1 != walked
    stats = []
    real_scandir = os.scandir
    monkeypatch.setattr(os, 'scandir', lambda *a: stats.append(a) or real_scandir(*a))
    # an edited installed file is not noticed (installed files do not change; reinstalling writes a new manifest)
    (pkg / 'data' / 'rules.xml').write_text('<rules></rules>')
    assert fingerprint() == fp1
    assert not stats
    # a new manifest (reinstalled package)
    diskcache.write_manifest(str(pkg))
    fp2 = fingerprint()
    assert fp2 != fp1
    # a rebuilt extension module
    (pkg / '_speedups.so').write_bytes(b'\0' * 11)
    fp3 = fingerprint()
    assert fp3 != fp2
    # LANGTOOL_DISK_CACHE_VERIFY=1: the files are looked at (like in a source tree)
    monkeypatch.setenv('LANGTOOL_DISK_CACHE_VERIFY', '1')
    monkeypatch.setattr(diskcache, '_manifest', None)
    assert diskcache.installed_manifest() is None
    fp4 = fingerprint()
    (pkg / 'data' / 'rules.xml').write_text('<rules>  </rules>')
    assert fingerprint() != fp4
    monkeypatch.setenv('LANGTOOL_DISK_CACHE_VERIFY', '0')
    assert fingerprint() == fp3
    # a damaged or foreign manifest: the files are looked at
    for text in ('{', '{"format": 99, "sha256": "x"}', '[]'):
        (pkg / diskcache.MANIFEST_NAME).write_text(text)
        monkeypatch.setattr(diskcache, '_manifest', None)
        assert diskcache.installed_manifest() is None
        assert fingerprint() not in (fp1, fp2, fp3)


def test_fingerprint_does_not_import_lxml():
    # (importing lxml.etree takes about 10 ms; it is only needed to parse XML files)
    code = ('import sys; sys.path.insert(0, %r); from langtool import diskcache; diskcache.package_fingerprint(); '
            'print("lxml.etree" in sys.modules)' % SRC)
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == 'False'


def test_old_directories_are_removed(cache_dir, monkeypatch):
    monkeypatch.setattr(diskcache, '_fingerprint', 'c' * 64)
    diskcache.cached('test-kind', 'k', lambda: 1)
    old = cache_dir / ('c' * 20)
    os.utime(str(old / 'last-used'), (1, 1))
    os.utime(str(old), (1, 1))
    monkeypatch.setattr(diskcache, '_fingerprint', 'd' * 64)
    diskcache.cached('test-kind', 'k', lambda: 1)
    assert os.listdir(str(cache_dir)) == ['d' * 20]


@pytest.mark.pure_smoke
@pytest.mark.parametrize('damage', ['flip', 'truncate', 'garbage', 'empty', 'magic'])
def test_corrupt_entries_are_rebuilt(cache_dir, damage):
    value = {'words': ['x%d' % i for i in range(1000)]}
    diskcache.cached('test-corrupt', 'k', lambda: value)
    path, = _entries(cache_dir)
    data = bytearray(open(path, 'rb').read())
    if damage == 'flip':
        data[-100] ^= 0x55
    elif damage == 'truncate':
        data = data[:len(data) // 2]
    elif damage == 'garbage':
        data = bytearray(os.urandom(len(data)))
    elif damage == 'empty':
        data = bytearray()
    else:
        data[:4] = b'XXXX'
    with open(path, 'wb') as f:
        f.write(data)
    errors = diskcache.stats.get('test-corrupt', {}).get('error', 0)
    build, calls = _counting_build({'words': ['rebuilt']})
    assert diskcache.cached('test-corrupt', 'k', build) == {'words': ['rebuilt']}
    assert len(calls) == 1
    assert diskcache.stats['test-corrupt']['error'] == errors + 1
    # the entry was replaced
    assert diskcache.cached('test-corrupt', 'k', build) == {'words': ['rebuilt']}
    assert len(calls) == 1


def test_unreadable_directory_falls_back(tmp_path, cache_dir):
    blocker = tmp_path / 'file'
    blocker.write_text('not a directory')
    diskcache.set_disk_cache(True, blocker / 'derived')
    build, calls = _counting_build([3])
    assert diskcache.cached('test-kind', 'k', build) == [3]
    assert diskcache.cached('test-kind', 'k', build) == [3]
    assert len(calls) == 2


def test_uncacheable_values(cache_dir):
    class Local:
        pass
    build, calls = _counting_build([Local()])
    diskcache.cached('test-unc', 'k', build)
    diskcache.cached('test-unc', 'k', build)
    assert len(calls) == 2
    assert not _entries(cache_dir)

    def persist(obj):
        raise diskcache.Uncacheable('no')
    v = diskcache.load_or_build('test-unc2', 'k', lambda: [Local()], persist=persist)
    assert isinstance(v[0], Local)
    assert not _entries(cache_dir)


def test_build_errors_are_raised(cache_dir):
    def build():
        raise ValueError('bad data')
    with pytest.raises(ValueError):
        diskcache.cached('test-err', 'k', build)
    assert not _entries(cache_dir)


def test_external_references(cache_dir):
    marker = object()
    resolved = []

    def persist(obj):
        return 'M' if obj is marker else None

    def resolve(pid):
        resolved.append(pid)
        return marker
    v = diskcache.load_or_build('test-ext', 'k', lambda: [marker, {'m': marker}], persist=persist, resolve=resolve)
    assert v[0] is marker
    v = diskcache.load_or_build('test-ext', 'k', lambda: None, persist=persist, resolve=resolve)
    assert v[0] is marker and v[1]['m'] is marker
    assert resolved == ['M']  # (once per object)


_WRITER = r'''
import sys, json
sys.path.insert(0, sys.argv[1])
from langtool import diskcache, jregex, resources
diskcache.set_disk_cache(True, sys.argv[2])
n = int(sys.argv[3])
v = diskcache.cached('test-concurrent', 'k', lambda: list(range(200000)))
assert v == list(range(200000))
for i in range(50):
    jregex.compile('w%d[a-z]+(?:x|y)%d' % (n, i))
diskcache.flush_regex_store()
print(json.dumps(diskcache.stats.get('test-concurrent')))
'''


def test_concurrent_writers(cache_dir, tmp_path):
    script = tmp_path / 'writer.py'
    script.write_text(_WRITER)
    procs = [subprocess.Popen([sys.executable, str(script), SRC, str(cache_dir), str(n)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) for n in range(6)]
    for p in procs:
        out, err = p.communicate(timeout=300)
        assert p.returncode == 0, err.decode()
    files = [f for f in _entries(cache_dir)]
    assert len([f for f in files if 'test-concurrent' in f]) == 1
    leftovers = [n for _, _, fs in os.walk(str(cache_dir)) for n in fs if n.startswith('.tmp-')]
    assert leftovers == []
    build, calls = _counting_build(None)
    assert diskcache.cached('test-concurrent', 'k', build) == list(range(200000))
    assert not calls
    # the regular expressions of (some of) the writers are in the store (concurrent updates may lose some, which are
    # then compiled again)
    diskcache._regex_store = None
    found = [n for n in range(6) if diskcache.stored_regex(('w%d[a-z]+(?:x|y)%d' % (n, 0), 0)) is not None]
    assert found
    assert diskcache.stored_regex(('w%d[a-z]+(?:x|y)%d' % (found[0], 49), 0)).fullmatch('w%dabcx49' % found[0])


def test_concurrent_threads(cache_dir):
    results = []
    calls = []

    def build():
        calls.append(1)
        return {'x': list(range(1000))}

    def work():
        for i in range(5):
            results.append(diskcache.cached('test-threads', i % 2, build))
    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 40 and all(r == {'x': list(range(1000))} for r in results)
    assert len(calls) <= 16


@pytest.mark.pure_smoke
def test_regex_store(cache_dir):
    pattern = '(?i)st[oö]re[0-9]+\\p{Lu}*x'
    jregex._cache.pop((pattern, 0), None)
    compiled = jregex.compile(pattern)
    assert (pattern, 0) in diskcache._regex_new
    diskcache.flush_regex_store()
    assert not diskcache._regex_new
    # a new process: the stored compiled expression is used
    diskcache._regex_store = None
    jregex._cache.pop((pattern, 0), None)
    stored = diskcache.stored_regex((pattern, 0))
    assert stored is not None and stored is not compiled
    assert stored.pattern == compiled.pattern and stored.flags == compiled.flags
    for s in ('STÖRE12X', 'store1x', 'stare1x', 'store12ABx'):
        assert bool(stored.fullmatch(s)) == bool(compiled.fullmatch(s))
    assert jregex.compile(pattern).pattern == compiled.pattern
    assert (pattern, 0) not in diskcache._regex_new
    # invalid patterns are not stored, the error is raised as without the store
    with pytest.raises(jregex.JavaRegexError):
        jregex.compile('a(b')
    assert ('a(b', 0) not in diskcache._regex_new


@pytest.mark.pure_smoke
@pytest.mark.parametrize('damage', ['index', 'entry', 'truncate', 'magic'])
def test_damaged_regex_store(cache_dir, damage):
    patterns = ['dam[a-z]+%d(?:x|y)' % i for i in range(20)]
    for p in patterns:
        jregex._cache.pop((p, 0), None)
        jregex.compile(p)
    diskcache.flush_regex_store()
    diskcache._regex_store = None
    assert all(diskcache.stored_regex((p, 0)) is not None for p in patterns)
    path = diskcache._regex_path()
    diskcache._regex_store = None
    data = bytearray(open(path, 'rb').read())
    if damage == 'index':
        data[diskcache._REGEX_HEADER.size + 5] ^= 0xff
    elif damage == 'entry':
        data[-50] ^= 0xff
    elif damage == 'truncate':
        data = data[:len(data) - 200]
    else:
        data[:4] = b'XXXX'
    with open(path, 'wb') as f:
        f.write(data)
    found = [diskcache.stored_regex((p, 0)) for p in patterns]
    if damage == 'entry':
        assert found.count(None) == 1  # (only the damaged entry is not used)
    elif damage == 'truncate':
        assert None in found and any(found)
    else:
        assert found == [None] * len(patterns)
    for p, c in zip(patterns, found):
        if c is not None:
            assert c.pattern == jregex._cache[(p, 0)].pattern
    # the expressions compiled again are stored again
    for p in patterns:
        jregex._cache.pop((p, 0), None)
        jregex.compile(p)
    diskcache.flush_regex_store()
    diskcache._regex_store = None
    assert all(diskcache.stored_regex((p, 0)) is not None for p in patterns)


@pytest.mark.skipif(speedups is None, reason='C extension')
def test_c_types_pickle():
    from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
    from langtool.patterns.pattern_token import PatternToken, PosToken
    from langtool.patterns.string_matcher import StringMatcher
    t = AnalyzedToken('Häuser', 'SUB:NOM:PLU:NEU', 'Haus')
    t.whitespace_before = True
    t2 = pickle.loads(pickle.dumps(t, 5))
    assert type(t2) is AnalyzedToken
    assert t2.__getstate__() == t.__getstate__()
    r = AnalyzedTokenReadings([t], 5)
    r2 = pickle.loads(pickle.dumps(r, 5))
    assert r2.__getstate__()[1:] == r.__getstate__()[1:] and r2.readings[0].token == 'Häuser'
    pt = PatternToken('a.*', False, True)
    pt.skip = 2
    pt.pos_token = PosToken('NN.*', False, StringMatcher('NN.*', True, True))
    pt2 = pickle.loads(pickle.dumps(pt, 5))
    assert pt2.skip == 2 and pt2.text_matcher.pattern == 'a.*' and pt2.pos_token.pos_pattern.matches('NNS')
    # NULL members stay NULL (not None)
    empty = speedups.PatternTokenBase()
    vals, mask, d = empty.__getstate__()
    assert mask and d is None
    assert pickle.loads(pickle.dumps(empty)).__getstate__() == (vals, mask, d)
    with pytest.raises((TypeError, ValueError)):
        speedups.PatternTokenBase().__setstate__(((1,), 0, None))
    hints = speedups.RuleHints(2, (), None)
    assert pickle.loads(pickle.dumps(hints)).__reduce__()[1] == (2, (), None)


# --- the rules loaded from the cache ---

_IGNORED = {'compiled', '_regex_match', '_pos_regex_match', '_pattern'}  # (compiled lazily or eagerly)


def _state(obj):
    if hasattr(type(obj), '__getstate__') and speedups is not None and isinstance(
            obj, (speedups.AnalyzedTokenBase, speedups.AnalyzedTokenReadingsBase, speedups.StringMatcherBase,
                  speedups.PosTokenBase, speedups.PatternTokenBase)):
        vals, mask, d = obj.__getstate__()
        return [('#members', vals), ('#null', mask), ('#dict', d)]
    out = []
    for name in copyreg._slotnames(type(obj)):
        if name in ('__weakref__', '__dict__'):
            continue
        out.append((name, getattr(obj, name, '#unset')))
    if hasattr(obj, '__dict__'):
        out.extend(sorted(vars(obj).items()))
    return out


def _compare(a, b, ctx, memo, path='rules'):
    """deep comparison of the object graphs a and b (also their sharing)"""
    ta, tb = type(a), type(b)
    assert ta is tb, (path, ta, tb)
    if a is None or ta in (bool, int, float, str, bytes):
        assert a == b, (path, a, b)
        return
    if a is ctx['lang_a']:
        assert b is ctx['lang_b'], path
        return
    if a is b:
        return  # (an object that both refer to, e.g. the unifier configuration of the default variant)
    if isinstance(a, (type, enum.Enum, types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
        assert a is b or a == b, path
        return
    if ta.__name__ != 'StringMatcher' and ta not in (tuple, frozenset):
        # (the sharing of the mutable objects must be the same, e.g. of the PosTokens of the language's cache by the
        # rules of different files; the interned StringMatchers are shared by the rules of all languages, those of
        # other languages may be in the process: they are compared by value)
        seen = memo.get(id(a))
        if seen is not None:
            assert seen is b, ('sharing differs', path)
            return
        memo[id(a)] = b
        ctx['keep'].append(a)
    if ta.__name__ == 'Pattern' and hasattr(a, 'fullmatch'):
        assert (a.pattern, a.flags) == (b.pattern, b.flags), path
        return
    if ta in (list, tuple):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _compare(x, y, ctx, memo, '%s[%d]' % (path, i))
        return
    if ta is dict:
        assert list(a) == list(b), path
        for k in a:
            _compare(a[k], b[k], ctx, memo, '%s[%r]' % (path, k))
        return
    if ta in (set, frozenset):
        assert a == b, path
        return
    if 'Filter' in ta.__name__ or 'filter' in ta.__module__:
        return  # (a filter: created by the filter factory when loading)
    sa, sb = _state(a), _state(b)
    assert [k for k, _ in sa] == [k for k, _ in sb], path
    for (k, x), (_, y) in zip(sa, sb):
        if k in _IGNORED or k == '#members' and ta.__name__ == 'StringMatcher':
            if k == '#members':
                names = ('pattern', 'value', 'value_lower', 'values', 'compiled', 'cache', 'possible_values', 'kind',
                         'case_sensitive', 'is_regexp')
                for n, xv, yv in zip(names, x, y):
                    if n not in ('compiled', 'cache'):
                        _compare(xv, yv, ctx, memo, '%s.%s' % (path, n))
            continue
        _compare(x, y, ctx, memo, '%s.%s' % (path, k))


def _fresh_language(code):
    from langtool.api import get_language
    from langtool.language import Language
    lang = get_language(code)
    return Language(lang.short_code, lang.definition, lang.variant_definition, lang.registry)


@pytest.fixture
def no_static(monkeypatch):
    """the rules of the built-in languages are loaded from the XML files and the disk cache, not from the static
    rule tables (the fallback path)"""
    from langtool.patterns import static
    monkeypatch.setenv('LANGTOOL_STATIC_RULES', '0')
    static.reset()
    yield
    monkeypatch.undo()
    static.reset()


@pytest.fixture
def xml_cache(no_static):
    """saves and restores the (in-memory) cache of the disambiguation rules"""
    from langtool import extensions
    saved = dict(extensions._xml_cache)
    extensions._xml_cache.clear()
    yield extensions._xml_cache
    extensions._xml_cache.clear()
    extensions._xml_cache.update(saved)


def _hits(kind):
    return diskcache.stats.get(kind, {}).get('hit', 0)


@pytest.mark.parametrize('code', ['de-DE', 'nl'])
def test_cached_rules_are_identical(cache_dir, xml_cache, code):
    from langtool import extensions
    diskcache.set_disk_cache(False)
    lang_a = _fresh_language(code)
    rules_a = lang_a.get_pattern_rules()
    disamb_a = extensions.disambiguation_rules(lang_a)
    diskcache.set_disk_cache(True, cache_dir)
    hits = _hits('rules-grammar'), _hits('rules-disambiguation')
    for _ in range(2):  # (built and written, then loaded)
        lang_b = _fresh_language(code)
        xml_cache.clear()
        rules_b = lang_b.get_pattern_rules()
        disamb_b = extensions.disambiguation_rules(lang_b)
    # (an entry per file)
    assert (_hits('rules-grammar'), _hits('rules-disambiguation')) == (hits[0] + len(lang_b.get_rule_file_names()),
                                                                       hits[1] + 1)
    ctx = {'lang_a': lang_a, 'lang_b': lang_b, 'keep': []}
    _compare(rules_a, rules_b, ctx, {})
    _compare(disamb_a, disamb_b, ctx, {})
    # the side effects of the loading on the language
    for attr in ('unifier_config', 'disambiguation_unifier_config'):
        ua, ub = getattr(lang_a, attr), getattr(lang_b, attr)
        assert list(ua.equivalence_types) == list(ub.equivalence_types)
        assert ua.equivalence_features == ub.equivalence_features
        _compare(list(ua.equivalence_types.values()), list(ub.equivalence_types.values()), ctx, {})
    assert list(lang_a.pos_token_cache) == list(lang_b.pos_token_cache)


_DUMP = r'''
import sys, json
sys.path.insert(0, sys.argv[1])
from langtool import diskcache
from langtool.api import get_language
from langtool.tool import JLanguageTool
code, texts = sys.argv[2], json.loads(sys.argv[3])
lt = JLanguageTool(get_language(code))
out = []
for t in texts:
    for m in lt.check(t):
        out.append([m.rule.get_full_id(), m.from_pos, m.to_pos, m.message, m.short_message,
                    list(m.suggested_replacements)])
print(json.dumps({'matches': out, 'stats': {k: v for k, v in diskcache.stats.items()}}))
'''

_TEXTS = {
    'de-DE': ['Das ist ein Haus, das die Fehler hat.', 'Er hat das Auto gesehn und die Frau gefreut sich.',
              'Ich habe keine Lust, nach Hause zu gehen, wegen dem Wetter.', 'Der Abfluß ist verstopft.'],
    'en-US': ['This are a test with a error.', 'He go to school yesterday, did not he?',
              "Its a nice day and their going to the the park.", 'I could of done it.'],
}


@pytest.mark.parametrize('code', ['en-US', 'de-DE'])
def test_same_results_with_and_without_cache(tmp_path, code):
    script = tmp_path / 'dump.py'
    script.write_text(_DUMP)
    results = {}
    # (the rule entries: the rules loaded from the XML files, without the static rule tables; and with them: no rule
    # entries, the same results)
    for name, env in (('disabled', {'LANGTOOL_DISK_CACHE': '0'}), ('cold', {}), ('warm', {}), ('static', None)):
        e = dict(os.environ)
        e.pop('LANGTOOL_DISK_CACHE', None)
        e['LANGTOOL_DISK_CACHE_DIR'] = str(tmp_path / ('derived' if env is not None else 'derived-static'))
        if env is not None:
            e['LANGTOOL_STATIC_RULES'] = '0'
            e.update(env)
        p = subprocess.run([sys.executable, str(script), SRC, code, json.dumps(_TEXTS[code])], env=e,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        assert p.returncode == 0, p.stderr.decode()
        results[name] = json.loads(p.stdout.decode())
    assert results['disabled']['matches']
    assert results['cold']['matches'] == results['disabled']['matches']
    assert results['warm']['matches'] == results['disabled']['matches']
    assert not results['disabled']['stats']
    n = results['cold']['stats']['rules-grammar']['write']  # (an entry per rule file)
    assert n >= 2
    assert results['warm']['stats']['rules-grammar'] == {'hit': n, 'miss': 0, 'write': 0, 'error': 0}
    assert all(s['miss'] == 0 and s['error'] == 0 for s in results['warm']['stats'].values())
    assert results['static']['matches'] == results['disabled']['matches']
    from langtool.patterns import static
    if static.enabled() and static.available_languages():
        assert 'rules-grammar' not in results['static']['stats']
        assert 'rules-disambiguation' not in results['static']['stats']


def test_registered_languages_are_not_cached(cache_dir, xml_cache):
    from langtool import extensions
    from langtool.api import get_language
    lang = _fresh_language('xx')  # (the demo language of the tests, see conftest.py)
    assert diskcache.language_key(lang) is None
    assert diskcache.language_key(get_language('en-US')) == 'en-US'
    assert lang.get_pattern_rules()
    extensions.disambiguation_rules(lang)
    assert not [f for f in _entries(cache_dir) if 'rules-' in os.path.basename(f)]


def _writes(kind):
    return diskcache.stats.get(kind, {}).get('write', 0)


def test_variants_share_entries(cache_dir, xml_cache):
    from langtool.patterns.string_matcher import StringMatcher
    codes = ['en-US', 'en-GB', 'en-AU']
    diskcache.set_disk_cache(False)
    fresh = {}
    for code in codes:
        fresh[code] = _fresh_language(code)
        fresh[code].get_pattern_rules()
    diskcache.set_disk_cache(True, cache_dir)
    loaded = {}
    for code in codes:
        lang = loaded[code] = _fresh_language(code)
        files = lang.get_rule_file_names()
        writes, hits = _writes('rules-grammar'), _hits('rules-grammar')
        lang.get_pattern_rules()
        built = _writes('rules-grammar') - writes
        if code == 'en-US':
            assert built == len(files)
        else:
            # (only the files of the variant are loaded from XML, grammar.xml etc. come from the cache)
            assert built == len([f for f in files if os.sep + code + os.sep in f])
            assert _hits('rules-grammar') - hits == len(files) - built >= 2
    entries = [f for f in _entries(cache_dir) if os.path.basename(f).startswith('rules-grammar')]
    assert len(entries) == len(set(f for c in codes for f in loaded[c].get_rule_file_names()))
    # the same rules as loaded from XML, a variant loaded from entries built for another variant too
    for code in codes:
        lang_b = _fresh_language(code)
        rules_b = lang_b.get_pattern_rules()
        ctx = {'lang_a': fresh[code], 'lang_b': lang_b, 'keep': []}
        _compare(fresh[code].get_pattern_rules(), rules_b, ctx, {})
    # as when loading from XML: the variants have their own rules, the interned StringMatchers are shared
    for langs in (fresh, loaded):
        us, gb = langs['en-US'].get_pattern_rules(), langs['en-GB'].get_pattern_rules()
        assert not set(map(id, us)) & set(map(id, gb))
        m_us = {id(t.text_matcher) for r in us for t in (r.pattern_tokens or ()) if type(t.text_matcher) is StringMatcher}
        m_gb = {id(t.text_matcher) for r in gb for t in (r.pattern_tokens or ()) if type(t.text_matcher) is StringMatcher}
        assert len(m_us & m_gb) > 1000


def test_mother_tongue_rules(cache_dir, no_static):
    from langtool import language as L
    saved = dict(L._mother_tongue_rules)
    L._mother_tongue_rules.clear()
    try:
        diskcache.set_disk_cache(False)
        lang_a = _fresh_language('en-US')
        mt_a = lang_a.get_mother_tongue_rules('de')
        rules_a = lang_a.get_pattern_rules()
        diskcache.set_disk_cache(True, cache_dir)
        # the grammar entries don't depend on the state of the unifier configuration: those built without the rules
        # for German speakers are used with them
        L._mother_tongue_rules.clear()
        _fresh_language('en-US').get_pattern_rules()
        writes = _writes('rules-grammar')
        for _ in range(2):
            L._mother_tongue_rules.clear()
            lang_b = _fresh_language('en-US')
            mt_b = lang_b.get_mother_tongue_rules('de')
            rules_b = lang_b.get_pattern_rules()
        assert _writes('rules-grammar') == writes + 1  # (the file of the rules for German speakers)
        ctx = {'lang_a': lang_a, 'lang_b': lang_b, 'keep': []}
        memo = {}
        _compare(mt_a, mt_b, ctx, memo)
        _compare(rules_a, rules_b, ctx, memo)
        ua, ub = lang_a.unifier_config, lang_b.unifier_config
        assert list(ua.equivalence_types) == list(ub.equivalence_types)
        assert ua.equivalence_features == ub.equivalence_features
        _compare(list(ua.equivalence_types.values()), list(ub.equivalence_types.values()), ctx, memo)
    finally:
        L._mother_tongue_rules.clear()
        L._mother_tongue_rules.update(saved)


def test_size_limit(cache_dir, monkeypatch):
    big = list(range(50000))  # (about 100 KB compressed)
    diskcache.set_disk_cache(True, cache_dir, max_size=0)
    for i in range(10):
        diskcache.cached('test-size', i, lambda: big + [i])
    paths = {i: diskcache._entry_path('test-size', i) for i in range(10)}
    sizes = {i: os.path.getsize(p) for i, p in paths.items()}
    assert all(os.path.exists(p) for p in paths.values())  # (no limit)
    # the least recently used entries (by modification time) are removed first
    now = 2000000000
    for i, p in paths.items():
        os.utime(p, (now - 10000 + i * 10, now - 10000 + i * 10))
    os.utime(paths[0], (now - 5000, now - 5000))  # (entry 0 used recently)
    limit = sum(sizes.values()) - 1
    diskcache.set_disk_cache(True, cache_dir, max_size=limit)
    diskcache.cached('test-size', 'new', lambda: [1])
    remaining = [i for i, p in paths.items() if os.path.exists(p)]
    assert os.path.exists(diskcache._entry_path('test-size', 'new'))
    total = sum(os.path.getsize(f) for f in _entries(cache_dir))
    assert total <= limit * 0.8
    assert 0 in remaining and 1 not in remaining
    assert remaining == [0] + list(range(10 - len(remaining) + 1, 10))
    # a hit marks the entry as used
    p = paths[9]
    os.utime(p, (1, 1))
    build, calls = _counting_build(None)
    assert diskcache.cached('test-size', 9, build) == big + [9] and not calls
    assert os.path.getmtime(p) > 1
    # the setting: argument, environment variable (MB), default
    diskcache.set_disk_cache(True, cache_dir)
    monkeypatch.setenv('LANGTOOL_DISK_CACHE_MAX_MB', '2.5')
    assert diskcache.max_size() == int(2.5 * (1 << 20))
    monkeypatch.setenv('LANGTOOL_DISK_CACHE_MAX_MB', '0')
    assert diskcache.max_size() == 0
    monkeypatch.delenv('LANGTOOL_DISK_CACHE_MAX_MB')
    assert diskcache.max_size() == diskcache.DEFAULT_MAX_SIZE
    diskcache.set_disk_cache(True, cache_dir, max_size=12345)
    assert diskcache.max_size() == 12345
    # other package versions are removed when they are least recently used
    monkeypatch.setattr(diskcache, '_fingerprint', 'e' * 64)
    diskcache.set_disk_cache(True, cache_dir, max_size=10 ** 9)
    diskcache.cached('test-size', 'other', lambda: big)
    other = diskcache._entry_path('test-size', 'other')
    os.utime(other, (1, 1))
    diskcache._dir_checked.clear()
    monkeypatch.setattr(diskcache, '_fingerprint', 'f' * 64)
    diskcache.set_disk_cache(True, cache_dir, max_size=sum(os.path.getsize(f) for f in _entries(cache_dir)))
    diskcache.cached('test-size', 'x', lambda: big)
    assert not os.path.exists(os.path.dirname(other))
