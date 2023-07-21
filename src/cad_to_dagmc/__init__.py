try:
    # this works for python 3.7 and lower
    from importlib.metadata import version, PackageNotFoundError
except (ModuleNotFoundError, ImportError):
    # this works for python 3.8 and higher
    from importlib_metadata import version, PackageNotFoundError
try:
    __version__ = version("cad_to_dagmc")
except PackageNotFoundError:
    from setuptools_scm import get_version

    __version__ = get_version(root="..", relative_to=__file__)

__all__ = ["__version__"]

from .core import CadToDagmc
from .vertices_to_h5m import vertices_to_h5m
from .brep_part_finder import *
from .brep_to_h5m import *

[CadToDagmc, vertices_to_h5m]
