"""Languages. Port of org.languagetool.Language, configured declaratively
(see languages.py) instead of with one Java class per language."""

import os
import threading

from . import jregex
from .patterns.unifier import UnifierConfiguration

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
RULES_DIR = os.path.join(DATA_DIR, 'rules')
RESOURCE_DIR = os.path.join(DATA_DIR, 'resource')


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
        self._sentence_tokenizer = self._word_tokenizer = None
        self._pattern_rules = None
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
    def resource_dir(self):
        return os.path.join(RESOURCE_DIR, self.short_code)

    @property
    def rules_dir(self):
        return os.path.join(RULES_DIR, self.short_code)

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
        return os.path.join(RESOURCE_DIR, name)

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
                    from .patterns.loader import load_pattern_rules
                    from .rules.filters import default_filter_factory
                    from .messages import messages_for
                    ff = filter_factory or default_filter_factory()
                    rules = []
                    problems = []
                    msgs = messages_for(self.short_code)
                    for f in self.get_rule_file_names():
                        r, skipped = load_pattern_rules(f, self, RESOURCE_DIR, ff, msgs)
                        rules.extend(r)
                        problems.extend(skipped)
                    self._pattern_rule_problems = problems
                    self._pattern_rules = rules
        return self._pattern_rules

    def get_relevant_rules(self, messages, user_config=None):
        from . import extensions
        return extensions.create_rules(self, messages, user_config)

    def get_default_enabled_rules_for_variant(self):
        return list(self.variant_definition.get('default_enabled_rules', ()))

    def get_default_disabled_rules_for_variant(self):
        return list(self.variant_definition.get('default_disabled_rules', ()))

    def get_consistency_rule_prefix(self):
        return 'PREFIXFORCONSISTENCYRULES_'

    def adjust_match(self, rm, features):
        return rm

    def get_priority_for_id(self, id):
        prio = self.get('priorities', {})
        if id in prio:
            return prio[id]
        for prefix, p in self.get('priority_prefixes', ()):
            if id.startswith(prefix):
                return p
        if id.upper() == 'TOO_LONG_SENTENCE':
            return -101
        if id == 'REPETITIONS_STYLE':
            return -55
        if 'STYLE' in id:
            return -50
        return 0

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

    def filter_rule_matches_after_overlapping(self, matches):
        return matches

    def is_variant(self):
        return len(self.definition.get('variants', ())) > 1 and self.code != self.short_code

    def equals_consider_variants(self, other):
        if self.code == other.code:
            return True
        return self.short_code == other.short_code and (len(other.code) <= len(other.short_code))


_dict_cache = {}
_dict_lock = threading.Lock()


def _shared_dictionary(path):
    from .fsa import Dictionary
    with _dict_lock:
        d = _dict_cache.get(path)
        if d is None:
            d = _dict_cache[path] = Dictionary(path)
        return d
