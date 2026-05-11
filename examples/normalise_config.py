"""Example-specific configuration normalisation helpers."""

from __future__ import annotations

from typing import Any


def normalise_example_generation_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise example-generation config to a standard internal format."""
    sampling = raw.get("sampling", {})
    if not isinstance(sampling, dict):
        raise ValueError("'sampling' must be a mapping")

    delta_t = float(sampling.get("delta_t", 5.0))
    if "duration_seconds" in sampling:
        duration_seconds = float(sampling["duration_seconds"])
    else:
        duration_days = float(sampling.get("duration_days", 30.0))
        duration_seconds = duration_days * 24.0 * 3600.0

    noise_psd = raw.get("noise_psd", {})
    if not isinstance(noise_psd, dict):
        raise ValueError("'noise_psd' must be a mapping")

    sine_waves = raw.get("sine_waves", [])
    if not isinstance(sine_waves, list) or len(sine_waves) != 5:
        raise ValueError(
            "Config must contain exactly five entries in 'sine_waves'."
        )

    normalised_waves: list[dict[str, float]] = []
    for wave in sine_waves:
        if not isinstance(wave, dict):
            raise ValueError("Each sine wave entry must be a mapping")
        normalised_waves.append(
            {
                "amplitude": float(wave["amplitude"]),
                "frequency": float(wave["frequency"]),
                "phase": float(wave.get("phase", 0.0)),
            }
        )

    output = raw.get("output", {})
    if not isinstance(output, dict):
        raise ValueError("'output' must be a mapping")

    # Keep backward compatibility with the old single plot_file option.
    plot_time_file = output.get(
        "plot_time_file",
        output.get("plot_file", "example_data_plot_time.png"),
    )
    plot_frequency_file = output.get(
        "plot_frequency_file",
        "example_data_plot_frequency.png",
    )

    return {
        "seed": int(raw.get("seed", 12345)),
        "epoch": float(raw.get("epoch", 0.0)),
        "sampling": {
            "delta_t": delta_t,
            "duration_seconds": duration_seconds,
        },
        "noise_psd": {
            "amplitude": float(noise_psd.get("amplitude", 5.0e-2)),
            "floor": float(noise_psd.get("floor", 1.0e-4)),
            "f_knee": float(noise_psd.get("f_knee", 2.0e-4)),
            "slope": float(noise_psd.get("slope", -1.8)),
        },
        "signal": {
            "offset": float(raw.get("offset", 0.0)),
            "sine_waves": normalised_waves,
        },
        "output": {
            "directory": str(output.get("directory", "examples/out")),
            "data_file": str(output.get("data_file", "example_data.h5")),
            "truth_file": str(output.get("truth_file", "example_truth.yaml")),
            "plot_time_file": str(plot_time_file),
            "plot_frequency_file": str(plot_frequency_file),
            "data_dataset": str(output.get("data_dataset", "data")),
        },
    }
