"""Tests of the resource root (langtool.resources: relocating the data files
of the package) and of the support for freezing applications
(langtool.freeze)."""

import compileall
import json
import os
import shutil
import subprocess
import sys

import pytest

import langtool
from langtool import diskcache, freeze, resources
from langtool._base import speedups

from conftest import require_dictionaries

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')


@pytest.fixture
def fresh_root(monkeypatch):
    """the resource root is decided anew in the test (and restored)"""
    monkeypatch.delenv(resources.ENV_VAR, raising=False)
    monkeypatch.setattr(resources, '_root', None)
    monkeypatch.setattr(resources, '_requested', None)


def _fake_root(path):
    os.makedirs(os.path.join(str(path), 'data', 'rules'))
    return str(path)


def test_default_root_is_the_package_directory(fresh_root):
    assert resources.root() == resources.package_dir()
    assert langtool.get_resource_dir() == resources.package_dir()
    assert resources.rules_dir() == os.path.join(resources.package_dir(), 'data', 'rules')
    from langtool import language
    assert language.RESOURCE_DIR == os.path.join(resources.package_dir(), 'data', 'resource')


def test_environment_variable_and_set_resource_dir(fresh_root, tmp_path, monkeypatch):
    a, b = _fake_root(tmp_path / 'a'), _fake_root(tmp_path / 'b')
    monkeypatch.setenv(resources.ENV_VAR, a)
    assert resources.root() == a
    monkeypatch.setattr(resources, '_root', None)
    langtool.set_resource_dir(b)  # (wins over the environment variable)
    assert resources.root() == b
    langtool.set_resource_dir(b)  # (the same: no error)
    # the root can't change once it is used
    with pytest.raises(langtool.ResourceDirError):
        langtool.set_resource_dir(a)
    assert resources.root() == b
    assert resources.relative(os.path.join(b, 'data', 'rules', 'x.xml')) == 'data/rules/x.xml'
    assert resources.relative(os.path.join(a, 'data')) is None


def test_invalid_resource_dirs(fresh_root, tmp_path, monkeypatch):
    with pytest.raises(langtool.ResourceDirError):
        langtool.set_resource_dir(tmp_path)
    monkeypatch.setenv(resources.ENV_VAR, str(tmp_path / 'missing'))
    with pytest.raises(langtool.ResourceDirError):
        resources.root()


def test_frozen_application(fresh_root, tmp_path, monkeypatch):
    # in a frozen application whose package directory has no data, the data is looked for in sys._MEIPASS
    # (PyInstaller) and next to the executable
    monkeypatch.setattr(resources, '_PACKAGE_DIR', str(tmp_path / 'archive' / 'langtool'))
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'app' / 'app.exe'))
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path / 'meipass'), raising=False)
    assert resources.is_frozen()
    with pytest.raises(langtool.ResourceDirError):
        resources.root()
    exe = _fake_root(tmp_path / 'app' / 'langtool')
    assert resources.root() == exe
    monkeypatch.setattr(resources, '_root', None)
    meipass = _fake_root(tmp_path / 'meipass' / 'langtool')
    assert resources.root() == meipass
    monkeypatch.setattr(resources, '_root', None)
    pkg = _fake_root(tmp_path / 'archive' / 'langtool')
    assert resources.root() == pkg


def test_portable_keys():
    # the paths below the resource root are relative in the keys of the disk cache entries
    root = resources.root()
    key = ('en', os.path.join(root, 'data', 'rules', 'en', 'grammar.xml'), [root + os.sep + 'x', 3],
           '/elsewhere/file', root + 'x')
    assert diskcache._portable_key(key) == (
        'en', '<langtool>/data/rules/en/grammar.xml', ['<langtool>/x', 3], '/elsewhere/file', root + 'x')


def test_manifest_of_another_version_is_not_used(tmp_path, monkeypatch, caplog):
    root = _fake_root(tmp_path / 'root')
    with open(os.path.join(root, '__init__.py'), 'w') as f:
        f.write("__version__ = '0.0.1'\n")
    diskcache.write_manifest(root)
    m = diskcache._read_manifest
    with open(os.path.join(root, diskcache.MANIFEST_NAME)) as f:
        assert json.load(f)['version'] == '0.0.1'
    assert m(root) is None
    assert 'not of this version' in caplog.text
    with open(os.path.join(root, '__init__.py'), 'w') as f:
        f.write("__version__ = %r\n" % langtool.__version__)
    diskcache.write_manifest(root)
    assert m(root)['version'] == langtool.__version__


def test_hidden_imports():
    names = freeze.hidden_imports()
    assert names == sorted(names)
    for n in ('langtool', 'langtool.api', 'langtool.lang', 'langtool.lang.en', 'langtool.lang.de.filters',
              'langtool.patterns.static', 'langtool.rules.core_filters', 'langtool.lang.is_'):
        assert n in names
    if speedups is not None:
        assert 'langtool._speedups' in names
    assert not [n for n in names if n.startswith(('langtool.data', 'langtool._rule_tables'))]


def test_data_files_need_a_manifest(tmp_path):
    root = _fake_root(tmp_path / 'root')
    with pytest.raises(freeze.FreezeError):
        freeze.data_files(root)
    with pytest.raises(freeze.FreezeError):
        freeze.data_files(tmp_path / 'missing')


@pytest.fixture(scope='module')
def frozen_layout(tmp_path_factory):
    """(code directory, resource directory): a copy of the package without
    the data files and without the source files (only .pyc, like in a
    frozen application) and the resource files copied with
    freeze.copy_resources()"""
    top = tmp_path_factory.mktemp('frozen')
    res = str(top / 'res')
    copied = freeze.copy_resources(res)
    code = str(top / 'code' / 'langtool')
    shutil.copytree(resources.package_dir(), code,
                    ignore=shutil.ignore_patterns('data', '_rule_tables', '*.json', '__pycache__', '*.c', '*.h'))
    assert compileall.compile_dir(code, quiet=1, legacy=True)
    for dirpath, _, filenames in os.walk(code):
        for n in filenames:
            if n.endswith('.py'):
                os.unlink(os.path.join(dirpath, n))
    return str(top / 'code'), res, copied


def test_copy_resources_and_data_files(frozen_layout):
    _, res, copied = frozen_layout
    assert diskcache.MANIFEST_NAME in copied
    files = freeze.data_files(res)
    rels = [rel for _, rel in files]
    assert sorted(rels) == sorted(copied)
    for rel in ('dictionaries.json', 'hunspell_dictionaries.json', diskcache.MANIFEST_NAME,
                'data/rules/en/grammar.xml', 'data/resource/en/multiwords.txt'):
        assert rel in rels
    for src, rel in files:
        assert src == os.path.join(res, *rel.split('/'))
    if speedups is not None and hasattr(speedups, 'rule_blob_names'):
        for code in speedups.rule_blob_names():
            assert '_rule_tables/%s.ltrt' % code in rels
    # the manifest covers the code too (the static rule tables check the modules of the XML loading)
    with open(os.path.join(res, diskcache.MANIFEST_NAME)) as f:
        hashes = json.load(f)['hashes']
    assert 'patterns/loader.py' in hashes and 'data/rules/en/grammar.xml' in hashes
    # copying again replaces the files; not into a directory with other files
    assert freeze.copy_resources(res) == copied
    with pytest.raises(freeze.FreezeError):
        freeze.copy_resources(os.path.dirname(res))


_SCRIPT = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import langtool
from langtool import diskcache
tool = langtool.LanguageTool('en-US')
matches = [(m.rule_id, m.offset, m.length, m.message, m.replacements)
           for m in tool.check('This are a sentence with a error. He go to school yesterday.')]
jt = [v for v in vars(tool).values() if hasattr(v, 'rules_with')][0]
print(json.dumps({
    'root': langtool.get_resource_dir(),
    'module': langtool.__file__,
    'status': langtool.static_rules_status().get('en'),
    'matches': matches,
    'fingerprint': diskcache.package_fingerprint(),
    'misses': sum(v['miss'] for k, v in diskcache.stats.items() if k != 'regex'),
    'source_files': sorted(set(r.source_file for r in jt.rules_with(['PLURAL_VERB_AFTER_THIS']))),
}))
'''


def _run(code_dir, env):
    env = dict(os.environ, **env)
    env.pop('PYTHONPATH', None)
    r = subprocess.run([sys.executable, '-I', '-c', _SCRIPT, code_dir], env=env, capture_output=True,
                       text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_relocated_resources_without_source_files(frozen_layout, tmp_path):
    # the package without its data files and without the code files (a frozen application): the resource root
    # is set with LANGTOOL_RESOURCE_DIR, the static rule tables are used (the manifest has the hashes of the code)
    # and the results are the same; the entries of the disk cache are used when the resource root moves (e.g.
    # PyInstaller's onefile mode extracts the files into a new directory for every run)
    require_dictionaries('en')
    code, res, _ = frozen_layout
    env = {'LANGTOOL_CACHE_DIR': langtool.get_cache_dir(), 'LANGTOOL_DISK_CACHE_DIR': str(tmp_path / 'derived')}
    ref = _run(SRC, dict(env, LANGTOOL_DISK_CACHE='0'))
    assert ref['root'] == resources.package_dir()
    out = _run(code, dict(env, LANGTOOL_RESOURCE_DIR=res))
    assert out['module'].startswith(code) and out['root'] == res
    assert out['matches'] == ref['matches'] and out['matches']
    assert out['status'] == ref['status']
    if speedups is not None and 'en' in getattr(speedups, 'rule_blob_names', lambda: ())():
        assert out['status'] == 'ok'
    assert out['source_files'] == [os.path.join(res, 'data', 'rules', 'en', 'grammar.xml')]
    # the rules from the XML files and the disk cache (a new one: without the C extension the run above has used
    # the XML files too)
    env['LANGTOOL_STATIC_RULES'] = '0'
    env['LANGTOOL_DISK_CACHE_DIR'] = str(tmp_path / 'derived2')
    first = _run(code, dict(env, LANGTOOL_RESOURCE_DIR=res))
    assert first['matches'] == ref['matches']
    moved = res + '-moved'
    os.rename(res, moved)
    try:
        second = _run(code, dict(env, LANGTOOL_RESOURCE_DIR=moved))
    finally:
        os.rename(moved, res)
    assert second['fingerprint'] == first['fingerprint']
    assert first['misses'] > 0 and second['misses'] == 0
    assert second['matches'] == ref['matches']
    assert second['source_files'] == [os.path.join(moved, 'data', 'rules', 'en', 'grammar.xml')]


def test_cli_resource_dir(frozen_layout, capsys):
    from langtool import cli
    _, res, _ = frozen_layout
    # (the root of this process is the package directory already: the option is checked)
    with pytest.raises(langtool.ResourceDirError):
        cli.main(['--resource-dir', res, 'languages'])
