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
    resolve_signal_datasets,
    write_timeseries,
)
from gwaith.subtraction import subtract_signals

logger = logging.getLogger("gwaith.subtract_signals")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ``gwaith_subtract_signals``."""
    parser = argparse.ArgumentParser(
        prog="gwaith_subtract_signals",
        description="Subtract one or more signal HDF5 files from a data HDF5 file.",
    )
    add_data_input_args(parser, data_help="Path to HDF5 data file")
    add_signal_input_args(parser)
    add_data_output_args(parser, output_help="Output HDF5 file for residual")
    add_gwaith_common_options(parser)

    args = parser.parse_args(argv)
    init_logging(args.verbose)

    try:
        signal_datasets = resolve_signal_datasets(parser, args)

        logger.info("Loading data from %s [%s]", args.data, args.data_dataset)
        data_ts = load_timeseries(args.data, args.data_dataset)

        signals = []
        for sig_file, sig_dataset in zip(args.signal, signal_datasets):
            logger.info("Loading signal from %s [%s]", sig_file, sig_dataset)
            signals.append(load_timeseries(sig_file, sig_dataset))

        residual = subtract_signals(data_ts, signals)

        logger.info("Writing residual to %s [%s]", args.output, args.output_dataset)
        write_timeseries(residual, args.output, args.output_dataset)
        return 0

    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
