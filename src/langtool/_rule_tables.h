/*
 * _rule_tables.h (included by _speedups.c)
 *
 * The static rule tables: the rules of the built-in languages compiled at
 * build time into read-only files installed with the package
 * (langtool/_rule_tables/<code>.ltrt, see tools/gen_rule_tables.py and
 * langtool/patterns/static_format.py for the format), memory-mapped lazily
 * per language and used in place. This part has
 *  - RuleBlob: a table (a mapped file, or a buffer for the tests), its
 *    sections, and the creation of the Python objects of the rules from the
 *    object records (lazily, when they are needed)
 *  - the matching engine working on the tables in place (RuleSelector
 *    segments of static rules, see the second part)
 */

#include <stdint.h>

/* ------------------------------------------------------------------------ */
/* the format (see static_format.py) */

#define RT_MAGIC "LTRULES\0"
#define RT_FORMAT_VERSION 4  /* (not RT_VERSION: a macro of windows.h) */
#define RT_NONE 0xFFFFFFFFu

enum {
    RT_SEC_META = 1, RT_SEC_STRTAB, RT_SEC_STRDATA, RT_SEC_OBJIDX, RT_SEC_OBJDATA, RT_SEC_SM, RT_SEC_HSET,
    RT_SEC_POS, RT_SEC_CHUNK, RT_SEC_PT, RT_SEC_IDX, RT_SEC_RULE, RT_SEC_HINT, RT_SEC_CAT, RT_SEC_UNIT, RT_SEC_IENT,
    RT_SEC_REGEX, RT_SEC_COUNT
};

typedef struct { char magic[8]; uint32_t version, header_size, total_size, n_sections; uint8_t build_id[16]; } rt_header;
typedef struct { uint32_t id, offset, size, count; } rt_section;
typedef struct { uint32_t off, ncp; } rt_str;
typedef struct { uint32_t hash, str; } rt_hent;
typedef struct {
    uint8_t kind, cs, is_regexp, pad;
    uint32_t value, value_lower, set_off, set_n, obj, pattern, regex_flags;
} rt_sm;
typedef struct { uint32_t tag, sm; uint8_t negation, unknown; uint16_t pad; } rt_pos;
typedef struct { uint32_t str, obj; uint8_t is_regexp, pad; uint16_t pad2; } rt_chunk;
typedef struct {
    uint32_t obj, flags;
    int32_t skip, max_occurrence;
    uint32_t sm, pos, chunk, exc_off;
    uint16_t n_cn, n_prev;
    uint32_t and_off;
    uint16_t n_and, pad;
} rt_pt;
typedef struct { uint8_t kind, pad; uint16_t pad2; uint32_t set_off, set_n; } rt_hint;
typedef struct {
    uint32_t obj, id, sub_id, cat, flags;
    int32_t moc;
    uint32_t pt_off;
    uint16_t n_pt, n_elno;
    uint32_t elno_off, hints_off;
    uint16_t n_hints, n_pos_hints;
    int16_t anchor_hint, min_token_count;
    int32_t anchor_index, max_span;
    uint32_t ap_off;
    uint16_t n_ap, n_tags;
    uint32_t tags_off;
    uint16_t n_tone_tags, kind;
    int32_t min_prev_matches, xml_line, spc, epc;
    uint32_t regex_pattern, regex_flags;
} rt_rule;
typedef struct { uint32_t id, default_on; } rt_cat;
typedef struct {
    uint32_t name, kind, rule_off, rule_n;
    uint32_t sel[2][6];   /* with / without lemma hints: token index (off, n), lemma index (off, n), unclassified */
} rt_unit;
typedef struct { uint32_t hash, str, list_off, list_n; } rt_ient;
typedef struct { uint32_t hash, pattern, flags, val_off; } rt_regex;

#define RT_STATIC_ASSERT(c, m) typedef char rt_static_assert_##m[(c) ? 1 : -1]
RT_STATIC_ASSERT(sizeof(rt_header) == 40, header);
RT_STATIC_ASSERT(sizeof(rt_section) == 16, section);
RT_STATIC_ASSERT(sizeof(rt_sm) == 32, sm);
RT_STATIC_ASSERT(sizeof(rt_pos) == 12, pos);
RT_STATIC_ASSERT(sizeof(rt_chunk) == 12, chunk);
RT_STATIC_ASSERT(sizeof(rt_pt) == 44, pt);
RT_STATIC_ASSERT(sizeof(rt_hint) == 12, hint);
RT_STATIC_ASSERT(sizeof(rt_rule) == 96, rule);
RT_STATIC_ASSERT(sizeof(rt_unit) == 64, unit);

/* PT flags */
#define PTF_INFLECTED (1u << 0)
#define PTF_NEGATION (1u << 1)
#define PTF_TEST_WHITESPACE (1u << 2)
#define PTF_WHITESPACE_BEFORE (1u << 3)
#define PTF_INSIDE_MARKER (1u << 4)
#define PTF_EXCEPTION_VALID_NEXT (1u << 5)
#define PTF_MAY_BE_OMITTED (1u << 6)
#define PTF_TEST_STRING (1u << 7)
#define PTF_UNIFICATION_NEUTRAL (1u << 8)
#define PTF_UNI_NEGATION (1u << 9)
#define PTF_LAST_IN_UNIFICATION (1u << 10)
#define PTF_UNIFIED (1u << 11)
#define PTF_REFERENCE (1u << 12)
#define PTF_AND_GROUP (1u << 13)

/* RULE flags */
#define RF_SENT_START (1u << 0)
#define RF_GROUPS_OR_UNIFICATION (1u << 1)
#define RF_TEST_UNIFICATION (1u << 2)
#define RF_REFERENCES (1u << 3)
#define RF_PRE_DISAMBIGUATION (1u << 4)
#define RF_USE_LIST (1u << 5)
#define RF_CHECK_POS (1u << 6)
#define RF_DEFAULT_OFF (1u << 7)
#define RF_DEFAULT_TEMP_OFF (1u << 8)
#define RF_GOAL_SPECIFIC (1u << 9)
#define RF_GET_UNIFIED (1u << 10)
#define RF_HINTS (1u << 11)
#define RF_ANTI_PATTERN (1u << 12)
#define RF_PICKY (1u << 13)
#define RF_PLAIN_IMMUNIZE (1u << 14)

enum { RULE_KIND_PATTERN = 0, RULE_KIND_REGEX = 1, RULE_KIND_DISAMBIGUATION = 2 };
enum { HINT_KIND_TOKEN = 0, HINT_KIND_LEMMA = 1, HINT_KIND_POS = 2 };

/* value tags */
enum {
    V_NONE, V_FALSE, V_TRUE, V_INT, V_FLOAT, V_STR, V_LIST, V_TUPLE, V_DICT, V_SET, V_FROZENSET, V_OBJ, V_BYTES,
    V_UNSET, V_GLOBAL, V_EXT, V_HSET
};

/* object kinds (the types given to RuleBlob.set_types) */
enum { OK_SLOTS = 0, OK_SPECIAL = 1, OK_CONTAINER = 2 };

/* ------------------------------------------------------------------------ */
/* the tables of this build (rule_tables.c, generated: the languages and the build ids of their table files; weak:
 * the extension also works without it) */

typedef struct { const char *name; const char *build_id; } langtool_rule_table;

#if defined(__GNUC__) || defined(__clang__)
extern const langtool_rule_table langtool_rule_tables[] __attribute__((weak));
extern const int langtool_rule_table_count __attribute__((weak));
#define RT_TABLE_COUNT() (&langtool_rule_table_count != NULL && langtool_rule_tables != NULL ? langtool_rule_table_count : 0)
#else
extern const langtool_rule_table langtool_rule_tables[];
extern const int langtool_rule_table_count;
#define RT_TABLE_COUNT() langtool_rule_table_count
#endif

/* the read-only mapping of a table file */
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

/* maps the file path (str) read-only: *base, *size; returns 0, or -1 with an OSError/ValueError set */
static int
rt_map_file(PyObject *path, void **base, size_t *size)
{
#ifdef _WIN32
    wchar_t *w = PyUnicode_AsWideCharString(path, NULL);
    if (w == NULL) return -1;
    void *p = NULL;
    LARGE_INTEGER sz;
    sz.QuadPart = 0;
    DWORD err = 0;
    Py_BEGIN_ALLOW_THREADS
    HANDLE f = CreateFileW(w, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, NULL, OPEN_EXISTING,
                           FILE_ATTRIBUTE_NORMAL, NULL);
    if (f == INVALID_HANDLE_VALUE) {
        err = GetLastError();
    } else {
        if (!GetFileSizeEx(f, &sz) || sz.QuadPart <= 0 || (unsigned long long)sz.QuadPart > (size_t)-1) {
            err = GetLastError() ? GetLastError() : ERROR_BAD_LENGTH;
        } else {
            HANDLE m = CreateFileMappingW(f, NULL, PAGE_READONLY, 0, 0, NULL);
            if (m == NULL) {
                err = GetLastError();
            } else {
                p = MapViewOfFile(m, FILE_MAP_READ, 0, 0, 0);
                if (p == NULL) err = GetLastError();
                CloseHandle(m);  /* (the view keeps the mapping) */
            }
        }
        CloseHandle(f);
    }
    Py_END_ALLOW_THREADS
    PyMem_Free(w);
    if (p == NULL) {
        PyErr_SetExcFromWindowsErrWithFilenameObject(PyExc_OSError, (int)err, path);
        return -1;
    }
    *base = p;
    *size = (size_t)sz.QuadPart;
    return 0;
#else
    PyObject *bpath = NULL;
    if (!PyUnicode_FSConverter(path, &bpath)) return -1;
    void *p = MAP_FAILED;
    off_t sz = 0;
    int err = 0;
    const char *cpath = PyBytes_AS_STRING(bpath);
    Py_BEGIN_ALLOW_THREADS
    int fd = open(cpath, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        err = errno;
    } else {
        struct stat st;
        if (fstat(fd, &st) < 0) {
            err = errno;
        } else if (st.st_size <= 0 || (unsigned long long)st.st_size > (size_t)-1) {
            err = EINVAL;
        } else {
            sz = st.st_size;
            p = mmap(NULL, (size_t)sz, PROT_READ, MAP_PRIVATE, fd, 0);
            if (p == MAP_FAILED) err = errno;
        }
        close(fd);
    }
    Py_END_ALLOW_THREADS
    if (p == MAP_FAILED) {
        errno = err;
        PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, path);
        Py_DECREF(bpath);
        return -1;
    }
    Py_DECREF(bpath);
    *base = p;
    *size = (size_t)sz;
    return 0;
#endif
}

static void
rt_unmap(void *base, size_t size)
{
#ifdef _WIN32
    (void)size;
    UnmapViewOfFile(base);
#else
    munmap(base, size);
#endif
}

/* ------------------------------------------------------------------------ */
/* RuleBlob */

typedef struct {
    PyObject_HEAD
    PyObject *name;
    Py_buffer view;            /* when created from a buffer (view.obj != NULL) */
    void *map_base;            /* when created from a mapped file (unmapped when the RuleBlob is deallocated: the
                                * selectors and tables that use it keep a reference) */
    size_t map_size;
    const uint8_t *base;
    size_t size;
    const char *meta;
    uint32_t meta_size;
    const rt_str *strtab; uint32_t n_str;
    const char *strdata; uint32_t strdata_size;
    const uint32_t *objidx; uint32_t n_obj;
    const uint8_t *objdata; uint32_t objdata_size;
    const rt_sm *sm; uint32_t n_sm;
    const rt_hent *hset; uint32_t n_hset;
    const rt_pos *pos; uint32_t n_pos;
    const rt_chunk *chunk; uint32_t n_chunk;
    const rt_pt *pt; uint32_t n_pt;
    const uint32_t *idx; uint32_t n_idx;
    const rt_rule *rule; uint32_t n_rule;
    const rt_hint *hint; uint32_t n_hint;
    const rt_cat *cat; uint32_t n_cat;
    const rt_unit *unit; uint32_t n_unit;
    const rt_ient *ient; uint32_t n_ient;
    const rt_regex *regex; uint32_t n_regex;
    PyObject **strings;        /* str objects of the pool, created when needed */
    PyObject *types;           /* tuple of (kind, class or kind name, attribute names tuple, post) */
    PyObject *engine_hook;     /* callable(kind, index) -> object: the objects the engine needs (matchers, chunk tags) */
    PyObject **sm_objs;        /* the StringMatcher objects of the SM entries (regular expressions), when needed */
    PyObject **chunk_objs;     /* the ChunkTag objects of the CHUNK entries (regular expressions), when needed */
} RuleBlob;

static PyTypeObject RuleBlobType;

static int
rb_traverse(RuleBlob *self, visitproc visit, void *arg)
{
    Py_VISIT(self->name);
    Py_VISIT(self->types);
    Py_VISIT(self->engine_hook);
    if (self->view.obj != NULL) Py_VISIT(self->view.obj);
    if (self->strings != NULL) {
        for (uint32_t i = 0; i < self->n_str; i++) Py_VISIT(self->strings[i]);
    }
    if (self->sm_objs != NULL) {
        for (uint32_t i = 0; i < self->n_sm; i++) Py_VISIT(self->sm_objs[i]);
    }
    if (self->chunk_objs != NULL) {
        for (uint32_t i = 0; i < self->n_chunk; i++) Py_VISIT(self->chunk_objs[i]);
    }
    return 0;
}

static int
rb_clear(RuleBlob *self)
{
    Py_CLEAR(self->types);
    Py_CLEAR(self->engine_hook);
    if (self->strings != NULL) {
        for (uint32_t i = 0; i < self->n_str; i++) Py_CLEAR(self->strings[i]);
    }
    if (self->sm_objs != NULL) {
        for (uint32_t i = 0; i < self->n_sm; i++) Py_CLEAR(self->sm_objs[i]);
    }
    if (self->chunk_objs != NULL) {
        for (uint32_t i = 0; i < self->n_chunk; i++) Py_CLEAR(self->chunk_objs[i]);
    }
    return 0;
}

static void
rb_dealloc(RuleBlob *self)
{
    PyObject_GC_UnTrack(self);
    rb_clear(self);
    PyMem_Free(self->strings);
    PyMem_Free(self->sm_objs);
    PyMem_Free(self->chunk_objs);
    Py_CLEAR(self->name);
    if (self->view.obj != NULL) PyBuffer_Release(&self->view);
    if (self->map_base != NULL) rt_unmap(self->map_base, self->map_size);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

/* the section table: pointer and count of a section, checking that its size fits the entry size */
static int
rb_section(RuleBlob *self, const rt_section *secs, uint32_t nsec, uint32_t id, size_t entry_size, const void **ptr,
           uint32_t *count, uint32_t *size_out)
{
    for (uint32_t i = 0; i < nsec; i++) {
        if (secs[i].id != id) continue;
        if ((size_t)secs[i].offset + secs[i].size > self->size || (secs[i].offset & 7) != 0) break;
        if (entry_size > 0 && (size_t)secs[i].count * entry_size != secs[i].size) break;
        *ptr = self->base + secs[i].offset;
        *count = secs[i].count;
        if (size_out != NULL) *size_out = secs[i].size;
        return 0;
    }
    PyErr_Format(PyExc_ValueError, "rule tables: section %u missing or damaged", (unsigned)id);
    return -1;
}

/* parses the header and the sections (the sizes; the references between the tables are checked by validate()) */
static int
rb_parse(RuleBlob *self)
{
    if (self->size < sizeof(rt_header) || ((uintptr_t)self->base & 7) != 0) {
        PyErr_SetString(PyExc_ValueError, "rule tables: too short or misaligned");
        return -1;
    }
    rt_header h;
    memcpy(&h, self->base, sizeof h);
    if (memcmp(h.magic, RT_MAGIC, 8) != 0 || h.version != RT_FORMAT_VERSION) {
        PyErr_SetString(PyExc_ValueError, "rule tables: other format or version");
        return -1;
    }
    if (h.total_size != self->size || h.n_sections > 64 ||
            sizeof(rt_header) + (size_t)h.n_sections * sizeof(rt_section) > self->size) {
        PyErr_SetString(PyExc_ValueError, "rule tables: bad header");
        return -1;
    }
    const rt_section *secs = (const rt_section *)(self->base + sizeof(rt_header));
    uint32_t n = h.n_sections, dummy;
    const void *p;
#define SEC(id, esize, field, count) \
    do { if (rb_section(self, secs, n, id, esize, &p, &self->count, NULL) < 0) return -1; self->field = p; } while (0)
    if (rb_section(self, secs, n, RT_SEC_META, 0, &p, &dummy, &self->meta_size) < 0) return -1;
    self->meta = p;
    SEC(RT_SEC_STRTAB, sizeof(rt_str), strtab, n_str);
    if (rb_section(self, secs, n, RT_SEC_STRDATA, 0, &p, &dummy, &self->strdata_size) < 0) return -1;
    self->strdata = p;
    SEC(RT_SEC_OBJIDX, 4, objidx, n_obj);
    if (rb_section(self, secs, n, RT_SEC_OBJDATA, 0, &p, &dummy, &self->objdata_size) < 0) return -1;
    self->objdata = p;
    SEC(RT_SEC_SM, sizeof(rt_sm), sm, n_sm);
    SEC(RT_SEC_HSET, sizeof(rt_hent), hset, n_hset);
    SEC(RT_SEC_POS, sizeof(rt_pos), pos, n_pos);
    SEC(RT_SEC_CHUNK, sizeof(rt_chunk), chunk, n_chunk);
    SEC(RT_SEC_PT, sizeof(rt_pt), pt, n_pt);
    SEC(RT_SEC_IDX, 4, idx, n_idx);
    SEC(RT_SEC_RULE, sizeof(rt_rule), rule, n_rule);
    SEC(RT_SEC_HINT, sizeof(rt_hint), hint, n_hint);
    SEC(RT_SEC_CAT, sizeof(rt_cat), cat, n_cat);
    SEC(RT_SEC_UNIT, sizeof(rt_unit), unit, n_unit);
    SEC(RT_SEC_IENT, sizeof(rt_ient), ient, n_ient);
    SEC(RT_SEC_REGEX, sizeof(rt_regex), regex, n_regex);
#undef SEC
    /* the string table must point into the string data, in order (checked here: the strings are used everywhere) */
    for (uint32_t i = 0; i < self->n_str; i++) {
        const rt_str *s = &self->strtab[i];
        uint32_t stop = i + 1 < self->n_str ? self->strtab[i + 1].off : self->strdata_size;
        if (s->off >= stop || stop > self->strdata_size || self->strdata[stop - 1] != 0 || s->ncp > stop - 1 - s->off) {
            PyErr_SetString(PyExc_ValueError, "rule tables: bad string table");
            return -1;
        }
    }
    return 0;
}

static RuleBlob *
rb_alloc(void)
{
    RuleBlob *self = PyObject_GC_New(RuleBlob, &RuleBlobType);
    if (self == NULL) return NULL;
    char *start = (char *)self + offsetof(RuleBlob, name);
    memset(start, 0, sizeof(RuleBlob) - offsetof(RuleBlob, name));
    PyObject_GC_Track(self);
    return self;
}

/* RuleBlob(buffer, name): a table from a buffer (the tests; the table files: rule_blob(name, path)) */
static PyObject *
rb_new(PyTypeObject *Py_UNUSED(type), PyObject *args, PyObject *kwds)
{
    PyObject *buf, *name;
    static char *kwlist[] = {"buffer", "name", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OU", kwlist, &buf, &name)) return NULL;
    RuleBlob *self = rb_alloc();
    if (self == NULL) return NULL;
    if (PyObject_GetBuffer(buf, &self->view, PyBUF_SIMPLE) < 0) {
        Py_DECREF(self);
        return NULL;
    }
    self->base = self->view.buf;
    self->size = (size_t)self->view.len;
    Py_INCREF(name);
    self->name = name;
    if (rb_parse(self) < 0) {
        Py_DECREF(self);
        return NULL;
    }
    return (PyObject *)self;
}

/* the length in bytes of the string i (UTF-8, without the NUL) */
static inline uint32_t
rt_str_nbytes(const RuleBlob *b, uint32_t i)
{
    uint32_t stop = i + 1 < b->n_str ? b->strtab[i + 1].off : b->strdata_size;
    return stop - 1 - b->strtab[i].off;
}

/* the str of the string i (borrowed, cached), NULL on error */
static PyObject *
rb_string(RuleBlob *self, uint32_t i)
{
    if (i >= self->n_str) {
        PyErr_SetString(PyExc_ValueError, "rule tables: string index out of range");
        return NULL;
    }
    if (self->strings == NULL) {
        self->strings = PyMem_Calloc(self->n_str + 1, sizeof(PyObject *));
        if (self->strings == NULL) { PyErr_NoMemory(); return NULL; }
    }
    PyObject *s = self->strings[i];
    if (s == NULL) {
        const rt_str *e = &self->strtab[i];
        s = PyUnicode_DecodeUTF8(self->strdata + e->off, rt_str_nbytes(self, i), "strict");
        if (s == NULL) return NULL;
        if (self->strings[i] != NULL) {  /* (set meanwhile: the allocation can run other threads) */
            Py_DECREF(s);
            s = self->strings[i];
        } else {
            self->strings[i] = s;
        }
    }
    return s;
}

static PyObject *
rb_py_string(RuleBlob *self, PyObject *arg)
{
    long i = PyLong_AsLong(arg);
    if (i == -1 && PyErr_Occurred()) return NULL;
    if (i < 0 || (unsigned long)i >= self->n_str) {
        PyErr_SetString(PyExc_IndexError, "string index out of range");
        return NULL;
    }
    PyObject *s = rb_string(self, (uint32_t)i);
    Py_XINCREF(s);
    return s;
}

static PyObject *
rb_py_meta(RuleBlob *self, PyObject *Py_UNUSED(ignored))
{
    return PyBytes_FromStringAndSize(self->meta, self->meta_size);
}

/* set_types(types, engine_hook): the type descriptors of the object records (a tuple of (kind, class or kind name,
 * attribute names, post) per type index) and the callable creating the objects the engine needs */
static PyObject *
rb_set_types(RuleBlob *self, PyObject *args)
{
    PyObject *types, *hook;
    if (!PyArg_ParseTuple(args, "O!O", &PyTuple_Type, &types, &hook)) return NULL;
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(types); i++) {
        PyObject *t = PyTuple_GET_ITEM(types, i);
        if (!PyTuple_Check(t) || PyTuple_GET_SIZE(t) != 4 || !PyLong_Check(PyTuple_GET_ITEM(t, 0)) ||
                !PyTuple_Check(PyTuple_GET_ITEM(t, 2))) {
            PyErr_SetString(PyExc_TypeError, "bad type descriptor");
            return NULL;
        }
        long kind = PyLong_AsLong(PyTuple_GET_ITEM(t, 0));
        if (kind == OK_SLOTS && !PyType_Check(PyTuple_GET_ITEM(t, 1))) {
            PyErr_SetString(PyExc_TypeError, "a slots type descriptor needs a class");
            return NULL;
        }
        PyObject *attrs = PyTuple_GET_ITEM(t, 2);
        for (Py_ssize_t j = 0; j < PyTuple_GET_SIZE(attrs); j++) {
            if (!PyUnicode_Check(PyTuple_GET_ITEM(attrs, j))) {
                PyErr_SetString(PyExc_TypeError, "attribute names must be strings");
                return NULL;
            }
        }
    }
    Py_INCREF(types);
    Py_XSETREF(self->types, types);
    Py_INCREF(hook);
    Py_XSETREF(self->engine_hook, hook);
    Py_RETURN_NONE;
}

/* --- the decoder of the object records --- */

typedef struct {
    RuleBlob *blob;
    PyObject *memo;      /* dict: object index -> object (per language) */
    PyObject *special;   /* callable(kind name, state) -> object */
    PyObject *ext;       /* callable(code) -> object */
    PyObject *glob;      /* callable(module, qualname) -> object */
    PyObject *post;      /* callable(object), for the types with post set */
    int depth;
} DecodeCtx;

static PyObject *rb_materialize_obj(DecodeCtx *ctx, uint32_t idx);

static int
rd_varint(const uint8_t **p, const uint8_t *end, uint64_t *out)
{
    uint64_t v = 0;
    int shift = 0;
    while (*p < end) {
        uint8_t b = *(*p)++;
        if (shift > 63) break;
        v |= (uint64_t)(b & 0x7F) << shift;
        if (!(b & 0x80)) { *out = v; return 0; }
        shift += 7;
    }
    PyErr_SetString(PyExc_ValueError, "rule tables: bad varint");
    return -1;
}

static int
rd_u32(const uint8_t **p, const uint8_t *end, uint32_t *out)
{
    uint64_t v;
    if (rd_varint(p, end, &v) < 0) return -1;
    if (v > 0xFFFFFFFFu) {
        PyErr_SetString(PyExc_ValueError, "rule tables: value out of range");
        return -1;
    }
    *out = (uint32_t)v;
    return 0;
}

#define RT_MAX_DEPTH 200

/* decodes a value; *unset is set for V_UNSET (and NULL returned without an exception) */
static PyObject *
rd_value(DecodeCtx *ctx, const uint8_t **p, const uint8_t *end, int *unset)
{
    if (*p >= end) {
        PyErr_SetString(PyExc_ValueError, "rule tables: truncated record");
        return NULL;
    }
    if (++ctx->depth > RT_MAX_DEPTH) {
        ctx->depth--;
        PyErr_SetString(PyExc_ValueError, "rule tables: records nested too deeply");
        return NULL;
    }
    uint8_t tag = *(*p)++;
    PyObject *r = NULL;
    uint64_t v;
    uint32_t n, k;
    switch (tag) {
    case V_NONE: r = Py_None; Py_INCREF(r); break;
    case V_FALSE: r = Py_False; Py_INCREF(r); break;
    case V_TRUE: r = Py_True; Py_INCREF(r); break;
    case V_INT:
        if (rd_varint(p, end, &v) < 0) break;
        if (v & 1) {
            /* -(v >> 1) - 1 */
            r = PyLong_FromLongLong(-(long long)(v >> 1) - 1);
        } else {
            r = PyLong_FromUnsignedLongLong(v >> 1);
        }
        break;
    case V_FLOAT: {
        if (end - *p < 8) { PyErr_SetString(PyExc_ValueError, "rule tables: truncated float"); break; }
        double d;
        memcpy(&d, *p, 8);
        *p += 8;
        r = PyFloat_FromDouble(d);
        break;
    }
    case V_STR:
        if (rd_u32(p, end, &k) < 0) break;
        r = rb_string(ctx->blob, k);
        Py_XINCREF(r);
        break;
    case V_BYTES:
        if (rd_u32(p, end, &n) < 0) break;
        if ((uint64_t)(end - *p) < n) { PyErr_SetString(PyExc_ValueError, "rule tables: truncated bytes"); break; }
        r = PyBytes_FromStringAndSize((const char *)*p, n);
        *p += n;
        break;
    case V_LIST: case V_TUPLE: case V_SET: case V_FROZENSET: {
        if (rd_u32(p, end, &n) < 0) break;
        if (n > (uint32_t)(end - *p)) { PyErr_SetString(PyExc_ValueError, "rule tables: bad length"); break; }
        PyObject *items = PyList_New(n);
        if (items == NULL) break;
        int ok = 1;
        for (uint32_t i = 0; i < n; i++) {
            int u = 0;
            PyObject *x = rd_value(ctx, p, end, &u);
            if (x == NULL) {
                if (u) PyErr_SetString(PyExc_ValueError, "rule tables: unset value in a container");
                ok = 0;
                break;
            }
            PyList_SET_ITEM(items, i, x);
        }
        if (!ok) { Py_DECREF(items); break; }
        if (tag == V_LIST) r = items;
        else {
            if (tag == V_TUPLE) r = PyList_AsTuple(items);
            else if (tag == V_SET) r = PySet_New(items);
            else r = PyFrozenSet_New(items);
            Py_DECREF(items);
        }
        break;
    }
    case V_DICT: {
        if (rd_u32(p, end, &n) < 0) break;
        if (n > (uint32_t)(end - *p)) { PyErr_SetString(PyExc_ValueError, "rule tables: bad length"); break; }
        PyObject *d = PyDict_New();
        if (d == NULL) break;
        int ok = 1;
        for (uint32_t i = 0; i < n && ok; i++) {
            int u = 0;
            PyObject *key = rd_value(ctx, p, end, &u);
            if (key == NULL) { ok = 0; break; }
            PyObject *val = rd_value(ctx, p, end, &u);
            if (val == NULL) { Py_DECREF(key); ok = 0; break; }
            if (PyDict_SetItem(d, key, val) < 0) ok = 0;
            Py_DECREF(key);
            Py_DECREF(val);
        }
        if (!ok) {
            if (!PyErr_Occurred()) PyErr_SetString(PyExc_ValueError, "rule tables: unset value in a dict");
            Py_DECREF(d);
            break;
        }
        r = d;
        break;
    }
    case V_OBJ:
        if (rd_u32(p, end, &k) < 0) break;
        r = rb_materialize_obj(ctx, k);
        break;
    case V_UNSET:
        *unset = 1;
        break;
    case V_HSET: {
        uint32_t off;
        if (rd_u32(p, end, &off) < 0 || rd_u32(p, end, &n) < 0) break;
        if (*p >= end || (uint64_t)off + n > ctx->blob->n_hset) {
            PyErr_SetString(PyExc_ValueError, "rule tables: bad hash set reference");
            break;
        }
        int as_tuple = *(*p)++;
        PyObject *items = PyTuple_New(n);
        if (items == NULL) break;
        int ok = 1;
        for (uint32_t i = 0; i < n; i++) {
            PyObject *x = rb_string(ctx->blob, ctx->blob->hset[off + i].str);
            if (x == NULL) { ok = 0; break; }
            Py_INCREF(x);
            PyTuple_SET_ITEM(items, i, x);
        }
        if (!ok) { Py_DECREF(items); break; }
        if (as_tuple) r = items;
        else {
            r = PyFrozenSet_New(items);
            Py_DECREF(items);
        }
        break;
    }
    case V_GLOBAL: {
        uint32_t m, q;
        if (rd_u32(p, end, &m) < 0 || rd_u32(p, end, &q) < 0) break;
        PyObject *ms = rb_string(ctx->blob, m);
        if (ms == NULL) break;
        PyObject *qs = rb_string(ctx->blob, q);
        if (qs == NULL) break;
        r = PyObject_CallFunctionObjArgs(ctx->glob, ms, qs, NULL);
        break;
    }
    case V_EXT: {
        if (rd_u32(p, end, &k) < 0) break;
        PyObject *code = PyLong_FromUnsignedLong(k);
        if (code == NULL) break;
        r = PyObject_CallOneArg(ctx->ext, code);
        Py_DECREF(code);
        break;
    }
    default:
        PyErr_Format(PyExc_ValueError, "rule tables: unknown value tag %d", (int)tag);
    }
    ctx->depth--;
    return r;
}

/* the start and end of the record of the object idx, -1 on error */
static int
rb_record(RuleBlob *self, uint32_t idx, const uint8_t **start, const uint8_t **end)
{
    if (idx >= self->n_obj) {
        PyErr_SetString(PyExc_ValueError, "rule tables: object index out of range");
        return -1;
    }
    uint32_t off = self->objidx[idx];
    uint32_t stop = idx + 1 < self->n_obj ? self->objidx[idx + 1] : self->objdata_size;
    if (off > stop || stop > self->objdata_size) {
        PyErr_SetString(PyExc_ValueError, "rule tables: bad object table");
        return -1;
    }
    *start = self->objdata + off;
    *end = self->objdata + stop;
    return 0;
}

/* fills the (empty) container c from the encoded value at *p (a list, dict or set) */
static int
rd_fill_container(DecodeCtx *ctx, PyObject *c, const uint8_t **p, const uint8_t *end)
{
    int u = 0;
    PyObject *v = rd_value(ctx, p, end, &u);
    if (v == NULL) {
        if (u) PyErr_SetString(PyExc_ValueError, "rule tables: unset container");
        return -1;
    }
    int r = 0;
    if (PyList_CheckExact(c) && PyList_CheckExact(v)) {
        r = PyList_SetSlice(c, 0, 0, v);
    } else if (PyDict_CheckExact(c) && PyDict_CheckExact(v)) {
        r = PyDict_Update(c, v);
    } else if (PySet_CheckExact(c) && PySet_CheckExact(v)) {
        PyObject *it = PyObject_GetIter(v);
        if (it == NULL) r = -1;
        else {
            PyObject *x;
            while ((x = PyIter_Next(it)) != NULL) {
                if (PySet_Add(c, x) < 0) r = -1;
                Py_DECREF(x);
                if (r < 0) break;
            }
            Py_DECREF(it);
            if (PyErr_Occurred()) r = -1;
        }
    } else {
        PyErr_SetString(PyExc_ValueError, "rule tables: container record of another type");
        r = -1;
    }
    Py_DECREF(v);
    return r;
}

static PyObject *
rb_materialize_obj(DecodeCtx *ctx, uint32_t idx)
{
    RuleBlob *self = ctx->blob;
    PyObject *key = PyLong_FromUnsignedLong(idx);
    if (key == NULL) return NULL;
    PyObject *o = PyDict_GetItemWithError(ctx->memo, key);
    if (o != NULL) {
        Py_DECREF(key);
        Py_INCREF(o);
        return o;
    }
    if (PyErr_Occurred()) { Py_DECREF(key); return NULL; }
    const uint8_t *p, *end;
    uint32_t t;
    if (rb_record(self, idx, &p, &end) < 0 || rd_u32(&p, end, &t) < 0) { Py_DECREF(key); return NULL; }
    if (self->types == NULL || t >= (uint32_t)PyTuple_GET_SIZE(self->types)) {
        Py_DECREF(key);
        PyErr_SetString(PyExc_ValueError, "rule tables: unknown type (set_types() not called?)");
        return NULL;
    }
    PyObject *desc = PyTuple_GET_ITEM(self->types, t);
    long kind = PyLong_AsLong(PyTuple_GET_ITEM(desc, 0));
    PyObject *result = NULL;
    if (kind == OK_SLOTS) {
        PyTypeObject *cls = (PyTypeObject *)PyTuple_GET_ITEM(desc, 1);
        PyObject *attrs = PyTuple_GET_ITEM(desc, 2);
        o = cls->tp_new(cls, empty_tuple, NULL);
        if (o == NULL) goto done;
        if (PyDict_SetItem(ctx->memo, key, o) < 0) { Py_DECREF(o); goto done; }
        Py_ssize_t na = PyTuple_GET_SIZE(attrs);
        for (Py_ssize_t i = 0; i < na; i++) {
            int u = 0;
            PyObject *v = rd_value(ctx, &p, end, &u);
            if (v == NULL) {
                if (u) continue;
                goto fail_obj;
            }
            int r = PyObject_SetAttr(o, PyTuple_GET_ITEM(attrs, i), v);
            Py_DECREF(v);
            if (r < 0) goto fail_obj;
        }
        int u = 0;
        PyObject *d = rd_value(ctx, &p, end, &u);
        if (d == NULL) {
            if (u) PyErr_SetString(PyExc_ValueError, "rule tables: unset instance dict");
            goto fail_obj;
        }
        if (d != Py_None) {
            if (!PyDict_Check(d)) {
                Py_DECREF(d);
                PyErr_SetString(PyExc_ValueError, "rule tables: bad instance dict");
                goto fail_obj;
            }
            Py_ssize_t pos = 0;
            PyObject *k, *v;
            while (PyDict_Next(d, &pos, &k, &v)) {
                if (PyObject_SetAttr(o, k, v) < 0) { Py_DECREF(d); goto fail_obj; }
            }
        }
        Py_DECREF(d);
        if (PyObject_IsTrue(PyTuple_GET_ITEM(desc, 3)) && ctx->post != NULL && ctx->post != Py_None) {
            PyObject *r = PyObject_CallOneArg(ctx->post, o);
            if (r == NULL) goto fail_obj;
            Py_DECREF(r);
        }
        result = o;
        goto done;
fail_obj:
        {
            PyObject *et, *ev, *tb;
            PyErr_Fetch(&et, &ev, &tb);
            if (PyDict_DelItem(ctx->memo, key) < 0) PyErr_Clear();
            PyErr_Restore(et, ev, tb);
        }
        Py_DECREF(o);
        goto done;
    } else if (kind == OK_CONTAINER) {
        if (p >= end) { PyErr_SetString(PyExc_ValueError, "rule tables: truncated record"); goto done; }
        uint8_t tag = *p;
        if (tag == V_LIST) o = PyList_New(0);
        else if (tag == V_DICT) o = PyDict_New();
        else if (tag == V_SET) o = PySet_New(NULL);
        else { PyErr_SetString(PyExc_ValueError, "rule tables: bad container record"); goto done; }
        if (o == NULL) goto done;
        if (PyDict_SetItem(ctx->memo, key, o) < 0) { Py_DECREF(o); goto done; }
        if (rd_fill_container(ctx, o, &p, end) < 0) {
            PyObject *et, *ev, *tb;
            PyErr_Fetch(&et, &ev, &tb);
            if (PyDict_DelItem(ctx->memo, key) < 0) PyErr_Clear();
            PyErr_Restore(et, ev, tb);
            Py_DECREF(o);
            goto done;
        }
        result = o;
    } else {
        int u = 0;
        PyObject *state = rd_value(ctx, &p, end, &u);
        if (state == NULL) {
            if (u) PyErr_SetString(PyExc_ValueError, "rule tables: unset state");
            goto done;
        }
        o = PyObject_CallFunctionObjArgs(ctx->special, PyTuple_GET_ITEM(desc, 1), state, NULL);
        Py_DECREF(state);
        if (o == NULL) goto done;
        if (PyDict_SetItem(ctx->memo, key, o) < 0) { Py_DECREF(o); goto done; }
        result = o;
    }
done:
    Py_DECREF(key);
    return result;
}

/* materialize(index, memo, special, ext, glob, post): the object of the record index (memo: a dict index ->
 * object, the objects created already for the language) */
static PyObject *
rb_py_materialize(RuleBlob *self, PyObject *args)
{
    unsigned long idx;
    DecodeCtx ctx;
    ctx.blob = self;
    ctx.depth = 0;
    if (!PyArg_ParseTuple(args, "kO!OOOO", &idx, &PyDict_Type, &ctx.memo, &ctx.special, &ctx.ext, &ctx.glob,
                          &ctx.post))
        return NULL;
    if (idx > 0xFFFFFFFFul) {
        PyErr_SetString(PyExc_IndexError, "object index out of range");
        return NULL;
    }
    Py_INCREF(self);
    PyObject *r = rb_materialize_obj(&ctx, (uint32_t)idx);
    Py_DECREF(self);
    return r;
}

/* decode_value(offset, memo, special, ext, glob, post): the value encoded at offset of the object data (e.g. a
 * regular expression program) */
static PyObject *
rb_py_decode_value(RuleBlob *self, PyObject *args)
{
    unsigned long off;
    DecodeCtx ctx;
    ctx.blob = self;
    ctx.depth = 0;
    if (!PyArg_ParseTuple(args, "kO!OOOO", &off, &PyDict_Type, &ctx.memo, &ctx.special, &ctx.ext, &ctx.glob,
                          &ctx.post))
        return NULL;
    if (off >= self->objdata_size) {
        PyErr_SetString(PyExc_IndexError, "offset out of range");
        return NULL;
    }
    const uint8_t *p = self->objdata + off;
    int u = 0;
    PyObject *r = rd_value(&ctx, &p, self->objdata + self->objdata_size, &u);
    if (r == NULL && u) PyErr_SetString(PyExc_ValueError, "unset value");
    return r;
}

/* --- string helpers for the engine --- */

/* the FNV-1a hash of the code points of a str */
static uint32_t
rt_hash_unicode(PyObject *s)
{
    uint32_t h = 2166136261u;
    Py_ssize_t n = PyUnicode_GET_LENGTH(s);
    int kind = PyUnicode_KIND(s);
    const void *data = PyUnicode_DATA(s);
    for (Py_ssize_t i = 0; i < n; i++) {
        h = (h ^ (uint32_t)PyUnicode_READ(kind, data, i)) * 16777619u;
    }
    return h;
}

/* decodes the next code point of valid UTF-8 (the tables are generated from str) */
static inline uint32_t
rt_utf8_next(const unsigned char **pp)
{
    const unsigned char *p = *pp;
    uint32_t c = p[0];
    if (c < 0x80) { *pp = p + 1; return c; }
    if (c < 0xE0) { *pp = p + 2; return ((c & 0x1F) << 6) | (p[1] & 0x3F); }
    if (c < 0xF0) { *pp = p + 3; return ((c & 0x0F) << 12) | ((uint32_t)(p[1] & 0x3F) << 6) | (p[2] & 0x3F); }
    *pp = p + 4;
    return ((c & 0x07) << 18) | ((uint32_t)(p[1] & 0x3F) << 12) | ((uint32_t)(p[2] & 0x3F) << 6) | (p[3] & 0x3F);
}

/* whether the pool string i equals the str s */
static int
rt_str_eq(const RuleBlob *b, uint32_t i, PyObject *s)
{
    const rt_str *e = &b->strtab[i];
    Py_ssize_t n = PyUnicode_GET_LENGTH(s);
    if ((Py_ssize_t)e->ncp != n) return 0;
    int kind = PyUnicode_KIND(s);
    const void *data = PyUnicode_DATA(s);
    const unsigned char *p = (const unsigned char *)b->strdata + e->off;
    if (kind == PyUnicode_1BYTE_KIND && e->ncp == rt_str_nbytes(b, i)) {
        /* ASCII in the pool: compare the bytes (latin-1 data equal to ASCII bytes iff all are ASCII) */
        return memcmp(p, data, n) == 0;
    }
    for (Py_ssize_t k = 0; k < n; k++) {
        if (rt_utf8_next(&p) != (uint32_t)PyUnicode_READ(kind, data, k)) return 0;
    }
    return 1;
}

/* whether the sorted hash set (off, n) contains the str s (with the hash h) */
static int
rt_hset_contains(const RuleBlob *b, uint32_t off, uint32_t n, uint32_t h, PyObject *s)
{
    const rt_hent *e = b->hset + off;
    uint32_t lo = 0, hi = n;
    while (lo < hi) {
        uint32_t mid = lo + (hi - lo) / 2;
        if (e[mid].hash < h) lo = mid + 1;
        else hi = mid;
    }
    for (; lo < n && e[lo].hash == h; lo++) {
        if (rt_str_eq(b, e[lo].str, s)) return 1;
    }
    return 0;
}

/* the hash of the string i of the pool (the hash sets have the hashes) */
static uint32_t
rt_str_hash(const RuleBlob *b, uint32_t i)
{
    const unsigned char *p = (const unsigned char *)b->strdata + b->strtab[i].off;
    uint32_t h = 2166136261u;
    for (uint32_t k = 0; k < b->strtab[i].ncp; k++) h = (h ^ rt_utf8_next(&p)) * 16777619u;
    return h;
}

static PyObject *
rb_py_info(RuleBlob *self, PyObject *Py_UNUSED(ignored))
{
    return Py_BuildValue("{s:n,s:I,s:I,s:I,s:I,s:I,s:I,s:I,s:I}", "size", (Py_ssize_t)self->size, "strings",
                         self->n_str, "objects", self->n_obj, "matchers", self->n_sm, "pattern_tokens", self->n_pt,
                         "rules", self->n_rule, "units", self->n_unit, "regexes", self->n_regex, "hints",
                         self->n_hint);
}

/* validate(): checks all the references between the tables (the tests; the table files are generated with the
 * extension and not checked when used) */
static PyObject *
rb_py_validate(RuleBlob *self, PyObject *Py_UNUSED(ignored))
{
    const char *what = NULL;
#define CHECK(c, w) do { if (!(c)) { what = (w); goto bad; } } while (0)
#define STR_OK(i) ((i) < self->n_str)
#define STR_OR_NONE(i) ((i) == RT_NONE || (i) < self->n_str)
#define RANGE(off, n, total) ((uint64_t)(off) + (n) <= (total))
    for (uint32_t i = 0; i < self->n_obj; i++) {
        CHECK(self->objidx[i] <= self->objdata_size && (i == 0 || self->objidx[i] >= self->objidx[i - 1]), "objidx");
    }
    for (uint32_t i = 0; i < self->n_hset; i++) {
        CHECK(STR_OK(self->hset[i].str) && rt_str_hash(self, self->hset[i].str) == self->hset[i].hash, "hset");
    }
    for (uint32_t i = 0; i < self->n_sm; i++) {
        const rt_sm *m = &self->sm[i];
        CHECK(m->kind <= 2 && m->obj < self->n_obj && STR_OK(m->pattern), "sm");
        if (m->kind == 0) CHECK(STR_OK(m->value) && STR_OK(m->value_lower), "sm value");
        if (m->kind == 1) {
            CHECK(RANGE(m->set_off, m->set_n, self->n_hset), "sm set");
            for (uint32_t k = 1; k < m->set_n; k++)
                CHECK(self->hset[m->set_off + k].hash >= self->hset[m->set_off + k - 1].hash, "sm set order");
        }
    }
    for (uint32_t i = 0; i < self->n_pos; i++) {
        CHECK(STR_OR_NONE(self->pos[i].tag) && (self->pos[i].sm == RT_NONE || self->pos[i].sm < self->n_sm), "pos");
    }
    for (uint32_t i = 0; i < self->n_chunk; i++) {
        CHECK(STR_OK(self->chunk[i].str) && self->chunk[i].obj < self->n_obj, "chunk");
    }
    for (uint32_t i = 0; i < self->n_pt; i++) {
        const rt_pt *t = &self->pt[i];
        CHECK(t->obj < self->n_obj && t->sm < self->n_sm && (t->pos == RT_NONE || t->pos < self->n_pos) &&
              (t->chunk == RT_NONE || t->chunk < self->n_chunk), "pt");
        CHECK(RANGE(t->exc_off, (uint32_t)t->n_cn + t->n_prev, self->n_idx) && RANGE(t->and_off, t->n_and, self->n_idx),
              "pt lists");
        for (uint32_t k = 0; k < (uint32_t)t->n_cn + t->n_prev; k++) CHECK(self->idx[t->exc_off + k] < self->n_pt, "exc");
        for (uint32_t k = 0; k < t->n_and; k++) CHECK(self->idx[t->and_off + k] < self->n_pt, "and");
    }
    for (uint32_t i = 0; i < self->n_hint; i++) {
        const rt_hint *h = &self->hint[i];
        CHECK(h->kind <= 2 && RANGE(h->set_off, h->set_n, self->n_hset), "hint");
        for (uint32_t k = 1; k < h->set_n; k++)
            CHECK(self->hset[h->set_off + k].hash >= self->hset[h->set_off + k - 1].hash, "hint set order");
    }
    for (uint32_t i = 0; i < self->n_rule; i++) {
        const rt_rule *r = &self->rule[i];
        CHECK(r->obj < self->n_obj && STR_OK(r->id) && STR_OR_NONE(r->sub_id) && (r->cat == RT_NONE || r->cat < self->n_cat),
              "rule");
        CHECK(r->kind <= 2, "rule kind");
        CHECK(RANGE(r->pt_off, r->n_pt, self->n_idx) && RANGE(r->elno_off, r->n_elno, self->n_idx) &&
              RANGE(r->hints_off, (uint32_t)r->n_hints + r->n_pos_hints, self->n_hint) &&
              RANGE(r->ap_off, r->n_ap, self->n_idx) &&
              RANGE(r->tags_off, (uint32_t)r->n_tags + r->n_tone_tags, self->n_idx), "rule lists");
        for (uint32_t k = 0; k < r->n_pt; k++) CHECK(self->idx[r->pt_off + k] < self->n_pt, "rule pts");
        for (uint32_t k = 0; k < r->n_ap; k++) CHECK(self->idx[r->ap_off + k] < self->n_rule, "rule aps");
        for (uint32_t k = 0; k < (uint32_t)r->n_tags + r->n_tone_tags; k++) CHECK(STR_OK(self->idx[r->tags_off + k]), "tags");
        CHECK(r->anchor_hint < (int)r->n_hints && r->anchor_hint >= -1, "anchor");
        CHECK(r->n_pt <= 0x7FFF && r->moc >= 0 && r->moc <= r->n_pt, "rule sizes");
        if (r->kind == RULE_KIND_REGEX) CHECK(STR_OK(r->regex_pattern), "regex rule");
        for (uint32_t k = 0; k < r->n_hints; k++) CHECK(self->hint[r->hints_off + k].kind != HINT_KIND_POS, "hint kinds");
        for (uint32_t k = 0; k < r->n_pos_hints; k++) CHECK(self->hint[r->hints_off + r->n_hints + k].kind == HINT_KIND_POS, "pos hint kinds");
    }
    for (uint32_t i = 0; i < self->n_cat; i++) CHECK(STR_OR_NONE(self->cat[i].id), "cat");
    for (uint32_t i = 0; i < self->n_ient; i++) {
        const rt_ient *e = &self->ient[i];
        CHECK(STR_OK(e->str) && rt_str_hash(self, e->str) == e->hash && RANGE(e->list_off, e->list_n, self->n_idx), "ient");
    }
    for (uint32_t i = 0; i < self->n_unit; i++) {
        const rt_unit *u = &self->unit[i];
        CHECK(STR_OK(u->name) && u->kind <= 1 && RANGE(u->rule_off, u->rule_n, self->n_rule), "unit");
        for (int m = 0; m < 2; m++) {
            CHECK(RANGE(u->sel[m][0], u->sel[m][1], self->n_ient) && RANGE(u->sel[m][2], u->sel[m][3], self->n_ient) &&
                  RANGE(u->sel[m][4], u->sel[m][5], self->n_idx), "unit index");
            for (int w = 0; w < 2; w++) {
                for (uint32_t k = 0; k < u->sel[m][2 * w + 1]; k++) {
                    const rt_ient *e = &self->ient[u->sel[m][2 * w] + k];
                    CHECK(k == 0 || e->hash >= self->ient[u->sel[m][2 * w] + k - 1].hash, "index order");
                    for (uint32_t j = 0; j < e->list_n; j++) CHECK(self->idx[e->list_off + j] < u->rule_n, "index rule");
                }
            }
            for (uint32_t k = 0; k < u->sel[m][5]; k++) CHECK(self->idx[u->sel[m][4] + k] < u->rule_n, "unclassified");
        }
    }
    for (uint32_t i = 0; i < self->n_regex; i++) {
        CHECK(STR_OK(self->regex[i].pattern) && self->regex[i].val_off < self->objdata_size, "regex");
        CHECK(i == 0 || self->regex[i].hash >= self->regex[i - 1].hash, "regex order");
    }
#undef CHECK
#undef STR_OK
#undef STR_OR_NONE
#undef RANGE
    Py_RETURN_TRUE;
bad:
    PyErr_Format(PyExc_ValueError, "rule tables %S: bad table (%s)", self->name, what);
    return NULL;
}

/* the regex program for jregex.compile(pattern, flags): the offset of its encoded value in the object data, -1 if
 * there is none */
static PyObject *
rb_py_regex_program(RuleBlob *self, PyObject *args)
{
    PyObject *pattern;
    unsigned long flags;
    if (!PyArg_ParseTuple(args, "Uk", &pattern, &flags)) return NULL;
    uint32_t h = (rt_hash_unicode(pattern) ^ (uint32_t)((flags * 0x9E3779B1ul) & 0xFFFFFFFFul));
    uint32_t lo = 0, hi = self->n_regex;
    while (lo < hi) {
        uint32_t mid = lo + (hi - lo) / 2;
        if (self->regex[mid].hash < h) lo = mid + 1;
        else hi = mid;
    }
    for (; lo < self->n_regex && self->regex[lo].hash == h; lo++) {
        const rt_regex *e = &self->regex[lo];
        if (e->flags == flags && e->pattern < self->n_str && rt_str_eq(self, e->pattern, pattern))
            return PyLong_FromUnsignedLong(e->val_off);
    }
    return PyLong_FromLong(-1);
}

static PyObject *rb_py_unit_rules(RuleBlob *self, PyObject *args);
static PyObject *rb_py_rule_info(RuleBlob *self, PyObject *args);
static PyObject *rb_py_active_mask(RuleBlob *self, PyObject *args);
static PyObject *rb_py_select_rules(RuleBlob *self, PyObject *args);
static PyObject *rb_py_rule_ids(RuleBlob *self, PyObject *args);
static PyObject *rb_py_immunize(RuleBlob *self, PyObject *args);
static PyObject *rb_py_run_rule(RuleBlob *self, PyObject *args);

static PyMethodDef rb_methods[] = {
    {"meta", (PyCFunction)rb_py_meta, METH_NOARGS, "the META section (JSON)"},
    {"string", (PyCFunction)rb_py_string, METH_O, "a string of the pool"},
    {"set_types", (PyCFunction)rb_set_types, METH_VARARGS, "the type descriptors"},
    {"materialize", (PyCFunction)rb_py_materialize, METH_VARARGS, "create the object of a record"},
    {"decode_value", (PyCFunction)rb_py_decode_value, METH_VARARGS, "decode a value of the object data"},
    {"validate", (PyCFunction)rb_py_validate, METH_NOARGS, "check the references between the tables"},
    {"info", (PyCFunction)rb_py_info, METH_NOARGS, "sizes"},
    {"regex_program", (PyCFunction)rb_py_regex_program, METH_VARARGS, "the offset of a regex program"},
    {"unit_rules", (PyCFunction)rb_py_unit_rules, METH_VARARGS, "the object indices of the rules of a unit"},
    {"rule_info", (PyCFunction)rb_py_rule_info, METH_VARARGS, "the metadata of rules"},
    {"active_mask", (PyCFunction)rb_py_active_mask, METH_VARARGS, "the active rules of a range"},
    {"select_rules", (PyCFunction)rb_py_select_rules, METH_VARARGS, "the rules with ids, categories, ..."},
    {"rule_ids", (PyCFunction)rb_py_rule_ids, METH_VARARGS, "the ids of rules"},
    {"immunize", (PyCFunction)rb_py_immunize, METH_VARARGS, "apply the anti-patterns of a rule"},
    {"run_rule", (PyCFunction)rb_py_run_rule, METH_VARARGS, "match a rule"},
    {NULL, NULL, 0, NULL}
};

static PyMemberDef rb_members[] = {
    {"name", T_OBJECT, offsetof(RuleBlob, name), READONLY, NULL},
    {NULL, 0, 0, 0, NULL}
};

static PyTypeObject RuleBlobType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.RuleBlob",
    .tp_basicsize = sizeof(RuleBlob),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .tp_new = rb_new,
    .tp_dealloc = (destructor)rb_dealloc,
    .tp_traverse = (traverseproc)rb_traverse,
    .tp_clear = (inquiry)rb_clear,
    .tp_methods = rb_methods,
    .tp_members = rb_members,
};

/* unit_rules(unit): (first rule index, number of rules, [object indices of the rules]) */
static PyObject *
rb_py_unit_rules(RuleBlob *self, PyObject *args)
{
    unsigned int u;
    if (!PyArg_ParseTuple(args, "I", &u)) return NULL;
    if (u >= self->n_unit) {
        PyErr_SetString(PyExc_IndexError, "unit index out of range");
        return NULL;
    }
    const rt_unit *un = &self->unit[u];
    if ((uint64_t)un->rule_off + un->rule_n > self->n_rule) {
        PyErr_SetString(PyExc_ValueError, "rule tables: bad unit");
        return NULL;
    }
    PyObject *objs = PyList_New(un->rule_n);
    if (objs == NULL) return NULL;
    for (uint32_t i = 0; i < un->rule_n; i++) {
        PyObject *v = PyLong_FromUnsignedLong(self->rule[un->rule_off + i].obj);
        if (v == NULL) { Py_DECREF(objs); return NULL; }
        PyList_SET_ITEM(objs, i, v);
    }
    PyObject *r = Py_BuildValue("(IIN)", un->rule_off, un->rule_n, objs);
    return r;
}

/* rule_info(first, n): per rule (id, sub_id, category id or None, category default_on, flags, min_prev_matches,
 * tags tuple, tone tags tuple, kind) */
static PyObject *
rb_py_rule_info(RuleBlob *self, PyObject *args)
{
    unsigned int first, n;
    if (!PyArg_ParseTuple(args, "II", &first, &n)) return NULL;
    if ((uint64_t)first + n > self->n_rule) {
        PyErr_SetString(PyExc_IndexError, "rule index out of range");
        return NULL;
    }
    PyObject *out = PyList_New(n);
    if (out == NULL) return NULL;
    for (uint32_t i = 0; i < n; i++) {
        const rt_rule *r = &self->rule[first + i];
        PyObject *id = rb_string(self, r->id);
        PyObject *sub = r->sub_id == RT_NONE ? Py_None : rb_string(self, r->sub_id);
        PyObject *cat = Py_None;
        int default_on = 1;
        if (r->cat != RT_NONE) {
            if (r->cat >= self->n_cat) { PyErr_SetString(PyExc_ValueError, "rule tables: bad category"); goto error; }
            cat = self->cat[r->cat].id == RT_NONE ? Py_None : rb_string(self, self->cat[r->cat].id);
            default_on = self->cat[r->cat].default_on != 0;
        }
        if (id == NULL || sub == NULL || cat == NULL) goto error;
        if ((uint64_t)r->tags_off + r->n_tags + r->n_tone_tags > self->n_idx) {
            PyErr_SetString(PyExc_ValueError, "rule tables: bad tags");
            goto error;
        }
        PyObject *tags = PyTuple_New(r->n_tags);
        PyObject *tone = PyTuple_New(r->n_tone_tags);
        if (tags == NULL || tone == NULL) { Py_XDECREF(tags); Py_XDECREF(tone); goto error; }
        int ok = 1;
        for (uint32_t k = 0; k < (uint32_t)r->n_tags + r->n_tone_tags && ok; k++) {
            PyObject *s = rb_string(self, self->idx[r->tags_off + k]);
            if (s == NULL) { ok = 0; break; }
            Py_INCREF(s);
            if (k < r->n_tags) PyTuple_SET_ITEM(tags, k, s);
            else PyTuple_SET_ITEM(tone, k - r->n_tags, s);
        }
        if (!ok) { Py_DECREF(tags); Py_DECREF(tone); goto error; }
        PyObject *t = Py_BuildValue("(OOOiIiNNI)", id, sub, cat, default_on, r->flags, r->min_prev_matches, tags, tone,
                                    (unsigned)r->kind);
        if (t == NULL) goto error;
        PyList_SET_ITEM(out, i, t);
    }
    return out;
error:
    Py_DECREF(out);
    return NULL;
}

/* --- the table files of this build --- */

static PyObject *mapped_blobs = NULL;   /* dict name -> RuleBlob: the mapped tables (kept for the life of the process) */

/* the expected build id (32 hex digits) of the table of a language, NULL if this build has none */
static const char *
rt_expected_build_id(const char *name)
{
    int n = RT_TABLE_COUNT();
    for (int i = 0; i < n && langtool_rule_tables[i].name != NULL; i++) {
        if (strcmp(langtool_rule_tables[i].name, name) == 0) return langtool_rule_tables[i].build_id;
    }
    return NULL;
}

/* rule_blob_names(): the names (language codes) of the tables of this build */
static PyObject *
py_rule_blob_names(PyObject *Py_UNUSED(self), PyObject *Py_UNUSED(ignored))
{
    PyObject *out = PyList_New(0);
    if (out == NULL) return NULL;
    int n = RT_TABLE_COUNT();
    for (int i = 0; i < n && langtool_rule_tables[i].name != NULL; i++) {
        PyObject *s = PyUnicode_FromString(langtool_rule_tables[i].name);
        if (s == NULL || PyList_Append(out, s) < 0) { Py_XDECREF(s); Py_DECREF(out); return NULL; }
        Py_DECREF(s);
    }
    return out;
}

/* rule_blob_build_id(name): the build id (hex) of the table of a language in this build, None if there is none */
static PyObject *
py_rule_blob_build_id(PyObject *Py_UNUSED(self), PyObject *name)
{
    if (!PyUnicode_Check(name)) {
        PyErr_SetString(PyExc_TypeError, "name must be a str");
        return NULL;
    }
    const char *cname = PyUnicode_AsUTF8(name);
    if (cname == NULL) return NULL;
    const char *id = rt_expected_build_id(cname);
    if (id == NULL) Py_RETURN_NONE;
    return PyUnicode_FromString(id);
}

/* maps and checks the table file path of the language name (format, size, build id): a new RuleBlob, NULL with an
 * exception set if it can't be used */
static RuleBlob *
rt_open_table(PyObject *name, PyObject *path, const char *expected)
{
    void *base;
    size_t size;
    if (rt_map_file(path, &base, &size) < 0) return NULL;   /* (releases the GIL) */
    RuleBlob *self = rb_alloc();
    if (self == NULL) {
        rt_unmap(base, size);
        return NULL;
    }
    self->map_base = base;
    self->map_size = size;
    self->base = base;
    self->size = size;
    Py_INCREF(name);
    self->name = name;
    if (rb_parse(self) < 0) {
        Py_DECREF(self);
        return NULL;
    }
    char hex[33];
    const uint8_t *id = ((const rt_header *)self->base)->build_id;
    for (int i = 0; i < 16; i++) {
        hex[2 * i] = "0123456789abcdef"[id[i] >> 4];
        hex[2 * i + 1] = "0123456789abcdef"[id[i] & 15];
    }
    hex[32] = 0;
    if (strcmp(hex, expected) != 0) {
        PyErr_Format(PyExc_ValueError, "rule tables: %U is of another build (build id %s, expected %s)", path, hex,
                     expected);
        Py_DECREF(self);
        return NULL;
    }
    return self;
}

/* map_rule_table(name, path, build_id): a table mapped and checked (not shared: the tests) */
static PyObject *
py_map_rule_table(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *name, *path;
    const char *expected;
    if (!PyArg_ParseTuple(args, "UUs", &name, &path, &expected)) return NULL;
    return (PyObject *)rt_open_table(name, path, expected);
}

/* rule_blob(name, path): the table of a language (shared: mapped once, for the life of the process), mapped
 * read-only from the file path and checked (format, size, the build id of this build); None if this build has no
 * table for the language. Raises OSError or ValueError if the file can't be used. */
static PyObject *
py_rule_blob(PyObject *Py_UNUSED(self), PyObject *args)
{
    PyObject *name, *path;
    if (!PyArg_ParseTuple(args, "UU", &name, &path)) return NULL;
    if (mapped_blobs == NULL) {
        mapped_blobs = PyDict_New();
        if (mapped_blobs == NULL) return NULL;
    }
    PyObject *b = PyDict_GetItemWithError(mapped_blobs, name);
    if (b != NULL) { Py_INCREF(b); return b; }
    if (PyErr_Occurred()) return NULL;
    const char *cname = PyUnicode_AsUTF8(name);
    if (cname == NULL) return NULL;
    const char *expected = rt_expected_build_id(cname);
    if (expected == NULL) Py_RETURN_NONE;
    RuleBlob *self = rt_open_table(name, path, expected);
    if (self == NULL) return NULL;
    /* (another thread may have mapped it meanwhile, the GIL is released while mapping: the first one is kept) */
    b = PyDict_GetItemWithError(mapped_blobs, name);
    if (b != NULL) {
        Py_INCREF(b);
        Py_DECREF(self);
        return b;
    }
    if (PyErr_Occurred() || PyDict_SetItem(mapped_blobs, name, (PyObject *)self) < 0) {
        Py_DECREF(self);
        return NULL;
    }
    return (PyObject *)self;
}
