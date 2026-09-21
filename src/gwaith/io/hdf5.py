"""HDF5 data interface for GWAITH.

All GWAITH HDF5 files carry ``epoch`` (GPS start time) and ``delta_t``
(sample spacing in seconds) as root-level attributes.
"""

from __future__ import annotations

import h5py
import os

from gwaith.types import FrequencySeries, TimeSeries

__all__ = [
    "load_frequencyseries",
    "load_timeseries",
    "write_frequencyseries",
    "write_timeseries",
]


def load_timeseries(filepath: str, dataset_name: str | None = None) -> TimeSeries:
    """Load a timeseries from an HDF5 dataset."""
    actual_dataset_name = dataset_name if dataset_name is not None else "timeseries"
    with h5py.File(filepath, "r") as f:
        if actual_dataset_name not in f:
            raise KeyError(
                f"Dataset '{actual_dataset_name}' not found in {filepath}. "
                f"Available: {list(f.keys())}"
            )
        data = f[actual_dataset_name][:]
        if "epoch" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'epoch'")
        if "delta_t" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'delta_t'")
        epoch = float(f.attrs["epoch"])
        delta_t = float(f.attrs["delta_t"])
    return TimeSeries(data=data, epoch=epoch, delta_t=delta_t)


def load_frequencyseries(
    filepath: str, dataset_name: str | None = None
) -> FrequencySeries:
    """Load a :class:`~gwaith.types.FrequencySeries` from an HDF5 file."""
    actual_dataset_name = (
        dataset_name if dataset_name is not None else "frequencyseries"
    )
    with h5py.File(filepath, "r") as f:
        if actual_dataset_name not in f:
            raise KeyError(
                f"Dataset '{actual_dataset_name}' not found in {filepath}. "
                f"Available: {list(f.keys())}"
            )
        data = f[actual_dataset_name][:]
        if "f0" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'f0'")
        if "delta_f" not in f.attrs:
            raise KeyError(f"File {filepath!r} is missing required attribute 'delta_f'")
        f0 = float(f.attrs["f0"])
        delta_f = float(f.attrs["delta_f"])

        epoch = float(f.attrs["epoch"]) if "epoch" in f.attrs else None

    return FrequencySeries(data=data, delta_f=delta_f, f0=f0, epoch=epoch)


def _resolve_file_permission(filepath: str, file_permission: str | None) -> str:
    """Resolve the h5py open mode for a write operation.

    If ``file_permission`` is given it is used as-is (preferred over any
    detection). Otherwise the mode is detected from the file: an existing
    file is opened in append mode (``"a"``), a missing file in write mode
    (``"w"``).
    """
    if file_permission is not None:
        return file_permission
    return "a" if os.path.exists(filepath) else "w"


def write_timeseries(
    ts: TimeSeries,
    filepath: str,
    dataset_name: str | None = None,
    file_permission: str | None = None,
    overwrite: bool = True,
) -> None:
    """Write a :class:`~gwaith.types.TimeSeries` to an HDF5 file.

    Parameters
    ----------
    ts:
        TimeSeries object to save.
    filepath:
        Path to output file.
    dataset_name:
        Name of the dataset in the file (default: 'timeseries').
    file_permission:
        h5py open mode to use ('w', 'a', 'r+'). If given, it is preferred
        over detection; otherwise an existing file is opened in append mode
        ('a') and a missing file in write mode ('w').
    overwrite:
        If True (default), replace any existing dataset with the same name.
        If False, raise an error when the dataset already exists.
    """
    actual_dataset_name = dataset_name if dataset_name is not None else "timeseries"
    permission = _resolve_file_permission(filepath, file_permission)
    with h5py.File(filepath, permission) as f:
        if actual_dataset_name in f:
            if not overwrite:
                raise ValueError(
                    f"Dataset '{actual_dataset_name}' already exists in {filepath}"
                )
            del f[actual_dataset_name]
        f.create_dataset(actual_dataset_name, data=ts.data)
        f.attrs["epoch"] = ts.epoch
        f.attrs["delta_t"] = ts.delta_t


def write_frequencyseries(
    fseries: FrequencySeries,
    filepath: str,
    dataset_name: str | None = None,
    file_permission: str | None = None,
    overwrite: bool = True,
    **attrs,
) -> None:
    """Write a :class:`~gwaith.types.FrequencySeries` to an HDF5 file.

    Parameters
    ----------
    fseries:
        FrequencySeries object to save.
    filepath:
        Path to output file.
    dataset_name:
        Name of the dataset in the file (default: 'frequencyseries').
    file_permission:
        h5py open mode to use ('w', 'a', 'r+'). If given, it is preferred
        over detection; otherwise an existing file is opened in append mode
        ('a') and a missing file in write mode ('w').
    overwrite:
        If True (default), replace any existing dataset with the same name.
        If False, raise an error when the dataset already exists.
    **attrs:
        Additional attributes to store in the file.
    """
    actual_dataset_name = (
        dataset_name if dataset_name is not None else "frequencyseries"
    )
    permission = _resolve_file_permission(filepath, file_permission)
    with h5py.File(filepath, permission) as f:
        if actual_dataset_name in f:
            if not overwrite:
                raise ValueError(
                    f"Dataset '{actual_dataset_name}' already exists in {filepath}"
                )
            del f[actual_dataset_name]
        f.create_dataset(actual_dataset_name, data=fseries.data)
        f.attrs["f0"] = fseries.f0
        f.attrs["delta_f"] = fseries.delta_f
        if hasattr(fseries, "epoch"):
            f.attrs["epoch"] = fseries.epoch
        for key, val in attrs.items():
            f.attrs[key] = val
