"""GWAITH data processing backends for ingestion.

This package exposes file-type-specific processors and a single helper to
select the appropriate backend based on parsed CLI args.
"""
import logging

from gwaith.io import KeyValueOptionAction

from .ldc import process_ldc
from .mojito import process_mojito

logger = logging.getLogger('gwaith.process')

PROCESSORS = {
    'mojito': process_mojito,
    'ldc': process_ldc
}

def process(parser, args, processor_name=None):
    """Dispatch to the selected processing backend.

    Args:
        parser: CLI argument parser used to build the ingest command.
        args: Parsed CLI arguments from the ingest command.

    Returns:
        dict: Mapping from output dataset name to TimeSeries objects.

    Raises:
        ValueError: If the processor name is unknown.
    """
    try:
        backend = PROCESSORS[processor_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown processor '{processor_name}'. Supported values: {', '.join(PROCESSORS)}"
        ) from exc
    return backend(parser, args)



def add_data_processing_args(parser):
    grp = parser.add_argument_group('processor')
    parser.add_argument(
        '--processor',
        choices=list(PROCESSORS.keys()),
    )
    grp.add_argument(
        '--processor-options',
        nargs='+',
        action=KeyValueOptionAction,
        default={},
        help='Processor-specific keyword options in key:value form, e.g.'
             '--processor-options target_fs:0.2'
        )
    return None
        

