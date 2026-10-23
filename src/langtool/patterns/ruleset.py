"""Port of org.languagetool.rules.patterns.RuleSet: fast pre-selection of the
rules that can possibly match a sentence, based on the token/lemma hints of
pattern rules."""


class RuleSet:

    def __init__(self, rules, with_lemma_hints=True):
        self.all_rules = list(rules)
        self.by_token = {}
        self.by_lemma = {}
        self.unclassified = []
        for i, rule in enumerate(self.all_rules):
            hints = getattr(rule, 'token_hints', None)
            first = None
            if hints:
                if with_lemma_hints:
                    first = hints[0]
                else:
                    for th in hints:
                        if not th.inflected:
                            first = th
                            break
            if first is not None:
                m = self.by_lemma if first.inflected else self.by_token
                for h in first.lower_case_values:
                    m.setdefault(h, []).append(i)
            else:
                self.unclassified.append(i)

    def rules_for_sentence(self, sentence):
        included = set(self.unclassified)
        if self.by_lemma:
            bl = self.by_lemma
            for lemma in sentence.lemma_offsets:
                s = bl.get(lemma)
                if s is not None:
                    included.update(s)
        bt = self.by_token
        for token in sentence.token_offsets:
            s = bt.get(token)
            if s is not None:
                included.update(s)
        rules = self.all_rules
        return [rules[i] for i in sorted(included)]
