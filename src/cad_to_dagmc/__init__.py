try:
    # this works for python 3.7 and lower
    from importlib.metadata import PackageNotFoundError, version
except (ModuleNotFoundError, ImportError):
    # this works for python 3.8 and higher
    from importlib_metadata import PackageNotFoundError, version
try:
    __version__ = version("cad_to_dagmc")
except PackageNotFoundError:
    from setuptools_scm import get_version

    __version__ = get_version(root="..", relative_to=__file__)

__all__ = ["CadToDagmcMesherNotFoundError", "PyMoabNotFoundError", "__version__"]

from .core import *
from .core import CadToDagmcMesherNotFoundError, PyMoabNotFoundError
