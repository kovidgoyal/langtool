# Porting report: tokenizers, tagging, synthesis, analysis, tools, fsa tests

Ported from `languagetool-core/src/test/java/org/languagetool/` into
`tests/test_tokenizers.py`, `tests/test_tagging.py`, `tests/test_synthesis.py`,
`tests/test_multiword_chunker.py`, `tests/test_analysis.py`, `tests/test_tools.py`,
`tests/test_fsa.py`.

Added test resource: `tests/data/resource/yy/multiwords.txt` (copy of
`languagetool-core/src/test/resources/org/languagetool/resource/yy/multiwords.txt`,
needed by MultiWordChunkerTest).

## Suspected bugs / missing features (xfail tests)

### 1. ManualTagger accepts lines containing a non-breaking space

* Test: `tests/test_tagging.py::test_manual_tagger_rejects_nbsp`
* Input: a manual tagger file with the line `form x<TAB>lemma<TAB>TAG`
* Expected: loading fails (Java throws
  `RuntimeException("Non-breaking space found in line #...")`), see
  `org.languagetool.tagging.ManualTagger.loadMapping` (languagetool-core,
  `ManualTagger.java`, the `line.contains(" ")` check right after the
  comment/empty line skip).
* Actual: the file is loaded silently and `form x` becomes a tagged form.
* Cause: `langtool.tagging.iter_manual_lines` (shared by `ManualTagger` and
  `ManualSynthesizer`) has no equivalent of that check. Minor (data validation only).

## Notes on adaptations (not bugs)

* `SimpleSentenceTokenizer` has no Python class; the test builds the equivalent
  `SRXSentenceTokenizer` for a language with short code `xx` and
  `src/langtool/data/resource/segment-simple.srx`.
* `ManualTaggerAdapter` (a Java test helper) is re-implemented in the test file.
* `ManualTagger`/`ManualSynthesizer` take file paths instead of streams; the test data
  is written to a temporary file. An invalid manual tagger file raises `ValueError`
  instead of `IOException`.
* `MultiWordChunker.getTokenLettercaseVariants` is `_lettercase_variants` (private) in Python.
* `MultiWordChunker2.setRemoveOtherReadings(true)/setWrapTag(false)` map to the
  constructor arguments `remove_other_readings=True, wrap_tag=False`.
* The FakeLanguage of MultiWordChunkerTest is registered as language `yy` with a
  tagger factory registered through `langtool.extensions.register`.
* StringToolsTest: only functions present in `langtool.tools` are tested
  (assureSet, toId, readStream, readerToString, escapeXML/HTML, filterXML, asString,
  stringForSpeller are not part of the port).
* `test_fsa.py` is new (no Java counterpart): it checks the test dictionary and that the
  pure Python and C lookups agree for FSA5 (it, da), CFSA (ast) and CFSA2 (pl, en, de)
  dictionaries with SUFFIX and PREFIX encoders. No dictionary with the INFIX encoder
  was available in the download cache, so INFIX decoding is untested.
