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
    dataset_option: str = None,
    data_required: bool = True,
    default_dataset: str = "data",
    data_help: str = "Input HDF5 data file",
    dataset_help: str | None = None,
) -> argparse._ArgumentGroup:
    """Add standard data-input file and dataset CLI arguments."""
    grp = parser.add_argument_group("data input")
    grp.add_argument(data_option, required=data_required, help=data_help)
    grp.add_argument(
        dataset_option,
        default=default_dataset,
        help=(
            dataset_help
            or f"Dataset in {data_option} (default: {default_dataset})"
        ),
    )
    return grp


def add_data_output_args(
    parser: argparse.ArgumentParser,
    *,
    output_option: str = "--output",
    dataset_option: str = "--output-dataset",
    output_required: bool = True,
    default_dataset: str = "data",
    output_help: str = "Output HDF5 file",
    dataset_help: str | None = None,
) -> argparse._ArgumentGroup:
    """Add standard data-output file and dataset CLI arguments."""
    grp = parser.add_argument_group("data output")
    grp.add_argument(output_option, required=output_required, help=output_help)
    grp.add_argument(
        dataset_option,
        default=default_dataset,
        help=(
            dataset_help
            or f"Dataset in {output_option} (default: {default_dataset})"
        ),
    )
    return grp


def add_signal_input_args(
    parser: argparse.ArgumentParser,
) -> argparse._ArgumentGroup:
    """Add signal-file input and signal-dataset CLI arguments."""
    grp = parser.add_argument_group("signal input")
    grp.add_argument(
        "--signal",
        nargs="+",
        required=True,
        metavar="FILE",
        help="One or more HDF5 signal files to subtract",
    )
    grp.add_argument(
        "--signal-dataset",
        nargs="+",
        default=None,
        metavar="DATASET",
        help=(
            "Dataset name(s) in signal files; one per file or a single "
            "value broadcast to all (default: 'signal')"
        ),
    )
    return grp


def resolve_signal_datasets(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> list[str]:
    """Validate and expand signal dataset args to one entry per signal file."""
    signal_datasets = args.signal_dataset or ["signal"]
    if len(signal_datasets) == 1:
        return signal_datasets * len(args.signal)
    if len(signal_datasets) != len(args.signal):
        parser.error(
            f"--signal-dataset count ({len(signal_datasets)}) must match "
            f"--signal count ({len(args.signal)})"
        )
    return signal_datasets
