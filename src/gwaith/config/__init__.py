"""Configuration I/O for GWAITH with format auto-detection."""
from pathlib import Path
from typing import Any

from .yaml_config import load_yaml_data
from .types import GwaithConfig
from .parser import GwaithConfigParser, add_config_input_options
from .utils import safe_update, get_dict_value, resolve_match

__all__ = [
    "add_config_input_options",
    "load_yaml_data",
    "GwaithConfig",
    "GwaithConfigParser",
    "safe_update",
    "get_dict_value",
    "resolve_match"
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
        "Unsupported config format: "
        f"{suffix!r}. Supported formats: .yaml, .yml"
    )
