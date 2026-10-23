"""Language specific code (ports of the Java code of the language modules of
LanguageTool), one package per language code (a trailing underscore is added
when the code is a Python keyword, like ``is_``). Importing this package
registers the implementations with langtool.extensions."""

from . import is_  # noqa: F401
from . import lt  # noqa: F401
from . import ta  # noqa: F401
