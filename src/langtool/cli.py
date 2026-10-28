"""Command line interface: python -m langtool / langtool"""

import argparse
import json
import os
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog='langtool', description='Check text for grammar and style errors')
    p.add_argument('--cache-dir', help='directory for the downloaded dictionaries (default: LANGTOOL_CACHE_DIR '
                                       'or the user cache directory)')
    p.add_argument('--no-disk-cache', action='store_true',
                   help='do not use the disk cache of derived data (loaded rules etc., which makes loading a '
                        'language faster), same as LANGTOOL_DISK_CACHE=0')
    p.add_argument('--clear-disk-cache', action='store_true', help='remove the disk cache of derived data')
    p.add_argument('--resource-dir', help='directory with the data files of langtool (default: '
                                          'LANGTOOL_RESOURCE_DIR or the package directory)')
    sub = p.add_subparsers(dest='command')

    c = sub.add_parser('check', help='check text from files or stdin')
    c.add_argument('-l', '--language', required=True, help='language code, e.g. en-US')
    c.add_argument('-d', '--disable', action='append', default=[], help='rule ids to disable')
    c.add_argument('-e', '--enable', action='append', default=[], help='rule ids to enable')
    c.add_argument('--picky', action='store_true', help='enable picky rules')
    c.add_argument('--json', action='store_true', help='JSON output')
    c.add_argument('--dictionary-path', help='where to find the dictionaries')
    c.add_argument('--no-download', action='store_true', help='do not download dictionaries')
    c.add_argument('-s', '--spell-check', action='store_true',
                   help='report misspelled words (Hunspell, rule id HUNSPELL_RULE)')
    c.add_argument('--hunspell-dict', action='append', default=[], metavar='[CODE=]PATH',
                   help='Hunspell dictionary for spell checking: the path without .aff/.dic (e.g. '
                        '/usr/share/hunspell/en_US), optionally prefixed with the language code it is for '
                        '(default: the language of -l); can be repeated')
    c.add_argument('--cache-dir', default=argparse.SUPPRESS, help='directory for the downloaded dictionaries')
    c.add_argument('files', nargs='*')

    d = sub.add_parser('download', help='download dictionaries')
    d.add_argument('--spelling', action='store_true', help='also download the Hunspell dictionaries for spell '
                                                           'checking')
    d.add_argument('--cache-dir', default=argparse.SUPPRESS, help='directory for the downloaded dictionaries')
    d.add_argument('languages', nargs='*')

    sub.add_parser('spelling-languages', help='list the Hunspell dictionaries used for spell checking')

    sub.add_parser('languages', help='list the supported languages')

    a = sub.add_parser('analyze', help='show the analysis (tokens, tags) of text')
    a.add_argument('-l', '--language', required=True)
    a.add_argument('text', nargs='*')

    r = sub.add_parser('copy-resources', help='copy the data files of langtool into a directory (for freezing an '
                                              'application, see langtool.freeze)')
    r.add_argument('dest')

    args = p.parse_args(argv)
    if args.resource_dir:
        from .resources import set_resource_dir
        set_resource_dir(args.resource_dir)
    if args.cache_dir:
        from .api import set_cache_dir
        set_cache_dir(args.cache_dir)
    if args.clear_disk_cache:
        from .api import clear_disk_cache
        clear_disk_cache()
    if args.no_disk_cache:
        from .api import set_disk_cache
        set_disk_cache(False)
    if args.command == 'copy-resources':
        from .freeze import copy_resources
        files = copy_resources(args.dest)
        print('Copied %d files to %s' % (len(files), os.path.abspath(args.dest)))
        return 0
    if args.command == 'languages':
        from .api import language_names
        for code, name in sorted(language_names().items()):
            print(code, name, sep='\t')
        return 0
    if args.command == 'download':
        from .api import download_dictionaries, get_cache_dir
        from .dictionaries import DictionaryNotFound, download_language, manifest
        if args.languages:
            for lang in args.languages:
                print('Downloading dictionaries for', lang, '...')
                try:
                    download_dictionaries(lang, spelling=args.spelling)
                except DictionaryNotFound as e:
                    print('warning:', e, file=sys.stderr)
        else:
            for lang in sorted(manifest()['languages']):
                print('Downloading dictionaries for', lang, '...')
                download_language(lang)
            if args.spelling:
                print('Downloading the Hunspell dictionaries ...')
                from .hunspell_dictionaries import download_all
                download_all()
        print('Dictionaries are in', get_cache_dir())
        return 0
    if args.command == 'spelling-languages':
        from .api import hunspell_dictionary_info, languages
        for code in languages():
            info = hunspell_dictionary_info(code)
            print(code, info['name'] or '-', 'cached' if info['cached'] else '', info['note'] or '', sep='\t')
        return 0
    if args.command == 'analyze':
        from .api import LanguageTool
        tool = LanguageTool(args.language)
        text = ' '.join(args.text) if args.text else sys.stdin.read()
        for s in tool.analyze(text):
            print(s)
        return 0
    if args.command == 'check':
        from .api import LanguageTool
        from .hunspell_dictionaries import SpellCheckUnavailable
        hunspell_dicts = {}
        for spec in args.hunspell_dict:
            code, sep, path = spec.partition('=')
            if not sep or os.sep in code or not code:
                code, path = args.language, spec
            hunspell_dicts[code] = path
        tool = LanguageTool(args.language, dictionary_path=args.dictionary_path, download=not args.no_download,
                            picky=args.picky, hunspell_dictionaries=hunspell_dicts)
        if args.spell_check:
            try:
                tool.spell_check = True
            except SpellCheckUnavailable as e:
                print('warning: %s' % e, file=sys.stderr)
        for r in args.disable:
            tool.disable_rule(r)
        for r in args.enable:
            tool.enable_rule(r)
        texts = []
        if args.files:
            for f in args.files:
                with open(f, encoding='utf-8') as fh:
                    texts.append((f, fh.read()))
        else:
            texts.append(('<stdin>', sys.stdin.read()))
        out = []
        for name, text in texts:
            for m in tool.check(text):
                if args.json:
                    d = m.as_dict()
                    d['file'] = name
                    out.append(d)
                else:
                    print('%s:%d:%d: %s: %s' % (name, m.line + 1, m.column, m.full_rule_id, m.message))
                    if m.replacements:
                        print('    Suggestion: ' + '; '.join(m.replacements[:5]))
        if args.json:
            json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
            print()
        return 0
    p.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
