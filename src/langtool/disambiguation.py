"""Disambiguators. Port of org.languagetool.tagging.disambiguation
MultiWordChunker, MultiWordChunker2, XmlRuleDisambiguator and the
"hybrid" disambiguators that chain several of them."""

import regex

import threading

from .analysis import AnalyzedToken, AnalyzedTokenReadings, AnalyzedSentence
from .tools import (is_camel_case, uppercase_first_char, all_start_with_lowercase, titlecase_global,
                    java_trim, java_split, is_capitalized_word, lowercase_first_char)

TAG_FOR_NOT_ADDING_TAGS = '_NONE_'
MAX_TOKENS_IN_MULTIWORD = 20
_GERMAN_LINE_EXPANDER = regex.compile(r'^.*/[ESN]+$')


class DemoDisambiguator:
    def disambiguate(self, sentence):
        return sentence


def _word_utils_capitalize(s):
    """org.apache.commons.text.WordUtils.capitalize (whitespace delimiters)"""
    out = []
    cap_next = True
    for c in s:
        if c.isspace():
            cap_next = True
            out.append(c)
        elif cap_next:
            t = c.title()
            out.append(t if len(t) == 1 else c)
            cap_next = False
        else:
            out.append(c)
    return ''.join(out)


class MultiWordChunker:

    def __init__(self, path, allow_first_capitalized=False, allow_all_uppercase=False, allow_titlecase=False,
                 default_tag=None, ignore_spelling=False, remove_previous_tags=False):
        self.path = path
        self.allow_first_capitalized = allow_first_capitalized
        self.allow_all_uppercase = allow_all_uppercase
        self.allow_titlecase = allow_titlecase
        self.default_tag = default_tag
        self.add_ignore_spelling = ignore_spelling
        self.is_remove_previous_tags = remove_previous_tags
        self._initialized = False
        self._init_lock = threading.Lock()

    def _load_words(self):
        lines, self.separator = self._load_words_and_separator()
        return lines

    def _load_words_and_separator(self):
        lines = []
        separator = '\t'
        with open(self.path, encoding='utf-8') as f:
            for line in f:
                line = java_trim(line.rstrip('\r\n'))
                if line.startswith('#separatorRegExp='):
                    separator = line.replace('#separatorRegExp=', '')
                if not line or line[0] == '#':
                    continue
                if '#' in line:
                    line = java_trim(line[:line.index('#')])
                if _GERMAN_LINE_EXPANDER.fullmatch(line):
                    parts = line.split('/')
                    base = java_trim(parts[0])
                    lines.append(base)
                    if 'E' in parts[1]:
                        lines.append(base + 'e')
                    if 'S' in parts[1]:
                        lines.append(base + 's')
                    if 'N' in parts[1]:
                        lines.append(base + 'n')
                else:
                    lines.append(line)
        return lines, separator

    def _lazy_init(self):
        if self._initialized:
            return
        with self._init_lock:
            if not self._initialized:
                self._init_maps()

    def _init_maps(self):
        """(called once, with the lock held; the maps are built before
        they are published, so other threads never see incomplete maps)"""
        m_start_space = {}
        m_start_no_space = {}
        m_full_space = {}
        m_full_no_space = {}
        from . import jregex
        lines, sep = self._load_words_and_separator()
        self.separator = sep
        sep_re = None if sep == '\t' else jregex.compile(sep)
        for line in lines:
            parts = line.split('\t') if sep_re is None else sep_re.split(line)
            while parts and parts[-1] == '':
                parts.pop()
            if len(parts) != 2 and self.default_tag is None:
                raise ValueError('Invalid format in %s: %r, expected two tab-separated parts' % (self.path, line))
            if len(parts) != 1 and self.default_tag is not None:
                raise ValueError('Invalid format in %s: %r, expected one element with no separator' % (
                    self.path, line))
            original = parts[0]
            tag = self.default_tag if self.default_tag is not None else parts[1]
            contains_space = original.find(' ') > 0
            variants = [original]
            variants.extend(self._lettercase_variants(original, m_full_space if contains_space
                                                      else m_full_no_space))
            for v in variants:
                if not contains_space:
                    fc = v[0:1]
                    if m_start_no_space.get(fc, -1) < len(v):
                        m_start_no_space[fc] = len(v)
                    m_full_no_space[v] = AnalyzedToken(v, tag, original)
                else:
                    toks = java_split(v, ' ')
                    first = toks[0]
                    if m_start_space.get(first, -1) < len(toks):
                        m_start_space[first] = len(toks)
                    m_full_space[v] = AnalyzedToken(v, tag, original)
        self.m_start_space = m_start_space
        self.m_start_no_space = m_start_no_space
        self.m_full_space = m_full_space
        self.m_full_no_space = m_full_no_space
        self._initialized = True

    def _lettercase_variants(self, original, token_map):
        out = []
        if self.allow_all_uppercase and not is_camel_case(original):
            up = original.upper()
            if up not in token_map and original != up:
                out.append(up)
        if self.allow_first_capitalized:
            fc = uppercase_first_char(original)
            if fc not in token_map and original != fc:
                out.append(fc)
            if self.allow_titlecase and len(java_split(original, ' ')) > 1 and all_start_with_lowercase(original):
                naive = _word_utils_capitalize(original)
                if naive != fc and original != naive:
                    out.append(naive)
                smart = titlecase_global(original)
                if smart != fc and smart != naive and original != smart:
                    out.append(smart)
        return out

    def disambiguate(self, sentence):
        self._lazy_init()
        an = sentence.tokens
        output = an
        n = len(an)
        for i in range(n):
            tok = output[i].token
            if len(tok) < 1:
                continue
            k = i + 1
            parts = [tok]
            while k < n and not an[k].is_whitespace:
                parts.append(output[k].token)
                k += 1
            tok = ''.join(parts)
            length = self.m_start_space.get(tok)
            if length is not None:
                final_len = 0
                key = []
                j = i
                len_counter = 0
                while j < n and j - i < MAX_TOKENS_IN_MULTIWORD:
                    if not an[j].is_whitespace:
                        key.append(an[j].token)
                        at = self.m_full_space.get(''.join(key))
                        if at is not None:
                            if at.pos_tag != TAG_FOR_NOT_ADDING_TAGS:
                                if final_len == 0:
                                    output[i].add_reading(AnalyzedToken(an[j].token, at.pos_tag, at.lemma),
                                                          'MULTIWORD_CHUNKER')
                                else:
                                    _prepare_new_reading(at, output[i].token, output[i], False)
                                    _prepare_new_reading(at, an[final_len].token, output[final_len], True)
                            if self.add_ignore_spelling:
                                if final_len == 0:
                                    output[i].ignore_spelling()
                                else:
                                    for m in range(i, final_len + 1):
                                        output[m].ignore_spelling()
                    else:
                        if j > 1 and not an[j - 1].is_whitespace:
                            key.append(' ')
                            len_counter += 1
                        if len_counter == length:
                            break
                    j += 1
                    final_len = j
            if tok[0:1] in self.m_start_no_space:
                j = i
                key = []
                while j < n and not an[j].is_whitespace and j - i < MAX_TOKENS_IN_MULTIWORD:
                    key.append(an[j].token)
                    at = self.m_full_no_space.get(''.join(key))
                    if at is not None:
                        if at.pos_tag != TAG_FOR_NOT_ADDING_TAGS:
                            if i == j:
                                postag = at.pos_tag
                                if not _is_low_priority_tag(postag) or not output[i].has_reading() or \
                                        output[i].is_pos_tag_unknown:
                                    output[i].add_reading(AnalyzedToken(an[j].token, postag, at.lemma),
                                                          'MULTIWORD_CHUNKER')
                            else:
                                _prepare_new_reading(at, an[i].token, output[i], False)
                                _prepare_new_reading(at, an[j].token, output[j], True)
                        if self.add_ignore_spelling:
                            for m in range(i, j + 1):
                                output[m].ignore_spelling()
                    j += 1
        if self.is_remove_previous_tags:
            return AnalyzedSentence(_remove_previous_tags(output))
        return AnalyzedSentence(output)


def _prepare_new_reading(at, token, atrs, is_last):
    tag = '<' + ('/' if is_last else '') + at.pos_tag + '>'
    atrs.add_reading(AnalyzedToken(token, tag, at.lemma), 'MULTIWORD_CHUNKER')
    return atrs


def _is_low_priority_tag(tag):
    return tag == 'NPCN000'


def _remove_previous_tags(a):
    i = 0
    pos_tag = ''
    lemma = ''
    next_pos_tag = ''
    n = len(a)
    while i < n:
        if not a[i].is_whitespace:
            if next_pos_tag:
                nat = AnalyzedToken(a[i].token, next_pos_tag, lemma)
                if a[i].has_pos_tag_and_lemma('</' + pos_tag + '>', lemma):
                    next_pos_tag = ''
                    lemma = ''
                a[i] = AnalyzedTokenReadings.from_old(a[i], [nat], 'HybridDisamb')
            else:
                at = _get_multiword_analyzed_token(a, i)
                if at is not None:
                    pos_tag = at.pos_tag[1:-1]
                    lemma = at.lemma
                    if a[i].has_pos_tag_and_lemma('</' + pos_tag + '>', lemma):
                        a[i].remove_reading(a[i].reading_with_tag_regex(regex.compile(
                            regex.escape('</' + pos_tag + '>'))), 'HybridDisamb')
                        a[i].remove_reading(a[i].reading_with_tag_regex(regex.compile(
                            regex.escape('<' + pos_tag + '>'))), 'HybridDisamb')
                        a[i].add_reading(AnalyzedToken(at.token, pos_tag, lemma), 'HybridDisamb')
                        next_pos_tag = ''
                        lemma = ''
                    else:
                        nat = AnalyzedToken(at.token, pos_tag, lemma)
                        a[i] = AnalyzedTokenReadings.from_old(a[i], [nat], 'HybridDisamb')
                        next_pos_tag = _get_next_pos_tag(pos_tag)
        i += 1
    return a


def _get_multiword_analyzed_token(a, i):
    l = []
    for r in a[i].readings:
        p = r.pos_tag
        if p is not None and p.startswith('<') and p.endswith('>') and not p.startswith('</'):
            l.append(r)
    if not l:
        return None
    selected = None
    max_distance = 0
    for at in l:
        tag = '</' + at.pos_tag[1:]
        clean = at.pos_tag[1:len(at.pos_tag) - 2]
        lemma = at.lemma
        distance = 1
        while i + distance < len(a):
            if a[i + distance].has_pos_tag_and_lemma(tag, lemma):
                if distance > max_distance:
                    max_distance = distance
                    selected = at
                if distance == max_distance and not _is_low_priority_tag(clean):
                    max_distance = distance
                    selected = at
                break
            distance += 1
    return selected


def _get_next_pos_tag(postag):
    if postag.startswith('NC'):
        return 'AQ0' + postag[2:4] + '0'
    if postag.startswith('N '):
        return 'J ' + postag[2:]
    return postag


class MultiWordChunker2:

    def __init__(self, path, allow_first_capitalized=False, remove_other_readings=False, wrap_tag=True):
        self.path = path
        self.allow_first_capitalized = allow_first_capitalized
        self.remove_other_readings = remove_other_readings
        self.tag_format = '<%s>' if wrap_tag else None
        self.token_map = None

    def format_pos_tag(self, pos_tag, position, length):
        return self.tag_format % pos_tag if self.tag_format is not None else pos_tag

    def _lazy_init(self):
        if self.token_map is not None:
            return
        m = {}
        with open(self.path, encoding='utf-8') as f:
            for line in f:
                line = java_trim(line.rstrip('\r\n'))
                if not line or line[0] == '#':
                    continue
                parts = line.split('\t')
                if len(parts) != 2:
                    raise ValueError('Invalid format in %s: %r' % (self.path, line))
                toks = parts[0].split(' ')
                m.setdefault(toks[0], []).append((toks, parts[1]))
        self.token_map = m

    def matches(self, match_text, atr):
        return match_text == atr.token

    def disambiguate(self, sentence):
        self._lazy_init()
        inp = sentence.tokens
        out = inp
        for i in range(1, len(inp)):
            first = inp[i].token
            items = self.token_map.get(first)
            if items is None:
                if self.allow_first_capitalized and is_capitalized_word(first):
                    items = self.token_map.get(lowercase_first_char(first))
                if items is None:
                    continue
            entry = None
            for e in items:
                if self._is_matching(inp, i, e):
                    entry = e
                    break
            if entry is None:
                continue
            toks, tag = entry
            mpos = 0
            ipos = i
            while mpos < len(toks):
                cur = inp[ipos]
                if cur.is_whitespace:
                    ipos += 1
                    continue
                mtag = self.format_pos_tag(tag, mpos, len(toks))
                out[ipos] = self._prepare_new_reading(' '.join(toks), cur.token, cur, mtag)
                mpos += 1
                ipos += 1
        return AnalyzedSentence(out)

    def _is_matching(self, inp, start, entry):
        toks = entry[0]
        j = 1
        i = 1
        while j < len(toks) and start + i < len(inp):
            if inp[start + i].is_whitespace:
                i += 1
                continue
            if not self.matches(toks[j], inp[start + i]):
                return False
            j += 1
            i += 1
        return j == len(toks)

    def _prepare_new_reading(self, lemma, tok, atr, tag):
        new = AnalyzedToken(tok, tag, lemma)
        readings = [] if self.remove_other_readings else list(atr.readings)
        readings.append(new)
        return AnalyzedTokenReadings.from_old(atr, readings, 'MULTIWORD_CHUNKER')


class XmlRuleDisambiguator:
    """Applies the rules from disambiguation.xml (and optionally
    disambiguation-global.xml)."""

    def __init__(self, language, rules):
        from .patterns.ruleset import RuleSet
        self.language = language
        self.rules = rules
        self.rule_set = RuleSet(rules, with_lemma_hints=False)

    def disambiguate(self, sentence):
        # for rule in self.rule_set.rules_for_sentence(sentence): sentence = rule.replace(sentence)
        return self.rule_set.disambiguate(sentence)


class ChainDisambiguator:
    """Runs a list of disambiguators in order (the "hybrid" disambiguators of
    LanguageTool)."""

    def __init__(self, stages):
        self.stages = stages

    def disambiguate(self, sentence):
        for s in self.stages:
            sentence = s.disambiguate(sentence)
        return sentence

    def pre_disambiguate(self, sentence):
        """Disambiguator.preDisambiguate of the stages that have one (the
        identity for the others)"""
        for s in self.stages:
            f = getattr(s, 'pre_disambiguate', None)
            if f is not None:
                sentence = f(sentence)
        return sentence
