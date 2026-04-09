#!/usr/bin/env python
"""Consolidate workflow module parameter files into one YAML output."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

from gwaith import add_gwaith_common_options, init_logging

logger = logging.getLogger("gwaith.workflow.consolidate")


def _parse_module_param(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "--module-param entries must be in the form <module_name>=<path>"
        )
    name, path = value.split("=", 1)
    name = name.strip()
    path = path.strip()
    if not name or not path:
        raise argparse.ArgumentTypeError(
            "--module-param entries must include both module name and path"
        )
    return name, path


def consolidate_params(
    final_round: int,
    module_params: list[tuple[str, str]],
    output_file: Path,
) -> None:
    module_outputs: dict[str, object] = {}

    for name, path in module_params:
        with Path(path).open("r", encoding="utf-8") as f:
            module_outputs[name] = yaml.safe_load(f)

    payload = {
        "round": int(final_round),
        "module_outputs": module_outputs,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_consolidate_params",
        description="Consolidate final-round workflow parameter files into one YAML output.",
    )
    parser.add_argument("--round", type=int, required=True, help="Final round index")
    parser.add_argument(
        "--module-param",
        action="append",
        default=[],
        type=_parse_module_param,
        help="Module output mapping in the form <module_name>=<params_yaml_path>. Repeat for each module.",
    )
    parser.add_argument("--output", required=True, help="Output consolidated YAML path")
    add_gwaith_common_options(parser)
    args = parser.parse_args(argv)

    init_logging(args.verbose)
    consolidate_params(
        final_round=args.round,
        module_params=args.module_param,
        output_file=Path(args.output),
    )
    logger.info("Wrote consolidated params to %s", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
