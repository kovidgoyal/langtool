"""Tests of langtool.lang.ca.remote (CatalanRemoteRewriteHelper,
CatalanSplitLongSentenceRule) with the cached responses "for testing" of
CatalanRemoteRewriteHelper (there are no Java unit tests for these
classes; the rule examples of the rules with CatalanRemoteRewriteFilter
are tested by test_ca_pattern_rules)."""

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.lang.ca.remote import CACHED_RESPONSES, CatalanSplitLongSentenceRule, send_post_request
from langtool.messages import messages_for
from langtool.tool import JLanguageTool


def test_send_post_request_cached():
    sentence = 'En no poder venir, vam decidir deixar-ho córrer.'
    assert send_post_request('  ' + sentence + ' ', 'EN_NO_INFINITIU_CAUSAL_REMOTE') == \
        'Com que no podíem venir, vam decidir deixar-ho córrer.'
    assert send_post_request(sentence, 'GERUNDI_POSTERIORITAT') == ''
    assert send_post_request('   ', 'GERUNDI_POSTERIORITAT') == ''


def test_split_long_sentence_rule():
    require_dictionaries('ca')
    lang = get_language('ca-ES')
    rule = CatalanSplitLongSentenceRule(messages_for('ca'), lang, None, 60)
    assert rule.get_id() == 'CA_SPLIT_LONG_SENTENCE'
    sentence = next(iter(CACHED_RESPONSES['CA_SPLIT_LONG_SENTENCE']))
    matches = rule.match(JLanguageTool(lang).analyze_text(sentence))
    assert len(matches) == 1
    assert sentence[matches[0].from_pos:matches[0].to_pos] == 'desfigurant i'
    assert matches[0].suggested_replacements == ['desfigurant. I']
    # sentences without a cached response (and no server) have no matches
    assert rule.match(JLanguageTool(lang).analyze_text(sentence.replace('grisa', 'blava'))) == []
