#!/usr/bin/env python3
"""Run the XML rule example tests for languages and report pass rates.

Usage: run_rule_tests.py [-v] lang [lang...]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from langtool.api import get_language  # noqa
from langtool.tool import JLanguageTool  # noqa
from langtool.testing import DisambiguationRuleTester, PatternRuleTester  # noqa


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', action='count', default=0)
    p.add_argument('--rule', help='only test rules with this id')
    p.add_argument('languages', nargs='+')
    args = p.parse_args()
    for code in args.languages:
        t0 = time.time()
        lang = get_language(code)
        lt = JLanguageTool(lang)
        tester = PatternRuleTester(lt)
        rules = tester.rules
        if args.rule:
            rules = [r for r in rules if r.get_id() == args.rule]
        failures = tester.run(rules)
        failed_rules = {f.rule.get_full_id() for f in failures}
        n = len(rules)
        print('%s: %d rules, %d failed rules (%.1f%% pass), %d failures, %.1fs' % (
            code, n, len(failed_rules), 100.0 * (n - len(failed_rules)) / max(n, 1), len(failures), time.time() - t0))
        if args.verbose:
            for f in failures[:None if args.verbose > 1 else 50]:
                print('---', f.rule.get_full_id(), f.rule.source_file and os.path.basename(f.rule.source_file))
                print(f.message)
        print('skipped (load problems):', len(lang._pattern_rule_problems))
        if not lang.is_variant() and not args.rule:
            # DisambiguationRuleTest, for the language (not per variant) as in Java
            t0 = time.time()
            dt = DisambiguationRuleTester(lt)
            dfailures = dt.run()
            dfailed = {f.rule.get_full_id() for f in dfailures}
            n = len(dt.rules)
            print('%s (disambiguation): %d rules, %d failed rules (%.1f%% pass), %d failures, %.1fs' % (
                code, n, len(dfailed), 100.0 * (n - len(dfailed)) / max(n, 1), len(dfailures), time.time() - t0))
            if args.verbose:
                for f in dfailures[:None if args.verbose > 1 else 50]:
                    print('---', f.rule.get_full_id())
                    print(f.message)


if __name__ == '__main__':
    main()
