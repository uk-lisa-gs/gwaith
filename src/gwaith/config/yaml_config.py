"""YAML configuration interface for GWAITH."""

from pathlib import Path
from typing import Any, Sequence
import logging
import yaml
import re

# 1. Completely clear the built-in implicit resolvers for everything 
# except what we want (which is basically nothing).
# This prevents anything from being seen as something which is not a string.
yaml.SafeLoader.yaml_implicit_resolvers = {}

# 2. Add back ONLY the string resolver as a catch-all
yaml.add_implicit_resolver(
    'tag:yaml.org,2002:str', 
    re.compile(r'.*'), 
    Loader=yaml.SafeLoader
)

# 3. If the value is missing, give back an empty string rather than None
yaml.SafeLoader.add_constructor(
    'tag:yaml.org,2002:null', 
    lambda loader, node: ""
)

logger = logging.getLogger('gwaith.config.yaml')


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> None:
    """Recursively merge the update dictionary into the base dictionary."""
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_yaml_data(paths: str | Path | Sequence[str | Path]) -> dict[str, Any]:
    """Load YAML config file(s) and consolidate them into a single dictionary."""
    if isinstance(paths, (str, Path)):
        paths = [paths]

    consolidated: dict[str, Any] = {}
    for path in paths:
        p = Path(path)
        logger.info(f"Loading YAML Config from: {p}")
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            _deep_merge(consolidated, data)
            
    return consolidated


__all__ = [
    "write_to_yaml",
    "load_yaml_data",
]
