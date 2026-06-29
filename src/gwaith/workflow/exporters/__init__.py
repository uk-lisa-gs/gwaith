"""Workflow exporter package."""

from __future__ import annotations

import os
from pathlib import Path

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


def output_workflow(
        workflow,
        exporter: GwaithExporter | None = None,
):
    """Output a built workflow to disk using an exporter.
    
    Args:
        workflow: Built GwaithWorkflow to export
        exporter: Exporter instance to use (defaults to environment selection)
        
    Returns:
        GwaithWorkflow with manifest and master_script populated
    """
    if exporter is None:
        exporter = get_exporter()
    
    target_dir = Path(workflow.workflow_dir)
    output = exporter.export(workflow, target_dir)
    workflow.manifest = output.manifest
    workflow.master_script = output.master_script
    return workflow


__all__ = [
    "GwaithExportResult",
    "GwaithExporter",
    "GwaithBashExporter",
    "GwaithHTCondorExporter",
    "GwaithPegasusExporter",
    "GwaithSlurmExporter",
    "GwaithSnakemakeExporter",
    "get_exporter",
    "output_workflow",
]
