"""Languages. Port of org.languagetool.Language, configured declaratively
(see languages.py) instead of with one Java class per language."""

import os
import threading

from . import jregex
from .patterns.unifier import UnifierConfiguration

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
RULES_DIR = os.path.join(DATA_DIR, 'rules')
RESOURCE_DIR = os.path.join(DATA_DIR, 'resource')

_DEFAULT_QUOTES = ('"', '"', "'", "'")
_INSIDE_SUGGESTION = jregex.compile('<suggestion>(.+?)</suggestion>')
_TYPO_APOSTROPHE = jregex.compile("([\\p{L}\\d-])'([\\p{L}\u00ab])", jregex.IGNORECASE)
_NBSPACE1 = jregex.compile('\\b([a-zA-Z]\\.) ([a-zA-Z]\\.)')
_NBSPACE2 = jregex.compile('\\b([a-zA-Z]\\.) ')
_QUOTED_CHAR = jregex.compile(" '(.)'")
_TYPO1 = jregex.compile("([\u202f\u00a0 \u00ab\"\\(])'")
_TYPO2 = jregex.compile("'([\u202f\u00a0 !\\?,\\.;:\"\\)])")
_TYPO3 = jregex.compile("\u2018s\\b([^\u2019])")
_TYPO4 = jregex.compile('([ \\(])"')
_TYPO5 = jregex.compile('"([\u202f\u00a0 !\\?,\\.;:\\)])')


class Language:
    """A language (variant). Instances are obtained with get_language()."""

    def __init__(self, short_code, definition, variant_definition, registry):
        self.short_code = short_code
        self.definition = definition
        self.variant_definition = variant_definition
        self.registry = registry
        self.name = variant_definition.get('name', definition['name'])
        self.countries = variant_definition.get('countries', definition.get('countries', []))
        self.variant = variant_definition.get('variant')
        self.code = variant_definition['code']
        self.dictionary_path = None
        self.download_dictionaries = True
        self.single_line_breaks_marks_para = False
        self._lock = threading.RLock()
        self._tagger = self._synthesizer = self._disambiguator = self._chunker = None
        self._post_disambiguation_chunker = None
        self._sentence_tokenizer = self._word_tokenizer = None
        self._pattern_rules = None
        self._pattern_rule_parts = None
        self._pattern_rule_problems = []
        self._unifier_config = UnifierConfiguration()
        self.pos_token_cache = {}
        self._dicts = {}
        icr = definition.get('ignored_characters_regex', '[­]')
        self.ignored_characters_regex = jregex.compile(icr) if icr else None

    def __repr__(self):
        return '<Language %s>' % self.code

    @property
    def short_code_with_country_and_variant(self):
        return self.code

    @property
    def resource_root(self):
        d = self.definition.get('data_dir')
        return os.path.join(d, 'resource') if d else RESOURCE_DIR

    @property
    def rules_root(self):
        d = self.definition.get('data_dir')
        return os.path.join(d, 'rules') if d else RULES_DIR

    @property
    def resource_dir(self):
        return os.path.join(self.resource_root, self.definition.get('resource_language', self.short_code))

    @property
    def rules_dir(self):
        return os.path.join(self.rules_root, self.short_code)

    def get(self, key, default=None):
        """Lookup a configuration value, the variant overrides the language."""
        if key in self.variant_definition:
            return self.variant_definition[key]
        return self.definition.get(key, default)

    @property
    def default_variant(self):
        dv = self.definition.get('default_variant')
        if dv is None or dv == self.code:
            return self
        return self.registry(dv)

    @property
    def unifier_config(self):
        return self._unifier_config

    @property
    def disambiguation_unifier_config(self):
        dv = self.default_variant
        if dv is self:
            if not hasattr(self, '_disambiguation_unifier_config'):
                self._disambiguation_unifier_config = UnifierConfiguration()
            return self._disambiguation_unifier_config
        return dv.disambiguation_unifier_config

    # --- resources ---

    def resource_path(self, name):
        """Path to a resource file, name like 'en/multiwords.txt' or
        'segment.srx'"""
        p = os.path.join(self.resource_root, name)
        if not os.path.exists(p) and self.resource_root != RESOURCE_DIR:
            p = os.path.join(RESOURCE_DIR, name)
        return p

    def dictionary(self, name):
        """Load a morfologik dictionary, name like 'en/english.dict'"""
        with self._lock:
            d = self._dicts.get(name)
            if d is None:
                from .dictionaries import locate
                from .fsa import Dictionary
                path = locate(name, self.dictionary_path, self.download_dictionaries)
                d = self._dicts[name] = _shared_dictionary(path)
            return d

    # --- components ---

    @property
    def tagger(self):
        if self._tagger is None:
            with self._lock:
                if self._tagger is None:
                    self._tagger = self.create_tagger()
        return self._tagger

    @property
    def synthesizer(self):
        if self._synthesizer is None:
            with self._lock:
                if self._synthesizer is None:
                    self._synthesizer = self.create_synthesizer() or False
        return self._synthesizer or None

    @property
    def disambiguator(self):
        if self._disambiguator is None:
            with self._lock:
                if self._disambiguator is None:
                    self._disambiguator = self.create_disambiguator()
        return self._disambiguator

    @property
    def chunker(self):
        if self._chunker is None:
            with self._lock:
                if self._chunker is None:
                    self._chunker = self.create_chunker() or False
        return self._chunker or None

    @property
    def post_disambiguation_chunker(self):
        """Language.getPostDisambiguationChunker(): the chunker that adds
        chunk tags to the disambiguated tokens (definition key
        'post_disambiguation_chunker'), or None"""
        if self._post_disambiguation_chunker is None:
            with self._lock:
                if self._post_disambiguation_chunker is None:
                    self._post_disambiguation_chunker = self.create_post_disambiguation_chunker() or False
        return self._post_disambiguation_chunker or None

    @property
    def sentence_tokenizer(self):
        if self._sentence_tokenizer is None:
            with self._lock:
                if self._sentence_tokenizer is None:
                    self._sentence_tokenizer = self.create_sentence_tokenizer()
        return self._sentence_tokenizer

    @property
    def word_tokenizer(self):
        if self._word_tokenizer is None:
            with self._lock:
                if self._word_tokenizer is None:
                    self._word_tokenizer = self.create_word_tokenizer()
        return self._word_tokenizer

    def create_tagger(self):
        from . import extensions
        return extensions.create_tagger(self)

    def create_synthesizer(self):
        from . import extensions
        return extensions.create_synthesizer(self)

    def create_disambiguator(self):
        from . import extensions
        return extensions.create_disambiguator(self)

    def create_chunker(self):
        from . import extensions
        return extensions.create_chunker(self)

    def create_post_disambiguation_chunker(self):
        from . import extensions
        return extensions.create_post_disambiguation_chunker(self)

    def create_sentence_tokenizer(self):
        from . import extensions
        return extensions.create_sentence_tokenizer(self)

    def create_word_tokenizer(self):
        from . import extensions
        return extensions.create_word_tokenizer(self)

    # --- rules ---

    def get_rule_file_names(self):
        files = [os.path.join(self.rules_dir, 'grammar.xml')]
        for extra in ('style.xml', 'grammar_custom.xml'):
            p = os.path.join(self.rules_dir, extra)
            if os.path.exists(p):
                files.append(p)
        if len(self.code) > 2:
            for name in ('grammar.xml', 'style.xml', 'grammar-premium.xml'):
                p = os.path.join(self.rules_dir, self.code, name)
                if os.path.exists(p):
                    files.append(p)
        files.extend(os.path.join(self.rules_dir, f) for f in self.get('extra_rule_files', ()))
        return [f for f in files if os.path.exists(f)]

    def get_pattern_rules(self, filter_factory=None):
        if self._pattern_rules is None:
            with self._lock:
                if self._pattern_rules is None:
                    if filter_factory is None:
                        from .patterns.static import flatten
                        rules = flatten(self.get_pattern_rule_parts())
                    else:
                        from .patterns.loader import load_pattern_rules
                        from .messages import messages_for
                        msgs = messages_for(self.short_code)
                        rules, problems = [], []
                        for f in self.get_rule_file_names():
                            r, skipped = load_pattern_rules(f, self, self.resource_root, filter_factory, msgs)
                            rules.extend(r)
                            problems.extend(skipped)
                        self._pattern_rule_problems = problems
                    self._pattern_rules = rules
        return self._pattern_rules

    def get_pattern_rule_parts(self):
        """The pattern rules of the rule files of the language: a list with,
        per file, the rules of the static rule tables (a
        langtool.patterns.static.StaticRules, whose rule objects are created
        when they are needed) or the list of the rules loaded from the XML
        file (from the persistent cache if possible, see langtool.diskcache).
        get_pattern_rules() has the rule objects of all of them."""
        parts = self._pattern_rule_parts
        if parts is None:
            with self._lock:
                parts = self._pattern_rule_parts
                if parts is None:
                    from .patterns.loader import load_pattern_rules
                    from .patterns.static import rule_parts
                    from .rules.filters import default_filter_factory
                    from .messages import messages_for
                    msgs = messages_for(self.short_code)

                    def load_file(f, ff):
                        return load_pattern_rules(f, self, self.resource_root, ff, msgs)

                    parts, problems = rule_parts('grammar', self, self.get_rule_file_names(), load_file,
                                                 default_filter_factory())
                    self._pattern_rule_problems = problems
                    self._pattern_rule_parts = parts
        return parts

    def get_relevant_rules(self, messages, user_config=None, mother_tongue=None):
        """Language.getRelevantRules: the code based rules, preceded by the
        pattern rules for speakers of the mother tongue (see
        get_mother_tongue_rules())"""
        from . import extensions
        rules = self.get_mother_tongue_rules(mother_tongue)
        rules.extend(extensions.create_rules(self, messages, user_config))
        return rules

    def get_mother_tongue_rules(self, mother_tongue):
        """The pattern rules that Language.getRelevantRules adds for the
        user's mother tongue (a language code or Language), e.g. the rules
        of rules/en/grammar-l2-de.xml for English and German speakers: the
        definition key 'mother_tongue_rule_files' maps the short codes of
        the mother tongues to files of the rules directory of the language.
        The rules are loaded once (a cache in Java)."""
        if mother_tongue is None:
            return []
        files = self.get('mother_tongue_rule_files')
        if not files:
            return []
        code = getattr(mother_tongue, 'short_code', None)
        if code is None:
            code = str(mother_tongue).replace('_', '-').split('-')[0].lower()
        name = files.get(code)
        if name is None:
            return []
        path = os.path.join(self.rules_dir, name)
        key = (path, self.code)
        with _mother_tongue_rules_lock:
            rules = _mother_tongue_rules.get(key)
            if rules is None:
                from .patterns.loader import load_pattern_rules
                from .patterns.static import rule_parts, flatten
                from .rules.filters import default_filter_factory
                from .messages import messages_for
                msgs = messages_for(self.short_code)

                def load_file(f, ff):
                    return load_pattern_rules(f, self, self.resource_root, ff, msgs)
                # (from the static rule tables or the persistent cache if possible)
                rules = _mother_tongue_rules[key] = flatten(rule_parts('grammar', self, [path], load_file,
                                                                       default_filter_factory())[0])
        return list(rules)

    def get_default_enabled_rules_for_variant(self):
        return list(self.variant_definition.get('default_enabled_rules', ()))

    def get_default_disabled_rules_for_variant(self):
        return list(self.variant_definition.get('default_disabled_rules', ()))

    def get_default_spelling_rule(self):
        """Language.getDefaultSpellingRule(), as far as ported: the
        misspelling check (langtool.spelling.MorfologikMisspellingCheck,
        no spell checking rule) registered for the language (kind
        'default_spelling_rule', a factory language -> check), None (Java's
        null) for the others."""
        from . import extensions
        with self._lock:
            if not hasattr(self, '_default_spelling_rule'):
                f = extensions.lookup('default_spelling_rule', self.short_code, self.short_code)
                self._default_spelling_rule = f(self) if f is not None else None
            return self._default_spelling_rule

    def get_multitoken_speller(self):
        """Language.getMultitokenSpeller(): the multitoken speller registered
        for the language (kind 'multitoken_speller'), None by default."""
        from . import extensions
        f = extensions.lookup('multitoken_speller', self.short_code, self.short_code)
        return f(self) if f is not None else None

    def get_consistency_rule_prefix(self):
        return 'PREFIXFORCONSISTENCYRULES_'

    def adjust_match(self, rm, features):
        return rm

    def get_priority_for_id(self, id):
        from .priorities import priority_for_id
        return priority_for_id(self.short_code, id, self.get('priorities'))

    def get_rule_priority(self, rule):
        cat = self.get_priority_for_id(rule.category.id if rule.category is not None else '')
        rp = self.get_priority_for_id(rule.get_id())
        if rp != 0:
            return rp
        if rule.priority != 0:
            return rule.priority
        if cat != 0:
            return cat
        dps = self.get('default_rule_priority_for_style', 0)
        if dps != 0 and rule.loc_quality_issue_type == 'Style':
            return dps
        return 0

    def filter_rule_matches(self, matches, annotated_text, enabled_rules):
        """Language.filterRuleMatches(), called (by the
        LanguageDependentRuleMatchFilter) before the overlapping matches are
        removed; enabled_rules are the ids of the active rules. Languages
        override it by registering a 'filter_rule_matches' extension, a
        function (language, matches, annotated_text, enabled_rules) ->
        matches."""
        from . import extensions
        f = extensions.lookup('filter_rule_matches', self.short_code, self.short_code)
        if f is None:
            return matches
        return f(self, matches, annotated_text, enabled_rules)

    def filter_rule_matches_after_overlapping(self, matches):
        """Language.filterRuleMatchesAfterOverlapping(), called after the
        overlapping matches are removed. Languages override it by
        registering a 'filter_rule_matches_after_overlapping' extension, a
        function (language, matches) -> matches."""
        from . import extensions
        f = extensions.lookup('filter_rule_matches_after_overlapping', self.short_code, self.short_code)
        if f is None:
            return matches
        return f(self, matches)

    # --- typography (Language.getOpeningDoubleQuote() etc.) ---

    def _quote(self, i):
        q = self.get('quotes')
        return q[i] if q else _DEFAULT_QUOTES[i]

    def get_opening_double_quote(self):
        return self._quote(0)

    def get_closing_double_quote(self):
        return self._quote(1)

    def get_opening_single_quote(self):
        return self._quote(2)

    def get_closing_single_quote(self):
        return self._quote(3)

    def is_advanced_typography_enabled(self):
        return bool(self.get('advanced_typography', False))

    def to_advanced_typography(self, text):
        """Language.toAdvancedTypography(), see
        base_to_advanced_typography(). Languages override it by registering
        a 'to_advanced_typography' extension, a function (language, text) ->
        text."""
        from . import extensions
        f = extensions.lookup('to_advanced_typography', self.short_code, self.short_code)
        if f is None:
            return self.base_to_advanced_typography(text)
        return f(self, text)

    def base_to_advanced_typography(self, text):
        """Port of Language.toAdvancedTypography(): converts the
        <suggestion> markup and (if advanced typography is enabled) quotes,
        apostrophes, ellipses and spaces of a message to typographic
        characters"""
        od, cd = self.get_opening_double_quote(), self.get_closing_double_quote()
        if not self.is_advanced_typography_enabled():
            return text.replace('<suggestion>', od).replace('</suggestion>', cd)
        os_, cs = self.get_opening_single_quote(), self.get_closing_single_quote()
        out = text
        preserved = []
        offset = 0
        while True:
            # (Java: the matcher is on the input, not on the output with the replacements)
            m = _INSIDE_SUGGESTION.search(text, offset)
            if m is None:
                break
            group = m.group(1)
            preserved.append(group)
            out = out.replace('<suggestion>' + group + '</suggestion>', '\\' + str(len(preserved) - 1), 1)
            offset = m.end()
        out = out.replace('...', '\u2026')
        out = _NBSPACE1.sub('\\1\u00a0\\2', out)
        out = _NBSPACE2.sub('\\1\u00a0', out)
        out = _TYPO_APOSTROPHE.sub('\\1\u2019\\2', out)
        if out.startswith("'"):
            out = os_ + out[1:]
        if out.endswith("'"):
            out = out[:-1] + cs
        out = _QUOTED_CHAR.sub(lambda m: ' ' + os_ + m.group(1) + cs, out)
        out = _TYPO1.sub(lambda m: m.group(1) + os_, out)
        out = _TYPO2.sub(lambda m: cs + m.group(1), out)
        out = _TYPO3.sub(lambda m: '\u2019s' + m.group(1), out)
        if out.startswith('"'):
            out = od + out[1:]
        if out.endswith('"'):
            out = out[:-1] + cd
        out = _TYPO4.sub(lambda m: m.group(1) + od, out)
        out = _TYPO5.sub(lambda m: cd + m.group(1), out)
        for i, p in enumerate(preserved):
            out = out.replace('\\' + str(i), od + p + cd, 1)
        return out.replace('<suggestion>', od).replace('</suggestion>', cd)

    def is_variant(self):
        """Like Language.isVariant(): true for the languages that are subclasses
        of another language class, i.e. all but the first variant. The
        definition key 'is_variant' overrides this for a language whose
        Java class is a subclass of the class of another language (e.g.
        SimpleGerman extends GermanyGerman)."""
        if 'is_variant' in self.definition:
            return bool(self.definition['is_variant'])
        return self.code != self.definition['variants'][0]['code']

    def equals_consider_variants(self, other):
        if self.code == other.code:
            return True
        return self.short_code == other.short_code and (len(other.code) <= len(other.short_code))


_dict_cache = {}
_dict_lock = threading.Lock()
_mother_tongue_rules = {}
_mother_tongue_rules_lock = threading.Lock()


def _shared_dictionary(path):
    from .fsa import Dictionary
    with _dict_lock:
        d = _dict_cache.get(path)
        if d is None:
            d = _dict_cache[path] = Dictionary(path)
        return d
