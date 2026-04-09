"""GWAITH: tools for gravitational wave analysis."""

from __future__ import annotations

import argparse
import logging
from importlib.metadata import PackageNotFoundError, version

__version__ = "0.1.0"

_LOG_FORMAT = "%(levelname)s: %(asctime)s: %(name)s.%(module)s: %(message)s"
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


__all__ = [
    "__version__",
    "add_gwaith_common_options",
    "init_logging",
]
