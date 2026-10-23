"""Differential test: the C extension (_speedups) must give exactly the same
results as the pure Python implementation (LANGTOOL_PURE_PYTHON=1). Both are
run in subprocesses on example sentences of the English and Polish grammar
rules."""

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

_EXAMPLE = re.compile(r'<example\b[^>]*>(.*?)</example>', re.S)


def example_sentences(lang, n=SENTENCES_PER_LANGUAGE):
    """Every k-th <example> sentence of rules/<lang>/grammar.xml (n sentences)"""
    with open(os.path.join(RULES, lang, 'grammar.xml'), encoding='utf-8') as f:
        xml = f.read()
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
sys.path.insert(0, sys.argv[1])
import langtool
data = json.load(sys.stdin)
result = {'speedups': langtool.have_speedups(), 'results': {}}
for code, texts in data.items():
    tool = langtool.LanguageTool(code)
    out = []
    for text in texts:
        out.append([[m.full_rule_id, m.offset, m.length, m.message, m.replacements, m.line, m.column]
                    for m in tool.check(text)])
    result['results'][code] = out
json.dump(result, sys.stdout)
'''


def _run(texts, pure):
    env = dict(os.environ)
    env.pop('LANGTOOL_PURE_PYTHON', None)
    if pure:
        env['LANGTOOL_PURE_PYTHON'] = '1'
    p = subprocess.run([sys.executable, '-c', _RUNNER, SRC], input=json.dumps(texts), capture_output=True,
                       text=True, env=env, timeout=1200)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout)


@pytest.fixture(scope='module')
def texts():
    require_dictionaries('en')
    require_dictionaries('pl')
    data = {}
    for code, lang in (('en-US', 'en'), ('pl-PL', 'pl')):
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
    return c['results'], py['results']


@pytest.mark.parametrize('code', ['en-US', 'pl-PL'])
def test_c_vs_python(texts, results, code):
    c, py = results
    assert len(c[code]) == len(py[code]) == len(texts[code])
    diffs = []
    for text, mc, mp in zip(texts[code], c[code], py[code]):
        if mc != mp:
            diffs.append('%r:\n  C:      %r\n  Python: %r' % (text, mc, mp))
    assert not diffs, '%d differences:\n' % len(diffs) + '\n'.join(diffs[:20])
    # sanity check: the example sentences contain errors that are found
    assert sum(1 for m in py[code] if m) > 50
