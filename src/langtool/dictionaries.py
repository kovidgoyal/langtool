"""Locating and downloading the binary (morfologik) dictionaries.

The dictionaries are too large to be bundled with the package. They are
found in (in order):

1. Paths passed explicitly (``dictionary_path`` argument) or set in the
   ``LANGTOOL_DICT_PATH`` environment variable (os.pathsep separated). Each
   path can be a directory containing the dictionary files (either directly,
   in a ``<lang>/`` sub directory or in the ``org/languagetool/resource/<lang>``
   layout), a LanguageTool installation directory, or a .jar file
   (e.g. ``english-pos-dict-0.6.jar`` or ``language-pl-6.8.jar``).
2. The download cache (the directory set with set_cache_dir() or the
   ``cache_dir`` argument of LanguageTool, else ``LANGTOOL_CACHE_DIR``, else
   the user cache directory).
3. If not found and downloading is allowed, the jars listed in
   dictionaries.json are downloaded from Maven Central into the cache,
   checksums verified and the dictionary files extracted.
"""

import os
import sys
import threading
from collections import namedtuple
from functools import lru_cache

# (json, zipfile, shutil, tempfile and hashlib are imported when needed: importing them takes about half of the
# import time of the package)

_lock = threading.RLock()


class DictionaryNotFound(Exception):
    pass


class DownloadAborted(Exception):
    """A download was aborted (by the abort event of
    download_dictionaries() or by a download hook raising it)."""


# (namedtuple rather than typing.NamedTuple: importing typing takes a few milliseconds)
class DownloadItem(namedtuple('DownloadItem', 'url dest sha256 size kind language')):
    """A file that is downloaded into the cache:

    - url
    - dest: the path of the file in the cache (for the jars of the
      dictionaries: the jar, from which the dictionary files are extracted,
      after which the jar is removed)
    - sha256
    - size: the size in bytes, from the manifest
    - kind: 'dictionary' (the tagger/synthesizer/speller dictionaries and
      other data of LanguageTool), 'opennlp' (the OpenNLP models of
      English), 'ipadic' (the Japanese dictionary) or 'hunspell' (a file of
      a Hunspell dictionary for spell checking)
    - language: the language code the item is for (the code of
      dictionaries.json, e.g. 'en', for the dictionaries, the requested
      code, e.g. 'en-US', for the Hunspell dictionaries)
    """
    __slots__ = ()


class DownloadProgress(namedtuple('DownloadProgress',
                                  'item item_index item_count received batch_received batch_total state')):
    """The progress of a download, passed to the hook set with
    set_download_hook():

    - item: the DownloadItem
    - item_index, item_count: the index of the item in the batch (the files
      downloaded by one call of download_dictionaries(), or downloaded
      implicitly when a language needs them) and the number of items
    - received: the bytes of the item received so far
    - batch_received: the bytes of the whole batch received so far
    - batch_total: the total size of the batch (from the manifests)
    - state: 'start' (before the first byte of the item), 'progress' (after
      each chunk) or 'done' (the item was downloaded, verified and
      installed)
    """
    __slots__ = ()


_download_hook = None
_url_opener = None


def set_download_hook(hook):
    """Set a function called with a DownloadProgress for every download
    (process-wide; None removes it), including the downloads made
    implicitly when a LanguageTool is created or a text is checked. It is
    called in the thread that downloads. An exception raised by the hook
    (DownloadAborted, preferably) aborts the download: the partially
    downloaded file is removed and the exception propagates to the caller
    of the function that downloads (e.g. LanguageTool() or check()).

    The hook is called while the download lock is held: it must not wait
    for another thread that downloads (is_ready(), downloads_needed() and
    download_size() don't take the lock)."""
    global _download_hook
    _download_hook = hook


def set_url_opener(opener):
    """Set the function used to open the URLs of all downloads
    (process-wide; None restores the default, urllib.request.urlopen with
    a timeout of 60 s): opener(url) returns a file-like object with a
    read(n) method (close() and the context manager protocol are used if
    it has them, and the Content-Length of its headers attribute, if any,
    for the total of the legacy progress callback when the size is not
    known)."""
    global _url_opener
    _url_opener = opener


def _open_url(url):
    if _url_opener is not None:
        return _url_opener(url)
    import urllib.request
    return urllib.request.urlopen(url, timeout=60)


@lru_cache()
def manifest():
    import json
    from . import resources
    with open(resources.path('dictionaries.json'), encoding='utf-8') as f:
        return json.load(f)


_cache_root = None


def set_cache_dir(path):
    """Set the directory where all downloaded resources are cached (the
    tagger/synthesizer/speller dictionaries and the Hunspell dictionaries
    for spell checking). This is a process-wide setting; None restores the
    default (LANGTOOL_CACHE_DIR or the user cache directory)."""
    global _cache_root
    _cache_root = os.path.abspath(os.fspath(path)) if path is not None else None


def cache_root():
    """The base directory of the download cache: the directory set with
    set_cache_dir() (or LanguageTool(cache_dir=...)), else the
    LANGTOOL_CACHE_DIR environment variable, else the user cache directory
    (~/.cache/langtool on Linux)."""
    if _cache_root is not None:
        return _cache_root
    d = os.environ.get('LANGTOOL_CACHE_DIR')
    if not d:
        if sys.platform == 'win32':
            base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            d = os.path.join(base, 'langtool', 'cache')
        elif sys.platform == 'darwin':
            d = os.path.join(os.path.expanduser('~/Library/Caches'), 'langtool')
        else:
            d = os.path.join(os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache'), 'langtool')
    return d


def cache_dir():
    """The cache directory of the (morfologik etc.) dictionaries of the
    manifest, below cache_root()."""
    return os.path.join(cache_root(), 'dictionaries-v%d' % manifest()['version'])


def join_name(base, name):
    """os.path.join for a relative name with / separators (e.g.
    en/english.dict): the native separators on Windows."""
    return os.path.join(base, *name.split('/'))


def required_files(lang):
    """The dictionary related files (relative names like en/english.dict) for a
    language code (e.g. 'en')."""
    out = []
    for src in manifest()['languages'].get(lang, ()):
        for e in src['files']:
            out.append(e['name'])
    return out


def _search_paths(extra):
    paths = []
    if extra:
        if isinstance(extra, (str, os.PathLike)):
            extra = [extra]
        paths.extend(os.fspath(p) for p in extra)
    env = os.environ.get('LANGTOOL_DICT_PATH')
    if env:
        paths.extend(p for p in env.split(os.pathsep) if p)
    return paths


@lru_cache()
def _manifest_jar_paths(name):
    """The paths in the jars of the manifest for the dictionary file name
    (e.g. el/analysis.dict is org/ioperm/morphology/el/analysis.dict in the
    morphology-el jar)"""
    lang = name.split('/', 1)[0]
    return tuple(e['path'] for src in manifest()['languages'].get(lang, ()) for e in src['files']
                 if e['name'] == name)


def _find_in_jar(jar, name):
    import zipfile
    try:
        with zipfile.ZipFile(jar) as z:
            for cand in ('org/languagetool/resource/' + name, name) + _manifest_jar_paths(name):
                try:
                    z.getinfo(cand)
                except KeyError:
                    continue
                return cand
    except (OSError, zipfile.BadZipFile):
        pass
    return None


def _extract_from_jar(jar, entry, dest):
    import shutil
    import tempfile
    import zipfile
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with zipfile.ZipFile(jar) as z, z.open(entry) as src:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest))
        with os.fdopen(fd, 'wb') as out:
            shutil.copyfileobj(src, out)
        os.replace(tmp, dest)


def _locate_in_path(base, name, extract=True):
    """Return a filesystem path for the dictionary file name (e.g.
    en/english.dict) in the search path base, extracting it from a jar into
    the cache if necessary (with extract=False: the path of the jar)."""
    lang, fname = name.split('/', 1) if '/' in name else ('', name)
    if os.path.isfile(base):
        if base.endswith(('.jar', '.zip')):
            entry = _find_in_jar(base, name)
            if entry is not None:
                if not extract:
                    return base
                dest = join_name(os.path.join(cache_dir(), 'extracted'), name)
                if not os.path.exists(dest) or os.path.getmtime(dest) < os.path.getmtime(base):
                    _extract_from_jar(base, entry, dest)
                return dest
        return None
    if not os.path.isdir(base):
        return None
    for cand in (join_name(base, name), os.path.join(base, fname),
                 join_name(os.path.join(base, 'org', 'languagetool', 'resource'), name)):
        if os.path.isfile(cand):
            return cand
    # jars in the directory or a LanguageTool installation
    for sub in ('', 'libs'):
        d = os.path.join(base, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.jar'):
                r = _locate_in_path(os.path.join(d, f), name, extract)
                if r is not None:
                    return r
    return None


def locate(name, dictionary_path=None, download=True):
    """Return the path of the dictionary file name, e.g. 'en/english.dict'.
    The corresponding .info file is guaranteed to be next to it."""
    is_dict = name.endswith('.dict')
    info = name[:-5] + '.info' if is_dict else None
    for base in _search_paths(dictionary_path):
        p = _locate_in_path(base, name)
        if p is not None:
            if info is not None:
                ip = os.path.splitext(p)[0] + '.info'
                if not os.path.exists(ip):
                    ip2 = _locate_in_path(base, info)
                    if ip2 is None:
                        continue
                    if os.path.dirname(ip2) != os.path.dirname(p):
                        # make sure the .info is next to the .dict
                        import shutil
                        dest = join_name(os.path.join(cache_dir(), 'extracted'), name)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(p, dest)
                        shutil.copy2(ip2, os.path.splitext(dest)[0] + '.info')
                        p = dest
            return p
    lang = name.split('/', 1)[0]
    p = join_name(cache_dir(), name)
    if os.path.exists(p):
        return p
    if download:
        download_language(lang)
        if os.path.exists(p):
            return p
    raise DictionaryNotFound(
        'The dictionary %s was not found. Either allow downloading it or specify its location with the '
        'dictionary_path argument or the LANGTOOL_DICT_PATH environment variable.' % name)


def is_available(lang, dictionary_path=None):
    for name in required_files(lang):
        try:
            locate(name, dictionary_path, download=False)
        except DictionaryNotFound:
            return False
    return True


def download_file(url, dest, expected_sha256, progress=None, size=None, abort=None, _chunk=None):
    """Download url to dest, verifying its sha256 (and its size, if given).
    The file is written to a temporary file next to dest, which replaces
    dest when complete and verified; an error or abort removes it.
    progress(url, done, total) is called after each chunk; abort (a
    threading.Event) is checked between the chunks (DownloadAborted is
    raised when it is set)."""
    import hashlib
    import tempfile
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest))
    h = hashlib.sha256()
    try:
        with os.fdopen(fd, 'wb') as out:
            if abort is not None and abort.is_set():
                raise DownloadAborted('Download of %s aborted' % url)
            r = _open_url(url)
            try:
                total = size
                if total is None:
                    headers = getattr(r, 'headers', None)
                    total = int((headers.get('Content-Length') if headers is not None else None) or 0)
                done = 0
                while True:
                    if abort is not None and abort.is_set():
                        raise DownloadAborted('Download of %s aborted' % url)
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    h.update(chunk)
                    out.write(chunk)
                    done += len(chunk)
                    if size is not None and done > size:
                        raise OSError('Size mismatch for %s: more than %d bytes' % (url, size))
                    if progress is not None:
                        progress(url, done, total)
                    if _chunk is not None:
                        _chunk(done, len(chunk))
            finally:
                close = getattr(r, 'close', None)
                if close is not None:
                    close()
        if size is not None and done != size:
            raise OSError('Size mismatch for %s: %d bytes instead of %d' % (url, done, size))
        if h.hexdigest() != expected_sha256:
            raise OSError('Checksum mismatch for %s' % url)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def run_batch(items, progress=None, abort=None, install=None):
    """Download the DownloadItems items (a batch) with download_file(),
    reporting the progress to the download hook and to the legacy
    progress(url, done, total) callback. install(item) is called after an
    item was downloaded (e.g. to extract the files of a jar), before its
    'done' report. The caller holds the download lock."""
    items = list(items)
    count = len(items)
    batch_total = sum(item.size for item in items)
    batch_received = 0
    for index, item in enumerate(items):
        hook = _download_hook
        if hook is not None:
            hook(DownloadProgress(item, index, count, 0, batch_received, batch_total, 'start'))
        chunk = None
        if hook is not None:
            def report(done, n, item=item, index=index, base=batch_received):
                hook(DownloadProgress(item, index, count, done, base + done, batch_total, 'progress'))
            chunk = report
        download_file(item.url, item.dest, item.sha256, progress, item.size, abort, chunk)
        if install is not None:
            install(item)
        batch_received += item.size
        if hook is not None:
            hook(DownloadProgress(item, index, count, item.size, batch_received, batch_total, 'done'))


def _source_kind(src):
    name = src['url'].rsplit('/', 1)[1]
    if name.startswith('opennlp-'):
        return 'opennlp'
    if 'ipadic' in name:
        return 'ipadic'
    return 'dictionary'


def _jar_path(src):
    return os.path.join(cache_dir(), 'jars', src['url'].rsplit('/', 1)[1])


def language_downloads(lang):
    """The DownloadItems (jars) that download_language(lang) would download
    now: those with dictionary files missing in the cache (the jars are
    removed after the files have been extracted). Nothing is downloaded,
    cheap (only checks that files exist)."""
    cd = cache_dir()
    out = []
    for src in manifest()['languages'].get(lang, ()):
        if all(os.path.exists(join_name(cd, e['name'])) for e in src['files']):
            continue
        out.append(DownloadItem(src['url'], _jar_path(src), src['sha256'], src['size'], _source_kind(src), lang))
    return out


def _sources_by_url():
    return {src['url']: src for sources in manifest()['languages'].values() for src in sources}


def install_item(item):
    """Install a downloaded item: extract the dictionary files of a jar
    and remove the jar (nothing for the other kinds of items)."""
    if item.kind == 'hunspell':
        return
    src = _sources_by_url().get(item.url)
    if src is None:
        return
    cd = cache_dir()
    for e in src['files']:
        _extract_from_jar(item.dest, e['path'], join_name(cd, e['name']))
    try:
        os.remove(item.dest)
    except OSError:
        pass


def download_items(items, progress=None, abort=None):
    """Download the DownloadItems items as one batch (and install them)."""
    with _lock:
        run_batch(items, progress, abort, install_item)


def download_language(lang, progress=None, abort=None):
    """Download the dictionaries for the language code lang (e.g. 'en') into
    the cache directory."""
    with _lock:
        run_batch(language_downloads(lang), progress, abort, install_item)


def is_present(lang, dictionary_path=None):
    """Whether all the dictionary files of the language code lang (e.g.
    'en') are found (in the search paths or the cache) without
    downloading anything: then nothing is downloaded when the language is
    used. Cheap: doesn't extract files from jars."""
    for name in required_files(lang):
        if not _is_found(name, dictionary_path):
            return False
    return True


def _is_found(name, dictionary_path=None):
    """locate(name, dictionary_path, download=False) without its side
    effects (extracting files from jars)"""
    is_dict = name.endswith('.dict')
    info = name[:-5] + '.info' if is_dict else None
    for base in _search_paths(dictionary_path):
        if _locate_in_path(base, name, extract=False) is not None:
            if info is None or _locate_in_path(base, info, extract=False) is not None:
                return True
    return os.path.exists(join_name(cache_dir(), name))


def main(argv=None):
    """Command line entry point: download the dictionaries for the given
    languages (or all)."""
    import argparse
    p = argparse.ArgumentParser(description='Download LanguageTool dictionaries')
    p.add_argument('languages', nargs='*', help='language codes, e.g. en de (default: all)')
    p.add_argument('--cache-dir', help='the directory for downloaded resources')
    args = p.parse_args(argv)
    if args.cache_dir:
        set_cache_dir(args.cache_dir)
    langs = args.languages or sorted(manifest()['languages'])
    for lang in langs:
        code = lang.split('-')[0]
        print('Downloading dictionaries for', code, '...')
        download_language(code)
    print('Dictionaries are in', cache_dir())


if __name__ == '__main__':
    main()


def dependency_files(language):
    """The paths of the (downloadable) dictionary files of a language as
    they are found now (where a missing file would be downloaded to): the
    dependencies of data derived from them that is cached on disk (see
    langtool.diskcache). Nothing is downloaded."""
    from .extensions import resource_language
    out = []
    for name in required_files(resource_language(language).split('-')[0]):
        try:
            out.append(locate(name, language.dictionary_path, False))
        except DictionaryNotFound:
            out.append(join_name(cache_dir(), name))
    return out
