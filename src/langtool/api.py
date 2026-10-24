"""The public API of langtool."""

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


def download_dictionaries(language_code=None, progress=None):
    """Download the dictionaries for a language (all languages if None) into
    the cache directory, so that they are available offline later."""
    from . import dictionaries
    if language_code is None:
        codes = sorted(dictionaries.manifest()['languages'])
    else:
        codes = [get_language(language_code).definition.get('resource_language', resolve_code(language_code)[0])]
    for c in codes:
        dictionaries.download_language(c.split('-')[0], progress)


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
    """

    def __init__(self, language, dictionary_path=None, download=True, mother_tongue=None, picky=False):
        from .tool import JLanguageTool, LEVEL_DEFAULT, LEVEL_PICKY
        self.language = get_language(language)
        if dictionary_path is not None:
            self.language.dictionary_path = dictionary_path
        self.language.download_dictionaries = download
        self._lt = JLanguageTool(self.language, mother_tongue=mother_tongue,
                                 level=LEVEL_PICKY if picky else LEVEL_DEFAULT)
        self._lock = threading.RLock()

    @property
    def language_code(self):
        return self.language.code

    @property
    def picky(self):
        return self._lt.level == 'PICKY'

    @picky.setter
    def picky(self, val):
        self._lt.level = 'PICKY' if val else 'DEFAULT'

    def check(self, text):
        """Check the text, returns a list of Match objects, sorted by position."""
        with self._lock:
            matches = self._lt.check(text)
        return [Match(m, text) for m in matches]

    def correct(self, text):
        """Apply the first suggestion of every match to the text."""
        matches = self.check(text)
        out = []
        pos = 0
        for m in matches:
            if not m.replacements or m.offset < pos:
                continue
            out.append(text[pos:m.offset])
            out.append(m.replacements[0])
            pos = m.end
        out.append(text[pos:])
        return ''.join(out)

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


def check(text, language):
    """Convenience function: check text in the given language with a cached
    LanguageTool instance."""
    with _lock:
        tool = _tools.get(language)
        if tool is None:
            tool = _tools[language] = LanguageTool(language)
    return tool.check(text)


_tools = {}
