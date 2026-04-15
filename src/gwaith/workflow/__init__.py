from .helpers import (
    make_file_uid,
    make_node_uid,
    register_file,
    register_node
)
from .types import (
    GwaithFile,
    GwaithNode,
    GwaithStream
)

def add_workflow_input_options(parser):
    parser.add_argument(
        "--workflow-name",
        required=True,
        help="Name of the workflow",
    )
    parser.add_argument(
        "--workflow-dir",
        help="Path to the workflow directory, default is same as --workflow-name"
    )

__all__ = [
    "add_workflow_input_options",
    'GwaithFile',
    'GwaithNode',
    'GwaithStream',
    'make_file_uid',
    'make_node_uid',
    'register_file',
    'register_node',
]
