"""Mojito file processing helpers for GWAITH ingestion."""
import logging
from pathlib import Path

from mojito import MojitoL1File
from MojitoProcessor import process_pipeline

from gwaith.types import TimeSeries
logger = logging.getLogger('gwaith.process.mojito')

_ORBITS_DATASETS = [
    'sc_position_1',
    'sc_position_2',
    'sc_position_3',
    'sc_velocity_1',
    'sc_velocity_2',
    'sc_velocity_3',
]


def _copy_orbits(orbits):
    data = type('OrbitsData', (), {})()
    data.time_sampling = orbits.time_sampling
    for dataset_name in _ORBITS_DATASETS:
        if hasattr(orbits, dataset_name):
            setattr(data, dataset_name, getattr(orbits, dataset_name)[:])
    return data

# From the mojitoprocessor options
FILTER_OPTIONS = ['highpass_cutoff', 'lowpass_cutoff', 'order']
DOWNSAMPLE_OPTIONS = ['target_fs', 'kaiser_window']
TRIM_OPTIONS = ['fraction']
TRUNCATE_OPTIONS = ['days']
WINDOW_OPTIONS = ['window', 'alpha']


def separate_processor_options(processor_option_dict):
    filter_kwargs = {}
    downsample_kwargs = {}
    trim_kwargs = {}
    truncate_kwargs = {}
    window_kwargs = {}

    # check that all of the options in the option dict are valid
    for key in processor_option_dict:
        if key not in FILTER_OPTIONS + DOWNSAMPLE_OPTIONS + TRIM_OPTIONS + TRUNCATE_OPTIONS + WINDOW_OPTIONS:
            raise ValueError(f'Unknown processor option: {key}')

    # Extract filter parameters
    for key in FILTER_OPTIONS:
        if key in processor_option_dict:
            filter_kwargs[key] = float(processor_option_dict[key])

    # Extract downsample parameters
    for key in DOWNSAMPLE_OPTIONS:
        if key in processor_option_dict:
            downsample_kwargs[key] = float(processor_option_dict[key])
    # SPECIAL CASE: downsample_kwargs will _also_ take the target_fs
    # which is the same as filter_kwargs
    if 'target_fs' in filter_kwargs:
        downsample_kwargs['target_fs'] = filter_kwargs['target_fs']

    # Extract trim parameters
    for key in TRIM_OPTIONS:
        if key in processor_option_dict:
            trim_kwargs[key] = processor_option_dict[key]

    # Do not extract truncation parameters
    # for key in TRUNCATE_OPTIONS:
    #     if key in processor_option_dict:
    #         truncate_kwargs[key] = processor_option_dict[key]

    # Extract window parameters
    for key in WINDOW_OPTIONS:
        if 'window' in processor_option_dict:
            window_kwargs['window'] = processor_option_dict['window']
        if 'alpha' in processor_option_dict:
            window_kwargs['alpha'] = float(processor_option_dict['alpha'])

    return {
        'filter_kwargs': filter_kwargs,
        'downsample_kwargs': downsample_kwargs,
        'trim_kwargs': trim_kwargs,
        'truncate_kwargs': truncate_kwargs,
        'window_kwargs': window_kwargs,
    }

def process_mojito(
    input_path,
    processor_options
):
    """Process a Mojito file using parsed ingest CLI arguments.

    Args:
        parser: Argument parser used to build the ingest command.
        args: Parsed CLI arguments from ingest_data.

    Returns:
        dict: Mapping containing 'tdis' and 'orbits' output payloads.
    """
    logger.info(
        'Processing Mojito file %s',
        input_path,
    )
    processor_options = separate_processor_options(processor_options)
    with MojitoL1File(input_path) as f:
        tdi_sampling = f.tdis.time_sampling
        epoch = float(tdi_sampling.epoch) if hasattr(tdi_sampling, 'epoch') else 0.0
        delta_t = float(tdi_sampling.dt)
    
        tdi_sampling = f.tdis.time_sampling
        ltt_sampling = f.ltts.time_sampling
        orbit_sampling = f.orbits.time_sampling

        data = {
            # ── TDI observables ──────────────────────────────────────────────────
            "tdis": {
                "X": f.tdis.x2[:],
                "Y": f.tdis.y2[:],
                "Z": f.tdis.z2[:],
            },
            "fs": tdi_sampling.fs,
            "dt": tdi_sampling.dt,
            "t_tdi": tdi_sampling.t()[:],
            # ── Light travel times ───────────────────────────────────────────────
            "ltts": {
                "12": f.ltts.ltt_12[:],
                "13": f.ltts.ltt_13[:],
                "21": f.ltts.ltt_21[:],
                "23": f.ltts.ltt_23[:],
                "31": f.ltts.ltt_31[:],
                "32": f.ltts.ltt_32[:],
            },
            "ltt_derivatives": {
                "12": f.ltts.ltt_derivative_12[:],
                "13": f.ltts.ltt_derivative_13[:],
                "21": f.ltts.ltt_derivative_21[:],
                "23": f.ltts.ltt_derivative_23[:],
                "31": f.ltts.ltt_derivative_31[:],
                "32": f.ltts.ltt_derivative_32[:],
            },
            "ltt_times": ltt_sampling.t()[:],
            # ── Spacecraft orbits ────────────────────────────────────────────────
            "orbits": f.orbits.positions[:],  # (n_orbit, 3, 3)
            "velocities": f.orbits.velocities[:],  # (n_orbit, 3, 3)
            "orbit_times": orbit_sampling.t()[:],
            # ── Noise estimates (frequency-domain, not truncated) ────────────────
            "noise_estimates": {
                "xyz": f.noise_estimates.xyz[:],
                "aet": f.noise_estimates.aet[:],
                "freqs": f.noise_estimates.freq_sampling.f(),
            },
            # ── Metadata ─────────────────────────────────────────────────────────
            "metadata": {
                "laser_frequency": f.laser_frequency,
                "pipeline_name": f.pipeline_names,
            },
        }
        logger.info("Mojito file read")

        processed = process_pipeline(
            data,
            **processor_options
        )['segment0'].data
        logger.info("Mojito file processed")
        tdis_results = {}
        for name, array in processed.items():
            tdis_results[name] = TimeSeries(data=array[:], epoch=epoch, delta_t=delta_t)
        orbits_data = _copy_orbits(f.orbits)
    logger.info(
        'Processed Mojito file %s with %d TDI channels and epoch=%s delta_t=%s',
        input_path,
        len(tdis_results),
        epoch,
        delta_t,
    )
    return {'tdis': tdis_results, 'orbits': orbits_data}
