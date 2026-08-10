"""Data ingestion CLI for GWAITH.

This tool selects a file-type-specific processor and writes the resulting
output channels into a new timeseries file.
"""

import argparse
import logging

from gwaith import add_gwaith_common_options, init_logging
from gwaith.io import (
    add_data_input_args,
    write_mojito_orbits,
    write_mojito_tdis,
)
from gwaith.process import (
    add_data_processing_args,
    process,
)

logger = logging.getLogger("gwaith.ingest_data")


def add_ingest_data_argument_parser(argv=None):
    parser = argparse.ArgumentParser()
    add_gwaith_common_options(parser)
    add_data_input_args(parser)
    parser.add_argument(
        "--output-tdi",
        required=True,
        help="Output HDF5 file for the initial tdi Mojito file.",
    )
    parser.add_argument(
        "--output-orbits",
        required=True,
        help="Output HDF5 file for static orbits-only Mojito file.",
    )
    add_data_processing_args(parser)
    parser.add_argument(
        "--chunk-duration",
        type=float,
        help="Chunk duration in seconds for processing.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=float,
        default=0,
        help="Overlap between chunks in seconds.",
    )
    args = parser.parse_args(argv)
    return (parser, args)


def main(argv=None):
    """
    Returns:
        int:
    """
    _, args = add_ingest_data_argument_parser(argv)
    init_logging(args.verbose, default_level=1)
    # Convert the key:value pairs from the processor options

    if args.chunk_duration:
        if not hasattr(args, "tstart") or not hasattr(args, "duration"):
            logger.error("Chunking requires --tstart and --duration to be specified.")
            return 1
        args.processor_options["chunk_duration"] = args.chunk_duration
        args.processor_options["chunk_overlap"] = args.chunk_overlap
        args.processor_options["tstart"] = args.tstart
        args.processor_options["duration"] = args.duration

    try:
        output_data = process(args.data, args.processor_options, args.processor)
        logger.info("Processed data")
        print(output_data)
        write_mojito_tdis(output_data["tdis"], args.output_tdi)
        write_mojito_orbits(output_data["orbits"], args.output_orbits)
        logger.info(
            "Wrote TDI output to %s and static orbits to %s",
            args.output_tdi,
            args.output_orbits,
        )

        return 0
    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
