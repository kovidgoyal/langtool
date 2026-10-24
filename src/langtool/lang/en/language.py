"""The code of org.languagetool.language.English (and its variants) that is
not declarative (see langtool.languages): filterRuleMatches."""


def filter_rule_matches(language, rule_matches, annotated_text, enabled_rules):
    """English.filterRuleMatches: a whitespace is added to the suggestions
    when the error is in a contraction ('ll, n't...) and the suggestion is
    not (duplicate suggestions are removed); the rules of the matches of
    EN_SIMPLE_REPLACE...GRAMME(S) get the issue type LocaleViolation."""
    new_rule_matches = []
    for rm in rule_matches:
        error_str = rm.original_error_str
        new_replacements = []
        for suggested_replacement in rm.suggested_replacement_objects:
            new_repl_str = suggested_replacement.replacement
            if len(error_str) > 2:
                # add a whitespace when the error is in a contraction and the suggestion is not
                if (error_str.startswith("'") and not new_repl_str.startswith("'")
                        and not new_repl_str.startswith('’') and not new_repl_str.startswith(' ')):
                    new_repl_str = ' ' + new_repl_str
                if error_str.startswith("n't") and not new_repl_str.startswith("n't") and \
                        not new_repl_str.startswith('n’t'):
                    new_repl_str = ' ' + new_repl_str
            new_suggested_replacement = suggested_replacement.copy(new_repl_str)
            if new_suggested_replacement not in new_replacements:
                new_replacements.append(new_suggested_replacement)
        new_match = rm.copy()  # new RuleMatch(rm, newReplacements)
        new_match.set_suggested_replacement_objects(new_replacements)
        specific_id = new_match.get_specific_rule_id()
        if specific_id.startswith('EN_SIMPLE_REPLACE') and (specific_id.endswith('GRAMME')
                                                            or specific_id.endswith('GRAMMES')):
            new_match.rule.loc_quality_issue_type = 'LocaleViolation'
        new_rule_matches.append(new_match)
    return new_rule_matches
