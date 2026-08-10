"""Configuration I/O for GWAITH with format auto-detection."""

from pathlib import Path
from typing import Any

from .ini_config import load_ini_data, write_ini_data
from .parser import GwaithConfigParser, add_config_input_options
from .types import GwaithConfig
from .utils import get_dict_value, resolve_match, safe_update
from .yaml_config import load_yaml_data, write_yaml_data

__all__ = [
    "GwaithConfig",
    "GwaithConfigParser",
    "add_config_input_options",
    "get_dict_value",
    "resolve_match",
    "safe_update",
]


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
        write_yaml_data(filepath, config)
        return
    elif suffix in (".ini"):
        write_ini_data(filepath, config)
        return
    raise ValueError(
        f"Unsupported config format: {suffix!r}. Supported formats: .yaml, .yml, .ini"
    )


def load_config(filepath: str | Path) -> dict[str, Any]:
    """Load a configuration file, auto-detecting format from extension.

    Parameters
    ----------
    filepath:
        Path to the configuration file.


    Returns
    -------
    dict[str, Any]:
        The loaded configuration
    """
    suffix = Path(filepath).suffix.lower()
    if suffix in (".yaml", ".yml"):
        return load_yaml_data(filepath)
    elif suffix in (".ini"):
        return load_ini_data(filepath)
    raise ValueError(
        f"Unsupported config format: {suffix!r}. Supported formats: .yaml, .yml, .ini"
    )
