"""Port of org.languagetool.rules.ca.QueIniciCorpusTest: a statistical tool for
the QUE_INICIAL_* rules (and the QueIniciFilter).

It counts:
 - FP (false positives): matches on the original sentences of the corpus,
   which are in principle correct and should not get any match.
 - TP (true positives) and FN (false negatives): inverting the initial
   que/què of every sentence of the corpus makes it incorrect; the rule should
   then suggest a replacement that restores the original sentence (TP),
   otherwise it is a FN.

The file of ambiguous examples (both forms are valid) is only used to count
FP: neither the original nor the inverted sentence should get a match.

As in Java this is not a pass/fail test: it is skipped unless it is enabled
(Java: -DqueInici.run=true or -DqueInici.errorsOnly=true, here the
environment variables QUE_INICI_RUN=true or QUE_INICI_ERRORS_ONLY=true; the
other system properties queInici.* are the environment variables QUE_INICI_*,
e.g. QUE_INICI_CORPUS_DIR), and the corpus files are not distributed with the
code (skipped if they are missing).
"""

import datetime
import os

import pytest

from conftest import require_dictionaries
from langtool import jregex
from langtool.lang.ca import que_inici
from langtool.lang.ca.synthesis import VerbSynthesizer
from langtool.rules.abstract_rules import java_hash_set_order

# Etiquetes de direcció (claus dels comptadors i del report)
SENSE_ACCENT = 'SENSE (què->que)'
AMB_ACCENT = 'AMB (que->què)'


def _property(name, default=None):
    """System.getProperty("queInici.<name>") -> the environment variable QUE_INICI_<NAME>"""
    return os.environ.get('QUE_INICI_' + ''.join('_' + c if c.isupper() else c.upper() for c in name), default)


def ids_from_property(prop, default_value):
    value = _property(prop, default_value)
    return [i.strip() for i in value.split(',') if i.strip()]


def int_from_property(prop, default_value):
    value = _property(prop)
    if value is None:
        return default_value
    return int(value)


def _boolean_property(prop):
    """Boolean.getBoolean"""
    return (_property(prop) or '').lower() == 'true'


# Selecció de regles, NO classificació de la direcció (configurable, see _property)
SENSE_IDS = ids_from_property('sense', 'QUE_INICIAL_SENSEACCENT_NOVERB,QUE_INICIAL_SENSEACCENT_HO,'
                                       'QUE_INICIAL_SENSEACCENT_VERB')
AMB_IDS = ids_from_property('amb', 'QUE_INICIAL_AMBACCENT_NOVERB,QUE_INICIAL_AMBACCENT_VERB,QUE_INICIAL_AMBACCENT_HO')

# que/què com a paraula sencera (sense lletres a banda i banda)
QUE_WORD = jregex.compile('(?<!\\p{L})[Qq][Uu][EeÈè](?!\\p{L})')
CONTRAST_HEADER = ('total\taccent_count\tnoaccent_count\taccent_ratio\tverb\tnoun'
                   '\taccent_subject_compatible_count\tnoaccent_subject_compatible_count\taccent_examples'
                   '\tnoaccent_examples')
EXPLETIVES = frozenset((
    'collons', 'coi', 'cony', 'dimonis', 'dimoni', 'carai', 'diantre', 'caram',
    'carall', 'punyeta', 'punyetes', 'redimonis', 'diables', 'diable', 'hòstia',
    'dimontri', 'dimontris', 'redéu', 'redeu', 'punyetera', 'leche', 'putes',
    'fotons', 'llamps', 'trons'))


def matches_any(rule_id, ids):
    return any(rule_id.startswith(i) for i in ids)


def get_tool():
    from langtool.api import get_language
    from langtool.tool import JLanguageTool
    tool = JLanguageTool(get_language('ca-ES'))
    # Activem explícitament els grups seleccionats, com en les passades històriques.
    for rule in tool.get_all_rules():
        rule_id = rule.get_id()
        if matches_any(rule_id, SENSE_IDS) or matches_any(rule_id, AMB_IDS):
            tool.enable_rule(rule_id)
        else:
            tool.disable_rule(rule_id)
    return tool


def find_corpus_directory():
    configured = _property('corpusDir')
    if configured is not None:
        return configured
    for directory in ('var-languagetool-que-inici', 'var'):
        for prefix in ('', '../../', '../../../'):
            candidate = prefix + directory
            if os.path.isfile(os.path.join(candidate, 'que_inici.txt')):
                return candidate
    return 'var-languagetool-que-inici'


def invert_que(sentence):
    """Inverteix l'accent del primer que/què que apareix a la frase, conservant les majúscules."""
    m = QUE_WORD.search(sentence)
    if m is None:
        return None
    word = m.group()
    inverted = {'e': 'è', 'è': 'e', 'E': 'È', 'È': 'E'}.get(word[2])
    if inverted is None:
        return None
    return sentence[:m.start()] + word[:2] + inverted + sentence[m.end():]


class TargetMatches:
    def __init__(self):
        self.first_match_id = None
        self.correction_rule_id = None


def evaluate_matches(sentence, matches):
    """Només comptem avisos que cobreixen el primer que/què. Un TP requereix una
    proposta que desfaci exactament la inversió, inclosos els matches de més d'un
    token ("que tal")."""
    result = TargetMatches()
    target = QUE_WORD.search(sentence)
    if target is None:
        return result
    corrected = invert_que(sentence)
    for match in matches:
        rule_id = match.rule.get_id()
        if ((not matches_any(rule_id, SENSE_IDS) and not matches_any(rule_id, AMB_IDS))
                or match.from_pos < 0 or match.to_pos > len(sentence)
                or match.from_pos > target.start() or match.to_pos < target.end()):
            continue
        if result.first_match_id is None:
            result.first_match_id = match.rule.get_full_id()
        expected_replacement = corrected[match.from_pos:match.to_pos]
        if expected_replacement in match.suggested_replacements:
            result.correction_rule_id = match.rule.get_full_id()
            break
    return result


def evaluate_sentence(tool, sentence):
    return evaluate_matches(sentence, tool.check(sentence))


def first_que_has_accent(sentence):
    """True si el primer que/què de la frase porta accent (què), False si no (que), None si no n'hi ha."""
    m = QUE_WORD.search(sentence)
    if m is None:
        return None
    return m.group()[2] in 'èÈ'


class ErrorCase:
    def __init__(self, error_id, correct_sentence, checked_sentence, inverted):
        self.id = error_id
        self.correct_sentence = correct_sentence
        self.checked_sentence = checked_sentence
        self.inverted = inverted

    def format(self):
        if self.inverted:
            return self.id + '\t' + self.correct_sentence + '  ==>  ' + self.checked_sentence
        return self.id + '\t' + self.checked_sentence


class RuleStats:
    def __init__(self, rule_id):
        self.rule_id = rule_id
        self.fp = self.tp = self.fn = 0

    def total(self):
        return self.fp + self.tp + self.fn


class VerbNounContext:
    def __init__(self, verb_lemma, noun_lemma, subject_compatible):
        self.verb_lemma = verb_lemma
        self.noun_lemma = noun_lemma
        self.subject_compatible = subject_compatible


def _merge(counts, key, n=1):
    counts[key] = counts.get(key, 0) + n


def _add_verb_noun_context(counts, examples, verb_lemma, noun_lemma, sentence):
    key = verb_lemma + '\t' + noun_lemma
    _merge(counts, key)
    key_examples = examples.setdefault(key, [])
    if len(key_examples) < 3:
        key_examples.append(sentence)


class VerbNounReports:
    """Accent observat i compatibilitat de subjecte són dimensions independents."""

    def __init__(self):
        self.nouns_after_accent = {}
        self.nouns_after_no_accent = {}
        self.verb_noun_after_accent = {}
        self.verb_noun_after_no_accent = {}
        self.verb_noun_examples_accent = {}
        self.verb_noun_examples_no_accent = {}
        self.subject_compatible_accent = {}
        self.subject_compatible_no_accent = {}
        self.details = ['correct_accent\tsubject_compatible\tnoun_role_candidate\tverb\tnoun\terror_id\tsentence']

    def add(self, correct_accent, context, error_id, sentence):
        key = context.verb_lemma + '\t' + context.noun_lemma
        _merge(self.nouns_after_accent if correct_accent else self.nouns_after_no_accent, context.noun_lemma)
        _add_verb_noun_context(self.verb_noun_after_accent if correct_accent else self.verb_noun_after_no_accent,
                               self.verb_noun_examples_accent if correct_accent
                               else self.verb_noun_examples_no_accent,
                               context.verb_lemma, context.noun_lemma, '[' + error_id + '] ' + sentence)
        if context.subject_compatible:
            _merge(self.subject_compatible_accent if correct_accent else self.subject_compatible_no_accent, key)
        # La concordança només indica una possibilitat: no prova que el nom sigui el subjecte.
        self.details.append('%s\t%s\t%s\t%s\t%s\t%s' % (
            'true' if correct_accent else 'false', 'true' if context.subject_compatible else 'false',
            'subject_possible' if context.subject_compatible else 'undetermined', key, error_id, sentence))


class VerbNounStats:
    def __init__(self, verb, noun, accent, no_accent, accent_subject_compatible, no_accent_subject_compatible):
        self.verb = verb
        self.noun = noun
        self.accent = accent
        self.no_accent = no_accent
        self.total = accent + no_accent
        self.accent_subject_compatible = accent_subject_compatible
        self.no_accent_subject_compatible = no_accent_subject_compatible

    def accent_ratio(self):
        return 0.0 if self.total == 0 else self.accent / self.total


def _accepts_subject(stats):
    return (stats.total >= 5 and stats.accent_subject_compatible >= 5 and stats.accent_ratio() >= 0.90
            and not que_inici.is_animate_subject_noun(stats.noun) and not que_inici.is_never_subject_noun(stats.noun))


def _accepts_object(stats):
    return stats.total >= 5 and stats.no_accent >= 5 and stats.accent_ratio() <= 0.05


def _accepts_review(stats):
    return stats.total >= 10 and not _accepts_subject(stats) and not _accepts_object(stats)


def _sorted_entries(counts):
    """The entries of a HashMap sorted by descending count (stable sort of the HashMap order)"""
    return sorted(((k, counts[k]) for k in java_hash_set_order(list(counts))), key=lambda e: -e[1])


def sort_by_freq(counts):
    return ['%d\t%s' % (v, k) for k, v in _sorted_entries(counts)]


def format_rule_stats(stats_by_rule):
    stats = sorted(stats_by_rule.values(), key=lambda s: (-s.total(), s.rule_id))
    result = ['rule_id\tfp\ttp\tfn\ttotal']
    for s in stats:
        result.append('%s\t%d\t%d\t%d\t%d' % (s.rule_id, s.fp, s.tp, s.fn, s.total()))
    return result


def sort_verb_noun_contexts(counts, examples):
    result = ['count\tverb\tnoun\texamples']
    for key, value in _sorted_entries(counts):
        verb, noun = key.split('\t', 1)
        result.append('%d\t%s\t%s\t%s' % (value, verb, noun, ' || '.join(examples.get(key, []))))
    return result


def sorted_verb_noun_stats(contexts):
    all_counts = {}
    for k, v in contexts.verb_noun_after_accent.items():
        _merge(all_counts, k, v)
    for k, v in contexts.verb_noun_after_no_accent.items():
        _merge(all_counts, k, v)
    result = []
    for key, _value in _sorted_entries(all_counts):
        verb, noun = key.split('\t', 1)
        result.append(VerbNounStats(verb, noun, contexts.verb_noun_after_accent.get(key, 0),
                                    contexts.verb_noun_after_no_accent.get(key, 0),
                                    contexts.subject_compatible_accent.get(key, 0),
                                    contexts.subject_compatible_no_accent.get(key, 0)))
    return result


def format_verb_noun_stats(stats, contexts):
    key = stats.verb + '\t' + stats.noun
    return '%d\t%d\t%d\t%.4f\t%s\t%s\t%d\t%d\t%s\t%s' % (
        stats.total, stats.accent, stats.no_accent, stats.accent_ratio(), stats.verb, stats.noun,
        stats.accent_subject_compatible, stats.no_accent_subject_compatible,
        ' || '.join(contexts.verb_noun_examples_accent.get(key, [])),
        ' || '.join(contexts.verb_noun_examples_no_accent.get(key, [])))


def sort_verb_noun_contrast(contexts):
    return [CONTRAST_HEADER] + [format_verb_noun_stats(e, contexts) for e in sorted_verb_noun_stats(contexts)]


def filter_verb_noun_candidates(stats, contexts, accepts):
    return [CONTRAST_HEADER] + [format_verb_noun_stats(s, contexts) for s in stats if accepts(s)]


def write_lines(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')


def write_verb_noun_context_reports(report_dir, contexts):
    j = os.path.join
    write_lines(j(report_dir, 'nouns_after_verb_accent.txt'), sort_by_freq(contexts.nouns_after_accent))
    write_lines(j(report_dir, 'nouns_after_verb_noaccent.txt'), sort_by_freq(contexts.nouns_after_no_accent))
    write_lines(j(report_dir, 'verb_noun_after_verb_accent.tsv'),
                sort_verb_noun_contexts(contexts.verb_noun_after_accent, contexts.verb_noun_examples_accent))
    write_lines(j(report_dir, 'verb_noun_after_verb_noaccent.tsv'),
                sort_verb_noun_contexts(contexts.verb_noun_after_no_accent, contexts.verb_noun_examples_no_accent))
    write_lines(j(report_dir, 'verb_noun_after_verb_contrast.tsv'), sort_verb_noun_contrast(contexts))
    stats = sorted_verb_noun_stats(contexts)
    write_lines(j(report_dir, 'verb_noun_subject_candidates.tsv'),
                filter_verb_noun_candidates(stats, contexts, _accepts_subject))
    write_lines(j(report_dir, 'verb_noun_object_candidates.tsv'),
                filter_verb_noun_candidates(stats, contexts, _accepts_object))
    write_lines(j(report_dir, 'verb_noun_manual_review.tsv'),
                filter_verb_noun_candidates(stats, contexts, _accepts_review))
    write_lines(j(report_dir, 'verb_noun_contexts.tsv'), contexts.details)


def exact_verb_noun_context_after_que(tokens, que_idx, core_end):
    from langtool.api import get_language
    if que_idx < 0 or core_end < 0:
        return None
    verb_synthesizer = VerbSynthesizer(tokens, que_idx + 1, get_language('ca-ES'))
    if (verb_synthesizer.is_undefined() or verb_synthesizer.get_first_verb_index() >= core_end
            or verb_synthesizer.get_last_index() >= core_end):
        return None
    for i in range(que_idx + 1, verb_synthesizer.get_first_verb_index()):
        if tokens[i].token.lower() in EXPLETIVES:
            return None
    main_verb_reading = tokens[verb_synthesizer.get_last_verb_index()].reading_with_tag_regex('V.*')
    if main_verb_reading is None:
        return None
    noun_idx = verb_synthesizer.get_last_index() + 1
    while noun_idx < core_end and tokens[noun_idx].matches_pos_tag_regex('D.*'):
        noun_idx += 1
    if noun_idx >= core_end:
        return None
    noun_reading = tokens[noun_idx].reading_with_tag_regex('NC.*')
    if noun_reading is None:
        return None
    first = tokens[verb_synthesizer.get_first_verb_index()]
    verb3s = first.matches_pos_tag_regex('V.[SI].3S.*')
    verb3p = first.matches_pos_tag_regex('V.[SI].3P.*')
    noun_singular = tokens[noun_idx].matches_pos_tag_regex('NC.S.*')
    noun_plural = tokens[noun_idx].matches_pos_tag_regex('NC.P.*')
    subject_compatible = (verb3s and noun_singular) or (verb3p and noun_plural)
    return VerbNounContext(main_verb_reading.lemma, noun_reading.lemma, subject_compatible)


def collect_verb_noun_contexts_from_errors(tool, errors, seen, contexts):
    for error in errors:
        correct_accent = first_que_has_accent(error.correct_sentence)
        if correct_accent is None:
            continue
        if error.correct_sentence in seen:
            continue
        seen.add(error.correct_sentence)
        toks = tool.get_analyzed_sentence(error.correct_sentence).get_tokens_without_whitespace()
        qi = que_inici.find_que(toks)
        core_end = -1
        if qi >= 0:
            question = que_inici.find_question_mark(toks, qi)
            if question >= 0:
                core_end = que_inici.strip_confirmation_tag(toks, qi, question)
        context = exact_verb_noun_context_after_que(toks, qi, core_end)
        if context is not None:
            contexts.add(correct_accent, context, error.id, error.correct_sentence)


def parse_error_case(line, inverted):
    trimmed = line.strip()
    if not trimmed:
        return None
    parts = trimmed.split('\t', 1)
    if len(parts) != 2:
        return None
    if inverted:
        sentences = parts[1].split('  ==>  ', 1)
        if len(sentences) != 2:
            return None
        return ErrorCase(parts[0], sentences[0], sentences[1], True)
    return ErrorCase(parts[0], parts[1], parts[1], False)


def collect_verb_noun_contexts_from_error_file(tool, path, inverted, seen, contexts):
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        errors = [e for e in (parse_error_case(line.rstrip('\n'), inverted) for line in f) if e is not None]
    collect_verb_noun_contexts_from_errors(tool, errors, seen, contexts)
    return len(errors)


def write_verb_noun_context_reports_from_existing_errors(report_dir):
    tool = get_tool()
    contexts = VerbNounReports()
    seen = set()
    errors = 0
    for name, inverted in (('false_positives_sense_accent.txt', False), ('false_positives_amb_accent.txt', False),
                           ('false_negatives_sense_accent.txt', True), ('false_negatives_amb_accent.txt', True)):
        errors += collect_verb_noun_contexts_from_error_file(tool, os.path.join(report_dir, name), inverted, seen,
                                                             contexts)
    write_verb_noun_context_reports(report_dir, contexts)
    print('Regenerats els TSV de context verb+nom a partir de %d casos FP/FN de: %s' % (
        errors, os.path.abspath(report_dir)))
    assert errors > 0, "No s'ha trobat cap cas FP/FN a " + os.path.abspath(report_dir)


def append_metrics(sb, fp, tp, fn, applicable):
    precision = 0 if (tp + fp) == 0 else tp / (tp + fp)
    recall = 0 if applicable == 0 else tp / applicable
    sb.append('  FP: %d   TP: %d   FN: %d   (aplicables: %d)\n' % (fp, tp, fn, applicable))
    sb.append('  Precisió: %.4f   Recall: %.4f\n' % (precision, recall))


def append_rule_stats(sb, rule_id, fp, tp, fn, applicable):
    sb.append('--- ' + rule_id + ' ---\n')
    append_metrics(sb, fp, tp, fn, applicable)


def fn_id(expected_direction, fired_id):
    expected = 'SENSE' if expected_direction == SENSE_ACCENT else 'AMB'
    if fired_id is not None:
        return 'EXPECTED_' + expected + '_GOT_' + fired_id
    return 'EXPECTED_' + expected + '_NO_MATCH'


def test_corpus():
    """QueIniciCorpusTest.testCorpus"""
    # Eina estadística, no un test de pass/fail: se salta per defecte.
    errors_only = _boolean_property('errorsOnly')
    if not (_boolean_property('run') or errors_only):
        pytest.skip('Eina estadística desactivada; executeu-la amb QUE_INICI_RUN=true o QUE_INICI_ERRORS_ONLY=true '
                    '(-DqueInici.run=true in Java)')
    require_dictionaries('ca')
    corpus_dir = find_corpus_directory()
    main_corpus = os.path.join(corpus_dir, 'que_inici.txt')
    ambig_corpus = os.path.join(corpus_dir, 'que_inici_ambigu.txt')
    report_dir = _property('reportDir', os.path.join(corpus_dir, 'que_inici_report'))
    if errors_only:
        assert os.path.isdir(report_dir), 'Report dir not found: ' + os.path.abspath(report_dir)
        write_verb_noun_context_reports_from_existing_errors(report_dir)
        return
    if _property('corpusDir') is not None:
        assert os.path.isfile(main_corpus), 'Corpus file not found: ' + os.path.abspath(main_corpus)
    if not os.path.isfile(main_corpus):
        pytest.skip('Corpus file not found: ' + os.path.abspath(main_corpus))

    tool = get_tool()
    fp_sense, fp_amb, fp_sense_cases, fp_amb_cases = [], [], [], []
    fn_sense, fn_amb, fn_sense_cases, fn_amb_cases = [], [], [], []
    stats_by_rule = {}

    def stats_for(rule_id):
        s = stats_by_rule.get(rule_id)
        if s is None:
            s = stats_by_rule[rule_id] = RuleStats(rule_id)
        return s

    tp_sense = tp_amb = 0
    verbs_after_que_accent = {}
    verbs_after_que = {}
    contexts = VerbNounReports()
    accent_verb = accent_no_verb = sense_accent_verb = sense_accent_no_verb = 0
    accent_no_verb_examples = []

    with open(main_corpus, encoding='utf-8') as f:
        lines = f.read().splitlines()
    total_sentences = sum(1 for line in lines if line.strip())
    progress_every = int_from_property('progressEvery', 5000)
    processed_sentences = 0
    for line in lines:
        sentence = line.strip()
        if not sentence:
            continue
        processed_sentences += 1
        if progress_every > 0 and (processed_sentences % progress_every == 0
                                   or processed_sentences == total_sentences):
            print('QUE_INICI: analitzades %d/%d frases' % (processed_sentences, total_sentences))
        # Comprovació de la hipòtesi + acumulació de verbs (per lema) darrere el que/què
        orig_accent = first_que_has_accent(sentence)
        if orig_accent is not None:
            toks = tool.get_analyzed_sentence(sentence).get_tokens_without_whitespace()
            qi = que_inici.find_que(toks)
            verb_idx = -1
            if qi >= 0:
                qq = que_inici.find_question_mark(toks, qi)
                if qq >= 0:
                    core_end = que_inici.strip_confirmation_tag(toks, qi, qq)
                    verb_idx = que_inici.verb_index_after_que(toks, qi, core_end)
            has_verb = verb_idx >= 0
            if has_verb:
                lemma = que_inici.verb_lemma(toks[verb_idx])
                if lemma is not None:
                    _merge(verbs_after_que_accent if orig_accent else verbs_after_que, lemma)
            if orig_accent:
                if has_verb:
                    accent_verb += 1
                else:
                    accent_no_verb += 1
                    accent_no_verb_examples.append(sentence)
            elif has_verb:
                sense_accent_verb += 1
            else:
                sense_accent_no_verb += 1
        # FP: la frase original és (en principi) correcta -> no hauria de saltar cap regla
        fired_id_original = evaluate_sentence(tool, sentence).first_match_id
        if fired_id_original is not None and orig_accent is True:
            fp_sense.append(fired_id_original + '\t' + sentence)
            fp_sense_cases.append(ErrorCase(fired_id_original, sentence, sentence, False))
            stats_for(fired_id_original).fp += 1
        elif fired_id_original is not None and orig_accent is False:
            fp_amb.append(fired_id_original + '\t' + sentence)
            fp_amb_cases.append(ErrorCase(fired_id_original, sentence, sentence, False))
            stats_for(fired_id_original).fp += 1
        # TP/FN: invertim el que/què inicial -> la frase esdevé incorrecta -> hauria de saltar.
        inverted = invert_que(sentence)
        if inverted is not None and inverted != sentence:
            inv_accent = first_que_has_accent(inverted)
            expected = SENSE_ACCENT if inv_accent is True else AMB_ACCENT
            inverted_matches = evaluate_sentence(tool, inverted)
            fired_id_inverted = inverted_matches.first_match_id
            detected = inverted_matches.correction_rule_id is not None
            if detected:
                if expected == SENSE_ACCENT:
                    tp_sense += 1
                else:
                    tp_amb += 1
                stats_for(inverted_matches.correction_rule_id).tp += 1
            else:
                error_case = ErrorCase(fn_id(expected, fired_id_inverted), sentence, inverted, True)
                (fn_sense if expected == SENSE_ACCENT else fn_amb).append(error_case.format())
                (fn_sense_cases if expected == SENSE_ACCENT else fn_amb_cases).append(error_case)
                stats_for(error_case.id).fn += 1

    seen = set()
    for cases in (fp_sense_cases, fp_amb_cases, fn_sense_cases, fn_amb_cases):
        collect_verb_noun_contexts_from_errors(tool, cases, seen, contexts)

    # Fitxer ambigu: cap forma (original ni invertida) hauria de generar avisos
    fp_ambig = []
    if os.path.exists(ambig_corpus):
        with open(ambig_corpus, encoding='utf-8') as f:
            for line in f.read().splitlines():
                sentence = line.strip()
                if not sentence:
                    continue
                fired_orig = evaluate_sentence(tool, sentence).first_match_id
                if fired_orig is not None:
                    fp_ambig.append('[orig][' + fired_orig + '] ' + sentence)
                inverted = invert_que(sentence)
                if inverted is not None and inverted != sentence:
                    fired_inv = evaluate_sentence(tool, inverted).first_match_id
                    if fired_inv is not None:
                        fp_ambig.append('[inv] [' + fired_inv + '] ' + inverted)

    os.makedirs(report_dir, exist_ok=True)
    j = os.path.join
    write_lines(j(report_dir, 'false_positives_sense_accent.txt'), fp_sense)
    write_lines(j(report_dir, 'false_positives_amb_accent.txt'), fp_amb)
    write_lines(j(report_dir, 'false_negatives_sense_accent.txt'), fn_sense)
    write_lines(j(report_dir, 'false_negatives_amb_accent.txt'), fn_amb)
    write_lines(j(report_dir, 'false_positives_ambig.txt'), fp_ambig)
    write_lines(j(report_dir, 'rule_stats.tsv'), format_rule_stats(stats_by_rule))
    write_lines(j(report_dir, 'verbs_after_que_accent.txt'), sort_by_freq(verbs_after_que_accent))
    write_lines(j(report_dir, 'verbs_after_que.txt'), sort_by_freq(verbs_after_que))
    write_verb_noun_context_reports(report_dir, contexts)
    write_lines(j(report_dir, 'hipotesi_que_accent_sense_verb.txt'), accent_no_verb_examples)

    applicable_sense = tp_sense + len(fn_sense)
    applicable_amb = tp_amb + len(fn_amb)
    applicable_total = applicable_sense + applicable_amb
    report = []
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report.append('========================================================\n')
    report.append('=== QUE_INICI corpus report -- ' + timestamp + ' ===\n')
    report.append('Avaluador v2: match sobre el primer que/què; TP per restitució exacta, no per ID.\n')
    report.append('Corpus dir: ' + os.path.realpath(corpus_dir) + '\n')
    report.append('Report dir: ' + os.path.realpath(report_dir) + '\n')
    report.append('Corpus principal (%s): %d línies\n' % (os.path.basename(main_corpus), len(lines)))
    report.append('Selecció queInici.sense (activació explícita): [%s]\n' % ', '.join(SENSE_IDS))
    report.append('Selecció queInici.amb (activació explícita):   [%s]\n' % ', '.join(AMB_IDS))
    report.append('Corpus ambigu: ' + (os.path.realpath(ambig_corpus) if os.path.isfile(ambig_corpus) else 'ABSENT')
                  + '\n')
    append_rule_stats(report, SENSE_ACCENT, len(fp_sense), tp_sense, len(fn_sense), applicable_sense)
    append_rule_stats(report, AMB_ACCENT, len(fp_amb), tp_amb, len(fn_amb), applicable_amb)
    report.append('--- Global ---\n')
    append_metrics(report, len(fp_sense) + len(fp_amb), tp_sense + tp_amb, len(fn_sense) + len(fn_amb),
                   applicable_total)
    report.append('FP (corpus ambigu, orig+inv):  %d\n' % len(fp_ambig))
    report.append('--- Hipòtesi "sense estructura verbal -> que" ---\n')
    accent_total = accent_verb + accent_no_verb
    sense_accent_total = sense_accent_verb + sense_accent_no_verb
    report.append('  Què  (amb accent): amb verb %d / sense verb %d  (sense verb: %.1f%%)\n' % (
        accent_verb, accent_no_verb, 0.0 if accent_total == 0 else 100.0 * accent_no_verb / accent_total))
    report.append('  Que  (sense accent): amb verb %d / sense verb %d  (sense verb: %.1f%%)\n' % (
        sense_accent_verb, sense_accent_no_verb,
        0.0 if sense_accent_total == 0 else 100.0 * sense_accent_no_verb / sense_accent_total))
    report.append('  FP potencials de SENSE_ACCENT si apliquem "sense verb -> que": %d\n' % accent_no_verb)
    report = ''.join(report)
    print(report, end='')
    print('Detall a: ' + os.path.abspath(report_dir))
    with open(j(report_dir, 'results.log'), 'a', encoding='utf-8') as f:
        f.write(report + '\n')
    assert applicable_total > 0, "No s'ha processat cap frase invertida"
