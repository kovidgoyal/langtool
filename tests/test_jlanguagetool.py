"""Ports of JLanguageToolTest, markup/AnnotatedTextTest (as far as applicable
to langtool.tool.AnnotatedText) and of the language independent parts of
LanguageSpecificTest (languagetool-core/src/test/java/org/languagetool/)."""

import re

import pytest

import langtool
from langtool.api import get_language
from langtool.patterns.pattern_token import PatternToken
from langtool.patterns.rules import AbstractPatternRule, PatternRule
from langtool.tool import AnnotatedText, JLanguageTool


# --- JLanguageToolTest -------------------------------------------------------

@pytest.fixture
def lang():
    """Languages.getLanguageForShortCode("xx")"""
    return get_language('xx')


def test_user_config(lang):
    lt1 = JLanguageTool(lang)
    lt1.disable_rule('test_unification_with_negation')
    assert len(lt1.check('This is my test')) == 0
    # Java passes the user rules in a UserConfig, which is not ported. The
    # equivalent in langtool is JLanguageTool.add_rule()
    pattern_tokens = [PatternToken('my'), PatternToken('test')]
    user_rule = PatternRule('MY_TEST', lang, pattern_tokens, 'test rule desc', 'my test rule', 'my test rule')
    lt2 = JLanguageTool(lang)
    lt2.add_rule(user_rule)
    lt2.disable_rule('test_unification_with_negation')
    matches2 = lt2.check('This is my test')
    assert len(matches2) == 1
    assert matches2[0].rule.get_id() == 'MY_TEST'
    assert (matches2[0].from_pos, matches2[0].to_pos) == (8, 15)


def test_check_string(lang):
    lt = JLanguageTool(lang)
    assert len(lt.check('This is my test.')) == 1



def test_check_string_with_callback_returns_true(lang):
    lt = JLanguageTool(lang)
    lt.set_check_cancelled_callback(lambda: True)
    assert len(lt.check('This is my test.')) == 0


def test_check_string_with_callback_returns_false(lang):
    lt = JLanguageTool(lang)
    lt.set_check_cancelled_callback(lambda: False)
    assert len(lt.check('This is my test.')) == 1


def test_list_unknown_words(lang):
    """JLanguageTool.setListUnknownWords/getUnknownWords"""
    lt = JLanguageTool(lang)
    with pytest.raises(RuntimeError):
        lt.get_unknown_words()
    lt.set_list_unknown_words(True)
    lt.check('This is my test. This is your test.')
    # the demo tagger tags no word: all non-whitespace tokens, sorted, without duplicates
    assert lt.get_unknown_words() == ['.', 'This', 'is', 'my', 'test', 'your']
    lt.check('Other')
    assert lt.get_unknown_words() == ['Other']


def test_set_output(lang):
    """JLanguageTool.setOutput: prints the analyzed sentences and switches
    the global verbose mode (disambiguator log) on"""
    import io
    from langtool import global_config
    lt = JLanguageTool(lang)
    out = io.StringIO()
    try:
        lt.set_output(out)
        assert global_config.is_verbose()
        lt.check('This is my test.')
        a = lt.analyze_text('This is my test.')[0]
        assert out.getvalue() == 2 * (str(a) + '\n' + a.get_annotations() + '\n')
        # (the paragraph end reading is added by 'add_paragaph_end', as in Java)
        assert a.get_annotations() == ('Disambiguator log: \n\nadd_paragaph_end: .[./SENT_END*] -> '
                                       '.[./SENT_END*,./PARA_END*]\n')
    finally:
        lt.set_output(None)
    assert not global_config.is_verbose()


def test_correct_text_from_matches():
    """Tools.correctTextFromMatches"""
    from langtool.rules.base import RuleMatch
    from langtool.tool import correct_text_from_matches

    class _Rule:
        pass
    text = 'This is is a a test.'
    m1 = RuleMatch(_Rule(), None, 5, 10, 'x', suggestions=['IS'])
    m2 = RuleMatch(_Rule(), None, 8, 12, 'x', suggestions=['a'])  # overlaps, the error was already corrected
    m3 = RuleMatch(_Rule(), None, 11, 14, 'x')  # no suggestion
    m4 = RuleMatch(_Rule(), None, 15, 19, 'x', suggestions=['example'])
    assert correct_text_from_matches(text, [m1, m2, m3, m4]) == 'This IS a a example.'
    assert correct_text_from_matches(text, []) == text


def test_pattern_rule_performers_per_thread(lang):
    """The matchers of pattern rules and the replacers of disambiguation
    rules keep state while matching (like in Java, where a new one is created
    for every match), so each thread gets its own one"""
    import threading
    from langtool.extensions import disambiguation_rules
    rule = [r for r in lang.get_pattern_rules() if hasattr(r, 'get_matcher')][0]
    drule = disambiguation_rules(lang)[0][0]
    drule.replace(JLanguageTool(lang).get_analyzed_sentence('This is a test.'))
    m, r = rule.get_matcher(), drule._replacers.r
    assert rule.get_matcher() is m
    other = {}

    def run():
        other['m'] = rule.get_matcher()
        drule.replace(JLanguageTool(lang).get_analyzed_sentence('This is a test.'))
        other['r'] = drule._replacers.r
    t = threading.Thread(target=run)
    t.start()
    t.join()
    assert other['m'] is not m and other['r'] is not r
    assert rule.get_matcher() is m and drule._replacers.r is r


# --- AnnotatedTextTest -------------------------------------------------------
# langtool's AnnotatedText is built from (is_markup, text, interpret_as) parts,
# there's no AnnotatedTextBuilder, no global meta data and no
# getTextWithMarkup(), so only the plain text and position mapping are tested.

def test_annotated_text():
    # hello <b>user!</b>
    text = AnnotatedText([(False, 'hello ', None), (True, '<b>', ''), (False, 'user!', None), (True, '</b>', '')])
    assert text.plain_text == 'hello user!'
    assert text.original_position(0, False) == 0
    assert text.original_position(5, False) == 5
    assert text.original_position(6, False) == 9
    assert text.original_position(7, False) == 10
    # hello user!
    #        ^ = position 8
    # hello <b>user!</b>
    #           ^ = position 11
    assert text.original_position(8, False) == 11


def test_annotated_text_interpret_as():
    # https://github.com/languagetool-org/languagetool/issues/1393
    text = AnnotatedText([(False, 'hello ', None), (True, '<p>', '\n\n'), (False, 'more xxxx text!', None)])
    assert text.plain_text == 'hello \n\nmore xxxx text!'
    # "xxxx" is at 13-17 in the plain text, at 14-18 in "hello <p>more xxxx text!"
    assert text.plain_text[13:17] == 'xxxx'
    assert text.original_position(13, False) == 14
    assert text.original_position(17, True) == 18


def test_check_annotated_text(lang):
    # positions of matches refer to the original text including markup
    lt = JLanguageTool(lang)
    text = AnnotatedText([(True, '<p>', ''), (False, 'This is ', None), (True, '<b>', ''),
                          (False, 'my test', None), (True, '</b>', ''), (False, '.', None)])
    assert text.plain_text == 'This is my test.'
    matches = lt.check(text)
    plain_matches = lt.check('This is my test.')
    assert len(matches) == len(plain_matches) == 1
    assert matches[0].rule.get_full_id() == plain_matches[0].rule.get_full_id()
    assert plain_matches[0].from_pos == 0
    assert matches[0].from_pos == 3


# --- LanguageSpecificTest ----------------------------------------------------
# Ported: testJavaRules (id/description validity, id uniqueness, examples of
# the Java rules) and testNoQuotesAroundSuggestion. Not ported: the checks that
# only print warnings (testNoLineBreaksEtcInMessage, countTempOffRules), tests
# of spell checking / language model / word list / coherency data
# (testReplaceRuleReplacements, testConfusionSetLoading, WordListValidatorTest,
# testCoherencyBaseformIsOtherForm) and DisambiguationRuleTest.

# languages whose Java module has a test class extending LanguageSpecificTest
# (plus the demo language)
_JAVA_TESTED = ('ast be br ca da de de-DE-x-simple-language el en eo es fa fr gl it ja km nl pl pt ro ru sk sl sv '
                'ta tl uk zh xx').split()


def _one_variant_per_language():
    out = {}
    for code in langtool.languages():
        short = 'de-DE-x-simple-language' if code == 'de-DE-x-simple-language' else code.split('-')[0]
        if short in _JAVA_TESTED:
            out.setdefault(short, code)
    return sorted(out.values())


LANGUAGES = _one_variant_per_language()


_ID_RE = re.compile(r'^[A-Z_][A-Z0-9_]+$')


def test_java_rules():
    """testJavaRules: runs over all languages (Languages.getWithDemoLanguage()).
    In Java each language module runs it with its own language and the demo
    language on the classpath, so the id uniqueness is checked for each
    language together with the demo language only (rule classes of different
    language modules may share an id, e.g. RussianSimpleWordRepeatRule, a
    WordRepeatRule subclass)."""
    problems = []
    for code in LANGUAGES:
        ids_to_class_name = {}
        rule_classes = set()
        for c in (code, 'xx-XX') if code != 'xx-XX' else (code,):
            _check_java_rules(c, ids_to_class_name, rule_classes, problems, examples=c == code)
    assert not problems, '\n'.join(problems)


def _check_java_rules(code, ids_to_class_name, rule_classes, problems, examples=True):
    language = get_language(code)
    lt = JLanguageTool(language)
    for rule in lt.get_all_rules():
        # assertIdAndDescriptionValidity
        rid = rule.get_id()
        if not rid.strip():
            problems.append('Empty rule id: %r, language: %s' % (rid, code))
        if not rule.get_description().strip():
            problems.append('Empty rule description for rule: %r, language: %s' % (rid, code))
        if isinstance(rule, AbstractPatternRule):
            continue
        # assertIdUniqueness
        cls = type(rule)
        if rid in ids_to_class_name and cls not in rule_classes:
            problems.append('Rule id occurs more than once: %r, one of them %s, the other one %s, language: %s'
                            % (rid, cls.__name__, ids_to_class_name[rid], code))
        ids_to_class_name[rid] = cls.__name__
        rule_classes.add(cls)
        # assertIdValidity
        if not _ID_RE.match(rid):
            problems.append('Invalid character in rule id: %r, language: %s' % (rid, code))
        if examples:
            problems.extend(_test_examples(rule, language))


_ID_TO_EXPECTED_MATCHES = {
    'EN_CONSISTENT_APOS': 2,
    'STYLE_REPEATED_WORD_RULE_DE': 2,
    'STYLE_REPEATED_SHORT_SENTENCES': 3,
    'STYLE_REPEATED_SENTENCE_BEGINNING': 3,
}


def _clean_markers(s):
    return s.replace('<marker>', '').replace('</marker>', '')


def _test_examples(rule, language):
    if not rule.correct_examples and not rule.incorrect_examples:
        return []
    out = []
    saved_tags = list(rule.tags)
    rule.tags = [t for t in rule.tags if t != 'picky']  # make sure "picky" rules also run
    try:
        lt = JLanguageTool(language, rules=[rule])
        lt.enable_rule(rule.get_id())
        for ex in rule.correct_examples:
            text = _clean_markers(getattr(ex, 'example', ex))
            matches = lt.check(text)
            if matches:
                out.append('Got unexpected rule match for correct example sentence: %r, rule %s: %s'
                           % (text, rule.get_id(), matches))
        for ex in rule.incorrect_examples:
            text = _clean_markers(getattr(ex, 'example', ex))
            matches = lt.check(text)
            if len(matches) != _ID_TO_EXPECTED_MATCHES.get(rule.get_id(), 1):
                out.append('Did not get the expected rule match for the incorrect example sentence: %r, rule %s: %s'
                           % (text, rule.get_id(), matches))
    finally:
        rule.tags = saved_tags
    return out


_QUOTE_BEFORE = re.compile('.*[\'"«»“”’]<suggestion.*')
_QUOTE_AFTER = re.compile('.*</suggestion>[\'"«»“”’].*')


@pytest.mark.parametrize('code', [c for c in LANGUAGES if c.split('-')[0] not in ('fa', 'zh')])
def test_no_quotes_around_suggestion(code):
    language = get_language(code)
    bad = []
    for rule in language.get_pattern_rules():
        if rule.source_file and '-test-' in rule.source_file:
            continue
        message = rule.message or ''
        # Java's String.matches(): '.' does not match line terminators
        if _QUOTE_BEFORE.fullmatch(message) and _QUOTE_AFTER.fullmatch(message):
            bad.append('%s rule %s uses quotes around <suggestion>...<suggestion> in its <message>, this should be '
                       'avoided: %r' % (language.name, rule.get_full_id(), message))
    assert not bad, '\n'.join(bad)
