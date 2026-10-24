"""Portuguese specific rules (port of org.languagetool.rules.pt).

The Java rules get a Locale("pt") from getLocale(), used for case
conversion; it has no special case mapping, so the default lower() is
used. The rules whose Java constructors take no language
(PortugueseDiacriticsRule, PortugueseWeaselWordsRule) use
Portuguese.getInstance(), i.e. the language pt."""

from ... import jregex
from ...rules.abstract_rules import (AbstractCompoundRule, AbstractDashRule, AbstractFillerWordsRule,
                                     AbstractSimpleReplaceRule, AbstractSimpleReplaceRule2, AbstractWordCoherencyRule,
                                     ReadabilityRule, WordRepeatBeginningRule, WrongWordInContextRule,
                                     load_compound_rule_data)
from ...rules.base import Category
from ...rules.core import Categories, WordRepeatRule
from ...rules.unit_conversion import (AbstractUnitConversionRule, CELSIUS, CHECK, CHECK_UNKNOWN_UNIT, CUBIC_METRE,
                                      DecimalFormat, FAHRENHEIT, FEET, HOUR, INCH, KILOGRAM, KILOMETRE_PER_HOUR,
                                      LITRE, METRE, MILE, OUNCE, POUND, SQUARE_METRE, SUGGESTION, UNIT_MISMATCH,
                                      YARD)
from ...tools import lowercase_first_char, java_split


def _portuguese():
    """Portuguese.getInstance(), the language of the rules whose Java
    constructors only get the messages"""
    from ...api import get_language
    return get_language('pt')


# --- AbstractSimpleReplaceRule subclasses ---

class PortugueseReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseReplaceRule: foreign
    words (estrangeirismos) of /pt/replace.txt, case insensitive."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('STYLE', messages)
        self.use_sub_rule_specific_ids()
        self.url = 'https://pt.wikipedia.org/wiki/Estrangeirismo'

    def get_wrong_words(self):
        return self.load_from_path('/pt/replace.txt')

    def get_id(self):
        return 'PT_SIMPLE_REPLACE'

    def get_description(self):
        return 'Palavras estrangeiras facilmente confundidas em Português'

    def get_short(self):
        return 'Estrangeirismo'

    def get_message(self, token_str, replacements):
        return ("'" + token_str + "' é um estrangeirismo. Em Português é mais comum usar: " + ', '.join(replacements)
                + '.')

    def is_case_sensitive(self):
        return False


class PortugueseAgreementReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseAgreementReplaceRule:
    spellings changed by the orthographic agreement of 1990
    (/pt/AOreplace.txt), case insensitive."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.add_example_pair('<marker>abstracto</marker>', '<marker>abstrato</marker>')
        self.use_sub_rule_specific_ids()
        self.url = 'https://pt.wikipedia.org/wiki/Lista_das_alterações_previstas_pelo_acordo_ortográfico_de_1990'

    def get_wrong_words(self):
        return self.load_from_path('/pt/AOreplace.txt')

    def get_id(self):
        return 'PT_AGREEMENT_REPLACE'

    def get_description(self):
        return 'Palavras alteradas pelo Acordo Ortográfico de 90'

    def get_short(self):
        return 'Forma do Acordo Ortográfico de 45.'

    def get_message(self, token_str, replacements):
        return ("'" + token_str + "' é uma forma do antigo acordo ortográfico. No novo acordo ortográfico, a palavra "
                "escreve-se assim: " + ', '.join(replacements) + '.')

    def is_case_sensitive(self):
        return False


class PortugueseOrthographyReplaceRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseOrthographyReplaceRule:
    misspellings of /pt/replace_orthography.txt, case insensitive."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.use_sub_rule_specific_ids()

    def get_wrong_words(self):
        return self.load_from_path('/pt/replace_orthography.txt')

    def get_id(self):
        return 'PT_SIMPLE_REPLACE_ORTHOGRAPHY'

    def is_case_sensitive(self):
        return False

    def get_description(self):
        return self.messages['desc_spelling']

    def get_short(self):
        return self.messages['desc_spelling_short']

    def get_message(self, token_str, replacements):
        return self.messages['spelling']


class EnglishContractionSpellingRule(AbstractSimpleReplaceRule):
    """Port of org.languagetool.rules.pt.EnglishContractionSpellingRule:
    English contractions without apostrophe (/pt/english_contractions.txt),
    case sensitive, lemmas are not checked."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('TYPOS', messages)
        self.add_example_pair('Ele adorava assistir <marker>whats</marker> cooking às sextas-feiras.',
                              "Ele adorava assistir <marker>what's</marker> cooking às sextas-feiras.")
        self.check_lemmas = False

    def get_wrong_words(self):
        return self.load_from_path('/pt/english_contractions.txt')

    def get_id(self):
        return 'PT_ENGLISH_CONTRACTION_ORTHOGRAPHY'

    def get_description(self):
        return 'Ortografia de contrações inglesas'

    def get_short(self):
        return 'Erro de ortografia inglesa'

    def get_message(self, token_str, replacements):
        return 'Caso seja uma contração da língua inglesa, prefira "' + replacements[0] + '".'

    def is_case_sensitive(self):
        return True


# --- AbstractSimpleReplaceRule2 subclasses ---

class _PathReplaceRule(AbstractSimpleReplaceRule2):
    """The AbstractSimpleReplaceRule2 subclasses whose Java constructors get
    the path of the replacement file (the files differ per variant)."""

    def __init__(self, messages, path, language):
        super().__init__(messages, language)
        if path is None:
            raise ValueError('path must not be None')
        self.path = path

    def get_file_names(self):
        return [self.path]

    def get_suggestions_separator(self):
        return ' ou '


class PortugalPortugueseReplaceRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugalPortugueseReplaceRule:
    Brazilian words (brasileirismos) and their European Portuguese
    equivalents (/pt/pt-PT/replace.txt for pt-PT); proper nouns (NP*) and
    immunized tokens are exceptions."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('<marker>aeromoça</marker>', '<marker>hospedeira de bordo</marker>')
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'PT_PT_SIMPLE_REPLACE'

    def get_description(self):
        return 'Brasileirismo: 1. palavras confundidas com as de Portugal'

    def get_short(self):
        return 'Palavra de português do Brasil'

    def get_message(self):
        return "'$match' é uma expressão brasileira, em português de Portugal utiliza-se: $suggestions"

    def is_token_exception(self, atr):
        # proper nouns tagged in multiwords are exceptions
        return atr.has_pos_tag_starting_with('NP') or atr.immunized


class BrazilianPortugueseReplaceRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.BrazilianPortugueseReplaceRule:
    European Portuguese words and their Brazilian equivalents
    (/pt/pt-BR/replace.txt for pt-BR); proper nouns (NP*) and immunized
    tokens are exceptions."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('<marker>hospedeira de bordo</marker>', '<marker>aeromoça</marker>')
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'PT_BR_SIMPLE_REPLACE'

    def get_description(self):
        return 'Palavras portuguesas facilmente confundidas com as do Brasil'

    def get_short(self):
        return 'Palavra do português de Portugal'

    def get_message(self):
        return '"$match" é uma expressão usada sobretudo em Portugal. No português brasileiro diz-se $suggestions'

    def is_token_exception(self, atr):
        # proper nouns tagged in multiwords are exceptions
        return atr.has_pos_tag_starting_with('NP') or atr.immunized


class PortugueseArchaismsRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseArchaismsRule: archaic
    words (/pt/pt-PT/archaisms.txt, /pt/pt-BR/archaisms.txt)."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('STYLE', messages)
        self.use_sub_rule_specific_ids()
        self.url = 'https://pt.wikipedia.org/wiki/Arca%C3%ADsmo'

    def get_id(self):
        return 'PT_ARCHAISMS_REPLACE'

    def get_description(self):
        return 'Palavras arcaicas evitáveis'

    def get_short(self):
        return 'Arcaísmo'

    def get_message(self):
        return '"$match" é um arcaísmo. É preferível dizer $suggestions.'


class PortugueseBarbarismsRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseBarbarismsRule: avoidable
    words of foreign origin (/pt/barbarisms.txt and the variant files);
    immunized tokens, proper nouns (NP*) and tokens tagged
    _english_ignore_ are exceptions."""

    issue_type = 'LocaleViolation'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('STYLE', messages)
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>curriculum vitae</marker>', '<marker>currículo</marker>')
        self.url = 'https://pt.wikipedia.org/wiki/Estrangeirismo'

    def get_id(self):
        return 'PT_BARBARISMS_REPLACE'

    def get_description(self):
        return 'Palavras de origem estrangeira evitáveis: $match'

    def get_short(self):
        return 'Estrangeirismo'

    def get_message(self):
        return '"$match" é um estrangeirismo. É preferível dizer $suggestions.'

    def is_token_exception(self, atr):
        # proper nouns tagged in multiwords are exceptions
        return (atr.immunized or atr.has_pos_tag_starting_with('NP')
                or atr.has_pos_tag_starting_with('_english_ignore_'))


class PortugueseClicheRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseClicheRule: clichés and
    idioms (/pt/cliches.txt and the variant files)."""

    issue_type = 'Style'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('STYLE', messages)
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>quente como uma fornalha</marker>', '<marker>quente</marker>')
        self.url = 'https://pt.wikipedia.org/wiki/Clichê'

    def get_id(self):
        return 'PT_CLICHE_REPLACE'

    def get_description(self):
        return 'Frases-feitas e expressões idiomáticas: $match'

    def get_short(self):
        return 'Frase-feita'

    def get_message(self):
        return '"$match" é uma frase-feita. É preferível dizer $suggestions.'


class PortugueseRedundancyRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseRedundancyRule:
    pleonasms (/pt/redundancies.txt and the variant files)."""

    issue_type = 'Style'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>duna de areia</marker>', '<marker>duna</marker>')
        self.url = 'https://pt.wikipedia.org/wiki/Pleonasmo'

    def get_id(self):
        return 'PT_REDUNDANCY_REPLACE'

    def get_description(self):
        return '1. Pleonasmos e redundâncias: $match'

    def get_short(self):
        return 'Pleonasmo'

    def get_message(self):
        return '"$match" é um pleonasmo. É preferível dizer $suggestions'


class PortugueseWordinessRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseWordinessRule: wordy
    expressions (/pt/wordiness.txt and the variant files)."""

    issue_type = 'Style'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('REDUNDANCY', messages)
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>Raramente é o caso em que acontece</marker> isto.',
                              '<marker>Raramente acontece</marker> isto.')
        self.url = 'https://pt.wikipedia.org/wiki/V%C3%ADcio_de_linguagem#Prolixidade_ou_preciosismo'

    def get_id(self):
        return 'PT_WORDINESS_REPLACE'

    def get_description(self):
        return '2. Expressões prolixas: $match'

    def get_short(self):
        return 'Expressão prolixa'

    def get_message(self):
        return '"$match" é uma expressão prolixa. É preferível dizer $suggestions.'


class PortugueseWikipediaRule(_PathReplaceRule):
    """Port of org.languagetool.rules.pt.PortugueseWikipediaRule: common
    errors of Wikipedia articles (/pt/wikipedia.txt and the variant
    files)."""

    issue_type = 'Grammar'

    def __init__(self, messages, path, language):
        super().__init__(messages, path, language)
        self.category = Categories.get('WIKIPEDIA', messages)
        self.use_sub_rule_specific_ids()
        # gradually making this rule obsolete, we've removed tests and also this example pair
        self.url = 'https://pt.wikipedia.org/wiki/Wikip%C3%A9dia:Lista_de_erros_comuns/M%C3%A1quinas'

    def get_id(self):
        return 'PT_WIKIPEDIA_COMMON_ERRORS'

    def get_description(self):
        return 'Erros frequentes nos artigos da Wikipédia: $match'

    def get_short(self):
        return 'Erro gramatical ou de normativa'

    def get_message(self):
        return 'Possível erro em "$match". Prefira $suggestions'


class PortugueseDiacriticsRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.pt.PortugueseDiacriticsRule: foreign
    words whose original spelling has diacritics (/pt/diacritics.txt),
    default off."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, _portuguese())
        self.set_default_off()
        self.category = Categories.get('TYPOS', messages)
        self.use_sub_rule_specific_ids()
        self.add_example_pair('<marker>coupe</marker>', '<marker>coupé</marker>')
        self.url = 'http://escreverbem.com.br/o-frances-no-portugues-2/'

    def get_file_names(self):
        return ['/pt/diacritics.txt']

    def get_id(self):
        return 'PT_DIACRITICS_REPLACE'

    def get_description(self):
        return 'Palavras estrangeiras com diacríticos: $match'

    def get_short(self):
        return 'A palavra estrangeira original tem diacrítico'

    def get_message(self):
        return ("'$match' é uma expressão estrangeira importada cuja grafia tem diacríticos. É preferível escrever "
                "$suggestions")

    def get_suggestions_separator(self):
        return ' ou '


class PortugueseWeaselWordsRule(AbstractSimpleReplaceRule2):
    """Port of org.languagetool.rules.pt.PortugueseWeaselWordsRule: weasel
    words (/pt/weaselwords.txt). Not used by Portuguese.getRelevantRules
    (commented out in Java)."""

    issue_type = 'Style'

    def __init__(self, messages, language=None):
        super().__init__(messages, _portuguese())
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair('<marker>Diz-se</marker> que programas gratuitos não têm qualidade.',
                              '<marker>XYZ</marker> dizem que programas gratuitos não têm qualidade. Por isso vendem '
                              'programas pagos.')
        self.url = 'https://pt.wikipedia.org/wiki/Weasel_word'

    def get_file_names(self):
        return ['/pt/weaselwords.txt']

    def get_id(self):
        return 'PT_WEASELWORD_REPLACE'

    def get_description(self):
        return 'Escrita avançada: Expressões evasivas'

    def get_short(self):
        return 'Expressão evasiva'

    def get_message(self):
        return ("'$match' é uma expressão ambígua e evasiva. Reconsidere o seu uso, de acordo com o objetivo do seu "
                "texto.")

    def get_suggestions_separator(self):
        return ' ou '


# --- other rules ---

class PortugueseWordCoherencyRule(AbstractWordCoherencyRule):
    """Port of org.languagetool.rules.pt.PortugueseWordCoherencyRule: words
    with two permitted spellings (/pt/coherency.txt) should be written
    consistently."""

    issue_type = 'Inconsistency'

    def __init__(self, messages, language=None):
        super().__init__(messages, language or _portuguese())
        self.category = Categories.get('STYLE', messages)
        self.add_example_pair(
            'Foi um período duradouro. Tão marcante e <marker>duradoiro</marker> dificilmente será esquecido.',
            'Foi um período duradouro. Tão marcante e <marker>duradouro</marker> dificilmente será esquecido.')

    def get_word_map(self):
        return self.load_word_map('/pt/coherency.txt')

    def get_message(self, word1, word2):
        return ('Não deve utilizar formas distintas de palavras com dupla grafia no mesmo texto. Escolha entre \''
                + word1 + "' e '" + word2 + "'.")

    def get_id(self):
        return 'PT_WORD_COHERENCY'

    def get_description(self):
        return 'Consistência de palavras com grafias múltiplas'


class PortugueseWrongWordInContextRule(WrongWordInContextRule):
    """Port of org.languagetool.rules.pt.PortugueseWrongWordInContextRule
    (/pt/wrongWordInContext.txt)."""

    issue_type = 'Grammar'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('SEMANTICS', messages)
        self.add_example_pair('O acidente <marker>infringiu</marker> grandes danos.',
                              'O acidente <marker>infligiu</marker> grandes danos.')

    def get_category_string(self):
        return 'Confusão de Palavras: $match'

    def get_id(self):
        return 'PORTUGUESE_WRONG_WORD_IN_CONTEXT'

    def get_description(self):
        return 'Confusão de palavra dentro do contexto (p.ex. infligir/infringir, etc.)'

    def get_filename(self):
        return '/pt/wrongWordInContext.txt'

    def get_message_string(self):
        return 'Pretende dizer <suggestion>$SUGGESTION</suggestion> em vez de $WRONGWORD?'

    def get_short_message_string(self):
        return 'Possível confusão de termos. Verifique.'

    def get_long_message_string(self):
        return ("Considere <suggestion>$SUGGESTION</suggestion>, i.e. $EXPLANATION_SUGGESTION, em vez de "
                "'$WRONGWORD', i.e. $EXPLANATION_WRONGWORD?")


# Tautonym list from https://en.wikipedia.org/wiki/List_of_tautonyms
_TAUTONYMS_GENUS = jregex.compile(
    'A(?:aptos|canthogyrus|chatina|gagus|gama|lburnus|lces|lle|losa|mandava|mazilia|meiva|nableps|nguilla'
    '|nhinga|nostomus|nser|nthias|pus|rcinella|riadne|spredo|stacus|vicularia|xis)|B(?:adis|agarius|agre|'
    'alanus|anjos|arbatula|arbus|asiliscus|atasio|elobranchus|elone|elonimorphis|idyanus|ison|ombina|oops'
    '|rama|rosme|ubo|ucayana|ufo|uteo|utis)|C(?:alamus|alappa|aleta|allichthys|alotes|apoeta|apreolus|ara'
    'cal|arassius|ardinalis|arduelis|aretta|asuarius|atla|atostomus|ephea|erastes|haca|halcides|handramar'
    'a|hanos|haos|hinchilla|hiropotes|hitala|hromis|iconia|idaris|inclus|itellus|lelia|occothraustes|ochl'
    'earius|oeligena|olius|olumella|oncholepas|onger|onta|onvoluta|ordylus|oscoroba|ossus|otinga|oturnix|'
    'rangon|ressida|rex|ricetus|rocuta|rossoptilon|uraeus|yanicterus|ygnus|ymbium|ynoglossus)|D(?:ama|ari'
    'o|entex|evario|iuca|ives|olabrifera)|E(?:nhydris|nsifera|nsis|rythrinus|xtra)|F(?:alcipennis|eroculu'
    's|icus|ragum|rancolinus|urcula)|G(?:agata|albula|allinago|allus|azella|emma|enetta|erbillus|ibberulu'
    's|iraffa|lis|lycimeris|lyphis|obio|oliathus|onorynchus|orilla|rapsus|rus|ryllotalpa|uira|ulo)|H(?:ar'
    'a|arpa|austellum|emilepidotus|eterophyes|imantopus|ippocampus|ippoglossus|ippopus|istrio|istrionicus'
    '|oolock|ucho|uso|yaena|ypnale)|I(?:chthyaetus|cterus|dea|guana|ndicator|ndri)|J(?:acana|aculus|anthi'
    'na)|K(?:achuga|oilofera)|L(?:actarius|agocephalus|agopus|agurus|ambis|emmus|epadogaster|erwa|euciscu'
    's|ima|imanda|imosa|iparis|ithognathus|ithophaga|oa|ota|uscinia|utjanus|utra|utraria|ynx)|M(?:acrophy'
    'llum|anacus|argaritifera|armota|artes|ascarinus|ashuna|egacephala|elanodera|eles|elo|elolontha|elong'
    'ena|enidia|ephitis|ercenaria|eretrix|erluccius|eza|icrostoma|ilvus|itella|itra|itu|odiolus|odulus|ol'
    'a|olossus|olva|onachus|oniliformis|ops|ustelus|yaka|yospalax|yotis)|N(?:aja|aja|angra|asua|atrix|eit'
    'a|iviventer|otopterus|ycticorax)|O(?:enanthe|gasawarana|liva|phioscincus|plopomus|reotragus|riolus)|'
    'P(?:agrus|angasius|apio|auxi|erdix|eriphylla|erna|etaurista|etronia|hocoena|hoenicurus|hoxinus|hycis'
    '|ica|ipa|ipile|ipistrellus|ipra|ithecia|lanorbis|lica|oliocephalus|ollachius|ollicipes|orites|orphyr'
    'io|orphyrolaema|orpita|orzana|ristis|seudobagarius|udu|uffinus|ungitius|yrrhocorax|yrrhula)|Q(?:uadr'
    'ula|uelea)|R(?:ama|anina|apa|asbora|attus|edunca|egulus|emora|etropinna|hinobatos|iparia|ita|upicapr'
    'a|upicola|utilus)|S(?:accolaimus|alamandra|arda|calpellum|cincus|colytus|ephanoides|erinus|odreana|o'
    'lea|phyraena|pinachia|pirorbis|pirula|prattus|quatina|taphylaea|uiriri|ula|uta|ynodus)|T(?:adorna|an'
    'danus|chagra|elescopium|emnurus|erebellum|etradactylus|etrax|herezopolis|hymallus|ibicen|inca|odus|o'
    'rpedo|rachurus|rachycorystes|rachyrinchus|ricornis|roglodytes|ropheops|ubifex|yrannus)|U(?:mbraculum'
    '|ncia)|V(?:anellus|elella|elutina|icugna|illosa|imba|iviparus|olva|ulpes)|X(?:anthocephalus|anthosti'
    'gma|enopirostris)|Ypiranga|Z(?:ebrus|era|ingel|ingha|oma|onia|ungaro|ygoneura)|Se')
_TAUTONYMS_SPECIES = jregex.compile(
    'a(?:aptos|canthogyrus|chatina|gagus|gama|lburnus|lces|lle|losa|mandava|mazilia|meiva|nableps|nguilla'
    '|nhinga|nostomus|nser|nthias|pus|rcinella|riadne|spredo|stacus|vicularia|xis)|b(?:adis|agarius|agre|'
    'alanus|anjos|arbatula|arbus|asiliscus|atasio|elobranchus|elone|elonimorphis|idyanus|ison|ombina|oops'
    '|rama|rosme|ubo|ucayana|ufo|uteo|utis)|c(?:alamus|alappa|aleta|allichthys|alotes|apoeta|apreolus|ara'
    'cal|arassius|ardinalis|arduelis|aretta|asuarius|atla|atostomus|ephea|erastes|haca|halcides|handramar'
    'a|hanos|haos|hinchilla|hiropotes|hitala|hromis|iconia|idaris|inclus|itellus|lelia|occothraustes|ochl'
    'earius|oeligena|olius|olumella|oncholepas|onger|onta|onvoluta|ordylus|oscoroba|ossus|otinga|oturnix|'
    'rangon|ressida|rex|ricetus|rocuta|rossoptilon|uraeus|yanicterus|ygnus|ymbium|ynoglossus)|d(?:ama|ari'
    'o|entex|evario|iuca|ives|olabrifera)|e(?:nhydris|nsifera|nsis|rythrinus|xtra)|f(?:alcipennis|eroculu'
    's|icus|ragum|rancolinus|urcula)|g(?:agata|albula|allinago|allus|azella|emma|enetta|erbillus|ibberulu'
    's|iraffa|lis|lycimeris|lyphis|obio|oliathus|onorynchus|orilla|rapsus|rus|ryllotalpa|uira|ulo)|h(?:ar'
    'a|arpa|austellum|emilepidotus|eterophyes|imantopus|ippocampus|ippoglossus|ippopus|istrio|istrionicus'
    '|oolock|ucho|uso|yaena|ypnale)|i(?:chthyaetus|cterus|dea|guana|ndicator|ndri)|j(?:acana|aculus|anthi'
    'na)|k(?:achuga|oilofera)|l(?:actarius|agocephalus|agopus|agurus|ambis|emmus|epadogaster|erwa|euciscu'
    's|ima|imanda|imosa|iparis|ithognathus|ithophaga|oa|ota|uscinia|utjanus|utra|utraria|ynx)|m(?:acrophy'
    'llum|anacus|argaritifera|armota|artes|ascarinus|ashuna|egacephala|elanodera|eles|elo|elolontha|elong'
    'ena|enidia|ephitis|ercenaria|eretrix|erluccius|eza|icrostoma|ilvus|itella|itra|itu|odiolus|odulus|ol'
    'a|olossus|olva|onachus|oniliformis|ops|ustelus|yaka|yospalax|yotis)|n(?:aja|aja|angra|asua|atrix|eit'
    'a|iviventer|otopterus|ycticorax)|o(?:enanthe|gasawarana|liva|phioscincus|plopomus|reotragus|riolus)|'
    'p(?:agrus|angasius|apio|auxi|erdix|eriphylla|erna|etaurista|etronia|hocoena|hoenicurus|hoxinus|hycis'
    '|ica|ipa|ipile|ipistrellus|ipra|ithecia|lanorbis|lica|oliocephalus|ollachius|ollicipes|orites|orphyr'
    'io|orphyrolaema|orpita|orzana|ristis|seudobagarius|udu|uffinus|ungitius|yrrhocorax|yrrhula)|q(?:uadr'
    'ula|uelea)|r(?:ama|anina|apa|asbora|attus|edunca|egulus|emora|etropinna|hinobatos|iparia|ita|upicapr'
    'a|upicola|utilus)|s(?:accolaimus|alamandra|arda|calpellum|cincus|colytus|ephanoides|erinus|odreana|o'
    'lea|phyraena|pinachia|pirorbis|pirula|prattus|quatina|taphylaea|uiriri|ula|uta|ynodus)|t(?:adorna|an'
    'danus|chagra|elescopium|emnurus|erebellum|etradactylus|etrax|herezopolis|hymallus|ibicen|inca|odus|o'
    'rpedo|rachurus|rachycorystes|rachyrinchus|ricornis|roglodytes|ropheops|ubifex|yrannus)|u(?:mbraculum'
    '|ncia)|v(?:anellus|elella|elutina|icugna|illosa|imba|iviparus|olva|ulpes)|x(?:anthocephalus|anthosti'
    'gma|enopirostris)|ypiranga|z(?:ebrus|era|ingel|ingha|oma|onia|ungaro|ygoneura)|se')
_PRONOUNS = jregex.compile('mas|n?[ao]s?|se')
_REDUPLICATED_ADVERBS = jregex.compile('já|logo|fácil', jregex.IGNORECASE)


class PortugueseWordRepeatRule(WordRepeatRule):
    """Port of org.languagetool.rules.pt.PortugueseWordRepeatRule: no false
    alarms for "blá blá", "se se", "Homo sapiens sapiens", "tuk tuk",
    tautonyms (Vulpes vulpes), pronouns after a hyphenated verb
    ("Coloquem-na na sala.") and reduplicated adverbs ("logo logo")."""

    rule_id = 'PORTUGUESE_WORD_REPEAT_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('REPETITIONS', messages)
        self.loc_quality_issue_type = 'Duplication'
        self.add_example_pair('Este <marker>é é</marker> apenas uma frase de exemplo.',
                              'Este <marker>é</marker> apenas uma frase de exemplo.')

    def ignore(self, tokens, position):
        if self.word_repetition_of('blá', tokens, position):
            return True  # "blá blá"
        if self.word_repetition_of('se', tokens, position):
            return True  # "se se"
        if self.word_repetition_of('sapiens', tokens, position):
            return True  # "Homo sapiens sapiens"
        if self.word_repetition_of('tuk', tokens, position):
            return True  # "tuk tuk"
        if _TAUTONYMS_GENUS.fullmatch(tokens[position - 1].token) and \
                _TAUTONYMS_SPECIES.fullmatch(tokens[position].token):
            return True  # e.g. Vulpes vulpes
        if (tokens[position - 2].token == '-' and not tokens[position - 1].whitespace_before
                and _PRONOUNS.fullmatch(tokens[position].token)):
            return True  # e.g. "Coloquem-na na sala."
        if _REDUPLICATED_ADVERBS.fullmatch(tokens[position].token):
            return True  # e.g. "Logo logo" => we need another rule to suggest a comma.
        return super().ignore(tokens, position)


_ADVERBS = frozenset((
    'Abaixo', 'Acaso', 'Acima', 'Acolá', 'Ademais', 'Adentro', 'Adiante', 'Adicionalmente', 'Afinal', 'Afora',
    'Agora', 'Aí', 'Ainda', 'Além', 'Algures', 'Ali', 'Aliás', 'Amanhã', 'Amiúde', 'Antigamente', 'Aonde',
    'Apenas', 'Apesar', 'Aquém', 'Aqui', 'Assaz', 'Assim', 'Até', 'Atrás', 'Bastante', 'Bem', 'Bondosamente',
    'Breve', 'Cá', 'Casualmente', 'Cedo', 'Certamente', 'Certo', 'Constantemente', 'Cuidadosamente', 'Dantes',
    'Debaixo', 'Debalde', 'Decerto', 'Defronte', 'Demais', 'Demasiado', 'Dentro', 'Depois', 'Depressa', 'Detrás',
    'Devagar', 'Doravante', 'E', 'Efetivamente', 'Embaixo', 'Embora', 'Enfim', 'Então', 'Entrementes',
    'Exclusivamente', 'Externamente', 'Fora', 'Frequentemente', 'Generosamente', 'Hoje', 'Imediatamente',
    'Inclusivamente', 'Inda', 'Já', 'Jamais', 'Lá', 'Logo', 'Longe', 'Mais', 'Mal', 'Mas', 'Melhor', 'Menos',
    'Mesmo', 'Muito', 'Não', 'Nem', 'Nenhures', 'Nunca', 'Onde', 'Ontem', 'Ora', 'Ou', 'Outra', 'Outro',
    'Outrora', 'Outrossim', 'Perto', 'Pior', 'Porventura', 'Possivelmente', 'Pouco', 'Primeiramente', 'Primeiro',
    'Principalmente', 'Provavelmente', 'Provisoriamente', 'Quanto', 'Quão', 'Quase', 'Quiçá', 'Realmente',
    'Salvo', 'Seguidamente', 'Sempre', 'Senão', 'Será', 'Sim', 'Simplesmente', 'Só', 'Sobremaneira', 'Sobremodo',
    'Sobretudo', 'Somente', 'Sucessivamente', 'Talvez', 'Também', 'Tampouco', 'Tanto', 'Tão', 'Tarde',
    'Ultimamente', 'Unicamente'))


class PortugueseWordRepeatBeginningRule(WordRepeatBeginningRule):
    """Port of org.languagetool.rules.pt.PortugueseWordRepeatBeginningRule:
    WordRepeatBeginningRule with a list of Portuguese adverbs."""

    rule_id = 'PORTUGUESE_WORD_REPEAT_BEGINNING_RULE'

    def __init__(self, messages, language):
        super().__init__(messages, language)
        self.category = Categories.get('STYLE', messages)
        self.loc_quality_issue_type = 'Style'
        self.add_example_pair(
            'Além disso, a rua é quase completamente residêncial. <marker>Além</marker> disso, foi chamada em nome '
            'de um poeta.',
            'Além disso, a rua é quase completamente residêncial. <marker>Foi</marker> chamada em nome de um poeta.')

    def is_adverb(self, atr):
        return atr.token in _ADVERBS


_FILLER_WORDS = frozenset((
    'abundante', 'acrescentou', 'acrescidamente', 'adição', 'agora', 'ainda', 'além', 'algo', 'algum', 'alguma',
    'algumas', 'alguns', 'aparecer', 'aparentemente', 'apenas', 'apesar', 'aproximadamente', 'assim', 'atrás',
    'atualmente', 'automaticamente', 'bem', 'bonito', 'certamente', 'certo', 'claramente', 'claro', 'completam',
    'completamente', 'completo', 'comumente', 'consequentemente', 'consistentemente', 'continuamente', 'contra',
    'contraste', 'contudo', 'cuidado', 'curto', 'dependendo', 'depois', 'desigual', 'determinado', 'deve',
    'dever', 'difícil', 'direito', 'dúvida', 'embora', 'enquanto', 'entanto', 'ergo', 'especial', 'estranhamente',
    'eventualmente', 'evidentemente', 'expressar', 'extremamente', 'fácil', 'famoso', 'feio', 'felizmente',
    'francamente', 'frequência', 'frequentemente', 'geralmente', 'graças', 'impressionante', 'impronunciável',
    'incomum', 'indizível', 'infelizmente', 'irrelevante', 'irrelevantes', 'já', 'justo', 'lento', 'longo',
    'lugares', 'maior', 'mais', 'mas', 'melhor', 'mesmo', 'muita', 'muitas', 'muito', 'muitos', 'múltipla', 'nada',
    'não', 'natural', 'naturalmente', 'natureza', 'nehumas', 'nenhum', 'nenhuma', 'nenhuns', 'nomeadamente',
    'normalmente', 'novo', 'número', 'nunca', 'óbvio', 'ocasionalmente', 'outra', 'outros', 'para', 'parente',
    'particularmente', 'pessoa', 'pode', 'poderia', 'pois', 'porém', 'porque', 'portanto', 'possível',
    'possivelmente', 'pouca', 'poucas', 'pouco', 'poucos', 'prático', 'precisas', 'principalmente', 'provável',
    'provavelmente', 'quaisquer', 'qualquer', 'quase', 'rápido', 'raramente', 'razoavelmente', 'realmente',
    'recentemente', 'relativamente', 'repente', 'sempre', 'senão', 'sentida', 'sentidas', 'sentido', 'sentidos',
    'siga', 'significativo', 'sim', 'simples', 'simplesmente', 'sobre', 'sozinho', 'suave', 'suavemente',
    'substancialmente', 'suficientemente', 'tipo', 'tornar', 'tornaram', 'tornou', 'total', 'totalmente', 'toda',
    'todas', 'todo', 'todos', 'tudo', 'ultrajante', 'velho', 'verdade', 'vez', 'vezes', 'volta'))


class PortugueseFillerWordsRule(AbstractFillerWordsRule):
    """Port of org.languagetool.rules.pt.PortugueseFillerWordsRule (default
    off); "mas" after a comma is no filler word."""

    def get_id(self):
        return self.rule_id + '_PT'

    def is_filler_word(self, token):
        return token in _FILLER_WORDS

    def is_exception(self, tokens, num):
        return tokens[num].token == 'mas' and num >= 1 and tokens[num - 1].token == ','


_COMPOUNDING_URL = 'https://pt.wikipedia.org/wiki/Lista_das_alterações_previstas_pelo_acordo_ortográfico_de_1990'


class PortugueseColourHyphenationRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.pt.PortugueseColourHyphenationRule:
    compound colour names (/pt/compound_colours.txt) are hyphenated."""

    issue_type = 'Grammar'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Nomes de cores são palavras compostas e devem ser hifenizados.',
                         'Esta palavra é composta por justaposição.',
                         'Esta palavra pode ser composta por justaposição ou hifenizada.',
                         'Nomes de cores são palavras compostas.')
        self.category = Categories.get('COMPOUNDING', messages)
        self.use_sub_rule_specific_ids()
        self.url = _COMPOUNDING_URL

    def get_id(self):
        return 'PT_COLOUR_HYPHENATION'

    def get_description(self):
        return 'Nomes de cores devem ser hifenizados: "$match"'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/pt/compound_colours.txt')


_VOWEL = jregex.compile('(?i).+[aeiou]$')
_RS = jregex.compile('(?i)^[rs].+')


class PostReformPortugueseCompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.pt.PostReformPortugueseCompoundRule:
    compounds of the orthography after the agreement of 1990
    (/pt/post-reform-compounds.txt); merging doubles an initial r or s after
    a vowel (ultra + som => ultrassom)."""

    issue_type = 'Grammar'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Esta palavra é hifenizada.',
                         'Esta palavra é composta por justaposição.',
                         'Esta palavra pode ser composta por justaposição ou hifenizada.',
                         'Este conjunto forma uma palavra composta.')
        self.category = Categories.get('COMPOUNDING', messages)
        self.use_sub_rule_specific_ids()
        self.url = _COMPOUNDING_URL

    def get_id(self):
        return 'PT_COMPOUNDS_POST_REFORM'

    def get_description(self):
        return 'Erro na formação da palavra composta "$match"'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/pt/post-reform-compounds.txt')

    def merge_compound(self, s, uncapitalize_mid_words):
        # This override is here to account for Portuguese transformations required as per the latest orthography:
        # ultra + som  => ultrassom (with <s> turned into <ss> to keep the sound).
        string_parts = java_split(s.replace('-', ' '), ' ')
        sb = []
        for k in range(len(string_parts)):
            if k == 0:
                sb.append(string_parts[0])
            else:
                # if previous element ends in vowel and current one starts with <r> or <s>, we need to double the
                # letter into a digraph that creates the sound we want
                if _VOWEL.fullmatch(string_parts[k - 1]) and _RS.fullmatch(string_parts[k]):
                    string_parts[k] = string_parts[k][0] + string_parts[k]
                sb.append(lowercase_first_char(string_parts[k]) if uncapitalize_mid_words else string_parts[k])
        return ''.join(sb)


class PreReformPortugueseCompoundRule(AbstractCompoundRule):
    """Port of org.languagetool.rules.pt.PreReformPortugueseCompoundRule:
    compounds of the orthography before the agreement of 1990
    (/pt/pre-reform-compounds.txt)."""

    issue_type = 'Grammar'

    def __init__(self, messages, language, user_config=None):
        super().__init__(messages, language, user_config,
                         'Esta palavra é hifenizada.',
                         'Esta palavra é composta por justaposição.',
                         'Esta palavra pode ser composta por justaposição ou hifenizada.',
                         'Este conjunto forma uma palavra composta.')
        self.category = Categories.get('COMPOUNDING', messages)
        self.use_sub_rule_specific_ids()

    def get_id(self):
        return 'PT_COMPOUNDS_PRE_REFORM'

    def get_description(self):
        return 'Palavras compostas'

    def get_compound_rule_data(self):
        return load_compound_rule_data(self.language, '/pt/pre-reform-compounds.txt')


# chars from http://unicode.e-workers.de/portugiesisch.php
_PT_LETTER = jregex.compile('[a-zA-ZÂâÃãÇçÊêÓóÔôÕõü]')


class PostReformPortugueseDashRule(AbstractDashRule):
    """Port of org.languagetool.rules.pt.PostReformPortugueseDashRule:
    compounds of /pt/post-reform-compounds.txt written with dashes instead
    of hyphens."""

    issue_type = 'Typographical'

    def get_id(self):
        return 'PT_POSAO_DASH_RULE'

    def get_description(self):
        return 'Travessões no lugar de hífens'

    def get_message(self):
        return 'Um travessão foi utilizado em vez de um hífen.'

    def is_boundary(self, s):
        return not _PT_LETTER.fullmatch(s)

    def get_compounds_data(self):
        return self.load_compound_file('/pt/post-reform-compounds.txt')


class PreReformPortugueseDashRule(AbstractDashRule):
    """Port of org.languagetool.rules.pt.PreReformPortugueseDashRule:
    compounds of /pt/pre-reform-compounds.txt written with dashes instead of
    hyphens."""

    issue_type = 'Typographical'

    def get_id(self):
        return 'PT_PREAO_DASH_RULE'

    def get_description(self):
        return 'Travessões no lugar de hífens'

    def get_message(self):
        return 'Um travessão foi utilizado em vez de um hífen.'

    def is_boundary(self, s):
        return not _PT_LETTER.fullmatch(s)

    def get_compounds_data(self):
        return self.load_compound_file('/pt/pre-reform-compounds.txt')


_LEVEL_NAMES = ('Muito complexo', 'Complexo', 'Moderadamente complexo', 'Meio-termo', 'Moderadamente simples',
                'Simples', 'Muito simples')
_PT_VOWELS = frozenset('aeiouyAEIOUYáéíóúàÁÉÍÓÚÀâêôÂÊÔÜ')


class PortugueseReadabilityRule(ReadabilityRule):
    """Port of org.languagetool.rules.pt.PortugueseReadabilityRule: the
    Flesch reading ease adapted to Portuguese (FRE = 206.84 - 1.02 * ASL -
    60.0 * ASW) with a Portuguese syllable count."""

    def __init__(self, messages, language, user_config=None, too_easy_test=False, level=-1, default_on=False):
        super().__init__(messages, language, user_config, too_easy_test, level, default_on)
        self.category = Category('TEXT_ANALYSIS', 'Análise de Texto', 'INTERNAL', False)

    def get_id(self, too_easy_test=None):
        if too_easy_test is None:
            too_easy_test = self.too_easy_test
        if too_easy_test:
            return 'READABILITY_RULE_SIMPLE_PT'
        return 'READABILITY_RULE_DIFFICULT_PT'

    def get_description(self):
        if self.too_easy_test:
            return 'Legibilidade: texto demasiado simples'
        return 'Legibilidade: texto demasiado complexo'

    def print_message_level(self, level):
        if 0 <= level <= 6:
            return ' {Nível ' + str(level) + ': ' + _LEVEL_NAMES[level] + '}'
        return ''

    def get_message(self, level, fre, asl, asw):
        if self.too_easy_test:
            simple, few = 'fácil', 'poucas'
        else:
            simple, few = 'difícil', 'muitas'
        return ('Legibilidade {FRE: ' + str(fre) + ', ASL: ' + str(asl) + ', ASW: ' + str(asw)
                + '}: O texto deste parágrafo é ' + simple + self.print_message_level(level) + '. Tem ' + few
                + ' palavras por frase e ' + few + ' sílabas por palavra.')

    def get_configure_text(self):
        return 'Nível de legibilidade 0 (muito difícil) a 6 (muito fácil):'

    @staticmethod
    def get_flesch_reading_ease(asl, asw):
        # Equation for readability
        # FRE = Flesch-Reading-Ease
        # ASL = Average Sentence Length
        # ASW = Average Number of Syllables per Word
        # Portuguese: FRE= 206,840 - ( 1.020 * ASL ) - ( 60.0 * ASW )
        # http://ridi.ibict.br/bitstream/123456789/273/1/EnyIS2007.pdf
        return 206.84 - (1.02 * asl) - (60.0 * asw)

    def simple_syllables_count(self, word):
        if not word:
            return 0
        n_syllables = 0
        if word[0] in _PT_VOWELS:
            n_syllables += 1
        last_double = False
        for i in range(1, len(word)):
            c = word[i]
            if c in _PT_VOWELS:
                cl = word[i - 1]
                if last_double:
                    n_syllables += 1
                    last_double = False
                elif ((c in 'ãõ' and cl in 'eo')
                      or (c == 'a' and cl in 'eiíouú')
                      or (c == 'e' and cl in 'eiíoau')
                      or (c == 'i' and cl in 'aeouáé')
                      or (c == 'í' and cl in 'ae')
                      or (c == 'o' and cl in 'aáeéiíu')
                      or (c == 'u' and cl in 'aáeéio')
                      or (c == 'ú' and cl in 'aeo')):
                    last_double = True
                else:
                    n_syllables += 1
                    last_double = False
            else:
                last_double = False
        return 1 if n_syllables == 0 else n_syllables


class PortugueseUnitConversionRule(AbstractUnitConversionRule):
    """Port of org.languagetool.rules.pt.PortugueseUnitConversionRule: the
    AbstractUnitConversionRule with Portuguese unit names, the number format
    of Locale.GERMANY (decimal comma, at most 2 fraction digits, HALF_UP)
    and Portuguese messages."""

    _format = DecimalFormat(decimal=',', grouping='.', maximum_fraction_digits=2)

    _MESSAGES = {
        CHECK: 'Esta conversão não parece estar precisa. Gostaria de corrigi-la?',
        SUGGESTION: 'Deseja adicionar automaticamente uma conversão ao sistema métrico?',
        CHECK_UNKNOWN_UNIT: 'A unidade usada nesta conversão não foi reconhecida.',
        UNIT_MISMATCH: 'Estas unidades de medida não são compatíveis.',
    }
    _SHORT_MESSAGES = {
        CHECK: 'Conversão incorreta. Corrigir?',
        SUGGESTION: 'Adicionar conversão ao sistema métrico?',
        CHECK_UNKNOWN_UNIT: 'Unidade desconhecida.',
        UNIT_MISMATCH: 'Unidade incompatível.',
    }

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        add = self.add_unit
        add('(qui|ki)lo(grama)?', KILOGRAM, 'quilogramas', 1, True)
        add('grama', KILOGRAM, 'gramas', 1e-3, True)
        add('toneladas?', KILOGRAM, 'toneladas', 1e3, True)
        add('libras?', POUND, 'libras', 1, False)
        add('onças?', OUNCE, 'onças', 1, False)
        add('milhas?', MILE, 'milhas', 1, False)
        add('jardas?', YARD, 'jardas', 1, False)
        add('pés?', FEET, 'pés', 1, False)
        add('polegadas?', INCH, 'polegadas', 1, False)
        add('(qu|k)ilômetros? por hora', KILOMETRE_PER_HOUR, 'quilômetros por hora', 1, True)
        add('milhas? por hora', MILE.divide(HOUR), 'milhas por hora', 1, False)
        add('metros?', METRE, 'metros', 1, True)
        add('(qu|k)ilômetros?', METRE, 'quilômetros', 1e3, True)
        add('decímetros?', METRE, 'decímetros', 1e-1, False)  # metric, but should not be suggested
        add('centímetros?', METRE, 'centímetros', 1e-2, True)
        add('milímetros?', METRE, 'milímetros', 1e-3, True)
        add('micrômetros?', METRE, 'micrômetros', 1e-6, True)
        add('nanômetros?', METRE, 'nanômetros', 1e-9, True)
        add('picômetros?', METRE, 'picômetros', 1e-12, True)
        add('fentômetros?', METRE, 'fentômetros', 1e-15, True)
        add('metros? quadrados?', SQUARE_METRE, 'metros quadrados', 1, True)
        add('hectar(es)?', SQUARE_METRE, 'hectares', 1e4, True)
        add('ares?', SQUARE_METRE, 'ares', 1e2, True)
        add('(k|qui)ilômetros? quadrados?', SQUARE_METRE, 'quilômetros quadrados', 1e6, True)
        add('decímetros? quadrados?', SQUARE_METRE, 'decímetros quadrados', 1e-2, False)  # Metric, not commonly used
        add('centímetros? quadrados?', SQUARE_METRE, 'centímetros quadrados', 1e-4, True)
        add('milímetros? quadrados?', SQUARE_METRE, 'milímetros quadrados', 1e-6, True)
        add('micrômetros? quadrados?', SQUARE_METRE, 'micrômetros quadrados', 1e-12, True)
        add('nanômetros? quadrados?', SQUARE_METRE, 'nanômetros quadrados', 1e-18, True)
        add('metros? cúbicos?', CUBIC_METRE, 'metros cúbicos', 1, True)
        add('(k|qu)ilômetros? cúbicos?', CUBIC_METRE, 'quilômetros cúbicos', 1e9, True)
        add('decímetros? cúbicos?', CUBIC_METRE, 'decímetros cúbicos', 1e-3, False)  # Metric, not commonly used
        add('centímetros? cúbicos?', CUBIC_METRE, 'centímetros cúbicos', 1e-6, True)
        add('milímetros? cúbicos?', CUBIC_METRE, 'milímetros cúbicos', 1e-9, True)
        add('micrômetros? cúbicos?', CUBIC_METRE, 'micrômetros cúbicos', 1e-18, True)
        add('nanômetros? cúbicos?', CUBIC_METRE, 'nanômetros cúbicos', 1e-27, True)
        add('litros?', LITRE, 'litros', 1, True)
        add('mililitros?', LITRE, 'mililitros', 1e-3, True)
        add('(?:Graus)? Fahrenheit', FAHRENHEIT, 'graus Fahrenheit', 1, False)
        add('(?:Graus)? (Celsi[ou]s|[cC]entígrados?)', CELSIUS, 'graus Celsius', 1, True)

    def get_id(self):
        return 'UNIDADES_METRICAS'

    def format_rounded(self, s):
        return 'aprox. ' + s

    def get_description(self):
        return 'Sugere ou verifica informações equivalentes à métrica de unidades de medida específicas.'

    def get_message(self, message):
        return self._MESSAGES[message]

    def get_short_message(self, message):
        return self._SHORT_MESSAGES[message]

    def get_number_format(self):
        return self._format
