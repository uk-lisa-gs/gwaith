"""Pegasus workflow exporter."""
import logging
from pathlib import Path
from .exporter import GwaithExporter, GwaithExportResult
from gwaith import import_optional


pegasus_api = import_optional("pegasus.api")
logger = logging.getLogger(__name__)


class GwaithPegasusExporter(GwaithExporter):
    """GwaithPegasusExporter."""

    def export(self, workflow, target_dir) -> GwaithExportResult:
        """Export a Pegasus workflow object to a DAX file.

        Args:
            workflow (pegasus.api.Workflow): The Pegasus workflow object.
            target_dir (Path): The directory to write the files to.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        dax_path = target_dir / f"{workflow.name}.dax"

        workflow.write(str(dax_path))
        logger.info(f"Pegasus DAX file written to: {dax_path}")

        return GwaithExportResult(manifest=str(dax_path), master_script=None)