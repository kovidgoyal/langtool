"""The checker. Port of org.languagetool.JLanguageTool (without remote rules,
language models and spell checking)."""

import threading

from . import global_config
from .analysis import (AnalyzedToken, AnalyzedTokenReadings, AnalyzedSentence, SENTENCE_START_TAGNAME,
                       copy_readings)
from .messages import messages_for
from .patterns.ruleset import RuleSet
from .rules.base import (RuleMatch, TextLevelRule, same_rule_group_filter, clean_overlapping_filter)
from .rules.transformers import transform_pattern_rules

LEVEL_DEFAULT = 'DEFAULT'
LEVEL_PICKY = 'PICKY'

PARA_NORMAL = 'NORMAL'
PARA_ONLYPARA = 'ONLYPARA'
PARA_ONLYNONPARA = 'ONLYNONPARA'


# the characters that are markup in a plain text: the hiddenChars of AnnotatedTextBuilder and the zero width no-break
# space (or BOM) of JLanguageTool.cleanText
_HIDDEN_CHARS = frozenset('\u00ad\u202d\u202c\ufeff')


class AnnotatedText:
    """Text consisting of plain text and markup parts. Only the plain text is
    checked, positions of matches refer to the original text."""

    def __init__(self, parts=(), global_meta_data=None):
        self.parts = []  # list of (is_markup, text, interpret_as)
        for p in parts:
            self.parts.append(p)
        # AnnotatedTextBuilder.addGlobalMetaData: key (e.g. 'EmailToAddress', AnnotatedText.MetaDataKey) -> value
        self.global_meta_data = dict(global_meta_data or {})
        self._build()

    def get_global_meta_data(self, key, default_value=None):
        """AnnotatedText.getGlobalMetaData(key, defaultValue)"""
        return self.global_meta_data.get(key, default_value)

    @classmethod
    def from_text(cls, text):
        # AnnotatedTextBuilder.addText: the hidden characters (soft hyphen, U+202D, U+202C) are markup, and
        # like JLanguageTool.cleanText: BOM/zero width non breaking spaces are markup
        if not any(c in text for c in _HIDDEN_CHARS):
            # (the result of the loop below for a text without hidden characters)
            return cls([(False, text, None)] if text else [])
        parts = []
        buf = []
        for c in text:
            if c in _HIDDEN_CHARS:
                if buf:
                    parts.append((False, ''.join(buf), None))
                    buf = []
                parts.append((True, c, ''))
            else:
                buf.append(c)
        if buf:
            parts.append((False, ''.join(buf), None))
        return cls(parts)

    def _build(self):
        if all(not is_markup for is_markup, _, _ in self.parts):
            # (the result of the loop below if there is no markup)
            self.plain_text = ''.join(text for _, text, _ in self.parts)
            self.original_length = len(self.plain_text)
            self._mapping = list(range(self.original_length + 1))
            return
        plain = []
        mapping = []  # plain index -> original index
        orig = 0
        for is_markup, text, interpret_as in self.parts:
            if is_markup:
                if interpret_as:
                    for c in interpret_as:
                        plain.append(c)
                        mapping.append(orig)
                orig += len(text)
            else:
                for c in text:
                    plain.append(c)
                    mapping.append(orig)
                    orig += 1
        mapping.append(orig)
        self.plain_text = ''.join(plain)
        self.original_length = orig
        self._mapping = mapping

    def original_position(self, plain_pos, is_to_pos=False):
        m = self._mapping
        if is_to_pos:
            if plain_pos <= 0:
                return 0
            return m[min(plain_pos - 1, len(m) - 1)] + 1
        return m[min(plain_pos, len(m) - 1)]


class SentenceData:
    __slots__ = ('analyzed', 'text', 'start_offset', 'start_line', 'start_column', 'word_count')

    def __init__(self, analyzed, text, start_offset, start_line, start_column):
        self.analyzed = analyzed
        self.text = text
        self.start_offset = start_offset
        self.start_line = start_line
        self.start_column = start_column
        self.word_count = len(analyzed.non_blank_tokens)


def count_line_breaks(s):
    return s.count('\n')


class JLanguageTool:

    def __init__(self, language, mother_tongue=None, user_config=None, rules=None, level=LEVEL_DEFAULT):
        self.language = language
        self.mother_tongue = mother_tongue
        self.user_config = user_config
        self.check_cancelled_callback = None
        self.messages = messages_for(language.short_code, language.countries[0] if len(language.countries) == 1
                                     else None)
        self.disabled_rules = set()
        self.enabled_rules = set()
        self.disabled_categories = set()
        self.enabled_categories = set()
        self.clean_overlapping_matches = True
        self.level = level
        self.match_filters = []
        self.list_unknown_words = False
        self.unknown_words = set()
        self.print_stream = None
        self._lock = threading.RLock()
        if rules is not None:
            self.builtin_rules = list(rules)
            self.user_rules = []
        else:
            self.builtin_rules = list(language.get_relevant_rules(self.messages, user_config, mother_tongue))
            self.user_rules = []
            self._activate_default_pattern_rules()
        self._rule_set_cache = {}

    def _activate_default_pattern_rules(self):
        lang = self.language
        prules = lang.get_pattern_rules()
        enabled = lang.get_default_enabled_rules_for_variant()
        disabled = lang.get_default_disabled_rules_for_variant()
        if enabled or disabled:
            for r in prules:
                if r.get_id() in enabled:
                    r.set_default_on()
                if r.get_id() in disabled:
                    r.set_default_off()
        self.user_rules.extend(transform_pattern_rules(prules, lang))

    # --- rule configuration ---

    def add_rule(self, rule):
        self.user_rules.append(rule)
        self._rule_set_cache.clear()

    def remove_rule(self, rule):
        """Remove a rule added with add_rule() or a built-in rule."""
        self.user_rules = [r for r in self.user_rules if r is not rule]
        self.builtin_rules = [r for r in self.builtin_rules if r is not rule]
        self._rule_set_cache.clear()

    def disable_rule(self, rule_id):
        self.disabled_rules.add(rule_id)
        self.enabled_rules.discard(rule_id)
        self._rule_set_cache.clear()

    def disable_rules(self, rule_ids):
        for r in rule_ids:
            self.disable_rule(r)

    def enable_rule(self, rule_id):
        self.disabled_rules.discard(rule_id)
        self.enabled_rules.add(rule_id)
        self._rule_set_cache.clear()

    def disable_category(self, cat_id):
        self.disabled_categories.add(cat_id)
        self.enabled_categories.discard(cat_id)
        self._rule_set_cache.clear()

    def enable_category(self, cat_id):
        self.disabled_categories.discard(cat_id)
        self.enabled_categories.add(cat_id)
        self._rule_set_cache.clear()

    def get_all_rules(self):
        return self.builtin_rules + self.user_rules

    def ignore_rule(self, rule):
        cat = rule.category
        cat_id = cat.id if cat is not None else None
        disabled_rules = self.disabled_rules
        enabled_rules = self.enabled_rules
        # (the full id is only needed if rules are enabled or disabled)
        fid = rule.get_full_id() if disabled_rules or enabled_rules else None
        rid = rule.get_id()
        is_cat_disabled = (cat_id in self.disabled_categories or (cat is not None and cat.is_default_off())) and \
            cat_id not in self.enabled_categories
        if is_cat_disabled:
            return not (fid in enabled_rules or rid in enabled_rules)
        return fid in disabled_rules or rid in disabled_rules or \
            (rule.default_off and not (fid in enabled_rules or rid in enabled_rules))

    def get_all_active_rules(self):
        return [r for r in self.get_all_rules() if not self.ignore_rule(r)]

    def _active_rule_set(self, level):
        rs = self._rule_set_cache.get(level)
        if rs is None:
            rules = [r for r in self.get_all_active_rules() if is_rule_active_for_level(r, level)]
            rs = self._rule_set_cache[level] = RuleSet(rules, with_lemma_hints=True)
            rs.text_level_rules = [r for r in rules if r.is_text_level_rule()]
        return rs

    def _active_rule_ids(self, level):
        """RuleSet.allRuleIds() of the active rules for the level"""
        rs = self._active_rule_set(level)
        ids = getattr(rs, 'all_rule_ids', None)
        if ids is None:
            ids = rs.all_rule_ids = frozenset(r.get_id() for r in rs.all_rules)
        return ids

    # --- analysis ---

    def sentence_tokenize(self, text):
        return self.language.sentence_tokenizer.tokenize(text)

    def get_raw_analyzed_sentence(self, sentence):
        lang = self.language
        tokens = lang.word_tokenizer.tokenize(sentence)
        soft = self._replace_soft_hyphens(tokens)
        a_tokens = lang.tagger.tag(tokens)
        chunker = lang.chunker
        if chunker is not None:
            chunker.add_chunk_tags(a_tokens)
        token_array = [AnalyzedTokenReadings([AnalyzedToken('', SENTENCE_START_TAGNAME, None)], 0)]
        start_pos = 0
        for t in a_tokens:
            t.start_pos = start_pos
            token_array.append(t)
            start_pos += len(t.token)
        pos_fix = 0
        for i, t in enumerate(a_tokens):
            if i > 0:
                t.set_whitespace_before(a_tokens[i - 1].token)
                t.start_pos = t.start_pos + pos_fix
                t.pos_fix = pos_fix
            if soft and i in soft:
                orig, clean = soft[i]
                pos_fix += len(orig) - len(t.token)
                t.add_reading(lang.tagger.create_token(orig, None), 'softHyphenTokens')
                t.clean_token = clean
        last = len(token_array) - 1
        for i in range(len(token_array) - 1):
            if not token_array[last - i].is_whitespace:
                last -= i
                break
        token_array[last].set_sentence_end()
        if len(token_array) == last + 1 and token_array[last].is_linebreak:
            token_array[last].set_paragraph_end()
        return AnalyzedSentence(token_array)

    def _replace_soft_hyphens(self, tokens):
        rx = self.language.ignored_characters_regex
        out = {}
        if rx is None:
            return out
        for i, t in enumerate(tokens):
            if rx.search(t):
                cleaned = rx.sub('', t)
                out[i] = (t, cleaned)
                tokens[i] = cleaned
        return out

    def get_analyzed_sentence(self, sentence):
        raw = self.get_raw_analyzed_sentence(sentence)
        pre = copy_readings(raw.tokens)
        disamb = self.language.disambiguator.disambiguate(raw)
        analyzed = AnalyzedSentence(disamb.tokens, pre)
        chunker = self.language.post_disambiguation_chunker
        if chunker is not None:
            chunker.add_chunk_tags(list(analyzed.tokens))
        return analyzed

    def set_check_cancelled_callback(self, callback):
        """callback() returning True stops the check (port of
        setCheckCancelledCallback)"""
        self.check_cancelled_callback = callback

    def _cancelled(self):
        cb = self.check_cancelled_callback
        return cb is not None and cb()

    def set_output(self, print_stream):
        """JLanguageTool.setOutput: the stream (a file-like object) to print
        the analyzed sentences and the disambiguator log to, None for no
        output. Like in Java this switches the global verbose mode
        (langtool.global_config) on or off."""
        self.print_stream = print_stream
        global_config.set_verbose(print_stream is not None)

    def set_list_unknown_words(self, list_unknown_words):
        """Whether to store the unknown words of the checked texts, see
        get_unknown_words()."""
        self.list_unknown_words = list_unknown_words

    def get_unknown_words(self):
        """The sorted list of unknown words in the latest run of check()
        (Java's String order)."""
        if not self.list_unknown_words:
            raise RuntimeError('listUnknownWords is set to false, unknown words not stored')
        return sorted(self.unknown_words, key=lambda w: w.encode('utf-16-be', 'surrogatepass'))

    def _remember_unknown_words(self, analyzed):
        if self.list_unknown_words:
            for reading in analyzed.non_blank_tokens:
                if not reading.is_tagged():
                    self.unknown_words.add(reading.token)

    def _print_sentence_info(self, analyzed):
        if self.print_stream is not None:
            print(str(analyzed), file=self.print_stream)
            print(analyzed.get_annotations(), file=self.print_stream)

    def analyze_sentences(self, sentences):
        self.unknown_words = set()
        out = []
        n = len(sentences)
        for j, s in enumerate(sentences):
            if self._cancelled():
                break
            a = self.get_analyzed_sentence(s)
            self._remember_unknown_words(a)
            if j + 1 == n:
                a = mark_as_paragraph_end(a)
            out.append(a)
            self._print_sentence_info(a)
        return out

    def analyze_text(self, text):
        return self.analyze_sentences(self.sentence_tokenize(text))

    # --- checking ---

    def check(self, text, tokenize_text=True, para_mode=PARA_NORMAL, level=None):
        if not isinstance(text, AnnotatedText):
            text = AnnotatedText.from_text(text)
        level = level or self.level
        plain = text.plain_text
        sentences = self.sentence_tokenize(plain) if tokenize_text else [plain]
        analyzed = self.analyze_sentences(sentences)
        return self.check_internal(text, para_mode, level, sentences, analyzed)

    def check_internal(self, annotated_text, para_mode, level, sentences, analyzed):
        rule_set = self._active_rule_set(level)
        sdata = self._compute_sentence_data(analyzed, sentences)
        matches = []
        if para_mode != PARA_ONLYNONPARA:
            matches.extend(self._text_level_matches(rule_set, sdata, annotated_text, analyzed))
        if para_mode != PARA_ONLYPARA:
            matches.extend(self._other_rule_matches(rule_set, sdata, annotated_text, para_mode))
        if not matches:
            return matches
        return self._filter_matches(annotated_text, matches, level)

    def _filter_matches(self, annotated_text, matches, level):
        matches = [m for m in matches if not self.ignore_rule(m.rule)]
        matches = [m for m in matches if is_rule_active_for_level(m.rule, level)]
        matches = same_rule_group_filter(matches)
        # LanguageDependentRuleMatchFilter
        matches = self.language.filter_rule_matches(matches, annotated_text, self._active_rule_ids(level))
        if self.clean_overlapping_matches:
            matches = clean_overlapping_filter(matches, self.language)
        matches = self.language.filter_rule_matches_after_overlapping(matches)
        for f in self.match_filters:
            matches = f(matches, annotated_text)
        return matches

    def _compute_sentence_data(self, analyzed, texts):
        out = []
        char_count = line_count = 0
        column = 1
        for a, t in zip(analyzed, texts):
            out.append(SentenceData(a, t, char_count, line_count, column))
            char_count += len(t)
            line_count += count_line_breaks(t)
            column = self._process_column_change(column, t)
        return out

    def _process_column_change(self, column, sentence):
        lb = sentence.rfind('\n')
        if lb == -1:
            return column + len(sentence)
        column = len(sentence) - lb
        if lb == 0 and not self.language.sentence_tokenizer.single_line_breaks_marks_para():
            column -= 1
        return column

    def _text_level_matches(self, rule_set, sdata, annotated_text, analyzed):
        out = []
        for rule in rule_set.text_level_rules:
            if self._cancelled():
                break
            for m in rule.match(analyzed, annotated_text):
                fl, fc = self._find_line_column(sdata, m.from_pos)
                tl, tc = self._find_line_column(sdata, m.to_pos)
                nm = m.copy()
                nm.set_offset_position(annotated_text.original_position(m.from_pos, False),
                                       annotated_text.original_position(m.to_pos, True))
                nm.line, nm.end_line = fl, tl
                nm.column = fc - (1 if fl == 0 else 0)
                nm.end_column = tc - (1 if tl == 0 else 0)
                out.append(nm)
        return out

    def _find_line_column(self, sdata, offset):
        if not sdata:
            return 0, 0
        lo, hi = 0, len(sdata) - 1
        found = None
        while lo <= hi:
            mid = (lo + hi) // 2
            s = sdata[mid]
            if s.start_offset < offset:
                lo = mid + 1
            elif s.start_offset > offset:
                hi = mid - 1
            else:
                found = s
                break
        if found is None:
            found = sdata[lo - 1]
        prefix = found.text[:offset - found.start_offset]
        return found.start_line + count_line_breaks(prefix), self._process_column_change(found.start_column, prefix)

    def _other_rule_matches(self, rule_set, sdata, annotated_text, para_mode):
        out = []
        for sd in sdata:
            sm = self.check_analyzed_sentence(para_mode, rule_set, sd.analyzed)
            if sm and self._cancelled():
                break
            for m in sm:
                out.append(self.adjust_rule_match_pos(m, sd.start_offset, sd.start_column, sd.start_line, sd.text,
                                                      annotated_text))
        return out

    def check_analyzed_sentence(self, para_mode, rules, analyzed):
        if para_mode == PARA_ONLYPARA:
            return []
        if isinstance(rules, RuleSet):
            matches = rules.match_sentence(analyzed, self)
        else:
            matches = []
            for rule in rules:
                if rule.is_text_level_rule():
                    continue
                if self._cancelled():
                    break
                matches.extend(rule.match(analyzed))
        if not matches:
            return matches
        matches = [m for m in matches if not self.ignore_rule(m.rule)]
        return same_rule_group_filter(matches)

    def adjust_rule_match_pos(self, match, char_count, column_count, line_count, sentence, annotated_text):
        from_pos = match.from_pos + char_count
        to_pos = match.to_pos + char_count
        if annotated_text is not None:
            from_pos = annotated_text.original_position(from_pos, False)
            to_pos = annotated_text.original_position(to_pos, True)
        m = match.copy()
        m.set_offset_position(from_pos, to_pos)
        m.set_sentence_position(match.from_pos, match.to_pos)
        m.set_pattern_position(match.pattern_from_pos + char_count, match.pattern_to_pos + char_count)
        to_error = sentence[:match.from_pos]
        to_end = sentence[:match.to_pos]
        lb = to_error.rfind('\n')
        column = len(to_error) + column_count if lb == -1 else len(to_error) - lb
        lbe = to_end.rfind('\n')
        end_column = len(to_end) + column_count if lbe == -1 else len(to_end) - lbe
        m.line = line_count + count_line_breaks(to_error)
        m.end_line = line_count + count_line_breaks(to_end)
        m.column = column
        m.end_column = end_column
        return m


def correct_text(contents, lt):
    """Port of org.languagetool.tools.Tools.correctText: automatically
    applies the first suggestion of each match of lt.check(contents)."""
    rule_matches = lt.check(contents)
    if not rule_matches:
        return contents
    return correct_text_from_matches(contents, rule_matches)


def correct_text_from_matches(contents, matches):
    """Port of org.languagetool.tools.Tools.correctTextFromMatches"""
    sb = contents
    errors = []
    for rm in matches:
        if rm.suggested_replacements:
            errors.append(sb[rm.from_pos:rm.to_pos])
    offset = 0
    counter = 0
    for rm in matches:
        replacements = rm.suggested_replacements
        if replacements:
            # make sure the error hasn't been already corrected:
            start, end = rm.from_pos - offset, rm.to_pos - offset
            if start >= 0 and end >= start and errors[counter] == sb[start:end]:
                sb = sb[:start] + replacements[0] + sb[end:]
                offset += rm.to_pos - rm.from_pos - len(replacements[0])
            counter += 1
    return sb


def mark_as_paragraph_end(a):
    tokens = a.tokens
    tokens[-1].set_paragraph_end()
    pre = a.pre_disambig_tokens
    pre[len(tokens) - 1].set_paragraph_end()
    return AnalyzedSentence(tokens, pre)


def is_rule_active_for_level(rule, level):
    if level == LEVEL_DEFAULT and 'picky' in rule.tags:
        return False
    if not rule.tone_tags:
        return True
    return not rule.goal_specific
