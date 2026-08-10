"""Mojito file processing helpers for GWAITH ingestion."""

import logging

import numpy as np
from mojito import MojitoL1File
from MojitoProcessor import process_pipeline

from gwaith.types import TimeSeries

logger = logging.getLogger("gwaith.process.mojito")

_ORBITS_DATASETS = [
    "sc_position_1",
    "sc_position_2",
    "sc_position_3",
    "sc_velocity_1",
    "sc_velocity_2",
    "sc_velocity_3",
]


def _copy_orbits(orbits):
    data = type("OrbitsData", (), {})()
    data.time_sampling = orbits.time_sampling
    for dataset_name in _ORBITS_DATASETS:
        if hasattr(orbits, dataset_name):
            setattr(data, dataset_name, getattr(orbits, dataset_name)[:])
    return data


# From the mojitoprocessor options
FILTER_OPTIONS = ["highpass_cutoff", "lowpass_cutoff", "order"]
DOWNSAMPLE_OPTIONS = ["target_fs", "kaiser_window"]
TRIM_OPTIONS = ["fraction"]
TRUNCATE_OPTIONS = ["days"]
WINDOW_OPTIONS = ["window", "alpha"]

CHUNK_OPTIONS = ["chunk_duration", "chunk_overlap", "tstart", "duration"]


def separate_processor_options(processor_option_dict):
    filter_kwargs = {}
    downsample_kwargs = {}
    trim_kwargs = {}
    truncate_kwargs = {}
    window_kwargs = {}
    chunk_kwargs = {}

    # check that all of the options in the option dict are valid
    for key in processor_option_dict:
        if (
            key
            not in FILTER_OPTIONS
            + DOWNSAMPLE_OPTIONS
            + TRIM_OPTIONS
            + TRUNCATE_OPTIONS
            + WINDOW_OPTIONS
            + CHUNK_OPTIONS
        ):
            raise ValueError(f"Unknown processor option: {key}")

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
    if "target_fs" in filter_kwargs:
        downsample_kwargs["target_fs"] = filter_kwargs["target_fs"]

    # Extract trim parameters
    for key in TRIM_OPTIONS:
        if key in processor_option_dict:
            trim_kwargs[key] = processor_option_dict[key]

    # Do not extract truncation parameters
    # for key in TRUNCATE_OPTIONS:
    #     if key in processor_option_dict:
    #         truncate_kwargs[key] = processor_option_dict[key]

    # Extract window parameters
    if "window" in processor_option_dict:
        window_kwargs["window"] = processor_option_dict["window"]
    if "alpha" in processor_option_dict:
        window_kwargs["alpha"] = float(processor_option_dict["alpha"])

    # Extract chunk parameters
    for key in CHUNK_OPTIONS:
        if key in processor_option_dict:
            chunk_kwargs[key] = float(processor_option_dict[key])

    return {
        "filter_kwargs": filter_kwargs,
        "downsample_kwargs": downsample_kwargs,
        "trim_kwargs": trim_kwargs,
        "truncate_kwargs": truncate_kwargs,
        "window_kwargs": window_kwargs,
        "chunk_kwargs": chunk_kwargs,
    }


def process_mojito(input_path, processor_options):
    """Process a Mojito file using parsed ingest CLI arguments.

    This function handles chunking if specified in the processor options.

    Args:
        input_path (str): Path to the input Mojito file.
        processor_options (dict): Dictionary of processor options.

    Returns:
        dict: Mapping containing 'tdis' and 'orbits' output payloads.
    """
    separated_opts = separate_processor_options(processor_options)
    chunk_opts = separated_opts.pop("chunk_kwargs")

    if not chunk_opts.get("chunk_duration"):
        with MojitoL1File(input_path) as f:
            tstart = f.tdis.time_sampling.t()[0]
            duration = f.tdis.time_sampling.t()[-1] - tstart
        return _process_mojito_slice(input_path, separated_opts, tstart, duration)

    if chunk_opts["chunk_overlap"] >= chunk_opts["chunk_duration"]:
        raise ValueError("Chunk overlap must be smaller than chunk duration.")

    start_time = chunk_opts["tstart"]
    end_time = start_time + chunk_opts["duration"]
    chunk_duration = chunk_opts["chunk_duration"]
    step = chunk_duration - chunk_opts["chunk_overlap"]

    all_tdis = {}
    orbits_data = None

    chunk_start = start_time
    is_first_chunk = True
    while chunk_start < end_time:
        current_chunk_end = min(chunk_start + chunk_duration, end_time)
        current_chunk_duration = current_chunk_end - chunk_start

        if current_chunk_duration <= 0:
            break

        logger.info(
            "Processing chunk: tstart=%f, duration=%f",
            chunk_start,
            current_chunk_duration,
        )

        # NOTE: This implementation does not yet handle trimming of overlapping sections.
        # The data from each chunk is simply concatenated.
        output_data = _process_mojito_slice(
            input_path, separated_opts, chunk_start, current_chunk_duration
        )

        if is_first_chunk:
            orbits_data = output_data.get("orbits")
            for name, ts in output_data["tdis"].items():
                all_tdis[name] = [ts]
            is_first_chunk = False
        else:
            for name, ts in output_data["tdis"].items():
                all_tdis[name].append(ts)

        chunk_start += step

    final_tdis = {}
    if all_tdis:
        for name, ts_list in all_tdis.items():
            # Concatenate data arrays and create a new TimeSeries object
            full_data = np.concatenate([ts.data for ts in ts_list])
            first_ts = ts_list[0]
            final_tdis[name] = TimeSeries(
                data=full_data, epoch=first_ts.epoch, delta_t=first_ts.delta_t
            )

    logger.info(
        "Processed Mojito file %s in chunks, produced %d TDI channels.",
        input_path,
        len(final_tdis),
    )
    return {"tdis": final_tdis, "orbits": orbits_data}


def _process_mojito_slice(input_path, processor_options, tstart, duration):
    """Process a Mojito file using parsed ingest CLI arguments.

    Args:
        parser: Argument parser used to build the ingest command.
        args: Parsed CLI arguments from ingest_data.

    Returns:
        dict: Mapping containing 'tdis' and 'orbits' output payloads.
    """
    logger.info(
        "Processing Mojito file %s",
        input_path,
    )
    with MojitoL1File(input_path) as f:
        tdi_sampling = f.tdis.time_sampling
        epoch = float(tdi_sampling.epoch) if hasattr(tdi_sampling, "epoch") else 0.0
        delta_t = float(tdi_sampling.dt)

        # Calculate indices for TDI data
        tdi_start_idx = int((tstart - epoch) / delta_t) if tstart > epoch else 0
        tdi_num_samples = int(duration / delta_t)
        tdi_end_idx = tdi_start_idx + tdi_num_samples

        ltt_sampling = f.ltts.time_sampling
        ltt_dt = ltt_sampling.dt
        ltt_epoch = float(ltt_sampling.epoch) if hasattr(ltt_sampling, "epoch") else 0.0
        ltt_start_idx = int((tstart - ltt_epoch) / ltt_dt) if tstart > ltt_epoch else 0
        ltt_num_samples = int(duration / ltt_dt)
        ltt_end_idx = ltt_start_idx + ltt_num_samples

        orbit_sampling = f.orbits.time_sampling
        orbit_dt = orbit_sampling.dt
        orbit_epoch = (
            float(orbit_sampling.epoch) if hasattr(orbit_sampling, "epoch") else 0.0
        )
        orbit_start_idx = (
            int((tstart - orbit_epoch) / orbit_dt) if tstart > orbit_epoch else 0
        )
        orbit_num_samples = int(duration / orbit_dt)
        orbit_end_idx = orbit_start_idx + orbit_num_samples

        data = {
            # ── TDI observables ──────────────────────────────────────────────────
            "tdis": {
                "X": f.tdis.x2[tdi_start_idx:tdi_end_idx],
                "Y": f.tdis.y2[tdi_start_idx:tdi_end_idx],
                "Z": f.tdis.z2[tdi_start_idx:tdi_end_idx],
            },
            "fs": tdi_sampling.fs,
            "dt": tdi_sampling.dt,
            "t_tdi": tdi_sampling.t()[tdi_start_idx:tdi_end_idx],
            # ── Light travel times ───────────────────────────────────────────────
            "ltts": {
                "12": f.ltts.ltt_12[ltt_start_idx:ltt_end_idx],
                "13": f.ltts.ltt_13[ltt_start_idx:ltt_end_idx],
                "21": f.ltts.ltt_21[ltt_start_idx:ltt_end_idx],
                "23": f.ltts.ltt_23[ltt_start_idx:ltt_end_idx],
                "31": f.ltts.ltt_31[ltt_start_idx:ltt_end_idx],
                "32": f.ltts.ltt_32[ltt_start_idx:ltt_end_idx],
            },
            "ltt_derivatives": {
                "12": f.ltts.ltt_derivative_12[ltt_start_idx:ltt_end_idx],
                "13": f.ltts.ltt_derivative_13[ltt_start_idx:ltt_end_idx],
                "21": f.ltts.ltt_derivative_21[ltt_start_idx:ltt_end_idx],
                "23": f.ltts.ltt_derivative_23[ltt_start_idx:ltt_end_idx],
                "31": f.ltts.ltt_derivative_31[ltt_start_idx:ltt_end_idx],
                "32": f.ltts.ltt_derivative_32[ltt_start_idx:ltt_end_idx],
            },
            "ltt_times": ltt_sampling.t()[ltt_start_idx:ltt_end_idx],
            # ── Spacecraft orbits ────────────────────────────────────────────────
            "orbits": f.orbits.positions[
                orbit_start_idx:orbit_end_idx
            ],  # (n_orbit, 3, 3)
            "velocities": f.orbits.velocities[
                orbit_start_idx:orbit_end_idx
            ],  # (n_orbit, 3, 3)
            "orbit_times": orbit_sampling.t()[orbit_start_idx:orbit_end_idx],
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

        processed = process_pipeline(data, **processor_options)["segment0"].data
        logger.info("Mojito file processed")
        tdis_results = {}
        for name, array in processed.items():
            tdis_results[name] = TimeSeries(
                data=array[:], epoch=tstart, delta_t=delta_t
            )
        orbits_data = _copy_orbits(f.orbits)
    logger.info(
        "Processed Mojito file %s with %d TDI channels and epoch=%s delta_t=%s",
        input_path,
        len(tdis_results),
        tstart,
        delta_t,
    )
    return {"tdis": tdis_results, "orbits": orbits_data}
