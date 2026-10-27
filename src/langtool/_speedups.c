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

#ifndef PySet_CheckExact  /* (Python 3.10+) */
#define PySet_CheckExact(op) Py_IS_TYPE(op, &PySet_Type)
#endif

#define MAX_MATCH_LENGTH 250
#define KIND_EQUALS 0
#define KIND_SET 1
#define KIND_REGEX 2

static inline int unicode_eq(PyObject *a, PyObject *b);

static PyObject *str_lower = NULL;          /* "lower" */
static PyObject *str_regex_match = NULL;    /* "_regex_match" */
static PyObject *str_chunk_tag = NULL;      /* "chunk_tag" */
static PyObject *str_matches = NULL;        /* "matches" */
static PyObject *str_is_regexp = NULL;      /* "is_regexp" */
static PyObject *str_fullmatch = NULL;      /* "fullmatch" */
static PyObject *str_token = NULL;          /* "token" */

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


/* ------------------------------------------------------------------------ */
/* pickle support of the base types with C members (used by the persistent
 * cache of langtool.diskcache): the state is (values, null_mask, dict) where
 * values are the members in the order of the PyMemberDef table, bit i of
 * null_mask is set if the object member i is NULL (not set, unlike None) and
 * dict is the instance __dict__ of a Python subclass (or None). Python
 * subclasses must not add other slots than __weakref__ (checked by the
 * pickler of langtool.diskcache). */

static Py_ssize_t
members_count(PyMemberDef *members)
{
    Py_ssize_t n = 0;
    while (members[n].name != NULL) n++;
    return n;
}

static PyObject *
members_getstate(PyObject *self, PyMemberDef *members)
{
    Py_ssize_t n = members_count(members);
    unsigned long long mask = 0;
    PyObject *vals = PyTuple_New(n);
    if (vals == NULL) return NULL;
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *v;
        if (members[i].type == T_OBJECT && *(PyObject **)((char *)self + members[i].offset) == NULL) {
            mask |= 1ULL << i;
            v = Py_None;
            Py_INCREF(v);
        } else {
            v = PyMember_GetOne((const char *)self, &members[i]);
            if (v == NULL) { Py_DECREF(vals); return NULL; }
        }
        PyTuple_SET_ITEM(vals, i, v);
    }
    PyObject *dict = PyObject_GetAttrString(self, "__dict__");
    if (dict == NULL) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) { Py_DECREF(vals); return NULL; }
        PyErr_Clear();
        dict = Py_None;
        Py_INCREF(dict);
    } else if (PyDict_Check(dict) && PyDict_GET_SIZE(dict) == 0) {
        Py_DECREF(dict);
        dict = Py_None;
        Py_INCREF(dict);
    }
    PyObject *r = Py_BuildValue("(NKN)", vals, mask, dict);
    return r;
}

static PyObject *
members_setstate(PyObject *self, PyObject *state, PyMemberDef *members)
{
    PyObject *vals, *dict;
    unsigned long long mask;
    if (!PyArg_ParseTuple(state, "O!KO;invalid pickle state", &PyTuple_Type, &vals, &mask, &dict)) return NULL;
    Py_ssize_t n = members_count(members);
    if (PyTuple_GET_SIZE(vals) != n) {
        PyErr_SetString(PyExc_ValueError, "invalid pickle state: wrong number of members");
        return NULL;
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        if (members[i].type == T_OBJECT && (mask & (1ULL << i))) {
            PyObject **addr = (PyObject **)((char *)self + members[i].offset);
            Py_CLEAR(*addr);
        } else if (PyMember_SetOne((char *)self, &members[i], PyTuple_GET_ITEM(vals, i)) < 0) {
            return NULL;
        }
    }
    if (dict != Py_None) {
        if (!PyDict_Check(dict)) {
            PyErr_SetString(PyExc_ValueError, "invalid pickle state: the dict is not a dict");
            return NULL;
        }
        Py_ssize_t pos = 0;
        PyObject *k, *v;
        while (PyDict_Next(dict, &pos, &k, &v)) {
            if (PyObject_SetAttr(self, k, v) < 0) return NULL;
        }
    }
    Py_RETURN_NONE;
}

#define MEMBERS_PICKLE_METHODS(prefix, members)                                                         \
    static PyObject *prefix##_getstate(PyObject *self, PyObject *Py_UNUSED(ignored))                    \
    { return members_getstate(self, members); }                                                          \
    static PyObject *prefix##_setstate(PyObject *self, PyObject *state)                                  \
    { return members_setstate(self, state, members); }                                                   \
    static PyMethodDef prefix##_pickle_methods[] = {                                                     \
        {"__getstate__", (PyCFunction)prefix##_getstate, METH_NOARGS, "pickle support"},               \
        {"__setstate__", (PyCFunction)prefix##_setstate, METH_O, "pickle support"},                    \
        {NULL, NULL, 0, NULL}                                                                           \
    };

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
    {NULL, 0, 0, 0, NULL}
};


static PyObject *str_strip = NULL;
static PyObject *str_sent_start = NULL;     /* "SENT_START" */
static PyObject *str_sent_end = NULL;       /* "SENT_END" */
static PyObject *str_para_end = NULL;       /* "PARA_END" */
static PyObject *str_empty = NULL;          /* "" */
static PyObject *empty_tuple = NULL;
static PyObject *int_zero = NULL;
/* Python functions used by the C code (set with set_fallbacks()) */
static PyObject *fallback_is_whitespace = NULL;  /* tools.is_whitespace */
static PyObject *fallback_atr_init = NULL;       /* the Python AnalyzedTokenReadings.__init__(self, readings list, start_pos) */

/* o == the interned string s (1, 0 or -1 on error) */
static inline int
eq_str(PyObject *o, PyObject *s)
{
    if (o == s) return 1;
    if (o == NULL || o == Py_None) return 0;
    if (PyUnicode_CheckExact(o)) return unicode_eq(o, s);
    return PyObject_RichCompareBool(o, s, Py_EQ);
}

/* AnalyzedToken.__init__(token, pos_tag=None, lemma=None) */
static int
at_init(AnalyzedTokenBase *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"token", "pos_tag", "lemma", NULL};
    PyObject *token, *pos_tag = Py_None, *lemma = Py_None;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|OO", kwlist, &token, &pos_tag, &lemma)) return -1;
    if (token == Py_None) {
        PyErr_SetString(PyExc_ValueError, "token cannot be None");
        return -1;
    }
    Py_INCREF(token);
    Py_XSETREF(self->token, token);
    PyObject *pt = Py_None;
    Py_INCREF(pt);
    if (pos_tag != Py_None) {
        Py_DECREF(pt);
        pt = PyObject_CallMethodNoArgs(pos_tag, str_strip);
        if (pt == NULL) return -1;
    }
    Py_XSETREF(self->pos_tag, pt);
    Py_INCREF(lemma);
    Py_XSETREF(self->lemma, lemma);
    PyObject *lot = lemma == Py_None ? token : lemma;
    Py_INCREF(lot);
    Py_XSETREF(self->lemma_or_token, lot);
    self->whitespace_before = 0;
    int no_tag = pos_tag == Py_None;
    if (!no_tag) {
        no_tag = eq_str(pos_tag, str_sent_end);
        if (no_tag == 0) no_tag = eq_str(pos_tag, str_para_end);
        if (no_tag < 0) return -1;
    }
    self->has_no_pos_tag = (char)no_tag;
    Py_INCREF(Py_None); Py_XSETREF(self->lemma_or_token_lower, Py_None);
    Py_INCREF(Py_None); Py_XSETREF(self->token_lower, Py_None);
    Py_INCREF(Py_None); Py_XSETREF(self->lemma_lower, Py_None);
    return 0;
}

MEMBERS_PICKLE_METHODS(at, at_members)

static PyTypeObject AnalyzedTokenBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.AnalyzedTokenBase",
    .tp_basicsize = sizeof(AnalyzedTokenBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)at_dealloc,
    .tp_traverse = (traverseproc)at_traverse,
    .tp_clear = (inquiry)at_clear,
    .tp_methods = at_pickle_methods,
    .tp_members = at_members,
    .tp_init = (initproc)at_init,
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
    PyObject *start_pos, *pos_fix, *clean_token, *whitespace_before_char, *immunization_source_line,
        *historical_annotations;
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
    Py_VISIT(self->start_pos); Py_VISIT(self->pos_fix); Py_VISIT(self->clean_token);
    Py_VISIT(self->whitespace_before_char); Py_VISIT(self->immunization_source_line);
    Py_VISIT(self->historical_annotations);
    return 0;
}

static int
atr_clear(ATRBase *self)
{
    Py_CLEAR(self->readings); Py_CLEAR(self->token); Py_CLEAR(self->token_lower); Py_CLEAR(self->chunk_tags);
    Py_CLEAR(self->start_pos); Py_CLEAR(self->pos_fix); Py_CLEAR(self->clean_token);
    Py_CLEAR(self->whitespace_before_char); Py_CLEAR(self->immunization_source_line);
    Py_CLEAR(self->historical_annotations);
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
    {"start_pos", T_OBJECT, offsetof(ATRBase, start_pos), 0, NULL},
    {"pos_fix", T_OBJECT, offsetof(ATRBase, pos_fix), 0, NULL},
    {"clean_token", T_OBJECT, offsetof(ATRBase, clean_token), 0, NULL},
    {"whitespace_before_char", T_OBJECT, offsetof(ATRBase, whitespace_before_char), 0, NULL},
    {"immunization_source_line", T_OBJECT, offsetof(ATRBase, immunization_source_line), 0, NULL},
    {"historical_annotations", T_OBJECT, offsetof(ATRBase, historical_annotations), 0, NULL},
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
    {NULL, 0, 0, 0, NULL}
};


/* tools.is_whitespace(s) (1, 0 or -1 on error): the common cases here, the others with the Python function */
static int
token_is_whitespace(PyObject *s)
{
    if (PyUnicode_Check(s)) {
        Py_ssize_t n = PyUnicode_GET_LENGTH(s);
        if (n >= 2 && PyUnicode_READ_CHAR(s, 0) > ' ' && PyUnicode_READ_CHAR(s, n - 1) > ' ') {
            /* java_trim(s) == s, more than one character */
            return 0;
        }
    }
    if (fallback_is_whitespace == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "speedups.set_fallbacks() not called");
        return -1;
    }
    PyObject *r = PyObject_CallOneArg(fallback_is_whitespace, s);
    if (r == NULL) return -1;
    int t = PyObject_IsTrue(r);
    Py_DECREF(r);
    return t;
}

static int
is_linebreak_str(PyObject *s)
{
    if (!PyUnicode_Check(s)) return 0;
    Py_ssize_t n = PyUnicode_GET_LENGTH(s);
    if (n == 1) {
        Py_UCS4 c = PyUnicode_READ_CHAR(s, 0);
        return c == '\n' || c == '\r';
    }
    if (n == 2) {
        Py_UCS4 a = PyUnicode_READ_CHAR(s, 0), b = PyUnicode_READ_CHAR(s, 1);
        return (a == '\r' && b == '\n') || (a == '\n' && b == '\r');
    }
    return 0;
}

#define ATR_SET(f, v) do { PyObject *_v = (v); Py_INCREF(_v); Py_XSETREF(self->f, _v); } while (0)

/* AnalyzedTokenReadings.__init__(readings, start_pos=0) */
static int
atr_init(ATRBase *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"readings", "start_pos", NULL};
    PyObject *readings, *start_pos = int_zero;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O", kwlist, &readings, &start_pos)) return -1;
    PyObject *list;
    if (PyObject_TypeCheck(readings, &AnalyzedTokenBaseType)) {
        list = PyList_New(1);
        if (list == NULL) return -1;
        Py_INCREF(readings);
        PyList_SET_ITEM(list, 0, readings);
    } else {
        list = PySequence_List(readings);
        if (list == NULL) return -1;
    }
    Py_ssize_t n = PyList_GET_SIZE(list);
    int all_tokens = n > 0;
    for (Py_ssize_t i = 0; i < n && all_tokens; i++) {
        AnalyzedTokenBase *r = AT(PyList_GET_ITEM(list, i));
        all_tokens = PyObject_TypeCheck((PyObject *)r, &AnalyzedTokenBaseType) && r->token != NULL;
    }
    if (!all_tokens) {
        /* the Python implementation (raises the same errors) */
        if (fallback_atr_init == NULL) {
            Py_DECREF(list);
            PyErr_SetString(PyExc_RuntimeError, "speedups.set_fallbacks() not called");
            return -1;
        }
        PyObject *r = PyObject_CallFunctionObjArgs(fallback_atr_init, (PyObject *)self, list, start_pos, NULL);
        Py_DECREF(list);
        if (r == NULL) return -1;
        Py_DECREF(r);
        return 0;
    }
    Py_XSETREF(self->readings, list);
    AnalyzedTokenBase *first = AT(PyList_GET_ITEM(list, 0));
    ATR_SET(start_pos, start_pos);
    ATR_SET(pos_fix, int_zero);
    ATR_SET(token, first->token);
    ATR_SET(token_lower, Py_None);
    ATR_SET(clean_token, Py_None);
    ATR_SET(chunk_tags, empty_tuple);
    int ws = token_is_whitespace(first->token);
    if (ws < 0) return -1;
    self->is_whitespace = (char)ws;
    self->whitespace_before = first->whitespace_before;
    int lb = is_linebreak_str(first->token);
    self->is_linebreak = (char)lb;
    int r = eq_str(first->pos_tag, str_sent_start);
    if (r < 0) return -1;
    self->is_sentence_start = (char)r;
    int para_end = 0, sent_end = 0;
    for (Py_ssize_t i = 0; i < n && !para_end; i++) {
        para_end = eq_str(AT(PyList_GET_ITEM(list, i))->pos_tag, str_para_end);
        if (para_end < 0) return -1;
    }
    for (Py_ssize_t i = 0; i < n && !sent_end; i++) {
        sent_end = eq_str(AT(PyList_GET_ITEM(list, i))->pos_tag, str_sent_end);
        if (sent_end < 0) return -1;
    }
    self->is_paragraph_end = (char)para_end;
    self->is_sentence_end = (char)sent_end;
    self->is_pos_tag_unknown = n == 1 && (first->pos_tag == NULL || first->pos_tag == Py_None);
    ATR_SET(whitespace_before_char, str_empty);
    self->typographic_apostrophe = 0;
    self->immunized = 0;
    ATR_SET(immunization_source_line, int_zero);
    self->ignored_by_speller = 0;
    ATR_SET(historical_annotations, str_empty);
    /* _set_no_real_pos_tag */
    int has_no = !lb;
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *p = AT(PyList_GET_ITEM(list, i))->pos_tag;
        int e = eq_str(p, str_para_end);
        if (e == 0) e = eq_str(p, str_sent_end);
        if (e < 0) return -1;
        if (e) continue;
        if (p != NULL && p != Py_None) { has_no = 0; break; }
    }
    for (Py_ssize_t i = 0; i < n; i++) AT(PyList_GET_ITEM(list, i))->has_no_pos_tag = (char)has_no;
    /* _are_lemmas_same */
    PyObject *prev = first->lemma;
    int same = 1;
    if (prev == NULL || prev == Py_None) {
        for (Py_ssize_t i = 0; i < n && same; i++) {
            PyObject *l = AT(PyList_GET_ITEM(list, i))->lemma;
            if (l != NULL && l != Py_None) same = 0;
        }
    } else {
        for (Py_ssize_t i = 0; i < n && same; i++) {
            PyObject *l = AT(PyList_GET_ITEM(list, i))->lemma;
            int ne = PyObject_RichCompareBool(prev, l != NULL ? l : Py_None, Py_NE);
            if (ne < 0) return -1;
            if (ne) same = 0;
        }
    }
    self->has_same_lemmas = (char)same;
    return 0;
}

#undef ATR_SET

/* set_fallbacks(is_whitespace, atr_init) */
static PyObject *
py_set_fallbacks(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *iw, *ai;
    if (!PyArg_ParseTuple(args, "OO", &iw, &ai)) return NULL;
    Py_INCREF(iw); Py_XSETREF(fallback_is_whitespace, iw);
    Py_INCREF(ai); Py_XSETREF(fallback_atr_init, ai);
    Py_RETURN_NONE;
}

MEMBERS_PICKLE_METHODS(atr, atr_members)

static PyTypeObject ATRBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.AnalyzedTokenReadingsBase",
    .tp_basicsize = sizeof(ATRBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)atr_dealloc,
    .tp_traverse = (traverseproc)atr_traverse,
    .tp_clear = (inquiry)atr_clear,
    .tp_methods = atr_pickle_methods,
    .tp_members = atr_members,
    .tp_init = (initproc)atr_init,
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
    {NULL, 0, 0, 0, NULL}
};

MEMBERS_PICKLE_METHODS(sm, sm_members)

static PyTypeObject StringMatcherBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.StringMatcherBase",
    .tp_basicsize = sizeof(StringMatcherBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)sm_dealloc,
    .tp_traverse = (traverseproc)sm_traverse,
    .tp_clear = (inquiry)sm_clear,
    .tp_methods = sm_pickle_methods,
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
    {NULL, 0, 0, 0, NULL}
};

MEMBERS_PICKLE_METHODS(pos, pos_members)

static PyTypeObject PosTokenBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.PosTokenBase",
    .tp_basicsize = sizeof(PosTokenBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)pos_dealloc,
    .tp_traverse = (traverseproc)pos_traverse,
    .tp_clear = (inquiry)pos_clear,
    .tp_methods = pos_pickle_methods,
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
    {NULL, 0, 0, 0, NULL}
};

MEMBERS_PICKLE_METHODS(pt, pt_members)

static PyTypeObject PatternTokenBaseType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.PatternTokenBase",
    .tp_basicsize = sizeof(PatternTokenBase),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_dealloc = (destructor)pt_dealloc,
    .tp_traverse = (traverseproc)pt_traverse,
    .tp_clear = (inquiry)pt_clear,
    .tp_methods = pt_pickle_methods,
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
        if (PyDict_CheckExact(sm->cache) && sm->compiled != NULL && sm->compiled != Py_None) {
            /* StringMatcher._regex_match when the pattern is compiled */
            PyObject *m = PyObject_CallMethodOneArg(sm->compiled, str_fullmatch, s);
            if (m == NULL) return -1;
            int ans = m != Py_None;
            Py_DECREF(m);
            if (PyDict_GET_SIZE(sm->cache) > 50000) PyDict_Clear(sm->cache);
            if (PyDict_SetItem(sm->cache, s, ans ? Py_True : Py_False) < 0) return -1;
            return ans;
        }
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
    /* unification: the index of the first pattern token that is the same object (the readings to unify are
     * collected per pattern token object, like the dicts keyed by id(pattern token) of the Python code) */
    Py_ssize_t *canon;
    /* token references (<match no="..."/> in a token): has_refs is set if a pattern token or an AND group member
     * has a reference. ref_pos[k] is the reference of the pattern token k (REF_NONE if it has none),
     * and_start[k] the index of its first AND group member in and_ref/resolved_and. resolved[k] /
     * resolved_and[i] are the pattern tokens resolved for the current match (NULL: the pattern token itself),
     * like PatternTokenMatcher.pattern_token they are kept between the calls. */
    int has_refs;
    long *ref;
    Py_ssize_t *and_start;
    long *and_ref;
    PyObject **resolved;
    PyObject **resolved_and;
} CompiledPattern;

#define REF_NONE (-0x7fffffffL - 1)

static void
cp_free_arrays(CompiledPattern *self)
{
    if (self->resolved != NULL) {
        for (Py_ssize_t i = 0; i < self->n; i++) Py_XDECREF(self->resolved[i]);
    }
    if (self->resolved_and != NULL && self->and_start != NULL) {
        for (Py_ssize_t i = 0; i < self->and_start[self->n]; i++) Py_XDECREF(self->resolved_and[i]);
    }
    PyMem_Free(self->element_no); self->element_no = NULL;
    PyMem_Free(self->canon); self->canon = NULL;
    PyMem_Free(self->ref); self->ref = NULL;
    PyMem_Free(self->and_start); self->and_start = NULL;
    PyMem_Free(self->and_ref); self->and_ref = NULL;
    PyMem_Free(self->resolved); self->resolved = NULL;
    PyMem_Free(self->resolved_and); self->resolved_and = NULL;
}

static void
cp_dealloc(CompiledPattern *self)
{
    cp_free_arrays(self);
    Py_XDECREF(self->tokens_tuple);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

/* the token_ref of a pattern token's token_reference (REF_NONE if it has none), -2 on error (with an exception
 * set) */
static int
cp_token_ref(PatternTokenBase *pt, long *out)
{
    PyObject *tr = pt->token_reference;
    if (tr == NULL || tr == Py_None) { *out = REF_NONE; return 0; }
    PyObject *v = PyObject_GetAttrString(tr, "token_ref");
    if (v == NULL) return -1;
    long r = PyLong_AsLong(v);
    Py_DECREF(v);
    if (r == -1 && PyErr_Occurred()) return -1;
    *out = r;
    return 0;
}

static int
cp_init(CompiledPattern *self, PyObject *args, PyObject *Py_UNUSED(kwds))
{
    PyObject *tokens, *element_no;
    int moc, gou, ci;
    if (!PyArg_ParseTuple(args, "O!iiiO", &PyTuple_Type, &tokens, &moc, &gou, &ci, &element_no)) return -1;
    Py_ssize_t n = PyTuple_GET_SIZE(tokens);
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *t = PyTuple_GET_ITEM(tokens, i);
        if (!PyObject_TypeCheck(t, &PatternTokenBaseType)) {
            PyErr_SetString(PyExc_TypeError, "pattern tokens must be PatternToken instances");
            return -1;
        }
        PyObject *ag = PT(t)->and_group;
        if (ag != NULL && ag != Py_None) {
            if (!PyList_Check(ag)) {
                PyErr_SetString(PyExc_TypeError, "and_group must be a list");
                return -1;
            }
            for (Py_ssize_t j = 0; j < PyList_GET_SIZE(ag); j++) {
                if (!PyObject_TypeCheck(PyList_GET_ITEM(ag, j), &PatternTokenBaseType)) {
                    PyErr_SetString(PyExc_TypeError, "and_group members must be PatternToken instances");
                    return -1;
                }
            }
        }
    }
    cp_free_arrays(self);
    self->n = 0;
    self->min_occur_correction = moc;
    self->groups_or_unification = gou;
    self->check_immunized = ci;
    self->use_list = 0;
    self->n_element_no = 0;
    self->has_refs = 0;
    self->canon = PyMem_Calloc(n + 1, sizeof(Py_ssize_t));
    self->ref = PyMem_Calloc(n + 1, sizeof(long));
    self->and_start = PyMem_Calloc(n + 1, sizeof(Py_ssize_t));
    self->resolved = PyMem_Calloc(n + 1, sizeof(PyObject *));
    if (self->canon == NULL || self->ref == NULL || self->and_start == NULL || self->resolved == NULL) goto nomem;
    Py_ssize_t nand_total = 0;
    for (Py_ssize_t i = 0; i < n; i++) {
        PatternTokenBase *pt = PT(PyTuple_GET_ITEM(tokens, i));
        Py_ssize_t c = i;
        for (Py_ssize_t j = 0; j < i; j++) {
            if (PyTuple_GET_ITEM(tokens, j) == (PyObject *)pt) { c = j; break; }
        }
        self->canon[i] = c;
        if (cp_token_ref(pt, &self->ref[i]) < 0) goto error;
        if (self->ref[i] != REF_NONE) self->has_refs = 1;
        self->and_start[i] = nand_total;
        if (pt->and_group != NULL && pt->and_group != Py_None) nand_total += PyList_GET_SIZE(pt->and_group);
    }
    self->and_start[n] = nand_total;
    self->and_ref = PyMem_Calloc(nand_total + 1, sizeof(long));
    self->resolved_and = PyMem_Calloc(nand_total + 1, sizeof(PyObject *));
    if (self->and_ref == NULL || self->resolved_and == NULL) goto nomem;
    for (Py_ssize_t i = 0; i < n; i++) {
        PatternTokenBase *pt = PT(PyTuple_GET_ITEM(tokens, i));
        for (Py_ssize_t j = self->and_start[i]; j < self->and_start[i + 1]; j++) {
            PatternTokenBase *m = PT(PyList_GET_ITEM(pt->and_group, j - self->and_start[i]));
            if (cp_token_ref(m, &self->and_ref[j]) < 0) goto error;
            if (self->and_ref[j] != REF_NONE) self->has_refs = 1;
        }
    }
    if (element_no != Py_None) {
        PyObject *seq = PySequence_Fast(element_no, "element_no must be a sequence");
        if (seq == NULL) goto error;
        Py_ssize_t m = PySequence_Fast_GET_SIZE(seq);
        self->element_no = PyMem_Calloc(m + 1, sizeof(int));
        if (self->element_no == NULL) { Py_DECREF(seq); goto nomem; }
        for (Py_ssize_t i = 0; i < m; i++) {
            long v = PyLong_AsLong(PySequence_Fast_GET_ITEM(seq, i));
            if (v == -1 && PyErr_Occurred()) { Py_DECREF(seq); goto error; }
            self->element_no[i] = (int)v;
        }
        self->n_element_no = m;
        self->use_list = 1;
        Py_DECREF(seq);
    }
    Py_INCREF(tokens);
    Py_XSETREF(self->tokens_tuple, tokens);
    self->n = n;
    return 0;
nomem:
    PyErr_NoMemory();
error:
    cp_free_arrays(self);
    return -1;
}

typedef struct {
    CompiledPattern *cp;
    PyObject **pts;
    PyObject **tokens;    /* ATRBase */
    Py_ssize_t ntokens;
    int prev_matched;
    PyObject *resolver;   /* callable(pattern_token, atr) -> resolved pattern token, or NULL */
    int unify;            /* collect the readings to unify / the neutral readings */
    PyObject **to_unify;  /* per (canonical) pattern token: list of lists of readings, or NULL */
    PyObject **neutral;   /* per (canonical) pattern token: list of AnalyzedTokenReadings, or NULL */
} MatchCtx;

static int
translate_element_no(MatchCtx *ctx, int i)
{
    if (!ctx->cp->use_list || i < 0) return i;
    int j = 0;
    for (int k = 0; k < i && k < ctx->cp->n_element_no; k++) j += ctx->cp->element_no[k];
    return j;
}

/* the current pattern token of the pattern token k (PatternTokenMatcher.pattern_token), borrowed */
static inline PatternTokenBase *
cur_pt(MatchCtx *ctx, Py_ssize_t k)
{
    PyObject *r = ctx->cp->resolved[k];
    return PT(r != NULL ? r : ctx->pts[k]);
}

/* the current pattern token of the AND group member j of the pattern token k, borrowed */
static inline PatternTokenBase *
cur_and(MatchCtx *ctx, Py_ssize_t k, Py_ssize_t j)
{
    PyObject *r = ctx->cp->resolved_and[ctx->cp->and_start[k] + j];
    return PT(r != NULL ? r : PyList_GET_ITEM(PT(ctx->pts[k])->and_group, j));
}

/* PatternTokenMatcher.resolve_reference: *slot = resolver(base, tokens[first_match_token + ref]) if that index
 * is < the number of tokens (Python indexing, negative indices count from the end) */
static int
resolve_one(MatchCtx *ctx, PyObject *base, long ref, long first_match_token, PyObject **slot)
{
    if (ref == REF_NONE) return 0;
    long ref_pos = first_match_token + ref;
    if (ref_pos >= ctx->ntokens) return 0;
    if (ref_pos < 0) {
        ref_pos += ctx->ntokens;
        if (ref_pos < 0) {
            PyErr_SetString(PyExc_IndexError, "list index out of range");
            return -1;
        }
    }
    if (ctx->resolver == NULL) {
        PyErr_SetString(PyExc_ValueError, "pattern with token references matched without a resolver");
        return -1;
    }
    PyObject *r = PyObject_CallFunctionObjArgs(ctx->resolver, base, ctx->tokens[ref_pos], NULL);
    if (r == NULL) return -1;
    if (!PyObject_TypeCheck(r, &PatternTokenBaseType)) {
        Py_DECREF(r);
        PyErr_SetString(PyExc_TypeError, "the resolver must return a PatternToken");
        return -1;
    }
    Py_XSETREF(*slot, r);
    return 0;
}

static int
resolve_reference(MatchCtx *ctx, Py_ssize_t k, long first_match_token)
{
    return resolve_one(ctx, ctx->pts[k], ctx->cp->ref[k], first_match_token, &ctx->cp->resolved[k]);
}

/* PatternTokenMatcher.prepare_and_group (the reference resolution part) */
static int
prepare_and_group(MatchCtx *ctx, Py_ssize_t k, long first_match_token)
{
    CompiledPattern *cp = ctx->cp;
    PyObject *ag = PT(ctx->pts[k])->and_group;
    for (Py_ssize_t i = cp->and_start[k]; i < cp->and_start[k + 1]; i++) {
        if (resolve_one(ctx, PyList_GET_ITEM(ag, i - cp->and_start[k]), cp->and_ref[i], first_match_token,
                        &cp->resolved_and[i]) < 0)
            return -1;
    }
    return 0;
}

/* appends item to the list *slot (created if needed) */
static int
append_to_slot(PyObject **slot, PyObject *item)
{
    if (*slot == NULL) {
        *slot = PyList_New(0);
        if (*slot == NULL) return -1;
    }
    return PyList_Append(*slot, item);
}

#define MAX_AND_GROUP 64

/* port of AbstractPatternRulePerformer.testAllReadings (+ the immunization
 * check of PatternRuleMatcher). Returns 1, 0 or -1 on error. */
static int
test_all_readings(MatchCtx *ctx, Py_ssize_t k, Py_ssize_t prev_k, Py_ssize_t token_no, long first_match_token,
                  int prev_skip_next)
{
    ATRBase *atr = ATR(ctx->tokens[token_no]);
    if (ctx->cp->check_immunized && atr->immunized) return 0;
    PatternTokenBase *pt = PT(ctx->pts[k]);          /* matcher.base */
    if (ctx->cp->has_refs && prepare_and_group(ctx, k, first_match_token) < 0) return -1;
    PatternTokenBase *cpt = cur_pt(ctx, k);          /* matcher.pattern_token */
    PatternTokenBase *prev = prev_k >= 0 ? PT(ctx->pts[prev_k]) : NULL;
    PatternTokenBase *prev_cur = prev_k >= 0 ? cur_pt(ctx, prev_k) : NULL;
    /* keep them alive while Python code is called */
    Py_INCREF(cpt);
    Py_XINCREF(prev_cur);
    PyObject *readings = atr->readings;
    Py_INCREF(readings);
    PyObject *readings_to_unify = NULL;
    Py_ssize_t nreadings = PyList_GET_SIZE(readings);
    int any_matched = 0;
    int result = -1;
    int has_and = pt->and_group != NULL && pt->and_group != Py_None;
    Py_ssize_t nand = has_and ? PyList_GET_SIZE(pt->and_group) : 0;
    char and_check[MAX_AND_GROUP + 1];
    if (has_and) {
        if (nand > MAX_AND_GROUP || ctx->cp->and_start[k + 1] - ctx->cp->and_start[k] != nand) {
            PyErr_SetString(PyExc_ValueError, "AND group too large or modified");
            goto done;
        }
        memset(and_check, 0, nand + 1);
    }
    int prev_has_cn = prev != NULL && pt_has_current_or_next_exceptions(prev);
    int gou = ctx->cp->groups_or_unification;
    int collect = ctx->unify && pt->unification_features != NULL && pt->unification_features != Py_None &&
        !pt->unification_neutral;
    int r;
    for (Py_ssize_t i = 0; i < nreadings && i < PyList_GET_SIZE(readings); i++) {
        AnalyzedTokenBase *mt = AT(PyList_GET_ITEM(readings, i));
        if (!ctx->prev_matched && prev_skip_next > 0 && prev_cur != NULL) {
            r = pt_is_matched_by_scope_next_exception(prev_cur, mt);
            if (r < 0) goto done;
            ctx->prev_matched = r;
        }
        if (!ctx->prev_matched && prev_skip_next == 0 && token_no <= ctx->ntokens - 2) {
            ATRBase *nxt = ATR(ctx->tokens[token_no + 1]);
            r = pt_is_matched_by_scope_next_exception(cpt, AT(PyList_GET_ITEM(nxt->readings, 0)));
            if (r < 0) goto done;
            ctx->prev_matched = r;
        }
        if (ctx->prev_matched) { result = 0; goto done; }
        int reading_tested = 0, reading_matches = 0;
        if (!any_matched) {
            r = pt_is_matched(cpt, mt);
            if (r < 0) goto done;
            if (has_and) and_check[0] = and_check[0] || r;
            any_matched = reading_matches = r;
            reading_tested = 1;
        }
        if (!any_matched && !prev_has_cn) {
            if (!pt_has_pos_tag(pt)) {
                if (pt->inflected) {
                    if (atr->has_same_lemmas) { result = 0; goto done; }
                } else {
                    result = 0;
                    goto done;
                }
            } else if (!pt_pos_negation(pt) && !atr_is_tagged(atr)) {
                result = 0;
                goto done;
            }
        }
        if (gou) {
            if (!reading_tested) {
                r = pt_is_matched(cpt, mt);
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
                        r = pt_is_matched(cur_and(ctx, k, j), mt);
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
            r = pt_is_exception_matched_completely(cpt, AT(PyList_GET_ITEM(readings, i)));
            if (r < 0) goto done;
            if (r) { result = 0; goto done; }
        }
        if (token_no > 0 && pt_has_previous_exception(cpt)) {
            r = pt_is_matched_by_previous_exception(cpt, ATR(ctx->tokens[token_no - 1]));
            if (r < 0) goto done;
            if (r) { result = 0; goto done; }
        }
        if (pt->unification_neutral && ctx->unify) {
            if (append_to_slot(&ctx->neutral[ctx->cp->canon[k]], (PyObject *)atr) < 0) goto done;
        }
    }
    if (pt->chunk_tag != NULL && pt->chunk_tag != Py_None) {
        int isre = chunk_is_regexp(pt->chunk_tag);
        if (isre < 0) goto done;
        r = chunk_matches(pt->chunk_tag, atr, isre);
        if (r < 0) goto done;
        any_matched = any_matched && ((r != 0) != (pt->negation != 0));
    }
    if (has_and) {
        for (Py_ssize_t j = 0; j < nand; j++) {
            PatternTokenBase *e = PT(PyList_GET_ITEM(pt->and_group, j));
            if (e->chunk_tag != NULL && e->chunk_tag != Py_None) {
                r = chunk_matches(e->chunk_tag, atr, 0);
                if (r < 0) goto done;
                any_matched = any_matched && ((r != 0) != (e->negation != 0));
            }
        }
    }
    if (any_matched && readings_to_unify != NULL) {
        if (append_to_slot(&ctx->to_unify[ctx->cp->canon[k]], readings_to_unify) < 0) goto done;
    }
    result = any_matched;
done:
    Py_XDECREF(readings_to_unify);
    Py_DECREF(readings);
    Py_DECREF(cpt);
    Py_XDECREF(prev_cur);
    return result;
}

static int
skip_max_tokens(MatchCtx *ctx, Py_ssize_t k, Py_ssize_t prev_k, long first_match_token, int prev_skip_next,
                Py_ssize_t m, Py_ssize_t remaining)
{
    int max_skip = 0;
    int mo = PT(ctx->pts[k])->max_occurrence;
    long long max_occ = mo == -1 ? 0x7fffffffLL : mo;
    for (long long j = 1; j < max_occ && m + j < ctx->ntokens - remaining; j++) {
        int r = test_all_readings(ctx, k, prev_k, m + j, first_match_token, prev_skip_next);
        if (r < 0) return -1;
        if (r) max_skip++;
        else break;
    }
    return max_skip;
}

static void
clear_unify(MatchCtx *ctx)
{
    if (!ctx->unify) return;
    for (Py_ssize_t i = 0; i < ctx->cp->n; i++) {
        Py_CLEAR(ctx->to_unify[i]);
        Py_CLEAR(ctx->neutral[i]);
    }
}

/* calls unify(to_unify, neutral) with lists (None for the pattern tokens without readings), returns 1, 0 or -1
 * on error */
static int
call_unify(MatchCtx *ctx, PyObject *unify)
{
    Py_ssize_t n = ctx->cp->n;
    PyObject *tu = PyList_New(n);
    if (tu == NULL) return -1;
    PyObject *nl = PyList_New(n);
    if (nl == NULL) { Py_DECREF(tu); return -1; }
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *a = ctx->to_unify[i] != NULL ? ctx->to_unify[i] : Py_None;
        PyObject *b = ctx->neutral[i] != NULL ? ctx->neutral[i] : Py_None;
        Py_INCREF(a);
        Py_INCREF(b);
        PyList_SET_ITEM(tu, i, a);
        PyList_SET_ITEM(nl, i, b);
    }
    PyObject *r = PyObject_CallFunctionObjArgs(unify, tu, nl, NULL);
    Py_DECREF(tu);
    Py_DECREF(nl);
    if (r == NULL) return -1;
    int t = PyObject_IsTrue(r);
    Py_DECREF(r);
    return t;
}

/* port of AbstractPatternRulePerformer.matchFrom. Returns 1 if all pattern
 * tokens matched (and fills the output values), 0 if not, -1 on error. */
static int
match_from(MatchCtx *ctx, PyObject *unify, Py_ssize_t start_index, int *positions, int *first_out,
           int *last_out, int *first_marker_out, int *last_marker_out)
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
    clear_unify(ctx);
    for (Py_ssize_t k = 0; k < n; k++) {
        if (k > 0) prev_k = k - 1;
        if (ctx->cp->has_refs && resolve_reference(ctx, k, first_match_token) < 0) return -1;
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
            int r = test_all_readings(ctx, k, prev_k, m, first_match_token, (int)prev_skip_next);
            if (r < 0) return -1;
            all_match = r;
            if (pt->may_be_omitted) {
                int found_next = 0;
                for (Py_ssize_t k2 = k + 1; k2 < n; k2++) {
                    r = test_all_readings(ctx, k2, k, m, first_match_token, (int)prev_skip_next);
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
                int skip_for_max = skip_max_tokens(ctx, k, prev_k, first_match_token, (int)prev_skip_next, m,
                                                   n - k - 1);
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
        if (ctx->unify) {
            int u = call_unify(ctx, unify);
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

/* Runs the pattern on the tokens (an array of AnalyzedTokenReadings, kept
 * alive by the caller) from the start indices: starts[0..nstarts-1] if starts
 * is not NULL, else the range from..to (inclusive). For every match
 * consumer(*prefix, positions, first, last, first_marker, last_marker) is
 * called (prefix: a tuple or NULL), its results that are not None are appended
 * to results (if not NULL). *nmatches is incremented for every match. unify
 * and resolver: see CompiledPattern.match (Py_None if not needed). Returns 0,
 * or -1 on error. */
static int
cp_run(CompiledPattern *self, PyObject **tokens, Py_ssize_t ntokens, const long *starts, Py_ssize_t nstarts,
       long from, long to, PyObject *consumer, PyObject *prefix, PyObject *results, PyObject *unify,
       PyObject *resolver, Py_ssize_t *nmatches)
{
    /* keep the pattern tokens alive (and the arrays valid) even if the consumer re-initializes the pattern */
    PyObject *pts = self->tokens_tuple;
    if (pts == NULL) {
        PyErr_SetString(PyExc_ValueError, "CompiledPattern not initialized");
        return -1;
    }
    Py_INCREF(pts);
    Py_INCREF(self);
    MatchCtx ctx;
    ctx.cp = self;
    ctx.pts = &PyTuple_GET_ITEM(pts, 0);
    ctx.tokens = tokens;
    ctx.ntokens = ntokens;
    ctx.prev_matched = 0;
    ctx.resolver = resolver != Py_None ? resolver : NULL;
    ctx.unify = unify != Py_None;
    ctx.to_unify = NULL;
    ctx.neutral = NULL;
    Py_ssize_t n = self->n;
    Py_ssize_t nprefix = prefix != NULL ? PyTuple_GET_SIZE(prefix) : 0;
    int ret = -1;
    int *positions = PyMem_Calloc(n + 1, sizeof(int));
    if (positions == NULL) { PyErr_NoMemory(); goto done; }
    if (ctx.unify) {
        ctx.to_unify = PyMem_Calloc(n + 1, sizeof(PyObject *));
        ctx.neutral = PyMem_Calloc(n + 1, sizeof(PyObject *));
        if (ctx.to_unify == NULL || ctx.neutral == NULL) { PyErr_NoMemory(); goto done; }
    }
    if (starts != NULL) { from = 0; to = (long)nstarts - 1; }
    for (long idx = from; idx <= to; idx++) {
        long start = starts != NULL ? starts[idx] : idx;
        int first, last, fm, lm;
        if (self->n != n || self->tokens_tuple != pts) {
            PyErr_SetString(PyExc_RuntimeError, "CompiledPattern modified while matching");
            goto done;
        }
        int r = match_from(&ctx, unify, start, positions, &first, &last, &fm, &lm);
        if (r < 0) goto done;
        if (r) {
            (*nmatches)++;
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
            int vals[4];
            vals[0] = first; vals[1] = last; vals[2] = fm; vals[3] = lm;
            for (int i = 0; i < 4; i++) {
                PyObject *v = PyLong_FromLong(vals[i]);
                if (v == NULL) { Py_DECREF(cargs); goto done; }
                PyTuple_SET_ITEM(cargs, nprefix + 1 + i, v);
            }
            PyObject *res = PyObject_Call(consumer, cargs, NULL);
            Py_DECREF(cargs);
            if (res == NULL) goto done;
            if (results != NULL && res != Py_None && PyList_Append(results, res) < 0) {
                Py_DECREF(res);
                goto done;
            }
            Py_DECREF(res);
        }
    }
    ret = 0;
done:
    if (ctx.unify && ctx.to_unify != NULL && ctx.neutral != NULL) clear_unify(&ctx);
    PyMem_Free(positions);
    PyMem_Free(ctx.to_unify);
    PyMem_Free(ctx.neutral);
    Py_DECREF(pts);
    Py_DECREF(self);
    return ret;
}

/* checks that all items of the list are AnalyzedTokenReadings and returns a copy (a new reference), NULL on
 * error */
static PyObject *
checked_tokens_copy(PyObject *tokens)
{
    if (!PyList_Check(tokens)) {
        PyErr_SetString(PyExc_TypeError, "tokens must be a list");
        return NULL;
    }
    Py_ssize_t ntokens = PyList_GET_SIZE(tokens);
    for (Py_ssize_t i = 0; i < ntokens; i++) {
        if (!PyObject_TypeCheck(PyList_GET_ITEM(tokens, i), &ATRBaseType)) {
            PyErr_SetString(PyExc_TypeError, "tokens must be AnalyzedTokenReadings instances");
            return NULL;
        }
    }
    return PyList_GetSlice(tokens, 0, ntokens);
}

/* CompiledPattern.match(tokens, starts, consumer, unify=None, resolver=None)
 * tokens: list of AnalyzedTokenReadings
 * starts: list of start indices, or a (from, to) tuple (inclusive range)
 * consumer: called with (positions, first, last, first_marker, last_marker)
 * unify: for patterns with unification, called with (to_unify, neutral) when
 *   all tokens matched, the match is only accepted if it returns true.
 *   to_unify[k] is the list of the lists of readings to unify of the pattern
 *   token k, neutral[k] the list of the neutral tokens (None if empty; the
 *   entries are stored at the first index of the same pattern token object)
 * resolver: for patterns with token references, called with (pattern token,
 *   token) to get the resolved pattern token (PatternToken.compile)
 */
static PyObject *
cp_match(CompiledPattern *self, PyObject *args)
{
    PyObject *tokens, *starts, *consumer, *unify = Py_None, *resolver = Py_None;
    if (!PyArg_ParseTuple(args, "O!OO|OO", &PyList_Type, &tokens, &starts, &consumer, &unify, &resolver))
        return NULL;
    /* keep the tokens alive even if the consumer modifies the list */
    PyObject *tokens_copy = checked_tokens_copy(tokens);
    if (tokens_copy == NULL) return NULL;
    PyObject *seq = NULL;
    long *arr = NULL;
    Py_ssize_t narr = 0;
    long from = 0, to = -1;
    if (PyTuple_Check(starts)) {
        if (!PyArg_ParseTuple(starts, "ll", &from, &to)) goto error;
    } else {
        seq = PySequence_Fast(starts, "starts must be a sequence");
        if (seq == NULL) goto error;
        narr = PySequence_Fast_GET_SIZE(seq);
        arr = PyMem_Calloc(narr + 1, sizeof(long));
        if (arr == NULL) { PyErr_NoMemory(); goto error; }
        for (Py_ssize_t i = 0; i < narr; i++) {
            arr[i] = PyLong_AsLong(PySequence_Fast_GET_ITEM(seq, i));
            if (arr[i] == -1 && PyErr_Occurred()) goto error;
        }
    }
    Py_ssize_t nm = 0;
    if (cp_run(self, &PyList_GET_ITEM(tokens_copy, 0), PyList_GET_SIZE(tokens_copy), seq != NULL ? arr : NULL,
               narr, from, to, consumer, NULL, NULL, unify, resolver, &nm) < 0)
        goto error;
    Py_XDECREF(seq);
    PyMem_Free(arr);
    Py_DECREF(tokens_copy);
    Py_RETURN_NONE;
error:
    Py_XDECREF(seq);
    PyMem_Free(arr);
    Py_DECREF(tokens_copy);
    return NULL;
}

static PyMethodDef cp_methods[] = {
    {"match", (PyCFunction)cp_match, METH_VARARGS, "Match the pattern against a list of tokens"},
    {NULL, NULL, 0, NULL}
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
py_pt_is_matched(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *pt, *at;
    if (!PyArg_ParseTuple(args, "O!O!", &PatternTokenBaseType, &pt, &AnalyzedTokenBaseType, &at)) return NULL;
    int r = pt_is_matched(PT(pt), AT(at));
    if (r < 0) return NULL;
    return PyBool_FromLong(r);
}

static PyObject *
py_sm_matches(PyObject *Py_UNUSED(self), PyObject *args)
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
    PyObject *pos_tuples;  /* the pos hints as tuples (or None) */
} RuleHints;

static void
rh_dealloc(RuleHints *self)
{
    Py_XDECREF(self->hints);
    Py_XDECREF(self->pos_hints);
    Py_XDECREF(self->pos_tuples);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
rh_init(RuleHints *self, PyObject *args, PyObject *Py_UNUSED(kwds))
{
    PyObject *hints, *pos_hints;
    long mtc;
    if (!PyArg_ParseTuple(args, "lO!O", &mtc, &PyTuple_Type, &hints, &pos_hints)) return -1;
    if (pos_hints != Py_None && !PyTuple_Check(pos_hints)) {
        PyErr_SetString(PyExc_TypeError, "pos_hints must be a tuple or None");
        return -1;
    }
    Py_ssize_t nh = PyTuple_GET_SIZE(hints);
    for (Py_ssize_t i = 0; i < nh; i++) {
        PyObject *h = PyTuple_GET_ITEM(hints, i);
        if (!PyTuple_Check(h) || PyTuple_GET_SIZE(h) != 3 || !PyTuple_Check(PyTuple_GET_ITEM(h, 1)) ||
                !PyAnySet_Check(PyTuple_GET_ITEM(h, 2))) {
            PyErr_SetString(PyExc_TypeError, "hints must be (inflected, values tuple, values set) tuples");
            return -1;
        }
    }
    PyObject *pos_tuples = Py_None;
    Py_INCREF(pos_tuples);
    if (pos_hints != Py_None) {
        Py_ssize_t np = PyTuple_GET_SIZE(pos_hints);
        Py_DECREF(pos_tuples);
        pos_tuples = PyTuple_New(np);
        if (pos_tuples == NULL) return -1;
        for (Py_ssize_t i = 0; i < np; i++) {
            PyObject *ph = PyTuple_GET_ITEM(pos_hints, i);
            if (!PyAnySet_Check(ph)) {
                PyErr_SetString(PyExc_TypeError, "pos hints must be sets");
                Py_DECREF(pos_tuples);
                return -1;
            }
            PyObject *t = PySequence_Tuple(ph);
            if (t == NULL) { Py_DECREF(pos_tuples); return -1; }
            PyTuple_SET_ITEM(pos_tuples, i, t);
        }
    }
    self->min_token_count = mtc;
    Py_INCREF(hints); Py_XSETREF(self->hints, hints);
    Py_INCREF(pos_hints); Py_XSETREF(self->pos_hints, pos_hints);
    Py_XSETREF(self->pos_tuples, pos_tuples);
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

/* port of AbstractTokenBasedRule.canBeIgnoredFor: returns 1 if the rule can be
 * ignored for the sentence, 0 if not, -1 on error */
static int
rh_check(RuleHints *self, long nnb, PyObject *to, PyObject *lo, PyObject *tags, int check_pos)
{
    if (nnb < self->min_token_count) return 1;
    Py_ssize_t nh = PyTuple_GET_SIZE(self->hints);
    for (Py_ssize_t i = 0; i < nh; i++) {
        PyObject *h = PyTuple_GET_ITEM(self->hints, i);
        int inflected = PyObject_IsTrue(PyTuple_GET_ITEM(h, 0));
        if (inflected < 0) return -1;
        int r = hint_ignorable(PyTuple_GET_ITEM(h, 1), PyTuple_GET_ITEM(h, 2), inflected ? lo : to);
        if (r != 0) return r;
    }
    if (check_pos && self->pos_hints != Py_None) {
        if (!PyAnySet_Check(tags)) {
            PyErr_SetString(PyExc_TypeError, "pos_tag_set must be a set");
            return -1;
        }
        Py_ssize_t np = PyTuple_GET_SIZE(self->pos_hints);
        for (Py_ssize_t i = 0; i < np; i++) {
            PyObject *ph = PyTuple_GET_ITEM(self->pos_hints, i);
            int found = 0;
            if (PySet_GET_SIZE(ph) <= PySet_GET_SIZE(tags)) {
                PyObject *pt = PyTuple_GET_ITEM(self->pos_tuples, i);
                Py_ssize_t m = PyTuple_GET_SIZE(pt);
                for (Py_ssize_t j = 0; j < m; j++) {
                    int r = PySet_Contains(tags, PyTuple_GET_ITEM(pt, j));
                    if (r < 0) return -1;
                    if (r) { found = 1; break; }
                }
                if (!found) return 1;
                continue;
            }
            /* iterate the smaller set */
            PyObject *smaller = tags, *big = ph;
            PyObject *it = PyObject_GetIter(smaller);
            if (it == NULL) return -1;
            PyObject *item;
            while ((item = PyIter_Next(it)) != NULL) {
                int r = PySet_Contains(big, item);
                Py_DECREF(item);
                if (r < 0) { Py_DECREF(it); return -1; }
                if (r) { found = 1; break; }
            }
            Py_DECREF(it);
            if (PyErr_Occurred()) return -1;
            if (!found) return 1;
        }
    }
    return 0;
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
    int r = rh_check(self, nnb, to, lo, tags, check_pos);
    if (r < 0) return NULL;
    return PyBool_FromLong(r);
}

/* pickle support: RuleHints(min_token_count, hints, pos_hints) */
static PyObject *
rh_reduce(RuleHints *self, PyObject *Py_UNUSED(ignored))
{
    if (self->hints == NULL) {
        PyErr_SetString(PyExc_TypeError, "cannot pickle an uninitialized RuleHints");
        return NULL;
    }
    return Py_BuildValue("O(lOO)", (PyObject *)Py_TYPE(self), self->min_token_count, self->hints, self->pos_hints);
}

static PyMethodDef rh_methods[] = {
    {"ignorable", (PyCFunction)rh_ignorable, METH_VARARGS, "canBeIgnoredFor"},
    {"__reduce__", (PyCFunction)rh_reduce, METH_NOARGS, "pickle support"},
    {NULL, NULL, 0, NULL}
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

#include "_rule_tables.h"
#include "_rule_engine.h"

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
fsa_init(FSADict *self, PyObject *args, PyObject *Py_UNUSED(kwds))
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
    {NULL, NULL, 0, NULL}
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
/* morfologik Speller: the error-tolerant search (Speller.findRepl,
 * langtool.spelling.Speller._find_repl with cuted/ed/areEqual and the
 * replacement pairs). Exactly the semantics of the Python implementation,
 * including Python's index wrapping of negative indexes. */

#define SP_MAX_PREV 8

typedef struct {
    Py_UCS4 *chars;
    int len;
    int start_anchor, end_anchor;
} SpPattern;

typedef struct {
    unsigned long long key;
    int start, count;   /* range in the pattern array */
} SpKey;

typedef struct {
    PyObject_HEAD
    PyObject *eq_func;
    unsigned long long *eq_keys;   /* (x << 32 | y) + 1, 0 = empty */
    signed char *eq_vals;
    Py_ssize_t eq_cap, eq_n;
    SpKey *k1; int n1; SpPattern *p1; int np1;
    SpKey *k2; int n2; SpPattern *p2; int np2;
    int utf8;                       /* 1: UTF-8, 0: single byte table */
    int table[256];
    Py_UCS4 separator_char;
    int separator;
} SpellerSearch;

static void
sp_free_patterns(SpPattern *p, int n)
{
    if (!p) return;
    for (int i = 0; i < n; i++) PyMem_Free(p[i].chars);
    PyMem_Free(p);
}

static void
sp_dealloc(SpellerSearch *self)
{
    Py_XDECREF(self->eq_func);
    PyMem_Free(self->eq_keys);
    PyMem_Free(self->eq_vals);
    PyMem_Free(self->k1);
    PyMem_Free(self->k2);
    sp_free_patterns(self->p1, self->np1);
    sp_free_patterns(self->p2, self->np2);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
sp_key_cmp(const void *a, const void *b)
{
    unsigned long long x = ((const SpKey *)a)->key, y = ((const SpKey *)b)->key;
    return x < y ? -1 : (x > y ? 1 : 0);
}

/* items: list of (key string, [(chars, start_anchor, end_anchor), ...]) in order */
static int
sp_load_map(PyObject *items, int keylen, SpKey **keys_out, int *nk_out, SpPattern **pats_out, int *np_out)
{
    if (!PyList_Check(items)) { PyErr_SetString(PyExc_TypeError, "list expected"); return -1; }
    Py_ssize_t nk = PyList_GET_SIZE(items), np = 0;
    for (Py_ssize_t i = 0; i < nk; i++) {
        PyObject *it = PyList_GET_ITEM(items, i);
        if (!PyTuple_Check(it) || PyTuple_GET_SIZE(it) != 2 || !PyList_Check(PyTuple_GET_ITEM(it, 1))) {
            PyErr_SetString(PyExc_TypeError, "(key, list) expected"); return -1;
        }
        np += PyList_GET_SIZE(PyTuple_GET_ITEM(it, 1));
    }
    SpKey *keys = PyMem_Calloc(nk ? nk : 1, sizeof(SpKey));
    SpPattern *pats = PyMem_Calloc(np ? np : 1, sizeof(SpPattern));
    if (!keys || !pats) { PyMem_Free(keys); PyMem_Free(pats); PyErr_NoMemory(); return -1; }
    *keys_out = keys; *pats_out = pats; *nk_out = (int)nk; *np_out = 0;
    int pi = 0;
    for (Py_ssize_t i = 0; i < nk; i++) {
        PyObject *it = PyList_GET_ITEM(items, i);
        PyObject *k = PyTuple_GET_ITEM(it, 0), *lst = PyTuple_GET_ITEM(it, 1);
        if (!PyUnicode_Check(k) || PyUnicode_GET_LENGTH(k) != keylen) {
            PyErr_SetString(PyExc_ValueError, "bad key"); return -1;
        }
        unsigned long long key = PyUnicode_READ_CHAR(k, 0);
        if (keylen == 2) key = (key << 32) | PyUnicode_READ_CHAR(k, 1);
        keys[i].key = key;
        keys[i].start = pi;
        keys[i].count = (int)PyList_GET_SIZE(lst);
        for (Py_ssize_t j = 0; j < PyList_GET_SIZE(lst); j++) {
            PyObject *t = PyList_GET_ITEM(lst, j);
            PyObject *chars;
            int sa, ea;
            if (!PyArg_ParseTuple(t, "Upp", &chars, &sa, &ea)) return -1;
            Py_ssize_t n = PyUnicode_GET_LENGTH(chars);
            pats[pi].chars = PyMem_Malloc((n ? n : 1) * sizeof(Py_UCS4));
            if (!pats[pi].chars) { PyErr_NoMemory(); return -1; }
            for (Py_ssize_t c = 0; c < n; c++) pats[pi].chars[c] = PyUnicode_READ_CHAR(chars, c);
            pats[pi].len = (int)n;
            pats[pi].start_anchor = sa;
            pats[pi].end_anchor = ea;
            pi++;
            *np_out = pi;
        }
    }
    qsort(keys, nk, sizeof(SpKey), sp_key_cmp);  /* keys are distinct */
    return 0;
}

static const SpKey *
sp_find_key(const SpKey *keys, int n, unsigned long long key)
{
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        if (keys[mid].key == key) return &keys[mid];
        if (keys[mid].key < key) lo = mid + 1; else hi = mid - 1;
    }
    return NULL;
}

/* SpellerSearch(eq_func, any_to_one_items, any_to_two_items, utf8, table (list of 256 ints, -1: undecodable),
 *               separator_char, separator_byte) */
static int
sp_init(SpellerSearch *self, PyObject *args, PyObject *Py_UNUSED(kwds))
{
    PyObject *eq, *m1, *m2, *table, *sepc;
    int utf8, sep;
    if (!PyArg_ParseTuple(args, "OOOpOUi", &eq, &m1, &m2, &utf8, &table, &sepc, &sep)) return -1;
    if (PyUnicode_GET_LENGTH(sepc) != 1) { PyErr_SetString(PyExc_ValueError, "separator char"); return -1; }
    Py_INCREF(eq);
    Py_XSETREF(self->eq_func, eq);
    if (sp_load_map(m1, 1, &self->k1, &self->n1, &self->p1, &self->np1) < 0) return -1;
    if (sp_load_map(m2, 2, &self->k2, &self->n2, &self->p2, &self->np2) < 0) return -1;
    self->utf8 = utf8;
    if (!PyList_Check(table) || PyList_GET_SIZE(table) != 256) {
        PyErr_SetString(PyExc_ValueError, "table of 256 ints expected"); return -1;
    }
    for (int i = 0; i < 256; i++) {
        long v = PyLong_AsLong(PyList_GET_ITEM(table, i));
        if (v == -1 && PyErr_Occurred()) return -1;
        self->table[i] = (int)v;
    }
    self->separator_char = PyUnicode_READ_CHAR(sepc, 0);
    self->separator = sep;
    self->eq_cap = 1024;
    self->eq_keys = PyMem_Calloc(self->eq_cap, sizeof(unsigned long long));
    self->eq_vals = PyMem_Calloc(self->eq_cap, 1);
    if (!self->eq_keys || !self->eq_vals) { PyErr_NoMemory(); return -1; }
    return 0;
}

static int
sp_eq_insert(SpellerSearch *s, unsigned long long k, signed char v)
{
    if ((s->eq_n + 1) * 2 > s->eq_cap) {
        Py_ssize_t nc = s->eq_cap * 2;
        unsigned long long *nk = PyMem_Calloc(nc, sizeof(unsigned long long));
        signed char *nv = PyMem_Calloc(nc, 1);
        if (!nk || !nv) { PyMem_Free(nk); PyMem_Free(nv); PyErr_NoMemory(); return -1; }
        for (Py_ssize_t i = 0; i < s->eq_cap; i++) {
            if (s->eq_keys[i]) {
                Py_ssize_t h = (Py_ssize_t)((s->eq_keys[i] * 0x9E3779B97F4A7C15ULL) >> 20) & (nc - 1);
                while (nk[h]) h = (h + 1) & (nc - 1);
                nk[h] = s->eq_keys[i];
                nv[h] = s->eq_vals[i];
            }
        }
        PyMem_Free(s->eq_keys); PyMem_Free(s->eq_vals);
        s->eq_keys = nk; s->eq_vals = nv; s->eq_cap = nc;
    }
    Py_ssize_t h = (Py_ssize_t)((k * 0x9E3779B97F4A7C15ULL) >> 20) & (s->eq_cap - 1);
    while (s->eq_keys[h]) h = (h + 1) & (s->eq_cap - 1);
    s->eq_keys[h] = k;
    s->eq_vals[h] = v;
    s->eq_n++;
    return 0;
}

/* 1 / 0, -1 on error */
static int
sp_are_equal(SpellerSearch *s, Py_UCS4 x, Py_UCS4 y)
{
    if (x == y) return 1;
    unsigned long long k = (((unsigned long long)x << 32) | y) + 1;
    Py_ssize_t h = (Py_ssize_t)((k * 0x9E3779B97F4A7C15ULL) >> 20) & (s->eq_cap - 1);
    while (s->eq_keys[h]) {
        if (s->eq_keys[h] == k) return s->eq_vals[h];
        h = (h + 1) & (s->eq_cap - 1);
    }
    PyObject *xs = PyUnicode_FromOrdinal(x);
    if (!xs) return -1;
    PyObject *ys = PyUnicode_FromOrdinal(y);
    if (!ys) { Py_DECREF(xs); return -1; }
    PyObject *r = PyObject_CallFunctionObjArgs(s->eq_func, xs, ys, NULL);
    Py_DECREF(xs); Py_DECREF(ys);
    if (!r) return -1;
    int v = PyObject_IsTrue(r);
    Py_DECREF(r);
    if (v < 0) return -1;
    if (sp_eq_insert(s, k, (signed char)v) < 0) return -1;
    return v;
}

typedef struct {
    SpellerSearch *s;
    FSADict *d;                 /* binary FSA, or NULL for the trie */
    const int *t_first; const unsigned char *t_labels; const int *t_dests;
    const unsigned char *t_finals, *t_lasts;
    Py_ssize_t t_nnodes, t_narcs;
    const Py_UCS4 *wp; Py_ssize_t word_len;
    Py_UCS4 *cand; Py_ssize_t maxw;
    int *p; Py_ssize_t plen; Py_ssize_t rl; Py_ssize_t e1;
    int effect_ed;
    PyObject *result;
} SpCtx;

#define SP_ERR (-0x7fffffffL)

static int
sp_index_error(void)
{
    PyErr_SetString(PyExc_IndexError, "index out of range");
    return -1;
}

static int
sp_corrupt(void)
{
    if (!PyErr_Occurred()) PyErr_SetString(PyExc_ValueError, "Corrupt FSA dictionary");
    return -1;
}

/* Python list index semantics */
static inline int
sp_pidx(SpCtx *c, Py_ssize_t i, Py_ssize_t *out)
{
    if (i < 0) i += c->plen;
    if (i < 0 || i >= c->plen) return sp_index_error();
    *out = i;
    return 0;
}

static inline int
sp_wp(SpCtx *c, Py_ssize_t i, Py_UCS4 *out)
{
    if (i < 0) i += c->word_len;
    if (i < 0 || i >= c->word_len) return sp_index_error();
    *out = c->wp[i];
    return 0;
}

static inline int
sp_cand(SpCtx *c, Py_ssize_t i, Py_UCS4 *out)
{
    if (i < 0) i += c->maxw;
    if (i < 0 || i >= c->maxw) return sp_index_error();
    *out = c->cand[i];
    return 0;
}

/* H(i, j) */
static inline int
sp_hget(SpCtx *c, Py_ssize_t i, Py_ssize_t j, int *out)
{
    Py_ssize_t k;
    if (sp_pidx(c, (j - i + c->e1) * c->rl + j, &k) < 0) return -1;
    *out = c->p[k];
    return 0;
}

static inline int
sp_hset(SpCtx *c, Py_ssize_t i, Py_ssize_t j, int v)
{
    Py_ssize_t k;
    if (sp_pidx(c, (j - i + c->e1) * c->rl + j, &k) < 0) return -1;
    c->p[k] = v;
    return 0;
}

/* FSA operations, mirroring the Python FSA classes; return SP_ERR on errors */
static inline long
sp_first_arc(SpCtx *c, long node)
{
    if (c->d) return fsa_first_arc(c->d, node) < 0 ? SP_ERR : fsa_first_arc(c->d, node);
    if (node < 0 || node >= c->t_nnodes) return SP_ERR;
    return c->t_first[node];
}

static inline int
sp_arc_ok(SpCtx *c, long arc)
{
    if (c->d) return arc >= 0 && arc < c->d->narcs && !(c->d->kind == 5 && arc + 1 >= c->d->narcs)
                     && !(c->d->kind == 0xc6 && (c->d->arcs[arc] & 0x1f) == 0 && arc + 1 >= c->d->narcs);
    return arc >= 0 && arc < c->t_narcs;
}

static inline long
sp_next_arc(SpCtx *c, long arc)
{
    if (!sp_arc_ok(c, arc)) return SP_ERR;
    if (c->d) {
        if (fsa_is_last(c->d, arc)) return 0;
        long r = fsa_skip_arc(c->d, arc);
        return r < 0 ? SP_ERR : r;
    }
    return c->t_lasts[arc] ? 0 : arc + 1;
}

static inline int
sp_label(SpCtx *c, long arc)
{
    return c->d ? fsa_label(c->d, arc) : c->t_labels[arc];
}

static inline int
sp_is_final(SpCtx *c, long arc)
{
    return c->d ? fsa_is_final(c->d, arc) : c->t_finals[arc];
}

static inline long
sp_destination(SpCtx *c, long arc)
{
    if (!sp_arc_ok(c, arc)) return SP_ERR;
    if (c->d) {
        long r = fsa_destination(c->d, arc);
        return r < 0 ? SP_ERR : r;
    }
    return c->t_dests[arc];
}

static long
sp_get_arc(SpCtx *c, long node, int lbl)
{
    if (c->d) {
        long arc = sp_first_arc(c, node);
        if (arc == SP_ERR) return SP_ERR;
        while (1) {
            if (!sp_arc_ok(c, arc)) return SP_ERR;
            if (fsa_label(c->d, arc) == lbl) return arc;
            if (fsa_is_last(c->d, arc)) return 0;
            arc = fsa_skip_arc(c->d, arc);
            if (arc < 0) return SP_ERR;
        }
    }
    if (node < 0 || node >= c->t_nnodes) return SP_ERR;
    if (node == 0) return 0;  /* (no arc map) */
    long arc = c->t_first[node];
    while (1) {
        if (arc < 0 || arc >= c->t_narcs) return SP_ERR;
        if (c->t_labels[arc] == lbl) return arc;
        if (c->t_lasts[arc]) return 0;
        arc++;
    }
}

/* _is_end_of_candidate: 1/0, -1 error */
static int
sp_is_end_of_candidate(SpCtx *c, long arc, Py_ssize_t word_index)
{
    int ok = sp_is_final(c, arc);
    if (!ok) {
        long dest = sp_destination(c, arc);
        if (dest == SP_ERR) return sp_corrupt();
        long arc1 = sp_get_arc(c, dest, c->s->separator);
        if (arc1 == SP_ERR) return sp_corrupt();
        if (arc1 != 0) {
            long d2 = sp_destination(c, arc1);
            if (d2 == SP_ERR) return sp_corrupt();
            ok = d2 != 0;
        }
    }
    if (!ok) return 0;
    Py_ssize_t diff = c->word_len - 1 - word_index;
    if (diff < 0) diff = -diff;
    return diff <= c->effect_ed;
}

static int
sp_is_arc_not_terminal(SpCtx *c, long arc, Py_ssize_t cand_index)
{
    long dest = sp_destination(c, arc);
    if (dest == SP_ERR) return sp_corrupt();
    if (dest == 0) return 0;
    Py_UCS4 ch;
    if (sp_cand(c, cand_index, &ch) < 0) return -1;
    return ch != c->s->separator_char;
}

static int
sp_add_candidate(SpCtx *c, Py_ssize_t cand_index, int dist)
{
    Py_ssize_t n = cand_index + 1;
    if (n > c->maxw) n = c->maxw;
    if (n < 0) n = 0;
    PyObject *w = PyUnicode_FromKindAndData(PyUnicode_4BYTE_KIND, c->cand, n);
    if (!w) return -1;
    PyObject *t = Py_BuildValue("(Ni)", w, dist);
    if (!t) return -1;
    int r = PyList_Append(c->result, t);
    Py_DECREF(t);
    return r;
}

/* ed(i, j, word_index, cand_index) */
static int
sp_ed(SpCtx *c, Py_ssize_t i, Py_ssize_t j, Py_ssize_t word_index, Py_ssize_t cand_index, int *out)
{
    Py_ssize_t base = (j - i + c->e1) * c->rl + j, k;
    Py_UCS4 x, y;
    int result, a, b, cc;
    if (sp_wp(c, word_index, &x) < 0 || sp_cand(c, cand_index, &y) < 0) return -1;
    int eq = sp_are_equal(c->s, x, y);
    if (eq < 0) return -1;
    int transposed = 0;
    if (!eq && word_index > 0 && cand_index > 0) {
        Py_UCS4 cp, wpp;
        if (sp_cand(c, cand_index - 1, &cp) < 0) return -1;
        if (x == cp) {
            if (sp_wp(c, word_index - 1, &wpp) < 0) return -1;
            transposed = wpp == y;
        }
    }
    if (eq) {
        if (sp_pidx(c, base, &k) < 0) return -1;
        result = c->p[k];
    } else {
        if (sp_pidx(c, transposed ? base - 1 : base, &k) < 0) return -1;
        a = c->p[k];
        if (sp_pidx(c, base - c->rl, &k) < 0) return -1;
        b = c->p[k];
        if (sp_pidx(c, base + c->rl + 1, &k) < 0) return -1;
        cc = c->p[k];
        result = 1 + (a <= b && a <= cc ? a : (b <= cc ? b : cc));
    }
    if (sp_pidx(c, base + 1, &k) < 0) return -1;
    c->p[k] = result;
    *out = result;
    return 0;
}

static int
sp_cuted(SpCtx *c, Py_ssize_t depth, Py_ssize_t word_index, Py_ssize_t cand_index, int *out)
{
    int ee = c->effect_ed;
    Py_ssize_t lo = depth - ee > 0 ? depth - ee : 0;
    Py_ssize_t up = c->word_len - 1 - (word_index - depth);
    if (depth + ee < up) up = depth + ee;
    int min_ed = ee + 1;
    Py_ssize_t wi = word_index + lo - depth;
    for (Py_ssize_t i = lo; i <= up; i++) {
        int d;
        if (sp_ed(c, i, depth, wi, cand_index, &d) < 0) return -1;
        if (d < min_ed) min_ed = d;
        wi++;
    }
    *out = min_ed;
    return 0;
}

static int
sp_match_any_to_one(SpCtx *c, Py_ssize_t word_index, Py_ssize_t cand_index, int *out)
{
    Py_UCS4 ch;
    *out = 0;
    if (sp_cand(c, cand_index, &ch) < 0) return -1;
    const SpKey *k = sp_find_key(c->s->k1, c->s->n1, ch);
    if (!k) return 0;
    for (int pi = k->start; pi < k->start + k->count; pi++) {
        const SpPattern *p = &c->s->p1[pi];
        if (p->start_anchor && word_index != 0) continue;
        int i = 0;
        while (i < p->len && word_index + i < c->word_len) {
            Py_UCS4 w;
            if (sp_wp(c, word_index + i, &w) < 0) return -1;
            if (p->chars[i] != w) break;
            i++;
        }
        if (i == p->len) {
            if (p->end_anchor && word_index + i != c->word_len) continue;
            *out = i;
            return 0;
        }
    }
    return 0;
}

static int
sp_match_any_to_two(SpCtx *c, Py_ssize_t word_index, Py_ssize_t cand_index, Py_ssize_t min_lookback,
                    Py_ssize_t src_start, Py_ssize_t src_len, Py_UCS4 target, int *out)
{
    *out = 0;
    if (!(0 < cand_index && cand_index < c->maxw && word_index > 0)) return 0;
    Py_UCS4 c1 = c->cand[cand_index - 1], c2 = c->cand[cand_index];
    const SpKey *k = sp_find_key(c->s->k2, c->s->n2, ((unsigned long long)c1 << 32) | c2);
    if (!k) return 0;
    for (int pi = k->start; pi < k->start + k->count; pi++) {
        const SpPattern *p = &c->s->p2[pi];
        if (p->start_anchor && word_index - 1 != 0) continue;
        if (p->len == 2 && word_index < c->word_len) {
            Py_UCS4 w1, w2;
            if (sp_wp(c, word_index - 1, &w1) < 0) return -1;
            if (c1 == w1) {
                if (sp_wp(c, word_index, &w2) < 0) return -1;
                if (c2 == w2) { *out = 0; return 0; }  /* unnecessary replacements */
            }
        }
        int i = 0;
        while (i < p->len && word_index - 1 + i < c->word_len) {
            Py_UCS4 w;
            if (sp_wp(c, word_index - 1 + i, &w) < 0) return -1;
            if (p->chars[i] != w) break;
            i++;
        }
        if (i == p->len) {
            if (p->end_anchor && word_index - 1 + i != c->word_len) continue;
            /* Reject if this match directly reverses a previous anyToOne match at an overlapping position */
            if (word_index - 1 < min_lookback && src_len >= 0 && p->len == 1 && p->chars[0] == target
                    && src_len == 2) {
                Py_UCS4 s1, s2;
                if (sp_wp(c, src_start, &s1) < 0 || sp_wp(c, src_start + 1, &s2) < 0) return -1;
                if (s1 == c1 && s2 == c2) continue;
            }
            *out = i;
            return 0;
        }
    }
    return 0;
}

/* decoding of the accumulated bytes plus label: the character or -1 (incomplete / undecodable) */
static long
sp_decode(SpCtx *c, const unsigned char *prev, int prev_len, int label, unsigned char *buf, int *buf_len)
{
    int n = prev_len + 1;
    for (int i = 0; i < prev_len && i < SP_MAX_PREV; i++) buf[i] = prev[i];
    if (prev_len < SP_MAX_PREV) buf[prev_len] = (unsigned char)label;
    *buf_len = n;
    if (!c->s->utf8) {
        if (prev_len == 0) return c->s->table[label];
        return -1;  /* (not used: all bytes are decodable) */
    }
    if (prev_len == 0 && label < 0x80) return label;
    unsigned char lead = buf[0];
    int need = lead < 0x80 ? 1 : lead >= 0xf0 ? 4 : lead >= 0xe0 ? 3 : lead >= 0xc0 ? 2 : 0;
    if (need == 0 || n != need || n > SP_MAX_PREV) return -1;
    PyObject *u = PyUnicode_DecodeUTF8((const char *)buf, n, "strict");
    if (!u) {
        if (!PyErr_ExceptionMatches(PyExc_UnicodeDecodeError)) return -2;
        PyErr_Clear();
        return -1;
    }
    long r = PyUnicode_GET_LENGTH(u) ? (long)PyUnicode_READ_CHAR(u, 0) : -1;
    Py_DECREF(u);
    return r;
}

static int
sp_find_repl(SpCtx *c, Py_ssize_t depth, long node, const unsigned char *prev, int prev_len,
             Py_ssize_t word_index, Py_ssize_t cand_index, Py_ssize_t min_lookback,
             Py_ssize_t src_start, Py_ssize_t src_len, Py_UCS4 target)
{
    int ee = c->effect_ed;
    long arc = sp_first_arc(c, node);
    if (arc == SP_ERR) return sp_corrupt();
    while (arc != 0) {
        if (!sp_arc_ok(c, arc)) return sp_corrupt();
        int label = sp_label(c, arc);
        unsigned char buf[SP_MAX_PREV];
        int buf_len;
        long ch = sp_decode(c, prev, prev_len, label, buf, &buf_len);
        if (ch == -2) return -1;
        if (ch < 0) {
            /* incomplete multi-byte sequence: accumulate bytes and descend */
            long dest = sp_destination(c, arc);
            if (dest == SP_ERR) return sp_corrupt();
            if (dest != 0) {
                if (sp_find_repl(c, depth, dest, buf, buf_len, word_index, cand_index, min_lookback,
                                 src_start, src_len, target) < 0) return -1;
            }
        } else {
            if (ch > 0xffff) ch = 0xd800 + ((ch - 0x10000) >> 10);  /* the first UTF-16 code unit */
            Py_ssize_t ci = cand_index < 0 ? cand_index + c->maxw : cand_index;
            if (ci < 0 || ci >= c->maxw) return sp_index_error();
            c->cand[ci] = (Py_UCS4)ch;
            int lr, r;
            /* replacement "any to two" */
            if (sp_match_any_to_two(c, word_index, cand_index, min_lookback, src_start, src_len, target, &lr) < 0)
                return -1;
            if (lr > 0) {
                if ((r = sp_is_end_of_candidate(c, arc, word_index)) < 0) return -1;
                if (r) {
                    int dist;
                    if (sp_hget(c, depth - 1, depth - 1, &dist) < 0) return -1;
                    if (dist <= ee) {
                        Py_ssize_t extra = c->word_len - 1 - (word_index + lr - 2);
                        if (extra < 0) extra = -extra;
                        if (extra > 0) dist += (int)extra;
                        if (dist <= ee && sp_add_candidate(c, cand_index, dist) < 0) return -1;
                    }
                }
                if ((r = sp_is_arc_not_terminal(c, arc, cand_index)) < 0) return -1;
                if (r) {
                    int x, v;
                    if (sp_hget(c, depth, depth, &x) < 0) return -1;
                    if (sp_hget(c, depth - 1, depth - 1, &v) < 0 || sp_hset(c, depth, depth, v) < 0) return -1;
                    long dest = sp_destination(c, arc);
                    if (dest == SP_ERR) return sp_corrupt();
                    if (sp_find_repl(c, depth > 0 ? depth : 0, dest, NULL, 0, word_index + lr - 1, cand_index + 1,
                                     min_lookback, src_start, src_len, target) < 0) return -1;
                    if (sp_hset(c, depth, depth, x) < 0) return -1;
                }
            }
            /* replacement "any to one" */
            if (sp_match_any_to_one(c, word_index, cand_index, &lr) < 0) return -1;
            if (lr > 0) {
                if ((r = sp_is_end_of_candidate(c, arc, word_index)) < 0) return -1;
                if (r) {
                    int dist;
                    if (sp_hget(c, depth, depth, &dist) < 0) return -1;
                    if (dist <= ee) {
                        Py_ssize_t extra = c->word_len - 1 - (word_index + lr - 1);
                        if (extra < 0) extra = -extra;
                        if (extra > 0) dist += (int)extra;
                        if (dist <= ee && sp_add_candidate(c, cand_index, dist) < 0) return -1;
                    }
                }
                if ((r = sp_is_arc_not_terminal(c, arc, cand_index)) < 0) return -1;
                if (r) {
                    /* new_any_to_one_source = word_processed[word_index:word_index + lr] (a Python slice) */
                    Py_ssize_t s0 = word_index, s1 = word_index + lr, L = c->word_len;
                    if (s0 < 0) { s0 += L; if (s0 < 0) s0 = 0; } else if (s0 > L) s0 = L;
                    if (s1 < 0) { s1 += L; if (s1 < 0) s1 = 0; } else if (s1 > L) s1 = L;
                    Py_ssize_t slen = s1 > s0 ? s1 - s0 : 0;
                    long dest = sp_destination(c, arc);
                    if (dest == SP_ERR) return sp_corrupt();
                    if (sp_find_repl(c, depth, dest, NULL, 0, word_index + lr, cand_index + 1, word_index + lr,
                                     s0, slen, c->cand[ci]) < 0) return -1;
                }
            }
            /* general */
            int cut;
            if (sp_cuted(c, depth, word_index, cand_index, &cut) < 0) return -1;
            if (cut <= ee) {
                if ((r = sp_is_end_of_candidate(c, arc, word_index)) < 0) return -1;
                if (r) {
                    int dist;
                    if (sp_ed(c, c->word_len - 1 - (word_index - depth), depth, c->word_len - 1, cand_index, &dist) < 0)
                        return -1;
                    if (dist <= ee && sp_add_candidate(c, cand_index, dist) < 0) return -1;
                }
                if ((r = sp_is_arc_not_terminal(c, arc, cand_index)) < 0) return -1;
                if (r) {
                    long dest = sp_destination(c, arc);
                    if (dest == SP_ERR) return sp_corrupt();
                    if (sp_find_repl(c, depth + 1, dest, NULL, 0, word_index + 1, cand_index + 1, min_lookback,
                                     src_start, src_len, target) < 0) return -1;
                }
            }
        }
        arc = sp_next_arc(c, arc);
        if (arc == SP_ERR) return sp_corrupt();
    }
    return 0;
}

/* search(fsa, root, word, h_list, h_edit_distance, row_length, effect_edit_distance, max_word_length)
 * -> list of (candidate, distance). fsa is an FSADict or a tuple of bytes
 * (first (int32), labels (uint8), dests (int32), finals (uint8), lasts (uint8)) of a trie.
 * h_list (the HMatrix vector, a list of ints) is updated. */
static PyObject *
sp_search(SpellerSearch *self, PyObject *args)
{
    PyObject *fsa, *word, *hlist;
    long root;
    Py_ssize_t hed, rl, maxw;
    int effect_ed;
    if (!PyArg_ParseTuple(args, "OlUO!nnin", &fsa, &root, &word, &PyList_Type, &hlist, &hed, &rl, &effect_ed, &maxw))
        return NULL;
    SpCtx c;
    memset(&c, 0, sizeof(c));
    c.s = self;
    Py_buffer bufs[5];
    int nbufs = 0;
    if (PyObject_TypeCheck(fsa, &FSADictType)) {
        c.d = (FSADict *)fsa;
    } else {
        if (!PyTuple_Check(fsa) || PyTuple_GET_SIZE(fsa) != 5) {
            PyErr_SetString(PyExc_TypeError, "FSADict or trie arrays expected"); return NULL;
        }
        for (int i = 0; i < 5; i++) {
            if (PyObject_GetBuffer(PyTuple_GET_ITEM(fsa, i), &bufs[i], PyBUF_SIMPLE) < 0) goto fail;
            nbufs++;
        }
        c.t_first = bufs[0].buf; c.t_nnodes = bufs[0].len / (Py_ssize_t)sizeof(int);
        c.t_labels = bufs[1].buf; c.t_narcs = bufs[1].len;
        c.t_dests = bufs[2].buf; c.t_finals = bufs[3].buf; c.t_lasts = bufs[4].buf;
        if (bufs[2].len / (Py_ssize_t)sizeof(int) != c.t_narcs || bufs[3].len != c.t_narcs || bufs[4].len != c.t_narcs) {
            PyErr_SetString(PyExc_ValueError, "inconsistent trie arrays"); goto fail;
        }
    }
    {
        Py_ssize_t wl = PyUnicode_GET_LENGTH(word);
        Py_UCS4 *wp = PyUnicode_AsUCS4Copy(word);
        Py_UCS4 *cand = PyMem_Calloc(maxw > 0 ? maxw : 1, sizeof(Py_UCS4));
        Py_ssize_t plen = PyList_GET_SIZE(hlist);
        int *p = PyMem_Malloc((plen ? plen : 1) * sizeof(int));
        PyObject *result = PyList_New(0);
        if (!wp || !cand || !p || !result) {
            PyMem_Free(wp); PyMem_Free(cand); PyMem_Free(p); Py_XDECREF(result);
            if (!PyErr_Occurred()) PyErr_NoMemory();
            goto fail;
        }
        for (Py_ssize_t i = 0; i < plen; i++) {
            long v = PyLong_AsLong(PyList_GET_ITEM(hlist, i));
            if (v == -1 && PyErr_Occurred()) {
                PyMem_Free(wp); PyMem_Free(cand); PyMem_Free(p); Py_DECREF(result); goto fail;
            }
            p[i] = (int)v;
        }
        c.wp = wp; c.word_len = wl; c.cand = cand; c.maxw = maxw;
        c.p = p; c.plen = plen; c.rl = rl; c.e1 = hed + 1; c.effect_ed = effect_ed;
        c.result = result;
        int rc = sp_find_repl(&c, 0, root, NULL, 0, 0, 0, -1, 0, -1, 0);
        /* write back the HMatrix (also after errors, like the Python code would have modified it) */
        for (Py_ssize_t i = 0; i < plen; i++) {
            PyObject *v = PyLong_FromLong(p[i]);
            if (!v) { rc = -1; break; }
            PyList_SetItem(hlist, i, v);
        }
        PyMem_Free(wp); PyMem_Free(cand); PyMem_Free(p);
        for (int i = 0; i < nbufs; i++) PyBuffer_Release(&bufs[i]);
        if (rc < 0) { Py_DECREF(result); return NULL; }
        return result;
    }
fail:
    for (int i = 0; i < nbufs; i++) PyBuffer_Release(&bufs[i]);
    return NULL;
}

static PyMethodDef sp_methods[] = {
    {"search", (PyCFunction)sp_search, METH_VARARGS, "The error-tolerant search of morfologik's Speller"},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject SpellerSearchType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.SpellerSearch",
    .tp_basicsize = sizeof(SpellerSearch),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)sp_init,
    .tp_dealloc = (destructor)sp_dealloc,
    .tp_methods = sp_methods,
};

/* ------------------------------------------------------------------------ */
/* OpenNLP GIS model evaluation (langtool.opennlp.GISModel)                  */

#define GIS_MAX_OUTCOMES 1024

/* Adds the parameters of the context predicates (in their order, like
 * ArrayMath.sumFeatures) to the sums. pmap maps a predicate to a tuple
 * (outcome indices, parameters). */
/* the shared tables of a model whose pmap values are int codes (offset * number of patterns + pattern index):
 * the outcome patterns (a tuple of tuples of outcome indices) and the parameters (doubles) */
typedef struct {
    PyObject *patterns;
    const double *params;
    Py_ssize_t nparams;
} GISTables;

static int
gis_add_coded(double *sums, Py_ssize_t n, PyObject *code, GISTables *tab)
{
    if (tab == NULL || tab->patterns == NULL) {
        PyErr_SetString(PyExc_TypeError, "coded pmap values need the model tables");
        return -1;
    }
    Py_ssize_t c = PyLong_AsSsize_t(code);
    if (c == -1 && PyErr_Occurred()) return -1;
    Py_ssize_t npat = PyTuple_GET_SIZE(tab->patterns);
    if (c < 0 || npat == 0) {
        PyErr_SetString(PyExc_ValueError, "bad pmap code");
        return -1;
    }
    PyObject *outs = PyTuple_GET_ITEM(tab->patterns, c % npat);
    Py_ssize_t off = c / npat;
    if (!PyTuple_Check(outs) || off + PyTuple_GET_SIZE(outs) > tab->nparams) {
        PyErr_SetString(PyExc_ValueError, "bad pmap code");
        return -1;
    }
    for (Py_ssize_t j = 0; j < PyTuple_GET_SIZE(outs); j++) {
        Py_ssize_t oid = PyLong_AsSsize_t(PyTuple_GET_ITEM(outs, j));
        if (oid == -1 && PyErr_Occurred()) return -1;
        if (oid < 0 || oid >= n) {
            PyErr_SetString(PyExc_IndexError, "outcome index out of range");
            return -1;
        }
        sums[oid] += tab->params[off + j];
    }
    return 0;
}

static int
gis_add_features(double *sums, Py_ssize_t n, PyObject *pmap, PyObject *context, GISTables *tab)
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
        if (PyLong_Check(e)) {
            if (gis_add_coded(sums, n, e, tab) < 0) { Py_DECREF(seq); return -1; }
            continue;
        }
        if (!PyTuple_Check(e) || PyTuple_GET_SIZE(e) != 2) {
            PyErr_SetString(PyExc_TypeError, "pmap values must be (outcomes, parameters) tuples");
            Py_DECREF(seq); return -1;
        }
        PyObject *outs = PyTuple_GET_ITEM(e, 0), *params = PyTuple_GET_ITEM(e, 1);
        /* the parameters: a tuple of floats or a buffer of doubles (array('d')) */
        Py_buffer view;
        const double *pd = NULL;
        int is_tuple = PyTuple_Check(params);
        if (!is_tuple) {
            if (PyObject_GetBuffer(params, &view, PyBUF_FORMAT | PyBUF_C_CONTIGUOUS) < 0) {
                Py_DECREF(seq); return -1;
            }
            if (view.format == NULL || strcmp(view.format, "d") != 0 || view.itemsize != sizeof(double)) {
                PyBuffer_Release(&view);
                PyErr_SetString(PyExc_TypeError, "parameters must be a tuple of floats or an array of doubles");
                Py_DECREF(seq); return -1;
            }
            pd = (const double *)view.buf;
        }
        Py_ssize_t np = is_tuple ? PyTuple_GET_SIZE(params) : view.len / (Py_ssize_t)sizeof(double);
        if (!PyTuple_Check(outs) || PyTuple_GET_SIZE(outs) != np) {
            if (!is_tuple) PyBuffer_Release(&view);
            PyErr_SetString(PyExc_TypeError, "outcomes and parameters must have the same length");
            Py_DECREF(seq); return -1;
        }
        Py_ssize_t m = PyTuple_GET_SIZE(outs);
        for (Py_ssize_t j = 0; j < m; j++) {
            Py_ssize_t oid = PyLong_AsSsize_t(PyTuple_GET_ITEM(outs, j));
            double p;
            if (oid == -1 && PyErr_Occurred()) goto feature_error;
            if (is_tuple) {
                p = PyFloat_AsDouble(PyTuple_GET_ITEM(params, j));
                if (p == -1.0 && PyErr_Occurred()) goto feature_error;
            } else {
                p = pd[j];
            }
            if (oid < 0 || oid >= n) {
                PyErr_SetString(PyExc_IndexError, "outcome index out of range");
                goto feature_error;
            }
            sums[oid] += p;
        }
        if (!is_tuple) PyBuffer_Release(&view);
        continue;
feature_error:
        if (!is_tuple) PyBuffer_Release(&view);
        Py_DECREF(seq);
        return -1;
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
py_gis_sum(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *prior, *pmap, *context, *patterns = Py_None, *params = Py_None;
    double sums[GIS_MAX_OUTCOMES];
    Py_ssize_t n;
    if (!PyArg_ParseTuple(args, "OO!O|OO", &prior, &PyDict_Type, &pmap, &context, &patterns, &params)) return NULL;
    if (gis_read_prior(prior, sums, &n) < 0) return NULL;
    GISTables tab = {NULL, NULL, 0};
    Py_buffer view;
    int have_view = 0;
    if (patterns != Py_None) {
        if (!PyTuple_Check(patterns)) {
            PyErr_SetString(PyExc_TypeError, "patterns must be a tuple");
            return NULL;
        }
        if (PyObject_GetBuffer(params, &view, PyBUF_FORMAT | PyBUF_C_CONTIGUOUS) < 0) return NULL;
        have_view = 1;
        if (view.format == NULL || strcmp(view.format, "d") != 0 || view.itemsize != sizeof(double)) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_TypeError, "params must be an array of doubles");
            return NULL;
        }
        tab.patterns = patterns;
        tab.params = (const double *)view.buf;
        tab.nparams = view.len / (Py_ssize_t)sizeof(double);
    }
    int r = gis_add_features(sums, n, pmap, context, &tab);
    if (have_view) PyBuffer_Release(&view);
    if (r < 0) return NULL;
    return gis_make_list(sums, n);
}

/* gis_eval(prior, pmap, context) -> the probabilities of GISModel.eval (exp and normalization of the sums), or
 * None if the sum of the exps is 0 or infinite (the caller handles these cases) */
static PyObject *
py_gis_eval(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *prior, *pmap, *context, *patterns = Py_None, *params = Py_None;
    double sums[GIS_MAX_OUTCOMES];
    Py_ssize_t n;
    if (!PyArg_ParseTuple(args, "OO!O|OO", &prior, &PyDict_Type, &pmap, &context, &patterns, &params)) return NULL;
    if (gis_read_prior(prior, sums, &n) < 0) return NULL;
    GISTables tab = {NULL, NULL, 0};
    Py_buffer view;
    int have_view = 0;
    if (patterns != Py_None) {
        if (!PyTuple_Check(patterns)) {
            PyErr_SetString(PyExc_TypeError, "patterns must be a tuple");
            return NULL;
        }
        if (PyObject_GetBuffer(params, &view, PyBUF_FORMAT | PyBUF_C_CONTIGUOUS) < 0) return NULL;
        have_view = 1;
        if (view.format == NULL || strcmp(view.format, "d") != 0 || view.itemsize != sizeof(double)) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_TypeError, "params must be an array of doubles");
            return NULL;
        }
        tab.patterns = patterns;
        tab.params = (const double *)view.buf;
        tab.nparams = view.len / (Py_ssize_t)sizeof(double);
    }
    int r = gis_add_features(sums, n, pmap, context, &tab);
    if (have_view) PyBuffer_Release(&view);
    if (r < 0) return NULL;
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
py_levenshtein(PyObject *Py_UNUSED(self), PyObject *args)
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

/* ------------------------------------------------------------------------ */
/* AnalyzedSentence.__init__: the non blank tokens and the token / lemma /
 * POS tag indexes */

static int
nb_tokens(PyObject *tokens, PyObject *mapping, PyObject **out)
{
    Py_ssize_t n = PyList_GET_SIZE(tokens);
    PyObject *l = PyList_New(0);
    if (l == NULL) return -1;
    Py_ssize_t nwh = 0;
    for (Py_ssize_t wh = 0; wh < n; wh++) {
        ATRBase *t = ATR(PyList_GET_ITEM(tokens, wh));
        if (!t->is_whitespace || t->is_sentence_start || t->is_sentence_end || t->is_paragraph_end) {
            if (PyList_Append(l, (PyObject *)t) < 0) { Py_DECREF(l); return -1; }
            if (nwh >= PyList_GET_SIZE(mapping)) {
                Py_DECREF(l);
                PyErr_SetString(PyExc_IndexError, "list assignment index out of range");
                return -1;
            }
            PyObject *v = PyLong_FromSsize_t(wh);
            if (v == NULL) { Py_DECREF(l); return -1; }
            if (PyList_SetItem(mapping, nwh, v) < 0) { Py_DECREF(l); return -1; }
            nwh++;
        }
    }
    *out = l;
    return 0;
}

/* appends i to index[key] (a new list if needed), only if it is not the last element (unique = 1) */
static int
index_add(PyObject *index, PyObject *key, Py_ssize_t i, int unique)
{
    PyObject *lst = PyDict_GetItemWithError(index, key);
    if (lst == NULL) {
        if (PyErr_Occurred()) return -1;
        lst = PyList_New(0);
        if (lst == NULL) return -1;
        int r = PyDict_SetItem(index, key, lst);
        Py_DECREF(lst);
        if (r < 0) return -1;
    } else if (unique) {
        Py_ssize_t m = PyList_GET_SIZE(lst);
        if (m > 0) {
            Py_ssize_t last = PyLong_AsSsize_t(PyList_GET_ITEM(lst, m - 1));
            if (last == -1 && PyErr_Occurred()) return -1;
            if (last == i) return 0;
        }
    }
    PyObject *v = PyLong_FromSsize_t(i);
    if (v == NULL) return -1;
    int r = PyList_Append(lst, v);
    Py_DECREF(v);
    return r;
}

/* the lowercase version of a cached string slot (computed from src if not set yet), borrowed */
static PyObject *
cached_lower(PyObject **slot, PyObject *src)
{
    if (*slot == NULL || *slot == Py_None) {
        if (src == NULL) {
            PyErr_SetString(PyExc_AttributeError, "token not initialized");
            return NULL;
        }
        PyObject *l = PyObject_CallMethodNoArgs(src, str_lower);
        if (l == NULL) return NULL;
        Py_XSETREF(*slot, l);
    }
    return *slot;
}

/* sentence_index(tokens, pre_disambig_tokens, previous, readings_unchanged) ->
 * (wh_positions, non_blank_tokens, non_blank_pre_disambig_tokens,
 * token_offsets, lemma_offsets, pos_tag_set), or None if the tokens are not
 * all AnalyzedTokenReadings (with AnalyzedToken readings) */
static PyObject *
py_sentence_index(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *tokens, *pre, *previous;
    int readings_unchanged;
    if (!PyArg_ParseTuple(args, "OOOp", &tokens, &pre, &previous, &readings_unchanged)) return NULL;
    if (!PyList_Check(tokens) || !PyList_Check(pre)) Py_RETURN_NONE;
    PyObject *lists[2] = {tokens, pre};
    for (int k = 0; k < 2; k++) {
        for (Py_ssize_t i = 0; i < PyList_GET_SIZE(lists[k]); i++) {
            PyObject *t = PyList_GET_ITEM(lists[k], i);
            if (!PyObject_TypeCheck(t, &ATRBaseType) || ATR(t)->readings == NULL || !PyList_Check(ATR(t)->readings))
                Py_RETURN_NONE;
            PyObject *rs = ATR(t)->readings;
            for (Py_ssize_t j = 0; j < PyList_GET_SIZE(rs); j++) {
                if (!PyObject_TypeCheck(PyList_GET_ITEM(rs, j), &AnalyzedTokenBaseType)) Py_RETURN_NONE;
            }
        }
    }
    PyObject *mapping = NULL, *nb = NULL, *nb_pre = NULL, *to = NULL, *lo = NULL, *tags = NULL, *pnb = NULL;
    Py_ssize_t n = PyList_GET_SIZE(tokens);
    mapping = PyList_New(n + 1);
    if (mapping == NULL) goto error;
    for (Py_ssize_t i = 0; i <= n; i++) {
        PyObject *z = PyLong_FromLong(0);
        if (z == NULL) goto error;
        PyList_SET_ITEM(mapping, i, z);
    }
    if (nb_tokens(tokens, mapping, &nb) < 0) goto error;
    if (nb_tokens(pre, mapping, &nb_pre) < 0) goto error;
    Py_ssize_t nnb = PyList_GET_SIZE(nb);
    int same_tokens = 0;
    if (previous != Py_None) {
        pnb = PyObject_GetAttr(previous, str_non_blank_tokens);
        if (pnb == NULL) goto error;
        if (!PyList_Check(pnb)) {
            PyErr_SetString(PyExc_TypeError, "non_blank_tokens must be a list");
            goto error;
        }
        same_tokens = PyList_GET_SIZE(pnb) == nnb;
        for (Py_ssize_t i = 0; same_tokens && i < nnb; i++) {
            PyObject *x = PyObject_GetAttr(PyList_GET_ITEM(pnb, i), str_token);
            if (x == NULL) goto error;
            int eq = PyObject_RichCompareBool(x, ATR(PyList_GET_ITEM(nb, i))->token, Py_EQ);
            Py_DECREF(x);
            if (eq < 0) goto error;
            same_tokens = eq;
        }
    }
    if (same_tokens) {
        to = PyObject_GetAttr(previous, str_token_offsets);
        if (to == NULL) goto error;
    } else {
        to = PyDict_New();
        if (to == NULL) goto error;
        for (Py_ssize_t i = 0; i < nnb; i++) {
            ATRBase *t = ATR(PyList_GET_ITEM(nb, i));
            PyObject *key = cached_lower(&t->token_lower, t->token);
            if (key == NULL || index_add(to, key, i, 0) < 0) goto error;
        }
    }
    if (same_tokens && readings_unchanged) {
        lo = PyObject_GetAttr(previous, str_lemma_offsets);
        if (lo == NULL) goto error;
        tags = PyObject_GetAttr(previous, str_pos_tag_set);
        if (tags == NULL) goto error;
    } else {
        lo = PyDict_New();
        if (lo == NULL) goto error;
        PyObject *set = PySet_New(NULL);
        if (set == NULL) goto error;
        for (Py_ssize_t i = 0; i < nnb; i++) {
            PyObject *rs = ATR(PyList_GET_ITEM(nb, i))->readings;
            for (Py_ssize_t j = 0; j < PyList_GET_SIZE(rs); j++) {
                AnalyzedTokenBase *r = AT(PyList_GET_ITEM(rs, j));
                PyObject *key = cached_lower(&r->lemma_or_token_lower, r->lemma_or_token);
                if (key == NULL || index_add(lo, key, i, 1) < 0) { Py_DECREF(set); goto error; }
            }
        }
        for (Py_ssize_t i = 0; i < nnb; i++) {
            PyObject *rs = ATR(PyList_GET_ITEM(nb, i))->readings;
            for (Py_ssize_t j = 0; j < PyList_GET_SIZE(rs); j++) {
                AnalyzedTokenBase *r = AT(PyList_GET_ITEM(rs, j));
                if (r->pos_tag != NULL && r->pos_tag != Py_None && PySet_Add(set, r->pos_tag) < 0) {
                    Py_DECREF(set);
                    goto error;
                }
            }
        }
        tags = PyFrozenSet_New(set);
        Py_DECREF(set);
        if (tags == NULL) goto error;
    }
    Py_XDECREF(pnb);
    PyObject *res = PyTuple_Pack(6, mapping, nb, nb_pre, to, lo, tags);
    Py_DECREF(mapping); Py_DECREF(nb); Py_DECREF(nb_pre); Py_DECREF(to); Py_DECREF(lo); Py_DECREF(tags);
    return res;
error:
    Py_XDECREF(mapping); Py_XDECREF(nb); Py_XDECREF(nb_pre); Py_XDECREF(to); Py_XDECREF(lo); Py_XDECREF(tags);
    Py_XDECREF(pnb);
    return NULL;
}

/* ------------------------------------------------------------------------ */
/* OpenNLP beam search (langtool.opennlp.BeamSearch.best_sequences) */

/* a sequence: the Python tuple (score, outcome, parent, probability) and its score */
typedef struct {
    double score;
    PyObject *seq;   /* new reference */
} BSItem;

/* java.util.PriorityQueue (the highest score first, see _JavaPriorityQueue) */
typedef struct {
    BSItem *q;
    Py_ssize_t n, cap;
} BSQueue;

static int
bsq_add(BSQueue *h, double score, PyObject *seq)
{
    if (h->n == h->cap) {
        Py_ssize_t cap = h->cap ? h->cap * 2 : 64;
        BSItem *q = PyMem_Realloc(h->q, cap * sizeof(BSItem));
        if (q == NULL) { PyErr_NoMemory(); return -1; }
        h->q = q;
        h->cap = cap;
    }
    Py_ssize_t k = h->n++;
    while (k > 0) {
        Py_ssize_t parent = (k - 1) >> 1;
        if (h->q[parent].score >= score) break;
        h->q[k] = h->q[parent];
        k = parent;
    }
    h->q[k].score = score;
    h->q[k].seq = seq;
    return 0;
}

/* removes the first item (the caller owns the reference) */
static BSItem
bsq_remove(BSQueue *h)
{
    BSItem result = h->q[0];
    BSItem x = h->q[--h->n];
    Py_ssize_t n = h->n;
    if (n > 0) {
        Py_ssize_t k = 0, half = n >> 1;
        while (k < half) {
            Py_ssize_t child = 2 * k + 1, right = child + 1;
            if (right < n && h->q[right].score > h->q[child].score) child = right;
            if (x.score >= h->q[child].score) break;
            h->q[k] = h->q[child];
            k = child;
        }
        h->q[k] = x;
    }
    return result;
}

static void
bsq_clear(BSQueue *h)
{
    for (Py_ssize_t i = 0; i < h->n; i++) Py_DECREF(h->q[i].seq);
    h->n = 0;
}

/* the expansions of a (scores, allowed outcomes) pair */
typedef struct {
    PyObject *scores, *allowed;   /* new references (kept, so the pointers are not reused) */
    PyObject *sf;                 /* the scores as a list or tuple (new reference) */
    double *probs;                /* the scores */
    Py_ssize_t nprobs;
    Py_ssize_t *ext;              /* the outcomes with one of the best scores (in the order of the outcomes) */
    Py_ssize_t next;
    Py_ssize_t *valid;            /* the allowed outcomes (or all) */
    Py_ssize_t nvalid;
} BSExp;

static void
bsexp_free(BSExp *e)
{
    Py_XDECREF(e->scores);
    Py_XDECREF(e->allowed);
    Py_XDECREF(e->sf);
    PyMem_Free(e->probs);
    PyMem_Free(e->ext);
    PyMem_Free(e->valid);
}

static int
cmp_double_nan_last(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;
    int xn = x != x, yn = y != y;
    if (xn || yn) return xn - yn;
    return (x > y) - (x < y);
}

/* StrictMath.log (see opennlp._log) */
static inline double
bs_log(double p)
{
    if (p > 0) return log(p);
    return p == 0 ? -INFINITY : NAN;
}

/* fills the expansion e for scores / allowed; returns 0 or -1 on error */
static int
bsexp_init(BSExp *e, PyObject *scores, PyObject *allowed, Py_ssize_t n_outcomes, Py_ssize_t size_index)
{
    memset(e, 0, sizeof(BSExp));
    Py_INCREF(scores); e->scores = scores;
    Py_INCREF(allowed); e->allowed = allowed;
    PyObject *sf = PySequence_Fast(scores, "the scores must be a sequence");
    if (sf == NULL) return -1;
    e->sf = sf;
    Py_ssize_t np = PySequence_Fast_GET_SIZE(sf);
    if (np != n_outcomes) {
        PyErr_SetString(PyExc_ValueError, "the number of scores must be the number of outcomes");
        return -1;
    }
    if (size_index >= np) {
        PyErr_SetString(PyExc_IndexError, "list index out of range");
        return -1;
    }
    e->probs = PyMem_Calloc(np + 1, sizeof(double));
    double *sorted = PyMem_Calloc(np + 1, sizeof(double));
    if (e->probs == NULL || sorted == NULL) { PyMem_Free(sorted); PyErr_NoMemory(); return -1; }
    e->nprobs = np;
    for (Py_ssize_t i = 0; i < np; i++) {
        double d = PyFloat_AsDouble(PySequence_Fast_GET_ITEM(sf, i));
        if (d == -1.0 && PyErr_Occurred()) { PyMem_Free(sorted); return -1; }
        e->probs[i] = sorted[i] = d;
    }
    qsort(sorted, np, sizeof(double), cmp_double_nan_last);
    double min_score = sorted[size_index];
    PyMem_Free(sorted);
    if (allowed == Py_None) {
        e->valid = PyMem_Calloc(np + 1, sizeof(Py_ssize_t));
        if (e->valid == NULL) { PyErr_NoMemory(); return -1; }
        for (Py_ssize_t i = 0; i < np; i++) e->valid[i] = i;
        e->nvalid = np;
    } else {
        PyObject *af = PySequence_Fast(allowed, "the allowed outcomes must be a sequence");
        if (af == NULL) return -1;
        Py_ssize_t na = PySequence_Fast_GET_SIZE(af);
        e->valid = PyMem_Calloc(na + 1, sizeof(Py_ssize_t));
        if (e->valid == NULL) { Py_DECREF(af); PyErr_NoMemory(); return -1; }
        for (Py_ssize_t i = 0; i < na; i++) {
            Py_ssize_t v = PyLong_AsSsize_t(PySequence_Fast_GET_ITEM(af, i));
            if (v == -1 && PyErr_Occurred()) { Py_DECREF(af); return -1; }
            if (v < 0 || v >= np) {
                Py_DECREF(af);
                PyErr_SetString(PyExc_IndexError, "outcome index out of range");
                return -1;
            }
            e->valid[i] = v;
        }
        e->nvalid = na;
        Py_DECREF(af);
    }
    e->ext = PyMem_Calloc(e->nvalid + 1, sizeof(Py_ssize_t));
    if (e->ext == NULL) { PyErr_NoMemory(); return -1; }
    for (Py_ssize_t i = 0; i < e->nvalid; i++) {
        Py_ssize_t p = e->valid[i];
        if (e->probs[p] >= min_score) e->ext[e->next++] = p;
    }
    return 0;
}

/* the sequence tuple (score, names[p], parent, scores[p]) */
static PyObject *
bs_sequence(double score, PyObject *names, BSExp *ex, Py_ssize_t p, PyObject *parent)
{
    PyObject *s = PyFloat_FromDouble(score);
    if (s == NULL) return NULL;
    PyObject *t = PyTuple_Pack(4, s, PyList_GET_ITEM(names, p), parent, PySequence_Fast_GET_ITEM(ex->sf, p));
    Py_DECREF(s);
    return t;
}

/* beam_search(size, num_sequences, length, outcome_names, evaluate, allowed_outcomes, min_sequence_score,
 * empty_sequence) -> the best sequences (see BeamSearch.best_sequences) */
static PyObject *
py_beam_search(PyObject *Py_UNUSED(self), PyObject *args)
{
    Py_ssize_t size, num_sequences, length;
    PyObject *names, *evaluate, *allowed_outcomes, *empty;
    double min_sequence_score;
    if (!PyArg_ParseTuple(args, "nnnO!OOdO", &size, &num_sequences, &length, &PyList_Type, &names, &evaluate,
                          &allowed_outcomes, &min_sequence_score, &empty))
        return NULL;
    Py_ssize_t n_outcomes = PyList_GET_SIZE(names);
    if (n_outcomes == 0) {
        PyErr_SetString(PyExc_ValueError, "no outcomes");
        return NULL;
    }
    Py_ssize_t size_index = n_outcomes - size > 0 ? n_outcomes - size : 0;
    BSQueue heap = {NULL, 0, 0};
    BSExp *exps = NULL;
    Py_ssize_t nexps = 0, capexps = 0;
    PyObject *expindex = PyDict_New();   /* (id(scores), id(allowed)) -> index in exps */
    PyObject *result = NULL;
    /* the current tops (new references) */
    PyObject **tops = PyMem_Calloc(size + 2, sizeof(PyObject *));
    Py_ssize_t ntops = 0;
    /* the expansion index of each top */
    Py_ssize_t *topexp = PyMem_Calloc(size + 2, sizeof(Py_ssize_t));
    if (expindex == NULL || tops == NULL || topexp == NULL) { PyErr_NoMemory(); goto done; }
    Py_INCREF(empty);
    tops[ntops++] = empty;
    for (Py_ssize_t i = 0; i < length; i++) {
        PyObject *idx = PyLong_FromSsize_t(i);
        if (idx == NULL) goto done;
        for (Py_ssize_t t = 0; t < ntops; t++) {
            PyObject *scores = PyObject_CallFunctionObjArgs(evaluate, idx, tops[t], NULL);
            if (scores == NULL) { Py_DECREF(idx); goto done; }
            PyObject *allowed = PyObject_CallFunctionObjArgs(allowed_outcomes, idx, tops[t], NULL);
            if (allowed == NULL) { Py_DECREF(scores); Py_DECREF(idx); goto done; }
            PyObject *key = Py_BuildValue("(NN)", PyLong_FromVoidPtr(scores), PyLong_FromVoidPtr(allowed));
            if (key == NULL) { Py_DECREF(scores); Py_DECREF(allowed); Py_DECREF(idx); goto done; }
            PyObject *ei = PyDict_GetItemWithError(expindex, key);
            Py_ssize_t e;
            if (ei != NULL) {
                e = PyLong_AsSsize_t(ei);
            } else if (PyErr_Occurred()) {
                e = -1;
            } else {
                if (nexps == capexps) {
                    Py_ssize_t cap = capexps ? capexps * 2 : 16;
                    BSExp *ne = PyMem_Realloc(exps, cap * sizeof(BSExp));
                    if (ne == NULL) {
                        PyErr_NoMemory();
                        Py_DECREF(key); Py_DECREF(scores); Py_DECREF(allowed); Py_DECREF(idx);
                        goto done;
                    }
                    exps = ne;
                    capexps = cap;
                }
                e = nexps;
                int r = bsexp_init(&exps[nexps], scores, allowed, n_outcomes, size_index);
                nexps++;   /* (freed in any case) */
                if (r < 0) {
                    e = -1;
                } else {
                    PyObject *v = PyLong_FromSsize_t(e);
                    if (v == NULL || PyDict_SetItem(expindex, key, v) < 0) e = -1;
                    Py_XDECREF(v);
                }
            }
            Py_DECREF(key);
            Py_DECREF(scores);
            Py_DECREF(allowed);
            if (e < 0) { Py_DECREF(idx); goto done; }
            topexp[t] = e;
        }
        Py_DECREF(idx);
        /* the candidates, in the order of _candidates(prune=False), added to the queue */
        int added = 0;
        for (Py_ssize_t t = 0; t < ntops; t++) {
            BSExp *ex = &exps[topexp[t]];
            PyObject *sc = PyTuple_GET_ITEM(tops[t], 0);
            double top_score = PyFloat_AsDouble(sc);
            if (top_score == -1.0 && PyErr_Occurred()) goto done;
            for (Py_ssize_t j = 0; j < ex->next; j++) {
                Py_ssize_t p = ex->ext[j];
                double ns = top_score + bs_log(ex->probs[p]);
                if (ns > min_sequence_score) {
                    PyObject *s = bs_sequence(ns, names, ex, p, tops[t]);
                    if (s == NULL || bsq_add(&heap, ns, s) < 0) { Py_XDECREF(s); goto done; }
                    added = 1;
                }
            }
            if (!added) {
                for (Py_ssize_t j = 0; j < ex->nvalid; j++) {
                    Py_ssize_t p = ex->valid[j];
                    double ns = top_score + bs_log(ex->probs[p]);
                    if (ns > min_sequence_score) {
                        PyObject *s = bs_sequence(ns, names, ex, p, tops[t]);
                        if (s == NULL || bsq_add(&heap, ns, s) < 0) { Py_XDECREF(s); goto done; }
                        added = 1;
                    }
                }
            }
        }
        for (Py_ssize_t t = 0; t < ntops; t++) Py_DECREF(tops[t]);
        ntops = 0;
        while (ntops < size && heap.n > 0) {
            BSItem it = bsq_remove(&heap);
            tops[ntops++] = it.seq;
        }
        bsq_clear(&heap);
    }
    {
        Py_ssize_t k = num_sequences < ntops ? num_sequences : ntops;
        if (k < 0) k = 0;
        result = PyList_New(k);
        if (result == NULL) goto done;
        for (Py_ssize_t t = 0; t < k; t++) {
            Py_INCREF(tops[t]);
            PyList_SET_ITEM(result, t, tops[t]);
        }
    }
done:
    bsq_clear(&heap);
    PyMem_Free(heap.q);
    for (Py_ssize_t t = 0; t < ntops; t++) Py_DECREF(tops[t]);
    PyMem_Free(tops);
    PyMem_Free(topexp);
    for (Py_ssize_t e = 0; e < nexps; e++) bsexp_free(&exps[e]);
    PyMem_Free(exps);
    Py_XDECREF(expindex);
    return result;
}

/* ------------------------------------------------------------------------ */
/* the trie of langtool.spelling._TrieFSA */

typedef struct {
    unsigned char label;
    int child;
    char child_final;
} TrieArc;

typedef struct {
    TrieArc *arcs;
    Py_ssize_t n, cap;
    char final;
} TrieNode;

typedef struct {
    char *data;
    Py_ssize_t n, cap, itemsize;
} TrieBuf;

static int
tbuf_add(TrieBuf *b, const void *item)
{
    if (b->n == b->cap) {
        Py_ssize_t cap = b->cap ? b->cap * 2 : 1024;
        char *d = PyMem_Realloc(b->data, cap * b->itemsize);
        if (d == NULL) { PyErr_NoMemory(); return -1; }
        b->data = d;
        b->cap = cap;
    }
    memcpy(b->data + b->n * b->itemsize, item, b->itemsize);
    b->n++;
    return 0;
}

typedef struct {
    TrieBuf first, ends, labels, dests, finals, lasts;
} Trie;

/* finish(arcs) of _TrieFSA.__init__: the number of the node (0 if it has no arcs) */
static int
trie_finish(Trie *t, TrieNode *node, int *out)
{
    if (node->n == 0) { *out = 0; return 0; }
    int nid = (int)t->first.n;
    int fa = (int)t->labels.n;
    if (tbuf_add(&t->first, &fa) < 0) return -1;
    for (Py_ssize_t k = 0; k < node->n; k++) {
        TrieArc *a = &node->arcs[k];
        char last = k == node->n - 1;
        if (tbuf_add(&t->labels, &a->label) < 0 || tbuf_add(&t->dests, &a->child) < 0 ||
                tbuf_add(&t->finals, &a->child_final) < 0 || tbuf_add(&t->lasts, &last) < 0)
            return -1;
    }
    int end = (int)t->labels.n;
    if (tbuf_add(&t->ends, &end) < 0) return -1;
    *out = nid;
    return 0;
}

static int
tnode_add_arc(TrieNode *node, unsigned char label)
{
    if (node->n == node->cap) {
        Py_ssize_t cap = node->cap ? node->cap * 2 : 4;
        TrieArc *a = PyMem_Realloc(node->arcs, cap * sizeof(TrieArc));
        if (a == NULL) { PyErr_NoMemory(); return -1; }
        node->arcs = a;
        node->cap = cap;
    }
    node->arcs[node->n].label = label;
    node->arcs[node->n].child = 0;
    node->arcs[node->n].child_final = 0;
    node->n++;
    return 0;
}

/* build_trie(sequences) -> (root, first, ends, labels, dests, finals, lasts): the trie of the sorted byte
 * sequences, numbered like the Python implementation (first, ends and dests are arrays of C ints as bytes,
 * node 0 is the terminal node) */
static PyObject *
py_build_trie(PyObject *Py_UNUSED(self), PyObject *arg)
{
    PyObject *seqs = PySequence_Fast(arg, "sequences must be a sequence");
    if (seqs == NULL) return NULL;
    Trie t;
    memset(&t, 0, sizeof(t));
    t.first.itemsize = t.ends.itemsize = t.dests.itemsize = sizeof(int);
    t.labels.itemsize = t.finals.itemsize = t.lasts.itemsize = 1;
    TrieNode *stack = NULL;
    Py_ssize_t depth = 0, stack_cap = 0;   /* stack[0..depth] */
    PyObject *result = NULL;
    int zero = 0;
    unsigned char zb = 0;
    /* node 0 / arc 0 */
    if (tbuf_add(&t.first, &zero) < 0 || tbuf_add(&t.ends, &zero) < 0 || tbuf_add(&t.labels, &zb) < 0 ||
            tbuf_add(&t.dests, &zero) < 0 || tbuf_add(&t.finals, &zb) < 0 || tbuf_add(&t.lasts, &zb) < 0)
        goto done;
    stack_cap = 64;
    stack = PyMem_Calloc(stack_cap, sizeof(TrieNode));
    if (stack == NULL) { PyErr_NoMemory(); goto done; }
    const char *prev = "";
    Py_ssize_t prev_len = 0;
    Py_ssize_t nseq = PySequence_Fast_GET_SIZE(seqs);
    for (Py_ssize_t i = 0; i < nseq; i++) {
        PyObject *so = PySequence_Fast_GET_ITEM(seqs, i);
        if (!PyBytes_Check(so)) {
            PyErr_SetString(PyExc_TypeError, "sequences must be bytes");
            goto done;
        }
        const char *seq = PyBytes_AS_STRING(so);
        Py_ssize_t len = PyBytes_GET_SIZE(so);
        Py_ssize_t n = prev_len < len ? prev_len : len, k = 0;
        while (k < n && prev[k] == seq[k]) k++;
        while (depth > k) {
            int nid;
            if (trie_finish(&t, &stack[depth], &nid) < 0) goto done;
            TrieNode *parent = &stack[depth - 1];
            parent->arcs[parent->n - 1].child = nid;
            parent->arcs[parent->n - 1].child_final = stack[depth].final;
            stack[depth].n = 0;
            stack[depth].final = 0;
            depth--;
        }
        for (Py_ssize_t j = k; j < len; j++) {
            if (tnode_add_arc(&stack[depth], (unsigned char)seq[j]) < 0) goto done;
            if (depth + 1 >= stack_cap) {
                Py_ssize_t cap = stack_cap * 2;
                TrieNode *ns = PyMem_Realloc(stack, cap * sizeof(TrieNode));
                if (ns == NULL) { PyErr_NoMemory(); goto done; }
                memset(ns + stack_cap, 0, (cap - stack_cap) * sizeof(TrieNode));
                stack = ns;
                stack_cap = cap;
            }
            depth++;
            stack[depth].n = 0;
            stack[depth].final = 0;
        }
        stack[depth].final = 1;
        prev = seq;
        prev_len = len;
    }
    while (depth > 0) {
        int nid;
        if (trie_finish(&t, &stack[depth], &nid) < 0) goto done;
        TrieNode *parent = &stack[depth - 1];
        parent->arcs[parent->n - 1].child = nid;
        parent->arcs[parent->n - 1].child_final = stack[depth].final;
        stack[depth].n = 0;
        depth--;
    }
    int root;
    if (trie_finish(&t, &stack[0], &root) < 0) goto done;
    result = Py_BuildValue("(iy#y#y#y#y#y#)", root, t.first.data, t.first.n * t.first.itemsize,
                           t.ends.data, t.ends.n * t.ends.itemsize, t.labels.data, t.labels.n,
                           t.dests.data, t.dests.n * t.dests.itemsize, t.finals.data, t.finals.n,
                           t.lasts.data, t.lasts.n);
done:
    if (stack != NULL) {
        for (Py_ssize_t i = 0; i < stack_cap; i++) PyMem_Free(stack[i].arcs);
        PyMem_Free(stack);
    }
    PyMem_Free(t.first.data); PyMem_Free(t.ends.data); PyMem_Free(t.labels.data);
    PyMem_Free(t.dests.data); PyMem_Free(t.finals.data); PyMem_Free(t.lasts.data);
    Py_DECREF(seqs);
    return result;
}

static PyMethodDef module_methods[] = {
    {"rule_blob_names", py_rule_blob_names, METH_NOARGS, NULL},
    {"rule_blob", py_rule_blob, METH_VARARGS, NULL},
    {"rule_blob_build_id", py_rule_blob_build_id, METH_O, NULL},
    {"map_rule_table", py_map_rule_table, METH_VARARGS, NULL},
    {"levenshtein", py_levenshtein, METH_VARARGS, NULL},
    {"build_trie", py_build_trie, METH_O, NULL},
    {"beam_search", py_beam_search, METH_VARARGS, NULL},
    {"set_fallbacks", py_set_fallbacks, METH_VARARGS, NULL},
    {"sentence_index", py_sentence_index, METH_VARARGS, NULL},
    {"gis_sum", py_gis_sum, METH_VARARGS, NULL},
    {"gis_eval", py_gis_eval, METH_VARARGS, NULL},
    {"pattern_token_is_matched", py_pt_is_matched, METH_VARARGS, NULL},
    {"string_matcher_matches", py_sm_matches, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

int lt_hunspell_init(PyObject *m);  /* _hunspell.c */

static int
exec_module(PyObject *m)
{
    if (lt_hunspell_init(m) < 0) return -1;
#define ADD_TYPE(t, name) do { if (PyType_Ready(&t) < 0) return -1; Py_INCREF(&t); if (PyModule_AddObject(m, name, (PyObject *)&t) < 0) return -1; } while (0)
    ADD_TYPE(AnalyzedTokenBaseType, "AnalyzedTokenBase");
    ADD_TYPE(ATRBaseType, "AnalyzedTokenReadingsBase");
    ADD_TYPE(StringMatcherBaseType, "StringMatcherBase");
    ADD_TYPE(PosTokenBaseType, "PosTokenBase");
    ADD_TYPE(PatternTokenBaseType, "PatternTokenBase");
    ADD_TYPE(CompiledPatternType, "CompiledPattern");
    ADD_TYPE(FSADictType, "FSADict");
    ADD_TYPE(RuleHintsType, "RuleHints");
    ADD_TYPE(RuleSelectorType, "RuleSelector");
    ADD_TYPE(MatcherTableType, "MatcherTable");
    ADD_TYPE(SpellerSearchType, "SpellerSearch");
    ADD_TYPE(RuleBlobType, "RuleBlob");
#undef ADD_TYPE
    str_lower = PyUnicode_InternFromString("lower");
    str_regex_match = PyUnicode_InternFromString("_regex_match");
    str_chunk_tag = PyUnicode_InternFromString("chunk_tag");
    str_matches = PyUnicode_InternFromString("matches");
    str_is_regexp = PyUnicode_InternFromString("is_regexp");
    str_fullmatch = PyUnicode_InternFromString("fullmatch");
    str_token = PyUnicode_InternFromString("token");
    str_strip = PyUnicode_InternFromString("strip");
    str_sent_start = PyUnicode_InternFromString("SENT_START");
    str_sent_end = PyUnicode_InternFromString("SENT_END");
    str_para_end = PyUnicode_InternFromString("PARA_END");
    str_empty = PyUnicode_InternFromString("");
    empty_tuple = PyTuple_New(0);
    int_zero = PyLong_FromLong(0);
    if (!str_strip || !str_sent_start || !str_sent_end || !str_para_end || !str_empty || !empty_tuple || !int_zero)
        return -1;
    if (str_token == NULL) return -1;
    if (!str_lower || !str_regex_match || !str_chunk_tag || !str_matches || !str_is_regexp || !str_fullmatch)
        return -1;
    str_non_blank_tokens = PyUnicode_InternFromString("non_blank_tokens");
    str_token_offsets = PyUnicode_InternFromString("token_offsets");
    str_lemma_offsets = PyUnicode_InternFromString("lemma_offsets");
    str_pos_tag_set = PyUnicode_InternFromString("pos_tag_set");
    if (!str_non_blank_tokens || !str_token_offsets || !str_lemma_offsets || !str_pos_tag_set) return -1;
    str_non_blank_pre_disambig_tokens = PyUnicode_InternFromString("non_blank_pre_disambig_tokens");
    str_check_cancelled_callback = PyUnicode_InternFromString("check_cancelled_callback");
    str_text = PyUnicode_InternFromString("text");
    if (!str_non_blank_pre_disambig_tokens || !str_check_cancelled_callback || !str_text) return -1;
    str_get_original_position = PyUnicode_InternFromString("get_original_position");
    str_immunize = PyUnicode_InternFromString("immunize");
    str_tokens = PyUnicode_InternFromString("tokens");
    if (!str_get_original_position || !str_immunize || !str_tokens) return -1;
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
