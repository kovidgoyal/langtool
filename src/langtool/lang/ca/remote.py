"""Ports of org.languagetool.rules.ca.CatalanRemoteRewriteHelper,
CatalanRemoteRewriteFilter and CatalanSplitLongSentenceRule: suggestions
from an external rewriting service (an LLM server configured with the
environment variables CA_REMOTE_REWRITE_SERVER, CA_REMOTE_REWRITE_API_KEY,
CA_REMOTE_REWRITE_PROVIDER, CA_REMOTE_REWRITE_MODEL and
CA_REMOTE_REWRITE_TIME_OUT, as in Java). Without a configured server only
the cached responses "for testing" of the helper are used (they make the
examples of the rules with CatalanRemoteRewriteFilter pass, as in Java)."""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

from ... import jregex
from ...diffs import DiffsAsMatches
from ...rules.abstract_rules import _config_values
from ...rules.base import RuleMatch
from ...rules.core import LongSentenceRule
from ...rules.filters import RuleFilter

_SERVER_URL = os.environ.get('CA_REMOTE_REWRITE_SERVER')
_API_KEY = os.environ.get('CA_REMOTE_REWRITE_API_KEY')
_PROVIDER = os.environ.get('CA_REMOTE_REWRITE_PROVIDER')
_MODEL = os.environ.get('CA_REMOTE_REWRITE_MODEL')


def _timeout_ms():
    val = os.environ.get('CA_REMOTE_REWRITE_TIME_OUT')
    try:
        return int(val) if val is not None else 5000
    except ValueError:
        return 5000


_TIMEOUT_MS = _timeout_ms()
_MAX_SENTENCE_CHARS = 1200
_CACHE_MAX_SIZE = 1000
_CACHE_EXPIRE_SECONDS = 3600

# StringTools.TRIM_PATTERN
_TRIM_PATTERN = jregex.compile('^[\\s\\u00A0]+|[\\s\\u00A0]+$')


def trim_leading_and_trailing_spaces(s):
    """StringTools.trimLeadingAndTrailingSpaces"""
    return jregex.java_replace(_TRIM_PATTERN, '', s)


PROMPTS = {
    'GERUNDI_POSTERIORITAT':
        'Reescriu les frases sense el gerundi de posterioritat. Respon directament amb la frase, sense comentaris '
        'ni puntuació extra.',
    'CA_SPLIT_LONG_SENTENCE':
        'Aquesta frase és massa llarga. Divideix-la fent els mínims canvis possibles. Respon només amb la frase '
        'dividida.',
    'EN_NO_INFINITIU_CAUSAL_REMOTE':
        "Reescriu la frase canviant la construcció 'al no + infinitiu' o 'en no + infinitiu' per 'com que...' o "
        "'perquè...', fent els mínims canvis possibles. Respon amb la frase reescrita sense comentaris extra.",
    'CA_REMOTE_ESCOLTAR_SENTIR':
        "Reescriu aquesta frase canviant el verb 'escoltar' pel verb 'sentir', si està mal usat, és a dir, si no "
        "vol dir 'parar atenció, atendre o obeir'.No canviïs el verb si 'escoltar' vol dir 'parar atenció, atendre "
        "o obeir', i per tant està ben usat (p. ex., El vaig escoltar atentament).Respon directament amb la frase "
        'reescrita, sense comentaris ni puntuació extra.',
}

# For testing
CACHED_RESPONSES = {
    'GERUNDI_POSTERIORITAT': {
        'El lladre va atracar dues joieries, escapant-se més tard amb un cotxe robat.':
            '>El lladre va atracar dues joieries i després va escapar-se amb un cotxe robat.',
        'El lladre va atracar dues joieries, fugint després amb un cotxe robat.':
            '. El lladre va atracar dues joieries i després va fugir amb un cotxe robat.',
        'El lladre va atracar dues joieries, essent assassinat pocs dies després.':
            'El lladre va atracar dues joieries i va ser assassinat pocs dies després.',
        'El lladre va atracar dues joieries, fugint al cap de poc amb un cotxe robat.':
            'El lladre va atracar dues joieries i al cap de poc va fugir amb un cotxe robat.',
        "El lladre va atracar dues joieries, escapant-se al cap d'una estona amb un cotxe robat.":
            'El lladre va atracar dues joieries i després es va escapar amb un cotxe robat.',
        "Es van presentar els estatuts, aprovant-se l'endemà mateix.":
            "Es van presentar els estatuts i es van aprovar l'endemà mateix.",
        "Es van presentar els estatuts, sent aprovats l'endemà mateix.":
            "Es van presentar els estatuts i van ser aprovats l'endemà mateix.",
        'Es van presentar els estatuts, sent aprovats al cap de poc.':
            'Es van presentar els estatuts i al cap de poc van ser aprovats.',
        'Es van presentar diverses esmenes, sent aprovades per una àmplia majoria.':
            'Es van presentar diverses esmenes, i van ser aprovades per una àmplia majoria.',
        'Es presentaren diverses esmenes, sent aprovades per una àmplia majoria.':
            'Es presentaren diverses esmenes, i foren aprovades per una àmplia majoria.',
        "Hi hagué un accident greu a l'autopista entre un camió i un turisme, morint al cap de poc els passatgers "
        'del turisme.':
            "Hi hagué un accident greu a l'autopista entre un camió i un turisme, i els passatgers del turisme van "
            'morir al cap de poc.',
        "Hi hagué un accident greu a l'autopista entre un camió i un turisme, morint els passatgers del turisme al "
        'cap de poc.':
            "Hi hagué un accident greu a l'autopista entre un camió i un turisme i els passatgers del turisme van "
            'morir al cap de poc.',
        "Va arribar tard a l'examen, perdent així després tota oportunitat d'aprovar l'assignatura.":
            "Va arribar tard a l'examen i, per això, va perdre tota oportunitat d'aprovar l'assignatura.",
        'Van anul·lar la reunió, convocant-la per a la setmana següent.':
            'Van anul·lar la reunió i la van convocar per a la setmana següent.',
        'Van anul·lar la reunió, convocant-la per a la propera setmana.':
            'Van anul·lar la reunió i la van convocar per a la propera setmana.',
    },
    'CA_SPLIT_LONG_SENTENCE': {
        'En una tarda grisa que avançava sense pressa sobre els carrers estrets de la ciutat, mentre els comerços '
        'abaixaven persianes i el soroll del trànsit es diluïa en un murmuri constant, un home caminava pensant en '
        'decisions ajornades, en paraules no dites i en projectes que havia volgut compondre amb rigor, però que '
        'el cansament havia anat desfigurant i, així i tot, convençut que encara disposava de prou lucidesa per a '
        "ordenar les idees, assumir els errors, fer servir l'experiència acumulada com a criteri i continuar "
        'avançant amb una determinació menys impulsiva però més sòlida.':
            'En una tarda grisa que avançava sense pressa sobre els carrers estrets de la ciutat, mentre els '
            'comerços abaixaven persianes i el soroll del trànsit es diluïa en un murmuri constant, un home '
            'caminava pensant en decisions ajornades, en paraules no dites i en projectes que havia volgut '
            'compondre amb rigor, però que el cansament havia anat desfigurant. I, així i tot, convençut que '
            'encara disposava de prou lucidesa per a ordenar les idees, assumir els errors, fer servir '
            "l'experiència acumulada com a criteri i continuar avançant amb una determinació menys impulsiva però "
            'més sòlida.',
    },
    'CA_REMOTE_ESCOLTAR_SENTIR': {
        'Vaig escoltar que deien coses inversemblants.':
            'Vaig sentir que deien coses inversemblants.',
        'Vaig escoltar atentament les seves explicacions.':
            'Vaig escoltar atentament les seves explicacions.',
    },
    'EN_NO_INFINITIU_CAUSAL_REMOTE': {
        'En no poder venir, vam decidir deixar-ho córrer.':
            'Com que no podíem venir, vam decidir deixar-ho córrer.',
        'Al no poder venir, vam decidir deixar-ho córrer.':
            'Com que no podíem venir, vam decidir deixar-ho córrer.',
        'En no tenir efectes pràctics, vam decidir deixar-ho córrer.':
            'Com que no tenia efectes pràctics, vam decidir deixar-ho córrer.',
        "Al no venir fonamentades, tothom s'estranya.":
            "Com que no venen fonamentades, tothom s'estranya.",
        "Ho vaig deixar córrer al no disposar d'informació.":
            "Ho vaig deixar córrer perquè no disposava d'informació.",
        'En no haver descobert el resultat, vam quedar decebuts.':
            'Com que no havíem descobert el resultat, vam quedar decebuts.',
    },
}

# the cache of the responses of the server (Guava cache: maximum size 1000, entries expire after an hour)
_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry[1] > _CACHE_EXPIRE_SECONDS:
            del _cache[key]
            return None
        return entry[0]


def _cache_put(key, value):
    with _cache_lock:
        if key not in _cache and len(_cache) >= _CACHE_MAX_SIZE:
            del _cache[next(iter(_cache))]
        _cache[key] = (value, time.monotonic())


def is_remote_service_available():
    """CatalanRemoteRewriteHelper.isRemoteServiceAvailable"""
    return bool(_SERVER_URL)


def send_post_request(sentence, rule_id):
    """CatalanRemoteRewriteHelper.sendPostRequest: the sentence rewritten
    for the rule by the remote service (a cached response for testing,
    otherwise a request to the server if one is configured), "" if there
    is none"""
    if sentence is None:
        return ''
    trim_sentence = trim_leading_and_trailing_spaces(sentence)
    if not trim_sentence:
        return ''
    responses_map = CACHED_RESPONSES.get(rule_id)
    if responses_map is not None:
        corrected_sentence = responses_map.get(trim_sentence, '')
        if corrected_sentence:
            return corrected_sentence
    if not is_remote_service_available():
        return ''
    # ignorem frases molt llargues, no tractem d'arreglar-les
    if len(sentence) > _MAX_SENTENCE_CHARS:
        return ''
    cache_key = rule_id + '|' + trim_sentence
    cached_val = _cache_get(cache_key)
    if cached_val is not None:
        return cached_val
    print('Requesting server ' + _SERVER_URL + ' for rule ' + rule_id)
    try:
        provider = (_PROVIDER or '').lower()
        if provider == 'openai':
            payload = {}
            messages = [{'role': 'system', 'content': PROMPTS.get(rule_id)}, {'role': 'user', 'content': sentence}]
            if _MODEL:
                payload['model'] = _MODEL
            payload['messages'] = messages
            payload['temperature'] = 0.0
        elif provider == 'google':
            payload = {
                'systemInstruction': {'parts': [{'text': PROMPTS.get(rule_id)}]},
                'contents': [{'parts': [{'text': sentence}], 'role': 'user'}],
                'generationConfig': {'temperature': 0.0},
            }
        else:
            payload = {'system_prompt': PROMPTS.get(rule_id), 'user_prompt': sentence, 'temperature': 0.0}
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json; charset=UTF-8', 'Accept': 'application/json'}
        if _API_KEY:
            headers['Authorization'] = 'Bearer ' + _API_KEY
        request = urllib.request.Request(_SERVER_URL, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_MS / 1000.0) as conn:
                code = conn.status
                response = conn.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            code = e.code
            response = e.read().decode('utf-8') if e.fp is not None else ''
        # (BufferedReader.readLine: the lines are joined without line breaks)
        response = ''.join(response.splitlines())
        if code == 200:
            json_response = json.loads(response)
            if provider == 'openai':
                result = json_response['choices'][0]['message']['content'].strip()
            elif provider == 'google':
                result = json_response['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                result = json_response['response'].strip()
            if result:
                _cache_put(cache_key, result)
            return result
        print('API error (%d): %s// PAYLOAD: %s' % (code, response, json.dumps(payload, ensure_ascii=False)),
              file=sys.stderr)
        return ''
    except Exception as e:  # noqa: BLE001 -- like the catch (Exception e) in Java
        print('Exception in sendPostRequest: ' + str(e), file=sys.stderr)
        return ''


class CatalanRemoteRewriteFilter(RuleFilter):
    """Port of org.languagetool.rules.ca.CatalanRemoteRewriteFilter: provide
    suggestions from an external service (send_post_request): the
    differences between the sentence and its rewritten version near the
    match (from 2 characters before to 60 after) become the new match.
    Without a rewritten version the match is kept (or discarded with
    suppressMatch:true)."""

    def accept_rule_match(self, match, arguments, pattern_token_pos, pattern_tokens, token_positions):
        original_sentence = trim_leading_and_trailing_spaces(match.sentence.text)
        corrected_sentence = send_post_request(original_sentence, match.rule.get_id())
        b_suppress_match = self.get_optional('suppressMatch', arguments, 'false').lower() == 'true'
        if not corrected_sentence:
            return None if b_suppress_match else match
        diffs_as_matches = DiffsAsMatches()
        pseudo_matches = diffs_as_matches.get_pseudo_matches(original_sentence, corrected_sentence)
        pseudo_match = diffs_as_matches.get_joined_match(pseudo_matches, original_sentence, match.from_pos - 2,
                                                         match.to_pos + 60)
        if pseudo_match is None:
            return None if b_suppress_match else match
        suggestion = pseudo_match.replacements[0]
        underlined = original_sentence[pseudo_match.from_pos:pseudo_match.to_pos]
        if ((pseudo_match.to_pos == len(original_sentence) or pseudo_match.from_pos == 0)
                and not trim_leading_and_trailing_spaces(underlined)):
            return None if b_suppress_match else match
        if trim_leading_and_trailing_spaces(suggestion) == trim_leading_and_trailing_spaces(underlined):
            return None if b_suppress_match else match
        if pseudo_match.to_pos <= pseudo_match.from_pos:
            raise ValueError('fromPos (%d) must be less than toPos (%d). Sentence: %s'
                             % (pseudo_match.from_pos, pseudo_match.to_pos, original_sentence))
        new_rule_match = RuleMatch(match.rule, match.sentence, pseudo_match.from_pos, pseudo_match.to_pos,
                                   match.message, match.short_message)
        new_rule_match.set_suggested_replacements(pseudo_match.replacements)
        return new_rule_match


_LINE_BREAKS = jregex.compile('[\r\n\\s]*[\r\n][\r\n\\s]*')


class CatalanSplitLongSentenceRule(LongSentenceRule):
    """Port of org.languagetool.rules.ca.CatalanSplitLongSentenceRule: for
    the matches of the LongSentenceRule, the sentence divided by the remote
    service (send_post_request); each difference becomes a match (with the
    message "Canvi recomanat." for changes that don't split the sentence).
    Without a divided sentence there are no matches."""

    rule_id = 'CA_SPLIT_LONG_SENTENCE'

    def __init__(self, messages, language=None, user_config=None, max_words=50):
        # (LongSentenceRule: the maximum number of words can be configured for the rule id)
        cf = _config_values(user_config, self.rule_id)
        if cf:
            max_words = int(cf[0])
        super().__init__(messages, language, max_words)

    def match(self, sentences, annotated_text=None):
        original_rule_matches = super().match(sentences, annotated_text)
        result_rule_matches = []
        for rm in original_rule_matches:
            sentence = rm.sentence.text  # the whole sentence, not the selected match
            corrected_sentence = send_post_request(sentence, self.get_id())
            if not corrected_sentence:
                continue
            corrected_sentence = jregex.java_replace(_LINE_BREAKS, ' ', corrected_sentence)
            diffs_as_matches = DiffsAsMatches()
            for pm in diffs_as_matches.get_pseudo_matches(sentence, corrected_sentence):
                message = rm.message
                short_message = rm.short_message
                underlined = sentence[pm.from_pos:pm.to_pos]
                if not underlined.strip(''.join(chr(c) for c in range(33))):
                    continue
                if '.' not in pm.replacement or pm.replacement.endswith('.'):
                    # no és de la divisió de la frase, no sabem què és. Es poden aprofitar si es filtren bé.
                    message = 'Canvi recomanat.'
                    short_message = 'Canvi recomanat'
                rule_match = RuleMatch(rm.rule, rm.sentence, rm.from_pos + pm.from_pos, rm.from_pos + pm.to_pos,
                                       message, short_message)
                rule_match.type = rm.type
                rule_match.set_suggested_replacement(pm.replacements[0])
                result_rule_matches.append(rule_match)
        return result_rule_matches


# the filter classes of this module (registered as org.languagetool.rules.ca.<class name>)
FILTERS = (CatalanRemoteRewriteFilter,)
# rule factories of this module: Java class name -> factory(messages, language, user_config, **kwargs)
RULES = {
    # (Java: new CatalanSplitLongSentenceRule(messages, userConfig, maxWords))
    'CatalanSplitLongSentenceRule': lambda messages, language, user_config, max_words=50: (
        CatalanSplitLongSentenceRule(messages, language, user_config, max_words)),
}
