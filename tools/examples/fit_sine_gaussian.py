#!/usr/bin/env python
"""Estimate sine-gaussian parameters from data.

A sine-gaussian is a sinusoidal wave modulated by a Gaussian envelope.
Model: A * exp(-(t - t0)^2 / (2 * sigma^2)) * sin(2*pi*f*t + phi)

This tool fits multiple indexed instances (0, 1, 2, ...) each with separate priors.

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

from .common import (
    get_param_prior,
    load_prior_file,
)

logger = logging.getLogger("gwaith.examples.fit_sine_gaussian")


def _sine_gaussian_model(
    t: np.ndarray,
    central_time: float,
    amplitude: float,
    frequency: float,
    width: float = 3600.0,
    phase: float = 0.0,
) -> np.ndarray:
    """Generate a sine-gaussian signal."""
    gaussian_envelope = amplitude * np.exp(-((t - central_time) ** 2) / (2 * width**2))
    sinusoidal = np.sin(2.0 * np.pi * frequency * t + phase)
    return gaussian_envelope * sinusoidal


def _fit_single_instance(
    residual: np.ndarray,
    t: np.ndarray,
    instance_priors: dict,
) -> dict[str, float] | None:
    """Fit a single fixed-width, zero-phase sine-gaussian instance to the residual.

    Returns None if fitting fails or bounds are invalid.
    Only amplitude, frequency, and central_time are fitted.
    """
    frequency_prior = get_param_prior(instance_priors, "frequency")
    central_time_prior = get_param_prior(instance_priors, "central_time")

    # Validate that required bounds exist
    if not all(k in central_time_prior for k in ["min", "max"]):
        logger.warning("central_time must have min and max bounds")
        return None

    # Use frequency from prior (fixed)
    if "value" in frequency_prior:
        freq_fixed = float(frequency_prior["value"])
    else:
        # If not provided, use the midpoint of min/max
        freq_fixed = (
            float(frequency_prior.get("min", 0.0))
            + float(frequency_prior.get("max", 1.0))
        ) / 2.0

    # Initial guess for central_time
    if "value" in central_time_prior:
        t0_init = float(central_time_prior["value"])
    else:
        t0_min = float(central_time_prior["min"])
        t0_max = float(central_time_prior["max"])
        t0_init = (t0_min + t0_max) / 2.0

    # Use a 2-day window (±1 day) around t0_init
    window_width = 86400  # 1 day in seconds
    t_min = t0_init - window_width / 2
    t_max = t0_init + window_width / 2
    mask = (t >= t_min) & (t <= t_max)
    t_win = t[mask]
    residual_win = residual[mask]
    if len(t_win) < 10:
        logger.warning("Window too small for fitting at t0=%.1f", t0_init)
        return None

    # Objective function: minimize squared error (fit t0 only)
    def objective(params):
        t0 = params[0]
        model = _sine_gaussian_model(
            t_win, t0, 1.0, freq_fixed
        )  # amplitude=1 for LS fit
        # Analytic least squares amplitude fit
        amp_num = np.dot(residual_win, model)
        amp_den = np.dot(model, model)
        amp = amp_num / amp_den if amp_den > 0 else 0.0
        fit = amp * model
        error = np.sum((residual_win - fit) ** 2)
        return error

    # Bounds for t0
    bounds = [
        (float(central_time_prior["min"]), float(central_time_prior["max"])),
    ]
    x0 = [t0_init]

    from scipy.optimize import minimize

    result = minimize(objective, x0, bounds=bounds, method="L-BFGS-B")
    if not result.success:
        logger.warning("Optimization failed: %s", result.message)
        return None
    t0_fit = result.x[0]
    # Final amplitude fit
    model = _sine_gaussian_model(t_win, t0_fit, 1.0, freq_fixed)
    amp_num = np.dot(residual_win, model)
    amp_den = np.dot(model, model)
    amp_fit = amp_num / amp_den if amp_den > 0 else 0.0
    return {
        "central_time": float(t0_fit),
        "width": 3600.0,
        "amplitude": float(amp_fit),
        "frequency": float(freq_fixed),
        "phase": 0.0,
    }


def fit_sine_gaussians(data_ts: TimeSeries, priors: dict) -> list[dict[str, float]]:
    """Fit multiple sine-gaussian instances from priors structure.

    Priors should be structured as:
    {
        0: {amplitude: {...}, frequency: {...}, ...},
        1: {amplitude: {...}, frequency: {...}, ...},
        ...
    }

    Fits sequentially, subtracting each fitted signal from the residual.
    """
    y = np.asarray(data_ts.data, dtype=float)
    t = np.arange(len(y), dtype=float) * data_ts.delta_t
    residual = y.copy()

    components = []

    # Find all numeric keys (instance indices) - handle both int and str keys
    instance_keys = []
    for k in priors:
        if isinstance(k, int):
            instance_keys.append(k)
        elif isinstance(k, str) and k.isdigit():
            instance_keys.append(int(k))

    instance_keys = sorted(instance_keys)

    if not instance_keys:
        logger.warning(
            "No indexed instances found in priors (keys: %s)", list(priors.keys())
        )
        return []

    for instance_idx in instance_keys:
        # Get the actual key (might be int or str key mapping to this idx)
        prior_key = instance_idx
        if prior_key not in priors and str(prior_key) in priors:
            prior_key = str(prior_key)

        instance_priors = priors[prior_key]

        logger.info("Fitting fixed-width sine-gaussian instance %d", instance_idx)
        params = _fit_single_instance(residual, t, instance_priors)

        if params is None:
            logger.warning("Failed to fit instance %d", instance_idx)
            continue

        components.append(params)

        # Subtract fitted signal from residual for next iteration
        fitted_signal = _sine_gaussian_model(
            t, params["central_time"], params["amplitude"], params["frequency"]
        )
        residual = residual - fitted_signal

        logger.info(
            "Instance %d: central_time=%.1f, amplitude=%.6f, frequency=%.2e",
            instance_idx,
            params["central_time"],
            params["amplitude"],
            params["frequency"],
        )

    return components


def _extract_indexed_priors(priors: dict) -> dict[int, dict]:
    """Extract indexed instance priors from a mixed prior dictionary."""
    indexed: dict[int, dict] = {}
    for key, value in priors.items():
        if isinstance(key, int) and isinstance(value, dict):
            indexed[key] = value
        elif isinstance(key, str) and key.isdigit() and isinstance(value, dict):
            indexed[int(key)] = value
    return indexed


def _build_next_round_priors(
    components: list[dict[str, float]],
    source_priors: dict,
) -> dict[int, dict[str, dict[str, float]]]:
    """Build indexed priors for the next round from fitted components.

    If indexed priors already exist, keep their bounds and update values.
    Otherwise create heuristic bounds around fitted values.
    """
    prior_seed = _extract_indexed_priors(source_priors)
    next_priors: dict[int, dict[str, dict[str, float]]] = {}

    for index, component in enumerate(components):
        seed = prior_seed.get(index, {})

        amp = float(component["amplitude"])
        t0 = float(component["central_time"])
        width = float(component["width"])
        freq = float(component["frequency"])

        # Keep previous bounds when present; otherwise infer pragmatic windows.
        amp_seed = get_param_prior(seed, "amplitude")
        t0_seed = get_param_prior(seed, "central_time")
        width_seed = get_param_prior(seed, "width")
        freq_seed = get_param_prior(seed, "frequency")

        next_priors[index] = {
            "amplitude": {
                "min": float(amp_seed.get("min", max(0.0, 0.5 * amp))),
                "max": float(amp_seed.get("max", 1.5 * amp if amp > 0 else 1.0)),
                "value": amp,
            },
            "central_time": {
                "min": float(t0_seed.get("min", t0 - max(3600.0, 10.0 * width))),
                "max": float(t0_seed.get("max", t0 + max(3600.0, 10.0 * width))),
                "value": t0,
            },
            "width": {
                "min": float(width_seed.get("min", max(1.0, 0.5 * width))),
                "max": float(width_seed.get("max", max(2.0 * width, 2.0))),
                "value": width,
            },
            "frequency": {
                "min": float(freq_seed.get("min", max(1e-9, 0.8 * freq))),
                "max": float(freq_seed.get("max", 1.2 * freq if freq > 0 else 1e-6)),
                "value": freq,
            },
        }

    return next_priors


def sine_gaussian_model(
    ts: TimeSeries, components: list[dict[str, float]]
) -> TimeSeries:
    """Generate combined signal from all sine-gaussian components."""
    t = np.arange(len(ts.data)) * ts.delta_t
    model = np.zeros_like(ts.data, dtype=float)
    for comp in components:
        model += _sine_gaussian_model(
            t,
            comp["central_time"],
            comp["amplitude"],
            comp["frequency"],
        )
    return TimeSeries(data=model, epoch=ts.epoch, delta_t=ts.delta_t)


def sine_gaussian_component_model(
    ts: TimeSeries, component: dict[str, float]
) -> TimeSeries:
    """Generate a signal timeseries for a single sine-gaussian component."""
    t = np.arange(len(ts.data)) * ts.delta_t
    model = _sine_gaussian_model(
        t,
        component["central_time"],
        component["amplitude"],
        component["frequency"],
    )
    return TimeSeries(data=model, epoch=ts.epoch, delta_t=ts.delta_t)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_fit_sine_gaussian",
        description=(
            "Fit multiple sine-gaussian components and output signal timeseries "
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
        output_help="Output HDF5 signal file",
    )
    parser.add_argument(
        "--output-components-dir",
        required=False,
        help=(
            "Optional output directory for per-component sine-gaussian files. "
            "One file per fitted component is written with automatic names."
        ),
    )
    parser.add_argument(
        "--output-params",
        required=True,
        help="Output YAML parameters file",
    )
    add_gwaith_common_options(parser)
    args = parser.parse_args(argv)

    init_logging(args.verbose)

    logger.info("Starting")
    try:
        data_ts = load_timeseries(args.data, args.data_dataset)

        logger.info("Loading Priors")
        prior_path = args.priors or args.init_params
        priors = load_prior_file(prior_path) if prior_path else {}

        logger.info("Fitting")
        components = fit_sine_gaussians(data_ts, priors)

        if not components:
            logger.warning("No sine-gaussian components fitted")
            components = []

        logger.debug(
            "Fitted components:\n%s", yaml.dump(components, default_flow_style=False)
        )
        # Generate signal from fitted components
        signal_ts = sine_gaussian_model(data_ts, components)

        write_timeseries(
            signal_ts,
            args.output_signal,
            args.output_dataset,
        )

        if args.output_components_dir:
            components_dir = Path(args.output_components_dir)
            components_dir.mkdir(parents=True, exist_ok=True)
            signal_stem = Path(args.output_signal).stem
            for component_index, component in enumerate(components):
                component_ts = sine_gaussian_component_model(data_ts, component)
                component_path = components_dir / (
                    f"{signal_stem}_component_{component_index:03d}.hdf"
                )
                write_timeseries(
                    component_ts,
                    str(component_path),
                    args.output_dataset,
                )

        # Write parameters to YAML file
        next_round_priors = _build_next_round_priors(components, priors)
        out = {
            "model": "sine_gaussian",
            "sine_gaussians": components,
            "next_round_priors": next_round_priors,
        }
        # Also expose indexed priors at top level so the next round can pass
        # this file directly as --priors without extra conversion.
        for index, prior_spec in next_round_priors.items():
            out[index] = prior_spec
        with open(args.output_params, "w", encoding="utf-8") as f:
            yaml.dump(out, f, default_flow_style=False)

        logger.info(
            "Fitted %d sine-gaussian components",
            len(components),
        )

        return 0

    except Exception as e:
        logger.exception("An error occurred: %s", str(e))
        return 1


if __name__ == "__main__":
    exit(main())
