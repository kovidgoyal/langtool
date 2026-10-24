#!/usr/bin/env python3
"""Create src/langtool/dictionaries.json, the manifest describing where the
binary morfologik dictionaries for each language can be downloaded from
(Maven Central jars), with checksums.

Usage: make_dict_manifest.py /path/to/languagetool [jar_cache_dir]
"""

import hashlib
import json
import os
import sys
import urllib.request
import zipfile

MAVEN = 'https://repo1.maven.org/maven2/'
LT_RELEASE = '6.8'

# dictionaries not part of the LanguageTool repository
EXTERNAL = {
    'ast': ('org.languagetool', 'asturian-pos-dict', '0.1'),
    'be': ('io.github.belarus', 'linguistics.grammardb.spell.languagetool', '1.0.2'),
    'ca': ('org.softcatala', 'catalan-pos-dict', '3.3'),
    'crh': ('org.qirimca.nlp', 'morfologik-crh-lt', '1.0.1'),
    'de': ('de.danielnaber', 'german-pos-dict', '1.2.4'),
    'el': ('org.ioperm', 'morphology-el', '1.0.0'),
    'en': ('org.languagetool', 'english-pos-dict', '0.6'),
    'es': ('org.softcatala', 'spanish-pos-dict', '2.5'),
    'fr': ('org.languagetool', 'french-pos-dict', '0.7'),
    'ga': ('io.github.jimregan', 'languagetool-ga-dicts', '0.02'),
    'nl': ('org.languagetool', 'dutch-pos-dict', '0.1'),
    'pt': ('org.languagetool', 'portuguese-pos-dict', '1.2.0'),
    'uk': ('ua.net.nlp', 'morfologik-ukrainian-lt', '6.8.6'),
}
# files of EXTERNAL jars that are not in the org/languagetool/resource
# layout: jar path -> name (the jar is searched for the path given in the
# manifest, see dictionaries._find_in_jar)
EXTERNAL_FILES = {
    # GreekAnalyzer of org.ioperm.morphology.el (used by GreekTagger)
    'el': {
        'org/ioperm/morphology/el/analysis.dict': 'el/analysis.dict',
        'org/ioperm/morphology/el/analysis.info': 'el/analysis.info',
    },
}
# files of the speller (only the misspelling check is ported, see
# langtool/spelling.py) that the dictionary download provides: names
# (relative to org/languagetool/resource) from the EXTERNAL jar of the
# language ('external') and from the language-<code> jar of the
# LanguageTool release ('module'); the plain text word lists are not part
# of the package data, see tools/import_data.py
SPELLER_FILES = {
    'fr': {
        'module': ['fr/hunspell/spelling.txt', 'fr/hunspell/spelling_custom.txt', 'fr/hunspell/ignore.txt',
                   'fr/hunspell/prohibit.txt'],
    },
    'nl': {
        'external': ['nl/spelling/nl_NL.dict', 'nl/spelling/nl_NL.info'],
        'module': ['nl/spelling/spelling.txt', 'nl/spelling/ignore.txt', 'nl/spelling/prohibit.txt'],
    },
    'pt': {
        'external': ['pt/spelling/pt-BR.dict', 'pt/spelling/pt-BR.info', 'pt/spelling/pt-PT-90.dict',
                     'pt/spelling/pt-PT-90.info', 'pt/spelling/pt-PT-45.dict', 'pt/spelling/pt-PT-45.info'],
        'module': ['pt/spelling.txt', 'pt/ignore.txt', 'pt/prohibit.txt'],
    },
    'ru': {
        'module': ['ru/hunspell/ru_RU.dict', 'ru/hunspell/ru_RU.info', 'ru/hunspell/spelling.txt',
                   'ru/hunspell/ignore.txt', 'ru/hunspell/prohibit.txt'],
    },
}
SKIP_MODULES = {'all', 'sr', 'de-DE-x-simple-language'}


def jar_url(group, artifact, version):
    return '%s%s/%s/%s/%s-%s.jar' % (MAVEN, group.replace('.', '/'), artifact, version, artifact, version)


def fetch(url, cache):
    path = os.path.join(cache, url.rsplit('/', 1)[1])
    if not os.path.exists(path):
        print('Downloading', url, file=sys.stderr)
        with urllib.request.urlopen(url) as r, open(path + '.tmp', 'wb') as f:
            f.write(r.read())
        os.rename(path + '.tmp', path)
    return path


def wanted(name):
    if '/hunspell/' in name or '/spelling/' in name:
        return False
    base = name.rsplit('/', 1)[-1]
    if base.endswith('.dict') or base.endswith('.info'):
        return 'spell' not in base.lower()
    return base.endswith('_tags.txt')


def entries(jar_path, names=None, extra=()):
    """The dictionary files of a jar; names: mapping of jar paths to names
    (only those files are taken), see EXTERNAL_FILES; extra: names of
    further files (in the org/languagetool/resource layout), see
    SPELLER_FILES"""
    out = []
    with zipfile.ZipFile(jar_path) as z:
        for info in z.infolist():
            n = info.filename
            if names is not None:
                if n in names:
                    out.append({'path': n, 'name': names[n], 'size': info.file_size})
                continue
            if info.is_dir() or '/resource/' not in n:
                continue
            rel = n.split('/resource/', 1)[1]
            if not wanted(n) and rel not in extra:
                continue
            out.append({'path': n, 'name': rel, 'size': info.file_size})
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    lt = sys.argv[1]
    cache = sys.argv[2] if len(sys.argv) > 2 else '/tmp/ltdl'
    os.makedirs(cache, exist_ok=True)
    modules = os.path.join(lt, 'languagetool-language-modules')
    manifest = {'version': 1, 'languages': {}}
    for mod in sorted(os.listdir(modules)):
        if mod in SKIP_MODULES:
            continue
        res = os.path.join(modules, mod, 'src', 'main', 'resources', 'org', 'languagetool', 'resource')
        sources = []
        in_repo = []
        if os.path.isdir(res):
            for root, dirs, files in os.walk(res):
                dirs[:] = [d for d in dirs if d not in ('hunspell', 'spelling')]
                for f in files:
                    if f.endswith('.dict') and 'spell' not in f.lower():
                        in_repo.append(os.path.relpath(os.path.join(root, f), res))
        speller_files = SPELLER_FILES.get(mod, {})
        if in_repo or speller_files.get('module'):
            url = jar_url('org.languagetool', 'language-' + mod, LT_RELEASE)
            jar = fetch(url, cache)
            module_files = set(speller_files.get('module', ()))
            ents = [e for e in entries(jar, extra=module_files) if e['name'] in module_files or
                    e['name'].rsplit('.', 1)[0] in {p.rsplit('.', 1)[0] for p in in_repo}]
            # verify identical to the repository versions
            with zipfile.ZipFile(jar) as z:
                for e in ents:
                    if e['name'].endswith('.dict'):
                        repo_file = os.path.join(res, e['name'])
                        if os.path.exists(repo_file):
                            with open(repo_file, 'rb') as f:
                                if f.read() != z.read(e['path']):
                                    print('WARNING: %s differs from repository version' % e['name'],
                                          file=sys.stderr)
            sources.append({'url': url, 'sha256': sha256(jar), 'size': os.path.getsize(jar), 'files': ents})
        if mod in EXTERNAL:
            url = jar_url(*EXTERNAL[mod])
            jar = fetch(url, cache)
            ents = [e for e in entries(jar, EXTERNAL_FILES.get(mod), speller_files.get('external', ()))
                    if not e['name'].rsplit('/', 1)[-1].startswith('SynthDictionaryBuilder')]
            if ents:  # jars without (non-spelling) dictionaries are not needed
                sources.append({'url': url, 'sha256': sha256(jar), 'size': os.path.getsize(jar), 'files': ents})
        if sources:
            manifest['languages'][mod] = sources
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'langtool', 'dictionaries.json')
    with open(out, 'w') as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    for lang, srcs in manifest['languages'].items():
        print(lang, [e['name'] for s in srcs for e in s['files']])


if __name__ == '__main__':
    main()
