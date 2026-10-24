"""SRX based sentence segmentation.

Port of the algorithm used by net.loomchild.segment (SrxTextIterator,
RuleManager, RuleMatcher) as used by LanguageTool's SRXSentenceTokenizer,
including the subtle semantics of Java regex regions (opaque, anchoring
bounds) that affect how rules match.
"""

import threading

from lxml import etree

from . import jregex

SRX_NS = '{http://www.lisa.org/srx20}'


class SrxRule:
    __slots__ = ('is_break', 'before', 'after')

    def __init__(self, is_break, before, after):
        self.is_break = is_break
        self.before = before
        self.after = after


class SrxDocument:

    def __init__(self, path):
        self.cascade = True
        self.language_rules = {}
        self.language_maps = []
        self._rule_managers = {}
        self._patterns = {}
        self._lock = threading.Lock()
        self._parse(path)

    def _parse(self, path):
        tree = etree.parse(path)
        root = tree.getroot()

        def local(el):
            return etree.QName(el).localname

        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            name = local(el)
            if name == 'header':
                self.cascade = el.get('cascade') == 'yes'
            elif name == 'languagerule':
                rules = []
                for r in el:
                    if not isinstance(r.tag, str) or local(r) != 'rule':
                        continue
                    before = after = ''
                    for c in r:
                        if not isinstance(c.tag, str):
                            continue
                        if local(c) == 'beforebreak':
                            before = ''.join(c.itertext())
                        elif local(c) == 'afterbreak':
                            after = ''.join(c.itertext())
                    rules.append(SrxRule(r.get('break') != 'no', before, after))
                self.language_rules[el.get('languagerulename')] = rules
            elif name == 'languagemap':
                self.language_maps.append((jregex.compile(el.get('languagepattern')), el.get('languagerulename')))

    def get_language_rule_names(self, language_code):
        names = []
        for pat, name in self.language_maps:
            if pat.fullmatch(language_code):
                names.append(name)
                if not self.cascade:
                    break
        return names

    def compile(self, pattern):
        p = self._patterns.get(pattern)
        if p is None:
            p = self._patterns[pattern] = jregex.compile(pattern, jregex.UNICODE_CHARACTER_CLASS)
        return p

    def rule_manager(self, language_code):
        names = tuple(self.get_language_rule_names(language_code))
        rm = self._rule_managers.get(names)
        if rm is None:
            with self._lock:
                rm = self._rule_managers.get(names)
                if rm is None:
                    rm = self._rule_managers[names] = RuleManager(self, names)
        return rm

    def segment(self, text, language_code):
        return list(SrxTextIterator(self, language_code, text))


def _caret_to_G(pattern):
    """Replace ^ anchors (outside character classes) by \\G: in Java the
    exception patterns are matched against a region starting at the break
    position with anchoring bounds, so ^ matches only there."""
    out = []
    i = 0
    n = len(pattern)
    depth = 0
    while i < n:
        c = pattern[i]
        if c == '\\':
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if depth:
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
            out.append(c)
        elif c == '[':
            depth = 1
            out.append(c)
            if pattern.startswith('^', i + 1):
                out.append('^')
                i += 1
        elif c == '^':
            out.append('\\G')
        else:
            out.append(c)
        i += 1
    return ''.join(out)


class _BreakRule:
    __slots__ = ('rule', 'before', 'after', 'after_needs_slice', 'exception')

    def __init__(self, doc, rule, exception):
        self.rule = rule
        self.before = doc.compile(rule.before)
        self.after = doc.compile(rule.after)
        a = rule.after
        self.after_needs_slice = '^' in a.replace('[^', '') or '(?<' in a or a.startswith('\\b') or a.startswith('\\B')
        self.exception = exception


class RuleManager:

    def __init__(self, doc, names):
        self.break_rules = []
        exception_parts = []
        for name in names:
            for rule in doc.language_rules.get(name, ()):
                if rule.is_break:
                    if exception_parts:
                        exc = jregex.compile('|'.join(exception_parts), jregex.UNICODE_CHARACTER_CLASS)
                    else:
                        exc = None
                    self.break_rules.append(_BreakRule(doc, rule, exc))
                else:
                    # (the before pattern is in a lookbehind: with the transparent bounds of the
                    # exception matcher, Java's lookbehind sets the region start to 0, so ^
                    # matches at the start of the text there; in the lookahead it matches at the
                    # break position, the region start)
                    s = '(?:'
                    if rule.before:
                        s += '(?<=' + rule.before + ')'
                    if rule.after:
                        s += '(?=' + _caret_to_G(rule.after) + ')'
                    s += ')'
                    exception_parts.append(s)


class _RuleMatcher:
    """Emulates loomchild RuleMatcher with java.util.regex.Matcher
    semantics."""

    __slots__ = ('br', 'text', 'n', 'base', 'sub', 'first', 'last', 'bstart', 'bend', 'break_pos', 'found')

    def __init__(self, br, text):
        self.br = br
        self.text = text
        self.n = len(text)
        self.base = 0
        self.sub = text
        self.first = -1
        self.last = 0
        self.found = True
        self.bstart = self.bend = self.break_pos = 0

    def find(self, start=None):
        if start is not None:
            # region(start, len): resets the matcher
            self.base = start
            self.sub = self.text[start:]
            self.first = -1
            self.last = 0
        self.found = False
        br = self.br
        sub = self.sub
        sublen = len(sub)
        while not self.found:
            nxt = self.last
            if nxt == self.first:
                nxt += 1
            if nxt > sublen:
                return False
            m = br.before.search(sub, nxt)
            if m is None:
                self.first, self.last = -1, sublen + 1
                return False
            self.first, self.last = m.start(), m.end()
            bend = self.base + m.end()
            if br.after_needs_slice:
                am = br.after.match(self.text[bend:])
                if am is not None:
                    self.found = True
                    self.break_pos = bend + am.start()
            else:
                am = br.after.match(self.text, bend)
                if am is not None:
                    self.found = True
                    self.break_pos = am.start()
            if self.found:
                self.bstart = self.base + m.start()
                self.bend = bend
        return True


class SrxTextIterator:

    def __init__(self, doc, language_code, text):
        self.text = text
        self.rm = doc.rule_manager(language_code)

    def __iter__(self):
        text = self.text
        n = len(text)
        start = 0
        matchers = []
        for br in self.rm.break_rules:
            m = _RuleMatcher(br, text)
            m.find()
            if m.found:
                matchers.append(m)
        while start < n:
            found = False
            end = start
            while not found:
                min_m = None
                min_pos = None
                for m in matchers:
                    if min_pos is None or m.break_pos < min_pos:
                        min_pos = m.break_pos
                        min_m = m
                if min_m is None:
                    found = True
                    end = n
                else:
                    end = min_m.break_pos
                    if end > start:
                        exc = min_m.br.exception
                        if exc is None:
                            found = True
                        else:
                            found = exc.match(text, end) is None
                        if found:
                            # cutMatchers
                            keep = []
                            for m in matchers:
                                if m.bstart < end:
                                    m.find(end)
                                    if m.found:
                                        keep.append(m)
                                else:
                                    keep.append(m)
                            matchers = keep
                # moveMatchers
                keep = []
                for m in matchers:
                    alive = True
                    while m.break_pos <= end:
                        m.find()
                        if not m.found:
                            alive = False
                            break
                    if alive:
                        keep.append(m)
                matchers = keep
            yield text[start:end]
            start = end
