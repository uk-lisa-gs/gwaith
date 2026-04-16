"""Utility functions for the GWAITH package."""
import importlib
import inspect

import argparse
import logging
from importlib.metadata import PackageNotFoundError, version

__version__ = "0.1.0"

_LOG_FORMAT = "%(levelname)s:%(asctime)s:%(name)s:%(message)s"
_LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"

def _resolve_version() -> str:
    try:
        return version("gwaith")
    except PackageNotFoundError:
        return __version__

def add_gwaith_common_options(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add common GWAITH CLI options.

    - `--version`: print package version
    - `-v/--verbose`: increase logging level (`-v` => INFO, `-vv` => DEBUG)
    """
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_resolve_version()}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (use -v for INFO, -vv for DEBUG)",
    )
    return parser

def init_logging(verbosity: int = 0) -> int:
    """Initialize unified logging format and return selected level."""
    if verbosity <= 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(level=level, format=_LOG_FORMAT, datefmt=_LOG_DATEFMT)
    return level


class _MissingModule:
    def __init__(self, name):
        self._name = name
    def __getattr__(self, attr):
        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame, 2)
        func = outer[1][3] if len(outer) > 1 else '<unknown>'
        msg = (f"The function '{func}' tried to access attribute '{attr}' of module '"
                f"{self._name}', but it is not installed. "
                f"Please install '{self._name}' to enable this functionality.")
        raise ImportError(msg)

def import_optional(module_name):
    """
    Attempt to import a module by name. If the module is not found,
    return a stub object that raises ImportError with a helpful message
    when any attribute is accessed.

    Parameters
    ----------
    module_name : str
        The name of the module to import.

    Returns
    -------
    module or stub : module or object
        The imported module, or a stub that raises ImportError on attribute access.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return _MissingModule(module_name)
    