"""Support for freezing applications that use langtool (PyInstaller,
cx_Freeze, Nuitka, py2exe, ...).

A frozen application needs, besides the code of the package, its data files:
the files of the resource root (see langtool.resources), which must be real
files (the static rule tables are memory-mapped and the XML files are
parsed from files, so they can't be read from a zip archive). They must
include the manifest written when the package was built
(``_package_manifest.json``): the code files are not available in a frozen
application, so the static rule tables and the disk cache rely on the
hashes of the manifest. Freeze from an installed package (pip install, not
editable); for a source tree (``build_ext --inplace``) copy_resources()
writes the manifest.

data_files() lists the files (source path, path relative to the resource
root) and hidden_imports() the modules that a freezer can't find by
following the imports (the language modules are imported by name). Bundle
the files in a ``langtool`` directory next to the frozen modules (where
the package directory of the frozen code is) and langtool finds them
without configuration; elsewhere, call langtool.set_resource_dir() before
using langtool or set the LANGTOOL_RESOURCE_DIR environment variable.

PyInstaller (in the .spec file)::

    import os
    from langtool import freeze
    a = Analysis(['app.py'],
                 datas=[(src, os.path.join('langtool', os.path.dirname(rel)))
                        for src, rel in freeze.data_files()],
                 hiddenimports=freeze.hidden_imports())

Nuitka::

    args = ['--include-data-files=%s=langtool/%s' % (src, rel) for src, rel in freeze.data_files()]
    args += ['--include-module=%s' % m for m in freeze.hidden_imports()]

cx_Freeze (build_exe options; with langtool in zip_exclude_packages)::

    include_files=[(src, 'lib/langtool/' + rel) for src, rel in freeze.data_files()],
    packages=freeze.hidden_imports()

To keep the data outside the executable (about 250 MB), copy it with
copy_resources(dest) (or ``python -m langtool copy-resources DEST``) and
point langtool to it at run time.
"""

import os
import shutil
import warnings

from . import resources
from .diskcache import MANIFEST_NAME, _read_manifest, write_manifest

RESOURCE_DIRS = ('data', '_rule_tables')
RESOURCE_FILES = ('dictionaries.json', 'hunspell_dictionaries.json', MANIFEST_NAME)


class FreezeError(Exception):
    """The resource files can't be bundled as they are."""


def _walk(root):
    """[(source path, relative path)] of the resource files below root"""
    out = []
    for d in RESOURCE_DIRS:
        top = os.path.join(root, d)
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = sorted(n for n in dirnames if n != '__pycache__')
            for n in sorted(filenames):
                if n.endswith(('.pyc', '.pyo', '.tmp')):
                    continue
                src = os.path.join(dirpath, n)
                out.append((src, os.path.relpath(src, root).replace(os.sep, '/')))
    for n in RESOURCE_FILES:
        src = os.path.join(root, n)
        if os.path.isfile(src):
            out.append((src, n))
    return out


def _check_tables(root):
    """warns if the C extension has static rule tables whose files are missing"""
    from ._base import speedups
    if speedups is None or not hasattr(speedups, 'rule_blob_names'):
        return
    missing = [n for n in speedups.rule_blob_names()
               if not os.path.isfile(os.path.join(root, '_rule_tables', n + '.ltrt'))]
    if missing:
        warnings.warn('the static rule tables of %s are missing in %s: the rules of these languages will be loaded '
                      'from the XML files (slower)' % (', '.join(sorted(missing)), root), stacklevel=3)


def data_files(root=None):
    """The files to bundle with a frozen application: [(source path, path
    relative to the resource root, with /)], the files of the resource root
    (default: the one in use, see langtool.resources). Raises FreezeError
    if it has no valid manifest (a source tree or an editable install: see
    copy_resources())."""
    root = os.path.abspath(os.fspath(root)) if root is not None else resources.root()
    if not os.path.isdir(os.path.join(root, 'data', 'rules')):
        raise FreezeError('%s is not a langtool resource directory (it has no data/rules directory)' % root)
    if _read_manifest(root) is None:
        raise FreezeError('%s has no valid %s (a source tree or an editable install, or the files of another '
                          'version of langtool): freeze an installed package, or bundle the files written by '
                          'langtool.freeze.copy_resources(dest) (data_files(root=dest))' % (root, MANIFEST_NAME))
    _check_tables(root)
    return _walk(root)


def hidden_imports():
    """The names of all the modules of the package (sorted): a freezer does
    not find all of them by following the imports (the language modules and
    the classes named in the rule tables are imported by name)."""
    top = resources.package_dir()
    out = set()
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(n for n in dirnames
                             if n not in RESOURCE_DIRS and n != '__pycache__'
                             and os.path.isfile(os.path.join(dirpath, n, '__init__.py')))
        rel = os.path.relpath(dirpath, top)
        prefix = 'langtool' if rel == '.' else 'langtool.' + rel.replace(os.sep, '.')
        for n in filenames:
            if n.endswith('.py'):
                name = n[:-3]
            elif n.endswith(('.so', '.pyd')):
                name = n.split('.', 1)[0]
            else:
                continue
            out.add(prefix if name == '__init__' else prefix + '.' + name)
    return sorted(out)


def copy_resources(dest, root=None):
    """Copy the files of the resource root (default: the one in use) into
    the directory dest (created; a langtool resource directory there is
    replaced), which can then be bundled (data_files(root=dest)) or used as
    the resource root (langtool.set_resource_dir(dest)). In a source tree
    (the resource root is the package directory and has no manifest) the
    manifest is written (rebuild the extension first if the rule files or
    the code changed: stale static rule tables are not used). Returns the
    list of the copied files (paths relative to dest)."""
    root = os.path.abspath(os.fspath(root)) if root is not None else resources.root()
    dest = os.path.abspath(os.fspath(dest))
    if not os.path.isdir(os.path.join(root, 'data', 'rules')):
        raise FreezeError('%s is not a langtool resource directory (it has no data/rules directory)' % root)
    if os.path.normcase(dest) == os.path.normcase(root):
        raise FreezeError('cannot copy the resource directory %s onto itself' % root)
    write_new_manifest = False
    if _read_manifest(root) is None:
        if os.path.normcase(root) != os.path.normcase(resources.package_dir()):
            raise FreezeError('%s has no valid %s' % (root, MANIFEST_NAME))
        write_new_manifest = True  # (a source tree: the manifest covers the code and data of the package directory)
    if os.path.isdir(dest) and os.listdir(dest):
        if not os.path.isdir(os.path.join(dest, 'data', 'rules')):
            raise FreezeError('%s is not empty and not a langtool resource directory' % dest)
        for d in RESOURCE_DIRS:
            shutil.rmtree(os.path.join(dest, d), ignore_errors=True)
        for n in RESOURCE_FILES:
            if os.path.exists(os.path.join(dest, n)):
                os.unlink(os.path.join(dest, n))
    os.makedirs(dest, exist_ok=True)
    copied = []
    for src, rel in _walk(root):
        if rel == MANIFEST_NAME and write_new_manifest:
            continue
        target = os.path.join(dest, *rel.split('/'))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)
    if write_new_manifest:
        write_manifest(root, out_dir=dest)
        copied.append(MANIFEST_NAME)
    _check_tables(dest)
    return copied
