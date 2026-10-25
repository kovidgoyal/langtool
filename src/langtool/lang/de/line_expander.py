"""Port of org.languagetool.rules.de.LineExpander: expands the lines of the
German word lists (spelling.txt, prohibit.txt etc.) with their suffix
flags (/S, /N, /E, /F, /T, /A, /P) and verb prefixes (prefix_verb)."""

import re
import threading

from ...tools import is_lower_case, java_hash_set_copy_order, java_split, java_trim, uppercase_first_char

_STRASSE = re.compile('stra(ß|ss)e')
_STRASSE_UC = re.compile('Stra(ß|ss)e')

_verb_form_cache = {}
_ver_tags = None
_cache_lock = threading.Lock()


def _verb_forms(verb):
    """GermanSynthesizer.INSTANCE.synthesizeForPosTags(verb, s -> s.startsWith("VER:")),
    cached like the verbFormCache"""
    forms = _verb_form_cache.get(verb)
    if forms is None:
        from ...api import get_language
        synthesizer = get_language('de-DE').synthesizer
        if hasattr(synthesizer, 'synthesize_for_tag_list'):
            global _ver_tags
            if _ver_tags is None:
                _ver_tags = [t for t in synthesizer.get_possible_tags() if t.startswith('VER:')]
            forms = tuple(synthesizer.synthesize_for_tag_list(verb, _ver_tags))
        else:
            forms = tuple(synthesizer.synthesize_for_pos_tags(verb, lambda s: s.startswith('VER:')))
        with _cache_lock:
            _verb_form_cache[verb] = forms
    return forms


def _clean_tags_and_escape_chars(s):
    """ignore "#..." so it can be used as a tag"""
    idx = s.find('#')
    if idx != -1:
        s = s[:idx]
    return java_trim(s.replace('\\', ''))


def _handle_line_with_prefix(line):
    result = []
    parts = java_split(_clean_tags_and_escape_chars(line), '_')
    if len(parts) != 2:
        raise ValueError("Unexpected line format, expected at most one '_': " + line)
    if '/' in parts[0] or '/' in parts[1]:
        raise ValueError("Unexpected line format, '_' cannot be combined with '/': " + line)
    if parts[1] == 'in':
        # special case for the common gender gap characters:
        result.append(parts[0] + '_in')
        result.append(parts[0] + '_innen')
        result.append(parts[0] + '*in')
        result.append(parts[0] + '*innen')
        result.append(parts[0] + ':in')
        result.append(parts[0] + ':innen')
    else:
        forms = _verb_forms(parts[1])
        if not forms:
            raise RuntimeError("Could not expand '" + parts[1] + "' from line '" + line + "', no forms found")
        # (iteration order of new HashSet<>(Arrays.asList(forms)))
        for form in java_hash_set_copy_order(list(forms)):
            if 'ß' not in form and len(form) > 0 and is_lower_case(form[0]):
                # skip these, it's too risky to introduce old spellings like "gewußt" from the synthesizer
                result.append(parts[0] + form)
        result.append(parts[0] + 'zu' + parts[1])  # "zu<verb>" is not part of forms from synthesizer
        result.append(uppercase_first_char(parts[0]) + parts[1] + 's')  # Genitiv, e.g. "des Weitergehens"
    return result


def _is_line_with_flag(line):
    idx = line.find('/')
    return not line.startswith('#') and idx > 0 and line[idx - 1] != '\\'


def _is_line_with_verb_prefix(line):
    idx = line.find('_')
    return not line.startswith('#') and idx > 0 and line[idx - 1] != '\\'


def _add(result, word):
    if word not in result:
        result.append(word)


def _handle_line_with_flags(line):
    result = []
    parts = java_split(_clean_tags_and_escape_chars(line), '/')
    if len(parts) != 2:
        raise ValueError('Unexpected line format, expected at most one slash: ' + line)
    word = parts[0]
    suffix = parts[1]
    for c in suffix:
        if c == 'S':
            _add(result, word)
            result.append(word + 's')
        elif c == 'N':
            _add(result, word)
            result.append(word + 'n')
        elif c == 'E':
            _add(result, word)
            result.append(word + 'e')
        elif c == 'F':
            _add(result, word)
            result.append(word + 'in')  # (m/f)
        elif c == 'T':
            _add(result, word)
            if word.endswith('straße') or word.endswith('strasse'):
                result.append(_STRASSE.sub('str.', word))
            if word.endswith('Straße') or word.endswith('Strasse'):
                result.append(_STRASSE_UC.sub('Str.', word))
        elif c == 'A' or c == 'P':  # Adjektiv / Partizip
            _add(result, word)
            if word.endswith('e'):
                result.append(word + 'r')
                result.append(word + 's')
                result.append(word + 'n')
                result.append(word + 'm')
            else:
                result.append(word + 'e')
                result.append(word + 'er')
                result.append(word + 'es')
                result.append(word + 'en')
                result.append(word + 'em')
        else:
            raise ValueError('Unknown suffix: ' + suffix + ' in line: ' + line)
    return result


class LineExpander:
    """LineExpander.expandLine(line)"""

    def expand_line(self, line):
        if ('_' not in line and '/' not in line and '#' not in line and '\\' not in line
                and (not line or (line[0] > ' ' and line[-1] > ' '))):
            return [line]  # (nothing to expand or clean)
        if _is_line_with_verb_prefix(line):
            return _handle_line_with_prefix(line)
        if _is_line_with_flag(line):
            return _handle_line_with_flags(line)
        return [_clean_tags_and_escape_chars(line)]


def expand_line(line):
    """LineExpander.expandLine(line)"""
    return LineExpander().expand_line(line)
