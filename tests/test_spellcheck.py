"""Tests of the user-facing spell checking (langtool/spellcheck.py,
langtool/hunspell_dictionaries.py, the spell checking and cache directory
options of the API and the CLI).

The tests with a tiny hand-written Hunspell dictionary (and the demo
language xx-XX) need no network; the tests with the LibreOffice
dictionaries download them (and are skipped if that is not possible)."""

import hashlib
import io
import json
import os
import re
import sys

import pytest

import langtool
from langtool import dictionaries, hunspell_dictionaries as hd, spellcheck
from langtool.hunspell_dictionaries import SpellCheckUnavailable
from conftest import require_dictionaries

AFF = """SET UTF-8
TRY esianrtolcdugmphbyfvkwz'
WORDCHARS 0123456789'
REP 2
REP f ph
REP ph f
SFX S Y 1
SFX S 0 s .
"""

DIC = """21
thank
you
this
is
a
an
and
e
mail
the
test/S
spell
checker/S
phone/S
word/S
with
hello
world
don't
foo
"""


@pytest.fixture(scope='module')
def tiny_dict(tmp_path_factory):
    d = tmp_path_factory.mktemp('hunspell')
    with open(d / 'tiny.aff', 'w', encoding='utf-8') as f:
        f.write(AFF)
    with open(d / 'tiny.dic', 'w', encoding='utf-8') as f:
        f.write(DIC)
    return str(d / 'tiny')


def xx_tool(**kwargs):
    """a LanguageTool for the demo language without its pattern rule that
    matches most sentences"""
    tool = langtool.LanguageTool('xx-XX', **kwargs)
    tool.disable_rule('test_unification_with_negation')
    return tool


@pytest.fixture(scope='module')
def tiny_tool(tiny_dict):
    return xx_tool(spell_check=True, hunspell_dictionaries={'xx-XX': tiny_dict})


@pytest.fixture
def restore_cache_dir():
    yield
    dictionaries.set_cache_dir(None)


def spelling(matches):
    return [(m.context, m.replacements) for m in matches if m.rule_id == 'HUNSPELL_RULE']


# --- the rule with a tiny dictionary (no network) ------------------------------

def test_misspelled_words_and_suggestions(tiny_tool):
    text = 'This is a tset with a fone.'
    matches = [m for m in tiny_tool.check(text) if m.rule_id == 'HUNSPELL_RULE']
    assert [(m.offset, m.length, m.context) for m in matches] == [(10, 4, 'tset'), (22, 4, 'fone')]
    assert matches[0].replacements[0] == 'test'
    assert 'phone' in matches[1].replacements
    m = matches[0]
    assert m.full_rule_id == 'HUNSPELL_RULE'
    assert m.category == 'TYPOS'
    assert m.issue_type == 'Misspelling'
    assert m.message
    assert m.rule_description


def test_wrong_split(tiny_tool):
    """HunspellRule's matches for wrongly split words, but no single letter parts"""
    found = [(m.context, m.replacements) for m in tiny_tool.check('This is thanky ou.')
             if m.rule_id == 'HUNSPELL_RULE']
    assert found == [('thanky ou', ['thank you'])]
    assert [c for c, _ in spelling(tiny_tool.check('This is a ne test.'))] == ['ne']


def test_correct_words(tiny_tool):
    # suffixes, capitalization at the sentence start, apostrophe of WORDCHARS
    assert spelling(tiny_tool.check('Hello world, this is a test with words. Tests with phones.')) == []
    assert spelling(tiny_tool.check("This don't test.")) == []
    assert spelling(tiny_tool.check('HELLO WORLD.')) == []


@pytest.mark.parametrize('text', [
    'This is a test with http://www.exmaple.org/xyzzy and an e-mail fooo@exmaple.org.',  # URLs, e-mails
    'This is a test with abc123 and 3D.',  # digits
    'This is a test with XYZQ and ABCD.',  # all uppercase
    'This is a test with LanguageTool.',
    'This is a test with ... 1234 !!',  # no letters
])
def test_ignored_words(tiny_tool, text):
    assert spelling(tiny_tool.check(text)) == []


def test_ignore_options(tiny_dict):
    tool = xx_tool(spell_check=True, hunspell_dictionaries={'xx': tiny_dict})
    rule = tool.spelling_rule
    try:
        rule.ignore_all_uppercase = False
        rule.ignore_words_with_digits = False
        rule._misspelled_cache.clear()
        assert [c for c, _ in spelling(tool.check('This is XYZQ with abc123.'))] == ['XYZQ', 'abc123']
    finally:
        del rule.ignore_all_uppercase
        del rule.ignore_words_with_digits
        rule._misspelled_cache.clear()


def test_word_lists(tiny_dict):
    rule = spellcheck.HunspellSpellingRule(langtool.LanguageTool('xx-XX')._lt.messages, langtool.get_language('xx'),
                                           tiny_dict + '.aff', tiny_dict + '.dic')
    rule.ensure_initialized()
    assert rule.is_misspelled('zork')
    rule.add_ignore_words('zork')  # spelling.txt / ignore.txt entry
    rule._misspelled_cache.clear()
    assert not rule.is_misspelled('zork')
    assert not rule.is_misspelled('Zork')  # sentence start
    rule.add_prohibited_words(['hello'])  # prohibit.txt entry
    assert rule.is_misspelled('hello')
    # a multi-word entry is ignored only as a phrase
    rule.add_ignore_words('gronk blub')
    lt = xx_tool()._lt
    lt.builtin_rules = [rule]
    lt.user_rules = []
    lt._rule_set_cache.clear()
    found = [m for m in lt.check('This gronk blub test. This gronk test.')]
    assert [(m.from_pos, m.to_pos) for m in found] == [(27, 32)]


def test_runtime_switch(tiny_dict):
    tool = xx_tool(hunspell_dictionaries={'xx-XX': tiny_dict})
    text = 'This is a tset.'
    assert not tool.spell_check and tool.spelling_rule is None and tool.hunspell_dictionary is None
    assert spelling(tool.check(text)) == []
    tool.spell_check = True
    assert tool.hunspell_dictionary == (tiny_dict + '.aff', tiny_dict + '.dic')
    assert [c for c, _ in spelling(tool.check(text))] == ['tset']
    assert 'HUNSPELL_RULE' in {r.id for r in tool.rules()}
    tool.disable_category('TYPOS')
    assert spelling(tool.check(text)) == []
    tool.enable_category('TYPOS')
    assert spelling(tool.check(text))
    tool.disable_rule('HUNSPELL_RULE')
    assert spelling(tool.check(text)) == []
    tool.enable_rule('HUNSPELL_RULE')
    assert spelling(tool.check(text))
    tool.spell_check = False
    assert spelling(tool.check(text)) == []
    assert 'HUNSPELL_RULE' not in {r.id for r in tool.rules()}


def test_rule_shared_and_cached(tiny_dict, tiny_tool):
    other = langtool.LanguageTool('xx-XX', spell_check=True, hunspell_dictionaries={'xx': (tiny_dict + '.aff',
                                                                                         tiny_dict + '.dic')})
    assert other.spelling_rule is tiny_tool.spelling_rule
    rule = other.spelling_rule
    assert rule.suggest('tset')[0] == 'test'
    assert ('tset', 'tset') in rule._suggestion_cache
    assert rule.suggest('tset') == rule.suggest('tset')
    assert rule.is_misspelled('tset') and rule._misspelled_cache['tset'] is True


def test_correct_with_spelling(tiny_tool):
    assert tiny_tool.correct('This is a tset.') == 'This is a test.'


def test_module_level_check(tiny_dict):
    text = 'This is a tset.'
    assert spelling(langtool.check(text, 'xx-XX')) == []
    found = spelling(langtool.check(text, 'xx-XX', spell_check=True, hunspell_dictionaries={'xx': tiny_dict}))
    assert [c for c, _ in found] == ['tset']


# --- dictionary locations -----------------------------------------------------

def test_dictionary_locations(tiny_dict):
    pair = (tiny_dict + '.aff', tiny_dict + '.dic')
    for loc in (tiny_dict, tiny_dict + '.aff', tiny_dict + '.dic', pair, list(pair), pair[::-1]):
        assert hd.normalize_location(loc) == pair
    from pathlib import Path
    assert hd.normalize_location(Path(tiny_dict)) == pair
    with pytest.raises(FileNotFoundError):
        hd.normalize_location(tiny_dict + 'x')
    with pytest.raises(TypeError):
        hd.normalize_location(42)
    # lookup: variant code, then the language code; '_' and case don't matter
    lang = langtool.get_language('xx-XX')
    assert hd.user_dictionary({'xx_xx': tiny_dict}, lang) == pair
    assert hd.user_dictionary({'xx': tiny_dict}, lang) == pair
    assert hd.user_dictionary({'yy': tiny_dict}, lang) is None
    assert hd.user_dictionary(None, lang) is None
    assert hd.user_dictionary({'xx': tiny_dict}, 'xx-XX') == pair


def test_missing_dictionary_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        langtool.LanguageTool('xx-XX', hunspell_dictionaries={'xx': str(tmp_path / 'none')})


def test_spell_check_unavailable():
    # no LibreOffice dictionary for the language
    with pytest.raises(SpellCheckUnavailable) as e:
        langtool.LanguageTool('xx-XX', spell_check=True)
    assert 'xx-XX' in str(e.value) and 'hunspell_dictionaries' in str(e.value)
    assert isinstance(e.value, langtool.DictionaryNotFound)
    tool = langtool.LanguageTool('xx-XX')
    with pytest.raises(SpellCheckUnavailable):
        tool.spell_check = True
    assert not tool.spell_check


def test_not_downloaded_without_download(tmp_path, restore_cache_dir):
    langtool.set_cache_dir(tmp_path)
    with pytest.raises(SpellCheckUnavailable) as e:
        hd.locate('en-US', download_allowed=False)
    assert 'not in the cache' in str(e.value)


# --- the manifest -------------------------------------------------------------

def test_manifest_covers_all_languages():
    m = hd.manifest()
    assert re.fullmatch('[0-9a-f]{40}', m['commit'])
    assert m['repository'] == 'https://github.com/LibreOffice/dictionaries'
    from langtool.language import RULES_DIR
    # (the test languages registered by the tests have no rules in the package)
    codes = {c for c in langtool.languages()
             if os.path.isdir(os.path.join(RULES_DIR, langtool.get_language(c).short_code))}
    assert len(codes) > 50
    assert codes <= set(m['languages'])
    for code, name in m['languages'].items():
        if name is not None:
            assert name in m['dictionaries'], code
    for name, entry in m['dictionaries'].items():
        for ext in ('aff', 'dic'):
            e = entry[ext]
            assert e['url'] == 'https://raw.githubusercontent.com/LibreOffice/dictionaries/%s/%s.%s' % (
                m['commit'], name, ext)
            assert re.fullmatch('[0-9a-f]{64}', e['sha256'])
            assert e['size'] > 0


@pytest.mark.parametrize('code,name', [
    ('en-US', 'en/en_US'), ('en', 'en/en_US'), ('en-GB', 'en/en_GB'), ('en-NZ', 'en/en_GB'),
    ('de-DE', 'de/de_DE_frami'), ('de-CH', 'de/de_CH_frami'), ('de-AT', 'de/de_AT_frami'),
    ('pt-BR', 'pt_BR/pt_BR'), ('pt-PT', 'pt_PT/pt_PT'), ('fr-CA', 'fr_FR/dictionaries/fr'),
    ('ca-ES-valencia', 'ca/dictionaries/ca-valencia'), ('es-AR', 'es/es_AR'), ('nl-BE', 'nl_NL/nl_NL'),
    ('ru', 'ru_RU/ru_RU'), ('sv', 'sv_SE/dictionaries/sv_SE'), ('ja-JP', None), ('zh', None), ('ga-IE', None),
    ('xx-XX', None),
])
def test_mapping(code, name):
    assert hd.dictionary_name(code) == name
    assert hd.dictionary_name(langtool.get_language(code)) == name


def test_available_languages():
    avail = langtool.spell_check_languages()
    assert 'en-US' in avail and 'de-CH' in avail
    unavail = hd.unavailable_languages()
    assert {'ja-JP', 'zh-CN', 'km-KH'} <= set(unavail)
    assert not set(avail) & set(unavail)
    info = langtool.hunspell_dictionary_info('en-NZ')
    assert info['name'] == 'en/en_GB' and 'en_GB' in info['note']
    assert info['dic_url'].endswith('/en/en_GB.dic')
    assert langtool.hunspell_dictionary_info('ja-JP')['name'] is None


def test_download_verifies_checksum(tmp_path, monkeypatch, tiny_dict, restore_cache_dir):
    """download() with a manifest pointing to local files (file: URLs)"""
    def entry(path, sha=None):
        with open(path, 'rb') as f:
            data = f.read()
        return {'url': 'file://' + path, 'sha256': sha or hashlib.sha256(data).hexdigest(), 'size': len(data)}
    m = {'commit': 'f' * 40, 'languages': {'xx-XX': 'tiny/tiny'}, 'notes': {},
         'dictionaries': {'tiny/tiny': {'aff': entry(tiny_dict + '.aff'), 'dic': entry(tiny_dict + '.dic')}}}
    monkeypatch.setattr(hd, 'manifest', lambda: m)
    langtool.set_cache_dir(tmp_path)
    assert not hd.is_cached('xx-XX')
    aff, dic = hd.locate('xx-XX')
    assert aff == os.path.join(str(tmp_path), 'hunspell', 'f' * 12, 'tiny', 'tiny.aff')
    assert hd.is_cached('xx-XX')
    with open(dic, encoding='utf-8') as f:
        assert f.read() == DIC
    # a checksum mismatch is an error, nothing is left in the cache
    m['dictionaries']['tiny/tiny']['dic'] = entry(tiny_dict + '.dic', '0' * 64)
    m['commit'] = 'e' * 40
    with pytest.raises(OSError):
        hd.locate('xx-XX')
    assert not os.path.exists(os.path.join(str(tmp_path), 'hunspell', 'e' * 12, 'tiny', 'tiny.dic'))


# --- the cache directory ------------------------------------------------------

def test_cache_dir(tmp_path, monkeypatch, restore_cache_dir):
    monkeypatch.setenv('LANGTOOL_CACHE_DIR', str(tmp_path / 'env'))
    assert langtool.get_cache_dir() == str(tmp_path / 'env')
    assert dictionaries.cache_dir().startswith(str(tmp_path / 'env') + os.sep)
    langtool.set_cache_dir(tmp_path / 'set')
    assert langtool.get_cache_dir() == str(tmp_path / 'set')
    assert dictionaries.cache_dir() == os.path.join(str(tmp_path / 'set'), 'dictionaries-v1')
    assert hd.hunspell_cache_dir() == os.path.join(str(tmp_path / 'set'), 'hunspell', hd.manifest()['commit'][:12])
    langtool.set_cache_dir(None)
    assert langtool.get_cache_dir() == str(tmp_path / 'env')
    monkeypatch.delenv('LANGTOOL_CACHE_DIR')
    assert langtool.get_cache_dir().endswith('langtool')


def test_cache_dir_argument(tmp_path, restore_cache_dir):
    langtool.LanguageTool('xx-XX', cache_dir=str(tmp_path))
    assert langtool.get_cache_dir() == str(tmp_path)
    assert dictionaries.cache_dir().startswith(str(tmp_path))


def test_cache_dir_used_for_downloads(tmp_path, monkeypatch, restore_cache_dir):
    """the morfologik dictionaries are downloaded to and found in the cache
    directory (a fake manifest with a local jar)"""
    import zipfile
    jar = tmp_path / 'fake.jar'
    with zipfile.ZipFile(jar, 'w') as z:
        z.writestr('org/languagetool/resource/qq/qq.dict', b'dict')
        z.writestr('org/languagetool/resource/qq/qq.info', b'info')
    with open(jar, 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    m = {'version': 1, 'languages': {'qq': [{'url': 'file://' + str(jar), 'sha256': sha, 'size': 0, 'files': [
        {'name': 'qq/qq.dict', 'path': 'org/languagetool/resource/qq/qq.dict'},
        {'name': 'qq/qq.info', 'path': 'org/languagetool/resource/qq/qq.info'}]}]}}
    monkeypatch.setattr(dictionaries, 'manifest', lambda: m)
    monkeypatch.delenv('LANGTOOL_DICT_PATH', raising=False)
    langtool.set_cache_dir(tmp_path / 'cache')
    p = dictionaries.locate('qq/qq.dict')
    assert p == os.path.join(str(tmp_path / 'cache'), 'dictionaries-v1', 'qq', 'qq.dict')
    assert os.path.exists(os.path.join(os.path.dirname(p), 'qq.info'))


# --- CLI ----------------------------------------------------------------------

def run_cli(args, stdin, monkeypatch, capsys):
    from langtool.cli import main
    monkeypatch.setattr(sys, 'stdin', io.StringIO(stdin))
    rc = main(args)
    out = capsys.readouterr()
    return rc, out.out, out.err


def test_cli_spell_check(tiny_dict, monkeypatch, capsys):
    rc, out, _ = run_cli(['check', '-l', 'xx-XX', '-s', '--hunspell-dict', tiny_dict, '--json'],
                         'This is a tset.', monkeypatch, capsys)
    assert rc == 0
    found = [d for d in json.loads(out) if d['rule_id'] == 'HUNSPELL_RULE']
    assert [(d['context'], d['replacements'][0]) for d in found] == [('tset', 'test')]
    rc, out, _ = run_cli(['check', '-l', 'xx-XX', '--hunspell-dict', 'xx=' + tiny_dict, '-s'],
                         'This is a tset.', monkeypatch, capsys)
    assert 'HUNSPELL_RULE' in out and 'Suggestion: test' in out
    # without -s: no spell checking
    rc, out, _ = run_cli(['check', '-l', 'xx-XX', '--hunspell-dict', tiny_dict], 'This is a tset.', monkeypatch,
                         capsys)
    assert 'HUNSPELL_RULE' not in out


def test_cli_spell_check_unavailable(monkeypatch, capsys):
    rc, out, err = run_cli(['check', '-l', 'xx-XX', '-s'], 'This is a tset.', monkeypatch, capsys)
    assert rc == 0
    assert 'warning' in err and 'not available' in err


def test_cli_cache_dir(tmp_path, monkeypatch, capsys, restore_cache_dir):
    rc, out, _ = run_cli(['check', '-l', 'xx-XX', '--cache-dir', str(tmp_path)], 'Test.', monkeypatch, capsys)
    assert langtool.get_cache_dir() == str(tmp_path)
    langtool.set_cache_dir(None)
    rc, out, _ = run_cli(['--cache-dir', str(tmp_path / 'b'), 'check', '-l', 'xx-XX'], 'Test.', monkeypatch,
                         capsys)
    assert langtool.get_cache_dir() == str(tmp_path / 'b')


def test_cli_spelling_languages(monkeypatch, capsys):
    rc, out, _ = run_cli(['spelling-languages'], '', monkeypatch, capsys)
    lines = dict(line.split('\t', 1) for line in out.splitlines())
    assert lines['en-US'].startswith('en/en_US')
    assert lines['ja-JP'].startswith('-')


# --- LibreOffice dictionaries (downloaded) ------------------------------------

def require_hunspell(code):
    if hd.is_cached(code):
        return
    if os.environ.get('LANGTOOL_NO_DOWNLOAD'):
        pytest.skip('Hunspell dictionary for %s not available' % code)
    try:
        hd.download(code)
    except Exception as e:  # network problems etc.
        pytest.skip('could not download the Hunspell dictionary for %s: %s' % (code, e))


@pytest.fixture(scope='module')
def en_tool():
    require_dictionaries('en')
    require_hunspell('en-US')
    return langtool.LanguageTool('en-US', spell_check=True)


def test_english(en_tool):
    found = spelling(en_tool.check('This is an exmaple of a sentense with speling errors.'))
    assert [c for c, _ in found] == ['exmaple', 'sentense', 'speling']
    assert found[0][1][0] == 'example'
    assert found[1][1][0] == 'sentence'
    assert 'spelling' in found[2][1]
    # spelling.txt of LanguageTool, URLs, abbreviations, numbers
    assert spelling(en_tool.check('I use LanguageTool, see https://languagetool.org/xyzzy, NATO and 3rd.')) == []
    # the grammar rules still work
    assert 'HE_VERB_AGR' in [m.rule_id for m in en_tool.check('He go to school.')]


def test_english_variants():
    require_dictionaries('en')
    require_hunspell('en-GB')
    require_hunspell('en-US')
    gb = langtool.LanguageTool('en-GB', spell_check=True)
    us = langtool.LanguageTool('en-US', spell_check=True)
    assert [c for c, _ in spelling(gb.check('The color of the program.'))] == ['color']
    assert spelling(gb.check('The colour of the programme.')) == []
    assert [c for c, _ in spelling(us.check('The colour of the program.'))] == ['colour']


def test_english_prohibited():
    """a word of en/hunspell/prohibit.txt is an error even if Hunspell accepts it"""
    require_dictionaries('en')
    require_hunspell('en-US')
    tool = langtool.LanguageTool('en-US', spell_check=True)
    rule = tool.spelling_rule
    rule.ensure_initialized()
    prohibited = sorted(w for w in rule.words_to_be_prohibited if w.isalpha() and w.islower())
    assert prohibited
    word = next((w for w in prohibited if rule.hunspell.spell(w)), None)
    if word is None:
        pytest.skip('no prohibited word accepted by Hunspell')
    assert rule.is_misspelled(word)


def test_german():
    require_dictionaries('de')
    require_hunspell('de-DE')
    tool = langtool.LanguageTool('de-DE', spell_check=True)
    found = spelling(tool.check('Das ist ein Tset mit einem Fehlr. Ich wohne in Müncen.'))
    assert [c for c, _ in found] == ['Tset', 'Fehlr', 'Müncen']
    assert 'Test' in found[0][1] and 'Fehler' in found[1][1] and found[2][1][0] == 'München'
    assert spelling(tool.check('Die Haustür ist offen, die Donaudampfschifffahrt auch.')) == []


def test_swiss_german():
    require_dictionaries('de')
    require_hunspell('de-CH')
    tool = langtool.LanguageTool('de-CH', spell_check=True)
    assert [c for c, _ in spelling(tool.check('Die Strasse ist gross. Die Straße ist groß.'))] == ['Straße', 'groß']


def test_french():
    require_dictionaries('fr')
    require_hunspell('fr')
    tool = langtool.LanguageTool('fr', spell_check=True)
    found = spelling(tool.check("C'est une phrase avec une fautte d'ortographe."))
    # (the apostrophe is a word character of the dictionary, which suggests the typographic one)
    assert [c for c, _ in found] == ['fautte', "d'ortographe"]
    assert 'faute' in found[0][1] and 'd’orthographe' in found[1][1]
    assert spelling(tool.check("L'été est très chaud aujourd'hui.")) == []


def test_portuguese_brazil():
    require_dictionaries('pt')
    require_hunspell('pt-BR')
    tool = langtool.LanguageTool('pt-BR', spell_check=True)
    found = spelling(tool.check('Esta é uma frase com um erro de ortografia: excessão.'))
    assert [c for c, _ in found] == ['excessão']
    assert 'exceção' in found[0][1]


def test_russian():
    require_dictionaries('ru')
    require_hunspell('ru-RU')
    tool = langtool.LanguageTool('ru-RU', spell_check=True)
    found = spelling(tool.check('Это предложение с ашибкой.'))
    assert [c for c, _ in found] == ['ашибкой']
    assert 'ошибкой' in found[0][1]


def test_suggestion_time_limit(tmp_path):
    """Hunspell.suggest with a time limit (the spelling rule uses one): a MAP
    table with a combinatorial explosion"""
    import time
    from langtool.hunspell import Hunspell
    (tmp_path / 'm.aff').write_text('SET UTF-8\nMAP 1\nMAP aáàâäãå\nTRY a\n', encoding='utf-8')
    (tmp_path / 'm.dic').write_text('2\naaaa\nbanana\n', encoding='utf-8')
    h = Hunspell(str(tmp_path / 'm.dic'), str(tmp_path / 'm.aff'))
    assert h.suggest('aaaáa') == h.suggest('aaaáa', 1.0)
    t = time.time()
    h.suggest('a' * 14 + 'x', 0.2)
    assert time.time() - t < 2
    assert h._deadline is None


def test_rule_suggestion_time_limit(tiny_tool):
    assert tiny_tool.spelling_rule.suggestion_time_limit > 0
