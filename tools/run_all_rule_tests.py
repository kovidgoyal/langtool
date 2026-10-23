#!/usr/bin/env python3
"""Run the rule example tests for all languages (like PatternRuleTest does for
all languages) and print a summary table.

Usage: run_all_rule_tests.py [--write-baseline] [out.json]

--write-baseline writes the failing rules to tests/data/rule_test_baseline.json
(used by tests/test_language_rules.py)."""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from langtool.api import get_language  # noqa
from langtool.languages import LANGUAGES  # noqa
from langtool.tool import JLanguageTool  # noqa
from langtool.testing import PatternRuleTester  # noqa


def codes_to_test():
    out = []
    for short, d in sorted(LANGUAGES.items()):
        if short == 'xx':
            continue
        variants = [v['code'] for v in d['variants']]
        if short == 'de':
            out.extend(['de-DE', 'de', 'de-CH'])
            continue
        first = True
        for v in variants:
            lang = get_language(v)
            if first:
                out.append(v)
                first = False
                continue
            # skip variants without own grammar files
            if os.path.isdir(os.path.join(lang.rules_dir, v)):
                out.append(v)
    return out


BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'data',
                        'rule_test_baseline.json')


def run_language(code):
    t0 = time.time()
    lang = get_language(code)
    lt = JLanguageTool(lang)
    tester = PatternRuleTester(lt)
    failures = tester.run()
    failed = sorted({f.rule.get_full_id() for f in failures})
    return dict(rules=len(tester.rules), failed_rules=len(failed), failures=len(failures),
                skipped=len(lang._pattern_rule_problems), seconds=round(time.time() - t0, 1), failed_ids=failed)


def main():
    args = sys.argv[1:]
    write_baseline = '--write-baseline' in args
    args = [a for a in args if a != '--write-baseline']
    results = {}
    for code in codes_to_test():
        try:
            r = results[code] = run_language(code)
            n = r['rules']
            print('%-24s %6d rules %5d failed (%5.1f%% pass) %4d skipped %6.1fs' % (
                code, n, r['failed_rules'], 100.0 * (n - r['failed_rules']) / max(n, 1), r['skipped'],
                r['seconds']), flush=True)
        except Exception as e:
            traceback.print_exc()
            results[code] = dict(error=str(e))
            print('%-24s ERROR %s' % (code, e), flush=True)
    if args:
        with open(args[0], 'w') as f:
            json.dump(results, f, indent=1)
    if write_baseline:
        baseline = {code: dict(failed_ids=r['failed_ids'], skipped=r['skipped'])
                    for code, r in results.items() if 'error' not in r}
        with open(BASELINE, 'w', encoding='utf-8') as f:
            json.dump(baseline, f, indent=1, sort_keys=True, ensure_ascii=False)
            f.write('\n')


if __name__ == '__main__':
    main()
