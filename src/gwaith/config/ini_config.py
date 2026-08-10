"""INI configuration interface for GWAITH."""

import logging
from collections.abc import Sequence
from configparser import ConfigParser
from pathlib import Path
from typing import Any

logger = logging.getLogger("gwaith.config.ini")


def load_ini_data(paths: str | Path | Sequence[str | Path]) -> dict[str, Any]:
    """Load INI config file(s) and consolidate them into a single dictionary."""
    if isinstance(paths, (str, Path)):
        paths = [paths]

    parser = ConfigParser()
    read_files = parser.read(paths)
    logger.info(f"Loading INI Config from: {read_files}")

    # Convert ConfigParser object to a dictionary
    config = {section: dict(parser.items(section)) for section in parser.sections()}

    # Convert numeric and boolean strings to their respective types
    for section in config:
        for key, value in config[section].items():
            if isinstance(value, str):
                if value.lower() in ("true", "false"):
                    config[section][key] = value.lower() == "true"
                elif value.replace(".", "", 1).isdigit():
                    config[section][key] = float(value) if "." in value else int(value)
    return config


__all__ = ["load_ini_data"]
