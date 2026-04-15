"""Generate a basic iterative GWAITH workflow as bash scripts.

Per round:
1. Estimate noise (PSD)
2. Run module jobs in parallel (interchangeable tools)
3. Subtract all produced module signals from the round input data

After all rounds:
- consolidate parameter files into one YAML
- estimate final noise from the final residual
"""

import argparse
import logging
from pathlib import Path

import yaml
from gwaith import add_gwaith_common_options, init_logging
from gwaith.workflow import (
    add_workflow_input_options,
)
from gwaith.config import (
    GwaithConfigParser,
    add_config_input_options,
)

logger = logging.getLogger('gwaith.tools.workflow.build_workflow')

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='gwaith_build_workflow',
        description='Generate iterative GWAITH workflow from config.'
    )
    add_gwaith_common_options(parser)
    add_workflow_input_options(parser)
    add_config_input_options(parser)
    args = parser.parse_args(argv)
    init_logging(args.verbose)
    logger.info("Loading Config")
    parser = GwaithConfigParser.from_cli(args)
    print(parser._data)
    # result = build_workflow(config)
    # logger.info('Workflow created in: %s', result['workflow_dir'])
    # logger.info('Manifest: %s', result['manifest'])
    # logger.info('Run with: %s', result['master_script'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
