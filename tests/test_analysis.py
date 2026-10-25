"""Port of org.languagetool.AnalyzedTokenTest, AnalyzedTokenReadingsTest and
AnalyzedSentenceTest."""

from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings


# --- AnalyzedTokenTest ---

def test_token_to_string():
    t = AnalyzedToken('word', 'POS', 'lemma')
    assert str(t) == 'lemma/POS'
    assert t.lemma == 'lemma'
    t2 = AnalyzedToken('word', 'POS', None)
    assert str(t2) == 'word/POS'
    assert t2.lemma is None
    assert t2.token == 'word'
    # Java's toString() concatenates a null POS tag as "null"
    assert str(AnalyzedToken('word', None, None)) == 'word/null'
    assert str(AnalyzedTokenReadings(AnalyzedToken('word', None, None))) == 'word[word/null*]'


def test_token_matches():
    t1 = AnalyzedToken('word', 'POS', 'lemma')
    assert not t1.matches(AnalyzedToken('', None, None))
    assert t1.matches(AnalyzedToken('word', None, None))
    assert t1.matches(AnalyzedToken('word', 'POS', None))
    assert t1.matches(AnalyzedToken('word', 'POS', 'lemma'))
    assert not t1.matches(AnalyzedToken('word', 'POS1', 'lemma'))
    assert not t1.matches(AnalyzedToken('word1', 'POS', 'lemma'))
    assert not t1.matches(AnalyzedToken('word', 'POS', 'lemma1'))
    assert t1.matches(AnalyzedToken('', 'POS', 'lemma'))
    assert t1.matches(AnalyzedToken('', None, 'lemma'))


# --- AnalyzedTokenReadingsTest ---

def test_readings_new_tags():
    tr = AnalyzedTokenReadings(AnalyzedToken('word', 'POS', 'lemma'))
    assert tr.is_linebreak is False
    assert tr.is_sentence_end is False
    assert tr.is_paragraph_end is False
    assert tr.is_sentence_start is False
    tr.set_sentence_end()
    assert tr.is_sentence_start is False
    assert tr.is_sentence_end is True
    # test SENT_END or PARA_END added without directly via addReading
    # which is possible e.g. in rule disambiguator
    tr = AnalyzedTokenReadings(AnalyzedToken('word', None, 'lemma'))
    tr.add_reading(AnalyzedToken('word', 'SENT_END', None), '')
    assert tr.is_sentence_end is True
    assert tr.is_paragraph_end is False
    tr.add_reading(AnalyzedToken('word', 'PARA_END', None), '')
    assert tr.is_paragraph_end is True
    assert tr.is_sentence_start is False
    # but you can't add SENT_START to a non-empty token
    # and get isSentStart == true
    tr.add_reading(AnalyzedToken('word', 'SENT_START', None), '')
    assert tr.is_sentence_start is False
    a_tok = AnalyzedToken('word', 'POS', 'lemma')
    a_tok.whitespace_before = True
    tr = AnalyzedTokenReadings(a_tok)
    assert tr.readings[0] == a_tok
    a_tok2 = AnalyzedToken('word', 'POS', 'lemma')
    assert not (a_tok2 == tr.readings[0])
    a_tok3 = AnalyzedToken('word', 'POS', 'lemma')
    a_tok3.whitespace_before = True
    assert tr.readings[0] == a_tok3
    test_readings = AnalyzedTokenReadings(a_tok3)
    test_readings.remove_reading(a_tok3, '')
    assert len(test_readings.readings) == 1
    assert test_readings.token == 'word'
    assert not test_readings.has_pos_tag('POS')
    # now what about removing something that does not belong to testReadings?
    test_readings.leave_reading(a_tok2)
    assert test_readings.token == 'word'
    assert not test_readings.has_pos_tag('POS')

    test_readings.remove_reading(a_tok2, '')
    assert test_readings.token == 'word'
    assert not test_readings.has_pos_tag('POS')


def test_readings_to_string():
    tr = AnalyzedTokenReadings(AnalyzedToken('word', 'POS', 'lemma'))
    assert str(tr) == 'word[lemma/POS*]'
    tr.add_reading(AnalyzedToken('word', 'POS2', 'lemma2'), '')
    assert str(tr) == 'word[lemma/POS*,lemma2/POS2*]'


def test_has_pos_tag():
    tr = AnalyzedTokenReadings(AnalyzedToken('word', 'POS:FOO:BAR', 'lemma'))
    assert tr.has_pos_tag('POS:FOO:BAR')
    assert not tr.has_pos_tag('POS:FOO:bar')
    assert not tr.has_pos_tag('POS:FOO')
    assert not tr.has_pos_tag('xaz')


def test_has_partial_pos_tag():
    tr = AnalyzedTokenReadings(AnalyzedToken('word', 'POS:FOO:BAR', 'lemma'))
    assert tr.has_partial_pos_tag('POS:FOO:BAR')
    assert tr.has_partial_pos_tag('POS:FOO:')
    assert tr.has_partial_pos_tag('POS:FOO')
    assert tr.has_partial_pos_tag(':FOO:')
    assert tr.has_partial_pos_tag('FOO:BAR')

    assert not tr.has_partial_pos_tag('POS:FOO:BARX')
    assert not tr.has_partial_pos_tag('POS:foo:BAR')
    assert not tr.has_partial_pos_tag('xaz')


def test_matches_pos_tag_regex():
    tr = AnalyzedTokenReadings(AnalyzedToken('word', 'POS:FOO:BAR', 'lemma'))
    assert tr.matches_pos_tag_regex('POS:FOO:BAR')
    assert tr.matches_pos_tag_regex('POS:...:BAR')
    assert tr.matches_pos_tag_regex('POS:[A-Z]+:BAR')

    assert not tr.matches_pos_tag_regex('POS:[AB]OO:BAR')
    assert not tr.matches_pos_tag_regex('POS:FOO:BARX')


def test_iteration():
    tr = AnalyzedTokenReadings([AnalyzedToken('word1', None, None), AnalyzedToken('word2', None, None)], 0)
    tokens = [r.token for r in tr]
    assert tokens == ['word1', 'word2']


# --- AnalyzedSentenceTest ---

def _words():
    words = [
        AnalyzedTokenReadings(AnalyzedToken('', 'SENT_START', None)),
        AnalyzedTokenReadings(AnalyzedToken('word', 'POS', 'lemma')),
        AnalyzedTokenReadings(AnalyzedToken('.', 'INTERP', None)),
    ]
    words[2].add_reading(AnalyzedToken('.', 'SENT_END', None), '')
    return words


def test_sentence_to_string():
    sentence = AnalyzedSentence(_words())
    assert str(sentence) == '<S> word[lemma/POS].[./INTERP,</S>]'


def test_sentence_copy():
    words = _words()
    sentence = AnalyzedSentence(words)
    copy_sentence = sentence.copy()
    assert sentence == copy_sentence
    # now change the first sentence
    words[1].immunize(999)  # this would not work if we stored a copy, which we probably should
    assert str(sentence) == '<S> word[lemma/POS{!}].[./INTERP,</S>]'
    assert sentence != copy_sentence


def test_historical_annotations():
    """AnalyzedTokenReadings.getHistoricalAnnotations and
    AnalyzedSentence.getAnnotations: the disambiguator actions are only
    recorded in verbose mode (GlobalConfig.isVerbose())"""
    from langtool import global_config
    atr = AnalyzedTokenReadings([AnalyzedToken('word', 'A', 'w')], 0)
    atr.add_reading(AnalyzedToken('word', 'B', 'w'), 'RULE1')
    assert atr.historical_annotations == ''
    try:
        global_config.set_verbose(True)
        atr = AnalyzedTokenReadings([AnalyzedToken('word', 'A', 'w')], 0)
        atr.add_reading(AnalyzedToken('word', 'B', 'w'), 'RULE1')
        atr.add_reading(AnalyzedToken('word', 'C', 'w'), '')  # not recorded
        atr.remove_reading(AnalyzedToken('word', 'A', 'w'), 'RULE2[1]')
        new = AnalyzedTokenReadings.from_old(atr, [AnalyzedToken('word', 'C', 'w')], 'RULE3')
        assert new.historical_annotations == (
            '\nRULE1: word[w/A*] -> word[w/A*,w/B*]'
            '\nRULE2[1]: word[w/A*,w/B*,w/C*] -> word[w/B*,w/C*]'
            '\nRULE3: word[w/B*,w/C*] -> word[w/C*]')
        # copies keep the history
        assert AnalyzedTokenReadings.from_old(new, new.readings, '').historical_annotations == \
            new.historical_annotations
        start = AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)
        space = AnalyzedTokenReadings([AnalyzedToken(' ', None, None)], 4)
        space.add_reading(AnalyzedToken(' ', 'X', None), 'RULE4')
        sentence = AnalyzedSentence([start, new, space])
        assert sentence.get_annotations() == 'Disambiguator log: \n' + new.historical_annotations + '\n'
    finally:
        global_config.set_verbose(False)
