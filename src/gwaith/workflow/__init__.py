from .helpers import (
    make_file_uid,
    make_node_uid,
    register_file,
    register_node
)
from .generator import (
    build_workflow,
    build_workflow_graph,
)
from .exporters import output_workflow
from .types import (
    GwaithFile,
    GwaithNode,
    GwaithStream,
    GwaithWorkflow
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
    parser.add_argument(
        "--exporter",
        default=None,
        help=(
            "Workflow exporter to use (e.g., 'bash', 'slurm', 'pegasus'). "
            "Can also be set via GWAITH_EXPORTER environment variable. "
            "Defaults to 'bash'."
        ),
    )

__all__ = [
    "add_workflow_input_options",
    'GwaithFile',
    'GwaithNode',
    'GwaithStream',
    'GwaithWorkflow',
    'make_file_uid',
    'make_node_uid',
    'register_file',
    'register_node',
    'build_workflow',
    'build_workflow_graph',
    'output_workflow',
]
