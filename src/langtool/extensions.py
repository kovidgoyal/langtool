"""Creation of the language components (tokenizers, tagger, synthesizer,
disambiguator, rules) from the declarative language definitions.

Language specific implementations (ports of the Java code of the language
modules) register themselves here with register(); a component that is
referenced by a definition but not (yet) implemented falls back to the
generic implementation (for taggers, tokenizers, ...) or is skipped (rules)
and reported by unsupported_components().
"""

import os
import threading
from collections import defaultdict

_registry = {}
_unsupported = defaultdict(set)
_lock = threading.RLock()
_loaded = False  # all language packages imported
_loaded_packages = set()
# the packages of the language codes that are not package names
_PACKAGE_NAMES = {'is': 'is_', 'de-DE-x-simple-language': 'de_simple'}


def register(kind, name, factory, language=None):
    """Register a factory for a language specific component. kind is one of
    'tagger', 'synthesizer', 'word_tokenizer', 'sentence_tokenizer',
    'disambiguator', 'chunker', 'rule', 'filter'. language is the short code
    of the language the name is meant for: names (Java class names) are
    looked up for the language first, then globally, so different languages
    can have components with the same name (e.g. 'CompoundRule')."""
    _registry[(kind, name, language)] = factory


def _load_language_modules(language=None):
    """Imports the language packages (which register the language specific
    code): only the package of the language (a short code) if it is given,
    else all of them."""
    global _loaded
    if _loaded:
        return
    if language is not None:
        pkg = _PACKAGE_NAMES.get(language, language)
        if pkg in _loaded_packages:
            return
        with _lock:
            if pkg not in _loaded_packages:
                import importlib
                import importlib.util
                from . import lang
                if pkg.isidentifier() and importlib.util.find_spec(lang.__name__ + '.' + pkg) is not None:
                    importlib.import_module(lang.__name__ + '.' + pkg)
                _loaded_packages.add(pkg)
        return
    with _lock:
        if not _loaded:
            from . import lang
            lang.load_all()
            _loaded = True


def lookup(kind, name, language=None):
    if language is not None and not _loaded:
        # only the package of the language is needed if the name is found: the names are registered only once,
        # and the names of a language are registered by its package
        _load_language_modules(language)
        f = _registry.get((kind, name, language))
        if f is None:
            f = _registry.get((kind, name, None))
        if f is not None or name == language:
            # (the hooks of a language (the name is the language) are registered only by its package)
            return f
    _load_language_modules()
    if language is not None:
        f = _registry.get((kind, name, language))
        if f is not None:
            return f
    return _registry.get((kind, name, None))


def note_unsupported(language, kind, name):
    _unsupported[language.code].add((kind, name))


def unsupported_components(language=None):
    """Components referenced by the language definitions that are not
    implemented (yet). Returns a dict: language code -> set of (kind, name)."""
    if language is None:
        return {k: set(v) for k, v in _unsupported.items()}
    return set(_unsupported.get(language.code, ()))


def resource_language(language):
    return language.definition.get('resource_language', language.short_code)


def resource_dir(language):
    return language.resource_dir


def _custom(language, kind, name):
    if not name:
        return None
    f = lookup(kind, name, language.short_code)
    if f is None:
        note_unsupported(language, kind, name)
    return f


def create_tagger(language):
    from .tagging import BaseTagger, DemoTagger
    spec = language.get('tagger')
    if not spec:
        return DemoTagger()
    impl = language.variant_definition.get('tagger_impl') or spec.get('impl')
    f = _custom(language, 'tagger', impl)
    if f is not None:
        return f(language, spec)
    if not spec.get('dict'):
        return DemoTagger()
    return BaseTagger(language.dictionary(spec['dict']), resource_language(language), resource_dir(language),
                      spec.get('lowercase_with_uppercase', True))


def synthesizer_resources(language, spec):
    """The arguments of a BaseSynthesizer for a synthesizer spec of a
    language definition: (dictionary, tags_path, number_speller,
    roman_numberer)"""
    tags = spec.get('tags')
    tags_path = language.resource_path(tags) if tags else None
    if tags_path and not os.path.exists(tags_path):
        # the tags file is part of the dictionary download for some languages
        from .dictionaries import locate, DictionaryNotFound
        try:
            tags_path = locate(tags, language.dictionary_path, language.download_dictionaries)
        except DictionaryNotFound:
            tags_path = None
    # BaseSynthesizer(sorosFileName, ...): the number speller of the .sor
    # file (spec 'sor', none without one) and the Roman numberer of
    # Roman.sor that every BaseSynthesizer has
    from .soros import load_soros
    sor = spec.get('sor')
    number_speller = load_soros(language.resource_path(sor), language.short_code) if sor else None
    roman_numberer = load_soros(language.resource_path('Roman.sor'), 'Roman')
    return language.dictionary(spec['dict']), tags_path, number_speller, roman_numberer


def create_synthesizer(language):
    from .synthesis import BaseSynthesizer
    spec = language.get('synthesizer')
    if not spec:
        return None
    f = _custom(language, 'synthesizer', spec.get('impl'))
    if f is not None:
        return f(language, spec)
    dictionary, tags_path, number_speller, roman_numberer = synthesizer_resources(language, spec)
    return BaseSynthesizer(dictionary, tags_path, resource_language(language), resource_dir(language),
                           number_speller, roman_numberer)


def create_word_tokenizer(language):
    from .tokenizers import WordTokenizer
    name = language.get('word_tokenizer')
    f = _custom(language, 'word_tokenizer', name)
    if f is not None:
        return f(language)
    return WordTokenizer()


def create_sentence_tokenizer(language):
    """'srx' is the language's segment.srx (SRXSentenceTokenizer), the
    default is SimpleSentenceTokenizer as in Language.java"""
    name = language.get('sentence_tokenizer')
    if name == 'srx':
        return SRXSentenceTokenizer(language)
    f = _custom(language, 'sentence_tokenizer', name)
    if f is not None:
        return f(language)
    if name:
        return SRXSentenceTokenizer(language)  # unported language specific tokenizer
    return SimpleSentenceTokenizer(language)


def create_chunker(language):
    name = language.get('chunker')
    f = _custom(language, 'chunker', name)
    if f is not None:
        return f(language)
    return None


def create_post_disambiguation_chunker(language):
    """Language.createDefaultPostDisambiguationChunker(): a 'chunker'
    component (definition key 'post_disambiguation_chunker')"""
    name = language.get('post_disambiguation_chunker')
    f = _custom(language, 'chunker', name)
    if f is not None:
        return f(language)
    return None


def create_disambiguator(language):
    from .disambiguation import (DemoDisambiguator, ChainDisambiguator, MultiWordChunker, MultiWordChunker2,
                                 XmlRuleDisambiguator)
    stages = language.get('disambiguator')
    if not stages:
        return DemoDisambiguator()
    out = []
    for st in stages:
        kind = st[0]
        if kind == 'xml':
            out.append(_xml_disambiguator(language.default_variant, st[1]))
        elif kind == 'xml_of':
            from .api import get_language
            out.append(_xml_disambiguator(get_language(st[1]).default_variant, st[2]))
        elif kind == 'multiword':
            path = _resource_or_downloaded(language, st[1])
            if path is not None:
                out.append(_shared_chunker(path, **st[2]))
        elif kind == 'multiword2':
            kw = dict(st[2])
            impl = kw.pop('impl', None)
            path = language.resource_path(st[1])
            f = _custom(language, 'disambiguator', impl)
            if f is not None:
                out.append(f(language, path, **kw))
            elif os.path.exists(path):
                out.append(MultiWordChunker2(path, **kw))
        elif kind == 'custom':
            f = _custom(language, 'disambiguator', st[1])
            if f is not None:
                out.append(f(language))
        else:
            raise ValueError('Unknown disambiguator stage: %r' % (st,))
    return ChainDisambiguator(out)


def _resource_or_downloaded(language, name):
    """The path of a resource file (e.g. 'de/multitoken-ignore.txt'), or of
    the downloaded file for word lists that are part of the dictionary
    download instead of the package data (see dictionaries.json), None if
    neither exists"""
    path = language.resource_path(name)
    if os.path.exists(path):
        return path
    from .dictionaries import DictionaryNotFound, locate, required_files
    if name not in required_files(resource_language(language)):
        return None
    try:
        return locate(name, language.dictionary_path, language.download_dictionaries)
    except DictionaryNotFound:
        return None


_chunker_cache = {}


def _shared_chunker(path, **kw):
    from .disambiguation import MultiWordChunker
    key = (path, tuple(sorted(kw.items())))
    with _lock:
        c = _chunker_cache.get(key)
        if c is None:
            c = _chunker_cache[key] = MultiWordChunker(path, **kw)
        return c


_xml_cache = {}


def disambiguation_rules(language, use_global=False):
    """Load the disambiguation rules of a language (default variant)."""
    from .patterns.loader import load_disambiguation_rules
    from .rules.filters import default_filter_factory
    key = (language.code, use_global, language.resource_root)
    with _lock:
        r = _xml_cache.get(key)
        if r is None:
            rules = []
            problems = []
            ff = default_filter_factory()
            path = os.path.join(language.resource_dir, 'disambiguation.xml')
            if os.path.exists(path):
                rr, p = load_disambiguation_rules(path, language, language.resource_root, ff)
                rules.extend(rr)
                problems.extend(p)
            if use_global:
                rr, p = load_disambiguation_rules(language.resource_path('disambiguation-global.xml'), language,
                                                  language.resource_root, ff)
                rules.extend(rr)
                problems.extend(p)
            r = _xml_cache[key] = (rules, problems)
        return r


def _xml_disambiguator(language, use_global):
    from .disambiguation import XmlRuleDisambiguator
    rules, problems = disambiguation_rules(language, use_global)
    return XmlRuleDisambiguator(language, rules)


def create_rules(language, messages, user_config=None):
    """Create the code based rules of a language."""
    from .rules.core import CORE_RULES
    specs = list(language.definition.get('rules', ()))
    specs.extend(language.variant_definition.get('extra_rules', ()))
    rules = []
    for name, kw in specs:
        # examples=(wrong, fixed): the IncorrectExample/CorrectExample
        # constructor arguments of the Java rule (Rule.addExamplePair)
        examples = kw.get('examples')
        # url: the URL constructor argument of the Java rule (Rule.setUrl)
        url = kw.get('url')
        if examples is not None or url is not None:
            kw = {k: v for k, v in kw.items() if k not in ('examples', 'url')}
        # a language specific class with the name of a core rule (e.g. the
        # LongSentenceRule of org.languagetool.rules.en) replaces the core rule
        _load_language_modules(language.short_code)  # (the rules of a language are registered by its package)
        cls = None if (('rule', name, language.short_code) in _registry) else CORE_RULES.get(name)
        if cls is not None:
            r = cls(messages, language, **kw)
        else:
            f = _custom(language, 'rule', name)
            r = f(messages, language, user_config, **kw) if f is not None else None
        if r is None:
            continue
        new = r if isinstance(r, (list, tuple)) else [r]
        if examples is not None:
            for rule in new:
                rule.add_example_pair(*examples)
        if url is not None:
            for rule in new:
                rule.url = url
        rules.extend(new)
    return rules


class SRXSentenceTokenizer:
    """Port of org.languagetool.tokenizers.SRXSentenceTokenizer"""

    _doc = None
    _doc_lock = threading.Lock()

    def __init__(self, language, srx_path=None, lang_code=None):
        self.language = language
        self.srx_path = srx_path or language.resource_path('segment.srx')
        self.lang_code = lang_code or language.short_code
        self.par_code = '_two'

    @classmethod
    def _document(cls, path):
        from .srx import SrxDocument
        with cls._doc_lock:
            docs = cls.__dict__.get('_docs')
            if docs is None:
                docs = cls._docs = {}
            d = docs.get(path)
            if d is None:
                d = docs[path] = SrxDocument(path)
            return d

    def tokenize(self, text):
        return self._document(self.srx_path).segment(text, self.lang_code + self.par_code)

    def single_line_breaks_marks_para(self):
        return self.par_code == '_one'

    def set_single_line_breaks_marks_paragraph(self, val):
        self.par_code = '_one' if val else '_two'


class SimpleSentenceTokenizer(SRXSentenceTokenizer):
    """Port of org.languagetool.tokenizers.SimpleSentenceTokenizer, the
    default for languages without their own segmentation rules"""

    def __init__(self, language=None):
        from .language import RESOURCE_DIR
        super().__init__(language, os.path.join(RESOURCE_DIR, 'segment-simple.srx'), 'xx')
