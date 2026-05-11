#!/usr/bin/env python
"""Generate synthetic example data for GWAITH demonstration

The generated data is:
- colored Gaussian noise from a non-white PSD
- plus a constant offset
- plus sine wave components

All signal parameters, cadence, and duration come from a YAML config file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from normalise_config import normalise_example_generation_config  # noqa: E402

from gwaith.config import load_config  # noqa: E402
from gwaith.io import write_timeseries  # noqa: E402
from gwaith.types import TimeSeries  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def get_sampling(sampling: dict) -> tuple[float, float, int]:
    delta_t = float(sampling.get("delta_t", 5.0))
    duration_seconds = float(sampling["duration_seconds"])

    n_samples = int(round(duration_seconds / delta_t))
    if n_samples <= 1:
        raise ValueError("Sampling configuration produced too few samples.")

    return delta_t, duration_seconds, n_samples


def build_nonwhite_psd(freqs: np.ndarray, noise_cfg: dict) -> np.ndarray:
    """Build a simple non-white PSD model.

    Model:
        PSD(f) = floor + amplitude * (max(f, f_knee) / f_knee) ** slope
    """
    amplitude = float(noise_cfg.get("amplitude", 5.0e-2))
    floor = float(noise_cfg.get("floor", 1.0e-4))
    f_knee = float(noise_cfg.get("f_knee", 2.0e-4))
    slope = float(noise_cfg.get("slope", -1.8))

    if f_knee <= 0:
        raise ValueError("noise_psd.f_knee must be positive.")

    f_safe = np.maximum(freqs, f_knee)
    psd = floor + amplitude * (f_safe / f_knee) ** slope

    if np.any(psd <= 0):
        raise ValueError("PSD model produced non-positive values.")

    return psd


def generate_colored_noise(
    psd: np.ndarray, delta_t: float, n_samples: int, rng: np.random.Generator
) -> np.ndarray:
    """Generate approximate colored Gaussian noise.

    The target spectrum is one-sided.
    """
    white = rng.normal(0.0, 1.0, size=n_samples)
    white_fft = np.fft.rfft(white)

    # Approximate one-sided PSD of unit-variance white noise.
    psd_white = np.full_like(psd, 2.0 * delta_t, dtype=float)
    psd_white[0] = delta_t
    if n_samples % 2 == 0:
        psd_white[-1] = delta_t

    shaped_fft = white_fft * np.sqrt(psd / psd_white)
    return np.fft.irfft(shaped_fft, n=n_samples)


def generate_signal(
    t: np.ndarray, signal_cfg: dict
) -> tuple[np.ndarray, dict, list[dict]]:
    offset = float(signal_cfg["offset"])
    sine_waves = signal_cfg["sine_waves"]

    if not isinstance(sine_waves, list) or len(sine_waves) != 5:
        raise ValueError(
            "Config must contain exactly five entries in 'sine_waves'."
        )

    frequencies = [float(w["frequency"]) for w in sine_waves]
    if len(set(frequencies)) != len(frequencies):
        raise ValueError("All sine_waves frequencies must be distinct.")

    signal = np.full_like(t, offset, dtype=float)
    components: list[dict] = []

    for i, wave in enumerate(sine_waves):
        amp = float(wave["amplitude"])
        freq = float(wave["frequency"])
        phase = float(wave.get("phase", 0.0))
        component = amp * np.sin(2.0 * np.pi * freq * t + phase)
        signal += component
        components.append(
            {
                "amplitude": amp,
                "frequency": freq,
                "phase": phase,
                "series": component,
            }
        )

    components.sort(key=lambda x: x["frequency"])

    truth_components = [
        {
            "amplitude": float(comp["amplitude"]),
            "frequency": float(comp["frequency"]),
            "phase": float(comp["phase"]),
        }
        for comp in components
    ]

    return (
        signal,
        {
            "offset": {
                "model": "offset",
                "value": offset,
            },
            "sine_waves": truth_components,
        },
        components,
    )


def plot_example_data_time(
    t: np.ndarray,
    data: np.ndarray,
    signal: np.ndarray,
    noise: np.ndarray,
    components: list[dict],
    offset_value: float,
    output_path: Path,
    max_points: int = 20000,
) -> None:
    """Save a compact diagnostic plot of generated time-domain data."""
    n = len(t)
    step = max(1, n // max_points)

    t_plot_days = t[::step] / 86400.0
    data_plot = data[::step]
    noise_plot = noise[::step]

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(t_plot_days, data_plot, lw=0.8)
    axes[0].set_ylabel("data")
    axes[0].set_title("Generated Example Data")
    axes[0].grid(alpha=0.25)

    cmap = plt.get_cmap("tab10")
    for i, comp in enumerate(components):
        comp_plot = comp["series"][::step]
        color = cmap(i % 10)
        axes[1].plot(
            t_plot_days,
            comp_plot,
            lw=1.0,
            color=color,
            label=f"sine {i + 1} (f={comp['frequency']:.1e} Hz)",
        )
    axes[1].plot(
        t_plot_days,
        np.full_like(t_plot_days, offset_value),
        lw=1.2,
        color="0.35",
        ls="--",
        label="offset",
    )
    axes[1].set_ylabel("signal")
    axes[1].legend(loc="upper right", fontsize=8, ncol=2)
    axes[1].grid(alpha=0.25)

    axes[2].plot(t_plot_days, noise_plot, lw=0.8)
    axes[2].set_ylabel("noise")
    axes[2].set_xlabel("time [days]")
    axes[2].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _magnitude_spectrum(
    x: np.ndarray, delta_t: float
) -> tuple[np.ndarray, np.ndarray]:
    freqs = np.fft.rfftfreq(len(x), d=delta_t)
    mags = np.abs(np.fft.rfft(x)) / len(x)
    return freqs, mags


def plot_example_data_frequency(
    data: np.ndarray,
    noise: np.ndarray,
    components: list[dict],
    delta_t: float,
    output_path: Path,
) -> None:
    """Save a frequency-domain diagnostic plot.

    The plot shows individual sine components.
    """
    freqs, data_mag = _magnitude_spectrum(data, delta_t)
    _, noise_mag = _magnitude_spectrum(noise, delta_t)

    mask = freqs > 0.0
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axes[0].loglog(freqs[mask], data_mag[mask], lw=1.0, label="data")
    axes[0].loglog(freqs[mask], noise_mag[mask], lw=1.0, label="noise")
    axes[0].set_ylabel("|FFT|")
    axes[0].set_title("Generated Example Data (Frequency Domain)")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(alpha=0.25, which="both")

    cmap = plt.get_cmap("tab10")
    for i, comp in enumerate(components):
        _, comp_mag = _magnitude_spectrum(comp["series"], delta_t)
        color = cmap(i % 10)
        axes[1].loglog(
            freqs[mask],
            comp_mag[mask],
            lw=1.2,
            color=color,
            label=f"sine {i + 1} (f={comp['frequency']:.2e} Hz)",
        )

    axes[1].set_xlabel("frequency [Hz]")
    axes[1].set_ylabel("|FFT|")
    axes[1].set_title("Signal Components")
    axes[1].legend(loc="upper right", fontsize=8, ncol=2)
    axes[1].grid(alpha=0.25, which="both")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_example_data",
        description=(
            "Generate example data (colored noise + offset + five sines) "
            "for GWAITH."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(
            REPO_ROOT / "examples" / "example_generation_config.yaml"
        ),
        help="Path to YAML config file",
    )
    args = parser.parse_args(argv)

    cfg_path = Path(args.config)
    cfg = normalise_example_generation_config(load_config(cfg_path))

    seed = int(cfg["seed"])
    epoch = float(cfg["epoch"])

    delta_t, duration_seconds, n_samples = get_sampling(cfg["sampling"])
    t = np.arange(n_samples, dtype=float) * delta_t

    freqs = np.fft.rfftfreq(n_samples, d=delta_t)
    psd_cfg = cfg["noise_psd"]
    psd = build_nonwhite_psd(freqs, psd_cfg)

    rng = np.random.default_rng(seed)
    noise = generate_colored_noise(psd, delta_t, n_samples, rng)

    signal, signal_params, signal_components = generate_signal(
        t, cfg["signal"]
    )
    data = noise + signal

    output_cfg = cfg["output"]
    out_dir = REPO_ROOT / output_cfg["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)

    data_file = out_dir / output_cfg["data_file"]
    truth_file = out_dir / output_cfg["truth_file"]
    plot_time_file = out_dir / output_cfg["plot_time_file"]
    plot_frequency_file = out_dir / output_cfg["plot_frequency_file"]

    data_dataset = output_cfg["data_dataset"]

    write_timeseries(
        ts=TimeSeries(data=data, epoch=epoch, delta_t=delta_t),
        filepath=str(data_file),
        dataset_name=data_dataset,
    )

    plot_example_data_time(
        t=t,
        data=data,
        signal=signal,
        noise=noise,
        components=signal_components,
        offset_value=float(signal_params["offset"]["value"]),
        output_path=plot_time_file,
    )
    plot_example_data_frequency(
        data=data,
        noise=noise,
        components=signal_components,
        delta_t=delta_t,
        output_path=plot_frequency_file,
    )

    truth = {
        "seed": seed,
        "epoch": epoch,
        "sampling": {
            "delta_t": delta_t,
            "duration_seconds": duration_seconds,
            "n_samples": n_samples,
        },
        "noise_psd": {
            "model": "floor_plus_power_law",
            **psd_cfg,
        },
        "signal": signal_params,
        "files": {
            "data": str(data_file),
            "data_dataset": data_dataset,
            "plot": str(plot_time_file),
            "plot_time": str(plot_time_file),
            "plot_frequency": str(plot_frequency_file),
        },
    }

    with truth_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(truth, f, sort_keys=False)

    print(f"Wrote data:  {data_file}")
    print(f"Wrote truth: {truth_file}")
    print(f"Wrote plot (time):      {plot_time_file}")
    print(f"Wrote plot (frequency): {plot_frequency_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
