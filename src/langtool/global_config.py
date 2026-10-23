"""Port of org.languagetool.GlobalConfig (the verbose flag; the other
settings are for the excluded components)."""

_verbose = False


def is_verbose():
    """Whether we need to track additional information like e.g. the
    disambiguation log to show in verbose mode."""
    return _verbose


def set_verbose(verbose):
    global _verbose
    _verbose = bool(verbose)
