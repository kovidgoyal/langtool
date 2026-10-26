import os
import sys

from setuptools import Extension, setup

extra = []
if sys.platform != 'win32':
    extra = ['-O3', '-std=c11', '-Wall', '-Wno-missing-field-initializers']

# The C extension is optional: if it cannot be built the pure Python
# implementation is used. Set LANGTOOL_NO_EXTENSION=1 to skip it.
ext_modules = []
if not os.environ.get('LANGTOOL_NO_EXTENSION'):
    ext_modules.append(Extension('langtool._speedups', sources=['src/langtool/_speedups.c', 'src/langtool/_hunspell.c'],
                                 extra_compile_args=extra, optional=True))

setup(ext_modules=ext_modules)
