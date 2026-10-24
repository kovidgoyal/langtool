"""Arabic specific rules (port of org.languagetool.rules.ar)."""

from ...analysis import AnalyzedToken
from ...rules.abstract_rules import AbstractSimpleReplaceRule2, AbstractWordCoherencyRule, WrongWordInContextRule
from ...rules.base import RuleMatch
from ...rules.core import Categories, CommaWhitespaceRule, DoublePunctuationRule, WordRepeatRule
from ...tools import java_split
from .tagging import TAG_MANAGER

_ARABIC_COMMA = '،'


class ArabicCommaWhitespaceRule(CommaWhitespaceRule):
    """Port of org.languagetool.rules.ar.ArabicCommaWhitespaceRule: the
    CommaWhitespaceRule for the Arabic comma"""

    rule_id = 'ARABIC_COMMA_PARENTHESIS_WHITESPACE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('نعم<marker> ،</marker> لقد نجحنا.', 'نعم<marker>،</marker> لقد نجحنا.')

    def get_comma_character(self):
        return _ARABIC_COMMA


class ArabicQuestionMarkWhitespaceRule(CommaWhitespaceRule):
    """Port of org.languagetool.rules.ar.ArabicQuestionMarkWhitespaceRule:
    the CommaWhitespaceRule for the Arabic question mark"""

    rule_id = 'ARABIC_QM_WHITESPACE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('نعم<marker> ؟</marker>', 'نعم<marker>؟</marker>')

    def get_comma_character(self):
        return '؟'


class ArabicSemiColonWhitespaceRule(CommaWhitespaceRule):
    """Port of org.languagetool.rules.ar.ArabicSemiColonWhitespaceRule: the
    CommaWhitespaceRule for the Arabic semicolon (Java's example pair is the
    one of the question mark rule)"""

    rule_id = 'ARABIC_SC_WHITESPACE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('نعم<marker> ؟</marker>', 'نعم<marker>؟</marker>')

    def get_comma_character(self):
        return '؛'


class ArabicDoublePunctuationRule(DoublePunctuationRule):
    """Port of org.languagetool.rules.ar.ArabicDoublePunctuationRule: ".."
    and "،،\""""

    rule_id = 'ARABIC_DOUBLE_PUNCTUATION'

    def get_comma_character(self):
        return _ARABIC_COMMA


class ArabicWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.ar.ArabicWordRepeatRule: the
    WordRepeatRule without some accepted repetitions"""

    rule_id = 'ARABIC_WORD_REPEAT_RULE'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.add_example_pair('هذا <marker>فقط فقط</marker> مثال.', 'هذا <marker>فقط</marker> مثال.')

    def ignore(self, tokens, position):
        if self.word_repetition_of('خطوة', tokens, position):
            return True  # "نفذت التعليمات خطوة خطوة."
        if self.word_repetition_of('رويدا', tokens, position):
            return True
        return super().ignore(tokens, position)


class _ArabicReplaceRule(AbstractSimpleReplaceRule2):
    """AbstractSimpleReplaceRule2 with the data file file_name (getLocale()
    is Locale("ar"), which AbstractSimpleReplaceRule2 does not use)"""

    file_name = None

    def get_file_names(self):
        return [self.file_name]


class ArabicSimpleReplaceRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicSimpleReplaceRule: words to
    avoid (/ar/replaces.txt)"""

    file_name = 'ar/replaces.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('CONFUSED_WORDS', messages)
        self.add_example_pair('<marker>الى</marker>', '<marker>إلى</marker>')

    def get_id(self):
        return 'AR_SIMPLE_REPLACE'

    def get_description(self):
        return 'قاعدة تطابق الكلمات التي يجب تجنبها وتقترح تصويبا لها'

    def get_short(self):
        return 'خطأ، يفضل أن  يقال:'

    def get_message(self):
        return 'قل $suggestions'

    def get_suggestions_separator(self):
        return ' أو  '


class ArabicDiacriticsRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicDiacriticsRule: words that
    should get diacritics to clarify their pronunciation
    (/ar/diacritics.txt)"""

    file_name = '/ar/diacritics.txt'
    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('<marker>تجربة</marker>', '<marker>تجرِِبة</marker>')

    def get_id(self):
        return 'AR_DIACRITICS_REPLACE'

    def get_description(self):
        return 'كلمات مشكولة للتوضيح'

    def get_short(self):
        return 'كلمات يستحسن أن تشكّل لتصحيح نطقها'

    def get_message(self):
        return "'$match' كلمة يشيع نطقها نطقا خاطئا لذا نقترح تشكيلها كالآتي: $suggestions"

    def get_suggestions_separator(self):
        return ' أو '


class ArabicDarjaRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicDarjaRule: replacements for
    colloquial or foreign words (/ar/darja.txt)"""

    file_name = '/ar/darja.txt'
    issue_type = 'LocaleViolation'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('<marker>طرشي</marker>', '<marker>فلفل حلو</marker>')

    def get_id(self):
        return 'AR_DARJA_REPLACE'

    def get_description(self):
        return 'كلمات بديلة للكلمات العامية أو الأجنبية'

    def get_short(self):
        return 'كلمات بديلة للكلمات العامية أو الأجنبية'

    def get_message(self):
        return 'الكلمة عامية  أو أجنبية يفضل أن يقال $suggestions'

    def get_suggestions_separator(self):
        return ' أو  '


class ArabicHomophonesRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicHomophonesRule: words that
    sound alike, like ظ and ض (/ar/homophones.txt)"""

    file_name = 'ar/homophones.txt'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('CONFUSED_WORDS', messages)
        self.add_example_pair('<marker>ضن</marker>', '<marker>ظن</marker>')

    def get_id(self):
        return 'AR_HOMOPHONES_REPLACE'

    def get_description(self):
        return 'كلمات متشابهة لفظا للتوضيح، يرجى التحقق منها مثل تشابه الظاء والضاد.'

    def get_short(self):
        return 'كلمات متشابهة لفظا يرجى التحقق منها'

    def get_message(self):
        return 'قل $suggestions'

    def get_suggestions_separator(self):
        return ' أو  '


class ArabicRedundancyRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicRedundancyRule: redundant
    expressions (/ar/redundancies.txt)"""

    file_name = '/ar/redundancies.txt'
    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.add_example_pair('<marker>سوف لن</marker>', '<marker>لن</marker>')

    def get_id(self):
        return 'AR_REDUNDANCY_REPLACE'

    def get_description(self):
        return '1. تكرار (عام)'

    def get_short(self):
        return 'تكرار'

    def get_message(self):
        return "'$match' تعبير فيه تكرار.في بعض الحالات، يستحسن استعمال $suggestions"

    def get_suggestions_separator(self):
        return ' أو '


class ArabicWordinessRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicWordinessRule: wordy
    expressions (/ar/wordiness.txt)"""

    file_name = '/ar/wordiness.txt'
    issue_type = 'Style'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.add_example_pair('<marker>هناك خطأ في العبارة</marker>', '<marker>في العبارة خطأ</marker>')

    def get_id(self):
        return 'AR_WORDINESS_REPLACE'

    def get_description(self):
        return '2. حشو(تعبير فيه تكرار)'

    def get_short(self):
        return 'حشو (تعبير فيه تكرار)'

    def get_message(self):
        return "'$match' تعبير فيه حشو يفضل أن يقال $suggestions"

    def get_suggestions_separator(self):
        return ' أو '


class ArabicWordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.ar.ArabicWordCoherencyRule: words with
    more than one accepted spelling (/ar/coherency.txt) should be written
    consistently"""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('وزارة الشؤون الخارجية تهتم  بكل <marker>شئون</marker> العالم.',
                              'وزارة الشؤون الخارجية تهتم  بكل <marker>شؤون</marker> العالم.')

    def get_word_map(self):
        return self.load_word_map('/ar/coherency.txt')

    def get_message(self, word1, word2):
        return "تجنب استعمال شكلين للكلمة نفسها ('" + word1 + "' و '" + word2 + "') في  النص نفسه."

    def get_id(self):
        return 'AR_WORD_COHERENCY'

    def get_description(self):
        return 'ضبط انسجام التهجئة للكلمات التي تكتب بطرق مختلفة مقبولة.'


class ArabicWrongWordInContextRule(WrongWordInContextRule):
    """Port of org.languagetool.rules.ar.ArabicWrongWordInContextRule:
    easily confused words (/ar/wrongWordInContext.txt)"""

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.add_example_pair('من سوء <marker>الضن</marker> بالله ترك الأمر بالمعروف.',
                              'من سوء <marker>الظن</marker> بالله ترك الأمر بالمعروف.')

    def get_category_string(self):
        return 'كلمات متشابهة'

    def get_id(self):
        return 'ARABIC_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'كلمات شائعةمتشابهة (ظل/ضلَ, رؤيا/رؤية الخ.)'

    def get_filename(self):
        return '/ar/wrongWordInContext.txt'

    def get_message_string(self):
        return "احتمال كلمة متشابهة: هل تقصد <suggestion>$SUGGESTION</suggestion> بدلا من '$WRONGWORD'?"

    def get_short_message_string(self):
        return 'احتمال كلمة متشابهة'

    def get_long_message_string(self):
        return ("احتمال كلمة متشابهة: هل تقصد <suggestion>$SUGGESTION</suggestion> (= $EXPLANATION_SUGGESTION) "
                "بدلا من '$WRONGWORD' (= $EXPLANATION_WRONGWORD)?")


class ArabicTransVerbRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicTransVerbRule: verbs with an
    attached pronoun that are transitive with a preposition
    (/ar/verb_trans_to_untrans2.txt: verb lemma = prepositions), e.g.
    "أفاضها" -> "أفاض فيها". (Java creates an ArabicTagger with the new
    style pronoun tags that it does not use.)"""

    file_name = '/ar/verb_trans_to_untrans2.txt'
    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.tag_manager = TAG_MANAGER
        self.category = Categories.get('MISC', messages)
        self.add_example_pair('The train arrived <marker>a hour</marker> ago.',
                              'The train arrived <marker>an hour</marker> ago.')
        # get the wrong words from the resource file
        self.wrong_words = self.get_wrong_words()

    def get_id(self):
        return 'AR_VERB_TRANSITIVE_IINDIRECT'

    def get_description(self):
        return 'َTransitive verbs corrected to indirect transitive'

    def get_short(self):
        return 'أفعال متعدية بحرف، يخطئ في تعديتها'

    def get_message(self):
        return "'$match' الفعل خاطئ في التعدية بحرف: $suggestions"

    def get_suggestions_separator(self):
        return ' أو '

    def match(self, sentence):
        rule_matches = []
        if not self.wrong_words:
            return rule_matches
        tokens = sentence.non_blank_tokens
        prev_token_index = 0
        for i in range(1, len(tokens)):  # ignoring token 0, i.e., SENT_START
            token = tokens[i]
            prev_token = tokens[prev_token_index] if prev_token_index > 0 else None
            if prev_token is not None:
                prev_token_str = prev_token.token
                # test if the first token is a verb
                is_attached_verb_transitive = self._is_attached_transitive_verb(prev_token)
                # test if the preposition token is suitable for verb token (previous)
                prepositions = self._get_proper_preposition_for_transitive_verb(prev_token)
                is_right_preposition = self._is_right_preposition(token, prepositions)
                # the verb is attached and the next token is not the suitable preposition:
                # we give the correct new form
                if is_attached_verb_transitive and not is_right_preposition:
                    verb = self._generate_unattached_new_form(prev_token)
                    # generate suggestion according to suggested prepositions
                    # FIXME: test all suggestions
                    preposition = self._generate_attached_new_form(prepositions[0], prev_token)
                    replacement = verb + ' ' + preposition
                    msg = ('قل <suggestion>' + replacement + "</suggestion> بدلا من '" + prev_token_str
                           + "' لأنّ الفعل  متعد بحرف  .")
                    rule_matches.append(RuleMatch(self, sentence, prev_token.start_pos, prev_token.end_pos, msg,
                                                  'خطأ في الفعل المتعدي بحرف', prev_token.start_pos, token.end_pos))
            prev_token_index = i if self._is_attached_transitive_verb(token) else 0
        return rule_matches

    def _lemma_match(self, mytoken):
        for verb_tok in mytoken.readings:
            # test if the verb is in the verb list
            if verb_tok.pos_tag is not None:
                verb_lemma_match = self.wrong_words[-1].get(verb_tok.lemma)
                # the lemma is found in the dictionary file
                if verb_lemma_match is not None:
                    return verb_lemma_match
        return None

    def _is_attached_transitive_verb(self, mytoken):
        return self._lemma_match(mytoken) is not None

    def _get_proper_preposition_for_transitive_verb(self, mytoken):
        """the proper prepositions of a transitive verb"""
        m = self._lemma_match(mytoken)
        if m is not None:
            return java_split(m[0], '|')
        return []

    @staticmethod
    def _is_right_preposition(next_token, preposition_list):
        # FIXME: test if the next token is the suitable preposition for the previous token as verbtoken
        return next_token.readings[0].lemma in preposition_list

    def _generate_new_form(self, word, pos_tag, flag):
        """the form of word for pos_tag with the pronoun flag"""
        new_pos_tag = self.tag_manager.set_flag(pos_tag, 'PRONOUN', flag)
        # FIXME: remove the specific flag for option D
        if flag != '-':
            new_pos_tag = self.tag_manager.set_flag(new_pos_tag, 'OPTION', 'D')
        # generate the new preposition according to the modified postag
        new_word_list = self.language.synthesizer.synthesize(AnalyzedToken(word, new_pos_tag, word), new_pos_tag)
        return new_word_list[0] if new_word_list else ''

    def _generate_unattached_new_form(self, token):
        reading = token.readings[0]
        return self._generate_new_form(reading.lemma, reading.pos_tag, '-')

    def _generate_attached_new_form(self, preposition_lemma, prevtoken):
        # FIXME: generate multiple cases
        postag = 'PR-;---;---'
        flag = self.tag_manager.get_flag(prevtoken.readings[0].pos_tag, 'PRONOUN')
        return self._generate_new_form(preposition_lemma, postag, flag)


class ArabicInflectedOneWordReplaceRule(_ArabicReplaceRule):
    """Port of org.languagetool.rules.ar.ArabicInflectedOneWordReplaceRule:
    words (lemmas of /ar/inflected_one_word.txt) to replace by other words,
    the suggestions are inflected like the wrong word. (Java creates an
    ArabicTagger with the new style pronoun tags that it does not use.)"""

    file_name = '/ar/inflected_one_word.txt'
    issue_type = 'Inconsistency'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('MISC', messages)
        self.add_example_pair('أجريت <marker>أبحاثا</marker> في المخبر', 'أجريت <marker>بحوثا</marker> في المخبر.')
        # get the wrong words from the resource file
        self.wrong_words = self.get_wrong_words()

    def get_id(self):
        return 'AR_INFLECTED_ONE_WORD'

    def get_description(self):
        return 'قاعدة تطابق الكلمات التي يجب تجنبها وتقترح تصويبا لها'

    def get_short(self):
        return 'خطأ، يفضل أن  يقال:'

    def get_message(self):
        return " لا تقل '$match' بل قل: $suggestions"

    def get_suggestions_separator(self):
        return ' أو '

    def match(self, sentence):
        rule_matches = []
        if not self.wrong_words:
            return rule_matches
        synthesizer = self.language.synthesizer
        for token in sentence.non_blank_tokens:
            # browse each reading
            for word_tok in token.readings:
                # test if the token is a word to replace
                propositions_with_message = self._get_suggested_words(word_tok)
                if propositions_with_message is None:
                    continue
                suggestion, sug_msg = propositions_with_message
                propositions = java_split(suggestion, '|')
                sug_msg = sug_msg if sug_msg is not None else ''
                # generate the suggestions according to the suggested words
                replacement = []
                for proposition in propositions:
                    for w in synthesizer.inflect_lemma_like(proposition, word_tok):
                        replacement.append('<suggestion>' + w + '</suggestion>&nbsp;')
                msg = "' الكلمة خاطئة " + token.token + " ' ،" + sug_msg + '. استعمل  ' + ''.join(replacement)
                rule_matches.append(RuleMatch(self, sentence, token.start_pos, token.end_pos, msg,
                                              'خطأ في استعمال كلمة:' + sug_msg, token.start_pos, token.end_pos))
        return rule_matches

    def _get_suggested_words(self, word_tok):
        """the (suggestion, message) for a reading with a lemma of the rule
        file"""
        if word_tok.pos_tag is not None:
            return self.wrong_words[-1].get(word_tok.lemma)
        return None
