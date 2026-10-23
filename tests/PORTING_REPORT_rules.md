# Porting report: core rule tests, rule match filters, JLanguageTool, public API

New test files:

| file | ported from |
|------|-------------|
| `tests/test_core_rules.py` | `rules/CommaWhitespaceRuleTest`, `DoublePunctuationRuleTest`, `UppercaseSentenceStartRuleTest`, `MultipleWhitespaceRuleTest`, `SentenceWhitespaceRuleTest`, `WordRepeatRuleTest`, `GenericUnpairedBracketsRuleTest`, `LongSentenceRuleTest`, `LongParagraphRuleTest`, `PunctuationMarkAtParagraphEndTest`, `PunctuationMarkAtParagraphEnd2Test`, `WhitespaceBeforePunctuationRuleTest` |
| `tests/test_rule_filters.py` | `rules/RuleMatchTest`, `RuleWithMaxFilterTest`, `SameRuleGroupFilterTest`, `CleanOverlappingFilterTest` |
| `tests/test_jlanguagetool.py` | `JLanguageToolTest`, `markup/AnnotatedTextTest` (the parts that apply), `LanguageSpecificTest` (`testJavaRules`, `testNoQuotesAroundSuggestion`) |
| `tests/test_api.py` | new: public API (`langtool.LanguageTool`, `Match`, `RuleInfo`, `languages()`, ...) |
| `tests/test_c_vs_python.py` | new: compares the C extension with pure Python on 2 x 300 `<example>` sentences plus 20 multi-sentence texts from `rules/en/grammar.xml` and `rules/pl/grammar.xml`. Both run in subprocesses. |

Result: 336 passed, 19 xfailed (all xfails are `strict=True`). Pure Python
mode (`LANGTOOL_PURE_PYTHON=1`) gives the same result.

Notes on the port:

* `FakeLanguage` (code `yy`, no rules) is registered in `test_core_rules.py`
  with `register_language('yy', ...)`.
* Tests that disable rules or add rules get their own `JLanguageTool` instead
  of the session-wide `demo_lt`.
* `UserConfig` is not ported. `JLanguageToolTest.testUserConfig` adds the user
  rule with `JLanguageTool.add_rule()` instead.
* `AnnotatedTextTest`: langtool's `AnnotatedText` has no builder, no global
  meta data, no `getTextWithMarkup()`, and there is no `ContextTools`. Only the
  plain text and the position mapping are tested. The Java test's context
  check is ported as a position check: "xxxx" at plain-text offset 13-17 maps
  to 14-18 in the original. These missing parts are left out, not marked
  xfail.
* `LanguageSpecificTest`: Java runs `testJavaRules` for the languages whose
  module has a `LanguageSpecificTest` subclass, plus the demo language. The
  port uses the same set of languages, one variant each. Not ported:
  spelling / language model / word list / coherency / replace.txt checks,
  `DisambiguationRuleTest`, and the checks that only print warnings.
* `UppercaseSentenceStartRuleTest` passes `Example.wrong/fixed` to the rule
  constructor. The Python rule has no such parameters, so they are left out.
  They don't affect matching.

## Suspected bugs / missing features

### 1. Wrong default sentence tokenizer for languages without their own SRX rules (Demo, FakeLanguage): 14 xfails

**Fixed:** the default is now `SimpleSentenceTokenizer` (segment-simple.srx), as
in Java; the language definitions of all languages except crh select
`sentence_tokenizer='srx'`. The xfail marks were removed.

* Expected behaviour, from `Language.createDefaultSentenceTokenizer()`
  (languagetool-core `Language.java`): languages that don't override it get
  `SimpleSentenceTokenizer`. That is an `SRXSentenceTokenizer` that uses
  `/org/languagetool/tokenizers/segment-simple.srx`. Its `Default` rules
  split after `[.!?…]\s` and `[.!?…]\p{Lu}`. `Demo` and `FakeLanguage`
  don't override it.
* Actual behaviour: `langtool.extensions.create_sentence_tokenizer()` always
  returns `SRXSentenceTokenizer(language)` with `segment.srx`, unless the
  language definition names a `sentence_tokenizer`. In `segment.srx`, codes
  `xx`/`yy` fall into the `Default` language rule. It only splits at
  `\p{L}[.!?…] +\s+`, ` ` and a few rare cases. So, for example,
  `lt.sentence_tokenize("This is a text.  And there's the next sentence.")`
  returns one sentence instead of two. There is no `SimpleSentenceTokenizer`
  equivalent that a language definition can select. The demo definition in
  conftest can't ask for one.
* Verification: I replaced `_sentence_tokenizer` of `xx-XX` and `yy-YY` with
  `SRXSentenceTokenizer(lang, <data>/resource/segment-simple.srx)` in a
  throw-away pytest plugin. All 14 xfailed tests then pass and no other test
  fails.
* Affected tests (input → expected / actual):
  * `SentenceWhitespaceRule`, via `lt.check` with the fake language:
    * `"This is a text.And there's the next sentence."`, and the same with
      `!` and `?`: expected 1 match, actual 0. The rule only looks at
      sentence boundaries.
    * `"This is a text. \r\n  And there's the next sentence."`: expected 0,
      actual 1 (`SENTENCE_WHITESPACE` 18-20). Without the split after `. `,
      the line break and the following spaces are treated as space after a
      sentence end.
  * `UppercaseSentenceStartRule`: `"¿Esto es una pregunta? ¿y esto?"`:
    expected 1, actual 0.
  * `GenericUnpairedBracketsRule`: `"»This is not correct. No matter if it's
    more than one sentence"`: expected 1, actual 0.
  * `LongSentenceRule(40)`: the "The quote ..." texts with unbalanced
    quotes and with no quotes. Expected one match at 0-253 or 0-249. Actual:
    0-316 or 0-313, because the text is not split after "(p." and the
    whole text is treated as one sentence.
  * `LongParagraphRule(6)`: `"Here's some text as a filler.  A test.\nNot a
    long paragraph.\nBecause of the line breaks.\n"` and the `- [ ] ...`
    list: expected 0, actual 1.
  * `PunctuationMarkAtParagraphEnd`: `"This is a test sentence. It can be
    found at http://example.com/foobar"`, `"This is a test sentence. And this
    is a second test sentence"`, the same with a leading `"`, and `"This is a
    test sentence.\nAnd this is a second test sentence. Here is a dot
    missing"`: expected 1, actual 0.
* Possible fix: add a `sentence_tokenizer='simple'` option, or make
  segment-simple.srx the default for languages that are not in `segment.srx`.
  The demo definition in conftest would also need to use it.

### 2. `RuleMatch.trimMatchEnds()` not ported: 3 xfails

**Fixed:** `RuleMatch.trim_match_ends()` was added.

* `RuleMatchTest.testTrimMatchEnds*`. Java: `RuleMatch.trimMatchEnds()` in
  `RuleMatch.java`. `langtool.rules.base.RuleMatch` has no `trim_match_ends()`
  (AttributeError).
* Expected: `"foo bar baz"` → `"foo qux baz"` at 10-21 is trimmed to 14-17,
  `bar` → `qux`. A whitespace-only error string is not changed. `"fins  tot"`
  → `"fins i tot"` must stay a valid range (0-5).

### 3. `JLanguageTool.setCheckCancelledCallback()` not ported: 2 xfails

**Fixed:** `JLanguageTool.set_check_cancelled_callback()` was added.

* `JLanguageToolTest.testCheckStringWithCallbackReturnsTrue/False`. Java:
  `JLanguageTool.setCheckCancelledCallback(CheckCancelledCallback)`. When the
  callback returns true, `check()` returns no matches. `langtool.tool.JLanguageTool`
  has no `set_check_cancelled_callback()` (AttributeError).

## Other observations (not covered by xfails)

* `rules/ml/grammar.xml` has a rule `ഭയങ്കര` with `name=""` (empty
  description). Java's `LanguageSpecificTest` would reject it, but Malayalam
  has no `LanguageSpecificTest` in Java, so it is a data issue and not checked
  here.
* **Fixed** (the `getRuleFileNames()` overrides of uk, sk, de-DE, de-AT and nl
  are now `extra_rule_files`): Ukrainian (`uk-UA`) only loads `rules/uk/grammar.xml`, which contains only
  unification definitions, so there are 0 pattern rules. Java's
  `Ukrainian.getRuleFileNames()` also adds `grammar-barbarism.xml`,
  `grammar-grammar.xml`, `grammar-punctuation.xml`, `grammar-spelling.xml` and
  `grammar-style.xml`. They exist in `src/langtool/data/rules/uk/` but are
  not listed in `extra_rule_files` of the `uk` definition in `languages.py`.
  Together with the unported Java rules, `JLanguageTool(uk-UA)` has only one
  rule (`WHITESPACE_RULE`).
* Column numbers (checked in `test_api.py`): as in Java, sentence-level rule
  matches have 1-based columns on every line. Text-level rule matches
  (`JLanguageTool.checkInternal`, `from.column - (from.line == 0 ? 1 : 0)`)
  have 0-based columns on the first line only. langtool copies this
  inconsistency from Java.
