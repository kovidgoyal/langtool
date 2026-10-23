"""Port of org.languagetool.rules.sv.SwedishTest (LanguageSpecificTest),
org.languagetool.rules.sv.CompoundRuleTest,
org.languagetool.rules.sv.LanguageSpecificSpellcheckerTest,
org.languagetool.tokenizers.sv.SwedishSRXSentenceTokenizerTest,
org.languagetool.tagging.sv.SwedishTaggerTest,
org.languagetool.tagging.disambiguation.sv.SwedishDisambiguationRuleTest and
org.languagetool.synthesis.sv.SwedishSynthesizerTest, plus checks of the
Swedish language definition against org.languagetool.language.Swedish and
the rules of org.languagetool.rules.sv. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedSentence, AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.sv.rules import CompoundRule, WordCoherencyRule
from langtool.messages import messages_for
from langtool.rules.abstract_rules import load_word_coherency_data
from langtool.synthesis import BaseSynthesizer
from langtool.tagging import BaseTagger
from langtool.tokenizers import WordTokenizer
from langtool.tool import JLanguageTool
from langtool.tools import is_digit, is_letter


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('sv')


# --- SwedishTest ---

def test_language():
    """SwedishTest.testLanguage: runTests(new Swedish()) without a demo text;
    the language independent checks are in tests/test_jlanguagetool.py.
    testCoherencyBaseformIsOtherForm: no form of a coherency.txt word
    triggers a match (Java disables all rules except EN_WORD_COHERENCY)"""
    lang = get_language('sv')
    lt = JLanguageTool(lang)
    for rule in lt.get_all_rules():
        lt.disable_rule(rule.get_id())
    lt.enable_rule('EN_WORD_COHERENCY')
    synthesizer = lang.synthesizer
    word_map = load_word_coherency_data(lang.rules_dir + '/coherency.txt')
    assert word_map
    invalid = set()
    for key in word_map:
        for form in synthesizer.synthesize(AnalyzedToken(key, 'fake', key), '.*', True):
            if lt.check(form):
                invalid.add('%s (a form of %s)' % (form, key))
    assert not invalid


def test_spelling_and_colon():
    """SwedishTest.testSpellingAndColon"""
    assert len(JLanguageTool(get_language('sv')).check('Arbeta med var:')) == 0


def test_weekday_and_month_names():
    """SwedishTest.testWeekdayAndMonthNames"""
    lt = JLanguageTool(get_language('sv'))
    assert len(lt.check('På måndag är alla lediga.')) == 0
    assert len(lt.check('På Måndag är alla lediga.')) == 1
    assert len(lt.check('Onsdag är lillördag på många håll.')) == 0
    assert len(lt.check('I oktober kommer ofta den första snön.')) == 0
    assert len(lt.check('I Oktober kommer ofta den första snön.')) == 1
    assert len(lt.check('Septembers färger är sköna.')) == 0


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificSpellcheckerTest checks the hunspell '
                         'spelling.txt/ignore.txt word lists')
def test_language_specific_spellchecker():
    """Port of org.languagetool.rules.sv.LanguageSpecificSpellcheckerTest"""


def test_definition():
    lang = get_language('sv')
    # two countries: getShortCodeWithCountryAndVariant() is just "sv"
    assert lang.code == 'sv'
    assert lang.name == 'Swedish'
    assert lang.countries == ['SE', 'FI']
    # SwedishHybridDisambiguator: chunker.disambiguate(disambiguator.disambiguate(input))
    assert lang.definition['disambiguator'][0] == ('xml', False)
    assert lang.definition['disambiguator'][1][:2] == ('multiword', 'sv/multiwords.txt')
    assert not any(lang.definition['disambiguator'][1][2].values())
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    assert type(lang.word_tokenizer) is WordTokenizer
    tagger = lang.tagger
    assert isinstance(tagger, BaseTagger)
    assert tagger.tag_lowercase_with_uppercase
    synth = lang.synthesizer
    assert isinstance(synth, BaseSynthesizer)
    assert synth.number_speller is not None and synth.roman_numberer is not None
    files = [f.replace('\\', '/').rsplit('/', 2)[-2:] for f in lang.get_rule_file_names()]
    assert files == [['sv', 'grammar.xml']]


def test_relevant_rules():
    lang = get_language('sv')
    rules = lang.get_relevant_rules(messages_for('sv'))
    # getRelevantRules without HunspellRule (spell checking, not ported)
    assert [r.get_id() for r in rules] == [
        'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UNPAIRED_BRACKETS', 'TOO_LONG_PARAGRAPH',
        'UPPERCASE_SENTENCE_START', 'TOO_LONG_SENTENCE', 'WORD_REPEAT_RULE', 'SV_WORD_COHERENCY',
        'WHITESPACE_RULE', 'SENTENCE_WHITESPACE', 'SV_COMPOUNDS']
    assert rules[3].max_words == 150
    assert rules[5].max_words == 40
    assert isinstance(rules[7], WordCoherencyRule)
    assert isinstance(rules[-1], CompoundRule)
    assert not unsupported_components(lang)


# --- WordCoherencyRule ---

def test_word_coherency_rule():
    lang = get_language('sv')
    rule = WordCoherencyRule(messages_for('sv'), lang)
    assert rule.get_id() == 'SV_WORD_COHERENCY'
    assert rule.get_description() == \
        'Enhetlig och konsekvent stavning av ord när det finns stavningsvarianter att välja på.'
    assert [(e.example, e.corrections) for e in rule.incorrect_examples] == [
        ('Det är en blandning av <marker>mejl</marker> och <marker>mail</marker> i det du skriver.', ['mejl'])]
    assert [e.example for e in rule.correct_examples] == [
        'Om du använder enbart <marker>mejl</marker> när du skriver <marker>mejl</marker> blir det mer konsekvent.']
    lt = JLanguageTool(lang)
    m, = rule.match(lt.analyze_text('Det är en blandning av mejl och mail i det du skriver.'))
    assert m.message == "Använd endast en av stavningsvarianterna 'mail' och 'mejl' i en och samma text."
    assert m.suggested_replacements == ['mejl']
    assert (m.from_pos, m.to_pos) == (32, 36)


# --- CompoundRuleTest ---

def _check(lt, rule, expected_errors, text, *exp_suggestions):
    # AbstractCompoundRuleTest.check
    matches = rule.match(lt.get_analyzed_sentence(text))
    assert len(matches) == expected_errors, matches
    if exp_suggestions:
        assert matches[0].suggested_replacements == list(exp_suggestions)


def test_compound_rule():
    """CompoundRuleTest.testRule"""
    lang = get_language('sv')
    lt = JLanguageTool(lang)
    rule = CompoundRule(messages_for('en'), lang, None)
    # correct:
    # _check(lt, rule, 0, 'skit-bra')
    _check(lt, rule, 0, 'IP-Adress')
    _check(lt, rule, 0, 'moll-tonart')
    _check(lt, rule, 0, 'e-mail')
    # incorrect:
    _check(lt, rule, 1, 'skit bra', 'skitbra')
    _check(lt, rule, 1, 'skit-bra', 'skitbra')
    _check(lt, rule, 1, 'IP Adress', 'IP-Adress')
    _check(lt, rule, 1, 'moll tonart', 'moll-tonart', 'molltonart')
    _check(lt, rule, 1, 'e mail', 'e-mail')


def test_compound_rule_properties():
    lang = get_language('sv')
    rule = CompoundRule(messages_for('sv'), lang)
    assert rule.get_id() == 'SV_COMPOUNDS'
    assert rule.get_description() == "Särskrivningar, t.ex. 'e mail' bör skrivas 'e-mail'"
    lt = JLanguageTool(lang)
    m, = rule.match(lt.get_analyzed_sentence('Skicka ett e mail.'))
    assert m.message == 'Dessa ord skrivs samman med bindestreck.'
    m, = rule.match(lt.get_analyzed_sentence('Det var skit bra.'))
    assert m.message == 'Dessa ord skrivs samman.'
    m, = rule.match(lt.get_analyzed_sentence('Det är moll tonart.'))
    assert m.message == 'Dessa ord skrivs samman med eller utan bindestreck.'


# --- SwedishSRXSentenceTokenizerTest ---

def test_tokenize():
    """SwedishSRXSentenceTokenizerTest.testTokenize"""
    stokenizer = SRXSentenceTokenizer(get_language('sv'))

    def test_split(*sentences):
        # TestTools.testSplit
        assert stokenizer.tokenize(''.join(sentences)) == list(sentences)

    test_split('Onkel Toms stuga är en roman skriven av Harriet Beecher Stowe, publicerad den 1852. ',
               'Den handlar om slaveriet i USA sett ur slavarnas perspektiv och bidrog starkt till att slaveriet '
               'avskaffades 1865 efter amerikanska inbördeskriget.')
    test_split(
        'Vi kan leverera varorna alt. snabbt med expressfrakt.',
        'Rapporten innehåller bl.a. statistik och tabeller.',
        'Han kom sent, dvs. att mötet redan hade börjat.',
        'Vi behöver hammare, spik, etc. verktyg för arbetet.',
        'Hör av dig vid ev. problem med datorn.',
        'Den f.d. kollega arbetar nu på ett nytt företag.',
        'Fig. visar sambandet mellan tid och temperatur.',
        'Berättelsen slutar med texten “forts. följer”.',
        'Avtalet gäller fr.o.m. måndag.',
        'Priset anges inkl. moms.',
        'Resultatet är m.a.o. fel.',
        'Orig. version sparades i arkivet.',
        'Vi diskuterade mål, strategier, osv. detaljer.',
        'Han var frånvarande p.g.a. sjukdom.',
        'Vi har satt ett prel. schema för veckan.',
        'Ref. hänvisar till tidigare forskning.',
        'De har resp. ansvar för olika områden.',
        'Han kallar sig en s.k. expert.',
        'Varje exemplar st. kostar fem kronor.',
        'Jag gillar djur, t.ex. hundar och katter.',
        'Vi tar upp övr. frågor på nästa möte.',
        'Vi bjuder på kaffe, te, m.fl. drycker.',
        'Mötet varar t.o.m. fredag.',
        'Vi träffas kl. tre.',
        'Han tog med sig kartor, kompass, m.m. utrustning.',
        'Det var kallt, d.v.s. under noll grader.'
    )


# --- SwedishTaggerTest ---

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
    # (getNoWhitespaceTokens: only the tokens with a letter or digit)
    tokens = [t for t in tokenizer.tokenize(text) if _is_word(t)]
    out = ['|'.join(_as_strings(r.readings)) for r in tagger.tag(tokens)]
    assert ' -- '.join(out) == expected


def test_dictionary():
    """SwedishTaggerTest.testDictionary (TestTools.testDictionary only prints
    warnings for entries without POS tags; check that the dictionary can be
    read completely)"""
    d = get_language('sv').tagger.dictionary
    entries, _ = d.count_entries()
    assert entries > 0


def test_tagger():
    """SwedishTaggerTest.testTagger"""
    tagger = get_language('sv').tagger
    tokenizer = WordTokenizer()
    _my_assert('Det är nog bäst att du får en klubba till',
               'Det/[det]PN -- är/[vara]VB:PRS -- nog/[nog]AB -- bäst/[bra]JJ:S|bäst/[bäst]AB|bäst/[god]JJ:S -- '
               'att/[att]KN -- du/[du]PN -- får/[få]VB:PRS|får/[får]NN:OF:PLU:NOM:NEU|får/[får]NN:OF:SIN:NOM:NEU -- '
               'en/[en]NN:OF:SIN:NOM:UTR|en/[en]PN -- klubba/[klubba]NN:OF:SIN:NOM:UTR|klubba/[klubba]VB:IMP|'
               'klubba/[klubba]VB:INF -- till/[till]AB|till/[till]PP', tokenizer, tagger)

    # en + passant/[null]null
    _my_assert('Hon nämnde, en passant, att det inte var klädsamt',
               'Hon/[hon]PN -- nämnde/[nämna]VB:PRT -- en/[en]NN:OF:SIN:NOM:UTR|en/[en]PN -- passant/[null]null -- '
               'att/[att]KN -- det/[det]PN -- inte/[inte]AB -- var/[var]AB|var/[var]NN:OF:SIN:NOM:NEU|var/[var]PN|'
               'var/[vara]VB:IMP|var/[vara]VB:PRT -- klädsamt/[klädsam]JJ:PN', tokenizer, tagger)

    _my_assert('Nato-vänliga länder har blivit fler.',
               'Nato-vänliga/[null]null -- länder/[land]NN:OF:PLU:NOM:NEU|länder/[länd]NN:OF:PLU:NOM:UTR|'
               'länder/[lända]VB:PRS -- har/[ha]VB:PRS -- blivit/[bli]VB:SUP -- fler/[mången]JJ:K', tokenizer, tagger)
    _my_assert('FN:s nya projekt.',
               'FN/[FN]PM:NOM:ACR -- s/[null]null -- nya/[ny]JJ:BF|nya/[ny]JJ:P -- '
               'projekt/[projekt]NN:OF:PLU:NOM:NEU|projekt/[projekt]NN:OF:SIN:NOM:NEU', tokenizer, tagger)

    _my_assert('Du menar sannolikt "massera" om du inte skriver om masarnas era förstås.',
               'Du/[du]PN -- menar/[mena]VB:PRS -- sannolikt/[sannolik]JJ:PN|sannolikt/[sannolikt]AB -- '
               'massera/[massera]VB:IMP|massera/[massera]VB:INF -- om/[om]AB|om/[om]KN|om/[om]PP -- du/[du]PN -- '
               'inte/[inte]AB -- skriver/[skriva]VB:PRS -- om/[om]AB|om/[om]KN|om/[om]PP -- '
               'masarnas/[mas]NN:BF:PLU:GEN:UTR -- era/[era]NN:OF:SIN:NOM:UTR|era/[era]PN -- '
               'förstås/[förstå]VB:INF:PF|förstås/[förstå]VB:PRS:PF|förstås/[förstås]AB', tokenizer, tagger)


# --- SwedishDisambiguationRuleTest ---

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


def test_chunker():
    """SwedishDisambiguationRuleTest.testChunker"""
    lang = get_language('sv')
    tagger = lang.tagger
    tokenizer = WordTokenizer()
    sentence_tokenizer = SRXSentenceTokenizer(lang)
    disambiguator = MultiWordChunker(lang.resource_path('sv/multiwords.txt'))

    def my_assert(text, expected):
        _my_assert_disambiguated(text, expected, tokenizer, sentence_tokenizer, tagger, disambiguator)

    # fixme! - Still missing SENT_END
    # my_assert('blablabla', '/[null]SENT_START blablabla/[null]SENT_END')

    my_assert('Att testa ... disambiguering',
              '/[null]SENT_START Att/[att]KN  /[null]null testa/[testa]VB:IMP|testa/[testa]VB:INF  /[null]null '
              './[...]<ELLIPS> ./[null]null ./[...]</ELLIPS>  /[null]null/[null]SENT_START '
              'disambiguering/[null]null')

    my_assert('Att testa disambiguering är, en passant, kul.',
              '/[null]SENT_START Att/[att]KN  /[null]null testa/[testa]VB:IMP|testa/[testa]VB:INF  /[null]null '
              'disambiguering/[null]null  /[null]null är/[vara]VB:PRS ,/[null]null  /[null]null '
              'en/[en passant]<NN:OF:SIN:NOM:UTR>|en/[en]NN:OF:SIN:NOM:UTR|en/[en]PN  /[null]null '
              'passant/[en passant]</NN:OF:SIN:NOM:UTR> ,/[null]null  /[null]null kul/[kul]JJ:PU ./[null]null')
    my_assert('Te från Sri Lanka är mycket gott.',
              '/[null]SENT_START Te/[te]NN:OF:NON:NOM:UTR|Te/[te]NN:OF:SIN:NOM:NEU|Te/[te]VB:IMP|Te/[te]VB:INF  '
              '/[null]null från/[från]PP  /[null]null Sri/[Sri Lanka]<PM:NOM>  /[null]null '
              'Lanka/[Sri Lanka]</PM:NOM>  /[null]null är/[vara]VB:PRS  /[null]null '
              'mycket/[mycken]JJ:PN|mycket/[mycket]AB  /[null]null gott/[god]JJ:PN|gott/[gott]AB ./[null]null')
    _my_assert('VW-skandalen tog fuskandet till en ny nivå.',
               'VW-skandalen/[null]null -- tog/[ta]VB:PRT -- fuskandet/[null]null -- till/[till]AB|till/[till]PP -- '
               'en/[en]NN:OF:SIN:NOM:UTR|en/[en]PN -- ny/[ny]JJ:PU -- nivå/[null]null', tokenizer, tagger)

    my_assert('Test ...',
              '/[null]SENT_START Test/[test]NN:OF:PLU:NOM:NEU|Test/[test]NN:OF:SIN:NOM:NEU|'
              'Test/[test]NN:OF:SIN:NOM:UTR  /[null]null ./[...]<ELLIPS> ./[null]null ./[...]</ELLIPS>')
    my_assert('Test 2 ... ',
              '/[null]SENT_START Test/[test]NN:OF:PLU:NOM:NEU|Test/[test]NN:OF:SIN:NOM:NEU|'
              'Test/[test]NN:OF:SIN:NOM:UTR  /[null]null 2/[null]null  /[null]null ./[...]<ELLIPS> ./[null]null '
              './[...]</ELLIPS>  /[null]null')


def test_hybrid_disambiguator():
    """SwedishHybridDisambiguator: the XML rule disambiguator, then the
    multiword chunker"""
    lang = get_language('sv')
    stages = lang.disambiguator
    stages = getattr(stages, 'disambiguators', None) or getattr(stages, 'stages', None)
    assert stages is not None and len(stages) == 2
    assert isinstance(stages[0], XmlRuleDisambiguator)
    assert isinstance(stages[1], MultiWordChunker)
    s = JLanguageTool(lang).get_analyzed_sentence('Te från Sri Lanka är mycket gott.')
    sri = [t for t in s.tokens if t.token == 'Sri'][0]
    assert ('Sri Lanka', '<PM:NOM>') in [(r.lemma, r.pos_tag) for r in sri.readings]


# --- SwedishSynthesizerTest ---

def _dummy_token(s):
    return AnalyzedToken(s, s, s)


def test_synthesize_string_string():
    """SwedishSynthesizerTest.testSynthesizeStringString"""
    synth = get_language('sv').synthesizer
    assert len(synth.synthesize(_dummy_token('blablabla'), 'blablabla')) == 0
    assert synth.synthesize(_dummy_token('nyckel'), 'NN:BF:SIN:GEN:UTR', True) == ['nyckelns']
    assert synth.synthesize(_dummy_token('FN'), 'PM:GEN:ACR', True) == ['FN:s']
    # with regular expressions
    assert synth.synthesize(_dummy_token('stor'), 'JJ:S:BF:.*', True) == ['störste', 'största']
    assert synth.synthesize(_dummy_token('VW'), 'PM:.*:ACR', True) == ['VW:s', 'VW']


def test_synthesize_spell_number():
    """SwedishSynthesizer: BaseSynthesizer with the number speller of
    /sv/sv.sor (values from LanguageTool 6.6)"""
    synth = get_language('sv').synthesizer
    assert synth.synthesize(_dummy_token('21'), '_spell_number_') == ['tjugoett']
    assert synth.synthesize(_dummy_token('2024'), '_spell_number_') == ['tvåtusen tjugofyra']
    assert synth.synthesize(_dummy_token('1999'), '_spell_number_:Roman') == ['MCMXCIX']
