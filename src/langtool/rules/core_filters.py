"""Language independent rule filters from languagetool-core (the
<filter class="org.languagetool.rules.XXX"> classes)."""

import regex

from .. import jregex
from ..tools import (is_punctuation_or_symbol, is_capitalized_word, is_whitespace, uppercase_first_char,
                     is_not_all_lowercase)
from .filters import RuleFilter

_WS = regex.compile(r'\s+')
_OPENING_QUOTES = regex.compile('[«“"‘\'„¿¡]', regex.DOTALL)


def java_parse_int(s):
    """java.lang.Integer.parseInt: optional sign followed by digits."""
    if s is None:
        raise ValueError('null')
    t = s
    if t[:1] in ('+', '-'):
        t = t[1:]
    if not t or not all(c.isdigit() for c in t):
        raise ValueError('For input string: "%s"' % s)
    v = int(s)
    if not -2 ** 31 <= v < 2 ** 31:
        raise ValueError('For input string: "%s"' % s)
    return v


class AdaptSuggestionsFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule = match.rule
        lang = getattr(rule, 'language', None)
        if lang is None:
            return match
        adjusted = []
        for repl in match.suggested_replacements:
            match.set_original_error_str()
            adjusted.append(adapt_suggestion(lang, repl, match.original_error_str))
        match.set_suggested_replacements(adjusted)
        return match


def adapt_suggestion(lang, s, original_error_str):
    from .. import extensions
    f = extensions.lookup('adapt_suggestion', lang.short_code)
    if f is not None:
        return f(lang, s, original_error_str)
    return s


class AddCommasFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        ss = self.get_optional('suggestSemicolon', arguments)
        suggest_semicolon = ss is not None and ss.lower() == 'true'
        sentence = match.sentence
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        pf = 1
        while pf < n and tokens[pf].start_pos < match.from_pos:
            pf += 1
        pt = pf
        while pt < n and tokens[pt].end_pos < match.to_pos:
            pt += 1
        before_ok = pf == 1 or is_punctuation_or_symbol(tokens[pf - 1].token) or is_capitalized_word(tokens[pf].token)
        after_ok = not (pt + 1 > n - 1) and is_punctuation_or_symbol(tokens[pt + 1].token) and \
            not (tokens[pt + 1].whitespace_before and _OPENING_QUOTES.fullmatch(tokens[pt + 1].token))
        if before_ok and after_ok:
            return None
        from .base import RuleMatch
        text = sentence.text
        nm = None
        if suggest_semicolon and tokens[pf - 1].token == ',' and not after_ok:
            nm = RuleMatch(match.rule, sentence, tokens[pf - 1].start_pos, tokens[pt].end_pos, match.message,
                           match.short_message)
            nm.add_suggested_replacement('; ' + text[match.from_pos:match.to_pos] + ',')
            nm.add_suggested_replacement(', ' + text[match.from_pos:match.to_pos] + ',')
        elif before_ok and not after_ok:
            nm = RuleMatch(match.rule, sentence, tokens[pt].start_pos, match.to_pos, match.message,
                           match.short_message)
            nm.set_suggested_replacement(tokens[pt].token + ',')
        elif not before_ok and after_ok:
            sp = tokens[pf].start_pos
            if tokens[pf].whitespace_before:
                sp -= 1
            nm = RuleMatch(match.rule, sentence, sp, tokens[pf].end_pos, match.message, match.short_message)
            nm.set_suggested_replacement(', ' + tokens[pf].token)
        else:
            sp = tokens[pf].start_pos
            if tokens[pf].whitespace_before:
                sp -= 1
            nm = RuleMatch(match.rule, sentence, sp, tokens[pt].end_pos, match.message, match.short_message)
            nm.set_suggested_replacement(', ' + text[match.from_pos:match.to_pos] + ',')
        return nm


class UnderlineSpacesFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        mode = self.get_required('underlineSpaces', arguments)
        sentence = match.sentence.text
        if mode in ('before', 'both'):
            if match.from_pos - 1 >= 0 and is_whitespace(sentence[match.from_pos - 1:match.from_pos]):
                match.set_offset_position(match.from_pos - 1, match.to_pos)
        if mode in ('after', 'both'):
            if match.to_pos + 1 < len(sentence) and is_whitespace(sentence[match.to_pos:match.to_pos + 1]):
                match.set_offset_position(match.from_pos, match.to_pos + 1)
        return match


class ApostropheTypeFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        word_from = self.get_required('wordFrom', arguments)
        has = self.get_required('hasTypographicalApostrophe', arguments).lower() == 'true'
        if word_from == 'marker':
            pos = 0
            while pos < len(pattern_tokens) and pattern_tokens[pos].start_pos < match.from_pos:
                pos += 1
            pos += 1
        else:
            pos = java_parse_int(word_from)
        if pos < 1 or pos > len(pattern_tokens):
            raise ValueError('ApostropheTypeFilter: Index out of bounds in %s, wordFrom: %d' % (
                match.rule.get_full_id(), pos))
        if has == pattern_tokens[pos - 1].typographic_apostrophe:
            return match
        return None


class WhitespaceCheckFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        ws = self.get_required('whitespaceChar', arguments)
        pos = java_parse_int(self.get_required('position', arguments))
        if pos < 1 or pos > len(pattern_tokens):
            raise ValueError('Wrong position in WhitespaceCheckFilter: %d' % pos)
        if pattern_tokens[pos - 1].whitespace_before_char != ws:
            return match
        return None


class DateRangeChecker(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        try:
            x = java_parse_int(arguments.get('x'))
            y = java_parse_int(arguments.get('y'))
        except ValueError:
            return None
        return match if x >= y else None


class ShortenedYearRangeChecker(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        try:
            x = java_parse_int(arguments.get('x'))
            prefix = arguments.get('x')[:2]
            y = java_parse_int(prefix + arguments.get('y'))
        except (ValueError, TypeError):
            return None
        return match if x >= y else None


_IS_PUNCTUATION = regex.compile(r'\p{P}')


class ConvertToSentenceCaseFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        first_done = False
        repl = []
        orig = []
        n = len(pattern_tokens)
        for i in range(pattern_token_pos, n):
            t = pattern_tokens[i]
            if t.start_pos < match.from_pos or t.end_pos > match.to_pos:
                continue
            nc = self._normalized_case(t)
            if i + 1 < n and pattern_tokens[i + 1].token == '.':
                if len(nc) == 1:
                    nc = nc.upper()
                elif nc == 'corp':
                    nc = 'Corp'
            ts = t.token
            cap = uppercase_first_char(nc)
            if not first_done and not _IS_PUNCTUATION.fullmatch(ts) and ts:
                first_done = True
                repl.append(cap)
                orig.append(ts)
            else:
                if t.whitespace_before:
                    repl.append(' ')
                    orig.append(' ')
                repl.append(nc)
                orig.append(ts)
        if ''.join(repl) == ''.join(orig):
            return None
        match.set_suggested_replacement(''.join(repl))
        return match

    def token_is_exception(self, s):
        return False

    def _normalized_case(self, atr):
        lower = atr.token.lower()
        if atr.typographic_apostrophe:
            lower = lower.replace("'", '’')
        if self.token_is_exception(lower):
            return lower
        cap = uppercase_first_char(lower)
        lemma_cap = lemma_lower = False
        for at in atr.readings:
            if at.has_no_pos_tag or at.lemma is None:
                return cap
            lemma = at.lemma.split(' ')[0]
            lemma_cap = lemma_cap or is_capitalized_word(lemma)
            lemma_lower = lemma_lower or not is_not_all_lowercase(lemma)
        if lemma_lower:
            return lower
        if lemma_cap:
            return cap
        return atr.token


class CheckPostagsInSuggestionFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        lang = match.rule.language
        tagger = lang.tagger
        new = []
        tags = self.get_required('PostagsList', arguments).split(',')
        for repl in match.suggested_replacements:
            toks = _WS.split(repl)
            if len(toks) != len(tags) or not tags:
                raise ValueError('Mismatch between number of tokens and number of tags in rule %s' %
                                 match.rule.get_full_id())
            atrs = tagger.tag(toks)
            ok = True
            for i, t in enumerate(tags):
                ok = ok and atrs[i].matches_pos_tag_regex(t)
                if not ok:
                    break
            if ok:
                new.append(repl)
        if not new:
            return None
        match.set_suggested_replacements(new)
        return match


class PartialPosTagFilter(RuleFilter):
    """Abstract: subclasses implement tag(token) -> list of
    AnalyzedTokenReadings."""

    def tag(self, token):
        raise NotImplementedError()

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        if not ('no' in args and 'regexp' in args and 'postag_regexp' in args):
            raise ValueError("Set 'no', 'regexp' and 'postag_regexp' for filter PartialPosTagFilter")
        pos = java_parse_int(args['no'])
        pattern = jregex.compile(args['regexp'])
        required = args['postag_regexp']
        negate_pos = 'negate_pos' in args
        two = 'two_groups_regexp' in args
        token = args.get('prefix', '') + pattern_tokens[pos - 1].token + args.get('suffix', '')
        if pattern.groups != 1 and not two:
            raise ValueError('Got %d groups for regex %r, expected 1' % (pattern.groups, args['regexp']))
        if pattern.groups != 2 and two:
            raise ValueError('Got %d groups for regex %r, expected 2' % (pattern.groups, args['regexp']))
        m = pattern.fullmatch(token)
        if m:
            partial = m.group(1) or ''
            if pattern.groups == 2:
                partial += m.group(2) or ''
            tags = self.tag(partial)
            if tags is not None and self._partial_tag_has_required_tag(tags, required, negate_pos):
                return match
            return None
        return None

    @staticmethod
    def _partial_tag_has_required_tag(tags, required, negate_pos):
        p = jregex.compile(required)
        count = 0
        for atr in tags:
            for at in atr.readings:
                if at.pos_tag is not None:
                    if negate_pos:
                        count += 1
                        if p.fullmatch(at.pos_tag):
                            return False
                    elif p.fullmatch(at.pos_tag):
                        return True
        return False if count == 0 else negate_pos


class IsEnglishWordFilter(RuleFilter):

    def __init__(self, language=None):
        super().__init__(language)
        self._tagger = None

    def _get_tagger(self):
        if self._tagger is None:
            from ..api import get_language
            try:
                self._tagger = get_language('en-US').tagger
            except Exception:
                self._tagger = False
        return self._tagger or None

    def accept_rule_match(self, match, args, pattern_token_pos, pattern_tokens, token_positions):
        tagger = self._get_tagger()
        if tagger is None:
            return None
        forms = [pattern_tokens[self.get_skip_corrected_reference(token_positions, java_parse_int(p))].token
                 for p in self.get_required('formPositions', args).split(',')]
        ok = True
        postags = self.get_optional('postags', args)
        if postags is not None:
            pts = postags.split(',')
            if len(pts) != len(forms):
                raise ValueError('The number of forms and postags has to be the same in rule with filter '
                                 'IsEnglishWordFilter.')
            for f, p in zip(forms, pts):
                ok = ok and tagger.tag([f])[0].matches_pos_tag_regex(p)
        else:
            for f in forms:
                ok = ok and tagger.tag([f])[0].is_tagged()
        return match if ok else None


class SuppressIfAnyRuleMatchesFilter(RuleFilter):

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        rule_ids = self.get_required('ruleIDs', arguments).split(',')
        fast_only = self.get_optional('fastOnly', arguments, 'false') == 'true'
        lang = match.rule.language
        lt = _default_tool(lang)
        sentence = match.sentence.text
        for repl in match.suggested_replacements:
            partial = self._replace_token(match, repl, lang)
            if partial is not None:
                if self._any_rule_matches(lt, rule_ids, partial, match):
                    return None
                if fast_only:
                    continue
            new_sentence = sentence[:match.from_pos] + repl + sentence[match.to_pos:]
            analyzed = lt.analyze_text(new_sentence)[0]
            if self._any_rule_matches(lt, rule_ids, analyzed, match):
                return None
        return match

    @staticmethod
    def _any_rule_matches(lt, rule_ids, analyzed, match):
        for r in lt.get_all_active_rules():
            if r.get_id() in rule_ids and not r.is_text_level_rule():
                for m in r.match(analyzed):
                    if (match.from_pos <= m.to_pos <= match.to_pos) or (m.from_pos <= match.to_pos <= m.to_pos):
                        return True
        return False

    @staticmethod
    def _replace_token(match, repl, lang):
        from ..analysis import AnalyzedTokenReadings, AnalyzedSentence
        f, t = match.from_pos, match.to_pos
        if len(repl) != t - f or ' ' in repl:
            return None
        s = match.sentence
        tokens = s.tokens
        idx = -1
        for i, tok in enumerate(tokens):
            if not tok.is_whitespace and tok.start_pos == f:
                idx = i
                break
        if idx < 0:
            return None
        tagged = lang.tagger.tag([repl])
        if len(tagged) != 1:
            return None
        new_tokens = list(tokens)
        new_tokens[idx] = AnalyzedTokenReadings.from_old(tokens[idx], tagged[0].readings,
                                                         'SuppressIfAnyRuleMatchesFilter')
        new_pre = list(s.pre_disambig_tokens)
        new_pre[idx] = new_tokens[idx]
        return AnalyzedSentence(new_tokens, new_pre)


_tools = {}


def _default_tool(lang):
    """Port of Language.createDefaultJLanguageTool()"""
    from ..tool import JLanguageTool
    t = _tools.get(lang.code)
    if t is None:
        t = _tools[lang.code] = JLanguageTool(lang)
    return t


def register(ff):
    p = 'org.languagetool.rules.'
    ff.register(p + 'AdaptSuggestionsFilter', AdaptSuggestionsFilter)
    ff.register(p + 'AddCommasFilter', AddCommasFilter)
    ff.register(p + 'UnderlineSpacesFilter', UnderlineSpacesFilter)
    ff.register(p + 'patterns.ApostropheTypeFilter', ApostropheTypeFilter)
    ff.register(p + 'WhitespaceCheckFilter', WhitespaceCheckFilter)
    ff.register(p + 'DateRangeChecker', DateRangeChecker)
    ff.register(p + 'ShortenedYearRangeChecker', ShortenedYearRangeChecker)
    ff.register(p + 'ConvertToSentenceCaseFilter', ConvertToSentenceCaseFilter)
    ff.register(p + 'CheckPostagsInSuggestionFilter', CheckPostagsInSuggestionFilter)
    ff.register(p + 'IsEnglishWordFilter', IsEnglishWordFilter)
    ff.register(p + 'SuppressIfAnyRuleMatchesFilter', SuppressIfAnyRuleMatchesFilter)
