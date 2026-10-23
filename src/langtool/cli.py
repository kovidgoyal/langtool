"""Command line interface: python -m langtool / langtool"""

import argparse
import json
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog='langtool', description='Check text for grammar and style errors')
    sub = p.add_subparsers(dest='command')

    c = sub.add_parser('check', help='check text from files or stdin')
    c.add_argument('-l', '--language', required=True, help='language code, e.g. en-US')
    c.add_argument('-d', '--disable', action='append', default=[], help='rule ids to disable')
    c.add_argument('-e', '--enable', action='append', default=[], help='rule ids to enable')
    c.add_argument('--picky', action='store_true', help='enable picky rules')
    c.add_argument('--json', action='store_true', help='JSON output')
    c.add_argument('--dictionary-path', help='where to find the dictionaries')
    c.add_argument('--no-download', action='store_true', help='do not download dictionaries')
    c.add_argument('files', nargs='*')

    d = sub.add_parser('download', help='download dictionaries')
    d.add_argument('languages', nargs='*')

    sub.add_parser('languages', help='list the supported languages')

    a = sub.add_parser('analyze', help='show the analysis (tokens, tags) of text')
    a.add_argument('-l', '--language', required=True)
    a.add_argument('text', nargs='*')

    args = p.parse_args(argv)
    if args.command == 'languages':
        from .api import language_names
        for code, name in sorted(language_names().items()):
            print(code, name, sep='\t')
        return 0
    if args.command == 'download':
        from .dictionaries import main as dmain
        return dmain(args.languages)
    if args.command == 'analyze':
        from .api import LanguageTool
        tool = LanguageTool(args.language)
        text = ' '.join(args.text) if args.text else sys.stdin.read()
        for s in tool.analyze(text):
            print(s)
        return 0
    if args.command == 'check':
        from .api import LanguageTool
        tool = LanguageTool(args.language, dictionary_path=args.dictionary_path, download=not args.no_download,
                            picky=args.picky)
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
