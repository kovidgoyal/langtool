"""Ports of org.languagetool.tagging.ar.ArabicTagManager and ArabicTagger."""

import re

from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...tagging import BaseTagger
from .tools import remove_tashkeel

# the positions of the flags in the POS tags (ArabicTagManager.loadHashmap)
_FLAG_POS = {
    'None': 0,
    'NOUN_TAG_LENGTH': 12,
    'NOUN_WORDTYPE': 0,
    'NOUN_CATEGORY': 1,
    'NOUN_GENDER': 4,
    'NOUN_NUMBER': 5,
    'NOUN_CASE': 6,
    'NOUN_INFLECT_MARK': 7,
    'NOUN_CONJ': 9,
    'NOUN_JAR': 10,
    'NOUN_PRONOUN': 11,
    # verb flags
    'VERB_TAG_LENGTH': 15,
    'VERB_WORDTYPE': 0,
    'VERB_CATEGORY': 1,
    'VERB_TRANS': 2,
    'VERB_GENDER': 4,
    'VERB_NUMBER': 5,
    'VERB_PERSON': 6,
    'VERB_INFLECT_MARK': 7,
    'VERB_TENSE': 8,
    'VERB_VOICE': 9,
    'VERB_CASE': 10,
    'VERB_CONJ': 12,
    'VERB_ISTIQBAL': 13,
    'VERB_PRONOUN': 14,
    # particle flags
    'PARTICLE_TAG_LENGTH': 11,
    'PARTICLE_WORDTYPE': 0,
    'PARTICLE_CATEGORY': 1,
    'PARTICLE_OPTION': 2,
    'PARTICLE_CONJ': 8,
    'PARTICLE_JAR': 9,
    'PARTICLE_PRONOUN': 10,
}

_PRONOUN_SUFFIXES = {'b': 'ني', 'c': 'نا', 'd': 'ك', 'e': 'كما', 'f': 'كم', 'g': 'كن', 'H': 'ه', 'i': 'ها',
                     'j': 'هما', 'k': 'هم', 'n': 'هن'}


def _remove_end(s, remove):
    """StringUtils.removeEnd"""
    if s and remove and s.endswith(remove):
        return s[:-len(remove)]
    return s


class ArabicTagManager:
    """Port of org.languagetool.tagging.ar.ArabicTagManager: reads and
    changes the flags of the Arabic POS tags. The tags have three parts
    separated by ';': word type and category, conjugation (gender, number,
    case, ...) and affixes (conjunction, jar/istiqbal, pronoun or definite
    article), e.g. "NJ-;F3--;W-L" or "V61;M1H-pa-;W-H". The position of a
    flag depends on the word type (noun, verb or particle/stop word)."""

    def modify_pos_tag(self, postag, tags):
        """Add the tags (like "CONJ;W"), None if one of them is
        incompatible"""
        for tg in tags:
            postag = self.add_tag(postag, tg)
            if postag is None:
                return None
        return postag

    def add_tag(self, postag, flag_string, flag=None):
        """addTag(postag, flagString) with a flag string "TYPE;F" or
        addTag(postag, flagType, flag)"""
        if flag is None:
            flag_tuple = flag_string.split(';')
            flag_type = ''
            flag = ''
            if len(flag_tuple) == 1:
                flag = flag_tuple[0]
            if len(flag_tuple) >= 2:
                flag_type = flag_tuple[0]
                flag = flag_tuple[1]
        else:
            flag_type = flag_string
        if flag == 'W':
            postag = self.set_flag(postag, 'CONJ', 'W')
        elif flag == 'K':
            if self.is_noun(postag) and self.is_majrour(postag):
                postag = self.set_flag(postag, 'JAR', 'K')
            else:  # a prefix K but non majrour
                return None
        elif flag == 'B':
            # the noun must be majrour
            if self.is_noun(postag) and self.is_majrour(postag):
                postag = self.set_flag(postag, 'JAR', 'B')
            else:
                return None
        elif flag == 'L':
            if self.is_noun(postag):
                # the noun must be majrour
                if self.is_majrour(postag):
                    postag = self.set_flag(postag, 'JAR', 'L')
                else:
                    return None
            else:  # verb case
                postag = self.set_flag(postag, 'ISTIQBAL', 'L')
        elif flag == 'D':
            # the noun must be not attached
            if self.is_un_attached_noun(postag):
                postag = self.set_flag(postag, 'PRONOUN', 'L')
            else:
                return None
        elif flag == 'S':
            # if postag contains a future tag
            if self.is_future_tense(postag):
                postag = self.set_flag(postag, 'ISTIQBAL', 'S')
            else:  # a prefix Seen but non verb or future
                return None
        # case of Pronoun
        if flag_type == 'PRONOUN' and flag and flag != 'D':
            postag = self.set_flag(postag, flag_type, flag[0])
        return postag

    def is_majrour(self, postag):
        """true if the case flag is majrour (or unset)"""
        flag = self.get_flag(postag, 'CASE')
        return flag in ('I', '-')

    def set_jar(self, postag, jar):
        """add a jar flag to a noun"""
        if self.is_majrour(postag):
            myflag = None
            if jar in ('ب', 'B'):
                myflag = 'B'
            elif jar in ('ل', 'L'):
                myflag = 'L'
            elif jar in ('ك', 'K'):
                myflag = 'K'
            elif jar in ('-', ''):
                myflag = '-'
            if myflag is not None:
                postag = self.set_flag(postag, 'JAR', myflag)
        return postag

    def set_definite(self, postag, flag):
        """add the definite flag to a noun"""
        if self.is_noun(postag) and self.is_un_attached_noun(postag):
            myflag = None
            if flag in ('ال', 'L', 'لل', 'D'):
                myflag = 'L'
            elif flag in ('-', ''):
                myflag = '-'
            if myflag is not None:
                postag = self.set_flag(postag, 'PRONOUN', myflag)
        return postag

    def unify_pronoun_tag(self, postag):
        if self.is_attached(postag):
            postag = self.set_flag(postag, 'PRONOUN', 'H')
        return postag

    def set_conjunction(self, postag, flag):
        """add the conjunction flag to a noun or verb"""
        myflag = None
        if flag in ('و', 'W', 'ف', 'F'):
            myflag = 'W'
        elif flag in ('-', ''):
            myflag = '-'
        if myflag is not None and (self.is_noun(postag) or self.is_verb(postag)):
            postag = self.set_flag(postag, 'CONJ', myflag)
        return postag

    def set_pronoun(self, postag, flag):
        """add the pronoun flag to a noun or verb"""
        if flag in ('ه', 'H') and (self.is_noun(postag) or self.is_verb(postag)):
            postag = self.set_flag(postag, 'PRONOUN', 'H')
        return postag

    def is_future_tense(self, postag):
        return self.is_verb(postag) and self.get_flag(postag, 'TENSE') == 'f'

    def is_un_attached_noun(self, postag):
        """a noun without attached pronoun"""
        return self.is_noun(postag) and self.get_flag(postag, 'PRONOUN') != 'H' and not postag.endswith('X')

    def is_attached(self, postag):
        """a noun or verb with attached pronoun"""
        return (self.is_noun(postag) or self.is_verb(postag)) and self.get_flag(postag, 'PRONOUN') == 'H'

    @staticmethod
    def is_stop_word(postag):
        return postag is not None and postag.startswith('P')

    @staticmethod
    def is_noun(postag):
        return postag is not None and postag.startswith('N')

    def is_dual(self, postag):
        return postag is not None and self.get_flag(postag, 'NUMBER') == '2'

    @staticmethod
    def is_verb(postag):
        return postag is not None and postag.startswith('V')

    @staticmethod
    def is_adj(postag):
        return postag is not None and postag.startswith('NA')

    @staticmethod
    def is_masdar(postag):
        return postag is not None and postag.startswith('NM')

    def is_definite(self, postag):
        return self.is_noun(postag) and self.get_flag(postag, 'PRONOUN') == 'L'

    def is_feminin(self, postag):
        return self.is_noun(postag) and self.get_flag(postag, 'GENDER') == 'F'

    def is_break(self, postag):
        """true if a word has no proclitics like conjunction and jar"""
        return ((self.is_stop_word(postag) and not self.has_conjunction(postag))  # a stopword without conjunction
                # a noun without conjunction and jar
                or (self.is_noun(postag) and not self.has_jar(postag) and not self.has_conjunction(postag))
                # a verb without conjunction and istiqbal
                or (self.is_verb(postag) and not self.has_conjunction(postag)))

    def has_jar(self, postag):
        return self.is_noun(postag) and self.get_flag(postag, 'JAR') != '-'

    def has_pronoun(self, postag):
        return self.get_flag(postag, 'PRONOUN') == 'H'

    def has_conjunction(self, postag):
        flag = self.get_flag(postag, 'CONJ')
        return ((self.is_noun(postag) and flag != '-') or (self.is_verb(postag) and flag != '-')
                or (self.is_stop_word(postag) and flag != 'W'))

    def get_definite_prefix(self, postag):
        """the prefix of a definite noun (ال, or ل after the jar ل)"""
        if not postag:
            return ''
        if self.is_noun(postag) and self.get_flag(postag, 'PRONOUN') == 'L':
            if self.has_jar(postag) and self.get_jar_prefix(postag) == 'ل':
                return 'ل'
            return 'ال'
        return ''

    def get_jar_prefix(self, postag):
        if not postag:
            return ''
        if self.is_noun(postag):
            flag = self.get_flag(postag, 'JAR')
            if flag == 'L':
                return 'ل'
            if flag == 'K':
                return 'ك'
            if flag == 'B':
                return 'ب'
        return ''

    def get_conjunction_prefix(self, postag):
        flag = self.get_flag(postag, 'CONJ')
        if flag == 'F':
            return 'ف'
        if flag == 'W':
            return 'و'
        return ''

    def get_pronoun_suffix(self, postag):
        if not postag:
            return ''
        return _PRONOUN_SUFFIXES.get(self.get_flag(postag, 'PRONOUN'), '')

    def _get_flag_pos(self, postag, flag_type):
        """getFlagPos2: the position of a flag according to the word type"""
        if self.is_noun(postag):
            key = 'NOUN_' + flag_type
        elif self.is_verb(postag):
            key = 'VERB_' + flag_type
        elif self.is_stop_word(postag):
            key = 'PARTICLE_' + flag_type
        else:
            key = ''
        return _FLAG_POS.get(key, 0)

    def get_flag(self, postag, flag_type):
        """the value of a flag of postag ('-' if the tag is too short)"""
        pos = self._get_flag_pos(postag, flag_type)
        if pos < len(postag):
            return postag[pos]
        return '-'

    def set_flag(self, postag, flag_type, flag):
        """set a flag of postag (unchanged if the tag is too short)"""
        pos = self._get_flag_pos(postag, flag_type)
        if pos >= len(postag):
            return postag
        return postag[:pos] + flag + postag[pos + 1:]

    def set_proclitic_flags(self, postag):
        """setProcleticFlags: remove the proclitic flags of a tag"""
        if not postag:
            return ''
        new_pos_tag = postag
        if self.is_verb(postag):
            new_pos_tag = self.set_flag(new_pos_tag, 'CONJ', '-')
            new_pos_tag = self.set_flag(new_pos_tag, 'ISTIQBAL', '-')
        elif self.is_noun(postag):
            new_pos_tag = self.set_flag(new_pos_tag, 'CONJ', '-')
            new_pos_tag = self.set_flag(new_pos_tag, 'JAR', '-')
            # if the word is a definite word, remove the definite flag
            if self.is_definite(postag):
                new_pos_tag = self.set_flag(new_pos_tag, 'PRONOUN', '-')
        elif self.is_stop_word(postag):
            new_pos_tag = self.set_flag(new_pos_tag, 'CONJ', '-')
            new_pos_tag = self.set_flag(new_pos_tag, 'JAR', '-')
        else:
            return postag
        return new_pos_tag

    def merge_pos_tag(self, source_pos_tag, target_pos_tag):
        """mergePosTag: inflect a target tag like a source tag, e.g. when a
        word is replaced by another word: merge("VW1;M3H-faU;WS-",
        "V31;--------;---") -> "V31;M3H-faU;WS-" (same word type: the
        conjugation and affixes of the source with the category of the
        target), merge("VW1;M1H-pa-;--H", "PRD;---;---") -> "PRD;---;--H"
        (different word types: the target with the compatible affixes of
        the source)"""
        tmp = source_pos_tag
        if not source_pos_tag:
            return target_pos_tag
        if not target_pos_tag:
            return source_pos_tag
        if self.is_noun(source_pos_tag) and self.is_noun(target_pos_tag):
            if len(source_pos_tag) != len(target_pos_tag):
                return source_pos_tag
            # copy target category into source
            return self.set_flag(source_pos_tag, 'CATEGORY', self.get_flag(target_pos_tag, 'CATEGORY'))
        if self.is_verb(source_pos_tag) and self.is_verb(target_pos_tag):
            if len(source_pos_tag) != len(target_pos_tag):
                return source_pos_tag
            tmp = self.set_flag(tmp, 'CATEGORY', self.get_flag(target_pos_tag, 'CATEGORY'))
            return self.set_flag(tmp, 'TRANS', self.get_flag(target_pos_tag, 'TRANS'))
        if self.is_stop_word(source_pos_tag) and self.is_stop_word(target_pos_tag):
            if len(source_pos_tag) != len(target_pos_tag):
                return source_pos_tag
            tmp = self.set_flag(tmp, 'CATEGORY', self.get_flag(target_pos_tag, 'CATEGORY'))
            return self.set_flag(tmp, 'OPTION', self.get_flag(target_pos_tag, 'OPTION'))
        # different word types
        tmp = target_pos_tag
        if (self.is_stop_word(source_pos_tag) and (self.is_verb(target_pos_tag) or self.is_noun(target_pos_tag))
                or (self.is_verb(source_pos_tag) or self.is_noun(source_pos_tag))
                and self.is_stop_word(target_pos_tag)):
            # use the compatible affixes parts (pronoun only, not the definite article)
            if self.has_pronoun(source_pos_tag):
                tmp = self.set_flag(tmp, 'PRONOUN', self.get_flag(source_pos_tag, 'PRONOUN'))
            return tmp
        if (self.is_verb(source_pos_tag) and self.is_noun(target_pos_tag)
                or self.is_noun(source_pos_tag) and self.is_verb(target_pos_tag)):
            # use the compatible affixes parts (pronoun and conjunction)
            if self.has_pronoun(source_pos_tag):
                tmp = self.set_flag(tmp, 'PRONOUN', self.get_flag(source_pos_tag, 'PRONOUN'))
            return self.set_flag(tmp, 'CONJ', self.get_flag(source_pos_tag, 'CONJ'))
        return target_pos_tag

    def set_single(self, postag):
        return self.set_flag(postag, 'NUMBER', '1')

    def set_dual(self, postag):
        return self.set_flag(postag, 'NUMBER', '2')

    def set_plural(self, postag):
        return self.set_flag(postag, 'NUMBER', '3')

    def set_majrour(self, postag):
        if self.is_noun(postag):
            if self.is_dual(postag):
                return self.set_flag(postag, 'CASE', 'A')
            return self.set_flag(postag, 'CASE', 'I')
        return postag

    def set_marfou3(self, postag):
        return self.set_flag(postag, 'CASE', 'U')

    def set_mansoub(self, postag):
        return self.set_flag(postag, 'CASE', 'A')

    def set_tanwin(self, postag):
        return self.set_flag(postag, 'PRONOUN', 'n')


TAG_MANAGER = ArabicTagManager()

# the attached pronouns are converted to one model form in the stems
_ATTACHED_PRONOUN = re.compile('(ك|ها|هما|هم|هن|كما|كم|كن|نا|ي)$')
_SUFFIXES = ('ك', 'ها', 'هما', 'كما', 'هم', 'هن', 'كم', 'كن', 'نا')
_OLD_STYLE_PRONOUNS = frozenset(('ني', 'نا', 'ك', 'كما', 'كم', 'كن', 'ه', 'ها', 'هما', 'هم', 'هن'))
_NEW_STYLE_PRONOUNS = {'ني': 'PRONOUN;b', 'نا': 'PRONOUN;c', 'ك': 'PRONOUN;d', 'كما': 'PRONOUN;e',
                       'كم': 'PRONOUN;f', 'كن': 'PRONOUN;g', 'ه': 'PRONOUN;H', 'ها': 'PRONOUN;i',
                       'هما': 'PRONOUN;j', 'هم': 'PRONOUN;k', 'هن': 'PRONOUN;n'}
_CACHE_SIZE = 100000


def _get_suffix_index_list(word):
    suffix_indexes = [len(word)]
    if word.endswith(_SUFFIXES):
        if word.endswith('ك'):
            suffix_pos = len(word) - 1
        elif word.endswith('هما') or word.endswith('كما'):
            suffix_pos = len(word) - 3
        else:
            suffix_pos = len(word) - 2
        suffix_indexes.append(suffix_pos)
    return suffix_indexes


def _get_prefix_index_list(word):
    prefix_indexes = [0]
    # four letters
    if word.startswith(('وكال', 'وبال', 'فكال', 'فبال')):
        prefix_indexes.append(4)
    # three letters
    if word.startswith(('ولل', 'فلل', 'فال', 'وال', 'بال', 'كال')):  # ولل: و+ل+ال
        prefix_indexes.append(3)
    # two letters
    if word.startswith(('لل', 'وك', 'ول', 'وب', 'فك', 'فل', 'فب', 'ال',  # لل: ل+ال
                        # the present tense of verbs, only the seen is taken
                        'فسأ', 'فسن', 'فسي', 'فست', 'وسأ', 'وسن', 'وسي', 'وست')):
        prefix_indexes.append(2)
    # one letter
    if word.startswith(('ك', 'ل', 'ب', 'و', 'ف',
                        'سأ', 'سن', 'سي', 'ست')):  # the present tense of verbs, only the seen is taken
        prefix_indexes.append(1)
    return prefix_indexes


class ArabicTagger(BaseTagger):
    """Port of org.languagetool.tagging.ar.ArabicTagger: the words are
    looked up without tashkeel in /ar/arabic.dict (with the manual
    additions and removals); words that are not stop words also get the
    readings of their stems without the proclitics (conjunction و/ف, jar
    ك/ل/ب, the istiqbal س, the article ال) and the attached pronouns, with the
    corresponding flags added to the POS tags (if they are compatible). No
    case conversions (Arabic has no letter case)."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'ar', resource_dir, tag_lowercase_with_uppercase=False)
        self.tag_manager = TAG_MANAGER
        self.new_style_pronoun_tag = False

    def enable_new_style_pronoun_tag(self):
        """a temporary attribute to be compatible with the existing pronoun
        tag style"""
        self.new_style_pronoun_tag = True
        self._cache = {}

    def tag(self, sentence_tokens):
        if isinstance(sentence_tokens, str):
            # tag(String word): tag a single word
            return self.tag([sentence_tokens])[0]
        token_readings = []
        pos = 0
        for word in sentence_tokens:
            token_readings.append(AnalyzedTokenReadings(self.get_analyzed_tokens(word), pos))
            pos += len(word)
        return token_readings

    def get_analyzed_tokens(self, word):
        cached = self._cache.get(word)
        if cached is None:
            cached = tuple(self._compute(word))
            if len(self._cache) > _CACHE_SIZE:
                self._cache.clear()
            self._cache[word] = cached
        return [AnalyzedToken(word, tag, lemma) for lemma, tag in cached]

    def _compute(self, word):
        striped = remove_tashkeel(word)
        tagger_tokens = self._tagged(striped)
        result = list(tagger_tokens)
        # additional tagging with prefixes, if not a stop word
        if not any(self.tag_manager.is_stop_word(tag) for lemma, tag in tagger_tokens):
            result.extend(self.additional_tags(word))
        if not result:
            result.append((None, None))
        return result

    def additional_tags(self, word):
        """the readings with proclitics and enclitics, a list of (lemma,
        tag); the stems are looked up in the dictionary only (Java: the
        IStemmer of the dictionary)"""
        striped = remove_tashkeel(word)
        out = []
        prefix_index_list = _get_prefix_index_list(striped)
        suffix_index_list = _get_suffix_index_list(striped)
        for i in prefix_index_list:
            for j in suffix_index_list:
                # avoid the default case of the word as it is
                if i == 0 and j == len(striped):
                    continue
                stems = self._get_stem(striped, i, j)
                tags = self._get_tags(striped, i, j)
                for stem in stems:
                    for lemma, pos_tag in self.dictionary.lookup(stem):
                        # modify the flags in the postag, None if not compatible
                        pos_tag = self.tag_manager.modify_pos_tag(pos_tag, tags)
                        if pos_tag is not None:
                            out.append((lemma, pos_tag))
        return out

    def _get_tags(self, word, pos_start, pos_end):
        tags = []
        prefix = word[:pos_start]
        suffix = word[pos_end:]
        # prefixes, first place
        if prefix.startswith('و') or prefix.startswith('ف'):
            tags.append('CONJ;W')
            prefix = prefix[1:]
        # second place
        if prefix.startswith('ك'):
            tags.append('JAR;K')
        elif prefix.startswith('ل'):
            tags.append('JAR;L')
        elif prefix.startswith('ب'):
            tags.append('JAR;B')
        elif prefix.startswith('س'):
            tags.append('ISTIQBAL;S')
        # last place
        if prefix.endswith('ال') or prefix.endswith('لل'):
            tags.append('PRONOUN;D')
        # suffixes
        if not self.new_style_pronoun_tag:
            if suffix in _OLD_STYLE_PRONOUNS:
                tags.append('PRONOUN;H')
        else:
            t = _NEW_STYLE_PRONOUNS.get(suffix)
            if t is not None:
                tags.append(t)
        return tags

    @staticmethod
    def _get_stem(word, pos_start, pos_end):
        # extract only stem+suffix, the suffix will be replaced by the pronoun model
        stem_list = []
        stem = word[pos_start:]
        if pos_end != len(word):  # convert attached pronouns to one model form
            stem = _ATTACHED_PRONOUN.sub('ه', stem, count=1)
        # correct the case of ل+ال: للاعب => لل- لاعب
        if word[:pos_start].endswith('لل'):
            stem_list.append('ل' + stem)
        stem_list.append(stem)  # لاسم أو ل+لاعب
        return stem_list

    def get_proclitic(self, token):
        """the proclitic letters of a token according to the flags of its
        POS tag"""
        postag = token.pos_tag
        word = token.token
        if not postag:
            return ''
        tm = self.tag_manager
        prefix = ''
        if tm.is_verb(postag):
            # extract conjunction and istiqbal proclitics
            prefix_length = 0
            if tm.get_flag(postag, 'CONJ') == 'W':
                prefix_length += 1
            if tm.get_flag(postag, 'ISTIQBAL') == 'S':
                prefix_length += 1
            prefix = word[:prefix_length]
        elif tm.is_noun(postag):
            jarflag = tm.get_flag(postag, 'JAR')
            prefix_length = 0
            if tm.get_flag(postag, 'CONJ') != '-':
                prefix_length += 1
            if jarflag != '-':
                prefix_length += 1
            if tm.is_definite(postag):
                if jarflag == 'L':
                    prefix_length += 1  # case of لل+بيت
                else:
                    prefix_length += 2  # case of ال+بيت
            prefix = word[:prefix_length]
        return prefix

    def get_enclitic(self, token):
        """the suffix letters of a token with a pronoun flag"""
        postag = token.pos_tag
        word = token.token
        if not postag:
            return ''
        flag = self.tag_manager.get_flag(postag, 'PRONOUN')
        if flag == '-':
            return self.tag_manager.get_pronoun_suffix(postag)
        for suffix in ('ه', 'ها', 'هما', 'هم', 'هن', 'ك', 'كما', 'كم', 'كن', 'ني', 'نا'):
            if word.endswith(suffix):
                return suffix
        # (Java also checks the prepositions عني, مني, عنا, منا, which end with
        # ني and نا and are handled above)
        return ''

    def get_jar_proclitic(self, token):
        """the jar proclitic letter of a noun"""
        postag = token.pos_tag
        word = token.token
        if not postag:
            return ''
        tm = self.tag_manager
        prefix = ''
        if tm.is_noun(postag):
            prefix_length = 0
            if tm.get_flag(postag, 'CONJ') != '-':
                prefix_length += 1
            if tm.get_flag(postag, 'JAR') != '-':
                prefix_length += 1
            if prefix_length > 0:
                prefix = word[prefix_length - 1:prefix_length]
        return prefix

    def get_lemmas(self, pattern_tokens, word_type):
        """the lemmas of the readings of a type ('verb', 'adj' or 'masdar'),
        without duplicates"""
        tm = self.tag_manager
        lemma_list = []
        for tok in pattern_tokens.readings:
            tag = tok.pos_tag
            if ((tm.is_verb(tag) and word_type == 'verb') or (tm.is_adj(tag) and word_type == 'adj')
                    or (tm.is_masdar(tag) and word_type == 'masdar')):
                if tok.lemma not in lemma_list:
                    lemma_list.append(tok.lemma)
        return lemma_list
