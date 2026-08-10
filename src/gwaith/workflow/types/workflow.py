"""GwaithWorkflow type definition."""


class GwaithWorkflow:
    def __init__(
        self,
        cp,
        name,
        workflow_dir,
        rounds,
        input_data=None,
        global_retention_level=None,
    ):
        self.cp = cp
        self.name = name
        self.workflow_dir = workflow_dir
        self.rounds = rounds
        self.input = input_data or {}
        self.input_data = self.input
        self.global_retention_level = global_retention_level
        self.streams = []
        self.nodes = []
        self.files = []
        self.round_entries = []
        self.final_residual_file = None
        self.final_noise_file = None
        self.final_params = {}
        self.manifest = None
        self.master_script = None

    def from_cli(self, args):
        """
        Build a GwaithWorkflow object from the command line arguments.

        Args:
            args (argparse.Namespace):

        Returns:
            GwaithWorkflow:
        """

    @classmethod
    def add_input_options(parser):
        """
        Adds an argumnet group to an argparse ArgumentParser with the options
        needed to define a workflow.

        Args:
            parser (argparse.ArgumentParser):
        """
        grp = parser.add_argument_group("Workflow options")
        grp.add_argument(
            "--workflow-name",
            required=True,
            help="Name of the workflow",
        )
        grp.add_argument(
            "--workflow-dir",
            help="Path to the workflow directory, default is same as --workflow-name",
        )
        grp.add_argument(
            "--exporter",
            default=None,
            help=(
                "Workflow exporter to use (e.g., 'bash', 'slurm', 'pegasus'). "
                "Can also be set via GWAITH_EXPORTER environment variable. "
                "Defaults to 'bash'."
            ),
        )
        grp.add_argument(
            "--submit-now", action="store_true", help="If given, submit the workflow"
        )
