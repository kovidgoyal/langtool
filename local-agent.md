initialize_command: python setup.py build_ext --inplace

# Notes for coding agents working on langtool

`langtool` is a port of the Java [LanguageTool](https://github.com/languagetool-org/languagetool)
grammar checker (version 6.8) to Python, with a C extension for the hot
paths. It is a pip installable package (`src/langtool`), shipped as source
only (users compile the extension). All 35 LanguageTool languages are ported
(Serbian is excluded because LanguageTool itself does not build it), and
every language passes all its XML rule examples and its ported Java unit
tests.

Read README.md for the user facing documentation (API, dictionaries, disk
cache, static rule tables, spell checking).

## Golden rules

1. **Faithful port.** Behaviour must match Java LanguageTool exactly,
   including odd corner cases (keep Java quirks and say so in a comment).
   When in doubt, read the Java source (LanguageTool 6.8; clone
   `languagetool-org/languagetool` at tag `v6.8` if it is not available
   locally, the core is in `languagetool-core/`, languages in
   `languagetool-language-modules/<code>/`). Earlier work verified results
   against a real Java LanguageTool (6.6 jar plus the ecj compiler); doing the
   same is the gold standard for tricky behaviour.
2. **Java semantics helpers.** Java regexes are compiled with
   `langtool.jregex` (`jregex.compile`, `jregex.java_replace`), never with
   plain `re`/`regex` (unless trivially identical). Java string and character
   semantics (Character.isLetter, String.trim, equalsIgnoreCase,
   StringTools.*) are in `langtool/tools.py`. Java HashSet/HashMap iteration
   order, where results depend on it: `java_hash_set_order`,
   `java_hash_set_copy_order` and `java_string_hash` in `tools.py`.
3. **C and pure Python must give identical results.** The C extension
   (`_speedups.c`, `_hunspell.c`, `_rule_engine.h`, `_rule_tables.h`, compiled
   into `langtool._speedups`) accelerates hot paths. Every C path has a pure
   Python fallback (selected in `_base.py`; `LANGTOOL_PURE_PYTHON=1` forces
   it) which is the fallback when the extension can't be built.
   `tests/test_c_vs_python.py` compares both. C code: correct reference
   counting, no leaks, no warnings with `-Wall -Wextra`, CPython 3.11+, thread
   safe.
4. **Never commit large or downloaded data.** Dictionaries, speller data,
   OpenNLP models, HanLP/IPADIC data, Hunspell dictionaries etc. are
   downloaded on demand (sha256 pinned manifests) or come from a path the user
   supplies. Generated files (rule tables `src/langtool/_rule_tables/*.ltrt`,
   `_package_manifest.json`, the built extension) are git ignored.
5. **Don't break other languages.** Core changes need the full verification
   (see Testing), including the all-language rule example check.

## Repository layout

- `src/langtool/`
  - `api.py` — public API (`LanguageTool`, `check`, `Match`, spell checking
    options, cache dir); `cli.py`, `__main__.py` — command line
    (`python -m langtool check ...`).
  - `tool.py` — port of `JLanguageTool` (checking pipeline, rule activation,
    AnnotatedText).
  - `language.py` (Language class), `languages.py` (**declarative
    definitions of all languages**, derived from the Java Language classes:
    tagger, synthesizer, tokenizers, disambiguator chain, rules with
    constructor args, variants, quotes/typography, extra rule files...),
    `priorities.py` (rule priorities, `getPriorityForId`).
  - `extensions.py` — creates components from the definitions; registry of
    language specific implementations: `register(kind, name, factory,
    language='<code>')`; kinds: tagger, synthesizer, word_tokenizer,
    sentence_tokenizer, disambiguator, chunker, rule, filter. Names are Java
    class names, looked up for the language first, then globally (several
    languages have e.g. a `CompoundRule`). Filters are global, by fully
    qualified Java class name (as referenced in the XML).
  - `lang/<code>/` — language specific ports (one package per language;
    `is_` for Icelandic, `de_simple` for de-DE-x-simple-language). Each package
    registers its components in `__init__.py`. `lang/__init__.py` documents the
    convention; packages are imported lazily.
  - `patterns/` — the XML rule engine: `loader.py` (lxml SAX-style handlers),
    `rules.py`, `pattern_token.py`, `string_matcher.py`, `matcher.py`,
    `unifier.py`, `ruleset.py`, `rulecache.py` (disk cache of rule sets),
    `static.py`/`static_format.py` (static rule tables).
  - `rules/` — `base.py` (Rule, RuleMatch, match filters), `core.py`
    (language independent rules), `abstract_rules.py` (abstract rule classes
    the language modules subclass: simple replace, compound, coherency,
    repetitions, style statistics, ...), `core_filters.py` (abstract and
    generic rule filters: date checks, advanced synthesizer, suppress
    misspelled suggestions, find suggestions, ...), `unit_conversion.py`,
    `multitoken.py`, `filters.py`, `transformers.py`.
  - Analysis: `tokenizers.py`, `srx.py` (sentence segmentation), `tagging.py`,
    `synthesis.py`, `disambiguation.py`, `chunking.py`, `analysis.py`
    (AnalyzedToken/AnalyzedTokenReadings/AnalyzedSentence), `fsa.py`
    (Morfologik dictionaries), `messages.py`.
  - Ported Java libraries: `opennlp.py` (English chunker), `openregex.py`
    (ru/de chunkers), `hunspell.py` (+ C in `_hunspell.c`), `soros.py` (number
    speller), `diffs.py` (java-diff-utils), `lang/de/compound_tokenizer.py`
    (jWordSplitter), `lang/ja/sen.py` (lucene-gosen), `lang/zh/hanlp.py`
    (HanLP).
  - Spelling: `spelling.py` (the "is misspelled" check and suggestions of the
    Morfologik speller, used internally by filters/rules exactly as in Java),
    `hunspell_rule.py`, `spellcheck.py` (the opt-in user facing Hunspell
    spelling rule), `hunspell_dictionaries.py/.json` (LibreOffice dictionary
    manifest).
  - `resources.py` — the resource root (data/, _rule_tables/, the JSON
    manifests and `_package_manifest.json`; the package directory unless
    relocated with `set_resource_dir()`/`LANGTOOL_RESOURCE_DIR` or found in a
    frozen app). Never locate data files with `__file__`: use
    `resources.path()`, `rules_dir()`, `resource_dir()` (needed for frozen
    apps). Paths below the root are relative in disk cache keys, and the
    static tables store rule `source_file` relative to it.
  - `freeze.py` — `data_files()`, `hidden_imports()`, `copy_resources()`
    for scripts that freeze applications (PyInstaller, Nuitka, cx_Freeze).
  - Data and caches: `dictionaries.py`/`dictionaries.json` (download manifest
    from Maven Central), `diskcache.py` (disk cache of derived data),
    `testing.py` (PatternRuleTester, DisambiguationRuleTester).
  - `data/` — rules, resources and message bundles imported from the
    LanguageTool source by `tools/import_data.py` (don't edit by hand; fix
    the importer and re-import).
- `tests/` — pytest suite (`conftest.py` defines the demo language `xx`,
  fixtures and `require_dictionaries()`); `tests/lang/test_<code>_*.py` are
  the ported Java tests of each language; `tests/data/` test resources and
  `rule_test_baseline.json` (known rule example failures: now empty for all
  languages, keep it that way).
- `tools/` — `import_data.py`, `make_dict_manifest.py` (dictionaries.json),
  `make_hunspell_manifest.py`, `gen_rule_tables.py` (static rule tables, run
  by `build_ext`), `run_rule_tests.py [-v] <codes>` (rule example report per
  language/variant, also disambiguation examples), `run_all_rule_tests.py`
  (all languages; `--write-baseline`).

## Build

    python setup.py build_ext --inplace

`build_ext` also generates the static rule tables (`tools/gen_rule_tables.py`,
parallel, ~20 s) into `src/langtool/_rule_tables/` (in place) or the build
lib. Rebuild after editing rule XML files, entity/message files or the loader
modules listed in `patterns/static_format.py`, otherwise the tables are stale:
langtool then falls back to the XML + disk cache path (slower startup, same
results) and logs on the `langtool.static` logger; `langtool.static_rules_status()`
shows the state.

Build/runtime switches (env vars): `LANGTOOL_NO_EXTENSION` (build without C),
`LANGTOOL_NO_RULE_TABLES` (build without tables), `LANGTOOL_RULE_TABLES_JOBS`,
`LANGTOOL_RULE_TABLES_DIR`, `LANGTOOL_RESOURCE_DIR` (relocated data files),
`LANGTOOL_STATIC_RULES=0` (don't use the tables),
`LANGTOOL_PURE_PYTHON=1`, `LANGTOOL_CACHE_DIR` (download cache; also
`langtool.set_cache_dir()` / `cache_dir=`), `LANGTOOL_DICT_PATH`,
`LANGTOOL_NO_DOWNLOAD`, `LANGTOOL_DISK_CACHE=0`, `LANGTOOL_DISK_CACHE_DIR`,
`LANGTOOL_DISK_CACHE_MAX_MB`, `LANGTOOL_DISK_CACHE_VERIFY`.

## Testing

Always rebuild the extension first if C code changed. Then:

    PYTHONPATH=src python -m pytest -q tests                                   # full suite with C (~15 min)
    LANGTOOL_PURE_PYTHON=1 PYTHONPATH=src python -m pytest -q -m pure_smoke tests  # pure Python smoke subset (~1.5 min)
    PYTHONPATH=src python tools/run_rule_tests.py -v <code> <variant>...      # rule + disambiguation examples
    LANGTOOL_LANGUAGE_TESTS=1 PYTHONPATH=src python -m pytest -q tests/test_language_rules.py  # all languages vs baseline (~6 min)

- The full pure Python suite is deliberately not run routinely; the
  `pure_smoke` marker (module list in `tests/conftest.py`) plus
  `test_c_vs_python.py` cover the fallback.
- Many tests need downloaded dictionaries (downloaded on first use into the
  cache dir; `require_dictionaries()` skips when downloads are impossible).
- Tests may be skipped only for excluded features (see below), with a reason
  saying which. Don't use xfail.
- Ported Java tests keep the Java inputs and expected values, with a
  docstring naming the Java test class. Where Java's expectation includes a
  spell checker match, assert without it and say so.
- For performance or engine changes, check that results are byte-identical:
  dump all matches (rule id, positions, message, suggestions) for all 35
  languages before and after (e.g. using a `git worktree` of HEAD as the
  baseline) on single sentences and multi-sentence texts.

## Porting conventions (language modules)

- A Java class referenced by a language definition gets a Python port in
  `lang/<code>/`, registered with `language='<code>'`. Mirror the Java class
  and method structure; docstrings name the ported Java class.
- Fix the definition in `languages.py` to match the Java Language class
  line by line (getRelevantRules order and constructor args, priorities,
  disambiguator chain, getRuleFileNames → `extra_rule_files`, quotes and
  `advanced_typography`, `sentence_tokenizer='srx'` (check both
  createDefaultSentenceTokenizer and getSentenceTokenizer overrides), `sor=`
  for number spelling, rule `examples=(wrong, fixed)`, `url=`).
- Reuse the abstract classes and filters in `rules/abstract_rules.py`,
  `rules/core_filters.py`, `rules/unit_conversion.py` and the speller helpers
  in `spelling.py` (MorfologikSuggestions mixin etc.); put new shared base
  classes into the core with tests.
- Core bugs found while porting: fix them in the core with a test, never
  work around them in a language package.

## Excluded features

- Spell checking *as LanguageTool does it* (MorfologikSpellerRule/HunspellRule
  rule matches) is not provided; the internal speller lookups that filters and
  rules use (is misspelled, single word suggestions) are ported faithfully.
  User facing spell checking is a separate, opt-in feature based on Hunspell
  (`LanguageTool(spell_check=True, hunspell_dictionaries=..., cache_dir=...)`,
  LibreOffice dictionaries downloaded automatically) — it must not change
  the internal lookups.
- Language model / n-gram / word2vec / neural rules, remote rules, premium,
  GUI/LibreOffice and server code.

## Performance notes

- Hot paths are in C: rule selection and pattern matching (including
  unification), disambiguation, the data model, OpenNLP beam search, speller
  tries, Hunspell (checking, suggestions, loading), Levenshtein.
- Built-in rule sets are static tables (per language `.ltrt` files,
  memory mapped, used in place; Python rule objects are created lazily when a
  rule matches or is asked for). Don't add code paths that force creating all
  rule objects at check time (use `rules_with()` / `get_all_active_rule_ids()`).
- Dictionary derived data and runtime added rules use the disk cache
  (`diskcache.py`, pickles keyed on a package fingerprint; atomic writes; LRU
  size limit).
- Typical steady speed: 1–5 ms per sentence for the large languages; startup
  0.1–0.6 s with warm caches. Benchmark corpora/scripts used so far lived in
  /tmp and are not part of the repo; recreate from rule example sentences.

## Known limitations

- Match offsets count Python characters (code points), not Java UTF-16 units;
  they differ only after characters outside the BMP (emoji).
- Hunspell port follows Hunspell 1.7.1 (the version LanguageTool bundles);
  suggestions can differ from newer native Hunspell versions.

## Git

- Commit messages: a short summary line (plus an optional body); no
  co-author trailers.
- Separate commits for core changes and for language (or feature) work; one
  commit per language port.
- Don't commit generated or downloaded files, or local/private files such as
  `CLAUDE.local.md`.
