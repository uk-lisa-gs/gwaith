"""Configuration I/O for GWAITH with format auto-detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .normalise import (
    normalise_config,
    normalise_workflow_config,
)
from .yaml_config import (
    load_yaml_config as _load_config_yaml,
    write_yaml_config as _write_config_yaml,
)

__all__ = [
    "load_config",
    "write_config",
    "normalise_config",
    "normalise_workflow_config",
]


def load_config(filepath: str | Path) -> dict[str, Any]:
    """Load a configuration file, auto-detecting format from extension.

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
        return _load_config_yaml(filepath)
    raise ValueError(
        f"Unsupported config format: {suffix!r}. " f"Supported formats: .yaml, .yml"
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
        f"Unsupported config format: {suffix!r}. " f"Supported formats: .yaml, .yml"
    )
