"""HDF5 data interface for GWAITH.

All GWAITH HDF5 files carry ``epoch`` (GPS start time) and ``delta_t``
(sample spacing in seconds) as root-level attributes.
"""

from __future__ import annotations

import h5py

from gwaith.types import FrequencySeries, TimeSeries

__all__ = [
    "load_timeseries",
    "write_timeseries",
    "load_frequencyseries",
    "write_frequencyseries",
]


def load_timeseries(filepath: str, dataset_name: str) -> TimeSeries:
    """Load a timeseries from an HDF5 dataset."""
    with h5py.File(filepath, "r") as f:
        if dataset_name not in f:
            raise KeyError(
                f"Dataset '{dataset_name}' not found in {filepath}. "
                f"Available: {list(f.keys())}"
            )
        data = f[dataset_name][:]
        if "epoch" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'epoch'")
        if "delta_t" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'delta_t'")
        epoch = float(f.attrs["epoch"])
        delta_t = float(f.attrs["delta_t"])
    return TimeSeries(data=data, epoch=epoch, delta_t=delta_t)


def load_frequencyseries(filepath: str, dataset_name: str) -> FrequencySeries:
    """Load a :class:`~gwaith.types.FrequencySeries` from an HDF5 file."""
    with h5py.File(filepath, "r") as f:
        if dataset_name not in f:
            raise KeyError(
                f"Dataset '{dataset_name}' not found in {filepath}. "
                f"Available: {list(f.keys())}"
            )
        if "frequencies" not in f:
            raise KeyError(
                f"File {filepath!r} is missing required dataset 'frequencies'"
            )
        if "epoch" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'epoch'")
        if "delta_t" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'delta_t'")
        data = f[dataset_name][:]
        frequencies = f["frequencies"][:]
        epoch = float(f.attrs["epoch"])
        delta_t = float(f.attrs["delta_t"])
    return FrequencySeries(
        data=data, frequencies=frequencies, epoch=epoch, delta_t=delta_t
    )


def write_timeseries(ts: TimeSeries, filepath: str, dataset_name: str) -> None:
    """Write a :class:`~gwaith.types.TimeSeries` to an HDF5 file."""
    with h5py.File(filepath, "w") as f:
        f.create_dataset(dataset_name, data=ts.data)
        f.attrs["epoch"] = ts.epoch
        f.attrs["delta_t"] = ts.delta_t


def write_frequencyseries(
    series: FrequencySeries, filepath: str, dataset_name: str, **attrs
) -> None:
    """Write a :class:`~gwaith.types.FrequencySeries` to an HDF5 file."""
    with h5py.File(filepath, "w") as f:
        f.create_dataset(dataset_name, data=series.data)
        f.create_dataset("frequencies", data=series.frequencies)
        f.attrs["epoch"] = series.epoch
        f.attrs["delta_t"] = series.delta_t
        for key, val in attrs.items():
            f.attrs[key] = val
