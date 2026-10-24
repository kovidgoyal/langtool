"""Language specific code (ports of the Java code of the language modules of
LanguageTool), one package per language code (a trailing underscore is added
when the code is a Python keyword, like ``is_``). Importing this package
registers the implementations with langtool.extensions."""

from . import ast  # noqa: F401
from . import be  # noqa: F401
from . import br  # noqa: F401
from . import crh  # noqa: F401
from . import da  # noqa: F401
from . import el  # noqa: F401
from . import eo  # noqa: F401
from . import fa  # noqa: F401
from . import gl  # noqa: F401
from . import is_  # noqa: F401
from . import it  # noqa: F401
from . import km  # noqa: F401
from . import lt  # noqa: F401
from . import ml  # noqa: F401
from . import nl  # noqa: F401
from . import pl  # noqa: F401
from . import ro  # noqa: F401
from . import ru  # noqa: F401
from . import sk  # noqa: F401
from . import sl  # noqa: F401
from . import sv  # noqa: F401
from . import ta  # noqa: F401
from . import tl  # noqa: F401
