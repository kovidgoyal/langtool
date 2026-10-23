# langtool

Grammar, style and typography checking for more than 30 languages, based on the
rules of [LanguageTool](https://languagetool.org). This is a port of the
LanguageTool core (written in Java) to Python, with a C extension for the
performance critical parts. No Java and no server are needed.

```python
import langtool

tool = langtool.LanguageTool('en-US')
for m in tool.check('This are a test. He go to school.'):
    print(m.offset, m.length, m.rule_id, m.message, m.replacements)

print(tool.correct('This are a test.'))
```

## Installation

    pip install langtool

The package is distributed as source; a C compiler is needed to build the
optional C extension (`langtool._speedups`). Without it a pure Python
implementation is used, which is about two times slower.

## Dictionaries

Most languages need binary part-of-speech dictionaries (morfologik format).
They are too large to be bundled and are downloaded from Maven Central the
first time a language is used (checksums are verified), and cached in the user
cache directory (`~/.cache/langtool` on Linux, override with
`LANGTOOL_CACHE_DIR`). To download them ahead of time:

    python -m langtool download en de fr

To use already downloaded dictionaries (for example the jars of a
LanguageTool installation, or a directory with the `.dict` and `.info`
files), pass `dictionary_path` or set `LANGTOOL_DICT_PATH`:

```python
tool = langtool.LanguageTool('de-DE', dictionary_path='/opt/LanguageTool-6.6', download=False)
```

## API

* `langtool.LanguageTool(language, dictionary_path=None, download=True, picky=False)`
  * `check(text)` — list of `Match` objects (`offset`, `length`, `rule_id`,
    `full_rule_id`, `message`, `short_message`, `replacements`, `category`,
    `line`, `column`, `context`, ...)
  * `correct(text)` — text with the first suggestion of each match applied
  * `sentences(text)`, `analyze(text)` — sentence splitting and the
    analysis (tokens, part-of-speech tags, lemmas)
  * `rules()`, `disable_rule(id)`, `enable_rule(id)`, `disable_category(id)`,
    `enable_category(id)`
* `langtool.languages()` — the supported language codes
* `langtool.download_dictionaries(code)`

There is also a command line interface: `python -m langtool check -l en-US file.txt`.

## Status

The engine of LanguageTool (XML pattern rules, disambiguation rules,
unification, tokenization, tagging, synthesis, the language independent
rules and filters) is ported and the rule sets of all languages are included.
Spell checking, statistical (n-gram / neural network) rules and remote rules
are not part of this package. Some rules of LanguageTool are implemented in
Java code specific to a language; those that are not ported yet are skipped,
`LanguageTool.unsupported_components()` lists them. The abstract rule classes
those language rules are built on (simple replacement, compounds, word
coherency, repetitions, style statistics, ...) are in
`langtool.rules.abstract_rules`; language specific code registers its
components with `langtool.extensions.register()`.

## Testing

    pip install -e .[test]
    pytest

The tests include ports of the unit tests of the LanguageTool core. The check
of the example sentences of the XML rules of all languages against a baseline
of known failures (`tests/data/rule_test_baseline.json`) needs the
dictionaries and takes a while, it runs with `LANGTOOL_LANGUAGE_TESTS=1 pytest
tests/test_language_rules.py`. `tools/run_rule_tests.py [-v] <lang>` gives a
per-language report.

## License

LGPL 2.1 or later, like LanguageTool. The rule files are part of LanguageTool
and are under the same license.
