"""Port of org.languagetool.tagging.MorfologikTaggerTest, CombiningTaggerTest,
ManualTaggerTest (languagetool-standalone) and some extra ManualTagger
checks."""

import os

import pytest

from conftest import DATA
from langtool.fsa import Dictionary
from langtool.tagging import CombiningTagger, ManualTagger, MorfologikTagger

XX = os.path.join(DATA, 'resource', 'xx')
SRC_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'langtool', 'data')


# --- MorfologikTaggerTest ---

def test_morfologik_tag():
    tagger = MorfologikTagger(Dictionary(os.path.join(DATA, 'test.dict')))

    result1 = tagger.tag('lowercase')
    assert len(result1) == 2
    assert result1[0].lemma == 'lclemma'
    assert result1[0].pos_tag == 'POS1'
    assert result1[1].lemma == 'lclemma2'
    assert result1[1].pos_tag == 'POS1a'

    assert len(tagger.tag('Lowercase')) == 0

    result3 = tagger.tag('schön')
    assert len(result3) == 1
    assert result3[0].lemma == 'testlemma'
    assert result3[0].pos_tag == 'POSTEST'

    assert len(tagger.tag('noSuchWord')) == 0


def test_position_with_ignored_chars(demo_lt):
    text = 't­ox te­stx'
    sent = demo_lt.get_raw_analyzed_sentence(text)
    tokens = sent.tokens
    assert tokens[3].token is not None
    assert tokens[3].readings[0].pos_tag == 'SENT_END'
    assert tokens[3].start_pos == text.index('te­st')
    assert tokens[3].end_pos == len(text)


# --- CombiningTaggerTest ---

def _combining_tagger(overwrite, removal_path):
    tagger1 = ManualTagger([os.path.join(XX, 'added1.txt')])
    tagger2 = ManualTagger([os.path.join(XX, 'added2.txt')])
    removal = ManualTagger([os.path.join(XX, removal_path)]) if removal_path is not None else None
    return CombiningTagger(tagger1, tagger2, removal, overwrite)


def _as_string(result):
    return ''.join('%s/%s\n' % (t.lemma, t.pos_tag) for t in result)


def test_combining_tag_no_overwrite():
    tagger = _combining_tagger(False, None)
    assert len(tagger.tag('nosuchword')) == 0
    result = tagger.tag('fullform')
    assert len(result) == 2
    s = _as_string(result)
    assert 'baseform1/POSTAG1' in s
    assert 'baseform2/POSTAG2' in s


def test_combining_tag_overwrite():
    tagger = _combining_tagger(True, None)
    assert len(tagger.tag('nosuchword')) == 0
    result = tagger.tag('fullform')
    assert len(result) == 1
    assert 'baseform2/POSTAG2' in _as_string(result)


def test_combining_tag_removal():
    tagger = _combining_tagger(False, 'removed.txt')
    assert len(tagger.tag('nosuchword')) == 0
    s = _as_string(tagger.tag('fullform'))
    assert 'baseform1/POSTAG1' not in s  # first tagged, but in removed.txt
    assert 'baseform2/POSTAG2' in s


def test_invalid_file():
    # Java: IOException ("Unknown line format ...")
    with pytest.raises(ValueError):
        ManualTagger([os.path.join(XX, 'added-invalid.txt')])


# --- ManualTaggerTest (languagetool-standalone) ---

def test_manual_tagger_de():
    tagger = ManualTagger([os.path.join(SRC_DATA, 'resource', 'de', 'added.txt')])
    assert len(tagger.tag('')) == 0
    assert len(tagger.tag('gibtsnicht')) == 0
    assert str(list(tagger.tag('drunter'))) == '[drunter/ADV:LOK+PRO]'
    # lookup is case sensitive:
    assert len(tagger.tag('Drunter')) == 0


# --- additional ManualTagger checks (behaviour of ManualTagger.loadMapping) ---

def test_manual_tagger_comments_and_separator(tmp_path):
    p = tmp_path / 'added.txt'
    p.write_text('# comment\n'
                 '\n'
                 '  form1\tlemma1\tTAG1  \n'
                 'form1\tlemma1b\tTAG1b # trailing comment\n'
                 '#separatorRegExp=[ ]+\n'
                 'form2   lemma2 TAG2\n', encoding='utf-8')
    tagger = ManualTagger([str(p)])
    assert str(list(tagger.tag('form1'))) == '[lemma1/TAG1, lemma1b/TAG1b]'
    assert str(list(tagger.tag('form2'))) == '[lemma2/TAG2]'
    assert len(tagger.tag('lemma1')) == 0


def test_manual_tagger_rejects_nbsp(tmp_path):
    p = tmp_path / 'added.txt'
    p.write_text('form x\tlemma\tTAG\n', encoding='utf-8')
    with pytest.raises(Exception):
        ManualTagger([str(p)])
