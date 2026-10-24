"""Port of org.languagetool.tagging.ga.IrishTaggerTest and
org.languagetool.tagging.disambiguation.rules.ga.IrishDisambiguationRuleTest,
plus checks of the guessing of IrishTagger."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, disambiguation_rules
from langtool.lang.ga.tagging import IrishTagger
from langtool.tokenizers import WordTokenizer
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('ga')


@pytest.fixture(scope='module')
def tagger():
    return get_language('ga').tagger


def _null(s):
    return 'null' if s is None else s


def _is_word(token):
    # TestTools.isWord
    return any(is_letter(c) or is_digit(c) for c in token)


def _as_strings(readings):
    # TestTools.getAsStrings
    return sorted('%s/[%s]%s' % (t.token, _null(t.lemma), _null(t.pos_tag)) for t in readings)


def _my_assert(text, expected, tokenizer, tagger):
    # TestTools.myAssert(input, expected, tokenizer, tagger)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_dictionary(tagger):
    """IrishTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    entries, _ = tagger.dictionary.count_entries()
    assert entries > 0


def test_tagger(tagger):
    """IrishTaggerTest.testTagger"""
    assert isinstance(tagger, IrishTagger)
    tokenizer = WordTokenizer()
    _my_assert('nonexistingword', 'nonexistingword/[null]null', tokenizer, tagger)
    _my_assert('bhí sé anseo',
               'bhí/[bí]Noun:Fem:Com:Sg:DefArt|bhí/[bí]Noun:Fem:Com:Sg:Len|bhí/[bí]Noun:Fem:Gen:Sg:Len|'
               'bhí/[bí]Noun:Fem:Voc:Sg:Len|bhí/[bí]Verb:VI:PastInd:Len -- sé/[is]Cop:Pres:Pron:Pers:3P:Sg:Masc|'
               'sé/[sé]Noun:Masc:Com:Sg|sé/[sé]Noun:Masc:Com:Sg:DefArt|sé/[sé]Noun:Masc:Com:Sg:Ecl|'
               'sé/[sé]Noun:Masc:Gen:Sg|sé/[sé]Noun:Masc:Gen:Sg:Ecl|sé/[sé]Num:Card|sé/[sé]Num:Card:Ecl|'
               'sé/[sé]Pron:Pers:3P:Sg:Masc:Sbj -- anseo/[anseo]Adv:Loc', tokenizer, tagger)
    _my_assert('t-athair', 't-athair/[athair]Noun:Masc:Com:Sg:DefArt', tokenizer, tagger)
    _my_assert('tAthair', 'tAthair/[athair]Noun:Masc:Com:Sg:DefArt', tokenizer, tagger)
    _my_assert('nAthair', 'nAthair/[athair]Noun:Fem:Com:Sg:Ecl|nAthair/[athair]Noun:Masc:Com:Sg:Ecl', tokenizer,
               tagger)
    _my_assert('t-seomra', 't-seomra/[null]null|t-seomra/[seomra]Noun:Masc:Com:Sg:DefArt:MorphError', tokenizer,
               tagger)


def test_guessing(tagger):
    """the suffix guesses of Utils.morphWord; unknown words get a null
    reading too when the uppercase-first form is not known either (or the
    word is not lowercase), positions of the readings"""
    tokens = tagger.tag(['caimiléaracht', 'Caimiléaracht', 'tSeomra'])
    assert [r.start_pos for r in tokens] == [0, 13, 26]
    assert _as_strings(tokens[0].readings) == [
        'caimiléaracht/[caimiléireacht]Noun:Fem:Com:Sg:MorphError', 'caimiléaracht/[null]null']
    assert _as_strings(tokens[1].readings) == [
        'Caimiléaracht/[caimiléireacht]Noun:Fem:Com:Sg:MorphError', 'Caimiléaracht/[null]null']
    assert _as_strings(tokens[2].readings) == ['tSeomra/[seomra]Noun:Masc:Gen:Sg:DefArt']
    # the cached readings are returned for repeated words
    assert _as_strings(tagger.tag(['tSeomra'])[0].readings) == _as_strings(tokens[2].readings)


# --- IrishDisambiguationRuleTest ---

def _my_assert_disambiguated(text, expected, tokenizer, sentence_tokenizer, tagger, disambiguator):
    # TestTools.myAssert(input, expected, tokenizer, sentenceTokenizer, tagger, disambiguator)
    out = []
    for sentence in sentence_tokenizer.tokenize(text):
        tokens = tokenizer.tokenize(sentence)
        a_tokens = tagger.tag([t for t in tokens if _is_word(t)])
        token_array = [AnalyzedTokenReadings([AnalyzedToken('', 'SENT_START', None)], 0)]
        start_pos = 0
        no_whitespace_count = 0
        for token in tokens:
            if _is_word(token):
                pos_tag = a_tokens[no_whitespace_count]
                pos_tag.start_pos = start_pos
                no_whitespace_count += 1
            else:
                pos_tag = tagger.create_null_token(token, start_pos)
            token_array.append(pos_tag)
            start_pos += len(token)
        final_sentence = disambiguator.disambiguate(AnalyzedSentence(token_array))
        out.append(' '.join('|'.join(_as_strings(r.readings)) for r in final_sentence.tokens))
    assert ''.join(out) == expected


def test_disambiguation():
    """IrishDisambiguationRuleTest.testDisambiguation"""
    lang = get_language('ga')
    tagger = IrishTagger(lang.dictionary('ga/irish.dict'), lang.resource_dir)
    tokenizer = WordTokenizer()
    sentence_tokenizer = SRXSentenceTokenizer(lang)
    rules, problems = disambiguation_rules(lang)
    assert not problems
    disambiguator = XmlRuleDisambiguator(lang, rules)

    def my_assert(text, expected):
        _my_assert_disambiguated(text, expected, tokenizer, sentence_tokenizer, tagger, disambiguator)

    my_assert('As sin amach.',
              '/[null]SENT_START As/[as]Prep:Simp  /[null]null sin/[sin]Pron:Dem  /[null]null amach/[amach]Adv:Dir '
              './[null]null')
    my_assert('Dé Luain.',
              '/[null]SENT_START Dé/[Dé]Subst:Noun:Sg  /[null]null Luain/[Luan]Noun:Masc:Gen:Sg|'
              'Luain/[luan]Noun:Masc:Gen:Sg ./[null]null')
    my_assert('á haistriú.',
              '/[null]SENT_START á/[do]Prep:Poss:3P:Sg:Fem:Obj  /[null]null '
              'haistriú/[aistriú]Verbal:Noun:VTI:hPref ./[null]null')
    my_assert('a haon',
              '/[null]SENT_START a/[a]Part:Nm  /[null]null haon/[aon]Num:Card:hPref')
