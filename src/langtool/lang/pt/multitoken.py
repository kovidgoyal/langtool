"""Port of org.languagetool.rules.pt.PortugueseMultitokenSpeller."""

import threading

from ...rules.multitoken import MultitokenSpeller
from .spelling import prepare_line_for_speller


class PortugueseMultitokenSpeller(MultitokenSpeller):
    """The MultitokenSpeller for /pt/multiwords.txt, /spelling_global.txt
    and /pt/hyphenated_words.txt (the lines are prepared with
    Portuguese.prepareLineForSpeller)."""

    def prepare_line_for_speller(self, s):
        return prepare_line_for_speller(s)


_instance = []
_lock = threading.Lock()


def portuguese_multitoken_speller(language):
    """PortugueseMultitokenSpeller.INSTANCE, for the language pt-PT (whose
    default spelling rule is used) in Java, for all variants"""
    with _lock:
        if not _instance:
            from ...api import get_language
            pt_pt = get_language('pt-PT')
            _instance.append(PortugueseMultitokenSpeller(
                pt_pt, [pt_pt.resource_path('pt/multiwords.txt'), pt_pt.resource_path('spelling_global.txt'),
                        pt_pt.resource_path('pt/hyphenated_words.txt')],
                pt_pt.get_default_spelling_rule()))
        return _instance[0]
