"""Tests of the downloads into the cache: downloads_needed(),
download_size(), is_ready(), the download hook, aborting downloads and the
URL opener. Fake manifests and a fake URL opener are used (no network)."""

import hashlib
import io
import os
import subprocess
import sys
import threading
import zipfile

import pytest

import langtool
from langtool import api, dictionaries
from langtool import hunspell_dictionaries as hd
from langtool.dictionaries import DownloadAborted, DownloadItem, DownloadProgress

from conftest import require_dictionaries

LANG = 'tl-PH'


class FakeOpener:
    """An URL opener (see set_url_opener()) serving bytes from a dict,
    in chunks of at most chunk_size bytes."""

    def __init__(self, files, chunk_size=1000):
        self.files = files
        self.chunk_size = chunk_size
        self.opened = []
        self.closed = 0

    def __call__(self, url):
        self.opened.append(url)
        if url not in self.files:
            raise OSError('not found: ' + url)
        opener = self

        class Response(io.BytesIO):
            def read(self, n=-1):
                return super().read(min(n, opener.chunk_size) if n >= 0 else opener.chunk_size)

            def close(self):
                opener.closed += 1
                super().close()

        return Response(self.files[url])


def make_jar(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for path, data in entries.items():
            z.writestr(path, data)
    return buf.getvalue()


def source(url, data, files):
    return {'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
            'files': [{'name': name, 'path': path, 'size': 0} for name, path in files]}


def hunspell_entry(url, data):
    return {'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    """Fake manifests for the language tl (two jars, one of them with OpenNLP
    in the name, and a Hunspell dictionary) served by a FakeOpener, an
    empty cache directory."""
    jar1 = make_jar({'org/languagetool/resource/tl/a.dict': b'a' * 3000,
                     'org/languagetool/resource/tl/a.info': b'info'})
    jar2 = make_jar({'models/b.bin': b'b' * 5000})
    aff = b'SET UTF-8\n'
    dic = b'2\nfoo\nbar\n' * 300
    base = 'https://example.org/'
    files = {base + 'tl-dict-1.0.jar': jar1, base + 'opennlp-tl-models-1.0.jar': jar2,
             base + 'tl.aff': aff, base + 'tl.dic': dic}
    m = {'version': 1, 'languages': {'tl': [
        source(base + 'tl-dict-1.0.jar', jar1, [('tl/a.dict', 'org/languagetool/resource/tl/a.dict'),
                                                ('tl/a.info', 'org/languagetool/resource/tl/a.info')]),
        source(base + 'opennlp-tl-models-1.0.jar', jar2, [('tl/b.bin', 'models/b.bin')])]}}
    hm = {'commit': 'f' * 40, 'languages': {'tl-PH': 'tl/tl'}, 'notes': {},
          'dictionaries': {'tl/tl': {'aff': hunspell_entry(base + 'tl.aff', aff),
                                     'dic': hunspell_entry(base + 'tl.dic', dic)}}}
    monkeypatch.setattr(dictionaries, 'manifest', lambda: m)
    monkeypatch.setattr(hd, 'manifest', lambda: hm)
    monkeypatch.delenv('LANGTOOL_DICT_PATH', raising=False)
    opener = FakeOpener(files)
    langtool.set_cache_dir(tmp_path / 'cache')
    langtool.set_url_opener(opener)
    yield opener, m, hm
    langtool.set_url_opener(None)
    langtool.set_download_hook(None)
    langtool.set_cache_dir(None)


def cache_files(tmp_path):
    out = []
    for dirpath, dirnames, filenames in os.walk(tmp_path / 'cache'):
        out.extend(os.path.relpath(os.path.join(dirpath, f), tmp_path / 'cache') for f in filenames)
    return sorted(out)


def test_downloads_needed(setup, tmp_path):
    opener, m, hm = setup
    items = langtool.downloads_needed(LANG)
    cd = dictionaries.cache_dir()
    assert items == [
        DownloadItem('https://example.org/tl-dict-1.0.jar', os.path.join(cd, 'jars', 'tl-dict-1.0.jar'),
                     m['languages']['tl'][0]['sha256'], m['languages']['tl'][0]['size'], 'dictionary', 'tl'),
        DownloadItem('https://example.org/opennlp-tl-models-1.0.jar',
                     os.path.join(cd, 'jars', 'opennlp-tl-models-1.0.jar'), m['languages']['tl'][1]['sha256'],
                     m['languages']['tl'][1]['size'], 'opennlp', 'tl')]
    sp = langtool.downloads_needed(LANG, spelling=True)
    assert sp[:2] == items
    assert [(i.kind, i.language, os.path.basename(i.dest)) for i in sp[2:]] == [
        ('hunspell', LANG, 'tl.aff'), ('hunspell', LANG, 'tl.dic')]
    assert langtool.download_size(LANG) == sum(s['size'] for s in m['languages']['tl'])
    assert langtool.download_size(LANG, spelling=True) == langtool.download_size(LANG) + sum(
        e['size'] for e in hm['dictionaries']['tl/tl'].values())
    assert [i.url for i in langtool.downloads_needed()] == [i.url for i in items]
    assert not langtool.is_ready(LANG)
    assert not langtool.is_ready(LANG, spelling=True)
    # nothing was downloaded
    assert opener.opened == []
    assert cache_files(tmp_path) == []

    langtool.download_dictionaries(LANG)
    assert langtool.downloads_needed(LANG) == []
    assert langtool.download_size(LANG) == 0
    assert langtool.is_ready(LANG)
    assert not langtool.is_ready(LANG, spelling=True)
    assert langtool.downloads_needed(LANG, spelling=True) == sp[2:]
    # (the jars are removed after the files have been extracted)
    assert cache_files(tmp_path) == [os.path.join('dictionaries-v1', 'tl', f) for f in ('a.dict', 'a.info', 'b.bin')]
    with open(os.path.join(cd, 'tl', 'b.bin'), 'rb') as f:
        assert f.read() == b'b' * 5000

    langtool.download_dictionaries(LANG, spelling=True)
    assert langtool.downloads_needed(LANG, spelling=True) == []
    assert langtool.is_ready(LANG, spelling=True)
    assert opener.opened == [i.url for i in sp]
    assert opener.closed == 4
    # nothing to download: nothing is opened
    langtool.download_dictionaries(LANG, spelling=True)
    assert len(opener.opened) == 4


def test_is_ready_with_dictionary_path(setup, tmp_path):
    """is_ready() also finds the dictionaries in the dictionary path (as
    the language does when it is used), without extracting them"""
    d = tmp_path / 'dicts' / 'tl'
    d.mkdir(parents=True)
    for name in ('a.dict', 'a.info', 'b.bin'):
        (d / name).write_bytes(b'x')
    assert langtool.is_ready(LANG, dictionary_path=str(tmp_path / 'dicts'))
    assert not langtool.is_ready(LANG)
    jar = tmp_path / 'tl.jar'
    jar.write_bytes(make_jar({'org/languagetool/resource/tl/a.dict': b'x', 'org/languagetool/resource/tl/a.info': b'',
                              'org/languagetool/resource/tl/b.bin': b''}))
    assert langtool.is_ready(LANG, dictionary_path=[str(jar)])
    assert cache_files(tmp_path) == []
    (d / 'b.bin').unlink()
    assert not langtool.is_ready(LANG, dictionary_path=str(tmp_path / 'dicts'))


def test_spelling_unavailable(setup):
    with pytest.raises(langtool.SpellCheckUnavailable):
        langtool.downloads_needed('ja-JP', spelling=True)
    with pytest.raises(langtool.SpellCheckUnavailable):
        langtool.is_ready('ja-JP', spelling=True)


def test_hook(setup):
    opener, m, hm = setup
    events = []
    langtool.set_download_hook(events.append)
    items = langtool.downloads_needed(LANG, spelling=True)
    total = sum(i.size for i in items)
    langtool.download_dictionaries(LANG, spelling=True)
    assert all(isinstance(e, DownloadProgress) for e in events)
    assert {e.item_count for e in events} == {4}
    assert {e.batch_total for e in events} == {total}
    done = 0
    for index, item in enumerate(items):
        evs = [e for e in events if e.item_index == index]
        assert {e.item for e in evs} == {item}
        assert evs[0].state == 'start' and evs[-1].state == 'done'
        assert all(e.state == 'progress' for e in evs[1:-1])
        # (chunks of at most 1000 bytes)
        assert len(evs) - 2 == (item.size + 999) // 1000
        assert evs[0].received == 0 and evs[0].batch_received == done
        received = [e.received for e in evs]
        assert received == sorted(received) and received[-1] == item.size == received[-2]
        assert [e.batch_received - done for e in evs] == received
        done += item.size
    assert events[-1].batch_received == total
    # the events are in the order of the items
    assert [e.item_index for e in events] == sorted(e.item_index for e in events)


def test_implicit_download_calls_hook(tmp_path, monkeypatch):
    """Creating a LanguageTool and checking a text downloads the missing
    dictionaries of the language (with the hook called): a manifest with a
    jar made of the real Tagalog dictionary files, served by a fake
    opener"""
    require_dictionaries('tl')
    monkeypatch.delenv('LANGTOOL_DICT_PATH', raising=False)
    entries = {}
    real = dictionaries.manifest()['languages']['tl']
    for src in real:
        for e in src['files']:
            with open(dictionaries.locate(e['name'], download=False), 'rb') as f:
                entries[e['path']] = f.read()
    jar = make_jar(entries)
    url = 'https://example.org/language-tl.jar'
    m = {'version': 1, 'languages': {'tl': [source(url, jar, [(e['name'], e['path']) for src in real
                                                              for e in src['files']])]}}
    monkeypatch.setattr(dictionaries, 'manifest', lambda: m)
    # (a new Language object: the one of the process may have loaded the dictionaries already)
    monkeypatch.setattr(api, '_languages', {})
    opener = FakeOpener({url: jar}, chunk_size=1 << 16)
    events = []
    langtool.set_url_opener(opener)
    langtool.set_download_hook(events.append)
    try:
        langtool.set_cache_dir(tmp_path)
        assert not langtool.is_ready(LANG)
        tool = langtool.LanguageTool(LANG)
        tool.check('Ito ay isang pangungusap.')
        assert langtool.is_ready(LANG)
    finally:
        langtool.set_url_opener(None)
        langtool.set_download_hook(None)
        langtool.set_cache_dir(None)
    assert opener.opened == [url]
    assert events[0].state == 'start' and events[-1].state == 'done'
    assert events[-1].batch_received == events[-1].batch_total == len(jar)
    assert events[0].item.url == url and events[0].item.language == 'tl'


def leftovers(tmp_path):
    """the temporary files and jars in the cache"""
    return [f for f in cache_files(tmp_path) if os.path.basename(f).startswith('tmp') or f.endswith('.jar')]


def test_hook_aborts(setup, tmp_path):
    """raising DownloadAborted from the hook (in the middle of the second
    item) aborts: the partial file is removed, the first item is kept"""
    opener, m, hm = setup

    def hook(p):
        if p.item_index == 1 and p.state == 'progress' and p.received >= 2000:
            raise DownloadAborted('cancelled')

    langtool.set_download_hook(hook)
    with pytest.raises(DownloadAborted):
        langtool.download_dictionaries(LANG)
    assert cache_files(tmp_path) == [os.path.join('dictionaries-v1', 'tl', f) for f in ('a.dict', 'a.info')]
    assert [i.kind for i in langtool.downloads_needed(LANG)] == ['opennlp']
    # any exception aborts
    langtool.set_download_hook(lambda p: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        langtool.download_dictionaries(LANG)
    assert leftovers(tmp_path) == []
    langtool.set_download_hook(None)
    langtool.download_dictionaries(LANG)
    assert langtool.is_ready(LANG)


def test_abort_event(setup, tmp_path):
    opener, m, hm = setup
    abort = threading.Event()
    abort.set()
    with pytest.raises(DownloadAborted):
        langtool.download_dictionaries(LANG, abort=abort)
    assert cache_files(tmp_path) == []
    assert opener.opened == []
    # set during the download (e.g. by another thread): checked between the chunks
    abort.clear()
    calls = []

    def progress(url, done, total):
        calls.append(done)
        if len(calls) == 2:
            abort.set()

    with pytest.raises(DownloadAborted):
        langtool.download_dictionaries(LANG, progress=progress, abort=abort, spelling=True)
    assert len(calls) == 2
    assert cache_files(tmp_path) == []
    assert len(langtool.downloads_needed(LANG, spelling=True)) == 4


def test_abort_event_hunspell(setup, tmp_path):
    langtool.download_dictionaries(LANG)
    abort = threading.Event()
    langtool.set_download_hook(lambda p: abort.set() if p.state == 'progress' else None)
    with pytest.raises(DownloadAborted):
        langtool.download_dictionaries(LANG, spelling=True, abort=abort)
    assert leftovers(tmp_path) == []
    assert not hd.is_cached(LANG)


def test_size_mismatch(setup, tmp_path):
    opener, m, hm = setup
    url = 'https://example.org/tl.dic'
    data = opener.files[url]
    for bad in (data + b'x', data[:-1]):
        opener.files[url] = bad
        hm['dictionaries']['tl/tl']['dic']['sha256'] = hashlib.sha256(bad).hexdigest()
        with pytest.raises(OSError, match='Size mismatch'):
            hd.download(LANG)
        assert leftovers(tmp_path) == []
        assert not os.path.exists(hd._cached_paths('tl/tl')[1])
    # a checksum mismatch
    opener.files[url] = data[:-1] + b'!'
    with pytest.raises(OSError, match='Checksum mismatch'):
        hd.download(LANG)
    assert leftovers(tmp_path) == []
    assert not os.path.exists(hd._cached_paths('tl/tl')[1])
    # (the .aff was downloaded)
    assert [os.path.basename(i.dest) for i in langtool.downloads_needed(LANG, spelling=True)][-1:] == ['tl.dic']


def test_legacy_progress(setup):
    opener, m, hm = setup
    calls = []
    langtool.download_dictionaries(LANG, progress=lambda url, done, total: calls.append((url, done, total)))
    for src in m['languages']['tl']:
        mine = [c for c in calls if c[0] == src['url']]
        assert [c[1] for c in mine] == [min(1000 * (i + 1), src['size']) for i in range(len(mine))]
        assert {c[2] for c in mine} == {src['size']}
        assert mine[-1][1] == src['size']


def test_opener_used_for_all_downloads(setup, tmp_path, monkeypatch):
    """the opener is used for every download: download_dictionaries(),
    the implicit downloads (dictionaries.locate(), hunspell locate()) and
    download_all()"""
    opener, m, hm = setup
    import urllib.request

    def fail(*args, **kwargs):
        raise AssertionError('urlopen used')

    monkeypatch.setattr(urllib.request, 'urlopen', fail)
    dictionaries.locate('tl/b.bin')
    assert opener.opened == ['https://example.org/tl-dict-1.0.jar', 'https://example.org/opennlp-tl-models-1.0.jar']
    hd.locate(LANG)
    assert opener.opened[2:] == ['https://example.org/tl.aff', 'https://example.org/tl.dic']
    langtool.set_cache_dir(tmp_path / 'cache2')
    hd.download_all()
    dictionaries.download_language('tl')
    langtool.download_dictionaries(spelling=True)
    assert len(opener.opened) == 8
    # without an opener: urllib
    langtool.set_url_opener(None)
    langtool.set_cache_dir(tmp_path / 'cache3')
    with pytest.raises(AssertionError, match='urlopen used'):
        langtool.download_dictionaries(LANG)
    assert leftovers(tmp_path) == []


def test_concurrent_downloads(setup, tmp_path):
    """concurrent downloads of the same files don't corrupt them (the
    download lock)"""
    opener, m, hm = setup
    opener.chunk_size = 100
    errors = []

    def run():
        try:
            langtool.download_dictionaries(LANG, spelling=True)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert langtool.is_ready(LANG, spelling=True)
    assert len(opener.opened) == 4


def test_cli_progress(setup, monkeypatch, capsys):
    from langtool import cli
    assert cli.main(['download', LANG, '--spelling']) == 0
    err = capsys.readouterr().err
    lines = err.splitlines()
    assert len(lines) == 4
    assert lines[0].startswith('[1/4] tl-dict-1.0.jar ')
    assert lines[-1].startswith('[4/4] tl.dic 100% ')
    assert langtool.is_ready(LANG, spelling=True)


def test_no_urllib_import():
    """importing langtool and using a language don't import urllib.request
    (startup time)"""
    code = ('import sys, langtool; langtool.is_ready("en-US"); langtool.downloads_needed("de-DE", spelling=True); '
            'print("urllib.request" in sys.modules)')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, check=True).stdout
    assert out.strip() == 'False'
