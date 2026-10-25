"""The code of org.languagetool.language.German and SwissGerman that is not
declarative (see langtool.languages): filterRuleMatches (merging of
adjacent AI_DE_GGEC matches, and for SwissGerman the replacement of ß by ss
in the suggestions) and toAdvancedTypography."""

from ... import jregex
from ...rules.base import RuleMatch

_TYPOGRAPHY_PATTERN = jregex.compile('\\b([a-zA-Z]\\.)([a-zA-Z]\\.)')
_TRAILING_WHITESPACE = jregex.compile('\\s+$')


def to_advanced_typography(language, text):
    """German.toAdvancedTypography: Language.toAdvancedTypography plus a
    non-breaking space between abbreviation parts like "z.B." """
    output = language.base_to_advanced_typography(text)
    # non-breaking space
    output = _TYPOGRAPHY_PATTERN.sub('\\1\u00a0\\2', output)
    output = _TYPOGRAPHY_PATTERN.sub('\\1\u00a0\\2', output)
    return output


def _merge_matches(match1, match2):
    """German.mergeMatches"""
    # Calculate separator based on position
    separator = ''
    if match1.to_pos + 1 == match2.from_pos:
        separator = ' '
    # Merge original error strings and suggested replacements
    new_error_str = match1.original_error_str + separator + match2.original_error_str
    new_replacement = match1.suggested_replacements[0] + separator + match2.suggested_replacements[0]
    # Create a new merged RuleMatch object
    merged = RuleMatch(match1.rule, match1.sentence, match1.from_pos, match2.to_pos,
                       'Hier scheint es einen Fehler zu geben.', 'Potenzieller Fehler')
    merged.set_original_error_str(new_error_str)
    merged.set_suggested_replacement(new_replacement)
    # Create a new specific rule ID based on conditions
    merged.specific_rule_id = 'AI_DE_MERGED_MATCH'
    # If issue types differ, set to Grammar unless both are Style (Java changes the rule)
    t1, t2 = match1.rule.loc_quality_issue_type, match2.rule.loc_quality_issue_type
    if t1 != t2:
        merged.rule.loc_quality_issue_type = 'Grammar'
    elif t1 == 'Style' and t2 == 'Style':
        merged.rule.loc_quality_issue_type = 'Style'
    return merged


def german_filter_rule_matches(rule_matches):
    """German.filterRuleMatches"""
    result_matches = []
    previous = None
    for current in rule_matches:
        suggestions = current.suggested_replacements
        current_id = current.rule.get_id()
        # ignore adding punctuation at the sentence end
        if len(suggestions) == 1 and current_id.startswith('AI_DE_GGEC'):
            suggestion = suggestions[0]
            if current_id == 'AI_DE_GGEC_MISSING_PUNCTUATION_PERIOD' and suggestion.endswith('.'):
                text = _TRAILING_WHITESPACE.sub('', current.sentence.text)
                if text.endswith(suggestion[:-1]):
                    continue
        if previous is not None and previous.rule.get_id().startswith('AI_DE_GGEC') and \
                current_id.startswith('AI_DE_GGEC'):
            if previous.to_pos > current.from_pos:
                continue  # Skip overlapping matches
            # Check if matches are adjacent and share the same 'picky' status
            if (previous.to_pos == current.from_pos or previous.to_pos + 1 == current.from_pos) and \
                    (('picky' in previous.rule.tags) == ('picky' in current.rule.tags)):
                prev_type = previous.rule.loc_quality_issue_type
                cur_type = current.rule.loc_quality_issue_type
                # Merge if they have the same ITSIssueType
                if prev_type == cur_type:
                    previous = _merge_matches(previous, current).copy()
                    continue
                # If matches have different ITSIssueTypes but neither is a style match, merge them
                if prev_type != cur_type and prev_type != 'Style' and cur_type != 'Style':
                    previous = _merge_matches(previous, current).copy()
                    continue
            # If no merge happened, add the previous match to results
            result_matches.append(previous)
            previous = current  # Move to next match
        else:
            # Ensure current match becomes previous if no merging criteria are met
            if previous is not None:
                result_matches.append(previous)
            previous = current
    # Add the last processed match if it exists and hasn't been added yet
    if previous is not None:
        result_matches.append(previous)
    return result_matches


def _swiss_filter_rule_matches(rule_matches):
    """SwissGerman.filterRuleMatches (after German.filterRuleMatches)"""
    new_rule_matches = []
    for rm in rule_matches:
        # TODO (Java): replace this by supporting remote-rule-filter for language variants
        rule_id = rm.rule.get_id()
        if rule_id in ('AI_DE_GGEC_REPLACEMENT_ORTHOGRAPHY_SPELL', 'AI_DE_GGEC_REPLACEMENT_ADJECTIVE_FORM'):
            matching_string = None
            if rm.sentence is not None and rm.from_pos > -1 and rm.to_pos > -1:
                sentence_str = rm.sentence.text
                if sentence_str:
                    matching_string = sentence_str[rm.from_pos:rm.to_pos]
            if matching_string is not None and 'ss' in matching_string and \
                    any(s == matching_string.replace('ss', 'ß') for s in rm.suggested_replacements):
                continue
        new_replacements = [s.copy(s.replacement.replace('ß', 'ss')) for s in rm.suggested_replacement_objects]
        new_match = rm.copy()  # new RuleMatch(rm, newReplacements)
        new_match.set_suggested_replacement_objects(new_replacements)
        new_rule_matches.append(new_match)
    return new_rule_matches


def filter_rule_matches(language, rule_matches, annotated_text, enabled_rules):
    """Language.filterRuleMatches of German and its variants (SwissGerman
    additionally replaces ß by ss in the suggestions)"""
    rule_matches = german_filter_rule_matches(rule_matches)
    if language.code == 'de-CH':
        rule_matches = _swiss_filter_rule_matches(rule_matches)
    return rule_matches
