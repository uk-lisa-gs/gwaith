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
