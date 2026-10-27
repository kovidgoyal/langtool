"""Tests of the static rule tables (langtool.patterns.static, the generator
tools/gen_rule_tables.py and the C engine working on the tables): the
format, the objects created from the tables (the same as the XML loader's,
with the same sharing), the lazy creation, the detection of stale tables
and the fallback to the XML files, and static rules together with rules
added at runtime."""

import json
import os
import subprocess
import sys
import threading

import pytest

from langtool._base import speedups
from langtool.patterns import static
from langtool.patterns import static_format as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')

pytestmark = pytest.mark.skipif(not static.enabled() or not static.available_languages(),
                                reason='no static rule tables (pure Python mode or built without them)')

ALL = os.environ.get('LANGTOOL_LANGUAGE_TESTS')


def _blob(code):
    return speedups.rule_blob(code, static.table_path(code))


def _fresh(code):
    from langtool.api import get_language
    from langtool.language import Language
    from langtool.languages import LANGUAGES, resolve_code
    short, vcode = resolve_code(code)
    d = LANGUAGES[short]
    vdef = next(v for v in d['variants'] if v['code'] == vcode)
    return Language(short, d, vdef, get_language)


# --- the format ---

def test_struct_sizes():
    # (the C structs are checked with static assertions against the same sizes)
    assert (F.SM.size, F.POS.size, F.CHUNK.size, F.PT.size, F.HINT.size, F.RULE.size, F.UNIT.size) == \
        (32, 12, 12, 44, 12, 96, 64)
    assert len(F.RULE_FIELDS) == len(F.RULE.format) - 1
    assert len(F.UNIT_FIELDS) == 16


def test_hash_matches_c():
    # the hashes of the tables (computed by the generator in Python) are those of the C engine: the C lookup of a
    # regex program (by its pattern) finds the entries of all the regex rules
    assert F.fnv1a('') == 2166136261 and F.fnv1a('a') == 0xE40C292C
    t = static.tables_for('de')
    rules = t.binding(_fresh('de-DE')).unit_rules(0)[0]
    keys = [r._pattern_src for r in rules if type(r).__name__ == 'RegexPatternRule']
    assert keys
    for pattern, flags in keys:
        assert t.blob.regex_program(pattern, flags) >= 0
    assert t.blob.regex_program('no such pattern', 0) == -1


@pytest.mark.parametrize('code', static.available_languages() if ALL else ['en', 'de', 'eo'])
def test_tables_are_consistent(code):
    blob = _blob(code)
    assert blob.validate() is True
    meta = json.loads(blob.meta())
    assert meta['language'] == code
    info = blob.info()
    assert info['units'] == len(meta['units']) > 0


def test_table_files_are_checked(tmp_path):
    # a table file is mapped and checked: format, size and the build id of this build
    import shutil
    path = static.table_path('eo')
    bid = speedups.rule_blob_build_id('eo')
    assert len(bid) == 32
    blob = speedups.map_rule_table('eo', path, bid)
    assert blob.validate() and blob.info() == _blob('eo').info()
    data = open(path, 'rb').read()

    def bad(content, expected=bid, error=ValueError):
        p = tmp_path / 'x.ltrt'
        if content is None:
            if p.exists():
                p.unlink()
        else:
            p.write_bytes(content)
        with pytest.raises(error):
            speedups.map_rule_table('eo', str(p), expected)
    bad(b'NOTRULES' + data[8:])                       # magic
    bad(data[:8] + b'\x63\0\0\0' + data[12:])        # format version
    bad(data[:-8])                                    # truncated
    bad(data + b'\0' * 8)                             # longer
    bad(data, expected='0' * 32)                      # another build
    bad(b'', error=OSError)                           # empty
    bad(None, error=OSError)                          # missing
    shutil.copy(path, str(tmp_path / 'y.ltrt'))
    assert speedups.map_rule_table('eo', str(tmp_path / 'y.ltrt'), bid).info() == blob.info()
    # the tables of the languages are mapped once per process
    assert _blob('eo') is _blob('eo')
    assert speedups.rule_blob('no-such-language', path) is None


def _run_status(env, code='eo'):
    script = ('import sys, json; sys.path.insert(0, %r)\n'
              'import langtool\nfrom langtool.api import get_language\nfrom langtool.tool import JLanguageTool\n'
              'lt = JLanguageTool(get_language(%r))\n'
              'm = [(x.rule.get_full_id(), x.from_pos) for x in lt.check("Mi estas bona homo. La hundo kuras.")]\n'
              'print(json.dumps([langtool.static_rules_status()[%r], m]))' % (SRC, code, code))
    r = subprocess.run([sys.executable, '-c', script], env=dict(os.environ, **env), capture_output=True, text=True,
                       check=True)
    return json.loads(r.stdout), r.stderr


def test_tables_dir_and_fallback(tmp_path):
    import shutil
    ok, _ = _run_status({})
    assert ok[0] == 'ok'
    # another directory with the files of this build
    d = tmp_path / 'tables'
    d.mkdir()
    shutil.copy(static.table_path('eo'), str(d / 'eo.ltrt'))
    r, _ = _run_status({'LANGTOOL_RULE_TABLES_DIR': str(d)})
    assert r == ok
    # missing, damaged or of another build: the XML files are used (the same results), logged
    for content in (None, b'garbage', open(static.table_path('eo'), 'rb').read()[:-100]):
        if content is None:
            (d / 'eo.ltrt').unlink()
        else:
            (d / 'eo.ltrt').write_bytes(content)
        r, err = _run_status({'LANGTOOL_RULE_TABLES_DIR': str(d), 'LANGTOOL_DISK_CACHE_DIR': str(tmp_path / 'c')})
        assert r[0].startswith('unavailable: ')
        assert r[1] == ok[1]
        assert 'static rule tables of eo not used' in err


def test_damaged_blobs_are_rejected():
    blob = _blob('eo')
    data = bytearray(bytes(memoryview(blob.meta())))  # (any bytes)
    with pytest.raises(ValueError):
        speedups.RuleBlob(b'LTRULES\x00' + b'\0' * 30, 'x')
    with pytest.raises(ValueError):
        speedups.RuleBlob(bytes(data), 'x')


def test_generator(tmp_path):
    # the generator writes the tables of a language, deterministically, readable by the extension
    out = tmp_path / 'rt'
    cmd = [sys.executable, os.path.join(ROOT, 'tools', 'gen_rule_tables.py'), str(out), '--languages', 'eo',
           '--jobs', '1', '--src', SRC]
    subprocess.run(cmd, check=True, capture_output=True)
    b1 = (out / 'eo.ltrt').read_bytes()
    c = (out / 'rule_tables.c').read_text()
    # (the list of the tables of the build with their build ids; the same inputs: the build id of this build)
    bid = speedups.rule_blob_build_id('eo')
    assert '{"eo", "%s"},' % bid in c and '.incbin' not in c
    assert F.HEADER.unpack_from(b1, 0)[5].hex() == bid
    # (up to date: not generated again)
    r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert '(0 generated)' in r.stdout
    os.unlink(str(out / 'eo.stamp'))
    subprocess.run(cmd, check=True, capture_output=True)
    b2 = (out / 'eo.ltrt').read_bytes()
    blob = speedups.RuleBlob(b2, 'eo')
    assert blob.validate()
    # the same as the first generation, except the bytes of the compiled programs of the regular expressions (the
    # regex module does not compile deterministically: e.g. the order of the characters of a first set)
    assert len(b1) == len(b2)
    assert _without_regex_programs(b1) == _without_regex_programs(b2)
    assert speedups.RuleBlob(b1, 'eo').info() == blob.info() == _blob('eo').info()


def _without_regex_programs(b):
    """the blob without the encoded regex programs (at the end of the object data)"""
    import struct
    ns = F.HEADER.unpack_from(b, 0)[4]
    secs = {}
    for k in range(ns):
        sid, off, size, count = F.SECTION.unpack_from(b, F.HEADER.size + k * F.SECTION.size)
        secs[sid] = (off, size, count)
    off, size, count = secs[F.SEC_REGEX]
    first = min((F.REGEX.unpack_from(b, off + i * F.REGEX.size)[3] for i in range(count)), default=None)
    doff, dsize, _ = secs[F.SEC_OBJDATA]
    cut = doff + (first if first is not None else dsize)
    del struct
    return b[:cut] + b[doff + dsize:]


# --- the objects created from the tables ---

PRIMS = (str, int, float, bool, bytes, type(None))


class _Cmp:
    """structural comparison of two object graphs, including which objects are shared (a bijection)"""

    def __init__(self, pairs):
        self.fwd = {}
        self.rev = {}
        self.keep = []
        for a, b in pairs:
            self.fwd[id(a)] = b
            self.rev[id(b)] = a
            self.keep += [a, b]

    def ident(self, a, b, path):
        x = self.fwd.get(id(a))
        y = self.rev.get(id(b))
        if x is None and y is None:
            self.fwd[id(a)] = b
            self.rev[id(b)] = a
            self.keep += [a, b]
            return True
        assert x is b and y is a, '%s: sharing differs' % path
        return False

    def cmp(self, a, b, path='r'):
        from langtool.language import Language
        ta = type(a)
        assert ta is type(b), '%s: %r %r' % (path, ta, type(b))
        if ta in PRIMS:
            assert a == b, '%s: %r %r' % (path, a, b)
            return
        if ta is tuple and path.endswith('.lower_case_values'):
            # (the order comes from iterating a frozenset of strings: random per process in the XML path too)
            assert sorted(a) == sorted(b)
            return
        if ta in (tuple, list):
            if ta is list and not self.ident(a, b, path):
                return
            assert len(a) == len(b), path
            for i, (x, y) in enumerate(zip(a, b)):
                self.cmp(x, y, '%s[%d]' % (path, i))
            return
        if ta in (set, frozenset):
            if ta is set and not self.ident(a, b, path):
                return
            assert a == b, path
            return
        if ta is dict:
            if not self.ident(a, b, path):
                return
            assert list(a) == list(b), path
            for k in a:
                self.cmp(a[k], b[k], '%s{%r}' % (path, k))
            return
        if isinstance(a, type) or callable(a) and ta.__name__ in ('function', 'builtin_function_or_method'):
            assert a is b, path
            return
        if not self.ident(a, b, path) or a is b:
            return
        assert not isinstance(a, Language), path
        if ta.__name__ == 'Pattern':
            assert (a.pattern, a.flags) == (b.pattern, b.flags), path
            return
        if ta is speedups.RuleHints:
            ma, ha, pa = a.__reduce__()[1]
            mb, hb, pb = b.__reduce__()[1]
            assert (ma, pa, len(ha)) == (mb, pb, len(hb)), path
            for x, y in zip(ha, hb):
                assert (x[0], sorted(x[1]), x[2]) == (y[0], sorted(y[1]), y[2]), path
            return
        for n in _attr_names(a):
            self.cmp(getattr(a, n, '<unset>'), getattr(b, n, '<unset>'), '%s.%s' % (path, n))
        da, db = getattr(a, '__dict__', None), getattr(b, '__dict__', None)
        assert (da is None) == (db is None), path
        if da is not None:
            self.cmp(dict(da), dict(db), path + '.__dict__')


def _attr_names(o):
    names = []
    for k in reversed(type(o).__mro__):
        s = k.__dict__.get('__slots__', ())
        if isinstance(s, str):
            s = (s,)
        names.extend(n for n in s if n not in ('__dict__', '__weakref__') and n not in names)
        for m in getattr(k, '__dict__', {}).values():
            if type(m).__name__ == 'member_descriptor' and m.__name__ not in names and m.__name__ != '__weakref__':
                names.append(m.__name__)
    return names


def _compare_unit(t, ui):
    """loads the rule file of the unit from XML and from the tables (with two fresh Language objects) and compares"""
    from langtool.patterns import loader
    from langtool.rules.filters import default_filter_factory
    from langtool.messages import messages_for
    u = t.units[ui]
    la, lb = _fresh(u['loaded_with']), _fresh(u['loaded_with'])
    path = os.path.join(static._PACKAGE_DIR, u['name'])
    if u['kind'] == 'grammar':
        ra, pa = loader.load_pattern_rules(path, la, la.resource_root, default_filter_factory(),
                                           messages_for(la.short_code))
    else:
        ra, pa = loader.load_disambiguation_rules(path, la, la.resource_root, default_filter_factory())
    rb, pb = t.binding(lb).unit_rules(ui)
    assert [tuple(p) for p in pa] == pb
    pairs = [(la, lb), (la.unifier_config, lb.unifier_config)]
    if la.default_variant is la:
        pairs.append((la.disambiguation_unifier_config, lb.disambiguation_unifier_config))
    c = _Cmp(pairs)
    c.cmp(ra, rb, u['name'])
    for cfg in ('unifier_config', 'disambiguation_unifier_config'):
        if cfg == 'disambiguation_unifier_config' and la.default_variant is not la:
            continue
        ca, cb = getattr(la, cfg), getattr(lb, cfg)
        c.cmp(ca.equivalence_features, cb.equivalence_features, cfg)
        assert list(ca.equivalence_types) == list(cb.equivalence_types)
        for k in ca.equivalence_types:
            c.cmp(ca.equivalence_types[k], cb.equivalence_types[k], '%s%r' % (cfg, k))
    assert set(la.pos_token_cache) == set(lb.pos_token_cache)
    for k in la.pos_token_cache:
        c.cmp(la.pos_token_cache[k], lb.pos_token_cache[k], 'pos_token_cache%r' % (k,))
    return len(ra)


@pytest.mark.parametrize('code', static.available_languages() if ALL else ['eo', 'pl', 'ca'])
def test_created_objects_are_identical_to_the_xml_loaders(code, monkeypatch):
    monkeypatch.setenv('LANGTOOL_DISK_CACHE', '0')
    t = static.tables_for(code)
    assert t is not None, static.status()
    n = sum(_compare_unit(t, ui) for ui in range(len(t.units)))
    assert n > 0


def test_lazy_objects_and_sharing():
    from langtool.api import get_language
    from langtool.patterns import string_matcher
    from langtool.tool import JLanguageTool
    lang = _fresh('en-US')
    parts = lang.get_pattern_rule_parts()
    assert any(isinstance(p, static.StaticRules) for p in parts)
    sr = next(p for p in parts if isinstance(p, static.StaticRules))
    assert sr.materialized() == []
    lt = JLanguageTool(lang)
    lt.check('This are a test.')
    created = len(sr.materialized())
    assert 0 < created < len(sr) / 4
    # the objects are created once: the same as those of get_pattern_rules()
    rules = lang.get_pattern_rules()
    assert rules[5] is sr[5] is sr.rule(5)
    assert len(sr.materialized()) == len(sr)
    # the PosTokens are those of the cache of the language, the matchers the interned ones
    for r in rules:
        for pt in r.pattern_tokens or ():
            p = pt.pos_token
            if p is not None and p.pos_tag is not None:
                key = (p.pos_tag, p.pos_pattern is not None, p.negation)
                assert lang.pos_token_cache.get(key) is p
            m = pt.text_matcher
            assert string_matcher.create(m.pattern, m.is_regexp, m.case_sensitive) is m
    # the rules of a group share their anti-patterns, the rules of a category their Category
    by_id = {}
    for r in rules:
        by_id.setdefault(r.get_id(), []).append(r)
    group = next(g for g in by_id.values() if len(g) > 2 and g[0].anti_patterns and
                 len(set(len(r.anti_patterns) for r in g)) == 1)
    assert group[0].anti_patterns[0] is group[1].anti_patterns[0]
    assert group[0].category is group[1].category
    del get_language


def test_no_rule_objects_at_startup():
    from langtool.tool import JLanguageTool
    lang = _fresh('de-DE')
    lt = JLanguageTool(lang)
    parts = [p for p in lang.get_pattern_rule_parts() if isinstance(p, static.StaticRules)]
    assert parts and all(p.materialized() == [] for p in parts)
    assert not lt.get_all_active_rule_ids() == []
    assert all(p.materialized() == [] for p in parts)


# --- stale tables and the fallback ---

def test_stale_tables_are_detected(monkeypatch, caplog):
    static.reset()
    t = static.Tables(_blob('eo'))
    assert t.check() is None
    rel = next(iter(t.meta['files']))
    size, mtime, digest = t.meta['files'][rel]
    t.meta['files'][rel] = [size, mtime + 1, digest]  # (touched: same content)
    assert t.check() is None
    t.meta['files'][rel] = [size + 1, mtime, digest]
    monkeypatch.setattr(static.Tables, 'check', lambda self: '%s changed' % rel)
    with caplog.at_level('WARNING', logger='langtool.static'):
        assert static.tables_for('eo') is None
    assert static.status()['eo'] == 'stale: %s changed' % rel
    assert 'not used' in caplog.text
    # the rules are then loaded from the XML files
    lang = _fresh('eo')
    parts = lang.get_pattern_rule_parts()
    assert parts and not any(isinstance(p, static.StaticRules) for p in parts)
    monkeypatch.undo()
    static.reset()
    assert static.tables_for('eo') is not None
    assert static.status()['eo'] == 'ok'


def test_installed_manifest_is_used(monkeypatch):
    from langtool import diskcache
    t = static.Tables(_blob('eo'))
    hashes = {rel: info[2] for rel, info in t.meta['files'].items()}
    monkeypatch.setattr(diskcache, 'installed_manifest', lambda: {'sha256': 'x', 'hashes': hashes})
    monkeypatch.setattr(os, 'stat', None)  # (no file is looked at)
    assert t.check() is None
    monkeypatch.undo()
    rel = next(iter(hashes))
    hashes[rel] = '0' * 32
    monkeypatch.setattr(diskcache, 'installed_manifest', lambda: {'sha256': 'x', 'hashes': hashes})
    assert t.check() == '%s changed' % rel


def test_static_rules_can_be_disabled():
    code = ('import sys; sys.path.insert(0, %r); from langtool.patterns import static; '
            'from langtool.api import get_language; l = get_language("eo"); p = l.get_pattern_rule_parts(); '
            'print(static.enabled(), any(isinstance(x, static.StaticRules) for x in p), static.status()["eo"])' % SRC)
    env = dict(os.environ, LANGTOOL_STATIC_RULES='0')
    out = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split() == ['False', 'False', 'disabled']


def test_unavailable_filters_fall_back(monkeypatch):
    lang = _fresh('fr')
    t = static.tables_for('fr')
    b = t.binding(lang)
    u = next(k for k, unit in enumerate(t.units) if unit['filters'])
    assert b.unit_ok(u) is None
    monkeypatch.setattr(static, '_filter_available', lambda method, name, language: False)
    b._unit_ok.clear()
    assert 'not available' in b.unit_ok(u)


SENTENCES = {
    'en-US': ['This are a test. He go to school.', 'I has a apple and a orange.', 'Their is a problem here.'],
    'de-DE': ['Das ist ein Test. Ich habe keine Zeit gehabt.', 'Er gehen nach Hause.', 'Der Frau ist nett.'],
    'fr': ['Il sont parti hier.', "C'est un erreur.", 'Je vous aime beaucoup.'],
    'ca-ES': ['Els nens va a escola.', 'Aquest és un exemple.'],
}


def _results(code, env):
    script = ('import sys, json; sys.path.insert(0, %r)\n'
              'from langtool.api import get_language\nfrom langtool.tool import JLanguageTool\n'
              'lt = JLanguageTool(get_language(%r))\nout = []\n'
              'for s in %r:\n'
              '    out.append([(m.rule.get_full_id(), m.from_pos, m.to_pos, m.message, m.suggested_replacements) '
              'for m in lt.check(s)])\n'
              '    out.append([[(t.token, [(r.pos_tag, r.lemma) for r in t.readings], t.immunized) for t in a.tokens] '
              'for a in lt.analyze_text(s)])\n'
              'print(json.dumps(out))' % (SRC, code, SENTENCES[code]))
    r = subprocess.run([sys.executable, '-c', script], env=dict(os.environ, **env), capture_output=True, text=True,
                       check=True)
    return json.loads(r.stdout)


@pytest.mark.parametrize('code', sorted(SENTENCES))
def test_same_results_as_the_xml_rules(code, tmp_path):
    static_r = _results(code, {})
    xml_r = _results(code, {'LANGTOOL_STATIC_RULES': '0', 'LANGTOOL_DISK_CACHE_DIR': str(tmp_path)})
    assert static_r == xml_r
    assert any(static_r[0::2])


# --- static rules with rules added at runtime ---

USER_RULES = '''<?xml version="1.0" encoding="UTF-8"?>
<rules lang="en">
<category id="USER" name="User rules">
<rule id="USER_FOO" name="foo">
  <pattern><token>foo</token><token>bar</token></pattern>
  <message>Use <suggestion>foobar</suggestion>.</message>
  <example correction="foobar">This is <marker>foo bar</marker>.</example>
</rule>
</category>
</rules>
'''


def test_static_and_user_rules_together(tmp_path):
    from langtool.patterns.loader import load_pattern_rules
    from langtool.rules.filters import default_filter_factory
    from langtool.tool import JLanguageTool
    lang = _fresh('en-US')
    lt = JLanguageTool(lang)
    text = 'This are a foo bar.'
    before = [m.rule.get_id() for m in lt.check(text)]
    assert before and 'USER_FOO' not in before
    p = tmp_path / 'user.xml'
    p.write_text(USER_RULES)
    rules, _ = load_pattern_rules(str(p), lang, lang.resource_root, default_filter_factory())
    lt.add_rule(rules[0])
    ids = [m.rule.get_id() for m in lt.check(text)]
    assert 'USER_FOO' in ids and set(before) <= set(ids)
    assert lt.get_all_rules()[-1] is rules[0]
    # a static rule can be disabled and removed
    sid = before[0]
    lt.disable_rule(sid)
    assert sid not in [m.rule.get_id() for m in lt.check(text)]
    lt.enable_rule(sid)
    m = next(m for m in lt.check(text) if m.rule.get_id() == sid)
    lt.remove_rule(m.rule)
    assert m.rule not in lt.get_all_rules()
    after = [x.rule for x in lt.check(text)]
    assert m.rule not in after and rules[0] in after
    # the list of the user rules: all the rule objects
    n = len(lt.get_all_rules())
    assert len(lt.builtin_rules) + len(lt.user_rules) == n
    assert [x.rule for x in lt.check(text)] == after
    lt.user_rules = []
    lt._rule_set_cache.clear()
    assert all(x.rule in lt.builtin_rules for x in lt.check(text))


def test_rules_with_and_active_ids():
    from langtool.tool import JLanguageTool
    lang = _fresh('fr')
    lt = JLanguageTool(lang)
    ids = lt.get_all_active_rule_ids()
    found = lt.rules_with(['CET_CE'], ['CAT_ELISION'])
    assert found and all(r.get_id() == 'CET_CE' or r.category.id == 'CAT_ELISION' for r in found)
    full = [r for r in lt.get_all_rules() if r.get_id() == 'CET_CE' or
            (r.category is not None and r.category.id == 'CAT_ELISION')]
    assert found == full
    assert ids == [r.get_id() for r in lt.get_all_active_rules()]


def test_variant_defaults():
    from langtool.tool import JLanguageTool
    lang = _fresh('es-AR')
    enabled = lang.get_default_enabled_rules_for_variant()
    disabled = set(lang.get_default_disabled_rules_for_variant())
    if not (enabled or disabled):
        pytest.skip('no variant defaults')
    lt = JLanguageTool(lang)
    # (applied to the rules created later, as JLanguageTool applies them to all of them in the XML path)
    found = [r for r in lt.rules_with(disabled | set(enabled))]
    assert found
    assert not [i for i in lt.get_all_active_rule_ids() if i in disabled]
    for r in lt.get_all_rules():
        rid = getattr(r, 'get_id', lambda: None)()
        if rid in disabled:
            assert r.default_off
        elif rid in enabled:
            assert not r.default_off


def test_threads():
    from langtool.tool import JLanguageTool
    lang = _fresh('en-US')
    lt = JLanguageTool(lang)
    texts = ['This are a test number %d. He go to school.' % i for i in range(20)]
    expected = [[(m.rule.get_full_id(), m.from_pos) for m in lt.check(t)] for t in texts]
    errors = []

    def run():
        try:
            for _ in range(3):
                got = [[(m.rule.get_full_id(), m.from_pos) for m in lt.check(t)] for t in texts]
                assert got == expected
        except Exception as e:  # pragma: no cover
            errors.append(e)
    ts = [threading.Thread(target=run) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errors


def test_regex_programs():
    from langtool import jregex
    t = static.tables_for('de')
    assert t.regex_programs_usable()
    rx = [r for r in t.binding(_fresh('de-DE')).unit_rules(0)[0] if type(r).__name__ == 'RegexPatternRule']
    pattern, flags = rx[0]._pattern_src
    data = static.regex_program(pattern, flags)
    assert data is not None
    jregex._cache.pop((pattern, flags), None)
    r = jregex.compile(pattern, flags)
    import regex
    assert r.pattern == regex.compile('(?-f)' + jregex.translate(pattern, flags),
                                      regex.V1 | (regex.IGNORECASE if flags & jregex.IGNORECASE else 0)).pattern


def test_sentence_match_functions():
    from langtool.tool import JLanguageTool
    lang = _fresh('en-US')
    lt = JLanguageTool(lang)
    rs = lt._active_rule_set('DEFAULT')
    assert rs.static_parts()
    sentence = lt.analyze_text('This are a test. He go to school.')[0]
    funcs = rs.sentence_match_functions(sentence)
    via_functions = [m for f in funcs for m in f(sentence)]
    direct = rs.match_sentence(sentence)
    key = lambda m: (m.rule.get_full_id(), m.from_pos, m.to_pos, m.message)
    assert [key(m) for m in via_functions] == [key(m) for m in direct]
    assert direct


def test_status_function():
    import langtool
    st = langtool.static_rules_status()
    assert set(st) == set(static.available_languages())
    static.tables_for('en')
    assert langtool.static_rules_status()['en'] == 'ok'
