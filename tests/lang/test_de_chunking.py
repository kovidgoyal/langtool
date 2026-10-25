"""Port of org.languagetool.chunking.GermanChunkerTest and
org.languagetool.chunking.TokenPredicateTest (language-de)."""

import pytest

from conftest import require_dictionaries
from langtool.analysis import AnalyzedToken, AnalyzedTokenReadings
from langtool.api import get_language
from langtool.chunking import ChunkTag, ChunkTaggedToken, TokenPredicate
from langtool.jregex import compile as jcompile
from langtool.lang.de.chunking import GermanChunker
from langtool.tool import JLanguageTool


@pytest.fixture(scope='module', autouse=True)
def _dictionaries():
    require_dictionaries('de')


_lt = None
_chunker = GermanChunker()
_TAG_RE = jcompile('/[A-Z-]*')
_EXPANSION = {'B': 'B-NP', 'I': 'I-NP', 'NPP': 'NPP', 'NPS': 'NPS', 'PP': 'PP'}


def _get_lt():
    global _lt
    if _lt is None:
        _lt = JLanguageTool(get_language('de-DE'))
    return _lt


def _get_plain_input(s):
    return _TAG_RE.sub('', s).replace(' ,', ',')


def _get_expected_chunks(s):
    expected = []
    for part in s.split(' '):
        token_parts = [p for p in part.split('/')]
        while token_parts and not token_parts[-1]:
            token_parts.pop()  # String.split() drops trailing empty strings
        if len(token_parts) == 2:
            chunk = token_parts[1]
            if chunk not in _EXPANSION:
                raise RuntimeError("Unknown chunk type: '%s'" % chunk)
            expected.append(_EXPANSION[chunk])
        else:
            expected.append('O')
    return expected


def _assert_chunks(s, plain_input, chunks, expected_chunks):
    for i, expected_chunk in enumerate(expected_chunks):
        output_chunks_here = chunks[i]
        assert ChunkTag(expected_chunk) in output_chunks_here.chunk_tags, (
            "Expected '%s' but got '%s' at position %d for input:\n  %s\nPlain input:\n  %s\nChunks:\n  %s\n"
            "Expected:\n  %s" % (expected_chunk, output_chunks_here, i, s, plain_input, chunks, expected_chunks))


def _assert_basic_chunks(s):
    plain_input = _get_plain_input(s)
    result = _get_lt().get_analyzed_sentence(plain_input).get_tokens_without_whitespace()
    basic_chunks = _chunker.get_basic_chunks(list(result))
    _assert_chunks(s, plain_input, basic_chunks, _get_expected_chunks(s))


def _assert_full_chunks(s):
    plain_input = _get_plain_input(s)
    result = _get_lt().get_analyzed_sentence(plain_input).get_tokens_without_whitespace()
    _chunker.add_chunk_tags(list(result))
    result2 = [ChunkTaggedToken(r.token, r.chunk_tags, r) for r in result[1:]]
    _assert_chunks(s, plain_input, result2, _get_expected_chunks(s))


def test_chunking():
    """GermanChunkerTest.testChunking"""
    _assert_full_chunks("Ein/B Haus/I")
    _assert_full_chunks("Ein/NPP Hund/NPP und/NPP eine/NPP Katze/NPP stehen dort")
    _assert_full_chunks("Es war die/NPS größte/NPS und/NPS erfolgreichste/NPS Erfindung/NPS")
    _assert_full_chunks("Geräte/B , deren/NPS Bestimmung/NPS und/NPS Funktion/NPS unklar sind.")
    _assert_full_chunks("Julia/NPP und/NPP Karsten/NPP sind alt")
    _assert_full_chunks("Es ist die/NPS älteste/NPS und/NPS bekannteste/NPS Maßnahme/NPS")
    _assert_full_chunks("Das ist eine/NPS Masseeinheit/NPS und/NPS keine/NPS Gewichtseinheit/NPS")
    _assert_full_chunks("Sie fährt nur eins/NPS ihrer/NPS drei/NPS Autos/NPS")
    _assert_full_chunks("Da sind er/NPP und/NPP seine/NPP Schwester/NPP")
    # assertFullChunks("Sowohl/NPP sein/NPP Vater/NPP als/NPP auch/NPP seine/NPP Mutter/NPP sind da");  //?
    # assertFullChunks("Sowohl/NPP Tom/NPP als/NPP auch/NPP Maria/NPP sind da");
    # assertFullChunks("Sowohl/NPP er/NPP als/NPP auch/NPP seine/NPP Schwester/NPP sind da");
    _assert_full_chunks("Rekonstruktionen/NPP oder/NPP der/NPP Wiederaufbau/NPP sind das/NPS Ziel/NPS")
    _assert_full_chunks("Isolation/NPP und/NPP ihre/NPP Überwindung/NPP ist das/NPS Thema/NPS")
    _assert_full_chunks("Es gibt weder/NPP Gerechtigkeit/NPP noch/NPP Freiheit/NPP")
    _assert_full_chunks("Da sitzen drei/NPP Katzen/NPP")
    _assert_full_chunks("Der/NPS von/NPS der/NPS Regierung/NPS geprüfte/NPS Hund/NPS ist grün")
    _assert_full_chunks("Herr/NPP und/NPP Frau/NPP Schröder/NPP sind betrunken")
    # assertFullChunks("Die/NPS hohe/NPS Zahl/NPS dieser/NPS relativ/NPS kleinen/NPS Verwaltungseinheiten/NPS ist beeindruckend");   //?
    # assertFullChunks("Das ist eine/NPS der/NPS am/NPS meisten/NPS verbreiteten/NPS Krankheiten/NPS");   //?
    _assert_full_chunks("Das sind 37/NPS Prozent/NPS")
    _assert_full_chunks("Das sind 37/NPP Prozent/NPP")
    _assert_full_chunks("Er will die/NPP Arbeitsplätze/NPP so umgestalten , dass/NPP sie/NPP wie/NPP ein/NPP Spiel/NPP sind.")
    _assert_full_chunks("So dass Knochenbrüche/NPP und/NPP Platzwunden/NPP die/NPP Regel/NPP sind")
    _assert_full_chunks("Eine/NPS Veranstaltung/NPS ,/NPS die/NPS immer/NPS wieder/NPS ein/NPS kultureller/NPS Höhepunkt/NPS war")
    _assert_full_chunks("Und die/NPS ältere/NPS der/NPS beiden/NPS Töchter/NPS ist 20.")
    _assert_full_chunks("Der/NPS Synthese/NPS organischer/NPS Verbindungen/NPS steht nichts im/PP Weg/NPS")
    _assert_full_chunks("Aber/B die/NPP Kenntnisse/NPP der/NPP Sprache/NPP sind nötig.")  # actually "Aber" should not be tagged
    _assert_full_chunks("Dort steht die/NPS Pyramide/NPS des/NPS Friedens/NPS und/NPS der/NPS Eintracht/NPS")
    _assert_full_chunks("Und Teil/B der/NPS dort/NPS ausgestellten/NPS Bestände/NPS wurde privat finanziert.")
    _assert_full_chunks("Autor/NPS der/NPS ersten/NPS beiden/NPS Bücher/NPS ist Stephen King/NPS")
    _assert_full_chunks("Autor/NPS der/NPS beiden/NPS Bücher/NPS ist Stephen King/NPS")
    _assert_full_chunks("Teil/NPS der/NPS umfangreichen/NPS dort/NPS ausgestellten/NPS Bestände/NPS stammt von privat")
    _assert_full_chunks("Ein/NPS Teil/NPS der/NPS umfangreichen/NPS dort/NPS ausgestellten/NPS Bestände/NPS stammt von privat")
    _assert_full_chunks("Die/NPS Krankheit/NPS unserer/NPS heutigen/NPS Städte/NPS und/NPS Siedlungen/NPS ist der/NPS Verkehr/NPS")
    _assert_full_chunks("Der/B Nil/I ist der/NPS letzte/NPS der/NPS vier/NPS großen/NPS Flüsse/NPS")
    _assert_full_chunks("Der/NPS letzte/NPS der/NPS vier/NPS großen/NPS Flüsse/NPS ist der/B Nil/I")
    _assert_full_chunks("Sie kennt eine/NPP Menge/NPP englischer/NPP Wörter/NPP")
    _assert_full_chunks("Eine/NPP Menge/NPP englischer/NPP Wörter/NPP sind aus/PP dem/NPS Lateinischen/NPS abgeleitet.")
    _assert_full_chunks("Laut/PP den/PP meisten/PP Quellen/PP ist er 35 Jahre/B alt.")
    _assert_full_chunks("Bei/PP den/PP sehr/PP niedrigen/PP Oberflächentemperaturen/PP verbrennt nichts")
    _assert_full_chunks("In/PP den/PP alten/PP Religionen/PP ,/PP Mythen/PP und/PP Sagen/PP tauchen Geister/B auf.")
    _assert_full_chunks("Die/B Straße/I ist wichtig für/PP die/PP Stadtteile/PP und/PP selbständigen/PP Ortsteile/PP")
    _assert_full_chunks("Es herrscht gute/NPS Laune/NPS in/PP chemischen/PP Komplexverbindungen/PP")
    _assert_full_chunks("Funktionen/NPP des/NPP Körpers/NPP einschließlich/PP der/PP biologischen/PP und/PP sozialen/PP Grundlagen/PP")
    _assert_full_chunks("Das/NPS Dokument/NPS umfasst das für/PP Ärzte/PP und/PP Ärztinnen/PP festgestellte/PP Risikoprofil/PP")
    _assert_full_chunks("In/PP den/PP darauf/PP folgenden/PP Wochen/PP ging es los.")
    _assert_full_chunks("In/PP nur/PP zwei/PP Wochen/PP geht es los.")
    _assert_full_chunks("Programme/B , in/PP deren/PP deutschen/PP Installationen/PP nichts funktioniert.")
    _assert_full_chunks("Nach/PP sachlichen/PP und/PP militärischen/PP Kriterien/PP war das unnötig.")
    _assert_full_chunks("Mit/PP über/PP 1000/PP Handschriften/PP ist es die/NPS größte/NPS Sammlung/NPS")
    _assert_full_chunks("Es gab Beschwerden/NPP über/PP laufende/PP Sanierungsmaßnahmen/PP")
    _assert_full_chunks("Gesteigerte/B Effizienz/I durch/PP Einsatz/PP größerer/PP Maschinen/PP und/PP bessere/PP Kapazitätsplanung/PP")
    _assert_full_chunks("Bei/PP sehr/PP guten/PP Beobachtungsbedingungen/PP bin ich dabei")
    _assert_full_chunks("Die/NPP Beziehungen/NPP zwischen/NPP Kanada/NPP und/NPP dem/NPP Iran/NPP sind unterkühlt")
    _assert_full_chunks("Die/PP darauffolgenden/PP Jahre/PP war es kalt")
    _assert_full_chunks("Die/NPP darauffolgenden/NPP Jahre/NPP waren kalt")
    _assert_full_chunks("Die/PP letzten/PP zwei/PP Monate/PP war es kalt")
    # assertFullChunks("Die/NPP letzten/NPP zwei/NPP Monate/NPP waren kalt");
    _assert_full_chunks("Letztes/PP Jahr/PP war kalt")
    _assert_full_chunks("Letztes/PP Jahr/PP war es kalt")
    _assert_full_chunks("Es sind Atome/NPP ,/NPP welche/NPP der/NPP Urstoff/NPP aller/NPP Körper/NPP sind")
    _assert_full_chunks("Kommentare/NPP ,/NPP Korrekturen/NPP ,/NPP Kritik/NPP bitte nach /dev/null")
    _assert_full_chunks("Einer/NPS der/NPS beiden/NPS Höfe/NPS war schön")

def test_open_nlp_like_chunking():
    """GermanChunkerTest.testOpenNLPLikeChunking (B = begin, will be expanded
    to B-NP, I = inner, will be expanded to I-NP)"""
    # GermanChunker.setDebug(true);
    _assert_basic_chunks("Ein/B Haus/I")
    _assert_basic_chunks("Da steht ein/B Haus/I")
    _assert_basic_chunks("Da steht ein/B schönes/I Haus/I")
    _assert_basic_chunks("Da steht ein/B schönes/I großes/I Haus/I")
    _assert_basic_chunks("Da steht ein/B sehr/I großes/I Haus/I")
    _assert_basic_chunks("Da steht ein/B sehr/I schönes/I großes/I Haus/I")
    _assert_basic_chunks("Da steht ein/B sehr/I großes/I Haus/I mit Dach/B")
    _assert_basic_chunks("Da steht ein/B sehr/I großes/I Haus/I mit einem/B blauen/I Dach/I")
    _assert_basic_chunks("Eine/B leckere/I Lasagne/I")
    _assert_basic_chunks("Herr/B Meier/I isst eine/B leckere/I Lasagne/I")
    _assert_basic_chunks("Herr/B Schrödinger/I isst einen/B Kuchen/I")
    _assert_basic_chunks("Herr/B Schrödinger/I isst einen/B leckeren/I Kuchen/I")
    _assert_basic_chunks("Herr/B Karl/I Meier/I isst eine/B leckere/I Lasagne/I")
    _assert_basic_chunks("Herr/B Finn/I Westerwalbesloh/I isst eine/B leckere/I Lasagne/I")
    _assert_basic_chunks("Unsere/B schöne/I Heimat/I geht den/B Bach/I runter")
    _assert_basic_chunks("Er meint das/B Haus/I am grünen/B Hang/I")
    _assert_basic_chunks("Ich/B muss dem/B Hund/I Futter/I geben")  # TODO: see next line for how it should be (but: 'Pariser Innenstadt' should be one NP)
    # assertChunks("Ich muss dem/B Hund/I Futter/B geben");
    _assert_basic_chunks("Das/B Wasser/I , das die/B Wärme/I überträgt")
    _assert_basic_chunks("Er mag das/B Wasser/I , das/B Meer/I und die/B Luft/I")
    _assert_basic_chunks("Schon mehr als zwanzig/B Prozent/I der/B Arbeiter/I sind im Streik/B")
    _assert_basic_chunks("Das/B neue/I Gesetz/I betrifft 1000 Bürger/B")  # '1000' sollte evtl. mit in die NP...
    _assert_basic_chunks("In zwei/B Wochen/I ist Weihnachten/B")
    _assert_basic_chunks("Eines ihrer/B drei/I Autos/I ist blau")

def _assert_match(expr, chunk_tagged_token):
    assert TokenPredicate(expr, False).apply(chunk_tagged_token)


def _assert_no_match(expr, chunk_tagged_token):
    assert not TokenPredicate(expr, False).apply(chunk_tagged_token)


def test_token_predicate():
    """TokenPredicateTest.test"""
    chunk_tags = [ChunkTag('CHUNK1'), ChunkTag('CHUNK2')]
    readings = AnalyzedTokenReadings(AnalyzedToken('mytoken', 'MYPOS', 'mylemma'), 0)
    chunk_tagged_token = ChunkTaggedToken('mytoken', chunk_tags, readings)
    _assert_match('mytoken', chunk_tagged_token)
    _assert_no_match('mytoken2', chunk_tagged_token)
    _assert_match('string=mytoken', chunk_tagged_token)
    _assert_no_match('string=mytoken2', chunk_tagged_token)
    _assert_match('regex=my[abct]oken', chunk_tagged_token)
    _assert_no_match('regex=my[abc]oken', chunk_tagged_token)
    _assert_match('chunk=CHUNK1', chunk_tagged_token)
    _assert_match('chunk=CHUNK2', chunk_tagged_token)
    _assert_no_match('chunk=OTHERCHUNK', chunk_tagged_token)
    _assert_match('pos=MYPOS', chunk_tagged_token)
    _assert_no_match('pos=OTHER', chunk_tagged_token)
    _assert_match('posre=M.POS', chunk_tagged_token)
    _assert_no_match('posre=O.HER', chunk_tagged_token)
    with pytest.raises(Exception):
        _assert_no_match('invalid=token', chunk_tagged_token)
