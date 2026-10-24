/*
 * _speedups.c
 * C implementation of the hot spots of the langtool package:
 *
 *  - base types for the data model (AnalyzedToken, AnalyzedTokenReadings,
 *    StringMatcher, PosToken, PatternToken) so that the matcher can access
 *    their fields directly. The Python classes subclass these.
 *  - the pattern matching loop (port of AbstractPatternRulePerformer.matchFrom
 *    and testAllReadings of LanguageTool).
 *  - lookups in morfologik FSA dictionaries.
 *
 * The pure Python implementation in the package is the reference, this code
 * must behave identically.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#include <string.h>
#include <math.h>

#define MAX_MATCH_LENGTH 250
#define KIND_EQUALS 0
#define KIND_SET 1
#define KIND_REGEX 2

static PyObject *str_lower = NULL;          /* "lower" */
static PyObject *str_regex_match = NULL;    /* "_regex_match" */
static PyObject *str_chunk_tag = NULL;      /* "chunk_tag" */
static PyObject *str_matches = NULL;        /* "matches" */
static PyObject *str_is_regexp = NULL;      /* "is_regexp" */

/* ------------------------------------------------------------------------ */
/* AnalyzedTokenBase */

typedef struct {
    PyObject_HEAD
    PyObject *token;
    PyObject *pos_tag;
    PyObject *lemma;
    PyObject *lemma_or_token;
    PyObject *lemma_or_token_lower;
    PyObject *token_lower;
    PyObject *lemma_lower;
    char whitespace_before;
    char has_no_pos_tag;
} AnalyzedTokenBase;

static int
at_traverse(AnalyzedTokenBase *self, visitproc visit, void *arg)
{
    Py_VISIT(self->token); Py_VISIT(self->pos_tag); Py_VISIT(self->lemma); Py_VISIT(self->lemma_or_token);
    Py_VISIT(self->lemma_or_token_lower); Py_VISIT(self->token_lower); Py_VISIT(self->lemma_lower);
    return 0;
}

static int
at_clear(AnalyzedTokenBase *self)
{
    Py_CLEAR(self->token); Py_CLEAR(self->pos_tag); Py_CLEAR(self->lemma); Py_CLEAR(self->lemma_or_token);
    Py_CLEAR(self->lemma_or_token_lower); Py_CLEAR(self->token_lower); Py_CLEAR(self->lemma_lower);
    return 0;
}

static void
at_dealloc(AnalyzedTokenBase *self)
{
    PyObject_GC_UnTrack(self);
    at_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyMemberDef at_members[] = {
    {"token", T_OBJECT, offsetof(AnalyzedTokenBase, token), 0, NULL},
    {"pos_tag", T_OBJECT, offsetof(AnalyzedTokenBase, pos_tag), 0, NULL},
    {"lemma", T_OBJECT, offsetof(AnalyzedTokenBase, lemma), 0, NULL},
    {"lemma_or_token", T_OBJECT, offsetof(AnalyzedTokenBase, lemma_or_token), 0, NULL},
    {"_lemma_or_token_lower", T_OBJECT, offsetof(AnalyzedTokenBase, lemma_or_token_lower), 0, NULL},
    {"_token_lower", T_OBJECT, offsetof(AnalyzedTokenBase, token_lower), 0, NULL},
    {"_lemma_lower", T_OBJECT, offsetof(AnalyzedTokenBase, lemma_lower), 0, NULL},
    {"whitespace_before", T_BOOL, offsetof(AnalyzedTokenBase, whitespace_before), 0, NULL},
    {"has_no_pos_tag", T_BOOL, offsetof(AnalyzedTokenBase, has_no_pos_tag), 0, NULL},
    {NULL}
};

static PyTypeObject AnalyzedTokenBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.AnalyzedTokenBase",
    .tp_basicsize = sizeof(AnalyzedTokenBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)at_dealloc,
    .tp_traverse = (traverseproc)at_traverse,
    .tp_clear = (inquiry)at_clear,
    .tp_members = at_members,
};

#define AT(o) ((AnalyzedTokenBase *)(o))

/* ------------------------------------------------------------------------ */
/* AnalyzedTokenReadingsBase */

typedef struct {
    PyObject_HEAD
    PyObject *readings;   /* list */
    PyObject *token;
    PyObject *token_lower;
    PyObject *chunk_tags; /* tuple */
    char is_whitespace;
    char is_linebreak;
    char is_sentence_start;
    char is_pos_tag_unknown;
    char is_sentence_end;
    char is_paragraph_end;
    char whitespace_before;
    char immunized;
    char has_same_lemmas;
    char ignored_by_speller;
    char typographic_apostrophe;
} ATRBase;

static int
atr_traverse(ATRBase *self, visitproc visit, void *arg)
{
    Py_VISIT(self->readings); Py_VISIT(self->token); Py_VISIT(self->token_lower); Py_VISIT(self->chunk_tags);
    return 0;
}

static int
atr_clear(ATRBase *self)
{
    Py_CLEAR(self->readings); Py_CLEAR(self->token); Py_CLEAR(self->token_lower); Py_CLEAR(self->chunk_tags);
    return 0;
}

static void
atr_dealloc(ATRBase *self)
{
    PyObject_GC_UnTrack(self);
    atr_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyMemberDef atr_members[] = {
    {"readings", T_OBJECT, offsetof(ATRBase, readings), 0, NULL},
    {"token", T_OBJECT, offsetof(ATRBase, token), 0, NULL},
    {"_token_lower", T_OBJECT, offsetof(ATRBase, token_lower), 0, NULL},
    {"chunk_tags", T_OBJECT, offsetof(ATRBase, chunk_tags), 0, NULL},
    {"is_whitespace", T_BOOL, offsetof(ATRBase, is_whitespace), 0, NULL},
    {"is_linebreak", T_BOOL, offsetof(ATRBase, is_linebreak), 0, NULL},
    {"is_sentence_start", T_BOOL, offsetof(ATRBase, is_sentence_start), 0, NULL},
    {"is_pos_tag_unknown", T_BOOL, offsetof(ATRBase, is_pos_tag_unknown), 0, NULL},
    {"is_sentence_end", T_BOOL, offsetof(ATRBase, is_sentence_end), 0, NULL},
    {"is_paragraph_end", T_BOOL, offsetof(ATRBase, is_paragraph_end), 0, NULL},
    {"whitespace_before", T_BOOL, offsetof(ATRBase, whitespace_before), 0, NULL},
    {"immunized", T_BOOL, offsetof(ATRBase, immunized), 0, NULL},
    {"has_same_lemmas", T_BOOL, offsetof(ATRBase, has_same_lemmas), 0, NULL},
    {"ignored_by_speller", T_BOOL, offsetof(ATRBase, ignored_by_speller), 0, NULL},
    {"typographic_apostrophe", T_BOOL, offsetof(ATRBase, typographic_apostrophe), 0, NULL},
    {NULL}
};

static PyTypeObject ATRBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.AnalyzedTokenReadingsBase",
    .tp_basicsize = sizeof(ATRBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)atr_dealloc,
    .tp_traverse = (traverseproc)atr_traverse,
    .tp_clear = (inquiry)atr_clear,
    .tp_members = atr_members,
};

#define ATR(o) ((ATRBase *)(o))

/* ------------------------------------------------------------------------ */
/* StringMatcherBase */

typedef struct {
    PyObject_HEAD
    PyObject *pattern;
    PyObject *value;
    PyObject *value_lower;
    PyObject *values;    /* frozenset or None */
    PyObject *compiled;
    PyObject *cache;     /* dict or None */
    PyObject *possible_values;
    int kind;
    char case_sensitive;
    char is_regexp;
} StringMatcherBase;

static int
sm_traverse(StringMatcherBase *self, visitproc visit, void *arg)
{
    Py_VISIT(self->pattern); Py_VISIT(self->value); Py_VISIT(self->value_lower); Py_VISIT(self->values);
    Py_VISIT(self->compiled); Py_VISIT(self->cache); Py_VISIT(self->possible_values);
    return 0;
}

static int
sm_clear(StringMatcherBase *self)
{
    Py_CLEAR(self->pattern); Py_CLEAR(self->value); Py_CLEAR(self->value_lower); Py_CLEAR(self->values);
    Py_CLEAR(self->compiled); Py_CLEAR(self->cache); Py_CLEAR(self->possible_values);
    return 0;
}

static void
sm_dealloc(StringMatcherBase *self)
{
    PyObject_GC_UnTrack(self);
    sm_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyMemberDef sm_members[] = {
    {"pattern", T_OBJECT, offsetof(StringMatcherBase, pattern), 0, NULL},
    {"value", T_OBJECT, offsetof(StringMatcherBase, value), 0, NULL},
    {"value_lower", T_OBJECT, offsetof(StringMatcherBase, value_lower), 0, NULL},
    {"values", T_OBJECT, offsetof(StringMatcherBase, values), 0, NULL},
    {"compiled", T_OBJECT, offsetof(StringMatcherBase, compiled), 0, NULL},
    {"cache", T_OBJECT, offsetof(StringMatcherBase, cache), 0, NULL},
    {"possible_values", T_OBJECT, offsetof(StringMatcherBase, possible_values), 0, NULL},
    {"kind", T_INT, offsetof(StringMatcherBase, kind), 0, NULL},
    {"case_sensitive", T_BOOL, offsetof(StringMatcherBase, case_sensitive), 0, NULL},
    {"is_regexp", T_BOOL, offsetof(StringMatcherBase, is_regexp), 0, NULL},
    {NULL}
};

static PyTypeObject StringMatcherBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.StringMatcherBase",
    .tp_basicsize = sizeof(StringMatcherBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)sm_dealloc,
    .tp_traverse = (traverseproc)sm_traverse,
    .tp_clear = (inquiry)sm_clear,
    .tp_members = sm_members,
};

#define SM(o) ((StringMatcherBase *)(o))

/* ------------------------------------------------------------------------ */
/* PosTokenBase */

typedef struct {
    PyObject_HEAD
    PyObject *pos_tag;
    PyObject *pos_pattern;
    char negation;
    char pos_unknown;
} PosTokenBase;

static int
pos_traverse(PosTokenBase *self, visitproc visit, void *arg)
{
    Py_VISIT(self->pos_tag); Py_VISIT(self->pos_pattern);
    return 0;
}

static int
pos_clear(PosTokenBase *self)
{
    Py_CLEAR(self->pos_tag); Py_CLEAR(self->pos_pattern);
    return 0;
}

static void
pos_dealloc(PosTokenBase *self)
{
    PyObject_GC_UnTrack(self);
    pos_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyMemberDef pos_members[] = {
    {"pos_tag", T_OBJECT, offsetof(PosTokenBase, pos_tag), 0, NULL},
    {"pos_pattern", T_OBJECT, offsetof(PosTokenBase, pos_pattern), 0, NULL},
    {"negation", T_BOOL, offsetof(PosTokenBase, negation), 0, NULL},
    {"pos_unknown", T_BOOL, offsetof(PosTokenBase, pos_unknown), 0, NULL},
    {NULL}
};

static PyTypeObject PosTokenBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.PosTokenBase",
    .tp_basicsize = sizeof(PosTokenBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)pos_dealloc,
    .tp_traverse = (traverseproc)pos_traverse,
    .tp_clear = (inquiry)pos_clear,
    .tp_members = pos_members,
};

#define POS(o) ((PosTokenBase *)(o))

/* ------------------------------------------------------------------------ */
/* PatternTokenBase */

typedef struct {
    PyObject_HEAD
    PyObject *text_matcher;
    PyObject *pos_token;
    PyObject *current_and_next_exceptions;  /* tuple */
    PyObject *previous_exceptions;          /* tuple */
    PyObject *unification_features;
    PyObject *phrase_name;
    PyObject *and_group;                    /* list or None */
    PyObject *or_group;
    PyObject *token_reference;
    PyObject *chunk_tag;
    int skip;
    int max_occurrence;
    char inflected;
    char negation;
    char test_whitespace;
    char whitespace_before;
    char inside_marker;
    char exception_valid_next;
    char may_be_omitted;
    char test_string;
    char unification_neutral;
    char uni_negation;
    char last_in_unification;
} PatternTokenBase;

static int
pt_traverse(PatternTokenBase *self, visitproc visit, void *arg)
{
    Py_VISIT(self->text_matcher); Py_VISIT(self->pos_token); Py_VISIT(self->current_and_next_exceptions);
    Py_VISIT(self->previous_exceptions); Py_VISIT(self->unification_features); Py_VISIT(self->phrase_name);
    Py_VISIT(self->and_group); Py_VISIT(self->or_group); Py_VISIT(self->token_reference); Py_VISIT(self->chunk_tag);
    return 0;
}

static int
pt_clear(PatternTokenBase *self)
{
    Py_CLEAR(self->text_matcher); Py_CLEAR(self->pos_token); Py_CLEAR(self->current_and_next_exceptions);
    Py_CLEAR(self->previous_exceptions); Py_CLEAR(self->unification_features); Py_CLEAR(self->phrase_name);
    Py_CLEAR(self->and_group); Py_CLEAR(self->or_group); Py_CLEAR(self->token_reference); Py_CLEAR(self->chunk_tag);
    return 0;
}

static void
pt_dealloc(PatternTokenBase *self)
{
    PyObject_GC_UnTrack(self);
    pt_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyMemberDef pt_members[] = {
    {"text_matcher", T_OBJECT, offsetof(PatternTokenBase, text_matcher), 0, NULL},
    {"pos_token", T_OBJECT, offsetof(PatternTokenBase, pos_token), 0, NULL},
    {"current_and_next_exceptions", T_OBJECT, offsetof(PatternTokenBase, current_and_next_exceptions), 0, NULL},
    {"previous_exceptions", T_OBJECT, offsetof(PatternTokenBase, previous_exceptions), 0, NULL},
    {"unification_features", T_OBJECT, offsetof(PatternTokenBase, unification_features), 0, NULL},
    {"phrase_name", T_OBJECT, offsetof(PatternTokenBase, phrase_name), 0, NULL},
    {"and_group", T_OBJECT, offsetof(PatternTokenBase, and_group), 0, NULL},
    {"or_group", T_OBJECT, offsetof(PatternTokenBase, or_group), 0, NULL},
    {"token_reference", T_OBJECT, offsetof(PatternTokenBase, token_reference), 0, NULL},
    {"chunk_tag", T_OBJECT, offsetof(PatternTokenBase, chunk_tag), 0, NULL},
    {"skip", T_INT, offsetof(PatternTokenBase, skip), 0, NULL},
    {"max_occurrence", T_INT, offsetof(PatternTokenBase, max_occurrence), 0, NULL},
    {"inflected", T_BOOL, offsetof(PatternTokenBase, inflected), 0, NULL},
    {"negation", T_BOOL, offsetof(PatternTokenBase, negation), 0, NULL},
    {"test_whitespace", T_BOOL, offsetof(PatternTokenBase, test_whitespace), 0, NULL},
    {"whitespace_before", T_BOOL, offsetof(PatternTokenBase, whitespace_before), 0, NULL},
    {"inside_marker", T_BOOL, offsetof(PatternTokenBase, inside_marker), 0, NULL},
    {"exception_valid_next", T_BOOL, offsetof(PatternTokenBase, exception_valid_next), 0, NULL},
    {"may_be_omitted", T_BOOL, offsetof(PatternTokenBase, may_be_omitted), 0, NULL},
    {"test_string", T_BOOL, offsetof(PatternTokenBase, test_string), 0, NULL},
    {"unification_neutral", T_BOOL, offsetof(PatternTokenBase, unification_neutral), 0, NULL},
    {"uni_negation", T_BOOL, offsetof(PatternTokenBase, uni_negation), 0, NULL},
    {"last_in_unification", T_BOOL, offsetof(PatternTokenBase, last_in_unification), 0, NULL},
    {NULL}
};

static PyTypeObject PatternTokenBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.PatternTokenBase",
    .tp_basicsize = sizeof(PatternTokenBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)pt_dealloc,
    .tp_traverse = (traverseproc)pt_traverse,
    .tp_clear = (inquiry)pt_clear,
    .tp_members = pt_members,
};

#define PT(o) ((PatternTokenBase *)(o))

/* ------------------------------------------------------------------------ */
/* matching primitives */

/* Returns a borrowed reference to the lowercase version of the token or
 * lemma of an analyzed token, computing and caching it if needed. */
static PyObject *
at_lower(AnalyzedTokenBase *at, int use_lemma)
{
    PyObject **slot = use_lemma ? &at->lemma_lower : &at->token_lower;
    if (*slot == NULL || *slot == Py_None) {
        PyObject *s = use_lemma ? at->lemma : at->token;
        PyObject *l = PyObject_CallMethodNoArgs(s, str_lower);
        if (l == NULL) return NULL;
        Py_XSETREF(*slot, l);
    }
    return *slot;
}

static inline int
unicode_eq(PyObject *a, PyObject *b)
{
    if (a == b) return 1;
    if (PyUnicode_GET_LENGTH(a) != PyUnicode_GET_LENGTH(b)) return 0;
    int r = PyUnicode_Compare(a, b);
    if (r == -1 && PyErr_Occurred()) return -1;
    return r == 0;
}

/* sm: StringMatcherBase, s: the string to test, lower: lowercase version of s
 * or NULL (computed with lower_src/lower_use_lemma when needed). Returns 1, 0
 * or -1 on error. */
static int
sm_matches(PyObject *smo, PyObject *s, AnalyzedTokenBase *lower_src, int lower_use_lemma)
{
    StringMatcherBase *sm = SM(smo);
    if (PyUnicode_GET_LENGTH(s) > MAX_MATCH_LENGTH) return 0;
    if (sm->kind == KIND_EQUALS) {
        if (sm->case_sensitive) return unicode_eq(s, sm->value);
        int r = unicode_eq(s, sm->value);
        if (r != 0) return r;
        PyObject *l;
        if (lower_src != NULL) l = at_lower(lower_src, lower_use_lemma);
        else {
            l = PyObject_CallMethodNoArgs(s, str_lower);
            if (l == NULL) return -1;
            r = unicode_eq(l, sm->value_lower);
            Py_DECREF(l);
            return r;
        }
        if (l == NULL) return -1;
        return unicode_eq(l, sm->value_lower);
    }
    if (sm->kind == KIND_SET) {
        if (sm->case_sensitive) return PySet_Contains(sm->values, s);
        if (lower_src != NULL) {
            PyObject *l = at_lower(lower_src, lower_use_lemma);
            if (l == NULL) return -1;
            return PySet_Contains(sm->values, l);
        }
        PyObject *l = PyObject_CallMethodNoArgs(s, str_lower);
        if (l == NULL) return -1;
        int r = PySet_Contains(sm->values, l);
        Py_DECREF(l);
        return r;
    }
    /* regex */
    if (sm->cache != NULL && sm->cache != Py_None) {
        PyObject *r = PyDict_GetItemWithError(sm->cache, s);
        if (r != NULL) return r == Py_True;
        if (PyErr_Occurred()) return -1;
    }
    PyObject *r = PyObject_CallMethodOneArg(smo, str_regex_match, s);
    if (r == NULL) return -1;
    int ans = PyObject_IsTrue(r);
    Py_DECREF(r);
    return ans;
}

static int
pos_matched(PatternTokenBase *pt, AnalyzedTokenBase *at)
{
    PyObject *po = pt->pos_token;
    if (po == NULL || po == Py_None) return 1;
    PosTokenBase *pos = POS(po);
    if (pos->pos_tag == NULL || pos->pos_tag == Py_None || (pos->pos_unknown && at->has_no_pos_tag)) return 1;
    PyObject *tp = at->pos_tag;
    if (tp == NULL || tp == Py_None) return 0;
    if (pos->pos_pattern != NULL && pos->pos_pattern != Py_None) return sm_matches(pos->pos_pattern, tp, NULL, 0);
    return unicode_eq(pos->pos_tag, tp);
}

/* PatternToken.is_matched */
static int
pt_is_matched(PatternTokenBase *pt, AnalyzedTokenBase *at)
{
    if (pt->test_whitespace && pt->whitespace_before != at->whitespace_before) return 0;
    PyObject *po = pt->pos_token;
    int pos_negation = (po != NULL && po != Py_None) ? POS(po)->negation : 0;
    if (pt->test_string) {
        int use_lemma = pt->inflected && at->lemma != NULL && at->lemma != Py_None;
        PyObject *test = use_lemma ? at->lemma : at->token;
        int m = sm_matches(pt->text_matcher, test, at, use_lemma);
        if (m < 0) return -1;
        if ((m != 0) == (pt->negation != 0)) return 0;
        int p = pos_matched(pt, at);
        if (p < 0) return -1;
        return (p != 0) != (pos_negation != 0);
    }
    if (pt->negation) return 0;
    int p = pos_matched(pt, at);
    if (p < 0) return -1;
    return (p != 0) != (pos_negation != 0);
}

static int
pt_is_exception_matched(PatternTokenBase *pt, AnalyzedTokenBase *at)
{
    PyObject *t = pt->current_and_next_exceptions;
    if (t == NULL || !PyTuple_Check(t)) return 0;
    Py_ssize_t n = PyTuple_GET_SIZE(t);
    for (Py_ssize_t i = 0; i < n; i++) {
        PatternTokenBase *e = PT(PyTuple_GET_ITEM(t, i));
        if (!e->exception_valid_next) {
            int r = pt_is_matched(e, at);
            if (r != 0) return r;
        }
    }
    return 0;
}

static int
pt_is_exception_matched_completely(PatternTokenBase *pt, AnalyzedTokenBase *at)
{
    int r = pt_is_exception_matched(pt, at);
    if (r != 0) return r;
    PyObject *ag = pt->and_group;
    if (ag == NULL || ag == Py_None) return 0;
    Py_ssize_t n = PyList_GET_SIZE(ag);
    for (Py_ssize_t i = 0; i < n; i++) {
        r = pt_is_exception_matched(PT(PyList_GET_ITEM(ag, i)), at);
        if (r != 0) return r;
    }
    return 0;
}

static int
pt_is_matched_by_scope_next_exception(PatternTokenBase *pt, AnalyzedTokenBase *at)
{
    PyObject *t = pt->current_and_next_exceptions;
    if (t == NULL || !PyTuple_Check(t)) return 0;
    Py_ssize_t n = PyTuple_GET_SIZE(t);
    for (Py_ssize_t i = 0; i < n; i++) {
        PatternTokenBase *e = PT(PyTuple_GET_ITEM(t, i));
        if (e->exception_valid_next) {
            int r = pt_is_matched(e, at);
            if (r != 0) return r;
        }
    }
    return 0;
}

static int
pt_is_matched_by_previous_exception(PatternTokenBase *pt, ATRBase *atr)
{
    PyObject *t = pt->previous_exceptions;
    if (t == NULL || !PyTuple_Check(t)) return 0;
    Py_ssize_t n = PyTuple_GET_SIZE(t);
    if (n == 0) return 0;
    Py_ssize_t nr = PyList_GET_SIZE(atr->readings);
    for (Py_ssize_t j = 0; j < nr; j++) {
        AnalyzedTokenBase *at = AT(PyList_GET_ITEM(atr->readings, j));
        for (Py_ssize_t i = 0; i < n; i++) {
            PatternTokenBase *e = PT(PyTuple_GET_ITEM(t, i));
            if (!e->exception_valid_next) {
                int r = pt_is_matched(e, at);
                if (r != 0) return r;
            }
        }
    }
    return 0;
}

static inline int
pt_has_current_or_next_exceptions(PatternTokenBase *pt)
{
    PyObject *t = pt->current_and_next_exceptions;
    return t != NULL && PyTuple_Check(t) && PyTuple_GET_SIZE(t) > 0;
}

static inline int
pt_has_previous_exception(PatternTokenBase *pt)
{
    PyObject *t = pt->previous_exceptions;
    return t != NULL && PyTuple_Check(t) && PyTuple_GET_SIZE(t) > 0;
}

static inline int
pt_has_pos_tag(PatternTokenBase *pt)
{
    PyObject *po = pt->pos_token;
    return po != NULL && po != Py_None && POS(po)->pos_tag != NULL && POS(po)->pos_tag != Py_None;
}

static inline int
pt_pos_negation(PatternTokenBase *pt)
{
    PyObject *po = pt->pos_token;
    return po != NULL && po != Py_None && POS(po)->negation;
}

static int
atr_is_tagged(ATRBase *atr)
{
    Py_ssize_t n = PyList_GET_SIZE(atr->readings);
    for (Py_ssize_t i = 0; i < n; i++) {
        if (!AT(PyList_GET_ITEM(atr->readings, i))->has_no_pos_tag) return 1;
    }
    return 0;
}

/* chunk tag matching, uses the Python level ChunkTag objects */
static int
chunk_matches(PyObject *chunk, ATRBase *atr, int is_regexp)
{
    PyObject *tags = atr->chunk_tags;
    if (tags == NULL || !PyTuple_Check(tags)) return 0;
    Py_ssize_t n = PyTuple_GET_SIZE(tags);
    if (n == 0) return 0;
    if (is_regexp) {
        for (Py_ssize_t i = 0; i < n; i++) {
            PyObject *r = PyObject_CallMethodOneArg(chunk, str_matches, PyTuple_GET_ITEM(tags, i));
            if (r == NULL) return -1;
            int t = PyObject_IsTrue(r);
            Py_DECREF(r);
            if (t != 0) return t;
        }
        return 0;
    }
    PyObject *ct = PyObject_GetAttr(chunk, str_chunk_tag);
    if (ct == NULL) return -1;
    int found = 0;
    for (Py_ssize_t i = 0; i < n && !found; i++) {
        PyObject *ot = PyObject_GetAttr(PyTuple_GET_ITEM(tags, i), str_chunk_tag);
        if (ot == NULL) { Py_DECREF(ct); return -1; }
        int r = unicode_eq(ct, ot);
        Py_DECREF(ot);
        if (r < 0) { Py_DECREF(ct); return -1; }
        found = r;
    }
    Py_DECREF(ct);
    return found;
}

static int
chunk_is_regexp(PyObject *chunk)
{
    PyObject *r = PyObject_GetAttr(chunk, str_is_regexp);
    if (r == NULL) return -1;
    int t = PyObject_IsTrue(r);
    Py_DECREF(r);
    return t;
}

/* ------------------------------------------------------------------------ */
/* CompiledPattern: a pattern rule prepared for matching in C */

typedef struct {
    PyObject_HEAD
    PyObject *tokens_tuple;   /* tuple of PatternTokenBase */
    Py_ssize_t n;
    int min_occur_correction;
    int groups_or_unification;
    int check_immunized;
    int use_list;
    int *element_no;
    Py_ssize_t n_element_no;
} CompiledPattern;

static void
cp_dealloc(CompiledPattern *self)
{
    Py_XDECREF(self->tokens_tuple);
    PyMem_Free(self->element_no);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
cp_init(CompiledPattern *self, PyObject *args, PyObject *kwds)
{
    PyObject *tokens, *element_no;
    int moc, gou, ci;
    if (!PyArg_ParseTuple(args, "O!iiiO", &PyTuple_Type, &tokens, &moc, &gou, &ci, &element_no)) return -1;
    Py_ssize_t n = PyTuple_GET_SIZE(tokens);
    for (Py_ssize_t i = 0; i < n; i++) {
        if (!PyObject_TypeCheck(PyTuple_GET_ITEM(tokens, i), &PatternTokenBaseType)) {
            PyErr_SetString(PyExc_TypeError, "pattern tokens must be PatternToken instances");
            return -1;
        }
    }
    Py_INCREF(tokens);
    Py_XSETREF(self->tokens_tuple, tokens);
    self->n = n;
    self->min_occur_correction = moc;
    self->groups_or_unification = gou;
    self->check_immunized = ci;
    self->use_list = 0;
    if (element_no != Py_None) {
        PyObject *seq = PySequence_Fast(element_no, "element_no must be a sequence");
        if (seq == NULL) return -1;
        Py_ssize_t m = PySequence_Fast_GET_SIZE(seq);
        self->element_no = PyMem_Calloc(m + 1, sizeof(int));
        if (self->element_no == NULL) { Py_DECREF(seq); PyErr_NoMemory(); return -1; }
        for (Py_ssize_t i = 0; i < m; i++) {
            long v = PyLong_AsLong(PySequence_Fast_GET_ITEM(seq, i));
            if (v == -1 && PyErr_Occurred()) { Py_DECREF(seq); return -1; }
            self->element_no[i] = (int)v;
        }
        self->n_element_no = m;
        self->use_list = 1;
        Py_DECREF(seq);
    }
    return 0;
}

typedef struct {
    CompiledPattern *cp;
    PyObject **pts;
    PyObject **tokens;    /* ATRBase */
    Py_ssize_t ntokens;
    int prev_matched;
} MatchCtx;

static int
translate_element_no(MatchCtx *ctx, int i)
{
    if (!ctx->cp->use_list || i < 0) return i;
    int j = 0;
    for (int k = 0; k < i && k < ctx->cp->n_element_no; k++) j += ctx->cp->element_no[k];
    return j;
}

#define MAX_AND_GROUP 64

/* port of AbstractPatternRulePerformer.testAllReadings (+ the immunization
 * check of PatternRuleMatcher). Returns 1, 0 or -1 on error. */
static int
test_all_readings(MatchCtx *ctx, Py_ssize_t k, Py_ssize_t prev_k, Py_ssize_t token_no, int prev_skip_next)
{
    ATRBase *atr = ATR(ctx->tokens[token_no]);
    if (ctx->cp->check_immunized && atr->immunized) return 0;
    PatternTokenBase *pt = PT(ctx->pts[k]);
    PatternTokenBase *prev = prev_k >= 0 ? PT(ctx->pts[prev_k]) : NULL;
    PyObject *readings = atr->readings;
    Py_ssize_t nreadings = PyList_GET_SIZE(readings);
    int any_matched = 0;
    int has_and = pt->and_group != NULL && pt->and_group != Py_None;
    Py_ssize_t nand = has_and ? PyList_GET_SIZE(pt->and_group) : 0;
    char and_check[MAX_AND_GROUP + 1];
    if (has_and) {
        if (nand > MAX_AND_GROUP) {
            PyErr_SetString(PyExc_ValueError, "AND group too large");
            return -1;
        }
        memset(and_check, 0, nand + 1);
    }
    int prev_has_cn = prev != NULL && pt_has_current_or_next_exceptions(prev);
    int gou = ctx->cp->groups_or_unification;
    int r;
    for (Py_ssize_t i = 0; i < nreadings; i++) {
        AnalyzedTokenBase *mt = AT(PyList_GET_ITEM(readings, i));
        if (!ctx->prev_matched && prev_skip_next > 0 && prev != NULL) {
            r = pt_is_matched_by_scope_next_exception(prev, mt);
            if (r < 0) return -1;
            ctx->prev_matched = r;
        }
        if (!ctx->prev_matched && prev_skip_next == 0 && token_no <= ctx->ntokens - 2) {
            ATRBase *nxt = ATR(ctx->tokens[token_no + 1]);
            r = pt_is_matched_by_scope_next_exception(pt, AT(PyList_GET_ITEM(nxt->readings, 0)));
            if (r < 0) return -1;
            ctx->prev_matched = r;
        }
        if (ctx->prev_matched) return 0;
        int reading_tested = 0, reading_matches = 0;
        if (!any_matched) {
            r = pt_is_matched(pt, mt);
            if (r < 0) return -1;
            if (has_and) and_check[0] = and_check[0] || r;
            any_matched = reading_matches = r;
            reading_tested = 1;
        }
        if (!any_matched && !prev_has_cn) {
            if (!pt_has_pos_tag(pt)) {
                if (pt->inflected) {
                    if (atr->has_same_lemmas) return 0;
                } else {
                    return 0;
                }
            } else if (!pt_pos_negation(pt) && !atr_is_tagged(atr)) {
                return 0;
            }
        }
        if (gou) {
            if (!reading_tested) {
                r = pt_is_matched(pt, mt);
                if (r < 0) return -1;
                if (has_and) and_check[0] = and_check[0] || r;
                reading_matches = r;
            }
            (void)reading_matches;
            int is_last = i + 1 == nreadings;
            if (has_and) {
                for (Py_ssize_t j = 0; j < nand; j++) {
                    if (!and_check[j + 1]) {
                        r = pt_is_matched(PT(PyList_GET_ITEM(pt->and_group, j)), mt);
                        if (r < 0) return -1;
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
        for (Py_ssize_t i = 0; i < nreadings; i++) {
            r = pt_is_exception_matched_completely(pt, AT(PyList_GET_ITEM(readings, i)));
            if (r < 0) return -1;
            if (r) return 0;
        }
        if (token_no > 0 && pt_has_previous_exception(pt)) {
            r = pt_is_matched_by_previous_exception(pt, ATR(ctx->tokens[token_no - 1]));
            if (r < 0) return -1;
            if (r) return 0;
        }
    }
    if (pt->chunk_tag != NULL && pt->chunk_tag != Py_None) {
        int isre = chunk_is_regexp(pt->chunk_tag);
        if (isre < 0) return -1;
        r = chunk_matches(pt->chunk_tag, atr, isre);
        if (r < 0) return -1;
        any_matched = any_matched && ((r != 0) != (pt->negation != 0));
    }
    if (has_and) {
        for (Py_ssize_t j = 0; j < nand; j++) {
            PatternTokenBase *e = PT(PyList_GET_ITEM(pt->and_group, j));
            if (e->chunk_tag != NULL && e->chunk_tag != Py_None) {
                r = chunk_matches(e->chunk_tag, atr, 0);
                if (r < 0) return -1;
                any_matched = any_matched && ((r != 0) != (e->negation != 0));
            }
        }
    }
    return any_matched;
}

static int
skip_max_tokens(MatchCtx *ctx, Py_ssize_t k, Py_ssize_t prev_k, int prev_skip_next, Py_ssize_t m,
                Py_ssize_t remaining)
{
    int max_skip = 0;
    int mo = PT(ctx->pts[k])->max_occurrence;
    long long max_occ = mo == -1 ? 0x7fffffffLL : mo;
    for (long long j = 1; j < max_occ && m + j < ctx->ntokens - remaining; j++) {
        int r = test_all_readings(ctx, k, prev_k, m + j, prev_skip_next);
        if (r < 0) return -1;
        if (r) max_skip++;
        else break;
    }
    return max_skip;
}

/* port of AbstractPatternRulePerformer.matchFrom. Returns 1 if all pattern
 * tokens matched (and fills the output values), 0 if not, -1 on error. */
static int
match_from(MatchCtx *ctx, Py_ssize_t start_index, int *positions, int *first_out, int *last_out,
           int *first_marker_out, int *last_marker_out)
{
    Py_ssize_t n = ctx->cp->n;
    Py_ssize_t ntokens = ctx->ntokens;
    int moc = ctx->cp->min_occur_correction;
    long skip_shift_total = 0;
    int all_match = 0;
    Py_ssize_t matching_tokens = 0;
    long first_match_token = -1, last_match_token = -1, first_marker = -1, last_marker = -1;
    long prev_skip_next = 0;
    long min_occur_skip = 0;
    Py_ssize_t prev_k = -1;
    for (Py_ssize_t k = 0; k < n; k++) {
        if (k > 0) prev_k = k - 1;
        PatternTokenBase *pt = PT(ctx->pts[k]);
        long next_pos = (long)start_index + (long)k + skip_shift_total - min_occur_skip;
        ctx->prev_matched = 0;
        if (prev_skip_next + next_pos >= ntokens || prev_skip_next < 0) {
            prev_skip_next = (long)ntokens - (next_pos + 1);
        }
        long a = next_pos + prev_skip_next;
        long b = (long)ntokens - ((long)n - (long)k) + moc;
        long max_tok = a < b ? a : b;
        for (long m = next_pos; m <= max_tok; m++) {
            int r = test_all_readings(ctx, k, prev_k, m, (int)prev_skip_next);
            if (r < 0) return -1;
            all_match = r;
            if (pt->may_be_omitted) {
                int found_next = 0;
                for (Py_ssize_t k2 = k + 1; k2 < n; k2++) {
                    r = test_all_readings(ctx, k2, k, m, (int)prev_skip_next);
                    if (r < 0) return -1;
                    if (r) {
                        all_match = 1;
                        min_occur_skip++;
                        positions[matching_tokens++] = 0;
                        found_next = 1;
                        break;
                    } else if (!PT(ctx->pts[k2])->may_be_omitted) {
                        break;
                    }
                }
                if (found_next) break;
            }
            if (all_match) {
                int skip_for_max = skip_max_tokens(ctx, k, prev_k, (int)prev_skip_next, m, n - k - 1);
                if (skip_for_max < 0) return -1;
                last_match_token = m + skip_for_max;
                long skip_shift = last_match_token - next_pos;
                positions[matching_tokens++] = (int)(skip_shift + 1);
                prev_skip_next = translate_element_no(ctx, pt->skip);
                skip_shift_total += skip_shift;
                if (first_match_token == -1) first_match_token = last_match_token - skip_for_max;
                if (first_marker == -1 && pt->inside_marker) first_marker = last_match_token - skip_for_max;
                if (pt->inside_marker) last_marker = last_match_token;
                break;
            }
        }
        if (!all_match) break;
    }
    if (all_match && matching_tokens == n) {
        *first_out = (int)first_match_token;
        *last_out = (int)last_match_token;
        *first_marker_out = (int)first_marker;
        *last_marker_out = (int)last_marker;
        return 1;
    }
    return 0;
}

/* CompiledPattern.match(tokens, starts, consumer)
 * tokens: list of AnalyzedTokenReadings
 * starts: list of start indices, or a (from, to) tuple (inclusive range)
 * consumer: called with (positions, first, last, first_marker, last_marker)
 */
static PyObject *
cp_match(CompiledPattern *self, PyObject *args)
{
    PyObject *tokens, *starts, *consumer;
    if (!PyArg_ParseTuple(args, "O!OO", &PyList_Type, &tokens, &starts, &consumer)) return NULL;
    Py_ssize_t ntokens = PyList_GET_SIZE(tokens);
    for (Py_ssize_t i = 0; i < ntokens; i++) {
        if (!PyObject_TypeCheck(PyList_GET_ITEM(tokens, i), &ATRBaseType)) {
            PyErr_SetString(PyExc_TypeError, "tokens must be AnalyzedTokenReadings instances");
            return NULL;
        }
    }
    /* keep the tokens alive even if the consumer modifies the list */
    PyObject *tokens_copy = PyList_GetSlice(tokens, 0, ntokens);
    if (tokens_copy == NULL) return NULL;
    MatchCtx ctx;
    ctx.cp = self;
    ctx.pts = &PyTuple_GET_ITEM(self->tokens_tuple, 0);
    ctx.tokens = &PyList_GET_ITEM(tokens_copy, 0);
    ctx.ntokens = ntokens;
    ctx.prev_matched = 0;
    Py_ssize_t n = self->n;
    int *positions = PyMem_Calloc(n + 1, sizeof(int));
    if (positions == NULL) { Py_DECREF(tokens_copy); return PyErr_NoMemory(); }
    PyObject *seq = NULL;
    long from = 0, to = -1;
    int use_seq = 0;
    if (PyTuple_Check(starts)) {
        if (!PyArg_ParseTuple(starts, "ll", &from, &to)) goto error;
    } else {
        seq = PySequence_Fast(starts, "starts must be a sequence");
        if (seq == NULL) goto error;
        use_seq = 1;
        from = 0;
        to = (long)PySequence_Fast_GET_SIZE(seq) - 1;
    }
    for (long idx = from; idx <= to; idx++) {
        long start;
        if (use_seq) {
            start = PyLong_AsLong(PySequence_Fast_GET_ITEM(seq, idx));
            if (start == -1 && PyErr_Occurred()) goto error;
        } else {
            start = idx;
        }
        int first, last, fm, lm;
        int r = match_from(&ctx, start, positions, &first, &last, &fm, &lm);
        if (r < 0) goto error;
        if (r) {
            PyObject *pl = PyList_New(n);
            if (pl == NULL) goto error;
            for (Py_ssize_t i = 0; i < n; i++) {
                PyObject *v = PyLong_FromLong(positions[i]);
                if (v == NULL) { Py_DECREF(pl); goto error; }
                PyList_SET_ITEM(pl, i, v);
            }
            PyObject *res = PyObject_CallFunction(consumer, "Niiii", pl, first, last, fm, lm);
            if (res == NULL) goto error;
            Py_DECREF(res);
        }
    }
    Py_XDECREF(seq);
    PyMem_Free(positions);
    Py_DECREF(tokens_copy);
    Py_RETURN_NONE;
error:
    Py_XDECREF(seq);
    PyMem_Free(positions);
    Py_DECREF(tokens_copy);
    return NULL;
}

static PyMethodDef cp_methods[] = {
    {"match", (PyCFunction)cp_match, METH_VARARGS, "Match the pattern against a list of tokens"},
    {NULL}
};

static PyTypeObject CompiledPatternType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.CompiledPattern",
    .tp_basicsize = sizeof(CompiledPattern),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)cp_init,
    .tp_dealloc = (destructor)cp_dealloc,
    .tp_methods = cp_methods,
};

/* module level functions exposing the primitives (used by the Python code
 * for the matching that is not done by CompiledPattern) */

static PyObject *
py_pt_is_matched(PyObject *self, PyObject *args)
{
    PyObject *pt, *at;
    if (!PyArg_ParseTuple(args, "O!O!", &PatternTokenBaseType, &pt, &AnalyzedTokenBaseType, &at)) return NULL;
    int r = pt_is_matched(PT(pt), AT(at));
    if (r < 0) return NULL;
    return PyBool_FromLong(r);
}

static PyObject *
py_sm_matches(PyObject *self, PyObject *args)
{
    PyObject *sm, *s;
    if (!PyArg_ParseTuple(args, "O!U", &StringMatcherBaseType, &sm, &s)) return NULL;
    int r = sm_matches(sm, s, NULL, 0);
    if (r < 0) return NULL;
    return PyBool_FromLong(r);
}

/* ------------------------------------------------------------------------ */
/* RuleHints: port of AbstractTokenBasedRule.canBeIgnoredFor */

typedef struct {
    PyObject_HEAD
    long min_token_count;
    PyObject *hints;       /* tuple of (inflected, values tuple, values frozenset) */
    PyObject *pos_hints;   /* tuple of frozensets or None */
} RuleHints;

static void
rh_dealloc(RuleHints *self)
{
    Py_XDECREF(self->hints);
    Py_XDECREF(self->pos_hints);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
rh_init(RuleHints *self, PyObject *args, PyObject *kwds)
{
    PyObject *hints, *pos_hints;
    long mtc;
    if (!PyArg_ParseTuple(args, "lO!O", &mtc, &PyTuple_Type, &hints, &pos_hints)) return -1;
    if (pos_hints != Py_None && !PyTuple_Check(pos_hints)) {
        PyErr_SetString(PyExc_TypeError, "pos_hints must be a tuple or None");
        return -1;
    }
    self->min_token_count = mtc;
    Py_INCREF(hints); Py_XSETREF(self->hints, hints);
    Py_INCREF(pos_hints); Py_XSETREF(self->pos_hints, pos_hints);
    return 0;
}

/* returns 1 if the hint can not match (no value occurs in offsets) */
static int
hint_ignorable(PyObject *values, PyObject *value_set, PyObject *offsets)
{
    Py_ssize_t nv = PyTuple_GET_SIZE(values);
    Py_ssize_t no = PyDict_GET_SIZE(offsets);
    if (nv <= no) {
        for (Py_ssize_t i = 0; i < nv; i++) {
            int r = PyDict_Contains(offsets, PyTuple_GET_ITEM(values, i));
            if (r != 0) return r < 0 ? -1 : 0;
        }
        return 1;
    }
    Py_ssize_t pos = 0;
    PyObject *key, *value;
    while (PyDict_Next(offsets, &pos, &key, &value)) {
        int r = PySet_Contains(value_set, key);
        if (r != 0) return r < 0 ? -1 : 0;
    }
    return 1;
}

/* ignorable(n_nonblank, token_offsets, lemma_offsets, pos_tag_set, check_pos) */
static PyObject *
rh_ignorable(RuleHints *self, PyObject *args)
{
    long nnb;
    PyObject *to, *lo, *tags;
    int check_pos;
    if (!PyArg_ParseTuple(args, "lO!O!Op", &nnb, &PyDict_Type, &to, &PyDict_Type, &lo, &tags, &check_pos))
        return NULL;
    if (nnb < self->min_token_count) Py_RETURN_TRUE;
    Py_ssize_t nh = PyTuple_GET_SIZE(self->hints);
    for (Py_ssize_t i = 0; i < nh; i++) {
        PyObject *h = PyTuple_GET_ITEM(self->hints, i);
        int inflected = PyObject_IsTrue(PyTuple_GET_ITEM(h, 0));
        int r = hint_ignorable(PyTuple_GET_ITEM(h, 1), PyTuple_GET_ITEM(h, 2), inflected ? lo : to);
        if (r < 0) return NULL;
        if (r) Py_RETURN_TRUE;
    }
    if (check_pos && self->pos_hints != Py_None) {
        Py_ssize_t np = PyTuple_GET_SIZE(self->pos_hints);
        for (Py_ssize_t i = 0; i < np; i++) {
            PyObject *ph = PyTuple_GET_ITEM(self->pos_hints, i);
            int found = 0;
            /* iterate the smaller set */
            PyObject *small = ph, *big = tags;
            if (PySet_GET_SIZE(tags) < PySet_GET_SIZE(ph)) { small = tags; big = ph; }
            PyObject *it = PyObject_GetIter(small);
            if (it == NULL) return NULL;
            PyObject *item;
            while ((item = PyIter_Next(it)) != NULL) {
                int r = PySet_Contains(big, item);
                Py_DECREF(item);
                if (r < 0) { Py_DECREF(it); return NULL; }
                if (r) { found = 1; break; }
            }
            Py_DECREF(it);
            if (PyErr_Occurred()) return NULL;
            if (!found) Py_RETURN_TRUE;
        }
    }
    Py_RETURN_FALSE;
}

static PyMethodDef rh_methods[] = {
    {"ignorable", (PyCFunction)rh_ignorable, METH_VARARGS, "canBeIgnoredFor"},
    {NULL}
};

static PyTypeObject RuleHintsType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.RuleHints",
    .tp_basicsize = sizeof(RuleHints),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)rh_init,
    .tp_dealloc = (destructor)rh_dealloc,
    .tp_methods = rh_methods,
};

/* ------------------------------------------------------------------------ */
/* FSA dictionaries */

typedef struct {
    PyObject_HEAD
    PyObject *arcs_obj;
    const unsigned char *arcs;
    Py_ssize_t narcs;
    int kind;           /* 5: FSA5, 0xc5: CFSA, 0xc6: CFSA2 */
    long root;
    int gtl;
    int node_data_length;
    unsigned char label_mapping[256];
    int has_numbers;
    unsigned char separator;
    int prefix_bytes;
    int encoder;        /* 0 suffix, 1 prefix, 2 infix, 3 none */
} FSADict;

static void
fsa_dealloc(FSADict *self)
{
    Py_XDECREF(self->arcs_obj);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
fsa_init(FSADict *self, PyObject *args, PyObject *kwds)
{
    PyObject *arcs, *mapping;
    int kind, gtl, ndl, has_numbers, sep, prefix_bytes;
    long root;
    const char *encoder;
    if (!PyArg_ParseTuple(args, "O!ilii" "O!" "pii" "s", &PyBytes_Type, &arcs, &kind, &root, &gtl, &ndl,
                          &PyBytes_Type, &mapping, &has_numbers, &sep, &prefix_bytes, &encoder)) return -1;
    Py_INCREF(arcs);
    Py_XSETREF(self->arcs_obj, arcs);
    self->arcs = (const unsigned char *)PyBytes_AS_STRING(arcs);
    self->narcs = PyBytes_GET_SIZE(arcs);
    self->kind = kind;
    self->root = root;
    self->gtl = gtl;
    self->node_data_length = ndl;
    memset(self->label_mapping, 0, sizeof(self->label_mapping));
    Py_ssize_t ml = PyBytes_GET_SIZE(mapping);
    if (ml > 256) ml = 256;
    memcpy(self->label_mapping, PyBytes_AS_STRING(mapping), ml);
    self->has_numbers = has_numbers;
    self->separator = (unsigned char)sep;
    self->prefix_bytes = prefix_bytes;
    if (strcmp(encoder, "SUFFIX") == 0) self->encoder = 0;
    else if (strcmp(encoder, "PREFIX") == 0) self->encoder = 1;
    else if (strcmp(encoder, "INFIX") == 0) self->encoder = 2;
    else self->encoder = 3;
    if (kind != 5 && kind != 0xc5 && kind != 0xc6) {
        PyErr_SetString(PyExc_ValueError, "Unknown FSA kind");
        return -1;
    }
    return 0;
}

#define BOUNDS(off) do { if ((off) < 0 || (off) >= d->narcs) return -1; } while (0)

/* All functions return -1 on out of bounds access (corrupt dictionary) */

static long
fsa_skip_arc(FSADict *d, long off)
{
    const unsigned char *a = d->arcs;
    BOUNDS(off);
    if (d->kind == 5) {
        BOUNDS(off + 1);
        return off + ((a[off + 1] & 4) ? 2 : 1 + d->gtl);
    }
    if (d->kind == 0xc5) {
        unsigned char f = a[off];
        if (f & 4) return off + ((f & 0xf8) ? 1 : 2);
        return off + 1 + d->gtl;
    }
    unsigned char flag = a[off++];
    if ((flag & 0x1f) == 0) off++;
    if ((flag & 0x80) == 0) {
        while (1) {
            BOUNDS(off);
            if (!(a[off] & 0x80)) break;
            off++;
        }
        off++;
    }
    return off;
}

static long
fsa_first_arc(FSADict *d, long node)
{
    if (d->kind == 0xc6) {
        if (d->has_numbers) {
            while (1) {
                BOUNDS(node);
                if (!(d->arcs[node] & 0x80)) break;
                node++;
            }
            return node + 1;
        }
        return node;
    }
    return d->node_data_length + node;
}

static int
fsa_is_last(FSADict *d, long arc)
{
    if (d->kind == 5) return (d->arcs[arc + 1] & 2) != 0;
    if (d->kind == 0xc5) return (d->arcs[arc] & 2) != 0;
    return (d->arcs[arc] & 0x40) != 0;
}

static int
fsa_is_final(FSADict *d, long arc)
{
    if (d->kind == 5) return (d->arcs[arc + 1] & 1) != 0;
    if (d->kind == 0xc5) return (d->arcs[arc] & 1) != 0;
    return (d->arcs[arc] & 0x20) != 0;
}

static int
fsa_label(FSADict *d, long arc)
{
    const unsigned char *a = d->arcs;
    if (d->kind == 5) return a[arc];
    if (d->kind == 0xc5) {
        unsigned char f = a[arc];
        if ((f & 4) && (f & 0xf8)) return d->label_mapping[(f >> 3) & 0x1f];
        return a[arc + 1];
    }
    int idx = a[arc] & 0x1f;
    if (idx > 0) return d->label_mapping[idx];
    return a[arc + 1];
}

static long
fsa_destination(FSADict *d, long arc)
{
    const unsigned char *a = d->arcs;
    BOUNDS(arc);
    if (d->kind == 5) {
        BOUNDS(arc + 1);
        if (a[arc + 1] & 4) return fsa_skip_arc(d, arc);
        long r = 0;
        for (int i = d->gtl - 1; i >= 0; i--) {
            BOUNDS(arc + 1 + i);
            r = (r << 8) | a[arc + 1 + i];
        }
        return r >> 3;
    }
    if (d->kind == 0xc5) {
        if (a[arc] & 4) return fsa_skip_arc(d, arc);
        long r = 0;
        for (int i = d->gtl - 1; i >= 1; i--) {
            BOUNDS(arc + 1 + i);
            r = (r << 8) | a[arc + 1 + i];
        }
        r = (r << 8) | a[arc];
        return r >> 3;
    }
    if (a[arc] & 0x80) {
        while (!(a[arc] & 0x40)) {
            arc = fsa_skip_arc(d, arc);
            if (arc < 0) return -1;
            BOUNDS(arc);
        }
        return fsa_skip_arc(d, arc);
    }
    long off = arc + (((a[arc] & 0x1f) == 0) ? 2 : 1);
    BOUNDS(off);
    unsigned char b = a[off];
    long value = b & 0x7f;
    int shift = 7;
    while (b & 0x80) {
        off++;
        BOUNDS(off);
        b = a[off];
        value |= ((long)(b & 0x7f)) << shift;
        shift += 7;
    }
    return value;
}

static long
fsa_get_arc(FSADict *d, long node, int lbl)
{
    /* like morfologik: an arc offset of 0 means "no arc" */
    long arc = fsa_first_arc(d, node);
    while (arc != 0) {
        if (arc < 0 || arc >= d->narcs || (d->kind == 5 && arc + 1 >= d->narcs)) return -1;
        if (fsa_label(d, arc) == lbl) return arc;
        if (fsa_is_last(d, arc)) return 0;
        arc = fsa_skip_arc(d, arc);
    }
    return 0;
}

typedef struct {
    unsigned char *data;
    Py_ssize_t len, cap;
} Buf;

static int
buf_put(Buf *b, Py_ssize_t pos, unsigned char c)
{
    if (pos >= b->cap) {
        Py_ssize_t nc = b->cap ? b->cap * 2 : 256;
        while (nc <= pos) nc *= 2;
        unsigned char *nd = PyMem_Realloc(b->data, nc);
        if (nd == NULL) { PyErr_NoMemory(); return -1; }
        b->data = nd;
        b->cap = nc;
    }
    b->data[pos] = c;
    b->len = pos + 1;
    return 0;
}

static PyObject *
decode_stem(FSADict *d, const unsigned char *src, Py_ssize_t srclen, const unsigned char *enc, Py_ssize_t enclen)
{
    if (d->encoder == 3) return PyBytes_FromStringAndSize((const char *)enc, enclen);
    if (d->encoder == 0) {
        if (enclen < 1) return PyBytes_FromStringAndSize("", 0);
        int trunc = (enc[0] - 'A') & 0xff;
        if (trunc == 255) trunc = (int)srclen;
        Py_ssize_t l1 = srclen - trunc;
        if (l1 < 0) l1 = 0;
        PyObject *r = PyBytes_FromStringAndSize(NULL, l1 + enclen - 1);
        if (r == NULL) return NULL;
        char *p = PyBytes_AS_STRING(r);
        memcpy(p, src, l1);
        memcpy(p + l1, enc + 1, enclen - 1);
        return r;
    }
    if (d->encoder == 1) {
        if (enclen < 2) return PyBytes_FromStringAndSize("", 0);
        int tp = (enc[0] - 'A') & 0xff, ts = (enc[1] - 'A') & 0xff;
        if (tp == 255 || ts == 255) { tp = (int)srclen; ts = 0; }
        Py_ssize_t l1 = srclen - (tp + ts);
        if (l1 < 0) l1 = 0;
        if (tp > srclen) tp = (int)srclen;
        PyObject *r = PyBytes_FromStringAndSize(NULL, l1 + enclen - 2);
        if (r == NULL) return NULL;
        char *p = PyBytes_AS_STRING(r);
        memcpy(p, src + tp, l1);
        memcpy(p + l1, enc + 2, enclen - 2);
        return r;
    }
    /* infix */
    if (enclen < 3) return PyBytes_FromStringAndSize("", 0);
    int ii = (enc[0] - 'A') & 0xff, il = (enc[1] - 'A') & 0xff, ts = (enc[2] - 'A') & 0xff;
    if (il == 255 || ts == 255) { ii = 0; il = (int)srclen; ts = 0; }
    Py_ssize_t l1 = srclen - (ii + il + ts);
    if (l1 < 0) l1 = 0;
    if (ii > srclen) ii = (int)srclen;
    Py_ssize_t off2 = ii + il;
    if (off2 > srclen) off2 = srclen;
    PyObject *r = PyBytes_FromStringAndSize(NULL, ii + l1 + enclen - 3);
    if (r == NULL) return NULL;
    char *p = PyBytes_AS_STRING(r);
    memcpy(p, src, ii);
    memcpy(p + ii, src + off2, l1);
    memcpy(p + ii + l1, enc + 3, enclen - 3);
    return r;
}

static PyObject *
fsa_lookup(FSADict *d, PyObject *args)
{
    const unsigned char *word;
    Py_ssize_t wlen;
    if (!PyArg_ParseTuple(args, "y#", &word, &wlen)) return NULL;
    PyObject *result = PyList_New(0);
    if (result == NULL) return NULL;
    long node = d->root;
    for (Py_ssize_t i = 0; i < wlen; i++) {
        long arc = fsa_get_arc(d, node, word[i]);
        if (arc < 0) goto corrupt;
        if (arc == 0) return result;
        if (i == wlen - 1 && fsa_is_final(d, arc)) return result;
        node = fsa_destination(d, arc);
        if (node < 0) goto corrupt;
        if (node == 0) return result;
    }
    long arc = fsa_get_arc(d, node, d->separator);
    if (arc < 0) goto corrupt;
    if (arc == 0 || fsa_is_final(d, arc)) return result;
    long start = fsa_destination(d, arc);
    if (start < 0) goto corrupt;
    if (start == 0) return result;
    /* depth first iteration over all sequences from start */
    {
        long *stack = NULL;
        Py_ssize_t sp = 0, scap = 0;
        Buf buf = {NULL, 0, 0};
#define PUSH(v) do { if (sp >= scap) { scap = scap ? scap * 2 : 64; long *ns = PyMem_Realloc(stack, scap * sizeof(long)); if (!ns) { PyErr_NoMemory(); goto iter_error; } stack = ns; } stack[sp++] = (v); } while (0)
        long fa = fsa_first_arc(d, start);
        if (fa < 0) goto iter_corrupt;
        PUSH(fa);
        while (sp > 0) {
            long a = stack[sp - 1];
            Py_ssize_t depth = sp - 1;
            if (a == -2 || a == 0) { sp--; continue; }
            if (a < 0 || a >= d->narcs || (d->kind == 5 && a + 1 >= d->narcs)) goto iter_corrupt;
            long nxt = fsa_is_last(d, a) ? -2 : fsa_skip_arc(d, a);
            if (nxt == -1) goto iter_corrupt;
            stack[sp - 1] = nxt;
            if (buf_put(&buf, depth, (unsigned char)fsa_label(d, a)) < 0) goto iter_error;
            buf.len = depth + 1;
            long dest = fsa_destination(d, a);
            if (dest < 0) goto iter_corrupt;
            int fin = fsa_is_final(d, a);
            if (dest != 0) {
                long f2 = fsa_first_arc(d, dest);
                if (f2 < 0) goto iter_corrupt;
                PUSH(f2);
            }
            if (fin) {
                Py_ssize_t n = depth + 1;
                const unsigned char *seq = buf.data;
                Py_ssize_t sep_pos = d->prefix_bytes;
                while (sep_pos < n && seq[sep_pos] != d->separator) sep_pos++;
                if (sep_pos > n) sep_pos = n;
                PyObject *stem = decode_stem(d, word, wlen, seq, sep_pos);
                if (stem == NULL) goto iter_error;
                PyObject *tag;
                if (sep_pos + 1 < n) {
                    tag = PyBytes_FromStringAndSize((const char *)seq + sep_pos + 1, n - sep_pos - 1);
                    if (tag == NULL) { Py_DECREF(stem); goto iter_error; }
                } else {
                    tag = Py_None;
                    Py_INCREF(tag);
                }
                PyObject *t = PyTuple_Pack(2, stem, tag);
                Py_DECREF(stem);
                Py_DECREF(tag);
                if (t == NULL) goto iter_error;
                if (PyList_Append(result, t) < 0) { Py_DECREF(t); goto iter_error; }
                Py_DECREF(t);
            }
        }
        PyMem_Free(stack);
        PyMem_Free(buf.data);
        return result;
iter_corrupt:
        PyErr_SetString(PyExc_ValueError, "Corrupt FSA dictionary");
iter_error:
        PyMem_Free(stack);
        PyMem_Free(buf.data);
        Py_DECREF(result);
        return NULL;
#undef PUSH
    }
corrupt:
    PyErr_SetString(PyExc_ValueError, "Corrupt FSA dictionary");
    Py_DECREF(result);
    return NULL;
}

static PyMethodDef fsa_methods[] = {
    {"lookup", (PyCFunction)fsa_lookup, METH_VARARGS, "Lookup an encoded word, returns list of (stem, tag)"},
    {NULL}
};

static PyTypeObject FSADictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.FSADict",
    .tp_basicsize = sizeof(FSADict),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)fsa_init,
    .tp_dealloc = (destructor)fsa_dealloc,
    .tp_methods = fsa_methods,
};

/* ------------------------------------------------------------------------ */

/* ------------------------------------------------------------------------ */
/* OpenNLP GIS model evaluation (langtool.opennlp.GISModel)                  */

#define GIS_MAX_OUTCOMES 1024

/* Adds the parameters of the context predicates (in their order, like
 * ArrayMath.sumFeatures) to the sums. pmap maps a predicate to a tuple
 * (outcome indices, parameters). */
static int
gis_add_features(double *sums, Py_ssize_t n, PyObject *pmap, PyObject *context)
{
    PyObject *seq = PySequence_Fast(context, "context must be a sequence");
    if (!seq) return -1;
    Py_ssize_t len = PySequence_Fast_GET_SIZE(seq);
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < len; i++) {
        PyObject *e = PyDict_GetItemWithError(pmap, items[i]);
        if (!e) {
            if (PyErr_Occurred()) { Py_DECREF(seq); return -1; }
            continue;
        }
        if (!PyTuple_Check(e) || PyTuple_GET_SIZE(e) != 2) {
            PyErr_SetString(PyExc_TypeError, "pmap values must be (outcomes, parameters) tuples");
            Py_DECREF(seq); return -1;
        }
        PyObject *outs = PyTuple_GET_ITEM(e, 0), *params = PyTuple_GET_ITEM(e, 1);
        if (!PyTuple_Check(outs) || !PyTuple_Check(params) || PyTuple_GET_SIZE(outs) != PyTuple_GET_SIZE(params)) {
            PyErr_SetString(PyExc_TypeError, "outcomes and parameters must be tuples of the same length");
            Py_DECREF(seq); return -1;
        }
        Py_ssize_t m = PyTuple_GET_SIZE(outs);
        for (Py_ssize_t j = 0; j < m; j++) {
            Py_ssize_t oid = PyLong_AsSsize_t(PyTuple_GET_ITEM(outs, j));
            if (oid == -1 && PyErr_Occurred()) { Py_DECREF(seq); return -1; }
            double p = PyFloat_AsDouble(PyTuple_GET_ITEM(params, j));
            if (p == -1.0 && PyErr_Occurred()) { Py_DECREF(seq); return -1; }
            if (oid < 0 || oid >= n) {
                PyErr_SetString(PyExc_IndexError, "outcome index out of range");
                Py_DECREF(seq); return -1;
            }
            sums[oid] += p;
        }
    }
    Py_DECREF(seq);
    return 0;
}

static int
gis_read_prior(PyObject *prior, double *sums, Py_ssize_t *n)
{
    if (!PyList_Check(prior)) { PyErr_SetString(PyExc_TypeError, "prior must be a list"); return -1; }
    *n = PyList_GET_SIZE(prior);
    if (*n > GIS_MAX_OUTCOMES) { PyErr_SetString(PyExc_ValueError, "too many outcomes"); return -1; }
    for (Py_ssize_t i = 0; i < *n; i++) {
        sums[i] = PyFloat_AsDouble(PyList_GET_ITEM(prior, i));
        if (sums[i] == -1.0 && PyErr_Occurred()) return -1;
    }
    return 0;
}

static PyObject *
gis_make_list(const double *values, Py_ssize_t n)
{
    PyObject *out = PyList_New(n);
    if (!out) return NULL;
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *f = PyFloat_FromDouble(values[i]);
        if (!f) { Py_DECREF(out); return NULL; }
        PyList_SET_ITEM(out, i, f);
    }
    return out;
}

/* gis_sum(prior, pmap, context) -> new list: prior plus the parameters of the context predicates */
static PyObject *
py_gis_sum(PyObject *self, PyObject *args)
{
    PyObject *prior, *pmap, *context;
    double sums[GIS_MAX_OUTCOMES];
    Py_ssize_t n;
    if (!PyArg_ParseTuple(args, "OO!O", &prior, &PyDict_Type, &pmap, &context)) return NULL;
    if (gis_read_prior(prior, sums, &n) < 0) return NULL;
    if (gis_add_features(sums, n, pmap, context) < 0) return NULL;
    return gis_make_list(sums, n);
}

/* gis_eval(prior, pmap, context) -> the probabilities of GISModel.eval (exp and normalization of the sums), or
 * None if the sum of the exps is 0 or infinite (the caller handles these cases) */
static PyObject *
py_gis_eval(PyObject *self, PyObject *args)
{
    PyObject *prior, *pmap, *context;
    double sums[GIS_MAX_OUTCOMES];
    Py_ssize_t n;
    if (!PyArg_ParseTuple(args, "OO!O", &prior, &PyDict_Type, &pmap, &context)) return NULL;
    if (gis_read_prior(prior, sums, &n) < 0) return NULL;
    if (gis_add_features(sums, n, pmap, context) < 0) return NULL;
    double normal = 0.0;
    for (Py_ssize_t i = 0; i < n; i++) {
        sums[i] = exp(sums[i]);
        normal += sums[i];
    }
    if (normal == 0.0 || isinf(normal) || isnan(normal)) Py_RETURN_NONE;
    for (Py_ssize_t i = 0; i < n; i++) sums[i] /= normal;
    return gis_make_list(sums, n);
}

/* levenshtein(s1, s2) -> int: org.apache.commons.text.similarity.LevenshteinDistance (unlimited) */
static PyObject *
py_levenshtein(PyObject *self, PyObject *args)
{
    PyObject *a, *b;
    if (!PyArg_ParseTuple(args, "UU", &a, &b))
        return NULL;
    Py_ssize_t n = PyUnicode_GET_LENGTH(a), m = PyUnicode_GET_LENGTH(b);
    if (n < m) { PyObject *t = a; a = b; b = t; Py_ssize_t tn = n; n = m; m = tn; }
    if (m == 0)
        return PyLong_FromSsize_t(n);
    int ka = PyUnicode_KIND(a), kb = PyUnicode_KIND(b);
    const void *da = PyUnicode_DATA(a), *db = PyUnicode_DATA(b);
    Py_ssize_t *row = PyMem_Malloc((m + 1) * sizeof(Py_ssize_t));
    if (row == NULL)
        return PyErr_NoMemory();
    for (Py_ssize_t j = 0; j <= m; j++)
        row[j] = j;
    for (Py_ssize_t i = 1; i <= n; i++) {
        Py_UCS4 c1 = PyUnicode_READ(ka, da, i - 1);
        Py_ssize_t diag = row[0];
        row[0] = i;
        for (Py_ssize_t j = 1; j <= m; j++) {
            Py_ssize_t up = row[j];
            Py_ssize_t cost = diag + (c1 != PyUnicode_READ(kb, db, j - 1));
            Py_ssize_t v = up + 1;
            if (row[j - 1] + 1 < v) v = row[j - 1] + 1;
            if (cost < v) v = cost;
            row[j] = v;
            diag = up;
        }
    }
    Py_ssize_t r = row[m];
    PyMem_Free(row);
    return PyLong_FromSsize_t(r);
}

static PyMethodDef module_methods[] = {
    {"levenshtein", py_levenshtein, METH_VARARGS, NULL},
    {"gis_sum", py_gis_sum, METH_VARARGS, NULL},
    {"gis_eval", py_gis_eval, METH_VARARGS, NULL},
    {"pattern_token_is_matched", py_pt_is_matched, METH_VARARGS, NULL},
    {"string_matcher_matches", py_sm_matches, METH_VARARGS, NULL},
    {NULL}
};

static int
exec_module(PyObject *m)
{
#define ADD_TYPE(t, name) do { if (PyType_Ready(&t) < 0) return -1; Py_INCREF(&t); if (PyModule_AddObject(m, name, (PyObject *)&t) < 0) return -1; } while (0)
    ADD_TYPE(AnalyzedTokenBaseType, "AnalyzedTokenBase");
    ADD_TYPE(ATRBaseType, "AnalyzedTokenReadingsBase");
    ADD_TYPE(StringMatcherBaseType, "StringMatcherBase");
    ADD_TYPE(PosTokenBaseType, "PosTokenBase");
    ADD_TYPE(PatternTokenBaseType, "PatternTokenBase");
    ADD_TYPE(CompiledPatternType, "CompiledPattern");
    ADD_TYPE(FSADictType, "FSADict");
    ADD_TYPE(RuleHintsType, "RuleHints");
#undef ADD_TYPE
    str_lower = PyUnicode_InternFromString("lower");
    str_regex_match = PyUnicode_InternFromString("_regex_match");
    str_chunk_tag = PyUnicode_InternFromString("chunk_tag");
    str_matches = PyUnicode_InternFromString("matches");
    str_is_regexp = PyUnicode_InternFromString("is_regexp");
    if (!str_lower || !str_regex_match || !str_chunk_tag || !str_matches || !str_is_regexp) return -1;
    return 0;
}

static PyModuleDef_Slot slots[] = {
    {Py_mod_exec, exec_module},
#ifdef Py_mod_gil
    {Py_mod_gil, Py_MOD_GIL_USED},
#endif
    {0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_speedups",
    .m_doc = "C accelerated parts of langtool",
    .m_size = 0,
    .m_methods = module_methods,
    .m_slots = slots,
};

PyMODINIT_FUNC
PyInit__speedups(void)
{
    return PyModuleDef_Init(&moduledef);
}
