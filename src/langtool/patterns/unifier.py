"""Port of org.languagetool.rules.patterns.Unifier and UnifierConfiguration:
unification of features (e.g. gender, number) over tokens."""

from ..analysis import AnalyzedTokenReadings

UNIFY_IGNORE = 'unify-ignore'


class UnifierConfiguration:

    def __init__(self):
        self.equivalence_types = {}  # (feature, type) -> PatternToken
        self.equivalence_features = {}  # feature -> [types]

    def set_equivalence(self, feature, type_, elem):
        key = (feature, type_)
        if key in self.equivalence_types:
            return
        self.equivalence_types[key] = elem
        self.equivalence_features.setdefault(feature, []).append(type_)

    def create_unifier(self):
        return Unifier(self.equivalence_types, self.equivalence_features)


class Unifier:

    def __init__(self, equivalence_types, equivalence_features):
        self.equivalence_types = equivalence_types
        self.equivalence_features = equivalence_features
        self.tok_sequence = []
        self.tok_sequence_equivalences = []
        self.equivalences_matched = []
        self.equivalences_to_be_kept = {}
        self.features_found = []
        self.tmp_features_found = []
        self.unification_feats = None
        self.reset()

    def reset(self):
        self.equivalences_matched = []
        self.all_feats_in = False
        self.tok_cnt = 0
        self.features_found = []
        self.tmp_features_found = []
        self.tok_sequence = []
        self.tok_sequence_equivalences = []
        self.readings_counter = 1
        self.uni_matched = False
        self.uni_all_matched = False
        self.in_unification = False

    def is_satisfied(self, a_token, u_features):
        if self.all_feats_in and not self.equivalences_matched:
            return False
        if u_features is None:
            raise RuntimeError('isSatisfied called without features being set')
        self.unification_feats = u_features
        unified = True
        if self.all_feats_in:
            unified = self._check_next(a_token, u_features)
        else:
            em = self.equivalences_matched
            while len(em) <= self.tok_cnt:
                em.append({})
            for feat, types in u_features.items():
                if not types:
                    types = self.equivalence_features.get(feat)
                if types is None:
                    raise RuntimeError("Unification feature '%s' is not defined in this unifier." % feat)
                for type_name in types:
                    test_elem = self.equivalence_types.get((feat, type_name))
                    if test_elem is None:
                        return False
                    if test_elem.is_matched(a_token):
                        em[self.tok_cnt].setdefault(feat, set()).add(type_name)
                unified = feat in em[self.tok_cnt]
                if not unified:
                    del em[self.tok_cnt]
                    break
            if unified:
                if self.tok_cnt == 0 or not self.tok_sequence:
                    self.tok_sequence.append(AnalyzedTokenReadings(a_token, 0))
                    self.tok_sequence_equivalences.append([em[self.tok_cnt]])
                else:
                    self.tok_sequence[0].add_reading(a_token, '')
                    self.tok_sequence_equivalences[0].append(em[self.tok_cnt])
                self.tok_cnt += 1
        return unified

    def _check_next(self, a_token, u_features):
        any_feat_unified = False
        token_features_found = list(self.tmp_features_found)
        here = {}
        if self.all_feats_in:
            for i in range(self.tok_cnt):
                all_feats_unified = True
                for feat, types in u_features.items():
                    feat_unified = False
                    if not types:
                        types = self.equivalence_features.get(feat)
                    for type_name in types:
                        s = self.equivalences_matched[i].get(feat)
                        if s is not None and type_name in s:
                            test_elem = self.equivalence_types.get((feat, type_name))
                            matched = test_elem.is_matched(a_token)
                            feat_unified = feat_unified or matched
                            if matched:
                                self.equivalences_to_be_kept.setdefault(feat, set()).add(type_name)
                                here.setdefault(feat, set()).add(type_name)
                    all_feats_unified = all_feats_unified and feat_unified
                token_features_found[i] = token_features_found[i] or all_feats_unified
                any_feat_unified = any_feat_unified or all_feats_unified
            if any_feat_unified:
                if len(self.tok_sequence) == self.readings_counter:
                    self.tok_sequence.append(AnalyzedTokenReadings(a_token, 0))
                    self.tok_sequence_equivalences.append([here])
                else:
                    if self.readings_counter < len(self.tok_sequence):
                        self.tok_sequence[self.readings_counter].add_reading(a_token, '')
                        self.tok_sequence_equivalences[self.readings_counter].append(here)
                    else:
                        any_feat_unified = False
                self.tmp_features_found = token_features_found
        return any_feat_unified

    def start_next_token(self):
        self.features_found = list(self.tmp_features_found)
        self.readings_counter += 1
        keep = self.equivalences_to_be_kept
        for j in range(len(self.tok_sequence)):
            for eqmap in self.tok_sequence_equivalences[j]:
                for feat in self.equivalence_features:
                    if feat != UNIFY_IGNORE:
                        if feat in eqmap:
                            if feat in keep:
                                eqmap[feat] &= keep[feat]
                            else:
                                del eqmap[feat]
                        else:
                            eqmap.pop(feat, None)
        keep.clear()

    def start_unify(self):
        self.all_feats_in = True
        for i in range(self.tok_cnt):
            self.features_found.append(False)
        self.tmp_features_found = list(self.features_found)

    def get_final_unification_value(self, u_features):
        tok_unified = 0
        for j in range(len(self.tok_sequence)):
            found = False
            for i, eqmap in enumerate(self.tok_sequence_equivalences[j]):
                feat_unified = 0
                if UNIFY_IGNORE in eqmap:
                    if i == 0:
                        tok_unified += 1
                    found = True
                    continue
                for feat in u_features:
                    s = eqmap.get(feat)
                    if s is not None and not s:
                        feat_unified = 0
                    else:
                        feat_unified += 1
                    if feat_unified == len(self.unification_feats) and tok_unified <= j:
                        tok_unified += 1
                        found = True
                        break
            if not found:
                return False
        return tok_unified == len(self.tok_sequence)

    def get_unified_tokens(self):
        if not self.tok_sequence:
            return None
        u_tokens = []
        for j in range(len(self.tok_sequence)):
            found = False
            for i, eqmap in enumerate(self.tok_sequence_equivalences[j]):
                feat_unified = 0
                if UNIFY_IGNORE in eqmap:
                    self._add_token_to_sequence(u_tokens, self.tok_sequence[j].readings[i], j)
                    found = True
                else:
                    for feat in self.unification_feats:
                        s = eqmap.get(feat)
                        if s is not None and not s:
                            feat_unified = 0
                        else:
                            feat_unified += 1
                        if feat_unified == len(self.unification_feats):
                            self._add_token_to_sequence(u_tokens, self.tok_sequence[j].readings[i], j)
                            found = True
            if not found:
                return None
        return u_tokens

    @staticmethod
    def _add_token_to_sequence(seq, token, pos):
        if len(seq) <= pos or not seq:
            seq.append(AnalyzedTokenReadings(token, 0))
        else:
            seq[pos].add_reading(token, '')

    def is_unified(self, match_token, u_features, last_reading, is_matched=True):
        if self.in_unification:
            if is_matched:
                self.uni_matched = self.is_satisfied(match_token, u_features) or self.uni_matched
            self.uni_all_matched = self.uni_matched
            if last_reading:
                self.start_next_token()
                self.uni_matched = False
            return self.uni_all_matched and self.get_final_unification_value(u_features)
        else:
            if is_matched:
                self.is_satisfied(match_token, u_features)
        if last_reading:
            self.in_unification = True
            self.uni_matched = False
            self.start_unify()
        return True

    def add_neutral_element(self, atr):
        self.tok_sequence.append(atr)
        m = {UNIFY_IGNORE: set()}
        self.tok_sequence_equivalences.append([m] * len(atr.readings))
        self.readings_counter += 1

    def get_final_unified(self):
        if self.in_unification:
            return self.get_unified_tokens()
        return None
