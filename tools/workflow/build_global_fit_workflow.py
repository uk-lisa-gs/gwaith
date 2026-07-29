"""Generate iterative GWAITH workflow using a blocked Gibbs sampling approach."""

from __future__ import annotations

import argparse
import logging

from gwaith import add_gwaith_common_options, init_logging
from gwaith.config import GwaithConfigParser, add_config_input_options
from gwaith.workflow import (
    add_workflow_input_options,
    build_workflow,
)
from gwaith.workflow.exporters import get_exporter, output_workflow
from gwaith.types import GwaithFile


logger = logging.getLogger("gwaith.tools.workflow.build_workflow")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gwaith_build_global_fit_workflow",
        description="Generate LISA global fit GWAITH workflow from config.",
    )
    add_gwaith_common_options(parser)
    add_workflow_input_options(parser)
    add_config_input_options(parser)

    args = parser.parse_args(argv)
    init_logging(args.verbose)

    # Also log to a file, so that the generator log can be added to the results page
    wf_log_file = GwaithFile(
        args.workflow_dir / f'{args.workflow_name}_workflow_generation.log'
    )
    init_logging(args.verbose, wf_log_file)

    logger.info("Loading Config")
    config_parser = GwaithConfigParser.from_cli(args)
    
    # Build workflow graph without exporting yet
    logger.info("Building workflow graph")
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