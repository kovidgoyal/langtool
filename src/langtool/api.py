"""The public API of langtool."""

import bisect
import threading

from .languages import LANGUAGES, resolve_code, all_codes

_languages = {}
_lock = threading.RLock()


def get_language(code):
    """Get the Language object for a code like 'en-US', 'de', 'pl-PL'."""
    from .language import Language
    short, vcode = resolve_code(code)
    with _lock:
        lang = _languages.get(vcode)
        if lang is None:
            d = LANGUAGES[short]
            vdef = next(v for v in d['variants'] if v['code'] == vcode)
            lang = _languages[vcode] = Language(short, d, vdef, get_language)
        return lang


def languages():
    """Codes of all supported languages (including variants)."""
    return all_codes()


def language_names():
    """Mapping of language code to language name."""
    out = {}
    for short, d in LANGUAGES.items():
        for v in d['variants']:
            out[v['code']] = v.get('name', d['name'])
    return out


def download_dictionaries(language_code=None, progress=None, spelling=False):
    """Download the dictionaries for a language (all languages if None) into
    the cache directory, so that they are available offline later. With
    spelling=True the Hunspell dictionary for spell checking is also
    downloaded (for a language without one, SpellCheckUnavailable is
    raised; with language_code None all of them are downloaded)."""
    from . import dictionaries, hunspell_dictionaries
    if language_code is None:
        codes = sorted(dictionaries.manifest()['languages'])
    else:
        codes = [get_language(language_code).definition.get('resource_language', resolve_code(language_code)[0])]
    for c in codes:
        dictionaries.download_language(c.split('-')[0], progress)
    if spelling:
        if language_code is None:
            hunspell_dictionaries.download_all(progress)
        else:
            hunspell_dictionaries.download(get_language(language_code), progress)


def set_cache_dir(path):
    """Set the directory where all downloaded resources (the dictionaries
    of the languages and the Hunspell dictionaries for spell checking) are
    cached. This is a process-wide setting (the dictionaries are shared by
    all LanguageTool instances); None restores the default, the
    LANGTOOL_CACHE_DIR environment variable or else the user cache
    directory (~/.cache/langtool on Linux). The disk cache of derived data
    (see set_disk_cache()) is in its ``derived`` sub directory by
    default."""
    from . import dictionaries
    dictionaries.set_cache_dir(path)


def get_cache_dir():
    """The directory where downloaded resources are cached."""
    from . import dictionaries
    return dictionaries.cache_root()


def set_disk_cache(enabled=True, directory=None, max_size=None):
    """Configure the disk cache of derived data (process-wide).

    Loading a language (parsing its XML rules, compiling regular
    expressions, building word lists and other tables from the data files)
    takes seconds; the results are cached on disk, which makes creating a
    LanguageTool and the first checks several times faster in later
    processes. The results of the checks are the same with and without the
    cache. Entries are invalidated automatically when the package (its
    version, code or data files), the Python version, the C extension or
    the dictionaries they were built from change, and any unreadable or
    corrupt entry is silently rebuilt.

    :param enabled: False disables the cache (nothing is read or written),
           None restores the default: enabled unless the environment
           variable LANGTOOL_DISK_CACHE is 0, off, no or false
    :param directory: the directory of the cache; None means the
           LANGTOOL_DISK_CACHE_DIR environment variable, else the
           ``derived`` sub directory of the cache directory (see
           set_cache_dir(), e.g. ~/.cache/langtool/derived on Linux). The
           directory must not be writable by other users (the entries are
           pickles).
    :param max_size: the maximum size of the cache directory in bytes (0:
           no limit); when it is exceeded the least recently used entries
           are removed. None means the LANGTOOL_DISK_CACHE_MAX_MB
           environment variable (in MB), else 512 MB.

    The cache takes up to about 20 MB per language (less than 1 MB for
    most languages) and is safe to use from concurrent processes (entries
    are written atomically).
    Directories of other package versions that were not used for a week
    are removed automatically; clear_disk_cache() removes everything."""
    from . import diskcache
    diskcache.set_disk_cache(enabled, directory, max_size)


def get_disk_cache_dir():
    """The directory of the disk cache of derived data (see
    set_disk_cache()); the entries are in sub directories for the package
    versions."""
    from . import diskcache
    return diskcache.base_directory()


def clear_disk_cache():
    """Remove all entries of the disk cache of derived data (see
    set_disk_cache())."""
    from . import diskcache
    diskcache.clear()


def spell_check_languages():
    """The language codes for which a Hunspell dictionary for spell checking
    can be downloaded (from the LibreOffice dictionaries). For the other
    languages a dictionary must be given with the hunspell_dictionaries
    argument of LanguageTool."""
    from . import hunspell_dictionaries
    return hunspell_dictionaries.available_languages()


def hunspell_dictionary_info(language_code):
    """Information about the Hunspell dictionary that spell checking uses by
    default for a language: a dict with 'name' (the dictionary in the
    LibreOffice dictionaries repository, e.g. 'en/en_US', None if there is
    none), 'aff_url', 'dic_url', 'commit', 'cached' and 'note'."""
    from . import hunspell_dictionaries as hd
    lang = get_language(language_code)
    name = hd.dictionary_name(lang)
    m = hd.manifest()
    entry = m['dictionaries'].get(name, {}) if name else {}
    return {'name': name, 'aff_url': entry.get('aff', {}).get('url'), 'dic_url': entry.get('dic', {}).get('url'),
            'commit': m['commit'], 'cached': hd.is_cached(lang), 'note': hd.note(lang)}


class Match:
    """A potential problem found in the text."""

    __slots__ = ('rule_id', 'full_rule_id', 'sub_id', 'message', 'short_message', 'offset', 'length',
                 'replacements', 'rule_description', 'category', 'category_name', 'type', 'issue_type',
                 'line', 'column', 'end_line', 'end_column', 'url', 'context', 'sentence', 'rule')

    def __init__(self, rm, text):
        rule = rm.rule
        self.rule = rule
        self.rule_id = rule.get_id()
        self.sub_id = rule.get_sub_id()
        self.full_rule_id = rule.get_full_id()
        self.message = _clean_message(rm.message)
        self.short_message = rm.short_message or ''
        self.offset = rm.from_pos
        self.length = rm.to_pos - rm.from_pos
        self.replacements = list(rm.suggested_replacements)
        self.rule_description = rule.get_description()
        cat = rule.category
        self.category = cat.id if cat is not None else None
        self.category_name = cat.name if cat is not None else None
        self.type = rm.type
        self.issue_type = rule.loc_quality_issue_type
        self.line = rm.line
        self.column = rm.column
        self.end_line = rm.end_line
        self.end_column = rm.end_column
        self.url = rm.url or getattr(rule, 'url', None)
        self.context = text[self.offset:self.offset + self.length] if text is not None else None
        self.sentence = rm.sentence.text if rm.sentence is not None else None

    @property
    def end(self):
        return self.offset + self.length

    def as_dict(self):
        d = {k: getattr(self, k) for k in self.__slots__ if k != 'rule'}
        return d

    def __repr__(self):
        return '<Match %s %d-%d %r -> %r>' % (self.full_rule_id, self.offset, self.end, self.context,
                                              self.replacements[:3])


def _clean_message(msg):
    return msg.replace('<suggestion>', '“').replace('</suggestion>', '”')


def _correct_text_from_matches(text, matches):
    """Port of Java's Tools.correctTextFromMatches: apply the first
    suggestion of every match, skipping a match whose text was already
    changed by an earlier correction."""
    matches = [m for m in matches if m.replacements]
    errors = [text[m.offset:m.end] for m in matches]
    sb = text
    offset = 0
    for m, error in zip(matches, errors):
        start = m.offset - offset
        end = m.end - offset
        if start >= 0 and end >= start and sb[start:end] == error:
            replacement = m.replacements[0]
            sb = sb[:start] + replacement + sb[end:]
            offset += m.end - m.offset - len(replacement)
    return sb


class RuleInfo:
    __slots__ = ('id', 'full_id', 'description', 'category', 'default_off', 'tags', 'issue_type')

    def __init__(self, rule):
        self.id = rule.get_id()
        self.full_id = rule.get_full_id()
        self.description = rule.get_description()
        self.category = rule.category.id if rule.category is not None else None
        self.default_off = rule.default_off
        self.tags = list(rule.tags)
        self.issue_type = rule.loc_quality_issue_type

    def __repr__(self):
        return '<Rule %s: %s>' % (self.full_id, self.description)


class LanguageTool:
    """Check text for grammar and style problems.

    Example::

        tool = LanguageTool('en-US')
        for m in tool.check('This are a test.'):
            print(m.rule_id, m.offset, m.length, m.message, m.replacements)

    :param language: the language code, e.g. 'en-US', 'de-DE', 'fr', 'pl-PL'
    :param dictionary_path: where to look for the dictionaries (a directory
           or a list of directories/jar files), see langtool.dictionaries
    :param download: whether to download missing dictionaries
    :param mother_tongue: language code of the user's mother tongue (enables
           the rules for speakers of that language, like the English rules
           for German and French speakers; false friend rules are not
           supported yet)
    :param picky: enable rules tagged as "picky" (Java: Level.PICKY)
    :param spell_check: report misspelled words (rule id HUNSPELL_RULE,
           category TYPOS) with suggestions, using a Hunspell dictionary.
           Off by default; can be switched at any time with the
           spell_check property. Raises SpellCheckUnavailable if there is
           no dictionary for the language.
    :param hunspell_dictionaries: Hunspell dictionaries to use for spell
           checking instead of the LibreOffice dictionaries that are
           downloaded otherwise: a mapping of language or variant codes to
           a path prefix (the .aff and .dic files) or an (aff, dic) pair of
           paths, e.g. {'en-US': '/usr/share/hunspell/en_US'}. The
           variant code (en-US) is looked up first, then the language (en).
    :param cache_dir: the directory where downloaded resources (all
           dictionaries) are cached; a process-wide setting, see
           set_cache_dir(). By default the disk cache of derived data
           (rules etc. loaded from the data files, which makes creating
           a LanguageTool much faster, see set_disk_cache()) is there too.
    """

    def __init__(self, language, dictionary_path=None, download=True, mother_tongue=None, picky=False,
                 spell_check=False, hunspell_dictionaries=None, cache_dir=None):
        from .tool import JLanguageTool, LEVEL_DEFAULT, LEVEL_PICKY
        from . import hunspell_dictionaries as hd
        if cache_dir is not None:
            set_cache_dir(cache_dir)
        self.language = get_language(language)
        if dictionary_path is not None:
            self.language.dictionary_path = dictionary_path
        self.language.download_dictionaries = download
        self._download = download
        self._hunspell_dictionaries = dict(hunspell_dictionaries or {})
        for loc in self._hunspell_dictionaries.values():
            hd.normalize_location(loc)  # fail early on missing files
        self._lt = JLanguageTool(self.language, mother_tongue=mother_tongue,
                                 level=LEVEL_PICKY if picky else LEVEL_DEFAULT)
        self._lock = threading.RLock()
        self._spelling_rule = None
        self.spell_check = spell_check

    @property
    def language_code(self):
        return self.language.code

    @property
    def picky(self):
        return self._lt.level == 'PICKY'

    @picky.setter
    def picky(self, val):
        self._lt.level = 'PICKY' if val else 'DEFAULT'

    @property
    def spell_check(self):
        """Whether misspelled words are reported (can be switched on and off)."""
        return self._spelling_rule is not None

    @spell_check.setter
    def spell_check(self, value):
        with self._lock:
            if value and self._spelling_rule is None:
                rule = self._create_spelling_rule()
                # (like the spelling rules of LanguageTool, before the other rules)
                self._lt.builtin_rules.insert(0, rule)
                self._lt._rule_set_cache.clear()
                self._spelling_rule = rule
            elif not value and self._spelling_rule is not None:
                self._lt.remove_rule(self._spelling_rule)
                self._spelling_rule = None

    def _create_spelling_rule(self):
        from . import hunspell_dictionaries, spellcheck
        aff, dic = hunspell_dictionaries.locate(self.language, self._hunspell_dictionaries, self._download)
        return spellcheck.get_rule(self._lt.messages, self.language, aff, dic)

    @property
    def spelling_rule(self):
        """The spell checking rule (a langtool.spellcheck.HunspellSpellingRule
        with is_misspelled(word) and suggest(word)), None if spell checking
        is off."""
        return self._spelling_rule

    @property
    def hunspell_dictionary(self):
        """The (aff, dic) paths of the Hunspell dictionary used for spell
        checking, None if spell checking is off."""
        r = self._spelling_rule
        return (r.aff_path, r.dic_path) if r is not None else None

    def check(self, text):
        """Check the text, returns a list of Match objects, sorted by position."""
        with self._lock:
            matches = self._lt.check(text)
        return [Match(m, text) for m in matches]

    def correct(self, text, java_compat=False, max_rounds=100):
        """Correct the text using the first suggestion of the matches.

        By default the text is checked again after each correction: in
        every round the first match with suggestions of each sentence is
        applied, until no such match is left. This avoids applying two
        alternative fixes of the same error (``'This are a test.'`` gives
        ``'These are a test.'``, not ``'These is a test.'``). It stops after
        ``max_rounds`` rounds or when a correction would produce a text
        seen before.

        With ``java_compat=True`` the first suggestion of every match is
        applied in a single pass, like Java's ``Tools.correctText`` (and the
        command line ``--apply`` option of LanguageTool).
        """
        if java_compat:
            return _correct_text_from_matches(text, self.check(text))
        seen = {text}
        for _ in range(max_rounds):
            matches = [m for m in self.check(text) if m.replacements]
            if not matches:
                break
            # sentence start offsets
            starts = []
            pos = 0
            for sentence in self.sentences(text):
                starts.append(pos)
                pos += len(sentence)
            out = []
            pos = 0
            done = set()
            for m in matches:
                sentence = bisect.bisect_right(starts, m.offset) - 1
                if sentence in done or m.offset < pos:
                    continue
                done.add(sentence)
                out.append(text[pos:m.offset])
                out.append(m.replacements[0])
                pos = m.end
            out.append(text[pos:])
            new_text = ''.join(out)
            if new_text in seen:
                break
            seen.add(new_text)
            text = new_text
        return text

    def sentences(self, text):
        """Split the text into sentences."""
        return self._lt.sentence_tokenize(text)

    def analyze(self, text):
        """Tokenize, tag and disambiguate the text. Returns a list of
        AnalyzedSentence objects."""
        with self._lock:
            return self._lt.analyze_text(text)

    # rule configuration

    def rules(self):
        """All rules of the language."""
        out = []
        for r in self._lt.get_all_rules():
            sub = getattr(r, 'rules', None)
            if sub is not None:
                out.extend(RuleInfo(x) for x in sub)
            else:
                out.append(RuleInfo(r))
        return out

    def disable_rule(self, rule_id):
        self._lt.disable_rule(rule_id)

    def disable_rules(self, rule_ids):
        self._lt.disable_rules(rule_ids)

    def enable_rule(self, rule_id):
        """Enable a rule, also works for rules that are off by default."""
        self._lt.enable_rule(rule_id)

    def disable_category(self, category_id):
        self._lt.disable_category(category_id)

    def enable_category(self, category_id):
        self._lt.enable_category(category_id)

    @property
    def disabled_rules(self):
        return set(self._lt.disabled_rules)

    @property
    def enabled_rules(self):
        return set(self._lt.enabled_rules)

    def unsupported_components(self):
        """Parts of the language that are not implemented yet (language specific
        Java code of LanguageTool that has not been ported, and rules that were
        skipped because they use such code). Returns a dict."""
        from . import extensions
        lt = self._lt
        self.language.tagger, self.language.word_tokenizer, self.language.disambiguator
        return {
            'components': sorted(extensions.unsupported_components(self.language)),
            'skipped_rules': list(self.language._pattern_rule_problems),
        }


def check(text, language, spell_check=False, hunspell_dictionaries=None):
    """Convenience function: check text in the given language with a cached
    LanguageTool instance (see LanguageTool for the arguments)."""
    key = (language, bool(spell_check),
           tuple(sorted((k, repr(v)) for k, v in (hunspell_dictionaries or {}).items())))
    with _lock:
        tool = _tools.get(key)
        if tool is None:
            tool = _tools[key] = LanguageTool(language, spell_check=spell_check,
                                              hunspell_dictionaries=hunspell_dictionaries)
    return tool.check(text)


_tools = {}
