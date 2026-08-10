"""GwaithFile type definition."""
from ..helpers import make_file_uid


class GwaithFile:
    def __init__(
        self,
        final_path,
        local_path=None,
        dataset=None,
        uid=None,
        kind=None,
        retention_level=None,
        produced_by=None,
        round_index=None,
        stream_uid=None,
    ):
        # The file path that it will be moved to after it is no longer needed
        self.final_path = final_path
        # The local path that the file will be saved in until it has been
        # used for the final time
        if local_path is None:
            self.local_path = final_path
        else:
            self.local_path = local_path
        # This is the unique identifier by which we will refer to the file
        # from other nodes etc.
        self.uid = uid
        self.file_uid = uid
        # a retention level to indicate to compare to a global level to see
        # if the file will just b e deleted after it has been used
        self.retention_level = retention_level
        # The UID of the node that created the file
        self.produced_by = produced_by
        # The UIDs of node that will use the file down the line
        self.used_by = []
        # The round associated with this file
        self.round_index = round_index
        # The stream associated with this file
        self.stream = stream_uid
        # The dataset name used when reading/writing the file, if any
        self.dataset = dataset
        # Logical role in the workflow graph
        self.kind = kind
