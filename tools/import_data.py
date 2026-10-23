#!/usr/bin/env python3
"""Import the rule and resource data files from a LanguageTool source checkout
into the package data directory (src/langtool/data).

Usage: import_data.py /path/to/languagetool [dest_dir]

Dictionaries (*.dict) are not copied, they are downloaded on demand (see
langtool/dictionaries.py and tools/make_dict_manifest.py).
"""

import fnmatch
import os
import shutil
import sys

EXCLUDED_MODULES = {'all', 'sr'}  # sr is not built by LanguageTool

EXCLUDE_DIRS = {'hunspell'}
EXCLUDE_PATTERNS = [
    '*.dict', '*.bin', '*.zip', '*.html', '*.pl', '*.py', '*.sh', '*.awk', '*.README', '*.profile',
    'common_words.txt', 'spelling.txt', 'spelling_*.txt', 'ignore.txt', 'prohibit.txt', 'prohibit_custom.txt',
    'multitoken-ignore.txt', 'multitoken-suggest.txt', 'readme*', 'README*', '*-readme.txt', 'coduri.html',
    'word_definitions.txt', '*.ser', 'spelling_correction_model*',
]


def excluded(name):
    return any(fnmatch.fnmatch(name, p) for p in EXCLUDE_PATTERNS)


def copy_tree(src, dst, filter_files=True):
    count = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        rel = os.path.relpath(root, src)
        for f in sorted(files):
            if filter_files and excluded(f):
                continue
            s = os.path.join(root, f)
            d = os.path.normpath(os.path.join(dst, rel, f))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            count += 1
    return count


def main():
    lt = sys.argv[1]
    dest = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'langtool', 'data')
    dest = os.path.abspath(dest)
    for sub in ('rules', 'resource', 'messages'):
        p = os.path.join(dest, sub)
        if os.path.exists(p):
            shutil.rmtree(p)
    core = os.path.join(lt, 'languagetool-core', 'src', 'main', 'resources', 'org', 'languagetool')
    n = 0
    os.makedirs(os.path.join(dest, 'resource'), exist_ok=True)
    for f in ('segment.srx', 'disambiguation-global.xml', 'spelling_global.txt', 'Roman.sor'):
        shutil.copy2(os.path.join(core, 'resource', f), os.path.join(dest, 'resource', f))
        n += 1
    shutil.copy2(os.path.join(core, 'resource', 'org', 'languagetool', 'tokenizers', 'segment-simple.srx'),
                 os.path.join(dest, 'resource', 'segment-simple.srx'))
    os.makedirs(os.path.join(dest, 'messages'), exist_ok=True)
    for f in os.listdir(core):
        if f.startswith('MessagesBundle') and f.endswith('.properties'):
            shutil.copy2(os.path.join(core, f), os.path.join(dest, 'messages', f))
            n += 1
    modules = os.path.join(lt, 'languagetool-language-modules')
    for mod in sorted(os.listdir(modules)):
        if mod in EXCLUDED_MODULES:
            continue
        base = os.path.join(modules, mod, 'src', 'main', 'resources', 'org', 'languagetool')
        if not os.path.isdir(base):
            continue
        for f in os.listdir(base):
            if f.startswith('MessagesBundle') and f.endswith('.properties'):
                shutil.copy2(os.path.join(base, f), os.path.join(dest, 'messages', f))
                n += 1
        for kind in ('rules', 'resource'):
            kdir = os.path.join(base, kind)
            if not os.path.isdir(kdir):
                continue
            for lang in sorted(os.listdir(kdir)):
                src = os.path.join(kdir, lang)
                if os.path.isdir(src):
                    n += copy_tree(src, os.path.join(dest, kind, lang))
    print('Copied %d files to %s' % (n, dest))


if __name__ == '__main__':
    main()
