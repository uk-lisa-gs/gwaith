"""Configuration I/O for GWAITH with format auto-detection."""
from pathlib import Path
from typing import Any

from .yaml_config import load_yaml_data
from .types import GwaithConfig
from .parser import GwaithConfigParser
from .utils import safe_update, get_dict_value, resolve_match


def add_config_input_options(parser):
    parser.add_argument(
        '--config-files',
        required=True,
        nargs='+',
        help='Configuration files to control the workflow'
    )

__all__ = [
    "add_config_input_options",
    "load_yaml_data",
    "GwaithConfig",
    "GwaithConfigParser",
    "safe_update",
    "get_dict_value",
    "resolve_match"
]


def load_config(filepath: str | Path) -> dict[str, Any]:
    """Load a configuration file, auto-detecting format from extension.

    For YAML/INI files, interpolation tokens in string values are resolved
    using :class:`GwaithConfigParser`.

    Parameters
    ----------
    filepath:
        Path to the configuration file.

    Returns
    -------
    config:
        Parsed configuration dictionary.

    Raises
    ------
    ValueError:
        If file extension is not recognized.
    """
    suffix = Path(filepath).suffix.lower()
    if suffix in (".yaml", ".yml"):
        return GwaithConfigParser.from_file(filepath).as_dict()
    raise ValueError(
        "Unsupported config format: "
        f"{suffix!r}. Supported formats: .yaml, .yml"
    )


def write_config(filepath: str | Path, config: dict[str, Any]) -> None:
    """Write a configuration file, auto-detecting format from extension.

    Parameters
    ----------
    filepath:
        Path to the configuration file.
    config:
        Configuration dictionary to write.

    Raises
    ------
    ValueError:
        If file extension is not recognized.
    """
    suffix = Path(filepath).suffix.lower()
    if suffix in (".yaml", ".yml"):
        _write_config_yaml(filepath, config)
        return
    raise ValueError(
        "Unsupported config format: "
        f"{suffix!r}. Supported formats: .yaml, .yml"
    )
