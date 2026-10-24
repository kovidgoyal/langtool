"""Port of org.languagetool.tagging.ca.CatalanTagger and VerbClassifier."""

import os
import threading
import unicodedata

from ... import jregex
from ...analysis import AnalyzedToken, AnalyzedTokenReadings
from ...chunking import ChunkTag
from ...rules.abstract_rules import load_simple_replace_data
from ...tagging import BaseTagger, TaggedWord
from ...tools import is_all_uppercase, is_emoji, is_mixed_case, java_trim, uppercase_first_char

_ADJ_PART_FS = jregex.compile('VMP00SF.|A[QO].[FC]S.')
_VERB = jregex.compile('V.+')
_PREFIXES_FOR_VERBS = jregex.compile('(auto)(.*[aeiouàéèíòóïü].+[aeiouàéèíòóïü].*)', jregex.IGNORECASE)
_ADJECTIU_COMPOST = jregex.compile('(.*)o-(.*.*)', jregex.IGNORECASE)
_TRES_ADJECTIUS = jregex.compile('(.*)o-(.*)o-(.*.*)', jregex.IGNORECASE)
_ALTRES_PREFIXOS = ('greco', 'sino', 'italo', 'franco', 'gal·lo', 'luso', 'germano', 'hispano', 'anglo', 'àrabo',
                    'austro', 'belgo')
_NO_ALTRES_PREFIXOS = ('grego', 'xineso', 'italiano', 'franceso', 'portugueso', 'angleso', 'espanyolo', 'alemanyo',
                       'arabo', 'austríaco', 'bèlgico')
_ALLUPPERCASE_EXCEPTIONS = ('ARNAU', 'CRISTIAN', 'TOMÀS')
_MENT = jregex.compile('^(.+)ment$')
_ISTE = jregex.compile('^(.+)iste$')

_ENDINGS = ('a|ada|ades|am|ant|ar|ara|aran|arem|aren|ares|areu|aria|arien|aries|arà|aràs|aré|aríem|aríeu|assen|'
            'asses|assin|assis|at|ats|au|ava|aven|aves|e|ec|ega|eguda|egudes|eguem|eguen|eguera|egueren|egueres|'
            'egues|eguessen|eguesses|eguessin|eguessis|egueu|egui|eguin|eguis|egut|eguts|egué|eguérem|eguéreu|'
            'egués|eguéssem|eguésseu|eguéssim|eguéssiu|eguí|eix|eixem|eixen|eixent|eixeran|eixerem|eixeren|'
            'eixeres|eixereu|eixeria|eixerien|eixeries|eixerà|eixeràs|eixeré|eixeríem|eixeríeu|eixes|eixessen|'
            'eixesses|eixessin|eixessis|eixeu|eixi|eixia|eixien|eixies|eixin|eixis|eixo|eixé|eixérem|eixéreu|'
            'eixés|eixéssem|eixésseu|eixéssim|eixéssiu|eixí|eixíem|eixíeu|em|en|es|esc|esca|escuda|escudes|escut|'
            'escuts|esquem|esquen|esquera|esqueren|esqueres|esques|esquessen|esquesses|esquessin|esquessis|'
            'esqueu|esqui|esquin|esquis|esqué|esquérem|esquéreu|esqués|esquéssem|esquésseu|esquéssim|esquéssiu|'
            'esquí|essen|esses|essin|essis|eu|i|ia|ida|ides|ien|ies|iguem|igueu|im|in|int|ir|ira|iran|irem|iren|'
            'ires|ireu|iria|irien|iries|irà|iràs|iré|iríem|iríeu|is|isc|isca|isquen|isques|issen|isses|issin|'
            'issis|it|its|iu|ix|ixen|ixes|o|à|àrem|àreu|às|àssem|àsseu|àssim|àssiu|àvem|àveu|èixer|éixer|és|'
            'éssem|ésseu|éssim|éssiu|í|íem|íeu|írem|íreu|ís|íssem|ísseu|íssim|íssiu|ïs')
# (Java: Pattern.CASE_INSENSITIVE without UNICODE_CASE)
_DESINENCIES_1CONJ_0 = jregex.compile('(?i)(.+?)(' + _ENDINGS + ')')
_DESINENCIES_1CONJ_1 = jregex.compile('(?i)(.+)(' + _ENDINGS + ')')

_INCORRECT_VERB_CHUNK = ChunkTag('_incorrect_verb_')


def _nfc(s):
    return unicodedata.normalize('NFC', s)


def _adjust_lexeme_for_soft_vowel(lexeme):
    if lexeme.endswith('c'):
        return lexeme[:-1] + 'ç'
    if lexeme.endswith('qu'):
        return lexeme[:-2] + 'c'
    if lexeme.endswith('g'):
        return lexeme[:-1] + 'j'
    if lexeme.endswith('gü'):
        return lexeme[:-2] + 'gu'
    if lexeme.endswith('gu'):
        return lexeme[:-2] + 'g'
    return lexeme


class CatalanTagger(BaseTagger):
    """Catalan part-of-speech tagger: a BaseTagger for /ca/ca-ES.dict (with
    added.txt, added_custom.txt, removed.txt and removed_custom.txt, the
    manual additions don't overwrite the dictionary) with its own tag():
    typographic apostrophes of tokens longer than one character are
    replaced by typewriter apostrophes (the token text changes too and the
    readings are marked with the typographic apostrophe flag); the word is
    looked up in NFC; words that are not lowercase and not mixed case also
    get the readings of the lowercase word, unknown all uppercase words
    (and ARNAU, CRISTIAN, TOMÀS) those of the word with only the first
    character uppercase. Unknown words that are not mixed case are tagged
    as adverbs (-ment after a feminine singular adjective or participle),
    verbs with the prefix auto-, compound adjectives (folklòrico-popular,
    franco-americano-alemany), words with the deprecated characters of the
    "ela geminada" (U+013F, U+0140) and, in Valencian, as adjectives -iste;
    unknown emojis get the tag _emoji_. The tags starting with "0" are
    Valencian: without the "0" in the Valencian variant, removed in the
    other variants. Unknown words that are forms of the incorrect verbs of
    replace_verbs.txt get the verb tags (with the chunk tag
    _incorrect_verb_). Locale("ca") has no special case mapping."""

    def __init__(self, dictionary, resource_dir=None, rules_dir=None, is_valencian=False):
        super().__init__(dictionary, 'ca', resource_dir, tag_lowercase_with_uppercase=False)
        self.is_valencian = is_valencian
        path = os.path.join(rules_dir, 'replace_verbs.txt') if rules_dir else None
        self.wrong_verbs = load_simple_replace_data(path) if path and os.path.exists(path) else {}

    def tag(self, sentence_tokens):
        token_readings = []
        pos = 0
        for original_word in sentence_tokens:
            # This hack allows all rules and dictionary entries to work with
            # typewriter apostrophe
            contains_typographic_apostrophe = False
            if len(original_word) > 1 and '’' in original_word:
                contains_typographic_apostrophe = True
                original_word = original_word.replace('’', "'")
            tags, is_incorrect_verb = self._cached_tags(original_word)
            atr = AnalyzedTokenReadings([AnalyzedToken(original_word, tag, lemma) for lemma, tag in tags], pos)
            if contains_typographic_apostrophe:
                atr.typographic_apostrophe = True
            if is_incorrect_verb:
                atr.set_chunk_tags([_INCORRECT_VERB_CHUNK])
            token_readings.append(atr)
            pos += len(original_word)
        return token_readings

    def get_analyzed_tokens(self, word):
        return [AnalyzedToken(word, tag, lemma) for lemma, tag in self._cached_tags(word)[0]]

    def _cached_tags(self, word):
        cached = self._cache.get(word)
        if cached is None:
            cached = self._compute(word)
            if len(self._cache) > 100000:
                self._cache.clear()
            self._cache[word] = cached
        return cached

    def _compute(self, original_word):
        """Returns ((lemma, tag) pairs, is_incorrect_verb)"""
        normalized_word = _nfc(original_word)
        result = []
        lower_word = normalized_word.lower()
        is_lowercase = normalized_word == lower_word
        is_mixed = is_mixed_case(normalized_word)
        is_all_upper = is_all_uppercase(normalized_word)
        # normal case:
        result.extend(self._tagged(normalized_word))
        # tag non-lowercase (alluppercase or startuppercase), but not mixedcase
        # word with lowercase word tags:
        if not is_lowercase and not is_mixed:
            result.extend(self._tagged(lower_word))
        # tag all-uppercase proper nouns (ex. FRANÇA)
        if (not result or normalized_word in _ALLUPPERCASE_EXCEPTIONS) and is_all_upper:
            result.extend(self._tagged(uppercase_first_char(lower_word)))
        # additional tagging with prefixes
        if not result and not is_mixed:
            add = self.additional_tags(original_word)
            if add:
                result.extend(add)
        # emoji
        if not result and is_emoji(original_word):
            result.append(('_emoji_', '_emoji_'))
        # filter for Valencian POS tags
        result = self._filter_valencian_tags(result)
        # incorrect verbs
        is_incorrect_verb = False
        if not result:
            tags_for_incorrect_verbs = self._additional_tags_for_incorrect_verbs(lower_word)
            if tags_for_incorrect_verbs:
                result.extend(tags_for_incorrect_verbs)
                is_incorrect_verb = True
        # if empty, add an analyzed token with no lemma and no postag
        if not result:
            result.append((None, None))
        return tuple(result), is_incorrect_verb

    def _filter_valencian_tags(self, tags):
        """filterAnalyzedTokensInPlace: in Valencian the "0" at the
        beginning of the tags is removed, in the other variants the tags
        starting with "0" are ignored"""
        if self.is_valencian:
            return [(lemma, tag[1:] if tag and tag[0] == '0' else tag) for lemma, tag in tags]
        return [(lemma, tag) for lemma, tag in tags if not (tag and tag[0] == '0')]

    def additional_tags(self, word):
        """Returns a list of (lemma, tag), or None (CatalanTagger.additionalTags)."""
        additional = []
        # Any well-formed adverb with suffix -ment is tagged as an adverb (RG)
        # Adjectiu femení singular o participi femení singular + -ment
        lower_word = _nfc(word.lower())
        if lower_word.endswith('ment'):
            possible_adj = jregex.java_replace(_MENT, '$1', lower_word)
            for _lemma, pos_tag in self._tagged(possible_adj):
                if pos_tag is not None and _ADJ_PART_FS.fullmatch(pos_tag):
                    additional.append((lower_word, 'RG'))
                    return additional
        # Any well-formed verb with prefixes is tagged as a verb copying the original tags
        m = _PREFIXES_FOR_VERBS.fullmatch(word)
        if m:
            possible_verb = _nfc(m.group(2).lower())
            for lemma, pos_tag in self._tagged(possible_verb):
                if lemma != 'nòmer' and pos_tag is not None and _VERB.fullmatch(pos_tag):
                    additional.append((m.group(1).lower() + lemma, pos_tag))
            return additional
        # folklòrico-popular
        m = _ADJECTIU_COMPOST.fullmatch(word)
        if m:
            adj1 = m.group(1).lower()
            if self._is_valid_adjective_form(adj1):
                adj2 = m.group(2).lower()
                for lemma, pos_tag in self._tagged(adj2):
                    if pos_tag is not None and pos_tag.startswith('A'):
                        additional.append((adj1 + 'o-' + lemma, pos_tag))
                        return additional
        # franco-americano-alemany
        m = _TRES_ADJECTIUS.fullmatch(word)
        if m:
            adj1 = m.group(1).lower()
            adj2 = m.group(2).lower()
            if self._is_valid_adjective_form(adj1) and self._is_valid_adjective_form(adj2):
                adj3 = m.group(3).lower()
                for lemma, pos_tag in self._tagged(adj3):
                    if pos_tag is not None and pos_tag.startswith('A'):
                        additional.append((adj1 + 'o-' + adj2 + 'o-' + lemma, pos_tag))
                        return additional
        # Interpret deprecated characters of "ela geminada"
        # U+013F LATIN CAPITAL LETTER L WITH MIDDLE DOT
        # U+0140 LATIN SMALL LETTER L WITH MIDDLE DOT
        if 'ŀ' in word or 'Ŀ' in word:
            possible_word = lower_word.replace('ŀ', 'l·')
            return self._tagged(possible_word)
        # adjectives -iste in Valencian variant
        if self.is_valencian and lower_word.endswith('iste'):
            possible_adj_noun = jregex.java_replace(_ISTE, '$1ista', lower_word)
            for _lemma, pos_tag in self._tagged(possible_adj_noun):
                if pos_tag is not None:
                    if pos_tag == 'NCCS000':
                        additional.append((possible_adj_noun, 'NCMS000'))
                    if pos_tag == 'AQ0CS0':
                        additional.append((possible_adj_noun, 'AQ0MS0'))
                    if additional:
                        return additional
        return None

    def _wordform_has_postag(self, wordform, postag):
        return any(pos_tag == postag for _lemma, pos_tag in self._tagged(wordform))

    def _is_valid_adjective_form(self, word_stem):
        """check: grec(o)-, russ(o)-..."""
        return (word_stem + 'o' not in _NO_ALTRES_PREFIXOS
                and (self._wordform_has_postag(word_stem + 'a', 'AQ0FS0') or word_stem + 'o' in _ALTRES_PREFIXOS))

    def _additional_tags_for_incorrect_verbs(self, lower_word):
        """Get POS tags for incorrect verbs including inflected forms"""
        # enriure, enfotre...
        if lower_word.startswith('en'):
            selected = []
            lemma = ''
            for tw in self.word_tagger.tag(lower_word[2:]):
                if tw.pos_tag.startswith('V'):
                    selected.append(TaggedWord('en' + tw.lemma, tw.pos_tag))
                    lemma = 'en' + tw.lemma
            if selected and lemma in ('enfotre', 'enriure'):
                return self._with_lemma(lemma, selected)
        additional = []
        for pattern in (_DESINENCIES_1CONJ_0, _DESINENCIES_1CONJ_1):
            m = pattern.fullmatch(lower_word)
            if not m:
                continue
            base_lexeme = m.group(1)
            desinence = m.group(2)
            adjusted_lexeme = base_lexeme
            lexemes = [base_lexeme]
            if desinence[0] in 'eéiï':
                adjusted_lexeme = _adjust_lexeme_for_soft_vowel(base_lexeme)
                if adjusted_lexeme not in lexemes:
                    lexemes.append(adjusted_lexeme)
            if desinence.startswith('ï'):
                desinence = 'i' + desinence[1:]
            additional = self._try_tag(adjusted_lexeme + 'ar', 'cant' + desinence)
            for lex in lexemes:
                if not additional:
                    additional = self._try_tag(lex + 'ir', 'serv' + desinence)
                if not additional and lex.endswith('g'):
                    additional = self._try_tag(lex + 'uir', 'serv' + desinence)
            if not additional:
                eixer = base_lexeme + 'èixer'
                additional = self._try_tag(eixer, 'con' + desinence)
                if not additional:
                    additional = self._try_tag(eixer, 'desmer' + desinence)
            if additional:
                break
        return additional

    def _try_tag(self, infinitive, conjugated):
        if infinitive not in self.wrong_verbs:
            return []
        return self._with_lemma(infinitive, self.word_tagger.tag(conjugated))

    @staticmethod
    def _with_lemma(lemma, tagged_words):
        """asAnalyzedTokenListWithLemma: the verb readings with a new lemma"""
        # només verbs, no "cantada/NCFS000"
        return [(lemma, tw.pos_tag) for tw in tagged_words if tw.pos_tag.startswith('V')]


class VerbClassifier:
    """Port of org.languagetool.tagging.ca.VerbClassifier: the
    classification of verbs (transitive, intransitive, pronominal) of
    /ca/verbs_classification.txt"""

    VTR_CODE = 0b00000001
    INTR_CODE = 0b00000010
    PRON_CODE = 0b00000100

    _map = None
    _lock = threading.Lock()

    @classmethod
    def _init(cls):
        if cls._map is None:
            with cls._lock:
                if cls._map is None:
                    from ...language import RESOURCE_DIR
                    m = {}
                    with open(os.path.join(RESOURCE_DIR, 'ca', 'verbs_classification.txt'), encoding='utf-8') as f:
                        for line in f:
                            line = line.rstrip('\r\n')
                            i = line.find('#')
                            if i >= 0:
                                line = line[:i]
                            line = java_trim(line)
                            if not line:
                                continue
                            parts = line.split('=')
                            lemma = parts[0]
                            tags = parts[1]
                            # abs, aux, cop, imp, intr, pron, vtr
                            code = 0
                            if 'vtr' in tags:
                                code |= cls.VTR_CODE
                            if 'intr' in tags or 'abs' in tags:
                                code |= cls.INTR_CODE
                            if 'pron' in tags:
                                code |= cls.PRON_CODE
                            m[lemma] = code
                    cls._map = m
        return cls._map

    @classmethod
    def is_verb_code(cls, lemma, code_byte):
        code = cls._init().get(lemma)
        return code is not None and (code & code_byte) != 0

    @classmethod
    def is_intransitive(cls, lemma):
        return cls.is_verb_code(lemma, cls.INTR_CODE) and not cls.is_verb_code(lemma, cls.VTR_CODE)
