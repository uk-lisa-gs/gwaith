"""GWAITH I/O: file format dispatcher for series save/load methods."""

from pathlib import Path

from .cli import (
    add_data_input_args,
    add_data_output_args,
    add_signal_input_args,
    MultiOptionAction,
    KeyValueOptionAction
)
from .hdf5 import (
    load_frequencyseries as load_frequencyseries_hdf5,
    load_timeseries as load_timeseries_hdf5,
    write_frequencyseries as write_frequencyseries_hdf5,
    write_timeseries as write_timeseries_hdf5,
)


from .mojito import (
    write_mojito_orbits,
    write_mojito_tdis,
)

__all__ = [
    "get_format_from_filename",
    "add_data_input_args",
    "add_data_output_args",
    "add_signal_input_args",
    "resolve_filenames_datasets",
    "write_timeseries",
    "load_timeseries",
    "write_frequencyseries",
    "load_frequencyseries",
    'write_mojito_orbits',
    'write_mojito_tdis',
    'MultiOptionAction',
    'KeyValueOptionAction'
]


def get_format_from_filename(filepath: str) -> str:
    """Determine file format from filename extension.

    Parameters
    ----------
    filepath:
        Path to the file.

    Returns
    -------
    format:
        Format identifier ('hdf5').

    Raises
    ------
    ValueError:
        If file extension is not recognized.
    """
    suffix = Path(filepath).suffix.lower()
    if suffix in (".h5", ".hdf5", ".hdf"):
        return "hdf5"
    raise ValueError(
        "Unsupported file format: "
        f"{suffix!r}. Supported formats: .h5, .hdf5, .hdf"
    )


def write_timeseries(ts, filepath: str, dataset_name: str = "data") -> None:
    """Write a TimeSeries to file, auto-detecting format from extension.

    Parameters
    ----------
    ts:
        TimeSeries object to save.
    filepath:
        Path to output file.
    dataset_name:
        Name of the dataset in the file (default: 'data').
    """
    fmt = get_format_from_filename(filepath)
    if fmt == "hdf5":
        write_timeseries_hdf5(ts, filepath, dataset_name)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def load_timeseries(filepath: str, dataset_name: str = "data"):
    """Load a TimeSeries from file, auto-detecting format from extension.

    Parameters
    ----------
    filepath:
        Path to input file.
    dataset_name:
        Name of the dataset in the file (default: 'data').

    Returns
    -------
    ts:
        Loaded TimeSeries object.
    """
    fmt = get_format_from_filename(filepath)
    if fmt == "hdf5":
        return load_timeseries_hdf5(filepath, dataset_name)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def write_frequencyseries(
    series, filepath: str, dataset_name: str = "psd", **attrs
) -> None:
    """Write a FrequencySeries to file, auto-detecting format from extension.

    Parameters
    ----------
    series:
        FrequencySeries object to save.
    filepath:
        Path to output file.
    dataset_name:
        Name of the dataset in the file (default: 'psd').
    **attrs:
        Additional attributes to store in the file.
    """
    fmt = get_format_from_filename(filepath)
    if fmt == "hdf5":
        write_frequencyseries_hdf5(series, filepath, dataset_name, **attrs)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def load_frequencyseries(filepath: str, dataset_name: str = "psd"):
    """Load a FrequencySeries from file, auto-detecting format from extension.

    Parameters
    ----------
    filepath:
        Path to input file.
    dataset_name:
        Name of the dataset in the file (default: 'psd').

    Returns
    -------
    fs:
        Loaded FrequencySeries object.
    """
    fmt = get_format_from_filename(filepath)
    if fmt == "hdf5":
        return load_frequencyseries_hdf5(filepath, dataset_name)
    else:
        raise ValueError(f"Unknown format: {fmt}")
