"""Port of org.languagetool.rules.patterns.MatchTest and MatchStateTest"""

import pytest

from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.language import Language
from langtool.languages import LANGUAGES
from langtool.patterns import match as M
from langtool.patterns.match import Match, MatchState, convert_case
from langtool.synthesis import BaseSynthesizer, ManualSynthesizer
from langtool.tagging import ManualTagger
from langtool.tool import JLanguageTool

TEST_DATA = ("# some test data\n"
             "inflectedform11\tlemma1\tPOS1\n"
             "inflectedform121\tlemma1\tPOS2\n"
             "inflectedform122\tlemma1\tPOS2\n"
             "inflectedform123\tlemma1\tPOS3\n"
             "inflectedform2\tlemma2\tPOS1\n")


class ManualTaggerAdapter:
    """Port of org.languagetool.tokenizers.ManualTaggerAdapter"""

    def __init__(self, manual_tagger):
        self.manual_tagger = manual_tagger

    def tag(self, sentence_tokens):
        out = []
        pos = 0
        for word in sentence_tokens:
            readings = [AnalyzedToken(word, tw.pos_tag, tw.lemma) for tw in self.manual_tagger.tag(word)]
            if not readings:
                readings = [AnalyzedToken(word, None, None)]
            out.append(AnalyzedTokenReadings(readings, pos))
            pos += len(word)
        return out

    def create_null_token(self, token, start_pos):
        return AnalyzedTokenReadings(AnalyzedToken(token, None, None), start_pos)

    def create_token(self, token, pos_tag):
        return AnalyzedToken(token, pos_tag, None)


class ManualSynthesizerAdapter(BaseSynthesizer):
    """Port of org.languagetool.synthesis.ManualSynthesizerAdapter"""

    def __init__(self, manual_synthesizer):
        super().__init__(None, None, 'xx')
        self.adapted = manual_synthesizer

    def get_possible_tags(self):
        return list(self.adapted.possible_tags)

    def lookup(self, lemma, pos_tag):
        results = super().lookup(lemma, pos_tag)
        manual_forms = self.adapted.lookup(lemma.lower(), pos_tag)
        if manual_forms:
            results.extend(manual_forms)
        return results


@pytest.fixture(scope='module')
def setup(tmp_path_factory):
    path = tmp_path_factory.mktemp('match') / 'test-data.txt'
    path.write_text(TEST_DATA, encoding='utf-8')
    tagger = ManualTaggerAdapter(ManualTagger([str(path)]))
    synthesizer = ManualSynthesizerAdapter(ManualSynthesizer([str(path)]))
    definition = dict(LANGUAGES['xx'], name='TEST')
    demo = Language('xx', definition, {'code': 'xx-XX'}, lambda code: demo)
    demo._tagger = tagger
    demo._synthesizer = synthesizer
    lt = JLanguageTool(demo)
    return lt, synthesizer


def atr(token, pos_tag, lemma):
    return AnalyzedTokenReadings(AnalyzedToken(token, pos_tag, lemma), 0)


def get_match(pos_tag, pos_tag_replace, case_conversion=M.NONE, include_range=M.INCLUDE_NONE):
    return Match(pos_tag, pos_tag_replace, True, None, None, case_conversion, False, False, include_range)


def tokens_without_whitespace(lt, text):
    return lt.get_analyzed_sentence(text).non_blank_tokens


def java_list(lst):
    return '[' + ', '.join(lst) + ']'


# -- CASE CONVERSION

@pytest.mark.parametrize('conv,pos,pos_repl,token,expected', [
    # testStartUpper
    (M.STARTUPPER, 'POS1', 'POS2', 'inflectedform11', '[Inflectedform121, Inflectedform122]'),
    # testStartLower
    (M.STARTLOWER, 'POS1', 'POS2', 'InflectedForm11', '[inflectedform121, inflectedform122]'),
    # testAllUpper
    (M.ALLUPPER, 'POS1', 'POS2', 'InflectedForm11', '[INFLECTEDFORM121, INFLECTEDFORM122]'),
    # testAllLower
    (M.ALLLOWER, 'POS1', 'POS2', 'InflectedForm11', '[inflectedform121, inflectedform122]'),
    # testPreserveStartUpper
    (M.PRESERVE, 'POS1', 'POS2', 'InflectedForm11', '[Inflectedform121, Inflectedform122]'),
    # testPreserveStartLower
    (M.PRESERVE, 'POS1', 'POS2', 'inflectedForm11', '[inflectedform121, inflectedform122]'),
    # testPreserveAllUpper
    (M.PRESERVE, 'POS1', 'POS2', 'INFLECTEDFORM11', '[INFLECTEDFORM121, INFLECTEDFORM122]'),
    # testPreserveMixed
    (M.PRESERVE, 'POS1', 'POS2', 'inflecTedForm11', '[inflectedform121, inflectedform122]'),
    # testPreserveNoneUpper
    (M.NONE, 'POS1', 'POS2', 'INFLECTEDFORM11', '[inflectedform121, inflectedform122]'),
    # testPreserveNoneLower
    (M.NONE, 'POS1', 'POS2', 'inflectedform11', '[inflectedform121, inflectedform122]'),
    # testPreserveNoneMixed
    (M.NONE, 'POS1', 'POS2', 'inFLectedFOrm11', '[inflectedform121, inflectedform122]'),
])
def test_case_conversion(setup, conv, pos, pos_repl, token, expected):
    lt, synthesizer = setup
    match = get_match(pos, pos_repl, conv)
    state = match.create_state(synthesizer, atr(token, pos, 'Lemma1'))
    assert java_list(state.to_final_string(None)) == expected


@pytest.mark.parametrize('token,expected', [
    ('inflectedform121', '[inflectedform2]'),  # testStaticLemmaPreserveStartLower
    ('InflectedForm121', '[Inflectedform2]'),  # testStaticLemmaPreserveStartUpper
    ('INFLECTEDFORM121', '[INFLECTEDFORM2]'),  # testStaticLemmaPreserveAllUpper
    ('infleCtedForm121', '[inflectedform2]'),  # testStaticLemmaPreserveMixed
])
def test_static_lemma_preserve(setup, token, expected):
    lt, synthesizer = setup
    match = get_match('POS2', 'POS1', M.PRESERVE)
    match.set_lemma_string('lemma2')
    state = match.create_state(synthesizer, atr(token, 'POS2', 'Lemma1'))
    assert java_list(state.to_final_string(None)) == expected


# -- INCLUDE RANGE

SENT = 'inflectedform11 inflectedform2 inflectedform122 inflectedform122'


def test_simple_include_following(setup):
    lt, synthesizer = setup
    match = get_match(None, None, include_range=M.INCLUDE_FOLLOWING)
    state = match.create_state(synthesizer, tokens_without_whitespace(lt, SENT), 1, 3)
    assert java_list(state.to_final_string(None)) == '[inflectedform2 inflectedform122]'


def test_pos_include_following(setup):
    # POS is ignored when using IncludeRange.Following
    lt, synthesizer = setup
    match = get_match('POS2', 'POS33', include_range=M.INCLUDE_FOLLOWING)
    state = match.create_state(synthesizer, tokens_without_whitespace(lt, SENT), 1, 3)
    assert java_list(state.to_final_string(None)) == '[inflectedform2 inflectedform122]'


def test_include_all(setup):
    lt, synthesizer = setup
    match = get_match(None, None, include_range=M.INCLUDE_ALL)
    state = match.create_state(synthesizer, tokens_without_whitespace(lt, SENT), 1, 3)
    assert java_list(state.to_final_string(None)) == '[inflectedform11 inflectedform2 inflectedform122]'


def test_pos_include_all(setup):
    lt, synthesizer = setup
    match = get_match('POS1', 'POS3', include_range=M.INCLUDE_ALL)
    state = match.create_state(synthesizer, tokens_without_whitespace(lt, SENT), 1, 3)
    # Note that in this case the first token has the requested POS (POS3 replaces POS1)
    assert java_list(state.to_final_string(None)) == '[inflectedform123 inflectedform2 inflectedform122]'


# -- MatchStateTest

def test_convert_case():
    # Java: MatchState.convertCase(s, sample, language) of a MatchState created with
    # new Match("", "", false, "", "", conversion, ...); here: convert_case(conversion, s, sample, lang_code)
    state = MatchState(Match('', '', False, '', '', M.STARTUPPER, False, False, M.INCLUDE_NONE), None)
    assert state.match.case_conversion == M.STARTUPPER

    assert convert_case(M.STARTUPPER, None, 'Y', 'en') is None
    assert convert_case(M.STARTUPPER, '', 'Y', 'en') == ''
    assert convert_case(M.STARTUPPER, 'x', 'Y', 'en') == 'X'
    assert convert_case(M.STARTUPPER, 'xxx', 'Yyy', 'en') == 'Xxx'
    # special case for Dutch:
    assert convert_case(M.STARTUPPER, 'ijsselmeer', 'Uppercase', 'nl') == 'IJsselmeer'
    assert convert_case(M.STARTUPPER, 'ijsselmeer', 'lowercase', 'nl') == 'IJsselmeer'
    assert convert_case(M.STARTUPPER, 'ij', 'Uppercase', 'nl') == 'IJ'

    assert convert_case(M.PRESERVE, 'xxx', 'Yyy', 'en') == 'Xxx'
    assert convert_case(M.PRESERVE, 'xxx', 'yyy', 'en') == 'xxx'
    assert convert_case(M.PRESERVE, 'xxx', 'YYY', 'en') == 'XXX'
    # special case for Dutch:
    assert convert_case(M.PRESERVE, 'ijsselmeer', 'Uppercase', 'nl') == 'IJsselmeer'
    assert convert_case(M.PRESERVE, 'ijsselmeer', 'lowercase', 'nl') == 'ijsselmeer'
    assert convert_case(M.PRESERVE, 'ijsselmeer', 'ALLUPPER', 'nl') == 'IJSSELMEER'

    assert convert_case(M.STARTLOWER, 'xxx', 'YYY', 'en') == 'xxx'
    assert convert_case(M.STARTLOWER, 'xxx', 'yyy', 'en') == 'xxx'
    assert convert_case(M.STARTLOWER, 'xxx', 'Yyy', 'en') == 'xxx'
    assert convert_case(M.STARTLOWER, 'XXX', 'Yyy', 'en') == 'xXX'
    assert convert_case(M.STARTLOWER, 'Xxx', 'Yyy', 'en') == 'xxx'
