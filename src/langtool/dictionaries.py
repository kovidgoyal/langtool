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
from functools import lru_cache

# (json, zipfile, shutil, tempfile and hashlib are imported when needed: importing them takes about half of the
# import time of the package)

_lock = threading.RLock()


class DictionaryNotFound(Exception):
    pass


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


def _locate_in_path(base, name):
    """Return a filesystem path for the dictionary file name (e.g.
    en/english.dict) in the search path base, extracting it from a jar into
    the cache if necessary."""
    lang, fname = name.split('/', 1) if '/' in name else ('', name)
    if os.path.isfile(base):
        if base.endswith(('.jar', '.zip')):
            entry = _find_in_jar(base, name)
            if entry is not None:
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
                r = _locate_in_path(os.path.join(d, f), name)
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


def download_file(url, dest, expected_sha256, progress=None):
    import hashlib
    import tempfile
    import urllib.request
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest))
    h = hashlib.sha256()
    try:
        with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(url, timeout=60) as r:
            total = int(r.headers.get('Content-Length') or 0)
            done = 0
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                h.update(chunk)
                out.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(url, done, total)
        if h.hexdigest() != expected_sha256:
            raise OSError('Checksum mismatch for %s' % url)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def download_language(lang, progress=None):
    """Download the dictionaries for the language code lang (e.g. 'en') into
    the cache directory."""
    with _lock:
        sources = manifest()['languages'].get(lang)
        if not sources:
            return
        cd = cache_dir()
        for src in sources:
            files = src['files']
            if all(os.path.exists(join_name(cd, e['name'])) for e in files):
                continue
            jar = os.path.join(cd, 'jars', src['url'].rsplit('/', 1)[1])
            if not os.path.exists(jar):
                download_file(src['url'], jar, src['sha256'], progress)
            for e in files:
                _extract_from_jar(jar, e['path'], join_name(cd, e['name']))
            try:
                os.remove(jar)
            except OSError:
                pass


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
