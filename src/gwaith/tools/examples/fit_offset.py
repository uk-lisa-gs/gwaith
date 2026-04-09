#!/usr/bin/env python
"""Estimate constant offset from data and output signal/parameters.

Standard module interface:
- Input: data file (+ optional priors)
- Output: signal timeseries + parameter file
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from gwaith import add_gwaith_common_options, init_logging
from gwaith.io import add_data_input_args, add_data_output_args, load_timeseries, write_timeseries
from gwaith.types import TimeSeries
from gwaith.tools.examples.common import apply_bounds, get_param_prior, load_prior_file

logger = logging.getLogger("gwaith.examples.fit_offset")


def fit_offset(data_ts: TimeSeries, priors: dict) -> float:
    """Estimate constant offset using the sample mean and optional bounds."""
    offset_prior = get_param_prior(priors, "offset")

    if "value" in offset_prior:
        estimate = float(offset_prior["value"])
    else:
        estimate = float(data_ts.data.mean())

    return apply_bounds(estimate, offset_prior)


def offset_model(ts: TimeSeries, offset: float) -> TimeSeries:
    return TimeSeries(data=0.0 * ts.data + offset, epoch=ts.epoch, delta_t=ts.delta_t)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_fit_offset",
        description="Fit a constant offset and output signal timeseries + parameters.",
    )
    add_data_input_args(parser, data_help="Input HDF5 data file")
    parser.add_argument("--priors", required=False, help="Optional prior file (.yaml/.yml or .ini)")
    parser.add_argument("--init-params", required=False, help=argparse.SUPPRESS)
    add_data_output_args(
        parser,
        output_option="--output-signal",
        dataset_option="--output-signal-dataset",
        default_dataset="signal",
        output_help="Output HDF5 signal file",
    )
    parser.add_argument("--output-params", required=True, help="Output YAML parameters file")
    add_gwaith_common_options(parser)
    args = parser.parse_args(argv)

    init_logging(args.verbose)

    try:
        data_ts = load_timeseries(args.data, args.data_dataset)

        prior_path = args.priors or args.init_params
        priors = load_prior_file(prior_path) if prior_path else {}
        offset = fit_offset(data_ts, priors)

        signal_ts = offset_model(data_ts, offset)
        write_timeseries(signal_ts, args.output_signal, args.output_signal_dataset)

        # Emit exactly one scalar value as requested.
        Path(args.output_params).write_text(f"{offset}\n", encoding="utf-8")

        logger.info("Wrote signal to %s and parameters to %s", args.output_signal, args.output_params)
        return 0
    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
