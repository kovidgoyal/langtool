"""The code of org.languagetool.language.French that is not declarative
(see the 'fr' entry of langtool.languages): toAdvancedTypography() and
filterRuleMatches() (with adjustFrenchRuleMatch and mergeMatches)."""

from ... import jregex
from ...rules.base import RuleMatch
from ...tools import java_equals_ignore_case

_BEFORE_APOS = ('([cjnmtsldCJNMTSLD]|qu|jusqu|lorsqu|puisqu|quoiqu|Qu|Jusqu|Lorsqu|Puisqu|Quoiqu|QU|JUSQU|LORSQU|'
                'PUISQU|QUOIQU)')
_BEFORE_APOS_PATTERN_1 = jregex.compile('(\\b' + _BEFORE_APOS + ")'")
_BEFORE_APOS_PATTERN_2 = jregex.compile('(\\b' + _BEFORE_APOS + ')’"')
_BEFORE_APOS_PATTERN_3 = jregex.compile('(\\b' + _BEFORE_APOS + ")’'")

# (pattern, replacement) pairs replaced literally, in this order
_TYPOGRAPHY = (
    # non-breaking (thin) space
    # according to https://fr.wikipedia.org/wiki/Espace_ins%C3%A9cable#En_France
    (' ;', ' ;'), (' !', ' !'), (' ?', ' ?'),
    (';', ' ;'), ('!', ' !'), ('?', ' ?'),
    (':', ' :'), ('»', ' »'), ('«', '« '),
    # remove duplicate spaces
    ('  ', ' '), ('  ', ' '), ('  ', ' '), ('  ', ' '),
    ('  ', ' '), ('  ', ' '), ('  ', ' '),
)


def to_advanced_typography(language, text):
    """French.toAdvancedTypography: Language.toAdvancedTypography, then the
    apostrophe before quotation marks and the French (thin) non-breaking
    spaces before ;!?:» and after «"""
    output = language.base_to_advanced_typography(text)
    # special cases: apostrophe + quotation marks
    output = jregex.java_replace(_BEFORE_APOS_PATTERN_1, '$1’', output)
    output = jregex.java_replace(_BEFORE_APOS_PATTERN_2, '$1’' + language.get_opening_double_quote(), output)
    output = jregex.java_replace(_BEFORE_APOS_PATTERN_3, '$1’' + language.get_opening_single_quote(), output)
    for pattern, replacement in _TYPOGRAPHY:
        # (Matcher.replaceAll of a literal pattern)
        output = output.replace(pattern, replacement)
    return output


_TRAILING_WHITESPACE = jregex.compile('\\s+$')


def _category_casing(language):
    from ...messages import messages_for
    from ...rules.core import Categories
    return Categories.get('CASING', messages_for(language.short_code))


def adjust_french_rule_match(language, rm, enabled_rules):
    """French.adjustFrenchRuleMatch: messages, ids, tags and issue types of
    the matches of the AI rules (AI_FR_GGEC_*, remote rules that are not
    ported, so this only concerns matches created by other code); if the
    typographical apostrophe rule (APOS_TYP) is enabled, the suggestions use
    the typographical apostrophe."""
    rm.set_original_error_str()
    error_str = rm.original_error_str
    suggestions = rm.suggested_replacements
    rule_id = rm.rule.get_id()
    if len(suggestions) == 1 and rule_id.startswith('AI_FR_GGEC'):
        suggestion = suggestions[0]
        # the suggestion only changes the casing
        if java_equals_ignore_case(suggestion, error_str):
            rm.message = 'Un usage différent des majuscules et des minuscules est recommandé.'
            rm.short_message = 'Majuscules et minuscules'
            rm.rule.loc_quality_issue_type = 'Typographical'
            rm.rule.category = _category_casing(language)
            rm.specific_rule_id = rule_id.replace('ORTHOGRAPHY', 'CASING')
    if len(suggestions) == 1 and rule_id.startswith('AI_FR_GGEC') and 'MISSING_PRONOUN_LAPOSTROPHE' in rule_id:
        if error_str == 'on' and suggestions[0] == "l'on" and 'si on' in rm.sentence.text.lower():
            rm.specific_rule_id = 'AI_FR_GGEC_SI_LON'
            rm.rule.tags = ['picky']
    if rule_id.startswith('AI_FR_GGEC') and 'REPLACEMENT_PUNCTUATION_QUOTE' in rule_id:
        rm.specific_rule_id = 'AI_FR_GGEC_QUOTES'
        rm.rule.tags = ['picky']
        rm.rule.loc_quality_issue_type = 'Typographical'
    # if the typographical apostrophe rule is enabled, use the typographical apostrophe in suggestons
    if enabled_rules is not None and 'APOS_TYP' in enabled_rules:
        new_replacements = []
        for s in rm.suggested_replacements:
            if len(s) > 1:
                s = s.replace("'", '’')
            new_replacements.append(s)
        rm.set_suggested_replacements(new_replacements)
    return rm


def _merge_matches(match1, match2):
    """French.mergeMatches"""
    # Calculate separator based on position
    separator = ''
    if match1.to_pos + 1 == match2.from_pos:
        separator = ' '
    # Merge original error strings and suggested replacements
    new_error_str = match1.original_error_str + separator + match2.original_error_str
    new_replacement = match1.suggested_replacements[0] + separator + match2.suggested_replacements[0]
    # Create a new merged RuleMatch object
    merged_match = RuleMatch(match1.rule, match1.sentence, match1.from_pos, match2.to_pos,
                             'Il pourrait y avoir un problème ici.', 'Erreur potentielle')
    merged_match.set_original_error_str(new_error_str)
    merged_match.set_suggested_replacement(new_replacement)
    # Set ID based on issue type
    new_id = 'AI_FR_MERGED_MATCH'
    type1 = match1.rule.loc_quality_issue_type
    type2 = match2.rule.loc_quality_issue_type
    if type1 == 'Style' and type2 == 'Style':
        new_id += '_STYLE'
    if 'picky' in match1.rule.tags and 'picky' in match2.rule.tags:
        new_id += '_PICKY'
    merged_match.specific_rule_id = new_id
    # Set ITSIssueType to Grammar unless both are Style
    if type1 != type2:
        merged_match.rule.loc_quality_issue_type = 'Grammar'
    elif type1 == 'Style':
        merged_match.rule.loc_quality_issue_type = 'Style'
    return merged_match


def filter_rule_matches(language, rule_matches, annotated_text, enabled_rules):
    """French.filterRuleMatches: adjustFrenchRuleMatch for every match;
    adjacent or overlapping matches of the AI rules (AI_FR_GGEC_*) are
    merged or skipped"""
    result_matches = []
    previous_match = None
    for match in rule_matches:
        current_match = adjust_french_rule_match(language, match, enabled_rules)
        suggestions = current_match.suggested_replacements
        current_id = current_match.rule.get_id()
        # ignore adding punctuation at the sentence end
        if len(suggestions) == 1 and current_id.startswith('AI_FR_GGEC'):
            suggestion = suggestions[0]
            if current_id == 'AI_FR_GGEC_MISSING_PUNCTUATION_PERIOD' and suggestion.endswith('.'):
                if jregex.java_replace(_TRAILING_WHITESPACE, '', current_match.sentence.text).endswith(
                        suggestion[:-1]):
                    continue
        if (previous_match is not None and previous_match.rule.get_id().startswith('AI_FR_GGEC')
                and current_id.startswith('AI_FR_GGEC')):
            if previous_match.to_pos > current_match.from_pos:
                continue  # Skip overlapping matches
            # Check if matches are adjacent and share the same 'picky' status
            if ((previous_match.to_pos == current_match.from_pos or previous_match.to_pos + 1 == current_match.from_pos)
                    and ('picky' in previous_match.rule.tags) == ('picky' in current_match.rule.tags)):
                prev_type = previous_match.rule.loc_quality_issue_type
                cur_type = current_match.rule.loc_quality_issue_type
                # Merge if they have the same ITSIssueType
                if prev_type == cur_type:
                    previous_match = _merge_matches(previous_match, current_match).copy()
                    continue
                # If matches have different ITSIssueTypes but neither is a style match, merge them
                if prev_type != cur_type and prev_type != 'Style' and cur_type != 'Style':
                    previous_match = _merge_matches(previous_match, current_match).copy()
                    continue
            # If no merge happened, add the previous match to results
            result_matches.append(previous_match)
            previous_match = current_match  # Move to next match
        else:
            # Ensure current match becomes previous if no merging criteria are met
            if previous_match is not None:
                result_matches.append(previous_match)
            previous_match = current_match
    # Add the last processed match if it exists and hasn't been added yet
    if previous_match is not None:
        result_matches.append(previous_match)
    return result_matches
