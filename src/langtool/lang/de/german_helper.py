"""Port of org.languagetool.rules.de.GermanHelper: helper functions for
German POS tags."""

from ...analysis import PARAGRAPH_END_TAGNAME, SENTENCE_END_TAGNAME
from ...tools import java_split
from .german_token import AnalyzedGermanToken


def has_reading_of_type(token_readings, pos_type):
    """hasReadingOfType(): whether a reading of the AnalyzedTokenReadings
    has the GermanToken.POSType (False at the sentence/paragraph end)"""
    if token_readings is None:
        return False
    for token in token_readings.readings:
        if token.pos_tag is not None and (token.pos_tag == SENTENCE_END_TAGNAME
                                          or token.pos_tag == PARAGRAPH_END_TAGNAME):
            return False
        if AnalyzedGermanToken(token).type is pos_type:
            return True
    return False


def _get_index_or_empty_string(pos_tag, idx):
    if pos_tag is None:
        return ''
    array = java_split(pos_tag, ':')
    if len(array) > idx:
        return array[idx]
    return ''


def get_noun_case(pos_tag):
    """getNounCase(), input e.g. SUB:AKK:SIN:NEU"""
    return _get_index_or_empty_string(pos_tag, 1)


def get_noun_number(pos_tag):
    return _get_index_or_empty_string(pos_tag, 2)


def get_noun_gender(pos_tag):
    return _get_index_or_empty_string(pos_tag, 3)


def get_determiner_definiteness(pos_tag):
    """getDeterminerDefiniteness(), input e.g. ART:DEF:DAT:SIN:FEM"""
    return _get_index_or_empty_string(pos_tag, 1)


def get_comparison(pos_tag):
    """getComparison(): GRU, KOM, or SUP (input e.g. ADJ:AKK:PLU:MAS:KOM:SOL)"""
    cmp = _get_index_or_empty_string(pos_tag, 4)
    if cmp not in ('GRU', 'KOM', 'SUP'):
        # for cases like "PA2:PRD:GRU:VER"
        cmp = _get_index_or_empty_string(pos_tag, 2)
    return cmp


def get_determiner_case(pos_tag):
    return _get_index_or_empty_string(pos_tag, 2)


def get_determiner_number(pos_tag):
    return _get_index_or_empty_string(pos_tag, 3)


def get_determiner_gender(pos_tag):
    return _get_index_or_empty_string(pos_tag, 4)
