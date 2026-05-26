"""Workflow exporter package."""

from __future__ import annotations

import os

from .bash_exporter import GwaithBashExporter
from .exporter import GwaithExportResult, GwaithExporter

_EXPORTER_ENV_VAR = "GWAITH_EXPORTER"


def get_exporter(name: str | None = None) -> GwaithExporter:
    """Return the configured workflow exporter.

    The exporter can be selected with `name` or the `GWAITH_EXPORTER`
    environment variable. Bash is the default for now.
    """
    exporter_name = (name or os.getenv(_EXPORTER_ENV_VAR, "bash")).strip().lower()
    if exporter_name in {"bash", "shell", "default"}:
        return GwaithBashExporter()
    raise ValueError(f"Unknown workflow exporter: {exporter_name}")


__all__ = [
    "GwaithExportResult",
    "GwaithExporter",
    "GwaithBashExporter",
    "get_exporter",
]
