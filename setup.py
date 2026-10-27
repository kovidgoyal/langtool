import importlib.util
import os
import sys

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py

HERE = os.path.dirname(os.path.abspath(__file__))

extra = []
if sys.platform != 'win32':
    extra = ['-O3', '-std=c11', '-Wall', '-Wno-missing-field-initializers']


def _load_module(name, path):
    """a module of the source tree, without importing the package"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _diskcache_module():
    return _load_module('_langtool_diskcache', os.path.join(HERE, 'src', 'langtool', 'diskcache.py'))


class BuildPy(build_py):
    """also writes the manifest of the built package (the hashes of its
    files, used by the disk cache and the static rule tables instead of
    looking at every file of an installed package; see
    langtool.diskcache.package_fingerprint())"""

    def run(self):
        super().run()
        if getattr(self, 'editable_mode', False):
            return  # (an editable install uses the source tree: no manifest, the files are looked at)
        top = os.path.join(self.build_lib, 'langtool')
        if os.path.isdir(top):
            _diskcache_module().write_manifest(top)


class BuildExt(build_ext):
    """generates the static rule tables (tools/gen_rule_tables.py): the table
    files are installed with the package (langtool/_rule_tables/<code>.ltrt,
    also in the source tree with --inplace) and memory-mapped by the
    extension, which has the list of the tables of the build and their build
    ids. LANGTOOL_NO_RULE_TABLES=1 builds the extension without them (the
    rules are then loaded from the XML files); LANGTOOL_RULE_TABLES_JOBS sets
    the number of parallel processes."""

    def run(self):
        tables = None
        for ext in self.extensions:
            if ext.name == 'langtool._speedups':
                path, tables = self._rule_tables()
                ext.sources.append(path)
        super().run()
        if tables is not None:
            pkg = os.path.dirname(self.get_ext_fullpath('langtool._speedups'))
            self._install_tables(tables, os.path.join(pkg, '_rule_tables'))
            if not self.inplace and os.path.exists(os.path.join(pkg, '_package_manifest.json')):
                # (the manifest written by build_py must cover the table files)
                _diskcache_module().write_manifest(pkg)

    def _rule_tables(self):
        """(the path of the generated rule_tables.c, the paths of the table files)"""
        outdir = os.path.join(os.path.abspath(self.build_temp), 'rule_tables')
        gen = _load_module('_langtool_gen_rule_tables', os.path.join(HERE, 'tools', 'gen_rule_tables.py'))
        if os.environ.get('LANGTOOL_NO_RULE_TABLES'):
            return gen.write_empty_c_file(outdir), []
        import subprocess
        cmd = [sys.executable, os.path.join(HERE, 'tools', 'gen_rule_tables.py'), outdir, '--src',
               os.path.join(HERE, 'src')]
        jobs = os.environ.get('LANGTOOL_RULE_TABLES_JOBS')
        if jobs:
            cmd += ['--jobs', jobs]
        r = subprocess.run(cmd)
        path = os.path.join(outdir, 'rule_tables.c')
        if r.returncode != 0 or not os.path.exists(path):
            # (the extension works without the tables)
            print('WARNING: the static rule tables could not be generated; the rules will be loaded from the XML '
                  'files', file=sys.stderr)
            return gen.write_empty_c_file(outdir), []
        return path, gen.table_files(outdir)

    @staticmethod
    def _install_tables(tables, dest):
        """copies the table files to dest (those that changed; written to another file and renamed, processes may
        have the old ones mapped) and removes the other table files there"""
        import shutil
        os.makedirs(dest, exist_ok=True)
        names = set()
        for src in tables:
            name = os.path.basename(src)
            names.add(name)
            target = os.path.join(dest, name)
            try:
                with open(src, 'rb') as a, open(target, 'rb') as b:
                    if a.read(40) == b.read(40) and os.path.getsize(src) == os.path.getsize(target):
                        continue  # (the same build id)
            except OSError:
                pass
            tmp = target + '.tmp'
            shutil.copyfile(src, tmp)
            os.replace(tmp, target)
        for name in os.listdir(dest):
            if name.endswith('.ltrt') and name not in names:
                os.unlink(os.path.join(dest, name))


# The C extension is optional: if it cannot be built the pure Python
# implementation is used. Set LANGTOOL_NO_EXTENSION=1 to skip it.
ext_modules = []
if not os.environ.get('LANGTOOL_NO_EXTENSION'):
    ext_modules.append(Extension('langtool._speedups', sources=['src/langtool/_speedups.c', 'src/langtool/_hunspell.c'],
                                 depends=['src/langtool/_rule_tables.h', 'src/langtool/_rule_engine.h'],
                                 extra_compile_args=extra, optional=True))

setup(ext_modules=ext_modules, cmdclass={'build_py': BuildPy, 'build_ext': BuildExt})
