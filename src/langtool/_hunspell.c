/*
 * _hunspell.c
 * C implementation of langtool.hunspell (the port of Hunspell 1.7.1): the
 * word table, the affix and compound checks, spell(), the suggestions and
 * the loading of the .dic file. It is part of the _speedups extension.
 *
 * The pure Python implementation (langtool/hunspell.py) is the reference:
 * this code is a literal port of it (including its quirks), and the results
 * must be identical. The Python side parses the .aff file and passes the
 * parsed data to HunDict.__init__; HunDict.load_dic reads the .dic file.
 *
 * Words are byte strings (UTF-8 or the 8-bit encoding of the dictionary);
 * "units" are the UTF-16 code units Python's version works with (str
 * objects there, uint16_t arrays here).
 *
 * Data: the words are in an open-addressing hash table (with a Bloom
 * filter in front of it, most lookups are for words that do not exist),
 * the entries (homonyms are chained) in an array, their sorted flag sets
 * in a shared pool. The affix entries are arrays with the NextEQ/NextNE
 * links of Hunspell's sorted affix lists (computed by the Python side).
 *
 * Memory: the temporary strings of a call live in an arena with stack
 * discipline (amark/arelease); the results of a suggestion call in a
 * second arena that is freed at the end of the call. An allocation failure
 * longjmps to the entry point, which frees both and raises MemoryError.
 *
 * Threads: spell() and add() run with the GIL held, suggest() releases it
 * (it only uses the C data). A busy flag rejects concurrent use of a
 * dictionary; the Python object serializes the calls with its lock. The
 * lazily built tables (ngram index, MAP pruning) are built during such a
 * call and freed when add() changes the word list.
 *
 * Besides the literal port there are two exact shortcuts (they can not
 * change the results): the compound pass of the suggestions is skipped for
 * dictionaries without compounding, and the MAP search prunes the partial
 * candidates that can not become a word of the affix checks (see
 * MapPrune).
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <time.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

typedef uint16_t flag_t;

#define H_FLAG_NULL 0
#define H_ONLYUPCASEFLAG 65511

enum { H_NOCAP, H_INITCAP, H_ALLCAP, H_HUHCAP, H_HUHINITCAP };

#define SPELL_COMPOUND (1 << 0)
#define SPELL_FORBIDDEN (1 << 1)
#define SPELL_ALLCAP (1 << 2)
#define SPELL_NOCAP (1 << 3)
#define SPELL_INITCAP (1 << 4)
#define SPELL_ORIGCAP (1 << 5)
#define SPELL_WARN (1 << 6)

enum { IN_CPD_NOT, IN_CPD_BEGIN, IN_CPD_END, IN_CPD_OTHER };

#define AE_XPRODUCT 1

#define H_FLAG_CHAR 0
#define H_FLAG_LONG 1
#define H_FLAG_NUM 2
#define H_FLAG_UNI 3

#define H_MAXWORDLEN 100
#define H_MAXWORDUTF8LEN 300
#define H_MAXSHARPS 5
#define H_MAX_CHAR_DISTANCE 4
#define H_LANG_az 100
#define H_LANG_crh 102
#define H_LANG_de 49
#define H_LANG_hu 36
#define H_LANG_tr 90

#define NO_INFO (-1) /* compound_check: info is None */

/* ------------------------------------------------------------------------ */
/* arena */

typedef struct ABlock {
    struct ABlock *prev;
    size_t size;
    size_t used;
    size_t pad;
} ABlock;

#define ABLOCK_DATA(b) ((unsigned char *)(b) + sizeof(ABlock))
#define ABLOCK_SIZE 65536

typedef struct {
    ABlock *cur;
    ABlock *spare;
    jmp_buf *jb;
} Arena;

typedef struct {
    ABlock *b;
    size_t used;
} AMark;

static void *
aalloc(Arena *a, size_t n)
{
    n = (n + 15) & ~(size_t)15;
    ABlock *b = a->cur;
    if (b == NULL || b->size - b->used < n) {
        ABlock *nb;
        if (a->spare != NULL && a->spare->size >= n) {
            nb = a->spare;
            a->spare = NULL;
        } else {
            size_t sz = n > ABLOCK_SIZE ? n : ABLOCK_SIZE;
            nb = malloc(sizeof(ABlock) + sz);
            if (nb == NULL) longjmp(*a->jb, 1);
            nb->size = sz;
        }
        nb->used = 0;
        nb->prev = b;
        a->cur = nb;
        b = nb;
    }
    void *p = ABLOCK_DATA(b) + b->used;
    b->used += n;
    return p;
}

static inline AMark
amark(Arena *a)
{
    AMark m;
    m.b = a->cur;
    m.used = a->cur != NULL ? a->cur->used : 0;
    return m;
}

static void
arelease(Arena *a, AMark m)
{
    while (a->cur != m.b) {
        ABlock *p = a->cur->prev;
        if (a->spare == NULL) {
            a->spare = a->cur;
        } else if (a->spare->size < a->cur->size) {
            free(a->spare);
            a->spare = a->cur;
        } else {
            free(a->cur);
        }
        a->cur = p;
    }
    if (a->cur != NULL) a->cur->used = m.used;
}

static void
afree(Arena *a)
{
    while (a->cur != NULL) {
        ABlock *p = a->cur->prev;
        free(a->cur);
        a->cur = p;
    }
    free(a->spare);
    a->spare = NULL;
}

/* ------------------------------------------------------------------------ */
/* data */

typedef struct {
    uint32_t word;   /* offset in wpool */
    uint32_t flags;  /* offset in fpool of the sorted flags (with duplicates), fpool[flags - 1]: their number;
                      * 0: no flags */
    int32_t next;    /* the next homonym */
    int32_t phon;    /* index in phon, -1: none */
    uint32_t wlen : 31;
    uint32_t head : 1;   /* the first homonym (in the hash table) */
} HEntry;

typedef struct {
    uint32_t h;      /* the high bits of the hash */
    int32_t e;       /* the first homonym, -1: empty slot */
} WSlot;

typedef struct {
    const uint8_t *appnd;
    const uint8_t *strip;
    const uint8_t *conds;
    const uint8_t *key;
    const flag_t *cont;
    int appnd_len, strip_len, conds_len, key_len, ncont;
    int numconds;
    int opts;
    int utf8;
    int key_dot;     /* '.' in key */
    flag_t aflag;
    int32_t next, nexteq, nextne;
} AffEntry;

typedef struct {
    const uint8_t *s;
    int n;
} BStr;

typedef struct {
    BStr pat;
    BStr out[4];
} RepEntry;

typedef struct {
    RepEntry *v;
    int n;
} RepTable;

typedef struct {
    BStr pat, pat2, pat3;
    flag_t cond, cond2;
} CpdPat;

typedef struct {
    flag_t *f;
    int n;
} FlagRule;

typedef struct {
    BStr *v;
    int n;
} MapEntry;

typedef struct HunDict {
    PyObject_HEAD
    /* HashMgr settings */
    int h_utf8, h_cpx, h_langnum, flag_mode;
    flag_t h_forbidden;
    BStr h_ignore;
    flag_t **aliasf; int *aliasf_n; int naliasf;
    BStr *aliasm; int naliasm; int has_aliasm;
    /* AffixMgr settings */
    int a_utf8, a_cpx, a_langnum;
    flag_t a_forbidden;
    BStr a_ignore;
    int has_ignore_units;
    flag_t compoundflag, compoundbegin, compoundmiddle, compoundend, compoundroot, compoundpermitflag,
        compoundforbidflag, nosuggest, nongramsuggest, needaffix, circumfix, onlyincompound, keepcase, forceucase,
        warn, substandard;
    int compoundmoresuffixes, checkcompounddup, checkcompoundrep, checkcompoundcase, checkcompoundtriple,
        simplifiedtriple, fullstrip, checksharps, forbidwarn, havecontclass, nosplitsugs, sugswithdots,
        onlymaxdiff, simplifiedcpd, is_compound, lang_with_dash_usage;
    int cpdwordmax, cpdmin, cpdmaxsyllable, maxngramsugs, maxdiff, s_maxngramsugs, s_maxcpdsugs, maxsug;
    uint16_t *cpdvowels; int ncpdvowels;
    uint8_t *contclasses;        /* bitmap of 65536 flags */
    CpdPat *checkcpd; int ncheckcpd;
    FlagRule *defcpd; int ndefcpd;
    MapEntry *maptable; int nmaptable;
    RepTable rep;
    BStr *wordbreak; int nwordbreak;
    RepTable iconv, oconv;       /* sorted pattern tables; n < 0: none */
    uint16_t *ckey; int nckey;
    uint16_t *ctry; int nctry;
    uint16_t *upper, *lower, *plain_upper;   /* 65536 entries each */
    /* affixes */
    AffEntry *pent; int npent;
    AffEntry *sent; int nsent;
    int32_t pstart[256], sstart[256];
    int32_t **pflag; int *pflag_n;   /* 256 lists */
    int32_t **sflag; int *sflag_n;
    int max_pfx_key, max_sfx_key;
    int pfx_groups;                  /* the Python version searches the prefixes by groups (empty word: none) */
    /* the strings of the settings */
    uint8_t **blobs; int nblobs, cblobs;
    /* words */
    HEntry *ent; int nent, cent;
    uint8_t *wpool; size_t wpool_n, wpool_c;
    flag_t *fpool; size_t fpool_n, fpool_c;
    WSlot *slots; uint32_t nslots;   /* power of 2 */
    uint64_t *bloom; uint32_t bloom_mask;
    BStr *phon; int nphon, cphon;
    long tablesize;
    /* flag set dedup (load) */
    uint32_t *fsets; uint32_t nfsets_slots; uint32_t nfsets;
    /* ngram data (lazy) */
    int32_t *ng_order; uint8_t *ng_clen; uint8_t *ng_bits; int ng_n;
    uint64_t *ng_pos;                /* (the ngram scan) */
    int ng_pos_dirty;
    struct MapPrune *mp;             /* (the pruning of the MAP suggestions, lazy) */
    int busy;
} HunDict;

#define NG_SKIP 1
#define NG_INITCAP 2

/* the state of a call (AffixMgr's pfx/sfx etc.) */
typedef struct {
    HunDict *d;
    Arena ar;     /* temporaries */
    Arena keep;   /* results */
    jmp_buf jb;
    int32_t pfx, sfx;
    int has_deadline;
    double deadline, time_limit;
    int map_timer_on, map_count, map_abort;
    double map_deadline;
    int no_map_prune;   /* (tests: the MAP search without pruning) */
    unsigned pfx_gen, sfx_gen;  /* (counters of the assignments of pfx and sfx: the memo) */
    struct Memo *memo;          /* the memo of the affix checks of compound_check (suggest()), NULL: none */
} Ctx;

#define SET_PFX(c, v) ((c)->pfx = (v), (c)->pfx_gen++)
#define SET_SFX(c, v) ((c)->sfx = (v), (c)->sfx_gen++)

/* time.perf_counter() */
static double
now_mono(void)
{
#ifdef _WIN32
    static LARGE_INTEGER freq;
    LARGE_INTEGER t;
    if (freq.QuadPart == 0) QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart / (double)freq.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
#endif
}

static inline int
popcount64(uint64_t x)
{
    x = x - ((x >> 1) & 0x5555555555555555ULL);
    x = (x & 0x3333333333333333ULL) + ((x >> 2) & 0x3333333333333333ULL);
    x = (x + (x >> 4)) & 0x0f0f0f0f0f0f0f0fULL;
    return (int)((x * 0x0101010101010101ULL) >> 56);
}

/* ------------------------------------------------------------------------ */
/* flags and strings */

static inline int
flags_has(const flag_t *f, int n, flag_t x)
{
    if (n <= 8) {
        for (int i = 0; i < n; i++)
            if (f[i] == x) return 1;
        return 0;
    }
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int m = (lo + hi) >> 1;
        if (f[m] == x) return 1;
        if (f[m] < x) lo = m + 1; else hi = m - 1;
    }
    return 0;
}

#define EFLAGS(d, e) ((d)->fpool + (d)->ent[e].flags)
#define ENFLAGS(d, e) ((d)->ent[e].flags ? (int)(d)->fpool[(d)->ent[e].flags - 1] : 0)
#define EHAS(d, e, x) flags_has(EFLAGS(d, e), ENFLAGS(d, e), (x))
#define EWORD(d, e) ((d)->wpool + (d)->ent[e].word)
#define EWLEN(d, e) ((int)(d)->ent[e].wlen)
#define CONT_HAS(a, x) flags_has((a)->cont, (a)->ncont, (x))

static inline uint8_t *
bdup(Ctx *c, const uint8_t *s, int n)
{
    uint8_t *p = aalloc(&c->ar, (size_t)n + 1);
    if (n) memcpy(p, s, (size_t)n);
    p[n] = 0;
    return p;
}

/* a + b in the temporary arena */
static inline uint8_t *
bcat(Ctx *c, const uint8_t *a, int an, const uint8_t *b, int bn)
{
    uint8_t *p = aalloc(&c->ar, (size_t)an + (size_t)bn + 1);
    if (an) memcpy(p, a, (size_t)an);
    if (bn) memcpy(p + an, b, (size_t)bn);
    p[an + bn] = 0;
    return p;
}

static inline uint8_t *
bcat3(Ctx *c, const uint8_t *a, int an, const uint8_t *b, int bn, const uint8_t *x, int xn)
{
    uint8_t *p = aalloc(&c->ar, (size_t)an + (size_t)bn + (size_t)xn + 1);
    if (an) memcpy(p, a, (size_t)an);
    if (bn) memcpy(p + an, b, (size_t)bn);
    if (xn) memcpy(p + an + bn, x, (size_t)xn);
    p[an + bn + xn] = 0;
    return p;
}

/* Python's slice bounds for s[a:b] of a string of length n (non-negative a, b) */
static inline void
clamp_slice(int n, int *a, int *b)
{
    if (*a > n) *a = n;
    if (*b > n) *b = n;
    if (*a < 0) *a = 0;
    if (*b < *a) *b = *a;
}

/* bytes.find(needle, start) */
static int
py_find(const uint8_t *h, int hn, const uint8_t *nd, int nn, int start)
{
    if (start < 0) start = 0;
    if (start > hn) return -1;
    if (nn == 0) return start;
    if (nn > hn - start) return -1;
    const uint8_t *p = h + start;
    const uint8_t *end = h + hn - nn;
    while (p <= end) {
        p = memchr(p, nd[0], (size_t)(end - p) + 1);
        if (p == NULL) return -1;
        if (memcmp(p, nd, (size_t)nn) == 0) return (int)(p - h);
        p++;
    }
    return -1;
}

static inline int
has_four_byte(const uint8_t *b, int n)
{
    for (int i = 0; i < n; i++)
        if (b[i] >= 0xf0) return 1;
    return 0;
}

/* csutil's u8_u16 (see hunspell.u8_u16): out must have room for n units; returns the number of units */
static int
u8_u16_raw(const uint8_t *b, int n, uint16_t *out)
{
    int k = 0;
    int i = 0;
#define AT(j) ((j) < n ? b[j] : 0)
    while (i < n) {
        int c = b[i];
        if (c < 0x80) {
            out[k++] = (uint16_t)c;
            i++;
            continue;
        }
        int hi = c & 0xf0;
        if (hi < 0xc0) {
            out[k++] = 0xfffd;
        } else if (hi < 0xe0) {
            if ((AT(i + 1) & 0xc0) == 0x80) {
                out[k++] = (uint16_t)(((c & 0x1f) << 6) | (AT(i + 1) & 0x3f));
                i++;
            } else {
                out[k++] = 0xfffd;
            }
        } else if (hi == 0xe0) {
            if ((AT(i + 1) & 0xc0) == 0x80) {
                int h = (((c & 0x0f) << 4) + ((AT(i + 1) & 0x3f) >> 2)) & 0xff;
                i++;
                if ((AT(i + 1) & 0xc0) == 0x80) {
                    int lo = ((b[i] << 6) + (AT(i + 1) & 0x3f)) & 0xff;
                    i++;
                    out[k++] = (uint16_t)((h << 8) | lo);
                } else {
                    out[k++] = 0xfffd;
                }
            } else {
                out[k++] = 0xfffd;
            }
        } else {
            out[k++] = 0xfffd;
            break;
        }
        i++;
    }
#undef AT
    return k;
}

/* Python's u8_u16 decodes valid UTF-8 without 4-byte sequences with the codec
 * (strict), which gives the same units as the literal conversion. */

static int
u8_u16(Ctx *c, const uint8_t *b, int n, uint16_t **out)
{
    uint16_t *u = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 1));
    *out = u;
    return u8_u16_raw(b, n, u);
}

static int
u16_u8_raw(const uint16_t *u, int n, uint8_t *out)
{
    int k = 0;
    for (int i = 0; i < n; i++) {
        unsigned v = u[i];
        if (v < 0x80) {
            out[k++] = (uint8_t)v;
        } else if (v < 0x800) {
            out[k++] = (uint8_t)(0xc0 | (v >> 6));
            out[k++] = (uint8_t)(0x80 | (v & 0x3f));
        } else {
            out[k++] = (uint8_t)(0xe0 | (v >> 12));
            out[k++] = (uint8_t)(0x80 | ((v >> 6) & 0x3f));
            out[k++] = (uint8_t)(0x80 | (v & 0x3f));
        }
    }
    return k;
}

static int
u16_u8(Ctx *c, const uint16_t *u, int n, uint8_t **out)
{
    uint8_t *b = aalloc(&c->ar, 3 * (size_t)n + 1);
    int k = u16_u8_raw(u, n, b);
    b[k] = 0;
    *out = b;
    return k;
}

/* self._units (utf8: the AffixMgr's or the HashMgr's flag, as the caller says) */
static int
to_units(Ctx *c, const uint8_t *b, int n, int utf8, uint16_t **out)
{
    if (utf8) return u8_u16(c, b, n, out);
    uint16_t *u = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 1));
    for (int i = 0; i < n; i++) u[i] = b[i];
    *out = u;
    return n;
}

/* self._from_units */
static int
from_units(Ctx *c, const uint16_t *u, int n, int utf8, uint8_t **out)
{
    if (utf8) return u16_u8(c, u, n, out);
    uint8_t *b = aalloc(&c->ar, (size_t)n + 1);
    for (int i = 0; i < n; i++) b[i] = (uint8_t)u[i];
    b[n] = 0;
    *out = b;
    return n;
}

static inline uint16_t *
udup(Ctx *c, const uint16_t *u, int n)
{
    uint16_t *r = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 1));
    if (n) memcpy(r, u, sizeof(uint16_t) * (size_t)n);
    return r;
}

static inline void
u_lower(HunDict *d, uint16_t *u, int n)
{
    for (int i = 0; i < n; i++) u[i] = d->lower[u[i]];
}

static inline void
u_upper(HunDict *d, uint16_t *u, int n)
{
    for (int i = 0; i < n; i++) u[i] = d->upper[u[i]];
}

/* captype_units */
static int
captype_units(HunDict *d, const uint16_t *u, int n)
{
    int same = 1;
    for (int i = 0; i < n; i++)
        if (d->lower[u[i]] != u[i]) { same = 0; break; }
    if (same) return H_NOCAP;
    int ncap = 0, nneutral = 0;
    for (int i = 0; i < n; i++) {
        uint16_t lo = d->lower[u[i]];
        if (u[i] != lo) ncap++;
        if (d->upper[u[i]] == lo) nneutral++;
    }
    int firstcap = u[0] != d->lower[u[0]];
    if (ncap == 1 && firstcap) return H_INITCAP;
    if (ncap == n || ncap + nneutral == n) return H_ALLCAP;
    if (ncap > 1 && firstcap) return H_HUHINITCAP;
    return H_HUHCAP;
}

/* _remove_ignored(b, ignore) */
static int
remove_ignored(Ctx *c, const uint8_t *b, int n, BStr ignore, const uint8_t **out)
{
    HunDict *d = c->d;
    *out = b;
    if (ignore.n == 0) return n;
    if (d->a_utf8) {
        AMark m = amark(&c->ar);
        uint16_t *ig, *u;
        int ni = u8_u16(c, ignore.s, ignore.n, &ig);
        int nu = u8_u16(c, b, n, &u);
        int any = 0;
        for (int i = 0; i < nu && !any; i++)
            for (int j = 0; j < ni; j++)
                if (u[i] == ig[j]) { any = 1; break; }
        if (!any) {
            arelease(&c->ar, m);
            return n;
        }
        int k = 0;
        for (int i = 0; i < nu; i++) {
            int in = 0;
            for (int j = 0; j < ni; j++)
                if (u[i] == ig[j]) { in = 1; break; }
            if (!in) u[k++] = u[i];
        }
        uint8_t *r;
        int rn = u16_u8(c, u, k, &r);
        *out = r;
        return rn;
    }
    uint8_t *r = aalloc(&c->ar, (size_t)n + 1);
    int k = 0;
    for (int i = 0; i < n; i++)
        if (memchr(ignore.s, b[i], (size_t)ignore.n) == NULL) r[k++] = b[i];
    r[k] = 0;
    *out = r;
    return k;
}

/* _reverse_utf (or the reversed bytes) */
static int
reverse_word(Ctx *c, const uint8_t *b, int n, int utf8, const uint8_t **out)
{
    if (utf8) {
        uint16_t *u;
        int nu = u8_u16(c, b, n, &u);
        for (int i = 0, j = nu - 1; i < j; i++, j--) {
            uint16_t t = u[i]; u[i] = u[j]; u[j] = t;
        }
        uint8_t *r;
        int rn = u16_u8(c, u, nu, &r);
        *out = r;
        return rn;
    }
    uint8_t *r = aalloc(&c->ar, (size_t)n + 1);
    for (int i = 0; i < n; i++) r[i] = b[n - 1 - i];
    r[n] = 0;
    *out = r;
    return n;
}

/* ------------------------------------------------------------------------ */
/* the word table */

/* the hash of a word (8 bytes at a time, with a final mix): the slot index
 * uses the low bits, the tag the high 32 bits, the Bloom filter two other
 * bit ranges */
static inline uint64_t
hfinal(uint64_t h)
{
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= h >> 33;
    return h;
}

static inline uint64_t
whash(const uint8_t *p, int n)
{
    uint64_t h = 0x9E3779B97F4A7C15ULL ^ (uint64_t)(uint32_t)n;
    while (n >= 8) {
        uint64_t v;
        memcpy(&v, p, 8);
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
        v = __builtin_bswap64(v);
#endif
        h = (h ^ v) * 0xff51afd7ed558ccdULL;
        h ^= h >> 29;
        p += 8;
        n -= 8;
    }
    if (n) {
        uint64_t v = 0;
        for (int i = 0; i < n; i++) v |= (uint64_t)p[i] << (8 * i);
        h = (h ^ v) * 0xc4ceb9fe1a85ec53ULL;
        h ^= h >> 29;
    }
    return hfinal(h);
}

/* whash(a + b) without the concatenation */
static uint64_t
whash2(const uint8_t *a, int an, const uint8_t *b, int bn)
{
    uint64_t h = 0x9E3779B97F4A7C15ULL ^ (uint64_t)(uint32_t)(an + bn);
    uint64_t v = 0;
    int k = 0;
    for (int i = 0; i < an + bn; i++) {
        v |= (uint64_t)(i < an ? a[i] : b[i - an]) << (8 * k);
        if (++k == 8) {
            h = (h ^ v) * 0xff51afd7ed558ccdULL;
            h ^= h >> 29;
            v = 0;
            k = 0;
        }
    }
    if (k) {
        h = (h ^ v) * 0xc4ceb9fe1a85ec53ULL;
        h ^= h >> 29;
    }
    return hfinal(h);
}

#define BLOOM1(h, m) ((uint32_t)((h) >> 20) & (m))
#define BLOOM2(h, m) ((uint32_t)(((h) * 0x9E3779B97F4A7C15ULL) >> 32) & (m))

static inline int
bloom_test(const HunDict *d, uint64_t h)
{
    uint32_t a = BLOOM1(h, d->bloom_mask), b = BLOOM2(h, d->bloom_mask);
    return ((d->bloom[a >> 6] >> (a & 63)) & 1) && ((d->bloom[b >> 6] >> (b & 63)) & 1);
}

static inline void
bloom_set(HunDict *d, uint64_t h)
{
    uint32_t a = BLOOM1(h, d->bloom_mask), b = BLOOM2(h, d->bloom_mask);
    d->bloom[a >> 6] |= (uint64_t)1 << (a & 63);
    d->bloom[b >> 6] |= (uint64_t)1 << (b & 63);
}

/* the first homonym of a + b (b may be empty), -1: none */
static int32_t
lookup2(const HunDict *d, const uint8_t *a, int an, const uint8_t *b, int bn)
{
    if (d->nslots == 0) return -1;
    uint64_t h;
    if (bn == 0) {
        h = whash(a, an);
    } else if (an + bn <= 256) {
        uint8_t buf[256];
        memcpy(buf, a, (size_t)an);
        memcpy(buf + an, b, (size_t)bn);
        h = whash(buf, an + bn);
    } else {
        h = whash2(a, an, b, bn);
    }
    if (!bloom_test(d, h)) return -1;
    uint32_t tag = (uint32_t)(h >> 32);
    uint32_t mask = d->nslots - 1;
    uint32_t i = (uint32_t)h & mask;
    int n = an + bn;
    for (;;) {
        const WSlot *s = &d->slots[i];
        if (s->e < 0) return -1;
        if (s->h == tag) {
            const HEntry *e = &d->ent[s->e];
            const uint8_t *w = d->wpool + e->word;
            if ((int)e->wlen == n && (an == 0 || memcmp(w, a, (size_t)an) == 0)
                && (bn == 0 || memcmp(w + an, b, (size_t)bn) == 0))
                return s->e;
        }
        i = (i + 1) & mask;
    }
}

static inline int32_t
lookup(const HunDict *d, const uint8_t *w, int n)
{
    return lookup2(d, w, n, NULL, 0);
}

static void
slots_insert(WSlot *slots, uint32_t nslots, uint64_t h, int32_t e)
{
    uint32_t mask = nslots - 1;
    uint32_t i = (uint32_t)h & mask;
    while (slots[i].e >= 0) i = (i + 1) & mask;
    slots[i].h = (uint32_t)(h >> 32);
    slots[i].e = e;
}

/* a bigger table (and Bloom filter: 4 bits per slot, at least 8 per word) */
static int
grow_slots(HunDict *d, uint32_t want)
{
    uint32_t n = 1024;
    while (n < want) n <<= 1;
    WSlot *s = malloc(sizeof(WSlot) * n);
    uint64_t *bloom = calloc((size_t)n / 16, sizeof(uint64_t));
    if (s == NULL || bloom == NULL) {
        free(s);
        free(bloom);
        return -1;
    }
    for (uint32_t i = 0; i < n; i++) s[i].e = -1;
    free(d->slots);
    free(d->bloom);
    d->slots = s;
    d->nslots = n;
    d->bloom = bloom;
    d->bloom_mask = n * 4 - 1;
    /* (the heads of the homonym chains: the entries that are not a next) */
    for (int32_t e = 0; e < d->nent; e++) {
        HEntry *he = &d->ent[e];
        if (he->head) {
            uint64_t h = whash(d->wpool + he->word, (int)he->wlen);
            slots_insert(s, n, h, e);
            bloom_set(d, h);
        }
    }
    return 0;
}

static int
grow(void **p, size_t *cap, size_t need, size_t elsize)
{
    if (need <= *cap) return 0;
    size_t nc = *cap ? *cap : 64;
    while (nc < need) nc *= 2;
    void *np = realloc(*p, nc * elsize);
    if (np == NULL) return -1;
    *p = np;
    *cap = nc;
    return 0;
}

/* the offset of a sorted flag set in fpool (shared between the entries) */
static int
intern_flags(HunDict *d, const flag_t *f, int n, uint32_t *off)
{
    if (n == 0) {
        *off = 0;
        return 0;
    }
    uint32_t h = 2166136261u;
    for (int i = 0; i < n; i++) {
        h ^= f[i];
        h *= 16777619u;
    }
    h ^= (uint32_t)n;
    if (d->nfsets * 2 + 2 > d->nfsets_slots) {
        uint32_t ns = d->nfsets_slots ? d->nfsets_slots * 2 : 1024;
        uint32_t *s = malloc(sizeof(uint32_t) * 2 * ns);
        if (s == NULL) return -1;
        for (uint32_t i = 0; i < ns; i++) s[2 * i + 1] = UINT32_MAX;
        for (uint32_t i = 0; i < d->nfsets_slots; i++) {
            if (d->fsets[2 * i + 1] == UINT32_MAX) continue;
            uint32_t j = d->fsets[2 * i] & (ns - 1);
            while (s[2 * j + 1] != UINT32_MAX) j = (j + 1) & (ns - 1);
            s[2 * j] = d->fsets[2 * i];
            s[2 * j + 1] = d->fsets[2 * i + 1];
        }
        free(d->fsets);
        d->fsets = s;
        d->nfsets_slots = ns;
    }
    uint32_t mask = d->nfsets_slots - 1;
    uint32_t j = h & mask;
    while (d->fsets[2 * j + 1] != UINT32_MAX) {
        uint32_t o = d->fsets[2 * j + 1];
        if (d->fsets[2 * j] == h && d->fpool[o] == (flag_t)n && memcmp(d->fpool + o + 1, f, sizeof(flag_t) * n) == 0) {
            *off = o + 1;
            return 0;
        }
        j = (j + 1) & mask;
    }
    /* the set is stored after its length (n < 65536 is checked by the caller) */
    if (grow((void **)&d->fpool, &d->fpool_c, d->fpool_n + (size_t)n + 1, sizeof(flag_t)) < 0) return -1;
    uint32_t o = (uint32_t)d->fpool_n;
    d->fpool[o] = (flag_t)n;
    memcpy(d->fpool + o + 1, f, sizeof(flag_t) * n);
    d->fpool_n += (size_t)n + 1;
    d->fsets[2 * j] = h;
    d->fsets[2 * j + 1] = o;
    d->nfsets++;
    *off = o + 1;
    return 0;
}

static void
sort_flags(flag_t *f, int n)
{
    for (int i = 1; i < n; i++) {
        flag_t x = f[i];
        int j = i - 1;
        while (j >= 0 && f[j] > x) {
            f[j + 1] = f[j];
            j--;
        }
        f[j + 1] = x;
    }
}

/* HashMgr::add_word (the flags are sorted): the new entry, -1 if none was added, -2 on memory errors */
static int32_t
add_word(HunDict *d, const uint8_t *w, int n, const flag_t *flags, int nflags, int onlyupcase)
{
    uint32_t foff;
    if (nflags > 65535) nflags = 65535;
    int32_t dp = lookup(d, w, n);
    if (dp >= 0) {
        while (d->ent[dp].next >= 0) dp = d->ent[dp].next;
        if (onlyupcase) return -1;
        if (EHAS(d, dp, H_ONLYUPCASEFLAG)) {
            if (intern_flags(d, flags, nflags, &foff) < 0) return -2;
            d->ent[dp].flags = foff;
            return -1;
        }
    }
    if (intern_flags(d, flags, nflags, &foff) < 0) return -2;
    if (d->nent >= INT32_MAX - 1 || n > INT32_MAX / 2) return -2;
    size_t cent = (size_t)d->cent;
    if (grow((void **)&d->ent, &cent, (size_t)d->nent + 1, sizeof(HEntry)) < 0) return -2;
    d->cent = (int)cent;
    if (dp < 0) {
        if (grow((void **)&d->wpool, &d->wpool_c, d->wpool_n + (size_t)n + 1, 1) < 0) return -2;
        if (d->wpool_n + (size_t)n + 1 > UINT32_MAX) return -2;
    }
    int32_t e = d->nent++;
    HEntry *he = &d->ent[e];
    if (dp >= 0) {
        he->word = d->ent[dp].word;
    } else {
        he->word = (uint32_t)d->wpool_n;
        memcpy(d->wpool + d->wpool_n, w, (size_t)n);
        d->wpool[d->wpool_n + n] = 0;
        d->wpool_n += (size_t)n + 1;
    }
    he->wlen = (uint32_t)n;
    he->flags = foff;
    he->next = -1;
    he->phon = -1;
    he->head = dp < 0;
    if (dp >= 0) {
        d->ent[dp].next = e;
    } else {
        if (((uint64_t)d->nent + 1) * 2 > d->nslots) {
            if (grow_slots(d, (uint32_t)((d->nent + 1) * 2)) < 0) {
                d->nent--;
                return -2;
            }
        } else {
            uint64_t h = whash(w, n);
            slots_insert(d->slots, d->nslots, h, e);
            bloom_set(d, h);
        }
    }
    return e;
}

/* ------------------------------------------------------------------------ */
/* affix conditions (PfxEntry::test_condition, SfxEntry::test_condition) */

static int
pfx_test_condition(const AffEntry *pe, const uint8_t *s, int slen)
{
    if (pe->numconds == 0) return 1;
    const uint8_t *c = pe->conds;
    int nc = pe->conds_len;
    int utf8 = pe->utf8;
    int st = 0;
    int pos = -1;
    int neg = 0;
    int ingroup = 0;
    int p = 0;
#define NEXTP(p) ((p) >= 0 && (p) + 1 < nc ? (p) + 1 : -1)
    for (;;) {
        int ch = c[p];
        if (ch == '[') {
            neg = 0;
            ingroup = 0;
            p = NEXTP(p);
            pos = st;
        } else if (ch == '^') {
            p = NEXTP(p);
            neg = 1;
        } else if (ch == ']') {
            if (neg == ingroup) return 0;
            pos = -1;
            p = NEXTP(p);
            if (!ingroup && st < slen) {
                st++;
                while (utf8 && st < slen && (s[st] & 0xc0) == 0x80) st++;
            }
            if (st == slen && p >= 0) return 0;
        } else if (ch == '.' && pos == -1) {
            p = NEXTP(p);
            st++;
            while (utf8 && st < slen && (s[st] & 0xc0) == 0x80) st++;
            if (st == slen && p >= 0) return 0;
        } else {
            if (st < slen && s[st] == ch) {
                st++;
                p = NEXTP(p);
                if (utf8 && (s[st - 1] & 0x80)) {
                    while (p >= 0 && (c[p] & 0xc0) == 0x80) {
                        if (c[p] != (st < slen ? s[st] : 0)) {
                            if (pos == -1) return 0;
                            st = pos;
                            break;
                        }
                        p = NEXTP(p);
                        st++;
                    }
                    if (pos != -1 && st != pos) {
                        ingroup = 1;
                        while (p >= 0 && c[p] != ']') p = NEXTP(p);
                    }
                } else if (pos != -1) {
                    ingroup = 1;
                    while (p >= 0 && c[p] != ']') p = NEXTP(p);
                }
            } else if (pos != -1) {
                p = NEXTP(p);
            } else {
                return 0;
            }
        }
        if (p < 0) return 1;
    }
}

static int
sfx_test_condition(const AffEntry *se, const uint8_t *s, int slen, int end)
{
    if (se->numconds == 0) return 1;
    const uint8_t *c = se->conds;
    int nc = se->conds_len;
    int utf8 = se->utf8;
    int numconds = se->numconds;
#define AT(k) ((k) >= 0 && (k) < slen ? s[k] : 0)
    int pos = -1; /* None */
    int haspos = 0;
    int neg = 0;
    int ingroup = 0;
    int p = 0;
    int st = end - 1;
    int i = 1;
    for (;;) {
        int ch = c[p];
        if (ch == '[') {
            p = NEXTP(p);
            pos = st;
            haspos = 1;
        } else if (ch == '^') {
            p = NEXTP(p);
            neg = 1;
        } else if (ch == ']') {
            if (!neg && !ingroup) return 0;
            i++;
            if (!ingroup) {
                while (utf8 && st >= 0 && (AT(st) & 0xc0) == 0x80) st--;
                st--;
            }
            haspos = 0;
            neg = 0;
            ingroup = 0;
            p = NEXTP(p);
            if (st < 0 && p >= 0) return 0;
        } else if (ch == '.' && !haspos) {
            p = NEXTP(p);
            st--;
            while (utf8 && st >= 0 && (AT(st) & 0xc0) == 0x80) st--;
            if (st < 0) return p < 0;
            if (utf8 && (AT(st) & 0x80)) {
                st--;
                if (st < 0) return p < 0;
            }
        } else {
            if (AT(st) == ch) {
                p = NEXTP(p);
                if (utf8 && (AT(st) & 0x80)) {
                    st--;
                    while (p >= 0 && st >= 0) {
                        if (c[p] != AT(st)) {
                            if (!haspos) return 0;
                            st = pos;
                            break;
                        }
                        if ((c[p] & 0xc0) != 0x80) break;
                        p = NEXTP(p);
                        st--;
                    }
                    if (haspos && st != pos) {
                        if (neg) return 0;
                        else if (i == numconds) return 1;
                        ingroup = 1;
                        while (p >= 0 && c[p] != ']') p = NEXTP(p);
                        st--;
                    }
                    if (p >= 0 && c[p] != ']') p = NEXTP(p);
                } else if (haspos) {
                    if (neg) return 0;
                    else if (i == numconds) return 1;
                    ingroup = 1;
                    while (p >= 0 && c[p] != ']') p = NEXTP(p);
                    st--;
                }
                if (!haspos) {
                    i++;
                    st--;
                }
                if (st < 0 && p >= 0 && c[p] != ']') return 0;
            } else if (haspos) {
                p = NEXTP(p);
            } else {
                return 0;
            }
        }
        if (p < 0) return 1;
    }
#undef AT
}
#undef NEXTP

/* _is_subset(key, word, start) ('.' matches any character, also after the end) */
static inline int
is_subset(const uint8_t *key, int kn, int dot, const uint8_t *w, int wn, int start)
{
    if (!dot) {
        if (start < 0 || start > wn || wn - start < kn) return 0;
        return memcmp(w + start, key, (size_t)kn) == 0;
    }
    for (int k = 0; k < kn; k++) {
        int pp = start + k;
        if (key[k] != '.' && (pp >= wn || key[k] != w[pp])) return 0;
    }
    return 1;
}

/* _is_rev_subset(key, seg, n, n) */
static inline int
is_rev_subset(const AffEntry *e, const uint8_t *seg, int n)
{
    if (e->key_len > n) return 0;
    int pp = n - 1;
    const uint8_t *key = e->key;
    if (!e->key_dot) {
        for (int k = 0; k < e->key_len; k++, pp--)
            if (seg[pp] != key[k]) return 0;
        return 1;
    }
    for (int k = 0; k < e->key_len; k++, pp--)
        if (key[k] != seg[pp] && key[k] != '.') return 0;
    return 1;
}

/* the first prefix entry of the search for word[start:] (_pfx_matches) */
#define PFX_SEG(d, wl, start, segn) do { \
        segn = (wl) - (start); \
        if (segn > (d)->max_pfx_key) segn = (d)->max_pfx_key; \
        if (segn < 0) segn = 0; \
    } while (0)

/* ------------------------------------------------------------------------ */
/* AffixMgr checks */

static int32_t suffix_check(Ctx *c, const uint8_t *w, int wl, int start, int length, int sfxopts,
                            const AffEntry *ppfx, flag_t cclass, flag_t needflag, int in_compound);
static int32_t suffix_check_twosfx(Ctx *c, const uint8_t *w, int wl, int start, int length, int sfxopts,
                                   const AffEntry *ppfx, flag_t needflag);

/* PfxEntry::checkword */
static int32_t
pfx_checkword(Ctx *c, const AffEntry *pe, const uint8_t *w, int wl, int start, int length, int in_compound,
              flag_t needflag)
{
    HunDict *d = c->d;
    int la = pe->appnd_len;
    int tmpl = length - la;
    if (tmpl > 0 || (tmpl == 0 && d->fullstrip)) {
        int a = start + la, b = start + la + tmpl;
        clamp_slice(wl, &a, &b);
        AMark m = amark(&c->ar);
        const uint8_t *tmpword = pe->strip_len ? bcat(c, pe->strip, pe->strip_len, w + a, b - a) : w + a;
        int tn = pe->strip_len + b - a;
        if (pfx_test_condition(pe, tmpword, tn)) {
            tmpl += pe->strip_len;
            int32_t he = lookup(d, tmpword, tn);
            if (he >= 0) {
                flag_t aflag = pe->aflag;
                int nacont = CONT_HAS(pe, d->needaffix);
                while (he >= 0) {
                    if (EHAS(d, he, aflag) && !nacont
                        && (needflag == H_FLAG_NULL || EHAS(d, he, needflag) || CONT_HAS(pe, needflag))) {
                        arelease(&c->ar, m);
                        return he;
                    }
                    he = d->ent[he].next;
                }
            }
            if (pe->opts & AE_XPRODUCT) {
                he = suffix_check(c, tmpword, tn, 0, tmpl, AE_XPRODUCT, pe, H_FLAG_NULL, needflag, in_compound);
                if (he >= 0) {
                    arelease(&c->ar, m);
                    return he;
                }
            }
        }
        arelease(&c->ar, m);
    }
    return -1;
}

static int32_t
prefix_check(Ctx *c, const uint8_t *w, int wl, int start, int length, int in_compound, flag_t needflag)
{
    HunDict *d = c->d;
    SET_PFX(c, -1);
    flag_t oic = d->onlyincompound, cpf = d->compoundpermitflag;
    for (int32_t i = d->pstart[0]; i >= 0; i = d->pent[i].next) {
        const AffEntry *pe = &d->pent[i];
        if ((in_compound != IN_CPD_NOT || !CONT_HAS(pe, oic)) && (in_compound != IN_CPD_END || CONT_HAS(pe, cpf))) {
            int32_t rv = pfx_checkword(c, pe, w, wl, start, length, in_compound, needflag);
            if (rv >= 0) {
                SET_PFX(c, i);
                return rv;
            }
        }
    }
    int segn;
    PFX_SEG(d, wl, start, segn);
    const uint8_t *seg = w + start;
    int32_t pp = segn ? d->pstart[seg[0]] : (d->pfx_groups ? -1 : d->pstart[0]);
    while (pp >= 0) {
        const AffEntry *pe = &d->pent[pp];
        if (is_subset(pe->key, pe->key_len, pe->key_dot, seg, segn, 0)) {
            if ((in_compound != IN_CPD_NOT || !CONT_HAS(pe, oic))
                && (in_compound != IN_CPD_END || CONT_HAS(pe, cpf))) {
                int32_t rv = pfx_checkword(c, pe, w, wl, start, length, in_compound, needflag);
                if (rv >= 0) {
                    SET_PFX(c, pp);
                    return rv;
                }
            }
            pp = pe->nexteq;
        } else {
            pp = pe->nextne;
        }
    }
    return -1;
}

/* PfxEntry::check_twosfx */
static int32_t
pfx_check_twosfx(Ctx *c, const AffEntry *pe, const uint8_t *w, int wl, int start, int length, int in_compound,
                 flag_t needflag)
{
    HunDict *d = c->d;
    int la = pe->appnd_len;
    int tmpl = length - la;
    if ((tmpl > 0 || (tmpl == 0 && d->fullstrip)) && tmpl + pe->strip_len >= pe->numconds) {
        int a = start + la, b = wl;
        clamp_slice(wl, &a, &b);
        AMark m = amark(&c->ar);
        uint8_t *tmpword = bcat(c, pe->strip, pe->strip_len, w + a, b - a);
        int tn = pe->strip_len + b - a;
        if (pfx_test_condition(pe, tmpword, tn)) {
            tmpl += pe->strip_len;
            if ((pe->opts & AE_XPRODUCT) && in_compound != IN_CPD_BEGIN) {
                int32_t he = suffix_check_twosfx(c, tmpword, tn, 0, tmpl, AE_XPRODUCT, pe, needflag);
                if (he >= 0) {
                    arelease(&c->ar, m);
                    return he;
                }
            }
        }
        arelease(&c->ar, m);
    }
    return -1;
}

static int32_t
prefix_check_twosfx(Ctx *c, const uint8_t *w, int wl, int start, int length, int in_compound, flag_t needflag)
{
    HunDict *d = c->d;
    SET_PFX(c, -1);
    for (int32_t i = d->pstart[0]; i >= 0; i = d->pent[i].next) {
        int32_t rv = pfx_check_twosfx(c, &d->pent[i], w, wl, start, length, in_compound, needflag);
        if (rv >= 0) return rv;
    }
    int segn;
    PFX_SEG(d, wl, start, segn);
    const uint8_t *seg = w + start;
    int32_t pp = segn ? d->pstart[seg[0]] : (d->pfx_groups ? -1 : d->pstart[0]);
    while (pp >= 0) {
        const AffEntry *pe = &d->pent[pp];
        if (is_subset(pe->key, pe->key_len, pe->key_dot, seg, segn, 0)) {
            int32_t rv = pfx_check_twosfx(c, pe, w, wl, start, length, in_compound, needflag);
            if (rv >= 0) {
                SET_PFX(c, pp);
                return rv;
            }
            pp = pe->nexteq;
        } else {
            pp = pe->nextne;
        }
    }
    return -1;
}

/* the conditions of suffix_check for a suffix entry */
static int
sfx_allowed(HunDict *d, const AffEntry *se, const AffEntry *ppfx, flag_t cclass, int in_compound)
{
    if (!(in_compound != IN_CPD_BEGIN
          || (se->ncont && d->compoundpermitflag != H_FLAG_NULL && CONT_HAS(se, d->compoundpermitflag))))
        return 0;
    flag_t circ = d->circumfix;
    if (circ != H_FLAG_NULL) {
        int pc = ppfx != NULL && CONT_HAS(ppfx, circ);
        int sc = CONT_HAS(se, circ);
        if (!((!pc && !sc) || (pc && sc))) return 0;
    }
    if (!(in_compound || !CONT_HAS(se, d->onlyincompound))) return 0;
    if (!(cclass != H_FLAG_NULL || !CONT_HAS(se, d->needaffix)
          || (ppfx != NULL && !CONT_HAS(ppfx, d->needaffix))))
        return 0;
    return 1;
}

/* SfxEntry::checkword */
static int32_t
sfx_checkword(Ctx *c, const AffEntry *se, const uint8_t *w, int wl, int start, int length, int optflags,
              const AffEntry *ppfx, flag_t cclass, flag_t needflag, flag_t badflag)
{
    HunDict *d = c->d;
    if ((optflags & AE_XPRODUCT) && !(se->opts & AE_XPRODUCT)) return -1;
    int tmpl = length - se->appnd_len;
    if ((tmpl > 0 || (tmpl == 0 && d->fullstrip)) && tmpl + se->strip_len >= se->numconds) {
        int a = start, b = start + tmpl;
        clamp_slice(wl, &a, &b);
        AMark m = amark(&c->ar);
        const uint8_t *tmp = se->strip_len ? bcat(c, w + a, b - a, se->strip, se->strip_len) : w + a;
        int tn = b - a + se->strip_len;
        int32_t res = -1;
        if (sfx_test_condition(se, tmp, tn, tn)) {
            int32_t he = lookup(d, tmp, tn);
            flag_t aflag = se->aflag;
            while (he >= 0) {
                if ((EHAS(d, he, aflag) || (ppfx != NULL && CONT_HAS(ppfx, aflag)))
                    && (!(optflags & AE_XPRODUCT) || (ppfx != NULL && EHAS(d, he, ppfx->aflag))
                        || (ppfx != NULL && CONT_HAS(se, ppfx->aflag)))
                    && (cclass == H_FLAG_NULL || CONT_HAS(se, cclass))
                    && (badflag == H_FLAG_NULL || !EHAS(d, he, badflag))
                    && (needflag == H_FLAG_NULL || EHAS(d, he, needflag) || CONT_HAS(se, needflag))) {
                    res = he;
                    break;
                }
                he = d->ent[he].next;
            }
        }
        arelease(&c->ar, m);
        return res;
    }
    return -1;
}

/* the stem lookups of a suffix_check call (the suffix entries often share their strip strings) */
#define STEM_CACHE 8
typedef struct {
    int n;
    int alen[STEM_CACHE];
    const uint8_t *strip[STEM_CACHE];
    int found[STEM_CACHE];
} StemCache;

static inline int
stem_found(const HunDict *d, StemCache *sc, const uint8_t *w, int a, int b, const AffEntry *e)
{
    for (int k = 0; k < sc->n; k++)
        if (sc->alen[k] == e->appnd_len && sc->strip[k] == e->strip) return sc->found[k];
    int f = lookup2(d, w + a, b - a, e->strip, e->strip_len) >= 0;
    int k = sc->n < STEM_CACHE ? sc->n++ : (int)(((uintptr_t)e->strip >> 4) % STEM_CACHE);
    sc->alen[k] = e->appnd_len;
    sc->strip[k] = e->strip;
    sc->found[k] = f;
    return f;
}

static int32_t
suffix_check(Ctx *c, const uint8_t *w, int wl, int start, int length, int sfxopts, const AffEntry *ppfx,
             flag_t cclass, flag_t needflag, int in_compound)
{
    HunDict *d = c->d;
    StemCache sc;
    sc.n = 0;
    flag_t badflag = in_compound ? H_FLAG_NULL : d->onlyincompound;
    int32_t se = d->sstart[0];
    if (se >= 0 && length == 0 && !d->fullstrip) se = -1;
    if (se >= 0) {
        int a = start, b = start + length;
        clamp_slice(wl, &a, &b);
        for (; se >= 0; se = d->sent[se].next) {
            const AffEntry *e = &d->sent[se];
            if (cclass != H_FLAG_NULL && !e->ncont) continue;
            /* (shortcut: the entry can only match if the stem is a dictionary word) */
            if (!stem_found(d, &sc, w, a, b, e)) continue;
            if (sfx_allowed(d, e, ppfx, cclass, in_compound)) {
                int32_t rv = sfx_checkword(c, e, w, wl, start, length, sfxopts, ppfx, cclass, needflag, badflag);
                if (rv >= 0) {
                    SET_SFX(c, se);
                    return rv;
                }
            }
        }
    }
    if (length == 0) return -1;
    int end = start + length;
    int s0 = end - d->max_sfx_key;
    if (s0 < start) s0 = start;
    int e0 = end;
    clamp_slice(wl, &s0, &e0);
    const uint8_t *seg = w + s0;
    int n = e0 - s0;
    if (n == 0) return -1; /* (Python: IndexError) */
    int32_t sp = d->sstart[seg[n - 1]];
    while (sp >= 0) {
        const AffEntry *e = &d->sent[sp];
        if (is_rev_subset(e, seg, n)) {
            int tmpl = length - e->appnd_len;
            if (!(tmpl < 0 || (tmpl == 0 && !d->fullstrip))) {
                int a = start, b = start + tmpl;
                clamp_slice(wl, &a, &b);
                if (stem_found(d, &sc, w, a, b, e) && sfx_allowed(d, e, ppfx, cclass, in_compound)) {
                    if (in_compound != IN_CPD_END || ppfx != NULL || !CONT_HAS(e, d->onlyincompound)) {
                        int32_t rv = sfx_checkword(c, e, w, wl, start, length, sfxopts, ppfx, cclass, needflag,
                                                   badflag);
                        if (rv >= 0) {
                            SET_SFX(c, sp);
                            return rv;
                        }
                    }
                }
            }
            sp = e->nexteq;
        } else {
            sp = e->nextne;
        }
    }
    return -1;
}

/* SfxEntry::check_twosfx */
static int32_t
sfx_check_twosfx(Ctx *c, const AffEntry *se, const uint8_t *w, int wl, int start, int length, int optflags,
                 const AffEntry *ppfx, flag_t needflag)
{
    HunDict *d = c->d;
    if ((optflags & AE_XPRODUCT) && !(se->opts & AE_XPRODUCT)) return -1;
    int tmpl = length - se->appnd_len;
    if ((tmpl > 0 || (tmpl == 0 && d->fullstrip)) && tmpl + se->strip_len >= se->numconds) {
        int a = start, b = start + tmpl;
        clamp_slice(wl, &a, &b);
        AMark m = amark(&c->ar);
        uint8_t *tmp = bcat(c, w + a, b - a, se->strip, se->strip_len);
        int tn = b - a + se->strip_len;
        tmpl += se->strip_len;
        int32_t he = -1;
        if (sfx_test_condition(se, tmp, tn, tmpl)) {
            if (ppfx != NULL) {
                if (se->ncont && CONT_HAS(se, ppfx->aflag))
                    he = suffix_check(c, tmp, tn, 0, tmpl, 0, NULL, se->aflag, needflag, IN_CPD_NOT);
                else
                    he = suffix_check(c, tmp, tn, 0, tmpl, optflags, ppfx, se->aflag, needflag, IN_CPD_NOT);
            } else {
                he = suffix_check(c, tmp, tn, 0, tmpl, 0, NULL, se->aflag, needflag, IN_CPD_NOT);
            }
        }
        arelease(&c->ar, m);
        return he;
    }
    return -1;
}

#define IS_CONTCLASS(d, f) ((d)->contclasses[(f) >> 3] & (1 << ((f) & 7)))

static int32_t
suffix_check_twosfx(Ctx *c, const uint8_t *w, int wl, int start, int length, int sfxopts, const AffEntry *ppfx,
                    flag_t needflag)
{
    HunDict *d = c->d;
    for (int32_t se = d->sstart[0]; se >= 0; se = d->sent[se].next) {
        const AffEntry *e = &d->sent[se];
        if (IS_CONTCLASS(d, e->aflag)) {
            int32_t rv = sfx_check_twosfx(c, e, w, wl, start, length, sfxopts, ppfx, needflag);
            if (rv >= 0) return rv;
        }
    }
    if (length == 0) return -1;
    int end = start + length;
    int s0 = end - d->max_sfx_key;
    if (s0 < start) s0 = start;
    int e0 = end;
    clamp_slice(wl, &s0, &e0);
    const uint8_t *seg = w + s0;
    int n = e0 - s0;
    if (n == 0) return -1;
    int32_t sp = d->sstart[seg[n - 1]];
    while (sp >= 0) {
        const AffEntry *e = &d->sent[sp];
        if (is_rev_subset(e, seg, n)) {
            if (IS_CONTCLASS(d, e->aflag)) {
                int32_t rv = sfx_check_twosfx(c, e, w, wl, start, length, sfxopts, ppfx, needflag);
                if (rv >= 0) return rv;
            }
            sp = e->nexteq;
        } else {
            sp = e->nextne;
        }
    }
    return -1;
}

static int32_t
affix_check(Ctx *c, const uint8_t *w, int wl, int start, int length, flag_t needflag, int in_compound)
{
    HunDict *d = c->d;
    int32_t rv = prefix_check(c, w, wl, start, length, in_compound, needflag);
    if (rv >= 0) return rv;
    rv = suffix_check(c, w, wl, start, length, 0, NULL, H_FLAG_NULL, needflag, in_compound);
    if (d->havecontclass) {
        SET_SFX(c, -1);
        SET_PFX(c, -1);
        if (rv >= 0) return rv;
        rv = suffix_check_twosfx(c, w, wl, start, length, 0, NULL, needflag);
        if (rv >= 0) return rv;
        rv = prefix_check_twosfx(c, w, wl, start, length, IN_CPD_NOT, needflag);
    }
    return rv;
}

/* ------------------------------------------------------------------------ */
/* compounding */

static int
candidate_check(Ctx *c, const uint8_t *w, int n)
{
    if (lookup(c->d, w, n) >= 0) return 1;
    return affix_check(c, w, n, 0, n, H_FLAG_NULL, IN_CPD_NOT) >= 0;
}

static int
cpdrep_check(Ctx *c, const uint8_t *in_word, int in_len, int wl)
{
    HunDict *d = c->d;
    if (wl < 2 || d->rep.n == 0) return 0;
    int a = 0, b = wl;
    clamp_slice(in_len, &a, &b);
    const uint8_t *word = in_word;
    int n = b;
    for (int k = 0; k < d->rep.n; k++) {
        RepEntry *re = &d->rep.v[k];
        BStr out = re->out[0];
        if (!out.n) continue;
        int lenp = re->pat.n;
        int r = py_find(word, n, re->pat.s, lenp, 0);
        while (r != -1) {
            AMark m = amark(&c->ar);
            int e2 = r + lenp;
            if (e2 > n) e2 = n;
            uint8_t *cand = bcat3(c, word, r, out.s, out.n, word + e2, n - e2);
            int ok = candidate_check(c, cand, r + out.n + n - e2);
            arelease(&c->ar, m);
            if (ok) return 1;
            r = py_find(word, n, re->pat.s, lenp, r + 1);
        }
    }
    return 0;
}

static int
cpdwordpair_check(Ctx *c, const uint8_t *word, int wlen, int wl)
{
    if (wl > 2) {
        int a = 0, b = wl;
        clamp_slice(wlen, &a, &b);
        int n = b;
        int utf8 = c->d->h_utf8;
        for (int i = 1; i < n; i++) {
            if (utf8 && (word[i] & 0xc0) == 0x80) continue;
            AMark m = amark(&c->ar);
            uint8_t *cand = bcat3(c, word, i, (const uint8_t *)" ", 1, word + i, n - i);
            int ok = candidate_check(c, cand, n + 1);
            arelease(&c->ar, m);
            if (ok) return 1;
        }
    }
    return 0;
}

static int
cpdpat_check(Ctx *c, const uint8_t *word, int wlen, int pos, int32_t r1, int32_t r2)
{
    HunDict *d = c->d;
    for (int k = 0; k < d->ncheckcpd; k++) {
        CpdPat *cp = &d->checkcpd[k];
        int dot = memchr(cp->pat2.s, '.', (size_t)cp->pat2.n) != NULL;
        if (!is_subset(cp->pat2.s, cp->pat2.n, dot, word, wlen, pos)) continue;
        if (!(r1 < 0 || cp->cond == H_FLAG_NULL || EHAS(d, r1, cp->cond))) continue;
        if (!(r2 < 0 || cp->cond2 == H_FLAG_NULL || EHAS(d, r2, cp->cond2))) continue;
        if (cp->pat.n == 0) return 1;
        if (cp->pat.s[0] == '0') {
            int rl = EWLEN(d, r1);
            if (rl <= pos && pos <= wlen && memcmp(word + pos - rl, EWORD(d, r1), (size_t)rl) == 0) return 1;
        } else {
            int pl = cp->pat.n;
            if (pl <= pos && pos <= wlen && memcmp(word + pos - pl, cp->pat.s, (size_t)pl) == 0) return 1;
        }
    }
    return 0;
}

static int
cpdcase_check(Ctx *c, const uint8_t *word, int wlen, int pos)
{
    HunDict *d = c->d;
    if (d->h_utf8) {
        int p = pos - 1;
        while (p > 0 && (word[p] & 0xc0) == 0x80) p--;
        if (p < 0) p = 0;
        /* the first two units of u8_u16(word[p:]) only depend on its first 6 bytes */
        int rest = wlen - p;
        if (rest > 6) rest = 6;
        uint16_t pair[8];
        int nu = rest > 0 ? u8_u16_raw(word + p, rest, pair) : 0;
        int a = nu > 1 ? pair[1] : 0;
        int b = nu > 0 ? pair[0] : 0;
        return (d->upper[a] == a || d->upper[b] == b) && a != '-' && b != '-';
    }
    int a = pos >= 1 && pos - 1 < wlen ? word[pos - 1] : 0;
    int b = pos >= 0 && pos < wlen ? word[pos] : 0;
    return (d->lower[a] != a || d->lower[b] != b) && a != '-' && b != '-';
}

static int
get_syllable(Ctx *c, const uint8_t *w, int n)
{
    HunDict *d = c->d;
    if (d->cpdmaxsyllable == 0) return 0;
    if (!d->h_utf8) {
        int k = 0;
        for (int i = 0; i < n; i++)
            for (int j = 0; j < d->ncpdvowels; j++)
                if (d->cpdvowels[j] == w[i]) { k++; break; }
        return k;
    }
    if (!d->ncpdvowels) return 0;
    AMark m = amark(&c->ar);
    uint16_t *u;
    int nu = u8_u16(c, w, n, &u);
    int k = 0;
    for (int i = 0; i < nu; i++)
        for (int j = 0; j < d->ncpdvowels; j++)
            if (d->cpdvowels[j] == u[i]) { k++; break; }
    arelease(&c->ar, m);
    return k;
}

static void
setcminmax(HunDict *d, const uint8_t *w, int wn, int length, int *cmin, int *cmax)
{
#define WB(k) ((k) >= 0 && (k) < wn ? w[k] : 0)
    if (d->h_utf8) {
        int cpdmin = d->cpdmin;
        int mn = 0;
        for (int i = 0; i < cpdmin && mn < length; i++) {
            mn++;
            while (mn < length && (WB(mn) & 0xc0) == 0x80) mn++;
        }
        int mx = length;
        for (int i = 0; i < cpdmin - 1 && mx >= 0; i++) {
            mx--;
            while (mx >= 0 && (WB(mx) & 0xc0) == 0x80) mx--;
        }
        *cmin = mn;
        *cmax = mx;
        return;
    }
#undef WB
    *cmin = d->cpdmin;
    *cmax = length - d->cpdmin + 1;
}

/* AffixMgr::defcpd_check: words is the array of the compound's words (NULL: None) */
static int
defcpd_check(HunDict *d, int32_t **words_p, int32_t *def, int wnum, int32_t rv, int all)
{
    int w = 0;
    int32_t *words = *words_p;
    if (words == NULL) {
        w = 1;
        words = def;
    }
    if (words == NULL) {
        *words_p = NULL;
        return 0;
    }
    if (wnum < 0 || wnum >= 100) return 0; /* (Python: IndexError; does not occur) */
    words[wnum] = rv;
    if (ENFLAGS(d, rv) == 0) {
        words[wnum] = -1;
        *words_p = w ? NULL : words;
        return 0;
    }
    int ok = 0;
    for (int r = 0; r < d->ndefcpd && !ok; r++) {
        FlagRule *rule = &d->defcpd[r];
        for (int k = 0; k < rule->n; k++) {
            flag_t f = rule->f[k];
            if (f != '*' && f != '?' && EHAS(d, rv, f)) {
                ok = 1;
                break;
            }
        }
    }
    if (!ok) {
        words[wnum] = -1;
        *words_p = w ? NULL : words;
        return 0;
    }
    for (int r = 0; r < d->ndefcpd; r++) {
        FlagRule *rr = &d->defcpd[r];
        const flag_t *rule = rr->f;
        int rlen = rr->n;
        int btinfo[64][3];
        int bt = 0, pp = 0, wp = 0, ok2 = 1;
        ok = 1;
        btinfo[0][0] = btinfo[0][1] = btinfo[0][2] = 0;
        for (;;) {
            while (pp < rlen && wp <= wnum) {
                if (pp + 1 < rlen && (rule[pp + 1] == '*' || rule[pp + 1] == '?')) {
                    int wend = rule[pp + 1] == '?' ? wp : wnum;
                    ok2 = 1;
                    pp += 2;
                    btinfo[bt][0] = pp;
                    btinfo[bt][1] = wp;
                    while (wp <= wend) {
                        int32_t ww = words[wp];
                        if (ww < 0 || ENFLAGS(d, ww) == 0 || !EHAS(d, ww, rule[pp - 2])) {
                            ok2 = 0;
                            break;
                        }
                        wp++;
                    }
                    if (wp <= wnum) ok2 = 0;
                    btinfo[bt][2] = wp - btinfo[bt][1];
                    if (btinfo[bt][2] > 0) {
                        bt++;
                        if (bt >= 63) bt = 63; /* (rules have less than 63 * or ? items) */
                        btinfo[bt][0] = btinfo[bt][1] = btinfo[bt][2] = 0;
                    }
                    if (ok2) break;
                } else {
                    ok2 = 1;
                    int32_t ww = words[wp];
                    if (ww < 0 || ENFLAGS(d, ww) == 0 || !EHAS(d, ww, rule[pp])) {
                        ok = 0;
                        break;
                    }
                    pp++;
                    wp++;
                    if (rlen == pp && !(wp > wnum)) ok = 0;
                }
            }
            if (ok && ok2) {
                int q = pp;
                while (rlen > q && q + 1 < rlen && (rule[q + 1] == '*' || rule[q + 1] == '?')) q += 2;
                if (rlen <= q) {
                    *words_p = words;
                    return 1;
                }
            }
            if (bt) {
                for (;;) {
                    ok = 1;
                    btinfo[bt - 1][2] -= 1;
                    pp = btinfo[bt - 1][0];
                    wp = btinfo[bt - 1][1] + btinfo[bt - 1][2];
                    if (btinfo[bt - 1][2] < 0) {
                        bt--;
                        if (bt) continue;
                    }
                    break;
                }
            }
            if (!bt) break;
        }
        if (ok && ok2 && (!all || rlen <= pp)) {
            *words_p = words;
            return 1;
        }
        while (ok && ok2 && rlen > pp && pp + 1 < rlen && (rule[pp + 1] == '*' || rule[pp + 1] == '?')) pp += 2;
        if (ok && ok2 && rlen <= pp) {
            *words_p = words;
            return 1;
        }
    }
    words[wnum] = -1;
    *words_p = w ? NULL : words;
    return 0;
}

/* The memo of the affix checks that compound_check makes during a suggest()
 * call: the candidates of the suggestions share most of their compound
 * parts. prefix_check, suffix_check, suffix_check_twosfx and affix_check
 * of the rest of a word (start + length == the word length; the checks only
 * read that part) with the top-level options are functions of that string
 * and the flags, with the side effects on the pfx and sfx of the state
 * (replayed on a hit). */
enum { MEMO_PFX, MEMO_SFX, MEMO_SFX2, MEMO_AFFIX, MEMO_RELAXED };

typedef struct {
    uint64_t h;
    const uint8_t *key;
    int keylen;
    uint32_t tag;
    int32_t rv, pfx, sfx;
    uint8_t pfx_set, sfx_set;
} MemoEntry;

typedef struct Memo {
    MemoEntry *v;
    uint32_t n, cap;   /* cap: a power of 2 */
} Memo;

#ifndef MEMO_MAX
#define MEMO_MAX (1 << 15)  /* the maximum number of entries (the table has at most 2 MEMO_MAX slots) */
#endif

static void
memo_free(Memo *m)
{
    if (m == NULL) return;
    free(m->v);
    free(m);
}

static int relaxed_accept(Ctx *c, const uint8_t *x, int n);

static int32_t
memo_direct(Ctx *c, int kind, const uint8_t *w, int wl, int start, flag_t needflag, int in_compound)
{
    switch (kind) {
    case MEMO_RELAXED:
        return relaxed_accept(c, w + start, wl - start);
    case MEMO_PFX:
        return prefix_check(c, w, wl, start, wl - start, in_compound, needflag);
    case MEMO_SFX:
        return suffix_check(c, w, wl, start, wl - start, 0, NULL, H_FLAG_NULL, needflag, in_compound);
    case MEMO_SFX2:
        return suffix_check_twosfx(c, w, wl, start, wl - start, 0, NULL, needflag);
    default:
        return affix_check(c, w, wl, start, wl - start, needflag, in_compound);
    }
}

static int32_t
memo_check(Ctx *c, int kind, const uint8_t *w, int wl, int start, flag_t needflag, int in_compound)
{
    Memo *m = c->memo;
    if (m == NULL || start < 0 || start > wl) return memo_direct(c, kind, w, wl, start, needflag, in_compound);
    const uint8_t *key = w + start;
    int kn = wl - start;
    uint32_t tag = (uint32_t)kind | ((uint32_t)needflag << 8) | ((uint32_t)in_compound << 24);
    uint64_t h = whash(key, kn) ^ ((uint64_t)tag * 0x9E3779B97F4A7C15ULL);
    if (m->n * 2 + 2 > m->cap && m->n < MEMO_MAX) {
        uint32_t nc = m->cap ? m->cap * 2 : 4096;
        MemoEntry *nv = calloc(nc, sizeof(MemoEntry));
        if (nv == NULL) longjmp(c->jb, 1);
        for (uint32_t i = 0; i < m->cap; i++) {
            if (m->v[i].key == NULL) continue;
            uint32_t j = (uint32_t)m->v[i].h & (nc - 1);
            while (nv[j].key != NULL) j = (j + 1) & (nc - 1);
            nv[j] = m->v[i];
        }
        free(m->v);
        m->v = nv;
        m->cap = nc;
    }
    uint32_t mask = m->cap - 1;
    uint32_t j = (uint32_t)h & mask;
    while (m->v[j].key != NULL) {
        MemoEntry *e = &m->v[j];
        if (e->h == h && e->tag == tag && e->keylen == kn && memcmp(e->key, key, (size_t)kn) == 0) {
            if (e->pfx_set) SET_PFX(c, e->pfx);
            if (e->sfx_set) SET_SFX(c, e->sfx);
            return e->rv;
        }
        j = (j + 1) & mask;
    }
    unsigned gp = c->pfx_gen, gs = c->sfx_gen;
    int32_t rv = memo_direct(c, kind, w, wl, start, needflag, in_compound);
    if (m->n >= MEMO_MAX) return rv; /* (full: the first entries are the parts of the word, they are reused) */
    /* (the table did not change: the checks do not use the memo) */
    MemoEntry *e = &m->v[j];
    uint8_t *k = aalloc(&c->keep, (size_t)kn + 1);
    if (kn) memcpy(k, key, (size_t)kn);
    e->h = h;
    e->key = k;
    e->keylen = kn;
    e->tag = tag;
    e->rv = rv;
    e->pfx_set = c->pfx_gen != gp;
    e->sfx_set = c->sfx_gen != gs;
    e->pfx = c->pfx;
    e->sfx = c->sfx;
    m->n++;
    return rv;
}

/* a growable byte buffer in the temporary arena (compound_check's st) */
typedef struct {
    uint8_t *p;
    int n, cap;
} TBuf;

static void
tb_reserve(Ctx *c, TBuf *b, int need)
{
    if (need <= b->cap) return;
    int nc = b->cap * 2 + 16;
    if (nc < need) nc = need;
    uint8_t *np = aalloc(&c->ar, (size_t)nc + 1);
    if (b->n) memcpy(np, b->p, (size_t)b->n);
    b->p = np;
    b->cap = nc;
}

static inline void
tb_truncate(TBuf *b, int i)
{
    if (i < b->n) b->n = i < 0 ? 0 : i;
}

static void
tb_append(Ctx *c, TBuf *b, const uint8_t *s, int n)
{
    tb_reserve(c, b, b->n + n);
    if (n) memcpy(b->p + b->n, s, (size_t)n);
    b->n += n;
}

static int deadline_passed(Ctx *c);

/* AffixMgr::compound_check; info: NO_INFO or the spell info */
static int32_t
compound_check(Ctx *c, const uint8_t *word, int wlen, int wordnum, int numsyllable, int maxwordnum, int wnum,
               int32_t *words, int32_t *rwords, int hu_mov_rule, int is_sug, int info)
{
    HunDict *d = c->d;
    if (is_sug && c->has_deadline && deadline_passed(c)) return -1;
    int utf8 = d->h_utf8;
    flag_t cf = d->compoundflag, cb = d->compoundbegin, cm = d->compoundmiddle, ce = d->compoundend;
    flag_t cff = d->compoundforbidflag, needaffix = d->needaffix, forbiddenword = d->a_forbidden;
    flag_t nosuggest = d->nosuggest;
    int defcpd = d->ndefcpd > 0;
    int ncheckcpd = d->ncheckcpd;
    CpdPat *checkcpd = d->checkcpd;
    int32_t rv = -1;
    int striple = 0, soldi = 0;
    int oldcmin = 0, oldcmax = 0, oldlen = 0;
    int checkedstriple = 0;
    int32_t *oldwords = words;
    int scpd = 0;
    int length = wlen;
    int cmin, cmax;
    AMark m0 = amark(&c->ar);
#define WB(k) ((k) >= 0 && (k) < wlen ? word[k] : 0)
#define FL_HAS(e, f) EHAS(d, e, f)
#define RETURN(x) do { int32_t r_ = (x); arelease(&c->ar, m0); return r_; } while (0)
    setcminmax(d, word, wlen, length, &cmin, &cmax);
    TBuf st = {NULL, 0, 0};
    tb_append(c, &st, word, wlen);
    int i = cmin;
    while (i < cmax) {
        if (utf8) {
            while ((((i >= 0 && i < st.n) ? st.p[i] : 0) & 0xc0) == 0x80) i++;
            if (i >= cmax) RETURN(-1);
        }
        words = oldwords;
        int onlycpdrule = words != NULL ? 1 : 0;
        for (;;) { /* onlycpdrule loop */
            int oldnumsyllable = numsyllable;
            int oldwordnum = wordnum;
            int checked_prefix = 0;
            for (;;) { /* simplified checkcompoundpattern loop */
                int exit_inner = 0;
                int32_t rv_first;
                const uint8_t *first;
                int fn;
                if (scpd > 0) {
                    while (scpd <= ncheckcpd) {
                        CpdPat *cp = &checkcpd[scpd - 1];
                        if (!(cp->pat3.n == 0 || i > wlen || i + cp->pat3.n > wlen || word[i] != cp->pat3.s[0]
                              || memcmp(word + i, cp->pat3.s, (size_t)cp->pat3.n) != 0))
                            break;
                        scpd++;
                    }
                    if (scpd > ncheckcpd) {
                        exit_inner = 1;
                        goto body_end;
                    }
                    {
                        CpdPat *cp = &checkcpd[scpd - 1];
                        tb_truncate(&st, i);
                        tb_append(c, &st, cp->pat.s, cp->pat.n);
                        soldi = i;
                        i += cp->pat.n;
                        tb_truncate(&st, i);
                        tb_append(c, &st, cp->pat2.s, cp->pat2.n);
                        tb_truncate(&st, i + cp->pat2.n);
                        {
                            int a = soldi + cp->pat3.n, b = wlen;
                            clamp_slice(wlen, &a, &b);
                            tb_append(c, &st, word + a, b - a);
                        }
                        oldlen = length;
                        length += cp->pat.n + cp->pat2.n - cp->pat3.n;
                        oldcmin = cmin;
                        oldcmax = cmax;
                        setcminmax(d, st.p, st.n, length, &cmin, &cmax);
                        cmax = length - d->cpdmin + 1;
                    }
                }
                if (i > st.n) RETURN(-1);
                /* (a copy: st changes) */
                first = bdup(c, st.p, i);
                fn = i;
                SET_SFX(c, -1);
                SET_PFX(c, -1);
                /* FIRST WORD */
                rv = lookup(d, first, fn);
                if (rv >= 0 && cff != H_FLAG_NULL && FL_HAS(rv, cff) && !hu_mov_rule) goto body_continue;
                while (rv >= 0 && !hu_mov_rule) {
                    if (needaffix != H_FLAG_NULL && FL_HAS(rv, needaffix)) {
                        rv = d->ent[rv].next;
                        continue;
                    }
                    int ok = ((cf != H_FLAG_NULL && words == NULL && !onlycpdrule && FL_HAS(rv, cf))
                              || (cb != H_FLAG_NULL && !wordnum && !onlycpdrule && FL_HAS(rv, cb))
                              || (cm != H_FLAG_NULL && wordnum && words == NULL && !onlycpdrule && FL_HAS(rv, cm)));
                    if (!ok && defcpd && onlycpdrule) {
                        if (words == NULL && !wordnum) ok = defcpd_check(d, &words, rwords, wnum, rv, 0);
                        if (!ok && words != NULL) ok = defcpd_check(d, &words, rwords, wnum, rv, 0);
                    }
                    if (!ok || (scpd != 0 && checkcpd[scpd - 1].cond != H_FLAG_NULL
                                && !FL_HAS(rv, checkcpd[scpd - 1].cond))) {
                        rv = d->ent[rv].next;
                        continue;
                    }
                    break;
                }
                if (rv < 0) {
                    if (onlycpdrule) {
                        exit_inner = 1;
                        goto body_end;
                    }
                    int in_cpd = hu_mov_rule ? IN_CPD_OTHER : IN_CPD_BEGIN;
                    if (cf != H_FLAG_NULL) {
                        rv = memo_check(c, MEMO_PFX, first, fn, 0, cf, in_cpd);
                        if (rv < 0) {
                            rv = memo_check(c, MEMO_SFX, first, fn, 0, cf, in_cpd);
                            if (rv < 0 && d->compoundmoresuffixes)
                                rv = memo_check(c, MEMO_SFX2, first, fn, 0, cf, 0);
                            if (rv >= 0 && !hu_mov_rule && c->sfx >= 0 && d->sent[c->sfx].ncont
                                && ((cff != H_FLAG_NULL && CONT_HAS(&d->sent[c->sfx], cff))
                                    || (ce != H_FLAG_NULL && CONT_HAS(&d->sent[c->sfx], ce))))
                                rv = -1;
                        }
                    }
                    if (rv >= 0) {
                        checked_prefix = 1;
                    } else {
                        if (wordnum == 0 && cb != H_FLAG_NULL) {
                            rv = memo_check(c, MEMO_SFX, first, fn, 0, cb, in_cpd);
                            if (rv < 0 && d->compoundmoresuffixes)
                                rv = memo_check(c, MEMO_SFX2, first, fn, 0, cb, 0);
                            if (rv < 0) rv = memo_check(c, MEMO_PFX, first, fn, 0, cb, in_cpd);
                        } else if (wordnum > 0 && cm != H_FLAG_NULL) {
                            rv = memo_check(c, MEMO_SFX, first, fn, 0, cm, in_cpd);
                            if (rv < 0 && d->compoundmoresuffixes)
                                rv = memo_check(c, MEMO_SFX2, first, fn, 0, cm, 0);
                            if (rv < 0) rv = memo_check(c, MEMO_PFX, first, fn, 0, cm, in_cpd);
                        }
                        if (rv >= 0) checked_prefix = 1;
                    }
                } else if (ENFLAGS(d, rv)
                           && (FL_HAS(rv, forbiddenword) || FL_HAS(rv, needaffix) || FL_HAS(rv, H_ONLYUPCASEFLAG)
                               || (is_sug && nosuggest != H_FLAG_NULL && FL_HAS(rv, nosuggest)))) {
                    exit_inner = 1;
                    goto body_end;
                }
                {
                    const AffEntry *pfx = c->pfx >= 0 ? &d->pent[c->pfx] : NULL;
                    const AffEntry *sfx = c->sfx >= 0 ? &d->sent[c->sfx] : NULL;
                    if (rv >= 0 && !hu_mov_rule
                        && ((pfx != NULL && CONT_HAS(pfx, cff)) || (sfx != NULL && CONT_HAS(sfx, cff))))
                        rv = -1;
                    if (rv >= 0 && !checked_prefix && ce != H_FLAG_NULL && !hu_mov_rule
                        && ((pfx != NULL && CONT_HAS(pfx, ce)) || (sfx != NULL && CONT_HAS(sfx, ce))))
                        rv = -1;
                    if (rv >= 0 && !checked_prefix && wordnum == 0 && cm != H_FLAG_NULL && !hu_mov_rule
                        && ((pfx != NULL && CONT_HAS(pfx, cm)) || (sfx != NULL && CONT_HAS(sfx, cm))))
                        rv = -1;
                }
                if (rv >= 0 && ENFLAGS(d, rv)
                    && (FL_HAS(rv, forbiddenword) || FL_HAS(rv, H_ONLYUPCASEFLAG)
                        || (is_sug && nosuggest != H_FLAG_NULL && FL_HAS(rv, nosuggest))))
                    RETURN(-1);
                if (rv >= 0 && d->compoundroot != H_FLAG_NULL && FL_HAS(rv, d->compoundroot)) wordnum++;
                {
                    int first_ok = 0;
                    if (rv >= 0) {
                        if ((checked_prefix || (words != NULL && words[wnum] >= 0)
                             || (cf != H_FLAG_NULL && FL_HAS(rv, cf))
                             || (oldwordnum == 0 && cb != H_FLAG_NULL && FL_HAS(rv, cb))
                             || (oldwordnum > 0 && cm != H_FLAG_NULL && FL_HAS(rv, cm)))
                            && (scpd == 0 || checkcpd[scpd - 1].cond == H_FLAG_NULL
                                || FL_HAS(rv, checkcpd[scpd - 1].cond))
                            && !((d->checkcompoundtriple && scpd == 0 && words == NULL && WB(i - 1) == WB(i)
                                  && ((i > 1 && WB(i - 1) == WB(i - 2)) || WB(i - 1) == WB(i + 1)))
                                 || (d->checkcompoundcase && scpd == 0 && words == NULL && i < wlen
                                     && cpdcase_check(c, word, wlen, i))))
                            first_ok = 1;
                    }
                    if (!first_ok) goto after_first;
                }
                /* NEXT WORD(S) */
                rv_first = rv;
                for (;;) { /* striple loop */
                    if (d->simplifiedtriple) {
                        if (striple) {
                            checkedstriple = 1;
                            i--;
                        } else if (i > 2 && i <= wlen && WB(i - 1) == WB(i - 2)) {
                            striple = 1;
                        }
                    }
                    {
                        int ra = i, rb = st.n;
                        clamp_slice(st.n, &ra, &rb);
                        rv = lookup(d, st.p + ra, rb - ra);
                    }
                    while (rv >= 0) {
                        if (needaffix != H_FLAG_NULL && FL_HAS(rv, needaffix)) {
                            rv = d->ent[rv].next;
                            continue;
                        }
                        int ok = ((cf != H_FLAG_NULL && words == NULL && FL_HAS(rv, cf))
                                  || (ce != H_FLAG_NULL && words == NULL && FL_HAS(rv, ce)));
                        if (!ok && defcpd && words != NULL) ok = defcpd_check(d, &words, NULL, wnum + 1, rv, 1);
                        if (!ok || (scpd != 0 && checkcpd[scpd - 1].cond2 != H_FLAG_NULL
                                    && !FL_HAS(rv, checkcpd[scpd - 1].cond2))) {
                            rv = d->ent[rv].next;
                            continue;
                        }
                        break;
                    }
                    if (rv >= 0 && d->forceucase != H_FLAG_NULL && FL_HAS(rv, d->forceucase)
                        && !(info != NO_INFO && (info & SPELL_ORIGCAP)))
                        rv = -1;
                    if (rv >= 0 && words != NULL && wnum + 1 < 100 && words[wnum + 1] >= 0) RETURN(rv_first);
                    {
                        int oldnumsyllable2 = numsyllable;
                        int oldwordnum2 = wordnum;
                        if (rv >= 0 && d->compoundroot != H_FLAG_NULL && FL_HAS(rv, d->compoundroot)) wordnum++;
                        if (rv >= 0 && ENFLAGS(d, rv)
                            && (FL_HAS(rv, forbiddenword) || FL_HAS(rv, H_ONLYUPCASEFLAG)
                                || (is_sug && nosuggest != H_FLAG_NULL && FL_HAS(rv, nosuggest))))
                            RETURN(-1);
                        if (rv >= 0
                            && ((cf != H_FLAG_NULL && FL_HAS(rv, cf)) || (ce != H_FLAG_NULL && FL_HAS(rv, ce)))
                            && ((d->cpdwordmax == -1 || wordnum + 1 < d->cpdwordmax)
                                || (d->cpdmaxsyllable != 0
                                    && numsyllable + get_syllable(c, EWORD(d, rv), EWLEN(d, rv))
                                       <= d->cpdmaxsyllable))
                            && (ncheckcpd == 0 || scpd != 0
                                || (i < wlen && !cpdpat_check(c, word, wlen, i, rv_first, rv)))
                            && (!d->checkcompounddup || rv != rv_first)
                            && (scpd == 0 || checkcpd[scpd - 1].cond2 == H_FLAG_NULL
                                || FL_HAS(rv, checkcpd[scpd - 1].cond2))) {
                            if ((d->checkcompoundrep && cpdrep_check(c, word, wlen, length))
                                || cpdwordpair_check(c, word, wlen, length))
                                RETURN(-1);
                            RETURN(rv_first);
                        }
                        numsyllable = oldnumsyllable2;
                        wordnum = oldwordnum2;
                        SET_SFX(c, -1);
                        rv = (cf != H_FLAG_NULL && !onlycpdrule && i < wlen)
                                 ? memo_check(c, MEMO_AFFIX, word, wlen, i, cf, IN_CPD_END) : -1;
                        if (rv < 0 && ce != H_FLAG_NULL && !onlycpdrule) {
                            SET_SFX(c, -1);
                            SET_PFX(c, -1);
                            if (i < wlen) rv = memo_check(c, MEMO_AFFIX, word, wlen, i, ce, IN_CPD_END);
                        }
                        if (rv < 0 && defcpd && words != NULL) {
                            if (i < wlen) rv = memo_check(c, MEMO_AFFIX, word, wlen, i, H_FLAG_NULL, IN_CPD_END);
                            if (rv >= 0) {
                                int ok = defcpd_check(d, &words, NULL, wnum + 1, rv, 1);
                                if (ok) RETURN(rv_first);
                            }
                            rv = -1;
                        }
                        if (rv >= 0 && !(scpd == 0 || checkcpd[scpd - 1].cond2 == H_FLAG_NULL
                                         || FL_HAS(rv, checkcpd[scpd - 1].cond2)))
                            rv = -1;
                        if (rv >= 0 && ncheckcpd && scpd == 0 && cpdpat_check(c, word, wlen, i, rv_first, rv))
                            rv = -1;
                        {
                            const AffEntry *pfx = c->pfx >= 0 ? &d->pent[c->pfx] : NULL;
                            const AffEntry *sfx = c->sfx >= 0 ? &d->sent[c->sfx] : NULL;
                            if (rv >= 0 && ((pfx != NULL && CONT_HAS(pfx, cff)) || (sfx != NULL && CONT_HAS(sfx, cff))))
                                rv = -1;
                        }
                        if (rv >= 0 && d->forceucase != H_FLAG_NULL && FL_HAS(rv, d->forceucase)
                            && !(info != NO_INFO && (info & SPELL_ORIGCAP)))
                            rv = -1;
                        if (rv >= 0 && ENFLAGS(d, rv)
                            && (FL_HAS(rv, forbiddenword) || FL_HAS(rv, H_ONLYUPCASEFLAG)
                                || (is_sug && nosuggest != H_FLAG_NULL && FL_HAS(rv, nosuggest))))
                            RETURN(-1);
                        if (rv >= 0 && d->compoundroot != H_FLAG_NULL && FL_HAS(rv, d->compoundroot)) wordnum++;
                        if (rv >= 0
                            && ((d->cpdwordmax == -1 || wordnum + 1 < d->cpdwordmax)
                                || (d->cpdmaxsyllable != 0 && numsyllable <= d->cpdmaxsyllable))
                            && (!d->checkcompounddup || rv != rv_first)) {
                            if ((d->checkcompoundrep && cpdrep_check(c, word, wlen, length))
                                || cpdwordpair_check(c, word, wlen, length))
                                RETURN(-1);
                            RETURN(rv_first);
                        }
                        numsyllable = oldnumsyllable2;
                        wordnum = oldwordnum2;
                        if (wordnum + 2 < maxwordnum) {
                            int ra = i, rb = st.n;
                            clamp_slice(st.n, &ra, &rb);
                            uint8_t *rest = bdup(c, st.p + ra, rb - ra);
                            rv = compound_check(c, rest, rb - ra, wordnum + 1, numsyllable, maxwordnum, wnum + 1,
                                                words, rwords, 0, is_sug, info);
                            if (rv >= 0 && ncheckcpd && i < wlen
                                && ((scpd == 0 && cpdpat_check(c, word, wlen, i, rv_first, rv))
                                    || (scpd != 0 && !cpdpat_check(c, word, wlen, i, rv_first, rv))))
                                rv = -1;
                        } else {
                            rv = -1;
                        }
                        if (rv >= 0) {
                            if (cpdwordpair_check(c, word, wlen, length)) RETURN(-1);
                            if (d->checkcompoundrep || forbiddenword != H_FLAG_NULL) {
                                if (d->checkcompoundrep && cpdrep_check(c, word, wlen, length)) RETURN(-1);
                                int rl = EWLEN(d, rv);
                                if (i < wlen && i + rl <= wlen && memcmp(word + i, EWORD(d, rv), (size_t)rl) == 0) {
                                    int n = i + rl;
                                    int na = 0, nb = n;
                                    clamp_slice(st.n, &na, &nb);
                                    uint8_t *stn = bdup(c, st.p, nb);
                                    int stnn = nb;
                                    if ((d->checkcompoundrep && cpdrep_check(c, stn, stnn, n))
                                        || cpdwordpair_check(c, stn, stnn, n))
                                        goto striple_check;
                                    if (forbiddenword != H_FLAG_NULL) {
                                        int32_t rv2 = lookup(d, word, wlen);
                                        if (rv2 < 0 && length <= wlen) rv2 = affix_check(c, word, wlen, 0, length, H_FLAG_NULL, IN_CPD_NOT);
                                        if (rv2 >= 0 && ENFLAGS(d, rv2) && FL_HAS(rv2, forbiddenword)
                                            && EWLEN(d, rv2) >= stnn
                                            && memcmp(EWORD(d, rv2), stn, (size_t)stnn) == 0)
                                            RETURN(-1);
                                    }
                                }
                            }
                            RETURN(rv_first);
                        }
                    }
                striple_check:
                    if (!(striple && !checkedstriple)) break;
                }
                if (checkedstriple) {
                    i++;
                    checkedstriple = 0;
                    striple = 0;
                }
            after_first:
                if (soldi != 0) {
                    i = soldi;
                    soldi = 0;
                    length = oldlen;
                    cmin = oldcmin;
                    cmax = oldcmax;
                }
                scpd++;
            body_continue:
            body_end:
                if (exit_inner) break;
                if (!(!onlycpdrule && d->simplifiedcpd && scpd <= ncheckcpd)) break;
            }
            scpd = 0;
            wordnum = oldwordnum;
            numsyllable = oldnumsyllable;
            if (soldi != 0) {
                i = soldi;
                st.n = 0;
                tb_append(c, &st, word, wlen);
                soldi = 0;
            }
            if (!(defcpd && oldwordnum == 0 && onlycpdrule < 1)) break;
            onlycpdrule++;
        }
        i++;
    }
    RETURN(-1);
#undef WB
#undef FL_HAS
#undef RETURN
}

/* ------------------------------------------------------------------------ */
/* RepList (ICONV/OCONV) */

/* RepList::find: the last pattern that word[i:] starts with (binary search) */
static int
rep_find(const RepTable *t, const uint8_t *w, int wn, int i)
{
    int p1 = 0, p2 = t->n - 1, ret = -1;
    while (p1 <= p2) {
        int m = (p1 + p2) >> 1;
        const BStr *pat = &t->v[m].pat;
        int segn = wn - i;
        if (segn > pat->n) segn = pat->n;
        if (segn < 0) segn = 0;
        /* compare seg = word[i:i+len(pat)] with pat (bytes ordering) */
        int k = segn < pat->n ? segn : pat->n;
        int cmp = k ? memcmp(w + i, pat->s, (size_t)k) : 0;
        if (cmp == 0) cmp = segn < pat->n ? -1 : (segn > pat->n ? 1 : 0);
        if (cmp < 0) p2 = m - 1;
        else if (cmp > 0) p1 = m + 1;
        else {
            ret = m;
            p1 = m + 1;
        }
    }
    return ret;
}

/* RepList::conv: the converted word (in the temporary arena), -1: no change */
static int
rep_conv(Ctx *c, const RepTable *t, const uint8_t *w, int n, const uint8_t **out)
{
    TBuf dest = {NULL, 0, 0};
    int change = 0;
    int i = 0;
    while (i < n) {
        int m = rep_find(t, w, n, i);
        if (m < 0) {
            tb_append(c, &dest, w + i, 1);
            i++;
            continue;
        }
        int atstart = i == 0;
        int rtype = atstart ? 1 : 0;
        if (n - i == t->v[m].pat.n) rtype = atstart ? 3 : 2;
        const BStr *outs = t->v[m].out;
        while (rtype && !outs[rtype].n) rtype = (rtype == 2 && !atstart) ? 0 : rtype - 1;
        const BStr *rep = &outs[rtype];
        if (!rep->n) {
            tb_append(c, &dest, w + i, 1);
            i++;
            continue;
        }
        tb_append(c, &dest, rep->s, rep->n);
        if (t->v[m].pat.n) i += t->v[m].pat.n - 1;
        change = 1;
        i++;
    }
    if (!change) return -1;
    tb_reserve(c, &dest, dest.n + 1);
    dest.p[dest.n] = 0;
    *out = dest.p;
    return dest.n;
}

/* ------------------------------------------------------------------------ */
/* HunspellImpl::checkword and spell */

static int
clean_ignore(Ctx *c, const uint8_t *w, int n, const uint8_t **out)
{
    if (!c->d->has_ignore_units) {
        *out = w;
        return n;
    }
    return remove_ignored(c, w, n, c->d->a_ignore, out);
}

static int32_t
checkword(Ctx *c, const uint8_t *w, int wn, int *info)
{
    HunDict *d = c->d;
    const uint8_t *word;
    int n = clean_ignore(c, w, wn, &word);
    if (!n) return -1;
    if (d->a_cpx) n = reverse_word(c, word, n, d->h_utf8, &word);
    int32_t he = lookup(d, word, n);
    if (he >= 0) {
        if (EHAS(d, he, d->a_forbidden)) {
            *info |= SPELL_FORBIDDEN;
            return -1;
        }
        flag_t needaffix = d->needaffix, oic = d->onlyincompound;
        while (he >= 0 && ENFLAGS(d, he)
               && ((needaffix != H_FLAG_NULL && EHAS(d, he, needaffix))
                   || (oic != H_FLAG_NULL && EHAS(d, he, oic))
                   || ((*info & SPELL_INITCAP) && EHAS(d, he, H_ONLYUPCASEFLAG))))
            he = d->ent[he].next;
    }
    if (he < 0) {
        he = affix_check(c, word, n, 0, n, H_FLAG_NULL, IN_CPD_NOT);
        if (he >= 0 && ((d->onlyincompound != H_FLAG_NULL && EHAS(d, he, d->onlyincompound))
                        || ((*info & SPELL_INITCAP) && EHAS(d, he, H_ONLYUPCASEFLAG))))
            he = -1;
        if (he >= 0) {
            if (EHAS(d, he, d->a_forbidden)) {
                *info |= SPELL_FORBIDDEN;
                return -1;
            }
        } else if (d->is_compound) {
            int32_t rwords[100];
            for (int k = 0; k < 100; k++) rwords[k] = -1;
            he = compound_check(c, word, n, 0, 0, 100, 0, NULL, rwords, 0, 0, *info);
            if (he >= 0) *info |= SPELL_COMPOUND;
        }
    }
    return he;
}

static int
is_keepcase(HunDict *d, int32_t rv)
{
    return d->keepcase != H_FLAG_NULL && EHAS(d, rv, d->keepcase);
}

static int32_t
spellsharps(Ctx *c, const uint8_t *base, int bn, int n_pos, int n, int repnum, int *info)
{
    HunDict *d = c->d;
    int pos = py_find(base, bn, (const uint8_t *)"ss", 2, n_pos);
    if (pos != -1 && n < H_MAXSHARPS) {
        const uint8_t *sharp = d->h_utf8 ? (const uint8_t *)"\xc3\x9f" : (const uint8_t *)"\xdf";
        int sl = d->h_utf8 ? 2 : 1;
        AMark m = amark(&c->ar);
        uint8_t *nb = bcat3(c, base, pos, sharp, sl, base + pos + 2, bn - pos - 2);
        int32_t h = spellsharps(c, nb, bn - 2 + sl, pos + sl, n + 1, repnum + 1, info);
        arelease(&c->ar, m);
        if (h >= 0) return h;
        h = spellsharps(c, base, bn, pos + 2, n + 1, repnum, info);
        if (h >= 0) return h;
    } else if (repnum > 0) {
        AMark m = amark(&c->ar);
        int32_t h = checkword(c, base, bn, info);
        arelease(&c->ar, m);
        return h;
    }
    return -1;
}

/* _cleanword2: scw (bytes), its units, the captype, abbv */
typedef struct {
    const uint8_t *w;
    int n;
    uint16_t *u;
    int nu;
} WordU;

static int
cleanword2(Ctx *c, const uint8_t *src, int sn, WordU *out, int *abbv)
{
    HunDict *d = c->d;
    const uint8_t *w2;
    int n2 = clean_ignore(c, src, sn, &w2);
    int q = 0, nl = n2;
    while (q < n2 && w2[q] == ' ') {
        q++;
        nl--;
    }
    *abbv = 0;
    while (nl > 0 && w2[q + nl - 1] == '.') {
        nl--;
        (*abbv)++;
    }
    if (nl <= 0) {
        out->w = (const uint8_t *)"";
        out->n = 0;
        out->u = NULL;
        out->nu = 0;
        return H_NOCAP;
    }
    out->w = bdup(c, w2 + q, nl);
    out->n = nl;
    out->nu = to_units(c, out->w, nl, d->a_utf8, &out->u);
    return captype_units(d, out->u, out->nu);
}

/* _mkallsmall2: lowercase units and their bytes */
static void
mkallsmall2(Ctx *c, WordU *x)
{
    uint16_t *u = udup(c, x->u, x->nu);
    u_lower(c->d, u, x->nu);
    x->u = u;
    uint8_t *b;
    x->n = from_units(c, u, x->nu, c->d->a_utf8, &b);
    x->w = b;
}

static void
mkinitcap2(Ctx *c, WordU *x)
{
    uint16_t *u = udup(c, x->u, x->nu);
    if (x->nu) u[0] = c->d->upper[u[0]];
    x->u = u;
    uint8_t *b;
    x->n = from_units(c, u, x->nu, c->d->a_utf8, &b);
    x->w = b;
}

typedef struct CStack {
    const uint8_t *w;
    int n;
    struct CStack *prev;
} CStack;

static int spell_internal(Ctx *c, const uint8_t *word, int wn, CStack *stack);

static int
spell_rec(Ctx *c, const uint8_t *word, int wn, CStack *stack)
{
    for (CStack *s = stack; s != NULL; s = s->prev)
        if (s->n == wn && memcmp(s->w, word, (size_t)wn) == 0) return 0;
    CStack top = {word, wn, stack};
    AMark m = amark(&c->ar);
    int r = spell_internal(c, word, wn, &top);
    arelease(&c->ar, m);
    return r;
}

/* bytes.count (non-overlapping, non-empty pattern) */
static int
py_count(const uint8_t *h, int hn, const uint8_t *p, int pn)
{
    if (pn == 0) return hn + 1;
    int k = 0, i = 0;
    for (;;) {
        int f = py_find(h, hn, p, pn, i);
        if (f < 0) return k;
        k++;
        i = f + pn;
    }
}

static int
spell_internal(Ctx *c, const uint8_t *word, int wn, CStack *stack)
{
    HunDict *d = c->d;
    int info = 0;
    if (wn == 7 && memcmp(word, "<?xml?>", 7) == 0) return 1;
    if (wn >= (d->h_utf8 ? H_MAXWORDUTF8LEN : H_MAXWORDLEN)) return 0;
    if (d->iconv.n >= 0) {
        const uint8_t *cv;
        int cn = rep_conv(c, &d->iconv, word, wn, &cv);
        if (cn >= 0) {
            word = cv;
            wn = cn;
        }
    }
    WordU s;
    int abbv;
    int captype = cleanword2(c, word, wn, &s, &abbv);
    if (!s.n) return 1;
    {
        int nstate = 0, i = 0;
        while (i < s.n) {
            int ch = s.w[i];
            if (ch >= '0' && ch <= '9') {
                nstate = 1;
            } else if (ch == ',' || ch == '.' || ch == '-') {
                if (nstate == 2 || i == 0) break;
                nstate = 2;
            } else {
                break;
            }
            i++;
        }
        if (i == s.n && nstate == 1) return 1;
    }
    int32_t rv = -1;
    if (captype == H_HUHCAP || captype == H_HUHINITCAP || captype == H_NOCAP) {
        if (captype != H_NOCAP) info |= SPELL_ORIGCAP;
        rv = checkword(c, s.w, s.n, &info);
        if (abbv && rv < 0) rv = checkword(c, bcat(c, s.w, s.n, (const uint8_t *)".", 1), s.n + 1, &info);
    } else {
        int done = 0;
        if (captype == H_ALLCAP) {
            info |= SPELL_ORIGCAP;
            rv = checkword(c, s.w, s.n, &info);
            if (rv >= 0) done = 1;
            if (!done && abbv) {
                rv = checkword(c, bcat(c, s.w, s.n, (const uint8_t *)".", 1), s.n + 1, &info);
                if (rv >= 0) done = 1;
            }
            if (!done) {
                int apos = py_find(s.w, s.n, (const uint8_t *)"'", 1, 0);
                if (apos != -1) {
                    mkallsmall2(c, &s);
                    if (apos < s.n - 1) {
                        const uint8_t *part1 = s.w;
                        int p1n = apos + 1;
                        const uint8_t *part2 = s.w + apos + 1;
                        int p2n = s.n - apos - 1;
                        if (d->h_utf8) {
                            WordU p1, p2;
                            p1.nu = u8_u16(c, part1, p1n, &p1.u);
                            p2.nu = u8_u16(c, part2, p2n, &p2.u);
                            mkinitcap2(c, &p2);
                            uint8_t *nw = bcat(c, part1, p1n, p2.w, p2.n);
                            uint16_t *nu = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)p1.nu + p2.nu + 1));
                            memcpy(nu, p1.u, sizeof(uint16_t) * p1.nu);
                            memcpy(nu + p1.nu, p2.u, sizeof(uint16_t) * p2.nu);
                            s.w = nw;
                            s.n = p1n + p2.n;
                            s.u = nu;
                            s.nu = p1.nu + p2.nu;
                            rv = checkword(c, s.w, s.n, &info);
                            if (rv >= 0) done = 1;
                        } else {
                            WordU p2;
                            p2.nu = to_units(c, part2, p2n, d->a_utf8, &p2.u);
                            mkinitcap2(c, &p2);
                            uint8_t *nw = bcat(c, part1, p1n, p2.w, p2.n);
                            s.w = nw;
                            s.n = p1n + p2.n;
                            rv = checkword(c, s.w, s.n, &info);
                            if (rv >= 0) done = 1;
                        }
                        if (!done) {
                            mkinitcap2(c, &s);
                            rv = checkword(c, s.w, s.n, &info);
                            if (rv >= 0) done = 1;
                        }
                    }
                }
            }
            if (!done && d->checksharps && py_find(s.w, s.n, (const uint8_t *)"SS", 2, 0) != -1) {
                mkallsmall2(c, &s);
                const uint8_t *u8b = s.w;
                int u8n = s.n;
                rv = spellsharps(c, u8b, u8n, 0, 0, 0, &info);
                if (rv < 0) {
                    mkinitcap2(c, &s);
                    rv = spellsharps(c, s.w, s.n, 0, 0, 0, &info);
                }
                if (abbv && rv < 0) {
                    u8b = bcat(c, u8b, u8n, (const uint8_t *)".", 1);
                    u8n++;
                    rv = spellsharps(c, u8b, u8n, 0, 0, 0, &info);
                    if (rv < 0) {
                        u8b = bcat(c, s.w, s.n, (const uint8_t *)".", 1);
                        u8n = s.n + 1;
                        rv = spellsharps(c, u8b, u8n, 0, 0, 0, &info);
                    }
                }
                if (rv >= 0) done = 1;
            }
        }
        if (!done) {
            int idot = d->h_utf8 && s.n >= 2 && s.w[0] == 0xc4 && s.w[1] == 0xb0;
            info |= SPELL_ORIGCAP;
            if (captype == H_ALLCAP) {
                mkallsmall2(c, &s);
                mkinitcap2(c, &s);
                if (idot) {
                    uint8_t *nw = bcat(c, (const uint8_t *)"\xc4\xb0", 2, s.w + 1, s.n - 1);
                    s.w = nw;
                    s.n = s.n + 1;
                }
            }
            if (captype == H_INITCAP) info |= SPELL_INITCAP;
            rv = checkword(c, s.w, s.n, &info);
            if (captype == H_INITCAP) info &= ~SPELL_INITCAP;
            if (info & SPELL_FORBIDDEN) {
                rv = -1;
            } else {
                if (rv >= 0 && is_keepcase(d, rv) && captype == H_ALLCAP) rv = -1;
                if (!(rv >= 0 || (idot && d->h_langnum != H_LANG_az && d->h_langnum != H_LANG_tr
                                  && d->h_langnum != H_LANG_crh))) {
                    mkallsmall2(c, &s);
                    const uint8_t *u8b = s.w;
                    int u8n = s.n;
                    mkinitcap2(c, &s);
                    rv = checkword(c, u8b, u8n, &info);
                    int finished = 0;
                    if (abbv && rv < 0) {
                        u8b = bcat(c, u8b, u8n, (const uint8_t *)".", 1);
                        u8n++;
                        rv = checkword(c, u8b, u8n, &info);
                        if (rv < 0) {
                            u8b = bcat(c, s.w, s.n, (const uint8_t *)".", 1);
                            u8n = s.n + 1;
                            if (captype == H_INITCAP) info |= SPELL_INITCAP;
                            rv = checkword(c, u8b, u8n, &info);
                            if (captype == H_INITCAP) info &= ~SPELL_INITCAP;
                            if (rv >= 0 && is_keepcase(d, rv) && captype == H_ALLCAP) rv = -1;
                            finished = 1;
                        }
                    }
                    if (!finished) {
                        int has_sharp = d->h_utf8 ? py_find(u8b, u8n, (const uint8_t *)"\xc3\x9f", 2, 0) != -1
                                                  : memchr(u8b, 0xdf, (size_t)u8n) != NULL;
                        if (rv >= 0 && is_keepcase(d, rv) && (captype == H_ALLCAP || !(d->checksharps && has_sharp)))
                            rv = -1;
                    }
                }
            }
        }
    }
    if (rv >= 0) {
        if (d->warn != H_FLAG_NULL && EHAS(d, rv, d->warn)) return !d->forbidwarn;
        return 1;
    }
    /* recursive breaking at break points */
    if (d->nwordbreak && !(info & SPELL_FORBIDDEN)) {
        const uint8_t *scw = s.w;
        int wl = s.n;
        int nbr = 0;
        for (int k = 0; k < d->nwordbreak; k++)
            if (d->wordbreak[k].n) nbr += py_count(scw, wl, d->wordbreak[k].s, d->wordbreak[k].n);
        if (nbr >= 10) return 0;
        for (int k = 0; k < d->nwordbreak; k++) {
            const uint8_t *j = d->wordbreak[k].s;
            int plen = d->wordbreak[k].n;
            if (plen == 1 || plen > wl || plen == 0) continue;
            if (j[0] == '^' && memcmp(scw, j + 1, (size_t)plen - 1) == 0
                && spell_rec(c, scw + plen - 1, wl - plen + 1, stack))
                return 1;
            if (j[plen - 1] == '$' && memcmp(scw + wl - plen + 1, j, (size_t)plen - 1) == 0) {
                if (spell_rec(c, scw, wl - plen + 1, stack)) return 1;
            }
        }
        for (int k = 0; k < d->nwordbreak; k++) {
            const uint8_t *j = d->wordbreak[k].s;
            int plen = d->wordbreak[k].n;
            int found = py_find(scw, wl, j, plen, 0);
            if (0 < found && found < wl - plen) {
                int found2 = py_find(scw, wl, j, plen, found + 1);
                if (0 < found2 && found2 < wl - plen) found = found2;
                if (!spell_rec(c, scw + found + plen, wl - found - plen, stack)) continue;
                if (spell_rec(c, scw, found, stack)) return 1;
            }
        }
        for (int k = 0; k < d->nwordbreak; k++) {
            const uint8_t *j = d->wordbreak[k].s;
            int plen = d->wordbreak[k].n;
            int found = py_find(scw, wl, j, plen, 0);
            if (0 < found && found < wl - plen) {
                if (!spell_rec(c, scw + found + plen, wl - found - plen, stack)) continue;
                if (spell_rec(c, scw, found, stack)) return 1;
            }
        }
    }
    return 0;
}

/* ------------------------------------------------------------------------ */
/* loading (HashMgr::load_tables, add_word, add_hidden_capitalized_word) */

/* _atoi: the value (saturated) and its low 16 bits (exact) */
static long long
h_atoi(const uint8_t *s, int n, unsigned *low16)
{
    int i = 0;
    while (i < n && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r' || s[i] == '\f' || s[i] == '\v'))
        i++;
    int neg = 0;
    if (i < n && (s[i] == '+' || s[i] == '-')) {
        neg = s[i] == '-';
        i++;
    }
    if (i >= n || s[i] < '0' || s[i] > '9') {
        if (low16) *low16 = 0;
        return 0;
    }
    long long v = 0;
    uint64_t wrap = 0;
    while (i < n && s[i] >= '0' && s[i] <= '9') {
        wrap = wrap * 10 + (uint64_t)(s[i] - '0');
        if (v < (1LL << 60)) v = v * 10 + (s[i] - '0');
        i++;
    }
    if (neg) {
        v = -v;
        wrap = (uint64_t)0 - wrap;
    }
    if (low16) *low16 = (unsigned)(wrap & 0xffff);
    return v;
}

/* decode_flags into out (room for n entries) */
static int
decode_flags(HunDict *d, const uint8_t *b, int n, flag_t *out)
{
    if (n == 0) return 0;
    switch (d->flag_mode) {
    case H_FLAG_LONG: {
        int k = n >> 1;
        for (int i = 0; i < k; i++) out[i] = (flag_t)((b[2 * i] << 8) | b[2 * i + 1]);
        return k;
    }
    case H_FLAG_NUM: {
        int k = 0, st = 0;
        for (int i = 0; i <= n; i++) {
            if (i == n || b[i] == ',') {
                unsigned lo;
                h_atoi(b + st, i - st, &lo);
                out[k++] = (flag_t)lo;
                st = i + 1;
            }
        }
        return k;
    }
    case H_FLAG_UNI: {
        uint16_t *u = (uint16_t *)out;
        return u8_u16_raw(b, n, u);
    }
    default:
        for (int i = 0; i < n; i++) out[i] = b[i];
        return n;
    }
}

typedef struct {
    flag_t *f;
    int n;
} FlagBuf;

/* HashMgr::add_word for a word with a description; returns 0 (or -2 on memory errors) and appends
 * (word, desc, captype) to phlist if the description has a ph: field */
static int add_word_desc(Ctx *c, const uint8_t *word, int wn, const flag_t *flags, int nflags, int onlyupcase,
                         const uint8_t *desc, int descn, int captype, PyObject *phlist);

static int
prepare_word(Ctx *c, const uint8_t *ts, int n, const uint8_t **out)
{
    HunDict *d = c->d;
    *out = ts;
    if (d->h_ignore.n) n = remove_ignored(c, ts, n, d->h_ignore, out);
    if (d->h_cpx) n = reverse_word(c, *out, n, d->h_utf8, out);
    return n;
}

static int
add_hidden(Ctx *c, const uint16_t *u, int nu, const flag_t *flags, int nflags, int captype, const uint8_t *desc,
           int descn, PyObject *phlist)
{
    HunDict *d = c->d;
    if ((captype == H_HUHCAP || captype == H_HUHINITCAP || (captype == H_ALLCAP && nflags))
        && !flags_has(flags, nflags, d->h_forbidden)) {
        AMark m = amark(&c->ar);
        flag_t *f2 = aalloc(&c->ar, sizeof(flag_t) * ((size_t)nflags + 1));
        if (nflags > 0) memcpy(f2, flags, sizeof(flag_t) * (size_t)nflags);
        f2[nflags] = H_ONLYUPCASEFLAG;
        sort_flags(f2, nflags + 1);
        uint16_t *st = udup(c, u, nu);
        u_lower(d, st, nu);
        if (nu) st[0] = d->upper[st[0]];
        uint8_t *w;
        int wn = from_units(c, st, nu, d->a_utf8, &w);
        int r;
        if (desc != NULL && descn) {
            r = add_word_desc(c, w, wn, f2, nflags + 1, 1, desc, descn, H_INITCAP, phlist);
        } else {
            const uint8_t *pw = w;
            if (d->h_ignore.n || d->h_cpx) wn = prepare_word(c, w, wn, &pw);
            r = add_word(d, pw, wn, f2, nflags + 1, 1) == -2 ? -2 : 0;
        }
        arelease(&c->ar, m);
        return r;
    }
    return 0;
}

static int
add_word_desc(Ctx *c, const uint8_t *word, int wn, const flag_t *flags, int nflags, int onlyupcase,
              const uint8_t *desc, int descn, int captype, PyObject *phlist)
{
    HunDict *d = c->d;
    if (d->h_ignore.n || d->h_cpx) wn = prepare_word(c, word, wn, &word);
    int32_t e = add_word(d, word, wn, flags, nflags, onlyupcase);
    if (e == -2) return -2;
    if (d->has_aliasm) {
        long long index = h_atoi(desc, descn, NULL);
        if (index > 0 && index <= d->naliasm) {
            desc = d->aliasm[index - 1].s;
            descn = d->aliasm[index - 1].n;
        } else {
            return 0;
        }
    }
    int k = py_find(desc, descn, (const uint8_t *)"ph:", 3, 0);
    if (k < 0) return 0;
    if (e >= 0) {
        int a = k + 3, b = a;
        while (b < descn && desc[b] != ' ' && desc[b] != '\t' && desc[b] != '\n') b++;
        size_t cp = (size_t)d->cphon;
        if (grow((void **)&d->phon, &cp, (size_t)d->nphon + 1, sizeof(BStr)) < 0) return -2;
        d->cphon = (int)cp;
        uint8_t *ph = malloc((size_t)(b - a) + 1);
        if (ph == NULL) return -2;
        memcpy(ph, desc + a, (size_t)(b - a));
        ph[b - a] = 0;
        d->phon[d->nphon].s = ph;
        d->phon[d->nphon].n = b - a;
        d->ent[e].phon = d->nphon++;
    }
    PyObject *t = Py_BuildValue("(y#y#i)", (const char *)word, (Py_ssize_t)wn, (const char *)desc,
                                (Py_ssize_t)descn, captype);
    if (t == NULL) return -1;
    int r = PyList_Append(phlist, t);
    Py_DECREF(t);
    return r < 0 ? -1 : 0;
}

static int
load_lines(Ctx *c, const uint8_t *data, size_t size, PyObject *phlist)
{
    HunDict *d = c->d;
    /* the lines (split at \n, without a last empty line) */
    size_t pos = 0;
    int lineno = 0;
    flag_t *fbuf = NULL;
    size_t fcap = 0;
    int ret = 0;
    while (pos < size) {
        const uint8_t *line = data + pos;
        const uint8_t *nl = memchr(line, '\n', size - pos);
        size_t ln = nl ? (size_t)(nl - line) : size - pos;
        pos += ln + 1;
        if (ln > INT32_MAX / 4) ln = INT32_MAX / 4;
        int n = (int)ln;
        AMark m = amark(&c->ar);
        if (lineno++ == 0) {
            /* _mychomp: (only a \r can end the line here) */
            int k = n;
            if (k > 0 && (line[k - 1] == 13 || line[k - 1] == 10)) n--;
            if (k > 1 && line[k - 2] == 13) n--;
            if (n >= 3 && line[0] == 0xef && line[1] == 0xbb && line[2] == 0xbf) {
                line += 3;
                n -= 3;
            }
            long long ts = h_atoi(line, n, NULL);
            if (ts <= 0) break;
            ts += 5 + 1000;
            if (ts % 2 == 0) ts++;
            d->tablesize = (long)ts;
            continue;
        }
        const uint8_t *ts = line;
        if (n && ts[n - 1] == 13) {
            int k = n;
            if (k > 0 && (ts[k - 1] == 13 || ts[k - 1] == 10)) n--;
            if (k > 1 && ts[k - 2] == 13) n--;
        }
        const uint8_t *desc = NULL;
        int descn = 0;
        if (memchr(ts, ':', (size_t)n) != NULL) {
            int dp_pos = -1;
            int k = py_find(ts, n, (const uint8_t *)":", 1, 0);
            while (k != -1) {
                if (k > 3 && (ts[k - 3] == ' ' || ts[k - 3] == '\t')) {
                    int q = k - 3;
                    while (q > 0 && (ts[q - 1] == ' ' || ts[q - 1] == '\t')) q--;
                    dp_pos = q == 0 ? -1 : q + 1;
                    break;
                }
                k = py_find(ts, n, (const uint8_t *)":", 1, k + 1);
            }
            int tab = py_find(ts, n, (const uint8_t *)"\t", 1, 0);
            if (tab != -1 && (dp_pos == -1 || tab < dp_pos)) dp_pos = tab + 1;
            if (dp_pos != -1) {
                desc = ts + dp_pos;
                descn = n - dp_pos;
                n = dp_pos - 1;
            }
        } else {
            int tab = py_find(ts, n, (const uint8_t *)"\t", 1, 0);
            if (tab != -1) {
                desc = ts + tab + 1;
                descn = n - tab - 1;
                n = tab;
            }
        }
        /* unescaped '/' */
        uint8_t *tw = NULL;
        int ap = py_find(ts, n, (const uint8_t *)"/", 1, 0);
        while (ap != -1) {
            if (ap == 0) {
                ap += 1;
                break; /* (ts[0] is '/') */
            } else if (ts[ap - 1] != '\\') {
                break;
            }
            if (tw == NULL) {
                tw = bdup(c, ts, n);
                ts = tw;
            }
            memmove(tw + ap - 1, tw + ap, (size_t)(n - ap));
            n--;
            ap = py_find(ts, n, (const uint8_t *)"/", 1, ap);
        }
        const flag_t *flags = NULL;
        int nflags = 0;
        if (ap != -1 && ap != n) {
            const uint8_t *fb = ts + ap + 1;
            int fbn = n - ap - 1;
            n = ap;
            if (d->naliasf) {
                long long index = h_atoi(fb, fbn, NULL);
                if (index > 0 && index <= d->naliasf) {
                    flags = d->aliasf[index - 1];
                    nflags = d->aliasf_n[index - 1];
                }
            } else {
                if ((size_t)fbn + 1 > fcap) {
                    fcap = (size_t)fbn * 2 + 16;
                    flag_t *nf = realloc(fbuf, sizeof(flag_t) * fcap);
                    if (nf == NULL) {
                        PyErr_NoMemory();
                        ret = -1;
                        break;
                    }
                    fbuf = nf;
                }
                nflags = decode_flags(d, fb, fbn, fbuf);
                sort_flags(fbuf, nflags);
                flags = fbuf;
            }
        }
        /* get_clen_and_captype (the HashMgr's units) */
        uint16_t *u;
        int nu = to_units(c, ts, n, d->h_utf8, &u);
        int captype = captype_units(d, u, nu);
        const uint8_t *pw = ts;
        int pn = n;
        if (d->h_ignore.n || d->h_cpx) pn = prepare_word(c, ts, n, &pw);
        int r;
        if (desc != NULL && descn) {
            r = add_word_desc(c, pw, pn, flags, nflags, 0, desc, descn, captype, phlist);
            if (r == 0 && captype >= H_ALLCAP) r = add_hidden(c, u, nu, flags, nflags, captype, desc, descn, phlist);
        } else {
            r = add_word(d, pw, pn, flags, nflags, 0) == -2 ? -2 : 0;
            if (r == 0 && captype >= H_ALLCAP) r = add_hidden(c, u, nu, flags, nflags, captype, NULL, 0, phlist);
        }
        arelease(&c->ar, m);
        if (r == -2) {
            PyErr_NoMemory();
            ret = -1;
            break;
        }
        if (r < 0) {
            ret = -1;
            break;
        }
    }
    free(fbuf);
    return ret;
}

static void ctx_init(Ctx *c, HunDict *d);
static void ctx_free(Ctx *c);
static int check_ready(HunDict *d);
static int get_word_arg(PyObject *arg, const uint8_t **w, int *n);

/* ------------------------------------------------------------------------ */
/* suggestion lists (the strings live in the keep arena) */

typedef struct {
    BStr *v;
    int n, cap;
} SList;

static void
sl_reserve(Ctx *c, SList *l, int need)
{
    if (need <= l->cap) return;
    int nc = l->cap ? l->cap * 2 : 16;
    if (nc < need) nc = need;
    BStr *nv = aalloc(&c->keep, sizeof(BStr) * (size_t)nc);
    if (l->n) memcpy(nv, l->v, sizeof(BStr) * (size_t)l->n);
    l->v = nv;
    l->cap = nc;
}

static BStr
keep_str(Ctx *c, const uint8_t *s, int n)
{
    uint8_t *p = aalloc(&c->keep, (size_t)n + 1);
    if (n) memcpy(p, s, (size_t)n);
    p[n] = 0;
    BStr b = {p, n};
    return b;
}

static void
sl_append(Ctx *c, SList *l, const uint8_t *s, int n)
{
    sl_reserve(c, l, l->n + 1);
    l->v[l->n++] = keep_str(c, s, n);
}

static void
sl_insert0(Ctx *c, SList *l, const uint8_t *s, int n)
{
    sl_reserve(c, l, l->n + 1);
    memmove(l->v + 1, l->v, sizeof(BStr) * (size_t)l->n);
    l->v[0] = keep_str(c, s, n);
    l->n++;
}

static void
sl_del(SList *l, int i)
{
    memmove(l->v + i, l->v + i + 1, sizeof(BStr) * (size_t)(l->n - i - 1));
    l->n--;
}

static int
sl_contains(const SList *l, const uint8_t *s, int n)
{
    for (int i = 0; i < l->n; i++)
        if (l->v[i].n == n && memcmp(l->v[i].s, s, (size_t)n) == 0) return 1;
    return 0;
}

static int
deadline_passed(Ctx *c)
{
    return now_mono() > c->deadline;
}

/* ------------------------------------------------------------------------ */
/* SuggestMgr */

static int
sug_checkword(Ctx *c, const uint8_t *word, int wn, int cpdsuggest)
{
    HunDict *d = c->d;
    if (cpdsuggest == 1) {
        if (d->is_compound) {
            int32_t rwords[100];
            for (int k = 0; k < 100; k++) rwords[k] = -1;
            int32_t rv = compound_check(c, word, wn, 0, 0, 100, 0, NULL, rwords, 0, 1, NO_INFO);
            if (rv >= 0) {
                int32_t rv2 = lookup(d, word, wn);
                if (rv2 < 0 || ENFLAGS(d, rv2) == 0
                    || !(EHAS(d, rv2, d->a_forbidden) || EHAS(d, rv2, d->nosuggest)))
                    return 3;
            }
        }
        return 0;
    }
    int nosuffix = 0;
    int32_t rv = lookup(d, word, wn);
    if (rv >= 0) {
        if (EHAS(d, rv, d->a_forbidden) || EHAS(d, rv, d->nosuggest) || EHAS(d, rv, d->substandard)) return 0;
        while (rv >= 0) {
            if (EHAS(d, rv, d->needaffix) || EHAS(d, rv, H_ONLYUPCASEFLAG) || EHAS(d, rv, d->onlyincompound))
                rv = d->ent[rv].next;
            else
                break;
        }
    } else {
        rv = prefix_check(c, word, wn, 0, wn, IN_CPD_NOT, H_FLAG_NULL);
    }
    if (rv >= 0)
        nosuffix = 1;
    else
        rv = suffix_check(c, word, wn, 0, wn, 0, NULL, H_FLAG_NULL, H_FLAG_NULL, IN_CPD_NOT);
    if (rv < 0 && d->havecontclass) {
        rv = suffix_check_twosfx(c, word, wn, 0, wn, 0, NULL, H_FLAG_NULL);
        if (rv < 0) rv = prefix_check_twosfx(c, word, wn, 0, wn, IN_CPD_NOT, H_FLAG_NULL);
    }
    if (rv >= 0 && (EHAS(d, rv, d->a_forbidden) || EHAS(d, rv, H_ONLYUPCASEFLAG) || EHAS(d, rv, d->nosuggest)
                    || EHAS(d, rv, d->onlyincompound)))
        return 0;
    if (rv >= 0) {
        if (d->compoundflag != H_FLAG_NULL && EHAS(d, rv, d->compoundflag)) return 2 + nosuffix;
        return 1;
    }
    return 0;
}

static int
sug_checkword_tmp(Ctx *c, const uint8_t *word, int wn, int cpdsuggest)
{
    AMark m = amark(&c->ar);
    int r = sug_checkword(c, word, wn, cpdsuggest);
    arelease(&c->ar, m);
    return r;
}

static void
testsug(Ctx *c, SList *wlst, const uint8_t *cand, int n, int cpdsuggest)
{
    if (wlst->n == c->d->maxsug) return;
    if (sl_contains(wlst, cand, n)) return;
    if (sug_checkword_tmp(c, cand, n, cpdsuggest)) sl_append(c, wlst, cand, n);
}

/* testsug for units */
static void
testsug_u(Ctx *c, SList *wlst, const uint16_t *u, int nu, int cpdsuggest)
{
    if (wlst->n == c->d->maxsug) return; /* (the conversion is not needed) */
    AMark m = amark(&c->ar);
    uint8_t *b;
    int n = from_units(c, u, nu, c->d->a_utf8, &b);
    testsug(c, wlst, b, n, cpdsuggest);
    arelease(&c->ar, m);
}

/* Pruning of the MAP search (map_related) in the first pass (cpdsuggest 0).
 * checkword(cand, 0) accepts cand only if a dictionary word W is its root:
 * cand = A + C where A is empty or the appendix of a prefix entry, and C =
 * R + T where R is a prefix of W[k:] (k: 0 or the strip length of a prefix
 * entry) and T, the rest from the suffixes (one or two levels, cross
 * products; also the cases where a strip is longer than the stem), is a
 * substring of a suffix appendix followed by a prefix of a suffix appendix.
 * A partial candidate that is not a prefix of such a string can not lead to
 * an accepted one, the search skips it. (Not used if an affix key contains
 * the wildcard '.'.) */
typedef struct {
    BStr a, strip;
} PfxPair;

typedef struct MapPrune {
    int ok;
    const uint8_t **roots; int nroots;  /* the dictionary words (NUL-terminated, without NUL bytes), sorted */
    PfxPair *pa; int npa;        /* the (appendix, strip) pairs of the prefix entries, sorted */
    int max_pa;
    BStr *sa; int nsa;           /* the suffix appendices, sorted */
    BStr *sub; int nsub;         /* the suffixes of the suffix appendices, sorted */
    int max_tail;
} MapPrune;

static int
bstr_cmp(const void *a, const void *b)
{
    const BStr *x = a, *y = b;
    int n = x->n < y->n ? x->n : y->n;
    int r = n ? memcmp(x->s, y->s, (size_t)n) : 0;
    if (r) return r;
    return x->n < y->n ? -1 : (x->n > y->n);
}

/* q is a prefix of an element of the sorted array */
static int
is_prefix_of_any(const BStr *v, int n, const uint8_t *q, int qn)
{
    if (qn == 0) return n > 0;
    int lo = 0, hi = n;
    BStr key = {q, qn};
    while (lo < hi) {
        int m = (lo + hi) >> 1;
        if (bstr_cmp(&v[m], &key) < 0) lo = m + 1; else hi = m;
    }
    return lo < n && v[lo].n >= qn && memcmp(v[lo].s, q, (size_t)qn) == 0;
}

static int
dedup_sorted(BStr *v, int n)
{
    if (n == 0) return 0;
    qsort(v, (size_t)n, sizeof(BStr), bstr_cmp);
    int k = 1;
    for (int i = 1; i < n; i++)
        if (bstr_cmp(&v[i], &v[k - 1]) != 0) v[k++] = v[i];
    return k;
}

static int
pfxpair_cmp(const void *x, const void *y)
{
    const PfxPair *p = x, *q = y;
    int r = bstr_cmp(&p->a, &q->a);
    return r ? r : bstr_cmp(&p->strip, &q->strip);
}

static int
root_cmp(const void *x, const void *y)
{
    return strcmp(*(const char *const *)x, *(const char *const *)y);
}

/* the order of the root r (NUL-terminated) and q[:qn] */
static inline int
root_cmp_q(const uint8_t *r, const uint8_t *q, int qn)
{
    for (int i = 0;; i++) {
        if (i == qn) return r[i] ? 1 : 0;
        if (!r[i]) return -1;
        if (r[i] != q[i]) return r[i] < q[i] ? -1 : 1;
    }
}

/* q is a prefix of a dictionary word */
static int
is_root_prefix(const MapPrune *mp, const uint8_t *q, int qn)
{
    if (qn == 0) return mp->nroots > 0;
    int lo = 0, hi = mp->nroots;
    while (lo < hi) {
        int m = (lo + hi) >> 1;
        if (root_cmp_q(mp->roots[m], q, qn) < 0) lo = m + 1; else hi = m;
    }
    if (lo >= mp->nroots) return 0;
    const uint8_t *r = mp->roots[lo];
    for (int i = 0; i < qn; i++)
        if (r[i] != q[i] || !r[i]) return 0;
    return 1;
}

static void
mp_free(MapPrune *mp)
{
    if (mp == NULL) return;
    free((void *)mp->roots);
    free(mp->pa);
    free(mp->sa);
    free(mp->sub);
    free(mp);
}

static MapPrune *
mp_build(Ctx *c)
{
    HunDict *d = c->d;
    if (d->mp != NULL) return d->mp;
    MapPrune *mp = calloc(1, sizeof(MapPrune));
    if (mp == NULL) longjmp(c->jb, 1);
    d->mp = mp;
    for (int i = 0; i < d->npent; i++)
        if (d->pent[i].key_dot) return mp;
    for (int i = 0; i < d->nsent; i++)
        if (d->sent[i].key_dot) return mp;
    size_t nr = 0;
    for (int32_t e = 0; e < d->nent; e++) {
        if (!d->ent[e].head) continue;
        if (memchr(EWORD(d, e), 0, (size_t)EWLEN(d, e)) != NULL) return mp; /* (NUL bytes: no pruning) */
        nr++;
    }
    mp->roots = malloc(sizeof(uint8_t *) * (nr + 1));
    mp->pa = malloc(sizeof(PfxPair) * ((size_t)d->npent + 1));
    mp->sa = malloc(sizeof(BStr) * ((size_t)d->nsent + 1));
    size_t nsub = 0;
    for (int i = 0; i < d->nsent; i++) nsub += (size_t)d->sent[i].appnd_len;
    mp->sub = malloc(sizeof(BStr) * (nsub + 1));
    if (mp->roots == NULL || mp->pa == NULL || mp->sa == NULL || mp->sub == NULL) longjmp(c->jb, 1);
    size_t r = 0;
    for (int32_t e = 0; e < d->nent; e++)
        if (d->ent[e].head) mp->roots[r++] = EWORD(d, e);
    qsort((void *)mp->roots, r, sizeof(uint8_t *), root_cmp);
    mp->nroots = (int)r;
    int n = 0;
    for (int i = 0; i < d->npent; i++) {
        mp->pa[n].a.s = d->pent[i].appnd;
        mp->pa[n].a.n = d->pent[i].appnd_len;
        mp->pa[n].strip.s = d->pent[i].strip;
        mp->pa[n].strip.n = d->pent[i].strip_len;
        n++;
    }
    if (n) {
        qsort(mp->pa, (size_t)n, sizeof(PfxPair), pfxpair_cmp);
        int k = 1;
        for (int i = 1; i < n; i++)
            if (pfxpair_cmp(&mp->pa[i], &mp->pa[k - 1]) != 0) mp->pa[k++] = mp->pa[i];
        n = k;
    }
    mp->npa = n;
    for (int i = 0; i < mp->npa; i++)
        if (mp->pa[i].a.n > mp->max_pa) mp->max_pa = mp->pa[i].a.n;
    n = 0;
    int maxa = 0;
    size_t ns = 0;
    for (int i = 0; i < d->nsent; i++) {
        const AffEntry *e = &d->sent[i];
        if (!e->appnd_len) continue;
        mp->sa[n].s = e->appnd;
        mp->sa[n].n = e->appnd_len;
        n++;
        if (e->appnd_len > maxa) maxa = e->appnd_len;
        for (int a = 0; a < e->appnd_len; a++) {
            mp->sub[ns].s = e->appnd + a;
            mp->sub[ns].n = e->appnd_len - a;
            ns++;
        }
    }
    mp->nsa = dedup_sorted(mp->sa, n);
    mp->nsub = dedup_sorted(mp->sub, (int)ns);
    mp->max_tail = 2 * maxa;
    mp->ok = 1;
    return mp;
}

/* T = a substring of a suffix appendix + a prefix of a suffix appendix (the substrings are prefix-closed:
 * the longest substring prefix of T by binary search) */
static int
mp_tail(const MapPrune *mp, const uint8_t *t, int tn)
{
    if (tn > mp->max_tail) return 0;
    int lo = 0, hi = tn;
    while (lo < hi) {
        int m = (lo + hi + 1) >> 1;
        if (is_prefix_of_any(mp->sub, mp->nsub, t, m)) lo = m; else hi = m - 1;
    }
    for (int s = lo; s >= 0; s--)
        if (s == tn || is_prefix_of_any(mp->sa, mp->nsa, t + s, tn - s)) return 1;
    return 0;
}

/* C = R + T (R a prefix of a root string). The root prefixes are prefix-closed and the tails suffix-closed:
 * only the longest root prefix R needs to be tried. */
static int
mp_rest(const MapPrune *mp, const uint8_t *cs, int cn)
{
    if (is_root_prefix(mp, cs, cn)) return 1;
    if (mp->nroots == 0) return 0;
    int lo = 0, hi = cn - 1;
    while (lo < hi) {
        int m = (lo + hi + 1) >> 1;
        if (is_root_prefix(mp, cs, m)) lo = m; else hi = m - 1;
    }
    return mp_tail(mp, cs + lo, cn - lo);
}

/* mp_rest(strip + C) */
static int
mp_rest_strip(const MapPrune *mp, const BStr *strip, const uint8_t *cs, int cn)
{
    if (strip->n == 0) return mp_rest(mp, cs, cn);
    uint8_t buf[512];
    if (strip->n + cn > (int)sizeof(buf)) return 1; /* (long: no pruning) */
    memcpy(buf, strip->s, (size_t)strip->n);
    if (cn) memcpy(buf + strip->n, cs, (size_t)cn);
    return mp_rest(mp, buf, strip->n + cn);
}

/* the first prefix pair whose appendix is not smaller than q[:qn] */
static int
pfxpair_lower(const MapPrune *mp, const uint8_t *q, int qn)
{
    int lo = 0, hi = mp->npa;
    BStr key = {q, qn};
    while (lo < hi) {
        int m = (lo + hi) >> 1;
        if (bstr_cmp(&mp->pa[m].a, &key) < 0) lo = m + 1; else hi = m;
    }
    return lo;
}

/* a candidate starting with P can be accepted by checkword(cand, 0) */
static int
mp_viable(const MapPrune *mp, const uint8_t *p, int n)
{
    if (mp_rest(mp, p, n)) return 1;
    /* prefix entries without appendix, with a strip S: S + P */
    for (int i = 0; i < mp->npa && mp->pa[i].a.n == 0; i++)
        if (mp->pa[i].strip.n && mp_rest_strip(mp, &mp->pa[i].strip, p, n)) return 1;
    /* P is a proper prefix of an appendix */
    for (int i = pfxpair_lower(mp, p, n); i < mp->npa; i++) {
        const BStr *a = &mp->pa[i].a;
        if (a->n < n || memcmp(a->s, p, (size_t)n) != 0) break;
        if (a->n > n) return 1;
    }
    /* P = A + C, with S + C */
    for (int k = 1; k <= n && k <= mp->max_pa; k++) {
        for (int i = pfxpair_lower(mp, p, k); i < mp->npa; i++) {
            const PfxPair *pp = &mp->pa[i];
            if (pp->a.n != k || memcmp(pp->a.s, p, (size_t)k) != 0) break;
            if (mp_rest_strip(mp, &pp->strip, p + k, n - k)) return 1;
        }
    }
    return 0;
}

/* The pruning of the MAP search in the compound pass (cpdsuggest 1): the
 * candidates are checked by compound_check, which accepts a word only if it
 * is a concatenation of at least two parts accepted by the affix checks
 * (lookup, prefix_check, suffix_check, the two-level suffixes, of the first
 * part and of the rest) - if the compound_check's st is the word: no
 * CHECKCOMPOUNDPATTERN replacement (third field) can occur in a candidate,
 * no SIMPLIFIEDTRIPLE. relaxed_accept is a superset of the affix checks
 * (without the flags, the conditions and the length limits: a lookup of the
 * word or of its stems after removing a prefix and up to two levels of
 * suffixes, found with the same affix searches). A partial candidate P is
 * viable only if P = A1 ... Ak R with relaxed_accept(Ai) and mp_viable(R)
 * (k >= 0); reach[e]: P[:e] is such a concatenation. */
static int relaxed_sfx(Ctx *c, const uint8_t *x, int n, int levels);

static int
relaxed_stem(Ctx *c, const uint8_t *x, int n, const AffEntry *e, int levels)
{
    int tl = n - e->appnd_len;
    if (tl < 0) return 0;
    if (lookup2(c->d, x, tl, e->strip, e->strip_len) >= 0) return 1;
    if (levels > 1) {
        AMark m = amark(&c->ar);
        uint8_t *y = bcat(c, x, tl, e->strip, e->strip_len);
        int r = relaxed_sfx(c, y, tl + e->strip_len, levels - 1);
        arelease(&c->ar, m);
        return r;
    }
    return 0;
}

/* (the stems of the entries with the same appendix length and strip are the same: checked once) */
#define RELAXED_SEEN 64
typedef struct {
    int n;
    int alen[RELAXED_SEEN];
    const uint8_t *strip[RELAXED_SEEN];
} RelaxedSeen;

static int
relaxed_new(RelaxedSeen *rs, const AffEntry *e)
{
    for (int k = 0; k < rs->n; k++)
        if (rs->alen[k] == e->appnd_len && rs->strip[k] == e->strip) return 0;
    if (rs->n < RELAXED_SEEN) {
        rs->alen[rs->n] = e->appnd_len;
        rs->strip[rs->n] = e->strip;
        rs->n++;
    }
    return 1;
}

/* a suffix (or two levels of suffixes) of x can be removed giving a dictionary word */
static int
relaxed_sfx(Ctx *c, const uint8_t *x, int n, int levels)
{
    HunDict *d = c->d;
    RelaxedSeen rs;
    rs.n = 0;
    for (int32_t se = d->sstart[0]; se >= 0; se = d->sent[se].next)
        if (relaxed_new(&rs, &d->sent[se]) && relaxed_stem(c, x, n, &d->sent[se], levels)) return 1;
    if (n == 0) return 0;
    int s0 = n - d->max_sfx_key;
    if (s0 < 0) s0 = 0;
    const uint8_t *seg = x + s0;
    int sn = n - s0;
    int32_t sp = d->sstart[seg[sn - 1]];
    while (sp >= 0) {
        const AffEntry *e = &d->sent[sp];
        if (is_rev_subset(e, seg, sn)) {
            if (relaxed_new(&rs, e) && relaxed_stem(c, x, n, e, levels)) return 1;
            sp = e->nexteq;
        } else {
            sp = e->nextne;
        }
    }
    return 0;
}

static int
relaxed_pfx(Ctx *c, const uint8_t *x, int n, const AffEntry *pe)
{
    int la = pe->appnd_len;
    if (la > n) return 0;
    AMark m = amark(&c->ar);
    uint8_t *t = bcat(c, pe->strip, pe->strip_len, x + la, n - la);
    int tn = pe->strip_len + n - la;
    int r = lookup(c->d, t, tn) >= 0 || relaxed_sfx(c, t, tn, 2);
    arelease(&c->ar, m);
    return r;
}

static int
relaxed_accept(Ctx *c, const uint8_t *x, int n)
{
    HunDict *d = c->d;
    if (lookup(d, x, n) >= 0) return 1;
    if (relaxed_sfx(c, x, n, 2)) return 1;
    RelaxedSeen rs;
    rs.n = 0;
    for (int32_t i = d->pstart[0]; i >= 0; i = d->pent[i].next)
        if (relaxed_new(&rs, &d->pent[i]) && relaxed_pfx(c, x, n, &d->pent[i])) return 1;
    int segn = n < d->max_pfx_key ? n : d->max_pfx_key;
    int32_t pp = segn ? d->pstart[x[0]] : (d->pfx_groups ? -1 : d->pstart[0]);
    while (pp >= 0) {
        const AffEntry *pe = &d->pent[pp];
        if (is_subset(pe->key, pe->key_len, pe->key_dot, x, segn, 0)) {
            if (relaxed_new(&rs, pe) && relaxed_pfx(c, x, n, pe)) return 1;
            pp = pe->nexteq;
        } else {
            pp = pe->nextne;
        }
    }
    return 0;
}

typedef struct {
    uint8_t *reach;
    int cap;
    uint8_t *ruleflags;  /* NULL, or (only COMPOUNDRULE, no COMPOUNDFLAG/BEGIN/MIDDLE) the flags of the rules */
} CpdPrune;

/* (only COMPOUNDRULE) a part before the last one is a dictionary word with a flag of a rule (the first word
 * of compound_check with onlycpdrule: lookup and defcpd_check, no affixes) */
static int
cpd_rule_part(HunDict *d, const uint8_t *ruleflags, const uint8_t *x, int n)
{
    for (int32_t e = lookup(d, x, n); e >= 0; e = d->ent[e].next) {
        const flag_t *f = EFLAGS(d, e);
        int nf = ENFLAGS(d, e);
        for (int k = 0; k < nf; k++)
            if (ruleflags[f[k] >> 3] & (1 << (f[k] & 7))) return 1;
    }
    return 0;
}

/* the candidate p (the bytes after base are new) can become a compound */
static int
cpd_viable(Ctx *c, const MapPrune *mp, CpdPrune *cp, const uint8_t *p, int base, int n)
{
    if (n + 1 > cp->cap) {
        int nc = 2 * (n + 1) + 16;
        uint8_t *r = aalloc(&c->ar, (size_t)nc);
        memcpy(r, cp->reach, (size_t)cp->cap);
        cp->reach = r;
        cp->cap = nc;
    }
    /* (the parts of compound_check have at least cpdmin characters: the first part ends after cpdmin
     * characters (setcminmax), the rest has at least cpdmin characters, recursively) */
    int cpdmin = c->d->cpdmin;
    int utf8 = c->d->h_utf8;
    for (int e = base + 1; e <= n; e++) {
        cp->reach[e] = 0;
        int nc = 0; /* the non-continuation bytes of p[s+1:e] */
        for (int s = e - 1; s >= 0; s--) {
            if (s < e - 1 && (p[s + 1] & 0xc0) != 0x80) nc++;
            if (!cp->reach[s]) continue;
            /* the characters of p[s:e]: its first byte and the following non-continuation bytes */
            int nch = utf8 ? 1 + nc : e - s;
            if (nch < cpdmin) continue;
            if (cp->ruleflags != NULL ? cpd_rule_part(c->d, cp->ruleflags, p + s, e - s)
                                      : memo_check(c, MEMO_RELAXED, p + s, e - s, 0, 0, 0)) {
                cp->reach[e] = 1;
                break;
            }
        }
    }
    for (int s = 0; s <= n; s++)
        if (cp->reach[s] && mp_viable(mp, p + s, n - s)) return 1;
    return 0;
}

typedef struct {
    int *start;   /* wl + 1 offsets into ent/klen */
    int *ent;
    int *klen;
} MapIndex;

static void
map_related(Ctx *c, const uint8_t *word, int wl, const MapIndex *mi, TBuf *cand, int wn, SList *wlst,
            int cpdsuggest, const MapPrune *mp, CpdPrune *cp)
{
    HunDict *d = c->d;
    if (c->map_abort) return;
    if (c->map_timer_on) {
        c->map_count--;
        if (!c->map_count) {
            if (now_mono() > c->map_deadline) {
                c->map_abort = 1;
                return;
            }
            c->map_count = 100;
        }
    }
    if (wn >= wl) {
        if (!sl_contains(wlst, cand->p, cand->n) && sug_checkword_tmp(c, cand->p, cand->n, cpdsuggest)) {
            if (wlst->n < d->maxsug) sl_append(c, wlst, cand->p, cand->n);
        }
        return;
    }
    int base = cand->n;
    int k0 = mi->start[wn], k1 = mi->start[wn + 1];
    for (int k = k0; k < k1; k++) {
        const MapEntry *me = &d->maptable[mi->ent[k]];
        for (int r = 0; r < me->n; r++) {
            cand->n = base;
            tb_append(c, cand, me->v[r].s, me->v[r].n);
            if (mp != NULL && me->v[r].n
                && !(cp != NULL ? cpd_viable(c, mp, cp, cand->p, base, cand->n) : mp_viable(mp, cand->p, cand->n)))
                continue;
            map_related(c, word, wl, mi, cand, wn + mi->klen[k], wlst, cpdsuggest, mp, cp);
            if (c->map_abort) return;
        }
    }
    if (k0 == k1) {
        cand->n = base;
        tb_append(c, cand, word + wn, 1);
        if (mp == NULL
            || (cp != NULL ? cpd_viable(c, mp, cp, cand->p, base, cand->n) : mp_viable(mp, cand->p, cand->n)))
            map_related(c, word, wl, mi, cand, wn + 1, wlst, cpdsuggest, mp, cp);
    }
    cand->n = base;
}

static void
mapchars(Ctx *c, SList *wlst, const uint8_t *word, int wl, int cpdsuggest)
{
    HunDict *d = c->d;
    if (wl < 2 || d->nmaptable == 0) return;
    AMark m = amark(&c->ar);
    MapIndex mi;
    int nkeys = 0;
    for (int e = 0; e < d->nmaptable; e++) nkeys += d->maptable[e].n;
    mi.start = aalloc(&c->ar, sizeof(int) * ((size_t)wl + 2));
    mi.ent = aalloc(&c->ar, sizeof(int) * ((size_t)wl * (size_t)nkeys + 1));
    mi.klen = aalloc(&c->ar, sizeof(int) * ((size_t)wl * (size_t)nkeys + 1));
    int nm = 0;
    for (int wn = 0; wn < wl; wn++) {
        mi.start[wn] = nm;
        for (int e = 0; e < d->nmaptable; e++) {
            const MapEntry *me = &d->maptable[e];
            for (int k = 0; k < me->n; k++) {
                BStr key = me->v[k];
                if (key.n && wn + key.n <= wl && memcmp(word + wn, key.s, (size_t)key.n) == 0) {
                    mi.ent[nm] = e;
                    mi.klen[nm] = key.n;
                    nm++;
                }
            }
        }
    }
    mi.start[wl] = nm;
    mi.start[wl + 1] = nm;
    TBuf cand = {NULL, 0, 0};
    tb_reserve(c, &cand, wl * 4 + 16);
    const MapPrune *mp = NULL;
    CpdPrune cpstate = {NULL, 0, NULL};
    CpdPrune *cp = NULL;
    if (!c->no_map_prune && (cpdsuggest == 0 || (cpdsuggest == 1 && c->memo != NULL && !d->simplifiedtriple))) {
        mp = mp_build(c);
        if (!mp->ok) mp = NULL;
        if (mp != NULL && cpdsuggest == 1) {
            /* (the CHECKCOMPOUNDPATTERN replacements need their third pattern in the word: possible only if its
             * bytes are in the word or the MAP table) */
            uint8_t possible[256] = {0};
            for (int i = 0; i < wl; i++) possible[word[i]] = 1;
            for (int e = 0; e < d->nmaptable; e++)
                for (int k = 0; k < d->maptable[e].n; k++)
                    for (int i = 0; i < d->maptable[e].v[k].n; i++) possible[d->maptable[e].v[k].s[i]] = 1;
            for (int k = 0; k < d->ncheckcpd && mp != NULL; k++) {
                const BStr *p3 = &d->checkcpd[k].pat3;
                int all = p3->n > 0;
                for (int i = 0; i < p3->n; i++) all &= possible[p3->s[i]];
                if (all) mp = NULL;
            }
            if (mp != NULL) {
                cpstate.cap = wl * 4 + 16;
                cpstate.reach = aalloc(&c->ar, (size_t)cpstate.cap);
                cpstate.reach[0] = 1;
                if (d->compoundflag == H_FLAG_NULL && d->compoundbegin == H_FLAG_NULL
                    && d->compoundmiddle == H_FLAG_NULL) {
                    /* (the parts before the last one: words with a flag of the rules) */
                    cpstate.ruleflags = aalloc(&c->ar, 65536 / 8);
                    memset(cpstate.ruleflags, 0, 65536 / 8);
                    for (int r = 0; r < d->ndefcpd; r++)
                        for (int k = 0; k < d->defcpd[r].n; k++) {
                            flag_t f = d->defcpd[r].f[k];
                            if (f != '*' && f != '?') cpstate.ruleflags[f >> 3] |= (uint8_t)(1 << (f & 7));
                        }
                }
                cp = &cpstate;
            }
        }
    }
    if (!c->has_deadline) {
        map_related(c, word, wl, &mi, &cand, 0, wlst, cpdsuggest, mp, cp);
    } else {
        c->map_timer_on = 1;
        c->map_count = 100;
        c->map_abort = 0;
        double t = now_mono() + c->time_limit / 4;
        c->map_deadline = c->deadline < t ? c->deadline : t;
        map_related(c, word, wl, &mi, &cand, 0, wlst, cpdsuggest, mp, cp);
        c->map_timer_on = 0;
        c->map_abort = 0;
    }
    arelease(&c->ar, m);
}

static void
replchars(Ctx *c, SList *wlst, const uint8_t *word, int wl, int cpdsuggest)
{
    HunDict *d = c->d;
    if (wl < 2) return;
    for (int k = 0; k < d->rep.n; k++) {
        RepEntry *re = &d->rep.v[k];
        int lp = re->pat.n;
        int r = py_find(word, wl, re->pat.s, lp, 0);
        while (r != -1) {
            int rtype = r == 0 ? 1 : 0;
            if (r + lp == wl) rtype += 2;
            while (rtype && !re->out[rtype].n) rtype = (rtype == 2 && r != 0) ? 0 : rtype - 1;
            BStr out = re->out[rtype];
            if (out.n) {
                AMark m = amark(&c->ar);
                int e2 = r + lp > wl ? wl : r + lp;
                uint8_t *cand = bcat3(c, word, r, out.s, out.n, word + e2, wl - e2);
                int cn = r + out.n + wl - e2;
                testsug(c, wlst, cand, cn, cpdsuggest);
                int sp = py_find(cand, cn, (const uint8_t *)" ", 1, 0);
                int prev = 0;
                while (sp != -1) {
                    if (sug_checkword_tmp(c, cand + prev, sp - prev, 0)) {
                        int oldns = wlst->n;
                        testsug(c, wlst, cand + sp + 1, cn - sp - 1, cpdsuggest);
                        if (oldns < wlst->n) wlst->v[wlst->n - 1] = keep_str(c, cand, cn);
                    }
                    prev = sp + 1;
                    sp = py_find(cand, cn, (const uint8_t *)" ", 1, prev);
                }
                arelease(&c->ar, m);
            }
            r = py_find(word, wl, re->pat.s, lp, r + 1);
        }
    }
}

static void
doubletwochars(Ctx *c, SList *wlst, const uint16_t *u, int wl, int cpdsuggest)
{
    if (wl < 5) return;
    int state = 0;
    AMark m = amark(&c->ar);
    uint16_t *t = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)wl + 1));
    for (int i = 2; i < wl; i++) {
        if (u[i] == u[i - 2]) {
            state++;
            if (state == 3 || (state == 2 && i >= 4)) {
                memcpy(t, u, sizeof(uint16_t) * (size_t)(i - 1));
                memcpy(t + i - 1, u + i + 1, sizeof(uint16_t) * (size_t)(wl - i - 1));
                testsug_u(c, wlst, t, wl - 2, cpdsuggest);
                state = 0;
            }
        } else {
            state = 0;
        }
    }
    arelease(&c->ar, m);
}

static void
badcharkey(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    HunDict *d = c->d;
    AMark m = amark(&c->ar);
    uint16_t *t = udup(c, u, n);
    const uint16_t *ckey = d->ckey;
    int nk = d->nckey;
    for (int i = 0; i < n; i++) {
        uint16_t tmpc = u[i];
        uint16_t up = d->h_utf8 ? d->plain_upper[tmpc] : d->upper[tmpc];
        if (up != tmpc) {
            t[i] = up;
            testsug_u(c, wlst, t, n, cpdsuggest);
            t[i] = tmpc;
        }
        if (!nk) continue;
        for (int loc = 0; loc < nk; loc++) {
            if (ckey[loc] != tmpc) continue;
            if (loc > 0 && ckey[loc - 1] != '|') {
                t[i] = ckey[loc - 1];
                testsug_u(c, wlst, t, n, cpdsuggest);
                t[i] = tmpc;
            }
            if (loc + 1 < nk && ckey[loc + 1] != '|') {
                t[i] = ckey[loc + 1];
                testsug_u(c, wlst, t, n, cpdsuggest);
                t[i] = tmpc;
            }
        }
    }
    arelease(&c->ar, m);
}

static void
badchar(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    HunDict *d = c->d;
    AMark m = amark(&c->ar);
    uint16_t *t = udup(c, u, n);
    for (int k = 0; k < d->nctry; k++) {
        uint16_t ch = d->ctry[k];
        for (int i = n - 1; i >= 0; i--) {
            if (u[i] == ch) continue;
            t[i] = ch;
            testsug_u(c, wlst, t, n, cpdsuggest);
            t[i] = u[i];
        }
    }
    arelease(&c->ar, m);
}

static void
extrachar(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    if (n < 2) return;
    AMark m = amark(&c->ar);
    uint16_t *t = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 1));
    for (int i = 0; i < n; i++) {
        int index = n - 1 - i;
        memcpy(t, u, sizeof(uint16_t) * (size_t)index);
        memcpy(t + index, u + index + 1, sizeof(uint16_t) * (size_t)(n - index - 1));
        testsug_u(c, wlst, t, n - 1, cpdsuggest);
    }
    arelease(&c->ar, m);
}

static void
forgotchar(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    HunDict *d = c->d;
    AMark m = amark(&c->ar);
    uint16_t *t = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 2));
    for (int k = 0; k < d->nctry; k++) {
        for (int i = 0; i <= n; i++) {
            int index = n - i;
            memcpy(t, u, sizeof(uint16_t) * (size_t)index);
            t[index] = d->ctry[k];
            memcpy(t + index + 1, u + index, sizeof(uint16_t) * (size_t)(n - index));
            testsug_u(c, wlst, t, n + 1, cpdsuggest);
        }
    }
    arelease(&c->ar, m);
}

static int
mystrlen(Ctx *c, const uint8_t *b, int n)
{
    if (c->d->h_utf8) {
        if (has_four_byte(b, n)) return -1;
        AMark m = amark(&c->ar);
        uint16_t *u;
        int nu = u8_u16(c, b, n, &u);
        arelease(&c->ar, m);
        return nu;
    }
    return n;
}

static int
twowords(Ctx *c, SList *wlst, const uint8_t *word, int wl, int cpdsuggest, int good)
{
    HunDict *d = c->d;
    if (wl < 3) return 0;
    int utf8 = d->h_utf8;
    int k = 0;
    AMark m = amark(&c->ar);
    uint8_t *cand = aalloc(&c->ar, (size_t)wl + 2);
    for (;;) {
        if (k + 1 >= wl) break;
        k++;
        while (utf8 && k < wl && (word[k] & 0xc0) == 0x80) k++;
        if (utf8 && k >= wl) break;
        memcpy(cand, word, (size_t)k);
        cand[k] = ' ';
        memcpy(cand + k + 1, word + k, (size_t)(wl - k));
        if (!cpdsuggest && sug_checkword_tmp(c, cand, wl + 1, cpdsuggest)) {
            if (!good) {
                good = 1;
                wlst->n = 0;
            }
            sl_insert0(c, wlst, cand, wl + 1);
        }
        if (d->lang_with_dash_usage) {
            cand[k] = '-';
            if (!cpdsuggest && sug_checkword_tmp(c, cand, wl + 1, cpdsuggest)) {
                if (!good) {
                    good = 1;
                    wlst->n = 0;
                }
                sl_insert0(c, wlst, cand, wl + 1);
            }
        }
        if (wlst->n < d->maxsug && !d->nosplitsugs && !good) {
            if (sug_checkword_tmp(c, word, k, cpdsuggest) && sug_checkword_tmp(c, word + k, wl - k, cpdsuggest)) {
                cand[k] = ' ';
                int cwrd = !sl_contains(wlst, cand, wl + 1);
                if (cwrd && wlst->n < d->maxsug) sl_append(c, wlst, cand, wl + 1);
                if (!d->nosplitsugs && d->lang_with_dash_usage && mystrlen(c, word + k, wl - k) > 1
                    && mystrlen(c, word, k) > 1) {
                    cand[k] = '-';
                    if (sl_contains(wlst, cand, wl + 1)) cwrd = 0;
                    if (wlst->n < d->maxsug && cwrd) sl_append(c, wlst, cand, wl + 1);
                }
            }
        }
    }
    arelease(&c->ar, m);
    return good;
}

static void
swapchar(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    if (n < 2) return;
    AMark m = amark(&c->ar);
    uint16_t *t = udup(c, u, n);
    for (int i = 0; i < n - 1; i++) {
        t[i] = u[i + 1];
        t[i + 1] = u[i];
        testsug_u(c, wlst, t, n, cpdsuggest);
        t[i] = u[i];
        t[i + 1] = u[i + 1];
    }
    if (n == 4 || n == 5) {
        t[0] = u[1];
        t[1] = u[0];
        t[2] = u[2];
        t[n - 2] = u[n - 1];
        t[n - 1] = u[n - 2];
        testsug_u(c, wlst, t, n, cpdsuggest);
        if (n == 5) {
            t[0] = u[0];
            t[1] = u[2];
            t[2] = u[1];
            testsug_u(c, wlst, t, n, cpdsuggest);
        }
    }
    arelease(&c->ar, m);
}

static void
longswapchar(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    AMark m = amark(&c->ar);
    uint16_t *t = udup(c, u, n);
    for (int p = 0; p < n; p++) {
        for (int q = 0; q < n; q++) {
            int dd = q > p ? q - p : p - q;
            if (dd > 1 && dd <= H_MAX_CHAR_DISTANCE) {
                t[p] = u[q];
                t[q] = u[p];
                testsug_u(c, wlst, t, n, cpdsuggest);
                t[p] = u[p];
                t[q] = u[q];
            }
        }
    }
    arelease(&c->ar, m);
}

static void
movechar(Ctx *c, SList *wlst, const uint16_t *u, int n, int cpdsuggest)
{
    if (n < 2) return;
    AMark m = amark(&c->ar);
    uint16_t *t = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 1));
    for (int p = 0; p < n; p++) {
        memcpy(t, u, sizeof(uint16_t) * (size_t)n);
        for (int q = p + 1; q < n && q - p <= H_MAX_CHAR_DISTANCE; q++) {
            uint16_t x = t[q];
            t[q] = t[q - 1];
            t[q - 1] = x;
            if (q - p >= 2) testsug_u(c, wlst, t, n, cpdsuggest);
        }
    }
    for (int p = n - 1; p >= 0; p--) {
        memcpy(t, u, sizeof(uint16_t) * (size_t)n);
        for (int q = p - 1; q >= 0 && p - q <= H_MAX_CHAR_DISTANCE; q--) {
            uint16_t x = t[q];
            t[q] = t[q + 1];
            t[q + 1] = x;
            if (p - q >= 2) testsug_u(c, wlst, t, n, cpdsuggest);
        }
    }
    arelease(&c->ar, m);
}

/* SuggestMgr::suggest: whether there is a good suggestion; *onlycmpdsug may be NULL */
static int
sm_suggest(Ctx *c, SList *slst, const uint8_t *word, int wn, int *onlycmpdsug)
{
    HunDict *d = c->d;
    int nocompoundtwowords = 0;
    int nsugorig = slst->n;
    int old_sug = 0;
    int good = 0;
    AMark m = amark(&c->ar);
    if (d->a_cpx) wn = reverse_word(c, word, wn, d->h_utf8, &word);
    uint16_t *u;
    int nu;
    if (d->h_utf8) {
        if (has_four_byte(word, wn)) {
            arelease(&c->ar, m);
            return 0;
        }
        nu = u8_u16(c, word, wn, &u);
    } else {
        nu = to_units(c, word, wn, 0, &u);
    }
    int maxsug = d->maxsug, maxcpdsugs = d->s_maxcpdsugs;
    int cpdsuggest = 0;
#define ROOM() ((!c->has_deadline || !deadline_passed(c)) && slst->n < maxsug \
                && (!cpdsuggest || slst->n < old_sug + maxcpdsugs))
    while (cpdsuggest < 2 && nocompoundtwowords == 0 && !good) {
        if (cpdsuggest > 0) old_sug = slst->n;
        if (cpdsuggest == 1 && !d->is_compound) {
            /* (without compounding the checks of this pass are always false: it adds nothing) */
            cpdsuggest++;
            continue;
        }
        if (slst->n < maxsug) {
            int i = slst->n;
            uint16_t *up = udup(c, u, nu);
            u_upper(d, up, nu);
            testsug_u(c, slst, up, nu, cpdsuggest);
            if (slst->n > i) good = 1;
        }
        if (ROOM()) {
            int i = slst->n;
            replchars(c, slst, word, wn, cpdsuggest);
            if (slst->n > i) good = 1;
        }
        if (ROOM()) mapchars(c, slst, word, wn, cpdsuggest);
        if (cpdsuggest == 0 && slst->n > nsugorig) nocompoundtwowords = 1;
        if (ROOM()) swapchar(c, slst, u, nu, cpdsuggest);
        if (ROOM()) longswapchar(c, slst, u, nu, cpdsuggest);
        if (ROOM()) badcharkey(c, slst, u, nu, cpdsuggest);
        if (ROOM()) extrachar(c, slst, u, nu, cpdsuggest);
        if (ROOM()) forgotchar(c, slst, u, nu, cpdsuggest);
        if (ROOM()) movechar(c, slst, u, nu, cpdsuggest);
        if (ROOM()) badchar(c, slst, u, nu, cpdsuggest);
        if (ROOM()) doubletwochars(c, slst, u, nu, cpdsuggest);
        if (!cpdsuggest || (!d->nosplitsugs && slst->n < old_sug + maxcpdsugs))
            good = twowords(c, slst, word, wn, cpdsuggest, good);
        cpdsuggest++;
    }
#undef ROOM
    if (!nocompoundtwowords && slst->n && onlycmpdsug != NULL) *onlycmpdsug = 1;
    arelease(&c->ar, m);
    return good;
}

/* ------------------------------------------------------------------------ */
/* ngram suggestions */

/* HashMgr::hash (Hunspell 1.7.1, signed chars, 64-bit unsigned long) */
static uint64_t
hm_hash(const uint8_t *w, int n, long tablesize)
{
    uint64_t hv = 0;
    int i = 0;
    for (; i < 4 && i < n; i++) hv = (hv << 8) | (uint64_t)(int64_t)(int8_t)w[i];
    for (; i < n; i++) {
        hv = (hv << 5) | ((hv >> 27) & 31);
        hv ^= (uint64_t)(int64_t)(int8_t)w[i];
    }
    return hv % (uint64_t)tablesize;
}

typedef struct {
    uint64_t h;
    int32_t e;
} HashPos;

typedef struct {
    uint32_t h;
    int32_t e;
} HashPos32;

static int
cmp_hashpos(const void *a, const void *b)
{
    const HashPos *x = a, *y = b;
    if (x->h != y->h) return x->h < y->h ? -1 : 1;
    return x->e < y->e ? -1 : (x->e > y->e);
}

static int
cmp_hashpos32(const void *a, const void *b)
{
    const HashPos32 *x = a, *y = b;
    if (x->h != y->h) return x->h < y->h ? -1 : 1;
    return x->e < y->e ? -1 : (x->e > y->e);
}

/* _ngram_data: the entries in the order of the hash table, their lengths and skip / initcap bits */
static int
ng_build(Ctx *c)
{
    HunDict *d = c->d;
    if (d->ng_order != NULL || d->nent == 0) return 0;
    int n = d->nent;
    int32_t *order = malloc(sizeof(int32_t) * (size_t)n);
    uint8_t *clen = malloc((size_t)n);
    uint8_t *bits = malloc((size_t)n);
    int hash32 = (uint64_t)d->tablesize <= UINT32_MAX;
    void *hp = malloc((hash32 ? sizeof(HashPos32) : sizeof(HashPos)) * (size_t)n);
    if (hp == NULL || order == NULL || clen == NULL || bits == NULL) {
        free(hp); free(order); free(clen); free(bits);
        longjmp(c->jb, 1);
    }
    /* the order of the entries: by hash, then by index */
    if (hash32) {
        HashPos32 *h32 = hp;
        for (int i = 0; i < n; i++) {
            h32[i].h = (uint32_t)hm_hash(EWORD(d, i), EWLEN(d, i), d->tablesize);
            h32[i].e = i;
        }
        qsort(h32, (size_t)n, sizeof(HashPos32), cmp_hashpos32);
        for (int i = 0; i < n; i++) order[i] = h32[i].e;
    } else {
        HashPos *h64 = hp;
        for (int i = 0; i < n; i++) {
            h64[i].h = hm_hash(EWORD(d, i), EWLEN(d, i), d->tablesize);
            h64[i].e = i;
        }
        qsort(h64, (size_t)n, sizeof(HashPos), cmp_hashpos);
        for (int i = 0; i < n; i++) order[i] = h64[i].e;
    }
    free(hp);
    flag_t skipf[5] = {d->a_forbidden, H_ONLYUPCASEFLAG, d->nosuggest, d->nongramsuggest, d->onlyincompound};
    for (int pos = 0; pos < n; pos++) {
        int32_t e = order[pos];
        int skip = 0;
        if (ENFLAGS(d, e))
            for (int k = 0; k < 5; k++)
                if (EHAS(d, e, skipf[k])) { skip = 1; break; }
        AMark m = amark(&c->ar);
        uint16_t *u;
        int nu;
        int cl;
        if (d->h_utf8) {
            int nonbmp = has_four_byte(EWORD(d, e), EWLEN(d, e));
            nu = u8_u16(c, EWORD(d, e), EWLEN(d, e), &u);
            cl = nonbmp ? 255 : nu & 0xff;
        } else {
            nu = to_units(c, EWORD(d, e), EWLEN(d, e), d->a_utf8, &u);
            cl = nu & 0xff;
        }
        int initcap = EHAS(d, e, H_ONLYUPCASEFLAG) ? 1 : captype_units(d, u, nu) == H_INITCAP;
        arelease(&c->ar, m);
        clen[pos] = (uint8_t)cl;
        bits[pos] = (uint8_t)((skip ? NG_SKIP : 0) | (initcap ? NG_INITCAP : 0));
    }
    d->ng_order = order;
    d->ng_clen = clen;
    d->ng_bits = bits;
    d->ng_n = n;
    return 0;
}

/* s1[i:i+j] in s2 */
static inline int
u_contains(const uint16_t *s2, int l2, const uint16_t *g, int j)
{
    if (j == 0) return 1;
    if (j > l2) return 0;
    uint16_t g0 = g[0];
    for (int k = 0; k + j <= l2; k++) {
        if (s2[k] != g0) continue;
        int t = 1;
        while (t < j && s2[k + t] == g[t]) t++;
        if (t == j) return 1;
    }
    return 0;
}

/* SuggestMgr::ngram */
static int
ngram(int n, const uint16_t *s1, int l1, const uint16_t *s2, int l2, int opt)
{
    if (l2 == 0) return 0;
    int nscore = 0;
    int weighted = opt & 8;
    for (int j = 1; j <= n; j++) {
        int ns = 0;
        for (int i = 0; i < l1 - j + 1; i++) {
            if (u_contains(s2, l2, s1 + i, j)) {
                ns++;
            } else if (weighted) {
                ns--;
                if (i == 0 || i == l1 - j) ns--;
            }
        }
        nscore += ns;
        if (ns < 2 && !weighted) break;
    }
    int ns = 0;
    if (opt & 1) ns = (l2 - l1) - 2;
    if (opt & 2) ns = (l2 > l1 ? l2 - l1 : l1 - l2) - 2;
    return nscore - (ns > 0 ? ns : 0);
}

static int
lcslen(Ctx *c, const uint16_t *s, int m, const uint16_t *s2, int n)
{
    AMark mk = amark(&c->ar);
    int *prev = aalloc(&c->ar, sizeof(int) * ((size_t)n + 1));
    int *cur = aalloc(&c->ar, sizeof(int) * ((size_t)n + 1));
    for (int j = 0; j <= n; j++) prev[j] = 0;
    for (int i = 1; i <= m; i++) {
        cur[0] = 0;
        uint16_t a = s[i - 1];
        for (int j = 1; j <= n; j++) {
            if (a == s2[j - 1]) cur[j] = prev[j - 1] + 1;
            else if (prev[j] >= cur[j - 1]) cur[j] = prev[j];
            else cur[j] = cur[j - 1];
        }
        int *t = prev;
        prev = cur;
        cur = t;
    }
    int r = prev[n];
    arelease(&c->ar, mk);
    return r;
}

/* SuggestMgr::leftcommonsubstring (units) */
static int
leftcommon_u(HunDict *d, const uint16_t *su1, int l1, const uint16_t *su2, int l2)
{
    if (d->a_cpx) return (l1 && l2 && su1[l1 - 1] == su2[l2 - 1]) ? 1 : 0;
    uint16_t idx = l2 ? su2[0] : 0;
    uint16_t otheridx = l1 ? su1[0] : 0;
    if (otheridx != idx && otheridx != d->lower[idx]) return 0;
    int i = 1;
    while (i < l1 && i < l2 && su1[i] == su2[i]) i++;
    return i;
}

/* SuggestMgr::leftcommonsubstring for 8-bit encodings (bytes) */
static int
leftcommon_8bit(HunDict *d, const uint8_t *s1, int l1, const uint8_t *s2, int l2)
{
    if (d->a_cpx) return (l1 <= l2 && l1 && s2[l1 - 1] == s2[l2 - 1]) ? 1 : 0;
    if (d->h_utf8) return 0;
    int a = l1 ? s1[0] : 0;
    int b = l2 ? s2[0] : 0;
    if (a != b && a != d->lower[b]) return 0;
    int i = 1;
    while (i < l1 && i < l2 && s1[i] == s2[i]) i++;
    return i;
}

static void
commoncharacterpositions(Ctx *c, const uint8_t *s1, int n1, const uint8_t *s2, int n2, int *num_out, int *swap_out)
{
    HunDict *d = c->d;
    AMark m = amark(&c->ar);
    *num_out = 0;
    *swap_out = 0;
    if (d->h_utf8) {
        uint16_t *su1, *su2;
        int l1 = u8_u16(c, s1, n1, &su1);
        int l2 = u8_u16(c, s2, n2, &su2);
        int f1 = has_four_byte(s1, n1), f2 = has_four_byte(s2, n2);
        if ((f1 || f2) && ((f1 && l1 <= 1) || (f2 && l2 <= 1))) {
            arelease(&c->ar, m);
            return;
        }
        if (l1 <= 0 || l2 <= 0) {
            arelease(&c->ar, m);
            return;
        }
        if (d->a_cpx) su2[l2 - 1] = d->lower[su2[l2 - 1]];
        else su2[0] = d->lower[su2[0]];
        int num = 0, diff = 0, dp[2] = {0, 0};
        int mn = l1 < l2 ? l1 : l2;
        for (int i = 0; i < mn; i++) {
            if (su1[i] == su2[i]) {
                num++;
            } else {
                if (diff < 2) dp[diff] = i;
                diff++;
            }
        }
        *num_out = num;
        *swap_out = diff == 2 && l1 == l2 && su1[dp[0]] == su2[dp[1]] && su1[dp[1]] == su2[dp[0]];
        arelease(&c->ar, m);
        return;
    }
    uint16_t *t, *su1;
    int lt = to_units(c, s2, n2, d->a_utf8, &t);
    if (d->a_cpx) {
        if (lt) t[lt - 1] = d->lower[t[lt - 1]];
    } else {
        u_lower(d, t, lt);
    }
    int l1 = to_units(c, s1, n1, d->a_utf8, &su1);
    int num = 0, diff = 0, dp[2] = {0, 0};
    int i = 0;
    while (i < lt && i < l1) {
        if (su1[i] == t[i]) {
            num++;
        } else {
            if (diff < 2) dp[diff] = i;
            diff++;
        }
        i++;
    }
    *num_out = num;
    *swap_out = diff == 2 && i == l1 && i == lt && su1[dp[0]] == t[dp[1]] && su1[dp[1]] == t[dp[0]];
    arelease(&c->ar, m);
}

/* PfxEntry::add / SfxEntry::add: the length of the new word (0: none) */
static int
pfx_add(Ctx *c, const AffEntry *pe, const uint8_t *w, int n, const uint8_t **out)
{
    int sl = pe->strip_len;
    if ((n > sl || (n == 0 && c->d->fullstrip)) && n >= pe->numconds && pfx_test_condition(pe, w, n)
        && (!sl || (n >= sl && memcmp(w, pe->strip, (size_t)sl) == 0))) {
        *out = bcat(c, pe->appnd, pe->appnd_len, w + sl, n - sl);
        return pe->appnd_len + n - sl;
    }
    return 0;
}

static int
sfx_add(Ctx *c, const AffEntry *se, const uint8_t *w, int n, const uint8_t **out)
{
    int sl = se->strip_len;
    if ((n > sl || (n == 0 && c->d->fullstrip)) && n >= se->numconds && sfx_test_condition(se, w, n, n)
        && (!sl || (n >= sl && memcmp(w + n - sl, se->strip, (size_t)sl) == 0))) {
        *out = bcat(c, w, n - sl, se->appnd, se->appnd_len);
        return n - sl + se->appnd_len;
    }
    return 0;
}

typedef struct {
    const uint8_t *w;
    int n;
    int allow;
    const uint8_t *orig; /* NULL: None */
    int orign;
} Guess;

/* AffixMgr::expand_rootword (the words in the temporary arena) */
static int
expand_rootword(Ctx *c, Guess *wlst, int maxn, const uint8_t *ts, int tsn, int32_t e, const uint8_t *bad, int badl,
                const BStr *phon)
{
    HunDict *d = c->d;
    int nw = 0;
    const flag_t *ap = EFLAGS(d, e);
    int nap = ENFLAGS(d, e);
    flag_t needaffix = d->needaffix, oic = d->onlyincompound, circ = d->circumfix;
    if (nw < maxn && !(nap && ((needaffix != H_FLAG_NULL && flags_has(ap, nap, needaffix))
                               || (oic != H_FLAG_NULL && flags_has(ap, nap, oic))))) {
        wlst[nw].w = ts; wlst[nw].n = tsn; wlst[nw].allow = 0; wlst[nw].orig = NULL; wlst[nw].orign = 0;
        nw++;
        if (phon != NULL && nw < maxn) {
            wlst[nw].w = phon->s; wlst[nw].n = phon->n; wlst[nw].allow = 0; wlst[nw].orig = ts;
            wlst[nw].orign = tsn;
            nw++;
        }
    }
#define CONT_OK(x) (!((x)->ncont && ((needaffix != H_FLAG_NULL && CONT_HAS(x, needaffix)) \
                                      || (circ != H_FLAG_NULL && CONT_HAS(x, circ)) \
                                      || (oic != H_FLAG_NULL && CONT_HAS(x, oic)))))
    for (int fi = 0; fi < nap; fi++) {
        flag_t f = ap[fi];
        int b = f & 0xff;
        for (int k = 0; k < d->sflag_n[b]; k++) {
            const AffEntry *sp = &d->sent[d->sflag[b][k]];
            if (sp->aflag == f
                && (!sp->appnd_len || (badl > sp->appnd_len
                                       && memcmp(bad + badl - sp->appnd_len, sp->appnd, (size_t)sp->appnd_len) == 0))
                && CONT_OK(sp)) {
                const uint8_t *nwd;
                int nn = sfx_add(c, sp, ts, tsn, &nwd);
                if (nn && nw < maxn) {
                    wlst[nw].w = nwd; wlst[nw].n = nn; wlst[nw].allow = (sp->opts & AE_XPRODUCT) != 0;
                    wlst[nw].orig = NULL; wlst[nw].orign = 0;
                    nw++;
                    if (phon != NULL && nw < maxn) {
                        wlst[nw].w = bcat(c, phon->s, phon->n, sp->appnd, sp->appnd_len);
                        wlst[nw].n = phon->n + sp->appnd_len;
                        wlst[nw].allow = 0;
                        wlst[nw].orig = nwd;
                        wlst[nw].orign = nn;
                        nw++;
                    }
                }
            }
        }
    }
    int n = nw;
    for (int j = 1; j < n; j++) {
        if (!wlst[j].allow) continue;
        for (int fi = 0; fi < nap; fi++) {
            flag_t f = ap[fi];
            int b = f & 0xff;
            for (int k = 0; k < d->pflag_n[b]; k++) {
                const AffEntry *cp = &d->pent[d->pflag[b][k]];
                if (cp->aflag == f && (cp->opts & AE_XPRODUCT)
                    && (!cp->appnd_len || (badl > cp->appnd_len
                                           && memcmp(bad, cp->appnd, (size_t)cp->appnd_len) == 0))) {
                    const uint8_t *nwd;
                    int nn = pfx_add(c, cp, wlst[j].w, wlst[j].n, &nwd);
                    if (nn && nw < maxn) {
                        wlst[nw].w = nwd; wlst[nw].n = nn; wlst[nw].allow = (cp->opts & AE_XPRODUCT) != 0;
                        wlst[nw].orig = NULL; wlst[nw].orign = 0;
                        nw++;
                    }
                }
            }
        }
    }
    for (int fi = 0; fi < nap; fi++) {
        flag_t f = ap[fi];
        int b = f & 0xff;
        for (int k = 0; k < d->pflag_n[b]; k++) {
            const AffEntry *pp = &d->pent[d->pflag[b][k]];
            if (pp->aflag == f
                && (!pp->appnd_len || (badl > pp->appnd_len && memcmp(bad, pp->appnd, (size_t)pp->appnd_len) == 0))
                && CONT_OK(pp)) {
                const uint8_t *nwd;
                int nn = pfx_add(c, pp, ts, tsn, &nwd);
                if (nn && nw < maxn) {
                    wlst[nw].w = nwd; wlst[nw].n = nn; wlst[nw].allow = (pp->opts & AE_XPRODUCT) != 0;
                    wlst[nw].orig = NULL; wlst[nw].orign = 0;
                    nw++;
                }
            }
        }
    }
#undef CONT_OK
    return nw;
}

#define MAX_ROOTS 100
#define MAX_WORDS 100
#define MAX_GUESS 200

/* SuggestMgr::bubblesort */
static void
bubblesort(Guess *rword, int *rsc, int n)
{
    for (int m = 1; m < n; m++) {
        int j = m;
        while (j > 0) {
            if (rsc[j - 1] < rsc[j]) {
                int t = rsc[j - 1]; rsc[j - 1] = rsc[j]; rsc[j] = t;
                Guess g = rword[j - 1]; rword[j - 1] = rword[j]; rword[j] = g;
                j--;
            } else {
                break;
            }
        }
    }
}

/* bytes containment (prev in guess) */
static inline int
b_contains(const uint8_t *h, int hn, const uint8_t *nd, int nn)
{
    return py_find(h, hn, nd, nn, 0) != -1;
}

/* SuggestMgr::ngsuggest (without PHONE tables) */
static void
ngsuggest(Ctx *c, SList *wlst, const uint8_t *word, int nc, int captype)
{
    HunDict *d = c->d;
    AMark m0 = amark(&c->ar);
    int32_t roots[MAX_ROOTS];
    int scores[MAX_ROOTS];
    for (int i = 0; i < MAX_ROOTS; i++) {
        roots[i] = -1;
        scores[i] = -100 * i;
    }
    int lp = MAX_ROOTS - 1;
    int low = 1;
    if (d->a_cpx) nc = reverse_word(c, word, nc, d->h_utf8, &word);
    int nonbmp = 0;
    int utf8 = d->h_utf8;
    if (utf8 && has_four_byte(word, nc)) {
        utf8 = 0;
        nonbmp = 1;
        low = 0;
    }
    uint16_t *w_word;
    int n = utf8 ? u8_u16(c, word, nc, &w_word) : to_units(c, word, nc, 0, &w_word);
    ng_build(c);
    int de = d->h_langnum == H_LANG_de;
    int nocap_skip = captype == H_NOCAP && !de;
    double ng_deadline = 0;
    if (c->has_deadline) {
        double t = now_mono() + c->time_limit / 2;
        ng_deadline = c->deadline > t ? c->deadline : t;
    }
    uint64_t *posmask = NULL;
    if (n <= 64) {
        if (d->ng_pos == NULL) {
            d->ng_pos = calloc(65536, sizeof(uint64_t));
            if (d->ng_pos == NULL) longjmp(c->jb, 1);
        }
        posmask = d->ng_pos;
        d->ng_pos_dirty = 1;
        for (int i = 0; i < n; i++) posmask[w_word[i]] |= (uint64_t)1 << i;
    }
    uint16_t *fbuf = aalloc(&c->ar, sizeof(uint16_t) * 300);
    int fcap = 300;
    uint16_t *flbuf = aalloc(&c->ar, sizeof(uint16_t) * 300);
    long count = 0;
    for (int pos = 0; pos < d->ng_n; pos++) {
        if (!nonbmp) {
            int cl = d->ng_clen[pos];
            if (cl < n - 4 || cl > n + 4) continue;
        }
        if (c->has_deadline && !(count & 255) && now_mono() > ng_deadline) break;
        count++;
        int32_t e = d->ng_order[pos];
        int bits = d->ng_bits[pos];
        int32_t phon = d->ent[e].phon;
        if ((bits & NG_SKIP) || (nocap_skip && (bits & NG_INITCAP) && phon < 0)) continue;
        const uint8_t *ew = EWORD(d, e);
        int ewn = EWLEN(d, e);
        if (ewn > fcap) {
            fcap = ewn * 2;
            fbuf = aalloc(&c->ar, sizeof(uint16_t) * (size_t)fcap);
            flbuf = aalloc(&c->ar, sizeof(uint16_t) * (size_t)fcap);
        }
        int lf;
        int leftcommon;
        if (!utf8) {
            for (int i = 0; i < ewn; i++) fbuf[i] = ew[i];
            lf = ewn;
            leftcommon = leftcommon_8bit(d, word, nc, ew, ewn);
        } else {
            /* (u8_u16_raw with a fast path for ASCII) */
            lf = 0;
            while (lf < ewn && ew[lf] < 0x80) {
                fbuf[lf] = ew[lf];
                lf++;
            }
            if (lf < ewn) lf += u8_u16_raw(ew + lf, ewn - lf, fbuf + lf);
            if (d->a_cpx) {
                leftcommon = leftcommon_u(d, w_word, n, fbuf, lf);
            } else {
                /* first = w_word[:1], idx = f[:1] (strings: empty if the word is empty) */
                int same;
                if (lf == 0) same = n == 0;
                else if (n == 0) same = 0;
                else same = w_word[0] == fbuf[0] || w_word[0] == d->lower[fbuf[0]];
                if (!same) {
                    leftcommon = 0;
                } else {
                    int i = 1;
                    while (i < n && i < lf && w_word[i] == fbuf[i]) i++;
                    leftcommon = i;
                }
            }
        }
        int l2 = lf;
        const uint16_t *fl = fbuf;
        if (low && posmask == NULL) {
            for (int i = 0; i < lf; i++) flbuf[i] = d->lower[fbuf[i]];
            fl = flbuf;
        }
        int sc;
        if (l2 == 0) {
            sc = leftcommon;
        } else if (posmask != NULL) {
            /* bit i of posmask[x]: w_word[i] == x; the grams of w_word found in fl (the lowercase f) are the
             * bits of m1, m2, m3 */
            uint64_t m1 = 0, m2 = 0, m3 = 0, p1 = 0, p2 = 0;
            const uint16_t *lowt = low ? d->lower : NULL;
            for (int k = 0; k < l2; k++) {
                uint64_t pk = posmask[lowt != NULL ? lowt[fl[k]] : fl[k]];
                m1 |= pk;
                m2 |= p1 & (pk >> 1);
                m3 |= p2 & (p1 >> 1) & (pk >> 2);
                p2 = p1;
                p1 = pk;
            }
            int ns = popcount64(m1);
            int nscore = ns;
            if (ns >= 2) {
                ns = popcount64(m2);
                nscore += ns;
                if (ns >= 2) nscore += popcount64(m3);
            }
            int pen = l2 - n - 2;
            sc = nscore - (pen > 0 ? pen : 0) + leftcommon;
        } else {
            int ns = 0;
            for (int i = 0; i < n; i++) ns += u_contains(fl, l2, w_word + i, 1);
            int nscore = ns;
            if (ns >= 2) {
                ns = 0;
                for (int i = 0; i + 2 <= n; i++) ns += u_contains(fl, l2, w_word + i, 2);
                nscore += ns;
                if (ns >= 2) {
                    ns = 0;
                    for (int i = 0; i + 3 <= n; i++) ns += u_contains(fl, l2, w_word + i, 3);
                    nscore += ns;
                }
            }
            int pen = l2 - n - 2;
            sc = nscore - (pen > 0 ? pen : 0) + leftcommon;
        }
        if (phon >= 0) {
            AMark m = amark(&c->ar);
            const BStr *ph = &d->phon[phon];
            uint16_t *fu;
            int nfu = utf8 ? u8_u16(c, ph->s, ph->n, &fu) : to_units(c, ph->s, ph->n, 0, &fu);
            int lc2 = utf8 ? leftcommon_u(d, w_word, n, fu, nfu) : leftcommon_8bit(d, word, nc, ph->s, ph->n);
            if (low) u_lower(d, fu, nfu);
            int sc2 = ngram(3, w_word, n, fu, nfu, 1) + lc2;
            if (sc2 > sc) sc = sc2;
            arelease(&c->ar, m);
        }
        if (sc > scores[lp]) {
            scores[lp] = sc;
            roots[lp] = e;
            int lval = sc;
            for (int j = 0; j < MAX_ROOTS; j++) {
                if (scores[j] < lval) {
                    lp = j;
                    lval = scores[j];
                }
            }
        }
    }
    if (posmask != NULL) {
        for (int i = 0; i < n; i++) posmask[w_word[i]] = 0;
        d->ng_pos_dirty = 0;
    }
    /* the minimum threshold for a passable suggestion */
    int thresh = 0;
    {
        uint16_t *mw = aalloc(&c->ar, sizeof(uint16_t) * ((size_t)n + 1));
        for (int sp = 1; sp < 4; sp++) {
            memcpy(mw, w_word, sizeof(uint16_t) * (size_t)n);
            for (int k = sp; k < n; k += 4) mw[k] = '*';
            if (low) u_lower(d, mw, n);
            thresh += ngram(n, w_word, n, mw, n, 2);
        }
        thresh = thresh / 3;
        thresh -= 1;
    }
    /* expand the affixes of the roots */
    Guess guess[MAX_GUESS];
    int gscore[MAX_GUESS];
    for (int i = 0; i < MAX_GUESS; i++) {
        guess[i].w = NULL;
        guess[i].n = 0;
        guess[i].orig = NULL;
        guess[i].orign = 0;
        gscore[i] = -100 * i;
    }
    lp = MAX_GUESS - 1;
    Guess *glst = aalloc(&c->ar, sizeof(Guess) * MAX_WORDS);
    for (int i = 0; i < MAX_ROOTS; i++) {
        int32_t rp = roots[i];
        if (rp < 0) continue;
        const BStr *field = d->ent[rp].phon >= 0 ? &d->phon[d->ent[rp].phon] : NULL;
        int ng = expand_rootword(c, glst, MAX_WORDS, EWORD(d, rp), EWLEN(d, rp), rp, word, nc, field);
        for (int g = 0; g < ng; g++) {
            AMark m = amark(&c->ar);
            uint16_t *w_f;
            int nf, sc, leftcommon;
            if (utf8) {
                nf = u8_u16(c, glst[g].w, glst[g].n, &w_f);
                leftcommon = leftcommon_u(d, w_word, n, w_f, nf);
                if (low) u_lower(d, w_f, nf);
            } else {
                nf = to_units(c, glst[g].w, glst[g].n, 0, &w_f);
                leftcommon = nonbmp ? 0 : leftcommon_8bit(d, word, nc, glst[g].w, glst[g].n);
                if (low) u_lower(d, w_f, nf);
            }
            sc = ngram(n, w_word, n, w_f, nf, 2) + leftcommon;
            arelease(&c->ar, m);
            if (sc > thresh && sc > gscore[lp]) {
                gscore[lp] = sc;
                guess[lp] = glst[g]; /* (the strings stay in the arena until the end) */
                int lval = sc;
                for (int j = 0; j < MAX_GUESS; j++) {
                    if (gscore[j] < lval) {
                        lp = j;
                        lval = gscore[j];
                    }
                }
            }
        }
    }
    bubblesort(guess, gscore, MAX_GUESS);
    /* weight the suggestions with a similarity index (longest common subsequence) */
    double fact = 1.0;
    if (d->maxdiff >= 0) fact = (10.0 - d->maxdiff) / 5.0;
    uint16_t *w_word_low = udup(c, w_word, n);
    u_lower(d, w_word_low, n);
    for (int i = 0; i < MAX_GUESS; i++) {
        if (guess[i].w == NULL) continue;
        AMark m = amark(&c->ar);
        uint16_t *w_gl;
        int nwgl, glen, lcs;
        const uint8_t *gl;
        int gln;
        if (utf8) {
            nwgl = u8_u16(c, guess[i].w, guess[i].n, &w_gl);
            u_lower(d, w_gl, nwgl);
            glen = nwgl;
            if (has_four_byte(guess[i].w, guess[i].n)) glen = -1;
            uint8_t *glb;
            gln = u16_u8(c, w_gl, nwgl, &glb);
            gl = glb;
            lcs = lcslen(c, w_word, n, w_gl, nwgl);
        } else {
            gl = guess[i].w;
            gln = guess[i].n;
            if (!nonbmp) {
                uint16_t *gu;
                int ngu = to_units(c, gl, gln, d->a_utf8, &gu);
                u_lower(d, gu, ngu);
                uint8_t *glb;
                gln = from_units(c, gu, ngu, d->a_utf8, &glb);
                gl = glb;
            }
            glen = guess[i].n;
            nwgl = to_units(c, gl, gln, 0, &w_gl);
            lcs = lcslen(c, w_word, n, w_gl, nwgl);
        }
        if (n == glen && n == lcs) {
            gscore[i] += 2000;
            arelease(&c->ar, m);
            break;
        }
        int re = ngram(2, w_word, n, w_gl, nwgl, 2 | 8);
        if (low) re += ngram(2, w_gl, nwgl, w_word_low, n, 2 | 8);
        else re += ngram(2, w_gl, nwgl, w_word, n, 2 | 8);
        int ngram_score = ngram(4, w_word, n, w_gl, nwgl, 2);
        int leftcommon_score;
        if (utf8) leftcommon_score = leftcommon_u(d, w_word, n, w_gl, nwgl);
        else leftcommon_score = nonbmp ? 0 : leftcommon_8bit(d, word, nc, gl, gln);
        int ccp = 0, is_swap = 0;
        if (!nonbmp) commoncharacterpositions(c, word, nc, gl, gln, &ccp, &is_swap);
        int dl = n - glen;
        if (dl < 0) dl = -dl;
        gscore[i] = 2 * lcs - dl + leftcommon_score + (ccp ? 1 : 0) + (is_swap ? 10 : 0) + ngram_score + re
                    + ((double)re < (double)(n + glen) * fact ? -1000 : 0);
        arelease(&c->ar, m);
    }
    bubblesort(guess, gscore, MAX_GUESS);
    /* copy over */
    int oldns = wlst->n;
    int same = 0;
    for (int i = 0; i < MAX_GUESS; i++) {
        if (guess[i].w == NULL) continue;
        if (wlst->n < oldns + d->s_maxngramsugs && wlst->n < d->maxsug && (!same || gscore[i] > 1000)) {
            int unique = 1;
            if (gscore[i] > 1000) {
                same = 1;
            } else if (gscore[i] < -100) {
                same = 1;
                if (wlst->n > oldns || d->onlymaxdiff) continue;
            }
            for (int k = 0; k < wlst->n; k++) {
                const BStr *prev = &wlst->v[k];
                if ((guess[i].orig == NULL && b_contains(guess[i].w, guess[i].n, prev->s, prev->n))
                    || (guess[i].orig != NULL && b_contains(guess[i].orig, guess[i].orign, prev->s, prev->n))
                    || !sug_checkword_tmp(c, guess[i].w, guess[i].n, 0)) {
                    unique = 0;
                    break;
                }
            }
            if (unique) {
                if (guess[i].orig != NULL) sl_append(c, wlst, guess[i].orig, guess[i].orign);
                else sl_append(c, wlst, guess[i].w, guess[i].n);
            }
        }
    }
    arelease(&c->ar, m0);
}

/* ------------------------------------------------------------------------ */
/* HunspellImpl::suggest */

static int
mkinitcap_b(Ctx *c, const uint8_t *b, int n, const uint8_t **out)
{
    uint16_t *u;
    int nu = to_units(c, b, n, c->d->a_utf8, &u);
    if (nu) u[0] = c->d->upper[u[0]];
    uint8_t *r;
    int rn = from_units(c, u, nu, c->d->a_utf8, &r);
    *out = r;
    return rn;
}

static int
mkallcap_b(Ctx *c, const uint8_t *b, int n, const uint8_t **out)
{
    uint16_t *u;
    int nu = to_units(c, b, n, c->d->a_utf8, &u);
    u_upper(c->d, u, nu);
    uint8_t *r;
    int rn = from_units(c, u, nu, c->d->a_utf8, &r);
    *out = r;
    return rn;
}

static int
spell_top(Ctx *c, const uint8_t *w, int n)
{
    return spell_rec(c, w, n, NULL);
}

typedef struct {
    int capwords, abbv, captype;
} SugInfo;

static void hsuggest(Ctx *c, const uint8_t *word, int wn, SList *out);

static void
suggest_internal(Ctx *c, const uint8_t *word, int wn, SList *slst, SugInfo *si)
{
    HunDict *d = c->d;
    si->captype = H_NOCAP;
    si->abbv = 0;
    si->capwords = 0;
    int onlycmpdsug = 0;
    if (wn >= 5 && memcmp(word, "<?xml", 5) == 0) return;
    if (wn >= (d->h_utf8 ? H_MAXWORDUTF8LEN : H_MAXWORDLEN)) return;
    if (d->iconv.n >= 0) {
        const uint8_t *cv;
        int cn = rep_conv(c, &d->iconv, word, wn, &cv);
        if (cn >= 0) {
            word = cv;
            wn = cn;
        }
    }
    WordU s;
    int captype = cleanword2(c, word, wn, &s, &si->abbv);
    si->captype = captype;
    if (!s.n) return;
    const uint8_t *scw = s.w;
    int wl = s.n;
    int good = 0;
    if (captype == H_NOCAP && d->forceucase != H_FLAG_NULL) {
        int info = SPELL_ORIGCAP;
        if (checkword(c, scw, wl, &info) >= 0) {
            const uint8_t *b;
            int bn = mkinitcap_b(c, scw, wl, &b);
            sl_append(c, slst, b, bn);
            return;
        }
    }
    if (captype == H_NOCAP) {
        good |= sm_suggest(c, slst, scw, wl, &onlycmpdsug);
        if (si->abbv) good |= sm_suggest(c, slst, bcat(c, scw, wl, (const uint8_t *)".", 1), wl + 1, &onlycmpdsug);
    } else if (captype == H_INITCAP) {
        si->capwords = 1;
        good |= sm_suggest(c, slst, scw, wl, &onlycmpdsug);
        mkallsmall2(c, &s);
        good |= sm_suggest(c, slst, s.w, s.n, &onlycmpdsug);
    } else if (captype == H_HUHINITCAP || captype == H_HUHCAP) {
        if (captype == H_HUHINITCAP) si->capwords = 1;
        good |= sm_suggest(c, slst, scw, wl, &onlycmpdsug);
        int dot_pos = py_find(scw, wl, (const uint8_t *)".", 1, 0);
        if (dot_pos != -1) {
            uint16_t *pu;
            int npu = to_units(c, scw + dot_pos + 1, wl - dot_pos - 1, d->a_utf8, &pu);
            if (npu && captype_units(d, pu, npu) == H_INITCAP) {
                uint8_t *nw = bcat3(c, scw, dot_pos + 1, (const uint8_t *)" ", 1, scw + dot_pos + 1, wl - dot_pos - 1);
                sl_insert0(c, slst, nw, wl + 1);
            }
        }
        if (captype == H_HUHINITCAP) {
            uint16_t *u = udup(c, s.u, s.nu);
            if (s.nu) u[0] = d->lower[u[0]];
            s.u = u;
            uint8_t *b;
            int bn = from_units(c, u, s.nu, d->a_utf8, &b);
            good |= sm_suggest(c, slst, b, bn, &onlycmpdsug);
        }
        mkallsmall2(c, &s);
        if (spell_top(c, s.w, s.n)) sl_insert0(c, slst, s.w, s.n);
        int prevns = slst->n;
        good |= sm_suggest(c, slst, s.w, s.n, &onlycmpdsug);
        if (captype == H_HUHINITCAP) {
            mkinitcap2(c, &s);
            if (spell_top(c, s.w, s.n)) sl_insert0(c, slst, s.w, s.n);
            good |= sm_suggest(c, slst, s.w, s.n, &onlycmpdsug);
        }
        int j = prevns;
        while (j < slst->n) {
            BStr x = slst->v[j];
            int sp = py_find(x.s, x.n, (const uint8_t *)" ", 1, 0);
            if (sp != -1) {
                const uint8_t *second = x.s + sp + 1;
                int slen = x.n - sp - 1;
                if (slen < wl && memcmp(scw + wl - slen, second, (size_t)slen) != 0) {
                    const uint8_t *sc2;
                    int sc2n = mkinitcap_b(c, second, slen, &sc2);
                    uint8_t *nw = bcat(c, x.s, sp + 1, sc2, sc2n);
                    sl_del(slst, j);
                    sl_insert0(c, slst, nw, sp + 1 + sc2n);
                }
            }
            j++;
        }
    } else if (captype == H_ALLCAP) {
        mkallsmall2(c, &s);
        good |= sm_suggest(c, slst, s.w, s.n, &onlycmpdsug);
        if (d->keepcase != H_FLAG_NULL && spell_top(c, s.w, s.n)) sl_insert0(c, slst, s.w, s.n);
        mkinitcap2(c, &s);
        good |= sm_suggest(c, slst, s.w, s.n, &onlycmpdsug);
        for (int j = 0; j < slst->n; j++) {
            const uint8_t *b;
            int bn = mkallcap_b(c, slst->v[j].s, slst->v[j].n, &b);
            if (d->checksharps) {
                /* s.replace(sharp s, b'SS') */
                const uint8_t *sharp = d->h_utf8 ? (const uint8_t *)"\xc3\x9f" : (const uint8_t *)"\xdf";
                int sl = d->h_utf8 ? 2 : 1;
                TBuf t = {NULL, 0, 0};
                int i = 0;
                for (;;) {
                    int f = py_find(b, bn, sharp, sl, i);
                    if (f < 0) break;
                    tb_append(c, &t, b + i, f - i);
                    tb_append(c, &t, (const uint8_t *)"SS", 2);
                    i = f + sl;
                }
                tb_append(c, &t, b + i, bn - i);
                b = t.p;
                bn = t.n;
            }
            slst->v[j] = keep_str(c, b, bn);
        }
    }
    /* try the ngram approach since nothing good was found */
    if (!good && (!slst->n || onlycmpdsug) && d->maxngramsugs != 0) {
        uint16_t *lu = udup(c, s.u, s.nu);
        u_lower(d, lu, s.nu);
        uint8_t *wsp;
        int wspn = from_units(c, lu, s.nu, d->a_utf8, &wsp);
        if (captype == H_NOCAP) {
            ngsuggest(c, slst, scw, wl, H_NOCAP);
        } else if (captype == H_HUHINITCAP || captype == H_HUHCAP) {
            if (captype == H_HUHINITCAP) si->capwords = 1;
            ngsuggest(c, slst, wsp, wspn, H_HUHCAP);
        } else if (captype == H_INITCAP) {
            si->capwords = 1;
            ngsuggest(c, slst, wsp, wspn, H_INITCAP);
        } else if (captype == H_ALLCAP) {
            int oldns = slst->n;
            ngsuggest(c, slst, wsp, wspn, H_ALLCAP);
            for (int j = oldns; j < slst->n; j++) {
                const uint8_t *b;
                int bn = mkallcap_b(c, slst->v[j].s, slst->v[j].n, &b);
                slst->v[j] = keep_str(c, b, bn);
            }
        }
    }
    /* try the dash suggestion (Afo-American -> Afro-American) */
    int dash_pos = py_find(scw, wl, (const uint8_t *)"-", 1, 0);
    if (dash_pos != -1) {
        int nodashsug = 1;
        for (int k = 0; k < slst->n; k++)
            if (memchr(slst->v[k].s, '-', (size_t)slst->v[k].n) != NULL) {
                nodashsug = 0;
                break;
            }
        int prev_pos = 0;
        int last = 0;
        while (!good && nodashsug && !last) {
            if (dash_pos == wl) last = 1;
            const uint8_t *chunk = scw + prev_pos;
            int chn = dash_pos - prev_pos;
            if (chn < 0) chn = 0;
            if (!spell_top(c, chunk, chn)) {
                SList nlst = {NULL, 0, 0};
                hsuggest(c, chunk, chn, &nlst);
                for (int k = nlst.n - 1; k >= 0; k--) {
                    BStr x = nlst.v[k];
                    uint8_t *wsp;
                    int wspn;
                    if (!last) {
                        int rest = wl - dash_pos - 1;
                        if (rest < 0) rest = 0;
                        wsp = aalloc(&c->ar, (size_t)prev_pos + x.n + 1 + rest + 1);
                        memcpy(wsp, scw, (size_t)prev_pos);
                        memcpy(wsp + prev_pos, x.s, (size_t)x.n);
                        wsp[prev_pos + x.n] = '-';
                        memcpy(wsp + prev_pos + x.n + 1, scw + dash_pos + 1, (size_t)rest);
                        wspn = prev_pos + x.n + 1 + rest;
                    } else {
                        wsp = bcat(c, scw, prev_pos, x.s, x.n);
                        wspn = prev_pos + x.n;
                    }
                    int info = 0;
                    if (d->a_forbidden != H_FLAG_NULL) {
                        AMark m = amark(&c->ar);
                        checkword(c, wsp, wspn, &info);
                        arelease(&c->ar, m);
                    }
                    if (!(info & SPELL_FORBIDDEN)) sl_insert0(c, slst, wsp, wspn);
                }
                nodashsug = 0;
            }
            if (!last) {
                prev_pos = dash_pos + 1;
                dash_pos = py_find(scw, wl, (const uint8_t *)"-", 1, prev_pos);
            }
            if (dash_pos == -1) dash_pos = wl;
        }
    }
}

static void
hsuggest(Ctx *c, const uint8_t *word, int wn, SList *out)
{
    HunDict *d = c->d;
    AMark m = amark(&c->ar);
    SList slst = {NULL, 0, 0};
    SugInfo si;
    suggest_internal(c, word, wn, &slst, &si);
    if (d->a_cpx) {
        for (int k = 0; k < slst.n; k++) {
            const uint8_t *r;
            int rn = reverse_word(c, slst.v[k].s, slst.v[k].n, d->h_utf8, &r);
            slst.v[k] = keep_str(c, r, rn);
        }
    }
    if (si.capwords) {
        for (int k = 0; k < slst.n; k++) {
            const uint8_t *r;
            int rn = mkinitcap_b(c, slst.v[k].s, slst.v[k].n, &r);
            slst.v[k] = keep_str(c, r, rn);
        }
    }
    if (si.abbv && d->sugswithdots) {
        for (int k = 0; k < slst.n; k++) {
            uint8_t *r = bcat(c, slst.v[k].s, slst.v[k].n, word + wn - si.abbv, si.abbv);
            slst.v[k] = keep_str(c, r, slst.v[k].n + si.abbv);
        }
    }
    /* remove bad capitalized and forbidden forms */
    if (d->keepcase != H_FLAG_NULL || d->a_forbidden != H_FLAG_NULL) {
        if (si.captype == H_INITCAP || si.captype == H_ALLCAP) {
            SList kept = {NULL, 0, 0};
            for (int k = 0; k < slst.n; k++) {
                BStr x = slst.v[k];
                if (memchr(x.s, ' ', (size_t)x.n) == NULL && !spell_top(c, x.s, x.n)) {
                    uint16_t *u;
                    int nu = to_units(c, x.s, x.n, d->a_utf8, &u);
                    u_lower(d, u, nu);
                    uint8_t *s2;
                    int s2n = from_units(c, u, nu, d->a_utf8, &s2);
                    if (spell_top(c, s2, s2n)) {
                        sl_append(c, &kept, s2, s2n);
                    } else {
                        if (nu) u[0] = d->upper[u[0]];
                        s2n = from_units(c, u, nu, d->a_utf8, &s2);
                        if (spell_top(c, s2, s2n)) sl_append(c, &kept, s2, s2n);
                    }
                } else {
                    sl_reserve(c, &kept, kept.n + 1);
                    kept.v[kept.n++] = x;
                }
            }
            slst = kept;
        }
    }
    /* remove duplications */
    for (int k = 0; k < slst.n; k++) {
        if (sl_contains(out, slst.v[k].s, slst.v[k].n)) continue;
        sl_reserve(c, out, out->n + 1);
        out->v[out->n++] = slst.v[k];
    }
    /* output conversion */
    if (d->oconv.n >= 0) {
        for (int k = 0; k < out->n; k++) {
            const uint8_t *cv;
            int cn = rep_conv(c, &d->oconv, out->v[k].s, out->v[k].n, &cv);
            if (cn > 0) out->v[k] = keep_str(c, cv, cn);
        }
    }
    arelease(&c->ar, m);
}

/* suggest(word: bytes, time_limit: float or None) -> list of bytes */
static PyObject *
HunDict_suggest(HunDict *d, PyObject *args)
{
    PyObject *wo, *tlo = Py_None;
    int no_prune = 0;
    if (!PyArg_ParseTuple(args, "O|Op", &wo, &tlo, &no_prune)) return NULL;
    const uint8_t *w;
    int n;
    if (check_ready(d) < 0 || get_word_arg(wo, &w, &n) < 0) return NULL;
    if (n >= H_MAXWORDUTF8LEN && n >= H_MAXWORDLEN) return PyList_New(0); /* (suggest_internal: too long) */
    double tl = 0;
    if (tlo != Py_None) {
        tl = PyFloat_AsDouble(tlo);
        if (tl == -1.0 && PyErr_Occurred()) return NULL;
    }
    Ctx c;
    ctx_init(&c, d);
    c.no_map_prune = no_prune;
    c.memo = calloc(1, sizeof(Memo));
    if (c.memo == NULL) return PyErr_NoMemory();
    if (tlo != Py_None) {
        c.has_deadline = 1;
        c.time_limit = tl;
        c.deadline = now_mono() + tl;
    }
    d->busy = 1;
    SList out = {NULL, 0, 0};
    /* (the word: a copy, the GIL is released) */
    uint8_t *wc = malloc((size_t)n + 1);
    if (wc == NULL) {
        d->busy = 0;
        ctx_free(&c);
        return PyErr_NoMemory();
    }
    memcpy(wc, w, (size_t)n);
    PyThreadState *volatile ts = NULL;
    if (setjmp(c.jb)) {
        if (ts != NULL) PyEval_RestoreThread(ts);
        d->busy = 0;
        ctx_free(&c);
        free(wc);
        return PyErr_NoMemory();
    }
    /* the search only uses the C data: other threads can run meanwhile (the
     * dictionary itself is protected by the busy flag and the lock of the
     * Python object) */
    ts = PyEval_SaveThread();
    hsuggest(&c, wc, n, &out);
    PyEval_RestoreThread(ts);
    ts = NULL;
    free(wc);
    d->busy = 0;
    PyObject *res = PyList_New(out.n);
    if (res != NULL) {
        for (int k = 0; k < out.n; k++) {
            PyObject *b = PyBytes_FromStringAndSize((const char *)out.v[k].s, out.v[k].n);
            if (b == NULL) {
                Py_CLEAR(res);
                break;
            }
            PyList_SET_ITEM(res, k, b);
        }
    }
    ctx_free(&c);
    return res;
}

/* ------------------------------------------------------------------------ */
/* the Python type */

static void
ctx_init(Ctx *c, HunDict *d)
{
    memset(c, 0, sizeof(*c));
    c->d = d;
    c->ar.jb = &c->jb;
    c->keep.jb = &c->jb;
    SET_PFX(c, -1);
    SET_SFX(c, -1);
}

static void
ctx_free(Ctx *c)
{
    afree(&c->ar);
    afree(&c->keep);
    memo_free(c->memo);
    c->memo = NULL;
    if (c->d->ng_pos_dirty) {
        /* (after a memory error in the ngram scan) */
        memset(c->d->ng_pos, 0, 65536 * sizeof(uint64_t));
        c->d->ng_pos_dirty = 0;
    }
}

static void *
dblob(HunDict *d, size_t size)
{
    if (d->nblobs == d->cblobs) {
        int nc = d->cblobs ? d->cblobs * 2 : 64;
        uint8_t **nb = realloc(d->blobs, sizeof(uint8_t *) * (size_t)nc);
        if (nb == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        d->blobs = nb;
        d->cblobs = nc;
    }
    void *p = calloc(1, size ? size : 1);
    if (p == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    d->blobs[d->nblobs++] = p;
    return p;
}

static PyObject *
cfg_item(PyObject *cfg, const char *k)
{
    PyObject *v = PyDict_GetItemString(cfg, k);
    if (v == NULL && !PyErr_Occurred()) PyErr_Format(PyExc_KeyError, "HunDict config: %s", k);
    return v;
}

static int
cfg_long(PyObject *cfg, const char *k, long *out)
{
    PyObject *v = cfg_item(cfg, k);
    if (v == NULL) return -1;
    if (PyBool_Check(v)) {
        *out = v == Py_True;
        return 0;
    }
    long x = PyLong_AsLong(v);
    if (x == -1 && PyErr_Occurred()) return -1;
    *out = x;
    return 0;
}

static int
cfg_intv(PyObject *cfg, const char *k, int *out)
{
    long x;
    if (cfg_long(cfg, k, &x) < 0) return -1;
    if (x > INT32_MAX) x = INT32_MAX;
    if (x < INT32_MIN) x = INT32_MIN;
    *out = (int)x;
    return 0;
}

static int
cfg_flagv(PyObject *cfg, const char *k, flag_t *out)
{
    long x;
    if (cfg_long(cfg, k, &x) < 0) return -1;
    if (x < 0 || x > 0xffff) {
        PyErr_Format(PyExc_ValueError, "HunDict config: bad flag %s", k);
        return -1;
    }
    *out = (flag_t)x;
    return 0;
}

static int
obj_bytes(HunDict *d, PyObject *v, BStr *out)
{
    if (!PyBytes_Check(v)) {
        PyErr_SetString(PyExc_TypeError, "HunDict config: bytes expected");
        return -1;
    }
    Py_ssize_t n = PyBytes_GET_SIZE(v);
    if (n > INT32_MAX / 4) {
        PyErr_SetString(PyExc_ValueError, "HunDict config: string too long");
        return -1;
    }
    uint8_t *p = dblob(d, (size_t)n + 1);
    if (p == NULL) return -1;
    memcpy(p, PyBytes_AS_STRING(v), (size_t)n);
    out->s = p;
    out->n = (int)n;
    return 0;
}

static int
cfg_bytes(HunDict *d, PyObject *cfg, const char *k, BStr *out)
{
    PyObject *v = cfg_item(cfg, k);
    if (v == NULL) return -1;
    return obj_bytes(d, v, out);
}

/* a str of BMP characters as an array of units (flags) */
static int
obj_units(HunDict *d, PyObject *v, uint16_t **out, int *n, int sort)
{
    if (!PyUnicode_Check(v)) {
        PyErr_SetString(PyExc_TypeError, "HunDict config: str expected");
        return -1;
    }
    Py_ssize_t len = PyUnicode_GET_LENGTH(v);
    if (len > 65535) {
        PyErr_SetString(PyExc_ValueError, "HunDict config: str too long");
        return -1;
    }
    uint16_t *u = dblob(d, sizeof(uint16_t) * ((size_t)len + 1));
    if (u == NULL) return -1;
    int kind = PyUnicode_KIND(v);
    const void *data = PyUnicode_DATA(v);
    for (Py_ssize_t i = 0; i < len; i++) {
        Py_UCS4 ch = PyUnicode_READ(kind, data, i);
        if (ch > 0xffff) {
            PyErr_SetString(PyExc_ValueError, "HunDict config: character outside the BMP");
            return -1;
        }
        u[i] = (uint16_t)ch;
    }
    if (sort) sort_flags(u, (int)len);
    *out = u;
    *n = (int)len;
    return 0;
}

static int
cfg_units(HunDict *d, PyObject *cfg, const char *k, uint16_t **out, int *n, int sort)
{
    PyObject *v = cfg_item(cfg, k);
    if (v == NULL) return -1;
    return obj_units(d, v, out, n, sort);
}

static int
cfg_table(HunDict *d, PyObject *cfg, const char *k, uint16_t **out)
{
    PyObject *v = cfg_item(cfg, k);
    if (v == NULL) return -1;
    if (!PyBytes_Check(v) || PyBytes_GET_SIZE(v) != 65536 * 2) {
        PyErr_Format(PyExc_ValueError, "HunDict config: bad table %s", k);
        return -1;
    }
    uint16_t *t = dblob(d, 65536 * 2);
    if (t == NULL) return -1;
    memcpy(t, PyBytes_AS_STRING(v), 65536 * 2);
    *out = t;
    return 0;
}

/* a list of [pattern, [out0, out1, out2, out3]] (or None: n = -1) */
static int
obj_reptable(HunDict *d, PyObject *v, RepTable *t)
{
    if (v == Py_None) {
        t->v = NULL;
        t->n = -1;
        return 0;
    }
    PyObject *seq = PySequence_Fast(v, "HunDict config: a list of REP entries expected");
    if (seq == NULL) return -1;
    Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
    t->v = dblob(d, sizeof(RepEntry) * ((size_t)n + 1));
    if (t->v == NULL) goto error;
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *e = PySequence_Fast_GET_ITEM(seq, i);
        PyObject *outs;
        PyObject *pat;
        if (!PySequence_Check(e) || PySequence_Size(e) != 2) {
            PyErr_SetString(PyExc_TypeError, "HunDict config: bad REP entry");
            goto error;
        }
        pat = PySequence_GetItem(e, 0);
        outs = PySequence_GetItem(e, 1);
        int bad = pat == NULL || outs == NULL || obj_bytes(d, pat, &t->v[i].pat) < 0;
        if (!bad) {
            if (!PySequence_Check(outs) || PySequence_Size(outs) != 4) {
                PyErr_SetString(PyExc_TypeError, "HunDict config: bad REP entry");
                bad = 1;
            }
            for (int k = 0; k < 4 && !bad; k++) {
                PyObject *o = PySequence_GetItem(outs, k);
                if (o == NULL || obj_bytes(d, o, &t->v[i].out[k]) < 0) bad = 1;
                Py_XDECREF(o);
            }
        }
        Py_XDECREF(pat);
        Py_XDECREF(outs);
        if (bad) goto error;
    }
    t->n = (int)n;
    Py_DECREF(seq);
    return 0;
error:
    Py_DECREF(seq);
    return -1;
}

static int
obj_affixes(HunDict *d, PyObject *v, AffEntry **out, int *nout)
{
    PyObject *seq = PySequence_Fast(v, "HunDict config: a list of affix entries expected");
    if (seq == NULL) return -1;
    Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
    AffEntry *a = dblob(d, sizeof(AffEntry) * ((size_t)n + 1));
    PyObject *strips = PyDict_New(); /* strip -> the index of its first entry (equal strips share the string) */
    if (a == NULL || strips == NULL) {
        Py_XDECREF(strips);
        goto error;
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *t = PySequence_Fast_GET_ITEM(seq, i);
        PyObject *appnd, *strip, *conds, *cont, *key;
        long aflag, opts, numconds, next, nexteq, nextne;
        int utf8;
        if (!PyArg_ParseTuple(t, "OOllOlOOlllp", &appnd, &strip, &aflag, &opts, &conds, &numconds, &cont, &key,
                              &next, &nexteq, &nextne, &utf8))
            goto error_s;
        AffEntry *e = &a[i];
        BStr b;
        if (obj_bytes(d, appnd, &b) < 0) goto error_s;
        e->appnd = b.s; e->appnd_len = b.n;
        PyObject *first = PyDict_GetItemWithError(strips, strip);
        if (first != NULL) {
            Py_ssize_t k = PyLong_AsSsize_t(first);
            e->strip = a[k].strip; e->strip_len = a[k].strip_len;
        } else {
            if (PyErr_Occurred()) goto error_s;
            if (obj_bytes(d, strip, &b) < 0) goto error_s;
            e->strip = b.s; e->strip_len = b.n;
            PyObject *ix = PyLong_FromSsize_t(i);
            if (ix == NULL || PyDict_SetItem(strips, strip, ix) < 0) {
                Py_XDECREF(ix);
                goto error_s;
            }
            Py_DECREF(ix);
        }
        if (obj_bytes(d, conds, &b) < 0) goto error_s;
        e->conds = b.s; e->conds_len = b.n;
        if (obj_bytes(d, key, &b) < 0) goto error_s;
        e->key = b.s; e->key_len = b.n;
        e->key_dot = memchr(e->key, '.', (size_t)e->key_len) != NULL;
        uint16_t *cu;
        int cn;
        if (obj_units(d, cont, &cu, &cn, 1) < 0) goto error_s;
        e->cont = cu; e->ncont = cn;
        if (aflag < 0 || aflag > 0xffff || next < -1 || next >= n || nexteq < -1 || nexteq >= n || nextne < -1
            || nextne >= n || numconds < 0 || (numconds > 0 && e->conds_len == 0)) {
            PyErr_SetString(PyExc_ValueError, "HunDict config: bad affix entry");
            goto error_s;
        }
        e->aflag = (flag_t)aflag;
        e->opts = (int)opts;
        e->numconds = (int)numconds;
        e->next = (int32_t)next;
        e->nexteq = (int32_t)nexteq;
        e->nextne = (int32_t)nextne;
        e->utf8 = utf8;
    }
    Py_DECREF(strips);
    *out = a;
    *nout = (int)n;
    Py_DECREF(seq);
    return 0;
error_s:
    Py_DECREF(strips);
error:
    Py_DECREF(seq);
    return -1;
}

static int
obj_index_list(HunDict *d, PyObject *v, int32_t *out, int n, int limit)
{
    PyObject *seq = PySequence_Fast(v, "HunDict config: a list expected");
    if (seq == NULL) return -1;
    if (PySequence_Fast_GET_SIZE(seq) != n) {
        Py_DECREF(seq);
        PyErr_SetString(PyExc_ValueError, "HunDict config: bad list length");
        return -1;
    }
    for (int i = 0; i < n; i++) {
        long x = PyLong_AsLong(PySequence_Fast_GET_ITEM(seq, i));
        if (x == -1 && PyErr_Occurred()) {
            Py_DECREF(seq);
            return -1;
        }
        if (x < -1 || x >= limit) {
            Py_DECREF(seq);
            PyErr_SetString(PyExc_ValueError, "HunDict config: index out of range");
            return -1;
        }
        out[i] = (int32_t)x;
    }
    Py_DECREF(seq);
    (void)d;
    return 0;
}

/* 256 lists of affix indices */
static int
obj_flag_lists(HunDict *d, PyObject *v, int32_t ***out, int **nout, int limit)
{
    PyObject *seq = PySequence_Fast(v, "HunDict config: a list expected");
    if (seq == NULL) return -1;
    if (PySequence_Fast_GET_SIZE(seq) != 256) {
        Py_DECREF(seq);
        PyErr_SetString(PyExc_ValueError, "HunDict config: 256 lists expected");
        return -1;
    }
    int32_t **lists = dblob(d, sizeof(int32_t *) * 256);
    int *ns = dblob(d, sizeof(int) * 256);
    if (lists == NULL || ns == NULL) {
        Py_DECREF(seq);
        return -1;
    }
    for (int k = 0; k < 256; k++) {
        PyObject *l = PySequence_Fast_GET_ITEM(seq, k);
        Py_ssize_t m = PySequence_Size(l);
        if (m < 0) {
            Py_DECREF(seq);
            return -1;
        }
        lists[k] = dblob(d, sizeof(int32_t) * ((size_t)m + 1));
        if (lists[k] == NULL || obj_index_list(d, l, lists[k], (int)m, limit) < 0) {
            Py_DECREF(seq);
            return -1;
        }
        ns[k] = (int)m;
    }
    Py_DECREF(seq);
    *out = lists;
    *nout = ns;
    return 0;
}

static int
obj_bstr_list(HunDict *d, PyObject *v, BStr **out, int *n)
{
    PyObject *seq = PySequence_Fast(v, "HunDict config: a list expected");
    if (seq == NULL) return -1;
    Py_ssize_t m = PySequence_Fast_GET_SIZE(seq);
    BStr *b = dblob(d, sizeof(BStr) * ((size_t)m + 1));
    if (b == NULL) {
        Py_DECREF(seq);
        return -1;
    }
    for (Py_ssize_t i = 0; i < m; i++) {
        if (obj_bytes(d, PySequence_Fast_GET_ITEM(seq, i), &b[i]) < 0) {
            Py_DECREF(seq);
            return -1;
        }
    }
    Py_DECREF(seq);
    *out = b;
    *n = (int)m;
    return 0;
}

static int
HunDict_init(HunDict *d, PyObject *args, PyObject *kwds)
{
    PyObject *cfg;
    (void)kwds;
    if (d->blobs != NULL) {
        PyErr_SetString(PyExc_RuntimeError, "HunDict already initialized");
        return -1;
    }
    if (!PyArg_ParseTuple(args, "O!", &PyDict_Type, &cfg)) return -1;
    PyObject *v;
#define I(name) if (cfg_intv(cfg, #name, &d->name) < 0) return -1
#define F(name) if (cfg_flagv(cfg, #name, &d->name) < 0) return -1
    I(h_utf8); I(h_cpx); I(h_langnum); I(flag_mode); F(h_forbidden);
    I(a_utf8); I(a_cpx); I(a_langnum); F(a_forbidden);
    F(compoundflag); F(compoundbegin); F(compoundmiddle); F(compoundend); F(compoundroot); F(compoundpermitflag);
    F(compoundforbidflag); F(nosuggest); F(nongramsuggest); F(needaffix); F(circumfix); F(onlyincompound);
    F(keepcase); F(forceucase); F(warn); F(substandard);
    I(compoundmoresuffixes); I(checkcompounddup); I(checkcompoundrep); I(checkcompoundcase);
    I(checkcompoundtriple); I(simplifiedtriple); I(fullstrip); I(checksharps); I(forbidwarn); I(havecontclass);
    I(nosplitsugs); I(sugswithdots); I(onlymaxdiff); I(simplifiedcpd); I(is_compound); I(lang_with_dash_usage);
    I(cpdwordmax); I(cpdmin); I(cpdmaxsyllable); I(maxngramsugs); I(maxdiff); I(s_maxngramsugs);
    I(s_maxcpdsugs); I(maxsug); I(has_aliasm); I(max_pfx_key); I(max_sfx_key); I(pfx_groups);
#undef I
#undef F
    if (cfg_bytes(d, cfg, "h_ignore", &d->h_ignore) < 0) return -1;
    if (cfg_bytes(d, cfg, "a_ignore", &d->a_ignore) < 0) return -1;
    d->has_ignore_units = d->a_ignore.n > 0;
    if (cfg_units(d, cfg, "cpdvowels", &d->cpdvowels, &d->ncpdvowels, 0) < 0) return -1;
    if (cfg_units(d, cfg, "ckey", &d->ckey, &d->nckey, 0) < 0) return -1;
    if (cfg_units(d, cfg, "ctry", &d->ctry, &d->nctry, 0) < 0) return -1;
    if (cfg_table(d, cfg, "upper", &d->upper) < 0) return -1;
    if (cfg_table(d, cfg, "lower", &d->lower) < 0) return -1;
    if (cfg_table(d, cfg, "plain_upper", &d->plain_upper) < 0) return -1;
    /* contclasses */
    d->contclasses = dblob(d, 65536 / 8);
    if (d->contclasses == NULL) return -1;
    {
        uint16_t *u;
        int n;
        if (cfg_units(d, cfg, "contclasses", &u, &n, 0) < 0) return -1;
        for (int i = 0; i < n; i++) d->contclasses[u[i] >> 3] |= (uint8_t)(1 << (u[i] & 7));
    }
    /* aliases */
    if ((v = cfg_item(cfg, "aliasf")) == NULL) return -1;
    {
        PyObject *seq = PySequence_Fast(v, "aliasf: a list expected");
        if (seq == NULL) return -1;
        Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
        d->aliasf = dblob(d, sizeof(flag_t *) * ((size_t)n + 1));
        d->aliasf_n = dblob(d, sizeof(int) * ((size_t)n + 1));
        if (d->aliasf == NULL || d->aliasf_n == NULL) {
            Py_DECREF(seq);
            return -1;
        }
        for (Py_ssize_t i = 0; i < n; i++) {
            if (obj_units(d, PySequence_Fast_GET_ITEM(seq, i), &d->aliasf[i], &d->aliasf_n[i], 1) < 0) {
                Py_DECREF(seq);
                return -1;
            }
        }
        d->naliasf = (int)n;
        Py_DECREF(seq);
    }
    if ((v = cfg_item(cfg, "aliasm")) == NULL || obj_bstr_list(d, v, &d->aliasm, &d->naliasm) < 0) return -1;
    if ((v = cfg_item(cfg, "wordbreak")) == NULL || obj_bstr_list(d, v, &d->wordbreak, &d->nwordbreak) < 0)
        return -1;
    if ((v = cfg_item(cfg, "reptable")) == NULL || obj_reptable(d, v, &d->rep) < 0) return -1;
    if (d->rep.n < 0) d->rep.n = 0;
    if ((v = cfg_item(cfg, "iconv")) == NULL || obj_reptable(d, v, &d->iconv) < 0) return -1;
    if ((v = cfg_item(cfg, "oconv")) == NULL || obj_reptable(d, v, &d->oconv) < 0) return -1;
    /* CHECKCOMPOUNDPATTERN: (pattern, pattern2, pattern3, cond, cond2) */
    if ((v = cfg_item(cfg, "checkcpd")) == NULL) return -1;
    {
        PyObject *seq = PySequence_Fast(v, "checkcpd: a list expected");
        if (seq == NULL) return -1;
        Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
        d->checkcpd = dblob(d, sizeof(CpdPat) * ((size_t)n + 1));
        if (d->checkcpd == NULL) {
            Py_DECREF(seq);
            return -1;
        }
        for (Py_ssize_t i = 0; i < n; i++) {
            PyObject *p1, *p2, *p3;
            long c1, c2;
            if (!PyArg_ParseTuple(PySequence_Fast_GET_ITEM(seq, i), "OOOll", &p1, &p2, &p3, &c1, &c2)
                || obj_bytes(d, p1, &d->checkcpd[i].pat) < 0 || obj_bytes(d, p2, &d->checkcpd[i].pat2) < 0
                || obj_bytes(d, p3, &d->checkcpd[i].pat3) < 0) {
                Py_DECREF(seq);
                return -1;
            }
            d->checkcpd[i].cond = (flag_t)c1;
            d->checkcpd[i].cond2 = (flag_t)c2;
        }
        d->ncheckcpd = (int)n;
        Py_DECREF(seq);
    }
    /* COMPOUNDRULE: list of str */
    if ((v = cfg_item(cfg, "defcpd")) == NULL) return -1;
    {
        PyObject *seq = PySequence_Fast(v, "defcpd: a list expected");
        if (seq == NULL) return -1;
        Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
        d->defcpd = dblob(d, sizeof(FlagRule) * ((size_t)n + 1));
        if (d->defcpd == NULL) {
            Py_DECREF(seq);
            return -1;
        }
        for (Py_ssize_t i = 0; i < n; i++) {
            if (obj_units(d, PySequence_Fast_GET_ITEM(seq, i), &d->defcpd[i].f, &d->defcpd[i].n, 0) < 0) {
                Py_DECREF(seq);
                return -1;
            }
        }
        d->ndefcpd = (int)n;
        Py_DECREF(seq);
    }
    /* MAP: list of lists of bytes */
    if ((v = cfg_item(cfg, "maptable")) == NULL) return -1;
    {
        PyObject *seq = PySequence_Fast(v, "maptable: a list expected");
        if (seq == NULL) return -1;
        Py_ssize_t n = PySequence_Fast_GET_SIZE(seq);
        d->maptable = dblob(d, sizeof(MapEntry) * ((size_t)n + 1));
        if (d->maptable == NULL) {
            Py_DECREF(seq);
            return -1;
        }
        for (Py_ssize_t i = 0; i < n; i++) {
            if (obj_bstr_list(d, PySequence_Fast_GET_ITEM(seq, i), &d->maptable[i].v, &d->maptable[i].n) < 0) {
                Py_DECREF(seq);
                return -1;
            }
        }
        d->nmaptable = (int)n;
        Py_DECREF(seq);
    }
    /* affixes */
    if ((v = cfg_item(cfg, "pentries")) == NULL || obj_affixes(d, v, &d->pent, &d->npent) < 0) return -1;
    if ((v = cfg_item(cfg, "sentries")) == NULL || obj_affixes(d, v, &d->sent, &d->nsent) < 0) return -1;
    if ((v = cfg_item(cfg, "pstart")) == NULL || obj_index_list(d, v, d->pstart, 256, d->npent) < 0) return -1;
    if ((v = cfg_item(cfg, "sstart")) == NULL || obj_index_list(d, v, d->sstart, 256, d->nsent) < 0) return -1;
    if ((v = cfg_item(cfg, "pflag")) == NULL || obj_flag_lists(d, v, &d->pflag, &d->pflag_n, d->npent) < 0)
        return -1;
    if ((v = cfg_item(cfg, "sflag")) == NULL || obj_flag_lists(d, v, &d->sflag, &d->sflag_n, d->nsent) < 0)
        return -1;
    d->tablesize = 1;
    return 0;
}

static PyObject *
HunDict_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    (void)args;
    (void)kwds;
    HunDict *d = (HunDict *)type->tp_alloc(type, 0);
    return (PyObject *)d;
}

static void mp_free(struct MapPrune *mp);

static void
ng_free(HunDict *d)
{
    /* (the derived data of the word list) */
    mp_free(d->mp);
    d->mp = NULL;
    free(d->ng_order);
    free(d->ng_clen);
    free(d->ng_bits);
    d->ng_order = NULL;
    d->ng_clen = NULL;
    d->ng_bits = NULL;
    d->ng_n = 0;
}

static void
HunDict_dealloc(HunDict *d)
{
    for (int i = 0; i < d->nblobs; i++) free(d->blobs[i]);
    free(d->blobs);
    free(d->ent);
    free(d->wpool);
    free(d->fpool);
    free(d->slots);
    free(d->bloom);
    for (int i = 0; i < d->nphon; i++) free((void *)d->phon[i].s);
    free(d->phon);
    free(d->fsets);
    ng_free(d);
    free(d->ng_pos);
    mp_free(d->mp);
    Py_TYPE(d)->tp_free((PyObject *)d);
}

static int
check_ready(HunDict *d)
{
    if (d->blobs == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "HunDict not initialized");
        return -1;
    }
    if (d->busy) {
        PyErr_SetString(PyExc_RuntimeError, "HunDict is in use");
        return -1;
    }
    return 0;
}

/* load_dic(data: bytes) -> [(word, desc, captype)] of the words with ph: fields */
static PyObject *
HunDict_load_dic(HunDict *d, PyObject *arg)
{
    if (check_ready(d) < 0) return NULL;
    Py_buffer buf;
    if (PyObject_GetBuffer(arg, &buf, PyBUF_SIMPLE) < 0) return NULL;
    PyObject *phlist = PyList_New(0);
    if (phlist == NULL) {
        PyBuffer_Release(&buf);
        return NULL;
    }
    /* (the first fpool entry: the empty flag set) */
    if (d->fpool_n == 0) {
        if (grow((void **)&d->fpool, &d->fpool_c, 1, sizeof(flag_t)) < 0) {
            PyBuffer_Release(&buf);
            Py_DECREF(phlist);
            return PyErr_NoMemory();
        }
        d->fpool[0] = 0;
        d->fpool_n = 1;
    }
    Ctx c;
    ctx_init(&c, d);
    d->busy = 1;
    int r;
    if (setjmp(c.jb)) {
        PyErr_NoMemory();
        r = -1;
    } else {
        r = load_lines(&c, (const uint8_t *)buf.buf, (size_t)buf.len, phlist);
    }
    d->busy = 0;
    ctx_free(&c);
    PyBuffer_Release(&buf);
    ng_free(d);
    if (r < 0) {
        Py_DECREF(phlist);
        return NULL;
    }
    /* (the arrays at their size; the table of the flag sets is only needed while loading) */
    if (d->nent > 0 && (size_t)d->cent > (size_t)d->nent) {
        HEntry *ne = realloc(d->ent, sizeof(HEntry) * (size_t)d->nent);
        if (ne != NULL) {
            d->ent = ne;
            d->cent = d->nent;
        }
    }
    if (d->wpool_n > 0 && d->wpool_c > d->wpool_n) {
        uint8_t *nw = realloc(d->wpool, d->wpool_n);
        if (nw != NULL) {
            d->wpool = nw;
            d->wpool_c = d->wpool_n;
        }
    }
    if (d->fpool_n > 0 && d->fpool_c > d->fpool_n) {
        flag_t *nf = realloc(d->fpool, sizeof(flag_t) * d->fpool_n);
        if (nf != NULL) {
            d->fpool = nf;
            d->fpool_c = d->fpool_n;
        }
    }
    free(d->fsets);
    d->fsets = NULL;
    d->nfsets = 0;
    d->nfsets_slots = 0;
    return phlist;
}

/* set_reptable(table): the REP table with the ph: replacements */
static PyObject *
HunDict_set_reptable(HunDict *d, PyObject *arg)
{
    if (check_ready(d) < 0) return NULL;
    RepTable t;
    if (obj_reptable(d, arg, &t) < 0) return NULL;
    if (t.n < 0) t.n = 0;
    d->rep = t;
    Py_RETURN_NONE;
}

static int
get_word_arg(PyObject *arg, const uint8_t **w, int *n)
{
    if (!PyBytes_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "bytes expected");
        return -1;
    }
    Py_ssize_t len = PyBytes_GET_SIZE(arg);
    if (len > INT32_MAX / 8) {
        PyErr_SetString(PyExc_ValueError, "word too long");
        return -1;
    }
    *w = (const uint8_t *)PyBytes_AS_STRING(arg);
    *n = (int)len;
    return 0;
}

static PyObject *
HunDict_spell(HunDict *d, PyObject *arg)
{
    const uint8_t *w;
    int n;
    if (check_ready(d) < 0 || get_word_arg(arg, &w, &n) < 0) return NULL;
    if (n >= H_MAXWORDUTF8LEN && n >= H_MAXWORDLEN) Py_RETURN_FALSE; /* (spell_internal: too long) */
    Ctx c;
    ctx_init(&c, d);
    d->busy = 1;
    int r;
    if (setjmp(c.jb)) {
        d->busy = 0;
        ctx_free(&c);
        return PyErr_NoMemory();
    }
    r = spell_rec(&c, w, n, NULL);
    d->busy = 0;
    ctx_free(&c);
    return PyBool_FromLong(r);
}

/* add(word): Hunspell::add (the word without flags) */
static PyObject *
HunDict_add(HunDict *d, PyObject *arg)
{
    const uint8_t *w;
    int n;
    if (check_ready(d) < 0 || get_word_arg(arg, &w, &n) < 0) return NULL;
    if (d->fpool_n == 0) {
        if (grow((void **)&d->fpool, &d->fpool_c, 1, sizeof(flag_t)) < 0) return PyErr_NoMemory();
        d->fpool[0] = 0;
        d->fpool_n = 1;
    }
    int32_t dp = lookup(d, w, n);
    if (dp >= 0) {
        /* remove_forbidden_flag */
        for (; dp >= 0; dp = d->ent[dp].next) {
            if (EHAS(d, dp, d->h_forbidden)) d->ent[dp].flags = 0;
        }
        Py_RETURN_NONE;
    }
    Ctx c;
    ctx_init(&c, d);
    d->busy = 1;
    int r = 0;
    if (setjmp(c.jb)) {
        r = -2;
    } else {
        uint16_t *u;
        int nu = to_units(&c, w, n, d->a_utf8, &u);
        int captype = captype_units(d, u, nu);
        if (add_word(d, w, n, NULL, 0, 0) == -2) r = -2;
        else r = add_hidden(&c, u, nu, NULL, 0, captype, NULL, 0, NULL);
    }
    d->busy = 0;
    ctx_free(&c);
    ng_free(d);
    if (r == -2) return PyErr_NoMemory();
    if (r < 0) return NULL;
    Py_RETURN_NONE;
}

static PyObject *HunDict_suggest(HunDict *d, PyObject *args);

static PyObject *
HunDict_sizeof(HunDict *d, PyObject *unused)
{
    (void)unused;
    size_t s = sizeof(HunDict) + sizeof(HEntry) * (size_t)d->cent + d->wpool_c + sizeof(flag_t) * d->fpool_c
               + sizeof(WSlot) * d->nslots + (d->nslots / 16) * sizeof(uint64_t)
               + sizeof(uint32_t) * 2 * d->nfsets_slots + (size_t)d->ng_n * (sizeof(int32_t) + 2)
               + (d->ng_pos != NULL ? 65536 * sizeof(uint64_t) : 0);
    if (d->mp != NULL)
        s += sizeof(MapPrune) + sizeof(uint8_t *) * (size_t)d->mp->nroots + sizeof(PfxPair) * (size_t)d->mp->npa
             + sizeof(BStr) * ((size_t)d->mp->nsa + d->mp->nsub);
    return PyLong_FromSize_t(s);
}

static PyMethodDef HunDict_methods[] = {
    {"load_dic", (PyCFunction)HunDict_load_dic, METH_O, NULL},
    {"set_reptable", (PyCFunction)HunDict_set_reptable, METH_O, NULL},
    {"spell", (PyCFunction)HunDict_spell, METH_O, NULL},
    {"suggest", (PyCFunction)HunDict_suggest, METH_VARARGS, NULL},
    {"add", (PyCFunction)HunDict_add, METH_O, NULL},
    {"__sizeof__", (PyCFunction)HunDict_sizeof, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject HunDictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "langtool._speedups.HunDict",
    .tp_basicsize = sizeof(HunDict),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "the data of a Hunspell dictionary (see langtool.hunspell)",
    .tp_new = HunDict_new,
    .tp_init = (initproc)HunDict_init,
    .tp_dealloc = (destructor)HunDict_dealloc,
    .tp_methods = HunDict_methods,
};

int
lt_hunspell_init(PyObject *m)
{
    if (PyType_Ready(&HunDictType) < 0) return -1;
    Py_INCREF(&HunDictType);
    if (PyModule_AddObject(m, "HunDict", (PyObject *)&HunDictType) < 0) {
        Py_DECREF(&HunDictType);
        return -1;
    }
    return 0;
}
