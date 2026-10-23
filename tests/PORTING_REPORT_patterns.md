# Porting report: pattern rule tests (rules/patterns, tagging/disambiguation/rules, jregex)

Ported from `languagetool-core/src/test/java/org/languagetool/`:

| Java test | Python test file |
|---|---|
| rules/patterns/StringMatcherTest | tests/test_string_matcher.py |
| rules/patterns/PatternTokenTest | tests/test_pattern_token.py |
| rules/patterns/MatchTest, MatchStateTest | tests/test_match.py |
| rules/patterns/PatternRuleMatcherTest, AbstractPatternRulePerformerTest | tests/test_pattern_rule_matcher.py |
| rules/patterns/UnifierTest | tests/test_unifier.py |
| rules/patterns/PatternRuleLoaderTest, PatternRuleHandlerTest | tests/test_rule_loader.py |
| rules/patterns/RegexPatternRuleTest, RuleFilterEvaluatorTest | tests/test_regex_rule.py |
| rules/patterns/RuleSetTest | tests/test_ruleset.py |
| tagging/disambiguation/rules/DisambiguationRuleTest (demo language) | tests/test_disambiguation_rules.py |
| (new) Java regex semantics | tests/test_jregex.py |

Every file gives the same results with and without the C extension
(`LANGTOOL_PURE_PYTHON=1`).

## How the Java reference results were obtained

There is no JVM at test time, so the java.util.regex results were computed once
with a small Java program (OpenJDK 27):
* `tests/data/java_string_matcher.json.gz`: results of `String.matches()` and of
  `Pattern.compile(re, CASE_INSENSITIVE|UNICODE_CASE).matcher(s).matches()` for all
  strings that StringMatcherTest checks (`trySomeMutations`,
  `specializedSequenceMatcherIsConsistent`).
* tests/test_jregex.py: the expected values are written directly in the test table.

## Adaptations (not bugs)

* StringMatcherTest.requiredSubstrings: the Python port has no
  `StringMatcher.getRequiredSubstrings()` (a Java-only optimization), so only the
  consistency checks with java.util.regex on the derived strings are ported.
* PatternTokenBuilder / PatternRuleBuilderHelper do not exist in Python, the tests
  have a small local builder.
* MatchTest: the `ManualTaggerAdapter` and `ManualSynthesizerAdapter` used by the
  Java test are re-implemented in the test. The test language is a copy of the demo
  language definition with that tagger/synthesizer.
* MatchStateTest: `MatchState.convertCase(s, sample, lang)` is the module function
  `match.convert_case(conversion, s, sample, lang_code)`.
* JLanguageTool.getPatternRulesByIdAndSubId() is missing; the test filters
  `lt.get_all_rules()`.
* DisambiguationRuleTest: in Java the demo language uses `DemoDisambiguator`, so
  the Java test skips it. The Python demo language uses the XML disambiguator, so
  the Java test logic (disambiguateUntil, toShortString, sortForms, untouched
  examples) is ported and run on `tests/data/resource/xx/disambiguation.xml`. All
  rules pass.
* PatternRuleMatcherTest.testTwoMinOccurrences is `@Ignore` in Java, so it is skipped here too.
* Exceptions: Java `RuntimeException`/`PatternSyntaxException` become
  `ValueError`/`jregex.JavaRegexError`.

Not ported (out of scope or not requested): PatternRuleXmlCreatorTest,
PatternRuleLoaderPermissionTest, RuleFilterCreatorTest, and PatternRuleTest/
DemoPatternRuleTest (already covered by tests/test_demo_pattern_rules.py).

## Bugs found and fixed (no xfail left)

All of these were first marked as strict xfail and were then fixed. The
RuleMatch bug was fixed by the coordinator in rules/base.py; the others were
fixed in src/langtool/jregex.py and src/langtool/testing.py.

1. StringMatcher did not validate the regex syntax.
   * Input: `string_matcher.regexp('tú|?')`.
   * Before: no error; the matcher became the value set `{'tú', ''}`.
   * Java throws in `StringMatcher.create()` (Pattern.compile, line 99).
   * Fixed: `jregex.translate()` now rejects quantifiers that have nothing to repeat.
2. `RuleMatch` had no `__eq__`/`__hash__` (Java RuleMatch.equals, lines 602-617).
   Fixed in rules/base.py by the coordinator.
3. `langtool.testing.DisambiguationRuleTester` reported false failures. Fixed: it
   now follows DisambiguationRuleTest.java:
   * it runs the pre-disambiguation (the stages before the XML rules) and the
     earlier rules first (`disambiguateUntil`);
   * it compares the `toShortString` + `sortForms` format;
   * it checks the marker position;
   * it compares untouched examples with `str()` of the sentence.

   Pass rates of the disambiguation examples, old tester then new tester:

   | lang | old | new |
   |---|---|---|
   | en | 73.8% | 91.2% |
   | de | 94.7% | 99.1% |
   | pl | 53.3% | 64.8% |
   | uk | 0% | 67.5% |
   | fr | 99.5% | 99.9% |
   | ca | 99.7% | 99.9% |
   | nl | 99.9% | 100% |
   | es | 99.5% | 100% |
   | pt | 97.4% | 99.8% |
   | ru | 94.8% | 100% |

   The remaining failures are tagger/disambiguator differences in the language
   modules (e.g. Polish `ale[ale/conj+qub]`), not tester problems.
4. jregex differences from java.util.regex, all fixed. All expected results come
   from OpenJDK 27.
   * **Case insensitivity:**
     * inline `(?i)` without `(?u)` is ASCII-only, done by expanding ASCII letters
       in literals and classes;
     * the jregex.IGNORECASE flag (= CASE_INSENSITIVE|UNICODE_CASE, used for
       case-insensitive tokens) still gives Unicode matching;
     * case-dependent properties (`\p{Lu}`, `\p{Lower}`, ...) are still matched
       case-insensitively, as in Java;
     * with UNICODE_CASE, `i`/`I`/`ı`/`İ` match each other like Java's
       toUpperCase/toLowerCase comparison, including in classes and ranges.
   * **Flag scoping:** the flags `i u U s d m x` are tracked per group and
     restored at `)`. Before, `(?U:...)` and the other flags leaked to the rest of
     the pattern.
   * **(?s):** `(?s).` matches `\n` (it is emitted as `(?s:.)`).
   * **(?d):** UNIX_LINES is supported for `.`, `$`, `^` and `\Z`.
   * **Line terminators:** `$`, `(?m)^` and `(?m)$` know all Java line terminators
     (`\r\n`, `\r`, `\u0085`, `\u2028`, `\u2029`), never match between `\r`
     and `\n`, and `(?m)^` does not match at the end of input.
   * **Stacked quantifiers:** a counted quantifier that directly follows another
     quantifier is ignored, as in Java (`a{2}{3}` == `a{2}`). Any other quantifier
     after a quantifier (`a**`, `a{2}*`, `a??+`) raises JavaRegexError.
   * **Invalid quantifier syntax** raises JavaRegexError: dangling quantifiers
     (`*a`, `a|*`, `(?i)*`, `\Q\E*`) and invalid braces (`a{`, `x{`, `{x`,
     `a{,3}`, `a{x}`, `x{1,2,3}`, `a{3,2}`). Very large upper bounds (> 100000)
     are treated as unbounded, to avoid huge memory use in the regex module.
   * **Property names** are validated like Java:
     * they are case sensitive;
     * the `Is`/`In` prefixes and `gc=`/`sc=`/`blk=` forms are supported;
     * `\p{Alphabetic}`, `\p{Emoji}`, `\p{lower}` and `\p{^L}` are errors;
     * `LC`, `LD`, `L1`, `all`, `IsEmoji_*` and the `javaJava/UnicodeIdentifier*`
       names were added.
   * **Group names:** names must be ASCII letters/digits and start with a letter;
     duplicates and `\k<name>` before the group is defined are errors.
   * **Comments mode** is handled entirely by the translator:
     * whitespace and `#` comments are also skipped inside classes, after `(` and
       before quantifier modifiers;
     * escaped spaces are kept (`(?x)a\ b` matches `a b`).
   * **Trailing `\c`** raises JavaRegexError instead of TypeError.
   * **inline flag `c`** (CANON_EQ) is accepted (ignored), as Java accepts it.
   * **java_replace():** invalid replacement strings raise JavaRegexError when the
     first match is replaced, like Matcher.appendReplacement: missing groups,
     unknown or invalid group names, a trailing `$` or `\`, and `$` without a
     group reference.

### How the jregex fixes were checked
* The tests/test_jregex.py table (731 cases) plus
  `tests/data/java_regex_cases.json.gz` (2809 further cases with Java results).
* All regexes of the real rule files of all languages were compared with
  java.util.regex: 56448 regexes from `<token>`/`<exception>` regexps (with
  CASE_INSENSITIVE|UNICODE_CASE unless case_sensitive="yes"), POS tag regexps and
  `<regexp>` rules. The comparison covered compile success and 731813
  match/find results on words and tags taken from the rule files. There were no
  differences.
* tools/run_rule_tests.py, with the old and the new jregex.py/testing.py on the
  same snapshot of the rest of the tree. No rule fails that passed before.

  | lang | failed rules before | after |
  |---|---|---|
  | ca | 2648 | 2644 |
  | de | 109 | 109 |
  | en | 1659 | 1659 |
  | es | 87 | 85 |
  | fr | 1410 | 1410 |
  | it | 0 | 0 |
  | nl | 21 | 19 |
  | pl | 229 | 229 |
  | pt | 120 | 102 |
  | ru | 4 | 4 |
  | uk | 92 | 92 |

  The number of skipped rules (load problems) did not change.
