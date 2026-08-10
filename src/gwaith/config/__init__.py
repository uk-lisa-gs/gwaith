"""Configuration I/O for GWAITH with format auto-detection."""

from pathlib import Path
from typing import Any

from .parser import GwaithConfigParser, add_config_input_options
from .types import GwaithConfig
from .utils import get_dict_value, resolve_match, safe_update
from .yaml_config import load_yaml_data

__all__ = [
    "GwaithConfig",
    "GwaithConfigParser",
    "add_config_input_options",
    "get_dict_value",
    "load_yaml_data",
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
        _write_config_yaml(filepath, config)
        return
    raise ValueError(
        f"Unsupported config format: {suffix!r}. Supported formats: .yaml, .yml"
    )
