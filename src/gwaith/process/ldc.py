"""LDC file processing helpers for GWAITH ingestion."""

import logging
from pathlib import Path

logger = logging.getLogger("gwaith.process.ldc")


def process_ldc(parser, args):
    """Process an LDC input file using parsed ingest CLI arguments.

    Args:
        parser: Argument parser used to build the ingest command.
        args: Parsed CLI arguments from ingest_data.

    Returns:
        dict[str, TimeSeries]: Mapping from output dataset name to TimeSeries.
    """
    input_path = Path(args.data)
    orbits_path = Path(args.orbits)
    signal_inputs = getattr(args, "signal", None) or []
    signal_datasets = getattr(args, "signal_dataset", None) or []
    processor_options = (
        args.processor_options if isinstance(args.processor_options, dict) else {}
    )
    logger.info(
        "Processing LDC file %s with orbits=%s signals=%s signal_datasets=%s options=%s",
        input_path,
        orbits_path,
        signal_inputs,
        signal_datasets,
        processor_options,
    )
    raise NotImplementedError("LDC processing is not implemented yet")
