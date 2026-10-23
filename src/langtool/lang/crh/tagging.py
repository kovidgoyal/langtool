"""Port of org.languagetool.tagging.crh.CrimeanTatarTagger."""

from ...tagging import BaseTagger


class CrimeanTatarTagger(BaseTagger):
    """Crimean Tatar part-of-speech tagger: a BaseTagger for
    /crh/crimean_tatar.dict with tagLowercaseWithUppercase=false and only
    /crh/added.txt as manual additions (getManualAdditionsFileNames, no
    added_custom.txt). Java uses Locale("uk", "UA") for lowercasing (there is
    no crh_UA locale in Java), which has no special case mapping, so the
    default str.lower is right."""

    def __init__(self, dictionary, resource_dir=None):
        super().__init__(dictionary, 'crh', resource_dir, tag_lowercase_with_uppercase=False,
                         manual_additions=['added.txt'])
