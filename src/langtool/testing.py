"""Checking the example sentences of the XML rules.

Port of org.languagetool.rules.patterns.PatternRuleTest (testCorrectSentences,
testBadSentences, testErrorTriggeringSentences) and of
org.languagetool.tagging.disambiguation.rules.DisambiguationRuleTest.
"""

import regex

from .patterns.loader import load_pattern_rules
from .patterns import rules as R
from .rules.transformers import RepeatedPatternRule, ConsistencyPatternRule

_CLEAN_XML = regex.compile(r'<([^<][^\n\r\x85  ]*?)>')
_WS = regex.compile(r'[\n\t]+')
_REF = regex.compile(r'\\[0-9]+')


def clean_xml(s):
    return _CLEAN_XML.sub('', s)


class RuleFailure:
    __slots__ = ('rule', 'message')

    def __init__(self, rule, message):
        self.rule = rule
        self.message = message

    def __repr__(self):
        return '%s: %s' % (self.rule.get_full_id(), self.message)


class PatternRuleTester:
    """Checks the <example>s of all pattern rules of a language."""

    def __init__(self, lt):
        from .language import RESOURCE_DIR
        from .rules.filters import default_filter_factory
        from .messages import messages_for
        self.lt = lt
        self.language = lt.language
        self.failures = []
        # like the Java test: a separate copy of the rules (lt.loadPatternRules)
        self.rules = []
        ff = default_filter_factory()
        msgs = messages_for(self.language.short_code)
        for f in self.language.get_rule_file_names():
            rr, _ = load_pattern_rules(f, self.language, RESOURCE_DIR, ff, msgs)
            self.rules.extend(rr)
        self.complex_rules = {}

    def add_error(self, rule, msg):
        self.failures.append(RuleFailure(rule, msg))

    def _rules_by_id(self):
        """The rules of the JLanguageTool by id: id -> [(position, rule)]
        (rebuilt when rules were added)"""
        all_rules = self.lt.get_all_rules()
        key = (len(all_rules), id(all_rules[-1]) if all_rules else None)
        if getattr(self, '_rule_index_key', None) != key:
            index = {}
            for pos, rule in enumerate(all_rules):
                index.setdefault(rule.get_id(), []).append((pos, rule))
            self._rule_index = index
            self._rule_index_key = key
        return self._rule_index

    def rules_by_id_and_sub_id(self, id, sub_id):
        out = []
        # the rules whose id is a prefix of id (or id), in the order of lt.get_all_rules()
        index = self._rules_by_id()
        candidates = []
        for k in range(1, len(id) + 1):
            candidates.extend(index.get(id[:k], ()))
        candidates.extend(index.get('', ()))
        candidates.sort(key=lambda x: x[0])
        for _, rule in candidates:
            if id.startswith(rule.get_id()):
                if isinstance(rule, ConsistencyPatternRule):
                    out.extend(r for r in rule.rules if r.get_sub_id() == sub_id)
            if rule.get_id() == id:
                if isinstance(rule, RepeatedPatternRule):
                    out.extend(r for r in rule.rules if r.get_sub_id() == sub_id)
                elif isinstance(rule, R.AbstractPatternRule) and rule.get_sub_id() == sub_id:
                    out.append(rule)
        return out

    def run(self, rules=None, progress=None):
        rules = self.rules if rules is None else rules
        lang = self.language
        for i, rule in enumerate(rules):
            src = rule.source_file or ''
            if lang.is_variant() and _is_base_grammar_file(src, lang) and '-l2-' not in src and \
                    lang.code != 'de-DE-x-simple-language':
                continue
            try:
                self.test_correct_sentences(rule)
                self.test_bad_sentences(rule)
                self.test_error_triggering_sentences(rule)
            except Exception as e:
                import traceback
                self.add_error(rule, 'Exception: %s\n%s' % (e, traceback.format_exc()))
            if progress is not None:
                progress(i, len(rules))
        if self.complex_rules:
            bad = [r for r in self.complex_rules.values() if r is not None and isinstance(r, R.PatternRule)]
            self.complex_rules = {}
            for r in bad:
                r.is_member_of_disjunctive_set = False
                r.message = 'The rule contains a phrase that never matched any incorrect example.\n' + \
                    r.to_pattern_string()
            if bad:
                self.run(bad)
        return self.failures

    def matches_for_text(self, rule, sentence):
        sentences = self.lt.analyze_text(sentence)
        out = []
        offset = 0
        for s in sentences:
            ms = rule.match(s)
            for m in ms:
                m.set_offset_position(m.from_pos + offset, m.to_pos + offset)
            out.extend(ms)
            offset += len(s.text)
        return out

    def matches_for_single_sentence(self, rule, sentence):
        return rule.match(self.lt.get_analyzed_sentence(sentence))

    def is_matched(self, rule, sentence):
        for s in self.lt.analyze_text(sentence):
            if rule.match(s):
                return True
        return False

    def test_correct_sentences(self, rule):
        rules = self.rules_by_id_and_sub_id(rule.get_id(), rule.get_sub_id())
        for ex in rule.correct_examples:
            good = clean_xml(_WS.sub('', ex.example))
            if not good.strip():
                self.add_error(rule, 'Empty correct example.')
                continue
            matched = False
            for r in rules:
                matched = matched or self.is_matched(r, good)
            if matched:
                a = self.lt.get_analyzed_sentence(good)
                self.add_error(rule, 'Did not expect error in:\n  %s\n  Analyzed token readings: %s\n' % (
                    good, ' '.join(str(t) for t in a.tokens)))

    def test_bad_sentences(self, rule):
        bad_examples = rule.incorrect_examples
        if not bad_examples:
            self.add_error(rule, 'No incorrect examples found.')
            return
        rules = self.rules_by_id_and_sub_id(rule.get_id(), rule.get_sub_id())
        lang = self.language
        lenient = lang.short_code in ('gl', 'eo', 'br', 'ca', 'zh')
        for ex in bad_examples:
            orig = _WS.sub('', ex.example)
            expected = ex.corrections or []
            start = orig.find('<marker>')
            end = orig.find('</marker>') - len('<marker>')
            if start == -1 or orig.find('</marker>') == -1:
                self.add_error(rule, "No error position markup ('<marker>...</marker>') in bad example.")
                continue
            bad = orig.replace('<marker>', '').replace('</marker>', '')
            if not bad.strip():
                self.add_error(rule, 'Empty incorrect example sentence after cleaning/trimming.')
                continue
            matches = []
            for r in rules:
                if lenient:
                    matches.extend(self.matches_for_single_sentence(r, bad))
                else:
                    matches.extend(self.matches_for_text(r, bad))
            if isinstance(rule, R.RegexPatternRule) or (isinstance(rule, R.PatternRule) and
                                                        not rule.is_with_complex_phrase()):
                if len(matches) != 1:
                    a = self.lt.get_analyzed_sentence(bad)
                    self.add_error(rule, '"%s"\nErrors expected: 1\nErrors found   : %d\nMessage: %s\n'
                                         'Analyzed token readings: %s\nMatches: %s' % (
                                             bad, len(matches), rule.message, ' '.join(str(t) for t in a.tokens),
                                             matches))
                    continue
                m0 = matches[0]
                if start != m0.from_pos or end != m0.to_pos:
                    self.add_error(rule, 'Incorrect match position markup (expected match position: %d - %d, '
                                         'actual: %d - %d) in sentence: %s' % (start, end, m0.from_pos, m0.to_pos,
                                                                               bad))
                else:
                    self.assert_suggestions(bad, expected, rule, matches)
                    if m0.suggested_replacements:
                        for repl in m0.suggested_replacements:
                            fixed = bad[:m0.from_pos] + repl + bad[m0.to_pos:]
                            fm = self.matches_for_text(rule, fixed)
                            if fm:
                                self.add_error(rule, 'Incorrect input:\n  %s\nCorrected sentence:\n  %s\n'
                                                     'The correction triggered an error itself:\n  %s\n' % (
                                                         bad, fixed, fm[0]))
            else:
                matches = self.matches_for_text(rule, bad)
                key = rule.get_id() + bad
                if not matches and key not in self.complex_rules:
                    self.complex_rules[key] = rule
                if matches:
                    self.complex_rules[key] = None
                    if len(matches) != 1:
                        self.add_error(rule, 'Did expect one error in: "%s" , got %d' % (bad, len(matches)))
                    elif start != matches[0].from_pos or end != matches[0].to_pos:
                        self.add_error(rule, 'Incorrect match position markup (expected match position: %d - %d, '
                                             'actual: %d - %d)in sentence: %s' % (start, end, matches[0].from_pos,
                                                                                  matches[0].to_pos, bad))
                    else:
                        self.assert_suggestions(bad, expected, rule, matches)
                        m0 = matches[0]
                        for repl in m0.suggested_replacements:
                            fixed = bad[:m0.from_pos] + repl + bad[m0.to_pos:]
                            if self.matches_for_text(rule, fixed):
                                self.add_error(rule, 'Corrected sentence for rule %s triggered error: %s' % (
                                    rule.get_full_id(), fixed))

    def test_error_triggering_sentences(self, rule):
        for ex in rule.error_triggering_examples:
            s = clean_xml(ex.example)
            if not self.matches_for_text(rule, s):
                self.add_error(rule, "Example sentence marked with 'triggers_error' didn't actually trigger an "
                                     "error: '%s'" % s)

    def assert_suggestions(self, sentence, expected, rule, matches):
        if not expected:
            return
        if expected[0]:
            if not ('<suggestion>' in rule.message or '<suggestion>' in rule.suggestions_out_msg) and \
                    rule.filter is None and getattr(rule, 'regex_filter', None) is None:
                self.add_error(rule, 'You specified a correction, but your message has no suggestions.')
        real = matches[0].suggested_replacements
        if not real:
            if not (len(expected) == 1 and not expected[0]):
                self.add_error(rule, "Incorrect suggestions: Expected '%s', got  <no suggestion> on input: '%s'" % (
                    expected, sentence))
        elif list(expected) != list(real):
            self.add_error(rule, "Incorrect suggestions: Expected '%s', got: '%s' on input: '%s'" % (
                '|'.join(expected), '|'.join(real), sentence))


def _is_base_grammar_file(src, lang):
    import os
    d, f = os.path.split(src)
    return os.path.basename(d) == lang.short_code and f.startswith('grammar') and f.endswith('.xml')


class DisambiguationRuleTester:
    """Port of DisambiguationRuleTest: checks the examples of
    disambiguation.xml. Like the Java test, each example is analyzed with
    the pre-disambiguation (e.g. multiword chunkers) and all the rules that
    come before the tested rule, and the readings of the marked token are
    compared with the inputform/outputform in AnalyzedSentence.toShortString
    format (e.g. "10[10/CD]")."""

    def __init__(self, lt):
        self.lt = lt
        self.language = lt.language
        self.failures = []
        self.rules = None

    def run(self, rules=None):
        from .extensions import disambiguation_rules
        if rules is None:
            lang = self.language.default_variant
            rules, _ = disambiguation_rules(lang, False)
        self.rules = rules
        for rule in rules:
            try:
                self._test_rule(rule)
            except Exception as e:
                import traceback
                self.failures.append(RuleFailure(rule, 'Exception: %s\n%s' % (e, traceback.format_exc())))
        return self.failures

    def _fail(self, rule, msg):
        self.failures.append(RuleFailure(rule, msg))

    def disambiguate_until(self, rule_id, sentence):
        """Pre-disambiguation plus all rules before the first one with the
        given id (DisambiguationRuleTest.disambiguateUntil)."""
        sentence = _pre_xml_disambiguate(self.lt, sentence)
        for rule in self.rules:
            if rule.get_id() == rule_id:
                break
            sentence = rule.replace(sentence)
        return sentence

    def _test_rule(self, rule):
        from .analysis import AnalyzedSentence
        lt = self.lt
        rid = rule.get_id()
        for good in rule.untouched_examples or ():
            good = clean_xml(_WS.sub('', good))
            if not good.strip():
                self._fail(rule, 'Empty untouched example')
                continue
            sent = self.disambiguate_until(rid, lt.get_raw_analyzed_sentence(good))
            to_replace = self.disambiguate_until(rid, lt.get_raw_analyzed_sentence(good))
            before, after = str(sent), str(rule.replace(to_replace))
            if before != after:
                self._fail(rule, 'The untouched example (%s) for rule %s was touched!\nbefore: %s\nafter:  %s' % (
                    good, rule, before, after))
        for example, input_forms, output_forms in rule.examples or ():
            if not output_forms or not output_forms.strip():
                self._fail(rule, 'No output form found for: %s' % rid)
                continue
            start = example.find('<marker>')
            end = example.find('</marker>') - len('<marker>')
            if start == -1 or example.find('</marker>') == -1:
                self._fail(rule, "No position markup ('<marker>...</marker>') in disambiguated example: %r" % example)
                continue
            if not input_forms or not input_forms.strip():
                self._fail(rule, 'No input form found for: %s' % rid)
                continue
            if input_forms == output_forms:
                self._fail(rule, 'Input and output forms for rule %s are the same!' % rid)
                continue
            text = clean_xml(example)
            clean_input = lt.get_raw_analyzed_sentence(text)
            sent = self.disambiguate_until(rid, lt.get_raw_analyzed_sentence(text))
            disambiguated = rule.replace(self.disambiguate_until(rid, lt.get_raw_analyzed_sentence(text)))
            if clean_input == disambiguated:
                self._fail(rule, 'Disambiguated sentence is equal to the non-disambiguated sentence for rule: '
                                 '%s. The sentence was: %s' % (rid, sent))
                continue
            if sent == disambiguated:
                self._fail(rule, 'Disambiguated sentence is equal to the input sentence for rule: %s. '
                                 'The sentence was: %s' % (rid, sent))
                continue
            ok = True
            for label, sentence, expected in (('input', sent, input_forms), ('output', disambiguated, output_forms)):
                reading = ''
                for atr in sentence.tokens:
                    if atr.is_sentence_start and '<S>' not in expected:
                        continue
                    if atr.start_pos == start:
                        reading = AnalyzedSentence([atr]).to_short_string(',')
                        if atr.end_pos != end:
                            self._fail(rule, 'Wrong marker position in the example for the rule %s: got %d-%d, '
                                             'expected %d-%d. Sentence: %r' % (rid, atr.start_pos, atr.end_pos,
                                                                              start, end, str(sentence)))
                            ok = False
                        break
                if not ok:
                    break
                got = _sort_forms(reading)
                if expected != got:
                    self._fail(rule, 'The %s form for the rule %s in the example: %s is different than expected '
                                     '(expected %s but got %s)' % (label, rid, example, expected, got))
                    break


def _pre_xml_disambiguate(lt, sentence):
    """Disambiguator.preDisambiguate: the identity for the disambiguators of
    languagetool-core (AbstractDisambiguator) and of the ported languages
    (in Java only UkrainianHybridDisambiguator overrides it); a
    disambiguator may define pre_disambiguate(sentence). In particular the
    multiword chunkers of the hybrid disambiguators do not run before the
    rules in DisambiguationRuleTest."""
    f = getattr(lt.language.disambiguator, 'pre_disambiguate', None)
    if f is not None:
        return f(sentence)
    return sentence


def _sort_forms(word_forms):
    """DisambiguationRuleTest.sortForms"""
    if word_forms == ',[,]' or not word_forms:
        return word_forms
    word = word_forms[:word_forms.index('[') + 1]
    forms = word_forms[word_forms.index('[') + 1:-1].split(',')
    forms.sort(key=lambda f: f.encode('utf-16-be', 'surrogatepass'))
    return word + ','.join(forms) + ']'
