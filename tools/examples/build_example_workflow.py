"""Generate iterative GWAITH workflow artifacts from parsed config files."""

from __future__ import annotations

import argparse
import logging

from gwaith import add_gwaith_common_options, init_logging
from gwaith.config import GwaithConfigParser, add_config_input_options
from gwaith.workflow import add_workflow_input_options, build_workflow
from gwaith.workflow.exporters import get_exporter, output_workflow

logger = logging.getLogger("gwaith.tools.workflow.build_workflow")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_build_exmple_workflow",
        description="Generate example iterative GWAITH workflow from config.",
    )
    add_gwaith_common_options(parser)
    add_workflow_input_options(parser)
    add_config_input_options(parser)

    args = parser.parse_args(argv)
    init_logging(args.verbose)

    logger.info("Loading Config")
    config_parser = GwaithConfigParser.from_cli(args)
    workflow = build_workflow(
        config_parser,
        workflow_name=args.workflow_name,
        workflow_dir=args.workflow_dir,
    )
    
    # Export workflow to disk
    logger.info("Exporting workflow")
    exporter = get_exporter(args.exporter)
    workflow = output_workflow(workflow, exporter=exporter)

    logger.info("Workflow created in: %s", workflow.workflow_dir)
    logger.info("Manifest: %s", workflow.manifest)
    logger.info("Run with: %s", workflow.master_script)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())