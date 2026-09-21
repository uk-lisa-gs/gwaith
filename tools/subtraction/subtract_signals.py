#!/usr/bin/env python
"""Subtract one or more signal timeseries from a data timeseries."""

from __future__ import annotations

import argparse
import logging

from gwaith import add_gwaith_common_options, init_logging
from gwaith.io import (
    add_data_input_args,
    add_data_output_args,
    add_signal_input_args,
    load_timeseries,
    resolve_filenames_datasets,
    write_timeseries,
)
from gwaith.subtraction import subtract_signals

logger = logging.getLogger("gwaith.subtract_signals")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ``gwaith_subtract_signals``."""
    parser = argparse.ArgumentParser(
        prog="gwaith_subtract_signals",
        description=(
            "Subtract one or more signal HDF5 files from a data "
            "HDF5 file. The signal files must have the same structure as the data file."
        ),
    )
    add_data_input_args(parser)
    # Pass an explicit, unambiguous dataset option. Without this the helper
    # defaults to "--signal-dataset", whose prefix collides with
    # "--signal-files"/"--signal-groups" under argparse abbreviation matching.
    add_signal_input_args(parser)
    add_data_output_args(parser)
    parser.add_argument(
        "--channels",
        nargs='+',
        required=True,
        help="Data channels to perform the subtraction",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Error out if an output dataset with the same name already exists "
        "in the output file (default: overwrite existing datasets)",
    )
    add_gwaith_common_options(parser)

    args = parser.parse_args(argv)
    init_logging(args.verbose)


    try:
        logger.info("Loading data from %s", args.data)
        data_ts = {
            channel: load_timeseries(args.data, dataset=channel)
            for channel in args.channels
        }

        signals = []
        for sig_file in args.signal_files:
            logger.info("Loading signal from %s", sig_file)
            signals.append(
                {
                    channel: load_timeseries(sig_file, dataset=channel)
                    for channel in args.channels
                }
            )

        residual = subtract_signals(data_ts, signals, channels=args.channels)

        logger.info("Writing residual to %s", args.output)
        for channel in args.channels:
            logger.info("Channel %s", channel)
            write_timeseries(
                residual[channel],
                args.output,
                channel,
                overwrite=not args.no_overwrite,
            )
        return 0

    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())