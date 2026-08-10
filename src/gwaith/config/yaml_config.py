"""YAML configuration interface for GWAITH."""

import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

# 1. Completely clear the built-in implicit resolvers for everything
# except what we want (which is basically nothing).
# This prevents anything from being seen as something which is not a string.
yaml.SafeLoader.yaml_implicit_resolvers = {}

# 2. Add back ONLY the string resolver as a catch-all
yaml.add_implicit_resolver(
    "tag:yaml.org,2002:str", re.compile(r".*"), Loader=yaml.SafeLoader
)

# 3. If the value is missing, give back an empty string rather than None
yaml.SafeLoader.add_constructor("tag:yaml.org,2002:null", lambda loader, node: "")


logger = logging.getLogger("gwaith.config.yaml")


def load_yaml_data(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file into a dictionary."""
    p = Path(path)
    logger.info(f"Loading YAML Config from: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def write_yaml_data(data: dict[str, Any], output_path: str | Path) -> None:
    """Write config data to a YAML file."""
    p = Path(output_path)
    logger.info(f"Writing YAML Config to: {p}")
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False)

__all__ = ["load_yaml_data", "write_yaml_data"]