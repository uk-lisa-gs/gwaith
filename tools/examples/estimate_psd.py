#!/usr/bin/env python
"""Estimate power spectral density (PSD) using Welch's method.

Usage:
    gwaith_estimate_psd --data residual.h5 --output psd.h5

Run gwaith_subtract_signals first to produce the residual.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
from scipy import signal

from gwaith import add_gwaith_common_options, init_logging
from gwaith.io import (
    add_data_input_args,
    add_data_output_args,
    load_timeseries,
    write_frequencyseries,
)
from gwaith.types import FrequencySeries

logger = logging.getLogger("gwaith.estimate_psd")


def load_data(filepath: str, dataset_name: str = "data") -> np.ndarray:
    """Backward-compatible loader returning raw ndarray samples."""
    return load_timeseries(filepath, dataset_name).data


def estimate_psd(
    data: np.ndarray,
    fs: float = 1.0,
    nperseg: int | None = None,
    noverlap: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate power spectral density using Welch's method.

    Parameters
    ----------
    data : np.ndarray
        Input timeseries.
    fs : float, optional
        Sampling frequency (default 1 Hz).
    nperseg : int, optional
        Length of each segment. If None, uses 256 or len(data)//8, whichever is smaller.
    noverlap : int, optional
        Number of points to overlap. If None, uses nperseg // 2.

    Returns
    -------
    freqs : np.ndarray
        Frequency array.
    psd : np.ndarray
        Power spectral density.
    """
    if nperseg is None:
        nperseg = min(256, len(data) // 8)
    if noverlap is None:
        noverlap = nperseg // 2

    freqs, psd = signal.welch(data, fs=fs, nperseg=nperseg, noverlap=noverlap)
    return freqs, psd


def main(argv: list[str] | None = None) -> int:
    """Main entry point for gwaith_estimate_psd."""
    parser = argparse.ArgumentParser(
        prog="gwaith_estimate_psd",
        description="Estimate PSD from data after subtracting signals.",
    )
    add_data_input_args(
        parser,
        data_help="Path to HDF5 data file (e.g. residual from gwaith_subtract_signals)",
    )
    add_data_output_args(
        parser,
        output_required=False,
        default_dataset="psd",
        output_help="Output HDF5 file for PSD",
    )
    parser.add_argument("--fs", type=float, default=None,
                        help="Sampling frequency in Hz; derived from file delta_t if not given")
    parser.add_argument("--nperseg", type=int, default=None, help="Segment length for Welch")
    parser.add_argument("--noverlap", type=int, default=None, help="Overlap length for Welch")
    add_gwaith_common_options(parser)

    args = parser.parse_args(argv)
    init_logging(args.verbose)

    try:
        logger.info("Loading data from %s [%s]", args.data, args.data_dataset)
        data_ts = load_timeseries(args.data, args.data_dataset)
        logger.info(
            "Loaded %d samples (epoch=%.3f, delta_t=%.6g)",
            len(data_ts.data), data_ts.epoch, data_ts.delta_t,
        )

        fs = args.fs if args.fs is not None else 1.0 / data_ts.delta_t

        logger.info("Estimating PSD with Welch method")
        freqs, psd = estimate_psd(data_ts.data, fs=fs, nperseg=args.nperseg, noverlap=args.noverlap)
        freq_series = FrequencySeries(
            data=psd,
            frequencies=freqs,
            epoch=data_ts.epoch,
            delta_t=data_ts.delta_t,
        )

        if args.output:
            logger.info("Writing PSD to %s [%s]", args.output, args.output_dataset)
            write_frequencyseries(
                freq_series, args.output, args.output_dataset,
                fs=fs,
                nperseg=args.nperseg if args.nperseg else "auto",
                noverlap=args.noverlap if args.noverlap else "auto",
            )
        else:
            output_array = np.column_stack([freqs, psd])
            np.savetxt("-", output_array, fmt="%.6e")

        return 0

    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
