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
cache directory (`~/.cache/langtool` on Linux). The same mechanism provides
the word lists of the spell checkers, for English the OpenNLP models of the
chunker and, for Japanese, the IPADIC dictionary of the morphological
analyzer. To download them ahead of time:

    python -m langtool download en de fr
    python -m langtool download --spelling en-US de-DE   # also the Hunspell dictionaries

The cache directory is used for all downloads (also the Hunspell
dictionaries for spell checking). It can be set with the `cache_dir`
argument of `LanguageTool`, with `langtool.set_cache_dir(path)` (both are
process-wide settings), with `--cache-dir` on the command line or with the
`LANGTOOL_CACHE_DIR` environment variable (used if nothing else is set):

```python
tool = langtool.LanguageTool('de-DE', cache_dir='/srv/langtool-cache')
```

To use already downloaded dictionaries (for example the jars of a
LanguageTool installation, or a directory with the `.dict` and `.info`
files), pass `dictionary_path` or set `LANGTOOL_DICT_PATH`:

```python
tool = langtool.LanguageTool('de-DE', dictionary_path='/opt/LanguageTool-6.6', download=False)
```

## Spell checking

Spell checking is optional and off by default. When it is on, misspelled
words are reported as matches of the rule `HUNSPELL_RULE` (category
`TYPOS`, issue type `Misspelling`) with suggestions:

```python
tool = langtool.LanguageTool('en-US', spell_check=True)
for m in tool.check('This is an exmaple.'):
    print(m.rule_id, m.context, m.replacements)   # HUNSPELL_RULE exmaple ['example', ...]

tool.spell_check = False   # can be switched at any time
```

It uses [Hunspell](https://hunspell.github.io/) dictionaries (checked with
`langtool.hunspell`, a port of Hunspell: in C in the extension, with an
identical pure Python fallback). By default the
dictionary of the language is downloaded from the
[LibreOffice dictionaries](https://github.com/LibreOffice/dictionaries)
(a pinned commit, checksums verified; `langtool.hunspell_dictionary_info(code)`
tells which one is used and `python -m langtool spelling-languages` lists
them all). The dictionaries have their own licenses (see the repository).
Your own dictionaries can be used instead, given as a mapping from language
or variant codes to a path prefix (the `.aff` and `.dic` files) or an
`(aff, dic)` pair of paths:

```python
tool = langtool.LanguageTool('en-US', spell_check=True,
                             hunspell_dictionaries={'en-US': '/usr/share/hunspell/en_US'})
tool = langtool.LanguageTool('de-CH', spell_check=True,
                             hunspell_dictionaries={'de': ('/dicts/de.aff', '/dicts/de.dic')})
```

The variant code (`de-CH`) is looked up first, then the language code
(`de`). The words are checked like LanguageTool's spelling rules do it
(`HunspellRule`/`SpellingCheckRule`): URLs, e-mail addresses, words
without letters and words of the ignore and spelling lists of the language
(`ignore.txt`, `spelling.txt`, ..., also multi-word entries) are ignored,
words of `prohibit.txt` are always errors. Words containing digits and
all-uppercase words are ignored too (attributes `ignore_words_with_digits`
and `ignore_all_uppercase` of `tool.spelling_rule`).

Without a LibreOffice dictionary (Asturian, Crimean Tatar, Irish, Japanese,
Khmer, Malayalam, Tagalog and Chinese) spell checking raises
`langtool.SpellCheckUnavailable` unless a dictionary is given. For New
Zealand English the British dictionary and for Balearic Catalan the
general Catalan dictionary are used.

The internal spelling lookups of LanguageTool's rules and filters ("is this
word misspelled", suggestions in rule messages) are not affected: they use
LanguageTool's own speller dictionaries, as in Java.

## API

* `langtool.LanguageTool(language, dictionary_path=None, download=True, mother_tongue=None, picky=False,
  spell_check=False, hunspell_dictionaries=None, cache_dir=None)`
  * `check(text)` — list of `Match` objects (`offset`, `length`, `rule_id`,
    `full_rule_id`, `message`, `short_message`, `replacements`, `category`,
    `line`, `column`, `context`, ...)
  * `correct(text)` — text with the first suggestion of each match applied
  * `sentences(text)`, `analyze(text)` — sentence splitting and the
    analysis (tokens, part-of-speech tags, lemmas)
  * `rules()`, `disable_rule(id)`, `enable_rule(id)`, `disable_category(id)`,
    `enable_category(id)`
  * `spell_check` (property, can be set), `spelling_rule`, `hunspell_dictionary`
* `langtool.check(text, language, spell_check=False, hunspell_dictionaries=None)`
* `langtool.languages()` — the supported language codes
* `langtool.download_dictionaries(code, spelling=False)`
* `langtool.set_cache_dir(path)`, `langtool.get_cache_dir()`
* `langtool.spell_check_languages()`, `langtool.hunspell_dictionary_info(code)`

There is also a command line interface: `python -m langtool check -l en-US file.txt`
(`-s` for spell checking, `--hunspell-dict [CODE=]PATH` for a dictionary,
`--cache-dir DIR`).

## Status

The engine of LanguageTool (XML pattern rules, disambiguation rules,
unification, tokenization, tagging, synthesis, the language independent
rules and filters) is ported and the rule sets of all languages are included.
Spell checking is based on Hunspell dictionaries (see above) instead of
LanguageTool's language specific speller rules. Statistical (n-gram / neural
network) rules and remote rules are not part of this package. Some rules of LanguageTool are implemented in
Java code specific to a language; those that are not ported yet are skipped,
`LanguageTool.unsupported_components()` lists them. The abstract rule classes
those language rules are built on (simple replacement, compounds, word
coherency, repetitions, style statistics, ...) are in
`langtool.rules.abstract_rules`; language specific code registers its
components with `langtool.extensions.register()`.

## Testing

    pip install -e .[test]
    pytest

The tests include ports of the unit tests of the LanguageTool core and of the
language modules. They run with the C extension; the pure Python
implementation (the fallback when the extension can not be built) is checked
by `tests/test_c_vs_python.py`, which compares the results of both
implementations, and by a smoke test subset: `LANGTOOL_PURE_PYTHON=1 pytest -m
pure_smoke`. The check
of the example sentences of the XML rules of all languages against a baseline
of known failures (`tests/data/rule_test_baseline.json`) needs the
dictionaries and takes a while, it runs with `LANGTOOL_LANGUAGE_TESTS=1 pytest
tests/test_language_rules.py`. `tools/run_rule_tests.py [-v] <lang>` gives a
per-language report.

## License

LGPL 2.1 or later, like LanguageTool. The rule files are part of LanguageTool
and are under the same license.
