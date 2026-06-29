"""CLI argument helpers for GWAITH I/O tools."""

from __future__ import annotations

import argparse

def parse_key_value_tokens(parser, option_string, values):
    tokens = values if isinstance(values, list) else [values]
    out = {}
    for token in tokens:
        if ':' not in token:
            parser.error(f'{option_string} mixed values are not allowed; use all key:value pairs')
        key, value = token.split(':', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            parser.error(f"{option_string} has an empty key in '{token}'")
        if key in out:
            parser.error(f"{option_string} has duplicate key '{key}'")
        out[key] = value
    return out


class MultiOptionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        tokens = values if isinstance(values, list) else [values]
        has_mapping = any(':' in token for token in tokens)

        if not has_mapping:
            if len(tokens) != 1:
                parser.error(f'{option_string} expects either one value or key:value pairs')
            setattr(namespace, self.dest, tokens[0])
            return

        setattr(namespace, self.dest, parse_key_value_tokens(parser, option_string, tokens))


class KeyValueOptionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        tokens = values if isinstance(values, list) else [values]
        if not any(':' in token for token in tokens):
            parser.error(f'{option_string} requires key:value pairs')
        setattr(namespace, self.dest, parse_key_value_tokens(parser, option_string, tokens))


def add_data_input_args(
    parser: argparse.ArgumentParser,
    *,
    data_option: str = "--data",
    data_required: bool = True,
    data_help: str = "Input HDF5 data file",
) -> argparse._ArgumentGroup:
    """Add standard data-input file and dataset CLI arguments."""
    grp = parser.add_argument_group("data input")
    grp.add_argument(
        "--data-file",
        required=True,
        help="Input HDF5 data file containing original data"
    )
    grp.add_argument(
        "--data-group",
        required=False,
        help="Group in the data hdf5 file which contains datasets for each channel"
    )
    return grp


def add_data_output_args(
    parser: argparse.ArgumentParser,
) -> argparse._ArgumentGroup:
    """Add standard data-output file and dataset CLI arguments."""
    grp = parser.add_argument_group("data output")
    grp.add_argument(
        "--output-filename",
        required=True,
        help="Output HDF5 file"
    )
    grp.add_argument(
        "--output-group",
        required=False,
        help="Output datasets into this group in the output hdf5 file - default is to use the file root group"
    )
    return grp


def add_signal_input_args(
    parser: argparse.ArgumentParser,
) -> argparse._ArgumentGroup:
    """Add signal-file input and signal-dataset CLI arguments."""
    grp = parser.add_argument_group("signal input")
    grp.add_argument(
        "--signal-files",
        nargs="+",
        required=True,
        metavar="FILE",
        help="One or more HDF5 signal file(s) to subtract. "
        "One file and multiple datasets (given by signal--datasets) or "
        "the same dataset name shared over multiple files (i.e. one "
        "filename, multiple signal-datasets values) can be used.",
    )
    grp.add_argument(
        "--signal-groups",
        nargs="+",
        metavar="DATASET",
        help=(
            "Signal group name(s) in signal files; one per file or a single "
            "value broadcast to file, or multiple values cast to a "
            "single file"
        ),
    )
    return grp


def resolve_filenames_datasets(
    filenames: list[str],
    datasets: list[str],
) -> list[str]:
    """
    Convert signal dataset name(s) and filename(s) to a list of paired
    tuples of datasets / filenames

    This function will return a list of tuples of filenames and datasets
    This can be used as e.g. zip(*resolve_filename_datasets(filenames, dataset))
    """

    # The filenames and datasets can be any of:
    # 1) 1 filename and N dataset names
    # 2) 1 dataset name and N filenames
    # 3) N filenames and N datasets

    if len(filenames) == 0 or len(datasets) == 0:
        raise ValueError(
            "Both filenames and datasets must be provided"
        )
    if len(filenames) != 1 and len(datasets) != 1:
        if not len(datasets) == len(filenames):
            raise ValueError(
                "filenames and datasets must be the same length "
                "or one must have length one"
            )
    
    if len(filenames) == 1 and len(datasets) == 1:
        return [(filenames[0], datasets[0])]
    elif len(filenames) == 1 and len(datasets) > 1:
        return [(filenames[0], d) for d in datasets]
    elif len(filenames) > 1 and len(datasets) == 1:
        return [(f, datasets[0]) for f in filenames]
    else:
        return list(zip(filenames, datasets))
    
