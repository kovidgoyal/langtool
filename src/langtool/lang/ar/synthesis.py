"""Port of org.languagetool.synthesis.ar.ArabicSynthesizer."""

from ... import jregex
from ...analysis import AnalyzedToken
from ...synthesis import BaseSynthesizer
from ...tools import java_hash_set_copy_order
from .tagging import TAG_MANAGER, _remove_end
from .tools import ALEF, FATHATAN, TEH_MARBUTA


class ArabicSynthesizer(BaseSynthesizer):
    """Arabic word form synthesizer (/ar/arabic_synth.dict with
    /ar/arabic_tags.txt). The dictionary only has the forms without
    proclitics and with the attached pronoun ه: the proclitics (conjunction,
    jar, article) are added to the stems according to the flags of the POS
    tag and the pronoun ه is removed for attached forms (correct_stem). With
    a POS tag regular expression, the flags of the regular expression are
    corrected first (correct_tag). The forms are not filtered with
    removeExceptions (both synthesize methods are overridden in Java); the
    synthesis without regular expression uses the dictionary only (Java:
    createStemmer()), without the manual additions and removals.

    tagger is the ArabicTagger used by the methods that tag words
    (inflect_lemma_like) and get the affixes of tokens."""

    def __init__(self, dictionary, tags_path, resource_dir=None, tagger=None):
        super().__init__(dictionary, tags_path, 'ar', resource_dir)
        self.tag_manager = TAG_MANAGER
        self.tagger = tagger

    def synthesize(self, token, pos_tag, pos_tag_regexp=False):
        if pos_tag is not None and pos_tag_regexp:
            p = jregex.compile(self.correct_tag(pos_tag))
            results = []
            for tag in self.get_possible_tags():
                if p.fullmatch(tag) and token.lemma is not None:
                    for wd in self.lookup(token.lemma, tag):
                        # adjust some stems according to the original postag
                        results.append(self.correct_stem(wd, pos_tag))
            return results
        word = ('null' if token.lemma is None else token.lemma) + '|' + ('null' if pos_tag is None else pos_tag)
        # adjust some stems
        return [self.correct_stem(stem, pos_tag) for stem, tag in self.dictionary.lookup(word)]

    def correct_tag(self, postag):
        """correctTag: remove the conjunction and the definite article
        flags, change all pronouns to one kind"""
        if postag is None:
            return None
        tm = self.tag_manager
        mypostag = tm.set_conjunction(postag, '-')
        mypostag = tm.set_definite(mypostag, '-')
        return tm.unify_pronoun_tag(mypostag)

    def get_pos_tag_correction(self, pos_tag):
        return self.correct_tag(pos_tag)

    def correct_stem(self, stem, postag):
        """correctStem: the stem with the proclitics of postag, without the
        pronoun ه of attached forms"""
        correct_stem = stem
        if postag is None:
            return stem
        tm = self.tag_manager
        if tm.is_attached(postag):
            correct_stem = _remove_end(correct_stem, 'ه')
        if tm.is_definite(postag):
            correct_stem = tm.get_definite_prefix(postag) + correct_stem  # can handle ال & لل
        if tm.has_jar(postag):
            correct_stem = tm.get_jar_prefix(postag) + correct_stem
        if tm.has_conjunction(postag):
            correct_stem = tm.get_conjunction_prefix(postag) + correct_stem
        return correct_stem

    def set_enclitic(self, token, suffix):
        """a new enclitic for the given word"""
        return self.set_enclitic_multiple(token, suffix)[0]

    def set_enclitic_multiple(self, token, suffix):
        """setEncliticMultiple: the forms of a token with a new enclitic
        (keeping its proclitics); "(word)" if there are none"""
        postag = token.pos_tag
        word = token.token
        default_wordlist = ['(' + word + ')']
        if not postag:
            return default_wordlist
        tm = self.tag_manager
        wordlist = []
        # the flag is by default '-', 'H' with a suffix
        flag = 'H' if suffix else '-'
        # save the proclitic
        procletic = self.tagger.get_proclitic(token)
        # set the enclitic flag, adjust the proclitics
        new_pos_tag = tm.set_proclitic_flags(tm.set_flag(postag, 'PRONOUN', flag))
        # synthesis => lookup for stems with similar postag and has enclitic flag
        lemma = token.lemma
        new_word_list = self.synthesize(AnalyzedToken(lemma, new_pos_tag, lemma), new_pos_tag)
        if new_word_list:
            for stem in new_word_list:
                # the tag dictionary only has Heh pronouns (for reasons of compression),
                # the other pronoun suffixes are added by the tagger or synthesizer
                if tm.has_pronoun(new_pos_tag) and flag == 'H':
                    if stem.endswith('ي'):
                        # a stem ending with Yeh for the 1st person pronoun:
                        # keep it for the Yeh pronoun suffix only
                        new_word = procletic + stem if suffix == 'ي' else ''
                    elif stem.endswith('ه'):
                        new_word = procletic + _remove_end(stem, 'ه') + suffix
                    else:
                        new_word = procletic + stem + suffix
                else:
                    new_word = procletic + stem
                if new_word:
                    wordlist.append(new_word)
        else:  # no word generated
            wordlist.append('(' + word + ')')
        if not wordlist:
            return default_wordlist
        return wordlist

    def set_jar_procletic(self, token, prefix):
        """setJarProcletic: a new jar proclitic for the given word (with the
        article of definite words)"""
        postag = token.pos_tag
        if not postag:
            return token.token
        # add the jar to the definite article
        if self.tag_manager.is_definite(postag):
            if prefix == 'ل':
                prefix += 'ل'
            else:  # case of Beh Jar, Kaf Jar, empty Jar
                prefix += 'ال'
        return self.set_procletic(token, prefix)

    def set_procletic(self, token, prefix):
        """setProcletic: a new proclitic for the given word (keeping its
        enclitic)"""
        postag = token.pos_tag
        word = token.token
        if not postag:
            return word
        # save the enclitic
        enclitic = self.tagger.get_enclitic(token)
        # remove the proclitics
        new_pos_tag = self.tag_manager.set_proclitic_flags(postag)
        lemma = token.lemma
        new_word_list = self.synthesize(AnalyzedToken(lemma, new_pos_tag, lemma), new_pos_tag)
        if new_word_list:
            stem = new_word_list[0]
            if self.tag_manager.has_pronoun(new_pos_tag):
                stem = _remove_end(stem, 'ه')
        else:  # no word generated
            stem = '(' + word + ')'
        return prefix + stem + enclitic

    def inflect_lemma_like(self, target_lemma, source_token):
        """inflectLemmaLike: the forms of target_lemma inflected like
        source_token (with its affixes); "[lemma]" if the lemma is unknown"""
        # make a token with the lemma
        token_read_list = self.tagger.tag(target_lemma)
        if not token_read_list.has_lemma(target_lemma):
            return ['[' + target_lemma + ']']
        source_postag = source_token.pos_tag
        # get the affixes
        prefix = self.tagger.get_proclitic(source_token)
        suffix = self.tagger.get_enclitic(source_token)
        wordlist = []
        # if we tag a diacritized verb, the tagger removes the diacritics and can generate other lemmas
        for current_token in token_read_list.readings:
            if target_lemma != current_token.lemma:
                continue
            merged_postag = self.tag_manager.merge_pos_tag(source_postag, current_token.pos_tag)
            # construct the word
            token = AnalyzedToken(prefix + target_lemma, merged_postag, target_lemma)
            wordlist.extend(self.set_enclitic_multiple(token, suffix))
        # remove duplicates (in the order of Java's HashSet)
        return java_hash_set_copy_order(wordlist)


def inflect_mafoul_mutlq(word):
    """inflectMafoulMutlq: generate the Mafoul Mutlaq from a masdar"""
    if word is None:
        return word
    if word.endswith(TEH_MARBUTA):
        return word + FATHATAN
    return word + FATHATAN + ALEF


def inflect_adjective_tanwin_nasb(word, feminin):
    """inflectAdjectiveTanwinNasb"""
    if word is None:
        return word
    if feminin:
        if word.endswith(TEH_MARBUTA):
            return word + FATHATAN
        return word + TEH_MARBUTA + FATHATAN
    # if masculine, remove the teh marbuta
    if word.endswith(TEH_MARBUTA):
        return word.replace(TEH_MARBUTA, '')
    # (Java: Character.toString(FATHATAN) + ALEF)
    return word + FATHATAN + ALEF
