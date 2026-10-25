#!/usr/bin/env python3
"""Create src/langtool/hunspell_dictionaries.json, the manifest of the
Hunspell dictionaries (.aff/.dic) used for spell checking (see
langtool/hunspell_dictionaries.py). The dictionaries come from the
LibreOffice dictionaries repository at a pinned commit; the manifest records
the download URL, size and sha256 of every file and maps every language
(variant) code of langtool to a dictionary (or to none).

Usage: make_hunspell_manifest.py [download_dir]

The files are downloaded into download_dir (default /tmp/lt_hunspell_dl) to
compute the checksums. They are never part of the package.
"""

import hashlib
import json
import os
import sys
import urllib.request

REPOSITORY = 'https://github.com/LibreOffice/dictionaries'
COMMIT = '67032ee957631908098a72edf48dc81cac27e369'  # 2026-10-12
RAW = 'https://raw.githubusercontent.com/LibreOffice/dictionaries/%s/%s'

# language/variant code -> dictionary (path in the repository without .aff/.dic)
# or None if LibreOffice has no dictionary for the language
LANGUAGES = {
    'ar': 'ar/ar',
    'ast-ES': None,
    'be-BY': 'be_BY/be-official',
    'br-FR': 'br_FR/br_FR',
    'ca-ES': 'ca/dictionaries/ca',
    'ca-ES-valencia': 'ca/dictionaries/ca-valencia',
    'ca-ES-balear': 'ca/dictionaries/ca',
    'crh-UA': None,
    'da-DK': 'da_DK/da_DK',
    'de': 'de/de_DE_frami',
    'de-DE': 'de/de_DE_frami',
    'de-AT': 'de/de_AT_frami',
    'de-CH': 'de/de_CH_frami',
    'de-DE-x-simple-language': 'de/de_DE_frami',
    'el-GR': 'el_GR/el_GR',
    'en': 'en/en_US',
    'en-US': 'en/en_US',
    'en-GB': 'en/en_GB',
    'en-AU': 'en/en_AU',
    'en-CA': 'en/en_CA',
    'en-NZ': 'en/en_GB',
    'en-ZA': 'en/en_ZA',
    'eo': 'eo/eo',
    'es': 'es/es_ES',
    'es-AR': 'es/es_AR',
    'fa': 'fa_IR/fa-IR',
    'fr': 'fr_FR/dictionaries/fr',
    'fr-CA': 'fr_FR/dictionaries/fr',
    'fr-CH': 'fr_FR/dictionaries/fr',
    'fr-BE': 'fr_FR/dictionaries/fr',
    'ga-IE': None,
    'gl-ES': 'gl/gl_ES',
    'is-IS': 'is/is',
    'it': 'it_IT/it_IT',
    'ja-JP': None,
    'km-KH': None,
    'lt-LT': 'lt_LT/lt',
    'ml-IN': None,
    'nl': 'nl_NL/nl_NL',
    'nl-BE': 'nl_NL/nl_NL',
    'pl-PL': 'pl_PL/pl_PL',
    'pt': 'pt_PT/pt_PT',
    'pt-PT': 'pt_PT/pt_PT',
    'pt-BR': 'pt_BR/pt_BR',
    'pt-AO': 'pt_PT/pt_PT',
    'pt-MZ': 'pt_PT/pt_PT',
    'ro-RO': 'ro/ro_RO',
    'ru-RU': 'ru_RU/ru_RU',
    'sk-SK': 'sk_SK/sk_SK',
    'sl-SI': 'sl_SI/sl_SI',
    'sv': 'sv_SE/dictionaries/sv_SE',
    'ta-IN': 'ta_IN/ta_IN',
    'tl-PH': None,
    'uk-UA': 'uk_UA/uk_UA',
    'zh-CN': None,
}

# remarks on the mapping (shown by langtool.hunspell_dictionaries.info())
NOTES = {
    'en-NZ': 'LibreOffice has no en_NZ dictionary, the British English one (en_GB) is used',
    'ca-ES-balear': 'LibreOffice has no Balearic dictionary, the general Catalan one is used',
    'de': 'the dictionary of Germany (de_DE_frami)',
    'en': 'the American English dictionary (en_US)',
    'fr-CA': 'one French dictionary for all variants',
    'fr-CH': 'one French dictionary for all variants',
    'fr-BE': 'one French dictionary for all variants',
    'nl-BE': 'one Dutch dictionary for all variants',
    'pt': 'the European Portuguese dictionary (pt_PT)',
    'pt-AO': 'the European Portuguese dictionary (pt_PT)',
    'pt-MZ': 'the European Portuguese dictionary (pt_PT)',
    'de-DE-x-simple-language': 'the dictionary of Germany (de_DE_frami)',
    'ast-ES': 'no Asturian dictionary in LibreOffice',
    'crh-UA': 'no Crimean Tatar dictionary in LibreOffice',
    'ga-IE': 'no Irish dictionary in LibreOffice',
    'ja-JP': 'no Japanese dictionary in LibreOffice',
    'km-KH': 'no Khmer dictionary in LibreOffice',
    'ml-IN': 'no Malayalam dictionary in LibreOffice',
    'tl-PH': 'no Tagalog dictionary in LibreOffice',
    'zh-CN': 'no Chinese dictionary in LibreOffice',
}


def fetch(path, dest_dir):
    url = RAW % (COMMIT, path)
    dest = os.path.join(dest_dir, COMMIT[:12], path)
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print('Downloading', url, file=sys.stderr)
        with urllib.request.urlopen(url, timeout=120) as r, open(dest + '.tmp', 'wb') as f:
            f.write(r.read())
        os.replace(dest + '.tmp', dest)
    return url, dest


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp/lt_hunspell_dl'
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
    from langtool.languages import all_codes
    missing = set(all_codes()) - set(LANGUAGES)
    if missing:
        sys.exit('no mapping for the language codes %s' % sorted(missing))
    dictionaries = {}
    for name in sorted({d for d in LANGUAGES.values() if d}):
        entry = {}
        for ext in ('aff', 'dic'):
            url, path = fetch(name + '.' + ext, dest_dir)
            entry[ext] = {'url': url, 'sha256': sha256(path), 'size': os.path.getsize(path)}
        dictionaries[name] = entry
    manifest = {
        'version': 1,
        'repository': REPOSITORY,
        'commit': COMMIT,
        'dictionaries': dictionaries,
        'languages': LANGUAGES,
        'notes': NOTES,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'langtool',
                       'hunspell_dictionaries.json')
    with open(out, 'w') as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write('\n')
    print('%d dictionaries, %d languages without a dictionary: %s' % (
        len(dictionaries), sum(1 for v in LANGUAGES.values() if not v),
        ', '.join(k for k, v in sorted(LANGUAGES.items()) if not v)))


if __name__ == '__main__':
    main()
