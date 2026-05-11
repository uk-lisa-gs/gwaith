#!/usr/bin/env python
"""Estimate sine-wave parameters (amplitude, frequency, phase) from data.

Standard module interface:
- Input: data file (+ optional priors)
- Output: signal timeseries + parameter file
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import yaml

from gwaith import add_gwaith_common_options, init_logging
from gwaith.io import (
    add_data_input_args,
    add_data_output_args,
    load_timeseries,
    write_timeseries,
)
from gwaith.types import TimeSeries
from gwaith.tools.examples.common import (
    apply_bounds,
    get_param_prior,
    load_prior_file,
)

logger = logging.getLogger("gwaith.examples.fit_sine")


def _initial_frequency(data: np.ndarray, delta_t: float, prior: dict) -> float:
    if "value" in prior:
        return float(prior["value"])

    freqs = np.fft.rfftfreq(len(data), d=delta_t)
    amps = np.abs(np.fft.rfft(data))

    if len(amps) > 0:
        amps[0] = 0.0

    if "min" in prior or "max" in prior:
        mask = np.ones_like(freqs, dtype=bool)
        if "min" in prior:
            mask &= freqs >= float(prior["min"])
        if "max" in prior:
            mask &= freqs <= float(prior["max"])
        if np.any(mask):
            idx_local = int(np.argmax(amps[mask]))
            return float(freqs[mask][idx_local])

    idx = int(np.argmax(amps))
    return float(freqs[idx])


def _fit_component_at_frequency(
    y: np.ndarray, t: np.ndarray, frequency: float
) -> tuple[float, float, np.ndarray]:
    w = 2.0 * np.pi * frequency
    s = np.sin(w * t)
    c = np.cos(w * t)
    design = np.column_stack([s, c])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    a, b = float(coeffs[0]), float(coeffs[1])
    amplitude = float(np.hypot(a, b))
    phase = float(np.arctan2(b, a))
    component = amplitude * np.sin(w * t + phase)
    return amplitude, phase, component


def fit_sine_parameters(
    data_ts: TimeSeries, priors: dict
) -> list[dict[str, float]]:
    """Fit multiple sine components.

    The loop stops when amplitude falls below the prior minimum.
    """
    y = np.asarray(data_ts.data, dtype=float)
    t = np.arange(len(y), dtype=float) * data_ts.delta_t
    residual = y.copy()

    amp_prior = get_param_prior(priors, "amplitude")
    freq_prior = get_param_prior(priors, "frequency")
    phase_prior = get_param_prior(priors, "phase")

    # Default threshold is 0.45 if not explicitly set in priors.
    amp_min = float(amp_prior.get("min", 0.45))
    max_components = int(priors.get("max_components", 5))
    if max_components < 1:
        return []

    freqs = np.fft.rfftfreq(len(y), d=data_ts.delta_t)
    mask = np.ones_like(freqs, dtype=bool)
    mask &= freqs > 0.0
    if "min" in freq_prior:
        mask &= freqs >= float(freq_prior["min"])
    if "max" in freq_prior:
        mask &= freqs <= float(freq_prior["max"])

    if not np.any(mask):
        return []

    valid_freqs = freqs[mask]
    components: list[dict[str, float]] = []
    max_components = min(max_components, len(valid_freqs))

    # Require selected frequencies to be separated by at least this amount.
    # Default is one FFT-bin spacing if not explicitly configured.
    freq_bin = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 0.0
    min_sep = float(priors.get("min_frequency_separation", freq_bin))
    min_sep = max(0.0, min_sep)
    selected_freqs: list[float] = []

    for _ in range(max_components):
        spectrum = np.abs(np.fft.rfft(residual))
        spectrum[0] = 0.0

        candidate_indices = np.argsort(spectrum[mask])[::-1]
        f0: float | None = None
        for idx_local in candidate_indices:
            f_try = float(valid_freqs[int(idx_local)])
            if all(
                abs(f_try - f_prev) >= min_sep for f_prev in selected_freqs
            ):
                f0 = f_try
                break

        if f0 is None:
            break

        f0 = apply_bounds(f0, freq_prior)

        amplitude, phase, component = _fit_component_at_frequency(
            residual, t, f0
        )
        if "value" in amp_prior:
            amplitude = float(amp_prior["value"])
        amplitude = apply_bounds(amplitude, amp_prior)

        if amplitude < amp_min:
            break

        if "value" in phase_prior:
            phase = float(phase_prior["value"])
        phase = apply_bounds(phase, phase_prior)

        components.append(
            {
                "amplitude": float(amplitude),
                "frequency": float(f0),
                "phase": float(phase),
            }
        )
        selected_freqs.append(float(f0))
        residual = residual - component

    components.sort(key=lambda x: x["frequency"])

    return components


def sine_model(
    ts: TimeSeries, components: list[dict[str, float]]
) -> TimeSeries:
    t = np.arange(len(ts.data)) * ts.delta_t
    model = np.zeros_like(ts.data, dtype=float)
    for comp in components:
        model += comp["amplitude"] * np.sin(
            2.0 * np.pi * comp["frequency"] * t + comp["phase"]
        )
    return TimeSeries(data=model, epoch=ts.epoch, delta_t=ts.delta_t)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_fit_sine",
        description=(
            "Fit amplitude/frequency/phase and output signal timeseries "
            "+ parameters."
        ),
    )
    add_data_input_args(parser, data_help="Input HDF5 data file")
    parser.add_argument(
        "--priors",
        required=False,
        help="Optional prior file (.yaml/.yml or .ini)",
    )
    parser.add_argument(
        "--init-params",
        required=False,
        help=argparse.SUPPRESS,
    )
    add_data_output_args(
        parser,
        output_option="--output-signal",
        dataset_option="--output-signal-dataset",
        default_dataset="signal",
        output_help="Output HDF5 signal file",
    )
    parser.add_argument(
        "--output-params",
        required=True,
        help="Output YAML parameters file",
    )
    add_gwaith_common_options(parser)
    args = parser.parse_args(argv)

    init_logging(args.verbose)

    try:
        data_ts = load_timeseries(args.data, args.data_dataset)

        prior_path = args.priors or args.init_params
        priors = load_prior_file(prior_path) if prior_path else {}
        components = fit_sine_parameters(data_ts, priors)

        signal_ts = sine_model(data_ts, components)
        write_timeseries(
            signal_ts,
            args.output_signal,
            args.output_signal_dataset,
        )

        out = {
            "model": "sine",
            "sine_waves": components,
        }
        Path(args.output_params).write_text(
            yaml.safe_dump(out, sort_keys=False), encoding="utf-8"
        )

        logger.info(
            "Wrote signal to %s and parameters to %s",
            args.output_signal,
            args.output_params,
        )
        return 0
    except Exception as exc:
        logger.error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
