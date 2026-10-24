"""The code of org.languagetool.language.Catalan that is not declarative
(see the 'ca' entry of langtool.languages): toAdvancedTypography(),
adaptSuggestion(), filterRuleMatches() (with adjustCatalanMatch) and
filterRuleMatchesAfterOverlapping()."""

from ... import jregex
from ...rules.base import RuleMatch
from ...tools import is_capitalized_word, java_equals_ignore_case, preserve_case, uppercase_first_char

_PATTERN_1 = jregex.compile("(\\b[lmnstdLMNSTD])'")
_PATTERN_2 = jregex.compile('(\\b[lmnstdLMNSTD])’"')
_PATTERN_3 = jregex.compile("(\\b[lmnstdLMNSTD])’'")


def to_advanced_typography(language, text):
    """Catalan.toAdvancedTypography: Language.toAdvancedTypography, then
    the special cases of apostrophe + quotation marks"""
    output = language.base_to_advanced_typography(text)
    # special cases: apostrophe + quotation marks
    output = jregex.java_replace(_PATTERN_1, '$1’', output)
    output = jregex.java_replace(_PATTERN_2, '$1’' + language.get_opening_double_quote(), output)
    output = jregex.java_replace(_PATTERN_3, '$1’' + language.get_opening_single_quote(), output)
    return output


_CI = jregex.IGNORECASE
_UC = jregex.UNICODE_CHARACTER_CLASS
_CA_OLD_DIACRITICS = jregex.compile('.*\\b(sóc|dóna|dónes|vénen|véns|fóra|adéu|féu|desféu|vés|contrapèl)\\b.*', _CI)
_CA_CONTRACTIONS = jregex.compile('\\b([Aa]|[DdPp]e)r? e(ls?)\\b', _UC)
_CA_CONTRACTIONS2 = jregex.compile("\\b([Dd])[' ]+(els?)\\b", _UC)
_CA_APOSTROPHES1 = jregex.compile("\\b([LDNSTMldnstm]['’]) ", _UC)
# exceptions: l'FBI, l'statu quo
_CA_APOSTROPHES2 = jregex.compile("\\b([mtlsn])['’]([^1haeiouáàèéíòóúA-ZÀÈÉÍÒÓÚ“«\"])", _UC)
# exceptions: el iogurt, la essa
_CA_APOSTROPHES3 = jregex.compile('\\be?([mtsldn])e? (h[aeio]|h?[aeiouàèéíòóú][a-zàèéíòóúïüç])', _CI | _UC)
_CA_APOSTROPHES4 = jregex.compile('\\b(l)a ([aeoàúèéí][^ ])', _CI | _UC)
_CA_APOSTROPHES5 = jregex.compile("\\b([mts]e) (['’])", _CI | _UC)
_CA_APOSTROPHES6 = jregex.compile("\\bs'e(ns|ls)\\b", _CI | _UC)
_CA_APOSTROPHES7 = jregex.compile('\\b(de|a)l (h?[aeoàúèéí][^ ])', _CI | _UC)
_CA_APOSTROPHES8 = jregex.compile("\\b([MTLSN])['’]([^1haeiouáàèéíòóúA-ZÀÈÉÍÒÓÚ“«\"])", _UC)
_CA_APOSTROPHES9 = jregex.compile("\\b([Dd])['’]([^1haeiouáàèéíòóúA-ZÀÈÉÍÒÓÚ“«\"])", _UC)
# (Java: UNICODE_CASE without CASE_INSENSITIVE)
POSSESSIUS_v = jregex.compile('\\b([mtsMTS]e)v(a|es)\\b', _UC)
POSSESSIUS_V = jregex.compile('\\b([MTS]E)V(A|ES)\\b', _UC)
_CA_REMOVE_SPACES = jregex.compile("\\b(a|de|pe) (ls?)(?!['’])\\b", _CI | _UC)


def adapt_suggestion(language, s, original_error_str):
    """Catalan.adaptSuggestion: contractions (a el -> al, de els -> dels,
    per el -> pel...), apostrophes (el home -> l'home, me ha -> m'ha, l'
    + consonant...), and the case of the original error string"""
    # Exceptions: Digues-me alguna cosa, urbi et orbi, Guns N' Roses
    capitalized = is_capitalized_word(s)
    s = s.replace('gens traça', 'gens de traça')
    s = s.replace('gens facilitat', 'gens de facilitat')
    s = jregex.java_replace(_CA_CONTRACTIONS, '$1$2', s)
    s = jregex.java_replace(_CA_CONTRACTIONS2, '$1$2', s)
    s = jregex.java_replace(_CA_APOSTROPHES1, '$1', s)
    s = jregex.java_replace(_CA_APOSTROPHES2, 'e$1 $2', s)
    if 'en el' not in s and '-se' not in s:
        s = jregex.java_replace(_CA_APOSTROPHES3, "$1'$2", s)
    s = jregex.java_replace(_CA_APOSTROPHES4, "$1'$2", s)
    s = jregex.java_replace(_CA_APOSTROPHES5, '$1$2', s)
    s = jregex.java_replace(_CA_APOSTROPHES6, "se'$1", s)
    s = jregex.java_replace(_CA_APOSTROPHES7, "$1 l'$2", s)
    # T'comença -> Et comença
    s = _CA_APOSTROPHES8.sub(lambda m: 'E' + m.group(1).lower() + ' ' + m.group(2), s)
    s = jregex.java_replace(_CA_APOSTROPHES9, '$1e $2', s)
    s = jregex.java_replace(_CA_REMOVE_SPACES, '$1$2', s)
    if capitalized:
        s = uppercase_first_char(s)
    s = s.replace(' ,', ',')
    return preserve_case(s, original_error_str)


def _remove_old_diacritics(s):
    return (s.replace('contrapèl', 'contrapel').replace('Contrapèl', 'Contrapel').replace('vés', 'ves')
            .replace('féu', 'feu').replace('desféu', 'desfeu').replace('adéu', 'adeu').replace('dóna', 'dona')
            .replace('dónes', 'dones').replace('sóc', 'soc').replace('vénen', 'venen').replace('véns', 'vens')
            .replace('fóra', 'fora').replace('Vés', 'Ves').replace('Féu', 'Feu').replace('Desféu', 'Desfeu')
            .replace('Adéu', 'Adeu').replace('Dóna', 'Dona').replace('Dónes', 'Dones').replace('Sóc', 'Soc')
            .replace('Vénen', 'Venen').replace('Véns', 'Vens').replace('Fóra', 'Fora'))


def _adjust_catalan_match(rule_match, enabled_rules):
    """Catalan.adjustCatalanMatch"""
    error_str = rule_match.original_error_str
    suggested_replacements = rule_match.suggested_replacements
    # Avoid two white spaces after removing a word
    if len(suggested_replacements) == 1 and not suggested_replacements[0]:
        sentence_text = rule_match.sentence.text
        from_sent = rule_match.get_from_pos_sentence()
        to_sent = rule_match.get_to_pos_sentence()
        if (from_sent >= 0 and to_sent + 1 <= len(sentence_text)
                and (from_sent == 0 or sentence_text[from_sent - 1] == ' ') and sentence_text[to_sent] == ' '):
            new_rule_match = RuleMatch(rule_match.rule, rule_match.sentence, rule_match.from_pos,
                                       rule_match.to_pos + 1, rule_match.message, rule_match.short_message)
            new_rule_match.set_sentence_position(from_sent, to_sent + 1)
            new_rule_match.set_suggested_replacement('')
            return new_rule_match
    has_typographic_apostrophe = any(x.typographic_apostrophe
                                     for x in rule_match.sentence.get_tokens_without_whitespace())
    new_replacements = []
    for suggested_replacement in rule_match.suggested_replacement_objects:
        new_repl_str = suggested_replacement.replacement
        if len(error_str) > 2 and error_str.endswith("'") and not new_repl_str.endswith("'") \
                and not new_repl_str.endswith('’'):
            new_repl_str = new_repl_str + ' '
        if not java_equals_ignore_case(new_repl_str, 'després') and 'EXIGEIX_ACCENTUACIO_GENERAL' in enabled_rules:
            if 'é' in new_repl_str and new_repl_str.replace('é', 'è') in suggested_replacements:
                continue
            if 'É' in new_repl_str and new_repl_str.replace('É', 'È') in suggested_replacements:
                continue
        elif 'EXIGEIX_ACCENTUACIO_VALENCIANA' in enabled_rules:
            if 'è' in new_repl_str and new_repl_str.replace('è', 'é') in suggested_replacements:
                continue
            if 'È' in new_repl_str and new_repl_str.replace('È', 'É') in suggested_replacements:
                continue
        if (('APOSTROF_TIPOGRAFIC' in enabled_rules or has_typographic_apostrophe) and len(new_repl_str) > 1
                and 'APOSTROF_RECTE' not in enabled_rules):
            new_repl_str = new_repl_str.replace("'", '’')
        if 'EXIGEIX_POSSESSIUS_U' in enabled_rules and len(new_repl_str) > 3:
            new_repl_str = jregex.java_replace(POSSESSIUS_v, '$1u$2', new_repl_str)
            new_repl_str = jregex.java_replace(POSSESSIUS_V, '$1U$2', new_repl_str)
            new_repl_str = new_repl_str.replace('feina', 'faena')
            new_repl_str = new_repl_str.replace('feiner', 'faener')
            new_repl_str = new_repl_str.replace('feinera', 'faenera')
        if 'DIACRITICS_TRADITIONAL_RULES' not in enabled_rules and _CA_OLD_DIACRITICS.fullmatch(new_repl_str):
            new_suggested_replacement = suggested_replacement.copy(_remove_old_diacritics(new_repl_str))
        else:
            new_suggested_replacement = suggested_replacement.copy(new_repl_str)
        # (SuggestedReplacement.equals compares the replacement and the short description)
        if not any(r.replacement == new_suggested_replacement.replacement
                   and r.short_description == new_suggested_replacement.short_description for r in new_replacements):
            new_replacements.append(new_suggested_replacement)
    new_match = rule_match.copy()
    new_match.set_suggested_replacement_objects(new_replacements)
    return new_match


def filter_rule_matches(language, rule_matches, annotated_text, enabled_rules):
    """Catalan.filterRuleMatches: matches that change nothing are removed
    (except for the speller rule); IGNORE_PROPER_NOUNS and
    MORFOLOGIK_RULE_CA_ES matches at the same position cancel each other;
    FALTA_ELEMENT_ENTRE_VERBS[3], [4] and [5] are removed in some contexts;
    the other matches are adjusted (adjustCatalanMatch)."""
    if enabled_rules is None:
        enabled_rules = set()
    results = []
    ignore_match_in_pos = -1
    previous_rule_match = None
    n = len(rule_matches)
    for i in range(n):
        rule_match = rule_matches[i]
        rule_id = rule_match.rule.get_id()
        full_id = rule_match.rule.get_full_id()
        # ignore rules that change nothing
        if rule_id != 'MORFOLOGIK_RULE_CA_ES':
            suggestions = rule_match.suggested_replacements
            if len(suggestions) == 1 and rule_match.original_error_str == suggestions[0]:
                continue
        # remove rules IGNORE_PROPER_NOUNS and MORFOLOGIK_RULE_CA_ES if they are in the same position
        if rule_id == 'IGNORE_PROPER_NOUNS':
            if (previous_rule_match is not None and previous_rule_match.rule.get_id() == 'MORFOLOGIK_RULE_CA_ES'
                    and rule_match.from_pos == previous_rule_match.from_pos):
                results.pop()
                ignore_match_in_pos = -1
                continue
            ignore_match_in_pos = rule_match.from_pos
            continue
        if rule_id == 'MORFOLOGIK_RULE_CA_ES' and rule_match.from_pos == ignore_match_in_pos:
            ignore_match_in_pos = -1
            continue
        if full_id in ('FALTA_ELEMENT_ENTRE_VERBS[3]', 'FALTA_ELEMENT_ENTRE_VERBS[4]'):
            if i + 1 < n:
                following = rule_matches[i + 1]
                if (following.get_from_pos_sentence() > -1
                        and following.rule.get_full_id() != 'FALTA_ELEMENT_ENTRE_VERBS[5]'
                        and following.get_from_pos_sentence() - rule_match.get_to_pos_sentence() < 20):
                    continue
        if (i > 0 and full_id == 'FALTA_ELEMENT_ENTRE_VERBS[5]'
                and rule_matches[i - 1].rule.get_id() == 'FALTA_ELEMENT_ENTRE_VERBS'):
            continue
        results.append(_adjust_catalan_match(rule_match, enabled_rules))
        previous_rule_match = rule_match
    # (Collections.sort: stable, by the start position)
    results.sort(key=lambda m: m.from_pos)
    return results


def filter_rule_matches_after_overlapping(language, rule_matches):
    """Catalan.filterRuleMatchesAfterOverlapping: trimMatchEnds for every
    match, sorted"""
    return sorted((m.trim_match_ends() for m in rule_matches), key=lambda m: m.from_pos)
