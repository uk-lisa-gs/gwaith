"""CLI argument helpers for GWAITH I/O tools."""

from __future__ import annotations

import argparse


def parse_key_value_tokens(parser, option_string, values):
    tokens = values if isinstance(values, list) else [values]
    out = {}
    for token in tokens:
        if ":" not in token:
            parser.error(
                f"{option_string} mixed values are not allowed; use all key:value pairs"
            )
        key, value = token.split(":", 1)
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
        has_mapping = any(":" in token for token in tokens)

        if not has_mapping:
            if len(tokens) != 1:
                parser.error(
                    f"{option_string} expects either one value or key:value pairs"
                )
            setattr(namespace, self.dest, tokens[0])
            return

        setattr(
            namespace, self.dest, parse_key_value_tokens(parser, option_string, tokens)
        )


class KeyValueOptionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        tokens = values if isinstance(values, list) else [values]
        if not any(":" in token for token in tokens):
            parser.error(f"{option_string} requires key:value pairs")
        setattr(
            namespace, self.dest, parse_key_value_tokens(parser, option_string, tokens)
        )


def add_data_input_args(
    parser: argparse.ArgumentParser,
    *,
    data_option: str = "--data",
    data_required: bool = True,
    data_help: str = "Input HDF5 data file",
) -> argparse._ArgumentGroup:
    """Add standard data-input file CLI arguments.

    Parameters
    ----------
    parser : ArgumentParser
        The argument parser to add data input arguments to.
    data_option : str
        The name of the data file option (default: "--data").
    data_required : bool
        Whether the data file argument is required (default: True).
    data_help : str
        Help text for the data file argument.
    """
    grp = parser.add_argument_group("data input")
    grp.add_argument(
        data_option,
        required=data_required,
        help=data_help,
    )
    return grp


def add_data_output_args(
    parser: argparse.ArgumentParser,
    *,
    output_option: str = "--output",
    output_required: bool = True,
    output_help: str = "Output HDF5 file",
) -> argparse._ArgumentGroup:
    """Add standard data-output file CLI arguments.

    Parameters
    ----------
    parser : ArgumentParser
        The argument parser to add output arguments to.
    output_option : str
        The name of the output file option (default: "--output").
    output_required : bool
        Whether the output file argument is required (default: True). Set to
        False for tools that can write to stdout when no output file is
        specified.
    output_help : str
        Help text for the output file argument.
    output_group_default : str | None
        The default value for the output-group option. If None, no group
        argument is added. This is needed when tools expect
        ``args.output_group``.
    """
    grp = parser.add_argument_group("data output")
    grp.add_argument(
        output_option,
        required=output_required,
        help=output_help,
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
        raise ValueError("Both filenames and datasets must be provided")
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
        return list(zip(filenames, datasets, strict=True))
