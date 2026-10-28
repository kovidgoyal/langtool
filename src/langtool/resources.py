"""The location of the data files of the package: the *resource root*.

The resource root is a directory with the layout of the package directory,
holding the files that langtool reads at run time (not the code)::

    data/                        rules, resources, message bundles, spelling data
    _rule_tables/<code>.ltrt     static rule tables (when built with the extension)
    dictionaries.json            download manifest of the binary dictionaries
    hunspell_dictionaries.json   download manifest of the Hunspell dictionaries
    _package_manifest.json       hashes of the package files (written by setup.py)

These belong together: the static rule tables refer to the rule files by
their paths relative to the root and are checked against the hashes of the
manifest, which also describes the code (the manifest is what the disk
cache and the static rule tables use instead of looking at the files, so it
is required when the code files are not available, e.g. in a frozen
application).

The root is, in this order: the directory set with set_resource_dir(), the
LANGTOOL_RESOURCE_DIR environment variable, the package directory, and in a
frozen application (PyInstaller, cx_Freeze, ...) where the package directory
has no data, ``langtool`` below sys._MEIPASS or next to the executable. It
is decided when it is first needed and can't be changed afterwards (the
languages, caches and tables loaded from it would not follow).

See langtool.freeze for collecting the files when freezing an application.
"""

import os
import sys
import threading

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_VAR = 'LANGTOOL_RESOURCE_DIR'

_lock = threading.Lock()
_root = None      # the resolved root (an absolute path), None: not decided yet
_requested = None  # the directory given to set_resource_dir()


class ResourceDirError(Exception):
    """The resource root is not usable or can't be changed."""


def package_dir():
    """The directory of the package (its code)."""
    return _PACKAGE_DIR


def is_frozen():
    """Whether langtool runs in a frozen application (PyInstaller, cx_Freeze,
    py2exe, Nuitka, ...)."""
    return bool(getattr(sys, 'frozen', False)) or '__compiled__' in globals()


def _has_data(d):
    return os.path.isdir(os.path.join(d, 'data', 'rules'))


def _check(d, origin):
    d = os.path.abspath(os.fspath(d))
    if not _has_data(d):
        raise ResourceDirError('%s (%s) is not a langtool resource directory (it has no data/rules directory)'
                               % (d, origin))
    return d


def _resolve():
    if _requested is not None:
        return _check(_requested, 'set_resource_dir()')
    env = os.environ.get(ENV_VAR)
    if env:
        return _check(env, ENV_VAR)
    if _has_data(_PACKAGE_DIR) or not is_frozen():
        return _PACKAGE_DIR
    candidates = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(os.path.join(meipass, 'langtool'))
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates += [os.path.join(exe_dir, 'langtool'), os.path.join(exe_dir, 'lib', 'langtool')]
    for c in candidates:
        if _has_data(c):
            return os.path.abspath(c)
    raise ResourceDirError('the langtool data files were not found in the frozen application (looked in %s); '
                           'bundle them (see langtool.freeze) or set %s'
                           % (', '.join([_PACKAGE_DIR] + candidates), ENV_VAR))


def root():
    """The resource root (an absolute path)."""
    global _root
    r = _root
    if r is None:
        with _lock:
            r = _root
            if r is None:
                r = _root = _resolve()
    return r


def set_resource_dir(directory):
    """Use directory as the resource root (instead of LANGTOOL_RESOURCE_DIR or
    the package directory). Must be called before langtool uses its data
    (e.g. first thing in a frozen application); raises ResourceDirError if
    another root is already in use or the directory has no data."""
    global _requested
    d = _check(directory, 'set_resource_dir()')
    with _lock:
        if _root is not None and os.path.normcase(_root) != os.path.normcase(d):
            raise ResourceDirError('the langtool resource directory is already %s: set_resource_dir() must be '
                                   'called before the data is used' % _root)
        _requested = d


def path(*parts):
    """A path below the resource root."""
    return os.path.join(root(), *parts)


def data_dir():
    return os.path.join(root(), 'data')


def rules_dir():
    """The directory of the rule files (data/rules)."""
    return os.path.join(root(), 'data', 'rules')


def resource_dir():
    """The directory of the resource files (data/resource)."""
    return os.path.join(root(), 'data', 'resource')


def _under(p, top):
    try:
        return os.path.commonpath([p, top]) == top
    except ValueError:
        return False


def relative(p):
    """The path of p relative to the resource root (with /), None if it is
    not below it."""
    p = os.path.abspath(os.fspath(p))
    r = root()
    if not _under(p, r):
        return None
    return os.path.relpath(p, r).replace(os.sep, '/')


def is_package_file(p):
    """Whether p is a file of the package: below the resource root or the
    package directory."""
    p = os.path.abspath(os.fspath(p))
    return _under(p, root()) or _under(p, _PACKAGE_DIR)


def package_file(rel):
    """The path of a file of the package (rel: relative path with /): below
    the resource root if it is there, else below the package directory
    (code files, when the root is not the package directory)."""
    parts = rel.split('/')
    p = os.path.join(root(), *parts)
    if root() != _PACKAGE_DIR and not os.path.exists(p):
        p = os.path.join(_PACKAGE_DIR, *parts)
    return p


def _reset(directory=None):
    """(tests) forget the root; directory: use it without checking"""
    global _root, _requested
    with _lock:
        _requested = None
        _root = os.path.abspath(directory) if directory is not None else None
