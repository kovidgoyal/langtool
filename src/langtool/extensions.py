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
_lock = threading.Lock()
_loaded = False


def register(kind, name, factory):
    """Register a factory for a language specific component. kind is one of
    'tagger', 'synthesizer', 'word_tokenizer', 'sentence_tokenizer',
    'disambiguator', 'chunker', 'rule', 'filter'."""
    _registry[(kind, name)] = factory


def _load_language_modules():
    global _loaded
    if not _loaded:
        with _lock:
            if not _loaded:
                from . import lang  # noqa: registers language specific code
                _loaded = True


def lookup(kind, name):
    _load_language_modules()
    return _registry.get((kind, name))


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
    from .language import RESOURCE_DIR
    return os.path.join(RESOURCE_DIR, resource_language(language))


def _custom(language, kind, name):
    if not name:
        return None
    f = lookup(kind, name)
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


def create_synthesizer(language):
    from .synthesis import BaseSynthesizer
    from .language import RESOURCE_DIR
    spec = language.get('synthesizer')
    if not spec:
        return None
    f = _custom(language, 'synthesizer', spec.get('impl'))
    if f is not None:
        return f(language, spec)
    tags = spec.get('tags')
    tags_path = os.path.join(RESOURCE_DIR, tags) if tags else None
    if tags_path and not os.path.exists(tags_path):
        # the tags file is part of the dictionary download for some languages
        from .dictionaries import locate, DictionaryNotFound
        try:
            tags_path = locate(tags, language.dictionary_path, language.download_dictionaries)
        except DictionaryNotFound:
            tags_path = None
    return BaseSynthesizer(language.dictionary(spec['dict']), tags_path, resource_language(language),
                           resource_dir(language))


def create_word_tokenizer(language):
    from .tokenizers import WordTokenizer
    name = language.get('word_tokenizer')
    f = _custom(language, 'word_tokenizer', name)
    if f is not None:
        return f(language)
    return WordTokenizer()


def create_sentence_tokenizer(language):
    name = language.get('sentence_tokenizer')
    f = _custom(language, 'sentence_tokenizer', name)
    if f is not None:
        return f(language)
    return SRXSentenceTokenizer(language)


def create_chunker(language):
    name = language.get('chunker')
    f = _custom(language, 'chunker', name)
    if f is not None:
        return f(language)
    return None


def create_disambiguator(language):
    from .disambiguation import (DemoDisambiguator, ChainDisambiguator, MultiWordChunker, MultiWordChunker2,
                                 XmlRuleDisambiguator)
    from .language import RESOURCE_DIR
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
            path = os.path.join(RESOURCE_DIR, st[1])
            if os.path.exists(path):
                out.append(_shared_chunker(path, **st[2]))
        elif kind == 'multiword2':
            kw = dict(st[2])
            impl = kw.pop('impl', None)
            path = os.path.join(RESOURCE_DIR, st[1])
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
    from .language import RESOURCE_DIR
    from .patterns.loader import load_disambiguation_rules
    from .rules.filters import default_filter_factory
    key = (language.code, use_global)
    with _lock:
        r = _xml_cache.get(key)
        if r is None:
            rules = []
            problems = []
            ff = default_filter_factory()
            path = os.path.join(RESOURCE_DIR, language.short_code, 'disambiguation.xml')
            if os.path.exists(path):
                rr, p = load_disambiguation_rules(path, language, RESOURCE_DIR, ff)
                rules.extend(rr)
                problems.extend(p)
            if use_global:
                rr, p = load_disambiguation_rules(os.path.join(RESOURCE_DIR, 'disambiguation-global.xml'), language,
                                                  RESOURCE_DIR, ff)
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
        cls = CORE_RULES.get(name)
        if cls is not None:
            rules.append(cls(messages, language, **kw))
            continue
        f = _custom(language, 'rule', name)
        if f is not None:
            r = f(messages, language, user_config, **kw)
            if r is not None:
                if isinstance(r, (list, tuple)):
                    rules.extend(r)
                else:
                    rules.append(r)
    return rules


class SRXSentenceTokenizer:
    """Port of org.languagetool.tokenizers.SRXSentenceTokenizer"""

    _doc = None
    _doc_lock = threading.Lock()

    def __init__(self, language, srx_path=None):
        from .language import RESOURCE_DIR
        self.language = language
        self.srx_path = srx_path or os.path.join(RESOURCE_DIR, 'segment.srx')
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
        return self._document(self.srx_path).segment(text, self.language.short_code + self.par_code)

    def single_line_breaks_marks_para(self):
        return self.par_code == '_one'

    def set_single_line_breaks_marks_paragraph(self, val):
        self.par_code = '_one' if val else '_two'
