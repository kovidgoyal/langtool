"""Language independent rules implemented in code (port of rules from
org.languagetool.rules in languagetool-core)."""

import regex

from ..tokenizers import is_url, is_email
from ..tools import (is_non_breaking_whitespace, is_field_code_token, uppercase_first_char, is_camel_case,
                     is_lower_case, is_letter, is_digit, is_not_word_character, contains_line_break,
                     java_trim, is_emoji, is_numeric_space, java_equals_ignore_case, is_numeric)
from .base import Rule, TextLevelRule, RuleMatch, Category


class Categories:
    _defs = {
        'CASING': 'category_case', 'COMPOUNDING': 'category_compounding', 'GRAMMAR': 'category_grammar',
        'TYPOS': 'category_typo', 'PUNCTUATION': 'category_punctuation', 'TYPOGRAPHY': 'category_typography',
        'CONFUSED_WORDS': 'category_confused_words', 'REPETITIONS': 'category_repetitions',
        'REDUNDANCY': 'category_redundancy', 'REPETITIONS_STYLE': 'cateogry_repetitions_style',
        'STYLE': 'category_style', 'PLAIN_ENGLISH': 'category_plain_english',
        'GENDER_NEUTRALITY': 'category_gender_neutrality', 'SEMANTICS': 'category_semantics',
        'COLLOQUIALISMS': 'category_colloquialism', 'REGIONALISMS': 'category_regionalisms',
        'FALSE_FRIENDS': 'category_false_friend', 'WIKIPEDIA': 'category_wikipedia', 'MISC': 'category_misc',
    }

    @classmethod
    def get(cls, id, messages):
        return Category(id, messages.get(cls._defs[id], id))


def is_paragraph_end(sentences, n, single_line_breaks_marks_para=False):
    """Port of Tools.isParagraphEnd"""
    if n >= len(sentences) - 1:
        return True
    t = sentences[n].text
    if single_line_breaks_marks_para:
        if t.endswith('\n') or t.endswith('\n\r'):
            return True
    elif t.endswith('\n\n') or t.endswith('\n\r\n\r') or t.endswith('\r\n\r\n'):
        return True
    nt = sentences[n + 1].text
    return nt.startswith('\n') or nt.startswith('\r\n')


class CoreRule(Rule):
    category_id = 'MISC'
    issue_type = 'Uncategorized'

    def __init__(self, messages, language=None):
        super().__init__()
        self.messages = messages
        self.language = language
        self.category = Categories.get(self.category_id, messages)
        self.loc_quality_issue_type = self.issue_type

    def get_id(self):
        return self.rule_id

    def get_description(self):
        return self.messages.get(self.description_key, self.rule_id)


class CoreTextLevelRule(TextLevelRule, CoreRule):
    pass


_FILE_EXTENSION = regex.compile(r'([a-z]{3,4}|[A-Z]{3,4}|ai|mp[34]|MP[34])(-.+)?')
_DOMAIN = regex.compile(r'(?i)(com|org|net|int|edu|gov|mil|[a-z]{2})')
_LETTERS = regex.compile(r'[a-zA-Z]+')


def _is_quote(s):
    return len(s) == 1 and s in '\'"’”“«»'


def _is_hyphen_or_comma(s):
    return len(s) == 1 and s in '-,'


def _contains_digit(s):
    return any(is_digit(c) for c in s)


class CommaWhitespaceRule(CoreRule):
    rule_id = 'COMMA_PARENTHESIS_WHITESPACE'
    category_id = 'TYPOGRAPHY'
    issue_type = 'Whitespace'
    description_key = 'desc_comma_whitespace'

    def __init__(self, messages, language=None, quotes_whitespace_check=True):
        super().__init__(messages, language)
        self.quotes_whitespace_check = quotes_whitespace_check

    def get_comma_character(self):
        return ','

    def is_exception(self, tokens, i):
        return False

    def match(self, sentence):
        msgs = self.messages
        out = []
        tokens = sentence.tokens
        prev = ''
        prevprev = ''
        prev_white = False
        comma = self.get_comma_character()
        text = sentence.text
        n = len(tokens)
        for i in range(n):
            atr = tokens[i]
            token = atr.token
            is_white = (atr.is_whitespace or is_non_breaking_whitespace(token) or atr.is_field_code()) and \
                token != '​'
            two = False
            msg = sugg = None
            if is_white and prev[:1] == '(':
                exc = i + 1 < n and prev == '[' and token == ' ' and tokens[i + 1].token == ']'
                if not exc:
                    msg = msgs['no_space_after']
                    sugg = prev
            elif is_white and _is_quote(prev) and self.quotes_whitespace_check and prevprev == ' ':
                msg = msgs['no_space_around_quotes']
                sugg = prev
                two = True
            elif (not is_white and prev == comma and not _is_quote(token) and not _is_hyphen_or_comma(token)
                  and not _contains_digit(prevprev) and not _contains_digit(token) and prevprev != ','):
                msg = msgs['missing_space_after_comma']
                sugg = comma + ' ' + token
            elif prev_white:
                if token[:1] == ')':
                    exc = token == ']' and prev == ' ' and prevprev == '['
                    if not exc:
                        msg = msgs['no_space_before']
                        sugg = token
                elif token == comma:
                    msg = msgs['space_after_comma']
                    sugg = comma
                    if i + 1 < n and comma == tokens[i + 1].token:
                        msg = None
                    if i + 1 < n and not tokens[i + 1].is_whitespace:
                        sugg = comma + ' '
                elif token == '.' and not (i + 1 < n and _DOMAIN.fullmatch(tokens[i + 1].token)) and \
                        not (i + 1 < n and _FILE_EXTENSION.fullmatch(tokens[i + 1].token)) and \
                        not _is_proper_noun(atr):
                    msg = msgs['no_space_before_dot']
                    sugg = '.'
                    if i + 1 < n and _is_digit_or_dot(tokens[i + 1].token):
                        msg = None
                    elif i + 2 < n and tokens[i + 1].token == '/' and _LETTERS.fullmatch(tokens[i + 2].token):
                        msg = None
            if msg is not None and not self.is_exception(tokens, i) and not atr.immunized:
                from_pos = tokens[i - 1].start_pos
                if two:
                    from_pos = tokens[i - 2].start_pos
                to_pos = atr.end_pos
                if to_pos < len(text):
                    marked = text[from_pos:to_pos]
                    if marked == sugg and not two:
                        prevprev = prev
                        prev = token
                        prev_white = is_white and not atr.is_field_code()
                        continue
                rm = RuleMatch(self, sentence, from_pos, to_pos, msg)
                if two:
                    rm.add_suggested_replacement(sugg + ' ')
                    rm.add_suggested_replacement(' ' + sugg)
                else:
                    rm.set_suggested_replacement(sugg)
                out.append(rm)
            prevprev = prev
            prev = token
            prev_white = is_white and not atr.is_field_code()
        return out


def _is_proper_noun(atr):
    return atr.has_pos_tag('NNP') or atr.has_pos_tag('NNPS') or atr.has_pos_tag_starting_with('NP')


def _is_digit_or_dot(s):
    if not s:
        return False
    return s[0] == '.' or is_digit(s[0])


class DoublePunctuationRule(CoreRule):
    rule_id = 'DOUBLE_PUNCTUATION'
    category_id = 'PUNCTUATION'
    issue_type = 'Typographical'
    description_key = 'desc_double_punct'

    def get_comma_character(self):
        return ','

    def get_dot_message(self):
        return self.messages['two_dots']

    def get_comma_message(self):
        return self.messages['two_commas']

    def match(self, sentence):
        out = []
        tokens = sentence.non_blank_tokens
        start_pos = 0
        dot_count = comma_count = 0
        comma = self.get_comma_character()
        n = len(tokens)
        for i in range(1, n):
            token = tokens[i].token
            nxt = tokens[i + 1].token if i < n - 1 else None
            pp = tokens[i - 2].token if i > 1 else None
            if token == '.':
                dot_count += 1
                comma_count = 0
                start_pos = tokens[i].start_pos
            elif token == comma:
                comma_count += 1
                dot_count = 0
                start_pos = tokens[i].start_pos
            if dot_count == 2 and nxt not in ('.', '…') and token != '/' and nxt != '/' and token != '\\' and \
                    nxt != '\\' and pp not in ('?', '!', '…', '.'):
                rm = RuleMatch(self, sentence, max(0, start_pos - 1), start_pos + 1, self.get_dot_message(),
                               self.messages['double_dots_short'])
                rm.add_suggested_replacement('.')
                rm.add_suggested_replacement('…')
                out.append(rm)
                dot_count = 0
            elif comma_count == 2 and nxt != comma:
                rm = RuleMatch(self, sentence, max(0, start_pos - 1), start_pos + 1, self.get_comma_message(),
                               self.messages['double_commas_short'])
                rm.set_suggested_replacement(comma)
                out.append(rm)
                comma_count = 0
            if token != '.' and token != comma:
                dot_count = comma_count = 0
        return out


_NUMERALS_EN_UC = regex.compile(r'[a-z]|(m{0,4}(c[md]|d?c{0,3})(x[cl]|l?x{0,3})(i[xv]|v?i{0,3}))$')
_CONTAINS_DIGIT = regex.compile(r'[^\n\r\x85  ]*[0-9][^\n\r\x85  ]*')
_ONLY_LOWERCASE_START = regex.compile(r'[a-z][A-Z][^\n\r\x85  ]*')
_WHITESPACE_OR_QUOTE = regex.compile('[ "\'„«»‘’“”\\n]')
_SENTENCE_END1 = regex.compile(r'[.?!…]|')
_UC_EXCEPTIONS = frozenset(('n', 'w', 'x86', 'ⓒ', 'ø', 'cc', 'pH', 'heylogin'))
_DIGIT_DOT = regex.compile(r'[0-9]+\. [^\n\r\x85  ]*')
_LINEBREAK_DIGIT_DOT = regex.compile('[^\\n\\r\\x85\\u2028\\u2029]*\\n[0-9]+\\. ')


class UppercaseSentenceStartRule(CoreTextLevelRule):
    rule_id = 'UPPERCASE_SENTENCE_START'
    category_id = 'CASING'
    issue_type = 'Typographical'
    description_key = 'desc_uppercase_sentence'

    def is_exception(self, tokens, i):
        return False

    def match(self, sentences, annotated_text=None):
        last_para = ''
        out = []
        if len(sentences) == 1 and len(sentences[0].tokens) == 2:
            return out
        pos = 0
        prev_numbered = False
        lang_code = self.language.short_code
        for sentence in sentences:
            tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
            if len(tokens) < 2:
                return out
            mpos = 1
            first_obj = tokens[mpos]
            first = first_obj.token
            second = third = None
            if len(tokens) >= 3 and self._is_quote_start(first, lang_code):
                mpos = 2
                second = tokens[mpos].token
            fd = None
            if lang_code == 'nl' and len(tokens) > 3 and first == "'" and second in ('k', 'm', 'n', 'r', 's', 't'):
                fd = tokens[3].token
            if fd is not None:
                third = fd
                mpos = 3
            if self.is_exception(tokens, mpos):
                return out
            check = first
            if third is not None:
                check = third
            elif second is not None:
                check = second
            last = tokens[-1].token
            if _WHITESPACE_OR_QUOTE.fullmatch(last):
                last = tokens[-2].token
            prevent = False
            if last_para in (',', ';'):
                prevent = True
            if _CONTAINS_DIGIT.fullmatch(tokens[mpos].token):
                prevent = True
            if not _SENTENCE_END1.fullmatch(last_para) and last not in ('.', '?', '!', '…'):
                prevent = True
            if java_trim(sentence.text.replace(' ', ' ')):
                last_para = last
            if mpos + 1 < len(tokens) and _NUMERALS_EN_UC.fullmatch(tokens[mpos].token) and \
                    tokens[mpos + 1].token in ('.', ')'):
                prevent = True
            if prev_numbered or is_url(check) or is_email(check) or first_obj.immunized or \
                    tokens[mpos].has_pos_tag('_IS_URL'):
                prevent = True
            if check:
                fc = check[0]
                cap = uppercase_first_char(check)
                if cap != check and not prevent and is_lower_case(fc) and not _ONLY_LOWERCASE_START.fullmatch(check) \
                        and check not in _UC_EXCEPTIONS and not is_camel_case(check):
                    rm = RuleMatch(self, sentence, pos + tokens[mpos].start_pos, pos + tokens[mpos].end_pos,
                                   self.messages['incorrect_case'])
                    rm.set_suggested_replacement(cap)
                    rm.short_message = self.messages['category_case']
                    out.append(rm)
            pos += sentence.get_corrected_text_length()
            prev_numbered = bool(_DIGIT_DOT.fullmatch(sentence.text) or _LINEBREAK_DIGIT_DOT.fullmatch(sentence.text))
        return out

    @staticmethod
    def _is_quote_start(w, lang_code):
        base = ('"', "'", '„', '»', '«', '“', '‘', '¡', '¿')
        if lang_code == 'pt':
            return w in base or w in ('-', '–', '—')
        return w in base


def _is_first_white(t):
    tok = t.token
    return (t.is_whitespace or is_non_breaking_whitespace(tok)) and not t.is_linebreak and \
        '​' not in tok and '﻿' not in tok and '⁠' not in tok


def _is_removable_white(t):
    tok = t.token
    return (t.is_whitespace or is_non_breaking_whitespace(tok)) and not t.is_linebreak and tok != '\t' and \
        '​' not in tok and '﻿' not in tok and '⁠' not in tok


class MultipleWhitespaceRule(CoreTextLevelRule):
    rule_id = 'WHITESPACE_RULE'
    category_id = 'TYPOGRAPHY'
    issue_type = 'Whitespace'
    description_key = 'desc_whitespacerepetition'

    def match(self, sentences, annotated_text=None):
        out = []
        pos = 0
        for sentence in sentences:
            tokens = sentence.tokens
            n = len(tokens)
            i = 1
            while i < n:
                if _is_first_white(tokens[i]):
                    first = i
                    i += 1
                    while i < n and _is_removable_white(tokens[i]):
                        i += 1
                    i -= 1
                    if i > first:
                        rm = RuleMatch(self, sentence, pos + tokens[first].start_pos, pos + tokens[i].end_pos,
                                       self.messages['whitespace_repetition'])
                        rm.set_suggested_replacement(tokens[first].token)
                        out.append(rm)
                elif tokens[i].is_linebreak:
                    i += 1
                    while i < n and _is_removable_white(tokens[i]):
                        i += 1
                    # the Java for loop increments again after this inner loop
                i += 1
            pos += sentence.get_corrected_text_length()
        return out


def _is_only_spaces(s):
    return all(c == ' ' for c in s)


def _is_line_break_token(t):
    return t.is_linebreak or contains_line_break(t.token)


class SentenceWhitespaceRule(CoreTextLevelRule):
    rule_id = 'SENTENCE_WHITESPACE'
    category_id = 'TYPOGRAPHY'
    issue_type = 'Whitespace'
    description_key = 'missing_space_between_sentences'

    def __init__(self, messages, language=None, max_spaces_between_sentences=1):
        super().__init__(messages, language)
        self.max_spaces = max_spaces_between_sentences

    def get_message(self, prev_ends_with_number):
        return self.messages['addSpaceBetweenSentences']

    def match(self, sentences, annotated_text=None):
        first = True
        prev_ending_ws = ''
        prev_ends_lb = False
        prev_ends_number = False
        out = []
        pos = 0
        for sentence in sentences:
            tokens = sentence.tokens
            self._add_repeated_ws(sentence, tokens, pos, out)
            if first:
                first = False
            elif not prev_ends_lb and not (len(tokens) > 1 and _is_line_break_token(tokens[1])):
                lead = 0
                k = 1
                while k < len(tokens) and _is_only_spaces(tokens[k].token):
                    lead += len(tokens[k].token)
                    k += 1
                if _is_only_spaces(prev_ending_ws) and len(prev_ending_ws) + lead > self.max_spaces and \
                        (prev_ending_ws or lead > 0) and self._has_text_after(tokens, lead):
                    rm = RuleMatch(self, sentence, pos - len(prev_ending_ws), pos + lead,
                                   self.messages['whitespace_repetition'])
                    rm.set_suggested_replacement(' ')
                    out.append(rm)
                elif not prev_ending_ws and len(tokens) > 1:
                    ft = tokens[1].token
                    rm = RuleMatch(self, sentence, pos, pos + len(ft), self.get_message(prev_ends_number))
                    rm.set_suggested_replacement(' ' + ft)
                    out.append(rm)
            if tokens:
                last = tokens[-1]
                prev_ending_ws = last.token if not java_trim(last.token.replace(' ', ' ')) else ''
                prev_ends_lb = _is_line_break_token(last)
            if len(tokens) > 1:
                prev_ends_number = is_numeric(tokens[-2].token)
            pos += sentence.get_corrected_text_length()
        return out

    def _add_repeated_ws(self, sentence, tokens, pos, out):
        n = len(tokens)
        i = 1
        while i < n:
            if _is_only_spaces(tokens[i].token) and self._follows_sentence_end(tokens, i):
                fw = lw = i
                i += 1
                while i < n and _is_only_spaces(tokens[i].token):
                    lw = i
                    i += 1
                i -= 1
                length = sum(len(tokens[k].token) for k in range(fw, lw + 1))
                if length > self.max_spaces and lw + 1 < n and not tokens[lw + 1].is_whitespace and \
                        not _is_line_break_token(tokens[lw + 1]):
                    rm = RuleMatch(self, sentence, pos + tokens[fw].start_pos, pos + tokens[lw].end_pos,
                                   self.messages['whitespace_repetition'])
                    rm.set_suggested_replacement(' ')
                    out.append(rm)
            i += 1

    @staticmethod
    def _follows_sentence_end(tokens, wp):
        for i in range(wp - 1, 0, -1):
            if not tokens[i].is_whitespace:
                return tokens[i].token in ('.', '!', '?')
        return False

    @staticmethod
    def _has_text_after(tokens, lead):
        p = 1
        sl = 0
        while p < len(tokens) and sl < lead:
            sl += len(tokens[p].token)
            p += 1
        return p < len(tokens) and not tokens[p].is_whitespace and not _is_line_break_token(tokens[p])


class WhiteSpaceBeforeParagraphEnd(CoreTextLevelRule):
    rule_id = 'WHITESPACE_PARAGRAPH'
    category_id = 'STYLE'
    issue_type = 'Style'
    description_key = 'whitespace_before_parapgraph_end_desc'

    def __init__(self, messages, language=None, default_active=False):
        super().__init__(messages, language)
        if not default_active:
            self.set_default_off()

    def match(self, sentences, annotated_text=None):
        out = []
        pos = 0
        slb = self.language.single_line_breaks_marks_para if self.language else False
        for n, sentence in enumerate(sentences):
            if is_paragraph_end(sentences, n, slb):
                tokens = sentence.tokens
                lb = len(tokens) - 1
                while lb > 0 and tokens[lb].is_linebreak:
                    lb -= 1
                lw = lb
                while lw > 0 and tokens[lw].is_whitespace and tokens[lw].token != '​':
                    lw -= 1
                if lw < lb:
                    from_pos = pos + (tokens[lw + 1].start_pos if tokens[lw].is_whitespace else tokens[lw].start_pos)
                    to_pos = pos + tokens[lb].end_pos
                    rm = RuleMatch(self, sentence, from_pos, to_pos,
                                   self.messages['whitespace_before_parapgraph_end_msg'])
                    if lw > 0 and not tokens[lw].is_whitespace:
                        rm.set_suggested_replacement(tokens[lw].token)
                    else:
                        rm.set_suggested_replacement('')
                    out.append(rm)
            pos += sentence.get_corrected_text_length()
        return out


class WhiteSpaceAtBeginOfParagraph(CoreRule):
    rule_id = 'WHITESPACE_PARAGRAPH_BEGIN'
    category_id = 'STYLE'
    issue_type = 'Style'
    description_key = 'whitespace_at_begin_parapgraph_desc'

    def __init__(self, messages, language=None, default_active=False):
        super().__init__(messages, language)
        if not default_active:
            self.set_default_off()

    def match(self, sentence):
        tokens = sentence.tokens
        i = 1
        while i < len(tokens) and tokens[i].is_whitespace and tokens[i].token != '​' and \
                not tokens[i].is_linebreak:
            i += 1
        if i > 1 and i < len(tokens) and not tokens[i].is_linebreak:
            rm = RuleMatch(self, sentence, tokens[1].start_pos, tokens[i].end_pos,
                           self.messages['whitespace_at_begin_parapgraph_msg'])
            rm.set_suggested_replacement(tokens[i].token)
            return [rm]
        return []


class EmptyLineRule(CoreTextLevelRule):
    rule_id = 'EMPTY_LINE'
    category_id = 'STYLE'
    issue_type = 'Style'
    description_key = 'empty_line_rule_desc'

    def __init__(self, messages, language=None, default_active=False):
        super().__init__(messages, language)
        if not default_active:
            self.set_default_off()

    def match(self, sentences, annotated_text=None):
        out = []
        pos = 0
        slb = self.language.single_line_breaks_marks_para if self.language else False
        for n in range(len(sentences) - 1):
            sentence = sentences[n]
            if is_paragraph_end(sentences, n, slb):
                t = sentence.text
                if slb:
                    second = t.endswith('\n\n') or t.endswith('\n\r\n\r')
                else:
                    second = t.endswith('\n\n\n\n') or t.endswith('\n\r\n\r\n\r\n\r') or t.endswith('\r\n\r\n\r\n\r\n')
                if second:
                    tokens = sentence.non_blank_tokens
                    if len(tokens) > 1:
                        out.append(RuleMatch(self, sentence, pos + tokens[-1].start_pos, pos + tokens[-1].end_pos,
                                             self.messages['empty_line_rule_msg']))
            pos += sentence.get_corrected_text_length()
        return out


_QUOTED_SENT_END = regex.compile('[?!.]["“”„»«]', regex.DOTALL)
_SENT_END = regex.compile('[?!.]')
_OPENING_QUOTES = ('"', '“', '„', '«', '(', '[', '{', '—')
_CLOSING_QUOTES = ('"', '”', '“', '»', ')', ']', '}', '—')


class LongSentenceRule(CoreTextLevelRule):
    rule_id = 'TOO_LONG_SENTENCE'
    category_id = 'STYLE'
    issue_type = 'Style'

    def __init__(self, messages, language=None, max_words=50):
        super().__init__(messages, language)
        self.tags = ['picky']
        self.max_words = max_words

    def get_description(self):
        return self.messages.format('long_sentence_rule_desc', self.max_words)

    def get_message(self):
        return self.messages.format('long_sentence_rule_msg2', self.max_words)

    @staticmethod
    def _is_word_count(t):
        return bool(t) and not is_not_word_character(t[0])

    def match(self, sentences, annotated_text=None):
        out = []
        pos = 0
        mw = self.max_words
        for sentence in sentences:
            tokens = sentence.tokens
            if len(tokens) < mw or _QUOTED_SENT_END.search(sentence.text):
                pos += sentence.get_corrected_text_length()
                continue
            msg = self.get_message()
            i = 0
            from_pos, to_pos = [], []
            from_tok = to_tok = None
            idx_quote = -1
            n = len(tokens)
            while i < n:
                num_words = 0
                while i < n and tokens[i].token not in (':', ';', '\n', '\r\n', '\n\r'):
                    token = tokens[i].token
                    if idx_quote == -1 and token in _OPENING_QUOTES:
                        idx_quote = _OPENING_QUOTES.index(token)
                    elif idx_quote > -1 and token in _CLOSING_QUOTES and _CLOSING_QUOTES.index(token) == idx_quote:
                        idx_quote = -1
                    if self._is_word_count(token) and idx_quote == -1:
                        if from_tok is None:
                            from_tok = tokens[i]
                        if num_words == mw:
                            if to_tok is None:
                                for j in range(n - 1, -1, -1):
                                    if self._is_word_count(tokens[j].token):
                                        if n > j + 1 and _SENT_END.fullmatch(tokens[j + 1].token):
                                            to_tok = tokens[j + 1]
                                        else:
                                            to_tok = tokens[j]
                                        break
                            if from_tok is not None and to_tok is not None:
                                from_pos.append(from_tok.start_pos)
                                to_pos.append(to_tok.end_pos)
                            else:
                                from_pos.append(tokens[0].start_pos)
                                to_pos.append(tokens[-1].end_pos)
                            break
                        num_words += 1
                    i += 1
                i += 1
            for f, t in zip(from_pos, to_pos):
                out.append(RuleMatch(self, sentence, pos + f, pos + t, msg))
            pos += sentence.get_corrected_text_length()
        return out


class LongParagraphRule(CoreTextLevelRule):
    rule_id = 'TOO_LONG_PARAGRAPH'
    category_id = 'STYLE'
    issue_type = 'Style'

    def __init__(self, messages, language=None, default_words=-1, default_active=False):
        super().__init__(messages, language)
        self.set_default_off()
        self.max_words = default_words if default_words > 0 else 220
        self.tags = ['picky']

    def get_description(self):
        return self.messages.format('long_paragraph_rule_desc', self.max_words)

    def get_message(self):
        return self.messages.format('long_paragraph_rule_msg', self.max_words)

    def match(self, sentences, annotated_text=None):
        out = []
        pos = start_pos = end_pos = word_count = 0
        has_lb = False
        slb = self.language.single_line_breaks_marks_para if self.language else False
        mw = self.max_words
        for n, sentence in enumerate(sentences):
            pe = is_paragraph_end(sentences, n, slb)
            if not pe and '\n' in _LEADING_NL.sub('', sentence.text, count=1):
                has_lb = True
            for t in sentence.non_blank_tokens:
                if not t.is_whitespace and not t.is_sentence_start and not t.is_non_word():
                    word_count += 1
                    if word_count == mw:
                        end_pos = t.end_pos + pos
                    elif word_count == mw - 1:
                        start_pos = t.start_pos + pos
            if pe:
                if word_count > mw + 5 and not has_lb:
                    out.append(RuleMatch(self, sentence, start_pos, end_pos, self.get_message()))
                word_count = 0
                has_lb = False
            pos += sentence.get_corrected_text_length()
        if word_count > mw:
            out.append(RuleMatch(self, None, start_pos, end_pos, self.get_message()))
        return out


_LEADING_NL = regex.compile(r'^\n+')
_END_PUNCT = regex.compile(r'[:.?!…]')
_QUOTES_REGEX = regex.compile('[’\'"„“”»«‚‘›‹()\\[\\]]')


class ParagraphRepeatBeginningRule(CoreTextLevelRule):
    rule_id = 'PARAGRAPH_REPEAT_BEGINNING_RULE'
    category_id = 'STYLE'
    issue_type = 'Style'
    description_key = 'repetition_paragraph_beginning_desc'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def is_article(self, token):
        return token.has_pos_tag_starting_with('DT')

    def _num_char_equal_beginning(self, last, nxt):
        if len(last) < 2 or len(nxt) < 2 or last[1].is_whitespace or nxt[1].is_whitespace:
            return 0
        k = 1
        lt = last[k].token
        nt = nxt[k].token
        if _QUOTES_REGEX.fullmatch(lt) and lt == nt:
            if len(last) <= k + 1 or len(nxt) <= k + 1:
                return 0
            k += 1
            lt = last[k].token
            nt = nxt[k].token
        if not is_letter(lt[0]):
            return 0
        if len(last) > k + 1 and self.is_article(last[k]) and lt == nt:
            if len(nxt) <= k + 1:
                return 0
            k += 1
            lt = last[k].token
            nt = nxt[k].token
        if not is_letter(lt[0]):
            return 0
        if lt == nt:
            return last[k].end_pos
        return 0

    def match(self, sentences, annotated_text=None):
        out = []
        if not sentences:
            return out
        next_pos = last_pos = 0
        slb = self.language.single_line_breaks_marks_para if self.language else False
        last_sentence = sentences[0]
        last_tokens = last_sentence.non_blank_tokens
        for n in range(len(sentences) - 1):
            next_pos += len(sentences[n].text)
            if is_paragraph_end(sentences, n, slb):
                next_sentence = sentences[n + 1]
                next_tokens = next_sentence.non_blank_tokens
                end_pos = self._num_char_equal_beginning(last_tokens, next_tokens)
                if end_pos > 0:
                    sp = last_pos + last_tokens[1].start_pos
                    if sp < last_pos + end_pos:
                        msg = self.messages['repetition_paragraph_beginning_last_msg']
                        out.append(RuleMatch(self, last_sentence, sp, last_pos + end_pos, msg))
                        sp = next_pos + next_tokens[1].start_pos
                        out.append(RuleMatch(self, next_sentence, sp, next_pos + end_pos, msg))
                last_sentence = next_sentence
                last_tokens = next_tokens
                last_pos = next_pos
        return out


_PUNCTUATION_MARKS = ('.', '!', '?', ':', ',', ';')
_QUOTATION_MARKS = ('„', '»', '«', '"', '”', '″', '’', '‚', '‘', '›', '‹', '′', "'")
_P_NUMERIC = regex.compile('[0-9.]+')


class PunctuationMarkAtParagraphEnd(CoreTextLevelRule):
    rule_id = 'PUNCTUATION_PARAGRAPH_END'
    category_id = 'PUNCTUATION'
    issue_type = 'Grammar'
    description_key = 'punctuation_mark_paragraph_end_desc'

    def __init__(self, messages, language=None, default_active=True):
        super().__init__(messages, language)
        self.tags = ['picky']
        if not default_active:
            self.set_default_off()

    def is_ignored_paragraph(self, first_sentence):
        return False

    def match(self, sentences, annotated_text=None):
        out = []
        last_para = -1
        pos = 0
        slb = self.language.single_line_breaks_marks_para if self.language else False

        def is_word(t):
            return is_letter(t.token[0])

        for n, sentence in enumerate(sentences):
            if is_paragraph_end(sentences, n, slb):
                tokens = sentence.non_blank_tokens
                if len(tokens) > 2:
                    first_word = (is_word(tokens[1]) and tokens[2].token not in _PUNCTUATION_MARKS) or \
                        (len(tokens) > 3 and tokens[1].token in _QUOTATION_MARKS and is_word(tokens[2]) and
                         tokens[3].token not in _PUNCTUATION_MARKS)
                    ignore = False
                    if n == 1 and _P_NUMERIC.fullmatch(java_trim(sentences[0].text)):
                        ignore = True
                    if n > 0 and _P_NUMERIC.fullmatch(java_trim(sentences[n - 1].text)):
                        ignore = True
                    if n - last_para > 1 and first_word and not ignore and \
                            not self.is_ignored_paragraph(sentences[last_para + 1]):
                        lnw = len(tokens) - 1
                        while tokens[lnw].is_linebreak:
                            lnw -= 1
                        if tokens[-2].token == ':' and is_url(tokens[-1].token):
                            last_para = n
                            pos += len(sentence.text)
                            continue
                        last = tokens[lnw].token
                        if (len(last) > 30 and last.lower().startswith('http')) or last.lower().startswith('ftp'):
                            continue
                        if is_word(tokens[lnw]) or (tokens[lnw].token in _QUOTATION_MARKS and is_word(tokens[lnw - 1])):
                            rm = RuleMatch(self, sentence, pos + tokens[lnw].start_pos, pos + tokens[lnw].end_pos,
                                           self.messages['punctuation_mark_paragraph_end_msg'])
                            rm.set_suggested_replacements([tokens[lnw].token + m for m in _PUNCTUATION_MARKS])
                            out.append(rm)
                last_para = n
            pos += sentence.get_corrected_text_length()
        return out


class PunctuationMarkAtParagraphEnd2(CoreTextLevelRule):
    rule_id = 'PUNCTUATION_PARAGRAPH_END2'
    category_id = 'PUNCTUATION'
    issue_type = 'Grammar'
    description_key = 'punctuation_mark_paragraph_end_desc'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.set_default_off()

    def match(self, sentences, annotated_text=None):
        out = []
        pos = sent_pos = token_count = 0
        slb = self.language.single_line_breaks_marks_para if self.language else False
        for sentence in sentences:
            tokens = sentence.tokens
            for t in tokens:
                if not t.is_non_word() and not t.is_whitespace:
                    token_count += 1
            last = None
            for t in reversed(tokens):
                if not t.is_whitespace:
                    last = t
                    break
            pe = is_paragraph_end(sentences, sent_pos, slb)
            if pe and token_count > 10 and last is not None and not _END_PUNCT.fullmatch(last.token) and \
                    not last.is_non_word():
                rm = RuleMatch(self, sentence, pos + last.start_pos, pos + last.end_pos,
                               self.messages['punctuation_mark_paragraph_end_msg'])
                rm.set_suggested_replacement(last.token + '.')
                out.append(rm)
            if pe:
                token_count = 0
            sent_pos += 1
            pos += sentence.get_corrected_text_length()
        return out


_NUMERALS_BR = r"(?i)\d{1,2}?[a-z']*|M*(D?C{0,3}|C[DM])(L?X{0,3}|X[LC])(V?I{0,3}|I[VX])$"
_PUNCT_BR = regex.compile(r'[!-/:-@\[-`{-~…–—]')
_PUNCT_NO_DOT_BR = regex.compile(r"[ldmnstLDMNST]'|[[–—!-/:-@\[-`{-~]&&[^.]]", regex.V1)
_URL_PAREN = regex.compile(r'https?://[^\n\r\x85  ]+')
_ITEM_CTX1 = regex.compile(r'\n[a-zA-Z]\)')
_ITEM_CTX2 = regex.compile(r'[a-zA-Z]\)')


class _SymbolLocator:
    __slots__ = ('symbol', 'symbol_type', 'index', 'start_pos', 'sentence', 'sentence_index')

    def __init__(self, symbol, symbol_type, index, start_pos, sentence, sentence_index):
        self.symbol = symbol
        self.symbol_type = symbol_type
        self.index = index
        self.start_pos = start_pos
        self.sentence = sentence
        self.sentence_index = sentence_index


class GenericUnpairedBracketsRule(CoreTextLevelRule):
    category_id = 'PUNCTUATION'
    issue_type = 'Typographical'
    description_key = 'desc_unpaired_brackets'

    def __init__(self, messages, language=None, start_symbols=None, end_symbols=None, rule_id=None, numerals=None):
        super().__init__(messages, language)
        if start_symbols is None:
            start_symbols = ['[', '(', '{', '"', "'"]
            end_symbols = [']', ')', '}', '"', "'"]
        if len(start_symbols) != len(end_symbols):
            raise ValueError('Different number of start and end symbols')
        self.rule_id = rule_id or 'UNPAIRED_BRACKETS'
        self.start_symbols = list(start_symbols)
        self.end_symbols = list(end_symbols)
        from .. import jregex
        self.numerals = jregex.compile(numerals or _NUMERALS_BR)
        self.unique = {e: self.end_symbols.count(e) == 1 for e in self.end_symbols}

    def is_no_exception(self, token, tokens, i, j, prec_space, foll_space, stack):
        ts = tokens[i].token
        if i > 0 and _URL_PAREN.fullmatch(tokens[i - 1].token) and '(' in tokens[i - 1].token:
            return False
        if i >= 2:
            pp, p = tokens[i - 2].token, tokens[i - 1].token
            if pp in (':', ';') and p == '-' and ts in (')', '('):
                return False
        if i >= 1:
            p = tokens[i - 1].token
            if p in (':', ';') and not tokens[i].whitespace_before and ts in (')', '('):
                return False
        return True

    def match(self, sentences, annotated_text=None):
        stack = []
        rm_stack = []
        out = []
        base = 0
        for si, sentence in enumerate(sentences):
            tokens = sentence.non_blank_tokens
            for i in range(1, len(tokens)):
                for j in range(len(self.start_symbols)):
                    if self._fill(base, tokens, i, j, stack, sentence, si):
                        break
            base += sentence.get_corrected_text_length()
        symmetric = False
        ss = len(stack)
        if ss > 2 and ss % 2 == 1:
            symmetric = True
            for i in range(ss // 2):
                a = self.start_symbols.index(stack[i].symbol) if stack[i].symbol in self.start_symbols else -1
                b = self.end_symbols.index(stack[-1].symbol) if stack[-1].symbol in self.end_symbols else -1
                if a != b:
                    symmetric = False
                    break
        full = [None]

        def full_text():
            if full[0] is None:
                full[0] = ''.join(s.text for s in sentences)
            return full[0]

        if symmetric:
            loc = stack[ss // 2]
            m = self._create_match(out, rm_stack, loc.start_pos, loc.symbol, loc.symbol_type, loc.sentence,
                                   loc.sentence_index, full_text)
            if m is not None:
                out.append(m)
        else:
            for loc in stack:
                m = self._create_match(out, rm_stack, loc.start_pos, loc.symbol, loc.symbol_type, loc.sentence,
                                       loc.sentence_index, full_text)
                if m is not None and (loc.symbol_type == 'Closing' or _ends_like_real_sentence(loc.sentence.text)
                                      or len(sentences) - 1 > loc.sentence_index):
                    out.append(m)
        return out

    def _fill(self, base, tokens, i, j, stack, sentence, si):
        token = tokens[i].token
        start_pos = base + tokens[i].start_pos
        ss, es = self.start_symbols[j], self.end_symbols[j]
        if token == ss or token == es:
            preceded = True
            if ss == es:
                preceded = tokens[i - 1].is_sentence_start or tokens[i].whitespace_before or \
                    _PUNCT_NO_DOT_BR.fullmatch(tokens[i - 1].token) is not None or \
                    tokens[i - 1].token in self.start_symbols
            special = True
            if i < len(tokens) - 1 and ss == es:
                nt = tokens[i + 1].token
                special = tokens[i + 1].whitespace_before or _PUNCT_BR.fullmatch(nt) is not None or \
                    nt in self.end_symbols or (i >= 1 and tokens[i - 1].token.endswith('-')) or \
                    nt.startswith('-') or nt == 's'
            no_exc = self.is_no_exception(token, tokens, i, j, preceded, special, stack)
            if no_exc and preceded and token == ss:
                stack.append(_SymbolLocator(ss, 'Opening', i, start_pos, sentence, si))
                return True
            elif no_exc and (special or tokens[i].is_sentence_end) and token == es:
                peek_open = bool(stack) and stack[-1].symbol == '('
                if (i > 2 and es == ')' and (tokens[i - 3].has_pos_tag('SENT_START') or
                                             tokens[i - 2].whitespace_before) and
                        tokens[i - 1].token == '.' and
                        (self.numerals.fullmatch(tokens[i - 2].token) and not peek_open)) or \
                        (i > 1 and es == ')' and (self.numerals.fullmatch(tokens[i - 1].token) and not peek_open)):
                    pass
                else:
                    if not stack:
                        stack.append(_SymbolLocator(es, 'Closing', i, start_pos, sentence, si))
                        return True
                    if stack[-1].symbol == ss:
                        stack.pop()
                        return True
                    if self.unique[es]:
                        stack.append(_SymbolLocator(es, 'Closing', i, start_pos, sentence, si))
                        return True
                    if j == len(self.end_symbols) - 1:
                        stack.append(_SymbolLocator(es, 'Closing', i, start_pos, sentence, si))
                        return True
        return False

    def find_corresponding_symbol(self, symbol):
        if symbol in self.start_symbols:
            return self.end_symbols[self.start_symbols.index(symbol)]
        return self.start_symbols[self.end_symbols.index(symbol)]

    def get_message(self):
        return None

    def get_suggestions(self, full_text, start_pos, end_pos, symbol, other_symbol, symbol_type=None):
        """getSuggestions(text, startPos, endPos, Symbol, otherSymbol): the
        Java Symbol is given as the symbol string and its type ('Opening'
        or 'Closing')"""
        return None

    def prevent_match(self, sentence):
        return False

    def _create_match(self, out, rm_stack, start_pos, symbol, symbol_type, sentence, si, full_text):
        if rm_stack:
            if symbol in self.end_symbols:
                index = self.end_symbols.index(symbol)
                r = rm_stack[-1]
                if r.symbol == self.start_symbols[index]:
                    if len(out) > r.index:
                        del out[r.index]
                        rm_stack.pop()
                        return None
        rm_stack.append(_SymbolLocator(symbol, symbol_type, len(out), start_pos, sentence, si))
        other = self.find_corresponding_symbol(symbol)
        message = self.get_message()
        if message is None:
            from ..messages import message_format
            message = message_format(self.messages['unpaired_brackets'], other)
        ft = full_text()
        sl = len(symbol)
        if start_pos + sl < len(ft):
            if start_pos >= 2:
                ctx = ft[start_pos - 2:start_pos + sl]
                if _ITEM_CTX1.fullmatch(ctx):
                    return None
            elif start_pos >= 1:
                ctx = ft[start_pos - 1:start_pos + sl]
                if _ITEM_CTX2.fullmatch(ctx):
                    return None
        if self.prevent_match(sentence):
            return None
        m = RuleMatch(self, sentence, start_pos, start_pos + sl, message)
        repl = self.get_suggestions(full_text, start_pos, start_pos + sl, symbol, other, symbol_type)
        if repl is not None:
            m.set_suggested_replacements(repl)
        return m


def _ends_like_real_sentence(r):
    s = java_trim(r)
    return s.endswith('.') or s.endswith('?') or s.endswith('!')


class WordRepeatRule(CoreRule):
    rule_id = 'WORD_REPEAT_RULE'
    category_id = 'MISC'
    issue_type = 'Duplication'
    description_key = 'desc_repetition'
    _IGNORED = ('Phi', 'Li', 'Xiao', 'Duran', 'Wagga', 'Abdullah', 'Nwe', 'Pago', 'Cao')

    def ignore(self, tokens, position):
        for w in self._IGNORED:
            if self.word_repetition_of(w, tokens, position):
                return True
        return False

    def estimate_context_for_sure_match(self):
        return 1

    @staticmethod
    def word_repetition_of(word, tokens, position):
        return position > 0 and tokens[position - 1].token == word and tokens[position].token == word

    @staticmethod
    def is_word(token):
        if is_emoji(token):
            return False
        if is_numeric_space(token):
            return False
        if len(token) == 1 and not is_letter(token):
            return False
        return True

    def match(self, sentence):
        out = []
        tokens = self.get_sentence_with_immunization(sentence).non_blank_tokens
        prev = ''
        for i in range(1, len(tokens)):
            token = tokens[i].token
            if tokens[i].immunized:
                prev = ''
                continue
            if self.is_word(token) and java_equals_ignore_case(prev, token) and not self.ignore(tokens, i):
                out.append(self.create_rule_match(prev, token, tokens[i - 1].start_pos, tokens[i].start_pos,
                                                  self.messages['repetition'], sentence))
            prev = token
        return out

    def create_rule_match(self, prev, token, prev_pos, pos, msg, sentence):
        rm = RuleMatch(self, sentence, prev_pos, pos + len(prev), msg, self.messages['desc_repetition_short'])
        rm.set_suggested_replacement(prev)
        return rm


class WhitespaceBeforePunctuationRule(CoreRule):
    rule_id = 'WHITESPACE_PUNCTUATION'
    category_id = 'TYPOGRAPHY'
    issue_type = 'Whitespace'
    description_key = 'desc_whitespace_before_punctuation'

    def match(self, sentence):
        out = []
        tokens = sentence.tokens
        prev_white = False
        prev_len = 0
        for i in range(len(tokens)):
            t = tokens[i]
            token = t.token
            is_white = t.is_whitespace or is_non_breaking_whitespace(token) or t.is_field_code()
            msg = sugg = None
            if prev_white:
                if token == ':':
                    msg = self.messages['no_space_before_colon']
                    sugg = ':'
                    if i + 2 < len(tokens) and tokens[i + 1].is_whitespace and tokens[i + 2].token and \
                            is_digit(tokens[i + 2].token[0]):
                        msg = None
                elif token == ';':
                    msg = self.messages['no_space_before_semicolon']
                    sugg = ';'
                elif i > 1 and token == '%':
                    pp = tokens[i - 2].token
                    if pp and is_digit(pp[0]):
                        msg = self.messages['no_space_before_percentage']
                        sugg = '%'
            if msg is not None:
                fp = tokens[i - 1].start_pos
                rm = RuleMatch(self, sentence, fp, fp + 1 + prev_len, msg)
                rm.set_suggested_replacement(sugg)
                out.append(rm)
            prev_white = is_white and not t.is_field_code()
            prev_len = len(token)
        return out


CORE_RULES = {
    'CommaWhitespaceRule': CommaWhitespaceRule,
    'DoublePunctuationRule': DoublePunctuationRule,
    'UppercaseSentenceStartRule': UppercaseSentenceStartRule,
    'MultipleWhitespaceRule': MultipleWhitespaceRule,
    'SentenceWhitespaceRule': SentenceWhitespaceRule,
    'WhiteSpaceBeforeParagraphEnd': WhiteSpaceBeforeParagraphEnd,
    'WhiteSpaceAtBeginOfParagraph': WhiteSpaceAtBeginOfParagraph,
    'EmptyLineRule': EmptyLineRule,
    'LongSentenceRule': LongSentenceRule,
    'LongParagraphRule': LongParagraphRule,
    'ParagraphRepeatBeginningRule': ParagraphRepeatBeginningRule,
    'PunctuationMarkAtParagraphEnd': PunctuationMarkAtParagraphEnd,
    'PunctuationMarkAtParagraphEnd2': PunctuationMarkAtParagraphEnd2,
    'GenericUnpairedBracketsRule': GenericUnpairedBracketsRule,
    'WordRepeatRule': WordRepeatRule,
    'WhitespaceBeforePunctuationRule': WhitespaceBeforePunctuationRule,
}
