"""YAML configuration interface for GWAITH."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file into a dictionary."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML config must parse to a dictionary/mapping")
    return data


def write_yaml_config(path: str | Path, config: dict[str, Any]) -> None:
    """Write a configuration dictionary to a YAML file."""
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary/mapping")
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)
