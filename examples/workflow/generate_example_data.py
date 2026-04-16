"""Generate synthetic example data for GWAITH demonstration

The generated data is:
- colored Gaussian noise from a non-white PSD
- plus a constant offset
- plus sine wave components

All signal parameters, cadence, and duration come from a YAML config file.
"""
import argparse
import logging
from pathlib import Path
import matplotlib
import os
import copy
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from gwaith.io import write_timeseries  # noqa: E402
from gwaith.types import TimeSeries  # noqa: E402
from gwaith import add_gwaith_common_options, init_logging  # noqa: E402

import os 
dir_path = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger('gwaith.examples.generate_data')


def build_psd(freqs, noise_cfg):
    """Build a simple non-white PSD model.

    Model:
        PSD(f) = floor + amplitude * (max(f, f_knee) / f_knee) ** slope
    """
    amplitude = float(noise_cfg.get('amplitude', 0.05))
    floor = float(noise_cfg.get('floor', 0.0001))
    f_knee = float(noise_cfg.get('f_knee', 0.0002))
    slope = float(noise_cfg.get('slope', -1.8))
    if f_knee <= 0:
        raise ValueError('noise_psd.f_knee must be positive.')
    f_safe = np.maximum(freqs, f_knee)
    psd = floor + amplitude * (f_safe / f_knee) ** slope
    if np.any(psd <= 0):
        raise ValueError('PSD model produced non-positive values.')
    return psd


def generate_noise(
    psd: np.ndarray, delta_t: float, n_samples: int, rng: np.random.Generator
) -> np.ndarray:
    """Generate approximate colored Gaussian noise.

    The target spectrum is one-sided.
    """
    white = rng.normal(0.0, 1.0, size=n_samples)
    white_fft = np.fft.rfft(white)
    psd_white = np.full_like(psd, 2.0 * delta_t, dtype=float)
    psd_white[0] = delta_t
    if n_samples % 2 == 0:
        psd_white[-1] = delta_t
    shaped_fft = white_fft * np.sqrt(psd / psd_white)
    return np.fft.irfft(shaped_fft, n=n_samples)


def plot_example_data_time(
    t: np.ndarray,
    data: np.ndarray,
    noise: np.ndarray,
    components: dict[int, dict],
    output_path: Path,
) -> None:
    """Save a compact diagnostic plot of generated time-domain data."""
    t_days = t / (24.0 * 3600.0)
    fig, axes = plt.subplots(3, 1, figsize=(8, 12), sharex=True)
    axes[0].plot(t_days, data, lw=0.8, c='k')
    axes[0].set_ylabel('Data')
    axes[0].set_title('Generated Example Data')
    axes[0].grid(alpha=0.25)
    cmap = plt.get_cmap('tab10')
    for i, (idx, comp) in enumerate(components.items()):
        color = cmap(i % 10)
        axes[1].plot(
            t_days,
            comp.data,
            color=color,
            label=idx,
        )

    axes[1].set_ylabel("Signal Components")
    axes[1].legend(loc="upper left", fontsize=8, ncol=2)
    axes[2].plot(t_days, noise, lw=0.8)
    axes[2].set_ylabel('Noise')
    axes[2].set_xlabel('Time [days]')
    for ax in axes:
        ax.grid(alpha=0.25, which='both')
    fig.savefig(output_path, dpi=150)


def _magnitude_spectrum(
    x: np.ndarray,
    delta_t: float
) -> tuple[np.ndarray, np.ndarray]:
    freqs = np.fft.rfftfreq(len(x), d=delta_t)
    mags = np.abs(np.fft.rfft(x)) / len(x)
    return (freqs, mags)


def plot_example_data_frequency(
    data: np.ndarray,
    noise: np.ndarray,
    components: dict[int, dict],
    psd_model: np.ndarray,
    delta_t: float,
    output_path: Path,
) -> None:
    """Save a frequency-domain diagnostic plot.

    The plot shows individual sine components.
    """
    freqs, data_mag = _magnitude_spectrum(data, delta_t)
    _, noise_mag = _magnitude_spectrum(noise, delta_t)
    delta_f = freqs[1] - freqs[0] if len(freqs) > 1 else 0.0
    psd_mag = np.sqrt(psd_model * delta_f / 2.0)
    mask = freqs > 0.0
    fig, axes = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

    axes[0].loglog(freqs[mask], data_mag[mask], lw=1.0, label='Data')
    axes[0].loglog(freqs[mask], noise_mag[mask], lw=1.0, label='Noise')
    axes[0].set_ylabel('|FFT|')
    axes[0].set_title('Generated Example Data')

    axes[0].loglog(
        freqs[mask],
        psd_mag[mask],
        lw=1.2,
        color='k',
        label='PSD model',
    )

    cmap = plt.get_cmap('tab10')
    for i, (idx, comp) in enumerate(components.items()):
        _, comp_mag = _magnitude_spectrum(comp.data, delta_t)
        color = cmap(i % 10)
        axes[1].loglog(
            freqs[mask],
            comp_mag[mask],
            color=color,
            label=idx,
        )
    axes[1].set_xlabel('Frequency [Hz]')
    axes[1].set_xlim(1e-6, 1e-1)
    axes[1].set_ylabel('|FFT|')
    axes[1].set_title('Signal Components')

    for ax in axes:
        ax.grid(alpha=0.25, which='both')
        ax.legend(loc='upper left')
    fig.savefig(output_path, dpi=150)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_generate_example_data",
        description=(
            "Generate example data (colored noise + offset + five sines) "
            "for GWAITH."
        ),
    )
    add_gwaith_common_options(parser)
    parser.add_argument(
        "--delta-t",
        type=float,
        default=5.0,
        help="Sample spacing in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        help="Duration in seconds (overrides duration-days)"
    )
    parser.add_argument(
        "--duration-days",
        type=float,
        default=30.0,
        help="Duration in days (default: 30.0, used if duration-seconds not set)"
    )
    parser.add_argument(
        "--epoch",
        type=float,
        default=0.0,
        help="GPS epoch time in seconds (default: 0.0)"
    )
    parser.add_argument(
        "--noise-psd",
        nargs="+",
        default=["amplitude:0.05"],
        help="Details for the noise PSD model, in key:value pairs. "
        "This should contain amplitude, floor, f_knee and slope keys"
    )
    parser.add_argument(
        "--sine-waves",
        nargs="+",
        help="Details for the sine waves, in the form "
        "amplitude:frequency:phase."
    )
    parser.add_argument(
        "--sine-gaussians",
        nargs="+",
        help="Details for the sine-gaussian components, in the form "
        "time:width:amplitude:frequency:phase."
    )
    parser.add_argument(
        "--offset",
        type=float,
        help="Value by which the data is offset from zero."
    )
    parser.add_argument(
        "--seed",
        default=42,
        type=int,
        help="Seed for random number generator."
    )
    parser.add_argument(
        "--output-directory",
        default=dir_path,
        help="Directory to output files and plots, defaults to 'example_data' in examples."
    )
    parser.add_argument(
        "--generate-plots",
        action="store_true",
        help="Flag to generate time-domain and frequency-domain plots of the data."
    )
    args = parser.parse_args(argv)
    init_logging(args.verbose)

    sine_wave_config = {}
    if args.sine_waves:
        logger.debug("Loading sine wave config")
        for i, wave_str in enumerate(args.sine_waves):
            parts = wave_str.split(':')
            if len(parts) != 3:
                parser.error(
                    f"Sine wave {i}: expected 'amplitude:frequency:phase' "
                    f"but got '{wave_str}'"
                )
            try:
                amplitude = float(parts[0])
                frequency = float(parts[1])
                phase = float(parts[2])
            except ValueError as e:
                parser.error(
                    f"Sine wave {i}: could not parse 'amplitude:frequency:phase' "
                    f"from '{wave_str}': {e}"
                )
            sine_wave_config[i] = {
                "amplitude": amplitude,
                "frequency": frequency,
                "phase": phase,
            }
            
    sine_gaussian_config = {}
    if args.sine_gaussians:
        logger.debug("Loading sine gaussian config")
        for i, wave_str in enumerate(args.sine_gaussians):
            parts = wave_str.split(':')
            if len(parts) != 3:
                parser.error(
                    f"Sine gaussian {i}: expected 'time:amplitude:frequency' "
                    f"but got '{wave_str}'"
                )
            try:
                central_time = float(parts[0])
                amplitude = float(parts[1])
                frequency = float(parts[2])
                # Hardcoded width and phase
                width = 3600.0
                phase = 0.0
            except ValueError as e:
                parser.error(
                    f"Sine-gaussian {i}: could not parse 'time:amplitude:frequency' "
                    f"from '{wave_str}': {e}"
                )
            sine_gaussian_config[i] = {
                "central_time": central_time,
                "width": width,
                "amplitude": amplitude,
                "frequency": frequency,
                "phase": phase,
            }

    noise_config = {}
    if args.noise_psd:
        logger.debug("Loading noise config")
        for pair_str in args.noise_psd:
            parts = pair_str.split(':')
            if len(parts) != 2:
                parser.error(
                    f"Noise PSD parameter: expected 'key:value' "
                    f"but got '{pair_str}'"
                )
            key = parts[0].strip()
            value_str = parts[1].strip()
            try:
                # Try to parse as float first
                value = float(value_str)
            except ValueError:
                parser.error(
                    f"Noise PSD parameter '{key}': could not parse value "
                    f"'{value_str}' as a number"
                )
            noise_config[key] = value

    logger.debug("Creating time array")
    if args.duration_seconds is not None:
        duration_seconds = float(args.duration_seconds)
    else:
        duration_seconds = float(args.duration_days) * 24.0 * 3600.0
    n_samples = int(round(duration_seconds / args.delta_t))
    
    if n_samples <= 1:
        parser.error('Sampling configuration produced too few samples.')
    
    t = np.arange(n_samples, dtype=float) * args.delta_t
    offset = args.offset if args.offset is not None else 0.0
    
    logger.debug("Generating frequency array")
    freqs = np.fft.rfftfreq(n_samples, d=args.delta_t)
    logger.debug("Building PSD")
    psd = build_psd(freqs, noise_config)
    
    logger.debug("Generating noise")
    rng = np.random.default_rng(args.seed)
    noise_data = generate_noise(psd, args.delta_t, n_samples, rng)
    
    # Convert to TimeSeries
    noise_ts = TimeSeries(
        data=noise_data,
        epoch=args.epoch,
        delta_t=args.delta_t
    )
    
    # Generate sine wave components and create TimeSeries objects
    component_ts_dict = {}
    for idx, params in sine_wave_config.items():
        amp = params["amplitude"]
        freq = params["frequency"]
        phase = params["phase"]
        component_data = amp * np.sin(
            2.0 * np.pi * freq * t + phase
            )
        component_ts_dict[f"sine_{idx}"] = TimeSeries(
            data=component_data,
            epoch=args.epoch,
            delta_t=args.delta_t
        )

    for idx, params in sine_gaussian_config.items():
        amp = params["amplitude"]
        t0 = params["central_time"]
        width = params["width"]
        frequency = params["frequency"]
        phase = params["phase"]

        gaussian_envelope =  amp * np.exp(
            -(t - t0) ** 2 / (2 * width ** 2)
        )
        sinusoidal_component = np.sin(
            2.0 * np.pi * frequency * t + phase
        )

        component_data = gaussian_envelope * sinusoidal_component

        component_ts_dict[f"sine_gaussian_{idx}"] = TimeSeries(
            data=component_data,
            epoch=args.epoch,
            delta_t=args.delta_t
        )

    component_ts_dict["offset"] = TimeSeries(
        data=np.ones_like(t) * offset,
        epoch=args.epoch,
        delta_t=args.delta_t
    )

    data = copy.deepcopy(noise_ts)
    for component_key, component_timeseries in component_ts_dict.items():
        data += component_timeseries
        logger.info("Adding %s to data", component_key)
    
    logger.info("Writing data to %s", args.output_directory)

    out_dir = Path(args.output_directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    write_timeseries(
        data,
        out_dir / "example_data.hdf"
    )

    if args.generate_plots:
        logger.info("Plotting data to %s", out_dir)
        td_plot_outfile = out_dir / "example_data_time.png"
        logger.debug("Plotting Time domain data to %s", td_plot_outfile)
        plot_example_data_time(
            t=t,
            data=data.data,
            noise=noise_ts.data,
            components=component_ts_dict,
            output_path=td_plot_outfile
        )
        fd_plot_outfile = out_dir / "example_data_frequency.png"
        logger.debug("Plotting Frequency domain data to %s", fd_plot_outfile)
        plot_example_data_frequency(
            data=data.data,
            noise=noise_ts.data,
            components=component_ts_dict,
            psd_model=psd,
            delta_t=args.delta_t,
            output_path=fd_plot_outfile
        )

    truth_file = out_dir / "truth.yaml"
    logger.info("Writing truth file to %s", str(truth_file))
    truth = {
        'seed': args.seed, 
        'epoch': args.epoch,
        'sampling': {
            'delta_t': args.delta_t,
            'duration_seconds': duration_seconds,
            'n_samples': n_samples
        },
        'noise_psd': noise_config,
        'sine_waves': sine_wave_config,
        'offset': offset,
    }
    with truth_file.open('w', encoding='utf-8') as f:
        yaml.safe_dump(truth, f, sort_keys=False)

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
