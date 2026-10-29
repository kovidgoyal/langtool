# langtool

Grammar, style and typography checking for more than 30 languages, based on the
rules of [LanguageTool](https://languagetool.org) based off commit
[bc7e597](https://github.com/languagetool-org/languagetool/commit/bc7e597ca2a147c1139012fbf5fd9662de8034ad).
This is a port of the LanguageTool core (written in Java) to Python, with a C extension for the
performance critical parts. No Java and no server are needed.

```python
import langtool

tool = langtool.LanguageTool('en-US')
for m in tool.check('This are a test. He go to school.'):
    print(m.offset, m.length, m.rule_id, m.message, m.replacements)

print(tool.correct('This are a test.'))  # These are a test.
```

## Installation

    pip install kovidgoyal-langtool

The package is distributed as source; a C compiler is needed to build the
optional C extension (`langtool._speedups`). Without it a pure Python
implementation is used, which is about two times slower.

Building the extension also compiles the grammar and disambiguation rules
of all languages into static table files that are installed with the
package (`langtool/_rule_tables/<code>.ltrt`, about 150 MB; see below). This
needs `lxml` and `regex` at build time (they are build requirements) and
about 20 seconds on 16 cores (about 3 minutes of CPU time; the languages are
processed in parallel, `LANGTOOL_RULE_TABLES_JOBS` sets the number of
processes). `python setup.py build_ext --inplace` writes the table files
into the source tree. `LANGTOOL_NO_RULE_TABLES=1` builds the extension
without them. Note that the generated tables are tied to the exact version
of `regex`, they should be re-built if it changes.

## Static rule tables

The rules of the built-in languages (all rule files of all variants:
grammar, style, the rules for speakers of other mother tongues and the
disambiguation rules) are compiled at build time into read-only table
files, one per language (`tools/gen_rule_tables.py` loads them with the XML
loader of the package, so they are the same by construction). The C
extension memory-maps the file of a language when it is first used and
selects and matches the rules on the tables in place, and applies the
disambiguation rules and the anti-patterns there; the Python objects of a
rule are only created when they are needed (when the rule matched, or when
code asks for the rules, e.g. `JLanguageTool.get_all_rules()`), and they are
the same objects as those the XML loader creates. Loading the rules takes no
time, there is no slow first start for them, and processes share the pages
of the tables (e.g. forked servers). A table file is only used if it is the
one of the build of the extension (format, size and a build id are
checked); `LANGTOOL_RULE_TABLES_DIR` is another directory with the table
files (of the same build).

The tables are not used (the rules are loaded from the XML files and the
disk cache as before) in the pure Python mode, for languages added with
`langtool.languages.register_language()`, with a custom filter factory and
when the table file is missing, damaged or of another build, or
when they are stale: when a rule file, an entity file, a message bundle or a
module of the XML loading changed after the extension was built (an
installed package is checked with the hashes of its manifest, a source tree
with the size and modification time of the files). Stale tables are logged
on the `langtool.static` logger and shown by
`langtool.static_rules_status()`; rebuild the extension to update them.
`LANGTOOL_STATIC_RULES=0` disables the tables. Rules added at runtime
(`add_rule()`, rule files of the user) work together with the static rules.

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

### Download progress

An application can find out what a language needs, download it with its
own progress display and cancel button, and use its own HTTP stack:

```python
import threading
import langtool

langtool.set_cache_dir(my_cache_dir)
if not langtool.is_ready('de-DE', spelling=True):   # cheap, never downloads
    items = langtool.downloads_needed('de-DE', spelling=True)   # DownloadItem list
    print('%.1f MB to download' % (langtool.download_size('de-DE', spelling=True) / 1e6))

def hook(p):   # a DownloadProgress, called in the downloading thread
    show(p.item.url, p.received, p.item.size, p.batch_received, p.batch_total)
    if user_cancelled:
        raise langtool.DownloadAborted()

langtool.set_download_hook(hook)
langtool.set_url_opener(lambda url: my_http_get(url))   # returns an object with read(n)
cancel = threading.Event()
langtool.download_dictionaries('de-DE', spelling=True, abort=cancel)
```

* `downloads_needed(code=None, spelling=False)` — the `DownloadItem`s
  (`url`, `dest`, `sha256`, `size`, `kind`, `language`) that
  `download_dictionaries()` with the same arguments would download now,
  only those not in the cache. `kind` is `'dictionary'`, `'opennlp'`
  (English chunker/tagger models), `'ipadic'` (Japanese) or `'hunspell'`.
  The dictionaries come in jars: `dest` is the jar, from which the files are
  extracted, after which the jar is removed. `download_size()` is the sum of
  their sizes.
* `is_ready(code, spelling=False, dictionary_path=None)` — whether using the
  language (and spell checking it) will not download anything. Both
  functions only check whether files exist (they can be called from GUI
  code); for a language without a Hunspell dictionary they raise
  `SpellCheckUnavailable` with `spelling=True`.
* `set_download_hook(hook)` — process-wide, `None` removes it. The hook is
  called for every download, including the implicit ones made when a
  `LanguageTool` is created or a text is checked, with a `DownloadProgress`:
  `item`, `item_index`, `item_count` (the batch: the files of one
  `download_dictionaries()` call, or of one implicit download of a
  language), `received` (bytes of the item), `batch_received`,
  `batch_total` (from the manifests, known before the first byte) and
  `state`: `'start'` and `'done'` once per item, `'progress'` after every
  chunk. It is called in the downloading thread, while the download lock is
  held: it must not wait for another thread that downloads. Any exception
  raised by the hook (preferably `DownloadAborted`) aborts the download and
  propagates to the caller (e.g. `LanguageTool()` or `check()`).
* `download_dictionaries(..., abort=event)` — a `threading.Event` checked
  between chunks: when set, `DownloadAborted` is raised. The files that were
  downloaded completely are kept, a partial file is always removed.
* `set_url_opener(opener)` — process-wide, `None` restores
  `urllib.request.urlopen`. `opener(url)` returns an object with `read(n)`
  (`close()` and the context manager protocol are not required, `close()` is
  called if it exists). It is used for all downloads.

The sha256 checksum and the size from the manifest are verified for every
file; a file is written to a temporary file in the cache and moved into
place when complete. `python -m langtool download` shows the progress.

## Disk cache

Loading a language means parsing thousands of XML rules, compiling their
regular expressions and building word lists and other tables from the data
files, which takes a few seconds for the large languages. The results are
cached on disk the first time, after which creating a `LanguageTool` and
the first checks are several times faster (e.g. German: about 1 second
instead of 5 to 6 seconds until the first result). The results of the
checks are the same with and without the cache.

The cache is in the `derived` directory of the cache directory (see above,
e.g. `~/.cache/langtool/derived`), or in the directory given by the
`LANGTOOL_DISK_CACHE_DIR` environment variable. It takes up to about 20 MB
per language (English, German), less than 1 MB for most languages, about
90 MB for all of them. Entries are invalidated automatically when the package (its
version, code or data files), the Python version, the use of the C
extension or the downloaded dictionaries they were built from change. For
an installed package, a manifest written when the package is built (a hash
of all its files) stands for the code and data files, which do not change
after the installation; in a source tree (or with
`LANGTOOL_DISK_CACHE_VERIFY=1`) the size and modification time of every
file are looked at.
Entries are written atomically, so concurrent processes can share the
cache, and an unreadable or corrupt entry is silently rebuilt. The
directory must not be writable by other users (the entries are Python
pickles). The rules of languages added with
`langtool.languages.register_language()` are not cached (changing the
built-in language definitions in place requires disabling the cache).

The rules of the built-in languages normally come from the static rule
tables (see above) and are not cached; when the tables are not used the
rules are cached per rule file, so the variants of a language (e.g.
en-US, en-GB, en-AU) share the entries of the common files and loading a
further variant takes about a second even the first time.

The cache directory is kept below 512 MB: when it grows beyond that, the
least recently used entries (of all package versions) are removed. The
limit can be set with `LANGTOOL_DISK_CACHE_MAX_MB` (0 for no limit) or the
`max_size` argument of `set_disk_cache()`.

To disable the cache set `LANGTOOL_DISK_CACHE=0` (or use `--no-disk-cache`
on the command line), or call:

```python
langtool.set_disk_cache(False)                         # process-wide
langtool.set_disk_cache(True, directory='/srv/lt-derived')   # another directory
langtool.set_disk_cache(True, max_size=200 << 20)      # at most 200 MB
langtool.clear_disk_cache()                            # remove all entries
```

## Data files and frozen applications

The files langtool reads at run time (the rules and other data in `data/`,
the static rule tables in `_rule_tables/`, the dictionary manifests
`dictionaries.json` and `hunspell_dictionaries.json`, and the package
manifest `_package_manifest.json`) form the *resource root*. By default
this is the package directory. They have to stay together, because the
static rule tables and the disk cache check them against the hashes in the
manifest. The resource root can be moved with
`langtool.set_resource_dir(path)` (call it before langtool uses its data),
the `LANGTOOL_RESOURCE_DIR` environment variable or `--resource-dir` on the
command line. `langtool.get_resource_dir()` returns the directory in use.

### Freezing an application

`langtool.freeze` tells a freezing script (PyInstaller, Nuitka, cx_Freeze,
py2exe, ...) what to bundle:

* `freeze.data_files()` — the resource files, as (source path, path
  relative to the resource root) pairs.
* `freeze.hidden_imports()` — all modules of the package. Freezers can't
  find them all by following imports, because the language modules and the
  classes named in the rule tables are imported by name.
* `freeze.copy_resources(dest)` (or `python -m langtool copy-resources
  DEST`) — copies the resource files into a directory (see below).

Put the files in a `langtool` directory next to the frozen modules, where
the frozen package directory is, and langtool finds them without
configuration. In a frozen application langtool also looks in
`sys._MEIPASS/langtool` and in `langtool` (or `lib/langtool`) next to the
executable.

PyInstaller (in the `.spec` file, or as `--add-data`/`--hidden-import`
options):

```python
import os
from langtool import freeze
a = Analysis(['app.py'],
             datas=[(src, os.path.join('langtool', os.path.dirname(rel))) for src, rel in freeze.data_files()],
             hiddenimports=freeze.hidden_imports())
```

Nuitka:

```python
args = ['--include-data-files=%s=langtool/%s' % (src, rel) for src, rel in freeze.data_files()]
args += ['--include-module=%s' % m for m in freeze.hidden_imports()]
```

cx_Freeze (`build_exe` options; langtool must be in `zip_exclude_packages`,
see below):

```python
options = {'build_exe': {
    'include_files': [(src, 'lib/langtool/' + rel) for src, rel in freeze.data_files()],
    'packages': freeze.hidden_imports(),
    'zip_exclude_packages': ['langtool']}}
```

Notes:

* Freeze from an installed package (`pip install`, not editable). A frozen
  application has no code files, so langtool relies on the manifest
  written when the package is built (it has the hashes of the code and
  data files). `data_files()` raises `freeze.FreezeError` when there is no
  manifest. From a source tree (`build_ext --inplace`), run
  `python -m langtool copy-resources DEST` first, which also writes the
  manifest, and bundle `freeze.data_files(root=DEST)`. Rebuild the extension
  before that if the rules or the code changed, otherwise the static rule
  tables are stale and are not used.
* The data is about 250 MB (rules and data files about 95 MB, static rule
  tables about 150 MB). The files must be real files, not inside a zip
  archive: the tables are memory-mapped and the XML files are parsed from
  disk.
* To keep the data outside the executable (e.g. to share it between
  applications, or ship it separately), copy it with `copy-resources` and
  point `LANGTOOL_RESOURCE_DIR` or `langtool.set_resource_dir()` at the copy.
* PyInstaller's onedir mode starts fastest. Onefile works too, but it
  extracts all the files (about 250 MB) on every start. Paths below the
  resource root are relative in the disk cache keys, so a onefile
  application, which extracts to a new directory on every run, keeps using
  its cache entries.
* Downloaded dictionaries still go to the cache directory (see
  Dictionaries); they are not part of the resource root. An offline
  application can bundle them and pass `dictionary_path` (or set
  `LANGTOOL_DICT_PATH`).
* If a different version of langtool's data is bundled, the manifest is
  ignored (with a warning on the `langtool.resources` logger) and the
  rules are loaded from the XML files.
* To check a frozen application, `langtool.get_resource_dir()` shows where
  the data was found and `langtool.static_rules_status()` should report
  `ok` for the languages used.

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
  * `correct(text, java_compat=False, max_rounds=100)` — the corrected
    text: the first suggestion of a match is applied and the text checked
    again, until no match with suggestions is left (in each round one
    match per sentence is applied, so alternative fixes of the same error
    are not combined). `java_compat=True` applies the first suggestion of
    every match in a single pass, like Java's `Tools.correctText`
  * `sentences(text)`, `analyze(text)` — sentence splitting and the
    analysis (tokens, part-of-speech tags, lemmas)
  * `rules()`, `disable_rule(id)`, `enable_rule(id)`, `disable_category(id)`,
    `enable_category(id)`
  * `spell_check` (property, can be set), `spelling_rule`, `hunspell_dictionary`
* `langtool.check(text, language, spell_check=False, hunspell_dictionaries=None)`
* `langtool.languages()` — the supported language codes
* `langtool.download_dictionaries(code=None, progress=None, spelling=False, abort=None)` — `progress(url,
  done, total)` is called after each chunk, `abort` is a `threading.Event` (see Download progress)
* `langtool.downloads_needed(code=None, spelling=False)`, `langtool.download_size(code=None, spelling=False)`,
  `langtool.is_ready(code, spelling=False, dictionary_path=None)`, `langtool.set_download_hook(hook)`,
  `langtool.set_url_opener(opener)`, `DownloadItem`, `DownloadProgress`, `DownloadAborted` — see Download
  progress
* `langtool.set_cache_dir(path)`, `langtool.get_cache_dir()`
* `langtool.set_disk_cache(enabled=True, directory=None, max_size=None)`, `langtool.get_disk_cache_dir()`,
  `langtool.clear_disk_cache()` — the disk cache of derived data (see above)
* `langtool.spell_check_languages()`, `langtool.hunspell_dictionary_info(code)`
* `langtool.static_rules_status()` — whether the static rule tables are used (see above)
* `langtool.set_resource_dir(path)`, `langtool.get_resource_dir()` — the location of the data files;
  `langtool.freeze.data_files()`, `hidden_imports()`, `copy_resources(dest)` — for freezing applications (see
  above)

There is also a command line interface: `python -m langtool check -l en-US file.txt`
(`-s` for spell checking, `--hunspell-dict [CODE=]PATH` for a dictionary,
`--cache-dir DIR`, `--no-disk-cache`, `--clear-disk-cache`, `--resource-dir DIR`;
`python -m langtool copy-resources DEST` copies the data files).

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

The tests run in parallel, on all CPU cores, with pytest-xdist (configured in
`pyproject.toml`: `-n auto --dist loadgroup`); `pytest -n 0` runs them
sequentially, `-n 4` on 4 workers (each worker needs up to about 1.5 GB of
memory).

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
