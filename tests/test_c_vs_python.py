"""Differential test: the C extension (_speedups) must give exactly the same
results as the pure Python implementation (LANGTOOL_PURE_PYTHON=1). Both are
run in subprocesses on example sentences of the grammar rules of several
languages (covering the C paths: the rule selection with the hints, the
matching of pattern rules with unification and token references, the
disambiguation and the anti-patterns). The rule matches and the analyzed
(disambiguated) sentences are compared. The C extension matches the rules
of the built-in languages on the static rule tables (langtool.patterns.static);
it is also run with them disabled (the rules loaded from the XML files,
matched with the rule objects), which must give the same results."""

import html
import json
import os
import re
import subprocess
import sys

import pytest

from conftest import require_dictionaries

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'src')
RULES = os.path.join(SRC, 'langtool', 'data', 'rules')

SENTENCES_PER_LANGUAGE = 300
SPELL_CHECK_LANGUAGES = ('en-US', 'de-DE')
SPELL_CHECK_SENTENCES = 25
LANGUAGES = (('en-US', 'en'), ('pl-PL', 'pl'), ('de-DE', 'de'), ('fr', 'fr'), ('ca-ES', 'ca'), ('es', 'es'),
             ('pt-PT', 'pt'), ('uk-UA', 'uk'), ('nl', 'nl'), ('ru-RU', 'ru'), ('gl-ES', 'gl'))

_EXAMPLE = re.compile(r'<example\b[^>]*>(.*?)</example>', re.S)


def example_sentences(lang, n=SENTENCES_PER_LANGUAGE):
    """Every k-th <example> sentence of rules/<lang>/grammar*.xml (n sentences)"""
    xml = ''
    for name in sorted(os.listdir(os.path.join(RULES, lang))):
        if name.startswith('grammar') and name.endswith('.xml'):
            with open(os.path.join(RULES, lang, name), encoding='utf-8') as f:
                xml += f.read()
    xml = re.sub(r'<!--.*?-->', '', xml, flags=re.S)
    out = []
    for m in _EXAMPLE.finditer(xml):
        s = m.group(1).replace('<marker>', '').replace('</marker>', '')
        if '<' in s or re.search(r'&[A-Za-z_][\w.-]*;', html.unescape(s)):
            continue  # nested markup or unresolved custom entities
        s = html.unescape(s).strip()
        if s:
            out.append(s)
    step = max(1, len(out) // n)
    return out[::step][:n]


_RUNNER = r'''
import json, sys
SPELL_CHECK_LANGUAGES = %r
SPELL_CHECK_SENTENCES = %d
sys.path.insert(0, sys.argv[1])
import langtool
data = json.load(sys.stdin)
from langtool.tool import JLanguageTool
from langtool.api import get_language
from langtool.patterns import static
result = {'speedups': langtool.have_speedups(), 'results': {}, 'analysis': {}, 'static': {}}
for code, texts in data.items():
    tool = langtool.LanguageTool(code)
    out = []
    for text in texts:
        out.append([[m.full_rule_id, m.offset, m.length, m.message, m.replacements, m.line, m.column]
                    for m in tool.check(text)])
    result['results'][code] = out
    lt = JLanguageTool(get_language(code))
    result['analysis'][code] = [[str(a) for a in lt.analyze_text(text)] for text in texts[:100]]
    result['static'][code] = static.status().get(get_language(code).short_code)
    if code in SPELL_CHECK_LANGUAGES:
        # Hunspell spell checking (the C ngram suggestion search)
        try:
            spell_tool = langtool.LanguageTool(code, spell_check=True)
        except Exception as e:  # (no Hunspell dictionary)
            result.setdefault('spelling', {})[code] = repr(e)
        else:
            result.setdefault('spelling', {})[code] = [
                [[m.full_rule_id, m.offset, m.length, m.replacements] for m in spell_tool.check(text)]
                for text in texts[:SPELL_CHECK_SENTENCES]]
json.dump(result, sys.stdout)
'''


def _run(texts, pure, static_rules=True):
    env = dict(os.environ)
    env.pop('LANGTOOL_PURE_PYTHON', None)
    env.pop('LANGTOOL_STATIC_RULES', None)
    if pure:
        env['LANGTOOL_PURE_PYTHON'] = '1'
    if not static_rules:
        env['LANGTOOL_STATIC_RULES'] = '0'
    p = subprocess.run([sys.executable, '-c', _RUNNER % (SPELL_CHECK_LANGUAGES, SPELL_CHECK_SENTENCES), SRC], input=json.dumps(texts), capture_output=True,
                       text=True, env=env, timeout=1200)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout)


@pytest.fixture(scope='module')
def texts():
    data = {}
    for code, lang in LANGUAGES:
        require_dictionaries(lang)
        sentences = example_sentences(lang)
        assert len(sentences) >= 200
        # also check some multi sentence / multi paragraph texts
        multi = [' '.join(sentences[i:i + 5]) for i in range(0, 50, 5)]
        multi += ['\n\n'.join(sentences[i:i + 3]) for i in range(50, 80, 3)]
        data[code] = sentences + multi
    return data


@pytest.fixture(scope='module')
def results(texts):
    c = _run(texts, pure=False)
    if not c['speedups']:
        pytest.skip('C extension not available')
    py = _run(texts, pure=True)
    assert py['speedups'] is False
    return c, py


@pytest.fixture(scope='module')
def xml_results(texts, results):
    """the C extension without the static rule tables"""
    x = _run(texts, pure=False, static_rules=False)
    assert all(v in (None, 'disabled') for v in x['static'].values())
    return x


@pytest.mark.parametrize('code', [code for code, _ in LANGUAGES])
def test_c_uses_the_static_tables(results, code):
    from langtool.patterns import static
    if not static.available_languages():
        pytest.skip('built without the static rule tables')
    assert results[0]['static'][code] == 'ok'


@pytest.mark.parametrize('code', [code for code, _ in LANGUAGES])
def test_static_tables_vs_xml_rules(texts, results, xml_results, code):
    c, x = results[0], xml_results
    assert c['results'][code] == x['results'][code]
    assert c['analysis'][code] == x['analysis'][code]


@pytest.mark.parametrize('code', [code for code, _ in LANGUAGES])
def test_c_vs_python(texts, results, code):
    c, py = results[0]['results'], results[1]['results']
    assert len(c[code]) == len(py[code]) == len(texts[code])
    diffs = []
    for text, mc, mp in zip(texts[code], c[code], py[code]):
        if mc != mp:
            diffs.append('%r:\n  C:      %r\n  Python: %r' % (text, mc, mp))
    assert not diffs, '%d differences:\n' % len(diffs) + '\n'.join(diffs[:20])
    # sanity check: the example sentences contain errors that are found
    assert sum(1 for m in py[code] if m) > 50


@pytest.mark.parametrize('code', [code for code, _ in LANGUAGES])
def test_c_vs_python_analysis(texts, results, code):
    c, py = results[0]['analysis'], results[1]['analysis']
    assert len(c[code]) == len(py[code]) == min(100, len(texts[code]))
    diffs = []
    for text, ac, ap in zip(texts[code], c[code], py[code]):
        if ac != ap:
            diffs.append('%r:\n  C:      %r\n  Python: %r' % (text, ac, ap))
    assert not diffs, '%d differences:\n' % len(diffs) + '\n'.join(diffs[:10])


@pytest.mark.parametrize('code', SPELL_CHECK_LANGUAGES)
def test_c_vs_python_spell_check(texts, results, code):
    c, py = results[0].get('spelling', {}), results[1].get('spelling', {})
    assert c.get(code) == py.get(code)
