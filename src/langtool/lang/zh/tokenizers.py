"""Port of org.languagetool.tokenizers.zh.ChineseWordTokenizer and
org.languagetool.tokenizers.zh.ChineseSentenceTokenizer."""

from ...dictionaries import locate
from ...tools import java_is_whitespace
from . import hanlp


def _utf16_units(s):
    """A Python string as a string of UTF-16 code units (characters outside
    the BMP as surrogate pairs)"""
    if not s or max(s) <= '\uffff':
        return s
    return ''.join(c if c <= '\uffff' else chr(0xd800 + ((ord(c) - 0x10000) >> 10)) + chr(0xdc00 + (ord(c) & 0x3ff))
                   for c in s)


def _java_str(s):
    """A Python string from UTF-16 code units (pairs joined, unpaired
    surrogates kept)"""
    if any('\ud800' <= c <= '\udfff' for c in s):
        return s.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'surrogatepass')
    return s


class ChineseWordTokenizer:
    """Segments a text with HanLP's ViterbiSegment (HanLP.newSegment() with
    all named entity recognition and the custom dictionary disabled and part
    of speech tagging enabled, see langtool.lang.zh.hanlp). Each token is
    Term.toString(), "word/nature", which ChineseTagger splits again.

    HanLP works on UTF-16 code units: a character outside the BMP is two
    units in Java. The atoms of the segmenter keep a surrogate pair together
    (surrogates have the same character type) and the core dictionary has no
    surrogates, so a pair is never split in practice; should it be split, the
    two halves are joined into one token (with the nature of the first) so
    that token positions are character positions like everywhere in
    langtool."""

    def __init__(self, dictionary_path=None, download=True):
        self.data = hanlp.get_data(lambda name: locate('zh/' + name, dictionary_path, download))

    def tokenize(self, text):
        terms = hanlp.seg(self.data, _utf16_units(text))
        result = []
        pending = None  # a word ending with a high surrogate
        for word, nature in terms:
            if pending is not None and '\udc00' <= word[0] <= '\udfff':
                word = pending[0] + word
                nature = pending[1]
                result.pop()
            pending = (word, nature) if '\ud800' <= word[-1] <= '\udbff' else None
            result.append(_java_str(word) + '/' + nature)
        return result


class ChineseSentenceTokenizer:
    """Splits with HanLP's SentencesUtil.toSentenceList, which drops
    whitespace: runs of whitespace are added as separate sentences so that
    the positions are kept."""

    def tokenize(self, text):
        result = []
        whitespace = []
        non_whitespace = []
        for c in text:
            if java_is_whitespace(c):
                if non_whitespace:
                    result.extend(hanlp.to_sentence_list(''.join(non_whitespace)))
                    non_whitespace = []
                whitespace.append(c)  # keep collecting whitespaces
            else:
                if whitespace:
                    result.append(''.join(whitespace))
                    whitespace = []
                non_whitespace.append(c)
        if whitespace:
            result.append(''.join(whitespace))
        if non_whitespace:
            result.extend(hanlp.to_sentence_list(''.join(non_whitespace)))
        return result

    def set_single_line_breaks_marks_paragraph(self, line_break_paragraphs):
        """Note: does have no effect for Chinese"""

    def single_line_breaks_marks_para(self):
        """Note: will always return False"""
        return False
