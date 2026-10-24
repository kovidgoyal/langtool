"""Port of org.languagetool.rules.pt.PortugueseAccentuationCheckRule (with
PortugueseAccentuationDataLoader)."""

import threading

from ... import jregex
from ...rules.abstract_rules import _rules_file
from ...rules.base import RuleMatch
from ...rules.core import Categories, CoreRule
from ...tools import java_split, java_trim

_c = jregex.compile
PREPOSICAO_DE = _c('de|d[a|o]s?')
ARTIGO_O_MS = _c('o|O')
ARTIGO_O_FS = _c('a|A')
ARTIGO_O_MP = _c('as|As')
ARTIGO_O_FP = _c('os|Os')
DETERMINANTE = _c('D[^R].*')
DETERMINANTE_MS = _c('D[^R].[MC][SN].*')
DETERMINANTE_FS = _c('D[^R].[FC][SN].*')
DETERMINANTE_MP = _c('D[^R].[MC][PN].*')
DETERMINANTE_FP = _c('D[^R].[FC][PN].*')
NOME_MS = _c('NC[MC][SN].*')
NOME_FS = _c('NC[FC][SN].*')
NOME_MP = _c('NC[MC][PN].*')
NOME_FP = _c('NC[FC][PN].*')
ADJETIVO_MS = _c('A..[MC][SN].*|V.P..SM.?|PX.MS.*')
ADJETIVO_FS = _c('A..[FC][SN].*|V.P..SF.?|PX.FS.*')
ADJETIVO_MP = _c('A..[MC][PN].*|V.P..PM.?|PX.MP.*')
ADJETIVO_FP = _c('A..[FC][PN].*|V.P..PF.?|PX.FP.*')
INFINITIVO = _c('V.N.*')
VERBO_CONJUGADO = _c('V.[^NGP].*|_GV_')
PARTICIPIO_MS = _c('V.P.*SM.?')
GRUPO_VERBAL = _c('_GV_')
VERBO_3S = _c('V...3S..?')
NOT_IN_PREV_TOKEN = _c('V..*|PP.*|P0.*|V.P.*')
BEFORE_ADJECTIVE_MS = _c('SPS00|D[^R].[MC][SN].*|V.[^NGP].*|PX.*')
BEFORE_ADJECTIVE_FS = _c('SPS00|D[^R].[FC][SN].*|V.[^NGP].*|PX.*')
BEFORE_ADJECTIVE_MP = _c('SPS00|D[^R].[MC][PN].*|V.[^NGP].*|PX.*')
BEFORE_ADJECTIVE_FP = _c('SPS00|D[^R].[FC][PN].*|V.[^NGP].*|PX.*')
GN = _c('.*_GN_.*|<?/?N[CP].*')
EXCEPCOES_ANTES_DE = _c('forma|manera|por|costat', jregex.IGNORECASE)
# TODO Confirmar a exclusão de: PP3..A00 (coincidee COM articles determinats) se aplica ao português
PRONOME_PESSOAL = _c('P0.{6}|PP3CN000|PP3NN000|PP3CP000|PP3CSD00')

_data = {}
_data_lock = threading.Lock()


def load_accentuation_words(path):
    """PortugueseAccentuationDataLoader.loadWords: form -> (token, POS tag),
    the single reading of the AnalyzedTokenReadings in Java (a later line
    for the same form replaces the earlier one)"""
    m = {}
    with open(path, encoding='utf-8') as f:
        for raw in f.read().splitlines():
            line = java_trim(raw)
            if not line or line[0] == '#':  # ignore comments
                continue
            parts = java_split(line, ';')
            if len(parts) != 3:
                raise RuntimeError('Format error in file ' + path + ', line: ' + line + ', '
                                   + 'expected 3 semicolon-separated parts, got ' + str(len(parts)))
            m[parts[0]] = (parts[1], parts[2])
    return m


def _relevant_words(language, name):
    with _data_lock:
        m = _data.get(name)
        if m is None:
            m = _data[name] = load_accentuation_words(_rules_file(language, name))
        return m


def _match_postag_regexp(atr, pattern):
    """Match the POS tags of the readings with a regular expression"""
    for reading in atr.readings:
        pos_tag = reading.pos_tag
        if pos_tag is not None and pattern.fullmatch(pos_tag):
            return True
    return False


def _match_word_tag(word, pattern):
    """matchPostagRegexp for the reading of an entry of the data files"""
    return word[1] is not None and pattern.fullmatch(word[1]) is not None


class PortugueseAccentuationCheckRule(CoreRule):
    """Port of org.languagetool.rules.pt.PortugueseAccentuationCheckRule:
    verb forms without accent that should be nouns
    (/pt/verbos_sem_acento_nomes_com_acento.txt) or adjectives
    (/pt/verbos_sem_acento_adj_com_acento.txt) with accent, recognized by
    their context. Default off (a basic adaptation without exceptions)."""

    issue_type = 'Misspelling'

    def __init__(self, messages, language=None):
        super().__init__(messages, language)
        self.category = Categories.get('CONFUSED_WORDS', messages)
        # FIXME This rule is a basic adaptation that has no exceptions added. Users may test the rule and give the
        # required feedback so that the rule can be on by default
        self.set_default_off()

    def get_id(self):
        return 'ACCENTUATION_CHECK_PT'

    def get_description(self):
        return 'Confusão com acentos gráficos'

    def match(self, sentence):
        relevant_words = _relevant_words(self.language, '/pt/verbos_sem_acento_nomes_com_acento.txt')
        relevant_words2 = _relevant_words(self.language, '/pt/verbos_sem_acento_adj_com_acento.txt')
        rule_matches = []
        tokens = sentence.non_blank_tokens
        n = len(tokens)
        mp = _match_postag_regexp
        mw = _match_word_tag
        for i in range(1, n):
            # ignoring token 0, i.e. SENT_START
            if i == 1:
                token = tokens[i].token.lower()
            else:
                token = tokens[i].token
            prev_token = tokens[i - 1].token
            prev_prev_token = tokens[i - 2].token if i > 2 else ''
            next_token = tokens[i + 1].token if i < n - 1 else ''
            next_next_token = tokens[i + 2].token if i < n - 2 else ''
            if not token:
                continue
            is_relevant_word = token in relevant_words
            is_relevant_word2 = token in relevant_words2
            if not is_relevant_word and not is_relevant_word2:
                continue
            # verbo precedido de pronome reflexo
            if mp(tokens[i - 1], PRONOME_PESSOAL) and not prev_token.startswith('-'):
                continue
            replacement = None
            m_preposicao_de = PREPOSICAO_DE.fullmatch(next_token) is not None
            m_excepcoes_de = EXCEPCOES_ANTES_DE.fullmatch(next_next_token) is not None
            m_artigo_o_ms = ARTIGO_O_MS.fullmatch(prev_token) is not None
            m_artigo_o_fs = ARTIGO_O_FS.fullmatch(prev_token) is not None
            m_artigo_o_mp = ARTIGO_O_MP.fullmatch(prev_token) is not None
            m_artigo_o_fp = ARTIGO_O_FP.fullmatch(prev_token) is not None

            # VERB WITHOUT ACCENT -> NOUN WITH ACCENT
            if is_relevant_word and not mp(tokens[i], GN):
                w = relevant_words[token]
                if (tokens[i - 1].has_pos_tag('SPS00') and not tokens[i - 1].has_pos_tag('RG')
                        and not mp(tokens[i - 1], DETERMINANTE) and not mp(tokens[i], INFINITIVO)):
                    # amb renuncies
                    replacement = w[0]
                elif ((mp(tokens[i - 1], DETERMINANTE_MS) and mw(w, NOME_MS))
                      or (mp(tokens[i - 1], DETERMINANTE_MP) and mw(w, NOME_MP))
                      or (mp(tokens[i - 1], DETERMINANTE_FS) and mw(w, NOME_FS))
                      or (mp(tokens[i - 1], DETERMINANTE_FP) and mw(w, NOME_FP))):
                    # aquestes renuncies
                    replacement = w[0]
                elif (i > 2 and mp(tokens[i - 2], VERBO_CONJUGADO)
                      and ((mp(tokens[i - 1], DETERMINANTE_MS) and mw(w, NOME_MS))
                           or (mp(tokens[i - 1], DETERMINANTE_MP) and mw(w, NOME_MP))
                           or (mp(tokens[i - 1], DETERMINANTE_FS) and mw(w, NOME_FS))
                           or (mp(tokens[i - 1], DETERMINANTE_FP) and mw(w, NOME_FP)))):
                    # fumaré una faria (correct: fària)
                    replacement = w[0]
                elif (i > 2 and mp(tokens[i - 2], VERBO_CONJUGADO)
                      and ((m_artigo_o_ms and mw(w, NOME_MS))
                           or (m_artigo_o_mp and mw(w, NOME_MP))
                           or (m_artigo_o_fs and mw(w, NOME_FS))
                           or (m_artigo_o_fp and mw(w, NOME_FP)))):
                    # fem la copia (correct: còpia)
                    replacement = w[0]
                elif (not mp(tokens[i], PARTICIPIO_MS)
                      and not mp(tokens[i - 1], NOT_IN_PREV_TOKEN)
                      and i < n - 2
                      and not mp(tokens[i + 2], INFINITIVO)
                      and not m_excepcoes_de
                      and not tokens[i - 1].has_pos_tag('RG')):
                    # circumstancies d'una altra classe
                    replacement = w[0]
                elif (((m_artigo_o_ms and mw(w, NOME_MS))
                       or (m_artigo_o_fs and mw(w, NOME_FS))
                       or (m_artigo_o_mp and mw(w, NOME_MP))
                       or (m_artigo_o_fp and mw(w, NOME_FP)))
                      and m_preposicao_de):
                    # la renuncia del president.
                    replacement = w[0]
                elif (i < n - 1
                      and ((mw(w, NOME_MS) and mp(tokens[i + 1], ADJETIVO_MS))
                           or (mw(w, NOME_FS) and mp(tokens[i + 1], ADJETIVO_FS))
                           or (mw(w, NOME_MP) and mp(tokens[i + 1], ADJETIVO_MP))
                           or (mw(w, NOME_FP) and mp(tokens[i + 1], ADJETIVO_FP)))):
                    # circunstancias extraordináries
                    replacement = w[0]
                elif ((mw(w, NOME_MS) and mp(tokens[i - 1], ADJETIVO_MS)
                       and not mp(tokens[i], VERBO_3S) and not mp(tokens[i], GRUPO_VERBAL))
                      or (mw(w, NOME_FS) and mp(tokens[i - 1], ADJETIVO_FS) and not mp(tokens[i], VERBO_3S))
                      or (mw(w, NOME_MP) and mp(tokens[i - 1], ADJETIVO_MP))
                      or (mw(w, NOME_FP) and mp(tokens[i - 1], ADJETIVO_FP))):
                    # les seves contraries
                    replacement = w[0]
                elif (next_token == 'que' and i > 2
                      and ((mw(w, NOME_MS) and mp(tokens[i - 1], ADJETIVO_MS) and mp(tokens[i - 2], DETERMINANTE_MS))
                           or (mw(w, NOME_FS) and mp(tokens[i - 1], ADJETIVO_FS)
                               and mp(tokens[i - 2], DETERMINANTE_FS))
                           or (mw(w, NOME_MP) and mp(tokens[i - 1], ADJETIVO_MP)
                               and mp(tokens[i - 2], DETERMINANTE_MP))
                           or (mw(w, NOME_FP) and mp(tokens[i - 1], ADJETIVO_FP)
                               and mp(tokens[i - 2], DETERMINANTE_FP)))):
                    # uma nova formula que (fórmula)
                    replacement = w[0]
                elif (next_token == 'que'
                      and ((m_artigo_o_ms and mw(w, NOME_MS))
                           or (m_artigo_o_fs and mw(w, NOME_FS))
                           or (m_artigo_o_mp and mw(w, NOME_MP))
                           or (m_artigo_o_fp and mw(w, NOME_FP)))):
                    # les circumstancies que ens envolten
                    replacement = w[0]
                # de positiva influencia
                if (i > 2 and tokens[i - 2].has_pos_tag('SPS00') and not tokens[i - 2].has_pos_tag('RG')
                        and ((mw(w, NOME_MS) and mp(tokens[i - 1], ADJETIVO_MS))
                             or (mw(w, NOME_FS) and mp(tokens[i - 1], ADJETIVO_FS))
                             or (mw(w, NOME_MP) and mp(tokens[i - 1], ADJETIVO_MP))
                             or (mw(w, NOME_FP) and mp(tokens[i - 1], ADJETIVO_FP)))):
                    replacement = w[0]

            # VERB WITHOUT ACCENT -> ADJECTIVE WITH ACCENT
            if is_relevant_word2 and not mp(tokens[i], GN):
                w = relevant_words2[token]
                if ((mw(w, ADJETIVO_MS) and mp(tokens[i - 1], NOME_MS) and not tokens[i - 1].has_pos_tag('_GN_FS')
                     and mp(tokens[i], VERBO_CONJUGADO) and not mp(tokens[i], VERBO_3S))
                        or (mw(w, ADJETIVO_FS) and prev_prev_token.lower() == 'de'
                            and prev_token in ('maneira', 'forma'))
                        or (mw(w, ADJETIVO_MP) and mp(tokens[i - 1], NOME_MP))
                        or (mw(w, ADJETIVO_FP) and mp(tokens[i - 1], NOME_FP))):
                    # de maneira obvia, circumstancias extraordinarias.
                    replacement = w[0]
                elif (i < n - 1 and prev_token != 'que' and not mp(tokens[i - 1], NOT_IN_PREV_TOKEN)
                      and ((mw(w, ADJETIVO_MS) and mp(tokens[i + 1], NOME_MS)
                            and mp(tokens[i - 1], BEFORE_ADJECTIVE_MS))
                           or (mw(w, ADJETIVO_FS) and mp(tokens[i + 1], NOME_FS)
                               and mp(tokens[i - 1], BEFORE_ADJECTIVE_FS))
                           or (mw(w, ADJETIVO_MP) and mp(tokens[i + 1], NOME_MP)
                               and mp(tokens[i - 1], BEFORE_ADJECTIVE_MP))
                           or (mw(w, ADJETIVO_FP) and mp(tokens[i + 1], NOME_FP)
                               and mp(tokens[i - 1], BEFORE_ADJECTIVE_FP)))):
                    # de continua disputa
                    replacement = w[0]
                elif (i < n - 1
                      and ((mw(w, ADJETIVO_MS) and mp(tokens[i + 1], NOME_MS) and m_artigo_o_ms)
                           or (mw(w, ADJETIVO_FS) and mp(tokens[i + 1], NOME_FS) and m_artigo_o_fs)
                           or (mw(w, ADJETIVO_MP) and mp(tokens[i + 1], NOME_MP) and m_artigo_o_mp)
                           or (mw(w, ADJETIVO_FP) and mp(tokens[i + 1], NOME_FP) and m_artigo_o_fp))):
                    # a magnifica conservação
                    replacement = w[0]
            if replacement is not None:
                msg = 'Se é um nome ou um adjectivo, tem acento.'
                rule_match = RuleMatch(self, sentence, tokens[i].start_pos, tokens[i].end_pos, msg,
                                       'Falta um acento')
                rule_match.set_suggested_replacement(replacement)
                rule_matches.append(rule_match)
        return rule_matches
