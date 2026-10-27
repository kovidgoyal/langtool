/*
 * _rule_engine.h (included by _speedups.c, after _rule_tables.h)
 *
 * RuleSelector: port of RuleSet.rules_for_sentence plus the canBeIgnoredFor
 * check of the selected rules, the rule loop of match_sentence (the pattern
 * rules) and of XmlRuleDisambiguator. The rules of a selector are Python
 * items (the methods of rule objects, with an optional RuleHints) and
 * static segments: the rules of a unit of the static rule tables, which are
 * selected and matched on the tables in place (the Python objects of a rule
 * are only created when it matched, through the callbacks).
 *
 * MatcherTable: the per thread matchers of the rules of a RuleSelector.
 */

static PyObject *str_non_blank_tokens = NULL;
static PyObject *str_token_offsets = NULL;
static PyObject *str_lemma_offsets = NULL;
static PyObject *str_pos_tag_set = NULL;
static PyObject *str_text = NULL;

/* ------------------------------------------------------------------------ */
/* KeySet: the keys of a dict or set of str (the token offsets, lemma offsets and POS tags of a sentence) with
 * their table hashes, for the lookups of the strings of the tables */

typedef struct {
    Py_ssize_t n;
    uint32_t *hash;
    PyObject **key;      /* strong references */
    PyObject **value;    /* strong references (dict values) or NULL */
    int32_t *table;      /* open addressing, cap entries (a power of 2), -1: empty */
    uint32_t mask;
} KeySet;

static void
ks_clear(KeySet *ks)
{
    for (Py_ssize_t i = 0; i < ks->n; i++) {
        Py_XDECREF(ks->key[i]);
        if (ks->value != NULL) Py_XDECREF(ks->value[i]);
    }
    PyMem_Free(ks->hash);
    PyMem_Free(ks->key);
    PyMem_Free(ks->value);
    PyMem_Free(ks->table);
    memset(ks, 0, sizeof *ks);
}

static int
ks_add(KeySet *ks, PyObject *key, PyObject *value)
{
    if (!PyUnicode_Check(key)) {
        PyErr_SetString(PyExc_TypeError, "the token offsets, lemma offsets and POS tags must be str");
        return -1;
    }
    Py_ssize_t i = ks->n++;
    Py_INCREF(key);
    ks->key[i] = key;
    if (ks->value != NULL) {
        Py_INCREF(value);
        ks->value[i] = value;
    }
    uint32_t h = ks->hash[i] = rt_hash_unicode(key);
    uint32_t slot = h & ks->mask;
    while (ks->table[slot] != -1) slot = (slot + 1) & ks->mask;
    ks->table[slot] = (int32_t)i;
    return 0;
}

/* builds the key set of a dict (with the values) or a set */
static int
ks_build(KeySet *ks, PyObject *container)
{
    int is_dict = PyDict_Check(container);
    if (!is_dict && !PyAnySet_Check(container)) {
        PyErr_SetString(PyExc_TypeError, "a dict or set expected");
        return -1;
    }
    Py_ssize_t n = is_dict ? PyDict_GET_SIZE(container) : PySet_GET_SIZE(container);
    uint32_t cap = 8;
    while (cap < 2 * (uint64_t)n + 2) cap <<= 1;
    ks->hash = PyMem_Calloc(n + 1, sizeof(uint32_t));
    ks->key = PyMem_Calloc(n + 1, sizeof(PyObject *));
    ks->value = is_dict ? PyMem_Calloc(n + 1, sizeof(PyObject *)) : NULL;
    ks->table = PyMem_Malloc(cap * sizeof(int32_t));
    if (ks->hash == NULL || ks->key == NULL || (is_dict && ks->value == NULL) || ks->table == NULL) {
        ks_clear(ks);
        PyErr_NoMemory();
        return -1;
    }
    memset(ks->table, 0xFF, cap * sizeof(int32_t));
    ks->mask = cap - 1;
    ks->n = 0;
    if (is_dict) {
        Py_ssize_t pos = 0;
        PyObject *k, *v;
        while (PyDict_Next(container, &pos, &k, &v)) {
            if (ks->n >= n) break;
            if (ks_add(ks, k, v) < 0) { ks_clear(ks); return -1; }
        }
    } else {
        PyObject *it = PyObject_GetIter(container);
        if (it == NULL) { ks_clear(ks); return -1; }
        PyObject *k;
        while ((k = PyIter_Next(it)) != NULL) {
            int r = ks->n < n ? ks_add(ks, k, NULL) : 0;
            Py_DECREF(k);
            if (r < 0) { Py_DECREF(it); ks_clear(ks); return -1; }
        }
        Py_DECREF(it);
        if (PyErr_Occurred()) { ks_clear(ks); return -1; }
    }
    return 0;
}

/* the index of the key equal to the string stri (with the hash h) of the tables, -1 if there is none */
static inline Py_ssize_t
ks_find(const KeySet *ks, const RuleBlob *b, uint32_t stri, uint32_t h)
{
    uint32_t slot = h & ks->mask;
    int32_t k;
    while ((k = ks->table[slot]) != -1) {
        if (ks->hash[k] == h && rt_str_eq(b, stri, ks->key[k])) return k;
        slot = (slot + 1) & ks->mask;
    }
    return -1;
}

/* ------------------------------------------------------------------------ */
/* SentenceHints: the attributes of an AnalyzedSentence needed for the hint checks */

enum { KS_TOKENS = 0, KS_LEMMAS = 1, KS_TAGS = 2 };

typedef struct {
    PyObject *sentence;      /* borrowed */
    long nnb;
    PyObject *to, *lo, *tags;  /* new references */
    KeySet ks[3];
    char built[3];
} SentenceHints;

static void
shints_clear(SentenceHints *sh)
{
    Py_CLEAR(sh->to);
    Py_CLEAR(sh->lo);
    Py_CLEAR(sh->tags);
    for (int i = 0; i < 3; i++) {
        if (sh->built[i]) ks_clear(&sh->ks[i]);
        sh->built[i] = 0;
    }
    sh->sentence = NULL;
}

static void
shints_init(SentenceHints *sh)
{
    memset(sh, 0, sizeof *sh);
}

static int
shints_load(SentenceHints *sh, PyObject *sentence)
{
    if (sh->sentence == sentence) return 0;
    shints_clear(sh);
    PyObject *nb = PyObject_GetAttr(sentence, str_non_blank_tokens);
    if (nb == NULL) return -1;
    Py_ssize_t nnb = PyObject_Length(nb);
    Py_DECREF(nb);
    if (nnb < 0) return -1;
    sh->to = PyObject_GetAttr(sentence, str_token_offsets);
    if (sh->to == NULL) goto error;
    sh->lo = PyObject_GetAttr(sentence, str_lemma_offsets);
    if (sh->lo == NULL) goto error;
    sh->tags = PyObject_GetAttr(sentence, str_pos_tag_set);
    if (sh->tags == NULL) goto error;
    if (!PyDict_Check(sh->to) || !PyDict_Check(sh->lo)) {
        PyErr_SetString(PyExc_TypeError, "token_offsets and lemma_offsets must be dicts");
        goto error;
    }
    sh->nnb = (long)nnb;
    sh->sentence = sentence;
    return 0;
error:
    shints_clear(sh);
    return -1;
}

/* the key set of the loaded sentence (built when first needed), NULL on error */
static KeySet *
shints_keys(SentenceHints *sh, int which)
{
    if (!sh->built[which]) {
        PyObject *c = which == KS_TOKENS ? sh->to : which == KS_LEMMAS ? sh->lo : sh->tags;
        if (which == KS_TAGS && !PyAnySet_Check(c)) {
            PyErr_SetString(PyExc_TypeError, "pos_tag_set must be a set");
            return NULL;
        }
        if (ks_build(&sh->ks[which], c) < 0) return NULL;
        sh->built[which] = 1;
    }
    return &sh->ks[which];
}

/* ------------------------------------------------------------------------ */
/* the hint checks of the static rules (port of AbstractTokenBasedRule.canBeIgnoredFor, see rh_check) */

/* 1 if no string of the sorted hash set (off, n) is a key of ks */
static int
hset_disjoint(const RuleBlob *b, uint32_t off, uint32_t n, const KeySet *ks)
{
    if ((Py_ssize_t)n <= ks->n) {
        const rt_hent *e = b->hset + off;
        for (uint32_t i = 0; i < n; i++) {
            if (ks_find(ks, b, e[i].str, e[i].hash) >= 0) return 0;
        }
        return 1;
    }
    for (Py_ssize_t k = 0; k < ks->n; k++) {
        if (rt_hset_contains(b, off, n, ks->hash[k], ks->key[k])) return 0;
    }
    return 1;
}

/* 1 if the static rule can be ignored for the loaded sentence, 0 if not, -1 on error */
static int
static_rh_check(const RuleBlob *b, const rt_rule *r, SentenceHints *sh)
{
    if (sh->nnb < r->min_token_count) return 1;
    for (uint32_t k = 0; k < r->n_hints; k++) {
        const rt_hint *h = &b->hint[r->hints_off + k];
        KeySet *ks = shints_keys(sh, h->kind == HINT_KIND_LEMMA ? KS_LEMMAS : KS_TOKENS);
        if (ks == NULL) return -1;
        if (hset_disjoint(b, h->set_off, h->set_n, ks)) return 1;
    }
    if ((r->flags & RF_CHECK_POS) && r->n_pos_hints > 0) {
        KeySet *ks = shints_keys(sh, KS_TAGS);
        if (ks == NULL) return -1;
        for (uint32_t k = 0; k < r->n_pos_hints; k++) {
            const rt_hint *h = &b->hint[r->hints_off + r->n_hints + k];
            if (hset_disjoint(b, h->set_off, h->set_n, ks)) return 1;
        }
    }
    return 0;
}

/* ------------------------------------------------------------------------ */
/* matching on the tables (port of AbstractPatternRulePerformer.matchFrom and testAllReadings, see test_all_readings;
 * the rules with token references are matched with their objects) */

/* the StringMatcher object of the matcher entry smi (created when first needed), borrowed */
static PyObject *
rb_sm_obj(RuleBlob *b, uint32_t smi)
{
    if (b->sm_objs == NULL) {
        b->sm_objs = PyMem_Calloc(b->n_sm + 1, sizeof(PyObject *));
        if (b->sm_objs == NULL) { PyErr_NoMemory(); return NULL; }
    }
    PyObject *o = b->sm_objs[smi];
    if (o == NULL) {
        if (b->engine_hook == NULL) {
            PyErr_SetString(PyExc_RuntimeError, "rule tables: set_types() not called");
            return NULL;
        }
        o = PyObject_CallFunction(b->engine_hook, "iI", 0, b->sm[smi].obj);
        if (o == NULL) return NULL;
        if (!PyObject_TypeCheck(o, &StringMatcherBaseType)) {
            Py_DECREF(o);
            PyErr_SetString(PyExc_TypeError, "rule tables: not a StringMatcher");
            return NULL;
        }
        if (b->sm_objs[smi] != NULL) {  /* (created meanwhile by a call from the hook) */
            Py_DECREF(o);
            o = b->sm_objs[smi];
        } else {
            b->sm_objs[smi] = o;
        }
    }
    return o;
}

/* the ChunkTag object of the chunk entry ci, borrowed */
static PyObject *
rb_chunk_obj(RuleBlob *b, uint32_t ci)
{
    if (b->chunk_objs == NULL) {
        b->chunk_objs = PyMem_Calloc(b->n_chunk + 1, sizeof(PyObject *));
        if (b->chunk_objs == NULL) { PyErr_NoMemory(); return NULL; }
    }
    PyObject *o = b->chunk_objs[ci];
    if (o == NULL) {
        if (b->engine_hook == NULL) {
            PyErr_SetString(PyExc_RuntimeError, "rule tables: set_types() not called");
            return NULL;
        }
        o = PyObject_CallFunction(b->engine_hook, "iI", 1, b->chunk[ci].obj);
        if (o == NULL) return NULL;
        if (b->chunk_objs[ci] != NULL) {
            Py_DECREF(o);
            o = b->chunk_objs[ci];
        } else {
            b->chunk_objs[ci] = o;
        }
    }
    return o;
}

/* StringMatcher.matches for a matcher of the tables (see sm_matches) */
static int
s_sm_matches(RuleBlob *b, uint32_t smi, PyObject *s, AnalyzedTokenBase *lower_src, int lower_use_lemma)
{
    const rt_sm *m = &b->sm[smi];
    if (PyUnicode_GET_LENGTH(s) > MAX_MATCH_LENGTH) return 0;
    if (m->kind == KIND_EQUALS) {
        if (rt_str_eq(b, m->value, s)) return 1;
        if (m->cs) return 0;
        if (lower_src != NULL) {
            PyObject *l = at_lower(lower_src, lower_use_lemma);
            if (l == NULL) return -1;
            return rt_str_eq(b, m->value_lower, l);
        }
        PyObject *l = PyObject_CallMethodNoArgs(s, str_lower);
        if (l == NULL) return -1;
        int r = rt_str_eq(b, m->value_lower, l);
        Py_DECREF(l);
        return r;
    }
    if (m->kind == KIND_SET) {
        if (m->cs) return rt_hset_contains(b, m->set_off, m->set_n, rt_hash_unicode(s), s);
        if (lower_src != NULL) {
            PyObject *l = at_lower(lower_src, lower_use_lemma);
            if (l == NULL) return -1;
            return rt_hset_contains(b, m->set_off, m->set_n, rt_hash_unicode(l), l);
        }
        PyObject *l = PyObject_CallMethodNoArgs(s, str_lower);
        if (l == NULL) return -1;
        int r = rt_hset_contains(b, m->set_off, m->set_n, rt_hash_unicode(l), l);
        Py_DECREF(l);
        return r;
    }
    PyObject *o = rb_sm_obj(b, smi);
    if (o == NULL) return -1;
    Py_INCREF(o);
    int r = sm_matches(o, s, lower_src, lower_use_lemma);
    Py_DECREF(o);
    return r;
}

static int
s_pos_matched(RuleBlob *b, const rt_pt *pt, AnalyzedTokenBase *at)
{
    if (pt->pos == RT_NONE) return 1;
    const rt_pos *pos = &b->pos[pt->pos];
    if (pos->tag == RT_NONE || (pos->unknown && at->has_no_pos_tag)) return 1;
    PyObject *tp = at->pos_tag;
    if (tp == NULL || tp == Py_None) return 0;
    if (pos->sm != RT_NONE) return s_sm_matches(b, pos->sm, tp, NULL, 0);
    return rt_str_eq(b, pos->tag, tp);
}

/* PatternToken.is_matched */
static int
s_pt_is_matched(RuleBlob *b, const rt_pt *pt, AnalyzedTokenBase *at)
{
    if ((pt->flags & PTF_TEST_WHITESPACE) && ((pt->flags & PTF_WHITESPACE_BEFORE) != 0) != (at->whitespace_before != 0))
        return 0;
    int pos_negation = pt->pos != RT_NONE ? b->pos[pt->pos].negation : 0;
    if (pt->flags & PTF_TEST_STRING) {
        int use_lemma = (pt->flags & PTF_INFLECTED) && at->lemma != NULL && at->lemma != Py_None;
        PyObject *test = use_lemma ? at->lemma : at->token;
        int m = s_sm_matches(b, pt->sm, test, at, use_lemma);
        if (m < 0) return -1;
        if ((m != 0) == ((pt->flags & PTF_NEGATION) != 0)) return 0;
        int p = s_pos_matched(b, pt, at);
        if (p < 0) return -1;
        return (p != 0) != (pos_negation != 0);
    }
    if (pt->flags & PTF_NEGATION) return 0;
    int p = s_pos_matched(b, pt, at);
    if (p < 0) return -1;
    return (p != 0) != (pos_negation != 0);
}

static int
s_pt_is_exception_matched(RuleBlob *b, const rt_pt *pt, AnalyzedTokenBase *at)
{
    for (uint32_t i = 0; i < pt->n_cn; i++) {
        const rt_pt *e = &b->pt[b->idx[pt->exc_off + i]];
        if (!(e->flags & PTF_EXCEPTION_VALID_NEXT)) {
            int r = s_pt_is_matched(b, e, at);
            if (r != 0) return r;
        }
    }
    return 0;
}

static int
s_pt_is_exception_matched_completely(RuleBlob *b, const rt_pt *pt, AnalyzedTokenBase *at)
{
    int r = s_pt_is_exception_matched(b, pt, at);
    if (r != 0) return r;
    if (!(pt->flags & PTF_AND_GROUP)) return 0;
    for (uint32_t i = 0; i < pt->n_and; i++) {
        r = s_pt_is_exception_matched(b, &b->pt[b->idx[pt->and_off + i]], at);
        if (r != 0) return r;
    }
    return 0;
}

static int
s_pt_is_matched_by_scope_next_exception(RuleBlob *b, const rt_pt *pt, AnalyzedTokenBase *at)
{
    for (uint32_t i = 0; i < pt->n_cn; i++) {
        const rt_pt *e = &b->pt[b->idx[pt->exc_off + i]];
        if (e->flags & PTF_EXCEPTION_VALID_NEXT) {
            int r = s_pt_is_matched(b, e, at);
            if (r != 0) return r;
        }
    }
    return 0;
}

static int
s_pt_is_matched_by_previous_exception(RuleBlob *b, const rt_pt *pt, ATRBase *atr)
{
    if (pt->n_prev == 0) return 0;
    Py_ssize_t nr = PyList_GET_SIZE(atr->readings);
    for (Py_ssize_t j = 0; j < nr; j++) {
        AnalyzedTokenBase *at = AT(PyList_GET_ITEM(atr->readings, j));
        for (uint32_t i = 0; i < pt->n_prev; i++) {
            const rt_pt *e = &b->pt[b->idx[pt->exc_off + pt->n_cn + i]];
            if (!(e->flags & PTF_EXCEPTION_VALID_NEXT)) {
                int r = s_pt_is_matched(b, e, at);
                if (r != 0) return r;
            }
        }
    }
    return 0;
}

/* `chunk in atr.chunk_tags` (ChunkTag equality: the chunk_tag strings) for the chunk entry ci */
static int
s_chunk_in(RuleBlob *b, uint32_t ci, ATRBase *atr)
{
    PyObject *tags = atr->chunk_tags;
    if (tags == NULL || !PyTuple_Check(tags)) return 0;
    Py_ssize_t n = PyTuple_GET_SIZE(tags);
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *ot = PyObject_GetAttr(PyTuple_GET_ITEM(tags, i), str_chunk_tag);
        if (ot == NULL) return -1;
        int r = PyUnicode_Check(ot) ? rt_str_eq(b, b->chunk[ci].str, ot) : 0;
        Py_DECREF(ot);
        if (r) return 1;
    }
    return 0;
}

typedef struct {
    RuleBlob *b;
    const rt_rule *r;
    const uint32_t *pts;  /* the pattern token entries */
    Py_ssize_t n;
    PyObject **tokens;    /* ATRBase */
    Py_ssize_t ntokens;
    int prev_matched;
    int check_immunized;
    int unify;            /* collect the readings to unify / the neutral readings */
    PyObject **to_unify;
    PyObject **neutral;
    Py_ssize_t *canon;    /* per pattern token: the first index of the same pattern token */
} SCtx;

#define SPT(ctx, k) (&(ctx)->b->pt[(ctx)->pts[k]])

static int
s_translate_element_no(SCtx *ctx, int i)
{
    if (!(ctx->r->flags & RF_USE_LIST) || i < 0) return i;
    int j = 0;
    for (int k = 0; k < i && k < (int)ctx->r->n_elno; k++) j += (int)ctx->b->idx[ctx->r->elno_off + k];
    return j;
}

static int
s_test_all_readings(SCtx *ctx, Py_ssize_t k, Py_ssize_t prev_k, Py_ssize_t token_no, int prev_skip_next)
{
    RuleBlob *b = ctx->b;
    ATRBase *atr = ATR(ctx->tokens[token_no]);
    if (ctx->check_immunized && atr->immunized) return 0;
    const rt_pt *pt = SPT(ctx, k);
    const rt_pt *prev = prev_k >= 0 ? SPT(ctx, prev_k) : NULL;
    PyObject *readings = atr->readings;
    Py_INCREF(readings);
    PyObject *readings_to_unify = NULL;
    Py_ssize_t nreadings = PyList_GET_SIZE(readings);
    int any_matched = 0;
    int result = -1;
    int has_and = (pt->flags & PTF_AND_GROUP) != 0;
    Py_ssize_t nand = has_and ? pt->n_and : 0;
    char and_check[MAX_AND_GROUP + 1];
    if (has_and) {
        if (nand > MAX_AND_GROUP) {
            PyErr_SetString(PyExc_ValueError, "AND group too large");
            goto done;
        }
        memset(and_check, 0, nand + 1);
    }
    int prev_has_cn = prev != NULL && prev->n_cn > 0;
    int gou = (ctx->r->flags & RF_GROUPS_OR_UNIFICATION) != 0;
    int collect = ctx->unify && (pt->flags & PTF_UNIFIED) && !(pt->flags & PTF_UNIFICATION_NEUTRAL);
    int pt_has_pos_tag = pt->pos != RT_NONE && b->pos[pt->pos].tag != RT_NONE;
    int pt_pos_negation = pt->pos != RT_NONE && b->pos[pt->pos].negation;
    int r;
    for (Py_ssize_t i = 0; i < nreadings && i < PyList_GET_SIZE(readings); i++) {
        AnalyzedTokenBase *mt = AT(PyList_GET_ITEM(readings, i));
        if (!ctx->prev_matched && prev_skip_next > 0 && prev != NULL) {
            r = s_pt_is_matched_by_scope_next_exception(b, prev, mt);
            if (r < 0) goto done;
            ctx->prev_matched = r;
        }
        if (!ctx->prev_matched && prev_skip_next == 0 && token_no <= ctx->ntokens - 2) {
            ATRBase *nxt = ATR(ctx->tokens[token_no + 1]);
            r = s_pt_is_matched_by_scope_next_exception(b, pt, AT(PyList_GET_ITEM(nxt->readings, 0)));
            if (r < 0) goto done;
            ctx->prev_matched = r;
        }
        if (ctx->prev_matched) { result = 0; goto done; }
        int reading_tested = 0, reading_matches = 0;
        if (!any_matched) {
            r = s_pt_is_matched(b, pt, mt);
            if (r < 0) goto done;
            if (has_and) and_check[0] = and_check[0] || r;
            any_matched = reading_matches = r;
            reading_tested = 1;
        }
        if (!any_matched && !prev_has_cn) {
            if (!pt_has_pos_tag) {
                if (pt->flags & PTF_INFLECTED) {
                    if (atr->has_same_lemmas) { result = 0; goto done; }
                } else {
                    result = 0;
                    goto done;
                }
            } else if (!pt_pos_negation && !atr_is_tagged(atr)) {
                result = 0;
                goto done;
            }
        }
        if (gou) {
            if (!reading_tested) {
                r = s_pt_is_matched(b, pt, mt);
                if (r < 0) goto done;
                if (has_and) and_check[0] = and_check[0] || r;
                reading_matches = r;
            }
            int is_last = i + 1 == nreadings;
            if (reading_matches && collect) {
                if (append_to_slot(&readings_to_unify, (PyObject *)mt) < 0) goto done;
            }
            if (has_and) {
                for (Py_ssize_t j = 0; j < nand; j++) {
                    if (!and_check[j + 1]) {
                        r = s_pt_is_matched(b, &b->pt[b->idx[pt->and_off + j]], mt);
                        if (r < 0) goto done;
                        if (r) and_check[j + 1] = 1;
                    }
                }
            }
            int cag = 1;
            if (is_last && has_and) {
                for (Py_ssize_t j = 0; j <= nand; j++) {
                    if (!and_check[j]) { cag = 0; break; }
                }
            }
            any_matched = any_matched && (!is_last || cag);
        }
    }
    if (any_matched) {
        for (Py_ssize_t i = 0; i < PyList_GET_SIZE(readings); i++) {
            r = s_pt_is_exception_matched_completely(b, pt, AT(PyList_GET_ITEM(readings, i)));
            if (r < 0) goto done;
            if (r) { result = 0; goto done; }
        }
        if (token_no > 0 && pt->n_prev > 0) {
            r = s_pt_is_matched_by_previous_exception(b, pt, ATR(ctx->tokens[token_no - 1]));
            if (r < 0) goto done;
            if (r) { result = 0; goto done; }
        }
        if ((pt->flags & PTF_UNIFICATION_NEUTRAL) && ctx->unify) {
            if (append_to_slot(&ctx->neutral[ctx->canon[k]], (PyObject *)atr) < 0) goto done;
        }
    }
    if (pt->chunk != RT_NONE) {
        if (b->chunk[pt->chunk].is_regexp) {
            PyObject *co = rb_chunk_obj(b, pt->chunk);
            if (co == NULL) goto done;
            Py_INCREF(co);
            r = chunk_matches(co, atr, 1);
            Py_DECREF(co);
        } else {
            r = s_chunk_in(b, pt->chunk, atr);
        }
        if (r < 0) goto done;
        any_matched = any_matched && ((r != 0) != ((pt->flags & PTF_NEGATION) != 0));
    }
    if (has_and) {
        for (Py_ssize_t j = 0; j < nand; j++) {
            const rt_pt *e = &b->pt[b->idx[pt->and_off + j]];
            if (e->chunk != RT_NONE) {
                r = s_chunk_in(b, e->chunk, atr);
                if (r < 0) goto done;
                any_matched = any_matched && ((r != 0) != ((e->flags & PTF_NEGATION) != 0));
            }
        }
    }
    if (any_matched && readings_to_unify != NULL) {
        if (append_to_slot(&ctx->to_unify[ctx->canon[k]], readings_to_unify) < 0) goto done;
    }
    result = any_matched;
done:
    Py_XDECREF(readings_to_unify);
    Py_DECREF(readings);
    return result;
}

static int
s_skip_max_tokens(SCtx *ctx, Py_ssize_t k, Py_ssize_t prev_k, int prev_skip_next, Py_ssize_t m, Py_ssize_t remaining)
{
    int max_skip = 0;
    int mo = SPT(ctx, k)->max_occurrence;
    long long max_occ = mo == -1 ? 0x7fffffffLL : mo;
    for (long long j = 1; j < max_occ && m + j < ctx->ntokens - remaining; j++) {
        int r = s_test_all_readings(ctx, k, prev_k, m + j, prev_skip_next);
        if (r < 0) return -1;
        if (r) max_skip++;
        else break;
    }
    return max_skip;
}

static void
s_clear_unify(SCtx *ctx)
{
    if (!ctx->unify) return;
    for (Py_ssize_t i = 0; i < ctx->n; i++) {
        Py_CLEAR(ctx->to_unify[i]);
        Py_CLEAR(ctx->neutral[i]);
    }
}

static int
s_call_unify(SCtx *ctx, PyObject *unify)
{
    Py_ssize_t n = ctx->n;
    PyObject *tu = PyList_New(n);
    if (tu == NULL) return -1;
    PyObject *nl = PyList_New(n);
    if (nl == NULL) { Py_DECREF(tu); return -1; }
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *a = ctx->to_unify[i] != NULL ? ctx->to_unify[i] : Py_None;
        PyObject *c = ctx->neutral[i] != NULL ? ctx->neutral[i] : Py_None;
        Py_INCREF(a);
        Py_INCREF(c);
        PyList_SET_ITEM(tu, i, a);
        PyList_SET_ITEM(nl, i, c);
    }
    PyObject *r = PyObject_CallFunctionObjArgs(unify, tu, nl, NULL);
    Py_DECREF(tu);
    Py_DECREF(nl);
    if (r == NULL) return -1;
    int t = PyObject_IsTrue(r);
    Py_DECREF(r);
    return t;
}

/* the callbacks of a static rule (the methods of the matcher of the rule object, created when first needed) */
typedef struct {
    PyObject *on_match, *finish, *unify;   /* borrowed from the entry (kept alive by the caller) or NULL */
    int (*load)(void *arg);                /* loads them (with an exception set on error) */
    void *arg;
    /* a consumer in C (called instead of on_match if not NULL; returns 0 or -1) */
    int (*native)(void *narg, const int *positions, Py_ssize_t n, int first, int last, int first_marker,
                  int last_marker);
    void *narg;
} SCallbacks;

static int
s_match_from(SCtx *ctx, SCallbacks *cb, Py_ssize_t start_index, int *positions, int *first_out, int *last_out,
             int *first_marker_out, int *last_marker_out)
{
    Py_ssize_t n = ctx->n;
    Py_ssize_t ntokens = ctx->ntokens;
    int moc = ctx->r->moc;
    long skip_shift_total = 0;
    int all_match = 0;
    Py_ssize_t matching_tokens = 0;
    long first_match_token = -1, last_match_token = -1, first_marker = -1, last_marker = -1;
    long prev_skip_next = 0;
    long min_occur_skip = 0;
    Py_ssize_t prev_k = -1;
    s_clear_unify(ctx);
    for (Py_ssize_t k = 0; k < n; k++) {
        if (k > 0) prev_k = k - 1;
        const rt_pt *pt = SPT(ctx, k);
        long next_pos = (long)start_index + (long)k + skip_shift_total - min_occur_skip;
        ctx->prev_matched = 0;
        if (prev_skip_next + next_pos >= ntokens || prev_skip_next < 0) {
            prev_skip_next = (long)ntokens - (next_pos + 1);
        }
        long a = next_pos + prev_skip_next;
        long bb = (long)ntokens - ((long)n - (long)k) + moc;
        long max_tok = a < bb ? a : bb;
        for (long m = next_pos; m <= max_tok; m++) {
            int r = s_test_all_readings(ctx, k, prev_k, m, (int)prev_skip_next);
            if (r < 0) return -1;
            all_match = r;
            if (pt->flags & PTF_MAY_BE_OMITTED) {
                int found_next = 0;
                for (Py_ssize_t k2 = k + 1; k2 < n; k2++) {
                    r = s_test_all_readings(ctx, k2, k, m, (int)prev_skip_next);
                    if (r < 0) return -1;
                    if (r) {
                        all_match = 1;
                        min_occur_skip++;
                        positions[matching_tokens++] = 0;
                        found_next = 1;
                        break;
                    } else if (!(SPT(ctx, k2)->flags & PTF_MAY_BE_OMITTED)) {
                        break;
                    }
                }
                if (found_next) break;
            }
            if (all_match) {
                int skip_for_max = s_skip_max_tokens(ctx, k, prev_k, (int)prev_skip_next, m, n - k - 1);
                if (skip_for_max < 0) return -1;
                last_match_token = m + skip_for_max;
                long skip_shift = last_match_token - next_pos;
                positions[matching_tokens++] = (int)(skip_shift + 1);
                prev_skip_next = s_translate_element_no(ctx, pt->skip);
                skip_shift_total += skip_shift;
                if (first_match_token == -1) first_match_token = last_match_token - skip_for_max;
                if (first_marker == -1 && (pt->flags & PTF_INSIDE_MARKER)) first_marker = last_match_token - skip_for_max;
                if (pt->flags & PTF_INSIDE_MARKER) last_marker = last_match_token;
                break;
            }
        }
        if (!all_match) break;
    }
    if (all_match && matching_tokens == n) {
        if (ctx->unify) {
            if (cb->unify == NULL && cb->load(cb->arg) < 0) return -1;
            if (cb->unify == NULL || cb->unify == Py_None) {
                PyErr_SetString(PyExc_ValueError, "a rule with unification without the unify callback");
                return -1;
            }
            int u = s_call_unify(ctx, cb->unify);
            if (u <= 0) return u;
        }
        *first_out = (int)first_match_token;
        *last_out = (int)last_match_token;
        *first_marker_out = (int)first_marker;
        *last_marker_out = (int)last_marker;
        return 1;
    }
    return 0;
}

/* runs the static rule r on the tokens from the start indices (like cp_run): for every match
 * on_match(*prefix, positions, first, last, first_marker, last_marker) is called (the callbacks are loaded when
 * first needed), its results that are not None are appended to results (if not NULL) */
static int
s_run(RuleBlob *b, const rt_rule *r, PyObject **tokens, Py_ssize_t ntokens, const long *starts, Py_ssize_t nstarts,
      long from, long to, SCallbacks *cb, PyObject *prefix, PyObject *results, Py_ssize_t *nmatches)
{
    SCtx ctx;
    ctx.b = b;
    ctx.r = r;
    ctx.pts = b->idx + r->pt_off;
    ctx.n = r->n_pt;
    ctx.tokens = tokens;
    ctx.ntokens = ntokens;
    ctx.prev_matched = 0;
    ctx.check_immunized = r->kind == RULE_KIND_PATTERN && !(r->flags & RF_ANTI_PATTERN);
    ctx.unify = (r->flags & RF_TEST_UNIFICATION) != 0;
    ctx.to_unify = NULL;
    ctx.neutral = NULL;
    ctx.canon = NULL;
    Py_ssize_t n = ctx.n;
    Py_ssize_t nprefix = prefix != NULL ? PyTuple_GET_SIZE(prefix) : 0;
    int ret = -1;
    int *positions = PyMem_Calloc(n + 1, sizeof(int));
    if (positions == NULL) { PyErr_NoMemory(); goto done; }
    if (ctx.unify) {
        ctx.to_unify = PyMem_Calloc(n + 1, sizeof(PyObject *));
        ctx.neutral = PyMem_Calloc(n + 1, sizeof(PyObject *));
        ctx.canon = PyMem_Calloc(n + 1, sizeof(Py_ssize_t));
        if (ctx.to_unify == NULL || ctx.neutral == NULL || ctx.canon == NULL) { PyErr_NoMemory(); goto done; }
        for (Py_ssize_t i = 0; i < n; i++) {
            Py_ssize_t c = i;
            for (Py_ssize_t j = 0; j < i; j++) {
                if (ctx.pts[j] == ctx.pts[i]) { c = j; break; }
            }
            ctx.canon[i] = c;
        }
    }
    if (starts != NULL) { from = 0; to = (long)nstarts - 1; }
    for (long idx = from; idx <= to; idx++) {
        long start = starts != NULL ? starts[idx] : idx;
        int first, last, fm, lm;
        int m = s_match_from(&ctx, cb, start, positions, &first, &last, &fm, &lm);
        if (m < 0) goto done;
        if (!m) continue;
        (*nmatches)++;
        if (cb->native != NULL) {
            if (cb->native(cb->narg, positions, n, first, last, fm, lm) < 0) goto done;
            continue;
        }
        if (cb->on_match == NULL && cb->load(cb->arg) < 0) goto done;
        PyObject *cargs = PyTuple_New(nprefix + 5);
        if (cargs == NULL) goto done;
        for (Py_ssize_t i = 0; i < nprefix; i++) {
            PyObject *o = PyTuple_GET_ITEM(prefix, i);
            Py_INCREF(o);
            PyTuple_SET_ITEM(cargs, i, o);
        }
        PyObject *pl = PyList_New(n);
        if (pl == NULL) { Py_DECREF(cargs); goto done; }
        PyTuple_SET_ITEM(cargs, nprefix, pl);
        for (Py_ssize_t i = 0; i < n; i++) {
            PyObject *v = PyLong_FromLong(positions[i]);
            if (v == NULL) { Py_DECREF(cargs); goto done; }
            PyList_SET_ITEM(pl, i, v);
        }
        int vals[4] = {first, last, fm, lm};
        for (int i = 0; i < 4; i++) {
            PyObject *v = PyLong_FromLong(vals[i]);
            if (v == NULL) { Py_DECREF(cargs); goto done; }
            PyTuple_SET_ITEM(cargs, nprefix + 1 + i, v);
        }
        PyObject *res = PyObject_Call(cb->on_match, cargs, NULL);
        Py_DECREF(cargs);
        if (res == NULL) goto done;
        if (results != NULL && res != Py_None && PyList_Append(results, res) < 0) {
            Py_DECREF(res);
            goto done;
        }
        Py_DECREF(res);
    }
    ret = 0;
done:
    if (ctx.unify && ctx.to_unify != NULL && ctx.neutral != NULL) s_clear_unify(&ctx);
    PyMem_Free(positions);
    PyMem_Free(ctx.to_unify);
    PyMem_Free(ctx.neutral);
    PyMem_Free(ctx.canon);
    return ret;
}

/* ------------------------------------------------------------------------ */
/* RuleSelector */

typedef struct {
    RuleBlob *blob;          /* strong reference */
    uint32_t unit;
    uint32_t rule_off;       /* the first rule of the unit in the tables */
    uint32_t n;              /* the number of rules of the unit */
    Py_ssize_t start;        /* the index of the first rule of the unit in the selector */
    int sel;                 /* the index of the unit's selector data: 0 with lemma hints, 1 without */
    char *mode;              /* per rule: 0 inactive, 1 matched on the tables, 2 a Python item (see init) */
} StaticSeg;

typedef struct {
    PyObject_HEAD
    Py_ssize_t n;
    PyObject *by_token;      /* dict: str -> list/tuple of rule indices */
    PyObject *by_lemma;      /* dict or None */
    PyObject *items;         /* tuple of n objects (returned by select / called by disambiguate), None for the
                              * static rules */
    PyObject *hints;         /* tuple of n RuleHints or None */
    Py_ssize_t *unclassified;
    Py_ssize_t n_unclassified;
    char *check_pos;
    StaticSeg *segs;
    Py_ssize_t nsegs;
    int32_t *seg_of;         /* per rule: the static segment or -1 */
} RuleSelector;

static int
rs_traverse(RuleSelector *self, visitproc visit, void *arg)
{
    Py_VISIT(self->by_token);
    Py_VISIT(self->by_lemma);
    Py_VISIT(self->items);
    Py_VISIT(self->hints);
    for (Py_ssize_t i = 0; i < self->nsegs; i++) Py_VISIT(self->segs[i].blob);
    return 0;
}

static int
rs_clear(RuleSelector *self)
{
    Py_CLEAR(self->by_token);
    Py_CLEAR(self->by_lemma);
    Py_CLEAR(self->items);
    Py_CLEAR(self->hints);
    return 0;
}

static void
rs_free_segs(RuleSelector *self)
{
    for (Py_ssize_t i = 0; i < self->nsegs; i++) {
        Py_CLEAR(self->segs[i].blob);
        PyMem_Free(self->segs[i].mode);
    }
    PyMem_Free(self->segs);
    self->segs = NULL;
    self->nsegs = 0;
    PyMem_Free(self->seg_of);
    self->seg_of = NULL;
}

static void
rs_dealloc(RuleSelector *self)
{
    PyObject_GC_UnTrack(self);
    rs_clear(self);
    rs_free_segs(self);
    PyMem_Free(self->unclassified);
    PyMem_Free(self->check_pos);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

/* parses the static segments [(start, blob, unit, mode bytes, with_lemma_hints)] */
static int
rs_parse_segs(PyObject *segments, Py_ssize_t n, StaticSeg **out, Py_ssize_t *nout,
              int32_t **seg_of_out)
{
    *out = NULL;
    *nout = 0;
    *seg_of_out = NULL;
    if (segments == Py_None) return 0;
    PyObject *seq = PySequence_Fast(segments, "segments must be a sequence");
    if (seq == NULL) return -1;
    Py_ssize_t ns = PySequence_Fast_GET_SIZE(seq);
    StaticSeg *segs = PyMem_Calloc(ns + 1, sizeof(StaticSeg));
    int32_t *seg_of = PyMem_Malloc((n + 1) * sizeof(int32_t));
    if (segs == NULL || seg_of == NULL) {
        PyMem_Free(segs);
        PyMem_Free(seg_of);
        Py_DECREF(seq);
        PyErr_NoMemory();
        return -1;
    }
    for (Py_ssize_t i = 0; i <= n; i++) seg_of[i] = -1;
    Py_ssize_t k;
    for (k = 0; k < ns; k++) {
        PyObject *t = PySequence_Fast_GET_ITEM(seq, k);
        Py_ssize_t start;
        PyObject *blob;
        unsigned int unit;
        Py_buffer mode;
        int lemma;
        if (!PyTuple_Check(t) || !PyArg_ParseTuple(t, "nO!Iy*p;bad static segment", &start, &RuleBlobType, &blob,
                                                    &unit, &mode, &lemma))
            goto error;
        RuleBlob *b = (RuleBlob *)blob;
        int ok = unit < b->n_unit;
        uint32_t rn = ok ? b->unit[unit].rule_n : 0;
        ok = ok && mode.len == (Py_ssize_t)rn && start >= 0 && start + (Py_ssize_t)rn <= n &&
             (uint64_t)b->unit[unit].rule_off + rn <= b->n_rule;
        for (Py_ssize_t j = 0; ok && j < (Py_ssize_t)rn; j++) {
            if (seg_of[start + j] != -1) ok = 0;
        }
        if (!ok) {
            PyBuffer_Release(&mode);
            PyErr_SetString(PyExc_ValueError, "bad static segment (unit, size or overlap)");
            goto error;
        }
        segs[k].mode = PyMem_Malloc(rn + 1);
        if (segs[k].mode == NULL) { PyBuffer_Release(&mode); PyErr_NoMemory(); goto error; }
        memcpy(segs[k].mode, mode.buf, rn);
        PyBuffer_Release(&mode);
        for (uint32_t j = 0; j < rn; j++) {
            if (segs[k].mode[j] > 2) { PyErr_SetString(PyExc_ValueError, "bad static rule mode"); k++; goto error; }
            seg_of[start + j] = (int32_t)k;
        }
        Py_INCREF(blob);
        segs[k].blob = b;
        segs[k].unit = unit;
        segs[k].rule_off = b->unit[unit].rule_off;
        segs[k].n = rn;
        segs[k].start = start;
        segs[k].sel = lemma ? 0 : 1;
    }
    Py_DECREF(seq);
    *out = segs;
    *nout = ns;
    *seg_of_out = seg_of;
    return 0;
error:
    for (Py_ssize_t j = 0; j <= k && j < ns; j++) {
        Py_XDECREF(segs[j].blob);
        PyMem_Free(segs[j].mode);
    }
    PyMem_Free(segs);
    PyMem_Free(seg_of);
    Py_DECREF(seq);
    return -1;
}

/* RuleSelector(by_token, by_lemma, unclassified, items, hints, check_pos, segments=None) */
static int
rs_init(RuleSelector *self, PyObject *args, PyObject *Py_UNUSED(kwds))
{
    PyObject *by_token, *by_lemma, *unclassified, *items, *hints, *check_pos, *segments = Py_None;
    if (!PyArg_ParseTuple(args, "O!OOO!O!O|O", &PyDict_Type, &by_token, &by_lemma, &unclassified, &PyTuple_Type,
                          &items, &PyTuple_Type, &hints, &check_pos, &segments))
        return -1;
    if (by_lemma != Py_None && !PyDict_Check(by_lemma)) {
        PyErr_SetString(PyExc_TypeError, "by_lemma must be a dict or None");
        return -1;
    }
    Py_ssize_t n = PyTuple_GET_SIZE(items);
    if (PyTuple_GET_SIZE(hints) != n) {
        PyErr_SetString(PyExc_ValueError, "items and hints must have the same length");
        return -1;
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *h = PyTuple_GET_ITEM(hints, i);
        if (h != Py_None && !PyObject_TypeCheck(h, &RuleHintsType)) {
            PyErr_SetString(PyExc_TypeError, "hints must be RuleHints or None");
            return -1;
        }
    }
    PyObject *cp = PySequence_Fast(check_pos, "check_pos must be a sequence");
    if (cp == NULL) return -1;
    if (PySequence_Fast_GET_SIZE(cp) != n) {
        Py_DECREF(cp);
        PyErr_SetString(PyExc_ValueError, "check_pos must have the length of items");
        return -1;
    }
    char *cpos = PyMem_Calloc(n + 1, 1);
    if (cpos == NULL) { Py_DECREF(cp); PyErr_NoMemory(); return -1; }
    for (Py_ssize_t i = 0; i < n; i++) {
        int t = PyObject_IsTrue(PySequence_Fast_GET_ITEM(cp, i));
        if (t < 0) { Py_DECREF(cp); PyMem_Free(cpos); return -1; }
        cpos[i] = (char)t;
    }
    Py_DECREF(cp);
    PyObject *uc = PySequence_Fast(unclassified, "unclassified must be a sequence");
    if (uc == NULL) { PyMem_Free(cpos); return -1; }
    Py_ssize_t nu = PySequence_Fast_GET_SIZE(uc);
    Py_ssize_t *ucl = PyMem_Calloc(nu + 1, sizeof(Py_ssize_t));
    if (ucl == NULL) { Py_DECREF(uc); PyMem_Free(cpos); PyErr_NoMemory(); return -1; }
    for (Py_ssize_t i = 0; i < nu; i++) {
        Py_ssize_t v = PyLong_AsSsize_t(PySequence_Fast_GET_ITEM(uc, i));
        if (v == -1 && PyErr_Occurred()) { Py_DECREF(uc); PyMem_Free(cpos); PyMem_Free(ucl); return -1; }
        if (v < 0 || v >= n) {
            Py_DECREF(uc); PyMem_Free(cpos); PyMem_Free(ucl);
            PyErr_SetString(PyExc_IndexError, "rule index out of range");
            return -1;
        }
        ucl[i] = v;
    }
    Py_DECREF(uc);
    StaticSeg *segs;
    Py_ssize_t nsegs;
    int32_t *seg_of;
    if (rs_parse_segs(segments, n, &segs, &nsegs, &seg_of) < 0) {
        PyMem_Free(cpos);
        PyMem_Free(ucl);
        return -1;
    }
    Py_INCREF(by_token); Py_XSETREF(self->by_token, by_token);
    Py_INCREF(by_lemma); Py_XSETREF(self->by_lemma, by_lemma);
    Py_INCREF(items); Py_XSETREF(self->items, items);
    Py_INCREF(hints); Py_XSETREF(self->hints, hints);
    PyMem_Free(self->unclassified);
    self->unclassified = ucl;
    self->n_unclassified = nu;
    PyMem_Free(self->check_pos);
    self->check_pos = cpos;
    rs_free_segs(self);
    self->segs = segs;
    self->nsegs = nsegs;
    self->seg_of = seg_of;
    self->n = n;
    return 0;
}

/* marks the rules of index (str -> rule indices) for the keys of offsets */
static int
rs_mark(RuleSelector *self, char *mark, PyObject *index, PyObject *offsets)
{
    if (!PyDict_Check(offsets)) {
        PyErr_SetString(PyExc_TypeError, "offsets must be a dict");
        return -1;
    }
    Py_ssize_t pos = 0;
    PyObject *key, *value;
    while (PyDict_Next(offsets, &pos, &key, &value)) {
        PyObject *idx = PyDict_GetItemWithError(index, key);
        if (idx == NULL) {
            if (PyErr_Occurred()) return -1;
            continue;
        }
        if (!PyList_Check(idx) && !PyTuple_Check(idx)) {
            PyErr_SetString(PyExc_TypeError, "rule indices must be a list or tuple");
            return -1;
        }
        Py_ssize_t m = PySequence_Fast_GET_SIZE(idx);
        PyObject **it = PySequence_Fast_ITEMS(idx);
        for (Py_ssize_t j = 0; j < m; j++) {
            Py_ssize_t v = PyLong_AsSsize_t(it[j]);
            if (v == -1 && PyErr_Occurred()) return -1;
            if (v < 0 || v >= self->n) {
                PyErr_SetString(PyExc_IndexError, "rule index out of range");
                return -1;
            }
            mark[v] = 1;
        }
    }
    return 0;
}

/* marks the rules of a static segment for the keys of ks in the index entries (off, n) */
static void
static_mark_index(const StaticSeg *seg, char *mark, uint32_t off, uint32_t n, const KeySet *ks)
{
    const RuleBlob *b = seg->blob;
    const rt_ient *ents = b->ient + off;
    for (Py_ssize_t k = 0; k < ks->n; k++) {
        uint32_t h = ks->hash[k];
        uint32_t lo = 0, hi = n;
        while (lo < hi) {
            uint32_t mid = lo + (hi - lo) / 2;
            if (ents[mid].hash < h) lo = mid + 1;
            else hi = mid;
        }
        for (; lo < n && ents[lo].hash == h; lo++) {
            if (!rt_str_eq(b, ents[lo].str, ks->key[k])) continue;
            const uint32_t *list = b->idx + ents[lo].list_off;
            for (uint32_t j = 0; j < ents[lo].list_n; j++) {
                uint32_t local = list[j];
                if (seg->mode[local]) mark[seg->start + local] = 1;
            }
        }
    }
}

/* the marks of the rules selected by the tokens (and lemmas) of the sentence. Returns a new buffer (PyMem) or NULL
 * on error. sh: loaded for the sentence if needed (the static segments) */
static char *
rs_select_marks(RuleSelector *self, PyObject *sentence, SentenceHints *sh)
{
    char *mark = PyMem_Calloc(self->n + 1, 1);
    if (mark == NULL) { PyErr_NoMemory(); return NULL; }
    for (Py_ssize_t i = 0; i < self->n_unclassified; i++) mark[self->unclassified[i]] = 1;
    if (self->by_lemma != Py_None && PyDict_GET_SIZE(self->by_lemma) > 0) {
        PyObject *lo = PyObject_GetAttr(sentence, str_lemma_offsets);
        if (lo == NULL) goto error;
        int r = rs_mark(self, mark, self->by_lemma, lo);
        Py_DECREF(lo);
        if (r < 0) goto error;
    }
    if (PyDict_GET_SIZE(self->by_token) > 0 || self->nsegs == 0) {
        PyObject *to = PyObject_GetAttr(sentence, str_token_offsets);
        if (to == NULL) goto error;
        int r = rs_mark(self, mark, self->by_token, to);
        Py_DECREF(to);
        if (r < 0) goto error;
    }
    for (Py_ssize_t s = 0; s < self->nsegs; s++) {
        StaticSeg *seg = &self->segs[s];
        const rt_unit *u = &seg->blob->unit[seg->unit];
        const uint32_t *sel = u->sel[seg->sel];
        for (uint32_t k = 0; k < sel[5]; k++) {
            uint32_t local = seg->blob->idx[sel[4] + k];
            if (seg->mode[local]) mark[seg->start + local] = 1;
        }
        if (sel[3] > 0 || sel[1] > 0) {
            if (shints_load(sh, sentence) < 0) goto error;
        }
        if (sel[3] > 0) {
            KeySet *ks = shints_keys(sh, KS_LEMMAS);
            if (ks == NULL) goto error;
            static_mark_index(seg, mark, sel[2], sel[3], ks);
        }
        if (sel[1] > 0) {
            KeySet *ks = shints_keys(sh, KS_TOKENS);
            if (ks == NULL) goto error;
            static_mark_index(seg, mark, sel[0], sel[1], ks);
        }
    }
    return mark;
error:
    PyMem_Free(mark);
    return NULL;
}

/* the static rule of the selector's rule i (whose seg_of is s) */
static inline const rt_rule *
rs_static_rule(RuleSelector *self, Py_ssize_t i, int32_t s, StaticSeg **seg_out, uint32_t *local_out)
{
    StaticSeg *seg = &self->segs[s];
    uint32_t local = (uint32_t)(i - seg->start);
    *seg_out = seg;
    *local_out = local;
    return &seg->blob->rule[seg->rule_off + local];
}

/* the hint check of the rule i: 1 if it can be ignored for the sentence, 0 if not, -1 on error */
static int
rs_ignorable(RuleSelector *self, Py_ssize_t i, PyObject *sentence, SentenceHints *sh)
{
    int32_t s = self->seg_of != NULL ? self->seg_of[i] : -1;
    if (s >= 0) {
        StaticSeg *seg;
        uint32_t local;
        const rt_rule *r = rs_static_rule(self, i, s, &seg, &local);
        if (seg->mode[local] != 1 || !(r->flags & RF_HINTS)) return 0;
        if (shints_load(sh, sentence) < 0) return -1;
        return static_rh_check(seg->blob, r, sh);
    }
    PyObject *h = PyTuple_GET_ITEM(self->hints, i);
    if (h == Py_None) return 0;
    if (shints_load(sh, sentence) < 0) return -1;
    return rh_check((RuleHints *)h, sh->nnb, sh->to, sh->lo, sh->tags, self->check_pos[i]);
}

/* select(sentence, use_hints, resolve=None): the items (that are not None) of the rules
 * selected for the sentence (in rule order); with use_hints, without the rules whose hints
 * show that they can be ignored for the sentence. resolve(i) gives the item of a static rule. */
static PyObject *
rs_select(RuleSelector *self, PyObject *args)
{
    PyObject *sentence, *resolve = Py_None;
    int use_hints;
    if (!PyArg_ParseTuple(args, "Op|O", &sentence, &use_hints, &resolve)) return NULL;
    if (self->items == NULL) {
        PyErr_SetString(PyExc_ValueError, "RuleSelector not initialized");
        return NULL;
    }
    SentenceHints sh;
    shints_init(&sh);
    char *mark = rs_select_marks(self, sentence, &sh);
    if (mark == NULL) { shints_clear(&sh); return NULL; }
    PyObject *out = PyList_New(0);
    if (out == NULL) goto error;
    for (Py_ssize_t i = 0; i < self->n; i++) {
        if (!mark[i]) continue;
        if (use_hints) {
            int r = rs_ignorable(self, i, sentence, &sh);
            if (r < 0) goto error;
            if (r) continue;
        }
        int32_t s = self->seg_of != NULL ? self->seg_of[i] : -1;
        if (s >= 0) {
            if (resolve == Py_None) {
                PyErr_SetString(PyExc_ValueError, "select() of static rules needs resolve");
                goto error;
            }
            PyObject *idx = PyLong_FromSsize_t(i);
            if (idx == NULL) goto error;
            PyObject *item = PyObject_CallOneArg(resolve, idx);
            Py_DECREF(idx);
            if (item == NULL) goto error;
            int r = item == Py_None ? 0 : PyList_Append(out, item);
            Py_DECREF(item);
            if (r < 0) goto error;
            continue;
        }
        PyObject *item = PyTuple_GET_ITEM(self->items, i);
        if (item == Py_None) continue;
        if (PyList_Append(out, item) < 0) goto error;
    }
    shints_clear(&sh);
    PyMem_Free(mark);
    return out;
error:
    shints_clear(&sh);
    PyMem_Free(mark);
    Py_XDECREF(out);
    return NULL;
}

/* ------------------------------------------------------------------------ */
/* MatcherTable: the per thread matchers of the rules of a RuleSelector, for
 * matching the pattern rules (applying the disambiguation rules) without
 * calling Python code for every rule. The entries are initialized lazily:
 *
 * - the Python items: by calling init(i), which returns None (the rule's item
 *   is called) or the tuple (compiled pattern, on_match, finish, unify,
 *   resolver, anchor_inflected, anchor_values, anchor_value_set,
 *   anchor_index, sent_start, pre_disambig, pattern_size,
 *   min_occur_correction):
 *   - the tokens are sentence.non_blank_pre_disambig_tokens if pre_disambig,
 *     else sentence.non_blank_tokens
 *   - the start positions: like AbstractPatternRulePerformer.do_match (the
 *     anchor hint is not used if anchor_values is None or pre_disambig)
 *   - on_match(sentence, tokens, scratch, positions, first, last,
 *     first_marker, last_marker) is called for each match (scratch: a list,
 *     the same for the matches of one sentence), the results that are not None
 *     are collected
 *   - if there was a match, finish(sentence, scratch, results) gives the
 *     result: the list of rule matches (match_sentence), the new sentence
 *     (disambiguate).
 * - the static rules are matched on the tables (no call); when a rule matched
 *   (or its unification is tested), callbacks(i) gives (on_match, finish,
 *   unify) (the methods of the matcher of the rule object). The static rules
 *   with token references (mode 1) and those of mode 2 are initialized with
 *   init(i), which returns a tuple as above or a callable (called with the
 *   sentence, like an item). The regular expression rules are only called
 *   (init(i) returns rule.match) when their expression is found in the
 *   sentence. */

enum {
    MT_NEW = 0, MT_SPEC = 1, MT_ITEM = 2, MT_STATIC = 3, MT_STATIC_CB = 4, MT_CALL = 5, MT_REGEX = 6
};

typedef struct {
    char state;
    char anchor_inflected;
    char sent_start;
    char pre_disambig;
    PyObject *compiled, *on_match, *finish, *unify, *resolver, *anchor_values, *anchor_value_set;
    long anchor_index, pattern_size, moc;
} MTEntry;

typedef struct {
    PyObject_HEAD
    Py_ssize_t n;
    MTEntry *entries;
} MatcherTable;

static void
mte_clear(MTEntry *e)
{
    Py_CLEAR(e->compiled);
    Py_CLEAR(e->on_match);
    Py_CLEAR(e->finish);
    Py_CLEAR(e->unify);
    Py_CLEAR(e->resolver);
    Py_CLEAR(e->anchor_values);
    Py_CLEAR(e->anchor_value_set);
    e->state = MT_NEW;
}

static int
mt_traverse(MatcherTable *self, visitproc visit, void *arg)
{
    if (self->entries != NULL) {
        for (Py_ssize_t i = 0; i < self->n; i++) {
            MTEntry *e = &self->entries[i];
            Py_VISIT(e->compiled);
            Py_VISIT(e->on_match);
            Py_VISIT(e->finish);
            Py_VISIT(e->unify);
            Py_VISIT(e->resolver);
            Py_VISIT(e->anchor_values);
            Py_VISIT(e->anchor_value_set);
        }
    }
    return 0;
}

static int
mt_clear(MatcherTable *self)
{
    if (self->entries != NULL) {
        for (Py_ssize_t i = 0; i < self->n; i++) mte_clear(&self->entries[i]);
    }
    return 0;
}

static void
mt_dealloc(MatcherTable *self)
{
    PyObject_GC_UnTrack(self);
    mt_clear(self);
    PyMem_Free(self->entries);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

/* MatcherTable(n) */
static int
mt_init(MatcherTable *self, PyObject *args, PyObject *Py_UNUSED(kwds))
{
    Py_ssize_t n;
    if (!PyArg_ParseTuple(args, "n", &n)) return -1;
    if (n < 0) { PyErr_SetString(PyExc_ValueError, "n must be >= 0"); return -1; }
    if (self->entries != NULL) {
        for (Py_ssize_t i = 0; i < self->n; i++) mte_clear(&self->entries[i]);
        PyMem_Free(self->entries);
        self->entries = NULL;
        self->n = 0;
    }
    self->entries = PyMem_Calloc(n + 1, sizeof(MTEntry));
    if (self->entries == NULL) { PyErr_NoMemory(); return -1; }
    self->n = n;
    return 0;
}

static PyTypeObject MatcherTableType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.MatcherTable",
    .tp_basicsize = sizeof(MatcherTable),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)mt_init,
    .tp_dealloc = (destructor)mt_dealloc,
    .tp_traverse = (traverseproc)mt_traverse,
    .tp_clear = (inquiry)mt_clear,
};

/* sets the entry from a spec tuple (see above); returns 0 or -1 */
static int
mte_set_spec(MTEntry *e, PyObject *spec)
{
    PyObject *compiled, *on_match, *finish, *unify, *resolver, *avalues, *aset;
    int ainfl, sent_start, pre;
    long aindex, psize, moc;
    if (!PyArg_ParseTuple(spec, "O!OOOOpOOlppll;bad matcher spec", &CompiledPatternType, &compiled, &on_match,
                          &finish, &unify, &resolver, &ainfl, &avalues, &aset, &aindex, &sent_start, &pre, &psize,
                          &moc))
        return -1;
    if (avalues != Py_None && (!PyTuple_Check(avalues) || !PyAnySet_Check(aset))) {
        PyErr_SetString(PyExc_TypeError, "the anchor values must be a tuple and a set");
        return -1;
    }
#define MT_SET(f, v) do { Py_INCREF(v); Py_XSETREF(e->f, v); } while (0)
    MT_SET(compiled, compiled);
    MT_SET(on_match, on_match);
    MT_SET(finish, finish);
    MT_SET(unify, unify);
    MT_SET(resolver, resolver);
    MT_SET(anchor_values, avalues);
    MT_SET(anchor_value_set, aset);
#undef MT_SET
    e->anchor_inflected = (char)ainfl;
    e->anchor_index = aindex;
    e->sent_start = (char)sent_start;
    e->pre_disambig = (char)pre;
    e->pattern_size = psize;
    e->moc = moc;
    e->state = MT_SPEC;
    return 0;
}

/* the (initialized) entry i, NULL on error */
static MTEntry *
mt_entry(MatcherTable *t, RuleSelector *sel, Py_ssize_t i, PyObject *init)
{
    MTEntry *e = &t->entries[i];
    if (e->state != MT_NEW) return e;
    int32_t s = sel->seg_of != NULL ? sel->seg_of[i] : -1;
    int static_object = 0;
    if (s >= 0) {
        StaticSeg *seg;
        uint32_t local;
        const rt_rule *r = rs_static_rule(sel, i, s, &seg, &local);
        if (seg->mode[local] == 1 && r->kind == RULE_KIND_REGEX) {
            e->state = MT_REGEX;
            return e;
        }
        if (seg->mode[local] == 1 && !(r->flags & RF_REFERENCES)) {
            e->state = MT_STATIC;
            return e;
        }
        static_object = 1;
    }
    if (init == Py_None) {
        PyErr_SetString(PyExc_ValueError, "MatcherTable entry without init");
        return NULL;
    }
    PyObject *idx = PyLong_FromSsize_t(i);
    if (idx == NULL) return NULL;
    PyObject *spec = PyObject_CallOneArg(init, idx);
    Py_DECREF(idx);
    if (spec == NULL) return NULL;
    if (e->state != MT_NEW) {  /* initialized by the init call */
        Py_DECREF(spec);
        return e;
    }
    if (spec == Py_None) {
        Py_DECREF(spec);
        if (static_object) {
            PyErr_SetString(PyExc_ValueError, "init() of a static rule returned None");
            return NULL;
        }
        e->state = MT_ITEM;
        return e;
    }
    if (static_object && !PyTuple_Check(spec)) {
        Py_XSETREF(e->on_match, spec);
        e->state = MT_CALL;
        return e;
    }
    int r = mte_set_spec(e, spec);
    Py_DECREF(spec);
    return r < 0 ? NULL : e;
}

/* the token lists of a sentence (and their checked copies) */
typedef struct {
    PyObject *sentence;    /* borrowed */
    PyObject *nb, *nb_copy, *pre, *pre_copy;   /* new references or NULL */
} SentenceTokens;

static void
stoks_clear(SentenceTokens *st)
{
    Py_CLEAR(st->nb);
    Py_CLEAR(st->nb_copy);
    Py_CLEAR(st->pre);
    Py_CLEAR(st->pre_copy);
    st->sentence = NULL;
}

static PyObject *str_non_blank_pre_disambig_tokens = NULL;

/* sets *list and *copy (borrowed) to the token list for the matching */
static int
stoks_get(SentenceTokens *st, PyObject *sentence, int pre, PyObject **list, PyObject **copy)
{
    if (st->sentence != sentence) {
        stoks_clear(st);
        st->sentence = sentence;
    }
    PyObject **l = pre ? &st->pre : &st->nb;
    PyObject **c = pre ? &st->pre_copy : &st->nb_copy;
    if (*l == NULL) {
        PyObject *v = PyObject_GetAttr(sentence, pre ? str_non_blank_pre_disambig_tokens : str_non_blank_tokens);
        if (v == NULL) return -1;
        PyObject *cp = checked_tokens_copy(v);
        if (cp == NULL) { Py_DECREF(v); return -1; }
        *l = v;
        *c = cp;
    }
    *list = *l;
    *copy = *c;
    return 0;
}

/* the union of the offsets (lists of token indices) of the anchor values that occur in the sentence: marks
 * mark[0..nnb-1]; for the Python entries (values tuple and set) or a static hint (set (off, n) of b). Returns 1 if a
 * position was marked, 0 if not, -1 on error */
static int
anchor_marks(char *mark, Py_ssize_t nnb, PyObject *offsets, PyObject *values, PyObject *value_set, const RuleBlob *b,
             const rt_hint *h, const KeySet *ks)
{
    int found = 0;
    PyObject *key, *value;
    Py_ssize_t pos = 0, vi = 0;
    Py_ssize_t nv = values != NULL ? PyTuple_GET_SIZE(values) : (Py_ssize_t)h->set_n;
    Py_ssize_t no = ks != NULL ? ks->n : PyDict_GET_SIZE(offsets);
    for (;;) {
        PyObject *lst;
        if (nv <= no) {
            if (vi >= nv) break;
            if (values != NULL) {
                lst = PyDict_GetItemWithError(offsets, PyTuple_GET_ITEM(values, vi++));
                if (lst == NULL) {
                    if (PyErr_Occurred()) return -1;
                    continue;
                }
            } else {
                const rt_hent *e = &b->hset[h->set_off + vi++];
                Py_ssize_t k = ks_find(ks, b, e->str, e->hash);
                if (k < 0) continue;
                lst = ks->value[k];
            }
        } else if (values != NULL) {
            if (!PyDict_Next(offsets, &pos, &key, &value)) break;
            int c = PySet_Contains(value_set, key);
            if (c < 0) return -1;
            if (!c) continue;
            lst = value;
        } else {
            if (pos >= ks->n) break;
            Py_ssize_t k = pos++;
            if (!rt_hset_contains(b, h->set_off, h->set_n, ks->hash[k], ks->key[k])) continue;
            lst = ks->value[k];
        }
        if (!PyList_Check(lst)) {
            PyErr_SetString(PyExc_TypeError, "offsets must be lists");
            return -1;
        }
        for (Py_ssize_t j = 0; j < PyList_GET_SIZE(lst); j++) {
            Py_ssize_t ai = PyLong_AsSsize_t(PyList_GET_ITEM(lst, j));
            if (ai == -1 && PyErr_Occurred()) return -1;
            if (ai < 0 || ai >= nnb) {
                PyErr_SetString(PyExc_IndexError, "token offset out of range");
                return -1;
            }
            mark[ai] = 1;
            found = 1;
        }
    }
    return found;
}

/* the start positions from the anchor marks: *starts (PyMem, may stay NULL) and *nstarts */
static int
anchor_starts(const char *mark, Py_ssize_t nnb, long anchor_index, long limit, long **starts, Py_ssize_t *nstarts)
{
    *starts = PyMem_Calloc(nnb + 1, sizeof(long));
    if (*starts == NULL) { PyErr_NoMemory(); return -1; }
    *nstarts = 0;
    for (Py_ssize_t ai = 0; ai < nnb; ai++) {
        if (!mark[ai]) continue;
        long s = (long)ai - anchor_index;
        if (s >= 0 && s < limit) (*starts)[(*nstarts)++] = s;
    }
    return 0;
}

/* runs the entry's pattern on the sentence. Returns the result of finish (a new
 * reference) if there was a match, Py_None (new reference) if not, NULL on
 * error. */
static PyObject *mt_run_entry(MTEntry *e, PyObject *sentence, SentenceHints *sh, SentenceTokens *st, int collect);

static PyObject *
mt_run(MTEntry *e, PyObject *sentence, SentenceHints *sh, SentenceTokens *st, int collect)
{
    /* a copy of the entry with strong references (the entry could be cleared while Python code runs) */
    MTEntry c = *e;
    Py_XINCREF(c.compiled); Py_XINCREF(c.on_match); Py_XINCREF(c.finish); Py_XINCREF(c.unify);
    Py_XINCREF(c.resolver); Py_XINCREF(c.anchor_values); Py_XINCREF(c.anchor_value_set);
    PyObject *r = mt_run_entry(&c, sentence, sh, st, collect);
    Py_XDECREF(c.compiled); Py_XDECREF(c.on_match); Py_XDECREF(c.finish); Py_XDECREF(c.unify);
    Py_XDECREF(c.resolver); Py_XDECREF(c.anchor_values); Py_XDECREF(c.anchor_value_set);
    return r;
}

static PyObject *
mt_run_entry(MTEntry *e, PyObject *sentence, SentenceHints *sh, SentenceTokens *st, int collect)
{
    PyObject *tokens, *copy;
    if (stoks_get(st, sentence, e->pre_disambig, &tokens, &copy) < 0) return NULL;
    Py_ssize_t ntokens = PyList_GET_SIZE(copy);
    long limit;
    if (e->sent_start) {
        limit = 1;
    } else {
        limit = (long)ntokens - e->pattern_size + 1;
        if (limit < 0) limit = 0;
        limit += e->moc;
    }
    long *starts = NULL;
    Py_ssize_t nstarts = 0;
    long from = 0, to = -1;
    int use_anchor = e->anchor_values != Py_None && !e->pre_disambig;
    if (use_anchor) {
        if (shints_load(sh, sentence) < 0) return NULL;
        PyObject *offsets = e->anchor_inflected ? sh->lo : sh->to;
        Py_ssize_t nnb = sh->nnb;
        char *mark = PyMem_Calloc(nnb + 1, 1);
        if (mark == NULL) return PyErr_NoMemory();
        int found = anchor_marks(mark, nnb, offsets, e->anchor_values, e->anchor_value_set, NULL, NULL, NULL);
        if (found < 0 || (found && anchor_starts(mark, nnb, e->anchor_index, limit, &starts, &nstarts) < 0)) {
            PyMem_Free(mark);
            return NULL;
        }
        PyMem_Free(mark);
        if (nstarts == 0) {
            PyMem_Free(starts);
            Py_RETURN_NONE;
        }
    } else {
        from = 0;
        to = limit - 1;
        if (from > to) Py_RETURN_NONE;
    }
    PyObject *scratch = NULL, *prefix = NULL, *results = NULL, *ret = NULL;
    scratch = PyList_New(0);
    if (scratch == NULL) goto done;
    prefix = PyTuple_Pack(3, sentence, tokens, scratch);
    if (prefix == NULL) goto done;
    if (collect) {
        results = PyList_New(0);
        if (results == NULL) goto done;
    }
    /* keep the token copy alive while the callbacks run */
    Py_INCREF(copy);
    Py_ssize_t nm = 0;
    int r = cp_run((CompiledPattern *)e->compiled, &PyList_GET_ITEM(copy, 0), ntokens, starts, nstarts, from, to,
                   e->on_match, prefix, results, e->unify, e->resolver, &nm);
    Py_DECREF(copy);
    if (r < 0) goto done;
    if (nm == 0) {
        ret = Py_None;
        Py_INCREF(ret);
    } else {
        ret = PyObject_CallFunctionObjArgs(e->finish, sentence, scratch, results != NULL ? results : Py_None, NULL);
    }
done:
    PyMem_Free(starts);
    Py_XDECREF(scratch);
    Py_XDECREF(prefix);
    Py_XDECREF(results);
    return ret;
}

/* --- the static entries --- */

typedef struct {
    MatcherTable *table;
    Py_ssize_t i;
    PyObject *callbacks;     /* callbacks(i) -> (on_match, finish, unify) */
    SCallbacks *cb;
    PyObject *hold[3];       /* strong references to the callbacks while running */
} SLoadArg;

static int
s_load_callbacks(void *argp)
{
    SLoadArg *a = argp;
    if (a->callbacks == NULL || a->callbacks == Py_None) {
        PyErr_SetString(PyExc_ValueError, "static rules matched without callbacks");
        return -1;
    }
    PyObject *idx = PyLong_FromSsize_t(a->i);
    if (idx == NULL) return -1;
    PyObject *t = PyObject_CallOneArg(a->callbacks, idx);
    Py_DECREF(idx);
    if (t == NULL) return -1;
    PyObject *on_match, *finish, *unify;
    if (!PyTuple_Check(t) || !PyArg_ParseTuple(t, "OOO;bad static callbacks", &on_match, &finish, &unify)) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_TypeError, "callbacks() must return a tuple");
        Py_DECREF(t);
        return -1;
    }
    for (int k = 0; k < 3; k++) {
        PyObject *v = k == 0 ? on_match : k == 1 ? finish : unify;
        Py_INCREF(v);
        Py_XSETREF(a->hold[k], v);
    }
    a->cb->on_match = a->hold[0];
    a->cb->finish = a->hold[1];
    a->cb->unify = a->hold[2];
    /* store them in the entry (if it is still there) */
    if (a->table->entries != NULL && a->i < a->table->n) {
        MTEntry *e = &a->table->entries[a->i];
        if (e->state == MT_STATIC || e->state == MT_STATIC_CB) {
            Py_INCREF(on_match); Py_XSETREF(e->on_match, on_match);
            Py_INCREF(finish); Py_XSETREF(e->finish, finish);
            Py_INCREF(unify); Py_XSETREF(e->unify, unify);
            e->state = MT_STATIC_CB;
        }
    }
    Py_DECREF(t);
    return 0;
}

/* runs the static rule i (state MT_STATIC or MT_STATIC_CB) on the sentence: the result of finish (new reference),
 * Py_None if there was no match, NULL on error */
static PyObject *
mt_run_static(MatcherTable *t, RuleSelector *sel, Py_ssize_t i, PyObject *sentence, SentenceHints *sh,
              SentenceTokens *st, int collect, PyObject *callbacks)
{
    StaticSeg *seg;
    uint32_t local;
    const rt_rule *r = rs_static_rule(sel, i, sel->seg_of[i], &seg, &local);
    RuleBlob *b = seg->blob;
    int pre = (r->flags & RF_PRE_DISAMBIGUATION) != 0;
    PyObject *tokens, *copy;
    if (stoks_get(st, sentence, pre, &tokens, &copy) < 0) return NULL;
    Py_ssize_t ntokens = PyList_GET_SIZE(copy);
    long limit;
    if (r->flags & RF_SENT_START) {
        limit = 1;
    } else {
        limit = (long)ntokens - (long)r->n_pt + 1;
        if (limit < 0) limit = 0;
        limit += r->moc;
    }
    long *starts = NULL;
    Py_ssize_t nstarts = 0;
    long from = 0, to = -1;
    if (r->anchor_hint >= 0 && !pre) {
        if (shints_load(sh, sentence) < 0) return NULL;
        const rt_hint *h = &b->hint[r->hints_off + r->anchor_hint];
        KeySet *ks = shints_keys(sh, h->kind == HINT_KIND_LEMMA ? KS_LEMMAS : KS_TOKENS);
        if (ks == NULL) return NULL;
        Py_ssize_t nnb = sh->nnb;
        char *mark = PyMem_Calloc(nnb + 1, 1);
        if (mark == NULL) return PyErr_NoMemory();
        int found = anchor_marks(mark, nnb, NULL, NULL, NULL, b, h, ks);
        if (found < 0 || (found && anchor_starts(mark, nnb, r->anchor_index, limit, &starts, &nstarts) < 0)) {
            PyMem_Free(mark);
            return NULL;
        }
        PyMem_Free(mark);
        if (nstarts == 0) {
            PyMem_Free(starts);
            Py_RETURN_NONE;
        }
    } else {
        from = 0;
        to = limit - 1;
        if (from > to) Py_RETURN_NONE;
    }
    MTEntry *e = &t->entries[i];
    SCallbacks cb;
    SLoadArg la;
    la.table = t;
    la.i = i;
    la.callbacks = callbacks;
    la.cb = &cb;
    la.hold[0] = la.hold[1] = la.hold[2] = NULL;
    if (e->state == MT_STATIC_CB) {
        for (int k = 0; k < 3; k++) {
            PyObject *v = k == 0 ? e->on_match : k == 1 ? e->finish : e->unify;
            Py_XINCREF(v);
            la.hold[k] = v;
        }
    }
    cb.on_match = la.hold[0];
    cb.finish = la.hold[1];
    cb.unify = la.hold[2];
    cb.load = s_load_callbacks;
    cb.arg = &la;
    cb.native = NULL;
    cb.narg = NULL;
    PyObject *scratch = NULL, *prefix = NULL, *results = NULL, *ret = NULL;
    scratch = PyList_New(0);
    if (scratch == NULL) goto done;
    prefix = PyTuple_Pack(3, sentence, tokens, scratch);
    if (prefix == NULL) goto done;
    if (collect) {
        results = PyList_New(0);
        if (results == NULL) goto done;
    }
    Py_INCREF(copy);
    Py_INCREF(b);
    Py_ssize_t nm = 0;
    int rr = s_run(b, r, &PyList_GET_ITEM(copy, 0), ntokens, starts, nstarts, from, to, &cb, prefix, results, &nm);
    Py_DECREF(b);
    Py_DECREF(copy);
    if (rr < 0) goto done;
    if (nm == 0) {
        ret = Py_None;
        Py_INCREF(ret);
    } else {
        if (cb.finish == NULL && s_load_callbacks(&la) < 0) goto done;
        ret = PyObject_CallFunctionObjArgs(cb.finish, sentence, scratch, results != NULL ? results : Py_None, NULL);
    }
done:
    PyMem_Free(starts);
    Py_XDECREF(scratch);
    Py_XDECREF(prefix);
    Py_XDECREF(results);
    for (int k = 0; k < 3; k++) Py_XDECREF(la.hold[k]);
    return ret;
}

/* a regular expression rule (state MT_REGEX): its expression is searched in sentence.text (like match_regex_rule);
 * if it is found, the rule's match (init(i)) is called. Returns the matches (new reference) or Py_None (no match) */
static PyObject *
mt_run_regex(MatcherTable *t, RuleSelector *sel, Py_ssize_t i, PyObject *sentence, PyObject *init)
{
    StaticSeg *seg;
    uint32_t local;
    const rt_rule *r = rs_static_rule(sel, i, sel->seg_of[i], &seg, &local);
    RuleBlob *b = seg->blob;
    MTEntry *e = &t->entries[i];
    if (e->compiled == NULL) {
        PyObject *pattern = rb_string(b, r->regex_pattern);
        if (pattern == NULL) return NULL;
        if (b->engine_hook == NULL) {
            PyErr_SetString(PyExc_RuntimeError, "rule tables: set_types() not called");
            return NULL;
        }
        PyObject *c = PyObject_CallFunction(b->engine_hook, "i(OI)", 2, pattern, r->regex_flags);
        if (c == NULL) return NULL;
        Py_XSETREF(e->compiled, c);
    }
    PyObject *compiled = e->compiled;
    Py_INCREF(compiled);
    PyObject *text = PyObject_GetAttr(sentence, str_text);
    if (text == NULL) { Py_DECREF(compiled); return NULL; }
    PyObject *ret = NULL;
    if (!PyUnicode_Check(text) || PyUnicode_GET_LENGTH(text) > 2000) {  /* RegexPatternRule.MAX_SENT_LENGTH */
        ret = Py_None;
        Py_INCREF(ret);
        goto done;
    }
    PyObject *m = PyObject_CallMethod(compiled, "search", "O", text);
    if (m == NULL) goto done;
    int found = m != Py_None;
    Py_DECREF(m);
    if (!found) {
        ret = Py_None;
        Py_INCREF(ret);
        goto done;
    }
    if (e->on_match == NULL) {
        PyObject *idx = PyLong_FromSsize_t(i);
        if (idx == NULL) goto done;
        PyObject *f = PyObject_CallOneArg(init, idx);
        Py_DECREF(idx);
        if (f == NULL) goto done;
        if (i >= t->n || t->entries == NULL) { Py_DECREF(f); PyErr_SetString(PyExc_RuntimeError, "table changed"); goto done; }
        e = &t->entries[i];
        Py_XSETREF(e->on_match, f);
    }
    PyObject *f = e->on_match;
    Py_INCREF(f);
    ret = PyObject_CallOneArg(f, sentence);
    Py_DECREF(f);
done:
    Py_DECREF(text);
    Py_DECREF(compiled);
    return ret;
}

static PyObject *str_check_cancelled_callback = NULL;

/* owner.check_cancelled_callback is set and returns true: 1, 0 if not, -1 on error */
static int
is_cancelled(PyObject *owner)
{
    if (owner == Py_None) return 0;
    PyObject *cb = PyObject_GetAttr(owner, str_check_cancelled_callback);
    if (cb == NULL) return -1;
    if (cb == Py_None) { Py_DECREF(cb); return 0; }
    PyObject *r = PyObject_CallNoArgs(cb);
    Py_DECREF(cb);
    if (r == NULL) return -1;
    int t = PyObject_IsTrue(r);
    Py_DECREF(r);
    return t;
}

/* the result of the (initialized) entry i for the sentence: the matches (match_sentence) or the new sentence
 * (disambiguate) as a new reference; Py_None if a matched entry had no match */
static PyObject *
rs_run_entry(RuleSelector *self, MatcherTable *t, MTEntry *e, Py_ssize_t i, PyObject *sentence, SentenceHints *sh,
             SentenceTokens *st, int collect, PyObject *init, PyObject *callbacks)
{
    switch (e->state) {
    case MT_SPEC:
        return mt_run(e, sentence, sh, st, collect);
    case MT_STATIC: case MT_STATIC_CB:
        return mt_run_static(t, self, i, sentence, sh, st, collect, callbacks);
    case MT_REGEX:
        return mt_run_regex(t, self, i, sentence, init);
    case MT_CALL: {
        PyObject *f = e->on_match;
        Py_INCREF(f);
        PyObject *r = PyObject_CallOneArg(f, sentence);
        Py_DECREF(f);
        return r;
    }
    default:
        return PyObject_CallOneArg(PyTuple_GET_ITEM(self->items, i), sentence);
    }
}

/* whether the entry state matches on its own (returns None when there was no match) */
#define MT_MATCHED_HERE(state) ((state) == MT_SPEC || (state) == MT_STATIC || (state) == MT_STATIC_CB || \
                                (state) == MT_REGEX)

/* match_sentence(sentence, table, init, owner, callbacks=None): the rule matches of the
 * selected rules (the items that are not None) for the sentence:
 *   for each rule: if owner.check_cancelled_callback is set and returns true,
 *   stop; if the hints show that the rule can be ignored, skip it; else add
 *   the matches of the rule (computed with the table's entry, or the result of
 *   item(sentence)). */
static PyObject *
rs_match_sentence(RuleSelector *self, PyObject *args)
{
    PyObject *sentence, *table, *init, *owner, *callbacks = Py_None;
    if (!PyArg_ParseTuple(args, "OO!OO|O", &sentence, &MatcherTableType, &table, &init, &owner, &callbacks))
        return NULL;
    MatcherTable *t = (MatcherTable *)table;
    if (t->n != self->n || self->items == NULL) {
        PyErr_SetString(PyExc_ValueError, "the matcher table does not fit the rule selector");
        return NULL;
    }
    SentenceHints sh;
    shints_init(&sh);
    char *mark = rs_select_marks(self, sentence, &sh);
    if (mark == NULL) { shints_clear(&sh); return NULL; }
    Py_INCREF(table);
    Py_INCREF(self);
    SentenceTokens st = {NULL, NULL, NULL, NULL, NULL};
    PyObject *out = PyList_New(0);
    if (out == NULL) goto error;
    for (Py_ssize_t i = 0; i < self->n; i++) {
        if (!mark[i]) continue;
        int32_t s = self->seg_of != NULL ? self->seg_of[i] : -1;
        if (s < 0 && PyTuple_GET_ITEM(self->items, i) == Py_None) continue;
        int c = is_cancelled(owner);
        if (c < 0) goto error;
        if (c) break;
        int ig = rs_ignorable(self, i, sentence, &sh);
        if (ig < 0) goto error;
        if (ig) continue;
        if (t->n != self->n) {
            PyErr_SetString(PyExc_RuntimeError, "the matcher table was changed");
            goto error;
        }
        MTEntry *e = mt_entry(t, self, i, init);
        if (e == NULL) goto error;
        char state = e->state;
        PyObject *res = rs_run_entry(self, t, e, i, sentence, &sh, &st, 1, init, callbacks);
        if (res == NULL) goto error;
        if (res != Py_None) {
            if (!PyList_Check(res)) {
                PyObject *l = PySequence_List(res);
                Py_DECREF(res);
                if (l == NULL) goto error;
                res = l;
            }
            Py_ssize_t len = PyList_GET_SIZE(out);
            if (PyList_SetSlice(out, len, len, res) < 0) { Py_DECREF(res); goto error; }
        } else if (!MT_MATCHED_HERE(state)) {
            Py_DECREF(res);
            PyErr_SetString(PyExc_TypeError, "a rule's match() returned None");
            goto error;
        }
        Py_DECREF(res);
    }
    shints_clear(&sh);
    stoks_clear(&st);
    PyMem_Free(mark);
    Py_DECREF(table);
    Py_DECREF(self);
    return out;
error:
    shints_clear(&sh);
    stoks_clear(&st);
    PyMem_Free(mark);
    Py_DECREF(table);
    Py_DECREF(self);
    Py_XDECREF(out);
    return NULL;
}

/* disambiguate(sentence, before_first=None, table=None, init=None, callbacks=None): for the
 * rules selected by the tokens of the sentence, in order: unless the hints of
 * the rule show that it can be ignored for the current sentence, sentence =
 * item(sentence) (or the result of the table's entry, see MatcherTable). If
 * before_first is given, sentence = before_first(sentence) before the first
 * rule is applied. Returns the final sentence. */
static PyObject *
rs_disambiguate(RuleSelector *self, PyObject *args)
{
    PyObject *sentence, *before_first = Py_None, *table = Py_None, *init = Py_None, *callbacks = Py_None;
    if (!PyArg_ParseTuple(args, "O|OOOO", &sentence, &before_first, &table, &init, &callbacks)) return NULL;
    if (self->items == NULL) {
        PyErr_SetString(PyExc_ValueError, "RuleSelector not initialized");
        return NULL;
    }
    if (table != Py_None) {
        if (!PyObject_TypeCheck(table, &MatcherTableType) || ((MatcherTable *)table)->n != self->n) {
            PyErr_SetString(PyExc_TypeError, "table must be a MatcherTable for the rule selector");
            return NULL;
        }
    } else if (self->nsegs > 0) {
        PyErr_SetString(PyExc_TypeError, "disambiguate() with static rules needs a MatcherTable");
        return NULL;
    }
    SentenceHints sh;
    shints_init(&sh);
    char *mark = rs_select_marks(self, sentence, &sh);
    if (mark == NULL) { shints_clear(&sh); return NULL; }
    Py_INCREF(table);
    Py_INCREF(self);
    SentenceTokens st = {NULL, NULL, NULL, NULL, NULL};
    PyObject *cur = sentence;
    Py_INCREF(cur);
    for (Py_ssize_t i = 0; i < self->n; i++) {
        if (!mark[i]) continue;
        int32_t s = self->seg_of != NULL ? self->seg_of[i] : -1;
        if (s < 0 && PyTuple_GET_ITEM(self->items, i) == Py_None) continue;
        int ig = rs_ignorable(self, i, cur, &sh);
        if (ig < 0) goto error;
        if (ig) continue;
        if (before_first != Py_None) {
            PyObject *b = PyObject_CallOneArg(before_first, cur);
            if (b == NULL) goto error;
            before_first = Py_None;
            Py_SETREF(cur, b);
            shints_clear(&sh);
            stoks_clear(&st);
        }
        MTEntry *e = NULL;
        if (table != Py_None) {
            MatcherTable *t = (MatcherTable *)table;
            if (t->n != self->n) {
                PyErr_SetString(PyExc_RuntimeError, "the matcher table was changed");
                goto error;
            }
            e = mt_entry(t, self, i, init);
            if (e == NULL) goto error;
        }
        PyObject *res;
        if (e != NULL && MT_MATCHED_HERE(e->state)) {
            res = rs_run_entry(self, (MatcherTable *)table, e, i, cur, &sh, &st, 0, init, callbacks);
            if (res == Py_None) {
                Py_DECREF(res);
                continue;
            }
        } else if (e != NULL && e->state == MT_CALL) {
            res = rs_run_entry(self, (MatcherTable *)table, e, i, cur, &sh, &st, 0, init, callbacks);
        } else {
            res = PyObject_CallOneArg(PyTuple_GET_ITEM(self->items, i), cur);
        }
        if (res == NULL) goto error;
        if (res != cur) {
            shints_clear(&sh);
            stoks_clear(&st);
        }
        Py_SETREF(cur, res);
    }
    shints_clear(&sh);
    stoks_clear(&st);
    PyMem_Free(mark);
    Py_DECREF(table);
    Py_DECREF(self);
    return cur;
error:
    shints_clear(&sh);
    stoks_clear(&st);
    PyMem_Free(mark);
    Py_DECREF(table);
    Py_DECREF(self);
    Py_DECREF(cur);
    return NULL;
}

static PyMethodDef rs_methods[] = {
    {"select", (PyCFunction)rs_select, METH_VARARGS, "The rules for a sentence"},
    {"disambiguate", (PyCFunction)rs_disambiguate, METH_VARARGS, "Apply the disambiguation rules to a sentence"},
    {"match_sentence", (PyCFunction)rs_match_sentence, METH_VARARGS, "The rule matches for a sentence"},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject RuleSelectorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.RuleSelector",
    .tp_basicsize = sizeof(RuleSelector),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)rs_init,
    .tp_dealloc = (destructor)rs_dealloc,
    .tp_traverse = (traverseproc)rs_traverse,
    .tp_clear = (inquiry)rs_clear,
    .tp_methods = rs_methods,
};

/* ------------------------------------------------------------------------ */
/* the activation of the static rules (JLanguageTool.ignore_rule and is_rule_active_for_level on the tables) */

/* RuleBlob.active_mask(first, n, disabled_rules, enabled_rules, disabled_categories, enabled_categories,
 * variant_enabled, variant_disabled, level): bytes, 1 for the active rules (level: 0 no level check, 1 the default
 * level, 2 another level) */
static PyObject *
rb_py_active_mask(RuleBlob *self, PyObject *args)
{
    unsigned int first, n;
    PyObject *dis_r, *en_r, *dis_c, *en_c, *v_en, *v_dis;
    int level;
    if (!PyArg_ParseTuple(args, "IIOOOOOOi", &first, &n, &dis_r, &en_r, &dis_c, &en_c, &v_en, &v_dis, &level))
        return NULL;
    if ((uint64_t)first + n > self->n_rule) {
        PyErr_SetString(PyExc_IndexError, "rule range out of range");
        return NULL;
    }
    PyObject *sets[6] = {dis_r, en_r, dis_c, en_c, v_en, v_dis};
    for (int k = 0; k < 6; k++) {
        if (!PyAnySet_Check(sets[k])) {
            PyErr_SetString(PyExc_TypeError, "sets expected");
            return NULL;
        }
    }
    int rules_cfg = PySet_GET_SIZE(dis_r) > 0 || PySet_GET_SIZE(en_r) > 0;
    int cats_cfg = PySet_GET_SIZE(dis_c) > 0 || PySet_GET_SIZE(en_c) > 0;
    int variant_cfg = PySet_GET_SIZE(v_en) > 0 || PySet_GET_SIZE(v_dis) > 0;
    PyObject *out = PyBytes_FromStringAndSize(NULL, n);
    if (out == NULL) return NULL;
    char *m = PyBytes_AS_STRING(out);
    for (uint32_t i = 0; i < n; i++) {
        const rt_rule *r = &self->rule[first + i];
        int default_off = (r->flags & RF_DEFAULT_OFF) != 0;
        PyObject *rid = NULL, *fid = NULL;
        int active;
        if (rules_cfg || variant_cfg) {
            rid = rb_string(self, r->id);
            if (rid == NULL) goto error;
            Py_INCREF(rid);
        }
        if (variant_cfg) {
            int on = PySet_Contains(v_en, rid);
            int off = PySet_Contains(v_dis, rid);
            if (on < 0 || off < 0) goto error_ids;
            if (on) default_off = 0;
            if (off) default_off = 1;
        }
        if (rules_cfg) {
            if (r->sub_id == RT_NONE) {
                fid = rid;
                Py_INCREF(fid);
            } else {
                PyObject *sub = rb_string(self, r->sub_id);
                if (sub == NULL) goto error_ids;
                fid = PyUnicode_FromFormat("%U[%U]", rid, sub);
                if (fid == NULL) goto error_ids;
            }
        }
        int cat_disabled;
        int cat_default_off = r->cat != RT_NONE && r->cat < self->n_cat && !self->cat[r->cat].default_on;
        if (cats_cfg) {
            PyObject *cid = Py_None;
            if (r->cat != RT_NONE && r->cat < self->n_cat && self->cat[r->cat].id != RT_NONE) {
                cid = rb_string(self, self->cat[r->cat].id);
                if (cid == NULL) goto error_ids;
            }
            int d = PySet_Contains(dis_c, cid);
            int e = PySet_Contains(en_c, cid);
            if (d < 0 || e < 0) goto error_ids;
            cat_disabled = (d || cat_default_off) && !e;
        } else {
            cat_disabled = cat_default_off;
        }
        int fe = 0, re = 0, fd = 0, rd = 0;
        if (rules_cfg) {
            if ((fe = PySet_Contains(en_r, fid)) < 0 || (re = PySet_Contains(en_r, rid)) < 0 ||
                    (fd = PySet_Contains(dis_r, fid)) < 0 || (rd = PySet_Contains(dis_r, rid)) < 0)
                goto error_ids;
        }
        if (cat_disabled) {
            active = fe || re;
        } else {
            active = !(fd || rd || (default_off && !(fe || re)));
        }
        if (active && level == 1 && (r->flags & RF_PICKY)) active = 0;
        if (active && level != 0 && r->n_tone_tags > 0 && (r->flags & RF_GOAL_SPECIFIC)) active = 0;
        m[i] = (char)active;
        Py_XDECREF(rid);
        Py_XDECREF(fid);
        continue;
error_ids:
        Py_XDECREF(rid);
        Py_XDECREF(fid);
        goto error;
    }
    return out;
error:
    Py_DECREF(out);
    return NULL;
}

/* RuleBlob.select_rules(first, n, ids, category_ids, id_prefix, min_prev_matches): the indices (relative to first)
 * of the rules whose id is in the set ids, or whose category id is in the set category_ids, or whose id starts with
 * id_prefix (a str or None), or (if min_prev_matches) whose min_prev_matches is > 0 */
static PyObject *
rb_py_select_rules(RuleBlob *self, PyObject *args)
{
    unsigned int first, n;
    PyObject *ids, *cats, *prefix;
    int mpm;
    if (!PyArg_ParseTuple(args, "IIOOOp", &first, &n, &ids, &cats, &prefix, &mpm)) return NULL;
    if ((uint64_t)first + n > self->n_rule) {
        PyErr_SetString(PyExc_IndexError, "rule range out of range");
        return NULL;
    }
    if ((ids != Py_None && !PyAnySet_Check(ids)) || (cats != Py_None && !PyAnySet_Check(cats)) ||
            (prefix != Py_None && !PyUnicode_Check(prefix))) {
        PyErr_SetString(PyExc_TypeError, "sets and a str expected");
        return NULL;
    }
    PyObject *out = PyList_New(0);
    if (out == NULL) return NULL;
    for (uint32_t i = 0; i < n; i++) {
        const rt_rule *r = &self->rule[first + i];
        int hit = mpm && r->min_prev_matches > 0;
        if (!hit && ((ids != Py_None && PySet_GET_SIZE(ids) > 0) || prefix != Py_None)) {
            PyObject *rid = rb_string(self, r->id);
            if (rid == NULL) goto error;
            if (ids != Py_None && PySet_GET_SIZE(ids) > 0) {
                int c = PySet_Contains(ids, rid);
                if (c < 0) goto error;
                hit = c;
            }
            if (!hit && prefix != Py_None) {
                Py_ssize_t t = PyUnicode_Tailmatch(rid, prefix, 0, PY_SSIZE_T_MAX, -1);
                if (t < 0) goto error;
                hit = t > 0;
            }
        }
        if (!hit && cats != Py_None && PySet_GET_SIZE(cats) > 0 && r->cat != RT_NONE && r->cat < self->n_cat &&
                self->cat[r->cat].id != RT_NONE) {
            PyObject *cid = rb_string(self, self->cat[r->cat].id);
            if (cid == NULL) goto error;
            int c = PySet_Contains(cats, cid);
            if (c < 0) goto error;
            hit = c;
        }
        if (hit) {
            PyObject *v = PyLong_FromUnsignedLong(i);
            if (v == NULL || PyList_Append(out, v) < 0) { Py_XDECREF(v); goto error; }
            Py_DECREF(v);
        }
    }
    return out;
error:
    Py_DECREF(out);
    return NULL;
}

/* RuleBlob.rule_ids(first, n, mask): the set of the ids of the rules i with mask[i] (mask: bytes of length n) */
static PyObject *
rb_py_rule_ids(RuleBlob *self, PyObject *args)
{
    unsigned int first, n;
    Py_buffer mask;
    if (!PyArg_ParseTuple(args, "IIy*", &first, &n, &mask)) return NULL;
    if ((uint64_t)first + n > self->n_rule || mask.len != (Py_ssize_t)n) {
        PyBuffer_Release(&mask);
        PyErr_SetString(PyExc_ValueError, "bad rule range or mask");
        return NULL;
    }
    PyObject *out = PySet_New(NULL);
    if (out == NULL) { PyBuffer_Release(&mask); return NULL; }
    const char *m = mask.buf;
    for (uint32_t i = 0; i < n; i++) {
        if (!m[i]) continue;
        PyObject *rid = rb_string(self, self->rule[first + i].id);
        if (rid == NULL || PySet_Add(out, rid) < 0) { PyBuffer_Release(&mask); Py_DECREF(out); return NULL; }
    }
    PyBuffer_Release(&mask);
    return out;
}


/* ------------------------------------------------------------------------ */
/* the anti-patterns of a static rule on the tables (Rule.get_sentence_with_immunization and the matching again,
 * PatternRule.apply_anti_patterns) */

static PyObject *str_get_original_position = NULL;
static PyObject *str_immunize = NULL;
static PyObject *str_tokens = NULL;

/* the state of the application of an anti-pattern (DisambiguationPatternRuleReplacer._c_on_match / _c_finish with
 * the IMMUNIZE action) */
typedef struct {
    const rt_rule *ap;
    PyObject *sentence;     /* borrowed: the current sentence */
    PyObject *wh_tokens;    /* the new token list (scratch[0]) or NULL */
    int changed;            /* scratch[1] */
} ImmunizeState;

static PyObject *
call_orig(PyObject *sentence, long pos)
{
    PyObject *p = PyLong_FromLong(pos);
    if (p == NULL) return NULL;
    PyObject *r = PyObject_CallMethodOneArg(sentence, str_get_original_position, p);
    Py_DECREF(p);
    return r;
}

/* execute_action() for IMMUNIZE (see DisambiguationPatternRuleReplacer.execute_action) */
static int
immunize_on_match(void *narg, const int *positions, Py_ssize_t npos, int first, int last, int first_marker,
                  int last_marker)
{
    (void)last;
    (void)first_marker;
    ImmunizeState *is = narg;
    const rt_rule *rule = is->ap;
    if (is->wh_tokens == NULL) {
        is->wh_tokens = PyObject_GetAttr(is->sentence, str_tokens);
        if (is->wh_tokens == NULL) return -1;
        is->changed = 0;
    }
    Py_ssize_t matching_tokens = 0;
    for (Py_ssize_t i = 0; i < npos; i++) {
        if (positions[i] != 0) matching_tokens++;
    }
    if (!is->changed) {
        PyObject *l = PySequence_List(is->wh_tokens);
        if (l == NULL) return -1;
        Py_SETREF(is->wh_tokens, l);
    }
    long corrected = 0;
    long spc = rule->spc, epc = rule->epc;
    long mtwc = (long)matching_tokens;
    if (spc > 0) {
        corrected -= 1;
        for (long l = 0; l <= spc && l < npos; l++) corrected += positions[l];
        long w = spc;
        for (long j = 0; j <= w; j++) {
            if (j < npos && positions[j] == 0) spc -= 1;
        }
    }
    if (epc < 0) {
        for (long d = spc; d < npos; d++) {
            /* (Python indexing: a negative index counts from the end) */
            Py_ssize_t k = d < 0 ? d + npos : d;
            if (k < 0 || k >= npos) {
                PyErr_SetString(PyExc_IndexError, "list index out of range");
                return -1;
            }
            if (positions[k] == 0) epc += 1;
        }
    }
    if (last_marker != -1) {
        long max_pos_corr = ((long)last_marker + 1 - ((long)first + corrected)) - (long)matching_tokens;
        if (max_pos_corr < 0) max_pos_corr = 0;
        mtwc += max_pos_corr;
    }
    PyObject *from_pos = call_orig(is->sentence, (long)first + corrected);
    if (from_pos == NULL) return -1;
    Py_DECREF(from_pos);
    long count = mtwc - spc + epc;
    PyObject *line = PyLong_FromLong(rule->xml_line);
    if (line == NULL) return -1;
    for (long i = 0; i < count; i++) {
        PyObject *pos = call_orig(is->sentence, (long)first + corrected + i);
        if (pos == NULL) { Py_DECREF(line); return -1; }
        PyObject *tok = PyObject_GetItem(is->wh_tokens, pos);
        Py_DECREF(pos);
        if (tok == NULL) { Py_DECREF(line); return -1; }
        PyObject *r = PyObject_CallMethodOneArg(tok, str_immunize, line);
        Py_DECREF(tok);
        if (r == NULL) { Py_DECREF(line); return -1; }
        Py_DECREF(r);
    }
    Py_DECREF(line);
    is->changed = 1;
    return 0;
}

typedef struct {
    PyObject *ap_unify;   /* callable(k) -> the unify callback of the anti-pattern k */
    Py_ssize_t k;
    SCallbacks *cb;
    PyObject *hold;
} ApUnifyArg;

static int
ap_load_unify(void *argp)
{
    ApUnifyArg *a = argp;
    PyObject *idx = PyLong_FromSsize_t(a->k);
    if (idx == NULL) return -1;
    PyObject *u = PyObject_CallOneArg(a->ap_unify, idx);
    Py_DECREF(idx);
    if (u == NULL) return -1;
    Py_XSETREF(a->hold, u);
    a->cb->unify = u;
    return 0;
}

/* the start positions of a static rule for the sentence (like do_match): *starts / *nstarts, or the range from..to;
 * returns 1 if there are positions to try, 0 if not, -1 on error */
static int
s_starts(RuleBlob *b, const rt_rule *r, PyObject *sentence, Py_ssize_t ntokens, SentenceHints *sh, long **starts,
         Py_ssize_t *nstarts, long *from, long *to)
{
    int pre = (r->flags & RF_PRE_DISAMBIGUATION) != 0;
    long limit;
    if (r->flags & RF_SENT_START) {
        limit = 1;
    } else {
        limit = (long)ntokens - (long)r->n_pt + 1;
        if (limit < 0) limit = 0;
        limit += r->moc;
    }
    *starts = NULL;
    *nstarts = 0;
    if (r->anchor_hint >= 0 && !pre) {
        if (shints_load(sh, sentence) < 0) return -1;
        const rt_hint *h = &b->hint[r->hints_off + r->anchor_hint];
        KeySet *ks = shints_keys(sh, h->kind == HINT_KIND_LEMMA ? KS_LEMMAS : KS_TOKENS);
        if (ks == NULL) return -1;
        Py_ssize_t nnb = sh->nnb;
        char *mark = PyMem_Calloc(nnb + 1, 1);
        if (mark == NULL) { PyErr_NoMemory(); return -1; }
        int found = anchor_marks(mark, nnb, NULL, NULL, NULL, b, h, ks);
        if (found < 0 || (found && anchor_starts(mark, nnb, r->anchor_index, limit, starts, nstarts) < 0)) {
            PyMem_Free(mark);
            return -1;
        }
        PyMem_Free(mark);
        if (*nstarts == 0) {
            PyMem_Free(*starts);
            *starts = NULL;
            return 0;
        }
        return 1;
    }
    *from = 0;
    *to = limit - 1;
    return *from <= *to;
}

/* RuleBlob.immunize(rule, sentence, copy, sentence_class, ap_unify): Rule.get_sentence_with_immunization for the
 * static rule (index) whose anti-patterns are all plain immunizations (else NotImplemented): the immunized copy of
 * the sentence, or the sentence itself if no anti-pattern can match. copy(sentence) copies the sentence,
 * sentence_class(tokens, pre_disambig_tokens, previous, readings_unchanged) creates one, ap_unify(k) gives the
 * unify callback of the anti-pattern k (for the anti-patterns with unification) */
static PyObject *
rb_py_immunize(RuleBlob *self, PyObject *args)
{
    unsigned int ri;
    PyObject *sentence, *copy, *cls, *ap_unify;
    if (!PyArg_ParseTuple(args, "IOOOO", &ri, &sentence, &copy, &cls, &ap_unify)) return NULL;
    if (ri >= self->n_rule) {
        PyErr_SetString(PyExc_IndexError, "rule index out of range");
        return NULL;
    }
    const rt_rule *r = &self->rule[ri];
    if ((uint64_t)r->ap_off + r->n_ap > self->n_idx) {
        PyErr_SetString(PyExc_ValueError, "rule tables: bad anti-patterns");
        return NULL;
    }
    for (uint32_t k = 0; k < r->n_ap; k++) {
        uint32_t ai = self->idx[r->ap_off + k];
        if (ai >= self->n_rule) {
            PyErr_SetString(PyExc_ValueError, "rule tables: bad anti-pattern");
            return NULL;
        }
        const rt_rule *ap = &self->rule[ai];
        if (!(ap->flags & RF_PLAIN_IMMUNIZE) || (ap->flags & RF_REFERENCES) || !(ap->flags & RF_HINTS))
            Py_RETURN_NOTIMPLEMENTED;
    }
    Py_INCREF(self);
    SentenceHints sh;
    shints_init(&sh);
    SentenceTokens st = {NULL, NULL, NULL, NULL, NULL};
    PyObject *cur = sentence;
    Py_INCREF(cur);
    int copied = 0;
    for (uint32_t k = 0; k < r->n_ap; k++) {
        const rt_rule *ap = &self->rule[self->idx[r->ap_off + k]];
        if (shints_load(&sh, cur) < 0) goto error;
        int ig = static_rh_check(self, ap, &sh);
        if (ig < 0) goto error;
        if (ig) continue;
        if (!copied) {
            PyObject *c = PyObject_CallOneArg(copy, cur);
            if (c == NULL) goto error;
            Py_SETREF(cur, c);
            copied = 1;
            shints_clear(&sh);
            stoks_clear(&st);
        }
        PyObject *tokens, *tcopy;
        if (stoks_get(&st, cur, 0, &tokens, &tcopy) < 0) goto error;
        Py_ssize_t ntokens = PyList_GET_SIZE(tcopy);
        long *starts = NULL;
        Py_ssize_t nstarts = 0;
        long from = 0, to = -1;
        int any = s_starts(self, ap, cur, ntokens, &sh, &starts, &nstarts, &from, &to);
        if (any < 0) goto error;
        if (!any) continue;
        ImmunizeState is = {ap, cur, NULL, 0};
        SCallbacks cb;
        ApUnifyArg ua = {ap_unify, (Py_ssize_t)k, &cb, NULL};
        cb.on_match = cb.finish = cb.unify = NULL;
        cb.load = ap_load_unify;
        cb.arg = &ua;
        cb.native = immunize_on_match;
        cb.narg = &is;
        Py_ssize_t nm = 0;
        Py_INCREF(tcopy);
        int rr = s_run(self, ap, &PyList_GET_ITEM(tcopy, 0), ntokens, starts, nstarts, from, to, &cb, NULL, NULL, &nm);
        Py_DECREF(tcopy);
        PyMem_Free(starts);
        Py_XDECREF(ua.hold);
        if (rr < 0) { Py_XDECREF(is.wh_tokens); goto error; }
        if (is.changed) {
            /* AnalyzedSentence(scratch[0], sentence.tokens, sentence, True) */
            PyObject *orig_tokens = PyObject_GetAttr(cur, str_tokens);
            if (orig_tokens == NULL) { Py_XDECREF(is.wh_tokens); goto error; }
            PyObject *ns = PyObject_CallFunctionObjArgs(cls, is.wh_tokens, orig_tokens, cur, Py_True, NULL);
            Py_DECREF(orig_tokens);
            Py_XDECREF(is.wh_tokens);
            if (ns == NULL) goto error;
            if (ns != cur) {
                shints_clear(&sh);
                stoks_clear(&st);
            }
            Py_SETREF(cur, ns);
        } else {
            Py_XDECREF(is.wh_tokens);
        }
    }
    shints_clear(&sh);
    stoks_clear(&st);
    Py_DECREF(self);
    return cur;
error:
    shints_clear(&sh);
    stoks_clear(&st);
    Py_DECREF(self);
    Py_DECREF(cur);
    return NULL;
}

/* RuleBlob.run_rule(rule, sentence, on_match, unify): the results (not None) of on_match(sentence, tokens, scratch,
 * positions, first, last, first_marker, last_marker) for the matches of the static rule (index) in the sentence
 * (like the matcher's do_match; unify: the unify callback, None for the rules without unification) */
static PyObject *
rb_py_run_rule(RuleBlob *self, PyObject *args)
{
    unsigned int ri;
    PyObject *sentence, *on_match, *unify;
    if (!PyArg_ParseTuple(args, "IOOO", &ri, &sentence, &on_match, &unify)) return NULL;
    if (ri >= self->n_rule) {
        PyErr_SetString(PyExc_IndexError, "rule index out of range");
        return NULL;
    }
    const rt_rule *r = &self->rule[ri];
    if (r->kind == RULE_KIND_REGEX || (r->flags & RF_REFERENCES)) {
        PyErr_SetString(PyExc_ValueError, "run_rule() of a rule that is matched with its objects");
        return NULL;
    }
    if ((r->flags & RF_TEST_UNIFICATION) && unify == Py_None) {
        PyErr_SetString(PyExc_ValueError, "a rule with unification without the unify callback");
        return NULL;
    }
    Py_INCREF(self);
    SentenceHints sh;
    shints_init(&sh);
    SentenceTokens st = {NULL, NULL, NULL, NULL, NULL};
    PyObject *results = PyList_New(0), *scratch = NULL, *prefix = NULL;
    long *starts = NULL;
    if (results == NULL) goto error;
    PyObject *tokens, *tcopy;
    if (stoks_get(&st, sentence, (r->flags & RF_PRE_DISAMBIGUATION) != 0, &tokens, &tcopy) < 0) goto error;
    Py_ssize_t ntokens = PyList_GET_SIZE(tcopy);
    Py_ssize_t nstarts = 0;
    long from = 0, to = -1;
    int any = s_starts(self, r, sentence, ntokens, &sh, &starts, &nstarts, &from, &to);
    if (any < 0) goto error;
    if (any) {
        scratch = PyList_New(0);
        if (scratch == NULL) goto error;
        prefix = PyTuple_Pack(3, sentence, tokens, scratch);
        if (prefix == NULL) goto error;
        SCallbacks cb;
        cb.on_match = on_match;
        cb.finish = NULL;
        cb.unify = unify;
        cb.load = NULL;
        cb.arg = NULL;
        cb.native = NULL;
        cb.narg = NULL;
        Py_ssize_t nm = 0;
        Py_INCREF(tcopy);
        int rr = s_run(self, r, &PyList_GET_ITEM(tcopy, 0), ntokens, starts, nstarts, from, to, &cb, prefix, results,
                       &nm);
        Py_DECREF(tcopy);
        if (rr < 0) goto error;
    }
    PyMem_Free(starts);
    Py_XDECREF(scratch);
    Py_XDECREF(prefix);
    shints_clear(&sh);
    stoks_clear(&st);
    Py_DECREF(self);
    return results;
error:
    PyMem_Free(starts);
    Py_XDECREF(scratch);
    Py_XDECREF(prefix);
    Py_XDECREF(results);
    shints_clear(&sh);
    stoks_clear(&st);
    Py_DECREF(self);
    return NULL;
}
