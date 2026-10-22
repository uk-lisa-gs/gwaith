"""Mojito L1 output helpers for GWAITH.

This module provides support for writing incomplete Mojito L1 files using the
mojito writer API. It exposes separate helpers for TDI and orbit-only output.
"""

import logging
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def silence_logger(name, level=logging.ERROR):
    logger = logging.getLogger(name)
    old_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(old_level)


_CHANNEL_ATTR_MAP = {
    "A": "a2",
    "E": "e2",
    "T": "t2",
    "X": "x2",
    "Y": "y2",
    "Z": "z2",
}

_ORBITS_DATASET_NAMES = [
    "sc_position_1",
    "sc_position_2",
    "sc_position_3",
    "sc_velocity_1",
    "sc_velocity_2",
    "sc_velocity_3",
]


def _series_to_array(series):
    return series.data if hasattr(series, "data") else series


class _MojitoTDIData:
    def __init__(self, channels):
        for label, attr_name in _CHANNEL_ATTR_MAP.items():
            value = channels.get(label) or channels.get(attr_name)
            if value is not None:
                setattr(self, attr_name, _series_to_array(value))


def write_mojito_tdis(ts_map, filepath):
    """Write a TDI-only Mojito L1 file.

    Parameters
    ----------
    ts_map:
        Mapping from channel names (X,Y,Z) to TimeSeries objects.
    filepath:
        Output HDF5 file path.
    """
    # Load the optional backend only when writing Mojito data.
    from mojito import writer
    from mojito.sampling import UniformTimeSampling

    if not isinstance(ts_map, dict):
        raise TypeError("TDI output requires a mapping of channel TimeSeries objects")
    if not ts_map:
        raise ValueError("No TDI timeseries provided for output")

    first_epoch = None
    first_delta_t = None
    first_length = None
    for series in ts_map.values():
        if not hasattr(series, "data"):
            raise TypeError("All values in TDI mapping must be TimeSeries objects")
        epoch = float(series.epoch)
        delta_t = float(series.delta_t)
        length = len(series.data)
        if first_epoch is None:
            first_epoch = epoch
            first_delta_t = delta_t
            first_length = length
        elif epoch != first_epoch:
            raise ValueError("Inconsistent epoch values across TDI timeseries")
        elif delta_t != first_delta_t:
            raise ValueError("Inconsistent delta_t across TDI timeseries")
        elif length != first_length:
            raise ValueError("Inconsistent length across TDI timeseries")

    data_object = _MojitoTDIData(ts_map)
    time_sampling = UniformTimeSampling(
        t0=first_epoch, dt=first_delta_t, size=first_length
    )
    filepath = Path(filepath)
    with writer.MojitoL1File(filepath, mode="w") as mojito_file:
        with silence_logger("mojito.writer"):
            writer.create_tdis(mojito_file, time_sampling, data=data_object)
        root = mojito_file.files[0]
        root.attrs["epoch"] = first_epoch
        root.attrs["delta_t"] = first_delta_t


def write_mojito_orbits(orbits_obj, filepath):
    """Write an orbits-only Mojito L1 file.

    Parameters
    ----------
    orbits_obj:
        Mojito Orbits object or a lightweight object with orbit datasets.
    filepath:
        Output HDF5 file path.
    """
    from mojito import writer

    if orbits_obj is None:
        raise ValueError("No orbits object provided for output")
    if not hasattr(orbits_obj, "time_sampling"):
        raise TypeError("Orbits object must provide time_sampling")

    time_sampling = orbits_obj.time_sampling
    filepath = Path(filepath)
    with writer.MojitoL1File(filepath, mode="w") as mojito_file:
        with silence_logger("mojito.writer"):
            writer.create_orbits(mojito_file, time_sampling, data=orbits_obj)
        root = mojito_file.files[0]
        root.attrs["epoch"] = float(time_sampling.t0)
        root.attrs["delta_t"] = float(time_sampling.dt)
