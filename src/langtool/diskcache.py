"""Persistent on-disk cache of expensive derived data.

Loading a language means parsing thousands of XML rules, translating and
compiling regular expressions and building lookup tables from data files.
The results only depend on the package (code and data) and on a few files
outside of it, so they are cached on disk (with pickle) and loaded from there
by later processes, which is several times faster.

Location: the directory set with ``set_disk_cache(directory=...)``, else
the ``LANGTOOL_DISK_CACHE_DIR`` environment variable, else the ``derived``
directory of the cache directory (the directory set with
``langtool.set_cache_dir()``, else ``LANGTOOL_CACHE_DIR``, else the user
cache directory, e.g. ``~/.cache/langtool/derived``). Below it there is one directory
per *package fingerprint*: a hash of the langtool version, the Python
version, whether the C extension is used, the versions of the ``regex`` and
``lxml`` modules and the size and modification time of every file of the
package (code and data). Any change of these selects a new directory (the
directories that were not used for a week are removed). An entry is
additionally keyed on its parameters (e.g. the language code) and records
the size and modification time of the files outside of the package that it
was built from (e.g. downloaded dictionaries); it is rebuilt when they
change.

Robustness: entries are written to a temporary file and renamed (atomic,
so concurrent processes never see partial entries; the last writer wins),
are compressed (zstd or zlib) and have a checksum, and any problem reading an entry (missing, stale,
truncated, corrupt, written by an incompatible version, unreadable
directory) silently falls back to building the data (and replacing the
entry if possible). Errors writing are ignored too. Problems are logged to
the ``langtool.diskcache`` logger (debug level).

Disabling: set the environment variable ``LANGTOOL_DISK_CACHE=0`` (also
``off``, ``no`` or ``false``) or call ``langtool.set_disk_cache(False)``.
"""

import gc
import hashlib
import io
import logging
import os
import pickle
import struct
import sys
import threading
import time
import zlib

log = logging.getLogger(__name__)

# bump when the format of the files or of the cached objects changes in a way
# that the package fingerprint does not capture
FORMAT_VERSION = 1
_MAGIC = b'LTDC%04d' % FORMAT_VERSION
_HEADER = struct.Struct('<8sQQI')  # magic, header length, payload length, payload crc32
_BUILTIN_FUNCTION = type(len)
_FUNCTION = type(lambda: None)
_PROTOCOL = 5 if pickle.HIGHEST_PROTOCOL >= 5 else pickle.HIGHEST_PROTOCOL
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_UNUSED_DIR_MAX_AGE = 7 * 24 * 3600
_TMP_MAX_AGE = 24 * 3600

_lock = threading.RLock()
_enabled = None  # None: the environment variable decides
_directory = None
_fingerprint = None
_dir_checked = set()
_dir_used = set()
_local = threading.local()

# counters, for tests and diagnostics: kind -> {'hit': n, 'miss': n, 'write': n, 'error': n}
stats = {}


def _env_enabled():
    v = os.environ.get('LANGTOOL_DISK_CACHE', '').strip().lower()
    return v not in ('0', 'off', 'no', 'false')


def set_disk_cache(enabled=True, directory=None):
    """Enable or disable the persistent cache of derived data (see the
    module documentation) for this process, optionally with a directory to
    use instead of the default (LANGTOOL_DISK_CACHE_DIR, else
    ``<cache dir>/derived``). enabled=None
    restores the default (enabled unless the LANGTOOL_DISK_CACHE environment
    variable is 0/off/no/false)."""
    global _enabled, _directory
    with _lock:
        _enabled = enabled if enabled is None else bool(enabled)
        _directory = os.path.abspath(os.fspath(directory)) if directory is not None else None


def is_enabled():
    """Whether the persistent cache is used."""
    e = _enabled
    return _env_enabled() if e is None else e


def base_directory():
    """The directory of the persistent cache (the entries are in sub
    directories named after the package fingerprint)."""
    d = _directory
    if d is not None:
        return d
    d = os.environ.get('LANGTOOL_DISK_CACHE_DIR')
    if d:
        return os.path.abspath(d)
    from .dictionaries import cache_root
    return os.path.join(cache_root(), 'derived')


def directory():
    """The directory of the entries for this version of the package."""
    return os.path.join(base_directory(), package_fingerprint()[:20])


def clear():
    """Remove all entries of the persistent cache (of all package
    versions)."""
    import shutil
    global _regex_store
    base = base_directory()
    with _regex_lock:
        mine = _regex_store
        _regex_store = None
    if mine:
        mine[1].close()
    with _lock:
        _dir_checked.clear()
        _dir_used.clear()
        try:
            names = os.listdir(base)
        except OSError:
            return
        for n in names:
            p = os.path.join(base, n)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)


def _walk_stats(top):
    out = []
    stack = [top]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            continue
        with it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=True):
                        if e.name != '__pycache__':
                            stack.append(e.path)
                        continue
                    if e.name.endswith(('.pyc', '.pyo')):
                        continue
                    st = e.stat()
                except OSError:
                    continue
                out.append((os.path.relpath(e.path, top), st.st_size, st.st_mtime_ns))
    out.sort()
    return out


def package_fingerprint():
    """A hash of everything the cached data depends on inside the package
    (code and data files, versions, interpreter, C extension or not)."""
    global _fingerprint
    fp = _fingerprint
    if fp is None:
        from . import _base
        try:
            import regex
            regex_version = (regex.__version__, getattr(regex._regex, 'MAGIC', None))
        except Exception:  # pragma: no cover
            regex_version = None
        try:
            from lxml import etree
            lxml_version = etree.LXML_VERSION, etree.LIBXML_VERSION
        except Exception:  # pragma: no cover
            lxml_version = None
        version = getattr(sys.modules.get(__package__), '__version__', None)
        h = hashlib.sha256()
        h.update(repr((FORMAT_VERSION, version, sys.version, sys.implementation.cache_tag, sys.platform,
                       sys.maxunicode, _PROTOCOL, _base.speedups is not None, regex_version, lxml_version,
                       _PACKAGE_DIR)).encode('utf-8', 'surrogatepass'))
        h.update(repr(_walk_stats(_PACKAGE_DIR)).encode('utf-8', 'surrogatepass'))
        fp = _fingerprint = h.hexdigest()
    return fp


def _file_stat(path):
    try:
        st = os.stat(path)
        return (st.st_size, st.st_mtime_ns)
    except OSError:
        return None


def _is_package_file(path):
    try:
        return os.path.commonpath([os.path.abspath(path), _PACKAGE_DIR]) == _PACKAGE_DIR
    except ValueError:
        return False


def note_dependency(path):
    """Record that the data being built (by load_or_build(), in this thread)
    depends on the file path. Files of the package need not be recorded
    (they are covered by the package fingerprint)."""
    stack = getattr(_local, 'deps', None)
    if stack and path is not None:
        path = os.path.abspath(os.fspath(path))
        if not _is_package_file(path):
            for deps in stack:
                deps.add(path)


def _count(kind, what):
    with _lock:
        d = stats.setdefault(kind, {'hit': 0, 'miss': 0, 'write': 0, 'error': 0})
        d[what] += 1


def _default_codec():
    """zstd (Python 3.14+, compressing and decompressing are 3-4 times
    faster) or zlib"""
    try:
        from compression import zstd
    except ImportError:  # pragma: no cover
        return 'zlib'
    return 'zstd' if zstd.decompress else 'zlib'


def _codec(name):
    """(compress, decompress) of a codec"""
    if name == 'zstd':
        from compression import zstd
        return (lambda b: zstd.compress(b, 1)), zstd.decompress
    if name == 'zlib':
        return (lambda b: zlib.compress(b, 1)), zlib.decompress
    raise ValueError('unknown codec %r' % name)


def _external(pid):
    """(unpickling) an object that was pickled by reference, see
    load_or_build()"""
    resolve = getattr(_local, 'resolve', None)
    if resolve is None:
        raise pickle.UnpicklingError('unexpected external reference %r' % (pid,))
    return resolve(pid)


def _entry_path(kind, key):
    h = hashlib.sha256(repr((kind, key)).encode('utf-8', 'surrogatepass')).hexdigest()[:24]
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in kind)
    return os.path.join(directory(), '%s-%s.pkl' % (safe, h))


def _read(path, kind, key, resolve):
    """the cached value, or raises (any exception: the entry can't be used)"""
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < _HEADER.size:
        raise ValueError('truncated')
    magic, hlen, plen, crc = _HEADER.unpack_from(data)
    if magic != _MAGIC:
        raise ValueError('other format')
    start = _HEADER.size + hlen
    if len(data) != start + plen:
        raise ValueError('truncated')
    header = pickle.loads(data[_HEADER.size:start])
    if header.get('kind') != kind or header.get('key') != key:
        raise ValueError('other key')
    for p, st in header.get('deps', ()):
        if _file_stat(p) != st:
            raise _Stale('%s changed' % p)
    payload = memoryview(data)[start:]
    if zlib.crc32(payload) != crc:
        raise ValueError('checksum mismatch')
    del data
    codec = header.get('codec')
    if codec is not None:
        payload = _codec(codec)[1](payload)
    outer = getattr(_local, 'resolve', None)
    _local.resolve = resolve
    _gc_pause()
    try:
        return pickle.loads(payload)
    finally:
        _gc_resume()
        _local.resolve = outer


_gc_state = [0, False]  # number of loads in progress, whether the collector was enabled before


def _gc_pause():
    """disable the garbage collector while unpickling (which creates many
    objects, the collections would make it several times slower); the
    first of concurrent loads disables it, the last restores the state"""
    with _lock:
        if _gc_state[0] == 0:
            _gc_state[1] = gc.isenabled()
            gc.disable()
        _gc_state[0] += 1


def _gc_resume():
    with _lock:
        _gc_state[0] -= 1
        if _gc_state[0] == 0 and _gc_state[1]:
            gc.enable()


class _Stale(Exception):
    pass


class Uncacheable(Exception):
    """Raised by the persist function of load_or_build() (or by pickling)
    when the data can't be cached; it is then just returned."""


class Reduced(tuple):
    """a value that the persist function of load_or_build() can return:
    the reduce tuple (callable, args) to pickle the object with"""


_slot_setters = {}


def uses_slots_reduced(cls):
    """whether instances of the class are pickled with slots_reduced(): the
    classes with __slots__ defined in Python (not those with C members,
    which have a __getstate__)"""
    if '__getstate__' in cls.__dict__ or any('__getstate__' in vars(k) for k in cls.__mro__[1:-1]
                                              if k.__module__ not in ('builtins',)):
        return False
    return any('__slots__' in vars(k) for k in cls.__mro__[:-1])


def slots_reduced(obj):
    """a Reduced for an object of a class with slots (and maybe an instance
    dict): faster to pickle and unpickle than the default (which builds a
    dict of the slots), with fewer temporary objects (which fragment the
    memory)"""
    cls = type(obj)
    names = _slot_names(cls)
    vals = []
    for n in names:
        try:
            vals.append(getattr(obj, n))
        except AttributeError:
            vals.append(_Unset)
    return Reduced((_restore_slots, (cls, tuple(vals), getattr(obj, '__dict__', None) or None)))


class _Unset:
    """(a slot without value)"""


def _slot_names(cls):
    r = _slot_setters.get(cls)
    if r is None:
        import copyreg
        names = tuple(copyreg._slotnames(cls))
        r = _slot_setters[cls] = (names, tuple(getattr(cls, n).__set__ for n in names))
    return r[0]


def _restore_slots(cls, vals, d):
    r = _slot_setters.get(cls)
    if r is None:
        _slot_names(cls)
        r = _slot_setters[cls]
    obj = cls.__new__(cls)
    for setter, v in zip(r[1], vals):
        if v is not _Unset:
            setter(obj, v)
    if d:
        obj.__dict__.update(d)
    return obj


class _Pickler(pickle.Pickler):

    def __init__(self, f, persist):
        super().__init__(f, _PROTOCOL)
        self._persist = persist

    def reducer_override(self, obj):
        # (not called for None, booleans and exact ints, floats, strings, bytes, lists, tuples, dicts and sets)
        if obj is _external or obj is _restore_slots:
            return NotImplemented  # (the callables of the reduce tuples: pickled by name)
        pid = self._persist(obj)
        if pid is None:
            return NotImplemented
        if type(pid) is Reduced:
            return tuple(pid)
        return _external, (pid,)


def _pickler(f, persist):
    if persist is None:
        return pickle.Pickler(f, _PROTOCOL)
    return _Pickler(f, persist)


def _cleanup(base, current):
    """remove the old fingerprint directories and stale temporary files"""
    now = time.time()
    try:
        names = os.listdir(base)
    except OSError:
        return
    for n in names:
        p = os.path.join(base, n)
        if n == current or not os.path.isdir(p):
            continue
        try:
            stamp = os.path.getmtime(os.path.join(p, 'last-used'))
        except OSError:
            stamp = 0
            try:
                stamp = os.path.getmtime(p)
            except OSError:
                pass
        if now - stamp > _UNUSED_DIR_MAX_AGE:
            import shutil
            shutil.rmtree(p, ignore_errors=True)


def _mark_used(d):
    """touch the last-used file of the directory (at most once a day; the
    directories that were not used for a week are removed by other versions
    of the package)"""
    if d in _dir_used:
        return
    _dir_used.add(d)
    stamp = os.path.join(d, 'last-used')
    try:
        if time.time() - os.path.getmtime(stamp) < 24 * 3600:
            return
    except OSError:
        pass
    try:
        with open(stamp, 'w'):
            pass
    except OSError:
        pass


def _prepare_dir(d):
    """create the directory (and once per process: mark it as used, remove
    old directories and stale temporary files)"""
    os.makedirs(d, exist_ok=True)
    if d in _dir_checked:
        return
    _dir_checked.add(d)
    _dir_used.discard(d)
    _mark_used(d)
    _cleanup(os.path.dirname(d), os.path.basename(d))
    now = time.time()
    for n in os.listdir(d):
        if n.startswith('.tmp-'):
            p = os.path.join(d, n)
            try:
                if now - os.path.getmtime(p) > _TMP_MAX_AGE:
                    os.unlink(p)
            except OSError:
                pass


def _write(path, kind, key, deps, value, persist):
    buf = io.BytesIO()
    _pickler(buf, persist).dump(value)
    # (level 1: 3-5 times smaller, decompressing takes about 1 (zstd) or 3 (zlib) ms per MB)
    codec = _default_codec()
    payload = _codec(codec)[0](buf.getbuffer())
    del buf
    header = pickle.dumps({'kind': kind, 'key': key, 'deps': deps, 'created': time.time(), 'codec': codec},
                          _PROTOCOL)
    d = os.path.dirname(path)
    with _lock:
        _prepare_dir(d)
    # (not tempfile.mkstemp(): the file gets the permissions of normal files, which allows sharing the cache)
    tmp = os.path.join(d, '.tmp-%d-%s' % (os.getpid(), os.urandom(8).hex()))
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o666)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(_HEADER.pack(_MAGIC, len(header), len(payload), zlib.crc32(payload)))
            f.write(header)
            f.write(payload)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_or_build(kind, key, build, persist=None, resolve=None, deps=()):
    """The value built by build(), from the persistent cache if possible.

    kind: a name for the kind of data (part of the file name); key: the
    parameters that the value depends on besides the package (repr()-able
    builtin values, e.g. a language code); build: a function returning the
    value; deps: files outside the package that the value depends on (the
    files noted with note_dependency() during the build are added).
    persist/resolve: for objects that must not be pickled by value (e.g.
    the Language): persist(obj) returns None (pickle by value) or an id
    (a picklable value) of the object that resolve(id) returns when loading
    (it is called once per object). persist is not called for None,
    booleans and exact instances of int, float, str, bytes, list, tuple,
    dict, set and frozenset. persist can also return a Reduced (a reduce
    tuple to pickle the object with) and raise Uncacheable (the value is
    then not cached).

    The value must not be changed before it is stored: it is stored right
    after build() (in this thread)."""
    if not is_enabled():
        return build()
    try:
        path = _entry_path(kind, key)
    except Exception as e:
        log.debug('disk cache unavailable: %s', e)
        return build()
    try:
        value = _read(path, kind, key, resolve)
        _count(kind, 'hit')
        _mark_used(os.path.dirname(path))
        return value
    except FileNotFoundError:
        pass
    except Exception as e:
        log.debug('disk cache entry %s not used: %r', path, e)
        if not isinstance(e, _Stale):
            _count(kind, 'error')
    _count(kind, 'miss')
    stack = getattr(_local, 'deps', None)
    if stack is None:
        stack = _local.deps = []
    noted = set(os.path.abspath(os.fspath(p)) for p in deps)
    stack.append(noted)
    try:
        value = build()
    finally:
        # (the builds are nested: the last one is this one; not stack.remove(), which compares the sets by value)
        stack.pop()
    for outer in stack:
        outer.update(noted)
    try:
        _write(path, kind, key, sorted((p, _file_stat(p)) for p in noted), value, persist)
        _count(kind, 'write')
        if len(_regex_new) >= 200:
            flush_regex_store()
    except Uncacheable as e:
        log.debug('not cached (%s): %s', kind, e)
    except Exception as e:
        _count(kind, 'error')
        log.debug('disk cache entry %s not written: %r', path, e)
    return value


def function_key(f):
    """A name ('module:qualname') for a function of the package that is
    reachable by its name (e.g. a module level function or a method of a
    module level class), usable in the key of an entry; None for other
    functions (lambdas, closures, functions outside the package)."""
    if f is None:
        return 'None'
    mod = getattr(f, '__module__', None)
    qn = getattr(f, '__qualname__', None)
    if not mod or not qn or '<' in qn or not (mod == __package__ or mod.startswith(__package__ + '.')):
        return None
    obj = sys.modules.get(mod)
    for part in qn.split('.'):
        obj = getattr(obj, part, None)
    return '%s:%s' % (mod, qn) if obj is f else None


def language_key(language):
    """The code of the language if data derived from it (e.g. its rules)
    can be cached: if its definition is part of the package (languages added
    or replaced with languages.register_language() are not cached, their
    definitions and code are not covered by the package fingerprint;
    changing the definitions of the package in place requires disabling the
    cache). None otherwise."""
    from .languages import is_builtin
    return language.code if is_builtin(language) else None


def _plain_types():
    import array
    import collections
    return (array.array, bytearray, collections.OrderedDict, collections.defaultdict, complex, range)


def cached(kind, key, build, deps=(), types=()):
    """load_or_build() for plain data: the value must consist of builtin
    values (numbers, strings, containers, array.array) and instances of the
    given classes (pickled by value); if it contains other objects it is
    not cached."""
    allowed = frozenset(_plain_types())
    by_slots = frozenset(t for t in types if uses_slots_reduced(t))
    allowed |= frozenset(types) - by_slots

    def persist(obj):
        t = type(obj)
        if t in by_slots:
            return slots_reduced(obj)
        if t in allowed or t is type or t is _BUILTIN_FUNCTION:
            return None  # (classes and builtin functions are pickled by name)
        if t is _FUNCTION and function_key(obj) is not None:
            return None  # (a function of the package: pickled by name)
        raise Uncacheable('%s: unexpected %s' % (kind, t.__qualname__))
    return load_or_build(kind, key, build, persist=persist, deps=deps)


# --- the store of compiled regular expressions (used by jregex.compile) ---
#
# Compiling a regular expression with the regex module takes 0.2-3 ms (its
# parser is written in Python) while unpickling the compiled expression takes
# a few microseconds. The compiled expressions of jregex.compile() (keyed on
# the Java pattern and the flags) are stored in one file: an index (hash of
# the key -> offset, length and checksum of the entry) and the entries (the
# pickled key and compiled expression). A process loads the index (on the
# first compilation) and reads the entries it needs (the file is mapped into
# memory). The expressions compiled by a process are added to the store after
# building other entries and when the process exits (the file is rewritten
# with the old and the new entries, and replaced atomically).

REGEX_STORE_MAX = 50000  # (entries; the store is not extended beyond this)
REGEX_STORE_MAX_BYTES = 64 << 20
_REGEX_MAGIC = b'LTRX%04d' % FORMAT_VERSION
_REGEX_HEADER = struct.Struct('<8sQI')  # magic, index length, index crc32
_regex_store = None  # (index, mmap, data offset) of the store file, or () if there is none
_regex_new = {}  # compiled by this process, not in the store
_regex_lock = threading.Lock()
_atexit_registered = False


def _regex_path():
    return os.path.join(directory(), 'regex-store.bin')


def _regex_hash(key):
    return hashlib.blake2b(repr(key).encode('utf-8', 'surrogatepass'), digest_size=16).digest()


def _open_regex_store(path):
    """(index, mmap, data offset) of a store file; raises if it can't be used"""
    import mmap
    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    try:
        magic, ilen, icrc = _REGEX_HEADER.unpack_from(mm)
        if magic != _REGEX_MAGIC:
            raise ValueError('other format')
        start = _REGEX_HEADER.size
        raw = mm[start:start + ilen]
        if len(raw) != ilen or zlib.crc32(raw) != icrc:
            raise ValueError('index checksum mismatch')
        index = pickle.loads(raw)
        if not isinstance(index, dict):
            raise ValueError('bad index')
        return index, mm, start + ilen
    except BaseException:
        mm.close()
        raise


def _load_regex_store():
    global _regex_store
    with _regex_lock:
        if _regex_store is None:
            store = ()
            try:
                store = _open_regex_store(_regex_path())
                _count('regex', 'hit')
            except FileNotFoundError:
                _count('regex', 'miss')
            except Exception as e:
                _count('regex', 'error')
                log.debug('regex store not used: %r', e)
            _regex_store = store
        return _regex_store


def _regex_entry(store, h):
    """the (key, compiled) of the entry with the hash h, None if missing or
    damaged"""
    index, mm, data_start = store
    e = index.get(h)
    if e is None:
        return None
    off, ln, crc = e
    try:
        b = mm[data_start + off:data_start + off + ln]
        if len(b) != ln or zlib.crc32(b) != crc:
            return None
        return pickle.loads(b)
    except Exception:
        return None


def stored_regex(key):
    """The compiled regular expression stored for the key (pattern, flags)
    of jregex.compile(), or None."""
    if not is_enabled():
        return None
    store = _regex_store
    if store is None:
        store = _load_regex_store()
    if not store:
        return None
    entry = _regex_entry(store, _regex_hash(key))
    if entry is None or entry[0] != key:
        return None
    return entry[1]


class regex_store_paused:
    """A context manager: the regular expressions compiled in it (in this
    thread) are not added to the store (e.g. those of the rules, which are
    stored with the rules)."""

    def __enter__(self):
        _local.no_regex_store = getattr(_local, 'no_regex_store', 0) + 1
        return self

    def __exit__(self, *exc):
        _local.no_regex_store -= 1


def add_regex(key, compiled):
    """Record a regular expression compiled by jregex.compile() (to be
    added to the store)."""
    global _atexit_registered
    if not is_enabled() or getattr(_local, 'no_regex_store', 0):
        return
    with _regex_lock:
        if len(_regex_new) < REGEX_STORE_MAX:
            _regex_new[key] = compiled
        if not _atexit_registered:
            import atexit
            atexit.register(flush_regex_store)
            _atexit_registered = True


def flush_regex_store():
    """Add the regular expressions compiled by this process to the store
    (merged with the current file: concurrent processes may have added
    others)."""
    global _regex_store
    with _regex_lock:
        if not _regex_new:
            return
        new = dict(_regex_new)
        _regex_new.clear()
    if not is_enabled():
        return
    path = _regex_path()
    old = None
    try:
        try:
            old = _open_regex_store(path)
        except FileNotFoundError:
            pass
        except Exception as e:
            log.debug('regex store replaced: %r', e)
        index = {}
        chunks = []
        size = 0
        if old is not None:
            # (the entries of the current file, which may have entries that this process did not see)
            oindex, omm, ostart = old
            for h, (off, ln, crc) in oindex.items():
                b = omm[ostart + off:ostart + off + ln]
                if len(b) != ln or zlib.crc32(b) != crc:
                    continue
                index[h] = (size, ln, crc)
                chunks.append(b)
                size += ln
            omm.close()
            old = None
        added = 0
        for k, v in new.items():
            if len(index) >= REGEX_STORE_MAX or size >= REGEX_STORE_MAX_BYTES:
                break
            h = _regex_hash(k)
            if h in index:
                continue
            try:
                b = pickle.dumps((k, v), _PROTOCOL)
            except Exception:
                continue
            crc = zlib.crc32(b)
            index[h] = (size, len(b), crc)
            chunks.append(b)
            size += len(b)
            added += 1
        if not added:
            return
        raw_index = pickle.dumps(index, _PROTOCOL)
        with _regex_lock:
            # (the file of this process is not used anymore: on Windows a mapped file can't be replaced; a reader in
            # another thread then compiles the expression)
            mine = _regex_store
            _regex_store = None
        if mine:
            mine[1].close()
        d = os.path.dirname(path)
        with _lock:
            _prepare_dir(d)
        tmp = os.path.join(d, '.tmp-%d-%s' % (os.getpid(), os.urandom(8).hex()))
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o666)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(_REGEX_HEADER.pack(_REGEX_MAGIC, len(raw_index), zlib.crc32(raw_index)))
                f.write(raw_index)
                for b in chunks:
                    f.write(b)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        _count('regex', 'write')
    except Exception as e:
        _count('regex', 'error')
        log.debug('regex store not written: %r', e)
    finally:
        if old is not None:
            old[1].close()
    with _regex_lock:
        # (the process uses the new file from now on; the old mapping stays valid until it is not used)
        _regex_store = None
