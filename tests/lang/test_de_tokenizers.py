"""Port of org.languagetool.tokenizers.de.GermanCompoundTokenizerTest and
GermanSRXSentenceTokenizerTest (plus tests of GermanWordTokenizer and the
jWordSplitter port)."""

import pytest

from conftest import require_dictionaries
from langtool.api import get_language
from langtool.extensions import SRXSentenceTokenizer
from langtool.lang.de.compound_tokenizer import GermanCompoundTokenizer, get_non_strict_instance, \
    get_strict_instance
from langtool.lang.de.tokenizers import GermanWordTokenizer


@pytest.fixture(autouse=True, scope='module')
def _dicts():
    require_dictionaries('de')


def _java_list(items):
    # List.toString()
    return '[' + ', '.join(items) + ']'


# --- GermanCompoundTokenizerTest ---

def test_compound_tokenizer():
    """GermanCompoundTokenizerTest.test"""
    tokenizer = GermanCompoundTokenizer(True)
    assert _java_list(tokenizer.tokenize('Bahnhofsuhr')) == '[Bahnhofs, uhr]'
    assert _java_list(tokenizer.tokenize('natofreundlich')) == '[nato, freundlich]'
    assert _java_list(tokenizer.tokenize('natofreundliches')) == '[nato, freundliches]'
    assert _java_list(tokenizer.tokenize('Firefox-Add-on')) == '[Firefox, , Add-on]'  # why the space?


@pytest.mark.parametrize('word,strict,non_strict', [
    # results of jWordSplitter 4.7 / GermanCompoundTokenizer in Java
    ('Schranktüren', ['Schrank', 'türen'], ['Schrank', 'türen']),
    ('Haustürschlüssel', ['Haus', 'tür', 'schlüssel'], ['Haus', 'türschlüssel']),
    ('Urlaubsorte', ['Urlaubs', 'orte'], ['Urlaubs', 'orte']),
    ('Verkehrsamt', ['Verkehrs', 'amt'], ['Verkehrs', 'amt']),
    ('Donaudampfschifffahrt', ['Donau', 'dampf', 'schiff', 'fahrt'], ['Don', 'audampfschifffahrt']),
    ('Rettungshubschraubernotlandeplatz', ['Rettungs', 'hubschrauber', 'not', 'lande', 'platz'],
     ['Rettung', 'shubschraubernotlandeplatz']),
    ('Absolventen', ['Absolventen'], ['Absolventen']),  # exception added by GermanCompoundTokenizer
    ('Reinigungstabs', ['Reinigungs', 'tabs'], ['Reinigungs', 'tabs']),
    ('x' * 71, ['x' * 71], ['x' * 71]),  # InputTooLongException
])
def test_compound_splits(word, strict, non_strict):
    """Splits of the strict and non-strict instances as in Java"""
    assert get_strict_instance().tokenize(word) == strict
    assert get_non_strict_instance().tokenize(word) == non_strict


def test_get_all_splits():
    """AbstractWordSplitter.getAllSplits"""
    splits = get_strict_instance().word_splitter.get_all_splits('Haustür')
    assert ['Haus', 'tür'] in splits


# --- GermanWordTokenizer ---

def test_word_tokenizer():
    """GermanWordTokenizer: '_' and '‚' are tokenizing characters"""
    assert GermanWordTokenizer().tokenize('Das ‚Haus_Boot‘ ist gut.') == \
        ['Das', ' ', '‚', 'Haus', '_', 'Boot', '‘', ' ', 'ist', ' ', 'gut', '.']
    assert get_language('de-DE').word_tokenizer.tokenize('Freund_innen') == ['Freund', '_', 'innen']


# --- GermanSRXSentenceTokenizerTest ---

SPLITS = [
    # NOTE: sentences here need to end with a space character so they
    # have correct whitespace when appended:
    ('Dies ist ein Satz.',),
    ('Dies ist ein Satz. ', 'Noch einer.'),
    ('Dies ist ein Satz.¹ ', 'Noch einer.'),
    ('Ein Satz! ', 'Noch einer.'),
    ('Ein Satz... ', 'Noch einer.'),
    ('Unter http://www.test.de gibt es eine Website.',),
    ('Das Schreiben ist auf den 3.10. datiert.',),
    ('Das Schreiben ist auf den 31.1. datiert.',),
    ('Das Schreiben ist auf den 3.10.2000 datiert.',),
    ('Natürliche Vererbungsprozesse prägten sich erst im 18. und frühen 19. Jahrhundert aus.',),
    ('Das ist ja 1a. ', 'Und das auch.'),
    ('Hallo, ich bin’s. ', 'Könntest du kommen?'),
    ('In der 1. Bundesliga kam es zum Eklat.',),
    ('Dies ist, z. B., ein Satz.',),
    ('Da hatte es über 30 °C. ', 'Hier kommt der nächste Satz.'),
    ('Das 1. Internationale Filmfestival findet nächste Woche statt.',),
    ('Friedrich I., auch bekannt als Friedrich der Große.',),
    ('Friedrich II., auch bekannt als Friedrich der Große.',),
    ('Friedrich IIXC., auch bekannt als Friedrich der Große.',),
    ('Friedrich II. öfter auch bekannt als Friedrich der Große.',),
    ('Friedrich VII. öfter auch bekannt als Friedrich der Große.',),
    ('Friedrich X. öfter auch bekannt als Friedrich der Zehnte.',),
    ('Ein Satz! ', 'Noch einer.'),
    ('Dies ist, z. B., ein Satz.',),
    ('Hier steht was mit mehr Wörtern, weil wir mal sehen wollen, wie denn so die Erkennung der Satzlänge geht, '
     'wenn die Sätze doch deutlich länger werden, also wirklich deutlich länger als das normal. ',
     'Hier steht etwas anderes.'),
    ('Heute ist der 13.12.2004.',),
    ('Heute ist der 13. Dezember.',),
    ('Heute ist der 1. Januar.',),
    ('Es geht am 24.09. los.',),
    ('Es geht um ca. 17:00 los.',),
    ('Das in Punkt 3.9.1 genannte Verhalten.',),
    ('Diese Periode begann im 13. Jahrhundert und damit bla.',),
    ('Diese Periode begann im 13. oder 14. Jahrhundert und damit bla.',),
    ('Diese Periode datiert auf das 13. bis zum 14. Jahrhundert und damit bla.',),
    ('Das gilt lt. aktuellem Plan.',),
    ('Orangen, Äpfel etc. werden gekauft.',),
    ('Das ist,, also ob es bla.',),
    ('Das ist es.. ', 'So geht es weiter.'),
    ('Das hier ist ein(!) Satz.',),
    ('Das hier ist ein(!!) Satz.',),
    ('Das hier ist ein(?) Satz.',),
    ('Das hier ist ein(???) Satz.',),
    ('Das hier ist ein(???) Satz.',),
    ('»Der Papagei ist grün.« ', 'Das kam so.'),
    ('»Der Papagei ist grün«, sagte er',),
    # TODO: derzeit unterscheiden wir nicht, ob nach dem Doppelpunkt ein
    # ganzer Satz kommt oder nicht:
    ('Das war es: gar nichts.',),
    ('Das war es: Dies ist ein neuer Satz.',),
    # Tests created as part of regression testing of SRX tokenizer.
    # They come from Schuld und Sühne (Crime and Punishment) book.
    ('schlug er die Richtung nach der K … brücke ein. ',),
    ('sobald ich es von einem Freunde zurückbekomme …« Er wurde verlegen und schwieg.',),
    ('Er kannte eine Unmenge Quellen, aus denen er schöpfen konnte, d. h. natürlich, wo er durch Arbeit sich '
     'etwas verdienen konnte.',),
    ('Stimme am lautesten heraustönte …. ', 'Sobald er auf der Straße war'),
    ('»Welche Wohnung?" ', '»Die, wo wir arbeiten.'),
    ('»Nun also, wie ist\'s?« fragte Lushin und blickte sie fest an.',),
    ('»Nun also, wie ist es?« fragte Lushin und blickte sie fest an.',),
    ('„Nun also, wie ist es?“ fragte Lushin und blickte sie fest an.',),
    ('»Nun also, wie ist es?« ', 'Dann ging er.'),
    ('Dies ist ein Satz mit einer EMail.Addresse@example.com!',),
    ('Sonderbarerweise sind auch Beispiel!Eins@example.com und Foo?Bar@example.com valide.',),
    ('Er kauft Obst, Gemüse, Brot, Milch, usw. ', 'Danach geht er nach Hause.'),
    ('Sie kaufte Bücher, Hefte, Stifte usw., weil sie sich auf das neue Schuljahr vorbereiten wollte.',),
    ('Im Supermarkt gibt es viele Sorten von Käse, Wurst, Brot usw. und alle sind sehr lecker.',),
    ('Im Büro gibt es Computer, Drucker, Telefone etc. ',
     'Die Mitarbeiter arbeiten den ganzen Tag an verschiedenen Projekten.'),
    ('Die Ergebnisse sind in Tabellen, Grafiken, Diagrammen etc. dargestellt.',),
    ('Master of Law (LL.B.)',),
    ('Master of Law (LL. B.)',),
]


@pytest.fixture(scope='module')
def stokenizer():
    return SRXSentenceTokenizer(get_language('de-DE'))


@pytest.mark.parametrize('sentences', SPLITS)
def test_sentence_tokenize(stokenizer, sentences):
    """GermanSRXSentenceTokenizerTest.testTokenize (TestTools.testSplit)"""
    assert stokenizer.tokenize(''.join(sentences)) == list(sentences)


@pytest.mark.parametrize('text', [
    'Dies ist ein Satz.  Noch einer.',
    'Dies ist ein Satz.    Noch einer.',
    'Dies ist ein Satz.  Noch einer.',
    'Dies ist ein Satz.    Noch einer.',
])
def test_sentence_tokenize_nbsp(stokenizer, text):
    """GermanSRXSentenceTokenizerTest.testTokenize: non-breaking space,
    happen e.g. in online editors, because HTML merges spaces"""
    assert len(stokenizer.tokenize(text)) == 2
