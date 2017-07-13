import os
import errno

from errors import DotEnsimeNotFound, BadEnsimeConfig
from config import ProjectConfig


def _locations(window):
    """Intelligently guess the appropriate .ensime file locations for the
    given window. Return: list of possible locations."""
    return [(f + os.sep + ".ensime") for f in window.folders() if os.path.exists(f + os.sep + ".ensime")]


def load(window):
    """Intelligently guess the appropriate .ensime file location for the
    given window. Load the .ensime and parse as s-expression.
    Return: (inferred project root directory, config sexp)
    """
    for f in _locations(window):
        try:
            conf = ProjectConfig(f)
            return conf
        except Exception:
            exc_type, exc_val, _ = os.sys.exc_info()
            raise BadEnsimeConfig("""Ensime has failed to parse the .ensime configuration file at
{loc} because ofthe following error:
{typ} : {val}""".format(loc=str(f), typ=str(exc_type), val=str(exc_val)))
    raise DotEnsimeNotFound(errno.ENOENT,
                            """Ensime has failed to find a .ensime file within this project.
Create a .ensime file by running'sbt ensimeConfig' or equivalent for your build tool.
We looked at : """,
                            window.folders())
