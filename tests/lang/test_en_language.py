"""Port of org.languagetool.rules.en.EnglishTest (LanguageSpecificTest),
org.languagetool.JLanguageToolTest, org.languagetool.AnnotatedTextBuilderTest,
org.languagetool.SpellIgnoreTest (skipped, spell checking) and
org.languagetool.tools.ToolsTest (language-en), plus checks of the English
language definition against org.languagetool.language.English,
AmericanEnglish, BritishEnglish, AustralianEnglish, CanadianEnglish,
NewZealandEnglish and SouthAfricanEnglish. The language independent parts of
LanguageSpecificTest.runTests are ported in tests/test_jlanguagetool.py
(testReplaceRuleReplacements is not ported, it needs the spell checker).
DynamicMorfologikLanguageTest has no active test in Java."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.disambiguation import MultiWordChunker, XmlRuleDisambiguator
from langtool.extensions import SRXSentenceTokenizer, SimpleSentenceTokenizer, unsupported_components
from langtool.lang.en.chunking import EnglishChunker
from langtool.lang.en.language import filter_rule_matches
from langtool.lang.en.rules import LongSentenceRule, UnitConversionRuleImperial, UnitConversionRuleUS
from langtool.lang.en.spelling import (EnglishMultitokenSpeller, MorfologikAmericanSpellerCheck,
                                       MorfologikAustralianSpellerCheck, MorfologikBritishSpellerCheck,
                                       MorfologikCanadianSpellerCheck, MorfologikNewZealandSpellerCheck,
                                       MorfologikSouthAfricanSpellerCheck, prepare_line_for_speller)
from langtool.lang.en.synthesis import EnglishSynthesizer
from langtool.lang.en.tagging import EnglishTagger
from langtool.lang.en.tokenizers import EnglishWordTokenizer
from langtool.messages import messages_for
from langtool.patterns.pattern_token import PatternToken
from langtool.patterns.rules import PatternRule
from langtool.rules.base import Category, RuleMatch, TextLevelRule
from langtool.tool import AnnotatedText, JLanguageTool, LEVEL_PICKY, PARA_ONLYNONPARA, PARA_ONLYPARA, correct_text

DEMO_TEXT = ('Write or paste your text here too have it checked continuously. Errors will be underlined in different '
             'colours: we will mark seplling errors with red underilnes. Furthermore grammar error\'s are '
             'highlighted in yellow. LanguageTool also marks style issues in a reliable manner by underlining them in '
             'blue. did you know that you can sea synonyms by double clicking a word? Its a impressively versatile '
             'tool, e.g. if youd like to tell a colleague from over sea\'s about what happened at 5 PM in the '
             'afternoon on Monday, 27 May 2007.')


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('en')


# --- EnglishTest ---

def test_demo_text():
    """EnglishTest.testLanguage (testDemoText). Java expects three more matches
    of MORFOLOGIK_RULE_EN_US (for "seplling", "underilnes" and
    "LanguageTool"... after TOO_TO), the spell checker, which is not
    ported"""
    # NOTE: this text needs to be kept in sync with config.ts -> DEMO_TEXTS:
    matches = JLanguageTool(get_language('en-US')).check(DEMO_TEXT)
    assert [m.get_specific_rule_id() for m in matches] == [
        'TOO_TO', 'SENT_START_CONJUNCTIVE_LINKING_ADVERB_COMMA', 'APOS_ARE', 'IN_A_X_MANNER',
        'UPPERCASE_SENTENCE_START', 'DOUBLE_HYPHEN', 'IT_IS', 'EN_A_VS_AN', 'EN_CONTRACTION_SPELLING', 'OVER_SEAS',
        'PM_IN_THE_EVENING', 'EN_DATE_WEEKDAY']


@pytest.mark.skip(reason='spell checking is not ported: LanguageSpecificTest.testReplaceRuleReplacements checks '
                         'that the replacements of the replace rules are accepted by the spell checker')
def test_replace_rule_replacements():
    """EnglishTest.testLanguage (testReplaceRuleReplacements for en-US)"""


def test_repeated_pattern_rules():
    """EnglishTest.testRepeatedPatternRules"""
    lt = JLanguageTool(get_language('en'))
    matches = lt.check('Thank you for all your help. Here is another sentence. Thank you so much for all the fish.')
    assert len(matches) == 1, 'Matches when close together'
    matches = lt.check("Thank you for all your help. This is filler. Here are more words. There needs to be a certain "
                       "distance between sentences so that this doesn't match again. How long does it need to be? The "
                       "default setting is 350 characters. That's quite a lot. Here are some more words to fill up "
                       "this text. Here are some more words to fill up this text. Now here are some more words to fill "
                       "up this text. Thank you so much for all the fish.")
    assert len(matches) == 0, 'No matches when further apart'


def test_messages():
    """EnglishTest.testMessages (Java only prints warnings for British words in
    the messages of the pattern rules): all messages can be read"""
    lt = JLanguageTool(get_language('en-US'))
    from langtool.patterns.rules import AbstractPatternRule
    messages = [r.message for r in lt.get_all_rules() if isinstance(r, AbstractPatternRule)]
    assert messages and all(isinstance(m, str) for m in messages)


# --- JLanguageToolTest ---

def _assert_errors(lt, text, n):
    matches = lt.check(text)
    assert len(matches) == n, "Expected %d errors in test sentence: '%s', but got: %s" % (n, text, matches)


def test_english():
    """JLanguageToolTest.testEnglish (more error-free sentences to deal with
    possible regressions)"""
    lt = JLanguageTool(get_language('en'))
    for text in ('Old values may remain although they are ignored.', 'A test that should not give errors.',
                 'As long as you have hope, a chance remains.', 'A rolling stone gathers no moss.',
                 'Hard work causes fitness.',
                 'Gershwin overlays the slow blues theme from section B in the final “Grandioso.”',
                 'Making ingroup membership more noticeable increases cooperativeness.',
                 'Dog mushing is more of a sport than a true means of transportation.', 'No one trusts him any more.',
                 'A member of the United Nations since 1992, Azerbaijan was elected to membership in the newly '
                 'established Human Rights Council by the United Nations General Assembly on May 9, 2006 (the term '
                 'of office began on June 19, 2006).',
                 'Anatomy and geometry are fused in one, and each does something to the other.',
                 'Certain frogs that lay eggs underground have unpigmented eggs.',
                 "It's a kind of agreement in which each party gives something to the other, Jack said.",
                 'Later, you shall know it better.',
                 'And the few must win what the many lose, for the opposite arrangement would not support markets '
                 'as we know them at all, and is, in fact, unimaginable.',
                 'He explained his errand, but without bothering much to make it plausible, for he felt something '
                 'well up in him which was the reason he had fled the army.',
                 "I think it's better, and it's not a big deal.", 'The files .edu and .htaccess are special',
                 # with hidden characters, separated with annotated text
                 'This\u202d\u202c \u202d\u202cis\u202d\u202c \u202d\u202ca\u202d\u202c \u202d\u202ctest\u202d\u202c '
                 '\u202d\u202csentence,\u202d\u202c \u202d\u202cwith\u202d\u202c \u202d\u202cstrange\u202d\u202c '
                 '\u202d\u202chidden\u202d\u202c \u202d\u202ccharacters.'):
        _assert_errors(lt, text, 0)
    _assert_errors(lt, 'A test test that should give errors.', 1)
    _assert_errors(lt, 'I can give you more a detailed description.', 1)
    _assert_errors(lt, 'This is a sentence.  This is another sentence.', 0)
    _assert_errors(lt, 'This is a sentence.   This is another sentence.', 1)
    assert len(lt.get_all_rules()) > 1000
    _assert_errors(lt, 'The sea ice is highly variable — frozen solid during cold, calm weather and broke ...', 0)
    _assert_errors(lt, 'I can give you more a detailed description.', 1)
    lt.disable_rule('MORE_A_JJ')
    _assert_errors(lt, 'I can give you more a detailed description.', 0)
    _assert_errors(lt, "I've go to go.", 1)
    lt.disable_category('TYPOS')
    _assert_errors(lt, "I've go to go.", 0)
    # Passive voice: repetitions
    # the first match is at a long distance
    _assert_errors(lt, (
        'The territory of Metropolitan France was settled by Celtic tribes known as Gauls. France reached its '
        'political and military zenith in the early 19th century under Napoleon Bonaparte, subjugating much of '
        'continental Europe and establishing the First French Empire. The French Revolutionary and Napoleonic Wars '
        'shaped the course of European and world history. The collapse of the empire initiated a period of relative '
        'decline, in which France endured a tumultuous succession of governments until the founding of the French '
        'Third Republic during the Franco-Prussian War in 1870. Subsequent decades saw a period of optimism, '
        'cultural and scientific flourishing, as well as economic prosperity known as the Belle Époque. France was '
        'one of the major participants of World War I, from which it emerged victorious at great human and economic '
        'cost. It was among the Allied powers of World War II, but was soon occupied by the Axis in 1940. France was '
        'plunged into a series of dynastic conflicts involving England. The second half of the 16th century was '
        'dominated by religious civil wars. The short-lived Fourth Republic was established and later dissolved '
        'during the Algerian War. The current Fifth Republic was formed in 1958 by Charles de Gaulle.'), 0)
    # 4 previous matches within 80 tokens
    # the match for this text is from a picky rule so we need to call check with the correct level
    matches = lt.check('The territory of Metropolitan France was settled by Celtic tribes known as Gauls. France was '
                       'plunged into a series of dynastic conflicts involving England. The second half of the 16th '
                       'century was dominated by religious civil wars. The short-lived Fourth Republic was '
                       'established and later dissolved during the Algerian War. The current Fifth Republic was formed '
                       'in 1958 by Charles de Gaulle. ', level=LEVEL_PICKY)
    assert len(matches) == 1


@pytest.mark.skip(reason='spell checking is not ported: JLanguageToolTest.testPositionsWithEnglish and '
                         'testPositionsWithEnglishTwoLineBreaks check the position of the MORFOLOGIK_RULE_EN_US match '
                         'for "typoh"')
def test_positions_with_english():
    pass


def test_analyzed_sentence():
    """JLanguageToolTest.testAnalyzedSentence"""
    lt = JLanguageTool(get_language('en'))
    # test soft-hyphen ignoring:
    assert str(lt.get_analyzed_sentence('This is a test\u00aded sentence.')) == (
        '<S> This[this/DT,B-NP-singular|E-NP-singular] is[be/VBZ,B-VP] a[a/DT,B-NP-singular] '
        'test\u00aded[tested/JJ,I-NP-singular] sentence[sentence/NN,E-NP-singular].[./.,</S>./PCT,O]')
    # test paragraph ends adding
    assert str(lt.get_analyzed_sentence('\n')) == '<S> </S><P/> '
    # test vertical tab as white space
    a_sentence = lt.get_analyzed_sentence("I'm a cool test\u000Bwith a line")
    assert a_sentence.tokens[9].is_whitespace
    assert a_sentence.tokens[10].whitespace_before


def test_paragraph_rules():
    """JLanguageToolTest.testParagraphRules"""
    lt = JLanguageTool(get_language('en'))
    text = '(This is an quote.\n It ends in the second sentence.'
    # run normally
    assert len(lt.check(text)) == 2
    # run in a sentence-only mode
    matches2 = lt.check(text, False, PARA_ONLYNONPARA)
    assert [m.rule.get_id() for m in matches2] == ['EN_A_VS_AN']
    # run in a paragraph mode - single sentence
    matches3 = lt.check(text, False, PARA_ONLYPARA)
    assert [m.rule.get_id() for m in matches3] == ['EN_UNPAIRED_BRACKETS']
    # run in a paragraph mode - many sentences
    matches4 = lt.check(text, True, PARA_ONLYPARA)
    assert [m.rule.get_id() for m in matches4] == ['EN_UNPAIRED_BRACKETS']


def test_whitespace():
    """JLanguageToolTest.testWhitespace"""
    lt = JLanguageTool(get_language('en'))
    raw = lt.get_raw_analyzed_sentence('Let\'s do a "test", do you understand?')
    cooked = lt.get_analyzed_sentence('Let\'s do a "test", do you understand?')
    # test if there was a change
    assert raw != cooked
    # see if nothing has been deleted
    assert len(raw.tokens) == len(cooked.tokens)
    for a, b in zip(raw.tokens, cooked.tokens):
        assert a.whitespace_before == b.whitespace_before


def test_overlap_filter():
    """JLanguageToolTest.testOverlapFilter"""
    lang = get_language('en')
    category = Category('TEST_ID', 'test category')
    rule1 = PatternRule('id1', lang, [PatternToken('one', True, False, False)], 'desc1', 'msg1', 'shortMsg1')
    rule1.sub_id = '1'
    rule1.category = category
    rule2 = PatternRule('id1', lang, [PatternToken('one', True, False, False), PatternToken('two', True, False, False)],
                        'desc2', 'msg2', 'shortMsg2')
    rule2.sub_id = '2'
    rule2.category = category
    lt = JLanguageTool(lang)
    lt.add_rule(rule1)
    lt.add_rule(rule2)
    rule_matches1 = lt.check('And one two three.')
    assert len(rule_matches1) == 1, 'one overlapping rule must be filtered out'
    assert rule_matches1[0].message == 'msg1'


class _MyTextLevelRule(TextLevelRule):

    def get_id(self):
        return 'MyTextLevelRule'

    def get_description(self):
        return 'Test rule'

    def min_to_check_paragraph(self):
        return -1

    def match(self, sentences, annotated_text=None):
        if 'Foo Bar' in annotated_text.get_global_meta_data('EmailToAddress', ''):
            return [RuleMatch(self, None, 0, 1, 'test message')]
        return []


def test_text_level_rule_with_global_data():
    """JLanguageToolTest.testTextLevelRuleWithGlobalData"""
    lt = JLanguageTool(get_language('en'))
    lt.add_rule(_MyTextLevelRule())
    text1 = AnnotatedText([], {'EmailToAddress': 'Foo Bar <foo@foo.de>'})
    assert len(lt.check(text1)) == 1
    text2 = AnnotatedText([], {'EmailToAddress': 'blah blah <foo@foo.de>'})
    assert len(lt.check(text2)) == 0


def test_advanced_typography():
    """JLanguageToolTest.testAdvancedTypography"""
    lang = get_language('en-US')
    assert lang.to_advanced_typography("The genitive ('s) may be missing.") == 'The genitive (’s) may be missing.'
    assert lang.to_advanced_typography("The word 'Language‘s' is not standard English") == \
        'The word ‘Language‘s’ is not standard English'
    assert lang.to_advanced_typography(
        "Did you mean <suggestion>Language's</suggestion> (straight apostrophe) or "
        '<suggestion>Language’s</suggestion> (curly apostrophe)?') == \
        "Did you mean “Language's” (straight apostrophe) or “Language’s” (curly apostrophe)?"
    assert lang.to_advanced_typography(
        'Did you mean <suggestion>Language’s</suggestion> (curly apostrophe) or '
        "<suggestion>Language's</suggestion> (straight apostrophe)?") == \
        "Did you mean “Language’s” (curly apostrophe) or “Language's” (straight apostrophe)?"
    assert lang.to_advanced_typography('Did you mean <suggestion>|?</suggestion>') == 'Did you mean “|?”'


def test_adapt_suggestions():
    """JLanguageToolTest.testAdaptSuggestions"""
    lt = JLanguageTool(get_language('en-US'))
    matches = lt.check("Whatever their needs, we doesn't never disappoint them.")
    assert matches[0].suggested_replacements == ["n't", ' never']


@pytest.mark.parametrize('code', ['en-US', 'en-AU', 'en-GB', 'en-CA', 'en-ZA', 'en-NZ'])
def test_english_variants(code):
    """JLanguageToolTest.testEnglishVariants"""
    lt = JLanguageTool(get_language(code))
    assert len(lt.check('This is a test.')) == 0
    assert len(lt.check('This is an test.')) == 1


# --- AnnotatedTextBuilderTest, SpellIgnoreTest, ToolsTest ---

def test_annotated_text_builder():
    """AnnotatedTextBuilderTest.test"""
    text = AnnotatedText([(False, 'This is a caf', None), (True, '&eacute;', 'é')])
    assert len(JLanguageTool(get_language('en-US')).check(text)) == 0


@pytest.mark.skip(reason='spell checking is not ported: AnnotatedTextBuilderTest.testWithEmptyFakeContent expects '
                         'the MORFOLOGIK_RULE_EN_GB match for "ths"')
def test_annotated_text_builder_with_empty_fake_content():
    pass


@pytest.mark.skip(reason='spell checking is not ported: SpellIgnoreTest.testIgnore checks the matches of the '
                         'spelling rule and SpellingCheckRule.addIgnoreTokens')
def test_spell_ignore():
    pass


def test_correct_text():
    """ToolsTest.testCorrect"""
    assert correct_text('This is an test.', JLanguageTool(get_language('en'))) == 'This is a test.'


# --- the language definition ---

def test_definition():
    lang = get_language('en')
    assert (lang.code, lang.name, lang.countries) == ('en', 'English', [])
    assert not lang.is_variant()
    assert lang.default_variant is get_language('en-US')
    for code, name, countries in (('en-US', 'English (US)', ['US']), ('en-GB', 'English (GB)', ['GB']),
                                  ('en-AU', 'English (Australian)', ['AU']), ('en-CA', 'English (Canadian)', ['CA']),
                                  ('en-NZ', 'English (New Zealand)', ['NZ']),
                                  ('en-ZA', 'English (South African)', ['ZA'])):
        variant = get_language(code)
        assert (variant.name, variant.countries) == (name, countries)
        assert variant.is_variant()
        assert variant.default_variant is get_language('en-US')
        assert variant.get_default_disabled_rules_for_variant() == []
        assert variant.get_default_enabled_rules_for_variant() == []
    assert isinstance(lang.tagger, EnglishTagger)
    assert isinstance(lang.synthesizer, EnglishSynthesizer)
    assert lang.synthesizer.number_speller is not None
    assert type(lang.word_tokenizer) is EnglishWordTokenizer
    assert isinstance(lang.chunker, EnglishChunker)
    assert lang.post_disambiguation_chunker is None
    # EnglishHybridDisambiguator: the chunkers for spelling_global.txt and en/multiwords.txt, then the
    # XmlRuleDisambiguator (of the default variant en-US) with the global disambiguation rules
    stages = lang.disambiguator.stages
    assert [type(s) for s in stages] == [MultiWordChunker, MultiWordChunker, XmlRuleDisambiguator]
    assert stages[2].language is get_language('en-US')
    # createDefaultSentenceTokenizer() returns an SRXSentenceTokenizer
    st = lang.sentence_tokenizer
    assert isinstance(st, SRXSentenceTokenizer) and not isinstance(st, SimpleSentenceTokenizer)
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in lang.get_rule_file_names()]
    assert files == [['rules', 'en', 'grammar.xml'], ['rules', 'en', 'style.xml']]
    files = [f.replace('\\', '/').rsplit('/', 3)[-3:] for f in get_language('en-GB').get_rule_file_names()]
    assert files == [['rules', 'en', 'grammar.xml'], ['rules', 'en', 'style.xml'], ['en', 'en-GB', 'grammar.xml'],
                     ['en', 'en-GB', 'style.xml']]
    for code, cls in (('en', MorfologikAmericanSpellerCheck), ('en-US', MorfologikAmericanSpellerCheck),
                      ('en-GB', MorfologikBritishSpellerCheck), ('en-AU', MorfologikAustralianSpellerCheck),
                      ('en-CA', MorfologikCanadianSpellerCheck), ('en-NZ', MorfologikNewZealandSpellerCheck),
                      ('en-ZA', MorfologikSouthAfricanSpellerCheck)):
        assert type(get_language(code).get_default_spelling_rule()) is cls
    assert isinstance(lang.get_multitoken_speller(), EnglishMultitokenSpeller)
    assert lang.get_multitoken_speller() is get_language('en-GB').get_multitoken_speller()
    assert lang.ignored_characters_regex.pattern.endswith('[\u00ad]')


def test_typography():
    """English.getOpeningDoubleQuote() etc. and isAdvancedTypographyEnabled()"""
    for code in ('en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-NZ', 'en-ZA'):
        lang = get_language(code)
        assert (lang.get_opening_double_quote(), lang.get_closing_double_quote(), lang.get_opening_single_quote(),
                lang.get_closing_single_quote()) == ('“', '”', '‘', '’')
        assert lang.is_advanced_typography_enabled()
    assert get_language('en').to_advanced_typography('Use "this" or \'that\'.') == 'Use “this” or ‘that’.'


def test_priorities():
    """English.getPriorityForId, BritishEnglish.getPriorityForId and
    getDefaultRulePriorityForStyle"""
    p = get_language('en').get_priority_for_id
    assert p('I_E') == 10
    assert p('SENTENCE_FRAGMENT') == -51
    assert p('TOO_LONG_SENTENCE') == -997
    assert p('TOO_LONG_PARAGRAPH') == -998
    assert p('ALL_UPPERCASE') == -1000
    assert p('EN_COMPOUNDS_PART_TIME') == 2
    assert p('PRP_VBZ') == -2
    assert p('CONFUSION_RULE_X') == -20
    assert p('EN_UPPER_CASE_NGRAM') == -12
    assert p('AI_SPELLING_RULE_X') == -9
    assert p('EN_MULTITOKEN_SPELLING_X') == -9
    assert p('EN_GB_SIMPLE_REPLACE_X') == -5
    assert p('EN_US_SIMPLE_REPLACE_X') == -5
    assert p('QB_EN_OXFORD') == -51
    assert p('EN_SIMPLE_REPLACE_KILOGRAMME') == -49
    assert p('EN_SIMPLE_REPLACE_KILOGRAMMES') == -49
    assert p('AI_HYDRA_LEO_MISSING_COMMA') == -51
    assert p('AI_HYDRA_LEO_CP_YOU_YOUARE_X') == -1
    assert p('AI_HYDRA_LEO_CP_X') == 2
    assert p('AI_HYDRA_LEO_MISSING_TO_X') == -14
    assert p('AI_HYDRA_LEO_X') == -11
    assert p('AI_EN_LECTOR_X') == -11
    assert p('EN_FOR_DE_SPEAKERS_FALSE_FRIENDS_X') == -21
    assert p('SOME_STYLE_RULE') == -50
    assert p('REPETITIONS_STYLE') == -51
    assert p('OXFORD_SPELLING_IZE') == 0
    assert p('OTHER') == 0
    p = get_language('en-GB').get_priority_for_id
    assert (p('OXFORD_SPELLING_ISATION_NOUNS'), p('OXFORD_SPELLING_ISE_VERBS'), p('OXFORD_SPELLING_IZE')) == \
        (-20, -21, -22)
    assert p('I_E') == 10
    for code in ('en-US', 'en-AU', 'en-CA', 'en-NZ', 'en-ZA'):
        assert get_language(code).get_priority_for_id('OXFORD_SPELLING_IZE') == 0
    # getDefaultRulePriorityForStyle: -50 for style rules without other priority
    lang = get_language('en-US')
    rule = next(r for r in JLanguageTool(lang).get_all_rules() if r.get_id() == 'EN_REDUNDANCY_REPLACE')
    assert lang.get_rule_priority(rule) == -510
    rule = next(r for r in JLanguageTool(lang).get_all_rules() if r.get_id() == 'PROFANITY')
    assert lang.get_rule_priority(rule) == 1


_EN_RULES = [
    'COMMA_PARENTHESIS_WHITESPACE', 'DOUBLE_PUNCTUATION', 'UPPERCASE_SENTENCE_START', 'WHITESPACE_RULE',
    'SENTENCE_WHITESPACE', 'WHITESPACE_PARAGRAPH', 'WHITESPACE_PARAGRAPH_BEGIN', 'EMPTY_LINE', 'TOO_LONG_SENTENCE',
    'TOO_LONG_PARAGRAPH', 'PARAGRAPH_REPEAT_BEGINNING_RULE', 'PUNCTUATION_PARAGRAPH_END',
    'PUNCTUATION_PARAGRAPH_END2', 'EN_CONSISTENT_APOS', 'EN_SPECIFIC_CASE', 'EN_UNPAIRED_BRACKETS',
    'EN_UNPAIRED_QUOTES', 'ENGLISH_WORD_REPEAT_RULE', 'EN_A_VS_AN', 'ENGLISH_WORD_REPEAT_BEGINNING_RULE',
    'EN_COMPOUNDS', 'EN_CONTRACTION_SPELLING', 'ENGLISH_WRONG_WORD_IN_CONTEXT', 'EN_DASH_RULE', 'EN_WORD_COHERENCY',
    'EN_DIACRITICS_REPLACE_ORTHOGRAPHY', 'EN_PLAIN_ENGLISH_REPLACE', 'EN_REDUNDANCY_REPLACE', 'EN_SIMPLE_REPLACE',
    'PROFANITY', 'READABILITY_RULE_DIFFICULT', 'READABILITY_RULE_SIMPLE', 'EN_REPEATEDWORDS', 'TOO_OFTEN_USED_VERB_EN',
    'TOO_OFTEN_USED_NOUN_EN', 'TOO_OFTEN_USED_ADJECTIVE_EN']


def test_relevant_rules():
    """English.getRelevantRules (without the spelling and language model
    rules, not ported) and the rules added by the variants"""
    rules = get_language('en').get_relevant_rules(messages_for('en'))
    assert [r.get_id() for r in rules] == _EN_RULES
    assert rules[0].incorrect_examples[0].example == 'We had coffee<marker> ,</marker> cheese and crackers and grapes.'
    assert rules[2].incorrect_examples[0].example == 'This house is old. <marker>it</marker> was built in 1950.'
    assert type(rules[8]) is LongSentenceRule and rules[8].max_words == 40
    assert rules[4].max_spaces == 2
    assert [r.default_off for r in rules[26:28]] == [True, True]
    assert rules[13].default_temp_off
    extra = {'en-US': ['EN_US_SIMPLE_REPLACE', 'METRIC_UNITS_EN_US'],
             'en-GB': ['EN_GB_SIMPLE_REPLACE', 'METRIC_UNITS_EN_IMPERIAL'], 'en-AU': ['METRIC_UNITS_EN_IMPERIAL'],
             'en-CA': ['METRIC_UNITS_EN_IMPERIAL'], 'en-NZ': ['EN_NZ_SIMPLE_REPLACE', 'METRIC_UNITS_EN_IMPERIAL'],
             'en-ZA': []}
    for code, ids in extra.items():
        rules = get_language(code).get_relevant_rules(messages_for('en'))
        assert [r.get_id() for r in rules] == _EN_RULES + ids, code
    us = get_language('en-US').get_relevant_rules(messages_for('en'))
    assert us[-2].path == '/en/en-US/replace.txt' and type(us[-1]) is UnitConversionRuleUS
    gb = get_language('en-GB').get_relevant_rules(messages_for('en'))
    assert gb[-2].path == '/en/en-GB/replace.txt' and type(gb[-1]) is UnitConversionRuleImperial
    for code in ('en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-NZ', 'en-ZA'):
        get_language(code).get_pattern_rules()
        assert not unsupported_components(get_language(code))


def test_filter_rule_matches():
    """English.filterRuleMatches: a whitespace is added to suggestions for
    errors in contractions, duplicates are removed, the matches of
    EN_SIMPLE_REPLACE...GRAMME(S) get the issue type LocaleViolation"""
    lt = JLanguageTool(get_language('en-US'))
    sentence = lt.get_analyzed_sentence("We'll test.")

    class _R(TextLevelRule):
        def get_id(self):
            return 'X'

        def get_description(self):
            return 'x'
    m = RuleMatch(_R(), sentence, 2, 5, 'msg', suggestions=['will', "'ll", ' shall', 'will'])
    m.set_original_error_str("'ll")
    m2 = RuleMatch(_R(), sentence, 0, 2, 'msg', suggestions=['we'])
    m2.set_original_error_str('We')
    out = filter_rule_matches(get_language('en-US'), [m, m2], None, set())
    assert out[0].suggested_replacements == [' will', "'ll", ' shall']
    assert out[1].suggested_replacements == ['we']
    assert m.suggested_replacements == ['will', "'ll", ' shall', 'will']


def test_prepare_line_for_speller():
    """English.prepareLineForSpeller"""
    assert prepare_line_for_speller('word') == ['word']
    assert prepare_line_for_speller('foo bar\tNN') == ['foo bar']
    assert prepare_line_for_speller('foo bar\tJJS # comment') == ['foo bar']
    assert prepare_line_for_speller('foo bar\tVB') == ['']
    assert prepare_line_for_speller('C++') == ['']
    assert prepare_line_for_speller('#') == ['#']


def test_misspelling_check():
    """The misspelling check of the speller rules (the word lists of the
    variants, compounds, ignored words)"""
    us = get_language('en-US').get_default_spelling_rule()
    gb = get_language('en-GB').get_default_spelling_rule()
    assert not us.is_misspelled('color') and us.is_misspelled('colour')
    assert not gb.is_misspelled('colour')
    assert us.is_misspelled('xyzzyq')
    assert not us.is_misspelled('part-time') and us.is_misspelled('part-timx')
    assert not us.is_misspelled('LanguageTool')
    assert us.ignore_word('a')  # ignoreWordsWithLength = 1


def test_spelling_suggestions():
    """The single word suggestions of the speller rules
    (AbstractEnglishSpellerRule: irregular forms, the spellings of the
    other variants, getOnlySuggestions, the curated top suggestions,
    hyphenated words), used by EnglishNumberInWordFilter; the expected
    suggestions are those of MorfologikAmericanSpellerRuleTest"""
    us = get_language('en-US').get_default_spelling_rule()
    for word, expected in (('teached', 'taught'), ('buyed', 'bought'), ('thinked', 'thought'),
                           ('becomed', 'became'), ('begined', 'began'), ('one-diminensional', 'one-dimensional'),
                           ('parple-people-eater', 'purple-people-eater'), ('Abudhabi', 'Abu Dhabi'),
                           ('Casagrande', 'Casa Grande'), ('ELPASO', 'El Paso'), ('Eldorado', 'El Dorado')):
        assert expected in us.get_spelling_suggestions(word), word
    assert us.get_spelling_suggestions('behaviour') == ['behavior']  # British English
    assert get_language('en-GB').get_default_spelling_rule().get_spelling_suggestions('color') == ['colour']
    assert us.get_spelling_suggestions('supercedes') == ['supersedes']  # getOnlySuggestions
    assert us.get_spelling_suggestions('wheater')[0] == 'weather'  # getTopSuggestions
    assert us.get_spelling_suggestions('wensday')[0] == 'Wednesday'  # getTopSuggestionsIgnoreCase
    assert us.get_spelling_suggestions('good') == []
